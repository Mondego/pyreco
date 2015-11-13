__FILENAME__ = codegen
#!/usr/bin/env python

import os
import sys
import string

sys.path.append(os.path.join("vendor", "rabbitmq-codegen"))
from amqp_codegen import *

AMQP_ACCEPTED_BY_UPDATE_JSON="amqp-accepted-by-update.json"

BANNED_CLASSES=['access', 'tx']
BANNED_FIELDS= {
    'ticket': 0,
    'nowait': 0,
    'capabilities': '',
    'insist' : 0,
    'out_of_band': '',
    'known_hosts': '',
}

import codegen_helpers


def pyize(*args):
    a = ' '.join(args).replace('-', '_').replace(' ', '_')
    if a == 'global': a+= '_'
    if a == 'type': a+= '_'
    return a

def Pyize(*args):
    words = []
    for a in args:
        words.extend( a.split('-') )
    a = ''.join([a.title() for a in words]).replace('-', '').replace(' ', '')
    if a in ['SyntaxError', 'NotImplemented']:
        a = 'AMQP' + a
    return a

def PYIZE(*args):
    return ' '.join(args).replace('-', '_').replace(' ', '_').upper()



def print_constants(spec):
    for c in spec.allClasses():
        for m in c.allMethods():
            print "%-32s= 0x%08X \t# %i,%i %i" % (
                m.u,
                m.method_id,
                m.klass.index, m.index, m.method_id
                )

    print
    for c in spec.allClasses():
        if c.fields:
            print "%-24s= 0x%04X" % (
                c.u,
                c.index,)
    print

def print_decode_methods_map(client_methods):
    print "METHODS = {"
    for m in client_methods:
        print "    %-32s%s," % (
            m.u + ':',
            m.decode,
            )
    print "}"
    print

def print_decode_properties_map(props_classes):
    print "PROPS = {"
    for c in props_classes:
        print "    %s: %s, \t# %d" % (
            c.u, c.decode, c.index)
    print "}"
    print


def print_decode_method(m):
    print "class %s(Frame):" % (m.frame,)
    print "    name = '%s'" % (pyize(m.klass.name + '.' + m.name),)
    print "    method_id = %s" % (pyize('method', m.klass.name, m.name).upper(),)
    if m.hasContent:
        print "    has_content = True"
        print "    class_id = %s" % (m.klass.u,)
    print ""

    print "def %s(data, offset):" % (m.decode,)
    print "    frame = %s()" % (m.frame,)

    fields = codegen_helpers.UnpackWrapper()
    for i, f in enumerate(m.arguments):
        fields.add(f.n, f.t)

    fields.do_print(' '*4, "frame['%s']")
    print "    return frame, offset"
    print


def print_decode_properties(c):
    print "def %s(data, offset):" % (c.decode,)
    print "    props = {}"
    print "    flags, = unpack_from('!H', data, offset)"
    print "    offset += 2"
    print "    assert (flags & 0x01) == 0"
    for i, f in enumerate(c.fields):
        print "    if (flags & 0x%04x): # 1 << %i" % (1 << (15-i), 15-i)
        fields = codegen_helpers.UnpackWrapper()
        fields.add(f.n, f.t)
        fields.do_print(" "*8, "props['%s']")
    print "    return props, offset"
    print




def _default_params(m):
    for f in m.arguments:
        yield "%s=%r" % (f.n, str(f.defaultvalue) if type(f.defaultvalue) == unicode else f.defaultvalue)
    if m.hasContent:
        yield "user_headers={}"
        yield "payload=''"
        yield "frame_size=None"

def _method_params_list(m):
    for f in m.arguments:
        if not f.banned:
            yield f.n
    if m.hasContent:
        yield 'user_headers'
        yield 'body'
        yield 'frame_size'

def print_encode_method(m):
    print "# %s" % (' '.join(_default_params(m)),)
    print "def %s(%s):" % (m.encode, ', '.join(_method_params_list(m)),)
    for f in [f for f in m.arguments if not f.banned and f.t in ['table']]:
        print "    %s_raw = table.encode(%s)" % (f.n, f.n)

    if m.hasContent:
        print "    props, headers = split_headers(user_headers, %s_PROPS_SET)" % (
            m.klass.name.upper(),)
        print "    if headers:"
        print "        props['headers'] = headers"

    fields = codegen_helpers.PackWrapper()
    fields.add(m.u, 'long')
    for f in m.arguments:
        fields.add(f.n, f.t)
    fields.close()

    if not m.hasContent:
        print "    return ( (0x01,"
        if fields.group_count() > 1:
            print "              ''.join(("
            fields.do_print(' '*16, '%s')
            print "              ))"
        else:
            fields.do_print(' '*16, '%s')
        print "           ), )"
    else:
        print "    return [ (0x01,"
        print "              ''.join(("
        fields.do_print(' '*16, '%s')
        print "              ))"
        print "           ),"
        print "           %s(len(body), props)," % (m.klass.encode,)
        print "        ] + encode_body(body, frame_size)"

def print_encode_properties(c):
    print "%s_PROPS_SET = set(("% (c.name.upper(),)
    for f in c.fields:
        print '    "%s", %s # %s' % (f.n, ' '*(16-len(f.n)), f.t)
    print "    ))"
    print
    print "ENCODE_PROPS_%s = {" % (c.name.upper(),)
    for i, f in enumerate(c.fields):
        pn = pyize(f.name)
        print "    '%s': (" % (pn,)
        print "        %i," % (i,)
        print "        0x%04x, # (1 << %i)" % ( 1 << (15-i), 15-i,)

        fields = codegen_helpers.PackWrapper()
        if f.t not in ['table']:
            fields.add("val", f.t)
        else:
            fields.add("table.encode(val)", f.t, nr='%s')
        fields.close()
        if len(fields.fields) > 1:
            print ' '*8 + "lambda val: ''.join(("
            fields.do_print(' '*16, '%s')
            print ' '*8 + ')) ),'
        else:
            print '  '*4 + 'lambda val:',
            fields.do_print('', '%s', comma=False)
            print '        ),'

    print "}"
    print
    print "def %s(body_size, props):" % (c.encode,)
    print "    pieces = ['']*%i" % (len(c.fields),)
    print "    flags = 0"
    print "    enc = ENCODE_PROPS_%s" % (c.name.upper(),)
    print
    print "    for key in %s_PROPS_SET & set(props.iterkeys()):" % \
        (c.name.upper(),)
    print "        i, f, fun = enc[key]"
    print "        flags |= f"
    print "        pieces[i] = fun(props[key])"
    print ""
    print "    return (0x02, ''.join(("
    print "        pack('!HHQH',"
    print "              %s, 0, body_size, flags)," % (c.u,)
    print "        ''.join(pieces),"
    print "        ))"
    print "        )"


def GetAmqpSpec(spec_path, accepted_by_udate):
    spec = AmqpSpec(spec_path)

    for c in spec.allClasses():
        c.banned = bool(c.name in BANNED_CLASSES)
        c.u = PYIZE('CLASS', c.name)

    spec.classes = filter(lambda c:not c.banned, spec.classes)

    for c in spec.allClasses():
        for m in c.allMethods():
            m.u = PYIZE('METHOD', m.klass.name, m.name)
            m.method_id = m.klass.index << 16 | m.index
            m.decode = pyize('decode', m.klass.name, m.name)
            m.encode = pyize('encode', m.klass.name, m.name)
            m.frame = Pyize('frame', m.klass.name, m.name)

            try:
                m.accepted_by = accepted_by_udate[c.name][m.name]
            except KeyError:
                print >> sys.stderr, " [!] Method %s.%s unknown! Assuming " \
                    "['server', 'client']" % (c.name, m.name)
                m.accepted_by = ['server', 'client']

            for f in m.arguments:
                f.t = spec.resolveDomain(f.domain)
                f.n = pyize(f.name)
                f.banned = bool(f.name in BANNED_FIELDS)

    for c in spec.allClasses():
        if c.fields:
            c.decode = pyize('decode', c.name, 'properties')
            c.encode = pyize('encode', c.name, 'properties')
            for f in c.fields:
                f.t = spec.resolveDomain(f.domain)
                f.n = pyize(f.name)
    return spec

def generate_spec(spec_path):
    accepted_by_udate = json.loads(file(AMQP_ACCEPTED_BY_UPDATE_JSON).read())
    return GetAmqpSpec(spec_path, accepted_by_udate)


def main(spec_path):
    spec = generate_spec(spec_path)
    print """# Autogenerated - do not edit
import calendar
import datetime
from struct import pack, unpack_from

from . import table

"""
    print "PREAMBLE = 'AMQP\\x00\\x%02x\\x%02x\\x%02x'" % (
        spec.major, spec.minor, spec.revision)
    print
    print_constants(spec)
    print

    props_classes = [c for c in spec.allClasses() if c.fields]


    client_methods = [m for m in spec.allMethods() if 'client' in m.accepted_by]
    print
    print '''
class Frame(dict):
    has_content = False
    is_error = False

'''
    for m in client_methods:
        print_decode_method(m)
        print
    print
    print_decode_methods_map(client_methods)
    print
    for c in props_classes:
        print_decode_properties(c)
        print
    print_decode_properties_map(props_classes)
    print

    server_methods = [m for m in spec.allMethods() if 'server' in m.accepted_by]
    for m in server_methods:
        print_encode_method(m)
        print

    for c in props_classes:
        print_encode_properties(c)
        print

    print """
def split_headers(user_headers, properties_set):
    props = {}
    headers = {}
    for key, value in user_headers.iteritems():
        if key in properties_set:
            props[key] = value
        else:
            headers[key] = value
    return props, headers

def encode_body(body, frame_size):
    limit = frame_size - 7 - 1   # spec is broken...
    r = []
    while body:
        payload, body = body[:limit], body[limit:]
        r.append( (0x03, payload) )
    return r
"""

def spec_exceptions(spec_path):
    spec = generate_spec(spec_path)
    print """# Autogenerated - do not edit
"""
    err_constants = [(name, value, klass)
                     for name, value, klass in spec.constants
                     if klass in ('hard-error', 'soft-error')]
    print "class AMQPError(Exception): pass"
    print "class AMQPSoftError(AMQPError): pass"
    print "class AMQPHardError(AMQPError): pass"
    print
    for name, value, klass in err_constants:
            print "class %s(AMQP%s):" % (Pyize(name),
                                         Pyize(klass))
            print "    reply_code = %s" % (value,)
    print
    print "ERRORS = {"
    for name, value, klass in err_constants:
        print "    %i: %s," % (value, Pyize(name))
    print "}"
    print



if __name__ == "__main__":
    do_main_dict({"spec": main, 'spec_exceptions': spec_exceptions})








########NEW FILE########
__FILENAME__ = codegen_helpers
import itertools
import random
import re

from codegen import BANNED_FIELDS


def fl_iterate(items):
    items = list(items)
    assert len(items) > 0
    for j, item in enumerate(items):
        yield item, j == 0, j == len(items)-1



class Field(object):
    def __init__(self, fmt=None, size=None, name=None, decor_name=True):
        self.fmt = fmt
        self.size = size
        self.name = name
        self.decor_name = decor_name

    def dname(self, decor):
        if self.decor_name:
            return decor % self.name
        else:
            return self.name

    def do_print(self, prefix, decor):
        dname = self.dname(decor)
        self._do_print(prefix, dname)

class FieldStr(Field):
    def _do_print(self, prefix, dname):
        print prefix+"%s = data[offset : offset+str_len]" % dname
        print prefix+"offset += str_len"

class FieldTable(Field):
    def _do_print(self, prefix, dname):
        print prefix+"%s, offset = table.decode(data, offset)" % dname

def xdecode_bits(wrapper, name):
    wrapper.bits.append( name )
    if len(wrapper.bits) == 1:
        return [Field('B', 1, 'bits', False)]
    else:
        return []

unpack_fixed_types = {
    'octet':     lambda w, n:[Field('B', 1, n)],
    'short':     lambda w, n:[Field('H', 2, n)],
    'long':      lambda w, n:[Field('I', 4, n)],
    'longlong':  lambda w, n:[Field('Q', 8, n)],
    'timestamp': lambda w, n:[Field('Q', 8, n)],
    'shortstr':  lambda w, n:[Field('B', 1, 'str_len', False), FieldStr(name=n)],
    'longstr':   lambda w, n:[Field('I', 4, 'str_len', False), FieldStr(name=n)],
    'table':     lambda w, n:[FieldTable(name=n)],
    'bit':      xdecode_bits,
}


class UnpackWrapper(object):
    fixed_types = unpack_fixed_types
    def __init__(self):
        self.fields = []
        self.bits = []

    def add(self, n, t):
        self.fields += self.fixed_types[t](self, n)

    def _groups(self):
        for for_struct, group in itertools.groupby(self.fields, lambda f: \
                                           True if f.fmt else random.random()):
            yield for_struct is True, list(group)

    def do_print(self, p, decor):
        for for_struct, fields in self._groups():
            if for_struct:
                for f, first, last in fl_iterate(fields):
                    print p+"%s%s%s%s" % (
                        '(' if first else ' ',
                        f.dname(decor),
                        ',' if first and last else '',
                        ')' if last else ',\n',
                    ),
                fmts = ''.join([f.fmt for f in fields])
                print "= unpack_from('!%s', data, offset)" % (fmts,)
                if 'bits' in [f.dname(decor) for f in fields]:
                    self.do_print_bits(p, decor)
                print p+"offset += %s" % ('+'.join(
                        map(str, [f.size for f in fields])
                        ),)
            else:
                assert len(fields)==1
                fields[0].do_print(p, decor)

    def do_print_bits(self, prefix, decor):
        for b, name in enumerate(self.bits):
            print prefix+"%s = bool(bits & 0x%x)" % (decor % name, 1 << b)


fixed_types = {
    'octet': ('B', 1),
    'short': ('H', 2),
    'long': ('I', 4),
    'longlong': ('Q', 8),
    'timestamp': ('Q', 8),
}

class PackWrapper(object):
    def __init__(self):
        self.fields = []
        self.bits = []

    def add(self, n, t, nr=None):
        nl = 'len(%s)' % n
        if nr is None:
            nr = '%s_raw' % n
        else:
            nr = nr % n
        nrl = 'len(%s)' % nr
        if n in BANNED_FIELDS:
            default = BANNED_FIELDS[n]
            if t in fixed_types:
                self.fields += [
                    (fixed_types[t][0], fixed_types[t][1], str(default))
                    ]
                return
            elif t == 'shortstr':
                if not default:
                    self.fields += [
                        ('B', 1, '0'),
                        ]
                    return
                else:
                    self.fields += [
                        ('B', 1, str(len(default))),
                        (None, len(default), repr(default)),
                        ]
                    return
            elif t == 'bit':
                pass
            else:
                assert False, "not supported %s" % (t,)

        if t in fixed_types:
            self.fields += [
                (fixed_types[t][0], fixed_types[t][1], n)
                ]
        elif t == 'shortstr':
            self.fields += [
                ('B', 1, nl),
                (None, nl, n),
                ]
        elif t == 'longstr':
            self.fields += [
                ('I', 4, nl),
                (None, nl, n),
                ]
        elif t == 'table':
            self.fields += [
                (None, nrl, nr)
                ]
        elif t == 'bit':
            if not self.bits:
                self.fields += [
                    ('B', 1, self.encode_bits)
                    ]
            self.bits.append( n )
        else:
            raise Exception("bad type %s" % (t,))

    def encode_bits(self):
        acc = []
        for i, n in enumerate(self.bits):
            if n in BANNED_FIELDS:
                if BANNED_FIELDS[n]:
                    acc.append( str(BANNED_FIELDS[n]) )
            else:
                acc.append( '(%s and 0x%x or 0)' % (n, 1 << i) )
        if not acc:
            acc = '0'
        return ' | '.join( acc )

    def get_sizes(self):
        return zip(*self.fields)[1]

    def close(self):
        nfields = []
        for fmt, sz, name in self.fields:
            if callable(name):
                name = name()
            nfields.append( (fmt, sz, str(name)) )
        self.fields = nfields

    def group_count(self):
        return len(list(self.groups()))

    def groups(self):
        groups = itertools.groupby(self.fields, lambda (a,b,c): True \
                                       if a else random.random())
        for _, fields_group in groups:
            fmt, sizes, names = itertools.izip(*fields_group)
            if re.match("^[0-9]+$", ''.join(names)):
                for sz in sizes:
                    assert isinstance(sz, int), repr(sz)
                immediate = True
            else:
                immediate = False
            yield immediate, fmt, sizes, names

    def do_print(self, prefix, _, comma=True):
        for immediate, fmt, sizes, names in self.groups():
            if immediate:
                s = ""
                for size, name in zip(sizes, names):
                    s+=  "%0*x" % (size*2, int(name))
                print prefix+'"%s",' % (''.join(["\\x%s" % p
                                                for p in re.findall('..', s)]),)
            else:
                if fmt[0] is not None:
                    print prefix+"pack('!%s', %s)%s" % (''.join(fmt),
                                                              ', '.join(names),
                                                               ',' if comma else '')
                else:
                    assert len(fmt) == 1
                    print prefix+"%s%s" % (names[0],
                                           ',' if comma else '')


########NEW FILE########
__FILENAME__ = conf

master_doc = 'puka'

########NEW FILE########
__FILENAME__ = emit_log_headers
#!/usr/bin/env python
import sys
sys.path.append("..")
import puka

client = puka.Client("amqp://localhost/")
promise = client.connect()
client.wait(promise)


promise = client.exchange_declare(exchange='headers_logs', type='headers')
client.wait(promise)

argv = sys.argv[1:-1] if len(sys.argv) > 2 else ['anonymous:info']
headers = dict(arg.split(':', 2) for arg in argv)

message = sys.argv[-1] if len(sys.argv) > 1 else 'Hello World!'
promise = client.basic_publish(exchange='headers_logs', routing_key='',
                               body=message,
                               headers=headers)
client.wait(promise)

print " [x] Sent %r %r" % (headers, message)
client.close()

########NEW FILE########
__FILENAME__ = parallel_declare
#!/usr/bin/env python

import sys
sys.path.append("..")

import logging
FORMAT_CONS = '%(asctime)s %(name)-12s %(levelname)8s\t%(message)s'
logging.basicConfig(level=logging.DEBUG, format=FORMAT_CONS)



import puka

client = puka.Client("amqp://localhost/")

promise = client.connect()
client.wait(promise)

promises = [client.queue_declare(queue='a%04i' % i) for i in range(1000)]
for promise in promises:
    client.wait(promise)

promises = [client.queue_delete(queue='a%04i' % i) for i in range(1000)]
for promise in promises:
    client.wait(promise)

promise = client.close()
client.wait(promise)

########NEW FILE########
__FILENAME__ = receive
#!/usr/bin/env python

import sys
sys.path.append("..")

import puka


client = puka.Client("amqp://localhost/")
promise = client.connect()
client.wait(promise)

promise = client.queue_declare(queue='test')
client.wait(promise)

print "  [*] Waiting for messages. Press CTRL+C to quit."

consume_promise = client.basic_consume(queue='test', prefetch_count=1)
while True:
    result = client.wait(consume_promise)
    print " [x] Received message %r" % (result,)
    client.basic_ack(result)

promise = client.close()
client.wait(promise)


########NEW FILE########
__FILENAME__ = receive_logs_headers
#!/usr/bin/env python
import sys
sys.path.append("..")
import puka

client = puka.Client("amqp://localhost/")
promise = client.connect()
client.wait(promise)


promise = client.exchange_declare(exchange='headers_logs', type='headers')
client.wait(promise)

promise = client.queue_declare(exclusive=True)
queue_name = client.wait(promise)['queue']

argv = sys.argv[1:]
if not argv:
    print >> sys.stderr, "Usage: %s [header:value]..." % (sys.argv[0],)
    sys.exit(1)

headers = dict(arg.split(':', 2) for arg in argv)
headers['x-match'] = 'any'
promise = client.queue_bind(exchange='headers_logs', queue=queue_name,
                            routing_key='', arguments=headers)
client.wait(promise)

print ' [*] Waiting for logs %r. To exit press CTRL+C' % (headers,)

consume_promise = client.basic_consume(queue=queue_name, no_ack=True)
while True:
    msg_result = client.wait(consume_promise)
    print " [x] %r:%r" % (msg_result['headers'], msg_result['body'])

########NEW FILE########
__FILENAME__ = receive_one
#!/usr/bin/env python

import sys
sys.path.append("..")

import puka


client = puka.Client("amqp://localhost/")
promise = client.connect()
client.wait(promise)

promise = client.queue_declare(queue='test')
client.wait(promise)

print "  [*] Waiting for a message. Press CTRL+C to quit."

consume_promise = client.basic_consume(queue='test')
result = client.wait(consume_promise)
print " [x] Received message %r" % (result,)

client.basic_ack(result)

promise = client.basic_cancel(consume_promise)
client.wait(promise)

promise = client.close()
client.wait(promise)

########NEW FILE########
__FILENAME__ = send
#!/usr/bin/env python

import sys
sys.path.append("..")


import puka

client = puka.Client("amqp://localhost/")

promise = client.connect()
client.wait(promise)

promise = client.queue_declare(queue='test')
client.wait(promise)

promise = client.basic_publish(exchange='', routing_key='test',
                              body="Hello world!")
client.wait(promise)

print " [*] Message sent"

promise = client.queue_declare(queue='test', passive=True)
print " [*] Queue size:", client.wait(promise)['message_count']

promise = client.close()
client.wait(promise)


########NEW FILE########
__FILENAME__ = send_async
#!/usr/bin/env python

import sys
sys.path.append("..")


import puka

def on_connection(promise, result):
    client.queue_declare(queue='test', callback=on_queue_declare)

def on_queue_declare(promise, result):
    client.basic_publish(exchange='', routing_key='test',
                         body="Hello world!",
                         callback=on_basic_publish)

def on_basic_publish(promise, result):
    print " [*] Message sent"
    client.loop_break()

client = puka.Client("amqp://localhost/")
client.connect(callback=on_connection)
client.loop()

promise = client.close()
client.wait(promise)

########NEW FILE########
__FILENAME__ = serialized_declare
#!/usr/bin/env python

import sys
sys.path.append("..")

import logging
FORMAT_CONS = '%(asctime)s %(name)-12s %(levelname)8s\t%(message)s'
logging.basicConfig(level=logging.DEBUG, format=FORMAT_CONS)



import puka

client = puka.Client("amqp://localhost/")

promise = client.connect()
client.wait(promise)

for i in range(1000):
    promise = client.queue_declare(queue='a%04i' % i)
    client.wait(promise)

for i in range(1000):
    promise = client.queue_delete(queue='a%04i' % i)
    client.wait(promise)

promise = client.close()
client.wait(promise)

########NEW FILE########
__FILENAME__ = stress_amqp
#!/usr/bin/env python

import sys
sys.path.append("..")

import puka
import time
import collections

AMQP_URL = "amqp://localhost/"
QUEUE_CNT = 32
BURST_SIZE = 120
QUEUE_SIZE = 1000
BODY_SIZE = 1
PREFETCH_CNT = 1
MSG_HEADERS = {'persistent': False}
PUBACKS = False

counter = 0
counter_t0 = time.time()

class AsyncGeneratorState(object):
    def __init__(self, client, gen):
        self.gen = gen
        self.client = client
        self.promises = collections.defaultdict(list)

        self.waiting_for = self.gen.next()
        self.client.set_callback(self.waiting_for, self.callback_wrapper)

    def callback_wrapper(self, t, result):
        self.promises[t].append(result)
        while self.waiting_for in self.promises:
            result = self.promises[self.waiting_for].pop(0)
            if not self.promises[self.waiting_for]:
                del self.promises[self.waiting_for]
            self.waiting_for = self.gen.send(result)
        self.client.set_callback(self.waiting_for, self.callback_wrapper)

