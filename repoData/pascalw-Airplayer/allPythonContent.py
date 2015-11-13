__FILENAME__ = airplayer
#!/usr/bin/env python
# encoding: utf-8
"""
airplayer.py

Created by Pascal Widdershoven on 2010-12-19.
Copyright (c) 2010 P. Widdershoven. All rights reserved.
"""

import sys
import thread
from socket import gethostname
import signal
from optparse import OptionParser
import logging
import os

import bonjour
from protocol_handler import AirplayProtocolHandler
import settings
import utils
from pidfile import Pidfile

class Application(object):
    
    def __init__(self, port):
        self._port = port
        self._pidfile = None
        self._media_backend = None
        self._protocol_handler = None
        self._opts = None
        self._args = None
        
        self.log = None
        
    def _setup_path(self):
        sys.path.append(os.path.join(os.path.dirname(__file__), 'lib'))  
        
    def _configure_logging(self):
        """
        Configure logging.
        When no logfile argument is given we log to stdout.
        """
        self.log = logging.getLogger('airplayer')

        fmt = r"%(asctime)s [%(levelname)s] %(message)s"
        datefmt = r"%Y-%m-%d %H:%M:%S"

        if self._opts.logfile:
            handler = logging.FileHandler(self._opts.logfile)
        else:
            handler = logging.StreamHandler()

        if getattr(settings, 'DEBUG', None):
            loglevel = logging.DEBUG
        else:
            loglevel = logging.INFO
            
        self.log.setLevel(loglevel)
        handler.setFormatter(logging.Formatter(fmt, datefmt))
        self.log.addHandler(handler)
        
    def _parse_opts(self):
        parser = OptionParser(usage='usage: %prog [options] filename')
        
        parser.add_option('-d', '--daemon', 
            action='store_true', 
            dest='daemon', 
            default=False,
            help='run Airplayer as a daemon in the background'
        )
        
        parser.add_option('-p', '--pidfile', 
            action='store',
            type='string', 
            dest='pidfile',
            default=None,
            help='path for the PID file'
        )
        
        parser.add_option('-l', '--logfile', 
            action='store',
            type='string', 
            dest='logfile', 
            default=None,
            help='path for the PID file'
        )
        
        (self._opts, self._args) = parser.parse_args()
        
        file_opts = ['logfile', 'pidfile']
        for opt in file_opts:
            """
            Expand user variables for all options containing a file path
            """
            value = getattr(self._opts, opt, None)
            
            if value:
                setattr(self._opts, opt, os.path.expanduser(value))                        
        
        if self._opts.daemon:
            if not self._opts.pidfile or not self._opts.logfile:
                print "It's required to specify a logfile and a pidfile when running in daemon mode.\n"
                parser.print_help()
                sys.exit(1)
                
    def _register_bonjour(self):
        """
        Register our service with bonjour.
        """
        if getattr(settings, 'AIRPLAY_HOSTNAME', None):
            hostname = settings.AIRPLAY_HOSTNAME
        else:    
            hostname = gethostname()
            """
            gethostname() often returns <hostname>.local, remove that.
            """
            hostname = utils.clean_hostname(hostname)
            
            if not hostname:
                hostname = 'Airplayer'
        
        thread.start_new_thread(bonjour.register_service, (hostname, "_airplay._tcp", self._port,))
        
    def _register_media_backend(self):
        """
        Backends follow the following naming convention:
        
        Backend module should be named <backend_name>_media_backend and should contain
        a class named <backend_name>MediaBackend which inherits from the BaseMediaBackend.
        """        
        backend_module = '%s_media_backend' % settings.MEDIA_BACKEND
        backend_class = '%sMediaBackend' % settings.MEDIA_BACKEND
                
        try:        
            mod = __import__('mediabackends.%s' % backend_module, fromlist=[backend_module])
        except ImportError, e:
            print e
            raise Exception('Invalid media backend specified: %s' % settings.MEDIA_BACKEND)
                
        backend_cls = getattr(mod, backend_class)
        
        username = getattr(settings, 'MEDIA_BACKEND_USERNAME', None)
        password = getattr(settings, 'MEDIA_BACKEND_PASSWORD', None)

        self._media_backend = backend_cls(settings.MEDIA_BACKEND_HOST, settings.MEDIA_BACKEND_PORT, username, password)
        
    def _init_signals(self):
        """
        Setup kill signal handlers.
        """
        signals = ['TERM', 'HUP', 'QUIT', 'INT']

        for signame in signals:
            """
            SIGHUP and SIGQUIT are not available on Windows, so just don't register a handler for them
            if they don't exist.
            """
            sig = getattr(signal, 'SIG%s' % signame, None)
            
            if sig:
                signal.signal(sig, self.receive_signal)    
        
    def _start_protocol_handler(self):
        """
        Start the webserver and connect our media backend.
        """
        self._protocol_handler = AirplayProtocolHandler(self._port, self._media_backend)
        self._protocol_handler.start()
                
    def run(self):
        """
        Run the application.
        Perform some bootstrapping, fork/daemonize if necessary.
        """
        self._parse_opts()
        self._setup_path()
                
        if self._opts.daemon:
            utils.daemonize()
            
            pid = os.getpid()
            self._pidfile = Pidfile(self._opts.pidfile)
            self._pidfile.create(pid)

        self._init_signals()
        self._configure_logging()
        self.log.info('Starting Airplayer')

        self._register_bonjour()
        self._register_media_backend()

        self._media_backend.notify_started()
        self._start_protocol_handler()
    
    def shutdown(self):
        """
        Called on application shutdown.
        
        Stop the webserver and stop the media backend.
        """
        self._protocol_handler.stop()
        self._media_backend.stop_playing()
        
        if self._opts.daemon:
            self._pidfile.unlink()
            
    def receive_signal(self, signum, stack):
        self.shutdown()    

def main():
    app = Application(settings.AIRPLAYER_PORT)
    
    try:
        app.run()
    except Exception, e:
        raise e
        sys.exit(1)

if __name__ == '__main__':
    main()

########NEW FILE########
__FILENAME__ = appletv
DEVICE_INFO = {
    'deviceid' : 'FF:FF:FF:FF:FF:FF',
    'features' : '0x77',
    'model' : 'AppleTV2,1',
    'srcvers' : '101.10'
}

