__FILENAME__ = DataUtil
import struct
import types
from io import BytesIO
from pynbt import NBTFile


def readBoolean(FileObject):
    return struct.unpack('?', FileObject.read(1))[0]


def readByte(FileObject):
    return struct.unpack('>b', FileObject.read(1))[0]


def readUnsignedByte(FileObject):
    return struct.unpack('>B', FileObject.read(1))[0]


def readShort(FileObject):
    return struct.unpack('>h', FileObject.read(2))[0]


def readUnsignedShort(FileObject):
    return struct.unpack('>H', FileObject.read(2))[0]


def readInt(FileObject):
    return struct.unpack('>i', FileObject.read(4))[0]


def readFloat(FileObject):
    return struct.unpack('>f', FileObject.read(4))[0]


def readLong(FileObject):
    return struct.unpack('>q', FileObject.read(8))[0]


def readDouble(FileObject):
    return struct.unpack('>d', FileObject.read(8))[0]


def readByteArray(FileObject, length):
    return struct.unpack(str(length) + "s", FileObject.read(length))[0]


def readString(FileObject):
    length = readShort(FileObject) * 2
    return unicode(FileObject.read(length), "utf-16be")


def sendBoolean(socket, value):
    assert type(value) is types.BooleanType, "value is not a boolean: %r" % value
    socket.send(struct.pack('?', value))


def sendByte(socket, value):
    socket.send(struct.pack('>b', value))


def sendUnsignedByte(socket, value):
    socket.send(struct.pack('>B', value))


def sendShort(socket, value):
    socket.send(struct.pack('>h', value))


def sendUnsignedShort(socket, value):
    socket.send(struct.pack('>H', value))


def sendInt(socket, value):
    assert type(value) is types.IntType, "value is not an integer: %r" % value
    socket.send(struct.pack('>i', value))


def sendFloat(socket, value):
    socket.send(struct.pack('>f', value))


def sendLong(socket, value):
    socket.send(struct.pack('>q', value))


def sendDouble(socket, value):
    socket.send(struct.pack('>d', value))


def sendString(socket, value):
    value = unicode(value).encode('utf-16be')
    socket.send(struct.pack('>h', len(value) / 2))
    socket.send(value)


def readEntityMetadata(FileObject):
    metadata = {}
    byte = readUnsignedByte(FileObject)
    while byte != 127:
        index = byte & 0x1F # Lower 5 bits
        ty = byte >> 5   # Upper 3 bits
        if ty == 0: val = readByte(FileObject)
        if ty == 1: val = readShort(FileObject)
        if ty == 2: val = readInt(FileObject)
        if ty == 3: val = readFloat(FileObject)
        if ty == 4:
            val = readString(FileObject)
        if ty == 5:
            val = {}
            val["id"] = readShort(FileObject)
            if (val["id"] != -1):
                val["count"] = readByte(FileObject)
                val["damage"] = readShort(FileObject)
                nbtDataLength = readShort(FileObject)
                if (nbtDataLength != -1):
                    val["NBT"] = NBTFile(BytesIO(readByteArray(FileObject, nbtDataLength)),
                        compression=NBTFile.Compression.GZIP)
        if ty == 6:
            val = []
            for i in range(3):
                val.append(readInt(FileObject))
        metadata[index] = (ty, val)
        byte = readUnsignedByte(FileObject)
    return metadata


def readSlotData(FileObject):
    BlockID = readShort(FileObject)
    if (BlockID != -1):
        ItemCount = readByte(FileObject)
        Damage = readShort(FileObject)
        MetadataLength = readShort(FileObject)
        if (MetadataLength != -1):
            ByteArray = readByteArray(FileObject, MetadataLength)
            NBTData = NBTFile(BytesIO(ByteArray), compression=NBTFile.Compression.GZIP)
            return {'BlockID': BlockID,
                    'ItemCount': ItemCount,
                    'Damage': Damage,
                    'Data': NBTData
                    }
        return {'BlockID': BlockID,
                'ItemCount': ItemCount,
                'Damage': Damage
                }
    return {'BlockID': -1,
            'ItemCount': 0
            }

########NEW FILE########
__FILENAME__ = NetworkManager
import socket
import PacketListenerManager
import urllib2
import traceback
import threading
import hashlib
import string
import unicodedata
import Utils
import sys
from networking import PacketSenderManager
from Crypto.Random import _UserFriendlyRNG
from Crypto.Util import asn1
from Crypto.PublicKey import RSA
from Crypto.Cipher import AES
from Crypto.Cipher import PKCS1_v1_5
from json import loads

EntityID = 0


class ServerConnection(threading.Thread):
    def __init__(self, pluginLoader, username, sessionID, server, port, options=None):
        threading.Thread.__init__(self)
        self.pluginLoader = pluginLoader
        self.options = options
        self.isConnected = False
        self.username = username
        self.sessionID = sessionID
        self.server = server
        self.port = port

    def disconnect(self, reason="Disconnected by user"):
        PacketSenderManager.sendFF(self.socket, reason)
        self.listener.kill = True
        self.socket.close()

    def setWindow(self, window):
        self.window = window

    def grabSocket(self):
        return self.socket

    def run(self):
        try:
            #Create the socket and fileobject
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.socket.connect(( self.server, self.port ))
            self.FileObject = self.socket.makefile()

            #Send out the handshake packet
            PacketSenderManager.sendHandshake(self.socket, self.username, self.server, self.port)

            #Receive the encryption packet id
            packetid = self.socket.recv(1)

            if (packetid == "\xFF"):
                print PacketListenerManager.handleFF(self.FileObject)
            #Sanity check the packet id
            assert packetid == "\xFD", "Server didn't respond back to handshake with proper packet!"

            #Parse the packet
            packetFD = PacketListenerManager.handleFD(self.FileObject)

            #Import the server's public key
            self.pubkey = RSA.importKey(packetFD['Public Key'])

            #Generate a 16 byte (128 bit) shared secret
            self.sharedSecret = _UserFriendlyRNG.get_random_bytes(16)

            #Authenticate the server from sessions.minecraft.net
            if (packetFD['ServerID'] != '-'):
                try:
                    #Grab the server id
                    sha1 = hashlib.sha1()
                    sha1.update(packetFD['ServerID'])
                    sha1.update(self.sharedSecret)
                    sha1.update(packetFD['Public Key'])
                    #lovely java style hex digest by barneygale
                    serverid = Utils.javaHexDigest(sha1)
                    #Open up the url with the appropriate get parameters
                    url = "http://session.minecraft.net/game/joinserver.jsp?user=" + self.username + "&sessionId=" + self.sessionID + "&serverId=" + serverid
                    response = urllib2.urlopen(url).read()

                    if (response != "OK"):
                        print "Response from sessions.minecraft.net wasn't OK, it was " + response
                        return False

                    #Success \o/ We can now begin sending our serverAddress to the server

                    #Instantiate our main packet listener
                    self.listener = PacketListener(self, self.socket, self.FileObject)
                    self.listener.setDaemon(True)
                    self.listener.start()

                    #Encrypt the verification token from earlier along with our shared secret with the server's rsa key
                    self.RSACipher = PKCS1_v1_5.new(self.pubkey)
                    encryptedSanityToken = self.RSACipher.encrypt(str(packetFD['Token']))
                    encryptedSharedSecret = self.RSACipher.encrypt(str(self.sharedSecret))

                    #Send out a a packet FC to the server
                    PacketSenderManager.sendFC(self.socket, encryptedSharedSecret, encryptedSanityToken)
                    self.pluginLoader.notify("onConnect")

                except Exception, e:
                    traceback.print_exc()
            else:
                print "Server is in offline mode"
                #Instantiate our main packet listener
                self.listener = PacketListener(self, self.socket, self.FileObject)
                self.listener.setDaemon(True)
                self.listener.start()

                #Encrypt the verification token from earlier along with our shared secret with the server's rsa key
                self.RSACipher = PKCS1_v1_5.new(self.pubkey)
                encryptedSanityToken = self.RSACipher.encrypt(str(packetFD['Token']))
                encryptedSharedSecret = self.RSACipher.encrypt(str(self.sharedSecret))

                #Send out a a packet FC to the server
                PacketSenderManager.sendFC(self.socket, encryptedSharedSecret, encryptedSanityToken)
                self.pluginLoader.notify("onConnect")
        except Exception, e:
            print "Connection to server failed"
            traceback.print_exc()
            sys.exit(1)