def puka_async_generator(method):
    def wrapper(client, *args, **kwargs):
        AsyncGeneratorState(client, method(client, *args, **kwargs))
        return None
    return wrapper


@puka_async_generator
def worker(client, q, msg_cnt, body, prefetch_cnt, inc, avg):
    result = (yield client.queue_declare(queue=q, durable=True))
    fill = max(msg_cnt - result['message_count'], 0)

    while fill > 0:
        fill -= BURST_SIZE
        for i in xrange(BURST_SIZE):
            promise = client.basic_publish(exchange='', routing_key=q,
                                          body=body, headers=MSG_HEADERS)
        yield promise # Wait only for one in burst (the last one).
        inc(BURST_SIZE)

    consume_promise = client.basic_consume(queue=q, prefetch_count=prefetch_cnt)
    while True:
        msg = (yield consume_promise)
        t0 = time.time()
        yield client.basic_publish(exchange='', routing_key=q,
                             body=body, headers=MSG_HEADERS)
        td = time.time() - t0
        avg(td)
        client.basic_ack(msg)
        inc()


average = average_count = 0.0
def main():
    client = puka.Client(AMQP_URL, pubacks=PUBACKS)
    promise = client.connect()
    client.wait(promise)

    def inc(value=1):
        global counter
        counter += value

    def avg(td):
        global average, average_count
        average += td
        average_count += 1

    for q in ['q%04i' % i for i in range(QUEUE_CNT)]:
        worker(client, q, QUEUE_SIZE, 'a' * BODY_SIZE, PREFETCH_CNT, inc, avg)


    global counter, average, average_count

    print ' [*] loop'
    while True:
        t0 = time.time()
        client.loop(timeout=1.0)
        td = time.time() - t0
        average_count = max(average_count, 1.0)
        print "send: %i  avg: %.3fms " % (counter/td,
                                          (average/average_count)*1000.0)
        counter = average = average_count = 0

if __name__ == '__main__':
    main()

########NEW FILE########
__FILENAME__ = channel
import array
import logging

from . import machine
from spec_exceptions import ChannelError

log = logging.getLogger('puka')



class ChannelCollection(object):
    channel_max = 65535

    def __init__(self):
        self.channels = {}
        self.free_channels = []
        # Channel 0 is a special case.
        self.free_channel_numbers = [0]
        zero_channel = self.new()
        self.free_channels.append( zero_channel )

    def tune_channel_max(self, new_channel_max):
        new_channel_max = new_channel_max if new_channel_max != 0 else 65535
        self.channel_max = min(self.channel_max, new_channel_max)
        self.free_channel_numbers = array.array('H',
                                                xrange(self.channel_max, 0, -1))
        return self.channel_max

    def new(self):
        try:
            number = self.free_channel_numbers.pop()
        except IndexError:
            raise ChannelError('No free channels')
        channel = Channel(number)
        self.channels[number] = channel
        return channel

    def allocate(self, promise, on_channel):
        if self.free_channels:
            channel = self.free_channels.pop()
            channel.promise = promise
            promise.channel = channel
            promise.after_machine_callback = on_channel
        else:
            channel = self.new()
            channel.promise = promise
            promise.channel = channel
            machine.channel_open(promise, on_channel)
        return channel

    def deallocate(self, channel):
        channel.promise.channel = channel.promise = None
        if channel.alive:
            self.free_channels.append( channel )
        else:
            del self.channels[channel.number]
            self.free_channel_numbers.append( channel.number )



class Channel(object):
    alive = False

    def __init__(self, number):
        self.number = number
        self.promise = None
        self._clear_inbound_state()

    def _clear_inbound_state(self):
        self.method_frame = self.props = None
        self.body_chunks = []
        self.body_len = self.body_size = 0


    def inbound_method(self, frame):
        if frame.has_content:
            self.method_frame = frame
        else:
            self._handle_inbound(frame)

    def inbound_props(self, body_size, props):
        self.body_size = body_size
        self.props = props
        if self.body_size == 0: # don't expect body frame
            self.inbound_body('')

    def inbound_body(self, body_chunk):
        self.body_chunks.append( body_chunk )
        self.body_len += len(body_chunk)
        if self.body_len == self.body_size:
            result = self.method_frame
            props = self.props

            result['body'] = ''.join(self.body_chunks)
            result['headers'] = props.get('headers', {})
            # Aint need a reference loop.
            if 'headers' in props:
                del props['headers']
            result['headers'].update( props )

            self._clear_inbound_state()
            return self._handle_inbound(result)

    def _handle_inbound(self, result):
        self.promise.recv_method(result)


########NEW FILE########
__FILENAME__ = client
import functools

from . import connection
from . import machine

def meta_attach_methods(name, bases, cls):
    decorator, list_of_methods = cls['attach_methods']
    for method in list_of_methods:
        cls[method.__name__] = decorator(method)
    return type(name, bases, cls)


def machine_decorator(method):
    @functools.wraps(method)
    def wrapper(*args, **kwargs):
        callback = kwargs.get('callback')
        if callback is not None:
            del kwargs['callback']
        p = method(*args, **kwargs)
        p.user_callback = callback
        p.after_machine()
        return p.number
    return wrapper


class Client(connection.Connection):
    __metaclass__ = meta_attach_methods
    attach_methods = (machine_decorator, [
        machine.queue_declare,
        machine.queue_purge,
        machine.queue_delete,
        machine.basic_publish,
        machine.basic_consume,
        machine.basic_consume_multi,
        machine.basic_cancel,
        machine.basic_qos,
        machine.basic_get,
        machine.exchange_declare,
        machine.exchange_delete,
        machine.exchange_bind,
        machine.exchange_unbind,
        machine.queue_bind,
        machine.queue_unbind,
        ])

    @machine_decorator
    def connect(self):
        return self._connect()

    @machine_decorator
    def close(self):
        return self._close()

    def basic_ack(self, *args, **kwargs):
        machine.basic_ack(self, *args, **kwargs)

    def basic_reject(self, *args, **kwargs):
        machine.basic_reject(self, *args, **kwargs)

########NEW FILE########
__FILENAME__ = connection
import errno
import logging
import select
import socket
import ssl
import struct
import time
import urllib
from . import urlparse

from . import channel
from . import exceptions
from . import machine
from . import simplebuffer
from . import spec
from . import promise

log = logging.getLogger('puka')


class Connection(object):
    frame_max = 131072

    '''
    Constructor of Puka Connection object.

    amqp_url - a url-like address of an AMQP server
    pubacks  - should Puka try to use 'publisher acks' for implementing
               blocking 'publish'. In early days (before RabbitMQ 2.3),
               pubacks weren't available, so Puka had to emulate blocking
               publish using trickery - sending a confirmation message with
               'mandatory' flag and waiting for it being bounced by the
               broker. Possible values:
                   True  - always use pubacks
                   False - never use pubakcs, always emualte them
                   None (default) - auto-detect if pubacks are availalbe
    client_properties - A dictionary of properties to be sent to the
               server.
    heartbeat - basic support for AMQP-level heartbeats (in seconds)
    ssl_parameters - SSL parameters to be used for amqps: connection
               (instance of SslConnectionParameters)
    '''
    def __init__(self, amqp_url='amqp:///', pubacks=None,
                 client_properties=None, heartbeat=0,
                 ssl_parameters=None):
        self.pubacks = pubacks

        self.channels = channel.ChannelCollection()
        self.promises = promise.PromiseCollection(self)

        (self.username, self.password, self.vhost,
            self.host, self.port, self.ssl) = parse_amqp_url(str(amqp_url))

        self.client_properties = client_properties

        self.heartbeat = heartbeat
        self._ssl_parameters = ssl_parameters
        self._needs_ssl_handshake = False

    def _init_buffers(self):
        self.recv_buf = simplebuffer.SimpleBuffer()
        self.recv_need = 8
        self.send_buf = simplebuffer.SimpleBuffer()

    def fileno(self):
        return self.sd.fileno()

    def socket(self):
        return self.sd

    def _connect(self):
        self._handle_read = self._handle_conn_read
        self._init_buffers()

        addrinfo = None
        if socket.has_ipv6:
            try:
                addrinfo = socket.getaddrinfo(
                    self.host, self.port, socket.AF_INET6, socket.SOCK_STREAM)
            except socket.gaierror:
                pass
        if not addrinfo:
            addrinfo = socket.getaddrinfo(
                self.host, self.port, socket.AF_INET, socket.SOCK_STREAM)

        (family, socktype, proto, canonname, sockaddr) = addrinfo[0]
        self.sd = socket.socket(family, socktype, proto)
        set_ridiculously_high_buffers(self.sd)
        set_close_exec(self.sd)
        try:
            self.sd.connect(sockaddr)
        except socket.error, e:
            if e.errno not in (errno.EINPROGRESS, errno.EWOULDBLOCK):
                raise

        self.sd.setblocking(False)
        if self.ssl:
            self.sd = self._wrap_socket(self.sd)
            self._needs_ssl_handshake = True

        return machine.connection_handshake(self)

    def _wrap_socket(self, sock):
        """Wrap the socket for connecting over SSL.
        :rtype: ssl.SSLSocket
        """
        keyfile = None if self._ssl_parameters is None else \
            self._ssl_parameters.keyfile

        certfile = None if self._ssl_parameters is None else \
            self._ssl_parameters.certfile

        ca_certs = None if self._ssl_parameters is None else \
            self._ssl_parameters.ca_certs

        #require_certificate
        cert_reqs = ssl.CERT_NONE
        if ca_certs:
            cert_reqs = ssl.CERT_REQUIRED if \
                self._ssl_parameters.require_certificate \
                else ssl.CERT_OPTIONAL

        return ssl.wrap_socket(sock,
                               do_handshake_on_connect=False,
                               keyfile=keyfile,
                               certfile=certfile,
                               cert_reqs=cert_reqs,
                               ca_certs=ca_certs)

    def _do_ssl_handshake(self, timeout=None):
        """Perform SSL handshaking
        """
        if not self._needs_ssl_handshake:
            return False
        if timeout is not None:
            t1 = time.time() + timeout
        else:
            td = None
            t1 = None

        while True:
            if timeout is not None:
                t0 = time.time()
                td = t1 - t0
                if td < 0:
                    break
            try:
                self.sd.do_handshake()
                self._needs_ssl_handshake = False
                break
            except ssl.SSLError, e:
                if e.args[0] == ssl.SSL_ERROR_WANT_READ:
                    select.select([self.sd], [], [])
                elif e.args[0] == ssl.SSL_ERROR_WANT_WRITE:
                    select.select([], [self.sd], [])
                else:
                    raise

    def on_read(self):
        while True:
            try:
                r = self.sd.recv(Connection.frame_max)
                break
            except ssl.SSLError, e:
                if e.args[0] == ssl.SSL_ERROR_WANT_READ:
                    select.select([self.sd], [], [])
                    continue
                raise
            except socket.error, e:
                if e.errno == errno.EAGAIN:
                    return
                else:
                    raise

        if len(r) == 0:
            # a = self.sd.getsockopt(socket.SOL_SOCKET, socket.SO_ERROR)
            self._shutdown(exceptions.mark_frame(spec.Frame(),
                                                 exceptions.ConnectionBroken()))

        self.recv_buf.write(r)

        if len(self.recv_buf) >= self.recv_need:
            data = self.recv_buf.read()
            offset = 0
            while len(data) - offset >= self.recv_need and self.sd is not None:
                offset, self.recv_need = \
                    self._handle_read(data, offset)
            self.recv_buf.consume(offset)

    def _handle_conn_read(self, data, offset):
        self._handle_read = self._handle_frame_read
        if data[offset:].startswith('AMQP'):
            a,b,c,d = struct.unpack('!BBBB', data[offset+4:offset+4+4])
            self._shutdown(exceptions.mark_frame(
                    spec.Frame(),
                    exceptions.UnsupportedProtocol("%s.%s.%s.%s" % (a,b,c,d))))
            return 0,0
        else:
            return self._handle_frame_read(data, offset)

    def _handle_frame_read(self, data, start_offset):
        offset = start_offset
        if len(data)-start_offset < 8:
            return start_offset, 8
        frame_type, channel, payload_size = \
            struct.unpack_from('!BHI', data, offset)
        offset += 7
        if len(data)-start_offset < 8+payload_size:
            return start_offset, 8+payload_size
        assert data[offset+payload_size] == '\xCE'

        if frame_type == 0x01: # Method frame
            method_id, = struct.unpack_from('!I', data, offset)
            offset += 4
            frame, offset = spec.METHODS[method_id](data, offset)
            self.channels.channels[channel].inbound_method(frame)
        elif frame_type == 0x02: # header frame
            (class_id, body_size) = struct.unpack_from('!HxxQ', data, offset)
            offset += 12
            props, offset = spec.PROPS[class_id](data, offset)
            self.channels.channels[channel].inbound_props(body_size, props)
        elif frame_type == 0x03: # body frame
            body_chunk = str(data[offset : offset+payload_size])
            self.channels.channels[channel].inbound_body(body_chunk)
            offset += len(body_chunk)
        elif frame_type == 0x08: # heartbeat frame
            # One corner of the spec doc says this will be 0x04, most
            # says 0x08 which seems to be what's been implemented by
            # RabbitMQ at least.
            #
            # Got heartbeat, respond with one.
            #
            # It seems likely this logic is slightly incorrect. We're
            # getting a heartbeat because we asked for one from the
            # server. At connection setup it probably asked us for one
            # as well with the same timeout.  We're using the server
            # heartbeat as a trigger instead of setting up a separate
            # heartbeat cycler.
            self._send_frames(channel_number=0, frames=[(0x08, '')])
        else:
            assert False, "Unknown frame type 0x%x" % frame_type

        offset += 1 # '\xCE'
        assert offset == start_offset+8+payload_size
        return offset, 8


    def _send(self, data):
        # Do not try to write straightaway, better wait for more data.
        self.send_buf.write(data)

    def _send_frames(self, channel_number, frames):
        self._send( ''.join([''.join((struct.pack('!BHI',
                                                  frame_type,
                                                  channel_number,
                                                  len(payload)),
                                      payload, '\xCE')) \
                                 for frame_type, payload in frames]) )

    def needs_write(self):
        return bool(self.send_buf)

    def on_write(self):
        if not self.send_buf:  # already shutdown or empty buffer?
            return
        while True:
            try:
                # On windows socket.send blows up if the buffer is too large.
                r = self.sd.send(self.send_buf.read(128*1024))
                break
            except ssl.SSLError, e:
                if e.args[0] == ssl.SSL_ERROR_WANT_WRITE:
                    select.select([], [self.sd], [])
                    continue
                raise
            except socket.error, e:
                if e.errno in (errno.EWOULDBLOCK, errno.ENOBUFS):
                    return
                else:
                    raise
        self.send_buf.consume(r)


    def _tune_frame_max(self, new_frame_max):
        new_frame_max = new_frame_max if new_frame_max != 0 else 2**19
        self.frame_max = min(self.frame_max, new_frame_max)
        return self.frame_max


    def wait(self, promise_numbers, timeout=None, raise_errors=True):
        '''
        Wait for selected promises. Exit after promise runs a callback.
        '''
        if timeout is not None:
            t1 = time.time() + timeout
        else:
            td = None

        if isinstance(promise_numbers, int):
            promise_numbers = [promise_numbers]
        promise_numbers = set(promise_numbers)

        self._do_ssl_handshake(timeout=timeout)

        # Make sure the buffer is flushed if possible before entering
        # the loop. We may return soon, and the user has no way to
        # figure out if the write buffer was flushed or not - (ie: did
        # the wait run select() or not)
        #
        # This is problem is especially painful with regard to
        # async messages, like basic_ack. See #3.
        r, w, e = select.select((self,),
                                (self,) if self.needs_write() else (),
                                (self,),
                                0)
        if r or e:
            self.on_read()
        if w:
            self.on_write()


        while True:
            while True:
                ready = promise_numbers & self.promises.ready
                if not ready:
                    break
                promise_number = ready.pop()
                return self.promises.run_callback(promise_number,
                                                  raise_errors=raise_errors)

            if timeout is not None:
                t0 = time.time()
                td = t1 - t0
                if td < 0:
                    break

            r, w, e = select.select([self],
                                    [self] if self.needs_write() else [],
                                    [self],
                                    td)
            if r or e:
                self.on_read()
            if w:
                self.on_write()
            if not r and not e and not w:
                # timeout
                return None

    def wait_for_any(self):
        return self.loop()

    def wait_for_all(self, promise_list, raise_errors=True):
        for promise in promise_list:
            self.wait(promise, raise_errors=raise_errors)

    def loop(self, timeout=None):
        '''
        Wait for any promise. Block forever.
        '''
        if timeout is not None:
            t1 = time.time() + timeout
        else:
            td = None
        self._loop_break = False

        self._do_ssl_handshake(timeout=timeout)

        while True:
            self.run_any_callbacks()

            if self._loop_break:
                break

            if timeout is not None:
                t0 = time.time()
                td = t1 - t0
                if td < 0:
                    break
            r, w, e = select.select([self],
                                    [self] if self.needs_write() else [],
                                    [self],
                                    td)
            if r or e:
                self.on_read()
            if w:
                self.on_write()

        # Try flushing the write buffer just after the loop. The user
        # has no way to figure out if the buffer was flushed or
        # not. (ie: if the loop() require waiting on for data or not).
        self.on_write()


    def loop_break(self):
        self._loop_break = True

    def run_any_callbacks(self):
        '''
        Run any callbacks, any promises, but do not block.
        '''
        while self.promises.ready:
            [self.promises.run_callback(promise, raise_errors=False) \
                 for promise in list(self.promises.ready)]


    def _shutdown(self, result):
        # Cancel all events.
        for promise in self.promises.all():
            # It's possible that a promise may be already `done` but still not
            # removed. For example due to `refcnt`. In that case don't run
            # callbacks.
            if promise.to_be_released is False:
                promise.done(result)

        # And kill the socket
        try:
            self.sd.shutdown(socket.SHUT_RDWR)
        except socket.error, e:
            if e.errno is not errno.ENOTCONN: raise
        self.sd.close()
        self.sd = None
        # Sending is illegal
        self.send_buf = None

    def _close(self):
        return machine.connection_close(self)

    def set_callback(self, promise_number, callback):
        promise = self.promises.by_number(promise_number)
        promise.user_callback = callback


def parse_amqp_url(amqp_url):
    '''
    >>> parse_amqp_url('amqp:///')
    ('guest', 'guest', '/', 'localhost', 5672, False)
    >>> parse_amqp_url('amqp://a:b@c:1/d')
    ('a', 'b', 'd', 'c', 1, False)
    >>> parse_amqp_url('amqp://g%20uest:g%20uest@host/vho%20st')
    ('g uest', 'g uest', 'vho st', 'host', 5672, False)
    >>> parse_amqp_url('http://asd')
    Traceback (most recent call last):
      ...
    AssertionError: Only amqp:// protocol supported.
    >>> parse_amqp_url('amqp://host/%2f')
    ('guest', 'guest', '/', 'host', 5672, False)
    >>> parse_amqp_url('amqp://host/%2fabc')
    ('guest', 'guest', '/abc', 'host', 5672, False)
    >>> parse_amqp_url('amqp://host/')
    ('guest', 'guest', '/', 'host', 5672, False)
    >>> parse_amqp_url('amqp://host')
    ('guest', 'guest', '/', 'host', 5672, False)
    >>> parse_amqp_url('amqp://user:pass@host:10000/vhost')
    ('user', 'pass', 'vhost', 'host', 10000, False)
    >>> parse_amqp_url('amqp://user%61:%61pass@ho%61st:10000/v%2fhost')
    ('usera', 'apass', 'v/host', 'hoast', 10000, False)
    >>> parse_amqp_url('amqp://')
    ('guest', 'guest', '/', 'localhost', 5672, False)
    >>> parse_amqp_url('amqp://:@/') # this is a violation, vhost should be=''
    ('', '', '/', 'localhost', 5672, False)
    >>> parse_amqp_url('amqp://user@/')
    ('user', 'guest', '/', 'localhost', 5672, False)
    >>> parse_amqp_url('amqp://user:@/')
    ('user', '', '/', 'localhost', 5672, False)
    >>> parse_amqp_url('amqp://host')
    ('guest', 'guest', '/', 'host', 5672, False)
    >>> parse_amqp_url('amqp:///vhost')
    ('guest', 'guest', 'vhost', 'localhost', 5672, False)
    >>> parse_amqp_url('amqp://host/')
    ('guest', 'guest', '/', 'host', 5672, False)
    >>> parse_amqp_url('amqp://host/%2f%2f')
    ('guest', 'guest', '//', 'host', 5672, False)
    >>> parse_amqp_url('amqp://[::1]')
    ('guest', 'guest', '/', '::1', 5672, False)
    >>> parse_amqp_url('amqps://user:pass@host:10000/vhost')
    ('user', 'pass', 'vhost', 'host', 10000, True)
    '''
    assert amqp_url.startswith('amqp://') or \
        amqp_url.startswith('amqps://'), \
        "Only amqp:// and amqps:// protocols are supported."
    # urlsplit doesn't know how to parse query when scheme is amqp,
    # we need to pretend we're http'
    o = urlparse.urlsplit('http' + amqp_url[len('amqp'):])
    username = urllib.unquote(o.username) if o.username is not None else 'guest'
    password = urllib.unquote(o.password) if o.password is not None else 'guest'

    path = o.path[1:] if o.path.startswith('/') else o.path
    # We do not support empty vhost case. Empty vhost is treated as
    # '/'. This is mostly for backwards compatibility, and the fact
    # that empty vhost is not very useful.
    vhost = urllib.unquote(path) if path else '/'
    host = urllib.unquote(o.hostname) if o.hostname else 'localhost'
    port = o.port if o.port else 5672
    ssl = o.scheme == 'https'
    return (username, password, vhost, host, port, ssl)

def set_ridiculously_high_buffers(sd):
    '''
    Set large tcp/ip buffers kernel. Let's move the complexity
    to the operating system! That's a wonderful idea!
    '''
    for flag in [socket.SO_SNDBUF, socket.SO_RCVBUF]:
        for i in range(10):
            bef = sd.getsockopt(socket.SOL_SOCKET, flag)
            try:
                sd.setsockopt(socket.SOL_SOCKET, flag, bef*2)
            except socket.error:
                break
            aft = sd.getsockopt(socket.SOL_SOCKET, flag)
            if aft <= bef or aft >= 1024*1024:
                break

def set_close_exec(fd):
    '''
    exec functions (e.g. subprocess.Popen) by default force the child
    process to inherit all file handles which can result in stuck
    connections and unacknowledged messages. Setting FD_CLOEXEC forces
    the handles to be closed first.
    '''
    try:
        import fcntl
        flags = fcntl.fcntl(fd, fcntl.F_GETFD)
        fcntl.fcntl(fd, fcntl.F_SETFD, flags | fcntl.FD_CLOEXEC)
    except ImportError:
        pass


class SslConnectionParameters(object):
    def __init__(self):
        self._certfile = None
        self._keyfile = None
        self._ca_certs = None
        self._require_certificate = True

    @property
    def certfile(self):
        return self._certfile

    @certfile.setter
    def certfile(self, value):
        self._certfile = value

    @property
    def keyfile(self):
        return self._keyfile

    @keyfile.setter
    def keyfile(self, value):
        self._keyfile = value

    @property
    def ca_certs(self):
        return self._ca_certs

    @ca_certs.setter
    def ca_certs(self, value):
        self._ca_certs = value

    @property
    def require_certificate(self):
        return self._require_certificate

    @require_certificate.setter
    def require_certificate(self, value):
        self._require_certificate = value

