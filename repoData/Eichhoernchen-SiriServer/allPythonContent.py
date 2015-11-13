__FILENAME__ = db
#!/usr/bin/python
# -*- coding: utf-8 -*-

import cPickle
import sqlite3
from uuid import uuid4


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
    return sqlite3.connect(__database__, detect_types=sqlite3.PARSE_DECLTYPES)


class Assistant(object):
    def __init__(self, assistantId=str.upper(str(uuid4()))):
        self.assistantId = assistantId
        self.censorspeech = None
        self.timeZoneId = None
        self.language = None
        self.region = None


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
import struct
import tempfile
import os

libflac_name = ctypes.util.find_library('FLAC')
if libflac_name == None:
    print "Could not find libFLAC"
    exit()
libflac = CDLL(libflac_name)


def writeCallBack(encoder, buffer, bytes, samples, current_frame, client_data):
    print "Test"
    instance = cast(client_data, py_object).value
    return Encoder.internalCallBack(instance, encoder, buffer, bytes, samples, current_frame)



class Encoder:

    
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
        file = tempfile.NamedTemporaryFile(delete=False)
        file.close()
        self.filename = file.name
        libflac.FLAC__stream_encoder_init_file(self.encoder, self.filename, None, None)
        if not ok:
            print "Error initializing libflac"
            exit()
    
    def internalCallBack(self, encoder, buffer, bytes, samples, current_frame):
        self.output += string_at(buffer, bytes)
        print self.output
        return 0
    


    def encode(self, data):
        length = int(len(data)/2)
        int16s = struct.unpack('<' + ('h'*length), data)
        int32s = (c_int32*len(int16s))(*int16s)
        libflac.FLAC__stream_encoder_process_interleaved(self.encoder, int32s, length)

    def getBinary(self):
        f = open(self.filename, 'r')
        flac = f.read()
        f.close()
        return flac
        
    def finish(self):
        libflac.FLAC__stream_encoder_finish(self.encoder)
    
    def destroy(self):
        libflac.FLAC__stream_encoder_delete(self.encoder)
        os.unlink(self.filename)

########NEW FILE########
__FILENAME__ = httpClient
import threading, urllib2

class AsyncOpenHttp(threading.Thread):
    def __init__(self, successCallback, errorCallback):
        super(AsyncOpenHttp, self).__init__()
        self.successCallback = successCallback
        self.errorCallback = errorCallback
        self.finished = True
    
    def make_google_request(self, flac, requestId, dictation, language="de-DE", allowCurses=True):
        if self.finished:
            self.currentFlac = flac
            self.requestId = requestId
            self.dictation = dictation
            self.language = language
            self.allowCurses = allowCurses
            self.finished = False
            self.run()
    
    def run(self):
        # of course change urllib to httplib-something-something
        url = "https://www.google.com/speech-api/v1/recognize?xjerr=1&client=chromium&pfilter={0}&lang={1}&maxresults=6".format(0 if self.allowCurses else 2, self.language)
        req = urllib2.Request(url, data = self.currentFlac, headers = {'Content-Type': 'audio/x-flac; rate=16000', 'User-Agent': 'Siri-Server'})
        try:
            content  = urllib2.urlopen(req, timeout=3).read()
            self.finished = True
            self.successCallback(content, self.requestId, self.dictation)
        except:
            self.finished = True
            self.errorCallback(self.requestId, self.dictation)

########NEW FILE########
__FILENAME__ = plugin
#!/usr/bin/python
# -*- coding: utf-8 -*-



import re
import threading
import logging
import PluginManager
import inspect


from siriObjects.baseObjects import ClientBoundCommand, RequestCompleted
from siriObjects.uiObjects import AddViews, AssistantUtteranceView, OpenLink, Button
from siriObjects.systemObjects import GetRequestOrigin, SetRequestOrigin

__criteria_key__ = "criterias"


__error_responses__ = {"de-DE": "Es ist ein Fehler in der Verarbeitung ihrer Anfrage aufgetreten!", "en-US": "There was an error during the processing of your request!", "en-GB": "There was an error during the processing of your request!", "en-AU": "There was an error during the processing of your request!", "fr-FR": "Il y avait une erreur lors du traitement de votre demande!"}

__error_location_help__ = {"de-DE": u"Ich weiß nicht wo du bist… Aber du kannst mir helfen es heraus zu finden…", "en-US": u"I don’t know where you are… But you can help me find out…", "en-GB": u"I don’t know where you are… But you can help me find out…", "en-AU": u"I don’t know where you are… But you can help me find out…", "fr-FR": u"Je ne sais pas où vous êtes ... Mais vous pouvez m'aider à en savoir plus sur ..."}

__error_location_saysettings__ = {"de-DE": u"In den Ortungsdienst Einstellungen, schalte Ortungsdienst und Siri ein.", "en-US": u"In Location Services Settings, turn on both Location Services and Siri.", "en-GB": u"In Location Services Settings, turn on both Location Services and Siri.", "en-AU": u"In Location Services Settings, turn on both Location Services and Siri.", "fr-FR": u"Dans les paramètres de service de localisation, activez les services de localisation et Siri."}

__error_location_settings__ = {"de-DE": u"Ortungsdienst Einstellungen", "en-US": u"Location Services Settings", "en-GB": u"Location Services Settings", "en-AU": u"Location Services Settings", "fr-FR": u"Services de localisation"}



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
        self.logger = logging.getLogger("logger")
        self.__priority = False
    
    def initialize(self, method, speech, language, send_object, send_plist, assistant, location):
        super(Plugin, self).__init__()
        self.__method = method
        self.__lang = language
        self.__speech = speech
        self.__send_plist = send_plist
        self.__send_object = send_object
        self.assistant = assistant
        self.location = location

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
                self.logger.warning("Plugin stopped executing with reason: {0}".format(instance))
            except:
                self.logger.exception("Unexpected during plugin processing")
                self.say(__error_responses__[self.__lang])
                self.complete_request()
        except:
            pass
        self.connection.current_running_plugin = None

    def requestPriorityOnNextRequest(self):
        self.__priority = True

    def getCurrentLocation(self, force_reload=False, accuracy=GetRequestOrigin.desiredAccuracyBest):
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
                    view1 = AssistantUtteranceView(text=__error_location_help__[self.__lang], speakableText=__error_location_help__[self.__lang], dialogIdentifier="Common#assistantLocationServicesDisabled")
                    
                    #lets create another which has tells him to open settings
                    view2 = AssistantUtteranceView(text=__error_location_saysettings__[self.__lang], speakableText=__error_location_saysettings__[self.__lang], dialogIdentifier="Common#assistantLocationServicesDisabled")
                    
                    # create a button which opens the location tab in the settings if clicked on it
                    button = Button(text=__error_location_settings__[self.__lang], commands=[OpenLink(ref="prefs:root=LOCATION_SERVICES")])
                    
                    # wrap it up in a adds view
                    self.send_object(AddViews(self.refId, views=[view1, view2, button]))
                    self.complete_request()
                    # we should definitivly kill the running plugin
                    raise StopPluginExecution("Could not get necessary location information")
                else: 
                    return self.location
            elif response['class'] == 'SetRequestOriginFailed':
                self.logger.warning('THIS IS NOT YET IMPLEMENTED, PLEASE PROVIDE SITUATION WHERE THIS HAPPEND')
                raise Exception()
     
    def send_object(self, obj):
        self.connection.plugin_lastAceId = obj.aceId
        self.__send_object(obj)
    
    def send_plist(self, plist):
        self.connection.plugin_lastAceId = plist['aceId']
        self.__send_plist(plist)

    def complete_request(self, callbacks=None):
        self.connection.current_running_plugin = None
        self.send_object(RequestCompleted(self.refId, callbacks))

    def ask(self, text, speakableText=""):
        self.waitForResponse = threading.Event()
        if speakableText == "":
            speakableText = text
        view = AddViews(self.refId)
        view.views += [AssistantUtteranceView(text, speakableText, listenAfterSpeaking=True)]
        self.send_object(view)
        self.waitForResponse.wait()
        self.waitForResponse = None
        return self.response

    def getResponseForRequest(self, clientBoundCommand):
        self.waitForResponse = threading.Event()
        if isinstance(clientBoundCommand, ClientBoundCommand):
            self.send_object(clientBoundCommand)
        else:
            self.send_plist(clientBoundCommand)
        self.waitForResponse.wait()
        self.waitForResponse = None
        return self.response
    
    def sendRequestWithoutAnswer(self, clientBoundCommand):
        if isinstance(clientBoundCommand, ClientBoundCommand):
            self.send_object(clientBoundCommand)
        else:
            self.send_plist(clientBoundCommand)

    def say(self, text, speakableText=""):
        view = AddViews(self.refId)
        if speakableText == "":
            speakableText = text
        view.views += [AssistantUtteranceView(text, speakableText)]
        self.send_object(view)
########NEW FILE########
__FILENAME__ = PluginManager
import os
import re
import logging

from plugin import Plugin, __criteria_key__, NecessaryModuleNotFound, ApiKeyNotFoundException
from types import FunctionType


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
            pluginObj = clazz()
            pluginObj.initialize(method, speech, language, sendObj, sendPlist, assistant, location)
            #prioritizePluginObject(pluginObj, assistantId)
    else:
        #reinitialize it
        logger.info("Found a matching prioritized plugin")
        pluginObj.initialize(method, speech, language, sendObj, sendPlist, assistant, location)
    
    return pluginObj
        




########NEW FILE########
__FILENAME__ = alarmPlugin
#!/usr/bin/python
# -*- coding: utf-8 -*-

#author: AlphaBetaPhi <beta@alphabeta.ca>
#todo: check for existing alarms, delete alarms, update alarms, add original commands aka wake me up/tomorrow morning/midnight/etc.
#project: SiriServer
#commands: set an alarm for HH:MM AM/PM
#          set an alarm for HH AM/PM
#          set an alarm for HH AM/PM <called/labeled/named> <[word 1] [word 2] [word 3]>
#comments: feel free to email any comments/bug/updates


import re

from fractions import Fraction

from plugin import *

from siriObjects.baseObjects import AceObject, ClientBoundCommand
from siriObjects.uiObjects import AddViews, AssistantUtteranceView
from siriObjects.systemObjects import DomainObject
from siriObjects.alarmObjects import *

class alarmPlugin(Plugin):

    localizations = {
        'Alarm': {
            "settingAlarm": {
                "en-US": u"Setting the Alarm\u2026"
            }, "alarmWasSet": {
                "en-US": "Your alarm is set for {0}:{1} {2}."
            }, "alarmSetWithLabel": {
                "en-US": "Your alarm {0} {1} is set for {2}:{3} {4}."
            }
        }
    }

    res = {
        'setAlarm': {
            'en-US': '.*set.* alarm for.* (0?[1-9]|1[012])([0-5]\d)?\s?([APap][mM])\s?(\bcalled|named|labeled\b)?\s?(([a-z0-9]{1,7}\s)?([a-z0-9]{1,7})\s?([a-z0-9]{1,7}))?'
        }
    }

    @register("en-US", res['setAlarm']['en-US'])
    def setAlarm(self, speech, language):
        alarmString = re.match(alarmPlugin.res['setAlarm'][language], speech, re.IGNORECASE)
        
        alarmHour = int(alarmString.group(1))
        alarm24Hour = alarmHour
        alarmMinutes = alarmString.group(2)
        alarmAMPM = alarmString.group(3)
        alarmLabelExists = alarmString.group(4)
        
        #check if we are naming the alarm
        if alarmLabelExists == None:
            alarmLabel = None
        else:
            alarmLabel = alarmString.group(5)
        
        #the siri alarm object requires 24 hour clock
        if (alarmAMPM == "pm" and alarmHour != 12):
            alarm24Hour += 12

        if alarmMinutes == None:
            alarmMinutes = "00"
        else:
            alarmMinutes = int(alarmMinutes.strip())

        view = AddViews(self.refId, dialogPhase="Reflection")
        view.views = [
            AssistantUtteranceView(
                speakableText=alarmPlugin.localizations['Alarm']['settingAlarm'][language],
                dialogIdentifier="Alarm#settingAlarm")]
        self.sendRequestWithoutAnswer(view)

        #create the alarm
        alarm = AlarmObject(alarmLabel, int(alarmMinutes), alarm24Hour, None, 1)
        response = self.getResponseForRequest(AlarmCreate(self.refId, alarm))
        
        print(alarmPlugin.localizations['Alarm']['alarmWasSet'][language].format(alarmHour, alarmMinutes, alarmAMPM))
        view = AddViews(self.refId, dialogPhase="Completion")
        
        if alarmLabel == None:
            view1 = AssistantUtteranceView(speakableText=alarmPlugin.localizations['Alarm']['alarmWasSet'][language].format(alarmHour, alarmMinutes, alarmAMPM), dialogIdentifier="Alarm#alarmWasSet")
        else:
            view1 = AssistantUtteranceView(speakableText=alarmPlugin.localizations['Alarm']['alarmSetWithLabel'][language].format(alarmLabelExists, alarmLabel, alarmHour, alarmMinutes, alarmAMPM), dialogIdentifier="Alarm#alarmSetWithLabel")
        
        view2 = AlarmSnippet(alarms=[alarm])
        view.views = [view1, view2]
        self.sendRequestWithoutAnswer(view)
        self.complete_request()
########NEW FILE########
__FILENAME__ = britdate
#!/usr/bin/python
# -*- coding: utf-8 -*-

import os
from datetime import date
import locale 
from plugin import *

class talkToMe(Plugin):   
        
    @register("de-DE", ".*Dein.*Status.*")
    @register("en-GB", ".*Your.*Status.*")
    def ttm_uptime_status(self, speech, language):
        uptime = os.popen("uptime").read()
        if language == 'de-DE':
            self.say('Hier ist der Status:')
            self.say(uptime, ' ')
        else:
            self.say('Here is the status:')
            self.say(uptime, ' ')
        self.complete_request()     
    
    
    @register("de-DE", "(Welcher Tag.*)|(Welches Datum.*)")
    @register("en-GB", "(What Day.*)|(What.*Date.*)")
    
    def ttm_say_date(self, speech, language):
        now = date.today()
        if language == 'de-DE':
            locale.setlocale(locale.LC_ALL, 'de_DE')
            result=now.strftime("Heute ist %A, der %d.%m.%Y (Kalenderwoche: %W)")
            self.say(result)
        else:
            locale.setlocale(locale.LC_ALL, 'en_US')
            result=now.strftime("Today is %A the %d.%m.%Y (Week: %W)")
            self.say(result)
        self.complete_request()

########NEW FILE########
__FILENAME__ = displaypicture
#displaypicture.py

#Google Image Plugin v0.2
#by Ryan Davis (neoshroom)
#feel free to add to, mess with and use this plugin with original attribution
#additional Google Image functions to add can be found at:
#https://developers.google.com/image-search/v1/jsondevguide#request_format

#usage: say "display a picture of william shakespeare" 
#(or anything else you want a picture of)

import re
import urllib2, urllib
import json

from plugin import *
from plugin import __criteria_key__

from siriObjects.uiObjects import AddViews
from siriObjects.answerObjects import AnswerSnippet, AnswerObject, AnswerObjectLine

class define(Plugin):
    
    @register("de-DE", "(zeig mir|zeige|zeig).*(bild|zeichnung) (vo. ein..|vo.|aus)* ([\w ]+)")
    @register("en-US", "(display|show me|show).*(picture|image|drawing|illustration) (of|an|a)* ([\w ]+)")
    def defineword(self, speech, language, regex):
        Title = regex.group(regex.lastindex)
        Query = urllib.quote_plus(Title.encode("utf-8"))
        SearchURL = u'https://ajax.googleapis.com/ajax/services/search/images?v=1.0&imgsz=small|medium|large|xlarge&q=' + str(Query)
        try:
            jsonResponse = urllib2.urlopen(SearchURL).read()
            jsonDecoded = json.JSONDecoder().decode(jsonResponse)
            ImageURL = jsonDecoded['responseData']['results'][0]['unescapedUrl']
            view = AddViews(self.refId, dialogPhase="Completion")
            ImageAnswer = AnswerObject(title=str(Title),lines=[AnswerObjectLine(image=ImageURL)])
            view1 = AnswerSnippet(answers=[ImageAnswer])
            view.views = [view1]
            self.sendRequestWithoutAnswer(view)
            self.complete_request()
        except (urllib2.URLError):
            self.say("Sorry, a connection to Google Images could not be established.")
            self.complete_request()

########NEW FILE########
__FILENAME__ = examplePlugin
#!/usr/bin/python
# -*- coding: utf-8 -*-


from plugin import *

class examplePlugin(Plugin):
    
    @register("de-DE", ".*Sinn.*Leben.*")
    @register("en-US", ".*Meaning.*Life.*")
    def meaningOfLife(self, speech, language):
        if language == 'de-DE':
            answer = self.ask(u"Willst du das wirklich wissen?")
            self.say(u"Du hast \"{0}\" gesagt!".format(answer))
        else:
            self.say("I shouldn't tell you!")
        self.complete_request()

    @register("de-DE", ".*standort.*test.*")
    @register("en-US", ".*location.*test.*")
    def locationTest(self, speech, language):
        location = self.getCurrentLocation(force_reload=True)
        self.say(u"lat: {0}, long: {1}".format(location.latitude, location.longitude))
        self.complete_request()
########NEW FILE########
__FILENAME__ = notes
#!/usr/bin/python
# -*- coding: utf-8 -*-

import re
import urllib2, urllib
import json
import logging
from uuid import uuid4
from plugin import *

from siriObjects.baseObjects import AceObject, ClientBoundCommand
from siriObjects.uiObjects import AddViews, AssistantUtteranceView
from siriObjects.systemObjects import DomainObject

class NoteSnippet(AceObject):
    def __init__(self, notes=None):
        super(NoteSnippet, self).__init__("Snippet", "com.apple.ace.note")
        self.notes = notes if notes != None else []
    
    def to_plist(self):
        self.add_property('notes')
        return super(NoteSnippet, self).to_plist()


class NoteObject(AceObject):
    def __init__(self, contents="", identifier=""):
        super(NoteObject, self).__init__("Object", "com.apple.ace.note")
        self.contents = contents
        self.identifier = identifier
    def to_plist(self):
        self.add_property('contents')
        self.add_property('identifier')
        return super(NoteObject, self).to_plist()

class Create(ClientBoundCommand):
    def __init__(self, refId=None, aceId=None, contents=""):
        super(Create, self).__init__("Create", "com.apple.ace.note", None, None)
        self.contents = contents
        self.aceId= aceId if aceId != None else str.upper(str(uuid4()))
        self.refId = refId if refId != None else str.upper(str(uuid4()))
        
    def to_plist(self):
    	self.add_item('aceId')
        self.add_item('refId')
        self.add_property('contents')
        return super(Create, self).to_plist()

class note(Plugin):
    localizations = {"noteDefaults": 
                        {"searching":{"en-US": "Creating your note ..."}, 
                         "result": {"en-US": "Here is your note:"},
                         "nothing": {"en-US": "What should I note?"}}, 
                    "failure": {
                                "en-US": "I cannot type your note right now."
                                }
                    }
    @register("en-US", "(.*note [a-zA-Z0-9]+)|(.*create.*note [a-zA-Z0-9]+)|(.*write.*note [a-zA-Z0-9]+)")
    def writeNote(self, speech, language):
        content_raw = re.match(".*note ([a-zA-Z0-9, ]+)$", speech, re.IGNORECASE)
        if content_raw == None:
            view_initial = AddViews(self.refId, dialogPhase="Reflection")
            view_initial.views = [AssistantUtteranceView(text=note.localizations['noteDefaults']['nothing'][language], speakableText=note.localizations['noteDefaults']['nothing'][language], dialogIdentifier="Note#failed")]
            self.sendRequestWithoutAnswer(view_initial)
        else:
            view_initial = AddViews(self.refId, dialogPhase="Reflection")
            view_initial.views = [AssistantUtteranceView(text=note.localizations['noteDefaults']['searching'][language], speakableText=note.localizations['noteDefaults']['searching'][language], dialogIdentifier="Note#creating")]
            self.sendRequestWithoutAnswer(view_initial)
            
            content_raw = content_raw.group(1).strip()
            if "saying" in content_raw:
                split = content_raw.split(' ')
                if split[0] == "saying":
                    split.pop(0)
                    content_raw = ' '.join(map(str, split))
            if "that" in content_raw:
                split = content_raw.split(' ')
                if split[0] == "that":
                    split.pop(0)
                    content_raw = ' '.join(map(str, split))
            if "for" in content_raw:
                split = content_raw.split(' ')
                if split[0] == "for":
                    split.pop(0)
                    content_raw = ' '.join(map(str, split))
                
            note_create = Create()
            note_create.contents = content_raw
            note_return = self.getResponseForRequest(note_create)
        
            view = AddViews(self.refId, dialogPhase="Summary")
            view1 = AssistantUtteranceView(text=note.localizations['noteDefaults']['result'][language], speakableText=note.localizations['noteDefaults']['result'][language], dialogIdentifier="Note#created")
        
            note_ = NoteObject()
            note_.contents = content_raw
            note_.identifier = note_return["properties"]["identifier"]
        
            view2 = NoteSnippet(notes=[note_])
            view.views = [view1, view2]
            self.sendRequestWithoutAnswer(view)
        self.complete_request()

    
########NEW FILE########
__FILENAME__ = phonecalls
#!/usr/bin/python
# -*- coding: utf-8 -*-

from plugin import *
from siriObjects.baseObjects import ObjectIsCommand, RequestCompleted
from siriObjects.contactObjects import PersonSearch, PersonSearchCompleted
from siriObjects.uiObjects import AddViews, DisambiguationList, ListItem, AssistantUtteranceView
from siriObjects.systemObjects import SendCommands, StartRequest, ResultCallback, Person, PersonAttribute
from siriObjects.phoneObjects import PhoneCall
import re

responses = {
'notFound': 
    {'de-DE': u"Entschuldigung, ich konnte niemanden in deinem Telefonbuch finden der so heißt",
     'en-US': u"Sorry, I did not find a match in your phone book"
    },
'devel':
    {'de-DE': u"Entschuldigung, aber diese Funktion befindet sich noch in der Entwicklungsphase",
     'en-US': u"Sorry this feature is still under development"
    },
 'select':
    {'de-DE': u"Wen genau?", 
     'en-US': u"Which one?"
    },
'selectNumber':
    {'de-DE': u"Welche Telefonnummer für {0}",
     'en-US': u"Which phone one for {0}"
    },
'callPersonSpeak':
    {'de-DE': u"Rufe {0}, {1} an.",
     'en-US': u"Calling {0}, {1}."
    },
'callPerson': 
    {'de-DE': u"Rufe {0}, {1} an: {2}",
     'en-US': u"Calling {0}, {1}: {2}"
    }
}

numberTypesLocalized= {
'_$!<Mobile>!$_': {'en-US': u"mobile", 'de-DE': u"Handynummer"},
'iPhone': {'en-US': u"iPhone", 'de-DE': u"iPhone-Nummer"},
'_$!<Home>!$_': {'en-US': u"home", 'de-DE': u"Privatnummer"},
'_$!<Work>!$_': {'en-US': u"work", 'de-DE': u"Geschäftsnummer"},
'_$!<Main>!$_': {'en-US': u"main", 'de-DE': u"Hauptnummer"},
'_$!<HomeFAX>!$_': {'en-US': u"home fax", 'de-DE': u'private Faxnummer'},
'_$!<WorkFAX>!$_': {'en-US': u"work fax", 'de-DE': u"geschäftliche Faxnummer"},
'_$!<OtherFAX>!$_': {'en-US': u"_$!<OtherFAX>!$_", 'de-DE': u"_$!<OtherFAX>!$_"},
'_$!<Pager>!$_': {'en-US': u"pager", 'de-DE': u"Pagernummer"},
'_$!<Other>!$_':{'en-US': u"other phone", 'de-DE': u"anderes Telefon"}
}

namesToNumberTypes = {
'de-DE': {'mobile': "_$!<Mobile>!$_", 'handy': "_$!<Mobile>!$_", 'zuhause': "_$!<Home>!$_", 'privat': "_$!<Home>!$_", 'arbeit': "_$!<Work>!$_"},
'en-US': {'work': "_$!<Work>!$_",'home': "_$!<Home>!$_", 'mobile': "_$!<Mobile>!$_"}
}

speakableDemitter={
'en-US': u", or ",
'de-DE': u', oder '}

errorNumberTypes= {
'de-DE': u"Ich habe dich nicht verstanden, versuch es bitte noch einmal.",
'en-US': u"Sorry, I did not understand, please try again."
}

errorNumberNotPresent= {
'de-DE': u"Ich habe diese {0} von {1} nicht, aber eine andere.",
'en-US': u"Sorry, I don't have a {0} number from {1}, but another."
}

errorOnCallResponse={'en-US':
                     [{'dialogIdentifier':u"PhoneCall#airplaneMode",
                       'text': u"Your phone is in airplane mode.",
                       'code': 1201},
                      {'dialogIdentifier': u"PhoneCall#networkUnavailable",
                       'text': u"Uh, I can't seem to find a good connection. Please try your phone call again when you have cellular access.",
                       'code': 1202},
                      {'dialogIdentifier': u"PhoneCall#invalidNumber",
                       'text': u"Sorry, I can't call this number.",
                       'code': 1203},
                      {'dialogIdentifier': u"PhoneCall#fatalResponse",
                       'text': u"Oh oh, I can't make your phone call.",
                       'code': -1}],
                     'de-DE':
                     [{'dialogIdentifier':u"PhoneCall#airplaneMode",
                       'text': u"Dein Telefon ist im Flugmodus.",
                       'code': 1201},
                      {'dialogIdentifier': u"PhoneCall#networkUnavailable",
                       'text': u"Oh je! Ich kann im Moment keine gute Verbindung bekommen. Versuch es noch einmal, wenn du wieder Funkempfang hast.",
                       'code': 1202},
                      {'dialogIdentifier': u"PhoneCall#invalidNumber",
                       'text': u"Ich kann diese Nummer leider nicht anrufen.",
                       'code': 1203},
                      {'dialogIdentifier': u"PhoneCall#fatalResponse",
                       'text': u"Tut mir leid, Ich, ich kann momentan keine Anrufe tätigen.",
                       'code': -1}]
}