class EncryptedFileObjectHandler():
    def __init__(self, fileobject, cipher):
        self.fileobject = fileobject
        self.cipher = cipher
        self.length = 0

    def read(self, length):
        rawData = self.fileobject.read(length)
        self.length += length
        unencryptedData = self.cipher.decrypt(rawData)
        return unencryptedData

    def tell(self):
        return self.length


class EncryptedSocketObjectHandler():
    def __init__(self, socket, cipher):
        self.socket = socket
        self.cipher = cipher

    def send(self, serverAddress):
        self.socket.send(self.cipher.encrypt(serverAddress))

    def close(self):
        self.socket.close()


class PacketListener(threading.Thread):
    def __init__(self, connection, socket, FileObject):
        threading.Thread.__init__(self)
        self.connection = connection
        self.socket = socket
        self.FileObject = FileObject
        self.encryptedConnection = False
        self.kill = False

    def enableEncryption(self):
        #Create an AES cipher from the previously obtained public key
        self.cipher = AES.new(self.connection.sharedSecret, AES.MODE_CFB, IV=self.connection.sharedSecret)
        self.decipher = AES.new(self.connection.sharedSecret, AES.MODE_CFB, IV=self.connection.sharedSecret)

        self.rawsocket = self.socket
        self.connection.rawsocket = self.connection.socket
        self.socket = EncryptedSocketObjectHandler(self.rawsocket, self.cipher)
        self.connection.socket = self.socket

        self.rawFileObject = self.FileObject
        self.connection.rawFileObject = self.connection.FileObject
        self.FileObject = EncryptedFileObjectHandler(self.rawFileObject, self.decipher)
        self.connection.FileObject = self.FileObject

        self.encryptedConnection = True

    def run(self):
        while True:
            if (self.kill):
                break
            try:
                response = self.FileObject.read(1)
                if (response == ""):
                    continue
            except Exception, e:
                print "Ping timeout"
                sys.exit()
                break
            if (response == "\x00"):
                packet = PacketListenerManager.handle00(self.FileObject, self.socket)
            elif (response == "\x01"):
                packet = PacketListenerManager.handle01(self.FileObject)
                print "Logged in \o/ Received an entity id of " + str(packet['EntityID'])
            elif (response == "\x03"):
                packet = PacketListenerManager.handle03(self.FileObject)
                filtered_string = loads(packet['Message'])["text"]
                if not self.connection.options.disableAnsiColours:
                    filtered_string = Utils.translate_escapes(filtered_string)
                print filtered_string.decode("unicode-escape")

            elif (response == "\x04"):
                packet = PacketListenerManager.handle04(self.FileObject)
            elif (response == "\x05"):
                packet = PacketListenerManager.handle05(self.FileObject)
            elif (response == "\x06"):
                packet = PacketListenerManager.handle06(self.FileObject)
            elif (response == "\x07"):
                packet = PacketListenerManager.handle07(self.FileObject)
            elif (response == "\x08"):
                packet = PacketListenerManager.handle08(self.FileObject)
            elif (response == "\x09"):
                packet = PacketListenerManager.handle09(self.FileObject)
            elif (response == "\x0D"):
                packet = PacketListenerManager.handle0D(self.FileObject)
            elif (response == "\x10"):
                packet = PacketListenerManager.handle10(self.FileObject)
            elif (response == "\x11"):
                packet = PacketListenerManager.handle11(self.FileObject)
            elif (response == "\x12"):
                packet = PacketListenerManager.handle12(self.FileObject)
            elif (response == "\x14"):
                packet = PacketListenerManager.handle14(self.FileObject)
            elif (response == "\x15"):
                packet = PacketListenerManager.handle15(self.FileObject)
            elif (response == "\x16"):
                packet = PacketListenerManager.handle16(self.FileObject)
            elif (response == "\x17"):
                packet = PacketListenerManager.handle17(self.FileObject)
            elif (response == "\x18"):
                packet = PacketListenerManager.handle18(self.FileObject)
            elif (response == "\x19"):
                packet = PacketListenerManager.handle19(self.FileObject)
            elif (response == "\x1A"):
                packet = PacketListenerManager.handle1A(self.FileObject)
            elif (response == "\x1C"):
                packet = PacketListenerManager.handle1C(self.FileObject)
            elif (response == "\x1D"):
                packet = PacketListenerManager.handle1D(self.FileObject)
            elif (response == "\x1E"):
                packet = PacketListenerManager.handle1E(self.FileObject)
            elif (response == "\x1F"):
                packet = PacketListenerManager.handle1F(self.FileObject)
            elif (response == "\x20"):
                packet = PacketListenerManager.handle20(self.FileObject)
            elif (response == "\x21"):
                packet = PacketListenerManager.handle21(self.FileObject)
            elif (response == "\x22"):
                packet = PacketListenerManager.handle22(self.FileObject)
            elif (response == "\x23"):
                packet = PacketListenerManager.handle23(self.FileObject)
            elif (response == "\x26"):
                packet = PacketListenerManager.handle26(self.FileObject)
            elif (response == "\x27"):
                packet = PacketListenerManager.handle27(self.FileObject)
            elif (response == "\x28"):
                packet = PacketListenerManager.handle28(self.FileObject)
            elif (response == "\x29"):
                packet = PacketListenerManager.handle29(self.FileObject)
            elif (response == "\x2A"):
                packet = PacketListenerManager.handle2A(self.FileObject)
            elif (response == "\x2B"):
                packet = PacketListenerManager.handle2B(self.FileObject)
            elif (response == "\x2C"):
                packet = PacketListenerManager.handle2C(self.FileObject)
            elif (response == "\x33"):
                packet = PacketListenerManager.handle33(self.FileObject)
            elif (response == "\x34"):
                packet = PacketListenerManager.handle34(self.FileObject)
            elif (response == "\x35"):
                packet = PacketListenerManager.handle35(self.FileObject)
            elif (response == "\x36"):
                packet = PacketListenerManager.handle36(self.FileObject)
            elif (response == "\x37"):
                packet = PacketListenerManager.handle37(self.FileObject)
            elif (response == "\x38"):
                packet = PacketListenerManager.handle38(self.FileObject)
            elif (response == "\x3C"):
                packet = PacketListenerManager.handle3C(self.FileObject)
            elif (response == "\x3D"):
                packet = PacketListenerManager.handle3D(self.FileObject)
            elif (response == "\x3E"):
                packet = PacketListenerManager.handle3E(self.FileObject)
            elif (response == "\x3F"):
                packet = PacketListenerManager.handle3F(self.FileObject)
            elif (response == "\x46"):
                packet = PacketListenerManager.handle46(self.FileObject)
            elif (response == "\x47"):
                packet = PacketListenerManager.handle47(self.FileObject)
            elif (response == "\x64"):
                packet = PacketListenerManager.handle64(self.FileObject)
            elif (response == "\x65"):
                packet = PacketListenerManager.handle65(self.FileObject)
            elif (response == "\x67"):
                packet = PacketListenerManager.handle67(self.FileObject)
            elif (response == "\x68"):
                packet = PacketListenerManager.handle68(self.FileObject)
            elif (response == "\x69"):
                packet = PacketListenerManager.handle69(self.FileObject)
            elif (response == "\x6A"):
                packet = PacketListenerManager.handle6A(self.FileObject)
            elif (response == "\x6B"):
                packet = PacketListenerManager.handle6B(self.FileObject)
            elif (response == "\x82"):
                packet = PacketListenerManager.handle82(self.FileObject)
            elif (response == "\x83"):
                packet = PacketListenerManager.handle83(self.FileObject)
            elif (response == "\x84"):
                packet = PacketListenerManager.handle84(self.FileObject)
            elif (response == "\x85"):
                packet = PacketListenerManager.handle85(self.FileObject)
            elif (response == "\xC8"):
                packet = PacketListenerManager.handleC8(self.FileObject)
            elif (response == "\xC9"):
                packet = PacketListenerManager.handleC9(self.FileObject)
            elif (response == "\xCA"):
                packet = PacketListenerManager.handleCA(self.FileObject)
            elif (response == "\xCB"):
                packet = PacketListenerManager.handleCB(self.FileObject)
            elif (response == "\xCE"):
                packet = PacketListenerManager.handleCE(self.FileObject)
            elif (response == "\xCF"):
                packet = PacketListenerManager.handleCF(self.FileObject)
            elif (response == "\xD0"):
                packet = PacketListenerManager.handleD0(self.FileObject)
            elif (response == "\xD1"):
                packet = PacketListenerManager.handleD1(self.FileObject)
            elif (response == "\xFA"):
                packet = PacketListenerManager.handleFA(self.FileObject)
            elif (response == "\xFC"):
                packet = PacketListenerManager.handleFC(self.FileObject)
                if (not self.encryptedConnection):
                    self.enableEncryption()
                    self.connection.isConnected = True
                    PacketSenderManager.sendCD(self.socket, 0)
            elif (response == "\xFF"):
                packet = PacketListenerManager.handleFF(self.FileObject)
                print "Disconnected: " + packet['Reason']
                self.connection.disconnect()
                self.connection.pluginLoader.disablePlugins()
                sys.exit(1)
                break
            else:
                print "Protocol error: " + hex(ord(response))
                self.connection.disconnect("Protocol error, invalid packet: " + hex(ord(response)))
                self.connection.pluginLoader.disablePlugins()
                sys.exit(1)
                break

            # Invoke plugin listeners
            for listener in self.connection.pluginLoader.getPacketListeners():
                listener(response, packet)

