__FILENAME__ = db
#!/usr/bin/python
# -*- coding: utf-8 -*-

from siriObjects.systemObjects import SetAssistantData
from uuid import uuid4
import cPickle
import logging
import sqlite3

__database__ = "database.sqlite3"

def setup():
    conn = getConnection()
    c = conn.cursor()
    c.execute("""
        create table if not exists assistants(assistantId text primary key, assistant assi)
        """)
    conn.commit()
    c.close()
    conn.close()

def getConnection():
    try:
        return sqlite3.connect(__database__, detect_types=sqlite3.PARSE_DECLTYPES, timeout=10.0, check_same_thread=False)
    except sqlite3.Error.OperationalError as e:
        logging.getLogger().error("Connecting to the internal database timed out, there are probably to many connections accessing the database")
        logging.getLogger().error(e)
    return None

class Assistant(SetAssistantData):
    def __init__(self):
        self.activationToken = None # @"NSData"
        self.connectionType = None # @"NSString"
        self.language = None # @"NSString"
        self.validationData = None # @"NSData"
        self.assistantId = None
        self.nickName = u''
        self.firstName=u''


def adaptAssistant(assistant):
    return cPickle.dumps(assistant)

def convertAssistant(fromDB):
    return cPickle.loads(fromDB)

sqlite3.register_adapter(Assistant, adaptAssistant)
sqlite3.register_converter("assi", convertAssistant)
########NEW FILE########
__FILENAME__ = flac
from ctypes import *
import ctypes.util
import math
import os
import struct
import tempfile

libflac_name = ctypes.util.find_library('FLAC')
if libflac_name == None:
    print "Could not find libFLAC"
    exit()
libflac = CDLL(libflac_name)


def writeCallBack(encoder, buf, numBytes, samples, current_frame, client_data):
    print "Test"
    instance = cast(client_data, py_object).value
    return Encoder.internalCallBack(instance, encoder, buf, numBytes, samples, current_frame)



class Encoder:
    
    def __init__(self):
        self.encoder = None
        self.output = None
        self.filename = None

    
    def initialize(self, sample_rate, channels, bps):
        libflac.FLAC__stream_encoder_new.restype = c_void_p
        libflac.FLAC__stream_encoder_set_verify.argtypes = [c_void_p, c_bool]
        libflac.FLAC__stream_encoder_set_verify.restype = c_bool
        
        libflac.FLAC__stream_encoder_set_compression_level.argtypes = [c_void_p, c_uint]
        libflac.FLAC__stream_encoder_set_compression_level.restype = c_bool
        
        libflac.FLAC__stream_encoder_set_channels.argtypes = [c_void_p, c_uint]
        libflac.FLAC__stream_encoder_set_channels.restype = c_bool
        
        libflac.FLAC__stream_encoder_set_bits_per_sample.argtypes = [c_void_p, c_uint]
        libflac.FLAC__stream_encoder_set_bits_per_sample.restype = c_bool
        
        libflac.FLAC__stream_encoder_set_sample_rate.argtypes = [c_void_p, c_uint]
        libflac.FLAC__stream_encoder_set_sample_rate.restype = c_bool
        
        libflac.FLAC__stream_encoder_set_total_samples_estimate.argtypes = [c_void_p, c_uint64]
        
        libflac.FLAC__stream_encoder_set_total_samples_estimate.restype = c_bool
        
        writeCallBackFUN = CFUNCTYPE(c_uint, c_void_p, c_char_p, c_size_t, c_uint, c_uint, c_void_p)
        
        libflac.FLAC__stream_encoder_init_stream.argtypes = [c_void_p, writeCallBackFUN, c_void_p, c_void_p, c_void_p, py_object]
        
        libflac.FLAC__stream_encoder_process.restype = c_bool
        libflac.FLAC__stream_encoder_process.argtypes = [c_void_p, POINTER(POINTER(c_int32)), c_uint]
        
        libflac.FLAC__stream_encoder_process_interleaved.restype = c_bool

        libflac.FLAC__stream_encoder_process_interleaved.argtypes = [c_void_p, c_void_p, c_uint]
        
        libflac.FLAC__stream_encoder_finish.argtypes = [c_void_p]
        libflac.FLAC__stream_encoder_finish.restype = c_bool
        libflac.FLAC__stream_encoder_delete.argtypes = [c_void_p]
        
        libflac.FLAC__stream_encoder_init_file.argtypes = [c_void_p, c_char_p, c_void_p, c_void_p]
        
        self.encoder = libflac.FLAC__stream_encoder_new()
        
        ok = 1

        ok &= libflac.FLAC__stream_encoder_set_verify(self.encoder, True)

        ok &= libflac.FLAC__stream_encoder_set_compression_level(self.encoder, 5)
        ok &= libflac.FLAC__stream_encoder_set_channels(self.encoder, channels)
        ok &= libflac.FLAC__stream_encoder_set_bits_per_sample(self.encoder, bps);
        ok &= libflac.FLAC__stream_encoder_set_sample_rate(self.encoder, sample_rate);
        
        
        self.output = ""
        #libflac.FLAC__stream_encoder_init_stream(self.encoder, writeCallBackFUN(writeCallBack), None, None, None, py_object(self))
        tmpFile = tempfile.NamedTemporaryFile(delete=False)
        tmpFile.close()
        self.filename = tmpFile.name
        libflac.FLAC__stream_encoder_init_file(self.encoder, self.filename, None, None)
        if not ok:
            print "Error initializing libflac"
            exit()
    
    def internalCallBack(self, encoder, buf, numBytes, samples, current_frame):
        self.output += string_at(buf, numBytes)
        print self.output
        return 0
    


    def encode(self, data):
        length = int(len(data)/2)
        int16s = struct.unpack('<' + ('h'*length), data)
        int32s = struct.pack('@' + ('i'*length), *int16s)
        libflac.FLAC__stream_encoder_process_interleaved(self.encoder, int32s, length)

    def getBinary(self):
        f = open(self.filename, 'r')
        flac = f.read()
        f.close()
        return flac
        
    def finish(self):
        if self.encoder:
            libflac.FLAC__stream_encoder_finish(self.encoder)
    
    def destroy(self):
        if self.encoder:
            libflac.FLAC__stream_encoder_delete(self.encoder)
            os.unlink(self.filename)
            self.encoder = None

########NEW FILE########
__FILENAME__ = httpClient
from twisted.internet import threads, defer
import contextlib
import logging
import urllib2

class AsyncOpenHttp(object):
    def __init__(self, callback):
        super(AsyncOpenHttp, self).__init__()
        self.callback = callback
    
    def make_google_request(self, flac, requestId, dictation, language="de-DE", allowCurses=True):
        d = threads.deferToThread(self.run, flac, requestId, dictation, language, allowCurses)
        d.addCallback(self.callback, requestId, dictation)
        d.addErrback(self.onError)
        return d
    
    def onError(self, failure):
        failure.trap(defer.CancelledError)
        logging.getLogger().info("Google request canceled")
        pass
    
    def getWebsite(self, url, timeout=5):
        '''
            This method retrieved the website at the url encoded url
            if this method fails to retrieve the website with the given timeout
            or anything else, None is returned
        '''
        try:
            with contextlib.closing(urllib2.urlopen(url, timeout=timeout)) as page:
                body = page.read()
                return body
        except:
            pass
        return None
    
    def run(self, flac, requestId, dictation, language, allowCurses):
        url = "https://www.google.com/speech-api/v1/recognize?xjerr=1&client=chromium&pfilter={0}&lang={1}&maxresults=6".format(0 if allowCurses else 2, language)
        req = urllib2.Request(url, data = flac, headers = {'Content-Type': 'audio/x-flac; rate=16000', 'User-Agent': 'Siri-Server'})
        return self.getWebsite(req, timeout=10)

########NEW FILE########
__FILENAME__ = HTTPRequest
#!/usr/bin/python
# -*- coding: utf-8 -*-

from BaseHTTPServer import BaseHTTPRequestHandler
from StringIO import StringIO

class HTTPRequest(BaseHTTPRequestHandler):
    def __init__(self, request_text):
        self.rfile = StringIO(request_text)
        self.raw_requestline = self.rfile.readline()
        self.error_code = self.error_message = None
        self.parse_request()

    def send_error(self, code, message):
        self.error_code = code
        self.error_message = message

########NEW FILE########
__FILENAME__ = plugin
#!/usr/bin/python
# -*- coding: utf-8 -*-



from siriObjects.baseObjects import ClientBoundCommand, RequestCompleted
from siriObjects.systemObjects import GetRequestOrigin, SetRequestOrigin
from siriObjects.uiObjects import UIAddViews, UIAssistantUtteranceView, \
    UIOpenLink, UIButton
