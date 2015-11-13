__FILENAME__ = tropo
"""
The TropoPython module. This module implements a set of classes and methods for manipulating the Voxeo Tropo WebAPI.

Usage:

----
from tropo import Tropo

tropo = Tropo()
tropo.say("Hello, World")
json = tropo.RenderJson()
----

You can write this JSON back to standard output to get Tropo to perform
the action. For example, on Google Appengine you might write something like:

handler.response.out.write(json)

Much of the time, a you will interact with Tropo by  examining the Result
object and communicating back to Tropo via the Tropo class methods, such
as "say". In some cases, you'll want to build a class object directly such as in :

    choices = tropo.Choices("[5 digits]").obj

    tropo.ask(choices,
              say="Please enter your 5 digit zip code.",
              attempts=3, bargein=True, name="zip", timeout=5, voice="dave")
    ...

NOTE: This module requires python 2.5 or higher.

"""

try:
    import cjson as jsonlib
    jsonlib.dumps = jsonlib.encode
    jsonlib.loads = jsonlib.decode
except ImportError:
    try:
        from django.utils import simplejson as jsonlib
    except ImportError:
        try:
            import simplejson as jsonlib
        except ImportError:
            import json as jsonlib

class TropoAction(object):
    """
    Class representing the base Tropo action.
    Two properties are provided in order to avoid defining the same attributes for every action.
    """
    @property
    def json(self):
        return self._dict

    @property
    def obj(self):
        return {self.action: self._dict}

class Ask(TropoAction):
    """
    Class representing the "ask" Tropo action. Builds an "ask" JSON object.
    Class constructor arg: choices, a Choices object
    Convenience function: Tropo.ask()
    Class constructor options: attempts, bargein, choices, minConfidence, name, recognizer, required, say, timeout, voice

    Request information from the caller and wait for a response.
    (See https://www.tropo.com/docs/webapi/ask.htm)

        { "ask": {
            "attempts": Integer,
            "allowSiganls": String or Array,
            "bargein": Boolean,
            "choices": Object, #Required
            "interdigitTimeout": Integer,
            "minConfidence": Integer,
            "name": String,
            "recognizer": String,
            "required": Boolean,
            "say": Object,
            "sensitivity": Integer,
            "speechCompleteTimeout": Integer,
            "speechIncompleteTimeout": Integer,
            "timeout": Float,
            "voice": String,
             
            ,
             } }

    """
    action = 'ask'
    options_array = ['attempts', 'allowSiganls', 'bargein', 'choices', 'interdigitTimeout', 'minConfidence', 'name', 'recognizer', 'required', 'say', 'sensitivity', 'speechCompleteTimeout', 'speechIncompleteTimeout', 'timeout', 'voice']

    def __init__(self, choices, **options):
        self._dict = {}
        if (isinstance(choices, basestring)):
            self._dict['choices'] = Choices(choices).json
        else:
#            self._dict['choices'] = choices['choices']
            self._dict['choices'] = choices.json
        for opt in self.options_array:
            if opt in options:
                if ((opt == 'say') and (isinstance(options['say'], basestring))):
                    self._dict['say'] = Say(options['say']).json
                else:
                    self._dict[opt] = options[opt]

class Call(TropoAction):
    """
    Class representing the "call" Tropo action. Builds a "call" JSON object.
    Class constructor arg: to, a String
    Class constructor options: answerOnMedia, channel, from, headers, name, network, recording, required, timeout
    Convenience function: Tropo.call()

    (See https://www.tropo.com/docswebapi/call.htm)

    { "call": {
        "to": String or Array,#Required
        "answerOnMedia": Boolean,
        "allowSignals": String or Array
        "channel": string,
        "from": string,
        "headers": Object,
        "name": String,
        "network": String,
        "recording": Array or Object,
        "required": Boolean,
        "timeout": Float } }
    """
    action = 'call'
    options_array = ['answerOnMedia', 'allowSignals', 'channel', '_from', 'headers', 'name', 'network', 'recording', 'required', 'timeout']

    def __init__(self, to, **options):
        self._dict = {'to': to}
        for opt in self.options_array:
            if opt in options:
                if (opt == "_from"):
                    self._dict['from'] = options[opt]
                else:
                    self._dict[opt] = options[opt]

                

class Choices(TropoAction):
    """
    Class representing choice made by a user. Builds a "choices" JSON object.
    Class constructor options: terminator, mode

    (See https://www.tropo.com/docs/webapi/ask.htm)
    """
    action = 'choices'
    options_array = ['terminator', 'mode']

    def __init__(self, value, **options):
        self._dict = {'value': value}
        for opt in self.options_array:
            if opt in options:
                self._dict[opt] = options[opt]

class Conference(TropoAction):
    """
    Class representing the "conference" Tropo action. Builds a "conference" JSON object.
    Class constructor arg: id, a String
    Convenience function: Tropo.conference()
    Class constructor options: mute, name, playTones, required, terminator

    (See https://www.tropo.com/docs/webapi/conference.htm)

    { "conference": {
        "id": String,#Required
        "allowSignals": String or Array,
        "interdigitTimeout":Integer,
        "mute": Boolean,
        "name": String,
        "playTones": Boolean,
        "required": Boolean,
        "terminator": String } }
    """
    action = 'conference'
    options_array = ['allowSignals', 'interdigitTimeout', 'mute', 'name', 'playTones', 'required', 'terminator']

    def __init__(self, id, **options):
        self._dict = {'id': id}
        for opt in self.options_array:
            if opt in options:
                self._dict[opt] = options[opt]

class Hangup(TropoAction):
    """
    Class representing the "hangup" Tropo action. Builds a "hangup" JSON object.
    Class constructor arg:
    Class constructor options:
    Convenience function: Tropo.hangup()

    (See https://www.tropo.com/docs/webapi/hangup.htm)

    { "hangup": { } }
    """
    action = 'hangup'

    def __init__(self):
        self._dict = {}

class Message(TropoAction):
    """
    Class representing the "message" Tropo action. Builds a "message" JSON object.
    Class constructor arg: say_obj, a Say object
    Class constructor arg: to, a String
    Class constructor options: answerOnMedia, channel, from, name, network, required, timeout, voice
    Convenience function: Tropo.message()

    (See https://www.tropo.com/docs/webapi/message.htm)
    { "message": {
            "say": Object,#Required
            "to": String or Array,#Required
            "answerOnMedia": Boolean,
            "channel": string,
            "from": String,
            "name": String,
            "network": String,
            "required": Boolean,
            "timeout": Float,
            "voice": String } }
    """
    action = 'message'
    options_array = ['answerOnMedia', 'channel', '_from', 'name', 'network', 'required', 'timeout', 'voice']

    def __init__(self, say_obj, to, **options):
        self._dict = {'say': say_obj['say'], 'to': to}
        for opt in self.options_array:
            if opt in options:
                if (opt == "_from"):
                    self._dict['from'] = options[opt]
                else:
                    self._dict[opt] = options[opt]


class On(TropoAction):
    """
    Class representing the "on" Tropo action. Builds an "on" JSON object.
    Class constructor arg: event, a String
    Class constructor options:  name,next,required,say
    Convenience function: Tropo.on()

    (See https://www.tropo.com/docs/webapi/on.htm)

    { "on": {
        "event": String,#Required
        "name": String,
        "next": String,
        "required": Boolean,
        "say": Object
        "voice": String } }
    """
    action = 'on'
    options_array = ['name','next','required','say', 'voice']

    def __init__(self, event, **options):
        self._dict = {'event': event}
        for opt in self.options_array:
            if opt in options:
                if ((opt == 'say') and (isinstance(options['say'], basestring))):
                    if('voice' in options):
                      self._dict['say'] = Say(options['say'], voice=options['voice']).json
                    else:
                      self._dict['say'] = Say(options['say']).json
                elif(opt != 'voice'):
                    self._dict[opt] = options[opt]

class Record(TropoAction):
    """
    Class representing the "record" Tropo action. Builds a "record" JSON object.
    Class constructor arg:
    Class constructor options: attempts, bargein, beep, choices, format, maxSilence, maxTime, method, minConfidence, name, password, required, say, timeout, transcription, url, username
    Convenience function: Tropo.record()

    (See https://www.tropo.com/docs/webapi/record.htm)

        { "record": {
            "attempts": Integer,
            "bargein": Boolean,
            "beep": Boolean,
            "choices": Object,
            "format": String,
            "maxSilence": Float,
            "maxTime": Float,
            "method": String,
            "minConfidence": Integer,
            "name": String,
            "password": String,
            "required": Boolean,
            "say": Object,
            "timeout": Float,
            "transcription": Array or Object,
            "url": String,#Required ?????
            "username": String,
            "voice": String} }
    """
    action = 'record'
    options_array = ['attempts', 'bargein', 'beep', 'choices', 'format', 'maxSilence', 'maxTime', 'method', 'minConfidence', 'name', 'password', 'required', 'say', 'timeout', 'transcription', 'url', 'username', 'allowSignals', 'voice', 'interdigitTimeout']

    def __init__(self, **options):
        self._dict = {}
        for opt in self.options_array:
            if opt in options:
                if ((opt == 'say') and (isinstance(options['say'], basestring))):
                    self._dict['say'] = Say(options['say']).json
                else:
                    self._dict[opt] = options[opt]

class Redirect(TropoAction):
    """
    Class representing the "redirect" Tropo action. Builds a "redirect" JSON object.
    Class constructor arg: to, a String
    Class constructor options:  name, required
    Convenience function: Tropo.redirect()

    (See https://www.tropo.com/docs/webapi/redirect.htm)

    { "redirect": {
        "to": Object,#Required
        "name": String,
        "required": Boolean } }
    """
    action = 'redirect'
    options_array = ['name', 'required']

    def __init__(self, to, **options):
        self._dict = {'to': to}
        for opt in self.options_array:
            if opt in options:
                self._dict[opt] = options[opt]

class Reject(TropoAction):
    """
    Class representing the "reject" Tropo action. Builds a "reject" JSON object.
    Class constructor arg:
    Class constructor options:
    Convenience function: Tropo.reject()

    (See https://www.tropo.com/docs/webapi/reject.htm)

    { "reject": { } }
    """
    action = 'reject'

    def __init__(self):
        self._dict = {}

class Say(TropoAction):
    """
    Class representing the "say" Tropo action. Builds a "say" JSON object.
    Class constructor arg: message, a String, or a List of Strings
    Class constructor options: attempts, bargein, choices, minConfidence, name, recognizer, required, say, timeout, voice
    Convenience function: Tropo.say()

    (See https://www.tropo.com/docs/webapi/say.htm)

    { "say": {
        "voice": String,
        "as": String,
        "name": String,
        "required": Boolean,
        "value": String #Required
        } }
    """
    action = 'say'
    # added _as because 'as' is reserved
    options_array = ['_as', 'name', 'required', 'voice', 'allowSignals']

    def __init__(self, message, **options):
        dict = {}
        for opt in self.options_array:
            if opt in options:
                if (opt == "_as"):
                    dict['as'] = options['_as']
                else:
                    dict[opt] = options[opt]
        self._list = []
        if (isinstance (message, list)):
            for mess in message:
                new_dict = dict.copy()
                new_dict['value'] = mess
                self._list.append(new_dict)
        else:
            dict['value'] = message
            self._list.append(dict)

    @property
    def json(self):
        return self._list[0] if len(self._list) == 1 else self._list

    @property
    def obj(self):
        return {self.action: self._list[0]} if len(self._list) == 1 else {self.action: self._list}

class StartRecording(TropoAction):
    """
    Class representing the "startRecording" Tropo action. Builds a "startRecording" JSON object.
    Class constructor arg: url, a String
    Class constructor options: format, method, username, password
    Convenience function: Tropo.startRecording()

    (See https://www.tropo.com/docs/webapi/startrecording.htm)

    { "startRecording": {
        "format": String,
        "method": String,
        "url": String,#Required
        "username": String,
        "password": String, 
        "transcriptionID": String
        "transcriptionEmailFormat":String
        "transcriptionOutURI": String} }
    """
    action = 'startRecording'
    options_array = ['format', 'method', 'username', 'password', 'transcriptionID', 'transcriptionEmailFormat', 'transcriptionOutURI']

    def __init__(self, url, **options):
        self._dict = {'url': url}
        for opt in self.options_array:
            if opt in options:
                self._dict[opt] = options[opt]

class StopRecording(TropoAction):
   """
    Class representing the "stopRecording" Tropo action. Builds a "stopRecording" JSON object.
    Class constructor arg:
    Class constructor options:
    Convenience function: Tropo.stopRecording()

   (See https://www.tropo.com/docs/webapi/stoprecording.htm)
      { "stopRecording": { } }
   """
   action = 'stopRecording'

   def __init__(self):
       self._dict = {}

class Transfer(TropoAction):
    """
    Class representing the "transfer" Tropo action. Builds a "transfer" JSON object.
    Class constructor arg: to, a String, or List
    Class constructor options: answerOnMedia, choices, from, name, required, terminator
    Convenience function: Tropo.transfer()

    (See https://www.tropo.com/docs/webapi/transfer.htm)
    { "transfer": {
        "to": String or Array,#Required
        "answerOnMedia": Boolean,
        "choices": Object,
	# # **Wed May 18 21:14:05 2011** -- egilchri
	"headers": Object,
	# # **Wed May 18 21:14:05 2011** -- egilchri
	
        "from": String,
        "name": String,
        "required": Boolean,
        "terminator": String,
        "timeout": Float } }
    """
    action = 'transfer'
    options_array = ['answerOnMedia', 'choices', '_from', 'name', 'on', 'required', 'allowSignals', 'headers', 'interdigitTimeout', 'ringRepeat', 'timeout']

    def __init__(self, to, **options):
        self._dict = {'to': to}
        for opt in self.options_array:
            if opt in options:
                if (opt == '_from'):
                    self._dict['from'] = options['_from']
                elif(opt == 'choices'):
                    self._dict['choices'] = options['choices']
                else:
                    self._dict[opt] = options[opt]
                    