########NEW FILE########
__FILENAME__ = PacketListenerManager
import DataUtil
import PacketSenderManager
from io import BytesIO
from pynbt import NBTFile

def handle00(FileObject, socket):
    KAid = DataUtil.readInt(FileObject)
    PacketSenderManager.send00(socket, KAid)


def handle01(FileObject):
    Eid = DataUtil.readInt(FileObject)
    world = DataUtil.readString(FileObject)
    mode = DataUtil.readByte(FileObject)
    dimension = DataUtil.readByte(FileObject)
    difficulty = DataUtil.readByte(FileObject)
    FileObject.read(1)
    maxplayers = DataUtil.readByte(FileObject)
    return {'EntityID': Eid,
            'World': world,
            'Mode': mode,
            'Dimension': dimension,
            'Difficulty': difficulty,
            'MaxPlayers': maxplayers
    }


def handle02(FileObject):
    message = DataUtil.readString(FileObject)
    return message


def handle03(FileObject):
    message = DataUtil.readString(FileObject)
    return {'Message': message}


def handle04(FileObject):
    time = DataUtil.readLong(FileObject)
    dayTime = DataUtil.readLong(FileObject)
    return {'Time': time,
            'DayTime': dayTime
    }


def handle05(FileObject):
    EntityID = DataUtil.readInt(FileObject)
    Slot = DataUtil.readShort(FileObject)
    Item = DataUtil.readSlotData(FileObject)
    return {'EntityID': EntityID,
            'Slot': Slot,
            'Item': Item
    }


def handle06(FileObject):
    x = DataUtil.readInt(FileObject)
    y = DataUtil.readInt(FileObject)
    z = DataUtil.readInt(FileObject)
    return {'x': x,
            'y': y,
            'z': z
    }


def handle07(FileObject):
    userID = DataUtil.readInt(FileObject)
    targetID = DataUtil.readInt(FileObject)
    mButton = DataUtil.readBoolean(FileObject)
    return {'userID': userID,
            'targetID': targetID,
            'mButton': mButton
    }


def handle08(FileObject):
    health = DataUtil.readFloat(FileObject)
    food = DataUtil.readShort(FileObject)
    saturation = DataUtil.readFloat(FileObject)
    return {'health': health,
            'food': food,
            'saturation': saturation
    }


def handle09(FileObject):
    dimension = DataUtil.readInt(FileObject)
    difficulty = DataUtil.readByte(FileObject)
    mode = DataUtil.readByte(FileObject)
    height = DataUtil.readShort(FileObject)
    world = DataUtil.readString(FileObject)
    return {'Dimension': dimension,
            'Difficulty': difficulty,
            'Mode': mode,
            'Height': height,
            'World': world
    }


def handle0D(FileObject):
    x = DataUtil.readDouble(FileObject)
    stance = DataUtil.readDouble(FileObject)
    y = DataUtil.readDouble(FileObject)
    z = DataUtil.readDouble(FileObject)
    yaw = DataUtil.readFloat(FileObject)
    pitch = DataUtil.readFloat(FileObject)
    onGround = DataUtil.readBoolean(FileObject)
    return {'x': x,
            'stance': stance,
            'y': y,
            'z': z,
            'yaw': yaw,
            'pitch': pitch,
            'onGround': onGround
    }


def handle10(FileObject):
    slotID = DataUtil.readShort(FileObject)
    return {'SlotID': slotID}


def handle11(FileObject):
    EntityID = DataUtil.readInt(FileObject)
    FileObject.read(1) #Unused
    x = DataUtil.readInt(FileObject)
    y = DataUtil.readByte(FileObject)
    z = DataUtil.readInt(FileObject)
    return {'EntityID': EntityID,
            'x': x,
            'y': y,
            'z': z
    }


def handle12(FileObject):
    EntityID = DataUtil.readInt(FileObject)
    Animation = DataUtil.readByte(FileObject)
    return {'EntityID': EntityID,
            'AnimationID': Animation
    }


def handle14(FileObject):
    EntityID = DataUtil.readInt(FileObject)
    PlayerName = DataUtil.readString(FileObject)
    x = DataUtil.readInt(FileObject)
    y = DataUtil.readInt(FileObject)
    z = DataUtil.readInt(FileObject)
    yaw = DataUtil.readFloat(FileObject)
    pitch = DataUtil.readFloat(FileObject)
    curItem = DataUtil.readShort(FileObject)
    metadata = DataUtil.readEntityMetadata(FileObject)
    toReturn = {'EntityID': EntityID,
                'Player Name': PlayerName,
                'x': x,
                'y': y,
                'z': z,
                'yaw': yaw,
                'pitch': pitch,
                'curItem': curItem,
                'Metadata': metadata
    }
    return toReturn


def handle15(FileObject):
    EntityID = DataUtil.readInt(FileObject)
    ItemID = DataUtil.readShort(FileObject)
    if (ItemID != -1):
        Count = DataUtil.readByte(FileObject)
        Damage = DataUtil.readShort(FileObject)
        ArrayLength = DataUtil.readShort(FileObject)
        if (ArrayLength != -1):
            Array = FileObject.read(ArrayLength) #TODO: find out what this does and do stuff accrodingly
    x = DataUtil.readInt(FileObject)
    y = DataUtil.readInt(FileObject)
    z = DataUtil.readInt(FileObject)
    Rotation = DataUtil.readByte(FileObject)
    Pitch = DataUtil.readByte(FileObject)
    Roll = DataUtil.readByte(FileObject)
    toReturn = {'EntityID': EntityID,
                'ItemID': ItemID,
                'x': x,
                'y': y,
                'z': z,
                'Rotation': Rotation,
                'Pitch': Pitch,
                'Roll': Roll
    }
    if (ItemID != -1):
        toReturn['Count'] = Count
        toReturn['Damage'] = Damage
    return toReturn


def handle16(FileObject):
    CollectedID = DataUtil.readInt(FileObject)
    CollectorID = DataUtil.readInt(FileObject)
    return {'CollectedID': CollectedID,
            'CollectorID': CollectorID
    }


def handle17(FileObject):
    EntityID = DataUtil.readInt(FileObject)
    Type = DataUtil.readByte(FileObject)
    x = DataUtil.readInt(FileObject)
    y = DataUtil.readInt(FileObject)
    z = DataUtil.readInt(FileObject)
    yaw = DataUtil.readByte(FileObject)
    pitch = DataUtil.readByte(FileObject)
    data = DataUtil.readInt(FileObject)
    if (data > 0):
        SpeedX = DataUtil.readShort(FileObject)
        SpeedY = DataUtil.readShort(FileObject)
        SpeedZ = DataUtil.readShort(FileObject)
        return {'EntityID': EntityID,
                'Type': Type,
                'x': x,
                'y': y,
                'z': z,
                'yaw': yaw,
                'pitch': pitch,
                'SpeedX': SpeedX,
                'SpeedY': SpeedY,
                'SpeedZ': SpeedZ
        }
    else:
        return {'EntityID': EntityID,
                'Type': Type,
                'x': x,
                'y': y,
                'z': z,
                'yaw': yaw,
                'pitch': pitch
        }