import PluginManager
import contextlib
import inspect
import logging
import re
import threading
import urllib2



__criteria_key__ = "criterias"


__error_responses__ = {
    "de-DE": "Es ist ein Fehler in der Verarbeitung ihrer Anfrage aufgetreten!",
    "en-US": "There was an error during the processing of your request!",
    "en-GB": "There was an error during the processing of your request!",
    "en-AU": "There was an error during the processing of your request!",
    "fr-FR": "Il y avait une erreur lors du traitement de votre demande!",
    "nl-NL": u"Er is een fout opgetreden tijdens de verwerking van uw aanvraag!",
}

__error_location_help__ = {
    "de-DE": u"Ich weiß nicht wo du bist… Aber du kannst mir helfen es heraus zu finden…",
    "en-US": u"I don’t know where you are… But you can help me find out…",
    "en-GB": u"I don’t know where you are… But you can help me find out…",
    "en-AU": u"I don’t know where you are… But you can help me find out…",
    "fr-FR": u"Je ne sais pas où vous êtes ... Mais vous pouvez m'aider à en savoir plus sur ...",
    "nl-NL": u"Ik weet niet waar je bent… Maar je kunt me helpen erachter te komen…",
}

__error_location_saysettings__ = {
    "de-DE": u"In den Ortungsdienst Einstellungen, schalte Ortungsdienst und Siri ein.",
    "en-US": u"In Location Services Settings, turn on both Location Services and Siri.",
    "en-GB": u"In Location Services Settings, turn on both Location Services and Siri.",
    "en-AU": u"In Location Services Settings, turn on both Location Services and Siri.",
    "fr-FR": u"Dans les paramètres de service de localisation, activez les services de localisation et Siri.",
    "nl-NL": u"In locatievoorzieningen instellingen, zet locatievoorzieningen en Siri aan."
}

__error_location_settings__ = {
    "de-DE": u"Ortungsdienst Einstellungen",
    "en-US": u"Location Services Settings",
    "en-GB": u"Location Services Settings",
    "en-AU": u"Location Services Settings",
    "fr-FR": u"Services de localisation",
    "nl-NL": u"Locatievoorzieningen Instellingen",
}



def register(lang, regex):
    def addInfosTo(func):
        if not __criteria_key__ in func.__dict__:
            func.__dict__[__criteria_key__] = dict()
        crits = func.__dict__[__criteria_key__]
        crits[lang] = re.compile(regex, re.IGNORECASE | re.UNICODE)
        return func
    return addInfosTo

class StopPluginExecution(Exception):
    def __init__(self, reason):
        self.reason = reason
    def __str__(self):
        return repr(self.reason)

class ApiKeyNotFoundException(Exception):
    def __init__(self, reason):
        self.reason = reason
    def __str__(self):
        return repr(self.reason)

class NecessaryModuleNotFound(Exception):
    def __init__(self, reason):
        self.reason = reason
    def __str__(self):
        return repr(self.reason)

def APIKeyForAPI(apiName):
    apiKey = PluginManager.getAPIKeyForAPI(apiName)
    if apiKey == None or apiKey == "":
        raise ApiKeyNotFoundException("Could not find API key for: "+ apiName + ". Please check your " + PluginManager.__apikeys_file__)
    return apiKey


def getWebsite(url, timeout=5):
    '''
        This method retrieved the website at the url encoded url
        if this method fails to retrieve the website with the given timeout
        or anything else, None is returned
    '''
    try:
        with contextlib.closing(urllib2.urlopen(url, timeout=timeout)) as page:
            body = page.read()
            return body
    except:
        pass
    return None

class Plugin(threading.Thread):
    def __init__(self):
        super(Plugin, self).__init__()
        self.__method = None
        self.__lang = None
        self.__speech = None
        self.waitForResponse = None
        self.response = None
        self.refId = None
        self.connection = None
        self.__send_plist = None
        self.__send_object = None
        self.assistant = None
        self.location = None
        self.logger = logging.getLogger()
        self.__priority = False
        self.__shouldCancel = False
    
    def initialize(self, method, speech, language, send_object, send_plist, assistant, location):
        super(Plugin, self).__init__()
        self.__method = method
        self.__lang = language
        self.__speech = speech
        self.__send_plist = send_plist
        self.__send_object = send_object
        self.assistant = assistant
        self.location = location
        self.__shouldCancel = False
        self.__priority = False
        
    def _abortPluginRun(self):
        self.__shouldCancel = True
        

    def run(self):
        try:
            try:
                arguments = inspect.getargspec(self.__method).args
                if len(arguments) == 3:
                    self.__method(self, self.__speech, self.__lang)
                elif len(arguments) == 4:
                    self.__method(self, self.__speech, self.__lang, self.__method.__dict__[__criteria_key__][self.__lang].match(self.__speech))
                if self.__priority:
                    PluginManager.prioritizePluginObject(self, self.assistant.assistantId)
                else:
                    PluginManager.clearPriorityFor(self.assistant.assistantId)
            except ApiKeyNotFoundException as e:
                self.logger.warning("Failed executing plugin due to missing API key: "+str(e))
            except StopPluginExecution, instance:
                self.logger.info("Plugin stopped executing with reason: {0}".format(instance))
            except:
                self.logger.exception("Unexpected error during plugin processing")
                self.say(__error_responses__[self.__lang])
                self.complete_request()
        except:
            pass
        self.connection.current_running_plugin = None
        self.connection = None
        self.assistant = None
        self.location = None
        self.__send_object = None
        self.__send_plist = None
        self.__method = None
        self.__lang = None
        self.__speech = None
        self.waitForResponse = None
        self.response = None
        self.refId = None
        
    def _checkForCancelRequest(self):
        if self.__shouldCancel:
            raise StopPluginExecution("Plugin run was aborted")

    def requestPriorityOnNextRequest(self):
        self._checkForCancelRequest()
        self.__priority = True

    def getCurrentLocation(self, force_reload=False, accuracy=GetRequestOrigin.desiredAccuracyBest):
        self._checkForCancelRequest()
        if self.location != None and force_reload == False:
            return self.location
        if self.location == None or (self.location != None and force_reload):
            #do a reload
            response = self.getResponseForRequest(GetRequestOrigin(self.refId, desiredAccuracy=accuracy, searchTimeout=5.0))
            if response['class'] == 'SetRequestOrigin':
                self.location = SetRequestOrigin(response)
                if self.location.status != None and self.location.status != SetRequestOrigin.statusValid:
                    # urgs... we are fucked no location here, there is a status
                    # tell the other end that it fucked up and should enable location service
                    
                    #We need to say something
                    view1 = UIAssistantUtteranceView()
                    view1.text = view1.speakableText = __error_location_help__[self.__lang] if self.__lang in __error_location_help__ else __error_location_help__['en-US']
                    view1.dialogIdentifier="Common#assistantLocationServicesDisabled"
                    
                    #lets create another which has tells him to open settings
                    view2 = UIAssistantUtteranceView()
                    view2.text = view2.speakableText = __error_location_saysettings__[self.__lang] if self.__lang in __error_location_saysettings__ else __error_location_saysettings__['en-US']
                    view2.dialogIdentifier="Common#assistantLocationServicesDisabled"
                    
                    #create a link
                    link = UIOpenLink(self.refId)
                    link.ref="prefs:root=LOCATION_SERVICES"
                    
                    # create a button which opens the location tab in the settings if clicked on it
                    button = UIButton()
                    button.text = __error_location_settings__[self.__lang] if self.__lang in __error_location_settings__ else __error_location_settings__['en-US']
                    button.commands = [link]
                    
                    # wrap it up in a adds view
                    addview = UIAddViews(self.refId)
                    addview.views = [view1, view2, button]
                    addview.dialogPhase = addview.DialogPhaseClarificationValue
                    self.send_object(addview)
                    self.complete_request()
                    # we should definitivly kill the running plugin
                    raise StopPluginExecution("Could not get necessary location information")
                else: 
                    return self.location
            elif response['class'] == 'SetRequestOriginFailed':
                self.logger.warning('THIS IS NOT YET IMPLEMENTED, PLEASE PROVIDE SITUATION WHERE THIS HAPPEND')
                raise Exception()
     
    def send_object(self, obj):
        self._checkForCancelRequest()
        self.connection.plugin_lastAceId = obj.aceId
        self.__send_object(obj)
    
    def send_plist(self, plist):
        self._checkForCancelRequest()
        self.connection.plugin_lastAceId = plist['aceId']
        self.__send_plist(plist)

    def complete_request(self, callbacks=None):
        self._checkForCancelRequest()
        self.connection.current_running_plugin = None
        self.send_object(RequestCompleted(self.refId, callbacks))

    def ask(self, text, speakableText=None):
        self._checkForCancelRequest()
        self.waitForResponse = threading.Event()
        if speakableText == None:
            speakableText = text
        view = UIAddViews(self.refId)
        view1 = UIAssistantUtteranceView()
        view1.text = text
        view1.speakableText = speakableText 
        view1.listenAfterSpeaking = True
        view.views = [view1]
        self.send_object(view)
        self.waitForResponse.wait()
        self._checkForCancelRequest()
        self.waitForResponse = None
        return self.response

    def getResponseForRequest(self, clientBoundCommand):
        self._checkForCancelRequest()
        self.waitForResponse = threading.Event()
        if isinstance(clientBoundCommand, ClientBoundCommand):
            self.send_object(clientBoundCommand)
        else:
            self.send_plist(clientBoundCommand)
        self.waitForResponse.wait()
        self._checkForCancelRequest()
        self.waitForResponse = None
        return self.response
    
    def sendRequestWithoutAnswer(self, clientBoundCommand):
        self._checkForCancelRequest()
        if isinstance(clientBoundCommand, ClientBoundCommand):
            self.send_object(clientBoundCommand)
        else:
            self.send_plist(clientBoundCommand)

    def say(self, text, speakableText=None):
        self._checkForCancelRequest()
        view = UIAddViews(self.refId)
        if speakableText == None:
            speakableText = text
        view1 = UIAssistantUtteranceView()
        view1.text = text
        view1.speakableText = speakableText
        view.views = [view1]
        self.send_object(view)
        
    def user_name(self):
        if self.assistant.nickName!='':
            self.user_name=self.assistant.nickName.decode("utf-8")
        elif self.assistant.firstName!='':
            self.user_name=self.assistant.firstName.decode("utf-8")
        else:
            self.user_name=u''
        return self.user_name