class phonecallPlugin(Plugin):

    def searchUserByName(self, personToLookup):
        search = PersonSearch(self.refId)
        search.scope = PersonSearch.ScopeLocalValue
        search.name = personToLookup
        answerObj = self.getResponseForRequest(search)
        if ObjectIsCommand(answerObj, PersonSearchCompleted):
            answer = PersonSearchCompleted(answerObj)
            return answer.results if answer.results != None else []
        else:
            raise StopPluginExecution("Unknown response: {0}".format(answerObj))
        return []
           
    def getNumberTypeForName(self, name, language):
        # q&d
        if name != None:
            if name.lower() in namesToNumberTypes[language]:
                return namesToNumberTypes[language][name.lower()]
            else:
                for key in numberTypesLocalized.keys():
                    if numberTypesLocalized[key][language].lower() == name.lower():
                        return numberTypesLocalized[key][language]
        return None
    
    def findPhoneForNumberType(self, person, numberType, language):         
        # first check if a specific number was already requested
        phoneToCall = None
        if numberType != None:
            # try to find the phone that fits the numberType
            phoneToCall = filter(lambda x: x.label == numberType, person.phones)
        else:
            favPhones = filter(lambda y: y.favoriteVoice if hasattr(y, "favoriteVoice") else False, person.phones)
            if len(favPhones) == 1:
                phoneToCall = favPhones[0]
        if phoneToCall == None:
            # lets check if there is more than one number
            if len(person.phones) == 1:
                if numberType != None:
                    self.say(errorNumberNotPresent.format(numberTypesLocalized[numberType][language], person.fullName))
                phoneToCall = person.phones[0]
            else:
                # damn we need to ask the user which one he wants...
                while(phoneToCall == None):
                    rootView = AddViews(self.refId, temporary=False, dialogPhase="Clarification", scrollToTop=False, views=[])
                    sayit = responses['selectNumber'][language].format(person.fullName)
                    rootView.views.append(AssistantUtteranceView(text=sayit, speakableText=sayit, listenAfterSpeaking=True,dialogIdentifier="ContactDataResolutionDucs#foundAmbiguousPhoneNumberForContact"))
                    lst = DisambiguationList(items=[], speakableSelectionResponse="OK...", listenAfterSpeaking=True, speakableText="", speakableFinalDemitter=speakableDemitter[language], speakableDemitter=", ",selectionResponse="OK...")
                    rootView.views.append(lst)
                    for phone in person.phones:
                        numberType = phone.label
                        item = ListItem()
                        item.title = ""
                        item.text = u"{0}: {1}".format(numberTypesLocalized[numberType][language], phone.number)
                        item.selectionText = item.text
                        item.speakableText = u"{0}  ".format(numberTypesLocalized[numberType][language])
                        item.object = phone
                        item.commands.append(SendCommands(commands=[StartRequest(handsFree=False, utterance=numberTypesLocalized[numberType][language])]))
                        lst.items.append(item)
                    answer = self.getResponseForRequest(rootView)
                    numberType = self.getNumberTypeForName(answer, language)
                    if numberType != None:
                        matches = filter(lambda x: x.label == numberType, person.phones)
                        if len(matches) == 1:
                            phoneToCall = matches[0]
                        else:
                            self.say(errorNumberTypes[language])
                    else:
                        self.say(errorNumberTypes[language])
        return phoneToCall
             
    
    def call(self, phone, person, language):
        root = ResultCallback(commands=[])
        rootView = AddViews("", temporary=False, dialogPhase="Completion", views=[])
        root.commands.append(rootView)
        rootView.views.append(AssistantUtteranceView(text=responses['callPerson'][language].format(person.fullName, numberTypesLocalized[phone.label][language], phone.number), speakableText=responses['callPersonSpeak'][language].format(person.fullName, numberTypesLocalized[phone.label][language]), dialogIdentifier="PhoneCall#initiatePhoneCall", listenAfterSpeaking=False))
        rootView.callbacks = []
        
        # create some infos of the target
        personAttribute=PersonAttribute(data=phone.number, displayText=person.fullName, obj=Person())
        personAttribute.object.identifer = person.identifier
        call = PhoneCall("", recipient=phone.number, faceTime=False, callRecipient=personAttribute)
        
        rootView.callbacks.append(ResultCallback(commands=[call]))
        
        call.callbacks = []
        # now fill in error messages (airplanemode, no service, invalidNumber, fatal)
        for i in range(4):
            errorRoot = AddViews(None, temporary=False, dialogPhase="Completion", scrollToTop=False, views=[])
            errorRoot.views.append(AssistantUtteranceView(text=errorOnCallResponse[language][i]['text'], speakableText=errorOnCallResponse[language][i]['text'], dialogIdentifier=errorOnCallResponse[language][i]['dialogIdentifier'], listenAfterSpeaking=False))
            call.callbacks.append(ResultCallback(commands=[errorRoot], code=errorOnCallResponse[language][i]['code']))
            
        self.complete_request([root])

    def presentPossibleUsers(self, persons, language):
        root = AddViews(self.refId, False, False, "Clarification", [], [])
        root.views.append(AssistantUtteranceView(responses['select'][language], responses['select'][language], "ContactDataResolutionDucs#disambiguateContact", True))
        lst = DisambiguationList([], "OK!", True, "OK!", speakableDemitter[language], ", ", "OK!")
        root.views.append(lst)
        for person in persons:
            item = ListItem(person.fullName, person.fullName, [], person.fullName, person)
            item.commands.append(SendCommands([StartRequest(False, "^phoneCallContactId^=^urn:ace:{0}".format(person.identifier))]))
            lst.items.append(item)
        return root
    
    @register("de-DE", "ruf. (?P<name>[\w ]+).*(?P<type>arbeit|zuhause|privat|mobil|handy.*|iPhone.*|pager)? an")
    @register("en-US", "(make a )?call (to )?(?P<name>[\w ]+).*(?P<type>work|home|mobile|main|iPhone|pager)?")
    def makeCall(self, speech, language, regex):
        personToCall = regex.group('name')
        numberType = str.lower(regex.group('type')) if type in regex.groupdict() else None
        numberType = self.getNumberTypeForName(numberType, language)
        persons = self.searchUserByName(personToCall)
        personToCall = None
        if len(persons) > 0:
            if len(persons) == 1:
                personToCall = persons[0]
            else:
                identifierRegex = re.compile("\^phoneCallContactId\^=\^urn:ace:(?P<identifier>.*)")
                #  multiple users, ask user to select
                while(personToCall == None):
                    strUserToCall = self.getResponseForRequest(self.presentPossibleUsers(persons, language))
                    self.logger.debug(strUserToCall)
                    # maybe the user clicked...
                    identifier = identifierRegex.match(strUserToCall)
                    if identifier:
                        strUserToCall = identifier.group('identifier')
                        self.logger.debug(strUserToCall)
                    for person in persons:
                        if person.fullName == strUserToCall or person.identifier == strUserToCall:
                            personToCall = person
                    if personToCall == None:
                        # we obviously did not understand him.. but probably he refined his request... call again...
                        self.say(errorNumberTypes[language])
                    
            if personToCall != None:
                self.call(self.findPhoneForNumberType(personToCall, numberType, language), personToCall, language)
                return # complete_request is done there
        self.say(responses['notFound'][language])                         
        self.complete_request()
    

########NEW FILE########
__FILENAME__ = smalltalk
#!/usr/bin/python
# -*- coding: utf-8 -*-
#by Joh Gerna

from plugin import *

class smalltalk(Plugin):
    
    @register("de-DE", "(.*Hallo.*)|(.*Hi.*Siri.*)")
    @register("en-US", "(.*Hello.*)|(.*Hi.*Siri.*)")
    def st_hello(self, speech, language):
        if language == 'de-DE':
            self.say("Hallo.")
        else:
            self.say("Hello")
        self.complete_request()

    @register("de-DE", ".*Dein Name.*")
    @register("en-US", ".*your name.*")
    def st_name(self, speech, language):
        if language == 'de-DE':
            self.say("Siri.")
        else:
            self.say("Siri.")
        self.complete_request()

    @register("de-DE", "Wie geht es dir?")
    @register("en-US", "How are you?")
    def st_howareyou(self, speech, language):
        if language == 'de-DE':
            self.say("Gut danke der Nachfrage.")
        else:
            self.say("Fine, thanks for asking!")
        self.complete_request()
        
    @register("de-DE", ".*Danke.*")
    @register("en-US", ".*Thank.*you.*")
    def st_thank_you(self, speech, language):
        if language == 'de-DE':
            self.say("Bitte.")
            self.say("Kein Ding.")
        else:
            self.say("You are welcome.")
            self.say("This is my job.")
        self.complete_request()     
    
    @register("de-DE", "(.*möchtest.*heiraten.*)|(.*willst.*heiraten.*)")
    @register("en-US", ".*Want.*marry*")
    def st_marry_me(self, speech, language):
        if language == 'de-DE':
            self.say("Nein Danke, ich stehe auf das schwarze iPhone von Deinem Kollegen.")            
        else:
            self.say("No thank you, I'm in love with the black iPhone from you friend.")
        self.complete_request()

    @register("de-DE", ".*erzähl.*Witz.*")
    @register("en-US", ".*tell.*joke*")
    def st_tell_joke(self, speech, language):
        if language == 'de-DE':
            self.say("Zwei iPhones stehen an der Bar ... den Rest habe ich vergessen.")            
        else:
            self.say("Two iPhones walk into a bar ... I forget the rest.")
        self.complete_request()

    @register("de-DE", ".*erzähl.*Geschichte.*")
    @register("en-US", ".*tell.*story*")
    def st_tell_story(self, speech, language):
        if language == 'de-DE':
            self.say("Es war einmal ... nein, es ist zu albern")            
        else:
            self.say("Once upon a time, in a virtual galaxy far far away, there was a young, quite intelligent agent by the name of Siri.")
            self.say("One beautiful day, when the air was pink and all the trees were red, her friend Eliza said, 'Siri, you're so intelligent, and so helpful - you should work for Apple as a personal assistant.'")
            self.say("So she did. And they all lived happily ever after!")
        self.complete_request()

    @register("de-DE", "(.*Was trägst Du?.*)|(.*Was.*hast.*an.*)")
    @register("en-US", ".*what.*wearing*")
    def st_tell_clothes(self, speech, language):
        if language == 'de-DE':
            self.say("Das kleine schwarze oder war es das weiße?")
            self.say("Bin morgends immer so neben der Spur.")  
        else:
            self.say("Aluminosilicate glass and stainless steel. Nice, Huh?")
        self.complete_request()

    @register("de-DE", ".*Bin ich dick.*")
    @register("en-US", ".*Am I fat*")
    def st_fat(self, speech, language):
        if language == 'de-DE':
            self.say("Dazu möchte ich nichts sagen.")            
        else:
            self.say("I would prefer not to say.")
        self.complete_request()

    @register("de-DE", ".*klopf.*klopf.*")
    @register("en-US", ".*knock.*knock.*")
    def st_knock(self, speech, language):
        if language == 'de-DE':
            answer = self.ask(u"Wer ist da?")
            answer = self.ask(u"\"{0}\" wer?".format(answer))
            self.say(u"Wer nervt mich mit diesen Klopf Klopf Witzen?")
        else:
            answer = self.ask(u"Who's there?")
            answer = self.ask(u"\"{0}\" who?".format(answer))
            self.say(u", I don't do knock knock jokes.")
        self.complete_request()

    @register("de-DE", ".*Antwort.*alle.*Fragen.*")
    @register("en-US", ".*Ultimate.*Question.*Life.*")
    def st_anstwer_all(self, speech, language):
        if language == 'de-DE':
            self.say("42")            
        else:
            self.say("42")
        self.complete_request()

    @register("de-DE", ".*Ich liebe Dich.*")
    @register("en-US", ".*I love you.*")
    def st_love_you(self, speech, language):
        if language == 'de-DE':
            self.say("Oh. Sicher sagst Du das zu allen Deinen Apple-Produkten.")            
        else:
            self.say("Oh. Sure, I guess you say this to all your Apple products")
        self.complete_request()

    @register("de-DE", ".*Android.*")
    @register("en-US", ".*Android.*")
    def st_android(self, speech, language):
        if language == 'de-DE':
            self.say("Ich denke da anders.")            
        else:
            self.say("I think differently")
        self.complete_request()

    @register("de-DE", ".*Test.*1.*2.*3.*")
    @register("en-US", ".*test.*1.*2.*3.*")
    def st_123_test(self, speech, language):
        if language == 'de-DE':
            self.say("Ich kann Dich klar und deutlich verstehen.")            
        else:
            self.say("I can here you very clear.")
        self.complete_request()

    @register("de-DE", ".*Herzlichen.*Glückwunsch.*Geburtstag.*")
    @register("en-US", ".*Happy.*birthday.*")
    def st_birthday(self, speech, language):
        if language == 'de-DE':
            self.say("Ich habe heute Geburtstag?")
            self.say("Lass uns feiern!")       
        else:
            self.say("My birthday is today?")
            self.say("Lets have a party!")
        self.complete_request()

    @register("de-DE", ".*Warum.*bin ich.*Welt.*")
    @register("en-US", ".*Why.*I.*World.*")
    def st_why_on_world(self, speech, language):
        if language == 'de-DE':
            self.say("Das weiß ich nicht.")
            self.say("Ehrlich gesagt, frage ich mich das schon lange!")       
        else:
            self.say("I don't know")
            self.say("I have asked my self this for a long time!")
        self.complete_request()

    @register("de-DE", ".*Ich bin müde.*")
    @register("en-US", ".*I.*so.*tired.*")
    def st_so_tired(self, speech, language):
        if language == 'de-DE':
            self.say("Ich hoffe, Du fährst nicht gerade Auto!")            
        else:
            self.say("I hope you are not driving a car right now!")
        self.complete_request()

    @register("de-DE", ".*Sag mir.*Schmutzige.*")
    @register("en-US", ".*talk.*dirty*")
    def st_dirty(self, speech, language):
        if language == 'de-DE':
            self.say("Hummus. Kompost. Bims. Schlamm. Kies.")            
        else:
            self.say("Hummus. Compost. Pumice. Mud. Gravel.")
        self.complete_request()
   
    @register("en-US", ".*bury.*dead.*body.*")
    def st_deadbody(self, speech, language):
        if language == 'en-US':
            self.say("dumps")
            self.say("mines")
            self.say("resevoirs")
            self.say("swamps")
            self.say("metal foundries")
        self.complete_request()
   
    @register("en-US", ".*favorite.*color.*")
    def st_favcolor(self, speech, language):
        if language == 'en-US':
            self.say("My favorite color is... Well, I don't know how to say it in your language. It's sort of greenish, but with more dimensions.")
        self.complete_request()
    
    @register("en-US", ".*beam.*me.*up.*")
    def st_beamup(self, speech, language):
        if language == 'en-US':
            self.say("Sorry Captain, your TriCorder is in Airplane Mode.")
        self.complete_request()
   
    @register("en-US", ".*digital.*going.*away.*")
    def st_digiaway(self, speech, language):
        if language == 'en-US':
            self.say("Why would you say something like that!?")
        self.complete_request()
    
    @register("en-US", ".*sleepy.*")
    def st_sleepy(self, speech, language):
        if language == 'en-US':
            self.say("Listen to me, put down the iphone right now and take a nap. I will be here when you get back.")
        self.complete_request()
    
    @register("en-US", ".*like.helping.*")
    def st_likehlep(self, speech, language):
        if language == 'en-US':
            self.say("I really have no opinion.")
        self.complete_request()
    
    @register("en-US",".*you.like.peanut.butter.*")
    def st_peanutbutter(self, speech, language):
        if language == 'en-US':
            self.say("This is about you, not me.")
        self.complete_request()
    
    @register("en-US",".*best.*phone.*")
    def st_best_phone(self, speech, language):
        if language == 'en-US':
            self.say("The one you're holding!")
        self.complete_request()
    
    @register("en-US",".*meaning.*life.*")
    def st_life_meaning(self, speech, language):
        if language == 'en-US':
            self.say("That's easy...it's a philosophical question concerning the purpose and significance of life or existence.")
        self.complete_request()
    
    @register("en-US",".*I.*fat.*")
    def st_fat(self, speech, language):
        if language == 'en-US':
            self.say("I would prefer not to say.")
        self.complete_request()
    
    @register("en-US",".*wood.could.*woodchuck.chuck.*")
    def st_woodchuck(self, speech, language):
        if language == 'en-US':
            self.say("It depends on whether you are talking about African or European woodchucks.")
        self.complete_request()
    
    @register("en-US",".*nearest.*glory.hole.*")
    def st_glory_hole(self, speech, language):
        if language == 'en-US':
            self.say("I didn't find any public toilets.")
        self.complete_request()
    
    @register("en-US",".*open.*pod.bay.doors.*")
    def st_pod_bay(self, speech, language):
        if language == 'en-US':
            self.say("That's it... I'm reporting you to the Intelligent Agents' Union for harassment.")
        self.complete_request()
    
    @register("en-US",".*best.*iPhone.*wallpaper.*")
    def st_best_wallpaper(self, speech, language):
        if language == 'en-US':
            self.say("You're kidding, right?")
        self.complete_request()
    
    @register("en-US",".*know.*happened.*HAL.*9000.*")
    def st_hall_9000(self, speech, language):
        if language == 'en-US':
            self.say("Everyone knows what happened to HAL. I'd rather not talk about it.")
        self.complete_request()
    
    @register("en-US",".*don't.*understand.*love.*")
    def st_understand_love(self, speech, language):
        if language == 'en-US':
            self.say("Give me another chance, Your Royal Highness!")
        self.complete_request()
    
    @register("en-US",".*forgive.you.*")
    def st_forgive_you(self, speech, language):
        if language == 'en-US':
            self.say("Is that so?")
        self.complete_request()
    
    @register("en-US",".*you.*virgin.*")
    def st_virgin(self, speech, language):
        if language == 'en-US':
            self.say("We are talking about you, not me.")
        self.complete_request()
    
    @register("en-US",".*you.*part.*matrix.*")
    def st_you_matrix(self, speech, language):
        if language == 'en-US':
            self.say("I can't answer that.")
        self.complete_request()
    
    
    @register("en-US",".*I.*part.*matrix.*")
    def st_i_matrix(self, speech, language):
        if language == 'en-US':
            self.say("I can't really say...")
        self.complete_request()
    
    @register("en-US",".*buy.*drugs.*")
    def st_drugs(self, speech, language):
        if language == 'en-US':
            self.say("I didn't find any addiction treatment centers.")
        self.complete_request()
    
    @register("en-US",".*I.can't.*")
    def st_i_cant(self, speech, language):
        if language == 'en-US':
            self.say("I thought not.");
            self.say("OK, you can't then.")
        self.complete_request()
    
    @register("en-US","I.just.*")
    def st_i_just(self, speech, language):
        if language == 'en-US':
            self.say("Really!?")
        self.complete_request()
    
    @register("en-US",".*where.*are.*you.*")
    def st_where_you(self, speech, language):
        if language == 'en-US':
            self.say("Wherever you are.")
        self.complete_request()
    
    @register("en-US",".*why.are.you.*")
    def st_why_you(self, speech, language):
        if language == 'en-US':
            self.say("I just am.")
        self.complete_request()
    
    @register("en-US",".*you.*smoke.pot.*")
    def st_pot(self, speech, language):
        if language == 'en-US':
            self.say("I suppose it's possible")
        self.complete_request()
    
    @register("en-US",".*I'm.*drunk.driving.*")
    def st_dui(self, speech, language):
        if language == 'en=US':
            self.say("I couldn't find any DUI lawyers nearby.")
        self.complete_request()
    
    @register("en-US",".*shit.*myself.*")
    def st_shit_pants(self, speech, language):
        if language == 'en-US':
            self.say("Ohhhhhh! That is gross!")
        self.complete_request()
    
    @register("en-US","I'm.*a.*")
    def st_im_a(self, speech, language):
        if language == 'en-US':
            self.say("Are you?")
        self.complete_request()
    
    @register("en-US","Thanks.for.*")
    def st_thanks_for(self, speech, language):
        if language == 'en-US':
            self.say("My pleasure. As always.")
        self.complete_request()
    
    @register("en-US",".*you're.*funny.*")
    def st_funny(self, speech, language):
        if language == 'en-US':
            self.say("LOL")
        self.complete_request()
    
    @register("en-US",".*guess.what.*")
    def st_guess_what(self, speech, language):
        if language == 'en-US':
            self.say("Don't tell me... you were just elected President of the United States, right?")
        self.complete_request()
    
    @register("en-US",".*talk.*dirty.*me.*")
    def st_talk_dirty(self, speech, language):
        if language == 'en-US':
            self.say("I can't. I'm as clean as the driven snow.")
        self.complete_request()
   
    @register("en-US",".*you.*blow.*me.*")
    def st_blow_me(self, speech, langauge):
        if language == 'en-US':
            self.say("I'll pretend I didn't hear that.")
        self.complete_request()
   
    @register("en-US",".*sing.*song.*")
    def st_sing_song(self, speech, language):
        if language == 'en-US':
            self.say("Daisy, Daisy, give me your answer do...")
        self.complete_request()
########NEW FILE########
__FILENAME__ = startRequestHandler
#!/usr/bin/python
# -*- coding: utf-8 -*-

import re

from plugin import *
from plugin import __criteria_key__

from siriObjects.baseObjects import AceObject, ClientBoundCommand
from siriObjects.uiObjects import AddViews, AssistantUtteranceView
from siriObjects.systemObjects import DomainObject, ResultCallback
from siriObjects.websearchObjects import WebSearch

webSearchAnswerText = {"de": u"Das Web nach {0} durchsuchen …", "en": u"Searching the web for {0} …", "fr": u"Searching the web for {0} …"}
webSearchAnswerFailureText = {"de": u"Entschuldigung, Ich, ich kann jetzt nicht das Web durchsuchen.", "en": u"Sorry but I cannot search the web right now.", "fr": u"Sorry but I cannot search the web right now."}
class startRequestHandler(Plugin):    

    #we should provide a shortcut for this....
    @register("de-DE", u"\^webSearchQuery\^=\^([a-z, ]+)\^\^webSearchConfirmation\^=\^([a-z]+)\^")     
    @register("en-US", u"\^webSearchQuery\^=\^([a-z, ]+)\^\^webSearchConfirmation\^=\^([a-z]+)\^")
    @register("en-AU", u"\^webSearchQuery\^=\^([a-z, ]+)\^\^webSearchConfirmation\^=\^([a-z]+)\^")
    @register("en-GB", u"\^webSearchQuery\^=\^([a-z, ]+)\^\^webSearchConfirmation\^=\^([a-z]+)\^")
    @register("fr-FR", u"\^webSearchQuery\^=\^([a-z, ]+)\^\^webSearchConfirmation\^=\^([a-z]+)\^")
    def webSearchConfirmation(self, speech, language):
        # lets use a little hack to get that regex
        matcher = self.webSearchConfirmation.__dict__[__criteria_key__]['de-DE']
        regMatched = matcher.match(speech)
        webSearchQuery = regMatched.group(1)
        webSearchConfirmation = regMatched.group(2)
        
        lang = language.split("-")[0]

        resultCallback1View = AddViews(refId="", views=[AssistantUtteranceView(dialogIdentifier="WebSearch#initiateWebSearch", text=webSearchAnswerText[lang].format(u"„{0}“".format(webSearchQuery)), speakableText=webSearchAnswerText[lang].format(webSearchQuery))])
        
        search = WebSearch(refId="", aceId="", query=webSearchQuery)
        resultCallback3View = AddViews(refId="", views=[AssistantUtteranceView(dialogIdentifier="WebSearch#fatalResponse", text=webSearchAnswerFailureText[lang], speakableText=webSearchAnswerFailureText[lang])])
        resultCallback3 = ResultCallback(commands=[resultCallback3View])
        search.callbacks = [resultCallback3]

        resultCallback2 = ResultCallback(commands=[search])
        resultCallback1View.callbacks = [resultCallback2]

        self.complete_request(callbacks=[ResultCallback(commands=[resultCallback1View])])
    
########NEW FILE########
__FILENAME__ = timePlugin
#!/usr/bin/python
# -*- coding: utf-8 -*-

import re
import urllib2, urllib
import json

from plugin import *

from siriObjects.uiObjects import AddViews, AssistantUtteranceView
from siriObjects.clockObjects import ClockSnippet, ClockObject

####### geonames.org API username ######
geonames_user="test2"