########NEW FILE########
__FILENAME__ = exceptions
import socket
from . import spec_exceptions

class ConnectionBroken(socket.error): pass
class UnsupportedProtocol(socket.error): pass


def exception_from_frame(result):
    reply_code = result.get('reply_code', 0)
    if reply_code in spec_exceptions.ERRORS:
        return spec_exceptions.ERRORS[reply_code](result)
    return spec_exceptions.AMQPError(result)

def mark_frame(result, exception=None):
    result.is_error = True
    if exception is None:
        result.exception = exception_from_frame(result)
    else:
        result.exception = exception
    return result

########NEW FILE########
__FILENAME__ = machine
import copy
import logging

from . import exceptions
from . import spec
from . import ordereddict

log = logging.getLogger('puka')

def _nothing(t):
    pass

####
def connection_handshake(conn):
    # Bypass conn._send, we want the socket to be writable first.
    conn.send_buf.write(spec.PREAMBLE)
    t = conn.promises.new(_connection_handshake, reentrant=True)
    conn.x_connection_promise = t
    return t

def _connection_handshake(t):
    assert t.channel.number == 0
    t.register(spec.METHOD_CONNECTION_START, _connection_start)

def _connection_start(t, result):
    # log.info("Connected to %r", result['server_properties'])
    assert 'PLAIN' in result['mechanisms'].split(), "Only PLAIN auth supported."
    response = '\0%s\0%s' % (t.conn.username, t.conn.password)
    scapa = result['server_properties'].get('capabilities', {})
    ccapa = {}
    if scapa.get('consumer_cancel_notify'):
        ccapa['consumer_cancel_notify'] = True

    properties = {'product': 'Puka', 'capabilities': ccapa}
    if t.conn.client_properties is not None:
        properties.update(t.conn.client_properties)

    frames = spec.encode_connection_start_ok(properties,
                                    'PLAIN', response, 'en_US')
    t.register(spec.METHOD_CONNECTION_TUNE, _connection_tune)
    t.send_frames(frames)
    t.x_cached_result = result
    t.conn.x_server_props = result['server_properties']
    try:
        t.conn.x_server_version = \
            map(int, t.conn.x_server_props['version'].split('.'))
    except ValueError:
        t.conn.x_server_version = (Ellipsis,)
    if t.conn.pubacks is None:
        t.conn.x_pubacks = scapa.get('publisher_confirms', False)
    else:
        t.conn.x_pubacks = t.conn.pubacks


def _connection_tune(t, result):
    frame_max = t.conn._tune_frame_max(result['frame_max'])
    channel_max = t.conn.channels.tune_channel_max(result['channel_max'])

    t.register(spec.METHOD_CONNECTION_OPEN_OK, _connection_open_ok)
    f1 = spec.encode_connection_tune_ok(channel_max, frame_max, t.conn.heartbeat)
    f2 = spec.encode_connection_open(t.conn.vhost)
    t.send_frames(f1 + f2)

def _connection_open_ok(ct, result):
    ct.register(spec.METHOD_CONNECTION_CLOSE, _connection_close)
    # Never free the promise and channel.
    ct.ping(ct.x_cached_result)
    ct.conn.x_connection_promise = ct
    publish_promise(ct.conn)


def publish_promise(conn):
    if conn.x_pubacks:
        pt = conn.promises.new(_pt_channel_open_ok_puback)
    else:
        pt = conn.promises.new(_pt_channel_open_ok)
    pt.x_async_enabled = False
    pt.x_delivery_tag = 1
    pt.x_delivery_tag_shift = 0
    pt.x_async_inflight = ordereddict.OrderedDict()
    pt.x_async_next = []
    conn.x_publish_promise = pt

def _pt_channel_open_ok_puback(pt, _result=None):
    pt.send_frames( spec.encode_confirm_select() )
    pt.register(spec.METHOD_CONFIRM_SELECT_OK, _pt_channel_open_ok)
    pt.register(spec.METHOD_BASIC_ACK, _pt_basic_ack)

def _pt_channel_open_ok(pt, _result=None):
    pt.x_async_enabled = True
    pt.register(spec.METHOD_CHANNEL_CLOSE, _pt_channel_close)
    pt.register(spec.METHOD_BASIC_RETURN, _pt_basic_return)
    # Send remaining messages.
    _pt_async_flush(pt)

def fix_basic_publish_headers(headers):
    assert 'headers' not in headers # That's not a good idea.
    nheaders = {}
    nheaders.update(headers)
    return nheaders

def basic_publish(conn, exchange, routing_key='', mandatory=False,
                  headers={}, body=''):
    pt = conn.x_publish_promise
    delivery_tag = pt.x_delivery_tag
    pt.x_delivery_tag += 1

    nheaders = fix_basic_publish_headers(headers)
    assert 'x-puka-delivery-tag' not in nheaders
    nheaders['x-puka-delivery-tag'] = delivery_tag

    frames = spec.encode_basic_publish(exchange, routing_key, mandatory,
                                       False, nheaders, body,
                                       conn.frame_max)
    if not conn.x_pubacks:
        # Construct ack packet.
        eheaders = {'x-puka-delivery-tag': delivery_tag, 'x-puka-footer': True}
        frames = frames + \
                 spec.encode_basic_publish('', '', True, False, eheaders,
                                                '', conn.frame_max)
    t = conn.promises.new(_nothing, no_channel=True)
    pt.x_async_next.append( (delivery_tag, t, frames) )
    _pt_async_flush(pt)
    return t

def _pt_async_flush(pt):
    if pt.x_async_enabled:
        frames_acc = []
        for delivery_tag, t, frames in pt.x_async_next:
            pt.x_async_inflight[delivery_tag] = t
            frames_acc.extend( frames )
        pt.x_async_next = []
        pt.send_frames(frames_acc)

def _pt_basic_return(pt, result):
    pt.register(spec.METHOD_BASIC_RETURN, _pt_basic_return)
    delivery_tag = result['headers']['x-puka-delivery-tag']
    if delivery_tag in pt.x_async_inflight:
        t = pt.x_async_inflight.pop(delivery_tag)
        if 'x-puka-footer' in result['headers']: # ok
            t.done(spec.Frame())
        else: # return
            exceptions.mark_frame(result)
            t.done(result)

def _pt_basic_ack(pt, result):
    pt.register(spec.METHOD_BASIC_ACK, _pt_basic_ack)
    delivery_tag = result['delivery_tag'] + pt.x_delivery_tag_shift
    if delivery_tag in pt.x_async_inflight:
        if result['multiple'] == True:
            delivery_tags = []
            for key in pt.x_async_inflight.iterkeys():
                if key <= delivery_tag:
                    delivery_tags.append(key)
                else:
                    break
        else:
            delivery_tags = [delivery_tag]
        for delivery_tag in delivery_tags:
            t = pt.x_async_inflight.pop(delivery_tag)
            t.done(spec.Frame())


def _pt_channel_close(pt, result):
    pt.x_async_enabled = False
    pt.x_delivery_tag_shift = pt.x_delivery_tag
    # Start off with reestablishing the channel
    if pt.conn.x_pubacks:
        pt.x_delivery_tag_shift -= 1 # starting from 1.
        pt.register(spec.METHOD_CHANNEL_OPEN_OK, _pt_channel_open_ok_puback)
    else:
        pt.register(spec.METHOD_CHANNEL_OPEN_OK, _pt_channel_open_ok)
    pt.send_frames( spec.encode_channel_close_ok() +
                    spec.encode_channel_open(''))
    # All the publishes are marked as failed.
    exceptions.mark_frame(result)
    for t in pt.x_async_inflight.itervalues():
        t.done(result)
    pt.x_async_inflight.clear()


def _connection_close(t, result):
    exceptions.mark_frame(result)
    t.ping(result)
    # Explode, kill everything.
    log.error('Connection killed with %r', result)
    t.conn._shutdown(result)

def connection_close(conn):
    t = conn.x_connection_promise
    t.register(spec.METHOD_CONNECTION_CLOSE_OK, _connection_close_ok)
    t.send_frames(spec.encode_connection_close(200, '', 0, 0))
    return t

def _connection_close_ok(t, result):
    # Ping this promise with success.
    t.ping(copy.copy(result))
    # Cancel all our promises with failure.
    exceptions.mark_frame(result)
    t.conn._shutdown(result)


####
def channel_open(t, callback):
    t.register(spec.METHOD_CHANNEL_OPEN_OK, _channel_open_ok)
    t.x_callback = callback
    t.send_frames( spec.encode_channel_open('') )

def _channel_open_ok(t, result):
    t.x_callback()


####
def queue_declare(conn, queue='', durable=False, exclusive=False,
                  auto_delete=False, passive=False, arguments={}):
    t = conn.promises.new(_queue_declare)
    t.x_frames = spec.encode_queue_declare(queue, passive, durable, exclusive,
                                           auto_delete, arguments)
    return t

def _queue_declare(t, result=None):
    t.register(spec.METHOD_QUEUE_DECLARE_OK, _queue_declare_ok)
    t.send_frames(t.x_frames)

def _queue_declare_ok(t, result):
    t.done(result)


####
def basic_consume(conn, queue, prefetch_count=0, no_local=False, no_ack=False,
                  exclusive=False, arguments={}):
    q = {'queue': queue,
         'no_local': no_local,
         'exclusive': exclusive,
         'arguments': arguments,
         }
    return basic_consume_multi(conn, [q], prefetch_count, no_ack)

####
def basic_consume_multi(conn, queues, prefetch_count=0, no_ack=False):
    t = conn.promises.new(_bcm_basic_qos, reentrant=True)
    t.x_frames = spec.encode_basic_qos(0, prefetch_count, False)
    t.x_consumes = []
    for i, item in enumerate(queues):
        if isinstance(item, str):
            queue = item
            no_local = exclusive = False
            arguments = {}
            consumer_tag = '%s.%s.%s' % (t.number, i, '')
        else:
            queue = item['queue']
            no_local = item.get('no_local', False)
            exclusive = item.get('exclusive', False)
            arguments = item.get('arguments', {})
            consumer_tag = '%s.%s.%s' % (t.number, i, item.get('consumer_tag', ''))
        t.x_consumes.append( (queue, spec.encode_basic_consume(
                    queue, consumer_tag, no_local, no_ack, exclusive, arguments)) )
    t.x_no_ack = no_ack
    t.x_consumer_tag = {}
    t.register(spec.METHOD_BASIC_DELIVER, _bcm_basic_deliver)
    t.register(spec.METHOD_BASIC_CANCEL, _bcm_basic_cancel)
    return t

def _bcm_basic_qos(t):
    t.register(spec.METHOD_BASIC_QOS_OK, _bcm_basic_qos_ok)
    t.send_frames(t.x_frames)

def _bcm_basic_qos_ok(t, result):
    _bcm_send_basic_consume(t)

def _bcm_send_basic_consume(t):
    t.register(spec.METHOD_BASIC_CONSUME_OK, _bcm_basic_consume_ok)
    t.x_queue, frames = t.x_consumes.pop()
    t.send_frames(frames)

def _bcm_basic_consume_ok(t, consume_result):
    t.x_consumer_tag[t.x_queue] = consume_result['consumer_tag']
    if t.x_consumes:
        _bcm_send_basic_consume(t)

def _bcm_basic_deliver(t, msg_result):
    t.register(spec.METHOD_BASIC_DELIVER, _bcm_basic_deliver)
    msg_result['promise_number'] = t.number
    if t.x_no_ack is False:
        t.refcnt_inc()
    t.ping(msg_result)

def _bcm_basic_cancel(ct, result):
    ct.register(spec.METHOD_BASIC_CANCEL, _generic_callback_nop)
    ct.x_ct = ct
    _basic_cancel(ct)

##
def basic_ack(conn, msg_result):
    t = conn.promises.by_number(msg_result['promise_number'])
    t.send_frames( spec.encode_basic_ack(msg_result['delivery_tag'], False) )
    assert t.x_no_ack is False
    t.refcnt_dec()
    return t

##
def basic_reject(conn, msg_result, requeue=True):
    t = conn.promises.by_number(msg_result['promise_number'])
    t.send_frames(spec.encode_basic_reject(msg_result['delivery_tag'], requeue))
    assert t.x_no_ack is False
    t.refcnt_dec()
    return t

##
def basic_qos(conn, consume_promise, prefetch_count=0):
    # TODO: race?
    t = conn.promises.new(_basic_qos, no_channel=True)
    t.x_ct = conn.promises.by_number(consume_promise)
    t.x_frames = spec.encode_basic_qos(0, prefetch_count, False)
    return t

def _basic_qos(t):
    ct = t.x_ct
    ct.register(spec.METHOD_BASIC_QOS_OK, _basic_qos_ok)
    ct.send_frames( t.x_frames )
    ct.x_qos_promise = t

def _basic_qos_ok(ct, result):
    t = ct.x_qos_promise
    t.done(result)

##
def basic_cancel(conn, consume_promise):
    # TODO: race?
    t = conn.promises.new(_basic_cancel, no_channel=True)
    t.x_ct = conn.promises.by_number(consume_promise)
    return t

def _basic_cancel(t):
    t.x_ct.x_mt = t
    _basic_cancel_one(t.x_ct)

def _basic_cancel_one(ct):
    consumer_tag = ct.x_consumer_tag.pop(ct.x_consumer_tag.keys()[0])
    ct.register(spec.METHOD_BASIC_CANCEL_OK, _basic_cancel_ok)
    ct.send_frames( spec.encode_basic_cancel(consumer_tag) )

def _basic_cancel_ok(ct, result):
    if ct.x_consumer_tag:
        _basic_cancel_one(ct)
    else:
        ct.x_mt.done(result)
        if ct != ct.x_mt:
            ct.done(None, no_callback=True)
        ct.x_mt = None
        ct.refcnt_clear()

####
def basic_get(conn, queue, no_ack=False):
    t = conn.promises.new(_basic_get)
    t.x_frames = spec.encode_basic_get(queue, no_ack)
    t.x_no_ack = no_ack
    return t

def _basic_get(t):
    t.register(spec.METHOD_BASIC_GET_OK, _basic_get_ok)
    t.register(spec.METHOD_BASIC_GET_EMPTY, _basic_get_empty)
    t.send_frames(t.x_frames)

def _basic_get_ok(t, msg_result):
    msg_result['promise_number'] = t.number
    if t.x_no_ack is False:
        t.refcnt_inc()
    t.done(msg_result)

def _basic_get_empty(t, result):
    result['empty'] = True
    t.done(result)


####
def exchange_declare(conn, exchange, type='direct', durable=False,
                     auto_delete=False, arguments={}):
    t = conn.promises.new(_exchange_declare)

    t.x_frames = spec.encode_exchange_declare(exchange, type, False, durable,
                                              auto_delete, False, arguments)
    return t

def _exchange_declare(t, result=None):
    t.register(spec.METHOD_EXCHANGE_DECLARE_OK, _exchange_declare_ok)
    t.send_frames(t.x_frames)

def _exchange_declare_ok(t, result):
    t.done(result)


####
def _generic_callback(t):
    t.register(t.x_method, _generic_callback_ok)
    t.send_frames(t.x_frames)

def _generic_callback_ok(t, result):
    t.done(result)

def _generic_callback_nop(t, result):
    pass

####
def exchange_delete(conn, exchange, if_unused=False):
    t = conn.promises.new(_generic_callback)
    t.x_method = spec.METHOD_EXCHANGE_DELETE_OK
    t.x_frames = spec.encode_exchange_delete(exchange, if_unused)
    return t

def exchange_bind(conn, destination, source, routing_key='', arguments={}):
    t = conn.promises.new(_generic_callback)
    t.x_method = spec.METHOD_EXCHANGE_BIND_OK
    t.x_frames = spec.encode_exchange_bind(destination, source, routing_key,
                                           arguments)
    return t

def exchange_unbind(conn, destination, source, routing_key='', arguments={}):
    t = conn.promises.new(_generic_callback)
    t.x_method = spec.METHOD_EXCHANGE_UNBIND_OK
    t.x_frames = spec.encode_exchange_unbind(destination, source, routing_key,
                                             arguments)
    return t

def queue_delete(conn, queue, if_unused=False, if_empty=False):
    t = conn.promises.new(_generic_callback)
    t.x_method = spec.METHOD_QUEUE_DELETE_OK
    t.x_frames = spec.encode_queue_delete(queue, if_unused, if_empty)
    return t

def queue_purge(conn, queue):
    t = conn.promises.new(_generic_callback)
    t.x_method = spec.METHOD_QUEUE_PURGE_OK
    t.x_frames = spec.encode_queue_purge(queue)
    return t

def queue_bind(conn, queue, exchange, routing_key='', arguments={}):
    t = conn.promises.new(_generic_callback)
    t.x_method = spec.METHOD_QUEUE_BIND_OK
    t.x_frames = spec.encode_queue_bind(queue, exchange, routing_key,
                                        arguments)
    return t

def queue_unbind(conn, queue, exchange, routing_key='', arguments={}):
    t = conn.promises.new(_generic_callback)
    t.x_method = spec.METHOD_QUEUE_UNBIND_OK
    t.x_frames = spec.encode_queue_unbind(queue, exchange, routing_key,
                                          arguments)
    return t


########NEW FILE########
__FILENAME__ = ordereddict
# Copyright (c) 2009 Raymond Hettinger
#
# Permission is hereby granted, free of charge, to any person
# obtaining a copy of this software and associated documentation files
# (the "Software"), to deal in the Software without restriction,
# including without limitation the rights to use, copy, modify, merge,
# publish, distribute, sublicense, and/or sell copies of the Software,
# and to permit persons to whom the Software is furnished to do so,
# subject to the following conditions:
#
#     The above copyright notice and this permission notice shall be
#     included in all copies or substantial portions of the Software.
#
#     THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND,
#     EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES
#     OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND
#     NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT
#     HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY,
#     WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING
#     FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR
#     OTHER DEALINGS IN THE SOFTWARE.

from UserDict import DictMixin

class OrderedDict(dict, DictMixin):

    def __init__(self, *args, **kwds):
        if len(args) > 1:
            raise TypeError('expected at most 1 arguments, got %d' % len(args))
        try:
            self.__end
        except AttributeError:
            self.clear()
        self.update(*args, **kwds)

    def clear(self):
        self.__end = end = []
        end += [None, end, end]         # sentinel node for doubly linked list
        self.__map = {}                 # key --> [key, prev, next]
        dict.clear(self)

    def __setitem__(self, key, value):
        if key not in self:
            end = self.__end
            curr = end[1]
            curr[2] = end[1] = self.__map[key] = [key, curr, end]
        dict.__setitem__(self, key, value)

    def __delitem__(self, key):
        dict.__delitem__(self, key)
        key, prev, next = self.__map.pop(key)
        prev[2] = next
        next[1] = prev

    def __iter__(self):
        end = self.__end
        curr = end[2]
        while curr is not end:
            yield curr[0]
            curr = curr[2]

    def __reversed__(self):
        end = self.__end
        curr = end[1]
        while curr is not end:
            yield curr[0]
            curr = curr[1]

    def popitem(self, last=True):
        if not self:
            raise KeyError('dictionary is empty')
        if last:
            key = reversed(self).next()
        else:
            key = iter(self).next()
        value = self.pop(key)
        return key, value

    def __reduce__(self):
        items = [[k, self[k]] for k in self]
        tmp = self.__map, self.__end
        del self.__map, self.__end
        inst_dict = vars(self).copy()
        self.__map, self.__end = tmp
        if inst_dict:
            return (self.__class__, (items,), inst_dict)
        return self.__class__, (items,)

    def keys(self):
        return list(self)

    setdefault = DictMixin.setdefault
    update = DictMixin.update
    pop = DictMixin.pop
    values = DictMixin.values
    items = DictMixin.items
    iterkeys = DictMixin.iterkeys
    itervalues = DictMixin.itervalues
    iteritems = DictMixin.iteritems

    def __repr__(self):
        if not self:
            return '%s()' % (self.__class__.__name__,)
        return '%s(%r)' % (self.__class__.__name__, self.items())

    def copy(self):
        return self.__class__(self)

    @classmethod
    def fromkeys(cls, iterable, value=None):
        d = cls()
        for key in iterable:
            d[key] = value
        return d

    def __eq__(self, other):
        if isinstance(other, OrderedDict):
            if len(self) != len(other):
                return False
            for p, q in  zip(self.items(), other.items()):
                if p != q:
                    return False
            return True
        return dict.__eq__(self, other)

    def __ne__(self, other):
        return not self == other

########NEW FILE########
__FILENAME__ = poll
import select

def loop(clients):
    while True:
        for c in clients:
            c.run_any_callbacks()

        rfds = clients
        wfds = [c for c in clients if c.needs_write()]
        r, w, e = select.select(rfds, wfds, rfds)

        for c in r:
            c.on_read()
        for c in w:
            c.on_write()

########NEW FILE########
__FILENAME__ = promise
import logging

from . import channel
from . import spec
from . import exceptions

log = logging.getLogger('puka')



class PromiseCollection(object):
    def __init__(self, conn):
        self.conn = conn
        self._promises = {}
        self.promise_number = 1
        self.ready = set()

    def new(self, on_channel, **kwargs):
        number = self.promise_number
        self.promise_number += 1
        promise = Promise(self.conn, number, on_channel, **kwargs)
        self._promises[number] = promise
        return promise

    def free(self, promise):
        del self._promises[promise.number]

    def mark_ready(self, promise):
        self.ready.add( promise.number )

    def unmark_ready(self, promise):
        self.ready.remove( promise.number )

    def run_callback(self, number, **kwargs):
        return self._promises[number].run_callback(**kwargs)

    def by_number(self, number):
        return self._promises[number]

    def all(self):
        return self._promises.values()


class Promise(object):
    to_be_released = False
    delay_release = None
    user_callback = None
    after_machine_callback = None
    refcnt = 0

    def __init__(self, conn, number, on_channel, reentrant=False,
                 no_channel=False):
        self.number = number
        self.conn = conn
        self.on_channel = on_channel
        self.reentrant = reentrant

        self.methods = {}
        self.callbacks = []

        if not no_channel:
            self.conn.channels.allocate(self, self._on_channel)
        else:
            self.channel = None
            self.after_machine_callback = self._on_channel

    def restore_error_handler(self):
        self.register(spec.METHOD_CHANNEL_CLOSE, self._on_channel_close)

    def _on_channel(self):
        if self.channel:
            self.channel.alive = True
        self.restore_error_handler()
        self.on_channel(self)

    def _on_channel_close(self, _t, result):
        # log.warn('channel %i died %r', self.channel.number, result)
        exceptions.mark_frame(result)
        self.send_frames(spec.encode_channel_close_ok())
        if self.channel:
            self.channel.alive = False
        self.done(result)

    def recv_method(self, result):
        # log.debug('#%i recv_method %r', self.number, result)
        # In this order, to allow callback to re-register to the same method.
        callback = self.methods[result.method_id]
        del self.methods[result.method_id]
        callback(self, result)

    def register(self, method_id, callback):
        self.methods[method_id] = callback

    def unregister(self, method_id):
        del self.methods[method_id]


    def send_frames(self, frames):
        self.conn._send_frames(self.channel.number, frames)


    def done(self, result, delay_release=None, no_callback=False):
        # log.debug('#%i done %r', self.number, result)
        assert self.to_be_released == False
        if not self.reentrant:
            assert len(self.callbacks) == 0
        if not no_callback:
            self.callbacks.append( (self.user_callback, result) )
        else:
            self.callbacks.append( (None, result) )
        self.conn.promises.mark_ready(self)
        self.to_be_released = True
        self.delay_release = delay_release
        self.methods.clear()
        self.restore_error_handler()

    def ping(self, result):
        assert self.to_be_released == False
        assert self.reentrant
        self.callbacks.append( (self.user_callback, result) )
        self.conn.promises.mark_ready(self)


    def run_callback(self, raise_errors=True):
        user_callback, result = self.callbacks.pop(0)
        if not self.callbacks:
            self.conn.promises.unmark_ready(self)
        if user_callback:
            user_callback(self.number, result)
            # We may be already freed now.
            # (consider basic_get + basic_ack inside callback)

        self.maybe_release()
        if raise_errors and result.is_error:
            raise result.exception
        return result


    def after_machine(self):
        if self.after_machine_callback:
            self.after_machine_callback()
            self.after_machine_callback = None

    def refcnt_inc(self):
        self.refcnt += 1

    def refcnt_dec(self):
        assert self.refcnt > 0
        self.refcnt -= 1
        if self.refcnt == 0:
            self.maybe_release()

    def refcnt_clear(self):
        self.refcnt = 0

    def maybe_release(self):
        # If not released yet, not used by callbacks, and not refcounted.
        if ( self.number is not None and not self.callbacks and
             self.to_be_released and self.refcnt == 0):
            self._release()

    def _release(self):
        # Release channel and unlink self.
        if self.delay_release is None:
            if self.channel:
                self.conn.channels.deallocate(self.channel)
            self.conn.promises.free(self)
        elif self.delay_release is Ellipsis:
            # Never free.
            pass
        else:
            # TODO:
            print "Unable to free channel %i (promise %i)" % \
                (self.channel.number, self.number)
        self.number = None

