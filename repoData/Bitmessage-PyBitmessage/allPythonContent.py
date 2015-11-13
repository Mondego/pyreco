__FILENAME__ = addresses
import hashlib
from struct import *
from pyelliptic import arithmetic



#There is another copy of this function in Bitmessagemain.py
def convertIntToString(n):
    a = __builtins__.hex(n)
    if a[-1:] == 'L':
        a = a[:-1]
    if (len(a) % 2) == 0:
        return a[2:].decode('hex')
    else:
        return ('0'+a[2:]).decode('hex')

ALPHABET = "123456789ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz"

def encodeBase58(num, alphabet=ALPHABET):
    """Encode a number in Base X

    `num`: The number to encode
    `alphabet`: The alphabet to use for encoding
    """
    if (num == 0):
        return alphabet[0]
    arr = []
    base = len(alphabet)
    while num:
        rem = num % base
        #print 'num is:', num
        num = num // base
        arr.append(alphabet[rem])
    arr.reverse()
    return ''.join(arr)

def decodeBase58(string, alphabet=ALPHABET):
    """Decode a Base X encoded string into the number

    Arguments:
    - `string`: The encoded string
    - `alphabet`: The alphabet to use for encoding
    """
    base = len(alphabet)
    strlen = len(string)
    num = 0

    try:
        power = strlen - 1
        for char in string:
            num += alphabet.index(char) * (base ** power)
            power -= 1
    except:
        #character not found (like a space character or a 0)
        return 0
    return num

def encodeVarint(integer):
    if integer < 0:
        print 'varint cannot be < 0'
        raise SystemExit
    if integer < 253:
        return pack('>B',integer)
    if integer >= 253 and integer < 65536:
        return pack('>B',253) + pack('>H',integer)
    if integer >= 65536 and integer < 4294967296:
        return pack('>B',254) + pack('>I',integer)
    if integer >= 4294967296 and integer < 18446744073709551616:
        return pack('>B',255) + pack('>Q',integer)
    if integer >= 18446744073709551616:
        print 'varint cannot be >= 18446744073709551616'
        raise SystemExit

def decodeVarint(data):
    if len(data) == 0:
        return (0,0)
    firstByte, = unpack('>B',data[0:1])
    if firstByte < 253:
        return (firstByte,1) #the 1 is the length of the varint
    if firstByte == 253:
        a, = unpack('>H',data[1:3])
        return (a,3)
    if firstByte == 254:
        a, = unpack('>I',data[1:5])
        return (a,5)
    if firstByte == 255:
        a, = unpack('>Q',data[1:9])
        return (a,9)



def calculateInventoryHash(data):
    sha = hashlib.new('sha512')
    sha2 = hashlib.new('sha512')
    sha.update(data)
    sha2.update(sha.digest())
    return sha2.digest()[0:32]

def encodeAddress(version,stream,ripe):
    if version >= 2 and version < 4:
        if len(ripe) != 20:
            raise Exception("Programming error in encodeAddress: The length of a given ripe hash was not 20.")
        if ripe[:2] == '\x00\x00':
            ripe = ripe[2:]
        elif ripe[:1] == '\x00':
            ripe = ripe[1:]
    elif version == 4:
        if len(ripe) != 20:
            raise Exception("Programming error in encodeAddress: The length of a given ripe hash was not 20.")
        ripe = ripe.lstrip('\x00')

    a = encodeVarint(version) + encodeVarint(stream) + ripe
    sha = hashlib.new('sha512')
    sha.update(a)
    currentHash = sha.digest()
    #print 'sha after first hashing: ', sha.hexdigest()
    sha = hashlib.new('sha512')
    sha.update(currentHash)
    #print 'sha after second hashing: ', sha.hexdigest()

    checksum = sha.digest()[0:4]
    #print 'len(a) = ', len(a)
    #print 'checksum = ', checksum.encode('hex')
    #print 'len(checksum) = ', len(checksum)

    asInt = int(a.encode('hex') + checksum.encode('hex'),16)
    #asInt = int(checksum.encode('hex') + a.encode('hex'),16)
    # print asInt
    return 'BM-'+ encodeBase58(asInt)

def decodeAddress(address):
    #returns (status, address version number, stream number, data (almost certainly a ripe hash))

    address = str(address).strip()

    if address[:3] == 'BM-':
        integer = decodeBase58(address[3:])
    else:
        integer = decodeBase58(address)
    if integer == 0:
        status = 'invalidcharacters'
        return status,0,0,""
    #after converting to hex, the string will be prepended with a 0x and appended with a L
    hexdata = hex(integer)[2:-1]

    if len(hexdata) % 2 != 0:
        hexdata = '0' + hexdata

    #print 'hexdata', hexdata

    data = hexdata.decode('hex')
    checksum = data[-4:]

    sha = hashlib.new('sha512')
    sha.update(data[:-4])
    currentHash = sha.digest()
    #print 'sha after first hashing: ', sha.hexdigest()
    sha = hashlib.new('sha512')
    sha.update(currentHash)
    #print 'sha after second hashing: ', sha.hexdigest()

    if checksum != sha.digest()[0:4]:
        status = 'checksumfailed'
        return status,0,0,""
    #else:
    #    print 'checksum PASSED'

    addressVersionNumber, bytesUsedByVersionNumber = decodeVarint(data[:9])
    #print 'addressVersionNumber', addressVersionNumber
    #print 'bytesUsedByVersionNumber', bytesUsedByVersionNumber

    if addressVersionNumber > 4:
        print 'cannot decode address version numbers this high'
        status = 'versiontoohigh'
        return status,0,0,""
    elif addressVersionNumber == 0:
        print 'cannot decode address version numbers of zero.'
        status = 'versiontoohigh'
        return status,0,0,""

    streamNumber, bytesUsedByStreamNumber = decodeVarint(data[bytesUsedByVersionNumber:])
    #print streamNumber
    status = 'success'
    if addressVersionNumber == 1:
        return status,addressVersionNumber,streamNumber,data[-24:-4]
    elif addressVersionNumber == 2 or addressVersionNumber == 3:
        if len(data[bytesUsedByVersionNumber+bytesUsedByStreamNumber:-4]) == 19:
            return status,addressVersionNumber,streamNumber,'\x00'+data[bytesUsedByVersionNumber+bytesUsedByStreamNumber:-4]
        elif len(data[bytesUsedByVersionNumber+bytesUsedByStreamNumber:-4]) == 20:
            return status,addressVersionNumber,streamNumber,data[bytesUsedByVersionNumber+bytesUsedByStreamNumber:-4]
        elif len(data[bytesUsedByVersionNumber+bytesUsedByStreamNumber:-4]) == 18:
            return status,addressVersionNumber,streamNumber,'\x00\x00'+data[bytesUsedByVersionNumber+bytesUsedByStreamNumber:-4]
        elif len(data[bytesUsedByVersionNumber+bytesUsedByStreamNumber:-4]) < 18:
            return 'ripetooshort',0,0,""
        elif len(data[bytesUsedByVersionNumber+bytesUsedByStreamNumber:-4]) > 20:
            return 'ripetoolong',0,0,""
        else:
            return 'otherproblem',0,0,""
    elif addressVersionNumber == 4:
        if len(data[bytesUsedByVersionNumber+bytesUsedByStreamNumber:-4]) > 20:
            return 'ripetoolong',0,0,""
        elif len(data[bytesUsedByVersionNumber+bytesUsedByStreamNumber:-4]) < 4:
            return 'ripetooshort',0,0,""
        else:
            x00string = '\x00' * (20 - len(data[bytesUsedByVersionNumber+bytesUsedByStreamNumber:-4]))
            return status,addressVersionNumber,streamNumber,x00string+data[bytesUsedByVersionNumber+bytesUsedByStreamNumber:-4]

def addBMIfNotPresent(address):
    address = str(address).strip()
    if address[:3] != 'BM-':
        return 'BM-'+address
    else:
        return address

if __name__ == "__main__":
    print 'Let us make an address from scratch. Suppose we generate two random 32 byte values and call the first one the signing key and the second one the encryption key:'
    privateSigningKey = '93d0b61371a54b53df143b954035d612f8efa8a3ed1cf842c2186bfd8f876665'
    privateEncryptionKey = '4b0b73a54e19b059dc274ab69df095fe699f43b17397bca26fdf40f4d7400a3a'
    print 'privateSigningKey =', privateSigningKey
    print 'privateEncryptionKey =', privateEncryptionKey
    print 'Now let us convert them to public keys by doing an elliptic curve point multiplication.'
    publicSigningKey = arithmetic.privtopub(privateSigningKey)
    publicEncryptionKey = arithmetic.privtopub(privateEncryptionKey)
    print 'publicSigningKey =', publicSigningKey
    print 'publicEncryptionKey =', publicEncryptionKey

    print 'Notice that they both begin with the \\x04 which specifies the encoding type. This prefix is not send over the wire. You must strip if off before you send your public key across the wire, and you must add it back when you receive a public key.'

    publicSigningKeyBinary = arithmetic.changebase(publicSigningKey,16,256,minlen=64)
    publicEncryptionKeyBinary = arithmetic.changebase(publicEncryptionKey,16,256,minlen=64)

    ripe = hashlib.new('ripemd160')
    sha = hashlib.new('sha512')
    sha.update(publicSigningKeyBinary+publicEncryptionKeyBinary)

    ripe.update(sha.digest())
    addressVersionNumber = 2
    streamNumber = 1
    print 'Ripe digest that we will encode in the address:', ripe.digest().encode('hex')
    returnedAddress = encodeAddress(addressVersionNumber,streamNumber,ripe.digest())
    print 'Encoded address:', returnedAddress
    status,addressVersionNumber,streamNumber,data = decodeAddress(returnedAddress)
    print '\nAfter decoding address:'
    print 'Status:', status
    print 'addressVersionNumber', addressVersionNumber
    print 'streamNumber', streamNumber
    print 'length of data(the ripe hash):', len(data)
    print 'ripe data:', data.encode('hex')


########NEW FILE########
__FILENAME__ = api
# Copyright (c) 2012-2014 Jonathan Warren
# Copyright (c) 2012-2014 The Bitmessage developers

comment= """
This is not what you run to run the Bitmessage API. Instead, enable the API
( https://bitmessage.org/wiki/API ) and optionally enable daemon mode
( https://bitmessage.org/wiki/Daemon ) then run bitmessagemain.py. 
"""

if __name__ == "__main__":
    print comment
    import sys
    sys.exit(0)

from SimpleXMLRPCServer import SimpleXMLRPCRequestHandler
import json

import shared
import time
from addresses import decodeAddress,addBMIfNotPresent,decodeVarint,calculateInventoryHash
import helper_inbox
import helper_sent
import hashlib

from pyelliptic.openssl import OpenSSL
from struct import pack

# Classes
from helper_sql import sqlQuery,sqlExecute,SqlBulkExecute
from debug import logger

# Helper Functions
import proofofwork

str_chan = '[chan]'


class APIError(Exception):
    def __init__(self, error_number, error_message):
        super(APIError, self).__init__()
        self.error_number = error_number
        self.error_message = error_message
    def __str__(self):
        return "API Error %04i: %s" % (self.error_number, self.error_message)

# This is one of several classes that constitute the API
# This class was written by Vaibhav Bhatia. Modified by Jonathan Warren (Atheros).
# http://code.activestate.com/recipes/501148-xmlrpc-serverclient-which-does-cookie-handling-and/
class MySimpleXMLRPCRequestHandler(SimpleXMLRPCRequestHandler):

    def do_POST(self):
        # Handles the HTTP POST request.
        # Attempts to interpret all HTTP POST requests as XML-RPC calls,
        # which are forwarded to the server's _dispatch method for handling.

        # Note: this method is the same as in SimpleXMLRPCRequestHandler,
        # just hacked to handle cookies

        # Check that the path is legal
        if not self.is_rpc_path_valid():
            self.report_404()
            return

        try:
            # Get arguments by reading body of request.
            # We read this in chunks to avoid straining
            # socket.read(); around the 10 or 15Mb mark, some platforms
            # begin to have problems (bug #792570).
            max_chunk_size = 10 * 1024 * 1024
            size_remaining = int(self.headers["content-length"])
            L = []
            while size_remaining:
                chunk_size = min(size_remaining, max_chunk_size)
                L.append(self.rfile.read(chunk_size))
                size_remaining -= len(L[-1])
            data = ''.join(L)

            # In previous versions of SimpleXMLRPCServer, _dispatch
            # could be overridden in this class, instead of in
            # SimpleXMLRPCDispatcher. To maintain backwards compatibility,
            # check to see if a subclass implements _dispatch and dispatch
            # using that method if present.
            response = self.server._marshaled_dispatch(
                data, getattr(self, '_dispatch', None)
            )
        except:  # This should only happen if the module is buggy
            # internal error, report as HTTP server error
            self.send_response(500)
            self.end_headers()
        else:
            # got a valid XML RPC response
            self.send_response(200)
            self.send_header("Content-type", "text/xml")
            self.send_header("Content-length", str(len(response)))

            # HACK :start -> sends cookies here
            if self.cookies:
                for cookie in self.cookies:
                    self.send_header('Set-Cookie', cookie.output(header=''))
            # HACK :end

            self.end_headers()
            self.wfile.write(response)

            # shut down the connection
            self.wfile.flush()
            self.connection.shutdown(1)

    def APIAuthenticateClient(self):
        if 'Authorization' in self.headers:
            # handle Basic authentication
            (enctype, encstr) = self.headers.get('Authorization').split()
            (emailid, password) = encstr.decode('base64').split(':')
            if emailid == shared.config.get('bitmessagesettings', 'apiusername') and password == shared.config.get('bitmessagesettings', 'apipassword'):
                return True
            else:
                return False
        else:
            logger.warn('Authentication failed because header lacks Authentication field')
            time.sleep(2)
            return False

        return False

    def _decode(self, text, decode_type):
        try:
            return text.decode(decode_type)
        except Exception as e:
            raise APIError(22, "Decode error - " + str(e) + ". Had trouble while decoding string: " + repr(text))

    def _verifyAddress(self, address):
        status, addressVersionNumber, streamNumber, ripe = decodeAddress(address)
        if status != 'success':
            logger.warn('API Error 0007: Could not decode address %s. Status: %s.', address, status)

            if status == 'checksumfailed':
                raise APIError(8, 'Checksum failed for address: ' + address)
            if status == 'invalidcharacters':
                raise APIError(9, 'Invalid characters in address: ' + address)
            if status == 'versiontoohigh':
                raise APIError(10, 'Address version number too high (or zero) in address: ' + address)
            raise APIError(7, 'Could not decode address: ' + address + ' : ' + status)
        if addressVersionNumber < 2 or addressVersionNumber > 4:
            raise APIError(11, 'The address version number currently must be 2, 3 or 4. Others aren\'t supported. Check the address.')
        if streamNumber != 1:
            raise APIError(12, 'The stream number must be 1. Others aren\'t supported. Check the address.')

        return (status, addressVersionNumber, streamNumber, ripe)

    def _handle_request(self, method, params):
        if method == 'helloWorld':
            (a, b) = params
            return a + '-' + b
        elif method == 'add':
            (a, b) = params
            return a + b
        elif method == 'statusBar':
            message, = params
            shared.UISignalQueue.put(('updateStatusBar', message))
        elif method == 'listAddresses' or method == 'listAddresses2':
            data = '{"addresses":['
            configSections = shared.config.sections()
            for addressInKeysFile in configSections:
                if addressInKeysFile != 'bitmessagesettings':
                    status, addressVersionNumber, streamNumber, hash01 = decodeAddress(
                        addressInKeysFile)
                    if len(data) > 20:
                        data += ','
                    if shared.config.has_option(addressInKeysFile, 'chan'):
                        chan = shared.config.getboolean(addressInKeysFile, 'chan')
                    else:
                        chan = False
                    label = shared.config.get(addressInKeysFile, 'label')
                    if method == 'listAddresses2':
                        label = label.encode('base64')
                    data += json.dumps({'label': label, 'address': addressInKeysFile, 'stream':
                                        streamNumber, 'enabled': shared.config.getboolean(addressInKeysFile, 'enabled'), 'chan': chan}, indent=4, separators=(',', ': '))
            data += ']}'
            return data
        elif method == 'listAddressBookEntries' or method == 'listAddressbook': # the listAddressbook alias should be removed eventually.
            queryreturn = sqlQuery('''SELECT label, address from addressbook''')
            data = '{"addresses":['
            for row in queryreturn:
                label, address = row
                label = shared.fixPotentiallyInvalidUTF8Data(label)
                if len(data) > 20:
                    data += ','
                data += json.dumps({'label':label.encode('base64'), 'address': address}, indent=4, separators=(',', ': '))
            data += ']}'
            return data
        elif method == 'addAddressBookEntry' or method == 'addAddressbook': # the addAddressbook alias should be deleted eventually.
            if len(params) != 2:
                raise APIError(0, "I need label and address")
            address, label = params
            label = self._decode(label, "base64")
            address = addBMIfNotPresent(address)
            self._verifyAddress(address)
            queryreturn = sqlQuery("SELECT address FROM addressbook WHERE address=?", address)
            if queryreturn != []:
                raise APIError(16, 'You already have this address in your address book.')

            sqlExecute("INSERT INTO addressbook VALUES(?,?)", label, address)
            shared.UISignalQueue.put(('rerenderInboxFromLabels',''))
            shared.UISignalQueue.put(('rerenderSentToLabels',''))
            shared.UISignalQueue.put(('rerenderAddressBook',''))
            return "Added address %s to address book" % address
        elif method == 'deleteAddressBookEntry' or method == 'deleteAddressbook': # The deleteAddressbook alias should be deleted eventually.
            if len(params) != 1:
                raise APIError(0, "I need an address")
            address, = params
            address = addBMIfNotPresent(address)
            self._verifyAddress(address)
            sqlExecute('DELETE FROM addressbook WHERE address=?', address)
            shared.UISignalQueue.put(('rerenderInboxFromLabels',''))
            shared.UISignalQueue.put(('rerenderSentToLabels',''))
            shared.UISignalQueue.put(('rerenderAddressBook',''))
            return "Deleted address book entry for %s if it existed" % address
        elif method == 'createRandomAddress':
            if len(params) == 0:
                raise APIError(0, 'I need parameters!')
            elif len(params) == 1:
                label, = params
                eighteenByteRipe = False
                nonceTrialsPerByte = shared.config.get(
                    'bitmessagesettings', 'defaultnoncetrialsperbyte')
                payloadLengthExtraBytes = shared.config.get(
                    'bitmessagesettings', 'defaultpayloadlengthextrabytes')
            elif len(params) == 2:
                label, eighteenByteRipe = params
                nonceTrialsPerByte = shared.config.get(
                    'bitmessagesettings', 'defaultnoncetrialsperbyte')
                payloadLengthExtraBytes = shared.config.get(
                    'bitmessagesettings', 'defaultpayloadlengthextrabytes')
            elif len(params) == 3:
                label, eighteenByteRipe, totalDifficulty = params
                nonceTrialsPerByte = int(
                    shared.networkDefaultProofOfWorkNonceTrialsPerByte * totalDifficulty)
                payloadLengthExtraBytes = shared.config.get(
                    'bitmessagesettings', 'defaultpayloadlengthextrabytes')
            elif len(params) == 4:
                label, eighteenByteRipe, totalDifficulty, smallMessageDifficulty = params
                nonceTrialsPerByte = int(
                    shared.networkDefaultProofOfWorkNonceTrialsPerByte * totalDifficulty)
                payloadLengthExtraBytes = int(
                    shared.networkDefaultPayloadLengthExtraBytes * smallMessageDifficulty)
            else:
                raise APIError(0, 'Too many parameters!')
            label = self._decode(label, "base64")
            try:
                unicode(label, 'utf-8')
            except:
                raise APIError(17, 'Label is not valid UTF-8 data.')
            shared.apiAddressGeneratorReturnQueue.queue.clear()
            streamNumberForAddress = 1
            shared.addressGeneratorQueue.put((
                'createRandomAddress', 4, streamNumberForAddress, label, 1, "", eighteenByteRipe, nonceTrialsPerByte, payloadLengthExtraBytes))
            return shared.apiAddressGeneratorReturnQueue.get()
        elif method == 'createDeterministicAddresses':
            if len(params) == 0:
                raise APIError(0, 'I need parameters!')
            elif len(params) == 1:
                passphrase, = params
                numberOfAddresses = 1
                addressVersionNumber = 0
                streamNumber = 0
                eighteenByteRipe = False
                nonceTrialsPerByte = shared.config.get(
                    'bitmessagesettings', 'defaultnoncetrialsperbyte')
                payloadLengthExtraBytes = shared.config.get(
                    'bitmessagesettings', 'defaultpayloadlengthextrabytes')
            elif len(params) == 2:
                passphrase, numberOfAddresses = params
                addressVersionNumber = 0
                streamNumber = 0
                eighteenByteRipe = False
                nonceTrialsPerByte = shared.config.get(
                    'bitmessagesettings', 'defaultnoncetrialsperbyte')
                payloadLengthExtraBytes = shared.config.get(
                    'bitmessagesettings', 'defaultpayloadlengthextrabytes')
            elif len(params) == 3:
                passphrase, numberOfAddresses, addressVersionNumber = params
                streamNumber = 0
                eighteenByteRipe = False
                nonceTrialsPerByte = shared.config.get(
                    'bitmessagesettings', 'defaultnoncetrialsperbyte')
                payloadLengthExtraBytes = shared.config.get(
                    'bitmessagesettings', 'defaultpayloadlengthextrabytes')
            elif len(params) == 4:
                passphrase, numberOfAddresses, addressVersionNumber, streamNumber = params
                eighteenByteRipe = False
                nonceTrialsPerByte = shared.config.get(
                    'bitmessagesettings', 'defaultnoncetrialsperbyte')
                payloadLengthExtraBytes = shared.config.get(
                    'bitmessagesettings', 'defaultpayloadlengthextrabytes')
            elif len(params) == 5:
                passphrase, numberOfAddresses, addressVersionNumber, streamNumber, eighteenByteRipe = params
                nonceTrialsPerByte = shared.config.get(
                    'bitmessagesettings', 'defaultnoncetrialsperbyte')
                payloadLengthExtraBytes = shared.config.get(
                    'bitmessagesettings', 'defaultpayloadlengthextrabytes')
            elif len(params) == 6:
                passphrase, numberOfAddresses, addressVersionNumber, streamNumber, eighteenByteRipe, totalDifficulty = params
                nonceTrialsPerByte = int(
                    shared.networkDefaultProofOfWorkNonceTrialsPerByte * totalDifficulty)
                payloadLengthExtraBytes = shared.config.get(
                    'bitmessagesettings', 'defaultpayloadlengthextrabytes')
            elif len(params) == 7:
                passphrase, numberOfAddresses, addressVersionNumber, streamNumber, eighteenByteRipe, totalDifficulty, smallMessageDifficulty = params
                nonceTrialsPerByte = int(
                    shared.networkDefaultProofOfWorkNonceTrialsPerByte * totalDifficulty)
                payloadLengthExtraBytes = int(
                    shared.networkDefaultPayloadLengthExtraBytes * smallMessageDifficulty)
            else:
                raise APIError(0, 'Too many parameters!')
            if len(passphrase) == 0:
                raise APIError(1, 'The specified passphrase is blank.')
            if not isinstance(eighteenByteRipe, bool):
                raise APIError(23, 'Bool expected in eighteenByteRipe, saw %s instead' % type(eighteenByteRipe))
            passphrase = self._decode(passphrase, "base64")
            if addressVersionNumber == 0:  # 0 means "just use the proper addressVersionNumber"
                addressVersionNumber = 4
            if addressVersionNumber != 3 and addressVersionNumber != 4:
                raise APIError(2,'The address version number currently must be 3, 4, or 0 (which means auto-select). ' + addressVersionNumber + ' isn\'t supported.')
            if streamNumber == 0:  # 0 means "just use the most available stream"
                streamNumber = 1
            if streamNumber != 1:
                raise APIError(3,'The stream number must be 1 (or 0 which means auto-select). Others aren\'t supported.')
            if numberOfAddresses == 0:
                raise APIError(4, 'Why would you ask me to generate 0 addresses for you?')
            if numberOfAddresses > 999:
                raise APIError(5, 'You have (accidentally?) specified too many addresses to make. Maximum 999. This check only exists to prevent mischief; if you really want to create more addresses than this, contact the Bitmessage developers and we can modify the check or you can do it yourself by searching the source code for this message.')
            shared.apiAddressGeneratorReturnQueue.queue.clear()
            logger.debug('Requesting that the addressGenerator create %s addresses.', numberOfAddresses)
            shared.addressGeneratorQueue.put(
                ('createDeterministicAddresses', addressVersionNumber, streamNumber,
                 'unused API address', numberOfAddresses, passphrase, eighteenByteRipe, nonceTrialsPerByte, payloadLengthExtraBytes))
            data = '{"addresses":['
            queueReturn = shared.apiAddressGeneratorReturnQueue.get()
            for item in queueReturn:
                if len(data) > 20:
                    data += ','
                data += "\"" + item + "\""
            data += ']}'
            return data
        elif method == 'getDeterministicAddress':
            if len(params) != 3:
                raise APIError(0, 'I need exactly 3 parameters.')
            passphrase, addressVersionNumber, streamNumber = params
            numberOfAddresses = 1
            eighteenByteRipe = False
            if len(passphrase) == 0:
                raise APIError(1, 'The specified passphrase is blank.')
            passphrase = self._decode(passphrase, "base64")
            if addressVersionNumber != 3 and addressVersionNumber != 4:
                raise APIError(2, 'The address version number currently must be 3 or 4. ' + addressVersionNumber + ' isn\'t supported.')
            if streamNumber != 1:
                raise APIError(3, ' The stream number must be 1. Others aren\'t supported.')
            shared.apiAddressGeneratorReturnQueue.queue.clear()
            logger.debug('Requesting that the addressGenerator create %s addresses.', numberOfAddresses)
            shared.addressGeneratorQueue.put(
                ('getDeterministicAddress', addressVersionNumber,
                 streamNumber, 'unused API address', numberOfAddresses, passphrase, eighteenByteRipe))
            return shared.apiAddressGeneratorReturnQueue.get()

        elif method == 'createChan':
            if len(params) == 0:
                raise APIError(0, 'I need parameters.')
            elif len(params) == 1:
                passphrase, = params
            passphrase = self._decode(passphrase, "base64")
            if len(passphrase) == 0:
                raise APIError(1, 'The specified passphrase is blank.')
            # It would be nice to make the label the passphrase but it is
            # possible that the passphrase contains non-utf-8 characters.
            try:
                unicode(passphrase, 'utf-8')
                label = str_chan + ' ' + passphrase
            except:
                label = str_chan + ' ' + repr(passphrase)

            addressVersionNumber = 4
            streamNumber = 1
            shared.apiAddressGeneratorReturnQueue.queue.clear()
            logger.debug('Requesting that the addressGenerator create chan %s.', passphrase)
            shared.addressGeneratorQueue.put(('createChan', addressVersionNumber, streamNumber, label, passphrase))
            queueReturn = shared.apiAddressGeneratorReturnQueue.get()
            if len(queueReturn) == 0:
                raise APIError(24, 'Chan address is already present.')
            address = queueReturn[0]
            return address
        elif method == 'joinChan':
            if len(params) < 2:
                raise APIError(0, 'I need two parameters.')
            elif len(params) == 2:
                passphrase, suppliedAddress= params
            passphrase = self._decode(passphrase, "base64")
            if len(passphrase) == 0:
                raise APIError(1, 'The specified passphrase is blank.')
            # It would be nice to make the label the passphrase but it is
            # possible that the passphrase contains non-utf-8 characters.
            try:
                unicode(passphrase, 'utf-8')
                label = str_chan + ' ' + passphrase
            except:
                label = str_chan + ' ' + repr(passphrase)

            status, addressVersionNumber, streamNumber, toRipe = self._verifyAddress(suppliedAddress)
            suppliedAddress = addBMIfNotPresent(suppliedAddress)
            shared.apiAddressGeneratorReturnQueue.queue.clear()
            shared.addressGeneratorQueue.put(('joinChan', suppliedAddress, label, passphrase))
            addressGeneratorReturnValue = shared.apiAddressGeneratorReturnQueue.get()

            if addressGeneratorReturnValue == 'chan name does not match address':
                raise APIError(18, 'Chan name does not match address.')
            if len(addressGeneratorReturnValue) == 0:
                raise APIError(24, 'Chan address is already present.')
            #TODO: this variable is not used to anything
            createdAddress = addressGeneratorReturnValue[0] # in case we ever want it for anything.
            return "success"
        elif method == 'leaveChan':
            if len(params) == 0:
                raise APIError(0, 'I need parameters.')
            elif len(params) == 1:
                address, = params
            status, addressVersionNumber, streamNumber, toRipe = self._verifyAddress(address)
            address = addBMIfNotPresent(address)
            if not shared.config.has_section(address):
                raise APIError(13, 'Could not find this address in your keys.dat file.')
            if not shared.safeConfigGetBoolean(address, 'chan'):
                raise APIError(25, 'Specified address is not a chan address. Use deleteAddress API call instead.')
            shared.config.remove_section(address)
            with open(shared.appdata + 'keys.dat', 'wb') as configfile:
                shared.config.write(configfile)
            return 'success'

        elif method == 'deleteAddress':
            if len(params) == 0:
                raise APIError(0, 'I need parameters.')
            elif len(params) == 1:
                address, = params
            status, addressVersionNumber, streamNumber, toRipe = self._verifyAddress(address)
            address = addBMIfNotPresent(address)
            if not shared.config.has_section(address):
                raise APIError(13, 'Could not find this address in your keys.dat file.')
            shared.config.remove_section(address)
            with open(shared.appdata + 'keys.dat', 'wb') as configfile:
                shared.config.write(configfile)
            shared.UISignalQueue.put(('rerenderInboxFromLabels',''))
            shared.UISignalQueue.put(('rerenderSentToLabels',''))
            shared.reloadMyAddressHashes()
            return 'success'

        elif method == 'getAllInboxMessages':
            queryreturn = sqlQuery(
                '''SELECT msgid, toaddress, fromaddress, subject, received, message, encodingtype, read FROM inbox where folder='inbox' ORDER BY received''')
            data = '{"inboxMessages":['
            for row in queryreturn:
                msgid, toAddress, fromAddress, subject, received, message, encodingtype, read = row
                subject = shared.fixPotentiallyInvalidUTF8Data(subject)
                message = shared.fixPotentiallyInvalidUTF8Data(message)
                if len(data) > 25:
                    data += ','
                data += json.dumps({'msgid': msgid.encode('hex'), 'toAddress': toAddress, 'fromAddress': fromAddress, 'subject': subject.encode(
                    'base64'), 'message': message.encode('base64'), 'encodingType': encodingtype, 'receivedTime': received, 'read': read}, indent=4, separators=(',', ': '))
            data += ']}'
            return data
        elif method == 'getAllInboxMessageIds' or method == 'getAllInboxMessageIDs':
            queryreturn = sqlQuery(
                '''SELECT msgid FROM inbox where folder='inbox' ORDER BY received''')
            data = '{"inboxMessageIds":['
            for row in queryreturn:
                msgid = row[0]
                if len(data) > 25:
                    data += ','
                data += json.dumps({'msgid': msgid.encode('hex')}, indent=4, separators=(',', ': '))
            data += ']}'
            return data
        elif method == 'getInboxMessageById' or method == 'getInboxMessageByID':
            if len(params) == 0:
                raise APIError(0, 'I need parameters!')
            elif len(params) == 1:
                msgid = self._decode(params[0], "hex")
            elif len(params) >= 2:
                msgid = self._decode(params[0], "hex")
                readStatus = params[1]
                if not isinstance(readStatus, bool):
                    raise APIError(23, 'Bool expected in readStatus, saw %s instead.' % type(readStatus))
                queryreturn = sqlQuery('''SELECT read FROM inbox WHERE msgid=?''', msgid)
                # UPDATE is slow, only update if status is different
                if queryreturn != [] and (queryreturn[0][0] == 1) != readStatus:
                    sqlExecute('''UPDATE inbox set read = ? WHERE msgid=?''', readStatus, msgid)
                    shared.UISignalQueue.put(('changedInboxUnread', None))
            queryreturn = sqlQuery('''SELECT msgid, toaddress, fromaddress, subject, received, message, encodingtype, read FROM inbox WHERE msgid=?''', msgid)
            data = '{"inboxMessage":['
            for row in queryreturn:
                msgid, toAddress, fromAddress, subject, received, message, encodingtype, read = row
                subject = shared.fixPotentiallyInvalidUTF8Data(subject)
                message = shared.fixPotentiallyInvalidUTF8Data(message)
                data += json.dumps({'msgid':msgid.encode('hex'), 'toAddress':toAddress, 'fromAddress':fromAddress, 'subject':subject.encode('base64'), 'message':message.encode('base64'), 'encodingType':encodingtype, 'receivedTime':received, 'read': read}, indent=4, separators=(',', ': '))
                data += ']}'
                return data
        elif method == 'getAllSentMessages':
            queryreturn = sqlQuery('''SELECT msgid, toaddress, fromaddress, subject, lastactiontime, message, encodingtype, status, ackdata FROM sent where folder='sent' ORDER BY lastactiontime''')
            data = '{"sentMessages":['
            for row in queryreturn:
                msgid, toAddress, fromAddress, subject, lastactiontime, message, encodingtype, status, ackdata = row
                subject = shared.fixPotentiallyInvalidUTF8Data(subject)
                message = shared.fixPotentiallyInvalidUTF8Data(message)
                if len(data) > 25:
                    data += ','
                data += json.dumps({'msgid':msgid.encode('hex'), 'toAddress':toAddress, 'fromAddress':fromAddress, 'subject':subject.encode('base64'), 'message':message.encode('base64'), 'encodingType':encodingtype, 'lastActionTime':lastactiontime, 'status':status, 'ackData':ackdata.encode('hex')}, indent=4, separators=(',', ': '))
            data += ']}'
            return data
        elif method == 'getAllSentMessageIds' or method == 'getAllSentMessageIDs':
            queryreturn = sqlQuery('''SELECT msgid FROM sent where folder='sent' ORDER BY lastactiontime''')
            data = '{"sentMessageIds":['
            for row in queryreturn:
                msgid = row[0]
                if len(data) > 25:
                    data += ','
                data += json.dumps({'msgid':msgid.encode('hex')}, indent=4, separators=(',', ': '))
            data += ']}'
            return data
        elif method == 'getInboxMessagesByReceiver' or method == 'getInboxMessagesByAddress': #after some time getInboxMessagesByAddress should be removed
            if len(params) == 0:
                raise APIError(0, 'I need parameters!')
            toAddress = params[0]
            queryreturn = sqlQuery('''SELECT msgid, toaddress, fromaddress, subject, received, message, encodingtype FROM inbox WHERE folder='inbox' AND toAddress=?''', toAddress)
            data = '{"inboxMessages":['
            for row in queryreturn:
                msgid, toAddress, fromAddress, subject, received, message, encodingtype = row
                subject = shared.fixPotentiallyInvalidUTF8Data(subject)
                message = shared.fixPotentiallyInvalidUTF8Data(message)
                if len(data) > 25:
                    data += ','
                data += json.dumps({'msgid':msgid.encode('hex'), 'toAddress':toAddress, 'fromAddress':fromAddress, 'subject':subject.encode('base64'), 'message':message.encode('base64'), 'encodingType':encodingtype, 'receivedTime':received}, indent=4, separators=(',', ': '))
            data += ']}'
            return data
        elif method == 'getSentMessageById' or method == 'getSentMessageByID':
            if len(params) == 0:
                raise APIError(0, 'I need parameters!')
            msgid = self._decode(params[0], "hex")
            queryreturn = sqlQuery('''SELECT msgid, toaddress, fromaddress, subject, lastactiontime, message, encodingtype, status, ackdata FROM sent WHERE msgid=?''', msgid)
            data = '{"sentMessage":['
            for row in queryreturn:
                msgid, toAddress, fromAddress, subject, lastactiontime, message, encodingtype, status, ackdata = row
                subject = shared.fixPotentiallyInvalidUTF8Data(subject)
                message = shared.fixPotentiallyInvalidUTF8Data(message)
                data += json.dumps({'msgid':msgid.encode('hex'), 'toAddress':toAddress, 'fromAddress':fromAddress, 'subject':subject.encode('base64'), 'message':message.encode('base64'), 'encodingType':encodingtype, 'lastActionTime':lastactiontime, 'status':status, 'ackData':ackdata.encode('hex')}, indent=4, separators=(',', ': '))
                data += ']}'
                return data
        elif method == 'getSentMessagesByAddress' or method == 'getSentMessagesBySender':
            if len(params) == 0:
                raise APIError(0, 'I need parameters!')
            fromAddress = params[0]
            queryreturn = sqlQuery('''SELECT msgid, toaddress, fromaddress, subject, lastactiontime, message, encodingtype, status, ackdata FROM sent WHERE folder='sent' AND fromAddress=? ORDER BY lastactiontime''',
                                   fromAddress)
            data = '{"sentMessages":['
            for row in queryreturn:
                msgid, toAddress, fromAddress, subject, lastactiontime, message, encodingtype, status, ackdata = row
                subject = shared.fixPotentiallyInvalidUTF8Data(subject)
                message = shared.fixPotentiallyInvalidUTF8Data(message)
                if len(data) > 25:
                    data += ','
                data += json.dumps({'msgid':msgid.encode('hex'), 'toAddress':toAddress, 'fromAddress':fromAddress, 'subject':subject.encode('base64'), 'message':message.encode('base64'), 'encodingType':encodingtype, 'lastActionTime':lastactiontime, 'status':status, 'ackData':ackdata.encode('hex')}, indent=4, separators=(',', ': '))
            data += ']}'
            return data
        elif method == 'getSentMessageByAckData':
            if len(params) == 0:
                raise APIError(0, 'I need parameters!')
            ackData = self._decode(params[0], "hex")
            queryreturn = sqlQuery('''SELECT msgid, toaddress, fromaddress, subject, lastactiontime, message, encodingtype, status, ackdata FROM sent WHERE ackdata=?''',
                                   ackData)
            data = '{"sentMessage":['
            for row in queryreturn:
                msgid, toAddress, fromAddress, subject, lastactiontime, message, encodingtype, status, ackdata = row
                subject = shared.fixPotentiallyInvalidUTF8Data(subject)
                message = shared.fixPotentiallyInvalidUTF8Data(message)
                data += json.dumps({'msgid':msgid.encode('hex'), 'toAddress':toAddress, 'fromAddress':fromAddress, 'subject':subject.encode('base64'), 'message':message.encode('base64'), 'encodingType':encodingtype, 'lastActionTime':lastactiontime, 'status':status, 'ackData':ackdata.encode('hex')}, indent=4, separators=(',', ': '))
            data += ']}'
            return data
        elif method == 'trashMessage':
            if len(params) == 0:
                raise APIError(0, 'I need parameters!')
            msgid = self._decode(params[0], "hex")

            # Trash if in inbox table
            helper_inbox.trash(msgid)
            # Trash if in sent table
            sqlExecute('''UPDATE sent SET folder='trash' WHERE msgid=?''', msgid)
            return 'Trashed message (assuming message existed).'
        elif method == 'trashInboxMessage':
            if len(params) == 0:
                raise APIError(0, 'I need parameters!')
            msgid = self._decode(params[0], "hex")
            helper_inbox.trash(msgid)
            return 'Trashed inbox message (assuming message existed).'
        elif method == 'trashSentMessage':
            if len(params) == 0:
                raise APIError(0, 'I need parameters!')
            msgid = self._decode(params[0], "hex")
            sqlExecute('''UPDATE sent SET folder='trash' WHERE msgid=?''', msgid)
            return 'Trashed sent message (assuming message existed).'
        elif method == 'trashSentMessageByAckData':
            # This API method should only be used when msgid is not available
            if len(params) == 0:
                raise APIError(0, 'I need parameters!')
            ackdata = self._decode(params[0], "hex")
            sqlExecute('''UPDATE sent SET folder='trash' WHERE ackdata=?''',
                       ackdata)
            return 'Trashed sent message (assuming message existed).'
        elif method == 'sendMessage':
            if len(params) == 0:
                raise APIError(0, 'I need parameters!')
            elif len(params) == 4:
                toAddress, fromAddress, subject, message = params
                encodingType = 2
            elif len(params) == 5:
                toAddress, fromAddress, subject, message, encodingType = params
            if encodingType != 2:
                raise APIError(6, 'The encoding type must be 2 because that is the only one this program currently supports.')
            subject = self._decode(subject, "base64")
            message = self._decode(message, "base64")
            toAddress = addBMIfNotPresent(toAddress)
            fromAddress = addBMIfNotPresent(fromAddress)
            status, addressVersionNumber, streamNumber, toRipe = self._verifyAddress(toAddress)
            self._verifyAddress(fromAddress)
            try:
                fromAddressEnabled = shared.config.getboolean(
                    fromAddress, 'enabled')
            except:
                raise APIError(13, 'Could not find your fromAddress in the keys.dat file.')
            if not fromAddressEnabled:
                raise APIError(14, 'Your fromAddress is disabled. Cannot send.')

            ackdata = OpenSSL.rand(32)

            t = ('', toAddress, toRipe, fromAddress, subject, message, ackdata, int(
                time.time()), 'msgqueued', 1, 1, 'sent', 2)
            helper_sent.insert(t)

            toLabel = ''
            queryreturn = sqlQuery('''select label from addressbook where address=?''', toAddress)
            if queryreturn != []:
                for row in queryreturn:
                    toLabel, = row
            # apiSignalQueue.put(('displayNewSentMessage',(toAddress,toLabel,fromAddress,subject,message,ackdata)))
            shared.UISignalQueue.put(('displayNewSentMessage', (
                toAddress, toLabel, fromAddress, subject, message, ackdata)))

            shared.workerQueue.put(('sendmessage', toAddress))

            return ackdata.encode('hex')

        elif method == 'sendBroadcast':
            if len(params) == 0:
                raise APIError(0, 'I need parameters!')
            if len(params) == 3:
                fromAddress, subject, message = params
                encodingType = 2
            elif len(params) == 4:
                fromAddress, subject, message, encodingType = params
            if encodingType != 2:
                raise APIError(6, 'The encoding type must be 2 because that is the only one this program currently supports.')
            subject = self._decode(subject, "base64")
            message = self._decode(message, "base64")

            fromAddress = addBMIfNotPresent(fromAddress)
            self._verifyAddress(fromAddress)
            try:
                fromAddressEnabled = shared.config.getboolean(
                    fromAddress, 'enabled')
            except:
                raise APIError(13, 'could not find your fromAddress in the keys.dat file.')
            ackdata = OpenSSL.rand(32)
            toAddress = '[Broadcast subscribers]'
            ripe = ''


            t = ('', toAddress, ripe, fromAddress, subject, message, ackdata, int(
                time.time()), 'broadcastqueued', 1, 1, 'sent', 2)
            helper_sent.insert(t)

            toLabel = '[Broadcast subscribers]'
            shared.UISignalQueue.put(('displayNewSentMessage', (
                toAddress, toLabel, fromAddress, subject, message, ackdata)))
            shared.workerQueue.put(('sendbroadcast', ''))

            return ackdata.encode('hex')
        elif method == 'getStatus':
            if len(params) != 1:
                raise APIError(0, 'I need one parameter!')
            ackdata, = params
            if len(ackdata) != 64:
                raise APIError(15, 'The length of ackData should be 32 bytes (encoded in hex thus 64 characters).')
            ackdata = self._decode(ackdata, "hex")
            queryreturn = sqlQuery(
                '''SELECT status FROM sent where ackdata=?''',
                ackdata)
            if queryreturn == []:
                return 'notfound'
            for row in queryreturn:
                status, = row
                return status
        elif method == 'addSubscription':
            if len(params) == 0:
                raise APIError(0, 'I need parameters!')
            if len(params) == 1:
                address, = params
                label = ''
            if len(params) == 2:
                address, label = params
                label = self._decode(label, "base64")
                try:
                    unicode(label, 'utf-8')
                except:
                    raise APIError(17, 'Label is not valid UTF-8 data.')
            if len(params) > 2:
                raise APIError(0, 'I need either 1 or 2 parameters!')
            address = addBMIfNotPresent(address)
            self._verifyAddress(address)
            # First we must check to see if the address is already in the
            # subscriptions list.
            queryreturn = sqlQuery('''select * from subscriptions where address=?''', address)
            if queryreturn != []:
                raise APIError(16, 'You are already subscribed to that address.')
            sqlExecute('''INSERT INTO subscriptions VALUES (?,?,?)''',label, address, True)
            shared.reloadBroadcastSendersForWhichImWatching()
            shared.UISignalQueue.put(('rerenderInboxFromLabels', ''))
            shared.UISignalQueue.put(('rerenderSubscriptions', ''))
            return 'Added subscription.'

        elif method == 'deleteSubscription':
            if len(params) != 1:
                raise APIError(0, 'I need 1 parameter!')
            address, = params
            address = addBMIfNotPresent(address)
            sqlExecute('''DELETE FROM subscriptions WHERE address=?''', address)
            shared.reloadBroadcastSendersForWhichImWatching()
            shared.UISignalQueue.put(('rerenderInboxFromLabels', ''))
            shared.UISignalQueue.put(('rerenderSubscriptions', ''))
            return 'Deleted subscription if it existed.'
        elif method == 'listSubscriptions':
            queryreturn = sqlQuery('''SELECT label, address, enabled FROM subscriptions''')
            data = '{"subscriptions":['
            for row in queryreturn:
                label, address, enabled = row
                label = shared.fixPotentiallyInvalidUTF8Data(label)
                if len(data) > 20:
                    data += ','
                data += json.dumps({'label':label.encode('base64'), 'address': address, 'enabled': enabled == 1}, indent=4, separators=(',',': '))
            data += ']}'
            return data
        elif method == 'disseminatePreEncryptedMsg':
            # The device issuing this command to PyBitmessage supplies a msg object that has
            # already been encrypted but which still needs the POW to be done. PyBitmessage
            # accepts this msg object and sends it out to the rest of the Bitmessage network
            # as if it had generated the message itself. Please do not yet add this to the
            # api doc.
            if len(params) != 3:
                raise APIError(0, 'I need 3 parameter!')
            encryptedPayload, requiredAverageProofOfWorkNonceTrialsPerByte, requiredPayloadLengthExtraBytes = params
            encryptedPayload = self._decode(encryptedPayload, "hex")
            # Let us do the POW and attach it to the front
            target = 2**64 / ((len(encryptedPayload)+requiredPayloadLengthExtraBytes+8) * requiredAverageProofOfWorkNonceTrialsPerByte)
            with shared.printLock:
                print '(For msg message via API) Doing proof of work. Total required difficulty:', float(requiredAverageProofOfWorkNonceTrialsPerByte) / shared.networkDefaultProofOfWorkNonceTrialsPerByte, 'Required small message difficulty:', float(requiredPayloadLengthExtraBytes) / shared.networkDefaultPayloadLengthExtraBytes
            powStartTime = time.time()
            initialHash = hashlib.sha512(encryptedPayload).digest()
            trialValue, nonce = proofofwork.run(target, initialHash)
            with shared.printLock:
                print '(For msg message via API) Found proof of work', trialValue, 'Nonce:', nonce
                try:
                    print 'POW took', int(time.time() - powStartTime), 'seconds.', nonce / (time.time() - powStartTime), 'nonce trials per second.'
                except:
                    pass
            encryptedPayload = pack('>Q', nonce) + encryptedPayload
            toStreamNumber = decodeVarint(encryptedPayload[16:26])[0]
            inventoryHash = calculateInventoryHash(encryptedPayload)
            objectType = 'msg'
            shared.inventory[inventoryHash] = (
                objectType, toStreamNumber, encryptedPayload, int(time.time()),'')
            shared.inventorySets[toStreamNumber].add(inventoryHash)
            with shared.printLock:
                print 'Broadcasting inv for msg(API disseminatePreEncryptedMsg command):', inventoryHash.encode('hex')
            shared.broadcastToSendDataQueues((
                toStreamNumber, 'advertiseobject', inventoryHash))
        elif method == 'disseminatePubkey':
            # The device issuing this command to PyBitmessage supplies a pubkey object to be
            # disseminated to the rest of the Bitmessage network. PyBitmessage accepts this
            # pubkey object and sends it out to the rest of the Bitmessage network as if it
            # had generated the pubkey object itself. Please do not yet add this to the api
            # doc.
            if len(params) != 1:
                raise APIError(0, 'I need 1 parameter!')
            payload, = params
            payload = self._decode(payload, "hex")

            # Let us do the POW
            target = 2 ** 64 / ((len(payload) + shared.networkDefaultPayloadLengthExtraBytes +
                                 8) * shared.networkDefaultProofOfWorkNonceTrialsPerByte)
            print '(For pubkey message via API) Doing proof of work...'
            initialHash = hashlib.sha512(payload).digest()
            trialValue, nonce = proofofwork.run(target, initialHash)
            print '(For pubkey message via API) Found proof of work', trialValue, 'Nonce:', nonce
            payload = pack('>Q', nonce) + payload

            pubkeyReadPosition = 8 # bypass the nonce
            if payload[pubkeyReadPosition:pubkeyReadPosition+4] == '\x00\x00\x00\x00': # if this pubkey uses 8 byte time
                pubkeyReadPosition += 8
            else:
                pubkeyReadPosition += 4
            addressVersion, addressVersionLength = decodeVarint(payload[pubkeyReadPosition:pubkeyReadPosition+10])
            pubkeyReadPosition += addressVersionLength
            pubkeyStreamNumber = decodeVarint(payload[pubkeyReadPosition:pubkeyReadPosition+10])[0]
            inventoryHash = calculateInventoryHash(payload)
            objectType = 'pubkey'
                        #todo: support v4 pubkeys
            shared.inventory[inventoryHash] = (
                objectType, pubkeyStreamNumber, payload, int(time.time()),'')
            shared.inventorySets[pubkeyStreamNumber].add(inventoryHash)
            with shared.printLock:
                print 'broadcasting inv within API command disseminatePubkey with hash:', inventoryHash.encode('hex')
            shared.broadcastToSendDataQueues((
                streamNumber, 'advertiseobject', inventoryHash))
        elif method == 'getMessageDataByDestinationHash' or method == 'getMessageDataByDestinationTag':
            # Method will eventually be used by a particular Android app to
            # select relevant messages. Do not yet add this to the api
            # doc.

            if len(params) != 1:
                raise APIError(0, 'I need 1 parameter!')
            requestedHash, = params
            if len(requestedHash) != 32:
                raise APIError(19, 'The length of hash should be 32 bytes (encoded in hex thus 64 characters).')
            requestedHash = self._decode(requestedHash, "hex")

            # This is not a particularly commonly used API function. Before we
            # use it we'll need to fill out a field in our inventory database
            # which is blank by default (first20bytesofencryptedmessage).
            queryreturn = sqlQuery(
                '''SELECT hash, payload FROM inventory WHERE tag = '' and objecttype = 'msg' ; ''')
            with SqlBulkExecute() as sql:
                for row in queryreturn:
                    hash01, payload = row
                    readPosition = 16 # Nonce length + time length
                    readPosition += decodeVarint(payload[readPosition:readPosition+10])[1] # Stream Number length
                    t = (payload[readPosition:readPosition+32],hash01)
                    sql.execute('''UPDATE inventory SET tag=? WHERE hash=?; ''', *t)

            queryreturn = sqlQuery('''SELECT payload FROM inventory WHERE tag = ?''',
                                   requestedHash)
            data = '{"receivedMessageDatas":['
            for row in queryreturn:
                payload, = row
                if len(data) > 25:
                    data += ','
                data += json.dumps({'data':payload.encode('hex')}, indent=4, separators=(',', ': '))
            data += ']}'
            return data
        elif method == 'getPubkeyByHash':
            # Method will eventually be used by a particular Android app to
            # retrieve pubkeys. Please do not yet add this to the api docs.
            if len(params) != 1:
                raise APIError(0, 'I need 1 parameter!')
            requestedHash, = params
            if len(requestedHash) != 40:
                raise APIError(19, 'The length of hash should be 20 bytes (encoded in hex thus 40 characters).')
            requestedHash = self._decode(requestedHash, "hex")
            queryreturn = sqlQuery('''SELECT transmitdata FROM pubkeys WHERE hash = ? ; ''', requestedHash)
            data = '{"pubkey":['
            for row in queryreturn:
                transmitdata, = row
                data += json.dumps({'data':transmitdata.encode('hex')}, indent=4, separators=(',', ': '))
            data += ']}'
            return data
        elif method == 'clientStatus':
            if len(shared.connectedHostsList) == 0:
                networkStatus = 'notConnected'
            elif len(shared.connectedHostsList) > 0 and not shared.clientHasReceivedIncomingConnections:
                networkStatus = 'connectedButHaveNotReceivedIncomingConnections'
            else:
                networkStatus = 'connectedAndReceivingIncomingConnections'
            return json.dumps({'networkConnections':len(shared.connectedHostsList),'numberOfMessagesProcessed':shared.numberOfMessagesProcessed, 'numberOfBroadcastsProcessed':shared.numberOfBroadcastsProcessed, 'numberOfPubkeysProcessed':shared.numberOfPubkeysProcessed, 'networkStatus':networkStatus, 'softwareName':'PyBitmessage','softwareVersion':shared.softwareVersion}, indent=4, separators=(',', ': '))
        elif method == 'decodeAddress':
            # Return a meaningful decoding of an address.
            if len(params) != 1:
                raise APIError(0, 'I need 1 parameter!')
            address, = params
            status, addressVersion, streamNumber, ripe = decodeAddress(address)
            return json.dumps({'status':status, 'addressVersion':addressVersion,
                               'streamNumber':streamNumber, 'ripe':ripe.encode('base64')}, indent=4,
                              separators=(',', ': '))
        else:
            raise APIError(20, 'Invalid method: %s' % method)

    def _dispatch(self, method, params):
        self.cookies = []

        validuser = self.APIAuthenticateClient()
        if not validuser:
            time.sleep(2)
            return "RPC Username or password incorrect or HTTP header lacks authentication at all."

        try:
            return self._handle_request(method, params)
        except APIError as e:
            return str(e)
        except Exception as e:
            logger.exception(e)
            return "API Error 0021: Unexpected API Failure - %s" % str(e)


########NEW FILE########
__FILENAME__ = api_client
# This is an example of how to connect to and use the Bitmessage API.
# See https://bitmessage.org/wiki/API_Reference

import xmlrpclib
import json
import time

api = xmlrpclib.ServerProxy("http://bradley:password@localhost:8442/")

print 'Let\'s test the API first.'
inputstr1 = "hello"
inputstr2 = "world"
print api.helloWorld(inputstr1, inputstr2)
print api.add(2,3)

print 'Let\'s set the status bar message.'
print api.statusBar("new status bar message")

print 'Let\'s list our addresses:'
print api.listAddresses()

print 'Let\'s list our address again, but this time let\'s parse the json data into a Python data structure:'
jsonAddresses = json.loads(api.listAddresses())
print jsonAddresses
print 'Now that we have our address data in a nice Python data structure, let\'s look at the first address (index 0) and print its label:'
print jsonAddresses['addresses'][0]['label']

print 'Uncomment the next two lines to create a new random address with a slightly higher difficulty setting than normal.'
#addressLabel = 'new address label'.encode('base64')
#print api.createRandomAddress(addressLabel,False,1.05,1.1111)

print 'Uncomment these next four lines to create new deterministic addresses.'
#passphrase = 'asdfasdfqwser'.encode('base64')
#jsonDeterministicAddresses = api.createDeterministicAddresses(passphrase, 2, 4, 1, False)
#print jsonDeterministicAddresses
#print json.loads(jsonDeterministicAddresses)

#print 'Uncomment this next line to print the first deterministic address that would be generated with the given passphrase. This will Not add it to the Bitmessage interface or the keys.dat file.'
#print api.getDeterministicAddress('asdfasdfqwser'.encode('base64'),4,1)

#print 'Uncomment this line to subscribe to an address. (You must use your own address, this one is invalid).'
#print api.addSubscription('2D94G5d8yp237GGqAheoecBYpdehdT3dha','test sub'.encode('base64'))

#print 'Uncomment this line to unsubscribe from an address.'
#print api.deleteSubscription('2D94G5d8yp237GGqAheoecBYpdehdT3dha')

print 'Let\'s now print all of our inbox messages:'
print api.getAllInboxMessages()
inboxMessages = json.loads(api.getAllInboxMessages())
print inboxMessages

print 'Uncomment this next line to decode the actual message data in the first message:'
#print inboxMessages['inboxMessages'][0]['message'].decode('base64')

print 'Uncomment this next line in the code to delete a message'
#print api.trashMessage('584e5826947242a82cb883c8b39ac4a14959f14c228c0fbe6399f73e2cba5b59')

print 'Uncomment these lines to send a message. The example addresses are invalid; you will have to put your own in.'
#subject = 'subject!'.encode('base64')
#message = 'Hello, this is the message'.encode('base64')
#ackData = api.sendMessage('BM-Gtsm7PUabZecs3qTeXbNPmqx3xtHCSXF', 'BM-2DCutnUZG16WiW3mdAm66jJUSCUv88xLgS', subject,message)
#print 'The ackData is:', ackData
#while True:
#    time.sleep(2)
#    print 'Current status:', api.getStatus(ackData)

print 'Uncomment these lines to send a broadcast. The example address is invalid; you will have to put your own in.'
#subject = 'subject within broadcast'.encode('base64')
#message = 'Hello, this is the message within a broadcast.'.encode('base64')
#print api.sendBroadcast('BM-onf6V1RELPgeNN6xw9yhpAiNiRexSRD4e', subject,message)

########NEW FILE########
__FILENAME__ = bitmessagemain
#!/usr/bin/env python
# Copyright (c) 2012 Jonathan Warren
# Copyright (c) 2012 The Bitmessage developers
# Distributed under the MIT/X11 software license. See the accompanying
# file COPYING or http://www.opensource.org/licenses/mit-license.php.

# Right now, PyBitmessage only support connecting to stream 1. It doesn't
# yet contain logic to expand into further streams.

# The software version variable is now held in shared.py

import signal  # Used to capture a Ctrl-C keypress so that Bitmessage can shutdown gracefully.
# The next 3 are used for the API
import singleton
import os
import socket
import ctypes
from struct import pack

from SimpleXMLRPCServer import SimpleXMLRPCServer
from api import MySimpleXMLRPCRequestHandler
from helper_startup import isOurOperatingSystemLimitedToHavingVeryFewHalfOpenConnections

import shared
from helper_sql import sqlQuery
import threading

# Classes
#from helper_sql import *
#from class_sqlThread import *
from class_sqlThread import sqlThread
from class_singleCleaner import singleCleaner
#from class_singleWorker import *
from class_objectProcessor import objectProcessor
from class_outgoingSynSender import outgoingSynSender
from class_singleListener import singleListener
from class_singleWorker import singleWorker
#from class_addressGenerator import *
from class_addressGenerator import addressGenerator
from debug import logger

# Helper Functions
import helper_bootstrap
import helper_generic

from subprocess import call
import time

# OSX python version check
import sys
if sys.platform == 'darwin':
    if float("{1}.{2}".format(*sys.version_info)) < 7.5:
        msg = "You should use python 2.7.5 or greater. Your version: %s", "{0}.{1}.{2}".format(*sys.version_info)
        logger.critical(msg)
        print msg
        sys.exit(0)

def connectToStream(streamNumber):
    shared.streamsInWhichIAmParticipating[streamNumber] = 'no data'
    selfInitiatedConnections[streamNumber] = {}
    shared.inventorySets[streamNumber] = set()
    queryData = sqlQuery('''SELECT hash FROM inventory WHERE streamnumber=?''', streamNumber)
    for row in queryData:
        shared.inventorySets[streamNumber].add(row[0])

    
    if isOurOperatingSystemLimitedToHavingVeryFewHalfOpenConnections():
        # Some XP and Vista systems can only have 10 outgoing connections at a time.
        maximumNumberOfHalfOpenConnections = 9
    else:
        maximumNumberOfHalfOpenConnections = 64
    for i in range(maximumNumberOfHalfOpenConnections):
        a = outgoingSynSender()
        a.setup(streamNumber, selfInitiatedConnections)
        a.start()

def _fixWinsock():
    if not ('win32' in sys.platform) and not ('win64' in sys.platform):
        return

    # Python 2 on Windows doesn't define a wrapper for
    # socket.inet_ntop but we can make one ourselves using ctypes
    if not hasattr(socket, 'inet_ntop'):
        addressToString = ctypes.windll.ws2_32.WSAAddressToStringA
        def inet_ntop(family, host):
            if family == socket.AF_INET:
                if len(host) != 4:
                    raise ValueError("invalid IPv4 host")
                host = pack("hH4s8s", socket.AF_INET, 0, host, "\0" * 8)
            elif family == socket.AF_INET6:
                if len(host) != 16:
                    raise ValueError("invalid IPv6 host")
                host = pack("hHL16sL", socket.AF_INET6, 0, 0, host, 0)
            else:
                raise ValueError("invalid address family")
            buf = "\0" * 64
            lengthBuf = pack("I", len(buf))
            addressToString(host, len(host), None, buf, lengthBuf)
            return buf[0:buf.index("\0")]
        socket.inet_ntop = inet_ntop

    # Same for inet_pton
    if not hasattr(socket, 'inet_pton'):
        stringToAddress = ctypes.windll.ws2_32.WSAStringToAddressA
        def inet_pton(family, host):
            buf = "\0" * 28
            lengthBuf = pack("I", len(buf))
            if stringToAddress(str(host),
                               int(family),
                               None,
                               buf,
                               lengthBuf) != 0:
                raise socket.error("illegal IP address passed to inet_pton")
            if family == socket.AF_INET:
                return buf[4:8]
            elif family == socket.AF_INET6:
                return buf[8:24]
            else:
                raise ValueError("invalid address family")
        socket.inet_pton = inet_pton

    # These sockopts are needed on for IPv6 support
    if not hasattr(socket, 'IPPROTO_IPV6'):
        socket.IPPROTO_IPV6 = 41
    if not hasattr(socket, 'IPV6_V6ONLY'):
        socket.IPV6_V6ONLY = 27

# This thread, of which there is only one, runs the API.
class singleAPI(threading.Thread):

    def __init__(self):
        threading.Thread.__init__(self)

    def run(self):
        se = SimpleXMLRPCServer((shared.config.get('bitmessagesettings', 'apiinterface'), shared.config.getint(
            'bitmessagesettings', 'apiport')), MySimpleXMLRPCRequestHandler, True, True)
        se.register_introspection_functions()
        se.serve_forever()

# This is a list of current connections (the thread pointers at least)
selfInitiatedConnections = {}

if shared.useVeryEasyProofOfWorkForTesting:
    shared.networkDefaultProofOfWorkNonceTrialsPerByte = int(
        shared.networkDefaultProofOfWorkNonceTrialsPerByte / 16)
    shared.networkDefaultPayloadLengthExtraBytes = int(
        shared.networkDefaultPayloadLengthExtraBytes / 7000)

class Main:
    def start(self, daemon=False):
        _fixWinsock()

        shared.daemon = daemon
        # is the application already running?  If yes then exit.
        thisapp = singleton.singleinstance()

        signal.signal(signal.SIGINT, helper_generic.signal_handler)
        # signal.signal(signal.SIGINT, signal.SIG_DFL)

        helper_bootstrap.knownNodes()
        # Start the address generation thread
        addressGeneratorThread = addressGenerator()
        addressGeneratorThread.daemon = True  # close the main program even if there are threads left
        addressGeneratorThread.start()

        # Start the thread that calculates POWs
        singleWorkerThread = singleWorker()
        singleWorkerThread.daemon = True  # close the main program even if there are threads left
        singleWorkerThread.start()

        # Start the SQL thread
        sqlLookup = sqlThread()
        sqlLookup.daemon = False  # DON'T close the main program even if there are threads left. The closeEvent should command this thread to exit gracefully.
        sqlLookup.start()

        # Start the thread that calculates POWs
        objectProcessorThread = objectProcessor()
        objectProcessorThread.daemon = False  # DON'T close the main program even the thread remains. This thread checks the shutdown variable after processing each object.
        objectProcessorThread.start()

        # Start the cleanerThread
        singleCleanerThread = singleCleaner()
        singleCleanerThread.daemon = True  # close the main program even if there are threads left
        singleCleanerThread.start()

        shared.reloadMyAddressHashes()
        shared.reloadBroadcastSendersForWhichImWatching()

        if shared.safeConfigGetBoolean('bitmessagesettings', 'apienabled'):
            try:
                apiNotifyPath = shared.config.get(
                    'bitmessagesettings', 'apinotifypath')
            except:
                apiNotifyPath = ''
            if apiNotifyPath != '':
                with shared.printLock:
                    print 'Trying to call', apiNotifyPath

                call([apiNotifyPath, "startingUp"])
            singleAPIThread = singleAPI()
            singleAPIThread.daemon = True  # close the main program even if there are threads left
            singleAPIThread.start()

        connectToStream(1)

        singleListenerThread = singleListener()
        singleListenerThread.setup(selfInitiatedConnections)
        singleListenerThread.daemon = True  # close the main program even if there are threads left
        singleListenerThread.start()

        if daemon == False and shared.safeConfigGetBoolean('bitmessagesettings', 'daemon') == False:
            try:
                from PyQt4 import QtCore, QtGui
            except Exception as err:
                print 'PyBitmessage requires PyQt unless you want to run it as a daemon and interact with it using the API. You can download PyQt from http://www.riverbankcomputing.com/software/pyqt/download   or by searching Google for \'PyQt Download\'. If you want to run in daemon mode, see https://bitmessage.org/wiki/Daemon'
                print 'Error message:', err
                os._exit(0)

            import bitmessageqt
            bitmessageqt.run()
        else:
            shared.config.remove_option('bitmessagesettings', 'dontconnect')

            if daemon:
                with shared.printLock:
                    print 'Running as a daemon. The main program should exit this thread.'
            else:
                with shared.printLock:
                    print 'Running as a daemon. You can use Ctrl+C to exit.'
                while True:
                    time.sleep(20)

    def stop(self):
        with shared.printLock:
            print 'Stopping Bitmessage Deamon.'
        shared.doCleanShutdown()


    #TODO: nice function but no one is using this 
    def getApiAddress(self):
        if not shared.safeConfigGetBoolean('bitmessagesettings', 'apienabled'):
            return None
        address = shared.config.get('bitmessagesettings', 'apiinterface')
        port = shared.config.getint('bitmessagesettings', 'apiport')
        return {'address':address,'port':port}

if __name__ == "__main__":
    mainprogram = Main()
    mainprogram.start()


# So far, the creation of and management of the Bitmessage protocol and this
# client is a one-man operation. Bitcoin tips are quite appreciated.
# 1H5XaDA6fYENLbknwZyjiYXYPQaFjjLX2u

########NEW FILE########
__FILENAME__ = about
# -*- coding: utf-8 -*-

# Form implementation generated from reading ui file 'about.ui'
#
# Created: Tue Jan 21 22:29:38 2014
#      by: PyQt4 UI code generator 4.10.3
#
# WARNING! All changes made in this file will be lost!

from PyQt4 import QtCore, QtGui

try:
    _fromUtf8 = QtCore.QString.fromUtf8
except AttributeError:
    def _fromUtf8(s):
        return s

try:
    _encoding = QtGui.QApplication.UnicodeUTF8
    def _translate(context, text, disambig):
        return QtGui.QApplication.translate(context, text, disambig, _encoding)
except AttributeError:
    def _translate(context, text, disambig):
        return QtGui.QApplication.translate(context, text, disambig)

class Ui_aboutDialog(object):
    def setupUi(self, aboutDialog):
        aboutDialog.setObjectName(_fromUtf8("aboutDialog"))
        aboutDialog.resize(360, 315)
        self.buttonBox = QtGui.QDialogButtonBox(aboutDialog)
        self.buttonBox.setGeometry(QtCore.QRect(20, 280, 311, 32))
        self.buttonBox.setOrientation(QtCore.Qt.Horizontal)
        self.buttonBox.setStandardButtons(QtGui.QDialogButtonBox.Ok)
        self.buttonBox.setObjectName(_fromUtf8("buttonBox"))
        self.label = QtGui.QLabel(aboutDialog)
        self.label.setGeometry(QtCore.QRect(70, 126, 111, 20))
        font = QtGui.QFont()
        font.setBold(True)
        font.setWeight(75)
        self.label.setFont(font)
        self.label.setAlignment(QtCore.Qt.AlignRight|QtCore.Qt.AlignTrailing|QtCore.Qt.AlignVCenter)
        self.label.setObjectName(_fromUtf8("label"))
        self.labelVersion = QtGui.QLabel(aboutDialog)
        self.labelVersion.setGeometry(QtCore.QRect(190, 126, 161, 20))
        self.labelVersion.setObjectName(_fromUtf8("labelVersion"))
        self.label_2 = QtGui.QLabel(aboutDialog)
        self.label_2.setGeometry(QtCore.QRect(10, 150, 341, 41))
        self.label_2.setAlignment(QtCore.Qt.AlignCenter)
        self.label_2.setObjectName(_fromUtf8("label_2"))
        self.label_3 = QtGui.QLabel(aboutDialog)
        self.label_3.setGeometry(QtCore.QRect(20, 200, 331, 71))
        self.label_3.setWordWrap(True)
        self.label_3.setOpenExternalLinks(True)
        self.label_3.setObjectName(_fromUtf8("label_3"))
        self.label_5 = QtGui.QLabel(aboutDialog)
        self.label_5.setGeometry(QtCore.QRect(10, 190, 341, 20))
        self.label_5.setAlignment(QtCore.Qt.AlignCenter)
        self.label_5.setObjectName(_fromUtf8("label_5"))

        self.retranslateUi(aboutDialog)
        QtCore.QObject.connect(self.buttonBox, QtCore.SIGNAL(_fromUtf8("accepted()")), aboutDialog.accept)
        QtCore.QObject.connect(self.buttonBox, QtCore.SIGNAL(_fromUtf8("rejected()")), aboutDialog.reject)
        QtCore.QMetaObject.connectSlotsByName(aboutDialog)

    def retranslateUi(self, aboutDialog):
        aboutDialog.setWindowTitle(_translate("aboutDialog", "About", None))
        self.label.setText(_translate("aboutDialog", "PyBitmessage", None))
        self.labelVersion.setText(_translate("aboutDialog", "version ?", None))
        self.label_2.setText(_translate("aboutDialog", "<html><head/><body><p>Copyright © 2012-2014 Jonathan Warren<br/>Copyright © 2013-2014 The Bitmessage Developers</p></body></html>", None))
        self.label_3.setText(_translate("aboutDialog", "<html><head/><body><p>Distributed under the MIT/X11 software license; see <a href=\"http://www.opensource.org/licenses/mit-license.php\"><span style=\" text-decoration: underline; color:#0000ff;\">http://www.opensource.org/licenses/mit-license.php</span></a></p></body></html>", None))
        self.label_5.setText(_translate("aboutDialog", "This is Beta software.", None))


########NEW FILE########
__FILENAME__ = addaddressdialog
# -*- coding: utf-8 -*-

# Form implementation generated from reading ui file 'addaddressdialog.ui'
#
# Created: Sat Nov 30 20:35:38 2013
#      by: PyQt4 UI code generator 4.10.3
#
# WARNING! All changes made in this file will be lost!

from PyQt4 import QtCore, QtGui

try:
    _fromUtf8 = QtCore.QString.fromUtf8
except AttributeError:
    def _fromUtf8(s):
        return s

try:
    _encoding = QtGui.QApplication.UnicodeUTF8
    def _translate(context, text, disambig):
        return QtGui.QApplication.translate(context, text, disambig, _encoding)
except AttributeError:
    def _translate(context, text, disambig):
        return QtGui.QApplication.translate(context, text, disambig)

class Ui_AddAddressDialog(object):
    def setupUi(self, AddAddressDialog):
        AddAddressDialog.setObjectName(_fromUtf8("AddAddressDialog"))
        AddAddressDialog.resize(368, 162)
        self.formLayout = QtGui.QFormLayout(AddAddressDialog)
        self.formLayout.setFieldGrowthPolicy(QtGui.QFormLayout.AllNonFixedFieldsGrow)
        self.formLayout.setObjectName(_fromUtf8("formLayout"))
        self.label_2 = QtGui.QLabel(AddAddressDialog)
        self.label_2.setObjectName(_fromUtf8("label_2"))
        self.formLayout.setWidget(0, QtGui.QFormLayout.SpanningRole, self.label_2)
        self.newAddressLabel = QtGui.QLineEdit(AddAddressDialog)
        self.newAddressLabel.setObjectName(_fromUtf8("newAddressLabel"))
        self.formLayout.setWidget(2, QtGui.QFormLayout.SpanningRole, self.newAddressLabel)
        self.label = QtGui.QLabel(AddAddressDialog)
        self.label.setObjectName(_fromUtf8("label"))
        self.formLayout.setWidget(4, QtGui.QFormLayout.LabelRole, self.label)
        self.lineEditAddress = QtGui.QLineEdit(AddAddressDialog)
        self.lineEditAddress.setObjectName(_fromUtf8("lineEditAddress"))
        self.formLayout.setWidget(5, QtGui.QFormLayout.SpanningRole, self.lineEditAddress)
        self.labelAddressCheck = QtGui.QLabel(AddAddressDialog)
        self.labelAddressCheck.setText(_fromUtf8(""))
        self.labelAddressCheck.setWordWrap(True)
        self.labelAddressCheck.setObjectName(_fromUtf8("labelAddressCheck"))
        self.formLayout.setWidget(6, QtGui.QFormLayout.SpanningRole, self.labelAddressCheck)
        self.buttonBox = QtGui.QDialogButtonBox(AddAddressDialog)
        self.buttonBox.setOrientation(QtCore.Qt.Horizontal)
        self.buttonBox.setStandardButtons(QtGui.QDialogButtonBox.Cancel|QtGui.QDialogButtonBox.Ok)
        self.buttonBox.setObjectName(_fromUtf8("buttonBox"))
        self.formLayout.setWidget(7, QtGui.QFormLayout.FieldRole, self.buttonBox)

        self.retranslateUi(AddAddressDialog)
        QtCore.QObject.connect(self.buttonBox, QtCore.SIGNAL(_fromUtf8("accepted()")), AddAddressDialog.accept)
        QtCore.QObject.connect(self.buttonBox, QtCore.SIGNAL(_fromUtf8("rejected()")), AddAddressDialog.reject)
        QtCore.QMetaObject.connectSlotsByName(AddAddressDialog)

    def retranslateUi(self, AddAddressDialog):
        AddAddressDialog.setWindowTitle(_translate("AddAddressDialog", "Add new entry", None))
        self.label_2.setText(_translate("AddAddressDialog", "Label", None))
        self.label.setText(_translate("AddAddressDialog", "Address", None))


########NEW FILE########
__FILENAME__ = bitmessageui
# -*- coding: utf-8 -*-

# Form implementation generated from reading ui file 'bitmessageui.ui'
#
# Created: Sat Nov  2 18:01:09 2013
#      by: PyQt4 UI code generator 4.10
#
# WARNING! All changes made in this file will be lost!

from PyQt4 import QtCore, QtGui

try:
    _fromUtf8 = QtCore.QString.fromUtf8
except AttributeError:
    def _fromUtf8(s):
        return s

try:
    _encoding = QtGui.QApplication.UnicodeUTF8
    def _translate(context, text, disambig):
        return QtGui.QApplication.translate(context, text, disambig, _encoding)
except AttributeError:
    def _translate(context, text, disambig):
        return QtGui.QApplication.translate(context, text, disambig)

class Ui_MainWindow(object):
    def setupUi(self, MainWindow):
        MainWindow.setObjectName(_fromUtf8("MainWindow"))
        MainWindow.resize(885, 580)
        icon = QtGui.QIcon()
        icon.addPixmap(QtGui.QPixmap(_fromUtf8(":/newPrefix/images/can-icon-24px.png")), QtGui.QIcon.Normal, QtGui.QIcon.Off)
        MainWindow.setWindowIcon(icon)
        MainWindow.setTabShape(QtGui.QTabWidget.Rounded)
        self.centralwidget = QtGui.QWidget(MainWindow)
        self.centralwidget.setObjectName(_fromUtf8("centralwidget"))
        self.gridLayout = QtGui.QGridLayout(self.centralwidget)
        self.gridLayout.setMargin(0)
        self.gridLayout.setObjectName(_fromUtf8("gridLayout"))
        self.tabWidget = QtGui.QTabWidget(self.centralwidget)
        sizePolicy = QtGui.QSizePolicy(QtGui.QSizePolicy.Expanding, QtGui.QSizePolicy.Expanding)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.tabWidget.sizePolicy().hasHeightForWidth())
        self.tabWidget.setSizePolicy(sizePolicy)
        self.tabWidget.setMinimumSize(QtCore.QSize(0, 0))
        self.tabWidget.setBaseSize(QtCore.QSize(0, 0))
        font = QtGui.QFont()
        font.setPointSize(9)
        self.tabWidget.setFont(font)
        self.tabWidget.setTabPosition(QtGui.QTabWidget.North)
        self.tabWidget.setTabShape(QtGui.QTabWidget.Rounded)
        self.tabWidget.setObjectName(_fromUtf8("tabWidget"))
        self.inbox = QtGui.QWidget()
        self.inbox.setObjectName(_fromUtf8("inbox"))
        self.verticalLayout_2 = QtGui.QVBoxLayout(self.inbox)
        self.verticalLayout_2.setObjectName(_fromUtf8("verticalLayout_2"))
        self.horizontalLayoutSearch = QtGui.QHBoxLayout()
        self.horizontalLayoutSearch.setContentsMargins(-1, 0, -1, -1)
        self.horizontalLayoutSearch.setObjectName(_fromUtf8("horizontalLayoutSearch"))
        self.inboxSearchLineEdit = QtGui.QLineEdit(self.inbox)
        self.inboxSearchLineEdit.setObjectName(_fromUtf8("inboxSearchLineEdit"))
        self.horizontalLayoutSearch.addWidget(self.inboxSearchLineEdit)
        self.inboxSearchOptionCB = QtGui.QComboBox(self.inbox)
        self.inboxSearchOptionCB.setObjectName(_fromUtf8("inboxSearchOptionCB"))
        self.inboxSearchOptionCB.addItem(_fromUtf8(""))
        self.inboxSearchOptionCB.addItem(_fromUtf8(""))
        self.inboxSearchOptionCB.addItem(_fromUtf8(""))
        self.inboxSearchOptionCB.addItem(_fromUtf8(""))
        self.inboxSearchOptionCB.addItem(_fromUtf8(""))
        self.horizontalLayoutSearch.addWidget(self.inboxSearchOptionCB)
        self.verticalLayout_2.addLayout(self.horizontalLayoutSearch)
        self.splitter = QtGui.QSplitter(self.inbox)
        self.splitter.setOrientation(QtCore.Qt.Vertical)
        self.splitter.setObjectName(_fromUtf8("splitter"))
        self.tableWidgetInbox = QtGui.QTableWidget(self.splitter)
        self.tableWidgetInbox.setEditTriggers(QtGui.QAbstractItemView.NoEditTriggers)
        self.tableWidgetInbox.setAlternatingRowColors(True)
        self.tableWidgetInbox.setSelectionMode(QtGui.QAbstractItemView.ExtendedSelection)
        self.tableWidgetInbox.setSelectionBehavior(QtGui.QAbstractItemView.SelectRows)
        self.tableWidgetInbox.setWordWrap(False)
        self.tableWidgetInbox.setObjectName(_fromUtf8("tableWidgetInbox"))
        self.tableWidgetInbox.setColumnCount(4)
        self.tableWidgetInbox.setRowCount(0)
        item = QtGui.QTableWidgetItem()
        self.tableWidgetInbox.setHorizontalHeaderItem(0, item)
        item = QtGui.QTableWidgetItem()
        self.tableWidgetInbox.setHorizontalHeaderItem(1, item)
        item = QtGui.QTableWidgetItem()
        self.tableWidgetInbox.setHorizontalHeaderItem(2, item)
        item = QtGui.QTableWidgetItem()
        self.tableWidgetInbox.setHorizontalHeaderItem(3, item)
        self.tableWidgetInbox.horizontalHeader().setCascadingSectionResizes(True)
        self.tableWidgetInbox.horizontalHeader().setDefaultSectionSize(200)
        self.tableWidgetInbox.horizontalHeader().setHighlightSections(False)
        self.tableWidgetInbox.horizontalHeader().setMinimumSectionSize(27)
        self.tableWidgetInbox.horizontalHeader().setSortIndicatorShown(False)
        self.tableWidgetInbox.horizontalHeader().setStretchLastSection(True)
        self.tableWidgetInbox.verticalHeader().setVisible(False)
        self.tableWidgetInbox.verticalHeader().setDefaultSectionSize(26)
        self.textEditInboxMessage = QtGui.QTextEdit(self.splitter)
        self.textEditInboxMessage.setBaseSize(QtCore.QSize(0, 500))
        self.textEditInboxMessage.setReadOnly(True)
        self.textEditInboxMessage.setObjectName(_fromUtf8("textEditInboxMessage"))
        self.verticalLayout_2.addWidget(self.splitter)
        icon1 = QtGui.QIcon()
        icon1.addPixmap(QtGui.QPixmap(_fromUtf8(":/newPrefix/images/inbox.png")), QtGui.QIcon.Normal, QtGui.QIcon.Off)
        self.tabWidget.addTab(self.inbox, icon1, _fromUtf8(""))
        self.send = QtGui.QWidget()
        self.send.setObjectName(_fromUtf8("send"))
        self.gridLayout_2 = QtGui.QGridLayout(self.send)
        self.gridLayout_2.setObjectName(_fromUtf8("gridLayout_2"))
        self.pushButtonLoadFromAddressBook = QtGui.QPushButton(self.send)
        font = QtGui.QFont()
        font.setPointSize(7)
        self.pushButtonLoadFromAddressBook.setFont(font)
        self.pushButtonLoadFromAddressBook.setObjectName(_fromUtf8("pushButtonLoadFromAddressBook"))
        self.gridLayout_2.addWidget(self.pushButtonLoadFromAddressBook, 3, 2, 1, 1)
        self.pushButtonFetchNamecoinID = QtGui.QPushButton(self.send)
        font = QtGui.QFont()
        font.setPointSize(7)
        self.pushButtonFetchNamecoinID.setFont(font)
        self.pushButtonFetchNamecoinID.setObjectName(_fromUtf8("pushButtonFetchNamecoinID"))
        self.gridLayout_2.addWidget(self.pushButtonFetchNamecoinID, 3, 3, 1, 1)
        self.label_4 = QtGui.QLabel(self.send)
        self.label_4.setObjectName(_fromUtf8("label_4"))
        self.gridLayout_2.addWidget(self.label_4, 5, 0, 1, 1)
        self.comboBoxSendFrom = QtGui.QComboBox(self.send)
        self.comboBoxSendFrom.setMinimumSize(QtCore.QSize(300, 0))
        self.comboBoxSendFrom.setObjectName(_fromUtf8("comboBoxSendFrom"))
        self.gridLayout_2.addWidget(self.comboBoxSendFrom, 2, 1, 1, 1)
        self.label_3 = QtGui.QLabel(self.send)
        self.label_3.setObjectName(_fromUtf8("label_3"))
        self.gridLayout_2.addWidget(self.label_3, 4, 0, 1, 1)
        self.labelFrom = QtGui.QLabel(self.send)
        self.labelFrom.setText(_fromUtf8(""))
        self.labelFrom.setObjectName(_fromUtf8("labelFrom"))
        self.gridLayout_2.addWidget(self.labelFrom, 2, 2, 1, 3)
        self.radioButtonSpecific = QtGui.QRadioButton(self.send)
        self.radioButtonSpecific.setChecked(True)
        self.radioButtonSpecific.setObjectName(_fromUtf8("radioButtonSpecific"))
        self.gridLayout_2.addWidget(self.radioButtonSpecific, 0, 1, 1, 1)
        self.lineEditTo = QtGui.QLineEdit(self.send)
        self.lineEditTo.setObjectName(_fromUtf8("lineEditTo"))
        self.gridLayout_2.addWidget(self.lineEditTo, 3, 1, 1, 1)
        self.textEditMessage = QtGui.QTextEdit(self.send)
        self.textEditMessage.setObjectName(_fromUtf8("textEditMessage"))
        self.gridLayout_2.addWidget(self.textEditMessage, 5, 1, 2, 5)
        self.label = QtGui.QLabel(self.send)
        self.label.setObjectName(_fromUtf8("label"))
        self.gridLayout_2.addWidget(self.label, 3, 0, 1, 1)
        self.label_2 = QtGui.QLabel(self.send)
        self.label_2.setObjectName(_fromUtf8("label_2"))
        self.gridLayout_2.addWidget(self.label_2, 2, 0, 1, 1)
        spacerItem = QtGui.QSpacerItem(20, 297, QtGui.QSizePolicy.Minimum, QtGui.QSizePolicy.Expanding)
        self.gridLayout_2.addItem(spacerItem, 6, 0, 1, 1)
        self.radioButtonBroadcast = QtGui.QRadioButton(self.send)
        self.radioButtonBroadcast.setObjectName(_fromUtf8("radioButtonBroadcast"))
        self.gridLayout_2.addWidget(self.radioButtonBroadcast, 1, 1, 1, 3)
        self.lineEditSubject = QtGui.QLineEdit(self.send)
        self.lineEditSubject.setText(_fromUtf8(""))
        self.lineEditSubject.setObjectName(_fromUtf8("lineEditSubject"))
        self.gridLayout_2.addWidget(self.lineEditSubject, 4, 1, 1, 5)
        spacerItem1 = QtGui.QSpacerItem(20, 20, QtGui.QSizePolicy.Expanding, QtGui.QSizePolicy.Minimum)
        self.gridLayout_2.addItem(spacerItem1, 3, 4, 1, 1)
        self.pushButtonSend = QtGui.QPushButton(self.send)
        self.pushButtonSend.setObjectName(_fromUtf8("pushButtonSend"))
        self.gridLayout_2.addWidget(self.pushButtonSend, 7, 5, 1, 1)
        self.labelSendBroadcastWarning = QtGui.QLabel(self.send)
        self.labelSendBroadcastWarning.setEnabled(True)
        sizePolicy = QtGui.QSizePolicy(QtGui.QSizePolicy.Ignored, QtGui.QSizePolicy.Preferred)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.labelSendBroadcastWarning.sizePolicy().hasHeightForWidth())
        self.labelSendBroadcastWarning.setSizePolicy(sizePolicy)
        self.labelSendBroadcastWarning.setIndent(-1)
        self.labelSendBroadcastWarning.setObjectName(_fromUtf8("labelSendBroadcastWarning"))
        self.gridLayout_2.addWidget(self.labelSendBroadcastWarning, 7, 1, 1, 4)
        icon2 = QtGui.QIcon()
        icon2.addPixmap(QtGui.QPixmap(_fromUtf8(":/newPrefix/images/send.png")), QtGui.QIcon.Normal, QtGui.QIcon.Off)
        self.tabWidget.addTab(self.send, icon2, _fromUtf8(""))
        self.sent = QtGui.QWidget()
        self.sent.setObjectName(_fromUtf8("sent"))
        self.verticalLayout = QtGui.QVBoxLayout(self.sent)
        self.verticalLayout.setObjectName(_fromUtf8("verticalLayout"))
        self.horizontalLayout = QtGui.QHBoxLayout()
        self.horizontalLayout.setContentsMargins(-1, 0, -1, -1)
        self.horizontalLayout.setObjectName(_fromUtf8("horizontalLayout"))
        self.sentSearchLineEdit = QtGui.QLineEdit(self.sent)
        self.sentSearchLineEdit.setObjectName(_fromUtf8("sentSearchLineEdit"))
        self.horizontalLayout.addWidget(self.sentSearchLineEdit)
        self.sentSearchOptionCB = QtGui.QComboBox(self.sent)
        self.sentSearchOptionCB.setObjectName(_fromUtf8("sentSearchOptionCB"))
        self.sentSearchOptionCB.addItem(_fromUtf8(""))
        self.sentSearchOptionCB.addItem(_fromUtf8(""))
        self.sentSearchOptionCB.addItem(_fromUtf8(""))
        self.sentSearchOptionCB.addItem(_fromUtf8(""))
        self.sentSearchOptionCB.addItem(_fromUtf8(""))
        self.horizontalLayout.addWidget(self.sentSearchOptionCB)
        self.verticalLayout.addLayout(self.horizontalLayout)
        self.splitter_2 = QtGui.QSplitter(self.sent)
        self.splitter_2.setOrientation(QtCore.Qt.Vertical)
        self.splitter_2.setObjectName(_fromUtf8("splitter_2"))
        self.tableWidgetSent = QtGui.QTableWidget(self.splitter_2)
        self.tableWidgetSent.setEditTriggers(QtGui.QAbstractItemView.NoEditTriggers)
        self.tableWidgetSent.setDragDropMode(QtGui.QAbstractItemView.DragDrop)
        self.tableWidgetSent.setAlternatingRowColors(True)
        self.tableWidgetSent.setSelectionMode(QtGui.QAbstractItemView.ExtendedSelection)
        self.tableWidgetSent.setSelectionBehavior(QtGui.QAbstractItemView.SelectRows)
        self.tableWidgetSent.setWordWrap(False)
        self.tableWidgetSent.setObjectName(_fromUtf8("tableWidgetSent"))
        self.tableWidgetSent.setColumnCount(4)
        self.tableWidgetSent.setRowCount(0)
        item = QtGui.QTableWidgetItem()
        self.tableWidgetSent.setHorizontalHeaderItem(0, item)
        item = QtGui.QTableWidgetItem()
        self.tableWidgetSent.setHorizontalHeaderItem(1, item)
        item = QtGui.QTableWidgetItem()
        self.tableWidgetSent.setHorizontalHeaderItem(2, item)
        item = QtGui.QTableWidgetItem()
        self.tableWidgetSent.setHorizontalHeaderItem(3, item)
        self.tableWidgetSent.horizontalHeader().setCascadingSectionResizes(True)
        self.tableWidgetSent.horizontalHeader().setDefaultSectionSize(130)
        self.tableWidgetSent.horizontalHeader().setHighlightSections(False)
        self.tableWidgetSent.horizontalHeader().setSortIndicatorShown(False)
        self.tableWidgetSent.horizontalHeader().setStretchLastSection(True)
        self.tableWidgetSent.verticalHeader().setVisible(False)
        self.tableWidgetSent.verticalHeader().setStretchLastSection(False)
        self.textEditSentMessage = QtGui.QTextEdit(self.splitter_2)
        self.textEditSentMessage.setReadOnly(True)
        self.textEditSentMessage.setObjectName(_fromUtf8("textEditSentMessage"))
        self.verticalLayout.addWidget(self.splitter_2)
        icon3 = QtGui.QIcon()
        icon3.addPixmap(QtGui.QPixmap(_fromUtf8(":/newPrefix/images/sent.png")), QtGui.QIcon.Normal, QtGui.QIcon.Off)
        self.tabWidget.addTab(self.sent, icon3, _fromUtf8(""))
        self.youridentities = QtGui.QWidget()
        self.youridentities.setObjectName(_fromUtf8("youridentities"))
        self.gridLayout_3 = QtGui.QGridLayout(self.youridentities)
        self.gridLayout_3.setObjectName(_fromUtf8("gridLayout_3"))
        self.pushButtonNewAddress = QtGui.QPushButton(self.youridentities)
        self.pushButtonNewAddress.setObjectName(_fromUtf8("pushButtonNewAddress"))
        self.gridLayout_3.addWidget(self.pushButtonNewAddress, 0, 0, 1, 1)
        spacerItem2 = QtGui.QSpacerItem(689, 20, QtGui.QSizePolicy.Expanding, QtGui.QSizePolicy.Minimum)
        self.gridLayout_3.addItem(spacerItem2, 0, 1, 1, 1)
        self.tableWidgetYourIdentities = QtGui.QTableWidget(self.youridentities)
        self.tableWidgetYourIdentities.setFrameShadow(QtGui.QFrame.Sunken)
        self.tableWidgetYourIdentities.setLineWidth(1)
        self.tableWidgetYourIdentities.setAlternatingRowColors(True)
        self.tableWidgetYourIdentities.setSelectionMode(QtGui.QAbstractItemView.SingleSelection)
        self.tableWidgetYourIdentities.setSelectionBehavior(QtGui.QAbstractItemView.SelectRows)
        self.tableWidgetYourIdentities.setObjectName(_fromUtf8("tableWidgetYourIdentities"))
        self.tableWidgetYourIdentities.setColumnCount(3)
        self.tableWidgetYourIdentities.setRowCount(0)
        item = QtGui.QTableWidgetItem()
        font = QtGui.QFont()
        font.setKerning(True)
        item.setFont(font)
        self.tableWidgetYourIdentities.setHorizontalHeaderItem(0, item)
        item = QtGui.QTableWidgetItem()
        self.tableWidgetYourIdentities.setHorizontalHeaderItem(1, item)
        item = QtGui.QTableWidgetItem()
        self.tableWidgetYourIdentities.setHorizontalHeaderItem(2, item)
        self.tableWidgetYourIdentities.horizontalHeader().setCascadingSectionResizes(True)
        self.tableWidgetYourIdentities.horizontalHeader().setDefaultSectionSize(346)
        self.tableWidgetYourIdentities.horizontalHeader().setMinimumSectionSize(52)
        self.tableWidgetYourIdentities.horizontalHeader().setSortIndicatorShown(True)
        self.tableWidgetYourIdentities.horizontalHeader().setStretchLastSection(True)
        self.tableWidgetYourIdentities.verticalHeader().setVisible(False)
        self.tableWidgetYourIdentities.verticalHeader().setDefaultSectionSize(26)
        self.tableWidgetYourIdentities.verticalHeader().setSortIndicatorShown(False)
        self.tableWidgetYourIdentities.verticalHeader().setStretchLastSection(False)
        self.gridLayout_3.addWidget(self.tableWidgetYourIdentities, 1, 0, 1, 2)
        icon4 = QtGui.QIcon()
        icon4.addPixmap(QtGui.QPixmap(_fromUtf8(":/newPrefix/images/identities.png")), QtGui.QIcon.Normal, QtGui.QIcon.Off)
        self.tabWidget.addTab(self.youridentities, icon4, _fromUtf8(""))
        self.subscriptions = QtGui.QWidget()
        self.subscriptions.setObjectName(_fromUtf8("subscriptions"))
        self.gridLayout_4 = QtGui.QGridLayout(self.subscriptions)
        self.gridLayout_4.setObjectName(_fromUtf8("gridLayout_4"))
        self.label_5 = QtGui.QLabel(self.subscriptions)
        self.label_5.setWordWrap(True)
        self.label_5.setObjectName(_fromUtf8("label_5"))
        self.gridLayout_4.addWidget(self.label_5, 0, 0, 1, 2)
        self.pushButtonAddSubscription = QtGui.QPushButton(self.subscriptions)
        self.pushButtonAddSubscription.setObjectName(_fromUtf8("pushButtonAddSubscription"))
        self.gridLayout_4.addWidget(self.pushButtonAddSubscription, 1, 0, 1, 1)
        spacerItem3 = QtGui.QSpacerItem(689, 20, QtGui.QSizePolicy.Expanding, QtGui.QSizePolicy.Minimum)
        self.gridLayout_4.addItem(spacerItem3, 1, 1, 1, 1)
        self.tableWidgetSubscriptions = QtGui.QTableWidget(self.subscriptions)
        self.tableWidgetSubscriptions.setAlternatingRowColors(True)
        self.tableWidgetSubscriptions.setSelectionMode(QtGui.QAbstractItemView.SingleSelection)
        self.tableWidgetSubscriptions.setSelectionBehavior(QtGui.QAbstractItemView.SelectRows)
        self.tableWidgetSubscriptions.setObjectName(_fromUtf8("tableWidgetSubscriptions"))
        self.tableWidgetSubscriptions.setColumnCount(2)
        self.tableWidgetSubscriptions.setRowCount(0)
        item = QtGui.QTableWidgetItem()
        self.tableWidgetSubscriptions.setHorizontalHeaderItem(0, item)
        item = QtGui.QTableWidgetItem()
        self.tableWidgetSubscriptions.setHorizontalHeaderItem(1, item)
        self.tableWidgetSubscriptions.horizontalHeader().setCascadingSectionResizes(True)
        self.tableWidgetSubscriptions.horizontalHeader().setDefaultSectionSize(400)
        self.tableWidgetSubscriptions.horizontalHeader().setHighlightSections(False)
        self.tableWidgetSubscriptions.horizontalHeader().setSortIndicatorShown(False)
        self.tableWidgetSubscriptions.horizontalHeader().setStretchLastSection(True)
        self.tableWidgetSubscriptions.verticalHeader().setVisible(False)
        self.gridLayout_4.addWidget(self.tableWidgetSubscriptions, 2, 0, 1, 2)
        icon5 = QtGui.QIcon()
        icon5.addPixmap(QtGui.QPixmap(_fromUtf8(":/newPrefix/images/subscriptions.png")), QtGui.QIcon.Normal, QtGui.QIcon.Off)
        self.tabWidget.addTab(self.subscriptions, icon5, _fromUtf8(""))
        self.addressbook = QtGui.QWidget()
        self.addressbook.setObjectName(_fromUtf8("addressbook"))
        self.gridLayout_5 = QtGui.QGridLayout(self.addressbook)
        self.gridLayout_5.setObjectName(_fromUtf8("gridLayout_5"))
        self.label_6 = QtGui.QLabel(self.addressbook)
        self.label_6.setWordWrap(True)
        self.label_6.setObjectName(_fromUtf8("label_6"))
        self.gridLayout_5.addWidget(self.label_6, 0, 0, 1, 2)
        self.pushButtonAddAddressBook = QtGui.QPushButton(self.addressbook)
        self.pushButtonAddAddressBook.setObjectName(_fromUtf8("pushButtonAddAddressBook"))
        self.gridLayout_5.addWidget(self.pushButtonAddAddressBook, 1, 0, 1, 1)
        spacerItem4 = QtGui.QSpacerItem(689, 20, QtGui.QSizePolicy.Expanding, QtGui.QSizePolicy.Minimum)
        self.gridLayout_5.addItem(spacerItem4, 1, 1, 1, 1)
        self.tableWidgetAddressBook = QtGui.QTableWidget(self.addressbook)
        self.tableWidgetAddressBook.setAlternatingRowColors(True)
        self.tableWidgetAddressBook.setSelectionMode(QtGui.QAbstractItemView.ExtendedSelection)
        self.tableWidgetAddressBook.setSelectionBehavior(QtGui.QAbstractItemView.SelectRows)
        self.tableWidgetAddressBook.setObjectName(_fromUtf8("tableWidgetAddressBook"))
        self.tableWidgetAddressBook.setColumnCount(2)
        self.tableWidgetAddressBook.setRowCount(0)
        item = QtGui.QTableWidgetItem()
        self.tableWidgetAddressBook.setHorizontalHeaderItem(0, item)
        item = QtGui.QTableWidgetItem()
        self.tableWidgetAddressBook.setHorizontalHeaderItem(1, item)
        self.tableWidgetAddressBook.horizontalHeader().setCascadingSectionResizes(True)
        self.tableWidgetAddressBook.horizontalHeader().setDefaultSectionSize(400)
        self.tableWidgetAddressBook.horizontalHeader().setHighlightSections(False)
        self.tableWidgetAddressBook.horizontalHeader().setStretchLastSection(True)
        self.tableWidgetAddressBook.verticalHeader().setVisible(False)
        self.gridLayout_5.addWidget(self.tableWidgetAddressBook, 2, 0, 1, 2)
        icon6 = QtGui.QIcon()
        icon6.addPixmap(QtGui.QPixmap(_fromUtf8(":/newPrefix/images/addressbook.png")), QtGui.QIcon.Normal, QtGui.QIcon.Off)
        self.tabWidget.addTab(self.addressbook, icon6, _fromUtf8(""))
        self.blackwhitelist = QtGui.QWidget()
        self.blackwhitelist.setObjectName(_fromUtf8("blackwhitelist"))
        self.gridLayout_6 = QtGui.QGridLayout(self.blackwhitelist)
        self.gridLayout_6.setObjectName(_fromUtf8("gridLayout_6"))
        self.radioButtonBlacklist = QtGui.QRadioButton(self.blackwhitelist)
        self.radioButtonBlacklist.setChecked(True)
        self.radioButtonBlacklist.setObjectName(_fromUtf8("radioButtonBlacklist"))
        self.gridLayout_6.addWidget(self.radioButtonBlacklist, 0, 0, 1, 2)
        self.radioButtonWhitelist = QtGui.QRadioButton(self.blackwhitelist)
        self.radioButtonWhitelist.setObjectName(_fromUtf8("radioButtonWhitelist"))
        self.gridLayout_6.addWidget(self.radioButtonWhitelist, 1, 0, 1, 2)
        self.pushButtonAddBlacklist = QtGui.QPushButton(self.blackwhitelist)
        self.pushButtonAddBlacklist.setObjectName(_fromUtf8("pushButtonAddBlacklist"))
        self.gridLayout_6.addWidget(self.pushButtonAddBlacklist, 2, 0, 1, 1)
        spacerItem5 = QtGui.QSpacerItem(689, 20, QtGui.QSizePolicy.Expanding, QtGui.QSizePolicy.Minimum)
        self.gridLayout_6.addItem(spacerItem5, 2, 1, 1, 1)
        self.tableWidgetBlacklist = QtGui.QTableWidget(self.blackwhitelist)
        self.tableWidgetBlacklist.setAlternatingRowColors(True)
        self.tableWidgetBlacklist.setSelectionMode(QtGui.QAbstractItemView.SingleSelection)
        self.tableWidgetBlacklist.setSelectionBehavior(QtGui.QAbstractItemView.SelectRows)
        self.tableWidgetBlacklist.setObjectName(_fromUtf8("tableWidgetBlacklist"))
        self.tableWidgetBlacklist.setColumnCount(2)
        self.tableWidgetBlacklist.setRowCount(0)
        item = QtGui.QTableWidgetItem()
        self.tableWidgetBlacklist.setHorizontalHeaderItem(0, item)
        item = QtGui.QTableWidgetItem()
        self.tableWidgetBlacklist.setHorizontalHeaderItem(1, item)
        self.tableWidgetBlacklist.horizontalHeader().setCascadingSectionResizes(True)
        self.tableWidgetBlacklist.horizontalHeader().setDefaultSectionSize(400)
        self.tableWidgetBlacklist.horizontalHeader().setHighlightSections(False)
        self.tableWidgetBlacklist.horizontalHeader().setSortIndicatorShown(False)
        self.tableWidgetBlacklist.horizontalHeader().setStretchLastSection(True)
        self.tableWidgetBlacklist.verticalHeader().setVisible(False)
        self.gridLayout_6.addWidget(self.tableWidgetBlacklist, 3, 0, 1, 2)
        icon7 = QtGui.QIcon()
        icon7.addPixmap(QtGui.QPixmap(_fromUtf8(":/newPrefix/images/blacklist.png")), QtGui.QIcon.Normal, QtGui.QIcon.Off)
        self.tabWidget.addTab(self.blackwhitelist, icon7, _fromUtf8(""))
        self.networkstatus = QtGui.QWidget()
        self.networkstatus.setObjectName(_fromUtf8("networkstatus"))
        self.pushButtonStatusIcon = QtGui.QPushButton(self.networkstatus)
        self.pushButtonStatusIcon.setGeometry(QtCore.QRect(680, 440, 21, 23))
        self.pushButtonStatusIcon.setText(_fromUtf8(""))
        icon8 = QtGui.QIcon()
        icon8.addPixmap(QtGui.QPixmap(_fromUtf8(":/newPrefix/images/redicon.png")), QtGui.QIcon.Normal, QtGui.QIcon.Off)
        self.pushButtonStatusIcon.setIcon(icon8)
        self.pushButtonStatusIcon.setFlat(True)
        self.pushButtonStatusIcon.setObjectName(_fromUtf8("pushButtonStatusIcon"))
        self.tableWidgetConnectionCount = QtGui.QTableWidget(self.networkstatus)
        self.tableWidgetConnectionCount.setGeometry(QtCore.QRect(20, 70, 241, 241))
        palette = QtGui.QPalette()
        brush = QtGui.QBrush(QtGui.QColor(212, 208, 200))
        brush.setStyle(QtCore.Qt.SolidPattern)
        palette.setBrush(QtGui.QPalette.Active, QtGui.QPalette.Base, brush)
        brush = QtGui.QBrush(QtGui.QColor(212, 208, 200))
        brush.setStyle(QtCore.Qt.SolidPattern)
        palette.setBrush(QtGui.QPalette.Inactive, QtGui.QPalette.Base, brush)
        brush = QtGui.QBrush(QtGui.QColor(212, 208, 200))
        brush.setStyle(QtCore.Qt.SolidPattern)
        palette.setBrush(QtGui.QPalette.Disabled, QtGui.QPalette.Base, brush)
        self.tableWidgetConnectionCount.setPalette(palette)
        self.tableWidgetConnectionCount.setFrameShape(QtGui.QFrame.Box)
        self.tableWidgetConnectionCount.setFrameShadow(QtGui.QFrame.Plain)
        self.tableWidgetConnectionCount.setProperty("showDropIndicator", False)
        self.tableWidgetConnectionCount.setAlternatingRowColors(True)
        self.tableWidgetConnectionCount.setSelectionMode(QtGui.QAbstractItemView.NoSelection)
        self.tableWidgetConnectionCount.setObjectName(_fromUtf8("tableWidgetConnectionCount"))
        self.tableWidgetConnectionCount.setColumnCount(2)
        self.tableWidgetConnectionCount.setRowCount(0)
        item = QtGui.QTableWidgetItem()
        self.tableWidgetConnectionCount.setHorizontalHeaderItem(0, item)
        item = QtGui.QTableWidgetItem()
        self.tableWidgetConnectionCount.setHorizontalHeaderItem(1, item)
        self.tableWidgetConnectionCount.horizontalHeader().setCascadingSectionResizes(True)
        self.tableWidgetConnectionCount.horizontalHeader().setHighlightSections(False)
        self.tableWidgetConnectionCount.horizontalHeader().setStretchLastSection(True)
        self.tableWidgetConnectionCount.verticalHeader().setVisible(False)
        self.labelTotalConnections = QtGui.QLabel(self.networkstatus)
        self.labelTotalConnections.setGeometry(QtCore.QRect(20, 30, 401, 16))
        self.labelTotalConnections.setObjectName(_fromUtf8("labelTotalConnections"))
        self.labelStartupTime = QtGui.QLabel(self.networkstatus)
        self.labelStartupTime.setGeometry(QtCore.QRect(320, 110, 331, 20))
        self.labelStartupTime.setObjectName(_fromUtf8("labelStartupTime"))
        self.labelMessageCount = QtGui.QLabel(self.networkstatus)
        self.labelMessageCount.setGeometry(QtCore.QRect(350, 130, 361, 16))
        self.labelMessageCount.setObjectName(_fromUtf8("labelMessageCount"))
        self.labelPubkeyCount = QtGui.QLabel(self.networkstatus)
        self.labelPubkeyCount.setGeometry(QtCore.QRect(350, 170, 331, 16))
        self.labelPubkeyCount.setObjectName(_fromUtf8("labelPubkeyCount"))
        self.labelBroadcastCount = QtGui.QLabel(self.networkstatus)
        self.labelBroadcastCount.setGeometry(QtCore.QRect(350, 150, 351, 16))
        self.labelBroadcastCount.setObjectName(_fromUtf8("labelBroadcastCount"))
        self.labelLookupsPerSecond = QtGui.QLabel(self.networkstatus)
        self.labelLookupsPerSecond.setGeometry(QtCore.QRect(320, 210, 291, 16))
        self.labelLookupsPerSecond.setObjectName(_fromUtf8("labelLookupsPerSecond"))
        icon9 = QtGui.QIcon()
        icon9.addPixmap(QtGui.QPixmap(_fromUtf8(":/newPrefix/images/networkstatus.png")), QtGui.QIcon.Normal, QtGui.QIcon.Off)
        self.tabWidget.addTab(self.networkstatus, icon9, _fromUtf8(""))
        self.gridLayout.addWidget(self.tabWidget, 0, 0, 1, 1)
        MainWindow.setCentralWidget(self.centralwidget)
        self.menubar = QtGui.QMenuBar(MainWindow)
        self.menubar.setGeometry(QtCore.QRect(0, 0, 885, 27))
        self.menubar.setObjectName(_fromUtf8("menubar"))
        self.menuFile = QtGui.QMenu(self.menubar)
        self.menuFile.setObjectName(_fromUtf8("menuFile"))
        self.menuSettings = QtGui.QMenu(self.menubar)
        self.menuSettings.setObjectName(_fromUtf8("menuSettings"))
        self.menuHelp = QtGui.QMenu(self.menubar)
        self.menuHelp.setObjectName(_fromUtf8("menuHelp"))
        MainWindow.setMenuBar(self.menubar)
        self.statusbar = QtGui.QStatusBar(MainWindow)
        self.statusbar.setMaximumSize(QtCore.QSize(16777215, 22))
        self.statusbar.setObjectName(_fromUtf8("statusbar"))
        MainWindow.setStatusBar(self.statusbar)
        self.actionImport_keys = QtGui.QAction(MainWindow)
        self.actionImport_keys.setObjectName(_fromUtf8("actionImport_keys"))
        self.actionManageKeys = QtGui.QAction(MainWindow)
        self.actionManageKeys.setCheckable(False)
        self.actionManageKeys.setEnabled(True)
        icon = QtGui.QIcon.fromTheme(_fromUtf8("dialog-password"))
        self.actionManageKeys.setIcon(icon)
        self.actionManageKeys.setObjectName(_fromUtf8("actionManageKeys"))
        self.actionExit = QtGui.QAction(MainWindow)
        icon = QtGui.QIcon.fromTheme(_fromUtf8("application-exit"))
        self.actionExit.setIcon(icon)
        self.actionExit.setObjectName(_fromUtf8("actionExit"))
        self.actionHelp = QtGui.QAction(MainWindow)
        icon = QtGui.QIcon.fromTheme(_fromUtf8("help-contents"))
        self.actionHelp.setIcon(icon)
        self.actionHelp.setObjectName(_fromUtf8("actionHelp"))
        self.actionAbout = QtGui.QAction(MainWindow)
        icon = QtGui.QIcon.fromTheme(_fromUtf8("help-about"))
        self.actionAbout.setIcon(icon)
        self.actionAbout.setObjectName(_fromUtf8("actionAbout"))
        self.actionSettings = QtGui.QAction(MainWindow)
        icon = QtGui.QIcon.fromTheme(_fromUtf8("document-properties"))
        self.actionSettings.setIcon(icon)
        self.actionSettings.setObjectName(_fromUtf8("actionSettings"))
        self.actionRegenerateDeterministicAddresses = QtGui.QAction(MainWindow)
        icon = QtGui.QIcon.fromTheme(_fromUtf8("view-refresh"))
        self.actionRegenerateDeterministicAddresses.setIcon(icon)
        self.actionRegenerateDeterministicAddresses.setObjectName(_fromUtf8("actionRegenerateDeterministicAddresses"))
        self.actionDeleteAllTrashedMessages = QtGui.QAction(MainWindow)
        icon = QtGui.QIcon.fromTheme(_fromUtf8("user-trash"))
        self.actionDeleteAllTrashedMessages.setIcon(icon)
        self.actionDeleteAllTrashedMessages.setObjectName(_fromUtf8("actionDeleteAllTrashedMessages"))
        self.actionJoinChan = QtGui.QAction(MainWindow)
        icon = QtGui.QIcon.fromTheme(_fromUtf8("contact-new"))
        self.actionJoinChan.setIcon(icon)
        self.actionJoinChan.setObjectName(_fromUtf8("actionJoinChan"))
        self.menuFile.addAction(self.actionManageKeys)
        self.menuFile.addAction(self.actionDeleteAllTrashedMessages)
        self.menuFile.addAction(self.actionRegenerateDeterministicAddresses)
        self.menuFile.addAction(self.actionJoinChan)
        self.menuFile.addAction(self.actionExit)
        self.menuSettings.addAction(self.actionSettings)
        self.menuHelp.addAction(self.actionHelp)
        self.menuHelp.addAction(self.actionAbout)
        self.menubar.addAction(self.menuFile.menuAction())
        self.menubar.addAction(self.menuSettings.menuAction())
        self.menubar.addAction(self.menuHelp.menuAction())

        self.retranslateUi(MainWindow)
        self.tabWidget.setCurrentIndex(0)
        QtCore.QObject.connect(self.radioButtonSpecific, QtCore.SIGNAL(_fromUtf8("toggled(bool)")), self.lineEditTo.setEnabled)
        QtCore.QObject.connect(self.radioButtonSpecific, QtCore.SIGNAL(_fromUtf8("clicked(bool)")), self.labelSendBroadcastWarning.hide)
        QtCore.QObject.connect(self.radioButtonBroadcast, QtCore.SIGNAL(_fromUtf8("clicked()")), self.labelSendBroadcastWarning.show)
        QtCore.QMetaObject.connectSlotsByName(MainWindow)
        MainWindow.setTabOrder(self.tabWidget, self.tableWidgetInbox)
        MainWindow.setTabOrder(self.tableWidgetInbox, self.textEditInboxMessage)
        MainWindow.setTabOrder(self.textEditInboxMessage, self.radioButtonSpecific)
        MainWindow.setTabOrder(self.radioButtonSpecific, self.radioButtonBroadcast)
        MainWindow.setTabOrder(self.radioButtonBroadcast, self.comboBoxSendFrom)
        MainWindow.setTabOrder(self.comboBoxSendFrom, self.lineEditTo)
        MainWindow.setTabOrder(self.lineEditTo, self.pushButtonLoadFromAddressBook)
        MainWindow.setTabOrder(self.pushButtonLoadFromAddressBook, self.lineEditSubject)
        MainWindow.setTabOrder(self.lineEditSubject, self.textEditMessage)
        MainWindow.setTabOrder(self.textEditMessage, self.pushButtonSend)
        MainWindow.setTabOrder(self.pushButtonSend, self.tableWidgetSent)
        MainWindow.setTabOrder(self.tableWidgetSent, self.textEditSentMessage)
        MainWindow.setTabOrder(self.textEditSentMessage, self.pushButtonNewAddress)
        MainWindow.setTabOrder(self.pushButtonNewAddress, self.tableWidgetYourIdentities)
        MainWindow.setTabOrder(self.tableWidgetYourIdentities, self.pushButtonAddSubscription)
        MainWindow.setTabOrder(self.pushButtonAddSubscription, self.tableWidgetSubscriptions)
        MainWindow.setTabOrder(self.tableWidgetSubscriptions, self.pushButtonAddAddressBook)
        MainWindow.setTabOrder(self.pushButtonAddAddressBook, self.tableWidgetAddressBook)
        MainWindow.setTabOrder(self.tableWidgetAddressBook, self.radioButtonBlacklist)
        MainWindow.setTabOrder(self.radioButtonBlacklist, self.radioButtonWhitelist)
        MainWindow.setTabOrder(self.radioButtonWhitelist, self.pushButtonAddBlacklist)
        MainWindow.setTabOrder(self.pushButtonAddBlacklist, self.tableWidgetBlacklist)
        MainWindow.setTabOrder(self.tableWidgetBlacklist, self.tableWidgetConnectionCount)
        MainWindow.setTabOrder(self.tableWidgetConnectionCount, self.pushButtonStatusIcon)

    def retranslateUi(self, MainWindow):
        MainWindow.setWindowTitle(_translate("MainWindow", "Bitmessage", None))
        self.inboxSearchLineEdit.setPlaceholderText(_translate("MainWindow", "Search", None))
        self.inboxSearchOptionCB.setItemText(0, _translate("MainWindow", "All", None))
        self.inboxSearchOptionCB.setItemText(1, _translate("MainWindow", "To", None))
        self.inboxSearchOptionCB.setItemText(2, _translate("MainWindow", "From", None))
        self.inboxSearchOptionCB.setItemText(3, _translate("MainWindow", "Subject", None))
        self.inboxSearchOptionCB.setItemText(4, _translate("MainWindow", "Message", None))
        self.tableWidgetInbox.setSortingEnabled(True)
        item = self.tableWidgetInbox.horizontalHeaderItem(0)
        item.setText(_translate("MainWindow", "To", None))
        item = self.tableWidgetInbox.horizontalHeaderItem(1)
        item.setText(_translate("MainWindow", "From", None))
        item = self.tableWidgetInbox.horizontalHeaderItem(2)
        item.setText(_translate("MainWindow", "Subject", None))
        item = self.tableWidgetInbox.horizontalHeaderItem(3)
        item.setText(_translate("MainWindow", "Received", None))
        self.tabWidget.setTabText(self.tabWidget.indexOf(self.inbox), _translate("MainWindow", "Inbox", None))
        self.pushButtonLoadFromAddressBook.setText(_translate("MainWindow", "Load from Address book", None))
        self.pushButtonFetchNamecoinID.setText(_translate("MainWindow", "Fetch Namecoin ID", None))
        self.label_4.setText(_translate("MainWindow", "Message:", None))
        self.label_3.setText(_translate("MainWindow", "Subject:", None))
        self.radioButtonSpecific.setText(_translate("MainWindow", "Send to one or more specific people", None))
        self.textEditMessage.setHtml(_translate("MainWindow", "<!DOCTYPE HTML PUBLIC \"-//W3C//DTD HTML 4.0//EN\" \"http://www.w3.org/TR/REC-html40/strict.dtd\">\n"
"<html><head><meta name=\"qrichtext\" content=\"1\" /><style type=\"text/css\">\n"
"p, li { white-space: pre-wrap; }\n"
"</style></head><body style=\" font-family:\'Sans\'; font-size:9pt; font-weight:400; font-style:normal;\">\n"
"<p style=\"-qt-paragraph-type:empty; margin-top:0px; margin-bottom:0px; margin-left:0px; margin-right:0px; -qt-block-indent:0; text-indent:0px; font-family:\'MS Shell Dlg 2\';\"><br /></p></body></html>", None))
        self.label.setText(_translate("MainWindow", "To:", None))
        self.label_2.setText(_translate("MainWindow", "From:", None))
        self.radioButtonBroadcast.setText(_translate("MainWindow", "Broadcast to everyone who is subscribed to your address", None))
        self.pushButtonSend.setText(_translate("MainWindow", "Send", None))
        self.labelSendBroadcastWarning.setText(_translate("MainWindow", "Be aware that broadcasts are only encrypted with your address. Anyone who knows your address can read them.", None))
        self.tabWidget.setTabText(self.tabWidget.indexOf(self.send), _translate("MainWindow", "Send", None))
        self.sentSearchLineEdit.setPlaceholderText(_translate("MainWindow", "Search", None))
        self.sentSearchOptionCB.setItemText(0, _translate("MainWindow", "All", None))
        self.sentSearchOptionCB.setItemText(1, _translate("MainWindow", "To", None))
        self.sentSearchOptionCB.setItemText(2, _translate("MainWindow", "From", None))
        self.sentSearchOptionCB.setItemText(3, _translate("MainWindow", "Subject", None))
        self.sentSearchOptionCB.setItemText(4, _translate("MainWindow", "Message", None))
        self.tableWidgetSent.setSortingEnabled(True)
        item = self.tableWidgetSent.horizontalHeaderItem(0)
        item.setText(_translate("MainWindow", "To", None))
        item = self.tableWidgetSent.horizontalHeaderItem(1)
        item.setText(_translate("MainWindow", "From", None))
        item = self.tableWidgetSent.horizontalHeaderItem(2)
        item.setText(_translate("MainWindow", "Subject", None))
        item = self.tableWidgetSent.horizontalHeaderItem(3)
        item.setText(_translate("MainWindow", "Status", None))
        self.tabWidget.setTabText(self.tabWidget.indexOf(self.sent), _translate("MainWindow", "Sent", None))
        self.pushButtonNewAddress.setText(_translate("MainWindow", "New", None))
        self.tableWidgetYourIdentities.setSortingEnabled(True)
        item = self.tableWidgetYourIdentities.horizontalHeaderItem(0)
        item.setText(_translate("MainWindow", "Label (not shown to anyone)", None))
        item = self.tableWidgetYourIdentities.horizontalHeaderItem(1)
        item.setText(_translate("MainWindow", "Address", None))
        item = self.tableWidgetYourIdentities.horizontalHeaderItem(2)
        item.setText(_translate("MainWindow", "Stream", None))
        self.tabWidget.setTabText(self.tabWidget.indexOf(self.youridentities), _translate("MainWindow", "Your Identities", None))
        self.label_5.setText(_translate("MainWindow", "Here you can subscribe to \'broadcast messages\' that are sent by other users. Messages will appear in your Inbox. Addresses here override those on the Blacklist tab.", None))
        self.pushButtonAddSubscription.setText(_translate("MainWindow", "Add new Subscription", None))
        self.tableWidgetSubscriptions.setSortingEnabled(True)
        item = self.tableWidgetSubscriptions.horizontalHeaderItem(0)
        item.setText(_translate("MainWindow", "Label", None))
        item = self.tableWidgetSubscriptions.horizontalHeaderItem(1)
        item.setText(_translate("MainWindow", "Address", None))
        self.tabWidget.setTabText(self.tabWidget.indexOf(self.subscriptions), _translate("MainWindow", "Subscriptions", None))
        self.label_6.setText(_translate("MainWindow", "The Address book is useful for adding names or labels to other people\'s Bitmessage addresses so that you can recognize them more easily in your inbox. You can add entries here using the \'Add\' button, or from your inbox by right-clicking on a message.", None))
        self.pushButtonAddAddressBook.setText(_translate("MainWindow", "Add new entry", None))
        self.tableWidgetAddressBook.setSortingEnabled(True)
        item = self.tableWidgetAddressBook.horizontalHeaderItem(0)
        item.setText(_translate("MainWindow", "Name or Label", None))
        item = self.tableWidgetAddressBook.horizontalHeaderItem(1)
        item.setText(_translate("MainWindow", "Address", None))
        self.tabWidget.setTabText(self.tabWidget.indexOf(self.addressbook), _translate("MainWindow", "Address Book", None))
        self.radioButtonBlacklist.setText(_translate("MainWindow", "Use a Blacklist (Allow all incoming messages except those on the Blacklist)", None))
        self.radioButtonWhitelist.setText(_translate("MainWindow", "Use a Whitelist (Block all incoming messages except those on the Whitelist)", None))
        self.pushButtonAddBlacklist.setText(_translate("MainWindow", "Add new entry", None))
        self.tableWidgetBlacklist.setSortingEnabled(True)
        item = self.tableWidgetBlacklist.horizontalHeaderItem(0)
        item.setText(_translate("MainWindow", "Name or Label", None))
        item = self.tableWidgetBlacklist.horizontalHeaderItem(1)
        item.setText(_translate("MainWindow", "Address", None))
        self.tabWidget.setTabText(self.tabWidget.indexOf(self.blackwhitelist), _translate("MainWindow", "Blacklist", None))
        item = self.tableWidgetConnectionCount.horizontalHeaderItem(0)
        item.setText(_translate("MainWindow", "Stream #", None))
        item = self.tableWidgetConnectionCount.horizontalHeaderItem(1)
        item.setText(_translate("MainWindow", "Connections", None))
        self.labelTotalConnections.setText(_translate("MainWindow", "Total connections: 0", None))
        self.labelStartupTime.setText(_translate("MainWindow", "Since startup at asdf:", None))
        self.labelMessageCount.setText(_translate("MainWindow", "Processed 0 person-to-person message.", None))
        self.labelPubkeyCount.setText(_translate("MainWindow", "Processed 0 public key.", None))
        self.labelBroadcastCount.setText(_translate("MainWindow", "Processed 0 broadcast.", None))
        self.labelLookupsPerSecond.setText(_translate("MainWindow", "Inventory lookups per second: 0", None))
        self.tabWidget.setTabText(self.tabWidget.indexOf(self.networkstatus), _translate("MainWindow", "Network Status", None))
        self.menuFile.setTitle(_translate("MainWindow", "File", None))
        self.menuSettings.setTitle(_translate("MainWindow", "Settings", None))
        self.menuHelp.setTitle(_translate("MainWindow", "Help", None))
        self.actionImport_keys.setText(_translate("MainWindow", "Import keys", None))
        self.actionManageKeys.setText(_translate("MainWindow", "Manage keys", None))
        self.actionExit.setText(_translate("MainWindow", "Quit", None))
        self.actionExit.setShortcut(_translate("MainWindow", "Ctrl+Q", None))
        self.actionHelp.setText(_translate("MainWindow", "Help", None))
        self.actionHelp.setShortcut(_translate("MainWindow", "F1", None))
        self.actionAbout.setText(_translate("MainWindow", "About", None))
        self.actionSettings.setText(_translate("MainWindow", "Settings", None))
        self.actionRegenerateDeterministicAddresses.setText(_translate("MainWindow", "Regenerate deterministic addresses", None))
        self.actionDeleteAllTrashedMessages.setText(_translate("MainWindow", "Delete all trashed messages", None))
        self.actionJoinChan.setText(_translate("MainWindow", "Join / Create chan", None))

import bitmessage_icons_rc

########NEW FILE########
__FILENAME__ = bitmessage_icons_rc
# -*- coding: utf-8 -*-

# Resource object code
#
# Created: Sa 21. Sep 13:45:58 2013
#      by: The Resource Compiler for PyQt (Qt v4.8.4)
#
# WARNING! All changes made in this file will be lost!

from PyQt4 import QtCore

qt_resource_data = "\
\x00\x00\x03\x66\
\x89\
\x50\x4e\x47\x0d\x0a\x1a\x0a\x00\x00\x00\x0d\x49\x48\x44\x52\x00\
\x00\x00\x10\x00\x00\x00\x10\x08\x06\x00\x00\x00\x1f\xf3\xff\x61\
\x00\x00\x00\x19\x74\x45\x58\x74\x53\x6f\x66\x74\x77\x61\x72\x65\
\x00\x41\x64\x6f\x62\x65\x20\x49\x6d\x61\x67\x65\x52\x65\x61\x64\
\x79\x71\xc9\x65\x3c\x00\x00\x03\x08\x49\x44\x41\x54\x78\xda\x84\
\x53\x6d\x48\x53\x51\x18\x7e\xce\xfd\xd8\x75\x9b\x8e\xdc\x2c\xdd\
\x4c\x5d\x4e\xa7\xc9\xe6\xb7\xf6\x61\x61\x11\x14\x52\x16\xf5\xc7\
\x0a\x0b\xa2\x3f\x41\x51\x41\x61\x7f\x0a\x84\xa2\x9f\xfd\xeb\x67\
\x7f\xfa\x51\x44\x50\x91\x14\x15\x5a\x14\x41\x25\x6d\x44\x59\x68\
\x69\xd9\x74\xa6\x6d\xd7\x7d\x38\xb6\xdd\x6d\x77\xa7\x73\x2d\x4d\
\x84\xe8\x81\x87\xf7\x7d\xef\x7b\xde\xe7\xbe\xe7\x9c\xf7\x10\x30\
\x48\x84\x20\x4f\xb3\xf8\x8b\xb3\x1b\xe9\xbc\xe5\x38\x14\xb3\x74\
\x2f\x73\xab\x18\x47\x28\x45\x6f\x36\x0b\xff\xc2\x3a\xde\xc6\xb2\
\x06\xcd\x61\x24\x4b\x04\xbe\x87\x09\x48\x82\x89\x8a\xb8\x62\xaf\
\x76\x75\x5a\x4a\xcb\x9d\x31\x85\xae\x9d\x0d\xce\x15\x7c\xf1\xa3\
\xef\x67\x18\xd0\xc8\xe1\x1f\xf0\xcf\x01\x43\x53\xc4\xf1\x33\x04\
\x57\x20\x12\x29\xcc\x31\x5b\x84\x4d\x7b\xf6\x18\xb5\x78\xcc\x0f\
\x07\x23\x34\x0a\xcb\xea\x0a\x19\x4f\x32\xda\x19\xc7\x53\x04\x91\
\x99\x10\xc4\xde\xd3\xa7\x61\x30\x1a\xa1\xb2\xde\xb5\x98\xe7\xb0\
\x85\xe5\xc7\xb4\x02\x81\x2e\xa9\x66\xfe\xb9\x86\xd6\xd6\xfd\xee\
\xba\x3a\xcb\x3b\x8f\x47\x9e\x78\xe7\x8d\xc5\x13\x88\x4a\x3a\x1d\
\x94\x78\x1c\x82\x28\x22\xae\x6d\x8b\x47\x23\x5b\x7e\x6d\x5e\xa0\
\xdd\xf9\x77\xe7\xcf\x3e\xd3\x0d\xbd\xa7\x3a\xac\x2e\xa7\x15\x43\
\x9f\x6d\xd6\xae\x43\xde\xb0\x51\x44\x74\x6c\x78\x18\xf6\x8a\x0a\
\x68\x96\xc5\x1a\x4a\x16\x6a\x84\xad\xce\xc5\xfa\xae\xc1\x69\x53\
\x65\xbd\xdb\x8e\x74\x32\x09\xcd\xea\xf2\x4c\xb9\x0e\x5b\x94\x0c\
\xdc\xba\xe9\x6d\xda\xbe\xa3\xd1\xf3\xe4\xb1\x37\xf7\xb7\x40\xc1\
\xa2\x40\x26\xbb\x28\xc0\x75\xd5\x29\x23\xc9\xb9\xb9\x8d\x99\x74\
\x1a\x2a\xe3\xae\xfa\xf4\xc7\xf1\x92\xa2\x60\xce\xc4\x0f\x4b\x85\
\xb3\x0a\xcf\xfb\x6e\xd2\x57\xdd\x35\x1f\x73\x43\xc9\x47\x33\x25\
\x26\x4c\x15\xe7\x82\x27\xb5\x07\x41\x09\x87\x7c\x75\x66\xc8\x28\
\x66\xaa\x4b\x2a\xdd\x4d\xec\x42\x85\xf0\x6c\x20\xf5\x32\x3c\xfa\
\x4d\x3a\xd1\xe3\xd4\xd7\xb4\x54\xa5\x14\x17\xa6\xdb\xaa\x6d\x85\
\x5b\xda\x0b\x9e\xe6\x04\x12\xe1\x3c\xc1\x8e\x2c\xfd\xc2\x7f\x6d\
\xba\x8c\x41\x7d\x07\x1e\x99\x8e\x40\xa5\x24\xc0\x7d\xb8\xb1\x3e\
\x96\x26\xb6\x57\xaf\x07\xfc\x74\x77\x77\x45\xc1\x6a\x87\x79\x2a\
\x91\xc0\xd9\x8e\xa3\xb8\x3d\xe5\x41\xe9\xaa\x62\x93\xcb\x5c\x5e\
\x6b\xa0\xba\x35\xdf\x02\x93\xe2\x92\x39\xa0\xcd\xfd\xa6\xc3\x3b\
\x83\xf2\x2c\x69\x6c\x6e\x41\x24\x1a\x13\xef\x8f\xb4\xbe\x1f\xf7\
\x49\x93\x49\x76\x26\xb2\x2c\x43\xb3\x1a\xd4\x54\x46\xaa\x36\x97\
\xb9\x69\x54\x69\x23\x7c\x77\xdf\x0a\x70\xe2\x7e\x83\x24\xd4\x1c\
\xeb\x74\xef\x5b\x19\x19\x2a\xb6\x4b\x32\xc6\x15\x0b\x82\xf9\x95\
\xa1\xab\x0f\xfb\x3d\x49\xce\x17\x6b\x19\xf6\x0e\x0c\x6e\xf0\x6f\
\xa3\x69\x55\x0f\x45\x35\xd0\x74\x36\x07\xa3\xd1\x27\x84\x3f\x70\
\xe7\x4c\xe7\xfa\xf2\xee\xa6\x2a\xeb\x5a\x4b\x7e\x9e\xe4\xf3\x4d\
\xe3\xd2\xde\x52\x9c\xbf\xeb\x43\x59\x99\x15\x72\x28\x9a\x7a\xfb\
\xe9\xfb\x68\x5f\xff\xeb\x7b\xea\x83\x93\xd7\x97\x0d\x9e\xcc\x41\
\x89\x36\xd7\xda\xcd\xf5\xd9\x4c\x76\xfe\x2d\x2d\x6f\x97\xaa\xd0\
\xd5\x39\xac\x35\x90\x4c\xe5\xfc\xe6\x9e\x11\xed\x41\x2d\x61\x90\
\xf0\xf5\x87\x2e\xc0\xda\xd0\x4e\x79\x29\x41\x05\x7d\x0c\x82\x3e\
\xde\x36\x7d\xf5\xcd\xcb\xa2\xe3\xeb\x48\x26\x69\x20\x99\x84\x91\
\xa8\x8a\x1e\x3f\xbc\x2f\xe8\xec\xe8\x45\x1a\x99\x04\x8d\x4c\x2c\
\xb6\x40\xfe\x0c\x85\x05\xff\x87\xac\xfd\x71\xf9\xc7\x5f\x02\x0c\
\x00\x00\x31\x44\x70\x94\xe4\x6d\xa8\x00\x00\x00\x00\x49\x45\x4e\
\x44\xae\x42\x60\x82\
\x00\x00\x02\xaf\
\x89\
\x50\x4e\x47\x0d\x0a\x1a\x0a\x00\x00\x00\x0d\x49\x48\x44\x52\x00\
\x00\x00\x10\x00\x00\x00\x10\x08\x06\x00\x00\x00\x1f\xf3\xff\x61\
\x00\x00\x00\x19\x74\x45\x58\x74\x53\x6f\x66\x74\x77\x61\x72\x65\
\x00\x41\x64\x6f\x62\x65\x20\x49\x6d\x61\x67\x65\x52\x65\x61\x64\
\x79\x71\xc9\x65\x3c\x00\x00\x02\x51\x49\x44\x41\x54\x78\xda\x9c\
\x53\xcf\x6b\x13\x51\x10\xfe\x36\xfb\x62\x8d\x69\x48\x62\x9b\x18\
\x8d\xab\x5d\xd3\x84\xa2\x10\xbd\x48\x0f\x62\xa9\xd8\x93\xe0\x49\
\x0f\xa5\x20\x52\xb0\xe0\x7f\xe0\x45\x3c\xf5\xa6\x77\x7b\xe8\x55\
\x28\x41\x3d\x78\x28\x7a\xf0\x47\x51\xa4\xbd\x58\x0d\xa8\x60\x5a\
\x13\x51\xd0\x43\x89\x69\xf3\x63\xb3\xc9\xee\x3e\x67\x9e\xd9\xa2\
\x08\x4a\x1d\x18\xde\xdb\x99\xf9\xbe\xf7\xcd\x7b\xb3\xda\x8d\x85\
\x05\xb0\x69\x9a\x76\x9e\x96\xfd\xf8\xbb\x3d\x71\x1c\x67\xad\xdb\
\xe9\xe0\xdc\xf3\x19\x48\x0a\x08\xd7\x75\xfd\xe4\x81\xeb\x93\x93\
\x73\x0e\x7d\x73\xc2\x95\x12\x5d\xda\x77\x3d\x4f\xed\x2b\x95\x0a\
\x1e\x15\x8b\x57\xa5\x94\x1a\xa5\x4b\x3e\x28\x30\xf1\xf8\x32\xcc\
\xb5\x7b\x20\x56\x4d\x72\xb1\xe3\xc0\xe9\x76\xe1\xf6\xbc\xd3\x6e\
\xc3\x6a\x36\xd1\x68\x34\x30\x3b\x35\x35\x47\xb9\xb3\x44\x92\xf5\
\x09\x04\xfb\xf0\xa7\x07\x57\x5a\x32\x78\x41\xd3\x2e\xe1\xc5\xea\
\x2a\x3c\x22\x8a\xc5\x62\x68\xb5\x5a\x38\x3e\x32\xa2\x0a\xab\xd5\
\x2a\xee\x2c\x2e\x22\x9f\x4c\xde\x5e\x29\xcc\x3e\x85\x8e\x02\x85\
\xe7\x05\xa9\x1b\x44\x40\xcf\x65\x8f\x9e\x9c\x60\x6d\x99\x4c\x06\
\x74\x82\x22\x89\xc7\xe3\x08\xea\xba\x22\x38\x35\x3a\x8a\x0e\xa9\
\x0b\x85\xc3\x18\x68\x5d\x3c\x23\x1f\xbe\x7a\x2d\x3d\x77\x50\xb8\
\x12\xc6\x5e\xe3\xd8\xf0\x26\x5d\x4c\x40\xd3\x54\xaf\xd1\x68\x54\
\x9d\xc8\x24\x1f\x89\x8c\x09\x39\xc6\x8a\x4e\xe4\xf3\xb0\x6d\x1b\
\x49\xc2\x54\x2b\x45\x43\xb8\x1e\x0e\xed\x8e\x26\xf7\x59\x56\x1b\
\xbf\x2a\xe0\xd3\x7d\x25\xb2\x47\xe2\x2b\xe2\x5a\xc6\x30\x96\x14\
\xc8\xa1\x60\x38\x16\x6a\x12\x3b\x3d\x25\xca\xe5\xf2\x36\xc0\x57\
\xc2\x2b\x7f\xb3\x82\xc3\xa9\x14\xb8\x96\x31\x8c\x15\x8e\x87\x5c\
\x24\x65\x26\xac\xf7\x75\x94\x0b\xd7\x30\x40\xb7\xde\x97\x1b\x47\
\x5f\x76\xec\x37\x25\xf6\x87\x25\x04\x4b\x4b\xf8\xba\xbe\x07\x56\
\xdb\x46\xc4\x34\x13\x8c\xe5\x16\x44\x24\x91\x4e\x4d\x27\x7e\x3e\
\x0b\x4f\xd2\xca\xf2\x7d\x38\xc2\x50\x40\x7e\x0d\x6e\x63\x73\xf9\
\x2e\x4e\x8f\x8d\xab\x9a\x69\x53\x2d\x29\xc6\xb2\x02\xb1\xb5\xb1\
\x41\x7d\x59\x2a\xda\x4f\x00\x23\x9d\xc6\x97\x67\x37\x15\x41\x93\
\x62\x3c\x58\xe6\x90\x89\x66\xbd\x8e\x46\xad\xa6\xea\x42\xa1\x10\
\x1c\x45\xe0\x4a\xe1\xf0\xf0\x90\xb3\xd5\x88\xcc\xc8\x66\x71\xd0\
\x3c\xf2\xc7\x1c\x7f\x2e\x6d\x0f\xa0\xaa\x67\xac\xe8\x7a\x08\x76\
\x3a\x34\x71\xe4\xbe\xad\xbf\x7d\x87\x7f\x99\xae\x0b\x30\x56\x34\
\x6c\xf4\x4b\xc9\x5a\x74\xec\xc4\x18\xc3\x58\xf1\xe6\x9b\xac\x6c\
\xcd\xdf\x7a\x89\xff\xb0\xf2\x77\x54\x78\x76\x76\x91\xc7\x7a\xff\
\xc5\x4e\x8c\x2f\xad\xf6\x43\x80\x01\x00\xc1\x52\x4e\xcc\x97\x5f\
\x6c\x5a\x00\x00\x00\x00\x49\x45\x4e\x44\xae\x42\x60\x82\
\x00\x00\x02\xcc\
\x89\
\x50\x4e\x47\x0d\x0a\x1a\x0a\x00\x00\x00\x0d\x49\x48\x44\x52\x00\
\x00\x00\x10\x00\x00\x00\x10\x08\x06\x00\x00\x01\x68\xf4\xcf\xf7\
\x00\x00\x00\x06\x62\x4b\x47\x44\x00\xff\x00\xff\x00\xff\xa0\xbd\
\xa7\x93\x00\x00\x00\x09\x70\x48\x59\x73\x00\x00\x0b\x13\x00\x00\
\x0b\x13\x01\x00\x9a\x9c\x18\x00\x00\x02\x6c\x49\x44\x41\x54\x38\
\xcb\x4d\xd2\xbd\x6b\xdd\x65\x14\x07\xf0\xcf\xaf\xb9\x49\x9a\x10\
\x69\x08\x06\x6a\x2c\x82\xf4\x25\x2e\xed\x50\x87\x4e\x85\x2e\x42\
\xb2\x34\xe0\xe4\x58\x10\xea\x58\x69\x57\x47\x57\x83\xd2\x49\xc1\
\xad\xfe\x01\xba\x28\xb8\xa8\x93\x83\xa0\x4b\x41\x89\x10\x1b\x43\
\x20\x37\x37\xf7\xe6\xbe\xfe\xee\xef\x2d\xc7\xe1\xb9\x6a\x1f\x38\
\x1c\x9e\xf3\x7c\xbf\xe7\x7c\x9f\x73\x4e\x16\xb7\x6e\x71\xf5\x6a\
\x2d\xae\x5f\x2f\x82\x10\x0f\x1e\x6c\xc6\x8d\x1b\xc4\xc5\x8b\xf1\
\x17\x21\xee\xdf\xbf\x19\x77\xee\x44\xac\xad\x45\xcc\xcf\x47\x36\
\xc4\x11\x91\xe3\x67\x64\xb1\xb3\xc3\xa5\x4b\xbf\xd8\xdf\xff\xd1\
\xf3\xe7\x4f\xc4\xce\x4e\xc4\x95\x2b\x11\xab\xab\x31\xa0\x16\x1b\
\x1b\x11\x44\x45\xfc\x40\x64\x07\xc4\x18\x2f\xb0\xc7\x6e\x16\xdb\
\xdb\xac\xaf\x7f\xab\x69\xb6\x74\x3a\x9c\x9d\x31\x1e\x27\xdf\xed\
\x2e\xb6\x8c\xc7\x7b\x8e\x8f\xaf\x39\x3c\xe4\xf4\x94\xf3\x73\xd0\
\x8f\xd0\xa6\x10\xcb\xcb\x4f\x83\x28\x67\x56\x10\x6d\xe2\x27\xe2\
\x19\x91\x75\x92\x6e\x6d\x86\x7d\x56\x06\xe8\xa2\xe6\x83\xd7\xf9\
\x22\x8b\x7b\xf7\xd8\xd8\x60\x71\xf1\x13\x79\xfe\xc8\xd9\xd9\x6f\
\xda\xed\xf7\xb4\xdb\x7f\xea\xf5\xb4\x5c\xbe\xbc\x60\x7e\xbe\xd0\
\xef\xd3\xe9\x30\x1a\xbd\x6d\x30\xd8\x33\x99\x7c\xa7\x28\xb6\x5b\
\xca\x72\xa2\xdb\xe5\xe0\x20\x89\xac\x6b\xea\x5a\x33\x1c\x6e\x9d\
\xb1\xd9\x72\x7c\x3c\xa7\xdd\xe6\xf0\x90\xe9\x14\x54\x11\x4e\xd0\
\xe1\xab\x96\xa3\x23\xfa\xfd\xf4\x18\x21\x90\xe3\x24\x89\x7f\x23\
\x8b\x56\x2b\x9a\xba\x56\x63\x0e\x25\xfe\xc6\xef\x18\xf0\x59\xd6\
\xe6\xd3\x21\x8f\x4a\x34\x29\xe8\x45\xfa\xb6\x55\xb2\xd6\x84\x0f\
\x8f\xd9\xef\x26\xa0\x5e\x02\x8d\x96\x79\xe5\x35\x64\x71\xf7\x2e\
\x6b\x6b\xac\xac\xb0\xb0\xf0\x58\x96\x7d\xac\xae\x97\x14\x45\xd2\
\x35\x9d\x52\x14\xe4\x39\x93\x49\x6e\x32\xf9\xc8\x64\xb2\x2b\xcf\
\x29\xcb\xd9\x42\x2c\x2d\x7d\xee\xc2\x85\x87\xaa\x2a\x01\x87\x43\
\x46\xa3\x44\x2e\x4b\x9a\x26\x59\x59\xa6\x58\x9e\x8b\xe9\x74\xb7\
\xe2\x49\x4b\x51\x3c\x55\x96\x0f\x4d\xa7\x89\xd8\xeb\xa5\x4d\xc8\
\x73\xaa\x8a\x08\x20\xcb\xa8\x6b\x65\x84\x1c\x13\x1e\x17\xcc\x65\
\x71\xfb\x76\xa1\xae\x17\xe4\x79\x5a\xa3\xe1\x30\x91\x9b\xe6\x7f\
\x32\xff\xb5\x77\x34\x6b\xd4\x20\x25\x39\x69\x39\x3a\x3a\x50\x55\
\xd7\x54\x55\xaa\x58\x96\xa2\x69\xbc\x7c\xce\x67\xed\x1f\xa6\xe1\
\xe9\xe2\x0c\x05\x07\x59\xc3\xcd\x29\xbf\x56\xcc\xd5\xb3\x4a\x90\
\xcd\x7c\x83\xe9\x4b\xe4\x53\xf4\x53\xc2\x66\x81\xb7\xb2\x6e\x92\
\xb5\x30\xe6\xeb\x9c\xad\x7f\xe7\xd9\xa0\x4a\x55\xe4\x33\xc9\xa3\
\xd9\x1d\xdf\x2c\xf3\xee\xab\x34\x59\x0f\xe3\x19\xa0\x9f\xfc\x9b\
\x23\xde\x1f\xf1\x4e\xce\x66\x91\x12\xfd\xd1\xf0\xfd\x1c\x5f\x2e\
\xb1\x7f\x09\xeb\x33\xfb\x07\x6a\x4f\x76\xe7\x35\x05\x41\x4b\x00\
\x00\x00\x00\x49\x45\x4e\x44\xae\x42\x60\x82\
\x00\x00\x02\x24\
\x89\
\x50\x4e\x47\x0d\x0a\x1a\x0a\x00\x00\x00\x0d\x49\x48\x44\x52\x00\
\x00\x00\x10\x00\x00\x00\x10\x08\x06\x00\x00\x00\x1f\xf3\xff\x61\
\x00\x00\x00\x19\x74\x45\x58\x74\x53\x6f\x66\x74\x77\x61\x72\x65\
\x00\x41\x64\x6f\x62\x65\x20\x49\x6d\x61\x67\x65\x52\x65\x61\x64\
\x79\x71\xc9\x65\x3c\x00\x00\x01\xc6\x49\x44\x41\x54\x78\xda\x8c\
\x53\x3d\x4b\x03\x41\x10\x7d\xd9\x3b\xf5\x44\x45\x8b\x44\x34\xa2\
\xc4\x42\x49\x2b\xe8\xcf\xb0\xf3\x07\x28\xd6\x82\x9d\x20\x58\x88\
\x0a\x36\x82\x8d\x95\xa0\x58\x0b\x16\xda\x8b\xd8\x08\x09\x44\x0b\
\x8b\x54\x22\x7e\x44\x10\x41\x42\xce\xe4\x2e\xb7\x1f\xce\x9c\xe6\
\xcb\x5c\xc0\xe5\x06\x6e\xdf\xbe\xf7\x66\x76\x76\x37\x96\xdd\x05\
\x62\xc0\x12\x80\x14\xfe\x3f\x1e\x0d\x70\x3c\xbb\x66\x60\x1b\xfa\
\xa3\x6f\x72\x6e\xf5\x62\x03\x5a\x03\x4a\x75\x96\x59\x16\x20\x04\
\xb2\xfb\xf3\x5b\x35\x48\x84\x06\x06\xe2\x25\x93\x01\x1b\x18\x29\
\x61\xaa\x7e\x7b\x10\xce\xeb\xcc\x63\x3e\xeb\x42\x03\xc5\x49\x35\
\x44\x6f\x3c\x8e\xfb\xcb\x4b\xca\x22\x60\x44\x7b\x30\xce\xeb\xcc\
\x63\x3e\xeb\x78\xd8\xfa\xc7\xc9\x1a\x1a\x4e\xa0\xe2\x96\x70\x73\
\x7e\x51\xaf\xd8\xf3\x3c\x38\x8e\x53\x9f\x4f\x4c\x4f\x81\x79\xa4\
\xb1\x6a\x98\xfd\xeb\x24\x0c\xed\x7d\x38\x39\x1a\x46\x08\x74\x75\
\xe3\x29\x9f\xc7\x44\x3a\x0d\x1d\x54\xeb\x26\xcc\xe3\x0a\xfe\x1a\
\x58\x5a\x05\x50\x32\x68\x34\x4c\xc4\x30\xd0\xd7\x87\x28\x9c\x34\
\x56\xbb\x81\x54\xd0\xdc\xa8\xdf\x11\x13\x16\x1d\x08\x63\x11\x78\
\x94\x81\x51\x92\xb2\x35\x88\x42\x59\x90\x94\x39\x0a\xef\x50\x41\
\x00\xdd\x54\xaa\x1f\x28\x2c\xf6\x6c\xa2\xfa\xa6\xa8\x99\x92\x22\
\x80\xef\x2b\x64\xa6\x8f\x5a\x0d\xa4\xaa\x19\x48\xda\x6b\x23\x53\
\xd9\xf5\x70\x32\x53\x6e\xba\x45\x22\x0c\xf7\xae\x04\xd2\x44\x54\
\x10\x96\xda\xa8\xc0\xfd\x2c\xc2\xae\x54\x90\xcb\xe5\x90\x48\x24\
\xc2\x7e\xa4\x52\x29\xe8\x62\xa9\x53\x0f\xa8\x59\x4d\xd7\xd8\x25\
\x62\x77\xb9\x8c\x34\x1d\x63\xbd\x2a\x9a\xeb\xd2\x57\xab\xc1\xdd\
\x23\x90\x4e\xc2\x79\x79\x7a\xa5\x9b\xaa\x9a\x7a\xe0\xe3\xe3\x74\
\xa5\xed\x39\x0c\xc6\x87\xe0\x55\xe1\xe4\x0b\xc0\x02\x1b\xec\x9c\
\x61\xf0\x60\x19\xfd\xe3\xe3\xc9\xd6\xf3\x1e\x1b\x89\x7e\x4f\x76\
\x17\x6e\xaf\xd1\xcf\xba\x6d\xa0\x68\xb3\xe9\xfd\x33\x0a\x87\x7b\
\xeb\x57\xff\x7d\xcb\x0f\xef\x28\xb0\x8e\xa2\xf8\x2d\xc0\x00\x14\
\x2c\x1a\x71\xde\xeb\xd2\x54\x00\x00\x00\x00\x49\x45\x4e\x44\xae\
\x42\x60\x82\
\x00\x00\x06\xe3\
\x89\
\x50\x4e\x47\x0d\x0a\x1a\x0a\x00\x00\x00\x0d\x49\x48\x44\x52\x00\
\x00\x00\x90\x00\x00\x00\x90\x08\x06\x00\x00\x00\xe7\x46\xe2\xb8\
\x00\x00\x00\x04\x73\x42\x49\x54\x08\x08\x08\x08\x7c\x08\x64\x88\
\x00\x00\x00\x09\x70\x48\x59\x73\x00\x00\x0e\xc4\x00\x00\x0e\xc4\
\x01\x95\x2b\x0e\x1b\x00\x00\x06\x85\x49\x44\x41\x54\x78\x9c\xed\
\x9d\x4b\x72\xe3\x38\x10\x44\xc1\x8e\x5e\xf8\x3c\x3a\x8e\x0f\xa8\
\xe3\xf8\x3c\xda\x79\x16\x0e\x4c\xd3\x10\x89\x6f\x7d\xb2\x0a\xf5\
\x96\x0e\x59\x2c\x24\x12\x29\x90\x20\xc1\xe3\xf3\xe3\xeb\x3b\xa5\
\x94\x9e\xaf\xc7\x91\x0c\x92\xeb\xb7\x8c\x65\xed\x8f\xb2\x03\x2c\
\x37\x46\xbb\x86\x59\xac\x69\x7e\xd6\xfa\x28\xff\x90\xb1\xd6\xa8\
\x8c\x45\x23\x59\xd1\xfa\x4a\xdb\x5b\x03\x65\xac\x34\xae\xc4\x92\
\x91\xd0\x35\xbe\xd3\xf2\xf9\x7a\x1c\x47\xeb\x43\xe7\x0f\x53\x17\
\x26\x81\x05\x23\xa1\x6a\xdb\xe3\x89\x6e\x03\x9d\xff\x69\xb5\x30\
\x0d\x90\x8d\x84\xa6\x69\x8f\x56\xb9\xe6\x5f\x85\x8f\x88\x8c\xd6\
\xe8\x5e\x10\x8d\x84\xa2\xe5\x4c\xff\x4f\x1b\xa8\xfc\x22\x6b\x20\
\x19\x49\x5b\xc3\x51\x2d\xce\xf5\xbe\x15\x3e\x2b\xac\xb6\x08\xb3\
\x20\x18\x49\x4b\x3b\x8a\xbe\x26\x33\xd0\xd5\x97\x5b\x42\xd3\x48\
\xd2\x9a\xad\xb4\xb5\xac\xf5\xb2\x70\x0a\x31\xc3\x48\xfd\x48\x69\
\xc5\xd1\xaf\x6c\x06\xba\x3b\xa0\x15\x24\x8d\xc4\xad\x11\x55\x5b\
\xae\xea\xbc\x2d\x9c\x5a\x40\x8b\x46\x92\x32\x11\x97\x36\x12\x7d\
\xf8\x97\xf2\x00\x35\x2c\x2d\xda\x5e\xad\x0f\x22\x4c\xb6\x7b\xe1\
\xa8\xf5\xae\xdf\xaa\x9d\xc9\x29\x1a\xa2\x91\x6a\x97\xec\x5b\x9f\
\x59\x81\x4a\x0b\x8d\xfe\x12\x4b\xa0\x12\xa4\x44\x9a\xb9\x80\x86\
\x94\x48\xdc\xb5\xd4\xfa\xa8\xd9\x79\xd6\xe7\x01\x35\x28\x96\x6f\
\x34\xcf\x58\x11\xfa\x46\x2d\x81\x4a\x24\x13\x89\xe3\x2c\x53\x32\
\x91\x90\xce\x10\xbb\x3a\xcb\xcb\xb5\x11\x89\xab\xec\x9c\xcb\x41\
\x88\xfd\x00\x93\x40\x25\x94\x89\xa4\x31\x62\x29\x8f\xa9\x35\xdf\
\xea\xd1\x9e\x75\x64\x51\x32\x63\x24\xce\x0b\x68\x94\x35\xdc\x7d\
\xbf\x05\xcd\x61\x13\xa8\x64\x24\x91\xb4\x85\x3f\x33\x93\x48\x08\
\xf5\xf7\x0e\x9a\xa1\x91\x85\xd0\xb0\xcc\x55\x03\xb9\xea\xa3\x9c\
\x8f\xd5\xee\x3f\x47\xd7\xf7\x0a\xb3\x06\xca\x48\x5c\x25\x46\x9a\
\xd0\x4b\x30\xd2\xde\x3f\x5c\x5f\x2c\x05\x72\x47\xd4\x40\xd4\x72\
\x86\x21\x03\xa1\x62\xad\x33\x3e\x3f\xbe\xbe\x51\x8d\x3f\xaa\xe5\
\xb0\x81\x50\x3b\xeb\xf9\x7a\x1c\xa8\xb5\x65\x90\x8d\x33\x8b\x99\
\xb3\xb0\x5e\x10\x27\xa4\x48\xb5\xd4\x98\x19\x80\x53\x3f\x61\xe8\
\x23\x3d\x25\x8c\x44\xf2\x98\x38\x25\xee\x12\xa8\xc4\xfb\x5a\x15\
\x15\xb3\x83\x6d\x7a\x12\xad\x3d\xba\x47\x91\x48\xa4\x1d\x12\xa7\
\xc4\x7d\x02\x95\x78\x5a\xab\xa2\x62\x65\x60\x2d\x9d\xc6\x5b\x4b\
\xa1\x33\x14\x89\xb4\x63\xe2\x94\x6c\x97\x40\x25\x56\xd7\xaa\xa8\
\x58\x1d\x44\xcb\x17\x12\x2d\xa7\xd0\x99\x9e\x44\x8a\xc4\x79\x07\
\xfe\x66\xee\x1e\x76\x5b\xab\xa2\x82\x42\x37\x92\xa5\x0c\x2f\x29\
\x74\xc6\x63\x9b\x38\xd8\x7e\x0e\x74\x45\xa4\x4f\x3f\x64\x8b\xa9\
\x1e\x46\x6c\xcc\x71\xc6\x89\x04\x4a\x7b\x24\xce\x19\xca\xc1\x4e\
\x7a\x3b\x87\xb5\x14\x8a\xc4\x59\x67\xcb\x04\xda\xd9\x34\xd4\x83\
\x9c\xfc\x86\x32\xe4\x14\x8a\xc4\xa1\x67\x8b\x04\x0a\xd3\xfc\xc0\
\x31\xb8\x59\x6e\x69\x45\x49\xa1\x48\x1c\x7e\x5c\x26\x50\x98\xe6\
\x1d\xae\x41\xcd\x76\x53\xbd\xd6\x6e\x1b\x61\x1e\x59\x4c\xec\xcd\
\x17\xac\xc1\x39\x98\xff\x46\x27\x07\x2b\xb8\x9c\x03\x59\xc3\xca\
\x26\x9b\x57\xdf\xcf\xfe\x60\x21\xca\x19\x19\x32\x12\x1d\xcd\xf5\
\xdd\xac\x06\x0a\xf3\xe8\x21\x65\x4a\x91\x47\x9b\xc3\x48\x6d\xac\
\xa6\x90\xab\xd3\xf8\xe0\x07\x49\x33\x8a\x6d\xae\x10\x86\x6a\x63\
\x31\x85\x5c\x2f\x65\xec\x88\xb4\x09\x45\xb7\x77\x09\x63\xb5\xb1\
\x96\x42\x5b\xdd\xce\xe1\x1d\x0d\xf3\x89\x6f\x30\x15\x06\x6b\x63\
\x29\x85\xb6\xbe\xa5\xd5\x13\x5a\xa6\x53\xd9\xe2\x2e\x8c\xd6\xc6\
\x4a\x0a\xc5\x63\x3d\x0e\xd0\x34\x9b\xda\x26\x9b\x61\xb8\x36\x16\
\x52\x28\x1e\x6d\x36\x8e\xb6\xc9\x54\xb7\xf9\x0d\xe3\xb5\xd1\x36\
\x48\x8b\xd8\xde\xc5\x30\x08\xe6\x52\xdf\x68\x3c\x0c\xd8\x06\xc1\
\x28\x77\x6c\xbb\xc5\x9d\x75\x50\x4c\xa5\x9e\x40\x29\x85\x11\x7b\
\x40\x31\x4c\xc9\x36\xdb\xfc\x7a\x02\xc9\x4c\x10\x09\x94\x52\x18\
\xb2\x07\x24\xe3\x64\xa6\xde\xb5\x65\xf5\x29\x82\x80\x1e\xf6\x97\
\xb5\x05\xbe\x89\xe7\xc2\x0c\x82\xf4\x0b\x00\xf7\xbe\xb0\x98\x0b\
\xb5\x41\xfa\xd5\x80\x7a\xe5\x65\x98\x47\x0f\xd1\xd3\xf8\x30\x92\
\x3e\x28\x29\xd4\x6d\xa0\x30\x8d\x5f\x54\x96\x32\xc2\x50\xfa\x20\
\xa4\x50\x97\x81\xc2\x2c\x7e\x51\xbd\x9d\x23\x8c\xa5\x8f\x76\x0a\
\x35\x0d\x14\x26\xf1\x0b\xc4\x2d\xad\x61\x30\x7d\x34\x53\xa8\x6a\
\xa0\x30\x87\x5f\xa0\x1e\xeb\x09\xa3\xe9\xa3\x95\x42\xb7\x06\x0a\
\x53\xf8\x05\xf2\xd1\xe6\x30\x9c\x3e\x1a\x29\x74\x69\xa0\x30\x83\
\x5f\xa0\xb7\x77\x09\xe3\xe9\x23\x9d\x42\x6f\x06\x0a\x13\xf8\xc5\
\xc4\x16\x77\x61\x40\x7d\x24\x53\xe8\x97\x81\xa2\xf3\xfd\x62\x6a\
\x9b\xdf\x30\xa2\x3e\x52\x29\xf4\xbf\x81\xa2\xd3\xfd\x62\xf2\x55\
\x07\x61\x48\x7d\x24\x52\xe8\x4f\x4a\xd1\xd9\x9e\xe1\x36\xd1\xf1\
\xf9\xf1\xf5\xcd\xd9\xc1\xda\xf7\xab\x04\xbc\xc4\x1b\x0b\x15\x79\
\xbe\x1e\x22\x0f\x76\x72\x06\x04\xcc\xb3\xf1\x3b\xf1\x7c\x3d\x0e\
\xc9\x9f\x75\x4e\x93\xb2\x3d\x99\x1a\xe9\xf3\x8e\xc7\xb9\x60\x24\
\x90\x00\xd2\x89\x73\x05\xd7\x80\x66\x49\xa0\x48\x9f\x1f\xb4\x4d\
\x23\x41\x24\x10\x03\x08\x89\x73\x05\xc7\xc0\x26\x4f\xa0\x9d\xd3\
\x07\xd1\x34\xdc\x44\x02\x11\x80\x9a\x38\x57\x50\x0f\x70\xd2\x04\
\xda\x2d\x7d\xac\x98\x86\x93\x48\xa0\x09\x2c\x25\xce\x15\x94\x03\
\x9d\x2c\x81\x76\x48\x1f\xcb\xa6\xe1\x22\x12\xa8\x13\x6f\xe6\x81\
\x7a\xb0\xd0\x6b\xfa\x9c\x4d\xf3\xf9\xf1\xf5\xed\xb5\x9d\x2b\x44\
\x02\x5d\x50\x9b\xe3\x78\x32\x12\x45\x3b\x96\xe7\x40\x5e\xc4\x4c\
\x69\xec\x67\x2a\xb7\xdb\xdb\x4f\xdb\x28\x91\x40\x69\xed\xac\xca\
\x7a\x22\xad\xd6\xbe\x94\x40\x96\x85\x4b\x89\x36\x3d\x76\x4d\xa4\
\x2d\x13\x88\xf3\x3a\x8e\xc5\x44\x5a\xa9\x77\x3a\x81\xac\x89\x94\
\x92\x6c\x3a\xec\x92\x48\x5b\x24\x90\xe6\x95\x63\x2b\x89\x34\x5b\
\xe3\x54\x02\x59\x10\x24\x25\xac\xd1\xef\x35\x91\x5c\x26\x10\xf2\
\x5a\x15\x72\x22\xcd\xd4\x35\x9c\x40\xa8\x8d\x4f\xc9\xd6\xe8\x46\
\xd6\x71\x04\x37\x09\x64\xc9\x3c\xc8\x8c\x1a\x7b\xc8\x40\x68\xa3\
\xc6\xfa\x5a\x55\xfe\xa9\xb5\x6c\xfe\xa1\xc2\x51\x3a\xa8\x34\x4e\
\xeb\x33\x2b\x70\xb4\xb9\x56\x1b\xa2\xc6\x35\xba\xe7\x40\x08\x0d\
\xb3\xbe\x56\xd5\x53\x4b\xfe\x0c\x82\xde\x3d\x0c\x77\x88\x06\x14\
\x23\x76\x65\xad\x6b\xe6\xff\x28\x8e\x4d\x75\xfc\x59\x7a\xea\xee\
\x4a\x20\xad\x46\x58\x5f\xab\xa2\x38\x16\x7a\x22\x75\x35\x50\xba\
\xf8\x99\x9f\x2a\xae\x63\x20\xbd\x16\x3d\x25\xbc\xbe\x68\x26\x90\
\x64\xc1\xd6\xd7\xaa\x24\xea\x47\x4b\xa4\x66\x83\xd1\xb7\x1f\xa1\
\xaa\xaf\x76\x07\xe2\xec\xff\x4a\xa0\xdd\x3f\xd5\x04\xe2\x2e\x0e\
\xe9\x0c\x69\x26\x91\x10\xea\xd7\x4e\xa4\xaa\x00\x5c\x45\x71\x4c\
\x8e\xa9\xa9\x75\x0c\x82\x71\xee\x90\xee\x33\xd1\x0b\x5a\x1c\xc2\
\x7b\x9d\xa3\xad\x42\xad\x8b\xaa\x81\x3c\x9c\x95\x58\x32\xcf\x19\
\xee\x7e\x9c\x9e\x38\xce\x1e\x90\x1a\xb4\xd3\x5a\x54\xb8\x2e\x88\
\xb2\x18\xc8\xcb\xfe\x7f\x35\x76\x35\x52\xd9\xee\x37\x11\x56\x0e\
\xa0\x21\xaa\xf6\xf5\x90\xdd\x8c\xc4\x62\x20\xef\xd7\x41\x7a\xd8\
\xc9\x48\xe7\xb6\xfe\x6a\xf4\xe8\x97\x21\x88\x86\x62\xa0\x0c\x82\
\x26\x33\x8c\xe8\xb8\x6c\x20\x24\x91\xd0\x0c\x94\x41\xd2\x68\x84\
\x51\x0f\x34\x6f\xcc\xba\xfa\x27\x24\x50\x0d\x94\x41\xd4\xac\x87\
\x96\xae\x43\x06\x42\x16\x01\xdd\x40\x19\x64\x0d\x6b\xb4\x7c\x51\
\x5d\x47\xb1\xd0\x68\x2b\x06\xca\x58\xd0\xf4\x8a\xbb\x25\x9d\x4b\
\x03\x59\x6a\xa4\x35\x03\x65\x2c\x69\x7c\xa6\xd4\xfb\xd7\xdb\x62\
\x2c\x36\xca\xaa\x81\x32\x16\x35\x4f\xe9\x9f\xee\xff\x01\x8b\x65\
\xc9\x17\x1c\x9e\xef\x70\x00\x00\x00\x00\x49\x45\x4e\x44\xae\x42\
\x60\x82\
\x00\x00\x02\xf0\
\x89\
\x50\x4e\x47\x0d\x0a\x1a\x0a\x00\x00\x00\x0d\x49\x48\x44\x52\x00\
\x00\x00\x10\x00\x00\x00\x10\x08\x06\x00\x00\x00\x1f\xf3\xff\x61\
\x00\x00\x00\x19\x74\x45\x58\x74\x53\x6f\x66\x74\x77\x61\x72\x65\
\x00\x41\x64\x6f\x62\x65\x20\x49\x6d\x61\x67\x65\x52\x65\x61\x64\
\x79\x71\xc9\x65\x3c\x00\x00\x02\x92\x49\x44\x41\x54\x78\xda\x84\
\x53\x5f\x48\x53\x61\x14\x3f\xf7\xee\x6e\x22\x0b\x4c\x6b\xac\x60\
\x6a\xb5\x39\xdd\x06\x36\xd9\x70\x6b\xb8\x31\xd4\xb2\x35\x82\x3d\
\x4c\x50\x50\x08\x1f\x24\x84\x24\x56\xea\xc3\xdc\x2a\x63\x36\x1d\
\x4d\xa1\xb0\xf0\xc1\x17\x1f\x7c\xb0\x3f\x0f\x51\x96\x12\xe8\xa6\
\x84\xa6\xeb\x45\xa9\x84\x22\x25\x08\xb7\x97\xec\x45\xe6\xee\xdd\
\xed\x7c\x97\xb5\x36\x1a\x74\xe0\xc7\xe1\xfb\x9d\xf3\xfb\x9d\xf3\
\xdd\x8f\x4b\x41\x4e\xd0\xc5\xc5\x20\xa9\xa8\x80\xc3\xdd\x5d\x48\
\x1f\x1c\x40\x75\x43\x03\x68\x6d\x36\xa0\x45\x22\xa0\x69\x5a\x85\
\x2d\x8d\x90\x1f\x3f\x18\x28\x10\x4a\xa3\x11\xaa\x4d\x26\x41\x98\
\x89\xaa\x74\x3a\xdd\x38\x3b\x34\xf4\xf8\x0f\x41\x21\xdc\x7e\xff\
\xd5\x3c\x83\x53\x7a\xbd\x20\x16\x31\x79\x74\x55\x9a\xe3\x9a\x66\
\x03\x81\x47\xd1\xf5\x75\xf8\xb0\xb5\x05\x75\x3a\x1d\x58\xb1\x0f\
\x79\x4a\xe8\x2c\xaf\xab\x83\xd3\x48\x30\xcc\x3f\x0b\x55\x71\x1c\
\xd7\xfc\x34\x18\x9c\xc0\x0c\x89\xfd\x7d\x28\x2d\x2b\xa3\x30\xf3\
\xa4\xc8\x11\x03\x53\x47\x07\x88\xc4\xe2\x42\x37\x51\xe3\x84\xf3\
\xcf\x42\xa1\x87\xc9\x64\x12\x44\x78\x1d\x8d\x52\x09\xdf\xe3\x71\
\xbe\x5c\x2e\x17\x1a\xb0\x4e\xd3\x50\x38\xd4\x2c\xc7\x5d\x78\x82\
\xe2\x58\x2c\x06\x57\x70\xc8\xd6\xe6\x26\x9c\x51\x28\xc0\x6e\x30\
\x80\xba\xb2\x12\x2e\x79\x3c\xd7\x70\x83\x85\x42\x06\xd5\x1c\xcb\
\xb6\x3c\x0f\x87\x1f\xbc\x5f\x5b\x83\xbb\x7e\x3f\x1c\xe0\x8b\xdc\
\x1a\x1c\x24\x2b\x0b\x1f\xd6\xd1\xdb\xdb\x8b\xd3\x17\xf0\x1e\xdb\
\x4c\x01\xf1\xc5\x17\x13\x13\xe3\xef\x56\x56\xe0\x8e\xd7\x9b\x2d\
\x04\x46\x47\x41\x52\x54\x04\x2d\x3d\x3d\xd7\x29\x8a\x9a\x47\xa3\
\xcf\x84\xcf\x35\xa8\x61\x59\xd6\xf1\x6a\x72\x32\xbc\xbc\xb4\x04\
\xbe\xfe\xfe\x6c\x61\x64\x6c\x0c\x8c\xf5\xf5\xd0\xdc\xdd\xed\x41\
\xf1\x1b\x51\x46\x9c\x6b\xa0\x21\xe2\xd7\x53\x53\xf7\x23\x8b\x8b\
\xe0\xef\xeb\xcb\x8a\xef\x85\xc3\x60\xb6\x58\xa0\xb1\xab\xeb\x06\
\x8a\xe7\x50\xfc\x29\x77\x65\x62\xa0\xe1\x52\x29\xe7\xfc\xf4\x74\
\x28\x8a\xe2\x00\xae\x2d\x91\x48\x84\xe2\xed\x60\x10\x2c\x56\x2b\
\xd8\x3b\x3b\xfb\x80\x88\x19\x26\x2b\xfe\x8a\xdf\xe7\xcb\xea\x2a\
\x30\x38\xf9\xf2\xdb\x99\x99\x91\xbd\x78\x1c\xc6\x87\x87\x41\x2a\
\x95\x0a\x0d\x37\x7d\x3e\x41\x6c\x6b\x6f\x1f\xc0\xc9\x2f\x71\xf2\
\x47\xc2\xef\xe0\xab\xec\x6c\x6c\xfc\x5d\x41\xdf\xda\xaa\x3d\xeb\
\x76\x0f\xfc\xe4\x79\x7e\x2e\x12\xe1\x5d\x2e\x17\x3f\x1f\x8d\xf2\
\xbf\xf0\x4c\x78\x52\x37\xb4\xb5\x81\xa2\xb6\xb6\xf0\x83\x9f\xd0\
\x6a\xa1\xc6\xe9\xd4\xa9\x1d\x0e\x2f\x31\xd9\xde\xdb\xe3\xf7\x31\
\x93\x33\xe1\x49\xfd\x7f\x41\xfe\x98\x92\x12\x95\xaa\x49\x6e\x36\
\x0f\x11\x13\x92\x8f\xaa\x54\x76\xe4\x8f\x21\x4a\x49\x1d\x71\x04\
\x51\x8c\x28\x42\x88\x33\x3a\x8a\xca\x1c\x4e\x22\x8e\x4b\x64\x32\
\x85\x58\x26\x3b\x97\x4a\x24\x96\x0f\x13\x89\x6f\xc8\xa5\x10\x6c\
\x26\x13\x1c\xe6\x70\x04\xdc\x6f\x01\x06\x00\x2d\x06\x04\x62\x7f\
\xe8\x51\x71\x00\x00\x00\x00\x49\x45\x4e\x44\xae\x42\x60\x82\
\x00\x00\x03\x37\
\x89\
\x50\x4e\x47\x0d\x0a\x1a\x0a\x00\x00\x00\x0d\x49\x48\x44\x52\x00\
\x00\x00\x10\x00\x00\x00\x10\x08\x06\x00\x00\x00\x1f\xf3\xff\x61\
\x00\x00\x00\x19\x74\x45\x58\x74\x53\x6f\x66\x74\x77\x61\x72\x65\
\x00\x41\x64\x6f\x62\x65\x20\x49\x6d\x61\x67\x65\x52\x65\x61\x64\
\x79\x71\xc9\x65\x3c\x00\x00\x02\xd9\x49\x44\x41\x54\x78\xda\x6c\
\x93\x5d\x48\x14\x51\x14\xc7\xff\xbb\xb3\xbb\xb6\xab\x95\x5b\x46\
\xae\x99\xba\x7e\x40\x42\x46\x12\xa5\x4b\x49\xe8\x83\x60\x22\x11\
\x3d\x94\xf6\xd6\x43\xe9\x6b\x81\x6f\x46\xd1\x43\x54\xd0\xf6\x49\
\xf6\x24\x44\x81\x6f\x3d\x04\x8b\x08\x9a\x60\x59\xb6\x18\x65\xe9\
\x22\xbb\xce\xb8\xea\xfa\xb1\x8b\xdf\xe3\x3a\xbb\xb3\xce\xed\xcc\
\x75\x35\xad\x2e\x73\xb9\x77\xe6\x9c\xf3\xbf\xbf\x73\xee\x19\xc3\
\xad\xf6\x76\x18\x0c\x06\x3e\x35\x4d\x83\x3e\x68\x5f\x47\x8b\x03\
\xff\x1f\xdd\xeb\x89\x44\x40\x4d\x24\xc0\x18\x83\x69\xbb\xc5\x48\
\x22\x09\x32\xd0\xc8\x6a\xa9\xaf\x6f\x9d\x8e\x44\x61\xb7\x5b\xb8\
\xb0\x46\xce\x43\x81\x00\x3a\x07\x07\x1b\xf5\x33\x68\xfa\x79\xcc\
\x0e\x6d\x12\x30\x0a\x02\x74\xf5\xc8\x9c\x02\x8a\x44\x24\xb2\x86\
\x99\xd9\x28\xa6\x66\x56\x21\xcb\x32\xee\x36\x34\xb4\x92\xbd\x8a\
\xbc\x8b\xf4\x90\x4d\x82\x3a\xc2\x71\x24\xf1\x21\x08\x42\xc5\xe4\
\x62\x08\xcb\xb2\x8a\xe2\x9c\x83\xc8\xb0\x5a\xa1\xae\xaf\xe3\xc7\
\xf0\x3c\xde\x7a\x3c\x28\xc9\xc8\x68\x7d\xd2\xde\x7e\x83\xdc\xdd\
\x26\x8d\x0c\x9b\xc8\x23\x81\x15\xe4\xe6\x59\x77\x20\x0f\x07\xa7\
\x91\x99\xbe\x1f\xa9\x29\x36\x9c\x38\xea\x42\x82\x6c\x66\xb3\x19\
\xe5\xc1\xa0\xc2\x09\xd4\x8d\x9c\xe1\x17\x65\x3d\x03\x04\xc7\xd6\
\x78\x71\xf4\x7a\xea\xc8\x35\xe5\xe5\xf8\xe8\xf3\xc1\xbe\xc7\x8c\
\x0c\xbb\x8d\x93\x08\x24\x10\x8b\xc5\x0c\x1b\x02\xaa\xca\xc9\x8b\
\x9c\xa9\xf0\x4b\xab\x70\x1e\xb6\xf0\x53\x74\xc7\x21\x71\x03\x59\
\x1f\x83\xbf\xfc\xa8\xad\xa8\x24\x1b\xa3\xca\xa9\x88\x93\xc0\xc9\
\xee\x6e\x12\x88\xc7\xb9\x80\x38\x1e\x85\xd1\x68\xc0\xd8\x64\x9c\
\x13\xd0\x83\x92\xc2\xd3\x9c\x44\x7f\x5f\x54\xc7\x71\x60\x5f\x0a\
\xdf\xc7\x07\x06\xd0\xe8\x76\x5f\xd3\xc2\xe1\x21\x23\xa1\x70\x9c\
\xc2\x1c\x1b\x4f\xa1\x20\x67\x17\xf2\xf9\x4c\x41\x2e\xd1\x64\x67\
\x0b\xc8\xcb\xb7\x52\x41\xe3\x98\x5f\x4a\x60\xc4\x1f\x42\xaf\xf7\
\x3b\xca\x9a\x9a\x8e\x45\x80\x3b\x26\x42\xe1\x04\x52\x68\x8d\xdf\
\xc0\x58\x28\xc6\x4f\xd7\x34\xb6\x45\xc2\x98\x02\x9b\x05\xb0\xa8\
\xfd\x08\x8e\x2e\xa3\xe6\xfa\x55\xd4\xb9\x5c\x3d\x17\x19\xbb\x67\
\x8a\x25\x05\x0a\xb2\x6d\x18\x9d\x8c\x22\x2f\xcb\xca\x6f\x80\x17\
\x32\xb9\x1a\xa8\x37\xc4\x2e\x2f\x7c\xa1\xf7\xa8\x39\x75\x1c\xee\
\xa7\x12\x66\x9d\xce\xaf\xdf\x04\xa1\xd3\xa4\x28\xca\x06\xc1\x54\
\x92\x60\x4a\xd9\xca\x7b\x93\x24\xb6\xf8\x09\xc6\xb9\x37\x28\xab\
\x3c\x8b\x8e\x8e\x7e\x5c\xba\xd0\x82\xd7\x7d\x3d\xe1\xb6\x89\x09\
\xfc\x21\x38\x44\x04\xa1\x28\xf2\x75\x02\x60\x8b\x60\x61\xb6\x17\
\xe2\xec\x73\x54\x53\xf0\xc3\x47\xee\xd1\x8e\x61\xc7\x87\xa1\x97\
\xcd\x7e\x4d\x96\x97\xe5\x70\x38\xdf\x34\x23\x8a\xd8\xeb\x70\x18\
\x44\x22\xd0\x5b\x5c\x9a\x56\x92\x79\x33\x44\x17\x46\x11\x09\x3c\
\xc0\x19\x57\x29\x1e\x3f\x7b\x21\x05\x25\xa5\xb9\xcf\x23\x7d\x01\
\xa4\xcd\xe6\xd7\x83\x90\x7e\xe4\xfc\xf9\x9b\x14\xc0\x88\x40\x5f\
\x18\x9d\xcc\xd6\x89\xfd\xb3\xe7\x36\x63\xf2\x08\x7b\xd7\x56\xc5\
\x6a\xaf\x94\xbe\x22\x5f\xfb\xdf\xbf\xa6\xde\x4d\xb9\xbb\x8b\x8b\
\xab\x8d\x69\x69\xff\x18\x97\xbc\xde\xfb\x97\xcf\xa5\xfe\x1c\x5e\
\xcd\xec\x93\xc2\x96\x81\x15\x9f\xaf\x8b\x3e\x8b\xdb\x7d\x7e\x0b\
\x30\x00\x66\x8d\xa1\xfd\x87\x65\xe6\x27\x00\x00\x00\x00\x49\x45\
\x4e\x44\xae\x42\x60\x82\
\x00\x00\x02\xa1\
\x89\
\x50\x4e\x47\x0d\x0a\x1a\x0a\x00\x00\x00\x0d\x49\x48\x44\x52\x00\
\x00\x00\x10\x00\x00\x00\x10\x08\x06\x00\x00\x00\x1f\xf3\xff\x61\
\x00\x00\x00\x19\x74\x45\x58\x74\x53\x6f\x66\x74\x77\x61\x72\x65\
\x00\x41\x64\x6f\x62\x65\x20\x49\x6d\x61\x67\x65\x52\x65\x61\x64\
\x79\x71\xc9\x65\x3c\x00\x00\x02\x43\x49\x44\x41\x54\x78\xda\xa4\
\x93\xcf\x6b\x13\x51\x10\xc7\xbf\xfb\x23\x6b\xd3\x4d\x63\x53\x51\
\x69\x93\x2d\x52\x62\xc5\xb6\x54\x08\x52\x28\x28\xb4\xa8\x08\xc5\
\x5e\x84\xfe\x01\x3d\x49\x2f\x9e\x7a\x29\x96\x9e\xf2\x07\xf4\xa4\
\x88\x17\x7f\x1c\x82\x22\x2a\xb9\x05\x5a\xe8\x49\x94\x0a\xb1\x58\
\x24\x97\x68\x49\xa5\x31\x35\x90\xd2\xcd\x26\xd9\xcd\x6e\xd6\x99\
\xad\x5b\x82\xb4\x50\x71\x60\xf6\xbd\x37\xcc\x7c\xdf\x7c\xde\xdb\
\x27\xb8\xae\x8b\xff\x31\x79\x66\x69\xe9\x70\x21\x08\xc2\x34\x0d\
\x7d\xff\x50\xbf\x23\xf3\xd7\x69\xb5\xfc\x40\xf4\x4d\x32\xf9\xe8\
\x24\x3d\x09\xe4\x77\x17\x17\xe7\x64\xda\x15\x92\x28\xc2\x34\x4d\
\x8e\x8b\x0e\x21\x7d\x2e\xba\xa8\x14\xbe\x42\x8b\x0f\x63\x20\xd2\
\x3a\x52\x40\xa4\x1a\xbb\xd9\x14\xbd\x0e\x04\x5a\x28\x8a\x82\x9a\
\x61\x88\x36\x09\xec\x15\xbe\xa0\x98\xdf\x84\x08\x07\x5a\xe2\x32\
\x0a\xa5\x12\x82\xc1\x20\x6c\xdb\x46\x6f\x4f\x8f\x27\x20\xd1\xc6\
\xbe\xc0\x34\x5c\xb7\x8f\x15\x03\x8a\x72\x6d\x65\x7d\x1d\xdb\xbb\
\x3a\x8a\xe5\x32\x6a\xe1\x5f\xa8\x7e\x32\xd0\xa0\x42\xdf\xce\x77\
\x77\xe3\x4a\x3c\x8e\x00\xe5\x37\x2d\x4b\x94\x6d\xc7\x39\x86\xfb\
\xe6\x91\xdc\x4f\x33\x19\x9c\x56\x55\x5c\xd0\x34\x58\x96\x25\xc9\
\xdc\x06\x73\x3f\xcb\xba\xf8\xfe\xfe\x35\xc6\x6f\xcf\xe0\xd6\xc0\
\xf1\xdc\x6a\x67\x27\x62\xd1\x28\x6c\x3a\x78\xcb\x34\x45\x91\x05\
\x98\xfb\xe7\x87\x57\xd8\x5c\x4d\x61\x63\xe5\x25\x9a\x8e\x83\xb5\
\x6c\x16\x1b\x5b\x5b\xf8\x98\xcb\x79\x6b\x76\xce\x4b\x2e\x2f\xa7\
\x9f\xa4\x52\xab\xcd\x03\x01\x49\x66\x0e\x56\x3b\xa3\x0d\xa1\x5a\
\xad\xe2\x5c\xff\x10\x2c\x62\x8e\xc5\x62\xde\xae\x2a\xb5\x6b\xfd\
\x39\x03\xe6\x56\x43\x21\x69\x6e\x76\xf6\x06\xd5\xc1\xd0\xf5\x80\
\xcc\x1c\xac\xf6\xee\x6d\x1a\x86\x61\x60\x2d\x93\xc6\x9d\xeb\xf7\
\x91\xa3\x9d\x7d\x2b\x45\x22\xa8\xd7\xeb\x18\x4f\x24\x50\xd3\xf5\
\xca\xd9\x78\x7c\x21\x14\x0e\x77\x39\x86\x51\x96\x99\x83\x3b\x78\
\xf1\x70\x9e\x52\xe7\xbd\x82\x7a\xad\x86\xab\xa3\xa3\xde\x3c\x48\
\xcc\xbe\x71\x9e\x24\x49\xdf\xec\x7c\xfe\xf9\x1e\xc0\xe7\x5e\x11\
\x99\x83\x3b\x60\xae\xde\x91\x91\x05\x1e\x2d\xe2\xf5\xbd\x3d\xce\
\x79\xa4\x60\x5c\x9c\x9c\xdc\xa1\xe2\x22\x79\x03\x97\xa6\xa6\x1e\
\xec\x9a\xa6\x5b\xa1\x57\xc5\x73\x1e\x7f\xe8\xfa\xa1\xb7\xc7\x39\
\x8f\xe7\xe4\x88\x8d\x8d\x1d\x5c\x6d\xd7\xe0\xe0\x3d\x49\x55\xfb\
\xab\xfb\xfb\xba\xd2\x68\x6c\x5b\x1d\x1d\x1a\xf3\xf9\x6d\xff\x1d\
\x27\xee\x02\xf9\xe3\xf6\x7f\xe3\x14\x79\x84\xaf\xf9\x04\x6f\xc8\
\xe3\xf6\x5a\x27\x1b\x9e\x98\xc0\x6f\x01\x06\x00\x48\xae\x45\x78\
\x60\x4e\x1f\xe2\x00\x00\x00\x00\x49\x45\x4e\x44\xae\x42\x60\x82\
\
\x00\x00\x02\x75\
\x89\
\x50\x4e\x47\x0d\x0a\x1a\x0a\x00\x00\x00\x0d\x49\x48\x44\x52\x00\
\x00\x00\x10\x00\x00\x00\x10\x08\x06\x00\x00\x00\x1f\xf3\xff\x61\
\x00\x00\x00\x19\x74\x45\x58\x74\x53\x6f\x66\x74\x77\x61\x72\x65\
\x00\x41\x64\x6f\x62\x65\x20\x49\x6d\x61\x67\x65\x52\x65\x61\x64\
\x79\x71\xc9\x65\x3c\x00\x00\x02\x17\x49\x44\x41\x54\x78\xda\xa4\
\x93\x4f\x6b\x13\x51\x14\xc5\xcf\x9b\x37\x93\x49\xc6\xa9\x25\xa3\
\x15\x63\x16\x2e\x02\x06\xad\x0b\x45\xc1\x95\x5f\xc0\x3f\x0b\x21\
\x1b\xa5\x20\xb8\x31\xea\x7c\x82\xac\xf4\x2b\x54\x5b\x23\x88\x1b\
\x4b\xb3\x70\xe1\x42\xb7\x82\x20\xe8\x42\xbb\x70\xa1\x62\x36\xa2\
\xa0\x51\xda\x1a\xc2\x4c\xa6\x26\x93\xcc\x78\xef\x75\x5a\xb4\x2a\
\x54\x7c\x70\xb8\x2f\x93\x7b\x7e\xf7\xbc\x37\x89\xaa\xd5\x6a\x50\
\x4a\x9d\x06\xb0\x07\xff\xb6\x3e\xa5\x69\xfa\xc0\x4c\x92\x84\x3f\
\x94\x9b\xcd\xe6\xcd\x38\x8e\xb7\xe4\xb4\x2c\x0b\xf5\x7a\xfd\x12\
\xef\xcd\xd1\x68\xc4\xd5\x18\x0c\x06\xf0\x7d\x1f\x0c\x64\x11\x5d\
\xea\x78\x3c\x46\x18\xf6\xa9\xa6\x62\xf4\x3c\x0f\xf3\xf3\xd7\x41\
\x3e\xe3\x67\x80\xe2\xca\x86\x6a\xb5\x0a\x4e\xf2\xed\x68\x05\xa3\
\xc7\x2f\xb1\xb2\xf2\x95\x9e\x6b\x32\xdb\xb0\xed\x3c\xa2\x28\x60\
\x33\x4b\x09\x20\x8b\x6d\xf0\x43\x9e\xc6\x49\x58\x69\x79\x07\x56\
\x57\xbb\x64\x88\x91\xcf\x6f\x13\xb3\x65\xe5\xa9\x27\x16\x00\xf9\
\x8c\x0d\x23\x49\x33\x48\x00\x34\x39\x8a\x22\xa8\xbd\xbb\x08\x94\
\x60\xf2\x60\x05\xe5\xd9\x3a\x26\x4f\x1c\x13\x90\x69\xda\x92\x90\
\x3d\xec\x35\x86\xc3\x21\x48\x3f\x40\xa5\x22\x9d\x37\x84\x73\xed\
\xbc\x5c\xd6\xf6\xe9\x0a\x3c\xff\x14\x7a\x8d\x16\x01\x8b\xa8\x35\
\xaf\x12\xc0\x94\x04\xec\x61\xef\xc6\x11\xb8\x26\xef\xbf\xa0\xdf\
\x5d\x43\xf7\xe1\x53\xb8\x07\xf6\xa1\x78\xf9\x24\xfa\xb7\x1f\xc1\
\x75\x8b\x48\x5b\x4b\xb8\x77\xf7\x19\xbf\x72\x49\xb0\x7e\x04\x93\
\x29\xb4\x24\x8e\xe3\x38\xe8\xf5\x7a\x30\x0c\x0b\xfa\xed\x07\x84\
\xfe\x2c\x0a\x85\x09\x0c\x0c\x2d\x46\x5e\xb6\xad\xd7\x13\x68\x01\
\xb4\xdb\x6d\x94\x4a\xa5\x1c\x37\x34\x1a\x8d\x2d\xfd\x0e\xb8\x37\
\x08\x82\x5c\xa7\xd3\x01\x63\x3d\xd7\x75\x67\xb4\xd6\xbb\x37\x37\
\xd2\xa4\xb2\x4c\x31\xcd\x8f\x9b\xbf\xa3\x0b\xff\x4c\xf7\xb5\xc0\
\x80\x02\x69\x82\xfb\x7e\xe9\x98\xce\x01\xaf\x86\x7e\xb6\xbf\x41\
\xfb\xdf\xf8\xa4\x40\xfd\x35\xe7\xe2\xd4\x2d\xbc\x89\x8f\xc8\x7e\
\xbf\xb5\x84\x73\xcb\x17\xff\xd4\xc6\x53\x77\x92\x2a\xa4\x43\xa4\
\xc3\xa4\xaa\x24\x5a\x0c\x71\xe6\xce\x59\x01\xdc\xbf\xd0\xe2\xf2\
\x82\x93\x93\xde\x65\xfb\xe7\xa4\xd7\x9c\xc0\xca\x8e\xe1\x66\x72\
\xf8\xad\xe0\x8a\x33\x83\x29\x75\x5c\xc6\x2c\xa7\x4f\x30\x17\x2d\
\x64\x43\xd7\x38\x7a\xa6\x48\xf1\x9f\xe6\x7f\xd6\x77\x01\x06\x00\
\xf9\x1f\x11\xa0\x42\x25\x9c\x34\x00\x00\x00\x00\x49\x45\x4e\x44\
\xae\x42\x60\x82\
\x00\x00\x07\x62\
\x89\
\x50\x4e\x47\x0d\x0a\x1a\x0a\x00\x00\x00\x0d\x49\x48\x44\x52\x00\
\x00\x00\x18\x00\x00\x00\x18\x08\x06\x00\x00\x01\x97\x70\x0d\x6e\
\x00\x00\x00\x06\x62\x4b\x47\x44\x00\xff\x00\xff\x00\xff\xa0\xbd\
\xa7\x93\x00\x00\x00\x09\x70\x48\x59\x73\x00\x00\x0b\x13\x00\x00\
\x0b\x13\x01\x00\x9a\x9c\x18\x00\x00\x07\x02\x49\x44\x41\x54\x48\
\xc7\x55\x95\x6b\x70\x5d\x55\x15\xc7\x7f\xfb\x3c\xee\x3d\xe7\x9e\
\x7b\x93\xfb\x68\x4a\x93\x86\xb6\x69\x4b\xaa\x38\x16\x06\x3a\x16\
\x4b\x81\x22\x4c\xad\x55\xa9\x83\xce\xe0\xa3\x55\xa1\x0a\xc3\x07\
\xf0\x05\x0c\x33\x38\xea\x28\xc2\xe0\x03\x44\x1c\x18\x64\x8a\x03\
\xa3\x32\x08\x88\xa0\x0c\x8f\x3e\xd2\x34\x84\x16\xab\x96\x3e\xd2\
\x34\x49\x9b\x26\x6d\x92\x9b\xc7\xcd\x4d\x9a\xe6\xde\xdc\x7b\xf6\
\x39\x67\xf9\x21\x24\xc0\xfa\xb8\x67\xd6\xfa\xed\xb5\xd6\xff\xbf\
\xb7\x12\x11\x82\x20\xa0\xe2\x57\x2f\x41\x44\x78\xef\xf0\x51\x29\
\x57\x66\x04\x11\xa1\xa9\xa9\x59\x0e\x1f\x3d\x22\x68\xad\x69\x6b\
\x6b\x7f\x48\x6b\x8d\xaa\x56\xab\x4c\x97\x4b\x72\xf8\xbd\xa3\x18\
\x57\xac\xbd\x4a\x9c\xb8\xc3\xe2\xc6\x06\xc5\xfb\xd5\x6a\x47\xc7\
\x0a\xd7\x74\xf5\x74\x8b\xef\xfb\xf2\xce\x81\x03\x62\x00\xb4\xee\
\x6b\x9b\x0c\x42\xbd\x77\xf9\xb2\x26\x76\xed\xde\x8d\x6d\x59\xeb\
\x0d\x80\x96\xdd\xfb\x9e\xfc\xfa\x4d\xdf\xe4\xca\x75\x1b\x48\x67\
\xd2\x6a\xcd\xe5\x6b\xde\x26\x08\x02\x82\x20\x20\x0c\x43\x0e\x1d\
\x3a\xfc\x42\x10\x04\x68\xad\x21\x08\x02\xa5\xb5\x66\x4f\x4b\xab\
\xe4\x47\x86\x45\x6b\x2d\x22\x82\xa1\x94\x92\xb6\xb6\xf6\xb1\x65\
\x4d\x4b\x58\x90\xcd\xd1\xd6\xde\xce\xc0\xc0\xd0\x76\xd5\xdd\xd3\
\x43\x32\x99\x94\x64\x32\x89\x48\xc4\xa1\x43\x47\x58\x50\x97\x55\
\x6a\xed\xa7\xd6\xcb\xe4\xe4\x24\x7e\xe0\xf3\xf8\xe3\x7f\xc0\x30\
\x0d\xe3\xd2\x4b\x57\x8b\x71\xff\x03\x3f\x57\xb9\x5c\x8e\x86\x0b\
\xea\x19\x2f\x14\xd8\x78\xfd\x17\xa2\xa1\x81\x85\xa2\x44\x84\x30\
\x0c\x11\x11\xa5\x94\x32\x80\xb0\xe3\x78\x67\x7b\xa9\x34\xb3\xae\
\x7e\xf1\x42\x1a\x16\x35\x30\x75\xee\x5c\x21\x9b\xcd\xd6\x45\x51\
\x88\xc1\xfb\xa1\x94\x12\xd3\x34\xc3\x7f\xbd\xf6\xba\x80\x5a\x77\
\xe1\x92\x06\xea\x72\x75\xd8\x96\x05\x8a\x05\xbb\x5b\xf6\x4a\x7f\
\xff\xd9\x9b\x95\x88\x70\xac\xe3\x04\x41\xa8\x1f\x9d\x3a\x37\x75\
\x67\x43\x43\x3d\xa9\x9a\x24\xe9\x54\x2d\x96\x6d\xd1\xd5\xdd\xcd\
\xe0\x60\x9e\xfa\x86\x45\xac\x6a\x6e\x56\x4a\x44\xb8\x62\xed\xd5\
\x92\x1f\x1e\x22\x0c\x23\x1e\x7c\xf0\x97\x6c\xdb\xf6\x35\xb4\xd6\
\xb4\xef\xdf\x8f\x5f\xd5\xd4\xd6\xa6\x4e\x15\x27\x8a\x2b\x2f\xbb\
\xec\x32\x94\x88\xf0\xd8\x63\x4f\x7c\xef\xaf\x7f\x79\xee\x77\x5a\
\x6b\xb4\xd6\x84\x51\x44\xa9\x34\xcd\x8b\x7f\x7f\x9e\x6a\xb5\xf2\
\xd6\xba\x2b\xee\xdb\x08\x1d\x84\xe1\xc4\x6c\xc2\xce\xb7\x5a\xf0\
\xb5\xaf\x06\x06\x07\x6b\x0e\x1e\x3c\xf8\x8f\xb3\x67\x07\x36\x44\
\x41\xc8\x8f\xee\xfe\xfe\x77\x1a\x16\xd7\xef\x08\xfc\xd5\xfe\xd8\
\x18\x76\x47\x07\xcf\xcf\xef\x6e\x6e\x67\x5a\x6b\x46\x47\x47\xd7\
\xb6\xb4\xec\xdb\x7b\xba\xaf\xef\xae\x48\xa2\xb9\x73\x25\x22\x1f\
\x4c\x09\xb0\x94\x52\x18\x86\x61\xff\xef\xd0\x91\x03\x0b\xea\x72\
\xd7\x78\xa9\xe4\xaf\xc3\x20\x94\x62\xb1\xf8\x25\x40\x01\xf3\x09\
\x1e\x10\x98\xa6\xc9\x1b\x6f\xee\x2a\xcd\x4d\x2a\x1e\x8b\x61\x18\
\x06\x75\x75\x75\x2f\x9f\x3c\xd5\x7b\xe7\x87\x13\x4a\xb3\xe3\x3d\
\xfe\x70\x26\x93\xb6\x1d\x37\x46\x22\x91\xc0\x75\x5c\x82\x20\xe0\
\xc0\xbf\xdf\xa5\xb7\xb7\xef\x11\x00\x43\x29\x85\x52\x8a\x99\x4a\
\xf5\xaa\xfe\xfe\x33\x3f\x48\x67\xd2\x78\x9e\x47\xca\xf3\x30\x0d\
\x83\xa1\xfc\x10\xe5\x52\x85\x85\x0b\xeb\x66\xef\x7d\xbc\xb3\x1b\
\xa5\x14\x3d\x3d\xdd\xfb\x56\x35\x37\xe3\x79\x2e\x5e\xc2\xc3\xb2\
\x6c\x2a\x95\x0a\xdd\x3d\x27\xb1\x4c\x9b\x8b\x9a\x57\xdc\x00\x60\
\x84\x91\x06\x09\x5f\x6a\x6e\xbe\x88\x4c\x2e\x4d\x22\x91\x20\xee\
\xc4\x51\x4a\xd1\xd9\x75\x82\x28\x8c\x48\x26\x93\xd5\x7c\x3e\xff\
\x4f\x00\xa3\xab\xb3\xfb\x8e\x2f\xdf\x78\xd3\x8d\xd7\x6e\xb8\x9e\
\xad\xdf\xb8\x99\x94\x97\xc2\x89\xc5\x19\x2f\x8e\x33\x38\x90\x27\
\x9b\xcd\x31\x31\x39\xbe\xb4\x50\x28\x00\x60\x8c\x0c\x8f\xd6\x64\
\xb3\x59\xea\xea\xea\xe8\xeb\xeb\x63\x71\x63\x13\xcf\x3d\xf7\x3c\
\xa7\x7a\x7b\xc9\xe6\x72\x04\x81\xde\xa7\x94\x39\x72\xf1\xc5\x1f\
\x9f\x15\xe9\xce\xdd\x2d\xfc\xf4\xc7\x3f\x93\x30\x0c\xf1\x7d\x1f\
\xad\x03\x7c\x5d\xe5\xf6\xdb\x6f\x63\xd3\xe6\x8d\x7c\xac\xf9\xbe\
\x5e\x38\xb4\x1c\x26\x98\x98\x98\xd8\x6c\x48\x14\x71\xf7\x3d\x77\
\x27\x52\xa9\x14\xa9\x54\x8a\x4c\x26\x4d\x36\x93\xe5\xe9\x1d\xcf\
\x50\xa9\x54\xfe\x08\xef\x2c\x87\x5e\xca\xe5\x09\xda\xdb\xb9\xd5\
\x22\x52\xa4\x92\x5e\x75\xfb\x77\xb7\xab\xe3\xc7\x8f\xdf\x72\xf4\
\xe8\xb1\x27\xa7\xcf\x4f\x5b\xcb\x96\x37\x95\x6d\xdb\xbe\xad\xbf\
\x3f\x7f\x6c\x70\x90\xdf\x77\x76\x82\xd6\x6c\x9d\x77\xdc\x5c\x88\
\x08\x4a\x29\x00\x25\x22\x02\x60\x9a\x26\x85\xc2\xf8\xe7\x8e\x1c\
\x39\xfa\xd2\x74\xa9\xe4\xe6\x72\x59\x72\x0b\x72\x24\x93\x1e\xa6\
\x61\xcc\x58\xa6\xf5\x94\xeb\xba\x8f\x24\x12\x89\x3e\x80\x28\x12\
\x40\xb0\x6d\x9b\x8f\x00\x44\xc4\x02\x16\x29\xa5\xf2\x40\x38\x57\
\xbc\xf7\x74\xdf\xfd\x9d\x27\xba\xef\x4b\xd7\xd6\x90\x4c\x26\xf1\
\xbc\x04\xb1\xb8\x8d\xeb\xba\x24\x13\x1e\xf1\x78\x1c\xc3\x30\x98\
\x9a\x9a\x92\xf3\xe7\xcf\x3f\x5c\x5f\x5f\x7f\x97\x42\x50\x86\xf9\
\x11\x80\xfa\xa0\x89\xd9\x2e\xb4\xd6\xa9\xfd\xfb\xdf\x7d\xbb\xea\
\xfb\xab\x73\xb9\x1c\x6e\xc2\xc1\xf3\x12\xc4\xe3\x71\x1c\xc7\xc1\
\x4b\x24\xb0\x2d\x1b\x11\xc1\xf7\x7d\x86\x47\x46\xe8\xeb\xef\xa7\
\x5c\x9a\x29\x7c\xe6\xda\x0d\x97\xbb\xae\x73\xe6\xc3\xee\x11\x40\
\x94\x52\x58\x96\x45\xb1\x38\xb1\xe9\x8d\x37\x77\x4e\x99\x96\xb5\
\xba\xb1\xb1\x91\x74\x3a\x4d\x2a\x95\xc4\x71\x1d\x3c\xcf\x23\x99\
\x48\x60\x9b\x16\x22\x42\xb9\x5c\xa6\xb7\xef\x34\xbd\xa7\xfb\x08\
\x83\x88\x54\x2a\xb5\xa0\xab\xab\xfb\x16\x00\x0b\x60\x64\x74\xf4\
\x43\x14\x89\x9d\xe9\x1f\x78\x75\x64\x64\xec\xb3\x8d\x8d\x8d\x78\
\x09\x8f\xb8\x13\x23\xe6\xd8\x38\xb1\x38\xae\xe3\x12\x8b\xc5\x30\
\x0d\x83\x50\x84\xa9\xa9\x29\x7a\x7a\x4e\x52\x2a\x95\x09\xc3\x90\
\x78\x3c\xc6\xd2\x65\x4b\x06\x16\xd7\xd7\xef\x98\x07\x14\xc6\xc6\
\x67\x8d\x64\x59\x6b\xf2\xc3\xc3\xed\x5a\xeb\x58\xd3\xb2\xa5\xc4\
\xdd\x38\x8e\x13\x23\x16\x8b\x11\x77\x1c\xdc\x78\x1c\xdb\xb2\x31\
\x0c\x83\x20\x0c\x29\x8c\x17\xe8\xea\xea\x41\xeb\x00\x11\xa1\xb6\
\xb6\x96\x4c\x26\xbd\x2f\x1e\x8f\x5d\x33\x5e\x2c\x72\xc1\xc2\x85\
\xb3\x00\xc7\x71\x38\x71\xa2\xfb\xde\xd6\xd6\xd6\x07\xc3\x28\x62\
\xe9\x92\x0b\xb1\x6c\x93\x35\x6b\x2e\xa7\x26\x55\x83\x44\x11\x22\
\xb3\x1f\x9f\xa1\x0c\xb4\xd6\x0c\x0e\xe7\xe9\xe9\xea\x41\x04\x1c\
\xc7\x25\x93\x49\x33\x75\xfe\xdc\x43\xf9\xe1\xa1\x7b\x87\xf2\x83\
\xb8\xae\xfb\x01\xe0\x85\xbf\xbd\xf8\xea\xcb\x2f\xbf\xf2\x45\xa5\
\x14\x95\x4a\x05\x5f\xfb\xf8\x5a\x53\x2a\x95\xa8\x56\xab\xac\x5f\
\x7f\x25\x0f\x3c\xf0\x0b\x2e\x59\xfd\x49\x44\x84\x9e\x13\x27\x39\
\x75\xaa\x77\xbe\xb0\x9b\x70\x28\x14\x0a\xb7\x06\x81\x7e\x2a\x16\
\x8b\xb1\x72\xe5\x4a\x5c\xd7\x65\x4e\xeb\xbc\xf2\xca\x6b\x8d\xcf\
\x3e\xf3\xec\x7f\x06\x07\x87\x2e\x98\x83\x84\x61\x48\x18\x86\x44\
\x51\x84\x20\x54\x7c\x9f\xca\xcc\x0c\xdf\xfa\xf6\x56\xb6\x6c\xb9\
\x61\xf6\xf9\x4f\xd7\x00\x42\x6d\x4d\xcb\x1d\xcb\x9b\x8e\x6c\x87\
\x73\x97\x42\x11\x98\x28\xc0\xd0\x4f\x44\xa6\x9f\x50\x22\xc2\xae\
\xdd\x2d\xa0\x14\xad\x7b\x5a\x7f\xdb\xb2\x67\xef\x0f\xc3\x28\xc4\
\x34\x4d\xa2\x28\x9a\x87\x44\x51\x84\x44\xc2\x4c\x65\x86\xfa\x86\
\x7a\x1e\x79\xf4\x37\xd8\xb6\xe5\x17\x0a\x85\xeb\xae\x5e\x7f\x4f\
\x1b\x9c\x01\x86\x81\x88\x28\x82\xb1\x31\x18\x1b\xe3\xcf\xb3\xdf\
\xc8\xce\x96\x59\x05\x45\xc2\xe4\xe4\x24\xbd\xa7\x4f\x7f\xf5\xd8\
\xb1\x63\xbf\x1a\x19\x1e\xb9\x30\x08\x02\x4c\xd3\x44\x29\x35\x6f\
\xc8\x72\x79\x86\x1b\xbf\xb2\xe5\xfc\xe6\xcf\x6f\xfa\x74\x14\x45\
\x1d\xab\x2e\xba\xa4\xec\xfb\xe2\x2a\x05\x61\x08\x03\x03\xd0\xd1\
\x01\xa5\x12\x77\xcc\x76\xb0\x6b\xcf\x9c\x4a\x4d\x11\xe1\xdc\xd4\
\x74\x18\x86\x21\x95\x4a\x85\x62\xb1\x48\xb5\xea\xaf\x31\x4d\x63\
\xb3\x32\x68\x4e\xd7\xa6\x27\x57\xac\x58\xfe\xa7\x74\xa6\xf6\xbf\
\x86\xa9\xb0\x4c\x8b\xb8\xfd\x09\xfa\xfb\xb9\x6e\x68\x88\x6d\xc5\
\x22\xb5\x33\x33\xbc\x6e\xdb\x3c\x9d\x48\x10\xfc\x1f\x86\x93\xb9\
\x1a\xfd\x43\x9a\xa3\x00\x00\x00\x00\x49\x45\x4e\x44\xae\x42\x60\
\x82\
\x00\x00\x02\x77\
\x89\
\x50\x4e\x47\x0d\x0a\x1a\x0a\x00\x00\x00\x0d\x49\x48\x44\x52\x00\
\x00\x00\x10\x00\x00\x00\x10\x08\x06\x00\x00\x00\x1f\xf3\xff\x61\
\x00\x00\x00\x19\x74\x45\x58\x74\x53\x6f\x66\x74\x77\x61\x72\x65\
\x00\x41\x64\x6f\x62\x65\x20\x49\x6d\x61\x67\x65\x52\x65\x61\x64\
\x79\x71\xc9\x65\x3c\x00\x00\x02\x19\x49\x44\x41\x54\x78\xda\x8c\
\x93\xbd\xaf\xa1\x41\x14\xc6\xcf\xcb\x2b\xe2\x26\x16\x05\xb1\x42\
\x43\xa2\x11\xbd\x66\x23\xa2\x22\xb9\xff\xc1\xaa\xf7\xd6\x1a\x0a\
\x09\x89\x46\xb7\xd1\xdd\x68\x97\xbf\x60\x2b\x8a\x0d\xb1\x85\x8f\
\x42\x50\xae\x50\x21\x44\x04\xb1\xbe\x3f\x76\x9e\xb3\x5e\xb9\x37\
\x5b\xac\x93\x8c\x31\x73\xcc\xef\x79\xce\x99\x21\x25\x93\x49\xba\
\x5e\xaf\x24\x49\xd2\x33\x11\x7d\xa4\xff\xc7\x8f\xf3\xf9\xdc\x3b\
\x1e\x8f\x94\xc9\x64\x48\xc6\x8e\x4a\xa5\xa2\xd3\xe9\x64\x4b\x24\
\x12\xaf\x22\xc9\x40\x0c\xb1\x77\x1f\x58\xf7\x7a\x3d\x2a\x95\x4a\
\x2f\x37\x50\x0f\x1f\x00\x3c\x8b\x24\x94\x3f\xb5\x5a\x2d\x9a\x4e\
\xa7\xa4\x56\xab\xc9\x60\x30\xd0\x78\x3c\x26\x9d\x4e\x47\xbb\xdd\
\x8e\xdc\x6e\x37\xad\xd7\x6b\x4a\xa7\xd3\xaf\xf1\x78\x1c\x10\x49\
\x8c\x5f\x92\x50\xfd\xf2\x88\x32\x20\xc3\xe1\x90\x34\x1a\x0d\xcb\
\x67\xb3\xd9\x68\xa3\xd1\xf8\x2a\xa3\x16\xfc\xe8\x72\xb9\xfc\x33\
\x2b\x10\x28\x87\x42\x21\x2a\x16\x8b\x64\xb5\x5a\xc9\x62\xb1\x50\
\xbd\x5e\xdf\x71\xf9\x02\x20\xfa\x27\x51\xb3\xd9\xa4\x6e\xb7\xcb\
\xfd\xa8\x56\xab\xd4\xef\xf7\xa9\xdd\x6e\x93\x2c\xcb\x34\x9f\xcf\
\xa9\x50\x28\xd0\x6c\x36\xa3\x72\xb9\x8c\x86\xd3\x7e\xbf\x97\xb8\
\x07\x0a\xc0\xe7\xf3\xdd\x95\x03\x81\x00\xcf\x18\x70\xe8\xf7\xfb\
\xd9\x89\x56\xab\xa5\x5a\xad\xc6\xd0\xc3\xe1\xf0\x17\x00\x12\x00\
\xb9\x5c\x8e\xed\x79\xbd\x5e\x4a\xa5\x52\x64\xb3\xd9\xc8\xe9\x74\
\x52\x24\x12\xa1\x7c\x3e\x4f\x66\xb3\x99\x3c\x1e\x0f\x94\x19\x70\
\x77\x00\x12\x00\xe1\x70\x98\x1d\x38\x1c\x0e\xee\xbc\xc9\x64\xe2\
\x32\x50\x52\x30\x18\x64\x37\xc8\x0d\x06\x03\x06\x88\xa6\x32\x40\
\xa5\x38\xc0\x95\x2d\x16\x0b\xae\x0f\xca\x88\xd1\x68\xc4\x80\xc9\
\x64\x42\xcb\xe5\x92\x0f\xe2\xb6\xde\xf5\x00\x24\x6c\xc0\x32\x1c\
\xe0\x40\x2c\x16\xbb\x5f\x29\x94\xed\x76\x3b\xcf\x6f\x01\xdb\xed\
\xf6\xbd\x03\x58\x53\x1c\x54\x2a\x15\xea\x74\x3a\x3c\x03\x88\x1c\
\xe6\xdb\x41\x5a\xad\x56\x70\xcc\xaf\x58\x56\x48\x8a\xed\xb7\x25\
\xa0\x0f\x58\xbb\x5c\x2e\xe5\xff\x82\x07\xf4\x3d\x1a\x8d\xfe\x14\
\x8e\x26\x0c\x00\x49\x51\xc7\x7d\x23\xb0\x36\x1a\x8d\xac\x86\x40\
\x0e\x00\xc4\x66\xb3\x69\x89\x7e\x7c\x13\x5f\x57\x2c\xa8\xd7\xeb\
\x3f\x0b\x7b\x36\x7a\x30\x84\xf2\x48\xf4\x2d\xaf\xbc\x60\xd8\x7f\
\x12\xe3\x03\xfa\xf1\xc0\xf9\xeb\x4d\xf9\x37\x2f\x04\xe0\x8f\x00\
\x03\x00\xe7\xe3\x7a\x6e\x30\xbb\xf3\xb7\x00\x00\x00\x00\x49\x45\
\x4e\x44\xae\x42\x60\x82\
\x00\x00\x06\x71\
\x89\
\x50\x4e\x47\x0d\x0a\x1a\x0a\x00\x00\x00\x0d\x49\x48\x44\x52\x00\
\x00\x00\x90\x00\x00\x00\x90\x08\x02\x00\x00\x00\x68\x24\x75\xef\
\x00\x00\x00\x03\x73\x42\x49\x54\x08\x08\x08\xdb\xe1\x4f\xe0\x00\
\x00\x00\x09\x70\x48\x59\x73\x00\x00\x0e\xc4\x00\x00\x0e\xc4\x01\
\x95\x2b\x0e\x1b\x00\x00\x06\x14\x49\x44\x41\x54\x78\x9c\xed\x9d\
\x4b\x76\xa3\x30\x10\x45\x71\x8e\x07\xc9\x72\xb2\x9d\x64\x7d\xde\
\x4e\xb2\x1c\x0f\xe9\x01\x69\x2c\x0b\xa1\x6f\x7d\x5e\x95\xf5\x66\
\xdd\xb1\x41\xd4\xd5\xe5\x23\x0b\xb8\x7c\xbd\xff\x2c\xcb\x72\xbb\
\x7f\x2e\x18\xf9\xfe\xf8\xd5\x6e\x42\x1c\xa8\xe2\x5c\x36\x60\x5b\
\xa0\x5a\xa6\xdd\x84\x47\x10\xca\xb2\x17\xe4\xb2\xae\x6b\x54\x1d\
\x84\xf6\x6d\x01\xc1\xa6\x5b\x90\xa8\x08\xd7\xb3\x4f\x20\x60\xdb\
\xda\x00\x82\x4d\x3e\xc7\x0d\xbf\xdd\x3f\x2f\xeb\xba\x26\xff\xb6\
\x7f\x82\xbd\x5d\x75\x51\xc4\x26\x5f\x84\x0c\x8e\x84\x61\xc7\x6f\
\x22\x60\x7b\x11\xdb\x32\x1b\xb8\x55\xe0\xcf\xb0\xfc\x47\xc3\x2f\
\x20\x44\x18\x9b\xcc\x86\x57\xd6\xbf\x60\xd8\x71\x89\x08\xd8\x9c\
\xd9\x56\xb3\x21\x7b\xd9\x1f\x86\x55\x7e\x33\xfa\xbe\x7a\x04\xb0\
\xf1\x6d\x6c\x47\xc1\x1b\x0c\x3b\xae\x09\x01\x9b\x51\xdb\x9a\x1a\
\x1c\xd6\xf9\xc9\xb0\xd6\x05\x1d\x17\xa7\x1b\x26\x6c\xb4\x1b\x38\
\x58\xe1\x4e\xc3\x8e\x2d\x40\xc0\x06\x6e\x5b\x5f\xc3\xa2\xc2\xbe\
\xe5\xff\xdc\xd4\x1a\x90\x4a\x21\x74\x9d\x28\x84\xc5\x21\x30\x2c\
\x8c\xba\x6d\x61\x5d\x6e\xf7\x4f\xf5\x3e\x34\xd8\x80\x63\x25\x13\
\xc0\xc6\xb7\x53\x05\x5b\xb2\xcd\x8a\x3b\x49\xa6\x95\x12\x1b\x16\
\x46\x0c\x5b\xe5\x25\xa7\x18\x36\xaa\x15\x25\x4b\x97\x06\x46\xb8\
\x33\x61\xc5\xd6\x71\x72\xcc\x8a\x4d\xa0\x4f\x30\x1a\x16\x86\x1c\
\x5b\x77\x69\x98\xb0\x91\x2f\xf0\xac\x56\xa7\xc0\x38\x8e\xd8\x24\
\xd8\x48\x5a\x45\x88\x4d\xf8\x00\x29\x64\x58\x98\x6e\x6c\x4c\xbd\
\xb8\x7b\xb1\x7c\xa8\x32\xc5\xc9\x01\x63\x3d\x2d\x6e\xc2\xc6\xda\
\x8b\x3b\xb0\x29\x5e\x2d\x28\x18\x16\xa6\x88\x4d\xac\x34\x95\xd8\
\xd4\xc7\x9a\x0b\xc0\x64\xae\x3d\x93\xd8\x54\x7a\x71\x06\x9b\xfa\
\x35\xf8\x96\x78\xf0\xf7\x18\xf9\x5f\x0b\x59\xaf\x63\xea\xa3\xd8\
\x63\x32\x89\xc7\x12\x3b\x16\x41\x1b\x90\x8e\xbc\x40\x8e\x49\x2e\
\x35\xc0\xe4\x83\x50\x29\x95\xb1\xec\x9a\x0d\xaf\x02\x26\x5f\xc1\
\xdb\xfd\x53\x0b\x1b\xce\xcf\x0e\xc9\x28\x9f\x25\xe6\x63\x74\x0c\
\xb0\x2f\x95\x1d\xb4\x76\x97\xa8\xb8\x9b\x12\xb0\x0d\xdc\xaa\x30\
\xd0\x86\x85\xb1\x32\x06\xd8\x97\xfa\x1e\xd9\x70\xd2\x81\x70\x2e\
\x40\x68\x9b\x21\xab\xc2\x98\x31\x2c\x0c\xec\x18\x60\x5f\x9a\xba\
\x60\xdb\x69\x3d\x82\x64\x7b\x3a\x6c\x33\x6a\x55\x18\x93\x86\x85\
\xc1\x19\x03\xec\x4b\x6b\x9f\x6b\xbe\x70\x86\x92\x6c\x4f\xc6\x36\
\x07\x56\x85\x31\x6f\x58\x98\xc8\x36\x7c\x4e\x1d\xbd\xbf\x67\x68\
\x0a\x53\xb2\x3d\xe0\xcd\x1b\x8c\x2b\xc3\x16\x0b\x56\xed\xe9\xeb\
\x58\x9d\x83\xbf\x80\xbd\xd8\xd9\xb1\xea\x2c\x1e\x0c\xb3\xc8\xa9\
\xbb\xc7\xf7\xff\xbc\x82\x20\xd9\x8b\x58\x15\xc6\xaa\x61\xa6\x39\
\x8d\xf4\xf5\xa1\x1f\x30\x55\x24\x7b\x41\xab\xc2\x58\x32\xcc\x07\
\xa7\xc1\x5e\x3e\x3a\x45\x40\xec\x0e\x7b\x1f\xb4\xc6\x83\x6e\x98\
\x33\x4e\xe3\xfd\x9b\x60\x12\x0e\xdf\x9d\x29\xce\x68\x91\x04\xd1\
\x30\xaf\x9c\x48\x7a\xf6\xd5\x6b\x75\xbc\x06\xd1\x30\xb4\x8c\x9b\
\x41\x78\x77\x24\xd9\x44\x52\x84\x81\x0f\xa6\xd0\xde\x8c\x3a\x18\
\x1a\x60\x8e\x69\x8d\x87\x96\x37\xe5\x54\x6d\xc7\xd8\x70\x24\xc3\
\x3d\xad\xf7\x11\x72\xd2\xc4\x37\x43\x38\x86\x07\x22\x99\x8d\xa1\
\x29\xa3\xe1\x60\x4c\x7f\xbb\x91\x63\x84\x08\x92\xd9\xfb\x79\xc5\
\x4a\x98\xe8\xb2\xdc\xd0\xe7\x18\xa4\xba\x64\xb6\xa7\x08\xc0\x86\
\x8f\x2b\xd7\x2d\xb3\x8e\x71\xea\x4a\xe6\x67\x9a\x1b\x4e\x58\x89\
\x32\xde\x94\xee\x18\xaa\xa2\x64\x0e\xa7\x6a\xeb\x86\x9b\x25\xef\
\x63\x1f\x1c\xa3\xd5\x92\xcc\xc9\xed\x46\x20\x11\xa0\xc8\xfe\x60\
\x15\xc7\x80\x55\x24\x33\x7c\xcb\x2c\x5a\x64\xf8\x49\x3c\xba\xc8\
\x31\x66\x79\xc9\x8c\x3d\xf6\x01\x36\x62\xe4\x84\x1e\x0e\xe6\x18\
\xb6\xb0\x64\x4f\x6f\x99\xcd\x04\x67\xe6\xd0\x8b\xa7\x16\xd8\x0c\
\x48\xe6\xbc\x44\x9a\x88\xed\x81\x44\x9f\x97\x38\x8f\x64\xe3\x91\
\x7b\x84\xac\x63\x5a\xe3\xa1\x3f\xad\x9f\xd8\x8a\x91\x91\xac\x00\
\x6c\x72\x12\x08\xd7\xd0\xd4\x84\x57\x8c\x80\x64\x39\x60\x93\x90\
\x40\x78\x7f\x5e\x99\x08\x8b\xe1\x96\xec\x14\xd8\x64\x23\x10\x89\
\x29\x02\x13\x64\x31\xac\x92\xa5\x81\x4d\x2a\x02\x91\x9b\xe6\x36\
\x71\x16\xc3\x27\x59\x02\xd8\xe4\x21\x10\xe9\xa9\xda\x13\x6a\x31\
\x4c\x92\x91\xbd\xda\x9e\x69\x39\x2e\xa3\x73\xbb\xd1\x44\x5b\x0c\
\x87\x64\x4f\xc0\x26\x03\x81\x68\xde\x32\x3b\x01\x17\x43\x2e\xd9\
\x03\xd8\xac\xbe\x40\xf4\x1f\xfb\x30\x31\x17\x43\x2b\xd9\x1f\xb0\
\x59\x77\x81\xa0\x3c\xba\x68\xc2\x2e\x86\x50\xb2\xb7\x65\x56\x5c\
\x24\x54\xcc\x2e\x5f\xef\x3f\x24\x85\x9e\xf3\x44\x65\x52\x7e\x53\
\x7a\x4d\xbc\xd2\x22\x7c\x6d\xfb\x42\xb4\x07\x42\x7c\xf1\x36\x42\
\x38\x5e\x6d\x4b\xc2\x9e\x60\xe6\xaf\x33\xbd\xc0\x8f\xc4\xd3\xb0\
\x47\x64\x5e\x18\x3d\xb8\x84\x51\xc3\x7c\xe8\x05\x6e\x55\x98\x57\
\x37\x4c\xc0\xaa\x28\x83\x5d\x7c\xc8\x30\xd3\x7a\x19\xb2\x2a\xcc\
\x2b\x1a\x26\x6f\x55\x94\x91\x8e\xde\x6f\x98\x45\xbd\x8c\x5a\x15\
\xe6\x55\x0c\x53\xb7\x2a\x4a\x77\x77\xef\x34\xcc\x90\x5e\x50\x9c\
\xc6\xe3\xdc\x30\x64\x5a\x72\x13\x49\xf1\xf5\xda\x39\xf9\x7b\xa7\
\x95\x37\xc3\x92\xc7\x2a\x58\x6c\x1d\xad\x6a\x3e\x86\x61\x6e\xf9\
\x52\xb1\xf7\xdb\x5a\x8e\xbc\x93\xac\x89\x07\xc3\x9a\xce\x00\xd1\
\x6c\x6b\x6d\x4c\x9b\x61\x50\x9b\xba\x0c\xe8\x62\xd7\x36\xab\x86\
\x91\x5c\x57\x81\xd8\xd6\xd4\x86\x06\xc3\x10\xb6\x6d\x61\xd0\xc2\
\x96\x6d\x96\x0c\x63\x1d\xad\xd0\xb5\xad\x7e\xd5\xb5\x86\xe9\xea\
\x25\xd6\xfd\xf1\x6d\x43\x37\x4c\x65\x0c\x50\xc5\xb6\xca\x35\x56\
\x19\xa6\xa2\x97\x7a\x37\x07\x39\x66\x47\x01\x35\x4c\x9d\x96\x4a\
\x6a\xba\x48\x19\x98\x64\x47\x43\x1b\x03\xdc\x76\xc8\x50\xbd\x07\
\xe5\x01\x97\xc9\xa2\x28\x9e\x02\x44\x2b\xdd\xfe\x29\xd0\x87\xbe\
\x3f\x7e\xf3\xdb\x5b\x00\x26\xd0\x44\xb4\x31\xc0\xcc\x8a\xc4\xb0\
\x65\xa2\x69\x58\x13\x03\x01\x6c\x95\x0b\xe7\xc6\x96\x97\x2c\x07\
\x8c\xaf\x4d\x68\x63\x80\x1d\x0b\xd4\xb2\x4d\xda\x30\xc2\x3b\x65\
\x48\x16\x35\xb8\x10\x26\x6c\x19\xc9\x4e\x81\x91\x37\x02\x6d\x0c\
\x90\xb0\x3d\x92\xb6\x49\x18\xc6\x7a\xe0\xe9\xc0\xc6\xd4\x1e\x5a\
\x6c\x67\x92\xa5\x81\x51\xad\x15\x6d\x0c\x50\xa0\x3d\xdc\xb6\x71\
\x19\xa6\x72\xf1\x94\xc1\x26\xdc\x1e\x12\x6c\x49\xc9\x12\xc0\x06\
\x57\xa3\x3e\x2e\x10\xb5\x5f\xb1\x3d\x1c\xb6\x51\x8e\x25\xa2\x8d\
\xe2\x2c\x00\xbd\x67\x19\x2b\xcb\x11\x76\x6c\x58\x5f\x77\x40\xa8\
\x4b\x32\x38\xbf\x6f\x51\xd9\x16\xdf\x94\xde\xba\x44\xcc\x1b\x81\
\x93\x41\xc0\xb6\x65\xa4\xc8\x4f\x86\x35\x2d\x08\x67\xfb\x2b\xe3\
\xc3\xb6\x27\xc3\x2a\x17\x21\x70\x5d\xc5\x1d\x04\x6c\x5b\x5a\x6b\
\xfe\x30\xac\xe6\x9b\x38\xdb\x39\x18\xbb\xb6\x3d\x0c\xcb\x7f\x47\
\xf8\x12\x58\x32\x08\xd8\xb6\xd4\x20\xb8\x16\x3f\x8a\xb3\x3d\x4c\
\xb1\x65\xdb\x9f\x61\xc9\x0f\x29\x8e\x56\x68\x05\x01\xdb\x96\x33\
\x22\xd7\xe4\xdf\x70\xda\x2d\x1c\x7c\xdb\x2e\xeb\xba\x86\xff\xab\
\xde\x56\x84\xb9\x37\x5b\xd4\x4b\xb1\x27\xac\xc9\xe3\xb5\xc0\x20\
\xed\xc3\x01\xb6\x05\xa4\x2c\xcb\xff\xca\xfc\x03\x0c\x3a\xb7\xd7\
\x9d\x1e\xca\x90\x00\x00\x00\x00\x49\x45\x4e\x44\xae\x42\x60\x82\
\
\x00\x00\x07\x3c\
\x89\
\x50\x4e\x47\x0d\x0a\x1a\x0a\x00\x00\x00\x0d\x49\x48\x44\x52\x00\
\x00\x00\x18\x00\x00\x00\x18\x08\x06\x00\x00\x01\x97\x70\x0d\x6e\
\x00\x00\x00\x06\x62\x4b\x47\x44\x00\xff\x00\xff\x00\xff\xa0\xbd\
\xa7\x93\x00\x00\x00\x09\x70\x48\x59\x73\x00\x00\x0b\x13\x00\x00\
\x0b\x13\x01\x00\x9a\x9c\x18\x00\x00\x06\xdc\x49\x44\x41\x54\x48\
\xc7\x55\x95\x59\x6c\x54\xd7\x19\xc7\xff\xe7\x2e\x73\x77\xcf\x6e\
\x7b\xc6\x0e\x60\x30\x13\xb1\x04\x12\x07\x95\x94\x90\x1a\xda\x4a\
\x49\x53\x35\x54\xb4\x52\x9a\x86\xb4\x4d\xe9\xf2\xd4\x28\x6d\x43\
\x15\xa9\x2f\x51\x93\x80\xd2\x2c\x28\x52\x15\xa9\x8d\x68\x95\xbc\
\x44\x6d\x1a\x51\xd2\x46\x4d\xd8\x8c\xed\xb8\x40\x69\x4b\xd8\xed\
\x19\xb0\xc7\x60\x7b\x6c\x33\x1e\xcc\xc0\x8c\x67\xee\xb9\xe7\x7c\
\x7d\x18\x6c\xc8\x79\x3c\xba\xff\xef\xf7\x2d\xff\xef\x1e\x46\x44\
\x08\x82\x00\x35\xbf\xbe\x16\x44\x84\xcf\x4e\x9d\xa1\x6a\x6d\x8e\
\x40\x44\xe8\xe8\xc8\xd0\xa9\x33\xa7\x09\x9c\x73\xf4\xf7\x0f\xbc\
\xc2\x39\x07\xab\xd7\xeb\xb8\x59\xad\xd0\xa9\xcf\xce\x40\x79\x60\
\xfd\x43\x64\x1a\x26\xda\xda\xd3\x0c\xb7\xa2\x85\xa7\xaf\x16\xbb\
\x87\x72\x59\xf2\x7d\x9f\xfe\x75\xec\x18\x29\x00\xd0\xdb\xd7\x3f\
\x1b\x08\x7e\x64\xe9\x92\x0e\x1c\x3c\x74\x08\xba\xa6\x6d\x54\x00\
\xa0\xe7\x50\xdf\xef\xbf\xfb\xf8\xf7\xf0\xe0\x86\x4d\x88\x44\x23\
\x6c\x5d\x57\xd7\x00\x82\x20\x40\x10\x04\x10\x42\xe0\xe4\xc9\x53\
\xef\x07\x41\x00\xce\x39\x10\x04\x01\xe3\x9c\xe3\x70\x4f\x2f\x15\
\xa6\x26\x89\x73\x4e\x44\x04\x85\x31\x46\xfd\xfd\x03\x57\x97\x74\
\x2c\x42\x22\x16\x47\xff\xc0\x00\xc6\xc6\x26\xb6\xb3\x6c\x2e\x07\
\xd7\x75\xc9\x75\x5d\x10\x49\x9c\x3c\x79\x1a\x89\x64\x8c\xb1\xf5\
\x5f\xd8\x48\xb3\xb3\xb3\xf0\x03\x1f\x6f\xbd\xf5\x3b\x28\xaa\xa2\
\xdc\x7b\xef\x1a\x52\x5e\xda\xf9\x1b\x16\x8f\xc7\x91\x6e\x49\x61\
\xa6\x58\x44\x24\xd2\x44\xc9\x78\x02\x8c\x88\x20\x84\x00\x11\x31\
\xc6\x98\x02\x40\x9c\x3b\x7f\x61\xa0\x52\x99\xdb\x90\x6a\x6b\x46\
\xba\x35\x8d\xf2\xf5\xeb\xc5\x58\x2c\x96\x94\x52\x40\xc1\xad\xc3\
\x18\x23\x55\x55\xc5\x3f\x3e\xfa\x27\x01\x6c\xc3\x5d\x8b\xd2\x48\
\xc6\x93\xd0\x35\x0d\x60\x48\x1c\xea\x39\x42\xa3\xa3\x57\x9e\x66\
\x44\x84\xb3\xe7\x06\x11\x08\xfe\x66\xf9\x7a\xf9\x99\x74\x3a\x05\
\xaf\xc9\x45\xc4\x0b\x43\xd3\x35\x0c\x65\xb3\x18\x1f\x2f\x20\x95\
\x6e\xc5\xdd\x99\x0c\x63\x44\x84\x07\xd6\x7f\x89\x0a\x93\x13\x10\
\x42\x62\xd7\xae\x97\xf1\xd4\x53\x4f\x80\x73\x8e\x81\xa3\x47\xe1\
\xd7\x39\xc2\x61\xef\x52\xe9\x5a\xa9\xb3\xab\xab\xab\x91\xd2\x93\
\xdb\x9e\x78\x36\x9d\x4a\xa3\xb5\xa5\x05\xaf\xbd\xfa\x3a\x56\xaf\
\xee\x42\x26\xb3\x0a\x9e\xe7\xc1\xf5\xec\xfd\x3e\xf7\x3b\xd3\xe9\
\x74\x23\x75\x22\xc2\x81\xfd\x3d\xf0\xb9\xcf\xc6\xc6\xc7\x9b\x4e\
\x9c\x38\xf1\xb7\x2b\x57\xc6\x36\xc9\x40\xe0\x97\x3b\x9e\xfd\x51\
\xba\x2d\xb5\x67\xd5\x8a\x95\x60\x8c\x35\x8a\x9d\x9f\xdd\xfc\xcc\
\x38\xe7\x98\x9e\x9e\x5e\xdf\xd3\xd3\x77\x64\x24\x9f\x7f\x4e\x92\
\x9c\xbf\x67\x44\x74\xbb\x4b\x00\x34\xc6\x18\x14\x45\xd1\xff\x77\
\xf2\xf4\xb1\x44\x32\xde\xed\x78\xee\xab\x22\x10\x54\x2a\x95\xbe\
\x09\x80\x01\x58\x10\x38\x00\x02\x55\x55\xf1\xf1\x27\x07\x2b\xf3\
\x9d\x32\x42\x21\x28\x8a\x82\x64\x32\xb9\xf7\xe2\xa5\xe1\x67\xee\
\x14\x54\x1a\xed\x3d\xff\x46\x34\x1a\xd1\x4d\x2b\x04\xdb\xb6\x61\
\x99\x16\x82\x20\xc0\xb1\x7f\x1f\xc7\xf0\x70\x7e\x37\x00\x28\x8c\
\x31\x30\xc6\x30\x57\xab\x3f\x34\x3a\x7a\xf9\xe7\x91\x68\x04\x8e\
\xe3\xc0\x73\x1c\xa8\x8a\x82\x89\xc2\x04\xaa\x95\x1a\x9a\x9b\x93\
\x8d\xbc\xcf\x5f\xc8\x82\x31\x86\x5c\x2e\xdb\x77\x77\x26\x03\xc7\
\xb1\xe0\xd8\x0e\x34\x4d\x47\xad\x56\x43\x36\x77\x11\x9a\xaa\x63\
\x79\x66\xd9\x63\x00\xa0\x08\xc9\x01\x12\x1f\x64\x32\xcb\x11\x8d\
\x47\x60\xdb\x36\x0c\xd3\x00\x63\x0c\x17\x86\x06\x21\x85\x84\xeb\
\xba\xf5\x42\xa1\xf0\x77\x00\x50\x86\x2e\x64\x7f\xf6\xad\xad\x8f\
\x6f\xdd\xbc\xe9\xab\xd8\xf6\xe4\xd3\xf0\x1c\x0f\x66\xc8\xc0\x4c\
\x69\x06\xe3\x63\x05\xc4\x62\x71\x5c\x9b\x9d\x59\x5c\x2c\x16\x01\
\x00\xca\xd4\xe4\x74\x53\x2c\x16\x43\x32\x99\x44\x3e\x9f\x47\x5b\
\x7b\x07\xde\x7b\xef\xcf\xb8\x34\x3c\x8c\x58\x3c\x8e\x20\xe0\x7d\
\x8c\xa9\x53\x2b\x57\xae\x68\x08\x56\xac\x5e\xf1\x32\x63\x0c\xae\
\xe3\xa2\xc9\xf5\x90\x6a\x69\xc5\x0b\x2f\xbc\x88\xe3\x47\x4f\x20\
\x91\x88\x22\x10\xbc\xdb\x30\x34\x08\x21\x1b\x02\x92\x12\x3b\x7e\
\xb5\xc3\xf6\x3c\x0f\x9e\xe7\x21\x1a\x8d\x20\x16\x8d\xe1\x8f\x7b\
\xde\x41\xad\x56\xfb\x83\xae\xeb\xb8\x6f\xed\x7d\x48\xc4\xe2\x0d\
\x01\x24\x83\xe7\x3a\xf5\xed\x3f\xde\xce\xba\x37\x77\x6f\x8f\x27\
\x13\x81\xeb\x79\x58\x75\xcf\xaa\xaa\xae\xeb\x3f\x4d\xb5\xa6\xe0\
\x79\x1e\x88\xe8\xb6\xf9\x84\x10\x0b\xfe\x20\xa2\x79\xa3\x31\xba\
\xf5\x95\xaa\xaa\x28\x16\x67\xbe\x76\xfa\xf4\x99\x0f\x6e\x56\x2a\
\x56\x3c\x1e\x43\x3c\x11\x87\xeb\x3a\x50\x15\x65\x4e\x53\xb5\xb7\
\x2d\xcb\xda\x6d\xdb\x76\x1e\x00\xa4\x24\x00\x04\x5d\xd7\x3f\x0f\
\x20\x22\x0d\x40\x2b\x63\xac\x00\x40\xcc\x07\x1f\x1e\xc9\xbf\x74\
\x61\x30\xfb\xeb\x48\xb8\x09\xae\xeb\xc2\x71\x6c\x84\x0c\x1d\x96\
\x65\xc1\xb5\x1d\x18\x86\x01\x45\x51\x50\x2e\x97\xe9\xc6\x8d\x1b\
\x6f\xa4\x52\xa9\xe7\x18\x08\x4c\x51\x3f\x07\x60\xb7\x8b\x68\x54\
\xc1\x39\xf7\x8e\x1e\x3d\xfe\x69\xdd\xf7\xd7\xc4\xe3\x71\x58\xb6\
\x09\xc7\xb1\x61\x18\x06\x4c\xd3\x84\x63\xdb\xd0\x35\x1d\x44\x04\
\xdf\xf7\x31\x39\x35\x85\xfc\xe8\x28\xaa\x95\xb9\xe2\x97\x37\x6f\
\xba\xdf\xb2\xcc\xcb\x77\x6e\x0f\x01\x20\xc6\x18\x34\x4d\x43\xa9\
\x74\xed\x91\x8f\x3f\x39\x50\x56\x35\x6d\x4d\x7b\x7b\x3b\x22\x91\
\x08\x3c\xcf\x85\x69\x99\x70\x1c\x07\xae\x6d\x43\x57\x35\x10\x11\
\xaa\xd5\x2a\x86\xf3\x23\x18\x1e\xc9\x43\x04\x12\x9e\xe7\x25\x86\
\x86\xb2\x3f\x04\x00\x0d\x00\xa6\xa6\xa7\xef\xa0\x50\xe8\xf2\xe8\
\xd8\x87\x53\x53\x57\x1f\x6e\x6f\x6f\x87\x63\x3b\x30\xcc\x10\x42\
\xa6\x0e\x33\x64\xc0\x32\x2d\x84\x42\x21\xa8\x8a\x02\x41\x84\x72\
\xb9\x8c\x5c\xee\x22\x2a\x95\x2a\x84\x10\x30\x8c\x10\x16\x2f\x59\
\x34\xd6\x96\x4a\xed\x59\x00\x14\xaf\xce\x34\x16\x49\xd3\xd6\x15\
\x26\x27\x07\x38\xe7\xa1\x8e\x25\x8b\x61\x58\x06\x4c\x33\x84\x50\
\x28\x04\xc3\x34\x61\x19\x06\x74\x4d\x87\xa2\x28\x08\x84\x40\x71\
\xa6\x88\xa1\xa1\x1c\x38\x0f\x40\x44\x08\x87\xc3\x88\x46\x23\x7d\
\x86\x11\xea\x9e\x29\x95\xd0\xd2\xdc\xdc\x00\x98\xa6\x89\xc1\xc1\
\xec\xf3\xbd\xbd\xbd\xbb\x84\x94\x58\xbc\xe8\x2e\x68\xba\x8a\x75\
\xeb\xee\x47\x93\xd7\x04\x92\x12\x44\x8d\x87\x4f\x61\x0a\x38\xe7\
\x18\x9f\x2c\x20\x37\x94\x03\x11\x60\x9a\x16\xa2\xd1\x08\xca\x37\
\xae\xbf\x52\x98\x9c\x78\x7e\xa2\x30\x0e\xcb\xb2\x6e\x03\xde\xff\
\xcb\x5f\x3f\xdc\xbb\x77\xdf\x37\x18\x63\xa8\xd5\x6a\xf0\xb9\x0f\
\x9f\x73\x54\x2a\x15\xd4\xeb\x75\x6c\xdc\xf8\x20\x76\xee\x7c\x11\
\x6b\xd7\xdc\x03\x22\x42\x6e\xf0\x22\x2e\x5d\x1a\x5e\x08\x6c\xd9\
\x26\x8a\xc5\xe2\x4f\x82\x80\xbf\x1d\x0a\x85\xd0\xd9\xd9\x09\xcb\
\xb2\x6e\xef\xc1\xbe\x7d\x1f\xb5\xbf\xfb\xce\xbb\xff\x19\x1f\x9f\
\x68\x99\x87\x08\x21\x20\x84\x80\x94\x12\x04\x42\xcd\xf7\x51\x9b\
\x9b\xc3\xf7\x7f\xb0\x0d\x5b\xb6\x3c\xd6\xf8\xfd\x47\x9a\x00\x10\
\x4a\xa5\x6b\x0f\x83\xb1\xfd\x52\x4a\x2c\x5d\xda\x81\x70\x53\x13\
\xa4\x94\x68\x4e\x24\x1b\x80\x83\x87\x7a\x00\xc6\xd0\x7b\xb8\xf7\
\xf5\x9e\xc3\x47\x7e\x21\xa4\x80\xaa\xaa\x90\x52\x2e\x40\xa4\x94\
\x20\x49\x98\xab\xcd\x21\x95\x4e\x61\xf7\x9b\xaf\x41\xd7\x35\xbf\
\x58\x2c\x7e\xc5\x34\xcd\x4f\x89\x08\xaa\xaa\xc2\x73\x3d\xa4\xd3\
\x69\xa8\xaa\x0a\xdb\xb2\x6e\x3d\x23\x07\x7a\x1a\x0e\x92\x84\xd9\
\xd9\x59\x0c\x8f\x8c\x7c\xe7\xec\xd9\xb3\xbf\x9d\x9a\x9c\xba\x2b\
\x08\x02\xa8\xaa\x0a\xc6\xd8\xc2\x42\x56\xab\x73\xd8\xfa\xed\x2d\
\x37\x1e\xfd\xfa\x23\x5f\x94\x52\x9e\xe3\x9c\xa3\xb5\xa5\x15\x6d\
\xe9\xf4\xc2\xac\x00\x40\x51\x94\x5b\x15\x1c\x3c\x3c\xef\x52\x95\
\x88\x70\xbd\x7c\x53\x08\x21\x50\xab\xd5\x50\x2a\x95\x50\xaf\xfb\
\xeb\x54\x55\x79\x94\x29\xc8\x44\xc2\x91\xd9\x65\xcb\x96\xfe\x29\
\x12\x0d\xff\x57\x51\x19\x34\x55\x43\xa6\x73\x39\x74\x5d\x87\x94\
\x12\x77\x1e\x45\x51\xf0\x7f\x60\x84\x69\x65\x48\xcf\xfa\x14\x00\
\x00\x00\x00\x49\x45\x4e\x44\xae\x42\x60\x82\
\x00\x00\x07\x65\
\x89\
\x50\x4e\x47\x0d\x0a\x1a\x0a\x00\x00\x00\x0d\x49\x48\x44\x52\x00\
\x00\x00\x18\x00\x00\x00\x18\x08\x06\x00\x00\x01\x97\x70\x0d\x6e\
\x00\x00\x00\x06\x62\x4b\x47\x44\x00\xff\x00\xff\x00\xff\xa0\xbd\
\xa7\x93\x00\x00\x00\x09\x70\x48\x59\x73\x00\x00\x0b\x13\x00\x00\
\x0b\x13\x01\x00\x9a\x9c\x18\x00\x00\x07\x05\x49\x44\x41\x54\x48\
\xc7\x55\x95\x6b\x70\x54\xe5\x19\xc7\x7f\xef\x39\x67\x77\xcf\xd9\
\x73\x36\xd9\x4b\x16\xd8\x10\xb9\x08\xc6\x82\x8a\x8a\x99\x62\x11\
\x05\x6a\x47\xad\x9d\x8a\x83\x9d\xb1\x17\x6c\x6b\x69\xeb\x27\xed\
\x4d\x3a\x76\xec\x4c\x6d\x55\x1c\xab\x15\x1d\x3b\xf6\xc2\xd0\x8e\
\x8e\x2d\xb5\x6a\x29\xb6\x4e\xbd\x00\x21\x89\x29\x58\x6c\xb9\x5f\
\xb2\x81\x64\x03\x49\x36\x09\x9b\x4d\x08\x6c\xb2\xbb\xe7\xf2\xf4\
\x43\x48\xd0\xe7\xe3\x3b\xf3\x3c\xbf\xf7\x79\x9e\xff\xff\x7d\x95\
\x88\xe0\x79\x1e\xe5\x6a\xe5\x5a\x44\x84\x03\x07\x0f\xcb\x78\x79\
\x42\x10\x11\xe6\xcf\x6f\x94\x83\x87\x0f\x09\xae\xeb\xd2\xd6\xd6\
\xfe\xb4\xeb\xba\xa8\x4a\xa5\xc2\x85\xf1\x92\x1c\x3c\x70\x18\xed\
\xc6\x65\x37\x8b\x19\x31\x99\xdd\x50\xaf\xb8\x58\xad\x76\xe8\x6c\
\x61\x65\x47\x67\x56\xaa\xd5\xaa\xfc\x7b\xef\x5e\xd1\x00\x5a\x5a\
\xdb\x46\x3d\xdf\xdd\x7d\xf9\xbc\xf9\xec\xd8\xb9\x93\x90\x61\xac\
\xd0\x00\x9a\x77\xb6\xfe\xee\xab\xf7\x7e\x9d\x9b\x96\xaf\x22\x9e\
\x88\xab\xa6\xa6\xa6\x0f\xf0\x3c\x0f\xcf\xf3\xf0\x7d\x9f\xfd\xfb\
\x0f\xbe\xee\x79\x1e\xae\xeb\x82\xe7\x79\xca\x75\x5d\x76\x35\xb7\
\x48\x7e\x70\x40\x5c\xd7\x15\x11\x41\x53\x4a\x49\x5b\x5b\xfb\xd9\
\x79\xf3\xe7\x50\x97\x4c\xd1\xd6\xde\x4e\x6f\x6f\xff\x7a\x95\xed\
\xec\xc4\x71\x1c\x71\x1c\x07\x91\x80\xfd\xfb\x0f\x51\x97\x4e\x2a\
\xb5\xec\xd3\x2b\x64\x74\x74\x94\xaa\x57\xe5\xa5\x97\x7e\x8d\xa6\
\x6b\xda\x75\xd7\x2d\x11\xed\x89\x8d\xbf\x50\xa9\x54\x8a\xfa\x99\
\x19\x86\x0b\x05\x6e\xbb\x67\x6d\xd0\x9b\x9e\x21\x4a\x44\xf0\x7d\
\x1f\x11\x51\x4a\x29\x0d\xf0\x8f\x1e\x3b\xde\x5e\x2a\x4d\x2c\xcf\
\xcc\x9e\x41\xfd\xac\x7a\xc6\xce\x9d\x2b\x24\x93\xc9\x74\x10\xf8\
\x68\x5c\x0c\xa5\x94\xe8\xba\xee\xff\xf3\xed\x7f\x09\xa8\xe5\x97\
\xcd\xa9\x27\x9d\x4a\x13\x32\x0c\x50\xd4\xed\x6c\xde\x2d\x3d\x3d\
\x67\xee\x57\x22\xc2\x91\xa3\x27\xf0\x7c\xf7\x85\xb1\x73\x63\x0f\
\xd5\xd7\x67\x88\xd5\x38\xc4\x63\xb5\x18\x21\x83\x8e\x6c\x96\xbe\
\xbe\x3c\x99\xfa\x59\x5c\xd9\xd8\xa8\x94\x88\x70\xe3\xb2\x5b\x24\
\x3f\xd0\x8f\xef\x07\x3c\xf5\xd4\x93\xdc\x77\xdf\x57\x70\x5d\x97\
\xf6\x3d\x7b\xa8\x56\x5c\x6a\x6b\x63\xa7\x8a\x23\xc5\x85\x4b\x97\
\x2e\x45\x89\x08\x2f\xbe\xf8\x9b\xef\xfd\xf9\x4f\x5b\x9f\x77\x5d\
\x17\xd7\x75\xf1\x83\x80\x52\xe9\x02\x6f\xfc\xed\x35\x2a\x95\xf2\
\x7b\xcb\x9f\x79\xf6\x36\x0e\x1c\x40\xfa\xfb\xb3\x4a\x44\x78\xff\
\xbd\x66\xaa\x6e\x55\xf5\xf6\xf5\xd5\xec\xdb\xb7\xef\xef\x67\xce\
\xf4\xae\x0a\x3c\x9f\x1f\x6d\xf8\xfe\xb7\xeb\x67\x67\xb6\x04\xd7\
\x2c\x39\xd8\x07\x4b\xb2\xf0\xc4\xf4\xee\xa6\x76\xe6\xba\x2e\x43\
\x43\x43\xcb\x9a\x9b\x5b\x77\x77\xe7\x72\x0f\x07\x12\x4c\x9d\x2b\
\x11\xb9\x34\x25\xc0\x50\x4a\xa1\x69\x5a\xe8\x7f\xfb\x0f\xed\xad\
\x4b\xa7\x56\xda\x31\xe7\x19\xdf\xf3\xa5\x58\x2c\xde\x0d\x28\x60\
\x3a\xc1\x06\x3c\x5d\xd7\x79\xe7\xdd\x1d\xa5\xa9\x49\x45\xc2\x61\
\x34\x4d\x23\x9d\x4e\x6f\x3b\x79\xaa\xeb\xa1\x8f\x27\x94\x26\xc7\
\x7b\xec\xb9\x44\x22\x1e\x32\xad\x30\xd1\x68\x14\xcb\xb4\xf0\x3c\
\x8f\xbd\xff\xf9\x90\xae\xae\xdc\x26\x00\x4d\x29\x85\x52\x8a\x89\
\x72\xe5\xe6\x9e\x9e\xd3\x3f\x88\x27\xe2\xd8\xb6\x4d\xcc\xb6\xd1\
\x35\x8d\xfe\x7c\x3f\xe3\xa5\x32\x33\x66\xa4\x27\xef\x7d\xec\x78\
\x16\xa5\x14\x9d\x9d\xd9\xd6\x2b\x1b\x1b\xb1\x6d\x0b\x3b\x6a\x63\
\x18\x21\xca\xe5\x32\xd9\xce\x93\x18\x7a\x88\x2b\x1a\x17\xdc\x05\
\xa0\xf9\x81\x0b\xe2\xbf\xd9\xd8\x78\x05\x89\x54\x9c\x68\x34\x4a\
\xc4\x8c\xa0\x94\xe2\x78\xc7\x09\x02\x3f\xc0\x71\x9c\x4a\x3e\x9f\
\xff\x07\x80\xd6\x71\x3c\xfb\xe0\x3d\x6b\xef\x5d\xbb\x7a\xd5\xe7\
\x58\xf7\xb5\xfb\x89\xd9\x31\xcc\x70\x84\xe1\xe2\x30\x7d\xbd\x79\
\x92\xc9\x14\x23\xa3\xc3\x73\x0b\x85\x02\x00\xda\xe0\xc0\x50\x4d\
\x32\x99\x24\x9d\x4e\x93\xcb\xe5\x98\xdd\x30\x9f\xad\x5b\x5f\xe3\
\x54\x57\x17\xc9\x54\x0a\xcf\x73\x5b\x95\xd2\x07\x17\x2f\x5e\x34\
\x99\xb0\xe8\xea\x45\x4f\x2a\xa5\x70\x6c\x87\x1a\x27\x46\x66\xe6\
\x2c\x1e\x7b\xec\x71\x3e\xdc\xb3\x8f\xba\xba\x04\xcb\x9f\xdf\xf4\
\x97\xdb\x7e\xf2\x88\x24\x17\x5f\x2d\x25\x5d\xbf\x5e\x93\x20\x60\
\xc3\x8f\x37\x44\x63\xb1\x18\xb1\x58\x8c\x44\x22\x4e\x32\x91\xe4\
\x0f\x5b\x5e\xa6\x5c\x2e\xff\x9e\x7d\xfb\x7e\xce\x47\x1f\x31\x91\
\xcf\xd3\x1a\x04\x3f\xd5\x08\x14\x31\xc7\xae\xac\xff\xce\x7a\xb5\
\x72\xf5\xca\xf5\xa9\x74\x9d\xe7\xc4\x62\x5c\x75\xcd\x55\xe3\xa1\
\x50\xe8\x81\xfe\xee\xee\x9b\xdb\x80\x57\xc0\xcf\xc1\xba\x69\xc7\
\x4d\x85\x88\xa0\x94\x02\x50\x22\x22\x00\xba\xae\x53\x28\x0c\x7f\
\xfe\xd0\xa1\xc3\x6f\x5e\x28\x95\xac\x54\x2a\x49\xaa\x2e\x85\xe3\
\xd8\xe8\x9a\x36\x61\xe8\xc6\x66\xcb\xb2\x36\x45\xa3\xd1\x1c\x40\
\x10\x08\x20\x84\x42\x21\x3e\x01\x10\x11\x03\x98\xa5\x94\xca\x03\
\xfe\x54\xf1\xae\xee\xdc\x13\xc7\x4f\x64\x1f\x8d\xd7\xd6\xe0\x38\
\x0e\xb6\x1d\x25\x1c\x09\x61\x59\x16\x4e\xd4\x26\x12\x89\xa0\x69\
\x1a\x63\x63\x63\x72\xfe\xfc\xf9\xe7\x32\x99\xcc\xc3\x0a\x41\x69\
\xfa\x27\x00\xea\x52\x13\x93\x5d\xb8\xae\x1b\xdb\xb3\xe7\xc3\x0f\
\x2a\xd5\xea\x92\x54\x2a\x85\x15\x35\xb1\xed\x28\x91\x48\x04\xd3\
\x34\xb1\xa3\x51\x42\x46\x08\x11\xa1\x5a\xad\x32\x30\x38\x48\xae\
\xa7\x87\xf1\xd2\x44\xe1\xb3\xab\x57\xdd\x60\x59\xe6\xe9\x8f\xbb\
\x47\x00\x51\x4a\x61\x18\x06\xc5\xe2\xc8\x1d\xef\xbc\xfb\xfe\x98\
\x6e\x18\x4b\x1a\x1a\x1a\x88\xc7\xe3\xc4\x62\x0e\xa6\x65\x62\xdb\
\x36\x4e\x34\x4a\x48\x37\x10\x11\xc6\xc7\xc7\xe9\xca\x75\xd3\xd5\
\x9d\xc3\xf7\x02\x62\xb1\x58\x5d\x47\x47\xf6\x5b\x00\x06\xc0\xe0\
\xd0\xd0\xc7\x28\x12\x3e\xdd\xd3\xfb\xd6\xe0\xe0\xd9\xdb\x1b\x1a\
\x1a\xb0\xa3\x36\x11\x33\x4c\xd8\x0c\x61\x86\x23\x58\xa6\x45\x38\
\x1c\x46\xd7\x34\x7c\x11\xc6\xc6\xc6\xe8\xec\x3c\x49\xa9\x34\x8e\
\xef\xfb\x44\x22\x61\xe6\xce\x9b\xd3\x3b\x3b\x93\xd9\x32\x0d\x28\
\x9c\x1d\x9e\x34\x92\x61\x34\xe5\x07\x06\xda\x5d\xd7\x0d\xcf\x9f\
\x37\x97\x88\x15\xc1\x34\xc3\x84\xc3\x61\x22\xa6\x89\x15\x89\x10\
\x32\x42\x68\x9a\x86\xe7\xfb\x14\x86\x0b\x74\x74\x74\xe2\xba\x1e\
\x22\x42\x6d\x6d\x2d\x89\x44\xbc\x35\x12\x09\xaf\x1c\x2e\x16\x99\
\x39\x63\xc6\x24\xc0\x34\x4d\x4e\x9c\xc8\x3e\xd2\xd2\xd2\xf2\x94\
\x1f\x04\xcc\x9d\x73\x19\x46\x48\xa7\xa9\xe9\x06\x6a\x62\x35\x48\
\x10\x20\x32\xf9\xf1\x69\x4a\xc3\x75\x5d\xfa\x06\xf2\x74\x76\x74\
\x22\x02\xa6\x69\x91\x48\xc4\x19\x3b\x7f\xee\xe9\xfc\x40\xff\x23\
\xfd\xf9\x3e\x2c\xcb\xba\x04\x78\xfd\xaf\x6f\xbc\xb5\x6d\xdb\xf6\
\x2f\x2a\xa5\x28\x97\xcb\x54\xdd\x2a\x55\xd7\xa5\x54\x2a\x51\xa9\
\x54\x58\xb1\xe2\x26\x36\x6e\x7c\x9c\x6b\x97\x5c\x83\x88\xd0\x79\
\xe2\x24\xa7\x4e\x75\x4d\x17\xb6\xa2\x26\x85\x42\xe1\xbb\x9e\xe7\
\x6e\x0e\x87\xc3\x2c\x5c\xb8\x10\xcb\xb2\x98\xd2\x3a\xdb\xb7\xbf\
\xdd\xf0\xca\xcb\xaf\x7c\xd4\xd7\xd7\x3f\x73\x0a\xe2\xfb\x3e\xbe\
\xef\x13\x04\x01\x82\x50\xae\x56\x29\x4f\x4c\xf0\x8d\x6f\xae\x63\
\xcd\x9a\xbb\x26\x9f\xff\x78\x0d\x20\x14\x8b\x23\xb7\xdf\xfa\xea\
\xab\xb3\xa9\x56\x1f\x62\x64\x64\x16\x83\x83\xbb\xc9\xe5\x1e\xa5\
\x54\xea\x52\x22\xc2\x8e\x9d\xcd\xa0\x14\x2d\xbb\x5a\x7e\xd5\xbc\
\x6b\xf7\x0f\xfd\xc0\x47\xd7\x75\x82\x20\x98\x86\x04\x41\x80\x04\
\xc2\x44\x79\x82\x4c\x7d\x86\x4d\x2f\x3c\x4b\x28\x64\x54\x0b\x85\
\xc2\xad\xb7\xfc\xec\xb1\xcd\xe4\xf3\x9f\xa2\xbb\x1b\x2a\x15\x04\
\x28\x88\x30\x02\xbf\x9d\xfc\x46\xde\x6f\x9e\x54\x50\x20\x8c\x8e\
\x8e\xd2\xd5\xdd\xfd\xe5\x23\x47\x8e\xfc\x72\x70\x60\xf0\x32\xcf\
\xf3\xd0\x75\x1d\xa5\xd4\xb4\x21\xc7\xc7\x27\x58\xfb\xa5\x35\xe7\
\xef\xfc\xc2\x1d\x9f\x09\x82\xe0\xe8\xe2\xeb\xae\xdf\x56\xf6\xfd\
\xbb\xe5\xa2\xd6\x4f\x03\x87\x81\x32\x3c\x38\xd9\xc1\x8e\x5d\x53\
\x2a\xd5\x45\x84\x73\x63\x17\x7c\xdf\xf7\x29\x97\xcb\x14\x8b\x45\
\x2a\x95\x6a\x93\xae\x6b\x77\x2a\x8d\xc6\x78\x6d\x7c\x74\xc1\x82\
\xcb\xff\x18\x4f\xd4\xfe\x57\xd3\x15\x86\x6e\xe0\x2c\xbe\x8a\x3e\
\x58\x7c\x1a\x1e\x38\x0b\x0d\x25\x78\x2f\x0c\x5b\x2c\xf0\xfe\x0f\
\xa4\xa4\xa5\x79\xe8\x4b\xcf\x5e\x00\x00\x00\x00\x49\x45\x4e\x44\
\xae\x42\x60\x82\
\x00\x00\x03\x34\
\x89\
\x50\x4e\x47\x0d\x0a\x1a\x0a\x00\x00\x00\x0d\x49\x48\x44\x52\x00\
\x00\x00\x10\x00\x00\x00\x10\x08\x06\x00\x00\x01\x68\xf4\xcf\xf7\
\x00\x00\x00\x06\x62\x4b\x47\x44\x00\xff\x00\xff\x00\xff\xa0\xbd\
\xa7\x93\x00\x00\x00\x09\x70\x48\x59\x73\x00\x00\x0b\x13\x00\x00\
\x0b\x13\x01\x00\x9a\x9c\x18\x00\x00\x02\xd4\x49\x44\x41\x54\x38\
\xcb\x55\x92\x4f\x68\x5d\x65\x10\xc5\x7f\xdf\xbb\x37\xaf\x49\x48\
\xd5\x04\x23\x22\x22\x88\x85\x08\x12\x05\x0b\xa2\x0b\xc1\x8d\x90\
\x6c\x14\x04\xa1\xee\x94\x42\x15\x14\x22\xed\x56\x77\x6e\x0d\x82\
\x2b\x05\x97\xba\x15\xdd\x58\x10\x0a\x82\xab\x5a\x50\x2b\x41\x24\
\xb1\x31\x31\x79\x6d\xfe\xbc\x97\xfb\xde\xfd\xf7\xdd\xef\x7e\x33\
\xe3\xe2\x3e\x0a\xce\x76\xe6\x9c\x39\x67\xe6\xb8\x67\x77\xde\xe4\
\xa9\xfe\xe3\xb1\x57\xab\x6f\xbe\x9d\xdc\x48\x92\xb7\x0f\x3e\x5e\
\xa9\xde\x7b\x68\xe8\x66\xb7\x5e\x30\x7f\x98\xe3\x5e\xdb\xdb\x58\
\x3d\x8a\xc3\xdb\xdb\x61\x9f\x5c\x4b\x1c\x37\x57\xe1\xb8\x35\x1a\
\x85\xdf\x2b\xdc\xeb\x7b\x1b\x3c\x98\x9c\xbf\xb5\x1b\x0e\x7f\xda\
\x6a\xfe\xbe\x96\x02\x76\xa3\xbc\x49\xa1\xd5\xc5\x6c\x32\xde\x48\
\x7f\xa9\xb7\x18\xc4\x13\x10\x83\x3f\xab\x24\x1d\x1c\x0c\xa0\x56\
\x18\x04\xd8\x6b\x36\xdd\xfa\x3f\xef\xb3\x9c\x2e\xfe\x20\x26\x6b\
\xa7\x92\x91\x49\x4e\xa9\x35\x99\xe6\x8c\x64\x7c\x2e\x2d\xb5\xde\
\x3e\xf2\xc3\x0b\x07\xf1\x88\xa1\x64\xa8\x19\x00\x56\x44\x18\xc6\
\x26\xbd\xe5\xb7\xae\x57\xea\x3f\x20\x76\x0d\x0c\x28\x04\xee\x34\
\x70\x37\xe0\xf8\xf9\x19\x38\x89\x30\x8c\x39\x85\x2c\x50\x08\x8c\
\x05\xc4\xde\xe5\x91\x99\x2f\xdd\x2b\xbb\x97\x79\x2c\x5d\xe6\x9c\
\xeb\x7f\x5a\x5b\xb3\x91\x49\xfe\xdb\x71\x1c\x5d\x3a\x96\xd1\xce\
\x99\x4c\x48\x1f\x4d\x1f\xee\xcf\xb8\xb4\x19\x6b\xc1\x69\xcc\x28\
\xb4\xba\x38\xd1\x62\xbb\x52\x7f\xbd\xb1\xb0\x9e\x06\x6b\xab\x91\
\x8c\xd9\x6f\xef\x31\x94\x8c\x68\x42\x34\x21\x8f\xc5\x1a\x13\x59\
\x49\x8f\xe2\x30\x39\x8e\x23\x0e\xe2\x11\x5e\x43\xa7\x33\x2a\x8c\
\x22\x64\xf2\x75\x3a\x88\x27\x8c\xa5\xc0\x6b\xc0\xb0\xce\x85\x57\
\x38\x8b\x70\x1c\x9f\x48\xff\x6d\xef\x11\x25\x42\x04\x12\xa0\x35\
\x38\x8d\x70\x18\xa0\xd4\x6f\x12\x7d\x6b\x69\x91\x91\xbc\x48\x26\
\x1d\xed\xdd\x00\xbb\x4d\x67\xbd\xdf\x7b\x29\xa5\xd6\x0f\x19\xb6\
\xbb\x8c\xe5\x33\x4a\x85\x89\x40\x21\x05\xb3\xbd\xf3\x2c\xa7\xb8\
\x97\xef\xbc\xc3\x52\xf2\x00\x0b\xbd\x79\xfa\x6e\xe6\xaa\x73\xee\
\x93\x68\x32\xd7\x58\xc0\x6b\x83\xb7\x40\x63\x81\x5a\x1b\x2a\xf3\
\x75\xa5\xfe\xa3\x4a\xeb\xcd\xda\x1a\x82\xb5\x5d\x20\xe6\x7a\xb3\
\x5f\xf4\x70\x57\x5a\x8b\xd4\xd6\x90\x6b\x49\xa1\x35\x5e\xbb\x21\
\x41\x11\x13\x82\xb5\xf8\x29\x99\xd7\x66\x93\x68\xd7\xd2\xc6\xda\
\xcf\x83\xc4\x2b\x7e\x0a\x3c\x93\x9c\x4c\x26\xd4\xd6\xd0\x5a\xec\
\x2e\x03\x38\x1c\xd1\x04\x6b\x15\x1a\x85\x5a\xaf\x12\x2c\x71\xcf\
\xef\x5c\x6a\x22\xd2\xaf\xd5\x53\x6a\x4d\xae\x15\xb5\x79\xc4\xf4\
\x3e\xf8\x7e\x48\x1a\x85\x4a\xbb\xb0\x14\x0a\x5e\x4f\xd2\x41\x3c\
\xd9\x6f\xad\xbd\xd0\x5a\xa4\x25\x76\x92\x55\xf9\x5f\x99\x75\xe7\
\x2f\xa7\xff\x19\x0b\xe4\x02\xc1\xf6\x1d\xb7\x9f\x5b\x25\xe8\xaf\
\x44\x4b\x88\xd3\x47\x76\x9a\xbb\xd2\xe9\xe6\x52\x21\x8b\x90\x4d\
\xc1\xad\x09\x33\xee\xe9\x94\x42\xfe\xa0\xd2\x79\x6a\xfd\x0e\xaf\
\x6b\xb4\x06\x6a\x20\x40\x34\x08\xd6\x11\x14\xd2\xc9\x0f\x06\xf0\
\x3d\x73\xbd\x37\x98\xef\x49\x8a\x03\x7a\x04\xcc\xd6\x09\x06\xa5\
\x3c\x49\xa5\x97\xa9\xf4\x55\xbc\xae\xd0\x1a\xb4\xf6\x17\x6a\x3f\
\xd2\x73\x5f\x31\xeb\x76\x59\x48\x60\x29\x85\xc5\x94\xff\x00\xe1\
\x78\x1f\x4c\x73\x1c\xbc\x8b\x00\x00\x00\x00\x49\x45\x4e\x44\xae\
\x42\x60\x82\
\x00\x00\x07\x6a\
\x89\
\x50\x4e\x47\x0d\x0a\x1a\x0a\x00\x00\x00\x0d\x49\x48\x44\x52\x00\
\x00\x00\x18\x00\x00\x00\x18\x08\x06\x00\x00\x01\x97\x70\x0d\x6e\
\x00\x00\x00\x06\x62\x4b\x47\x44\x00\xff\x00\xff\x00\xff\xa0\xbd\
\xa7\x93\x00\x00\x00\x09\x70\x48\x59\x73\x00\x00\x0b\x13\x00\x00\
\x0b\x13\x01\x00\x9a\x9c\x18\x00\x00\x07\x0a\x49\x44\x41\x54\x48\
\xc7\x55\x95\x6b\x70\x5c\x65\x19\xc7\x7f\xef\x39\x67\xf7\x9c\xb3\
\x97\x64\x2f\xd9\x96\x4d\x43\x2f\x50\xc2\x08\xd2\x32\x50\x2d\x96\
\x62\x5b\x75\x10\x61\x04\x06\x54\x04\x01\xc5\xaa\x0c\x1f\x44\x40\
\x40\x1c\x9d\xd1\x51\x04\xf1\x02\x32\x38\xf5\xc2\x54\x07\x66\xb4\
\x53\x2e\x56\x40\x46\xa0\x97\x34\x09\xb1\x05\x94\xd2\x0b\xb4\x49\
\xda\x5c\x20\xc9\xe6\xb2\xd9\x26\xdb\xec\x66\xf7\xbc\xe7\x9c\xc7\
\x0f\x21\x01\x9e\x8f\xef\xcc\xfb\xfc\xde\xe7\x79\xfe\xff\xf7\x51\
\x22\x82\xef\xfb\xd4\xbc\xfa\x6a\x44\x84\xb7\x0e\x1e\x96\x6a\x6d\
\x56\x10\x11\x56\xac\x68\x95\x83\x87\x0f\x09\x5a\x6b\x3a\x3b\xbb\
\x1e\xd2\x5a\xa3\xea\xf5\x3a\x33\xd5\x8a\x1c\x7c\xeb\x30\xc6\x45\
\x6b\x2f\x11\xc7\x76\x58\xd2\xd2\xac\x78\x3f\x5b\xe3\xf8\x44\x71\
\x43\x77\x6f\x8f\x78\x9e\x27\xff\xd9\xbf\x5f\x0c\x80\xf6\x8e\xce\
\x29\x3f\xd0\x7b\xcf\x58\xbe\x82\x5d\xbb\x77\x13\xb1\xac\xf5\x06\
\x40\xdb\xee\x8e\x3f\xdd\x70\xdd\xcd\x5c\xbc\x6e\x23\xa9\x74\x4a\
\x7d\xc2\xdd\xfc\x2a\xbe\xef\xe3\xfb\x3e\x41\x10\x70\xe0\xc0\xc1\
\xa7\x7d\xdf\x47\x6b\x0d\xbe\xef\x2b\xad\x35\x7b\xda\xda\xa5\x30\
\x36\x2a\x5a\x6b\x11\x11\x0c\xa5\x94\x74\x76\x76\x4d\x2c\x5f\xb1\
\x94\xa6\x4c\x96\xce\xae\x2e\x86\x86\x46\x36\xab\x9e\xde\x5e\x12\
\x89\x84\x24\x12\x09\x44\x42\x0e\x1c\x38\x44\x53\x2e\xa3\xd4\xda\
\x4f\xae\x97\xa9\xa9\x29\x3c\xdf\x63\xcb\x96\xdf\x63\x98\x86\x71\
\xfe\xf9\xab\xc4\xb8\xff\x81\x9f\xa9\x6c\x36\x4b\xf3\xe2\x3c\x93\
\xc5\x22\x57\x2c\xf9\x41\xb8\xf8\xa5\x75\xa2\x44\x84\x20\x08\x10\
\x11\xa5\x94\x32\x80\xe0\xed\x77\x8e\x76\x55\x2a\xb3\xeb\xf2\x4b\
\x16\xd1\x7c\x5a\x33\xe5\xe9\xe9\x62\x26\x93\xc9\x85\x61\x80\xc1\
\xfb\xa1\x94\x12\xd3\x34\x83\x7f\xbd\xf8\x6f\x01\xb5\xee\xf4\xa5\
\xcd\xe4\xb2\x39\x22\x96\x05\x8a\xa6\xdd\x6d\x7b\x65\x70\xf0\xbd\
\x5b\x94\x88\x70\xe4\xed\x63\xf8\x81\x7e\xb4\x3c\x5d\xbe\xbd\xb9\
\x39\x4f\xb2\x21\x41\x2a\xd9\x88\x15\xb1\xe8\xee\xe9\x61\x78\xb8\
\x40\xbe\xf9\x34\xce\x6e\x6d\x55\x4a\x44\xb8\x68\xed\xa7\xa5\x30\
\x3a\x42\x10\x84\x3c\xf8\xe0\x2f\xb8\xe9\xa6\xeb\xd1\x5a\xd3\xb5\
\x6f\x1f\x5e\x5d\xd3\xd8\x98\x3c\x51\x3a\x59\x5a\x79\xc1\x05\x17\
\xa0\x44\x84\xc7\x1e\xfb\xc3\xf7\xfe\xfe\xb7\x6d\xbf\xd3\x5a\xa3\
\xb5\x26\x08\x43\x2a\x95\x19\x9e\xf9\xc7\x76\xea\xf5\xda\x2b\x77\
\x2d\xda\x72\x69\x8f\x37\xc8\x74\xad\x1c\x28\x11\x61\xe7\x2b\x6d\
\x78\xda\x53\x43\xc3\xc3\x0d\x6f\xbc\xf1\xc6\x3f\xdf\x7b\x6f\x68\
\x63\xe8\x07\x7c\xff\x9e\x3b\xbe\xd5\xbc\x24\xbf\x75\xf5\xa1\x6b\
\xa7\x99\xd0\x0d\x0c\x7b\x77\x2c\xcc\x6e\x7e\x66\x5a\x6b\xc6\xc7\
\xc7\xd7\xb6\xb5\x75\xec\xed\x1f\x18\xb8\x3b\x94\x70\xfe\x5c\x89\
\xc8\x07\x5d\x02\x2c\xa5\x14\x86\x61\x44\xde\x3c\x70\x68\x7f\x53\
\x2e\xbb\x21\x9e\x4c\xfc\x3a\xf0\x03\x29\x95\x4a\x57\x03\x0a\x58\
\xb8\x10\x07\x7c\xd3\x34\x79\xe9\xe5\x5d\x95\xf9\x4e\xd9\xd1\x28\
\x86\x61\x90\xcb\xe5\x76\x1c\x3f\xd1\x77\xfb\x87\x2f\x54\xe6\xda\
\xfb\xce\xc3\xe9\x74\x2a\xe2\xb8\x51\x62\xb1\x18\xae\xe3\xe2\xfb\
\x3e\xfb\x5f\x7f\x8d\xbe\xbe\x81\x47\x00\x0c\xa5\x14\x4a\x29\x66\
\x6b\xf5\x4b\x06\x07\xdf\xbd\x33\x95\x4e\x11\x8f\xc7\x49\xc6\xe3\
\x98\x86\xc1\x48\x61\x84\x6a\xa5\xc6\xa2\x45\xb9\xb9\x77\xbf\x73\
\xb4\x07\xa5\x14\xbd\xbd\x3d\x1d\x67\xb7\xb6\x12\x8f\xbb\xc4\x63\
\x71\x2c\x2b\x42\xad\x56\xa3\xa7\xf7\x38\x96\x19\xe1\xac\xd6\x33\
\xaf\x04\x30\x82\x50\x83\x04\xcf\xb6\xb6\x9e\x45\x3a\x9b\x22\x16\
\x8b\x61\x3b\x36\x4a\x29\x8e\x76\x1f\x23\x0c\x42\x12\x89\x44\xbd\
\x50\x28\xbc\x00\x60\x74\x1f\xed\xf9\xee\xb5\xd7\x5c\x77\xcd\xa6\
\x8d\x9f\xe3\xc6\xaf\xdd\x42\x32\x9e\xc4\x89\xda\x4c\x96\x26\x19\
\x1e\x2a\x90\xc9\x64\x39\x39\x35\xb9\xac\x58\x2c\x02\x60\x8c\x8d\
\x8e\x37\x64\x32\x19\x72\xb9\x1c\x03\x03\x03\x2c\x69\x59\xc1\xb6\
\x6d\xdb\x39\xd1\xd7\x47\x26\x9b\xc5\xf7\x75\x87\x52\xe6\xd8\x39\
\xe7\x7c\x6c\x4e\xa4\x3b\x77\xb7\xf1\x93\x1f\xff\x54\x82\x20\xc0\
\xf3\x3c\xb4\xf6\xf1\x74\x9d\xdb\x6e\xbb\x95\xcb\x2e\xbf\x94\x1f\
\x3a\x7f\x9c\x7d\xbd\x76\xc4\x2d\x87\x15\x66\x26\xcb\xd7\x19\x12\
\x86\xdc\x73\xef\x3d\xb1\x64\x32\x49\x32\x99\x24\x9d\x4e\x91\x49\
\x67\xf8\xcb\xd6\x27\xa8\xd5\x6a\x7f\x7e\xb5\x76\xc0\x1d\xf1\x27\
\x98\x39\x59\x86\x37\xab\x5f\x36\x08\x15\xc9\x44\xbc\xbe\xf9\xdb\
\x9b\xd5\x86\x4d\x1b\x36\x67\x73\x4d\x7e\x22\x99\xe4\xdc\xf3\xce\
\xad\x46\x22\x91\x5b\x8b\x7d\x63\xb7\xb2\x7f\x06\x5e\x98\xaa\x32\
\xa1\xaf\x5f\x70\xdc\x7c\x88\x08\x4a\x29\x00\x25\x22\x02\x60\x9a\
\x26\xc5\xe2\xe4\x17\x0e\x1d\x3a\xfc\xec\x4c\xa5\xe2\x66\xb3\x19\
\xb2\x4d\x59\x12\x89\x38\xa6\x61\xcc\x5a\xa6\xf5\xb8\xeb\xba\x8f\
\xc4\x62\xb1\x01\x80\x30\x14\x40\x88\x44\x22\x7c\x04\x20\x22\x16\
\x70\x9a\x52\xaa\x00\x04\xf3\xc9\xfb\xfa\x07\xee\x3f\x7a\xac\xe7\
\x47\xa9\xc6\x06\x12\x89\x04\xf1\x78\x8c\xa8\x1d\xc1\x75\x5d\x12\
\xb1\x38\xb6\x6d\x63\x18\x06\xe5\x72\x59\x4e\x9d\x3a\xf5\x70\x3e\
\x9f\xbf\x5b\x21\x28\xc3\xfc\x08\x40\x7d\x50\xc4\x5c\x15\x5a\xeb\
\xe4\xbe\x7d\xaf\xbd\x5a\xf7\xbc\x55\xd9\x6c\x16\x37\xe6\x10\x8f\
\xc7\xb0\x6d\x1b\xc7\x71\x88\xc7\x62\x44\xac\x08\x22\x82\xe7\x79\
\x8c\x8e\x8d\x31\x30\x38\x48\xb5\x32\x5b\xfc\xcc\xa6\x8d\x17\xba\
\xae\xf3\xee\x87\xdd\x23\x80\x28\xa5\xb0\x2c\x8b\x52\xe9\xe4\x65\
\x2f\xbd\xbc\xb3\x6c\x5a\xd6\xaa\x96\x96\x16\x52\xa9\x14\xc9\x64\
\x02\xc7\x75\x88\xc7\xe3\x24\x62\x31\x22\xa6\x85\x88\x50\xad\x56\
\xe9\x1b\xe8\xa7\xaf\x7f\x80\xc0\x0f\x49\x26\x93\x4d\xdd\xdd\x3d\
\xdf\x04\xb0\x00\xc6\xc6\xc7\x3f\x44\x91\xe8\xbb\x83\x43\xcf\x8f\
\x8d\x4d\x7c\xbe\xa5\xa5\x85\x78\x2c\x8e\xed\x44\x89\x3a\x11\x9c\
\xa8\x8d\xeb\xb8\x44\xa3\x51\x4c\xc3\x20\x10\xa1\x5c\x2e\xd3\xdb\
\x7b\x9c\x4a\xa5\x4a\x10\x04\xd8\x76\x94\x65\xcb\x97\x0e\x2d\xc9\
\xe7\xb7\x2e\x00\x8a\x13\x93\x73\x46\xb2\xac\x35\x85\xd1\xd1\x2e\
\xad\x75\x74\xc5\xf2\x65\xd8\xae\x8d\xe3\x44\x89\x46\xa3\xd8\x8e\
\x83\x6b\xdb\x44\xac\x08\x86\x61\xe0\x07\x01\xc5\xc9\x22\xdd\xdd\
\xbd\x68\xed\x23\x22\x34\x36\x36\x92\x4e\xa7\x3a\x6c\x3b\xba\x61\
\xb2\x54\x62\xf1\xa2\x45\x73\x00\xc7\x71\x38\x76\xac\xe7\xbe\xf6\
\xf6\xf6\x07\x83\x30\x64\xd9\xd2\xd3\xb1\x22\x26\x6b\xd6\x5c\x48\
\x43\xb2\x01\x09\x43\x44\xe6\x16\x9f\xa1\x0c\xb4\xd6\x0c\x8f\x16\
\xe8\xed\xee\x45\x04\x1c\xc7\x25\x9d\x4e\x51\x3e\x35\xfd\x50\x61\
\x74\xe4\xbe\x91\xc2\x30\xae\xeb\x7e\x00\x78\xfa\xa9\x67\x9e\xdf\
\xb1\xe3\xb9\x2f\x2a\xa5\xa8\xd5\x6a\x78\xda\xc3\xd3\x9a\x4a\xa5\
\x42\xbd\x5e\x67\xfd\xfa\x8b\x79\xe0\x81\x9f\xb3\x7a\xd5\x79\x88\
\x08\xbd\xc7\x8e\x73\xe2\x44\xdf\x42\x62\x37\xe6\x50\x2c\x16\xbf\
\xe3\xfb\xfa\xf1\x68\x34\xca\xca\x95\x2b\x71\x5d\x97\x79\xad\xf3\
\xdc\x73\x2f\xb6\x3c\xf9\xc4\x93\xff\x1d\x1e\x1e\x59\x3c\x0f\x09\
\x82\x80\x20\x08\x08\xc3\x10\x41\xa8\x79\x1e\xb5\xd9\x59\xbe\xfe\
\x8d\x1b\xb9\xea\xaa\x2b\xe7\xbe\xff\x54\x03\x20\xec\xb0\x3b\x7e\
\x39\x90\x1c\xdf\x3c\x19\x4c\xe7\x4e\xfa\x65\xa6\xc2\xf2\x54\xc1\
\x2f\xde\x3b\x1b\xd4\xb6\x2a\x11\x61\xd7\xee\x36\x50\x8a\xf6\x3d\
\xed\xbf\x6d\xdb\xb3\xf7\xae\x20\x0c\x30\x4d\x93\x30\x0c\x17\x20\
\x61\x18\x22\xa1\x30\x5b\x9b\x25\xdf\x9c\xe7\x91\x47\x7f\x43\x24\
\x62\x79\xc5\x62\xf1\xb3\x77\xe6\xb7\x74\x0e\xea\x11\x26\x83\xe9\
\x39\xb1\xeb\x10\x26\x7c\x98\x0e\xb6\xcf\xad\x91\x9d\x6d\x73\x0a\
\x0a\x85\xa9\xa9\x29\xfa\xfa\xfb\xbf\x7a\xe4\xc8\x91\x5f\x8d\x8d\
\x8e\x9d\xee\xfb\x3e\xa6\x69\xa2\x94\x5a\x30\x64\xb5\x3a\xcb\x35\
\x5f\xba\xea\xd4\xe5\x57\x5c\xf6\xa9\x30\x0c\xdf\x5e\x5d\xbb\xa1\
\x8e\x27\x51\x94\x02\x2d\x30\x54\x87\xfe\x3a\x04\xdc\x3c\x57\xc1\
\xae\x3d\xf3\x2a\x35\x45\x84\xe9\xf2\x4c\x10\x04\x01\xb5\x5a\x8d\
\x52\xa9\x44\xbd\xee\xad\x31\x4d\xe3\x72\x65\xd0\x9a\x6a\x4c\x4d\
\x9d\x79\xe6\x19\x7f\x4d\xa5\x1b\xff\x67\x98\x0a\xcb\xb4\xf8\x78\
\xdf\xb5\x30\xe2\x5d\xcd\x84\xfe\x0a\xe5\xc0\xa4\x2e\xcf\x12\x55\
\x4f\x61\x1b\xfc\x1f\x0b\x03\xc8\x05\x59\x65\x3b\x42\x00\x00\x00\
\x00\x49\x45\x4e\x44\xae\x42\x60\x82\
\x00\x00\x00\xc5\
\x89\
\x50\x4e\x47\x0d\x0a\x1a\x0a\x00\x00\x00\x0d\x49\x48\x44\x52\x00\
\x00\x00\x90\x00\x00\x00\x90\x08\x06\x00\x00\x00\xe7\x46\xe2\xb8\
\x00\x00\x00\x04\x73\x42\x49\x54\x08\x08\x08\x08\x7c\x08\x64\x88\
\x00\x00\x00\x09\x70\x48\x59\x73\x00\x00\x0e\xc4\x00\x00\x0e\xc4\
\x01\x95\x2b\x0e\x1b\x00\x00\x00\x67\x49\x44\x41\x54\x78\x9c\xed\
\xc1\x31\x01\x00\x00\x00\xc2\xa0\xf5\x4f\xed\x69\x09\xa0\x00\x00\
\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\
\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\
\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\
\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\
\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\xe0\x06\
\x44\x9f\x00\x01\xc3\xcd\x96\xea\x00\x00\x00\x00\x49\x45\x4e\x44\
\xae\x42\x60\x82\
\x00\x00\x02\x7a\
\x89\
\x50\x4e\x47\x0d\x0a\x1a\x0a\x00\x00\x00\x0d\x49\x48\x44\x52\x00\
\x00\x00\x10\x00\x00\x00\x10\x08\x06\x00\x00\x00\x1f\xf3\xff\x61\
\x00\x00\x00\x06\x62\x4b\x47\x44\x00\xff\x00\xff\x00\xff\xa0\xbd\
\xa7\x93\x00\x00\x00\x09\x70\x48\x59\x73\x00\x00\x0b\x13\x00\x00\
\x0b\x13\x01\x00\x9a\x9c\x18\x00\x00\x00\x07\x74\x49\x4d\x45\x07\
\xdd\x06\x0d\x08\x1d\x33\x51\xf1\xd4\x9e\x00\x00\x02\x07\x49\x44\
\x41\x54\x38\xcb\x65\x91\x3d\x6b\x14\x41\x18\xc7\x7f\x73\xb7\x2c\
\x6c\x0c\xb9\x20\xa6\x0d\x58\x45\x90\x88\x1f\x40\xb1\x12\x2e\x8d\
\x82\x5f\x41\x08\x58\x05\xb4\xb5\x0c\xd8\x09\xa2\x20\x08\x7e\x88\
\x58\x05\xac\x04\xfb\x08\x56\x42\x40\x48\x9d\xdc\xe5\xf6\x66\xe7\
\x75\x67\xc7\xe2\x19\x72\x07\x0e\xfc\x18\x06\xe6\xff\x32\xcf\xa8\
\x9c\x1f\x00\xb7\x81\x09\x70\x0b\xa8\xf7\x40\x1d\x42\x7a\x02\xe1\
\x21\x78\xc0\xfe\x82\xee\x07\x74\x9f\x41\x9f\x83\x41\xf0\xa8\x9c\
\x1f\x17\x83\x4d\xa0\x7e\x0d\xea\x18\xfa\x46\x84\xae\xe0\x01\x0b\
\x18\x0b\xe6\x2d\x98\xf7\x72\x0e\xa8\x9c\x0f\x80\x49\x0d\xf5\x09\
\xa8\x29\xf4\xe5\x72\x57\x76\x0f\x44\x20\xac\x19\x9a\x53\x70\xcf\
\x21\x84\x11\xd4\x00\x1f\xa1\x9f\x4a\xad\x05\x70\x05\x5c\x96\x7d\
\x06\x5c\x03\xcb\x62\xda\x01\x66\x9a\xb3\x79\x17\x42\x8f\xca\xf9\
\xd9\x3e\x54\x67\x90\xc6\x92\xb8\x28\xe8\x92\x9e\x80\x5c\x48\x80\
\x23\xa5\x88\x31\xa4\x10\xb8\x5f\x41\x38\x84\x38\x96\x6a\x4b\x60\
\x5e\x12\x6d\xa9\x9e\x91\xa5\x80\x9e\x10\x32\xd6\x82\x31\x8c\xbd\
\xe7\x55\x05\x66\x2a\xce\xb6\x18\x2c\xcb\x84\x03\x30\xb0\xbe\x62\
\x14\x71\xd7\x09\xd6\xf2\xa8\x02\xbd\xfb\xff\xe0\x62\x11\xe7\x1b\
\x71\xce\x10\x23\x78\x0f\xc6\xc0\x72\x09\xc6\xb0\x5b\x49\x62\xcf\
\xea\xdb\xe2\xda\xbb\x57\xe2\x94\xa0\xef\xb9\x69\x50\x0c\x18\xc1\
\xf2\x02\xda\x32\x34\x49\xcf\x39\x93\x33\x37\x0c\x83\xa4\x5b\x0b\
\x5a\x43\xdb\x0a\x5d\xc7\xc5\x08\xda\x53\x99\x7a\x4b\x4a\x96\x18\
\x13\x21\x48\x5a\x4a\xab\xda\x5a\xc3\xf5\x35\xcc\x66\x42\xdb\x82\
\xb5\xfc\x54\x29\xb1\xef\x1c\x67\x31\x32\xee\x7b\x49\x04\x50\x4a\
\xf6\x94\xc0\x39\xa9\x7c\x79\x09\x57\x57\xb0\x58\x40\x08\xa4\xba\
\xe6\x5e\x65\x0c\xbf\xad\xe5\x93\x73\x1c\xc5\x28\xc9\xc3\xb0\x12\
\xf7\xbd\xbc\xb5\x6d\x61\x3e\x17\xb1\xf7\x30\x1a\xf1\xa1\x69\x38\
\x57\xb3\x19\x68\x4d\xdd\x75\x9c\x58\xcb\x34\x04\x11\xae\xd7\xb7\
\x56\x0c\xb4\x96\x33\xf0\x6d\x63\x83\x17\x77\xee\x90\xaa\x61\x80\
\x61\x20\xc4\xc8\x81\x73\x1c\x19\xc3\xb1\x73\x6c\x7a\x0f\x21\x48\
\x7d\x6b\x85\x18\xd1\x4a\xf1\xa6\x69\xf8\xb2\xb5\x05\xdb\xdb\xa0\
\xe6\x73\xf9\x96\xb6\x95\x7a\x6d\xcb\x5d\xad\x79\xa9\x35\x4f\xad\
\x65\xcf\x7b\x88\x91\x3f\x29\xf1\x7d\x3c\xe6\x6b\xd3\xf0\x77\x32\
\x81\x9d\x1d\xe1\x1f\x3c\x20\x6c\x94\x65\x65\x77\x27\x00\x00\x00\
\x00\x49\x45\x4e\x44\xae\x42\x60\x82\
\x00\x00\x06\xc9\
\x89\
\x50\x4e\x47\x0d\x0a\x1a\x0a\x00\x00\x00\x0d\x49\x48\x44\x52\x00\
\x00\x00\x90\x00\x00\x00\x90\x08\x02\x00\x00\x00\x68\x24\x75\xef\
\x00\x00\x00\x03\x73\x42\x49\x54\x08\x08\x08\xdb\xe1\x4f\xe0\x00\
\x00\x00\x09\x70\x48\x59\x73\x00\x00\x0e\xc4\x00\x00\x0e\xc4\x01\
\x95\x2b\x0e\x1b\x00\x00\x06\x6c\x49\x44\x41\x54\x78\x9c\xed\x9d\
\x3b\x7a\xd3\x40\x14\x46\xc7\x7c\x2e\x48\x9f\x02\x0a\x16\x91\x2d\
\x50\xb2\x04\x52\x7a\x5b\xa4\xcc\x16\x52\x66\x09\x64\x11\x14\x2e\
\x48\xef\x52\x14\x0a\xf2\x58\x96\x34\x8f\xfb\xfa\xe7\x7a\x4e\x05\
\xc4\x1e\x8b\x39\x3e\x1e\x7b\x90\xc5\xee\xd7\xdf\x2f\x21\x84\xc3\
\xfd\x31\x60\xf0\x78\xf7\x66\x7d\x08\x73\x9e\x4f\x0f\xd6\x87\xf0\
\xc1\xd3\xfb\xd7\xfd\xf4\xab\x80\xa1\x6d\x9c\x1d\x40\x6d\xb6\x8c\
\x82\x42\x08\xbb\x61\x18\xa6\xdf\x8c\x20\x68\x1b\x01\xd1\x66\x5b\
\xd8\xcc\xce\x7e\xed\x16\x08\xda\x6e\xbc\xb6\x99\xaa\x10\xc2\xe1\
\xfe\xb8\x1b\x86\x61\xf1\x67\xd3\x2d\xc4\x8f\x2b\x0f\x43\x6d\xfa\
\x85\x6d\xe8\x58\x28\xec\xfa\x9e\x08\xda\x6e\xa4\xb6\x35\x55\xe1\
\xbf\x85\x8f\xc2\xb6\x6f\x1a\xdf\x01\x01\x65\x6d\x3a\x85\x65\xce\
\x7f\xa2\xb0\xeb\x11\x11\xb4\x39\xab\x2d\xa9\x2a\x44\xd3\x7e\x2e\
\x2c\xf3\x9e\xb3\xfb\x9b\xa3\xa0\x4d\xae\xb0\x8a\x09\x2f\x28\xec\
\xfa\x91\x10\xb4\x35\x5a\x5b\xbe\xaa\x70\x39\xcf\x17\x85\x95\x0e\
\x74\x3d\x9c\x2d\x42\xda\x78\x0b\x23\xce\x70\x65\x61\xd7\x47\x80\
\xa0\x0d\xbc\xb6\x0a\x55\xe1\x6a\x62\x3f\x6d\xff\xb8\xe8\x68\xea\
\x0e\x88\x1d\x9c\xad\xbf\x09\xc6\xc9\x61\x28\x2c\xc6\xbc\xb6\x38\
\xaf\xe7\xd3\x83\x79\x6d\x44\x4f\xd7\x33\xb9\x20\xec\x70\x7f\x24\
\x3e\x8c\x89\xb6\x45\x37\x86\x2f\x92\x42\xaf\x37\xcc\x85\xc5\xa8\
\x69\x4b\xfa\x50\xd6\xc6\xa5\x6a\x71\xea\x96\x85\xd1\x23\x9b\x10\
\xd5\x56\xe4\x40\x41\x9b\xc2\x2a\x2e\x58\x58\x0c\xbb\xb6\xea\x79\
\x17\xd2\xc6\xae\x6a\x6d\xae\x56\x85\x31\x46\x36\xc1\xa2\x8d\x65\
\xae\x19\xb5\x29\xbf\x37\x56\x2a\x2c\xa6\x5a\x1b\x7b\x16\x44\x6d\
\x72\xaa\x36\x26\x67\x4b\x98\x44\x64\x13\x45\xda\x44\x17\x9e\x0a\
\x6d\x86\x9f\x38\x0d\x0a\x8b\x49\x6a\x53\x7b\x6b\x97\xa9\x4d\x41\
\xd5\xf6\x93\x38\x21\x4c\x34\xb2\x89\x45\x6d\x26\x1f\x9e\x36\xb4\
\x81\xec\xe3\x18\x17\x16\x33\x69\x33\xdf\x9e\x98\x69\xd3\x54\x95\
\x5c\x23\xe6\x7b\x89\x15\x43\xf0\x02\xf2\x44\x0e\xff\xb5\x7d\xff\
\xf3\xc3\xfa\x40\x2e\x48\x0b\xd3\x07\x61\xf7\xf6\xf1\xee\x4d\x3f\
\xf4\x9c\x36\xb2\x5e\x12\x75\x56\xb2\x18\xc3\x3d\x40\xf3\x17\xe4\
\x6d\x80\xd6\xb0\x6b\x94\xb5\xd9\xaa\xca\x5c\x7a\x72\x85\xe9\x47\
\x36\xa1\xa0\x0d\xbc\xaa\x18\xe8\xc2\x62\x84\xb4\x81\xa8\xca\x7f\
\x67\x57\x20\xcc\x30\xb2\x09\x46\x6d\x20\xaa\x4a\x69\xa6\xb0\x18\
\xa2\x36\x34\x55\x45\x1f\x9c\xca\x84\x21\x44\x36\x51\xa1\x0d\x4d\
\x55\x05\x4d\x16\x16\x93\xa9\x0d\x56\x55\xe9\xbe\x44\xb1\x30\xa8\
\xc8\x26\x36\xb4\xc1\xaa\xaa\xa3\xf9\xc2\x62\x66\xda\xf0\x55\x55\
\x6c\xfb\xd5\x6c\x4d\x21\x9c\x33\xba\x01\xc2\xce\x96\x1c\xae\x0a\
\x0b\x2d\x54\x35\x51\xf7\xbc\xaf\x14\x06\xb8\x92\x35\xa4\x8a\x82\
\x87\xc2\x5a\x54\x55\xbd\xac\xd4\x0b\x43\x88\xac\x45\x55\x44\x5a\
\x2d\xac\x69\x55\x94\x77\x6d\x24\x61\x26\x91\x35\xad\x8a\x4e\x4b\
\x85\xf9\x50\x45\xfc\x50\x44\x15\xa6\x13\x99\x0f\x55\x2c\xa0\x17\
\xe6\x4c\x15\x7d\xcf\x81\x41\x98\x50\x64\xce\x54\x71\x81\x58\x98\
\x57\x55\x2c\x5b\x7a\x7b\xa6\xd9\x79\x41\x3b\x7f\x0f\x8d\xd7\x6f\
\x2f\x87\x13\xc3\x38\xbb\x9f\x9f\x7f\x33\x0c\xe3\x1a\xfa\x6e\xf2\
\x58\x05\xcb\x38\x6c\x27\x92\x3a\xde\x23\xe7\x7a\x89\x66\x19\x87\
\x47\x98\x63\x5b\x74\x78\x7d\x73\x9e\xaa\xed\x58\x1b\x4e\x64\x0c\
\xc2\x1c\x7b\xa2\xc3\x6e\x9a\xf9\xcb\x10\x8e\xe5\x81\x44\x46\x15\
\xe6\xd8\x10\x1d\x09\xc7\xfc\x5f\x37\x72\xac\x10\x21\x32\x92\x30\
\xc7\x6e\xe8\x08\xd9\x15\xf9\x42\x9f\x63\x91\xe6\x91\xd5\x0b\x73\
\x6c\x85\x8e\x9c\x57\xa9\xaf\xcc\x3a\xd6\x69\x1b\x59\xa5\x30\xc7\
\x3e\xe8\x88\x1a\x15\xfc\x52\xba\x63\xa9\x86\x91\xd5\x08\x73\x6c\
\x82\x8e\xb4\x4b\xd9\xcb\x3e\x38\x56\x6b\x15\x59\xb1\x30\xc7\x0e\
\xe8\x28\x58\x14\xbf\xb0\x8a\x63\xc1\x26\x91\x95\x09\x73\x3c\xfb\
\x74\x74\xfc\x69\x5c\xba\xc8\xb1\x66\xfd\xc8\x0a\x84\x39\x9e\x77\
\x3a\x6a\xe6\x94\x2e\x0e\xe6\x58\xb6\x72\x64\xb9\x67\x4d\x71\x9d\
\x39\xd4\x21\xd2\x4f\x73\x6b\x0c\xc4\x33\x7f\x5b\x44\xed\x15\x28\
\x6b\x0d\xe3\x5a\x81\xfa\x4a\x46\x27\x2d\xac\xdb\x52\x80\xff\x6d\
\x7d\xd7\x96\x44\x27\xb2\x84\xb0\xee\x49\x01\xa9\xad\xa9\x2e\x2f\
\x89\x42\x64\x5b\xc2\xba\x21\x05\x64\xff\x79\xa5\x2b\x4c\x22\x1d\
\xd9\xaa\xb0\xee\x46\x01\x8d\x53\x04\xba\xc8\x24\xa2\x91\x2d\x0b\
\xeb\x56\x14\xd0\x3b\xcd\xad\xeb\x4c\x22\x17\xd9\x82\xb0\xee\x43\
\x01\xed\x53\xb5\xbb\xd4\x24\x42\x91\xcd\x85\x75\x13\x0a\xd8\x7c\
\xdd\xa8\xab\x4d\x22\x11\xd9\x85\xb0\xee\x40\x01\xcb\xaf\xcc\x76\
\xc1\x49\xd8\x23\x3b\x0b\xeb\xb3\xaf\x80\xfd\x65\x1f\xba\xe6\x24\
\xbc\x91\x7d\x08\xeb\xf3\xae\x00\xca\xa5\x8b\xba\xec\x24\x8c\x91\
\x7d\x0a\x7d\xc6\x55\xe0\x72\xb6\xfb\xf9\xf9\x37\xcb\x44\x33\x5e\
\x94\xf4\xf5\xdb\x0b\xd7\x50\x74\x18\xaf\x03\xc9\xf2\xf7\xda\xa3\
\xd9\x82\xe2\xf9\xf4\xf0\xf4\xce\x39\x1a\x7d\x90\x7e\x22\xe9\x32\
\x12\x2f\xef\x4f\xef\x5f\x21\x2e\xd2\xec\x2c\x2f\xf0\x95\xb8\x17\
\x76\x46\x41\x15\x3d\x32\xaa\x30\x1f\x79\x81\x57\x15\x73\xeb\x85\
\xe9\xab\x22\x46\x46\x12\xd6\x74\x5e\x0d\x55\x15\x73\x8b\x85\x99\
\xab\xa2\x44\x56\x2f\xac\xc5\xbc\xcc\x55\xd1\xb9\x95\xc2\xd0\x54\
\x55\x47\x56\x29\xac\xa1\xbc\xd0\x54\x11\x51\xba\x8a\x80\x15\xc8\
\xb6\xea\x9e\xf4\x35\xc2\xf0\xf3\x9a\x3c\x3d\xde\xbd\x39\xbb\x7a\
\x81\xb7\x35\x6c\x31\x29\xae\xff\xab\x86\x9d\x8a\x95\xac\x58\x18\
\x6c\x5e\x49\x1f\xb0\xda\x8a\xf0\x50\x58\x91\x03\x34\x6d\xa5\x91\
\x95\x09\x43\xcb\xab\x7a\xde\xd1\xb4\xe5\xd3\x6a\x61\x2c\x73\x0d\
\xa2\xad\x28\xb2\x02\x61\x20\x79\xb1\xcf\x2f\x88\xb6\x4c\x5a\x2a\
\x4c\x74\x4e\x6d\xb5\xe5\x47\x96\x2b\xcc\x36\x2f\xb5\x79\xc4\xaf\
\x0d\xbd\x30\x93\xb9\x33\xd1\x96\x19\x59\x96\x30\x93\xbc\xcc\x9f\
\xe6\xa3\xb6\xef\x7f\x6c\x8f\x62\x0e\xdc\x5e\xe2\x78\xf2\x9e\xb9\
\x2d\x13\x72\xc2\x48\x17\xa6\x99\xd7\xe1\xfe\xf8\x1a\xde\x02\xcc\
\x5a\xf2\x7c\x7a\x08\xe1\x18\xac\x97\xf0\x18\x94\x35\x6c\xf1\xe5\
\xdb\x50\xdb\xec\x41\xc7\xc3\x53\xd0\x96\x5c\xc9\x12\xc2\x14\x0e\
\x31\xb9\xd2\x2a\x6b\xdb\x78\x20\x35\x6d\x1b\x58\x16\x56\xb4\x87\
\xa6\xa0\x2d\x73\x70\x69\x6d\xdb\x91\x6d\x09\x93\x3b\xa6\xea\x53\
\x50\x84\xb4\x55\x0c\x68\x55\x9b\x76\x61\xf4\x93\xcb\x03\xab\x36\
\xe2\x20\x42\xda\x36\x22\x5b\x15\xc6\x7e\x10\x2c\xaa\x62\x88\xda\
\x18\x33\xd5\xac\x4d\xa3\x30\x76\x55\x31\x15\xda\x84\x16\x42\x5e\
\x6d\x6b\x91\x2d\x0b\xe3\x7a\x54\x51\x55\x31\x99\xda\x14\xde\x6a\
\x4a\xd7\x26\x55\x98\x9a\xaa\x98\x0d\x6d\xca\x1f\xe6\x58\xb4\x2d\
\x46\xb6\x20\x8c\xf8\x30\x26\xaa\x62\x66\xa7\x49\x19\x6e\x97\x48\
\xd4\xc6\xb9\x97\x78\xb8\x3f\x9a\xdb\x9a\x61\xbe\xb9\x15\x68\xd3\
\x72\x2d\x7b\x5e\x58\xdd\xd3\x01\xcd\xd3\x04\xc8\x9e\x64\xe0\xab\
\x6d\x37\x0c\x43\xfc\xfb\xd2\x11\x85\xde\xac\x4b\x80\xa0\x6d\x84\
\x32\xc9\x17\x85\x15\x0d\x04\x5b\xd5\x1a\x3e\x6a\xbb\x28\x2c\x73\
\x08\x85\xcf\x55\xd2\x20\x68\x1b\x29\x9d\xf3\x73\x61\x39\xf7\x6c\
\xae\xaa\x35\xda\xad\xed\x5c\xd8\xf6\x7d\x94\x3f\x02\x6b\x82\xa0\
\x6d\x24\x47\xc1\x3e\x79\x53\x37\x55\xad\xd1\x56\x6d\x1f\x85\x2d\
\xde\xc8\x70\xb7\xc2\x0a\x04\x6d\x23\x6b\x46\xf6\x8b\x3f\x73\x5f\
\xd5\x1a\xf8\xb5\xed\x86\x61\x88\xff\xd4\x5c\x15\xce\xf7\xef\x10\
\xb4\x8d\xc4\x82\x76\xbf\xfe\x7e\x19\x7f\x65\xae\x6a\x04\x47\xd8\
\x08\x9a\xb6\x7f\x3b\xcf\xca\x48\x61\xee\x5b\x97\x00\x00\x00\x00\
\x49\x45\x4e\x44\xae\x42\x60\x82\
\x00\x00\x03\xef\
\x89\
\x50\x4e\x47\x0d\x0a\x1a\x0a\x00\x00\x00\x0d\x49\x48\x44\x52\x00\
\x00\x00\x10\x00\x00\x00\x10\x08\x06\x00\x00\x01\x68\xf4\xcf\xf7\
\x00\x00\x00\x06\x62\x4b\x47\x44\x00\xff\x00\xff\x00\xff\xa0\xbd\
\xa7\x93\x00\x00\x00\x09\x70\x48\x59\x73\x00\x00\x0b\x13\x00\x00\
\x0b\x13\x01\x00\x9a\x9c\x18\x00\x00\x03\x8f\x49\x44\x41\x54\x38\
\xcb\x3d\x91\xdf\x4f\x5b\x75\x00\xc5\xcf\xf7\x7e\x2f\xb4\xbd\xb7\
\xdc\x76\x8c\xfe\x80\x5b\xe4\x87\x73\xcc\x84\x8c\x9f\x0d\x83\x25\
\x2e\x6e\x3e\x8c\x44\xb3\x64\x66\x21\x6a\x62\x8c\xba\x68\xa6\x0f\
\xea\x93\x0f\x26\x8b\x0f\xc6\x7f\xc0\x44\x97\xc5\x2c\x53\x5f\xdc\
\xe2\xa3\xc8\xa0\xb0\x1f\x22\x14\xc1\x6d\x08\x6d\x2d\x90\x51\xda\
\x4b\x27\x3f\xd6\x52\xee\xbd\x50\x7a\xbf\xbd\x5f\x1f\x10\x5e\x4f\
\xce\x39\xf9\xe4\x1c\xca\x18\x43\x4f\x4f\xdf\x23\xc4\xe2\x09\x30\
\xc6\x38\xb1\x2c\x0b\x00\x20\xe6\xb6\xf2\x7c\xf9\xc9\x0a\x08\x63\
\x0c\xdb\xdb\x7a\x6f\xb1\x54\x9c\x30\x0c\x03\x88\x8c\xde\x43\xb8\
\xbb\x8f\xf7\xf6\xbe\xc4\x1f\x8c\xff\x0e\x58\x96\x85\x72\xb9\x8c\
\x8c\xa6\xfd\x64\x59\x16\xc0\x18\xc3\xf4\xcc\x43\x5e\x2e\x97\xf9\
\x48\x64\xcc\xa4\xe1\x70\x8f\xd6\x15\xee\x54\xa2\xd1\x28\x8e\x54\
\x7b\x2b\x71\xee\xec\x79\xb3\xed\x64\x37\x9f\x8b\xcd\x9b\x1b\xcf\
\x36\xf7\x23\x96\x65\x29\x8c\x31\xcc\xfc\xf5\x68\x28\x91\x4c\xf2\
\x7c\x61\x8b\xdb\xb6\xcd\x4d\xd3\xac\x21\xa9\x95\x34\x04\x41\x40\
\x3c\x9e\xe4\x27\x4e\x1c\x43\xd0\x1f\x00\x07\xc7\xfd\x07\xe3\xe8\
\xec\x6c\xbf\x86\xef\xbe\xbd\xfe\x59\x7b\x5b\x98\x07\x82\xf5\xfc\
\xe2\xeb\x03\x5c\xd7\x75\x3e\x7a\xf7\x1e\x1f\x1e\x89\xb4\x65\xff\
\x7d\x0a\x32\x3c\x3c\x06\x70\xe0\xe7\x5b\xb7\x22\xa9\xe5\xd4\x39\
\xc3\x30\x71\xe3\x87\x6b\xde\x50\x5d\xa8\x20\xcb\xf2\x3e\xc3\xff\
\x1c\xd0\xb4\xec\xab\xd3\x33\x0f\xe7\x0d\xd3\xec\x38\xd0\x0e\x0c\
\x4e\x9b\x73\x8c\xdd\xbd\xcf\x57\x32\x69\x5e\x2e\x97\xb9\xb6\xaa\
\x4d\x70\xce\x21\x02\x00\xa5\xb4\xf8\xeb\xe0\x90\xd5\xd2\xf2\x02\
\x8e\x56\x1f\x85\x6d\x73\xc4\x13\xc9\xde\xbd\xa2\x75\x41\xd4\x56\
\xb3\x58\x5b\x5f\xbf\xd1\xdc\xd4\x24\x2a\x1e\x05\x2e\xa7\x13\x8f\
\x67\x67\xe1\x74\x38\xd0\xd4\xd4\x10\x11\x76\x4c\xb3\xc6\xd0\xf5\
\x77\x1a\x9b\x1b\xa0\x54\x29\xd0\x75\x1d\x6b\x6b\x1b\xa8\xac\xac\
\x7c\xf3\xf1\xdf\xb3\x26\xe9\xeb\x3d\xc3\xd7\x37\x36\x90\xcb\xe7\
\x30\x15\x1d\xc7\xc2\xe2\x22\x82\xc1\x20\x37\x4c\x5d\x68\x6d\x6d\
\x85\xf0\xd1\xc7\x57\xfa\x8e\x78\xbd\x68\xa8\x7f\x0e\xfd\xe7\x5f\
\x83\xa2\x28\x30\x77\x8c\xe7\x5d\x2e\x17\x00\x40\xf0\xf9\x7c\x93\
\xef\xbd\xff\xee\x8b\xb5\x75\xb5\x7b\xaa\xaa\x22\x12\x19\x4b\x29\
\x8a\xb2\x1c\xee\xea\x86\x57\xf1\xec\x3f\x0e\x00\x9c\x73\x00\xa0\
\x84\x10\x4e\x08\xb1\x4b\xa5\x52\xf3\x64\xf4\xcf\x39\x87\xc3\x21\
\xf9\x03\x35\xf0\x7a\xbd\x90\x5d\x92\xb5\xbb\xbb\x7b\xdd\xed\x96\
\x3f\xa1\x54\xb4\x38\xb7\x0f\x0b\x08\x00\x0a\x80\x51\x4a\xb1\xb0\
\xb0\xf8\xf9\x93\xe5\xd4\xd7\x75\x75\xb5\x50\x3c\x55\x90\xdd\x32\
\x14\xb7\x82\x4a\xb1\x02\x7b\xa5\x22\xe6\x62\x71\x80\xe3\xc7\x8e\
\xf6\x93\x57\x0e\x09\x00\x80\x31\xe6\x9f\x98\x8c\xfe\x51\x51\xe1\
\x38\xe6\xf3\xd7\x40\x92\x9c\xa8\xaa\xaa\x82\xec\x92\x40\x29\x45\
\x2e\x9f\x43\x2c\xfe\x0f\xac\x92\x05\x8f\xc7\xb3\x13\x0c\x04\xde\
\x12\xe7\x63\x09\x08\x44\x00\x21\xe4\xed\x8c\x96\xb9\x19\x0a\x85\
\x20\x49\x4e\xb8\x24\x17\xdc\x6e\x37\x24\xa7\x0b\x84\x10\xa4\xd3\
\x69\x24\x17\x96\x40\x29\x85\x3f\xe0\x5b\x57\xd5\xba\x16\x4a\xe9\
\x96\x98\xcf\xe5\x4e\xdd\xbe\xfd\xcb\x37\x53\x53\xd3\x5d\x82\x40\
\x50\xab\xd6\xe2\x8d\x81\x01\x5c\xba\x74\x11\x94\x52\x94\x4a\x25\
\xc4\x12\x09\x68\x99\x55\x54\x57\x57\x83\x08\x18\x5a\x5d\xd5\xfa\
\x4d\xd3\x40\x30\x18\x84\x90\xcf\x17\xb6\x0c\xdd\x14\x08\x00\x66\
\x31\x2c\x25\x97\x70\xf5\xea\x97\x50\xd5\x46\x74\x74\xf6\xe0\xb7\
\x3b\x77\xa0\x6f\x1b\x08\xd5\xab\x00\xe1\xdf\xeb\xba\xde\xaf\xaa\
\x21\xb4\x1c\x3f\x0e\x49\x92\x40\x46\x22\x63\x10\x45\x11\xb1\xb9\
\xc4\x85\xc1\xc1\xc1\x9b\xf9\x7c\xde\x23\x08\xc2\xc1\x26\x28\x14\
\x0a\xf8\xe0\xc3\xcb\x38\xfb\xca\x99\x2f\x4c\x73\xe7\x2b\x59\x96\
\xd1\xd4\xd0\x08\x49\x92\x20\x08\x02\xc8\xc8\xf0\x28\x00\x80\x08\
\x84\x1a\xe6\x4e\x59\xd7\x0d\x64\xb3\xd9\xe6\xcd\xcd\x67\x97\x19\
\xb3\x5e\xf6\xfb\xfd\x4f\x4f\x9f\x3e\xf5\xa9\xc7\xab\xa4\x82\x81\
\x00\xfc\x3e\x3f\x6c\xdb\x3e\x1c\xfe\x3f\x11\x5f\xc4\xbb\xcd\x16\
\x27\xa0\x00\x00\x00\x00\x49\x45\x4e\x44\xae\x42\x60\x82\
\x00\x00\x07\x22\
\x89\
\x50\x4e\x47\x0d\x0a\x1a\x0a\x00\x00\x00\x0d\x49\x48\x44\x52\x00\
\x00\x00\x90\x00\x00\x00\x90\x08\x06\x00\x00\x00\xe7\x46\xe2\xb8\
\x00\x00\x00\x04\x73\x42\x49\x54\x08\x08\x08\x08\x7c\x08\x64\x88\
\x00\x00\x00\x09\x70\x48\x59\x73\x00\x00\x0e\xc4\x00\x00\x0e\xc4\
\x01\x95\x2b\x0e\x1b\x00\x00\x06\xc4\x49\x44\x41\x54\x78\x9c\xed\
\x9d\xbb\x71\x1b\x31\x14\x45\xb1\x1e\x05\x6a\x80\x33\x4a\xdc\x04\
\x4b\x70\xe8\x12\x14\xb3\x2c\xc5\x2a\xc1\xa1\x4b\x50\x13\x4e\x38\
\xa3\x06\x94\xd1\x81\x06\x36\x04\xee\x2e\x7e\xef\x73\x1f\xf6\x9d\
\x50\x23\xed\x82\x78\x87\x97\x58\x40\x00\x97\x97\xf7\xa7\x5b\x08\
\x21\x5c\x4e\xd7\x25\x18\xe4\xf9\xf1\xed\xa6\xdd\x86\x51\x5e\x3f\
\xce\x26\xfb\xfe\xe5\xfd\xe9\xb6\x44\x81\x22\x2e\x92\x3c\xd6\x04\
\x4a\x9d\x59\xf2\x1f\x44\x5c\x24\x39\xac\x08\xb4\xe6\xc9\xa6\x40\
\x11\x17\x89\x1f\x74\x81\xb6\xfc\xb8\x9c\xae\xcb\x52\xfa\xa5\xf4\
\x97\xa9\x1b\x26\x81\x05\x91\x50\x05\xaa\x71\xa2\x5a\xa0\xf4\x8f\
\x46\x1b\xa6\x01\xb2\x48\x68\x02\xd5\xb8\x10\x3d\xf8\xd2\xf0\x5a\
\x89\xd2\x0b\x58\x03\x51\x24\x14\x81\x7a\xea\xdf\x2d\x50\x7e\x21\
\x6b\x20\x89\xa4\x2d\x50\x6b\xdd\xd3\x9a\xdf\x35\xbc\x47\xa2\xfc\
\xa2\x96\x40\x10\x49\x4b\x20\x8a\x5a\x93\x09\xb4\x76\x71\x4b\x68\
\x8a\x24\x2d\xd0\x48\x8d\xf3\xfa\xae\x36\x7c\x54\xa2\xb5\x1b\x59\
\x41\x43\x24\x29\x81\x38\xea\xca\x26\xd0\xd6\x0d\xad\x20\x29\x12\
\xb7\x40\x54\xf5\x5c\xab\xe5\xb7\xda\x5f\xec\xe5\xe5\xfd\xe9\x46\
\x29\xa4\x14\xda\x03\x5b\x0a\x24\xfa\xfe\x81\xf3\xe2\x29\x96\x16\
\x6d\xf3\xf4\x79\xfd\x38\x2f\x08\x83\xed\x5a\x38\xa4\xd9\xaa\xdb\
\xa6\x40\x97\xd3\xf5\x6e\xa1\x95\x02\x64\x91\xf6\x24\x89\x89\x84\
\x2c\x92\x46\xd2\x8b\x25\x50\x0e\x92\x48\x2d\x52\x20\x8a\xc4\x2d\
\xce\x5e\x8d\x76\x05\xe2\x4a\xa1\x14\x4d\x91\x46\x24\x40\x10\x09\
\x61\x6c\xa9\x96\x40\x39\x92\x22\x51\x16\x5d\x43\x24\x49\x71\x4a\
\xf5\x28\x0a\x24\x91\x42\x29\x9c\x22\x71\x16\x59\x42\x24\x84\xc4\
\xc9\x81\x49\xa0\x1c\x4a\x91\x34\xe6\x74\x28\xef\xa9\x25\x4e\x4d\
\xdf\x57\x09\x24\x9d\x42\x29\x23\x22\x21\x2c\x4f\x8c\xb4\x01\x31\
\x71\x72\x60\x13\x28\xa7\x45\x24\xa4\x27\xa4\x1e\x91\x10\xc4\xa9\
\x7d\xc3\x56\x0b\xa4\x99\x42\x29\x7b\x22\x21\x89\x93\x53\x23\x12\
\x42\xff\xb6\x62\x26\x81\x72\x52\x91\x90\xc5\xc9\x59\x13\x09\x4d\
\x9c\x96\xe1\xc2\xea\x5a\x18\xc5\x85\xa5\x40\xeb\xfc\x5a\xa2\x48\
\x3f\xfe\xfc\xd4\x6e\xca\x10\x4d\x02\xa1\x62\x6d\xe1\xf3\xf9\xf1\
\xed\x86\x9a\x9a\xad\x21\xd1\xfc\x11\x86\x32\x16\xca\x41\x98\x19\
\x2e\x81\xdc\xb6\x5e\xcc\x8e\x81\xb6\x40\x14\x09\xa9\x2d\x7b\xf4\
\x0c\x51\xba\x04\x42\x4d\xa1\x14\x04\x91\xac\x88\x33\xc2\x74\x09\
\x94\xa3\x21\x92\x45\x71\x7a\x1f\x90\xba\x05\xb2\x90\x42\x29\x12\
\x22\x59\x14\x67\x94\xe9\x13\x28\x87\x43\x24\xeb\xe2\x8c\x4c\xcf\
\x0c\x09\x64\x2d\x85\x52\x28\x44\xb2\x2e\x0e\x05\x87\x4b\xa0\x9c\
\x1e\x91\x66\x12\x67\x74\x72\x78\x58\x20\xcb\x29\x94\x52\x23\xd2\
\x4c\xe2\x50\x71\xf8\x04\xca\x59\x13\x69\x56\x71\x28\x96\xa6\x48\
\x96\x32\x10\xd7\xc8\x46\xb1\xb6\x3c\xa2\x85\x27\xd0\x0a\xb3\x26\
\x4e\x0a\xd5\x9b\x9e\x4c\xa0\x19\xc6\x42\x47\x10\x87\x1a\x4f\xa0\
\x70\x3c\x71\x28\x87\x1c\xa4\x02\x59\x4b\xa1\xa3\x89\xc3\xc1\x21\
\x13\xe8\xc8\xe2\x50\x3f\xf0\x90\x0b\x84\x9c\x42\x47\x16\x87\x8b\
\x43\x24\x90\x8b\xf3\x09\xc7\x74\x0b\x8b\x40\x28\x29\xe4\xe2\xf0\
\x33\x65\x02\xb9\x38\xf7\x70\x4d\xf6\xb2\x09\xa4\x91\x42\x2e\x8e\
\x3c\x53\x24\x90\x8b\xb3\x0f\xe7\x52\xd3\x03\x67\xe7\xff\xfe\x6e\
\x7f\xdf\x93\x75\x7e\x7f\xff\x15\x42\x38\xb3\x5d\xdf\xd4\xae\xce\
\x59\xe1\x5a\xb8\x8d\xb5\xe5\xbc\x3e\xfb\xc6\x42\x5f\xd5\x2e\xc3\
\xfd\x26\xe6\xbc\x3e\xab\x40\x2e\x8f\x1e\x52\x52\x8a\x6c\x6d\x76\
\x91\xca\x58\x4d\x21\x36\x81\x5c\x1a\x3d\x24\x65\x14\x3b\x5c\xc1\
\x85\x2a\x63\x31\x85\x58\x04\x72\x59\xf4\x90\x96\x50\xf4\x78\x17\
\x17\xab\x8c\xb5\x14\x22\x17\xc8\x25\xd1\x43\x43\x3e\xf1\x03\xa6\
\x5c\xb0\x32\x96\x52\x88\x54\x20\x97\x43\x0f\x2d\xe9\x54\x8e\xb8\
\x73\xd1\xca\x58\x49\x21\x32\x81\x5c\x0a\x3d\x34\x65\x53\x3b\x64\
\xd3\x85\x2b\x63\x21\x85\x48\x04\x72\x19\xf4\xd0\x96\x4c\xf5\x98\
\x5f\x17\xaf\x8c\xb6\x20\x25\x86\x05\x72\x09\xf4\x40\x90\x4b\xfd\
\xa0\x71\x17\xb0\x0c\x82\x28\x5b\x0c\x09\xe4\xc5\xd7\x03\x45\x2a\
\xf5\x04\x0a\xc1\x45\xac\x01\x45\x98\x9c\x6e\x81\xbc\xe8\x7a\x20\
\xc9\x04\x91\x40\x21\xb8\x90\x35\x20\x89\x13\xe9\xda\x95\xc1\xbd\
\x8b\xc0\xb1\x83\x6f\xeb\x71\x86\x98\x62\x67\xea\xd1\x40\xfa\x04\
\x68\x1e\x03\x71\x8f\x55\x7c\x2c\x54\x06\xe9\x53\xa3\x49\x20\x97\
\x67\x5e\x44\x1f\xe3\x5d\x24\x7d\x50\x52\xa8\x5a\x20\x97\x66\x5e\
\x54\x96\x32\x5c\x28\x7d\x10\x52\xa8\x4a\x20\x97\x65\x5e\x54\xff\
\x9d\xc3\xc5\xd2\x47\x3b\x85\x8a\x02\xb9\x24\xf3\x02\xf1\x2f\xad\
\x2e\x98\x3e\x9a\x29\xb4\x2b\x90\xcb\x31\x2f\x50\xdb\x7a\x5c\x34\
\x7d\xb4\x52\x68\x53\x20\x97\x62\x5e\x20\xb7\x36\xbb\x70\xfa\x68\
\xa4\xd0\xaa\x40\x2e\xc3\xbc\x40\x1f\xef\xe2\xe2\xe9\x23\x9d\x42\
\x77\x02\xb9\x04\xf3\x62\xe2\x88\x3b\x17\x50\x1f\xc9\x14\xfa\x22\
\x90\x17\x7f\x5e\x4c\x1d\xf3\xeb\x22\xea\x23\x95\x42\xff\x04\xf2\
\xa2\xcf\x8b\xc9\xaf\x3a\x70\x21\xf5\x91\x48\xa1\x6f\x21\x78\xb1\
\x67\x86\x5b\xa2\xe5\xf9\xf1\xed\xc6\x59\x60\x89\x6f\x2d\xfc\xfc\
\x4e\x2c\x9b\x48\x7c\x9f\x1a\x67\xff\x3c\x58\x97\xc7\x32\xaf\x1f\
\xe7\xe5\x47\xe0\xef\x23\xce\x1a\xfb\xc6\x42\x05\xa4\x3f\xd2\x5f\
\xde\x9f\x6e\xe6\xbe\x74\xd7\xd3\xe7\x9e\x19\xc7\x82\x9e\x40\x02\
\x20\x88\xc3\x95\x42\x2c\x02\x79\xfa\x7c\x82\x20\x0e\x37\x9e\x40\
\x0c\xa0\x8a\xc3\x91\x42\xe4\x02\x1d\x39\x7d\x50\xc5\xe1\xc4\x13\
\x88\x00\x4b\xe2\x50\xa7\x10\xa9\x40\x47\x4b\x1f\x4b\xe2\x70\xe1\
\x09\xd4\x81\x75\x71\x28\x53\x88\x4c\xa0\x23\xa4\x8f\x75\x71\x38\
\x80\x39\xa5\x15\x9d\xd9\xe4\xa1\x7a\xc3\x93\x08\x34\x6b\xfa\xa4\
\xd2\x3c\x3f\xbe\xdd\xb4\x0f\x32\x40\xc4\xc7\x40\x2b\xec\xa5\x4d\
\x94\x68\x86\x44\xa2\x18\x0b\x0d\x0b\x34\x53\xfa\xb4\x48\x31\x93\
\x48\x23\x78\x02\x85\x31\x09\xac\x8b\x34\x9a\x42\x43\x02\x59\x4f\
\x1f\xca\xa2\x5b\x17\xa9\x97\x43\x26\x10\x67\x91\x2d\x8a\x34\x92\
\x42\xdd\x02\x59\x4c\x1f\xc9\xa2\x5a\x14\xa9\x87\x43\x24\x90\x66\
\x11\xad\x88\xd4\x9b\x42\x5d\x02\x59\x49\x1f\xa4\xa2\x59\x11\xa9\
\x95\x29\x13\x08\xb9\x48\xc8\x22\xf5\xa4\x50\xb3\x40\xc8\xe9\x83\
\x58\x94\x2d\xfe\xcf\x6a\xf3\x6f\xeb\xe1\xc4\xfc\x5a\x58\xdc\xf3\
\x64\x49\x1e\x64\x5a\x03\xa2\x49\x20\xb4\xf4\x49\xe3\xd6\xe2\x5a\
\xd5\xeb\xc7\x79\xb9\x9c\xae\x0b\xd7\x96\x1b\x09\x4c\x8e\x81\xf6\
\x3a\x1c\x79\x8c\x11\x59\x6b\x5b\x7c\x4d\x08\x6f\xd2\x96\xb1\x50\
\xb5\x40\x08\x2f\xac\xe5\x9d\x8a\x28\x52\x4d\x5b\x90\x44\xaa\xc1\
\x44\x02\x8d\x44\x3c\x82\x48\x3d\xf7\xd6\x16\xa9\x36\x85\xaa\x04\
\xd2\x7a\x11\x94\x63\x03\x0d\x91\x28\xee\xa5\x2d\x52\x09\xc8\x04\
\xe2\x1c\x54\x4a\x88\xc4\x71\x6d\x0d\x91\x6a\x52\xa8\x28\x90\x64\
\x83\x25\x9f\x46\x38\x44\x92\x48\x37\xb4\x44\x82\x48\x20\xcd\xc7\
\x58\x0a\x91\x34\xc6\x57\x52\x22\x95\x52\x68\x57\x20\xee\xc6\x21\
\xcd\x7f\xf4\x88\x84\xf0\x84\xa7\x9d\x48\x2a\x09\x84\x24\x4e\x4e\
\x8d\x48\x08\xe2\xe4\x70\x8a\xb4\x97\x42\x9b\x1d\xc1\xd1\x10\x0e\
\x71\x24\x67\x9f\x11\xc5\xd9\x82\xba\x7e\x5b\xb5\x13\x59\x0b\xb3\
\x3e\x5d\x1f\x82\x2d\x79\x42\xa0\xef\xf3\x2d\x21\x57\x6f\x40\x65\
\xaf\x84\x34\xd2\xeb\x5f\xd6\x44\x8a\x50\xd4\x74\xad\x9e\x2c\x02\
\x69\x3c\x8e\x4b\x73\x54\x91\xf2\xda\xde\x75\xc2\xc8\x0d\x34\x3e\
\xa6\xb4\x57\xe0\x8f\x26\x12\x8b\x40\x08\xf3\x38\xda\x1c\x49\xa4\
\xb4\xde\x5f\x5e\x74\xeb\xc5\x10\x06\xc6\x28\x02\x45\x8e\x20\xd2\
\xb0\x40\x08\xe2\x44\xd0\x04\x8a\xcc\x2e\x52\x74\xe0\xdf\x8b\xac\
\xf9\x43\x24\x71\x22\xa8\x02\x45\x66\x15\xa9\x49\x20\x44\x71\x22\
\xe8\x02\x45\x66\x14\xe9\x72\xba\x2e\xbb\xd3\xdf\xc8\xe2\x44\xac\
\x08\x14\x99\x49\xa4\x4d\x81\x2c\x88\x13\xb1\x26\x50\x64\x16\x91\
\x96\xf4\x07\x96\xc4\x89\x58\x15\x28\x62\x5d\xa4\xbf\xa8\xcc\xde\
\x47\x76\xb8\xb3\xea\x00\x00\x00\x00\x49\x45\x4e\x44\xae\x42\x60\
\x82\
"

qt_resource_name = "\
\x00\x09\
\x0c\x78\x54\x88\
\x00\x6e\
\x00\x65\x00\x77\x00\x50\x00\x72\x00\x65\x00\x66\x00\x69\x00\x78\
\x00\x06\
\x07\x03\x7d\xc3\
\x00\x69\
\x00\x6d\x00\x61\x00\x67\x00\x65\x00\x73\
\x00\x0e\
\x0a\x51\x2d\xe7\
\x00\x69\
\x00\x64\x00\x65\x00\x6e\x00\x74\x00\x69\x00\x74\x00\x69\x00\x65\x00\x73\x00\x2e\x00\x70\x00\x6e\x00\x67\
\x00\x09\
\x09\x6b\xb7\xc7\
\x00\x69\
\x00\x6e\x00\x62\x00\x6f\x00\x78\x00\x2e\x00\x70\x00\x6e\x00\x67\
\x00\x0b\
\x0a\xd0\x22\xa7\
\x00\x72\
\x00\x65\x00\x64\x00\x69\x00\x63\x00\x6f\x00\x6e\x00\x2e\x00\x70\x00\x6e\x00\x67\
\x00\x08\
\x0c\x57\x58\x67\
\x00\x73\
\x00\x65\x00\x6e\x00\x74\x00\x2e\x00\x70\x00\x6e\x00\x67\
\x00\x10\
\x0c\xc3\x45\x27\
\x00\x71\
\x00\x69\x00\x64\x00\x65\x00\x6e\x00\x74\x00\x69\x00\x63\x00\x6f\x00\x6e\x00\x5f\x00\x78\x00\x2e\x00\x70\x00\x6e\x00\x67\
\x00\x0d\
\x02\xe8\x12\x87\
\x00\x62\
\x00\x6c\x00\x61\x00\x63\x00\x6b\x00\x6c\x00\x69\x00\x73\x00\x74\x00\x2e\x00\x70\x00\x6e\x00\x67\
\x00\x08\
\x0c\x47\x58\x67\
\x00\x73\
\x00\x65\x00\x6e\x00\x64\x00\x2e\x00\x70\x00\x6e\x00\x67\
\x00\x0f\
\x05\x46\x9a\xc7\
\x00\x61\
\x00\x64\x00\x64\x00\x72\x00\x65\x00\x73\x00\x73\x00\x62\x00\x6f\x00\x6f\x00\x6b\x00\x2e\x00\x70\x00\x6e\x00\x67\
\x00\x11\
\x07\x34\x2d\xc7\
\x00\x6e\
\x00\x65\x00\x74\x00\x77\x00\x6f\x00\x72\x00\x6b\x00\x73\x00\x74\x00\x61\x00\x74\x00\x75\x00\x73\x00\x2e\x00\x70\x00\x6e\x00\x67\
\
\x00\x18\
\x02\x47\xd6\x47\
\x00\x63\
\x00\x61\x00\x6e\x00\x2d\x00\x69\x00\x63\x00\x6f\x00\x6e\x00\x2d\x00\x32\x00\x34\x00\x70\x00\x78\x00\x2d\x00\x79\x00\x65\x00\x6c\
\x00\x6c\x00\x6f\x00\x77\x00\x2e\x00\x70\x00\x6e\x00\x67\
\x00\x11\
\x02\xa0\x44\xa7\
\x00\x73\
\x00\x75\x00\x62\x00\x73\x00\x63\x00\x72\x00\x69\x00\x70\x00\x74\x00\x69\x00\x6f\x00\x6e\x00\x73\x00\x2e\x00\x70\x00\x6e\x00\x67\
\
\x00\x0e\
\x09\x39\xff\x47\
\x00\x71\
\x00\x69\x00\x64\x00\x65\x00\x6e\x00\x74\x00\x69\x00\x63\x00\x6f\x00\x6e\x00\x2e\x00\x70\x00\x6e\x00\x67\
\x00\x11\
\x05\x89\x73\x07\
\x00\x63\
\x00\x61\x00\x6e\x00\x2d\x00\x69\x00\x63\x00\x6f\x00\x6e\x00\x2d\x00\x32\x00\x34\x00\x70\x00\x78\x00\x2e\x00\x70\x00\x6e\x00\x67\
\
\x00\x15\
\x0c\xfc\x45\x87\
\x00\x63\
\x00\x61\x00\x6e\x00\x2d\x00\x69\x00\x63\x00\x6f\x00\x6e\x00\x2d\x00\x32\x00\x34\x00\x70\x00\x78\x00\x2d\x00\x72\x00\x65\x00\x64\
\x00\x2e\x00\x70\x00\x6e\x00\x67\
\x00\x0d\
\x07\x76\xdf\x07\
\x00\x67\
\x00\x72\x00\x65\x00\x65\x00\x6e\x00\x69\x00\x63\x00\x6f\x00\x6e\x00\x2e\x00\x70\x00\x6e\x00\x67\
\x00\x17\
\x00\xd3\x62\xc7\
\x00\x63\
\x00\x61\x00\x6e\x00\x2d\x00\x69\x00\x63\x00\x6f\x00\x6e\x00\x2d\x00\x32\x00\x34\x00\x70\x00\x78\x00\x2d\x00\x67\x00\x72\x00\x65\
\x00\x65\x00\x6e\x00\x2e\x00\x70\x00\x6e\x00\x67\
\x00\x11\
\x02\x8c\x5e\x67\
\x00\x6e\
\x00\x6f\x00\x5f\x00\x69\x00\x64\x00\x65\x00\x6e\x00\x74\x00\x69\x00\x63\x00\x6f\x00\x6e\x00\x73\x00\x2e\x00\x70\x00\x6e\x00\x67\
\
\x00\x0e\
\x02\x47\x93\x47\
\x00\x79\
\x00\x65\x00\x6c\x00\x6c\x00\x6f\x00\x77\x00\x69\x00\x63\x00\x6f\x00\x6e\x00\x2e\x00\x70\x00\x6e\x00\x67\
\x00\x12\
\x03\xf4\x2e\xc7\
\x00\x71\
\x00\x69\x00\x64\x00\x65\x00\x6e\x00\x74\x00\x69\x00\x63\x00\x6f\x00\x6e\x00\x5f\x00\x74\x00\x77\x00\x6f\x00\x2e\x00\x70\x00\x6e\
\x00\x67\
\x00\x11\
\x03\x89\x73\x27\
\x00\x63\
\x00\x61\x00\x6e\x00\x2d\x00\x69\x00\x63\x00\x6f\x00\x6e\x00\x2d\x00\x31\x00\x36\x00\x70\x00\x78\x00\x2e\x00\x70\x00\x6e\x00\x67\
\
\x00\x14\
\x07\x12\xd0\xa7\
\x00\x71\
\x00\x69\x00\x64\x00\x65\x00\x6e\x00\x74\x00\x69\x00\x63\x00\x6f\x00\x6e\x00\x5f\x00\x74\x00\x77\x00\x6f\x00\x5f\x00\x78\x00\x2e\
\x00\x70\x00\x6e\x00\x67\
"

qt_resource_struct = "\
\x00\x00\x00\x00\x00\x02\x00\x00\x00\x01\x00\x00\x00\x01\
\x00\x00\x00\x00\x00\x02\x00\x00\x00\x01\x00\x00\x00\x02\
\x00\x00\x00\x18\x00\x02\x00\x00\x00\x15\x00\x00\x00\x03\
\x00\x00\x02\x36\x00\x00\x00\x00\x00\x01\x00\x00\x3f\x80\
\x00\x00\x02\x92\x00\x00\x00\x00\x00\x01\x00\x00\x47\xb7\
\x00\x00\x01\x3e\x00\x00\x00\x00\x00\x01\x00\x00\x1d\x49\
\x00\x00\x02\x6a\x00\x00\x00\x00\x00\x01\x00\x00\x46\xee\
\x00\x00\x01\x74\x00\x00\x00\x00\x00\x01\x00\x00\x24\xaf\
\x00\x00\x00\xbc\x00\x00\x00\x00\x00\x01\x00\x00\x11\xfc\
\x00\x00\x02\xde\x00\x00\x00\x00\x00\x01\x00\x00\x51\x02\
\x00\x00\x02\xb4\x00\x00\x00\x00\x00\x01\x00\x00\x4a\x35\
\x00\x00\x00\xf2\x00\x00\x00\x00\x00\x01\x00\x00\x18\x2b\
\x00\x00\x01\xbe\x00\x00\x00\x00\x00\x01\x00\x00\x2d\x9f\
\x00\x00\x03\x06\x00\x00\x00\x00\x00\x01\x00\x00\x54\xf5\
\x00\x00\x01\x16\x00\x00\x00\x00\x00\x01\x00\x00\x1a\xd0\
\x00\x00\x02\x16\x00\x00\x00\x00\x00\x01\x00\x00\x3c\x48\
\x00\x00\x01\x9c\x00\x00\x00\x00\x00\x01\x00\x00\x27\x2a\
\x00\x00\x00\x4c\x00\x00\x00\x00\x00\x01\x00\x00\x03\x6a\
\x00\x00\x00\x2a\x00\x00\x00\x00\x00\x01\x00\x00\x00\x00\
\x00\x00\x00\x64\x00\x00\x00\x00\x00\x01\x00\x00\x06\x1d\
\x00\x00\x00\xdc\x00\x00\x00\x00\x00\x01\x00\x00\x14\xf0\
\x00\x00\x00\x80\x00\x00\x00\x00\x00\x01\x00\x00\x08\xed\
\x00\x00\x00\x96\x00\x00\x00\x00\x00\x01\x00\x00\x0b\x15\
\x00\x00\x01\xe6\x00\x00\x00\x00\x00\x01\x00\x00\x34\xdf\
"

def qInitResources():
    QtCore.qRegisterResourceData(0x01, qt_resource_struct, qt_resource_name, qt_resource_data)

def qCleanupResources():
    QtCore.qUnregisterResourceData(0x01, qt_resource_struct, qt_resource_name, qt_resource_data)

qInitResources()

########NEW FILE########
__FILENAME__ = connect
# -*- coding: utf-8 -*-

# Form implementation generated from reading ui file 'connect.ui'
#
# Created: Wed Jul 24 12:42:01 2013
#      by: PyQt4 UI code generator 4.10
#
# WARNING! All changes made in this file will be lost!

from PyQt4 import QtCore, QtGui

try:
    _fromUtf8 = QtCore.QString.fromUtf8
except AttributeError:
    def _fromUtf8(s):
        return s

try:
    _encoding = QtGui.QApplication.UnicodeUTF8
    def _translate(context, text, disambig):
        return QtGui.QApplication.translate(context, text, disambig, _encoding)
except AttributeError:
    def _translate(context, text, disambig):
        return QtGui.QApplication.translate(context, text, disambig)

class Ui_connectDialog(object):
    def setupUi(self, connectDialog):
        connectDialog.setObjectName(_fromUtf8("connectDialog"))
        connectDialog.resize(400, 124)
        self.gridLayout = QtGui.QGridLayout(connectDialog)
        self.gridLayout.setObjectName(_fromUtf8("gridLayout"))
        self.label = QtGui.QLabel(connectDialog)
        self.label.setObjectName(_fromUtf8("label"))
        self.gridLayout.addWidget(self.label, 0, 0, 1, 2)
        self.radioButtonConnectNow = QtGui.QRadioButton(connectDialog)
        self.radioButtonConnectNow.setChecked(True)
        self.radioButtonConnectNow.setObjectName(_fromUtf8("radioButtonConnectNow"))
        self.gridLayout.addWidget(self.radioButtonConnectNow, 1, 0, 1, 2)
        self.radioButtonConfigureNetwork = QtGui.QRadioButton(connectDialog)
        self.radioButtonConfigureNetwork.setObjectName(_fromUtf8("radioButtonConfigureNetwork"))
        self.gridLayout.addWidget(self.radioButtonConfigureNetwork, 2, 0, 1, 2)
        spacerItem = QtGui.QSpacerItem(185, 24, QtGui.QSizePolicy.Expanding, QtGui.QSizePolicy.Minimum)
        self.gridLayout.addItem(spacerItem, 3, 0, 1, 1)
        self.buttonBox = QtGui.QDialogButtonBox(connectDialog)
        self.buttonBox.setOrientation(QtCore.Qt.Horizontal)
        self.buttonBox.setStandardButtons(QtGui.QDialogButtonBox.Ok)
        self.buttonBox.setObjectName(_fromUtf8("buttonBox"))
        self.gridLayout.addWidget(self.buttonBox, 3, 1, 1, 1)

        self.retranslateUi(connectDialog)
        QtCore.QObject.connect(self.buttonBox, QtCore.SIGNAL(_fromUtf8("accepted()")), connectDialog.accept)
        QtCore.QObject.connect(self.buttonBox, QtCore.SIGNAL(_fromUtf8("rejected()")), connectDialog.reject)
        QtCore.QMetaObject.connectSlotsByName(connectDialog)

    def retranslateUi(self, connectDialog):
        connectDialog.setWindowTitle(_translate("connectDialog", "Bitmessage", None))
        self.label.setText(_translate("connectDialog", "Bitmessage won\'t connect to anyone until you let it. ", None))
        self.radioButtonConnectNow.setText(_translate("connectDialog", "Connect now", None))
        self.radioButtonConfigureNetwork.setText(_translate("connectDialog", "Let me configure special network settings first", None))


########NEW FILE########
__FILENAME__ = help
# -*- coding: utf-8 -*-

# Form implementation generated from reading ui file 'help.ui'
#
# Created: Mon Mar 11 11:20:54 2013
#      by: PyQt4 UI code generator 4.9.4
#
# WARNING! All changes made in this file will be lost!

from PyQt4 import QtCore, QtGui

try:
    _fromUtf8 = QtCore.QString.fromUtf8
except AttributeError:
    _fromUtf8 = lambda s: s

class Ui_helpDialog(object):
    def setupUi(self, helpDialog):
        helpDialog.setObjectName(_fromUtf8("helpDialog"))
        helpDialog.resize(335, 96)
        self.formLayout = QtGui.QFormLayout(helpDialog)
        self.formLayout.setObjectName(_fromUtf8("formLayout"))
        self.labelHelpURI = QtGui.QLabel(helpDialog)
        self.labelHelpURI.setOpenExternalLinks(True)
        self.labelHelpURI.setObjectName(_fromUtf8("labelHelpURI"))
        self.formLayout.setWidget(1, QtGui.QFormLayout.LabelRole, self.labelHelpURI)
        self.label = QtGui.QLabel(helpDialog)
        self.label.setWordWrap(True)
        self.label.setObjectName(_fromUtf8("label"))
        self.formLayout.setWidget(0, QtGui.QFormLayout.SpanningRole, self.label)
        spacerItem = QtGui.QSpacerItem(40, 20, QtGui.QSizePolicy.Expanding, QtGui.QSizePolicy.Minimum)
        self.formLayout.setItem(2, QtGui.QFormLayout.LabelRole, spacerItem)
        self.buttonBox = QtGui.QDialogButtonBox(helpDialog)
        self.buttonBox.setOrientation(QtCore.Qt.Horizontal)
        self.buttonBox.setStandardButtons(QtGui.QDialogButtonBox.Ok)
        self.buttonBox.setObjectName(_fromUtf8("buttonBox"))
        self.formLayout.setWidget(2, QtGui.QFormLayout.FieldRole, self.buttonBox)

        self.retranslateUi(helpDialog)
        QtCore.QObject.connect(self.buttonBox, QtCore.SIGNAL(_fromUtf8("accepted()")), helpDialog.accept)
        QtCore.QObject.connect(self.buttonBox, QtCore.SIGNAL(_fromUtf8("rejected()")), helpDialog.reject)
        QtCore.QMetaObject.connectSlotsByName(helpDialog)

    def retranslateUi(self, helpDialog):
        helpDialog.setWindowTitle(QtGui.QApplication.translate("helpDialog", "Help", None, QtGui.QApplication.UnicodeUTF8))
        self.labelHelpURI.setText(QtGui.QApplication.translate("helpDialog", "<a href=\"http://Bitmessage.org/wiki/PyBitmessage_Help\">http://Bitmessage.org/wiki/PyBitmessage_Help</a>", None, QtGui.QApplication.UnicodeUTF8))
        self.label.setText(QtGui.QApplication.translate("helpDialog", "As Bitmessage is a collaborative project, help can be found online in the Bitmessage Wiki:", None, QtGui.QApplication.UnicodeUTF8))


########NEW FILE########
__FILENAME__ = iconglossary
# -*- coding: utf-8 -*-

# Form implementation generated from reading ui file 'iconglossary.ui'
#
# Created: Thu Jun 13 20:15:48 2013
#      by: PyQt4 UI code generator 4.10.1
#
# WARNING! All changes made in this file will be lost!

from PyQt4 import QtCore, QtGui

try:
    _fromUtf8 = QtCore.QString.fromUtf8
except AttributeError:
    def _fromUtf8(s):
        return s

try:
    _encoding = QtGui.QApplication.UnicodeUTF8
    def _translate(context, text, disambig):
        return QtGui.QApplication.translate(context, text, disambig, _encoding)
except AttributeError:
    def _translate(context, text, disambig):
        return QtGui.QApplication.translate(context, text, disambig)

class Ui_iconGlossaryDialog(object):
    def setupUi(self, iconGlossaryDialog):
        iconGlossaryDialog.setObjectName(_fromUtf8("iconGlossaryDialog"))
        iconGlossaryDialog.resize(424, 282)
        self.gridLayout = QtGui.QGridLayout(iconGlossaryDialog)
        self.gridLayout.setObjectName(_fromUtf8("gridLayout"))
        self.groupBox = QtGui.QGroupBox(iconGlossaryDialog)
        self.groupBox.setObjectName(_fromUtf8("groupBox"))
        self.gridLayout_2 = QtGui.QGridLayout(self.groupBox)
        self.gridLayout_2.setObjectName(_fromUtf8("gridLayout_2"))
        self.label = QtGui.QLabel(self.groupBox)
        self.label.setText(_fromUtf8(""))
        self.label.setPixmap(QtGui.QPixmap(_fromUtf8(":/newPrefix/images/redicon.png")))
        self.label.setObjectName(_fromUtf8("label"))
        self.gridLayout_2.addWidget(self.label, 0, 0, 1, 1)
        self.label_2 = QtGui.QLabel(self.groupBox)
        self.label_2.setObjectName(_fromUtf8("label_2"))
        self.gridLayout_2.addWidget(self.label_2, 0, 1, 1, 1)
        self.label_3 = QtGui.QLabel(self.groupBox)
        self.label_3.setText(_fromUtf8(""))
        self.label_3.setPixmap(QtGui.QPixmap(_fromUtf8(":/newPrefix/images/yellowicon.png")))
        self.label_3.setObjectName(_fromUtf8("label_3"))
        self.gridLayout_2.addWidget(self.label_3, 1, 0, 1, 1)
        self.label_4 = QtGui.QLabel(self.groupBox)
        self.label_4.setAlignment(QtCore.Qt.AlignLeading|QtCore.Qt.AlignLeft|QtCore.Qt.AlignTop)
        self.label_4.setWordWrap(True)
        self.label_4.setObjectName(_fromUtf8("label_4"))
        self.gridLayout_2.addWidget(self.label_4, 1, 1, 2, 1)
        spacerItem = QtGui.QSpacerItem(20, 73, QtGui.QSizePolicy.Minimum, QtGui.QSizePolicy.Expanding)
        self.gridLayout_2.addItem(spacerItem, 2, 0, 2, 1)
        self.labelPortNumber = QtGui.QLabel(self.groupBox)
        self.labelPortNumber.setObjectName(_fromUtf8("labelPortNumber"))
        self.gridLayout_2.addWidget(self.labelPortNumber, 3, 1, 1, 1)
        self.label_5 = QtGui.QLabel(self.groupBox)
        self.label_5.setText(_fromUtf8(""))
        self.label_5.setPixmap(QtGui.QPixmap(_fromUtf8(":/newPrefix/images/greenicon.png")))
        self.label_5.setObjectName(_fromUtf8("label_5"))
        self.gridLayout_2.addWidget(self.label_5, 4, 0, 1, 1)
        self.label_6 = QtGui.QLabel(self.groupBox)
        self.label_6.setWordWrap(True)
        self.label_6.setObjectName(_fromUtf8("label_6"))
        self.gridLayout_2.addWidget(self.label_6, 4, 1, 1, 1)
        self.gridLayout.addWidget(self.groupBox, 0, 0, 1, 1)
        self.buttonBox = QtGui.QDialogButtonBox(iconGlossaryDialog)
        self.buttonBox.setOrientation(QtCore.Qt.Horizontal)
        self.buttonBox.setStandardButtons(QtGui.QDialogButtonBox.Ok)
        self.buttonBox.setObjectName(_fromUtf8("buttonBox"))
        self.gridLayout.addWidget(self.buttonBox, 1, 0, 1, 1)

        self.retranslateUi(iconGlossaryDialog)
        QtCore.QObject.connect(self.buttonBox, QtCore.SIGNAL(_fromUtf8("accepted()")), iconGlossaryDialog.accept)
        QtCore.QObject.connect(self.buttonBox, QtCore.SIGNAL(_fromUtf8("rejected()")), iconGlossaryDialog.reject)
        QtCore.QMetaObject.connectSlotsByName(iconGlossaryDialog)

    def retranslateUi(self, iconGlossaryDialog):
        iconGlossaryDialog.setWindowTitle(_translate("iconGlossaryDialog", "Icon Glossary", None))
        self.groupBox.setTitle(_translate("iconGlossaryDialog", "Icon Glossary", None))
        self.label_2.setText(_translate("iconGlossaryDialog", "You have no connections with other peers. ", None))
        self.label_4.setText(_translate("iconGlossaryDialog", "You have made at least one connection to a peer using an outgoing connection but you have not yet received any incoming connections. Your firewall or home router probably isn\'t configured to forward incoming TCP connections to your computer. Bitmessage will work just fine but it would help the Bitmessage network if you allowed for incoming connections and will help you be a better-connected node.", None))
        self.labelPortNumber.setText(_translate("iconGlossaryDialog", "You are using TCP port ?. (This can be changed in the settings).", None))
        self.label_6.setText(_translate("iconGlossaryDialog", "You do have connections with other peers and your firewall is correctly configured.", None))

import bitmessage_icons_rc

if __name__ == "__main__":
    import sys
    app = QtGui.QApplication(sys.argv)
    iconGlossaryDialog = QtGui.QDialog()
    ui = Ui_iconGlossaryDialog()
    ui.setupUi(iconGlossaryDialog)
    iconGlossaryDialog.show()
    sys.exit(app.exec_())


########NEW FILE########
__FILENAME__ = newaddressdialog
# -*- coding: utf-8 -*-

# Form implementation generated from reading ui file 'newaddressdialog.ui'
#
# Created: Sun Sep 15 23:53:31 2013
#      by: PyQt4 UI code generator 4.10.2
#
# WARNING! All changes made in this file will be lost!

from PyQt4 import QtCore, QtGui

try:
    _fromUtf8 = QtCore.QString.fromUtf8
except AttributeError:
    def _fromUtf8(s):
        return s

try:
    _encoding = QtGui.QApplication.UnicodeUTF8
    def _translate(context, text, disambig):
        return QtGui.QApplication.translate(context, text, disambig, _encoding)
except AttributeError:
    def _translate(context, text, disambig):
        return QtGui.QApplication.translate(context, text, disambig)

class Ui_NewAddressDialog(object):
    def setupUi(self, NewAddressDialog):
        NewAddressDialog.setObjectName(_fromUtf8("NewAddressDialog"))
        NewAddressDialog.resize(723, 704)
        self.formLayout = QtGui.QFormLayout(NewAddressDialog)
        self.formLayout.setFieldGrowthPolicy(QtGui.QFormLayout.AllNonFixedFieldsGrow)
        self.formLayout.setObjectName(_fromUtf8("formLayout"))
        self.label = QtGui.QLabel(NewAddressDialog)
        self.label.setAlignment(QtCore.Qt.AlignBottom|QtCore.Qt.AlignLeading|QtCore.Qt.AlignLeft)
        self.label.setWordWrap(True)
        self.label.setObjectName(_fromUtf8("label"))
        self.formLayout.setWidget(0, QtGui.QFormLayout.SpanningRole, self.label)
        self.label_5 = QtGui.QLabel(NewAddressDialog)
        self.label_5.setWordWrap(True)
        self.label_5.setObjectName(_fromUtf8("label_5"))
        self.formLayout.setWidget(2, QtGui.QFormLayout.SpanningRole, self.label_5)
        self.line = QtGui.QFrame(NewAddressDialog)
        sizePolicy = QtGui.QSizePolicy(QtGui.QSizePolicy.Preferred, QtGui.QSizePolicy.Fixed)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.line.sizePolicy().hasHeightForWidth())
        self.line.setSizePolicy(sizePolicy)
        self.line.setMinimumSize(QtCore.QSize(100, 2))
        self.line.setFrameShape(QtGui.QFrame.HLine)
        self.line.setFrameShadow(QtGui.QFrame.Sunken)
        self.line.setObjectName(_fromUtf8("line"))
        self.formLayout.setWidget(4, QtGui.QFormLayout.SpanningRole, self.line)
        self.radioButtonRandomAddress = QtGui.QRadioButton(NewAddressDialog)
        self.radioButtonRandomAddress.setChecked(True)
        self.radioButtonRandomAddress.setObjectName(_fromUtf8("radioButtonRandomAddress"))
        self.buttonGroup = QtGui.QButtonGroup(NewAddressDialog)
        self.buttonGroup.setObjectName(_fromUtf8("buttonGroup"))
        self.buttonGroup.addButton(self.radioButtonRandomAddress)
        self.formLayout.setWidget(5, QtGui.QFormLayout.SpanningRole, self.radioButtonRandomAddress)
        self.radioButtonDeterministicAddress = QtGui.QRadioButton(NewAddressDialog)
        self.radioButtonDeterministicAddress.setObjectName(_fromUtf8("radioButtonDeterministicAddress"))
        self.buttonGroup.addButton(self.radioButtonDeterministicAddress)
        self.formLayout.setWidget(6, QtGui.QFormLayout.LabelRole, self.radioButtonDeterministicAddress)
        self.checkBoxEighteenByteRipe = QtGui.QCheckBox(NewAddressDialog)
        self.checkBoxEighteenByteRipe.setObjectName(_fromUtf8("checkBoxEighteenByteRipe"))
        self.formLayout.setWidget(9, QtGui.QFormLayout.SpanningRole, self.checkBoxEighteenByteRipe)
        self.groupBoxDeterministic = QtGui.QGroupBox(NewAddressDialog)
        self.groupBoxDeterministic.setObjectName(_fromUtf8("groupBoxDeterministic"))
        self.gridLayout = QtGui.QGridLayout(self.groupBoxDeterministic)
        self.gridLayout.setObjectName(_fromUtf8("gridLayout"))
        self.label_9 = QtGui.QLabel(self.groupBoxDeterministic)
        self.label_9.setObjectName(_fromUtf8("label_9"))
        self.gridLayout.addWidget(self.label_9, 6, 0, 1, 1)
        self.label_8 = QtGui.QLabel(self.groupBoxDeterministic)
        self.label_8.setObjectName(_fromUtf8("label_8"))
        self.gridLayout.addWidget(self.label_8, 5, 0, 1, 3)
        self.spinBoxNumberOfAddressesToMake = QtGui.QSpinBox(self.groupBoxDeterministic)
        self.spinBoxNumberOfAddressesToMake.setMinimum(1)
        self.spinBoxNumberOfAddressesToMake.setProperty("value", 8)
        self.spinBoxNumberOfAddressesToMake.setObjectName(_fromUtf8("spinBoxNumberOfAddressesToMake"))
        self.gridLayout.addWidget(self.spinBoxNumberOfAddressesToMake, 4, 3, 1, 1)
        self.label_6 = QtGui.QLabel(self.groupBoxDeterministic)
        self.label_6.setObjectName(_fromUtf8("label_6"))
        self.gridLayout.addWidget(self.label_6, 0, 0, 1, 1)
        self.label_11 = QtGui.QLabel(self.groupBoxDeterministic)
        self.label_11.setObjectName(_fromUtf8("label_11"))
        self.gridLayout.addWidget(self.label_11, 4, 0, 1, 3)
        spacerItem = QtGui.QSpacerItem(73, 20, QtGui.QSizePolicy.Expanding, QtGui.QSizePolicy.Minimum)
        self.gridLayout.addItem(spacerItem, 6, 1, 1, 1)
        self.label_10 = QtGui.QLabel(self.groupBoxDeterministic)
        self.label_10.setObjectName(_fromUtf8("label_10"))
        self.gridLayout.addWidget(self.label_10, 6, 2, 1, 1)
        spacerItem1 = QtGui.QSpacerItem(42, 20, QtGui.QSizePolicy.Expanding, QtGui.QSizePolicy.Minimum)
        self.gridLayout.addItem(spacerItem1, 6, 3, 1, 1)
        self.label_7 = QtGui.QLabel(self.groupBoxDeterministic)
        self.label_7.setObjectName(_fromUtf8("label_7"))
        self.gridLayout.addWidget(self.label_7, 2, 0, 1, 1)
        self.lineEditPassphraseAgain = QtGui.QLineEdit(self.groupBoxDeterministic)
        self.lineEditPassphraseAgain.setEchoMode(QtGui.QLineEdit.Password)
        self.lineEditPassphraseAgain.setObjectName(_fromUtf8("lineEditPassphraseAgain"))
        self.gridLayout.addWidget(self.lineEditPassphraseAgain, 3, 0, 1, 4)
        self.lineEditPassphrase = QtGui.QLineEdit(self.groupBoxDeterministic)
        self.lineEditPassphrase.setInputMethodHints(QtCore.Qt.ImhHiddenText|QtCore.Qt.ImhNoAutoUppercase|QtCore.Qt.ImhNoPredictiveText)
        self.lineEditPassphrase.setEchoMode(QtGui.QLineEdit.Password)
        self.lineEditPassphrase.setObjectName(_fromUtf8("lineEditPassphrase"))
        self.gridLayout.addWidget(self.lineEditPassphrase, 1, 0, 1, 4)
        self.formLayout.setWidget(8, QtGui.QFormLayout.LabelRole, self.groupBoxDeterministic)
        self.groupBox = QtGui.QGroupBox(NewAddressDialog)
        self.groupBox.setObjectName(_fromUtf8("groupBox"))
        self.gridLayout_2 = QtGui.QGridLayout(self.groupBox)
        self.gridLayout_2.setObjectName(_fromUtf8("gridLayout_2"))
        self.label_2 = QtGui.QLabel(self.groupBox)
        self.label_2.setObjectName(_fromUtf8("label_2"))
        self.gridLayout_2.addWidget(self.label_2, 0, 0, 1, 2)
        self.newaddresslabel = QtGui.QLineEdit(self.groupBox)
        self.newaddresslabel.setObjectName(_fromUtf8("newaddresslabel"))
        self.gridLayout_2.addWidget(self.newaddresslabel, 1, 0, 1, 2)
        self.radioButtonMostAvailable = QtGui.QRadioButton(self.groupBox)
        self.radioButtonMostAvailable.setChecked(True)
        self.radioButtonMostAvailable.setObjectName(_fromUtf8("radioButtonMostAvailable"))
        self.gridLayout_2.addWidget(self.radioButtonMostAvailable, 2, 0, 1, 2)
        self.label_3 = QtGui.QLabel(self.groupBox)
        self.label_3.setAlignment(QtCore.Qt.AlignLeading|QtCore.Qt.AlignLeft|QtCore.Qt.AlignTop)
        self.label_3.setObjectName(_fromUtf8("label_3"))
        self.gridLayout_2.addWidget(self.label_3, 3, 1, 1, 1)
        self.radioButtonExisting = QtGui.QRadioButton(self.groupBox)
        self.radioButtonExisting.setChecked(False)
        self.radioButtonExisting.setObjectName(_fromUtf8("radioButtonExisting"))
        self.gridLayout_2.addWidget(self.radioButtonExisting, 4, 0, 1, 2)
        self.label_4 = QtGui.QLabel(self.groupBox)
        self.label_4.setAlignment(QtCore.Qt.AlignLeading|QtCore.Qt.AlignLeft|QtCore.Qt.AlignTop)
        self.label_4.setObjectName(_fromUtf8("label_4"))
        self.gridLayout_2.addWidget(self.label_4, 5, 1, 1, 1)
        spacerItem2 = QtGui.QSpacerItem(13, 20, QtGui.QSizePolicy.Expanding, QtGui.QSizePolicy.Minimum)
        self.gridLayout_2.addItem(spacerItem2, 6, 0, 1, 1)
        self.comboBoxExisting = QtGui.QComboBox(self.groupBox)
        self.comboBoxExisting.setEnabled(False)
        self.comboBoxExisting.setEditable(True)
        self.comboBoxExisting.setObjectName(_fromUtf8("comboBoxExisting"))
        self.gridLayout_2.addWidget(self.comboBoxExisting, 6, 1, 1, 1)
        self.formLayout.setWidget(7, QtGui.QFormLayout.LabelRole, self.groupBox)
        self.buttonBox = QtGui.QDialogButtonBox(NewAddressDialog)
        sizePolicy = QtGui.QSizePolicy(QtGui.QSizePolicy.MinimumExpanding, QtGui.QSizePolicy.MinimumExpanding)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.buttonBox.sizePolicy().hasHeightForWidth())
        self.buttonBox.setSizePolicy(sizePolicy)
        self.buttonBox.setMinimumSize(QtCore.QSize(160, 0))
        self.buttonBox.setOrientation(QtCore.Qt.Horizontal)
        self.buttonBox.setStandardButtons(QtGui.QDialogButtonBox.Cancel|QtGui.QDialogButtonBox.Ok)
        self.buttonBox.setObjectName(_fromUtf8("buttonBox"))
        self.formLayout.setWidget(10, QtGui.QFormLayout.SpanningRole, self.buttonBox)

        self.retranslateUi(NewAddressDialog)
        QtCore.QObject.connect(self.buttonBox, QtCore.SIGNAL(_fromUtf8("accepted()")), NewAddressDialog.accept)
        QtCore.QObject.connect(self.buttonBox, QtCore.SIGNAL(_fromUtf8("rejected()")), NewAddressDialog.reject)
        QtCore.QObject.connect(self.radioButtonExisting, QtCore.SIGNAL(_fromUtf8("toggled(bool)")), self.comboBoxExisting.setEnabled)
        QtCore.QObject.connect(self.radioButtonDeterministicAddress, QtCore.SIGNAL(_fromUtf8("toggled(bool)")), self.groupBoxDeterministic.setShown)
        QtCore.QObject.connect(self.radioButtonRandomAddress, QtCore.SIGNAL(_fromUtf8("toggled(bool)")), self.groupBox.setShown)
        QtCore.QMetaObject.connectSlotsByName(NewAddressDialog)
        NewAddressDialog.setTabOrder(self.radioButtonRandomAddress, self.radioButtonDeterministicAddress)
        NewAddressDialog.setTabOrder(self.radioButtonDeterministicAddress, self.newaddresslabel)
        NewAddressDialog.setTabOrder(self.newaddresslabel, self.radioButtonMostAvailable)
        NewAddressDialog.setTabOrder(self.radioButtonMostAvailable, self.radioButtonExisting)
        NewAddressDialog.setTabOrder(self.radioButtonExisting, self.comboBoxExisting)
        NewAddressDialog.setTabOrder(self.comboBoxExisting, self.lineEditPassphrase)
        NewAddressDialog.setTabOrder(self.lineEditPassphrase, self.lineEditPassphraseAgain)
        NewAddressDialog.setTabOrder(self.lineEditPassphraseAgain, self.spinBoxNumberOfAddressesToMake)
        NewAddressDialog.setTabOrder(self.spinBoxNumberOfAddressesToMake, self.checkBoxEighteenByteRipe)
        NewAddressDialog.setTabOrder(self.checkBoxEighteenByteRipe, self.buttonBox)

    def retranslateUi(self, NewAddressDialog):
        NewAddressDialog.setWindowTitle(_translate("NewAddressDialog", "Create new Address", None))
        self.label.setText(_translate("NewAddressDialog", "Here you may generate as many addresses as you like. Indeed, creating and abandoning addresses is encouraged. You may generate addresses by using either random numbers or by using a passphrase. If you use a passphrase, the address is called a \"deterministic\" address.\n"
"The \'Random Number\' option is selected by default but deterministic addresses have several pros and cons:", None))
        self.label_5.setText(_translate("NewAddressDialog", "<html><head/><body><p><span style=\" font-weight:600;\">Pros:<br/></span>You can recreate your addresses on any computer from memory. <br/>You need-not worry about backing up your keys.dat file as long as you can remember your passphrase. <br/><span style=\" font-weight:600;\">Cons:<br/></span>You must remember (or write down) your passphrase if you expect to be able to recreate your keys if they are lost. <br/>You must remember the address version number and the stream number along with your passphrase. <br/>If you choose a weak passphrase and someone on the Internet can brute-force it, they can read your messages and send messages as you.</p></body></html>", None))
        self.radioButtonRandomAddress.setText(_translate("NewAddressDialog", "Use a random number generator to make an address", None))
        self.radioButtonDeterministicAddress.setText(_translate("NewAddressDialog", "Use a passphrase to make addresses", None))
        self.checkBoxEighteenByteRipe.setText(_translate("NewAddressDialog", "Spend several minutes of extra computing time to make the address(es) 1 or 2 characters shorter", None))
        self.groupBoxDeterministic.setTitle(_translate("NewAddressDialog", "Make deterministic addresses", None))
        self.label_9.setText(_translate("NewAddressDialog", "Address version number: 4", None))
        self.label_8.setText(_translate("NewAddressDialog", "In addition to your passphrase, you must remember these numbers:", None))
        self.label_6.setText(_translate("NewAddressDialog", "Passphrase", None))
        self.label_11.setText(_translate("NewAddressDialog", "Number of addresses to make based on your passphrase:", None))
        self.label_10.setText(_translate("NewAddressDialog", "Stream number: 1", None))
        self.label_7.setText(_translate("NewAddressDialog", "Retype passphrase", None))
        self.groupBox.setTitle(_translate("NewAddressDialog", "Randomly generate address", None))
        self.label_2.setText(_translate("NewAddressDialog", "Label (not shown to anyone except you)", None))
        self.radioButtonMostAvailable.setText(_translate("NewAddressDialog", "Use the most available stream", None))
        self.label_3.setText(_translate("NewAddressDialog", " (best if this is the first of many addresses you will create)", None))
        self.radioButtonExisting.setText(_translate("NewAddressDialog", "Use the same stream as an existing address", None))
        self.label_4.setText(_translate("NewAddressDialog", "(saves you some bandwidth and processing power)", None))


########NEW FILE########
__FILENAME__ = newchandialog
# -*- coding: utf-8 -*-

# Form implementation generated from reading ui file 'newchandialog.ui'
#
# Created: Wed Aug  7 16:51:29 2013
#      by: PyQt4 UI code generator 4.10
#
# WARNING! All changes made in this file will be lost!

from PyQt4 import QtCore, QtGui

try:
    _fromUtf8 = QtCore.QString.fromUtf8
except AttributeError:
    def _fromUtf8(s):
        return s

try:
    _encoding = QtGui.QApplication.UnicodeUTF8
    def _translate(context, text, disambig):
        return QtGui.QApplication.translate(context, text, disambig, _encoding)
except AttributeError:
    def _translate(context, text, disambig):
        return QtGui.QApplication.translate(context, text, disambig)

class Ui_newChanDialog(object):
    def setupUi(self, newChanDialog):
        newChanDialog.setObjectName(_fromUtf8("newChanDialog"))
        newChanDialog.resize(553, 422)
        newChanDialog.setMinimumSize(QtCore.QSize(0, 0))
        self.formLayout = QtGui.QFormLayout(newChanDialog)
        self.formLayout.setObjectName(_fromUtf8("formLayout"))
        self.radioButtonCreateChan = QtGui.QRadioButton(newChanDialog)
        self.radioButtonCreateChan.setObjectName(_fromUtf8("radioButtonCreateChan"))
        self.formLayout.setWidget(0, QtGui.QFormLayout.LabelRole, self.radioButtonCreateChan)
        self.radioButtonJoinChan = QtGui.QRadioButton(newChanDialog)
        self.radioButtonJoinChan.setChecked(True)
        self.radioButtonJoinChan.setObjectName(_fromUtf8("radioButtonJoinChan"))
        self.formLayout.setWidget(1, QtGui.QFormLayout.LabelRole, self.radioButtonJoinChan)
        self.groupBoxCreateChan = QtGui.QGroupBox(newChanDialog)
        self.groupBoxCreateChan.setObjectName(_fromUtf8("groupBoxCreateChan"))
        self.gridLayout = QtGui.QGridLayout(self.groupBoxCreateChan)
        self.gridLayout.setObjectName(_fromUtf8("gridLayout"))
        self.label_4 = QtGui.QLabel(self.groupBoxCreateChan)
        self.label_4.setWordWrap(True)
        self.label_4.setObjectName(_fromUtf8("label_4"))
        self.gridLayout.addWidget(self.label_4, 0, 0, 1, 1)
        self.label_5 = QtGui.QLabel(self.groupBoxCreateChan)
        self.label_5.setObjectName(_fromUtf8("label_5"))
        self.gridLayout.addWidget(self.label_5, 1, 0, 1, 1)
        self.lineEditChanNameCreate = QtGui.QLineEdit(self.groupBoxCreateChan)
        self.lineEditChanNameCreate.setObjectName(_fromUtf8("lineEditChanNameCreate"))
        self.gridLayout.addWidget(self.lineEditChanNameCreate, 2, 0, 1, 1)
        self.formLayout.setWidget(2, QtGui.QFormLayout.SpanningRole, self.groupBoxCreateChan)
        self.groupBoxJoinChan = QtGui.QGroupBox(newChanDialog)
        self.groupBoxJoinChan.setObjectName(_fromUtf8("groupBoxJoinChan"))
        self.gridLayout_2 = QtGui.QGridLayout(self.groupBoxJoinChan)
        self.gridLayout_2.setObjectName(_fromUtf8("gridLayout_2"))
        self.label = QtGui.QLabel(self.groupBoxJoinChan)
        self.label.setWordWrap(True)
        self.label.setObjectName(_fromUtf8("label"))
        self.gridLayout_2.addWidget(self.label, 0, 0, 1, 1)
        self.label_2 = QtGui.QLabel(self.groupBoxJoinChan)
        self.label_2.setObjectName(_fromUtf8("label_2"))
        self.gridLayout_2.addWidget(self.label_2, 1, 0, 1, 1)
        self.lineEditChanNameJoin = QtGui.QLineEdit(self.groupBoxJoinChan)
        self.lineEditChanNameJoin.setObjectName(_fromUtf8("lineEditChanNameJoin"))
        self.gridLayout_2.addWidget(self.lineEditChanNameJoin, 2, 0, 1, 1)
        self.label_3 = QtGui.QLabel(self.groupBoxJoinChan)
        self.label_3.setObjectName(_fromUtf8("label_3"))
        self.gridLayout_2.addWidget(self.label_3, 3, 0, 1, 1)
        self.lineEditChanBitmessageAddress = QtGui.QLineEdit(self.groupBoxJoinChan)
        self.lineEditChanBitmessageAddress.setObjectName(_fromUtf8("lineEditChanBitmessageAddress"))
        self.gridLayout_2.addWidget(self.lineEditChanBitmessageAddress, 4, 0, 1, 1)
        self.formLayout.setWidget(3, QtGui.QFormLayout.SpanningRole, self.groupBoxJoinChan)
        spacerItem = QtGui.QSpacerItem(389, 2, QtGui.QSizePolicy.Minimum, QtGui.QSizePolicy.Expanding)
        self.formLayout.setItem(4, QtGui.QFormLayout.FieldRole, spacerItem)
        self.buttonBox = QtGui.QDialogButtonBox(newChanDialog)
        self.buttonBox.setOrientation(QtCore.Qt.Horizontal)
        self.buttonBox.setStandardButtons(QtGui.QDialogButtonBox.Cancel|QtGui.QDialogButtonBox.Ok)
        self.buttonBox.setObjectName(_fromUtf8("buttonBox"))
        self.formLayout.setWidget(5, QtGui.QFormLayout.FieldRole, self.buttonBox)

        self.retranslateUi(newChanDialog)
        QtCore.QObject.connect(self.buttonBox, QtCore.SIGNAL(_fromUtf8("accepted()")), newChanDialog.accept)
        QtCore.QObject.connect(self.buttonBox, QtCore.SIGNAL(_fromUtf8("rejected()")), newChanDialog.reject)
        QtCore.QObject.connect(self.radioButtonJoinChan, QtCore.SIGNAL(_fromUtf8("toggled(bool)")), self.groupBoxJoinChan.setShown)
        QtCore.QObject.connect(self.radioButtonCreateChan, QtCore.SIGNAL(_fromUtf8("toggled(bool)")), self.groupBoxCreateChan.setShown)
        QtCore.QMetaObject.connectSlotsByName(newChanDialog)
        newChanDialog.setTabOrder(self.radioButtonJoinChan, self.radioButtonCreateChan)
        newChanDialog.setTabOrder(self.radioButtonCreateChan, self.lineEditChanNameCreate)
        newChanDialog.setTabOrder(self.lineEditChanNameCreate, self.lineEditChanNameJoin)
        newChanDialog.setTabOrder(self.lineEditChanNameJoin, self.lineEditChanBitmessageAddress)
        newChanDialog.setTabOrder(self.lineEditChanBitmessageAddress, self.buttonBox)

    def retranslateUi(self, newChanDialog):
        newChanDialog.setWindowTitle(_translate("newChanDialog", "Dialog", None))
        self.radioButtonCreateChan.setText(_translate("newChanDialog", "Create a new chan", None))
        self.radioButtonJoinChan.setText(_translate("newChanDialog", "Join a chan", None))
        self.groupBoxCreateChan.setTitle(_translate("newChanDialog", "Create a chan", None))
        self.label_4.setText(_translate("newChanDialog", "<html><head/><body><p>Enter a name for your chan. If you choose a sufficiently complex chan name (like a strong and unique passphrase) and none of your friends share it publicly then the chan will be secure and private. If you and someone else both create a chan with the same chan name then it is currently very likely that they will be the same chan.</p></body></html>", None))
        self.label_5.setText(_translate("newChanDialog", "Chan name:", None))
        self.groupBoxJoinChan.setTitle(_translate("newChanDialog", "Join a chan", None))
        self.label.setText(_translate("newChanDialog", "<html><head/><body><p>A chan exists when a group of people share the same decryption keys. The keys and bitmessage address used by a chan are generated from a human-friendly word or phrase (the chan name). To send a message to everyone in the chan, send a normal person-to-person message to the chan address.</p><p>Chans are experimental and completely unmoderatable.</p></body></html>", None))
        self.label_2.setText(_translate("newChanDialog", "Chan name:", None))
        self.label_3.setText(_translate("newChanDialog", "Chan bitmessage address:", None))


########NEW FILE########
__FILENAME__ = newsubscriptiondialog
# -*- coding: utf-8 -*-

# Form implementation generated from reading ui file 'newsubscriptiondialog.ui'
#
# Created: Sat Nov 30 21:53:38 2013
#      by: PyQt4 UI code generator 4.10.3
#
# WARNING! All changes made in this file will be lost!

from PyQt4 import QtCore, QtGui

try:
    _fromUtf8 = QtCore.QString.fromUtf8
except AttributeError:
    def _fromUtf8(s):
        return s

try:
    _encoding = QtGui.QApplication.UnicodeUTF8
    def _translate(context, text, disambig):
        return QtGui.QApplication.translate(context, text, disambig, _encoding)
except AttributeError:
    def _translate(context, text, disambig):
        return QtGui.QApplication.translate(context, text, disambig)

class Ui_NewSubscriptionDialog(object):
    def setupUi(self, NewSubscriptionDialog):
        NewSubscriptionDialog.setObjectName(_fromUtf8("NewSubscriptionDialog"))
        NewSubscriptionDialog.resize(368, 173)
        self.formLayout = QtGui.QFormLayout(NewSubscriptionDialog)
        self.formLayout.setObjectName(_fromUtf8("formLayout"))
        self.label_2 = QtGui.QLabel(NewSubscriptionDialog)
        self.label_2.setObjectName(_fromUtf8("label_2"))
        self.formLayout.setWidget(0, QtGui.QFormLayout.LabelRole, self.label_2)
        self.newsubscriptionlabel = QtGui.QLineEdit(NewSubscriptionDialog)
        self.newsubscriptionlabel.setObjectName(_fromUtf8("newsubscriptionlabel"))
        self.formLayout.setWidget(1, QtGui.QFormLayout.SpanningRole, self.newsubscriptionlabel)
        self.label = QtGui.QLabel(NewSubscriptionDialog)
        self.label.setObjectName(_fromUtf8("label"))
        self.formLayout.setWidget(2, QtGui.QFormLayout.LabelRole, self.label)
        self.lineEditSubscriptionAddress = QtGui.QLineEdit(NewSubscriptionDialog)
        self.lineEditSubscriptionAddress.setObjectName(_fromUtf8("lineEditSubscriptionAddress"))
        self.formLayout.setWidget(3, QtGui.QFormLayout.SpanningRole, self.lineEditSubscriptionAddress)
        self.labelAddressCheck = QtGui.QLabel(NewSubscriptionDialog)
        self.labelAddressCheck.setText(_fromUtf8(""))
        self.labelAddressCheck.setWordWrap(True)
        self.labelAddressCheck.setObjectName(_fromUtf8("labelAddressCheck"))
        self.formLayout.setWidget(4, QtGui.QFormLayout.SpanningRole, self.labelAddressCheck)
        self.checkBoxDisplayMessagesAlreadyInInventory = QtGui.QCheckBox(NewSubscriptionDialog)
        self.checkBoxDisplayMessagesAlreadyInInventory.setEnabled(False)
        self.checkBoxDisplayMessagesAlreadyInInventory.setObjectName(_fromUtf8("checkBoxDisplayMessagesAlreadyInInventory"))
        self.formLayout.setWidget(5, QtGui.QFormLayout.SpanningRole, self.checkBoxDisplayMessagesAlreadyInInventory)
        self.buttonBox = QtGui.QDialogButtonBox(NewSubscriptionDialog)
        self.buttonBox.setOrientation(QtCore.Qt.Horizontal)
        self.buttonBox.setStandardButtons(QtGui.QDialogButtonBox.Cancel|QtGui.QDialogButtonBox.Ok)
        self.buttonBox.setObjectName(_fromUtf8("buttonBox"))
        self.formLayout.setWidget(6, QtGui.QFormLayout.FieldRole, self.buttonBox)

        self.retranslateUi(NewSubscriptionDialog)
        QtCore.QObject.connect(self.buttonBox, QtCore.SIGNAL(_fromUtf8("accepted()")), NewSubscriptionDialog.accept)
        QtCore.QObject.connect(self.buttonBox, QtCore.SIGNAL(_fromUtf8("rejected()")), NewSubscriptionDialog.reject)
        QtCore.QMetaObject.connectSlotsByName(NewSubscriptionDialog)

    def retranslateUi(self, NewSubscriptionDialog):
        NewSubscriptionDialog.setWindowTitle(_translate("NewSubscriptionDialog", "Add new entry", None))
        self.label_2.setText(_translate("NewSubscriptionDialog", "Label", None))
        self.label.setText(_translate("NewSubscriptionDialog", "Address", None))
        self.checkBoxDisplayMessagesAlreadyInInventory.setText(_translate("NewSubscriptionDialog", "CheckBox", None))


########NEW FILE########
__FILENAME__ = regenerateaddresses
# -*- coding: utf-8 -*-

# Form implementation generated from reading ui file 'regenerateaddresses.ui'
#
# Created: Sun Sep 15 23:50:23 2013
#      by: PyQt4 UI code generator 4.10.2
#
# WARNING! All changes made in this file will be lost!

from PyQt4 import QtCore, QtGui

try:
    _fromUtf8 = QtCore.QString.fromUtf8
except AttributeError:
    def _fromUtf8(s):
        return s

try:
    _encoding = QtGui.QApplication.UnicodeUTF8
    def _translate(context, text, disambig):
        return QtGui.QApplication.translate(context, text, disambig, _encoding)
except AttributeError:
    def _translate(context, text, disambig):
        return QtGui.QApplication.translate(context, text, disambig)

class Ui_regenerateAddressesDialog(object):
    def setupUi(self, regenerateAddressesDialog):
        regenerateAddressesDialog.setObjectName(_fromUtf8("regenerateAddressesDialog"))
        regenerateAddressesDialog.resize(532, 332)
        self.gridLayout_2 = QtGui.QGridLayout(regenerateAddressesDialog)
        self.gridLayout_2.setObjectName(_fromUtf8("gridLayout_2"))
        self.buttonBox = QtGui.QDialogButtonBox(regenerateAddressesDialog)
        self.buttonBox.setOrientation(QtCore.Qt.Horizontal)
        self.buttonBox.setStandardButtons(QtGui.QDialogButtonBox.Cancel|QtGui.QDialogButtonBox.Ok)
        self.buttonBox.setObjectName(_fromUtf8("buttonBox"))
        self.gridLayout_2.addWidget(self.buttonBox, 1, 0, 1, 1)
        self.groupBox = QtGui.QGroupBox(regenerateAddressesDialog)
        self.groupBox.setObjectName(_fromUtf8("groupBox"))
        self.gridLayout = QtGui.QGridLayout(self.groupBox)
        self.gridLayout.setObjectName(_fromUtf8("gridLayout"))
        self.label_6 = QtGui.QLabel(self.groupBox)
        self.label_6.setObjectName(_fromUtf8("label_6"))
        self.gridLayout.addWidget(self.label_6, 1, 0, 1, 1)
        self.lineEditPassphrase = QtGui.QLineEdit(self.groupBox)
        self.lineEditPassphrase.setInputMethodHints(QtCore.Qt.ImhHiddenText|QtCore.Qt.ImhNoAutoUppercase|QtCore.Qt.ImhNoPredictiveText)
        self.lineEditPassphrase.setEchoMode(QtGui.QLineEdit.Password)
        self.lineEditPassphrase.setObjectName(_fromUtf8("lineEditPassphrase"))
        self.gridLayout.addWidget(self.lineEditPassphrase, 2, 0, 1, 5)
        self.label_11 = QtGui.QLabel(self.groupBox)
        self.label_11.setObjectName(_fromUtf8("label_11"))
        self.gridLayout.addWidget(self.label_11, 3, 0, 1, 3)
        self.spinBoxNumberOfAddressesToMake = QtGui.QSpinBox(self.groupBox)
        sizePolicy = QtGui.QSizePolicy(QtGui.QSizePolicy.Fixed, QtGui.QSizePolicy.Fixed)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.spinBoxNumberOfAddressesToMake.sizePolicy().hasHeightForWidth())
        self.spinBoxNumberOfAddressesToMake.setSizePolicy(sizePolicy)
        self.spinBoxNumberOfAddressesToMake.setMinimum(1)
        self.spinBoxNumberOfAddressesToMake.setProperty("value", 8)
        self.spinBoxNumberOfAddressesToMake.setObjectName(_fromUtf8("spinBoxNumberOfAddressesToMake"))
        self.gridLayout.addWidget(self.spinBoxNumberOfAddressesToMake, 3, 3, 1, 1)
        spacerItem = QtGui.QSpacerItem(132, 20, QtGui.QSizePolicy.Expanding, QtGui.QSizePolicy.Minimum)
        self.gridLayout.addItem(spacerItem, 3, 4, 1, 1)
        self.label_2 = QtGui.QLabel(self.groupBox)
        self.label_2.setObjectName(_fromUtf8("label_2"))
        self.gridLayout.addWidget(self.label_2, 4, 0, 1, 1)
        self.lineEditAddressVersionNumber = QtGui.QLineEdit(self.groupBox)
        self.lineEditAddressVersionNumber.setEnabled(True)
        sizePolicy = QtGui.QSizePolicy(QtGui.QSizePolicy.Fixed, QtGui.QSizePolicy.Fixed)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.lineEditAddressVersionNumber.sizePolicy().hasHeightForWidth())
        self.lineEditAddressVersionNumber.setSizePolicy(sizePolicy)
        self.lineEditAddressVersionNumber.setMaximumSize(QtCore.QSize(31, 16777215))
        self.lineEditAddressVersionNumber.setText(_fromUtf8(""))
        self.lineEditAddressVersionNumber.setObjectName(_fromUtf8("lineEditAddressVersionNumber"))
        self.gridLayout.addWidget(self.lineEditAddressVersionNumber, 4, 1, 1, 1)
        spacerItem1 = QtGui.QSpacerItem(40, 20, QtGui.QSizePolicy.Expanding, QtGui.QSizePolicy.Minimum)
        self.gridLayout.addItem(spacerItem1, 4, 2, 1, 1)
        self.label_3 = QtGui.QLabel(self.groupBox)
        self.label_3.setObjectName(_fromUtf8("label_3"))
        self.gridLayout.addWidget(self.label_3, 5, 0, 1, 1)
        self.lineEditStreamNumber = QtGui.QLineEdit(self.groupBox)
        self.lineEditStreamNumber.setEnabled(False)
        sizePolicy = QtGui.QSizePolicy(QtGui.QSizePolicy.Ignored, QtGui.QSizePolicy.Fixed)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.lineEditStreamNumber.sizePolicy().hasHeightForWidth())
        self.lineEditStreamNumber.setSizePolicy(sizePolicy)
        self.lineEditStreamNumber.setMaximumSize(QtCore.QSize(31, 16777215))
        self.lineEditStreamNumber.setObjectName(_fromUtf8("lineEditStreamNumber"))
        self.gridLayout.addWidget(self.lineEditStreamNumber, 5, 1, 1, 1)
        spacerItem2 = QtGui.QSpacerItem(325, 20, QtGui.QSizePolicy.Expanding, QtGui.QSizePolicy.Minimum)
        self.gridLayout.addItem(spacerItem2, 5, 2, 1, 3)
        self.checkBoxEighteenByteRipe = QtGui.QCheckBox(self.groupBox)
        self.checkBoxEighteenByteRipe.setObjectName(_fromUtf8("checkBoxEighteenByteRipe"))
        self.gridLayout.addWidget(self.checkBoxEighteenByteRipe, 6, 0, 1, 5)
        self.label_4 = QtGui.QLabel(self.groupBox)
        self.label_4.setWordWrap(True)
        self.label_4.setObjectName(_fromUtf8("label_4"))
        self.gridLayout.addWidget(self.label_4, 7, 0, 1, 5)
        self.label = QtGui.QLabel(self.groupBox)
        self.label.setWordWrap(True)
        self.label.setObjectName(_fromUtf8("label"))
        self.gridLayout.addWidget(self.label, 0, 0, 1, 5)
        self.gridLayout_2.addWidget(self.groupBox, 0, 0, 1, 1)

        self.retranslateUi(regenerateAddressesDialog)
        QtCore.QObject.connect(self.buttonBox, QtCore.SIGNAL(_fromUtf8("accepted()")), regenerateAddressesDialog.accept)
        QtCore.QObject.connect(self.buttonBox, QtCore.SIGNAL(_fromUtf8("rejected()")), regenerateAddressesDialog.reject)
        QtCore.QMetaObject.connectSlotsByName(regenerateAddressesDialog)

    def retranslateUi(self, regenerateAddressesDialog):
        regenerateAddressesDialog.setWindowTitle(_translate("regenerateAddressesDialog", "Regenerate Existing Addresses", None))
        self.groupBox.setTitle(_translate("regenerateAddressesDialog", "Regenerate existing addresses", None))
        self.label_6.setText(_translate("regenerateAddressesDialog", "Passphrase", None))
        self.label_11.setText(_translate("regenerateAddressesDialog", "Number of addresses to make based on your passphrase:", None))
        self.label_2.setText(_translate("regenerateAddressesDialog", "Address version number:", None))
        self.label_3.setText(_translate("regenerateAddressesDialog", "Stream number:", None))
        self.lineEditStreamNumber.setText(_translate("regenerateAddressesDialog", "1", None))
        self.checkBoxEighteenByteRipe.setText(_translate("regenerateAddressesDialog", "Spend several minutes of extra computing time to make the address(es) 1 or 2 characters shorter", None))
        self.label_4.setText(_translate("regenerateAddressesDialog", "You must check (or not check) this box just like you did (or didn\'t) when you made your addresses the first time.", None))
        self.label.setText(_translate("regenerateAddressesDialog", "If you have previously made deterministic addresses but lost them due to an accident (like hard drive failure), you can regenerate them here. If you used the random number generator to make your addresses then this form will be of no use to you.", None))


########NEW FILE########
__FILENAME__ = settings
# -*- coding: utf-8 -*-

# Form implementation generated from reading ui file 'settings.ui'
#
# Created: Mon May 19 15:54:27 2014
#      by: PyQt4 UI code generator 4.10.3
#
# WARNING! All changes made in this file will be lost!

from PyQt4 import QtCore, QtGui

try:
    _fromUtf8 = QtCore.QString.fromUtf8
except AttributeError:
    def _fromUtf8(s):
        return s

try:
    _encoding = QtGui.QApplication.UnicodeUTF8
    def _translate(context, text, disambig):
        return QtGui.QApplication.translate(context, text, disambig, _encoding)
except AttributeError:
    def _translate(context, text, disambig):
        return QtGui.QApplication.translate(context, text, disambig)

class Ui_settingsDialog(object):
    def setupUi(self, settingsDialog):
        settingsDialog.setObjectName(_fromUtf8("settingsDialog"))
        settingsDialog.resize(521, 413)
        self.gridLayout = QtGui.QGridLayout(settingsDialog)
        self.gridLayout.setObjectName(_fromUtf8("gridLayout"))
        self.buttonBox = QtGui.QDialogButtonBox(settingsDialog)
        self.buttonBox.setOrientation(QtCore.Qt.Horizontal)
        self.buttonBox.setStandardButtons(QtGui.QDialogButtonBox.Cancel|QtGui.QDialogButtonBox.Ok)
        self.buttonBox.setObjectName(_fromUtf8("buttonBox"))
        self.gridLayout.addWidget(self.buttonBox, 1, 0, 1, 1)
        self.tabWidgetSettings = QtGui.QTabWidget(settingsDialog)
        self.tabWidgetSettings.setObjectName(_fromUtf8("tabWidgetSettings"))
        self.tabUserInterface = QtGui.QWidget()
        self.tabUserInterface.setEnabled(True)
        self.tabUserInterface.setObjectName(_fromUtf8("tabUserInterface"))
        self.formLayout = QtGui.QFormLayout(self.tabUserInterface)
        self.formLayout.setObjectName(_fromUtf8("formLayout"))
        self.checkBoxStartOnLogon = QtGui.QCheckBox(self.tabUserInterface)
        self.checkBoxStartOnLogon.setObjectName(_fromUtf8("checkBoxStartOnLogon"))
        self.formLayout.setWidget(0, QtGui.QFormLayout.LabelRole, self.checkBoxStartOnLogon)
        self.checkBoxStartInTray = QtGui.QCheckBox(self.tabUserInterface)
        self.checkBoxStartInTray.setObjectName(_fromUtf8("checkBoxStartInTray"))
        self.formLayout.setWidget(1, QtGui.QFormLayout.SpanningRole, self.checkBoxStartInTray)
        self.checkBoxMinimizeToTray = QtGui.QCheckBox(self.tabUserInterface)
        self.checkBoxMinimizeToTray.setChecked(True)
        self.checkBoxMinimizeToTray.setObjectName(_fromUtf8("checkBoxMinimizeToTray"))
        self.formLayout.setWidget(2, QtGui.QFormLayout.LabelRole, self.checkBoxMinimizeToTray)
        self.checkBoxShowTrayNotifications = QtGui.QCheckBox(self.tabUserInterface)
        self.checkBoxShowTrayNotifications.setObjectName(_fromUtf8("checkBoxShowTrayNotifications"))
        self.formLayout.setWidget(3, QtGui.QFormLayout.LabelRole, self.checkBoxShowTrayNotifications)
        self.checkBoxPortableMode = QtGui.QCheckBox(self.tabUserInterface)
        self.checkBoxPortableMode.setObjectName(_fromUtf8("checkBoxPortableMode"))
        self.formLayout.setWidget(4, QtGui.QFormLayout.LabelRole, self.checkBoxPortableMode)
        self.PortableModeDescription = QtGui.QLabel(self.tabUserInterface)
        sizePolicy = QtGui.QSizePolicy(QtGui.QSizePolicy.Minimum, QtGui.QSizePolicy.Fixed)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.PortableModeDescription.sizePolicy().hasHeightForWidth())
        self.PortableModeDescription.setSizePolicy(sizePolicy)
        self.PortableModeDescription.setWordWrap(True)
        self.PortableModeDescription.setObjectName(_fromUtf8("PortableModeDescription"))
        self.formLayout.setWidget(5, QtGui.QFormLayout.SpanningRole, self.PortableModeDescription)
        self.checkBoxWillinglySendToMobile = QtGui.QCheckBox(self.tabUserInterface)
        self.checkBoxWillinglySendToMobile.setObjectName(_fromUtf8("checkBoxWillinglySendToMobile"))
        self.formLayout.setWidget(6, QtGui.QFormLayout.SpanningRole, self.checkBoxWillinglySendToMobile)
        self.checkBoxUseIdenticons = QtGui.QCheckBox(self.tabUserInterface)
        self.checkBoxUseIdenticons.setObjectName(_fromUtf8("checkBoxUseIdenticons"))
        self.formLayout.setWidget(7, QtGui.QFormLayout.LabelRole, self.checkBoxUseIdenticons)
        self.checkBoxReplyBelow = QtGui.QCheckBox(self.tabUserInterface)
        self.checkBoxReplyBelow.setObjectName(_fromUtf8("checkBoxReplyBelow"))
        self.formLayout.setWidget(8, QtGui.QFormLayout.LabelRole, self.checkBoxReplyBelow)
        self.groupBox = QtGui.QGroupBox(self.tabUserInterface)
        self.groupBox.setObjectName(_fromUtf8("groupBox"))
        self.formLayout_2 = QtGui.QFormLayout(self.groupBox)
        self.formLayout_2.setObjectName(_fromUtf8("formLayout_2"))
        self.languageComboBox = QtGui.QComboBox(self.groupBox)
        self.languageComboBox.setMinimumSize(QtCore.QSize(100, 0))
        self.languageComboBox.setObjectName(_fromUtf8("languageComboBox"))
        self.languageComboBox.addItem(_fromUtf8(""))
        self.languageComboBox.addItem(_fromUtf8(""))
        self.languageComboBox.setItemText(1, _fromUtf8("English"))
        self.languageComboBox.addItem(_fromUtf8(""))
        self.languageComboBox.setItemText(2, _fromUtf8("Esperanto"))
        self.languageComboBox.addItem(_fromUtf8(""))
        self.languageComboBox.setItemText(3, _fromUtf8("Français"))
        self.languageComboBox.addItem(_fromUtf8(""))
        self.languageComboBox.setItemText(4, _fromUtf8("Deutsch"))
        self.languageComboBox.addItem(_fromUtf8(""))
        self.languageComboBox.setItemText(5, _fromUtf8("Españl"))
        self.languageComboBox.addItem(_fromUtf8(""))
        self.languageComboBox.setItemText(6, _fromUtf8("русский"))
        self.languageComboBox.addItem(_fromUtf8(""))
        self.languageComboBox.setItemText(7, _fromUtf8("Norsk"))
        self.languageComboBox.addItem(_fromUtf8(""))
        self.languageComboBox.setItemText(8, _fromUtf8("العربية"))
        self.languageComboBox.addItem(_fromUtf8(""))
        self.languageComboBox.setItemText(9, _fromUtf8("简体中文"))
        self.languageComboBox.addItem(_fromUtf8(""))
        self.languageComboBox.setItemText(10, _fromUtf8("日本語"))
        self.languageComboBox.addItem(_fromUtf8(""))
        self.languageComboBox.setItemText(11, _fromUtf8("Nederlands"))
        self.languageComboBox.addItem(_fromUtf8(""))
        self.languageComboBox.addItem(_fromUtf8(""))
        self.formLayout_2.setWidget(0, QtGui.QFormLayout.LabelRole, self.languageComboBox)
        self.formLayout.setWidget(9, QtGui.QFormLayout.FieldRole, self.groupBox)
        self.tabWidgetSettings.addTab(self.tabUserInterface, _fromUtf8(""))
        self.tabNetworkSettings = QtGui.QWidget()
        self.tabNetworkSettings.setObjectName(_fromUtf8("tabNetworkSettings"))
        self.gridLayout_4 = QtGui.QGridLayout(self.tabNetworkSettings)
        self.gridLayout_4.setObjectName(_fromUtf8("gridLayout_4"))
        self.groupBox1 = QtGui.QGroupBox(self.tabNetworkSettings)
        self.groupBox1.setObjectName(_fromUtf8("groupBox1"))
        self.gridLayout_3 = QtGui.QGridLayout(self.groupBox1)
        self.gridLayout_3.setObjectName(_fromUtf8("gridLayout_3"))
        spacerItem = QtGui.QSpacerItem(125, 20, QtGui.QSizePolicy.Expanding, QtGui.QSizePolicy.Minimum)
        self.gridLayout_3.addItem(spacerItem, 0, 0, 1, 1)
        self.label = QtGui.QLabel(self.groupBox1)
        self.label.setObjectName(_fromUtf8("label"))
        self.gridLayout_3.addWidget(self.label, 0, 1, 1, 1)
        self.lineEditTCPPort = QtGui.QLineEdit(self.groupBox1)
        self.lineEditTCPPort.setMaximumSize(QtCore.QSize(70, 16777215))
        self.lineEditTCPPort.setObjectName(_fromUtf8("lineEditTCPPort"))
        self.gridLayout_3.addWidget(self.lineEditTCPPort, 0, 2, 1, 1)
        self.gridLayout_4.addWidget(self.groupBox1, 0, 0, 1, 1)
        self.groupBox_2 = QtGui.QGroupBox(self.tabNetworkSettings)
        self.groupBox_2.setObjectName(_fromUtf8("groupBox_2"))
        self.gridLayout_2 = QtGui.QGridLayout(self.groupBox_2)
        self.gridLayout_2.setObjectName(_fromUtf8("gridLayout_2"))
        self.label_2 = QtGui.QLabel(self.groupBox_2)
        self.label_2.setObjectName(_fromUtf8("label_2"))
        self.gridLayout_2.addWidget(self.label_2, 0, 0, 1, 1)
        self.label_3 = QtGui.QLabel(self.groupBox_2)
        self.label_3.setObjectName(_fromUtf8("label_3"))
        self.gridLayout_2.addWidget(self.label_3, 1, 1, 1, 1)
        self.lineEditSocksHostname = QtGui.QLineEdit(self.groupBox_2)
        self.lineEditSocksHostname.setObjectName(_fromUtf8("lineEditSocksHostname"))
        self.gridLayout_2.addWidget(self.lineEditSocksHostname, 1, 2, 1, 2)
        self.label_4 = QtGui.QLabel(self.groupBox_2)
        self.label_4.setObjectName(_fromUtf8("label_4"))
        self.gridLayout_2.addWidget(self.label_4, 1, 4, 1, 1)
        self.lineEditSocksPort = QtGui.QLineEdit(self.groupBox_2)
        self.lineEditSocksPort.setObjectName(_fromUtf8("lineEditSocksPort"))
        self.gridLayout_2.addWidget(self.lineEditSocksPort, 1, 5, 1, 1)
        self.checkBoxAuthentication = QtGui.QCheckBox(self.groupBox_2)
        self.checkBoxAuthentication.setObjectName(_fromUtf8("checkBoxAuthentication"))
        self.gridLayout_2.addWidget(self.checkBoxAuthentication, 2, 1, 1, 1)
        self.label_5 = QtGui.QLabel(self.groupBox_2)
        self.label_5.setObjectName(_fromUtf8("label_5"))
        self.gridLayout_2.addWidget(self.label_5, 2, 2, 1, 1)
        self.lineEditSocksUsername = QtGui.QLineEdit(self.groupBox_2)
        self.lineEditSocksUsername.setEnabled(False)
        self.lineEditSocksUsername.setObjectName(_fromUtf8("lineEditSocksUsername"))
        self.gridLayout_2.addWidget(self.lineEditSocksUsername, 2, 3, 1, 1)
        self.label_6 = QtGui.QLabel(self.groupBox_2)
        self.label_6.setObjectName(_fromUtf8("label_6"))
        self.gridLayout_2.addWidget(self.label_6, 2, 4, 1, 1)
        self.lineEditSocksPassword = QtGui.QLineEdit(self.groupBox_2)
        self.lineEditSocksPassword.setEnabled(False)
        self.lineEditSocksPassword.setInputMethodHints(QtCore.Qt.ImhHiddenText|QtCore.Qt.ImhNoAutoUppercase|QtCore.Qt.ImhNoPredictiveText)
        self.lineEditSocksPassword.setEchoMode(QtGui.QLineEdit.Password)
        self.lineEditSocksPassword.setObjectName(_fromUtf8("lineEditSocksPassword"))
        self.gridLayout_2.addWidget(self.lineEditSocksPassword, 2, 5, 1, 1)
        self.checkBoxSocksListen = QtGui.QCheckBox(self.groupBox_2)
        self.checkBoxSocksListen.setObjectName(_fromUtf8("checkBoxSocksListen"))
        self.gridLayout_2.addWidget(self.checkBoxSocksListen, 3, 1, 1, 4)
        self.comboBoxProxyType = QtGui.QComboBox(self.groupBox_2)
        self.comboBoxProxyType.setObjectName(_fromUtf8("comboBoxProxyType"))
        self.comboBoxProxyType.addItem(_fromUtf8(""))
        self.comboBoxProxyType.addItem(_fromUtf8(""))
        self.comboBoxProxyType.addItem(_fromUtf8(""))
        self.gridLayout_2.addWidget(self.comboBoxProxyType, 0, 1, 1, 1)
        self.gridLayout_4.addWidget(self.groupBox_2, 1, 0, 1, 1)
        spacerItem1 = QtGui.QSpacerItem(20, 70, QtGui.QSizePolicy.Minimum, QtGui.QSizePolicy.Expanding)
        self.gridLayout_4.addItem(spacerItem1, 2, 0, 1, 1)
        self.tabWidgetSettings.addTab(self.tabNetworkSettings, _fromUtf8(""))
        self.tabDemandedDifficulty = QtGui.QWidget()
        self.tabDemandedDifficulty.setObjectName(_fromUtf8("tabDemandedDifficulty"))
        self.gridLayout_6 = QtGui.QGridLayout(self.tabDemandedDifficulty)
        self.gridLayout_6.setObjectName(_fromUtf8("gridLayout_6"))
        self.label_9 = QtGui.QLabel(self.tabDemandedDifficulty)
        self.label_9.setAlignment(QtCore.Qt.AlignRight|QtCore.Qt.AlignTrailing|QtCore.Qt.AlignVCenter)
        self.label_9.setObjectName(_fromUtf8("label_9"))
        self.gridLayout_6.addWidget(self.label_9, 1, 1, 1, 1)
        self.label_10 = QtGui.QLabel(self.tabDemandedDifficulty)
        self.label_10.setWordWrap(True)
        self.label_10.setObjectName(_fromUtf8("label_10"))
        self.gridLayout_6.addWidget(self.label_10, 2, 0, 1, 3)
        self.label_11 = QtGui.QLabel(self.tabDemandedDifficulty)
        self.label_11.setAlignment(QtCore.Qt.AlignRight|QtCore.Qt.AlignTrailing|QtCore.Qt.AlignVCenter)
        self.label_11.setObjectName(_fromUtf8("label_11"))
        self.gridLayout_6.addWidget(self.label_11, 3, 1, 1, 1)
        self.label_8 = QtGui.QLabel(self.tabDemandedDifficulty)
        self.label_8.setWordWrap(True)
        self.label_8.setObjectName(_fromUtf8("label_8"))
        self.gridLayout_6.addWidget(self.label_8, 0, 0, 1, 3)
        spacerItem2 = QtGui.QSpacerItem(203, 20, QtGui.QSizePolicy.Expanding, QtGui.QSizePolicy.Minimum)
        self.gridLayout_6.addItem(spacerItem2, 1, 0, 1, 1)
        self.label_12 = QtGui.QLabel(self.tabDemandedDifficulty)
        self.label_12.setWordWrap(True)
        self.label_12.setObjectName(_fromUtf8("label_12"))
        self.gridLayout_6.addWidget(self.label_12, 4, 0, 1, 3)
        self.lineEditSmallMessageDifficulty = QtGui.QLineEdit(self.tabDemandedDifficulty)
        sizePolicy = QtGui.QSizePolicy(QtGui.QSizePolicy.Fixed, QtGui.QSizePolicy.Fixed)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.lineEditSmallMessageDifficulty.sizePolicy().hasHeightForWidth())
        self.lineEditSmallMessageDifficulty.setSizePolicy(sizePolicy)
        self.lineEditSmallMessageDifficulty.setMaximumSize(QtCore.QSize(70, 16777215))
        self.lineEditSmallMessageDifficulty.setObjectName(_fromUtf8("lineEditSmallMessageDifficulty"))
        self.gridLayout_6.addWidget(self.lineEditSmallMessageDifficulty, 3, 2, 1, 1)
        self.lineEditTotalDifficulty = QtGui.QLineEdit(self.tabDemandedDifficulty)
        sizePolicy = QtGui.QSizePolicy(QtGui.QSizePolicy.Fixed, QtGui.QSizePolicy.Fixed)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.lineEditTotalDifficulty.sizePolicy().hasHeightForWidth())
        self.lineEditTotalDifficulty.setSizePolicy(sizePolicy)
        self.lineEditTotalDifficulty.setMaximumSize(QtCore.QSize(70, 16777215))
        self.lineEditTotalDifficulty.setObjectName(_fromUtf8("lineEditTotalDifficulty"))
        self.gridLayout_6.addWidget(self.lineEditTotalDifficulty, 1, 2, 1, 1)
        spacerItem3 = QtGui.QSpacerItem(203, 20, QtGui.QSizePolicy.Expanding, QtGui.QSizePolicy.Minimum)
        self.gridLayout_6.addItem(spacerItem3, 3, 0, 1, 1)
        spacerItem4 = QtGui.QSpacerItem(20, 40, QtGui.QSizePolicy.Minimum, QtGui.QSizePolicy.Expanding)
        self.gridLayout_6.addItem(spacerItem4, 5, 0, 1, 1)
        self.tabWidgetSettings.addTab(self.tabDemandedDifficulty, _fromUtf8(""))
        self.tabMaxAcceptableDifficulty = QtGui.QWidget()
        self.tabMaxAcceptableDifficulty.setObjectName(_fromUtf8("tabMaxAcceptableDifficulty"))
        self.gridLayout_7 = QtGui.QGridLayout(self.tabMaxAcceptableDifficulty)
        self.gridLayout_7.setObjectName(_fromUtf8("gridLayout_7"))
        self.label_15 = QtGui.QLabel(self.tabMaxAcceptableDifficulty)
        self.label_15.setWordWrap(True)
        self.label_15.setObjectName(_fromUtf8("label_15"))
        self.gridLayout_7.addWidget(self.label_15, 0, 0, 1, 3)
        spacerItem5 = QtGui.QSpacerItem(102, 20, QtGui.QSizePolicy.Expanding, QtGui.QSizePolicy.Minimum)
        self.gridLayout_7.addItem(spacerItem5, 1, 0, 1, 1)
        self.label_13 = QtGui.QLabel(self.tabMaxAcceptableDifficulty)
        self.label_13.setLayoutDirection(QtCore.Qt.LeftToRight)
        self.label_13.setAlignment(QtCore.Qt.AlignRight|QtCore.Qt.AlignTrailing|QtCore.Qt.AlignVCenter)
        self.label_13.setObjectName(_fromUtf8("label_13"))
        self.gridLayout_7.addWidget(self.label_13, 1, 1, 1, 1)
        self.lineEditMaxAcceptableTotalDifficulty = QtGui.QLineEdit(self.tabMaxAcceptableDifficulty)
        sizePolicy = QtGui.QSizePolicy(QtGui.QSizePolicy.Fixed, QtGui.QSizePolicy.Fixed)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.lineEditMaxAcceptableTotalDifficulty.sizePolicy().hasHeightForWidth())
        self.lineEditMaxAcceptableTotalDifficulty.setSizePolicy(sizePolicy)
        self.lineEditMaxAcceptableTotalDifficulty.setMaximumSize(QtCore.QSize(70, 16777215))
        self.lineEditMaxAcceptableTotalDifficulty.setObjectName(_fromUtf8("lineEditMaxAcceptableTotalDifficulty"))
        self.gridLayout_7.addWidget(self.lineEditMaxAcceptableTotalDifficulty, 1, 2, 1, 1)
        spacerItem6 = QtGui.QSpacerItem(102, 20, QtGui.QSizePolicy.Expanding, QtGui.QSizePolicy.Minimum)
        self.gridLayout_7.addItem(spacerItem6, 2, 0, 1, 1)
        self.label_14 = QtGui.QLabel(self.tabMaxAcceptableDifficulty)
        self.label_14.setAlignment(QtCore.Qt.AlignRight|QtCore.Qt.AlignTrailing|QtCore.Qt.AlignVCenter)
        self.label_14.setObjectName(_fromUtf8("label_14"))
        self.gridLayout_7.addWidget(self.label_14, 2, 1, 1, 1)
        self.lineEditMaxAcceptableSmallMessageDifficulty = QtGui.QLineEdit(self.tabMaxAcceptableDifficulty)
        sizePolicy = QtGui.QSizePolicy(QtGui.QSizePolicy.Fixed, QtGui.QSizePolicy.Fixed)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.lineEditMaxAcceptableSmallMessageDifficulty.sizePolicy().hasHeightForWidth())
        self.lineEditMaxAcceptableSmallMessageDifficulty.setSizePolicy(sizePolicy)
        self.lineEditMaxAcceptableSmallMessageDifficulty.setMaximumSize(QtCore.QSize(70, 16777215))
        self.lineEditMaxAcceptableSmallMessageDifficulty.setObjectName(_fromUtf8("lineEditMaxAcceptableSmallMessageDifficulty"))
        self.gridLayout_7.addWidget(self.lineEditMaxAcceptableSmallMessageDifficulty, 2, 2, 1, 1)
        spacerItem7 = QtGui.QSpacerItem(20, 147, QtGui.QSizePolicy.Minimum, QtGui.QSizePolicy.Expanding)
        self.gridLayout_7.addItem(spacerItem7, 3, 1, 1, 1)
        self.tabWidgetSettings.addTab(self.tabMaxAcceptableDifficulty, _fromUtf8(""))
        self.tabNamecoin = QtGui.QWidget()
        self.tabNamecoin.setObjectName(_fromUtf8("tabNamecoin"))
        self.gridLayout_8 = QtGui.QGridLayout(self.tabNamecoin)
        self.gridLayout_8.setObjectName(_fromUtf8("gridLayout_8"))
        spacerItem8 = QtGui.QSpacerItem(40, 20, QtGui.QSizePolicy.Expanding, QtGui.QSizePolicy.Minimum)
        self.gridLayout_8.addItem(spacerItem8, 2, 0, 1, 1)
        self.label_16 = QtGui.QLabel(self.tabNamecoin)
        self.label_16.setWordWrap(True)
        self.label_16.setObjectName(_fromUtf8("label_16"))
        self.gridLayout_8.addWidget(self.label_16, 0, 0, 1, 3)
        self.label_17 = QtGui.QLabel(self.tabNamecoin)
        self.label_17.setAlignment(QtCore.Qt.AlignRight|QtCore.Qt.AlignTrailing|QtCore.Qt.AlignVCenter)
        self.label_17.setObjectName(_fromUtf8("label_17"))
        self.gridLayout_8.addWidget(self.label_17, 2, 1, 1, 1)
        self.lineEditNamecoinHost = QtGui.QLineEdit(self.tabNamecoin)
        self.lineEditNamecoinHost.setObjectName(_fromUtf8("lineEditNamecoinHost"))
        self.gridLayout_8.addWidget(self.lineEditNamecoinHost, 2, 2, 1, 1)
        spacerItem9 = QtGui.QSpacerItem(40, 20, QtGui.QSizePolicy.Expanding, QtGui.QSizePolicy.Minimum)
        self.gridLayout_8.addItem(spacerItem9, 3, 0, 1, 1)
        spacerItem10 = QtGui.QSpacerItem(40, 20, QtGui.QSizePolicy.Expanding, QtGui.QSizePolicy.Minimum)
        self.gridLayout_8.addItem(spacerItem10, 4, 0, 1, 1)
        self.label_18 = QtGui.QLabel(self.tabNamecoin)
        self.label_18.setEnabled(True)
        self.label_18.setAlignment(QtCore.Qt.AlignRight|QtCore.Qt.AlignTrailing|QtCore.Qt.AlignVCenter)
        self.label_18.setObjectName(_fromUtf8("label_18"))
        self.gridLayout_8.addWidget(self.label_18, 3, 1, 1, 1)
        self.lineEditNamecoinPort = QtGui.QLineEdit(self.tabNamecoin)
        self.lineEditNamecoinPort.setObjectName(_fromUtf8("lineEditNamecoinPort"))
        self.gridLayout_8.addWidget(self.lineEditNamecoinPort, 3, 2, 1, 1)
        spacerItem11 = QtGui.QSpacerItem(20, 40, QtGui.QSizePolicy.Minimum, QtGui.QSizePolicy.Expanding)
        self.gridLayout_8.addItem(spacerItem11, 8, 1, 1, 1)
        self.labelNamecoinUser = QtGui.QLabel(self.tabNamecoin)
        self.labelNamecoinUser.setAlignment(QtCore.Qt.AlignRight|QtCore.Qt.AlignTrailing|QtCore.Qt.AlignVCenter)
        self.labelNamecoinUser.setObjectName(_fromUtf8("labelNamecoinUser"))
        self.gridLayout_8.addWidget(self.labelNamecoinUser, 4, 1, 1, 1)
        self.lineEditNamecoinUser = QtGui.QLineEdit(self.tabNamecoin)
        self.lineEditNamecoinUser.setObjectName(_fromUtf8("lineEditNamecoinUser"))
        self.gridLayout_8.addWidget(self.lineEditNamecoinUser, 4, 2, 1, 1)
        spacerItem12 = QtGui.QSpacerItem(40, 20, QtGui.QSizePolicy.Expanding, QtGui.QSizePolicy.Minimum)
        self.gridLayout_8.addItem(spacerItem12, 5, 0, 1, 1)
        self.labelNamecoinPassword = QtGui.QLabel(self.tabNamecoin)
        self.labelNamecoinPassword.setAlignment(QtCore.Qt.AlignRight|QtCore.Qt.AlignTrailing|QtCore.Qt.AlignVCenter)
        self.labelNamecoinPassword.setObjectName(_fromUtf8("labelNamecoinPassword"))
        self.gridLayout_8.addWidget(self.labelNamecoinPassword, 5, 1, 1, 1)
        self.lineEditNamecoinPassword = QtGui.QLineEdit(self.tabNamecoin)
        self.lineEditNamecoinPassword.setInputMethodHints(QtCore.Qt.ImhHiddenText|QtCore.Qt.ImhNoAutoUppercase|QtCore.Qt.ImhNoPredictiveText)
        self.lineEditNamecoinPassword.setEchoMode(QtGui.QLineEdit.Password)
        self.lineEditNamecoinPassword.setObjectName(_fromUtf8("lineEditNamecoinPassword"))
        self.gridLayout_8.addWidget(self.lineEditNamecoinPassword, 5, 2, 1, 1)
        self.labelNamecoinTestResult = QtGui.QLabel(self.tabNamecoin)
        self.labelNamecoinTestResult.setText(_fromUtf8(""))
        self.labelNamecoinTestResult.setObjectName(_fromUtf8("labelNamecoinTestResult"))
        self.gridLayout_8.addWidget(self.labelNamecoinTestResult, 7, 0, 1, 2)
        self.pushButtonNamecoinTest = QtGui.QPushButton(self.tabNamecoin)
        self.pushButtonNamecoinTest.setObjectName(_fromUtf8("pushButtonNamecoinTest"))
        self.gridLayout_8.addWidget(self.pushButtonNamecoinTest, 7, 2, 1, 1)
        self.horizontalLayout = QtGui.QHBoxLayout()
        self.horizontalLayout.setObjectName(_fromUtf8("horizontalLayout"))
        self.label_21 = QtGui.QLabel(self.tabNamecoin)
        self.label_21.setObjectName(_fromUtf8("label_21"))
        self.horizontalLayout.addWidget(self.label_21)
        self.radioButtonNamecoinNamecoind = QtGui.QRadioButton(self.tabNamecoin)
        self.radioButtonNamecoinNamecoind.setObjectName(_fromUtf8("radioButtonNamecoinNamecoind"))
        self.horizontalLayout.addWidget(self.radioButtonNamecoinNamecoind)
        self.radioButtonNamecoinNmcontrol = QtGui.QRadioButton(self.tabNamecoin)
        self.radioButtonNamecoinNmcontrol.setObjectName(_fromUtf8("radioButtonNamecoinNmcontrol"))
        self.horizontalLayout.addWidget(self.radioButtonNamecoinNmcontrol)
        self.gridLayout_8.addLayout(self.horizontalLayout, 1, 0, 1, 3)
        self.tabWidgetSettings.addTab(self.tabNamecoin, _fromUtf8(""))
        self.tabResendsExpire = QtGui.QWidget()
        self.tabResendsExpire.setObjectName(_fromUtf8("tabResendsExpire"))
        self.gridLayout_5 = QtGui.QGridLayout(self.tabResendsExpire)
        self.gridLayout_5.setObjectName(_fromUtf8("gridLayout_5"))
        self.label_7 = QtGui.QLabel(self.tabResendsExpire)
        self.label_7.setWordWrap(True)
        self.label_7.setObjectName(_fromUtf8("label_7"))
        self.gridLayout_5.addWidget(self.label_7, 0, 0, 1, 3)
        spacerItem13 = QtGui.QSpacerItem(212, 20, QtGui.QSizePolicy.Expanding, QtGui.QSizePolicy.Minimum)
        self.gridLayout_5.addItem(spacerItem13, 1, 0, 1, 1)
        self.widget = QtGui.QWidget(self.tabResendsExpire)
        self.widget.setMinimumSize(QtCore.QSize(231, 75))
        self.widget.setObjectName(_fromUtf8("widget"))
        self.label_19 = QtGui.QLabel(self.widget)
        self.label_19.setGeometry(QtCore.QRect(10, 20, 101, 20))
        self.label_19.setAlignment(QtCore.Qt.AlignRight|QtCore.Qt.AlignTrailing|QtCore.Qt.AlignVCenter)
        self.label_19.setObjectName(_fromUtf8("label_19"))
        self.label_20 = QtGui.QLabel(self.widget)
        self.label_20.setGeometry(QtCore.QRect(30, 40, 80, 16))
        self.label_20.setAlignment(QtCore.Qt.AlignRight|QtCore.Qt.AlignTrailing|QtCore.Qt.AlignVCenter)
        self.label_20.setObjectName(_fromUtf8("label_20"))
        self.lineEditDays = QtGui.QLineEdit(self.widget)
        self.lineEditDays.setGeometry(QtCore.QRect(113, 20, 51, 20))
        self.lineEditDays.setObjectName(_fromUtf8("lineEditDays"))
        self.lineEditMonths = QtGui.QLineEdit(self.widget)
        self.lineEditMonths.setGeometry(QtCore.QRect(113, 40, 51, 20))
        self.lineEditMonths.setObjectName(_fromUtf8("lineEditMonths"))
        self.label_22 = QtGui.QLabel(self.widget)
        self.label_22.setGeometry(QtCore.QRect(169, 23, 61, 16))
        self.label_22.setObjectName(_fromUtf8("label_22"))
        self.label_23 = QtGui.QLabel(self.widget)
        self.label_23.setGeometry(QtCore.QRect(170, 41, 71, 16))
        self.label_23.setObjectName(_fromUtf8("label_23"))
        self.gridLayout_5.addWidget(self.widget, 1, 2, 1, 1)
        spacerItem14 = QtGui.QSpacerItem(20, 129, QtGui.QSizePolicy.Minimum, QtGui.QSizePolicy.Expanding)
        self.gridLayout_5.addItem(spacerItem14, 2, 1, 1, 1)
        self.tabWidgetSettings.addTab(self.tabResendsExpire, _fromUtf8(""))
        self.gridLayout.addWidget(self.tabWidgetSettings, 0, 0, 1, 1)

        self.retranslateUi(settingsDialog)
        self.tabWidgetSettings.setCurrentIndex(0)
        QtCore.QObject.connect(self.buttonBox, QtCore.SIGNAL(_fromUtf8("accepted()")), settingsDialog.accept)
        QtCore.QObject.connect(self.buttonBox, QtCore.SIGNAL(_fromUtf8("rejected()")), settingsDialog.reject)
        QtCore.QObject.connect(self.checkBoxAuthentication, QtCore.SIGNAL(_fromUtf8("toggled(bool)")), self.lineEditSocksUsername.setEnabled)
        QtCore.QObject.connect(self.checkBoxAuthentication, QtCore.SIGNAL(_fromUtf8("toggled(bool)")), self.lineEditSocksPassword.setEnabled)
        QtCore.QMetaObject.connectSlotsByName(settingsDialog)
        settingsDialog.setTabOrder(self.tabWidgetSettings, self.checkBoxStartOnLogon)
        settingsDialog.setTabOrder(self.checkBoxStartOnLogon, self.checkBoxStartInTray)
        settingsDialog.setTabOrder(self.checkBoxStartInTray, self.checkBoxMinimizeToTray)
        settingsDialog.setTabOrder(self.checkBoxMinimizeToTray, self.lineEditTCPPort)
        settingsDialog.setTabOrder(self.lineEditTCPPort, self.comboBoxProxyType)
        settingsDialog.setTabOrder(self.comboBoxProxyType, self.lineEditSocksHostname)
        settingsDialog.setTabOrder(self.lineEditSocksHostname, self.lineEditSocksPort)
        settingsDialog.setTabOrder(self.lineEditSocksPort, self.checkBoxAuthentication)
        settingsDialog.setTabOrder(self.checkBoxAuthentication, self.lineEditSocksUsername)
        settingsDialog.setTabOrder(self.lineEditSocksUsername, self.lineEditSocksPassword)
        settingsDialog.setTabOrder(self.lineEditSocksPassword, self.checkBoxSocksListen)
        settingsDialog.setTabOrder(self.checkBoxSocksListen, self.buttonBox)

    def retranslateUi(self, settingsDialog):
        settingsDialog.setWindowTitle(_translate("settingsDialog", "Settings", None))
        self.checkBoxStartOnLogon.setText(_translate("settingsDialog", "Start Bitmessage on user login", None))
        self.checkBoxStartInTray.setText(_translate("settingsDialog", "Start Bitmessage in the tray (don\'t show main window)", None))
        self.checkBoxMinimizeToTray.setText(_translate("settingsDialog", "Minimize to tray", None))
        self.checkBoxShowTrayNotifications.setText(_translate("settingsDialog", "Show notification when message received", None))
        self.checkBoxPortableMode.setText(_translate("settingsDialog", "Run in Portable Mode", None))
        self.PortableModeDescription.setText(_translate("settingsDialog", "In Portable Mode, messages and config files are stored in the same directory as the program rather than the normal application-data folder. This makes it convenient to run Bitmessage from a USB thumb drive.", None))
        self.checkBoxWillinglySendToMobile.setText(_translate("settingsDialog", "Willingly include unencrypted destination address when sending to a mobile device", None))
        self.checkBoxUseIdenticons.setText(_translate("settingsDialog", "Use Identicons", None))
        self.checkBoxReplyBelow.setText(_translate("settingsDialog", "Reply below Quote", None))
        self.groupBox.setTitle(_translate("settingsDialog", "Interface Language", None))
        self.languageComboBox.setItemText(0, _translate("settingsDialog", "System Settings", "system"))
        self.languageComboBox.setItemText(12, _translate("settingsDialog", "Pirate English", "en_pirate"))
        self.languageComboBox.setItemText(13, _translate("settingsDialog", "Other (set in keys.dat)", "other"))
        self.tabWidgetSettings.setTabText(self.tabWidgetSettings.indexOf(self.tabUserInterface), _translate("settingsDialog", "User Interface", None))
        self.groupBox1.setTitle(_translate("settingsDialog", "Listening port", None))
        self.label.setText(_translate("settingsDialog", "Listen for connections on port:", None))
        self.groupBox_2.setTitle(_translate("settingsDialog", "Proxy server / Tor", None))
        self.label_2.setText(_translate("settingsDialog", "Type:", None))
        self.label_3.setText(_translate("settingsDialog", "Server hostname:", None))
        self.label_4.setText(_translate("settingsDialog", "Port:", None))
        self.checkBoxAuthentication.setText(_translate("settingsDialog", "Authentication", None))
        self.label_5.setText(_translate("settingsDialog", "Username:", None))
        self.label_6.setText(_translate("settingsDialog", "Pass:", None))
        self.checkBoxSocksListen.setText(_translate("settingsDialog", "Listen for incoming connections when using proxy", None))
        self.comboBoxProxyType.setItemText(0, _translate("settingsDialog", "none", None))
        self.comboBoxProxyType.setItemText(1, _translate("settingsDialog", "SOCKS4a", None))
        self.comboBoxProxyType.setItemText(2, _translate("settingsDialog", "SOCKS5", None))
        self.tabWidgetSettings.setTabText(self.tabWidgetSettings.indexOf(self.tabNetworkSettings), _translate("settingsDialog", "Network Settings", None))
        self.label_9.setText(_translate("settingsDialog", "Total difficulty:", None))
        self.label_10.setText(_translate("settingsDialog", "The \'Total difficulty\' affects the absolute amount of work the sender must complete. Doubling this value doubles the amount of work.", None))
        self.label_11.setText(_translate("settingsDialog", "Small message difficulty:", None))
        self.label_8.setText(_translate("settingsDialog", "When someone sends you a message, their computer must first complete some work. The difficulty of this work, by default, is 1. You may raise this default for new addresses you create by changing the values here. Any new addresses you create will require senders to meet the higher difficulty. There is one exception: if you add a friend or acquaintance to your address book, Bitmessage will automatically notify them when you next send a message that they need only complete the minimum amount of work: difficulty 1. ", None))
        self.label_12.setText(_translate("settingsDialog", "The \'Small message difficulty\' mostly only affects the difficulty of sending small messages. Doubling this value makes it almost twice as difficult to send a small message but doesn\'t really affect large messages.", None))
        self.tabWidgetSettings.setTabText(self.tabWidgetSettings.indexOf(self.tabDemandedDifficulty), _translate("settingsDialog", "Demanded difficulty", None))
        self.label_15.setText(_translate("settingsDialog", "Here you may set the maximum amount of work you are willing to do to send a message to another person. Setting these values to 0 means that any value is acceptable.", None))
        self.label_13.setText(_translate("settingsDialog", "Maximum acceptable total difficulty:", None))
        self.label_14.setText(_translate("settingsDialog", "Maximum acceptable small message difficulty:", None))
        self.tabWidgetSettings.setTabText(self.tabWidgetSettings.indexOf(self.tabMaxAcceptableDifficulty), _translate("settingsDialog", "Max acceptable difficulty", None))
        self.label_16.setText(_translate("settingsDialog", "<html><head/><body><p>Bitmessage can utilize a different Bitcoin-based program called Namecoin to make addresses human-friendly. For example, instead of having to tell your friend your long Bitmessage address, you can simply tell him to send a message to <span style=\" font-style:italic;\">test. </span></p><p>(Getting your own Bitmessage address into Namecoin is still rather difficult).</p><p>Bitmessage can use either namecoind directly or a running nmcontrol instance.</p></body></html>", None))
        self.label_17.setText(_translate("settingsDialog", "Host:", None))
        self.label_18.setText(_translate("settingsDialog", "Port:", None))
        self.labelNamecoinUser.setText(_translate("settingsDialog", "Username:", None))
        self.labelNamecoinPassword.setText(_translate("settingsDialog", "Password:", None))
        self.pushButtonNamecoinTest.setText(_translate("settingsDialog", "Test", None))
        self.label_21.setText(_translate("settingsDialog", "Connect to:", None))
        self.radioButtonNamecoinNamecoind.setText(_translate("settingsDialog", "Namecoind", None))
        self.radioButtonNamecoinNmcontrol.setText(_translate("settingsDialog", "NMControl", None))
        self.tabWidgetSettings.setTabText(self.tabWidgetSettings.indexOf(self.tabNamecoin), _translate("settingsDialog", "Namecoin integration", None))
        self.label_7.setText(_translate("settingsDialog", "<html><head/><body><p>By default, if you send a message to someone and he is offline for more than two days, Bitmessage will send the message again after an additional two days. This will be continued with exponential backoff forever; messages will be resent after 5, 10, 20 days ect. until the receiver acknowledges them. Here you may change that behavior by having Bitmessage give up after a certain number of days or months.</p><p>Leave these input fields blank for the default behavior. </p></body></html>", None))
        self.label_19.setText(_translate("settingsDialog", "Give up after", None))
        self.label_20.setText(_translate("settingsDialog", "and", None))
        self.label_22.setText(_translate("settingsDialog", "days", None))
        self.label_23.setText(_translate("settingsDialog", "months.", None))
        self.tabWidgetSettings.setTabText(self.tabWidgetSettings.indexOf(self.tabResendsExpire), _translate("settingsDialog", "Resends Expire", None))

import bitmessage_icons_rc

########NEW FILE########
__FILENAME__ = specialaddressbehavior
# -*- coding: utf-8 -*-

# Form implementation generated from reading ui file 'specialaddressbehavior.ui'
#
# Created: Fri Apr 26 17:43:31 2013
#      by: PyQt4 UI code generator 4.9.4
#
# WARNING! All changes made in this file will be lost!

from PyQt4 import QtCore, QtGui

try:
    _fromUtf8 = QtCore.QString.fromUtf8
except AttributeError:
    _fromUtf8 = lambda s: s

class Ui_SpecialAddressBehaviorDialog(object):
    def setupUi(self, SpecialAddressBehaviorDialog):
        SpecialAddressBehaviorDialog.setObjectName(_fromUtf8("SpecialAddressBehaviorDialog"))
        SpecialAddressBehaviorDialog.resize(386, 172)
        self.gridLayout = QtGui.QGridLayout(SpecialAddressBehaviorDialog)
        self.gridLayout.setObjectName(_fromUtf8("gridLayout"))
        self.radioButtonBehaveNormalAddress = QtGui.QRadioButton(SpecialAddressBehaviorDialog)
        self.radioButtonBehaveNormalAddress.setChecked(True)
        self.radioButtonBehaveNormalAddress.setObjectName(_fromUtf8("radioButtonBehaveNormalAddress"))
        self.gridLayout.addWidget(self.radioButtonBehaveNormalAddress, 0, 0, 1, 1)
        self.radioButtonBehaviorMailingList = QtGui.QRadioButton(SpecialAddressBehaviorDialog)
        self.radioButtonBehaviorMailingList.setObjectName(_fromUtf8("radioButtonBehaviorMailingList"))
        self.gridLayout.addWidget(self.radioButtonBehaviorMailingList, 1, 0, 1, 1)
        self.label = QtGui.QLabel(SpecialAddressBehaviorDialog)
        self.label.setWordWrap(True)
        self.label.setObjectName(_fromUtf8("label"))
        self.gridLayout.addWidget(self.label, 2, 0, 1, 1)
        self.label_2 = QtGui.QLabel(SpecialAddressBehaviorDialog)
        self.label_2.setObjectName(_fromUtf8("label_2"))
        self.gridLayout.addWidget(self.label_2, 3, 0, 1, 1)
        self.lineEditMailingListName = QtGui.QLineEdit(SpecialAddressBehaviorDialog)
        self.lineEditMailingListName.setEnabled(False)
        self.lineEditMailingListName.setObjectName(_fromUtf8("lineEditMailingListName"))
        self.gridLayout.addWidget(self.lineEditMailingListName, 4, 0, 1, 1)
        self.buttonBox = QtGui.QDialogButtonBox(SpecialAddressBehaviorDialog)
        self.buttonBox.setMinimumSize(QtCore.QSize(368, 0))
        self.buttonBox.setOrientation(QtCore.Qt.Horizontal)
        self.buttonBox.setStandardButtons(QtGui.QDialogButtonBox.Cancel|QtGui.QDialogButtonBox.Ok)
        self.buttonBox.setObjectName(_fromUtf8("buttonBox"))
        self.gridLayout.addWidget(self.buttonBox, 5, 0, 1, 1)

        self.retranslateUi(SpecialAddressBehaviorDialog)
        QtCore.QObject.connect(self.buttonBox, QtCore.SIGNAL(_fromUtf8("accepted()")), SpecialAddressBehaviorDialog.accept)
        QtCore.QObject.connect(self.buttonBox, QtCore.SIGNAL(_fromUtf8("rejected()")), SpecialAddressBehaviorDialog.reject)
        QtCore.QObject.connect(self.radioButtonBehaviorMailingList, QtCore.SIGNAL(_fromUtf8("clicked(bool)")), self.lineEditMailingListName.setEnabled)
        QtCore.QObject.connect(self.radioButtonBehaveNormalAddress, QtCore.SIGNAL(_fromUtf8("clicked(bool)")), self.lineEditMailingListName.setDisabled)
        QtCore.QMetaObject.connectSlotsByName(SpecialAddressBehaviorDialog)
        SpecialAddressBehaviorDialog.setTabOrder(self.radioButtonBehaveNormalAddress, self.radioButtonBehaviorMailingList)
        SpecialAddressBehaviorDialog.setTabOrder(self.radioButtonBehaviorMailingList, self.lineEditMailingListName)
        SpecialAddressBehaviorDialog.setTabOrder(self.lineEditMailingListName, self.buttonBox)

    def retranslateUi(self, SpecialAddressBehaviorDialog):
        SpecialAddressBehaviorDialog.setWindowTitle(QtGui.QApplication.translate("SpecialAddressBehaviorDialog", "Special Address Behavior", None, QtGui.QApplication.UnicodeUTF8))
        self.radioButtonBehaveNormalAddress.setText(QtGui.QApplication.translate("SpecialAddressBehaviorDialog", "Behave as a normal address", None, QtGui.QApplication.UnicodeUTF8))
        self.radioButtonBehaviorMailingList.setText(QtGui.QApplication.translate("SpecialAddressBehaviorDialog", "Behave as a pseudo-mailing-list address", None, QtGui.QApplication.UnicodeUTF8))
        self.label.setText(QtGui.QApplication.translate("SpecialAddressBehaviorDialog", "Mail received to a pseudo-mailing-list address will be automatically broadcast to subscribers (and thus will be public).", None, QtGui.QApplication.UnicodeUTF8))
        self.label_2.setText(QtGui.QApplication.translate("SpecialAddressBehaviorDialog", "Name of the pseudo-mailing-list:", None, QtGui.QApplication.UnicodeUTF8))


########NEW FILE########
__FILENAME__ = build_osx
from setuptools import setup

name = "Bitmessage"
version = "0.4.2"
mainscript = ["bitmessagemain.py"]

setup(
	name = name,
	version = version,
	app = mainscript,
	setup_requires = ["py2app"],
	options = dict(
		py2app = dict(
			resources = ["images", "translations"],
			includes = ['sip', 'PyQt4._qt'],
			iconfile = "images/bitmessage.icns"
		)
	)
)

########NEW FILE########
__FILENAME__ = class_addressGenerator
import shared
import threading
import time
import sys
from pyelliptic.openssl import OpenSSL
import ctypes
import hashlib
import highlevelcrypto
from addresses import *
from pyelliptic import arithmetic
import tr

class addressGenerator(threading.Thread):

    def __init__(self):
        # QThread.__init__(self, parent)
        threading.Thread.__init__(self)

    def run(self):
        while True:
            queueValue = shared.addressGeneratorQueue.get()
            nonceTrialsPerByte = 0
            payloadLengthExtraBytes = 0
            if queueValue[0] == 'createChan':
                command, addressVersionNumber, streamNumber, label, deterministicPassphrase = queueValue
                eighteenByteRipe = False
                numberOfAddressesToMake = 1
                numberOfNullBytesDemandedOnFrontOfRipeHash = 1
            elif queueValue[0] == 'joinChan':
                command, chanAddress, label, deterministicPassphrase = queueValue
                eighteenByteRipe = False
                addressVersionNumber = decodeAddress(chanAddress)[1]
                streamNumber = decodeAddress(chanAddress)[2]
                numberOfAddressesToMake = 1
                numberOfNullBytesDemandedOnFrontOfRipeHash = 1
            elif len(queueValue) == 7:
                command, addressVersionNumber, streamNumber, label, numberOfAddressesToMake, deterministicPassphrase, eighteenByteRipe = queueValue
                try:
                    numberOfNullBytesDemandedOnFrontOfRipeHash = shared.config.getint(
                        'bitmessagesettings', 'numberofnullbytesonaddress')
                except:
                    if eighteenByteRipe:
                        numberOfNullBytesDemandedOnFrontOfRipeHash = 2
                    else:
                        numberOfNullBytesDemandedOnFrontOfRipeHash = 1 # the default
            elif len(queueValue) == 9:
                command, addressVersionNumber, streamNumber, label, numberOfAddressesToMake, deterministicPassphrase, eighteenByteRipe, nonceTrialsPerByte, payloadLengthExtraBytes = queueValue
                try:
                    numberOfNullBytesDemandedOnFrontOfRipeHash = shared.config.getint(
                        'bitmessagesettings', 'numberofnullbytesonaddress')
                except:
                    if eighteenByteRipe:
                        numberOfNullBytesDemandedOnFrontOfRipeHash = 2
                    else:
                        numberOfNullBytesDemandedOnFrontOfRipeHash = 1 # the default
            else:
                sys.stderr.write(
                    'Programming error: A structure with the wrong number of values was passed into the addressGeneratorQueue. Here is the queueValue: %s\n' % repr(queueValue))
            if addressVersionNumber < 3 or addressVersionNumber > 4:
                sys.stderr.write(
                    'Program error: For some reason the address generator queue has been given a request to create at least one version %s address which it cannot do.\n' % addressVersionNumber)
            if nonceTrialsPerByte == 0:
                nonceTrialsPerByte = shared.config.getint(
                    'bitmessagesettings', 'defaultnoncetrialsperbyte')
            if nonceTrialsPerByte < shared.networkDefaultProofOfWorkNonceTrialsPerByte:
                nonceTrialsPerByte = shared.networkDefaultProofOfWorkNonceTrialsPerByte
            if payloadLengthExtraBytes == 0:
                payloadLengthExtraBytes = shared.config.getint(
                    'bitmessagesettings', 'defaultpayloadlengthextrabytes')
            if payloadLengthExtraBytes < shared.networkDefaultPayloadLengthExtraBytes:
                payloadLengthExtraBytes = shared.networkDefaultPayloadLengthExtraBytes
            if command == 'createRandomAddress':
                shared.UISignalQueue.put((
                    'updateStatusBar', tr.translateText("MainWindow", "Generating one new address")))
                # This next section is a little bit strange. We're going to generate keys over and over until we
                # find one that starts with either \x00 or \x00\x00. Then when we pack them into a Bitmessage address,
                # we won't store the \x00 or \x00\x00 bytes thus making the
                # address shorter.
                startTime = time.time()
                numberOfAddressesWeHadToMakeBeforeWeFoundOneWithTheCorrectRipePrefix = 0
                potentialPrivSigningKey = OpenSSL.rand(32)
                potentialPubSigningKey = pointMult(potentialPrivSigningKey)
                while True:
                    numberOfAddressesWeHadToMakeBeforeWeFoundOneWithTheCorrectRipePrefix += 1
                    potentialPrivEncryptionKey = OpenSSL.rand(32)
                    potentialPubEncryptionKey = pointMult(
                        potentialPrivEncryptionKey)
                    # print 'potentialPubSigningKey', potentialPubSigningKey.encode('hex')
                    # print 'potentialPubEncryptionKey',
                    # potentialPubEncryptionKey.encode('hex')
                    ripe = hashlib.new('ripemd160')
                    sha = hashlib.new('sha512')
                    sha.update(
                        potentialPubSigningKey + potentialPubEncryptionKey)
                    ripe.update(sha.digest())
                    # print 'potential ripe.digest',
                    # ripe.digest().encode('hex')
                    if ripe.digest()[:numberOfNullBytesDemandedOnFrontOfRipeHash] == '\x00' * numberOfNullBytesDemandedOnFrontOfRipeHash:
                        break
                print 'Generated address with ripe digest:', ripe.digest().encode('hex')
                print 'Address generator calculated', numberOfAddressesWeHadToMakeBeforeWeFoundOneWithTheCorrectRipePrefix, 'addresses at', numberOfAddressesWeHadToMakeBeforeWeFoundOneWithTheCorrectRipePrefix / (time.time() - startTime), 'addresses per second before finding one with the correct ripe-prefix.'
                address = encodeAddress(addressVersionNumber, streamNumber, ripe.digest())

                # An excellent way for us to store our keys is in Wallet Import Format. Let us convert now.
                # https://en.bitcoin.it/wiki/Wallet_import_format
                privSigningKey = '\x80' + potentialPrivSigningKey
                checksum = hashlib.sha256(hashlib.sha256(
                    privSigningKey).digest()).digest()[0:4]
                privSigningKeyWIF = arithmetic.changebase(
                    privSigningKey + checksum, 256, 58)
                # print 'privSigningKeyWIF',privSigningKeyWIF

                privEncryptionKey = '\x80' + potentialPrivEncryptionKey
                checksum = hashlib.sha256(hashlib.sha256(
                    privEncryptionKey).digest()).digest()[0:4]
                privEncryptionKeyWIF = arithmetic.changebase(
                    privEncryptionKey + checksum, 256, 58)
                # print 'privEncryptionKeyWIF',privEncryptionKeyWIF

                shared.config.add_section(address)
                shared.config.set(address, 'label', label)
                shared.config.set(address, 'enabled', 'true')
                shared.config.set(address, 'decoy', 'false')
                shared.config.set(address, 'noncetrialsperbyte', str(
                    nonceTrialsPerByte))
                shared.config.set(address, 'payloadlengthextrabytes', str(
                    payloadLengthExtraBytes))
                shared.config.set(
                    address, 'privSigningKey', privSigningKeyWIF)
                shared.config.set(
                    address, 'privEncryptionKey', privEncryptionKeyWIF)
                with open(shared.appdata + 'keys.dat', 'wb') as configfile:
                    shared.config.write(configfile)

                # The API and the join and create Chan functionality
                # both need information back from the address generator.
                shared.apiAddressGeneratorReturnQueue.put(address)

                shared.UISignalQueue.put((
                    'updateStatusBar', tr.translateText("MainWindow", "Done generating address. Doing work necessary to broadcast it...")))
                shared.UISignalQueue.put(('writeNewAddressToTable', (
                    label, address, streamNumber)))
                shared.reloadMyAddressHashes()
                if addressVersionNumber == 3:
                    shared.workerQueue.put((
                        'sendOutOrStoreMyV3Pubkey', ripe.digest()))
                elif addressVersionNumber == 4:
                    shared.workerQueue.put((
                        'sendOutOrStoreMyV4Pubkey', address))

            elif command == 'createDeterministicAddresses' or command == 'getDeterministicAddress' or command == 'createChan' or command == 'joinChan':
                if len(deterministicPassphrase) == 0:
                    sys.stderr.write(
                        'WARNING: You are creating deterministic address(es) using a blank passphrase. Bitmessage will do it but it is rather stupid.')
                if command == 'createDeterministicAddresses':
                    statusbar = 'Generating ' + str(
                        numberOfAddressesToMake) + ' new addresses.'
                    shared.UISignalQueue.put((
                        'updateStatusBar', statusbar))
                signingKeyNonce = 0
                encryptionKeyNonce = 1
                listOfNewAddressesToSendOutThroughTheAPI = [
                ]  # We fill out this list no matter what although we only need it if we end up passing the info to the API.

                for i in range(numberOfAddressesToMake):
                    # This next section is a little bit strange. We're going to generate keys over and over until we
                    # find one that has a RIPEMD hash that starts with either \x00 or \x00\x00. Then when we pack them
                    # into a Bitmessage address, we won't store the \x00 or
                    # \x00\x00 bytes thus making the address shorter.
                    startTime = time.time()
                    numberOfAddressesWeHadToMakeBeforeWeFoundOneWithTheCorrectRipePrefix = 0
                    while True:
                        numberOfAddressesWeHadToMakeBeforeWeFoundOneWithTheCorrectRipePrefix += 1
                        potentialPrivSigningKey = hashlib.sha512(
                            deterministicPassphrase + encodeVarint(signingKeyNonce)).digest()[:32]
                        potentialPrivEncryptionKey = hashlib.sha512(
                            deterministicPassphrase + encodeVarint(encryptionKeyNonce)).digest()[:32]
                        potentialPubSigningKey = pointMult(
                            potentialPrivSigningKey)
                        potentialPubEncryptionKey = pointMult(
                            potentialPrivEncryptionKey)
                        # print 'potentialPubSigningKey', potentialPubSigningKey.encode('hex')
                        # print 'potentialPubEncryptionKey',
                        # potentialPubEncryptionKey.encode('hex')
                        signingKeyNonce += 2
                        encryptionKeyNonce += 2
                        ripe = hashlib.new('ripemd160')
                        sha = hashlib.new('sha512')
                        sha.update(
                            potentialPubSigningKey + potentialPubEncryptionKey)
                        ripe.update(sha.digest())
                        # print 'potential ripe.digest',
                        # ripe.digest().encode('hex')
                        if ripe.digest()[:numberOfNullBytesDemandedOnFrontOfRipeHash] == '\x00' * numberOfNullBytesDemandedOnFrontOfRipeHash:
                            break

                    print 'ripe.digest', ripe.digest().encode('hex')
                    print 'Address generator calculated', numberOfAddressesWeHadToMakeBeforeWeFoundOneWithTheCorrectRipePrefix, 'addresses at', numberOfAddressesWeHadToMakeBeforeWeFoundOneWithTheCorrectRipePrefix / (time.time() - startTime), 'keys per second.'
                    address = encodeAddress(addressVersionNumber, streamNumber, ripe.digest())

                    saveAddressToDisk = True
                    # If we are joining an existing chan, let us check to make sure it matches the provided Bitmessage address
                    if command == 'joinChan':
                        if address != chanAddress:
                            shared.apiAddressGeneratorReturnQueue.put('chan name does not match address')
                            saveAddressToDisk = False
                    if command == 'getDeterministicAddress':
                        saveAddressToDisk = False

                    if saveAddressToDisk:
                        # An excellent way for us to store our keys is in Wallet Import Format. Let us convert now.
                        # https://en.bitcoin.it/wiki/Wallet_import_format
                        privSigningKey = '\x80' + potentialPrivSigningKey
                        checksum = hashlib.sha256(hashlib.sha256(
                            privSigningKey).digest()).digest()[0:4]
                        privSigningKeyWIF = arithmetic.changebase(
                            privSigningKey + checksum, 256, 58)

                        privEncryptionKey = '\x80' + \
                            potentialPrivEncryptionKey
                        checksum = hashlib.sha256(hashlib.sha256(
                            privEncryptionKey).digest()).digest()[0:4]
                        privEncryptionKeyWIF = arithmetic.changebase(
                            privEncryptionKey + checksum, 256, 58)

                        addressAlreadyExists = False
                        try:
                            shared.config.add_section(address)
                        except:
                            print address, 'already exists. Not adding it again.'
                            addressAlreadyExists = True
                        if not addressAlreadyExists:
                            print 'label:', label
                            shared.config.set(address, 'label', label)
                            shared.config.set(address, 'enabled', 'true')
                            shared.config.set(address, 'decoy', 'false')
                            if command == 'joinChan' or command == 'createChan':
                                shared.config.set(address, 'chan', 'true')
                            shared.config.set(address, 'noncetrialsperbyte', str(
                                nonceTrialsPerByte))
                            shared.config.set(address, 'payloadlengthextrabytes', str(
                                payloadLengthExtraBytes))
                            shared.config.set(
                                address, 'privSigningKey', privSigningKeyWIF)
                            shared.config.set(
                                address, 'privEncryptionKey', privEncryptionKeyWIF)
                            with open(shared.appdata + 'keys.dat', 'wb') as configfile:
                                shared.config.write(configfile)

                            shared.UISignalQueue.put(('writeNewAddressToTable', (
                                label, address, str(streamNumber))))
                            listOfNewAddressesToSendOutThroughTheAPI.append(
                                address)
                            shared.myECCryptorObjects[ripe.digest()] = highlevelcrypto.makeCryptor(
                                potentialPrivEncryptionKey.encode('hex'))
                            shared.myAddressesByHash[ripe.digest()] = address
                            tag = hashlib.sha512(hashlib.sha512(encodeVarint(
                                addressVersionNumber) + encodeVarint(streamNumber) + ripe.digest()).digest()).digest()[32:]
                            shared.myAddressesByTag[tag] = address
                            if addressVersionNumber == 3:
                                shared.workerQueue.put((
                                    'sendOutOrStoreMyV3Pubkey', ripe.digest())) # If this is a chan address,
                                        # the worker thread won't send out the pubkey over the network.
                            elif addressVersionNumber == 4:
                                shared.workerQueue.put((
                                    'sendOutOrStoreMyV4Pubkey', address))


                # Done generating addresses.
                if command == 'createDeterministicAddresses' or command == 'joinChan' or command == 'createChan':
                    shared.apiAddressGeneratorReturnQueue.put(
                        listOfNewAddressesToSendOutThroughTheAPI)
                    shared.UISignalQueue.put((
                        'updateStatusBar', tr.translateText("MainWindow", "Done generating address")))
                    # shared.reloadMyAddressHashes()
                elif command == 'getDeterministicAddress':
                    shared.apiAddressGeneratorReturnQueue.put(address)
                #todo: return things to the API if createChan or joinChan assuming saveAddressToDisk
            else:
                raise Exception(
                    "Error in the addressGenerator thread. Thread was given a command it could not understand: " + command)


# Does an EC point multiplication; turns a private key into a public key.
def pointMult(secret):
    # ctx = OpenSSL.BN_CTX_new() #This value proved to cause Seg Faults on
    # Linux. It turns out that it really didn't speed up EC_POINT_mul anyway.
    k = OpenSSL.EC_KEY_new_by_curve_name(OpenSSL.get_curve('secp256k1'))
    priv_key = OpenSSL.BN_bin2bn(secret, 32, 0)
    group = OpenSSL.EC_KEY_get0_group(k)
    pub_key = OpenSSL.EC_POINT_new(group)

    OpenSSL.EC_POINT_mul(group, pub_key, priv_key, None, None, None)
    OpenSSL.EC_KEY_set_private_key(k, priv_key)
    OpenSSL.EC_KEY_set_public_key(k, pub_key)
    # print 'priv_key',priv_key
    # print 'pub_key',pub_key

    size = OpenSSL.i2o_ECPublicKey(k, 0)
    mb = ctypes.create_string_buffer(size)
    OpenSSL.i2o_ECPublicKey(k, ctypes.byref(ctypes.pointer(mb)))
    # print 'mb.raw', mb.raw.encode('hex'), 'length:', len(mb.raw)
    # print 'mb.raw', mb.raw, 'length:', len(mb.raw)

    OpenSSL.EC_POINT_free(pub_key)
    # OpenSSL.BN_CTX_free(ctx)
    OpenSSL.BN_free(priv_key)
    OpenSSL.EC_KEY_free(k)
    return mb.raw
    
    

########NEW FILE########
__FILENAME__ = class_objectHashHolder
# objectHashHolder is a timer-driven thread. One objectHashHolder thread is used
# by each sendDataThread. The sendDataThread uses it whenever it needs to
# advertise an object to peers in an inv message, or advertise a peer to other
# peers in an addr message. Instead of sending them out immediately, it must
# wait a random number of seconds for each connection so that different peers
# get different objects at different times. Thus an attacker who is
# connecting to many network nodes who receives a message first from Alice
# cannot be sure if Alice is the node who originated the message.

import random
import time
import threading

class objectHashHolder(threading.Thread):
    def __init__(self, sendDataThreadMailbox):
        threading.Thread.__init__(self)
        self.shutdown = False
        self.sendDataThreadMailbox = sendDataThreadMailbox # This queue is used to submit data back to our associated sendDataThread.
        self.collectionOfHashLists = {}
        self.collectionOfPeerLists = {}
        for i in range(10):
            self.collectionOfHashLists[i] = []
            self.collectionOfPeerLists[i] = []

    def run(self):
        iterator = 0
        while not self.shutdown:
            if len(self.collectionOfHashLists[iterator]) > 0:
                self.sendDataThreadMailbox.put((0, 'sendinv', self.collectionOfHashLists[iterator]))
                self.collectionOfHashLists[iterator] = []
            if len(self.collectionOfPeerLists[iterator]) > 0:
                self.sendDataThreadMailbox.put((0, 'sendaddr', self.collectionOfPeerLists[iterator]))
                self.collectionOfPeerLists[iterator] = []
            iterator += 1
            iterator %= 10
            time.sleep(1)

    def holdHash(self,hash):
        self.collectionOfHashLists[random.randrange(0, 10)].append(hash)

    def holdPeer(self,peerDetails):
        self.collectionOfPeerLists[random.randrange(0, 10)].append(peerDetails)

    def close(self):
        self.shutdown = True
########NEW FILE########
__FILENAME__ = class_objectProcessor
import time
import threading
import shared
import hashlib
import random
from struct import unpack, pack
import sys
import string
from subprocess import call  # used when the API must execute an outside program
from pyelliptic.openssl import OpenSSL

import highlevelcrypto
from addresses import *
import helper_generic
import helper_bitcoin
import helper_inbox
import helper_sent
from helper_sql import *
import tr
from debug import logger


class objectProcessor(threading.Thread):
    """
    The objectProcessor thread, of which there is only one, receives network
    objecs (msg, broadcast, pubkey, getpubkey) from the receiveDataThreads.
    """
    def __init__(self):
        threading.Thread.__init__(self)
        """
        It may be the case that the last time Bitmessage was running, the user
        closed it before it finished processing everything in the
        objectProcessorQueue. Assuming that Bitmessage wasn't closed forcefully,
        it should have saved the data in the queue into the objectprocessorqueue 
        table. Let's pull it out.
        """
        queryreturn = sqlQuery(
            '''SELECT objecttype, data FROM objectprocessorqueue''')
        with shared.objectProcessorQueueSizeLock:
            for row in queryreturn:
                objectType, data = row
                shared.objectProcessorQueueSize += len(data)
                shared.objectProcessorQueue.put((objectType,data))
        sqlExecute('''DELETE FROM objectprocessorqueue''')
        logger.debug('Loaded %s objects from disk into the objectProcessorQueue.' % str(len(queryreturn)))


    def run(self):
        while True:
            objectType, data = shared.objectProcessorQueue.get()

            if objectType == 'getpubkey':
                self.processgetpubkey(data)
            elif objectType == 'pubkey':
                self.processpubkey(data)
            elif objectType == 'msg':
                self.processmsg(data)
            elif objectType == 'broadcast':
                self.processbroadcast(data)
            elif objectType == 'checkShutdownVariable': # is more of a command, not an object type. Is used to get this thread past the queue.get() so that it will check the shutdown variable.
                pass
            else:
                logger.critical('Error! Bug! The class_objectProcessor was passed an object type it doesn\'t recognize: %s' % str(objectType))

            with shared.objectProcessorQueueSizeLock:
                shared.objectProcessorQueueSize -= len(data) # We maintain objectProcessorQueueSize so that we will slow down requesting objects if too much data accumulates in the queue.

            if shared.shutdown:
                time.sleep(.5) # Wait just a moment for most of the connections to close
                numberOfObjectsThatWereInTheObjectProcessorQueue = 0
                with SqlBulkExecute() as sql:
                    while shared.objectProcessorQueueSize > 1:
                        objectType, data = shared.objectProcessorQueue.get()
                        sql.execute('''INSERT INTO objectprocessorqueue VALUES (?,?)''',
                                   objectType,data)
                        with shared.objectProcessorQueueSizeLock:
                            shared.objectProcessorQueueSize -= len(data) # We maintain objectProcessorQueueSize so that we will slow down requesting objects if too much data accumulates in the queue.
                        numberOfObjectsThatWereInTheObjectProcessorQueue += 1
                logger.debug('Saved %s objects from the objectProcessorQueue to disk. objectProcessorThread exiting.' % str(numberOfObjectsThatWereInTheObjectProcessorQueue))
                shared.shutdown = 2
                break
    
    def processgetpubkey(self, data):
        readPosition = 8  # bypass the nonce
        embeddedTime, = unpack('>I', data[readPosition:readPosition + 4])

        # This section is used for the transition from 32 bit time to 64 bit
        # time in the protocol.
        if embeddedTime == 0:
            embeddedTime, = unpack('>Q', data[readPosition:readPosition + 8])
            readPosition += 8
        else:
            readPosition += 4

        requestedAddressVersionNumber, addressVersionLength = decodeVarint(
            data[readPosition:readPosition + 10])
        readPosition += addressVersionLength
        streamNumber, streamNumberLength = decodeVarint(
            data[readPosition:readPosition + 10])
        readPosition += streamNumberLength

        if requestedAddressVersionNumber == 0:
            logger.debug('The requestedAddressVersionNumber of the pubkey request is zero. That doesn\'t make any sense. Ignoring it.')
            return
        elif requestedAddressVersionNumber == 1:
            logger.debug('The requestedAddressVersionNumber of the pubkey request is 1 which isn\'t supported anymore. Ignoring it.')
            return
        elif requestedAddressVersionNumber > 4:
            logger.debug('The requestedAddressVersionNumber of the pubkey request is too high. Can\'t understand. Ignoring it.')
            return

        myAddress = ''
        if requestedAddressVersionNumber <= 3 :
            requestedHash = data[readPosition:readPosition + 20]
            if len(requestedHash) != 20:
                logger.debug('The length of the requested hash is not 20 bytes. Something is wrong. Ignoring.')
                return
            logger.info('the hash requested in this getpubkey request is: %s' % requestedHash.encode('hex'))
            if requestedHash in shared.myAddressesByHash:  # if this address hash is one of mine
                myAddress = shared.myAddressesByHash[requestedHash]
        elif requestedAddressVersionNumber >= 4:
            requestedTag = data[readPosition:readPosition + 32]
            if len(requestedTag) != 32:
                logger.debug('The length of the requested tag is not 32 bytes. Something is wrong. Ignoring.')
                return
            logger.debug('the tag requested in this getpubkey request is: %s' % requestedTag.encode('hex'))
            if requestedTag in shared.myAddressesByTag:
                myAddress = shared.myAddressesByTag[requestedTag]

        if myAddress == '':
            logger.info('This getpubkey request is not for any of my keys.')
            return

        if decodeAddress(myAddress)[1] != requestedAddressVersionNumber:
            logger.warning('(Within the processgetpubkey function) Someone requested one of my pubkeys but the requestedAddressVersionNumber doesn\'t match my actual address version number. Ignoring.')
            return
        if decodeAddress(myAddress)[2] != streamNumber:
            logger.warning('(Within the processgetpubkey function) Someone requested one of my pubkeys but the stream number on which we heard this getpubkey object doesn\'t match this address\' stream number. Ignoring.')
            return
        if shared.safeConfigGetBoolean(myAddress, 'chan'):
            logger.info('Ignoring getpubkey request because it is for one of my chan addresses. The other party should already have the pubkey.')
            return
        try:
            lastPubkeySendTime = int(shared.config.get(
                myAddress, 'lastpubkeysendtime'))
        except:
            lastPubkeySendTime = 0
        if lastPubkeySendTime > time.time() - shared.lengthOfTimeToHoldOnToAllPubkeys:  # If the last time we sent our pubkey was more recent than 28 days ago...
            logger.info('Found getpubkey-requested-item in my list of EC hashes BUT we already sent it recently. Ignoring request. The lastPubkeySendTime is: %s' % lastPubkeySendTime) 
            return
        logger.info('Found getpubkey-requested-hash in my list of EC hashes. Telling Worker thread to do the POW for a pubkey message and send it out.') 
        if requestedAddressVersionNumber == 2:
            shared.workerQueue.put((
                'doPOWForMyV2Pubkey', requestedHash))
        elif requestedAddressVersionNumber == 3:
            shared.workerQueue.put((
                'sendOutOrStoreMyV3Pubkey', requestedHash))
        elif requestedAddressVersionNumber == 4:
            shared.workerQueue.put((
                'sendOutOrStoreMyV4Pubkey', myAddress))

    def processpubkey(self, data):
        pubkeyProcessingStartTime = time.time()
        shared.numberOfPubkeysProcessed += 1
        shared.UISignalQueue.put((
            'updateNumberOfPubkeysProcessed', 'no data'))
        readPosition = 8  # bypass the nonce
        embeddedTime, = unpack('>I', data[readPosition:readPosition + 4])

        # This section is used for the transition from 32 bit time to 64 bit
        # time in the protocol.
        if embeddedTime == 0:
            embeddedTime, = unpack('>Q', data[readPosition:readPosition + 8])
            readPosition += 8
        else:
            readPosition += 4

        addressVersion, varintLength = decodeVarint(
            data[readPosition:readPosition + 10])
        readPosition += varintLength
        streamNumber, varintLength = decodeVarint(
            data[readPosition:readPosition + 10])
        readPosition += varintLength
        if addressVersion == 0:
            logger.debug('(Within processpubkey) addressVersion of 0 doesn\'t make sense.')
            return
        if addressVersion > 4 or addressVersion == 1:
            logger.info('This version of Bitmessage cannot handle version %s addresses.' % addressVersion)
            return
        if addressVersion == 2:
            if len(data) < 146:  # sanity check. This is the minimum possible length.
                logger.debug('(within processpubkey) payloadLength less than 146. Sanity check failed.')
                return
            bitfieldBehaviors = data[readPosition:readPosition + 4]
            readPosition += 4
            publicSigningKey = data[readPosition:readPosition + 64]
            # Is it possible for a public key to be invalid such that trying to
            # encrypt or sign with it will cause an error? If it is, we should
            # probably test these keys here.
            readPosition += 64
            publicEncryptionKey = data[readPosition:readPosition + 64]
            if len(publicEncryptionKey) < 64:
                logger.debug('publicEncryptionKey length less than 64. Sanity check failed.')
                return
            sha = hashlib.new('sha512')
            sha.update(
                '\x04' + publicSigningKey + '\x04' + publicEncryptionKey)
            ripeHasher = hashlib.new('ripemd160')
            ripeHasher.update(sha.digest())
            ripe = ripeHasher.digest()


            logger.info('within recpubkey, addressVersion: %s, streamNumber: %s \n\
                        ripe %s\n\
                        publicSigningKey in hex: %s\n\
                        publicEncryptionKey in hex: %s' % (addressVersion, 
                                                           streamNumber, 
                                                           ripe.encode('hex'), 
                                                           publicSigningKey.encode('hex'), 
                                                           publicEncryptionKey.encode('hex')
                                                           )
                        )

            queryreturn = sqlQuery(
                '''SELECT usedpersonally FROM pubkeys WHERE hash=? AND addressversion=? AND usedpersonally='yes' ''', ripe, addressVersion)
            if queryreturn != []:  # if this pubkey is already in our database and if we have used it personally:
                logger.info('We HAVE used this pubkey personally. Updating time.')
                t = (ripe, addressVersion, data, embeddedTime, 'yes')
            else:
                logger.info('We have NOT used this pubkey personally. Inserting in database.')
                t = (ripe, addressVersion, data, embeddedTime, 'no')
                     # This will also update the embeddedTime.
            sqlExecute('''INSERT INTO pubkeys VALUES (?,?,?,?,?)''', *t)
            # shared.workerQueue.put(('newpubkey',(addressVersion,streamNumber,ripe)))
            self.possibleNewPubkey(ripe = ripe)
        if addressVersion == 3:
            if len(data) < 170:  # sanity check.
                logger.warning('(within processpubkey) payloadLength less than 170. Sanity check failed.')
                return
            bitfieldBehaviors = data[readPosition:readPosition + 4]
            readPosition += 4
            publicSigningKey = '\x04' + data[readPosition:readPosition + 64]
            # Is it possible for a public key to be invalid such that trying to
            # encrypt or sign with it will cause an error? If it is, we should
            # probably test these keys here.
            readPosition += 64
            publicEncryptionKey = '\x04' + data[readPosition:readPosition + 64]
            readPosition += 64
            specifiedNonceTrialsPerByte, specifiedNonceTrialsPerByteLength = decodeVarint(
                data[readPosition:readPosition + 10])
            readPosition += specifiedNonceTrialsPerByteLength
            specifiedPayloadLengthExtraBytes, specifiedPayloadLengthExtraBytesLength = decodeVarint(
                data[readPosition:readPosition + 10])
            readPosition += specifiedPayloadLengthExtraBytesLength
            endOfSignedDataPosition = readPosition
            signatureLength, signatureLengthLength = decodeVarint(
                data[readPosition:readPosition + 10])
            readPosition += signatureLengthLength
            signature = data[readPosition:readPosition + signatureLength]
            try:
                if not highlevelcrypto.verify(data[8:endOfSignedDataPosition], signature, publicSigningKey.encode('hex')):
                    logger.warning('ECDSA verify failed (within processpubkey)')
                    return
                logger.info('ECDSA verify passed (within processpubkey)')
            except Exception as err:
                logger.warning('ECDSA verify failed (within processpubkey) %s' % err)
                return

            sha = hashlib.new('sha512')
            sha.update(publicSigningKey + publicEncryptionKey)
            ripeHasher = hashlib.new('ripemd160')
            ripeHasher.update(sha.digest())
            ripe = ripeHasher.digest()
            

            logger.info('within recpubkey, addressVersion: %s, streamNumber: %s \n\
                        ripe %s\n\
                        publicSigningKey in hex: %s\n\
                        publicEncryptionKey in hex: %s' % (addressVersion, 
                                                           streamNumber, 
                                                           ripe.encode('hex'), 
                                                           publicSigningKey.encode('hex'), 
                                                           publicEncryptionKey.encode('hex')
                                                           )
                        )

            queryreturn = sqlQuery('''SELECT usedpersonally FROM pubkeys WHERE hash=? AND addressversion=? AND usedpersonally='yes' ''', ripe, addressVersion)
            if queryreturn != []:  # if this pubkey is already in our database and if we have used it personally:
                logger.info('We HAVE used this pubkey personally. Updating time.')
                t = (ripe, addressVersion, data, embeddedTime, 'yes')
            else:
                logger.info('We have NOT used this pubkey personally. Inserting in database.')
                t = (ripe, addressVersion, data, embeddedTime, 'no')
                     # This will also update the embeddedTime.
            sqlExecute('''INSERT INTO pubkeys VALUES (?,?,?,?,?)''', *t)
            self.possibleNewPubkey(ripe = ripe)

        if addressVersion == 4:
            """
            There exist a function: shared.decryptAndCheckPubkeyPayload which does something almost
            the same as this section of code. There are differences, however; one being that 
            decryptAndCheckPubkeyPayload requires that a cryptor object be created each time it is
            run which is an expensive operation. This, on the other hand, keeps them saved in 
            the shared.neededPubkeys dictionary so that if an attacker sends us many 
            incorrectly-tagged pubkeys, which would force us to try to decrypt them, this code 
            would run and handle that event quite quickly. 
            """ 
            if len(data) < 350:  # sanity check.
                logger.debug('(within processpubkey) payloadLength less than 350. Sanity check failed.')
                return
            signedData = data[8:readPosition] # Some of the signed data is not encrypted so let's keep it for now.
            tag = data[readPosition:readPosition + 32]
            readPosition += 32
            encryptedData = data[readPosition:]
            if tag not in shared.neededPubkeys:
                logger.info('We don\'t need this v4 pubkey. We didn\'t ask for it.')
                return

            # Let us try to decrypt the pubkey
            cryptorObject = shared.neededPubkeys[tag]
            try:
                decryptedData = cryptorObject.decrypt(encryptedData)
            except:
                # Someone must have encrypted some data with a different key
                # but tagged it with a tag for which we are watching.
                logger.info('Pubkey decryption was unsuccessful.')
                return

            readPosition = 0
            bitfieldBehaviors = decryptedData[readPosition:readPosition + 4]
            readPosition += 4
            publicSigningKey = '\x04' + decryptedData[readPosition:readPosition + 64]
            # Is it possible for a public key to be invalid such that trying to
            # encrypt or check a sig with it will cause an error? If it is, we
            # should probably test these keys here.
            readPosition += 64
            publicEncryptionKey = '\x04' + decryptedData[readPosition:readPosition + 64]
            readPosition += 64
            specifiedNonceTrialsPerByte, specifiedNonceTrialsPerByteLength = decodeVarint(
                decryptedData[readPosition:readPosition + 10])
            readPosition += specifiedNonceTrialsPerByteLength
            specifiedPayloadLengthExtraBytes, specifiedPayloadLengthExtraBytesLength = decodeVarint(
                decryptedData[readPosition:readPosition + 10])
            readPosition += specifiedPayloadLengthExtraBytesLength
            signedData += decryptedData[:readPosition]
            signatureLength, signatureLengthLength = decodeVarint(
                decryptedData[readPosition:readPosition + 10])
            readPosition += signatureLengthLength
            signature = decryptedData[readPosition:readPosition + signatureLength]
            try:
                if not highlevelcrypto.verify(signedData, signature, publicSigningKey.encode('hex')):
                    logger.info('ECDSA verify failed (within processpubkey)')
                    return
                logger.info('ECDSA verify passed (within processpubkey)')
            except Exception as err:
                logger.info('ECDSA verify failed (within processpubkey) %s' % err)
                return

            sha = hashlib.new('sha512')
            sha.update(publicSigningKey + publicEncryptionKey)
            ripeHasher = hashlib.new('ripemd160')
            ripeHasher.update(sha.digest())
            ripe = ripeHasher.digest()

            # We need to make sure that the tag on the outside of the encryption
            # is the one generated from hashing these particular keys.
            if tag != hashlib.sha512(hashlib.sha512(encodeVarint(addressVersion) + encodeVarint(streamNumber) + ripe).digest()).digest()[32:]:
                logger.info('Someone was trying to act malicious: tag doesn\'t match the keys in this pubkey message. Ignoring it.')
                return
            
            logger.info('within recpubkey, addressVersion: %s, streamNumber: %s \n\
                        ripe %s\n\
                        publicSigningKey in hex: %s\n\
                        publicEncryptionKey in hex: %s' % (addressVersion, 
                                                           streamNumber, 
                                                           ripe.encode('hex'), 
                                                           publicSigningKey.encode('hex'), 
                                                           publicEncryptionKey.encode('hex')
                                                           )
                        )

            t = (ripe, addressVersion, signedData, embeddedTime, 'yes')
            sqlExecute('''INSERT INTO pubkeys VALUES (?,?,?,?,?)''', *t)

            fromAddress = encodeAddress(addressVersion, streamNumber, ripe)
            # That this point we know that we have been waiting on this pubkey.
            # This function will command the workerThread to start work on
            # the messages that require it.
            self.possibleNewPubkey(address = fromAddress)

        # Display timing data
        timeRequiredToProcessPubkey = time.time(
        ) - pubkeyProcessingStartTime
        logger.debug('Time required to process this pubkey: %s' % timeRequiredToProcessPubkey)


    def processmsg(self, data):
        messageProcessingStartTime = time.time()
        shared.numberOfMessagesProcessed += 1
        shared.UISignalQueue.put((
            'updateNumberOfMessagesProcessed', 'no data'))
        readPosition = 8 # bypass the nonce
        embeddedTime, = unpack('>I', data[readPosition:readPosition + 4])

        # This section is used for the transition from 32 bit time to 64 bit
        # time in the protocol.
        if embeddedTime == 0:
            embeddedTime, = unpack('>Q', data[readPosition:readPosition + 8])
            readPosition += 8
        else:
            readPosition += 4
        streamNumberAsClaimedByMsg, streamNumberAsClaimedByMsgLength = decodeVarint(
            data[readPosition:readPosition + 9])
        readPosition += streamNumberAsClaimedByMsgLength
        inventoryHash = calculateInventoryHash(data)
        initialDecryptionSuccessful = False
        # Let's check whether this is a message acknowledgement bound for us.
        if data[readPosition:] in shared.ackdataForWhichImWatching:
            logger.info('This msg IS an acknowledgement bound for me.')
            del shared.ackdataForWhichImWatching[data[readPosition:]]
            sqlExecute('UPDATE sent SET status=? WHERE ackdata=?',
                       'ackreceived', data[readPosition:])
            shared.UISignalQueue.put(('updateSentItemStatusByAckdata', (data[readPosition:], tr.translateText("MainWindow",'Acknowledgement of the message received. %1').arg(unicode(
                time.strftime(shared.config.get('bitmessagesettings', 'timeformat'), time.localtime(int(time.time()))), 'utf-8')))))
            return
        else:
            logger.info('This was NOT an acknowledgement bound for me.')


        # This is not an acknowledgement bound for me. See if it is a message
        # bound for me by trying to decrypt it with my private keys.
        for key, cryptorObject in shared.myECCryptorObjects.items():
            try:
                decryptedData = cryptorObject.decrypt(
                    data[readPosition:])
                toRipe = key  # This is the RIPE hash of my pubkeys. We need this below to compare to the destination_ripe included in the encrypted data.
                initialDecryptionSuccessful = True
                logger.info('EC decryption successful using key associated with ripe hash: %s' % key.encode('hex')) 
                break
            except Exception as err:
                pass
                # print 'cryptorObject.decrypt Exception:', err
        if not initialDecryptionSuccessful:
            # This is not a message bound for me.
            logger.info('Length of time program spent failing to decrypt this message: %s seconds.' % (time.time() - messageProcessingStartTime,)) 
            return

        # This is a message bound for me.
        toAddress = shared.myAddressesByHash[
            toRipe]  # Look up my address based on the RIPE hash.
        readPosition = 0
        messageVersion, messageVersionLength = decodeVarint(
            decryptedData[readPosition:readPosition + 10])
        readPosition += messageVersionLength
        if messageVersion != 1:
            logger.info('Cannot understand message versions other than one. Ignoring message.') 
            return
        sendersAddressVersionNumber, sendersAddressVersionNumberLength = decodeVarint(
            decryptedData[readPosition:readPosition + 10])
        readPosition += sendersAddressVersionNumberLength
        if sendersAddressVersionNumber == 0:
            logger.info('Cannot understand sendersAddressVersionNumber = 0. Ignoring message.') 
            return
        if sendersAddressVersionNumber > 4:
            logger.info('Sender\'s address version number %s not yet supported. Ignoring message.' % sendersAddressVersionNumber)  
            return
        if len(decryptedData) < 170:
            logger.info('Length of the unencrypted data is unreasonably short. Sanity check failed. Ignoring message.')
            return
        sendersStreamNumber, sendersStreamNumberLength = decodeVarint(
            decryptedData[readPosition:readPosition + 10])
        if sendersStreamNumber == 0:
            logger.info('sender\'s stream number is 0. Ignoring message.')
            return
        readPosition += sendersStreamNumberLength
        behaviorBitfield = decryptedData[readPosition:readPosition + 4]
        readPosition += 4
        pubSigningKey = '\x04' + decryptedData[
            readPosition:readPosition + 64]
        readPosition += 64
        pubEncryptionKey = '\x04' + decryptedData[
            readPosition:readPosition + 64]
        readPosition += 64
        if sendersAddressVersionNumber >= 3:
            requiredAverageProofOfWorkNonceTrialsPerByte, varintLength = decodeVarint(
                decryptedData[readPosition:readPosition + 10])
            readPosition += varintLength
            logger.info('sender\'s requiredAverageProofOfWorkNonceTrialsPerByte is %s' % requiredAverageProofOfWorkNonceTrialsPerByte)
            requiredPayloadLengthExtraBytes, varintLength = decodeVarint(
                decryptedData[readPosition:readPosition + 10])
            readPosition += varintLength
            logger.info('sender\'s requiredPayloadLengthExtraBytes is %s' % requiredPayloadLengthExtraBytes)
        endOfThePublicKeyPosition = readPosition  # needed for when we store the pubkey in our database of pubkeys for later use.
        if toRipe != decryptedData[readPosition:readPosition + 20]:
            logger.info('The original sender of this message did not send it to you. Someone is attempting a Surreptitious Forwarding Attack.\n\
                See: http://world.std.com/~dtd/sign_encrypt/sign_encrypt7.html \n\
                your toRipe: %s\n\
                embedded destination toRipe: %s' % (toRipe.encode('hex'), decryptedData[readPosition:readPosition + 20].encode('hex'))
                       )
            return
        readPosition += 20
        messageEncodingType, messageEncodingTypeLength = decodeVarint(
            decryptedData[readPosition:readPosition + 10])
        readPosition += messageEncodingTypeLength
        messageLength, messageLengthLength = decodeVarint(
            decryptedData[readPosition:readPosition + 10])
        readPosition += messageLengthLength
        message = decryptedData[readPosition:readPosition + messageLength]
        # print 'First 150 characters of message:', repr(message[:150])
        readPosition += messageLength
        ackLength, ackLengthLength = decodeVarint(
            decryptedData[readPosition:readPosition + 10])
        readPosition += ackLengthLength
        ackData = decryptedData[readPosition:readPosition + ackLength]
        readPosition += ackLength
        positionOfBottomOfAckData = readPosition  # needed to mark the end of what is covered by the signature
        signatureLength, signatureLengthLength = decodeVarint(
            decryptedData[readPosition:readPosition + 10])
        readPosition += signatureLengthLength
        signature = decryptedData[
            readPosition:readPosition + signatureLength]
        try:
            if not highlevelcrypto.verify(decryptedData[:positionOfBottomOfAckData], signature, pubSigningKey.encode('hex')):
                logger.debug('ECDSA verify failed')
                return
            logger.debug('ECDSA verify passed')
        except Exception as err:
            logger.debug('ECDSA verify failed %s' % err)
            return
        logger.debug('As a matter of intellectual curiosity, here is the Bitcoin address associated with the keys owned by the other person: %s  ..and here is the testnet address: %s. The other person must take their private signing key from Bitmessage and import it into Bitcoin (or a service like Blockchain.info) for it to be of any use. Do not use this unless you know what you are doing.' %
                     (helper_bitcoin.calculateBitcoinAddressFromPubkey(pubSigningKey), helper_bitcoin.calculateTestnetAddressFromPubkey(pubSigningKey))
                     )

        # calculate the fromRipe.
        sha = hashlib.new('sha512')
        sha.update(pubSigningKey + pubEncryptionKey)
        ripe = hashlib.new('ripemd160')
        ripe.update(sha.digest())
        fromAddress = encodeAddress(
            sendersAddressVersionNumber, sendersStreamNumber, ripe.digest())
        # Let's store the public key in case we want to reply to this
        # person.
        if sendersAddressVersionNumber <= 3:
            sqlExecute(
                '''INSERT INTO pubkeys VALUES (?,?,?,?,?)''',
                ripe.digest(),
                sendersAddressVersionNumber,
                '\xFF\xFF\xFF\xFF\xFF\xFF\xFF\xFF' + '\xFF\xFF\xFF\xFF' + decryptedData[messageVersionLength:endOfThePublicKeyPosition],
                int(time.time()),
                'yes')
            # This will check to see whether we happen to be awaiting this
            # pubkey in order to send a message. If we are, it will do the POW
            # and send it.
            self.possibleNewPubkey(ripe=ripe.digest())
        elif sendersAddressVersionNumber >= 4:
            sqlExecute(
                '''INSERT INTO pubkeys VALUES (?,?,?,?,?)''',
                ripe.digest(),
                sendersAddressVersionNumber,
                '\x00\x00\x00\x00\x00\x00\x00\x01' + decryptedData[messageVersionLength:endOfThePublicKeyPosition],
                int(time.time()),
                'yes')
            # This will check to see whether we happen to be awaiting this
            # pubkey in order to send a message. If we are, it will do the POW
            # and send it.
            self.possibleNewPubkey(address = fromAddress)
        # If this message is bound for one of my version 3 addresses (or
        # higher), then we must check to make sure it meets our demanded
        # proof of work requirement. If this is bound for one of my chan
        # addresses then we skip this check; the minimum network POW is
        # fine.
        if decodeAddress(toAddress)[1] >= 3 and not shared.safeConfigGetBoolean(toAddress, 'chan'):  # If the toAddress version number is 3 or higher and not one of my chan addresses:
            if not shared.isAddressInMyAddressBookSubscriptionsListOrWhitelist(fromAddress):  # If I'm not friendly with this person:
                requiredNonceTrialsPerByte = shared.config.getint(
                    toAddress, 'noncetrialsperbyte')
                requiredPayloadLengthExtraBytes = shared.config.getint(
                    toAddress, 'payloadlengthextrabytes')
                if not shared.isProofOfWorkSufficient(data, requiredNonceTrialsPerByte, requiredPayloadLengthExtraBytes):
                    print 'Proof of work in msg message insufficient only because it does not meet our higher requirement.'
                    return
        blockMessage = False  # Gets set to True if the user shouldn't see the message according to black or white lists.
        if shared.config.get('bitmessagesettings', 'blackwhitelist') == 'black':  # If we are using a blacklist
            queryreturn = sqlQuery(
                '''SELECT label FROM blacklist where address=? and enabled='1' ''',
                fromAddress)
            if queryreturn != []:
                logger.info('Message ignored because address is in blacklist.')

                blockMessage = True
        else:  # We're using a whitelist
            queryreturn = sqlQuery(
                '''SELECT label FROM whitelist where address=? and enabled='1' ''',
                fromAddress)
            if queryreturn == []:
                logger.info('Message ignored because address not in whitelist.')
                blockMessage = True
        if not blockMessage:
            toLabel = shared.config.get(toAddress, 'label')
            if toLabel == '':
                toLabel = toAddress

            if messageEncodingType == 2:
                subject, body = self.decodeType2Message(message)
                logger.info('Message subject (first 100 characters): %s' % repr(subject)[:100])
            elif messageEncodingType == 1:
                body = message
                subject = ''
            elif messageEncodingType == 0:
                logger.info('messageEncodingType == 0. Doing nothing with the message. They probably just sent it so that we would store their public key or send their ack data for them.') 
            else:
                body = 'Unknown encoding type.\n\n' + repr(message)
                subject = ''
            if messageEncodingType != 0:
                t = (inventoryHash, toAddress, fromAddress, subject, int(
                    time.time()), body, 'inbox', messageEncodingType, 0)
                helper_inbox.insert(t)

                shared.UISignalQueue.put(('displayNewInboxMessage', (
                    inventoryHash, toAddress, fromAddress, subject, body)))

            # If we are behaving as an API then we might need to run an
            # outside command to let some program know that a new message
            # has arrived.
            if shared.safeConfigGetBoolean('bitmessagesettings', 'apienabled'):
                try:
                    apiNotifyPath = shared.config.get(
                        'bitmessagesettings', 'apinotifypath')
                except:
                    apiNotifyPath = ''
                if apiNotifyPath != '':
                    call([apiNotifyPath, "newMessage"])

            # Let us now check and see whether our receiving address is
            # behaving as a mailing list
            if shared.safeConfigGetBoolean(toAddress, 'mailinglist'):
                try:
                    mailingListName = shared.config.get(
                        toAddress, 'mailinglistname')
                except:
                    mailingListName = ''
                # Let us send out this message as a broadcast
                subject = self.addMailingListNameToSubject(
                    subject, mailingListName)
                # Let us now send this message out as a broadcast
                message = time.strftime("%a, %Y-%m-%d %H:%M:%S UTC", time.gmtime(
                )) + '   Message ostensibly from ' + fromAddress + ':\n\n' + body
                fromAddress = toAddress  # The fromAddress for the broadcast that we are about to send is the toAddress (my address) for the msg message we are currently processing.
                ackdataForBroadcast = OpenSSL.rand(
                    32)  # We don't actually need the ackdataForBroadcast for acknowledgement since this is a broadcast message but we can use it to update the user interface when the POW is done generating.
                toAddress = '[Broadcast subscribers]'
                ripe = ''

                t = ('', toAddress, ripe, fromAddress, subject, message, ackdataForBroadcast, int(
                    time.time()), 'broadcastqueued', 1, 1, 'sent', 2)
                helper_sent.insert(t)

                shared.UISignalQueue.put(('displayNewSentMessage', (
                    toAddress, '[Broadcast subscribers]', fromAddress, subject, message, ackdataForBroadcast)))
                shared.workerQueue.put(('sendbroadcast', ''))

        if self.ackDataHasAVaildHeader(ackData):
            if ackData[4:16] == 'getpubkey\x00\x00\x00':
                shared.checkAndSharegetpubkeyWithPeers(ackData[24:])
            elif ackData[4:16] == 'pubkey\x00\x00\x00\x00\x00\x00':
                shared.checkAndSharePubkeyWithPeers(ackData[24:])
            elif ackData[4:16] == 'msg\x00\x00\x00\x00\x00\x00\x00\x00\x00':
                shared.checkAndShareMsgWithPeers(ackData[24:])
            elif ackData[4:16] == 'broadcast\x00\x00\x00':
                shared.checkAndShareBroadcastWithPeers(ackData[24:])

        # Display timing data
        timeRequiredToAttemptToDecryptMessage = time.time(
        ) - messageProcessingStartTime
        shared.successfullyDecryptMessageTimings.append(
            timeRequiredToAttemptToDecryptMessage)
        sum = 0
        for item in shared.successfullyDecryptMessageTimings:
            sum += item
        logger.debug('Time to decrypt this message successfully: %s\n\
                     Average time for all message decryption successes since startup: %s.' %
                     (timeRequiredToAttemptToDecryptMessage, sum / len(shared.successfullyDecryptMessageTimings)) 
                     )


    def processbroadcast(self, data):
        messageProcessingStartTime = time.time()
        shared.numberOfBroadcastsProcessed += 1
        shared.UISignalQueue.put((
            'updateNumberOfBroadcastsProcessed', 'no data'))
        inventoryHash = calculateInventoryHash(data)
        readPosition = 8  # bypass the nonce
        embeddedTime, = unpack('>I', data[readPosition:readPosition + 4])

        # This section is used for the transition from 32 bit time to 64 bit
        # time in the protocol.
        if embeddedTime == 0:
            embeddedTime, = unpack('>Q', data[readPosition:readPosition + 8])
            readPosition += 8
        else:
            readPosition += 4

        broadcastVersion, broadcastVersionLength = decodeVarint(
            data[readPosition:readPosition + 9])
        readPosition += broadcastVersionLength
        if broadcastVersion < 1 or broadcastVersion > 3:
            logger.debug('Cannot decode incoming broadcast versions higher than 3. Assuming the sender isn\'t being silly, you should upgrade Bitmessage because this message shall be ignored.') 
            return
        if broadcastVersion == 1:
            beginningOfPubkeyPosition = readPosition  # used when we add the pubkey to our pubkey table
            sendersAddressVersion, sendersAddressVersionLength = decodeVarint(
                data[readPosition:readPosition + 9])
            if sendersAddressVersion <= 1 or sendersAddressVersion >= 3:
                # Cannot decode senderAddressVersion higher than 2. Assuming
                # the sender isn\'t being silly, you should upgrade Bitmessage
                # because this message shall be ignored.
                return
            readPosition += sendersAddressVersionLength
            if sendersAddressVersion == 2:
                sendersStream, sendersStreamLength = decodeVarint(
                    data[readPosition:readPosition + 9])
                readPosition += sendersStreamLength
                behaviorBitfield = data[readPosition:readPosition + 4]
                readPosition += 4
                sendersPubSigningKey = '\x04' + \
                    data[readPosition:readPosition + 64]
                readPosition += 64
                sendersPubEncryptionKey = '\x04' + \
                    data[readPosition:readPosition + 64]
                readPosition += 64
                endOfPubkeyPosition = readPosition
                sendersHash = data[readPosition:readPosition + 20]
                if sendersHash not in shared.broadcastSendersForWhichImWatching:
                    # Display timing data
                    logger.debug('Time spent deciding that we are not interested in this v1 broadcast: %s' % (time.time() - messageProcessingStartTime,))
                    return
                # At this point, this message claims to be from sendersHash and
                # we are interested in it. We still have to hash the public key
                # to make sure it is truly the key that matches the hash, and
                # also check the signiture.
                readPosition += 20

                sha = hashlib.new('sha512')
                sha.update(sendersPubSigningKey + sendersPubEncryptionKey)
                ripe = hashlib.new('ripemd160')
                ripe.update(sha.digest())
                if ripe.digest() != sendersHash:
                    # The sender of this message lied.
                    return
                messageEncodingType, messageEncodingTypeLength = decodeVarint(
                    data[readPosition:readPosition + 9])
                if messageEncodingType == 0:
                    return
                readPosition += messageEncodingTypeLength
                messageLength, messageLengthLength = decodeVarint(
                    data[readPosition:readPosition + 9])
                readPosition += messageLengthLength
                message = data[readPosition:readPosition + messageLength]
                readPosition += messageLength
                readPositionAtBottomOfMessage = readPosition
                signatureLength, signatureLengthLength = decodeVarint(
                    data[readPosition:readPosition + 9])
                readPosition += signatureLengthLength
                signature = data[readPosition:readPosition + signatureLength]
                try:
                    if not highlevelcrypto.verify(data[12:readPositionAtBottomOfMessage], signature, sendersPubSigningKey.encode('hex')):
                        logger.debug('ECDSA verify failed')
                        return
                    logger.debug('ECDSA verify passed')
                except Exception as err:
                    logger.debug('ECDSA verify failed %s' % err)
                    return
                # verify passed
                fromAddress = encodeAddress(
                    sendersAddressVersion, sendersStream, ripe.digest())
                logger.debug('fromAddress: %s' % fromAddress)

                # Let's store the public key in case we want to reply to this person.
                # We don't have the correct nonce or time (which would let us
                # send out a pubkey message) so we'll just fill it with 1's. We
                # won't be able to send this pubkey to others (without doing
                # the proof of work ourselves, which this program is programmed
                # to not do.)
                sqlExecute(
                    '''INSERT INTO pubkeys VALUES (?,?,?,?,?)''',
                    ripe.digest(),
                    sendersAddressVersion,
                    '\xFF\xFF\xFF\xFF\xFF\xFF\xFF\xFF' + '\xFF\xFF\xFF\xFF' + data[beginningOfPubkeyPosition:endOfPubkeyPosition],
                    int(time.time()),
                    'yes')
                # This will check to see whether we happen to be awaiting this
                # pubkey in order to send a message. If we are, it will do the
                # POW and send it.
                self.possibleNewPubkey(ripe=ripe.digest())


                if messageEncodingType == 2:
                    subject, body = decodeType2Message(message)
                    logger.info('Broadcast subject (first 100 characters): %s' % repr(subject)[:100])
                elif messageEncodingType == 1:
                    body = message
                    subject = ''
                elif messageEncodingType == 0:
                    logger.debug('messageEncodingType == 0. Doing nothing with the message.')
                else:
                    body = 'Unknown encoding type.\n\n' + repr(message)
                    subject = ''

                toAddress = '[Broadcast subscribers]'
                if messageEncodingType != 0:

                    t = (inventoryHash, toAddress, fromAddress, subject, int(
                        time.time()), body, 'inbox', messageEncodingType, 0)
                    helper_inbox.insert(t)

                    shared.UISignalQueue.put(('displayNewInboxMessage', (
                        inventoryHash, toAddress, fromAddress, subject, body)))

                    # If we are behaving as an API then we might need to run an
                    # outside command to let some program know that a new
                    # message has arrived.
                    if shared.safeConfigGetBoolean('bitmessagesettings', 'apienabled'):
                        try:
                            apiNotifyPath = shared.config.get(
                                'bitmessagesettings', 'apinotifypath')
                        except:
                            apiNotifyPath = ''
                        if apiNotifyPath != '':
                            call([apiNotifyPath, "newBroadcast"])

                # Display timing data
                logger.debug('Time spent processing this interesting broadcast: %s' % (time.time() - messageProcessingStartTime,))

        if broadcastVersion == 2:
            cleartextStreamNumber, cleartextStreamNumberLength = decodeVarint(
                data[readPosition:readPosition + 10])
            readPosition += cleartextStreamNumberLength
            initialDecryptionSuccessful = False
            for key, cryptorObject in shared.MyECSubscriptionCryptorObjects.items():
                try:
                    decryptedData = cryptorObject.decrypt(data[readPosition:])
                    toRipe = key  # This is the RIPE hash of the sender's pubkey. We need this below to compare to the RIPE hash of the sender's address to verify that it was encrypted by with their key rather than some other key.
                    initialDecryptionSuccessful = True
                    logger.info('EC decryption successful using key associated with ripe hash: %s' % key.encode('hex'))
                    break
                except Exception as err:
                    pass
                    # print 'cryptorObject.decrypt Exception:', err
            if not initialDecryptionSuccessful:
                # This is not a broadcast I am interested in.
                logger.debug('Length of time program spent failing to decrypt this v2 broadcast: %s seconds.' % (time.time() - messageProcessingStartTime,))
                return
            # At this point this is a broadcast I have decrypted and thus am
            # interested in.
            signedBroadcastVersion, readPosition = decodeVarint(
                decryptedData[:10])
            beginningOfPubkeyPosition = readPosition  # used when we add the pubkey to our pubkey table
            sendersAddressVersion, sendersAddressVersionLength = decodeVarint(
                decryptedData[readPosition:readPosition + 9])
            if sendersAddressVersion < 2 or sendersAddressVersion > 3:
                logger.info('Cannot decode senderAddressVersion other than 2 or 3. Assuming the sender isn\'t being silly, you should upgrade Bitmessage because this message shall be ignored.')
                return
            readPosition += sendersAddressVersionLength
            sendersStream, sendersStreamLength = decodeVarint(
                decryptedData[readPosition:readPosition + 9])
            if sendersStream != cleartextStreamNumber:
                logger.info('The stream number outside of the encryption on which the POW was completed doesn\'t match the stream number inside the encryption. Ignoring broadcast.') 
                return
            readPosition += sendersStreamLength
            behaviorBitfield = decryptedData[readPosition:readPosition + 4]
            readPosition += 4
            sendersPubSigningKey = '\x04' + \
                decryptedData[readPosition:readPosition + 64]
            readPosition += 64
            sendersPubEncryptionKey = '\x04' + \
                decryptedData[readPosition:readPosition + 64]
            readPosition += 64
            if sendersAddressVersion >= 3:
                requiredAverageProofOfWorkNonceTrialsPerByte, varintLength = decodeVarint(
                    decryptedData[readPosition:readPosition + 10])
                readPosition += varintLength
                logger.debug('sender\'s requiredAverageProofOfWorkNonceTrialsPerByte is %s' % requiredAverageProofOfWorkNonceTrialsPerByte)
                requiredPayloadLengthExtraBytes, varintLength = decodeVarint(
                    decryptedData[readPosition:readPosition + 10])
                readPosition += varintLength
                logger.debug('sender\'s requiredPayloadLengthExtraBytes is %s' % requiredPayloadLengthExtraBytes)
            endOfPubkeyPosition = readPosition

            sha = hashlib.new('sha512')
            sha.update(sendersPubSigningKey + sendersPubEncryptionKey)
            ripe = hashlib.new('ripemd160')
            ripe.update(sha.digest())

            if toRipe != ripe.digest():
                logger.info('The encryption key used to encrypt this message doesn\'t match the keys inbedded in the message itself. Ignoring message.') 
                return
            messageEncodingType, messageEncodingTypeLength = decodeVarint(
                decryptedData[readPosition:readPosition + 9])
            if messageEncodingType == 0:
                return
            readPosition += messageEncodingTypeLength
            messageLength, messageLengthLength = decodeVarint(
                decryptedData[readPosition:readPosition + 9])
            readPosition += messageLengthLength
            message = decryptedData[readPosition:readPosition + messageLength]
            readPosition += messageLength
            readPositionAtBottomOfMessage = readPosition
            signatureLength, signatureLengthLength = decodeVarint(
                decryptedData[readPosition:readPosition + 9])
            readPosition += signatureLengthLength
            signature = decryptedData[
                readPosition:readPosition + signatureLength]
            try:
                if not highlevelcrypto.verify(decryptedData[:readPositionAtBottomOfMessage], signature, sendersPubSigningKey.encode('hex')):
                    logger.debug('ECDSA verify failed')
                    return
                logger.debug('ECDSA verify passed')
            except Exception as err:
                logger.debug('ECDSA verify failed %s' % err)
                return
            # verify passed

            # Let's store the public key in case we want to reply to this
            # person.
            sqlExecute('''INSERT INTO pubkeys VALUES (?,?,?,?,?)''',
                       ripe.digest(),
                       sendersAddressVersion,
                       '\xFF\xFF\xFF\xFF\xFF\xFF\xFF\xFF' + '\xFF\xFF\xFF\xFF' + decryptedData[beginningOfPubkeyPosition:endOfPubkeyPosition],
                       int(time.time()),
                       'yes')
            # shared.workerQueue.put(('newpubkey',(sendersAddressVersion,sendersStream,ripe.digest())))
            # This will check to see whether we happen to be awaiting this
            # pubkey in order to send a message. If we are, it will do the POW
            # and send it.
            self.possibleNewPubkey(ripe=ripe.digest())

            fromAddress = encodeAddress(
                sendersAddressVersion, sendersStream, ripe.digest())
            with shared.printLock:
                print 'fromAddress:', fromAddress

            if messageEncodingType == 2:
                subject, body = self.decodeType2Message(message)
                logger.info('Broadcast subject (first 100 characters): %s' % repr(subject)[:100])
            elif messageEncodingType == 1:
                body = message
                subject = ''
            elif messageEncodingType == 0:
                logger.info('messageEncodingType == 0. Doing nothing with the message.')
            else:
                body = 'Unknown encoding type.\n\n' + repr(message)
                subject = ''

            toAddress = '[Broadcast subscribers]'
            if messageEncodingType != 0:

                t = (inventoryHash, toAddress, fromAddress, subject, int(
                    time.time()), body, 'inbox', messageEncodingType, 0)
                helper_inbox.insert(t)

                shared.UISignalQueue.put(('displayNewInboxMessage', (
                    inventoryHash, toAddress, fromAddress, subject, body)))

                # If we are behaving as an API then we might need to run an
                # outside command to let some program know that a new message
                # has arrived.
                if shared.safeConfigGetBoolean('bitmessagesettings', 'apienabled'):
                    try:
                        apiNotifyPath = shared.config.get(
                            'bitmessagesettings', 'apinotifypath')
                    except:
                        apiNotifyPath = ''
                    if apiNotifyPath != '':
                        call([apiNotifyPath, "newBroadcast"])

            # Display timing data
            logger.info('Time spent processing this interesting broadcast: %s' % (time.time() - messageProcessingStartTime,))

        if broadcastVersion == 3:
            cleartextStreamNumber, cleartextStreamNumberLength = decodeVarint(
                data[readPosition:readPosition + 10])
            readPosition += cleartextStreamNumberLength
            embeddedTag = data[readPosition:readPosition+32]
            readPosition += 32
            if embeddedTag not in shared.MyECSubscriptionCryptorObjects:
                logger.debug('We\'re not interested in this broadcast.') 
                return
            # We are interested in this broadcast because of its tag.
            cryptorObject = shared.MyECSubscriptionCryptorObjects[embeddedTag]
            try:
                decryptedData = cryptorObject.decrypt(data[readPosition:])
                logger.debug('EC decryption successful')
            except Exception as err:
                logger.debug('Broadcast version 3 decryption Unsuccessful.') 
                return

            signedBroadcastVersion, readPosition = decodeVarint(
                decryptedData[:10])
            beginningOfPubkeyPosition = readPosition  # used when we add the pubkey to our pubkey table
            sendersAddressVersion, sendersAddressVersionLength = decodeVarint(
                decryptedData[readPosition:readPosition + 9])
            if sendersAddressVersion < 4:
                logger.info('Cannot decode senderAddressVersion less than 4 for broadcast version number 3. Assuming the sender isn\'t being silly, you should upgrade Bitmessage because this message shall be ignored.') 
                return
            readPosition += sendersAddressVersionLength
            sendersStream, sendersStreamLength = decodeVarint(
                decryptedData[readPosition:readPosition + 9])
            if sendersStream != cleartextStreamNumber:
                logger.info('The stream number outside of the encryption on which the POW was completed doesn\'t match the stream number inside the encryption. Ignoring broadcast.') 
                return
            readPosition += sendersStreamLength
            behaviorBitfield = decryptedData[readPosition:readPosition + 4]
            readPosition += 4
            sendersPubSigningKey = '\x04' + \
                decryptedData[readPosition:readPosition + 64]
            readPosition += 64
            sendersPubEncryptionKey = '\x04' + \
                decryptedData[readPosition:readPosition + 64]
            readPosition += 64
            if sendersAddressVersion >= 3:
                requiredAverageProofOfWorkNonceTrialsPerByte, varintLength = decodeVarint(
                    decryptedData[readPosition:readPosition + 10])
                readPosition += varintLength
                logger.debug('sender\'s requiredAverageProofOfWorkNonceTrialsPerByte is %s' % requiredAverageProofOfWorkNonceTrialsPerByte)
                requiredPayloadLengthExtraBytes, varintLength = decodeVarint(
                    decryptedData[readPosition:readPosition + 10])
                readPosition += varintLength
                logger.debug('sender\'s requiredPayloadLengthExtraBytes is %s' % requiredPayloadLengthExtraBytes)
            endOfPubkeyPosition = readPosition

            sha = hashlib.new('sha512')
            sha.update(sendersPubSigningKey + sendersPubEncryptionKey)
            ripeHasher = hashlib.new('ripemd160')
            ripeHasher.update(sha.digest())
            calculatedRipe = ripeHasher.digest()

            calculatedTag = hashlib.sha512(hashlib.sha512(encodeVarint(
                sendersAddressVersion) + encodeVarint(sendersStream) + calculatedRipe).digest()).digest()[32:]
            if calculatedTag != embeddedTag:
                logger.debug('The tag and encryption key used to encrypt this message doesn\'t match the keys inbedded in the message itself. Ignoring message.') 
                return
            messageEncodingType, messageEncodingTypeLength = decodeVarint(
                decryptedData[readPosition:readPosition + 9])
            if messageEncodingType == 0:
                return
            readPosition += messageEncodingTypeLength
            messageLength, messageLengthLength = decodeVarint(
                decryptedData[readPosition:readPosition + 9])
            readPosition += messageLengthLength
            message = decryptedData[readPosition:readPosition + messageLength]
            readPosition += messageLength
            readPositionAtBottomOfMessage = readPosition
            signatureLength, signatureLengthLength = decodeVarint(
                decryptedData[readPosition:readPosition + 9])
            readPosition += signatureLengthLength
            signature = decryptedData[
                readPosition:readPosition + signatureLength]
            try:
                if not highlevelcrypto.verify(decryptedData[:readPositionAtBottomOfMessage], signature, sendersPubSigningKey.encode('hex')):
                    logger.debug('ECDSA verify failed')
                    return
                logger.debug('ECDSA verify passed')
            except Exception as err:
                logger.debug('ECDSA verify failed %s' % err)
                return
            # verify passed

            fromAddress = encodeAddress(
                sendersAddressVersion, sendersStream, calculatedRipe)
            logger.info('fromAddress: %s' % fromAddress)

            # Let's store the public key in case we want to reply to this person.
            sqlExecute(
                '''INSERT INTO pubkeys VALUES (?,?,?,?,?)''',
                calculatedRipe,
                sendersAddressVersion,
                '\x00\x00\x00\x00\x00\x00\x00\x01' + decryptedData[beginningOfPubkeyPosition:endOfPubkeyPosition],
                int(time.time()),
                'yes')
            # This will check to see whether we happen to be awaiting this
            # pubkey in order to send a message. If we are, it will do the
            # POW and send it.
            self.possibleNewPubkey(address = fromAddress)

            if messageEncodingType == 2:
                subject, body = self.decodeType2Message(message)
                logger.info('Broadcast subject (first 100 characters): %s' % repr(subject)[:100])
            elif messageEncodingType == 1:
                body = message
                subject = ''
            elif messageEncodingType == 0:
                logger.info('messageEncodingType == 0. Doing nothing with the message.')
            else:
                body = 'Unknown encoding type.\n\n' + repr(message)
                subject = ''

            toAddress = '[Broadcast subscribers]'
            if messageEncodingType != 0:

                t = (inventoryHash, toAddress, fromAddress, subject, int(
                    time.time()), body, 'inbox', messageEncodingType, 0)
                helper_inbox.insert(t)

                shared.UISignalQueue.put(('displayNewInboxMessage', (
                    inventoryHash, toAddress, fromAddress, subject, body)))

                # If we are behaving as an API then we might need to run an
                # outside command to let some program know that a new message
                # has arrived.
                if shared.safeConfigGetBoolean('bitmessagesettings', 'apienabled'):
                    try:
                        apiNotifyPath = shared.config.get(
                            'bitmessagesettings', 'apinotifypath')
                    except:
                        apiNotifyPath = ''
                    if apiNotifyPath != '':
                        call([apiNotifyPath, "newBroadcast"])

            # Display timing data
            logger.debug('Time spent processing this interesting broadcast: %s' % (time.time() - messageProcessingStartTime,))

    # We have inserted a pubkey into our pubkey table which we received from a
    # pubkey, msg, or broadcast message. It might be one that we have been
    # waiting for. Let's check.
    def possibleNewPubkey(self, ripe=None, address=None):
        # For address versions <= 3, we wait on a key with the correct ripe hash
        if ripe != None:
            if ripe in shared.neededPubkeys:
                logger.info('We have been awaiting the arrival of this pubkey.')
                del shared.neededPubkeys[ripe]
                sqlExecute(
                    '''UPDATE sent SET status='doingmsgpow' WHERE toripe=? AND (status='awaitingpubkey' or status='doingpubkeypow') and folder='sent' ''',
                    ripe)
                shared.workerQueue.put(('sendmessage', ''))
            else:
                logger.debug('We don\'t need this pub key. We didn\'t ask for it. Pubkey hash: %s' % ripe.encode('hex'))
        # For address versions >= 4, we wait on a pubkey with the correct tag.
        # Let us create the tag from the address and see if we were waiting
        # for it.
        elif address != None:
            status, addressVersion, streamNumber, ripe = decodeAddress(address)
            tag = hashlib.sha512(hashlib.sha512(encodeVarint(
                addressVersion) + encodeVarint(streamNumber) + ripe).digest()).digest()[32:]
            if tag in shared.neededPubkeys:
                logger.info('We have been awaiting the arrival of this pubkey.')
                del shared.neededPubkeys[tag]
                sqlExecute(
                    '''UPDATE sent SET status='doingmsgpow' WHERE toripe=? AND (status='awaitingpubkey' or status='doingpubkeypow') and folder='sent' ''',
                    ripe)
                shared.workerQueue.put(('sendmessage', ''))

    def ackDataHasAVaildHeader(self, ackData):
        if len(ackData) < 24:
            logger.info('The length of ackData is unreasonably short. Not sending ackData.')
            return False
        if ackData[0:4] != '\xe9\xbe\xb4\xd9':
            logger.info('Ackdata magic bytes were wrong. Not sending ackData.')
            return False
        ackDataPayloadLength, = unpack('>L', ackData[16:20])
        if len(ackData) - 24 != ackDataPayloadLength:
            logger.info('ackData payload length doesn\'t match the payload length specified in the header. Not sending ackdata.')
            return False
        if ackData[20:24] != hashlib.sha512(ackData[24:]).digest()[0:4]:  # test the checksum in the message.
            logger.info('ackdata checksum wrong. Not sending ackdata.')
            return False
        if ackDataPayloadLength > 180000000: # If the size of the message is greater than 180MB, ignore it.
            return False
        if (ackData[4:16] != 'getpubkey\x00\x00\x00' and
            ackData[4:16] != 'pubkey\x00\x00\x00\x00\x00\x00' and
            ackData[4:16] != 'msg\x00\x00\x00\x00\x00\x00\x00\x00\x00' and
            ackData[4:16] != 'broadcast\x00\x00\x00'):
            return False
        return True

    def decodeType2Message(self, message):
        bodyPositionIndex = string.find(message, '\nBody:')
        if bodyPositionIndex > 1:
            subject = message[8:bodyPositionIndex]
            # Only save and show the first 500 characters of the subject.
            # Any more is probably an attack.
            subject = subject[:500]
            body = message[bodyPositionIndex + 6:]
        else:
            subject = ''
            body = message
        # Throw away any extra lines (headers) after the subject.
        if subject:
            subject = subject.splitlines()[0]
        return subject, body

    def addMailingListNameToSubject(self, subject, mailingListName):
        subject = subject.strip()
        if subject[:3] == 'Re:' or subject[:3] == 'RE:':
            subject = subject[3:].strip()
        if '[' + mailingListName + ']' in subject:
            return subject
        else:
            return '[' + mailingListName + '] ' + subject

    def decodeType2Message(self, message):
        bodyPositionIndex = string.find(message, '\nBody:')
        if bodyPositionIndex > 1:
            subject = message[8:bodyPositionIndex]
            # Only save and show the first 500 characters of the subject.
            # Any more is probably an attack.
            subject = subject[:500]
            body = message[bodyPositionIndex + 6:]
        else:
            subject = ''
            body = message
        # Throw away any extra lines (headers) after the subject.
        if subject:
            subject = subject.splitlines()[0]
        return subject, body
########NEW FILE########
__FILENAME__ = class_outgoingSynSender
import threading
import time
import random
import shared
import socks
import socket
import sys
import tr

from class_sendDataThread import *
from class_receiveDataThread import *

# For each stream to which we connect, several outgoingSynSender threads
# will exist and will collectively create 8 connections with peers.

class outgoingSynSender(threading.Thread):

    def __init__(self):
        threading.Thread.__init__(self)

    def setup(self, streamNumber, selfInitiatedConnections):
        self.streamNumber = streamNumber
        self.selfInitiatedConnections = selfInitiatedConnections

    def _getPeer(self):
        # If the user has specified a trusted peer then we'll only
        # ever connect to that. Otherwise we'll pick a random one from
        # the known nodes
        shared.knownNodesLock.acquire()
        if shared.trustedPeer:
            peer = shared.trustedPeer
            shared.knownNodes[self.streamNumber][peer] = time.time()
        else:
            peer, = random.sample(shared.knownNodes[self.streamNumber], 1)
        shared.knownNodesLock.release()

        return peer

    def run(self):
        while shared.safeConfigGetBoolean('bitmessagesettings', 'dontconnect'):
            time.sleep(2)
        while shared.safeConfigGetBoolean('bitmessagesettings', 'sendoutgoingconnections'):
            maximumConnections = 1 if shared.trustedPeer else 8 # maximum number of outgoing connections = 8
            while len(self.selfInitiatedConnections[self.streamNumber]) >= maximumConnections:
                time.sleep(10)
            if shared.shutdown:
                break
            random.seed()
            peer = self._getPeer()
            shared.alreadyAttemptedConnectionsListLock.acquire()
            while peer in shared.alreadyAttemptedConnectionsList or peer.host in shared.connectedHostsList:
                shared.alreadyAttemptedConnectionsListLock.release()
                # print 'choosing new sample'
                random.seed()
                peer = self._getPeer()
                time.sleep(1)
                # Clear out the shared.alreadyAttemptedConnectionsList every half
                # hour so that this program will again attempt a connection
                # to any nodes, even ones it has already tried.
                if (time.time() - shared.alreadyAttemptedConnectionsListResetTime) > 1800:
                    shared.alreadyAttemptedConnectionsList.clear()
                    shared.alreadyAttemptedConnectionsListResetTime = int(
                        time.time())
                shared.alreadyAttemptedConnectionsListLock.acquire()
            shared.alreadyAttemptedConnectionsList[peer] = 0
            shared.alreadyAttemptedConnectionsListLock.release()
            timeNodeLastSeen = shared.knownNodes[
                self.streamNumber][peer]
            if peer.host.find(':') == -1:
                address_family = socket.AF_INET
            else:
                address_family = socket.AF_INET6
            try:
                sock = socks.socksocket(address_family, socket.SOCK_STREAM)
            except:
                """
                The line can fail on Windows systems which aren't
                64-bit compatiable:
                      File "C:\Python27\lib\socket.py", line 187, in __init__
                        _sock = _realsocket(family, type, proto)
                      error: [Errno 10047] An address incompatible with the requested protocol was used
                      
                So let us remove the offending address from our knownNodes file.
                """
                shared.knownNodesLock.acquire()
                del shared.knownNodes[self.streamNumber][peer]
                shared.knownNodesLock.release()
                with shared.printLock:
                    print 'deleting ', peer, 'from shared.knownNodes because it caused a socks.socksocket exception. We must not be 64-bit compatible.'
                continue
            # This option apparently avoids the TIME_WAIT state so that we
            # can rebind faster
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            sock.settimeout(20)
            if shared.config.get('bitmessagesettings', 'socksproxytype') == 'none' and shared.verbose >= 2:
                with shared.printLock:
                    print 'Trying an outgoing connection to', peer

                # sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            elif shared.config.get('bitmessagesettings', 'socksproxytype') == 'SOCKS4a':
                if shared.verbose >= 2:
                    with shared.printLock:
                        print '(Using SOCKS4a) Trying an outgoing connection to', peer

                proxytype = socks.PROXY_TYPE_SOCKS4
                sockshostname = shared.config.get(
                    'bitmessagesettings', 'sockshostname')
                socksport = shared.config.getint(
                    'bitmessagesettings', 'socksport')
                rdns = True  # Do domain name lookups through the proxy; though this setting doesn't really matter since we won't be doing any domain name lookups anyway.
                if shared.config.getboolean('bitmessagesettings', 'socksauthentication'):
                    socksusername = shared.config.get(
                        'bitmessagesettings', 'socksusername')
                    sockspassword = shared.config.get(
                        'bitmessagesettings', 'sockspassword')
                    sock.setproxy(
                        proxytype, sockshostname, socksport, rdns, socksusername, sockspassword)
                else:
                    sock.setproxy(
                        proxytype, sockshostname, socksport, rdns)
            elif shared.config.get('bitmessagesettings', 'socksproxytype') == 'SOCKS5':
                if shared.verbose >= 2:
                    with shared.printLock:
                        print '(Using SOCKS5) Trying an outgoing connection to', peer

                proxytype = socks.PROXY_TYPE_SOCKS5
                sockshostname = shared.config.get(
                    'bitmessagesettings', 'sockshostname')
                socksport = shared.config.getint(
                    'bitmessagesettings', 'socksport')
                rdns = True  # Do domain name lookups through the proxy; though this setting doesn't really matter since we won't be doing any domain name lookups anyway.
                if shared.config.getboolean('bitmessagesettings', 'socksauthentication'):
                    socksusername = shared.config.get(
                        'bitmessagesettings', 'socksusername')
                    sockspassword = shared.config.get(
                        'bitmessagesettings', 'sockspassword')
                    sock.setproxy(
                        proxytype, sockshostname, socksport, rdns, socksusername, sockspassword)
                else:
                    sock.setproxy(
                        proxytype, sockshostname, socksport, rdns)

            try:
                sock.connect((peer.host, peer.port))
                rd = receiveDataThread()
                rd.daemon = True  # close the main program even if there are threads left
                someObjectsOfWhichThisRemoteNodeIsAlreadyAware = {} # This is not necessairly a complete list; we clear it from time to time to save memory.
                sendDataThreadQueue = Queue.Queue() # Used to submit information to the send data thread for this connection. 
                rd.setup(sock, 
                         peer.host, 
                         peer.port, 
                         self.streamNumber,
                         someObjectsOfWhichThisRemoteNodeIsAlreadyAware, 
                         self.selfInitiatedConnections, 
                         sendDataThreadQueue)
                rd.start()
                with shared.printLock:
                    print self, 'connected to', peer, 'during an outgoing attempt.'


                sd = sendDataThread(sendDataThreadQueue)
                sd.setup(sock, peer.host, peer.port, self.streamNumber,
                         someObjectsOfWhichThisRemoteNodeIsAlreadyAware)
                sd.start()
                sd.sendVersionMessage()

            except socks.GeneralProxyError as err:
                if shared.verbose >= 2:
                    with shared.printLock:
                        print 'Could NOT connect to', peer, 'during outgoing attempt.', err

                timeLastSeen = shared.knownNodes[
                    self.streamNumber][peer]
                if (int(time.time()) - timeLastSeen) > 172800 and len(shared.knownNodes[self.streamNumber]) > 1000:  # for nodes older than 48 hours old if we have more than 1000 hosts in our list, delete from the shared.knownNodes data-structure.
                    shared.knownNodesLock.acquire()
                    del shared.knownNodes[self.streamNumber][peer]
                    shared.knownNodesLock.release()
                    with shared.printLock:
                        print 'deleting ', peer, 'from shared.knownNodes because it is more than 48 hours old and we could not connect to it.'

            except socks.Socks5AuthError as err:
                shared.UISignalQueue.put((
                    'updateStatusBar', tr.translateText(
                    "MainWindow", "SOCKS5 Authentication problem: %1").arg(str(err))))
            except socks.Socks5Error as err:
                pass
                print 'SOCKS5 error. (It is possible that the server wants authentication).)', str(err)
            except socks.Socks4Error as err:
                print 'Socks4Error:', err
            except socket.error as err:
                if shared.config.get('bitmessagesettings', 'socksproxytype')[0:5] == 'SOCKS':
                    print 'Bitmessage MIGHT be having trouble connecting to the SOCKS server. ' + str(err)
                else:
                    if shared.verbose >= 1:
                        with shared.printLock:
                            print 'Could NOT connect to', peer, 'during outgoing attempt.', err

                    timeLastSeen = shared.knownNodes[
                        self.streamNumber][peer]
                    if (int(time.time()) - timeLastSeen) > 172800 and len(shared.knownNodes[self.streamNumber]) > 1000:  # for nodes older than 48 hours old if we have more than 1000 hosts in our list, delete from the knownNodes data-structure.
                        shared.knownNodesLock.acquire()
                        del shared.knownNodes[self.streamNumber][peer]
                        shared.knownNodesLock.release()
                        with shared.printLock:
                            print 'deleting ', peer, 'from knownNodes because it is more than 48 hours old and we could not connect to it.'

            except Exception as err:
                sys.stderr.write(
                    'An exception has occurred in the outgoingSynSender thread that was not caught by other exception types: ')
                import traceback
                traceback.print_exc()
            time.sleep(0.1)

########NEW FILE########
__FILENAME__ = class_receiveDataThread
doTimingAttackMitigation = True

import time
import threading
import shared
import hashlib
import socket
import random
from struct import unpack, pack
import sys
#import string
#from subprocess import call  # used when the API must execute an outside program
#from pyelliptic.openssl import OpenSSL

#import highlevelcrypto
from addresses import *
import helper_generic
#import helper_bitcoin
#import helper_inbox
#import helper_sent
from helper_sql import *
#import tr
from debug import logger
#from bitmessagemain import shared.lengthOfTimeToLeaveObjectsInInventory, shared.lengthOfTimeToHoldOnToAllPubkeys, shared.maximumAgeOfAnObjectThatIAmWillingToAccept, shared.maximumAgeOfObjectsThatIAdvertiseToOthers, shared.maximumAgeOfNodesThatIAdvertiseToOthers, shared.numberOfObjectsThatWeHaveYetToGetPerPeer, shared.neededPubkeys

# This thread is created either by the synSenderThread(for outgoing
# connections) or the singleListenerThread(for incoming connections).

class receiveDataThread(threading.Thread):

    def __init__(self):
        threading.Thread.__init__(self)
        self.data = ''
        self.verackSent = False
        self.verackReceived = False

    def setup(
        self,
        sock,
        HOST,
        port,
        streamNumber,
        someObjectsOfWhichThisRemoteNodeIsAlreadyAware,
        selfInitiatedConnections,
        sendDataThreadQueue):
        
        self.sock = sock
        self.peer = shared.Peer(HOST, port)
        self.streamNumber = streamNumber
        self.payloadLength = 0  # This is the protocol payload length thus it doesn't include the 24 byte message header
        self.objectsThatWeHaveYetToGetFromThisPeer = {}
        self.selfInitiatedConnections = selfInitiatedConnections
        self.sendDataThreadQueue = sendDataThreadQueue # used to send commands and data to the sendDataThread
        shared.connectedHostsList[
            self.peer.host] = 0  # The very fact that this receiveData thread exists shows that we are connected to the remote host. Let's add it to this list so that an outgoingSynSender thread doesn't try to connect to it.
        self.connectionIsOrWasFullyEstablished = False  # set to true after the remote node and I accept each other's version messages. This is needed to allow the user interface to accurately reflect the current number of connections.
        if self.streamNumber == -1:  # This was an incoming connection. Send out a version message if we accept the other node's version message.
            self.initiatedConnection = False
        else:
            self.initiatedConnection = True
            self.selfInitiatedConnections[streamNumber][self] = 0
        self.someObjectsOfWhichThisRemoteNodeIsAlreadyAware = someObjectsOfWhichThisRemoteNodeIsAlreadyAware

    def run(self):
        with shared.printLock:
            print 'ID of the receiveDataThread is', str(id(self)) + '. The size of the shared.connectedHostsList is now', len(shared.connectedHostsList)

        while True:
            dataLen = len(self.data)
            try:
                self.data += self.sock.recv(4096)
            except socket.timeout:
                with shared.printLock:
                    print 'Timeout occurred waiting for data from', self.peer, '. Closing receiveData thread. (ID:', str(id(self)) + ')'
                break
            except Exception as err:
                with shared.printLock:
                    print 'sock.recv error. Closing receiveData thread (HOST:', self.peer, 'ID:', str(id(self)) + ').', err
                break
            # print 'Received', repr(self.data)
            if len(self.data) == dataLen: # If self.sock.recv returned no data:
                with shared.printLock:
                    print 'Connection to', self.peer, 'closed. Closing receiveData thread. (ID:', str(id(self)) + ')'
                break
            else:
                self.processData()

        try:
            del self.selfInitiatedConnections[self.streamNumber][self]
            with shared.printLock:
                print 'removed self (a receiveDataThread) from selfInitiatedConnections'
        except:
            pass
        shared.broadcastToSendDataQueues((0, 'shutdown', self.peer)) # commands the corresponding sendDataThread to shut itself down.
        try:
            del shared.connectedHostsList[self.peer.host]
        except Exception as err:
            with shared.printLock:
                print 'Could not delete', self.peer.host, 'from shared.connectedHostsList.', err

        try:
            del shared.numberOfObjectsThatWeHaveYetToGetPerPeer[
                self.peer]
        except:
            pass
        shared.UISignalQueue.put(('updateNetworkStatusTab', 'no data'))
        with shared.printLock:
            print 'The size of the connectedHostsList is now:', len(shared.connectedHostsList)


    def processData(self):
        # if shared.verbose >= 3:
            # with shared.printLock:
            #   print 'self.data is currently ', repr(self.data)
            #
        if len(self.data) < 24:  # if so little of the data has arrived that we can't even read the checksum then wait for more data.
            return
        if self.data[0:4] != '\xe9\xbe\xb4\xd9':
            #if shared.verbose >= 1:
            #    with shared.printLock:
            #        print 'The magic bytes were not correct. First 40 bytes of data: ' + repr(self.data[0:40])

            self.data = ""
            return
        self.payloadLength, = unpack('>L', self.data[16:20])
        if self.payloadLength > 20000000:
            logger.info('The incoming message, which we have not yet download, is too large. Ignoring it. (unfortunately there is no way to tell the other node to stop sending it except to disconnect.) Message size: %s' % self.payloadLength)
            self.data = self.data[self.payloadLength + 24:]
            self.processData()
            return
        if len(self.data) < self.payloadLength + 24:  # check if the whole message has arrived yet.
            return
        if self.data[20:24] != hashlib.sha512(self.data[24:self.payloadLength + 24]).digest()[0:4]:  # test the checksum in the message. If it is correct...
            print 'Checksum incorrect. Clearing this message.'
            self.data = self.data[self.payloadLength + 24:]
            self.processData()
            return
        # The time we've last seen this node is obviously right now since we
        # just received valid data from it. So update the knownNodes list so
        # that other peers can be made aware of its existance.
        if self.initiatedConnection and self.connectionIsOrWasFullyEstablished:  # The remote port is only something we should share with others if it is the remote node's incoming port (rather than some random operating-system-assigned outgoing port).
            shared.knownNodesLock.acquire()
            shared.knownNodes[self.streamNumber][self.peer] = int(time.time())
            shared.knownNodesLock.release()
        
        remoteCommand = self.data[4:16]
        with shared.printLock:
            print 'remoteCommand', repr(remoteCommand.replace('\x00', '')), ' from', self.peer

        if remoteCommand == 'version\x00\x00\x00\x00\x00' and not self.connectionIsOrWasFullyEstablished:
            self.recversion(self.data[24:self.payloadLength + 24])
        elif remoteCommand == 'verack\x00\x00\x00\x00\x00\x00' and not self.connectionIsOrWasFullyEstablished:
            self.recverack()
        elif remoteCommand == 'addr\x00\x00\x00\x00\x00\x00\x00\x00' and self.connectionIsOrWasFullyEstablished:
            self.recaddr(self.data[24:self.payloadLength + 24])
        elif remoteCommand == 'getpubkey\x00\x00\x00' and self.connectionIsOrWasFullyEstablished:
            shared.checkAndSharegetpubkeyWithPeers(self.data[24:self.payloadLength + 24])
        elif remoteCommand == 'pubkey\x00\x00\x00\x00\x00\x00' and self.connectionIsOrWasFullyEstablished:
            self.recpubkey(self.data[24:self.payloadLength + 24])
        elif remoteCommand == 'inv\x00\x00\x00\x00\x00\x00\x00\x00\x00' and self.connectionIsOrWasFullyEstablished:
            self.recinv(self.data[24:self.payloadLength + 24])
        elif remoteCommand == 'getdata\x00\x00\x00\x00\x00' and self.connectionIsOrWasFullyEstablished:
            self.recgetdata(self.data[24:self.payloadLength + 24])
        elif remoteCommand == 'msg\x00\x00\x00\x00\x00\x00\x00\x00\x00' and self.connectionIsOrWasFullyEstablished:
            self.recmsg(self.data[24:self.payloadLength + 24])
        elif remoteCommand == 'broadcast\x00\x00\x00' and self.connectionIsOrWasFullyEstablished:
            self.recbroadcast(self.data[24:self.payloadLength + 24])
        elif remoteCommand == 'ping\x00\x00\x00\x00\x00\x00\x00\x00' and self.connectionIsOrWasFullyEstablished:
            self.sendpong()
        elif remoteCommand == 'pong\x00\x00\x00\x00\x00\x00\x00\x00' and self.connectionIsOrWasFullyEstablished:
            pass
        elif remoteCommand == 'alert\x00\x00\x00\x00\x00\x00\x00' and self.connectionIsOrWasFullyEstablished:
            pass

        self.data = self.data[
            self.payloadLength + 24:]  # take this message out and then process the next message
        if self.data == '':
            while len(self.objectsThatWeHaveYetToGetFromThisPeer) > 0:
                shared.numberOfInventoryLookupsPerformed += 1
                objectHash, = random.sample(
                    self.objectsThatWeHaveYetToGetFromThisPeer, 1)
                if objectHash in shared.inventory:
                    with shared.printLock:
                        print 'Inventory (in memory) already has object listed in inv message.'

                    del self.objectsThatWeHaveYetToGetFromThisPeer[
                        objectHash]
                elif shared.isInSqlInventory(objectHash):
                    if shared.verbose >= 3:
                        with shared.printLock:
                            print 'Inventory (SQL on disk) already has object listed in inv message.'

                    del self.objectsThatWeHaveYetToGetFromThisPeer[
                        objectHash]
                else:
                    self.sendgetdata(objectHash)
                    del self.objectsThatWeHaveYetToGetFromThisPeer[
                        objectHash]  # It is possible that the remote node might not respond with the object. In that case, we'll very likely get it from someone else anyway.
                    if len(self.objectsThatWeHaveYetToGetFromThisPeer) == 0:
                        with shared.printLock:
                            print '(concerning', str(self.peer) + ')', 'number of objectsThatWeHaveYetToGetFromThisPeer is now', len(self.objectsThatWeHaveYetToGetFromThisPeer)

                        try:
                            del shared.numberOfObjectsThatWeHaveYetToGetPerPeer[
                                self.peer]  # this data structure is maintained so that we can keep track of how many total objects, across all connections, are currently outstanding. If it goes too high it can indicate that we are under attack by multiple nodes working together.
                        except:
                            pass
                    break
                if len(self.objectsThatWeHaveYetToGetFromThisPeer) == 0:
                    with shared.printLock:
                        print '(concerning', str(self.peer) + ')', 'number of objectsThatWeHaveYetToGetFromThisPeer is now', len(self.objectsThatWeHaveYetToGetFromThisPeer)

                    try:
                        del shared.numberOfObjectsThatWeHaveYetToGetPerPeer[
                            self.peer]  # this data structure is maintained so that we can keep track of how many total objects, across all connections, are currently outstanding. If it goes too high it can indicate that we are under attack by multiple nodes working together.
                    except:
                        pass
            if len(self.objectsThatWeHaveYetToGetFromThisPeer) > 0:
                with shared.printLock:
                    print '(concerning', str(self.peer) + ')', 'number of objectsThatWeHaveYetToGetFromThisPeer is now', len(self.objectsThatWeHaveYetToGetFromThisPeer)

                shared.numberOfObjectsThatWeHaveYetToGetPerPeer[self.peer] = len(
                    self.objectsThatWeHaveYetToGetFromThisPeer)  # this data structure is maintained so that we can keep track of how many total objects, across all connections, are currently outstanding. If it goes too high it can indicate that we are under attack by multiple nodes working together.
        self.processData()


    def sendpong(self):
        print 'Sending pong'
        self.sendDataThreadQueue.put((0, 'sendRawData', '\xE9\xBE\xB4\xD9\x70\x6F\x6E\x67\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\xcf\x83\xe1\x35'))


    def recverack(self):
        print 'verack received'
        self.verackReceived = True
        if self.verackSent:
            # We have thus both sent and received a verack.
            self.connectionFullyEstablished()

    def connectionFullyEstablished(self):
        if self.connectionIsOrWasFullyEstablished:
            # there is no reason to run this function a second time
            return
        self.connectionIsOrWasFullyEstablished = True
        # Command the corresponding sendDataThread to set its own connectionIsOrWasFullyEstablished variable to True also
        self.sendDataThreadQueue.put((0, 'connectionIsOrWasFullyEstablished', 'no data'))
        if not self.initiatedConnection:
            shared.clientHasReceivedIncomingConnections = True
            shared.UISignalQueue.put(('setStatusIcon', 'green'))
        self.sock.settimeout(
            600)  # We'll send out a pong every 5 minutes to make sure the connection stays alive if there has been no other traffic to send lately.
        shared.UISignalQueue.put(('updateNetworkStatusTab', 'no data'))
        with shared.printLock:
            print 'Connection fully established with', self.peer
            print 'The size of the connectedHostsList is now', len(shared.connectedHostsList)
            print 'The length of sendDataQueues is now:', len(shared.sendDataQueues)
            print 'broadcasting addr from within connectionFullyEstablished function.'

        # Let all of our peers know about this new node.
        dataToSend = (int(time.time()), self.streamNumber, 1, self.peer.host, self.remoteNodeIncomingPort)
        shared.broadcastToSendDataQueues((
            self.streamNumber, 'advertisepeer', dataToSend))

        self.sendaddr()  # This is one large addr message to this one peer.
        if not self.initiatedConnection and len(shared.connectedHostsList) > 200:
            with shared.printLock:
                print 'We are connected to too many people. Closing connection.'

            shared.broadcastToSendDataQueues((0, 'shutdown', self.peer))
            return
        self.sendBigInv()

    def sendBigInv(self):
        # Select all hashes which are younger than two days old and in this
        # stream.
        queryreturn = sqlQuery(
            '''SELECT hash FROM inventory WHERE ((receivedtime>? and objecttype<>'pubkey') or (receivedtime>? and objecttype='pubkey')) and streamnumber=?''',
            int(time.time()) - shared.maximumAgeOfObjectsThatIAdvertiseToOthers,
            int(time.time()) - shared.lengthOfTimeToHoldOnToAllPubkeys,
            self.streamNumber)
        bigInvList = {}
        for row in queryreturn:
            hash, = row
            if hash not in self.someObjectsOfWhichThisRemoteNodeIsAlreadyAware:
                bigInvList[hash] = 0
        # We also have messages in our inventory in memory (which is a python
        # dictionary). Let's fetch those too.
        with shared.inventoryLock:
            for hash, storedValue in shared.inventory.items():
                if hash not in self.someObjectsOfWhichThisRemoteNodeIsAlreadyAware:
                    objectType, streamNumber, payload, receivedTime, tag = storedValue
                    if streamNumber == self.streamNumber and receivedTime > int(time.time()) - shared.maximumAgeOfObjectsThatIAdvertiseToOthers:
                        bigInvList[hash] = 0
        numberOfObjectsInInvMessage = 0
        payload = ''
        # Now let us start appending all of these hashes together. They will be
        # sent out in a big inv message to our new peer.
        for hash, storedValue in bigInvList.items():
            payload += hash
            numberOfObjectsInInvMessage += 1
            if numberOfObjectsInInvMessage >= 50000:  # We can only send a max of 50000 items per inv message but we may have more objects to advertise. They must be split up into multiple inv messages.
                self.sendinvMessageToJustThisOnePeer(
                    numberOfObjectsInInvMessage, payload)
                payload = ''
                numberOfObjectsInInvMessage = 0
        if numberOfObjectsInInvMessage > 0:
            self.sendinvMessageToJustThisOnePeer(
                numberOfObjectsInInvMessage, payload)

    # Used to send a big inv message when the connection with a node is 
    # first fully established. Notice that there is also a broadcastinv 
    # function for broadcasting invs to everyone in our stream.
    def sendinvMessageToJustThisOnePeer(self, numberOfObjects, payload):
        payload = encodeVarint(numberOfObjects) + payload
        headerData = '\xe9\xbe\xb4\xd9'  # magic bits, slighly different from Bitcoin's magic bits.
        headerData += 'inv\x00\x00\x00\x00\x00\x00\x00\x00\x00'
        headerData += pack('>L', len(payload))
        headerData += hashlib.sha512(payload).digest()[:4]
        with shared.printLock:
            print 'Sending huge inv message with', numberOfObjects, 'objects to just this one peer'
        self.sendDataThreadQueue.put((0, 'sendRawData', headerData + payload))

    def _sleepForTimingAttackMitigation(self, sleepTime):
        # We don't need to do the timing attack mitigation if we are
        # only connected to the trusted peer because we can trust the
        # peer not to attack
        if sleepTime > 0 and doTimingAttackMitigation and shared.trustedPeer == None:
            with shared.printLock:
                print 'Timing attack mitigation: Sleeping for', sleepTime, 'seconds.'
            time.sleep(sleepTime)

    # We have received a broadcast message
    def recbroadcast(self, data):
        self.messageProcessingStartTime = time.time()

        shared.checkAndShareBroadcastWithPeers(data)

        """
        Let us now set lengthOfTimeWeShouldUseToProcessThisMessage. Sleeping
        will help guarantee that we can process messages faster than a remote
        node can send them. If we fall behind, the attacker could observe that
        we are are slowing down the rate at which we request objects from the
        network which would indicate that we own a particular address (whichever
        one to which they are sending all of their attack messages). Note
        that if an attacker connects to a target with many connections, this
        mitigation mechanism might not be sufficient.
        """
        if len(data) > 100000000:  # Size is greater than 100 megabytes
            lengthOfTimeWeShouldUseToProcessThisMessage = 100  # seconds.
        elif len(data) > 10000000:  # Between 100 and 10 megabytes
            lengthOfTimeWeShouldUseToProcessThisMessage = 20  # seconds.
        elif len(data) > 1000000:  # Between 10 and 1 megabyte
            lengthOfTimeWeShouldUseToProcessThisMessage = 3  # seconds.
        else:  # Less than 1 megabyte
            lengthOfTimeWeShouldUseToProcessThisMessage = .6  # seconds.

        sleepTime = lengthOfTimeWeShouldUseToProcessThisMessage - \
            (time.time() - self.messageProcessingStartTime)
        self._sleepForTimingAttackMitigation(sleepTime)

    # We have received a msg message.
    def recmsg(self, data):
        self.messageProcessingStartTime = time.time()

        shared.checkAndShareMsgWithPeers(data)

        """
        Let us now set lengthOfTimeWeShouldUseToProcessThisMessage. Sleeping
        will help guarantee that we can process messages faster than a remote
        node can send them. If we fall behind, the attacker could observe that
        we are are slowing down the rate at which we request objects from the
        network which would indicate that we own a particular address (whichever
        one to which they are sending all of their attack messages). Note
        that if an attacker connects to a target with many connections, this
        mitigation mechanism might not be sufficient.
        """
        if len(data) > 100000000:  # Size is greater than 100 megabytes
            lengthOfTimeWeShouldUseToProcessThisMessage = 100  # seconds. Actual length of time it took my computer to decrypt and verify the signature of a 100 MB message: 3.7 seconds.
        elif len(data) > 10000000:  # Between 100 and 10 megabytes
            lengthOfTimeWeShouldUseToProcessThisMessage = 20  # seconds. Actual length of time it took my computer to decrypt and verify the signature of a 10 MB message: 0.53 seconds. Actual length of time it takes in practice when processing a real message: 1.44 seconds.
        elif len(data) > 1000000:  # Between 10 and 1 megabyte
            lengthOfTimeWeShouldUseToProcessThisMessage = 3  # seconds. Actual length of time it took my computer to decrypt and verify the signature of a 1 MB message: 0.18 seconds. Actual length of time it takes in practice when processing a real message: 0.30 seconds.
        else:  # Less than 1 megabyte
            lengthOfTimeWeShouldUseToProcessThisMessage = .6  # seconds. Actual length of time it took my computer to decrypt and verify the signature of a 100 KB message: 0.15 seconds. Actual length of time it takes in practice when processing a real message: 0.25 seconds.

        sleepTime = lengthOfTimeWeShouldUseToProcessThisMessage - \
            (time.time() - self.messageProcessingStartTime)
        self._sleepForTimingAttackMitigation(sleepTime)

    # We have received a pubkey
    def recpubkey(self, data):
        self.pubkeyProcessingStartTime = time.time()

        shared.checkAndSharePubkeyWithPeers(data)

        lengthOfTimeWeShouldUseToProcessThisMessage = .1
        sleepTime = lengthOfTimeWeShouldUseToProcessThisMessage - \
            (time.time() - self.pubkeyProcessingStartTime)
        self._sleepForTimingAttackMitigation(sleepTime)

    # We have received an inv message
    def recinv(self, data):
        totalNumberOfobjectsThatWeHaveYetToGetFromAllPeers = 0  # this counts duplicates seperately because they take up memory
        if len(shared.numberOfObjectsThatWeHaveYetToGetPerPeer) > 0:
            for key, value in shared.numberOfObjectsThatWeHaveYetToGetPerPeer.items():
                totalNumberOfobjectsThatWeHaveYetToGetFromAllPeers += value
            with shared.printLock:
                print 'number of keys(hosts) in shared.numberOfObjectsThatWeHaveYetToGetPerPeer:', len(shared.numberOfObjectsThatWeHaveYetToGetPerPeer)
                print 'totalNumberOfobjectsThatWeHaveYetToGetFromAllPeers = ', totalNumberOfobjectsThatWeHaveYetToGetFromAllPeers

        numberOfItemsInInv, lengthOfVarint = decodeVarint(data[:10])
        if numberOfItemsInInv > 50000:
            sys.stderr.write('Too many items in inv message!')
            return
        if len(data) < lengthOfVarint + (numberOfItemsInInv * 32):
            print 'inv message doesn\'t contain enough data. Ignoring.'
            return
        if numberOfItemsInInv == 1:  # we'll just request this data from the person who advertised the object.
            if totalNumberOfobjectsThatWeHaveYetToGetFromAllPeers > 200000 and len(self.objectsThatWeHaveYetToGetFromThisPeer) > 1000:  # inv flooding attack mitigation
                with shared.printLock:
                    print 'We already have', totalNumberOfobjectsThatWeHaveYetToGetFromAllPeers, 'items yet to retrieve from peers and over 1000 from this node in particular. Ignoring this inv message.'
                return
            self.someObjectsOfWhichThisRemoteNodeIsAlreadyAware[
                data[lengthOfVarint:32 + lengthOfVarint]] = 0
            shared.numberOfInventoryLookupsPerformed += 1
            if data[lengthOfVarint:32 + lengthOfVarint] in shared.inventory:
                with shared.printLock:
                    print 'Inventory (in memory) has inventory item already.'
            elif shared.isInSqlInventory(data[lengthOfVarint:32 + lengthOfVarint]):
                print 'Inventory (SQL on disk) has inventory item already.'
            else:
                self.sendgetdata(data[lengthOfVarint:32 + lengthOfVarint])
        else:
            # There are many items listed in this inv message. Let us create a
            # 'set' of objects we are aware of and a set of objects in this inv
            # message so that we can diff one from the other cheaply.
            startTime = time.time()
            advertisedSet = set()
            for i in range(numberOfItemsInInv):
                advertisedSet.add(data[lengthOfVarint + (32 * i):32 + lengthOfVarint + (32 * i)])
            objectsNewToMe = advertisedSet - shared.inventorySets[self.streamNumber]
            logger.info('inv message lists %s objects. Of those %s are new to me. It took %s seconds to figure that out.', numberOfItemsInInv, len(objectsNewToMe), time.time()-startTime)
            for item in objectsNewToMe:  
                if totalNumberOfobjectsThatWeHaveYetToGetFromAllPeers > 200000 and len(self.objectsThatWeHaveYetToGetFromThisPeer) > 1000:  # inv flooding attack mitigation
                    with shared.printLock:
                        print 'We already have', totalNumberOfobjectsThatWeHaveYetToGetFromAllPeers, 'items yet to retrieve from peers and over', len(self.objectsThatWeHaveYetToGetFromThisPeer), 'from this node in particular. Ignoring the rest of this inv message.'
                    break
                self.someObjectsOfWhichThisRemoteNodeIsAlreadyAware[item] = 0 # helps us keep from sending inv messages to peers that already know about the objects listed therein
                self.objectsThatWeHaveYetToGetFromThisPeer[item] = 0 # upon finishing dealing with an incoming message, the receiveDataThread will request a random object of from peer out of this data structure. This way if we get multiple inv messages from multiple peers which list mostly the same objects, we will make getdata requests for different random objects from the various peers.
            if len(self.objectsThatWeHaveYetToGetFromThisPeer) > 0:
                shared.numberOfObjectsThatWeHaveYetToGetPerPeer[
                    self.peer] = len(self.objectsThatWeHaveYetToGetFromThisPeer)

    # Send a getdata message to our peer to request the object with the given
    # hash
    def sendgetdata(self, hash):
        with shared.printLock:
            print 'sending getdata to retrieve object with hash:', hash.encode('hex')

        payload = '\x01' + hash
        headerData = '\xe9\xbe\xb4\xd9'  # magic bits, slighly different from Bitcoin's magic bits.
        headerData += 'getdata\x00\x00\x00\x00\x00'
        headerData += pack('>L', len(
            payload))  # payload length. Note that we add an extra 8 for the nonce.
        headerData += hashlib.sha512(payload).digest()[:4]
        self.sendDataThreadQueue.put((0, 'sendRawData', headerData + payload))


    # We have received a getdata request from our peer
    def recgetdata(self, data):
        numberOfRequestedInventoryItems, lengthOfVarint = decodeVarint(
            data[:10])
        if len(data) < lengthOfVarint + (32 * numberOfRequestedInventoryItems):
            print 'getdata message does not contain enough data. Ignoring.'
            return
        for i in xrange(numberOfRequestedInventoryItems):
            hash = data[lengthOfVarint + (
                i * 32):32 + lengthOfVarint + (i * 32)]
            with shared.printLock:
                print 'received getdata request for item:', hash.encode('hex')

            shared.numberOfInventoryLookupsPerformed += 1
            shared.inventoryLock.acquire()
            if hash in shared.inventory:
                objectType, streamNumber, payload, receivedTime, tag = shared.inventory[
                    hash]
                shared.inventoryLock.release()
                self.sendData(objectType, payload)
            else:
                shared.inventoryLock.release()
                queryreturn = sqlQuery(
                    '''select objecttype, payload from inventory where hash=?''',
                    hash)
                if queryreturn != []:
                    for row in queryreturn:
                        objectType, payload = row
                    self.sendData(objectType, payload)
                else:
                    print 'Someone asked for an object with a getdata which is not in either our memory inventory or our SQL inventory. That shouldn\'t have happened.'

    # Our peer has requested (in a getdata message) that we send an object.
    def sendData(self, objectType, payload):
        headerData = '\xe9\xbe\xb4\xd9'  # magic bits, slighly different from Bitcoin's magic bits.
        if objectType == 'pubkey':
            with shared.printLock:
                print 'sending pubkey'

            headerData += 'pubkey\x00\x00\x00\x00\x00\x00'
        elif objectType == 'getpubkey' or objectType == 'pubkeyrequest':
            with shared.printLock:
                print 'sending getpubkey'

            headerData += 'getpubkey\x00\x00\x00'
        elif objectType == 'msg':
            with shared.printLock:
                print 'sending msg'

            headerData += 'msg\x00\x00\x00\x00\x00\x00\x00\x00\x00'
        elif objectType == 'broadcast':
            with shared.printLock:
                print 'sending broadcast'

            headerData += 'broadcast\x00\x00\x00'
        else:
            sys.stderr.write(
                'Error: sendData has been asked to send a strange objectType: %s\n' % str(objectType))
            return
        headerData += pack('>L', len(payload))  # payload length.
        headerData += hashlib.sha512(payload).digest()[:4]
        self.sendDataThreadQueue.put((0, 'sendRawData', headerData + payload))


    # Advertise this object to all of our peers
    """def broadcastinv(self, hash):
        with shared.printLock:
            print 'broadcasting inv with hash:', hash.encode('hex')

        shared.broadcastToSendDataQueues((self.streamNumber, 'advertiseobject', hash))
    """

    def _checkIPv4Address(self, host, hostFromAddrMessage):
        # print 'hostFromAddrMessage', hostFromAddrMessage
        if host[0] == '\x7F':
            print 'Ignoring IP address in loopback range:', hostFromAddrMessage
            return False
        if host[0] == '\x0A':
            print 'Ignoring IP address in private range:', hostFromAddrMessage
            return False
        if host[0:2] == '\xC0A8':
            print 'Ignoring IP address in private range:', hostFromAddrMessage
            return False
        return True

    def _checkIPv6Address(self, host, hostFromAddrMessage):
        if host == ('\x00' * 15) + '\x01':
            print 'Ignoring loopback address:', hostFromAddrMessage
            return False
        if host[0] == '\xFE' and (ord(host[1]) & 0xc0) == 0x80:
            print 'Ignoring local address:', hostFromAddrMessage
            return False
        if (ord(host[0]) & 0xfe) == 0xfc:
            print 'Ignoring unique local address:', hostFromAddrMessage
            return False
        return True

    # We have received an addr message.
    def recaddr(self, data):
        #listOfAddressDetailsToBroadcastToPeers = []
        numberOfAddressesIncluded = 0
        numberOfAddressesIncluded, lengthOfNumberOfAddresses = decodeVarint(
            data[:10])

        if shared.verbose >= 1:
            with shared.printLock:
                print 'addr message contains', numberOfAddressesIncluded, 'IP addresses.'

        if numberOfAddressesIncluded > 1000 or numberOfAddressesIncluded == 0:
            return
        if len(data) != lengthOfNumberOfAddresses + (38 * numberOfAddressesIncluded):
            print 'addr message does not contain the correct amount of data. Ignoring.'
            return

        for i in range(0, numberOfAddressesIncluded):
            try:
                fullHost = data[20 + lengthOfNumberOfAddresses + (38 * i):36 + lengthOfNumberOfAddresses + (38 * i)]
            except Exception as err:
                with shared.printLock:
                   sys.stderr.write(
                       'ERROR TRYING TO UNPACK recaddr (recaddrHost). Message: %s\n' % str(err))
                break  # giving up on unpacking any more. We should still be connected however.

            try:
                recaddrStream, = unpack('>I', data[8 + lengthOfNumberOfAddresses + (
                    38 * i):12 + lengthOfNumberOfAddresses + (38 * i)])
            except Exception as err:
                with shared.printLock:
                   sys.stderr.write(
                       'ERROR TRYING TO UNPACK recaddr (recaddrStream). Message: %s\n' % str(err))
                break  # giving up on unpacking any more. We should still be connected however.
            if recaddrStream == 0:
                continue
            if recaddrStream != self.streamNumber and recaddrStream != (self.streamNumber * 2) and recaddrStream != ((self.streamNumber * 2) + 1):  # if the embedded stream number is not in my stream or either of my child streams then ignore it. Someone might be trying funny business.
                continue
            try:
                recaddrServices, = unpack('>Q', data[12 + lengthOfNumberOfAddresses + (
                    38 * i):20 + lengthOfNumberOfAddresses + (38 * i)])
            except Exception as err:
                with shared.printLock:
                   sys.stderr.write(
                        'ERROR TRYING TO UNPACK recaddr (recaddrServices). Message: %s\n' % str(err))
                break  # giving up on unpacking any more. We should still be connected however.

            try:
                recaddrPort, = unpack('>H', data[36 + lengthOfNumberOfAddresses + (
                    38 * i):38 + lengthOfNumberOfAddresses + (38 * i)])
            except Exception as err:
                with shared.printLock:
                    sys.stderr.write(
                        'ERROR TRYING TO UNPACK recaddr (recaddrPort). Message: %s\n' % str(err))
                break  # giving up on unpacking any more. We should still be connected however.
            # print 'Within recaddr(): IP', recaddrIP, ', Port',
            # recaddrPort, ', i', i
            if fullHost[0:12] == '\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\xFF\xFF':
                ipv4Host = fullHost[12:]
                hostFromAddrMessage = socket.inet_ntop(socket.AF_INET, ipv4Host)
                if not self._checkIPv4Address(ipv4Host, hostFromAddrMessage):
                    continue
            else:
                hostFromAddrMessage = socket.inet_ntop(socket.AF_INET6, fullHost)
                if hostFromAddrMessage == "":
                    # This can happen on Windows systems which are not 64-bit compatible 
                    # so let us drop the IPv6 address. 
                    continue
                if not self._checkIPv6Address(fullHost, hostFromAddrMessage):
                    continue
            timeSomeoneElseReceivedMessageFromThisNode, = unpack('>Q', data[lengthOfNumberOfAddresses + (
                38 * i):8 + lengthOfNumberOfAddresses + (38 * i)])  # This is the 'time' value in the received addr message. 64-bit.
            if recaddrStream not in shared.knownNodes:  # knownNodes is a dictionary of dictionaries with one outer dictionary for each stream. If the outer stream dictionary doesn't exist yet then we must make it.
                shared.knownNodesLock.acquire()
                shared.knownNodes[recaddrStream] = {}
                shared.knownNodesLock.release()
            peerFromAddrMessage = shared.Peer(hostFromAddrMessage, recaddrPort)
            if peerFromAddrMessage not in shared.knownNodes[recaddrStream]:
                if len(shared.knownNodes[recaddrStream]) < 20000 and timeSomeoneElseReceivedMessageFromThisNode > (int(time.time()) - 10800) and timeSomeoneElseReceivedMessageFromThisNode < (int(time.time()) + 10800):  # If we have more than 20000 nodes in our list already then just forget about adding more. Also, make sure that the time that someone else received a message from this node is within three hours from now.
                    shared.knownNodesLock.acquire()
                    shared.knownNodes[recaddrStream][peerFromAddrMessage] = (
                        timeSomeoneElseReceivedMessageFromThisNode)
                    shared.knownNodesLock.release()
                    with shared.printLock:
                        print 'added new node', peerFromAddrMessage, 'to knownNodes in stream', recaddrStream

                    shared.needToWriteKnownNodesToDisk = True
                    hostDetails = (
                        timeSomeoneElseReceivedMessageFromThisNode,
                        recaddrStream, recaddrServices, hostFromAddrMessage, recaddrPort)
                    #listOfAddressDetailsToBroadcastToPeers.append(hostDetails)
                    shared.broadcastToSendDataQueues((
                        self.streamNumber, 'advertisepeer', hostDetails))
            else:
                timeLastReceivedMessageFromThisNode = shared.knownNodes[recaddrStream][
                    peerFromAddrMessage]  # PORT in this case is either the port we used to connect to the remote node, or the port that was specified by someone else in a past addr message.
                if (timeLastReceivedMessageFromThisNode < timeSomeoneElseReceivedMessageFromThisNode) and (timeSomeoneElseReceivedMessageFromThisNode < int(time.time())):
                    shared.knownNodesLock.acquire()
                    shared.knownNodes[recaddrStream][peerFromAddrMessage] = timeSomeoneElseReceivedMessageFromThisNode
                    shared.knownNodesLock.release()

        #if listOfAddressDetailsToBroadcastToPeers != []:
        #    self.broadcastaddr(listOfAddressDetailsToBroadcastToPeers)
        with shared.printLock:
            print 'knownNodes currently has', len(shared.knownNodes[self.streamNumber]), 'nodes for this stream.'


    # Send a huge addr message to our peer. This is only used 
    # when we fully establish a connection with a 
    # peer (with the full exchange of version and verack 
    # messages).
    def sendaddr(self):
        addrsInMyStream = {}
        addrsInChildStreamLeft = {}
        addrsInChildStreamRight = {}
        # print 'knownNodes', shared.knownNodes

        # We are going to share a maximum number of 1000 addrs with our peer.
        # 500 from this stream, 250 from the left child stream, and 250 from
        # the right child stream.
        shared.knownNodesLock.acquire()
        if len(shared.knownNodes[self.streamNumber]) > 0:
            for i in range(500):
                peer, = random.sample(shared.knownNodes[self.streamNumber], 1)
                if helper_generic.isHostInPrivateIPRange(peer.host):
                    continue
                addrsInMyStream[peer] = shared.knownNodes[
                    self.streamNumber][peer]
        if len(shared.knownNodes[self.streamNumber * 2]) > 0:
            for i in range(250):
                peer, = random.sample(shared.knownNodes[
                                      self.streamNumber * 2], 1)
                if helper_generic.isHostInPrivateIPRange(peer.host):
                    continue
                addrsInChildStreamLeft[peer] = shared.knownNodes[
                    self.streamNumber * 2][peer]
        if len(shared.knownNodes[(self.streamNumber * 2) + 1]) > 0:
            for i in range(250):
                peer, = random.sample(shared.knownNodes[
                                      (self.streamNumber * 2) + 1], 1)
                if helper_generic.isHostInPrivateIPRange(peer.host):
                    continue
                addrsInChildStreamRight[peer] = shared.knownNodes[
                    (self.streamNumber * 2) + 1][peer]
        shared.knownNodesLock.release()
        numberOfAddressesInAddrMessage = 0
        payload = ''
        # print 'addrsInMyStream.items()', addrsInMyStream.items()
        for (HOST, PORT), value in addrsInMyStream.items():
            timeLastReceivedMessageFromThisNode = value
            if timeLastReceivedMessageFromThisNode > (int(time.time()) - shared.maximumAgeOfNodesThatIAdvertiseToOthers):  # If it is younger than 3 hours old..
                numberOfAddressesInAddrMessage += 1
                payload += pack(
                    '>Q', timeLastReceivedMessageFromThisNode)  # 64-bit time
                payload += pack('>I', self.streamNumber)
                payload += pack(
                    '>q', 1)  # service bit flags offered by this node
                payload += shared.encodeHost(HOST)
                payload += pack('>H', PORT)  # remote port
        for (HOST, PORT), value in addrsInChildStreamLeft.items():
            timeLastReceivedMessageFromThisNode = value
            if timeLastReceivedMessageFromThisNode > (int(time.time()) - shared.maximumAgeOfNodesThatIAdvertiseToOthers):  # If it is younger than 3 hours old..
                numberOfAddressesInAddrMessage += 1
                payload += pack(
                    '>Q', timeLastReceivedMessageFromThisNode)  # 64-bit time
                payload += pack('>I', self.streamNumber * 2)
                payload += pack(
                    '>q', 1)  # service bit flags offered by this node
                payload += shared.encodeHost(HOST)
                payload += pack('>H', PORT)  # remote port
        for (HOST, PORT), value in addrsInChildStreamRight.items():
            timeLastReceivedMessageFromThisNode = value
            if timeLastReceivedMessageFromThisNode > (int(time.time()) - shared.maximumAgeOfNodesThatIAdvertiseToOthers):  # If it is younger than 3 hours old..
                numberOfAddressesInAddrMessage += 1
                payload += pack(
                    '>Q', timeLastReceivedMessageFromThisNode)  # 64-bit time
                payload += pack('>I', (self.streamNumber * 2) + 1)
                payload += pack(
                    '>q', 1)  # service bit flags offered by this node
                payload += shared.encodeHost(HOST)
                payload += pack('>H', PORT)  # remote port

        payload = encodeVarint(numberOfAddressesInAddrMessage) + payload
        datatosend = '\xE9\xBE\xB4\xD9addr\x00\x00\x00\x00\x00\x00\x00\x00'
        datatosend = datatosend + pack('>L', len(payload))  # payload length
        datatosend = datatosend + hashlib.sha512(payload).digest()[0:4]
        datatosend = datatosend + payload
        self.sendDataThreadQueue.put((0, 'sendRawData', datatosend))


    # We have received a version message
    def recversion(self, data):
        if len(data) < 83:
            # This version message is unreasonably short. Forget it.
            return
        if self.verackSent:
            """
            We must have already processed the remote node's version message.
            There might be a time in the future when we Do want to process
            a new version message, like if the remote node wants to update
            the streams in which they are interested. But for now we'll
            ignore this version message
            """ 
            return
        self.remoteProtocolVersion, = unpack('>L', data[:4])
        if self.remoteProtocolVersion <= 1:
            shared.broadcastToSendDataQueues((0, 'shutdown', self.peer))
            with shared.printLock:
                print 'Closing connection to old protocol version 1 node: ', self.peer
            return
        # print 'remoteProtocolVersion', self.remoteProtocolVersion
        self.myExternalIP = socket.inet_ntoa(data[40:44])
        # print 'myExternalIP', self.myExternalIP
        self.remoteNodeIncomingPort, = unpack('>H', data[70:72])
        # print 'remoteNodeIncomingPort', self.remoteNodeIncomingPort
        useragentLength, lengthOfUseragentVarint = decodeVarint(
            data[80:84])
        readPosition = 80 + lengthOfUseragentVarint
        useragent = data[readPosition:readPosition + useragentLength]
        readPosition += useragentLength
        numberOfStreamsInVersionMessage, lengthOfNumberOfStreamsInVersionMessage = decodeVarint(
            data[readPosition:])
        readPosition += lengthOfNumberOfStreamsInVersionMessage
        self.streamNumber, lengthOfRemoteStreamNumber = decodeVarint(
            data[readPosition:])
        with shared.printLock:
            print 'Remote node useragent:', useragent, '  stream number:', self.streamNumber

        if self.streamNumber != 1:
            shared.broadcastToSendDataQueues((0, 'shutdown', self.peer))
            with shared.printLock:
                print 'Closed connection to', self.peer, 'because they are interested in stream', self.streamNumber, '.'
            return
        shared.connectedHostsList[
            self.peer.host] = 1  # We use this data structure to not only keep track of what hosts we are connected to so that we don't try to connect to them again, but also to list the connections count on the Network Status tab.
        # If this was an incoming connection, then the sendData thread
        # doesn't know the stream. We have to set it.
        if not self.initiatedConnection:
            self.sendDataThreadQueue.put((0, 'setStreamNumber', self.streamNumber))
        if data[72:80] == shared.eightBytesOfRandomDataUsedToDetectConnectionsToSelf:
            shared.broadcastToSendDataQueues((0, 'shutdown', self.peer))
            with shared.printLock:
                print 'Closing connection to myself: ', self.peer
            return
        
        # The other peer's protocol version is of interest to the sendDataThread but we learn of it
        # in this version message. Let us inform the sendDataThread.
        self.sendDataThreadQueue.put((0, 'setRemoteProtocolVersion', self.remoteProtocolVersion))

        shared.knownNodesLock.acquire()
        shared.knownNodes[self.streamNumber][shared.Peer(self.peer.host, self.remoteNodeIncomingPort)] = int(time.time())
        shared.needToWriteKnownNodesToDisk = True
        shared.knownNodesLock.release()

        self.sendverack()
        if self.initiatedConnection == False:
            self.sendversion()

    # Sends a version message
    def sendversion(self):
        with shared.printLock:
            print 'Sending version message'
        self.sendDataThreadQueue.put((0, 'sendRawData', shared.assembleVersionMessage(
                self.peer.host, self.peer.port, self.streamNumber)))


    # Sends a verack message
    def sendverack(self):
        with shared.printLock:
            print 'Sending verack'
        self.sendDataThreadQueue.put((0, 'sendRawData', '\xE9\xBE\xB4\xD9\x76\x65\x72\x61\x63\x6B\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\xcf\x83\xe1\x35'))
        self.verackSent = True
        if self.verackReceived:
            self.connectionFullyEstablished()

########NEW FILE########
__FILENAME__ = class_sendDataThread
import time
import threading
import shared
import Queue
from struct import unpack, pack
import hashlib
import random
import sys
import socket

from class_objectHashHolder import *
from addresses import *

# Every connection to a peer has a sendDataThread (and also a
# receiveDataThread).
class sendDataThread(threading.Thread):

    def __init__(self, sendDataThreadQueue):
        threading.Thread.__init__(self)
        self.sendDataThreadQueue = sendDataThreadQueue
        shared.sendDataQueues.append(self.sendDataThreadQueue)
        with shared.printLock:
            print 'The length of sendDataQueues at sendDataThread init is:', len(shared.sendDataQueues)

        self.data = ''
        self.objectHashHolderInstance = objectHashHolder(self.sendDataThreadQueue)
        self.objectHashHolderInstance.start()
        self.connectionIsOrWasFullyEstablished = False


    def setup(
        self,
        sock,
        HOST,
        PORT,
        streamNumber,
            someObjectsOfWhichThisRemoteNodeIsAlreadyAware):
        self.sock = sock
        self.peer = shared.Peer(HOST, PORT)
        self.streamNumber = streamNumber
        self.remoteProtocolVersion = - \
            1  # This must be set using setRemoteProtocolVersion command which is sent through the self.sendDataThreadQueue queue.
        self.lastTimeISentData = int(
            time.time())  # If this value increases beyond five minutes ago, we'll send a pong message to keep the connection alive.
        self.someObjectsOfWhichThisRemoteNodeIsAlreadyAware = someObjectsOfWhichThisRemoteNodeIsAlreadyAware
        with shared.printLock:
            print 'The streamNumber of this sendDataThread (ID:', str(id(self)) + ') at setup() is', self.streamNumber


    def sendVersionMessage(self):
        datatosend = shared.assembleVersionMessage(
            self.peer.host, self.peer.port, self.streamNumber)  # the IP and port of the remote host, and my streamNumber.

        with shared.printLock:
            print 'Sending version packet: ', repr(datatosend)

        try:
            self.sock.sendall(datatosend)
        except Exception as err:
            # if not 'Bad file descriptor' in err:
            with shared.printLock:
                sys.stderr.write('sock.sendall error: %s\n' % err)
            
        self.versionSent = 1

    def run(self):
        while True:
            deststream, command, data = self.sendDataThreadQueue.get()

            if deststream == self.streamNumber or deststream == 0:
                if command == 'shutdown':
                    if data == self.peer or data == 'all':
                        with shared.printLock:
                            print 'sendDataThread (associated with', self.peer, ') ID:', id(self), 'shutting down now.'
                        break
                # When you receive an incoming connection, a sendDataThread is
                # created even though you don't yet know what stream number the
                # remote peer is interested in. They will tell you in a version
                # message and if you too are interested in that stream then you
                # will continue on with the connection and will set the
                # streamNumber of this send data thread here:
                elif command == 'setStreamNumber':
                    self.streamNumber = data
                    with shared.printLock:
                        print 'setting the stream number in the sendData thread (ID:', id(self), ') to', self.streamNumber 
                elif command == 'setRemoteProtocolVersion':
                    specifiedRemoteProtocolVersion = data
                    with shared.printLock:
                        print 'setting the remote node\'s protocol version in the sendDataThread (ID:', id(self), ') to', specifiedRemoteProtocolVersion
                    self.remoteProtocolVersion = specifiedRemoteProtocolVersion
                elif command == 'advertisepeer':
                    self.objectHashHolderInstance.holdPeer(data)
                elif command == 'sendaddr':
                    if not self.connectionIsOrWasFullyEstablished:
                        # not sending addr because we haven't sent and heard a verack from the remote node yet
                        return
                    numberOfAddressesInAddrMessage = len(
                        data)
                    payload = ''
                    for hostDetails in data:
                        timeLastReceivedMessageFromThisNode, streamNumber, services, host, port = hostDetails
                        payload += pack(
                            '>Q', timeLastReceivedMessageFromThisNode)  # now uses 64-bit time
                        payload += pack('>I', streamNumber)
                        payload += pack(
                            '>q', services)  # service bit flags offered by this node
                        payload += shared.encodeHost(host)
                        payload += pack('>H', port)

                    payload = encodeVarint(numberOfAddressesInAddrMessage) + payload
                    datatosend = '\xE9\xBE\xB4\xD9addr\x00\x00\x00\x00\x00\x00\x00\x00'
                    datatosend = datatosend + pack('>L', len(payload))  # payload length
                    datatosend = datatosend + hashlib.sha512(payload).digest()[0:4]
                    datatosend = datatosend + payload

                    try:
                        self.sock.sendall(datatosend)
                        self.lastTimeISentData = int(time.time())
                    except:
                        print 'sendaddr: self.sock.sendall failed'
                        break
                elif command == 'advertiseobject':
                    self.objectHashHolderInstance.holdHash(data)
                elif command == 'sendinv':
                    if not self.connectionIsOrWasFullyEstablished:
                        # not sending inv because we haven't sent and heard a verack from the remote node yet
                        return
                    payload = ''
                    for hash in data:
                        if hash not in self.someObjectsOfWhichThisRemoteNodeIsAlreadyAware:
                            payload += hash
                    if payload != '':
                        payload = encodeVarint(len(payload)/32) + payload
                        headerData = '\xe9\xbe\xb4\xd9'  # magic bits, slighly different from Bitcoin's magic bits.
                        headerData += 'inv\x00\x00\x00\x00\x00\x00\x00\x00\x00'
                        headerData += pack('>L', len(payload))
                        headerData += hashlib.sha512(payload).digest()[:4]
                        try:
                            self.sock.sendall(headerData + payload)
                            self.lastTimeISentData = int(time.time())
                        except:
                            print 'sendinv: self.sock.sendall failed'
                            break
                elif command == 'pong':
                    self.someObjectsOfWhichThisRemoteNodeIsAlreadyAware.clear() # To save memory, let us clear this data structure from time to time. As its function is to help us keep from sending inv messages to peers which sent us the same inv message mere seconds earlier, it will be fine to clear this data structure from time to time.
                    if self.lastTimeISentData < (int(time.time()) - 298):
                        # Send out a pong message to keep the connection alive.
                        with shared.printLock:
                            print 'Sending pong to', self.peer, 'to keep connection alive.'

                        try:
                            self.sock.sendall(
                                '\xE9\xBE\xB4\xD9\x70\x6F\x6E\x67\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\xcf\x83\xe1\x35')
                            self.lastTimeISentData = int(time.time())
                        except:
                            print 'send pong failed'
                            break
                elif command == 'sendRawData':
                    try:
                        self.sock.sendall(data)
                        self.lastTimeISentData = int(time.time())
                    except:
                        print 'Sending of data to', self.peer, 'failed. sendDataThread thread', self, 'ending now.' 
                        break
                elif command == 'connectionIsOrWasFullyEstablished':
                    self.connectionIsOrWasFullyEstablished = True
            else:
                with shared.printLock:
                    print 'sendDataThread ID:', id(self), 'ignoring command', command, 'because the thread is not in stream', deststream

        try:
            self.sock.shutdown(socket.SHUT_RDWR)
            self.sock.close()
        except:
            pass
        shared.sendDataQueues.remove(self.sendDataThreadQueue)
        with shared.printLock:
            print 'Number of queues remaining in sendDataQueues:', len(shared.sendDataQueues)
        self.objectHashHolderInstance.close()

########NEW FILE########
__FILENAME__ = class_singleCleaner
import threading
import shared
import time
import sys
import os
import pickle

import tr#anslate
from helper_sql import *
from debug import logger

'''The singleCleaner class is a timer-driven thread that cleans data structures to free memory, resends messages when a remote node doesn't respond, and sends pong messages to keep connections alive if the network isn't busy.
It cleans these data structures in memory:
inventory (moves data to the on-disk sql database)
inventorySets (clears then reloads data out of sql database)

It cleans these tables on the disk:
inventory (clears data more than 2 days and 12 hours old)
pubkeys (clears pubkeys older than 4 weeks old which we have not used personally)

It resends messages when there has been no response:
resends getpubkey messages in 5 days (then 10 days, then 20 days, etc...)
resends msg messages in 5 days (then 10 days, then 20 days, etc...)

'''


class singleCleaner(threading.Thread):

    def __init__(self):
        threading.Thread.__init__(self)

    def run(self):
        timeWeLastClearedInventoryAndPubkeysTables = 0
        try:
            shared.maximumLengthOfTimeToBotherResendingMessages = (float(shared.config.get('bitmessagesettings', 'stopresendingafterxdays')) * 24 * 60 * 60) + (float(shared.config.get('bitmessagesettings', 'stopresendingafterxmonths')) * (60 * 60 * 24 *365)/12)
        except:
            # Either the user hasn't set stopresendingafterxdays and stopresendingafterxmonths yet or the options are missing from the config file.
            shared.maximumLengthOfTimeToBotherResendingMessages = float('inf')

        while True:
            shared.UISignalQueue.put((
                'updateStatusBar', 'Doing housekeeping (Flushing inventory in memory to disk...)'))

            with shared.inventoryLock: # If you use both the inventoryLock and the sqlLock, always use the inventoryLock OUTSIDE of the sqlLock.
                with SqlBulkExecute() as sql:
                    for hash, storedValue in shared.inventory.items():
                        objectType, streamNumber, payload, receivedTime, tag = storedValue
                        if int(time.time()) - 3600 > receivedTime:
                            sql.execute(
                                '''INSERT INTO inventory VALUES (?,?,?,?,?,?)''',
                                hash,
                                objectType,
                                streamNumber,
                                payload,
                                receivedTime,
                                tag)
                            del shared.inventory[hash]
            shared.UISignalQueue.put(('updateStatusBar', ''))
            shared.broadcastToSendDataQueues((
                0, 'pong', 'no data')) # commands the sendData threads to send out a pong message if they haven't sent anything else in the last five minutes. The socket timeout-time is 10 minutes.
            # If we are running as a daemon then we are going to fill up the UI
            # queue which will never be handled by a UI. We should clear it to
            # save memory.
            if shared.safeConfigGetBoolean('bitmessagesettings', 'daemon'):
                shared.UISignalQueue.queue.clear()
            if timeWeLastClearedInventoryAndPubkeysTables < int(time.time()) - 7380:
                timeWeLastClearedInventoryAndPubkeysTables = int(time.time())
                # inventory (moves data from the inventory data structure to
                # the on-disk sql database)
                # inventory (clears pubkeys after 28 days and everything else
                # after 2 days and 12 hours)
                sqlExecute(
                    '''DELETE FROM inventory WHERE (receivedtime<? AND objecttype<>'pubkey') OR (receivedtime<? AND objecttype='pubkey') ''',
                    int(time.time()) - shared.lengthOfTimeToLeaveObjectsInInventory,
                    int(time.time()) - shared.lengthOfTimeToHoldOnToAllPubkeys)

                # pubkeys
                sqlExecute(
                    '''DELETE FROM pubkeys WHERE time<? AND usedpersonally='no' ''',
                    int(time.time()) - shared.lengthOfTimeToHoldOnToAllPubkeys)

                queryreturn = sqlQuery(
                    '''select toaddress, toripe, fromaddress, subject, message, ackdata, lastactiontime, status, pubkeyretrynumber, msgretrynumber FROM sent WHERE ((status='awaitingpubkey' OR status='msgsent') AND folder='sent' AND lastactiontime>?) ''',
                    int(time.time()) - shared.maximumLengthOfTimeToBotherResendingMessages) # If the message's folder='trash' then we'll ignore it.
                for row in queryreturn:
                    if len(row) < 5:
                        with shared.printLock:
                            sys.stderr.write(
                                'Something went wrong in the singleCleaner thread: a query did not return the requested fields. ' + repr(row))
                        time.sleep(3)

                        break
                    toaddress, toripe, fromaddress, subject, message, ackdata, lastactiontime, status, pubkeyretrynumber, msgretrynumber = row
                    if status == 'awaitingpubkey':
                        if (int(time.time()) - lastactiontime) > (shared.maximumAgeOfAnObjectThatIAmWillingToAccept * (2 ** (pubkeyretrynumber))):
                            resendPubkey(pubkeyretrynumber,toripe)
                    else: # status == msgsent
                        if (int(time.time()) - lastactiontime) > (shared.maximumAgeOfAnObjectThatIAmWillingToAccept * (2 ** (msgretrynumber))):
                            resendMsg(msgretrynumber,ackdata)

                # Let's also clear and reload shared.inventorySets to keep it from
                # taking up an unnecessary amount of memory.
                for streamNumber in shared.inventorySets:
                    shared.inventorySets[streamNumber] = set()
                    queryData = sqlQuery('''SELECT hash FROM inventory WHERE streamnumber=?''', streamNumber)
                    for row in queryData:
                        shared.inventorySets[streamNumber].add(row[0])
                with shared.inventoryLock:
                    for hash, storedValue in shared.inventory.items():
                        objectType, streamNumber, payload, receivedTime, tag = storedValue
                        if streamNumber in shared.inventorySets:
                            shared.inventorySets[streamNumber].add(hash)

            # Let us write out the knowNodes to disk if there is anything new to write out.
            if shared.needToWriteKnownNodesToDisk:
                shared.knownNodesLock.acquire()
                output = open(shared.appdata + 'knownnodes.dat', 'wb')
                try:
                    pickle.dump(shared.knownNodes, output)
                    output.close()
                except Exception as err:
                    if "Errno 28" in str(err):
                        logger.fatal('(while receiveDataThread shared.needToWriteKnownNodesToDisk) Alert: Your disk or data storage volume is full. ')
                        shared.UISignalQueue.put(('alert', (tr.translateText("MainWindow", "Disk full"), tr.translateText("MainWindow", 'Alert: Your disk or data storage volume is full. Bitmessage will now exit.'), True)))
                        if shared.daemon:
                            os._exit(0)
                shared.knownNodesLock.release()
                shared.needToWriteKnownNodesToDisk = False
            time.sleep(300)


def resendPubkey(pubkeyretrynumber,toripe):
    print 'It has been a long time and we haven\'t heard a response to our getpubkey request. Sending again.'
    try:
        del shared.neededPubkeys[
            toripe] # We need to take this entry out of the shared.neededPubkeys structure because the shared.workerQueue checks to see whether the entry is already present and will not do the POW and send the message because it assumes that it has already done it recently.
    except:
        pass

    shared.UISignalQueue.put((
         'updateStatusBar', 'Doing work necessary to again attempt to request a public key...'))
    t = ()
    sqlExecute(
        '''UPDATE sent SET lastactiontime=?, pubkeyretrynumber=?, status='msgqueued' WHERE toripe=?''',
        int(time.time()),
        pubkeyretrynumber + 1,
        toripe)
    shared.workerQueue.put(('sendmessage', ''))

def resendMsg(msgretrynumber,ackdata):
    print 'It has been a long time and we haven\'t heard an acknowledgement to our msg. Sending again.'
    sqlExecute(
    '''UPDATE sent SET lastactiontime=?, msgretrynumber=?, status=? WHERE ackdata=?''',
    int(time.time()),
    msgretrynumber + 1,
    'msgqueued',
    ackdata)
    shared.workerQueue.put(('sendmessage', ''))
    shared.UISignalQueue.put((
    'updateStatusBar', 'Doing work necessary to again attempt to deliver a message...'))

########NEW FILE########
__FILENAME__ = class_singleListener
import threading
import shared
import socket
from class_sendDataThread import *
from class_receiveDataThread import *
import helper_bootstrap
import errno
import re

# Only one singleListener thread will ever exist. It creates the
# receiveDataThread and sendDataThread for each incoming connection. Note
# that it cannot set the stream number because it is not known yet- the
# other node will have to tell us its stream number in a version message.
# If we don't care about their stream, we will close the connection
# (within the recversion function of the recieveData thread)


class singleListener(threading.Thread):

    def __init__(self):
        threading.Thread.__init__(self)

    def setup(self, selfInitiatedConnections):
        self.selfInitiatedConnections = selfInitiatedConnections

    def _createListenSocket(self, family):
        HOST = ''  # Symbolic name meaning all available interfaces
        PORT = shared.config.getint('bitmessagesettings', 'port')
        sock = socket.socket(family, socket.SOCK_STREAM)
        if family == socket.AF_INET6:
            # Make sure we can accept both IPv4 and IPv6 connections.
            # This is the default on everything apart from Windows
            sock.setsockopt(socket.IPPROTO_IPV6, socket.IPV6_V6ONLY, 0)
        # This option apparently avoids the TIME_WAIT state so that we can
        # rebind faster
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        sock.bind((HOST, PORT))
        sock.listen(2)
        return sock

    def run(self):
        # If there is a trusted peer then we don't want to accept
        # incoming connections so we'll just abandon the thread
        if shared.trustedPeer:
            return

        while shared.safeConfigGetBoolean('bitmessagesettings', 'dontconnect'):
            time.sleep(1)
        helper_bootstrap.dns()
        # We typically don't want to accept incoming connections if the user is using a
        # SOCKS proxy, unless they have configured otherwise. If they eventually select
        # proxy 'none' or configure SOCKS listening then this will start listening for
        # connections.
        while shared.config.get('bitmessagesettings', 'socksproxytype')[0:5] == 'SOCKS' and not shared.config.getboolean('bitmessagesettings', 'sockslisten'):
            time.sleep(5)

        with shared.printLock:
            print 'Listening for incoming connections.'

        # First try listening on an IPv6 socket. This should also be
        # able to accept connections on IPv4. If that's not available
        # we'll fall back to IPv4-only.
        try:
            sock = self._createListenSocket(socket.AF_INET6)
        except socket.error, e:
            if (isinstance(e.args, tuple) and
                e.args[0] in (errno.EAFNOSUPPORT,
                              errno.EPFNOSUPPORT,
                              errno.ENOPROTOOPT)):
                sock = self._createListenSocket(socket.AF_INET)
            else:
                raise

        # regexp to match an IPv4-mapped IPv6 address
        mappedAddressRegexp = re.compile(r'^::ffff:([0-9]+\.[0-9]+\.[0-9]+\.[0-9]+)$')

        while True:
            # We typically don't want to accept incoming connections if the user is using a
            # SOCKS proxy, unless they have configured otherwise. If they eventually select
            # proxy 'none' or configure SOCKS listening then this will start listening for
            # connections.
            while shared.config.get('bitmessagesettings', 'socksproxytype')[0:5] == 'SOCKS' and not shared.config.getboolean('bitmessagesettings', 'sockslisten'):
                time.sleep(10)
            while len(shared.connectedHostsList) > 220:
                with shared.printLock:
                    print 'We are connected to too many people. Not accepting further incoming connections for ten seconds.'

                time.sleep(10)

            while True:
                a, sockaddr = sock.accept()
                (HOST, PORT) = sockaddr[0:2]

                # If the address is an IPv4-mapped IPv6 address then
                # convert it to just the IPv4 representation
                md = mappedAddressRegexp.match(HOST)
                if md != None:
                    HOST = md.group(1)

                # The following code will, unfortunately, block an
                # incoming connection if someone else on the same LAN
                # is already connected because the two computers will
                # share the same external IP. This is here to prevent
                # connection flooding.
                if HOST in shared.connectedHostsList:
                    a.close()
                    with shared.printLock:
                        print 'We are already connected to', HOST + '. Ignoring connection.'
                else:
                    break

            someObjectsOfWhichThisRemoteNodeIsAlreadyAware = {} # This is not necessairly a complete list; we clear it from time to time to save memory.
            sendDataThreadQueue = Queue.Queue() # Used to submit information to the send data thread for this connection.
            a.settimeout(20)

            sd = sendDataThread(sendDataThreadQueue)
            sd.setup(
                a, HOST, PORT, -1, someObjectsOfWhichThisRemoteNodeIsAlreadyAware)
            sd.start()

            rd = receiveDataThread()
            rd.daemon = True  # close the main program even if there are threads left
            rd.setup(
                a, HOST, PORT, -1, someObjectsOfWhichThisRemoteNodeIsAlreadyAware, self.selfInitiatedConnections, sendDataThreadQueue)
            rd.start()

            with shared.printLock:
                print self, 'connected to', HOST, 'during INCOMING request.'


########NEW FILE########
__FILENAME__ = class_singleWorker
import threading
import shared
import time
from time import strftime, localtime, gmtime
import random
from subprocess import call  # used when the API must execute an outside program
from addresses import *
import highlevelcrypto
import proofofwork
import sys
from class_addressGenerator import pointMult
import tr
from debug import logger
from helper_sql import *
import helper_inbox

# This thread, of which there is only one, does the heavy lifting:
# calculating POWs.


class singleWorker(threading.Thread):

    def __init__(self):
        # QThread.__init__(self, parent)
        threading.Thread.__init__(self)

    def run(self):
        queryreturn = sqlQuery(
            '''SELECT toripe, toaddress FROM sent WHERE ((status='awaitingpubkey' OR status='doingpubkeypow') AND folder='sent')''')
        for row in queryreturn:
            toripe, toaddress = row
            toStatus, toAddressVersionNumber, toStreamNumber, toRipe = decodeAddress(toaddress)
            if toAddressVersionNumber <= 3 :
                shared.neededPubkeys[toripe] = 0
            elif toAddressVersionNumber >= 4:
                doubleHashOfAddressData = hashlib.sha512(hashlib.sha512(encodeVarint(
                    toAddressVersionNumber) + encodeVarint(toStreamNumber) + toRipe).digest()).digest()
                privEncryptionKey = doubleHashOfAddressData[:32] # Note that this is the first half of the sha512 hash.
                tag = doubleHashOfAddressData[32:]
                shared.neededPubkeys[tag] = highlevelcrypto.makeCryptor(privEncryptionKey.encode('hex')) # We'll need this for when we receive a pubkey reply: it will be encrypted and we'll need to decrypt it.

        # Initialize the shared.ackdataForWhichImWatching data structure using data
        # from the sql database.
        queryreturn = sqlQuery(
            '''SELECT ackdata FROM sent where (status='msgsent' OR status='doingmsgpow')''')
        for row in queryreturn:
            ackdata, = row
            print 'Watching for ackdata', ackdata.encode('hex')
            shared.ackdataForWhichImWatching[ackdata] = 0

        queryreturn = sqlQuery(
            '''SELECT DISTINCT toaddress FROM sent WHERE (status='doingpubkeypow' AND folder='sent')''')
        for row in queryreturn:
            toaddress, = row
            self.requestPubKey(toaddress)

        time.sleep(
            10)  # give some time for the GUI to start before we start on existing POW tasks.

        self.sendMsg()
                     # just in case there are any pending tasks for msg
                     # messages that have yet to be sent.
        self.sendBroadcast()
                           # just in case there are any tasks for Broadcasts
                           # that have yet to be sent.

        while True:
            command, data = shared.workerQueue.get()
            if command == 'sendmessage':
                self.sendMsg()
            elif command == 'sendbroadcast':
                self.sendBroadcast()
            elif command == 'doPOWForMyV2Pubkey':
                self.doPOWForMyV2Pubkey(data)
            elif command == 'sendOutOrStoreMyV3Pubkey':
                self.sendOutOrStoreMyV3Pubkey(data)
            elif command == 'sendOutOrStoreMyV4Pubkey':
                self.sendOutOrStoreMyV4Pubkey(data)
            else:
                with shared.printLock:
                    sys.stderr.write(
                        'Probable programming error: The command sent to the workerThread is weird. It is: %s\n' % command)

            shared.workerQueue.task_done()

    def doPOWForMyV2Pubkey(self, hash):  # This function also broadcasts out the pubkey message once it is done with the POW
        # Look up my stream number based on my address hash
        """configSections = shared.config.sections()
        for addressInKeysFile in configSections:
            if addressInKeysFile <> 'bitmessagesettings':
                status,addressVersionNumber,streamNumber,hashFromThisParticularAddress = decodeAddress(addressInKeysFile)
                if hash == hashFromThisParticularAddress:
                    myAddress = addressInKeysFile
                    break"""
        myAddress = shared.myAddressesByHash[hash]
        status, addressVersionNumber, streamNumber, hash = decodeAddress(
            myAddress)
        embeddedTime = int(time.time() + random.randrange(
            -300, 300))  # the current time plus or minus five minutes
        payload = pack('>I', (embeddedTime))
        payload += encodeVarint(addressVersionNumber)  # Address version number
        payload += encodeVarint(streamNumber)
        payload += '\x00\x00\x00\x01'  # bitfield of features supported by me (see the wiki).

        try:
            privSigningKeyBase58 = shared.config.get(
                myAddress, 'privsigningkey')
            privEncryptionKeyBase58 = shared.config.get(
                myAddress, 'privencryptionkey')
        except Exception as err:
            with shared.printLock:
                sys.stderr.write(
                    'Error within doPOWForMyV2Pubkey. Could not read the keys from the keys.dat file for a requested address. %s\n' % err)

            return

        privSigningKeyHex = shared.decodeWalletImportFormat(
            privSigningKeyBase58).encode('hex')
        privEncryptionKeyHex = shared.decodeWalletImportFormat(
            privEncryptionKeyBase58).encode('hex')
        pubSigningKey = highlevelcrypto.privToPub(
            privSigningKeyHex).decode('hex')
        pubEncryptionKey = highlevelcrypto.privToPub(
            privEncryptionKeyHex).decode('hex')

        payload += pubSigningKey[1:]
        payload += pubEncryptionKey[1:]

        # Do the POW for this pubkey message
        target = 2 ** 64 / ((len(payload) + shared.networkDefaultPayloadLengthExtraBytes +
                             8) * shared.networkDefaultProofOfWorkNonceTrialsPerByte)
        print '(For pubkey message) Doing proof of work...'
        initialHash = hashlib.sha512(payload).digest()
        trialValue, nonce = proofofwork.run(target, initialHash)
        print '(For pubkey message) Found proof of work', trialValue, 'Nonce:', nonce
        payload = pack('>Q', nonce) + payload

        inventoryHash = calculateInventoryHash(payload)
        objectType = 'pubkey'
        shared.inventory[inventoryHash] = (
            objectType, streamNumber, payload, embeddedTime,'')
        shared.inventorySets[streamNumber].add(inventoryHash)

        with shared.printLock:
            print 'broadcasting inv with hash:', inventoryHash.encode('hex')

        shared.broadcastToSendDataQueues((
            streamNumber, 'advertiseobject', inventoryHash))
        shared.UISignalQueue.put(('updateStatusBar', ''))
        try:
            shared.config.set(
                myAddress, 'lastpubkeysendtime', str(int(time.time())))
            with open(shared.appdata + 'keys.dat', 'wb') as configfile:
                shared.config.write(configfile)
        except:
            # The user deleted the address out of the keys.dat file before this
            # finished.
            pass

    # If this isn't a chan address, this function assembles the pubkey data,
    # does the necessary POW and sends it out. If it *is* a chan then it
    # assembles the pubkey and stores is in the pubkey table so that we can
    # send messages to "ourselves".
    def sendOutOrStoreMyV3Pubkey(self, hash): 
        try:
            myAddress = shared.myAddressesByHash[hash]
        except:
            #The address has been deleted.
            return
        if shared.safeConfigGetBoolean(myAddress, 'chan'):
            with shared.printLock:
                print 'This is a chan address. Not sending pubkey.'
            return
        status, addressVersionNumber, streamNumber, hash = decodeAddress(
            myAddress)
        embeddedTime = int(time.time() + random.randrange(
            -300, 300))  # the current time plus or minus five minutes
        payload = pack('>I', (embeddedTime))
        payload += encodeVarint(addressVersionNumber)  # Address version number
        payload += encodeVarint(streamNumber)
        payload += '\x00\x00\x00\x01'  # bitfield of features supported by me (see the wiki).

        try:
            privSigningKeyBase58 = shared.config.get(
                myAddress, 'privsigningkey')
            privEncryptionKeyBase58 = shared.config.get(
                myAddress, 'privencryptionkey')
        except Exception as err:
            with shared.printLock:
                sys.stderr.write(
                    'Error within sendOutOrStoreMyV3Pubkey. Could not read the keys from the keys.dat file for a requested address. %s\n' % err)

            return

        privSigningKeyHex = shared.decodeWalletImportFormat(
            privSigningKeyBase58).encode('hex')
        privEncryptionKeyHex = shared.decodeWalletImportFormat(
            privEncryptionKeyBase58).encode('hex')
        pubSigningKey = highlevelcrypto.privToPub(
            privSigningKeyHex).decode('hex')
        pubEncryptionKey = highlevelcrypto.privToPub(
            privEncryptionKeyHex).decode('hex')

        payload += pubSigningKey[1:]
        payload += pubEncryptionKey[1:]

        payload += encodeVarint(shared.config.getint(
            myAddress, 'noncetrialsperbyte'))
        payload += encodeVarint(shared.config.getint(
            myAddress, 'payloadlengthextrabytes'))
        signature = highlevelcrypto.sign(payload, privSigningKeyHex)
        payload += encodeVarint(len(signature))
        payload += signature

        # Do the POW for this pubkey message
        target = 2 ** 64 / ((len(payload) + shared.networkDefaultPayloadLengthExtraBytes +
                             8) * shared.networkDefaultProofOfWorkNonceTrialsPerByte)
        print '(For pubkey message) Doing proof of work...'
        initialHash = hashlib.sha512(payload).digest()
        trialValue, nonce = proofofwork.run(target, initialHash)
        print '(For pubkey message) Found proof of work', trialValue, 'Nonce:', nonce

        payload = pack('>Q', nonce) + payload
        inventoryHash = calculateInventoryHash(payload)
        objectType = 'pubkey'
        shared.inventory[inventoryHash] = (
            objectType, streamNumber, payload, embeddedTime,'')
        shared.inventorySets[streamNumber].add(inventoryHash)

        with shared.printLock:
            print 'broadcasting inv with hash:', inventoryHash.encode('hex')

        shared.broadcastToSendDataQueues((
            streamNumber, 'advertiseobject', inventoryHash))
        shared.UISignalQueue.put(('updateStatusBar', ''))
        try:
            shared.config.set(
                myAddress, 'lastpubkeysendtime', str(int(time.time())))
            with open(shared.appdata + 'keys.dat', 'wb') as configfile:
                shared.config.write(configfile)
        except:
            # The user deleted the address out of the keys.dat file before this
            # finished.
            pass

    # If this isn't a chan address, this function assembles the pubkey data,
    # does the necessary POW and sends it out. 
    def sendOutOrStoreMyV4Pubkey(self, myAddress):
        if not shared.config.has_section(myAddress):
            #The address has been deleted.
            return
        if shared.safeConfigGetBoolean(myAddress, 'chan'):
            with shared.printLock:
                print 'This is a chan address. Not sending pubkey.'
            return
        status, addressVersionNumber, streamNumber, hash = decodeAddress(
            myAddress)
        embeddedTime = int(time.time() + random.randrange(
            -300, 300))  # the current time plus or minus five minutes
        payload = pack('>Q', (embeddedTime))
        payload += encodeVarint(addressVersionNumber)  # Address version number
        payload += encodeVarint(streamNumber)

        dataToEncrypt = '\x00\x00\x00\x01'  # bitfield of features supported by me (see the wiki).

        try:
            privSigningKeyBase58 = shared.config.get(
                myAddress, 'privsigningkey')
            privEncryptionKeyBase58 = shared.config.get(
                myAddress, 'privencryptionkey')
        except Exception as err:
            with shared.printLock:
                sys.stderr.write(
                    'Error within sendOutOrStoreMyV4Pubkey. Could not read the keys from the keys.dat file for a requested address. %s\n' % err)
            return

        privSigningKeyHex = shared.decodeWalletImportFormat(
            privSigningKeyBase58).encode('hex')
        privEncryptionKeyHex = shared.decodeWalletImportFormat(
            privEncryptionKeyBase58).encode('hex')
        pubSigningKey = highlevelcrypto.privToPub(
            privSigningKeyHex).decode('hex')
        pubEncryptionKey = highlevelcrypto.privToPub(
            privEncryptionKeyHex).decode('hex')
        dataToEncrypt += pubSigningKey[1:]
        dataToEncrypt += pubEncryptionKey[1:]

        dataToEncrypt += encodeVarint(shared.config.getint(
            myAddress, 'noncetrialsperbyte'))
        dataToEncrypt += encodeVarint(shared.config.getint(
            myAddress, 'payloadlengthextrabytes'))

        signature = highlevelcrypto.sign(payload + dataToEncrypt, privSigningKeyHex)
        dataToEncrypt += encodeVarint(len(signature))
        dataToEncrypt += signature

        # Let us encrypt the necessary data. We will use a hash of the data
        # contained in an address as a decryption key. This way in order to
        # read the public keys in a pubkey message, a node must know the address
        # first. We'll also tag, unencrypted, the pubkey with part of the hash
        # so that nodes know which pubkey object to try to decrypt when they
        # want to send a message.
        doubleHashOfAddressData = hashlib.sha512(hashlib.sha512(encodeVarint(
            addressVersionNumber) + encodeVarint(streamNumber) + hash).digest()).digest()
        payload += doubleHashOfAddressData[32:] # the tag
        privEncryptionKey = doubleHashOfAddressData[:32]
        pubEncryptionKey = pointMult(privEncryptionKey)
        payload += highlevelcrypto.encrypt(
            dataToEncrypt, pubEncryptionKey.encode('hex'))

        # Do the POW for this pubkey message
        target = 2 ** 64 / ((len(payload) + shared.networkDefaultPayloadLengthExtraBytes +
                             8) * shared.networkDefaultProofOfWorkNonceTrialsPerByte)
        print '(For pubkey message) Doing proof of work...'
        initialHash = hashlib.sha512(payload).digest()
        trialValue, nonce = proofofwork.run(target, initialHash)
        print '(For pubkey message) Found proof of work', trialValue, 'Nonce:', nonce

        payload = pack('>Q', nonce) + payload
        inventoryHash = calculateInventoryHash(payload)
        objectType = 'pubkey'
        shared.inventory[inventoryHash] = (
            objectType, streamNumber, payload, embeddedTime, doubleHashOfAddressData[32:])
        shared.inventorySets[streamNumber].add(inventoryHash)

        with shared.printLock:
            print 'broadcasting inv with hash:', inventoryHash.encode('hex')

        shared.broadcastToSendDataQueues((
            streamNumber, 'advertiseobject', inventoryHash))
        shared.UISignalQueue.put(('updateStatusBar', ''))
        try:
            shared.config.set(
                myAddress, 'lastpubkeysendtime', str(int(time.time())))
            with open(shared.appdata + 'keys.dat', 'wb') as configfile:
                shared.config.write(configfile)
        except Exception as err:
            logger.error('Error: Couldn\'t add the lastpubkeysendtime to the keys.dat file. Error message: %s' % err)

    def sendBroadcast(self):
        queryreturn = sqlQuery(
            '''SELECT fromaddress, subject, message, ackdata FROM sent WHERE status=? and folder='sent' ''', 'broadcastqueued')
        for row in queryreturn:
            fromaddress, subject, body, ackdata = row
            status, addressVersionNumber, streamNumber, ripe = decodeAddress(
                fromaddress)
            if addressVersionNumber <= 1:
                with shared.printLock:
                    sys.stderr.write(
                        'Error: In the singleWorker thread, the sendBroadcast function doesn\'t understand the address version.\n')
                return
            # We need to convert our private keys to public keys in order
            # to include them.
            try:
                privSigningKeyBase58 = shared.config.get(
                    fromaddress, 'privsigningkey')
                privEncryptionKeyBase58 = shared.config.get(
                    fromaddress, 'privencryptionkey')
            except:
                shared.UISignalQueue.put(('updateSentItemStatusByAckdata', (
                    ackdata, tr.translateText("MainWindow", "Error! Could not find sender address (your address) in the keys.dat file."))))
                continue

            privSigningKeyHex = shared.decodeWalletImportFormat(
                privSigningKeyBase58).encode('hex')
            privEncryptionKeyHex = shared.decodeWalletImportFormat(
                privEncryptionKeyBase58).encode('hex')

            pubSigningKey = highlevelcrypto.privToPub(privSigningKeyHex).decode(
                'hex')  # At this time these pubkeys are 65 bytes long because they include the encoding byte which we won't be sending in the broadcast message.
            pubEncryptionKey = highlevelcrypto.privToPub(
                privEncryptionKeyHex).decode('hex')

            payload = pack('>Q', (int(time.time()) + random.randrange(
                -300, 300)))  # the current time plus or minus five minutes
            if addressVersionNumber <= 3:
                payload += encodeVarint(2)  # broadcast version
            else:
                payload += encodeVarint(3)  # broadcast version
            payload += encodeVarint(streamNumber)
            if addressVersionNumber >= 4:
                doubleHashOfAddressData = hashlib.sha512(hashlib.sha512(encodeVarint(
                    addressVersionNumber) + encodeVarint(streamNumber) + ripe).digest()).digest()
                tag = doubleHashOfAddressData[32:]
                payload += tag
            else:
                tag = ''

            if addressVersionNumber <= 3:
                dataToEncrypt = encodeVarint(2)  # broadcast version
            else:
                dataToEncrypt = encodeVarint(3)  # broadcast version
            dataToEncrypt += encodeVarint(addressVersionNumber)
            dataToEncrypt += encodeVarint(streamNumber)
            dataToEncrypt += '\x00\x00\x00\x01'  # behavior bitfield
            dataToEncrypt += pubSigningKey[1:]
            dataToEncrypt += pubEncryptionKey[1:]
            if addressVersionNumber >= 3:
                dataToEncrypt += encodeVarint(shared.config.getint(fromaddress,'noncetrialsperbyte'))
                dataToEncrypt += encodeVarint(shared.config.getint(fromaddress,'payloadlengthextrabytes'))
            dataToEncrypt += '\x02' # message encoding type
            dataToEncrypt += encodeVarint(len('Subject:' + subject + '\n' + 'Body:' + body))  #Type 2 is simple UTF-8 message encoding per the documentation on the wiki.
            dataToEncrypt += 'Subject:' + subject + '\n' + 'Body:' + body
            signature = highlevelcrypto.sign(
                dataToEncrypt, privSigningKeyHex)
            dataToEncrypt += encodeVarint(len(signature))
            dataToEncrypt += signature

            # Encrypt the broadcast with the information contained in the broadcaster's address. Anyone who knows the address can generate 
            # the private encryption key to decrypt the broadcast. This provides virtually no privacy; its purpose is to keep questionable 
            # and illegal content from flowing through the Internet connections and being stored on the disk of 3rd parties. 
            if addressVersionNumber <= 3:
                privEncryptionKey = hashlib.sha512(encodeVarint(
                    addressVersionNumber) + encodeVarint(streamNumber) + ripe).digest()[:32]
            else:
                privEncryptionKey = doubleHashOfAddressData[:32]

            pubEncryptionKey = pointMult(privEncryptionKey)
            payload += highlevelcrypto.encrypt(
                dataToEncrypt, pubEncryptionKey.encode('hex'))

            target = 2 ** 64 / ((len(
                payload) + shared.networkDefaultPayloadLengthExtraBytes + 8) * shared.networkDefaultProofOfWorkNonceTrialsPerByte)
            print '(For broadcast message) Doing proof of work...'
            shared.UISignalQueue.put(('updateSentItemStatusByAckdata', (
                ackdata, tr.translateText("MainWindow", "Doing work necessary to send broadcast..."))))
            initialHash = hashlib.sha512(payload).digest()
            trialValue, nonce = proofofwork.run(target, initialHash)
            print '(For broadcast message) Found proof of work', trialValue, 'Nonce:', nonce

            payload = pack('>Q', nonce) + payload

            inventoryHash = calculateInventoryHash(payload)
            objectType = 'broadcast'
            shared.inventory[inventoryHash] = (
                objectType, streamNumber, payload, int(time.time()),tag)
            shared.inventorySets[streamNumber].add(inventoryHash)
            with shared.printLock:
                print 'sending inv (within sendBroadcast function) for object:', inventoryHash.encode('hex')
            shared.broadcastToSendDataQueues((
                streamNumber, 'advertiseobject', inventoryHash))

            shared.UISignalQueue.put(('updateSentItemStatusByAckdata', (ackdata, tr.translateText("MainWindow", "Broadcast sent on %1").arg(unicode(
                strftime(shared.config.get('bitmessagesettings', 'timeformat'), localtime(int(time.time()))), 'utf-8')))))

            # Update the status of the message in the 'sent' table to have
            # a 'broadcastsent' status
            sqlExecute(
                'UPDATE sent SET msgid=?, status=?, lastactiontime=? WHERE ackdata=?',
                inventoryHash,
                'broadcastsent',
                int(time.time()),
                ackdata)
        

    def sendMsg(self):
        # Check to see if there are any messages queued to be sent
        queryreturn = sqlQuery(
            '''SELECT DISTINCT toaddress FROM sent WHERE (status='msgqueued' AND folder='sent')''')
        for row in queryreturn:  # For each address to which we need to send a message, check to see if we have its pubkey already.
            toaddress, = row
            status, toAddressVersion, toStreamNumber, toRipe = decodeAddress(toaddress)
            # If we are sending a message to ourselves or a chan then we won't need an entry in the pubkeys table; we can calculate the needed pubkey using the private keys in our keys.dat file.
            if shared.config.has_section(toaddress):
                sqlExecute(
                    '''UPDATE sent SET status='doingmsgpow' WHERE toaddress=? AND status='msgqueued' ''',
                    toaddress)
                continue
            queryreturn = sqlQuery(
                '''SELECT hash FROM pubkeys WHERE hash=? AND addressversion=?''', toRipe, toAddressVersion)
            if queryreturn != []:  # If we have the needed pubkey in the pubkey table already, set the status to doingmsgpow (we'll do it further down)
                sqlExecute(
                    '''UPDATE sent SET status='doingmsgpow' WHERE toaddress=? AND status='msgqueued' ''',
                    toaddress)
            else:  # We don't have the needed pubkey in the pubkey table already.
                if toAddressVersion <= 3:
                    toTag = ''
                else:
                    toTag = hashlib.sha512(hashlib.sha512(encodeVarint(toAddressVersion)+encodeVarint(toStreamNumber)+toRipe).digest()).digest()[32:]
                if toRipe in shared.neededPubkeys or toTag in shared.neededPubkeys:
                    # We already sent a request for the pubkey
                    sqlExecute(
                        '''UPDATE sent SET status='awaitingpubkey' WHERE toaddress=? AND status='msgqueued' ''', toaddress)
                    shared.UISignalQueue.put(('updateSentItemStatusByHash', (
                        toRipe, tr.translateText("MainWindow",'Encryption key was requested earlier.'))))
                else:
                    # We have not yet sent a request for the pubkey
                    needToRequestPubkey = True
                    if toAddressVersion >= 4: # If we are trying to send to address version >= 4 then the needed pubkey might be encrypted in the inventory.
                        # If we have it we'll need to decrypt it and put it in the pubkeys table.
                        queryreturn = sqlQuery(
                            '''SELECT payload FROM inventory WHERE objecttype='pubkey' and tag=? ''', toTag)
                        if queryreturn != []: # if there was a pubkey in our inventory with the correct tag, we need to try to decrypt it.
                            for row in queryreturn:
                                data, = row
                                if shared.decryptAndCheckPubkeyPayload(data, toaddress) == 'successful':
                                    needToRequestPubkey = False
                                    print 'debug. successfully decrypted and checked pubkey from sql inventory.' #testing
                                    sqlExecute(
                                        '''UPDATE sent SET status='doingmsgpow' WHERE toaddress=? AND status='msgqueued' ''',
                                        toaddress)
                                    break
                                else: # There was something wrong with this pubkey even though it had the correct tag- almost certainly because of malicious behavior or a badly programmed client.
                                    continue
                        if needToRequestPubkey: # Obviously we had no success looking in the sql inventory. Let's look through the memory inventory.
                            with shared.inventoryLock:
                                for hash, storedValue in shared.inventory.items():
                                    objectType, streamNumber, payload, receivedTime, tag = storedValue
                                    if objectType == 'pubkey' and tag == toTag:
                                        result = shared.decryptAndCheckPubkeyPayload(payload, toaddress) #if valid, this function also puts it in the pubkeys table.
                                        if result == 'successful':
                                            print 'debug. successfully decrypted and checked pubkey from memory inventory.'
                                            needToRequestPubkey = False
                                            sqlExecute(
                                                '''UPDATE sent SET status='doingmsgpow' WHERE toaddress=? AND status='msgqueued' ''',
                                                toaddress)
                                            break
                    if needToRequestPubkey:
                        sqlExecute(
                            '''UPDATE sent SET status='doingpubkeypow' WHERE toaddress=? AND status='msgqueued' ''',
                            toaddress)
                        shared.UISignalQueue.put(('updateSentItemStatusByHash', (
                            toRipe, tr.translateText("MainWindow",'Sending a request for the recipient\'s encryption key.'))))
                        self.requestPubKey(toaddress)
        # Get all messages that are ready to be sent, and also all messages
        # which we have sent in the last 28 days which were previously marked
        # as 'toodifficult'. If the user as raised the maximum acceptable
        # difficulty then those messages may now be sendable.
        queryreturn = sqlQuery(
            '''SELECT toaddress, toripe, fromaddress, subject, message, ackdata, status FROM sent WHERE (status='doingmsgpow' or status='forcepow' or (status='toodifficult' and lastactiontime>?)) and folder='sent' ''',
            int(time.time()) - 2419200)
        for row in queryreturn:  # For each message we need to send..
            toaddress, toripe, fromaddress, subject, message, ackdata, status = row
            toStatus, toAddressVersionNumber, toStreamNumber, toHash = decodeAddress(
                toaddress)
            fromStatus, fromAddressVersionNumber, fromStreamNumber, fromHash = decodeAddress(
                fromaddress)

            if not shared.config.has_section(toaddress):
                # There is a remote possibility that we may no longer have the
                # recipient's pubkey. Let us make sure we still have it or else the
                # sendMsg function will appear to freeze. This can happen if the
                # user sends a message but doesn't let the POW function finish,
                # then leaves their client off for a long time which could cause
                # the needed pubkey to expire and be deleted.
                queryreturn = sqlQuery(
                    '''SELECT hash FROM pubkeys WHERE hash=? AND addressversion=?''',
                    toripe,
                    toAddressVersionNumber)
                if queryreturn == [] and toripe not in shared.neededPubkeys:
                    # We no longer have the needed pubkey and we haven't requested
                    # it.
                    with shared.printLock:
                        sys.stderr.write(
                            'For some reason, the status of a message in our outbox is \'doingmsgpow\' even though we lack the pubkey. Here is the RIPE hash of the needed pubkey: %s\n' % toripe.encode('hex'))
                    sqlExecute(
                        '''UPDATE sent SET status='doingpubkeypow' WHERE toaddress=? AND status='doingmsgpow' ''', toaddress)
                    shared.UISignalQueue.put(('updateSentItemStatusByHash', (
                        toripe, tr.translateText("MainWindow",'Sending a request for the recipient\'s encryption key.'))))
                    self.requestPubKey(toaddress)
                    continue
                shared.ackdataForWhichImWatching[ackdata] = 0
                shared.UISignalQueue.put(('updateSentItemStatusByAckdata', (
                    ackdata, tr.translateText("MainWindow", "Looking up the receiver\'s public key"))))
                with shared.printLock:
                    print 'Sending a message. First 150 characters of message:', repr(message[:150])


                # mark the pubkey as 'usedpersonally' so that we don't ever delete
                # it.
                sqlExecute(
                    '''UPDATE pubkeys SET usedpersonally='yes' WHERE hash=? and addressversion=?''',
                    toripe,
                    toAddressVersionNumber)
                # Let us fetch the recipient's public key out of our database. If
                # the required proof of work difficulty is too hard then we'll
                # abort.
                queryreturn = sqlQuery(
                    'SELECT transmitdata FROM pubkeys WHERE hash=? and addressversion=?',
                    toripe,
                    toAddressVersionNumber)
                if queryreturn == []:
                    with shared.printLock:
                        sys.stderr.write(
                            '(within sendMsg) The needed pubkey was not found. This should never happen. Aborting send.\n')

                    return
                for row in queryreturn:
                    pubkeyPayload, = row

                # The pubkey message is stored the way we originally received it
                # which means that we need to read beyond things like the nonce and
                # time to get to the actual public keys.
                if toAddressVersionNumber <= 3:
                    readPosition = 8  # to bypass the nonce
                elif toAddressVersionNumber >= 4:
                    readPosition = 0 # the nonce is not included here so we don't need to skip over it.
                pubkeyEmbeddedTime, = unpack(
                    '>I', pubkeyPayload[readPosition:readPosition + 4])
                # This section is used for the transition from 32 bit time to 64
                # bit time in the protocol.
                if pubkeyEmbeddedTime == 0:
                    pubkeyEmbeddedTime, = unpack(
                        '>Q', pubkeyPayload[readPosition:readPosition + 8])
                    readPosition += 8
                else:
                    readPosition += 4
                readPosition += 1  # to bypass the address version whose length is definitely 1
                streamNumber, streamNumberLength = decodeVarint(
                    pubkeyPayload[readPosition:readPosition + 10])
                readPosition += streamNumberLength
                behaviorBitfield = pubkeyPayload[readPosition:readPosition + 4]
                # Mobile users may ask us to include their address's RIPE hash on a message
                # unencrypted. Before we actually do it the sending human must check a box
                # in the settings menu to allow it.
                if shared.isBitSetWithinBitfield(behaviorBitfield,30): # if receiver is a mobile device who expects that their address RIPE is included unencrypted on the front of the message..
                    if not shared.safeConfigGetBoolean('bitmessagesettings','willinglysendtomobile'): # if we are Not willing to include the receiver's RIPE hash on the message..
                        logger.info('The receiver is a mobile user but the sender (you) has not selected that you are willing to send to mobiles. Aborting send.')
                        shared.UISignalQueue.put(('updateSentItemStatusByAckdata',(ackdata,tr.translateText("MainWindow",'Problem: Destination is a mobile device who requests that the destination be included in the message but this is disallowed in your settings.  %1').arg(unicode(strftime(shared.config.get('bitmessagesettings', 'timeformat'),localtime(int(time.time()))),'utf-8')))))
                        # if the human changes their setting and then sends another message or restarts their client, this one will send at that time.
                        continue
                readPosition += 4  # to bypass the bitfield of behaviors
                # pubSigningKeyBase256 =
                # pubkeyPayload[readPosition:readPosition+64] #We don't use this
                # key for anything here.
                readPosition += 64
                pubEncryptionKeyBase256 = pubkeyPayload[
                    readPosition:readPosition + 64]
                readPosition += 64

                # Let us fetch the amount of work required by the recipient.
                if toAddressVersionNumber == 2:
                    requiredAverageProofOfWorkNonceTrialsPerByte = shared.networkDefaultProofOfWorkNonceTrialsPerByte
                    requiredPayloadLengthExtraBytes = shared.networkDefaultPayloadLengthExtraBytes
                    shared.UISignalQueue.put(('updateSentItemStatusByAckdata', (
                        ackdata, tr.translateText("MainWindow", "Doing work necessary to send message.\nThere is no required difficulty for version 2 addresses like this."))))
                elif toAddressVersionNumber >= 3:
                    requiredAverageProofOfWorkNonceTrialsPerByte, varintLength = decodeVarint(
                        pubkeyPayload[readPosition:readPosition + 10])
                    readPosition += varintLength
                    requiredPayloadLengthExtraBytes, varintLength = decodeVarint(
                        pubkeyPayload[readPosition:readPosition + 10])
                    readPosition += varintLength
                    if requiredAverageProofOfWorkNonceTrialsPerByte < shared.networkDefaultProofOfWorkNonceTrialsPerByte:  # We still have to meet a minimum POW difficulty regardless of what they say is allowed in order to get our message to propagate through the network.
                        requiredAverageProofOfWorkNonceTrialsPerByte = shared.networkDefaultProofOfWorkNonceTrialsPerByte
                    if requiredPayloadLengthExtraBytes < shared.networkDefaultPayloadLengthExtraBytes:
                        requiredPayloadLengthExtraBytes = shared.networkDefaultPayloadLengthExtraBytes
                    shared.UISignalQueue.put(('updateSentItemStatusByAckdata', (ackdata, tr.translateText("MainWindow", "Doing work necessary to send message.\nReceiver\'s required difficulty: %1 and %2").arg(str(float(
                        requiredAverageProofOfWorkNonceTrialsPerByte) / shared.networkDefaultProofOfWorkNonceTrialsPerByte)).arg(str(float(requiredPayloadLengthExtraBytes) / shared.networkDefaultPayloadLengthExtraBytes)))))
                    if status != 'forcepow':
                        if (requiredAverageProofOfWorkNonceTrialsPerByte > shared.config.getint('bitmessagesettings', 'maxacceptablenoncetrialsperbyte') and shared.config.getint('bitmessagesettings', 'maxacceptablenoncetrialsperbyte') != 0) or (requiredPayloadLengthExtraBytes > shared.config.getint('bitmessagesettings', 'maxacceptablepayloadlengthextrabytes') and shared.config.getint('bitmessagesettings', 'maxacceptablepayloadlengthextrabytes') != 0):
                            # The demanded difficulty is more than we are willing
                            # to do.
                            sqlExecute(
                                '''UPDATE sent SET status='toodifficult' WHERE ackdata=? ''',
                                ackdata)
                            shared.UISignalQueue.put(('updateSentItemStatusByAckdata', (ackdata, tr.translateText("MainWindow", "Problem: The work demanded by the recipient (%1 and %2) is more difficult than you are willing to do.").arg(str(float(requiredAverageProofOfWorkNonceTrialsPerByte) / shared.networkDefaultProofOfWorkNonceTrialsPerByte)).arg(str(float(
                                requiredPayloadLengthExtraBytes) / shared.networkDefaultPayloadLengthExtraBytes)).arg(unicode(strftime(shared.config.get('bitmessagesettings', 'timeformat'), localtime(int(time.time()))), 'utf-8')))))
                            continue
            else: # if we are sending a message to ourselves or a chan..
                with shared.printLock:
                    print 'Sending a message. First 150 characters of message:', repr(message[:150])
                behaviorBitfield = '\x00\x00\x00\x01'

                try:
                    privEncryptionKeyBase58 = shared.config.get(
                        toaddress, 'privencryptionkey')
                except Exception as err:
                    shared.UISignalQueue.put(('updateSentItemStatusByAckdata',(ackdata,tr.translateText("MainWindow",'Problem: You are trying to send a message to yourself or a chan but your encryption key could not be found in the keys.dat file. Could not encrypt message. %1').arg(unicode(strftime(shared.config.get('bitmessagesettings', 'timeformat'),localtime(int(time.time()))),'utf-8')))))
                    with shared.printLock:
                        sys.stderr.write(
                            'Error within sendMsg. Could not read the keys from the keys.dat file for our own address. %s\n' % err)
                    continue
                privEncryptionKeyHex = shared.decodeWalletImportFormat(
                    privEncryptionKeyBase58).encode('hex')
                pubEncryptionKeyBase256 = highlevelcrypto.privToPub(
                    privEncryptionKeyHex).decode('hex')[1:]
                requiredAverageProofOfWorkNonceTrialsPerByte = shared.networkDefaultProofOfWorkNonceTrialsPerByte
                requiredPayloadLengthExtraBytes = shared.networkDefaultPayloadLengthExtraBytes
                shared.UISignalQueue.put(('updateSentItemStatusByAckdata', (
                    ackdata, tr.translateText("MainWindow", "Doing work necessary to send message."))))

            embeddedTime = pack('>Q', (int(time.time()) + random.randrange(
                -300, 300)))  # the current time plus or minus five minutes.
            if fromAddressVersionNumber == 2:
                payload = '\x01'  # Message version.
                payload += encodeVarint(fromAddressVersionNumber)
                payload += encodeVarint(fromStreamNumber)
                payload += '\x00\x00\x00\x01'  # Bitfield of features and behaviors that can be expected from me. (See https://bitmessage.org/wiki/Protocol_specification#Pubkey_bitfield_features  )

                # We need to convert our private keys to public keys in order
                # to include them.
                try:
                    privSigningKeyBase58 = shared.config.get(
                        fromaddress, 'privsigningkey')
                    privEncryptionKeyBase58 = shared.config.get(
                        fromaddress, 'privencryptionkey')
                except:
                    shared.UISignalQueue.put(('updateSentItemStatusByAckdata', (
                        ackdata, tr.translateText("MainWindow", "Error! Could not find sender address (your address) in the keys.dat file."))))
                    continue

                privSigningKeyHex = shared.decodeWalletImportFormat(
                    privSigningKeyBase58).encode('hex')
                privEncryptionKeyHex = shared.decodeWalletImportFormat(
                    privEncryptionKeyBase58).encode('hex')

                pubSigningKey = highlevelcrypto.privToPub(
                    privSigningKeyHex).decode('hex')
                pubEncryptionKey = highlevelcrypto.privToPub(
                    privEncryptionKeyHex).decode('hex')

                payload += pubSigningKey[
                    1:]  # The \x04 on the beginning of the public keys are not sent. This way there is only one acceptable way to encode and send a public key.
                payload += pubEncryptionKey[1:]

                payload += toHash  # This hash will be checked by the receiver of the message to verify that toHash belongs to them. This prevents a Surreptitious Forwarding Attack.
                payload += '\x02'  # Type 2 is simple UTF-8 message encoding as specified on the Protocol Specification on the Bitmessage Wiki.
                messageToTransmit = 'Subject:' + \
                    subject + '\n' + 'Body:' + message
                payload += encodeVarint(len(messageToTransmit))
                payload += messageToTransmit
                fullAckPayload = self.generateFullAckMessage(
                    ackdata, toStreamNumber)  # The fullAckPayload is a normal msg protocol message with the proof of work already completed that the receiver of this message can easily send out.
                payload += encodeVarint(len(fullAckPayload))
                payload += fullAckPayload
                signature = highlevelcrypto.sign(payload, privSigningKeyHex)
                payload += encodeVarint(len(signature))
                payload += signature

            if fromAddressVersionNumber >= 3:
                payload = '\x01'  # Message version.
                payload += encodeVarint(fromAddressVersionNumber)
                payload += encodeVarint(fromStreamNumber)
                payload += '\x00\x00\x00\x01'  # Bitfield of features and behaviors that can be expected from me. (See https://bitmessage.org/wiki/Protocol_specification#Pubkey_bitfield_features  )

                # We need to convert our private keys to public keys in order
                # to include them.
                try:
                    privSigningKeyBase58 = shared.config.get(
                        fromaddress, 'privsigningkey')
                    privEncryptionKeyBase58 = shared.config.get(
                        fromaddress, 'privencryptionkey')
                except:
                    shared.UISignalQueue.put(('updateSentItemStatusByAckdata', (
                        ackdata, tr.translateText("MainWindow", "Error! Could not find sender address (your address) in the keys.dat file."))))
                    continue

                privSigningKeyHex = shared.decodeWalletImportFormat(
                    privSigningKeyBase58).encode('hex')
                privEncryptionKeyHex = shared.decodeWalletImportFormat(
                    privEncryptionKeyBase58).encode('hex')

                pubSigningKey = highlevelcrypto.privToPub(
                    privSigningKeyHex).decode('hex')
                pubEncryptionKey = highlevelcrypto.privToPub(
                    privEncryptionKeyHex).decode('hex')

                payload += pubSigningKey[
                    1:]  # The \x04 on the beginning of the public keys are not sent. This way there is only one acceptable way to encode and send a public key.
                payload += pubEncryptionKey[1:]
                # If the receiver of our message is in our address book,
                # subscriptions list, or whitelist then we will allow them to
                # do the network-minimum proof of work. Let us check to see if
                # the receiver is in any of those lists.
                if shared.isAddressInMyAddressBookSubscriptionsListOrWhitelist(toaddress):
                    payload += encodeVarint(
                        shared.networkDefaultProofOfWorkNonceTrialsPerByte)
                    payload += encodeVarint(
                        shared.networkDefaultPayloadLengthExtraBytes)
                else:
                    payload += encodeVarint(shared.config.getint(
                        fromaddress, 'noncetrialsperbyte'))
                    payload += encodeVarint(shared.config.getint(
                        fromaddress, 'payloadlengthextrabytes'))

                payload += toHash  # This hash will be checked by the receiver of the message to verify that toHash belongs to them. This prevents a Surreptitious Forwarding Attack.
                payload += '\x02'  # Type 2 is simple UTF-8 message encoding as specified on the Protocol Specification on the Bitmessage Wiki.
                messageToTransmit = 'Subject:' + \
                    subject + '\n' + 'Body:' + message
                payload += encodeVarint(len(messageToTransmit))
                payload += messageToTransmit
                if shared.config.has_section(toaddress):
                    with shared.printLock:
                        print 'Not bothering to include ackdata because we are sending to ourselves or a chan.'
                    fullAckPayload = ''
                elif not shared.isBitSetWithinBitfield(behaviorBitfield,31):
                    with shared.printLock:
                        print 'Not bothering to include ackdata because the receiver said that they won\'t relay it anyway.'
                    fullAckPayload = ''                    
                else:
                    fullAckPayload = self.generateFullAckMessage(
                        ackdata, toStreamNumber)  # The fullAckPayload is a normal msg protocol message with the proof of work already completed that the receiver of this message can easily send out.
                payload += encodeVarint(len(fullAckPayload))
                payload += fullAckPayload
                signature = highlevelcrypto.sign(payload, privSigningKeyHex)
                payload += encodeVarint(len(signature))
                payload += signature

            print 'using pubEncryptionKey:', pubEncryptionKeyBase256.encode('hex')
            # We have assembled the data that will be encrypted.
            try:
                encrypted = highlevelcrypto.encrypt(payload,"04"+pubEncryptionKeyBase256.encode('hex'))
            except:
                sqlExecute('''UPDATE sent SET status='badkey' WHERE ackdata=?''', ackdata)
                shared.UISignalQueue.put(('updateSentItemStatusByAckdata',(ackdata,tr.translateText("MainWindow",'Problem: The recipient\'s encryption key is no good. Could not encrypt message. %1').arg(unicode(strftime(shared.config.get('bitmessagesettings', 'timeformat'),localtime(int(time.time()))),'utf-8')))))
                continue
            encryptedPayload = embeddedTime + encodeVarint(toStreamNumber) + encrypted
            target = 2**64 / ((len(encryptedPayload)+requiredPayloadLengthExtraBytes+8) * requiredAverageProofOfWorkNonceTrialsPerByte)
            with shared.printLock:
                print '(For msg message) Doing proof of work. Total required difficulty:', float(requiredAverageProofOfWorkNonceTrialsPerByte) / shared.networkDefaultProofOfWorkNonceTrialsPerByte, 'Required small message difficulty:', float(requiredPayloadLengthExtraBytes) / shared.networkDefaultPayloadLengthExtraBytes

            powStartTime = time.time()
            initialHash = hashlib.sha512(encryptedPayload).digest()
            trialValue, nonce = proofofwork.run(target, initialHash)
            with shared.printLock:
                print '(For msg message) Found proof of work', trialValue, 'Nonce:', nonce
                try:
                    print 'POW took', int(time.time() - powStartTime), 'seconds.', nonce / (time.time() - powStartTime), 'nonce trials per second.'
                except:
                    pass

            encryptedPayload = pack('>Q', nonce) + encryptedPayload

            inventoryHash = calculateInventoryHash(encryptedPayload)
            objectType = 'msg'
            shared.inventory[inventoryHash] = (
                objectType, toStreamNumber, encryptedPayload, int(time.time()),'')
            shared.inventorySets[toStreamNumber].add(inventoryHash)
            if shared.config.has_section(toaddress):
                shared.UISignalQueue.put(('updateSentItemStatusByAckdata', (ackdata, tr.translateText("MainWindow", "Message sent. Sent on %1").arg(unicode(
                    strftime(shared.config.get('bitmessagesettings', 'timeformat'), localtime(int(time.time()))), 'utf-8')))))
            else:
                # not sending to a chan or one of my addresses
                shared.UISignalQueue.put(('updateSentItemStatusByAckdata', (ackdata, tr.translateText("MainWindow", "Message sent. Waiting for acknowledgement. Sent on %1").arg(unicode(
                    strftime(shared.config.get('bitmessagesettings', 'timeformat'), localtime(int(time.time()))), 'utf-8')))))
            print 'Broadcasting inv for my msg(within sendmsg function):', inventoryHash.encode('hex')
            shared.broadcastToSendDataQueues((
                toStreamNumber, 'advertiseobject', inventoryHash))

            # Update the status of the message in the 'sent' table to have a
            # 'msgsent' status or 'msgsentnoackexpected' status.
            if shared.config.has_section(toaddress):
                newStatus = 'msgsentnoackexpected'
            else:
                newStatus = 'msgsent'
            sqlExecute('''UPDATE sent SET msgid=?, status=? WHERE ackdata=?''',
                       inventoryHash,newStatus,ackdata)

            # If we are sending to ourselves or a chan, let's put the message in
            # our own inbox.
            if shared.config.has_section(toaddress):
                t = (inventoryHash, toaddress, fromaddress, subject, int(
                    time.time()), message, 'inbox', 2, 0)
                helper_inbox.insert(t)

                shared.UISignalQueue.put(('displayNewInboxMessage', (
                    inventoryHash, toaddress, fromaddress, subject, message)))

                # If we are behaving as an API then we might need to run an
                # outside command to let some program know that a new message
                # has arrived.
                if shared.safeConfigGetBoolean('bitmessagesettings', 'apienabled'):
                    try:
                        apiNotifyPath = shared.config.get(
                            'bitmessagesettings', 'apinotifypath')
                    except:
                        apiNotifyPath = ''
                    if apiNotifyPath != '':
                        call([apiNotifyPath, "newMessage"])

    def requestPubKey(self, toAddress):
        toStatus, addressVersionNumber, streamNumber, ripe = decodeAddress(
            toAddress)
        if toStatus != 'success':
            with shared.printLock:
                sys.stderr.write('Very abnormal error occurred in requestPubKey. toAddress is: ' + repr(
                    toAddress) + '. Please report this error to Atheros.')

            return
        if addressVersionNumber <= 3:
            shared.neededPubkeys[ripe] = 0
        elif addressVersionNumber >= 4:
            privEncryptionKey = hashlib.sha512(hashlib.sha512(encodeVarint(addressVersionNumber)+encodeVarint(streamNumber)+ripe).digest()).digest()[:32] # Note that this is the first half of the sha512 hash.
            tag = hashlib.sha512(hashlib.sha512(encodeVarint(addressVersionNumber)+encodeVarint(streamNumber)+ripe).digest()).digest()[32:] # Note that this is the second half of the sha512 hash.
            shared.neededPubkeys[tag] = highlevelcrypto.makeCryptor(privEncryptionKey.encode('hex')) # We'll need this for when we receive a pubkey reply: it will be encrypted and we'll need to decrypt it.
        payload = pack('>Q', (int(time.time()) + random.randrange(
            -300, 300)))  # the current time plus or minus five minutes.
        payload += encodeVarint(addressVersionNumber)
        payload += encodeVarint(streamNumber)
        if addressVersionNumber <= 3:
            payload += ripe
            with shared.printLock:
                print 'making request for pubkey with ripe:', ripe.encode('hex')
        else:
            payload += tag
            with shared.printLock:
                print 'making request for v4 pubkey with tag:', tag.encode('hex')

        # print 'trial value', trialValue
        statusbar = 'Doing the computations necessary to request the recipient\'s public key.'
        shared.UISignalQueue.put(('updateStatusBar', statusbar))
        shared.UISignalQueue.put(('updateSentItemStatusByHash', (
            ripe, tr.translateText("MainWindow",'Doing work necessary to request encryption key.'))))
        target = 2 ** 64 / ((len(payload) + shared.networkDefaultPayloadLengthExtraBytes +
                             8) * shared.networkDefaultProofOfWorkNonceTrialsPerByte)
        initialHash = hashlib.sha512(payload).digest()
        trialValue, nonce = proofofwork.run(target, initialHash)
        with shared.printLock:
            print 'Found proof of work', trialValue, 'Nonce:', nonce


        payload = pack('>Q', nonce) + payload
        inventoryHash = calculateInventoryHash(payload)
        objectType = 'getpubkey'
        shared.inventory[inventoryHash] = (
            objectType, streamNumber, payload, int(time.time()),'')
        shared.inventorySets[streamNumber].add(inventoryHash)
        print 'sending inv (for the getpubkey message)'
        shared.broadcastToSendDataQueues((
            streamNumber, 'advertiseobject', inventoryHash))

        sqlExecute(
            '''UPDATE sent SET status='awaitingpubkey' WHERE toaddress=? AND status='doingpubkeypow' ''',
            toAddress)

        shared.UISignalQueue.put((
            'updateStatusBar', tr.translateText("MainWindow",'Broacasting the public key request. This program will auto-retry if they are offline.')))
        shared.UISignalQueue.put(('updateSentItemStatusByHash', (ripe, tr.translateText("MainWindow",'Sending public key request. Waiting for reply. Requested at %1').arg(unicode(
            strftime(shared.config.get('bitmessagesettings', 'timeformat'), localtime(int(time.time()))), 'utf-8')))))

    def generateFullAckMessage(self, ackdata, toStreamNumber):
        embeddedTime = pack('>Q', (int(time.time()) + random.randrange(
            -300, 300)))  # the current time plus or minus five minutes.
        payload = embeddedTime + encodeVarint(toStreamNumber) + ackdata
        target = 2 ** 64 / ((len(payload) + shared.networkDefaultPayloadLengthExtraBytes +
                             8) * shared.networkDefaultProofOfWorkNonceTrialsPerByte)
        with shared.printLock:
            print '(For ack message) Doing proof of work...'

        powStartTime = time.time()
        initialHash = hashlib.sha512(payload).digest()
        trialValue, nonce = proofofwork.run(target, initialHash)
        with shared.printLock:
            print '(For ack message) Found proof of work', trialValue, 'Nonce:', nonce
            try:
                print 'POW took', int(time.time() - powStartTime), 'seconds.', nonce / (time.time() - powStartTime), 'nonce trials per second.'
            except:
                pass

        payload = pack('>Q', nonce) + payload
        headerData = '\xe9\xbe\xb4\xd9'  # magic bits, slighly different from Bitcoin's magic bits.
        headerData += 'msg\x00\x00\x00\x00\x00\x00\x00\x00\x00'
        headerData += pack('>L', len(payload))
        headerData += hashlib.sha512(payload).digest()[:4]
        return headerData + payload

########NEW FILE########
__FILENAME__ = class_sqlThread
import threading
import shared
import sqlite3
import time
import shutil  # used for moving the messages.dat file
import sys
import os
from debug import logger
from namecoin import ensureNamecoinOptions
import random
import string
import tr#anslate

# This thread exists because SQLITE3 is so un-threadsafe that we must
# submit queries to it and it puts results back in a different queue. They
# won't let us just use locks.


class sqlThread(threading.Thread):

    def __init__(self):
        threading.Thread.__init__(self)

    def run(self):        
        self.conn = sqlite3.connect(shared.appdata + 'messages.dat')
        self.conn.text_factory = str
        self.cur = self.conn.cursor()

        try:
            self.cur.execute(
                '''CREATE TABLE inbox (msgid blob, toaddress text, fromaddress text, subject text, received text, message text, folder text, encodingtype int, read bool, UNIQUE(msgid) ON CONFLICT REPLACE)''' )
            self.cur.execute(
                '''CREATE TABLE sent (msgid blob, toaddress text, toripe blob, fromaddress text, subject text, message text, ackdata blob, lastactiontime integer, status text, pubkeyretrynumber integer, msgretrynumber integer, folder text, encodingtype int)''' )
            self.cur.execute(
                '''CREATE TABLE subscriptions (label text, address text, enabled bool)''' )
            self.cur.execute(
                '''CREATE TABLE addressbook (label text, address text)''' )
            self.cur.execute(
                '''CREATE TABLE blacklist (label text, address text, enabled bool)''' )
            self.cur.execute(
                '''CREATE TABLE whitelist (label text, address text, enabled bool)''' )
            # Explanation of what is in the pubkeys table:
            #   The hash is the RIPEMD160 hash that is encoded in the Bitmessage address.
            #   transmitdata is literally the data that was included in the Bitmessage pubkey message when it arrived, except for the 24 byte protocol header- ie, it starts with the POW nonce.
            #   time is the time that the pubkey was broadcast on the network same as with every other type of Bitmessage object.
            # usedpersonally is set to "yes" if we have used the key
            # personally. This keeps us from deleting it because we may want to
            # reply to a message in the future. This field is not a bool
            # because we may need more flexability in the future and it doesn't
            # take up much more space anyway.
            self.cur.execute(
                '''CREATE TABLE pubkeys (hash blob, addressversion int, transmitdata blob, time int, usedpersonally text, UNIQUE(hash, addressversion) ON CONFLICT REPLACE)''' )
            self.cur.execute(
                '''CREATE TABLE inventory (hash blob, objecttype text, streamnumber int, payload blob, receivedtime integer, tag blob, UNIQUE(hash) ON CONFLICT REPLACE)''' )
            self.cur.execute(
                '''INSERT INTO subscriptions VALUES('Bitmessage new releases/announcements','BM-GtovgYdgs7qXPkoYaRgrLFuFKz1SFpsw',1)''')
            self.cur.execute(
                '''CREATE TABLE settings (key blob, value blob, UNIQUE(key) ON CONFLICT REPLACE)''' )
            self.cur.execute( '''INSERT INTO settings VALUES('version','6')''')
            self.cur.execute( '''INSERT INTO settings VALUES('lastvacuumtime',?)''', (
                int(time.time()),))
            self.cur.execute(
                '''CREATE TABLE objectprocessorqueue (objecttype text, data blob, UNIQUE(objecttype, data) ON CONFLICT REPLACE)''' )
            self.conn.commit()
            logger.info('Created messages database file')
        except Exception as err:
            if str(err) == 'table inbox already exists':
                logger.debug('Database file already exists.')

            else:
                sys.stderr.write(
                    'ERROR trying to create database file (message.dat). Error message: %s\n' % str(err))
                os._exit(0)

        if shared.config.getint('bitmessagesettings', 'settingsversion') == 1:
            shared.config.set('bitmessagesettings', 'settingsversion', '2')
                      # If the settings version is equal to 2 or 3 then the
                      # sqlThread will modify the pubkeys table and change
                      # the settings version to 4.
            shared.config.set('bitmessagesettings', 'socksproxytype', 'none')
            shared.config.set('bitmessagesettings', 'sockshostname', 'localhost')
            shared.config.set('bitmessagesettings', 'socksport', '9050')
            shared.config.set('bitmessagesettings', 'socksauthentication', 'false')
            shared.config.set('bitmessagesettings', 'socksusername', '')
            shared.config.set('bitmessagesettings', 'sockspassword', '')
            shared.config.set('bitmessagesettings', 'sockslisten', 'false')
            shared.config.set('bitmessagesettings', 'keysencrypted', 'false')
            shared.config.set('bitmessagesettings', 'messagesencrypted', 'false')
            with open(shared.appdata + 'keys.dat', 'wb') as configfile:
                shared.config.write(configfile)

        # People running earlier versions of PyBitmessage do not have the
        # usedpersonally field in their pubkeys table. Let's add it.
        if shared.config.getint('bitmessagesettings', 'settingsversion') == 2:
            item = '''ALTER TABLE pubkeys ADD usedpersonally text DEFAULT 'no' '''
            parameters = ''
            self.cur.execute(item, parameters)
            self.conn.commit()

            shared.config.set('bitmessagesettings', 'settingsversion', '3')
            with open(shared.appdata + 'keys.dat', 'wb') as configfile:
                shared.config.write(configfile)

        # People running earlier versions of PyBitmessage do not have the
        # encodingtype field in their inbox and sent tables or the read field
        # in the inbox table. Let's add them.
        if shared.config.getint('bitmessagesettings', 'settingsversion') == 3:
            item = '''ALTER TABLE inbox ADD encodingtype int DEFAULT '2' '''
            parameters = ''
            self.cur.execute(item, parameters)

            item = '''ALTER TABLE inbox ADD read bool DEFAULT '1' '''
            parameters = ''
            self.cur.execute(item, parameters)

            item = '''ALTER TABLE sent ADD encodingtype int DEFAULT '2' '''
            parameters = ''
            self.cur.execute(item, parameters)
            self.conn.commit()

            shared.config.set('bitmessagesettings', 'settingsversion', '4')
            with open(shared.appdata + 'keys.dat', 'wb') as configfile:
                shared.config.write(configfile)

        if shared.config.getint('bitmessagesettings', 'settingsversion') == 4:
            shared.config.set('bitmessagesettings', 'defaultnoncetrialsperbyte', str(
                shared.networkDefaultProofOfWorkNonceTrialsPerByte))
            shared.config.set('bitmessagesettings', 'defaultpayloadlengthextrabytes', str(
                shared.networkDefaultPayloadLengthExtraBytes))
            shared.config.set('bitmessagesettings', 'settingsversion', '5')

        if shared.config.getint('bitmessagesettings', 'settingsversion') == 5:
            shared.config.set(
                'bitmessagesettings', 'maxacceptablenoncetrialsperbyte', '0')
            shared.config.set(
                'bitmessagesettings', 'maxacceptablepayloadlengthextrabytes', '0')
            shared.config.set('bitmessagesettings', 'settingsversion', '6')
            with open(shared.appdata + 'keys.dat', 'wb') as configfile:
                shared.config.write(configfile)

        # From now on, let us keep a 'version' embedded in the messages.dat
        # file so that when we make changes to the database, the database
        # version we are on can stay embedded in the messages.dat file. Let us
        # check to see if the settings table exists yet.
        item = '''SELECT name FROM sqlite_master WHERE type='table' AND name='settings';'''
        parameters = ''
        self.cur.execute(item, parameters)
        if self.cur.fetchall() == []:
            # The settings table doesn't exist. We need to make it.
            logger.debug('In messages.dat database, creating new \'settings\' table.')
            self.cur.execute(
                '''CREATE TABLE settings (key text, value blob, UNIQUE(key) ON CONFLICT REPLACE)''' )
            self.cur.execute( '''INSERT INTO settings VALUES('version','1')''')
            self.cur.execute( '''INSERT INTO settings VALUES('lastvacuumtime',?)''', (
                int(time.time()),))
            logger.debug('In messages.dat database, removing an obsolete field from the pubkeys table.')
            self.cur.execute(
                '''CREATE TEMPORARY TABLE pubkeys_backup(hash blob, transmitdata blob, time int, usedpersonally text, UNIQUE(hash) ON CONFLICT REPLACE);''')
            self.cur.execute(
                '''INSERT INTO pubkeys_backup SELECT hash, transmitdata, time, usedpersonally FROM pubkeys;''')
            self.cur.execute( '''DROP TABLE pubkeys''')
            self.cur.execute(
                '''CREATE TABLE pubkeys (hash blob, transmitdata blob, time int, usedpersonally text, UNIQUE(hash) ON CONFLICT REPLACE)''' )
            self.cur.execute(
                '''INSERT INTO pubkeys SELECT hash, transmitdata, time, usedpersonally FROM pubkeys_backup;''')
            self.cur.execute( '''DROP TABLE pubkeys_backup;''')
            logger.debug('Deleting all pubkeys from inventory. They will be redownloaded and then saved with the correct times.')
            self.cur.execute(
                '''delete from inventory where objecttype = 'pubkey';''')
            logger.debug('replacing Bitmessage announcements mailing list with a new one.')
            self.cur.execute(
                '''delete from subscriptions where address='BM-BbkPSZbzPwpVcYZpU4yHwf9ZPEapN5Zx' ''')
            self.cur.execute(
                '''INSERT INTO subscriptions VALUES('Bitmessage new releases/announcements','BM-GtovgYdgs7qXPkoYaRgrLFuFKz1SFpsw',1)''')
            logger.debug('Commiting.')
            self.conn.commit()
            logger.debug('Vacuuming message.dat. You might notice that the file size gets much smaller.')
            self.cur.execute( ''' VACUUM ''')

        # After code refactoring, the possible status values for sent messages
        # have changed.
        self.cur.execute(
            '''update sent set status='doingmsgpow' where status='doingpow'  ''')
        self.cur.execute(
            '''update sent set status='msgsent' where status='sentmessage'  ''')
        self.cur.execute(
            '''update sent set status='doingpubkeypow' where status='findingpubkey'  ''')
        self.cur.execute(
            '''update sent set status='broadcastqueued' where status='broadcastpending'  ''')
        self.conn.commit()
        
        if not shared.config.has_option('bitmessagesettings', 'sockslisten'):
            shared.config.set('bitmessagesettings', 'sockslisten', 'false')
            
        ensureNamecoinOptions()
            
        """# Add a new column to the inventory table to store the first 20 bytes of encrypted messages to support Android app
        item = '''SELECT value FROM settings WHERE key='version';'''
        parameters = ''
        self.cur.execute(item, parameters)
        if int(self.cur.fetchall()[0][0]) == 1:
            print 'upgrading database'
            item = '''ALTER TABLE inventory ADD first20bytesofencryptedmessage blob DEFAULT '' '''
            parameters = ''
            self.cur.execute(item, parameters)
            item = '''update settings set value=? WHERE key='version';'''
            parameters = (2,)
            self.cur.execute(item, parameters)"""

        # Let's get rid of the first20bytesofencryptedmessage field in the inventory table.
        item = '''SELECT value FROM settings WHERE key='version';'''
        parameters = ''
        self.cur.execute(item, parameters)
        if int(self.cur.fetchall()[0][0]) == 2:
            logger.debug('In messages.dat database, removing an obsolete field from the inventory table.')
            self.cur.execute(
                '''CREATE TEMPORARY TABLE inventory_backup(hash blob, objecttype text, streamnumber int, payload blob, receivedtime integer, UNIQUE(hash) ON CONFLICT REPLACE);''')
            self.cur.execute(
                '''INSERT INTO inventory_backup SELECT hash, objecttype, streamnumber, payload, receivedtime FROM inventory;''')
            self.cur.execute( '''DROP TABLE inventory''')
            self.cur.execute(
                '''CREATE TABLE inventory (hash blob, objecttype text, streamnumber int, payload blob, receivedtime integer, UNIQUE(hash) ON CONFLICT REPLACE)''' )
            self.cur.execute(
                '''INSERT INTO inventory SELECT hash, objecttype, streamnumber, payload, receivedtime FROM inventory_backup;''')
            self.cur.execute( '''DROP TABLE inventory_backup;''')
            item = '''update settings set value=? WHERE key='version';'''
            parameters = (3,)
            self.cur.execute(item, parameters)

        # Add a new column to the inventory table to store tags.
        item = '''SELECT value FROM settings WHERE key='version';'''
        parameters = ''
        self.cur.execute(item, parameters)
        currentVersion = int(self.cur.fetchall()[0][0])
        if currentVersion == 1 or currentVersion == 3:
            logger.debug('In messages.dat database, adding tag field to the inventory table.')
            item = '''ALTER TABLE inventory ADD tag blob DEFAULT '' '''
            parameters = ''
            self.cur.execute(item, parameters)
            item = '''update settings set value=? WHERE key='version';'''
            parameters = (4,)
            self.cur.execute(item, parameters)

        if not shared.config.has_option('bitmessagesettings', 'userlocale'):
            shared.config.set('bitmessagesettings', 'userlocale', 'system')
        if not shared.config.has_option('bitmessagesettings', 'sendoutgoingconnections'):
            shared.config.set('bitmessagesettings', 'sendoutgoingconnections', 'True')

        # Raise the default required difficulty from 1 to 2
        if shared.config.getint('bitmessagesettings', 'settingsversion') == 6:
            if int(shared.config.get('bitmessagesettings','defaultnoncetrialsperbyte')) == shared.networkDefaultProofOfWorkNonceTrialsPerByte:
                shared.config.set('bitmessagesettings','defaultnoncetrialsperbyte', str(shared.networkDefaultProofOfWorkNonceTrialsPerByte * 2))
            shared.config.set('bitmessagesettings', 'settingsversion', '7')
            with open(shared.appdata + 'keys.dat', 'wb') as configfile:
                shared.config.write(configfile)

        # Add a new column to the pubkeys table to store the address version.
        # We're going to trash all of our pubkeys and let them be redownloaded.
        item = '''SELECT value FROM settings WHERE key='version';'''
        parameters = ''
        self.cur.execute(item, parameters)
        currentVersion = int(self.cur.fetchall()[0][0])
        if currentVersion == 4:
            self.cur.execute( '''DROP TABLE pubkeys''')
            self.cur.execute(
                '''CREATE TABLE pubkeys (hash blob, addressversion int, transmitdata blob, time int, usedpersonally text, UNIQUE(hash, addressversion) ON CONFLICT REPLACE)''' )
            self.cur.execute(
                '''delete from inventory where objecttype = 'pubkey';''')
            item = '''update settings set value=? WHERE key='version';'''
            parameters = (5,)
            self.cur.execute(item, parameters)
            
        if not shared.config.has_option('bitmessagesettings', 'useidenticons'):
            shared.config.set('bitmessagesettings', 'useidenticons', 'True')
        if not shared.config.has_option('bitmessagesettings', 'identiconsuffix'): # acts as a salt
            shared.config.set('bitmessagesettings', 'identiconsuffix', ''.join(random.choice("123456789ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz") for x in range(12))) # a twelve character pseudo-password to salt the identicons
            # Since we've added a new config entry, let's write keys.dat to disk.
            with open(shared.appdata + 'keys.dat', 'wb') as configfile:
                shared.config.write(configfile)

        #Adjusting time period to stop sending messages
        if shared.config.getint('bitmessagesettings', 'settingsversion') == 7:
            shared.config.set(
                'bitmessagesettings', 'stopresendingafterxdays', '')
            shared.config.set(
                'bitmessagesettings', 'stopresendingafterxmonths', '')
            #shared.config.set(
            shared.config.set('bitmessagesettings', 'settingsversion', '8') 
            with open(shared.appdata + 'keys.dat', 'wb') as configfile:
                shared.config.write(configfile)

        # Add a new table: objectprocessorqueue with which to hold objects
        # that have yet to be processed if the user shuts down Bitmessage.
        item = '''SELECT value FROM settings WHERE key='version';'''
        parameters = ''
        self.cur.execute(item, parameters)
        currentVersion = int(self.cur.fetchall()[0][0])
        if currentVersion == 5:
            self.cur.execute( '''DROP TABLE knownnodes''')
            self.cur.execute(
                '''CREATE TABLE objectprocessorqueue (objecttype text, data blob, UNIQUE(objecttype, data) ON CONFLICT REPLACE)''' )
            item = '''update settings set value=? WHERE key='version';'''
            parameters = (6,)
            self.cur.execute(item, parameters)

        # Are you hoping to add a new option to the keys.dat file of existing
        # Bitmessage users? Add it right above this line!
        
        try:
            testpayload = '\x00\x00'
            t = ('1234', 1, testpayload, '12345678', 'no')
            self.cur.execute( '''INSERT INTO pubkeys VALUES(?,?,?,?,?)''', t)
            self.conn.commit()
            self.cur.execute(
                '''SELECT transmitdata FROM pubkeys WHERE hash='1234' ''')
            queryreturn = self.cur.fetchall()
            for row in queryreturn:
                transmitdata, = row
            self.cur.execute('''DELETE FROM pubkeys WHERE hash='1234' ''')
            self.conn.commit()
            if transmitdata == '':
                logger.fatal('Problem: The version of SQLite you have cannot store Null values. Please download and install the latest revision of your version of Python (for example, the latest Python 2.7 revision) and try again.\n')
                logger.fatal('PyBitmessage will now exit very abruptly. You may now see threading errors related to this abrupt exit but the problem you need to solve is related to SQLite.\n\n')
                os._exit(0)
        except Exception as err:
            if str(err) == 'database or disk is full':
                logger.fatal('(While null value test) Alert: Your disk or data storage volume is full. sqlThread will now exit.')
                shared.UISignalQueue.put(('alert', (tr.translateText("MainWindow", "Disk full"), tr.translateText("MainWindow", 'Alert: Your disk or data storage volume is full. Bitmessage will now exit.'), True)))
                if shared.daemon:
                    os._exit(0)
                else:
                    return
            else:
                logger.error(err)

        # Let us check to see the last time we vaccumed the messages.dat file.
        # If it has been more than a month let's do it now.
        item = '''SELECT value FROM settings WHERE key='lastvacuumtime';'''
        parameters = ''
        self.cur.execute(item, parameters)
        queryreturn = self.cur.fetchall()
        for row in queryreturn:
            value, = row
            if int(value) < int(time.time()) - 2592000:
                logger.info('It has been a long time since the messages.dat file has been vacuumed. Vacuuming now...')
                try:
                    self.cur.execute( ''' VACUUM ''')
                except Exception as err:
                    if str(err) == 'database or disk is full':
                        logger.fatal('(While VACUUM) Alert: Your disk or data storage volume is full. sqlThread will now exit.')
                        shared.UISignalQueue.put(('alert', (tr.translateText("MainWindow", "Disk full"), tr.translateText("MainWindow", 'Alert: Your disk or data storage volume is full. Bitmessage will now exit.'), True)))
                        if shared.daemon:
                            os._exit(0)
                        else:
                            return
                item = '''update settings set value=? WHERE key='lastvacuumtime';'''
                parameters = (int(time.time()),)
                self.cur.execute(item, parameters)

        while True:
            item = shared.sqlSubmitQueue.get()
            if item == 'commit':
                try:
                    self.conn.commit()
                except Exception as err:
                    if str(err) == 'database or disk is full':
                        logger.fatal('(While committing) Alert: Your disk or data storage volume is full. sqlThread will now exit.')
                        shared.UISignalQueue.put(('alert', (tr.translateText("MainWindow", "Disk full"), tr.translateText("MainWindow", 'Alert: Your disk or data storage volume is full. Bitmessage will now exit.'), True)))
                        if shared.daemon:
                            os._exit(0)
                        else:
                            return
            elif item == 'exit':
                self.conn.close()
                logger.info('sqlThread exiting gracefully.')

                return
            elif item == 'movemessagstoprog':
                logger.debug('the sqlThread is moving the messages.dat file to the local program directory.')

                try:
                    self.conn.commit()
                except Exception as err:
                    if str(err) == 'database or disk is full':
                        logger.fatal('(while movemessagstoprog) Alert: Your disk or data storage volume is full. sqlThread will now exit.')
                        shared.UISignalQueue.put(('alert', (tr.translateText("MainWindow", "Disk full"), tr.translateText("MainWindow", 'Alert: Your disk or data storage volume is full. Bitmessage will now exit.'), True)))
                        if shared.daemon:
                            os._exit(0)
                        else:
                            return
                self.conn.close()
                shutil.move(
                    shared.lookupAppdataFolder() + 'messages.dat', 'messages.dat')
                self.conn = sqlite3.connect('messages.dat')
                self.conn.text_factory = str
                self.cur = self.conn.cursor()
            elif item == 'movemessagstoappdata':
                logger.debug('the sqlThread is moving the messages.dat file to the Appdata folder.')

                try:
                    self.conn.commit()
                except Exception as err:
                    if str(err) == 'database or disk is full':
                        logger.fatal('(while movemessagstoappdata) Alert: Your disk or data storage volume is full. sqlThread will now exit.')
                        shared.UISignalQueue.put(('alert', (tr.translateText("MainWindow", "Disk full"), tr.translateText("MainWindow", 'Alert: Your disk or data storage volume is full. Bitmessage will now exit.'), True)))
                        if shared.daemon:
                            os._exit(0)
                        else:
                            return
                self.conn.close()
                shutil.move(
                    'messages.dat', shared.lookupAppdataFolder() + 'messages.dat')
                self.conn = sqlite3.connect(shared.appdata + 'messages.dat')
                self.conn.text_factory = str
                self.cur = self.conn.cursor()
            elif item == 'deleteandvacuume':
                self.cur.execute('''delete from inbox where folder='trash' ''')
                self.cur.execute('''delete from sent where folder='trash' ''')
                self.conn.commit()
                try:
                    self.cur.execute( ''' VACUUM ''')
                except Exception as err:
                    if str(err) == 'database or disk is full':
                        logger.fatal('(while deleteandvacuume) Alert: Your disk or data storage volume is full. sqlThread will now exit.')
                        shared.UISignalQueue.put(('alert', (tr.translateText("MainWindow", "Disk full"), tr.translateText("MainWindow", 'Alert: Your disk or data storage volume is full. Bitmessage will now exit.'), True)))
                        if shared.daemon:
                            os._exit(0)
                        else:
                            return
            else:
                parameters = shared.sqlSubmitQueue.get()
                # print 'item', item
                # print 'parameters', parameters
                try:
                    self.cur.execute(item, parameters)
                except Exception as err:
                    if str(err) == 'database or disk is full':
                        logger.fatal('(while cur.execute) Alert: Your disk or data storage volume is full. sqlThread will now exit.')
                        shared.UISignalQueue.put(('alert', (tr.translateText("MainWindow", "Disk full"), tr.translateText("MainWindow", 'Alert: Your disk or data storage volume is full. Bitmessage will now exit.'), True)))
                        if shared.daemon:
                            os._exit(0)
                        else:
                            return
                    else:
                        logger.fatal('Major error occurred when trying to execute a SQL statement within the sqlThread. Please tell Atheros about this error message or post it in the forum! Error occurred while trying to execute statement: "%s"  Here are the parameters; you might want to censor this data with asterisks (***) as it can contain private information: %s. Here is the actual error message thrown by the sqlThread: %s', str(item), str(repr(parameters)),  str(err))
                        logger.fatal('This program shall now abruptly exit!')

                    os._exit(0)

                shared.sqlReturnQueue.put(self.cur.fetchall())
                # shared.sqlSubmitQueue.task_done()

########NEW FILE########
__FILENAME__ = debug
# -*- coding: utf-8 -*-
'''
Logging and debuging facility
=============================

Levels:
    DEBUG       Detailed information, typically of interest only when diagnosing problems.
    INFO        Confirmation that things are working as expected.
    WARNING     An indication that something unexpected happened, or indicative of some problem in the
                near future (e.g. ‘disk space low’). The software is still working as expected.
    ERROR       Due to a more serious problem, the software has not been able to perform some function.
    CRITICAL    A serious error, indicating that the program itself may be unable to continue running.

There are three loggers: `console_only`, `file_only` and `both`.

Use: `from debug import logger` to import this facility into whatever module you wish to log messages from.
     Logging is thread-safe so you don't have to worry about locks, just import and log.
'''
import logging
import logging.config
import shared

# TODO(xj9): Get from a config file.
log_level = 'DEBUG'

def configureLogging():
    logging.config.dictConfig({
        'version': 1,
        'formatters': {
            'default': {
                'format': '%(asctime)s - %(levelname)s - %(message)s',
            },
        },
        'handlers': {
            'console': {
                'class': 'logging.StreamHandler',
                'formatter': 'default',
                'level': log_level,
                'stream': 'ext://sys.stdout'
            },
            'file': {
                'class': 'logging.handlers.RotatingFileHandler',
                'formatter': 'default',
                'level': log_level,
                'filename': shared.appdata + 'debug.log',
                'maxBytes': 2097152, # 2 MiB
                'backupCount': 1,
            }
        },
        'loggers': {
            'console_only': {
                'handlers': ['console'],
                'propagate' : 0
            },
            'file_only': {
                'handlers': ['file'],
                'propagate' : 0
            },
            'both': {
                'handlers': ['console', 'file'],
                'propagate' : 0
            },
        },
        'root': {
            'level': log_level,
            'handlers': ['console'],
        },
    })
# TODO (xj9): Get from a config file.
#logger = logging.getLogger('console_only')
configureLogging()
logger = logging.getLogger('both')

def restartLoggingInUpdatedAppdataLocation():
    global logger
    for i in list(logger.handlers):
        logger.removeHandler(i)
        i.flush()
        i.close()
    configureLogging()
    logger = logging.getLogger('both')
########NEW FILE########
__FILENAME__ = defaultKnownNodes
import pickle
import socket
from struct import *
import time
import random
import sys
from time import strftime, localtime
import shared

def createDefaultKnownNodes(appdata):
    ############## Stream 1 ################
    stream1 = {}

    #stream1[shared.Peer('2604:2000:1380:9f:82e:148b:2746:d0c7', 8080)] = int(time.time())
    stream1[shared.Peer('68.33.0.104', 8444)] = int(time.time())
    stream1[shared.Peer('97.77.34.35', 8444)] = int(time.time())
    stream1[shared.Peer('71.232.195.131', 8444)] = int(time.time())
    stream1[shared.Peer('192.241.231.39', 8444)] = int(time.time())
    stream1[shared.Peer('75.66.0.116', 8444)] = int(time.time())
    stream1[shared.Peer('182.169.23.102', 8444)] = int(time.time())
    stream1[shared.Peer('75.95.134.9', 8444)] = int(time.time())
    stream1[shared.Peer('46.236.100.108', 48444)] = int(time.time())
    stream1[shared.Peer('66.108.53.42', 8080)] = int(time.time())
    
    ############# Stream 2 #################
    stream2 = {}
    # None yet

    ############# Stream 3 #################
    stream3 = {}
    # None yet

    allKnownNodes = {}
    allKnownNodes[1] = stream1
    allKnownNodes[2] = stream2
    allKnownNodes[3] = stream3

    #print stream1
    #print allKnownNodes

    with open(appdata + 'knownnodes.dat', 'wb') as output:
        # Pickle dictionary using protocol 0.
        pickle.dump(allKnownNodes, output)

    return allKnownNodes

def readDefaultKnownNodes(appdata):
    pickleFile = open(appdata + 'knownnodes.dat', 'rb')
    knownNodes = pickle.load(pickleFile)
    pickleFile.close()
    for stream, storedValue in knownNodes.items():
        for host,value in storedValue.items():
            try:
                # Old knownNodes format.
                port, storedtime = value
            except:
                # New knownNodes format.
                host, port = host
                storedtime = value
            print host, '\t', port, '\t', unicode(strftime('%a, %d %b %Y  %I:%M %p',localtime(storedtime)),'utf-8')

if __name__ == "__main__":

    APPNAME = "PyBitmessage"
    from os import path, environ
    if sys.platform == 'darwin':
        from AppKit import NSSearchPathForDirectoriesInDomains  # @UnresolvedImport
        # http://developer.apple.com/DOCUMENTATION/Cocoa/Reference/Foundation/Miscellaneous/Foundation_Functions/Reference/reference.html#//apple_ref/c/func/NSSearchPathForDirectoriesInDomains
        # NSApplicationSupportDirectory = 14
        # NSUserDomainMask = 1
        # True for expanding the tilde into a fully qualified path
        appdata = path.join(NSSearchPathForDirectoriesInDomains(14, 1, True)[0], APPNAME) + '/'
    elif 'win' in sys.platform:
        appdata = path.join(environ['APPDATA'], APPNAME) + '\\'
    else:
        appdata = path.expanduser(path.join("~", "." + APPNAME + "/"))


    print 'New list of all known nodes:', createDefaultKnownNodes(appdata)
    readDefaultKnownNodes(appdata)



########NEW FILE########
__FILENAME__ = helper_bitcoin
import hashlib
from pyelliptic import arithmetic

# This function expects that pubkey begin with \x04
def calculateBitcoinAddressFromPubkey(pubkey):
    if len(pubkey) != 65:
        print 'Could not calculate Bitcoin address from pubkey because function was passed a pubkey that was', len(pubkey), 'bytes long rather than 65.'
        return "error"
    ripe = hashlib.new('ripemd160')
    sha = hashlib.new('sha256')
    sha.update(pubkey)
    ripe.update(sha.digest())
    ripeWithProdnetPrefix = '\x00' + ripe.digest()

    checksum = hashlib.sha256(hashlib.sha256(
        ripeWithProdnetPrefix).digest()).digest()[:4]
    binaryBitcoinAddress = ripeWithProdnetPrefix + checksum
    numberOfZeroBytesOnBinaryBitcoinAddress = 0
    while binaryBitcoinAddress[0] == '\x00':
        numberOfZeroBytesOnBinaryBitcoinAddress += 1
        binaryBitcoinAddress = binaryBitcoinAddress[1:]
    base58encoded = arithmetic.changebase(binaryBitcoinAddress, 256, 58)
    return "1" * numberOfZeroBytesOnBinaryBitcoinAddress + base58encoded


def calculateTestnetAddressFromPubkey(pubkey):
    if len(pubkey) != 65:
        print 'Could not calculate Bitcoin address from pubkey because function was passed a pubkey that was', len(pubkey), 'bytes long rather than 65.'
        return "error"
    ripe = hashlib.new('ripemd160')
    sha = hashlib.new('sha256')
    sha.update(pubkey)
    ripe.update(sha.digest())
    ripeWithProdnetPrefix = '\x6F' + ripe.digest()

    checksum = hashlib.sha256(hashlib.sha256(
        ripeWithProdnetPrefix).digest()).digest()[:4]
    binaryBitcoinAddress = ripeWithProdnetPrefix + checksum
    numberOfZeroBytesOnBinaryBitcoinAddress = 0
    while binaryBitcoinAddress[0] == '\x00':
        numberOfZeroBytesOnBinaryBitcoinAddress += 1
        binaryBitcoinAddress = binaryBitcoinAddress[1:]
    base58encoded = arithmetic.changebase(binaryBitcoinAddress, 256, 58)
    return "1" * numberOfZeroBytesOnBinaryBitcoinAddress + base58encoded

########NEW FILE########
__FILENAME__ = helper_bootstrap
import shared
import socket
import defaultKnownNodes
import pickle
import time

def knownNodes():
    try:
        # We shouldn't have to use the shared.knownNodesLock because this had
        # better be the only thread accessing knownNodes right now.
        pickleFile = open(shared.appdata + 'knownnodes.dat', 'rb')
        loadedKnownNodes = pickle.load(pickleFile)
        pickleFile.close()
        # The old format of storing knownNodes was as a 'host: (port, time)'
        # mapping. The new format is as 'Peer: time' pairs. If we loaded
        # data in the old format, transform it to the new style.
        for stream, nodes in loadedKnownNodes.items():
            shared.knownNodes[stream] = {}
            for node_tuple in nodes.items():
                try:
                    host, (port, time) = node_tuple
                    peer = shared.Peer(host, port)
                except:
                    peer, time = node_tuple
                shared.knownNodes[stream][peer] = time
    except:
        shared.knownNodes = defaultKnownNodes.createDefaultKnownNodes(shared.appdata)
    if shared.config.getint('bitmessagesettings', 'settingsversion') > 8:
        print 'Bitmessage cannot read future versions of the keys file (keys.dat). Run the newer version of Bitmessage.'
        raise SystemExit

def dns():
    # DNS bootstrap. This could be programmed to use the SOCKS proxy to do the
    # DNS lookup some day but for now we will just rely on the entries in
    # defaultKnownNodes.py. Hopefully either they are up to date or the user
    # has run Bitmessage recently without SOCKS turned on and received good
    # bootstrap nodes using that method.
    with shared.printLock:
        if shared.config.get('bitmessagesettings', 'socksproxytype') == 'none':
            try:
                for item in socket.getaddrinfo('bootstrap8080.bitmessage.org', 80):
                    print 'Adding', item[4][0], 'to knownNodes based on DNS boostrap method'
                    shared.knownNodes[1][shared.Peer(item[4][0], 8080)] = int(time.time())
            except:
                print 'bootstrap8080.bitmessage.org DNS bootstrapping failed.'
            try:
                for item in socket.getaddrinfo('bootstrap8444.bitmessage.org', 80):
                    print 'Adding', item[4][0], 'to knownNodes based on DNS boostrap method'
                    shared.knownNodes[1][shared.Peer(item[4][0], 8444)] = int(time.time())
            except:
                print 'bootstrap8444.bitmessage.org DNS bootstrapping failed.'
        else:
            print 'DNS bootstrap skipped because SOCKS is used.'


########NEW FILE########
__FILENAME__ = helper_generic
import shared
import sys

def convertIntToString(n):
    a = __builtins__.hex(n)
    if a[-1:] == 'L':
        a = a[:-1]
    if (len(a) % 2) == 0:
        return a[2:].decode('hex')
    else:
        return ('0' + a[2:]).decode('hex')


def convertStringToInt(s):
    return int(s.encode('hex'), 16)


def signal_handler(signal, frame):
    if shared.safeConfigGetBoolean('bitmessagesettings', 'daemon'):
        shared.doCleanShutdown()
        sys.exit(0)
    else:
        print 'Unfortunately you cannot use Ctrl+C when running the UI because the UI captures the signal.'

def isHostInPrivateIPRange(host):
    if host[:3] == '10.':
        return True
    if host[:4] == '172.':
        if host[6] == '.':
            if int(host[4:6]) >= 16 and int(host[4:6]) <= 31:
                return True
    if host[:8] == '192.168.':
        return True
    return False

########NEW FILE########
__FILENAME__ = helper_inbox
from helper_sql import *
import shared

def insert(t):
    sqlExecute('''INSERT INTO inbox VALUES (?,?,?,?,?,?,?,?,?)''', *t)
    shared.UISignalQueue.put(('changedInboxUnread', None))
    
def trash(msgid):
    sqlExecute('''UPDATE inbox SET folder='trash' WHERE msgid=?''', msgid)
    shared.UISignalQueue.put(('removeInboxRowByMsgid',msgid))
    

########NEW FILE########
__FILENAME__ = helper_sent
from helper_sql import *

def insert(t):
    sqlExecute('''INSERT INTO sent VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)''', *t)

########NEW FILE########
__FILENAME__ = helper_sql
import threading
import Queue

sqlSubmitQueue = Queue.Queue() #SQLITE3 is so thread-unsafe that they won't even let you call it from different threads using your own locks. SQL objects can only be called from one thread.
sqlReturnQueue = Queue.Queue()
sqlLock = threading.Lock()

def sqlQuery(sqlStatement, *args):
    sqlLock.acquire()
    sqlSubmitQueue.put(sqlStatement)

    if args == ():
        sqlSubmitQueue.put('')
    else:
        sqlSubmitQueue.put(args)
    
    queryreturn = sqlReturnQueue.get()
    sqlLock.release()

    return queryreturn

def sqlExecute(sqlStatement, *args):
    sqlLock.acquire()
    sqlSubmitQueue.put(sqlStatement)

    if args == ():
        sqlSubmitQueue.put('')
    else:
        sqlSubmitQueue.put(args)
    
    sqlReturnQueue.get()
    sqlSubmitQueue.put('commit')
    sqlLock.release()

def sqlStoredProcedure(procName):
    sqlLock.acquire()
    sqlSubmitQueue.put(procName)
    sqlLock.release()

class SqlBulkExecute:
    def __enter__(self):
        sqlLock.acquire()
        return self

    def __exit__(self, type, value, traceback):
        sqlSubmitQueue.put('commit')
        sqlLock.release()

    def execute(self, sqlStatement, *args):
        sqlSubmitQueue.put(sqlStatement)
        
        if args == ():
            sqlSubmitQueue.put('')
        else:
            sqlSubmitQueue.put(args)
        sqlReturnQueue.get()

    def query(self, sqlStatement, *args):
        sqlSubmitQueue.put(sqlStatement)

        if args == ():
            sqlSubmitQueue.put('')
        else:
            sqlSubmitQueue.put(args)
        return sqlReturnQueue.get()


########NEW FILE########
__FILENAME__ = helper_startup
import shared
import ConfigParser
import sys
import os
import locale
import random
import string
import platform
from distutils.version import StrictVersion

from namecoin import ensureNamecoinOptions

storeConfigFilesInSameDirectoryAsProgramByDefault = False  # The user may de-select Portable Mode in the settings if they want the config files to stay in the application data folder.

def _loadTrustedPeer():
    try:
        trustedPeer = shared.config.get('bitmessagesettings', 'trustedpeer')
    except ConfigParser.Error:
        # This probably means the trusted peer wasn't specified so we
        # can just leave it as None
        return

    host, port = trustedPeer.split(':')
    shared.trustedPeer = shared.Peer(host, int(port))

def loadConfig():
    if shared.appdata:
        shared.config.read(shared.appdata + 'keys.dat')
        #shared.appdata must have been specified as a startup option.
        try:
            shared.config.get('bitmessagesettings', 'settingsversion')
            print 'Loading config files from directory specified on startup: ' + shared.appdata
            needToCreateKeysFile = False
        except:
            needToCreateKeysFile = True

    else:
        shared.config.read('keys.dat')
        try:
            shared.config.get('bitmessagesettings', 'settingsversion')
            print 'Loading config files from same directory as program.'
            needToCreateKeysFile = False
            shared.appdata = ''
        except:
            # Could not load the keys.dat file in the program directory. Perhaps it
            # is in the appdata directory.
            shared.appdata = shared.lookupAppdataFolder()
            shared.config.read(shared.appdata + 'keys.dat')
            try:
                shared.config.get('bitmessagesettings', 'settingsversion')
                print 'Loading existing config files from', shared.appdata
                needToCreateKeysFile = False
            except:
                needToCreateKeysFile = True

    if needToCreateKeysFile:
        # This appears to be the first time running the program; there is
        # no config file (or it cannot be accessed). Create config file.
        shared.config.add_section('bitmessagesettings')
        shared.config.set('bitmessagesettings', 'settingsversion', '8')
        shared.config.set('bitmessagesettings', 'port', '8444')
        shared.config.set(
            'bitmessagesettings', 'timeformat', '%%a, %%d %%b %%Y  %%I:%%M %%p')
        shared.config.set('bitmessagesettings', 'blackwhitelist', 'black')
        shared.config.set('bitmessagesettings', 'startonlogon', 'false')
        if 'linux' in sys.platform:
            shared.config.set(
                'bitmessagesettings', 'minimizetotray', 'false')
                              # This isn't implimented yet and when True on
                              # Ubuntu causes Bitmessage to disappear while
                              # running when minimized.
        else:
            shared.config.set(
                'bitmessagesettings', 'minimizetotray', 'true')
        shared.config.set(
            'bitmessagesettings', 'showtraynotifications', 'true')
        shared.config.set('bitmessagesettings', 'startintray', 'false')
        shared.config.set('bitmessagesettings', 'socksproxytype', 'none')
        shared.config.set(
            'bitmessagesettings', 'sockshostname', 'localhost')
        shared.config.set('bitmessagesettings', 'socksport', '9050')
        shared.config.set(
            'bitmessagesettings', 'socksauthentication', 'false')
        shared.config.set(
            'bitmessagesettings', 'sockslisten', 'false')
        shared.config.set('bitmessagesettings', 'socksusername', '')
        shared.config.set('bitmessagesettings', 'sockspassword', '')
        shared.config.set('bitmessagesettings', 'keysencrypted', 'false')
        shared.config.set(
            'bitmessagesettings', 'messagesencrypted', 'false')
        shared.config.set('bitmessagesettings', 'defaultnoncetrialsperbyte', str(
            shared.networkDefaultProofOfWorkNonceTrialsPerByte * 2))
        shared.config.set('bitmessagesettings', 'defaultpayloadlengthextrabytes', str(
            shared.networkDefaultPayloadLengthExtraBytes))
        shared.config.set('bitmessagesettings', 'minimizeonclose', 'false')
        shared.config.set(
            'bitmessagesettings', 'maxacceptablenoncetrialsperbyte', '0')
        shared.config.set(
            'bitmessagesettings', 'maxacceptablepayloadlengthextrabytes', '0')
        shared.config.set('bitmessagesettings', 'dontconnect', 'true')
        shared.config.set('bitmessagesettings', 'userlocale', 'system')
        shared.config.set('bitmessagesettings', 'useidenticons', 'True')
        shared.config.set('bitmessagesettings', 'identiconsuffix', ''.join(random.choice("123456789ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz") for x in range(12))) # a twelve character pseudo-password to salt the identicons
        shared.config.set('bitmessagesettings', 'replybelow', 'False')
        
         #start:UI setting to stop trying to send messages after X days/months
        shared.config.set(
            'bitmessagesettings', 'stopresendingafterxdays', '')
        shared.config.set(
            'bitmessagesettings', 'stopresendingafterxmonths', '')
        #shared.config.set(
        #    'bitmessagesettings', 'timeperiod', '-1')
        #end

        # Are you hoping to add a new option to the keys.dat file? You're in
        # the right place for adding it to users who install the software for
        # the first time. But you must also add it to the keys.dat file of
        # existing users. To do that, search the class_sqlThread.py file for the
        # text: "right above this line!"

        ensureNamecoinOptions()

        if storeConfigFilesInSameDirectoryAsProgramByDefault:
            # Just use the same directory as the program and forget about
            # the appdata folder
            shared.appdata = ''
            print 'Creating new config files in same directory as program.'
        else:
            print 'Creating new config files in', shared.appdata
            if not os.path.exists(shared.appdata):
                os.makedirs(shared.appdata)
        if not sys.platform.startswith('win'):
            os.umask(0o077)
        with open(shared.appdata + 'keys.dat', 'wb') as configfile:
            shared.config.write(configfile)

    _loadTrustedPeer()

def isOurOperatingSystemLimitedToHavingVeryFewHalfOpenConnections():
    try:
        VER_THIS=StrictVersion(platform.version())
        if sys.platform[0:3]=="win":
            return StrictVersion("5.1.2600")<=VER_THIS and StrictVersion("6.0.6000")>=VER_THIS
        return False
    except Exception as err:
        print 'An Exception occurred within isOurOperatingSystemLimitedToHavingVeryFewHalfOpenConnections:', err
        return False

########NEW FILE########
__FILENAME__ = highlevelcrypto
import pyelliptic
from pyelliptic import arithmetic as a
def makeCryptor(privkey):
  privkey_bin = '\x02\xca\x00 '+a.changebase(privkey,16,256,minlen=32)
  pubkey = a.changebase(a.privtopub(privkey),16,256,minlen=65)[1:]
  pubkey_bin = '\x02\xca\x00 '+pubkey[:32]+'\x00 '+pubkey[32:]
  cryptor = pyelliptic.ECC(curve='secp256k1',privkey=privkey_bin,pubkey=pubkey_bin)
  return cryptor
def hexToPubkey(pubkey):
  pubkey_raw = a.changebase(pubkey[2:],16,256,minlen=64)
  pubkey_bin = '\x02\xca\x00 '+pubkey_raw[:32]+'\x00 '+pubkey_raw[32:]
  return pubkey_bin
def makePubCryptor(pubkey):
  pubkey_bin = hexToPubkey(pubkey)
  return pyelliptic.ECC(curve='secp256k1',pubkey=pubkey_bin)
# Converts hex private key into hex public key
def privToPub(privkey):
  return a.privtopub(privkey)
# Encrypts message with hex public key
def encrypt(msg,hexPubkey):
  return pyelliptic.ECC(curve='secp256k1').encrypt(msg,hexToPubkey(hexPubkey))
# Decrypts message with hex private key
def decrypt(msg,hexPrivkey):
  return makeCryptor(hexPrivkey).decrypt(msg)
# Decrypts message with an existing pyelliptic.ECC.ECC object
def decryptFast(msg,cryptor):
  return cryptor.decrypt(msg)
# Signs with hex private key
def sign(msg,hexPrivkey):
  return makeCryptor(hexPrivkey).sign(msg)
# Verifies with hex public key
def verify(msg,sig,hexPubkey):
  return makePubCryptor(hexPubkey).verify(sig,msg)

########NEW FILE########
__FILENAME__ = message_data_reader
#This program can be used to print out everything in your Inbox or Sent folders and also take things out of the trash.
#Scroll down to the bottom to see the functions that you can uncomment. Save then run this file.
#The functions which only read the database file seem to function just fine even if you have Bitmessage running but you should definitly close it before running the functions that make changes (like taking items out of the trash).

import sqlite3
from time import strftime, localtime
import sys
import shared
import string

appdata = shared.lookupAppdataFolder()

conn = sqlite3.connect( appdata + 'messages.dat' )
conn.text_factory = str
cur = conn.cursor()

def readInbox():
    print 'Printing everything in inbox table:'
    item = '''select * from inbox'''
    parameters = ''
    cur.execute(item, parameters)
    output = cur.fetchall()
    for row in output:
        print row

def readSent():
    print 'Printing everything in Sent table:'
    item = '''select * from sent where folder !='trash' '''
    parameters = ''
    cur.execute(item, parameters)
    output = cur.fetchall()
    for row in output:
        msgid, toaddress, toripe, fromaddress, subject, message, ackdata, lastactiontime, status, pubkeyretrynumber, msgretrynumber, folder, encodingtype = row
        print msgid.encode('hex'), toaddress, 'toripe:', toripe.encode('hex'), 'fromaddress:', fromaddress, 'ENCODING TYPE:', encodingtype, 'SUBJECT:', repr(subject), 'MESSAGE:', repr(message), 'ACKDATA:', ackdata.encode('hex'), lastactiontime, status, pubkeyretrynumber, msgretrynumber, folder

def readSubscriptions():
    print 'Printing everything in subscriptions table:'
    item = '''select * from subscriptions'''
    parameters = ''
    cur.execute(item, parameters)
    output = cur.fetchall()
    for row in output:
        print row

def readPubkeys():
    print 'Printing everything in pubkeys table:'
    item = '''select hash, transmitdata, time, usedpersonally from pubkeys'''
    parameters = ''
    cur.execute(item, parameters)
    output = cur.fetchall()
    for row in output:
        hash, transmitdata, time, usedpersonally = row
        print 'Hash:', hash.encode('hex'), '\tTime first broadcast:', unicode(strftime('%a, %d %b %Y  %I:%M %p',localtime(time)),'utf-8'), '\tUsed by me personally:', usedpersonally, '\tFull pubkey message:', transmitdata.encode('hex')

def readInventory():
    print 'Printing everything in inventory table:'
    item = '''select hash, objecttype, streamnumber, payload, receivedtime from inventory'''
    parameters = ''
    cur.execute(item, parameters)
    output = cur.fetchall()
    for row in output:
        hash, objecttype, streamnumber, payload, receivedtime = row
        print 'Hash:', hash.encode('hex'), objecttype, streamnumber, '\t', payload.encode('hex'), '\t', unicode(strftime('%a, %d %b %Y  %I:%M %p',localtime(receivedtime)),'utf-8')


def takeInboxMessagesOutOfTrash():
    item = '''update inbox set folder='inbox' where folder='trash' '''
    parameters = ''
    cur.execute(item, parameters)
    output = cur.fetchall()
    conn.commit()
    print 'done'

def takeSentMessagesOutOfTrash():
    item = '''update sent set folder='sent' where folder='trash' '''
    parameters = ''
    cur.execute(item, parameters)
    output = cur.fetchall()
    conn.commit()
    print 'done'

def markAllInboxMessagesAsUnread():
    item = '''update inbox set read='0' '''
    parameters = ''
    cur.execute(item, parameters)
    output = cur.fetchall()
    conn.commit()
    shared.UISignalQueue.put(('changedInboxUnread', None))
    print 'done'

def vacuum():
    item = '''VACUUM'''
    parameters = ''
    cur.execute(item, parameters)
    output = cur.fetchall()
    conn.commit()
    print 'done'

#takeInboxMessagesOutOfTrash()
#takeSentMessagesOutOfTrash()
#markAllInboxMessagesAsUnread()
readInbox()
#readSent()
#readPubkeys()
#readSubscriptions()
#readInventory()
#vacuum()  #will defragment and clean empty space from the messages.dat file.




########NEW FILE########
__FILENAME__ = namecoin
# Copyright (C) 2013 by Daniel Kraft <d@domob.eu>
# This file is part of the Bitmessage project.
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.

import base64
import json
import socket
import sys
import os

import shared
import tr # translate

configSection = "bitmessagesettings"

# Error thrown when the RPC call returns an error.
class RPCError (Exception):
    error = None

    def __init__ (self, data):
        self.error = data

# This class handles the Namecoin identity integration.
class namecoinConnection (object):
    user = None
    password = None
    host = None
    port = None
    nmctype = None
    bufsize = 4096
    queryid = 1

    # Initialise.  If options are given, take the connection settings from
    # them instead of loading from the configs.  This can be used to test
    # currently entered connection settings in the config dialog without
    # actually changing the values (yet).
    def __init__ (self, options = None):
        if options is None:
          self.nmctype = shared.config.get (configSection, "namecoinrpctype")
          self.host = shared.config.get (configSection, "namecoinrpchost")
          self.port = shared.config.get (configSection, "namecoinrpcport")
          self.user = shared.config.get (configSection, "namecoinrpcuser")
          self.password = shared.config.get (configSection,
                                             "namecoinrpcpassword")
        else:
          self.nmctype = options["type"]
          self.host = options["host"]
          self.port = options["port"]
          self.user = options["user"]
          self.password = options["password"]

        assert self.nmctype == "namecoind" or self.nmctype == "nmcontrol"

    # Query for the bitmessage address corresponding to the given identity
    # string.  If it doesn't contain a slash, id/ is prepended.  We return
    # the result as (Error, Address) pair, where the Error is an error
    # message to display or None in case of success.
    def query (self, string):
        slashPos = string.find ("/")
        if slashPos < 0:
            string = "id/" + string

        try:
            if self.nmctype == "namecoind":
                res = self.callRPC ("name_show", [string])
                res = res["value"]
            elif self.nmctype == "nmcontrol":
                res = self.callRPC ("data", ["getValue", string])
                res = res["reply"]
                if res == False:
                    raise RPCError ({"code": -4})
            else:
                assert False
        except RPCError as exc:
            if exc.error["code"] == -4:
                return (tr.translateText("MainWindow",'The name %1 was not found.').arg(unicode(string)), None)
            else:
                return (tr.translateText("MainWindow",'The namecoin query failed (%1)').arg(unicode(exc.error["message"])), None)
        except Exception as exc:
            print "Namecoin query exception: %s" % str (exc)
            return (tr.translateText("MainWindow",'The namecoin query failed.'), None)

        try:
            val = json.loads (res)
        except:
            return (tr.translateText("MainWindow",'The name %1 has no valid JSON data.').arg(unicode(string)), None)            

        if "bitmessage" in val:
            return (None, val["bitmessage"])
        return (tr.translateText("MainWindow",'The name %1 has no associated Bitmessage address.').arg(unicode(string)), None) 

    # Test the connection settings.  This routine tries to query a "getinfo"
    # command, and builds either an error message or a success message with
    # some info from it.
    def test (self):
        try:
            if self.nmctype == "namecoind":
                res = self.callRPC ("getinfo", [])
                vers = res["version"]
                
                v3 = vers % 100
                vers = vers / 100
                v2 = vers % 100
                vers = vers / 100
                v1 = vers
                if v3 == 0:
                  versStr = "0.%d.%d" % (v1, v2)
                else:
                  versStr = "0.%d.%d.%d" % (v1, v2, v3)
                return ('success',  tr.translateText("MainWindow",'Success!  Namecoind version %1 running.').arg(unicode(versStr)) )

            elif self.nmctype == "nmcontrol":
                res = self.callRPC ("data", ["status"])
                prefix = "Plugin data running"
                if ("reply" in res) and res["reply"][:len(prefix)] == prefix:
                    return ('success', tr.translateText("MainWindow",'Success!  NMControll is up and running.'))

                print "Unexpected nmcontrol reply: %s" % res
                return ('failed',  tr.translateText("MainWindow",'Couldn\'t understand NMControl.'))

            else:
                assert False

        except Exception as exc:
            print "Namecoin connection test: %s" % str (exc)
            return ('failed', "The connection to namecoin failed.")

    # Helper routine that actually performs an JSON RPC call.
    def callRPC (self, method, params):
        data = {"method": method, "params": params, "id": self.queryid}
        if self.nmctype == "namecoind":
          resp = self.queryHTTP (json.dumps (data))
        elif self.nmctype == "nmcontrol":
          resp = self.queryServer (json.dumps (data))
        else:
          assert False
        val = json.loads (resp)

        if val["id"] != self.queryid:
            raise Exception ("ID mismatch in JSON RPC answer.")
        self.queryid = self.queryid + 1

        if val["error"] is not None:
            raise RPCError (val["error"])

        return val["result"]

    # Query the server via HTTP.
    def queryHTTP (self, data):
        header = "POST / HTTP/1.1\n"
        header += "User-Agent: bitmessage\n"
        header += "Host: %s\n" % self.host
        header += "Content-Type: application/json\n"
        header += "Content-Length: %d\n" % len (data)
        header += "Accept: application/json\n"
        authstr = "%s:%s" % (self.user, self.password)
        header += "Authorization: Basic %s\n" % base64.b64encode (authstr)

        resp = self.queryServer ("%s\n%s" % (header, data))
        lines = resp.split ("\r\n")
        result = None
        body = False
        for line in lines:
            if line == "" and not body:
                body = True
            elif body:
                if result is not None:
                    raise Exception ("Expected a single line in HTTP response.")
                result = line

        return result

    # Helper routine sending data to the RPC server and returning the result.
    def queryServer (self, data):
        try:
            s = socket.socket (socket.AF_INET, socket.SOCK_STREAM)
            s.setsockopt (socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            s.settimeout(3) 
            s.connect ((self.host, int (self.port)))
            s.sendall (data)
            result = ""

            while True:
                tmp = s.recv (self.bufsize)
                if not tmp:
                  break
                result += tmp

            s.close ()

            return result

        except socket.error as exc:
            raise Exception ("Socket error in RPC connection: %s" % str (exc))

# Look up the namecoin data folder.
# FIXME: Check whether this works on other platforms as well!
def lookupNamecoinFolder ():
    app = "namecoin"
    from os import path, environ
    if sys.platform == "darwin":
        if "HOME" in environ:
            dataFolder = path.join (os.environ["HOME"],
                                    "Library/Application Support/", app) + '/'
        else:
            print ("Could not find home folder, please report this message"
                    + " and your OS X version to the BitMessage Github.")
            sys.exit()

    elif "win32" in sys.platform or "win64" in sys.platform:
        dataFolder = path.join(environ["APPDATA"], app) + "\\"
    else:
        dataFolder = path.join(environ["HOME"], ".%s" % app) + "/"

    return dataFolder

# Ensure all namecoin options are set, by setting those to default values
# that aren't there.
def ensureNamecoinOptions ():
    if not shared.config.has_option (configSection, "namecoinrpctype"):
        shared.config.set (configSection, "namecoinrpctype", "namecoind")
    if not shared.config.has_option (configSection, "namecoinrpchost"):
        shared.config.set (configSection, "namecoinrpchost", "localhost")

    hasUser = shared.config.has_option (configSection, "namecoinrpcuser")
    hasPass = shared.config.has_option (configSection, "namecoinrpcpassword")
    hasPort = shared.config.has_option (configSection, "namecoinrpcport")

    # Try to read user/password from .namecoin configuration file.
    defaultUser = ""
    defaultPass = ""
    try:
        nmcFolder = lookupNamecoinFolder ()
        nmcConfig = nmcFolder + "namecoin.conf"
        nmc = open (nmcConfig, "r")

        while True:
            line = nmc.readline ()
            if line == "":
                break
            parts = line.split ("=")
            if len (parts) == 2:
                key = parts[0]
                val = parts[1].rstrip ()

                if key == "rpcuser" and not hasUser:
                    defaultUser = val
                if key == "rpcpassword" and not hasPass:
                    defaultPass = val
                if key == "rpcport":
                    shared.namecoinDefaultRpcPort = val
                
        nmc.close ()

    except Exception as exc:
        print "Could not read the Namecoin config file probably because you don't have Namecoin installed. That's ok; we don't really need it. Detailed error message: %s" % str (exc)

    # If still nothing found, set empty at least.
    if (not hasUser):
        shared.config.set (configSection, "namecoinrpcuser", defaultUser)
    if (not hasPass):
        shared.config.set (configSection, "namecoinrpcpassword", defaultPass)

    # Set default port now, possibly to found value.
    if (not hasPort):
        shared.config.set (configSection, "namecoinrpcport",
                           shared.namecoinDefaultRpcPort)

########NEW FILE########
__FILENAME__ = proofofwork
#import shared
#import time
#from multiprocessing import Pool, cpu_count
import hashlib
from struct import unpack, pack
import sys
from shared import config, frozen
#import os

def _set_idle():
    if 'linux' in sys.platform:
        import os
        os.nice(20)  # @UndefinedVariable
    else:
        try:
            sys.getwindowsversion()
            import win32api,win32process,win32con  # @UnresolvedImport
            pid = win32api.GetCurrentProcessId()
            handle = win32api.OpenProcess(win32con.PROCESS_ALL_ACCESS, True, pid)
            win32process.SetPriorityClass(handle, win32process.IDLE_PRIORITY_CLASS)
        except:
            #Windows 64-bit
            pass

def _pool_worker(nonce, initialHash, target, pool_size):
    _set_idle()
    trialValue = float('inf')
    while trialValue > target:
        nonce += pool_size
        trialValue, = unpack('>Q',hashlib.sha512(hashlib.sha512(pack('>Q',nonce) + initialHash).digest()).digest()[0:8])
    return [trialValue, nonce]

def _doSafePoW(target, initialHash):
    nonce = 0
    trialValue = float('inf')
    while trialValue > target:
        nonce += 1
        trialValue, = unpack('>Q',hashlib.sha512(hashlib.sha512(pack('>Q',nonce) + initialHash).digest()).digest()[0:8])
    return [trialValue, nonce]

def _doFastPoW(target, initialHash):
    import shared
    import time
    from multiprocessing import Pool, cpu_count
    try:
        pool_size = cpu_count()
    except:
        pool_size = 4
    try:
        maxCores = config.getint('bitmessagesettings', 'maxcores')
    except:
        maxCores = 99999
    if pool_size > maxCores:
        pool_size = maxCores
    pool = Pool(processes=pool_size)
    result = []
    for i in range(pool_size):
        result.append(pool.apply_async(_pool_worker, args = (i, initialHash, target, pool_size)))
    while True:
        if shared.shutdown >= 1:
            pool.terminate()
            while True:
                time.sleep(10) # Don't let this thread return here; it will return nothing and cause an exception in bitmessagemain.py
            return
        for i in range(pool_size):
            if result[i].ready():
                result = result[i].get()
                pool.terminate()
                pool.join() #Wait for the workers to exit...
                return result[0], result[1]
        time.sleep(0.2)

def run(target, initialHash):
    if frozen == "macosx_app" or not frozen:
        return _doFastPoW(target, initialHash)
    else:
        return _doSafePoW(target, initialHash)

########NEW FILE########
__FILENAME__ = arithmetic
import hashlib, re

P = 2**256-2**32-2**9-2**8-2**7-2**6-2**4-1
A = 0
Gx = 55066263022277343669578718895168534326250603453777594175500187360389116729240
Gy = 32670510020758816978083085130507043184471273380659243275938904335757337482424
G = (Gx,Gy)

def inv(a,n):
  lm, hm = 1,0
  low, high = a%n,n
  while low > 1:
    r = high/low
    nm, new = hm-lm*r, high-low*r
    lm, low, hm, high = nm, new, lm, low
  return lm % n

def get_code_string(base):
   if base == 2: return '01'
   elif base == 10: return '0123456789'
   elif base == 16: return "0123456789abcdef"
   elif base == 58: return "123456789ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz"
   elif base == 256: return ''.join([chr(x) for x in range(256)])
   else: raise ValueError("Invalid base!")

def encode(val,base,minlen=0):
   code_string = get_code_string(base)
   result = ""   
   while val > 0:
      result = code_string[val % base] + result
      val /= base
   if len(result) < minlen:
      result = code_string[0]*(minlen-len(result))+result
   return result

def decode(string,base):
   code_string = get_code_string(base)
   result = 0
   if base == 16: string = string.lower()
   while len(string) > 0:
      result *= base
      result += code_string.find(string[0])
      string = string[1:]
   return result

def changebase(string,frm,to,minlen=0):
   return encode(decode(string,frm),to,minlen)

def base10_add(a,b):
  if a == None: return b[0],b[1]
  if b == None: return a[0],a[1]
  if a[0] == b[0]: 
    if a[1] == b[1]: return base10_double(a[0],a[1])
    else: return None
  m = ((b[1]-a[1]) * inv(b[0]-a[0],P)) % P
  x = (m*m-a[0]-b[0]) % P
  y = (m*(a[0]-x)-a[1]) % P
  return (x,y)
  
def base10_double(a):
  if a == None: return None
  m = ((3*a[0]*a[0]+A)*inv(2*a[1],P)) % P
  x = (m*m-2*a[0]) % P
  y = (m*(a[0]-x)-a[1]) % P
  return (x,y)

def base10_multiply(a,n):
  if n == 0: return G
  if n == 1: return a
  if (n%2) == 0: return base10_double(base10_multiply(a,n/2))
  if (n%2) == 1: return base10_add(base10_double(base10_multiply(a,n/2)),a)

def hex_to_point(h): return (decode(h[2:66],16),decode(h[66:],16))

def point_to_hex(p): return '04'+encode(p[0],16,64)+encode(p[1],16,64)

def multiply(privkey,pubkey):
  return point_to_hex(base10_multiply(hex_to_point(pubkey),decode(privkey,16)))

def privtopub(privkey):
  return point_to_hex(base10_multiply(G,decode(privkey,16)))

def add(p1,p2):
  if (len(p1)==32):
    return encode(decode(p1,16) + decode(p2,16) % P,16,32)
  else:
    return point_to_hex(base10_add(hex_to_point(p1),hex_to_point(p2)))

def hash_160(string):
   intermed = hashlib.sha256(string).digest()
   ripemd160 = hashlib.new('ripemd160')
   ripemd160.update(intermed)
   return ripemd160.digest()

def dbl_sha256(string):
   return hashlib.sha256(hashlib.sha256(string).digest()).digest()
  
def bin_to_b58check(inp):
   inp_fmtd = '\x00' + inp
   leadingzbytes = len(re.match('^\x00*',inp_fmtd).group(0))
   checksum = dbl_sha256(inp_fmtd)[:4]
   return '1' * leadingzbytes + changebase(inp_fmtd+checksum,256,58)

#Convert a public key (in hex) to a Bitcoin address
def pubkey_to_address(pubkey):
   return bin_to_b58check(hash_160(changebase(pubkey,16,256)))

########NEW FILE########
__FILENAME__ = cipher
#!/usr/bin/env python
# -*- coding: utf-8 -*-

#  Copyright (C) 2011 Yann GUIBET <yannguibet@gmail.com>
#  See LICENSE for details.

from pyelliptic.openssl import OpenSSL


class Cipher:
    """
    Symmetric encryption

        import pyelliptic
        iv = pyelliptic.Cipher.gen_IV('aes-256-cfb')
        ctx = pyelliptic.Cipher("secretkey", iv, 1, ciphername='aes-256-cfb')
        ciphertext = ctx.update('test1')
        ciphertext += ctx.update('test2')
        ciphertext += ctx.final()

        ctx2 = pyelliptic.Cipher("secretkey", iv, 0, ciphername='aes-256-cfb')
        print ctx2.ciphering(ciphertext)
    """
    def __init__(self, key, iv, do, ciphername='aes-256-cbc'):
        """
        do == 1 => Encrypt; do == 0 => Decrypt
        """
        self.cipher = OpenSSL.get_cipher(ciphername)
        self.ctx = OpenSSL.EVP_CIPHER_CTX_new()
        if do == 1 or do == 0:
            k = OpenSSL.malloc(key, len(key))
            IV = OpenSSL.malloc(iv, len(iv))
            OpenSSL.EVP_CipherInit_ex(
                self.ctx, self.cipher.get_pointer(), 0, k, IV, do)
        else:
            raise Exception("RTFM ...")

    @staticmethod
    def get_all_cipher():
        """
        static method, returns all ciphers available
        """
        return OpenSSL.cipher_algo.keys()

    @staticmethod
    def get_blocksize(ciphername):
        cipher = OpenSSL.get_cipher(ciphername)
        return cipher.get_blocksize()

    @staticmethod
    def gen_IV(ciphername):
        cipher = OpenSSL.get_cipher(ciphername)
        return OpenSSL.rand(cipher.get_blocksize())

    def update(self, input):
        i = OpenSSL.c_int(0)
        buffer = OpenSSL.malloc(b"", len(input) + self.cipher.get_blocksize())
        inp = OpenSSL.malloc(input, len(input))
        if OpenSSL.EVP_CipherUpdate(self.ctx, OpenSSL.byref(buffer),
                                    OpenSSL.byref(i), inp, len(input)) == 0:
            raise Exception("[OpenSSL] EVP_CipherUpdate FAIL ...")
        return buffer.raw[0:i.value]

    def final(self):
        i = OpenSSL.c_int(0)
        buffer = OpenSSL.malloc(b"", self.cipher.get_blocksize())
        if (OpenSSL.EVP_CipherFinal_ex(self.ctx, OpenSSL.byref(buffer),
                                       OpenSSL.byref(i))) == 0:
            raise Exception("[OpenSSL] EVP_CipherFinal_ex FAIL ...")
        return buffer.raw[0:i.value]

    def ciphering(self, input):
        """
        Do update and final in one method
        """
        buff = self.update(input)
        return buff + self.final()

    def __del__(self):
        OpenSSL.EVP_CIPHER_CTX_cleanup(self.ctx)
        OpenSSL.EVP_CIPHER_CTX_free(self.ctx)

########NEW FILE########
__FILENAME__ = ecc
#!/usr/bin/env python
# -*- coding: utf-8 -*-

#  Copyright (C) 2011 Yann GUIBET <yannguibet@gmail.com>
#  See LICENSE for details.

from hashlib import sha512
from pyelliptic.openssl import OpenSSL
from pyelliptic.cipher import Cipher
from pyelliptic.hash import hmac_sha256
from struct import pack, unpack


class ECC:
    """
    Asymmetric encryption with Elliptic Curve Cryptography (ECC)
    ECDH, ECDSA and ECIES

        import pyelliptic

        alice = pyelliptic.ECC() # default curve: sect283r1
        bob = pyelliptic.ECC(curve='sect571r1')

        ciphertext = alice.encrypt("Hello Bob", bob.get_pubkey())
        print bob.decrypt(ciphertext)

        signature = bob.sign("Hello Alice")
        # alice's job :
        print pyelliptic.ECC(
            pubkey=bob.get_pubkey()).verify(signature, "Hello Alice")

        # ERROR !!!
        try:
            key = alice.get_ecdh_key(bob.get_pubkey())
        except: print("For ECDH key agreement,\
                      the keys must be defined on the same curve !")

        alice = pyelliptic.ECC(curve='sect571r1')
        print alice.get_ecdh_key(bob.get_pubkey()).encode('hex')
        print bob.get_ecdh_key(alice.get_pubkey()).encode('hex')

    """
    def __init__(self, pubkey=None, privkey=None, pubkey_x=None,
                 pubkey_y=None, raw_privkey=None, curve='sect283r1'):
        """
        For a normal and High level use, specifie pubkey,
        privkey (if you need) and the curve
        """
        if type(curve) == str:
            self.curve = OpenSSL.get_curve(curve)
        else:
            self.curve = curve

        if pubkey_x is not None and pubkey_y is not None:
            self._set_keys(pubkey_x, pubkey_y, raw_privkey)
        elif pubkey is not None:
            curve, pubkey_x, pubkey_y, i = ECC._decode_pubkey(pubkey)
            if privkey is not None:
                curve2, raw_privkey, i = ECC._decode_privkey(privkey)
                if curve != curve2:
                    raise Exception("Bad ECC keys ...")
            self.curve = curve
            self._set_keys(pubkey_x, pubkey_y, raw_privkey)
        else:
            self.privkey, self.pubkey_x, self.pubkey_y = self._generate()

    def _set_keys(self, pubkey_x, pubkey_y, privkey):
        if self.raw_check_key(privkey, pubkey_x, pubkey_y) < 0:
            self.pubkey_x = None
            self.pubkey_y = None
            self.privkey = None
            raise Exception("Bad ECC keys ...")
        else:
            self.pubkey_x = pubkey_x
            self.pubkey_y = pubkey_y
            self.privkey = privkey

    @staticmethod
    def get_curves():
        """
        static method, returns the list of all the curves available
        """
        return OpenSSL.curves.keys()

    def get_curve(self):
        return OpenSSL.get_curve_by_id(self.curve)

    def get_curve_id(self):
        return self.curve

    def get_pubkey(self):
        """
        High level function which returns :
        curve(2) + len_of_pubkeyX(2) + pubkeyX + len_of_pubkeyY + pubkeyY
        """
        return b''.join((pack('!H', self.curve),
                         pack('!H', len(self.pubkey_x)),
                         self.pubkey_x,
                         pack('!H', len(self.pubkey_y)),
                         self.pubkey_y
                         ))

    def get_privkey(self):
        """
        High level function which returns
        curve(2) + len_of_privkey(2) + privkey
        """
        return b''.join((pack('!H', self.curve),
                         pack('!H', len(self.privkey)),
                         self.privkey
                         ))

    @staticmethod
    def _decode_pubkey(pubkey):
        i = 0
        curve = unpack('!H', pubkey[i:i + 2])[0]
        i += 2
        tmplen = unpack('!H', pubkey[i:i + 2])[0]
        i += 2
        pubkey_x = pubkey[i:i + tmplen]
        i += tmplen
        tmplen = unpack('!H', pubkey[i:i + 2])[0]
        i += 2
        pubkey_y = pubkey[i:i + tmplen]
        i += tmplen
        return curve, pubkey_x, pubkey_y, i

    @staticmethod
    def _decode_privkey(privkey):
        i = 0
        curve = unpack('!H', privkey[i:i + 2])[0]
        i += 2
        tmplen = unpack('!H', privkey[i:i + 2])[0]
        i += 2
        privkey = privkey[i:i + tmplen]
        i += tmplen
        return curve, privkey, i

    def _generate(self):
        try:
            pub_key_x = OpenSSL.BN_new()
            pub_key_y = OpenSSL.BN_new()

            key = OpenSSL.EC_KEY_new_by_curve_name(self.curve)
            if key == 0:
                raise Exception("[OpenSSL] EC_KEY_new_by_curve_name FAIL ...")
            if (OpenSSL.EC_KEY_generate_key(key)) == 0:
                raise Exception("[OpenSSL] EC_KEY_generate_key FAIL ...")
            if (OpenSSL.EC_KEY_check_key(key)) == 0:
                raise Exception("[OpenSSL] EC_KEY_check_key FAIL ...")
            priv_key = OpenSSL.EC_KEY_get0_private_key(key)

            group = OpenSSL.EC_KEY_get0_group(key)
            pub_key = OpenSSL.EC_KEY_get0_public_key(key)

            if (OpenSSL.EC_POINT_get_affine_coordinates_GFp(group, pub_key,
                                                            pub_key_x,
                                                            pub_key_y, 0
                                                            )) == 0:
                raise Exception(
                    "[OpenSSL] EC_POINT_get_affine_coordinates_GFp FAIL ...")

            privkey = OpenSSL.malloc(0, OpenSSL.BN_num_bytes(priv_key))
            pubkeyx = OpenSSL.malloc(0, OpenSSL.BN_num_bytes(pub_key_x))
            pubkeyy = OpenSSL.malloc(0, OpenSSL.BN_num_bytes(pub_key_y))
            OpenSSL.BN_bn2bin(priv_key, privkey)
            privkey = privkey.raw
            OpenSSL.BN_bn2bin(pub_key_x, pubkeyx)
            pubkeyx = pubkeyx.raw
            OpenSSL.BN_bn2bin(pub_key_y, pubkeyy)
            pubkeyy = pubkeyy.raw
            self.raw_check_key(privkey, pubkeyx, pubkeyy)

            return privkey, pubkeyx, pubkeyy

        finally:
            OpenSSL.EC_KEY_free(key)
            OpenSSL.BN_free(pub_key_x)
            OpenSSL.BN_free(pub_key_y)

    def get_ecdh_key(self, pubkey):
        """
        High level function. Compute public key with the local private key
        and returns a 512bits shared key
        """
        curve, pubkey_x, pubkey_y, i = ECC._decode_pubkey(pubkey)
        if curve != self.curve:
            raise Exception("ECC keys must be from the same curve !")
        return sha512(self.raw_get_ecdh_key(pubkey_x, pubkey_y)).digest()

    def raw_get_ecdh_key(self, pubkey_x, pubkey_y):
        try:
            ecdh_keybuffer = OpenSSL.malloc(0, 32)

            other_key = OpenSSL.EC_KEY_new_by_curve_name(self.curve)
            if other_key == 0:
                raise Exception("[OpenSSL] EC_KEY_new_by_curve_name FAIL ...")

            other_pub_key_x = OpenSSL.BN_bin2bn(pubkey_x, len(pubkey_x), 0)
            other_pub_key_y = OpenSSL.BN_bin2bn(pubkey_y, len(pubkey_y), 0)

            other_group = OpenSSL.EC_KEY_get0_group(other_key)
            other_pub_key = OpenSSL.EC_POINT_new(other_group)

            if (OpenSSL.EC_POINT_set_affine_coordinates_GFp(other_group,
                                                            other_pub_key,
                                                            other_pub_key_x,
                                                            other_pub_key_y,
                                                            0)) == 0:
                raise Exception(
                    "[OpenSSL] EC_POINT_set_affine_coordinates_GFp FAIL ...")
            if (OpenSSL.EC_KEY_set_public_key(other_key, other_pub_key)) == 0:
                raise Exception("[OpenSSL] EC_KEY_set_public_key FAIL ...")
            if (OpenSSL.EC_KEY_check_key(other_key)) == 0:
                raise Exception("[OpenSSL] EC_KEY_check_key FAIL ...")

            own_key = OpenSSL.EC_KEY_new_by_curve_name(self.curve)
            if own_key == 0:
                raise Exception("[OpenSSL] EC_KEY_new_by_curve_name FAIL ...")
            own_priv_key = OpenSSL.BN_bin2bn(
                self.privkey, len(self.privkey), 0)

            if (OpenSSL.EC_KEY_set_private_key(own_key, own_priv_key)) == 0:
                raise Exception("[OpenSSL] EC_KEY_set_private_key FAIL ...")

            OpenSSL.ECDH_set_method(own_key, OpenSSL.ECDH_OpenSSL())
            ecdh_keylen = OpenSSL.ECDH_compute_key(
                ecdh_keybuffer, 32, other_pub_key, own_key, 0)

            if ecdh_keylen != 32:
                raise Exception("[OpenSSL] ECDH keylen FAIL ...")

            return ecdh_keybuffer.raw

        finally:
            OpenSSL.EC_KEY_free(other_key)
            OpenSSL.BN_free(other_pub_key_x)
            OpenSSL.BN_free(other_pub_key_y)
            OpenSSL.EC_POINT_free(other_pub_key)
            OpenSSL.EC_KEY_free(own_key)
            OpenSSL.BN_free(own_priv_key)

    def check_key(self, privkey, pubkey):
        """
        Check the public key and the private key.
        The private key is optional (replace by None)
        """
        curve, pubkey_x, pubkey_y, i = ECC._decode_pubkey(pubkey)
        if privkey is None:
            raw_privkey = None
            curve2 = curve
        else:
            curve2, raw_privkey, i = ECC._decode_privkey(privkey)
        if curve != curve2:
            raise Exception("Bad public and private key")
        return self.raw_check_key(raw_privkey, pubkey_x, pubkey_y, curve)

    def raw_check_key(self, privkey, pubkey_x, pubkey_y, curve=None):
        if curve is None:
            curve = self.curve
        elif type(curve) == str:
            curve = OpenSSL.get_curve(curve)
        else:
            curve = curve
        try:
            key = OpenSSL.EC_KEY_new_by_curve_name(curve)
            if key == 0:
                raise Exception("[OpenSSL] EC_KEY_new_by_curve_name FAIL ...")
            if privkey is not None:
                priv_key = OpenSSL.BN_bin2bn(privkey, len(privkey), 0)
            pub_key_x = OpenSSL.BN_bin2bn(pubkey_x, len(pubkey_x), 0)
            pub_key_y = OpenSSL.BN_bin2bn(pubkey_y, len(pubkey_y), 0)

            if privkey is not None:
                if (OpenSSL.EC_KEY_set_private_key(key, priv_key)) == 0:
                    raise Exception(
                        "[OpenSSL] EC_KEY_set_private_key FAIL ...")

            group = OpenSSL.EC_KEY_get0_group(key)
            pub_key = OpenSSL.EC_POINT_new(group)

            if (OpenSSL.EC_POINT_set_affine_coordinates_GFp(group, pub_key,
                                                            pub_key_x,
                                                            pub_key_y,
                                                            0)) == 0:
                raise Exception(
                    "[OpenSSL] EC_POINT_set_affine_coordinates_GFp FAIL ...")
            if (OpenSSL.EC_KEY_set_public_key(key, pub_key)) == 0:
                raise Exception("[OpenSSL] EC_KEY_set_public_key FAIL ...")
            if (OpenSSL.EC_KEY_check_key(key)) == 0:
                raise Exception("[OpenSSL] EC_KEY_check_key FAIL ...")
            return 0

        finally:
            OpenSSL.EC_KEY_free(key)
            OpenSSL.BN_free(pub_key_x)
            OpenSSL.BN_free(pub_key_y)
            OpenSSL.EC_POINT_free(pub_key)
            if privkey is not None:
                OpenSSL.BN_free(priv_key)

    def sign(self, inputb):
        """
        Sign the input with ECDSA method and returns the signature
        """
        try:
            size = len(inputb)
            buff = OpenSSL.malloc(inputb, size)
            digest = OpenSSL.malloc(0, 64)
            md_ctx = OpenSSL.EVP_MD_CTX_create()
            dgst_len = OpenSSL.pointer(OpenSSL.c_int(0))
            siglen = OpenSSL.pointer(OpenSSL.c_int(0))
            sig = OpenSSL.malloc(0, 151)

            key = OpenSSL.EC_KEY_new_by_curve_name(self.curve)
            if key == 0:
                raise Exception("[OpenSSL] EC_KEY_new_by_curve_name FAIL ...")

            priv_key = OpenSSL.BN_bin2bn(self.privkey, len(self.privkey), 0)
            pub_key_x = OpenSSL.BN_bin2bn(self.pubkey_x, len(self.pubkey_x), 0)
            pub_key_y = OpenSSL.BN_bin2bn(self.pubkey_y, len(self.pubkey_y), 0)

            if (OpenSSL.EC_KEY_set_private_key(key, priv_key)) == 0:
                raise Exception("[OpenSSL] EC_KEY_set_private_key FAIL ...")

            group = OpenSSL.EC_KEY_get0_group(key)
            pub_key = OpenSSL.EC_POINT_new(group)

            if (OpenSSL.EC_POINT_set_affine_coordinates_GFp(group, pub_key,
                                                            pub_key_x,
                                                            pub_key_y,
                                                            0)) == 0:
                raise Exception(
                    "[OpenSSL] EC_POINT_set_affine_coordinates_GFp FAIL ...")
            if (OpenSSL.EC_KEY_set_public_key(key, pub_key)) == 0:
                raise Exception("[OpenSSL] EC_KEY_set_public_key FAIL ...")
            if (OpenSSL.EC_KEY_check_key(key)) == 0:
                raise Exception("[OpenSSL] EC_KEY_check_key FAIL ...")

            OpenSSL.EVP_MD_CTX_init(md_ctx)
            OpenSSL.EVP_DigestInit(md_ctx, OpenSSL.EVP_ecdsa())

            if (OpenSSL.EVP_DigestUpdate(md_ctx, buff, size)) == 0:
                raise Exception("[OpenSSL] EVP_DigestUpdate FAIL ...")
            OpenSSL.EVP_DigestFinal(md_ctx, digest, dgst_len)
            OpenSSL.ECDSA_sign(0, digest, dgst_len.contents, sig, siglen, key)
            if (OpenSSL.ECDSA_verify(0, digest, dgst_len.contents, sig,
                                     siglen.contents, key)) != 1:
                raise Exception("[OpenSSL] ECDSA_verify FAIL ...")

            return sig.raw[:siglen.contents.value]

        finally:
            OpenSSL.EC_KEY_free(key)
            OpenSSL.BN_free(pub_key_x)
            OpenSSL.BN_free(pub_key_y)
            OpenSSL.BN_free(priv_key)
            OpenSSL.EC_POINT_free(pub_key)
            OpenSSL.EVP_MD_CTX_destroy(md_ctx)

    def verify(self, sig, inputb):
        """
        Verify the signature with the input and the local public key.
        Returns a boolean
        """
        try:
            bsig = OpenSSL.malloc(sig, len(sig))
            binputb = OpenSSL.malloc(inputb, len(inputb))
            digest = OpenSSL.malloc(0, 64)
            dgst_len = OpenSSL.pointer(OpenSSL.c_int(0))
            md_ctx = OpenSSL.EVP_MD_CTX_create()

            key = OpenSSL.EC_KEY_new_by_curve_name(self.curve)

            if key == 0:
                raise Exception("[OpenSSL] EC_KEY_new_by_curve_name FAIL ...")

            pub_key_x = OpenSSL.BN_bin2bn(self.pubkey_x, len(self.pubkey_x), 0)
            pub_key_y = OpenSSL.BN_bin2bn(self.pubkey_y, len(self.pubkey_y), 0)
            group = OpenSSL.EC_KEY_get0_group(key)
            pub_key = OpenSSL.EC_POINT_new(group)

            if (OpenSSL.EC_POINT_set_affine_coordinates_GFp(group, pub_key,
                                                            pub_key_x,
                                                            pub_key_y,
                                                            0)) == 0:
                raise Exception(
                    "[OpenSSL] EC_POINT_set_affine_coordinates_GFp FAIL ...")
            if (OpenSSL.EC_KEY_set_public_key(key, pub_key)) == 0:
                raise Exception("[OpenSSL] EC_KEY_set_public_key FAIL ...")
            if (OpenSSL.EC_KEY_check_key(key)) == 0:
                raise Exception("[OpenSSL] EC_KEY_check_key FAIL ...")

            OpenSSL.EVP_MD_CTX_init(md_ctx)
            OpenSSL.EVP_DigestInit(md_ctx, OpenSSL.EVP_ecdsa())
            if (OpenSSL.EVP_DigestUpdate(md_ctx, binputb, len(inputb))) == 0:
                raise Exception("[OpenSSL] EVP_DigestUpdate FAIL ...")

            OpenSSL.EVP_DigestFinal(md_ctx, digest, dgst_len)
            ret = OpenSSL.ECDSA_verify(
                0, digest, dgst_len.contents, bsig, len(sig), key)

            if ret == -1:
                return False  # Fail to Check
            else:
                if ret == 0:
                    return False  # Bad signature !
                else:
                    return True  # Good
            return False

        finally:
            OpenSSL.EC_KEY_free(key)
            OpenSSL.BN_free(pub_key_x)
            OpenSSL.BN_free(pub_key_y)
            OpenSSL.EC_POINT_free(pub_key)
            OpenSSL.EVP_MD_CTX_destroy(md_ctx)

    @staticmethod
    def encrypt(data, pubkey, ephemcurve=None, ciphername='aes-256-cbc'):
        """
        Encrypt data with ECIES method using the public key of the recipient.
        """
        curve, pubkey_x, pubkey_y, i = ECC._decode_pubkey(pubkey)
        return ECC.raw_encrypt(data, pubkey_x, pubkey_y, curve=curve,
                               ephemcurve=ephemcurve, ciphername=ciphername)

    @staticmethod
    def raw_encrypt(data, pubkey_x, pubkey_y, curve='sect283r1',
                    ephemcurve=None, ciphername='aes-256-cbc'):
        if ephemcurve is None:
            ephemcurve = curve
        ephem = ECC(curve=ephemcurve)
        key = sha512(ephem.raw_get_ecdh_key(pubkey_x, pubkey_y)).digest()
        key_e, key_m = key[:32], key[32:]
        pubkey = ephem.get_pubkey()
        iv = OpenSSL.rand(OpenSSL.get_cipher(ciphername).get_blocksize())
        ctx = Cipher(key_e, iv, 1, ciphername)
        ciphertext = ctx.ciphering(data)
        mac = hmac_sha256(key_m, ciphertext)
        return iv + pubkey + ciphertext + mac

    def decrypt(self, data, ciphername='aes-256-cbc'):
        """
        Decrypt data with ECIES method using the local private key
        """
        blocksize = OpenSSL.get_cipher(ciphername).get_blocksize()
        iv = data[:blocksize]
        i = blocksize
        curve, pubkey_x, pubkey_y, i2 = ECC._decode_pubkey(data[i:])
        i += i2
        ciphertext = data[i:len(data)-32]
        i += len(ciphertext)
        mac = data[i:]
        key = sha512(self.raw_get_ecdh_key(pubkey_x, pubkey_y)).digest()
        key_e, key_m = key[:32], key[32:]
        if hmac_sha256(key_m, ciphertext) != mac:
            raise RuntimeError("Fail to verify data")
        ctx = Cipher(key_e, iv, 0, ciphername)
        return ctx.ciphering(ciphertext)

########NEW FILE########
__FILENAME__ = hash
#!/usr/bin/env python
# -*- coding: utf-8 -*-

#  Copyright (C) 2011 Yann GUIBET <yannguibet@gmail.com>
#  See LICENSE for details.

from pyelliptic.openssl import OpenSSL


def hmac_sha256(k, m):
    """
    Compute the key and the message with HMAC SHA5256
    """
    key = OpenSSL.malloc(k, len(k))
    d = OpenSSL.malloc(m, len(m))
    md = OpenSSL.malloc(0, 32)
    i = OpenSSL.pointer(OpenSSL.c_int(0))
    OpenSSL.HMAC(OpenSSL.EVP_sha256(), key, len(k), d, len(m), md, i)
    return md.raw


def hmac_sha512(k, m):
    """
    Compute the key and the message with HMAC SHA512
    """
    key = OpenSSL.malloc(k, len(k))
    d = OpenSSL.malloc(m, len(m))
    md = OpenSSL.malloc(0, 64)
    i = OpenSSL.pointer(OpenSSL.c_int(0))
    OpenSSL.HMAC(OpenSSL.EVP_sha512(), key, len(k), d, len(m), md, i)
    return md.raw


def pbkdf2(password, salt=None, i=10000, keylen=64):
    if salt is None:
        salt = OpenSSL.rand(8)
    p_password = OpenSSL.malloc(password, len(password))
    p_salt = OpenSSL.malloc(salt, len(salt))
    output = OpenSSL.malloc(0, keylen)
    OpenSSL.PKCS5_PBKDF2_HMAC(p_password, len(password), p_salt,
                              len(p_salt), i, OpenSSL.EVP_sha256(),
                              keylen, output)
    return salt, output.raw

########NEW FILE########
__FILENAME__ = openssl
#!/usr/bin/env python
# -*- coding: utf-8 -*-

#  Copyright (C) 2011 Yann GUIBET <yannguibet@gmail.com>
#  See LICENSE for details.
#
#  Software slightly changed by Jonathan Warren <bitmessage at-symbol jonwarren.org>

import sys
import ctypes

OpenSSL = None


class CipherName:
    def __init__(self, name, pointer, blocksize):
        self._name = name
        self._pointer = pointer
        self._blocksize = blocksize

    def __str__(self):
        return "Cipher : " + self._name + " | Blocksize : " + str(self._blocksize) + " | Fonction pointer : " + str(self._pointer)

    def get_pointer(self):
        return self._pointer()

    def get_name(self):
        return self._name

    def get_blocksize(self):
        return self._blocksize


class _OpenSSL:
    """
    Wrapper for OpenSSL using ctypes
    """
    def __init__(self, library):
        """
        Build the wrapper
        """
        self._lib = ctypes.CDLL(library)

        self.pointer = ctypes.pointer
        self.c_int = ctypes.c_int
        self.byref = ctypes.byref
        self.create_string_buffer = ctypes.create_string_buffer

        self.BN_new = self._lib.BN_new
        self.BN_new.restype = ctypes.c_void_p
        self.BN_new.argtypes = []

        self.BN_free = self._lib.BN_free
        self.BN_free.restype = None
        self.BN_free.argtypes = [ctypes.c_void_p]

        self.BN_num_bits = self._lib.BN_num_bits
        self.BN_num_bits.restype = ctypes.c_int
        self.BN_num_bits.argtypes = [ctypes.c_void_p]

        self.BN_bn2bin = self._lib.BN_bn2bin
        self.BN_bn2bin.restype = ctypes.c_int
        self.BN_bn2bin.argtypes = [ctypes.c_void_p, ctypes.c_void_p]

        self.BN_bin2bn = self._lib.BN_bin2bn
        self.BN_bin2bn.restype = ctypes.c_void_p
        self.BN_bin2bn.argtypes = [ctypes.c_void_p, ctypes.c_int,
                                   ctypes.c_void_p]

        self.EC_KEY_free = self._lib.EC_KEY_free
        self.EC_KEY_free.restype = None
        self.EC_KEY_free.argtypes = [ctypes.c_void_p]

        self.EC_KEY_new_by_curve_name = self._lib.EC_KEY_new_by_curve_name
        self.EC_KEY_new_by_curve_name.restype = ctypes.c_void_p
        self.EC_KEY_new_by_curve_name.argtypes = [ctypes.c_int]

        self.EC_KEY_generate_key = self._lib.EC_KEY_generate_key
        self.EC_KEY_generate_key.restype = ctypes.c_int
        self.EC_KEY_generate_key.argtypes = [ctypes.c_void_p]

        self.EC_KEY_check_key = self._lib.EC_KEY_check_key
        self.EC_KEY_check_key.restype = ctypes.c_int
        self.EC_KEY_check_key.argtypes = [ctypes.c_void_p]

        self.EC_KEY_get0_private_key = self._lib.EC_KEY_get0_private_key
        self.EC_KEY_get0_private_key.restype = ctypes.c_void_p
        self.EC_KEY_get0_private_key.argtypes = [ctypes.c_void_p]

        self.EC_KEY_get0_public_key = self._lib.EC_KEY_get0_public_key
        self.EC_KEY_get0_public_key.restype = ctypes.c_void_p
        self.EC_KEY_get0_public_key.argtypes = [ctypes.c_void_p]

        self.EC_KEY_get0_group = self._lib.EC_KEY_get0_group
        self.EC_KEY_get0_group.restype = ctypes.c_void_p
        self.EC_KEY_get0_group.argtypes = [ctypes.c_void_p]

        self.EC_POINT_get_affine_coordinates_GFp = self._lib.EC_POINT_get_affine_coordinates_GFp
        self.EC_POINT_get_affine_coordinates_GFp.restype = ctypes.c_int
        self.EC_POINT_get_affine_coordinates_GFp.argtypes = [ctypes.c_void_p, ctypes.c_void_p, ctypes.c_void_p, ctypes.c_void_p, ctypes.c_void_p]

        self.EC_KEY_set_private_key = self._lib.EC_KEY_set_private_key
        self.EC_KEY_set_private_key.restype = ctypes.c_int
        self.EC_KEY_set_private_key.argtypes = [ctypes.c_void_p,
                                                ctypes.c_void_p]

        self.EC_KEY_set_public_key = self._lib.EC_KEY_set_public_key
        self.EC_KEY_set_public_key.restype = ctypes.c_int
        self.EC_KEY_set_public_key.argtypes = [ctypes.c_void_p,
                                               ctypes.c_void_p]

        self.EC_KEY_set_group = self._lib.EC_KEY_set_group
        self.EC_KEY_set_group.restype = ctypes.c_int
        self.EC_KEY_set_group.argtypes = [ctypes.c_void_p, ctypes.c_void_p]

        self.EC_POINT_set_affine_coordinates_GFp = self._lib.EC_POINT_set_affine_coordinates_GFp
        self.EC_POINT_set_affine_coordinates_GFp.restype = ctypes.c_int
        self.EC_POINT_set_affine_coordinates_GFp.argtypes = [ctypes.c_void_p, ctypes.c_void_p, ctypes.c_void_p, ctypes.c_void_p, ctypes.c_void_p]

        self.EC_POINT_new = self._lib.EC_POINT_new
        self.EC_POINT_new.restype = ctypes.c_void_p
        self.EC_POINT_new.argtypes = [ctypes.c_void_p]

        self.EC_POINT_free = self._lib.EC_POINT_free
        self.EC_POINT_free.restype = None
        self.EC_POINT_free.argtypes = [ctypes.c_void_p]

        self.BN_CTX_free = self._lib.BN_CTX_free
        self.BN_CTX_free.restype = None
        self.BN_CTX_free.argtypes = [ctypes.c_void_p]

        self.EC_POINT_mul = self._lib.EC_POINT_mul
        self.EC_POINT_mul.restype = None
        self.EC_POINT_mul.argtypes = [ctypes.c_void_p, ctypes.c_void_p, ctypes.c_void_p, ctypes.c_void_p, ctypes.c_void_p]

        self.EC_KEY_set_private_key = self._lib.EC_KEY_set_private_key
        self.EC_KEY_set_private_key.restype = ctypes.c_int
        self.EC_KEY_set_private_key.argtypes = [ctypes.c_void_p,
                                                ctypes.c_void_p]

        self.ECDH_OpenSSL = self._lib.ECDH_OpenSSL
        self._lib.ECDH_OpenSSL.restype = ctypes.c_void_p
        self._lib.ECDH_OpenSSL.argtypes = []

        self.BN_CTX_new = self._lib.BN_CTX_new
        self._lib.BN_CTX_new.restype = ctypes.c_void_p
        self._lib.BN_CTX_new.argtypes = []

        self.ECDH_set_method = self._lib.ECDH_set_method
        self._lib.ECDH_set_method.restype = ctypes.c_int
        self._lib.ECDH_set_method.argtypes = [ctypes.c_void_p, ctypes.c_void_p]

        self.ECDH_compute_key = self._lib.ECDH_compute_key
        self.ECDH_compute_key.restype = ctypes.c_int
        self.ECDH_compute_key.argtypes = [ctypes.c_void_p,
                                          ctypes.c_int, ctypes.c_void_p, ctypes.c_void_p]

        self.EVP_CipherInit_ex = self._lib.EVP_CipherInit_ex
        self.EVP_CipherInit_ex.restype = ctypes.c_int
        self.EVP_CipherInit_ex.argtypes = [ctypes.c_void_p,
                                           ctypes.c_void_p, ctypes.c_void_p]

        self.EVP_CIPHER_CTX_new = self._lib.EVP_CIPHER_CTX_new
        self.EVP_CIPHER_CTX_new.restype = ctypes.c_void_p
        self.EVP_CIPHER_CTX_new.argtypes = []

        # Cipher
        self.EVP_aes_128_cfb128 = self._lib.EVP_aes_128_cfb128
        self.EVP_aes_128_cfb128.restype = ctypes.c_void_p
        self.EVP_aes_128_cfb128.argtypes = []

        self.EVP_aes_256_cfb128 = self._lib.EVP_aes_256_cfb128
        self.EVP_aes_256_cfb128.restype = ctypes.c_void_p
        self.EVP_aes_256_cfb128.argtypes = []

        self.EVP_aes_128_cbc = self._lib.EVP_aes_128_cbc
        self.EVP_aes_128_cbc.restype = ctypes.c_void_p
        self.EVP_aes_128_cbc.argtypes = []

        self.EVP_aes_256_cbc = self._lib.EVP_aes_256_cbc
        self.EVP_aes_256_cbc.restype = ctypes.c_void_p
        self.EVP_aes_256_cbc.argtypes = []

        #self.EVP_aes_128_ctr = self._lib.EVP_aes_128_ctr
        #self.EVP_aes_128_ctr.restype = ctypes.c_void_p
        #self.EVP_aes_128_ctr.argtypes = []

        #self.EVP_aes_256_ctr = self._lib.EVP_aes_256_ctr
        #self.EVP_aes_256_ctr.restype = ctypes.c_void_p
        #self.EVP_aes_256_ctr.argtypes = []

        self.EVP_aes_128_ofb = self._lib.EVP_aes_128_ofb
        self.EVP_aes_128_ofb.restype = ctypes.c_void_p
        self.EVP_aes_128_ofb.argtypes = []

        self.EVP_aes_256_ofb = self._lib.EVP_aes_256_ofb
        self.EVP_aes_256_ofb.restype = ctypes.c_void_p
        self.EVP_aes_256_ofb.argtypes = []

        self.EVP_bf_cbc = self._lib.EVP_bf_cbc
        self.EVP_bf_cbc.restype = ctypes.c_void_p
        self.EVP_bf_cbc.argtypes = []

        self.EVP_bf_cfb64 = self._lib.EVP_bf_cfb64
        self.EVP_bf_cfb64.restype = ctypes.c_void_p
        self.EVP_bf_cfb64.argtypes = []

        self.EVP_rc4 = self._lib.EVP_rc4
        self.EVP_rc4.restype = ctypes.c_void_p
        self.EVP_rc4.argtypes = []

        self.EVP_CIPHER_CTX_cleanup = self._lib.EVP_CIPHER_CTX_cleanup
        self.EVP_CIPHER_CTX_cleanup.restype = ctypes.c_int
        self.EVP_CIPHER_CTX_cleanup.argtypes = [ctypes.c_void_p]

        self.EVP_CIPHER_CTX_free = self._lib.EVP_CIPHER_CTX_free
        self.EVP_CIPHER_CTX_free.restype = None
        self.EVP_CIPHER_CTX_free.argtypes = [ctypes.c_void_p]

        self.EVP_CipherUpdate = self._lib.EVP_CipherUpdate
        self.EVP_CipherUpdate.restype = ctypes.c_int
        self.EVP_CipherUpdate.argtypes = [ctypes.c_void_p,
                                          ctypes.c_void_p, ctypes.c_void_p, ctypes.c_void_p, ctypes.c_int]

        self.EVP_CipherFinal_ex = self._lib.EVP_CipherFinal_ex
        self.EVP_CipherFinal_ex.restype = ctypes.c_int
        self.EVP_CipherFinal_ex.argtypes = [ctypes.c_void_p,
                                            ctypes.c_void_p, ctypes.c_void_p]

        self.EVP_DigestInit = self._lib.EVP_DigestInit
        self.EVP_DigestInit.restype = ctypes.c_int
        self._lib.EVP_DigestInit.argtypes = [ctypes.c_void_p, ctypes.c_void_p]

        self.EVP_DigestUpdate = self._lib.EVP_DigestUpdate
        self.EVP_DigestUpdate.restype = ctypes.c_int
        self.EVP_DigestUpdate.argtypes = [ctypes.c_void_p,
                                          ctypes.c_void_p, ctypes.c_int]

        self.EVP_DigestFinal = self._lib.EVP_DigestFinal
        self.EVP_DigestFinal.restype = ctypes.c_int
        self.EVP_DigestFinal.argtypes = [ctypes.c_void_p,
                                         ctypes.c_void_p, ctypes.c_void_p]

        self.EVP_ecdsa = self._lib.EVP_ecdsa
        self._lib.EVP_ecdsa.restype = ctypes.c_void_p
        self._lib.EVP_ecdsa.argtypes = []

        self.ECDSA_sign = self._lib.ECDSA_sign
        self.ECDSA_sign.restype = ctypes.c_int
        self.ECDSA_sign.argtypes = [ctypes.c_int, ctypes.c_void_p,
                                    ctypes.c_int, ctypes.c_void_p, ctypes.c_void_p, ctypes.c_void_p]

        self.ECDSA_verify = self._lib.ECDSA_verify
        self.ECDSA_verify.restype = ctypes.c_int
        self.ECDSA_verify.argtypes = [ctypes.c_int, ctypes.c_void_p,
                                      ctypes.c_int, ctypes.c_void_p, ctypes.c_int, ctypes.c_void_p]

        self.EVP_MD_CTX_create = self._lib.EVP_MD_CTX_create
        self.EVP_MD_CTX_create.restype = ctypes.c_void_p
        self.EVP_MD_CTX_create.argtypes = []

        self.EVP_MD_CTX_init = self._lib.EVP_MD_CTX_init
        self.EVP_MD_CTX_init.restype = None
        self.EVP_MD_CTX_init.argtypes = [ctypes.c_void_p]

        self.EVP_MD_CTX_destroy = self._lib.EVP_MD_CTX_destroy
        self.EVP_MD_CTX_destroy.restype = None
        self.EVP_MD_CTX_destroy.argtypes = [ctypes.c_void_p]

        self.RAND_bytes = self._lib.RAND_bytes
        self.RAND_bytes.restype = ctypes.c_int
        self.RAND_bytes.argtypes = [ctypes.c_void_p, ctypes.c_int]


        self.EVP_sha256 = self._lib.EVP_sha256
        self.EVP_sha256.restype = ctypes.c_void_p
        self.EVP_sha256.argtypes = []

        self.i2o_ECPublicKey = self._lib.i2o_ECPublicKey
        self.i2o_ECPublicKey.restype = ctypes.c_void_p
        self.i2o_ECPublicKey.argtypes = [ctypes.c_void_p, ctypes.c_void_p]

        self.EVP_sha512 = self._lib.EVP_sha512
        self.EVP_sha512.restype = ctypes.c_void_p
        self.EVP_sha512.argtypes = []

        self.HMAC = self._lib.HMAC
        self.HMAC.restype = ctypes.c_void_p
        self.HMAC.argtypes = [ctypes.c_void_p, ctypes.c_void_p, ctypes.c_int,
                              ctypes.c_void_p, ctypes.c_int, ctypes.c_void_p, ctypes.c_void_p]

        try:
            self.PKCS5_PBKDF2_HMAC = self._lib.PKCS5_PBKDF2_HMAC
        except:
            # The above is not compatible with all versions of OSX.
            self.PKCS5_PBKDF2_HMAC = self._lib.PKCS5_PBKDF2_HMAC_SHA1
            
        self.PKCS5_PBKDF2_HMAC.restype = ctypes.c_int
        self.PKCS5_PBKDF2_HMAC.argtypes = [ctypes.c_void_p, ctypes.c_int,
                                           ctypes.c_void_p, ctypes.c_int,
                                           ctypes.c_int, ctypes.c_void_p,
                                           ctypes.c_int, ctypes.c_void_p]

        self._set_ciphers()
        self._set_curves()

    def _set_ciphers(self):
        self.cipher_algo = {
            'aes-128-cbc': CipherName('aes-128-cbc', self.EVP_aes_128_cbc, 16),
            'aes-256-cbc': CipherName('aes-256-cbc', self.EVP_aes_256_cbc, 16),
            'aes-128-cfb': CipherName('aes-128-cfb', self.EVP_aes_128_cfb128, 16),
            'aes-256-cfb': CipherName('aes-256-cfb', self.EVP_aes_256_cfb128, 16),
            'aes-128-ofb': CipherName('aes-128-ofb', self._lib.EVP_aes_128_ofb, 16),
            'aes-256-ofb': CipherName('aes-256-ofb', self._lib.EVP_aes_256_ofb, 16),
            #'aes-128-ctr': CipherName('aes-128-ctr', self._lib.EVP_aes_128_ctr, 16),
            #'aes-256-ctr': CipherName('aes-256-ctr', self._lib.EVP_aes_256_ctr, 16),
            'bf-cfb': CipherName('bf-cfb', self.EVP_bf_cfb64, 8),
            'bf-cbc': CipherName('bf-cbc', self.EVP_bf_cbc, 8),
            'rc4': CipherName('rc4', self.EVP_rc4, 128), # 128 is the initialisation size not block size
        }

    def _set_curves(self):
        self.curves = {
            'secp112r1': 704,
            'secp112r2': 705,
            'secp128r1': 706,
            'secp128r2': 707,
            'secp160k1': 708,
            'secp160r1': 709,
            'secp160r2': 710,
            'secp192k1': 711,
            'secp224k1': 712,
            'secp224r1': 713,
            'secp256k1': 714,
            'secp384r1': 715,
            'secp521r1': 716,
            'sect113r1': 717,
            'sect113r2': 718,
            'sect131r1': 719,
            'sect131r2': 720,
            'sect163k1': 721,
            'sect163r1': 722,
            'sect163r2': 723,
            'sect193r1': 724,
            'sect193r2': 725,
            'sect233k1': 726,
            'sect233r1': 727,
            'sect239k1': 728,
            'sect283k1': 729,
            'sect283r1': 730,
            'sect409k1': 731,
            'sect409r1': 732,
            'sect571k1': 733,
            'sect571r1': 734,
        }

    def BN_num_bytes(self, x):
        """
        returns the length of a BN (OpenSSl API)
        """
        return int((self.BN_num_bits(x) + 7) / 8)

    def get_cipher(self, name):
        """
        returns the OpenSSL cipher instance
        """
        if name not in self.cipher_algo:
            raise Exception("Unknown cipher")
        return self.cipher_algo[name]

    def get_curve(self, name):
        """
        returns the id of a elliptic curve
        """
        if name not in self.curves:
            raise Exception("Unknown curve")
        return self.curves[name]

    def get_curve_by_id(self, id):
        """
        returns the name of a elliptic curve with his id
        """
        res = None
        for i in self.curves:
            if self.curves[i] == id:
                res = i
                break
        if res is None:
            raise Exception("Unknown curve")
        return res

    def rand(self, size):
        """
        OpenSSL random function
        """
        buffer = self.malloc(0, size)
        # This pyelliptic library, by default, didn't check the return value of RAND_bytes. It is 
        # evidently possible that it returned an error and not-actually-random data. However, in
        # tests on various operating systems, while generating hundreds of gigabytes of random 
        # strings of various sizes I could not get an error to occur. Also Bitcoin doesn't check
        # the return value of RAND_bytes either. 
        # Fixed in Bitmessage version 0.4.2 (in source code on 2013-10-13)
        while self.RAND_bytes(buffer, size) != 1:
            import time
            time.sleep(1)
        return buffer.raw

    def malloc(self, data, size):
        """
        returns a create_string_buffer (ctypes)
        """
        buffer = None
        if data != 0:
            if sys.version_info.major == 3 and isinstance(data, type('')):
                data = data.encode()
            buffer = self.create_string_buffer(data, size)
        else:
            buffer = self.create_string_buffer(size)
        return buffer

try:
    OpenSSL = _OpenSSL('libcrypto.so')
except:
    try:
        OpenSSL = _OpenSSL('libeay32.dll')
    except:
        try:
            OpenSSL = _OpenSSL('libcrypto.dylib')
        except:
            try:
                # try homebrew installation
                OpenSSL = _OpenSSL('/usr/local/opt/openssl/lib/libcrypto.dylib')
            except:
                try:
                  # Load it from an Bitmessage.app on OSX
                  OpenSSL = _OpenSSL('./../Frameworks/libcrypto.dylib')
                except:
                  try:
                      from os import path
                      lib_path = path.join(sys._MEIPASS, "libeay32.dll")
                      OpenSSL = _OpenSSL(lib_path)
                  except:
                      if 'linux' in sys.platform or 'darwin' in sys.platform or 'freebsd' in sys.platform:
                          try:
                              from ctypes.util import find_library
                              OpenSSL = _OpenSSL(find_library('ssl'))
                          except Exception, err:
                              sys.stderr.write('(On Linux) Couldn\'t find and load the OpenSSL library. You must install it. If you believe that you already have it installed, this exception information might be of use:\n')
                              from ctypes.util import find_library
                              OpenSSL = _OpenSSL(find_library('ssl'))
                      else:
                          raise Exception("Couldn't find and load the OpenSSL library. You must install it.")

########NEW FILE########
__FILENAME__ = qidenticon
#!/usr/bin/env python
# -*- coding:utf-8 -*-

###
# qidenticon.py is Licesensed under FreeBSD License.
# (http://www.freebsd.org/copyright/freebsd-license.html)
#
# Copyright 2013 "Sendiulo". All rights reserved.
#
# Redistribution and use in source and binary forms, with or without modification, are permitted provided that the following conditions are met:
#
#    1. Redistributions of source code must retain the above copyright notice, this list of conditions and the following disclaimer.
#    2. Redistributions in binary form must reproduce the above copyright notice, this list of conditions and the following disclaimer in the documentation and/or other materials provided with the distribution.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDER ``AS IS'' AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT HOLDER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
###

###
# identicon.py is Licesensed under FreeBSD License.
# (http://www.freebsd.org/copyright/freebsd-license.html)
#
# Copyright 1994-2009 Shin Adachi. All rights reserved.
#
# Redistribution and use in source and binary forms, with or without modification, are permitted provided that the following conditions are met:
#
#    1. Redistributions of source code must retain the above copyright notice, this list of conditions and the following disclaimer.
#    2. Redistributions in binary form must reproduce the above copyright notice, this list of conditions and the following disclaimer in the documentation and/or other materials provided with the distribution.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDER ``AS IS'' AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT HOLDER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
###

"""
qidenticon.py
identicon python implementation with QPixmap output
by sendiulo <sendiulo@gmx.net>

based on
identicon.py
identicon python implementation.
by Shin Adachi <shn@glucose.jp>

= usage =

== python ==
>>> import qtidenticon
>>> qtidenticon.render_identicon(code, size)

Return a PIL Image class instance which have generated identicon image.
```size``` specifies `patch size`. Generated image size is 3 * ```size```.
"""

# we probably don't need all of them, but i don't want to check now
from PyQt4 import QtCore, QtGui
from PyQt4.QtCore import *
from PyQt4.QtGui import *

__all__ = ['render_identicon', 'IdenticonRendererBase']

class IdenticonRendererBase(object):
    PATH_SET = []
    
    def __init__(self, code):
        """
        @param code code for icon
        """
        if not isinstance(code, int):
            code = int(code)
        self.code = code
    
    def render(self, size, twoColor, opacity, penwidth):
        """
        render identicon to QPicture
        
        @param size identicon patchsize. (image size is 3 * [size])
        @return QPicture
        """
        
        # decode the code
        middle, corner, side, foreColor, secondColor, swap_cross = self.decode(self.code, twoColor)

        # make image
        image = QPixmap(QSize(size * 3 +penwidth, size * 3 +penwidth))
        
        # fill background
        backColor = QtGui.QColor(255,255,255,opacity)
        image.fill(backColor)
        
        kwds = {
            'image': image,
            'size': size,
            'foreColor': foreColor if swap_cross else secondColor,
            'penwidth': penwidth,
            'backColor': backColor}
            
        # middle patch
        image = self.drawPatchQt((1, 1), middle[2], middle[1], middle[0], **kwds)
        
        # side patch
        kwds['foreColor'] = foreColor
        kwds['type'] = side[0]
        for i in xrange(4):
            pos = [(1, 0), (2, 1), (1, 2), (0, 1)][i]
            image = self.drawPatchQt(pos, side[2] + 1 + i, side[1], **kwds)
            
        # corner patch
        kwds['foreColor'] = secondColor
        kwds['type'] = corner[0]
        for i in xrange(4):
            pos = [(0, 0), (2, 0), (2, 2), (0, 2)][i]
            image = self.drawPatchQt(pos, corner[2] + 1 + i, corner[1], **kwds)
        
        return image
                

    def drawPatchQt(self, pos, turn, invert, type, image, size, foreColor,
            backColor, penwidth):
        """
        @param size patch size
        """
        path = self.PATH_SET[type]
        if not path:
            # blank patch
            invert = not invert
            path = [(0., 0.), (1., 0.), (1., 1.), (0., 1.), (0., 0.)]

        
        polygon = QPolygonF([QPointF(x*size,y*size) for x,y in path])
        
        rot = turn % 4
        rect = [QPointF(0.,0.), QPointF(size, 0.), QPointF(size, size), QPointF(0., size)]
        rotation = [0,90,180,270]
        
        nopen = QtGui.QPen(foreColor, Qt.NoPen)
        foreBrush = QtGui.QBrush(foreColor, Qt.SolidPattern)
        if penwidth > 0:
            pen_color = QtGui.QColor(255, 255, 255)
            pen = QtGui.QPen(pen_color, Qt.SolidPattern)
            pen.setWidth(penwidth)
        
        painter = QPainter()
        painter.begin(image)
        painter.setPen(nopen)
        
        painter.translate(pos[0]*size +penwidth/2, pos[1]*size +penwidth/2)
        painter.translate(rect[rot])
        painter.rotate(rotation[rot])
        
        if invert:
            # subtract the actual polygon from a rectangle to invert it
            poly_rect = QPolygonF(rect)
            polygon = poly_rect.subtracted(polygon)
        painter.setBrush(foreBrush)
        if penwidth > 0:
            # draw the borders
            painter.setPen(pen)
            painter.drawPolygon(polygon, Qt.WindingFill)
        # draw the fill
        painter.setPen(nopen)
        painter.drawPolygon(polygon, Qt.WindingFill)
        
        painter.end()
        
        return image

    ### virtual functions
    def decode(self, code):
        raise NotImplementedError
        
class DonRenderer(IdenticonRendererBase):
    """
    Don Park's implementation of identicon
    see : http://www.docuverse.com/blog/donpark/2007/01/19/identicon-updated-and-source-released
    """
    
    PATH_SET = [
        #[0] full square:
        [(0, 0), (4, 0), (4, 4), (0, 4)],
        #[1] right-angled triangle pointing top-left:
        [(0, 0), (4, 0), (0, 4)],
        #[2] upwardy triangle:
        [(2, 0), (4, 4), (0, 4)],
        #[3] left half of square, standing rectangle:
        [(0, 0), (2, 0), (2, 4), (0, 4)],
        #[4] square standing on diagonale:
        [(2, 0), (4, 2), (2, 4), (0, 2)],
        #[5] kite pointing topleft:
        [(0, 0), (4, 2), (4, 4), (2, 4)],
        #[6] Sierpinski triangle, fractal triangles:
        [(2, 0), (4, 4), (2, 4), (3, 2), (1, 2), (2, 4), (0, 4)],
        #[7] sharp angled lefttop pointing triangle:
        [(0, 0), (4, 2), (2, 4)],
        #[8] small centered square:
        [(1, 1), (3, 1), (3, 3), (1, 3)],
        #[9] two small triangles:
        [(2, 0), (4, 0), (0, 4), (0, 2), (2, 2)],
        #[10] small topleft square:
        [(0, 0), (2, 0), (2, 2), (0, 2)],
        #[11] downpointing right-angled triangle on bottom:
        [(0, 2), (4, 2), (2, 4)],
        #[12] uppointing right-angled triangle on bottom:
        [(2, 2), (4, 4), (0, 4)],
        #[13] small rightbottom pointing right-angled triangle on topleft:
        [(2, 0), (2, 2), (0, 2)],
        #[14] small lefttop pointing right-angled triangle on topleft:
        [(0, 0), (2, 0), (0, 2)],
        #[15] empty:
        []]
    # get the [0] full square, [4] square standing on diagonale, [8] small centered square, or [15] empty tile:
    MIDDLE_PATCH_SET = [0, 4, 8, 15]
    
    # modify path set
    for idx in xrange(len(PATH_SET)):
        if PATH_SET[idx]:
            p = map(lambda vec: (vec[0] / 4.0, vec[1] / 4.0), PATH_SET[idx])
            PATH_SET[idx] = p + p[:1]
    
    def decode(self, code, twoColor):
        # decode the code
        shift  = 0; middleType  = (code >> shift) & 0x03
        shift += 2; middleInvert= (code >> shift) & 0x01
        shift += 1; cornerType  = (code >> shift) & 0x0F
        shift += 4; cornerInvert= (code >> shift) & 0x01
        shift += 1; cornerTurn  = (code >> shift) & 0x03
        shift += 2; sideType    = (code >> shift) & 0x0F
        shift += 4; sideInvert  = (code >> shift) & 0x01
        shift += 1; sideTurn    = (code >> shift) & 0x03
        shift += 2; blue        = (code >> shift) & 0x1F
        shift += 5; green       = (code >> shift) & 0x1F
        shift += 5; red         = (code >> shift) & 0x1F
        shift += 5; second_blue = (code >> shift) & 0x1F
        shift += 5; second_green= (code >> shift) & 0x1F
        shift += 5; second_red  = (code >> shift) & 0x1F
        shift += 1; swap_cross  = (code >> shift) & 0x01
        
        middleType = self.MIDDLE_PATCH_SET[middleType]
        
        foreColor = (red << 3, green << 3, blue << 3)
        foreColor = QtGui.QColor(*foreColor)
        
        if twoColor:
            secondColor = (second_blue << 3, second_green << 3, second_red << 3)
            secondColor = QtGui.QColor(*secondColor)
        else:
            secondColor = foreColor
        
        return (middleType, middleInvert, 0),\
               (cornerType, cornerInvert, cornerTurn),\
               (sideType, sideInvert, sideTurn),\
               foreColor, secondColor, swap_cross


def render_identicon(code, size, twoColor=False, opacity=255, penwidth=0, renderer=None):
    if not renderer:
        renderer = DonRenderer
    return renderer(code).render(size, twoColor, opacity, penwidth)
########NEW FILE########
__FILENAME__ = shared
softwareVersion = '0.4.2'
verbose = 1
maximumAgeOfAnObjectThatIAmWillingToAccept = 216000  # Equals two days and 12 hours.
lengthOfTimeToLeaveObjectsInInventory = 237600 # Equals two days and 18 hours. This should be longer than maximumAgeOfAnObjectThatIAmWillingToAccept so that we don't process messages twice.
lengthOfTimeToHoldOnToAllPubkeys = 2419200  # Equals 4 weeks. You could make this longer if you want but making it shorter would not be advisable because there is a very small possibility that it could keep you from obtaining a needed pubkey for a period of time.
maximumAgeOfObjectsThatIAdvertiseToOthers = 216000  # Equals two days and 12 hours
maximumAgeOfNodesThatIAdvertiseToOthers = 10800  # Equals three hours
useVeryEasyProofOfWorkForTesting = False  # If you set this to True while on the normal network, you won't be able to send or sometimes receive messages.


# Libraries.
import collections
import ConfigParser
import os
import pickle
import Queue
import random
import socket
import sys
import stat
import threading
import time
from os import path, environ

# Project imports.
from addresses import *
import highlevelcrypto
import shared
import helper_startup
from helper_sql import *


config = ConfigParser.SafeConfigParser()
myECCryptorObjects = {}
MyECSubscriptionCryptorObjects = {}
myAddressesByHash = {} #The key in this dictionary is the RIPE hash which is encoded in an address and value is the address itself.
myAddressesByTag = {} # The key in this dictionary is the tag generated from the address.
broadcastSendersForWhichImWatching = {}
workerQueue = Queue.Queue()
UISignalQueue = Queue.Queue()
addressGeneratorQueue = Queue.Queue()
knownNodesLock = threading.Lock()
knownNodes = {}
sendDataQueues = [] #each sendData thread puts its queue in this list.
inventory = {} #of objects (like msg payloads and pubkey payloads) Does not include protocol headers (the first 24 bytes of each packet).
inventoryLock = threading.Lock() #Guarantees that two receiveDataThreads don't receive and process the same message concurrently (probably sent by a malicious individual)
printLock = threading.Lock()
objectProcessorQueueSizeLock = threading.Lock()
objectProcessorQueueSize = 0 # in Bytes. We maintain this to prevent nodes from flooing us with objects which take up too much memory. If this gets too big we'll sleep before asking for further objects.
appdata = '' #holds the location of the application data storage directory
statusIconColor = 'red'
connectedHostsList = {} #List of hosts to which we are connected. Used to guarantee that the outgoingSynSender threads won't connect to the same remote node twice.
shutdown = 0 #Set to 1 by the doCleanShutdown function. Used to tell the proof of work worker threads to exit.
alreadyAttemptedConnectionsList = {
}  # This is a list of nodes to which we have already attempted a connection
alreadyAttemptedConnectionsListLock = threading.Lock()
alreadyAttemptedConnectionsListResetTime = int(
    time.time())  # used to clear out the alreadyAttemptedConnectionsList periodically so that we will retry connecting to hosts to which we have already tried to connect.
numberOfObjectsThatWeHaveYetToGetPerPeer = {}
neededPubkeys = {}
eightBytesOfRandomDataUsedToDetectConnectionsToSelf = pack(
    '>Q', random.randrange(1, 18446744073709551615))
successfullyDecryptMessageTimings = [
    ]  # A list of the amounts of time it took to successfully decrypt msg messages
apiAddressGeneratorReturnQueue = Queue.Queue(
    )  # The address generator thread uses this queue to get information back to the API thread.
ackdataForWhichImWatching = {}
clientHasReceivedIncomingConnections = False #used by API command clientStatus
numberOfMessagesProcessed = 0
numberOfBroadcastsProcessed = 0
numberOfPubkeysProcessed = 0
numberOfInventoryLookupsPerformed = 0
daemon = False
inventorySets = {} # key = streamNumer, value = a set which holds the inventory object hashes that we are aware of. This is used whenever we receive an inv message from a peer to check to see what items are new to us. We don't delete things out of it; instead, the singleCleaner thread clears and refills it every couple hours.
needToWriteKnownNodesToDisk = False # If True, the singleCleaner will write it to disk eventually.
maximumLengthOfTimeToBotherResendingMessages = 0
objectProcessorQueue = Queue.Queue(
    )  # receiveDataThreads dump objects they hear on the network into this queue to be processed.
streamsInWhichIAmParticipating = {}

#If changed, these values will cause particularly unexpected behavior: You won't be able to either send or receive messages because the proof of work you do (or demand) won't match that done or demanded by others. Don't change them!
networkDefaultProofOfWorkNonceTrialsPerByte = 320 #The amount of work that should be performed (and demanded) per byte of the payload. Double this number to double the work.
networkDefaultPayloadLengthExtraBytes = 14000 #To make sending short messages a little more difficult, this value is added to the payload length for use in calculating the proof of work target.

# Remember here the RPC port read from namecoin.conf so we can restore to
# it as default whenever the user changes the "method" selection for
# namecoin integration to "namecoind".
namecoinDefaultRpcPort = "8336"

# When using py2exe or py2app, the variable frozen is added to the sys
# namespace.  This can be used to setup a different code path for 
# binary distributions vs source distributions.
frozen = getattr(sys,'frozen', None)

# If the trustedpeer option is specified in keys.dat then this will
# contain a Peer which will be connected to instead of using the
# addresses advertised by other peers. The client will only connect to
# this peer and the timing attack mitigation will be disabled in order
# to download data faster. The expected use case is where the user has
# a fast connection to a trusted server where they run a BitMessage
# daemon permanently. If they then run a second instance of the client
# on a local machine periodically when they want to check for messages
# it will sync with the network a lot faster without compromising
# security.
trustedPeer = None

def isInSqlInventory(hash):
    queryreturn = sqlQuery('''select hash from inventory where hash=?''', hash)
    return queryreturn != []

def encodeHost(host):
    if host.find(':') == -1:
        return '\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\xFF\xFF' + \
            socket.inet_aton(host)
    else:
        return socket.inet_pton(socket.AF_INET6, host)

def assembleVersionMessage(remoteHost, remotePort, myStreamNumber):
    payload = ''
    payload += pack('>L', 2)  # protocol version.
    payload += pack('>q', 1)  # bitflags of the services I offer.
    payload += pack('>q', int(time.time()))

    payload += pack(
        '>q', 1)  # boolservices of remote connection; ignored by the remote host.
    payload += encodeHost(remoteHost)
    payload += pack('>H', remotePort)  # remote IPv6 and port

    payload += pack('>q', 1)  # bitflags of the services I offer.
    payload += '\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\xFF\xFF' + pack(
        '>L', 2130706433)  # = 127.0.0.1. This will be ignored by the remote host. The actual remote connected IP will be used.
    payload += pack('>H', shared.config.getint(
        'bitmessagesettings', 'port'))

    random.seed()
    payload += eightBytesOfRandomDataUsedToDetectConnectionsToSelf
    userAgent = '/PyBitmessage:' + shared.softwareVersion + '/'
    payload += encodeVarint(len(userAgent))
    payload += userAgent
    payload += encodeVarint(
        1)  # The number of streams about which I care. PyBitmessage currently only supports 1 per connection.
    payload += encodeVarint(myStreamNumber)

    datatosend = '\xe9\xbe\xb4\xd9'  # magic bits, slighly different from Bitcoin's magic bits.
    datatosend = datatosend + 'version\x00\x00\x00\x00\x00'  # version command
    datatosend = datatosend + pack('>L', len(payload))  # payload length
    datatosend = datatosend + hashlib.sha512(payload).digest()[0:4]
    return datatosend + payload

def lookupAppdataFolder():
    APPNAME = "PyBitmessage"
    if "BITMESSAGE_HOME" in environ:
        dataFolder = environ["BITMESSAGE_HOME"]
        if dataFolder[-1] not in [os.path.sep, os.path.altsep]:
            dataFolder += os.path.sep
    elif sys.platform == 'darwin':
        if "HOME" in environ:
            dataFolder = path.join(os.environ["HOME"], "Library/Application Support/", APPNAME) + '/'
        else:
            stringToLog = 'Could not find home folder, please report this message and your OS X version to the BitMessage Github.'
            if 'logger' in globals():
                logger.critical(stringToLog)
            else:
                print stringToLog
            sys.exit()

    elif 'win32' in sys.platform or 'win64' in sys.platform:
        dataFolder = path.join(environ['APPDATA'].decode(sys.getfilesystemencoding(), 'ignore'), APPNAME) + path.sep
    else:
        from shutil import move
        try:
            dataFolder = path.join(environ["XDG_CONFIG_HOME"], APPNAME)
        except KeyError:
            dataFolder = path.join(environ["HOME"], ".config", APPNAME)

        # Migrate existing data to the proper location if this is an existing install
        try:
            move(path.join(environ["HOME"], ".%s" % APPNAME), dataFolder)
            stringToLog = "Moving data folder to %s" % (dataFolder)
            if 'logger' in globals():
                logger.info(stringToLog)
            else:
                print stringToLog
        except IOError:
            # Old directory may not exist.
            pass
        dataFolder = dataFolder + '/'
    return dataFolder

def isAddressInMyAddressBook(address):
    queryreturn = sqlQuery(
        '''select address from addressbook where address=?''',
        address)
    return queryreturn != []

#At this point we should really just have a isAddressInMy(book, address)...
def isAddressInMySubscriptionsList(address):
    queryreturn = sqlQuery(
        '''select * from subscriptions where address=?''',
        str(address))
    return queryreturn != []

def isAddressInMyAddressBookSubscriptionsListOrWhitelist(address):
    if isAddressInMyAddressBook(address):
        return True

    queryreturn = sqlQuery('''SELECT address FROM whitelist where address=? and enabled = '1' ''', address)
    if queryreturn <> []:
        return True

    queryreturn = sqlQuery(
        '''select address from subscriptions where address=? and enabled = '1' ''',
        address)
    if queryreturn <> []:
        return True
    return False

def safeConfigGetBoolean(section,field):
    try:
        return config.getboolean(section,field)
    except Exception, err:
        return False

def decodeWalletImportFormat(WIFstring):
    fullString = arithmetic.changebase(WIFstring,58,256)
    privkey = fullString[:-4]
    if fullString[-4:] != hashlib.sha256(hashlib.sha256(privkey).digest()).digest()[:4]:
        logger.critical('Major problem! When trying to decode one of your private keys, the checksum '
                     'failed. Here are the first 6 characters of the PRIVATE key: %s' % str(WIFstring)[:6])
        os._exit(0)
        return ""
    else:
        #checksum passed
        if privkey[0] == '\x80':
            return privkey[1:]
        else:
            logger.critical('Major problem! When trying to decode one of your private keys, the '
                         'checksum passed but the key doesn\'t begin with hex 80. Here is the '
                         'PRIVATE key: %s' % str(WIFstring))
            os._exit(0)
            return ""


def reloadMyAddressHashes():
    logger.debug('reloading keys from keys.dat file')
    myECCryptorObjects.clear()
    myAddressesByHash.clear()
    myAddressesByTag.clear()
    #myPrivateKeys.clear()

    keyfileSecure = checkSensitiveFilePermissions(appdata + 'keys.dat')
    configSections = config.sections()
    hasEnabledKeys = False
    for addressInKeysFile in configSections:
        if addressInKeysFile <> 'bitmessagesettings':
            isEnabled = config.getboolean(addressInKeysFile, 'enabled')
            if isEnabled:
                hasEnabledKeys = True
                status,addressVersionNumber,streamNumber,hash = decodeAddress(addressInKeysFile)
                if addressVersionNumber == 2 or addressVersionNumber == 3 or addressVersionNumber == 4:
                    # Returns a simple 32 bytes of information encoded in 64 Hex characters,
                    # or null if there was an error.
                    privEncryptionKey = decodeWalletImportFormat(
                            config.get(addressInKeysFile, 'privencryptionkey')).encode('hex')

                    if len(privEncryptionKey) == 64:#It is 32 bytes encoded as 64 hex characters
                        myECCryptorObjects[hash] = highlevelcrypto.makeCryptor(privEncryptionKey)
                        myAddressesByHash[hash] = addressInKeysFile
                        tag = hashlib.sha512(hashlib.sha512(encodeVarint(
                            addressVersionNumber) + encodeVarint(streamNumber) + hash).digest()).digest()[32:]
                        myAddressesByTag[tag] = addressInKeysFile

                else:
                    logger.error('Error in reloadMyAddressHashes: Can\'t handle address versions other than 2, 3, or 4.\n')

    if not keyfileSecure:
        fixSensitiveFilePermissions(appdata + 'keys.dat', hasEnabledKeys)

def reloadBroadcastSendersForWhichImWatching():
    broadcastSendersForWhichImWatching.clear()
    MyECSubscriptionCryptorObjects.clear()
    queryreturn = sqlQuery('SELECT address FROM subscriptions where enabled=1')
    logger.debug('reloading subscriptions...')
    for row in queryreturn:
        address, = row
        status,addressVersionNumber,streamNumber,hash = decodeAddress(address)
        if addressVersionNumber == 2:
            broadcastSendersForWhichImWatching[hash] = 0
        #Now, for all addresses, even version 2 addresses, we should create Cryptor objects in a dictionary which we will use to attempt to decrypt encrypted broadcast messages.
        
        if addressVersionNumber <= 3:
            privEncryptionKey = hashlib.sha512(encodeVarint(addressVersionNumber)+encodeVarint(streamNumber)+hash).digest()[:32]
            MyECSubscriptionCryptorObjects[hash] = highlevelcrypto.makeCryptor(privEncryptionKey.encode('hex'))
        else:
            doubleHashOfAddressData = hashlib.sha512(hashlib.sha512(encodeVarint(
                addressVersionNumber) + encodeVarint(streamNumber) + hash).digest()).digest()
            tag = doubleHashOfAddressData[32:]
            privEncryptionKey = doubleHashOfAddressData[:32]
            MyECSubscriptionCryptorObjects[tag] = highlevelcrypto.makeCryptor(privEncryptionKey.encode('hex'))

def isProofOfWorkSufficient(
    data,
    nonceTrialsPerByte=0,
        payloadLengthExtraBytes=0):
    if nonceTrialsPerByte < networkDefaultProofOfWorkNonceTrialsPerByte:
        nonceTrialsPerByte = networkDefaultProofOfWorkNonceTrialsPerByte
    if payloadLengthExtraBytes < networkDefaultPayloadLengthExtraBytes:
        payloadLengthExtraBytes = networkDefaultPayloadLengthExtraBytes
    POW, = unpack('>Q', hashlib.sha512(hashlib.sha512(data[
                  :8] + hashlib.sha512(data[8:]).digest()).digest()).digest()[0:8])
    return POW <= 2 ** 64 / ((len(data) + payloadLengthExtraBytes) * (nonceTrialsPerByte))

def doCleanShutdown():
    global shutdown
    shutdown = 1 #Used to tell proof of work worker threads and the objectProcessorThread to exit.
    broadcastToSendDataQueues((0, 'shutdown', 'all'))   
    with shared.objectProcessorQueueSizeLock:
        data = 'no data'
        shared.objectProcessorQueueSize += len(data)
        objectProcessorQueue.put(('checkShutdownVariable',data))
    
    knownNodesLock.acquire()
    UISignalQueue.put(('updateStatusBar','Saving the knownNodes list of peers to disk...'))
    output = open(appdata + 'knownnodes.dat', 'wb')
    logger.info('finished opening knownnodes.dat. Now pickle.dump')
    pickle.dump(knownNodes, output)
    logger.info('Completed pickle.dump. Closing output...')
    output.close()
    knownNodesLock.release()
    logger.info('Finished closing knownnodes.dat output file.')
    UISignalQueue.put(('updateStatusBar','Done saving the knownNodes list of peers to disk.'))

    logger.info('Flushing inventory in memory out to disk...')
    UISignalQueue.put((
        'updateStatusBar',
        'Flushing inventory in memory out to disk. This should normally only take a second...'))
    flushInventory()
    
    # Verify that the objectProcessor has finished exiting. It should have incremented the 
    # shutdown variable from 1 to 2. This must finish before we command the sqlThread to exit.
    while shutdown == 1:
        time.sleep(.1)
    
    # This one last useless query will guarantee that the previous flush committed and that the
    # objectProcessorThread committed before we close the program.
    sqlQuery('SELECT address FROM subscriptions')
    logger.info('Finished flushing inventory.')
    sqlStoredProcedure('exit')
    
    # Wait long enough to guarantee that any running proof of work worker threads will check the
    # shutdown variable and exit. If the main thread closes before they do then they won't stop.
    time.sleep(.25) 

    if safeConfigGetBoolean('bitmessagesettings','daemon'):
        logger.info('Clean shutdown complete.')
        os._exit(0)

# When you want to command a sendDataThread to do something, like shutdown or send some data, this
# function puts your data into the queues for each of the sendDataThreads. The sendDataThreads are
# responsible for putting their queue into (and out of) the sendDataQueues list.
def broadcastToSendDataQueues(data):
    # logger.debug('running broadcastToSendDataQueues')
    for q in sendDataQueues:
        q.put(data)
        
def flushInventory():
    #Note that the singleCleanerThread clears out the inventory dictionary from time to time, although it only clears things that have been in the dictionary for a long time. This clears the inventory dictionary Now.
    with SqlBulkExecute() as sql:
        for hash, storedValue in inventory.items():
            objectType, streamNumber, payload, receivedTime, tag = storedValue
            sql.execute('''INSERT INTO inventory VALUES (?,?,?,?,?,?)''',
                       hash,objectType,streamNumber,payload,receivedTime,tag)
            del inventory[hash]

def fixPotentiallyInvalidUTF8Data(text):
    try:
        unicode(text,'utf-8')
        return text
    except:
        output = 'Part of the message is corrupt. The message cannot be displayed the normal way.\n\n' + repr(text)
        return output

# Checks sensitive file permissions for inappropriate umask during keys.dat creation.
# (Or unwise subsequent chmod.)
#
# Returns true iff file appears to have appropriate permissions.
def checkSensitiveFilePermissions(filename):
    if sys.platform == 'win32':
        # TODO: This might deserve extra checks by someone familiar with
        # Windows systems.
        return True
    elif sys.platform[:7] == 'freebsd':
        # FreeBSD file systems are the same as major Linux file systems
        present_permissions = os.stat(filename)[0]
        disallowed_permissions = stat.S_IRWXG | stat.S_IRWXO
        return present_permissions & disallowed_permissions == 0
    else:
        try:
            # Skip known problems for non-Win32 filesystems without POSIX permissions.
            import subprocess
            fstype = subprocess.check_output('stat -f -c "%%T" %s' % (filename),
                                             shell=True,
                                             stderr=subprocess.STDOUT)
            if 'fuseblk' in fstype:
                logger.info('Skipping file permissions check for %s. Filesystem fuseblk detected.',
                            filename)
                return True
        except:
            # Swallow exception here, but we might run into trouble later!
            logger.error('Could not determine filesystem type. %s', filename)
        present_permissions = os.stat(filename)[0]
        disallowed_permissions = stat.S_IRWXG | stat.S_IRWXO
        return present_permissions & disallowed_permissions == 0

# Fixes permissions on a sensitive file.
def fixSensitiveFilePermissions(filename, hasEnabledKeys):
    if hasEnabledKeys:
        logger.warning('Keyfile had insecure permissions, and there were enabled keys. '
                       'The truly paranoid should stop using them immediately.')
    else:
        logger.warning('Keyfile had insecure permissions, but there were no enabled keys.')
    try:
        present_permissions = os.stat(filename)[0]
        disallowed_permissions = stat.S_IRWXG | stat.S_IRWXO
        allowed_permissions = ((1<<32)-1) ^ disallowed_permissions
        new_permissions = (
            allowed_permissions & present_permissions)
        os.chmod(filename, new_permissions)

        logger.info('Keyfile permissions automatically fixed.')

    except Exception, e:
        logger.exception('Keyfile permissions could not be fixed.')
        raise
    
def isBitSetWithinBitfield(fourByteString, n):
    # Uses MSB 0 bit numbering across 4 bytes of data
    n = 31 - n
    x, = unpack('>L', fourByteString)
    return x & 2**n != 0

def decryptAndCheckPubkeyPayload(payload, address):
    status, addressVersion, streamNumber, ripe = decodeAddress(address)
    doubleHashOfAddressData = hashlib.sha512(hashlib.sha512(encodeVarint(
        addressVersion) + encodeVarint(streamNumber) + ripe).digest()).digest()
    readPosition = 8 # bypass the nonce
    readPosition += 8 # bypass the time
    embeddedVersionNumber, varintLength = decodeVarint(
        payload[readPosition:readPosition + 10])
    if embeddedVersionNumber != addressVersion:
        logger.info('Pubkey decryption was UNsuccessful due to address version mismatch. This shouldn\'t have happened.')
        return 'failed'
    readPosition += varintLength
    embeddedStreamNumber, varintLength = decodeVarint(
        payload[readPosition:readPosition + 10])
    if embeddedStreamNumber != streamNumber:
        logger.info('Pubkey decryption was UNsuccessful due to stream number mismatch. This shouldn\'t have happened.')
        return 'failed'
    readPosition += varintLength
    signedData = payload[8:readPosition] # Some of the signed data is not encrypted so let's keep it for now.
    toTag = payload[readPosition:readPosition+32]
    readPosition += 32 #for the tag
    encryptedData = payload[readPosition:]
    # Let us try to decrypt the pubkey
    privEncryptionKey = doubleHashOfAddressData[:32]
    cryptorObject = highlevelcrypto.makeCryptor(privEncryptionKey.encode('hex'))
    try:
        decryptedData = cryptorObject.decrypt(encryptedData)
    except:
        # Someone must have encrypted some data with a different key
        # but tagged it with a tag for which we are watching.
        logger.info('Pubkey decryption was UNsuccessful. This shouldn\'t have happened.')
        return 'failed'
    logger.debug('Pubkey decryption successful')
    readPosition = 4 # bypass the behavior bitfield
    publicSigningKey = '\x04' + decryptedData[readPosition:readPosition + 64]
    # Is it possible for a public key to be invalid such that trying to
    # encrypt or check a sig with it will cause an error? If it is, we should
    # probably test these keys here.
    readPosition += 64
    publicEncryptionKey = '\x04' + decryptedData[readPosition:readPosition + 64]
    readPosition += 64
    specifiedNonceTrialsPerByte, specifiedNonceTrialsPerByteLength = decodeVarint(
        decryptedData[readPosition:readPosition + 10])
    readPosition += specifiedNonceTrialsPerByteLength
    specifiedPayloadLengthExtraBytes, specifiedPayloadLengthExtraBytesLength = decodeVarint(
        decryptedData[readPosition:readPosition + 10])
    readPosition += specifiedPayloadLengthExtraBytesLength
    signedData += decryptedData[:readPosition]
    signatureLength, signatureLengthLength = decodeVarint(
        decryptedData[readPosition:readPosition + 10])
    readPosition += signatureLengthLength
    signature = decryptedData[readPosition:readPosition + signatureLength]
    try:
        if not highlevelcrypto.verify(signedData, signature, publicSigningKey.encode('hex')):
            logger.info('ECDSA verify failed (within decryptAndCheckPubkeyPayload).')
            return 'failed'
        logger.debug('ECDSA verify passed (within decryptAndCheckPubkeyPayload)')
    except Exception as err:
        logger.debug('ECDSA verify failed (within decryptAndCheckPubkeyPayload) %s' % err)
        return 'failed'

    sha = hashlib.new('sha512')
    sha.update(publicSigningKey + publicEncryptionKey)
    ripeHasher = hashlib.new('ripemd160')
    ripeHasher.update(sha.digest())
    embeddedRipe = ripeHasher.digest()

    if embeddedRipe != ripe:
        # Although this pubkey object had the tag were were looking for and was
        # encrypted with the correct encryption key, it doesn't contain the
        # correct keys. Someone is either being malicious or using buggy software.
        logger.info('Pubkey decryption was UNsuccessful due to RIPE mismatch. This shouldn\'t have happened.')
        return 'failed'
    
    t = (ripe, addressVersion, signedData, int(time.time()), 'yes')
    sqlExecute('''INSERT INTO pubkeys VALUES (?,?,?,?,?)''', *t)
    return 'successful'

Peer = collections.namedtuple('Peer', ['host', 'port'])

def checkAndShareMsgWithPeers(data):
    # Let us check to make sure that the proof of work is sufficient.
    if not isProofOfWorkSufficient(data):
        logger.debug('Proof of work in msg message insufficient.')
        return

    readPosition = 8
    embeddedTime, = unpack('>I', data[readPosition:readPosition + 4])

    # This section is used for the transition from 32 bit time to 64 bit
    # time in the protocol.
    if embeddedTime == 0:
        embeddedTime, = unpack('>Q', data[readPosition:readPosition + 8])
        readPosition += 8
    else:
        readPosition += 4

    if embeddedTime > (int(time.time()) + 10800): 
        logger.debug('The embedded time in this msg message is more than three hours in the future. That doesn\'t make sense. Ignoring message.')
        return
    if embeddedTime < (int(time.time()) - maximumAgeOfAnObjectThatIAmWillingToAccept):
        logger.debug('The embedded time in this msg message is too old. Ignoring message.')
        return
    streamNumberAsClaimedByMsg, streamNumberAsClaimedByMsgLength = decodeVarint(
        data[readPosition:readPosition + 9])
    if not streamNumberAsClaimedByMsg in streamsInWhichIAmParticipating:
        logger.debug('The streamNumber %s isn\'t one we are interested in.' % streamNumberAsClaimedByMsg)
        return
    readPosition += streamNumberAsClaimedByMsgLength
    inventoryHash = calculateInventoryHash(data)
    shared.numberOfInventoryLookupsPerformed += 1
    inventoryLock.acquire()
    if inventoryHash in inventory:
        logger.debug('We have already received this msg message. Ignoring.')
        inventoryLock.release()
        return
    elif isInSqlInventory(inventoryHash):
        logger.debug('We have already received this msg message (it is stored on disk in the SQL inventory). Ignoring it.')
        inventoryLock.release()
        return
    # This msg message is valid. Let's let our peers know about it.
    objectType = 'msg'
    inventory[inventoryHash] = (
        objectType, streamNumberAsClaimedByMsg, data, embeddedTime,'')
    inventorySets[streamNumberAsClaimedByMsg].add(inventoryHash)
    inventoryLock.release()
    logger.debug('advertising inv with hash: %s' % inventoryHash.encode('hex'))
    broadcastToSendDataQueues((streamNumberAsClaimedByMsg, 'advertiseobject', inventoryHash))

    # Now let's enqueue it to be processed ourselves.
    # If we already have too much data in the queue to be processed, just sleep for now.
    while shared.objectProcessorQueueSize > 120000000:
        time.sleep(2)
    with shared.objectProcessorQueueSizeLock:
        shared.objectProcessorQueueSize += len(data)
        objectProcessorQueue.put((objectType,data))

def checkAndSharegetpubkeyWithPeers(data):
    if not isProofOfWorkSufficient(data):
        logger.debug('Proof of work in getpubkey message insufficient.')
        return
    if len(data) < 34:
        logger.debug('getpubkey message doesn\'t contain enough data. Ignoring.')
        return
    readPosition = 8  # bypass the nonce
    embeddedTime, = unpack('>I', data[readPosition:readPosition + 4])

    # This section is used for the transition from 32 bit time to 64 bit
    # time in the protocol.
    if embeddedTime == 0:
        embeddedTime, = unpack('>Q', data[readPosition:readPosition + 8])
        readPosition += 8
    else:
        readPosition += 4

    if embeddedTime > int(time.time()) + 10800:
        logger.debug('The time in this getpubkey message is too new. Ignoring it. Time: %s' % embeddedTime)
        return
    if embeddedTime < int(time.time()) - maximumAgeOfAnObjectThatIAmWillingToAccept:
        logger.debug('The time in this getpubkey message is too old. Ignoring it. Time: %s' % embeddedTime)
        return
    requestedAddressVersionNumber, addressVersionLength = decodeVarint(
        data[readPosition:readPosition + 10])
    readPosition += addressVersionLength
    streamNumber, streamNumberLength = decodeVarint(
        data[readPosition:readPosition + 10])
    if not streamNumber in streamsInWhichIAmParticipating:
        logger.debug('The streamNumber %s isn\'t one we are interested in.' % streamNumber)
        return
    readPosition += streamNumberLength

    shared.numberOfInventoryLookupsPerformed += 1
    inventoryHash = calculateInventoryHash(data)
    inventoryLock.acquire()
    if inventoryHash in inventory:
        logger.debug('We have already received this getpubkey request. Ignoring it.')
        inventoryLock.release()
        return
    elif isInSqlInventory(inventoryHash):
        logger.debug('We have already received this getpubkey request (it is stored on disk in the SQL inventory). Ignoring it.')
        inventoryLock.release()
        return

    objectType = 'getpubkey'
    inventory[inventoryHash] = (
        objectType, streamNumber, data, embeddedTime,'')
    inventorySets[streamNumber].add(inventoryHash)
    inventoryLock.release()
    # This getpubkey request is valid. Forward to peers.
    logger.debug('advertising inv with hash: %s' % inventoryHash.encode('hex'))
    broadcastToSendDataQueues((streamNumber, 'advertiseobject', inventoryHash))

    # Now let's queue it to be processed ourselves.
    # If we already have too much data in the queue to be processed, just sleep for now.
    while shared.objectProcessorQueueSize > 120000000:
        time.sleep(2)
    with shared.objectProcessorQueueSizeLock:
        shared.objectProcessorQueueSize += len(data)
        objectProcessorQueue.put((objectType,data))

def checkAndSharePubkeyWithPeers(data):
    if len(data) < 146 or len(data) > 420:  # sanity check
        return
    # Let us make sure that the proof of work is sufficient.
    if not isProofOfWorkSufficient(data):
        logger.debug('Proof of work in pubkey message insufficient.')
        return

    readPosition = 8  # for the nonce
    embeddedTime, = unpack('>I', data[readPosition:readPosition + 4])

    # This section is used for the transition from 32 bit time to 64 bit
    # time in the protocol.
    if embeddedTime == 0:
        embeddedTime, = unpack('>Q', data[readPosition:readPosition + 8])
        readPosition += 8
    else:
        readPosition += 4

    if embeddedTime < int(time.time()) - lengthOfTimeToHoldOnToAllPubkeys:
        logger.debug('The embedded time in this pubkey message is too old. Ignoring. Embedded time is: %s' % embeddedTime)
        return
    if embeddedTime > int(time.time()) + 10800:
        logger.debug('The embedded time in this pubkey message more than several hours in the future. This is irrational. Ignoring message.') 
        return
    addressVersion, varintLength = decodeVarint(
        data[readPosition:readPosition + 10])
    readPosition += varintLength
    streamNumber, varintLength = decodeVarint(
        data[readPosition:readPosition + 10])
    readPosition += varintLength
    if not streamNumber in streamsInWhichIAmParticipating:
        logger.debug('The streamNumber %s isn\'t one we are interested in.' % streamNumber)
        return
    if addressVersion >= 4:
        tag = data[readPosition:readPosition + 32]
        logger.debug('tag in received pubkey is: %s' % tag.encode('hex'))
    else:
        tag = ''

    shared.numberOfInventoryLookupsPerformed += 1
    inventoryHash = calculateInventoryHash(data)
    inventoryLock.acquire()
    if inventoryHash in inventory:
        logger.debug('We have already received this pubkey. Ignoring it.')
        inventoryLock.release()
        return
    elif isInSqlInventory(inventoryHash):
        logger.debug('We have already received this pubkey (it is stored on disk in the SQL inventory). Ignoring it.')
        inventoryLock.release()
        return
    objectType = 'pubkey'
    inventory[inventoryHash] = (
        objectType, streamNumber, data, embeddedTime, tag)
    inventorySets[streamNumber].add(inventoryHash)
    inventoryLock.release()
    # This object is valid. Forward it to peers.
    logger.debug('advertising inv with hash: %s' % inventoryHash.encode('hex'))
    broadcastToSendDataQueues((streamNumber, 'advertiseobject', inventoryHash))


    # Now let's queue it to be processed ourselves.
    # If we already have too much data in the queue to be processed, just sleep for now.
    while shared.objectProcessorQueueSize > 120000000:
        time.sleep(2)
    with shared.objectProcessorQueueSizeLock:
        shared.objectProcessorQueueSize += len(data)
        objectProcessorQueue.put((objectType,data))


def checkAndShareBroadcastWithPeers(data):
    # Let us verify that the proof of work is sufficient.
    if not isProofOfWorkSufficient(data):
        logger.debug('Proof of work in broadcast message insufficient.')
        return
    readPosition = 8  # bypass the nonce
    embeddedTime, = unpack('>I', data[readPosition:readPosition + 4])

    # This section is used for the transition from 32 bit time to 64 bit
    # time in the protocol.
    if embeddedTime == 0:
        embeddedTime, = unpack('>Q', data[readPosition:readPosition + 8])
        readPosition += 8
    else:
        readPosition += 4

    if embeddedTime > (int(time.time()) + 10800):  # prevent funny business
        logger.debug('The embedded time in this broadcast message is more than three hours in the future. That doesn\'t make sense. Ignoring message.') 
        return
    if embeddedTime < (int(time.time()) - maximumAgeOfAnObjectThatIAmWillingToAccept):
        logger.debug('The embedded time in this broadcast message is too old. Ignoring message.')
        return
    if len(data) < 180:
        logger.debug('The payload length of this broadcast packet is unreasonably low. Someone is probably trying funny business. Ignoring message.')
        return
    broadcastVersion, broadcastVersionLength = decodeVarint(
        data[readPosition:readPosition + 10])
    readPosition += broadcastVersionLength
    if broadcastVersion >= 2:
        streamNumber, streamNumberLength = decodeVarint(data[readPosition:readPosition + 10])
        readPosition += streamNumberLength
        if not streamNumber in streamsInWhichIAmParticipating:
            logger.debug('The streamNumber %s isn\'t one we are interested in.' % streamNumber)
            return
    if broadcastVersion >= 3:
        tag = data[readPosition:readPosition+32]
    else:
        tag = ''
    shared.numberOfInventoryLookupsPerformed += 1
    inventoryLock.acquire()
    inventoryHash = calculateInventoryHash(data)
    if inventoryHash in inventory:
        logger.debug('We have already received this broadcast object. Ignoring.')
        inventoryLock.release()
        return
    elif isInSqlInventory(inventoryHash):
        logger.debug('We have already received this broadcast object (it is stored on disk in the SQL inventory). Ignoring it.')
        inventoryLock.release()
        return
    # It is valid. Let's let our peers know about it.
    objectType = 'broadcast'
    inventory[inventoryHash] = (
        objectType, streamNumber, data, embeddedTime, tag)
    inventorySets[streamNumber].add(inventoryHash)
    inventoryLock.release()
    # This object is valid. Forward it to peers.
    logger.debug('advertising inv with hash: %s' % inventoryHash.encode('hex'))
    broadcastToSendDataQueues((streamNumber, 'advertiseobject', inventoryHash))

    # Now let's queue it to be processed ourselves.
    # If we already have too much data in the queue to be processed, just sleep for now.
    while shared.objectProcessorQueueSize > 120000000:
        time.sleep(2)
    with shared.objectProcessorQueueSizeLock:
        shared.objectProcessorQueueSize += len(data)
        objectProcessorQueue.put((objectType,data))


helper_startup.loadConfig()
from debug import logger

########NEW FILE########
__FILENAME__ = singleton
#! /usr/bin/env python

import sys
import os
import errno
import tempfile
from multiprocessing import Process


class singleinstance:
    """
    Implements a single instance application by creating a lock file based on the full path to the script file.

    This is based upon the singleton class from tendo https://github.com/pycontribs/tendo
    which is under the Python Software Foundation License version 2    
    """
    def __init__(self, flavor_id=""):
        import sys
        self.initialized = False
        basename = os.path.splitext(os.path.abspath(sys.argv[0]))[0].replace("/", "-").replace(":", "").replace("\\", "-") + '-%s' % flavor_id + '.lock'
        self.lockfile = os.path.normpath(tempfile.gettempdir() + '/' + basename)

        if sys.platform == 'win32':
            try:
                # file already exists, we try to remove (in case previous execution was interrupted)
                if os.path.exists(self.lockfile):
                    os.unlink(self.lockfile)
                self.fd = os.open(self.lockfile, os.O_CREAT | os.O_EXCL | os.O_RDWR)
            except OSError:
                type, e, tb = sys.exc_info()
                if e.errno == 13:
                    print 'Another instance of this application is already running'
                    sys.exit(-1)
                print(e.errno)
                raise
        else:  # non Windows
            import fcntl  # @UnresolvedImport
            self.fp = open(self.lockfile, 'w')
            try:
                fcntl.lockf(self.fp, fcntl.LOCK_EX | fcntl.LOCK_NB)
            except IOError:
                print 'Another instance of this application is already running'
                sys.exit(-1)
        self.initialized = True

    def __del__(self):
        import sys
        if not self.initialized:
            return
        try:
            if sys.platform == 'win32':
                if hasattr(self, 'fd'):
                    os.close(self.fd)
                    os.unlink(self.lockfile)
            else:
                import fcntl  # @UnresolvedImport
                fcntl.lockf(self.fp, fcntl.LOCK_UN)
                if os.path.isfile(self.lockfile):
                    os.unlink(self.lockfile)
        except Exception, e:
            sys.exit(-1)

########NEW FILE########
__FILENAME__ = tr
import shared
import os

# This is used so that the translateText function can be used when we are in daemon mode and not using any QT functions.
class translateClass:
    def __init__(self, context, text):
        self.context = context
        self.text = text
    def arg(self,argument):
        if '%' in self.text:
            return translateClass(self.context, self.text.replace('%','',1)) # This doesn't actually do anything with the arguments because we don't have a UI in which to display this information anyway.
        else:
            return self.text

def _translate(context, text):
    return translateText(context, text)

def translateText(context, text):
    if not shared.safeConfigGetBoolean('bitmessagesettings', 'daemon'):
        try:
            from PyQt4 import QtCore, QtGui
        except Exception as err:
            print 'PyBitmessage requires PyQt unless you want to run it as a daemon and interact with it using the API. You can download PyQt from http://www.riverbankcomputing.com/software/pyqt/download   or by searching Google for \'PyQt Download\'. If you want to run in daemon mode, see https://bitmessage.org/wiki/Daemon'
            print 'Error message:', err
            os._exit(0)
        return QtGui.QApplication.translate(context, text)
    else:
        if '%' in text:
            return translateClass(context, text.replace('%','',1))
        else:
            return text
########NEW FILE########