class Wait(TropoAction):
      """
      Class representing the "wait" Tropo action. Builds a "wait" JSON object.
      Class constructor arg: milliseconds, an Integer
      Class constructor options: allowSignals
      Convenience function: Tropo.wait()

      (See https://www.tropo.com/docs/webapi/wait.htm)
      { "wait": {
          "milliseconds": Integer,#Required
          "allowSignals": String or Array
      """
      
      action = 'wait'
      options_array = ['allowSignals']

      def __init__(self, milliseconds, **options):
          self._dict = {'milliseconds': milliseconds}
          for opt in self.options_array:
              if opt in options:
                self._dict[opt] = options[opt]

class Result(object):
    """
    Returned anytime a request is made to the Tropo Web API.
    Method: getValue
    (See https://www.tropo.com/docs/webapi/result.htm)

        { "result": {
            "actions": Array or Object,
            "complete": Boolean,
            "error": String,
            "sequence": Integer,
            "sessionDuration": Integer,
            "sessionId": String,
            "state": String } }
    """
    options_array = ['actions','complete','error','sequence', 'sessionDuration', 'sessionId', 'state']

    def __init__(self, result_json):
        result_data = jsonlib.loads(result_json)
        result_dict = result_data['result']

        for opt in self.options_array:
            if result_dict.get(opt, False):
                setattr(self, '_%s' % opt, result_dict[opt])

    def getValue(self):
        """
        Get the value of the previously POSTed Tropo action.
        """
        actions = self._actions

        if (type (actions) is list):
            dict = actions[0]
        else:
            dict = actions
        # return dict['value'] Fixes issue 17
        return dict['value']

# # **Tue May 17 07:17:38 2011** -- egilchri

    def getInterpretation(self):
        """
        Get the value of the previously POSTed Tropo action.
        """
        actions = self._actions

        if (type (actions) is list):
            dict = actions[0]
        else:
            dict = actions
        return dict['interpretation']

# # **Tue May 17 07:17:38 2011** -- egilchri


class Session(object):
    """
    Session is the payload sent as an HTTP POST to your web application when a new session arrives.
    (See https://www.tropo.com/docs/webapi/session.htm)
    
    Because 'from' is a reserved word in Python, the session object's 'from' property is called
    fromaddress in the Python library
    """
    def __init__(self, session_json):
        session_data = jsonlib.loads(session_json)
        session_dict = session_data['session']
        for key in session_dict:
            val = session_dict[key]
            if key == "from":
                setattr(self, "fromaddress", val)
            else:
                setattr(self, key, val)
	setattr(self, 'dict', session_dict)


class Tropo(object):
    """
      This is the top level class for all the Tropo web api actions.
      The methods of this class implement individual Tropo actions.
      Individual actions are each methods on this class.

      Each method takes one or more required arguments, followed by optional
      arguments expressed as key=value pairs.

      The optional arguments for these methods are described here:
      https://www.tropo.com/docs/webapi/
    """
    def  __init__(self):
        self._steps = []

# # **Sun May 15 21:05:01 2011** -- egilchri
    def setVoice(self, voice):
        self.voice = voice

# # end **Sun May 15 21:05:01 2011** -- egilchri

    def ask(self, choices, **options):
        """
	 Sends a prompt to the user and optionally waits for a response.
         Arguments: "choices" is a Choices object
         See https://www.tropo.com/docs/webapi/ask.htm
        """
# # **Sun May 15 21:21:29 2011** -- egilchri

        # Settng the voice in this method call has priority.
	# Otherwise, we can pick up the voice from the Tropo object,
	# if it is set there.
        if hasattr (self, 'voice'):
            if (not 'voice' in options):
                options['voice'] = self.voice
        
# # **Sun May 15 21:21:29 2011** -- egilchri

        self._steps.append(Ask(choices, **options).obj)


    def call (self, to, **options):
        """
	 Places a call or sends an an IM, Twitter, or SMS message. To start a call, use the Session API to tell Tropo to launch your code.

	 Arguments: to is a String.
	 Argument: **options is a set of optional keyword arguments.
	 See https://www.tropo.com/docs/webapi/call.htm
        """
        self._steps.append(Call (to, **options).obj)

    def conference(self, id, **options):
        """
        This object allows multiple lines in separate sessions to be conferenced together so that the parties on each line can talk to each other simultaneously.
	This is a voice channel only feature.
	Argument: "id" is a String
        Argument: **options is a set of optional keyword arguments.
	See https://www.tropo.com/docs/webapi/conference.htm
        """
        self._steps.append(Conference(id, **options).obj)

    def hangup(self):
        """
        This method instructs Tropo to "hang-up" or disconnect the session associated with the current session.
	See https://www.tropo.com/docs/webapi/hangup.htm
        """
        self._steps.append(Hangup().obj)

    def message (self, say_obj, to, **options):
        """
	A shortcut method to create a session, say something, and hang up, all in one step. This is particularly useful for sending out a quick SMS or IM.

 	Argument: "say_obj" is a Say object
        Argument: "to" is a String
        Argument: **options is a set of optional keyword arguments.
        See https://www.tropo.com/docs/webapi/message.htm
        """
        if isinstance(say_obj, basestring):
            say = Say(say_obj).obj
        else:
            say = say_obj
        self._steps.append(Message(say, to, **options).obj)

    def on(self, event, **options):
        """
        Adds an event callback so that your application may be notified when a particular event occurs.
	      Possible events are: "continue", "error", "incomplete" and "hangup".
	      Argument: event is an event
        Argument: **options is a set of optional keyword arguments.
        See https://www.tropo.com/docs/webapi/on.htm
        """
        
        if hasattr (self, 'voice'):
          if (not 'voice' in options):
            options['voice'] = self.voice


        self._steps.append(On(event, **options).obj)

    def record(self, **options):
        """
	 Plays a prompt (audio file or text to speech) and optionally waits for a response from the caller that is recorded.
         Argument: **options is a set of optional keyword arguments.
	 See https://www.tropo.com/docs/webapi/record.htm
        """
        self._steps.append(Record(**options).obj)

    def redirect(self, id, **options):
        """
        Forwards an incoming call to another destination / phone number before answering it.
        Argument: id is a String
        Argument: **options is a set of optional keyword arguments.
        See https://www.tropo.com/docs/webapi/redirect.htm
        """
        self._steps.append(Redirect(id, **options).obj)

    def reject(self):
        """
        Allows Tropo applications to reject incoming sessions before they are answered.
        See https://www.tropo.com/docs/webapi/reject.htm
        """
        self._steps.append(Reject().obj)

    def say(self, message, **options):
        """
	When the current session is a voice channel this key will either play a message or an audio file from a URL.
	In the case of an text channel it will send the text back to the user via i nstant messaging or SMS.
        Argument: message is a string
        Argument: **options is a set of optional keyword arguments.
        See https://www.tropo.com/docs/webapi/say.htm
        """
        #voice = self.voice
# # **Sun May 15 21:21:29 2011** -- egilchri

        # Settng the voice in this method call has priority.
	# Otherwise, we can pick up the voice from the Tropo object,
	# if it is set there.
        if hasattr (self, 'voice'):
            if (not 'voice' in options):
                options['voice'] = self.voice
# # **Sun May 15 21:21:29 2011** -- egilchri

        self._steps.append(Say(message, **options).obj)

    def startRecording(self, url, **options):
        """
        Allows Tropo applications to begin recording the current session.
        Argument: url is a string
        Argument: **options is a set of optional keyword arguments.
        See https://www.tropo.com/docs/webapi/startrecording.htm
        """
        self._steps.append(StartRecording(url, **options).obj)

    def stopRecording(self):
        """
        Stops a previously started recording.
	See https://www.tropo.com/docs/webapi/stoprecording.htm
        """
        self._steps.append(StopRecording().obj)

    def transfer(self, to, **options):
        """
        Transfers an already answered call to another destination / phone number.
	Argument: to is a string
        Argument: **options is a set of optional keyword arguments.
        See https://www.tropo.com/docs/webapi/transfer.htm
        """
        self._steps.append(Transfer(to, **options).obj)
        
    def wait(self, milliseconds, **options):
      """
      Allows the thread to sleep for a given amount of time in milliseconds
      Argument: milliseconds is an Integer
      Argument: **options is a set of optional keyword arguments.
      See https://www.tropo.com/docs/webapi/wait.htm
      """
      self._steps.append(Wait(milliseconds, **options).obj)
      
    def RenderJson(self, pretty=False):
        """
        Render a Tropo object into a Json string.
        """
        steps = self._steps
        topdict = {}
        topdict['tropo'] = steps
        if pretty:
            try:
                json = jsonlib.dumps(topdict, indent=4, sort_keys=False)
            except TypeError:
                json = jsonlib.dumps(topdict)
        else:
            json = jsonlib.dumps(topdict)
        return json

if __name__ == '__main__':
    print """

 This is the Python web API for http://www.tropo.com/

 To run the test suite, please run:

    cd test
    python test.py


"""



########NEW FILE########
__FILENAME__ = GoogleS3
#!/usr/bin/env python

#  This software code is made available "AS IS" without warranties of any
#  kind.  You may copy, display, modify and redistribute the software
#  code either by itself or as incorporated into your code; provided that
#  you do not remove any proprietary notices.  Your use of this software
#  code is at your own risk and you waive any claim against Amazon
#  Digital Services, Inc. or its affiliates with respect to your use of
#  this software code. (c) 2006-2007 Amazon Digital Services, Inc. or its
#  affiliates.

# edited to work with Google App Engine - Maciej Ceglowski 

import base64
import hmac
import httplib
import re
import sha
import sys
import time
import urllib
import urlparse
import xml.sax
from google.appengine.api.urlfetch import * 

DEFAULT_HOST = 's3.amazonaws.com'
PORTS_BY_SECURITY = { True: 443, False: 80 }
METADATA_PREFIX = 'x-amz-meta-'
AMAZON_HEADER_PREFIX = 'x-amz-'

# generates the aws canonical string for the given parameters
def canonical_string(method, bucket="", key="", query_args={}, headers={}, expires=None):
    interesting_headers = {}
    for header_key in headers:
        lk = header_key.lower()
        if lk in ['content-md5', 'content-type', 'date'] or lk.startswith(AMAZON_HEADER_PREFIX):
            interesting_headers[lk] = headers[header_key].strip()

    # these keys get empty strings if they don't exist
    if not interesting_headers.has_key('content-type'):
        interesting_headers['content-type'] = ''
    if not interesting_headers.has_key('content-md5'):
        interesting_headers['content-md5'] = ''

    # just in case someone used this.  it's not necessary in this lib.
    if interesting_headers.has_key('x-amz-date'):
        interesting_headers['date'] = ''

    # if you're using expires for query string auth, then it trumps date
    # (and x-amz-date)
    if expires:
        interesting_headers['date'] = str(expires)

    sorted_header_keys = interesting_headers.keys()
    sorted_header_keys.sort()

    buf = "%s\n" % method
    for header_key in sorted_header_keys:
        if header_key.startswith(AMAZON_HEADER_PREFIX):
            buf += "%s:%s\n" % (header_key, interesting_headers[header_key])
        else:
            buf += "%s\n" % interesting_headers[header_key]

    # append the bucket if it exists
    if bucket != "":
        buf += "/%s" % bucket

    # add the key.  even if it doesn't exist, add the slash
    buf += "/%s" % urllib.quote_plus(key)

    # handle special query string arguments

    if query_args.has_key("acl"):
        buf += "?acl"
    elif query_args.has_key("torrent"):
        buf += "?torrent"
    elif query_args.has_key("logging"):
        buf += "?logging"
    elif query_args.has_key("location"):
        buf += "?location"

    return buf

# computes the base64'ed hmac-sha hash of the canonical string and the secret
# access key, optionally urlencoding the result
def encode(aws_secret_access_key, str, urlencode=False):
    b64_hmac = base64.encodestring(hmac.new(aws_secret_access_key, str, sha).digest()).strip()
    if urlencode:
        return urllib.quote_plus(b64_hmac)
    else:
        return b64_hmac

def merge_meta(headers, metadata):
    final_headers = headers.copy()
    for k in metadata.keys():
        final_headers[METADATA_PREFIX + k] = metadata[k]

    return final_headers

# builds the query arg string
def query_args_hash_to_string(query_args):
    query_string = ""
    pairs = []
    for k, v in query_args.items():
        piece = k
        if v != None:
            piece += "=%s" % urllib.quote_plus(str(v))
        pairs.append(piece)

    return '&'.join(pairs)


class CallingFormat:
    PATH = 1
    SUBDOMAIN = 2
    VANITY = 3

    def build_url_base(protocol, server, port, bucket, calling_format):
        url_base = '%s://' % protocol

        if bucket == '':
            url_base += server
        elif calling_format == CallingFormat.SUBDOMAIN:
            url_base += "%s.%s" % (bucket, server)
        elif calling_format == CallingFormat.VANITY:
            url_base += bucket
        else:
            url_base += server

        url_base += ":%s" % port

        if (bucket != '') and (calling_format == CallingFormat.PATH):
            url_base += "/%s" % bucket

        return url_base

    build_url_base = staticmethod(build_url_base)