########NEW FILE########
__FILENAME__ = simplebuffer
import os
try:
    import cStringIO as StringIO
except ImportError:
    import StringIO

# Python 2.4 support: os lacks SEEK_END and friends
try:
    getattr(os, "SEEK_END")
except AttributeError:
    os.SEEK_SET, os.SEEK_CUR, os.SEEK_END = range(3)


class SimpleBuffer(object):
    """
    >>> b = SimpleBuffer()
    >>> b.write('abcdef')
    >>> b.read(3)
    'abc'
    >>> b.consume(3)
    >>> b.write('z')
    >>> b.read()
    'defz'
    >>> b.read()
    'defz'
    >>> b.read(0)
    ''
    >>> repr(b)
    "<SimpleBuffer of 4 bytes, 7 total size, 'defz'>"
    >>> str(b)
    "<SimpleBuffer of 4 bytes, 7 total size, 'defz'>"
    >>> len(b)
    4
    >>> bool(b)
    True
    >>> b.flush()
    >>> len(b)
    0
    >>> bool(b)
    False
    >>> b.read(1)
    ''
    >>> b.write('a'*524288)
    >>> b.flush() # run GC code
    """
    def __init__(self):
        self.buf = StringIO.StringIO()
        self.size = 0
        self.offset = 0

    def write(self, data):
        self.buf.write(data)
        self.size += len(data)

    def read(self, size=None):
        self.buf.seek(self.offset)

        if size is None:
            data = self.buf.read()
        else:
            data = self.buf.read(size)

        self.buf.seek(0, os.SEEK_END)
        return data

    def consume(self, size):
        self.offset += size
        self.size -= size
        # GC old StringIO instance and free memory used by it.
        if self.size == 0 and self.offset > 524288:
            self.buf.close()
            self.buf = StringIO.StringIO()
            self.offset = 0

    def flush(self):
        self.consume(self.size)


    def __nonzero__(self):
        return self.size > 0

    def __len__(self):
        return self.size

    def __str__(self):
        return self.__repr__()

    def __repr__(self):
        return '<SimpleBuffer of %i bytes, %i total size, %r%s>' % \
                    (self.size, self.size + self.offset, self.read(16),
                     (self.size > 16) and '...' or '')

########NEW FILE########
__FILENAME__ = spec
# Autogenerated - do not edit
import calendar
import datetime
from struct import pack, unpack_from

from . import table


PREAMBLE = 'AMQP\x00\x00\x09\x01'

METHOD_CONNECTION_START         = 0x000A000A 	# 10,10 655370
METHOD_CONNECTION_START_OK      = 0x000A000B 	# 10,11 655371
METHOD_CONNECTION_SECURE        = 0x000A0014 	# 10,20 655380
METHOD_CONNECTION_SECURE_OK     = 0x000A0015 	# 10,21 655381
METHOD_CONNECTION_TUNE          = 0x000A001E 	# 10,30 655390
METHOD_CONNECTION_TUNE_OK       = 0x000A001F 	# 10,31 655391
METHOD_CONNECTION_OPEN          = 0x000A0028 	# 10,40 655400
METHOD_CONNECTION_OPEN_OK       = 0x000A0029 	# 10,41 655401
METHOD_CONNECTION_CLOSE         = 0x000A0032 	# 10,50 655410
METHOD_CONNECTION_CLOSE_OK      = 0x000A0033 	# 10,51 655411
METHOD_CHANNEL_OPEN             = 0x0014000A 	# 20,10 1310730
METHOD_CHANNEL_OPEN_OK          = 0x0014000B 	# 20,11 1310731
METHOD_CHANNEL_FLOW             = 0x00140014 	# 20,20 1310740
METHOD_CHANNEL_FLOW_OK          = 0x00140015 	# 20,21 1310741
METHOD_CHANNEL_CLOSE            = 0x00140028 	# 20,40 1310760
METHOD_CHANNEL_CLOSE_OK         = 0x00140029 	# 20,41 1310761
METHOD_EXCHANGE_DECLARE         = 0x0028000A 	# 40,10 2621450
METHOD_EXCHANGE_DECLARE_OK      = 0x0028000B 	# 40,11 2621451
METHOD_EXCHANGE_DELETE          = 0x00280014 	# 40,20 2621460
METHOD_EXCHANGE_DELETE_OK       = 0x00280015 	# 40,21 2621461
METHOD_EXCHANGE_BIND            = 0x0028001E 	# 40,30 2621470
METHOD_EXCHANGE_BIND_OK         = 0x0028001F 	# 40,31 2621471
METHOD_EXCHANGE_UNBIND          = 0x00280028 	# 40,40 2621480
METHOD_EXCHANGE_UNBIND_OK       = 0x00280033 	# 40,51 2621491
METHOD_QUEUE_DECLARE            = 0x0032000A 	# 50,10 3276810
METHOD_QUEUE_DECLARE_OK         = 0x0032000B 	# 50,11 3276811
METHOD_QUEUE_BIND               = 0x00320014 	# 50,20 3276820
METHOD_QUEUE_BIND_OK            = 0x00320015 	# 50,21 3276821
METHOD_QUEUE_PURGE              = 0x0032001E 	# 50,30 3276830
METHOD_QUEUE_PURGE_OK           = 0x0032001F 	# 50,31 3276831
METHOD_QUEUE_DELETE             = 0x00320028 	# 50,40 3276840
METHOD_QUEUE_DELETE_OK          = 0x00320029 	# 50,41 3276841
METHOD_QUEUE_UNBIND             = 0x00320032 	# 50,50 3276850
METHOD_QUEUE_UNBIND_OK          = 0x00320033 	# 50,51 3276851
METHOD_BASIC_QOS                = 0x003C000A 	# 60,10 3932170
METHOD_BASIC_QOS_OK             = 0x003C000B 	# 60,11 3932171
METHOD_BASIC_CONSUME            = 0x003C0014 	# 60,20 3932180
METHOD_BASIC_CONSUME_OK         = 0x003C0015 	# 60,21 3932181
METHOD_BASIC_CANCEL             = 0x003C001E 	# 60,30 3932190
METHOD_BASIC_CANCEL_OK          = 0x003C001F 	# 60,31 3932191
METHOD_BASIC_PUBLISH            = 0x003C0028 	# 60,40 3932200
METHOD_BASIC_RETURN             = 0x003C0032 	# 60,50 3932210
METHOD_BASIC_DELIVER            = 0x003C003C 	# 60,60 3932220
METHOD_BASIC_GET                = 0x003C0046 	# 60,70 3932230
METHOD_BASIC_GET_OK             = 0x003C0047 	# 60,71 3932231
METHOD_BASIC_GET_EMPTY          = 0x003C0048 	# 60,72 3932232
METHOD_BASIC_ACK                = 0x003C0050 	# 60,80 3932240
METHOD_BASIC_REJECT             = 0x003C005A 	# 60,90 3932250
METHOD_BASIC_RECOVER_ASYNC      = 0x003C0064 	# 60,100 3932260
METHOD_BASIC_RECOVER            = 0x003C006E 	# 60,110 3932270
METHOD_BASIC_RECOVER_OK         = 0x003C006F 	# 60,111 3932271
METHOD_BASIC_NACK               = 0x003C0078 	# 60,120 3932280
METHOD_CONFIRM_SELECT           = 0x0055000A 	# 85,10 5570570
METHOD_CONFIRM_SELECT_OK        = 0x0055000B 	# 85,11 5570571

CLASS_BASIC             = 0x003C




class Frame(dict):
    has_content = False
    is_error = False


class FrameConnectionStart(Frame):
    name = 'connection.start'
    method_id = METHOD_CONNECTION_START

def decode_connection_start(data, offset):
    frame = FrameConnectionStart()
    (frame['version_major'],
     frame['version_minor']) = unpack_from('!BB', data, offset)
    offset += 1+1
    frame['server_properties'], offset = table.decode(data, offset)
    (str_len,) = unpack_from('!I', data, offset)
    offset += 4
    frame['mechanisms'] = data[offset : offset+str_len]
    offset += str_len
    (str_len,) = unpack_from('!I', data, offset)
    offset += 4
    frame['locales'] = data[offset : offset+str_len]
    offset += str_len
    return frame, offset


class FrameConnectionSecure(Frame):
    name = 'connection.secure'
    method_id = METHOD_CONNECTION_SECURE

def decode_connection_secure(data, offset):
    frame = FrameConnectionSecure()
    (str_len,) = unpack_from('!I', data, offset)
    offset += 4
    frame['challenge'] = data[offset : offset+str_len]
    offset += str_len
    return frame, offset


class FrameConnectionTune(Frame):
    name = 'connection.tune'
    method_id = METHOD_CONNECTION_TUNE

def decode_connection_tune(data, offset):
    frame = FrameConnectionTune()
    (frame['channel_max'],
     frame['frame_max'],
     frame['heartbeat']) = unpack_from('!HIH', data, offset)
    offset += 2+4+2
    return frame, offset


class FrameConnectionOpenOk(Frame):
    name = 'connection.open_ok'
    method_id = METHOD_CONNECTION_OPEN_OK

def decode_connection_open_ok(data, offset):
    frame = FrameConnectionOpenOk()
    (str_len,) = unpack_from('!B', data, offset)
    offset += 1
    frame['known_hosts'] = data[offset : offset+str_len]
    offset += str_len
    return frame, offset


class FrameConnectionClose(Frame):
    name = 'connection.close'
    method_id = METHOD_CONNECTION_CLOSE

def decode_connection_close(data, offset):
    frame = FrameConnectionClose()
    (frame['reply_code'],
     str_len) = unpack_from('!HB', data, offset)
    offset += 2+1
    frame['reply_text'] = data[offset : offset+str_len]
    offset += str_len
    (frame['class_id'],
     frame['method_id']) = unpack_from('!HH', data, offset)
    offset += 2+2
    return frame, offset


class FrameConnectionCloseOk(Frame):
    name = 'connection.close_ok'
    method_id = METHOD_CONNECTION_CLOSE_OK

def decode_connection_close_ok(data, offset):
    frame = FrameConnectionCloseOk()
    return frame, offset


class FrameChannelOpenOk(Frame):
    name = 'channel.open_ok'
    method_id = METHOD_CHANNEL_OPEN_OK

def decode_channel_open_ok(data, offset):
    frame = FrameChannelOpenOk()
    (str_len,) = unpack_from('!I', data, offset)
    offset += 4
    frame['channel_id'] = data[offset : offset+str_len]
    offset += str_len
    return frame, offset


class FrameChannelFlow(Frame):
    name = 'channel.flow'
    method_id = METHOD_CHANNEL_FLOW

def decode_channel_flow(data, offset):
    frame = FrameChannelFlow()
    (bits,) = unpack_from('!B', data, offset)
    frame['active'] = bool(bits & 0x1)
    offset += 1
    return frame, offset


class FrameChannelFlowOk(Frame):
    name = 'channel.flow_ok'
    method_id = METHOD_CHANNEL_FLOW_OK

def decode_channel_flow_ok(data, offset):
    frame = FrameChannelFlowOk()
    (bits,) = unpack_from('!B', data, offset)
    frame['active'] = bool(bits & 0x1)
    offset += 1
    return frame, offset


class FrameChannelClose(Frame):
    name = 'channel.close'
    method_id = METHOD_CHANNEL_CLOSE

def decode_channel_close(data, offset):
    frame = FrameChannelClose()
    (frame['reply_code'],
     str_len) = unpack_from('!HB', data, offset)
    offset += 2+1
    frame['reply_text'] = data[offset : offset+str_len]
    offset += str_len
    (frame['class_id'],
     frame['method_id']) = unpack_from('!HH', data, offset)
    offset += 2+2
    return frame, offset


class FrameChannelCloseOk(Frame):
    name = 'channel.close_ok'
    method_id = METHOD_CHANNEL_CLOSE_OK

def decode_channel_close_ok(data, offset):
    frame = FrameChannelCloseOk()
    return frame, offset


class FrameExchangeDeclareOk(Frame):
    name = 'exchange.declare_ok'
    method_id = METHOD_EXCHANGE_DECLARE_OK

def decode_exchange_declare_ok(data, offset):
    frame = FrameExchangeDeclareOk()
    return frame, offset


class FrameExchangeDeleteOk(Frame):
    name = 'exchange.delete_ok'
    method_id = METHOD_EXCHANGE_DELETE_OK

def decode_exchange_delete_ok(data, offset):
    frame = FrameExchangeDeleteOk()
    return frame, offset


class FrameExchangeBindOk(Frame):
    name = 'exchange.bind_ok'
    method_id = METHOD_EXCHANGE_BIND_OK

def decode_exchange_bind_ok(data, offset):
    frame = FrameExchangeBindOk()
    return frame, offset


class FrameExchangeUnbindOk(Frame):
    name = 'exchange.unbind_ok'
    method_id = METHOD_EXCHANGE_UNBIND_OK

def decode_exchange_unbind_ok(data, offset):
    frame = FrameExchangeUnbindOk()
    return frame, offset


class FrameQueueDeclareOk(Frame):
    name = 'queue.declare_ok'
    method_id = METHOD_QUEUE_DECLARE_OK

def decode_queue_declare_ok(data, offset):
    frame = FrameQueueDeclareOk()
    (str_len,) = unpack_from('!B', data, offset)
    offset += 1
    frame['queue'] = data[offset : offset+str_len]
    offset += str_len
    (frame['message_count'],
     frame['consumer_count']) = unpack_from('!II', data, offset)
    offset += 4+4
    return frame, offset


class FrameQueueBindOk(Frame):
    name = 'queue.bind_ok'
    method_id = METHOD_QUEUE_BIND_OK

def decode_queue_bind_ok(data, offset):
    frame = FrameQueueBindOk()
    return frame, offset


class FrameQueuePurgeOk(Frame):
    name = 'queue.purge_ok'
    method_id = METHOD_QUEUE_PURGE_OK

def decode_queue_purge_ok(data, offset):
    frame = FrameQueuePurgeOk()
    (frame['message_count'],) = unpack_from('!I', data, offset)
    offset += 4
    return frame, offset


class FrameQueueDeleteOk(Frame):
    name = 'queue.delete_ok'
    method_id = METHOD_QUEUE_DELETE_OK

def decode_queue_delete_ok(data, offset):
    frame = FrameQueueDeleteOk()
    (frame['message_count'],) = unpack_from('!I', data, offset)
    offset += 4
    return frame, offset


class FrameQueueUnbindOk(Frame):
    name = 'queue.unbind_ok'
    method_id = METHOD_QUEUE_UNBIND_OK

def decode_queue_unbind_ok(data, offset):
    frame = FrameQueueUnbindOk()
    return frame, offset


class FrameBasicQosOk(Frame):
    name = 'basic.qos_ok'
    method_id = METHOD_BASIC_QOS_OK

def decode_basic_qos_ok(data, offset):
    frame = FrameBasicQosOk()
    return frame, offset


class FrameBasicConsumeOk(Frame):
    name = 'basic.consume_ok'
    method_id = METHOD_BASIC_CONSUME_OK

def decode_basic_consume_ok(data, offset):
    frame = FrameBasicConsumeOk()
    (str_len,) = unpack_from('!B', data, offset)
    offset += 1
    frame['consumer_tag'] = data[offset : offset+str_len]
    offset += str_len
    return frame, offset


class FrameBasicCancel(Frame):
    name = 'basic.cancel'
    method_id = METHOD_BASIC_CANCEL

def decode_basic_cancel(data, offset):
    frame = FrameBasicCancel()
    (str_len,) = unpack_from('!B', data, offset)
    offset += 1
    frame['consumer_tag'] = data[offset : offset+str_len]
    offset += str_len
    (bits,) = unpack_from('!B', data, offset)
    frame['nowait'] = bool(bits & 0x1)
    offset += 1
    return frame, offset


class FrameBasicCancelOk(Frame):
    name = 'basic.cancel_ok'
    method_id = METHOD_BASIC_CANCEL_OK

def decode_basic_cancel_ok(data, offset):
    frame = FrameBasicCancelOk()
    (str_len,) = unpack_from('!B', data, offset)
    offset += 1
    frame['consumer_tag'] = data[offset : offset+str_len]
    offset += str_len
    return frame, offset


class FrameBasicReturn(Frame):
    name = 'basic.return'
    method_id = METHOD_BASIC_RETURN
    has_content = True
    class_id = CLASS_BASIC

def decode_basic_return(data, offset):
    frame = FrameBasicReturn()
    (frame['reply_code'],
     str_len) = unpack_from('!HB', data, offset)
    offset += 2+1
    frame['reply_text'] = data[offset : offset+str_len]
    offset += str_len
    (str_len,) = unpack_from('!B', data, offset)
    offset += 1
    frame['exchange'] = data[offset : offset+str_len]
    offset += str_len
    (str_len,) = unpack_from('!B', data, offset)
    offset += 1
    frame['routing_key'] = data[offset : offset+str_len]
    offset += str_len
    return frame, offset


class FrameBasicDeliver(Frame):
    name = 'basic.deliver'
    method_id = METHOD_BASIC_DELIVER
    has_content = True
    class_id = CLASS_BASIC

def decode_basic_deliver(data, offset):
    frame = FrameBasicDeliver()
    (str_len,) = unpack_from('!B', data, offset)
    offset += 1
    frame['consumer_tag'] = data[offset : offset+str_len]
    offset += str_len
    (frame['delivery_tag'],
     bits,
     str_len) = unpack_from('!QBB', data, offset)
    frame['redelivered'] = bool(bits & 0x1)
    offset += 8+1+1
    frame['exchange'] = data[offset : offset+str_len]
    offset += str_len
    (str_len,) = unpack_from('!B', data, offset)
    offset += 1
    frame['routing_key'] = data[offset : offset+str_len]
    offset += str_len
    return frame, offset


class FrameBasicGetOk(Frame):
    name = 'basic.get_ok'
    method_id = METHOD_BASIC_GET_OK
    has_content = True
    class_id = CLASS_BASIC

def decode_basic_get_ok(data, offset):
    frame = FrameBasicGetOk()
    (frame['delivery_tag'],
     bits,
     str_len) = unpack_from('!QBB', data, offset)
    frame['redelivered'] = bool(bits & 0x1)
    offset += 8+1+1
    frame['exchange'] = data[offset : offset+str_len]
    offset += str_len
    (str_len,) = unpack_from('!B', data, offset)
    offset += 1
    frame['routing_key'] = data[offset : offset+str_len]
    offset += str_len
    (frame['message_count'],) = unpack_from('!I', data, offset)
    offset += 4
    return frame, offset


class FrameBasicGetEmpty(Frame):
    name = 'basic.get_empty'
    method_id = METHOD_BASIC_GET_EMPTY

def decode_basic_get_empty(data, offset):
    frame = FrameBasicGetEmpty()
    (str_len,) = unpack_from('!B', data, offset)
    offset += 1
    frame['cluster_id'] = data[offset : offset+str_len]
    offset += str_len
    return frame, offset


class FrameBasicAck(Frame):
    name = 'basic.ack'
    method_id = METHOD_BASIC_ACK

def decode_basic_ack(data, offset):
    frame = FrameBasicAck()
    (frame['delivery_tag'],
     bits) = unpack_from('!QB', data, offset)
    frame['multiple'] = bool(bits & 0x1)
    offset += 8+1
    return frame, offset


class FrameBasicRecoverOk(Frame):
    name = 'basic.recover_ok'
    method_id = METHOD_BASIC_RECOVER_OK

def decode_basic_recover_ok(data, offset):
    frame = FrameBasicRecoverOk()
    return frame, offset


class FrameConfirmSelectOk(Frame):
    name = 'confirm.select_ok'
    method_id = METHOD_CONFIRM_SELECT_OK

def decode_confirm_select_ok(data, offset):
    frame = FrameConfirmSelectOk()
    return frame, offset



METHODS = {
    METHOD_CONNECTION_START:        decode_connection_start,
    METHOD_CONNECTION_SECURE:       decode_connection_secure,
    METHOD_CONNECTION_TUNE:         decode_connection_tune,
    METHOD_CONNECTION_OPEN_OK:      decode_connection_open_ok,
    METHOD_CONNECTION_CLOSE:        decode_connection_close,
    METHOD_CONNECTION_CLOSE_OK:     decode_connection_close_ok,
    METHOD_CHANNEL_OPEN_OK:         decode_channel_open_ok,
    METHOD_CHANNEL_FLOW:            decode_channel_flow,
    METHOD_CHANNEL_FLOW_OK:         decode_channel_flow_ok,
    METHOD_CHANNEL_CLOSE:           decode_channel_close,
    METHOD_CHANNEL_CLOSE_OK:        decode_channel_close_ok,
    METHOD_EXCHANGE_DECLARE_OK:     decode_exchange_declare_ok,
    METHOD_EXCHANGE_DELETE_OK:      decode_exchange_delete_ok,
    METHOD_EXCHANGE_BIND_OK:        decode_exchange_bind_ok,
    METHOD_EXCHANGE_UNBIND_OK:      decode_exchange_unbind_ok,
    METHOD_QUEUE_DECLARE_OK:        decode_queue_declare_ok,
    METHOD_QUEUE_BIND_OK:           decode_queue_bind_ok,
    METHOD_QUEUE_PURGE_OK:          decode_queue_purge_ok,
    METHOD_QUEUE_DELETE_OK:         decode_queue_delete_ok,
    METHOD_QUEUE_UNBIND_OK:         decode_queue_unbind_ok,
    METHOD_BASIC_QOS_OK:            decode_basic_qos_ok,
    METHOD_BASIC_CONSUME_OK:        decode_basic_consume_ok,
    METHOD_BASIC_CANCEL:            decode_basic_cancel,
    METHOD_BASIC_CANCEL_OK:         decode_basic_cancel_ok,
    METHOD_BASIC_RETURN:            decode_basic_return,
    METHOD_BASIC_DELIVER:           decode_basic_deliver,
    METHOD_BASIC_GET_OK:            decode_basic_get_ok,
    METHOD_BASIC_GET_EMPTY:         decode_basic_get_empty,
    METHOD_BASIC_ACK:               decode_basic_ack,
    METHOD_BASIC_RECOVER_OK:        decode_basic_recover_ok,
    METHOD_CONFIRM_SELECT_OK:       decode_confirm_select_ok,
}