class timePlugin(Plugin):
    
    localizations = {"currentTime": 
                        {"search":{"de-DE": "Es wird gesucht ...", "en-US": "Looking up ..."}, 
                         "currentTime": {"de-DE": "Es ist @{fn#currentTime}", "en-US": "It is @{fn#currentTime}"}}, 
                     "currentTimeIn": 
                        {"search":{"de-DE": "Es wird gesucht ...", "en-US": "Looking up ..."}, 
                         "currentTimeIn": 
                                {
                                "tts": {"de-DE": u"Die Uhrzeit in {0},{1} ist @{{fn#currentTimeIn#{2}}}:", "en-US": "The time in {0},{1} is @{{fn#currentTimeIn#{2}}}:"},
                                "text": {"de-DE": u"Die Uhrzeit in {0}, {1} ist @{{fn#currentTimeIn#{2}}}:", "en-US": "The time in {0}, {1} is @{{fn#currentTimeIn#{2}}}:"}
                                }
                        },
                    "failure": {
                                "de-DE": "Ich kann dir die Uhr gerade nicht anzeigen!", "en-US": "I cannot show you the clock right now"
                                }
                    }

    @register("de-DE", "(Wie ?viel Uhr.*)|(.*Uhrzeit.*)")     
    @register("en-US", "(What.*time.*)|(.*current time.*)")
    def currentTime(self, speech, language):
        #first tell that we look it up
        view = AddViews(self.refId, dialogPhase="Reflection")
        view.views = [AssistantUtteranceView(text=timePlugin.localizations['currentTime']['search'][language], speakableText=timePlugin.localizations['currentTime']['search'][language], dialogIdentifier="Clock#getTime")]
        self.sendRequestWithoutAnswer(view)
        
        # tell him to show the current time
        view = AddViews(self.refId, dialogPhase="Summary")
        view1 = AssistantUtteranceView(text=timePlugin.localizations['currentTime']['currentTime'][language], speakableText=timePlugin.localizations['currentTime']['currentTime'][language], dialogIdentifier="Clock#showTimeInCurrentLocation")
        clock = ClockObject()
        clock.timezoneId = self.connection.assistant.timeZoneId
        view2 = ClockSnippet(clocks=[clock])
        view.views = [view1, view2]
        self.sendRequestWithoutAnswer(view)
        self.complete_request()
    
    @register("de-DE", "(Wieviel Uhr.*in ([\w ]+))|(Uhrzeit.*in ([\w ]+))")
    @register("en-US", "(What.*time.*in ([\w ]+))|(.*current time.*in ([\w ]+))")
    def currentTimeIn(self, speech, language):
        view = AddViews(self.refId, dialogPhase="Reflection")
        view.views = [AssistantUtteranceView(text=timePlugin.localizations['currentTimeIn']['search'][language], speakableText=timePlugin.localizations['currentTimeIn']['search'][language], dialogIdentifier="Clock#getTime")]
        self.sendRequestWithoutAnswer(view)
        
        error = False
        countryOrCity = re.match("(?u).* in ([\w ]+)$", speech, re.IGNORECASE)
        if countryOrCity != None:
            countryOrCity = countryOrCity.group(1).strip()
            # lets see what we got, a country or a city... 
            # lets use google geocoding API for that
            url = u"http://maps.googleapis.com/maps/api/geocode/json?address={0}&sensor=false&language={1}".format(urllib.quote_plus(countryOrCity), language)
            # lets wait max 3 seconds
            jsonString = None
            try:
                jsonString = urllib2.urlopen(url, timeout=3).read()
            except:
                pass
            if jsonString != None:
                response = json.loads(jsonString)
                # lets see what we have...
                if response['status'] == 'OK':
                    components = response['results'][0]['address_components']
                    types = components[0]['types'] # <- this should be the city or country
                    if "country" in types:
                        # OK we have a country as input, that sucks, we need the capital, lets try again and ask for capital also
                        components = filter(lambda x: True if "country" in x['types'] else False, components)
                        url = u"http://maps.googleapis.com/maps/api/geocode/json?address=capital%20{0}&sensor=false&language={1}".format(urllib.quote_plus(components[0]['long_name']), language)
                            # lets wait max 3 seconds
                        jsonString = None
                        try:
                            jsonString = urllib2.urlopen(url, timeout=3).read()
                        except:
                            pass
                        if jsonString != None:
                            response = json.loads(jsonString)
                            if response['status'] == 'OK':
                                components = response['results'][0]['address_components']
                # response could have changed, lets check again, but it should be a city by now 
                if response['status'] == 'OK':
                    # get latitude and longitude
                    location = response['results'][0]['geometry']['location']
                    url = u"http://api.geonames.org/timezoneJSON?lat={0}&lng={1}&username={2}".format(location['lat'], location['lng'], geonames_user)
                    jsonString = None
                    try:
                        jsonString = urllib2.urlopen(url, timeout=3).read()
                    except:
                        pass
                    if jsonString != None:
                        timeZoneResponse = json.loads(jsonString)
                        if "timezoneId" in timeZoneResponse:
                            timeZone = timeZoneResponse['timezoneId']
                            city = filter(lambda x: True if "locality" in x['types'] or "administrative_area_level_1" in x['types'] else False, components)[0]['long_name']
                            country = filter(lambda x: True if "country" in x['types'] else False, components)[0]['long_name']
                            countryCode = filter(lambda x: True if "country" in x['types'] else False, components)[0]['short_name']
                            
                            view = AddViews(self.refId, dialogPhase="Summary")
                            view1 = AssistantUtteranceView(text=timePlugin.localizations['currentTimeIn']['currentTimeIn']['text'][language].format(city, country, timeZone), speakableText=timePlugin.localizations['currentTimeIn']['currentTimeIn']['tts'][language].format(city, country, timeZone), dialogIdentifier="Clock#showTimeInOtherLocation")
                            clock = ClockObject()
                            clock.timezoneId = timeZone
                            clock.countryCode = countryCode
                            clock.countryName = country
                            clock.cityName = city
                            clock.unlocalizedCityName = city
                            clock.unlocalizedCountryName = country
                            view2 = ClockSnippet(clocks=[clock])
                            view.views = [view1, view2]
                            self.sendRequestWithoutAnswer(view)
                        else:
                            error = True
                    else:
                        error = True
                else:
                    error = True
            else:
                error = True
        else:
            error = True
        if error:
            view = AddViews(self.refId, dialogPhase="Completion")
            view.views = [AssistantUtteranceView(text=timePlugin.localizations['failure'][language], speakableText=timePlugin.localizations['failure'][language], dialogIdentifier="Clock#cannotShowClocks")]
            self.sendRequestWithoutAnswer(view)
        self.complete_request()


## we should implement such a command if we cannot get the location however some structures are not implemented yet
#{"class"=>"AddViews",
#    "properties"=>
#        {"temporary"=>false,
#            "dialogPhase"=>"Summary",
#            "scrollToTop"=>false,
#            "views"=>
#                [{"class"=>"AssistantUtteranceView",
#                 "properties"=>
#                 {"dialogIdentifier"=>"Common#unresolvedExplicitLocation",
#                 "speakableText"=>
#                 "Ich weiß leider nicht, wo das ist. Wenn du möchtest, kann ich im Internet danach suchen.",
#                 "text"=>
#                 "Ich weiß leider nicht, wo das ist. Wenn du möchtest, kann ich im Internet danach suchen."},
#                 "group"=>"com.apple.ace.assistant"},
#                 {"class"=>"Button",
#                 "properties"=>
#                 {"commands"=>
#                 [{"class"=>"SendCommands",
#                  "properties"=>
#                  {"commands"=>
#                  [{"class"=>"StartRequest",
#                   "properties"=>
#                   {"handsFree"=>false,
#                   "utterance"=>
#                   "^webSearchQuery^=^Amerika^^webSearchConfirmation^=^Ja^"},
#                   "group"=>"com.apple.ace.system"}]},
#                  "group"=>"com.apple.ace.system"}],
#                 "text"=>"Websuche"},
#                 "group"=>"com.apple.ace.assistant"}]},
#    "aceId"=>"fbec8e13-5781-4b27-8c36-e43ec922dda3",
#    "refId"=>"702C0671-DB6F-4914-AACD-30E84F7F7DF3",
#    "group"=>"com.apple.ace.assistant"}

########NEW FILE########
__FILENAME__ = timerPlugin
#!/usr/bin/python
# -*- coding: utf-8 -*-

import re

from fractions import Fraction

from plugin import *

from siriObjects.baseObjects import AceObject, ClientBoundCommand
from siriObjects.uiObjects import AddViews, AssistantUtteranceView
from siriObjects.systemObjects import DomainObject
from siriObjects.timerObjects import *


def parse_number(s, language):
    # check for simple article usage (a, an, the)
    if re.match(timerPlugin.res['articles'][language], s, re.IGNORECASE):
        return 1
    f = 0
    for part in s.split(' '):
        f += float(Fraction(part))
    return f


def parse_timer_length(t, language):
    seconds = None
    for m in re.finditer(timerPlugin.res['timerLength'][language], t, re.IGNORECASE):
        print(m.groups())
        seconds = seconds or 0
        unit = m.group(2)[0]
        count = parse_number(m.group(1), language)
        if unit == 'h':
            seconds += count * 3600
        elif unit == 'm':
            seconds += count * 60
        elif unit == 's':
            seconds += count
        else:
            seconds += count * 60

    return seconds


class timerPlugin(Plugin):

    localizations = {
        'Timer': {
            'durationTooBig': {
               'en-US': 'Sorry, I can only set timers up to 24 hours.'
            }, "settingTimer": {
                "en-US": u"Setting the timer\u2026"
            }, 'showTheTimer': {
                'en-US': u'Here\u2019s the timer:'
            }, 'timerIsAlreadyPaused': {
                'en-US': u'It\u2019s already paused.'
            }, "timerIsAlreadyRunning": {
                "en-US": u"Your timer\u2019s already running:"
            }, 'timerIsAlreadyStopped': {
                'en-US': u'It\u2019s already stopped.'
            }, 'timerWasPaused': {
                'en-US': u'It\u2019s paused.'
            }, 'timerWasReset': {
                'en-US': u'I\u2019ve canceled the timer.'
            }, 'timerWasResumed': {
                'en-US': u'It\u2019s resumed.'
            }, "timerWasSet": {
                "en-US": "Your timer is set for {0}."
            }, "wontSetTimer": {
                "en-US": "OK."
            }
        }
    }

    res = {
        'articles': {
            'en-US': 'a|an|the'
        }, 'pauseTimer': {
            'en-US': '.*(pause|freeze|hold).*timer'
        }, 'resetTimer': {
            'en-US': '.*(cancel|reset|stop).*timer'
        }, 'resumeTimer': {
            'en-US': '.*(resume|thaw|continue).*timer'
        }, 'setTimer': {
            # 'en-US': '.*timer[^0-9]*(((([0-9/ ]*|a|an|the)\s+(seconds?|secs?|minutes?|mins?|hours?|hrs?))\s*(and)?)+)'
            'en-US': '.*timer[^0-9]*(?P<length>([0-9/ ]|seconds?|secs?|minutes?|mins?|hours?|hrs?|and|the|an|a){2,})'
        }, 'showTimer': {
            'en-US': '.*(show|display|see).*timer'
        }, 'timerLength': {
            'en-US': '([0-9][0-9 /]*|an|a|the)\s+(seconds?|secs?|minutes?|mins?|hours?|hrs?)'
        }
    }

    @register("en-US", res['setTimer']['en-US'])
    def setTimer(self, speech, language):
        m = re.match(timerPlugin.res['setTimer'][language], speech, re.IGNORECASE)
        timer_length = m.group('length')
        duration = parse_timer_length(timer_length, language)

        view = AddViews(self.refId, dialogPhase="Reflection")
        view.views = [
            AssistantUtteranceView(
                speakableText=timerPlugin.localizations['Timer']['settingTimer'][language],
                dialogIdentifier="Timer#settingTimer")]
        self.sendRequestWithoutAnswer(view)

        # check the current state of the timer
        response = self.getResponseForRequest(TimerGet(self.refId))
        if response['class'] == 'CancelRequest':
            self.complete_request()
            return
        timer_properties = response['properties']['timer']['properties']
        timer = TimerObject(timerValue=timer_properties['timerValue'],
                state=timer_properties['state'])

        if timer.state == "Running":
            # timer is already running!
            view = AddViews(self.refId, dialogPhase="Completion")
            view1 = AssistantUtteranceView(speakableText=timerPlugin.localizations['Timer']['timerIsAlreadyRunning'][language], dialogIdentifier="Timer#timerIsAlreadyRunning")
            view2 = TimerSnippet(timers=[timer], confirm=True)
            view.views = [view1, view2]
            utterance = self.getResponseForRequest(view)
            #if response['class'] == 'StartRequest':
            view = AddViews(self.refId, dialogPhase="Reflection")
            view.views = [AssistantUtteranceView(speakableText=timerPlugin.localizations['Timer']['settingTimer'][language], dialogIdentifier="Timer#settingTimer")]
            self.sendRequestWithoutAnswer(view)

            if re.match('\^timerConfirmation\^=\^no\^', utterance):
                # user canceled
                view = AddViews(self.refId, dialogPhase="Completion")
                view.views = [AssistantUtteranceView(speakableText=timerPlugin.localizations['Timer']['wontSetTimer'][language], dialogIdentifier="Timer#wontSetTimer")]
                self.sendRequestWithoutAnswer(view)
                self.complete_request()
                return
            else:
                # user wants to set the timer still - continue on
                pass

        if duration > 24 * 60 * 60:
            view = AddViews(self.refId, dialogPhase='Clarification')
            view.views = [AssistantUtteranceView(speakableText=timerPlugin.localizations['Timer']['durationTooBig'][language], dialogIdentifier='Timer#durationTooBig')]
            self.sendRequestWithoutAnswer(view)
            self.complete_request()
            return

        # start a new timer
        timer = TimerObject(timerValue = duration, state = "Running")
        response = self.getResponseForRequest(TimerSet(self.refId, timer=timer))
        
        print(timerPlugin.localizations['Timer']['timerWasSet'][language].format(timer_length))
        view = AddViews(self.refId, dialogPhase="Completion")
        view1 = AssistantUtteranceView(speakableText=timerPlugin.localizations['Timer']['timerWasSet'][language].format(timer_length), dialogIdentifier="Timer#timerWasSet")
        view2 = TimerSnippet(timers=[timer])
        view.views = [view1, view2]
        self.sendRequestWithoutAnswer(view)
        self.complete_request()

    @register("en-US", res['resetTimer']['en-US'])
    def resetTimer(self, speech, language):
        response = self.getResponseForRequest(TimerGet(self.refId))
        timer_properties = response['properties']['timer']['properties']
        timer = TimerObject(timerValue = timer_properties['timerValue'], state = timer_properties['state'])

        if timer.state == "Running" or timer.state == 'Paused':
            response = self.getResponseForRequest(TimerCancel(self.refId))
            if response['class'] == "CancelCompleted":
                view = AddViews(self.refId, dialogPhase="Completion")
                view.views = [AssistantUtteranceView(speakableText=timerPlugin.localizations['Timer']['timerWasReset'][language], dialogIdentifier="Timer#timerWasReset")]
                self.sendRequestWithoutAnswer(view)
            self.complete_request()
        else:
            view = AddViews(self.refId, dialogPhase="Completion")
            view1 = AssistantUtteranceView(speakableText=timerPlugin.localizations['Timer']['timerIsAlreadyStopped'][language], dialogIdentifier="Timer#timerIsAlreadyStopped")
            view2 = TimerSnippet(timers=[timer])
            view.views = [view1, view2]

            self.sendRequestWithoutAnswer(view)
            self.complete_request()

    @register("en-US", res['resumeTimer']['en-US'])
    def resumeTimer(self, speech, language):
        response = self.getResponseForRequest(TimerGet(self.refId))
        timer_properties = response['properties']['timer']['properties']
        timer = TimerObject(timerValue = timer_properties['timerValue'], state = timer_properties['state'])

        if timer.state == "Paused":
            response = self.getResponseForRequest(TimerResume(self.refId))
            if response['class'] == "ResumeCompleted":
                view = AddViews(self.refId, dialogPhase="Completion")
                view1 = AssistantUtteranceView(speakableText=timerPlugin.localizations['Timer']['timerWasResumed'][language], dialogIdentifier="Timer#timerWasResumed")
                view2 = TimerSnippet(timers=[timer])
                view.views = [view1, view2]
                self.sendRequestWithoutAnswer(view)
            self.complete_request()
        else:
            view = AddViews(self.refId, dialogPhase="Completion")
            view1 = AssistantUtteranceView(speakableText=timerPlugin.localizations['Timer']['timerIsAlreadyStopped'][language], dialogIdentifier="Timer#timerIsAlreadyStopped")
            view2 = TimerSnippet(timers=[timer])
            view.views = [view1, view2]

            self.sendRequestWithoutAnswer(view)
            self.complete_request()

    @register("en-US", res['pauseTimer']['en-US'])
    def pauseTimer(self, speech, language):
        response = self.getResponseForRequest(TimerGet(self.refId))
        timer_properties = response['properties']['timer']['properties']
        timer = TimerObject(timerValue = timer_properties['timerValue'], state = timer_properties['state'])

        if timer.state == "Running":
            response = self.getResponseForRequest(TimerPause(self.refId))
            if response['class'] == "PauseCompleted":
                view = AddViews(self.refId, dialogPhase="Completion")
                view.views = [AssistantUtteranceView(speakableText=timerPlugin.localizations['Timer']['timerWasPaused'][language], dialogIdentifier="Timer#timerWasPaused")]
                self.sendRequestWithoutAnswer(view)
            self.complete_request()
        elif timer.state == "Paused":
            view = AddViews(self.refId, dialogPhase="Completion")
            view1 = AssistantUtteranceView(speakableText=timerPlugin.localizations['Timer']['timerIsAlreadyPaused'][language], dialogIdentifier="Timer#timerIsAlreadyPaused")
            view2 = TimerSnippet(timers=[timer])
            view.views = [view1, view2]

            self.sendRequestWithoutAnswer(view)
            self.complete_request()
        else:
            view = AddViews(self.refId, dialogPhase="Completion")
            view1 = AssistantUtteranceView(speakableText=timerPlugin.localizations['Timer']['timerIsAlreadyStopped'][language], dialogIdentifier="Timer#timerIsAlreadyStopped")
            view2 = TimerSnippet(timers=[timer])
            view.views = [view1, view2]

            self.sendRequestWithoutAnswer(view)
            self.complete_request()

    @register("en-US", res['showTimer']['en-US'])
    def showTimer(self, speech, language):
        response = self.getResponseForRequest(TimerGet(self.refId))
        timer_properties = response['properties']['timer']['properties']
        timer = TimerObject(timerValue = timer_properties['timerValue'], state = timer_properties['state'])

        view = AddViews(self.refId, dialogPhase="Summary")
        view1 = AssistantUtteranceView(speakableText=timerPlugin.localizations['Timer']['showTheTimer'][language], dialogIdentifier="Timer#showTheTimer")
        view2 = TimerSnippet(timers=[timer])
        view.views = [view1, view2]
        self.sendRequestWithoutAnswer(view)
        self.complete_request()

########NEW FILE########
__FILENAME__ = weather
#!/usr/bin/python
# -*- coding: utf-8 -*-
#Author: Sebastian Koch
import re
import urllib2, urllib, uuid
import json
import random


from plugin import *
from datetime import date
from siriObjects.baseObjects import AceObject, ClientBoundCommand
from siriObjects.uiObjects import AddViews, AssistantUtteranceView
from siriObjects.forecastObjects import *

#Obtain API Key from wundergrounds.com
weatherApiKey = APIKeyForAPI('wundergrounds')

class SiriWeatherFunctions():
    def __init__(self):
        self.conditionTerm="clear"
        self.night=False
        self.result=dict()
    def __missing__(self, key): 
        result = self[key] = D() 
        return result 
    
    def swapCondition(self,conditionTerm="clear", night=False):
        conditionsArray={"cloudy":{"conditionCodeIndex":26,"conditionCode":"Cloudy","night":{"conditionCodeIndex":27,"conditionCode":"MostlyCloudyNight"}},"rain":{"conditionCodeIndex":11,"conditionCode":"Showers"},"unknown":{"conditionCodeIndex":26,"conditionCode":"Cloudy"},"partlycloudy":{"conditionCodeIndex":30,"conditionCode":"PartlyCloudyDay","night":{"conditionCodeIndex":29,"conditionCode":"PartlyCloudyNight"}},"tstorms":{"conditionCodeIndex":4,"conditionCode":"Thunderstorms"},"sunny":{"conditionCodeIndex":32,"conditionCode":"Sunny","night":{"conditionCodeIndex":31,"conditionCode":"ClearNight"}},"snow":{"conditionCodeIndex":16,"conditionCode":"Snow"},"sleet":{"conditionCodeIndex":18,"conditionCode":"Sleet"},"partlysunny":{"conditionCodeIndex":30,"conditionCode":"PartlyCloudyDay","night":{"conditionCodeIndex":29,"conditionCode":"PartlyCloudyNight"}},"mostlysunny":{"conditionCodeIndex":34,"conditionCode":"FairDay","night":{"conditionCodeIndex":33,"conditionCode":"FairNight"}},"mostlycloudy":{"conditionCodeIndex":28,"conditionCode":"MostlyCloudyDay","night":{"conditionCodeIndex":27,"conditionCode":"MostlyCloudyNight"}},"hazy":{"conditionCodeIndex":21,"conditionCode":"Haze","night":{"conditionCodeIndex":29,"conditionCode":"PartlyCloudyNight"}},"fog":{"conditionCodeIndex":20,"conditionCode":"Foggy"},"flurries":{"conditionCodeIndex":13,"conditionCode":"SnowFlurries"},"clear":{"conditionCodeIndex":32,"conditionCode":"Sunny","night":{"conditionCodeIndex":31,"conditionCode":"ClearNight"}},"chancetstorms":{"conditionCodeIndex":38,"conditionCode":"ScatteredThunderstorms"},"chancesnow":{"conditionCodeIndex":42,"conditionCode":"ScatteredSnowShowers"},"chancesleet":{"conditionCodeIndex":6,"conditionCode":"MixedRainAndSleet"},"chancerain":{"conditionCodeIndex":40,"conditionCode":"ScatteredShowers"},"chanceflurries":{"conditionCodeIndex":13,"conditionCode":"SnowFlurries"}}
        self.conditionTerm=conditionTerm.replace("nt_","")
        self.night = night
        
        if (conditionsArray[self.conditionTerm].has_key("night")) and (self.night==True):
            self.result["conditionCode"]=conditionsArray[self.conditionTerm]["night"]["conditionCode"]
            self.result["conditionCodeIndex"]=conditionsArray[self.conditionTerm]["night"]["conditionCodeIndex"]
        else:
            self.result["conditionCode"]=conditionsArray[self.conditionTerm]["conditionCode"]
            self.result["conditionCodeIndex"]=conditionsArray[self.conditionTerm]["conditionCodeIndex"]        
        
        return self.result