########NEW FILE########
__FILENAME__ = PluginManager
from plugin import Plugin, __criteria_key__, NecessaryModuleNotFound, \
    ApiKeyNotFoundException
from types import FunctionType
import logging
import os
import re



logger = logging.getLogger("logger")
pluginPath = "plugins"

__config_file__ = "plugins.conf"
__apikeys_file__ = "apiKeys.conf"



plugins = dict()
prioritizedPlugins = dict()
apiKeys = dict()

def load_plugins():
    with open(__config_file__, "r") as fh:
        for line in fh:
            line = line.strip()
            if line.startswith("#") or line == "":
                continue
            # just load the whole shit...
            try:
                __import__(pluginPath+"."+line,  globals(), locals(), [], -1)
            except NecessaryModuleNotFound as e:
                logger.critical("Failed loading plugin due to missing module: "+str(e))
            except ApiKeyNotFoundException as e:
                logger.critical("Failed loading plugin due to missing API key: "+str(e))
            except:
                logger.exception("Plugin loading failed")
            
    # as they are loaded in the order in the file we will have the same order in __subclasses__()... I hope

    for clazz in Plugin.__subclasses__():
        # look at all functions of a class lets filter them first
        methods = filter(lambda x: type(x) == FunctionType, clazz.__dict__.values())
        # now we check if the method is decorated by register
        for method in methods:
            if __criteria_key__ in method.__dict__:
                criterias = method.__dict__[__criteria_key__]
                for lang, regex in criterias.items():
                    if not lang in plugins:
                        plugins[lang] = []
                    # yeah... save the regex, the clazz and the method, shit just got loaded...
                    plugins[lang].append((regex, clazz, method))


def reload_api_keys():
    global apiKeys
    apiKeys = dict()
    load_api_keys()

def load_api_keys():
    with open(__apikeys_file__, "r") as fh:
        for line in fh:
            line = line.strip()
            if line.startswith("#") or line == "":
                continue
            kv = line.split("=", 1)
            try:
                apiName = str.lower(kv[0]).strip()
                kv[1] = kv[1].strip()
                apiKey = kv[1][1:-1] #stip the ""
                apiKeys[apiName] = apiKey
            except:
                logger.critical("There was an error parsing an API in the line: "+ line)

def getAPIKeyForAPI(APIname):
    apiName = str.lower(APIname) 
    if apiName in apiKeys:
        return apiKeys[apiName]
    return None

def getPlugin(speech, language):
    if language in plugins:
        for (regex, clazz, method) in plugins[language]:
            if regex.match(speech) != None:
                return (clazz, method)
    return (None, None)

def clearPriorityFor(assistantId):
    if assistantId in prioritizedPlugins:
        del prioritizedPlugins[assistantId]

def prioritizePluginObject(pluginObj, assistantId):
    prioritizedPlugins[assistantId] = dict()
    for lang in plugins.keys():
        for (regex, clazz, method) in plugins[lang]:
            if pluginObj.__class__ == clazz:
                if not lang in prioritizedPlugins[assistantId]:
                    prioritizedPlugins[assistantId][lang] = []
                prioritizedPlugins[assistantId][lang].append((regex, pluginObj, method))

def searchPrioritizedPlugin(assistantId, speech, language):
    if assistantId in prioritizedPlugins:
        if language in prioritizedPlugins[assistantId]:
            for (regex, pluginObj, method) in prioritizedPlugins[assistantId][language]:
                if regex.match(speech) != None:
                    return (pluginObj, method)
    return (None, None)

def getPluginForImmediateExecution(assistantId, speech, language, otherPluginParams):
    (sendObj, sendPlist, assistant, location) = otherPluginParams

    (pluginObj, method) = searchPrioritizedPlugin(assistantId, speech, language)
    if pluginObj == None and method == None:
        (clazz, method) = getPlugin(speech, language)
        if clazz != None and method != None:
            logger.debug("Instantiating plugin and method: {0}.{1}".format(clazz.__name__, method.__name__))
            pluginObj = clazz()
            pluginObj.initialize(method, speech, language, sendObj, sendPlist, assistant, location)
            #prioritizePluginObject(pluginObj, assistantId)
    else:
        #reinitialize it
        logger.info("Found a matching prioritized plugin")
        pluginObj.initialize(method, speech, language, sendObj, sendPlist, assistant, location)
    
    return pluginObj
        




########NEW FILE########
__FILENAME__ = SiriCore
#!/usr/bin/python
# -*- coding: utf-8 -*-

from HTTPRequest import HTTPRequest
from email.utils import formatdate
from twisted.internet import error
from twisted.protocols.basic import LineReceiver
from twisted.python import failure
import OpenSSL
import biplist
import logging
import struct
import threading
import zlib
import pprint
import re

class Ping(object):
    def __init__(self, num):
        self.num = num
        
class ServerObject(object):
    def __init__(self, plist):
        self.plist = plist