def decode_basic_properties(data, offset):
    props = {}
    flags, = unpack_from('!H', data, offset)
    offset += 2
    assert (flags & 0x01) == 0
    if (flags & 0x8000): # 1 << 15
        (str_len,) = unpack_from('!B', data, offset)
        offset += 1
        props['content_type'] = data[offset : offset+str_len]
        offset += str_len
    if (flags & 0x4000): # 1 << 14
        (str_len,) = unpack_from('!B', data, offset)
        offset += 1
        props['content_encoding'] = data[offset : offset+str_len]
        offset += str_len
    if (flags & 0x2000): # 1 << 13
        props['headers'], offset = table.decode(data, offset)
    if (flags & 0x1000): # 1 << 12
        (props['delivery_mode'],) = unpack_from('!B', data, offset)
        offset += 1
    if (flags & 0x0800): # 1 << 11
        (props['priority'],) = unpack_from('!B', data, offset)
        offset += 1
    if (flags & 0x0400): # 1 << 10
        (str_len,) = unpack_from('!B', data, offset)
        offset += 1
        props['correlation_id'] = data[offset : offset+str_len]
        offset += str_len
    if (flags & 0x0200): # 1 << 9
        (str_len,) = unpack_from('!B', data, offset)
        offset += 1
        props['reply_to'] = data[offset : offset+str_len]
        offset += str_len
    if (flags & 0x0100): # 1 << 8
        (str_len,) = unpack_from('!B', data, offset)
        offset += 1
        props['expiration'] = data[offset : offset+str_len]
        offset += str_len
    if (flags & 0x0080): # 1 << 7
        (str_len,) = unpack_from('!B', data, offset)
        offset += 1
        props['message_id'] = data[offset : offset+str_len]
        offset += str_len
    if (flags & 0x0040): # 1 << 6
        (props['timestamp'],) = unpack_from('!Q', data, offset)
        offset += 8
    if (flags & 0x0020): # 1 << 5
        (str_len,) = unpack_from('!B', data, offset)
        offset += 1
        props['type_'] = data[offset : offset+str_len]
        offset += str_len
    if (flags & 0x0010): # 1 << 4
        (str_len,) = unpack_from('!B', data, offset)
        offset += 1
        props['user_id'] = data[offset : offset+str_len]
        offset += str_len
    if (flags & 0x0008): # 1 << 3
        (str_len,) = unpack_from('!B', data, offset)
        offset += 1
        props['app_id'] = data[offset : offset+str_len]
        offset += str_len
    if (flags & 0x0004): # 1 << 2
        (str_len,) = unpack_from('!B', data, offset)
        offset += 1
        props['cluster_id'] = data[offset : offset+str_len]
        offset += str_len
    return props, offset


PROPS = {
    CLASS_BASIC: decode_basic_properties, 	# 60
}


# client_properties=None mechanism='PLAIN' response=None locale='en_US'
def encode_connection_start_ok(client_properties, mechanism, response, locale):
    client_properties_raw = table.encode(client_properties)
    return ( (0x01,
              ''.join((
                pack('!I', METHOD_CONNECTION_START_OK),
                client_properties_raw,
                pack('!B', len(mechanism)),
                mechanism,
                pack('!I', len(response)),
                response,
                pack('!B', len(locale)),
                locale,
              ))
           ), )

# response=None
def encode_connection_secure_ok(response):
    return ( (0x01,
              ''.join((
                pack('!II', METHOD_CONNECTION_SECURE_OK, len(response)),
                response,
              ))
           ), )

# channel_max=0 frame_max=0 heartbeat=0
def encode_connection_tune_ok(channel_max, frame_max, heartbeat):
    return ( (0x01,
                pack('!IHIH', METHOD_CONNECTION_TUNE_OK, channel_max, frame_max, heartbeat),
           ), )

# virtual_host='/' capabilities='' insist=False
def encode_connection_open(virtual_host):
    return ( (0x01,
              ''.join((
                pack('!IB', METHOD_CONNECTION_OPEN, len(virtual_host)),
                virtual_host,
                "\x00\x00",
              ))
           ), )

# reply_code=None reply_text='' class_id=None method_id=None
def encode_connection_close(reply_code, reply_text, class_id, method_id):
    return ( (0x01,
              ''.join((
                pack('!IHB', METHOD_CONNECTION_CLOSE, reply_code, len(reply_text)),
                reply_text,
                pack('!HH', class_id, method_id),
              ))
           ), )

# 
def encode_connection_close_ok():
    return ( (0x01,
                pack('!I', METHOD_CONNECTION_CLOSE_OK),
           ), )

# out_of_band=''
def encode_channel_open(out_of_band):
    return ( (0x01,
                pack('!IB', METHOD_CHANNEL_OPEN, 0),
           ), )

# active=None
def encode_channel_flow(active):
    return ( (0x01,
                pack('!IB', METHOD_CHANNEL_FLOW, (active and 0x1 or 0)),
           ), )

# active=None
def encode_channel_flow_ok(active):
    return ( (0x01,
                pack('!IB', METHOD_CHANNEL_FLOW_OK, (active and 0x1 or 0)),
           ), )

# reply_code=None reply_text='' class_id=None method_id=None
def encode_channel_close(reply_code, reply_text, class_id, method_id):
    return ( (0x01,
              ''.join((
                pack('!IHB', METHOD_CHANNEL_CLOSE, reply_code, len(reply_text)),
                reply_text,
                pack('!HH', class_id, method_id),
              ))
           ), )

# 
def encode_channel_close_ok():
    return ( (0x01,
                pack('!I', METHOD_CHANNEL_CLOSE_OK),
           ), )

# ticket=0 exchange=None type_='direct' passive=False durable=False auto_delete=False internal=False nowait=False arguments={}
def encode_exchange_declare(exchange, type_, passive, durable, auto_delete, internal, arguments):
    arguments_raw = table.encode(arguments)
    return ( (0x01,
              ''.join((
                pack('!IHB', METHOD_EXCHANGE_DECLARE, 0, len(exchange)),
                exchange,
                pack('!B', len(type_)),
                type_,
                pack('!B', (passive and 0x1 or 0) | (durable and 0x2 or 0) | (auto_delete and 0x4 or 0) | (internal and 0x8 or 0)),
                arguments_raw,
              ))
           ), )

# ticket=0 exchange=None if_unused=False nowait=False
def encode_exchange_delete(exchange, if_unused):
    return ( (0x01,
              ''.join((
                pack('!IHB', METHOD_EXCHANGE_DELETE, 0, len(exchange)),
                exchange,
                pack('!B', (if_unused and 0x1 or 0)),
              ))
           ), )

# ticket=0 destination=None source=None routing_key='' nowait=False arguments={}
def encode_exchange_bind(destination, source, routing_key, arguments):
    arguments_raw = table.encode(arguments)
    return ( (0x01,
              ''.join((
                pack('!IHB', METHOD_EXCHANGE_BIND, 0, len(destination)),
                destination,
                pack('!B', len(source)),
                source,
                pack('!B', len(routing_key)),
                routing_key,
                "\x00",
                arguments_raw,
              ))
           ), )

# ticket=0 destination=None source=None routing_key='' nowait=False arguments={}
def encode_exchange_unbind(destination, source, routing_key, arguments):
    arguments_raw = table.encode(arguments)
    return ( (0x01,
              ''.join((
                pack('!IHB', METHOD_EXCHANGE_UNBIND, 0, len(destination)),
                destination,
                pack('!B', len(source)),
                source,
                pack('!B', len(routing_key)),
                routing_key,
                "\x00",
                arguments_raw,
              ))
           ), )

# ticket=0 queue='' passive=False durable=False exclusive=False auto_delete=False nowait=False arguments={}
def encode_queue_declare(queue, passive, durable, exclusive, auto_delete, arguments):
    arguments_raw = table.encode(arguments)
    return ( (0x01,
              ''.join((
                pack('!IHB', METHOD_QUEUE_DECLARE, 0, len(queue)),
                queue,
                pack('!B', (passive and 0x1 or 0) | (durable and 0x2 or 0) | (exclusive and 0x4 or 0) | (auto_delete and 0x8 or 0)),
                arguments_raw,
              ))
           ), )

# ticket=0 queue='' exchange=None routing_key='' nowait=False arguments={}
def encode_queue_bind(queue, exchange, routing_key, arguments):
    arguments_raw = table.encode(arguments)
    return ( (0x01,
              ''.join((
                pack('!IHB', METHOD_QUEUE_BIND, 0, len(queue)),
                queue,
                pack('!B', len(exchange)),
                exchange,
                pack('!B', len(routing_key)),
                routing_key,
                "\x00",
                arguments_raw,
              ))
           ), )

# ticket=0 queue='' nowait=False
def encode_queue_purge(queue):
    return ( (0x01,
              ''.join((
                pack('!IHB', METHOD_QUEUE_PURGE, 0, len(queue)),
                queue,
                "\x00",
              ))
           ), )

# ticket=0 queue='' if_unused=False if_empty=False nowait=False
def encode_queue_delete(queue, if_unused, if_empty):
    return ( (0x01,
              ''.join((
                pack('!IHB', METHOD_QUEUE_DELETE, 0, len(queue)),
                queue,
                pack('!B', (if_unused and 0x1 or 0) | (if_empty and 0x2 or 0)),
              ))
           ), )

# ticket=0 queue='' exchange=None routing_key='' arguments={}
def encode_queue_unbind(queue, exchange, routing_key, arguments):
    arguments_raw = table.encode(arguments)
    return ( (0x01,
              ''.join((
                pack('!IHB', METHOD_QUEUE_UNBIND, 0, len(queue)),
                queue,
                pack('!B', len(exchange)),
                exchange,
                pack('!B', len(routing_key)),
                routing_key,
                arguments_raw,
              ))
           ), )

# prefetch_size=0 prefetch_count=0 global_=False
def encode_basic_qos(prefetch_size, prefetch_count, global_):
    return ( (0x01,
                pack('!IIHB', METHOD_BASIC_QOS, prefetch_size, prefetch_count, (global_ and 0x1 or 0)),
           ), )

# ticket=0 queue='' consumer_tag='' no_local=False no_ack=False exclusive=False nowait=False arguments={}
def encode_basic_consume(queue, consumer_tag, no_local, no_ack, exclusive, arguments):
    arguments_raw = table.encode(arguments)
    return ( (0x01,
              ''.join((
                pack('!IHB', METHOD_BASIC_CONSUME, 0, len(queue)),
                queue,
                pack('!B', len(consumer_tag)),
                consumer_tag,
                pack('!B', (no_local and 0x1 or 0) | (no_ack and 0x2 or 0) | (exclusive and 0x4 or 0)),
                arguments_raw,
              ))
           ), )

# consumer_tag=None nowait=False
def encode_basic_cancel(consumer_tag):
    return ( (0x01,
              ''.join((
                pack('!IB', METHOD_BASIC_CANCEL, len(consumer_tag)),
                consumer_tag,
                "\x00",
              ))
           ), )

# ticket=0 exchange='' routing_key='' mandatory=False immediate=False user_headers={} payload='' frame_size=None
def encode_basic_publish(exchange, routing_key, mandatory, immediate, user_headers, body, frame_size):
    props, headers = split_headers(user_headers, BASIC_PROPS_SET)
    if headers:
        props['headers'] = headers
    return [ (0x01,
              ''.join((
                pack('!IHB', METHOD_BASIC_PUBLISH, 0, len(exchange)),
                exchange,
                pack('!B', len(routing_key)),
                routing_key,
                pack('!B', (mandatory and 0x1 or 0) | (immediate and 0x2 or 0)),
              ))
           ),
           encode_basic_properties(len(body), props),
        ] + encode_body(body, frame_size)

# ticket=0 queue='' no_ack=False
def encode_basic_get(queue, no_ack):
    return ( (0x01,
              ''.join((
                pack('!IHB', METHOD_BASIC_GET, 0, len(queue)),
                queue,
                pack('!B', (no_ack and 0x1 or 0)),
              ))
           ), )

# delivery_tag=0 multiple=False
def encode_basic_ack(delivery_tag, multiple):
    return ( (0x01,
                pack('!IQB', METHOD_BASIC_ACK, delivery_tag, (multiple and 0x1 or 0)),
           ), )

# delivery_tag=None requeue=True
def encode_basic_reject(delivery_tag, requeue):
    return ( (0x01,
                pack('!IQB', METHOD_BASIC_REJECT, delivery_tag, (requeue and 0x1 or 0)),
           ), )

# requeue=False
def encode_basic_recover_async(requeue):
    return ( (0x01,
                pack('!IB', METHOD_BASIC_RECOVER_ASYNC, (requeue and 0x1 or 0)),
           ), )

# requeue=False
def encode_basic_recover(requeue):
    return ( (0x01,
                pack('!IB', METHOD_BASIC_RECOVER, (requeue and 0x1 or 0)),
           ), )

# delivery_tag=0 multiple=False requeue=True
def encode_basic_nack(delivery_tag, multiple, requeue):
    return ( (0x01,
                pack('!IQB', METHOD_BASIC_NACK, delivery_tag, (multiple and 0x1 or 0) | (requeue and 0x2 or 0)),
           ), )

# nowait=False
def encode_confirm_select():
    return ( (0x01,
                pack('!IB', METHOD_CONFIRM_SELECT, 0),
           ), )

BASIC_PROPS_SET = set((
    "content_type",      # shortstr
    "content_encoding",  # shortstr
    "headers",           # table
    "delivery_mode",     # octet
    "priority",          # octet
    "correlation_id",    # shortstr
    "reply_to",          # shortstr
    "expiration",        # shortstr
    "message_id",        # shortstr
    "timestamp",         # timestamp
    "type_",             # shortstr
    "user_id",           # shortstr
    "app_id",            # shortstr
    "cluster_id",        # shortstr
    ))

ENCODE_PROPS_BASIC = {
    'content_type': (
        0,
        0x8000, # (1 << 15)
        lambda val: ''.join((
                pack('!B', len(val)),
                val,
        )) ),
    'content_encoding': (
        1,
        0x4000, # (1 << 14)
        lambda val: ''.join((
                pack('!B', len(val)),
                val,
        )) ),
    'headers': (
        2,
        0x2000, # (1 << 13)
        lambda val: table.encode(val)
        ),
    'delivery_mode': (
        3,
        0x1000, # (1 << 12)
        lambda val: pack('!B', val)
        ),
    'priority': (
        4,
        0x0800, # (1 << 11)
        lambda val: pack('!B', val)
        ),
    'correlation_id': (
        5,
        0x0400, # (1 << 10)
        lambda val: ''.join((
                pack('!B', len(val)),
                val,
        )) ),
    'reply_to': (
        6,
        0x0200, # (1 << 9)
        lambda val: ''.join((
                pack('!B', len(val)),
                val,
        )) ),
    'expiration': (
        7,
        0x0100, # (1 << 8)
        lambda val: ''.join((
                pack('!B', len(val)),
                val,
        )) ),
    'message_id': (
        8,
        0x0080, # (1 << 7)
        lambda val: ''.join((
                pack('!B', len(val)),
                val,
        )) ),
    'timestamp': (
        9,
        0x0040, # (1 << 6)
        lambda val: pack('!Q', val)
        ),
    'type_': (
        10,
        0x0020, # (1 << 5)
        lambda val: ''.join((
                pack('!B', len(val)),
                val,
        )) ),
    'user_id': (
        11,
        0x0010, # (1 << 4)
        lambda val: ''.join((
                pack('!B', len(val)),
                val,
        )) ),
    'app_id': (
        12,
        0x0008, # (1 << 3)
        lambda val: ''.join((
                pack('!B', len(val)),
                val,
        )) ),
    'cluster_id': (
        13,
        0x0004, # (1 << 2)
        lambda val: ''.join((
                pack('!B', len(val)),
                val,
        )) ),
}

def encode_basic_properties(body_size, props):
    pieces = ['']*14
    flags = 0
    enc = ENCODE_PROPS_BASIC

    for key in BASIC_PROPS_SET & set(props.iterkeys()):
        i, f, fun = enc[key]
        flags |= f
        pieces[i] = fun(props[key])

    return (0x02, ''.join((
        pack('!HHQH',
              CLASS_BASIC, 0, body_size, flags),
        ''.join(pieces),
        ))
        )


def split_headers(user_headers, properties_set):
    props = {}
    headers = {}
    for key, value in user_headers.iteritems():
        if key in properties_set:
            props[key] = value
        else:
            headers[key] = value
    return props, headers

def encode_body(body, frame_size):
    limit = frame_size - 7 - 1   # spec is broken...
    r = []
    while body:
        payload, body = body[:limit], body[limit:]
        r.append( (0x03, payload) )
    return r


########NEW FILE########
__FILENAME__ = spec_exceptions
# Autogenerated - do not edit

class AMQPError(Exception): pass
class AMQPSoftError(AMQPError): pass
class AMQPHardError(AMQPError): pass

class ContentTooLarge(AMQPSoftError):
    reply_code = 311
class NoRoute(AMQPSoftError):
    reply_code = 312
class NoConsumers(AMQPSoftError):
    reply_code = 313
class AccessRefused(AMQPSoftError):
    reply_code = 403
class NotFound(AMQPSoftError):
    reply_code = 404
class ResourceLocked(AMQPSoftError):
    reply_code = 405
class PreconditionFailed(AMQPSoftError):
    reply_code = 406
class ConnectionForced(AMQPHardError):
    reply_code = 320
class InvalidPath(AMQPHardError):
    reply_code = 402
class FrameError(AMQPHardError):
    reply_code = 501
class AMQPSyntaxError(AMQPHardError):
    reply_code = 502
class CommandInvalid(AMQPHardError):
    reply_code = 503
class ChannelError(AMQPHardError):
    reply_code = 504
class UnexpectedFrame(AMQPHardError):
    reply_code = 505
class ResourceError(AMQPHardError):
    reply_code = 506
class NotAllowed(AMQPHardError):
    reply_code = 530
class AMQPNotImplemented(AMQPHardError):
    reply_code = 540
class InternalError(AMQPHardError):
    reply_code = 541

ERRORS = {
    311: ContentTooLarge,
    312: NoRoute,
    313: NoConsumers,
    403: AccessRefused,
    404: NotFound,
    405: ResourceLocked,
    406: PreconditionFailed,
    320: ConnectionForced,
    402: InvalidPath,
    501: FrameError,
    502: AMQPSyntaxError,
    503: CommandInvalid,
    504: ChannelError,
    505: UnexpectedFrame,
    506: ResourceError,
    530: NotAllowed,
    540: AMQPNotImplemented,
    541: InternalError,
}


########NEW FILE########
__FILENAME__ = table
# ***** BEGIN LICENSE BLOCK *****
# Version: MPL 1.1/GPL 2.0
#
# The contents of this file are subject to the Mozilla Public License
# Version 1.1 (the "License"); you may not use this file except in
# compliance with the License. You may obtain a copy of the License at
# http://www.mozilla.org/MPL/
#
# Software distributed under the License is distributed on an "AS IS"
# basis, WITHOUT WARRANTY OF ANY KIND, either express or implied. See
# the License for the specific language governing rights and
# limitations under the License.
#
# The Original Code is Pika.
#
# The Initial Developers of the Original Code are LShift Ltd, Cohesive
# Financial Technologies LLC, and Rabbit Technologies Ltd.  Portions
# created before 22-Nov-2008 00:00:00 GMT by LShift Ltd, Cohesive
# Financial Technologies LLC, or Rabbit Technologies Ltd are Copyright
# (C) 2007-2008 LShift Ltd, Cohesive Financial Technologies LLC, and
# Rabbit Technologies Ltd.
#
# Portions created by LShift Ltd are Copyright (C) 2007-2009 LShift
# Ltd. Portions created by Cohesive Financial Technologies LLC are
# Copyright (C) 2007-2009 Cohesive Financial Technologies
# LLC. Portions created by Rabbit Technologies Ltd are Copyright (C)
# 2007-2009 Rabbit Technologies Ltd.
#
# Portions created by Tony Garnock-Jones are Copyright (C) 2009-2010
# LShift Ltd and Tony Garnock-Jones.
#
# All Rights Reserved.
#
# Contributor(s): ______________________________________.
#
# Alternatively, the contents of this file may be used under the terms
# of the GNU General Public License Version 2 or later (the "GPL"), in
# which case the provisions of the GPL are applicable instead of those
# above. If you wish to allow use of your version of this file only
# under the terms of the GPL, and not to allow others to use your
# version of this file under the terms of the MPL, indicate your
# decision by deleting the provisions above and replace them with the
# notice and other provisions required by the GPL. If you do not
# delete the provisions above, a recipient may use your version of
# this file under the terms of any one of the MPL or the GPL.
#
# ***** END LICENSE BLOCK *****
#
# Code originally from Pika, adapted to Puka.
#

import struct
import decimal
import datetime
import calendar


def encode(table):
    r'''
    >>> encode(None)
    '\x00\x00\x00\x00'
    >>> encode({})
    '\x00\x00\x00\x00'
    >>> encode({'a':1, 'c':1, 'd':'x', 'e':{}})
    '\x00\x00\x00\x1d\x01aI\x00\x00\x00\x01\x01cI\x00\x00\x00\x01\x01eF\x00\x00\x00\x00\x01dS\x00\x00\x00\x01x'
    >>> encode({'a':decimal.Decimal('1.0')})
    '\x00\x00\x00\x08\x01aD\x00\x00\x00\x00\x01'
    >>> encode({'a':decimal.Decimal('5E-3')})
    '\x00\x00\x00\x08\x01aD\x03\x00\x00\x00\x05'
    >>> encode({'a':datetime.datetime(2010,12,31,23,58,59)})
    '\x00\x00\x00\x0b\x01aT\x00\x00\x00\x00M\x1enC'
    >>> encode({'test':decimal.Decimal('-0.01')})
    '\x00\x00\x00\x0b\x04testD\x02\xff\xff\xff\xff'
    >>> encode({'a':-1, 'b':[1,2,3,4,-1],'g':-1})
    '\x00\x00\x00.\x01aI\xff\xff\xff\xff\x01bA\x00\x00\x00\x19I\x00\x00\x00\x01I\x00\x00\x00\x02I\x00\x00\x00\x03I\x00\x00\x00\x04I\xff\xff\xff\xff\x01gI\xff\xff\xff\xff'
    >>> encode({'a': True, 'b':False})
    '\x00\x00\x00\x08\x01at\x01\x01bt\x00'
    >>> encode({'a':None})
    '\x00\x00\x00\x03\x01aV'
    >>> encode({'a':float(0)})
    '\x00\x00\x00\x0b\x01ad\x00\x00\x00\x00\x00\x00\x00\x00'
    >>> encode({'a':float(1)})
    '\x00\x00\x00\x0b\x01ad?\xf0\x00\x00\x00\x00\x00\x00'
    >>> encode({'a':float(-1)})
    '\x00\x00\x00\x0b\x01ad\xbf\xf0\x00\x00\x00\x00\x00\x00'
    >>> encode({'a':float('nan')})
    '\x00\x00\x00\x0b\x01ad\x7f\xf8\x00\x00\x00\x00\x00\x00'
    >>> encode({'a':float('inf')})
    '\x00\x00\x00\x0b\x01ad\x7f\xf0\x00\x00\x00\x00\x00\x00'
    >>> encode({'a':float(10E-300)})
    '\x00\x00\x00\x0b\x01ad\x01\xda\xc9\xa7\xb3\xb70/'

    Encoding of integers, especially corner cases

    >>> encode({'a':2147483647})
    '\x00\x00\x00\x07\x01aI\x7f\xff\xff\xff'
    >>> encode({'a':-2147483647-1})
    '\x00\x00\x00\x07\x01aI\x80\x00\x00\x00'
    >>> encode({'a':9223372036854775807})
    '\x00\x00\x00\x0b\x01al\x7f\xff\xff\xff\xff\xff\xff\xff'
    >>> encode({'a':-9223372036854775807-1})
    '\x00\x00\x00\x0b\x01al\x80\x00\x00\x00\x00\x00\x00\x00'
    >>> encode({'a':2147483647+1})
    '\x00\x00\x00\x0b\x01al\x00\x00\x00\x00\x80\x00\x00\x00'
    >>> encode({'a':-2147483647-2})
    '\x00\x00\x00\x0b\x01al\xff\xff\xff\xff\x7f\xff\xff\xff'
    >>> encode({'a':9223372036854775807+1})
    Traceback (most recent call last):
        ...
    AssertionError: Unable to represent integer wider than 64 bits
    >>> encode({'a': set()})
    Traceback (most recent call last):
        ...
    AssertionError: Unsupported value type during encoding set([]) (<type 'set'>)
    '''
    pieces = []
    if table is None:
        table = {}
    length_index = len(pieces)
    pieces.append(None) # placeholder
    tablesize = 0
    for (key, value) in table.iteritems():
        pieces.append(struct.pack('B', len(key)))
        pieces.append(key)
        tablesize = tablesize + 1 + len(key)
        tablesize += encode_value(pieces, value)
    pieces[length_index] = struct.pack('>I', tablesize)
    return ''.join(pieces)