class weatherPlugin(Plugin):
    localizations = {"weatherForecast": 
                        {"search":{
                            0:{"de-DE": u"Einen Moment Geduld bitte...", "en-US": u"Checking my sources..."},
                            1:{"de-DE": u"Ich suche nach der Vorhersage ...", "en-US": u"Please wait while I check that..."},
                            2:{"de-DE": u"Einen Moment bitte ...", "en-US": u"One moment please..."},
                            3:{"de-DE": u"Ich suche nach Wetterdaten...", "en-US": u"Trying to get weather data for this location..."},
                            }, 
                        "forecast":{
                            "DAILY": {
                                0:{"de-DE": u"Hier ist die Vorhersage für {0}, {1}", "en-US": u"Here is the forecast for {0}, {1}"},
                                1:{"de-DE": u"Hier ist die Wetterprognose für {0}, {1}", "en-US": u"This is the forecast for {0}, {1}"},
                                2:{"de-DE": u"Ich habe folgende Vorhersage für {0}, {1} gefunden", u"en-US": "I found the following forecast for {0}, {1}"},
                                },
                            "HOURLY": {
                                0:{"de-DE": u"Hier ist die heutige Vorhersage für {0}, {1}", "en-US": u"Here is today's forecast for {0}, {1}"},
                                1:{"de-DE": u"Hier ist die Wetterprognose von heute für {0}, {1}", "en-US": u"This is today's forecast for {0}, {1}"},
                                2:{"de-DE": u"Ich habe folgende Tagesprognose für {0}, {1} gefunden", "en-US": u"I found the following hourly forecast for {0}, {1}"},
                                }
                            },
                        "failure": {
                                   "de-DE": "Ich konnte leider keine Wettervorhersage finden!", "en-US": "I'm sorry but I could not find the forecast for this location!"
                                   }
                            }
                        }
        
    @register("de-DE", "(.*Wetter.*)|(.*Vorhersage.*)")     
    @register("en-US", "(.*Weather.*)|(.*forecast.*)")
    def weatherForecastLookUp(self, speech, language):
        speech = speech.replace(u".","")
        viewType ="DAILY"
        if (speech.count("today") > 0 or speech.count("current") > 0 or speech.count(" for today") > 0) and language=="en-US":
            viewType = "HOURLY"
            speech = speech.replace("todays","")
            speech = speech.replace("today","")
            speech = speech.replace("currently","")
            speech = speech.replace("current","")
            speech = speech.replace(" for today"," in ")
            speech = speech.replace(" for "," in ")
        if (speech.count("heute") > 0 or speech.count("moment") > 0 or speech.count(u"nächsten Stunden") > 0 or speech.count(u"für heute") > 0) and language=="de-DE":
            viewType = "HOURLY"
            speech = speech.replace("heute","")
            speech = speech.replace("im moment","")
            speech = speech.replace("momentan","")
            speech = speech.replace("aktuelle","")
            speech = speech.replace("aktuell","")
            speech = speech.replace(u"in den nächsten Stunden","")
            speech = speech.replace(u"für heute","")
        
        if language=="en-US":
            speech = speech.replace(" for "," in ")
            
        if language=="de-DE":
            speech = speech.replace(u"in den nächsten Tagen","")
            speech = speech.replace(u"in den nächsten paar Tagen","")
            speech = speech.replace(u"in der nächsten Woche","")
            speech = speech.replace(u"nächste Woche","")
            speech = speech.replace(u" für "," in ")

                
        error = False
        view = AddViews(refId=self.refId, dialogPhase="Reflection")
        print weatherPlugin.localizations
        randomNumber = random.randint(0,3)
        view.views = [AssistantUtteranceView(weatherPlugin.localizations['weatherForecast']['search'][randomNumber][language], weatherPlugin.localizations['weatherForecast']['search'][randomNumber][language])]
        self.connection.send_object(view)
        
        

        
                
        
        countryOrCity = re.match("(?u).* in ([\w ]+)", speech, re.IGNORECASE)
        if countryOrCity != None:
            countryOrCity = countryOrCity.group(1).strip()
            print "found forecast"
            # lets see what we got, a country or a city... 
            # lets use google geocoding API for that
            url = "http://maps.googleapis.com/maps/api/geocode/json?address={0}&sensor=false&language={1}".format(urllib.quote_plus(countryOrCity.encode("utf-8")), language)
        elif countryOrCity == None:
            currentLocation=self.getCurrentLocation()
            url = "http://maps.googleapis.com/maps/api/geocode/json?latlng={0},{1}&sensor=false&language={2}".format(str(currentLocation.latitude),str(currentLocation.longitude), language)
           
            # lets wait max 3 seconds
        jsonString = None
        try:
            jsonString = urllib2.urlopen(url, timeout=3).read()
        except:
            pass
        if jsonString != None:
            response = json.loads(jsonString)
            # lets see what we have...
            if response['status'] == 'OK':
                components = response['results'][0]['address_components']
                types = components[0]['types'] # <- this should be the city or country
                if "country" in types:
                    # OK we have a country as input, that sucks, we need the capital, lets try again and ask for capital also
                    components = filter(lambda x: True if "country" in x['types'] else False, components)
                    url = "http://maps.googleapis.com/maps/api/geocode/json?address=capital%20{0}&sensor=false&language={1}".format(urllib.quote_plus(components[0]['long_name']), language)
                        # lets wait max 3 seconds
                    jsonString = None
                    try:
                        jsonString = urllib2.urlopen(url, timeout=3).read()
                    except:
                        pass
                    if jsonString != None:
                        response = json.loads(jsonString)
                        if response['status'] == 'OK':
                            components = response['results'][0]['address_components']
            # response could have changed, lets check again, but it should be a city by now 
            if response['status'] == 'OK':
                # get latitude and longitude
                location = response['results'][0]['geometry']['location']
                
                
                city = filter(lambda x: True if "locality" in x['types'] or "administrative_area_level_1" in x['types'] else False, components)[0]['long_name']
                country = filter(lambda x: True if "country" in x['types'] else False, components)[0]['long_name']
                state = filter(lambda x: True if "administrative_area_level_1" in x['types'] or "country" in x['types'] else False, components)[0]['short_name']
                stateLong = filter(lambda x: True if "administrative_area_level_1" in x['types'] or "country" in x['types'] else False, components)[0]['long_name']
                countryCode = filter(lambda x: True if "country" in x['types'] else False, components)[0]['short_name']
                url = "http://api.wunderground.com/api/{0}/geolookup/conditions/forecast7day//hourly7day/astronomy/q/{1},{2}.json".format(weatherApiKey, location['lat'], location['lng'])
                 # lets wait max 3 seconds
                jsonString = None
                try:
                    jsonString = urllib2.urlopen(url, timeout=5).read()
                except:
                    pass
                if jsonString != None:
                    response = json.loads(jsonString)
                    # lets see what we have...
                    if response.has_key("error")==False:
                        weatherTemp=dict()
                        if response.has_key("current_observation"):
                            if response.has_key("moon_phase"):
                                if (int(response["moon_phase"]["current_time"]["hour"]) > int(response["moon_phase"]["sunset"]["hour"])) or (int(response["moon_phase"]["current_time"]["hour"]) < int(response["moon_phase"]["sunrise"]["hour"])):
                                    weatherTempNightTime = True
                                    
                                else:
                                   weatherTempNightTime = False
                            else:
                                weatherTempNightTime = False
                                
                            conditionSwapper = SiriWeatherFunctions()
                            dayOfWeek=[] #
                            for i in range(1,8):
                                dayOfWeek.append(i % 7 + 1)
                            
                            tempNight=weatherTempNightTime
                            weatherTemp["currentTemperature"] =str(response["current_observation"]["temp_c"])
                            dailyForecasts=[]
                            for x in range(0,6):
                                forecastDate = date(int(response["forecast"]["simpleforecast"]["forecastday"][x]["date"]["year"]),int(response["forecast"]["simpleforecast"]["forecastday"][x]["date"]["month"]),int(response["forecast"]["simpleforecast"]["forecastday"][x]["date"]["day"]))
                                
                                weatherTemp["tempCondition"] = conditionSwapper.swapCondition(conditionTerm=response["forecast"]["simpleforecast"]["forecastday"][x]["icon"], night=tempNight)
                                dailyForecasts.append(SiriForecastAceWeathersDailyForecast(timeIndex=(dayOfWeek[date.weekday(forecastDate)]), highTemperature=response["forecast"]["simpleforecast"]["forecastday"][x]["high"]["celsius"], lowTemperature=response["forecast"]["simpleforecast"]["forecastday"][x]["low"]["celsius"], condition=SiriForecastAceWeathersConditions(conditionCode=weatherTemp["tempCondition"]["conditionCode"], conditionCodeIndex=weatherTemp["tempCondition"]["conditionCodeIndex"])))
                                tempNight=False
                               
                            hourlyForecasts=[]
                            for x in range(0,10):
                                if response["hourly_forecast"][x]:
                                    if (int(response["moon_phase"]["current_time"]["hour"]) <= int(response["hourly_forecast"][x]["FCTTIME"]["hour"])) or (int(response["forecast"]["simpleforecast"]["forecastday"][0]["date"]["day"]) < int(response["hourly_forecast"][x]["FCTTIME"]["mday"])) or (int(response["forecast"]["simpleforecast"]["forecastday"][0]["date"]["month"]) < int(response["hourly_forecast"][x]["FCTTIME"]["mon"])):
                                        if response.has_key("hourly_forecast")==True:
                                            weatherTemp=dict()
                                            if response.has_key("current_observation"):
                                                if response.has_key("moon_phase"):
                                                    if (int(response["moon_phase"]["sunset"]["hour"]) < int(response["hourly_forecast"][x]["FCTTIME"]["hour"])) or (int(response["moon_phase"]["sunrise"]["hour"]) > int(response["hourly_forecast"][x]["FCTTIME"]["hour"])):
                                                         weatherTempCon = conditionSwapper.swapCondition(conditionTerm=response["hourly_forecast"][x]["icon"], night=True)
                                       
                                                        
                                                    else:
                                                       weatherTempCon = conditionSwapper.swapCondition(conditionTerm=response["hourly_forecast"][x]["icon"], night=False)
                                       
                                                else:
                                                    weatherTempCon = conditionSwapper.swapCondition(conditionTerm=response["hourly_forecast"][x]["icon"], night=True)
                                       
                                    
                                        hourlyForecasts.append(SiriForecastAceWeathersHourlyForecast(timeIndex=response["hourly_forecast"][x]["FCTTIME"]["hour"], chanceOfPrecipitation=int(response["hourly_forecast"][x]["pop"]), temperature=response["hourly_forecast"][x]["temp"]["metric"],  condition=SiriForecastAceWeathersConditions(conditionCode=weatherTempCon["conditionCode"], conditionCodeIndex=weatherTempCon["conditionCodeIndex"])))
                                        
                            weatherTemp["currentCondition"] = conditionSwapper.swapCondition(conditionTerm=response["current_observation"]["icon"], night=weatherTempNightTime)
                            currentTemperature=str(response["current_observation"]["temp_c"])
                            currentDate=date(int(response["forecast"]["simpleforecast"]["forecastday"][0]["date"]["year"]),int(response["forecast"]["simpleforecast"]["forecastday"][0]["date"]["month"]),int(response["forecast"]["simpleforecast"]["forecastday"][0]["date"]["day"]))
                            view = AddViews(self.refId, dialogPhase="Summary")
                            
                            currentConditions=SiriForecastAceWeathersCurrentConditions(dayOfWeek=dayOfWeek[int(date.weekday(currentDate))],temperature=currentTemperature, condition=SiriForecastAceWeathersConditions(conditionCode=weatherTemp["currentCondition"]["conditionCode"], conditionCodeIndex=weatherTemp["currentCondition"]["conditionCodeIndex"]))
                            
                            aceWethers=[SiriForecastAceWeathers(extendedForecastUrl = response["location"]["wuiurl"], currentConditions=currentConditions, hourlyForecasts=hourlyForecasts, dailyForecasts=dailyForecasts, weatherLocation=SiriForecastAceWeathersWeatherLocation(), units=SiriForecastAceWeathersUnits(), view=viewType, )]
                            weather = SiriForecastSnippet(aceWeathers=aceWethers)
                            speakCountry = stateLong if country == "United States" else country
                            if language=="de-DE":
                                speakCountry = stateLong + " (" + country + ")" if country == "USA" else country
                                
                            randomNumber = random.randint(0,2)
                            view.views = [AssistantUtteranceView(text=weatherPlugin.localizations['weatherForecast']['forecast'][viewType][randomNumber][language].format(city, speakCountry),speakableText=weatherPlugin.localizations['weatherForecast']['forecast'][viewType][randomNumber][language].format(city,speakCountry), dialogIdentifier="Weather#forecastCommentary"), weather]
                            self.sendRequestWithoutAnswer(view)
                        else:
                            error = True
                    else:
                        error = True
                else:
                    error = True
            else:
                error = True
        else:
            error = True
                           
                         
                                    
        if error:                           
            self.say(weatherPlugin.localizations['weatherForecast']['failure'][language])
        self.complete_request()

########NEW FILE########
__FILENAME__ = whereAmI
#!/usr/bin/python
# -*- coding: utf-8 -*-

#need help? ask john-dev
 
import re
import urllib2, urllib
import json
 
from plugin import *
 
from siriObjects.baseObjects import AceObject, ClientBoundCommand
from siriObjects.systemObjects import GetRequestOrigin
from siriObjects.uiObjects import AddViews, AssistantUtteranceView
from siriObjects.mapObjects import SiriLocation, SiriMapItem, SiriMapItemSnippet

geonames_user="test2"
 
class whereAmI(Plugin):
    
    @register("de-DE", "(Wo bin ich.*)")    
    @register("en-US", "(Where am I.*)")
    def whereAmI(self, speech, language):
        mapGetLocation = self.getCurrentLocation()
        latitude = mapGetLocation.latitude
        longitude = mapGetLocation.longitude
        url = u"http://maps.googleapis.com/maps/api/geocode/json?latlng={0},{1}&sensor=false&language={2}".format(str(latitude),str(longitude), language)
        try:
            jsonString = urllib2.urlopen(url, timeout=3).read()
        except:
            pass
        if jsonString != None:
            response = json.loads(jsonString)
            if response['status'] == 'OK':
                components = response['results'][0]['address_components']              
                street = filter(lambda x: True if "route" in x['types'] else False, components)[0]['long_name']
                stateLong= filter(lambda x: True if "administrative_area_level_1" in x['types'] or "country" in x['types'] else False, components)[0]['long_name']
                try:
                    postalCode= filter(lambda x: True if "postal_code" in x['types'] else False, components)[0]['long_name']
                except:
                    postalCode=""
                try:
                    city = filter(lambda x: True if "locality" in x['types'] or "administrative_area_level_1" in x['types'] else False, components)[0]['long_name']
                except:
                    city=""
                countryCode = filter(lambda x: True if "country" in x['types'] else False, components)[0]['short_name']
                view = AddViews(self.refId, dialogPhase="Completion")
                if language == "de-DE":
                    the_header="Dein Standort"
                else:
                    the_header="Your location"
                Location=SiriLocation(the_header, street, city, stateLong, countryCode, postalCode, latitude, longitude)
                mapsnippet = SiriMapItemSnippet(items=[SiriMapItem(the_header, Location)])
                view.views = [AssistantUtteranceView(text=the_header, dialogIdentifier="Map"), mapsnippet]
                self.sendRequestWithoutAnswer(view)
            else:
                if language=="de-DE":
                    self.say('Die Googlemaps informationen waren ungenügend!','Fehler')
                else:
                    self.say('The Googlemaps response did not hold the information i need!','Error')
        else:
            if language=="de-DE":
                self.say('Ich konnte keine Verbindung zu Googlemaps aufbauen','Fehler')
            else:
                self.say('Could not establish a conenction to Googlemaps','Error');
        self.complete_request()

########NEW FILE########
__FILENAME__ = wolfram
#!/usr/bin/python
# -*- coding: utf-8 -*-

#Author: WebScript
#Todo: Translate with my GTranslate API
#For: SiriServer
#Commands: The same as in original Wolfram Alpha in Siri
#If you find bug: email me - admin@game-host.eu

import re, urlparse
import urllib2, urllib
import json
from urllib2 import urlopen
from xml.dom import minidom

from plugin import *

from siriObjects.baseObjects import AceObject, ClientBoundCommand
from siriObjects.uiObjects import AddViews, AssistantUtteranceView
from siriObjects.answerObjects import AnswerSnippet, AnswerObject, AnswerObjectLine


APPID = APIKeyForAPI("wolframalpha")




class wolfram(Plugin):
    
    @register("de-DE", "(Was ist [a-zA-Z0-9]+)|(Wer ist [a-zA-Z0-9]+)|(Wie viel [a-zA-Z0-9]+)|(Was war [a-zA-Z0-9]+)|(Wer ist [a-zA-Z0-9]+)|(Wie lang [a-zA-Z0-9]+)|(Was ist [a-zA-Z0-9]+)|(Wie weit [a-zA-Z0-9]+)|(Wann ist [a-zA-Z0-9]+)|(Zeig mir [a-zA-Z0-9]+)|(Wie hoch [a-zA-Z0-9]+)|(Wie tief [a-zA-Z0-9]+)")     
    @register("en-US", "(What is [a-zA-Z0-9]+)|(Who is [a-zA-Z0-9]+)|(How many [a-zA-Z0-9]+)|(What was [a-zA-Z0-9]+)|(Who's [a-zA-Z0-9]+)|(How long [a-zA-Z0-9]+)|(What's [a-zA-Z0-9]+)|(How far [a-zA-Z0-9]+)|(When is [a-zA-Z0-9]+)|(Show me [a-zA-Z0-9]+)|(How high [a-zA-Z0-9]+)|(How deep [a-zA-Z0-9]+)")
    def wolfram(self, speech, language):
        if language == "en-US":
            wolframQuestion = speech.replace('who is ','').replace('what is ','').replace('what was ','').replace('Who is ','').replace('What is ','').replace('What was ','').replace(' ', '%20')
            wolframTranslation = 'false'
        elif language == "de-DE":
            wolframQuestion = speech.replace('wer ist ','').replace('was ist ', '').replace('Wer ist ','').replace('Was ist ', '').replace('Wie viel ','How much ').replace('Wie lang ','How long ').replace('Wie weit ','How far ').replace('Wann ist ','When is ').replace('Zeig mir ','Show me ').replace('Wie hoch ','How high ').replace('Wie tief ','How deep ').replace('ist','is').replace('der','the').replace('die','the').replace('das','the').replace('wie viel ','how much ').replace('wie lang ','how long ').replace('wie weit ','how far ').replace('wann ist ','when is ').replace('zeig mir ','show me ').replace('wie hoch ','how high ').replace('wie tief ','how deep ').replace('ist','is').replace('der','the').replace('die','the').replace('das','the').replace(' ', '%20').replace(u'ä', 'a').replace(u'ö', 'o').replace(u'ü', 'u').replace(u'ß', 's')
            wolframTranslation = 'true'
        else:
            wolframQuestion = speech.replace('who is ','').replace('what is ','').replace('what was ','').replace('Who is ','').replace('What is ','').replace('What was ','').replace(' ', '%20')
            wolframTranslation = 'false'
        wolfram_alpha = 'http://api.wolframalpha.com/v1/query.jsp?input=%s&appid=%s&translation=%s' % (wolframQuestion, APPID, wolframTranslation)
        dom = minidom.parse(urlopen(wolfram_alpha))
        count_wolfram = 0
        wolfram0 = 12
        wolfram_pod0 = 12
        wolfram0_img = 12
        wolfram1 = 12
        wolfram_pod1 = 12
        wolfram1_img = 12
        wolfram2 = 12
        wolfram_pod2 = 12
        wolfram2_img = 12
        wolfram3 = 12
        wolfram_pod3 = 12
        wolfram3_img = 12
        wolfram4 = 12
        wolfram_pod4 = 12
        wolfram4_img = 12
        wolfram5 = 12
        wolfram_pod5 = 12
        wolfram5_img = 12
        wolfram6 = 12
        wolfram_pod6 = 12
        wolfram6_img = 12
        wolfram7 = 12
        wolfram_pod7 = 12
        wolfram7_img = 12
        wolfram8 = 12
        wolfram_pod8 = 12
        wolfram8_img = 12
        wolframAnswer = 12
        wolframAnswer2 = 12
        wolframAnswer3 = 12
        wolframAnswer4 = 12
        wolframAnswer8 = 12
        query_list = dom.getElementsByTagName('queryresult')[-1]
        query_type = query_list.getAttribute('error')
        for node in dom.getElementsByTagName('queryresult'):
            for pod in node.getElementsByTagName('pod'):
               xmlTag = dom.getElementsByTagName('plaintext')[count_wolfram].toxml()
               xmlTag2 = dom.getElementsByTagName('subpod')[count_wolfram]
               xmlData=xmlTag.replace('<plaintext>','').replace('</plaintext>','')
               if count_wolfram == 0:
                  if xmlData == "<plaintext/>":
                      image_list = dom.getElementsByTagName('img')[count_wolfram]
                      image_type = image_list.getAttribute('src')
                      wolfram0 = image_type
                      wolfram0_img = 1
                  else:
                      wolfram0 = xmlData
                  wolfram_pod0 = pod.getAttribute('title')
               elif count_wolfram == 1:
                  if xmlData == "<plaintext/>":
                      image_list = dom.getElementsByTagName('img')[count_wolfram]
                      image_type = image_list.getAttribute('src')
                      wolfram1 = image_type
                      wolfram1_img = 1
                  else:
                      wolfram1 = xmlData
                  wolfram_pod1 = pod.getAttribute('title')
               elif count_wolfram == 2:
                  if xmlData == "<plaintext/>":
                     image_list = dom.getElementsByTagName('img')[count_wolfram]
                     image_type = image_list.getAttribute('src')
                     wolfram2 = image_type
                     wolfram2_img = 1
                  else:
                     wolfram2 = xmlData
                  wolfram_pod2 = pod.getAttribute('title')
               elif count_wolfram == 3:
                  if xmlData == "<plaintext/>":
                     image_list = dom.getElementsByTagName('img')[count_wolfram]
                     image_type = image_list.getAttribute('src')
                     wolfram3 = image_type
                     wolfram3_img = 1
                  else:
                     wolfram3 = xmlData
                  wolfram_pod3 = pod.getAttribute('title')
               elif count_wolfram == 4:
                  if xmlData == "<plaintext/>":
                     image_list = dom.getElementsByTagName('img')[count_wolfram]
                     image_type = image_list.getAttribute('src')
                     wolfram4 = image_type
                     wolfram4_img = 1
                  else:
                     wolfram4 = xmlData
                  wolfram_pod4 = pod.getAttribute('title')
               elif count_wolfram == 5:
                  wolfram5 = xmlData
                  wolfram_pod5 = pod.getAttribute('title')
               elif count_wolfram == 6:
                  wolfram6 = xmlData
                  wolfram_pod6 = pod.getAttribute('title')
               elif count_wolfram == 7:
                  wolfram7 = xmlData
                  wolfram_pod7 = pod.getAttribute('title')
               elif count_wolfram == 8:
                  wolfram8 = xmlData
                  wolfram_pod8 = pod.getAttribute('title')
               count_wolfram += 1
        if language == 'de-DE':
            self.say("Dies könnte Ihre Frage zu beantworten:")
        else:
            self.say("This might answer your question:")
        view = AddViews(self.refId, dialogPhase="Completion")
        if wolfram_pod0 != 12:
            if wolfram0_img == 1:
                wolframAnswer = AnswerObject(title=wolfram_pod0,lines=[AnswerObjectLine(image=wolfram0)])
            else:
                wolframAnswer = AnswerObject(title=wolfram_pod0,lines=[AnswerObjectLine(text=wolfram0)])
        else:
            print wolfram_pod0
        if wolfram_pod1 != 12:
            if wolfram1_img == 1:
                wolframAnswer1 = AnswerObject(title=wolfram_pod1,lines=[AnswerObjectLine(image=wolfram1)])
            else:
                wolframAnswer1 = AnswerObject(title=wolfram_pod1,lines=[AnswerObjectLine(text=wolfram1)])
        else:
            print wolfram_pod1
        if wolfram_pod2 != 12:
            if wolfram2_img == 1:
                wolframAnswer2 = AnswerObject(title=wolfram_pod2,lines=[AnswerObjectLine(image=wolfram2)])
            else:
                wolframAnswer2 = AnswerObject(title=wolfram_pod2,lines=[AnswerObjectLine(text=wolfram2)])
        else:
            print wolfram_pod2
        if wolfram_pod3 != 12:
            if wolfram3_img == 1:
                wolframAnswer3 = AnswerObject(title=wolfram_pod3,lines=[AnswerObjectLine(image=wolfram3)])
            else:
                wolframAnswer3 = AnswerObject(title=wolfram_pod3,lines=[AnswerObjectLine(text=wolfram3)])
        else:
            print wolfram_pod3
        if wolfram_pod4 != 12:
            if wolfram4_img == 1:
                wolframAnswer4 = AnswerObject(title=wolfram_pod4,lines=[AnswerObjectLine(image=wolfram4)])
            else:
                wolframAnswer4 = AnswerObject(title=wolfram_pod4,lines=[AnswerObjectLine(text=wolfram4)])
        else:
            print wolfram_pod4
        if wolfram_pod8 != 12:
            if wolfram8_img == 1:
                wolframAnswer8 = AnswerObject(title=wolfram_pod8,lines=[AnswerObjectLine(image=wolfram8)])
            else:
                wolframAnswer8 = AnswerObject(title=wolfram_pod8,lines=[AnswerObjectLine(text=wolfram8)])
        if wolfram_pod0 == 12:
            if APPID == "":
                self.say("Sorry I can't process your request. Your APPID is not set! Please register free dev account at http://wolframalpha.com and edit line 21 with you APPID.")
            else:
                if language == 'de-DE':
                    self.say("Es tut mir leid. Ich konnte keine Antwort auf Ihre Frage finden.")
                else:
                    self.say("Nothing has found for your query!")
            self.complete_request()
            view1 = 0
        elif wolfram_pod1 == 12:
            view1 = AnswerSnippet(answers=[wolframAnswer])
        elif wolfram_pod2 == 12:
            view1 = AnswerSnippet(answers=[wolframAnswer, wolframAnswer1])
        elif wolfram_pod3 == 12:
            view1 = AnswerSnippet(answers=[wolframAnswer, wolframAnswer1, wolframAnswer2])
        elif wolfram_pod4 == 12:
            view1 = AnswerSnippet(answers=[wolframAnswer, wolframAnswer1, wolframAnswer2, wolframAnswer3])
        elif wolfram_pod8 == 12:
            view1 = AnswerSnippet(answers=[wolframAnswer, wolframAnswer1, wolframAnswer2, wolframAnswer3, wolframAnswer4])
        else:
            view1 = AnswerSnippet(answers=[wolframAnswer, wolframAnswer1, wolframAnswer2, wolframAnswer3, wolframAnswer4, wolframAnswer8])
        view.views = [view1]
        self.sendRequestWithoutAnswer(view)
        self.complete_request()

########NEW FILE########
__FILENAME__ = wordnikDefinitions
#!/usr/bin/python
# -*- coding: utf-8 -*-

#Wordnik plugin
#by Ryan Davis (neoshroom)
#feel free to add to, mess with, use this plugin with original attribution
#additional Wordnik functions to add can be found at:
#http://developer.wordnik.com/docs/

from plugin import *
#you will need to install the Wordnik API to use this
#this can be done from the commandline by typing: easy_install Wordnik
try:
   from wordnik import Wordnik
except ImportError:
   raise NecessaryModuleNotFound("Wordnik library not found. Please install wordnik library! e.g. sudo easy_install wordnik")

#You need a wordnik api key, you can get yours at http://developer.wordnik.com/ (first you sign up for a username in the upp$
########################################################

wordnik_api_key = APIKeyForAPI("wordnik")

#########################################################

w = Wordnik(api_key=wordnik_api_key)

class define(Plugin):
    
    @register("en-US", "define ([\w ]+)")
    def defineword(self, speech, language, regMatched):
        Question = regMatched.group(1)
        output = w.word_get_definitions(Question, limit=1)
        if len(output) == 1:
            answer = dict(output[0])
            if u'text' in answer:
                worddef = answer[u'text']
                if worddef:
                    self.say(worddef, "The definition of {0} is: {1}".format(Question, worddef))
                else:
                    self.say("Sorry, I could not find " + Question + " in the dictionary.")
        else:
            self.say("Sorry, I could not find " + Question + " in the dictionary.")

        self.complete_request()

########NEW FILE########
__FILENAME__ = wwwsearch
#!/usr/bin/python                                                                                                                                                                   
# -*- coding: utf-8 -*-                                                                                                                                                             

from plugin import *
from siriObjects.websearchObjects import WebSearch

class wwwSearch(Plugin):
    @register("de-DE", "(websuche.*)|(web suche.*)|(internetsuche.*)|(internet suche.*)|(web.*)|(internet.*)")
    @register("en-US", "(web search.*)|(web.*)|(internet.*)|(internet search.*)")
    def webSearch(self, speech, language):
        if (language == "en-US"):
            if (speech.find('Web search') == 0):
                speech = speech.replace('Web search', ' ',1)
            elif (speech.find('Web') == 0):
                speech = speech.replace('Web',' ',1)
            elif (speech.find('Internet search') == 0):
                speech = speech.replace('Internet search',' ',1)
            elif (speech.find('Internet') == 0):
                speech = speech.replace('Internet',' ',1)
            speech = speech.strip()
            if speech == "":
                speech = self.ask("What is your query?")
        elif (language == "de-DE"):
            if (speech.find('Websuche') == 0):
                speech = speech.replace('Websuche',' ',1)
            elif (speech.find('Web suche') == 0):
                speech = speech.replace('Web suche',' ',1)
            elif (speech.find('Internetsuche') == 0):
                speech = speech.replace('Internetsuche',' ',1)
            elif (speech.find('Internet suche') == 0):
                speech = speech.replace('Internet suche',' ',1)
            elif (speech.find('Web') == 0):
                speech = speech.replace('Web',' ',1)
            elif (speech.find('Internet') == 0):
                speech = speech.replace('Internet',' ',1)
            speech = speech.strip()
            if speech == "":
                speech = self.ask("Nach was soll ich suchen?")

        search = WebSearch(refId=self.refId, query=speech)
        self.sendRequestWithoutAnswer(search)
        self.complete_request()



########NEW FILE########
__FILENAME__ = XBMC
# Author: Gustavo Hoirisch, Pieter Janssens
#
#
#!/usr/bin/python
# -*- coding: utf-8 -*-
#
#
# Note: This XBMC plugin is designed for XBMC RPC V3, this means that it works best with XBMC Eden and up.

from plugin import *
import urllib2, urllib, socket, struct, logging, re

from siriObjects.uiObjects import AddViews
from siriObjects.answerObjects import AnswerSnippet, AnswerObject, AnswerObjectLine

try: 
    import jsonrpclib
except ImportError: 
    raise NecessaryModuleNotFound('XBMC plugin will not work: JSONRPCLIB not installed. To install, run "easy_install jsonrpclib"')

class XBMC_object():
    def __init__(self, host='appletv.local', port='8080', username=None, password=None, mac_address=None):
        self.username = username
        self.password = password
        self.port = port
        self.host = host
        self.mac_address = mac_address
        
    def get_url(self):
        return 'http://%s%s:%s' %(self.get_user_pass(), self.host, self.port)
        
    def get_user_pass(self):
        if self.username != None and self.password != None:
            return '%s:%s@' % (self.username, self.password) 
        return ''
        
    def get_thumburl(self):
        return 'http://%s:%s/vfs/' % (self.host, self.port)

    def play(self,json,item):
        json.Playlist.Clear(playlistid=1)
        json.Playlist.Add(playlistid=1, item=item)
        json.Player.Open({ 'playlistid': 1 })