class Location:
    DEFAULT = None
    EU = 'EU'



class AWSAuthConnection:
    def __init__(self, aws_access_key_id, aws_secret_access_key, is_secure=True,
            server=DEFAULT_HOST, port=None, calling_format=CallingFormat.SUBDOMAIN):

        if not port:
            port = PORTS_BY_SECURITY[is_secure]

        self.aws_access_key_id = aws_access_key_id
        self.aws_secret_access_key = aws_secret_access_key
        self.is_secure = is_secure
        self.server = server
        self.port = port
        self.calling_format = calling_format

    def create_bucket(self, bucket, headers={}):
        return Response(self._make_request('PUT', bucket, '', {}, headers))

    def create_located_bucket(self, bucket, location=Location.DEFAULT, headers={}):
        if location == Location.DEFAULT:
            body = ""
        else:
            body = "<CreateBucketConstraint><LocationConstraint>" + \
                   location + \
                   "</LocationConstraint></CreateBucketConstraint>"
        return Response(self._make_request('PUT', bucket, '', {}, headers, body))

    def check_bucket_exists(self, bucket):
        return self._make_request('HEAD', bucket, '', {}, {})

    def list_bucket(self, bucket, options={}, headers={}):
        return ListBucketResponse(self._make_request('GET', bucket, '', options, headers))

    def delete_bucket(self, bucket, headers={}):
        return Response(self._make_request('DELETE', bucket, '', {}, headers))

    def put(self, bucket, key, object, headers={}):
        if not isinstance(object, S3Object):
            object = S3Object(object)

        return Response(
                self._make_request(
                    'PUT',
                    bucket,
                    key,
                    {},
                    headers,
                    object.data,
                    object.metadata))

    def get(self, bucket, key, headers={}):
        return GetResponse(
                self._make_request('GET', bucket, key, {}, headers))

    def delete(self, bucket, key, headers={}):
        return Response(
                self._make_request('DELETE', bucket, key, {}, headers))

    def get_bucket_logging(self, bucket, headers={}):
        return GetResponse(self._make_request('GET', bucket, '', { 'logging': None }, headers))

    def put_bucket_logging(self, bucket, logging_xml_doc, headers={}):
        return Response(self._make_request('PUT', bucket, '', { 'logging': None }, headers, logging_xml_doc))

    def get_bucket_acl(self, bucket, headers={}):
        return self.get_acl(bucket, '', headers)

    def get_acl(self, bucket, key, headers={}):
        return GetResponse(
                self._make_request('GET', bucket, key, { 'acl': None }, headers))

    def put_bucket_acl(self, bucket, acl_xml_document, headers={}):
        return self.put_acl(bucket, '', acl_xml_document, headers)

    def put_acl(self, bucket, key, acl_xml_document, headers={}):
        return Response(
                self._make_request(
                    'PUT',
                    bucket,
                    key,
                    { 'acl': None },
                    headers,
                    acl_xml_document))

    def list_all_my_buckets(self, headers={}):
        return ListAllMyBucketsResponse(self._make_request('GET', '', '', {}, headers))

    def get_bucket_location(self, bucket):
        return LocationResponse(self._make_request('GET', bucket, '', {'location' : None}))

    # end public methods


    def _make_request(self, method, bucket='', key='', query_args={}, headers={}, data='', metadata={}):

        server = ''
        if bucket == '':
            server = self.server
        elif self.calling_format == CallingFormat.SUBDOMAIN:
            server = "%s.%s" % (bucket, self.server)
        elif self.calling_format == CallingFormat.VANITY:
            server = bucket
        else:
            server = self.server

        path = ''

        if (bucket != '') and (self.calling_format == CallingFormat.PATH):
            path += "/%s" % bucket

        # add the slash after the bucket regardless
        # the key will be appended if it is non-empty
        path += "/%s" % urllib.quote_plus(key)


        # build the path_argument string
        # add the ? in all cases since 
        # signature and credentials follow path args
        if len(query_args):
            path += "?" + query_args_hash_to_string(query_args)

        is_secure = self.is_secure
        host = "%s:%d" % (server, self.port)
        while True:
          
            final_headers = merge_meta(headers, metadata);
            # add auth header
            self._add_aws_auth_header(final_headers, method, bucket, key, query_args)
            resp = fetch("https://" + host + path,data,method,final_headers)
            
            
            if resp.status_code < 300 or resp.status_code >= 400:
                return resp
            # handle redirect
            try:
                location = resp.headers['location']
            except:
                return resp
            # (close connection)
           # resp.read()
            scheme, host, path, params, query, fragment \
                    = urlparse.urlparse(location)
            if scheme == "http":    is_secure = True
            elif scheme == "https": is_secure = False
            else: raise invalidURL("Not http/https: " + location)
            if query: path += "?" + query
            # retry with redirect
            
    def _xmake_request(self, method, bucket='', key='', query_args={}, headers={}, data='', metadata={}):

        server = ''
        if bucket == '':
            server = self.server
        elif self.calling_format == CallingFormat.SUBDOMAIN:
            server = "%s.%s" % (bucket, self.server)
        elif self.calling_format == CallingFormat.VANITY:
            server = bucket
        else:
            server = self.server

        path = ''

        if (bucket != '') and (self.calling_format == CallingFormat.PATH):
            path += "/%s" % bucket

        # add the slash after the bucket regardless
        # the key will be appended if it is non-empty
        path += "/%s" % urllib.quote_plus(key)


        # build the path_argument string
        # add the ? in all cases since 
        # signature and credentials follow path args
        if len(query_args):
            path += "?" + query_args_hash_to_string(query_args)

        is_secure = self.is_secure
        host = "%s:%d" % (server, self.port)
        while True:
            if (is_secure):
                connection = httplib.HTTPSConnection(host)
            else:
                connection = httplib.HTTPConnection(host)

            final_headers = merge_meta(headers, metadata);
            # add auth header
            self._add_aws_auth_header(final_headers, method, bucket, key, query_args)

            connection.request(method, path, data, final_headers)
            resp = connection.getresponse()
            if resp.status < 300 or resp.status >= 400:
                return resp
            # handle redirect
            location = resp.getheader('location')
            if not location:
                return resp
            # (close connection)
            resp.read()
            scheme, host, path, params, query, fragment \
                    = urlparse.urlparse(location)
            if scheme == "http":    is_secure = True
            elif scheme == "https": is_secure = False
            else: raise invalidURL("Not http/https: " + location)
            if query: path += "?" + query
            # retry with redirect

    def _add_aws_auth_header(self, headers, method, bucket, key, query_args):
        if not headers.has_key('Date'):
            headers['Date'] = time.strftime("%a, %d %b %Y %X GMT", time.gmtime())

        c_string = canonical_string(method, bucket, key, query_args, headers)
        headers['Authorization'] = \
            "AWS %s:%s" % (self.aws_access_key_id, encode(self.aws_secret_access_key, c_string))


class QueryStringAuthGenerator:
    # by default, expire in 1 minute
    DEFAULT_EXPIRES_IN = 60

    def __init__(self, aws_access_key_id, aws_secret_access_key, is_secure=True,
                 server=DEFAULT_HOST, port=None, calling_format=CallingFormat.SUBDOMAIN):

        if not port:
            port = PORTS_BY_SECURITY[is_secure]

        self.aws_access_key_id = aws_access_key_id
        self.aws_secret_access_key = aws_secret_access_key
        if (is_secure):
            self.protocol = 'https'
        else:
            self.protocol = 'http'

        self.is_secure = is_secure
        self.server = server
        self.port = port
        self.calling_format = calling_format
        self.__expires_in = QueryStringAuthGenerator.DEFAULT_EXPIRES_IN
        self.__expires = None

        # for backwards compatibility with older versions
        self.server_name = "%s:%s" % (self.server, self.port)

    def set_expires_in(self, expires_in):
        self.__expires_in = expires_in
        self.__expires = None

    def set_expires(self, expires):
        self.__expires = expires
        self.__expires_in = None

    def create_bucket(self, bucket, headers={}):
        return self.generate_url('PUT', bucket, '', {}, headers)

    def list_bucket(self, bucket, options={}, headers={}):
        return self.generate_url('GET', bucket, '', options, headers)

    def delete_bucket(self, bucket, headers={}):
        return self.generate_url('DELETE', bucket, '', {}, headers)

    def put(self, bucket, key, object, headers={}):
        if not isinstance(object, S3Object):
            object = S3Object(object)

        return self.generate_url(
                'PUT',
                bucket,
                key,
                {},
                merge_meta(headers, object.metadata))

    def get(self, bucket, key, headers={}):
        return self.generate_url('GET', bucket, key, {}, headers)

    def delete(self, bucket, key, headers={}):
        return self.generate_url('DELETE', bucket, key, {}, headers)

    def get_bucket_logging(self, bucket, headers={}):
        return self.generate_url('GET', bucket, '', { 'logging': None }, headers)

    def put_bucket_logging(self, bucket, logging_xml_doc, headers={}):
        return self.generate_url('PUT', bucket, '', { 'logging': None }, headers)

    def get_bucket_acl(self, bucket, headers={}):
        return self.get_acl(bucket, '', headers)

    def get_acl(self, bucket, key='', headers={}):
        return self.generate_url('GET', bucket, key, { 'acl': None }, headers)

    def put_bucket_acl(self, bucket, acl_xml_document, headers={}):
        return self.put_acl(bucket, '', acl_xml_document, headers)

    # don't really care what the doc is here.
    def put_acl(self, bucket, key, acl_xml_document, headers={}):
        return self.generate_url('PUT', bucket, key, { 'acl': None }, headers)

    def list_all_my_buckets(self, headers={}):
        return self.generate_url('GET', '', '', {}, headers)

    def make_bare_url(self, bucket, key=''):
        full_url = self.generate_url(self, bucket, key)
        return full_url[:full_url.index('?')]

    def generate_url(self, method, bucket='', key='', query_args={}, headers={}):
        expires = 0
        if self.__expires_in != None:
            expires = int(time.time() + self.__expires_in)
        elif self.__expires != None:
            expires = int(self.__expires)
        else:
            raise "Invalid expires state"

        canonical_str = canonical_string(method, bucket, key, query_args, headers, expires)
        encoded_canonical = encode(self.aws_secret_access_key, canonical_str)

        url = CallingFormat.build_url_base(self.protocol, self.server, self.port, bucket, self.calling_format)

        url += "/%s" % urllib.quote_plus(key)

        query_args['Signature'] = encoded_canonical
        query_args['Expires'] = expires
        query_args['AWSAccessKeyId'] = self.aws_access_key_id

        url += "?%s" % query_args_hash_to_string(query_args)

        return url


class S3Object:
    def __init__(self, data, metadata={}):
        self.data = data
        self.metadata = metadata

class Owner:
    def __init__(self, id='', display_name=''):
        self.id = id
        self.display_name = display_name

class ListEntry:
    def __init__(self, key='', last_modified=None, etag='', size=0, storage_class='', owner=None):
        self.key = key
        self.last_modified = last_modified
        self.etag = etag
        self.size = size
        self.storage_class = storage_class
        self.owner = owner

class CommonPrefixEntry:
    def __init(self, prefix=''):
        self.prefix = prefix

class Bucket:
    def __init__(self, name='', creation_date=''):
        self.name = name
        self.creation_date = creation_date

class Response:
    def __init__(self, http_response):
        self.http_response = http_response
        # you have to do this read, even if you don't expect a body.
        # otherwise, the next request fails.
        self.body = http_response.content
        if http_response.status_code >= 300 and self.body:
            self.message = self.body
        else:
            self.message = "%03d" % (http_response.status_code)



class ListBucketResponse(Response):
    def __init__(self, http_response):
        Response.__init__(self, http_response)
        if http_response.status_code < 300:
#        if http_response.status < 300:
            handler = ListBucketHandler()
            xml.sax.parseString(self.body, handler)
            self.entries = handler.entries
            self.common_prefixes = handler.common_prefixes
            self.name = handler.name
            self.marker = handler.marker
            self.prefix = handler.prefix
            self.is_truncated = handler.is_truncated
            self.delimiter = handler.delimiter
            self.max_keys = handler.max_keys
            self.next_marker = handler.next_marker
        else:
            self.entries = []

class ListAllMyBucketsResponse(Response):
    def __init__(self, http_response):
        Response.__init__(self, http_response)
        if http_response.status < 300: 
            handler = ListAllMyBucketsHandler()
            xml.sax.parseString(self.body, handler)
            self.entries = handler.entries
        else:
            self.entries = []

class GetResponse(Response):
    def __init__(self, http_response):
        Response.__init__(self, http_response)
        response_headers = http_response.msg   # older pythons don't have getheaders
        metadata = self.get_aws_metadata(response_headers)
        self.object = S3Object(self.body, metadata)

    def get_aws_metadata(self, headers):
        metadata = {}
        for hkey in headers.keys():
            if hkey.lower().startswith(METADATA_PREFIX):
                metadata[hkey[len(METADATA_PREFIX):]] = headers[hkey]
                del headers[hkey]

        return metadata

class LocationResponse(Response):
    def __init__(self, http_response):
        Response.__init__(self, http_response)
        if http_response.status < 300: 
            handler = LocationHandler()
            xml.sax.parseString(self.body, handler)
            self.location = handler.location