def handle18(FileObject):
    EntityID = DataUtil.readInt(FileObject)
    Type = DataUtil.readByte(FileObject)
    x = DataUtil.readInt(FileObject)
    y = DataUtil.readInt(FileObject)
    z = DataUtil.readInt(FileObject)
    Yaw = DataUtil.readByte(FileObject)
    Pitch = DataUtil.readByte(FileObject)
    HeadYaw = DataUtil.readByte(FileObject)
    VelocityX = DataUtil.readShort(FileObject)
    VelocityY = DataUtil.readShort(FileObject)
    VelocityZ = DataUtil.readShort(FileObject)
    metadata = DataUtil.readEntityMetadata(FileObject)

    return {'EntityID': EntityID,
            'Type': Type,
            'x': x,
            'y': y,
            'z': z,
            'Yaw': Yaw,
            'Pitch': Pitch,
            'HeadYaw': HeadYaw,
            'Metadata': metadata,
            'VelocityX': VelocityX,
            'VelocityY': VelocityY,
            'VelocityZ': VelocityZ
    }


def handle19(FileObject):
    EntityID = DataUtil.readInt(FileObject)
    Title = DataUtil.readString(FileObject)
    x = DataUtil.readInt(FileObject)
    y = DataUtil.readInt(FileObject)
    z = DataUtil.readInt(FileObject)
    Direction = DataUtil.readInt(FileObject)
    return {'EntityID': EntityID,
            'Title': Title,
            'x': x,
            'y': y,
            'z': z,
            'Direction': Direction
    }


def handle1A(FileObject):
    EntityID = DataUtil.readInt(FileObject)
    x = DataUtil.readInt(FileObject)
    y = DataUtil.readInt(FileObject)
    z = DataUtil.readInt(FileObject)
    Count = DataUtil.readShort(FileObject)
    return {'EntityID': EntityID,
            'x': x,
            'y': y,
            'z': z,
            'Count': Count
    }


def handle1C(FileObject):
    EntityID = DataUtil.readInt(FileObject)
    VelocityX = DataUtil.readShort(FileObject)
    VelocityY = DataUtil.readShort(FileObject)
    VelocityZ = DataUtil.readShort(FileObject)
    return {'EntityID': EntityID,
            'VelocityX': VelocityX,
            'VelocityY': VelocityY,
            'VelocityZ': VelocityZ
    }


def handle1D(FileObject):
    EntityArrayLength = DataUtil.readByte(FileObject)
    Entities = []
    for i in range(EntityArrayLength):
        Entities.append(DataUtil.readInt(FileObject))
    return Entities


def handle1E(FileObject):
    EntityID = DataUtil.readInt(FileObject)
    return EntityID


def handle1F(FileObject):
    EntityID = DataUtil.readInt(FileObject)
    x = DataUtil.readByte(FileObject)
    y = DataUtil.readByte(FileObject)
    z = DataUtil.readByte(FileObject)
    return {'EntityID': EntityID,
            'x': x,
            'y': y,
            'z': z
    }


def handle20(FileObject):
    EntityID = DataUtil.readInt(FileObject)
    Yaw = DataUtil.readByte(FileObject)
    Pitch = DataUtil.readByte(FileObject)
    return {'EntityID': EntityID,
            'Yaw': Yaw,
            'Pitch': Pitch
    }


def handle21(FileObject):
    EntityID = DataUtil.readInt(FileObject)
    x = DataUtil.readByte(FileObject)
    y = DataUtil.readByte(FileObject)
    z = DataUtil.readByte(FileObject)
    Yaw = DataUtil.readByte(FileObject)
    Pitch = DataUtil.readByte(FileObject)
    return {'EntityID': EntityID,
            'x': x,
            'y': y,
            'z': z,
            'Yaw': Yaw,
            'Pitch': Pitch
    }


def handle22(FileObject):
    EntityID = DataUtil.readInt(FileObject)
    x = DataUtil.readInt(FileObject)
    y = DataUtil.readInt(FileObject)
    z = DataUtil.readInt(FileObject)
    Yaw = DataUtil.readByte(FileObject)
    Pitch = DataUtil.readByte(FileObject)
    return {'EntityID': EntityID,
            'x': x,
            'y': y,
            'z': z,
            'Yaw': Yaw,
            'Pitch': Pitch
    }


def handle23(FileObject):
    EntityID = DataUtil.readInt(FileObject)
    HeadYaw = DataUtil.readByte(FileObject)
    return {'EntityID': EntityID,
            'HeadYaw': HeadYaw
    }


def handle26(FileObject):
    EntityID = DataUtil.readInt(FileObject)
    Status = DataUtil.readByte(FileObject)
    return {'EntityID': EntityID,
            'Status': Status
    }


def handle27(FileObject):
    EntityID = DataUtil.readInt(FileObject)
    VehicleID = DataUtil.readInt(FileObject)
    Leash = DataUtil.readBoolean(FileObject)
    return {'EntityID': EntityID,
            'VehicleID': VehicleID,
            'Leash': Leash
    }


def handle28(FileObject):
    EntityID = DataUtil.readInt(FileObject)
    metadata = DataUtil.readEntityMetadata(FileObject)
    return {'EntityID': EntityID,
            'MetaData': metadata
    }


def handle29(FileObject):
    EntityID = DataUtil.readInt(FileObject)
    EffectID = DataUtil.readByte(FileObject)
    Amplifier = DataUtil.readByte(FileObject)
    Duration = DataUtil.readShort(FileObject)
    return {'EntityID': EntityID,
            'EffectID': EffectID,
            'Amplifier': Amplifier,
            'Duration': Duration
    }


def handle2A(FileObject):
    EntityID = DataUtil.readInt(FileObject)
    EffectID = DataUtil.readByte(FileObject)
    return {'EntityID': EntityID,
            'EffectID': EffectID
    }


def handle2B(FileObject):
    ExperienceBar = DataUtil.readFloat(FileObject)
    Level = DataUtil.readShort(FileObject)
    TotalExp = DataUtil.readShort(FileObject)
    return {'ExpBar': ExperienceBar,
            'Level': Level,
            'TotalExp': TotalExp
    }


def handle2C(FileObject):
    EntityID = DataUtil.readInt(FileObject)
    PropertiesCount = DataUtil.readInt(FileObject)
    Properties = {}
    for i in range(PropertiesCount):
        key = DataUtil.readString(FileObject)
        value = DataUtil.readDouble(FileObject)
        Properties[key] = value
        len = DataUtil.readShort(FileObject)
        for x in range(len):
            uuid_msb = DataUtil.readLong(FileObject)
            uuid_lsb = DataUtil.readLong(FileObject)
            amount = DataUtil.readDouble(FileObject)
            operation = DataUtil.readByte(FileObject)
    return {'EntityID': EntityID,
            'Properties': Properties
    }


def handle33(FileObject):
    X = DataUtil.readInt(FileObject)
    Z = DataUtil.readInt(FileObject)
    GroundUpContinuous = DataUtil.readBoolean(FileObject)
    PrimaryBitMap = DataUtil.readShort(FileObject)
    AddBitMap = DataUtil.readShort(FileObject)
    CompressedSize = DataUtil.readInt(FileObject)
    RawData = FileObject.read(CompressedSize)
    return {'x': X,
            'z': Z,
            'GroundUpContinuous': GroundUpContinuous,
            'PrimaryBitMap': PrimaryBitMap,
            'AddBitMap': AddBitMap,
            'RawData': RawData
    }


def handle34(FileObject):
    ChunkX = DataUtil.readInt(FileObject)
    ChunkZ = DataUtil.readInt(FileObject)
    AffectedBlocks = DataUtil.readShort(FileObject)
    DataSize = DataUtil.readInt(FileObject)
    FileObject.read(DataSize) #not going to be using this until I know how to.
    return {'ChunkX': ChunkX,
            'ChunkZ': ChunkZ,
            'AffectedBlocks': AffectedBlocks
    }


def handle35(FileObject):
    X = DataUtil.readInt(FileObject)
    Y = DataUtil.readByte(FileObject)
    Z = DataUtil.readInt(FileObject)
    BlockType = DataUtil.readShort(FileObject)
    BlockMetaData = DataUtil.readByte(FileObject)
    return {'x': X,
            'y': Y,
            'z': Z,
            'BlockType': BlockType,
            'MetaData': BlockMetaData
    }


def handle36(FileObject):
    X = DataUtil.readInt(FileObject)
    Y = DataUtil.readShort(FileObject)
    Z = DataUtil.readInt(FileObject)
    Byte1 = DataUtil.readByte(FileObject)
    Byte2 = DataUtil.readByte(FileObject)
    BlockID = DataUtil.readShort(FileObject)
    return {'x': X,
            'y': Y,
            'z': Z,
            'Byte1': Byte1,
            'Byte2': Byte2,
            'BlockID': BlockID
    }