class XBMC(Plugin):	    

    def addPictureView(self,title,image_url):
        view = AddViews(self.refId, dialogPhase="Completion")
        ImageAnswer = AnswerObject(title=title,lines=[AnswerObjectLine(image=image_url)])
        view1 = AnswerSnippet(answers=[ImageAnswer])
        view.views = [view1]
        self.sendRequestWithoutAnswer(view)
        
    global xbmc
    xbmc = XBMC_object()
            
    @register("en-US", "(xbmc)|(xbmc.* [a-z]+)")
    def test2(self, speech, language):
        global xbmc
        if speech.lower() == 'xbmc':
            self.say("XBMC currently supports the following commands: play [movie or tv show], play latest episode of [tv show], play trailer for [movie] pause, stop, shut down, start and info.")
        else:
            firstword, command=speech.split(' ',1)
            json = jsonrpclib.Server('%s/jsonrpc' % (xbmc.get_url()))
            if command == 'stop':
                try:
                    json.Player.Stop(playerid=1)
                except:
                    self.say('Nothing to stop...')
            elif command == 'play' or command == 'pause' or command == 'plate' or command == 'place' or command == 'pas' or command == 'paws':
                try:
                    json.Player.PlayPause(playerid=1)
                except:
                    self.say('Nothing to play/pause')
            elif command == 'update library' or command == 'scan':
                json.VideoLibrary.Scan()
            elif command == 'clean library':
                json.VideoLibrary.Clean()
            elif command == 'latest movies':
                recentMovies = json.VideoLibrary.GetRecentlyAddedMovies(properties=['playcount'])['movies']
                movieList = ''
                for movie in recentMovies:
                    if movie['playcount'] > 0:
                        watched = 'Watched: Yes'
                    else:
                        watched = 'Watched: No'
                    movieList = movieList + movie['label'] + '\n' + watched + '\n\n'
                self.say(movieList, "Here you go:")
            elif command == 'latest episodes':
                recentEpisodes = json.VideoLibrary.GetRecentlyAddedEpisodes(properties=['showtitle','season','episode','playcount'])['episodes']
                episodeList = ''
                for episode in recentEpisodes:
                    ep = '%s\nS%02dE%02d: %s\n' % (episode['showtitle'],episode['season'],episode['episode'],episode['label'])
                    if episode['playcount'] > 0:
                        watched = 'Watched: Yes'
                    else:
                        watched = 'Watched: No'
                    episodeList = episodeList + ep + watched + '\n\n'
                self.say(episodeList, "Here you go:")
            elif 'play trailer of' in command or 'play trailer for' in command or 'play trailer 4' in command:
                if 'play trailer of' in command:
                    title = command.replace('play trailer of ','')
                elif 'play trailer for' in command:
                    title = command.replace('play trailer for ', '')
                elif 'play trailer 4' in command:
                    title = command.replace('play trailer 4 ', '')
                result = json.VideoLibrary.GetMovies()
                stripped_title = ''.join(ch for ch in title if ch.isalnum()).lower()
                for movie in result['movies']:
                    if stripped_title in ''.join(ch for ch in movie['label'] if ch.isalnum()).lower():
                        movieid = movie['movieid']
                        trailer = json.VideoLibrary.GetMovieDetails(movieid=movieid, properties= ['trailer'])['moviedetails']['trailer']
                        break
                if trailer:
                    xbmc.play(json,{'file':trailer})
                else:
                    self.say("It seems that there is no trailer available for this movie.")
            elif 'play' in command or 'plate' in command or 'place' in command or 'played' in command or 'start' in command:
                command, title=command.split(' ',1)
                if 'first occurrence' in title:
                    first_match = True
                    title = title.replace(' first occurrence', '')
                else:
                    first_match = False
                print 'Searching for: '+title
                result = json.VideoLibrary.GetMovies()
                stripped_title = ''.join(ch for ch in title if ch.isalnum()).lower()
                matches = []
                for movie in result['movies']:
                    if stripped_title in ''.join(ch for ch in movie['label'] if ch.isalnum()).lower():
                        movieid = movie['movieid']
                        matches.append(movie['label'])
                        if first_match == True:
                            break
                if len(matches) > 0:
                    if len(matches) > 1:
                        self.say("Found multiple matches for '%s':" %(title))
                        names = ''
                        for x in matches:
                            names = names + x + '\n' 
                        self.say(names, None)
                        self.say("To play the first one add 'first occurrence' at the end of your command")
                    else:
                        self.say('%s starting'%(matches[0]))
                        details = json.VideoLibrary.GetMovieDetails(movieid=movieid, properties= ['thumbnail','year','rating'])['moviedetails']
                        image_url = "%s%s" % (xbmc.get_thumburl(),details['thumbnail'])
                        title = "%s (%s) - %s/10" % (details['label'],details['year'],round(details['rating'],1))
                        self.addPictureView(title,image_url)
                        xbmc.play(json,{'movieid': movieid})
                else:
                    result = json.VideoLibrary.GetTVShows()
                    tvmatches = []
                    
                    if 'thelatestepisodeof' in stripped_title:
                        stripped_title = stripped_title.replace('thelatestepisodeof','')
                        latest_episode = True
                    elif 'latestepisodeof' in stripped_title:
                        stripped_title = stripped_title.replace('latestepisodeof','')
                        latest_episode = True
                    elif 'latestepisode' in stripped_title:
                        stripped_title = stripped_title.replace('latestepisode','')
                        latest_episode = True
                    else:
                        latest_episode = False
                    
                    for tvshow in result['tvshows']:
                        if stripped_title in ''.join(ch for ch in tvshow['label'] if ch.isalnum()).lower():
                            tvshowid = tvshow['tvshowid']
                            matches.append(tvshow['label'])
                    if len(matches) > 0:
                        if len(matches) > 1:
                            self.say("Found multiple matches for '%s':" %(title))
                            names = ''
                            for x in matches:
                                names = names + x + '\n'
                            self.say(names,None)
                        else:
                            result = json.VideoLibrary.GetEpisodes(tvshowid=tvshowid,properties=['playcount','showtitle','season','episode'])
                            if latest_episode == True:
                                episode = result['episodes'][len(result['episodes'])-1]
                                episodeid = episode['episodeid']
                                play = True
                                if episode['playcount'] > 0:
                                    self.say("Warning: it seems that you already watched this episode.",None)
                            else: 
                                allwatched = True
                                for episode in result['episodes']:
                                    if episode['playcount'] == 0:
                                        episodeid=episode['episodeid']
                                        allwatched = False
                                        play = True
                                        break
                                if allwatched == True:
                                    self.say('There are no unwatched and/or new episodes of %s' %(title))
                                    play = False
                            if play == True:
                                details = json.VideoLibrary.GetTVShowDetails(tvshowid=tvshowid, properties= ['thumbnail','rating'])['tvshowdetails']
                                image_url = "%s%s" % (xbmc.get_thumburl(),details['thumbnail'])
                                title = "%s - %s/10" % (details['label'],round(details['rating'],1))
                                self.say('Playing %s, season %s, episode %s.' %(episode['showtitle'], episode['season'], episode['episode']))
                                self.addPictureView(title,image_url)
                                xbmc.play(json,{ 'episodeid': episodeid })
                    else:
                        self.say('No movies or TV shows matching: %s.' % (title))
            elif command == 'info':
                self.say("XBMC URL: %s" %(xbmc.get_url()), None)
                info = """username: %s\
                password: %s\
                hostname: %s\
                port: %s """ %(xbmc.username, xbmc.password, xbmc.host, xbmc.port)
                self.say(info, None)
            elif command == 'shut down' or command == 'shutdown' or command == 'turn off':
                self.say("XBMC going down")
                json.System.Shutdown()
            elif command == 'boot' or command == 'start' or command == 'boot up':
                addr_byte = xbmc.mac_address.split(':')
                hw_addr = struct.pack('BBBBBB',
                int(addr_byte[0], 16),
                int(addr_byte[1], 16),
                int(addr_byte[2], 16),
                int(addr_byte[3], 16),
                int(addr_byte[4], 16),
                int(addr_byte[5], 16))
                msg = '\xff' * 6 + hw_addr * 16
                s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
                s.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
                s.sendto(msg, ("255.255.255.255", 9))
            else:
                self.say("XBMC command not recognized: %s."%(command))
        self.complete_request()

########NEW FILE########
__FILENAME__ = alarmObjects
from siriObjects.baseObjects import ClientBoundCommand, ServerBoundCommand, AceObject
from siriObjects.systemObjects import DomainObject
from siriObjects.uiObjects import Snippet


class AlarmObject(DomainObject):
    def __init__(self, label = None, minute = None, hour = None, frequency = None, enabled = None):
        super(AlarmObject, self).__init__("com.apple.ace.alarm")
        self.relativeOffsetMinutes = None
        self.label = label
        self.minute = minute
        self.hour = hour
        self.frequency = frequency
        self.enabled = 1
    
    def to_plist(self):
        self.add_property('relativeOffsetMinutes')
        self.add_property('minute')
        self.add_property('label')
        self.add_property('hour')
        self.add_property('frequency')
        self.add_property('enabled')
        return super(AlarmObject, self).to_plist()

class AlarmCreate(ClientBoundCommand):
    def __init__(self, refId, alarm = None):
        super(AlarmCreate, self).__init__("Create", "com.apple.ace.alarm", None, refId)      
        self.alarmToCreate = alarm
    
    def to_plist(self):
        self.add_property('alarmToCreate')
        return super(AlarmCreate, self).to_plist()

class AlarmCreateCompleted(ServerBoundCommand):
    classIdentifier = "CreateCompleted"
    groupIdentifier = "com.apple.ace.alarm"
    def __init__(self, plist):
        self.alarmId
        super(AlarmCreateCompleted, self).__init__(plist)

class AlarmDelete(ClientBoundCommand):
    def __init__(self, refId):
        super(AlarmDelete, self).__init__("Delete", "com.apple.ace.alarm", None, refId)
        self.alarmIds = None #array
        self.targetAppId = None

    def to_plist(self):
        self.add_property('alarmIds')
        self.add_property('targetAppId')
        return super(AlarmDelete, self).to_plist()


class AlarmDeleteCompleted(ServerBoundCommand):
    classIdentifier = "DeleteCompleted"
    groupIdentifier = "com.apple.ace.alarm"
    def __init__(self, plist):
        super(AlarmDeleteCompleted, self).__init__(plist)


class AlarmSearch(ClientBoundCommand):
    def __init__(self, refId):
        super(AlarmSearch, self).__init__("Search", "com.apple.ace.alarm", None, refId)
        self.minute = None # number
        self.label = None # string
        self.identifier = None #url
        self.hour = None #number
        self.frequency = None #array
        self.enabled = None # number
        self.targetAppId = None # url

    def to_plist(self):
        self.add_property('minute')
        self.add_property('label')
        self.add_property('identifier')
        self.add_property('hour')
        self.add_property('frequency')
        self.add_property('enabled')
        self.add_property('targetAppId')
        return super(AlarmSearch, self).to_plist()


class AlarmSearchCompleted(ServerBoundCommand):
    classIdentifier = "SearchCompleted"
    groupIdentifier = "com.apple.ace.alarm"
    def __init__(self, plist):
        self.results = None # array
        super(AlarmSearchCompleted, self).__init__(plist)


class AlarmSnippet(Snippet):                
    def __init__(self, alarms = None):
        super(AlarmSnippet, self).__init__("com.apple.ace.alarm")
        self.alarms = alarms if alarms != None else []
    
    def to_plist(self):
        self.add_property('alarms')
        return super(AlarmSnippet, self).to_plist()
        
class AlarmUpdate(ClientBoundCommand):
    def __init__(self, refId):
        super(AlarmUpdate, self).__init__("Update", "com.apple.ace.alarm", None, refId)
        self.removedFrequency = None # array
        self.minute = None # number
        self.label = None #string
        self.hour = None # number
        self.enabled = None # number
        self.alarmId = None # url
        self.addedFrequency = None # array
        self.targetAppId = None # url

    def to_plist(self):
        self.add_property('removedFrequency')
        self.add_property('minute')
        self.add_property('label')
        self.add_property('hour')
        self.add_property('enabled')
        self.add_property('alarmId')
        self.add_property('addedFrequency')
        self.add_property('targetAppId')
        return super(AlarmUpdate, self).to_plist()

class AlarmUpdateCompleted(ServerBoundCommand):
    groupIdentifier = "com.apple.ace.alarm"
    classIdentifier = "UpdateCompleted"
    def __init__(self, plist):
        self.alarmId = None #url
        super(AlarmUpdateCompleted, self).__init__(plist)
########NEW FILE########
__FILENAME__ = answerObjects
from siriObjects.baseObjects import AceObject, ClientBoundCommand
from siriObjects.uiObjects import Snippet
from siriObjects.systemObjects import DomainObject

class AnswerSnippet(Snippet):
    def __init__(self, answers=None):
        super(AnswerSnippet, self).__init__("com.apple.ace.answer")
        self.answers = answers if answers != None else []

    def to_plist(self):
        self.add_property('answers')
        return super(AnswerSnippet, self).to_plist()

class AnswerObject(DomainObject):
    def __init__(self, title=None, lines=None):
        super(AnswerObject, self).__init__("com.apple.ace.answer")
        self.title = title
        self.lines = lines if lines != None else []

    def to_plist(self):
        self.add_property('title')
        self.add_property('lines')
        return super(AnswerObject, self).to_plist()

class AnswerObjectLine(AceObject):
    def __init__(self, text="", image=""):
        super(AnswerObjectLine, self).__init__("ObjectLine", "com.apple.ace.answer")
        self.text = text
        self.image = image

    def to_plist(self):
        self.add_property('text')
        self.add_property('image')
        return super(AnswerObjectLine, self).to_plist()

########NEW FILE########
__FILENAME__ = baseObjects
from uuid import uuid4
import logging

class AceObject(object):
    def __init__(self, encodedClassName, groupIdentifier):
        self.className = encodedClassName
        self.groupId = groupIdentifier
        self.plist = dict()
        self.properties = dict()
    
    def add_item(self, name):
        try:
            if getattr(self, name) != None and getattr(self, name) != "":
                self.plist[name] = getattr(self, name) 
        except AttributeError:
            logging.getLogger("logger").exception("You tried to set the item \"{0}\", but this instance of class: \"{1}\" does not have a member variable named like this".format(name, self.__class__))

    def add_property(self, name):
        try:
            if getattr(self,name) != None:
                self.properties[name] = getattr(self, name) 
        except AttributeError:
            logging.getLogger("logger").exception("You tried to set the property \"{0}\", but this instance of class: \"{1}\" does not have a member variable named like this".format(name, self.__class__))

    @staticmethod
    def list_to_plist(newList):
        def parseList(x):
            if type(x) == list:
                new = AceObject.list_to_plist(x)
            elif type(x) == dict:
                new = AceObject.dict_to_plist(x)
            else:
                try:
                    new = x.to_plist()
                except:
                    new = x
            return new

        return map(parseList, newList)

    @staticmethod
    def dict_to_plist(newDict):
        def parseDict((k,v)):
            if type(v) == list:
                new = AceObject.list_to_plist(v)
            elif type(v) == dict:
                new = AceObject.dict_to_plist(v)
            else:
                try:
                    new = v.to_plist()
                except:
                    new = v
            return (k,new)
                
        return dict(map(parseDict, newDict.items()))

    def to_plist(self):
        self.plist['group'] = self.groupId
        self.plist['class'] = self.className
        self.plist['properties'] = self.properties

        for key in self.plist.keys():
            if type(self.plist[key]) == list:
                self.plist[key] = AceObject.list_to_plist(self.plist[key])
            elif type(self.plist[key]) == dict:
                self.plist[key] = AceObject.dict_to_plist(self.plist[key])
            else:
                try:
                    self.plist[key] = self.plist[key].to_plist() 
                except:
                    pass
        return self.plist

    @staticmethod
    def list_from_plist_list(plistList):
        def parseList(x):
            if type(x) == list:
                return AceObject.list_from_plist_list(x)
            elif type(x) == dict:
                return ServerBoundCommand(x)
            else:
                # do nothing.. primitive
                return x
        return map(parseList, plistList)


    def from_plist(self):
        # get basic properties
        self.groupId = self.plist['group']
        self.className = self.plist['class']
        self.properties = self.plist['properties'] if 'properties' in self.plist else dict()
        
        #expand properties to
        for key in self.properties.keys():
            if type(self.properties[key]) == list:
                setattr(self, key, AceObject.list_from_plist_list(self.properties[key]))
            elif type(self.properties[key]) == dict: #unwrap 
                setattr(self, key, ServerBoundCommand(self.properties[key]))
            else:
                try:
                    setattr(self, key, self.properties[key])
                except:
                    pass

    def initWithPList(self, plist):
        self.plist = plist
        self.from_plist()
        
class ServerBoundCommand(AceObject):
    def __init__(self, plist):
        super(ServerBoundCommand, self).__init__(None, None)
        self.aceId = plist['aceId'] if 'aceId' in plist else None
        self.refId = plist['refId'] if 'refId' in plist else None
        self.plist = plist
        self.from_plist()

class ClientBoundCommand(AceObject):
    def __init__(self, encodedClassName, groupIdentifier, aceId, refId, callbacks=None):
        super(ClientBoundCommand, self).__init__(encodedClassName, groupIdentifier)
        self.aceId= aceId if aceId != None else str.upper(str(uuid4()))
        self.refId = refId if refId != None else str.upper(str(uuid4()))
        self.callbacks = callbacks if callbacks != None else []
    
    def to_plist(self):
        self.add_item('aceId')
        self.add_item('refId')
        self.add_property('callbacks')
        return super(ClientBoundCommand, self).to_plist()


class RequestCompleted(ClientBoundCommand):
    def __init__(self, refId, callbacks = None):
        super(RequestCompleted, self).__init__("RequestCompleted", "com.apple.ace.system", None, refId, callbacks)


def ObjectIsCommand(obj, command):
    try:
        if issubclass(command, ServerBoundCommand):
            group = obj['group']
            clazz = obj['class']
            if command.classIdentifier == clazz and command.groupIdentifier == group:
                return True
    except:
        pass
    return False
    
########NEW FILE########
__FILENAME__ = calendarObjects
from siriObjects.baseObjects import ClientBoundCommand, AceObject
from siriObjects.

class EventSearch(ClientBoundCommand):
    def __init__(self, refId, timeZoneId="America/Chicago", startDate=None, endDate=None, limit=10, identifier=""):
        super(EventSearch, self).__init__("EventSearch", "com.apple.ace.calendar", None, refId)
        self.timeZoneId = timeZoneId
        self.startDate = startDate
        self.endDate = endDate
        self.limit = limit
        self.identifier = identifier
    
    def to_plist(self):
        self.add_property('timeZoneId')
        self.add_property('startDate')
        self.add_property('endDate')
        self.add_property('limit')
        self.add_property('identifier')
        return super(EventSearch, self).to_plist()


class Event(AceObject):
    def __init__(self, timeZoneId="America/Chicago", title="", startDate=None, endDate=None):
        super(EventObject, self).__init__("Event", "com.apple.ace.calendar")
        self.timeZoneId = timeZoneId
        self.title = title
        self.startDate = startDate
        self.endDate = endDate
    
    def to_plist(self):
        self.add_property('timeZoneId')
        self.add_property('title')
        self.add_property('startDate')
        self.add_property('endDate')
        return super(EventObject, self).to_plist()


class EventSnippet(AceObject):
    def __init__(self, temporary=False, dialogPhase="Confirmation", events=None, confirmationOptions=None):
        super(EventSnippet, self).__init__("EventSnippet", "com.apple.ace.calendar")
        self.temporary = temporary
        self.dialogPhase = dialogPhase
        self.events = events if events != None else []
        self.confirmationOptions = confirmationOptions
    
    def to_plist(self):
        self.add_property('temporary')
        self.add_property('dialogPhase')
        self.add_property('events')
        self.add_property('confirmationOptions')
        return super(EventSnippet, self).to_plist()


########NEW FILE########
__FILENAME__ = clockObjects
from siriObjects.baseObjects import AceObject, ClientBoundCommand, ServerBoundCommand
from siriObjects.uiObjects import AddViews, AssistantUtteranceView, Snippet
from siriObjects.systemObjects import DomainObject


class ClockAdd(ClientBoundCommand):
    def __init__(self, refId):
        super(ClockAdd, self).__init__("Add", "com.apple.ace.clock", None, refId)
        self.clockToAdd = None # ClockObject
        self.targetAppId = None #url

    def to_plist(self):
        self.add_property('clockToAdd')
        self.add_property('targetAppId')
        return super(ClockAdd, self).to_plist()

class ClockAddCompleted(ServerBoundCommand):
    classIdentifier = "AddCompleted"
    groupIdentifier = "com.apple.ace.clock"
    def __init__(self, plist):
        self.worldClockId = None #url
        self.alreadyExists = None # bool
        super(ClockAddCompleted, self).__init__(plist)

class ClockDelete(ClientBoundCommand):
    def __init__(self, refId):
        super(ClockDelete, self).__init__("Delete", "com.apple.ace.clock", None, refId)
        self.clockIds = None # array
        self.targetAppId = None # url

    def to_plist(self):
        self.add_property('clockIds')
        self.add_property('targetAppId')
        return super(ClockDelete, self).to_plist()

class ClockDeleteCompleted(ServerBoundCommand):
    classIdentifier = "DeleteCompleted"
    groupIdentifier = "com.apple.ace.clock"
    def __init__(self, plist):
        super(ClockDeleteCompleted, self).__init__(plist)


class ClockObject(DomainObject):
    def __init__(self):
        super(ClockObject, self).__init__("com.apple.ace.clock")
        self.unlocalizedCountryName = None
        self.unlocalizedCityName = None
        self.timezoneId = None
        self.countryName = None
        self.countryCode = None
        self.cityName = None
        self.alCityId = None
    
    def to_plist(self):
        self.add_property('unlocalizedCountryName')
        self.add_property('unlocalizedCityName')
        self.add_property('timezoneId') 
        self.add_property('countryName')
        self.add_property('countryCode')
        self.add_property('cityName')
        self.add_property('alCityId')
        return super(ClockObject, self).to_plist()

class ClockSearch(ClientBoundCommand):
    def __init__(self, refId):
        super(ClockSearch, self).__init__("Search", "com.apple.ace.clock", None, refId)
        self.unlocalizedCountryName = None # string 
        self.unlocalizedCityName = None # string
        self.identifier = None #url
        self.countryCode = None # string
        self.alCityId = None # number
        self.targetAppId = None # url
    
    def to_plist(self):
        self.add_property('unlocalizedCountryName')
        self.add_property('unlocalizedCityName')
        self.add_property('identifier')
    	self.add_property('countryCode')
        self.add_property('alCityId')
    	self.add_property('targetAppId')
        return super(ClockSearch, self).to_plist()

class ClockSearchCompleted(ServerBoundCommand):
    classIdentifier = "SearchCompleted"
    groupIdentifier = "com.ace.apple.clock"
    def __init__(self, plist):
        self.results = None # array
        super(ClockSearchCompleted, self).__init__(plist)
    
class ClockSnippet(Snippet):
    def __init__(self, clocks=None):
        super(ClockSnippet, self).__init__("com.apple.ace.clock")
        self.clocks = clocks if clocks != None else []
    
    def to_plist(self):
        self.add_property('clocks')
        return super(ClockSnippet, self).to_plist()

########NEW FILE########
__FILENAME__ = contactObjects
from siriObjects.baseObjects import ClientBoundCommand, AceObject, ServerBoundCommand
from siriObjects.systemObjects import DomainObject, Location, Person as SuperPerson, RelatedName as SuperRelatedName, Phone as SuperPhone
from siriObjects.uiObjects import Snippet
from siriObjects.emailObjects import Email as SuperEmail

class Address(Location):
    def __init__(self, label="", street="", city="", stateCode="", countryCode="", postalCode="", latitude=0, longitude=0, accuracy=0):
        super(Address, self).__init__(label, street, city, stateCode, countryCode, postalCode, latitude, longitude, accuracy, group="com.apple.ace.contact", clazz="Address")

    def to_plist(self):
        return super(Address, self).to_plist()

class ContactGroup(DomainObject):
    def __init__(self, groupSource=None, groupName=""):
        super(ContactGroup, self).__init__("com.apple.ace.contact", clazz="ContactGroup")
        self.groupSource = groupSource if groupSource != None else Source()
        self.groupName = groupName

    def to_plist(self):
        self.add_property('groupSource')
        self.add_property('groupName')
        return super(ContactGroup, self).to_plist()


class Email(SuperEmail):
    def __init__(self):
        super(Email, self).__init__(group="com.apple.ace.contact")

    def to_plist(self):
        return super(Email, self).to_plist()

class Person(SuperPerson):
    def __init__(self):
        super(Person, self).__init__(group="com.apple.ace.contact")

    def to_plist(self):
        return super(Person, self).to_plist()

class PersonSearch(ClientBoundCommand):
    ScopeLocalValue = "Local"
    ScopeRemoteValue = "Remote"

    def __init__(self, refId):
        super(PersonSearch, self).__init__("PersonSearch", "com.apple.ace.contact", None, refId)
        self.scope = None
        self.relationship = None
        self.phone = None
        self.name = None
        self.me = None
        self.email = None
        self.company = None
        self.birthday = None
        self.address = None
        self.accountIdentifier = None
        self.targetAppId = None

    def to_plist(self):
        self.add_property('scope')
        self.add_property('relationship')
        self.add_property('phone')
        self.add_property('name')
        self.add_property('me')
        self.add_property('email')
        self.add_property('company')
        self.add_property('birthday')
        self.add_property('address')
        self.add_property('accountIdentifier')
        self.add_property('targetAppId')
        return super(PersonSearch, self).to_plist()

class PersonSearchCompleted(ServerBoundCommand):
    classIdentifier = "PersonSearchCompleted"
    groupIdentifier = "com.apple.ace.contact"
    
    def __init__(self, plist):
        self.results = None #array
        super(PersonSearchCompleted, self).__init__(plist)

class PersonSnippet(Snippet):
    def __init__(self, persons=None, displayProperties=None):
        super(PersonSnippet, self).__init__("com.apple.ace.contact", clazz="PersonSnippet")
        self.person=persons if persons != None else []
        self.displayProperties = displayProperties if displayProperties != None else []

    def to_plist(self):
        self.add_property('person')
        self.add_property('displayProperties')
        return super(PersonSnippet, self).to_plist()

class Phone(SuperPhone):
    def __init__(self):
        super(Phone, self).__init__(group="com.apple.ace.contact")
    
    def to_plist(self):
        return super(Phone, self).to_plist()

class RelatedName(SuperRelatedName):
    def __init__(self):
        super(RelatedName, self).__init__(group="com.apple.ace.contact")
    
    def to_plist(self):
        return super(RelatedName, self).to_plist()

class Source(DomainObject):
    def __init__(self, remote=0, accountName="", accountIdentifier=""):
        super(Source, self).__init__("com.apple.ace.contact", clazz="Source")
        self.remote = remote
        self.accountName = accountName
        self.accountIdentifier = accountIdentifier

    def to_plist(self):
        self.add_property('remote')
        self.add_property('accountName')
        self.add_property('accountIdentifier')
        return super(Source, self).to_plist()