class ListBucketHandler(xml.sax.ContentHandler):
    def __init__(self):
        self.entries = []
        self.curr_entry = None
        self.curr_text = ''
        self.common_prefixes = []
        self.curr_common_prefix = None
        self.name = ''
        self.marker = ''
        self.prefix = ''
        self.is_truncated = False
        self.delimiter = ''
        self.max_keys = 0
        self.next_marker = ''
        self.is_echoed_prefix_set = False

    def startElement(self, name, attrs):
        if name == 'Contents':
            self.curr_entry = ListEntry()
        elif name == 'Owner':
            self.curr_entry.owner = Owner()
        elif name == 'CommonPrefixes':
            self.curr_common_prefix = CommonPrefixEntry()


    def endElement(self, name):
        if name == 'Contents':
            self.entries.append(self.curr_entry)
        elif name == 'CommonPrefixes':
            self.common_prefixes.append(self.curr_common_prefix)
        elif name == 'Key':
            self.curr_entry.key = self.curr_text
        elif name == 'LastModified':
            self.curr_entry.last_modified = self.curr_text
        elif name == 'ETag':
            self.curr_entry.etag = self.curr_text
        elif name == 'Size':
            self.curr_entry.size = int(self.curr_text)
        elif name == 'ID':
            self.curr_entry.owner.id = self.curr_text
        elif name == 'DisplayName':
            self.curr_entry.owner.display_name = self.curr_text
        elif name == 'StorageClass':
            self.curr_entry.storage_class = self.curr_text
        elif name == 'Name':
            self.name = self.curr_text
        elif name == 'Prefix' and self.is_echoed_prefix_set:
            self.curr_common_prefix.prefix = self.curr_text
        elif name == 'Prefix':
            self.prefix = self.curr_text
            self.is_echoed_prefix_set = True
        elif name == 'Marker':
            self.marker = self.curr_text
        elif name == 'IsTruncated':
            self.is_truncated = self.curr_text == 'true'
        elif name == 'Delimiter':
            self.delimiter = self.curr_text
        elif name == 'MaxKeys':
            self.max_keys = int(self.curr_text)
        elif name == 'NextMarker':
            self.next_marker = self.curr_text

        self.curr_text = ''

    def characters(self, content):
        self.curr_text += content


class ListAllMyBucketsHandler(xml.sax.ContentHandler):
    def __init__(self):
        self.entries = []
        self.curr_entry = None
        self.curr_text = ''

    def startElement(self, name, attrs):
        if name == 'Bucket':
            self.curr_entry = Bucket()

    def endElement(self, name):
        if name == 'Name':
            self.curr_entry.name = self.curr_text
        elif name == 'CreationDate':
            self.curr_entry.creation_date = self.curr_text
        elif name == 'Bucket':
            self.entries.append(self.curr_entry)

    def characters(self, content):
        self.curr_text = content


class LocationHandler(xml.sax.ContentHandler):
    def __init__(self):
        self.location = None
        self.state = 'init'

    def startElement(self, name, attrs):
        if self.state == 'init':
            if name == 'LocationConstraint':
                self.state = 'tag_location'
                self.location = ''
            else: self.state = 'bad'
        else: self.state = 'bad'

    def endElement(self, name):
        if self.state == 'tag_location' and name == 'LocationConstraint':
            self.state = 'done'
        else: self.state = 'bad'

    def characters(self, content):
        if self.state == 'tag_location':
            self.location += content

########NEW FILE########
__FILENAME__ = main
"""
This script is intended to be used with Google Appengine. It contains
a number of demos that illustrate the Tropo Web API for Python.
"""

from google.appengine.ext import webapp
from google.appengine.ext.webapp import util
import cgi
import logging
import tropo
import GoogleS3
from xml.dom import minidom
from google.appengine.api import urlfetch
from xml.etree import ElementTree
from setup import *



def HelloWorld(handler, t):
    """
    This is the traditional "Hello, World" function. The idiom is used throughout the API. We construct a Tropo object, and then flesh out that object by calling "action" functions (in this case, tropo.say). Then call tropo.Render, which translates the Tropo object into JSON format. Finally, we write the JSON object to the standard output, so that it will get POSTed back to the API.
    """
    t.say (["Hello, World", "How ya doing?"])
    json = t.RenderJson()
    logging.info ("HelloWorld json: %s" % json)
    handler.response.out.write(json)

def WeatherDemo(handler, t):
    """
    """
    choices = tropo.Choices("[5 digits]")

    t.ask(choices, 
              say="Please enter your 5 digit zip code.", 
              attempts=3, bargein=True, name="zip", timeout=5, voice="dave")

    t.on(event="continue", 
             next="/weather.py?uri=end",
             say="Please hold.")

    t.on(event="error",
             next="/weather.py?uri=error",
             say="Ann error occurred.")

    json = t.RenderJson()
    logging.info ("Json result: %s " % json)
    logging.info ("WeatherDemo json: %s" % json)

    handler.response.out.write(json)

def RecordDemo(handler, t):

    url = "%s/receive_recording.py" % THIS_URL
    choices_obj = tropo.Choices("", terminator="#").json
    t.record(say="Tell us about yourself", url=url, 
                 choices=choices_obj)
    json = t.RenderJson()
    logging.info ("Json result: %s " % json)
    handler.response.out.write(json)

def SMSDemo(handler, t):

    t.message("Hello World", MY_PHONE, channel='TEXT', network='SMS', timeout=5)
    json = t.RenderJson()
    logging.info ("Json result: %s " % json)
    handler.response.out.write(json)


def RecordHelloWorld(handler, t):
    """
    Demonstration of recording a message.
    """
    url = "%s/receive_recording.py" % THIS_URL
    t.startRecording(url)
    t.say ("Hello, World.")
    t.stopRecording()
    json = t.RenderJson()
    logging.info ("RecordHelloWorld json: %s" % json)
    handler.response.out.write(json)

def RedirectDemo(handler, t):
    """
    Demonstration of redirecting to another number.
    """
    # t.say ("One moment please.")
    t.redirect(SIP_PHONE)
    json = t.RenderJson()
    logging.info ("RedirectDemo json: %s" % json)
    handler.response.out.write(json)

def TransferDemo(handler, t):
    """
    Demonstration of transfering to another number
    """
    t.say ("One moment please.")
    t.transfer(MY_PHONE)
    t.say("Hi. I am a robot")
    json = t.RenderJson()
    logging.info ("TransferDemo json: %s" % json)
    handler.response.out.write(json)



def CallDemo(handler, t):
    t.call(THEIR_PHONE)
    json = t.RenderJson()
    logging.info ("CallDemo json: %s " % json)
    handler.response.out.write(json)

def ConferenceDemo(handler, t):
    t.say ("Have some of your friends launch this demo. You'll be on the world's simplest conference call.")
    t.conference("partyline", terminator="#", name="Family Meeting")
    json = t.RenderJson()
    logging.info ("ConferenceDemo json: %s " % json)
    handler.response.out.write(json)




# List of Demos
DEMOS = {
 '1' : ('Hello World', HelloWorld),
 '2' : ('Weather Demo', WeatherDemo),
 '3' : ('Record Demo', RecordDemo),
 '4' : ('SMS Demo', SMSDemo),
 '5' : ('Record Conversation Demo', RecordHelloWorld),
 '6' : ('Redirect Demo', RedirectDemo),
 '7' : ('Transfer Demo', TransferDemo),
 '8' : ('Call Demo', CallDemo),
 '9' : ('Conference Demo', ConferenceDemo)
}

class TropoDemo(webapp.RequestHandler):
    """
    This class is the entry point to the Tropo Web API for Python demos. Note that it's only method is a POST method, since this is how Tropo kicks off.
        
    A bundle of information about the call, such as who is calling, is passed in via the POST data.
    """
    def post(self):
        t = tropo.Tropo()
        t.say ("Welcome to the Tropo web API demo")

        request = "Please press"
        choices_string = ""
        choices_counter = 1
        for key in sorted(DEMOS.iterkeys()):
            if (len(choices_string) > 0):
                choices_string = "%s,%s" % (choices_string, choices_counter)
            else:
                choices_string = "%s" % (choices_counter)
            demo_name = DEMOS[key][0]
            demo = DEMOS[key][1]
            request = "%s %s for %s," % (request, key, demo_name)
            choices_counter += 1
        choices = tropo.Choices(choices_string)

        t.ask(choices, say=request, attempts=3, bargein=True, name="zip", timeout=5, voice="dave")

        t.on(event="continue", 
                     next="/demo_continue.py",
                     say="Please hold.")

        t.on(event="error",
                     next="/demo_continue.py",
                     say="An error occurred.")

        json = t.RenderJson()
        logging.info ("Json result: %s " % json)
        self.response.out.write(json)


class TropoDemoContinue(webapp.RequestHandler):
    """
    This class implements all the top-level demo functions. Data is POSTed to the application, to start tings off. After retrieving the result value, which is a digit indicating the user's choice of demo function, the POST method dispatches to the chosen demo.
    """
    def post (self):
        json = self.request.body
        logging.info ("json: %s" % json)
        t = tropo.Tropo()
        result = tropo.Result(json)
        choice = result.getValue()
        logging.info ("Choice of demo is: %s" % choice)

        for key in DEMOS:
            if (choice == key):
                demo_name = DEMOS[key][0]
                demo = DEMOS[key][1]
                demo(self, t)
                break
    
class Weather(webapp.RequestHandler):
    def post (self):
        json = self.request.body
        logging.info ("json: %s" % json)

        uri = self.request.get ('uri')
        logging.info ("uri: %s" % uri)

        t = tropo.Tropo()

	if (uri == "error"):
	   t.say ("Oops. There was some kind of error")
           json = t.RenderJson()
           self.response.out.write(json)
	   return

        result = tropo.Result(json);
        zip = result.getValue()
        google_weather_url = "%s?weather=%s&hl=en" % (GOOGLE_WEATHER_API_URL, zip)
        resp = urlfetch.fetch(google_weather_url)

        logging.info ("weather url: %s " % google_weather_url)
        if (resp.status_code == 200):
            xml = resp.content
            logging.info ("weather xml: %s " % xml)
            doc = ElementTree.fromstring(xml)            
            logging.info ("doc: %s " % doc)
            condition = doc.find("weather/current_conditions/condition").attrib['data']
            temp_f  = doc.find("weather/current_conditions/temp_f").attrib['data']
            wind_condition = doc.find("weather/current_conditions/wind_condition").attrib['data']
            city = doc.find("weather/forecast_information/city").attrib['data']
            logging.info ("condition: %s temp_f: %s wind_condition: %s city: %s" % (condition, temp_f, wind_condition, city))
            t = tropo.Tropo()
            # condition: Partly Cloudy temp_f: 73 wind_condition: Wind: NW at 10 mph city: Portsmouth, NH
            temp = "%s degrees" % temp_f
            wind = self.english_expand (wind_condition)
            t.say("Current city is %s . Weather conditions are %s. Temperature is %s. %s ." % (city, condition, temp, wind))        
            json = t.RenderJson()

            self.response.out.write(json)


# Wind: N at 0 mph

    def english_expand(self, expr):
        logging.info ("expr is : %s" % expr)
        expr = expr.replace("Wind: NW", "Wind is from the North West")
        expr = expr.replace("Wind: NE", "Wind is from the North East")
        expr = expr.replace("Wind: N", "Wind is from the North")
        expr = expr.replace("Wind: SW", "Wind is from the South West")
        expr = expr.replace("Wind: SE", "Wind is from the South East")
        expr = expr.replace("Wind: S", "Wind is from the South")
        expr = expr.replace("mph", "miles per hour")
        return expr


class ReceiveRecording(webapp.RequestHandler):
    def post(self):
        logging.info ("I just received a post recording")
#        wav = self.request.body
        wav = self.request.get ('filename')
        logging.info ("Just got the wav as %s" % wav)
        self.put_in_s3(wav)
        logging.info ("I just put the wav in s3")

    def put_in_s3 (self, wav):

        conn = GoogleS3.AWSAuthConnection(AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY)
        key_name = "testing.wav"
        logging.info ("Putting content in %s in %s bucket" % (key_name, S3_BUCKET_NAME))
        responsedict={}
        logging.info ("really putting stuff in %s %s" % (S3_BUCKET_NAME, key_name))
        audio_type = 'audio/wav'
        
        response = conn.put(
            S3_BUCKET_NAME,
            key_name,
            GoogleS3.S3Object(wav),
        {'Content-Type' : audio_type, 
         'x-amz-acl' : 'public-read'})
        responsedict["response"] = response
        responsedict["url"] = "%s/%s/%s" % (AMAZON_S3_URL, S3_BUCKET_NAME, key_name)
        return responsedict



class CallWorld(webapp.RequestHandler):
    def post(self):
        t = tropo.Tropo()
        t.call(MY_PHONE, channel='TEXT', network='SMS', answerOnMedia='True')
        t.say ("Wish you were here")
        json = t.RenderJson()
        logging.info ("Json result: %s " % json)
        self.response.out.write(json)



class MainHandler(webapp.RequestHandler):
    def get(self):
        self.response.out.write('Hello world!')


def main():
    application = webapp.WSGIApplication([('/', MainHandler),
                                          ('/hello_tropo.py', TropoDemo),
                                          ('/weather.py', Weather),
                                          ('/receive_recording.py', ReceiveRecording),
                                          ('/demo_continue.py', TropoDemoContinue),
#                                          ('/tropo_web_api.html', ShowDoc)

  ],
                                         debug=True)
    util.run_wsgi_app(application)