SLIDESHOW_FEATURES = '<?xml version="1.0" encoding="UTF-8"?>\
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">\
<plist version="1.0">\
<dict>\
<key>themes</key>\
<array>\
    <dict>\
        <key>key</key>\
        <string>KenBurns</string>\
        <key>name</key>\
        <string>Ken Burns</string>\
        <key>transitions</key>\
        <array>\
            <dict>\
                <key>key</key>\
                <string>None</string>\
                <key>name</key>\
                <string>None</string>\
            </dict>\
            <dict>\
                <key>directions</key>\
                <array>\
                    <string>up</string>\
                    <string>down</string>\
                    <string>left</string>\
                    <string>down</string>\
                </array>\
                <key>key</key>\
                <string>Cube</string>\
                <key>name</key>\
                <string>Cube</string>\
            </dict>\
            <dict>\
                <key>key</key>\
                <string>Dissolve</string>\
                <key>name</key>\
                <string>Dissolve</string>\
            </dict>\
            <dict>\
                <key>key</key>\
                <string>Droplet</string>\
                <key>name</key>\
                <string>Droplet</string>\
            </dict>\
            <dict>\
                <key>key</key>\
                <string>FadeThruColor</string>\
                <key>name</key>\
                <string>Fade Through White</string>\
            </dict>\
            <dict>\
                <key>directions</key>\
                <array>\
                    <string>up</string>\
                    <string>down</string>\
                    <string>left</string>\
                    <string>down</string>\
                </array>\
                <key>key</key>\
                <string>Flip</string>\
                <key>name</key>\
                <string>Flip</string>\
            </dict>\
            <dict>\
                <key>key</key>\
                <string>TileFlip</string>\
                <key>name</key>\
                <string>Mosaic Flip</string>\
            </dict>\
            <dict>\
                <key>directions</key>\
                <array>\
                    <string>up</string>\
                    <string>down</string>\
                    <string>left</string>\
                    <string>down</string>\
                </array>\
                <key>key</key>\
                <string>MoveIn</string>\
                <key>name</key>\
                <string>Move In</string>\
            </dict>\
            <dict>\
                <key>directions</key>\
                <array>\
                    <string>left</string>\
                    <string>down</string>\
                </array>\
                <key>key</key>\
                <string>PageFlip</string>\
                <key>name</key>\
                <string>Page Flip</string>\
            </dict>\
            <dict>\
                <key>directions</key>\
                <array>\
                    <string>up</string>\
                    <string>down</string>\
                    <string>left</string>\
                    <string>down</string>\
                </array>\
                <key>key</key>\
                <string>Push</string>\
                <key>name</key>\
                <string>Push</string>\
            </dict>\
            <dict>\
                <key>directions</key>\
                <array>\
                    <string>up</string>\
                    <string>down</string>\
                    <string>left</string>\
                    <string>down</string>\
                </array>\
                <key>key</key>\
                <string>Reveal</string>\
                <key>name</key>\
                <string>Reveal</string>\
            </dict>\
            <dict>\
                <key>key</key>\
                <string>Twirl</string>\
                <key>name</key>\
                <string>Twirl</string>\
            </dict>\
            <dict>\
                <key>directions</key>\
                <array>\
                    <string>up</string>\
                    <string>down</string>\
                    <string>left</string>\
                    <string>down</string>\
                </array>\
                <key>key</key>\
                <string>Wipe</string>\
                <key>name</key>\
                <string>Wipe</string>\
            </dict>\
        </array>\
    </dict>\
    <dict>\
        <key>key</key>\
        <string>Origami</string>\
        <key>name</key>\
        <string>Origami</string>\
    </dict>\
    <dict>\
        <key>key</key>\
        <string>Reflections</string>\
        <key>name</key>\
        <string>Reflections</string>\
    </dict>\
    <dict>\
        <key>key</key>\
        <string>Snapshots</string>\
        <key>name</key>\
        <string>Snapshots</string>\
    </dict>\
    <dict>\
        <key>key</key>\
        <string>Classic</string>\
        <key>name</key>\
        <string>Classic</string>\
        <key>transitions</key>\
        <array>\
            <dict>\
                <key>key</key>\
                <string>None</string>\
                <key>name</key>\
                <string>None</string>\
            </dict>\
            <dict>\
                <key>directions</key>\
                <array>\
                    <string>up</string>\
                    <string>down</string>\
                    <string>left</string>\
                    <string>down</string>\
                </array>\
                <key>key</key>\
                <string>Cube</string>\
                <key>name</key>\
                <string>Cube</string>\
            </dict>\
            <dict>\
                <key>key</key>\
                <string>Dissolve</string>\
                <key>name</key>\
                <string>Dissolve</string>\
            </dict>\
            <dict>\
                <key>key</key>\
                <string>Droplet</string>\
                <key>name</key>\
                <string>Droplet</string>\
            </dict>\
            <dict>\
                <key>key</key>\
                <string>FadeThruColor</string>\
                <key>name</key>\
                <string>Fade Through White</string>\
            </dict>\
            <dict>\
                <key>directions</key>\
                <array>\
                    <string>up</string>\
                    <string>down</string>\
                    <string>left</string>\
                    <string>down</string>\
                </array>\
                <key>key</key>\
                <string>Flip</string>\
                <key>name</key>\
                <string>Flip</string>\
            </dict>\
            <dict>\
                <key>key</key>\
                <string>TileFlip</string>\
                <key>name</key>\
                <string>Mosaic Flip</string>\
            </dict>\
            <dict>\
                <key>directions</key>\
                <array>\
                    <string>up</string>\
                    <string>down</string>\
                    <string>left</string>\
                    <string>down</string>\
                </array>\
                <key>key</key>\
                <string>MoveIn</string>\
                <key>name</key>\
                <string>Move In</string>\
            </dict>\
            <dict>\
                <key>directions</key>\
                <array>\
                    <string>left</string>\
                    <string>down</string>\
                </array>\
                <key>key</key>\
                <string>PageFlip</string>\
                <key>name</key>\
                <string>Page Flip</string>\
            </dict>\
            <dict>\
                <key>directions</key>\
                <array>\
                    <string>up</string>\
                    <string>down</string>\
                    <string>left</string>\
                    <string>down</string>\
                </array>\
                <key>key</key>\
                <string>Push</string>\
                <key>name</key>\
                <string>Push</string>\
            </dict>\
            <dict>\
                <key>directions</key>\
                <array>\
                    <string>up</string>\
                    <string>down</string>\
                    <string>left</string>\
                    <string>down</string>\
                </array>\
                <key>key</key>\
                <string>Reveal</string>\
                <key>name</key>\
                <string>Reveal</string>\
            </dict>\
            <dict>\
                <key>key</key>\
                <string>Twirl</string>\
                <key>name</key>\
                <string>Twirl</string>\
            </dict>\
            <dict>\
                <key>directions</key>\
                <array>\
                    <string>up</string>\
                    <string>down</string>\
                    <string>left</string>\
                    <string>down</string>\
                </array>\
                <key>key</key>\
                <string>Wipe</string>\
                <key>name</key>\
                <string>Wipe</string>\
            </dict>\
        </array>\
    </dict>\
</array>\
</dict>\
</plist>'

SERVER_INFO = '<?xml version="1.0" encoding="UTF-8"?>\
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">\
<plist version="1.0">\
<dict>\
<key>deviceid</key>\
<string>58:55:CA:06:BD:9E</string>\
<key>features</key>\
<integer>119</integer>\
<key>model</key>\
<string>AppleTV2,1</string>\
<key>protovers</key>\
<string>1.0</string>\
<key>srcvers</key>\
<string>101.10</string>\
</dict>\
</plist>'

PLAYBACK_INFO = '<?xml version="1.0" encoding="UTF-8"?>\
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">\
<plist version="1.0">\
<dict>\
<key>duration</key>\
<real>%f</real>\
<key>loadedTimeRanges</key>\
<array>\
    <dict>\
        <key>duration</key>\
        <real>%f</real>\
        <key>start</key>\
        <real>0.0</real>\
    </dict>\
</array>\
<key>playbackBufferEmpty</key>\
<true/>\
<key>playbackBufferFull</key>\
<false/>\
<key>playbackLikelyToKeepUp</key>\
<true/>\
<key>position</key>\
<real>%f</real>\
<key>rate</key>\
<real>%d</real>\
<key>readyToPlay</key>\
<true/>\
<key>seekableTimeRanges</key>\
<array>\
    <dict>\
        <key>duration</key>\
        <real>%f</real>\
        <key>start</key>\
        <real>0.0</real>\
    </dict>\
</array>\
</dict>\
</plist>'
########NEW FILE########
__FILENAME__ = bonjour
import select
import pybonjour
import logging
import appletv

logger = logging.getLogger('airplayer')

def register_service(name, regtype, port):
    def register_callback(sdRef, flags, errorCode, name, regtype, domain):
        if errorCode == pybonjour.kDNSServiceErr_NoError:
            logger.debug('Registered bonjour service %s.%s', name, regtype)

    record = pybonjour.TXTRecord(appletv.DEVICE_INFO)
    
    service = pybonjour.DNSServiceRegister(name = name,
                                         regtype = regtype,
                                         port = port,
                                         txtRecord = record,
                                         callBack = register_callback)

    try:
        try:
            while True:
                ready = select.select([service], [], [])
                if service in ready[0]:
                    pybonjour.DNSServiceProcessResult(service)
        except KeyboardInterrupt:
            pass
    finally:
        service.close()
########NEW FILE########
__FILENAME__ = config
import sys

class LocalClasses(dict):
    def add(self, cls):
        self[cls.__name__] = cls

class Config(object):
    """
    This is pretty much used exclusively for the 'jsonclass' 
    functionality... set use_jsonclass to False to turn it off.
    You can change serialize_method and ignore_attribute, or use
    the local_classes.add(class) to include "local" classes.
    """
    use_jsonclass = True
    # Change to False to keep __jsonclass__ entries raw.
    serialize_method = '_serialize'
    # The serialize_method should be a string that references the
    # method on a custom class object which is responsible for 
    # returning a tuple of the constructor arguments and a dict of
    # attributes.
    ignore_attribute = '_ignore'
    # The ignore attribute should be a string that references the
    # attribute on a custom class object which holds strings and / or
    # references of the attributes the class translator should ignore.
    classes = LocalClasses()
    # The list of classes to use for jsonclass translation.
    version = 2.0
    # Version of the JSON-RPC spec to support
    user_agent = 'jsonrpclib/0.1 (Python %s)' % \
        '.'.join([str(ver) for ver in sys.version_info[0:3]])
    # User agent to use for calls.
    _instance = None
    
    @classmethod
    def instance(cls):
        if not cls._instance:
            cls._instance = cls()
        return cls._instance

########NEW FILE########
__FILENAME__ = history
class History(object):
    """
    This holds all the response and request objects for a
    session. A server using this should call "clear" after
    each request cycle in order to keep it from clogging 
    memory.
    """
    requests = []
    responses = []
    _instance = None
    
    @classmethod
    def instance(cls):
        if not cls._instance:
            cls._instance = cls()
        return cls._instance

    def add_response(self, response_obj):
        self.responses.append(response_obj)
    
    def add_request(self, request_obj):
        self.requests.append(request_obj)

    @property
    def request(self):
        if len(self.requests) == 0:
            return None
        else:
            return self.requests[-1]

    @property
    def response(self):
        if len(self.responses) == 0:
            return None
        else:
            return self.responses[-1]

    def clear(self):
        del self.requests[:]
        del self.responses[:]