class Siri(LineReceiver):
    #Assistant(MacBook Pro/MacBookPro9,2; Mac OS X/10.8.2/12C60) Ace/1.2
    userAgentParser = re.compile("Assistant\((?P<deviceType>.*)/(?P<deviceVersion>.+); (?P<clientOSType>.*)/(?P<clientOSVersion>.*)/(?P<clientOSbuildNumber>.*)\) Ace/(?P<protocolVersion>.*)")

    def __init__(self, server, peer):
        self.server = server
        self.peer = peer
        self.header = ""
        self.headerPerField = dict()
        self.rawData = ""
        self.output_buffer = ""
        self.unzipped_output_buffer = ""
        self.unzipped_input = ""
        self.consumed_ace = False
        self.decompressor = zlib.decompressobj()
        self.compressor = zlib.compressobj()
        self.logger = logging.getLogger()
        self.sendLock = threading.Lock()
        self.deviceType = "Unknown"
        self.deviceVersion = "Unknown"
        self.protocolVersion = "Unknown"
        self.clientOSType = "Unknown"
        self.clientOSVersion = "Unknown"
        self.clientOSbuildNumber = "Unknown"

    def connectionMade(self):
        self.logger.info("New connection from {0} on port {1}".format(self.peer.host, self.peer.port))
        self.server.numberOfConnections += 1
        self.logger.info("Currently {0} clients connected".format(self.server.numberOfConnections))

    def connectionLost(self, reason):
        if reason.type == OpenSSL.SSL.Error:
            self.logger.warning("SSL related error")
            self.logger.warning(reason.value)
        elif reason.type == error.ConnectionLost:
            self.logger.warning("Connection Lost: {0}".format(reason.value))
        elif reason.type == error.ConnectionDone:
            self.logger.info("Connection Closed: {0}".format(reason.value))
        else:
            self.logger.error("Connection Lost: {0}".format(reason))
        self.server.numberOfConnections -= 1
        self.logger.info("Currently {0} clients connected".format(self.server.numberOfConnections))
        self.server = None
        self.peer = None
        self.decompressor = None
        self.compressor = None
        self.sendLock = None
        
    def checkHeader(self):
        if "\r\n\r\n" in self.header:
            # end of header found, lets check it
            self.logger.debug("--------------HEADER START---------------")
            self.logger.debug(self.header)
            self.logger.debug("---------------HEADER END----------------")
            request = HTTPRequest(self.header)
            if request.error_code == None:
                if request.command == "HEAD" and request.path == "/salt":
                    return (406, "Unacceptable")
                if request.command == "HEAD" and request.path == "/ace":
                    return (406, "Unacceptable")
                if request.command != "ACE":
                    return (405, "Method Not Allowed")
                if request.path != "/ace":
                    return (404, "Not Found")
            else:
                return (request.error_code, request.error_message)
            return True
        else:
            return False
    
    def lineReceived(self, line):
        self.header += line + "\r\n"
        headerCheck = self.checkHeader();
        success = False
        if type(headerCheck) == bool:
            if (headerCheck):
                code = 200
                message = "OK"
                success = True
                self.output_buffer = ("HTTP/1.1 {0} {1}\r\nServer: Apache-Coyote/1.1\r\nDate: " + formatdate(timeval=None, localtime=False, usegmt=True) + "\r\nConnection: close\r\n\r\n").format(code, message)
            else:
                # we need to receive more
                return
        else:
            code, message = headerCheck
            self.output_buffer = "HTTP/1.0 {0} {1}\r\nContent-Length: {2}\r\n\r\n{0} {1}".format(code, message, len(str(code))+len(message)+1)
            
        self.flush_output_buffer()
        if not success:
            self.transport.loseConnection()
        else:
            self.consumed_ace = False
            headerlines = self.header.strip().splitlines()[1:]
            self.headerPerField = dict([headerlines[i].split(": ") for i in range(0, len(headerlines))])
            if "User-Agent" in self.headerPerField.keys():
                match = Siri.userAgentParser.match(self.headerPerField["User-Agent"])
                if match != None:
                    self.deviceType = match.group('deviceType')
                    self.deviceVersion = match.group('deviceVersion')
                    self.clientOSType = match.group('clientOSType')
                    self.clientOSVersion = match.group('clientOSVersion')
                    self.clientOSbuildNumber = match.group('clientOSbuildNumber')
                    self.protocolVersion = match.group('protocolVersion')
            self.logger.info("New {0} ({1}) on {2} version {3} build {4} connected using protocol version {5}".format(self.deviceType, self.deviceVersion, self.clientOSType, self.clientOSVersion, self.clientOSbuildNumber, self.protocolVersion))
            self.setRawMode()
        
    def rawDataReceived(self, data):
        self.rawData += data
        if not self.consumed_ace:
            if len(self.rawData) > 4:
                ace = self.rawData[:4]
                if ace != "\xaa\xcc\xee\x02":
                    self.output_buffer = "No stream start instruction found"
                    self.flush_output_buffer()
                    self.transport.loseConnection(failure.Failure(error.ConnectionDone('Other side is not conform to protocol.')))
                else:
                    self.output_buffer = "\xaa\xcc\xee\x02"
                    self.flush_output_buffer()
                self.rawData = self.rawData[4:]
                self.consumed_ace = True
            else:
                return
        self.process_compressed_data()
    
    def process_compressed_data(self):
        self.unzipped_input += self.decompressor.decompress(self.rawData)
        self.rawData = ""
        while self.hasNextObj():
            obj = self.read_next_object_from_unzipped()
            if type(obj) == Ping:
                self.received_ping(obj.num)
            if type(obj) == ServerObject:
                plist = biplist.readPlistFromString(obj.plist)
                self.received_plist(plist)
    
    def hasNextObj(self):
        if len(self.unzipped_input) == 0:
            return False
        if len(self.unzipped_input) < 5:
            return False
        
        cmd, data = struct.unpack('>BI', self.unzipped_input[:5])        
            
        if cmd in (3, 4): #ping pong
            return True
        if cmd == 2:
            return (len(self.unzipped_input) >= (data + 5))
    
    def read_next_object_from_unzipped(self):
        cmd, data = struct.unpack('>BI', self.unzipped_input[:5])
        if cmd == 3: #ping
            self.unzipped_input = self.unzipped_input[5:]
            return Ping(data)

        object_size = data
        object_data = self.unzipped_input[5:object_size + 5]
        self.unzipped_input = self.unzipped_input[object_size + 5:]
        return ServerObject(object_data)
    
    def send_object(self, obj):
        self.send_plist(obj.to_plist())

    def send_plist(self, plist):
        self.sendLock.acquire()
        self.logger.debug("Sending packet with class: {0}".format(plist['class']))
        self.logger.debug("packet with content:\n{0}".format(pprint.pformat(plist, width=40)))
        bplist = biplist.writePlistToString(plist);
        self.unzipped_output_buffer = struct.pack('>BI', 2, len(bplist)) + bplist
        self.flush_unzipped_output() 
        self.sendLock.release()
    
    def send_pong(self, idOfPong):
        self.sendLock.acquire()
        self.unzipped_output_buffer = struct.pack('>BI', 4, idOfPong)
        self.flush_unzipped_output() 
        self.sendLock.release()

    def flush_unzipped_output(self):
        self.output_buffer += self.compressor.compress(self.unzipped_output_buffer)
        #make sure everything is compressed
        self.output_buffer += self.compressor.flush(zlib.Z_SYNC_FLUSH)
        self.unzipped_output_buffer = ""
        self.flush_output_buffer()
        
    def flush_output_buffer(self):
        if len(self.output_buffer) > 0:
            self.transport.write(self.output_buffer)
            self.output_buffer = ""
 

########NEW FILE########
__FILENAME__ = SiriProtocolHandler
#!/usr/bin/python
# -*- coding: utf-8 -*-

from OpenSSL import crypto
from SiriCore import Siri
from db import Assistant
from httpClient import AsyncOpenHttp
from siriObjects.baseObjects import ObjectIsCommand, RequestCompleted
from siriObjects.speechObjects import Phrase, Recognition, SpeechRecognized, \
    Token, Interpretation, StartSpeech, SpeechFailure, StartSpeechRequest, \
    StartSpeechDictation, FinishSpeech, SpeechPacket
from siriObjects.systemObjects import StartRequest, SendCommands, CancelRequest, \
    CancelSucceeded, GetSessionCertificate, GetSessionCertificateResponse, \
    CreateSessionInfoRequest, CommandFailed, RollbackRequest, CreateAssistant, \
    AssistantCreated, SetAssistantData, LoadAssistant, AssistantNotFound, \
    AssistantLoaded, DestroyAssistant, AssistantDestroyed, CreateSessionInfoResponse
from siriObjects.uiObjects import UIAddViews, UIAssistantUtteranceView, UIButton
from siriObjects.syncObjects import SyncChunk, SyncChunkAccepted, SyncAnchor,\
    SyncChunkDenied
import PluginManager
import biplist
import flac
import json
import pprint
import speex
import sqlite3
import time
import twisted
import uuid

       