if __name__ == '__main__':
    main()

########NEW FILE########
__FILENAME__ = gh-12-test_voice
# tests fix of gh-12 . Need a way to set the default voice
# for a Tropo object.
# added a new method "setVoice" on the Tropo object

# These examples show precdence of setVoice vs using "voice="..." in 
# the method call.

# Sample application using the itty-bitty python web framework from:
#  http://github.com/toastdriven/itty

from itty import *
from tropo import Tropo, Session, TropoAction, Choices

@post('/index.json')
def index(request):
    s = Session(request.body)
    t = Tropo()
    t.setVoice('dave')
    # we use what has been set in Tropo object
    t.say(['hello world!'])
    # we use what is set in the method call
    t.say(['hello world!'], voice="allison")

    # we use the voice that has been set in Tropo object
    choices = Choices("[5 digits]").obj
    t.ask(choices,
              say="Please enter your 5 digit zip code.",
              attempts=3, bargein=True, name="zip", timeout=5)

    # we use the voice passed in the method call.
    choices = Choices("[5 digits]").obj
    t.ask(choices,
              say="Please enter your 5 digit zip code.",
              attempts=3, bargein=True, name="zip", timeout=5, voice="allison")


    json = t.RenderJson()
    print json
    return json


run_itty()


########NEW FILE########
__FILENAME__ = gh-14.test_call
# tests fix of gh-14 for "from" parameter in the "call" function. 
# Proposed convention is to use "_from" as the parameter
# so as not to conflict with "from" Python reserved word.

# _from arg works

# Invoke using a token

# Sample application using the itty-bitty python web framework from:
#  http://github.com/toastdriven/itty

from itty import *
from tropo import Tropo, Session

TO_NUMBER = '1xxxxxxxxxx'
FROM_NUMBER = '1yyyyyyyyyy'


@post('/index.json')
def index(request):
    s = Session(request.body)
    t = Tropo()
    t.call(to='tel:+' + TO_NUMBER, _from='tel:+' + FROM_NUMBER)
    t.say('This is your mother. Did you brush your teeth today?')
    json = t.RenderJson()
    print json
    return json


run_itty()


########NEW FILE########
__FILENAME__ = gh-14.test_message
# tests fix of gh-14 for "_from" parameter in the "message" function. 
# Proposed convention is to use "_from" as the parameter
# so as not to conflict with "from" Python reserved word.

# _from arg works

# Invoke using a token

# Sample application using the itty-bitty python web framework from:
#  http://github.com/toastdriven/itty

from itty import *
from tropo import Tropo, Session

TO_NUMBER = '1xxxxxxxxxx'
FROM_NUMBER = '1yyyyyyyyyy'


@post('/index.json')
def index(request):
        t = Tropo()
        t.message("Hello World", TO_NUMBER, channel='VOICE', _from='tel:+' + FROM_NUMBER)
	json = t.RenderJson()
	print json
	return json
#retest


run_itty()


########NEW FILE########
__FILENAME__ = gh-14.test_say
# tests fix of gh-14 for "_as" parameter in the "say" function. 
# Proposed convention is to use "_from" as the parameter
# so as not to conflict with "from" Python reserved word.




# Sample application using the itty-bitty python web framework from:
#  http://github.com/toastdriven/itty

from itty import *
from tropo import Tropo, Session

@post('/index.json')
def index(request):
    s = Session(request.body)
    t = Tropo()
    t.say('12345', _as='DIGITS', voice='dave')
    json = t.RenderJson()
    print json
    return json


run_itty()


########NEW FILE########
__FILENAME__ = gh-14.test_transfer
# tests fix of gh-14 for "from" parameter in the "transfer" function. 
# Proposed convention is to use "_from" as the parameter
# so as not to conflict with "from" Python reserved word.

# _from arg works
# _from arg works with straight json

# Invoke by calling up app access number

# Sample application using the itty-bitty python web framework from:
#  http://github.com/toastdriven/itty

from itty import *
from tropo import Tropo, Session

TO_NUMBER = '1xxxxxxxxxx'
FROM_NUMBER = '1yyyyyyyyyy'


@post('/index.json')
def index(request):
    s = Session(request.body)
    t = Tropo()
    t.say ("One moment please.")
    t.transfer(TO_NUMBER, _from="tel:+" + FROM_NUMBER)
    t.say("Hi. I am a robot")
    json = t.RenderJson()
    print json
    return json


run_itty()


########NEW FILE########
__FILENAME__ = gh-14_test
# tests fix of gh-14. Proposed convention is to use "_as" as
# the attribute in "say" function, so as not to conflict with "as"
# Python reserved word.

# Sample application using the itty-bitty python web framework from:
#  http://github.com/toastdriven/itty

from itty import *
from tropo import Tropo, Session

@post('/index.json')
def index(request):
    s = Session(request.body)
    t = Tropo()
    t.say('12345', _as='DIGITS', voice='allison')
    json = t.RenderJson()
    print json
    return json

run_itty()

########NEW FILE########
__FILENAME__ = gh-17.test
from itty import *
from tropo import Tropo, Result

# Fixes issue gh-17 getValue() should work with "value" property
# and not "interpretation"

@post('/index.json')
def index(request):
	t = Tropo()
	t.ask(choices = "yes(yes,y,1), no(no,n,2)", timeout=60, name="reminder", say = "Hey, did you remember to take your pills?")	
	t.on(event = "continue", next ="/continue")
	t.on(event = "incomplete", next ="/incomplete")
	json = t.RenderJson()
	print json
	return json

@post("/continue")
def index(request):
	r = Result(request.body)
	t = Tropo()

	answer = r.getValue()

	t.say("You said " + str(answer))

	if answer == "yes" :
		t.say("Ok, just checkin.")
	else :
		t.say("What are you waiting for?")

	json = t.RenderJson()
	print json
	return json

@post("/incomplete")
def index(request):
	t = Tropo()
	t.say("Sorry, that wasn't on of the options.")
	json = t.RenderJson()
	print json
	return json

run_itty()

########NEW FILE########
__FILENAME__ = gh-20-test_ask
# tests fix of gh-20 . Extracting out of Result

# Added a new method on the Result object, called getInterpretation()


# Sample application using the itty-bitty python web framework from:
#  http://github.com/toastdriven/itty

from itty import *
from tropo import Tropo, Session, Result


@post('/index.json')
def index(request):

	t = Tropo()

	t.ask(choices = "yes(yes,y,1), no(no,n,2)", timeout = 15, name = "directory", minConfidence = 1, attempts = 3, say = "Are you trying to reach the sales department??")

	t.on(event = "continue", next ="/continue")

        json = t.RenderJson()

        print json
	return json

@post("/continue")
def index(request):

	r = Result(request.body)        
        print "Result : %s" % r

	t = Tropo()

	answer = r.getInterpretation()
	value = r.getValue()

	t.say("You said " + answer + ", which is a " + value)

        json = t.RenderJson()
        print json
	return json

run_itty()

########NEW FILE########
__FILENAME__ = gh-21.choices
# tests fix of gh-21 . Sorting out syntax of choices for ask.

# Fixed an error in the way the Ask class init function was
# taking apart the choices argument passed to it.

# Then, I corrected the original example provided for gh-21.
# Correct way to provide "choices" argument to "ask" is shown in 
# the example below.


# Sample application using the itty-bitty python web framework from:
#  http://github.com/toastdriven/itty

from itty import *
from tropo import Tropo, Session, Result, Choices


@post('/index.json')
def index(request):

	t = Tropo()

        choices = Choices("[4-5 DIGITS]", mode="dtmf", terminator = "#")
	t.ask(choices, timeout=15, name="digit", say = "What's your four or five digit pin? Press pound when finished.")

	t.on(event = "continue", next ="/continue")

        json = t.RenderJson()

        print json
	return json

@post("/continue")
def index(request):

	r = Result(request.body)        
        print "Result : %s" % r
#        dump(r)
	t = Tropo()

	answer = r.getInterpretation()

	t.say("You said ")
	t.say (answer, _as="DIGITS")

        json = t.RenderJson()
        print json
	return json

run_itty()


########NEW FILE########
__FILENAME__ = gh-22.transfer
# tests fix of gh-22 . headers parameter for transfer()

# Fixes an error whereby we weren't passing 
# the "headers" parameter to transfer()

# Sample below shows how to pass in headers.


# Sample application using the itty-bitty python web framework from:
#  http://github.com/toastdriven/itty


from itty import *
from tropo-webapi-python/tropo import Tropo, Session


#TO_NUMBER = '1xxxxxxxxxx'
TO_NUMBER = '16039570051'


@post('/index.json')
def index(request):

  s = Session(request.body)
  t = Tropo()

  t.say("Hello. , , , Transferring")
#  t.transfer(to="sip:9991489767@sip.tropo.com", headers={"x-callername":"Kevin Bond"})

  t.transfer(TO_NUMBER, headers={"x-callername":"Kevin Bond"})

  json = t.RenderJson()
  print json
  return json


run_itty()



########NEW FILE########
__FILENAME__ = gh-23.ask_timeout
# tests example clarifying gh-23 . How to use timeout, and nomatch parameters
# in "say" within "ask"


from itty import *
from tropo import Tropo, Session, Result


@post("/index.json")
def index (request):
    t = Tropo()
    t.ask(choices = "[4 DIGITs]", 
          timeout=5,
          bargein="true",
          name="year",
          attempts=3,
          required="true",
          say = [{'event':'timeout',
                  'value':"Sorry, I did not hear anything"},
                 {'event':'nomatch:1',
                  'value':"Don't think that was a year."},
                 {'event':'nomatch:2',
                  'value':"Nope, still not a year."},
                 {'value': "What is your birth year?"}
                 ])   

    json = t.RenderJson()
    print json
    return json



# @post("/index.json")
def index_straight_json (request):
    json = """{
    "tropo":[
      {
         "ask":{
            "attempts":3,
            "say":[
               {
                  "value":"Sorry, I did not hear anything.",
                  "event":"timeout"
               },
               {
                  "value":"Don't think that was a year. ",
                  "event":"nomatch:1"
               },
               {
                  "value":"Nope, still not a year.",
                  "event":"nomatch:2"
               },
               {
                  "value":"What is your birth year?"
               }
            ],
            "choices":{
               "value":"[4 DIGITS]"
            },
            "bargein":true,
            "timeout":5,
            "name":"year",
            "required":true
         }
      }
   ]

}
"""
    print json
    return json








run_itty()

########NEW FILE########
__FILENAME__ = gh-5.hello_cgi
#!/usr/bin/python

# Hello, World CGI script.
# Addresses gh-5.
# Steps:
# 1. edit Apache httpd.conf file
#  Alias /tropo/ "/path/to/examples/"
# <Directory "/path/to/examples">
#    Options +ExecCGI
#    SetHandler cgi-script
#    Allow from all
#    AllowOverride All
# </Directory>
#   2. Create Web API app in Tropo and assign it the url 
#        http://my_webserver.com/tropo/g-5.hello_cgi.py
#   3. Place this file in examples folder and chmod it executable
#   4. Dial up Tropo app, and hear "Hello, World ..."

import cgi
from tropo import Tropo

def hello():
    t = Tropo()
    t.say(['hello world! I am a C G I script.'])
    json = t.RenderJson()
    print json
    return json



print "Content-type: text/json"
print
print 

hello()


########NEW FILE########
__FILENAME__ = itty_hello_world
#!/usr/bin/env python

# Sample application using the itty-bitty python web framework from:
#  http://github.com/toastdriven/itty

from itty import *
from tropo import Tropo, Session

@post('/index.json')
def index(request):
    s = Session(request.body)
    t = Tropo()
    t.say(['hello world!', 'how are you doing?'])
    return t.RenderJson()

run_itty(server='wsgiref', host='0.0.0.0', port=8888)


########NEW FILE########
__FILENAME__ = itty_session_api
#!/usr/bin/env python
"""
Hello world script for Session API ( https://www.tropo.com/docs/webapi/sessionapi.htm )

Upon launch, it will trigger a message to be sent via Jabber to the addess specified in
'number'.
"""

# Sample application using the itty-bitty python web framework from:
#  http://github.com/toastdriven/itty

from itty import *
from tropo import Tropo, Session
from urllib import urlencode
from urllib2 import urlopen

@post('/index.json')
def index(request):
    session = Session(request.body)
    t = Tropo()
    t.call(to=session.parameters['numberToDial'], network='JABBER')
    t.say(session.parameters['message'])
    return t.RenderJson()


base_url = 'http://api.tropo.com/1.0/sessions'
token = 'xxxxxxxxxx'		# Insert your token here
action = 'create'
number = 'username@domain'	# change to the Jabber ID to which you want to send the message
message = 'hello from the session API!'

params = urlencode([('action', action), ('token', token), ('numberToDial', number), ('message', message)])
data = urlopen('%s?%s' % (base_url, params)).read()

run_itty(server='wsgiref', host='0.0.0.0', port=8888)


########NEW FILE########
__FILENAME__ = record_test
from itty import *
from tropo import Tropo, Session, Result

@post('/index')
def index(request):

    t = Tropo()
    VOICE = 'Grace' 

    t.record(name='voicemail.mp3', say='Your call is important. Please leave a short message after the tone: ', url = 'http://www.example.com', beep = True, format = 'audio/mp3', voice = VOICE) 

    return t.RenderJson()
	