########NEW FILE########
__FILENAME__ = jsonclass
import types
import inspect
import re
import traceback

from jsonrpclib import config

iter_types = [
    types.DictType,
    types.ListType,
    types.TupleType
]

string_types = [
    types.StringType,
    types.UnicodeType
]

numeric_types = [
    types.IntType,
    types.LongType,
    types.FloatType
]

value_types = [
    types.BooleanType,
    types.NoneType
]

supported_types = iter_types+string_types+numeric_types+value_types
invalid_module_chars = r'[^a-zA-Z0-9\_\.]'

class TranslationError(Exception):
    pass

def dump(obj, serialize_method=None, ignore_attribute=None, ignore=[]):
    if not serialize_method:
        serialize_method = config.serialize_method
    if not ignore_attribute:
        ignore_attribute = config.ignore_attribute
    obj_type = type(obj)
    # Parse / return default "types"...
    if obj_type in numeric_types+string_types+value_types:
        return obj
    if obj_type in iter_types:
        if obj_type in (types.ListType, types.TupleType):
            new_obj = []
            for item in obj:
                new_obj.append(dump(item, serialize_method,
                                     ignore_attribute, ignore))
            if obj_type is types.TupleType:
                new_obj = tuple(new_obj)
            return new_obj
        # It's a dict...
        else:
            new_obj = {}
            for key, value in obj.iteritems():
                new_obj[key] = dump(value, serialize_method,
                                     ignore_attribute, ignore)
            return new_obj
    # It's not a standard type, so it needs __jsonclass__
    module_name = inspect.getmodule(obj).__name__
    class_name = obj.__class__.__name__
    json_class = class_name
    if module_name not in ['', '__main__']:
        json_class = '%s.%s' % (module_name, json_class)
    return_obj = {"__jsonclass__":[json_class,]}
    # If a serialization method is defined..
    if serialize_method in dir(obj):
        # Params can be a dict (keyword) or list (positional)
        # Attrs MUST be a dict.
        serialize = getattr(obj, serialize_method)
        params, attrs = serialize()
        return_obj['__jsonclass__'].append(params)
        return_obj.update(attrs)
        return return_obj
    # Otherwise, try to figure it out
    # Obviously, we can't assume to know anything about the
    # parameters passed to __init__
    return_obj['__jsonclass__'].append([])
    attrs = {}
    ignore_list = getattr(obj, ignore_attribute, [])+ignore
    for attr_name, attr_value in obj.__dict__.iteritems():
        if type(attr_value) in supported_types and \
                attr_name not in ignore_list and \
                attr_value not in ignore_list:
            attrs[attr_name] = dump(attr_value, serialize_method,
                                     ignore_attribute, ignore)
    return_obj.update(attrs)
    return return_obj

def load(obj):
    if type(obj) in string_types+numeric_types+value_types:
        return obj
    if type(obj) is types.ListType:
        return_list = []
        for entry in obj:
            return_list.append(load(entry))
        return return_list
    # Othewise, it's a dict type
    if '__jsonclass__' not in obj.keys():
        return_dict = {}
        for key, value in obj.iteritems():
            new_value = load(value)
            return_dict[key] = new_value
        return return_dict
    # It's a dict, and it's a __jsonclass__
    orig_module_name = obj['__jsonclass__'][0]
    params = obj['__jsonclass__'][1]
    if orig_module_name == '':
        raise TranslationError('Module name empty.')
    json_module_clean = re.sub(invalid_module_chars, '', orig_module_name)
    if json_module_clean != orig_module_name:
        raise TranslationError('Module name %s has invalid characters.' %
                               orig_module_name)
    json_module_parts = json_module_clean.split('.')
    json_class = None
    if len(json_module_parts) == 1:
        # Local class name -- probably means it won't work
        if json_module_parts[0] not in config.classes.keys():
            raise TranslationError('Unknown class or module %s.' %
                                   json_module_parts[0])
        json_class = config.classes[json_module_parts[0]]
    else:
        json_class_name = json_module_parts.pop()
        json_module_tree = '.'.join(json_module_parts)
        try:
            temp_module = __import__(json_module_tree)
        except ImportError:
            raise TranslationError('Could not import %s from module %s.' %
                                   (json_class_name, json_module_tree))
        json_class = getattr(temp_module, json_class_name)
    # Creating the object...
    new_obj = None
    if type(params) is types.ListType:
        new_obj = json_class(*params)
    elif type(params) is types.DictType:
        new_obj = json_class(**params)
    else:
        raise TranslationError('Constructor args must be a dict or list.')
    for key, value in obj.iteritems():
        if key == '__jsonclass__':
            continue
        setattr(new_obj, key, value)
    return new_obj

########NEW FILE########
__FILENAME__ = jsonrpc
"""
Copyright 2009 Josh Marshall 
Licensed under the Apache License, Version 2.0 (the "License"); 
you may not use this file except in compliance with the License. 
You may obtain a copy of the License at 

   http://www.apache.org/licenses/LICENSE-2.0 

Unless required by applicable law or agreed to in writing, software 
distributed under the License is distributed on an "AS IS" BASIS, 
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. 
See the License for the specific language governing permissions and 
limitations under the License. 

============================
JSONRPC Library (jsonrpclib)
============================

This library is a JSON-RPC v.2 (proposed) implementation which
follows the xmlrpclib API for portability between clients. It
uses the same Server / ServerProxy, loads, dumps, etc. syntax,
while providing features not present in XML-RPC like:

* Keyword arguments
* Notifications
* Versioning
* Batches and batch notifications

Eventually, I'll add a SimpleXMLRPCServer compatible library,
and other things to tie the thing off nicely. :)

For a quick-start, just open a console and type the following,
replacing the server address, method, and parameters 
appropriately.
>>> import jsonrpclib
>>> server = jsonrpclib.Server('http://localhost:8181')
>>> server.add(5, 6)
11
>>> server._notify.add(5, 6)
>>> batch = jsonrpclib.MultiCall(server)
>>> batch.add(3, 50)
>>> batch.add(2, 3)
>>> batch._notify.add(3, 5)
>>> batch()
[53, 5]

See http://code.google.com/p/jsonrpclib/ for more info.
"""

import types
import sys
from xmlrpclib import Transport as XMLTransport
from xmlrpclib import SafeTransport as XMLSafeTransport
from xmlrpclib import ServerProxy as XMLServerProxy
from xmlrpclib import _Method as XML_Method
import time

# Library includes
import jsonrpclib
from jsonrpclib import config
from jsonrpclib import history

# JSON library importing
cjson = None
json = None
try:
    import cjson
except ImportError:
    pass
if not cjson:
    try:
        import json
    except ImportError:
        pass
if not cjson and not json: 
    try:
        import simplejson as json
    except ImportError:
        raise ImportError('You must have the cjson, json, or simplejson ' +
                          'module(s) available.')

#JSON Abstractions

def jdumps(obj, encoding='utf-8'):
    """
    XBMC is currently not fully compliant to the JSON-RPC 2.0 spec.
    When a single argument is passed an array with one element
    should be provied according to the spec, however XBMC expects a
    single value in this case.
    
    See http://forum.xbmc.org/showpost.php?p=671587&postcount=591
    """
    if 'params' in obj and len(obj['params']) == 1:
        obj['params'] = obj['params'][0]
    
    # Do 'serialize' test at some point for other classes
    global cjson
    if cjson:
        return cjson.encode(obj)
    else:
        return json.dumps(obj, encoding=encoding)

def jloads(json_string):
    global cjson
    if cjson:
        return cjson.decode(json_string)
    else:
        return json.loads(json_string)


# XMLRPClib re-implemntations

class ProtocolError(Exception):
    pass

class TransportMixIn(object):
    """ Just extends the XMLRPC transport where necessary. """
    user_agent = config.user_agent
    # for Python 2.7 support
    _connection = None

    def send_content(self, connection, request_body):
        connection.putheader("Content-Type", "application/json-rpc")
        connection.putheader("Content-Length", str(len(request_body)))
        connection.endheaders()
        if request_body:
            connection.send(request_body)

    def getparser(self):
        target = JSONTarget()
        return JSONParser(target), target

class JSONParser(object):
    def __init__(self, target):
        self.target = target

    def feed(self, data):
        self.target.feed(data)

    def close(self):
        pass

class JSONTarget(object):
    def __init__(self):
        self.data = []

    def feed(self, data):
        self.data.append(data)

    def close(self):
        return ''.join(self.data)

class Transport(TransportMixIn, XMLTransport):
    pass

class SafeTransport(TransportMixIn, XMLSafeTransport):
    pass
    