class SiriProtocolHandler(Siri):
    __not_recognized = {"de-DE": u"Entschuldigung, ich verstehe \"{0}\" nicht.", "en-US": u"Sorry I don't understand {0}", "fr-FR": u"Désolé je ne comprends pas ce que \"{0}\" veut dire.", "nl-NL": u"Excuses, \"{0}\" versta ik niet."}
    __websearch = {"de-DE": u"Websuche", "en-US": u"Websearch", "fr-FR": u"Rechercher sur le Web", "nl-NL": u"Zoeken op het web"}
    __scheduling_interval_timeout__ = 20
    __timeout_delay = 10
    
    def __init__(self, server, peer):
        Siri.__init__(self, server, peer)
        self.lastPing = 0
        self.pong = 0
        self.plugin_lastAceId = ""
        self.current_running_plugin = None
        self.dbConnection = server.dbConnection
        self.assistant = None
        self.speech = dict()
        self.httpClient = AsyncOpenHttp(self.handle_google_data)
        self.current_google_request = None
        self.current_location = None
        self.lastPingTime = time.time()
        self.syncAnchors = dict()
        self.timeoutschedule = twisted.internet.reactor.callLater(SiriProtocolHandler.__scheduling_interval_timeout__, self.checkTimeout)
        
    def seconds_since_last_ping(self):
        return time.time() - self.lastPingTime
    
    def connectionLost(self, reason):
        try:
            self.timeoutschedule.cancel()
        except:
            pass
        if self.current_google_request != None:
                self.current_google_request.cancel()
        #ensure all decoder/encoder attemps are closed
        for key in self.speech.keys():
            (decoder, encoder, _) = self.speech[key]
            if decoder:
                decoder.destroy()
            if encoder:
                encoder.finish()
                encoder.destroy()
        del self.speech
        self.current_running_plugin = None
        self.dbConnection = None
        self.httpClient = None
        Siri.connectionLost(self, reason)
    
    def checkTimeout(self):
        if self.seconds_since_last_ping() > SiriProtocolHandler.__timeout_delay:
            self.logger.info("Connection timed out")
            self.transport.loseConnection() 
        else:
            self.timeoutschedule = twisted.internet.reactor.callLater(SiriProtocolHandler.__scheduling_interval_timeout__, self.checkTimeout)  
    
    def handle_google_data(self, body, requestId, dictation):
        self.current_google_request = None
        if (body != None):
            googleAnswer = json.loads(body)
            for i in xrange(0,len(googleAnswer['hypotheses'])-1):
                utterance = googleAnswer['hypotheses'][i]['utterance']
                if len(utterance) == 1:
                    utterance = utterance.upper()
                else:
                    utterance = utterance[0].upper() + utterance[1:]
                googleAnswer['hypotheses'][i]['utterance'] = utterance
            self.process_recognized_speech(googleAnswer, requestId, dictation)
        else:
            self.send_object(SpeechFailure(requestId, "No connection to Google possible"))
            self.send_object(RequestCompleted(requestId))
        
    def received_ping(self, numOfPing):
        self.pong += 1
        self.lastPing = numOfPing
        self.lastPingTime = time.time()
        self.send_pong(self.pong)
        
    def process_recognized_speech(self, googleJson, requestId, dictation):
        possible_matches = googleJson['hypotheses']
        if len(possible_matches) > 0:
            best_match = possible_matches[0]['utterance']
            best_match_confidence = possible_matches[0]['confidence']
            self.logger.info(u"Best matching result: \"{0}\" with a confidence of {1}%".format(best_match, round(float(best_match_confidence) * 100, 2)))
            # construct a SpeechRecognized
            token = Token(best_match, 0, 0, 1000.0, True, True)
            interpretation = Interpretation([token])
            phrase = Phrase(lowConfidence=False, interpretations=[interpretation])
            recognition = Recognition([phrase])
            recognized = SpeechRecognized(requestId, recognition)
            
            if not dictation:
                if self.current_running_plugin == None:
                    plugin = PluginManager.getPluginForImmediateExecution(self.assistant.assistantId, best_match, self.assistant.language, (self.send_object, self.send_plist, self.assistant, self.current_location))
                    if plugin != None:
                        plugin.refId = requestId
                        plugin.connection = self
                        self.current_running_plugin = plugin
                        self.send_object(recognized)
                        self.current_running_plugin.start()
                    else:
                        self.send_object(recognized)
                        view = UIAddViews(requestId)
                        errorText = SiriProtocolHandler.__not_recognized[self.assistant.language] if self.assistant.language in SiriProtocolHandler.__not_recognized else SiriProtocolHandler.__not_recognized["en-US"]
                        errorView = UIAssistantUtteranceView()
                        errorView.text = errorText.format(best_match)
                        errorView.speakableText = errorText.format(best_match)
                        view.views = [errorView]
                        websearchText = SiriProtocolHandler.__websearch[self.assistant.language] if self.assistant.language in SiriProtocolHandler.__websearch else SiriProtocolHandler.__websearch["en-US"]
                        button = UIButton()
                        button.text = websearchText
                        cmd = SendCommands()
                        cmd.commands = [StartRequest(utterance=u"^webSearchQuery^=^{0}^^webSearchConfirmation^=^Yes^".format(best_match))]
                        button.commands = [cmd]
                        view.views.append(button)
                        self.send_object(view)
                        self.send_object(RequestCompleted(requestId))
                elif self.current_running_plugin.waitForResponse != None:
                    # do we need to send a speech recognized here? i.d.k
                    self.current_running_plugin.response = best_match
                    self.current_running_plugin.refId = requestId
                    self.current_running_plugin.waitForResponse.set()
                else:
                    self.send_object(recognized)
                    self.send_object(RequestCompleted(requestId))
            else:
                self.send_object(recognized)
                self.send_object(RequestCompleted(requestId))
    
    def received_plist(self, plist):
        self.logger.debug("Got packet with class: {0}".format(plist['class']))
        self.logger.debug("packet with content:\n{0}".format(pprint.pformat(plist, width=40)))
        
        # first handle speech stuff
        
        if 'refId' in plist:
            # if the following holds, this packet is an answer to a request by a plugin
            if plist['refId'] == self.plugin_lastAceId and self.current_running_plugin != None:
                if self.current_running_plugin.waitForResponse != None:
                    # just forward the object to the 
                    # don't change it's refId, further requests must reference last FinishSpeech
                    self.logger.debug("Forwarding object to plugin")
                    self.plugin_lastAceId = None
                    self.current_running_plugin.response = plist if plist['class'] != "StartRequest" else plist['properties']['utterance']
                    self.current_running_plugin.waitForResponse.set()
                    return
        
        if ObjectIsCommand(plist, StartSpeechRequest) or ObjectIsCommand(plist, StartSpeechDictation):
            self.logger.debug("New start of speech received")
            startSpeech = None
            if ObjectIsCommand(plist, StartSpeechDictation):
                dictation = True
                startSpeech = StartSpeechDictation(plist)
            else:
                dictation = False
                startSpeech = StartSpeechRequest(plist)
    
            decoder = speex.Decoder()
            encoder = flac.Encoder()
            speexUsed = False
            if startSpeech.codec == StartSpeech.CodecSpeex_WB_Quality8Value:
                decoder.initialize(mode=speex.SPEEX_MODEID_WB)
                encoder.initialize(16000, 1, 16)
                speexUsed = True
            elif startSpeech.codec == StartSpeech.CodecSpeex_NB_Quality7Value:
                decoder.initialize(mode=speex.SPEEX_MODEID_NB)
                encoder.initialize(16000, 1, 16)
                speexUsed = True
            elif startSpeech.codec == StartSpeech.CodecPCM_Mono_16Bit_8000HzValue:
                encoder.initialize(8000, 1, 16)
            elif startSpeech.codec == StartSpeech.CodecPCM_Mono_16Bit_11025HzValue:
                encoder.initialize(11025, 1, 16)
            elif startSpeech.coded == StartSpeech.CodecPCM_Mono_16Bit_16000HzValue:
                encoder.initialize(16000, 1, 16)
            elif startSpeech.coded == StartSpeech.CodecPCM_Mono_16Bit_22050HzValue:
                encoder.initialize(22050, 1, 16)
            elif startSpeech.coded == StartSpeech.CodecPCM_Mono_16Bit_32000HzValue:
                encoder.initialize(32000, 1, 16)
            # we probably need resampling for sample rates other than 16kHz...
            
            self.speech[startSpeech.aceId] = (decoder if speexUsed else None, encoder, dictation)
        
        elif ObjectIsCommand(plist, SpeechPacket):
            self.logger.debug("Decoding speech packet")
            speechPacket = SpeechPacket(plist)
            if speechPacket.refId in self.speech:
                (decoder, encoder, dictation) = self.speech[speechPacket.refId]
                if decoder:
                    pcm = decoder.decode(speechPacket.packets)
                else:
                    pcm = SpeechPacket.data # <- probably data... if pcm
                encoder.encode(pcm)
            else:
                self.logger.debug("Got a speech packet that did not match any current request")
                
        elif plist['class'] == 'StartCorrectedSpeechRequest':
            self.process_recognized_speech({u'hypotheses': [{'confidence': 1.0, 'utterance': plist['properties']['utterance']}]}, plist['aceId'], False)
    
        elif ObjectIsCommand(plist, FinishSpeech):
            self.logger.debug("End of speech received")
            finishSpeech = FinishSpeech(plist)
            if finishSpeech.refId in self.speech:
                (decoder, encoder, dictation) = self.speech[finishSpeech.refId]
                if decoder:
                    decoder.destroy()
                flacBin = None
                if encoder:
                    encoder.finish()
                    flacBin = encoder.getBinary()
                    encoder.destroy()
                del self.speech[finishSpeech.refId]
                if flacBin != None:
                    self.logger.info("Sending flac to google for recognition")
                    try:
                        self.current_google_request = self.httpClient.make_google_request(flacBin, finishSpeech.refId, dictation, language=self.assistant.language, allowCurses=True)
                    except (AttributeError, TypeError):
                        self.logger.warning("Unable to find language record for this assistant. Try turning Siri off and then back on.")
                else:
                    self.logger.info("There was no speech")
            else:
                self.logger.debug("Got a finish speech packet that did not match any current request")
                
        elif ObjectIsCommand(plist, CancelRequest):
            # this is probably called when we need to kill a plugin
            # wait for thread to finish a send
            self.logger.debug("Should cancel current request")
            cancelRequest = CancelRequest(plist)
            if cancelRequest.refId in self.speech:
                (decoder, encoder, dictation) = self.speech[cancelRequest.refId]
                if decoder:
                    decoder.destroy()
                if encoder:
                    encoder.finish()
                    encoder.destroy()
                del self.speech[cancelRequest.refId]
            if self.current_google_request != None:
                self.current_google_request.cancel()
                # if a google request is running (follow up listening..., plugin might get killed there by user)
                if self.current_running_plugin != None:
                    if self.current_running_plugin.waitForResponse != None:
                        self.current_running_plugin._abortPluginRun()
                        self.current_running_plugin.waitForResponse.set()
                        
            # if a plugin is running (processing, but not waiting for data from the device we kill it)   
            if self.current_running_plugin != None:
                if self.current_running_plugin.waitForResponse == None:
                    self.current_running_plugin._abortPluginRun()     
            
            self.send_object(CancelSucceeded(cancelRequest.aceId))
            
        elif ObjectIsCommand(plist, RollbackRequest):
            pass
        
        elif ObjectIsCommand(plist, SyncChunk):
            chunk = SyncChunk(plist)
            previous = self.syncAnchors[chunk.key] if chunk.key in self.syncAnchors else None
            if previous != None:
                if previous.generation != chunk.preGen:
                    chunkDenied = SyncChunkDenied(chunk.aceId)
                    self.send_object(chunkDenied)
                    return 
            current = SyncAnchor()
            current.generation = chunk.postGen
            current.value = chunk.postGen
            current.validity = chunk.validity
            current.key = chunk.key
            self.syncAnchors[current.key] = current
            chunkAccepted = SyncChunkAccepted(chunk.aceId)
            chunkAccepted.current = current
            self.send_object(chunkAccepted)
            pass

        elif ObjectIsCommand(plist, GetSessionCertificate):
            getSessionCertificate = GetSessionCertificate(plist)
            sessionCA_DER = crypto.dump_certificate(crypto.FILETYPE_ASN1, self.server.sessionCACert)
            sessionCert_DER = crypto.dump_certificate(crypto.FILETYPE_ASN1, self.server.sessionCert)
            response = GetSessionCertificateResponse(getSessionCertificate.aceId, sessionCA_DER, sessionCert_DER)
            self.send_object(response)

        elif ObjectIsCommand(plist, CreateSessionInfoRequest):
            # how does a positive answer look like?
            createSessionInfoRequest = CreateSessionInfoRequest(plist)
            
            #success = CreateSessionInfoResponse(createSessionInfoRequest.aceId)
            #success.sessionInfo = biplist.Data("\x01\x02BLABLABLBALBALBALBALBALBALBALBA")
            #success.validityDuration = 9600
            
            #self.send_object(success)
            fail = CommandFailed(createSessionInfoRequest.aceId)
            fail.reason = "Not authenticated"
            fail.errorCode = 0
            self.send_object(fail)

            ##self.send_plist({"class":"SessionValidationFailed", "properties":{"errorCode":"UnsupportedHardwareVersion"}, "aceId": str(uuid.uuid4()), "refId":plist['aceId'], "group":"com.apple.ace.system"})
            
        elif ObjectIsCommand(plist, CreateAssistant):
            createAssistant = CreateAssistant(plist)
            #create a new assistant
            helper = Assistant()     
            helper.assistantId = str.upper(str(uuid.uuid4()))
            helper.language = createAssistant.language
            helper.activationToken = createAssistant.activationToken
            helper.connectionType = createAssistant.connectionType
            helper.validationData = createAssistant.validationData
            c = self.dbConnection.cursor()
            noError = True
            try:
                c.execute("insert into assistants(assistantId, assistant) values (?,?)", (helper.assistantId, helper))
                self.dbConnection.commit()
            except sqlite3.Error: 
                noError = False
            c.close()
            if noError:
                self.assistant = helper
                assiCreatedCMD = AssistantCreated(createAssistant.aceId)
                assiCreatedCMD.assistantId = helper.assistantId
                assiCreatedCMD.speechId = str(uuid.uuid4())
                self.send_object(assiCreatedCMD)
            else:
                cmdFailed = CommandFailed(createAssistant.aceId)
                cmdFailed.reason = "Database Error"
                cmdFailed.errorCode = 2
                self.send_object(cmdFailed)
            
        elif ObjectIsCommand(plist, SetAssistantData):
            setAssistantData = SetAssistantData(plist)
            # fill assistant 
            if self.assistant != None:
                try:
                    c = self.dbConnection.cursor()
                    assi_id = self.assistant.assistantId
                    self.assistant.initializeFromPlist(setAssistantData.to_plist())
                    self.assistant.assistantId = assi_id
                    #Record the user firstName and nickName                    
                    try:                        
                        self.assistant.firstName = self.assistant.meCards[0].firstName.encode("utf-8")
                    except:
                        self.assistant.firstName = u''                        
                    try:                        
                        self.assistant.nickName = self.assistant.meCards[0].nickName.encode("utf-8")       
                    except:
                        self.assistant.nickName = u''
                    #Done recording
                    c.execute("update assistants set assistant = ? where assistantId = ?", (self.assistant, self.assistant.assistantId))
                    self.dbConnection.commit()
                    c.close()
                except:
                    cmdFailed = CommandFailed(setAssistantData.aceId)
                    cmdFailed.reason = "Database Error"
                    cmdFailed.errorCode = 2
                    self.send_object(cmdFailed)
                    self.logger.exception("Database Error on setting assistant data")
            else:
                cmdFailed = CommandFailed(setAssistantData.aceId)
                cmdFailed.reason = "Assistant to set data not found"
                cmdFailed.errorCode = 2
                self.send_object(cmdFailed)
                self.logger.warning("Trying to set assistant data without having a valid assistant")
                
        elif ObjectIsCommand(plist, LoadAssistant):
            loadAssistant = LoadAssistant(plist)
            try:
                c = self.dbConnection.cursor()
                c.execute("select assistant from assistants where assistantId = ?", (loadAssistant.assistantId,))
                self.dbConnection.commit()
                result = c.fetchone()
                if result == None:
                    self.send_object(AssistantNotFound(loadAssistant.aceId))
                    self.logger.warning("Assistant not found in database!!")                        
                else:
                    self.assistant = result[0]
                    #update assistant from LoadAssistant
                    self.assistant.language = loadAssistant.language
                    self.assistant.connectionType = loadAssistant.connectionType
                    
                    if self.assistant.language == '' or self.assistant.language == None:
                        self.logger.error ("No language is set for this assistant")                        
                        c.execute("delete from assistants where assistantId = ?", (plist['properties']['assistantId'],))
                        self.dbConnection.commit()
                        cmdFailed = CommandFailed(loadAssistant.aceId)
                        cmdFailed.reason = "Database error Assistant not found or language settings"
                        cmdFailed.errorCode = 2
                        self.send_object(cmdFailed)
                    else:                        
                        loaded = AssistantLoaded(loadAssistant.aceId)
                        loaded.version = "20111216-32234-branches/telluride?cnxn=293552c2-8e11-4920-9131-5f5651ce244e"
                        loaded.requestSync = 0
                        try:
                            loaded.dataAnchor = self.assistant.anchor
                        except:
                            loaded.dataAnchor = "removed"
                        self.send_object(loaded)
                c.close()
            except:
                self.send_object(AssistantNotFound(loadAssistant.aceId))
                self.logger.warning("Database error on fetching assistant")
                
        elif ObjectIsCommand(plist, DestroyAssistant):
            destroyAssistant = DestroyAssistant(plist)
            try:
                c = self.dbConnection.cursor()
                c.execute("delete from assistants where assistantId = ?", (plist['properties']['assistantId'],))
                self.dbConnection.commit()
                c.close()
                destroyed = AssistantDestroyed(destroyAssistant.aceId)
                destroyed.assistantId = destroyAssistant.assistantId
                self.send_object(destroyed)
            except:
                self.send_object(AssistantNotFound(destroyAssistant.aceId))
                self.logger.error("Database error on deleting assistant")
                
        elif ObjectIsCommand(plist, StartRequest):
            startRequest = StartRequest(plist)
            #this should also be handeled by special plugins, so lets call the plugin handling stuff
            self.process_recognized_speech({'hypotheses': [{'utterance': startRequest.utterance, 'confidence': 1.0}]}, startRequest.aceId, False)
        pass