run_itty(server='wsgiref', port=8888)
########NEW FILE########
__FILENAME__ = test
#!/usr/bin/env python


try:
    import cjson as jsonlib
    jsonlib.dumps = jsonlib.encode
    jsonlib.loads = jsonlib.decode
except ImportError:
    try:
        from django.utils import simplejson as jsonlib
    except ImportError:
        try:
            import simplejson as jsonlib
        except ImportError:
            import json as jsonlib

import unittest 
import sys
sys.path = ['..'] + sys.path
from tropo import Choices, Say, Tropo


class TestTropoPython(unittest.TestCase):        
    """
    Class implementing a set of unit tests for TropoPython.
    """
    TO = "8005551212"
    MY_PHONE = "6021234567"
    RECORDING_URL = "/receive_recording.py"
    ID = "foo"
    S3_URL = "http://s3.amazonaws.com/xxx_s3_bucket/hello.wav"


    def test_ask(self):
        """
        Test the "ask" Tropo class method.
        """
        tropo = Tropo()
        tropo.ask("[5 digits]",
                  say = Say("Please enter a 5 digit zip code").json)
        rendered = tropo.RenderJson()
        pretty_rendered = tropo.RenderJson(pretty=True)
        print "===============test_ask================="
        print "render json: %s" % pretty_rendered
        rendered_obj = jsonlib.loads(rendered)
        wanted_json = '{"tropo": [{"ask": {"say": {"value": "Please enter a 5 digit zip code"}, "choices": {"value": "[5 digits]"}}}]}'
        wanted_obj = jsonlib.loads(wanted_json)
        # print "test_ask: %s" % tropo.RenderJson()
        self.assertEqual(rendered_obj, wanted_obj)

    def test_call(self):
        """
        Test the "call" Tropo class method.
        """

        tropo = Tropo()
        tropo.call(self.MY_PHONE, channel='TEXT', network='SMS')
        tropo.say ("Wish you were here")
        rendered = tropo.RenderJson()
        pretty_rendered = tropo.RenderJson(pretty=True)
        print ("============test_call=============")
        print "render json: %s" % pretty_rendered

        rendered_obj = jsonlib.loads(rendered)
        wanted_json = '{"tropo": [{"call": {"to": "%s", "network": "SMS", "channel": "TEXT"}}, {"say": {"value": "Wish you were here"}}]}' % self.MY_PHONE
        wanted_obj = jsonlib.loads(wanted_json)
        # print "test_call: %s" % tropo.RenderJson()
        self.assertEqual(rendered_obj, wanted_obj)

    def test_conference(self):
        """
        Test the "conference" Tropo class method.
        """

        tropo = Tropo()
        tropo.conference(self.ID, playTones=True, mute=False,
                   name="Staff Meeting")
        rendered = tropo.RenderJson()
        pretty_rendered = tropo.RenderJson(pretty=True)
        print "===============test_conference================="
        print "render json: %s" % pretty_rendered

        rendered_obj = jsonlib.loads(rendered)
        wanted_json = '{"tropo": [{"conference": {"playTones": true, "mute": false, "name": "Staff Meeting", "id": "foo"}}]}'
        print "wanted_json: %s" % wanted_json
        wanted_obj = jsonlib.loads(wanted_json)
        # print "test_conference: %s" % tropo.RenderJson()
        self.assertEqual(rendered_obj, wanted_obj)

    def test_hangup(self):
        """
        Test the "hangup" Tropo class method.
        """

        tropo = Tropo()
        tropo.hangup()
        rendered = tropo.RenderJson()
        pretty_rendered = tropo.RenderJson(pretty=True)
        print "===============test_hangup================="
        print "render json: %s" % pretty_rendered

        # print "test_hangup: %s" % tropo.RenderJson()
        rendered_obj = jsonlib.loads(rendered)
        wanted_json = '{"tropo": [{"hangup": {}}]}'
        wanted_obj = jsonlib.loads(wanted_json)
        self.assertEqual(rendered_obj, wanted_obj)

    def test_message(self):
        """
        Test the "message" Tropo class method.
        """

        tropo = Tropo()
        tropo.message("Hello World", self.MY_PHONE, channel='TEXT', network='SMS', timeout=5)
        rendered = tropo.RenderJson()
        pretty_rendered = tropo.RenderJson(pretty=True)
        print "===============test_message================="
        print "render json: %s" % pretty_rendered

        # print "test_message: %s" % tropo.RenderJson()
        rendered_obj = jsonlib.loads(rendered)
        wanted_json = ' {"tropo": [{"message": {"to": "%s", "say": {"value": "Hello World"}, "network": "SMS", "timeout": 5, "channel": "TEXT"}}]}' % self.MY_PHONE
        wanted_obj = jsonlib.loads(wanted_json)
        self.assertEqual(rendered_obj, wanted_obj)

    def test_on(self):
        """
        Test the "on" Tropo class method.
        """

        tropo = Tropo()

        tropo.on(event="continue", 
             next="/weather.py?uri=end",
             say="Please hold.")
        rendered = tropo.RenderJson()
        pretty_rendered = tropo.RenderJson(pretty=True)
        print "===============test_on================="
        print "render json: %s" % pretty_rendered

        # print "test_on: %s" % tropo.RenderJson()
        rendered_obj = jsonlib.loads(rendered)
        wanted_json = ' {"tropo": [{"on": {"say": {"value": "Please hold."}, "event": "continue", "next": "/weather.py?uri=end"}}]}'
        wanted_obj = jsonlib.loads(wanted_json)
        self.assertEqual(rendered_obj, wanted_obj)

    def test_record(self):
        """
        Test the "record" Tropo class method.
        """

        tropo = Tropo()
        url = "/receive_recording.py"
        choices_obj = Choices("", terminator="#").json
        tropo.record(say="Tell us about yourself", url=url, 
                     choices=choices_obj)
        rendered = tropo.RenderJson()
        pretty_rendered = tropo.RenderJson(pretty=True)
        print "===============test_record================="
        print "render json: %s" % pretty_rendered

        # print "test_record: %s" % tropo.RenderJson()
        rendered_obj = jsonlib.loads(rendered)
        wanted_json = ' {"tropo": [{"record": {"url": "/receive_recording.py", "say": {"value": "Tell us about yourself"}, "choices": {"terminator": "#", "value": ""}}}]}'
        wanted_obj = jsonlib.loads(wanted_json)
        self.assertEqual(rendered_obj, wanted_obj)

    def test_redirect(self):
        """
        Test the "redirect" Tropo class method.
        """

        tropo = Tropo()
        tropo.redirect(self.MY_PHONE)
        rendered = tropo.RenderJson()
        pretty_rendered = tropo.RenderJson(pretty=True)
        print "===============test_redirect================="
        print "render json: %s" % pretty_rendered

        print "Wanted_Json %s" % tropo.RenderJson()
        rendered_obj = jsonlib.loads(rendered)
        wanted_json = '{"tropo": [{"redirect": {"to": "%s"}}]}' % self.MY_PHONE
        wanted_obj = jsonlib.loads(wanted_json)
        # print "test_redirect: %s" % tropo.RenderJson()
        self.assertEqual(rendered_obj, wanted_obj)

    def test_reject(self):
        """
        Test the "reject" Tropo class method.
        """

        tropo = Tropo()
        tropo.reject()
        rendered = tropo.RenderJson()
        pretty_rendered = tropo.RenderJson(pretty=True)
        print "===============test_reject================="
        print "render json: %s" % pretty_rendered

        print "Want %s" % tropo.RenderJson()
        rendered_obj = jsonlib.loads(rendered)
        wanted_json = '{"tropo": [{"reject": {}}]}'
        wanted_obj = jsonlib.loads(wanted_json)
        # print "test_reject: %s" % tropo.RenderJson()
        self.assertEqual(rendered_obj, wanted_obj)

    def test_say(self):
        """
        Test the "say" Tropo class method.
        """

        tropo = Tropo()
        tropo.say("Hello, World")
        rendered = tropo.RenderJson()
        pretty_rendered = tropo.RenderJson(pretty=True)
        print "===============test_say================="
        print "render json: %s" % pretty_rendered

        # print "test_say: %s" % tropo.RenderJson()
        rendered_obj = jsonlib.loads(rendered)
        wanted_json = '{"tropo": [{"say": {"value": "Hello, World"}}]}'
        wanted_obj = jsonlib.loads(wanted_json)
        self.assertEqual(rendered_obj, wanted_obj)

    def test_list_say(self):
        """
        Test the "say" Tropo class method, when a list of Strings is passed to it.
        """

        tropo = Tropo()
        tropo.say(["Hello, World", "How ya doing?"])
        rendered = tropo.RenderJson()
        pretty_rendered = tropo.RenderJson(pretty=True)
        print "===============test_list_say================="
        print "render json: %s" % pretty_rendered

        # print "test_say: %s" % tropo.RenderJson()
        rendered_obj = jsonlib.loads(rendered)
        wanted_json = '{"tropo": [{"say": [{"value": "Hello, World"}, {"value": "How ya doing?"}]}]}'
        wanted_obj = jsonlib.loads(wanted_json)
        self.assertEqual(rendered_obj, wanted_obj)

    def test_startRecording(self):
        """
        Test the "startRecording" Tropo class method.
        """

        tropo = Tropo()
        tropo.startRecording(self.RECORDING_URL)
        rendered = tropo.RenderJson()
        pretty_rendered = tropo.RenderJson(pretty=True)
        print "===============test_startRecording================="
        print "render json: %s" % pretty_rendered

        # print "test_startRecording: %s" % tropo.RenderJson()
        rendered_obj = jsonlib.loads(rendered)
        wanted_json = '{"tropo": [{"startRecording": {"url": "/receive_recording.py"}}]}'
        wanted_obj = jsonlib.loads(wanted_json)
        self.assertEqual(rendered_obj, wanted_obj)

    def test_stopRecording(self):
        """
        Test the "stopRecording" Tropo class method.
        """

        tropo = Tropo()
        tropo.stopRecording()
        rendered = tropo.RenderJson()
        pretty_rendered = tropo.RenderJson(pretty=True)
        print "===============test_stopRecording================="
        print "render json: %s" % pretty_rendered

        # print "test_stopRecording: %s" % tropo.RenderJson()
        rendered_obj = jsonlib.loads(rendered)
        wanted_json = ' {"tropo": [{"stopRecording": {}}]}'
        wanted_obj = jsonlib.loads(wanted_json)
        self.assertEqual(rendered_obj, wanted_obj)

    def test_transfer(self):
        """
        Test the "transfer" Tropo class method.
        """

        tropo = Tropo()
        tropo.say ("One moment please.")
        tropo.transfer(self.MY_PHONE)
        tropo.say("Hi. I am a robot")
        rendered = tropo.RenderJson()
        pretty_rendered = tropo.RenderJson(pretty=True)
        print "===============test_transfer================="
        print "render json: %s" % pretty_rendered

        # print "test_transfer: %s" % tropo.RenderJson()
        rendered_obj = jsonlib.loads(rendered)
        wanted_json = '{"tropo": [{"say": {"value": "One moment please."}}, {"transfer": {"to": "6021234567"}}, {"say": {"value": "Hi. I am a robot"}}]}'
        wanted_obj = jsonlib.loads(wanted_json)
        self.assertEqual(rendered_obj, wanted_obj)


if __name__ == '__main__':
    """
    Unit tests.
    """
    if (0):
        TO = "8005551212"

        ID = "foo"
        URL = "http://s3.amazonaws.com/xxx_s3_bucket/hello.wav"



        tropo = Tropo()

        tropo.ask("[5 digits]",
                  say = Say("Please enter a 5 digit zip code").json)


        tropo.call (TO)
        tropo.conference(ID)
        tropo.hangup()
        tropo.message ("Hello, World", TO)
        tropo.on(event="continue", 
             next="http://example.com/weather.py",
             say="Please hold.")

        tropo.record(say="Please say something for posterity", 
                     url=URL, 
                     choices = Choices("", terminator="#").json)
        tropo.redirect(ID)
        tropo.reject(ID)
        tropo.startRecording(URL)
        tropo.stopRecording()
        tropo.transfer(TO)

        tropo.message("Hello, World",
                      TO, 
                      channel='TEXT', 
                      network='SMS')

    else:
        unittest.main()



########NEW FILE########
__FILENAME__ = test1
import sys
sys.path = ['..'] + sys.path
from tropo import Choices, MachineDetection, JoinPrompt, LeavePrompt, On, Ask, Say, Tropo

t = Tropo()

#CPA
mc = MachineDetection(introduction="THis is a CPA test", voice="Victor").json
t.call("+14071234321", machineDetection=mc)

#CPA with Boolean value which will detect CPA with 30 seconds of silence. 
t.call("+14071234321", machineDetection=True)


#Conference with join/leave prompts
jp = JoinPrompt(value="Someone just joined the conference", voice="Victor").json
lp = LeavePrompt(value="Someone just left the conference", voice="Victor").json
t.conference(id="1234", joinPrompt=jp, leavePrompt=lp)


whisper = {}

c = Choices(value="1", mode="dtmf")
ask = Ask(say="Press 1 to accept this call", choices=c).json
whisper["ask"] = ask

say = Say("You are now being connected to the call").json
whisper["say"] = say

say1 = Say("http://www.phono.com/audio/holdmusic.mp3").json
whisper["ring"] = say1

t.transfer(to="+14071234321", on=whisper)
t.on(event="incomplete", say="You are now being disconnected. Goodbye")