class ServerProxy(XMLServerProxy):
    """
    Unfortunately, much more of this class has to be copied since
    so much of it does the serialization.
    """

    def __init__(self, uri, transport=None, encoding=None, 
                 verbose=0, version=None):
        import urllib
        if not version:
            version = config.version
        self.__version = version
        schema, uri = urllib.splittype(uri)
        if schema not in ('http', 'https'):
            raise IOError('Unsupported JSON-RPC protocol.')
        self.__host, self.__handler = urllib.splithost(uri)
        if not self.__handler:
            # Not sure if this is in the JSON spec?
            #self.__handler = '/'
            self.__handler == '/'
        if transport is None:
            if schema == 'https':
                transport = SafeTransport()
            else:
                transport = Transport()
        self.__transport = transport
        self.__encoding = encoding
        self.__verbose = verbose

    def _request(self, methodname, params, rpcid=None):
        request = dumps(params, methodname, encoding=self.__encoding,
                        rpcid=rpcid, version=self.__version)
        response = self._run_request(request)
        check_for_errors(response)
        return response['result']

    def _request_notify(self, methodname, params, rpcid=None):
        request = dumps(params, methodname, encoding=self.__encoding,
                        rpcid=rpcid, version=self.__version, notify=True)
        response = self._run_request(request, notify=True)
        check_for_errors(response)
        return

    def _run_request(self, request, notify=None):
        history.add_request(request)

        response = self.__transport.request(
            self.__host,
            self.__handler,
            request,
            verbose=self.__verbose
        )
        
        # Here, the XMLRPC library translates a single list
        # response to the single value -- should we do the
        # same, and require a tuple / list to be passed to
        # the response object, or expect the Server to be 
        # outputting the response appropriately?
        
        history.add_response(response)
        if not response:
            return None
        return_obj = loads(response)
        return return_obj

    def __getattr__(self, name):
        # Same as original, just with new _Method reference
        return _Method(self._request, name)

    @property
    def _notify(self):
        # Just like __getattr__, but with notify namespace.
        return _Notify(self._request_notify)


class _Method(XML_Method):
    
    def __call__(self, *args, **kwargs):
        if len(args) > 0 and len(kwargs) > 0:
            raise ProtocolError('Cannot use both positional ' +
                'and keyword arguments (according to JSON-RPC spec.)')
        if len(args) > 0:
            return self.__send(self.__name, args)
        else:
            return self.__send(self.__name, kwargs)

    def __getattr__(self, name):
        self.__name = '%s.%s' % (self.__name, name)
        return self
        # The old method returned a new instance, but this seemed wasteful.
        # The only thing that changes is the name.
        #return _Method(self.__send, "%s.%s" % (self.__name, name))

class _Notify(object):
    def __init__(self, request):
        self._request = request

    def __getattr__(self, name):
        return _Method(self._request, name)
        
# Batch implementation

class MultiCallMethod(object):
    
    def __init__(self, method, notify=False):
        self.method = method
        self.params = []
        self.notify = notify

    def __call__(self, *args, **kwargs):
        if len(kwargs) > 0 and len(args) > 0:
            raise ProtocolError('JSON-RPC does not support both ' +
                                'positional and keyword arguments.')
        if len(kwargs) > 0:
            self.params = kwargs
        else:
            self.params = args

    def request(self, encoding=None, rpcid=None):
        return dumps(self.params, self.method, version=2.0,
                     encoding=encoding, rpcid=rpcid, notify=self.notify)

    def __repr__(self):
        return '%s' % self.request()
        
    def __getattr__(self, method):
        new_method = '%s.%s' % (self.method, method)
        self.method = new_method
        return self

class MultiCallNotify(object):
    
    def __init__(self, multicall):
        self.multicall = multicall

    def __getattr__(self, name):
        new_job = MultiCallMethod(name, notify=True)
        self.multicall._job_list.append(new_job)
        return new_job

class MultiCallIterator(object):
    
    def __init__(self, results):
        self.results = results

    def __iter__(self):
        for i in range(0, len(self.results)):
            yield self[i]
        raise StopIteration

    def __getitem__(self, i):
        item = self.results[i]
        check_for_errors(item)
        return item['result']

    def __len__(self):
        return len(self.results)

class MultiCall(object):
    
    def __init__(self, server):
        self._server = server
        self._job_list = []

    def _request(self):
        if len(self._job_list) < 1:
            # Should we alert? This /is/ pretty obvious.
            return
        request_body = '[ %s ]' % ','.join([job.request() for
                                          job in self._job_list])
        responses = self._server._run_request(request_body)
        del self._job_list[:]
        if not responses:
            responses = []
        return MultiCallIterator(responses)

    @property
    def _notify(self):
        return MultiCallNotify(self)

    def __getattr__(self, name):
        new_job = MultiCallMethod(name)
        self._job_list.append(new_job)
        return new_job

    __call__ = _request

# These lines conform to xmlrpclib's "compatibility" line. 
# Not really sure if we should include these, but oh well.
Server = ServerProxy

class Fault(object):
    # JSON-RPC error class
    def __init__(self, code=-32000, message='Server error', rpcid=None):
        self.faultCode = code
        self.faultString = message
        self.rpcid = rpcid

    def error(self):
        return {'code':self.faultCode, 'message':self.faultString}

    def response(self, rpcid=None, version=None):
        if not version:
            version = config.version
        if rpcid:
            self.rpcid = rpcid
        return dumps(
            self, methodresponse=True, rpcid=self.rpcid, version=version
        )

    def __repr__(self):
        return '<Fault %s: %s>' % (self.faultCode, self.faultString)

def random_id(length=8):
    import string
    import random
    random.seed()
    choices = string.lowercase+string.digits
    return_id = ''
    for i in range(length):
        return_id += random.choice(choices)
    return return_id

class Payload(dict):
    def __init__(self, rpcid=None, version=None):
        if not version:
            version = config.version
        self.id = rpcid
        self.version = float(version)
    
    def request(self, method, params=[]):
        if type(method) not in types.StringTypes:
            raise ValueError('Method name must be a string.')
        if not self.id:
            self.id = random_id()
        request = { 'id':self.id, 'method':method }
        if params:
            request['params'] = params
        if self.version >= 2:
            request['jsonrpc'] = str(self.version)
        return request

    def notify(self, method, params=[]):
        request = self.request(method, params)
        if self.version >= 2:
            del request['id']
        else:
            request['id'] = None
        return request

    def response(self, result=None):
        response = {'result':result, 'id':self.id}
        if self.version >= 2:
            response['jsonrpc'] = str(self.version)
        else:
            response['error'] = None
        return response

    def error(self, code=-32000, message='Server error.'):
        error = self.response()
        if self.version >= 2:
            del error['result']
        else:
            error['result'] = None
        error['error'] = {'code':code, 'message':message}
        return error

def dumps(params=[], methodname=None, methodresponse=None, 
        encoding=None, rpcid=None, version=None, notify=None):
    """
    This differs from the Python implementation in that it implements 
    the rpcid argument since the 2.0 spec requires it for responses.
    """
    if not version:
        version = config.version
    valid_params = (types.TupleType, types.ListType, types.DictType)
    if methodname in types.StringTypes and \
            type(params) not in valid_params and \
            not isinstance(params, Fault):
        """ 
        If a method, and params are not in a listish or a Fault,
        error out.
        """
        raise TypeError('Params must be a dict, list, tuple or Fault ' +
                        'instance.')
    # Begin parsing object
    payload = Payload(rpcid=rpcid, version=version)
    if not encoding:
        encoding = 'utf-8'
    if type(params) is Fault:
        response = payload.error(params.faultCode, params.faultString)
        return jdumps(response, encoding=encoding)
    if type(methodname) not in types.StringTypes and methodresponse != True:
        raise ValueError('Method name must be a string, or methodresponse '+
                         'must be set to True.')
    if config.use_jsonclass == True:
        from jsonrpclib import jsonclass
        params = jsonclass.dump(params)
    if methodresponse is True:
        if rpcid is None:
            raise ValueError('A method response must have an rpcid.')
        response = payload.response(params)
        return jdumps(response, encoding=encoding)
    request = None
    if notify == True:
        request = payload.notify(methodname, params)
    else:
        request = payload.request(methodname, params)
    return jdumps(request, encoding=encoding)

def loads(data):
    """
    This differs from the Python implementation, in that it returns
    the request structure in Dict format instead of the method, params.
    It will return a list in the case of a batch request / response.
    """
    if data == '':
        # notification
        return None
    result = jloads(data)
    # if the above raises an error, the implementing server code 
    # should return something like the following:
    # { 'jsonrpc':'2.0', 'error': fault.error(), id: None }
    if config.use_jsonclass == True:
        from jsonrpclib import jsonclass
        result = jsonclass.load(result)
    return result

def check_for_errors(result):
    if not result:
        # Notification
        return result
    if type(result) is not types.DictType:
        raise TypeError('Response is not a dict.')
    if 'jsonrpc' in result.keys() and float(result['jsonrpc']) > 2.0:
        raise NotImplementedError('JSON-RPC version not yet supported.')
    if 'result' not in result.keys() and 'error' not in result.keys():
        raise ValueError('Response does not have a result or error key.')
    if 'error' in result.keys() and result['error'] != None:
        code = result['error']['code']
        message = result['error']['message']
        raise ProtocolError((code, message))
    return result