########NEW FILE########
__FILENAME__ = SiriServer
#!/usr/bin/python
# -*- coding: utf-8 -*-
from SiriProtocolHandler import SiriProtocolHandler
from optparse import OptionParser
from os.path import exists
from socket import gethostname
from twisted.internet.protocol import Protocol
import PluginManager
import db
import logging
import sys


try:    
    from twisted.internet import ssl
    from twisted.internet.protocol import Factory
except ImportError:
    print "You need to install the twisted python libraries (http://twistedmatrix.com/trac/)\n"
    print "On a debian based system try installing python-twisted\n"
    print "On other systems, you may use easy_install or other package managers\n"
    print "Please refer to the website listed above for further installation instructions\n"
    exit(-1)
    
    
try:       
    from OpenSSL import crypto
except:
    print "You need to install the python OpenSSL module (http://packages.python.org/pyOpenSSL/openssl.html)\n"
    print "On a debian based system try installing python-openssl\n"
    print "On other systems, you may use easy_install or a package manager available there\n"
    print "Please refer to the website listed above for further installation instructions\n"
    exit(-1)
    


log_levels = {'debug':logging.DEBUG,
              'info':logging.INFO,
              'warning':logging.WARNING,
              'error':logging.ERROR,
              'critical':logging.CRITICAL
              }
       