print t.RenderJson()


########NEW FILE########
__FILENAME__ = tropoTestMachineDetection
from itty import *
from tropo import Tropo, Result, MachineDetection

@post('/index.json')
def index(request):

  t = Tropo()

  mc = MachineDetection(introduction="This is a test. Please hold while I determine if you are a Machine or Human. Processing. Finished. THank you for your patience.", voice="Victor").json
  t.call(to="+14071234321", machineDetection=mc)
  
  t.on(event="continue", next="/continue.json")

  return t.RenderJson()

@post("/continue.json")
def index(request):

  r = Result(request.body)
  t = Tropo()

  userType = r.getUserType()

  t.say("You are a " + userType)

  return t.RenderJson()

run_itty(server='wsgiref', host='0.0.0.0',   port=8888)
########NEW FILE########
__FILENAME__ = tropo
"""
The TropoPython module. This module implements a set of classes and methods for manipulating the Voxeo Tropo WebAPI.

Usage:

----
from tropo import Tropo

tropo = Tropo()
tropo.say("Hello, World")
json = tropo.RenderJson()
----

You can write this JSON back to standard output to get Tropo to perform
the action. For example, on Google Appengine you might write something like:

handler.response.out.write(json)

Much of the time, a you will interact with Tropo by  examining the Result
object and communicating back to Tropo via the Tropo class methods, such
as "say". In some cases, you'll want to build a class object directly such as in :

    choices = tropo.Choices("[5 digits]").obj

    tropo.ask(choices,
              say="Please enter your 5 digit zip code.",
              attempts=3, bargein=True, name="zip", timeout=5, voice="dave")
    ...

NOTE: This module requires python 2.5 or higher.

"""

try:
    import cjson as jsonlib
    jsonlib.dumps = jsonlib.encode
    jsonlib.loads = jsonlib.decode
except ImportError:
    try:
        from django.utils import simplejson as jsonlib
    except ImportError:
        try:
            import simplejson as jsonlib
        except ImportError:
            import json as jsonlib

class TropoAction(object):
    """
    Class representing the base Tropo action.
    Two properties are provided in order to avoid defining the same attributes for every action.
    """
    @property
    def json(self):
        return self._dict

    @property
    def obj(self):
        return {self.action: self._dict}

class Ask(TropoAction):
    """
    Class representing the "ask" Tropo action. Builds an "ask" JSON object.
    Class constructor arg: choices, a Choices object
    Convenience function: Tropo.ask()
    Class constructor options: attempts, bargein, choices, minConfidence, name, recognizer, required, say, timeout, voice

    Request information from the caller and wait for a response.
    (See https://www.tropo.com/docs/webapi/ask.htm)

        { "ask": {
            "attempts": Integer,
            "allowSiganls": String or Array,
            "bargein": Boolean,
            "choices": Object, #Required
            "interdigitTimeout": Integer,
            "minConfidence": Integer,
            "name": String,
            "recognizer": String,
            "required": Boolean,
            "say": Object,
            "sensitivity": Integer,
            "speechCompleteTimeout": Integer,
            "speechIncompleteTimeout": Integer,
            "timeout": Float,
            "voice": String,
             
            ,
             } }

    """
    action = 'ask'
    options_array = ['attempts', 'allowSiganls', 'bargein', 'choices', 'interdigitTimeout', 'minConfidence', 'name', 'recognizer', 'required', 'say', 'sensitivity', 'speechCompleteTimeout', 'speechIncompleteTimeout', 'timeout', 'voice']

    def __init__(self, choices, **options):
        self._dict = {}
        if (isinstance(choices, basestring)):
            self._dict['choices'] = Choices(choices).json
        else:
#            self._dict['choices'] = choices['choices']
            self._dict['choices'] = choices.json
        for opt in self.options_array:
            if opt in options:
                if ((opt == 'say') and (isinstance(options['say'], basestring))):
                    self._dict['say'] = Say(options['say']).json
                else:
                    self._dict[opt] = options[opt]

class Call(TropoAction):
    """
    Class representing the "call" Tropo action. Builds a "call" JSON object.
    Class constructor arg: to, a String
    Class constructor options: answerOnMedia, channel, from, headers, name, network, recording, required, timeout, machineDetection
    Convenience function: Tropo.call()

    (See https://www.tropo.com/docswebapi/call.htm)

    { "call": {
        "to": String or Array,#Required
        "answerOnMedia": Boolean,
        "allowSignals": String or Array
        "channel": string,
        "from": string,
        "headers": Object,
        "name": String,
        "network": String,
        "recording": Array or Object,
        "required": Boolean,
        "timeout": Float.
        "machineDetection: Boolean or Object" } }
    """
    action = 'call'
    options_array = ['answerOnMedia', 'allowSignals', 'channel', '_from', 'headers', 'name', 'network', 'recording', 'required', 'timeout', 'machineDetection']

    def __init__(self, to, **options):
        self._dict = {'to': to}
        for opt in self.options_array:
            if opt in options:
                if (opt == "_from"):
                    self._dict['from'] = options[opt]
                else:
                    self._dict[opt] = options[opt]

                

class Choices(TropoAction):
    """
    Class representing choice made by a user. Builds a "choices" JSON object.
    Class constructor options: terminator, mode

    (See https://www.tropo.com/docs/webapi/ask.htm)
    """
    action = 'choices'
    options_array = ['terminator', 'mode']

    def __init__(self, value, **options):
        self._dict = {'value': value}
        for opt in self.options_array:
            if opt in options:
                self._dict[opt] = options[opt]

class Conference(TropoAction):
    """
    Class representing the "conference" Tropo action. Builds a "conference" JSON object.
    Class constructor arg: id, a String
    Convenience function: Tropo.conference()
    Class constructor options: mute, name, playTones, required, terminator

    (See https://www.tropo.com/docs/webapi/conference.htm)

    { "conference": {
        "id": String,#Required
        "allowSignals": String or Array,
        "interdigitTimeout":Integer,
        "mute": Boolean,
        "name": String,
        "playTones": Boolean,
        "required": Boolean,
        "terminator": String,
        "joinPrompt": Object,
        "leavePrompt": Object } }
    """
    action = 'conference'
    options_array = ['allowSignals', 'interdigitTimeout', 'mute', 'name', 'playTones', 'required', 'terminator', 'joinPrompt', 'leavePrompt']

    def __init__(self, id, **options):
        self._dict = {'id': id}
        for opt in self.options_array:
            if opt in options:
                self._dict[opt] = options[opt]

class Hangup(TropoAction):
    """
    Class representing the "hangup" Tropo action. Builds a "hangup" JSON object.
    Class constructor arg:
    Class constructor options:
    Convenience function: Tropo.hangup()

    (See https://www.tropo.com/docs/webapi/hangup.htm)

    { "hangup": { } }
    """
    action = 'hangup'

    def __init__(self):
        self._dict = {}
        
class JoinPrompt(TropoAction):
  """
  Class representing join prompts for the conference method. Builds a "joinPrompt" JSON object.
  Class constructor options: value, voice

  (See https://www.tropo.com/docs/webapi/conference.htm)
  """
  action = 'joinPrompt'
  options_array = ['value', 'voice']

  def __init__(self, value, **options):
    self._dict = {'value': value}
    for opt in self.options_array:
      if opt in options:
        self._dict[opt] = options[opt]

class LeavePrompt(TropoAction):
  """
  Class representing leave prompts for the conference method. Builds a "leavePrompt" JSON object.
  Class constructor options: value, voice

  (See https://www.tropo.com/docs/webapi/conference.htm)
  """
  action = 'leavePrompt'
  options_array = ['value', 'voice']

  def __init__(self, value, **options):
    self._dict = {'value': value}
    for opt in self.options_array:
      if opt in options:
        self._dict[opt] = options[opt]
                
class MachineDetection(TropoAction):
  """
  Class representing machine detection for the call method. Builds a "machineDetection" JSON object.
  Class constructor options: introduction, voice

  (See https://www.tropo.com/docs/webapi/call.htm)
  """
  action = 'machineDetection'
  options_array = ['introduction', 'voice']

  def __init__(self, introduction, **options):
    self._dict = {'introduction': introduction}
    for opt in self.options_array:
      if opt in options:
        self._dict[opt] = options[opt]
        
class Message(TropoAction):
    """
    Class representing the "message" Tropo action. Builds a "message" JSON object.
    Class constructor arg: say_obj, a Say object
    Class constructor arg: to, a String
    Class constructor options: answerOnMedia, channel, from, name, network, required, timeout, voice
    Convenience function: Tropo.message()

    (See https://www.tropo.com/docs/webapi/message.htm)
    { "message": {
            "say": Object,#Required
            "to": String or Array,#Required
            "answerOnMedia": Boolean,
            "channel": string,
            "from": String,
            "name": String,
            "network": String,
            "required": Boolean,
            "timeout": Float,
            "voice": String } }
    """
    action = 'message'
    options_array = ['answerOnMedia', 'channel', '_from', 'name', 'network', 'required', 'timeout', 'voice']

    def __init__(self, say_obj, to, **options):
        self._dict = {'say': say_obj['say'], 'to': to}
        for opt in self.options_array:
            if opt in options:
                if (opt == "_from"):
                    self._dict['from'] = options[opt]
                else:
                    self._dict[opt] = options[opt]


class On(TropoAction):
    """
    Class representing the "on" Tropo action. Builds an "on" JSON object.
    Class constructor arg: event, a String
    Class constructor options:  name,next,required,say
    Convenience function: Tropo.on()

    (See https://www.tropo.com/docs/webapi/on.htm)

    { "on": {
        "event": String,#Required
        "name": String,
        "next": String,
        "required": Boolean,
        "say": Object
        "voice": String } }
    """
    action = 'on'
    options_array = ['name','next','required','say', 'voice', 'ask', 'message', 'wait']

    def __init__(self, event, **options):
        self._dict = {}
        for opt in self.options_array:
            if opt in options:
                if ((opt == 'say') and (isinstance(options['say'], basestring))):
                    if('voice' in options):
                      self._dict['say'] = Say(options['say'], voice=options['voice']).json
                    else:
                      self._dict['say'] = Say(options['say']).json
             
                elif ((opt == 'ask') and (isinstance(options['ask'], basestring))):
                  if('voice' in options):
                    self._dict['ask'] = Ask(options['ask'], voice=options['voice']).json
                  else:
                    self._dict['ask'] = Ask(options['ask']).json
              
                elif ((opt == 'message') and (isinstance(options['message'], basestring))):
                  if('voice' in options):
                    self._dict['message'] = Message(options['message'], voice=options['voice']).json
                  else:
                    self._dict['message'] = Message(options['message']).json
                
                elif ((opt == 'wait') and (isinstance(options['wait'], basestring))):
                  self._dict['wait'] = Wait(options['wait']).json
                  
                elif(opt != 'voice'):
                    self._dict[opt] = options[opt]
                    
        self._dict['event'] = event

class Record(TropoAction):
    """
    Class representing the "record" Tropo action. Builds a "record" JSON object.
    Class constructor arg:
    Class constructor options: attempts, bargein, beep, choices, format, maxSilence, maxTime, method, minConfidence, name, password, required, say, timeout, transcription, url, username
    Convenience function: Tropo.record()

    (See https://www.tropo.com/docs/webapi/record.htm)

        { "record": {
            "attempts": Integer,
            "bargein": Boolean,
            "beep": Boolean,
            "choices": Object,
            "format": String,
            "maxSilence": Float,
            "maxTime": Float,
            "method": String,
            "minConfidence": Integer,
            "name": String,
            "password": String,
            "required": Boolean,
            "say": Object,
            "timeout": Float,
            "transcription": Array or Object,
            "url": String,#Required ?????
            "username": String,
            "voice": String} }
    """
    action = 'record'
    options_array = ['attempts', 'bargein', 'beep', 'choices', 'format', 'maxSilence', 'maxTime', 'method', 'minConfidence', 'name', 'password', 'required', 'say', 'timeout', 'transcription', 'url', 'username', 'allowSignals', 'voice', 'interdigitTimeout']

    def __init__(self, **options):
        self._dict = {}
        for opt in self.options_array:
            if opt in options:
                if ((opt == 'say') and (isinstance(options['say'], basestring))):
                    self._dict['say'] = Say(options['say']).json
                else:
                    self._dict[opt] = options[opt]

class Redirect(TropoAction):
    """
    Class representing the "redirect" Tropo action. Builds a "redirect" JSON object.
    Class constructor arg: to, a String
    Class constructor options:  name, required
    Convenience function: Tropo.redirect()

    (See https://www.tropo.com/docs/webapi/redirect.htm)

    { "redirect": {
        "to": Object,#Required
        "name": String,
        "required": Boolean } }
    """
    action = 'redirect'
    options_array = ['name', 'required']

    def __init__(self, to, **options):
        self._dict = {'to': to}
        for opt in self.options_array:
            if opt in options:
                self._dict[opt] = options[opt]

class Reject(TropoAction):
    """
    Class representing the "reject" Tropo action. Builds a "reject" JSON object.
    Class constructor arg:
    Class constructor options:
    Convenience function: Tropo.reject()

    (See https://www.tropo.com/docs/webapi/reject.htm)

    { "reject": { } }
    """
    action = 'reject'

    def __init__(self):
        self._dict = {}