def isbatch(result):
    if type(result) not in (types.ListType, types.TupleType):
        return False
    if len(result) < 1:
        return False
    if type(result[0]) is not types.DictType:
        return False
    if 'jsonrpc' not in result[0].keys():
        return False
    try:
        version = float(result[0]['jsonrpc'])
    except ValueError:
        raise ProtocolError('"jsonrpc" key must be a float(able) value.')
    if version < 2:
        return False
    return True

def isnotification(request):
    if 'id' not in request.keys():
        # 2.0 notification
        return True
    if request['id'] == None:
        # 1.0 notification
        return True
    return False

########NEW FILE########
__FILENAME__ = SimpleJSONRPCServer
import jsonrpclib
from jsonrpclib import Fault
import SimpleXMLRPCServer
import SocketServer
import types
import traceback
import sys
try:
    import fcntl
except ImportError:
    # For Windows
    fcntl = None

def get_version(request):
    # must be a dict
    if 'jsonrpc' in request.keys():
        return 2.0
    if 'id' in request.keys():
        return 1.0
    return None
    
def validate_request(request):
    if type(request) is not types.DictType:
        fault = Fault(
            -32600, 'Request must be {}, not %s.' % type(request)
        )
        return fault
    rpcid = request.get('id', None)
    version = get_version(request)
    if not version:
        fault = Fault(-32600, 'Request %s invalid.' % request, rpcid=rpcid)
        return fault        
    request.setdefault('params', [])
    method = request.get('method', None)
    params = request.get('params')
    param_types = (types.ListType, types.DictType, types.TupleType)
    if not method or type(method) not in types.StringTypes or \
        type(params) not in param_types:
        fault = Fault(
            -32600, 'Invalid request parameters or method.', rpcid=rpcid
        )
        return fault
    return True

class SimpleJSONRPCDispatcher(SimpleXMLRPCServer.SimpleXMLRPCDispatcher):

    def __init__(self, encoding=None):
        SimpleXMLRPCServer.SimpleXMLRPCDispatcher.__init__(self,
                                        allow_none=True,
                                        encoding=encoding)

    def _marshaled_dispatch(self, data, dispatch_method = None):
        response = None
        try:
            request = jsonrpclib.loads(data)
        except Exception, e:
            fault = Fault(-32700, 'Request %s invalid. (%s)' % (data, e))
            response = fault.response()
            return response
        if not request:
            fault = Fault(-32600, 'Request invalid -- no request data.')
            return fault.response()
        if type(request) is types.ListType:
            # This SHOULD be a batch, by spec
            responses = []
            for req_entry in request:
                result = validate_request(req_entry)
                if type(result) is Fault:
                    responses.append(result.response())
                    continue
                resp_entry = self._marshaled_single_dispatch(req_entry)
                if resp_entry is not None:
                    responses.append(resp_entry)
            if len(responses) > 0:
                response = '[%s]' % ','.join(responses)
            else:
                response = ''
        else:    
            result = validate_request(request)
            if type(result) is Fault:
                return result.response()
            response = self._marshaled_single_dispatch(request)
        return response

    def _marshaled_single_dispatch(self, request):
        # TODO - Use the multiprocessing and skip the response if
        # it is a notification
        # Put in support for custom dispatcher here
        # (See SimpleXMLRPCServer._marshaled_dispatch)
        method = request.get('method')
        params = request.get('params')
        try:
            response = self._dispatch(method, params)
        except:
            exc_type, exc_value, exc_tb = sys.exc_info()
            fault = Fault(-32603, '%s:%s' % (exc_type, exc_value))
            return fault.response()
        if 'id' not in request.keys() or request['id'] == None:
            # It's a notification
            return None
        try:
            response = jsonrpclib.dumps(response,
                                        methodresponse=True,
                                        rpcid=request['id']
                                        )
            return response
        except:
            exc_type, exc_value, exc_tb = sys.exc_info()
            fault = Fault(-32603, '%s:%s' % (exc_type, exc_value))
            return fault.response()

    def _dispatch(self, method, params):
        func = None
        try:
            func = self.funcs[method]
        except KeyError:
            if self.instance is not None:
                if hasattr(self.instance, '_dispatch'):
                    return self.instance._dispatch(method, params)
                else:
                    try:
                        func = SimpleXMLRPCServer.resolve_dotted_attribute(
                            self.instance,
                            method,
                            True
                            )
                    except AttributeError:
                        pass
        if func is not None:
            try:
                if type(params) is types.ListType:
                    response = func(*params)
                else:
                    response = func(**params)
                return response
            except TypeError:
                return Fault(-32602, 'Invalid parameters.')
            except:
                err_lines = traceback.format_exc().splitlines()
                trace_string = '%s | %s' % (err_lines[-3], err_lines[-1])
                fault = jsonrpclib.Fault(-32603, 'Server error: %s' % 
                                         trace_string)
                return fault
        else:
            return Fault(-32601, 'Method %s not supported.' % method)

class SimpleJSONRPCRequestHandler(
        SimpleXMLRPCServer.SimpleXMLRPCRequestHandler):
    
    def do_POST(self):
        if not self.is_rpc_path_valid():
            self.report_404()
            return
        try:
            max_chunk_size = 10*1024*1024
            size_remaining = int(self.headers["content-length"])
            L = []
            while size_remaining:
                chunk_size = min(size_remaining, max_chunk_size)
                L.append(self.rfile.read(chunk_size))
                size_remaining -= len(L[-1])
            data = ''.join(L)
            response = self.server._marshaled_dispatch(data)
            self.send_response(200)
        except Exception, e:
            self.send_response(500)
            err_lines = traceback.format_exc().splitlines()
            trace_string = '%s | %s' % (err_lines[-3], err_lines[-1])
            fault = jsonrpclib.Fault(-32603, 'Server error: %s' % trace_string)
            response = fault.response()
        if response == None:
            response = ''
        self.send_header("Content-type", "application/json-rpc")
        self.send_header("Content-length", str(len(response)))
        self.end_headers()
        self.wfile.write(response)
        self.wfile.flush()
        self.connection.shutdown(1)

class SimpleJSONRPCServer(SocketServer.TCPServer, SimpleJSONRPCDispatcher):

    allow_reuse_address = True

    def __init__(self, addr, requestHandler=SimpleJSONRPCRequestHandler,
                 logRequests=True, encoding=None, bind_and_activate=True):
        self.logRequests = logRequests
        SimpleJSONRPCDispatcher.__init__(self, encoding)
        # TCPServer.__init__ has an extra parameter on 2.6+, so
        # check Python version and decide on how to call it
        vi = sys.version_info
        # if python 2.5 and lower
        if vi[0] < 3 and vi[1] < 6:
            SocketServer.TCPServer.__init__(self, addr, requestHandler)
        else:
            SocketServer.TCPServer.__init__(self, addr, requestHandler,
                bind_and_activate)
        if fcntl is not None and hasattr(fcntl, 'FD_CLOEXEC'):
            flags = fcntl.fcntl(self.fileno(), fcntl.F_GETFD)
            flags |= fcntl.FD_CLOEXEC
            fcntl.fcntl(self.fileno(), fcntl.F_SETFD, flags)

class CGIJSONRPCRequestHandler(SimpleJSONRPCDispatcher):

    def __init__(self, encoding=None):
        SimpleJSONRPCDispatcher.__init__(self, encoding)

    def handle_jsonrpc(self, request_text):
        response = self._marshaled_dispatch(request_text)
        print 'Content-Type: application/json-rpc'
        print 'Content-Length: %d' % len(response)
        print
        sys.stdout.write(response)

    handle_xmlrpc = handle_jsonrpc

########NEW FILE########
__FILENAME__ = base_media_backend
import logging
import base64
import urllib2