class RejectHandler(Protocol):
    def makeConnection(self, transport):
        transport.loseConnection()
        return
    

class SiriFactory(Factory):

    def __init__(self, maxConnections):
        self.numberOfConnections = 0
        self.maxConnections = maxConnections
        self.sessionCert = None
        self.sessionCACert = None
        self.dbConnection = None
        
    def buildProtocol(self, addr):
        if self.maxConnections == None:
            return SiriProtocolHandler(self, addr)
        elif self.numberOfConnections < self.maxConnections:
            return SiriProtocolHandler(self, addr)
        else:
            return RejectHandler()
    
    def startFactory(self):
        logging.getLogger().info("Loading Session Certificates")
        caFile = open("keys/SessionCACert.pem")
        self.sessionCACert = crypto.load_certificate(crypto.FILETYPE_PEM,caFile.read())
        caFile.close()
        sessionCertFile = open("keys/SessionCert.pem")
        self.sessionCert = crypto.load_certificate(crypto.FILETYPE_PEM, sessionCertFile.read())
        sessionCertFile.close() 
        logging.getLogger().info("Setting Up Database")
        db.setup()
        logging.getLogger().info("Connection to Database")
        self.dbConnection = db.getConnection()
        logging.getLogger().info("Loading Plugin Framework")
        PluginManager.load_api_keys()
        PluginManager.load_plugins()
        logging.getLogger().info("Server is running and listening for connections")
        
    def stopFactory(self):
        logging.getLogger().info("Server is shutting down")
        self.dbConnection.close()
        logging.getLogger().info("Database Connection Closed")
        
        


ROOT_CA_CERT_FILE = "keys/ca.pem"
ROOT_CA_KEY_FILE = "keys/cakey.pem"
SERVER_CERT_FILE = "keys/server.crt"
SERVER_KEY_FILE = "keys/server.key"

def create_self_signed_cert():
    
    if not exists(SERVER_CERT_FILE) or not exists(SERVER_KEY_FILE) or not exists(ROOT_CA_CERT_FILE):

        print "I could not find valid certificates. I will now guide you through the process of creating some."
        
        print "I will create a Certification Authority (CA) first"
        # create a key pair
        ca_key = crypto.PKey()
        ca_key.generate_key(crypto.TYPE_RSA, 2048)

        # create a self-signed cert
        CAcert = crypto.X509()
        CAcert.get_subject().C = "DE"
        CAcert.get_subject().ST = "NRW"
        CAcert.get_subject().L = "Aachen"
        CAcert.get_subject().O = "SiriServer by Eichhoernchen"
        CAcert.get_subject().OU = "SiriServer Certificate Authority"
        CAcert.get_subject().CN = "SiriServer Fake CA Certificate"
        CAcert.set_serial_number(1000)
        CAcert.gmtime_adj_notBefore(0)
        CAcert.gmtime_adj_notAfter(10*365*24*60*60)
        CAcert.set_issuer(CAcert.get_subject())
        CAcert.set_pubkey(ca_key)
        
        extensions = []
        crypto.X509ExtensionType
        extensions.append(crypto.X509Extension("basicConstraints", critical=False, value="CA:TRUE"))
        extensions.append(crypto.X509Extension("subjectKeyIdentifier", critical=False, value="hash", subject=CAcert))
        CAcert.add_extensions(extensions)
        # we need to set this separatly... don't know why...
        CAcert.add_extensions([crypto.X509Extension("authorityKeyIdentifier", critical=False, value="keyid:always", issuer=CAcert)])
        CAcert.sign(ca_key, 'sha1')
        fhandle = open(ROOT_CA_CERT_FILE, "wb")
        fhandle.write(
            crypto.dump_certificate(crypto.FILETYPE_PEM, CAcert)
            )
        fhandle.close()
        fhandle = open(ROOT_CA_KEY_FILE, "wb")
        fhandle.write(
            crypto.dump_privatekey(crypto.FILETYPE_PEM, ca_key)
            )
        fhandle.close()
        
        print "I successfully created a CA for you, will now use it to create SSL certificates."
        # create a key pair
        k2 = crypto.PKey()
        k2.generate_key(crypto.TYPE_RSA, 2048)

        # create a self-signed cert
        cert = crypto.X509()
        cert.get_subject().C = "DE"
        cert.get_subject().ST = "NRW"
        cert.get_subject().L = "Aachen"
        cert.get_subject().O = "SiriServer by Eichhoernchen"
        cert.get_subject().OU = "SiriServer Certificate Authority"
        
        hostname = gethostname()
        print "We need to set the correct address of this machine in the certificate."
        print "I will now query your system for its name. But it might be that you want to use a DNS name I cannot find.\n"
        print "-------- IMPORTANT ----------"
        print "Your system tells me that your hostname/IP is: {0}".format(hostname)
        sys.stdout.write("Do you want to use this information (y/n): ")
        answer = sys.stdin.readline().lower()
        if "no" in answer or "n" in answer:
            sys.stdout.write("Okay what do you want the hostname to be: ")
            hostname = sys.stdin.readline().strip()
            print "Okay thanks I will now be using {0}".format(hostname)
            
        cert.get_subject().CN = hostname
        cert.set_serial_number(1000)
        cert.gmtime_adj_notBefore(0)
        cert.gmtime_adj_notAfter(10*365*24*60*60)
        cert.set_issuer(CAcert.get_subject())
        cert.set_pubkey(k2)
        
        extensions = []
        crypto.X509ExtensionType
        extensions.append(crypto.X509Extension("basicConstraints", critical=False, value="CA:FALSE"))
        extensions.append(crypto.X509Extension("subjectKeyIdentifier", critical=False, value="hash", subject=cert))
        extensions.append(crypto.X509Extension("authorityKeyIdentifier", critical=False, value="keyid:always", subject=CAcert, issuer=CAcert))
        cert.add_extensions(extensions)
        
        cert.sign(ca_key, 'sha1')
        fhandle = open(SERVER_CERT_FILE, "wb")
        fhandle.write(
            crypto.dump_certificate(crypto.FILETYPE_PEM, cert)
            )
        fhandle.close()
        fhandle = open(SERVER_KEY_FILE, "wb")
        fhandle.write(
            crypto.dump_privatekey(crypto.FILETYPE_PEM, k2)
            )
        fhandle.close()
        
        print """
        \t\t\t ------------ IMPORTANT ------------\n\n
        \t\tAll certificates have been generated... You must now install the CA certificate on your device\n\n
        \t\tThe file is located at keys/ca.pem in your SiriServer root\n\n
        \t\tMake sure to uninstall an old CA certificate first"\n\n
        \t\tTHE CERTIFICATES MUST MATCH! IF YOU DID THIS HERE BEFORE, THE OLD ca.pem WON'T WORK ANYMORE\n
        \t\tYou can just EMail the keys/ca.pem file to yourself\n
        """
    
        
def main():
    
    parser = OptionParser()
    parser.add_option('-l', '--loglevel', default='info', dest='logLevel', help='This sets the logging level you have these options: debug, info, warning, error, critical \t\tThe standard value is info')
    parser.add_option('-p', '--port', default=4443, type='int', dest='port', help='This options lets you use a custom port instead of 443 (use a port > 1024 to run as non root user)')
    parser.add_option('--logfile', default=None, dest='logfile', help='Log to a file instead of stdout.')
    parser.add_option('-m', '--maxConnections', default=None, type='int', dest='maxConnections', help='You can limit the number of maximum simultaneous connections with that switch')
    parser.add_option('-n', '--noSSL', action="store_true", default=False, dest='sslDisabled', help='You can switch off SSL with this switch.')
    (options, _) = parser.parse_args()
    
    x = logging.getLogger()
    x.setLevel(log_levels[options.logLevel])
    
    if options.logfile != None:
        h = logging.FileHandler(options.logfile)
    else:
        h = logging.StreamHandler()
    
    f = logging.Formatter(u"%(levelname)s %(message)s")
    h.setFormatter(f)
    x.addHandler(h)
    
    if not options.sslDisabled:
        create_self_signed_cert()
    
    try: 
        from twisted.internet import epollreactor
        epollreactor.install()
    except ImportError:
        x.debug("System does not support epoll")
        x.debug("-> Will use simple poll")
        try:
            from twisted.internet import pollreactor
            pollreactor.install()
        except ImportError:
            x.debug("System does not support poll")
            x.debug("-> Will use default select interface")
    from twisted.internet import reactor

    
    x.info("Starting server on port {0}".format(options.port))
    if options.sslDisabled:
        x.warning("Starting, as requested, without SSL, connections are not secured and can be altered and eavesdropped on from client to server")
        reactor.listenTCP(options.port, SiriFactory(options.maxConnections))
    else:
        reactor.listenSSL(options.port, SiriFactory(options.maxConnections), ssl.DefaultOpenSSLContextFactory(SERVER_KEY_FILE, SERVER_CERT_FILE))
    reactor.run()
    x.info("Server shutdown complete")
    