def encode_value(pieces, value):
    if value is None:
        pieces.append(struct.pack('>c', 'V'))
        return 1
    elif isinstance(value, str):
        pieces.append(struct.pack('>cI', 'S', len(value)))
        pieces.append(value)
        return 5 + len(value)
    elif isinstance(value, bool):
        pieces.append(struct.pack('>cB', 't', int(value)))
        return 2
    elif isinstance(value, int) or isinstance(value, long):
        if -2147483648L <= value <= 2147483647L:
            pieces.append(struct.pack('>ci', 'I', value))
            return 5
        elif -9223372036854775808L <= value <= 9223372036854775807L:
            pieces.append(struct.pack('>cq', 'l', value))
            return 9
        else:
            assert False, "Unable to represent integer wider than 64 bits"
    elif isinstance(value, decimal.Decimal):
        value = value.normalize()
        if value._exp < 0:
            decimals = -value._exp
            raw = int(value * (decimal.Decimal(10) ** decimals))
            pieces.append(struct.pack('>cBi', 'D', decimals, raw))
        else:
            # per spec, the "decimals" octet is unsigned (!)
            pieces.append(struct.pack('>cBi', 'D', 0, int(value)))
        return 6
    elif isinstance(value, datetime.datetime):
        pieces.append(struct.pack('>cQ', 'T', calendar.timegm(
                    value.utctimetuple())))
        return 9
    elif isinstance(value, float):
        pieces.append(struct.pack('>cd', 'd', value))
        return 9
    elif isinstance(value, dict):
        pieces.append(struct.pack('>c', 'F'))
        piece = encode(value)
        pieces.append(piece)
        return 1 + len(piece)
    elif isinstance(value, list):
        p = []
        [encode_value(p, v) for v in value]
        piece = ''.join(p)
        pieces.append(struct.pack('>cI', 'A', len(piece)))
        pieces.append(piece)
        return 5 + len(piece)
    else:
        assert False, "Unsupported value type during encoding %r (%r)" % (
            value, type(value))

def decode(encoded, offset):
    r'''
    >>> decode(encode(None), 0)
    ({}, 4)
    >>> decode(encode({}), 0)[0]
    {}
    >>> decode(encode({'a':1, 'c':1, 'd':'x', 'e':{}, 'f':-1}), 0)[0]
    {'a': 1, 'c': 1, 'e': {}, 'd': 'x', 'f': -1}

    # python 2.5 reports Decimal("1.01"), python 2.6 Decimal('1.01')
    >>> decode(encode({'a':decimal.Decimal('1.01')}), 0)[0] # doctest: +ELLIPSIS
    {'a': Decimal(...1.01...)}
    >>> decode(encode({'a':decimal.Decimal('5E-30')}), 0)[0] # doctest: +ELLIPSIS
    {'a': Decimal(...5E-30...)}
    >>> decode(encode({'a':datetime.datetime(2010,12,31,23,58,59)}), 0)[0]
    {'a': datetime.datetime(2010, 12, 31, 23, 58, 59)}
    >>> decode(encode({'test':decimal.Decimal('-1.234')}), 0)[0]
    {'test': Decimal('-1.234')}
    >>> decode(encode({'test':decimal.Decimal('1.234')}), 0)[0]
    {'test': Decimal('1.234')}
    >>> decode(encode({'test':decimal.Decimal('1000000')}), 0)[0]
    {'test': Decimal('1000000')}
    >>> decode(encode({'a':[1,2,3,'a',decimal.Decimal('-0.01')]}), 0)[0]
    {'a': [1, 2, 3, 'a', Decimal('-0.01')]}
    >>> decode(encode({'a': 100200L, 'b': 9223372036854775807L}), 0)[0]
    {'a': 100200, 'b': 9223372036854775807L}
    >>> decode(encode({'a': True, 'b': False}), 0)[0]
    {'a': True, 'b': False}
    >>> decode(encode({'a': None}), 0)[0]
    {'a': None}
    >>> decode(encode({'a': 1e-300}), 0)[0]
    {'a': 1e-300}
    >>> decode(encode({'a': float('inf'), 'b': float('nan')}), 0)[0]
    {'a': inf, 'b': nan}

    8 bit unsigned, not produced by our encode
    >>> decode('\x00\x00\x00\x04\x01ab\xff', 0)[0]
    {'a': 255}

    16 bit signed, not produced by our encode
    >>> decode('\x00\x00\x00\x04\x01as\xff\xff', 0)[0]
    {'a': -1}
    
    single precision real, not produced by our encode
    >>> decode('\x00\x00\x00\x06\x01af\x50\x15\x02\xF9', 0)[0]
    {'a': 10000000000.0}
    '''
    result = {}
    tablesize = struct.unpack_from('>I', encoded, offset)[0]
    offset = offset + 4
    limit = offset + tablesize
    while offset < limit:
        keylen = struct.unpack_from('B', encoded, offset)[0]
        offset = offset + 1
        key = encoded[offset : offset + keylen]
        offset = offset + keylen
        result[key], offset = decode_value(encoded, offset)
    return (result, offset)

def decode_value(encoded, offset):
    kind = encoded[offset]
    offset = offset + 1
    if (kind == 'S') or (kind == 'x'):
        length = struct.unpack_from('>I', encoded, offset)[0]
        offset = offset + 4
        value = encoded[offset : offset + length]
        offset = offset + length
    elif kind == 's':
        value = struct.unpack_from('>h', encoded, offset)[0]
        offset = offset + 2
    elif kind == 't':
        value = struct.unpack_from('>B', encoded, offset)[0]
        value = bool(value)
        offset = offset + 1
    elif kind == 'b':
        value = struct.unpack_from('>B', encoded, offset)[0]
        offset = offset + 1
    elif kind == 'I':
        value = struct.unpack_from('>i', encoded, offset)[0]
        offset = offset + 4
    elif kind == 'l':
        value = struct.unpack_from('>q', encoded, offset)[0]
        value = long(value)
        offset = offset + 8
    elif kind == 'f':
        # IEEE 754 single
        value = struct.unpack_from('>f', encoded, offset)[0]
        offset = offset + 4
    elif kind == 'd':
        # IEEE 754 double
        value = struct.unpack_from('>d', encoded, offset)[0]
        offset = offset + 8
    elif kind == 'D':
        decimals = struct.unpack_from('B', encoded, offset)[0]
        offset = offset + 1
        raw = struct.unpack_from('>i', encoded, offset)[0]
        offset = offset + 4
        value = decimal.Decimal(raw) * (decimal.Decimal(10) ** -decimals)
    elif kind == 'T':
        value = datetime.datetime.utcfromtimestamp(
            struct.unpack_from('>Q', encoded, offset)[0])
        offset = offset + 8
    elif kind == 'F':
        (value, offset) = decode(encoded, offset)
    elif kind == 'A':
        length, = struct.unpack_from('>I', encoded, offset)
        offset = offset + 4
        offset_end = offset + length
        value = []
        while offset < offset_end:
            v, offset = decode_value(encoded, offset)
            value.append(v)
        assert offset == offset_end
    elif kind == 'V':
        value = None
    else:
        assert False, "Unsupported field kind %s during decoding" % (kind,)
    return value, offset

########NEW FILE########
__FILENAME__ = urlparse
# Backported from Python 2.7 - ipv6 support.
# Distributed on Python License.

"""Parse (absolute and relative) URLs.

urlparse module is based upon the following RFC specifications.

RFC 3986 (STD66): "Uniform Resource Identifiers" by T. Berners-Lee, R. Fielding
and L.  Masinter, January 2005.

RFC 2732 : "Format for Literal IPv6 Addresses in URL's by R.Hinden, B.Carpenter
and L.Masinter, December 1999.

RFC 2396:  "Uniform Resource Identifiers (URI)": Generic Syntax by T.
Berners-Lee, R. Fielding, and L. Masinter, August 1998.

RFC 2368: "The mailto URL scheme", by P.Hoffman , L Masinter, J. Zwinski, July 1998.

RFC 1808: "Relative Uniform Resource Locators", by R. Fielding, UC Irvine, June
1995.

RFC 1738: "Uniform Resource Locators (URL)" by T. Berners-Lee, L. Masinter, M.
McCahill, December 1994

RFC 3986 is considered the current standard and any future changes to
urlparse module should conform with it.  The urlparse module is
currently not entirely compliant with this RFC due to defacto
scenarios for parsing, and for backward compatibility purposes, some
parsing quirks from older RFCs are retained. The testcases in
test_urlparse.py provides a good indicator of parsing behavior.

"""

__all__ = ["urlparse", "urlunparse", "urljoin", "urldefrag",
           "urlsplit", "urlunsplit", "parse_qs", "parse_qsl"]

# A classification of schemes ('' means apply by default)
uses_relative = ['ftp', 'http', 'gopher', 'nntp', 'imap',
                 'wais', 'file', 'https', 'shttp', 'mms',
                 'prospero', 'rtsp', 'rtspu', '', 'sftp']
uses_netloc = ['ftp', 'http', 'gopher', 'nntp', 'telnet',
               'imap', 'wais', 'file', 'mms', 'https', 'shttp',
               'snews', 'prospero', 'rtsp', 'rtspu', 'rsync', '',
               'svn', 'svn+ssh', 'sftp','nfs','git', 'git+ssh']
non_hierarchical = ['gopher', 'hdl', 'mailto', 'news',
                    'telnet', 'wais', 'imap', 'snews', 'sip', 'sips']
uses_params = ['ftp', 'hdl', 'prospero', 'http', 'imap',
               'https', 'shttp', 'rtsp', 'rtspu', 'sip', 'sips',
               'mms', '', 'sftp']
uses_query = ['http', 'wais', 'imap', 'https', 'shttp', 'mms',
              'gopher', 'rtsp', 'rtspu', 'sip', 'sips', '']
uses_fragment = ['ftp', 'hdl', 'http', 'gopher', 'news',
                 'nntp', 'wais', 'https', 'shttp', 'snews',
                 'file', 'prospero', '']

# Characters valid in scheme names
scheme_chars = ('abcdefghijklmnopqrstuvwxyz'
                'ABCDEFGHIJKLMNOPQRSTUVWXYZ'
                '0123456789'
                '+-.')

MAX_CACHE_SIZE = 20
_parse_cache = {}

def clear_cache():
    """Clear the parse cache."""
    _parse_cache.clear()


class ResultMixin(object):
    """Shared methods for the parsed result objects."""

    @property
    def username(self):
        netloc = self.netloc
        if "@" in netloc:
            userinfo = netloc.rsplit("@", 1)[0]
            if ":" in userinfo:
                userinfo = userinfo.split(":", 1)[0]
            return userinfo
        return None

    @property
    def password(self):
        netloc = self.netloc
        if "@" in netloc:
            userinfo = netloc.rsplit("@", 1)[0]
            if ":" in userinfo:
                return userinfo.split(":", 1)[1]
        return None

    @property
    def hostname(self):
        netloc = self.netloc.split('@')[-1]
        if '[' in netloc and ']' in netloc:
            return netloc.split(']')[0][1:].lower()
        elif ':' in netloc:
            return netloc.split(':')[0].lower()
        elif netloc == '':
            return None
        else:
            return netloc.lower()

    @property
    def port(self):
        netloc = self.netloc.split('@')[-1].split(']')[-1]
        if ':' in netloc:
            port = netloc.split(':')[1]
            return int(port, 10)
        else:
            return None

from collections import namedtuple

class SplitResult(namedtuple('SplitResult', 'scheme netloc path query fragment'), ResultMixin):

    __slots__ = ()

    def geturl(self):
        return urlunsplit(self)


class ParseResult(namedtuple('ParseResult', 'scheme netloc path params query fragment'), ResultMixin):

    __slots__ = ()

    def geturl(self):
        return urlunparse(self)


def urlparse(url, scheme='', allow_fragments=True):
    """Parse a URL into 6 components:
    <scheme>://<netloc>/<path>;<params>?<query>#<fragment>
    Return a 6-tuple: (scheme, netloc, path, params, query, fragment).
    Note that we don't break the components up in smaller bits
    (e.g. netloc is a single string) and we don't expand % escapes."""
    tuple = urlsplit(url, scheme, allow_fragments)
    scheme, netloc, url, query, fragment = tuple
    if scheme in uses_params and ';' in url:
        url, params = _splitparams(url)
    else:
        params = ''
    return ParseResult(scheme, netloc, url, params, query, fragment)

def _splitparams(url):
    if '/'  in url:
        i = url.find(';', url.rfind('/'))
        if i < 0:
            return url, ''
    else:
        i = url.find(';')
    return url[:i], url[i+1:]

def _splitnetloc(url, start=0):
    delim = len(url)   # position of end of domain part of url, default is end
    for c in '/?#':    # look for delimiters; the order is NOT important
        wdelim = url.find(c, start)        # find first of this delim
        if wdelim >= 0:                    # if found
            delim = min(delim, wdelim)     # use earliest delim position
    return url[start:delim], url[delim:]   # return (domain, rest)

def urlsplit(url, scheme='', allow_fragments=True):
    """Parse a URL into 5 components:
    <scheme>://<netloc>/<path>?<query>#<fragment>
    Return a 5-tuple: (scheme, netloc, path, query, fragment).
    Note that we don't break the components up in smaller bits
    (e.g. netloc is a single string) and we don't expand % escapes."""
    allow_fragments = bool(allow_fragments)
    key = url, scheme, allow_fragments, type(url), type(scheme)
    cached = _parse_cache.get(key, None)
    if cached:
        return cached
    if len(_parse_cache) >= MAX_CACHE_SIZE: # avoid runaway growth
        clear_cache()
    netloc = query = fragment = ''
    i = url.find(':')
    if i > 0:
        if url[:i] == 'http': # optimize the common case
            scheme = url[:i].lower()
            url = url[i+1:]
            if url[:2] == '//':
                netloc, url = _splitnetloc(url, 2)
                if (('[' in netloc and ']' not in netloc) or
                        (']' in netloc and '[' not in netloc)):
                    raise ValueError("Invalid IPv6 URL")
            if allow_fragments and '#' in url:
                url, fragment = url.split('#', 1)
            if '?' in url:
                url, query = url.split('?', 1)
            v = SplitResult(scheme, netloc, url, query, fragment)
            _parse_cache[key] = v
            return v
        for c in url[:i]:
            if c not in scheme_chars:
                break
        else:
            scheme, url = url[:i].lower(), url[i+1:]

    if url[:2] == '//':
        netloc, url = _splitnetloc(url, 2)
        if (('[' in netloc and ']' not in netloc) or
                (']' in netloc and '[' not in netloc)):
            raise ValueError("Invalid IPv6 URL")
    if allow_fragments and scheme in uses_fragment and '#' in url:
        url, fragment = url.split('#', 1)
    if scheme in uses_query and '?' in url:
        url, query = url.split('?', 1)
    v = SplitResult(scheme, netloc, url, query, fragment)
    _parse_cache[key] = v
    return v

def urlunparse(data):
    """Put a parsed URL back together again.  This may result in a
    slightly different, but equivalent URL, if the URL that was parsed
    originally had redundant delimiters, e.g. a ? with an empty query
    (the draft states that these are equivalent)."""
    scheme, netloc, url, params, query, fragment = data
    if params:
        url = "%s;%s" % (url, params)
    return urlunsplit((scheme, netloc, url, query, fragment))

def urlunsplit(data):
    """Combine the elements of a tuple as returned by urlsplit() into a
    complete URL as a string. The data argument can be any five-item iterable.
    This may result in a slightly different, but equivalent URL, if the URL that
    was parsed originally had unnecessary delimiters (for example, a ? with an
    empty query; the RFC states that these are equivalent)."""
    scheme, netloc, url, query, fragment = data
    if netloc or (scheme and scheme in uses_netloc and url[:2] != '//'):
        if url and url[:1] != '/': url = '/' + url
        url = '//' + (netloc or '') + url
    if scheme:
        url = scheme + ':' + url
    if query:
        url = url + '?' + query
    if fragment:
        url = url + '#' + fragment
    return url

def urljoin(base, url, allow_fragments=True):
    """Join a base URL and a possibly relative URL to form an absolute
    interpretation of the latter."""
    if not base:
        return url
    if not url:
        return base
    bscheme, bnetloc, bpath, bparams, bquery, bfragment = \
            urlparse(base, '', allow_fragments)
    scheme, netloc, path, params, query, fragment = \
            urlparse(url, bscheme, allow_fragments)
    if scheme != bscheme or scheme not in uses_relative:
        return url
    if scheme in uses_netloc:
        if netloc:
            return urlunparse((scheme, netloc, path,
                               params, query, fragment))
        netloc = bnetloc
    if path[:1] == '/':
        return urlunparse((scheme, netloc, path,
                           params, query, fragment))
    if not path:
        path = bpath
        if not params:
            params = bparams
        else:
            path = path[:-1]
            return urlunparse((scheme, netloc, path,
                                params, query, fragment))
        if not query:
            query = bquery
        return urlunparse((scheme, netloc, path,
                           params, query, fragment))
    segments = bpath.split('/')[:-1] + path.split('/')
    # XXX The stuff below is bogus in various ways...
    if segments[-1] == '.':
        segments[-1] = ''
    while '.' in segments:
        segments.remove('.')
    while 1:
        i = 1
        n = len(segments) - 1
        while i < n:
            if (segments[i] == '..'
                and segments[i-1] not in ('', '..')):
                del segments[i-1:i+1]
                break
            i = i+1
        else:
            break
    if segments == ['', '..']:
        segments[-1] = ''
    elif len(segments) >= 2 and segments[-1] == '..':
        segments[-2:] = ['']
    return urlunparse((scheme, netloc, '/'.join(segments),
                       params, query, fragment))

def urldefrag(url):
    """Removes any existing fragment from URL.

    Returns a tuple of the defragmented URL and the fragment.  If
    the URL contained no fragments, the second element is the
    empty string.
    """
    if '#' in url:
        s, n, p, a, q, frag = urlparse(url)
        defrag = urlunparse((s, n, p, a, q, ''))
        return defrag, frag
    else:
        return url, ''

# unquote method for parse_qs and parse_qsl
# Cannot use directly from urllib as it would create a circular reference
# because urllib uses urlparse methods (urljoin).  If you update this function,
# update it also in urllib.  This code duplication does not existin in Python3.

_hexdig = '0123456789ABCDEFabcdef'
_hextochr = dict((a+b, chr(int(a+b,16)))
                 for a in _hexdig for b in _hexdig)

def unquote(s):
    """unquote('abc%20def') -> 'abc def'."""
    res = s.split('%')
    # fastpath
    if len(res) == 1:
        return s
    s = res[0]
    for item in res[1:]:
        try:
            s += _hextochr[item[:2]] + item[2:]
        except KeyError:
            s += '%' + item
        except UnicodeDecodeError:
            s += unichr(int(item[:2], 16)) + item[2:]
    return s

def parse_qs(qs, keep_blank_values=0, strict_parsing=0):
    """Parse a query given as a string argument.

        Arguments:

        qs: URL-encoded query string to be parsed

        keep_blank_values: flag indicating whether blank values in
            URL encoded queries should be treated as blank strings.
            A true value indicates that blanks should be retained as
            blank strings.  The default false value indicates that
            blank values are to be ignored and treated as if they were
            not included.

        strict_parsing: flag indicating what to do with parsing errors.
            If false (the default), errors are silently ignored.
            If true, errors raise a ValueError exception.
    """
    dict = {}
    for name, value in parse_qsl(qs, keep_blank_values, strict_parsing):
        if name in dict:
            dict[name].append(value)
        else:
            dict[name] = [value]
    return dict

def parse_qsl(qs, keep_blank_values=0, strict_parsing=0):
    """Parse a query given as a string argument.

    Arguments:

    qs: URL-encoded query string to be parsed

    keep_blank_values: flag indicating whether blank values in
        URL encoded queries should be treated as blank strings.  A
        true value indicates that blanks should be retained as blank
        strings.  The default false value indicates that blank values
        are to be ignored and treated as if they were  not included.

    strict_parsing: flag indicating what to do with parsing errors. If
        false (the default), errors are silently ignored. If true,
        errors raise a ValueError exception.

    Returns a list, as G-d intended.
    """
    pairs = [s2 for s1 in qs.split('&') for s2 in s1.split(';')]
    r = []
    for name_value in pairs:
        if not name_value and not strict_parsing:
            continue
        nv = name_value.split('=', 1)
        if len(nv) != 2:
            if strict_parsing:
                raise ValueError, "bad query field: %r" % (name_value,)
            # Handle case of a control-name with no equal sign
            if keep_blank_values:
                nv.append('')
            else:
                continue
        if len(nv[1]) or keep_blank_values:
            name = unquote(nv[0].replace('+', ' '))
            value = unquote(nv[1].replace('+', ' '))
            r.append((name, value))

    return r


test_input = """
      http://a/b/c/d

      g:h        = <URL:g:h>
      http:g     = <URL:http://a/b/c/g>
      http:      = <URL:http://a/b/c/d>
      g          = <URL:http://a/b/c/g>
      ./g        = <URL:http://a/b/c/g>
      g/         = <URL:http://a/b/c/g/>
      /g         = <URL:http://a/g>
      //g        = <URL:http://g>
      ?y         = <URL:http://a/b/c/d?y>
      g?y        = <URL:http://a/b/c/g?y>
      g?y/./x    = <URL:http://a/b/c/g?y/./x>
      .          = <URL:http://a/b/c/>
      ./         = <URL:http://a/b/c/>
      ..         = <URL:http://a/b/>
      ../        = <URL:http://a/b/>
      ../g       = <URL:http://a/b/g>
      ../..      = <URL:http://a/>
      ../../g    = <URL:http://a/g>
      ../../../g = <URL:http://a/../g>
      ./../g     = <URL:http://a/b/g>
      ./g/.      = <URL:http://a/b/c/g/>
      /./g       = <URL:http://a/./g>
      g/./h      = <URL:http://a/b/c/g/h>
      g/../h     = <URL:http://a/b/c/h>
      http:g     = <URL:http://a/b/c/g>
      http:      = <URL:http://a/b/c/d>
      http:?y         = <URL:http://a/b/c/d?y>
      http:g?y        = <URL:http://a/b/c/g?y>
      http:g?y/./x    = <URL:http://a/b/c/g?y/./x>
"""