class BaseMediaBackend(object):
    
    def __init__(self, host, port, username=None, password=None):
        self._host = host
        self._port = port
        self._username = username
        self._password = password
        
        self.log = logging.getLogger('airplayer')
        
    def _http_request(self, req):
        """
        Perform a http request andapply HTTP Basic authentication headers,
        if an username and password are supplied in settings.
        """
        if self._username and self._password:
            base64string = base64.encodestring('%s:%s' % (self._username, self._password))[:-1]
            req.add_header("Authorization", "Basic %s" % base64string)

        try:
            return urllib2.urlopen(req).read()
        except urllib2.URLError, e:
            clsname = self.__class__.__name__
            name = clsname.replace('MediaBackend', '')
            
            self.log.warning("Couldn't connect to %s at %s, are you sure it's running?", name, self.host_string())
            return None
    
    def host_string(self):
        """
        Convenience method, get a string with the current host and port.
        @return <host>:<port>
        """
        return '%s:%d' % (self._host, self._port)        
                
    def cleanup(self):
        """
        Called when airplayer is about to shutdown.
        """
        raise NotImplementedError
        
    def stop_playing(self):
        """
        Stop playing media.
        """
        raise NotImplementedError
        
    def show_picture(self, data):
        """
        Show a picture.
        @param data raw picture data.
        """
        raise NotImplementedError
        
    def play_movie(self, url):
        """
        Play a movie from the given location.
        """
        raise NotImplementedError

    def notify_started(self):
        """
        Notify the user that Airplayer has started.
        """
        raise NotImplementedError
        
    def pause(self):
        """
        Pause media playback.
        """
        raise NotImplementedError
    
    def play(self):
        """
        Play media
        """
        raise NotImplementedError
        
    def get_player_position(self):
        """
        Get the current videoplayer positon.
        @returns int current position, int total length
        """
        raise NotImplementedError
        
    def is_playing(self):
        """
        Return wether the backend is currently playing any media.
        
        @returns boolean
        """
        raise NotImplementedError
    
    def set_player_position(self, position):
        """
        Set the current videoplayer position.
        
        @param position integer in seconds
        """
        raise NotImplementedError
        
    def set_player_position_percentage(self, percentage_position):
        """
        Set current videoplayer position, in percentage.
        
        @param percentage_position float
        """
        raise NotImplementedError
        
    def set_start_position(self, percentage_position):
        """
        Play media from the given location
        
        @param percentage_position float
        """
        raise NotImplementedError
########NEW FILE########
__FILENAME__ = Boxee_media_backend
from Plex_media_backend import PlexMediaBackend

class BoxeeMediaBackend(PlexMediaBackend):
    """
    Boxee uses the same HTTP API as Plex.
    This is class is purely intended for (configuration) clarity.
    """
    pass
########NEW FILE########
__FILENAME__ = Plex_media_backend
import time
import utils

from XBMC_media_backend import XBMCMediaBackend

class PlexMediaBackend(XBMCMediaBackend):
    
    class InvalidApiResponseFormatException(Exception):
        pass
    
    _NOTHING_PLAYING = '[Nothing Playing]'
    
    def _http_api_request(self, command):
        response = super(PlexMediaBackend, self)._http_api_request(command)
        
        try:
            return self._parse_http_api_response(response)
        except PlexMediaBackend.InvalidApiResponseFormatException:
            """
            The API result was returned in an unexpected format,
            try to set the response format, and retry the request.
            """ 
            self._init_http_api()
            response = super(PlexMediaBackend, self)._http_api_request(command)
            return self._parse_http_api_response(response)
        
    def _init_http_api(self):
        """
        Set the responseformat so we can conveniently parse the result
        """
        response = self._http_api_request('SetResponseFormat(webheader;false;webfooter;false;opentag;)')
        
        if response['error']:
            raise Exception('Could not set HTTP API response format')    
    
    def _parse_http_api_response(self, response):
        """
        Parse http api responses.
        We except the following response format:
            - One or more lines with key/value pairs
            OR
            - A single line with a single string value (like 'OK')
        """
        result = { 'error' : False }
        
        if not response:
            result['error'] = True
            return result
        
        lines = response.splitlines()
        
        for line in lines:
            if not line:
                """
                Sometimes responses contain empty lines, ignore them
                """
                continue
                
            try:
                key, value = line.split(':', 1)
            except ValueError:
                if '<html>' in line:
                    """
                    The response format is not set yet.
                    """
                    raise PlexMediaBackend.InvalidApiResponseFormatException()
                
                if len(lines) == 1:
                    """
                    The response only contained a single line, with a single value.
                    Wrap it in a response key.
                    """
                    result['response'] = lines[0]
                    return result
                
                """
                The response is invalid, bail out.
                """
                raise Exception('Invalid response item: ', line)    
            
            result[key] = value
        
        if 'Error' in result:
            result['error'] = True
            
        return result
        
    def _set_start_position(self, position_percentage):
        """
        Run in thread.
        See set_start_position in BaseMediaBackend
        
        Max retries is 5, Plex seems to wait longer before media is played
        due to buffering.
        """
        for i in range(5):
            response = self.set_player_position_percentage(position_percentage)
            if 'error' in response and response['error']:
                self.log.debug('Setting start position failed: %s', response)
                time.sleep(1)
                continue

            self.log.debug('Setting start position succeeded')    
            return

        self.log.warning('Failed to set start position')
        
    def is_playing(self):
        """
        Determine if Plex is currently playing any media.
        
        Playing:
        A file is loaded and PlayStatus != Paused
        
        Not playing:
        No file is loaded, or a file is loaded and PlayStatus == Paused
        """
        response = self.get_player_state()
        
        if response['error']:
            return False
            
        if response['Filename'] == self._NOTHING_PLAYING:
            return False
                        
        return response['PlayStatus'] != 'Paused'
    
    def get_player_state(self):
        """
        Get information about the currently playing media.
        """
        return self._http_api_request('GetCurrentlyPlaying()')
        
    def pause(self):
        """
        Pause media playback.
        Plex doesn't have a seperate play and pause command so we'll
        have to check if there's currently playing any media.
        """
        
        if self.is_playing():
            self._pause()
    
    def play(self):
        """
        Airplay sometimes sends a play command twice and since XBMC
        does not offer a seperate play and pause command we'll have
        to check the current player state and choose an action
        accordingly.
        
        If an error is returned there's not currently playing any
        media, so we can send the play command.
        
        If there's a response and the videoplayer is currently playing
        we can also send the play command.
        """        
        if not self.is_playing():
            self._play()
        
    def get_player_position(self):
        """
        Get the current videoplayer positon.
        @returns int current position, int total length
        """
        response = self.get_player_state()
        
        if not response['error'] and 'Duration' in response:
            total_str = response['Duration']
            time_str = response['Time']
            
            if total_str and time_str:
                total = utils.duration_to_seconds(total_str)
                time = utils.duration_to_seconds(time_str)
            
                return time, total
            
        return None, None    
    
    def set_player_position(self, position):
        """
        Set the current videoplayer position.
        
        Plex doesn't support seeking in seconds, so calculate a percentage
        for the given position first.
        
        @param position integer in seconds
        """
        
        time, total = self.get_player_position()
        
        if total:
            percentage = float(position) / float(total) * 100
            self.log.debug('Position: %d total: %d percentage: %f', position, total, percentage)
            
            self.set_player_position_percentage(percentage)
        
    def set_player_position_percentage(self, percentage_position):
        """
        Set current videoplayer position, in percentage.
        
        @param percentage_position float
        """
        return self._http_api_request('SeekPercentage(%f)' % percentage_position)
########NEW FILE########
__FILENAME__ = XBMC_media_backend
import urllib2
import urllib
import time
import thread
import tempfile
import shutil
import os

import lib.jsonrpclib as jsonrpclib
import utils

from base_media_backend import BaseMediaBackend

