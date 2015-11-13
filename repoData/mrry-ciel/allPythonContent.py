__FILENAME__ = cli
# Copyright (c) 2011 Derek Murray <Derek.Murray@cl.cam.ac.uk>
#
# Permission to use, copy, modify, and distribute this software for any
# purpose with or without fee is hereby granted, provided that the above
# copyright notice and this permission notice appear in all copies.
#
# THE SOFTWARE IS PROVIDED "AS IS" AND THE AUTHOR DISCLAIMS ALL WARRANTIES
# WITH REGARD TO THIS SOFTWARE INCLUDING ALL IMPLIED WARRANTIES OF
# MERCHANTABILITY AND FITNESS. IN NO EVENT SHALL THE AUTHOR BE LIABLE FOR
# ANY SPECIAL, DIRECT, INDIRECT, OR CONSEQUENTIAL DAMAGES OR ANY DAMAGES
# WHATSOEVER RESULTING FROM LOSS OF USE, DATA OR PROFITS, WHETHER IN AN
# ACTION OF CONTRACT, NEGLIGENCE OR OTHER TORTIOUS ACTION, ARISING OUT OF
# OR IN CONNECTION WITH THE USE OR PERFORMANCE OF THIS SOFTWARE.
import ciel.runtime.master
import ciel.runtime.util.start_job
import ciel.runtime.util.run_script
import ciel.config
from ciel import CIEL_VERSION_STRING
import sys

def start_master(args):
    ciel.runtime.master.main(args)

def start_worker(args):
    ciel.runtime.worker.main(args)

def run_job(args):
    ciel.runtime.util.start_job.main(args)

def run_jar(args):
    ciel.runtime.util.start_job.jar(args)

def run_sw(args):
    ciel.runtime.util.run_script.main(args)

def config(args):
    ciel.config.main(args)

def show_help(args):
    print >>sys.stderr, "usage: ciel COMMAND [ARGS]"
    print >>sys.stderr
    print >>sys.stderr, "The main Ciel commands are:"
    for command, _, description in default_command_list:
        if description is not None:
            print >>sys.stderr, '   %s %s' % (command.ljust(10), description)

def version():
    print >>sys.stderr, CIEL_VERSION_STRING

default_command_list = [('master',    start_master, "Start running a CIEL master"),
                        ('worker',    start_worker, "Start running a CIEL worker"),
                        ('run',       run_job,      "Run a CIEL job"),
                        ('java',      run_jar,      "Run a Java-based CIEL job"),
                        ('sw',        run_sw,       "Run a Skywriting script"),
                        ('config',    config,       "Configure CIEL"),
                        ('help',      show_help,    "Display this message"),
                        ('--version', version,      None)]

default_command_map = dict([(x, (y, z)) for x, y, z in default_command_list])

def main():

    my_args = sys.argv[:]

    if len(my_args) < 2:
        func = show_help
        exit_code = -1
    else:

        command = my_args.pop(1)
        try:
            func, _ = default_command_map[command]
            exit_code = 0
        except KeyError:
            print >>sys.stderr, 'Unrecognised command: %s' % command
            func = show_help
            exit_code = -1

    func(my_args)
    sys.exit(exit_code)
    

if __name__ == '__main__':
    main()

########NEW FILE########
__FILENAME__ = config
# Copyright (c) 2011 Derek Murray <Derek.Murray@cl.cam.ac.uk>
#
# Permission to use, copy, modify, and distribute this software for any
# purpose with or without fee is hereby granted, provided that the above
# copyright notice and this permission notice appear in all copies.
#
# THE SOFTWARE IS PROVIDED "AS IS" AND THE AUTHOR DISCLAIMS ALL WARRANTIES
# WITH REGARD TO THIS SOFTWARE INCLUDING ALL IMPLIED WARRANTIES OF
# MERCHANTABILITY AND FITNESS. IN NO EVENT SHALL THE AUTHOR BE LIABLE FOR
# ANY SPECIAL, DIRECT, INDIRECT, OR CONSEQUENTIAL DAMAGES OR ANY DAMAGES
# WHATSOEVER RESULTING FROM LOSS OF USE, DATA OR PROFITS, WHETHER IN AN
# ACTION OF CONTRACT, NEGLIGENCE OR OTHER TORTIOUS ACTION, ARISING OUT OF
# OR IN CONNECTION WITH THE USE OR PERFORMANCE OF THIS SOFTWARE.

import ConfigParser
import os
import sys
import optparse

# CIEL will consult a configuration file stored as '~/.ciel'
# Attempts to set the config will update such a file.
CIEL_USER_CONFIG = os.path.expanduser('~/.ciel')
CIEL_GLOBAL_CONFIG = '/etc/ciel.conf'

_cp = ConfigParser.SafeConfigParser()
_cp.read([CIEL_USER_CONFIG, CIEL_GLOBAL_CONFIG])

def get(section, key, default=None):
    try:
        return _cp.get(section, key)
    except:
        return default

def set(section, key, value):
    try:
        _cp.set(section, key, value)
    except ConfigParser.NoSectionError:
        _cp.add_section(section)
        _cp.set(section, key, value)
    return

def write():
    with open(os.path.expanduser('~/.ciel'), 'w') as f:
        _cp.write(f)

def main(my_args=sys.argv):

    def cli_get(option, opt_str, value, *args, **kwargs):
        section, key = value.split('.')
        print get(section, key)

    def cli_set(option, opt_str, value, *args, **kwargs):
        section_key, value = value
        section, key = section_key.split('.')
        set(section, key, value)
        write()

    parser = optparse.OptionParser(usage='Usage: ciel config [options]')
    parser.add_option("-g", "--get", action="callback", nargs=1, callback=cli_get, help="Display the value of a configuration option", metavar="SECTION.KEY", type="str")
    parser.add_option("-s", "--set", action="callback", nargs=2, callback=cli_set, help="Update the value of a configuration option (saved in %s)" % CIEL_USER_CONFIG, metavar="SECTION.KEY VALUE", type="str")

    if len(my_args) < 2:
        parser.print_help()
        sys.exit(-1)

    (options, args) = parser.parse_args(args=my_args)

########NEW FILE########
__FILENAME__ = logger
# Copyright (c) 2011 Derek Murray <Derek.Murray@cl.cam.ac.uk>
#
# Permission to use, copy, modify, and distribute this software for any
# purpose with or without fee is hereby granted, provided that the above
# copyright notice and this permission notice appear in all copies.
#
# THE SOFTWARE IS PROVIDED "AS IS" AND THE AUTHOR DISCLAIMS ALL WARRANTIES
# WITH REGARD TO THIS SOFTWARE INCLUDING ALL IMPLIED WARRANTIES OF
# MERCHANTABILITY AND FITNESS. IN NO EVENT SHALL THE AUTHOR BE LIABLE FOR
# ANY SPECIAL, DIRECT, INDIRECT, OR CONSEQUENTIAL DAMAGES OR ANY DAMAGES
# WHATSOEVER RESULTING FROM LOSS OF USE, DATA OR PROFITS, WHETHER IN AN
# ACTION OF CONTRACT, NEGLIGENCE OR OTHER TORTIOUS ACTION, ARISING OUT OF
# OR IN CONNECTION WITH THE USE OR PERFORMANCE OF THIS SOFTWARE.
import logging
import sys
import datetime
import rfc822
import time

class CielLogger:
    
    def __init__(self, logger_root='ciel'):
        self.logger_root = logger_root
        self.log = logging.getLogger(self.logger_root)
        self.log.setLevel(logging.ERROR)
    
        log_handler = logging.StreamHandler(sys.stderr)
        self.log.addHandler(log_handler)
    
    def setLevel(self, lvl):
        self.log.setLevel(lvl)
    
    def __call__(self, *args, **kwargs):
        """Write to the error log.
        
        This is not just for errors! Applications may call this at any time
        to log application-specific information.
        """
        return self.error(*args, **kwargs)
    
    def error(self, msg='', context='', severity=logging.INFO, traceback=False):
        """Write to the error log.
        
        This is not just for errors! Applications may call this at any time
        to log application-specific information.
        """
        if traceback:
            msg += format_exc()
        self.log.log(severity, ' '.join((self.time(), context, msg)))
    
    def time(self):
        return '[%f]' % (lambda t: (time.mktime(t.timetuple()) + t.microsecond / 1e6))(datetime.datetime.now())
        #"""Return now() in Apache Common Log Format (no timezone)."""
        #now = datetime.datetime.now()
        #month = rfc822._monthnames[now.month - 1].capitalize()
        #return ('[%02d/%s/%04d:%02d:%02d:%02d]' %
        #        (now.day, month, now.year, now.hour, now.minute, now.second))
    
def format_exc(exc=None):
    """Return exc (or sys.exc_info if None), formatted."""
    if exc is None:
        exc = sys.exc_info()
    if exc == (None, None, None):
        return ""
    import traceback
    return "".join(traceback.format_exception(*exc))
########NEW FILE########
__FILENAME__ = io_helpers

from StringIO import StringIO
import os
import tempfile
import simplejson
import struct
from ciel.public.references import json_decode_object_hook, SWReferenceJSONEncoder

class MaybeFile:

    def __init__(self, threshold_bytes=1024, filename=None, open_callback=None):
        self.real_fp = None
        self.filename = filename
        self.str = None
        self.open_callback = open_callback
        self.bytes_written = 0
        self.fake_fp = StringIO()
        self.threshold_bytes = threshold_bytes

    def write(self, str):
        if self.real_fp is not None:
            self.real_fp.write(str)
        else:
            if self.bytes_written + len(str) > self.threshold_bytes:
                if self.open_callback is not None:
                    self.real_fp = self.open_callback()
                elif self.filename is None:
                    self.fd, self.filename = tempfile.mkstemp()
                    self.real_fp = os.fdopen(self.fd, "w")
                else:
                    self.real_fp = open(self.filename, "w")
                self.real_fp.write(self.fake_fp.getvalue())
                self.real_fp.write(str)
                self.fake_fp.close()
                self.fake_fp = None
            else:
                self.fake_fp.write(str)
        self.bytes_written += len(str)

    def __enter__(self):
        return self

    def __exit__(self, extype, exvalue, extraceback):
        if self.real_fp is not None:
            self.real_fp.close()
        if self.fake_fp is not None:
            self.str = self.fake_fp.getvalue()
            self.fake_fp.close()
            
def write_framed_json(obj, fp):
    json_string = simplejson.dumps(obj, cls=SWReferenceJSONEncoder)
    fp.write(struct.pack('!I', len(json_string)))
    fp.write(json_string)
    fp.flush()
    
def read_framed_json(fp):
    request_len, = struct.unpack_from('!I', fp.read(4))
    request_string = fp.read(request_len)
    return simplejson.loads(request_string, object_hook=json_decode_object_hook)


########NEW FILE########
__FILENAME__ = references
# Copyright (c) 2010 Derek Murray <derek.murray@cl.cam.ac.uk>
#
# Permission to use, copy, modify, and distribute this software for any
# purpose with or without fee is hereby granted, provided that the above
# copyright notice and this permission notice appear in all copies.
#
# THE SOFTWARE IS PROVIDED "AS IS" AND THE AUTHOR DISCLAIMS ALL WARRANTIES
# WITH REGARD TO THIS SOFTWARE INCLUDING ALL IMPLIED WARRANTIES OF
# MERCHANTABILITY AND FITNESS. IN NO EVENT SHALL THE AUTHOR BE LIABLE FOR
# ANY SPECIAL, DIRECT, INDIRECT, OR CONSEQUENTIAL DAMAGES OR ANY DAMAGES
# WHATSOEVER RESULTING FROM LOSS OF USE, DATA OR PROFITS, WHETHER IN AN
# ACTION OF CONTRACT, NEGLIGENCE OR OTHER TORTIOUS ACTION, ARISING OUT OF
# OR IN CONNECTION WITH THE USE OR PERFORMANCE OF THIS SOFTWARE.

import simplejson
import base64
import re

class SWRealReference:
    
    def as_tuple(self):
        pass

    def as_protobuf(self):
        pass
    
    def is_consumable(self):
        return True

    def as_future(self):
        # XXX: Should really make id a field of RealReference.
        return SW2_FutureReference(self.id)
    
def protobuf_to_netloc(netloc):
    return '%s:%d' % (netloc.hostname, netloc.port)

class SWErrorReference(SWRealReference):
    
    def __init__(self, id, reason, details):
        self.id = id
        self.reason = reason
        self.details = details

    def as_tuple(self):
        return ('err', self.id, self.reason, self.details)

class SW2_FutureReference(SWRealReference):
    """
    Used as a reference to a task that hasn't completed yet. The identifier is in a
    system-global namespace, and may be passed to other tasks or returned from
    tasks.
    """
        
    def __init__(self, id):
        self.id = id
    
    def is_consumable(self):
        return False
    
    def as_future(self):
        return self
    
    def as_tuple(self):
        return ('f2', str(self.id))

    def __str__(self):
        return "<FutureRef: %s...>" % self.id[:10]

    def __repr__(self):
        return 'SW2_FutureReference(%s)' % (repr(self.id), )
        
class SW2_ConcreteReference(SWRealReference):
        
    def __init__(self, id, size_hint=None, location_hints=None):
        self.id = id
        self.size_hint = size_hint
        if location_hints is not None:
            self.location_hints = set(location_hints)
        else:
            self.location_hints = set()
        
    def add_location_hint(self, netloc):
        self.location_hints.add(netloc)
        
    def combine_with(self, ref):
        """Add the location hints from ref to this object."""
        if isinstance(ref, SW2_ConcreteReference):
            assert ref.id == self.id
            
            # We attempt to upgrade the size hint if more information is
            # available from the merging reference.
            if self.size_hint is None:
                self.size_hint = ref.size_hint
            
            # We calculate the union of the two sets of location hints.
            self.location_hints.update(ref.location_hints)
        
    def as_tuple(self):
        return('c2', str(self.id), self.size_hint, list(self.location_hints))

    def __str__(self):
        return "<ConcreteRef: %s..., length %s, held in %d locations>" % (self.id[:10], str(self.size_hint) if self.size_hint is not None else "Unknown", len(self.location_hints))
        
    def __repr__(self):
        return 'SW2_ConcreteReference(%s, %s, %s)' % (repr(self.id), repr(self.size_hint), repr(self.location_hints))

class SW2_SweetheartReference(SW2_ConcreteReference):

    def __init__(self, id, sweetheart_netloc, size_hint=None, location_hints=None):
        SW2_ConcreteReference.__init__(self, id, size_hint, location_hints)
        self.sweetheart_netloc = sweetheart_netloc
        
    @staticmethod
    def from_concrete(ref, sweet_netloc):
        assert isinstance(ref, SW2_ConcreteReference)
        return SW2_SweetheartReference(ref.id, sweet_netloc, ref.size_hint, ref.location_hints)
        
    def combine_with(self, ref):
        """Add the location hints from ref to this object."""
        SW2_ConcreteReference.combine_with(self, ref)
        if isinstance(ref, SW2_SweetheartReference):
            self.sweetheart_netloc = ref.sweetheart_netloc
        
    def as_tuple(self):
        return('<3', str(self.id), self.sweetheart_netloc, self.size_hint, list(self.location_hints))
        
    def __repr__(self):
        return 'SW2_SweetheartReference(%s, %s, %s, %s)' % (repr(self.id), repr(self.sweetheart_netloc), repr(self.size_hint), repr(self.location_hints))
        
class SW2_FixedReference(SWRealReference):
    
    def __init__(self, id, fixed_netloc):
        self.id = id
        self.fixed_netloc = fixed_netloc
    
    def combine_with(self, ref):
        pass
    
    def as_tuple(self):
        return ('fx', str(self.id), self.fixed_netloc)
        
    def __str__(self):
        return "<FixedRef: %s, stored at %s>" % (self.id[:10], self.fixed_netloc)
        
    def __repr__(self):
        return 'SW2_FixedReference(%s, %s)' % (repr(self.id), repr(self.fixed_netloc))
        
class SW2_StreamReference(SWRealReference):
    
    def __init__(self, id, location_hints=None):
        self.id = id
        if location_hints is not None:
            self.location_hints = set(location_hints)
        else:
            self.location_hints = set()
        
    def add_location_hint(self, netloc):
        self.location_hints.add(netloc)

    def combine_with(self, ref):
        """Add the location hints from ref to this object."""
        if isinstance(ref, SW2_StreamReference):
            assert ref.id == self.id
            
            # We attempt to upgrade the size hint if more information is
            # available from the merging reference.
            
            # We calculate the union of the two sets of location hints.
            self.location_hints.update(ref.location_hints)
        
    def as_tuple(self):
        return('s2', str(self.id), list(self.location_hints))

    def __str__(self):
        return "<StreamRef: %s..., held in %d locations>" % (self.id[:10], len(self.location_hints))
        
    def __repr__(self):
        return 'SW2_StreamReference(%s, %s)' % (repr(self.id), repr(self.location_hints))

class SW2_SocketStreamReference(SW2_StreamReference):

    def __init__(self, id, location_hint, socket_port):
        SW2_StreamReference.__init__(self, id, [location_hint])
        self.socket_port = socket_port
        self.socket_netloc = location_hint

    def as_tuple(self):
        return ('ss2', str(self.id), self.socket_netloc, self.socket_port)

    def __str__(self):
        return "<SocketStreamRef: %s..., at %s(:%s)>" % (self.id[:10], self.socket_netloc, self.socket_port)

    def __repr__(self):
        return 'SW2_SocketStreamReference(%s, %s, %s)' % (repr(self.id), repr(self.socket_netloc), repr(self.socket_port))

class SW2_TombstoneReference(SWRealReference):
    
    def __init__(self, id, netlocs=None):
        self.id = id
        if netlocs is not None:
            self.netlocs = set(netlocs)
        else:
            self.netlocs = set()
            
    def is_consumable(self):
        return False        
    
    def add_netloc(self, netloc):
        self.netlocs.add(netloc)
        
    def as_tuple(self):
        return ('t2', str(self.id), list(self.netlocs))

    def __str__(self):
        return "<Tombstone: %s...>" % self.id[:10]

    def __repr__(self):
        return 'SW2_TombstoneReference(%s, %s)' % (repr(self.id), repr(self.netlocs))

class SW2_CompletedReference(SWRealReference):
    
    def __init__(self, id):
        self.id = id

    def is_consumable(self):
        return False

    def as_tuple(self):
        return ('completed2', str(self.id))

    def __str__(self):
        return '<CompletedRef: %s...>' % self.id[:10]

    def __repr__(self):
        return "SW2_CompletedReference(%s)" % repr(self.id)

class SW2_FetchReference(SWRealReference):
    
    def __init__(self, id, url, index=None):
        self.id = id
        self.url = url
        self.index = index

    def is_consumable(self):
        return False
    
    def as_tuple(self):
        return ('fetch2', str(self.id), str(self.url))

    def __str__(self):
        return "<FetchRef: %s..., for %s...>" % (self.id[:10], self.url[:20])

    def __repr__(self):
        return 'SW2_FetchReference(%s, %s)' % (repr(self.id), repr(self.url))

def encode_datavalue(str):
    return base64.b64encode(str) 

def decode_datavalue(ref):
    return decode_datavalue_string(ref.value)

def decode_datavalue_string(str):
    return base64.b64decode(str)

control_chars = ''.join(map(unichr, range(0,32) + range(127,160)))
control_char_re = re.compile('[%s]' % re.escape(control_chars))

def remove_control_chars(s):
    return control_char_re.sub(lambda match: "[%d]" % ord(match.group(0)), s)

class SWDataValue(SWRealReference):
    """
    This is akin to a SW2_ConcreteReference which encapsulates its own data.
    The data is always a string, and must be decoded using block_store functions much like Concrete refs.
    """
    
    def __init__(self, id, value):
        self.id = id
        self.value = value
        
    def as_tuple(self):
        return ('val', self.id, self.value)
    
    def __str__(self):
        string_repr = ""
        # XXX: Disabled because it was being invoked during logging, causing exceptions to arise.
        #if len(self.value) < 20:
        #    string_repr = '"' + decode_datavalue_string(self.value) + '"'
        #else:
        #    string_repr = "%d Base64 chars inline, starting with '%s'" % (len(self.value), remove_control_chars(decode_datavalue_string(self.value)[:20]))
        return "<DataValue: %s...>" % (self.id[:10])

    def __repr__(self):
        return 'SWDataValue(%s, %s)' % (repr(self.id), repr(self.value))
    
class SWReferenceJSONEncoder(simplejson.JSONEncoder):

    def default(self, obj):
        if isinstance(obj, SWRealReference):
            return {'__ref__': obj.as_tuple()}
        else:
            return simplejson.JSONEncoder.default(self, obj)

def json_decode_object_hook(dict_):
        if '__ref__' in dict_:
            return build_reference_from_tuple(dict_['__ref__'])
        else:
            return dict_

def build_reference_from_tuple(reference_tuple):
    ref_type = reference_tuple[0]
    if ref_type == 'val':
        return SWDataValue(reference_tuple[1], reference_tuple[2])
    elif ref_type == 'err':
        return SWErrorReference(reference_tuple[1], reference_tuple[2], reference_tuple[3])
    elif ref_type == 'f2':
        return SW2_FutureReference(reference_tuple[1])
    elif ref_type == 'c2':
        return SW2_ConcreteReference(reference_tuple[1], reference_tuple[2], reference_tuple[3])
    elif ref_type == '<3':
        return SW2_SweetheartReference(reference_tuple[1], reference_tuple[2], reference_tuple[3], reference_tuple[4])
    elif ref_type == 's2':
        return SW2_StreamReference(reference_tuple[1], reference_tuple[2])
    elif ref_type == 'ss2':
        return SW2_SocketStreamReference(reference_tuple[1], reference_tuple[2], reference_tuple[3])
    elif ref_type == 'fx':
        return SW2_FixedReference(reference_tuple[1], reference_tuple[2])
    elif ref_type == 't2':
        return SW2_TombstoneReference(reference_tuple[1], reference_tuple[2])
    elif ref_type == 'fetch2':
        return SW2_FetchReference(reference_tuple[1], reference_tuple[2])
    elif ref_type == "completed2":
        return SW2_CompletedReference(reference_tuple[1])
    else:
        raise KeyError(ref_type)
    
def combine_references(original, update):

    # DataValues are better than all others: they *are* the data
    if isinstance(original, SWDataValue):
        return original
    if isinstance(update, SWDataValue):
        return update

    # Sweetheart reference over other non-vals; combine location hints if any available.
    if (isinstance(update, SW2_SweetheartReference)):
        if (isinstance(original, SW2_ConcreteReference)):
            update.location_hints.update(original.location_hints)
        return update

    # Concrete reference > streaming reference > future reference.
    if (isinstance(original, SW2_FutureReference) or isinstance(original, SW2_StreamReference)) and isinstance(update, SW2_ConcreteReference):
        return update
    if isinstance(original, SW2_FutureReference) and isinstance(update, SW2_StreamReference):
        return update
    
    # Error reference > future reference.
    if isinstance(original, SW2_FutureReference) and isinstance(update, SWErrorReference):
        return update
    
    # For references of the same type, merge the location hints for the two references.
    if isinstance(original, SW2_StreamReference) and isinstance(update, SW2_StreamReference):
        original.combine_with(update)
        return original
    if isinstance(original, SW2_ConcreteReference) and isinstance(update, SW2_ConcreteReference):
        original.combine_with(update)
        return original
    
    if (isinstance(original, SW2_ConcreteReference) or isinstance(original, SW2_StreamReference)) and isinstance(update, SW2_TombstoneReference):
        original.location_hints.difference_update(update.netlocs)
        if len(original.location_hints) == 0:
            return original.as_future()
        else:
            return original
    
    # Propagate failure if a fixed reference goes away.
    if (isinstance(original, SW2_FixedReference) and isinstance(update, SW2_TombstoneReference)):
        return SWErrorReference(original.id, 'LOST_FIXED_OBJECT', original.fixed_netloc)
    
    # If we reach this point, we should ignore the update.
    return original


########NEW FILE########
__FILENAME__ = rpc_helper

from __future__ import with_statement

import select
import sys
from ciel.public.io_helpers import read_framed_json, write_framed_json

class ShutdownException(Exception):
    
    def __init__(self, reason):
        self.reason = reason

class RpcRequest:

    def __init__(self, method):

        self.response = None
        self.method = method

class RpcHelper:

    def __init__(self, in_fp, out_fp, active_outputs=None):

        self.in_fp = in_fp
        self.in_fd = in_fp.fileno()
        self.out_fp = out_fp
        self.active_outputs = active_outputs
        self.pending_request = None

    def drain_receive_buffer(self):

        while True:
            if not self.receive_message(block=False):
                break

    def receive_message(self, block=True):

        try:
    
            if block:
                pargs = []
            else:
                pargs = [0.0]
    
            reads, _, _ = select.select([self.in_fd], [], [], *pargs)
    
            have_message = self.in_fd in reads
            if have_message:
                (method, args) = read_framed_json(self.in_fp)
                if method == "subscribe" or method == "unsubscribe":
                    if self.active_outputs is None:
                        print >>sys.stderr, "Ignored request", method, "args", args, "because I have no active outputs dict"
                    else:
                        self.active_outputs.handle_request(method, args)
                elif method == "die":
                    raise ShutdownException(args["reason"])
                else:
                    if self.pending_request is not None:
                        if method != self.pending_request.method:
                            print >>sys.stderr, "Ignored response of type", method, \
                                "because I'm waiting for", self.pending_request.method
                        self.pending_request.response = args
                    else:
                        print >>sys.stderr, "Ignored request", method, "args", args
            return have_message

        except IOError:
            print >>sys.stderr, "RPC error when receiving message: process dying."
            sys.exit(-1)
    
    def synchronous_request(self, method, args=None, send=True):
        
        self.pending_request = RpcRequest(method)
        if send:
            self.send_message(method, args)
        while self.pending_request.response is None:
            self.receive_message(block=True)
            ret = self.pending_request.response
        self.pending_request = None
        return ret
    
    def await_message(self, method):
        return self.synchronous_request(method, send=False)

    def send_message(self, method, args):
        try:
            write_framed_json((method, args), self.out_fp)
            self.out_fp.flush()

        except IOError:
            print >>sys.stderr, "RPC error when receiving message: process dying."
            sys.exit(-1)

########NEW FILE########
__FILENAME__ = block_store
# Copyright (c) 2010 Derek Murray <derek.murray@cl.cam.ac.uk>
#               2011 Christopher Smowton <chris.smowton@cl.cam.ac.uk>
# Permission to use, copy, modify, and distribute this software for any
# purpose with or without fee is hereby granted, provided that the above
# copyright notice and this permission notice appear in all copies.
#
# THE SOFTWARE IS PROVIDED "AS IS" AND THE AUTHOR DISCLAIMS ALL WARRANTIES
# WITH REGARD TO THIS SOFTWARE INCLUDING ALL IMPLIED WARRANTIES OF
# MERCHANTABILITY AND FITNESS. IN NO EVENT SHALL THE AUTHOR BE LIABLE FOR
# ANY SPECIAL, DIRECT, INDIRECT, OR CONSEQUENTIAL DAMAGES OR ANY DAMAGES
# WHATSOEVER RESULTING FROM LOSS OF USE, DATA OR PROFITS, WHETHER IN AN
# ACTION OF CONTRACT, NEGLIGENCE OR OTHER TORTIOUS ACTION, ARISING OUT OF
# OR IN CONNECTION WITH THE USE OR PERFORMANCE OF THIS SOFTWARE.
from __future__ import with_statement
import random
import os
import uuid
import struct
import tempfile
import logging
import re
import threading
from datetime import datetime

# XXX: Hack because urlparse doesn't nicely support custom schemes.
import urlparse
from ciel.public.references import SW2_ConcreteReference, SW2_StreamReference,\
    SW2_FetchReference, SW2_FixedReference, SWRealReference, SWErrorReference,\
    SWDataValue, decode_datavalue
import ciel
from ciel.runtime.exceptions import ErrorReferenceError
urlparse.uses_netloc.append("swbs")

BLOCK_LIST_RECORD_STRUCT = struct.Struct("!120pQ")

PIN_PREFIX = '.__pin__:'

length_regex = re.compile("^Content-Length:\s*([0-9]+)")
http_response_regex = re.compile("^HTTP/1.1 ([0-9]+)")

singleton_blockstore = None

def get_netloc_for_sw_url(url):
    return urlparse.urlparse(url).netloc

def get_id_for_sw_url(url):
    return urlparse.urlparse(url).path

def sw_to_external_url(url):
    parsed_url = urlparse.urlparse(url)
    if parsed_url.scheme == 'swbs':
        id = parsed_url.path[1:]
        return 'http://%s/data/%s' % (parsed_url.netloc, id)
    else:
        return url

class BlockStore:

    def __init__(self, hostname, port, base_dir, ignore_blocks=False):
        self.hostname = None
        self.port = port
        self.netloc = None
        if hostname is not None:
            self.set_hostname(hostname)
        # N.B. This is not set up for workers until contact is made with the master.

        self.base_dir = base_dir
        self.pin_set = set()
        self.ignore_blocks = ignore_blocks
        self.lock = threading.Lock()

        global singleton_blockstore
        assert singleton_blockstore is None
        singleton_blockstore = self

    def set_hostname(self, hostname):
        self.hostname = hostname
        self.netloc = '%s:%d' % (self.hostname, self.port)

    def allocate_new_id(self):
        return str(uuid.uuid1())
    
    def pin_filename(self, id): 
        return os.path.join(self.base_dir, PIN_PREFIX + id)
    
    class OngoingFetch:

        def __init__(self, ref, block_store):
            self.ref = ref
            self.filename = None
            self.block_store = block_store
            while self.filename is None:
                possible_name = os.path.join(block_store.base_dir, ".fetch:%s:%s" % (datetime.now().microsecond, ref.id))
                if not os.path.exists(possible_name):
                    self.filename = possible_name

        def commit(self):
            self.block_store.commit_file(self.filename, self.block_store.filename_for_ref(self.ref))

    def create_fetch_file_for_ref(self, ref):
        with self.lock:
            return BlockStore.OngoingFetch(ref, self)
    
    def producer_filename(self, id):
        return os.path.join(self.base_dir, '.producer:%s' % id)
    
    def filename(self, id):
        return os.path.join(self.base_dir, str(id))

    def filename_for_ref(self, ref):
        if isinstance(ref, SW2_FixedReference):
            return os.path.join(self.base_dir, '.__fixed__.%s' % ref.id)
        else:
            return self.filename(ref.id)
        
    def is_ref_local(self, ref):
        assert isinstance(ref, SWRealReference)

        if isinstance(ref, SWErrorReference):
            raise ErrorReferenceError(ref)

        if isinstance(ref, SW2_FixedReference):
            assert ref.fixed_netloc == self.netloc
            
        if os.path.exists(self.filename_for_ref(ref)):
            return True
        if isinstance(ref, SWDataValue):
            create_datavalue_file(ref)
            return True

        return False

    def commit_file(self, old_name, new_name):

        try:
            os.link(old_name, new_name)
        except OSError as e:
            if e.errno == 17: # File exists
                size_old = os.path.getsize(old_name)
                size_new = os.path.getsize(new_name)
                if size_old == size_new:
                    ciel.log('Produced/retrieved %s matching existing file (size %d): ignoring' % (new_name, size_new), 'BLOCKSTORE', logging.WARNING)
                else:
                    ciel.log('Produced/retrieved %s with size not matching existing block (old: %d, new %d)' % (new_name, size_old, size_new), 'BLOCKSTORE', logging.ERROR)
                    raise
            else:
                raise

    def commit_producer(self, id):
        ciel.log.error('Committing file for output %s' % id, 'BLOCKSTORE', logging.DEBUG)
        self.commit_file(self.producer_filename(id), self.filename(id))
        
    def choose_best_netloc(self, netlocs):
        for netloc in netlocs:
            if netloc == self.netloc:
                return netloc
        return random.choice(list(netlocs))
        
    def choose_best_url(self, urls):
        if len(urls) == 1:
            return urls[0]
        else:
            for url in enumerate(urls):
                parsed_url = urlparse.urlparse(url)
                if parsed_url.netloc == self.netloc:
                    return url
            return random.choice(urls)

    def check_local_blocks(self):
        ciel.log("Looking for local blocks", "BLOCKSTORE", logging.DEBUG)
        try:
            for block_name in os.listdir(self.base_dir):
                if block_name.startswith('.fetch:'):
                    if not os.path.exists(os.path.join(self.base_dir, block_name[7:])):
                        ciel.log("Deleting incomplete block %s" % block_name, "BLOCKSTORE", logging.WARNING)
                        os.remove(os.path.join(self.base_dir, block_name))
                elif block_name.startswith('.producer:'):
                    if not os.path.exists(os.path.join(self.base_dir, block_name[10:])):
                        ciel.log("Deleting incomplete block %s" % block_name, "BLOCKSTORE", logging.WARNING)
                        os.remove(os.path.join(self.base_dir, block_name))                        
        except OSError as e:
            ciel.log("Couldn't enumerate existing blocks: %s" % e, "BLOCKSTORE", logging.WARNING)

    def block_list_generator(self):
        ciel.log.error('Generating block list for local consumption', 'BLOCKSTORE', logging.DEBUG)
        for block_name in os.listdir(self.base_dir):
            if not block_name.startswith('.'):
                block_size = os.path.getsize(os.path.join(self.base_dir, block_name))
                yield block_name, block_size
    
    def build_pin_set(self):
        ciel.log.error('Building pin set', 'BLOCKSTORE', logging.DEBUG)
        initial_size = len(self.pin_set)
        for filename in os.listdir(self.base_dir):
            if filename.startswith(PIN_PREFIX):
                self.pin_set.add(filename[len(PIN_PREFIX):])
                ciel.log.error('Pinning block %s' % filename[len(PIN_PREFIX):], 'BLOCKSTORE', logging.DEBUG)
        ciel.log.error('Pinned %d new blocks' % (len(self.pin_set) - initial_size), 'BLOCKSTORE', logging.DEBUG)
    
    def generate_block_list_file(self):
        ciel.log.error('Generating block list file', 'BLOCKSTORE', logging.DEBUG)
        with tempfile.NamedTemporaryFile('w', delete=False) as block_list_file:
            filename = block_list_file.name
            for block_name, block_size in self.block_list_generator():
                block_list_file.write(BLOCK_LIST_RECORD_STRUCT.pack(block_name, block_size))
        return filename

    def generate_pin_refs(self):
        ret = []
        for id in self.pin_set:
            ret.append(SW2_ConcreteReference(id, os.path.getsize(self.filename(id)), [self.netloc]))
        return ret

    def pin_ref_id(self, id):
        open(self.pin_filename(id), 'w').close()
        self.pin_set.add(id)
        ciel.log.error('Pinned block %s' % id, 'BLOCKSTORE', logging.DEBUG)
        
    def flush_unpinned_blocks(self, really=True):
        ciel.log.error('Flushing unpinned blocks', 'BLOCKSTORE', logging.DEBUG)
        files_kept = 0
        files_removed = 0
        for block_name in os.listdir(self.base_dir):
            if block_name not in self.pin_set and not block_name.startswith(PIN_PREFIX):
                if really:
                    os.remove(os.path.join(self.base_dir, block_name))
                files_removed += 1
            elif not block_name.startswith(PIN_PREFIX):
                files_kept += 1
        if really:
            ciel.log.error('Flushed block store, kept %d blocks, removed %d blocks' % (files_kept, files_removed), 'BLOCKSTORE', logging.DEBUG)
        else:
            ciel.log.error('If we flushed block store, would keep %d blocks, remove %d blocks' % (files_kept, files_removed), 'BLOCKSTORE', logging.DEBUG)
        return (files_kept, files_removed)

    def is_empty(self):
        return self.ignore_blocks or len(os.listdir(self.base_dir)) == 0

### Stateless functions

def get_fetch_urls_for_ref(ref):

    if isinstance(ref, SW2_ConcreteReference):
        return ["http://%s/data/%s" % (loc_hint, ref.id) for loc_hint in ref.location_hints]
    elif isinstance(ref, SW2_StreamReference):
        return ["http://%s/data/.producer:%s" % (loc_hint, ref.id) for loc_hint in ref.location_hints]
    elif isinstance(ref, SW2_FixedReference):
        assert ref.fixed_netloc == get_own_netloc()
        return ["http://%s/data/%s" % (ref.fixed_netloc, ref.id)]
    elif isinstance(ref, SW2_FetchReference):
        return [ref.url]

### Proxies against the singleton blockstore

def commit_fetch(ref):
    singleton_blockstore.commit_fetch(ref)

def commit_producer(id):
    singleton_blockstore.commit_producer(id)

def get_own_netloc():
    return singleton_blockstore.netloc

def create_fetch_file_for_ref(ref):
    return singleton_blockstore.create_fetch_file_for_ref(ref)
    
def producer_filename(id):
    return singleton_blockstore.producer_filename(id)

def filename(id):
    return singleton_blockstore.filename(id)

def filename_for_ref(ref):
    return singleton_blockstore.filename_for_ref(ref)

def is_ref_local(ref):
    return singleton_blockstore.is_ref_local(ref)

def create_datavalue_file(ref):
    bs_ctx = create_fetch_file_for_ref(ref)
    with open(bs_ctx.filename, 'w') as obj_file:
        obj_file.write(decode_datavalue(ref))
    bs_ctx.commit()


########NEW FILE########
__FILENAME__ = exceptions
# Copyright (c) 2010 Derek Murray <derek.murray@cl.cam.ac.uk>
#
# Permission to use, copy, modify, and distribute this software for any
# purpose with or without fee is hereby granted, provided that the above
# copyright notice and this permission notice appear in all copies.
#
# THE SOFTWARE IS PROVIDED "AS IS" AND THE AUTHOR DISCLAIMS ALL WARRANTIES
# WITH REGARD TO THIS SOFTWARE INCLUDING ALL IMPLIED WARRANTIES OF
# MERCHANTABILITY AND FITNESS. IN NO EVENT SHALL THE AUTHOR BE LIABLE FOR
# ANY SPECIAL, DIRECT, INDIRECT, OR CONSEQUENTIAL DAMAGES OR ANY DAMAGES
# WHATSOEVER RESULTING FROM LOSS OF USE, DATA OR PROFITS, WHETHER IN AN
# ACTION OF CONTRACT, NEGLIGENCE OR OTHER TORTIOUS ACTION, ARISING OUT OF
# OR IN CONNECTION WITH THE USE OR PERFORMANCE OF THIS SOFTWARE.

'''
Created on 22 Apr 2010

@author: dgm36
'''

class WorkerFailedException(Exception):
    def __init__(self, worker):
        self.worker = worker

class AbortedException(Exception):
    def __init__(self):
        pass

class SkywritingParsingError(Exception):
    def __init__(self, message):
        self.message = message

class RuntimeSkywritingError(Exception):
    def __init__(self, message, cause):
        self.message = message
        self.cause = cause

class UnknownIdentifierError(Exception):
    def __init__(self, identifier):
        self.identifier = identifier
        
class TaskFailedError(Exception):
    def __init__(self, message):
        self.message = message

class ErrorReferenceError(Exception):
    def __init__(self, ref):
        self.ref = ref

class AbortedExecutionException(RuntimeSkywritingError):
    def __init__(self):
        pass
    
class BlameUserException(RuntimeSkywritingError):
    def __init__(self, description):
        self.description = description
        
    def __repr__(self):
        return self.description
    
    def __str__(self):
        return self.description

class MasterNotRespondingException(RuntimeSkywritingError):
    def __init__(self):
        pass

class WorkerShutdownException(RuntimeSkywritingError):
    def __init__(self):
        pass

class ExecutionInterruption(Exception):
    def __init__(self):
        pass
    
class FeatureUnavailableException(ExecutionInterruption):
    def __init__(self, feature_name):
        self.feature_name = feature_name

    def __repr__(self):
        return 'FeatureUnavailableException(feature_name="%s")' % (self.feature_name, )
        
class DataTooBigException(ExecutionInterruption):
    def __init__(self, size):
        self.size = size
        
class ReferenceUnavailableException(ExecutionInterruption):
    def __init__(self, ref):
        self.ref = ref
        
    def __repr__(self):
        return 'ReferenceUnavailableException(ref=%s)' % (repr(self.ref), )
    
class SelectException(ExecutionInterruption):
    def __init__(self, select_group, timeout):
        self.select_group = select_group
        self.timeout = timeout
        
class MissingInputException(RuntimeSkywritingError):
    def __init__(self, bindings):
        self.bindings = bindings
        
    def __repr__(self):
        return 'MissingInputException(refs=%s)' % (repr(self.bindings.values()), )

########NEW FILE########
__FILENAME__ = base
# Copyright (c) 2010--11 Derek Murray <derek.murray@cl.cam.ac.uk>
#                        Chris Smowton <chris.smowton@cl.cam.ac.uk>
#
# Permission to use, copy, modify, and distribute this software for any
# purpose with or without fee is hereby granted, provided that the above
# copyright notice and this permission notice appear in all copies.
#
# THE SOFTWARE IS PROVIDED "AS IS" AND THE AUTHOR DISCLAIMS ALL WARRANTIES
# WITH REGARD TO THIS SOFTWARE INCLUDING ALL IMPLIED WARRANTIES OF
# MERCHANTABILITY AND FITNESS. IN NO EVENT SHALL THE AUTHOR BE LIABLE FOR
# ANY SPECIAL, DIRECT, INDIRECT, OR CONSEQUENTIAL DAMAGES OR ANY DAMAGES
# WHATSOEVER RESULTING FROM LOSS OF USE, DATA OR PROFITS, WHETHER IN AN
# ACTION OF CONTRACT, NEGLIGENCE OR OTHER TORTIOUS ACTION, ARISING OUT OF
# OR IN CONNECTION WITH THE USE OR PERFORMANCE OF THIS SOFTWARE.
import ciel
import logging
from ciel.runtime.object_cache import retrieve_object_for_ref,\
    ref_from_object

class BaseExecutor:
    
    TASK_PRIVATE_ENCODING = 'pickle'
    
    def __init__(self, worker):
        self.worker = worker
        self.block_store = worker.block_store
    
    def run(self, task_descriptor, task_record):
        # XXX: This is braindead, considering that we just stashed task_private
        #      in here during prepare().
        self._run(task_descriptor["task_private"], task_descriptor, task_record)
    
    def abort(self):
        self._abort()    
    
    def cleanup(self):
        pass
        
    @classmethod
    def prepare_task_descriptor_for_execute(cls, task_descriptor, task_record, block_store):
        # Convert task_private from a reference to an object in here.
        try:
            task_descriptor["task_private"] = retrieve_object_for_ref(task_descriptor["task_private"], BaseExecutor.TASK_PRIVATE_ENCODING, task_record)
        except:
            ciel.log('Error retrieving task_private reference from task', 'BASE_EXECUTOR', logging.WARN, True)
            raise
        
    @classmethod
    def build_task_descriptor(cls, task_descriptor, parent_task_record):
        # Convert task_private to a reference in here. 
        task_private_id = ("%s:_private" % task_descriptor["task_id"])
        task_private_ref = ref_from_object(task_descriptor["task_private"], BaseExecutor.TASK_PRIVATE_ENCODING, task_private_id)
        parent_task_record.publish_ref(task_private_ref)
        task_descriptor["task_private"] = task_private_ref
        task_descriptor["dependencies"].append(task_private_ref)

########NEW FILE########
__FILENAME__ = cso
# Copyright (c) 2010 Chris Smowton <Chris.Smowton@cl.cam.ac.uk>
#
# Permission to use, copy, modify, and distribute this software for any
# purpose with or without fee is hereby granted, provided that the above
# copyright notice and this permission notice appear in all copies.
#
# THE SOFTWARE IS PROVIDED "AS IS" AND THE AUTHOR DISCLAIMS ALL WARRANTIES
# WITH REGARD TO THIS SOFTWARE INCLUDING ALL IMPLIED WARRANTIES OF
# MERCHANTABILITY AND FITNESS. IN NO EVENT SHALL THE AUTHOR BE LIABLE FOR
# ANY SPECIAL, DIRECT, INDIRECT, OR CONSEQUENTIAL DAMAGES OR ANY DAMAGES
# WHATSOEVER RESULTING FROM LOSS OF USE, DATA OR PROFITS, WHETHER IN AN
# ACTION OF CONTRACT, NEGLIGENCE OR OTHER TORTIOUS ACTION, ARISING OUT OF
# OR IN CONNECTION WITH THE USE OR PERFORMANCE OF THIS SOFTWARE.
from ciel.runtime.executors.simple import FilenamesOnStdinExecutor
import os
import ciel
from ciel.runtime.executors import test_program
from ciel.runtime.exceptions import BlameUserException
from ciel.runtime.fetcher import retrieve_filenames_for_refs
import logging

class CExecutor(FilenamesOnStdinExecutor):

    handler_name = "cso"

    def __init__(self, worker):
        FilenamesOnStdinExecutor.__init__(self, worker)

    @staticmethod
    def can_run():
        c_loader = os.getenv("SW_C_LOADER_PATH")
        if c_loader is None:
            ciel.log.error("Can't run C tasks: SW_C_LOADER_PATH not set", "CEXEC", logging.WARNING)
            return False
        return test_program([c_loader, "--version"], "C-loader")

    @classmethod
    def check_args_valid(cls, args, n_outputs):

        FilenamesOnStdinExecutor.check_args_valid(args, n_outputs)
        if "lib" not in args or "entry_point" not in args:
            raise BlameUserException('Incorrect arguments to the C-so executor: %s' % repr(args))

    def before_execute(self, block_store):
        self.so_refs = self.args['lib']
        self.entry_point_name = self.args['entry_point']

        ciel.log.error("Running C executor for entry point: %s" % self.entry_point_name, "CEXEC", logging.DEBUG)
        ciel.engine.publish("worker_event", "C-exec: fetching SOs")
        self.so_filenames = retrieve_filenames_for_refs(self.so_refs, self.task_record)

    def get_process_args(self):

        c_loader = os.getenv('SW_C_LOADER_PATH')
        process_args = [c_loader, self.entry_point_name]
        process_args.extend(self.so_filenames)
        return process_args

########NEW FILE########
__FILENAME__ = dotnet
# Copyright (c) 2010 Chris Smowton <Chris.Smowton@cl.cam.ac.uk>
#
# Permission to use, copy, modify, and distribute this software for any
# purpose with or without fee is hereby granted, provided that the above
# copyright notice and this permission notice appear in all copies.
#
# THE SOFTWARE IS PROVIDED "AS IS" AND THE AUTHOR DISCLAIMS ALL WARRANTIES
# WITH REGARD TO THIS SOFTWARE INCLUDING ALL IMPLIED WARRANTIES OF
# MERCHANTABILITY AND FITNESS. IN NO EVENT SHALL THE AUTHOR BE LIABLE FOR
# ANY SPECIAL, DIRECT, INDIRECT, OR CONSEQUENTIAL DAMAGES OR ANY DAMAGES
# WHATSOEVER RESULTING FROM LOSS OF USE, DATA OR PROFITS, WHETHER IN AN
# ACTION OF CONTRACT, NEGLIGENCE OR OTHER TORTIOUS ACTION, ARISING OUT OF
# OR IN CONNECTION WITH THE USE OR PERFORMANCE OF THIS SOFTWARE.
import os
import ciel
import logging
from ciel.runtime.executors.simple import FilenamesOnStdinExecutor
from ciel.runtime.executors import test_program
from ciel.runtime.exceptions import BlameUserException
from ciel.runtime.fetcher import retrieve_filenames_for_refs

class DotNetExecutor(FilenamesOnStdinExecutor):

    handler_name = "dotnet"

    def __init__(self, worker):
        FilenamesOnStdinExecutor.__init__(self, worker)

    @staticmethod
    def can_run():
        mono_loader = os.getenv('SW_MONO_LOADER_PATH')
        if mono_loader is None:
            ciel.log.error("Can't run Mono: SW_MONO_LOADER_PATH not set", "DOTNET", logging.WARNING)
            return False
        return test_program(["mono", mono_loader, "--version"], "Mono")

    @classmethod
    def check_args_valid(cls, args, n_outputs):

        FilenamesOnStdinExecutor.check_args_valid(args, n_outputs)
        if "lib" not in args or "class" not in args:
            raise BlameUserException('Incorrect arguments to the dotnet executor: %s' % repr(args))

    def before_execute(self):

        self.dll_refs = self.args['lib']
        self.class_name = self.args['class']

        ciel.log.error("Running Dotnet executor for class: %s" % self.class_name, "DOTNET", logging.DEBUG)
        ciel.engine.publish("worker_event", "Dotnet: fetching DLLs")
        self.dll_filenames = retrieve_filenames_for_refs(self.dll_refs, self.task_record)

    def get_process_args(self):

        mono_loader = os.getenv('SW_MONO_LOADER_PATH')
        process_args = ["mono", mono_loader, self.class_name]
        process_args.extend(self.dll_filenames)
        return process_args

########NEW FILE########
__FILENAME__ = environ
# Copyright (c) 2010--11 Derek Murray <Derek.Murray@cl.cam.ac.uk>
#
# Permission to use, copy, modify, and distribute this software for any
# purpose with or without fee is hereby granted, provided that the above
# copyright notice and this permission notice appear in all copies.
#
# THE SOFTWARE IS PROVIDED "AS IS" AND THE AUTHOR DISCLAIMS ALL WARRANTIES
# WITH REGARD TO THIS SOFTWARE INCLUDING ALL IMPLIED WARRANTIES OF
# MERCHANTABILITY AND FITNESS. IN NO EVENT SHALL THE AUTHOR BE LIABLE FOR
# ANY SPECIAL, DIRECT, INDIRECT, OR CONSEQUENTIAL DAMAGES OR ANY DAMAGES
# WHATSOEVER RESULTING FROM LOSS OF USE, DATA OR PROFITS, WHETHER IN AN
# ACTION OF CONTRACT, NEGLIGENCE OR OTHER TORTIOUS ACTION, ARISING OUT OF
# OR IN CONNECTION WITH THE USE OR PERFORMANCE OF THIS SOFTWARE.
from ciel.public.references import SWRealReference
import os
import stat
import ciel
import tempfile
import subprocess
from ciel.runtime.executors.simple import ProcessRunningExecutor
from ciel.runtime.exceptions import BlameUserException
from ciel.runtime.fetcher import retrieve_filename_for_ref
import logging

class EnvironmentExecutor(ProcessRunningExecutor):

    handler_name = "env"

    def __init__(self, worker):
        ProcessRunningExecutor.__init__(self, worker)

    @classmethod
    def check_args_valid(cls, args, n_outputs):
        ProcessRunningExecutor.check_args_valid(args, n_outputs)
        if "command_line" not in args:
            raise BlameUserException('Incorrect arguments to the env executor: %s' % repr(args))

    def start_process(self, input_files, output_files):

        command_line = self.args["command_line"]

        for i, arg in enumerate(command_line):
            if isinstance(arg, SWRealReference):
                # Command line argument has been passed in as a reference.
                command_line[i] = retrieve_filename_for_ref(arg, self.task_record, False)
                if i == 0:
                    # First argument must be executable.
                    os.chmod(command_line[0], stat.S_IRWXU)

        try:
            env = self.args['env']
        except KeyError:
            env = {}

        ciel.log.error("Executing environ with: %s" % " ".join(map(str, command_line)), 'EXEC', logging.DEBUG)

        with tempfile.NamedTemporaryFile(delete=False) as input_filenames_file:
            for filename in input_files:
                input_filenames_file.write(filename)
                input_filenames_file.write('\n')
            input_filenames_name = input_filenames_file.name
            
        with tempfile.NamedTemporaryFile(delete=False) as output_filenames_file:
            for filename in output_files:
                output_filenames_file.write(filename)
                output_filenames_file.write('\n')
            output_filenames_name = output_filenames_file.name
            
        environment = {'INPUT_FILES'  : input_filenames_name,
                       'OUTPUT_FILES' : output_filenames_name}
        
        environment.update(os.environ)
        environment.update(env)
            
        proc = subprocess.Popen(map(str, command_line), env=environment, close_fds=True)

        #_ = proc.stdout.read(1)
        #print 'Got byte back from Executor'

        return proc

########NEW FILE########
__FILENAME__ = grab
# Copyright (c) 2010 Derek Murray <Derek.Murray@cl.cam.ac.uk>
#
# Permission to use, copy, modify, and distribute this software for any
# purpose with or without fee is hereby granted, provided that the above
# copyright notice and this permission notice appear in all copies.
#
# THE SOFTWARE IS PROVIDED "AS IS" AND THE AUTHOR DISCLAIMS ALL WARRANTIES
# WITH REGARD TO THIS SOFTWARE INCLUDING ALL IMPLIED WARRANTIES OF
# MERCHANTABILITY AND FITNESS. IN NO EVENT SHALL THE AUTHOR BE LIABLE FOR
# ANY SPECIAL, DIRECT, INDIRECT, OR CONSEQUENTIAL DAMAGES OR ANY DAMAGES
# WHATSOEVER RESULTING FROM LOSS OF USE, DATA OR PROFITS, WHETHER IN AN
# ACTION OF CONTRACT, NEGLIGENCE OR OTHER TORTIOUS ACTION, ARISING OUT OF
# OR IN CONNECTION WITH THE USE OR PERFORMANCE OF THIS SOFTWARE.
import ciel
import logging
from ciel.public.references import SWReferenceJSONEncoder, SWDataValue
import simplejson
from ciel.runtime.executors.simple import SimpleExecutor
from ciel.runtime.exceptions import BlameUserException
from ciel.runtime.fetcher import get_ref_for_url
from ciel.runtime.object_cache import cache_object


class GrabURLExecutor(SimpleExecutor):

    handler_name = "grab"
    
    def __init__(self, worker):
        SimpleExecutor.__init__(self, worker)
    
    @classmethod
    def check_args_valid(cls, args, n_outputs):
        
        SimpleExecutor.check_args_valid(args, n_outputs)
        if "urls" not in args or "version" not in args or len(args["urls"]) != n_outputs:
            raise BlameUserException('Incorrect arguments to the grab executor: %s' % repr(args))

    def _execute(self):

        urls = self.args['urls']
        version = self.args['version']

        ciel.log.error('Starting to fetch URLs', 'FETCHEXECUTOR', logging.DEBUG)
        
        for i, url in enumerate(urls):
            ref = get_ref_for_url(url, version, self.task_id)
            self.task_record.publish_ref(ref)
            out_str = simplejson.dumps(ref, cls=SWReferenceJSONEncoder)
            cache_object(ref, "json", self.output_ids[i])
            self.output_refs[i] = SWDataValue(self.output_ids[i], out_str)

        ciel.log.error('Done fetching URLs', 'FETCHEXECUTOR', logging.DEBUG)

########NEW FILE########
__FILENAME__ = haskell
# Copyright (c) 2011 Anil Madhavapeddy <Anil.Madhavapeddy@cl.cam.ac.uk>
#
# Permission to use, copy, modify, and distribute this software for any
# purpose with or without fee is hereby granted, provided that the above
# copyright notice and this permission notice appear in all copies.
#
# THE SOFTWARE IS PROVIDED "AS IS" AND THE AUTHOR DISCLAIMS ALL WARRANTIES
# WITH REGARD TO THIS SOFTWARE INCLUDING ALL IMPLIED WARRANTIES OF
# MERCHANTABILITY AND FITNESS. IN NO EVENT SHALL THE AUTHOR BE LIABLE FOR
# ANY SPECIAL, DIRECT, INDIRECT, OR CONSEQUENTIAL DAMAGES OR ANY DAMAGES
# WHATSOEVER RESULTING FROM LOSS OF USE, DATA OR PROFITS, WHETHER IN AN
# ACTION OF CONTRACT, NEGLIGENCE OR OTHER TORTIOUS ACTION, ARISING OUT OF
# OR IN CONNECTION WITH THE USE OR PERFORMANCE OF THIS SOFTWARE.
from ciel.runtime.executors.proc import ProcExecutor
from ciel.runtime.exceptions import BlameUserException
import hashlib
from ciel.runtime.executors import hash_update_with_structure,\
    test_program
from os.path import isabs, join, expanduser

class HaskellExecutor(ProcExecutor):
    
    handler_name = "haskell"
    process_cache = set()
    
    def __init__(self, worker):
        ProcExecutor.__init__(self, worker)

    @classmethod
    def check_args_valid(cls, args, n_outputs):
        if "binary" not in args:
            raise BlameUserException("All Haskell invocations must specify a binary")
            
    @classmethod
    def build_task_descriptor(cls, task_descriptor, parent_task_record, binary, fn_ref=None, args=None, n_outputs=1, is_tail_spawn=False, **kwargs):
        if binary is None:
            raise BlameUserException("All Haskell invocations must specify a binary")
        
        if not isabs(binary):
            binary = join(expanduser("~/.cabal/bin"),binary)

        task_descriptor["task_private"]["binary"] = binary
        if fn_ref is not None:
            task_descriptor["task_private"]["fn_ref"] = fn_ref
            task_descriptor["dependencies"].append(fn_ref)

        if not is_tail_spawn:
            sha = hashlib.sha1()
            hash_update_with_structure(sha, [args, n_outputs])
            hash_update_with_structure(sha, binary)
            hash_update_with_structure(sha, fn_ref)
            name_prefix = "hsk:%s:" % (sha.hexdigest())
            task_descriptor["expected_outputs"] = ["%s%d" % (name_prefix, i) for i in range(n_outputs)]            
        
        if args is not None:
            task_descriptor["task_private"]["args"] = args
        
        return ProcExecutor.build_task_descriptor(task_descriptor, parent_task_record, n_extra_outputs=0, is_tail_spawn=is_tail_spawn, accept_ref_list_for_single=True, **kwargs)
        
    def get_command(self):
        cmd = self.task_descriptor["task_private"]["binary"]
        assert(cmd)
        return cmd.split(" ")

    @staticmethod
    def can_run():
        return True

########NEW FILE########
__FILENAME__ = init
# Copyright (c) 2010-11 Chris Smowton <Chris.Smowton@cl.cam.ac.uk>
#
# Permission to use, copy, modify, and distribute this software for any
# purpose with or without fee is hereby granted, provided that the above
# copyright notice and this permission notice appear in all copies.
#
# THE SOFTWARE IS PROVIDED "AS IS" AND THE AUTHOR DISCLAIMS ALL WARRANTIES
# WITH REGARD TO THIS SOFTWARE INCLUDING ALL IMPLIED WARRANTIES OF
# MERCHANTABILITY AND FITNESS. IN NO EVENT SHALL THE AUTHOR BE LIABLE FOR
# ANY SPECIAL, DIRECT, INDIRECT, OR CONSEQUENTIAL DAMAGES OR ANY DAMAGES
# WHATSOEVER RESULTING FROM LOSS OF USE, DATA OR PROFITS, WHETHER IN AN
# ACTION OF CONTRACT, NEGLIGENCE OR OTHER TORTIOUS ACTION, ARISING OUT OF
# OR IN CONNECTION WITH THE USE OR PERFORMANCE OF THIS SOFTWARE.
from ciel.runtime.executors.base import BaseExecutor
import pickle
from ciel.runtime.exceptions import BlameUserException
from ciel.runtime.executors import spawn_task_helper
from ciel.public.references import SWRealReference

# XXX: Passing ref_of_string to get round a circular import. Should really move ref_of_string() to
#      a nice utility package.
def build_init_descriptor(handler, args, package_ref, master_uri, ref_of_string):
    task_private_dict = {"package_ref": package_ref, 
                         "start_handler": handler, 
                         "start_args": args
                         } 
    task_private_ref = ref_of_string(pickle.dumps(task_private_dict), master_uri)
    return {"handler": "init", 
            "dependencies": [package_ref, task_private_ref], 
            "task_private": task_private_ref
            }

class InitExecutor(BaseExecutor):

    handler_name = "init"

    def __init__(self, worker):
        BaseExecutor.__init__(self, worker)

    @staticmethod
    def can_run():
        return True

    @classmethod
    def build_task_descriptor(cls, descriptor, parent_task_record, **args):
        raise BlameUserException("Can't spawn init tasks directly; build them from outside the cluster using 'build_init_descriptor'")

    def _run(self, task_private, task_descriptor, task_record):
        
        args_dict = task_private["start_args"]
        # Some versions of simplejson make these ascii keys into unicode objects :(
        args_dict = dict([(str(k), v) for (k, v) in args_dict.items()])
        initial_task_out_obj = spawn_task_helper(task_record,
                                                 task_private["start_handler"], 
                                                 True,
                                                 **args_dict)
        if isinstance(initial_task_out_obj, SWRealReference):
            initial_task_out_refs = [initial_task_out_obj]
        else:
            initial_task_out_refs = list(initial_task_out_obj)
        spawn_task_helper(task_record, "sync", True, delegated_outputs = task_descriptor["expected_outputs"], args = {"inputs": initial_task_out_refs}, n_outputs=1)

########NEW FILE########
__FILENAME__ = java
# Copyright (c) 2010--11 Chris Smowton <Chris.Smowton@cl.cam.ac.uk>
#
# Permission to use, copy, modify, and distribute this software for any
# purpose with or without fee is hereby granted, provided that the above
# copyright notice and this permission notice appear in all copies.
#
# THE SOFTWARE IS PROVIDED "AS IS" AND THE AUTHOR DISCLAIMS ALL WARRANTIES
# WITH REGARD TO THIS SOFTWARE INCLUDING ALL IMPLIED WARRANTIES OF
# MERCHANTABILITY AND FITNESS. IN NO EVENT SHALL THE AUTHOR BE LIABLE FOR
# ANY SPECIAL, DIRECT, INDIRECT, OR CONSEQUENTIAL DAMAGES OR ANY DAMAGES
# WHATSOEVER RESULTING FROM LOSS OF USE, DATA OR PROFITS, WHETHER IN AN
# ACTION OF CONTRACT, NEGLIGENCE OR OTHER TORTIOUS ACTION, ARISING OUT OF
# OR IN CONNECTION WITH THE USE OR PERFORMANCE OF THIS SOFTWARE.
import os
import os.path
import ciel
import logging
from ciel.runtime.executors.simple import FilenamesOnStdinExecutor
from ciel.runtime.executors import test_program
from ciel.runtime.exceptions import BlameUserException
from ciel.runtime.fetcher import retrieve_filenames_for_refs
import pkg_resources

class JavaExecutor(FilenamesOnStdinExecutor):

    handler_name = "java"

    classpath = None

    def __init__(self, worker):
        FilenamesOnStdinExecutor.__init__(self, worker)

    @staticmethod
    def can_run():
        jars_dir = os.getenv('CIEL_JARS_DIR')
        if jars_dir is None:
            ciel.log.error("Cannot run Java executor. The CIEL_JARS_DIR environment variable must be set.", "JAVA", logging.INFO)
            return False
        if not os.path.exists(os.path.join(jars_dir, 'ciel-0.1.jar')):
            ciel.log.error("Cannot run Java executor. The file 'ciel-0.1.jar' is not installed in CIEL_JARS_DIR.", "JAVA", logging.INFO)
            return False
        JavaExecutor.classpath = os.path.join(jars_dir, 'ciel-0.1.jar')
        return test_program(["java", "-cp", JavaExecutor.classpath, "uk.co.mrry.mercator.task.JarTaskLoader", "--version"], "Java")

    @classmethod
    def check_args_valid(cls, args, n_outputs):

        FilenamesOnStdinExecutor.check_args_valid(args, n_outputs)
        if "lib" not in args or "class" not in args:
            raise BlameUserException('Incorrect arguments to the java executor: %s' % repr(args))

    def before_execute(self):

        self.jar_refs = self.args["lib"]
        self.class_name = self.args["class"]

        ciel.log.error("Running Java executor for class: %s" % self.class_name, "JAVA", logging.DEBUG)
        ciel.engine.publish("worker_event", "Java: fetching JAR")

        self.jar_filenames = retrieve_filenames_for_refs(self.jar_refs, self.task_record)

    def get_process_args(self):
        process_args = ["java", "-cp", JavaExecutor.classpath]
        if "trace_io" in self.debug_opts:
            process_args.append("-Dskywriting.trace_io=1")
        process_args.extend(["uk.co.mrry.mercator.task.JarTaskLoader", self.class_name])
        process_args.extend(["file://" + x for x in self.jar_filenames])
        return process_args

########NEW FILE########
__FILENAME__ = java2
# Copyright (c) 2011 Derek Murray <Derek.Murray@cl.cam.ac.uk>
#
# Permission to use, copy, modify, and distribute this software for any
# purpose with or without fee is hereby granted, provided that the above
# copyright notice and this permission notice appear in all copies.
#
# THE SOFTWARE IS PROVIDED "AS IS" AND THE AUTHOR DISCLAIMS ALL WARRANTIES
# WITH REGARD TO THIS SOFTWARE INCLUDING ALL IMPLIED WARRANTIES OF
# MERCHANTABILITY AND FITNESS. IN NO EVENT SHALL THE AUTHOR BE LIABLE FOR
# ANY SPECIAL, DIRECT, INDIRECT, OR CONSEQUENTIAL DAMAGES OR ANY DAMAGES
# WHATSOEVER RESULTING FROM LOSS OF USE, DATA OR PROFITS, WHETHER IN AN
# ACTION OF CONTRACT, NEGLIGENCE OR OTHER TORTIOUS ACTION, ARISING OUT OF
# OR IN CONNECTION WITH THE USE OR PERFORMANCE OF THIS SOFTWARE.
from ciel.runtime.executors.proc import ProcExecutor
from ciel.runtime.exceptions import BlameUserException
import hashlib
from ciel.runtime.executors import hash_update_with_structure,\
    add_package_dep, test_program
from ciel.runtime.fetcher import retrieve_filename_for_ref
import ciel
import os
import logging
import pkg_resources
import tempfile
import shutil

REQUIRED_LIBS = ['ciel-0.1.jar', 'gson-1.7.1.jar']

class Java2Executor(ProcExecutor):
    
    handler_name = "java2"
    process_cache = set()

    classpath = None
    
    def __init__(self, worker):
        ProcExecutor.__init__(self, worker)

    @classmethod
    def check_args_valid(cls, args, n_outputs):
        if "class_name" not in args and "object_ref" not in args:
            raise BlameUserException("All Java2 invocations must specify either a class_name or an object_ref")
        if "jar_lib" not in args:
            raise BlameUserException("All Java2 invocations must specify a jar_lib")
            
    @classmethod
    def build_task_descriptor(cls, task_descriptor, parent_task_record, jar_lib=None, args=None, class_name=None, object_ref=None, n_outputs=1, is_tail_spawn=False, **kwargs):
        # More good stuff goes here.
        if jar_lib is None and kwargs.get("process_record_id", None) is None:
            raise BlameUserException("All Java2 invocations must either specify jar libs or an existing process ID")
        if class_name is None and object_ref is None and kwargs.get("process_record_id", None) is None:
            raise BlameUserException("All Java2 invocations must specify either a class_name or an object_ref, or else give a process ID")
        
        if jar_lib is not None:
            task_descriptor["task_private"]["jar_lib"] = jar_lib
            for jar_ref in jar_lib:
                task_descriptor["dependencies"].append(jar_ref)

        if not is_tail_spawn:
            sha = hashlib.sha1()
            hash_update_with_structure(sha, [args, n_outputs])
            hash_update_with_structure(sha, class_name)
            hash_update_with_structure(sha, object_ref)
            hash_update_with_structure(sha, jar_lib)
            name_prefix = "java2:%s:" % (sha.hexdigest())
            task_descriptor["expected_outputs"] = ["%s%d" % (name_prefix, i) for i in range(n_outputs)]            
        
        if class_name is not None:
            task_descriptor["task_private"]["class_name"] = class_name
        if object_ref is not None:
            task_descriptor["task_private"]["object_ref"] = object_ref
            task_descriptor["dependencies"].append(object_ref)
        if args is not None:
            task_descriptor["task_private"]["args"] = args
        add_package_dep(parent_task_record.package_ref, task_descriptor)
        
        return ProcExecutor.build_task_descriptor(task_descriptor, parent_task_record, n_extra_outputs=0, is_tail_spawn=is_tail_spawn, accept_ref_list_for_single=True, **kwargs)
        
    def get_command(self):
        jar_filenames = []
        for ref in self.task_private['jar_lib']:
            obj_store_filename = retrieve_filename_for_ref(ref, self.task_record, False)
            with open(obj_store_filename, 'r') as f:
                with tempfile.NamedTemporaryFile(suffix='.jar', delete=False) as temp_f:
                    shutil.copyfileobj(f, temp_f)
                    jar_filenames.append(temp_f.name)
        return ["java", "-Xmx2048M", "-cp", str(':'.join(jar_filenames)), "com.asgow.ciel.executor.Java2Executor"]

    @staticmethod
    def can_run():
        return test_program(["java", "-version"], "Java")

########NEW FILE########
__FILENAME__ = ocaml
# Copyright (c) 2011 Anil Madhavapeddy <Anil.Madhavapeddy@cl.cam.ac.uk>
#
# Permission to use, copy, modify, and distribute this software for any
# purpose with or without fee is hereby granted, provided that the above
# copyright notice and this permission notice appear in all copies.
#
# THE SOFTWARE IS PROVIDED "AS IS" AND THE AUTHOR DISCLAIMS ALL WARRANTIES
# WITH REGARD TO THIS SOFTWARE INCLUDING ALL IMPLIED WARRANTIES OF
# MERCHANTABILITY AND FITNESS. IN NO EVENT SHALL THE AUTHOR BE LIABLE FOR
# ANY SPECIAL, DIRECT, INDIRECT, OR CONSEQUENTIAL DAMAGES OR ANY DAMAGES
# WHATSOEVER RESULTING FROM LOSS OF USE, DATA OR PROFITS, WHETHER IN AN
# ACTION OF CONTRACT, NEGLIGENCE OR OTHER TORTIOUS ACTION, ARISING OUT OF
# OR IN CONNECTION WITH THE USE OR PERFORMANCE OF THIS SOFTWARE.
from ciel.runtime.executors.proc import ProcExecutor
from ciel.runtime.exceptions import BlameUserException
import hashlib
from ciel.runtime.executors import hash_update_with_structure,\
    test_program

class OCamlExecutor(ProcExecutor):
    
    handler_name = "ocaml"
    process_cache = set()
    
    def __init__(self, worker):
        ProcExecutor.__init__(self, worker)

    @classmethod
    def check_args_valid(cls, args, n_outputs):
        if "binary" not in args:
            raise BlameUserException("All OCaml invocations must specify a binary")
            
    @classmethod
    def build_task_descriptor(cls, task_descriptor, parent_task_record, binary, fn_ref=None, args=None, n_outputs=1, is_tail_spawn=False, **kwargs):
        if binary is None:
            raise BlameUserException("All OCaml invocations must specify a binary")
        
        task_descriptor["task_private"]["binary"] = binary
        if fn_ref is not None:
            task_descriptor["task_private"]["fn_ref"] = fn_ref
            task_descriptor["dependencies"].append(fn_ref)

        if not is_tail_spawn:
            sha = hashlib.sha1()
            hash_update_with_structure(sha, [args, n_outputs])
            hash_update_with_structure(sha, binary)
            hash_update_with_structure(sha, fn_ref)
            name_prefix = "ocaml:%s:" % (sha.hexdigest())
            task_descriptor["expected_outputs"] = ["%s%d" % (name_prefix, i) for i in range(n_outputs)]            
        
        if args is not None:
            task_descriptor["task_private"]["args"] = args
        
        return ProcExecutor.build_task_descriptor(task_descriptor, parent_task_record, n_extra_outputs=0, is_tail_spawn=is_tail_spawn, is_fixed=False, accept_ref_list_for_single=True, **kwargs)
        
    def get_command(self):
        cmd = self.task_descriptor["task_private"]["binary"]
        assert(cmd)
        return cmd.split(" ")

    @staticmethod
    def can_run():
        return test_program(["ocamlc", "-where"], "OCaml")

########NEW FILE########
__FILENAME__ = proc
# Copyright (c) 2010--11 Derek Murray <derek.murray@cl.cam.ac.uk>
#                        Chris Smowton <chris.smowton@cl.cam.ac.uk>
#
# Permission to use, copy, modify, and distribute this software for any
# purpose with or without fee is hereby granted, provided that the above
# copyright notice and this permission notice appear in all copies.
#
# THE SOFTWARE IS PROVIDED "AS IS" AND THE AUTHOR DISCLAIMS ALL WARRANTIES
# WITH REGARD TO THIS SOFTWARE INCLUDING ALL IMPLIED WARRANTIES OF
# MERCHANTABILITY AND FITNESS. IN NO EVENT SHALL THE AUTHOR BE LIABLE FOR
# ANY SPECIAL, DIRECT, INDIRECT, OR CONSEQUENTIAL DAMAGES OR ANY DAMAGES
# WHATSOEVER RESULTING FROM LOSS OF USE, DATA OR PROFITS, WHETHER IN AN
# ACTION OF CONTRACT, NEGLIGENCE OR OTHER TORTIOUS ACTION, ARISING OUT OF
# OR IN CONNECTION WITH THE USE OR PERFORMANCE OF THIS SOFTWARE.
import threading
import ciel
import os
from ciel.public.references import SW2_ConcreteReference, SW2_SweetheartReference,\
    SW2_FixedReference, SW2_FutureReference, SWErrorReference
import pickle
from ciel.runtime.executors.base import BaseExecutor
from ciel.runtime.producer import write_fixed_ref_string, ref_from_string,\
    ref_from_safe_string
from ciel.runtime.block_store import get_own_netloc
from ciel.runtime.exceptions import BlameUserException, TaskFailedError,\
    MissingInputException, ReferenceUnavailableException
from ciel.runtime.executors import ContextManager,\
    spawn_task_helper, OngoingOutput, package_lookup
import subprocess
from ciel.public.io_helpers import write_framed_json, read_framed_json
import logging
from ciel.runtime.fetcher import retrieve_filename_for_ref,\
    retrieve_file_or_string_for_ref, OngoingFetch
import datetime
import time
import socket
import struct

try:
    import sendmsg
    sendmsg_enabled = True
except ImportError:
    sendmsg_enabled = False

never_reuse_process = False
def set_never_reuse_process(setting=True):
    global never_reuse_process
    ciel.log("Disabling process reuse", "PROC", logging.INFO)
    never_reuse_process = setting

# Return states for proc task termination.
PROC_EXITED = 0
PROC_MUST_KEEP = 1
PROC_MAY_KEEP = 2
PROC_ERROR = 3

class ProcExecutor(BaseExecutor):
    """Executor for running generic processes."""
    
    handler_name = "proc"
    
    def __init__(self, worker):
        BaseExecutor.__init__(self, worker)
        self.process_pool = worker.process_pool
        self.ongoing_fetches = []
        self.ongoing_outputs = dict()
        self.transmit_lock = threading.Lock()

    @classmethod
    def build_task_descriptor(cls, task_descriptor, parent_task_record, 
                              process_record_id=None, is_fixed=False, command=None, proc_pargs=[], proc_kwargs={}, force_n_outputs=None,
                              n_extra_outputs=0, extra_dependencies=[], is_tail_spawn=False, accept_ref_list_for_single=False):

        #if process_record_id is None and start_command is None:
        #    raise BlameUserException("ProcExecutor tasks must specify either process_record_id or start_command")

        if process_record_id is not None:
            task_descriptor["task_private"]["id"] = process_record_id
        if command is not None:
            task_descriptor["task_private"]["command"] = command
        task_descriptor["task_private"]["proc_pargs"] = proc_pargs
        task_descriptor["task_private"]["proc_kwargs"] = proc_kwargs
        task_descriptor["dependencies"].extend(extra_dependencies)

        task_private_id = ("%s:_private" % task_descriptor["task_id"])
        if is_fixed:
            task_private_ref = SW2_FixedReference(task_private_id, get_own_netloc())
            write_fixed_ref_string(pickle.dumps(task_descriptor["task_private"]), task_private_ref)
        else:
            task_private_ref = ref_from_string(pickle.dumps(task_descriptor["task_private"]), task_private_id)
        parent_task_record.publish_ref(task_private_ref)
        
        task_descriptor["task_private"] = task_private_ref
        task_descriptor["dependencies"].append(task_private_ref)

        if force_n_outputs is not None:        
            if "expected_outputs" in task_descriptor and len(task_descriptor["expected_outputs"]) > 0:
                raise BlameUserException("Task already had outputs, but force_n_outputs is set")
            task_descriptor["expected_outputs"] = ["%s:out:%d" % (task_descriptor["task_id"], i) for i in range(force_n_outputs)]
        
        if not is_tail_spawn:
            if len(task_descriptor["expected_outputs"]) == 1 and not accept_ref_list_for_single:
                return SW2_FutureReference(task_descriptor["expected_outputs"][0])
            else:
                return [SW2_FutureReference(refid) for refid in task_descriptor["expected_outputs"]]

    def get_command(self):
        raise TaskFailedError("Attempted to get_command() for an executor that does not define this.")
    
    def get_env(self):
        return {}

    @staticmethod
    def can_run():
        return True
    
    def _run(self, task_private, task_descriptor, task_record):
        
        with ContextManager("Task %s" % task_descriptor["task_id"]) as manager:
            self.context_manager = manager
            self._guarded_run(task_private, task_descriptor, task_record)
            
    def _guarded_run(self, task_private, task_descriptor, task_record):
        self.task_private = task_private
        self.task_record = task_record
        self.task_descriptor = task_descriptor
        self.expected_outputs = list(self.task_descriptor['expected_outputs'])
        
        self.error_details = None
        
        if "id" in task_private:
            id = task_private['id']
            self.process_record = self.process_pool.get_process_record(id)
        else:
            self.process_record = self.process_pool.get_soft_cache_process(self.__class__, task_descriptor["dependencies"])
            if self.process_record is None:
                self.process_record = self.process_pool.create_process_record(None, "json")
                if "command" in task_private:
                    if isinstance(task_private["command"], SWRealReference):
                        # Command has been passed in as a reference.
                        command = [retrieve_filename_for_ref(arg, self.task_record, False)]
                        os.chmod(command_line[0], stat.S_IRWXU)
                    else:
                        command = [task_private["command"]]
                else:
                    command = self.get_command()
                command.extend(["--write-fifo", self.process_record.get_read_fifo_name(), 
                                "--read-fifo", self.process_record.get_write_fifo_name()])
                new_proc_env = os.environ.copy()
                new_proc_env.update(self.get_env())

                new_proc = subprocess.Popen(command, env=new_proc_env, close_fds=True)
                self.process_record.set_pid(new_proc.pid)
               
        # XXX: This will block until the attached process opens the pipes.
        reader = self.process_record.get_read_fifo()
        writer = self.process_record.get_write_fifo()
        self.reader = reader
        self.writer = writer
        
        #ciel.log('Got reader and writer FIFOs', 'PROC', logging.INFO)

        write_framed_json(("start_task", task_private), writer)

        try:
            if self.process_record.protocol == 'line':
                finished = self.line_event_loop(reader, writer)
            elif self.process_record.protocol == 'json':
                finished = self.json_event_loop(reader, writer)
            else:
                raise BlameUserException('Unsupported protocol: %s' % self.process_record.protocol)
        
        except MissingInputException, mie:
            self.process_pool.delete_process_record(self.process_record)
            raise
            
        except TaskFailedError, tfe:
            finished = PROC_ERROR
            self.error_details = tfe.message
            
        except:
            ciel.log('Got unexpected error', 'PROC', logging.ERROR, True)
            finished = PROC_ERROR
        
        global never_reuse_process
        if finished == PROC_EXITED or never_reuse_process:
            self.process_pool.delete_process_record(self.process_record)
        
        elif finished == PROC_MAY_KEEP:
            self.process_pool.soft_cache_process(self.process_record, self.__class__, self.soft_cache_keys)    
        
        elif finished == PROC_MUST_KEEP:
            pass
        elif finished == PROC_ERROR:
            ciel.log('Task died with an error', 'PROC', logging.ERROR)
            for output_id in self.expected_outputs:
                task_record.publish_ref(SWErrorReference(output_id, 'RUNTIME_ERROR', self.error_details))
            self.process_pool.delete_process_record(self.process_record)
            return False
        
        return True
        
    def line_event_loop(self, reader, writer):
        """Dummy event loop for testing interactive tasks."""
        while True:
            line = reader.readline()
            if line == '':
                return True
            
            argv = line.split()
            
            if argv[0] == 'exit':
                return True
            elif argv[0] == 'echo':
                print argv[1:]
            elif argv[0] == 'filename':
                print argv[1]
            else:
                print 'Unrecognised command:', argv
        
    def open_ref(self, ref, accept_string=False, make_sweetheart=False):
        """Fetches a reference if it is available, and returns a filename for reading it.
        Options to do with eagerness, streaming, etc.
        If reference is unavailable, raises a ReferenceUnavailableException."""
        ref = self.task_record.retrieve_ref(ref)
        if not accept_string:   
            ctx = retrieve_filename_for_ref(ref, self.task_record, return_ctx=True)
        else:
            ctx = retrieve_file_or_string_for_ref(ref, self.task_record)
        if ctx.completed_ref is not None:
            if make_sweetheart:
                ctx.completed_ref = SW2_SweetheartReference.from_concrete(ctx.completed_ref, get_own_netloc())
            self.task_record.publish_ref(ctx.completed_ref)
        return ctx.to_safe_dict()
        
    def publish_fetched_ref(self, fetch):
        completed_ref = fetch.get_completed_ref()
        if completed_ref is None:
            ciel.log("Cancelling async fetch %s (chunk %d)" % (fetch.ref.id, fetch.chunk_size), "EXEC", logging.DEBUG)
        else:
            if fetch.make_sweetheart:
                completed_ref = SW2_SweetheartReference.from_concrete(completed_ref, get_own_netloc())
            self.task_record.publish_ref(completed_ref)
        
    # Setting fd_socket_name implies you can accept a sendmsg'd FD.
    def open_ref_async(self, ref, chunk_size, sole_consumer=False, make_sweetheart=False, must_block=False, fd_socket_name=None):
        if not sendmsg_enabled:
            fd_socket_name = None
            ciel.log("Not using FDs directly: module 'sendmsg' not available", "EXEC", logging.DEBUG)
        real_ref = self.task_record.retrieve_ref(ref)

        new_fetch = OngoingFetch(real_ref, chunk_size, self.task_record, sole_consumer, make_sweetheart, must_block, can_accept_fd=(fd_socket_name is not None))
        ret = {"sending_fd": False}
        ret_fd = None
        if fd_socket_name is not None:
            fd, fd_blocking = new_fetch.get_fd()
            if fd is not None:
                ret["sending_fd"] = True
                ret["blocking"] = fd_blocking
                ret_fd = fd
        if not ret["sending_fd"]:
            filename, file_blocking = new_fetch.get_filename()
            ret["filename"] = filename
            ret["blocking"] = file_blocking
        if not new_fetch.done:
            self.context_manager.add_context(new_fetch)
            self.ongoing_fetches.append(new_fetch)
        else:
            self.publish_fetched_ref(new_fetch)
        # Definitions here: "done" means we're already certain that the producer has completed successfully.
        # "blocking" means that EOF, as and when it arrives, means what it says. i.e. it's a regular file and done, or a pipe-like thing.
        ret.update({"done": new_fetch.done, "size": new_fetch.bytes})
        ciel.log("Async fetch %s (chunk %d): initial status %d bytes, done=%s, blocking=%s, sending_fd=%s" % (real_ref, chunk_size, ret["size"], ret["done"], ret["blocking"], ret["sending_fd"]), "EXEC", logging.DEBUG)

        # XXX: adding this because the OngoingFetch isn't publishing the sweetheart correctly.        
        if make_sweetheart:
            self.task_record.publish_ref(SW2_SweetheartReference(ref.id, get_own_netloc()))

        if new_fetch.done:
            if not new_fetch.success:
                ciel.log("Async fetch %s failed early" % ref, "EXEC", logging.WARNING)
                ret["error"] = "EFAILED"
        return (ret, ret_fd)
    
    def close_async_file(self, id, chunk_size):
        for fetch in self.ongoing_fetches:
            if fetch.ref.id == id and fetch.chunk_size == chunk_size:
                self.publish_fetched_ref(fetch)
                self.context_manager.remove_context(fetch)
                self.ongoing_fetches.remove(fetch)
                return
        #ciel.log("Ignored cancel for async fetch %s (chunk %d): not in progress" % (id, chunk_size), "EXEC", logging.WARNING)

    def wait_async_file(self, id, eof=None, bytes=None):
        the_fetch = None
        for fetch in self.ongoing_fetches:
            if fetch.ref.id == id:
                the_fetch = fetch
                break
        if the_fetch is None:
            ciel.log("Failed to wait for async-fetch %s: not an active transfer" % id, "EXEC", logging.WARNING)
            return {"success": False}
        if eof is not None:
            ciel.log("Waiting for fetch %s to complete" % id, "EXEC", logging.DEBUG)
            the_fetch.wait_eof()
        else:
            ciel.log("Waiting for fetch %s length to exceed %d bytes" % (id, bytes), "EXEC", logging.DEBUG)
            the_fetch.wait_bytes(bytes)
        if the_fetch.done and not the_fetch.success:
            ciel.log("Wait %s complete: transfer has failed" % id, "EXEC", logging.WARNING)
            return {"success": False}
        else:
            ret = {"size": int(the_fetch.bytes), "done": the_fetch.done, "success": True}
            ciel.log("Wait %s complete: new length=%d, EOF=%s" % (id, ret["size"], ret["done"]), "EXEC", logging.DEBUG)
            return ret
        
    def spawn(self, request_args):
        """Spawns a child task. Arguments define a task_private structure. Returns a list
        of future references."""
        
        # Args dict arrives from sw with unicode keys :(
        str_args = dict([(str(k), v) for (k, v) in request_args.items()])
        
        if "small_task" not in str_args:
            str_args['small_task'] = False
        
        return spawn_task_helper(self.task_record, **str_args)
    
    def tail_spawn(self, request_args):
        
        if request_args.get("is_fixed", False):
            request_args["process_record_id"] = self.process_record.id
        request_args["delegated_outputs"] = self.task_descriptor["expected_outputs"]
        self.spawn(request_args)
    
    def allocate_output(self, prefix=""):
        new_output_name = self.task_record.create_published_output_name(prefix)
        self.expected_outputs.append(new_output_name)
        return {"index": len(self.expected_outputs) - 1}
    
    def publish_string(self, index, str):
        """Defines a reference with the given string contents."""
        ref = ref_from_safe_string(str, self.expected_outputs[index])
        self.task_record.publish_ref(ref)
        return {"ref": ref}

    def open_output(self, index, may_pipe=False, may_stream=False, make_local_sweetheart=False, can_smart_subscribe=False, fd_socket_name=None):
        if may_pipe and not may_stream:
            raise Exception("Insane parameters: may_stream=False and may_pipe=True may well lead to deadlock")
        if index in self.ongoing_outputs:
            raise Exception("Tried to open output %d which was already open" % index)
        if not sendmsg_enabled:
            ciel.log("Not using FDs directly: module 'sendmsg' not available", "EXEC", logging.DEBUG)
            fd_socket_name = None
        output_name = self.expected_outputs[index]
        can_accept_fd = (fd_socket_name is not None)
        output_ctx = OngoingOutput(output_name, index, can_smart_subscribe, may_pipe, make_local_sweetheart, can_accept_fd, self)
        self.ongoing_outputs[index] = output_ctx
        self.context_manager.add_context(output_ctx)
        if may_stream:
            ref = output_ctx.get_stream_ref()
            self.task_record.prepublish_refs([ref])
        x, is_fd = output_ctx.get_filename_or_fd()
        if is_fd:
            return ({"sending_fd": True}, x)
        else:
            return ({"sending_fd": False, "filename": x}, None)

    def stop_output(self, index):
        self.context_manager.remove_context(self.ongoing_outputs[index])
        del self.ongoing_outputs[index]

    def close_output(self, index, size=None):
        output = self.ongoing_outputs[index]
        if size is None:
            size = output.get_size()
        output.size_update(size)
        self.stop_output(index)
        ret_ref = output.get_completed_ref()
        self.task_record.publish_ref(ret_ref)
        return {"ref": ret_ref}

    def log(self, message):
        t = datetime.datetime.now()
        timestamp = time.mktime(t.timetuple()) + t.microsecond / 1e6
        self.worker.master_proxy.log(self.task_descriptor["job"], self.task_descriptor["task_id"], timestamp, message)

    def rollback_output(self, index):
        self.ongoing_outputs[index].rollback()
        self.stop_output(index)

    def output_size_update(self, index, size):
        self.ongoing_outputs[index].size_update(size)

    def _subscribe_output(self, index, chunk_size):
        message = ("subscribe", {"index": index, "chunk_size": chunk_size})
        with self.transmit_lock:
            write_framed_json(message, self.writer)

    def _unsubscribe_output(self, index):
        message = ("unsubscribe", {"index": index})
        with self.transmit_lock:
            write_framed_json(message, self.writer)
           
    def json_event_loop(self, reader, writer):
        while True:

            try:
                (method, args) = read_framed_json(reader)
            except:
                ciel.log('Error reading in JSON event loop', 'PROC', logging.WARN, True)
                return PROC_ERROR
                
            #ciel.log('Method is %s' % repr(method), 'PROC', logging.INFO)
            response = None
            response_fd = None
            
            try:
                if method == 'open_ref':
                    
                    if "ref" not in args:
                        ciel.log('Missing required argument key: ref', 'PROC', logging.ERROR, False)
                        return PROC_ERROR
                    
                    try:
                        response = self.open_ref(**args)
                    except ReferenceUnavailableException:
                        response = {'error' : 'EWOULDBLOCK'}
                        
                elif method == "open_ref_async":
                    
                    if "ref" not in args or "chunk_size" not in args:
                        ciel.log("Missing required argument key: open_ref_async needs both 'ref' and 'chunk_size'", "PROC", logging.ERROR, False)
                        return PROC_ERROR
            
                    try:
                        response, response_fd = self.open_ref_async(**args)
                    except ReferenceUnavailableException:
                        response = {"error": "EWOULDBLOCK"}
                        
                elif method == "wait_stream":
                    response = self.wait_async_file(**args)
                    
                elif method == "close_stream":
                    self.close_async_file(args["id"], args["chunk_size"])
                    
                elif method == 'spawn':
                    
                    response = self.spawn(args)
                                        
                elif method == 'tail_spawn':
                    
                    response = self.tail_spawn(args)
                    
                elif method == 'allocate_output':
                    
                    response = self.allocate_output(**args)
                    
                elif method == 'publish_string':
                    
                    response = self.publish_string(**args)

                elif method == 'log':
                    # No response.
                    self.log(**args)

                elif method == 'open_output':
                    
                    try:
                        index = int(args['index'])
                        if index < 0 or index > len(self.expected_outputs):
                            ciel.log('Invalid argument value: i (index) out of bounds [0, %s)' % self.expected_outputs, 'PROC', logging.ERROR, False)
                            return PROC_ERROR
                    except KeyError:
                        if len(self.task_descriptor['expected_outputs']) == 1:
                            args["index"] = 0
                        else:
                            ciel.log('Missing argument key: i (index), and >1 expected output so could not infer index', 'PROC', logging.ERROR, False)
                            return PROC_ERROR
                    
                    response, response_fd = self.open_output(**args)
                        
                elif method == 'close_output':
    
                    try:
                        index = int(args['index'])
                        if index < 0 or index > len(self.expected_outputs):
                            ciel.log('Invalid argument value: i (index) out of bounds [0, %s)' % self.expected_outputs, 'PROC', logging.ERROR, False)
                            return PROC_ERROR
                    except KeyError:
                        if len(self.task_descriptor['expected_outputs']) == 1:
                            args["index"] = 0
                        else:
                            ciel.log('Missing argument key: i (index), and >1 expected output so could not infer index', 'PROC', logging.ERROR, False)
                            return PROC_ERROR
                        
                    response = self.close_output(**args)
                    
                elif method == 'rollback_output':
    
                    try:
                        index = int(args['index'])
                        if index < 0 or index > len(self.expected_outputs):
                            ciel.log('Invalid argument value: i (index) out of bounds [0, %s)' % self.expected_outputs, 'PROC', logging.ERROR, False)
                            return PROC_ERROR
                    except KeyError:
                        if len(self.task_descriptor['expected_outputs']) == 1:
                            args["index"] = 0
                        else:
                            ciel.log('Missing argument key: i (index), and >1 expected output so could not infer index', 'PROC', logging.ERROR, False)
                            return PROC_ERROR
                        
                    response = {'ref' : self.rollback_output(**args)}
                    
                elif method == "advert":
                    self.output_size_update(**args)
    
                elif method == "package_lookup":
                    response = {"value": package_lookup(self.task_record, self.block_store, args["key"])}
    
                elif method == 'error':
                    ciel.log('Task reported error: %s' % args["report"], 'PROC', logging.ERROR, False)
                    raise TaskFailedError(args["report"])
    
                elif method == 'exit':
                    
                    if args["keep_process"] == "must_keep":
                        return PROC_MUST_KEEP
                    elif args["keep_process"] == "may_keep":
                        self.soft_cache_keys = args.get("soft_cache_keys", [])
                        return PROC_MAY_KEEP
                    elif args["keep_process"] == "no":
                        return PROC_EXITED
                    else:
                        ciel.log("Bad exit status from task: %s" % args, "PROC", logging.ERROR)
                
                else:
                    ciel.log('Invalid method: %s' % method, 'PROC', logging.WARN, False)
                    return PROC_ERROR

            except MissingInputException, mie:
                ciel.log("Task died due to missing input", 'PROC', logging.WARN)
                raise

            except TaskFailedError:
                raise

            except:
                ciel.log('Error during method handling in JSON event loop', 'PROC', logging.ERROR, True)
                return PROC_ERROR
        
            try:
                if response is not None:
                    with self.transmit_lock:
                        write_framed_json((method, response), writer)
                if response_fd is not None:
                    socket_name = args["fd_socket_name"]
                    sock = socket.socket(socket.AF_UNIX)
                    sock.connect(socket_name)
                    sendmsg.sendmsg(fd=sock.fileno(), data="FD", ancillary=(socket.SOL_SOCKET, sendmsg.SCM_RIGHTS, struct.pack("i", response_fd)))
                    os.close(response_fd)
                    sock.close()
            except:
                ciel.log('Error writing response in JSON event loop', 'PROC', logging.WARN, True)
                return PROC_ERROR
        
        return True
    

########NEW FILE########
__FILENAME__ = simple
# Copyright (c) 2010-11 Chris Smowton <Chris.Smowton@cl.cam.ac.uk>
#
# Permission to use, copy, modify, and distribute this software for any
# purpose with or without fee is hereby granted, provided that the above
# copyright notice and this permission notice appear in all copies.
#
# THE SOFTWARE IS PROVIDED "AS IS" AND THE AUTHOR DISCLAIMS ALL WARRANTIES
# WITH REGARD TO THIS SOFTWARE INCLUDING ALL IMPLIED WARRANTIES OF
# MERCHANTABILITY AND FITNESS. IN NO EVENT SHALL THE AUTHOR BE LIABLE FOR
# ANY SPECIAL, DIRECT, INDIRECT, OR CONSEQUENTIAL DAMAGES OR ANY DAMAGES
# WHATSOEVER RESULTING FROM LOSS OF USE, DATA OR PROFITS, WHETHER IN AN
# ACTION OF CONTRACT, NEGLIGENCE OR OTHER TORTIOUS ACTION, ARISING OUT OF
# OR IN CONNECTION WITH THE USE OR PERFORMANCE OF THIS SOFTWARE.
import hashlib
from ciel.public.references import SW2_FutureReference, SWRealReference
import ciel
import logging
import threading
import datetime
import time
import subprocess
from subprocess import PIPE
from ciel.runtime.executors.base import BaseExecutor
from ciel.runtime.exceptions import BlameUserException
from ciel.runtime.executors import hash_update_with_structure,\
    ContextManager, list_with, add_running_child, remove_running_child
from ciel.runtime.object_cache import ref_from_object,\
    retrieve_object_for_ref
from ciel.runtime.fetcher import retrieve_filenames_for_refs, OngoingFetch
from ciel.runtime.producer import make_local_output

class SimpleExecutor(BaseExecutor):

    def __init__(self, worker):
        BaseExecutor.__init__(self, worker)

    @classmethod
    def build_task_descriptor(cls, task_descriptor, parent_task_record, args, n_outputs, is_tail_spawn=False, handler_name=None):

        # This is needed to work around the fact that stdinout has its own implementation of build_task_descriptor, so
        # we can't rely using cls.handler_name to find the actual executor.
        if handler_name is None:
            handler_name = cls.handler_name

        if is_tail_spawn and len(task_descriptor["expected_outputs"]) != n_outputs:
            raise BlameUserException("SimpleExecutor being built with delegated outputs %s but n_outputs=%d" % (task_descriptor["expected_outputs"], n_outputs))

        # Throw early if the args are bad
        cls.check_args_valid(args, n_outputs)

        # Discover required ref IDs for this executor
        reqd_refs = cls.get_required_refs(args)
        task_descriptor["dependencies"].extend(reqd_refs)

        sha = hashlib.sha1()
        hash_update_with_structure(sha, [args, n_outputs])
        name_prefix = "%s:%s:" % (handler_name, sha.hexdigest())

        # Name our outputs
        if not is_tail_spawn:
            task_descriptor["expected_outputs"] = ["%s%d" % (name_prefix, i) for i in range(n_outputs)]

        # Add the args dict
        args_name = "%ssimple_exec_args" % name_prefix
        args_ref = ref_from_object(args, "pickle", args_name)
        parent_task_record.publish_ref(args_ref)
        task_descriptor["dependencies"].append(args_ref)
        task_descriptor["task_private"]["simple_exec_args"] = args_ref
        
        BaseExecutor.build_task_descriptor(task_descriptor, parent_task_record)

        if is_tail_spawn:
            return None
        else:
            return [SW2_FutureReference(x) for x in task_descriptor["expected_outputs"]]
        
    def resolve_required_refs(self, args):
        try:
            args["inputs"] = [self.task_record.retrieve_ref(ref) for ref in args["inputs"]]
        except KeyError:
            pass

    @classmethod
    def get_required_refs(cls, args):
        required = []
        
        try:
            required.extend([x for x in args["command_line"] if isinstance(x, SWRealReference)])
        except KeyError:
            pass
        
        try:
            # Shallow copy
            required.extend(list(args["inputs"]))
        except KeyError:
            pass
        
        return required

    @classmethod
    def check_args_valid(cls, args, n_outputs):
        if "inputs" in args:
            for ref in args["inputs"]:
                if not isinstance(ref, SWRealReference):
                    raise BlameUserException("Simple executors need args['inputs'] to be a list of references. %s is not a reference." % ref)

    @staticmethod
    def can_run():
        return True

    def _run(self, task_private, task_descriptor, task_record):
        self.task_record = task_record
        self.task_id = task_descriptor["task_id"]
        self.output_ids = task_descriptor["expected_outputs"]
        self.output_refs = [None for _ in range(len(self.output_ids))]
        self.succeeded = False
        self.args = retrieve_object_for_ref(task_private["simple_exec_args"], "pickle", self.task_record)

        try:
            self.debug_opts = self.args['debug_options']
        except KeyError:
            self.debug_opts = []
        self.resolve_required_refs(self.args)
        try:
            self._execute()
            for ref in self.output_refs:
                if ref is not None:
                    self.task_record.publish_ref(ref)
                else:
                    ciel.log.error("Executor failed to define output %s" % ref.id, "EXEC", logging.WARNING)
            self.succeeded = True
        except:
            ciel.log.error("Task execution failed", "EXEC", logging.ERROR, True)
            raise
        finally:
            self.cleanup_task()
        
    def cleanup_task(self):
        self._cleanup_task()
    
    def _cleanup_task(self):
        pass

class ProcessRunningExecutor(SimpleExecutor):

    def __init__(self, worker):
        SimpleExecutor.__init__(self, worker)

        self._lock = threading.Lock()
        self.proc = None
        self.context_mgr = None

    def _execute(self):
        self.context_mgr = ContextManager("Simple Task %s" % self.task_id)
        with self.context_mgr:
            self.guarded_execute()

    def guarded_execute(self):
        try:
            self.input_refs = self.args['inputs']
        except KeyError:
            self.input_refs = []
        try:
            self.stream_output = self.args['stream_output']
        except KeyError:
            self.stream_output = False
        try:
            self.pipe_output = self.args['pipe_output']
        except KeyError:
            self.pipe_output = False
        try:
            self.eager_fetch = self.args['eager_fetch']
        except KeyError:
            self.eager_fetch = False
        try:
            self.stream_chunk_size = self.args['stream_chunk_size']
        except KeyError:
            self.stream_chunk_size = 67108864

        try:
            self.make_sweetheart = self.args['make_sweetheart']
            if not isinstance(self.make_sweetheart, list):
                self.make_sweetheart = [self.make_sweetheart]
        except KeyError:
            self.make_sweetheart = []

        file_inputs = None
        push_threads = None

        if self.eager_fetch:
            file_inputs = retrieve_filenames_for_refs(self.input_refs, self.task_record)
        else:

            push_threads = [OngoingFetch(ref, chunk_size=self.stream_chunk_size, task_record=self.task_record, must_block=True) for ref in self.input_refs]

            for thread in push_threads:
                self.context_mgr.add_context(thread)

        # TODO: Make these use OngoingOutputs and the context manager.                
        with list_with([make_local_output(id, may_pipe=self.pipe_output) for id in self.output_ids]) as out_file_contexts:

            if self.stream_output:
       
                stream_refs = [ctx.get_stream_ref() for ctx in out_file_contexts]
                self.task_record.prepublish_refs(stream_refs)

            # We do these last, as these are the calls which can lead to stalls whilst we await a stream's beginning or end.
            if file_inputs is None:
                file_inputs = []
                for thread in push_threads:
                    (filename, is_blocking) = thread.get_filename()
                    if is_blocking is not None:
                        assert is_blocking is True
                    file_inputs.append(filename)
            
            file_outputs = [filename for (filename, _) in (ctx.get_filename_or_fd() for ctx in out_file_contexts)]
            
            self.proc = self.start_process(file_inputs, file_outputs)
            add_running_child(self.proc)

            rc = self.await_process(file_inputs, file_outputs)
            remove_running_child(self.proc)

            self.proc = None

            #        if "trace_io" in self.debug_opts:
            #            transfer_ctx.log_traces()

            if rc != 0:
                raise OSError()

        for i, output in enumerate(out_file_contexts):
            self.output_refs[i] = output.get_completed_ref()

        ciel.engine.publish("worker_event", "Executor: Done")

    def start_process(self, input_files, output_files):
        raise Exception("Must override start_process when subclassing ProcessRunningExecutor")
        
    def await_process(self, input_files, output_files):
        rc = self.proc.wait()
        return rc

    def _cleanup_task(self):
        pass

    def _abort(self):
        if self.proc is not None:
            self.proc.kill()
            
class FilenamesOnStdinExecutor(ProcessRunningExecutor):
    
    def __init__(self, worker):
        ProcessRunningExecutor.__init__(self, worker)

        self.last_event_time = None
        self.current_state = "Starting up"
        self.state_times = dict()

    def change_state(self, new_state):
        time_now = datetime.datetime.now()
        old_state_time = time_now - self.last_event_time
        old_state_secs = float(old_state_time.seconds) + (float(old_state_time.microseconds) / 10**6)
        if self.current_state not in self.state_times:
            self.state_times[self.current_state] = old_state_secs
        else:
            self.state_times[self.current_state] += old_state_secs
        self.last_event_time = time_now
        self.current_state = new_state

    def resolve_required_refs(self, args):
        SimpleExecutor.resolve_required_refs(self, args)
        try:
            args["lib"] = [self.task_record.retrieve_ref(ref) for ref in args["lib"]]
        except KeyError:
            pass

    @classmethod
    def get_required_refs(cls, args):
        l = SimpleExecutor.get_required_refs(args)
        try:
            l.extend(args["lib"])
        except KeyError:
            pass
        return l

    def start_process(self, input_files, output_files):

        try:
            self.argv = self.args['argv']
        except KeyError:
            self.argv = []

        self.before_execute()
        ciel.engine.publish("worker_event", "Executor: running")

        if "go_slow" in self.debug_opts:
            ciel.log.error("DEBUG: Executor sleep(3)'ing", "EXEC", logging.DEBUG)
            time.sleep(3)

        proc = subprocess.Popen(self.get_process_args(), shell=False, stdin=PIPE, stdout=PIPE, stderr=None, close_fds=True)
        self.last_event_time = datetime.datetime.now()
        self.change_state("Writing input details")
        
        proc.stdin.write("%d,%d,%d\0" % (len(input_files), len(output_files), len(self.argv)))
        for x in input_files:
            proc.stdin.write("%s\0" % x)
        for x in output_files:
            proc.stdin.write("%s\0" % x)
        for x in self.argv:
            proc.stdin.write("%s\0" % x)
        proc.stdin.close()
        self.change_state("Waiting for FIFO pickup")

        _ = proc.stdout.read(1)
        #print 'Got byte back from Executor'

        return proc

    def gather_io_trace(self):
        anything_read = False
        while True:
            try:
                message = ""
                while True:
                    c = self.proc.stdout.read(1)
                    if not anything_read:
                        self.change_state("Gathering IO trace")
                        anything_read = True
                    if c == ",":
                        if message[0] == "C":
                            timestamp = float(message[1:])
                            ciel.engine.publish("worker_event", "Process log %f Computing" % timestamp)
                        elif message[0] == "I":
                            try:
                                params = message[1:].split("|")
                                stream_id = int(params[0])
                                timestamp = float(params[1])
                                ciel.engine.publish("worker_event", "Process log %f Waiting %d" % (timestamp, stream_id))
                            except:
                                ciel.log.error("Malformed data from stdout: %s" % message)
                                raise
                        else:
                            ciel.log.error("Malformed data from stdout: %s" % message)
                            raise Exception("Malformed stuff")
                        break
                    elif c == "":
                        raise Exception("Stdout closed")
                    else:
                        message = message + c
            except Exception as e:
                ciel.log.error("Error gathering I/O trace", "EXEC", logging.DEBUG, True)
                break

    def await_process(self, input_files, output_files):
        self.change_state("Running")
        if "trace_io" in self.debug_opts:
            ciel.log.error("DEBUG: Executor gathering an I/O trace from child", "EXEC", logging.DEBUG)
            self.gather_io_trace()
        rc = self.proc.wait()
        self.change_state("Done")
        ciel.log.error("Process terminated. Stats:", "EXEC", logging.DEBUG)
        for key, value in self.state_times.items():
            ciel.log.error("Time in state %s: %s seconds" % (key, value), "EXEC", logging.DEBUG)
        return rc

    def get_process_args(self):
        raise Exception("Must override get_process_args subclassing FilenamesOnStdinExecutor")

########NEW FILE########
__FILENAME__ = stdinout
# Copyright (c) 2010--2011 Derek Murray <Derek.Murray@cl.cam.ac.uk>
#                          Chris Smowton <Chris.Smowton@cl.cam.ac.uk>
#
# Permission to use, copy, modify, and distribute this software for any
# purpose with or without fee is hereby granted, provided that the above
# copyright notice and this permission notice appear in all copies.
#
# THE SOFTWARE IS PROVIDED "AS IS" AND THE AUTHOR DISCLAIMS ALL WARRANTIES
# WITH REGARD TO THIS SOFTWARE INCLUDING ALL IMPLIED WARRANTIES OF
# MERCHANTABILITY AND FITNESS. IN NO EVENT SHALL THE AUTHOR BE LIABLE FOR
# ANY SPECIAL, DIRECT, INDIRECT, OR CONSEQUENTIAL DAMAGES OR ANY DAMAGES
# WHATSOEVER RESULTING FROM LOSS OF USE, DATA OR PROFITS, WHETHER IN AN
# ACTION OF CONTRACT, NEGLIGENCE OR OTHER TORTIOUS ACTION, ARISING OUT OF
# OR IN CONNECTION WITH THE USE OR PERFORMANCE OF THIS SOFTWARE.
from ciel.public.references import SWRealReference
import stat
import os
import subprocess
import ciel
import logging
import shutil
from subprocess import PIPE
import errno
from ciel.runtime.executors.simple import ProcessRunningExecutor
from ciel.runtime.exceptions import BlameUserException
from ciel.runtime.fetcher import retrieve_filename_for_ref
from ciel.runtime.executors import list_with

class SWStdinoutExecutor(ProcessRunningExecutor):
    
    handler_name = "stdinout"

    def __init__(self, worker):
        ProcessRunningExecutor.__init__(self, worker)

    @classmethod
    def build_task_descriptor(cls, task_descriptor, parent_task_record, args, is_tail_spawn=False):
        return ProcessRunningExecutor.build_task_descriptor(task_descriptor, parent_task_record, args, 1, is_tail_spawn, SWStdinoutExecutor.handler_name)

    @classmethod
    def check_args_valid(cls, args, n_outputs):

        ProcessRunningExecutor.check_args_valid(args, n_outputs)
        if n_outputs != 1:
            raise BlameUserException("Stdinout executor must have one output")
        if "command_line" not in args:
            raise BlameUserException('Incorrect arguments to the stdinout executor: %s' % repr(args))

    def start_process(self, input_files, output_files):

        command_line = self.args["command_line"]

        for i, arg in enumerate(command_line):
            if isinstance(arg, SWRealReference):
                # Command line argument has been passed in as a reference.
                command_line[i] = retrieve_filename_for_ref(arg, self.task_record, False)
                if i == 0:
                    # First argument must be executable.
                    os.chmod(command_line[0], stat.S_IRWXU)
        
        ciel.log.error("Executing stdinout with: %s" % " ".join(map(str, command_line)), 'EXEC', logging.DEBUG)

        with open(output_files[0], "w") as temp_output_fp:
            # This hopefully avoids the race condition in subprocess.Popen()
            return subprocess.Popen(map(str, command_line), stdin=PIPE, stdout=temp_output_fp, close_fds=True)

    def await_process(self, input_files, output_files):

        with list_with([open(filename, 'r') for filename in input_files]) as fileobjs:
            for fileobj in fileobjs:
                try:
                    shutil.copyfileobj(fileobj, self.proc.stdin)
                except IOError, e:
                    if e.errno == errno.EPIPE:
                        ciel.log.error('Abandoning cat due to EPIPE', 'EXEC', logging.WARNING)
                        break
                    else:
                        raise

        self.proc.stdin.close()
        rc = self.proc.wait()
        return rc

########NEW FILE########
__FILENAME__ = sync
# Copyright (c) 2010 Derek Murray <Derek.Murray@cl.cam.ac.uk>
#
# Permission to use, copy, modify, and distribute this software for any
# purpose with or without fee is hereby granted, provided that the above
# copyright notice and this permission notice appear in all copies.
#
# THE SOFTWARE IS PROVIDED "AS IS" AND THE AUTHOR DISCLAIMS ALL WARRANTIES
# WITH REGARD TO THIS SOFTWARE INCLUDING ALL IMPLIED WARRANTIES OF
# MERCHANTABILITY AND FITNESS. IN NO EVENT SHALL THE AUTHOR BE LIABLE FOR
# ANY SPECIAL, DIRECT, INDIRECT, OR CONSEQUENTIAL DAMAGES OR ANY DAMAGES
# WHATSOEVER RESULTING FROM LOSS OF USE, DATA OR PROFITS, WHETHER IN AN
# ACTION OF CONTRACT, NEGLIGENCE OR OTHER TORTIOUS ACTION, ARISING OUT OF
# OR IN CONNECTION WITH THE USE OR PERFORMANCE OF THIS SOFTWARE.
from ciel.runtime.object_cache import ref_from_object
from ciel.runtime.executors.simple import SimpleExecutor
from ciel.runtime.exceptions import BlameUserException

class SyncExecutor(SimpleExecutor):

    handler_name = "sync"
    
    def __init__(self, worker):
        SimpleExecutor.__init__(self, worker)

    @classmethod
    def check_args_valid(cls, args, n_outputs):
        SimpleExecutor.check_args_valid(args, n_outputs)
        if "inputs" not in args or n_outputs != 1:
            raise BlameUserException('Incorrect arguments to the sync executor: %s' % repr(args))            

    def _execute(self):
        reflist = [self.task_record.retrieve_ref(x) for x in self.args["inputs"]]
        self.output_refs[0] = ref_from_object(reflist, "json", self.output_ids[0])

########NEW FILE########
__FILENAME__ = fetcher
# Copyright (c) 2010--11 Chris Smowton <Chris.Smowton@cl.cam.ac.uk>
#
# Permission to use, copy, modify, and distribute this software for any
# purpose with or without fee is hereby granted, provided that the above
# copyright notice and this permission notice appear in all copies.
#
# THE SOFTWARE IS PROVIDED "AS IS" AND THE AUTHOR DISCLAIMS ALL WARRANTIES
# WITH REGARD TO THIS SOFTWARE INCLUDING ALL IMPLIED WARRANTIES OF
# MERCHANTABILITY AND FITNESS. IN NO EVENT SHALL THE AUTHOR BE LIABLE FOR
# ANY SPECIAL, DIRECT, INDIRECT, OR CONSEQUENTIAL DAMAGES OR ANY DAMAGES
# WHATSOEVER RESULTING FROM LOSS OF USE, DATA OR PROFITS, WHETHER IN AN
# ACTION OF CONTRACT, NEGLIGENCE OR OTHER TORTIOUS ACTION, ARISING OUT OF
# OR IN CONNECTION WITH THE USE OR PERFORMANCE OF THIS SOFTWARE.

from ciel.public.references import SW2_ConcreteReference, SW2_StreamReference, SW2_SocketStreamReference,\
    SWDataValue, SWErrorReference, SW2_FixedReference, decode_datavalue,\
    SW2_FetchReference, decode_datavalue_string, encode_datavalue,\
    SW2_TombstoneReference

import tempfile
import subprocess
import ciel
import logging
import threading
import os
from ciel.runtime.pycurl_data_fetch import HttpTransferContext
from ciel.runtime.tcp_data_fetch import TcpTransferContext
from ciel.runtime.block_store import filename_for_ref, producer_filename,\
    get_own_netloc, create_datavalue_file
from ciel.runtime.producer import get_producer_for_id,\
    ref_from_external_file, ref_from_string
from ciel.runtime.exceptions import ErrorReferenceError,\
    MissingInputException
import hashlib
import contextlib
import urllib2
import urlparse

class AsyncPushThread:

    def __init__(self, ref, read_filename, write_filename, fetch_ip):
        self.ref = ref
        self.fetch_ip = fetch_ip
        self.next_threshold = fetch_ip.chunk_size
        self.success = None
        self.lock = threading.RLock()
        self.fetch_done = False
        self.stream_done = False
        self.stream_started = False
        self.bytes_copied = 0
        self.bytes_available = 0
        self.completed_ref = None
        self.condvar = threading.Condition(self.lock)
        self.thread = None
        self.read_filename = read_filename
        self.write_filename = write_filename

    def _check_completion(self):
        if self.success is False:
            ciel.log("Fetch for %s failed" % self.ref, "EXEC", logging.WARNING)
            return False
        elif self.success is True:
            ciel.log("Fetch for %s completed; using file directly" % self.ref, "EXEC", logging.DEBUG)
            return True
        else:
            return False

    def check_completion(self):
        ret = self._check_completion()
        if ret:
            self.fetch_ip.set_filename(self.read_filename, True)
        return ret

    def start(self):
        if not self.check_completion():
            self.thread = threading.Thread(target=self.thread_main)
            self.thread.start()

    def thread_main(self):

        with self.lock:
            if self.check_completion():
                return
            while self.bytes_available < self.next_threshold and not self.fetch_done:
                self.condvar.wait()
            if self.check_completion():
                return
            else:
                self.stream_started = True
        ciel.log("Fetch for %s got more than %d bytes; commencing asynchronous push" % (self.ref, self.fetch_ip.chunk_size), "EXEC", logging.DEBUG)

        self.copy_loop()

    def copy_loop(self):
        
        try:
            self.fetch_ip.set_filename(self.write_filename, True)
            with open(self.read_filename, "r") as input_fp:
                with open(self.write_filename, "w") as output_fp:
                    while True:
                        while True:
                            buf = input_fp.read(4096)
                            output_fp.write(buf)
                            self.bytes_copied += len(buf)
                            with self.lock:
                                if self.success is False or (self.bytes_copied == self.bytes_available and self.fetch_done):
                                    self.stream_done = True
                                    self.condvar.notify_all()
                                    ciel.log("FIFO-push for %s complete (success: %s)" % (self.ref, self.success), "EXEC", logging.DEBUG)
                                    return
                            if len(buf) < 4096:
                                # EOF, for now.
                                break
                        with self.lock:
                            self.next_threshold = self.bytes_copied + self.fetch_ip.chunk_size
                            while self.bytes_available < self.next_threshold and not self.fetch_done:
                                self.condvar.wait()
        except Exception as e:
            ciel.log("Push thread for %s died with exception %s" % (self.ref, e), "EXEC", logging.WARNING)
            with self.lock:
                self.stream_done = True
                self.condvar.notify_all()
                
    def result(self, success):
        with self.lock:
            if self.success is None:
                self.success = success
                self.fetch_done = True
                self.condvar.notify_all()
            # Else we've already failed due to a reset.

    def progress(self, bytes_downloaded):
        with self.lock:
            self.bytes_available = bytes_downloaded
            if self.bytes_available >= self.next_threshold:
                self.condvar.notify_all()

    def reset(self):
        ciel.log("Reset of streamed fetch for %s!" % self.ref, "EXEC", logging.WARNING)
        should_cancel = False
        with self.lock:
            if self.stream_started:
                should_cancel = True
        if should_cancel:
            ciel.log("FIFO-stream had begun: failing transfer", "EXEC", logging.ERROR)
            self.fetch_ip.cancel()

class PlanFailedError(Exception):
    pass

class FetchInProgress:

    def __init__(self, ref, result_callback, reset_callback, start_filename_callback, start_fd_callback, string_callback, progress_callback, chunk_size, may_pipe, sole_consumer, must_block, task_record):
        self.lock = threading.RLock()
        self.result_callback = result_callback
        self.reset_callback = reset_callback
        self.start_filename_callback = start_filename_callback
        self.start_fd_callback = start_fd_callback
        self.string_callback = string_callback
        self.progress_callback = progress_callback
        self.chunk_size = chunk_size
        self.may_pipe = may_pipe
        self.sole_consumer = sole_consumer
        self.must_block = must_block
        self.task_record = task_record
        self.pusher_thread = None
        self.ref = ref
        self.producer = None
        self.cat_process = None
        self.started = False
        self.done = False
        self.cancelled = False
        self.success = None
        self.form_plan()
        
    def form_plan(self):
        self.current_plan = 0
        self.plans = []
        if isinstance(self.ref, SWDataValue):
            self.plans.append(self.resolve_dataval)
        elif isinstance(self.ref, SW2_FetchReference):
            self.plans.append(self.http_fetch)
        else:
            self.plans.append(self.use_local_file)
            self.plans.append(self.attach_local_producer)
            if isinstance(self.ref, SW2_ConcreteReference):
                self.plans.append(self.http_fetch)
            elif isinstance(self.ref, SW2_StreamReference):
                if isinstance(self.ref, SW2_SocketStreamReference):
                    self.plans.append(self.tcp_fetch)
                self.plans.append(self.http_fetch)

    def start_fetch(self):
        self.run_plans()

    def run_plans(self):
        while self.current_plan < len(self.plans):
            try:
                self.plans[self.current_plan]()
                return
            except PlanFailedError:
                self.current_plan += 1

    def run_next_plan(self):
        self.current_plan += 1
        self.run_plans()

    def resolve_dataval(self):
        if self.string_callback is not None:
            decoded_dataval = decode_datavalue(self.ref)
            self.string_callback(decoded_dataval)
        else:
            create_datavalue_file(self.ref)
            self.set_filename(filename_for_ref(self.ref), True)
            self.result(True, None)

    def use_local_file(self):
        filename = filename_for_ref(self.ref)
        if os.path.exists(filename):
            self.set_filename(filename, True)
            self.result(True, None)
        else:
            raise PlanFailedError("Plan use-local-file failed for %s: no such file %s" % (self.ref, filename), "BLOCKSTORE", logging.DEBUG)

    def attach_local_producer(self):
        producer = get_producer_for_id(self.ref.id)
        if producer is None:
            raise PlanFailedError("Plan attach-local-producer failed for %s: not being produced here" % self.ref, "BLOCKSTORE", logging.DEBUG)
        else:
            is_pipe = producer.subscribe(self, try_direct=(self.may_pipe and self.sole_consumer))
            if is_pipe:
                ciel.log("Fetch-ref %s: attached to direct pipe!" % self.ref, "BLOCKSTORE", logging.DEBUG)
                filename = producer.get_fifo_filename()
            else:
                ciel.log("Fetch-ref %s: following local producer's file" % self.ref, "BLOCKSTORE", logging.DEBUG)
                filename = producer_filename(self.ref.id)
            self.set_filename(filename, is_pipe)

    def http_fetch(self):
        self.producer = HttpTransferContext(self.ref, self)
        self.producer.start()

    def tcp_fetch(self):
        if (not self.may_pipe) or (not self.sole_consumer):
            raise PlanFailedError("TCP-Fetch currently only capable of delivering a pipe")
        self.producer = TcpTransferContext(self.ref, self.chunk_size, self)
        self.producer.start()
                
    ### Start callbacks from above
    def result(self, success, result_ref=None):
        with self.lock:
            if not success:
                if not self.started:
                    self.run_next_plan()
                    return
            self.producer = None
            self.done = True
            self.success = success
        if self.pusher_thread is not None:
            self.pusher_thread.result(success)
        self.result_callback(success, result_ref)

    def reset(self):
        if self.pusher_thread is not None:
            self.pusher_thread.reset()
        self.reset_callback()

    def progress(self, bytes):
        if self.pusher_thread is not None:
            self.pusher_thread.progress(bytes)
        if self.progress_callback is not None:
            self.progress_callback(bytes)
            
    def create_fifo(self):
        fifo_name = tempfile.mktemp(prefix="ciel-socket-fifo")
        os.mkfifo(fifo_name)
        return fifo_name

    def set_fd(self, fd, is_pipe):
        # TODO: handle FDs that might point to regular files.
        assert is_pipe
        self.started = True
        if self.start_fd_callback is not None:
            self.start_fd_callback(fd, is_pipe)
        else:
            fifo_name = self.create_fifo()
            self.cat_process = subprocess.Popen(["cat > %s" % fifo_name], shell=True, stdin=fd, close_fds=True)
            os.close(fd)
            self.start_filename_callback(fifo_name, True)

    def set_filename(self, filename, is_pipe):
        self.started = True
        if (not is_pipe) and self.must_block:
            fifo_name = self.create_fifo()
            self.pusher_thread = AsyncPushThread(self.ref, filename, fifo_name, self)
            self.pusher_thread.start()
        else:
            self.start_filename_callback(filename, is_pipe)

    def cancel(self):
        with self.lock:
            self.cancelled = True
            producer = self.producer
        if producer is not None:
            producer.unsubscribe(self)
        if self.cat_process is not None:
            try:
                self.cat_process.kill()
            except Exception as e:
                ciel.log("Fetcher for %s failed to kill 'cat': %s" % (self.ref.id, repr(e)), "FETCHER", logging.ERROR)

# After you call this, you'll get some callbacks:
# 1. A start_filename or start_fd to announce that the transfer has begun and you can use the given filename or FD.
# 1a. Or, if the data was very short, perhaps a string-callback which concludes the transfer.
# 2. A series of progress callbacks to update you on how many bytes have been written
# 3. Perhaps a reset callback, indicating the transfer has rewound to the beginning.
# 4. A result callback, stating whether the transfer was successful, 
#    and if so, perhaps giving a reference to a local copy.
# Only the final result, reset and start-filename callbacks are non-optional:
# * If you omit start_fd_callback and a provider gives an FD, it will be cat'd into a FIFO 
#   and the name of that FIFO supplied.
# * If you omit string_callback and a provider supplies a string, it will be written to a file
# * If you omit progress_callback, you won't get progress notifications until the transfer is complete.
# Parameters:
# * may_pipe: allows a producer to supply data via a channel that blocks the producer until the consumer
#             has read sufficient data, e.g. a pipe or socket. Must be False if you intend to wait for completion.
# * sole_consumer: If False, a copy of the file will be made to local disk as well as being supplied to the consumer.
#                  If True, the file might be directly supplied to the consumer, likely dependent on may_pipe.
def fetch_ref_async(ref, result_callback, reset_callback, start_filename_callback, 
                    start_fd_callback=None, string_callback=None, progress_callback=None, 
                    chunk_size=67108864, may_pipe=False, sole_consumer=False,
                    must_block=False, task_record=None):

    if isinstance(ref, SWErrorReference):
        raise ErrorReferenceError(ref)
    if isinstance(ref, SW2_FixedReference):
        assert ref.fixed_netloc == get_own_netloc()

    new_client = FetchInProgress(ref, result_callback, reset_callback, 
                                 start_filename_callback, start_fd_callback, 
                                 string_callback, progress_callback, chunk_size,
                                 may_pipe, sole_consumer, must_block, task_record)
    new_client.start_fetch()
    return new_client

class SynchronousTransfer:
        
    def __init__(self, ref, task_record):
        self.ref = ref
        self.filename = None
        self.str = None
        self.success = None
        self.completed_ref = None
        self.task_record = task_record
        self.finished_event = threading.Event()

    def result(self, success, completed_ref):
        self.success = success
        self.completed_ref = completed_ref
        self.finished_event.set()

    def reset(self):
        pass

    def start_filename(self, filename, is_pipe):
        self.filename = filename

    def return_string(self, str):
        self.str = str
        self.success = True
        self.finished_event.set()

    def wait(self):
        self.finished_event.wait()
        
class FileOrString:
    
    def __init__(self, strdata=None, filename=None, completed_ref=None):
        self.str = strdata
        self.filename = filename
        self.completed_ref = completed_ref
            
    @staticmethod
    def from_dict(in_dict):
        return FileOrString(**in_dict)
    
    @staticmethod
    def from_safe_dict(in_dict):
        try:
            in_dict["strdata"] = decode_datavalue_string(in_dict["strdata"])
        except KeyError:
            pass
        return FileOrString(**in_dict)
    
    def to_dict(self):
        if self.str is not None:
            return {"strdata": self.str}
        else:
            return {"filename": self.filename}
        
    def to_safe_dict(self):
        if self.str is not None:
            return {"strdata": encode_datavalue(self.str)}
        else:
            return {"filename": self.filename}

    def to_ref(self, refid):
        if self.str is not None:
            ref = ref_from_string(self.str, refid)
        else:
            ref = ref_from_external_file(self.filename, refid)
        return ref

    def to_str(self):
        if self.str is not None:
            return self.str
        else:
            with open(self.filename, "r") as f:
                return f.read()
            
def sync_retrieve_refs(refs, task_record, accept_string=False):
    
    ctxs = []
    
    for ref in refs:
        sync_transfer = SynchronousTransfer(ref, task_record)
        ciel.log("Synchronous fetch ref %s" % ref.id, "BLOCKSTORE", logging.DEBUG)
        if accept_string:
            kwargs = {"string_callback": sync_transfer.return_string}
        else:
            kwargs = {}
        fetch_ref_async(ref, sync_transfer.result, sync_transfer.reset, sync_transfer.start_filename, task_record=task_record, **kwargs)
        ctxs.append(sync_transfer)
            
    for ctx in ctxs:
        ctx.wait()
            
    failed_transfers = filter(lambda x: not x.success, ctxs)
    if len(failed_transfers) > 0:
        raise MissingInputException(dict([(ctx.ref.id, SW2_TombstoneReference(ctx.ref.id, ctx.ref.location_hints)) for ctx in failed_transfers]))
    return ctxs

def retrieve_files_or_strings_for_refs(refs, task_record):
    
    ctxs = sync_retrieve_refs(refs, task_record, accept_string=True)
    return [FileOrString(ctx.str, ctx.filename, ctx.completed_ref) for ctx in ctxs]

def retrieve_file_or_string_for_ref(ref, task_record):
    
    return retrieve_files_or_strings_for_refs([ref], task_record)[0]

def retrieve_filenames_for_refs(refs, task_record, return_ctx=False):
        
    ctxs = sync_retrieve_refs(refs, task_record, accept_string=False)
    if return_ctx:
        return [FileOrString(None, ctx.filename, ctx.completed_ref) for ctx in ctxs]
    else:
        return [x.filename for x in ctxs]

def retrieve_filename_for_ref(ref, task_record, return_ctx=False):

    return retrieve_filenames_for_refs([ref], task_record, return_ctx)[0]

def get_ref_for_url(url, version, task_id):
    """
    Returns a SW2_ConcreteReference for the data stored at the given URL.
    Currently, the version is ignored, but we imagine using this for e.g.
    HTTP ETags, which would raise an error if the data changed.
    """

    parsed_url = urlparse.urlparse(url)
    if parsed_url.scheme == 'swbs':
        # URL is in a Skywriting Block Store, so we can make a reference
        # for it directly.
        id = parsed_url.path[1:]
        ref = SW2_ConcreteReference(id, None)
        ref.add_location_hint(parsed_url.netloc)
    else:
        # URL is outside the cluster, so we have to fetch it. We use
        # content-based addressing to name the fetched data.
        hash = hashlib.sha1()

        # 1. Fetch URL to a file-like object.
        with contextlib.closing(urllib2.urlopen(url)) as url_file:

            # 2. Hash its contents and write it to disk.
            with tempfile.NamedTemporaryFile('wb', 4096, delete=False) as fetch_file:
                fetch_filename = fetch_file.name
                while True:
                    chunk = url_file.read(4096)
                    if not chunk:
                        break
                    hash.update(chunk)
                    fetch_file.write(chunk)

        # 3. Store the fetched file in the block store, named by the
        #    content hash.
        id = 'urlfetch:%s' % hash.hexdigest()
        ref = ref_from_external_file(fetch_filename, id)

    return ref

class OngoingFetch:

    def __init__(self, ref, chunk_size, task_record, sole_consumer=False, make_sweetheart=False, must_block=False, can_accept_fd=False):
        self.lock = threading.Lock()
        self.condvar = threading.Condition(self.lock)
        self.bytes = 0
        self.ref = ref
        self.chunk_size = chunk_size
        self.sole_consumer = sole_consumer
        self.make_sweetheart = make_sweetheart
        self.task_record = task_record
        self.done = False
        self.success = None
        self.filename = None
        self.fd = None
        self.completed_ref = None
        self.file_blocking = None
        # may_pipe = True because this class is only used for async operations.
        # The only current danger of pipes is that waiting for a transfer to complete might deadlock.
        if can_accept_fd:
            fd_callback = self.set_fd
        else:
            fd_callback = None
        self.fetch_ctx = fetch_ref_async(ref, 
                                         result_callback=self.result,
                                         progress_callback=self.progress, 
                                         reset_callback=self.reset,
                                         start_filename_callback=self.set_filename,
                                         start_fd_callback=fd_callback,
                                         chunk_size=chunk_size,
                                         may_pipe=True,
                                         must_block=must_block,
                                         sole_consumer=sole_consumer,
                                         task_record=task_record)
        
    def progress(self, bytes):
        with self.lock:
            self.bytes = bytes
            self.condvar.notify_all()

    def result(self, success, completed_ref):
        with self.lock:
            self.done = True
            self.success = success
            self.completed_ref = completed_ref
            self.condvar.notify_all()

    def reset(self):
        with self.lock:
            self.done = True
            self.success = False
            self.condvar.notify_all()
        # XXX: This is causing failures. Is it a vestige?
        #self.client.cancel()

    def set_filename(self, filename, is_blocking):
        with self.lock:
            self.filename = filename
            self.file_blocking = is_blocking
            self.condvar.notify_all()
            
    def set_fd(self, fd, is_blocking):
        with self.lock:
            self.fd = fd
            self.file_blocking = is_blocking
            self.condvar.notify_all()

    def get_filename(self):
        with self.lock:
            while self.filename is None and self.success is not False:
                self.condvar.wait()
            if self.filename is not None:
                return (self.filename, self.file_blocking)
            else:
                return (None, None)
        
    def get_fd(self):
        with self.lock:
            while self.fd is None and self.filename is None and self.success is not False:
                self.condvar.wait()
            if self.fd is not None:
                return (self.fd, self.file_blocking)
            else:
                return (None, None)

    def get_completed_ref(self):
        return self.completed_ref

    def wait_bytes(self, bytes):
        with self.lock:
            while self.bytes < bytes and not self.done:
                self.condvar.wait()

    def wait_eof(self):
        with self.lock:
            while not self.done:
                self.condvar.wait()

    def cancel(self):
        self.fetch_ctx.cancel()

    def __enter__(self):
        return self

    def __exit__(self, exnt, exnv, exnbt):
        if not self.done:
            ciel.log("Cancelling async fetch for %s" % self.ref, "EXEC", logging.WARNING)
            self.cancel()
        return False

def retrieve_strings_for_refs(refs, task_record):

    ctxs = retrieve_files_or_strings_for_refs(refs, task_record)
    return [ctx.to_str() for ctx in ctxs]

def retrieve_string_for_ref(ref, task_record):
        
    return retrieve_strings_for_refs([ref], task_record)[0]

########NEW FILE########
__FILENAME__ = file_watcher
# Copyright (c) 2010--11 Chris Smowton <Chris.Smowton@cl.cam.ac.uk>
#
# Permission to use, copy, modify, and distribute this software for any
# purpose with or without fee is hereby granted, provided that the above
# copyright notice and this permission notice appear in all copies.
#
# THE SOFTWARE IS PROVIDED "AS IS" AND THE AUTHOR DISCLAIMS ALL WARRANTIES
# WITH REGARD TO THIS SOFTWARE INCLUDING ALL IMPLIED WARRANTIES OF
# MERCHANTABILITY AND FITNESS. IN NO EVENT SHALL THE AUTHOR BE LIABLE FOR
# ANY SPECIAL, DIRECT, INDIRECT, OR CONSEQUENTIAL DAMAGES OR ANY DAMAGES
# WHATSOEVER RESULTING FROM LOSS OF USE, DATA OR PROFITS, WHETHER IN AN
# ACTION OF CONTRACT, NEGLIGENCE OR OTHER TORTIOUS ACTION, ARISING OUT OF
# OR IN CONNECTION WITH THE USE OR PERFORMANCE OF THIS SOFTWARE.

import threading
import os
import ciel
import logging

singleton_watcher = None

class FileWatcherThread:

    def __init__(self, bus, block_store):
        self.bus = bus
        self.block_store = block_store
        self.thread = threading.Thread(target=self.main_loop)
        self.lock = threading.Lock()
        self.condvar = threading.Condition(self.lock)
        self.active_watches = set()
        self.should_stop = False

    def subscribe(self):
        self.bus.subscribe('start', self.start, 75)
        self.bus.subscribe('stop', self.stop, 10)

    def start(self):
        self.thread.start()

    def stop(self):
        with self.lock:
            self.should_stop = True
            self.condvar.notify_all()

    def create_watch(self, output_ctx):
        return FileWatch(output_ctx, self)

    def add_watch(self, watch):
        with self.lock:
            self.active_watches.add(watch)
            self.condvar.notify_all()

    def remove_watch(self, watch):
        with self.lock:
            self.active_watches.discard(watch)
            self.condvar.notify_all()

    def main_loop(self):
        with self.lock:
            while True:
                dead_watches = []
                if self.should_stop:
                    return
                for watch in self.active_watches:
                    try:
                        watch.poll()
                    except Exception as e:
                        ciel.log("Watch died with exception %s: cancelled" % e, "FILE_WATCHER", logging.ERROR)
                        dead_watches.append(watch)
                for watch in dead_watches:
                    self.active_watches.discard(watch)
                self.condvar.wait(1)

class FileWatch:

    def __init__(self, output_ctx, thread):
        self.id = output_ctx.refid
        self.filename = thread.block_store.producer_filename(self.id)
        self.thread = thread
        self.output_ctx = output_ctx

    def poll(self):
        st = os.stat(self.filename)
        self.output_ctx.size_update(st.st_size)

    # Out-of-thread-call
    def start(self):
        self.thread.add_watch(self)

    # Out-of-thread call
    def cancel(self):
        self.thread.remove_watch(self)

    # Out-of-thread call
    def set_chunk_size(self, new_chunk_size):
        ciel.log("File-watch for %s: new chunk size %d. (ignored)" % (self.id, new_chunk_size), "FILE_WATCHER", logging.DEBUG)
        
def create_watcher_thread(bus, block_store):
    global singleton_watcher
    singleton_watcher = FileWatcherThread(bus, block_store)
    singleton_watcher.subscribe()

def get_watcher_thread():
    return singleton_watcher

def create_watch(output):
    return singleton_watcher.create_watch(output)

########NEW FILE########
__FILENAME__ = lighttpd
# Copyright (c) 2010--11 Chris Smowton <Chris.Smowton@cl.cam.ac.uk>
#
# Permission to use, copy, modify, and distribute this software for any
# purpose with or without fee is hereby granted, provided that the above
# copyright notice and this permission notice appear in all copies.
#
# THE SOFTWARE IS PROVIDED "AS IS" AND THE AUTHOR DISCLAIMS ALL WARRANTIES
# WITH REGARD TO THIS SOFTWARE INCLUDING ALL IMPLIED WARRANTIES OF
# MERCHANTABILITY AND FITNESS. IN NO EVENT SHALL THE AUTHOR BE LIABLE FOR
# ANY SPECIAL, DIRECT, INDIRECT, OR CONSEQUENTIAL DAMAGES OR ANY DAMAGES
# WHATSOEVER RESULTING FROM LOSS OF USE, DATA OR PROFITS, WHETHER IN AN
# ACTION OF CONTRACT, NEGLIGENCE OR OTHER TORTIOUS ACTION, ARISING OUT OF
# OR IN CONNECTION WITH THE USE OR PERFORMANCE OF THIS SOFTWARE.

from cherrypy.process import plugins
import subprocess
import os.path
import tempfile
import shutil

class LighttpdAdapter(plugins.SimplePlugin):

    def __init__(self, bus, static_content_root, local_port):
        self.local_port = local_port
        self.static_content_root = static_content_root
        self.lighty_ancillary_dir = tempfile.mkdtemp(prefix=os.getenv('TEMP', default='/tmp/ciel-lighttpd-'))
        self.lighty_conf = os.path.join(self.lighty_ancillary_dir, "ciel-lighttpd.conf")
        self.socket_path = os.path.join(self.lighty_ancillary_dir, "ciel-socket")
        self.bus = bus

    def subscribe(self):
        self.bus.subscribe("start", self.start, 75)
        self.bus.subscribe("stop", self.stop, 10)

    def start(self):
        with open(self.lighty_conf, "w") as conf_out:
            print >>conf_out, """
# Skywriting lighttpd configuration file

## modules to load
# at least mod_access and mod_accesslog should be loaded
# all other module should only be loaded if really neccesary
server.modules              = (
                                "mod_access",
                               "mod_fastcgi",
                                "mod_accesslog" )

## A static document-root. For virtual hosting take a look at the
## mod_simple_vhost module.
server.document-root        = "{ciel_static_content}"

## where to send error-messages to
server.errorlog             = "{ciel_log}/lighttpd.log"

# files to check for if .../ is requested
index-file.names            = ( "index.php", "index.html",
                                "index.htm", "default.htm" )

# mimetype mapping
mimetype.assign             = (
  ".rpm"          =>      "application/x-rpm",
  ".pdf"          =>      "application/pdf",
  ".sig"          =>      "application/pgp-signature",
  ".spl"          =>      "application/futuresplash",
  ".class"        =>      "application/octet-stream",
  ".ps"           =>      "application/postscript",
  ".torrent"      =>      "application/x-bittorrent",
  ".dvi"          =>      "application/x-dvi",
  ".gz"           =>      "application/x-gzip",
  ".pac"          =>      "application/x-ns-proxy-autoconfig",
  ".swf"          =>      "application/x-shockwave-flash",
  ".tar.gz"       =>      "application/x-tgz",
  ".tgz"          =>      "application/x-tgz",
  ".tar"          =>      "application/x-tar",
  ".zip"          =>      "application/zip",
  ".mp3"          =>      "audio/mpeg",
  ".m3u"          =>      "audio/x-mpegurl",
  ".wma"          =>      "audio/x-ms-wma",
  ".wax"          =>      "audio/x-ms-wax",
  ".ogg"          =>      "application/ogg",
  ".wav"          =>      "audio/x-wav",
  ".gif"          =>      "image/gif",
  ".jar"          =>      "application/x-java-archive",
  ".jpg"          =>      "image/jpeg",
  ".jpeg"         =>      "image/jpeg",
  ".png"          =>      "image/png",
  ".xbm"          =>      "image/x-xbitmap",
  ".xpm"          =>      "image/x-xpixmap",
  ".xwd"          =>      "image/x-xwindowdump",
  ".css"          =>      "text/css",
  ".html"         =>      "text/html",
  ".htm"          =>      "text/html",
  ".js"           =>      "text/javascript",
  ".asc"          =>      "text/plain",
  ".c"            =>      "text/plain",
  ".cpp"          =>      "text/plain",
  ".log"          =>      "text/plain",
  ".conf"         =>      "text/plain",
  ".text"         =>      "text/plain",
  ".txt"          =>      "text/plain",
  ".dtd"          =>      "text/xml",
  ".xml"          =>      "text/xml",
  ".mpeg"         =>      "video/mpeg",
  ".mpg"          =>      "video/mpeg",
  ".mov"          =>      "video/quicktime",
  ".qt"           =>      "video/quicktime",
  ".avi"          =>      "video/x-msvideo",
  ".asf"          =>      "video/x-ms-asf",
  ".asx"          =>      "video/x-ms-asf",
  ".wmv"          =>      "video/x-ms-wmv",
  ".bz2"          =>      "application/x-bzip",
  ".tbz"          =>      "application/x-bzip-compressed-tar",
  ".tar.bz2"      =>      "application/x-bzip-compressed-tar",
  # default mime type
  ""              =>      "application/octet-stream",
 )

#### accesslog module
accesslog.filename          = "{ciel_log}/lighttpd-access.log"

## bind to port (default: 80)
server.port                = {ciel_port}

#### fastcgi module
## read fastcgi.txt for more info
## for PHP don't forget to set cgi.fix_pathinfo = 1 in the php.ini
fastcgi.server             = ( "/control/" =>
                               ( "cherrypy" =>
                                 (
                                   "socket" => "{ciel_socket}",
                   "max-procs" => 1,
                   "check-local" => "disable",
                   "docroot" => "/",
                                 )
                               )
                            )

# Disable stat-cache, as files are liable to change size under lighty
server.stat-cache-engine = "disable"
""".format(ciel_port=self.local_port, ciel_log=self.lighty_ancillary_dir, ciel_static_content=self.static_content_root, ciel_socket=self.socket_path)
        self.lighty_proc = subprocess.Popen(["lighttpd", "-D", "-f", self.lighty_conf])

    def stop(self):
        try:
            self.lighty_proc.kill()
            shutil.rmtree(self.lighty_ancillary_dir)
        except:
            pass

########NEW FILE########
__FILENAME__ = local_task_graph
# Copyright (c) 2011 Chris Smowton <Chris.Smowton@cl.cam.ac.uk>
#
# Permission to use, copy, modify, and distribute this software for any
# purpose with or without fee is hereby granted, provided that the above
# copyright notice and this permission notice appear in all copies.
#
# THE SOFTWARE IS PROVIDED "AS IS" AND THE AUTHOR DISCLAIMS ALL WARRANTIES
# WITH REGARD TO THIS SOFTWARE INCLUDING ALL IMPLIED WARRANTIES OF
# MERCHANTABILITY AND FITNESS. IN NO EVENT SHALL THE AUTHOR BE LIABLE FOR
# ANY SPECIAL, DIRECT, INDIRECT, OR CONSEQUENTIAL DAMAGES OR ANY DAMAGES
# WHATSOEVER RESULTING FROM LOSS OF USE, DATA OR PROFITS, WHETHER IN AN
# ACTION OF CONTRACT, NEGLIGENCE OR OTHER TORTIOUS ACTION, ARISING OUT OF
# OR IN CONNECTION WITH THE USE OR PERFORMANCE OF THIS SOFTWARE.

from ciel.runtime.task_graph import DynamicTaskGraph, TaskGraphUpdate
from ciel.runtime.task import build_taskpool_task_from_descriptor
import Queue
import ciel
import logging

class LocalJobOutput:
    
    def __init__(self, required_refs, taskset=None):
        self.required_refs = set(required_refs)
        self.taskset = taskset
    def is_queued_streaming(self):
        return False
    def is_blocked(self):
        return True
    def is_complete(self):
        return len(self.required_refs) == 0
    def notify_ref_table_updated(self, ref_table_entry):
        self.required_refs.remove(ref_table_entry.ref)
        # Commented out because the refcounting should take care of it.
        #if self.is_complete() and self.taskset is not None:
        #    self.taskset.notify_completed()

class LocalTaskGraph(DynamicTaskGraph):

    def __init__(self, execution_features, runnable_queues):
        DynamicTaskGraph.__init__(self)
        self.root_task_ids = set()
        self.execution_features = execution_features
        self.runnable_queues = runnable_queues

    def add_root_task_id(self, root_task_id):
        self.root_task_ids.add(root_task_id)
        
    def remove_root_task_id(self, root_task_id):
        self.root_task_ids.remove(root_task_id)

    def spawn_and_publish(self, spawns, refs, producer=None, taskset=None):
        
        producer_task = None
        if producer is not None:
            producer_task = self.get_task(producer["task_id"])
            taskset = producer_task.taskset
        upd = TaskGraphUpdate()
        for spawn in spawns:
            task_object = build_taskpool_task_from_descriptor(spawn, producer_task, taskset)
            upd.spawn(task_object)
        for ref in refs:
            upd.publish(ref, producer_task)
        upd.commit(self)

    def task_runnable(self, task):
        ciel.log('Task %s became runnable!' % task.task_id, 'LTG', logging.DEBUG)
        if self.execution_features.can_run(task.handler):
            if task.task_id in self.root_task_ids:
                ciel.log('Putting task %s in the runnableQ because it is a root' % task.task_id, 'LTG', logging.DEBUG)
                try:
                    self.runnable_queues[task.scheduling_class].put(task)
                except KeyError:
                    try:
                        self.runnable_queues['*'].put(task)
                    except KeyError:
                        ciel.log('Scheduling class %s not supported on this worker (for task %s)' % (task.scheduling_class, task.task_id), 'LTG', logging.ERROR)
                        raise
                task.taskset.inc_runnable_count()
            else:
                try:
                    is_small_task = task.worker_private['hint'] == 'small_task'
                    if is_small_task:
                        ciel.log('Putting task %s in the runnableQ because it is small' % task.task_id, 'LTG', logging.DEBUG)
                        try:
                            self.runnable_queues[task.scheduling_class].put(task)
                        except KeyError:
                            try:
                                self.runnable_queues['*'].put(task)
                            except KeyError:
                                ciel.log('Scheduling class %s not supported on this worker (for task %s)' % (task.scheduling_class, task.task_id), 'LTG', logging.ERROR)
                                raise
                        self.taskset.inc_runnable_count()
                except KeyError:
                    pass
                except AttributeError:
                    pass

    def get_runnable_task(self):
        ret = self.get_runnable_task_as_task()
        if ret is not None:
            ret = ret.as_descriptor()
        return ret
        
    def get_runnable_task_as_task(self):
        try:
            return self.runnable_small_tasks.get_nowait()
        except Queue.Empty:
            return None

########NEW FILE########
__FILENAME__ = cluster_view
# Copyright (c) 2010 Derek Murray <derek.murray@cl.cam.ac.uk>
#
# Permission to use, copy, modify, and distribute this software for any
# purpose with or without fee is hereby granted, provided that the above
# copyright notice and this permission notice appear in all copies.
#
# THE SOFTWARE IS PROVIDED "AS IS" AND THE AUTHOR DISCLAIMS ALL WARRANTIES
# WITH REGARD TO THIS SOFTWARE INCLUDING ALL IMPLIED WARRANTIES OF
# MERCHANTABILITY AND FITNESS. IN NO EVENT SHALL THE AUTHOR BE LIABLE FOR
# ANY SPECIAL, DIRECT, INDIRECT, OR CONSEQUENTIAL DAMAGES OR ANY DAMAGES
# WHATSOEVER RESULTING FROM LOSS OF USE, DATA OR PROFITS, WHETHER IN AN
# ACTION OF CONTRACT, NEGLIGENCE OR OTHER TORTIOUS ACTION, ARISING OUT OF
# OR IN CONNECTION WITH THE USE OR PERFORMANCE OF THIS SOFTWARE.
from ciel.runtime.master.job_pool import JOB_STATE_NAMES
from cherrypy._cperror import HTTPError
from ciel.runtime.task import TASK_STATES, TASK_STATE_NAMES
import cherrypy
import time
from ciel.public.references import SWDataValue, decode_datavalue

def table_row(key, *args):
    return '<tr><td><b>%s</b></td>' % key + ''.join(['<td>%s</td>' % str(x) for x in args]) + '</tr>'
        
def span_row(heading, cols=2):
    return '<tr><td colspan="%d" bgcolor="#cccccc" align="center">%s</td></tr>' % (cols, heading)
        
def job_link(job):
    return '<a href="/control/browse/job/%s">%s</a>' % (job.id, job.id)

def ref_link(job, ref):
    return '<a href="/control/browse/ref/%s/%s">%s</a>' % (job.id, ref.id, ref.id)

def ref_id_link(job, ref_id):
    return '<a href="/control/browse/ref/%s/%s">%s</a>' % (job.id, ref_id, ref_id)

def task_link(job, task):
    return '<a href="/control/browse/task/%s/%s">%s</a>' % (job.id, task.task_id, task.task_id)

def swbs_link(netloc, ref_id):
    return '<a href="http://%s/data/%s">Link</a>' % (netloc, ref_id)

class WebBrowserRoot:
    
    def __init__(self, job_pool):
        self.job = JobBrowserRoot(job_pool)
        self.task = TaskBrowserRoot(job_pool)
        self.ref = RefBrowserRoot(job_pool)
        
class JobBrowserRoot:

    def __init__(self, job_pool):
        self.job_pool = job_pool
        
    @cherrypy.expose
    def index(self):
        jobs = self.job_pool.get_all_job_ids()
        job_string = '<html><head><title>Job Browser</title></head>'
        job_string += '<body><table>'
        for job_id in jobs:
            job = self.job_pool.get_job_by_id(job_id)
            job_string += table_row('Job', job_link(job), JOB_STATE_NAMES[job.state])
        job_string += '</table></body></html>'
        return job_string
        
    @cherrypy.expose
    def default(self, job_id):
        try:
            job = self.job_pool.get_job_by_id(job_id)
        except KeyError:
            raise HTTPError(404)

        job_string = '<html><head><title>Job Browser</title></head>'
        job_string += '<body><table>'
        job_string += table_row('ID', job.id)
        job_string += table_row('Root task', task_link(job, job.root_task))
        job_string += table_row('State', JOB_STATE_NAMES[job.state])
        job_string += table_row('Output ref', ref_id_link(job, job.root_task.expected_outputs[0]))
        job_string += span_row('Task states')
        for name, state in TASK_STATES.items():
            try:
                job_string += table_row('Tasks ' + name, job.task_state_counts[state])
            except KeyError:
                job_string += table_row('Tasks ' + name, 0)
        job_string += span_row('Task type/duration', 5)
        job_string += table_row('*', str(job.all_tasks.get()), str(job.all_tasks.min), str(job.all_tasks.max), str(job.all_tasks.count))
        for type, avg in job.all_tasks_by_type.items():
            job_string += table_row(type, str(avg.get()), str(avg.min), str(avg.max), str(avg.count))
        job_string += '</table></body></html>'
        return job_string

class TaskBrowserRoot:
    
    def __init__(self, job_pool):
        self.job_pool = job_pool
        
    @cherrypy.expose
    def default(self, job_id, task_id):
        
        try:
            job = self.job_pool.get_job_by_id(job_id)
        except KeyError:
            raise HTTPError(404)
        
        try:
            task = job.task_graph.get_task(task_id)
        except KeyError:
            raise HTTPError(404)
        
        task_string = '<html><head><title>Task Browser</title></head>'
        task_string += '<body><table>'
        task_string += table_row('ID', task.task_id)
        task_string += table_row('State', TASK_STATE_NAMES[task.state])
        for worker in [task.get_worker()]:
            task_string += table_row('Worker', worker.netloc if worker is not None else None)
        task_string += span_row('Dependencies')
        for local_id, ref in task.dependencies.items():
            task_string += table_row(local_id, ref_link(job, ref))
        task_string += span_row('Outputs')
        for i, output_id in enumerate(task.expected_outputs):
            task_string += table_row(i, ref_id_link(job, output_id))
        task_string += span_row('History')
        for t, name in task.history:
            task_string += table_row(time.mktime(t.timetuple()) + t.microsecond / 1e6, name)
        if len(task.children) > 0:
            task_string += span_row('Children')
            for i, child in enumerate(task.children):
                task_string += table_row(i, '%s</td><td>%s</td><td>%s' % (task_link(job, child), child.handler, TASK_STATE_NAMES[child.state]))
        task_string += '</table></body></html>'
        return task_string

class RefBrowserRoot:
    
    def __init__(self, job_pool):
        self.job_pool = job_pool

    @cherrypy.expose         
    def default(self, job_id, ref_id):
        
        try:
            job = self.job_pool.get_job_by_id(job_id)
        except KeyError:
            raise HTTPError(404)
        
        try:
            ref = job.task_graph.get_reference_info(ref_id).ref
        except KeyError:
            raise HTTPError(404)

        ref_string = '<html><head><title>Task Browser</title></head>'
        ref_string += '<body><table>'
        ref_string += table_row('ID', ref_id)
        ref_string += table_row('Ref type', ref.__class__.__name__)
        if isinstance(ref, SWDataValue):
            ref_string += table_row('Value', decode_datavalue(ref))
        elif hasattr(ref, 'location_hints'):
            ref_string += span_row('Locations')
            for netloc in ref.location_hints:
                ref_string += table_row(netloc, swbs_link(netloc, ref.id))
        ref_string += '</table></body></html>'
        return ref_string

########NEW FILE########
__FILENAME__ = deferred_work
'''
Created on 17 Aug 2010

@author: dgm36
'''
from ciel.runtime.plugins import AsynchronousExecutePlugin
from threading import Timer

class DeferredWorkPlugin(AsynchronousExecutePlugin):
    
    def __init__(self, bus, event_name="deferred_work"):
        AsynchronousExecutePlugin.__init__(self, bus, 1, event_name)
        self.timers = {}
        self.current_timer_id = 0
    
    def stop(self):
        for timer in self.timers.values():
            timer.cancel()
        AsynchronousExecutePlugin.stop(self)
    
    def handle_input(self, input):
        input()
        
    def do_deferred(self, callable):
        self.receive_input(callable)
        
    def _handle_deferred_after(self, callable, timer_id):
        del self.timers[timer_id]
        callable()
        
    def do_deferred_after(self, secs, callable):
        timer_id = self.current_timer_id
        self.current_timer_id += 1
        t = Timer(secs, self.do_deferred, args=(lambda: self._handle_deferred_after(callable, timer_id), ))
        self.timers[timer_id] = t
        t.start()
        
########NEW FILE########
__FILENAME__ = hot_standby
# Copyright (c) 2011 Derek Murray <derek.murray@cl.cam.ac.uk>
#
# Permission to use, copy, modify, and distribute this software for any
# purpose with or without fee is hereby granted, provided that the above
# copyright notice and this permission notice appear in all copies.
#
# THE SOFTWARE IS PROVIDED "AS IS" AND THE AUTHOR DISCLAIMS ALL WARRANTIES
# WITH REGARD TO THIS SOFTWARE INCLUDING ALL IMPLIED WARRANTIES OF
# MERCHANTABILITY AND FITNESS. IN NO EVENT SHALL THE AUTHOR BE LIABLE FOR
# ANY SPECIAL, DIRECT, INDIRECT, OR CONSEQUENTIAL DAMAGES OR ANY DAMAGES
# WHATSOEVER RESULTING FROM LOSS OF USE, DATA OR PROFITS, WHETHER IN AN
# ACTION OF CONTRACT, NEGLIGENCE OR OTHER TORTIOUS ACTION, ARISING OUT OF
# OR IN CONNECTION WITH THE USE OR PERFORMANCE OF THIS SOFTWARE.
from urlparse import urljoin
import httplib2
import logging
import simplejson

from cherrypy.process import plugins
from Queue import Queue, Empty
from ciel.runtime.plugins import THREAD_TERMINATOR
import threading
import ciel
    
class PingerPoker:
    pass
PINGER_POKER = PingerPoker()
    
class MasterRecoveryMonitor(plugins.SimplePlugin):
    '''
    The pinger maintains the connection between a master and a backup master.
    It operates as follows:
    
    1. The backup master registers with the primary master to receive journal
       events.
       
    2. The backup periodically pings the master to find out if it has failed.
    
    3. When the primary is deemed to have failed, the backup instructs the
       workers to re-register with it.

    4. The backup takes over at this point.
    '''
    
    def __init__(self, bus, my_url, master_url, job_pool, ping_timeout=5):
        plugins.SimplePlugin.__init__(self, bus)
        self.queue = Queue()
        self.non_urgent_queue = Queue()
        
        self.is_primary = False
        self.is_connected = False
        self.is_running = False
        
        self.thread = None
        self.my_url = my_url
        self.master_url = master_url
        self.ping_timeout = ping_timeout
        
        self.job_pool = job_pool
        
        self._lock = threading.Lock()
        self.workers = set()
                
    def subscribe(self):
        self.bus.subscribe('start', self.start, 75)
        self.bus.subscribe('stop', self.stop)
        self.bus.subscribe('poke', self.poke)
        
    def unsubscribe(self):
        self.bus.unsubscribe('start', self.start)
        self.bus.unsubscribe('stop', self.stop)
        self.bus.unsubscribe('poke', self.poke)
                
    def start(self):
        if not self.is_running:
            self.is_running = True
            self.thread = threading.Thread(target=self.thread_main, args=())
            self.thread.start()
    
    def stop(self):
        if self.is_running:
            self.is_running = False
            self.queue.put(THREAD_TERMINATOR)
            self.thread.join()
            self.thread = None
        
    def poke(self):
        self.queue.put(PINGER_POKER)
        
    def register_as_backup(self):
        h = httplib2.Http()
        h.request(urljoin(self.master_url, '/backup/'), 'POST', simplejson.dumps(self.my_url))
    
    def ping_master(self):
        h = httplib2.Http()
        try:
            response, _ = h.request(self.master_url, 'GET')
        except:
            ciel.log('Error contacting primary master', 'MONITOR', logging.WARN, True)
            return False
        if response['status'] != '200':
            ciel.log('Got unusual status from primary master: %s' % response['status'], 'MONITOR', logging.WARN)
            return False
        return True
    
    def add_worker(self, worker):
        with self._lock:
            self.workers.add(worker)
    
    def notify_all_workers(self):
        master_details = simplejson.dumps({'master' : self.my_url})
        with self._lock:
            for netloc in self.workers:
                h = httplib2.Http()
                ciel.log('Notifying worker: %s' % netloc, 'MONITOR', logging.INFO)
                try:
                    response, _ = h.request('http://%s/master/' % netloc, 'POST', master_details)
                    if response['status'] != '200':
                        ciel.log('Error %s when notifying worker of new master: %s' % (response['status'], netloc), 'MONITOR', logging.WARN, True)
                except:
                    ciel.log('Error notifying worker of new master: %s' % netloc, 'MONITOR', logging.WARN, True)
    
    def thread_main(self):
        
        # While not connected, attempt to register as a backup master.
        while not self.is_connected:
        
            try:    
                self.register_as_backup()
                ciel.log('Registered as backup master for %s' % self.master_url, 'MONITOR', logging.INFO)
                self.is_connected = True
                break
            except:
                ciel.log('Unable to register with master', 'MONITOR', logging.WARN, True)
                pass
        
            try:
                maybe_terminator = self.queue.get(block=True, timeout=self.ping_timeout)
                if not self.is_running or maybe_terminator is THREAD_TERMINATOR:
                    return
            except Empty:
                pass
        
            
        # While connected, periodically ping the master.
        while self.is_connected:
            
            try:
                new_thing = self.queue.get(block=True, timeout=self.ping_timeout)
                if not self.is_connected or not self.is_running or new_thing is THREAD_TERMINATOR:
                    return
            except Empty:
                pass
            
            try:
                if not self.ping_master():
                    self.is_connected = False
            except:
                self.is_connected = False
            
        if not self.is_running:
            return
        
        # This master is now the primary.
        self.is_primary = True
        
        self.job_pool.start_all_jobs()
        self.notify_all_workers()
            
class BackupSender:
    
    def __init__(self, bus):
        self.bus = bus
        self.standby_urls = set()
        self.queue = Queue()
        
        self.is_running = False
        self.is_logging = False
    
    def register_standby_url(self, url):
        self.is_logging = True
        self.queue.put(('U', url))

    def publish_refs(self, task_id, ref):
        if not self.is_logging:
            return
        self.queue.put(('P', task_id, ref))
        
    def add_worker(self, worker_netloc):
        if not self.is_logging:
            return
        self.queue.put(('W', worker_netloc))
        
    def add_job(self, id, root_task_descriptor):
        if not self.is_logging:
            return
        self.queue.put(('J', id, root_task_descriptor))
        
    def add_data(self, id, data):
        if not self.is_logging:
            return
        self.queue.put(('D', id, data))

    def do_publish_refs(self, task_id, ref):
        for url in self.standby_urls:
            spawn_url = urljoin(url, '/task/%s/publish' % task_id)
            h = httplib2.Http()
            h.request(spawn_url, 'POST', ref)        

    def do_add_job(self, id, root_task_descriptor):
        for url in self.standby_urls:
            spawn_url = urljoin(url, '/job/%s' % id)
            h = httplib2.Http()
            h.request(spawn_url, 'POST', root_task_descriptor)
            
    def do_add_data(self, id, data):
        for url in self.standby_urls:
            spawn_url = urljoin(url, '/data/%s' % id)
            h = httplib2.Http()
            h.request(spawn_url, 'POST', data)        
        
    def do_add_worker(self, worker_descriptor):
        for url in self.standby_urls:
            spawn_url = urljoin(url, '/worker/')
            h = httplib2.Http()
            h.request(spawn_url, 'POST', worker_descriptor)
        
    def subscribe(self):
        self.bus.subscribe('start', self.start, 75)
        self.bus.subscribe('stop', self.stop)
        
    def unsubscribe(self):
        self.bus.unsubscribe('start', self.start)
        self.bus.unsubscribe('stop', self.stop)
        
    def start(self):
        if not self.is_running:
            self.is_running = True
            self.thread = threading.Thread(target=self.thread_main, args=())
            self.thread.start()
    
    def stop(self):
        if self.is_running:
            self.is_running = False
            self.queue.put(THREAD_TERMINATOR)
            self.thread.join()
            self.thread = None
            
    def thread_main(self):
        
        while True:
            
            # While not connected, attempt to register as a backup master.
            while self.is_running:

                try:
                    maybe_terminator = self.queue.get(block=True)
                    if not self.is_running or maybe_terminator is THREAD_TERMINATOR:
                        return
                except Empty:
                    pass
                
                log_entry = maybe_terminator
                
                try:
                    if log_entry[0] == 'U':
                        self.standby_urls.add(log_entry[1])
                    elif log_entry[0] == 'P':
                        self.do_publish_refs(log_entry[1], log_entry[2])
                    elif log_entry[0] == 'W':
                        self.do_add_worker(log_entry[1])
                    elif log_entry[0] == 'J':
                        self.do_add_job(log_entry[1], log_entry[2])
                    elif log_entry[0] == 'D':
                        self.do_add_data(log_entry[1], log_entry[2])
                    else:
                        raise
                except:
                    ciel.log('Error passing log to backup master.', 'BACKUP_SENDER', logging.WARN, True)

########NEW FILE########
__FILENAME__ = job_pool
# Copyright (c) 2010 Derek Murray <derek.murray@cl.cam.ac.uk>
#
# Permission to use, copy, modify, and distribute this software for any
# purpose with or without fee is hereby granted, provided that the above
# copyright notice and this permission notice appear in all copies.
#
# THE SOFTWARE IS PROVIDED "AS IS" AND THE AUTHOR DISCLAIMS ALL WARRANTIES
# WITH REGARD TO THIS SOFTWARE INCLUDING ALL IMPLIED WARRANTIES OF
# MERCHANTABILITY AND FITNESS. IN NO EVENT SHALL THE AUTHOR BE LIABLE FOR
# ANY SPECIAL, DIRECT, INDIRECT, OR CONSEQUENTIAL DAMAGES OR ANY DAMAGES
# WHATSOEVER RESULTING FROM LOSS OF USE, DATA OR PROFITS, WHETHER IN AN
# ACTION OF CONTRACT, NEGLIGENCE OR OTHER TORTIOUS ACTION, ARISING OUT OF
# OR IN CONNECTION WITH THE USE OR PERFORMANCE OF THIS SOFTWARE.
from cherrypy.process import plugins
from ciel.public.references import SWReferenceJSONEncoder
from ciel.runtime.task import TASK_STATES, TASK_STATE_NAMES, \
    build_taskpool_task_from_descriptor, TASK_QUEUED, TASK_FAILED,\
    TASK_COMMITTED, TASK_QUEUED_STREAMING
from threading import Lock, Condition
import Queue
import ciel
import datetime
import logging
import os
import simplejson
import struct
import time
import uuid
from ciel.runtime.task_graph import DynamicTaskGraph, TaskGraphUpdate
from ciel.public.references import SWErrorReference
from ciel.runtime.master.scheduling_policy import LocalitySchedulingPolicy,\
    get_scheduling_policy
import collections

JOB_CREATED = -1
JOB_ACTIVE = 0
JOB_COMPLETED = 1
JOB_FAILED = 2
JOB_QUEUED = 3
JOB_RECOVERED = 4
JOB_CANCELLED = 5

JOB_STATES = {'CREATED': JOB_CREATED,
              'ACTIVE': JOB_ACTIVE,
              'COMPLETED': JOB_COMPLETED,
              'FAILED': JOB_FAILED,
               'QUEUED': JOB_QUEUED,
              'RECOVERED': JOB_RECOVERED,
              'CANCELLED' : JOB_CANCELLED}

JOB_STATE_NAMES = {}
for (name, number) in JOB_STATES.items():
    JOB_STATE_NAMES[number] = name

RECORD_HEADER_STRUCT = struct.Struct('!cI')

class Job:
    
    def __init__(self, id, root_task, job_dir, state, job_pool, job_options, journal=True):
        self.id = id
        self.root_task = root_task
        self.job_dir = job_dir
        
        self.job_pool = job_pool
        
        self.history = []
        
        self.state = state
        
        self.runnable_queue = Queue.Queue()
        
        self.global_queues = {}
        
        self.result_ref = None

        self.task_journal_fp = None

        self.journal = journal

        self.job_options = job_options
        
        try:
            self.journal = self.job_options['journal']
        except KeyError:
            pass

        # Start journalling immediately to capture the root task.
        if self.journal and self.task_journal_fp is None and self.job_dir is not None:
            self.task_journal_fp = open(os.path.join(self.job_dir, 'task_journal'), 'wb')


        self._lock = Lock()
        self._condition = Condition(self._lock)

        # Counters for each task state.
        self.task_state_counts = {}
        for state in TASK_STATES.values():
            self.task_state_counts[state] = 0

        self.all_tasks = RunningAverage()
        self.all_tasks_by_type = {}

        try:
            sched_opts = self.job_options["sched_opts"]
        except KeyError:
            sched_opts = {}

        try:
            self.scheduling_policy = get_scheduling_policy(self.job_options['scheduler'], **sched_opts)
        except KeyError:
            self.scheduling_policy = LocalitySchedulingPolicy()
            
        try:
            self.journal_sync_buffer = self.job_options['journal_sync_buffer']
        except KeyError:
            self.journal_sync_buffer = None
        self.journal_sync_counter = 0
        
        self.task_graph = JobTaskGraph(self, self.runnable_queue)
        
        self.workers = {}
        
        
    def restart_journalling(self):
        # Assume that the recovery process has truncated the file to the previous record boundary.
        if self.task_journal_fp is None and self.job_dir is not None:
            self.task_journal_fp = open(os.path.join(self.job_dir, 'task_journal'), 'ab')
        
    def schedule(self):
        self.job_pool.deferred_worker.do_deferred(lambda: self._schedule())
        
    def _schedule(self):
        
        ciel.log('Beginning to schedule job %s' % self.id, 'JOB', logging.DEBUG)
        
        with self._lock:
            
            # 1. Assign runnable tasks to worker queues.
            unassigned_tasks = []
            while True:
                try:
                    task = self.runnable_queue.get_nowait()
                    unassigned = True
                    self.assign_scheduling_class_to_task(task)
                    workers = self.select_workers_for_task(task)
                    for worker in workers:
                        if worker is None:
                            continue
                        ciel.log('Adding task %s to queue for worker %s' % (task.task_id, worker.id), 'SCHED', logging.DEBUG)
                        self.workers[worker].queue_task(task)
                        unassigned = False
                    if task.get_constrained_location() is None:
                        self.push_task_on_global_queue(task)
                        unassigned = False
                    if unassigned:
                        ciel.log('No workers available for task %s' % task.task_id, 'SCHED', logging.WARNING)
                        unassigned_tasks.append(task)
                except Queue.Empty:
                    break

            # 1a. If we have unassigned tasks, put them back on the queue for the next schedule.
            for task in unassigned_tasks:
                self.runnable_queue.put(task)
            
            # 2. For each worker, check if we need to assign any tasks.
            total_assigned = 0
            undersubscribed_worker_classes = []
            for worker, wstate in self.workers.items():
                for scheduling_class, capacity in worker.scheduling_classes.items():
                    num_assigned = wstate.tasks_assigned_in_class(scheduling_class)
                    while num_assigned < capacity:
                        task = wstate.pop_task_from_queue(scheduling_class)
                        if task is None:
                            break
                        elif task.state not in (TASK_QUEUED, TASK_QUEUED_STREAMING):
                            continue
                        task.set_worker(worker)
                        wstate.assign_task(task)
                        ciel.log('Executing task %s on worker %s' % (task.task_id, worker.id), 'SCHED', logging.DEBUG)
                        self.job_pool.worker_pool.execute_task_on_worker(worker, task)
                        num_assigned += 1
                        total_assigned += 1
                    if num_assigned < capacity:
                        undersubscribed_worker_classes.append((worker, scheduling_class, capacity - num_assigned))

            for worker, scheduling_class, deficit in undersubscribed_worker_classes:
                num_global_assigned = 0
                while num_global_assigned < deficit:
                    task = self.pop_task_from_global_queue(scheduling_class)
                    if task is None:
                        break
                    elif task.state not in (TASK_QUEUED, TASK_QUEUED_STREAMING):
                        continue
                    task.set_worker(worker)
                    self.workers[worker].assign_task(task)
                    ciel.log('Executing task %s on worker %s (STOLEN)' % (task.task_id, worker.id), 'SCHED', logging.DEBUG)
                    self.job_pool.worker_pool.execute_task_on_worker(worker, task)
                    num_global_assigned += 1
        
        ciel.log('Finished scheduling job %s. Tasks assigned = %d' % (self.id, total_assigned), 'JOB', logging.DEBUG)
        
    def pop_task_from_global_queue(self, scheduling_class):
        if scheduling_class == '*':
            for queue in self.global_queues.values():
                try:
                    return queue.popleft()
                except IndexError:
                    pass
            return None
        else:
            try:
                return self.global_queues[scheduling_class].popleft()
            except IndexError:
                return None
            except KeyError:
                return None
        
    def push_task_on_global_queue(self, task):
        try:
            class_queue = self.global_queues[task.scheduling_class]
        except KeyError:
            class_queue = collections.deque()
            self.global_queues[task.scheduling_class] = class_queue
        class_queue.append(task)
        
    def select_workers_for_task(self, task):
        constrained_location = task.get_constrained_location()
        if constrained_location is not None:
            return [self.job_pool.worker_pool.get_worker_at_netloc(constrained_location)]
        elif task.state in (TASK_QUEUED_STREAMING, TASK_QUEUED, TASK_COMMITTED):
            return self.scheduling_policy.select_workers_for_task(task, self.job_pool.worker_pool)
        else:
            ciel.log.error("Task %s scheduled in bad state %s; ignored" % (task, task.state), 
                               "SCHEDULER", logging.ERROR)
            raise
                
    def assign_scheduling_class_to_task(self, task):
        if task.scheduling_class is not None:
            return
        elif task.handler == 'swi':
            task.scheduling_class = 'cpu'
        elif task.handler == 'init':
            task.scheduling_class = 'cpu'
        elif task.handler == 'sync':
            task.scheduling_class = 'cpu'
        elif task.handler == 'grab':
            task.scheduling_class = 'disk'
        elif task.handler == 'java':
            task.scheduling_class = 'disk'
        else:
            task.scheduling_class = 'disk'

    def record_event(self, description):
        self.history.append((datetime.datetime.now(), description))
                    
    def set_state(self, state):
        self.record_event(JOB_STATE_NAMES[state])
        self.state = state
        evt_time = self.history[-1][0]
        ciel.log('%s %s @ %f' % (self.id, JOB_STATE_NAMES[self.state], time.mktime(evt_time.timetuple()) + evt_time.microsecond / 1e6), 'JOB', logging.INFO)

    def failed(self):
        # Done under self._lock (via _report_tasks()).
        self.set_state(JOB_FAILED)
        self.stop_journalling()
        self._condition.notify_all()

    def enqueued(self):
        self.job_pool.worker_pool.notify_job_about_current_workers(self)
        self.set_state(JOB_QUEUED)

    def completed(self, result_ref):
        # Done under self._lock (via _report_tasks()).
        self.set_state(JOB_COMPLETED)
        self.result_ref = result_ref
        self._condition.notify_all()
        self.stop_journalling()
        self.job_pool.job_completed(self)

    def activated(self):
        self.set_state(JOB_ACTIVE)
        mjo = MasterJobOutput(self.root_task.expected_outputs, self)
        for output in self.root_task.expected_outputs:
            self.task_graph.subscribe(output, mjo)
        self.task_graph.reduce_graph_for_references(self.root_task.expected_outputs)
        self.schedule()

    def cancelled(self):
        self.set_state(JOB_CANCELLED)
        self.stop_journalling()

    def stop_journalling(self):
        # Done under self._lock (via _report_tasks()).        
        if self.task_journal_fp is not None:
            self.task_journal_fp.close()
        self.task_journal_fp = None
                
        if self.job_dir is not None:
            with open(os.path.join(self.job_dir, 'result'), 'w') as result_file:
                simplejson.dump(self.result_ref, result_file, cls=SWReferenceJSONEncoder)

    def flush_journal(self):
        with self._lock:
            if self.task_journal_fp is not None:
                self.task_journal_fp.flush()
                os.fsync(self.task_journal_fp.fileno())

    def maybe_sync(self, must_sync=False):
        if must_sync or (self.journal_sync_buffer is not None and self.journal_sync_counter % self.journal_sync_buffer == 0):
            os.fsync(self.task_journal_fp.fileno())
        self.journal_sync_counter += 1

    def add_reference(self, id, ref, should_sync=False):
        # Called under self._lock (from _report_tasks()).
        if self.journal and self.task_journal_fp is not None:
            ref_details = simplejson.dumps({'id': id, 'ref': ref}, cls=SWReferenceJSONEncoder)
            self.task_journal_fp.write(RECORD_HEADER_STRUCT.pack('R', len(ref_details)))
            self.task_journal_fp.write(ref_details)
            self.maybe_sync(should_sync)
            
    def add_task(self, task, should_sync=False):
        # Called under self._lock (from _report_tasks()).
        self.task_state_counts[task.state] = self.task_state_counts[task.state] + 1
        if self.journal and self.task_journal_fp is not None:
            task_details = simplejson.dumps(task.as_descriptor(), cls=SWReferenceJSONEncoder)
            self.task_journal_fp.write(RECORD_HEADER_STRUCT.pack('T', len(task_details)))
            self.task_journal_fp.write(task_details)
            self.maybe_sync(should_sync)
            

#    def steal_task(self, worker, scheduling_class):
#        ciel.log('In steal_task(%s, %s)' % (worker.id, scheduling_class), 'LOG', logging.INFO)
#        # Stealing policy: prefer task with fewest replicas, then lowest cost on this worker.
#        best_candidate = (sys.maxint, 0, None)
#        for victim in self.workers.values():
#            if victim.worker == worker:
#                continue
#            task = victim.get_last_task_in_class(scheduling_class)
#            if task is None:
#                continue
#            num_workers = len(task.get_workers())
#            cost = self.guess_task_cost_on_worker(task, worker)
#            best_candidate = min(best_candidate, (num_workers, cost, task))
#        
#        task = best_candidate[2]
#        if task is not None:
#            task.add_worker(worker)
#            self.workers[worker].add_task(task)
#            self.job_pool.worker_pool.execute_task_on_worker(worker, task)
            
    def record_state_change(self, task, prev_state, next_state, additional=None):
        # Done under self._lock (from _report_tasks()).
        self.task_state_counts[prev_state] = self.task_state_counts[prev_state] - 1
        self.task_state_counts[next_state] = self.task_state_counts[next_state] + 1
        self.job_pool.log(task, TASK_STATE_NAMES[next_state], additional)

    def as_descriptor(self):
        counts = {}
        ret = {'job_id': self.id, 
               'task_counts': counts, 
               'state': JOB_STATE_NAMES[self.state], 
               'root_task': self.root_task.task_id if self.root_task is not None else None,
               'expected_outputs': self.root_task.expected_outputs if self.root_task is not None else None,
               'result_ref': self.result_ref,
               'job_options' : self.job_options}
        with self._lock:
            for (name, state_index) in TASK_STATES.items():
                counts[name] = self.task_state_counts[state_index]
        return ret

    def report_tasks(self, report, toplevel_task, worker):
        self.job_pool.deferred_worker.do_deferred(lambda: self._report_tasks(report, toplevel_task, worker))

    def _report_tasks(self, report, toplevel_task, worker):
        with self._lock:
    
            tx = TaskGraphUpdate()
            
            root_task = self.task_graph.get_task(report[0][0])
            
            ciel.log('Received report from task %s with %d entries' % (root_task.task_id, len(report)), 'SCHED', logging.DEBUG)
            
            try:
                self.workers[worker].deassign_task(root_task)
            except KeyError:
                # This can happen if we recieve the report after the worker is deemed to have failed. In this case, we should
                # accept the report and ignore the failed worker.
                pass

            for (parent_id, success, payload) in report:
                
                ciel.log('Processing report record from task %s' % (parent_id), 'SCHED', logging.DEBUG)
                
                parent_task = self.task_graph.get_task(parent_id)
                
                if success:
                    ciel.log('Task %s was successful' % (parent_id), 'SCHED', logging.DEBUG)
                    (spawned, published, profiling) = payload
                    parent_task.set_profiling(profiling)
                    parent_task.set_state(TASK_COMMITTED)
                    self.record_task_stats(parent_task, worker)
                    for child in spawned:
                        child_task = build_taskpool_task_from_descriptor(child, parent_task)
                        ciel.log('Task %s spawned task %s' % (parent_id, child_task.task_id), 'SCHED', logging.DEBUG)
                        tx.spawn(child_task)
                        #parent_task.children.append(child_task)
                    
                    for ref in published:
                        ciel.log('Task %s published reference %s' % (parent_id, str(ref)), 'SCHED', logging.DEBUG)
                        tx.publish(ref, parent_task)
                
                else:
                    ciel.log('Task %s failed' % (parent_id), 'SCHED', logging.WARN)
                    # Only one failed task per-report, at the moment.
                    self.investigate_task_failure(parent_task, payload)
                    self.schedule()
                    return
                    
            tx.commit(self.task_graph)
            self.task_graph.reduce_graph_for_references(toplevel_task.expected_outputs)
            
        # XXX: Need to remove assigned task from worker(s).
        self.schedule()

    def record_task_stats(self, task, worker):
        try:
            task_profiling = task.get_profiling()
            task_type = task.get_type()
            task_execution_time = task_profiling['FINISHED'] - task_profiling['STARTED']
            
            self.all_tasks.update(task_execution_time)
            try:
                self.all_tasks_by_type[task_type].update(task_execution_time)
            except KeyError:
                self.all_tasks_by_type[task_type] = RunningAverage(task_execution_time)
                
            self.workers[worker].record_task_stats(task)

        except:
            ciel.log('Error recording task statistics for task: %s' % task.task_id, 'JOB', logging.WARNING)

    def guess_task_cost_on_worker(self, task, worker):
        return self.workers[worker].load(task.scheduling_class, True)
                
    def investigate_task_failure(self, task, payload):
        self.job_pool.task_failure_investigator.investigate_task_failure(task, payload)
        
    def notify_worker_added(self, worker):
        with self._lock:
            try:
                _ = self.workers[worker] 
                return
            except KeyError:
                ciel.log('Job %s notified that worker being added' % self.id, 'JOB', logging.INFO)
                worker_state = JobWorkerState(worker)
                self.workers[worker] = worker_state
        self.schedule()
    
    def notify_worker_failed(self, worker):
        with self._lock:
            try:
                worker_state = self.workers[worker]
                del self.workers[worker]
                ciel.log('Reassigning tasks from failed worker %s for job %s' % (worker.id, self.id), 'JOB', logging.WARNING)
                for assigned in worker_state.assigned_tasks.values():
                    for failed_task in assigned:
                        failed_task.unset_worker(worker)
                        self.investigate_task_failure(failed_task, ('WORKER_FAILED', None, {}))
                for scheduling_class in worker_state.queues:
                    while True:
                        queued_task = worker_state.pop_task_from_queue(scheduling_class)
                        if queued_task is None:
                            break
                        self.runnable_queue.put(queued_task)
                        #self.investigate_task_failure(failed_task, ('WORKER_FAILED', None, {}))
                        #self.runnable_queue.put(queued_task)
                self.schedule()
            except KeyError:
                ciel.log('Weird keyerror coming out of notify_worker_failed', 'JOB', logging.WARNING, True)
                pass

class JobWorkerState:
    
    def __init__(self, worker):
        self.worker = worker
        self.assigned_tasks = {}
        self.queues = {}
        self.running_average = RunningAverage()
        self.running_average_by_type = {}
        
#    def get_last_task_in_class(self, scheduling_class):
#        ciel.log('In get_last_task_in_class(%s, %s)' % (self.worker.id, scheduling_class), 'JWS', logging.INFO)
#        eff_class = self.worker.get_effective_scheduling_class(scheduling_class)
#        try:
#            ciel.log('Returning task: %s' % (repr(self.assigned_tasks[eff_class][-1])), 'JWS', logging.INFO)
#            return self.assigned_tasks[eff_class][-1]
#        except:
#            # IndexError or KeyError is valid here.
#            return None
        
    def tasks_assigned_in_class(self, scheduling_class):
        eff_class = self.worker.get_effective_scheduling_class(scheduling_class)
        try:
            return len(self.assigned_tasks[eff_class])
        except KeyError:
            return 0
        
    def pop_task_from_queue(self, scheduling_class):
        eff_class = self.worker.get_effective_scheduling_class(scheduling_class)
        try:
            task = self.queues[eff_class].popleft()
            return task
        except KeyError:
            return None
        except IndexError:
            return None
        
    def queue_task(self, task):
        eff_class = self.worker.get_effective_scheduling_class(task.scheduling_class)
        try:
            self.queues[eff_class].append(task)
        except KeyError:
            class_queue = collections.deque()
            self.queues[eff_class] = class_queue
            class_queue.append(task)
        
    def assign_task(self, task):
        eff_class = self.worker.get_effective_scheduling_class(task.scheduling_class)
        try:
            self.assigned_tasks[eff_class].add(task)
        except KeyError:
            class_set = set()
            self.assigned_tasks[eff_class] = class_set
            class_set.add(task)
        
    def deassign_task(self, task):
        try:
            eff_class = self.worker.get_effective_scheduling_class(task.scheduling_class)
            self.assigned_tasks[eff_class].remove(task)
        except KeyError:
            # XXX: This is happening twice, once on receiving the report and again on the failure.
            pass
        
    def load(self, scheduling_class, normalized=False):
        eff_class = self.worker.get_effective_scheduling_class(scheduling_class)
        norm = float(self.worker.get_effective_scheduling_class_capacity(eff_class)) if normalized else 1.0
        ret = 0.0
        try:
            ret += len(self.queues[eff_class]) / norm
            ret += len(self.assigned_tasks[eff_class]) / norm
            return ret
        except KeyError:
            pass
        except:
            ciel.log('Weird exception in jws.load()', 'JWS', logging.ERROR, True)
        return ret

    
    def record_task_stats(self, task):
        try:
            task_profiling = task.get_profiling()
            task_type = task.get_type()
            task_execution_time = task_profiling['FINISHED'] - task_profiling['STARTED']
            
            self.running_average.update(task_execution_time)
            try:
                self.running_average_by_type[task_type].update(task_execution_time)
            except KeyError:
                self.running_average_by_type[task_type] = RunningAverage(task_execution_time)

        except:
            ciel.log('Error recording task statistics for task: %s' % task.task_id, 'JOB', logging.WARNING)


class RunningAverage:
    
    NEGATIVE_INF = float('-Inf')
    POSITIVE_INF = float('+Inf')
    
    def __init__(self, initial_observation=None):
        if initial_observation is None:
            self.min = RunningAverage.POSITIVE_INF
            self.max = RunningAverage.NEGATIVE_INF
            self.total = 0.0
            self.count = 0
        else:
            self.min = initial_observation
            self.max = initial_observation
            self.total = initial_observation
            self.count = 1
        
    def update(self, observation):
        self.total += observation
        self.count += 1
        self.max = max(self.max, observation)
        self.min = min(self.min, observation)
        
    def get(self):
        if self.count > 0:
            return self.total / self.count
        else:
            return float('+NaN')

class MasterJobOutput:
    
    def __init__(self, required_ids, job):
        self.required_ids = set(required_ids)
        self.job = job
    def is_queued_streaming(self):
        return False
    def is_blocked(self):
        return True
    def is_complete(self):
        return len(self.required_ids) == 0
    def notify_ref_table_updated(self, ref_table_entry):
        self.required_ids.discard(ref_table_entry.ref.id)
        if self.is_complete():
            self.job.completed(ref_table_entry.ref)

class JobTaskGraph(DynamicTaskGraph):
    
    
    def __init__(self, job, scheduler_queue):
        DynamicTaskGraph.__init__(self)
        self.job = job
        self.scheduler_queue = scheduler_queue
    
    def spawn(self, task, tx=None):
        self.job.add_task(task)
        DynamicTaskGraph.spawn(self, task, tx)
        
    def publish(self, reference, producing_task=None):
        self.job.add_reference(reference.id, reference)
        return DynamicTaskGraph.publish(self, reference, producing_task)
    
    def task_runnable(self, task):
        if self.job.state == JOB_ACTIVE:
            task.set_state(TASK_QUEUED)
            self.scheduler_queue.put(task)
        else:
            ciel.log('Task %s became runnable while job %s not active (%s): ignoring' % (task.task_id, self.job.id, JOB_STATE_NAMES[self.job.state]), 'JOBTASKGRAPH', logging.WARN)

    def task_failed(self, task, bindings, reason, details=None):

        ciel.log.error('Task failed because %s' % (reason, ), 'TASKPOOL', logging.WARNING)
        should_notify_outputs = False

        task.record_event(reason)

        for ref in bindings.values():
            self.publish(ref, None)

        if reason == 'WORKER_FAILED':
            # Try to reschedule task.
            task.current_attempt += 1
            # XXX: Remove this hard-coded constant. We limit the number of
            #      retries in case the task is *causing* the failures.
            if task.current_attempt > 3:
                task.set_state(TASK_FAILED)
                should_notify_outputs = True
            else:
                ciel.log.error('Rescheduling task %s after worker failure' % task.task_id, 'TASKFAIL', logging.WARNING)
                task.set_state(TASK_FAILED)
                self.task_runnable(task)
                
        elif reason == 'MISSING_INPUT':
            # Problem fetching input, so we will have to re-execute it.
            for binding in bindings.values():
                ciel.log('Missing input: %s' % str(binding), 'TASKFAIL', logging.WARNING)
            self.handle_missing_input(task)
            
        elif reason == 'RUNTIME_EXCEPTION':
            # A hard error, so kill the entire job, citing the problem.
            task.set_state(TASK_FAILED)
            should_notify_outputs = True

        if should_notify_outputs:
            for output in task.expected_outputs:
                ciel.log('Publishing error reference for %s (because %s)' % (output, reason), 'TASKFAIL', logging.ERROR)
                self.publish(SWErrorReference(output, reason, details), task)
                
        self.job.schedule()

    def handle_missing_input(self, task):
        task.set_state(TASK_FAILED)

        # Assume that all of the dependencies are unavailable.
        task.convert_dependencies_to_futures()
        
        # We will re-reduce the graph for this task, ignoring the network
        # locations for which getting the input failed.
        # N.B. We should already have published the necessary tombstone refs
        #      for the failed inputs.
        self.reduce_graph_for_tasks([task])

class JobPool(plugins.SimplePlugin):

    def __init__(self, bus, journal_root, scheduler, task_failure_investigator, deferred_worker, worker_pool, task_log_root=None):
        plugins.SimplePlugin.__init__(self, bus)
        self.journal_root = journal_root

        self.task_log_root = task_log_root
        if self.task_log_root is not None:
            try:
                self.task_log = open(os.path.join(self.task_log_root, "ciel-task-log.txt"), "w")
            except:
                import sys
                ciel.log.error("Error configuring task log root (%s), disabling task logging" % task_log_root, 'JOB_POOL', logging.WARNING)
                import traceback
                traceback.print_exc()
                self.task_log_root = None
                self.task_log = None
        else:
            self.task_log = None

        self.scheduler = scheduler
        self.task_failure_investigator = task_failure_investigator
        self.deferred_worker = deferred_worker
        self.worker_pool = worker_pool
    
        # Mapping from job ID to job object.
        self.jobs = {}
        
        
        self.current_running_job = None
        self.run_queue = Queue.Queue()
        
        self.num_running_jobs = 0
        self.max_running_jobs = 10
        
        # Synchronisation code for stopping/waiters.
        self.is_stopping = False
        self.current_waiters = 0
        self.max_concurrent_waiters = 10
        
        self._lock = Lock()
    
    def subscribe(self):
        # Higher priority than the HTTP server
        self.bus.subscribe("stop", self.server_stopping, 10)

    def unsubscribe(self):
        self.bus.unsubscribe("stop", self.server_stopping)
        
    def start_all_jobs(self):
        for job in self.jobs.values():
            self.queue_job(job)
        
    def log(self, task, state, details=None):
        if self.task_log is not None:
            log_at = datetime.datetime.now()
            log_float = time.mktime(log_at.timetuple()) + log_at.microsecond / 1e6
            print >>self.task_log, log_float, task.task_id if task is not None else None,  state, details
            self.task_log.flush()

    def server_stopping(self):
        # When the server is shutting down, we need to notify all threads
        # waiting on job completion.
        self.is_stopping = True
        for job in self.jobs.values():
            with job._lock:
                job._condition.notify_all()
        if self.task_log is not None:
            self.log(None, "STOPPING")
            self.task_log.close()

    def get_job_by_id(self, id):
        return self.jobs[id]
    
    def get_all_job_ids(self):
        return self.jobs.keys()
    
    def allocate_job_id(self):
        return str(uuid.uuid1())
    
    def add_job(self, job, sync_journal=False):
        self.jobs[job.id] = job
        
        # We will use this both for new jobs and on recovery.
        if job.root_task is not None:
            job.task_graph.spawn(job.root_task)
    
    def notify_worker_added(self, worker):
        for job in self.jobs.values():
            if job.state == JOB_ACTIVE:
                job.notify_worker_added(worker)
            
    def notify_worker_failed(self, worker):
        for job in self.jobs.values():
            if job.state == JOB_ACTIVE:
                job.notify_worker_failed(worker)
                
    def add_failed_job(self, job_id):
        # XXX: We lose job options... should probably persist these in the journal.
        job = Job(job_id, None, None, JOB_FAILED, self, {})
        self.jobs[job_id] = job
    
    def create_job_for_task(self, task_descriptor, job_options, job_id=None):
        
        with self._lock:
        
            if job_id is None:
                job_id = self.allocate_job_id()
            task_id = 'root:%s' % (job_id, )
    
            task_descriptor['task_id'] = task_id
    
            # TODO: Here is where we will set up the job journal, etc.
            job_dir = self.make_job_directory(job_id)
            
            try:
                expected_outputs = task_descriptor['expected_outputs']
            except KeyError:
                expected_outputs = ['%s:job_output' % job_id]
                task_descriptor['expected_outputs'] = expected_outputs
                
            task = build_taskpool_task_from_descriptor(task_descriptor, None)
            job = Job(job_id, task, job_dir, JOB_CREATED, self, job_options)
            task.job = job
            
            self.add_job(job)
            
            ciel.log('Added job: %s' % job.id, 'JOB_POOL', logging.INFO)
    
            return job

    def make_job_directory(self, job_id):
        if self.journal_root is not None:
            job_dir = os.path.join(self.journal_root, job_id)
            os.mkdir(job_dir)
            return job_dir
        else:
            return None

    def maybe_start_new_job(self):
        with self._lock:
            if self.num_running_jobs < self.max_running_jobs:
                try:
                    next_job = self.run_queue.get_nowait()
                    self.num_running_jobs += 1
                    self._start_job(next_job)
                except Queue.Empty:
                    ciel.log('Not starting a new job because there are no more to start', 'JOB_POOL', logging.INFO)
            else:
                ciel.log('Not starting a new job because there is insufficient capacity', 'JOB_POOL', logging.INFO)
                
    def queue_job(self, job):
        self.run_queue.put(job)
        job.enqueued()
        self.maybe_start_new_job()
            
    def job_completed(self, job):
        self.num_running_jobs -= 1
        self.maybe_start_new_job()

    def _start_job(self, job):
        ciel.log('Starting job ID: %s' % job.id, 'JOB_POOL', logging.INFO)
        # This will also start the job by subscribing to the root task output and reducing.
        job.activated()

    def wait_for_completion(self, job, timeout=None):
        with job._lock:
            ciel.log('Waiting for completion of job %s' % job.id, 'JOB_POOL', logging.INFO)
            while job.state not in (JOB_COMPLETED, JOB_FAILED):
                if self.is_stopping:
                    break
                elif self.current_waiters > self.max_concurrent_waiters:
                    break
                else:
                    self.current_waiters += 1
                    job._condition.wait(timeout)
                    self.current_waiters -= 1
                    if timeout is not None:
                        return job.state in (JOB_COMPLETED, JOB_FAILED)
            if timeout is not None:
                return job.state in (JOB_COMPLETED, JOB_FAILED)
            if self.is_stopping:
                raise Exception("Server stopping")
            elif self.current_waiters >= self.max_concurrent_waiters:
                raise Exception("Too many concurrent waiters")
            else:
                return job

########NEW FILE########
__FILENAME__ = lazy_task_pool
# Copyright (c) 2010 Derek Murray <derek.murray@cl.cam.ac.uk>
#
# Permission to use, copy, modify, and distribute this software for any
# purpose with or without fee is hereby granted, provided that the above
# copyright notice and this permission notice appear in all copies.
#
# THE SOFTWARE IS PROVIDED "AS IS" AND THE AUTHOR DISCLAIMS ALL WARRANTIES
# WITH REGARD TO THIS SOFTWARE INCLUDING ALL IMPLIED WARRANTIES OF
# MERCHANTABILITY AND FITNESS. IN NO EVENT SHALL THE AUTHOR BE LIABLE FOR
# ANY SPECIAL, DIRECT, INDIRECT, OR CONSEQUENTIAL DAMAGES OR ANY DAMAGES
# WHATSOEVER RESULTING FROM LOSS OF USE, DATA OR PROFITS, WHETHER IN AN
# ACTION OF CONTRACT, NEGLIGENCE OR OTHER TORTIOUS ACTION, ARISING OUT OF
# OR IN CONNECTION WITH THE USE OR PERFORMANCE OF THIS SOFTWARE.

from Queue import Queue
from cherrypy.process import plugins
from ciel.runtime.master.job_pool import Job
from ciel.public.references import SW2_FutureReference, \
    SWErrorReference, combine_references, SW2_StreamReference
from ciel.runtime.task import TASK_CREATED, TASK_BLOCKING, TASK_RUNNABLE, \
    TASK_COMMITTED, build_taskpool_task_from_descriptor, TASK_QUEUED, TASK_FAILED, TASK_QUEUED_STREAMING
from threading import Lock
import collections
import logging
import uuid
import ciel

class LazyTaskPool(plugins.SimplePlugin):
    
    def __init__(self, bus, worker_pool):
    
        # Used for publishing schedule events.
        self.bus = bus

        # For signalling workers of task state changes
        self.worker_pool = worker_pool
    
        # Mapping from task ID to task object.
        self.tasks = {}
        
        # Mapping from expected output to producing task.
        self.task_for_output = {}
        
        # Mapping from expected output to consuming tasks.
        self.consumers_for_output = {}
        
        # Mapping from output name to concrete reference.
        self.ref_for_output = {}
        
        # Current set of job outputs: i.e. expected outputs that we want to
        # produce by lazy graph reduction.
        self.job_outputs = {}
        
        # A thread-safe queue of runnable tasks, which we use to pass tasks to
        # the LazyScheduler.
        self.task_queue = Queue()
        
        # At the moment, this is a coarse-grained lock, which is acquired when
        # a task is added or completed, or when references are externally
        # published.
        self._lock = Lock()
        
    def subscribe(self):
        self.bus.subscribe('task_failed', self.task_failed)
        
    def unsubscribe(self):
        self.bus.unsubscribe('task_failed', self.task_failed)
        
    def get_task_by_id(self, task_id):
        return self.tasks[task_id]
        
    def get_ref_by_id(self, ref_id):
        with self._lock:
            return self.ref_for_output[ref_id]
        
    def get_reference_info(self, id):
        with self._lock:
            ref = self.ref_for_output[id]
            try:
                consumers = self.consumers_for_output[id]
            except KeyError:
                consumers = []
            task = self.task_for_output[id]
            return {'ref': ref, 'consumers': list(consumers), 'task': task.as_descriptor()}
        
    def add_task(self, task, is_root_task=False, may_reduce=True):

        if task.task_id not in self.tasks:
            self.tasks[task.task_id] = task
            should_register = True
        else:
            ciel.log('Already seen task %s: do not register its outputs' % task.task_id, 'TASKPOOL', logging.INFO)
            should_register = False
        
        if is_root_task:
            self.job_outputs[task.expected_outputs[0]] = task.job
            ciel.log('Registering job (%s) interest in output (%s)' % (task.job.id, task.expected_outputs[0]), 'TASKPOOL', logging.INFO)
            self.register_job_interest_for_output(task.expected_outputs[0], task.job)
        
        task.job.add_task(task)
        
        # If any of the task outputs are being waited on, we should reduce this
        # task's graph. 
        with self._lock:
            if should_register:
                should_reduce = self.register_task_outputs(task) and may_reduce
                if should_reduce:
                    self.do_graph_reduction(root_tasks=[task])
                elif is_root_task:
                    self.do_graph_reduction(root_tasks=[task])
            elif is_root_task:
                ciel.log('Reducing graph from roots.', 'TASKPOOL', logging.INFO)
                self.do_root_graph_reduction()
            
    def task_completed(self, task, commit_bindings, should_publish=True):
        task.set_state(TASK_COMMITTED)
        
        # Need to notify all of the consumers, which may make other tasks
        # runnable.
        self.publish_refs(commit_bindings, task.job, task=task)
        if task.worker is not None and should_publish:
            self.bus.publish('worker_idle', task.worker)
        
    def get_task_queue(self):
        return self.task_queue
        
    def task_failed(self, task, payload):

        (reason, details, bindings) = payload

        ciel.log.error('Task failed because %s' % (reason, ), 'TASKPOOL', logging.WARNING)
        worker = None
        should_notify_outputs = False

        task.record_event(reason)


        self.publish_refs(bindings, task.job)

        with self._lock:
            if reason == 'WORKER_FAILED':
                # Try to reschedule task.
                task.current_attempt += 1
                # XXX: Remove this hard-coded constant. We limit the number of
                #      retries in case the task is *causing* the failures.
                if task.current_attempt > 3:
                    task.set_state(TASK_FAILED)
                    should_notify_outputs = True
                else:
                    ciel.log.error('Rescheduling task %s after worker failure' % task.task_id, 'TASKPOOL', logging.WARNING)
                    task.set_state(TASK_FAILED)
                    self.add_runnable_task(task)
                    self.bus.publish('schedule')
                    
            elif reason == 'MISSING_INPUT':
                # Problem fetching input, so we will have to re-execute it.
                worker = task.worker
                for binding in bindings.values():
                    ciel.log('Missing input: %s' % str(binding), 'TASKPOOL', logging.WARNING)
                self.handle_missing_input(task)
                
            elif reason == 'RUNTIME_EXCEPTION':
                # A hard error, so kill the entire job, citing the problem.
                worker = task.worker
                task.set_state(TASK_FAILED)
                should_notify_outputs = True

        # Doing this outside the lock because this leads via add_refs_to_id
        # --> self::reference_available, creating a circular wait. We noted the task as FAILED inside the lock,
        # which ought to be enough.
        if should_notify_outputs:
            for output in task.expected_outputs:
                self._publish_ref(output, SWErrorReference(output, reason, details), task.job)

        if worker is not None:
            self.bus.publish('worker_idle', worker)
    
    def handle_missing_input(self, task):
        task.set_state(TASK_FAILED)
                
        # Assume that all of the dependencies are unavailable.
        task.convert_dependencies_to_futures()
        
        # We will re-reduce the graph for this task, ignoring the network
        # locations for which getting the input failed.
        # N.B. We should already have published the necessary tombstone refs
        #      for the failed inputs.
        self.do_graph_reduction(root_tasks=[task])
    
    def publish_single_ref(self, global_id, ref, job, should_journal=True, task=None):
        with self._lock:
            self._publish_ref(global_id, ref, job, should_journal, task)
    
    def publish_refs(self, refs, job=None, should_journal=True, task=None):
        with self._lock:
            for global_id, ref in refs.items():
                self._publish_ref(global_id, ref, job, should_journal, task)
        
    def _publish_ref(self, global_id, ref, job=None, should_journal=True, task=None):
        
        if should_journal and job is not None:
            job.add_reference(global_id, ref)
        
        # Record the name-to-concrete-reference mapping for this ref's name.
        try:
            combined_ref = combine_references(self.ref_for_output[global_id], ref)
            if not combined_ref:
                return
            if not combined_ref.is_consumable():
                del self.ref_for_output[global_id]
                return
            self.ref_for_output[global_id] = combined_ref
        except KeyError:
            if ref.is_consumable():
                self.ref_for_output[global_id] = ref
            else:
                return

        current_ref = self.ref_for_output[global_id]

        if task is not None:
            self.task_for_output[global_id] = task

        # Notify any consumers that the ref is now available.
        # Contrary to how this was in earlier versions, tasks must unsubscribe themselves.
        # I always unsubscribe Jobs for simplicity, and because Jobs never need more than one callback.
        try:
            consumers = self.consumers_for_output[global_id]
            iter_consumers = consumers.copy()
            # Avoid problems with deletion from set during iteration
            for consumer in iter_consumers:
                if isinstance(consumer, Job) and consumer.job_pool is not None:
                    consumer.job_pool.job_completed(consumer, current_ref)
                    self.unregister_job_interest_for_output(current_ref.id, consumer)
                else:
                    self.notify_task_of_reference(consumer, global_id, current_ref)
        except KeyError:
            pass

    def notify_task_of_reference(self, task, id, ref):
        if ref.is_consumable():
            was_queued_streaming = task.is_queued_streaming()
            was_blocked = task.is_blocked()
            task.notify_reference_changed(id, ref, self)
            if was_blocked and not task.is_blocked():
                self.add_runnable_task(task)
            elif was_queued_streaming and not task.is_queued_streaming():
                # Submit this to the scheduler again
                self.add_runnable_task(task)

    def register_job_interest_for_output(self, ref_id, job):
        try:
            subscribers = self.consumers_for_output[ref_id]
        except:
            subscribers = set()
            self.consumers_for_output[ref_id] = subscribers
        subscribers.add(job)

    def unregister_job_interest_for_output(self, ref_id, job):
        try:
            subscribers = self.consumers_for_output[ref_id]
            subscribers.remove(job)
            if len(subscribers) == 0:
                del self.consumers_for_output[ref_id]
        except:
            ciel.log.error("Job %s failed to unsubscribe from ref %s" % (job, ref_id), "TASKPOOL", logging.WARNING)

    def subscribe_task_to_ref(self, task, ref):
        try:
            subscribers = self.consumers_for_output[ref.id]
        except:
            subscribers = set()
            self.consumers_for_output[ref.id] = subscribers
        subscribers.add(task)

    def unsubscribe_task_from_ref(self, task, ref):
        try:
            subscribers = self.consumers_for_output[ref.id]
            subscribers.remove(task)
            if len(subscribers) == 0:
                del self.consumers_for_output[ref.id]
        except:
            ciel.log.error("Task %s failed to unsubscribe from ref %s" % (task, ref.id), "TASKPOOL", logging.WARNING)
            
    def register_task_interest_for_ref(self, task, ref):
        if isinstance(ref, SW2_FutureReference):
            # First, see if we already have a concrete reference for this
            # output.
            try:
                conc_ref = self.ref_for_output[ref.id]
                return conc_ref
            except KeyError:
                pass
            
            # Otherwise, subscribe to the production of the named output.
            self.subscribe_task_to_ref(task, ref)
            return None
        
        else:
            # We have an opaque reference, which can be accessed immediately.
            return ref
        
    def register_task_outputs(self, task):
        # If any tasks have previously registered an interest in any of this
        # task's outputs, we need to reduce the given task.
        should_reduce = False
        for output in task.expected_outputs:
            self.task_for_output[output] = task
            if self.output_has_consumers(output):
                should_reduce = True
        return should_reduce
    
    def output_has_consumers(self, output):
        try:
            subscribers = self.consumers_for_output[output]
            return len(subscribers) > 0
        except KeyError:
            return False
    
    def add_runnable_task(self, task):
        if len(task.unfinished_input_streams) == 0:
            task.set_state(TASK_QUEUED)
        else:
            task.set_state(TASK_QUEUED_STREAMING)
        self.task_queue.put(task)
    
    def do_root_graph_reduction(self):
        self.do_graph_reduction(object_ids=self.job_outputs.keys())
    
    def do_graph_reduction(self, object_ids=[], root_tasks=[]):
        
        should_schedule = False
        newly_active_task_queue = collections.deque()
        
        # Initially, start with the root set of tasks, based on the desired
        # object IDs.
        for object_id in object_ids:
            try:
                if self.ref_for_output[object_id].is_consumable():
                    continue
            except KeyError:
                pass
            task = self.task_for_output[object_id]
            if task.state == TASK_CREATED:
                # Task has not yet been scheduled, so add it to the queue.
                task.set_state(TASK_BLOCKING)
                newly_active_task_queue.append(task)
            
        for task in root_tasks:
            newly_active_task_queue.append(task)
                
        # Do breadth-first search through the task graph to identify other 
        # tasks to make active. We use task.state == TASK_BLOCKING as a marker
        # to prevent visiting a task more than once.
        while len(newly_active_task_queue) > 0:
            
            task = newly_active_task_queue.popleft()
            
            # Identify the other tasks that need to run to make this task
            # runnable.
            task_will_block = False
            for local_id, ref in task.dependencies.items():
                conc_ref = self.register_task_interest_for_ref(task, 
                                                               ref)
                if conc_ref is not None and conc_ref.is_consumable():
                    task.inputs[local_id] = conc_ref
                    if isinstance(conc_ref, SW2_StreamReference):
                        task.unfinished_input_streams.add(ref.id)
                        self.subscribe_task_to_ref(task, conc_ref)
                else:
                    # The reference is a future that has not yet been produced,
                    # so block the task.
                    task_will_block = True
                    task.block_on(ref.id, local_id)
                    
                    # We may need to recursively check the inputs on the
                    # producing task for this reference.
                    try:
                        producing_task = self.task_for_output[ref.id]
                    except KeyError:
                        ciel.log.error('Task %s cannot access missing input %s and will block until this is produced' % (task.task_id, ref.id), 'TASKPOOL', logging.WARNING)
                        continue
                    
                    # The producing task is inactive, so recursively visit it.                    
                    if producing_task.state in (TASK_CREATED, TASK_COMMITTED):
                        producing_task.set_state(TASK_BLOCKING)
                        newly_active_task_queue.append(producing_task)
            
            # If all inputs are available, we can now run this task. Otherwise,
            # it will run when its inputs are published.
            if not task_will_block:
                task.set_state(TASK_RUNNABLE)
                should_schedule = True
                self.add_runnable_task(task)
                
        if should_schedule:
            self.bus.publish('schedule')
    
class LazyTaskPoolAdapter:
    """
    We use this adapter class to convert from the view's idea of a task pool to
    the new LazyTaskPool.
    """
    
    def __init__(self, lazy_task_pool, task_failure_investigator):
        self.lazy_task_pool = lazy_task_pool
        self.task_failure_investigator = task_failure_investigator
        
        # XXX: This exposes the task pool to the view.
        self.tasks = lazy_task_pool.tasks
     
    def add_task(self, task_descriptor, parent_task=None, job=None, may_reduce=True):
        try:
            task_id = task_descriptor['task_id']
        except:
            task_id = self.generate_task_id()
            task_descriptor['task_id'] = task_id
        
        task = build_taskpool_task_from_descriptor(task_descriptor, parent_task)
        task.job = job
        
        self.lazy_task_pool.add_task(task, parent_task is None, may_reduce)
        
        #add_event = self.new_event(task)
        #add_event["task_descriptor"] = task.as_descriptor(long=True)
        #add_event["action"] = "CREATED"
    
        #self.events.append(add_event)

        return task
    
    def get_reference_info(self, id):
        return self.lazy_task_pool.get_reference_info(id)
    
    def get_ref_by_id(self, id):
        return self.lazy_task_pool.get_ref_by_id(id)
    
    def generate_task_id(self):
        return str(uuid.uuid1())
    
    def get_task_by_id(self, id):
        return self.lazy_task_pool.get_task_by_id(id)
    
    def unsubscribe_task_from_ref(self, task, ref):
        return self.lazy_task_pool.unsubscribe_task_from_ref(task, ref)

    def publish_refs(self, task, refs):
        self.lazy_task_pool.publish_refs(refs, task.job, True)
    
    def spawn_child_tasks(self, parent_task, spawned_task_descriptors, may_reduce=True):

        if parent_task.is_replay_task():
            return
            
        for child in spawned_task_descriptors:
            try:
                spawned_task_id = child['task_id']
            except KeyError:
                raise
            
            task = self.add_task(child, parent_task, parent_task.job, may_reduce)
            parent_task.children.append(task)
            
            if task.continues_task is not None:
                parent_task.continuation = spawned_task_id

    def report_tasks(self, report):
        
        for (parent_id, success, payload) in report:
            parent_task = self.get_task_by_id(parent_id)
            if success:
                (spawned, published) = payload
                self.spawn_child_tasks(parent_task, spawned, may_reduce=False)
                self.commit_task(parent_id, {"bindings": dict([(ref.id, ref) for ref in published])}, should_publish=False)
            else:
                # Only one failed task per-report, at the moment.
                self.investigate_task_failure(parent_task, payload)
                # I hope this frees up workers and so forth?
                return
                
        toplevel_task = self.get_task_by_id(report[0][0])
        self.lazy_task_pool.do_graph_reduction(toplevel_task.expected_outputs)
        self.lazy_task_pool.worker_pool.worker_idle(toplevel_task.worker)

    def investigate_task_failure(self, task, payload):
        self.task_failure_investigator.investigate_task_failure(task, payload)

    def commit_task(self, task_id, commit_payload, should_publish=True):
        
        commit_bindings = commit_payload['bindings']
        task = self.lazy_task_pool.get_task_by_id(task_id)
        
        self.lazy_task_pool.task_completed(task, commit_bindings, should_publish)
        
        # Saved continuation URI, if necessary.
        try:
            commit_continuation_uri = commit_payload['saved_continuation_uri']
            task.saved_continuation_uri = commit_continuation_uri
        except KeyError:
            pass

########NEW FILE########
__FILENAME__ = master_view
# Copyright (c) 2010 Derek Murray <derek.murray@cl.cam.ac.uk>
#
# Permission to use, copy, modify, and distribute this software for any
# purpose with or without fee is hereby granted, provided that the above
# copyright notice and this permission notice appear in all copies.
#
# THE SOFTWARE IS PROVIDED "AS IS" AND THE AUTHOR DISCLAIMS ALL WARRANTIES
# WITH REGARD TO THIS SOFTWARE INCLUDING ALL IMPLIED WARRANTIES OF
# MERCHANTABILITY AND FITNESS. IN NO EVENT SHALL THE AUTHOR BE LIABLE FOR
# ANY SPECIAL, DIRECT, INDIRECT, OR CONSEQUENTIAL DAMAGES OR ANY DAMAGES
# WHATSOEVER RESULTING FROM LOSS OF USE, DATA OR PROFITS, WHETHER IN AN
# ACTION OF CONTRACT, NEGLIGENCE OR OTHER TORTIOUS ACTION, ARISING OUT OF
# OR IN CONNECTION WITH THE USE OR PERFORMANCE OF THIS SOFTWARE.
from __future__ import with_statement
from cherrypy import HTTPError
from ciel.public.references import json_decode_object_hook,\
    SWReferenceJSONEncoder
import sys
import simplejson
import cherrypy
from ciel.runtime.worker.worker_view import DataRoot, StopwatchRoot
from ciel.runtime.master.cluster_view import WebBrowserRoot
import ciel
import logging
import socket
from ciel.runtime.task_graph import TaskGraphUpdate

class MasterRoot:
    
    def __init__(self, worker_pool, block_store, job_pool, backup_sender, monitor):
        self.control = ControlRoot(worker_pool, block_store, job_pool, backup_sender, monitor)
        self.data = self.control.data

class ControlRoot:

    def __init__(self, worker_pool, block_store, job_pool, backup_sender, monitor):
        self.worker = WorkersRoot(worker_pool, backup_sender, monitor)
        self.job = JobRoot(job_pool, backup_sender, monitor)
        self.task = MasterTaskRoot(job_pool, worker_pool, backup_sender)
        self.data = DataRoot(block_store, backup_sender)
        self.gethostname = HostnameRoot()
        self.shutdown = ShutdownRoot(worker_pool)
        self.browse = WebBrowserRoot(job_pool)
        self.backup = BackupMasterRoot(backup_sender)
        self.ref = RefRoot(job_pool)
        self.stopwatch = StopwatchRoot()

    @cherrypy.expose
    def index(self):
        return "Hello from the master!"    

class HostnameRoot:

    @cherrypy.expose
    def index(self):
        (name, _, _) = socket.gethostbyaddr(cherrypy.request.remote.ip)
        return simplejson.dumps(name)

class ShutdownRoot:
    
    def __init__(self, worker_pool):
        self.worker_pool = worker_pool
    
    @cherrypy.expose
    def index(self):
        self.worker_pool.shutdown()
        sys.exit(-1)

class WorkersRoot:
    
    def __init__(self, worker_pool, backup_sender, monitor=None):
        self.worker_pool = worker_pool
        self.backup_sender = backup_sender
        self.monitor = monitor
    
    @cherrypy.expose
    def index(self):
        if cherrypy.request.method == 'POST':
            request_body = cherrypy.request.body.read()
            worker_descriptor = simplejson.loads(request_body)
            if self.monitor is not None and not self.monitor.is_primary:
                self.monitor.add_worker(worker_descriptor['netloc'])
                self.backup_sender.add_worker(request_body)
            else:
                worker_id = self.worker_pool.create_worker(worker_descriptor)
                self.backup_sender.add_worker(request_body)
                return simplejson.dumps(str(worker_id))
        elif cherrypy.request.method == 'GET':
            workers = [x.as_descriptor() for x in self.worker_pool.get_all_workers()]
            return simplejson.dumps(workers, indent=4)
        else:
            raise HTTPError(405)

    @cherrypy.expose
    def versioned(self):
        if cherrypy.request.method == 'GET':
            (version, workers) = self.worker_pool.get_all_workers_with_version()
            return simplejson.dumps({"version": version, "workers": workers})
        else:
            raise HTTPError(405)

    @cherrypy.expose
    def await_event_count(self, version=0):
        if cherrypy.request.method == 'POST':
            try:
                return simplejson.dumps({ "current_version" : repr(self.worker_pool.await_version_after(int(version))) })
            except Exception as t:
                return simplejson.dumps({ "error": repr(t) })
                
        else:
            raise HTTPError(405)
        
    @cherrypy.expose
    def random(self):
        return simplejson.dumps('http://%s/' % (self.worker_pool.get_random_worker().netloc, ))
        
    @cherrypy.expose
    def default(self, worker_id, action=None):
        try:
            worker = self.worker_pool.get_worker_by_id(worker_id)
        except KeyError:
            if worker_id == 'reset':
                self.worker_pool.reset()
                return
            else:
                raise HTTPError(404)
        if cherrypy.request.method == 'POST':
            if action == 'ping':
                self.worker_pool.worker_ping(worker)
            elif action == 'stopping':
                self.worker_pool.worker_failed(worker)
            else:
                raise HTTPError(404)
        else:
            if action is None:
                return simplejson.dumps(worker.as_descriptor())

class JobRoot:
    
    def __init__(self, job_pool, backup_sender, monitor=None):
        self.job_pool = job_pool
        self.backup_sender = backup_sender
        self.monitor = monitor
        
    @cherrypy.expose
    def index(self):
        if cherrypy.request.method == 'POST':
            # 1. Read task descriptor from request.
            request_body = cherrypy.request.body.read()
            payload = simplejson.loads(request_body, 
                                               object_hook=json_decode_object_hook)

            task_descriptor = payload['root_task']
            try:
                job_options = payload['job_options']
            except KeyError:
                job_options = {}

            # 2. Add to job pool (synchronously).
            job = self.job_pool.create_job_for_task(task_descriptor, job_options)
            
            # 2bis. Send to backup master.
            self.backup_sender.add_job(job.id, request_body)
            
            # 2a. Start job. Possibly do this as deferred work.
            self.job_pool.queue_job(job)
                        
            # 3. Return descriptor for newly-created job.
            return simplejson.dumps(job.as_descriptor())
            
        elif cherrypy.request.method == 'GET':
            # Return a list of all jobs in the system.
            return simplejson.dumps(self.job_pool.get_all_job_ids())
        else:
            raise HTTPError(405)

    @cherrypy.expose
    def default(self, id, attribute=None):
        if cherrypy.request.method == 'POST' and attribute is None:
            ciel.log('Creating job for ID: %s' % id, 'JOB_POOL', logging.INFO)
            # Need to support this for backup masters, so that the job ID is
            # consistent.
            
            # 1. Read task descriptor from request.
            request_body = cherrypy.request.body.read()
            task_descriptor = simplejson.loads(request_body, 
                                               object_hook=json_decode_object_hook)

            # 2. Add to job pool (synchronously).
            job = self.job_pool.create_job_for_task(task_descriptor, job_id=id)

            # 2bis. Send to backup master.
            self.backup_sender.add_job(job.id, request_body)
            
            if self.monitor is not None and self.monitor.is_primary:
                # 2a. Start job. Possibly do this as deferred work.
                self.job_pool.queue_job(job)
            else:
                ciel.log('Registering job, but not starting it: %s' % job.id, 'JOB_POOL', logging.INFO)
                #self.job_pool.task_pool.add_task(job.root_task, False)
            
            # 3. Return descriptor for newly-created job.
            
            ciel.log('Done handling job POST', 'JOB_POOL', logging.INFO)
            return simplejson.dumps(job.as_descriptor())            
        
        try:
            job = self.job_pool.get_job_by_id(id)
        except KeyError:
            raise HTTPError(404)
        
        if attribute is None:
            # Return the job descriptor as JSON.
            return simplejson.dumps(job.as_descriptor(), cls=SWReferenceJSONEncoder, indent=4)
        elif attribute == 'completion':
            # Block until the job is completed.
            try:
                timeout = simplejson.loads(cherrypy.request.body.read(), object_hook=json_decode_object_hook)['timeout']
            except:
                timeout = None
            done = self.job_pool.wait_for_completion(job, timeout)            
            if timeout is None:
                return simplejson.dumps(job.as_descriptor(), cls=SWReferenceJSONEncoder) 
            else:
                return simplejson.dumps(done)
        elif attribute == 'resume':
            self.job_pool.queue_job(job)
        elif attribute == 'poke':
            job.schedule()
        else:
            # Invalid attribute.
            raise HTTPError(404)
        
class MasterTaskRoot:
    
    def __init__(self, job_pool, worker_pool, backup_sender):
        self.job_pool = job_pool
        self.worker_pool = worker_pool
        self.backup_sender = backup_sender
       
    @cherrypy.expose 
    def default(self, job_id, task_id, action=None):
        
        if action == 'report':
            ciel.stopwatch.multi(starts=["master_task"], laps=["end_to_end"])
        
        try:
            job = self.job_pool.get_job_by_id(job_id)
        except KeyError:
            ciel.log('No such job: %s' % job_id, 'MASTER', logging.ERROR)
            raise HTTPError(404)

        try:
            task = job.task_graph.get_task(task_id)
        except KeyError:
            ciel.log('No such task: %s in job: %s' % (task_id, job_id), 'MASTER', logging.ERROR)
            raise HTTPError(404)

        if cherrypy.request.method == 'GET':
            if action is None:
                return simplejson.dumps(task.as_descriptor(long=True), cls=SWReferenceJSONEncoder)
            else:
                ciel.log('Invalid operation: cannot GET with an action', 'MASTER', logging.ERROR)
                raise HTTPError(405)
        elif cherrypy.request.method != 'POST':
            ciel.log('Invalid operation: only POST is supported for task operations', 'MASTER', logging.ERROR)
            raise HTTPError(405)

        # Action-handling starts here.

        if action == 'report':
            # Multi-spawn-and-commit
            report_payload = simplejson.loads(cherrypy.request.body.read(), object_hook=json_decode_object_hook)
            worker = self.worker_pool.get_worker_by_id(report_payload['worker'])
            report = report_payload['report']
            job.report_tasks(report, task, worker)
            return

        elif action == 'failed':
            failure_payload = simplejson.loads(cherrypy.request.body.read(), object_hook=json_decode_object_hook)
            job.investigate_task_failure(task, failure_payload)
            return simplejson.dumps(True)
        
        elif action == 'publish':
            request_body = cherrypy.request.body.read()
            refs = simplejson.loads(request_body, object_hook=json_decode_object_hook)
            
            tx = TaskGraphUpdate()
            for ref in refs:
                tx.publish(ref, task)
            tx.commit(job.task_graph)
            job.schedule()

            self.backup_sender.publish_refs(task_id, refs)
            return
            
        elif action == 'log':
            # Message body is a JSON list containing UNIX timestamp in seconds and a message string.
            request_body = cherrypy.request.body.read()
            timestamp, message = simplejson.loads(request_body, object_hook=json_decode_object_hook)
            ciel.log("%s %f %s" % (task_id, timestamp, message), 'TASK_LOG', logging.INFO)
            
        elif action == 'abort':
            # FIXME (maybe): There is currently no abort method on Task.
            task.abort(task_id)
            return
        
        elif action is None:
            ciel.log('Invalid operation: only GET is supported for tasks', 'MASTER', logging.ERROR)
            raise HTTPError(404)
        else:
            ciel.log('Unknown action (%s) on task (%s)' % (action, task_id), 'MASTER', logging.ERROR)
            raise HTTPError(404)
            
            
class BackupMasterRoot:
    
    def __init__(self, backup_sender):
        self.backup_sender = backup_sender
        
    @cherrypy.expose
    def index(self):
        if cherrypy.request.method == 'POST':
            # Register the  a new global ID, and add the POSTed URLs if any.
            standby_url = simplejson.loads(cherrypy.request.body.read(), object_hook=json_decode_object_hook)
            self.backup_sender.register_standby_url(standby_url)
            return 'Registered a hot standby'
        
class RefRoot:
    
    def __init__(self, job_pool):
        self.job_pool = job_pool

    @cherrypy.expose         
    def default(self, job_id, ref_id):
        
        try:
            job = self.job_pool.get_job_by_id(job_id)
        except KeyError:
            raise HTTPError(404)
        
        try:
            ref = job.task_graph.get_reference_info(ref_id).ref
        except KeyError:
            raise HTTPError(404)

        return simplejson.dumps(ref, cls=SWReferenceJSONEncoder)

########NEW FILE########
__FILENAME__ = recovery
# Copyright (c) 2010 Derek Murray <derek.murray@cl.cam.ac.uk>
#
# Permission to use, copy, modify, and distribute this software for any
# purpose with or without fee is hereby granted, provided that the above
# copyright notice and this permission notice appear in all copies.
#
# THE SOFTWARE IS PROVIDED "AS IS" AND THE AUTHOR DISCLAIMS ALL WARRANTIES
# WITH REGARD TO THIS SOFTWARE INCLUDING ALL IMPLIED WARRANTIES OF
# MERCHANTABILITY AND FITNESS. IN NO EVENT SHALL THE AUTHOR BE LIABLE FOR
# ANY SPECIAL, DIRECT, INDIRECT, OR CONSEQUENTIAL DAMAGES OR ANY DAMAGES
# WHATSOEVER RESULTING FROM LOSS OF USE, DATA OR PROFITS, WHETHER IN AN
# ACTION OF CONTRACT, NEGLIGENCE OR OTHER TORTIOUS ACTION, ARISING OUT OF
# OR IN CONNECTION WITH THE USE OR PERFORMANCE OF THIS SOFTWARE.

from ciel.public.references import SW2_ConcreteReference, SW2_TombstoneReference
from cherrypy.process import plugins
import urllib2
from ciel.runtime.block_store import BLOCK_LIST_RECORD_STRUCT
from ciel.public.references import json_decode_object_hook
import logging
import os
import simplejson
from ciel.runtime.master.job_pool import RECORD_HEADER_STRUCT,\
    Job, JOB_ACTIVE, JOB_RECOVERED
from ciel.runtime.task import build_taskpool_task_from_descriptor
import ciel
import httplib2

class TaskFailureInvestigator:
    
    def __init__(self, worker_pool, deferred_worker):
        self.worker_pool = worker_pool
        self.deferred_worker = deferred_worker
        
    def investigate_task_failure(self, task_id, failure_payload):
        self.deferred_worker.do_deferred(lambda: self._investigate_task_failure(task_id, failure_payload))
        
    def _investigate_task_failure(self, task, failure_payload):
        (reason, detail, bindings) = failure_payload
        ciel.log('Investigating failure of task %s' % task.task_id, 'TASKFAIL', logging.WARN)
        ciel.log('Task failed because %s' % reason, 'TASKPOOL', logging.WARN)

        revised_bindings = {}
        failed_netlocs = set()

        # First, go through the bindings to determine which references are really missing.
        for id, tombstone in bindings.items():
            if isinstance(tombstone, SW2_TombstoneReference):
                ciel.log('Investigating reference: %s' % str(tombstone), 'TASKFAIL', logging.WARN)
                failed_netlocs_for_ref = set()
                for netloc in tombstone.netlocs:
                    h = httplib2.Http()
                    try:
                        response, _ = h.request('http://%s/data/%s' % (netloc, id), 'HEAD')
                        if response['status'] != '200':
                            ciel.log('Could not obtain object from %s: status %s' % (netloc, response['status']), 'TASKFAIL', logging.WARN)
                            failed_netlocs_for_ref.add(netloc)
                        else:
                            ciel.log('Object still available from %s' % netloc, 'TASKFAIL', logging.INFO)
                    except:
                        ciel.log('Could not contact store at %s' % netloc, 'TASKFAIL', logging.WARN)
                        failed_netlocs.add(netloc)
                        failed_netlocs_for_ref.add(netloc)
                if len(failed_netlocs_for_ref) > 0:
                    revised_bindings[id] = SW2_TombstoneReference(id, failed_netlocs_for_ref)
            else:
                # Could potentially mention a ConcreteReference or something similar in the failure bindings.
                revised_bindings[id] = tombstone
                
        # Now, having collected a set of actual failures, deem those workers to have failed.
        for netloc in failed_netlocs:
            worker = self.worker_pool.get_worker_at_netloc(netloc)
            if worker is not None:
                self.worker_pool.worker_failed(worker)
                
        with task.job._lock:
            # Finally, propagate the failure to the task pool, so that we can re-run the failed task.
            task.job.task_graph.task_failed(task, revised_bindings, reason, detail)

class RecoveryManager(plugins.SimplePlugin):
    
    def __init__(self, bus, job_pool, block_store, deferred_worker):
        plugins.SimplePlugin.__init__(self, bus)
        self.job_pool = job_pool
        self.block_store = block_store
        self.deferred_worker = deferred_worker
        
    def subscribe(self):
        # In order to present a consistent view to clients, we must do these
        # before starting the webserver.
        self.bus.subscribe('start', self.recover_local_blocks, 5)
        self.bus.subscribe('start', self.recover_job_descriptors, 10)
        
        
        self.bus.subscribe('fetch_block_list', self.fetch_block_list_defer)
    
    def unsubscribe(self):
        self.bus.unsubscribe('start', self.recover_local_blocks)
        self.bus.unsubscribe('start', self.recover_job_descriptors)
        self.bus.unsubscribe('fetch_block_list', self.fetch_block_list_defer)

    def recover_local_blocks(self):
        if not self.block_store.is_empty():
            for block_name, block_size in self.block_store.block_list_generator():
                conc_ref = SW2_ConcreteReference(block_name, block_size)
                conc_ref.add_location_hint(self.block_store.netloc)
                
                # FIXME: What should we do with recovered blocks?
                
                #ciel.log.error('Recovering block %s (size=%d)' % (block_name, block_size), 'RECOVERY', logging.INFO)
                #self.task_pool.publish_single_ref(block_name, conc_ref, None, False)                

    def recover_job_descriptors(self):
        root = self.job_pool.journal_root
        if root is None:
            return
        
        for job_id in os.listdir(root):

            try:
                job_dir = os.path.join(root, job_id)
                result_path = os.path.join(job_dir, 'result')
                if os.path.exists(result_path):
                    with open(result_path, 'r') as result_file:
                        result = simplejson.load(result_file, object_hook=json_decode_object_hook)
                else:
                    result = None
                    
                journal_path = os.path.join(job_dir, 'task_journal')
                journal_file = open(journal_path, 'rb')
                record_type, root_task_descriptor_length = RECORD_HEADER_STRUCT.unpack(journal_file.read(RECORD_HEADER_STRUCT.size))
                root_task_descriptor_string = journal_file.read(root_task_descriptor_length)
                assert record_type == 'T'
                assert len(root_task_descriptor_string) == root_task_descriptor_length
                root_task_descriptor = simplejson.loads(root_task_descriptor_string, object_hook=json_decode_object_hook)
                root_task = build_taskpool_task_from_descriptor(root_task_descriptor, None)
                
                # FIXME: Get the job pool to create this job, because it has access to the scheduler queue and task failure investigator.
                # FIXME: Store job options somewhere for recovered job.
                job = Job(job_id, root_task, job_dir, JOB_RECOVERED, self.job_pool, {}, journal=False)
                
                root_task.job = job
                if result is not None:
                    with job._lock:
                        job.completed(result)
                self.job_pool.add_job(job)
                # Adding the job to the job pool should add the root task.
                #self.task_pool.add_task(root_task)
                
                if result is None:
                    self.load_other_tasks_defer(job, journal_file)
                    ciel.log.error('Recovered job %s' % job_id, 'RECOVERY', logging.INFO, False)
                    ciel.log.error('Recovered task %s for job %s' % (root_task.task_id, job_id), 'RECOVERY', logging.INFO, False)
                else:
                    journal_file.close()
                    ciel.log.error('Found information about job %s' % job_id, 'RECOVERY', logging.INFO, False)
                
                
            except:
                # We have lost critical data for the job, so we must fail it.
                ciel.log.error('Error recovering job %s' % job_id, 'RECOVERY', logging.ERROR, True)
                self.job_pool.add_failed_job(job_id)

    def load_other_tasks_defer(self, job, journal_file):
        self.deferred_worker.do_deferred(lambda: self.load_other_tasks_for_job(job, journal_file))

    def load_other_tasks_for_job(self, job, journal_file):
        '''
        Process a the task journal for a recovered job.
        '''
        try:
            while True:
                record_header = journal_file.read(RECORD_HEADER_STRUCT.size)
                if len(record_header) != RECORD_HEADER_STRUCT.size:
                    ciel.log.error('Journal entry truncated for job %s' % job.id, 'RECOVERY', logging.WARNING, False)
                    # XXX: Need to truncate the journal file.
                    break
                record_type, record_length = RECORD_HEADER_STRUCT.unpack(record_header)
                record_string = journal_file.read(record_length)
                if len(record_string) != record_length:
                    ciel.log.error('Journal entry truncated for job %s' % job.id, 'RECOVERY', logging.WARNING, False)
                    # XXX: Need to truncate the journal file.
                    break
                rec = simplejson.loads(record_string, object_hook=json_decode_object_hook)
                if record_type == 'R':
                    job.task_graph.publish(rec['ref'])
                elif record_type == 'T':
                    task_id = rec['task_id']
                    parent_task = job.task_graph.get_task(rec['parent'])
                    task = build_taskpool_task_from_descriptor(rec, parent_task)
                    task.job = job
                    task.parent.children.append(task)
    
                    ciel.log.error('Recovered task %s for job %s' % (task_id, job.id), 'RECOVERY', logging.INFO, False)
                    job.task_graph.spawn(task)
                else:
                    ciel.log.error('Got invalid record type in job %s' % job.id, 'RECOVERY', logging.WARNING, False)
                
        except:
            ciel.log.error('Error recovering task_journal for job %s' % job.id, 'RECOVERY', logging.WARNING, True)

        finally:
            journal_file.close()
            job.restart_journalling()
            if job.state == JOB_ACTIVE:
                ciel.log.error('Restarting recovered job %s' % job.id, 'RECOVERY', logging.INFO)
            # We no longer immediately start a job when recovering it.
            #self.job_pool.restart_job(job)

    def fetch_block_list_defer(self, worker):
        ciel.log('Fetching block list is currently disabled', 'RECOVERY', logging.WARNING)
        #self.deferred_worker.do_deferred(lambda: self.fetch_block_names_from_worker(worker))
        
    def fetch_block_names_from_worker(self, worker):
        '''
        Loop through the block list file from the given worker, and publish the
        references found there.
        '''
        
        block_file = urllib2.urlopen('http://%s/control/data/' % worker.netloc)

        while True:
            record = block_file.read(BLOCK_LIST_RECORD_STRUCT.size)
            if not record:
                break
            block_name, block_size = BLOCK_LIST_RECORD_STRUCT.unpack(record)
            conc_ref = SW2_ConcreteReference(block_name, block_size)
            conc_ref.add_location_hint(worker.netloc)
            
            #ciel.log.error('Recovering block %s (size=%d)' % (block_name, block_size), 'RECOVERY', logging.INFO)
            # FIXME: What should we do with recovered blocks?
            self.task_pool.publish_single_ref(block_name, conc_ref, None, False)

        
        block_file.close()
        
        # Publishing recovered blocks may cause tasks to become QUEUED, so we
        # must run the scheduler.
        self.bus.publish('schedule')
        

########NEW FILE########
__FILENAME__ = scheduling_policy
# Copyright (c) 2011 Derek Murray <Derek.Murray@cl.cam.ac.uk>
#
# Permission to use, copy, modify, and distribute this software for any
# purpose with or without fee is hereby granted, provided that the above
# copyright notice and this permission notice appear in all copies.
#
# THE SOFTWARE IS PROVIDED "AS IS" AND THE AUTHOR DISCLAIMS ALL WARRANTIES
# WITH REGARD TO THIS SOFTWARE INCLUDING ALL IMPLIED WARRANTIES OF
# MERCHANTABILITY AND FITNESS. IN NO EVENT SHALL THE AUTHOR BE LIABLE FOR
# ANY SPECIAL, DIRECT, INDIRECT, OR CONSEQUENTIAL DAMAGES OR ANY DAMAGES
# WHATSOEVER RESULTING FROM LOSS OF USE, DATA OR PROFITS, WHETHER IN AN
# ACTION OF CONTRACT, NEGLIGENCE OR OTHER TORTIOUS ACTION, ARISING OUT OF
# OR IN CONNECTION WITH THE USE OR PERFORMANCE OF THIS SOFTWARE.
from ciel.public.references import SW2_SweetheartReference, SW2_ConcreteReference,\
    SW2_StreamReference
import random


class SchedulingPolicy:
    
    def __init__(self):
        pass
    
    def select_workers_for_task(self, task, worker_pool):
        """Returns a list of workers on which to run the given task."""
        raise Exception("Subclass must implement this")
    
class RandomSchedulingPolicy(SchedulingPolicy):
    
    def __init__(self):
        pass
    
    def select_workers_for_task(self, task, worker_pool):
        return [worker_pool.get_random_worker()]
    
class WeightedRandomSchedulingPolicy(SchedulingPolicy):
    
    def __init__(self):
        pass
    
    def select_workers_for_task(self, task, worker_pool):
        return [worker_pool.get_random_worker_with_capacity_weight(task.scheduling_class)]
    
class TwoRandomChoiceSchedulingPolicy(SchedulingPolicy):
    
    def __init__(self):
        pass
    
    def select_workers_for_task(self, task, worker_pool):
        worker1 = worker_pool.get_random_worker()
        worker2 = worker_pool.get_random_worker()
        cost1 = task.job.guess_task_cost_on_worker(task, worker1)
        cost2 = task.job.guess_task_cost_on_worker(task, worker2)
        if cost1 < cost2:
            return [worker1]
        else:
            return [worker2]

class LocalitySchedulingPolicy(SchedulingPolicy):
    
    def __init__(self, sweetheart_factor=1000, equally_local_margin=0.9, stream_source_bytes_equivalent=10000000, min_saving_threshold=1048576):
        self.sweetheart_factor = sweetheart_factor
        self.equally_local_margin = equally_local_margin
        self.stream_source_bytes_equivalent = stream_source_bytes_equivalent 
        self.min_saving_threshold = min_saving_threshold
    
    def select_workers_for_task(self, task, worker_pool):
        netlocs = {}
        for input in task.inputs.values():
            
            if isinstance(input, SW2_SweetheartReference) and input.size_hint is not None:
                # Sweetheart references get a boosted benefit for the sweetheart, and unboosted benefit for all other netlocs.
                try:
                    current_saving_for_netloc = netlocs[input.sweetheart_netloc]
                except KeyError:
                    current_saving_for_netloc = 0
                netlocs[input.sweetheart_netloc] = current_saving_for_netloc + self.sweetheart_factor * input.size_hint
                
                for netloc in input.location_hints:
                    try:
                        current_saving_for_netloc = netlocs[netloc]
                    except KeyError:
                        current_saving_for_netloc = 0
                    netlocs[netloc] = current_saving_for_netloc + input.size_hint
                    
            elif isinstance(input, SW2_ConcreteReference) and input.size_hint is not None:
                # Concrete references get an unboosted benefit for all netlocs.
                for netloc in input.location_hints:
                    try:
                        current_saving_for_netloc = netlocs[netloc]
                    except KeyError:
                        current_saving_for_netloc = 0
                    netlocs[netloc] = current_saving_for_netloc + input.size_hint
                    
            elif isinstance(input, SW2_StreamReference):
                # Stream references get a heuristically-chosen benefit for stream sources.
                for netloc in input.location_hints:
                    try:
                        current_saving_for_netloc = netlocs[netloc]
                    except KeyError:
                        current_saving_for_netloc = 0
                    netlocs[netloc] = current_saving_for_netloc + self.stream_source_bytes_equivalent
                    
        ranked_netlocs = [(saving, netloc) for (netloc, saving) in netlocs.items()]
        filtered_ranked_netlocs = filter(lambda (saving, netloc) : worker_pool.get_worker_at_netloc(netloc) is not None and saving > self.min_saving_threshold, ranked_netlocs)
        filtered_ranked_netlocs.sort(reverse=True)
        
        if len(filtered_ranked_netlocs) == 0:
            # If we have no preference for any worker, use the power of two random choices. [Azar et al. STOC 1994]
            worker1 = worker_pool.get_random_worker_with_capacity_weight(task.scheduling_class)
            return [worker1]
        elif len(filtered_ranked_netlocs) == 1:
            return [worker_pool.get_worker_at_netloc(filtered_ranked_netlocs[0][1])]
        
        else:
            threshold = filtered_ranked_netlocs[0][0] * self.equally_local_margin
            return [worker_pool.get_worker_at_netloc(netloc) for saved, netloc in filtered_ranked_netlocs if saved > threshold]
                
SCHEDULING_POLICIES = {'random' : RandomSchedulingPolicy,
                       'tworandom' : TwoRandomChoiceSchedulingPolicy,
                       'locality' : LocalitySchedulingPolicy}

def get_scheduling_policy(policy_name, *args, **kwargs):
    if policy_name is None:
        return LocalitySchedulingPolicy()
    else:
        return SCHEDULING_POLICIES[policy_name](*args, **kwargs)
########NEW FILE########
__FILENAME__ = worker_pool
# Copyright (c) 2010 Derek Murray <derek.murray@cl.cam.ac.uk>
#
# Permission to use, copy, modify, and distribute this software for any
# purpose with or without fee is hereby granted, provided that the above
# copyright notice and this permission notice appear in all copies.
#
# THE SOFTWARE IS PROVIDED "AS IS" AND THE AUTHOR DISCLAIMS ALL WARRANTIES
# WITH REGARD TO THIS SOFTWARE INCLUDING ALL IMPLIED WARRANTIES OF
# MERCHANTABILITY AND FITNESS. IN NO EVENT SHALL THE AUTHOR BE LIABLE FOR
# ANY SPECIAL, DIRECT, INDIRECT, OR CONSEQUENTIAL DAMAGES OR ANY DAMAGES
# WHATSOEVER RESULTING FROM LOSS OF USE, DATA OR PROFITS, WHETHER IN AN
# ACTION OF CONTRACT, NEGLIGENCE OR OTHER TORTIOUS ACTION, ARISING OUT OF
# OR IN CONNECTION WITH THE USE OR PERFORMANCE OF THIS SOFTWARE.
from __future__ import with_statement
from Queue import Queue
from ciel.public.references import SWReferenceJSONEncoder
from ciel.runtime.pycurl_rpc import post_string_noreturn, get_string
import ciel
import datetime
import logging
import random
import simplejson
import threading
import uuid
from urlparse import urlparse

class FeatureQueues:
    def __init__(self):
        self.queues = {}
        self.streaming_queues = {}
        
    def get_queue_for_feature(self, feature):
        try:
            return self.queues[feature]
        except KeyError:
            queue = Queue()
            self.queues[feature] = queue
            return queue

    def get_streaming_queue_for_feature(self, feature):
        try:
            return self.streaming_queues[feature]
        except KeyError:
            queue = Queue()
            self.streaming_queues[feature] = queue
            return queue

class Worker:
    
    def __init__(self, worker_id, worker_descriptor, feature_queues, worker_pool):
        self.id = worker_id
        self.netloc = worker_descriptor['netloc']
        self.features = worker_descriptor['features']
        self.scheduling_classes = worker_descriptor['scheduling_classes']
        self.last_ping = datetime.datetime.now()
        self.failed = False
        self.worker_pool = worker_pool

    def idle(self):
        pass

    def get_effective_scheduling_class(self, scheduling_class):
        if scheduling_class in self.scheduling_classes:
            return scheduling_class
        else:
            return '*'

    def get_effective_scheduling_class_capacity(self, scheduling_class):
        try:
            return self.scheduling_classes[scheduling_class]
        except KeyError:
            return self.scheduling_classes['*']

    def __repr__(self):
        return 'Worker(%s)' % self.id

    def as_descriptor(self):
        return {'worker_id': self.id,
                'netloc': self.netloc,
                'features': self.features,
                'last_ping': self.last_ping.ctime(),
                'failed':  self.failed}
        
class WorkerPool:
    
    def __init__(self, bus, deferred_worker, job_pool):
        self.bus = bus
        self.deferred_worker = deferred_worker
        self.job_pool = job_pool
        self.idle_worker_queue = Queue()
        self.workers = {}
        self.netlocs = {}
        self.idle_set = set()
        self._lock = threading.RLock()
        self.feature_queues = FeatureQueues()
        self.event_count = 0
        self.event_condvar = threading.Condition(self._lock)
        self.max_concurrent_waiters = 5
        self.current_waiters = 0
        self.is_stopping = False
        self.scheduling_class_capacities = {'*' : []}
        self.scheduling_class_total_capacities = {'*' : 0}

    def subscribe(self):
        self.bus.subscribe('start', self.start, 75)
        self.bus.subscribe('stop', self.server_stopping, 10) 
        
    def unsubscribe(self):
        self.bus.unsubscribe('start', self.start, 75)
        self.bus.unsubscribe('stop', self.server_stopping) 

    def start(self):
        self.deferred_worker.do_deferred_after(30.0, self.reap_dead_workers)
        
    def reset(self):
        self.idle_worker_queue = Queue()
        self.workers = {}
        self.netlocs = {}
        self.idle_set = set()
        self.feature_queues = FeatureQueues()
        
    def allocate_worker_id(self):
        return str(uuid.uuid1())
        
    def create_worker(self, worker_descriptor):
        with self._lock:
            id = self.allocate_worker_id()
            worker = Worker(id, worker_descriptor, self.feature_queues, self)
            ciel.log.error('Worker registered: %s (%s)' % (worker.id, worker.netloc), 'WORKER_POOL', logging.WARNING, True)
            self.workers[id] = worker
            try:
                previous_worker_at_netloc = self.netlocs[worker.netloc]
                ciel.log.error('Worker at netloc %s has reappeared' % worker.netloc, 'WORKER_POOL', logging.WARNING)
                self.worker_failed(previous_worker_at_netloc)
            except KeyError:
                pass
            self.netlocs[worker.netloc] = worker
            self.idle_set.add(id)
            self.event_count += 1
            self.event_condvar.notify_all()
            
            for scheduling_class, capacity in worker.scheduling_classes.items():
                try:
                    capacities = self.scheduling_class_capacities[scheduling_class]
                    current_total = self.scheduling_class_total_capacities[scheduling_class]
                except:
                    capacities = []
                    self.scheduling_class_capacities[scheduling_class] = capacities
                    current_total = 0
                capacities.append((worker, capacity))
                self.scheduling_class_total_capacities[scheduling_class] = current_total + capacity

            self.job_pool.notify_worker_added(worker)
            return id

    def notify_job_about_current_workers(self, job):
        """Nasty function included to avoid the race between job creation and worker creation."""
        with self._lock:
            for worker in self.workers.values():
                job.notify_worker_added(worker)

# XXX: This is currently disabled because we don't have a big central list of references.
#        try:
#            has_blocks = worker_descriptor['has_blocks']
#        except:
#            has_blocks = False
#            
#        if has_blocks:
#            ciel.log.error('%s has blocks, so will fetch' % str(worker), 'WORKER_POOL', logging.INFO)
#            self.bus.publish('fetch_block_list', worker)
            
        self.bus.publish('schedule')
        return id
    
    def shutdown(self):
        for worker in self.workers.values():
            try:
                get_string('http://%s/control/kill/' % worker.netloc)
            except:
                pass
        
    def get_worker_by_id(self, id):
        with self._lock:
            return self.workers[id]
        
    def get_all_workers(self):
        with self._lock:
            return self.workers.values()
    
    def execute_task_on_worker(self, worker, task):
        try:
            ciel.stopwatch.stop("master_task")
            
            message = simplejson.dumps(task.as_descriptor(), cls=SWReferenceJSONEncoder)
            post_string_noreturn("http://%s/control/task/" % (worker.netloc), message, result_callback=self.worker_post_result_callback)
        except:
            self.worker_failed(worker)

    def abort_task_on_worker(self, task, worker):
        try:
            ciel.log("Aborting task %s on worker %s" % (task.task_id, worker), "WORKER_POOL", logging.WARNING)
            post_string_noreturn('http://%s/control/abort/%s/%s' % (worker.netloc, task.job.id, task.task_id), "", result_callback=self.worker_post_result_callback)
        except:
            self.worker_failed(worker)
    
    def worker_failed(self, worker):
        ciel.log.error('Worker failed: %s (%s)' % (worker.id, worker.netloc), 'WORKER_POOL', logging.WARNING, True)
        with self._lock:
            worker.failed = True
            del self.netlocs[worker.netloc]
            del self.workers[worker.id]

            for scheduling_class, capacity in worker.scheduling_classes.items():
                self.scheduling_class_capacities[scheduling_class].remove((worker, capacity))
                self.scheduling_class_total_capacities[scheduling_class] -= capacity
                if self.scheduling_class_total_capacities[scheduling_class] == 0:
                    del self.scheduling_class_capacities[scheduling_class]
                    del self.scheduling_class_total_capacities[scheduling_class]

        if self.job_pool is not None:
            self.job_pool.notify_worker_failed(worker)

    def worker_ping(self, worker):
        with self._lock:
            self.event_count += 1
            self.event_condvar.notify_all()
        worker.last_ping = datetime.datetime.now()

    def server_stopping(self):
        with self._lock:
            self.is_stopping = True
            self.event_condvar.notify_all()

    def investigate_worker_failure(self, worker):
        ciel.log.error('Investigating possible failure of worker %s (%s)' % (worker.id, worker.netloc), 'WORKER_POOL', logging.WARNING)
        try:
            content = get_string('http://%s/control/master/' % worker.netloc)
            worker_fetch = simplejson.loads(content)
            assert worker_fetch['id'] == worker.id
        except:
            self.worker_failed(worker)

    def get_random_worker(self):
        with self._lock:
            return random.choice(self.workers.values())
        
    def get_random_worker_with_capacity_weight(self, scheduling_class):
        
        with self._lock:
            try:
                candidates = self.scheduling_class_capacities[scheduling_class]
                total_capacity = self.scheduling_class_total_capacities[scheduling_class]
            except KeyError:
                scheduling_class = '*'
                candidates = self.scheduling_class_capacities['*']
                total_capacity = self.scheduling_class_total_capacities['*']
        
            if total_capacity == 0:
                return None

            selected_slot = random.randrange(total_capacity)
            curr_slot = 0
            i = 0
            
            for worker, capacity in candidates:
                curr_slot += capacity
                if curr_slot > selected_slot:
                    return worker
            
            ciel.log('Ran out of workers in capacity-weighted selection class=%s selected=%d total=%d' % (scheduling_class, selected_slot, total_capacity), 'WORKER_POOL', logging.ERROR)
            
    def get_worker_at_netloc(self, netloc):
        try:
            return self.netlocs[netloc]
        except KeyError:
            return None

    def reap_dead_workers(self):
        if not self.is_stopping:
            for worker in self.workers.values():
                if worker.failed:
                    continue
                if (worker.last_ping + datetime.timedelta(seconds=10)) < datetime.datetime.now():
                    failed_worker = worker
                    self.deferred_worker.do_deferred(lambda: self.investigate_worker_failure(failed_worker))
                    
            self.deferred_worker.do_deferred_after(10.0, self.reap_dead_workers)

    def worker_post_result_callback(self, success, url):
        # An asynchronous post_string_noreturn has completed against 'url'. Called from the cURL thread.
        if not success:
            parsed = urlparse(url)
            worker = self.get_worker_at_netloc(parsed.netloc)
            if worker is not None:
                ciel.log("Aysnchronous post against %s failed: investigating" % url, "WORKER_POOL", logging.ERROR)
                # Safe to call from here: this bottoms out in a deferred-work call quickly.
                self.worker_failed(worker)
            else:
                ciel.log("Asynchronous post against %s failed, but we have no matching worker. Ignored." % url, "WORKER_POOL", logging.WARNING)


########NEW FILE########
__FILENAME__ = object_cache

import pickle
import simplejson
from cStringIO import StringIO
from ciel.public.references import SWReferenceJSONEncoder, json_decode_object_hook,\
    SWDataValue, encode_datavalue
from ciel.runtime.producer import make_local_output, ref_from_string
from ciel.runtime.fetcher import retrieve_strings_for_refs

def decode_handle(file):
    return file
def encode_noop(obj, file):
    return file.write(obj)
def decode_noop(file):
    return file.read()    
def encode_json(obj, file):
    return simplejson.dump(obj, file, cls=SWReferenceJSONEncoder)
def decode_json(file):
    return simplejson.load(file, object_hook=json_decode_object_hook)
def encode_pickle(obj, file):
    return pickle.dump(obj, file)
def decode_pickle(file):
    return pickle.load(file)

encoders = {'noop': encode_noop, 'json': encode_json, 'pickle': encode_pickle}
decoders = {'noop': decode_noop, 'json': decode_json, 'pickle': decode_pickle, 'handle': decode_handle}

object_cache = {}

def cache_object(object, encoder, id):
    object_cache[(id, encoder)] = object        

def ref_from_object(object, encoder, id):
    """Encodes an object, returning either a DataValue or ConcreteReference as appropriate"""
    cache_object(object, encoder, id)
    buffer = StringIO()
    encoders[encoder](object, buffer)
    ret = ref_from_string(buffer.getvalue(), id)
    buffer.close()
    return ret

def retrieve_objects_for_refs(ref_and_decoders, task_record):

    solutions = dict()
    unsolved_refs = []
    for (ref, decoder) in ref_and_decoders:
        try:
            solutions[ref.id] = object_cache[(ref.id, decoder)]
        except:
            unsolved_refs.append(ref)

    strings = retrieve_strings_for_refs(unsolved_refs, task_record)
    str_of_ref = dict([(ref.id, string) for (string, ref) in zip(strings, unsolved_refs)])
            
    for (ref, decoder) in ref_and_decoders:
        if ref.id not in solutions:
            decoded = decoders[decoder](StringIO(str_of_ref[ref.id]))
            object_cache[(ref.id, decoder)] = decoded
            solutions[ref.id] = decoded
            
    return [solutions[ref.id] for (ref, decoder) in ref_and_decoders]

def retrieve_object_for_ref(ref, decoder, task_record):
    
    return retrieve_objects_for_refs([(ref, decoder)], task_record)[0]

    


########NEW FILE########
__FILENAME__ = plugins
# Copyright (c) 2010 Derek Murray <derek.murray@cl.cam.ac.uk>
#
# Permission to use, copy, modify, and distribute this software for any
# purpose with or without fee is hereby granted, provided that the above
# copyright notice and this permission notice appear in all copies.
#
# THE SOFTWARE IS PROVIDED "AS IS" AND THE AUTHOR DISCLAIMS ALL WARRANTIES
# WITH REGARD TO THIS SOFTWARE INCLUDING ALL IMPLIED WARRANTIES OF
# MERCHANTABILITY AND FITNESS. IN NO EVENT SHALL THE AUTHOR BE LIABLE FOR
# ANY SPECIAL, DIRECT, INDIRECT, OR CONSEQUENTIAL DAMAGES OR ANY DAMAGES
# WHATSOEVER RESULTING FROM LOSS OF USE, DATA OR PROFITS, WHETHER IN AN
# ACTION OF CONTRACT, NEGLIGENCE OR OTHER TORTIOUS ACTION, ARISING OUT OF
# OR IN CONNECTION WITH THE USE OR PERFORMANCE OF THIS SOFTWARE.
from __future__ import with_statement
import ciel
from Queue import Queue
import logging
import threading

class ThreadTerminator:
    pass
THREAD_TERMINATOR = ThreadTerminator()

class AsynchronousExecutePlugin:
    
    def __init__(self, bus, num_threads, subscribe_event=None, publish_success_event=None, publish_fail_event=None):
        self.bus = bus
        self.threads = []
        
        self.queue = Queue()
        
        self.num_threads = num_threads
        self.subscribe_event = subscribe_event
        self.publish_success_event = publish_success_event
        self.publish_fail_event = publish_fail_event
        
    def subscribe(self):
        self.bus.subscribe('start', self.start)
        self.bus.subscribe('stop', self.stop)
        if self.subscribe_event is not None:
            self.bus.subscribe(self.subscribe_event, self.receive_input)
            
    def unsubscribe(self):
        self.bus.unsubscribe('start', self.start)
        self.bus.unsubscribe('stop', self.stop)
        if self.subscribe_event is not None:
            self.bus.unsubscribe(self.subscribe_event, self.receive_input)
            
    def start(self):
        self.is_running = True
        for _ in range(self.num_threads):
            t = threading.Thread(target=self.thread_main, args=())
            self.threads.append(t)
            t.start()
                
    def stop(self):
        self.is_running = False
        for _ in range(self.num_threads):
            self.queue.put(THREAD_TERMINATOR)
        for thread in self.threads:
            thread.join()
        self.threads = []
        
    def receive_input(self, input=None):
        self.queue.put(input)
        
    def thread_main(self):
        
        while True:
            if not self.is_running:
                break
            input = self.queue.get()
            if input is THREAD_TERMINATOR:
                break

            try:
                result = self.handle_input(input)
                if self.publish_success_event is not None:
                    self.bus.publish(self.publish_success_event, input, result)
            except Exception, ex:
                if self.publish_fail_event is not None:
                    self.bus.publish(self.publish_fail_event, input, ex)
                else:
                    ciel.log.error('Error handling input in %s' % (self.__class__, ), 'PLUGIN', logging.ERROR, True)

    def handle_input(self, input):
        """Override this method to specify the behaviour on processing a single input."""
        pass

########NEW FILE########
__FILENAME__ = producer
# Copyright (c) 2010--11 Chris Smowton <Chris.Smowton@cl.cam.ac.uk>
#
# Permission to use, copy, modify, and distribute this software for any
# purpose with or without fee is hereby granted, provided that the above
# copyright notice and this permission notice appear in all copies.
#
# THE SOFTWARE IS PROVIDED "AS IS" AND THE AUTHOR DISCLAIMS ALL WARRANTIES
# WITH REGARD TO THIS SOFTWARE INCLUDING ALL IMPLIED WARRANTIES OF
# MERCHANTABILITY AND FITNESS. IN NO EVENT SHALL THE AUTHOR BE LIABLE FOR
# ANY SPECIAL, DIRECT, INDIRECT, OR CONSEQUENTIAL DAMAGES OR ANY DAMAGES
# WHATSOEVER RESULTING FROM LOSS OF USE, DATA OR PROFITS, WHETHER IN AN
# ACTION OF CONTRACT, NEGLIGENCE OR OTHER TORTIOUS ACTION, ARISING OUT OF
# OR IN CONNECTION WITH THE USE OR PERFORMANCE OF THIS SOFTWARE.

import ciel
import logging

import subprocess
import tempfile
import threading
import os
from datetime import datetime, timedelta

import ciel.runtime.tcp_server
import ciel.runtime.file_watcher as fwt
from ciel.runtime.block_store import get_own_netloc, producer_filename,\
    filename_for_ref
from ciel.public.references import SWDataValue, encode_datavalue, SW2_ConcreteReference, \
    SW2_StreamReference, SW2_CompletedReference, SW2_SocketStreamReference,\
    decode_datavalue_string
import shutil

# Maintains a set of block IDs that are currently being written.
# (i.e. They are in the pre-publish/streamable state, and have not been
#       committed to the block store.)
# They map to the executor which is producing them.
streaming_producers = dict()

class FileOutputContext:

    # can_use_fd: If we're presented with an FD which a consumer wishes us to write to, the producer can do that directly.
    #             If it can't, we'll provide an intermediary FIFO for him.
    # may_pipe: Should wait for a direct connection, either via local pipe or direct remote socket
    def __init__(self, refid, subscribe_callback, can_use_fd=False, may_pipe=False):
        self.refid = refid
        self.subscribe_callback = subscribe_callback
        self.file_watch = None
        self.subscriptions = []
        self.current_size = None
        self.closed = False
        self.succeeded = None
        self.fifo_name = None
        self.may_pipe = may_pipe
        self.can_use_fd = can_use_fd
        self.direct_write_filename = None
        self.direct_write_fd = None
        self.started = False
        self.pipe_deadline = datetime.now() + timedelta(seconds=5)
        self.cat_proc = None
        self.lock = threading.Lock()
        self.cond = threading.Condition(self.lock)

    def get_filename_or_fd(self):
        if self.may_pipe:
            with self.lock:
                if self.direct_write_filename is None and self.direct_write_fd is None:
                    now = datetime.now()
                    if now < self.pipe_deadline:
                        wait_time = self.pipe_deadline - now
                        wait_secs = float(wait_time.seconds) + (float(wait_time.microseconds) / 10**6)
                        ciel.log("Producer for %s: waiting for a direct consumer" % self.refid, "BLOCKPIPE", logging.DEBUG)
                        self.cond.wait(wait_secs)
                if self.direct_write_filename is not None:
                    ciel.log("Producer for %s: writing direct to filename %s" % (self.refid, self.direct_write_filename), "BLOCKPIPE", logging.DEBUG)
                    self.started = True
                    return (self.direct_write_filename, False)
                elif self.direct_write_fd is not None:
                    ciel.log("Producer for %s: writing direct to consumer-supplied FD" % self.refid, "BLOCKPIPE", logging.DEBUG)
                    self.started = True
                    return (self.direct_write_fd, True)
                elif self.started:
                    ciel.log("Producer for %s: kicked by a regular-file subscription; using conventional stream-file" % self.refid, "BLOCKPIPE", logging.DEBUG)
                else:
                    self.started = True
                    ciel.log("Producer for %s: timed out waiting for a consumer; writing to local block store" % self.refid, "BLOCKPIPE", logging.DEBUG)
        return (producer_filename(self.refid), False)

    def get_stream_ref(self):
        if ciel.runtime.tcp_server.tcp_server_active():
            return SW2_SocketStreamReference(self.refid, get_own_netloc(), ciel.runtime.tcp_server.aux_listen_port)
        else:
            return SW2_StreamReference(self.refid, location_hints=[get_own_netloc()])

    def rollback(self):
        if not self.closed:
            ciel.log("Rollback output %s" % id, 'BLOCKSTORE', logging.WARNING)
            del streaming_producers[self.refid]
            with self.lock:
                self.closed = True
                self.succeeded = False
            if self.fifo_name is not None:
                try:
                    # Dismiss anyone waiting on this pipe
                    fd = os.open(self.fifo_name, os.O_NONBLOCK | os.O_WRONLY)
                    os.close(fd)
                except:
                    pass
                try:
                    os.remove(self.fifo_name)
                except:
                    pass
            if self.file_watch is not None:
                self.file_watch.cancel()
            if self.cat_proc is not None:
                try:
                    self.cat_proc.kill()
                except:
                    pass
            for subscriber in self.subscriptions:
                subscriber.result(False)

    def close(self):
        if not self.closed:
            del streaming_producers[self.refid]
            with self.lock:
                self.closed = True
                self.succeeded = True
            if self.direct_write_filename is None and self.direct_write_fd is None:
                ciel.runtime.block_store.commit_producer(self.refid)
            if self.file_watch is not None:
                self.file_watch.cancel()
            self.current_size = os.stat(producer_filename(self.refid)).st_size
            for subscriber in self.subscriptions:
                subscriber.progress(self.current_size)
                subscriber.result(True)

    def get_completed_ref(self):
        if not self.closed:
            raise Exception("FileOutputContext for ref %s must be closed before it is realised as a concrete reference" % self.refid)
        if self.direct_write_filename is not None or self.direct_write_fd is not None:
            return SW2_CompletedReference(self.refid)
        completed_file = producer_filename(self.refid)
        if self.current_size < 1024:
            with open(completed_file, "r") as fp:
                return SWDataValue(self.refid, encode_datavalue(fp.read()))
        else:
            return SW2_ConcreteReference(self.refid, size_hint=self.current_size, location_hints=[get_own_netloc()])

    def update_chunk_size(self):
        self.subscriptions.sort(key=lambda x: x.chunk_size)
        self.file_watch.set_chunk_size(self.subscriptions[0].chunk_size)

    def try_direct_attach_consumer(self, consumer, consumer_filename=None, consumer_fd=None):
        if not self.may_pipe:
            return False
        else:
            if self.started:
                ciel.log("Producer for %s: consumer tried to attach, but we've already started writing a file" % self.refid, "BLOCKPIPE", logging.DEBUG)
                ret = False
            elif consumer_filename is not None:
                ciel.log("Producer for %s: writing to consumer-supplied filename %s" % (self.refid, consumer_filename), "BLOCKPIPE", logging.DEBUG)
                self.direct_write_filename = consumer_filename
                ret = True
            elif consumer_fd is not None and self.can_use_fd:
                ciel.log("Producer for %s: writing to consumer-supplied FD %s" % (self.refid, consumer_fd), "BLOCKPIPE", logging.DEBUG)
                self.direct_write_fd = consumer_fd
                ret = True
            else:
                self.fifo_name = tempfile.mktemp(prefix="ciel-producer-fifo-")
                os.mkfifo(self.fifo_name)
                self.direct_write_filename = self.fifo_name
                if consumer_fd is not None:
                    ciel.log("Producer for %s: consumer gave an FD to attach, but we can't use FDs directly. Starting 'cat'" % self.refid, "BLOCKPIPE", logging.DEBUG)
                    self.cat_proc = subprocess.Popen(["cat < %s" % self.fifo_name], shell=True, stdout=consumer_fd, close_fds=True)
                    os.close(consumer_fd)
                ret = True
            self.cond.notify_all()
            return ret

    def get_fifo_filename(self):
        return self.fifo_name

    def follow_file(self, new_subscriber):
        should_start_watch = False
        if self.current_size is not None:
            new_subscriber.progress(self.current_size)
        if self.file_watch is None:
            ciel.log("Starting watch on output %s" % self.refid, "BLOCKSTORE", logging.DEBUG)
            self.file_watch = self.subscribe_callback(self)
            should_start_watch = True
        self.update_chunk_size()
        if should_start_watch:
            self.file_watch.start()       

    def subscribe(self, new_subscriber, try_direct=False, consumer_filename=None, consumer_fd=None):

        with self.lock:
            if self.closed:
                if self.current_size is not None:
                    new_subscriber.progress(self.current_size)
                new_subscriber.result(self.succeeded)
                return False
            self.subscriptions.append(new_subscriber)
            if self.may_pipe:
                if self.direct_write_filename is not None or self.direct_write_fd is not None:
                    raise Exception("Tried to subscribe to output %s, but it's already being consumed directly! Bug? Or duplicate consumer task?" % self.refid)
                if try_direct and self.try_direct_attach_consumer(new_subscriber, consumer_filename, consumer_fd):
                    ret = True
                else:
                    self.follow_file(new_subscriber)
                    ret = False
            else:
                self.follow_file(new_subscriber)
                ret = False
            self.started = True
            self.cond.notify_all()
            return ret

    def unsubscribe(self, subscriber):
        try:
            self.subscriptions.remove(subscriber)
        except ValueError:
            ciel.log("Couldn't unsubscribe %s from output %s: not a subscriber" % (subscriber, self.refid), "BLOCKSTORE", logging.ERROR)
        if len(self.subscriptions) == 0 and self.file_watch is not None:
            ciel.log("No more subscribers for %s; cancelling watch" % self.refid, "BLOCKSTORE", logging.DEBUG)
            self.file_watch.cancel()
            self.file_watch = None
        else:
            self.update_chunk_size()

    def chunk_size_changed(self, subscriber):
        self.update_chunk_size()

    def size_update(self, new_size):
        self.current_size = new_size
        for subscriber in self.subscriptions:
            subscriber.progress(new_size)

    def __enter__(self):
        return self

    def __exit__(self, exnt, exnv, exntb):
        if not self.closed:
            if exnt is None:
                self.close()
            else:
                ciel.log("FileOutputContext %s destroyed due to exception %s: rolling back" % (self.refid, repr(exnv)), "BLOCKSTORE", logging.WARNING)
                self.rollback()
        return False

def make_local_output(id, subscribe_callback=None, may_pipe=False, can_use_fd=False):
    '''
    Creates a file-in-progress in the block store directory.
    '''
    if subscribe_callback is None:
        subscribe_callback = fwt.create_watch
    ciel.log.error('Creating file for output %s' % id, 'BLOCKSTORE', logging.DEBUG)
    new_ctx = FileOutputContext(id, subscribe_callback, may_pipe=may_pipe, can_use_fd=can_use_fd)
    dot_filename = producer_filename(id)
    open(dot_filename, 'wb').close()
    streaming_producers[id] = new_ctx
    return new_ctx

def get_producer_for_id(id):
    try:
        return streaming_producers[id]
    except KeyError:
        return None

def ref_from_string(string, id):
    if len(string) < 1024:
        return SWDataValue(id, value=encode_datavalue(string))
    else:
        output_ctx = make_local_output(id)
        filename, _ = output_ctx.get_filename_or_fd()
        with open(filename, "w") as fp:
            fp.write(string)
        output_ctx.close()
        return output_ctx.get_completed_ref()
        
def write_fixed_ref_string(string, fixed_ref):
    output_ctx = make_local_output(fixed_ref.id)
    with open(filename_for_ref(fixed_ref), "w") as fp:
        fp.write(string)
    output_ctx.close()

def ref_from_safe_string(string, id):
    if len(string) < 1024:
        return SWDataValue(id, value=string)
    else:
        return ref_from_string(decode_datavalue_string(string), id)

# Why not just rename to self.filename(id) and skip this nonsense? Because os.rename() can be non-atomic.
# When it renames between filesystems it does a full copy; therefore I copy/rename to a colocated dot-file,
# then complete the job by linking the proper name in output_ctx.close().
def ref_from_external_file(filename, id):
    output_ctx = make_local_output(id)
    with output_ctx:
        (new_filename, is_fd) = output_ctx.get_filename_or_fd()
        assert not is_fd
        shutil.move(filename, new_filename)
    return output_ctx.get_completed_ref()
########NEW FILE########
__FILENAME__ = producer_stat
# Copyright (c) 2010--11 Chris Smowton <Chris.Smowton@cl.cam.ac.uk>
#
# Permission to use, copy, modify, and distribute this software for any
# purpose with or without fee is hereby granted, provided that the above
# copyright notice and this permission notice appear in all copies.
#
# THE SOFTWARE IS PROVIDED "AS IS" AND THE AUTHOR DISCLAIMS ALL WARRANTIES
# WITH REGARD TO THIS SOFTWARE INCLUDING ALL IMPLIED WARRANTIES OF
# MERCHANTABILITY AND FITNESS. IN NO EVENT SHALL THE AUTHOR BE LIABLE FOR
# ANY SPECIAL, DIRECT, INDIRECT, OR CONSEQUENTIAL DAMAGES OR ANY DAMAGES
# WHATSOEVER RESULTING FROM LOSS OF USE, DATA OR PROFITS, WHETHER IN AN
# ACTION OF CONTRACT, NEGLIGENCE OR OTHER TORTIOUS ACTION, ARISING OUT OF
# OR IN CONNECTION WITH THE USE OR PERFORMANCE OF THIS SOFTWARE.

import ciel
import logging
import simplejson
import threading
import os

from ciel.runtime.pycurl_rpc import post_string_noreturn
from ciel.runtime.block_store import filename
from ciel.runtime.producer import get_producer_for_id

# Remote endpoints that are receiving adverts from our streaming producers.
# Indexed by (refid, otherend_netloc)
remote_stream_subscribers = dict()

module_lock = threading.Lock()

class RemoteOutputSubscriber:
        
    def __init__(self, file_output, netloc, chunk_size):
        self.file_output = file_output
        self.netloc = netloc
        self.chunk_size = chunk_size
        self.current_size = None
        self.last_notify = None

    def set_chunk_size(self, chunk_size):
        self.chunk_size = chunk_size
        if self.current_size is not None:
            self.post(simplejson.dumps({"bytes": self.current_size, "done": False}))
        self.file_output.chunk_size_changed(self)

    def unsubscribe(self):
        self.file_output.unsubscribe(self)

    def post(self, message):
        post_string_noreturn("http://%s/control/streamstat/%s/advert" % (self.netloc, self.file_output.refid), message)

    def progress(self, bytes):
        self.current_size = bytes
        if self.last_notify is None or self.current_size - self.last_notify > self.chunk_size:
            data = simplejson.dumps({"bytes": bytes, "done": False})
            self.post(data)
            self.last_notify = self.current_size

    def result(self, success):
        if success:
            self.post(simplejson.dumps({"bytes": self.current_size, "done": True}))
        else:
            self.post(simplejson.dumps({"failed": True}))

# Remote is subscribing to updates regarding an output. Be helpful and inform him of a completed file, too.
def subscribe_output(otherend_netloc, chunk_size, id):
    post = None
    with module_lock:
        try:
            producer = get_producer_for_id(id)
            if producer is not None:
                try:
                    remote_stream_subscribers[(id, otherend_netloc)].set_chunk_size(chunk_size)
                    ciel.log("Remote %s changed chunk size for %s to %d" % (otherend_netloc, id, chunk_size), "BLOCKSTORE", logging.DEBUG)
                except KeyError:
                    new_subscriber = RemoteOutputSubscriber(producer, otherend_netloc, chunk_size)
                    producer.subscribe(new_subscriber, try_direct=False)
                    ciel.log("Remote %s subscribed to output %s (chunk size %d)" % (otherend_netloc, id, chunk_size), "BLOCKSTORE", logging.DEBUG)
            else:
                try:
                    st = os.stat(filename(id))
                    post = simplejson.dumps({"bytes": st.st_size, "done": True})
                except OSError:
                    post = simplejson.dumps({"absent": True})
        except Exception as e:
            ciel.log("Subscription to %s failed with exception %s; reporting absent" % (id, e), "BLOCKSTORE", logging.WARNING)
            post = simplejson.dumps({"absent": True})
    if post is not None:
        post_string_noreturn("http://%s/control/streamstat/%s/advert" % (otherend_netloc, id), post)

def unsubscribe_output(otherend_netloc, id):
    with module_lock:
        try:
            remote_stream_subscribers[(id, otherend_netloc)].cancel()
            ciel.log("%s unsubscribed from %s" % (otherend_netloc, id), "BLOCKSTORE", logging.DEBUG)
        except KeyError:
            ciel.log("Ignored unsubscribe request for unknown block %s" % id, "BLOCKSTORE", logging.WARNING)

########NEW FILE########
__FILENAME__ = pycurl_data_fetch
# Copyright (c) 2010--11 Chris Smowton <Chris.Smowton@cl.cam.ac.uk>
#
# Permission to use, copy, modify, and distribute this software for any
# purpose with or without fee is hereby granted, provided that the above
# copyright notice and this permission notice appear in all copies.
#
# THE SOFTWARE IS PROVIDED "AS IS" AND THE AUTHOR DISCLAIMS ALL WARRANTIES
# WITH REGARD TO THIS SOFTWARE INCLUDING ALL IMPLIED WARRANTIES OF
# MERCHANTABILITY AND FITNESS. IN NO EVENT SHALL THE AUTHOR BE LIABLE FOR
# ANY SPECIAL, DIRECT, INDIRECT, OR CONSEQUENTIAL DAMAGES OR ANY DAMAGES
# WHATSOEVER RESULTING FROM LOSS OF USE, DATA OR PROFITS, WHETHER IN AN
# ACTION OF CONTRACT, NEGLIGENCE OR OTHER TORTIOUS ACTION, ARISING OUT OF
# OR IN CONNECTION WITH THE USE OR PERFORMANCE OF THIS SOFTWARE.

from ciel.runtime.pycurl_thread import pycURLContext, do_from_curl_thread
from ciel.runtime.block_store import get_fetch_urls_for_ref, create_fetch_file_for_ref, get_own_netloc
from ciel.public.references import SW2_ConcreteReference, SW2_FetchReference
import ciel.runtime.remote_stat as remote_stat

import pycurl
import urlparse
import ciel
import logging

# pycURLFetches currently in operation
active_http_transfers = dict()

class pycURLFetchContext(pycURLContext):

    def __init__(self, dest_fp, src_url, result_callback, progress_callback=None, start_byte=None, fetch_client=None):

        pycURLContext.__init__(self, src_url, result_callback)

        self.description = src_url
        self.progress_callback = None

        self.fetch_client = fetch_client

        self.curl_ctx.setopt(pycurl.WRITEDATA, dest_fp)
        if progress_callback is not None:
            self.curl_ctx.setopt(pycurl.NOPROGRESS, False)
            self.curl_ctx.setopt(pycurl.PROGRESSFUNCTION, self.progress)
            self.progress_callback = progress_callback
        if start_byte is not None and start_byte != 0:
            self.curl_ctx.setopt(pycurl.HTTPHEADER, ["Range: bytes=%d-" % start_byte])

    def success(self):
        bytes_downloaded = self.curl_ctx.getinfo(pycurl.SIZE_DOWNLOAD)
        self.progress_callback(bytes_downloaded)
        pycURLContext.success(self)
        if self.fetch_client.task_record is not None:
            self.fetch_client.task_record.add_completed_fetch(self.description, bytes_downloaded)

    def progress(self, toDownload, downloaded, toUpload, uploaded):
        self.progress_callback(downloaded)

class FileTransferContext:

    def __init__(self, ref, callbacks, fetch_client):
        self.ref = ref
        self.urls = get_fetch_urls_for_ref(self.ref)
        self.callbacks = callbacks
        self.failures = 0
        self.cancelled = False
        self.curl_fetch = None
        self.fetch_client = fetch_client

    def start_next_attempt(self):
        self.fp = open(self.callbacks.bs_ctx.filename, "w")
        ciel.log("Starting fetch attempt %d using %s" % (self.failures + 1, self.urls[self.failures]), "CURL_FETCH", logging.DEBUG)
        self.curl_fetch = pycURLFetchContext(self.fp, self.urls[self.failures], self.result, self.callbacks.progress, fetch_client=self.fetch_client)
        self.curl_fetch.start()

    def start(self):
        self.start_next_attempt()

    def result(self, success):
        self.fp.close()
        if success:
            self.callbacks.result(True)
        else:
            self.failures += 1
            if self.failures == len(self.urls):
                ciel.log.error('Fetch %s: no more URLs to try.' % self.ref.id, 'BLOCKSTORE', logging.WARNING)
                self.callbacks.result(False)
            else:
                ciel.log.error("Fetch %s failed; trying next URL" % (self.urls[self.failures - 1]))
                self.curl_fetch = None
                self.callbacks.reset()
                if not self.cancelled:
                    self.start_next_attempt()

    def set_chunk_size(self, new_chunk_size):
        # Don't care: we always request the whole file.
        pass

    def cancel(self):
        ciel.log("Fetch %s: cancelling" % self.ref.id, "CURL_FETCH", logging.DEBUG)
        self.cancelled = True
        if self.curl_fetch is not None:
            self.curl_fetch.cancel()
        self.fp.close()
        self.callbacks.result(False)

class StreamTransferContext:

    def __init__(self, ref, callbacks, fetch_client):
        self.url = get_fetch_urls_for_ref(ref)[0]
        parsed_url = urlparse.urlparse(self.url)
        self.worker_netloc = parsed_url.netloc
        self.ref = ref
        self.fetch_client = fetch_client
        open(callbacks.bs_ctx.filename, "w").close()
        self.callbacks = callbacks
        self.current_data_fetch = None
        self.previous_fetches_bytes_downloaded = 0
        self.remote_done = False
        self.remote_failed = False
        self.latest_advertisment = 0
        self.cancelled = False
        self.local_done = False
        self.current_chunk_size = None
        self.subscribed_to_remote_adverts = True
        
    def start_next_fetch(self):
        ciel.log("Stream-fetch %s: start fetch from byte %d" % (self.ref.id, self.previous_fetches_bytes_downloaded), "CURL_FETCH", logging.DEBUG)
        self.current_data_fetch = pycURLFetchContext(self.fp, self.url, self.result, self.progress, self.previous_fetches_bytes_downloaded, fetch_client=self.fetch_client)
        self.current_data_fetch.start()

    def start(self):
        self.fp = open(self.callbacks.bs_ctx.filename, "w")
        self.start_next_fetch()

    def progress(self, bytes_downloaded):
        self.fp.flush()
        self.callbacks.progress(self.previous_fetches_bytes_downloaded + bytes_downloaded)

    def consider_next_fetch(self):
        if self.remote_done or self.latest_advertisment - self.previous_fetches_bytes_downloaded > self.current_chunk_size:
            self.start_next_fetch()
        else:
            ciel.log("Stream-fetch %s: paused (remote has %d, I have %d)" % 
                     (self.ref.id, self.latest_advertisment, self.previous_fetches_bytes_downloaded), 
                     "CURL_FETCH", logging.DEBUG)
            self.current_data_fetch = None

    def check_complete(self):
        if self.remote_done and self.latest_advertisment == self.previous_fetches_bytes_downloaded:
            self.complete(True)
        else:
            self.consider_next_fetch()

    def result(self, success):
        # Current transfer finished.
        if self.remote_failed:
            ciel.log("Stream-fetch %s: transfer completed, but failure advertised in the meantime" % self.ref.id, "CURL_FETCH", logging.WARNING)
            self.complete(False)
            return
        if not success:
            ciel.log("Stream-fetch %s: transfer failed" % self.ref.id)
            self.complete(False)
        else:
            this_fetch_bytes = self.current_data_fetch.curl_ctx.getinfo(pycurl.SIZE_DOWNLOAD)
            ciel.log("Stream-fetch %s: transfer succeeded (got %d bytes)" % (self.ref.id, this_fetch_bytes),
                     "CURL_FETCH", logging.DEBUG)
            self.previous_fetches_bytes_downloaded += this_fetch_bytes
            self.check_complete()

    def complete(self, success):
        if not self.local_done:
            self.local_done = True
            ciel.log("Stream-fetch %s: complete" % self.ref.id, "CURL_FETCH", logging.DEBUG)
            self.unsubscribe_remote_output()
            self.fp.close() 
            self.callbacks.result(success)        

    # Sneaky knowledge here: this call comes from the cURL thread.
    def subscribe_result(self, success, _):
        if not success:
            ciel.log("Stream-fetch %s: failed to subscribe to remote adverts. Abandoning stream." 
                     % self.ref.id, "CURL_FETCH", logging.DEBUG)
            self.subscribed_to_remote_adverts = False
            self.remote_failed = True
            if self.current_data_fetch is None:
                self.complete(False)

    def unsubscribe_remote_output(self):
        if self.subscribed_to_remote_adverts:
            remote_stat.unsubscribe_remote_output(self.ref.id)
            self.subscribed_to_remote_adverts = False

    def subscribe_remote_output(self, chunk_size):
        ciel.log("Stream-fetch %s: change notification chunk size to %d" 
                 % (self.ref.id, chunk_size), "CURL_FETCH", logging.DEBUG)
        remote_stat.subscribe_remote_output(self.ref.id, self.worker_netloc, chunk_size, self)

    def set_chunk_size(self, new_chunk_size):
        if new_chunk_size != self.current_chunk_size:
            self.subscribe_remote_output(new_chunk_size)
        self.current_chunk_size = new_chunk_size

    def cancel(self):
        ciel.log("Stream-fetch %s: cancelling" % self.ref.id, "CURL_FETCH", logging.DEBUG)
        self.cancelled = True
        if self.current_data_fetch is not None:
            self.current_data_fetch.cancel()
        self.complete(False)

    def _advertisment(self, bytes=None, done=None, absent=None, failed=None):
        if self.cancelled:
            return
        if done or absent or failed:
            self.subscribed_to_remote_adverts = False
        if absent is True or failed is True:
            if absent is True:
                ciel.log("Stream-fetch %s: advertisment subscription reported file absent" % self.ref.id, "CURL_FETCH", logging.WARNING)
            else:
                ciel.log("Stream-fetch %s: advertisment reported remote production failure" % self.ref.id, "CURL_FETCH", logging.WARNING)
            self.remote_failed = True
            if self.current_data_fetch is None:
                self.complete(False)
        else:
            ciel.log("Stream-fetch %s: got advertisment: bytes %d done %s" % (self.ref.id, bytes, done), "CURL_FETCH", logging.DEBUG)
            if self.latest_advertisment <= bytes:
                self.latest_advertisment = bytes
            else:
                ciel.log("Stream-fetch %s: intriguing anomaly: advert for %d bytes; currently have %d. Probable reordering in the network" % (self.ref.id, bytes, self.latest_advertisment), "CURL_FETCH", logging.WARNING)
            if self.remote_done and not done:
                ciel.log("Stream-fetch %s: intriguing anomaly: advert said not-done, but we are. Probable reordering in the network" % self.ref.id, "CURL_FETCH", logging.WARNING)
            self.remote_done = self.remote_done or done
            if self.current_data_fetch is None:
                self.check_complete()

    def advertisment(self, *pargs, **kwargs):
        do_from_curl_thread(lambda: self._advertisment(*pargs, **kwargs))

# Represents pycURL doing a fetch, with potentially many clients listening to the results.
class pycURLFetchInProgress:
        
    def __init__(self, ref):
        self.listeners = []
        self.last_progress = 0
        self.ref = ref
        self.bs_ctx = create_fetch_file_for_ref(self.ref)
        self.chunk_size = None
        self.completed = False

    def set_fetch_context(self, fetch_context):
        self.fetch_context = fetch_context

    def progress(self, bytes):
        for l in self.listeners:
            l.progress(bytes)
        self.last_progress = bytes

    def result(self, success):
        self.completed = True
        del active_http_transfers[self.ref.id]
        if success:
            ref = SW2_ConcreteReference(self.ref.id, self.last_progress, [get_own_netloc()])
            self.bs_ctx.commit()
        else:
            ref = None
        for l in self.listeners:
            l.result(success, ref)

    def reset(self):
        for l in self.listeners:
            l.reset()

    def update_chunk_size(self):
        interested_listeners = filter(lambda x: x.chunk_size is not None, self.listeners)
        if len(interested_listeners) != 0:
            interested_listeners.sort(key=lambda x: x.chunk_size)
            self.fetch_context.set_chunk_size(interested_listeners[0].chunk_size)

    def unsubscribe(self, fetch_client):
        if self.completed:
            ciel.log("Removing fetch client %s: transfer had already completed" % fetch_client, "CURL_FETCH", logging.WARNING)
            return
        self.listeners.remove(fetch_client)
        self.update_chunk_size()
        fetch_client.result(False)
        if len(self.listeners) == 0:
            ciel.log("Removing fetch client %s: no clients remain, cancelling transfer" % fetch_client, "CURL_FETCH", logging.DEBUG)
            self.fetch_context.cancel()

    def add_listener(self, fetch_client):
        self.listeners.append(fetch_client)
        fetch_client.progress(self.last_progress)
        self.update_chunk_size()

# Represents a single client to an HTTP fetch. 
# Also proxies calls so that everything from here on up is in the cURL thread.
class HttpTransferContext:
    
    def __init__(self, ref, fetch_client):
        self.ref = ref
        self.fetch_client = fetch_client
        self.fetch = None

    def start_http_fetch(self):
        new_fetch = pycURLFetchInProgress(self.ref)
        if isinstance(self.ref, SW2_ConcreteReference) or isinstance(self.ref, SW2_FetchReference):
            new_ctx = FileTransferContext(self.ref, new_fetch, self.fetch_client)
        else:
            new_ctx = StreamTransferContext(self.ref, new_fetch, self.fetch_client)
        new_fetch.set_fetch_context(new_ctx)
        active_http_transfers[self.ref.id] = new_fetch
        new_ctx.start()
        
    def _start(self):
        if self.ref.id in active_http_transfers:
            ciel.log("Joining existing fetch for ref %s" % self.ref, "BLOCKSTORE", logging.DEBUG)
        else:
            self.start_http_fetch()
        active_http_transfers[self.ref.id].add_listener(self.fetch_client)
        self.fetch = active_http_transfers[self.ref.id]
        self.fetch_client.set_filename(self.fetch.bs_ctx.filename, False)

    def start(self):
        do_from_curl_thread(lambda: self._start())

    def _unsubscribe(self):
        self.fetch.unsubscribe(self.fetch_client)

    def unsubscribe(self, fetcher):
        do_from_curl_thread(lambda: self._unsubscribe())


########NEW FILE########
__FILENAME__ = pycurl_rpc
# Copyright (c) 2010--11 Chris Smowton <Chris.Smowton@cl.cam.ac.uk>
#
# Permission to use, copy, modify, and distribute this software for any
# purpose with or without fee is hereby granted, provided that the above
# copyright notice and this permission notice appear in all copies.
#
# THE SOFTWARE IS PROVIDED "AS IS" AND THE AUTHOR DISCLAIMS ALL WARRANTIES
# WITH REGARD TO THIS SOFTWARE INCLUDING ALL IMPLIED WARRANTIES OF
# MERCHANTABILITY AND FITNESS. IN NO EVENT SHALL THE AUTHOR BE LIABLE FOR
# ANY SPECIAL, DIRECT, INDIRECT, OR CONSEQUENTIAL DAMAGES OR ANY DAMAGES
# WHATSOEVER RESULTING FROM LOSS OF USE, DATA OR PROFITS, WHETHER IN AN
# ACTION OF CONTRACT, NEGLIGENCE OR OTHER TORTIOUS ACTION, ARISING OUT OF
# OR IN CONNECTION WITH THE USE OR PERFORMANCE OF THIS SOFTWARE.

from cStringIO import StringIO
import threading
import ciel.runtime.pycurl_thread
import pycurl

class pycURLBufferContext(ciel.runtime.pycurl_thread.pycURLContext):

    def __init__(self, method, in_str, out_fp, url, result_callback):
        
        ciel.runtime.pycurl_thread.pycURLContext.__init__(self, url, result_callback)

        self.write_fp = out_fp

        self.curl_ctx.setopt(pycurl.WRITEFUNCTION, self.write)
        if method == "POST":
            self.curl_ctx.setopt(pycurl.POST, True)
            self.curl_ctx.setopt(pycurl.POSTFIELDS, in_str)
            self.curl_ctx.setopt(pycurl.POSTFIELDSIZE, len(in_str))
            self.curl_ctx.setopt(pycurl.HTTPHEADER, ["Content-Type: application/octet-stream", "Expect:"])

    def write(self, data):
        self.write_fp.write(data)
        return len(data)

class BufferTransferContext:
        
    def __init__(self, method, url, postdata, result_callback=None):
        
        self.response_buffer = StringIO()
        self.completed_event = threading.Event()
        self.result_callback = result_callback
        self.url = url
        self.curl_ctx = pycURLBufferContext(method, postdata, self.response_buffer, url, self.result)

    def start(self):

        self.curl_ctx.start()

    def get_result(self):

        self.completed_event.wait()
        if self.success:
            return self.response_string
        else:
            raise Exception("Curl-post failed. Possible error-document: %s" % self.response_string)

    def result(self, success):
            
        self.response_string = self.response_buffer.getvalue()
        self.success = success
        self.response_buffer.close()
        self.completed_event.set()
        if self.result_callback is not None:
            self.result_callback(success, self.url)

# Called from cURL thread
def _post_string_noreturn(url, postdata, result_callback=None):
    ctx = BufferTransferContext("POST", url, postdata, result_callback)
    ctx.start()

def post_string_noreturn(url, postdata, result_callback=None):
    ciel.runtime.pycurl_thread.do_from_curl_thread(lambda: _post_string_noreturn(url, postdata, result_callback))

# Called from cURL thread
def _post_string(url, postdata):
    ctx = BufferTransferContext("POST", url, postdata)
    ctx.start()
    return ctx

def post_string(url, postdata):
    ctx = ciel.runtime.pycurl_thread.do_from_curl_thread_sync(lambda: _post_string(url, postdata))
    return ctx.get_result()

# Called from the cURL thread
def _get_string(url):
    ctx = BufferTransferContext("GET", url, "")
    ctx.start()
    return ctx

def get_string(url):
    ctx = ciel.runtime.pycurl_thread.do_from_curl_thread_sync(lambda: _get_string(url))
    return ctx.get_result()

########NEW FILE########
__FILENAME__ = pycurl_thread
# Copyright (c) 2010--11 Chris Smowton <Chris.Smowton@cl.cam.ac.uk>
#
# Permission to use, copy, modify, and distribute this software for any
# purpose with or without fee is hereby granted, provided that the above
# copyright notice and this permission notice appear in all copies.
#
# THE SOFTWARE IS PROVIDED "AS IS" AND THE AUTHOR DISCLAIMS ALL WARRANTIES
# WITH REGARD TO THIS SOFTWARE INCLUDING ALL IMPLIED WARRANTIES OF
# MERCHANTABILITY AND FITNESS. IN NO EVENT SHALL THE AUTHOR BE LIABLE FOR
# ANY SPECIAL, DIRECT, INDIRECT, OR CONSEQUENTIAL DAMAGES OR ANY DAMAGES
# WHATSOEVER RESULTING FROM LOSS OF USE, DATA OR PROFITS, WHETHER IN AN
# ACTION OF CONTRACT, NEGLIGENCE OR OTHER TORTIOUS ACTION, ARISING OUT OF
# OR IN CONNECTION WITH THE USE OR PERFORMANCE OF THIS SOFTWARE.

import ciel
import logging
import fcntl
import pycurl
import os
import threading
import select

from errno import EAGAIN

class pycURLContext:

    def __init__(self, url, result_callback):

        self.result_callback = result_callback
        self.url = url

        self.curl_ctx = pycurl.Curl()
        self.curl_ctx.setopt(pycurl.FOLLOWLOCATION, 1)
        self.curl_ctx.setopt(pycurl.MAXREDIRS, 5)
        self.curl_ctx.setopt(pycurl.CONNECTTIMEOUT, 30)
        self.curl_ctx.setopt(pycurl.TIMEOUT, 300)
        self.curl_ctx.setopt(pycurl.NOSIGNAL, 1)
        self.curl_ctx.setopt(pycurl.URL, str(url))

        self.curl_ctx.ctx = self

    def start(self):
        add_fetch(self)

    def success(self):
        self.result_callback(True)
        self.cleanup()

    def failure(self, errno, errmsg):
        ciel.log("Transfer failure: %s error %s / %s" % (self.url, errno, errmsg), "CURL", logging.WARNING)
        self.result_callback(False)
        self.cleanup()

    def cancel(self):
        remove_fetch(self)

    def cleanup(self):
        self.curl_ctx.close()

class SelectableEventQueue:

    def set_fd_nonblocking(self, fd):
        oldflags = fcntl.fcntl(fd, fcntl.F_GETFL)
        newflags = oldflags | os.O_NONBLOCK
        fcntl.fcntl(fd, fcntl.F_SETFL, newflags)

    def __init__(self):
        self._lock = threading.Lock()
        self.event_pipe_read, self.event_pipe_write = os.pipe()
        self.set_fd_nonblocking(self.event_pipe_read)
        self.set_fd_nonblocking(self.event_pipe_write)
        self.event_queue = []

    def drain_event_pipe(self):
        try:
            while(len(os.read(self.event_pipe_read, 1024)) >= 0):
                pass
        except OSError, e:
            if e.errno == EAGAIN:
                return
            else:
                raise

    def notify_event(self):
        try:
            os.write(self.event_pipe_write, "X")
        except OSError, e:
            if e.errno == EAGAIN:
                # Event pipe is full -- that's fine, the thread will wake next time it selects.
                return
            else:
                raise

    def post_event(self, ev):
        with self._lock:
            self.event_queue.append(ev)
            self.notify_event()

    def dispatch_events(self):
        with self._lock:
            ret = (len(self.event_queue) > 0)
            to_run = self.event_queue
            self.event_queue = []
            self.drain_event_pipe()
        for event in to_run:
            event()
        return ret

    def get_select_fds(self):
        return [self.event_pipe_read], [], []

    # Called after all event-posting and dispatching is complete
    def cleanup(self):
        os.close(self.event_pipe_read)
        os.close(self.event_pipe_write)

class pycURLThread:

    def __init__(self):
        self.thread = None
        self.curl_ctx = pycurl.CurlMulti()
        self.curl_ctx.setopt(pycurl.M_PIPELINING, 0)
        self.curl_ctx.setopt(pycurl.M_MAXCONNECTS, 20)
        self.active_fetches = []
        self.event_queue = SelectableEventQueue()
        self.event_sources = []
        self.thread = threading.Thread(target=self.pycurl_main_loop, name="Ciel pycURL Thread")
        self.dying = False

    def subscribe(self, bus):
        bus.subscribe('start', self.start, 75)
        bus.subscribe('stop', self.stop, 10)

    def start(self):
        self.thread.start()

    # Called from cURL thread
    def add_fetch(self, new_context):
        self.active_fetches.append(new_context)
        self.curl_ctx.add_handle(new_context.curl_ctx)

    # Called from cURL thread
    def add_event_source(self, src):
        self.event_sources.append(src)

    def do_from_curl_thread(self, callback):
        if threading.current_thread().ident == self.thread.ident:
            callback()
        else:
            self.event_queue.post_event(callback)

    def call_and_signal(self, callback, e, ret):
        ret.ret = callback()
        e.set()

    class ReturnBucket:
        def __init__(self):
            self.ret = None

    def do_from_curl_thread_sync(self, callback):
        if threading.current_thread().ident == self.thread.ident:
            return callback()
        else:
            e = threading.Event()
            ret = pycURLThread.ReturnBucket()
            self.event_queue.post_event(lambda: self.call_and_signal(callback, e, ret))
            e.wait()
            return ret.ret

    def _stop_thread(self):
        self.dying = True
    
    def stop(self):
        self.event_queue.post_event(self._stop_thread)

    def remove_fetch(self, ctx):
        self.curl_ctx.remove_handle(ctx.curl_ctx)
        self.active_fetches.remove(ctx)

    def pycurl_main_loop(self):
        while True:
            # Curl-perform and process events until there's nothing left to do
            while True:
                go_again = False
                # Perform until cURL has nothing left to do
                while True:
                    ret, num_handles = self.curl_ctx.perform()
                    if ret != pycurl.E_CALL_MULTI_PERFORM:
                        break
                # Fire callbacks on completed fetches
                while True:
                    num_q, ok_list, err_list = self.curl_ctx.info_read()
                    if len(ok_list) > 0 or len(err_list) > 0:
                        go_again = True
                    for c in ok_list:
                        self.curl_ctx.remove_handle(c)
                        response_code = c.getinfo(pycurl.RESPONSE_CODE)
#                        ciel.log.error("Curl success: %s -- %s" % (c.ctx.description, str(response_code)))
                        if str(response_code).startswith("2"):
                            c.ctx.success()
                        else:
                            ciel.log.error("Curl failure: HTTP %s" % str(response_code), "CURL_FETCH", logging.WARNING)
                            c.ctx.failure(response_code, "")
                        self.active_fetches.remove(c.ctx)
                    for c, errno, errmsg in err_list:
                        self.curl_ctx.remove_handle(c)
                        ciel.log.error("Curl failure: %s, %s" % 
                                           (str(errno), str(errmsg)), "CURL_FETCH", logging.WARNING)
                        c.ctx.failure(errno, errmsg)
                        self.active_fetches.remove(c.ctx)
                    if num_q == 0:
                        break
                # Process events, both from out-of-thread and due to callbacks
                if self.event_queue.dispatch_events():
                    go_again = True
                if self.dying:
                    return
                if not go_again:
                    break
            if self.dying:
                return
            # Alright, all work appears to be done for now. Gather reasons to wake up.
            # Reason #1: cURL has work to do.
            read_fds, write_fds, exn_fds = self.curl_ctx.fdset()
            # Reason #2: out-of-thread events arrived.
            ev_rfds, ev_wfds, ev_exfds = self.event_queue.get_select_fds()
            # Reason #3: an event source has an interesting event
            for source in self.event_sources:
                rfds, wfds, efds = source.get_select_fds()
                ev_rfds.extend(rfds)
                ev_wfds.extend(wfds)
                ev_exfds.extend(efds)
            read_fds.extend(ev_rfds)
            write_fds.extend(ev_wfds)
            exn_fds.extend(ev_exfds)
            active_read, active_write, active_exn = select.select(read_fds, write_fds, exn_fds)
            for source in self.event_sources:
                source.notify_fds(active_read, active_write, active_exn)

singleton_pycurl_thread = None

def create_pycurl_thread(bus):
    global singleton_pycurl_thread
    singleton_pycurl_thread = pycURLThread()
    singleton_pycurl_thread.subscribe(bus)

def do_from_curl_thread(x):
    singleton_pycurl_thread.do_from_curl_thread(x)

def do_from_curl_thread_sync(x):
    return singleton_pycurl_thread.do_from_curl_thread_sync(x)

def add_fetch(x):
    singleton_pycurl_thread.add_fetch(x)

def remove_fetch(x):
    singleton_pycurl_thread.remove_fetch(x)

def add_event_source(src):
    do_from_curl_thread(lambda: singleton_pycurl_thread.add_event_source(src))

########NEW FILE########
__FILENAME__ = remote_stat
# Copyright (c) 2010--11 Chris Smowton <Chris.Smowton@cl.cam.ac.uk>
#
# Permission to use, copy, modify, and distribute this software for any
# purpose with or without fee is hereby granted, provided that the above
# copyright notice and this permission notice appear in all copies.
#
# THE SOFTWARE IS PROVIDED "AS IS" AND THE AUTHOR DISCLAIMS ALL WARRANTIES
# WITH REGARD TO THIS SOFTWARE INCLUDING ALL IMPLIED WARRANTIES OF
# MERCHANTABILITY AND FITNESS. IN NO EVENT SHALL THE AUTHOR BE LIABLE FOR
# ANY SPECIAL, DIRECT, INDIRECT, OR CONSEQUENTIAL DAMAGES OR ANY DAMAGES
# WHATSOEVER RESULTING FROM LOSS OF USE, DATA OR PROFITS, WHETHER IN AN
# ACTION OF CONTRACT, NEGLIGENCE OR OTHER TORTIOUS ACTION, ARISING OUT OF
# OR IN CONNECTION WITH THE USE OR PERFORMANCE OF THIS SOFTWARE.

from ciel.runtime.pycurl_rpc import post_string_noreturn
from ciel.runtime.block_store import get_own_netloc

import simplejson
import threading

import ciel
import logging

module_lock = threading.RLock()

# Maps reference ID -> entity interested in advertisments
remote_stat_subscriptions = dict()

def subscribe_remote_output_nopost(refid, subscriber):
    with module_lock:
        try:
            if remote_stat_subscriptions[refid] != subscriber:
                raise Exception("Subscribing %s: Remote-stat currently only supports one subscriber per remote output!" % refid)
        except KeyError:
            # Nobody is currently subscribed
            pass
        remote_stat_subscriptions[refid] = subscriber

def subscribe_remote_output(refid, remote_netloc, chunk_size, subscriber):
    subscribe_remote_output_nopost(refid, subscriber)
    post_data = simplejson.dumps({"netloc": get_own_netloc(), "chunk_size": chunk_size})
    post_string_noreturn("http://%s/control/streamstat/%s/subscribe" % (remote_netloc, refid), post_data, result_callback=(lambda success, url: subscribe_result(refid, success, url)))

def unsubscribe_remote_output_nopost(refid):
    with module_lock:
        del remote_stat_subscriptions[refid]

def unsubscribe_remote_output(refid):
    unsubscribe_remote_output_nopost(refid)
    netloc = get_own_netloc()
    post_data = simplejson.dumps({"netloc": netloc})
    post_string_noreturn("http://%s/control/streamstat/%s/unsubscribe" 
                          % (netloc, refid), post_data)

def subscribe_result(refid, success, url):
    try:
        with module_lock:
            remote_stat_subscriptions[refid].subscribe_result(success, url)
    except KeyError:
        ciel.log("Subscribe-result for %s ignored as no longer subscribed" % url, "REMOTE_STAT", logging.WARNING)

def receive_stream_advertisment(id, **args):
    try:
        with module_lock:
            remote_stat_subscriptions[id].advertisment(**args)
    except KeyError:
        ciel.log("Got advertisment for %s which is not an ongoing stream" % id, "REMOTE_STAT", logging.WARNING)


########NEW FILE########
__FILENAME__ = stopwatch
# Copyright (c) 2011 Derek Murray <derek.murray@cl.cam.ac.uk>
#
# Permission to use, copy, modify, and distribute this software for any
# purpose with or without fee is hereby granted, provided that the above
# copyright notice and this permission notice appear in all copies.
#
# THE SOFTWARE IS PROVIDED "AS IS" AND THE AUTHOR DISCLAIMS ALL WARRANTIES
# WITH REGARD TO THIS SOFTWARE INCLUDING ALL IMPLIED WARRANTIES OF
# MERCHANTABILITY AND FITNESS. IN NO EVENT SHALL THE AUTHOR BE LIABLE FOR
# ANY SPECIAL, DIRECT, INDIRECT, OR CONSEQUENTIAL DAMAGES OR ANY DAMAGES
# WHATSOEVER RESULTING FROM LOSS OF USE, DATA OR PROFITS, WHETHER IN AN
# ACTION OF CONTRACT, NEGLIGENCE OR OTHER TORTIOUS ACTION, ARISING OUT OF
# OR IN CONNECTION WITH THE USE OR PERFORMANCE OF THIS SOFTWARE.
import datetime

class Stopwatch:
    def __init__(self):
        self.enabled = False 
        self.times = {}
        self.starts = {}
        
    def enable(self):
        self.enabled = True
        
    def _start_at(self, name, at):
        self.starts[name] = at
        
    def start(self, name):
        if self.enabled:
            self._start_at(name, datetime.datetime.now())
        
    def _stop_at(self, name, at):
        try:
            start = self.starts.pop(name)
            finish = at
            
            try:
                time_list = self.times[name]
            except KeyError:
                time_list = []
                self.times[name] = time_list
            
            time_list.append(finish - start)
            
        except KeyError:
            pass
        
    def stop(self, name):
        if self.enabled:
            self._stop_at(name, datetime.datetime.now())
        
    def lap(self, name):
        if self.enabled:
            lap_time = datetime.datetime.now()
            self._stop_at(name, lap_time)
            self._start_at(name, lap_time)
    
    def multi(self, starts=[], stops=[], laps=[]):
        if self.enabled:
            now = datetime.datetime.now()
            for start_name in starts:
                self._start_at(start_name, now)
            for stop_name in stops:
                self._stop_at(stop_name, now)
            for lap_name in laps:
                self._stop_at(lap_name, now)
                self._start_at(lap_name, now)
                
    def get_times(self, name):
        return self.times[name]
########NEW FILE########
__FILENAME__ = task
# Copyright (c) 2010--2011 Derek Murray <derek.murray@cl.cam.ac.uk>
#
# Permission to use, copy, modify, and distribute this software for any
# purpose with or without fee is hereby granted, provided that the above
# copyright notice and this permission notice appear in all copies.
#
# THE SOFTWARE IS PROVIDED "AS IS" AND THE AUTHOR DISCLAIMS ALL WARRANTIES
# WITH REGARD TO THIS SOFTWARE INCLUDING ALL IMPLIED WARRANTIES OF
# MERCHANTABILITY AND FITNESS. IN NO EVENT SHALL THE AUTHOR BE LIABLE FOR
# ANY SPECIAL, DIRECT, INDIRECT, OR CONSEQUENTIAL DAMAGES OR ANY DAMAGES
# WHATSOEVER RESULTING FROM LOSS OF USE, DATA OR PROFITS, WHETHER IN AN
# ACTION OF CONTRACT, NEGLIGENCE OR OTHER TORTIOUS ACTION, ARISING OUT OF
# OR IN CONNECTION WITH THE USE OR PERFORMANCE OF THIS SOFTWARE.
from ciel.public.references import SW2_StreamReference, SW2_FixedReference
import datetime
import time

TASK_CREATED = -1
TASK_BLOCKING = 0
TASK_SELECTING = 1
TASK_RUNNABLE = 2
TASK_QUEUED_STREAMING = 3
TASK_QUEUED = 4
TASK_ASSIGNED = 6
TASK_COMMITTED = 7
TASK_FAILED = 8
TASK_ABORTED = 9

TASK_STATES = {'CREATED': TASK_CREATED,
               'BLOCKING': TASK_BLOCKING,
               'SELECTING': TASK_SELECTING,
               'RUNNABLE': TASK_RUNNABLE,
               'QUEUED_STREAMING': TASK_QUEUED_STREAMING,
               'QUEUED': TASK_QUEUED,
               'ASSIGNED': TASK_ASSIGNED,
               'COMMITTED': TASK_COMMITTED,
               'FAILED': TASK_FAILED,
               'ABORTED': TASK_ABORTED}

TASK_STATE_NAMES = {}
for (name, number) in TASK_STATES.items():
    TASK_STATE_NAMES[number] = name

class TaskPoolTask:
    
    def __init__(self, task_id, parent_task, handler, inputs, dependencies, expected_outputs, task_private=None, state=TASK_CREATED, job=None, taskset=None, worker_private=None, workers=[], scheduling_class=None, type=None):
        self.task_id = task_id
        
        # Task creation graph.
        self.parent = parent_task
        self.children = []
        
        self.handler = handler
        
        self.inputs = inputs
        self.dependencies = dependencies
            
        self.expected_outputs = expected_outputs

        self.task_private = task_private

        self.unfinished_input_streams = set()

        self.constrained_location_checked = False
        self.constrained_location = None

        self._blocking_dict = {}
            
        self.history = []
        
        self.job = job

        self.taskset = taskset
        
        self.worker_private = worker_private
        
        self.type = type
        
        self.worker = None
        
        self.state = None
        self.set_state(state)
        
        #self.worker = None
        self.scheduling_class = scheduling_class
        
        self.saved_continuation_uri = None

        self.event_index = 0
        self.current_attempt = 0
        
        self.profiling = {}

    def __str__(self):
        return 'TaskPoolTask(%s)' % self.task_id

    def set_state(self, state, additional=None):
        if self.job is not None and self.state is not None:
            self.job.record_state_change(self, self.state, state, additional)
        self.record_event(TASK_STATE_NAMES[state], additional=additional)
        #print self, TASK_STATE_NAMES[self.state] if self.state is not None else None, '-->', TASK_STATE_NAMES[state] if state is not None else None
        self.state = state
        
    def record_event(self, description, time=None, additional=None):
        if time is None:
            time = datetime.datetime.now()
        if additional is not None:
            self.history.append((time, (description, additional)))
        else:
            self.history.append((time, description))
        
    def is_blocked(self):
        return self.state == TASK_BLOCKING
    
    def is_queued_streaming(self):
        return self.state == TASK_QUEUED_STREAMING
        
    def blocked_on(self):
        if self.state == TASK_BLOCKING:
            return self._blocking_dict.keys()
        else:
            return []

    def set_profiling(self, profiling):
        if profiling is not None:
            self.profiling.update(profiling)
            try:    
                self.record_event('WORKER_CREATED', datetime.datetime.fromtimestamp(profiling['CREATED']))
                self.record_event('WORKER_STARTED', datetime.datetime.fromtimestamp(profiling['STARTED']))
                self.record_event('WORKER_FINISHED', datetime.datetime.fromtimestamp(profiling['FINISHED']))
            except KeyError:
                pass
    
    def get_type(self):
        if self.type is None:
            # Implicit task type assigned from the executor name, the number of inputs and the number of outputs.
            # FIXME: Obviously, we could do better.
            return '%s:%d:%d' % (self.handler, len(self.inputs), len(self.expected_outputs))
        else:
            return self.type
    
    def get_profiling(self):
        return self.profiling

    def set_worker(self, worker):
        self.set_state(TASK_ASSIGNED, additional=worker.netloc)
        self.worker = worker

    def unset_worker(self, worker):
        assert self.worker is worker
        self.worker = None

    def get_worker(self):
        """Returns the worker to which this task is assigned."""
        return self.worker

    def block_on(self, global_id, local_id):
        self.set_state(TASK_BLOCKING)
        try:
            self._blocking_dict[global_id].add(local_id)
        except KeyError:
            self._blocking_dict[global_id] = set([local_id])
            
    def notify_reference_changed(self, global_id, ref, task_pool):
        if global_id in self.unfinished_input_streams:
            self.unfinished_input_streams.remove(global_id)
            task_pool.unsubscribe_task_from_ref(self, ref)
            self.inputs[ref.id] = ref
            if len(self.unfinished_input_streams) == 0:
                if self.state == TASK_QUEUED_STREAMING:
                    self.set_state(TASK_QUEUED)
        else:
            if self.state == TASK_BLOCKING:
                local_ids = self._blocking_dict.pop(global_id)
                for local_id in local_ids:
                    self.inputs[local_id] = ref
                if isinstance(ref, SW2_StreamReference):
                    # Stay subscribed; this ref is still interesting
                    self.unfinished_input_streams.add(global_id)
                else:
                    # Don't need to hear about this again
                    task_pool.unsubscribe_task_from_ref(self, ref)
                if len(self._blocking_dict) == 0:
                    self.set_state(TASK_RUNNABLE)

    def notify_ref_table_updated(self, ref_table_entry):
        global_id = ref_table_entry.ref.id
        ref = ref_table_entry.ref
        if global_id in self.unfinished_input_streams:
            self.unfinished_input_streams.remove(global_id)
            ref_table_entry.remove_consumer(self)
            if len(self.unfinished_input_streams) == 0:
                if self.state == TASK_QUEUED_STREAMING:
                    self.set_state(TASK_QUEUED)
        else:
            if self.state == TASK_BLOCKING:
                local_ids = self._blocking_dict.pop(global_id)
                for local_id in local_ids:
                    self.inputs[local_id] = ref
                if isinstance(ref, SW2_StreamReference):
                    # Stay subscribed; this ref is still interesting
                    self.unfinished_input_streams.add(global_id)
                else:
                    # Don't need to hear about this again
                    ref_table_entry.remove_consumer(self)
                if len(self._blocking_dict) == 0:
                    self.set_state(TASK_RUNNABLE)
        
    def convert_dependencies_to_futures(self):
        new_deps = {}
        for local_id, ref in self.dependencies.items(): 
            new_deps[local_id] = ref.as_future()
        self.dependencies = new_deps

    def has_constrained_location(self):
        for dep in self.dependencies.values():
            if isinstance(dep, SW2_FixedReference):
                self.constrained_location = dep.fixed_netloc
        self.constrained_location_checked = True
                
    def get_constrained_location(self):
        if not self.constrained_location_checked:
            self.has_constrained_location()
        return self.constrained_location

    def as_descriptor(self, long=False):        
        descriptor = {'task_id': self.task_id,
                      'dependencies': self.dependencies.values(),
                      'handler': self.handler,
                      'expected_outputs': self.expected_outputs,
                      'inputs': self.inputs.values(),
                      'event_index': self.event_index,
                      'job' : self.job.id}
        
        descriptor['parent'] = self.parent.task_id if self.parent is not None else None
        
        if long:
            descriptor['history'] = map(lambda (t, name): (time.mktime(t.timetuple()) + t.microsecond / 1e6, name), self.history)
            descriptor['state'] = TASK_STATE_NAMES[self.state]
            descriptor['children'] = [x.task_id for x in self.children]
            descriptor['profiling'] = self.profiling
            descriptor['worker'] = self.worker.netloc if self.worker is not None else None
        
        if self.task_private is not None:
            descriptor['task_private'] = self.task_private
        if self.scheduling_class is not None:
            descriptor['scheduling_class'] = self.scheduling_class
        if self.type is not None:
            descriptor['scheduling_type'] = self.type
        
        return descriptor

class DummyJob:
    """Used to ensure that tasks on the worker can refer to their job (for inheriting job ID, e.g.)."""
    
    def __init__(self, id):
        self.id = id
        
    def record_state_change(self, task, from_state, to_state, additional=None):
        pass

def build_taskpool_task_from_descriptor(task_descriptor, parent_task=None, taskset=None):

    task_id = task_descriptor['task_id']

    handler = task_descriptor['handler']
    
    if parent_task is not None:
        job = parent_task.job
    else:
        try:
            job = DummyJob(task_descriptor['job'])
        except KeyError:
            job = DummyJob(None)
    
    try:
        inputs = dict([(ref.id, ref) for ref in task_descriptor['inputs']])
    except KeyError:
        inputs = {}
        
    dependencies = dict([(ref.id, ref) for ref in task_descriptor['dependencies']])
    expected_outputs = task_descriptor['expected_outputs']

    try:
        task_private = task_descriptor['task_private']
    except KeyError:
        task_private = None

    try:
        worker_private = task_descriptor['worker_private']
    except KeyError:
        worker_private = {}

    try:
        workers = task_descriptor['workers']
    except KeyError:
        workers = []

    try:
        scheduling_class = task_descriptor['scheduling_class']
    except KeyError:
        if parent_task is not None:
            # With no other information, scheduling class is inherited from the parent.
            scheduling_class = parent_task.scheduling_class
        else:
            scheduling_class = None
    
    try:
        type = task_descriptor['scheduling_type']
    except KeyError:
        type = None
    
    state = TASK_CREATED
    
    return TaskPoolTask(task_id, parent_task, handler, inputs, dependencies, expected_outputs, task_private, state, job, taskset, worker_private, workers, scheduling_class, type)

########NEW FILE########
__FILENAME__ = task_executor
# Copyright (c) 2010--2011  Derek Murray <derek.murray@cl.cam.ac.uk>
#                           Christopher Smowton <chris.smowton@cl.cam.ac.uk>
#
# Permission to use, copy, modify, and distribute this software for any
# purpose with or without fee is hereby granted, provided that the above
# copyright notice and this permission notice appear in all copies.
#
# THE SOFTWARE IS PROVIDED "AS IS" AND THE AUTHOR DISCLAIMS ALL WARRANTIES
# WITH REGARD TO THIS SOFTWARE INCLUDING ALL IMPLIED WARRANTIES OF
# MERCHANTABILITY AND FITNESS. IN NO EVENT SHALL THE AUTHOR BE LIABLE FOR
# ANY SPECIAL, DIRECT, INDIRECT, OR CONSEQUENTIAL DAMAGES OR ANY DAMAGES
# WHATSOEVER RESULTING FROM LOSS OF USE, DATA OR PROFITS, WHETHER IN AN
# ACTION OF CONTRACT, NEGLIGENCE OR OTHER TORTIOUS ACTION, ARISING OUT OF
# OR IN CONNECTION WITH THE USE OR PERFORMANCE OF THIS SOFTWARE.
from __future__ import with_statement
from ciel.runtime.plugins import AsynchronousExecutePlugin
from ciel.runtime.exceptions import ReferenceUnavailableException, MissingInputException,\
    AbortedException
from ciel.runtime.local_task_graph import LocalTaskGraph, LocalJobOutput
from threading import Lock
import logging
import hashlib
import ciel
import threading
import datetime
import time
import urlparse
from ciel.runtime.executors.base import BaseExecutor

class TaskExecutorPlugin(AsynchronousExecutePlugin):
    
    def __init__(self, bus, worker, master_proxy, execution_features, num_threads=1):
        AsynchronousExecutePlugin.__init__(self, bus, num_threads, "execute_task")
        self.worker = worker
        self.block_store = worker.block_store
        self.master_proxy = master_proxy
        self.execution_features = execution_features
        self.current_task_set = None
        self._lock = Lock()
    
    # Out-of-thread asynchronous notification calls

    def abort_task(self, task_id):
        with self._lock:
            if self.current_task_set is not None:
                self.current_task_set.abort_task(task_id)

    # Main entry point

    def handle_input(self, input):

        new_task_set = TaskSetExecutionRecord(input, self.block_store, self.master_proxy, self.execution_features, self.worker)
        with self._lock:
            self.current_task_set = new_task_set
        new_task_set.run()
        report_data = []
        for tr in new_task_set.task_records:
            if tr.success:
                report_data.append((tr.task_descriptor["task_id"], tr.success, (tr.spawned_tasks, tr.published_refs)))
            else:
                report_data.append((tr.task_descriptor["task_id"], tr.success, (tr.failure_reason, tr.failure_details, tr.failure_bindings)))
        self.master_proxy.report_tasks(input['job'], input['task_id'], report_data)
        with self._lock:
            self.current_task_set = None

class TaskSetExecutionRecord:

    def __init__(self, root_task_descriptor, block_store, master_proxy, execution_features, worker):
        self._lock = Lock()
        self.task_records = []
        self.current_task = None
        self.current_td = None
        self.block_store = block_store
        self.master_proxy = master_proxy
        self.execution_features = execution_features
        self.worker = worker
        self.reference_cache = dict([(ref.id, ref) for ref in root_task_descriptor["inputs"]])
        self.initial_td = root_task_descriptor
        self.task_graph = LocalTaskGraph(execution_features, [self.initial_td["task_id"]])
        self.job_output = LocalJobOutput(self.initial_td["expected_outputs"])
        for ref in self.initial_td["expected_outputs"]:
            self.task_graph.subscribe(ref, self.job_output)
        self.task_graph.spawn_and_publish([self.initial_td], self.initial_td["inputs"])

    def run(self):
        ciel.log.error("Running taskset starting at %s" % self.initial_td["task_id"], "TASKEXEC", logging.DEBUG)
        while not self.job_output.is_complete():
            next_td = self.task_graph.get_runnable_task()
            if next_td is None:
                ciel.log.error("No more runnable tasks", "TASKEXEC", logging.DEBUG)
                break
            next_td["inputs"] = [self.retrieve_ref(ref) for ref in next_td["dependencies"]]
            task_record = TaskExecutionRecord(next_td, self, self.execution_features, self.block_store, self.master_proxy, self.worker)
            with self._lock:
                self.current_task = task_record
                self.current_td = next_td
            try:
                task_record.run()
            except:
                ciel.log.error('Error during executor task execution', 'TASKEXEC', logging.ERROR, True)
            with self._lock:
                self.current_task.cleanup()
                self.current_task = None
                self.current_td = None
            self.task_records.append(task_record)
            if task_record.success:
                self.task_graph.spawn_and_publish(task_record.spawned_tasks, task_record.published_refs, next_td)
            else:
                break
        ciel.log.error("Taskset complete", "TASKEXEC", logging.DEBUG)

    def retrieve_ref(self, ref):
        if ref.is_consumable():
            return ref
        else:
            try:
                return self.reference_cache[ref.id]
            except KeyError:
                raise ReferenceUnavailableException(ref.id)

    def publish_ref(self, ref):
        self.reference_cache[ref.id] = ref

    def abort_task(self, task_id):
        with self._lock:
            if self.current_td["task_id"] == task_id:
                self.current_task.executor.abort()

class TaskExecutionRecord:

    def __init__(self, task_descriptor, task_set, execution_features, block_store, master_proxy, worker):
        self.published_refs = []
        self.spawned_tasks = []
        self.spawn_counter = 0
        self.publish_counter = 0
        self.task_descriptor = task_descriptor
        self.task_set = task_set
        self.execution_features = execution_features
        self.block_store = block_store
        self.master_proxy = master_proxy
        self.worker = worker
        self.executor = None
        self.failed = False
        self.success = False
        self.aborted = False
        self._executor_lock = threading.Lock()
        
        self.creation_time = datetime.datetime.now()
        self.start_time = None
        self.finish_time = None
        self.fetches = []
        
    def as_timestamp(self, t):
        return time.mktime(t.timetuple()) + t.microsecond / 1e6
        
    def get_profiling(self):
        profile = {'CREATED' : self.as_timestamp(self.creation_time),
                   'STARTED' : self.as_timestamp(self.start_time),
                   'FINISHED' : self.as_timestamp(self.finish_time)}
        
        fetches = {}
        for url, size in self.fetches:
            netloc = urlparse.urlparse(url).netloc
            try:
                fetches[netloc] += size
            except KeyError:
                fetches[netloc] = size

        profile['FETCHED'] = fetches
        
        return profile
        
    def add_completed_fetch(self, url, size):
        self.fetches.append((url, size))
        
    def run(self):
        ciel.engine.publish("worker_event", "Start execution " + repr(self.task_descriptor['task_id']) + " with handler " + self.task_descriptor['handler'])
        ciel.log.error("Starting task %s with handler %s" % (str(self.task_descriptor['task_id']), self.task_descriptor['handler']), 'TASK', logging.DEBUG, False)
        try:
            self.start_time = datetime.datetime.now()
            
            # Need to do this to bring task_private into the execution context.
            BaseExecutor.prepare_task_descriptor_for_execute(self.task_descriptor, self, self.block_store)
        
            if "package_ref" in self.task_descriptor["task_private"]:
                self.package_ref = self.task_descriptor["task_private"]["package_ref"]
            else:
                self.package_ref = None
            
            with self._executor_lock:
                if self.aborted:
                    raise AbortedException()
                else:
                    self.executor = self.execution_features.get_executor(self.task_descriptor["handler"], self.worker)

            self.executor.run(self.task_descriptor, self)
            self.finish_time = datetime.datetime.now()
            
            self.success = not self.failed
            
            ciel.engine.publish("worker_event", "Completed execution " + repr(self.task_descriptor['task_id']))
            ciel.log.error("Completed task %s with handler %s" % (str(self.task_descriptor['task_id']), self.task_descriptor['handler']), 'TASK', logging.DEBUG, False)
        except MissingInputException as mie:
            ciel.log.error('Missing input in task %s with handler %s' % (str(self.task_descriptor['task_id']), self.task_descriptor['handler']), 'TASKEXEC', logging.ERROR, True)
            self.failure_bindings = mie.bindings
            self.failure_details = ""
            self.failure_reason = "MISSING_INPUT"
            self.finish_time = datetime.datetime.now()
            self.success = False
            raise
        except AbortedException:
            self.finish_time = datetime.datetime.now()
            self.success = False
            raise
        except Exception, e:
            ciel.log.error("Error in task %s with handler %s" % (str(self.task_descriptor['task_id']), self.task_descriptor['handler']), 'TASK', logging.ERROR, True)
            self.failure_bindings = dict()
            self.failure_details = getattr(e, "message", '')
            self.failure_reason = "RUNTIME_EXCEPTION"
            self.finish_time = datetime.datetime.now()
            self.success = False
            raise

    def cleanup(self):
        with self._executor_lock:
            if self.executor is not None:
                self.executor.cleanup()
                del self.executor
                self.executor = None
    
    def publish_ref(self, ref):
        self.published_refs.append(ref)
        self.task_set.publish_ref(ref)

    def prepublish_refs(self, refs):
        # I don't put these in the ref-cache now because local-master operation is currently single-threaded.
        self.master_proxy.publish_refs(self.task_descriptor["job"], self.task_descriptor["task_id"], refs)

    def create_spawned_task_name(self):
        sha = hashlib.sha1()
        sha.update('%s:%d' % (self.task_descriptor["task_id"], self.spawn_counter))
        ret = sha.hexdigest()
        self.spawn_counter += 1
        return ret
    
    def create_published_output_name(self, prefix=""):
        if prefix == "":
            prefix = "pub"
        ret = '%s:%s:%d' % (self.task_descriptor["task_id"], prefix, self.publish_counter)
        self.publish_counter += 1
        return ret

    def spawn_task(self, new_task_descriptor, **args):
        new_task_descriptor["task_id"] = self.create_spawned_task_name()
        if "dependencies" not in new_task_descriptor:
            new_task_descriptor["dependencies"] = []
        if "task_private" not in new_task_descriptor:
            new_task_descriptor["task_private"] = dict()
        if "expected_outputs" not in new_task_descriptor:
            new_task_descriptor["expected_outputs"] = []
        executor_class = self.execution_features.get_executor_class(new_task_descriptor["handler"])
        # Throws a BlameUserException if we can quickly determine the task descriptor is bad
        return_obj = executor_class.build_task_descriptor(new_task_descriptor, self, **args)
        self.spawned_tasks.append(new_task_descriptor)
        return return_obj

    def retrieve_ref(self, ref):
        return self.task_set.retrieve_ref(ref)

    def abort(self):
        with self._executor_lock:
            self.aborted = True
            if self.executor is not None:
                self.executor.abort()

########NEW FILE########
__FILENAME__ = task_graph
# Copyright (c) 2011 Derek Murray <derek.murray@cl.cam.ac.uk>
#
# Permission to use, copy, modify, and distribute this software for any
# purpose with or without fee is hereby granted, provided that the above
# copyright notice and this permission notice appear in all copies.
#
# THE SOFTWARE IS PROVIDED "AS IS" AND THE AUTHOR DISCLAIMS ALL WARRANTIES
# WITH REGARD TO THIS SOFTWARE INCLUDING ALL IMPLIED WARRANTIES OF
# MERCHANTABILITY AND FITNESS. IN NO EVENT SHALL THE AUTHOR BE LIABLE FOR
# ANY SPECIAL, DIRECT, INDIRECT, OR CONSEQUENTIAL DAMAGES OR ANY DAMAGES
# WHATSOEVER RESULTING FROM LOSS OF USE, DATA OR PROFITS, WHETHER IN AN
# ACTION OF CONTRACT, NEGLIGENCE OR OTHER TORTIOUS ACTION, ARISING OUT OF
# OR IN CONNECTION WITH THE USE OR PERFORMANCE OF THIS SOFTWARE.
from ciel.public.references import SW2_FutureReference, combine_references,\
    SW2_StreamReference
from ciel.runtime.task import TASK_CREATED, TASK_BLOCKING, TASK_COMMITTED,\
    TASK_RUNNABLE
import collections

class ReferenceTableEntry:
    """Represents information stored about a reference in the task graph."""
    
    def __init__(self, ref, producing_task=None): 
        self.ref = ref
        self.producing_task = producing_task
        self.consumers = None

    def update_producing_task(self, task):
        self.producing_task = task

    def combine_references(self, other_ref):
        self.ref = combine_references(self.ref, other_ref)

    def has_consumers(self):
        return self.consumers is not None and len(self.consumers) > 0

    def add_consumer(self, task):
        """
        task must implement the notify_ref_table_updated(self, ref_table_entry)
        method.
        """
        if self.consumers is None:
            self.consumers = set([task])
        else:
            self.consumers.add(task)

    def remove_consumer(self, task):
        if self.consumers is not None:
            self.consumers.remove(task)

class TaskGraphUpdate:
    
    def __init__(self):
        self.spawns = []
        self.publishes = []
        self.reduce_list = []

    def spawn(self, task):
        self.spawns.append(task)
        
    def publish(self, reference, producing_task=None):
        self.publishes.append((reference, producing_task))

    def commit(self, graph):
        for (reference, producing_task) in self.publishes:
            graph.publish(reference, producing_task)
            
        for task in self.spawns:
            graph.spawn(task, self)
            
        graph.reduce_graph_for_tasks(self.reduce_list)

class DynamicTaskGraph:
    
    def __init__(self):
        
        # Mapping from task ID to task object.
        self.tasks = {}
        
        # Mapping from reference ID to reference table entry.
        self.references = {}
        
    def spawn(self, task, tx=None):
        """Add a new task to the graph. If tx is None, this will cause an immediate
        reduction; otherwise, tasks-to-reduce will be added to tx.result_list."""
        
        # Record the task in the task table, if we don't already know about it.
        if task.task_id in self.tasks:
            return
        self.tasks[task.task_id] = task
        if task.parent is not None:
            task.parent.children.append(task)
        
        # Now update the reference table to account for the new task.
        # We will need to reduce this task if any of its outputs have consumers. 
        should_reduce = False
        for output_id in task.expected_outputs:
            ref_table_entry = self.publish(SW2_FutureReference(output_id), task)
            should_reduce = should_reduce or ref_table_entry.has_consumers()
            
        if should_reduce:
            if tx is not None:
                tx.reduce_list.append(task)
            else:
                self.reduce_graph_for_tasks([task])
    
    def publish(self, reference, producing_task=None):
        """Updates the information held about a reference. Returns the updated
        reference table entry for the reference."""
        try:
            
            ref_table_entry = self.get_reference_info(reference.id)
            if producing_task is not None:
                ref_table_entry.update_producing_task(producing_task)
            ref_table_entry.combine_references(reference)
            
            if ref_table_entry.has_consumers():
                consumers_copy = ref_table_entry.consumers.copy()
                for task in consumers_copy:
                    self.notify_task_of_reference(task, ref_table_entry)
                
        except KeyError:
            ref_table_entry = ReferenceTableEntry(reference, producing_task)
            self.references[reference.id] = ref_table_entry
        return ref_table_entry
    
    def subscribe(self, id, consumer):
        """
        Adds a consumer for the given ID. Typically, this is used to monitor
        job completion (by adding a synthetic task).
        """
        try:
            ref_table_entry = self.get_reference_info(id)
            if ref_table_entry.ref.is_consumable():
                consumer.notify_ref_table_updated(ref_table_entry)
        except KeyError:
            reference = SW2_FutureReference(id)
            ref_table_entry = ReferenceTableEntry(reference, None)
            self.references[reference.id] = ref_table_entry
            
        ref_table_entry.add_consumer(consumer)
            
    
    
    def notify_task_of_reference(self, task, ref_table_entry):
        if ref_table_entry.ref.is_consumable():
            was_queued_streaming = task.is_queued_streaming()
            was_blocked = task.is_blocked()
            task.notify_ref_table_updated(ref_table_entry)
            if was_blocked and not task.is_blocked():
                self.task_runnable(task)
            elif was_queued_streaming and not task.is_queued_streaming():
                # Submit this to the scheduler again
                self.task_runnable(task)
    
    def reduce_graph_for_references(self, ref_ids):
    
        root_tasks = []
    
        # Initially, start with the root set of tasks, based on the desired
        # object IDs.
        for ref_id in ref_ids:
            task = self.get_reference_info(ref_id).producing_task
            if task.state == TASK_CREATED:
                # Task has not yet been scheduled, so add it to the queue.
                task.set_state(TASK_BLOCKING)
                root_tasks.append(task)

        self.reduce_graph_for_tasks(root_tasks)
    
    def reduce_graph_for_tasks(self, root_tasks):
        
        newly_active_task_queue = collections.deque()
            
        for task in root_tasks:
            newly_active_task_queue.append(task)
                
        # Do breadth-first search through the task graph to identify other 
        # tasks to make active. We use task.state == TASK_BLOCKING as a marker
        # to prevent visiting a task more than once.
        while len(newly_active_task_queue) > 0:
            
            task = newly_active_task_queue.popleft()
            
            # Identify the other tasks that need to run to make this task
            # runnable.
            task_will_block = False
            for local_id, ref in task.dependencies.items():

                try:
                    ref_table_entry = self.get_reference_info(ref.id)
                    ref_table_entry.combine_references(ref)
                except KeyError:
                    ref_table_entry = ReferenceTableEntry(ref, None)
                    self.references[ref.id] = ref_table_entry

                if ref_table_entry.ref.is_consumable():
                    conc_ref = ref_table_entry.ref
                    task.inputs[local_id] = conc_ref
                    if isinstance(conc_ref, SW2_StreamReference):
                        task.unfinished_input_streams.add(ref.id)
                        ref_table_entry.add_consumer(task)

                else:
                    
                    # The reference is a future that has not yet been produced,
                    # so subscribe to the reference and block the task.
                    ref_table_entry.add_consumer(task)
                    task_will_block = True
                    task.block_on(ref.id, local_id)
                    
                    # We may need to recursively check the inputs on the
                    # producing task for this reference.
                    producing_task = ref_table_entry.producing_task
                    if producing_task is not None:
                        # The producing task is inactive, so recursively visit it.                    
                        if producing_task.state in (TASK_CREATED, TASK_COMMITTED):
                            producing_task.set_state(TASK_BLOCKING)
                            newly_active_task_queue.append(producing_task)
            
            # If all inputs are available, we can now run this task. Otherwise,
            # it will run when its inputs are published.
            if not task_will_block:
                task.set_state(TASK_RUNNABLE)
                self.task_runnable(task)
    
    def task_runnable(self, task):
        """
        Called when a task becomes runnable. Subclasses should provide their
        own implementation of this function.
        """
        raise NotImplementedError()
    
    def get_task(self, task_id):
        return self.tasks[task_id]
    
    def get_reference_info(self, ref_id):
        return self.references[ref_id]

########NEW FILE########
__FILENAME__ = tcp_data_fetch
# Copyright (c) 2010--11 Chris Smowton <Chris.Smowton@cl.cam.ac.uk>
#
# Permission to use, copy, modify, and distribute this software for any
# purpose with or without fee is hereby granted, provided that the above
# copyright notice and this permission notice appear in all copies.
#
# THE SOFTWARE IS PROVIDED "AS IS" AND THE AUTHOR DISCLAIMS ALL WARRANTIES
# WITH REGARD TO THIS SOFTWARE INCLUDING ALL IMPLIED WARRANTIES OF
# MERCHANTABILITY AND FITNESS. IN NO EVENT SHALL THE AUTHOR BE LIABLE FOR
# ANY SPECIAL, DIRECT, INDIRECT, OR CONSEQUENTIAL DAMAGES OR ANY DAMAGES
# WHATSOEVER RESULTING FROM LOSS OF USE, DATA OR PROFITS, WHETHER IN AN
# ACTION OF CONTRACT, NEGLIGENCE OR OTHER TORTIOUS ACTION, ARISING OUT OF
# OR IN CONNECTION WITH THE USE OR PERFORMANCE OF THIS SOFTWARE.

from ciel.public.references import SW2_SocketStreamReference
from ciel.runtime.remote_stat import subscribe_remote_output_nopost, unsubscribe_remote_output_nopost
from ciel.runtime.block_store import get_own_netloc
import threading
import ciel
import logging
import socket
import os

class TcpTransferContext:
    
    def __init__(self, ref, chunk_size, fetch_ctx):
        self.ref = ref
        assert isinstance(ref, SW2_SocketStreamReference)
        self.otherend_hostname = self.ref.socket_netloc.split(":")[0]
        self.chunk_size = chunk_size
        self.fetch_ctx = fetch_ctx
        self.thread = threading.Thread(target=self.thread_main)
        self.lock = threading.Lock()
        self.done = False
        self.should_close = False

    def start(self):
        ciel.log("Stream-fetch %s: trying TCP (%s:%s)" % (self.ref.id, self.otherend_hostname, self.ref.socket_port), "TCP_FETCH", logging.DEBUG)
        self.thread.start()

    def thread_main(self):
        try:
            with self.lock:
                self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                self.should_close = True            
            ciel.log("Connecting %s:%s" % (self.otherend_hostname, self.ref.socket_port), "TCP_FETCH", logging.DEBUG)
            subscribe_remote_output_nopost(self.ref.id, self)
            self.sock.connect((self.otherend_hostname, self.ref.socket_port))
            self.sock.sendall("%s %s %d\n" % (self.ref.id, get_own_netloc(), self.chunk_size))
            ciel.log("%s:%s connected: requesting %s (chunk size %d)" % (self.otherend_hostname, self.ref.socket_port, self.ref.id, self.chunk_size), "TCP_FETCH", logging.DEBUG)
            fp = self.sock.makefile("r", bufsize=0)
            response = fp.readline().strip()
            fp.close()
            with self.lock:
                self.should_close = False
                if response.find("GO") != -1:
                    ciel.log("TCP-fetch %s: transfer started" % self.ref.id, "TCP_FETCH", logging.DEBUG)
                    new_fd = os.dup(self.sock.fileno())
                    self.sock.close()
                    self.fetch_ctx.set_fd(new_fd, True)
                else:
                    ciel.log("TCP-fetch %s: request failed: other end said '%s'" % (self.ref.id, response), "TCP_FETCH", logging.WARNING)
                    unsubscribe_remote_output_nopost(self.ref.id)
                    self.done = True
                    self.sock.close()
                    self.fetch_ctx.result(False)
        except Exception as e:
            unsubscribe_remote_output_nopost(self.ref.id)
            ciel.log("TCP-fetch %s: failed due to exception %s" % (self.ref.id, repr(e)), "TCP_FETCH", logging.ERROR)
            with self.lock:
                if self.should_close:
                    self.sock.close()
                self.done = True
                self.should_close = False
            self.fetch_ctx.result(False)

    def unsubscribe(self, fetcher):
        should_callback = False
        with self.lock:
            if self.done:
                return
            else:
                if self.should_close:
                    self.sock.close()
                self.done = True
                should_callback = True
                unsubscribe_remote_output_nopost(self.ref.id)
        if should_callback:
            self.fetch_ctx.result(False)

    def advertisment(self, bytes=None, done=None, absent=None, failed=None):
        if not self.done:
            self.done = True
            if failed is True:
                ciel.log("TCP-fetch %s: remote reported failure" % self.ref.id, "TCP_FETCH", logging.ERROR)
                self.fetch_ctx.result(False)
            elif done is True:
                ciel.log("TCP-fetch %s: remote reported success (%d bytes)" % (self.ref.id, bytes), "TCP_FETCH", logging.DEBUG)
                self.fetch_ctx.result(True)
            else:
                ciel.log("TCP-fetch %s: weird advertisment (%s, %s, %s, %s)" % (bytes, done, absent, failed), "TCP_FETCH", logging.ERROR)
                self.fetch_ctx.result(False)
        else:
            ciel.log("TCP-fetch %s: ignored advertisment as transfer is done" % self.ref.id, "TCP_FETCH", logging.WARNING)

########NEW FILE########
__FILENAME__ = tcp_server
# Copyright (c) 2010--11 Chris Smowton <Chris.Smowton@cl.cam.ac.uk>
#
# Permission to use, copy, modify, and distribute this software for any
# purpose with or without fee is hereby granted, provided that the above
# copyright notice and this permission notice appear in all copies.
#
# THE SOFTWARE IS PROVIDED "AS IS" AND THE AUTHOR DISCLAIMS ALL WARRANTIES
# WITH REGARD TO THIS SOFTWARE INCLUDING ALL IMPLIED WARRANTIES OF
# MERCHANTABILITY AND FITNESS. IN NO EVENT SHALL THE AUTHOR BE LIABLE FOR
# ANY SPECIAL, DIRECT, INDIRECT, OR CONSEQUENTIAL DAMAGES OR ANY DAMAGES
# WHATSOEVER RESULTING FROM LOSS OF USE, DATA OR PROFITS, WHETHER IN AN
# ACTION OF CONTRACT, NEGLIGENCE OR OTHER TORTIOUS ACTION, ARISING OUT OF
# OR IN CONNECTION WITH THE USE OR PERFORMANCE OF THIS SOFTWARE.

import ciel.runtime.pycurl_thread
import ciel.runtime.producer
from ciel.runtime.block_store import producer_filename

import threading
import socket
import ciel
import logging
import os

# This is a lot like the AsyncPushThread in executors.py.
# TODO after paper rush is over: get the spaghettificiation of the streaming code under control

class SocketPusher:
        
    def __init__(self, sock):
        self.sock_obj = sock
        self.write_fd = None
        self.bytes_available = 0
        self.bytes_copied = 0
        self.fetch_done = False
        self.pause_threshold = None
        self.lock = threading.Lock()
        self.cond = threading.Condition(self.lock)
        self.thread = threading.Thread(target=self.thread_main)
        
    def result(self, success):
        if not success:
            raise Exception("No way to signal failure to TCP consumers yet!")
        with self.lock:
            self.fetch_done = True
            self.cond.notify_all()

    def progress(self, n_bytes):
        with self.lock:
            self.bytes_available = n_bytes
            if self.pause_threshold is not None and self.bytes_available >= self.pause_threshold:
                self.cond.notify_all()

    def start(self):
        self.thread.start()

    def socket_init(self):
        self.sock_obj.setblocking(True)
        sock_file = self.sock_obj.makefile("r", bufsize=0)
        bits = sock_file.readline().strip().split()
        self.refid = bits[0]
        self.remote_netloc = bits[1]
        self.chunk_size = int(bits[2])
        sock_file.close()
        producer = ciel.runtime.producer.get_producer_for_id(self.refid)
        if producer is None:
            ciel.log("Got auxiliary TCP connection for bad output %s" % self.refid, "TCP_FETCH", logging.WARNING)
            self.sock_obj.sendall("FAIL\n")
            self.sock_obj.close()
            return None
        else:
            self.sock_obj.sendall("GO\n")
            self.write_fd = os.dup(self.sock_obj.fileno())
            return producer.subscribe(self, try_direct=True, consumer_fd=self.write_fd)

    def thread_main(self):
        try:
            fd_taken = self.socket_init()
            if fd_taken is None:
                return
            elif fd_taken is True:
                ciel.log("Incoming TCP connection for %s connected directly to producer" % self.refid, "TCP_SERVER", logging.DEBUG)
                self.sock_obj.close()
                return
            # Otherwise we'll get progress/result callbacks as we follow the producer's on-disk file.
            os.close(self.write_fd)
            self.read_filename = producer_filename(self.refid)
            ciel.log("Auxiliary TCP connection for output %s (chunk %s) attached via push thread" % (self.refid, self.chunk_size), "TCP_FETCH", logging.DEBUG)

            with open(self.read_filename, "r") as input_fp:
                while True:
                    while True:
                        buf = input_fp.read(4096)
                        self.sock_obj.sendall(buf)
                        self.bytes_copied += len(buf)
                        with self.lock:
                            if self.bytes_copied == self.bytes_available and self.fetch_done:
                                ciel.log("Socket-push for %s complete: wrote %d bytes" % (self.refid, self.bytes_copied), "TCP_SERVER", logging.DEBUG)
                                self.sock_obj.close()
                                return
                            if len(buf) < self.chunk_size:
                                # EOF, for now.
                                break
                    with self.lock:
                        self.pause_threshold = self.bytes_copied + self.chunk_size
                        while self.bytes_available < self.pause_threshold and not self.fetch_done:
                            self.cond.wait()
                        self.pause_threshold = None

        except Exception as e:
            ciel.log("Socket-push-thread died with exception %s" % repr(e), "TCP_FETCH", logging.ERROR)
            try:
                self.sock_obj.close()
            except:
                pass

    def start_direct_write(self):
        # Callback indicating the producer is about to take our socket
        self.sock_obj.sendall("GO\n")

def new_aux_connection(new_sock):
    try:
        handler = SocketPusher(new_sock)
        handler.start()
    except Exception as e:
        ciel.log("Error handling auxiliary TCP connection: %s" % repr(e), "TCP_FETCH", logging.ERROR)
        try:
            new_sock.close()
        except:
            pass

class TcpServer:

    def __init__(self, port):
        self.aux_port = port
        ciel.log("Listening for auxiliary connections on port %d" % port, "TCP_FETCH", logging.DEBUG)
        self.aux_listen_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.aux_listen_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.aux_listen_socket.bind(("0.0.0.0", port))
        self.aux_listen_socket.listen(5)
        self.aux_listen_socket.setblocking(False)

    def get_select_fds(self):
        return [self.aux_listen_socket.fileno()], [], []

    def notify_fds(self, read_fds, write_fds, exn_fds):
        if self.aux_listen_socket.fileno() in read_fds:
            (new_sock, _) = self.aux_listen_socket.accept()
            new_aux_connection(new_sock)

aux_listen_port = None

def create_tcp_server(port):
    global aux_listen_port
    aux_listen_port = port
    ciel.runtime.pycurl_thread.add_event_source(TcpServer(port))

def tcp_server_active():
    return aux_listen_port is not None

########NEW FILE########
__FILENAME__ = attach
# Copyright (c) 2011 Derek Murray <Derek.Murray@cl.cam.ac.uk>
#
# Permission to use, copy, modify, and distribute this software for any
# purpose with or without fee is hereby granted, provided that the above
# copyright notice and this permission notice appear in all copies.
#
# THE SOFTWARE IS PROVIDED "AS IS" AND THE AUTHOR DISCLAIMS ALL WARRANTIES
# WITH REGARD TO THIS SOFTWARE INCLUDING ALL IMPLIED WARRANTIES OF
# MERCHANTABILITY AND FITNESS. IN NO EVENT SHALL THE AUTHOR BE LIABLE FOR
# ANY SPECIAL, DIRECT, INDIRECT, OR CONSEQUENTIAL DAMAGES OR ANY DAMAGES
# WHATSOEVER RESULTING FROM LOSS OF USE, DATA OR PROFITS, WHETHER IN AN
# ACTION OF CONTRACT, NEGLIGENCE OR OTHER TORTIOUS ACTION, ARISING OUT OF
# OR IN CONNECTION WITH THE USE OR PERFORMANCE OF THIS SOFTWARE.
import optparse
import sys
import httplib2
import simplejson
import urlparse
import os

PROTOCOLS = {'json' : True, 'protobuf' : True, 'pickle' : True, 'line' : True}
FORMATS = {'json' : True, 'env' : True, 'protobuf' : True, 'pickle' : True}

def attach(worker_uri, pid, protocol='json'):
    
    h = httplib2.Http()
    process_request = simplejson.dumps((pid, protocol))
    try:
        response, content = h.request(urlparse.urljoin(worker_uri, '/control/process/'), 'POST', process_request)
    except:
        print >>sys.stderr, "Error: couldn't contact worker"
        return None

    if response['status'] != '200':
        print >>sys.stderr, "Error: non-OK status from worker (%s)" % response['status']
        return None

    else:
        return simplejson.loads(content)

def render(descriptor, format='json'):

    if format == 'json':
        print simplejson.dumps(descriptor)
    elif format == 'env':
        print 'export CIEL_PROCESS_ID=%s' % descriptor['id']
        print 'export CIEL_PROCESS_PROTOCOL=%s' % descriptor['protocol']
        print 'export CIEL_PIPE_TO_WORKER=%s' % descriptor['to_worker_fifo']
        print 'export CIEL_PIPE_FROM_WORKER=%s' % descriptor['from_worker_fifo']
        
    else:
        print >>sys.stderr, 'Format not yet supported: %s' % format
        raise


def main():
    parser = optparse.OptionParser(usage='sw-attach [options] -P PID')
    parser.add_option("-w", "--worker", action="store", dest="worker", help="Worker URI", metavar="WORKER", default='http://localhost:8001/')
    parser.add_option("-P", "--pid", action="store", dest="pid", help="Process ID", metavar="PID", type="int", default=os.getppid())
    parser.add_option("-p", "--protocol", action="store", dest="protocol", help="IPC protocol to use. Valid protocols are json (default), protobuf or pickle", default='json')
    parser.add_option("-F", "--format", action="store", dest="format", help="Format to write out umbilical details. Valid formats are json (default), env, protobuf or pickle", default='json')
    (options, _) = parser.parse_args()

    should_exit = False
    if options.protocol not in PROTOCOLS.keys():
        print >>sys.stderr, "Error: must specify a valid protocol"
        should_exit = True
        
    if options.format not in FORMATS.keys():
        print >>sys.stderr, "Error: must specify a valid format"
        should_exit = True

    if options.pid is None:
        print >>sys.stderr, "Error: must specify a process ID"
        should_exit = True
        
    if should_exit:
        parser.print_help()
        sys.exit(-1)
    else:
        descriptor = attach(options.worker, options.pid, options.protocol)
        if descriptor is None:
            parser.print_help()
            sys.exit(-1)
        else:
            render(descriptor, options.format)
            sys.exit(0)
        
if __name__ == '__main__':
    main()
########NEW FILE########
__FILENAME__ = cat
# Copyright (c) 2010 Chris Smowton <chris.smowton@cl.cam.ac.uk>
# Copyright (c) 2010 Derek Murray <Derek.Murray@cl.cam.ac.uk>
#
# Permission to use, copy, modify, and distribute this software for any
# purpose with or without fee is hereby granted, provided that the above
# copyright notice and this permission notice appear in all copies.
#
# THE SOFTWARE IS PROVIDED "AS IS" AND THE AUTHOR DISCLAIMS ALL WARRANTIES
# WITH REGARD TO THIS SOFTWARE INCLUDING ALL IMPLIED WARRANTIES OF
# MERCHANTABILITY AND FITNESS. IN NO EVENT SHALL THE AUTHOR BE LIABLE FOR
# ANY SPECIAL, DIRECT, INDIRECT, OR CONSEQUENTIAL DAMAGES OR ANY DAMAGES
# WHATSOEVER RESULTING FROM LOSS OF USE, DATA OR PROFITS, WHETHER IN AN
# ACTION OF CONTRACT, NEGLIGENCE OR OTHER TORTIOUS ACTION, ARISING OUT OF
# OR IN CONNECTION WITH THE USE OR PERFORMANCE OF THIS SOFTWARE.
from optparse import OptionParser
from ciel.runtime.object_cache import retrieve_object_for_ref
from ciel.public.references import SWReferenceJSONEncoder,\
    json_decode_object_hook
import sys
import os
import simplejson
import httplib2
from urlparse import urljoin
from ciel.public.references import SWURLReference

def main():
    parser = OptionParser()
    parser.add_option("-m", "--master", action="store", dest="master", help="Master URI", metavar="MASTER", default=os.getenv("SW_MASTER"))
    parser.add_option("-r", "--refs", action="store_true", dest="refs", help="Set this option to look up reference names in the master", default=False)
    parser.add_option("-j", "--json", action="store_true", dest="json", help="Set this option to use JSON pretty printing", default=False)
    (options, args) = parser.parse_args()
    
    if options.refs:
        ref_ids = args
        
        for ref_id in ref_ids:
            
            # Fetch information about the ref from the master.
            h = httplib2.Http()
            _, content = h.request(urljoin(options.master, '/refs/%s' % ref_id), 'GET')
            ref_info = simplejson.loads(content, object_hook=json_decode_object_hook)
            ref = ref_info['ref']
            
            if options.json:
                obj = retrieve_object_for_ref(ref, 'json', None)
                simplejson.dump(obj, sys.stdout, cls=SWReferenceJSONEncoder, indent=4)
                print
            else:
                fh = retrieve_object_for_ref(ref, 'handle', None)
                for line in fh:
                    sys.stdout.write(line)
                fh.close()
            
    else:
        urls = args    
        
        for url in urls:
            if options.json:
                obj = retrieve_object_for_ref(SWURLReference([url]), 'json', None)
                simplejson.dump(obj, sys.stdout, cls=SWReferenceJSONEncoder, indent=4)
                print
            else:
                fh = retrieve_object_for_ref(SWURLReference([url]), 'handle', None)
                print fh
                for line in fh:
                    sys.stdout.write(line)
                fh.close()
        
if __name__ == '__main__':
    main()

########NEW FILE########
__FILENAME__ = flush_workers
# Copyright (c) 2010 Derek Murray <Derek.Murray@cl.cam.ac.uk>
#
# Permission to use, copy, modify, and distribute this software for any
# purpose with or without fee is hereby granted, provided that the above
# copyright notice and this permission notice appear in all copies.
#
# THE SOFTWARE IS PROVIDED "AS IS" AND THE AUTHOR DISCLAIMS ALL WARRANTIES
# WITH REGARD TO THIS SOFTWARE INCLUDING ALL IMPLIED WARRANTIES OF
# MERCHANTABILITY AND FITNESS. IN NO EVENT SHALL THE AUTHOR BE LIABLE FOR
# ANY SPECIAL, DIRECT, INDIRECT, OR CONSEQUENTIAL DAMAGES OR ANY DAMAGES
# WHATSOEVER RESULTING FROM LOSS OF USE, DATA OR PROFITS, WHETHER IN AN
# ACTION OF CONTRACT, NEGLIGENCE OR OTHER TORTIOUS ACTION, ARISING OUT OF
# OR IN CONNECTION WITH THE USE OR PERFORMANCE OF THIS SOFTWARE.
from optparse import OptionParser
from ciel.runtime.util.load import get_worker_netlocs
import httplib2
import os
import sys

def main():
    
    parser = OptionParser()
    parser.add_option("-m", "--master", action="store", dest="master", help="Master URI", metavar="MASTER", default=os.getenv("SW_MASTER"))
    parser.add_option("-f", "--force", action="store_true", dest="force", help="Set this flag to really flush the blocks", default=False)
    (options, _) = parser.parse_args()

    h = httplib2.Http()

    workers = get_worker_netlocs(options.master)
    
    for netloc in workers:
        if options.force:
            response, content = h.request('http://%s/control/admin/flush/really' % (netloc), 'POST', 'flush')
            assert response.status == 200
            print >>sys.stderr, 'Flushed worker: %s' % netloc
        else:
            response, content = h.request('http://%s/control/admin/flush/' % (netloc), 'POST', 'flush')
            assert response.status == 200
            print >>sys.stderr, 'Worker: %s' % netloc
        print '---', content
              
if __name__ == '__main__':
    main()

########NEW FILE########
__FILENAME__ = load
# Copyright (c) 2010 Derek Murray <derek.murray@cl.cam.ac.uk>
#
# Permission to use, copy, modify, and distribute this software for any
# purpose with or without fee is hereby granted, provided that the above
# copyright notice and this permission notice appear in all copies.
#
# THE SOFTWARE IS PROVIDED "AS IS" AND THE AUTHOR DISCLAIMS ALL WARRANTIES
# WITH REGARD TO THIS SOFTWARE INCLUDING ALL IMPLIED WARRANTIES OF
# MERCHANTABILITY AND FITNESS. IN NO EVENT SHALL THE AUTHOR BE LIABLE FOR
# ANY SPECIAL, DIRECT, INDIRECT, OR CONSEQUENTIAL DAMAGES OR ANY DAMAGES
# WHATSOEVER RESULTING FROM LOSS OF USE, DATA OR PROFITS, WHETHER IN AN
# ACTION OF CONTRACT, NEGLIGENCE OR OTHER TORTIOUS ACTION, ARISING OUT OF
# OR IN CONNECTION WITH THE USE OR PERFORMANCE OF THIS SOFTWARE.
from optparse import OptionParser
import os
import httplib2
import urlparse
import simplejson
import math
import random
import uuid
from ciel.public.references import SW2_ConcreteReference, SW2_FetchReference, SWReferenceJSONEncoder
import sys
import time
import itertools

def get_worker_netlocs(master_uri):
    http = httplib2.Http()
    response, content = http.request(urlparse.urljoin(master_uri, 'control/worker/', 'GET'))
    if response.status != 200:
        raise Exception("Error: Could not contact master")
    workers = simplejson.loads(content)
    netlocs = []
    for worker in workers:#
        if not worker['failed']:
            netlocs.append(worker['netloc'])
    return netlocs
    
def build_extent_list(filename, size, count, delimiter):

    extents = []
    
    try:
        file_size = os.path.getsize(filename)
    except:
        raise Exception("Could not get the size of the input file.")
    
    if size is not None:
        # Divide the input file into a variable number of fixed sized chunks.
        if delimiter is not None:
            # Use the delimiter, and the size is an upper bound.
            with open(filename, 'rb') as f:
                start = 0
                while start < file_size:
                    finish = min(start + size, file_size)
                    curr = None
                    if finish == file_size:
                        # This is the last block, so take everything up to the
                        # end of the file.
                        extents.append((start, file_size))
                    else:
                        # First try seeking from the approximate finish point backwards
                        # until we see a delimiter.
                        while finish > start: 
                            f.seek(finish)
                            curr = f.read(1)
                            if curr == delimiter:
                                finish += 1
                                break
                            finish -= 1
                            
                        if curr != delimiter:
                            # Need to seek forward.
                            finish = min(file_size, start + size + 1)
                            f.seek(finish)
                            while finish < file_size:
                                curr = f.read(1)
                                finish += 1              
                                if curr == delimiter:
                                    break
              
                            
                        extents.append((start, finish))
                        start = finish 
        else:
            # Chunks are a fixed number of bytes.    
            for start in range(0, file_size, size):
                extents.append((start, min(file_size, start + size)))
        
    elif count is not None:
        # Divide the input file into a fixed number of equal-sized chunks.
        if delimiter is not None:
            # Use the delimiter to divide chunks.
            chunk_size = int(math.ceil(file_size / float(count)))
            with open(filename, 'rb') as f:
                start = 0
                for i in range(0, count - 1):
                    finish = min(start + chunk_size, file_size)
                    curr = None
                    if finish == file_size:
                        # This is the last block, so take everything up to the
                        # end of the file.
                        extents.append((start, file_size))
                    else:
                        # First try seeking from the approximate finish point backwards
                        # until we see a delimiter.
                        while finish > start: 
                            f.seek(finish)
                            curr = f.read(1)
                            if curr == delimiter:
                                finish += 1
                                break
                            finish -= 1
                            
                        if curr != delimiter:
                            # Need to seek forward.
                            finish = min(file_size, start + chunk_size + 1)
                            f.seek(finish)
                            while finish < file_size:
                                curr = f.read(1)
                                finish += 1                            
                                if curr == delimiter:
                                    break
                                
                        extents.append((start, finish))
                        start = finish
                extents.append((start, file_size))

        else:
            # Chunks are an equal number of bytes.
            chunk_size = int(math.ceil(file_size / float(count)))
            for start in range(0, file_size, chunk_size):
                extents.append((start, min(file_size, start + chunk_size)))
    
    return extents
    
def select_targets(netlocs, num_replicas):
    if len(netlocs) < 2:
        return netlocs.keys()
    target_set = set()
    while len(target_set) < num_replicas:
        x, y = random.sample(netlocs, 2)
        if netlocs[x] < netlocs[y]:
            if x not in target_set:
                target_set.add(x)
                netlocs[x] += 1
        else:
            if y not in target_set:
                target_set.add(y)
                netlocs[y] += 1
    return list(target_set)
    
def create_name_prefix(specified_name):
    if specified_name is None:
        specified_name = 'upload:%s' % str(uuid.uuid4())
    return specified_name
    
def make_block_id(name_prefix, block_index):
    return '%s:%s' % (name_prefix, block_index)
    
def upload_extent_to_targets(input_file, block_id, start, finish, targets, packet_size):

    input_file.seek(start)
    
    https = [httplib2.Http() for _ in targets]
        
    for h, target in zip(https, targets):
        h.request('http://%s/control/upload/%s' % (target, block_id), 'POST', 'start')
        
    for packet_start in range(start, finish, packet_size):
        packet = input_file.read(min(packet_size, finish - packet_start))
        for h, target in zip(https, targets):
            h.request('http://%s/control/upload/%s/%d' % (target, block_id, packet_start - start), 'POST', packet)
        
    for h, target in zip(https, targets):
        h.request('http://%s/control/upload/%s/commit' % (target, block_id), 'POST', simplejson.dumps(finish - start))
        h.request('http://%s/control/admin/pin/%s' % (target, block_id), 'POST', 'pin')
        
def upload_string_to_targets(input, block_id, targets):

    https = [httplib2.Http() for _ in targets]
        
    for h, target in zip(https, targets):
        h.request('http://%s/control/upload/%s' % (target, block_id), 'POST', 'start')
        
    for h, target in zip(https, targets):
        h.request('http://%s/control/upload/%s/%d' % (target, block_id, 0), 'POST', input)
        
    for h, target in zip(https, targets):
        h.request('http://%s/control/upload/%s/commit' % (target, block_id), 'POST', simplejson.dumps(len(input)))
        h.request('http://%s/control/admin/pin/%s' % (target, block_id), 'POST', 'pin')

def do_uploads(master, args, size=None, count=1, replication=1, delimiter=None, packet_size=1048576, name=None, do_urls=False, urllist=None, repeat=1):
    
    workers = dict([(w, 0) for w in get_worker_netlocs(master)])
    
    name_prefix = create_name_prefix(name)
    
    output_references = []
    
    # Upload the data in extents.
    if not do_urls:
        
        if len(args) == 1:
            input_filename = args[0] 
            extent_list = build_extent_list(input_filename, size, count, delimiter)
        
            with open(input_filename, 'rb') as input_file:
                for i, (start, finish) in enumerate(extent_list):
                    targets = select_targets(workers, replication)
                    block_name = make_block_id(name_prefix, i)
                    print >>sys.stderr, 'Uploading %s to (%s)' % (block_name, ",".join(targets))
                    upload_extent_to_targets(input_file, block_name, start, finish, targets, packet_size)
                    conc_ref = SW2_ConcreteReference(block_name, finish - start, targets)
                    output_references.append(conc_ref)
                    
        else:
            
            for i, input_filename in enumerate(args):
                with open(input_filename, 'rb') as input_file:
                    targets = select_targets(workers, replication)
                    block_name = make_block_id(name_prefix, i)
                    block_size = os.path.getsize(input_filename)
                    print >>sys.stderr, 'Uploading %s to (%s)' % (input_filename, ",".join(targets))
                    upload_extent_to_targets(input_file, block_name, 0, block_size, targets, packet_size)
                    conc_ref = SW2_ConcreteReference(block_name, block_size, targets)
                    output_references.append(conc_ref)

    else:
        
        if urllist is None:
            urls = []
            for filename in args:
                with open(filename, 'r') as f:
                    for line in f:
                        urls.append(line.strip())
        else:
            urls = urllist
            
        urls = itertools.chain.from_iterable(itertools.repeat(urls, repeat))
            
        #target_fetch_lists = {}
        
        upload_sessions = []
                    
        output_ref_dict = {}
                    
        for i, url in enumerate(urls):
            targets = select_targets(workers, replication)
            block_name = make_block_id(name_prefix, i)
            ref = SW2_FetchReference(block_name, url, i)
            for j, target in enumerate(targets):
                upload_sessions.append((target, ref, j))
            h = httplib2.Http()
            print >>sys.stderr, 'Getting size of %s' % url
            try:
                response, _ = h.request(url, 'HEAD')
                size = int(response['content-length'])
            except:
                print >>sys.stderr, 'Error while getting size of %s; assuming default size (1048576 bytes)' % url
                size = 1048576 
                
            # The refs will be updated as uploads succeed.
            conc_ref = SW2_ConcreteReference(block_name, size)
            output_ref_dict[block_name] = conc_ref
            output_references.append(conc_ref)
        
        while True:

            pending_uploads = {}
            
            failed_this_session = []
            
            for target, ref, index in upload_sessions:
                h2 = httplib2.Http()
                print >>sys.stderr, 'Uploading to %s' % target
                id = uuid.uuid4()
                response, _ = h2.request('http://%s/control/fetch/%s' % (target, id), 'POST', simplejson.dumps([ref], cls=SWReferenceJSONEncoder))
                if response.status != 202:
                    print >>sys.stderr, 'Failed... %s' % target
                    #failed_targets.add(target)
                    failed_this_session.append((ref, index))
                else:
                    pending_uploads[ref, index] = target, id
            
            # Wait until we get a non-try-again response from all of the targets.
            while len(pending_uploads) > 0:
                time.sleep(3)
                for ref, index in list(pending_uploads.keys()):
                    target, id = pending_uploads[ref, index]
                    try:
                        response, _ = h2.request('http://%s/control/fetch/%s' % (target, id), 'GET')
                        if response.status == 408:
                            print >>sys.stderr, 'Continuing to wait for %s:%d on %s' % (ref.id, index, target)
                            continue
                        elif response.status == 200:
                            print >>sys.stderr, 'Succeded! %s:%d on %s' % (ref.id, index, target)
                            output_ref_dict[ref.id].location_hints.add(target)
                            del pending_uploads[ref, index]
                        else:
                            print >>sys.stderr, 'Failed... %s' % target
                            del pending_uploads[ref, index]
                            failed_this_session.append((ref, index))

                    except:
                        print >>sys.stderr, 'Failed... %s' % target
                        del pending_uploads[target]
                        
            if len(pending_uploads) == 0 and len(failed_this_session) == 0:
                break
                        
            # All transfers have finished or failed, so check for failures.
            if len(failed_this_session) > 0:
                
                # We refetch the worker list, in case any have failed in the mean time.
                new_workers = {}
                for w in get_worker_netlocs(master):
                    try:
                        new_workers[w] = workers[w]
                    except KeyError:
                        new_workers[w] = 0
                workers = new_workers
                
                upload_sessions = []
                
                for ref, index in failed_this_session:
                    target, = select_targets(workers, 1)
                    upload_sessions.append((target, ref, index))
                    
    # Upload the index object.
    index = simplejson.dumps(output_references, cls=SWReferenceJSONEncoder)
    block_name = '%s:index' % name_prefix
    
    index_targets = select_targets(workers, replication)
    upload_string_to_targets(index, block_name, index_targets)
    
    index_ref = SW2_ConcreteReference(block_name, len(index), index_targets)
        
    return index_ref

def main():
    parser = OptionParser()
    parser.add_option("-m", "--master", action="store", dest="master", help="Master URI", metavar="MASTER", default=os.getenv("SW_MASTER"))
    parser.add_option("-s", "--size", action="store", dest="size", help="Block size in bytes", metavar="N", type="int", default=None)
    parser.add_option("-n", "--num-blocks", action="store", dest="count", help="Number of blocks", metavar="N", type="int", default=1)
    parser.add_option("-r", "--replication", action="store", dest="replication", help="Copies of each block", type="int", metavar="N", default=1)
    parser.add_option("-d", "--delimiter", action="store", dest="delimiter", help="Block delimiter character", metavar="CHAR", default=None)
    parser.add_option("-l", "--lines", action="store_const", dest="delimiter", const="\n", help="Use newline as block delimiter")
    parser.add_option("-p", "--packet-size", action="store", dest="packet_size", help="Upload packet size in bytes", metavar="N", type="int",default=1048576)
    parser.add_option("-i", "--id", action="store", dest="name", help="Block name prefix", metavar="NAME", default=None)
    parser.add_option("-u", "--urls", action="store_true", dest="urls", help="Treat files as containing lists of URLs", default=False)
    (options, args) = parser.parse_args()
    
    index_ref = do_uploads(options.master, args, options.size, options.count, options.replication, options.delimiter, options.packet_size, options.name, options.urls)

    block_name = index_ref.id
    index_targets = index_ref.location_hints

    for target in index_targets:
        print 'swbs://%s/%s' % (target, block_name)
    
if __name__ == '__main__':
    main()

########NEW FILE########
__FILENAME__ = pin
# Copyright (c) 2010 Derek Murray <Derek.Murray@cl.cam.ac.uk>
#
# Permission to use, copy, modify, and distribute this software for any
# purpose with or without fee is hereby granted, provided that the above
# copyright notice and this permission notice appear in all copies.
#
# THE SOFTWARE IS PROVIDED "AS IS" AND THE AUTHOR DISCLAIMS ALL WARRANTIES
# WITH REGARD TO THIS SOFTWARE INCLUDING ALL IMPLIED WARRANTIES OF
# MERCHANTABILITY AND FITNESS. IN NO EVENT SHALL THE AUTHOR BE LIABLE FOR
# ANY SPECIAL, DIRECT, INDIRECT, OR CONSEQUENTIAL DAMAGES OR ANY DAMAGES
# WHATSOEVER RESULTING FROM LOSS OF USE, DATA OR PROFITS, WHETHER IN AN
# ACTION OF CONTRACT, NEGLIGENCE OR OTHER TORTIOUS ACTION, ARISING OUT OF
# OR IN CONNECTION WITH THE USE OR PERFORMANCE OF THIS SOFTWARE.
from ciel.runtime.block_store import sw_to_external_url,\
    get_netloc_for_sw_url, get_id_for_sw_url
import sys
import httplib2
import simplejson
from ciel.public.references import SW2_ConcreteReference, json_decode_object_hook
from optparse import OptionParser

def main():
    
    parser = OptionParser()
    parser.add_option("-i", "--index", action="store", dest="index", help="Index SWBS URI", metavar="URI", default=None)
    parser.add_option("-b", "--block", action="store", dest="block", help="Block SWBS URI", metavar="URI", default=None)
    (options, _) = parser.parse_args()

    h = httplib2.Http()
    
    if options.block is not None:
        
        netloc = get_netloc_for_sw_url(options.block)
        id = get_id_for_sw_url(options.block)
        
        response, _ = h.request('http://%s/admin/pin/%s' % (netloc, id), 'POST', 'pin')
        assert response.status == 200
        print >>sys.stderr, 'Pinned block %s to %s' % (id, netloc)
        
    if options.index is not None:
    
        index_url = sw_to_external_url(options.index)
        
        _, content = h.request(index_url, 'GET')
        index = simplejson.loads(content, object_hook=json_decode_object_hook)
        
        for chunk in index:
            assert isinstance(chunk, SW2_ConcreteReference)
            for netloc in chunk.location_hints:
                response, _ = h.request('http://%s/admin/pin/%s' % (netloc, chunk.id), 'POST', 'pin')
                assert response.status == 200
                print >>sys.stderr, 'Pinned block %s to %s' % (chunk.id, netloc)
                    
if __name__ == '__main__':
    main()

########NEW FILE########
__FILENAME__ = rebuild_index
# Copyright (c) 2010 Derek Murray <Derek.Murray@cl.cam.ac.uk>
#
# Permission to use, copy, modify, and distribute this software for any
# purpose with or without fee is hereby granted, provided that the above
# copyright notice and this permission notice appear in all copies.
#
# THE SOFTWARE IS PROVIDED "AS IS" AND THE AUTHOR DISCLAIMS ALL WARRANTIES
# WITH REGARD TO THIS SOFTWARE INCLUDING ALL IMPLIED WARRANTIES OF
# MERCHANTABILITY AND FITNESS. IN NO EVENT SHALL THE AUTHOR BE LIABLE FOR
# ANY SPECIAL, DIRECT, INDIRECT, OR CONSEQUENTIAL DAMAGES OR ANY DAMAGES
# WHATSOEVER RESULTING FROM LOSS OF USE, DATA OR PROFITS, WHETHER IN AN
# ACTION OF CONTRACT, NEGLIGENCE OR OTHER TORTIOUS ACTION, ARISING OUT OF
# OR IN CONNECTION WITH THE USE OR PERFORMANCE OF THIS SOFTWARE.
from optparse import OptionParser
from ciel.runtime.util.load import get_worker_netlocs,\
    upload_string_to_targets, select_targets
import httplib2
import os
import sys
import simplejson
from ciel.public.references import SWReferenceJSONEncoder, json_decode_object_hook
import uuid

def main():
    
    parser = OptionParser()
    parser.add_option("-m", "--master", action="store", dest="master", help="Master URI", metavar="MASTER", default=os.getenv("SW_MASTER"))
    parser.add_option("-p", "--prefix", action="store", dest="prefix", help="Block name prefix", metavar="NAME", default=None)
    parser.add_option("-l", "--list", action="store_true", dest="list", help="Lists the pinned blocks in the cluster", default=False)
    parser.add_option("-r", "--replication", action="store", dest="replication", help="Copies of each block", type="int", metavar="N", default=1)
    (options, _) = parser.parse_args()

    if (options.prefix is None and not options.list) or options.master is None:
        parser.usage()
        sys.exit(-1)

    h = httplib2.Http()
    workers = get_worker_netlocs(options.master)

    

    if options.list:
        id_to_netloc = {}
        for netloc in workers:
            response, content = h.request('http://%s/control/admin/pin/' % netloc, 'GET')
            assert response.status == 200
            pin_set = simplejson.loads(content, object_hook=json_decode_object_hook)
            for ref in pin_set:
                try:
                    existing_set = id_to_netloc[ref.id]
                except KeyError:
                    existing_set = set()
                    id_to_netloc[ref.id] = existing_set
                existing_set.add(netloc)
            
        for id in sorted(id_to_netloc.keys()):
            print '%s\t%s' % (id, ", ".join(id_to_netloc[id]))

    else:
    
        id_to_ref = {}
        
        for netloc in workers:
            response, content = h.request('http://%s/control/admin/pin/' % netloc, 'GET')
            assert response.status == 200
            pin_set = simplejson.loads(content, object_hook=json_decode_object_hook)
            for ref in pin_set:
                if ref.id.startswith(options.prefix) and not ref.id.endswith('index'):
                    try:
                        existing_ref = id_to_ref[ref.id]
                        existing_ref.combine_with(ref)
                    except KeyError:
                        id_to_ref[ref.id] = ref
        
        sorted_ids = sorted(id_to_ref.keys())
        new_index = []
        for id in sorted_ids:
            new_index.append(id_to_ref[id])
    
        index_name = '%s:recovered_index' % str(uuid.uuid4())
        with open(index_name, 'w') as f:
            simplejson.dump(new_index, f, cls=SWReferenceJSONEncoder)
        print 'Wrote index to %s' % index_name
    
        targets = select_targets(workers, options.replication)
        upload_string_to_targets(simplejson.dumps(new_index, cls=SWReferenceJSONEncoder), index_name, targets)
        for target in targets:
            print 'swbs://%s/%s' % (target, index_name)
        
        
if __name__ == '__main__':
    main()

########NEW FILE########
__FILENAME__ = run_script
# Copyright (c) 2010 Derek Murray <derek.murray@cl.cam.ac.uk>
#
# Permission to use, copy, modify, and distribute this software for any
# purpose with or without fee is hereby granted, provided that the above
# copyright notice and this permission notice appear in all copies.
#
# THE SOFTWARE IS PROVIDED "AS IS" AND THE AUTHOR DISCLAIMS ALL WARRANTIES
# WITH REGARD TO THIS SOFTWARE INCLUDING ALL IMPLIED WARRANTIES OF
# MERCHANTABILITY AND FITNESS. IN NO EVENT SHALL THE AUTHOR BE LIABLE FOR
# ANY SPECIAL, DIRECT, INDIRECT, OR CONSEQUENTIAL DAMAGES OR ANY DAMAGES
# WHATSOEVER RESULTING FROM LOSS OF USE, DATA OR PROFITS, WHETHER IN AN
# ACTION OF CONTRACT, NEGLIGENCE OR OTHER TORTIOUS ACTION, ARISING OUT OF
# OR IN CONNECTION WITH THE USE OR PERFORMANCE OF THIS SOFTWARE.
from ciel.runtime.exceptions import ErrorReferenceError
from ciel.runtime.object_cache import retrieve_object_for_ref
import ciel.runtime.util.start_job
import time
import datetime
import sys
import os
from optparse import OptionParser

def now_as_timestamp():
    return (lambda t: (time.mktime(t.timetuple()) + t.microsecond / 1e6))(datetime.datetime.now())

def main(my_args=sys.argv):

    parser = OptionParser(usage='Usage: ciel sw [options] SW_SCRIPT [args...]')
    parser.add_option("-m", "--master", action="store", dest="master", help="Master URI", metavar="MASTER", default=ciel.config.get('cluster', 'master', 'http://localhost:8000'))
    parser.add_option("-i", "--id", action="store", dest="id", help="Job ID", metavar="ID", default="default")
    parser.add_option("-e", "--env", action="store_true", dest="send_env", help="Set this flag to send the current environment with the script as _env", default=False)
    parser.add_option("-v", "--verbose", action="store_true", dest="verbose", help="Set this flag to enable verbose output", default=False)
    parser.add_option("-p", "--package-file", action="append", type="string", dest="package_files", help="Specify files to be included as package inputs", metavar="KEY FILENAME", nargs=2, default=[])
    (options, args) = parser.parse_args(my_args)
   
    if not options.master:
        print >> sys.stderr, "Must specify master URI with -m or `ciel config --set cluster.master URI`"
        parser.print_help()
        sys.exit(-1)

    if len(args) != 2:
        print >> sys.stderr, "Must specify one script file to execute, as argument"

        parser.print_help()
        sys.exit(-1)

    script_name = args[1]
    master_uri = options.master
    id = options.id
    
    if options.verbose:
        print id, "STARTED", now_as_timestamp()

    swi_package = {"swimain": {"filename": script_name}}

    for key, filename in options.package_files:
        swi_package[key] = {"filename": filename}
    
    swi_args = {"sw_file_ref": {"__package__": "swimain"}, "start_args": args}
    if options.send_env:
        swi_args["start_env"] = dict(os.environ)
    else:
        swi_args["start_env"] = {}

    new_job = ciel.runtime.util.start_job.submit_job_with_package(swi_package, "swi", swi_args, {}, os.getcwd(), master_uri, args)
    
    result = ciel.runtime.util.start_job.await_job(new_job["job_id"], master_uri)

    try:
        reflist = retrieve_object_for_ref(result, "json", None)
        sw_return = retrieve_object_for_ref(reflist[0], "json", None)
    except ErrorReferenceError, ere:
        print >>sys.stderr, 'Task failed with an error'
        print >>sys.stderr, '%s: "%s"' % (ere.ref.reason, ere.ref.details)
        sys.exit(-2)

    print sw_return
    
if __name__ == '__main__':
    main()

########NEW FILE########
__FILENAME__ = skypy_submit
# Copyright (c) 2010 Christopher Smowton <chris.smowton@cl.cam.ac.uk>
#
# Permission to use, copy, modify, and distribute this software for any
# purpose with or without fee is hereby granted, provided that the above
# copyright notice and this permission notice appear in all copies.
#
# THE SOFTWARE IS PROVIDED "AS IS" AND THE AUTHOR DISCLAIMS ALL WARRANTIES
# WITH REGARD TO THIS SOFTWARE INCLUDING ALL IMPLIED WARRANTIES OF
# MERCHANTABILITY AND FITNESS. IN NO EVENT SHALL THE AUTHOR BE LIABLE FOR
# ANY SPECIAL, DIRECT, INDIRECT, OR CONSEQUENTIAL DAMAGES OR ANY DAMAGES
# WHATSOEVER RESULTING FROM LOSS OF USE, DATA OR PROFITS, WHETHER IN AN
# ACTION OF CONTRACT, NEGLIGENCE OR OTHER TORTIOUS ACTION, ARISING OUT OF
# OR IN CONNECTION WITH THE USE OR PERFORMANCE OF THIS SOFTWARE.

import ciel.runtime.util.start_job
from ciel.runtime.object_cache import retrieve_object_for_ref
import time
import datetime
import sys
import os
from optparse import OptionParser

def now_as_timestamp():
    return (lambda t: (time.mktime(t.timetuple()) + t.microsecond / 1e6))(datetime.datetime.now())

def main():
    parser = OptionParser()
    parser.add_option("-m", "--master", action="store", dest="master", help="Master URI", metavar="MASTER", default=os.getenv("SW_MASTER"))
    parser.add_option("-s", "--skypy-stub", action="store", dest="skypy_stub", help="Path to Skypy stub.py", metavar="PATH", default=None)
    (options, args) = parser.parse_args()
   
    if not options.master:
        parser.print_help()
        print >> sys.stderr, "Must specify master URI with --master"
        sys.exit(1)

    master_uri = options.master
    
    script_name = args[0]
    script_args = args[1:]

    sp_package = {"skypymain": {"filename": script_name}}
    sp_args = {"pyfile_ref": {"__package__": "skypymain"}, "entry_point": "skypy_main", "entry_args": script_args}

    new_job = ciel.runtime.util.start_job.submit_job_with_package(sp_package, "skypy", sp_args, os.getcwd(), master_uri, args)
    
    result = ciel.runtime.util.start_job.await_job(new_job["job_id"], master_uri)

    reflist = retrieve_object_for_ref(result, "json", None)

    return reflist[0]

if __name__ == '__main__':
    main()

########NEW FILE########
__FILENAME__ = start_job
import sys
import simplejson
import load
import urlparse
import httplib2
import pickle
import time
import datetime
import os.path
import glob
import ciel.config
from ciel.runtime.util.sw_pprint import sw_pprint

from ciel.public.references import SWReferenceJSONEncoder,json_decode_object_hook,\
    SW2_FutureReference, SWDataValue, SWErrorReference,\
    SW2_SocketStreamReference, SW2_StreamReference, SW2_ConcreteReference,\
    build_reference_from_tuple
from ciel.runtime.object_cache import retrieve_object_for_ref, decoders
from optparse import OptionParser
from ciel.runtime.block_store import get_fetch_urls_for_ref
from StringIO import StringIO
import sys
from ciel.runtime.executors.init import build_init_descriptor

http = httplib2.Http()

def now_as_timestamp():
    return (lambda t: (time.mktime(t.timetuple()) + t.microsecond / 1e6))(datetime.datetime.now())

def resolve_vars(value, callback_map):
    
    def resolve_vars_val(value):
        if isinstance(value, list):
            return [resolve_vars_val(v) for v in value]
        elif isinstance(value, dict):
            for callback_key in callback_map:
                if callback_key in value:
                    return callback_map[callback_key](value)
            return dict([(resolve_vars_val(k), resolve_vars_val(v)) for (k, v) in value.items()])
        else:
            return value

    return resolve_vars_val(value)

def ref_of_string(val, master_uri):
    master_data_uri = urlparse.urljoin(master_uri, "control/data/")
    master_netloc = urlparse.urlparse(master_uri).netloc
    (_, content) = http.request(master_data_uri, "POST", val)
    return simplejson.loads(content, object_hook=json_decode_object_hook)
    
def ref_of_object(key, val, package_path, master_uri):
    if "__ref__" in val:
        return build_reference_from_tuple(val['__ref__'])
    if "filenamelist" in val:
        
        with open(val["filenamelist"]) as listfile:
            filenamelist = [x.strip() for x in listfile.readlines()]
        
        try:
            replication = val["replication"]
        except KeyError:
            replication = 1
        return load.do_uploads(master_uri, filenamelist, replication=replication)
    if "filename" not in val and "urls" not in val:
        raise Exception("start_job can't handle resources that aren't files yet; package entries must have a 'filename' member")
    if "filename" in val and not os.path.isabs(val["filename"]):
        # Construct absolute path by taking it as relative to package descriptor
        if "cwd" in val and val["cwd"]:
            val["filename"] = os.path.join(os.getcwd(), val["filename"])
        else:
            val["filename"] = os.path.join(package_path, val["filename"])
    if "urlindex" in val and val["urlindex"]:
        try:
            replication = val["replication"]
        except KeyError:
            replication = 3
        try:
            repeat = val["repeat"]
        except KeyError:
            repeat = 1
        if 'urls' in val:
            return load.do_uploads(master_uri, [], urllist=val["urls"], do_urls=True, replication=replication, repeat=repeat)
        else:
            return load.do_uploads(master_uri, [val["filename"]], do_urls=True, replication=replication)
    elif "index" in val and val["index"]:
        return load.do_uploads(master_uri, [val["filename"]])
    else:
        with open(val["filename"], "r") as infile:
            file_data = infile.read()
        return ref_of_string(file_data, master_uri)

def task_descriptor_for_package_and_initial_task(package_dict, start_handler, start_args, package_path, master_uri, args):

    def resolve_arg(value):
        try:
            return args[value["__args__"]]
        except IndexError:
            if "default" in value:
                print >>sys.stderr, "Positional argument", value["__args__"], "not specified; using default", value["default"]
                return value["default"]
            else:
                print >>sys.stderr, "Mandatory argument", value["__args__"], "not specified."
                sys.exit(-1)

    def resolve_env(value):
        try:
            return os.environ[value["__env__"]]
        except KeyError:
            if "default" in value:
                print >>sys.stderr, "Environment variable", value["__env__"], "not specified; using default", value["default"]
                return value["default"]
            else:
                print >>sys.stderr, "Mandatory environment variable", value["__env__"], "not specified."
                sys.exit(-1)

    env_and_args_callbacks = {"__args__": resolve_arg,
                              "__env__": resolve_env}
    package_dict = resolve_vars(package_dict, env_and_args_callbacks)
    start_args = resolve_vars(start_args, env_and_args_callbacks)

    submit_package_dict = dict([(k, ref_of_object(k, v, package_path, master_uri)) for (k, v) in package_dict.items()])
    #for key, ref in submit_package_dict.items():
    #    print >>sys.stderr, key, '-->', simplejson.dumps(ref, cls=SWReferenceJSONEncoder)
    package_ref = ref_of_string(pickle.dumps(submit_package_dict), master_uri)

    resolved_args = resolve_vars(start_args, {"__package__": lambda x: submit_package_dict[x["__package__"]]})

    return build_init_descriptor(start_handler, resolved_args, package_ref, master_uri, ref_of_string)

def submit_job_for_task(task_descriptor, master_uri, job_options={}):
    payload = {"root_task" : task_descriptor, "job_options" : job_options}
    master_task_submit_uri = urlparse.urljoin(master_uri, "control/job/")
    (_, content) = http.request(master_task_submit_uri, "POST", simplejson.dumps(payload, cls=SWReferenceJSONEncoder))
    try:
        return simplejson.loads(content)
    except ValueError:
        print >>sys.stderr, 'Error submitting job'
        print >>sys.stderr, content
        sys.exit(-1)    

def submit_job_with_package(package_dict, start_handler, start_args, job_options, package_path, master_uri, args):
    task_descriptor = task_descriptor_for_package_and_initial_task(package_dict, start_handler, start_args, package_path, master_uri, args)
    return submit_job_for_task(task_descriptor, master_uri, job_options)

def await_job(jobid, master_uri, timeout=None):
    notify_url = urlparse.urljoin(master_uri, "control/job/%s/completion" % jobid)
    if timeout is not None:
        payload = simplejson.dumps({'timeout' : timeout})
    else:
        payload = None
    completion_result = None
    for i in range(5):
        try:
            (_, content) = http.request(notify_url, "GET" if timeout is None else "POST", body=payload)
            completion_result = simplejson.loads(content, object_hook=json_decode_object_hook)
            break
        except:
            print >>sys.stderr, "Decode failed; retrying fetch..."
            pass

    if timeout is not None:
        return completion_result

    if completion_result is not None and "error" in completion_result:
        print >>sys.stderr, "Job failed: %s" % completion_result["error"]
        sys.exit(-1)
    elif completion_result is not None:
        return completion_result["result_ref"]
    else:
        print >>sys.stderr, 'Error receiving result from master'
    
def external_get_real_ref(ref, jobid, master_uri):
    fetch_url = urlparse.urljoin(master_uri, "control/ref/%s/%s" % (jobid, ref.id))
    _, content = httplib2.Http().request(fetch_url)
    real_ref = simplejson.loads(content, object_hook=json_decode_object_hook)
    print >>sys.stderr, "Resolved", ref, "-->", real_ref
    return real_ref 
    
def simple_retrieve_object_for_ref(ref, decoder, jobid, master_uri):
    if isinstance(ref, SWErrorReference):
        raise Exception("Can't decode %s" % ref)
    if isinstance(ref, SW2_FutureReference) or isinstance(ref, SW2_StreamReference) or isinstance(ref, SW2_SocketStreamReference):
        ref = external_get_real_ref(ref, jobid, master_uri)
    if isinstance(ref, SWDataValue):
        return retrieve_object_for_ref(ref, decoder, None)
    elif isinstance(ref, SW2_ConcreteReference):
        urls = get_fetch_urls_for_ref(ref)
        _, content = httplib2.Http().request(urls[0])
        return decoders[decoder](StringIO(content))
    else:
        raise Exception("Don't know how to retrieve a %s" % ref)
    
def recursive_decode(to_decode, template, jobid, master_uri):
    if isinstance(template, dict):
        
        try:
            decode_method = template["__decode_ref__"]
            decoded_value = simple_retrieve_object_for_ref(to_decode, decode_method, jobid, master_uri)
            recurse_template = template.get("value", None)
            if recurse_template is None:
                return decoded_value
            else:
                return recursive_decode(decoded_value, recurse_template, jobid, master_uri)
        except KeyError:
            pass
    
        try:
            concat_list = template["__concat__"]
            try:
                decode_method = template["encoding"]
            except KeyError:
                decode_method = "json"
            print to_decode
            decoded_value = [simple_retrieve_object_for_ref(x, decode_method, jobid, master_uri) for x in to_decode]
            assert isinstance(concat_list, list)
            assert isinstance(decoded_value, list)
            return "".join(recursive_decode(decoded_value, concat_list, jobid, master_uri))
        except KeyError:
            pass
        
        if not isinstance(to_decode, dict):
            raise Exception("%s and %s: Type mismatch" % to_decode, template)
        ret_dict = {}
        for (k, v) in to_decode:
            value_template = template.get(k, None)
            if value_template is None:
                ret_dict[k] = v
            else:
                ret_dict[k] = recursive_decode(v, value_template, jobid, master_uri)
        return ret_dict
    elif isinstance(template, list):
        if len(to_decode) != len(template):
            raise Exception("%s and %s: length mismatch" % to_decode, template)
        result_list = []
        for (elem_decode, elem_template) in zip(to_decode, template):
            if elem_template is None:
                result_list.append(elem_decode)
            else:
                result_list.append(recursive_decode(elem_decode, elem_template, jobid, master_uri))
        return result_list

def jar(my_args=sys.argv):

    parser = OptionParser(usage='Usage: ciel jar [options] JAR_FILE CLASS_NAME [args...]')
    parser.add_option("-m", "--master", action="store", dest="master", help="URI of the cluster master", metavar="MASTER", default=ciel.config.get('cluster', 'master', 'http://localhost:8000'))
    parser.add_option("-j", "--extra-jar", action="append", dest="extra_jars", help="Filename of additional JAR to load", metavar="JAR_FILE", default=[])
    parser.add_option("-P", "--package", action="append", dest="package", help="Additional file to upload", metavar="ID=FILENAME", default=[])
    parser.add_option("-n", "--num-outputs", action="store", dest="num_outputs", help="Number of outputs for root task", type="int", metavar="N", default=1)
    parser.add_option("-L", "--jar-lib", action="store", dest="jar_lib", help="Directory containing CIEL bindings JARs", type="str", metavar="PATH", default=ciel.config.get('java', 'jar_lib'))
 
    (options, args) = parser.parse_args(args=my_args)
    master_uri = options.master

    if master_uri is None or master_uri == "":
        print >>sys.stderr, ("Must specify a master with -m or `ciel config --set cluster.master URL`")
        sys.exit(-1)
    elif len(args) < 2:
        print >>sys.stderr, "Must specify a fully-qualified class to run"
        parser.print_help()
        sys.exit(-1)

    jars = options.extra_jars + [args[1]]

    # Consult the config to see where the standard JARs are installed.
    jar_path = options.jar_lib
    if jar_path is None:
        print >>sys.stderr, "Could not find CIEL bindings. Set the JAR libary path using one of:"
        print >>sys.stderr, "\tciel jar (--jar-lib|-L) PATH ..."
        print >>sys.stderr, "\tciel config --set java.jar_lib PATH"
        sys.exit(-1)

    for jar_file in glob.glob(os.path.join(jar_path, '*.jar')):
        jars = jars + [jar_file]

    class_name = args[2]
    args = args[3:]

    def upload_jar(filename):
        with open(filename, 'r') as infile:
            return ref_of_string(infile.read(), master_uri)
        
    jar_refs = [upload_jar(j) for j in jars]

    package_dict = {}
    for binding in options.package:
        id, filename = binding.split("=", 2)
        with open(filename, 'r') as infile:
            package_dict[id] = ref_of_string(infile.read(), master_uri)

    package_ref = ref_of_string(pickle.dumps(package_dict), master_uri)

    args = {'jar_lib' : jar_refs,
            'class_name' : class_name,
            'args' : args,
            'n_outputs' : options.num_outputs}

    init_descriptor = build_init_descriptor("java2", args, package_ref, master_uri, ref_of_string)

    job_descriptor = submit_job_for_task(init_descriptor, master_uri)

    job_url = urlparse.urljoin(master_uri, "control/browse/job/%s" % job_descriptor['job_id'])

    result = await_job(job_descriptor['job_id'], master_uri)


    try:
        reflist = simple_retrieve_object_for_ref(result, "json", job_descriptor['job_id'], master_uri)
    except:
        print >>sys.stderr, "Error getting list of references as a result."

    try:
        j_return = retrieve_object_for_ref(reflist[0], "json", None)
    except:
        try:
            j_return = retrieve_object_for_ref(reflist[0], "noop", None)
        except:
            print >>sys.stderr, "Error parsing job result."
            sys.exit(-1)

    print j_return

def main(my_args=sys.argv):

    parser = OptionParser(usage='Usage: ciel run [options] PACKAGE_FILE')
    parser.add_option("-m", "--master", action="store", dest="master", help="URI of the cluster master", metavar="MASTER", default=ciel.config.get('cluster', 'master', 'http://localhost:8000'))
    
    (options, args) = parser.parse_args(args=my_args)
    master_uri = options.master

    if master_uri is None or master_uri == "":
        print >>sys.stderr, ("Must specify a master with -m or `ciel config --set cluster.master URL`")
        sys.exit(-1)
    elif len(args) < 1:
        print >>sys.stderr, "Must specify a package file to run"
        parser.print_help()
        sys.exit(-1)
    
    with open(args[-1], "r") as package_file:
        job_dict = simplejson.load(package_file)

    package_dict = job_dict.get("package",{})
    start_dict = job_dict["start"]
    start_handler = start_dict["handler"]
    start_args = start_dict["args"]
    try:
        job_options = job_dict["options"]
    except KeyError:
        job_options = {}
    
    (package_path, _) = os.path.split(args[-1])

    #print "BEFORE_SUBMIT", now_as_timestamp()

    new_job = submit_job_with_package(package_dict, start_handler, start_args, job_options, package_path, master_uri, args[2:])

    #print "SUBMITTED", now_as_timestamp()
    
    job_url = urlparse.urljoin(master_uri, "control/browse/job/%s" % new_job['job_id'])
    #print "JOB_URL", job_url

    result = await_job(new_job['job_id'], master_uri)

    #print "GOT_RESULT", now_as_timestamp()
    
    reflist = simple_retrieve_object_for_ref(result, "json", new_job['job_id'], master_uri)
    
    decode_template = job_dict.get("result", None)
    if decode_template is None:
        return reflist
    else:
        try:
            decoded = recursive_decode(reflist, decode_template, new_job['job_id'], master_uri)
            print decoded
            return decoded
        except Exception as e:
            print "Failed to decode due to exception", repr(e)
            return reflist
        
def submit():
    """Toned-down version of the above for automation purposes."""        
    parser = OptionParser()
    parser.add_option("-m", "--master", action="store", dest="master", help="Master URI", metavar="MASTER", default=ciel.config.get('cluster', 'master', 'http://localhost:8000'))
    
    (options, args) = parser.parse_args()
    master_uri = options.master

    if master_uri is None or master_uri == "":
        print >>sys.stderr, ("Must specify a master with -m or `ciel config --set cluster.master URL`")
        sys.exit(-1)
    
    with open(args[0], "r") as package_file:
        job_dict = simplejson.load(package_file)

    package_dict = job_dict.get("package",{})
    start_dict = job_dict["start"]
    start_handler = start_dict["handler"]
    start_args = start_dict["args"]
    try:
        job_options = job_dict["options"]
    except KeyError:
        job_options = {}
    

    (package_path, _) = os.path.split(args[0])

    new_job = submit_job_with_package(package_dict, start_handler, start_args, job_options, package_path, master_uri, args[1:])
    
    job_browse_url = urlparse.urljoin(master_uri, "control/browse/job/%s" % new_job['job_id'])
    print >>sys.stderr, "Information available at ", job_browse_url

    print new_job['job_id']

def wait():
    """Toned-down version of the above for automation purposes."""        
    parser = OptionParser()
    parser.add_option("-m", "--master", action="store", dest="master", help="Master URI", metavar="MASTER", default=ciel.config.get('cluster', 'master', 'http://localhost:8000'))
    parser.add_option("-t", "--timeout", action="store", dest="timeout", help="Timeout", metavar="DURATION", default=10)
    
    (options, args) = parser.parse_args()

    master_uri = options.master

    if master_uri is None or master_uri == "":
        print >>sys.stderr, ("Must specify a master with -m or `ciel config --set cluster.master URL`")
        sys.exit(-1)

    result = await_job(args[0], master_uri, options.timeout)

    print >>sys.stderr, "Job done?", result

    return result

def result():
    """Toned-down version of the above for automation purposes."""        
    
    parser = OptionParser()
    parser.add_option("-m", "--master", action="store", dest="master", help="Master URI", metavar="MASTER", default=ciel.config.get('cluster', 'master', 'http://localhost:8000'))
    parser.add_option("-t", "--timeout", action="store", dest="timeout", help="Timeout", metavar="DURATION", default=10)
    parser.add_option("-p", "--package", action="store", dest="package", help="Package file (for parsing format)", metavar="FILE", default=None)

    (options, args) = parser.parse_args()

    if len(args) < 1:
        print >>sys.stderr, "Must specify the job ID on the command line"
        sys.exit(-1)

    master_uri = options.master

    if master_uri is None or master_uri == "":
        print >>sys.stderr, ("Must specify a master with -m or `ciel config --set cluster.master URL`")
        sys.exit(-1)

    result = await_job(args[0], master_uri)

    print result

    if not result:
        print >>sys.stderr, "Timed out"
        sys.exit(-2)

    reflist = simple_retrieve_object_for_ref(result, "json", args[0], master_uri)

    if options.package is not None:
        with open(options.package) as f:
            job_dict = simplejson.load(f)
            decode_template = job_dict.get("result", None)
    else:
        return reflist
        
    if decode_template is not None:
        try:
            decoded = recursive_decode(reflist, decode_template, args[0], master_uri)
            return decoded
        except Exception as e:
            print "Failed to decode due to exception", repr(e)
            return reflist
    else:
        return reflist

########NEW FILE########
__FILENAME__ = sw_pprint

from pprint import PrettyPrinter
from ciel.public.references import SWRealReference

class RefPrettyPrinter(PrettyPrinter):

    def format(self, obj, context, maxlevels, level):
        if isinstance(obj, SWRealReference):
            return (str(obj), False, False)
        else:
            return PrettyPrinter.format(self, obj, context, maxlevels, level)

def sw_pprint(obj, **args):

    pprinter = RefPrettyPrinter(**args)
    pprinter.pprint(obj)


########NEW FILE########
__FILENAME__ = task_crawler
# Copyright (c) 2010 Derek Murray <Derek.Murray@cl.cam.ac.uk>
#
# Permission to use, copy, modify, and distribute this software for any
# purpose with or without fee is hereby granted, provided that the above
# copyright notice and this permission notice appear in all copies.
#
# THE SOFTWARE IS PROVIDED "AS IS" AND THE AUTHOR DISCLAIMS ALL WARRANTIES
# WITH REGARD TO THIS SOFTWARE INCLUDING ALL IMPLIED WARRANTIES OF
# MERCHANTABILITY AND FITNESS. IN NO EVENT SHALL THE AUTHOR BE LIABLE FOR
# ANY SPECIAL, DIRECT, INDIRECT, OR CONSEQUENTIAL DAMAGES OR ANY DAMAGES
# WHATSOEVER RESULTING FROM LOSS OF USE, DATA OR PROFITS, WHETHER IN AN
# ACTION OF CONTRACT, NEGLIGENCE OR OTHER TORTIOUS ACTION, ARISING OUT OF
# OR IN CONNECTION WITH THE USE OR PERFORMANCE OF THIS SOFTWARE.

from Queue import Queue, Empty
from ciel.public.references import json_decode_object_hook
from urlparse import urljoin, urlparse
import httplib2
import simplejson
import sys

def sanitise_job_url(root_url):

    h = httplib2.Http()

    # Postel's Law!
    # We expect the URL of a root task; however, we should liberally accept
    # URLs starting with '/control/browse/job/', '/control/job/' and '/control/browse/task/', and URLs missing '/control'.
    url_parts = urlparse(root_url)

    if not url_parts.path.startswith('/control'):
        root_url = urljoin(root_url, '/control' + url_parts.path)
        url_parts = urlparse(root_url)

    if url_parts.path.startswith('/control/browse/'):
        root_url = urljoin(root_url, '/control' + url_parts.path[len('/control/browse'):])
        url_parts = urlparse(root_url)

    if url_parts.path.startswith('/control/job/'):
        job_url = root_url
        _, content = h.request(job_url)
        job_descriptor = simplejson.loads(content)
        root_url = urljoin(root_url, '/control/task/%s/%s' % (job_descriptor['job_id'], job_descriptor['root_task']))
    elif not url_parts.path.startswith('/control/task/'):
        print >>sys.stderr, "Error: must specify task or job URL."
        raise Exception()
        
    return root_url

def task_descriptors_for_job(job_url, sanitise=True):

    h = httplib2.Http()
    q = Queue()
    q.put(sanitise_job_url(job_url) if sanitise else job_url)

    while True:
        try:
            url = q.get(block=False)
        except Empty:
            break
        _, content = h.request(url)
        
        descriptor = simplejson.loads(content, object_hook=json_decode_object_hook)

        for child in descriptor["children"]:
            q.put(urljoin(url, child))
            
        yield descriptor

def main():
    
    root_url = sys.argv[1]
        
    print 'task_id type parent created_at assigned_at committed_at duration num_children num_dependencies num_outputs final_state worker total_bytes_fetched'
    for descriptor in task_descriptors_for_job(root_url):

        try:
            total_bytes_fetched = sum(descriptor["profiling"]["FETCHED"].values())
        except:
            total_bytes_fetched = None

        task_id = descriptor["task_id"]
        parent = descriptor["parent"]

        #try:
        #    worker = descriptor["worker"] 
        #except KeyError:
        #    worker = None

        created_at = None
        assigned_at = None
        committed_at = None

        num_children = len(descriptor["children"])

        num_dependencies = len(descriptor["dependencies"])

        num_outputs = len(descriptor["expected_outputs"])

        type = descriptor["handler"]

        final_state = descriptor["state"]

        worker = None
        duration = None

        for (time, state) in descriptor["history"]:
            #print time, state
            if state == 'CREATED':
                created_at = time
            elif state == 'COMMITTED':
                committed_at = time
                duration = committed_at - assigned_at if (committed_at is not None and assigned_at is not None) else None
                print task_id, type, parent, created_at, assigned_at, committed_at, duration, num_children, num_dependencies, num_outputs, 'COMMITTED', worker, total_bytes_fetched
            elif state == 'FAILED':
                committed_at = time
                duration = committed_at - assigned_at if (committed_at is not None and assigned_at is not None) else None
                print task_id, type, parent, created_at, assigned_at, committed_at, duration, num_children, num_dependencies, num_outputs, 'FAILED', worker, total_bytes_fetched
            else:
                try:
                    if state[0] == 'ASSIGNED':
                        assigned_at = time
                        worker = state[1]
                        assigned_at = time
                        committed_at = None
                        duration = None
                except ValueError:
                    pass

        if committed_at is None:
            print task_id, type, parent, created_at, assigned_at, committed_at, duration, num_children, num_dependencies, num_outputs, final_state, worker, total_bytes_fetched

        
        #print task_id, type, parent, created_at, assigned_at, committed_at, duration, num_children, num_dependencies, num_outputs, final_state, worker, total_bytes_fetched


            
if __name__ == '__main__':
    main()

########NEW FILE########
__FILENAME__ = execution_features
# Copyright (c) 2011 Derek Murray <Derek.Murray@cl.cam.ac.uk>
#
# Permission to use, copy, modify, and distribute this software for any
# purpose with or without fee is hereby granted, provided that the above
# copyright notice and this permission notice appear in all copies.
#
# THE SOFTWARE IS PROVIDED "AS IS" AND THE AUTHOR DISCLAIMS ALL WARRANTIES
# WITH REGARD TO THIS SOFTWARE INCLUDING ALL IMPLIED WARRANTIES OF
# MERCHANTABILITY AND FITNESS. IN NO EVENT SHALL THE AUTHOR BE LIABLE FOR
# ANY SPECIAL, DIRECT, INDIRECT, OR CONSEQUENTIAL DAMAGES OR ANY DAMAGES
# WHATSOEVER RESULTING FROM LOSS OF USE, DATA OR PROFITS, WHETHER IN AN
# ACTION OF CONTRACT, NEGLIGENCE OR OTHER TORTIOUS ACTION, ARISING OUT OF
# OR IN CONNECTION WITH THE USE OR PERFORMANCE OF THIS SOFTWARE.
from ciel.runtime.executors.stdinout import SWStdinoutExecutor
from ciel.runtime.executors.dotnet import DotNetExecutor
from ciel.runtime.executors.environ import EnvironmentExecutor
from ciel.runtime.executors.cso import CExecutor
from ciel.runtime.executors.grab import GrabURLExecutor
from ciel.runtime.executors.sync import SyncExecutor
from ciel.runtime.executors.init import InitExecutor
from ciel.runtime.executors.proc import ProcExecutor
from ciel.runtime.executors.ocaml import OCamlExecutor
from ciel.runtime.executors.haskell import HaskellExecutor
from ciel.runtime.executors.java import JavaExecutor
from ciel.runtime.executors.java2 import Java2Executor
import ciel
import logging
import pkg_resources

class ExecutionFeatures:
    
    def __init__(self):

        self.executors = dict([(x.handler_name, x) for x in [SWStdinoutExecutor, 
                                                             EnvironmentExecutor, DotNetExecutor, 
                                                             CExecutor, GrabURLExecutor, SyncExecutor, InitExecutor,
                                                             OCamlExecutor, HaskellExecutor,
                                                             ProcExecutor, JavaExecutor, Java2Executor]])

        for entrypoint in pkg_resources.iter_entry_points(group="ciel.executor.plugin"):
            classes_function = entrypoint.load()
            plugin_classes = classes_function()
            for plugin_class in plugin_classes:
                ciel.log("Found plugin for %s executor" % plugin_class.handler_name, 'EXEC', logging.INFO)
                self.executors[plugin_class.handler_name] = plugin_class

        self.runnable_executors = dict([(x, self.executors[x]) for x in self.check_executors()])
        # TODO: Implement a class method for this.
        cacheable_executor_names = set(['swi', 'skypy', 'java2'])
        self.process_cacheing_executors = [self.runnable_executors[x] 
                                           for x in cacheable_executor_names & set(self.runnable_executors.keys())]

    def all_features(self):
        return self.executors.keys()

    def check_executors(self):
        ciel.log.error("Checking executors:", "EXEC", logging.INFO)
        retval = []
        for (name, executor) in self.executors.items():
            if executor.can_run():
                ciel.log.error("Executor '%s' can run" % name, "EXEC", logging.INFO)
                retval.append(name)
            else:
                ciel.log.error("Executor '%s' CANNOT run" % name, "EXEC", logging.INFO)
        return retval
    
    def can_run(self, name):
        return name in self.runnable_executors

    def get_executor(self, name, worker):
        try:
            return self.runnable_executors[name](worker)
        except KeyError:
            raise Exception("Executor %s not installed" % name)

    def get_executor_class(self, name):
        try:
            return self.executors[name]
        except KeyError:
            raise Exception("Executor %s not installed" % name)

########NEW FILE########
__FILENAME__ = master_proxy
# Copyright (c) 2010 Derek Murray <derek.murray@cl.cam.ac.uk>
#
# Permission to use, copy, modify, and distribute this software for any
# purpose with or without fee is hereby granted, provided that the above
# copyright notice and this permission notice appear in all copies.
#
# THE SOFTWARE IS PROVIDED "AS IS" AND THE AUTHOR DISCLAIMS ALL WARRANTIES
# WITH REGARD TO THIS SOFTWARE INCLUDING ALL IMPLIED WARRANTIES OF
# MERCHANTABILITY AND FITNESS. IN NO EVENT SHALL THE AUTHOR BE LIABLE FOR
# ANY SPECIAL, DIRECT, INDIRECT, OR CONSEQUENTIAL DAMAGES OR ANY DAMAGES
# WHATSOEVER RESULTING FROM LOSS OF USE, DATA OR PROFITS, WHETHER IN AN
# ACTION OF CONTRACT, NEGLIGENCE OR OTHER TORTIOUS ACTION, ARISING OUT OF
# OR IN CONNECTION WITH THE USE OR PERFORMANCE OF THIS SOFTWARE.
import ciel

'''
Created on 15 Apr 2010

@author: dgm36
'''
from urlparse import urljoin
from ciel.public.references import SWReferenceJSONEncoder
from ciel.runtime.exceptions import MasterNotRespondingException,\
    WorkerShutdownException
import logging
import random
import cherrypy
import socket
import httplib2
from ciel.runtime.pycurl_rpc import post_string, post_string_noreturn, get_string
from threading import Event

import simplejson

def get_worker_netloc():
    return '%s:%d' % (socket.getfqdn(), cherrypy.config.get('server.socket_port'))

class MasterProxy:
    
    def __init__(self, worker, bus, master_url=None):
        self.bus = bus
        self.worker = worker
        self.master_url = master_url
        self.stop_event = Event()

    def subscribe(self):
        # Stopping is high-priority
        self.bus.subscribe("stop", self.handle_shutdown, 10)

    def unsubscribe(self):
        self.bus.unsubscribe("stop", self.handle_shutdown)

    def change_master(self, master_url):
        self.master_url = master_url
        
    def get_master_details(self):
        return {'netloc': self.master_url, 'id':str(self.worker.id)}

    def handle_shutdown(self):
        self.stop_event.set()
    
    def backoff_request(self, url, method, payload=None, need_result=True, callback=None):
        if self.stop_event.is_set():
            return
        try:
            if method == "POST":
                if need_result:
                    content = post_string(url, payload)
                else:
                    if callback is None:
                        callback = self.master_post_result_callback
                    post_string_noreturn(url, payload, result_callback=callback)
                    return
            elif method == "GET":
                content = get_string(url)
            else:
                raise Exception("Invalid method %s" % method)
            return 200, content
        except:
            ciel.log("Error attempting to contact master, aborting", "MSTRPRXY", logging.WARNING, True)
            raise
    
    def _backoff_request(self, url, method, payload=None, num_attempts=1, initial_wait=0, need_result=True, callback=None):
        initial_wait = 5
        for _ in range(0, num_attempts):
            if self.stop_event.is_set():
                break
            try:
                try:
                    if method == "POST":
                        if need_result or num_attempts > 1:
                            content = post_string(url, payload)
                        else:
                            if callback is None:
                                callback = self.master_post_result_callback
                            post_string_noreturn(url, payload, result_callback=callback)
                            return
                    elif method == "GET":
                        content = get_string(url)
                    else:
                        raise Exception("Invalid method %s" % method)
                    return 200, content
                except Exception as e:
                    ciel.log("Backoff-request failed with exception %s; re-raising MasterNotResponding" % e, "MASTER_PROXY", logging.ERROR)
                    raise MasterNotRespondingException()
            except:
                ciel.log.error("Error contacting master", "MSTRPRXY", logging.WARN, True)
            self.stop_event.wait(initial_wait)
            initial_wait += initial_wait * random.uniform(0.5, 1.5)
        ciel.log.error("Given up trying to contact master", "MSTRPRXY", logging.ERROR, True)
        if self.stop_event.is_set():
            raise WorkerShutdownException()
        else:
            raise MasterNotRespondingException()

    def register_as_worker(self):
        message_payload = simplejson.dumps(self.worker.as_descriptor())
        message_url = urljoin(self.master_url, 'control/worker/')
        _, result = self.backoff_request(message_url, 'POST', message_payload)
        self.worker.id = simplejson.loads(result)
    
    def publish_refs(self, job_id, task_id, refs):
        message_payload = simplejson.dumps(refs, cls=SWReferenceJSONEncoder)
        message_url = urljoin(self.master_url, 'control/task/%s/%s/publish' % (job_id, task_id))
        self.backoff_request(message_url, "POST", message_payload, need_result=False)

    def log(self, job_id, task_id, timestamp, message):
        message_payload = simplejson.dumps([timestamp, message], cls=SWReferenceJSONEncoder)
        message_url = urljoin(self.master_url, 'control/task/%s/%s/log' % (job_id, task_id))
        self.backoff_request(message_url, "POST", message_payload, need_result=False)

    def report_tasks(self, job_id, root_task_id, report):
        message_payload = simplejson.dumps({'worker' : self.worker.id, 'report' : report}, cls=SWReferenceJSONEncoder)
        message_url = urljoin(self.master_url, 'control/task/%s/%s/report' % (job_id, root_task_id))
        self.backoff_request(message_url, "POST", message_payload, need_result=False)

    def failed_task(self, job_id, task_id, reason=None, details=None, bindings={}):
        message_payload = simplejson.dumps((reason, details, bindings), cls=SWReferenceJSONEncoder)
        message_url = urljoin(self.master_url, 'control/task/%s/%s/failed' % (job_id, task_id))
        self.backoff_request(message_url, "POST", message_payload, need_result=False)

    def get_public_hostname(self):
        message_url = urljoin(self.master_url, "control/gethostname/")
        _, result = self.backoff_request(message_url, "GET")
        return simplejson.loads(result)

    def ping(self, ping_fail_callback):
        message_url = urljoin(self.master_url, 'control/worker/%s/ping/' % (str(self.worker.id), ))
        self.backoff_request(message_url, "POST", "PING", need_result=False, callback=ping_fail_callback)

    def master_post_result_callback(self, success, url):
        if not success:
            ciel.log("Failed to async-post to %s!" % url, "MASTER_PROXY", logging.ERROR)


########NEW FILE########
__FILENAME__ = multiworker
# Copyright (c) 2011 Derek Murray <Derek.Murray@cl.cam.ac.uk>
#
# Permission to use, copy, modify, and distribute this software for any
# purpose with or without fee is hereby granted, provided that the above
# copyright notice and this permission notice appear in all copies.
#
# THE SOFTWARE IS PROVIDED "AS IS" AND THE AUTHOR DISCLAIMS ALL WARRANTIES
# WITH REGARD TO THIS SOFTWARE INCLUDING ALL IMPLIED WARRANTIES OF
# MERCHANTABILITY AND FITNESS. IN NO EVENT SHALL THE AUTHOR BE LIABLE FOR
# ANY SPECIAL, DIRECT, INDIRECT, OR CONSEQUENTIAL DAMAGES OR ANY DAMAGES
# WHATSOEVER RESULTING FROM LOSS OF USE, DATA OR PROFITS, WHETHER IN AN
# ACTION OF CONTRACT, NEGLIGENCE OR OTHER TORTIOUS ACTION, ARISING OUT OF
# OR IN CONNECTION WITH THE USE OR PERFORMANCE OF THIS SOFTWARE.
from ciel.runtime.exceptions import ReferenceUnavailableException,\
    AbortedException
from ciel.runtime.local_task_graph import LocalTaskGraph, LocalJobOutput
from ciel.runtime.task_executor import TaskExecutionRecord
import Queue
import ciel
import logging
import random
import threading
import math
import time

EWMA_ALPHA = 0.75
INITIAL_TASK_COST = 0.5

class WorkerJob:
    
    def __init__(self, id, worker, tickets=1000000):
        self.id = id
        self.incoming_queues = {}
        self.runnable_queues = {}
        
        for scheduling_class in worker.scheduling_classes.keys():
            self.incoming_queues[scheduling_class] = Queue.Queue()
            self.runnable_queues[scheduling_class] = Queue.Queue()
        
        self.reference_cache = {}
        self.task_graph = LocalTaskGraph(worker.execution_features, runnable_queues=self.runnable_queues)
        self.active_or_queued_tasksets = 0
        self.running_tasks = 0
        self.active_tasksets = {}
        self.tickets = tickets
        self.job_aborted = False
        self._tasksets_lock = threading.Lock()
        self.task_cost = INITIAL_TASK_COST

    def add_taskset(self, taskset):
        with self._tasksets_lock:
            if not self.job_aborted: 
                try:
                    self.incoming_queues[taskset.initial_td['scheduling_class']].put(taskset)
                except KeyError:
                    try:
                        self.incoming_queues['*'].put(taskset)
                    except KeyError:
                        ciel.log('Scheduling class %s not supported on this worker (for taskset %s)' % (taskset.initial_td['scheduling_class'], taskset.initial_td['task_id']), 'WJOB', logging.ERROR)
                        raise
                self.active_or_queued_tasksets += 1
            else:
                raise AbortedException()
        
    def abort_all_active_tasksets(self, id):
        with self._tasksets_lock:
            self.job_aborted = True
            for taskset in self.active_tasksets.values():
                taskset.abort_all_tasks()
            
    def abort_taskset_with_id(self, id):
        try:
            taskset = self.active_tasksets[id]
            taskset.abort_all_tasks()
            # Taskset completion routine will eventually call self.taskset_completed(taskset)
        except KeyError:
            pass
        
    def get_tickets(self):
        return math.ceil(self.tickets * (INITIAL_TASK_COST / self.task_cost))
        
    def taskset_activated(self, taskset):
        with self._tasksets_lock:
            if not self.job_aborted:
                self.active_tasksets[taskset.id] = taskset
            else:
                raise AbortedException()
        
    def taskset_completed(self, taskset):
        with self._tasksets_lock:
            del self.active_tasksets[taskset.id]
            self.active_or_queued_tasksets -= 1
            
    def task_started(self):
        self.running_tasks += 1
        ciel.log('Job %s started a task (now running %d)' % (self.id, self.running_tasks), 'JOB', logging.DEBUG)
        
    def task_finished(self, task, time):
        self.running_tasks -= 1
        self.task_cost = EWMA_ALPHA * time + (1 - EWMA_ALPHA) * self.task_cost
        ciel.log('Job %s finished a task (now running %d, task cost now %f)' % (self.id, self.running_tasks, self.task_cost), 'JOB', logging.DEBUG)

class MultiWorker:
    """FKA JobManager."""
    
    def __init__(self, bus, worker):
        self.worker = worker
        self.jobs = {}
        self.scheduling_classes = worker.scheduling_classes
        self._lock = threading.Lock()
        self.queue_manager = QueueManager(bus, self, worker)
        
        self.thread_pools = {}
        for (scheduling_class, capacity) in worker.scheduling_classes.items():
            self.thread_pools[scheduling_class] = WorkerThreadPool(bus, self.queue_manager, scheduling_class, capacity)
        
    def subscribe(self):
        self.queue_manager.subscribe()
        for thread_pool in self.thread_pools.values():
            thread_pool.subscribe()
    
    def unsubscribe(self):
        self.queue_manager.unsubscribe()
        for thread_pool in self.thread_pools.values():
            thread_pool.unsubscribe()
    
    def num_active_jobs(self):
        return len(self.jobs)
    
    def get_active_jobs(self):
        return self.jobs.values()
    
    def get_job_by_id(self, job_id):
        with self._lock:
            return self.jobs[job_id]
    
    def create_and_queue_taskset(self, task_descriptor):
        with self._lock:
            job_id = task_descriptor['job']
            try:
                job = self.jobs[job_id]
            except:
                job = WorkerJob(job_id, self.worker)
                self.jobs[job_id] = job
                
            taskset = MultiWorkerTaskSetExecutionRecord(task_descriptor, self.worker.block_store, self.worker.master_proxy, self.worker.execution_features, self.worker, job, self)
            job.add_taskset(taskset)

        # XXX: Don't want to do this immediately: instead block until the runqueue gets below a certain length.
        taskset.start()

    def taskset_completed(self, taskset):
        with self._lock:
            taskset.job.taskset_completed(taskset)
            if taskset.job.active_or_queued_tasksets == 0:
                del self.jobs[taskset.job.id]

class MultiWorkerTaskSetExecutionRecord:

    def __init__(self, root_task_descriptor, block_store, master_proxy, execution_features, worker, job, job_manager):
        self.id = root_task_descriptor['task_id']
        self._record_list_lock = threading.Lock()
        self.task_records = []
        self.block_store = worker.block_store
        self.master_proxy = worker.master_proxy
        self.execution_features = worker.execution_features
        self.worker = worker
        self.reference_cache = job.reference_cache
        # XXX: Should possibly combine_with()?
        for ref in root_task_descriptor['inputs']:
            self.reference_cache[ref.id] = ref
        self.initial_td = root_task_descriptor
        self.task_graph = job.task_graph
        
        self._refcount = 0
        
        self.job = job
        self.job_manager = job_manager
        
        self.aborted = False
        
        # LocalJobOutput gets self so that it can notify us when done.
        self.job_output = LocalJobOutput(self.initial_td["expected_outputs"], self)

    def abort_all_tasks(self):
        # This will inhibit the sending of a report, and also the creation of any new task records.
        self.aborted = True

        with self._record_list_lock:
            for record in self.task_records:
                record.abort()
            
    def inc_runnable_count(self):
        self._refcount += 1
        
    def dec_runnable_count(self):
        self._refcount -= 1
        # Note that we only notify when the count comes back down to zero.
        if self._refcount == 0:
            self.notify_completed()

    def start(self):
        ciel.log.error('Starting taskset with %s' % self.initial_td['task_id'], 'TASKEXEC', logging.DEBUG)
        self.job.taskset_activated(self)
        
        self.task_graph.add_root_task_id(self.initial_td['task_id'])
        for ref in self.initial_td['expected_outputs']:
            self.task_graph.subscribe(ref, self.job_output)
        # This pokes the root task into the job's runnable_queue.
        self.task_graph.spawn_and_publish([self.initial_td], self.initial_td["inputs"], taskset=self)
        
        # Notify a sleeping worker thread.
        self.job_manager.queue_manager.notify(self.initial_td['scheduling_class'])

    def notify_completed(self):
        """Called by LocalJobOutput.notify_ref_table_updated() when the taskset is complete."""
        ciel.log.error('Taskset complete', 'TASKEXEC', logging.DEBUG)

        # Release this task set, which may allow the JobManager to delete the job.
        self.job_manager.taskset_completed(self)
        
        if not self.aborted:
            # Send a task report back to the master.
            report_data = []
            for tr in self.task_records:
                if tr.success:
                    report_data.append((tr.task_descriptor['task_id'], tr.success, (tr.spawned_tasks, tr.published_refs, tr.get_profiling())))
                else:
                    ciel.log('Appending failure to report for task %s' % tr.task_descriptor['task_id'], 'TASKEXEC', logging.DEBUG)
                    report_data.append((tr.task_descriptor['task_id'], tr.success, (tr.failure_reason, tr.failure_details, tr.failure_bindings)))
            ciel.stopwatch.stop("worker_task")
            self.master_proxy.report_tasks(self.job.id, self.initial_td['task_id'], report_data)

    def build_task_record(self, task_descriptor):
        """Creates a new TaskExecutionRecord for the given task, and adds it to the journal for this task set."""
        with self._record_list_lock:
            if not self.aborted:
                record = TaskExecutionRecord(task_descriptor, self, self.execution_features, self.block_store, self.master_proxy, self.worker)
                self.task_records.append(record) 
                return record
            else:
                raise AbortedException()

    def retrieve_ref(self, ref):
        if ref.is_consumable():
            return ref
        else:
            try:
                return self.reference_cache[ref.id]
            except KeyError:
                raise ReferenceUnavailableException(ref.id)

    def publish_ref(self, ref):
        self.reference_cache[ref.id] = ref

class QueueManager:
    
    def __init__(self, bus, job_manager, worker):
        self.bus = bus
        self.job_manager = job_manager
        self.worker = worker
        #self._lock = threading.Lock()
        self._cond = {}
        
        self.current_heads = {}
        for scheduling_class in worker.scheduling_classes.keys():
            self.current_heads[scheduling_class] = {}
            self._cond[scheduling_class] = threading.Condition()
            
    def subscribe(self):
        self.bus.subscribe('start', self.start)
        self.bus.subscribe('stop', self.stop, 25)
            
    def unsubscribe(self):
        self.bus.unsubscribe('start', self.start)
        self.bus.unsubscribe('stop', self.stop)

    def start(self):
        self.is_running = True

    def stop(self):
        self.is_running = False
        for cond in self._cond.values():
            with cond:
                cond.notifyAll()
            
    def notify(self, scheduling_class):
        try:
            with self._cond[scheduling_class]:
                #ciel.log('Notifying Qmanager for class %s' % scheduling_class, 'LOTTERY', logging.INFO)
                self._cond[scheduling_class].notify()
        except KeyError:
            try:
                with self._cond['*']:
                    #ciel.log('Notifying Qmanager for class *', 'LOTTERY', logging.INFO)
                    self._cond['*'].notify()
            except:
                assert False
            
    def get_next_task(self, scheduling_class):
        
        current_heads = self.current_heads[scheduling_class]
        
        with self._cond[scheduling_class]:
            
            # Loop until a task has been assigned, or we get terminated. 
            while self.is_running:
                ticket_list = []
                total_tickets = 0
                some_jobs = False
                for job in self.job_manager.get_active_jobs():
                    some_jobs = True
                    try:
                        candidate = current_heads[job]
                    except KeyError:
                        try:
                            candidate = job.runnable_queues[scheduling_class].get_nowait()
                            current_heads[job] = candidate
                        except Queue.Empty:
                            continue
                        
                    job_tickets = job.get_tickets()
                    total_tickets += job_tickets
                    ticket_list.append((job, job_tickets, candidate))
        
                #ciel.log('Total tickets in all runnable jobs is %d' % total_tickets, 'LOTTERY', logging.INFO)
                
                if total_tickets > 0:
                    chosen_ticket = random.randrange(total_tickets)
                    #ciel.log('Chose ticket: %d' % chosen_ticket, 'LOTTERY', logging.INFO)
                    
                    curr_ticket = 0
                    for job, job_tickets, current_head in ticket_list:
                        curr_ticket += job_tickets
                        if curr_ticket > chosen_ticket:
                            #ciel.log('Ticket corresponds to job: %s' % job.id, 'LOTTERY', logging.INFO)
                            # Choose the current head from this job.
                            del current_heads[job]
                            return current_head
                elif some_jobs:
                    continue

                self._cond[scheduling_class].wait()
                
        # If we return None, the consuming thread should terminate.
        return None
            
class WorkerThreadPool:
    
    def __init__(self, bus, queue_manager, scheduling_class, num_threads=1):
        self.bus = bus
        self.queue_manager = queue_manager
        self.scheduling_class = scheduling_class
        self.num_threads = num_threads
        self.is_running = False
        self.threads = []
        
    def subscribe(self):
        self.bus.subscribe('start', self.start)
        # Must run after QueueManager.stop()
        self.bus.subscribe('stop', self.stop ,50)
            
    def unsubscribe(self):
        self.bus.unsubscribe('start', self.start)
        self.bus.unsubscribe('stop', self.stop)
            
    def start(self):
        self.is_running = True
        for _ in range(self.num_threads):
            t = threading.Thread(target=self.thread_main, args=())
            self.threads.append(t)
            t.start()
                
    def stop(self):
        self.is_running = False
        for thread in self.threads:
            thread.join()
        self.threads = []
        
    def thread_main(self):
        while True:
            task = self.queue_manager.get_next_task(self.scheduling_class)
            if task is None:
                return
            else:
                try:
                    self.handle_task(task)
                except Exception:
                    ciel.log.error('Uncaught error handling task in pool: %s' % (self.scheduling_class), 'MULTIWORKER', logging.ERROR, True)
                self.queue_manager.notify(self.scheduling_class)

    def handle_task(self, task):
        next_td = task.as_descriptor()
        next_td["inputs"] = [task.taskset.retrieve_ref(ref) for ref in next_td["dependencies"]]
        try:
            task_record = task.taskset.build_task_record(next_td)
            task_record.task_set.job.task_started()
            try:
                task_record.run()
            except:
                ciel.log.error('Error during executor task execution', 'MWPOOL', logging.ERROR, True)
            execution_time = task_record.finish_time - task_record.start_time
            execution_secs = execution_time.seconds + execution_time.microseconds / 1000000.0
            task_record.task_set.job.task_finished(task, execution_secs)
            if task_record.success:
                task.taskset.task_graph.spawn_and_publish(task_record.spawned_tasks, task_record.published_refs, next_td)
        except AbortedException:
            ciel.log('Task %s was aborted, skipping' % task.task_id, 'MWPOOL', logging.DEBUG)
        task.taskset.dec_runnable_count()
########NEW FILE########
__FILENAME__ = pinger
# Copyright (c) 2010 Derek Murray <derek.murray@cl.cam.ac.uk>
#
# Permission to use, copy, modify, and distribute this software for any
# purpose with or without fee is hereby granted, provided that the above
# copyright notice and this permission notice appear in all copies.
#
# THE SOFTWARE IS PROVIDED "AS IS" AND THE AUTHOR DISCLAIMS ALL WARRANTIES
# WITH REGARD TO THIS SOFTWARE INCLUDING ALL IMPLIED WARRANTIES OF
# MERCHANTABILITY AND FITNESS. IN NO EVENT SHALL THE AUTHOR BE LIABLE FOR
# ANY SPECIAL, DIRECT, INDIRECT, OR CONSEQUENTIAL DAMAGES OR ANY DAMAGES
# WHATSOEVER RESULTING FROM LOSS OF USE, DATA OR PROFITS, WHETHER IN AN
# ACTION OF CONTRACT, NEGLIGENCE OR OTHER TORTIOUS ACTION, ARISING OUT OF
# OR IN CONNECTION WITH THE USE OR PERFORMANCE OF THIS SOFTWARE.
import ciel
import logging

'''
Created on 4 Feb 2010

@author: dgm36
'''

from cherrypy.process import plugins
from Queue import Queue, Empty
from ciel.runtime.plugins import THREAD_TERMINATOR
import threading
    
class PingerPoker:
    pass
PINGER_POKER = PingerPoker()

class PingFailed:
    pass
PING_FAILED = PingFailed()
    
class Pinger(plugins.SimplePlugin):
    '''
    The pinger maintains the connection between a worker and the master. It
    serves two roles:
    
    1. At start up, the pinger is responsible for making the initial connection
       to the master. It periodically attempts registration.
       
    2. During normal operation, the pinger sends a heartbeat message every 30
       seconds to the master. The timeout is configurable, using the
       ping_timeout argument to the constructor.
       
    If the ping should fail, the pinger will attempt to re-register with a 
    master at the same URL. The master can be changed using the /master/ URI on
    the worker.
    '''
    
    def __init__(self, bus, master_proxy, status_provider=None, ping_timeout=5):
        plugins.SimplePlugin.__init__(self, bus)
        self.queue = Queue()
        self.non_urgent_queue = Queue()
        
        self.is_connected = False
        self.is_running = False
        
        self.thread = None
        self.master_proxy = master_proxy
        self.status_provider = status_provider
        self.ping_timeout = ping_timeout
                
    def subscribe(self):
        self.bus.subscribe('start', self.start, 75)
        self.bus.subscribe('stop', self.stop)
        self.bus.subscribe('poke', self.poke)
        
    def unsubscribe(self):
        self.bus.unsubscribe('start', self.start)
        self.bus.unsubscribe('stop', self.stop)
        self.bus.unsubscribe('poke', self.poke)
               
    def ping_fail_callback(self, success, url):
        if not success:
            ciel.log("Sending ping to master failed", "PINGER", logging.WARNING)
            self.queue.put(PING_FAILED)
                
    def start(self):
        if not self.is_running:
            self.is_running = True
            self.thread = threading.Thread(target=self.thread_main, args=())
            self.thread.start()
    
    def stop(self):
        if self.is_running:
            self.is_running = False
            self.queue.put(THREAD_TERMINATOR)
            self.thread.join()
            self.thread = None
        
    def poke(self):
        self.queue.put(PINGER_POKER)
        
    def thread_main(self):
        
        while True:
            
            # While not connected, attempt to register as a new worker.
            while not self.is_connected:
            
                try:    
                    hostname = self.master_proxy.get_public_hostname()
                    self.master_proxy.worker.set_hostname(hostname)
                    self.master_proxy.register_as_worker()
                    self.is_connected = True
                    break
                except:
                    pass
            
                try:
                    maybe_terminator = self.queue.get(block=True, timeout=self.ping_timeout)
                    if not self.is_running or maybe_terminator is THREAD_TERMINATOR:
                        return
                except Empty:
                    pass
            

            ciel.log.error("Registered with master at %s" % self.master_proxy.master_url, 'PINGER', logging.WARNING)
            
            # While connected, periodically ping the master.
            while self.is_connected:
                
                try:
                    new_thing = self.queue.get(block=True, timeout=self.ping_timeout)
                    if new_thing is PING_FAILED:
                        self.is_connected = False
                        break
                    if not self.is_connected or not self.is_running or new_thing is THREAD_TERMINATOR:
                        break
                except Empty:
                    pass
                
                try:
                    self.master_proxy.ping(self.ping_fail_callback)
                except:
                    self.is_connected = False
                
            if not self.is_running:
                break

########NEW FILE########
__FILENAME__ = process_pool
# Copyright (c) 2011 Derek Murray <Derek.Murray@cl.cam.ac.uk>
#
# Permission to use, copy, modify, and distribute this software for any
# purpose with or without fee is hereby granted, provided that the above
# copyright notice and this permission notice appear in all copies.
#
# THE SOFTWARE IS PROVIDED "AS IS" AND THE AUTHOR DISCLAIMS ALL WARRANTIES
# WITH REGARD TO THIS SOFTWARE INCLUDING ALL IMPLIED WARRANTIES OF
# MERCHANTABILITY AND FITNESS. IN NO EVENT SHALL THE AUTHOR BE LIABLE FOR
# ANY SPECIAL, DIRECT, INDIRECT, OR CONSEQUENTIAL DAMAGES OR ANY DAMAGES
# WHATSOEVER RESULTING FROM LOSS OF USE, DATA OR PROFITS, WHETHER IN AN
# ACTION OF CONTRACT, NEGLIGENCE OR OTHER TORTIOUS ACTION, ARISING OUT OF
# OR IN CONNECTION WITH THE USE OR PERFORMANCE OF THIS SOFTWARE.
import tempfile
import os
import uuid
import ciel
import logging
import simplejson
import shutil
from datetime import datetime
from ciel.public.references import SW2_FixedReference
import urlparse
from ciel.public.references import SWReferenceJSONEncoder
import pickle
import threading
from ciel.runtime.pycurl_rpc import post_string
from ciel.runtime.block_store import is_ref_local
from ciel.public.io_helpers import write_framed_json
from ciel.runtime.producer import write_fixed_ref_string

class ProcessRecord:
    """Represents a long-running process that is attached to this worker."""
    
    def __init__(self, id, pid, protocol):
        self.id = id
        self.pid = pid
        self.protocol = protocol
        self.job_id = None
        self.is_free = False
        self.last_used_time = None
        self.soft_cache_refs = set()
        
        # The worker communicates with the process using a pair of named pipes.
        self.fifos_dir = tempfile.mkdtemp(prefix="ciel-ipc-fifos-")
                
        self.from_process_fifo_name = os.path.join(self.fifos_dir, 'from_process')
        os.mkfifo(self.from_process_fifo_name)
        self.from_process_fifo = None 
        
        self.to_process_fifo_name = os.path.join(self.fifos_dir, 'to_process')
        os.mkfifo(self.to_process_fifo_name)
        self.to_process_fifo = None
        
        self._lock = threading.Lock()
        
    def set_pid(self, pid):
        self.pid = pid
        
    def get_read_fifo(self):
        with self._lock:
            if self.from_process_fifo is None:
                self.from_process_fifo = open(self.from_process_fifo_name, "r")
            return self.from_process_fifo
        
    def get_read_fifo_name(self):
        return self.from_process_fifo_name
        
    def get_write_fifo(self):
        with self._lock:
            if self.to_process_fifo is None:
                self.to_process_fifo = open(self.to_process_fifo_name, "w")
            return self.to_process_fifo
        
    def get_write_fifo_name(self):
        return self.to_process_fifo_name
        
    def cleanup(self):
        try:
            if self.from_process_fifo is not None: 
                self.from_process_fifo.close()
            if self.to_process_fifo is not None:
                self.to_process_fifo.close()
            shutil.rmtree(self.fifos_dir)
        except:
            ciel.log('Error cleaning up process %s, ignoring' % self.id, 'PROCESS', logging.WARN, True)
            
    def kill(self):
        ciel.log("Garbage collecting process %s" % self.id, "PROCESSPOOL", logging.INFO)
        write_fp = self.get_write_fifo()
        write_framed_json(("die", {"reason": "Garbage collected"}), write_fp)
        self.cleanup()
        
    def as_descriptor(self):
        return {'id' : self.id,
                'protocol' : self.protocol,
                'to_worker_fifo' : self.from_process_fifo_name,
                'from_worker_fifo' : self.to_process_fifo_name,
                'job_id' : self.job_id}
        
    def __repr__(self):
        return 'ProcessRecord(%s, %s)' % (repr(self.id), repr(self.pid))

class ProcessPool:
    """Represents a collection of long-running processes attached to this worker."""
    
    def __init__(self, bus, worker, soft_cache_executors):
        self.processes = {}
        self.bus = bus
        self.worker = worker
        self.lock = threading.Lock()
        self.gc_thread = None
        self.gc_thread_stop = threading.Event()
        self.soft_cache_executors = soft_cache_executors
        
    def subscribe(self):
        self.bus.subscribe('start', self.start)
        self.bus.subscribe('stop', self.stop)
        
    def unsubscribe(self):
        self.bus.unsubscribe('start', self.start)
        self.bus.unsubscribe('stop', self.stop)
        
    def soft_cache_process(self, proc_rec, exec_cls, soft_cache_keys):
        with self.lock:
            ciel.log("Caching process %s" % proc_rec.id, "PROCESSPOOL", logging.DEBUG)
            exec_cls.process_cache.add(proc_rec)
            proc_rec.is_free = True
            proc_rec.last_used_time = datetime.now()
            proc_rec.soft_cache_refs = set()
            for (refids, tag) in soft_cache_keys:
                proc_rec.soft_cache_refs.update(refids)
    
    def get_soft_cache_process(self, exec_cls, dependencies):
        if not hasattr(exec_cls, "process_cache"):
            return None
        with self.lock:
            best_proc = None
            ciel.log("Looking to re-use a process for class %s" % exec_cls.handler_name, "PROCESSPOOL", logging.DEBUG)
            for proc in exec_cls.process_cache:
                hits = 0
                for ref in dependencies:
                    if ref.id in proc.soft_cache_refs:
                        hits += 1
                ciel.log("Process %s: has %d/%d cached" % (proc.id, hits, len(dependencies)), "PROCESSPOOL", logging.DEBUG)
                if best_proc is None or best_proc[1] < hits:
                    best_proc = (proc, hits)
            if best_proc is None:
                return None
            else:
                proc = best_proc[0]
                ciel.log("Re-using process %s" % proc.id, "PROCESSPOOL", logging.DEBUG)
                exec_cls.process_cache.remove(proc)
                proc.is_free = False
                return proc
        
    def garbage_thread(self):
        while True:
            now = datetime.now()
            with self.lock:
                for executor in self.soft_cache_executors:
                    dead_recs = []
                    for proc_rec in executor.process_cache:
                        time_since_last_use = now - proc_rec.last_used_time
                        if time_since_last_use.seconds > 30:
                            proc_rec.kill()
                            dead_recs.append(proc_rec)
                    for dead_rec in dead_recs:
                        executor.process_cache.remove(dead_rec)
            self.gc_thread_stop.wait(60)
            if self.gc_thread_stop.isSet():
                with self.lock:
                    for executor in self.soft_cache_executors:
                        for proc_rec in executor.process_cache:
                            try:
                                proc_rec.kill()
                            except Exception as e:
                                ciel.log("Failed to shut a process down (%s)" % repr(e), "PROCESSPOOL", logging.WARNING)
                ciel.log("Process pool garbage collector: terminating", "PROCESSPOOL", logging.DEBUG)
                return
        
    def start(self):
        self.gc_thread = threading.Thread(target=self.garbage_thread)
        self.gc_thread.start()
    
    def stop(self):
        self.gc_thread_stop.set()
        for record in self.processes.values():
            record.cleanup()
        
    def get_reference_for_process(self, record):
        ref = SW2_FixedReference(record.id, self.worker.block_store.netloc)
        if not is_ref_local(ref):
            write_fixed_ref_string(pickle.dumps(record.as_descriptor()), ref)
        return ref
        
    def create_job_for_process(self, record):
        ref = self.get_reference_for_process(record)
        root_task_descriptor = {'handler' : 'proc',
                                'dependencies' : [ref],
                                'task_private' : ref}
        
        master_task_submit_uri = urlparse.urljoin(self.worker.master_url, "control/job/")
        
        try:
            message = simplejson.dumps(root_task_descriptor, cls=SWReferenceJSONEncoder)
            content = post_string(master_task_submit_uri, message)
        except Exception, e:
            ciel.log('Network error submitting process job to master', 'PROCESSPOOL', logging.WARN)
            raise e

        job_descriptor = simplejson.loads(content)
        record.job_id = job_descriptor['job_id']
        ciel.log('Created job %s for process %s (PID=%d)' % (record.job_id, record.id, record.pid), 'PROCESSPOOL', logging.DEBUG)
        
        
    def create_process_record(self, pid, protocol, id=None):
        if id is None:
            id = str(uuid.uuid4())
        
        record = ProcessRecord(id, pid, protocol)
        self.processes[id] = record
        return record
        
    def get_process_record(self, id):
        try:
            return self.processes[id]
        except KeyError:
            return None
        
    def delete_process_record(self, record):
        del self.processes[record.id]
        record.cleanup()
        
    def get_process_ids(self):
        return self.processes.keys()

########NEW FILE########
__FILENAME__ = upload_manager
# Copyright (c) 2010 Derek Murray <derek.murray@cl.cam.ac.uk>
#
# Permission to use, copy, modify, and distribute this software for any
# purpose with or without fee is hereby granted, provided that the above
# copyright notice and this permission notice appear in all copies.
#
# THE SOFTWARE IS PROVIDED "AS IS" AND THE AUTHOR DISCLAIMS ALL WARRANTIES
# WITH REGARD TO THIS SOFTWARE INCLUDING ALL IMPLIED WARRANTIES OF
# MERCHANTABILITY AND FITNESS. IN NO EVENT SHALL THE AUTHOR BE LIABLE FOR
# ANY SPECIAL, DIRECT, INDIRECT, OR CONSEQUENTIAL DAMAGES OR ANY DAMAGES
# WHATSOEVER RESULTING FROM LOSS OF USE, DATA OR PROFITS, WHETHER IN AN
# ACTION OF CONTRACT, NEGLIGENCE OR OTHER TORTIOUS ACTION, ARISING OUT OF
# OR IN CONNECTION WITH THE USE OR PERFORMANCE OF THIS SOFTWARE.
import shutil
import logging
import os
import ciel
from ciel.runtime.producer import make_local_output
from ciel.runtime.fetcher import sync_retrieve_refs

class UploadSession:
    
    def __init__(self, id, block_store):
        self.id = id
        self.block_store = block_store
        self.current_pos = 0
        self.output_ctx = make_local_output(self.id)
        (filename, is_fd) = self.output_ctx.get_filename_or_fd()
        assert not is_fd
        self.output_filename = filename
        
    def save_chunk(self, start_index, body_file):
        assert self.current_pos == start_index
        with open(self.output_filename, 'ab') as output_file:
            shutil.copyfileobj(body_file, output_file)
            self.current_pos = output_file.tell()
    
    def commit(self, size):
        assert os.path.getsize(self.output_filename) == size
        self.output_ctx.close()
    
class UploadManager:
    
    def __init__(self, block_store, deferred_work):
        self.block_store = block_store
        self.current_uploads = {}
        self.current_fetches = {}
        self.deferred_work = deferred_work
        
    def start_upload(self, id):
        self.current_uploads[id] = UploadSession(id, self.block_store)
        
    def handle_chunk(self, id, start_index, body_file):
        session = self.current_uploads[id]
        session.save_chunk(start_index, body_file)
        
    def commit_upload(self, id, size):
        session = self.current_uploads[id]
        session.commit(size)
        del self.current_uploads[id]
        
    def get_status_for_fetch(self, session_id):
        return self.current_fetches[session_id]
        
    def fetch_refs(self, session_id, refs):
        self.current_fetches[session_id] = 408
        self.deferred_work.do_deferred(lambda: self.fetch_refs_deferred(session_id, refs))
        
    def fetch_refs_deferred(self, session_id, refs):
        ciel.log.error('Fetching session %s' % session_id, 'UPLOAD', logging.DEBUG)
        try:
            sync_retrieve_refs(refs, None)
            self.current_fetches[session_id] = 200
            for ref in refs:
                self.block_store.pin_ref_id(ref.id)
        except:
            ciel.log.error('Exception during attempted fetch session %s' % session_id, 'UPLOAD', logging.WARNING, True)
            self.current_fetches[session_id] = 500
        ciel.log.error('Finished session %s, status = %d' % (session_id, self.current_fetches[session_id]), 'UPLOAD', logging.DEBUG)

########NEW FILE########
__FILENAME__ = worker_view
# Copyright (c) 2010 Derek Murray <derek.murray@cl.cam.ac.uk>
#
# Permission to use, copy, modify, and distribute this software for any
# purpose with or without fee is hereby granted, provided that the above
# copyright notice and this permission notice appear in all copies.
#
# THE SOFTWARE IS PROVIDED "AS IS" AND THE AUTHOR DISCLAIMS ALL WARRANTIES
# WITH REGARD TO THIS SOFTWARE INCLUDING ALL IMPLIED WARRANTIES OF
# MERCHANTABILITY AND FITNESS. IN NO EVENT SHALL THE AUTHOR BE LIABLE FOR
# ANY SPECIAL, DIRECT, INDIRECT, OR CONSEQUENTIAL DAMAGES OR ANY DAMAGES
# WHATSOEVER RESULTING FROM LOSS OF USE, DATA OR PROFITS, WHETHER IN AN
# ACTION OF CONTRACT, NEGLIGENCE OR OTHER TORTIOUS ACTION, ARISING OUT OF
# OR IN CONNECTION WITH THE USE OR PERFORMANCE OF THIS SOFTWARE.
import ciel.runtime.executors
import ciel
from ciel.runtime.producer import ref_from_string

'''
Created on 8 Feb 2010

@author: dgm36
'''
from cherrypy.lib.static import serve_file
from ciel.public.references import json_decode_object_hook,\
    SWReferenceJSONEncoder
from ciel.runtime.remote_stat import receive_stream_advertisment
from ciel.runtime.producer_stat import subscribe_output, unsubscribe_output
import sys
import simplejson
import cherrypy
import os

class WorkerRoot:
    
    def __init__(self, worker):
        self.worker = worker
        self.control = ControlRoot(worker)
        self.data = self.control.data

class ControlRoot:

    def __init__(self, worker):
        self.worker = worker
        self.master = RegisterMasterRoot(worker)
        self.task = TaskRoot(worker)
        self.data = DataRoot(worker.block_store)
        self.streamstat = StreamStatRoot()
        self.features = FeaturesRoot(worker.execution_features)
        self.kill = KillRoot()
        self.log = LogRoot(worker)
        self.upload = UploadRoot(worker.upload_manager)
        self.admin = ManageRoot(worker.block_store)
        self.fetch = FetchRoot(worker.upload_manager)
        self.process = ProcessRoot(worker.process_pool)
        self.abort = AbortRoot(worker)
        self.stopwatch = StopwatchRoot()
    
    @cherrypy.expose
    def index(self):
        return simplejson.dumps(self.worker.id)

class StreamStatRoot:

    @cherrypy.expose
    def default(self, id, op):
        if cherrypy.request.method == "POST":
            payload = simplejson.loads(cherrypy.request.body.read())
            if op == "subscribe":
                subscribe_output(payload["netloc"], payload["chunk_size"], id)
            elif op == "unsubscribe":
                unsubscribe_output(payload["netloc"], id)
            elif op == "advert":
                receive_stream_advertisment(id, **payload)
            else:
                raise cherrypy.HTTPError(404)
        else:
            raise cherrypy.HTTPError(405)

class KillRoot:
    
    def __init__(self):
        pass
    
    @cherrypy.expose
    def index(self):
        ciel.runtime.executors.kill_all_running_children()
        sys.exit(0)

class RegisterMasterRoot:
    
    def __init__(self, worker):
        self.worker = worker
            
    @cherrypy.expose
    def index(self):
        if cherrypy.request.method == 'POST':
            master_details = simplejson.loads(cherrypy.request.body.read())
            self.worker.set_master(master_details)
        elif cherrypy.request.method == 'GET':
            return simplejson.dumps(self.worker.master_proxy.get_master_details())
        else:
            raise cherrypy.HTTPError(405)
    
class TaskRoot:
    
    def __init__(self, worker):
        self.worker = worker
        
    @cherrypy.expose
    def index(self):
        if cherrypy.request.method == 'POST':
            ciel.stopwatch.multi(starts=["worker_task"], laps=["end_to_end"])
            task_descriptor = simplejson.loads(cherrypy.request.body.read(), object_hook=json_decode_object_hook)
            if task_descriptor is not None:
                self.worker.multiworker.create_and_queue_taskset(task_descriptor)
                return
        raise cherrypy.HTTPError(405)
    
    # TODO: Add some way of checking up on the status of a running task.
    #       This should grow to include a way of getting the present activity of the task
    #       and a way of setting breakpoints.
    #       ...and a way of killing the task.
    #       Ideally, we should create a task view (Root) for each running task.    

class AbortRoot:
    
    def __init__(self, worker):
        self.worker = worker
    
    @cherrypy.expose
    def default(self, job_id, task_id=None):
        
        try:
            job = self.worker.multiworker.get_job_by_id(job_id)
        except KeyError:
            return
            
        if task_id is None:
            job.abort_all_active_tasksets()
        else:
            job.abort_taskset_with_id(task_id)
            

class LogRoot:

    def __init__(self, worker):
        self.worker = worker

    @cherrypy.expose
    def wait_after(self, event_count):
        if cherrypy.request.method == 'POST':
            try:
                self.worker.await_log_entries_after(event_count)
                return simplejson.dumps({})
            except Exception as e:
                return simplejson.dumps({"error": repr(e)})
        else:
            raise cherrypy.HTTPError(405)

    @cherrypy.expose
    def index(self, first_event, last_event):
        if cherrypy.request.method == 'GET':
            events = self.worker.get_log_entries(int(first_event), int(last_event))
            return simplejson.dumps([{"time": repr(t), "event": e} for (t, e) in events])
        else:
            raise cherrypy.HTTPError(405)

class DataRoot:
    
    def __init__(self, block_store, backup_sender=None):
        self.block_store = block_store
        self.backup_sender = backup_sender
        
    @cherrypy.expose
    def default(self, id):
        safe_id = id
        if cherrypy.request.method == 'GET':
            filename = self.block_store.filename(safe_id)
            try:
                response_body = serve_file(filename)
                return response_body
            except cherrypy.HTTPError as he:
                if he.status == 404:
                    response_body = serve_file(self.block_store.producer_filename(safe_id))
                    return response_body
                else:
                    raise
                
        elif cherrypy.request.method == 'POST':
            request_body = cherrypy.request.body.read()
            new_ref = ref_from_string(request_body, safe_id)
            if self.backup_sender is not None:
                self.backup_sender.add_data(safe_id, request_body)
            #if self.task_pool is not None:
            #    self.task_pool.publish_refs({safe_id : new_ref})
            return simplejson.dumps(new_ref, cls=SWReferenceJSONEncoder)
        
        elif cherrypy.request.method == 'HEAD':
            if os.path.exists(self.block_store.filename(id)):
                return
            else:
                raise cherrypy.HTTPError(404)

        else:
            raise cherrypy.HTTPError(405)

    @cherrypy.expose
    def index(self):
        if cherrypy.request.method == 'POST':
            id = self.block_store.allocate_new_id()
            request_body = cherrypy.request.body.read()
            new_ref = ref_from_string(request_body, id)
            if self.backup_sender is not None:
                self.backup_sender.add_data(id, request_body)
            #if self.task_pool is not None:
            #    self.task_pool.publish_refs({id : new_ref})
            return simplejson.dumps(new_ref, cls=SWReferenceJSONEncoder)
        elif cherrypy.request.method == 'GET':
            return serve_file(self.block_store.generate_block_list_file())
        else:
            raise cherrypy.HTTPError(405)
        
    # TODO: Also might investigate a way for us to have a spanning tree broadcast
    #       for common files.
    
class UploadRoot:
    
    def __init__(self, upload_manager):
        self.upload_manager = upload_manager
        
    @cherrypy.expose
    def default(self, id, start=None):
        if cherrypy.request.method != 'POST':
            raise cherrypy.HTTPError(405)
        if start is None:
            #upload_descriptor = simplejson.loads(cherrypy.request.body.read(), object_hook=json_decode_object_hook)
            self.upload_manager.start_upload(id)#, upload_descriptor)
        elif start == 'commit':
            size = int(simplejson.load(cherrypy.request.body))
            self.upload_manager.commit_upload(id, size)
        else:
            start_index = int(start)
            self.upload_manager.handle_chunk(id, start_index, cherrypy.request.body)
    
class FetchRoot:
    
    def __init__(self, upload_manager):
        self.upload_manager = upload_manager
        
    @cherrypy.expose
    def default(self, id=None):
        if cherrypy.request.method != 'POST':
            if id is None:
                return simplejson.dumps(self.upload_manager.current_fetches)
            else:
                status = self.upload_manager.get_status_for_fetch(id)
                if status != 200:
                    raise cherrypy.HTTPError(status)
                else:
                    return
                
        refs = simplejson.load(cherrypy.request.body, object_hook=json_decode_object_hook)
        self.upload_manager.fetch_refs(id, refs)
        
        cherrypy.response.status = '202 Accepted'
        
class ProcessRoot:
    
    def __init__(self, process_pool):
        self.process_pool = process_pool
        
    @cherrypy.expose
    def default(self, id=None):
        
        if cherrypy.request.method == 'POST' and id is None:
            # Create a new process record.
            (pid, protocol) = simplejson.load(cherrypy.request.body)
            record = self.process_pool.create_process_record(pid, protocol)
            self.process_pool.create_job_for_process(record)
            
            return simplejson.dumps(record.as_descriptor())
            
        elif cherrypy.request.method == 'GET' and id is None:
            # Return a list of process IDs.
            return simplejson.dumps(self.process_pool.get_process_ids())
        
        elif id is not None:
            # Return information about a running process (for debugging).
            record = self.process_pool.get_process_record(id)
            if record is None:
                raise cherrypy.HTTPError(404)
            elif cherrypy.request.method != 'GET':
                raise cherrypy.HTTPError(405)
            else:
                return simplejson.dumps(record.as_descriptor())
        
        else:
            raise cherrypy.HTTPError(405)
        
class ManageRoot:
    
    def __init__(self, block_store):
        self.block_store = block_store
        
    @cherrypy.expose
    def default(self, action=None, id=None):
        if action == 'flush':
            if id == 'really':
                kept, removed = self.block_store.flush_unpinned_blocks(True)
                return 'Kept %d blocks, removed %d blocks' % (kept, removed)
            else:
                kept, removed = self.block_store.flush_unpinned_blocks(False)
                return 'Would keep %d blocks, remove %d blocks' % (kept, removed)
        elif action == 'pin' and id is not None:
            self.block_store.pin_ref_id(id)
        elif action == 'pin':
            return simplejson.dumps(self.block_store.generate_pin_refs(), cls=SWReferenceJSONEncoder)
    
class FeaturesRoot:
    
    def __init__(self, execution_features):
        self.execution_features = execution_features
    
    @cherrypy.expose
    def index(self):
        return simplejson.dumps(self.execution_features.all_features())

class StopwatchRoot:
    
    def __init__(self):
        pass
    
    @cherrypy.expose
    def index(self):
        return simplejson.dumps(ciel.stopwatch.times.keys())
    
    @cherrypy.expose
    def default(self, watch_name):
        try:
            times = ciel.stopwatch.get_times(watch_name)
            return simplejson.dumps([float(x.seconds) + (float(x.microseconds) / 1000000.0) for x in times])
        except KeyError:
            if not ciel.stopwatch.enabled:
                raise cherrypy.HTTPError(403, "Profiling not enabled")
            else:
                raise cherrypy.HTTPError(404)
########NEW FILE########
__FILENAME__ = simple
# Copyright (c) 2011 Derek Murray <Derek.Murray@cl.cam.ac.uk>
#
# Permission to use, copy, modify, and distribute this software for any
# purpose with or without fee is hereby granted, provided that the above
# copyright notice and this permission notice appear in all copies.
#
# THE SOFTWARE IS PROVIDED "AS IS" AND THE AUTHOR DISCLAIMS ALL WARRANTIES
# WITH REGARD TO THIS SOFTWARE INCLUDING ALL IMPLIED WARRANTIES OF
# MERCHANTABILITY AND FITNESS. IN NO EVENT SHALL THE AUTHOR BE LIABLE FOR
# ANY SPECIAL, DIRECT, INDIRECT, OR CONSEQUENTIAL DAMAGES OR ANY DAMAGES
# WHATSOEVER RESULTING FROM LOSS OF USE, DATA OR PROFITS, WHETHER IN AN
# ACTION OF CONTRACT, NEGLIGENCE OR OTHER TORTIOUS ACTION, ARISING OUT OF
# OR IN CONNECTION WITH THE USE OR PERFORMANCE OF THIS SOFTWARE.
import os
import sys

inputs = None
outputs = None

def init():
    global inputs, outputs
    
    try:
        input_files = os.getenv("INPUT_FILES")
        output_files = os.getenv("OUTPUT_FILES")
        
        if input_files is None or output_files is None:
            raise KeyError()
        
        with open(input_files) as f:
            inputs = [open(x.strip(), 'r') for x in f.readlines()]
            
        with open(output_files) as f:
            outputs = [open(x.strip(), 'w') for x in f.readlines()]
        
    except KeyError:
        print >>sys.stderr, "--- DEBUG MODE - using standard input and output ---"
        inputs = [sys.stdin]
        outputs = [sys.stdout]
########NEW FILE########