def handle37(FileObject):
    #int - EntityID
    EntityID = DataUtil.readInt(FileObject)

    #int - X cord
    x = DataUtil.readInt(FileObject)

    #int - Y cord
    y = DataUtil.readInt(FileObject)

    #int - Z cord
    z = DataUtil.readInt(FileObject)

    #byte - Stage
    DestroyedStage = DataUtil.readByte(FileObject)
    return {'EntityID': EntityID,
            'x': x,
            'y': y,
            'z': z,
            'DestroyedStage': DestroyedStage
    }


def handle38(FileObject):
    #short - number of chunks
    ChunkCount = DataUtil.readShort(FileObject)

    #int - chunk data length
    ChunkDataLength = DataUtil.readInt(FileObject)
    SkyLightSent = DataUtil.readBoolean(FileObject)
    RawData = FileObject.read(ChunkDataLength)

    metadata = []
    for i in range(ChunkCount):
        ChunkX = DataUtil.readInt(FileObject)
        ChunkZ = DataUtil.readInt(FileObject)
        PrimaryBitMap = DataUtil.readUnsignedShort(FileObject)
        AddBitMap = DataUtil.readUnsignedShort(FileObject)
        metadata.append({'x': ChunkX,
                         'z': ChunkZ,
                         'PrimaryBitMap': PrimaryBitMap,
                         'AddBitMap': AddBitMap
                         })

    return {'ChunkCount': ChunkCount,
            'SkyLightSent': SkyLightSent,
            'RawData': RawData,
            'ChunkMeta': metadata
    }


def handle3C(FileObject):
    X = DataUtil.readDouble(FileObject)
    Y = DataUtil.readDouble(FileObject)
    Z = DataUtil.readDouble(FileObject)
    Radius = DataUtil.readFloat(FileObject)
    RecordCount = DataUtil.readInt(FileObject)
    AffectedBlocks = []
    for i in range((RecordCount * 3)):
        x = DataUtil.readByte(FileObject)
        y = DataUtil.readByte(FileObject)
        z = DataUtil.readByte(FileObject)
        AffectedBlocks.append({'x': x, 'y': y, 'z': z})
        #---Unknown what these floats do
    FileObject.read(4)
    FileObject.read(4)
    FileObject.read(4)
    #---
    return {'x': X,
            'y': Y,
            'z': Z,
            'Raidus': Radius,
            'AffectedBlocks': AffectedBlocks
    }


def handle3D(FileObject):
    EffectID = DataUtil.readInt(FileObject)
    X = DataUtil.readInt(FileObject)
    Y = DataUtil.readByte(FileObject)
    Z = DataUtil.readInt(FileObject)
    Data = DataUtil.readInt(FileObject)
    NoVolDecrease = DataUtil.readBoolean(FileObject)
    return {'EffectID': EffectID,
            'X': X,
            'Y': Y,
            'Z': Z,
            'Data': Data,
            'NoVolumeDecrease': NoVolDecrease
    }


def handle3E(FileObject):
    Sound = DataUtil.readString(FileObject)
    x = DataUtil.readInt(FileObject)
    y = DataUtil.readInt(FileObject)
    z = DataUtil.readInt(FileObject)
    Volume = DataUtil.readFloat(FileObject)
    Pitch = DataUtil.readByte(FileObject)
    return {'Sound': Sound,
            'x': x,
            'y': y,
            'z': z,
            'Volume': Volume,
            'Pitch': Pitch
    }
    
def handle3F(FileObject):
    name = DataUtil.readString(FileObject)
    x = DataUtil.readFloat(FileObject)
    y = DataUtil.readFloat(FileObject)
    z = DataUtil.readFloat(FileObject)
    offsetx = DataUtil.readFloat(FileObject)
    offsety = DataUtil.readFloat(FileObject)
    offsetz = DataUtil.readFloat(FileObject)
    speed = DataUtil.readFloat(FileObject)
    num = DataUtil.readInt(FileObject)
    return {'Name' : name,
            'x' : x,
            'y' : y,
            'z' : z,
            'Offset x' : offsetx,
            'Offset y' : offsety,
            'Offset z' : offsetz,
            'Speed' : speed,
            'Number' : num
    }


def handle46(FileObject):
    Reason = DataUtil.readByte(FileObject)
    GameMode = DataUtil.readByte(FileObject)
    return {'Reason': Reason,
            'GameMode': GameMode
    }


def handle47(FileObject):
    EntityID = DataUtil.readInt(FileObject)
    FileObject.read(1) #Boolean don't do nothing
    x = DataUtil.readInt(FileObject)
    y = DataUtil.readInt(FileObject)
    z = DataUtil.readInt(FileObject)
    return {'EntityID': EntityID,
            'x': x,
            'y': y,
            'z': z
    }


def handle64(FileObject):
    WindowID = DataUtil.readByte(FileObject)
    InventoryType = DataUtil.readByte(FileObject)
    WindowTitle = DataUtil.readString(FileObject)
    NumberOfSlots = DataUtil.readByte(FileObject)
    UseName = DataUtil.readBoolean(FileObject)
    toReturn = {'WindowID': WindowID,
            'InventoryType': InventoryType,
            'WindowTitle': WindowTitle,
            'NumberOfSlots': NumberOfSlots,
            'UseName': UseName
    }
    if InventoryType == 11:
        toReturn['EntityId'] = DataUtil.readInt(FileObject)
    return toReturn


def handle65(FileObject):
    WindowID = DataUtil.readByte(FileObject)
    return WindowID


def handle67(FileObject):
    WindowID = DataUtil.readByte(FileObject)
    Slot = DataUtil.readShort(FileObject)
    SlotData = DataUtil.readSlotData(FileObject)
    return {'WindowID': WindowID,
            'Slot': Slot,
            'SlotData': SlotData
    }


def handle68(FileObject):
    WindowID = DataUtil.readByte(FileObject)
    Count = DataUtil.readShort(FileObject)
    Slots = []
    for i in range(Count):
        SlotData = DataUtil.readSlotData(FileObject)
        Slots.append(SlotData)
    return {'WindowID': WindowID,
            'Count': Count,
            'Slots': Slots
    }


def handle69(FileObject):
    WindowID = DataUtil.readByte(FileObject)
    Property = DataUtil.readShort(FileObject)
    Value = DataUtil.readShort(FileObject)
    return {'WindowID': WindowID,
            'Property': Property,
            'Value': Value
    }


def handle6A(FileObject):
    WindowID = DataUtil.readByte(FileObject)
    ActionType = DataUtil.readShort(FileObject)
    Accepted = DataUtil.readBoolean(FileObject)
    return {'WindowID': WindowID,
            'ActionType': ActionType,
            'Accepted': Accepted
    }


def handle6B(FileObject):
    Slot = DataUtil.readShort(FileObject)
    ClickedItem = DataUtil.readSlotData(FileObject)
    return {'Slot': Slot,
            'ClickedItem': ClickedItem
    }


def handle82(FileObject):
    X = DataUtil.readInt(FileObject)
    Y = DataUtil.readShort(FileObject)
    Z = DataUtil.readInt(FileObject)
    Line1 = DataUtil.readString(FileObject)
    Line2 = DataUtil.readString(FileObject)
    Line3 = DataUtil.readString(FileObject)
    Line4 = DataUtil.readString(FileObject)
    return {'x': X,
            'y': Y,
            'z': Z,
            'Line1': Line1,
            'Line2': Line2,
            'Line3': Line3,
            'Line4': Line4
    }


def handle83(FileObject):
    ItemType = DataUtil.readShort(FileObject)
    ItemID = DataUtil.readShort(FileObject)
    TextLength = DataUtil.readShort(FileObject)
    Text = DataUtil.readByteArray(FileObject, TextLength)
    return {'ItemType': ItemType,
            'ItemID': ItemID,
            'Text': Text
    }


def handle84(FileObject):
    X = DataUtil.readInt(FileObject)
    Y = DataUtil.readShort(FileObject)
    Z = DataUtil.readInt(FileObject)
    Action = DataUtil.readByte(FileObject)
    DataLength = DataUtil.readShort(FileObject)
    if (DataLength != -1):
        ByteArray = DataUtil.readByteArray(FileObject, DataLength)
        NBTData = NBTFile(BytesIO(ByteArray), compression=NBTFile.Compression.GZIP)
        return {'x': X,
                'y': Y,
                'z': Z,
                'Action': Action,
                'NBTData': NBTData
        }
    return {'x': X,
            'y': Y,
            'z': Z,
            'Action': Action
    }