class XBMCMediaBackend(BaseMediaBackend):
    """
    The XBMC media backend uses a hybride Web_Server_HTTP_API / JSON-RPC API approach,
    since the Web_Server_HTTP_API is deprecated from XBMC Dharma (current stable).
    
    However, not all required methods are exposed through the JSON-RPC API, so in that
    cases the old HTTP API is used. In the future when the JSON-RPC is extended to expose
    all required methods, the HTTP API will not be used anymore.
    """
    
    def __init__(self, host, port, username=None, password=None):
        super(XBMCMediaBackend, self).__init__(host, port, username, password)
        
        self._last_wakeup = None
        self._jsonrpc = jsonrpclib.Server(self._jsonrpc_connection_string())
        self._TMP_DIR = tempfile.mkdtemp()
        
        """
        Make sure the folder is world readable, since XBMC might be running as a
        different user then Airplayer.
        
        As pointed out at https://github.com/PascalW/Airplayer/issues#issue/9
        """
        os.chmod(self._TMP_DIR, 0755)
        
        self.log.debug('TEMP DIR: %s', self._TMP_DIR)
    
    def _jsonrpc_connection_string(self):
        host_string = self.host_string()
        
        if self._username and self._password:
            """
            Unfortunately there's no other way to provide authentication credentials
            to jsonrpclib but in the url.
            """
            host_string = '%s:%s@%s' % (self._username, self._password, host_string)
            
        return 'http://%s/jsonrpc' % host_string    

    def _http_api_request(self, command):
        """
        Perform a request to the XBMC http api.
        @return raw request result or None in case of error
        """
        self._wake_screen()
        
        command = urllib.quote(command)
        url = 'http://%s/xbmcCmds/xbmcHttp?command=%s' % (self.host_string(), command)

        req = urllib2.Request(url)
        return self._http_request(req)
        
    def _jsonrpc_api_request(self, method, *args):
        """
        Wrap calls to the json-rpc proxy to conveniently handle exceptions.
        @return response, exception
        """
        response = None
        exception = None
        
        try:
            self._wake_screen()    
            response = self._jsonrpc._request(method, args)
        except jsonrpclib.ProtocolError, e:
            """
            Protocol errors usually means a method could not be executed because
            for example a seek is requested when there's no movie playing.
            """
            self.log.debug('Caught protocol error %s', e)
            exception = e
        except Exception, e:
            exception = e
            
        return response, exception
        
    def _send_notification(self, title, message):
        """
        Sends a notification to XBMC, this is displayed to the user as a popup.
        """
        self._http_api_request('ExecBuiltIn(Notification(%s, %s))' % (title, message))
        
    def _set_start_position(self, position_percentage):
        for i in range(3):
            response, error = self.set_player_position_percentage(position_percentage)
            if error:
                self.log.debug('Setting start position failed: %s', error)
                time.sleep(1)
                continue

            self.log.debug('Setting start position succeeded')    
            return

        self.log.warning('Failed to set start position')
        
    def _wake_screen(self):
        """
        XBMC doesn't seem to wake the screen when the screen is dimmed and a slideshow is started.
        See http://trac.xbmc.org/ticket/10883.
        
        There isn't a real method to wake the screen, so we'll just send a bogus request which does
        nothing, but does wake up the screen.
        
        For performance concerns, we only send this request once every minute.
        """
        now = time.time()
        
        if not self._last_wakeup or now - self._last_wakeup > 60:
            self._last_wakeup = now
            
            self.log.debug('Sending wake event')
            self._http_api_request('sendkey(ACTION_NONE)')
        
    def cleanup(self):
        shutil.rmtree(self._TMP_DIR)                          
        
    def stop_playing(self):
        """
        Stop playing media.
        """
        self._http_api_request('stop')
        
    def show_picture(self, data):
        """
        Show a picture.
        @param data raw picture data.
        Note I'm using the XBMC PlaySlideshow command here, giving the pictures path as an argument.
        This is a workaround for the fact that calling the XBMC ShowPicture method more than once seems
        to crash XBMC?
        """
        utils.clear_folder(self._TMP_DIR)
        filename = 'picture%d.jpg' % int(time.time())
        path = os.path.join(self._TMP_DIR, filename)
        
        """
        write mode 'b' is needed for Windows compatibility, since we're writing a binary file here.
        """
        f = open(path, 'wb')
        f.write(data)
        f.close()
        
        self._http_api_request('PlaySlideshow(%s)' % self._TMP_DIR)
        
    def play_movie(self, url):
        """
        Play a movie from the given location.
        """
        self._http_api_request('PlayFile(%s)' % url)

    def notify_started(self):
        """
        Notify the user that Airplayer has started.
        """
        self._send_notification('Airplayer', 'Airplayer started')
        
    def is_playing(self):
        response, error = self.get_player_state('videoplayer')
        
        if error:
            return False
            
        return not response['paused']
    
    def get_player_state(self, player):
        """
        Return the current state for the given player. 
        @param player a valid player (e.g. videoplayer, audioplayer etc)
        """
        return self._jsonrpc_api_request('%s.state' % player)
        
    def _pause(self):
        """
        Play/Pause media playback.
        """
        self._http_api_request('Pause')       
        
    def pause(self):
        """
        Pause media playback.
        XBMC doesn't have a seperate play and pause command so we'll
        have to check if there's currently playing any media.
        """
        response, error = self.get_player_state('videoplayer')
        
        if response and not response['paused']:
            self._pause()
    
    def _play(self):
        """
        XBMC doesn't have a real play command, just play/pause.
        This method is purely for code readability.
        """
        self._pause()        
    
    def play(self):
        """
        Airplay sometimes sends a play command twice and since XBMC
        does not offer a seperate play and pause command we'll have
        to check the current player state and choose an action
        accordingly.
        
        If an error is returned there's not currently playing any
        media, so we can send the play command.
        
        If there's a response and the videoplayer is currently playing
        we can also send the play command.
        """
        response, error = self.get_player_state('videoplayer')
        
        if error or response and response['paused']:
            self._play()
        
    def get_player_position(self):
        """
        Get the current videoplayer positon.
        @returns int current position, int total length
        """
        response, error = self._jsonrpc_api_request('videoplayer.gettime')
        
        if not error:
            if 'time' in response:
                return int(response['time']), int(response['total'])

        return None, None
    
    def set_player_position(self, position):
        """
        Set the current videoplayer position.
        
        @param position integer in seconds
        """
        self._jsonrpc_api_request('videoplayer.seektime', position)
        
    def set_player_position_percentage(self, percentage_position):
        """
        Set current videoplayer position, in percentage.
        
        @param percentage_position float
        """
        return self._jsonrpc_api_request('videoplayer.seekpercentage', percentage_position)
        
    def set_start_position(self, percentage_position):
        """
        It can take a few seconds before XBMC starts playing the movie
        and accepts seeking, so we'll wait a bit before sending this command.
        This is a bit dirty, but it's the best I could come up with.
        
        @param percentage_position float
        """
        if percentage_position:
            thread.start_new_thread(self._set_start_position, (percentage_position,))

########NEW FILE########
__FILENAME__ = pidfile
# -*- coding: utf-8 -
#
# This file is part of gunicorn released under the MIT license. 
# See the NOTICE for more information.

from __future__ import with_statement

import errno
import os
import tempfile


class Pidfile(object):
    """\
    Manage a PID file. If a specific name is provided
    it and '"%s.oldpid" % name' will be used. Otherwise
    we create a temp file using os.mkstemp.
    """

    def __init__(self, fname):
        self.fname = fname
        self.pid = None
        
    def create(self, pid):
        oldpid = self.validate()
        if oldpid:
            if oldpid == os.getpid():
                return
            raise RuntimeError("Already running on PID %s " \
                "(or pid file '%s' is stale)" % (os.getpid(), self.fname))

        self.pid = pid
        
        # Write pidfile
        fdir = os.path.dirname(self.fname)
        if fdir and not os.path.isdir(fdir):
            raise RuntimeError("%s doesn't exist. Can't create pidfile." % fdir)
        fd, fname = tempfile.mkstemp(dir=fdir)
        os.write(fd, "%s\n" % self.pid)
        if self.fname:
            os.rename(fname, self.fname)
        else:
            self.fname = fname
        os.close(fd)

        # set permissions to -rw-r--r-- 
        os.chmod(self.fname, 420)
        
    def rename(self, path):
        self.unlink()
        self.fname = path
        self.create(self.pid)
        
    def unlink(self):
        """ delete pidfile"""
        try:
            with open(self.fname, "r") as f:
                pid1 =  int(f.read() or 0)

            if pid1 == self.pid:
                os.unlink(self.fname)
        except:
            pass
       
    def validate(self):
        """ Validate pidfile and make it stale if needed"""
        if not self.fname:
            return
        try:
            with open(self.fname, "r") as f:
                wpid = int(f.read() or 0)

                if wpid <= 0:
                    return

                try:
                    os.kill(wpid, 0)
                    return wpid
                except OSError, e:
                    if e[0] == errno.ESRCH:
                        return
                    raise
        except IOError, e:
            if e[0] == errno.ENOENT:
                return
            raise

########NEW FILE########
__FILENAME__ = protocol_handler
import logging
import appletv

import lib.biplist

import tornado.httpserver
import tornado.ioloop
import tornado.web
from tornado.httputil import HTTPHeaders

log = logging.getLogger('airplayer')