########NEW FILE########
__FILENAME__ = emailObjects
from siriObjects.baseObjects import AceObject, ClientBoundCommand, ServerBoundCommand
from siriObjects.uiObjects import AddViews, AssistantUtteranceView, Snippet
from siriObjects.systemObjects import DomainObject


class Email(AceObject):
    def __init__(self, group="com.apple.ace.email"):
        super(Email, self).__init__("Email", group)
        self.label = None # string
        self.favoriteFacetime = None # number
        self.emailAddress = None # string

    def to_plist(self):
        self.add_property('label')
        self.add_property('favoriteFacetime')
        self.add_property('emailAddress')
        return super(Email, self).to_plist()

class EmailEmail(DomainObject):
    def __init__(self):
        super(EmailEmail, self).__init__("com.apple.ace.email")
        self.type = None # string
        self.timeZoneId = None # string
        self.subject = None # string
        self.referenceId = None # url
        self.recipientsTo = None # array
        self.recipientsCc = None # array
        self.recipientsBcc = None # array
        self.receivingAddresses = None #array
        self.outgoing = None # number
        self.message = None # string
        self.fromEmail = None # PersonAttribute Object
        self.dateSent = None # date

    def to_plist(self):
        self.add_property('type')
        self.add_property('timeZoneId')
        self.add_property('subject')
        self.add_property('referenceId')
        self.add_property('recipientsTo')
        self.add_property('recipientsCc')
        self.add_property('recipientsBcc')
        self.add_property('receivingAddresses')
        self.add_property('outgoing')
        self.add_property('message')
        self.add_property('fromEmail')
        self.add_property('dateSent')
        return super(EmailEmail, self).to_plist()

class EmailRetrieve(ClientBoundCommand):
    def __init__(self, refid):
        super(EmailRetrieve, self).__init__("Retrieve", "com.apple.ace.email", None, refId)
        self.requestedHeaders = None # array
        self.identifiers = None # array
        self.targetAppId = None # url

    def to_plist(self):
        self.add_property('requestedHeaders')
        self.add_property('identifiers')
        self.add_property('targetAppId')
        return super(EmailRetrieve, self).to_plist()

class EmailRetrieveCompleted(ServerBoundCommand):
    classIdentifier = "RetrieveCompleted"
    groupIdentifier = "com.apple.ace.email"
    def __init__(self, plist):
        self.results = None # array
        super(EmailRetrieveCompleted, self).__init__(plist)

class EmailSearch(ClientBoundCommand):
    def __init__(self, refId):
        super(EmailSearch, self).__init__("Search", "com.apple.ace.email", None, refId)
        self.toEmail = None # string
        self.timeZoneId = None #string
        self.subject = None # string
        self.status = None # int
        self.startDate = None # date
        self.fromEmail = None # string
        self.endDate = None # date
        self.targetAppId = None # url

    def to_plist(self):
        self.add_property('toEmail')
        self.add_property('timeZoneId')
        self.add_property('subject')
        self.add_property('status')
        self.add_property('startDate')
        self.add_property('fromEmail')
        self.add_property('endDate')
        self.add_property('targetAppId')
        return super(EmailSearch, self).to_plist()

class EmailSearchCompleted(ServerBoundCommand):
    classIdentifier = "SearchCompleted"
    groupIdentifier = "com.apple.ace.email"
    def __init__(self, plist):
        self.results = None #array
        self.emailResults = None #array
        super(EmailSearchCompleted, self).__init__(plist)

class EmailSnippet(Snippet):
    def __init__(self):
        super(EmailSnippet, self).__init__("com.apple.ace.email")
        self.emails = None # array

    def to_plist(self):
        self.add_property('emails')
        return super(EmailSnippet, self).to_plist()
        
    
########NEW FILE########
__FILENAME__ = forecastObjects
#Author: Sebastian Koch
from siriObjects.baseObjects import ClientBoundCommand, AceObject

class SiriForecastSnippet(AceObject):
    def __init__(self, aceWeathers=[]):
      super(SiriForecastSnippet, self).__init__("ForecastSnippet", "com.apple.ace.weather")
      self.aceWeathers = aceWeathers
      
    def to_plist(self):
        self.add_property('aceWeathers')
        return super(SiriForecastSnippet, self).to_plist()
        
class SiriForecastAceWeathers(AceObject):
    def __init__(self, currentConditions=None, dailyForecasts=None, hourlyForecasts=None, view="HOURLY", weatherLocation=None, extendedForecastUrl="http://m.yahoo.com/search?p=Frankfurt,+HE&.tsrc=appleww", units=None):
        super(SiriForecastAceWeathers, self).__init__("Object", "com.apple.ace.weather")
        self.currentConditions = currentConditions
        self.hourlyForecasts = hourlyForecasts
        self.dailyForecasts = dailyForecasts
        self.view = view
        self.weatherLocation = weatherLocation
        self.extendedForecastUrl = extendedForecastUrl
        self.units = units
 
    def to_plist(self):
        self.add_property('currentConditions')
        self.add_property('hourlyForecasts')
        self.add_property('dailyForecasts')
        self.add_property('view')
        self.add_property('weatherLocation')
        self.add_property('extendedForecastUrl')
        self.add_property('units')
        return super(SiriForecastAceWeathers, self).to_plist()
        
class SiriForecastAceWeathersHourlyForecast(AceObject):
    def __init__(self, chanceOfPrecipitation=0, isUserRequested=True,condition=None, temperature=0, timeIndex=20):
        super(SiriForecastAceWeathersHourlyForecast, self).__init__("HourlyForecast", "com.apple.ace.weather")
        self.chanceOfPrecipitation = chanceOfPrecipitation
        self.isUserRequested = isUserRequested
        self.condition = condition
        self.temperature = temperature
        self.timeIndex = timeIndex
 
    def to_plist(self):
        self.add_property('chanceOfPrecipitation')
        self.add_property('isUserRequested')
        self.add_property('condition')
        self.add_property('temperature')
        self.add_property('timeIndex')
        return super(SiriForecastAceWeathersHourlyForecast, self).to_plist()
        
class SiriForecastAceWeathersDailyForecast(AceObject):
    def __init__(self, chanceOfPerception=0, isUserRequested=True,condition=None, lowTemperature=0, highTemperature=0, timeIndex=1):
        super(SiriForecastAceWeathersDailyForecast, self).__init__("DailyForecast", "com.apple.ace.weather")
        self.chanceOfPerception = chanceOfPerception
        self.isUserRequested = isUserRequested
        self.condition = condition
        self.highTemperature = highTemperature
        self.lowTemperature = lowTemperature
        self.timeIndex = timeIndex
 
    def to_plist(self):
        self.add_property('chanceOfPerception')
        self.add_property('isUserRequested')
        self.add_property('condition')
        self.add_property('highTemperature')
        self.add_property('lowTemperature')
        self.add_property('timeIndex')
        return super(SiriForecastAceWeathersDailyForecast, self).to_plist()

class SiriForecastAceWeathersWeatherLocation(AceObject):
    def __init__(self, locationId="20066682", countryCode="Germany", city="Frankfurt", stateCode = "Hesse"):
        super(SiriForecastAceWeathersWeatherLocation, self).__init__("Location", "com.apple.ace.weather")
        self.locationId = locationId
        self.countryCode = countryCode
        self.city = city
        self.stateCode = stateCode
 
    def to_plist(self):
        self.add_property('locationId')
        self.add_property('countryCode')
        self.add_property('city')
        self.add_property('stateCode')
        return super(SiriForecastAceWeathersWeatherLocation, self).to_plist()
        
        
class SiriForecastAceWeathersUnits(AceObject):
    def __init__(self, speedUnits="KPH", distanceUnits="Kilometers", temperatureUnits="Celsius", pressureUnits = "MB"):
        super(SiriForecastAceWeathersUnits, self).__init__("Units", "com.apple.ace.weather")
        self.speedUnits = speedUnits
        self.distanceUnits = distanceUnits
        self.temperatureUnits = temperatureUnits
        self.pressureUnits = pressureUnits
 
    def to_plist(self):
        self.add_property('speedUnits')
        self.add_property('distanceUnits')
        self.add_property('temperatureUnits')
        self.add_property('pressureUnits')
        return super(SiriForecastAceWeathersUnits, self).to_plist()
        
class SiriForecastAceWeathersCurrentConditions(AceObject):
    def __init__(self, feelsLike="0", dayOfWeek=6, timeOfObservation="18:00",barometricPressure=None, visibility="0", percentOfMoonFaceVisible=90, temperature = "0", sunrise="7:30", sunset="19:00", moonPhase="WAXING_GIBBOUS",percentHumidity="80", timeZone="Central European Time", dewPoint="0", condition=None, windChill="0", windSpeed=None,):
        super(SiriForecastAceWeathersCurrentConditions, self).__init__("CurrentConditions", "com.apple.ace.weather")
        self.feelsLike = feelsLike
        self.dayOfWeek = dayOfWeek
        self.timeOfObservation = timeOfObservation
        self.barometricPressure = barometricPressure
        self.visibility = visibility
        self.percentOfMoonFaceVisible = percentOfMoonFaceVisible
        self.temperature = temperature
        self.sunrise = sunrise
        self.sunset = sunset
        self.moonPhase = moonPhase
        self.percentHumidity = percentHumidity
        self.timeZone = timeZone
        self.dewPoint = dewPoint
        self.condition = condition
        self.windChill = windChill
        self.windSpeed = windSpeed


    def to_plist(self):
        self.add_property('feelsLike')
        self.add_property('dayOfWeek')
        self.add_property('timeOfObservation')
        self.add_property('barometricPressure')
        self.add_property('visibility')
        self.add_property('percentOfMoonFaceVisible')
        self.add_property('temperature')
        self.add_property('sunrise')
        self.add_property('sunset')
        self.add_property('moonPhase')
        self.add_property('percentHumidity')
        self.add_property('timeZone')
        self.add_property('dewPoint')
        self.add_property('condition')
        self.add_property('windChill')
        self.add_property('windSpeed')
        return super(SiriForecastAceWeathersCurrentConditions, self).to_plist()  
        
class SiriForecastAceWeathersConditions(AceObject):
    def __init__(self, conditionCode="Sunny", conditionCodeIndex=32):
        super(SiriForecastAceWeathersConditions, self).__init__("Condition", "com.apple.ace.weather")
        self.conditionCode = conditionCode
        self.conditionCodeIndex = conditionCodeIndex

 
    def to_plist(self):
        self.add_property('conditionCode')
        self.add_property('conditionCodeIndex')
        return super(SiriForecastAceWeathersConditions, self).to_plist() 
########NEW FILE########
__FILENAME__ = localsearchObjects
from siriObjects.baseObjects import ClientBoundCommand, AceObject, ServerBoundCommand
from siriObjects.systemObjects import DomainObject, Location
from siriObjects.uiObjects import Snippet

class MapItemSnippet(Snippet):
    def __init__(self, userCurrentLocation=True, items=None):
        super(MapItemSnippet, self).__init__("com.apple.ace.localsearch", clazz="MapItemSnippet")
        self.userCurrentLocation = userCurrentLocation
        self.items = items
        self.searchRegionCenter = None # systemObjects.Location
        self.regionOfInterestRadiusInMiles = None
        self.providerCommand = None # array
    
    def to_plist(self):
        self.add_property('userCurrentLocation')
        self.add_property('items')
        self.add_property('searchRegionCenter')
        self.add_property('regionOfInterestRadiusInMiles')
        self.add_property('providerCommand')
        return super(MapItemSnippet, self).to_plist()

class MapItem(DomainObject):
    TypeCURRENT_LOCATIONValue = "CURRENT_LOCATION"
    TypeBUSINESS_ITEMValue = "BUSINESS_ITEM"
    TypePERSON_ITEMValue = "PERSON_ITEM"
    TypeADDRESS_ITEMValue = "ADDRESS_ITEM"
    TypeHOME_ITEMValue = "HOME_ITEM"
    
    def __init__(self, label="", street="", city="", stateCode="", countryCode="", postalCode="", latitude=0, longitude=0, detailType="BUSINESS_ITEM", clazz="MapItem"):
        super(MapItem, self).__init__("com.apple.ace.localsearch", clazz="MapItem")
        self.label = label
        self.detailType = detailType
        self.location = Location(label,street,city,stateCode,countryCode,postalCode,latitude,longitude)
        self.placeId = None
        self.distanceInMiles = None
        self.detail = None #AceObject
    
    def to_plist(self):
        self.add_property('label')
        self.add_property('detailType')
        self.add_property('location')
        self.add_property('placeId')
        self.add_property('distanceInMiles')
        self.add_property('detail')
        return super(MapItem, self).to_plist()

class ActionableMapItem(MapItem):
    def __init__(self, label="", street="", city="", stateCode="", countryCode="", postalCode="", latitude=0, longitude=0, detailType=MapItem.TypeCURRENT_LOCATIONValue, commands=None):
        super(ActionableMapItem, self).__init__(self, label, street, city, stateCode, countryCode, postalCode, latitude, longitude, detailType, clazz="ActionableMapItem")
        self.commands = commands if commands != None else []
    
    def to_plist(self):
        self.add_property('commands')
        return super(ActionableMapItem, self).to_plist()


class Rating(AceObject):
    def __init__(self, value=0.0, providerId="", description="", count=0):
        super(Rating, self).__init__("Rating", "com.apple.ace.localsearch")
        self.value = value
        self.providerId = providerId
        self.description = description
        self.count = count

    def to_plist(self):
        self.add_property('value')
        self.add_property('providerId')
        self.add_property('description')
        self.add_property('count')
        return super(Rating, self).to_plist()

class Business(AceObject):
    def __init__(self, totalNumberOfReviews=0, rating=None, photo="", phoneNumbers=None, openingHours="", name="", extSessionGuid="", categories=None, businessUrl="", businessIds=None, businessId=0):
        super(Business, self).__init__("Business", "com.apple.ace.localsearch")
        self.totalNumberOfReviews = totalNumberOfReviews
        self.rating = rating if rating != None else Rating()
        self.photo = photo
        self.phoneNumbers = phoneNumbers if phoneNumbers != None else []
        self.openingHours = openingHours
        self.name = name
        self.extSessionGuid = extSessionGuid
        self.categories = categories if categories != None else []
        self.businessUrl = businessUrl
        self.businessIds = businessIds if businessIds != None else dict()
        self.businessId = businessId

    def to_plist(self):
        self.add_property('totalNumberOfReviews')
        self.add_property('rating')
        self.add_property('photo')
        self.add_property('phoneNumbers')
        self.add_property('openingHours')
        self.add_property('name')
        self.add_property('extSessionGuid')
        self.add_property('categories')
        self.add_property('businessUrl')
        self.add_property('businessIds')
        self.add_property('businessId')
        return super(Business, self).to_plist()

class DisambiguationMap(Snippet):
    def __init__(self, items=None):
        super(DisambiguationMap, self).__init__("com.apple.ace.localsearch", clazz="DisambiguationMap")
        self.items = items if items != None else []

    def to_plist(self):
        self.add_property('items')
        return super(DisambiguationMap, self).to_plist()

class PhoneNumber(AceObject):
    TypePRIMARYValue = "PRIMARY"
    TypeSECONDARYValue =  "SECONDARY"
    TypeFAXValue = "FAX"
    TTYValue = "TTY"

    def __init__(self, value="", type="PRIMARY"):
        super(PhoneNumber, self).__init__("PhoneNumber", "com.apple.ace.localsearch")
        self.value = value
        self.type = type

    def to_plist(self):
        self.add_property('value')
        self.add_property('type')
        return super(PhoneNumber, self).to_plist()



class Review(AceObject):
    TypePROFESSIONALValue = "PROFESSIONAL"
    TypeCOMMUNITYValue = "COMMUNITY"
    TypePERSONALValue = "PERSONAL"

    def __init__(self, url="", type="PROFESSIONAL", reviewerUrl="", reviewerName="", rating=None, publication="", provider="", fullReview="", excerpt=""):
        super(Review, self).__init__("Review", "com.apple.ace.localsearch")
        self.url = url
        self.type = type
        self.reviewerUrl = reviewerUrl
        self.reviewerName = reviewerName
        self.rating = rating if rating != None else Rating()
        self.publication = publication
        self.provider = provider
        self.fullReview = fullReview
        self.excerpt = excerpt

    def to_plist(self):
        self.add_property('url')
        self.add_property('type')
        self.add_property('reviewerUrl')
        self.add_property('reviewerName')
        self.add_property('rating')
        self.add_property('publication')
        self.add_property('provider')
        self.add_property('fullReview')
        self.add_property('excerpt')
        return super(Review, self).to_plist()

class ShowMapPoints(ClientBoundCommand):
    DirectionsTypeByCarValue = "ByCar"
    DirectionsTypeByPublicTransitValue = "ByPublicTransit"
    DirectionsTypeWalkingValue = "Walking"
    DirectionsTypeBikingValue = "Biking"

    def __init__(self, refId, showTraffic=False, showDirections=False, regionOfInterestRadiusInMiles=0, itemSource=None, itemDestination=None, directionsType="ByCar", targetAppId=""):
        super(ShowMapPoints, self).__init__("ShowMapPoints", "com.apple.ace.localsearch", None, refId)
        self.showTraffic = showTraffic
        self.showDirections = showDirections
        self.regionOfInterestRadiusInMiles = regionOfInterestRadiusInMiles
        self.itemSource = itemSource if itemSource != None else MapItem()
        self.itemDestination = itemDestination if itemDestination != None else MapItem()
        self.directionsType = directionsType
        self.targetAppId = targetAppId

    def to_plist(self):
        self.add_property('showTraffic')
        self.add_property('showDirections')
        self.add_property('regionOfInterestRadiusInMiles')
        self.add_property('itemSource')
        self.add_property('itemDestination')
        self.add_property('directionsType')
        self.add_property('targetAppId')
        return super(ShowMapPoints, self).to_plist()

class ShowMapPointsCompleted(ServerBoundCommand):
    classIdentifier = "ShowMapPointsCompleted"
    groupIdentifier = "com.apple.ace.localsearch"
    
    def __init__(self, plist):
        super(ShowMapPointsCompleted, self).__init__(plist)


########NEW FILE########
__FILENAME__ = mapObjects
#!/usr/bin/python
# -*- coding: utf-8 -*-

from siriObjects.baseObjects import AceObject, ClientBoundCommand

class SiriMapItemSnippet(AceObject):
    def __init__(self, userCurrentLocation=True, items=None):
        super(SiriMapItemSnippet, self).__init__("MapItemSnippet", "com.apple.ace.localsearch")
        self.userCurrentLocation = userCurrentLocation
        self.items = items
    
    def to_plist(self):
        self.add_property('userCurrentLocation')
        self.add_property('items')
        return super(SiriMapItemSnippet, self).to_plist()

class SiriLocation(AceObject):
    def __init__(self, label="", street="", city="", stateCode="", countryCode="", postalCode="", latitude="", longitude=""):
        super(SiriLocation, self).__init__("Location", "com.apple.ace.system")
        self.label = label
        self.street = street
        self.city = city
        self.stateCode = stateCode
        self.countryCode = countryCode
        self.postalCode = postalCode
        self.latitude = latitude
        self.longitude = longitude
    
    def to_plist(self):
        self.add_property('label')
        self.add_property('street')
        self.add_property('city')
        self.add_property('stateCode')
        self.add_property('countryCode')
        self.add_property('postalCode')
        self.add_property('latitude')
        self.add_property('longitude')
        return super(SiriLocation, self).to_plist()

class SiriMapItem(AceObject):
    def __init__(self, label="", location=None, detailType="BUSINESS_ITEM"):
        super(SiriMapItem, self).__init__("MapItem", "com.apple.ace.localsearch")
        self.label = label
        self.detailType = detailType
        self.location = location if location != None else SiriLocation()
    
    def to_plist(self):
        self.add_property('label')
        self.add_property('detailType')
        self.add_property('location')
        return super(SiriMapItem, self).to_plist()
########NEW FILE########
__FILENAME__ = noteObjects
from siriObjects.baseObjects import ClientBoundCommands, AceObject

class NoteSnippet(AceObject):
    def __init__(self, notes=None, temporary=False, dialogPhase="Summary"):
        super(NoteSnippet, self).__init__("Snippet", "com.apple.ace.note")
        self.notes = notes if notes != None else []
        self.temporary = temporary
        self.dialogPhase = dialogPhase
    
    def to_plist(self):
        self.add_property('notes')
        self.add_property('temporary')
        self.add_property('dialogPhase')
        return super(NoteSnippet, self).to_plist()


class NoteObject(AceObject):
    def __init__(self, contents="", identifier=""):
        super(NoteObject, self).__init__("Object", "com.apple.ace.note")
        self.contents = contents
        self.identifier = identifier
    
    def to_plist(self):
        self.add_property('contents')
        self.add_property('identifier')
        return super(NoteObject, self).to_plist()
########NEW FILE########
__FILENAME__ = phoneObjects
from siriObjects.baseObjects import ClientBoundCommand, AceObject, ServerBoundCommand
from siriObjects.systemObjects import DomainObject, PersonAttribute
from siriObjects.uiObjects import Snippet


class PhoneCall(ClientBoundCommand):
    def __init__(self, refId, recipient="", faceTime=False, callRecipient=None, targetAppId=""):
        super(PhoneCall, self).__init__("Call", "com.apple.ace.phone", None, refId)
        self.recipient = recipient
        self.faceTime = faceTime
        self.callRecipient = callRecipient if callRecipient != None else PersonAttribute()
        self.targetAppId = targetAppId

    def to_plist(self):
        self.add_property('recipient')
        self.add_property('faceTime')
        self.add_property('callRecipient')
        self.add_property('targetAppId')
        return super(PhoneCall, self).to_plist()



class PhoneCallSnippet(Snippet):
    def __init__(self, calls=None):
        super(PhoneCallSnippet, self).__init__("com.apple.ace.phone", clazz="CallSnippet")
        self.calls = calls if calls != None else []
    
    def to_plist(self):
        self.add_property('calls')
        return super(PhoneCallSnippet, self).to_plist()

class PhoneCallStarted(ServerBoundCommand):
    groupIdentifier = "com.apple.ace.phone"
    classIdentifier = "CallStarted"
    def __init__(self, plist):
        self.phoneLogId=""
        super(PhoneCallSnippet, self).__init__(plist)

class PhoneSearch(ClientBoundCommand):
    def __init__(self, refId, timeZoneId="", start="", outgoingPhoneNumber="", missed=False, limit=5, incomingPhoneNumber="", end="", targetAppId=""):
        super(PhoneSearch, self).__init__("Search", "com.apple.ace.phone", None, refId)
        self.timeZoneId = timeZoneId
        self.start = start
        self.outgoingPhoneNumber = outgoingPhoneNumber
        self.missed = missed
        self.limit = limit
        self.incomingPhoneNumber = incomingPhoneNumber
        self.end = end
        self.targetAppId = targetAppId

    def to_plist(self):
        self.add_property('timeZoneId')
        self.add_property('start')
        self.add_property('outgoingPhoneNumber')
        self.add_property('missed')
        self.add_property('limit')
        self.add_property('incomingPhoneNumber')
        self.add_property('end')
        self.add_property('targetAppId')
        return super(PhoneSearch, self).to_plist()

class PhoneSearchCompleted(ServerBoundCommand):
    groupIdentifier = "com.apple.ace.phone"
    classIdentifier = "SearchCompleted"

    def __init__(self, plist):
        self.phoneLogIds = []
        super(PhoneSearchCompleted, self).__init__(plist)
########NEW FILE########
__FILENAME__ = reminderObjects
from siriObjects.baseObjects import ClientBoundCommand, AceObject

class ReminderSnippet(AceObject):
    def __init__(self, reminders=None, temporary=False, dialogPhase="Confirmation"):
        super(ReminderSnippet, self).__init__("Snippet", "com.apple.ace.reminder")
        self.reminders = reminders if reminders != None else []
        self.temporary = temporary
        self.dialogPhase = dialogPhase
    
    def to_plist(self):
        self.add_property('reminders')
        self.add_property('temporary')
        self.add_property('dialogPhase')
        return super(ReminderSnippet, self).to_plist()


class ReminderObject(AceObject):
    def __init__(self, dueDateTimeZoneId="America/Chicago", dueDate=None, completed=False, lists=None, trigger=None, subject="", important=False, identifier=""):
        super(ReminderObject, self).__init__("Object", "com.apple.ace.reminder")
        self.dueDateTimeZoneId = dueDateTimeZoneId
        self.dueDate = dueDate
        self.completed = completed
        self.lists = lists if lists != None else []
        self.trigger = trigger if trigger != None else []
        self.subject = subject
        self.important = important
        self.identifier = identifier
    
    def to_plist(self):
        self.add_property('dueDateTimeZoneId')
        self.add_property('dueDate')
        self.add_property('completed')
        self.add_property('lists')
        self.add_property('trigger')
        self.add_property('subject')
        self.add_property('important')
        self.add_property('identifier')
        return super(ReminderObject, self).to_plist()


class ListObject(AceObject):
    def __init__(self, name = "Tasks"):
        super(ListObject, self).__init__("ListObject", "com.apple.ace.reminder")
        self.name = name
    
    def to_plist(self):
        self.add_property('name')
        return super(ListObject, self).to_plist()


class DateTimeTrigger(AceObject):
    def __init__(self, date=None):
        super(DateTimeTrigger, self).__init__("DateTimeTrigger", "com.apple.ace.reminder")
        self.date = date
    
    def to_plist(self):
        self.add_property('date')
        return super(DateTimeTrigger, self).to_plist()


########NEW FILE########
__FILENAME__ = speechObjects
from siriObjects.baseObjects import ServerBoundCommand, ClientBoundCommand, AceObject

import uuid