def handle85(FileObject):
    EntityID = DataUtil.readByte(FileObject)
    X = DataUtil.readInt(FileObject)
    Y = DataUtil.readInt(FileObject)
    Z = DataUtil.readInt(FileObject)
    return {'EntityID': EntityID,
            'x': X,
            'y': Y,
            'z': Z}


def handleC8(FileObject):
    StatID = DataUtil.readInt(FileObject)
    Amount = DataUtil.readInt(FileObject)
    return {'StatID': StatID,
            'Amount': Amount
    }


def handleC9(FileObject):
    PlayerName = DataUtil.readString(FileObject)
    Online = DataUtil.readBoolean(FileObject)
    Ping = DataUtil.readShort(FileObject)
    return {'PlayerName': PlayerName,
            'Online': Online,
            'Ping': Ping
    }


def handleCA(FileObject):
    #byte - flags
    Flags = DataUtil.readByte(FileObject)

    #byte - fly speed
    FlySpeed = DataUtil.readFloat(FileObject)

    #byte - walk speed
    WalkSpeed = DataUtil.readFloat(FileObject)
    return {'Flags': Flags,
            'Fly Speed': FlySpeed,
            'Walk Speed': WalkSpeed
    }

def handleCB(FileObject):
    text = DataUtil.readString(FileObject)
    return {'Text': text}
    
def handleCE(FileObject):
    name = DataUtil.readString(FileObject)
    display_text = DataUtil.readString(FileObject)
    create_or_remove = DataUtil.readBoolean(FileObject)
    return {'Name' : name,
            'Display Name' : display_text,
            'Remove' : create_or_remove
    }
    
def handleCF(FileObject):
    name = DataUtil.readString(FileObject)
    remove = DataUtil.readBoolean(FileObject)
    score_name = DataUtil.readString(FileObject)
    value = DataUtil.readInt(FileObject)
    return {'Item Name' : name,
            'Remove' : remove,
            'Score Name' : score_name,
            'Value' : value
    }

def handleD0(FileObject):
    position = DataUtil.readByte(FileObject)
    score = DataUtil.readString(FileObject)
    return {'Position' : position,
            'Score' : score
    }
    
def handleD1(FileObject):
    team = DataUtil.readString(FileObject)
    mode = DataUtil.readByte(FileObject)
    toReturn = {'Team' : team, 'Mode' : mode}
    if mode == 0 or mode == 2:
        toReturn['Display Name'] = DataUtil.readString(FileObject)
        toReturn['Prefix'] = DataUtil.readString(FileObject)
        toReturn['Suffix'] = DataUtil.readString(FileObject)
        toReturn['FriendlyFire'] = DataUtil.readByte(FileObject)
    if mode == 0 or mode == 3 or mode == 4:
        count = DataUtil.readShort(FileObject)
        players = []
        for i in range(count):
            players.append(DataUtil.readString(FileObject))
    return toReturn


def handleFA(FileObject):
    Channel = DataUtil.readString(FileObject)
    length = DataUtil.readShort(FileObject)
    message = DataUtil.readByteArray(FileObject, length)
    return {'Channel': Channel,
            'message': message
    }


def handleFC(FileObject):
    #short - shared secret length
    secretLength = DataUtil.readShort(FileObject)

    sharedSecret = DataUtil.readByteArray(FileObject, secretLength) #ignore this data, it doesn't matter

    #short - token length
    length = DataUtil.readShort(FileObject)

    token = DataUtil.readByteArray(FileObject, length) #ignore this data, it doesn't matter

    return {'Secret Length': secretLength,
            'Shared Secret': sharedSecret,
            'Token Length': length,
            'Token': token
    }


def handleFD(FileObject):
    #string - server id
    serverid = DataUtil.readString(FileObject)

    #short - pub key length
    length = DataUtil.readShort(FileObject)

    #byte array - pub key
    pubkey = DataUtil.readByteArray(FileObject, length)

    #short - token length
    length = DataUtil.readShort(FileObject)

    #byte array - token
    token = DataUtil.readByteArray(FileObject, length)

    return {'ServerID': serverid,
            'Public Key': pubkey,
            'Token': token
    }


def handleFF(FileObject):
    Reason = DataUtil.readString(FileObject)
    return {'Reason': Reason}

########NEW FILE########
__FILENAME__ = PacketSenderManager
import DataUtil

def send00(socket, KAid):
    #packet id
    socket.send("\x00")

    #int - keep alive id
    DataUtil.sendInt(socket, KAid)


def sendHandshake(socket, username, host, port):
    #packet id
    socket.send("\x02")

    #byte - protocol version
    DataUtil.sendByte(socket, 78)

    #string - username
    DataUtil.sendString(socket, username)

    #string - server host
    DataUtil.sendString(socket, host)

    #int - server port
    DataUtil.sendInt(socket, port)


def send03(socket, message):
    #packet id
    socket.send("\x03")

    #-----string - message-----#
    DataUtil.sendString(socket, message)


def sendCD(socket, payload):
    #packet id
    socket.send("\xCD")

    #payload - byte
    DataUtil.sendByte(socket, payload)


def sendFC(socket, secret, token):
    #packet id
    socket.send("\xFC")

    #shared secret
    DataUtil.sendShort(socket, secret.__len__()) #length
    socket.send(secret)

    #token
    DataUtil.sendShort(socket, token.__len__())
    socket.send(token)


def sendFF(socket, reason):
    #string - disconnect reason
    DataUtil.sendString(socket, reason)

########NEW FILE########
__FILENAME__ = pluginloader
import os
import imp

class PluginLoader():
    path = ""
    plugins = {}
    listeners = []

    def __init__(self, path):
        self.path = path

    def loadPlugins(self, parser):
        for item in os.listdir(self.path):
            split = os.path.splitext(item)
            if (split[1] == '.py'):
                name = split[0]
                full_name = split[0].replace(os.path.sep, '.')
                m = imp.load_module(full_name, *imp.find_module(name, [self.path]))

                pluginClass = None
                try:
                    pluginClass = getattr(m, name)()
                    self.plugins[name] = pluginClass
                    try:
                        pluginClass.onEnable(parser, self)
                    except AttributeError:
                        pass
                    try:
                        self.listeners.append(pluginClass.packetReceive)
                    except AttributeError:
                        pass
                except AttributeError:
                    print "Plugin " + name + " is malformed"

    def disablePlugins(self):
        for plugin in self.plugins.values():
            try:
                plugin.onDisable()
            except AttributeError:
                pass

    def notifyOptions(self, options):
        for plugin in self.plugins.values():
            try:
                plugin.optionsParsed(options)
            except AttributeError:
                pass

    def notify(self, methodName):
        for plugin in self.plugins.values():
            try:
                getattr(plugin, methodName)()
            except AttributeError:
                pass

    def getPlugins(self):
        return self.plugins.values()

    def getPlugin(self, name):
        return self.plugins[name]

    def getPacketListeners(self):
        return self.listeners

########NEW FILE########
__FILENAME__ = IRC
class IRC:
    options = None
    writeFile = None

    def onEnable(self, parser, pluginloader):
        parser.add_option("-q", "--irc-out-file", dest="ircDump", default="ircdump.txt",
            help="file to dump messages to")

    def onDisable(self):
        if (self.writeFile != None):
            self.writeFile.close()

    def optionsParsed(self, parsedOptions):
        self.options = parsedOptions
        if (self.options.ircDump):
            self.writeFile = open(self.options.filename, 'w')

########NEW FILE########
__FILENAME__ = PacketDumper
import string
import copy
import base64


class PacketDumper:
    options = None
    writeFile = None

    def onEnable(self, parser, pluginloader):
        parser.add_option("-d", "--dump-packets",
                          action="store_true", dest="dumpPackets", default=False,
                          help="run with this argument to dump packets")

        parser.add_option("-o", "--out-file", dest="filename", default="dump.txt",
                          help="file to dump packets to")

    def onDisable(self):
        if self.writeFile is not None:
            self.writeFile.close()

    def optionsParsed(self, parsedOptions):
        self.options = parsedOptions
        if self.options.dumpPackets:
            self.writeFile = open(self.options.filename, 'w')

    def packetReceive(self, packetID, receivedPacket):
        packet = copy.deepcopy(receivedPacket)
        if self.writeFile is not None:
            if packetID == "\x33" or packetID == "\x38":
                packet['Data'] = base64.b64encode(packet['RawData'])
                del packet['RawData']
            if packetID == "\x03":
                packet['Message'] = filter(lambda x: x in string.printable, packet['Message'])
            self.writeFile.write(hex(ord(packetID)) + " : " + str(packet) + '\n')