if __name__ == "__main__":
    main()

########NEW FILE########
__FILENAME__ = speex
from ctypes import *
import sys
import platform
import ctypes.util

system = platform.system()

libspeex_name = ctypes.util.find_library('speex')
if libspeex_name == None:
    print "Could not find libspeex"
    exit()
libspeex = CDLL(libspeex_name)

#defines copied from: http://speex.org/docs/api/speex-api-reference/group__Codec.html
SPEEX_SET_ENH = 0                   #Set enhancement on/off (decoder only)
SPEEX_GET_ENH = 1                   #Get enhancement state (decoder only)
SPEEX_GET_FRAME_SIZE = 3            #Obtain frame size used by encoder/decoder
SPEEX_SET_QUALITY = 4               #Set quality value
SPEEX_SET_MODE = 6                  #Set sub-mode to use
SPEEX_GET_MODE = 7                  #Get current sub-mode in use
SPEEX_SET_LOW_MODE = 8              #Set low-band sub-mode to use (wideband only)
SPEEX_GET_LOW_MODE = 9              #Get current low-band mode in use (wideband only)
SPEEX_SET_HIGH_MODE = 10            #Set high-band sub-mode to use (wideband only)
SPEEX_GET_HIGH_MODE = 11            #Get current high-band mode in use (wideband only)
SPEEX_SET_VBR = 12                  #Set VBR on (1) or off (0)
SPEEX_GET_VBR = 13                  #Get VBR status (1 for on, 0 for off)
SPEEX_SET_VBR_QUALITY = 14          #Set quality value for VBR encoding (0-10)
SPEEX_GET_VBR_QUALITY = 15          #Get current quality value for VBR encoding (0-10)
SPEEX_SET_COMPLEXITY = 16           #Set complexity of the encoder (0-10)
SPEEX_GET_COMPLEXITY = 17           #Get current complexity of the encoder (0-10)
SPEEX_SET_BITRATE = 18              #Set bit-rate used by the encoder (or lower)
SPEEX_GET_BITRATE = 19              #Get current bit-rate used by the encoder or decoder
SPEEX_SET_HANDLER = 20              #Define a handler function for in-band Speex request
SPEEX_SET_USER_HANDLER = 22         #Define a handler function for in-band user-defined request
SPEEX_SET_SAMPLING_RATE = 24        #Set sampling rate used in bit-rate computation
SPEEX_GET_SAMPLING_RATE = 25        #Get sampling rate used in bit-rate computation
SPEEX_RESET_STATE = 26              #Reset the encoder/decoder memories to zero
SPEEX_GET_RELATIVE_QUALITY = 29     #Get VBR info (mostly used internally)
SPEEX_SET_VAD = 30                  #Set VAD status (1 for on, 0 for off)
SPEEX_GET_VAD = 31                  #Get VAD status (1 for on, 0 for off)
SPEEX_SET_ABR = 32                  #Set Average Bit-Rate (ABR) to n bits per seconds
SPEEX_GET_ABR = 33                  #Get Average Bit-Rate (ABR) setting (in bps)
SPEEX_SET_DTX = 34                  #Set DTX status (1 for on, 0 for off)
SPEEX_GET_DTX = 35                  #Get DTX status (1 for on, 0 for off)
SPEEX_SET_SUBMODE_ENCODING = 36     #Set submode encoding in each frame (1 for yes, 0 for no, setting to no breaks the standard)
SPEEX_GET_SUBMODE_ENCODING = 37     #Get submode encoding in each frame
SPEEX_GET_LOOKAHEAD = 39            #Returns the lookahead used by Speex
SPEEX_SET_PLC_TUNING = 40           #Sets tuning for packet-loss concealment (expected loss rate)
SPEEX_GET_PLC_TUNING = 41           #Gets tuning for PLC
SPEEX_SET_VBR_MAX_BITRATE = 42      #Sets the max bit-rate allowed in VBR mode
SPEEX_GET_VBR_MAX_BITRATE = 43      #Gets the max bit-rate allowed in VBR mode
SPEEX_SET_HIGHPASS = 44             #Turn on/off input/output high-pass filtering
SPEEX_GET_HIGHPASS = 45             #Get status of input/output high-pass filtering
SPEEX_GET_ACTIVITY = 47             #Get "activity level" of the last decoded frame, i.e. how much damage we cause if we remove the frame
SPEEX_SET_PF = 0                    #Equivalent to SPEEX_SET_ENH
SPEEX_GET_PF = 1                    #Equivalent to SPEEX_GET_ENH
SPEEX_MODE_FRAME_SIZE = 0           #Query the frame size of a mode
SPEEX_SUBMODE_BITS_PER_FRAME = 1    #Query the size of an encoded frame for a particular sub-mode
SPEEX_LIB_GET_MAJOR_VERSION = 1     #Get major Speex version
SPEEX_LIB_GET_MINOR_VERSION = 3     #Get minor Speex version
SPEEX_LIB_GET_MICRO_VERSION = 5     #Get micro Speex version
SPEEX_LIB_GET_EXTRA_VERSION = 7     #Get extra Speex version
SPEEX_LIB_GET_VERSION_STRING = 9    #Get Speex version string
SPEEX_NB_MODES = 3                  #Number of defined modes in Speex

                                    #Encoding/Decoding Modes:
SPEEX_MODEID_NB = 0                 #modeID for the defined narrowband mode
SPEEX_MODEID_WB = 1                 #modeID for the defined wideband mode
SPEEX_MODEID_UWB = 2                #modeID for the defined ultra-wideband mode

class SpeexBits(Structure):
    _fields_ = [('chars', c_char_p)
                , ('nbBits', c_int)
                , ('charPtr', c_int)
                , ('bitPtr', c_int)
                , ('owner', c_int)
                , ('overflow', c_int)
                , ('buf_size', c_int)
                , ('reserved1', c_int)
                , ('reserved2', c_void_p)
                ]


class Decoder:
    
    def __init__(self):
        self.state = None
        self.frame_size = None
        self.bits = None
        
    def initialize(self, mode=SPEEX_MODEID_UWB):
        libspeex.speex_decoder_init.restype = c_void_p
        libspeex.speex_decoder_init.argtypes = [c_void_p]
        libspeex.speex_decode_int.restype = c_int
        libspeex.speex_decode_int.argtypes = [c_void_p, POINTER(SpeexBits), POINTER(c_int16)]
        libspeex.speex_bits_read_from.argtypes = [POINTER(SpeexBits), c_char_p, c_int]
        libspeex.speex_bits_destroy.argtypes = [POINTER(SpeexBits)]
        libspeex.speex_decoder_destroy.argtypes = [c_void_p]
        libspeex.speex_decoder_ctl.argtypes = [c_void_p, c_int, c_void_p]
        
        
        self.state = libspeex.speex_decoder_init(libspeex.speex_wb_mode)
        self.frame_size = c_int()
        result = libspeex.speex_decoder_ctl(self.state, SPEEX_GET_FRAME_SIZE, byref(self.frame_size));

        self.bits = SpeexBits()
        libspeex.speex_bits_init(byref(self.bits)) 

    def decode(self, data):
        self.buffer = create_string_buffer(1024)
        decoded_frame = (c_int16*self.frame_size.value)()
        
        out = ""
        for i in range(0,len(data)):
            self.buffer = data[i]
            libspeex.speex_bits_read_from(byref(self.bits), self.buffer, len(data[i]))
            while libspeex.speex_decode_int(self.state, byref(self.bits), decoded_frame) == 0:
                out += string_at(decoded_frame, self.frame_size.value*2)
        return out

    def destroy(self):
        if self.state:
            libspeex.speex_bits_destroy(byref(self.bits))
            libspeex.speex_decoder_destroy(self.state)
            self.state = None

########NEW FILE########