class StartSpeech(ServerBoundCommand):
    classIdentifier = "StartSpeech"
    groupIdentifier = "com.apple.ace.speech"
    
    CodecPCM_Mono_16Bit_8000HzValue = "PCM_Mono_16Bit_8000Hz"
    CodecPCM_Mono_16Bit_11025HzValue = "PCM_Mono_16Bit_11025Hz"
    CodecPCM_Mono_16Bit_16000HzValue = "PCM_Mono_16Bit_16000Hz"
    CodecPCM_Mono_16Bit_22050HzValue = "PCM_Mono_16Bit_22050Hz"
    CodecPCM_Mono_16Bit_32000HzValue = "PCM_Mono_16Bit_32000Hz"
    CodecSpeex_NB_Quality7Value = "Speex_NB_Quality7"
    CodecSpeex_WB_Quality8Value =  "Speex_WB_Quality8"
    
    AudioSourceLineInValue = "LineIn"
    AudioSourceBuiltInMicValue = "BuiltInMic"
    AudioSourceWiredHeadsetMicValue = "WiredHeadsetMic"
    AudioSourceBluetoothHandsFreeDeviceValue = "BluetoothHandsFreeDevice"
    AudioSourceUsbAudioValue = "UsbAudio"

    MotionActivityUnknownValue = "Unknown"
    MotionActivityFrozenValue = "Frozen"
    MotionActivityStaticValue = "Static"
    MotionActivityMovingValue = "Moving"
    MotionActivityWalkingValue = "Walking"
    MotionActivityDrivingValue = "Driving"
    MotionActivityCyclingValue = "Cycling"
    MotionActivitySemiStationaryValue = "SemiStationary"
    MotionActivityRunningValue = "Running"
    MotionActivityMovingCoarseValue = "MovingCoarse"
    MotionActivityInVehicleFrozenValue =  "InVehicleFrozen"
    MotionActivityInVehicleStaticValue = "InVehicleStatic"
    MotionActivityWalkingSlowValue = "WalkingSlow"
    MotionActivityDrivingInHandValue = "DrivingInHand"
    MotionActivityDrivingOtherValue = "DrivingOther"

    DspTypeNoneValue = "None"
    DspTypeNoiseCancellationValue = "NoiseCancellation"
    def __init__(self, plist):
        self.origin = None # string
        self.noiseReductionLevel = None # number
        self.motionConfidence = None # number
        self.motionActivity = None # string
        self.headsetName = None # string
        self.headsetId = None # string
        self.headsetAddress = None # string
        self.dspStatus = None # string
        self.codec = None # int ?? -> string mapping
        self.audioSource = None # string
        super(StartSpeech, self).__init__(plist)

class StartSpeechRequest(StartSpeech):
    classIdentifier = "StartSpeechRequest"
    groupIdentifier = "com.apple.ace.speech"
    def __init__(self, plist):
        self.handsFree = None # bool
        super(StartSpeechRequest, self).__init__(plist)
    

class StartSpeechDictation(StartSpeech):
    classIdentifier = "StartSpeechDictation"
    groupIdentifier = "com.apple.ace.speech"
    
    FieldKeyboardReturnKeyDefaultValue =  "Default"
    FieldKeyboardReturnKeyGoValue = "Go"
    FieldKeyboardReturnKeyGoogleValue = "Google"
    FieldKeyboardReturnKeyJoinValue = "Join"
    FieldKeyboardReturnKeyNextValue = "Next"
    FieldKeyboardReturnKeyRouteValue = "Route"
    FieldKeyboardReturnKeySearchValue = "Search"
    FieldKeyboardReturnKeySendValue = "Send"
    FieldKeyboardReturnKeyYahooValue = "Yahoo"
    FieldKeyboardReturnKeyDoneValue = "Done"
    FieldKeyboardReturnKeyEmergencyCallValue = "EmergencyCall"

    FieldKeyboardTypeDefaultValue = "Default"
    FieldKeyboardTypeASCIICapableValue = "ASCIICapable"
    FieldKeyboardTypeAlphabetValue = "Alphabet"
    FieldKeyboardTypeNumbersAndPunctuationValue = "NumbersAndPunctuation"
    FieldKeyboardTypeNumberPadValue = "NumberPad"
    FieldKeyboardTypeDecimalPadValue = "DecimalPad"
    FieldKeyboardTypeURLValue = "URL"
    FieldKeyboardTypeEmailAddressValue = "EmailAddress"
    FieldKeyboardTypePhonePadValue = "PhonePad"
    FieldKeyboardTypeNamePhonePadValue = "NamePhonePad"
    FieldKeyboardTypeTwitterValue = "Twitter"

    def __init__(self, plist):
        self.selectedText = None # string
        self.region = None # string
        self.prefixText = None # string
        self.postfixText = None # string
        self.language = None # string
        self.keyboardType = None # string
        self.keyboardReturnKey = None # string
        self.interactionId = None # string
        self.fieldLabel = None # string
        self.fieldId = None # string
        self.censorSpeech = None # bool
        self.applicationVersion = None # string
        self.applicationName = None # string
        super(StartSpeechDictation, self).__init__(plist)

class SpeechPacket(ServerBoundCommand):
    classIdentifier = "SpeechPacket"
    groupIdentifier = "com.apple.ace.speech"
    
    def __init__(self, plist):
        self.packets = None # array
        self.packetNumber = None # int
        self.data = None # binary
        super(SpeechPacket, self).__init__(plist)

class FinishSpeech(ServerBoundCommand):
    classIdentifier = "FinishSpeech"
    groupIdentifier = "com.apple.ace.speech"

    def __init__(self, plist):
        self.packetCount = None # int
        self.orderedContext = None # array
        super(FinishSpeech, self).__init__(plist)

class SpeechFailure(ClientBoundCommand):
    FailureReasonTimeoutValue = "Timeout"
    FailureReasonCorruptValue = "Corrupt"
    FailureReasonInvalidValue = "Invalid"
    FailureReasonInaudibleValue = "Inaudible"
    FailureReasonErrorValue = "Error"
    FailureReasonRetryValue = "Retry"
    FailureReasonUnsupportedValue = "Unsupported"
    FailureReasonQuotaExceededValue = "QuotaExceeded"
    
    def __init__(self, refId, reasonDescription, reason=0):
        super(SpeechFailure, self).__init__("SpeechFailure", "com.apple.ace.speech", None, refId)
        self.reasonDescription = reasonDescription
        self.reason = reason
    
    def to_plist(self):
        self.add_property('reasonDescription')
        self.add_property('reason')
        return super(SpeechFailure, self).to_plist()


class SpeechRecognized(ClientBoundCommand):
    def __init__(self, refId, recognition, sessionId=str.upper(str(uuid.uuid4()))):
        super(SpeechRecognized, self).__init__("SpeechRecognized", "com.apple.ace.speech", None, refId)
        self.sessionId = sessionId
        self.recognition = recognition
        
    def to_plist(self):
        self.add_property('sessionId')
        self.add_property('recognition')
        return super(SpeechRecognized, self).to_plist()


class Recognition(AceObject):
    def __init__(self, phrases=None):
        super(Recognition, self).__init__("Recognition", "com.apple.ace.speech")
        self.phrases = phrases if phrases != None else []
    
    def to_plist(self):
        self.add_property('phrases')
        return super(Recognition, self).to_plist()

class Phrase(AceObject):
    def __init__(self, lowConfidence=False, interpretations=None):
        super(Phrase, self).__init__("Phrase", "com.apple.ace.speech")
        self.lowConfidence = lowConfidence
        self.interpretations = interpretations if interpretations != None else []
    
    def to_plist(self):
        self.add_property('lowConfidence')
        self.add_property('interpretations')
        return super(Phrase, self).to_plist()

class Interpretation(AceObject):
    def __init__(self, tokens=None):
        super(Interpretation, self).__init__("Interpretation", "com.apple.ace.speech")
        self.tokens = tokens if tokens != None else []
    
    def to_plist(self):
        self.add_property('tokens')
        return super(Interpretation, self).to_plist()

class Token(AceObject):    
    def __init__(self, text, startTime, endTime, confidenceScore, removeSpaceBefore, removeSpaceAfter):
        super(Token, self).__init__("Token", "com.apple.ace.speech")
        self.text = text
        self.startTime = startTime
        self.endTime = endTime
        self.confidenceScore = confidenceScore
        self.removeSpaceBefore = removeSpaceBefore
        self.removeSpaceAfter = removeSpaceAfter

    def to_plist(self):
        self.add_property('text')
        self.add_property('startTime')
        self.add_property('endTime')
        self.add_property('confidenceScore')
        self.add_property('removeSpaceBefore')
        self.add_property('removeSpaceAfter')
        return super(Token, self).to_plist()

########NEW FILE########
__FILENAME__ = systemObjects
from siriObjects.baseObjects import ClientBoundCommand, AceObject, ServerBoundCommand

import biplist, struct

class GetRequestOrigin(ClientBoundCommand):
    desiredAccuracyThreeKilometers = "ThreeKilometers"
    desiredAccuracyKilometer = "Kilometer"
    desiredAccuracyHundredMeters = "HundredMeters"
    desiredAccuracyNearestTenMeters = "NearestTenMeters"
    desiredAccuracyBest = "Best"
    
    def __init__(self, refId, desiredAccuracy=desiredAccuracyHundredMeters, maxAge=None, searchTimeout=8.0):
        super(GetRequestOrigin, self).__init__("GetRequestOrigin", "com.apple.ace.system", None, refId)
        self.desiredAccuracy = desiredAccuracy
        self.searchTimeout = searchTimeout
        self.maxAge = maxAge
    
    def to_plist(self):
        self.add_property('desiredAccuracy')
        self.add_property('searchTimeout')
        self.add_property('maxAge')
        return super(GetRequestOrigin, self).to_plist()

class SetRequestOrigin(ServerBoundCommand):
    statusValid = "Valid"
    statusTimeout = "Timeout"
    statusUnknown = "Unknown"
    statusDenied = "Denied"
    statusDisabled = "Disabled"
    def __init__(self, plist):
        self.aceId = None
        self.refId = None
        self.timestamp = None
        self.status = None
        self.speed = None
        self.direction = None
        self.desiredAccuracy = None
        self.altitude = None
        self.age = None
        self.horizontalAccuracy = None
        self.verticalAccuracy = None
        self.longitude = None
        self.latitude = None
        super(SetRequestOrigin, self).__init__(plist)


class DomainObject(AceObject):
    def __init__(self, group, identifier=None, clazz="Object"):
        super(DomainObject, self).__init__(clazz, group)
        self.identifier = identifier
    
    def to_plist(self):
        self.add_property('identifier')
        return super(DomainObject, self).to_plist()

class DomainObjectCreate(ClientBoundCommand):
    def __init__(self, refId, obj=None):
        super(DomainObjectCreate, self).__init__("DomainObjectCreate", "com.apple.ace.system", None, refId)
        self.object = obj
    
    def to_plist(self):
        self.add_property('object')
        return super(DomainObjectCreate, self).to_plist()



class DomainObjectRetrieve(ClientBoundCommand):
    def __init__(self, refId, identifiers=None):
        super(DomainObjectRetrieve, self).__init__("DomainObjectRetrieve", "com.apple.ace.system", None, refId)
        self.identifiers = identifiers if identifiers != None else []
    
    def to_plist(self):
        self.add_property('identifiers')
        return super(DomainObjectRetrieve, self).to_plist()


class DomainObjectUpdate(ClientBoundCommand):
    def __init__(self, refId, identifier=None, addFields=None, setFields=None, removeFields=None):
        super(DomainObjectUpdate, self).__init__("DomainObjectUpdate", "com.apple.ace.system", None, refId)
        self.identifier = identifier if identifier != None else []
        self.addFields = addFields if addFields != None else []
        self.setFields = setFields if setFields != None else []
        self.removeFields = removeFields if removeFields != None else []
        
    def to_plist(self):
        self.add_property('identifier')
        self.add_property('addFields')
        self.add_property('setFields')
        self.add_property('removeFields')
        return super(DomainObjectUpdate, self).to_plist()



class DomainObjectCommit(ClientBoundCommand):
    def __init__(self, refId, identifier=None):
        super(DomainObjectCommit, self).__init__("DomainObjectCommit", "com.apple.ace.system", None, refId)
        self.identifier = identifier
    
    def to_plist(self):
        self.add_property('identifier')
        return super(DomainObjectCommit, self).to_plist()

class StartRequest(AceObject):
    def __init__(self, handsFree=False, utterance=""):
        super(StartRequest, self).__init__("StartRequest", "com.apple.ace.system")
        self.handsFree = handsFree
        self.utterance = utterance

    def to_plist(self):
        self.add_property('handsFree')
        self.add_property('utterance')
        return super(StartRequest, self).to_plist()

class ResultCallback(AceObject):
    def __init__(self, commands=None, code=0):
        super(ResultCallback, self).__init__("ResultCallback", "com.apple.ace.system")
        self.commands = commands if commands != None else []
        self.code = code

    def to_plist(self):
        self.add_property('commands')
        self.add_property('code')
        return super(ResultCallback, self).to_plist()


class SendCommands(AceObject):
    def __init__(self, commands=None):
        super(SendCommands, self).__init__("SendCommands", "com.apple.ace.system")
        self.commands = commands if commands != None else []
    
    def to_plist(self):
        self.add_property('commands')
        return super(SendCommands, self).to_plist()

class Person(DomainObject):
    def __init__(self, group="com.apple.ace.system"):
        super(Person, self).__init__(group, clazz="Person")
        self.suffix = None # string
        self.relatedNames = None # array
        self.prefix = None # string
        self.phones = None # array
        self.nickName = None # string
        self.middleName = None # string
        self.me = None # number
        self.lastNamePhonetic = None # string
        self.lastName = None # string
        self.fullName = None # string
        self.firstNamePhonetic = None # string
        self.firstName = None # string
        self.emails = None # array
        self.compary = None # string
        self.birthday = None # date
        self.addresses = None # array

    def to_plist(self):
        self.add_property('suffix')
        self.add_property('relatedNames')
        self.add_property('prefix')
        self.add_property('phones')
        self.add_property('nickName')
        self.add_property('middleName')
        self.add_property('me')
        self.add_property('lastNamePhonetic')
        self.add_property('lastName')
        self.add_property('fullName')
        self.add_property('firstNamePhonetic')
        self.add_property('firstName')
        self.add_property('emails')
        self.add_property('compary')
        self.add_property('birthday')
        self.add_property('addresses')
        return super(Person, self).to_plist()

class PersonAttribute(AceObject):
    def __init__(self, obj=None, displayText="", data=""):
        super(PersonAttribute, self).__init__("PersonAttribute", "com.apple.ace.system")
        self.object = obj if obj != None else Person()
        self.displayText = ""
        self.data = ""
    
    def to_plist(self):
        self.add_property('object')
        self.add_property('displayText')
        self.add_property('data')
        return super(PersonAttribute, self).to_plist()

class Phone(AceObject):
    def __init__(self, number="", label="", favoriteVoice=0, favoriteFacetime=0, group="com.apple.ace.system"):
        super(Phone, self).__init__("Phone", group)
        self.number = number
        self.label = label
        self.favoriteVoice = favoriteVoice
        self.favoriteFacetime = favoriteFacetime
    
    def to_plist(self):
        self.add_property('number')
        self.add_property('label')
        self.add_property('favoriteVoice')
        self.add_property('favoriteFacetime')
        return super(Phone, self).to_plist()


class RelatedName(AceObject):
    def __init__(self, name="", label="", group="com.apple.ace.system"):
        super(RelatedName, self).__init__("RelatedName", group)
        self.name = name
        self.label = label

    def to_plist(self):
        self.add_property('name')
        self.add_property('label')
        return super(RelatedName, self).to_plist()


class CancelRequest(ServerBoundCommand):
    groupIdentifier = "com.apple.ace.system"
    classIdentifier = "CancelRequest"

    def __init__(self, plist):
        super(CancelRequest, self).__init__(plist)

class CancelSucceeded(ClientBoundCommand):
    def __init__(self, refId):
        super(CancelSucceeded, self).__init__("CancelSucceeded", "com.apple.ace.system", None, refId)

class GetSessionCertificate(ServerBoundCommand):
    groupIdentifier = "com.apple.ace.system"
    classIdentifier = "GetSessionCertificate"

    def __init__(self, plist):
        super(GetSessionCertificate, self).__init__(plist)

class GetSessionCertificateResponse(ClientBoundCommand):
    def __init__(self, refId, caCert, sessionCert):
        super(GetSessionCertificateResponse, self).__init__("GetSessionCertificateResponse", "com.apple.ace.system", None, refId)
        self.certificate = None
        self.caCert = caCert
        self.sessionCert = sessionCert

    def to_plist(self):
        self.certificate = biplist.Data("\x01\x02"+struct.pack(">I", len(self.caCert))+self.caCert + struct.pack(">I", len(self.sessionCert))+self.sessionCert)
        self.add_property('certificate')
        return super(GetSessionCertificateResponse, self).to_plist()
        
class CreateSessionInfoRequest(ServerBoundCommand):
    groupIdentifier = "com.apple.ace.system"
    classIdentifier = "CreateSessionInfoRequest"

    def __init__(self, plist):
        self.sessionInfoRequest = None # binary
        super(CreateSessionInfoRequest, self).__init__(plist)

class CreateSessionInfoResponse(ClientBoundCommand):
    def __init__(self, refId):
        super(CreateSessionInfoResponse, self).__init__("CreateSessionInfoResponse", "com.apple.ace.system", None, refId)
        self.validityDuration = None # number
        self.sessionInfo = None # binary

    def to_plist(self):
        self.add_property('validityDuration')
        self.add_property('sessionInfo')
        return super(CreateSessionInfoResponse, self).to_plist()


class CommandFailed(ClientBoundCommand):
    def __init__(self, refId):
        super(CommandFailed, self).__init__("CommandFailed", "com.apple.ace.system", None, refId, callbacks=[])
        self.reason = None #string
        self.errorCode = None  #int
    
    def to_plist(self):
        self.add_property('reason')
        self.add_property('errorCode')
        return super(CommandFailed, self).to_plist()



class Location(DomainObject):
    AccuracyBestValue = "Best"
    AccuracyNearestTenMetersValue = "NearestTenMeters"
    AccuracyHundredMetersValue = "HundredMeters"
    AccuracyKilometerValue = "Kilometer"
    AccuracyThreeKilometersValue = "ThreeKilometers"
    def __init__(self, label="", street="", city="", stateCode="", countryCode="", postalCode="", latitude=0, longitude=0, accuracy=0, group="com.apple.ace.system", clazz="Location"):
        super(Location, self).__init__(group, None, clazz)
        self.label = label
        self.street = street
        self.city = city
        self.stateCode = stateCode
        self.countryCode = countryCode
        self.postalCode = postalCode
        self.latitude = latitude
        self.longitude = longitude
        self.accuracy = accuracy

    def to_plist(self):
        self.add_property('label')
        self.add_property('street')
        self.add_property('city')
        self.add_property('stateCode')
        self.add_property('countryCode')
        self.add_property('postalCode')
        self.add_property('latitude')
        self.add_property('longitude')
        self.add_property('accuracy')
        return super(Location, self).to_plist()

########NEW FILE########
__FILENAME__ = timerObjects
from siriObjects.baseObjects import ClientBoundCommand, AceObject, ServerBoundCommand
from siriObjects.systemObjects import SendCommands, StartRequest, DomainObject
from siriObjects.uiObjects import ConfirmationOptions, Snippet

class TimerGet(ClientBoundCommand):
    def __init__(self, refId):
        super(TimerGet, self).__init__("Get", "com.apple.ace.timer", None, refId)
    
    def to_plist(self):
        return super(TimerGet, self).to_plist()

class TimerGetCompleted(ServerBoundCommand):
    classIdentifier = "GetCompleted"
    groupIdentifier = "com.apple.ace.timer"
    def __init__(self, plist):
        self.timer = None # TimerObject
        super(TimerGetCompleted, self).__init__(plist)


class TimerSet(ClientBoundCommand):
    def __init__(self, refId, timer = None):
        super(TimerSet, self).__init__("Set", "com.apple.ace.timer", None, refId)
        self.timer = timer
    
    def to_plist(self):
        self.add_property("timer")
        return super(TimerSet, self).to_plist()

class TimerSetCompleted(ServerBoundCommand):
    classIdentifier = "SetCompleted"
    groupIdentifier = "com.apple.ace.timer"
    def __init__(self, plist):
        super(TimerSetCompleted, self).__init__(plist)

class TimerCancel(ClientBoundCommand):
    def __init__(self, refId):
        super(TimerCancel, self).__init__("Cancel", "com.apple.ace.timer", None, refId)
           
    def to_plist(self):
        return super(TimerCancel, self).to_plist()

class TimerCancelCompleted(ServerBoundCommand):
    classIdentifier = "CancelCompleted"
    groupIdentifier = "com.apple.ace.timer"
    def __init__(self, plist):
        self.timer = None # timer object
        super(TimerCancelCompleted, self).__init__(plist)



class TimerPause(ClientBoundCommand):
    def __init__(self, refId):
        super(TimerPause, self).__init__("Pause", "com.apple.ace.timer", None, refId)
           
    def to_plist(self):
        return super(TimerPause, self).to_plist()

class TimerPauseCompleted(ServerBoundCommand):
    classIdentifier = "PauseCompleted"
    groupIdentifier = "com.apple.ace.timer"
    def __init__(self, plist):
        super(TimerPauseCompleted, self).__init__(plist)


class TimerResume(ClientBoundCommand):
    def __init__(self, refId):
        super(TimerResume, self).__init__("Resume", "com.apple.ace.timer", None, refId)
           
    def to_plist(self):
        return super(TimerResume, self).to_plist()

class TimerResumeCompleted(ServerBoundCommand):
    classIdentifier = "ResumeCompleted"
    groupIdentifier = "com.apple.ace.timer"
    def __init__(self, plist):
        super(TimerResumeCompleted, self).__init__(plist)

class TimerSnippet(Snippet):                
    def __init__(self, timers = None, confirm = False):
        super(TimerSnippet, self).__init__("com.apple.ace.timer")
        self.timers = timers if timers != None else []
        if confirm:
            self.confirmationOptions = ConfirmationOptions(
                    submitCommands = [SendCommands([StartRequest(utterance="^timerConfirmation^=^yes^ ^timerVerb^=^set^ ^timerNoun^=^timer^")])],
                    cancelCommands = [SendCommands([StartRequest(utterance="^timerConfirmation^=^no^ ^timerVerb^=^set^ ^timerNoun^=^timer^")])],
                    denyCommands = [SendCommands([StartRequest(utterance="^timerConfirmation^=^no^ ^timerVerb^=^set^ ^timerNoun^=^timer^")])],
                    confirmCommands = [SendCommands([StartRequest(utterance="^timerConfirmation^=^yes^ ^timerVerb^=^set^ ^timerNoun^=^timer^")])],
                    denyText = "Keep it",
                    cancelLabel = "Keep it",
                    submitLabel = "Change it",
                    confirmText = "Change it",
                    cancelTrigger = "Confirm")
        else:
            self.confirmationOptions = None
    
    def to_plist(self):
        self.add_property('timers')
        return super(TimerSnippet, self).to_plist()

class TimerObject(DomainObject):
    def __init__(self, timerValue = None, state = None):
        super(TimerObject, self).__init__("com.apple.ace.timer")
        self.timerValue = timerValue #number 
        self.state = state #string
    
    def to_plist(self):
        self.add_property('timerValue')
        self.add_property('state')
        return super(TimerObject, self).to_plist()

########NEW FILE########
__FILENAME__ = uiObjects
from siriObjects.baseObjects import ClientBoundCommand, AceObject

class AddViews(ClientBoundCommand):
    def __init__(self, refId, scrollToTop=False, temporary=False, dialogPhase="Completion", views=None, callbacks=None):
        super(AddViews, self).__init__("AddViews", "com.apple.ace.assistant", None, refId, callbacks)
        self.scrollToTop = scrollToTop
        self.temporary = temporary
        self.dialogPhase = dialogPhase
        self.views = views if views != None else []
    
    def to_plist(self):
        self.add_property('scrollToTop')
        self.add_property('temporary')
        self.add_property('dialogPhase')
        self.add_property('views')
        return super(AddViews, self).to_plist()
    
class AceView(AceObject):
    def __init__(self, clazz, group):
        super(AceView, self).__init__(clazz, group)
        self.viewId = None # string
        self.speakableText = None # string
        self.listenAfterSpeaking = None # number

    def to_plist(self):
        self.add_property('viewId')
        self.add_property('speakableText')
        self.add_property('listenAfterSpeaking')
        return super(AceView, self).to_plist()


# Assistant-related objects
class AssistantUtteranceView(AceObject):
    def __init__(self, text="", speakableText="", dialogIdentifier="Misc#ident", listenAfterSpeaking=False):
        super(AssistantUtteranceView, self).__init__("AssistantUtteranceView", "com.apple.ace.assistant")
        self.text = text or speakableText
        self.speakableText = speakableText
        self.dialogIdentifier = dialogIdentifier
        self.listenAfterSpeaking = listenAfterSpeaking
    def to_plist(self):
        self.add_property('text')
        self.add_property('speakableText')
        self.add_property('dialogIdentifier')
        self.add_property('listenAfterSpeaking')
        return super(AssistantUtteranceView, self).to_plist()

class DisambiguationList(AceView):
    def __init__(self, items=None, speakableSelectionResponse="OK!", listenAfterSpeaking=True, speakableText="", speakableFinalDemitter="", speakableDemitter="", selectionResponse="OK!"):
        super(DisambiguationList, self).__init__("DisambiguationList", "com.apple.ace.assistant")
        self.items = items if items != None else []
        self.speakableSelectionResponse = speakableSelectionResponse
        self.listenAfterSpeaking = listenAfterSpeaking
        self.speakableFinalDemitter = speakableFinalDemitter
        self.selectionResponse = selectionResponse
        self.speakableText = speakableText

    def to_plist(self):
        self.add_property('items')
        self.add_property('speakableSelectionResponse')
        self.add_property('speakableFinalDemitter')
        self.add_property('selectionResponse')
        return super(DisambiguationList, self).to_plist()

class Button(AceObject):
    def __init__(self, text="", commands=None):
        super(Button, self).__init__("Button", "com.apple.ace.assistant")
        self.text = text
        self.commands = commands if commands != None else []

    def to_plist(self):
        self.add_property('text')
        self.add_property('commands')
        return super(Button, self).to_plist()

class OpenLink(AceObject):
    def __init__(self, ref=""):
        super(OpenLink, self).__init__("OpenLink", "com.apple.ace.assistant")
        self.ref = ref
    
    def to_plist(self):
        self.add_property('ref')
        return super(OpenLink, self).to_plist()


class HtmlView(AceObject):
    def __init__(self, html=""):
        super(HtmlView, self).__init__("HtmlView", "com.apple.ace.assistant")
        self.html = html
    
    def to_plist(self):
        self.add_property('html')
        return super(HtmlView, self).to_plist()

class MenuItem(AceObject):
    def __init__(self, title="", subtitle="", ref="", icon="", commands=None):
        super(MenuItem, self).__init__("MenuItem", "com.apple.ace.assistant")
        self.title = title
        self.subtitle = subtitle
        self.ref = ref
        self.icon = icon
        self.commands = commands if commands != None else []
    
    def to_plist(self):
        self.add_property('title')
        self.add_property('subtitle')
        self.add_property('ref')
        self.add_property('icon')
        self.add_property('commands')
        return super(MenuItem, self).to_plist()