########NEW FILE########
__FILENAME__ = nbt
#!/usr/bin/env python
# -*- coding: utf8 -*-
"""
Implements reading & writing for the Minecraft Named Binary Tag (NBT) format,
created by Markus Petersson.

.. moduleauthor:: Tyler Kennedy <tk@tkte.ch>
"""
import gzip
from struct import unpack, pack


class BaseTag(object):
    def __init__(self, value, name=None):
        self.name = name
        self.value = value

    @staticmethod
    def _read_utf8(read):
        """Reads a length-prefixed UTF-8 string."""
        name_length = read('H', 2)[0]
        return read.io.read(name_length).decode('utf-8')

    @staticmethod
    def _write_utf8(write, value):
        """Writes a length-prefixed UTF-8 string."""
        write('h', len(value))
        write.io.write(value.encode('UTF-8'))

    @classmethod
    def read(cls, read, has_name=True):
        """
        Read the tag in using the reader `rd`.
        If `has_name` is `False`, skip reading the tag name.
        """
        name = cls._read_utf8(read) if has_name else None

        if cls is TAG_Compound:
            # A TAG_Compound is almost identical to Python's native dict()
            # object, or a Java HashMap.
            final = {}
            while True:
                # Find the type of each tag in a compound in turn.
                tag = read('b', 1)[0]
                if tag == 0:
                    # A tag of 0 means we've reached TAG_End, used to terminate
                    # a TAG_Compound.
                    break
                    # We read in each tag in turn, using its name as the key in
                # the dict (Since a compound cannot have repeating names,
                # this works fine).
                tmp = _tags[tag].read(read)
                final[tmp.name] = tmp
            return cls(final, name=name)
        elif cls is TAG_List:
            # A TAG_List is a very simple homogeneous array, similar to
            # Python's native list() object, but restricted to a single type.
            tag_type, length = read('bi', 5)
            tag_read = _tags[tag_type].read
            return cls(
                _tags[tag_type],
                [tag_read(read, has_name=False) for x in range(0, length)],
                name=name
            )
        elif cls is TAG_String:
            # A simple length-prefixed UTF-8 string.
            value = cls._read_utf8(read)
            return cls(value, name=name)
        elif cls is TAG_Byte_Array:
            # A simple array of (signed) bytes.
            length = read('i', 4)[0]
            return cls(read('{0}b'.format(length), length), name=name)
        elif cls is TAG_Int_Array:
            # A simple array of (signed) 4-byte integers.
            length = read('i', 4)[0]
            return cls(read('{0}i'.format(length), length * 4), name=name)
        elif cls is TAG_Byte:
            # A single (signed) byte.
            return cls(read('b', 1)[0], name=name)
        elif cls is TAG_Short:
            # A single (signed) short.
            return cls(read('h', 2)[0], name=name)
        elif cls is TAG_Int:
            # A signed (signed) 4-byte int.
            return cls(read('i', 4)[0], name=name)
        elif cls is TAG_Long:
            # A single (signed) 8-byte long.
            return cls(read('q', 8)[0], name=name)
        elif cls is TAG_Float:
            # A single single-precision floating point value.
            return cls(read('f', 4)[0], name=name)
        elif cls is TAG_Double:
            # A single double-precision floating point value.
            return cls(read('d', 8)[0], name=name)

    def write(self, write):
        # Only write the name TAG_String if our name is not `None`.
        # If you want a blank name, use ''.
        if self.name is not None:
            if isinstance(self, NBTFile):
                write('b', 0x0A)
            else:
                write('b', _tags.index(self.__class__))
            self._write_utf8(write, self.name)
        if isinstance(self, TAG_List):
            write('bi', _tags.index(self.type_), len(self.value))
            for item in self.value:
                # If our list item isn't of type self._type, convert
                # it before writing.
                if not isinstance(item, self.type_):
                    item = self.type_(item)
                item.write(write)
        elif isinstance(self, TAG_Compound):
            for v in self.value.values():
                v.write(write)
                # A tag of type 0 (TAg_End) terminates a TAG_Compound.
            write('b', 0)
        elif isinstance(self, TAG_String):
            self._write_utf8(write, self.value)
        elif isinstance(self, TAG_Int_Array):
            l = len(self.value)
            write('i{0}i'.format(l), l, *self.value)
        elif isinstance(self, TAG_Byte_Array):
            l = len(self.value)
            write('i{0}b'.format(l), l, *self.value)
        elif isinstance(self, TAG_Byte):
            write('b', self.value)
        elif isinstance(self, TAG_Short):
            write('h', self.value)
        elif isinstance(self, TAG_Int):
            write('i', self.value)
        elif isinstance(self, TAG_Long):
            write('q', self.value)
        elif isinstance(self, TAG_Float):
            write('f', self.value)
        elif isinstance(self, TAG_Double):
            write('d', self.value)

    def pretty(self, indent=0, indent_str='  '):
        """
        Pretty-print a tag in the same general style as Markus's example
        output.
        """
        return '{0}{1}({2!r}): {3!r}'.format(
            indent_str * indent,
            self.__class__.__name__,
            self.name,
            self.value
        )

    def __repr__(self):
        return '{0}({1!r}, {2!r})'.format(
            self.__class__.__name__, self.value, self.name)

    def __str__(self):
        return repr(self)

    def __unicode__(self):
        return unicode(repr(self), 'utf-8')


class TAG_Byte(BaseTag):
    pass


class TAG_Short(BaseTag):
    pass


class TAG_Int(BaseTag):
    pass


class TAG_Long(BaseTag):
    pass


class TAG_Float(BaseTag):
    pass


class TAG_Double(BaseTag):
    pass


class TAG_Byte_Array(BaseTag):
    def pretty(self, indent=0, indent_str='  '):
        return '{0}TAG_Byte_Array({1!r}): [{2} bytes]'.format(
            indent_str * indent, self.name, len(self.value))


class TAG_String(BaseTag):
    pass


class TAG_List(BaseTag, list):
    def __init__(self, tag_type, value=None, name=None):
        """
        Creates a new homogeneous list of `tag_type` items, copying `value`
        if provided.
        """
        self.name = name
        self.value = self
        self.type_ = tag_type
        if value is not None:
            self.extend(value)

    def pretty(self, indent=0, indent_str='  '):
        t = []
        t.append('{0}TAG_List({1!r}): {2} entries'.format(
            indent_str * indent, self.name, len(self.value)))
        t.append('{0}{{'.format(indent_str * indent))
        for v in self.value:
            t.append(v.pretty(indent + 1, indent_str))
        t.append('{0}}}'.format(indent_str * indent))
        return '\n'.join(t)

    def __repr__(self):
        return '{0}({1!r} entries, {2!r})'.format(
            self.__class__.__name__, len(self), self.name)


class TAG_Compound(BaseTag, dict):
    def __init__(self, value=None, name=None):
        self.name = name
        self.value = self
        if value is not None:
            self.update(value)

    def pretty(self, indent=0, indent_str='  '):
        t = []
        t.append('{0}TAG_Compound({1!r}): {2} entries'.format(
            indent_str * indent, self.name, len(self.value)))
        t.append('{0}{{'.format(indent_str * indent))
        for v in self.values():
            t.append(v.pretty(indent + 1, indent_str))
        t.append('{0}}}'.format(indent_str * indent))
        return '\n'.join(t)

    def __repr__(self):
        return '{0}({1!r} entries, {2!r})'.format(
            self.__class__.__name__, len(self), self.name)

    def __setitem__(self, key, value):
        """
        Sets the TAG_*'s name if it isn't already set to that of the key
        it's being assigned to. This results in cleaner code, as the name
        does not need to be specified twice.
        """
        if value.name is None:
            value.name = key
        super(TAG_Compound, self).__setitem__(key, value)

    def update(self, *args, **kwargs):
        """See `__setitem__`."""
        super(TAG_Compound, self).update(*args, **kwargs)
        for key, item in self.items():
            if item.name is None:
                item.name = key


class TAG_Int_Array(BaseTag):
    def pretty(self, indent=0, indent_str='  '):
        return '{0}TAG_Int_Array({1!r}): [{2} integers]'.format(
            indent_str * indent, self.name, len(self.value))

# The TAG_* types have the convienient property of being continuous.
# The code is written in such a way that if this were to no longer be
# true in the future, _tags can simply be replaced with a dict().
_tags = (
    None,
    TAG_Byte,
    TAG_Short,
    TAG_Int,
    TAG_Long,
    TAG_Float,
    TAG_Double,
    TAG_Byte_Array,
    TAG_String,
    TAG_List,
    TAG_Compound,
    TAG_Int_Array
    )