class Say(TropoAction):
    """
    Class representing the "say" Tropo action. Builds a "say" JSON object.
    Class constructor arg: message, a String, or a List of Strings
    Class constructor options: attempts, bargein, choices, minConfidence, name, recognizer, required, say, timeout, voice
    Convenience function: Tropo.say()

    (See https://www.tropo.com/docs/webapi/say.htm)

    { "say": {
        "voice": String,
        "as": String,
        "name": String,
        "required": Boolean,
        "value": String #Required
        } }
    """
    action = 'say'
    # added _as because 'as' is reserved
    options_array = ['_as', 'name', 'required', 'voice', 'allowSignals']

    def __init__(self, message, **options):
        dict = {}
        for opt in self.options_array:
            if opt in options:
                if (opt == "_as"):
                    dict['as'] = options['_as']
                else:
                    dict[opt] = options[opt]
        self._list = []
        if (isinstance (message, list)):
            for mess in message:
                new_dict = dict.copy()
                new_dict['value'] = mess
                self._list.append(new_dict)
        else:
            dict['value'] = message
            self._list.append(dict)

    @property
    def json(self):
        return self._list[0] if len(self._list) == 1 else self._list

    @property
    def obj(self):
        return {self.action: self._list[0]} if len(self._list) == 1 else {self.action: self._list}

class StartRecording(TropoAction):
    """
    Class representing the "startRecording" Tropo action. Builds a "startRecording" JSON object.
    Class constructor arg: url, a String
    Class constructor options: format, method, username, password
    Convenience function: Tropo.startRecording()

    (See https://www.tropo.com/docs/webapi/startrecording.htm)

    { "startRecording": {
        "format": String,
        "method": String,
        "url": String,#Required
        "username": String,
        "password": String, 
        "transcriptionID": String
        "transcriptionEmailFormat":String
        "transcriptionOutURI": String} }
    """
    action = 'startRecording'
    options_array = ['format', 'method', 'username', 'password', 'transcriptionID', 'transcriptionEmailFormat', 'transcriptionOutURI']

    def __init__(self, url, **options):
        self._dict = {'url': url}
        for opt in self.options_array:
            if opt in options:
                self._dict[opt] = options[opt]

class StopRecording(TropoAction):
   """
    Class representing the "stopRecording" Tropo action. Builds a "stopRecording" JSON object.
    Class constructor arg:
    Class constructor options:
    Convenience function: Tropo.stopRecording()

   (See https://www.tropo.com/docs/webapi/stoprecording.htm)
      { "stopRecording": { } }
   """
   action = 'stopRecording'

   def __init__(self):
       self._dict = {}

class Transfer(TropoAction):
    """
    Class representing the "transfer" Tropo action. Builds a "transfer" JSON object.
    Class constructor arg: to, a String, or List
    Class constructor options: answerOnMedia, choices, from, name, required, terminator
    Convenience function: Tropo.transfer()

    (See https://www.tropo.com/docs/webapi/transfer.htm)
    { "transfer": {
        "to": String or Array,#Required
        "answerOnMedia": Boolean,
        "choices": Object,
	# # **Wed May 18 21:14:05 2011** -- egilchri
	"headers": Object,
	# # **Wed May 18 21:14:05 2011** -- egilchri
	
        "from": String,
        "name": String,
        "required": Boolean,
        "terminator": String,
        "timeout": Float,
        "machineDetection": Boolean or Object } }
    """
    action = 'transfer'
    options_array = ['answerOnMedia', 'choices', '_from', 'name', 'on', 'required', 'allowSignals', 'headers', 'interdigitTimeout', 'ringRepeat', 'timeout', 'machineDetection']

    def __init__(self, to, **options):
      self._dict = {'to': to}
      for opt in self.options_array:
        if opt in options:
          whisper = []
          for key, val in options['on'].iteritems():
            newDict = {}

            if(key == "ask"):
              newDict['ask'] = val
              newDict['event'] = 'connect'

            elif(key == "say"):
              newDict['say'] = val
              newDict['event'] = 'connect'

            elif(key == "wait"):
              newDict['wait'] = val
              newDict['event'] = 'connect'

            elif(key == "message"):
              newDict['message'] = val
              newDict['event'] = 'connect'
            
            elif(key == "ring"):
              newDict['say'] = val
              newDict['event'] = 'ring'

              
            whisper.append(newDict)

          self._dict['on'] = whisper
          if (opt == '_from'):
            self._dict['from'] = options['_from']
          elif(opt == 'choices'):
            self._dict['choices'] = options['choices']
          elif(opt != 'on'):
              self._dict[opt] = options[opt]

class Wait(TropoAction):
      """
      Class representing the "wait" Tropo action. Builds a "wait" JSON object.
      Class constructor arg: milliseconds, an Integer
      Class constructor options: allowSignals
      Convenience function: Tropo.wait()

      (See https://www.tropo.com/docs/webapi/wait.htm)
      { "wait": {
          "milliseconds": Integer,#Required
          "allowSignals": String or Array
      """
      
      action = 'wait'
      options_array = ['allowSignals']

      def __init__(self, milliseconds, **options):
          self._dict = {'milliseconds': milliseconds}
          for opt in self.options_array:
              if opt in options:
                self._dict[opt] = options[opt]

class Result(object):
    """
    Returned anytime a request is made to the Tropo Web API.
    Method: getValue
    (See https://www.tropo.com/docs/webapi/result.htm)

        { "result": {
            "actions": Array or Object,
            "complete": Boolean,
            "error": String,
            "sequence": Integer,
            "sessionDuration": Integer,
            "sessionId": String,
            "state": String } }
    """
    options_array = ['actions','complete','error','sequence', 'sessionDuration', 'sessionId', 'state', 'userType', 'connectedDuration', 'duration', 'calledID']

    def __init__(self, result_json):
        result_data = jsonlib.loads(result_json)
        result_dict = result_data['result']

        for opt in self.options_array:
            if result_dict.get(opt, False):
                setattr(self, '_%s' % opt, result_dict[opt])

    def getValue(self):
        """
        Get the value of the previously POSTed Tropo action.
        """
        actions = self._actions

        if (type (actions) is list):
            dict = actions[0]
        else:
            dict = actions
        # return dict['value'] Fixes issue 17
        return dict['value']


    def getUserType(self):
      """
      Get the userType of the previously POSTed Tropo action.
      """
      userType = self._userType
      return userType

# # **Tue May 17 07:17:38 2011** -- egilchri

    def getInterpretation(self):
        """
        Get the value of the previously POSTed Tropo action.
        """
        actions = self._actions

        if (type (actions) is list):
            dict = actions[0]
        else:
            dict = actions
        return dict['interpretation']

# # **Tue May 17 07:17:38 2011** -- egilchri


class Session(object):
    """
    Session is the payload sent as an HTTP POST to your web application when a new session arrives.
    (See https://www.tropo.com/docs/webapi/session.htm)
    
    Because 'from' is a reserved word in Python, the session object's 'from' property is called
    fromaddress in the Python library
    """
    def __init__(self, session_json):
        session_data = jsonlib.loads(session_json)
        session_dict = session_data['session']
        for key in session_dict:
            val = session_dict[key]
            if key == "from":
                setattr(self, "fromaddress", val)
            else:
                setattr(self, key, val)
	setattr(self, 'dict', session_dict)


class Tropo(object):
    """
      This is the top level class for all the Tropo web api actions.
      The methods of this class implement individual Tropo actions.
      Individual actions are each methods on this class.

      Each method takes one or more required arguments, followed by optional
      arguments expressed as key=value pairs.

      The optional arguments for these methods are described here:
      https://www.tropo.com/docs/webapi/
    """
    def  __init__(self):
        self._steps = []

# # **Sun May 15 21:05:01 2011** -- egilchri
    def setVoice(self, voice):
        self.voice = voice

# # end **Sun May 15 21:05:01 2011** -- egilchri

    def ask(self, choices, **options):
        """
	 Sends a prompt to the user and optionally waits for a response.
         Arguments: "choices" is a Choices object
         See https://www.tropo.com/docs/webapi/ask.htm
        """
# # **Sun May 15 21:21:29 2011** -- egilchri

        # Settng the voice in this method call has priority.
	# Otherwise, we can pick up the voice from the Tropo object,
	# if it is set there.
        if hasattr (self, 'voice'):
            if (not 'voice' in options):
                options['voice'] = self.voice
        
# # **Sun May 15 21:21:29 2011** -- egilchri

        self._steps.append(Ask(choices, **options).obj)


    def call (self, to, **options):
        """
	 Places a call or sends an an IM, Twitter, or SMS message. To start a call, use the Session API to tell Tropo to launch your code.

	 Arguments: to is a String.
	 Argument: **options is a set of optional keyword arguments.
	 See https://www.tropo.com/docs/webapi/call.htm
        """
        self._steps.append(Call (to, **options).obj)

    def conference(self, id, **options):
        """
        This object allows multiple lines in separate sessions to be conferenced together so that the parties on each line can talk to each other simultaneously.
	This is a voice channel only feature.
	Argument: "id" is a String
        Argument: **options is a set of optional keyword arguments.
	See https://www.tropo.com/docs/webapi/conference.htm
        """
        self._steps.append(Conference(id, **options).obj)

    def hangup(self):
        """
        This method instructs Tropo to "hang-up" or disconnect the session associated with the current session.
	See https://www.tropo.com/docs/webapi/hangup.htm
        """
        self._steps.append(Hangup().obj)

    def message (self, say_obj, to, **options):
        """
	A shortcut method to create a session, say something, and hang up, all in one step. This is particularly useful for sending out a quick SMS or IM.

 	Argument: "say_obj" is a Say object
        Argument: "to" is a String
        Argument: **options is a set of optional keyword arguments.
        See https://www.tropo.com/docs/webapi/message.htm
        """
        if isinstance(say_obj, basestring):
            say = Say(say_obj).obj
        else:
            say = say_obj
        self._steps.append(Message(say, to, **options).obj)

    def on(self, event, **options):
        """
        Adds an event callback so that your application may be notified when a particular event occurs.
	      Possible events are: "continue", "error", "incomplete" and "hangup".
	      Argument: event is an event
        Argument: **options is a set of optional keyword arguments.
        See https://www.tropo.com/docs/webapi/on.htm
        """
        
        if hasattr (self, 'voice'):
          if (not 'voice' in options):
            options['voice'] = self.voice


        self._steps.append(On(event, **options).obj)

    def record(self, **options):
        """
	 Plays a prompt (audio file or text to speech) and optionally waits for a response from the caller that is recorded.
         Argument: **options is a set of optional keyword arguments.
	 See https://www.tropo.com/docs/webapi/record.htm
        """
        self._steps.append(Record(**options).obj)

    def redirect(self, id, **options):
        """
        Forwards an incoming call to another destination / phone number before answering it.
        Argument: id is a String
        Argument: **options is a set of optional keyword arguments.
        See https://www.tropo.com/docs/webapi/redirect.htm
        """
        self._steps.append(Redirect(id, **options).obj)

    def reject(self):
        """
        Allows Tropo applications to reject incoming sessions before they are answered.
        See https://www.tropo.com/docs/webapi/reject.htm
        """
        self._steps.append(Reject().obj)

    def say(self, message, **options):
        """
	When the current session is a voice channel this key will either play a message or an audio file from a URL.
	In the case of an text channel it will send the text back to the user via i nstant messaging or SMS.
        Argument: message is a string
        Argument: **options is a set of optional keyword arguments.
        See https://www.tropo.com/docs/webapi/say.htm
        """
        #voice = self.voice
# # **Sun May 15 21:21:29 2011** -- egilchri

        # Settng the voice in this method call has priority.
	# Otherwise, we can pick up the voice from the Tropo object,
	# if it is set there.
        if hasattr (self, 'voice'):
            if (not 'voice' in options):
                options['voice'] = self.voice
# # **Sun May 15 21:21:29 2011** -- egilchri

        self._steps.append(Say(message, **options).obj)

    def startRecording(self, url, **options):
        """
        Allows Tropo applications to begin recording the current session.
        Argument: url is a string
        Argument: **options is a set of optional keyword arguments.
        See https://www.tropo.com/docs/webapi/startrecording.htm
        """
        self._steps.append(StartRecording(url, **options).obj)

    def stopRecording(self):
        """
        Stops a previously started recording.
	See https://www.tropo.com/docs/webapi/stoprecording.htm
        """
        self._steps.append(StopRecording().obj)

    def transfer(self, to, **options):
        """
        Transfers an already answered call to another destination / phone number.
	Argument: to is a string
        Argument: **options is a set of optional keyword arguments.
        See https://www.tropo.com/docs/webapi/transfer.htm
        """
        self._steps.append(Transfer(to, **options).obj)
        
    def wait(self, milliseconds, **options):
      """
      Allows the thread to sleep for a given amount of time in milliseconds
      Argument: milliseconds is an Integer
      Argument: **options is a set of optional keyword arguments.
      See https://www.tropo.com/docs/webapi/wait.htm
      """
      self._steps.append(Wait(milliseconds, **options).obj)
      
    def RenderJson(self, pretty=False):
        """
        Render a Tropo object into a Json string.
        """
        steps = self._steps
        topdict = {}
        topdict['tropo'] = steps
        if pretty:
            try:
                json = jsonlib.dumps(topdict, indent=4, sort_keys=False)
            except TypeError:
                json = jsonlib.dumps(topdict)
        else:
            json = jsonlib.dumps(topdict)
        return json

if __name__ == '__main__':
    print """

 This is the Python web API for http://www.tropo.com/

 To run the test suite, please run:

    cd test
    python test.py


"""



########NEW FILE########