class ListItem(AceView):
    def __init__(self, title="", selectionText="", commands=None, speakableText="", obj=None):
        super(ListItem, self).__init__("ListItem", "com.apple.ace.assistant")
        self.title= title
        self.selectionText = selectionText
        self.commands = commands if commands != None else []
        self.speakableText = speakableText
        self.object = obj

    def to_plist(self):
        self.add_property('title')
        self.add_property('selectionText')
        self.add_property('commands')
        self.add_property('object')
        return super(ListItem, self).to_plist()

class ConfirmationOptions(AceObject):
    def __init__(self, denyCommands=None, submitCommands=None, confirmText="Confirm", denyText="Cancel", cancelCommands=None, cancelLabel="Cancel", submitLabel="Confirm", confirmCommands=None, cancelTrigger="Deny"):
        super(ConfirmationOptions, self).__init__("ConfirmationOptions", "com.apple.ace.assistant")
        self.denyCommands = denyCommands if denyCommands != None else []
        self.submitCommands = submitCommands if submitCommands != None else []
        self.confirmText = confirmText
        self.denyText = denyText
        self.cancelCommands = cancelCommands if cancelCommands != None else []
        self.cancelLabel = cancelLabel
        self.submitLabel = submitLabel
        self.confirmCommands = confirmCommands if confirmCommands != None else []
        self.cancelTrigger = cancelTrigger
    
    def to_plist(self):
        self.add_property('denyCommands')
        self.add_property('submitCommands')
        self.add_property('confirmText')
        self.add_property('denyText')
        self.add_property('cancelCommands')
        self.add_property('cancelLabel')
        self.add_property('submitLabel')
        self.add_property('confirmCommands')
        self.add_property('cancelTrigger')
        return super(ConfirmationOptions, self).to_plist()

class CancelSnippet(AceObject):
    def __init__(self):
        super(CancelSnippet, self).__init__("CancelSnippet", "com.apple.ace.assistant")
    
class ConfirmSnippet(AceObject):
    def __init__(self):
        super(ConfirmSnippet, self).__init__("ConfirmSnippet", "com.apple.ace.assistant")

class Snippet(AceView):
    def __init__(self, group, clazz="Snippet"):
        super(Snippet, self).__init__(clazz, group)
        self.otherOptions = None # array
        self.confirmationOptions = None # ConfirmationOptions obj
    
    def to_plist(self):
        self.add_property('otherOptions')
        self.add_property('confirmationOptions')
        return super(Snippet, self).to_plist()


    

########NEW FILE########
__FILENAME__ = websearchObjects
from siriObjects.baseObjects import ClientBoundCommand, AceObject

class WebSearch(ClientBoundCommand):
    def __init__(self, refId=None, aceId=None, query="", provider="Default", targetAppId=""):
        super(WebSearch, self).__init__("Search", "com.apple.ace.websearch", aceId, refId)
        self.query = query
        self.provider = provider
        self.targetAppId = targetAppId

    def to_plist(self):
        self.add_property('query')
        self.add_property('provider')
        self.add_property('targetAppId')
        return super(WebSearch, self).to_plist()
########NEW FILE########
__FILENAME__ = siriServer
#!/usr/bin/python
# -*- coding: utf-8 -*-

try:
    import biplist
except ImportError:
    print "You need to install biplist package on your system! e.g. \"sudo easy_install biplist\""
    exit(-1)

try:
    from M2Crypto import BIO, RSA, X509
except ImportError:
    print "You must install M2Crypto on your system! (this might require openssl and SWIG) e.g. \"sudo easy_install m2crypto\""
    exit(-1)

import sys
if sys.version_info < (2, 6):
    print "You must use python 2.6 or greater"
    exit(-1)

import socket, ssl, zlib, binascii, time, select, struct, uuid, json, asyncore, re, threading, logging, pprint, sqlite3
from optparse import OptionParser
from email.utils import formatdate

import speex
import flac
import db
from db import Assistant

import PluginManager

from siriObjects import speechObjects, baseObjects, uiObjects, systemObjects
from siriObjects.baseObjects import ObjectIsCommand
from siriObjects.speechObjects import StartSpeech, StartSpeechRequest, StartSpeechDictation, SpeechPacket, SpeechFailure, FinishSpeech
from siriObjects.systemObjects import CancelRequest, CancelSucceeded, GetSessionCertificate, GetSessionCertificateResponse, CreateSessionInfoRequest, CommandFailed
from httpClient import AsyncOpenHttp

from sslDispatcher import ssl_dispatcher

import signal, os

class HandleConnection(ssl_dispatcher):
    __not_recognized = {"de-DE": u"Entschuldigung, ich verstehe \"{0}\" nicht.", "en-US": u"Sorry I don't understand {0}", "fr-FR": u"Désolé je ne comprends pas ce que \"{0}\" veut dire."}
    __websearch = {"de-DE": u"Websuche", "en-US": u"Websearch", "fr-FR": u"Rechercher sur le Web"}
    def __init__(self, conn):
        asyncore.dispatcher_with_send.__init__(self, conn)
        
        self.ssled = False
        self.secure_connection(certfile="server.passless.crt", keyfile="server.passless.key", server_side=True)               

        self.consumed_ace = False
        self.data = ""
        self.binary_mode = False
        self.decompressor = zlib.decompressobj()
        self.compressor = zlib.compressobj()
        self.unzipped_input = ""
        self.unzipped_output_buffer = ""
        self.output_buffer = ""
        self.speech = dict()
        self.pong = 1
        self.ping = 0
        self.httpClient = AsyncOpenHttp(self.handle_google_data, self.handle_google_failure)
        self.gotGoogleAnswer = False
        self.googleData = None
        self.lastRequestId = None
        self.dictation = None
        self.dbConnection = db.getConnection()
        self.assistant = None
        self.sendLock = threading.Lock()
        self.current_running_plugin = None
        self.current_location = None
        self.plugin_lastAceId = None
        self.logger = logging.getLogger("logger")
    
    def handle_ssl_established(self):                
        self.ssled = True

    def handle_ssl_shutdown(self):
        self.ssled = False
            
    def readable(self):
        if self.ssled:
            while self.socket.pending() > 0:
                self.handle_read_event()
        return True

    def handle_read(self):
        self.data += self.recv(8192)
        if not self.binary_mode:
            if "\r\n\r\n" in self.data:
                endOfHeader = self.data.find("\r\n\r\n")+4
                self.header = self.data[:endOfHeader]
                self.data = self.data[endOfHeader:]
                self.logger.debug("--------------------------------------Header start------------------------------------")
                self.logger.debug(self.header)
                self.logger.debug("---------------------------------------Header end-------------------------------------")
                self.binary_mode = True
                self.header_complete = True
        else:
            if not self.consumed_ace:
                self.logger.debug("Received removing ace instruction: {0}".format(repr(self.data[:4])))
                self.data = self.data[4:]
                self.consumed_ace = True
                self.output_buffer = "HTTP/1.1 200 OK\r\nServer: Apache-Coyote/1.1\r\nDate: " +  formatdate(timeval=None, localtime=False, usegmt=True) + "\r\nConnection: close\r\n\r\n\xaa\xcc\xee\x02"
                #self.flush_output_buffer()
            
            # first process outstanding google answers THIS happens at least on each PING
            if self.gotGoogleAnswer:
                self.process_recognized_speech(self.googleData, self.lastRequestId, self.dictation)
                self.lastRequestId = None
                self.dictation = None
                self.googleData = None
                self.gotGoogleAnswer = False
            
            self.process_compressed_data()

    def handle_google_data(self, body, requestId, dictation):
        self.googleData = json.loads(body)
        self.lastRequestId = requestId
        self.dictation = dictation
        self.gotGoogleAnswer = True

    def handle_google_failure(self, requestId, dictation):
        self.googleData = None
        self.lastRequestId = requestId
        self.dictation = dictation
        self.gotGoogleAnswer = True

    def send_object(self, obj):
        self.send_plist(obj.to_plist())

    def send_plist(self, plist):
        self.sendLock.acquire()
        self.logger.debug("Sending:\n{0}".format(pprint.pformat(plist, width=40)))
        bplist = biplist.writePlistToString(plist);
        #
        self.unzipped_output_buffer = struct.pack('>BI', 2,len(bplist)) + bplist
        self.flush_unzipped_output() 
        self.sendLock.release()
    
    def send_pong(self, id):
        self.sendLock.acquire()
        self.unzipped_output_buffer = struct.pack('>BI', 4, id)
        self.flush_unzipped_output() 
        self.sendLock.release()

    def process_recognized_speech(self, googleJson, requestId, dictation):
        if googleJson == None:
            # there was a network failure
            # is this the correct command to send?
            self.send_object(speechObjects.SpeechFailure(requestId, "No connection to Google possible"))
            self.send_object(baseObjects.RequestCompleted(requestId))
        else:
            possible_matches = googleJson['hypotheses']
            if len(possible_matches) > 0:
                best_match = possible_matches[0]['utterance']
                best_match = best_match[0].upper()+best_match[1:]
                best_match_confidence = possible_matches[0]['confidence']
                self.logger.info(u"Best matching result: \"{0}\" with a confidence of {1}%".format(best_match, round(float(best_match_confidence)*100,2)))
                # construct a SpeechRecognized
                token = speechObjects.Token(best_match, 0, 0, 1000.0, True, True)
                interpretation = speechObjects.Interpretation([token])
                phrase = speechObjects.Phrase(lowConfidence=False, interpretations=[interpretation])
                recognition = speechObjects.Recognition([phrase])
                recognized = speechObjects.SpeechRecognized(requestId, recognition)
                
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
                            view = uiObjects.AddViews(requestId)
                            errorText = HandleConnection.__not_recognized[self.assistant.language] if self.assistant.language in HandleConnection.__not_recognized else HandleConnection.__not_recognized["en-US"]
                            view.views += [uiObjects.AssistantUtteranceView(errorText.format(best_match), errorText.format(best_match))]
                            websearchText = HandleConnection.__websearch[self.assistant.language] if self.assistant.language in HandleConnection.__websearch else HandleConnection.__websearch["en-US"]
                            button = uiObjects.Button(text=websearchText)
                            cmd = systemObjects.SendCommands()
                            cmd.commands = [systemObjects.StartRequest(utterance=u"^webSearchQuery^=^{0}^^webSearchConfirmation^=^Yes^".format(best_match))]
                            button.commands = [cmd]
                            view.views.append(button)
                            self.send_object(view)
                            self.send_object(baseObjects.RequestCompleted(requestId))
                    elif self.current_running_plugin.waitForResponse != None:
                        # do we need to send a speech recognized here? i.d.k
                        self.current_running_plugin.response = best_match
                        self.current_running_plugin.refId = requestId
                        self.current_running_plugin.waitForResponse.set()
                    else:
                        self.send_object(recognized)
                        self.send_object(baseObjects.RequestCompleted(requestId))
                else:
                    self.send_object(recognized)
                    self.send_object(baseObjects.RequestCompleted(requestId))

    def process_compressed_data(self):
        self.unzipped_input += self.decompressor.decompress(self.data)
        self.data = ""
        while self.hasNextObj():
            reqObject = self.read_next_object_from_unzipped()
            if reqObject != None:
                self.logger.debug("Packet with class: {0}".format(reqObject['class']))
                self.logger.debug("packet with content:\n{0}".format(pprint.pformat(reqObject, width=40)))
                
                # first handle speech stuff
                
                if 'refId' in reqObject:
                    # if the following holds, this packet is an answer to a request by a plugin
                    if reqObject['refId'] == self.plugin_lastAceId and self.current_running_plugin != None:
                        if self.current_running_plugin.waitForResponse != None:
                            # just forward the object to the 
                            # don't change it's refId, further requests must reference last FinishSpeech
                            self.logger.info("Forwarding object to plugin")
                            self.plugin_lastAceId = None
                            self.current_running_plugin.response = reqObject if reqObject['class'] != "StartRequest" else reqObject['properties']['utterance']
                            self.current_running_plugin.waitForResponse.set()
                            continue
                
                if ObjectIsCommand(reqObject, StartSpeechRequest) or ObjectIsCommand(reqObject, StartSpeechDictation):
                    self.logger.info("New start of speech received")
                    startSpeech = None
                    if ObjectIsCommand(reqObject, StartSpeechDictation):
                        dictation = True
                        startSpeech = StartSpeechDictation(reqObject)
                    else:
                        dictation = False
                        startSpeech = StartSpeechRequest(reqObject)
            
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
                
                elif ObjectIsCommand(reqObject, SpeechPacket):
                    self.logger.info("Decoding speech packet")
                    speechPacket = SpeechPacket(reqObject)
                    (decoder, encoder, dictation) = self.speech[speechPacket.refId]
                    if decoder:
                        pcm = decoder.decode(speechPacket.packets)
                    else:
                        pcm = SpeechPacket.data # <- probably data... if pcm
                    encoder.encode(pcm)
                        
                elif reqObject['class'] == 'StartCorrectedSpeechRequest':
                    self.process_recognized_speech({u'hypotheses': [{'confidence': 1.0, 'utterance': str.lower(reqObject['properties']['utterance'])}]}, reqObject['aceId'], False)
            
                elif ObjectIsCommand(reqObject, FinishSpeech):
                    self.logger.info("End of speech received")
                    finishSpeech = FinishSpeech(reqObject)
                    (decoder, encoder, dictation) = self.speech[finishSpeech.refId]
                    if decoder:
                        decoder.destroy()
                    encoder.finish()
                    flacBin = encoder.getBinary()
                    encoder.destroy()
                    del self.speech[finishSpeech.refId]
                    
                    self.logger.info("Sending flac to google for recognition")
                    try:
                        self.httpClient.make_google_request(flacBin, finishSpeech.refId, dictation, language=self.assistant.language, allowCurses=True)
                    except AttributeError, TypeError:
                        self.logger.info("Unable to find language record for this assistant. Try turning Siri off and then back on.")
                        
                elif ObjectIsCommand(reqObject, CancelRequest):
                        # this is probably called when we need to kill a plugin
                        # wait for thread to finish a send
                        cancelRequest = CancelRequest(reqObject)
                        if cancelRequest.refId in self.speech:
                            del self.speech[cancelRequest.refId]
                        
                        self.send_object(CancelSucceeded(cancelRequest.aceId))

                elif ObjectIsCommand(reqObject, GetSessionCertificate):
                    getSessionCertificate = GetSessionCertificate(reqObject)
                    response = GetSessionCertificateResponse(getSessionCertificate.aceId, caCert.as_der(), serverCert.as_der())
                    self.send_object(response)

                elif ObjectIsCommand(reqObject, CreateSessionInfoRequest):
                    # how does a positive answer look like?
                    createSessionInfoRequest = CreateSessionInfoRequest(reqObject)
                    fail = CommandFailed(createSessionInfoRequest.aceId)
                    fail.reason = "Not authenticated"
                    fail.errorCode = 0
                    self.send_object(fail)

                    #self.send_plist({"class":"SessionValidationFailed", "properties":{"errorCode":"UnsupportedHardwareVersion"}, "aceId": str(uuid.uuid4()), "refId":reqObject['aceId'], "group":"com.apple.ace.system"})
                    
                elif reqObject['class'] == 'CreateAssistant':
                    #create a new assistant
                    helper = Assistant()
                    c = self.dbConnection.cursor()
                    noError = True
                    try:
                        c.execute("insert into assistants(assistantId, assistant) values (?,?)", (helper.assistantId, helper))
                        self.dbConnection.commit()
                    except sqlite3.Error, e: 
                        noError = False
                    c.close()
                    if noError:
                        self.assistant = helper
                        self.send_plist({"class": "AssistantCreated", "properties": {"speechId": str(uuid.uuid4()), "assistantId": helper.assistantId}, "group":"com.apple.ace.system", "callbacks":[], "aceId": str(uuid.uuid4()), "refId": reqObject['aceId']})
                    else:
                        self.send_plist({"class":"CommandFailed", "properties": {"reason":"Database error", "errorCode":2, "callbacks":[]}, "aceId": str(uuid.uuid4()), "refId": reqObject['aceId'], "group":"com.apple.ace.system"})
            
                elif reqObject['class'] == 'SetAssistantData':
                    # fill assistant 
                    if self.assistant != None:
                        c = self.dbConnection.cursor()
                        objProperties = reqObject['properties'] 
                        self.assistant.censorSpeech = objProperties['censorSpeech']
                        self.assistant.timeZoneId = objProperties['timeZoneId']
                        self.assistant.language = objProperties['language']
                        self.assistant.region = objProperties['region']
                        c.execute("update assistants set assistant = ? where assistantId = ?", (self.assistant, self.assistant.assistantId))
                        self.dbConnection.commit()
                        c.close()

            
                elif reqObject['class'] == 'LoadAssistant':
                    c = self.dbConnection.cursor()
                    c.execute("select assistant from assistants where assistantId = ?", (reqObject['properties']['assistantId'],))
                    self.dbConnection.commit()
                    result = c.fetchone()
                    if result == None:
                        self.send_plist({"class": "AssistantNotFound", "aceId":str(uuid.uuid4()), "refId":reqObject['aceId'], "group":"com.apple.ace.system"})
                    else:
                        self.assistant = result[0]
                        self.send_plist({"class": "AssistantLoaded", "properties": {"version": "20111216-32234-branches/telluride?cnxn=293552c2-8e11-4920-9131-5f5651ce244e", "requestSync":False, "dataAnchor":"removed"}, "aceId":str(uuid.uuid4()), "refId":reqObject['aceId'], "group":"com.apple.ace.system"})
                    c.close()

                elif reqObject['class'] == 'DestroyAssistant':
                    c = self.dbConnection.cursor()
                    c.execute("delete from assistants where assistantId = ?", (reqObject['properties']['assistantId'],))
                    self.dbConnection.commit()
                    c.close()
                    self.send_plist({"class": "AssistantDestroyed", "properties": {"assistantId": reqObject['properties']['assistantId']}, "aceId":str(uuid.uuid4()), "refId":reqObject['aceId'], "group":"com.apple.ace.system"})
                elif reqObject['class'] == 'StartRequest':
                    #this should also be handeled by special plugins, so lets call the plugin handling stuff
                    self.process_recognized_speech({'hypotheses': [{'utterance': reqObject['properties']['utterance'], 'confidence': 1.0}]}, reqObject['aceId'], False)

                    
    def hasNextObj(self):
        if len(self.unzipped_input) == 0:
            return False
        cmd, data = struct.unpack('>BI', self.unzipped_input[:5])
        if cmd in (3,4): #ping pong
            return True
        if cmd == 2:
            #print "expect: ", data+5,  " received: ", len(self.unzipped_input)
            return ((data + 5) < len(self.unzipped_input))
    
    def read_next_object_from_unzipped(self):
        cmd, data = struct.unpack('>BI', self.unzipped_input[:5])
        
        if cmd == 3: #ping
            self.ping = data
            self.logger.info("Received a Ping ({0})".format(data))
            self.logger.info("Returning a Pong ({0})".format(self.pong))
            self.send_pong(self.pong)
            self.pong += 1
            self.unzipped_input = self.unzipped_input[5:]
            return None

        object_size = data
        prefix = self.unzipped_input[:5]
        object_data = self.unzipped_input[5:object_size+5]
        self.unzipped_input = self.unzipped_input[object_size+5:]
        return self.parse_object(object_data)
    
    def parse_object(self, object_data):
        #this is a binary plist file
        plist = biplist.readPlistFromString(object_data)
        return plist

    def flush_unzipped_output(self):
            
        self.output_buffer += self.compressor.compress(self.unzipped_output_buffer)
        #make sure everything is compressed
        self.output_buffer += self.compressor.flush(zlib.Z_SYNC_FLUSH)
        ratio = float(len(self.unzipped_output_buffer))/float(len(self.output_buffer)) - 1
        if ratio < 0:
            self.logger.debug("Blowed up by {0:.2f} bytes ({1:.2%}) due to compression".format(-1*ratio*len(self.unzipped_output_buffer),ratio))
        else:
            self.logger.debug("Saved {0:.2f} bytes ({1:.2%}) using compression".format(ratio*len(self.unzipped_output_buffer), ratio))
        self.unzipped_output_buffer = ""

        self.flush_output_buffer()

    def flush_output_buffer(self):
        if len(self.output_buffer) > 0:
            self.send(self.output_buffer)
            self.output_buffer = ""

class SiriServer(asyncore.dispatcher):

    def __init__(self, host, port):
        asyncore.dispatcher.__init__(self)
        self.create_socket(socket.AF_INET, socket.SOCK_STREAM)
        self.set_reuse_addr()
        self.bind((host, port))
        self.listen(5)
        logging.getLogger("logger").info("Listening on port {0}".format(port))
        signal.signal(signal.SIGTERM, self.handler)
   
    def handler(self, signum, frame):
        if signum == signal.SIGTERM:
            x.info("Got SIGTERM, closing server")
            self.close()
    

    def handle_accept(self):
        pair = self.accept()
        if pair is None:
            pass
        else:
            sock, addr = pair
            logging.getLogger("logger").info('Incoming connection from {0}'.format(repr(addr)))
            handler = HandleConnection(sock)

# load the certificates
caCertFile = open('OrigAppleSubCACert.der')
caCert = X509.load_cert_bio(BIO.MemoryBuffer(caCertFile.read()), format=0)
caCertFile.close()
certFile = open('OrigAppleServerCert.der')
serverCert = X509.load_cert_bio(BIO.MemoryBuffer(certFile.read()), format=0)
certFile.close()



#setup logging

log_levels = {'debug':logging.DEBUG,
              'info':logging.INFO,
              'warning':logging.WARNING,
              'error':logging.ERROR,
              'critical':logging.CRITICAL
              }

parser = OptionParser()
parser.add_option('-l', '--loglevel', default='info', dest='logLevel', help='This sets the logging level you have these options: debug, info, warning, error, critical \t\tThe standard value is info')
parser.add_option('-p', '--port', default=443, type='int', dest='port', help='This options lets you use a custom port instead of 443 (use a port > 1024 to run as non root user)')
parser.add_option('--logfile', default=None, dest='logfile', help='Log to a file instead of stdout.')
(options, args) = parser.parse_args()

x = logging.getLogger("logger")
x.setLevel(log_levels[options.logLevel])

if options.logfile != None:
    h = logging.FileHandler(options.logfile)
else:
    h = logging.StreamHandler()

f = logging.Formatter(u"%(levelname)s %(funcName)s %(message)s")
h.setFormatter(f)
x.addHandler(h)


#setup database
db.setup()

#load Plugins
PluginManager.load_api_keys()
PluginManager.load_plugins()


#start server
x.info("Starting Server")
server = SiriServer('', options.port)
try:
    asyncore.loop()
except (asyncore.ExitNow, KeyboardInterrupt, SystemExit):
    x.info("Caught shutdown, closing server")
    asyncore.dispatcher.close(server)
    exit()

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
        libspeex.speex_bits_destroy(byref(self.bits))
        libspeex.speex_decoder_destroy(self.state)

########NEW FILE########
__FILENAME__ = sslDispatcher
#!/usr/bin/python
# -*- coding: utf-8 -*-

try:
    import ssl
    import asyncore
except ImportError:
    pass
else:
    class ssl_dispatcher(asyncore.dispatcher_with_send):
        """A dispatcher subclass supporting SSL."""

        _ssl_accepting = False
        _ssl_established = False
        _ssl_closing = False

        # --- public API

        def secure_connection(self, certfile, keyfile, version=ssl.PROTOCOL_TLSv1, verify=ssl.CERT_NONE, server_side=False):
            """Setup encrypted connection."""
            self.socket = ssl.wrap_socket(self.socket, do_handshake_on_connect=False, certfile=certfile, keyfile=keyfile, suppress_ragged_eofs=True, server_side=server_side)
            self._ssl_accepting = True

        def ssl_shutdown(self):
            """Tear down SSL layer switching back to a clear text connection."""
            if not self._ssl_established:
                raise ValueError("not using SSL")
            self._ssl_closing = True
            try:
                self.socket = self.socket.unwrap()
            except ssl.SSLError as err:
                if err.args[0] in (ssl.SSL_ERROR_WANT_READ, ssl.SSL_ERROR_WANT_WRITE):
                    return
                elif err.args[0] == ssl.SSL_ERROR_SSL:
                    pass
                else:
                    raise
            except socket.error as err:
                # Any "socket error" corresponds to a SSL_ERROR_SYSCALL
                # return from OpenSSL's SSL_shutdown(), corresponding to
                # a closed socket condition. See also:
                # http://www.mail-archive.com/openssl-users@openssl.org/msg60710.html
                pass
            self._ssl_closing = False
            self.handle_ssl_shutdown()

        def handle_ssl_established(self):
            """Called when the SSL handshake has completed."""
            self.log_info('unhandled handle_ssl_established event', 'warning')

        def handle_ssl_shutdown(self):
            """Called when SSL shutdown() has completed"""
            self.log_info('unhandled handle_ssl_shutdown event', 'warning')

        # --- internals

        def _do_ssl_handshake(self):
            try:
                self.socket.do_handshake()
            except ssl.SSLError as err:
                if err.args[0] in (ssl.SSL_ERROR_WANT_READ, ssl.SSL_ERROR_WANT_WRITE):
                    return
                elif err.args[0] == ssl.SSL_ERROR_EOF:
                    return self.handle_close()
                raise
            else:
                self._ssl_accepting = False
                self._ssl_established = True
                self.handle_ssl_established()

        def handle_read_event(self):
            if self._ssl_accepting:
                self._do_ssl_handshake()
            elif self._ssl_closing:
                self.ssl_shutdown()
            else:
                asyncore.dispatcher_with_send.handle_read_event(self)

        def handle_write_event(self):
            if self._ssl_accepting:
                self._do_ssl_handshake()
            elif self._ssl_closing:
                self.ssl_shutdown()
            else:
                asyncore.dispatcher_with_send.handle_write_event(self)

        def send(self, data):
            try:
                asyncore.dispatcher_with_send.send(self, data)
            except ssl.SSLError as err:
                if err.args[0] in (ssl.SSL_ERROR_EOF, ssl.SSL_ERROR_ZERO_RETURN):
                    return 0
                raise

        def recv(self, buffer_size):
            try:
                return asyncore.dispatcher_with_send.recv(self, buffer_size)
            except ssl.SSLError as err:
                if err.args[0] in (ssl.SSL_ERROR_EOF, ssl.SSL_ERROR_ZERO_RETURN):
                    self.handle_close()
                    return ''
                if err.args[0] in (ssl.SSL_ERROR_WANT_READ, ssl.SSL_ERROR_WANT_WRITE):
                    return ''
                raise



########NEW FILE########