def test():
    import sys
    base = ''
    if sys.argv[1:]:
        fn = sys.argv[1]
        if fn == '-':
            fp = sys.stdin
        else:
            fp = open(fn)
    else:
        try:
            from cStringIO import StringIO
        except ImportError:
            from StringIO import StringIO
        fp = StringIO(test_input)
    for line in fp:
        words = line.split()
        if not words:
            continue
        url = words[0]
        parts = urlparse(url)
        print '%-10s : %s' % (url, parts)
        abs = urljoin(base, url)
        if not base:
            base = abs
        wrapped = '<URL:%s>' % abs
        print '%-10s = %s' % (url, wrapped)
        if len(words) == 3 and words[1] == '=':
            if wrapped != words[2]:
                print 'EXPECTED', words[2], '!!!!!!!!!!'

if __name__ == '__main__':
    test()

########NEW FILE########
__FILENAME__ = base
import functools
import os
import puka
import random
import unittest_backport as unittest


class TestCase(unittest.TestCase):
    def setUp(self):
        self.name = 'test%s' % (random.random(),)
        self.name1 = 'test%s' % (random.random(),)
        self.name2 = 'test%s' % (random.random(),)
        self.msg = '%s' % (random.random(),)
        self.msg1 = '%s' % (random.random(),)
        self.msg2 = '%s' % (random.random(),)
        self.amqp_url = os.getenv('AMQP_URL', 'amqp:///')

    def tearDown(self):
        pass


def connect(method):
    @functools.wraps(method)
    def wrapper(self, *args, **kwargs):
        client = puka.Client(self.amqp_url)
        promise = client.connect()
        client.wait(promise)
        r = method(self, client, *args, **kwargs)
        promise = client.close()
        client.wait(promise)
        return r
    return wrapper

########NEW FILE########
__FILENAME__ = tests
#!/usr/bin/env python

import sys
import glob
import time
import os, os.path
import doctest
import unittest
try:
    import coverage
except ImportError:
    print "No 'coverage' module found. Try:"
    print "     sudo apt-get install python-coverage"
    sys.exit(1)

import logging
FORMAT_CONS = '%(asctime)s %(name)-12s %(levelname)8s\t%(message)s'
logging.basicConfig(level=logging.DEBUG, format=FORMAT_CONS)



VERBOSE=False

def my_import(name):
    mod = __import__(name)
    components = name.split('.')
    for comp in components[1:]:
        mod = getattr(mod, comp)
    return mod

def main_coverage(TESTS):
    TEST_NAMES = [f.rpartition('.')[0] for f in glob.glob("test_*.py")]
    TEST_NAMES.sort()

    pwd=os.getcwd()
    os.chdir(sys.argv[1])
    BAD_MODULES=(sys.argv[3] if len(sys.argv) >= 4 else '').split(',')
    MODULE_NAMES=[sys.argv[2] + '.' +f[0:-3] for f in glob.glob("*.py") if f not in BAD_MODULES]
    MODULE_NAMES.sort()
    os.chdir(pwd)

    modulenames = MODULE_NAMES

    try:
        cov = coverage.coverage(branch=True)
    except TypeError:
        cov = coverage
    cov.erase()
    cov.exclude('#pragma[: ]+[nN][oO] [cC][oO][vV][eE][rR]')
    cov.start()

    modules = []
    for modulename in modulenames:
        mod = my_import(modulename)
        modules.append(mod)

    if 'unittest' in TESTS:
        print "***** Unittest *****"
        test_args = {'verbosity': 1}
        suite = unittest.TestLoader().loadTestsFromNames(TEST_NAMES)
        unittest.TextTestRunner(**test_args).run(suite)

    if 'doctest' in TESTS:
        t0 = time.time()
        print "\n***** Doctest *****"
        for mod in modules:
            doctest.testmod(mod, verbose=VERBOSE)
        td = time.time() - t0
        print "      Tests took %.3f seconds" % (td, )

    print "\n***** Coverage Python *****"
    cov.stop()
    cov.report(modules, ignore_errors=1, show_missing=1)
    #cov.html_report(morfs=modules, directory='/tmp')
    cov.erase()



if __name__ == '__main__':
    main_coverage(['unittest', 'doctest'])


def run_unittests(g):
    test_args = {'verbosity': 1}
    for t in [t for t in g.keys()
                        if (t.startswith('Test') and issubclass(g[t], unittest.TestCase)) ]:
        suite = unittest.TestLoader().loadTestsFromTestCase(g[t])
        unittest.TextTestRunner(**test_args).run(suite)


########NEW FILE########
__FILENAME__ = test_async
import os
import puka
import random

import base


class TestBasic(base.TestCase):
    def test_simple_roundtrip(self):
        client = puka.Client(self.amqp_url)

        def on_connect(t, result):
            client.queue_declare(queue=self.name,
                                 callback=on_queue_declare)

        def on_queue_declare(t, result):
            client.basic_publish(exchange='', routing_key=self.name,
                                 body=self.msg,
                                 callback=on_basic_publish)

        def on_basic_publish(t, result):
            client.basic_get(queue=self.name,
                             callback=on_basic_get)

        def on_basic_get(t, result):
            self.assertEqual(result['body'], self.msg)
            client.basic_ack(result)
            client.queue_delete(queue=self.name,
                                callback=on_queue_delete)

        def on_queue_delete(t, result):
            client.loop_break()

        client.connect(callback=on_connect)
        client.loop()

        promise = client.close()
        client.wait(promise)


    def test_close(self):
        def on_connection(promise, result):
            client.queue_declare(queue=self.name, callback=on_queue_declare)

        def on_queue_declare(promise, result):
            client.basic_publish(exchange='', routing_key=self.name,
                                 body="Hello world!",
                                 callback=on_basic_publish)

        def on_basic_publish(promise, result):
            client.queue_delete(queue=self.name,
                                callback=on_queue_delete)

        def on_queue_delete(promise, result):
            client.loop_break()

        client = puka.Client(self.amqp_url)
        client.connect(callback=on_connection)
        client.loop()

        promise = client.close()
        client.wait(promise)


    def test_consume_close(self):
        def on_connection(promise, result):
            client.queue_declare(queue=self.name, auto_delete=True,
                                 callback=on_queue_declare)

        def on_queue_declare(promise, result):
            client.basic_consume(queue=self.name, callback=on_basic_consume)
            client.loop_break()

        def on_basic_consume(promise, result):
            self.assertTrue(result.is_error)

        client = puka.Client(self.amqp_url)
        client.connect(callback=on_connection)
        client.loop()

        promise = client.close()
        client.wait(promise)

        client.run_any_callbacks()

if __name__ == '__main__':
    import tests
    tests.run_unittests(globals())


########NEW FILE########
__FILENAME__ = test_basic
from __future__ import with_statement

import os
import puka

import base


class TestBasic(base.TestCase):
    def test_simple_roundtrip(self):
        client = puka.Client(self.amqp_url)
        promise = client.connect()
        client.wait(promise)

        promise = client.queue_declare(queue=self.name)
        client.wait(promise)

        promise = client.basic_publish(exchange='', routing_key=self.name,
                                       body=self.msg)
        client.wait(promise)

        consume_promise = client.basic_consume(queue=self.name, no_ack=True)
        result = client.wait(consume_promise)
        self.assertEqual(result['body'], self.msg)

        promise = client.queue_delete(queue=self.name)
        client.wait(promise)

    def test_simple_roundtrip_with_connection_properties(self):
        props = { 'puka_test': 'blah', 'random_prop': 1234 }

        client = puka.Client(self.amqp_url, client_properties=props)
        promise = client.connect()
        client.wait(promise)

        promise = client.queue_declare(queue=self.name)
        client.wait(promise)

        promise = client.basic_publish(exchange='', routing_key=self.name,
                                       body=self.msg)
        client.wait(promise)

        consume_promise = client.basic_consume(queue=self.name, no_ack=True)
        result = client.wait(consume_promise)
        self.assertEqual(result['body'], self.msg)

        promise = client.queue_delete(queue=self.name)
        client.wait(promise)


    def test_purge(self):
        client = puka.Client(self.amqp_url)
        promise = client.connect()
        client.wait(promise)

        promise = client.queue_declare(queue=self.name)
        client.wait(promise)

        promise = client.basic_publish(exchange='', routing_key=self.name,
                                       body=self.msg)
        client.wait(promise)

        promise = client.queue_purge(queue=self.name)
        r = client.wait(promise)
        self.assertEqual(r['message_count'], 1)

        promise = client.queue_purge(queue=self.name)
        r = client.wait(promise)
        self.assertEqual(r['message_count'], 0)

        promise = client.queue_delete(queue=self.name)
        client.wait(promise)


    def test_basic_get_ack(self):
        client = puka.Client(self.amqp_url)
        promise = client.connect()
        client.wait(promise)

        promise = client.queue_declare(queue=self.name)
        client.wait(promise)

        for i in range(4):
            promise = client.basic_publish(exchange='', routing_key=self.name,
                                           body=self.msg+str(i))
            client.wait(promise)

        msgs = []
        for i in range(4):
            promise = client.basic_get(queue=self.name)
            result = client.wait(promise)
            self.assertEqual(result['body'], self.msg+str(i))
            self.assertEqual(result['redelivered'], False)
            msgs.append( result )

        promise = client.basic_get(queue=self.name)
        result = client.wait(promise)
        self.assertEqual('body' in result, False)

        self.assertEqual(len(client.channels.free_channels), 1)
        self.assertEqual(client.channels.free_channel_numbers[-1], 7)
        for msg in msgs:
            client.basic_ack(msg)
        self.assertEqual(len(client.channels.free_channels), 5)
        self.assertEqual(client.channels.free_channel_numbers[-1], 7)

        promise = client.queue_delete(queue=self.name)
        client.wait(promise)


    def test_basic_publish_bad_exchange(self):
        client = puka.Client(self.amqp_url)
        promise = client.connect()
        client.wait(promise)

        for i in range(2):
            promise = client.basic_publish(exchange='invalid_exchange',
                                           routing_key='xxx', body='')

            self.assertEqual(len(client.channels.free_channels), 0)
            self.assertEqual(client.channels.free_channel_numbers[-1], 2)

            with self.assertRaises(puka.NotFound) as cm:
                client.wait(promise)

            (r,) = cm.exception # unpack args of exception
            self.assertTrue(r.is_error)
            self.assertEqual(r['reply_code'], 404)

            self.assertEqual(len(client.channels.free_channels), 0)
            self.assertEqual(client.channels.free_channel_numbers[-1], 2)


    def test_basic_return(self):
        client = puka.Client(self.amqp_url)
        promise = client.connect()
        client.wait(promise)

        promise = client.basic_publish(exchange='', routing_key=self.name,
                                       mandatory=True, body='')
        with self.assertRaises(puka.NoRoute):
            client.wait(promise)

        promise = client.queue_declare(queue=self.name)
        client.wait(promise)

        promise = client.basic_publish(exchange='', routing_key=self.name,
                                       mandatory=True, body='')
        client.wait(promise) # no error

        promise = client.queue_delete(queue=self.name)
        client.wait(promise)


    def test_persistent(self):
        client = puka.Client(self.amqp_url)
        promise = client.connect()
        client.wait(promise)

        promise = client.queue_declare(queue=self.name)
        client.wait(promise)

        promise = client.basic_publish(exchange='', routing_key=self.name,
                                       body=self.msg) # persistence=default
        client.wait(promise)

        promise = client.basic_publish(exchange='', routing_key=self.name,
                                       body=self.msg,
                                       headers={'delivery_mode':2})
        client.wait(promise)

        promise = client.basic_publish(exchange='', routing_key=self.name,
                                       body=self.msg,
                                       headers={'delivery_mode':1})
        client.wait(promise)

        promise = client.basic_get(queue=self.name, no_ack=True)
        result = client.wait(promise)
        self.assertTrue('delivery_mode' not in result['headers'])

        promise = client.basic_get(queue=self.name, no_ack=True)
        result = client.wait(promise)
        self.assertTrue('delivery_mode' in result['headers'])
        self.assertEquals(result['headers']['delivery_mode'], 2)

        promise = client.basic_get(queue=self.name, no_ack=True)
        result = client.wait(promise)
        self.assertTrue('delivery_mode' in result['headers'])
        self.assertEquals(result['headers']['delivery_mode'], 1)

        promise = client.queue_delete(queue=self.name)
        client.wait(promise)


    def test_basic_reject(self):
        client = puka.Client(self.amqp_url)
        promise = client.connect()
        client.wait(promise)

        promise = client.queue_declare(queue=self.name)
        client.wait(promise)

        promise = client.basic_publish(exchange='', routing_key=self.name,
                                       body='a')
        client.wait(promise)

        t = client.basic_get(queue=self.name)
        r = client.wait(t)
        self.assertEqual(r['body'], 'a')
        self.assertTrue(not r['redelivered'])
        client.basic_reject(r)

        t = client.basic_get(queue=self.name)
        r = client.wait(t)
        self.assertEqual(r['body'], 'a')
        self.assertTrue(r['redelivered'])

        promise = client.queue_delete(queue=self.name)
        client.wait(promise)


    def test_basic_reject_no_requeue(self):
        client = puka.Client(self.amqp_url)
        promise = client.connect()
        client.wait(promise)

        promise = client.queue_declare(queue=self.name)
        client.wait(promise)

        promise = client.basic_publish(exchange='', routing_key=self.name,
                                       body='a')
        client.wait(promise)

        t = client.basic_get(queue=self.name)
        r = client.wait(t)
        self.assertEqual(r['body'], 'a')
        self.assertTrue(not r['redelivered'])
        client.basic_reject(r, requeue=False)

        t = client.basic_get(queue=self.name)
        r = client.wait(t)
        self.assertTrue(r['empty'])
        self.assertFalse('redelivered' in r)
        self.assertFalse('body' in r)

        promise = client.queue_delete(queue=self.name)
        client.wait(promise)


    def test_basic_reject_dead_letter_exchange(self):
        client = puka.Client(self.amqp_url)
        promise = client.connect()
        client.wait(promise)

        promise = client.exchange_declare(exchange=self.name1, type='fanout')
        client.wait(promise)

        promise = client.queue_declare(
            queue=self.name, arguments={'x-dead-letter-exchange': self.name1})
        client.wait(promise)

        promise = client.queue_declare(exclusive=True)
        dlxqname = client.wait(promise)['queue']

        promise = client.queue_bind(queue=dlxqname, exchange=self.name1)
        client.wait(promise)

        promise = client.basic_publish(exchange='', routing_key=self.name,
                                       body='a')
        client.wait(promise)

        t = client.basic_get(queue=self.name)
        r = client.wait(t)
        self.assertEqual(r['body'], 'a')
        self.assertTrue(not r['redelivered'])
        client.basic_reject(r, requeue=False)

        t = client.basic_get(queue=self.name)
        r = client.wait(t)
        self.assertTrue(r['empty'])
        self.assertFalse('redelivered' in r)
        self.assertFalse('body' in r)

        t = client.basic_get(queue=dlxqname)
        r = client.wait(t)
        self.assertEqual(r['body'], 'a')
        self.assertEqual(r['headers']['x-death'][0]['reason'], 'rejected')
        self.assertTrue(not r['redelivered'])

        promise = client.queue_delete(queue=self.name)
        client.wait(promise)

        promise = client.exchange_delete(exchange=self.name1)
        client.wait(promise)


    def test_properties(self):
        client = puka.Client(self.amqp_url)
        promise = client.connect()
        client.wait(promise)

        t = client.queue_declare(queue=self.name)
        client.wait(t)

        headers = {
            "content_type": 'a',
            "content_encoding": 'b',
            #"headers":
            "delivery_mode": 2,
            "priority": 1,
            "correlation_id": 'd',
            "reply_to": 'e',
            "expiration": '1000000',
            "message_id": 'g',
            "timestamp": 1,
            "type_": 'h',
            "user_id": 'guest',  # that one needs to match real user
            "app_id": 'j',
            "cluster_id": 'k',
            "custom": 'l',
            "blah2": [True, 1, -1, 4611686018427387904L, None, float(12e10),
                      -4611686018427387904L, [1,2,3,4, {"a":"b", "c":[]}]],
            }

        t = client.basic_publish(exchange='', routing_key=self.name,
                                 body='a', headers=headers.copy())
        client.wait(t)

        t = client.basic_get(queue=self.name, no_ack=True)
        r = client.wait(t)
        self.assertEqual(r['body'], 'a')
        recv_headers = r['headers']
        del recv_headers['x-puka-delivery-tag']

        self.assertEqual(repr(headers), repr(recv_headers))

        promise = client.queue_delete(queue=self.name)
        client.wait(promise)


    def test_basic_ack_fail(self):
        client = puka.Client(self.amqp_url)
        promise = client.connect()
        client.wait(promise)

        promise = client.queue_declare(queue=self.name)
        client.wait(promise)

        promise = client.basic_publish(exchange='', routing_key=self.name,
                                       body='a')
        client.wait(promise)

        promise = client.basic_consume(queue=self.name)
        result = client.wait(promise)

        with self.assertRaises(puka.PreconditionFailed):
            r2 = result.copy()
            r2['delivery_tag'] = 999
            client.basic_ack(r2)
            client.wait(promise)

        promise = client.basic_consume(queue=self.name)
        result = client.wait(promise)
        client.basic_ack(result)

        with self.assertRaises(AssertionError):
            client.basic_ack(result)

        promise = client.queue_delete(queue=self.name)
        client.wait(promise)


    def test_basic_cancel(self):
        client = puka.Client(self.amqp_url)
        promise = client.connect()
        client.wait(promise)

        promise = client.queue_declare(queue=self.name)
        client.wait(promise)

        for i in range(2):
            promise = client.basic_publish(exchange='', routing_key=self.name,
                                           body='a')
            client.wait(promise)

        consume_promise = client.basic_consume(queue=self.name)
        msg1 = client.wait(consume_promise)
        self.assertEqual(msg1['body'], 'a')
        client.basic_ack(msg1)

        promise = client.basic_cancel(consume_promise)
        result = client.wait(promise)
        self.assertTrue('consumer_tag' in result)

        promise = client.basic_publish(exchange='', routing_key=self.name,
                                       body='b')
        client.wait(promise)

        promise = client.queue_delete(queue=self.name)
        client.wait(promise)


    def test_close(self):
        client = puka.Client(self.amqp_url)
        promise = client.connect()
        client.wait(promise)

        promise = client.queue_declare(queue=self.name)
        client.wait(promise)

        promise = client.basic_publish(exchange='', routing_key=self.name,
                                       body=self.msg)
        client.wait(promise)

        consume_promise = client.basic_consume(queue=self.name)
        msg_result = client.wait(consume_promise)

        promise = client.queue_delete(self.name)
        client.wait(promise)

        promise = client.close()
        client.wait(promise)


    def test_basic_consume_fail(self):
        client = puka.Client(self.amqp_url)
        promise = client.connect()
        client.wait(promise)

        consume_promise = client.basic_consume(queue='bad_q_name')
        with self.assertRaises(puka.NotFound):
            msg_result = client.wait(consume_promise)

        promise = client.close()
        client.wait(promise)

    def test_broken_ack_on_close(self):
        client = puka.Client(self.amqp_url)
        promise = client.connect()
        client.wait(promise)

        promise = client.queue_declare()
        qname = client.wait(promise)['queue']

        promise = client.basic_publish(exchange='', routing_key=qname, body='a')
        client.wait(promise)

        promise = client.basic_get(queue=qname)
        r = client.wait(promise)
        self.assertEquals(r['body'], 'a')

        promise = client.queue_delete(queue=qname)
        client.wait(promise)

        promise = client.close()
        client.wait(promise)

    @base.connect
    def test_basic_qos(self, client):
        promise = client.queue_declare(queue=self.name)
        client.wait(promise)

        promise = client.basic_publish(exchange='', routing_key=self.name,
                                       body='a')
        client.wait(promise)
        promise = client.basic_publish(exchange='', routing_key=self.name,
                                       body='b')
        client.wait(promise)
        promise = client.basic_publish(exchange='', routing_key=self.name,
                                       body='c')
        client.wait(promise)

        consume_promise = client.basic_consume(queue=self.name, prefetch_count=1)
        result = client.wait(consume_promise, timeout=0.1)
        self.assertEqual(result['body'], 'a')

        result = client.wait(consume_promise, timeout=0.1)
        self.assertEqual(result, None)

        promise = client.basic_qos(consume_promise, prefetch_count=2)
        result = client.wait(promise)

        result = client.wait(consume_promise, timeout=0.1)
        self.assertEqual(result['body'], 'b')

        result = client.wait(consume_promise, timeout=0.1)
        self.assertEqual(result, None)

        promise = client.queue_delete(queue=self.name)
        client.wait(promise)


    def test_simple_roundtrip_with_heartbeat(self):
        client = puka.Client(self.amqp_url, heartbeat=1)
        promise = client.connect()
        client.wait(promise)

        promise = client.queue_declare(queue=self.name)
        client.wait(promise)

        consume_promise = client.basic_consume(queue=self.name, no_ack=True)
        result = client.wait(consume_promise, timeout=1.1)
        self.assertEqual(result, None)

        promise = client.basic_publish(exchange='', routing_key=self.name,
                                       body=self.msg)
        client.wait(promise)

        result = client.wait(consume_promise)
        self.assertEqual(result['body'], self.msg)

        promise = client.queue_delete(queue=self.name)
        client.wait(promise)



if __name__ == '__main__':
    import tests
    tests.run_unittests(globals())

########NEW FILE########
__FILENAME__ = test_bug3
# https://github.com/majek/puka/issues/3
from __future__ import with_statement

import os
import puka
import random

import base


class TestBug3(base.TestCase):
    def test_bug3_wait(self):
        client = puka.Client(self.amqp_url)
        promise = client.connect()
        client.wait(promise)
        qname = 'test%s' % (random.random(),)
        promise = client.queue_declare(queue=qname)
        client.wait(promise)

        for i in range(3):
            promise = client.basic_publish(exchange='',
                                           routing_key=qname,
                                           body='x')
            client.wait(promise)

        consume_promise = client.basic_consume(qname)
        for i in range(3):
            msg = client.wait(consume_promise)
            client.basic_ack(msg)
            self.assertEqual(msg['body'], 'x')

        client.socket().close()
        self._epilogue(qname, 1)

    def _epilogue(self, qname, expected):
        client = puka.Client(self.amqp_url)
        promise = client.connect()
        client.wait(promise)
        promise = client.queue_declare(queue=qname)
        q = client.wait(promise)
        self.assertEqual(q['message_count'], expected)

        promise = client.queue_delete(queue=qname)
        client.wait(promise)

    def test_bug3_loop(self):
        client = puka.Client(self.amqp_url)
        promise = client.connect()
        client.wait(promise)
        qname = 'test%s' % (random.random(),)
        promise = client.queue_declare(queue=qname)
        client.wait(promise)

        for i in range(3):
            promise = client.basic_publish(exchange='',
                                           routing_key=qname,
                                           body='x')
            client.wait(promise)

        i = [0]
        def cb(_, msg):
            client.basic_ack(msg)
            self.assertEqual(msg['body'], 'x')
            i[0] += 1
            if i[0] == 3:
                client.loop_break()
        consume_promise = client.basic_consume(qname, callback=cb)
        client.loop()

        client.socket().close()
        self._epilogue(qname, 0)


if __name__ == '__main__':
    import tests
    tests.run_unittests(globals())


########NEW FILE########
__FILENAME__ = test_cancel
from __future__ import with_statement

import os
import puka

import base