class AirplayProtocolHandler(object):
    
    def __init__(self, port, media_backend):
        self._http_server = None
        self._media_backend = media_backend
        self._port = port
    
    def start(self):
        handlers = {
            '/reverse' : AirplayProtocolHandler.ReverseHandler,
            '/play' : AirplayProtocolHandler.PlayHandler,
            '/scrub' : AirplayProtocolHandler.ScrubHandler,
            '/rate' : AirplayProtocolHandler.RateHandler,
            '/photo' : AirplayProtocolHandler.PhotoHandler,
            '/authorize' : AirplayProtocolHandler.AuthorizeHandler,
            '/server-info' : AirplayProtocolHandler.ServerInfoHandler,
            '/slideshow-features' : AirplayProtocolHandler.SlideshowFeaturesHandler,
            '/playback-info' : AirplayProtocolHandler.PlaybackInfoHandler,
            '/stop' : AirplayProtocolHandler.StopHandler,
        }
        
        app_handlers = [(url, handlers[url], dict(media_backend=self._media_backend)) for url in handlers.keys()] 
        application = tornado.web.Application(app_handlers)

        self._http_server = tornado.httpserver.HTTPServer(application)
        self._http_server.listen(self._port)

        try:
            tornado.ioloop.IOLoop.instance().start()
        except:
            pass
        finally:
            log.debug('Cleaning up')
            self._media_backend.cleanup()
        
    def stop(self):
        try:
            tornado.ioloop.IOLoop.instance().stop()
            self._http_server.stop()
        except:
            pass
    
    class BaseHandler(tornado.web.RequestHandler):
        """
        Base request handler, all other handlers should inherit from this class.

        Provides some logging and media backend assignment.
        """

        def initialize(self, media_backend):
            self._media_backend = media_backend  

        def prepare(self):
            log.debug('%s %s', self.request.method, self.request.uri)

    class ReverseHandler(BaseHandler):
        """
        Handler for /reverse requests.

        The reverse command is the first command sent by Airplay,
        it's a handshake.
        """

        def post(self):
            self.set_status(101)
            self.set_header('Upgrade', 'PTTH/1.0')
            self.set_header('Connection', 'Upgrade')

    class PlayHandler(BaseHandler):
        """
        Handler for /play requests.

        Contains a header like format in the request body which should contain a
        Content-Location and optionally a Start-Position.
        """

        @tornado.web.asynchronous
        def post(self):
            """
            Immediately finish this request, no need for the client to wait for
            backend communication.
            """
            self.finish()
            
            if self.request.headers.get('Content-Type', None) == 'application/x-apple-binary-plist':
                body = lib.biplist.readPlistFromString(self.request.body)
            else:
                body = HTTPHeaders.parse(self.request.body)    

            if 'Content-Location' in body:
                url = body['Content-Location']
                log.debug('Playing %s', url)
                
                self._media_backend.play_movie(url)

                if 'Start-Position' in body:
                    """ 
                    Airplay sends start-position in percentage from 0 to 1.
                    Media backends expect a percentage from 0 to 100.
                    """
                    try:
                        str_pos = body['Start-Position']
                    except ValueError:
                        log.warning('Invalid start-position supplied: ', str_pos)
                    else:        
                        position_percentage = float(str_pos) * 100
                        self._media_backend.set_start_position(position_percentage)


    class ScrubHandler(BaseHandler):
        """
        Handler for /scrub requests.

        Used to perform seeking (POST request) and to retrieve current player position (GET request).
        """       

        def get(self):
            """
            Will return None, None if no media is playing or an error occures.
            """
            position, duration = self._media_backend.get_player_position()

            """
            Should None values be returned just default to 0 values.
            """
            if not position:
                duration = position = 0

            body = 'duration: %f\r\nposition: %f\r\n' % (duration, position)
            self.write(body)

        @tornado.web.asynchronous
        def post(self):
            """
            Immediately finish this request, no need for the client to wait for
            backend communication.
            """
            self.finish()

            if 'position' in self.request.arguments:
                try:
                    str_pos = self.request.arguments['position'][0]
                    position = int(float(str_pos))
                except ValueError:
                    log.warn('Invalid scrub value supplied: ', str_pos)
                else:       
                    self._media_backend.set_player_position(position)

    class RateHandler(BaseHandler):    
        """
        Handler for /rate requests.

        The rate command is used to play/pause media.
        A value argument should be supplied which indicates media should be played or paused.

        0.000000 => pause
        1.000000 => play
        """

        @tornado.web.asynchronous
        def post(self): 
            """
            Immediately finish this request, no need for the client to wait for
            backend communication.
            """
            self.finish()

            if 'value' in self.request.arguments:
                play = bool(float(self.request.arguments['value'][0]))

                if play:
                    self._media_backend.play()
                else:
                    self._media_backend.pause()    

    class PhotoHandler(BaseHandler):   
        """
        Handler for /photo requests.

        RAW JPEG data is contained in the request body.
        """     

        @tornado.web.asynchronous
        def put(self):           
            """
            Immediately finish this request, no need for the client to wait for
            backend communication.
            """
            self.finish()

            if self.request.body:        
                self._media_backend.show_picture(self.request.body)

    class AuthorizeHandler(BaseHandler):
        """
        Handler for /authorize requests.

        This is used to handle DRM authorization.
        We currently don't support DRM protected media.
        """

        def prepare(self):
            log.warning('Trying to play DRM protected, this is currently unsupported.')
            log.debug('Got an authorize %s request', self.request.method)
            log.debug('Authorize request info: %s %s %s', self.request.headers, self.request.arguments, self.request.body)

        def get(self):
            pass

        def post(self):
            pass    

    class StopHandler(BaseHandler):
        """
        Handler for /stop requests.

        Sent when media playback should be stopped.
        """

        def post(self):
            self._media_backend.stop_playing()
            
    class ServerInfoHandler(BaseHandler):
        """
        Handler for /server-info requests.
        
        Usage currently unknown.
        Available from IOS 4.3.
        """        
        
        def get(self):
            self.set_header('Content-Type', 'text/x-apple-plist+xml')
            self.write(appletv.SERVER_INFO)
            
    class SlideshowFeaturesHandler(BaseHandler):
        """
        Handler for /slideshow-features requests.

        Usage currently unknown.
        Available from IOS 4.3.
        """        

        def get(self):
            """
            I think slideshow effects should be implemented by the Airplay device.
            The currently supported media backends do not support this.
            
            We'll just ignore this request, that'll enable the simple slideshow without effects.
            """
            pass
            
    class PlaybackInfoHandler(BaseHandler):
        """
        Handler for /playback-info requests.
        """
        
        def get(self):
            playing = self._media_backend.is_playing()
            position, duration = self._media_backend.get_player_position()
            
            if not position:
                position = duration = 0
            else:    
                position = float(position)
                duration = float(duration)
            
            body = appletv.PLAYBACK_INFO % (duration, duration, position, int(playing), duration)
            
            self.set_header('Content-Type', 'text/x-apple-plist+xml')
            self.write(body)

########NEW FILE########
__FILENAME__ = settings
"""
Port used by Airplayer.
You should only need to change this in case port 6002 is already
in use on your machine by other software.
"""
AIRPLAYER_PORT = 6002

"""
Set your media backend.
Supported media backends are XBMC, Plex and Boxee.
"""
MEDIA_BACKEND = 'XBMC'

"""
Default ports:
XBMC: 8080
Plex: 3000
Boxee: 8800
"""
MEDIA_BACKEND_HOST = '127.0.0.1'
MEDIA_BACKEND_PORT = 8080

"""
If your media backend doesn't require authentication,
set this options to None.

Example:
MEDIA_BACKEND_USERNAME = None
MEDIA_BACKEND_PASSWORD = None
"""
MEDIA_BACKEND_USERNAME = 'username'
MEDIA_BACKEND_PASSWORD = 'password'

"""
This is the name by which Airplayer will identify itself to other Airplay
devices.
Leave this to None for auto-detection, provide a string to override your
default hostname.
Example:
AIRPLAY_HOSTNAME = 'My XBMC player'
"""
AIRPLAY_HOSTNAME = None

"""
Debug mode, set to False to disable debug logging.
"""
DEBUG = False
########NEW FILE########
__FILENAME__ = utils
import os
import platform
try:
    import resource
except ImportError:
    """
    Not available on Windows
    """
    pass    

def clear_folder(folder):
    """
    Remove the given folder's content.
    """
    for the_file in os.listdir(folder):
        file_path = os.path.join(folder, the_file)
        try:
            if os.path.isfile(file_path):
                os.unlink(file_path)
        except Exception, e:
            print e
            
def clean_hostname(hostname):
    """
    Remove the .local appendix of a hostname.
    """
    if hostname:
        return hostname.replace('.local', '')
        
def duration_to_seconds(duration_str):
    """
    Acceptable formats are: "MM:SS", "HH:MM" and "HH:MM:SS".
    """
    values = duration_str.split(':')
    
    if len(values) == 1:
        raise Exception('Invalid value supplied: %s', duration_str)
    
    seconds = 0
    
    for i, val in enumerate(reversed(values)):        
        val = int(val) * pow(60, i)
        seconds = seconds + val
        
    return seconds        
        
"""
The following code is originating from Gunicorn:
https://github.com/benoitc/gunicorn
"""        
        
MAXFD = 1024
if (hasattr(os, "devnull")):
   REDIRECT_TO = os.devnull
else:
   REDIRECT_TO = "/dev/null"        
        
def get_maxfd():
    maxfd = resource.getrlimit(resource.RLIMIT_NOFILE)[1]
    if (maxfd == resource.RLIM_INFINITY):
        maxfd = MAXFD
    return maxfd
            
def daemonize():
    """
    Currently only implemented for Unix like systems.
    """
    if platform.system() == 'Windows':
        raise Exception('Daemonizing is currently not supported on Windows.')
       
    if os.fork() == 0: 
        os.setsid()
        if os.fork():
            os._exit(0)
    else:
        os._exit(0)
                
    os.umask(0)
    maxfd = get_maxfd()

    # Iterate through and close all file descriptors.
    for fd in range(0, maxfd):
        try:
            os.close(fd)
        except OSError:	# ERROR, fd wasn't open to begin with (ignored)
            pass

    os.open(REDIRECT_TO, os.O_RDWR)
    os.dup2(0, 1)
    os.dup2(0, 2)    
########NEW FILE########