class NBTFile(TAG_Compound):
    class Compression(object):
        """
        Defines compression schemes to be used for loading and saving
        NBT files.
        """
        # NONE is simply for the sake of completeness.
        NONE = 10
        # Use Gzip compression when reading or writing.
        GZIP = 20

    def __init__(self, io=None, name=None, value=None, compression=None,
                 little_endian=False):
        """
        Creates a new NBTFile or loads one from any file-like object providing
        `read()`.

        Construction a new NBTFile() is as simple as:
        >>> nbt = NBTFile(name='')

        Whereas loading an existing one is most often done:
        >>> with open('my_file.nbt', rb') as io:
        ...     nbt = NBTFile(io=io, compression=NBTFile.Compression.GZIP)
        """
        # No file or path given, so we're creating a new NBTFile.
        if io is None:
            super(NBTFile, self).__init__(value if value else {}, name)
            return

        if compression is None or compression == NBTFile.Compression.NONE:
            final_io = io
        elif compression == NBTFile.Compression.GZIP:
            final_io = gzip.GzipFile(fileobj=io, mode='rb')
        else:
            raise ValueError('Unrecognized compression scheme.')

        # The pocket edition uses little-endian NBT files, but annoyingly
        # without any kind of header we can't determine that ourselves,
        # not even a magic number we could flip.
        if little_endian:
            read = lambda fmt, size: unpack('<' + fmt, final_io.read(size))
        else:
            read = lambda fmt, size: unpack('>' + fmt, final_io.read(size))
        read.io = final_io

        # All valid NBT files will begin with 0x0A, which is a TAG_Compound.
        if read('b', 1)[0] != 0x0A:
            raise IOError('NBTFile does not begin with 0x0A.')

        tmp = TAG_Compound.read(read)
        super(NBTFile, self).__init__(tmp, tmp.name)

    def save(self, io, compression=None, little_endian=False):
        """
        Saves the `NBTFile()` to `io`, which can be any file-like object
        providing `write()`.
        """
        if compression is None or compression == NBTFile.Compression.NONE:
            final_io = io
        elif compression == NBTFile.Compression.GZIP:
            final_io = gzip.GzipFile(fileobj=io, mode='wb')

        if little_endian:
            write = lambda fmt, *args: final_io.write(pack('<' + fmt, *args))
        else:
            write = lambda fmt, *args: final_io.write(pack('>' + fmt, *args))
        write.io = final_io

        self.write(write)
########NEW FILE########
__FILENAME__ = start
import getpass
import sys
import Utils
from pluginloader import PluginLoader
from networking import PacketSenderManager, NetworkManager
from optparse import OptionParser
try:
    import colorama
    colorama.init()
except ImportError:
    pass

if __name__ == "__main__":
    parser = OptionParser()

    parser.add_option("-u", "--username", dest="username", default="",
        help="username to log in with")

    parser.add_option("-p", "--password", dest="password", default="",
        help="password to log in with")

    parser.add_option("-s", "--server", dest="server", default="",
        help="server to connect to")

    parser.add_option("-x", "--offline-mode", dest="offlineMode",
        action="store_true", default=False,
        help="run in offline mode i.e don't attempt to auth via minecraft.net")

    parser.add_option("-c", "--disable-console-colours", dest="disableAnsiColours",
        action="store_true", default=False,
        help="print minecraft chat colours as their equivalent ansi colours")

    # pluginLoader
    pluginLoader = PluginLoader("plugins")
    pluginLoader.loadPlugins(parser)

    (options, args) = parser.parse_args()

    pluginLoader.notifyOptions(options)

    if (options.username != ""):
        user = options.username
    else:
        user = raw_input("Enter your username: ")
    if (options.password != ""):
        passwd = options.password
    elif (not options.offlineMode):
        passwd = getpass.getpass("Enter your password: ")

    if (not options.offlineMode):
        loginThread = Utils.MinecraftLoginThread(user, passwd)
        loginThread.start()
        loginThread.join()
        loginResponse = loginThread.getResponse()
        if (loginResponse['Response'] != "Good to go!"):
            print loginResponse['Response']
            sys.exit(1)
        sessionid = loginResponse['SessionID']
        user = loginResponse['Username']
        print "Logged in as " + loginResponse['Username'] + "! Your session id is: " + sessionid
    else:
        sessionid = None

    if (options.server != ""):
        serverAddress = options.server
    else:
        serverAddress = raw_input("Enter host and port if any: ")
    if ':' in serverAddress:
        StuffEnteredIntoBox = serverAddress.split(":")
        host = StuffEnteredIntoBox[0]
        port = int(StuffEnteredIntoBox[1])
    else:
        host = serverAddress
        port = 25565
    connection = NetworkManager.ServerConnection(pluginLoader, user, sessionid, host, port, options)
    connection.setDaemon(True)
    connection.start()
    while True:
        try:
            chat_input = raw_input()
            if (connection.isConnected):
                PacketSenderManager.send03(connection.grabSocket(),
                        chat_input.decode('utf-8')[:100])
            else:
                pass
        except KeyboardInterrupt, e:
            connection.disconnect()
            pluginLoader.disablePlugins()
            sys.exit(1)

########NEW FILE########
__FILENAME__ = Utils
import re
import urllib2
import urllib
import threading
from hashlib import sha1

# This function courtesy of barneygale
def javaHexDigest(digest):
    d = long(digest.hexdigest(), 16)
    if d >> 39 * 4 & 0x8:
        d = "-%x" % ((-d) & (2 ** (40 * 4) - 1))
    else:
        d = "%x" % d
    return d


def translate_escape(m):
    c = m.group(1).lower()

    if c == "0": return "\x1b[30m\x1b[21m" # black
    elif c == "1": return "\x1b[34m\x1b[21m" # dark blue
    elif c == "2": return "\x1b[32m\x1b[21m" # dark green
    elif c == "3": return "\x1b[36m\x1b[21m" # dark cyan
    elif c == "4": return "\x1b[31m\x1b[21m" # dark red
    elif c == "5": return "\x1b[35m\x1b[21m" # purple
    elif c == "6": return "\x1b[33m\x1b[21m" # gold
    elif c == "7": return "\x1b[37m\x1b[21m" # gray
    elif c == "8": return "\x1b[30m\x1b[1m"  # dark gray
    elif c == "9": return "\x1b[34m\x1b[1m"  # blue
    elif c == "a": return "\x1b[32m\x1b[1m"  # bright green
    elif c == "b": return "\x1b[36m\x1b[1m"  # cyan
    elif c == "c": return "\x1b[31m\x1b[1m"  # red
    elif c == "d": return "\x1b[35m\x1b[1m"  # pink
    elif c == "e": return "\x1b[33m\x1b[1m"  # yellow
    elif c == "f": return "\x1b[37m\x1b[1m"  # white
    elif c == "k": return "\x1b[5m"          # random
    elif c == "l": return "\x1b[1m"          # bold
    elif c == "m": return "\x1b[9m"          # strikethrough (escape code not widely supported)
    elif c == "n": return "\x1b[4m"          # underline
    elif c == "o": return "\x1b[3m"          # italic (escape code not widely supported)
    elif c == "r": return "\x1b[0m"          # reset

    return ""


def translate_escapes(s):
    return re.sub(ur"\xa7([0-9a-zA-Z])", translate_escape, s) + "\x1b[0m"


def loginToMinecraft(username, password):
    try:
        url = 'https://login.minecraft.net'
        header = {'Content-Type': 'application/x-www-form-urlencoded'}
        data = {'user': username,
                'password': password,
                'version': '13'}
        data = urllib.urlencode(data)
        req = urllib2.Request(url, data, header)
        opener = urllib2.build_opener()
        response = opener.open(req, None, 10)
        response = response.read()
    except urllib2.URLError:
        return {'Response': "Can't connect to minecraft.net"}
    if (not "deprecated" in response.lower()):
        return {'Response': response}
    response = response.split(":")
    sessionid = response[3]
    toReturn = {'Response': "Good to go!",
                'Username': response[2],
                'SessionID': sessionid
    }
    return toReturn


class MinecraftLoginThread(threading.Thread):
    def __init__(self, username, password):
        threading.Thread.__init__(self)
        self.username = username
        self.password = password

    def run(self):
        self.response = loginToMinecraft(self.username, self.password)

    def getResponse(self):
        return self.response
    
########NEW FILE########