class TestCancel(base.TestCase):
    @base.connect
    def test_cancel_single(self, client):
        promise = client.queue_declare(queue=self.name)
        client.wait(promise)

        promise = client.basic_publish(exchange='', routing_key=self.name,
                                       body='a')
        client.wait(promise)

        consume_promise = client.basic_consume(queue=self.name, prefetch_count=1)
        result = client.wait(consume_promise)
        self.assertEqual(result['body'], 'a')

        promise = client.basic_cancel(consume_promise)
        result = client.wait(promise)
        self.assertTrue('consumer_tag' in result)

        # TODO: better error
        # It's illegal to wait on consume_promise after cancel.
        #with self.assertRaises(Exception):
        #    client.wait(consume_promise)

        promise = client.queue_delete(queue=self.name)
        client.wait(promise)


    @base.connect
    def test_cancel_multi(self, client):
        names = [self.name, self.name1, self.name2]
        for name in names:
            promise = client.queue_declare(queue=name)
            client.wait(promise)
            promise = client.basic_publish(exchange='', routing_key=name,
                                           body='a')
            client.wait(promise)


        consume_promise = client.basic_consume_multi(queues=names,
                                                     no_ack=True)
        for i in range(len(names)):
            result = client.wait(consume_promise)
            self.assertEqual(result['body'], 'a')

        promise = client.basic_cancel(consume_promise)
        result = client.wait(promise)
        self.assertTrue('consumer_tag' in result)

        # TODO: better error
        #with self.assertRaises(Exception):
        #    client.wait(consume_promise)

        promise = client.queue_delete(queue=self.name)
        client.wait(promise)

    @base.connect
    def test_cancel_single_notification(self, client):
        promise = client.queue_declare(queue=self.name)
        client.wait(promise)

        promise = client.basic_publish(exchange='', routing_key=self.name,
                                       body='a')
        client.wait(promise)

        consume_promise = client.basic_consume(queue=self.name, prefetch_count=1)
        result = client.wait(consume_promise)
        self.assertEqual(result['body'], 'a')

        promise = client.queue_delete(self.name)

        result = client.wait(consume_promise)
        self.assertEqual(result.name, 'basic.cancel_ok')

        # Make sure the consumer died:
        promise = client.queue_declare(queue=self.name)
        result = client.wait(promise)
        self.assertEqual(result['consumer_count'], 0)


    @base.connect
    def test_cancel_multi_notification(self, client):
        names = [self.name, self.name1, self.name2]
        for name in names:
            promise = client.queue_declare(queue=name)
            client.wait(promise)
            promise = client.basic_publish(exchange='', routing_key=name,
                                           body='a')
            client.wait(promise)

        consume_promise = client.basic_consume_multi(queues=names,
                                                     no_ack=True)
        for i in range(len(names)):
            result = client.wait(consume_promise)
            self.assertEqual(result['body'], 'a')

        promise = client.queue_delete(names[0])

        result = client.wait(consume_promise)
        self.assertEqual(result.name, 'basic.cancel_ok')

        # Make sure the consumer died:
        for name in names:
            promise = client.queue_declare(queue=name)
            result = client.wait(promise)
            self.assertEqual(result['consumer_count'], 0)

    @base.connect
    def test_cancel_multi_notification_concurrent(self, client):
        names = [self.name, self.name1, self.name2]
        for name in names:
            promise = client.queue_declare(queue=name)
            client.wait(promise)
            promise = client.basic_publish(exchange='', routing_key=name,
                                           body='a')
            client.wait(promise)

        consume_promise = client.basic_consume_multi(queues=names,
                                                     no_ack=True)
        for i in range(len(names)):
            result = client.wait(consume_promise)
            self.assertEqual(result['body'], 'a')

        client.queue_delete(names[0])
        client.queue_delete(names[2])

        result = client.wait(consume_promise)
        self.assertEqual(result.name, 'basic.cancel_ok')

        # Make sure the consumer died:
        for name in names:
            promise = client.queue_declare(queue=name)
            result = client.wait(promise)
            self.assertEqual(result['consumer_count'], 0)



if __name__ == '__main__':
    import tests
    tests.run_unittests(globals())

########NEW FILE########
__FILENAME__ = test_connection
from __future__ import with_statement

import os
import puka
import puka.connection
import socket

import base

class TestConnection(base.TestCase):
    def test_broken_url(self):
        # Any address that doesn't resolve
        client = puka.Client('amqp://256.256.256.256/')
        with self.assertRaises(socket.gaierror):
            promise = client.connect()

    def test_connection_refused(self):
        client = puka.Client('amqp://127.0.0.1:9999/')
        with self.assertRaises(socket.error):
            # Can raise in connect or on wait
            promise = client.connect()
            client.wait(promise)

    # The following tests take 3 seconds each, due to Rabbit.
    def test_wrong_user(self):
        (username, password, vhost, host, port) = \
            puka.connection.parse_amqp_url(self.amqp_url)

        client = puka.Client('amqp://%s:%s@%s:%s%s' % \
                                 (username, 'wrongpass', host, port, vhost))
        promise = client.connect()
        with self.assertRaises(socket.error):
            client.wait(promise)

    # def test_wrong_vhost(self):
    #     client = puka.Client('amqp:///xxxx')
    #     promise = client.connect()
    #     with self.assertRaises(puka.ConnectionBroken):
    #         client.wait(promise)


if __name__ == '__main__':
    import tests
    tests.run_unittests(globals())


########NEW FILE########
__FILENAME__ = test_consume
from __future__ import with_statement

import os
import puka

import base


class TestBasicConsumeMulti(base.TestCase):
    @base.connect
    def test_shared_qos(self, client):
        promise = client.queue_declare(queue=self.name1)
        client.wait(promise)

        promise = client.queue_declare(queue=self.name2)
        client.wait(promise)


        promise = client.basic_publish(exchange='', routing_key=self.name1,
                                      body='a')
        client.wait(promise)
        promise = client.basic_publish(exchange='', routing_key=self.name2,
                                      body='b')
        client.wait(promise)


        consume_promise = client.basic_consume_multi([self.name1, self.name2],
                                                    prefetch_count=1)
        result = client.wait(consume_promise, timeout=0.1)
        r1 = result['body']
        self.assertTrue(r1 in ['a', 'b'])

        result = client.wait(consume_promise, timeout=0.1)
        self.assertEqual(result, None)

        promise = client.basic_qos(consume_promise, prefetch_count=2)
        result = client.wait(promise)

        result = client.wait(consume_promise, timeout=0.1)
        r2 = result['body']
        self.assertEqual(sorted([r1, r2]), ['a', 'b'])


        promise = client.basic_cancel(consume_promise)
        client.wait(promise)

        promise = client.queue_delete(queue=self.name1)
        client.wait(promise)

        promise = client.queue_delete(queue=self.name2)
        client.wait(promise)


    @base.connect
    def test_access_refused(self, client):
        promise = client.queue_declare(queue=self.name, exclusive=True)
        client.wait(promise)

        promise = client.queue_declare(queue=self.name)
        with self.assertRaises(puka.ResourceLocked):
            client.wait(promise)

        # Testing exclusive basic_consume.
        promise = client.basic_consume(queue=self.name, exclusive=True)
        client.wait(promise, timeout=0.001)

        # Do something synchronus.
        promise = client.queue_declare(exclusive=True)
        client.wait(promise)

        promise = client.basic_consume(queue=self.name)
        with self.assertRaises(puka.AccessRefused):
            client.wait(promise)

        promise = client.queue_delete(queue=self.name)
        client.wait(promise)


    @base.connect
    def test_consumer_tag(self, client):
        # In Puka it's impossible to get `consumer_tag` from
        # basic_consume result. And usually it doesn't matter. But
        # when calling `basic_consume_multi` that starts to be an
        # issue: how to distinguish one queue from another? In #38 we
        # enabled manually specifying consumer tags.

        p1 = client.queue_declare(queue=self.name1)
        p2 = client.queue_declare(queue=self.name2)
        client.wait_for_all([p1, p2])

        # Single consumer, unspecified tag
        promise = client.basic_publish(exchange='', routing_key=self.name1,
                                       body=self.msg)
        client.wait(promise)

        # basic_get doesn't return consumer_tag
        consume_promise = client.basic_consume(queue=self.name1)
        result = client.wait(consume_promise)
        self.assertEqual(result['body'], self.msg)
        self.assertEqual(result['consumer_tag'], '%s.0.' % consume_promise)
        client.basic_ack(result)
        promise = client.basic_cancel(consume_promise)
        result = client.wait(promise)

        # Consume multi
        p1 = client.basic_publish(exchange='', routing_key=self.name1,
                                  body=self.msg1)
        p2 = client.basic_publish(exchange='', routing_key=self.name2,
                                  body=self.msg2)
        client.wait_for_all([p1, p2])

        consume_promise = client.basic_consume_multi([
                self.name1,
                {'queue': self.name2,
                 'consumer_tag': 'whooa!'}])

        for _ in range(2):
            result = client.wait(consume_promise)
            if result['body'] == self.msg1:
                self.assertEqual(result['body'], self.msg1)
                self.assertEqual(result['consumer_tag'],
                                 '%s.0.' % consume_promise)
            else:
                self.assertEqual(result['body'], self.msg2)
                self.assertEqual(result['consumer_tag'],
                                 '%s.1.whooa!' % consume_promise)
            client.basic_ack(result)

        p1 = client.queue_delete(queue=self.name1)
        p2 = client.queue_delete(queue=self.name2)
        client.wait_for_all([p1, p2])


    @base.connect
    def test_consumer_tag_repeated(self, client):
        # In theory consumer_tags are unique. But our users may not
        # know about it. Test puka's behaviour in that case

        p1 = client.queue_declare(queue=self.name1)
        p2 = client.queue_declare(queue=self.name2)
        client.wait_for_all([p1, p2])

        promise = client.basic_publish(exchange='', routing_key=self.name1,
                                       body=self.msg)
        client.wait(promise)

        consume_promise = client.basic_consume_multi([
                {'queue': self.name1,
                 'consumer_tag': 'repeated'},
                {'queue': self.name1,
                 'consumer_tag': 'repeated'},
                {'queue': self.name2,
                 'consumer_tag': 'repeated'}])

        result = client.wait(consume_promise)
        self.assertEqual(result['body'], self.msg)
        ct = result['consumer_tag'].split('.')
        self.assertEqual(ct[0], '%s' % consume_promise)
        self.assertTrue(ct[1] in ('0', '1', '2'))
        self.assertEqual(ct[2], 'repeated')

        p1 = client.queue_delete(queue=self.name1)
        p2 = client.queue_delete(queue=self.name2)
        client.wait_for_all([p1, p2])


if __name__ == '__main__':
    import tests
    tests.run_unittests(globals())


########NEW FILE########
__FILENAME__ = test_exchange
from __future__ import with_statement

import os
import puka
import random

import base


class TestExchange(base.TestCase):
    def test_exchange_redeclare(self):
        client = puka.Client(self.amqp_url)
        promise = client.connect()
        client.wait(promise)

        promise = client.exchange_declare(exchange=self.name)
        r = client.wait(promise)

        promise = client.exchange_declare(exchange=self.name, type='fanout')
        with self.assertRaises(puka.PreconditionFailed):
            client.wait(promise)

        promise = client.exchange_delete(exchange=self.name)
        client.wait(promise)

    def test_exchange_delete_not_found(self):
        client = puka.Client(self.amqp_url)
        promise = client.connect()
        client.wait(promise)

        promise = client.exchange_delete(exchange='not_existing_exchange')

        with self.assertRaises(puka.NotFound):
            client.wait(promise)

    def test_bind(self):
        client = puka.Client(self.amqp_url)
        promise = client.connect()
        client.wait(promise)

        promise = client.exchange_declare(exchange=self.name1, type='fanout')
        client.wait(promise)

        promise = client.exchange_declare(exchange=self.name2, type='fanout')
        client.wait(promise)

        promise = client.queue_declare()
        qname = client.wait(promise)['queue']

        promise = client.queue_bind(queue=qname, exchange=self.name2)
        client.wait(promise)

        promise = client.basic_publish(exchange=self.name1, routing_key='',
                                      body='a')
        client.wait(promise)

        promise = client.exchange_bind(source=self.name1, destination=self.name2)
        client.wait(promise)

        promise = client.basic_publish(exchange=self.name1, routing_key='',
                                      body='b')
        client.wait(promise)

        promise = client.exchange_unbind(source=self.name1,
                                        destination=self.name2)
        client.wait(promise)

        promise = client.basic_publish(exchange=self.name1, routing_key='',
                                      body='c')
        client.wait(promise)

        promise = client.basic_get(queue=qname, no_ack=True)
        r = client.wait(promise)
        self.assertEquals(r['body'], 'b')

        promise = client.basic_get(queue=qname)
        r = client.wait(promise)
        self.assertTrue('empty' in r)

        promise = client.exchange_delete(exchange=self.name1)
        client.wait(promise)
        promise = client.exchange_delete(exchange=self.name2)
        client.wait(promise)
        promise = client.queue_delete(queue=qname)
        client.wait(promise)

        promise = client.close()
        client.wait(promise)


if __name__ == '__main__':
    import tests
    tests.run_unittests(globals())

########NEW FILE########
__FILENAME__ = test_limits
import os
import unittest
import puka
import random
import time

AMQP_URL=os.getenv('AMQP_URL', 'amqp:///')

class TestLimits(unittest.TestCase):
    def test_parallel_queue_declare(self):
        qname = 'test%s' % (random.random(),)
        msg = '%s' % (random.random(),)

        client = puka.Client(AMQP_URL)
        promise = client.connect()
        client.wait(promise)

        queues = [qname+'.%s' % (i,) for i in xrange(100)]
        promises = [client.queue_declare(queue=q) for q in queues]

        for promise in promises:
            client.wait(promise)

        promises = [client.queue_delete(queue=q) for q in queues]
        for promise in promises:
            client.wait(promise)


########NEW FILE########
__FILENAME__ = test_publish_async
from __future__ import with_statement

import os
import puka
import random
import socket

import base


class TestPublishAsync(base.TestCase):
    pubacks = None
    def test_simple_roundtrip(self):
        client = puka.Client(self.amqp_url, pubacks=self.pubacks)
        promise = client.connect()
        client.wait(promise)

        promise = client.queue_declare(queue=self.name)
        client.wait(promise)

        promise = client.basic_publish(exchange='', routing_key=self.name,
                                       body=self.msg)
        client.wait(promise)

        consume_promise = client.basic_consume(queue=self.name, no_ack=False)

        msg = client.wait(consume_promise)
        self.assertEqual(msg['body'], self.msg)

        client.basic_ack(msg)

        result = client.wait(consume_promise, timeout=0.1)
        self.assertEqual(result, None)

        promise = client.queue_delete(queue=self.name)
        client.wait(promise)

    def test_big_failure(self):
        client = puka.Client(self.amqp_url, pubacks=self.pubacks)
        promise = client.connect()
        client.wait(promise)

        # synchronize publish channel - give time for chanel-open
        promise = client.queue_declare(queue=self.name)
        client.wait(promise)

        promise1 = client.basic_publish(exchange='', routing_key='',
                                        body=self.msg)
        promise2 = client.basic_publish(exchange='wrong_exchange',
                                        routing_key='',
                                        body=self.msg)
        promise3 = client.basic_publish(exchange='', routing_key='',
                                        body=self.msg)
        client.wait(promise1)
        with self.assertRaises(puka.NotFound):
            client.wait(promise2)
        with self.assertRaises(puka.NotFound):
            client.wait(promise3)

        # validate if it still works
        promise = client.basic_publish(exchange='', routing_key='',
                                       body=self.msg)
        client.wait(promise)

        # and fail again.
        promise = client.basic_publish(exchange='wrong_exchange',
                                       routing_key='',
                                       body=self.msg)
        with self.assertRaises(puka.NotFound):
            client.wait(promise)

        # and validate again
        promise = client.basic_publish(exchange='', routing_key='',
                                       body=self.msg)
        client.wait(promise)

        promise = client.queue_delete(queue=self.name)
        client.wait(promise)

    def test_return(self):
        client = puka.Client(self.amqp_url, pubacks=self.pubacks)
        promise = client.connect()
        client.wait(promise)

        promise = client.basic_publish(exchange='', routing_key='',
                                       body=self.msg, mandatory=True)
        with self.assertRaises(puka.NoRoute):
            client.wait(promise)


    def test_return_2(self):
        client = puka.Client(self.amqp_url, pubacks=self.pubacks)
        promise = client.connect()
        client.wait(promise)

        promise = client.queue_declare(queue=self.name)
        client.wait(promise)

        promise = client.basic_publish(exchange='', routing_key='badname',
                                       mandatory=True, body=self.msg)
        try:
            client.wait(promise)
        except puka.NoRoute, (response,):
            pass

        self.assertEqual(response['reply_code'], 312)

        promise = client.queue_delete(queue=self.name)
        client.wait(promise)


    def test_simple_basic_get(self):
        client = puka.Client(self.amqp_url, pubacks=self.pubacks)
        promise = client.connect()
        client.wait(promise)

        promise = client.queue_declare(queue=self.name)
        client.wait(promise)

        promise = client.basic_publish(exchange='', routing_key=self.name,
                                       body=self.msg)
        client.wait(promise)

        promise = client.basic_get(queue=self.name)
        result = client.wait(promise)
        self.assertEqual(result['body'], self.msg)
        client.basic_ack(result)

        promise = client.basic_get(queue=self.name)
        result = client.wait(promise)
        self.assertTrue(result['empty'])

        promise = client.queue_delete(queue=self.name)
        client.wait(promise)


    def test_bug21(self):
        # Following the testcase: https://github.com/majek/puka/issues/21
        client = puka.Client(self.amqp_url, pubacks=self.pubacks)
        promise = client.connect()
        client.wait(promise)

        promises = []
        for i in range(0, 42):
            promise = client.basic_publish('', 'test_key', 'test_body')
            self.assertTrue(len(client.send_buf) > 0)
            promises.append(promise)

        #client.wait(promises)



class TestPublishAsyncPubacksTrue(TestPublishAsync):
    pubacks = True

class TestPublishAsyncPubacksFalse(TestPublishAsync):
    pubacks = False

class TestPublishAckDetection(base.TestCase):
    # Assuming reasonably recent RabbitMQ server (which does pubacks).
    def test_pubacks(self):
        client = puka.Client(self.amqp_url)
        promise = client.connect()
        r = client.wait(promise)
        self.assertEqual(client.pubacks, None)
        self.assertTrue(r['server_properties']['capabilities']\
                            ['publisher_confirms'])
        self.assertTrue(client.x_pubacks)


if __name__ == '__main__':
    import tests
    tests.run_unittests(globals())

########NEW FILE########
__FILENAME__ = test_queue
from __future__ import with_statement

import os
import puka
import random
import unittest_backport as unittest


AMQP_URL=os.getenv('AMQP_URL', 'amqp:///')

class TestQueue(unittest.TestCase):
    def test_queue_declare(self):
        qname = 'test%s-this-queue-should-be-autodeleted' % (random.random(),)

        client = puka.Client(AMQP_URL)
        promise = client.connect()
        client.wait(promise)

        promise = client.queue_declare(queue=qname, auto_delete=True)
        client.wait(promise)
        # The queue intentionally left hanging. Should be autoremoved.
        # Yes, no assertion here, we don't want to wait for 5 seconds.

    def test_queue_redeclare(self):
        qname = 'test%s' % (random.random(),)

        client = puka.Client(AMQP_URL)
        promise = client.connect()
        client.wait(promise)

        promise = client.queue_declare(queue=qname, auto_delete=False)
        r = client.wait(promise)

        promise = client.queue_declare(queue=qname, auto_delete=False)
        r = client.wait(promise)

        promise = client.queue_declare(queue=qname, auto_delete=True)
        with self.assertRaises(puka.PreconditionFailed):
            client.wait(promise)

        promise = client.queue_delete(queue=qname)
        client.wait(promise)


    def test_queue_redeclare_args(self):
        qname = 'test%s' % (random.random(),)

        client = puka.Client(AMQP_URL)
        promise = client.connect()
        client.wait(promise)

        promise = client.queue_declare(queue=qname, arguments={})
        r = client.wait(promise)

        promise = client.queue_declare(queue=qname, arguments={'x-expires':101})
        with self.assertRaises(puka.PreconditionFailed):
            client.wait(promise)

        promise = client.queue_delete(queue=qname)
        client.wait(promise)


    def test_queue_delete_not_found(self):
        client = puka.Client(AMQP_URL)
        promise = client.connect()
        client.wait(promise)

        promise = client.queue_delete(queue='not_existing_queue')

        with self.assertRaises(puka.NotFound):
            client.wait(promise)


    def test_queue_bind(self):
        qname = 'test%s' % (random.random(),)

        client = puka.Client(AMQP_URL)
        promise = client.connect()
        client.wait(promise)

        t = client.queue_declare(queue=qname)
        client.wait(t)

        t = client.exchange_declare(exchange=qname, type='direct')
        client.wait(t)

        t = client.basic_publish(exchange=qname, routing_key=qname, body='a')
        client.wait(t)

        t = client.queue_bind(exchange=qname, queue=qname, routing_key=qname)
        client.wait(t)

        t = client.basic_publish(exchange=qname, routing_key=qname, body='b')
        client.wait(t)

        t = client.queue_unbind(exchange=qname, queue=qname, routing_key=qname)
        client.wait(t)

        t = client.basic_publish(exchange=qname, routing_key=qname, body='c')
        client.wait(t)

        t = client.basic_get(queue=qname)
        r = client.wait(t)
        self.assertEquals(r['body'], 'b')
        self.assertEquals(r['message_count'], 0)

        t = client.queue_delete(queue=qname)
        client.wait(t)

        t = client.exchange_delete(exchange=qname)
        client.wait(t)


########NEW FILE########
__FILENAME__ = unittest_backport
# Unittest in 2.7 have few interesting features.
#
# This code is licensed on PSF.
# Original source: Python-2.7/Lib/unittest/case.py
#
from __future__ import with_statement

from unittest import *
import unittest

class _AssertRaisesContext(object):
    """A context manager used to implement TestCase.assertRaises* methods."""

    def __init__(self, expected, test_case, expected_regexp=None):
        self.expected = expected
        self.failureException = test_case.failureException
        self.expected_regexp = expected_regexp

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, tb):
        if exc_type is None:
            try:
                exc_name = self.expected.__name__
            except AttributeError:
                exc_name = str(self.expected)
            raise self.failureException(
                "{0} not raised".format(exc_name))
        if not issubclass(exc_type, self.expected):
            # let unexpected exceptions pass through
            return False
        self.exception = exc_value # store for later retrieval
        if self.expected_regexp is None:
            return True

        expected_regexp = self.expected_regexp
        if isinstance(expected_regexp, basestring):
            expected_regexp = re.compile(expected_regexp)
        if not expected_regexp.search(str(exc_value)):
            raise self.failureException('"%s" does not match "%s"' %
                     (expected_regexp.pattern, str(exc_value)))
        return True


class TestCase(unittest.TestCase):
    def assertRaises(self, excClass, callableObj=None, *args, **kwargs):
        """Fail unless an exception of class excClass is thrown
           by callableObj when invoked with arguments args and keyword
           arguments kwargs. If a different type of exception is
           thrown, it will not be caught, and the test case will be
           deemed to have suffered an error, exactly as for an
           unexpected exception.

           If called with callableObj omitted or None, will return a
           context object used like this::

                with self.assertRaises(SomeException):
                    do_something()

           The context manager keeps a reference to the exception as
           the 'exception' attribute. This allows you to inspect the
           exception after the assertion::

               with self.assertRaises(SomeException) as cm:
                   do_something()
               the_exception = cm.exception
               self.assertEqual(the_exception.error_code, 3)
        """
        context = _AssertRaisesContext(excClass, self)
        if callableObj is None:
            return context
        with context:
            callableObj(*args, **kwargs)


########NEW FILE########
