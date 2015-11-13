__FILENAME__ = example1
#!/usr/bin/env python
# =============================================================================
# Example 1 - How to read & write a record list.
#  - testWrite(): Write 10 record to a new file, and write schema)
#  - testAppend(): Append 10 record to previously created file,
#                  The schema is read from file.
#  - testRead(): Read the file and print the records.
# =============================================================================

from avro.datafile import DataFileWriter, DataFileReader
from avro.io import DatumWriter, DatumReader
import avro.schema

TEST_SCHEMA = """
{
    "type": "record",
    "name": "person",
    "fields": [
                { "name": "name", "type": "string" },
                { "name": "company", "type": "string" },
                { "name": "website", "type": { "type": "array", "items": "string" }}
              ]
}
"""

def _makeTestPerson(uid):
    return {'name':'Person %d' % uid,
            'company':'Company %d' % uid,
            'website': ['http://myurl%d.net' % i for i in xrange(uid % 5)],
            }

def testWrite(filename):
    schema_object = avro.schema.parse(TEST_SCHEMA)

    fd = open(filename, 'wb')
    datum_writer = DatumWriter()
    fwriter = DataFileWriter(fd, datum_writer, schema_object)
    for i in xrange(10):
        fwriter.append(_makeTestPerson(i))
    fwriter.close()

def testAppend(filename):
    fd = open(filename, 'a+b')
    datum_writer = DatumWriter()
    fwriter = DataFileWriter(fd, datum_writer)
    for i in xrange(10, 20):
        fwriter.append(_makeTestPerson(i))
    fwriter.close()

def testRead(filename):
    fd = open(filename, 'rb')
    datum_writer = DatumReader()
    freader = DataFileReader(fd, datum_writer)
    for datum in freader:
        print datum['name'], datum['company']
        print datum['website']
        print
    freader.close()

if __name__ == '__main__':
    FILENAME = 'test.db'
    testWrite(FILENAME)
    testAppend(FILENAME)
    testRead(FILENAME)


########NEW FILE########
__FILENAME__ = test-file
#!/usr/bin/env python

from avro import schema
from avro.io import DatumWriter, DatumReader
from avro.datafile import DataFileWriter, DataFileReader

def makeSchema():
    json_schema = """
                    {
                     "type":"record",
                     "name":"Person",
                     "namespace":"avro.test",
                     "fields":[
                        {"name":"name","type":"string"},
                        {"name":"age","type":"int"}]
                    }
                 """
    return schema.parse(json_schema);

def makeObject(name, age):
    return {'name': name, 'age': age}

def testWrite(filename, schema):
    fd = open(filename, 'wb')

    datum = DatumWriter()
    writer = DataFileWriter(fd, datum, schema)

    writer.append(makeObject("Person A", 23))
    writer.append(makeObject("Person B", 31))
    writer.append(makeObject("Person C", 28))

    writer.close()

def testRead(filename):
    fd = open(filename, 'rb')

    datum = DatumReader()
    reader = DataFileReader(fd, datum)

    for record in reader:
        print record['name'], record['age']

    reader.close()

if __name__ == '__main__':
    filename = 'test-file.avro'
    schema = makeSchema()

    testWrite(filename, schema)
    testRead(filename)

########NEW FILE########
__FILENAME__ = ht-client
#!/usr/bin/env python
# ==================================================
# Simple key/value storage client using Avro IPC
# put(key, value), get(key), delete(key)

from avro import protocol
from avro import ipc

_PROTO = protocol.parse(file('ht-proto.avpr').read())

class HTClient(object):
    def __init__(self, host, port):
        self._host = host
        self._port = port

    def get(self, key):
        return self._request('get', {'key': key})

    def put(self, key, value):
        return self._request('put', {'key': key, 'value': value})

    def delete(self, key):
        return self._request('delete', {'key': key})

    def _request(self, msg, args):
        transceiver = ipc.HTTPTransceiver(self._host, self._port)
        requestor = ipc.Requestor(_PROTO, transceiver)
        response = requestor.request(msg, args)
        transceiver.close()
        return response

if __name__ == '__main__':
    client = HTClient('localhost', 8080)

    def _testGet(client):
        for i in xrange(12):
            key = 'Key %d' % i
            value = client.get(key)
            print 'GET %s %r' % (key, value)


    for i in xrange(10):
        client.put('Key %d' % i, 'Value %d' % i)
    _testGet(client)

    for i in xrange(10):
        client.delete('Key %d' % i)
    _testGet(client)



########NEW FILE########
__FILENAME__ = ht-server
#!/usr/bin/env python
# ==================================================
# Simple key/value storage server using Avro IPC
# put(key, value), get(key), delete(key)

from BaseHTTPServer import BaseHTTPRequestHandler
from BaseHTTPServer import HTTPServer

from avro.ipc import AvroRemoteException
from avro import protocol
from avro import ipc

_PROTO = protocol.parse(file('ht-proto.avpr').read())
_STORAGE = {}

class Responder(ipc.Responder):
    def __init__(self):
        super(Responder, self).__init__(_PROTO)

    def invoke(self, msg, req):
        global _STORAGE
        if msg.name == 'get':
            return _STORAGE.get(req['key'])
        elif msg.name == 'put':
            _STORAGE[req['key']] = req['value']
        elif msg.name == 'delete':
            req_key = req['key']
            if req_key in _STORAGE:
                del _STORAGE[req_key]
        else:
            raise AvroRemoteException("unexpected message: " % msg.name)

class RequestHandler(BaseHTTPRequestHandler):
    def do_POST(self):
        request_reader = ipc.FramedReader(self.rfile)
        request = request_reader.read_framed_message()

        responder = Responder()
        response_body = responder.respond(request)

        self.send_response(200)
        self.send_header('Content-Type', 'avro/binary')
        self.end_headers()

        response_writer = ipc.FramedWriter(self.wfile)
        response_writer.write_framed_message(response_body)

if __name__ == '__main__':
    server = HTTPServer(('localhost', 8080), RequestHandler)
    server.allow_reuse_address = True
    server.serve_forever()


########NEW FILE########
__FILENAME__ = test-client
#!/usr/bin/env python

from avro import protocol
from avro import ipc

if __name__ == '__main__':
    proto = protocol.parse(file('test-proto.avpr').read())

    client = ipc.HTTPTransceiver('localhost', 8080)
    requestor = ipc.Requestor(proto, client)

    message = {'data': 'Hello from client'}
    result = requestor.request('xyz', {'message': message})
    print result

    client.close()

########NEW FILE########
__FILENAME__ = test-server
#!/usr/bin/env python

from BaseHTTPServer import BaseHTTPRequestHandler
from BaseHTTPServer import HTTPServer

from avro.ipc import AvroRemoteException
from avro import protocol
from avro import ipc

_PROTO = protocol.parse(file('test-proto.avpr').read())

class Responder(ipc.Responder):
    def __init__(self):
        super(Responder, self).__init__(_PROTO)

    def invoke(self, msg, req):
        print 'invoke', msg, req
        if msg.name == 'xyz':
            return "The python responder greets you."
        else:
            raise AvroRemoteException("unexpected message: " % msg.name)

class RequestHandler(BaseHTTPRequestHandler):
    def do_POST(self):
        request_reader = ipc.FramedReader(self.rfile)
        request = request_reader.read_framed_message()

        responder = Responder()
        response_body = responder.respond(request)

        self.send_response(200)
        self.send_header('Content-Type', 'avro/binary')
        self.end_headers()

        response_writer = ipc.FramedWriter(self.wfile)
        response_writer.write_framed_message(response_body)

if __name__ == '__main__':
    server = HTTPServer(('localhost', 8080), RequestHandler)
    server.allow_reuse_address = True
    server.serve_forever()


########NEW FILE########
__FILENAME__ = jhadoop
#!/usr/bin/env python
# Helper to compile & execute Single file java demo.
# Usage:
#      compile with -> jhadoop TestFile.java
#      execute with -> jhadoop TestFile.class
# Remember to export:
#   HADOOP_COMMON_HOME
#   HADOOP_HDFS_HOME
#   HADOOP_MAPRED_HOME
#   HBASE_HOME

from commands import getstatusoutput as execCommand
import mimetypes
import sys
import os

def hadoopClassPath():
    def _findJars(paths):
        jars = {'.':'.'}
        for path in paths:
            if path is None:
                continue

            for root, dirs, files in os.walk(path, topdown=False):
                for name in files:
                    if name.endswith('.jar'):
                        jars[name] = os.path.join(root, name)
        return jars.values()

    hadoop_env = ('HADOOP_COMMON_HOME',
                  'HADOOP_HDFS_HOME',
                  'HADOOP_MAPRED_HOME',
                  'HBASE_HOME',
                 )

    return ':'.join(_findJars(os.getenv(henv) for henv in reversed(hadoop_env)))

if __name__ == '__main__':
    if len(sys.argv) < 1:
        print 'usage:'
        print '     jhadoop FileName.java'
        print '     jhadoop FileName.class'
        sys.exit(1)

    mime, _ = mimetypes.guess_type(sys.argv[1])
    if mime == 'text/x-java':
        sources = ' '.join(sys.argv[1:])
        cmd = 'javac -classpath %s %s' % (hadoopClassPath(), sources)
    elif mime == 'application/java-vm':
        cmd = 'java -classpath %s %s' % (hadoopClassPath(), sys.argv[1][:-6])
    else:
        raise TypeError(mime)

    exit_code, output = execCommand(cmd)
    print output


########NEW FILE########
__FILENAME__ = ArrayFileTest
#!/usr/bin/env python
# ========================================================================
# Licensed to the Apache Software Foundation (ASF) under one
# or more contributor license agreements.  See the NOTICE file
# distributed with this work for additional information
# regarding copyright ownership.  The ASF licenses this file
# to you under the Apache License, Version 2.0 (the
# "License"); you may not use this file except in compliance
# with the License.  You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from hadoop.io.IntWritable import LongWritable, IntWritable
from hadoop.io import ArrayFile

if __name__ == '__main__':
    writer = ArrayFile.Writer('array-test', IntWritable)
    writer.INDEX_INTERVAL = 16
    for i in xrange(0, 100):
        writer.append(IntWritable(1 + i * 10))
    writer.close()

    key = LongWritable()
    value = IntWritable()
    reader = ArrayFile.Reader('array-test')
    while reader.next(key, value):
        print key, value

    print 'GET 8'
    print reader.get(8, value)
    print value
    print

    print 'GET 110'
    print reader.get(110, value)
    print

    print 'GET 25'
    print reader.get(25, value)
    print value
    print

    print 'GET 55'
    print reader.get(55, value)
    print value
    print

    reader.close()

########NEW FILE########
__FILENAME__ = MapFileTest
#!/usr/bin/env python
# ========================================================================
# Licensed to the Apache Software Foundation (ASF) under one
# or more contributor license agreements.  See the NOTICE file
# distributed with this work for additional information
# regarding copyright ownership.  The ASF licenses this file
# to you under the Apache License, Version 2.0 (the
# "License"); you may not use this file except in compliance
# with the License.  You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from hadoop.io.IntWritable import LongWritable
from hadoop.io import MapFile

if __name__ == '__main__':
    writer = MapFile.Writer('map-test', LongWritable, LongWritable)
    writer.INDEX_INTERVAL = 2
    for i in xrange(0, 100, 2):
        writer.append(LongWritable(i), LongWritable(i * 10))
    writer.close()

    key = LongWritable()
    value = LongWritable()
    reader = MapFile.Reader('map-test')
    while reader.next(key, value):
        print key, value

    print 'MID KEY', reader.midKey()
    print 'FINAL KEY', reader.finalKey(key), key

    print 'GET CLOSEST'
    key.set(8)
    print reader.get(key, value)
    print value
    print

    print 'GET 111'
    key.set(111)
    print reader.get(key, value)
    print

    key.set(25)
    print 'SEEK 25 before'
    print reader.getClosest(key, value, before=True)
    print value
    print

    key.set(55)
    print 'SEEK 55'
    print reader.getClosest(key, value)
    print value
    print

    reader.close()

########NEW FILE########
__FILENAME__ = SequenceFileMeta
#!/usr/bin/env python
# ========================================================================
# Licensed to the Apache Software Foundation (ASF) under one
# or more contributor license agreements.  See the NOTICE file
# distributed with this work for additional information
# regarding copyright ownership.  The ASF licenses this file
# to you under the Apache License, Version 2.0 (the
# "License"); you may not use this file except in compliance
# with the License.  You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from hadoop.io.SequenceFile import CompressionType
from hadoop.io.SequenceFile import Metadata
from hadoop.io import LongWritable
from hadoop.io import SequenceFile

def writeData(writer):
    key = LongWritable()
    value = LongWritable()

    for i in xrange(10):
        key.set(1000 - i)
        value.set(i)
        print '[%d] %s %s' % (writer.getLength(), key.toString(), value.toString())
        writer.append(key, value)

def testWrite(filename):
    metadata = Metadata()
    metadata.set('Meta Key 0', 'Meta Value 0')
    metadata.set('Meta Key 1', 'Meta Value 1')

    writer = SequenceFile.createWriter(filename, LongWritable, LongWritable, metadata)
    writeData(writer)
    writer.close()

def testRead(filename):
    reader = SequenceFile.Reader(filename)

    metadata = reader.getMetadata()
    for meta_key, meta_value in metadata:
        print 'METADATA:', meta_key, meta_value

    key_class = reader.getKeyClass()
    value_class = reader.getValueClass()

    key = key_class()
    value = value_class()

    position = reader.getPosition()
    while reader.next(key, value):
        print '*' if reader.syncSeen() else ' ',
        print '[%6s] %6s %6s' % (position, key.toString(), value.toString())
        position = reader.getPosition()

    reader.close()

if __name__ == '__main__':
    filename = 'test-meta.seq'
    testWrite(filename)
    testRead(filename)

########NEW FILE########
__FILENAME__ = SequenceFileReader
#!/usr/bin/env python
# ========================================================================
# Licensed to the Apache Software Foundation (ASF) under one
# or more contributor license agreements.  See the NOTICE file
# distributed with this work for additional information
# regarding copyright ownership.  The ASF licenses this file
# to you under the Apache License, Version 2.0 (the
# "License"); you may not use this file except in compliance
# with the License.  You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import sys

from hadoop.io import SequenceFile

if __name__ == '__main__':
    if len(sys.argv) < 2:
        print 'usage: SequenceFileReader <filename>'
    else:
        reader = SequenceFile.Reader(sys.argv[1])

        key_class = reader.getKeyClass()
        value_class = reader.getValueClass()

        key = key_class()
        value = value_class()

        #reader.sync(4042)
        position = reader.getPosition()
        while reader.next(key, value):
            print '*' if reader.syncSeen() else ' ',
            print '[%6s] %6s %6s' % (position, key.toString(), value.toString())
            position = reader.getPosition()

        reader.close()


########NEW FILE########
__FILENAME__ = SequenceFileWriterDemo
#!/usr/bin/env python
# ========================================================================
# Licensed to the Apache Software Foundation (ASF) under one
# or more contributor license agreements.  See the NOTICE file
# distributed with this work for additional information
# regarding copyright ownership.  The ASF licenses this file
# to you under the Apache License, Version 2.0 (the
# "License"); you may not use this file except in compliance
# with the License.  You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from hadoop.io.SequenceFile import CompressionType
from hadoop.io import LongWritable
from hadoop.io import SequenceFile

def writeData(writer):
    key = LongWritable()
    value = LongWritable()

    for i in xrange(1000):
        key.set(1000 - i)
        value.set(i)
        print '[%d] %s %s' % (writer.getLength(), key.toString(), value.toString())
        writer.append(key, value)

if __name__ == '__main__':
    writer = SequenceFile.createWriter('test.seq', LongWritable, LongWritable)
    writeData(writer)
    writer.close()

    writer = SequenceFile.createWriter('test-record.seq', LongWritable, LongWritable, compression_type=CompressionType.RECORD)
    writeData(writer)
    writer.close()

    writer = SequenceFile.createWriter('test-block.seq', LongWritable, LongWritable, compression_type=CompressionType.BLOCK)
    writeData(writer)
    writer.close()


########NEW FILE########
__FILENAME__ = SetFileTest
#!/usr/bin/env python
# ========================================================================
# Licensed to the Apache Software Foundation (ASF) under one
# or more contributor license agreements.  See the NOTICE file
# distributed with this work for additional information
# regarding copyright ownership.  The ASF licenses this file
# to you under the Apache License, Version 2.0 (the
# "License"); you may not use this file except in compliance
# with the License.  You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from hadoop.io.IntWritable import IntWritable
from hadoop.io import SetFile

if __name__ == '__main__':
    writer = SetFile.Writer('set-test', IntWritable)
    writer.INDEX_INTERVAL = 16
    for i in xrange(0, 100, 2):
        writer.append(IntWritable(i * 10))
    writer.close()

    key = IntWritable()
    reader = SetFile.Reader('set-test')
    while reader.next(key):
        print key

    print 'GET 8'
    key.set(8)
    print reader.get(key)
    print

    print 'GET 120'
    key.set(120)
    print reader.get(key)
    print

    print 'GET 240'
    key.set(240)
    print reader.get(key)
    print

    print 'GET 550'
    key.set(550)
    print reader.get(key)
    print

    reader.close()

########NEW FILE########
__FILENAME__ = TestText
#!/usr/bin/env python
# ========================================================================
# Licensed to the Apache Software Foundation (ASF) under one
# or more contributor license agreements.  See the NOTICE file
# distributed with this work for additional information
# regarding copyright ownership.  The ASF licenses this file
# to you under the Apache License, Version 2.0 (the
# "License"); you may not use this file except in compliance
# with the License.  You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from hadoop.io.SequenceFile import CompressionType
from hadoop.io import Text
from hadoop.io import SequenceFile

def writeData(writer):
    key = Text()
    value = Text()

    key.set('Key')
    value.set('Value')

    writer.append(key, value)

if __name__ == '__main__':
    writer = SequenceFile.createWriter('test.seq', Text, Text)
    writeData(writer)
    writer.close()

########NEW FILE########
__FILENAME__ = ArrayFile
#!/usr/bin/env python
# ========================================================================
# Licensed to the Apache Software Foundation (ASF) under one
# or more contributor license agreements.  See the NOTICE file
# distributed with this work for additional information
# regarding copyright ownership.  The ASF licenses this file
# to you under the Apache License, Version 2.0 (the
# "License"); you may not use this file except in compliance
# with the License.  You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from IntWritable import LongWritable
import MapFile

class Writer(MapFile.Writer):
    def __init__(self, path, value_class):
        super(Writer, self).__init__(path, LongWritable, value_class)
        self._count = 0

    def append(self, value):
        super(Writer, self).append(LongWritable(self._count), value)
        self._count += 1

class Reader(MapFile.Reader):
    def __init__(self, path):
        super(Reader, self).__init__(path)
        self._key = LongWritable(0)

    def seek(self, n):
        if isinstance(n, LongWritable):
            n = n.get()

        self._key.set(n)
        return super(Reader, self).seek(self._key)

    def key(self):
        return self._key.get()

    def get(self, n, value):
        self._key.set(n)
        return(super(Reader, self).get(self._key, value))


########NEW FILE########
__FILENAME__ = BZip2Codec
#!/usr/bin/env python
# ========================================================================
# Licensed to the Apache Software Foundation (ASF) under one
# or more contributor license agreements.  See the NOTICE file
# distributed with this work for additional information
# regarding copyright ownership.  The ASF licenses this file
# to you under the Apache License, Version 2.0 (the
# "License"); you may not use this file except in compliance
# with the License.  You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import bz2

from hadoop.io.InputStream import DataInputBuffer

class BZip2Codec:
    def compress(self, data):
        return bz2.compress(data)

    def decompress(self, data):
        return bz2.decompress(data)

    def decompressInputStream(self, data):
        return DataInputBuffer(bz2.decompress(data))


########NEW FILE########
__FILENAME__ = CodecPool
#!/usr/bin/env python
# ========================================================================
# Licensed to the Apache Software Foundation (ASF) under one
# or more contributor license agreements.  See the NOTICE file
# distributed with this work for additional information
# regarding copyright ownership.  The ASF licenses this file
# to you under the Apache License, Version 2.0 (the
# "License"); you may not use this file except in compliance
# with the License.  You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from hadoop.util import ReflectionUtils

from BZip2Codec import *
from ZlibCodec import *
from GzipCodec import *

class CodecPool(object):
    def __new__(cls, *p, **k):
        if not '_shared_instance' in cls.__dict__:
            cls._shared_instance = object.__new__(cls)
        return cls._shared_instance

    def getDecompressor(self, class_path=None):
        if not class_path:
            return DefaultCodec()
        codec_class = ReflectionUtils.hadoopClassFromName(class_path)
        return codec_class()

    def getCompressor(self, class_path=None):
        if not class_path:
            return DefaultCodec()
        codec_class = ReflectionUtils.hadoopClassFromName(class_path)
        return codec_class()


########NEW FILE########
__FILENAME__ = GzipCodec
#!/usr/bin/env python
# ========================================================================
# Licensed to the Apache Software Foundation (ASF) under one
# or more contributor license agreements.  See the NOTICE file
# distributed with this work for additional information
# regarding copyright ownership.  The ASF licenses this file
# to you under the Apache License, Version 2.0 (the
# "License"); you may not use this file except in compliance
# with the License.  You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import gzip

from hadoop.io.InputStream import DataInputBuffer
import StringIO

class GzipCodec:
    def compress(self, data):
        ioObj = StringIO.StringIO()
        f = gzip.GzipFile(fileobj = ioObj, mode='wb')
        f.write(data)
        f.close()
        return ioObj.getValue()

    def decompress(self, data):
        ioObj = StringIO.StringIO(data)
        f = gzip.GzipFile(fileobj = ioObj, mode='rb')
        d = f.read()
        f.close()
        return d

    def decompressInputStream(self, data):
        return DataInputBuffer(self.decompress(data))

########NEW FILE########
__FILENAME__ = ZlibCodec
#!/usr/bin/env python
# ========================================================================
# Licensed to the Apache Software Foundation (ASF) under one
# or more contributor license agreements.  See the NOTICE file
# distributed with this work for additional information
# regarding copyright ownership.  The ASF licenses this file
# to you under the Apache License, Version 2.0 (the
# "License"); you may not use this file except in compliance
# with the License.  You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import zlib

from hadoop.io.InputStream import DataInputBuffer

class ZlibCodec:
    def compress(self, data):
        return zlib.compress(data)

    def decompress(self, data):
        return zlib.decompress(data)

    def decompressInputStream(self, data):
        return DataInputBuffer(zlib.decompress(data))

DefaultCodec = ZlibCodec


########NEW FILE########
__FILENAME__ = FloatWritable
#!/usr/bin/env python
# ========================================================================
# Licensed to the Apache Software Foundation (ASF) under one
# or more contributor license agreements.  See the NOTICE file
# distributed with this work for additional information
# regarding copyright ownership.  The ASF licenses this file
# to you under the Apache License, Version 2.0 (the
# "License"); you may not use this file except in compliance
# with the License.  You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from Writable import AbstractValueWritable

class FloatWritable(AbstractValueWritable):
    def write(self, data_output):
        data_output.writeFloat(self._value)

    def readFields(self, data_input):
        self._value = data_input.readFloat()

class DoubleWritable(AbstractValueWritable):
    def write(self, data_output):
        data_output.writeDouble(self._value)

    def readFields(self, data_input):
        self._value = data_input.readDouble()


########NEW FILE########
__FILENAME__ = InputStream
#!/usr/bin/env python
# ========================================================================
# Licensed to the Apache Software Foundation (ASF) under one
# or more contributor license agreements.  See the NOTICE file
# distributed with this work for additional information
# regarding copyright ownership.  The ASF licenses this file
# to you under the Apache License, Version 2.0 (the
# "License"); you may not use this file except in compliance
# with the License.  You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import struct
import os

class InputStream(object):
    def available(self):
        raise NotImplementedError

    def close(self):
        raise NotImplementedError

    def mark(self, read_limit):
        raise NotImplementedError

    def markSupported(self):
        raise NotImplementedError

    def readByte(self):
        return self.read(1)

    def read(self, length):
        raise NotImplementedError

    def reset(self):
        raise NotImplementedError

    def skip(self, n):
        raise NotImplementedError

class ByteArrayInputStream(InputStream):
    def __init__(self, data='', offset=0, length=0):
        self.reset(data, offset, length)

    def size(self):
        return self._count - self._offset

    def toByteArray(self):
        return self._buffer[self._offset:self._offset+self._count]

    def reset(self, data, offset=0, length=0):
        if data and not length:
            length = len(data) - offset
        self._buffer = data
        self._offset = offset
        self._count = length

    def close(self):
        pass

    def flush(self):
        pass

    def read(self, length):
        data = self._buffer[self._offset:self._offset+length]
        self._offset += length
        return data

class FileInputStream(InputStream):
    def __init__(self, path):
        self._fd = open(path, 'rb')
        self._length = os.path.getsize(path)

    def length(self):
        return self._length

    def close(self):
        self._fd.close()

    def seek(self, offset):
        self._fd.seek(offset)

    def getPos(self):
        return self._fd.tell()

    def readByte(self):
        return self._fd.read(1)

    def read(self, length):
        byte_buffer = []
        while length > 0:
            data = self._fd.read(length)
            if not data:
                break

            data_length = len(data)
            byte_buffer.append(data)
            length -= data_length
        return ''.join(byte_buffer)

    def skip(self, n):
        skip_length = 0
        while n > 0:
            data = self._fd.read(n)
            if not data:
                break

            data_length = len(data)
            skip_length += data_length
            n -= data_length
        return skip_length

class DataInputStream(InputStream):
    def __init__(self, input_stream):
        assert isinstance(input_stream, InputStream)
        self._stream = input_stream

    def close(self):
        return self._stream.close()

    def seek(self, offset):
        return self._stream.seek(offset)

    def getPos(self):
        return self._stream.getPos()

    def length(self):
        return self._stream.length()

    def read(self, length):
        return self._stream.read(length)

    def readByte(self):
        data = self._stream.read(1)
        return struct.unpack(">b", data)[0]

    def readUByte(self):
        data = self._stream.read(1)
        return struct.unpack("B", data)[0]

    def readBoolean(self):
        data = self._stream.read(1)
        return struct.unpack(">?", data)[0]

    def readInt(self):
        data = self._stream.read(4)
        return struct.unpack(">i", data)[0]

    def readLong(self):
        data = self._stream.read(8)
        return struct.unpack(">q", data)[0]

    def readFloat(self):
        data = self._stream.read(4)
        return struct.unpack(">f", data)[0]

    def readDouble(self):
        data = self._stream.read(8)
        return struct.unpack(">d", data)[0]

    def skipBytes(self, n):
        return self._stream.skip(n)

class DataInputBuffer(DataInputStream):
    def __init__(self, data='', offset=0, length=0):
        input_stream = ByteArrayInputStream(data, offset, length)
        super(DataInputBuffer, self).__init__(input_stream)

    def reset(self, data, offset=0, length=0):
        self._stream.reset(data, offset, length)

    def size(self):
        return self._stream.size()

    def toByteArray(self):
        return self._stream.toByteArray()


########NEW FILE########
__FILENAME__ = IntWritable
#!/usr/bin/env python
# ========================================================================
# Licensed to the Apache Software Foundation (ASF) under one
# or more contributor license agreements.  See the NOTICE file
# distributed with this work for additional information
# regarding copyright ownership.  The ASF licenses this file
# to you under the Apache License, Version 2.0 (the
# "License"); you may not use this file except in compliance
# with the License.  You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from Writable import AbstractValueWritable
from WritableUtils import readVInt, readVLong, writeVInt, writeVLong

class IntWritable(AbstractValueWritable):
    def write(self, data_output):
        data_output.writeInt(self._value)

    def readFields(self, data_input):
        self._value = data_input.readInt()

class LongWritable(AbstractValueWritable):
    def write(self, data_output):
        data_output.writeLong(self._value)

    def readFields(self, data_input):
        self._value = data_input.readLong()

class VIntWritable(AbstractValueWritable):
    def write(self, data_output):
        writeVInt(data_output, self._value)

    def readFields(self, data_input):
        self._value = readVInt(data_input)

class VLongWritable(AbstractValueWritable):
    def write(self, data_output):
        writeVLong(data_output, self._value)

    def readFields(self, data_input):
        self._value = readVLong(data_input)


########NEW FILE########
__FILENAME__ = MapFile
#!/usr/bin/env python
# ========================================================================
# Licensed to the Apache Software Foundation (ASF) under one
# or more contributor license agreements.  See the NOTICE file
# distributed with this work for additional information
# regarding copyright ownership.  The ASF licenses this file
# to you under the Apache License, Version 2.0 (the
# "License"); you may not use this file except in compliance
# with the License.  You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import os

from IntWritable import LongWritable
import SequenceFile

INDEX_FILE_NAME = 'index'
DATA_FILE_NAME = 'data'

class Writer(object):
    INDEX_INTERVAL = 128

    def __init__(self, dirname, key_class, value_class):
        os.mkdir(dirname)

        data_path = os.path.join(dirname, DATA_FILE_NAME)
        self._data = SequenceFile.createWriter(data_path, key_class, value_class)

        index_path = os.path.join(dirname, INDEX_FILE_NAME)
        self._index = SequenceFile.createBlockWriter(index_path, key_class, LongWritable)

        self._size = 0
        self._last_index_pos = -1
        self._last_index_nkeys = -4294967295

    def close(self):
        self._data.close()
        self._index.close()

    def append(self, key, value):
        self._checkKey(key)

        pos = self._data.getLength()
        if self._size >= self._last_index_nkeys + self.INDEX_INTERVAL and pos > self._last_index_pos:
            self._index.append(key, LongWritable(pos))
            self._last_index_pos = pos
            self._last_index_nkeys = self._size

        self._data.append(key, value)
        self._size += 1

    def _checkKey(self, key):
        pass

class Reader(object):
    INDEX_SKIP = 0

    def __init__(self, dirname):
        self._data = SequenceFile.Reader(os.path.join(dirname, DATA_FILE_NAME))
        self._index = SequenceFile.Reader(os.path.join(dirname, INDEX_FILE_NAME))
        self._first_position = self._data.getPosition()
        self._positions = []
        self._keys = []

    def close(self):
        self._data.close()
        self._index.close()

    def getIndexInterval(self):
        return self._index_interval

    def setIndexInterval(self, interval):
        self._index_interval = interval

    def reset(self):
        self._data.seek(self._first_position)

    def midKey(self):
        self._readIndex()
        count = len(self._keys)
        if count == 0:
            return None
        return self._keys[(count - 1) >> 1]

    def finalKey(self, key):
        original_position = self._data.getPosition()
        try:
            self._readIndex()
            count = len(self._keys)
            if count > 0:
                self._data.seek(self._positions[count - 1])
            else:
                self._reset()
            while self._data.nextKey(key):
                continue
        finally:
            self._data.seek(original_position)

    def seek(self, key):
        return self._seekInternal(key) == 0

    def next(self, key, value):
        return self._data.next(key, value)

    def get(self, key, value):
        if self.seek(key):
            self._data._getCurrentValue(value)
            return value
        return None

    def getClosest(self, key, value, before=False):
        c = self._seekInternal(key, before)
        if (not before and c > 0) or (before and c < 0):
            return None

        self._data._getCurrentValue(value)
        return self._next_key

    def _readIndex(self):
        if self._keys:
            return

        key_class = self._index.getKeyClass()

        skip = self.INDEX_SKIP
        position = LongWritable()
        last_position = None
        while True:
            key = key_class()
            if not self._index.next(key, position):
                break

            if skip > 0:
                skip -= 1
                continue

            skip = self.INDEX_SKIP
            if position.get() == last_position:
                continue

            self._positions.append(position.get())
            self._keys.append(key)

    def _seekInternal(self, key, before=None):
        self._readIndex()

        seek_index = self._indexSearch(key)
        if seek_index < 0:
            seek_index = -seek_index - 2

        if seek_index == -1:
            seek_position = self._first_position
        else:
            seek_position = self._positions[seek_index]

        prev_position = -1
        curr_position = seek_position

        key_class = self._data.getKeyClass()
        self._next_key = key_class()

        self._data.seek(seek_position)
        while self._data.nextKey(self._next_key):
            cmp = key.compareTo(self._next_key)
            if cmp <= 0:
                if before and cmp != 0:
                    if prev_position == -1:
                        self._data.seek(curr_position)
                    else:
                        self._data.seek(prev_position)
                        self._data.nextKey(self._next_key)
                        return 1
                return cmp

            if before:
                prev_position = curr_position
                curr_position = self._data.getPosition()

        return 1

    def _indexSearch(self, key):
        high = len(self._keys) - 1
        low = 0

        while low <= high:
            mid = (low + high) >> 1

            cmp = self._keys[mid].compareTo(key)
            if cmp < 0:
                low = mid + 1
            elif cmp > 0:
                high = mid - 1
            else:
                return mid
        return -(low + 1)


########NEW FILE########
__FILENAME__ = NullWritable
#!/usr/bin/env python
# ========================================================================
# Licensed to the Apache Software Foundation (ASF) under one
# or more contributor license agreements.  See the NOTICE file
# distributed with this work for additional information
# regarding copyright ownership.  The ASF licenses this file
# to you under the Apache License, Version 2.0 (the
# "License"); you may not use this file except in compliance
# with the License.  You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from Writable import WritableComparable

class NullWritable(WritableComparable):
    def __new__(cls, *p, **k):
        if not '_shared_instance' in cls.__dict__:
            cls._shared_instance = WritableComparable.__new__(cls)
        return cls._shared_instance

    def write(self, data_output):
        pass

    def readFields(self, data_input):
        pass

    def toString(self):
        return "(null)"

    def hashCode(self):
        return 0

    def equals(self, other):
        return isinstance(other, NullWritable)

    def compareTo(self, other):
        assert isinstance(other, NullWritable)
        assert self is other
        return self is other # True


########NEW FILE########
__FILENAME__ = OutputStream
#!/usr/bin/env python
# ========================================================================
# Licensed to the Apache Software Foundation (ASF) under one
# or more contributor license agreements.  See the NOTICE file
# distributed with this work for additional information
# regarding copyright ownership.  The ASF licenses this file
# to you under the Apache License, Version 2.0 (the
# "License"); you may not use this file except in compliance
# with the License.  You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import struct

class OutputStream(object):
    def close(self):
        raise NotImplementedError

    def flush(self):
        raise NotImplementedError

    def writeByte(self, byte):
        return self.writeFully(str(byte))

    def write(self, data):
        raise NotImplementedError

class FileOutputStream(OutputStream):
    def __init__(self, path):
        self._fd = open(path, 'wb')

    def close(self):
        self._fd.close()

    def seek(self, offset):
        self._fd.seek(offset)

    def flush(self):
        return self._fd.flush()

    def getPos(self):
        return self._fd.tell()

    def writeByte(self, value):
        return self._fd.write(value)

    def write(self, value):
        return self._fd.write(value)

class DataOutputStream(object):
    def __init__(self, output_stream):
        assert isinstance(output_stream, OutputStream)
        self._stream = output_stream

    def close(self):
        return self._stream.close()

    def seek(self, offset):
        return self._stream.seek(offset)

    def getPos(self):
        return self._stream.getPos()

    def write(self, length):
        return self._stream.write(length)

    def writeByte(self, value):
        data = struct.pack(">b", value)
        assert len(data) == 1
        return self._stream.write(data)

    def writeUByte(self, value):
        data = struct.pack("B", value)
        assert len(data) == 1
        return self._stream.write(data)

    def writeBoolean(self, value):
        data = struct.pack(">?", value)
        assert len(data) == 1
        return self._stream.write(data)

    def writeInt(self, value):
        data = struct.pack(">i", value)
        assert len(data) == 4
        return self._stream.write(data)

    def writeLong(self, value):
        data = struct.pack(">q", value)
        assert len(data) == 8
        return self._stream.write(data)

    def writeFloat(self, value):
        data = struct.pack(">f", value)
        assert len(data) == 4
        return self._stream.write(data)

    def writeDouble(self, value):
        data = struct.pack(">d", value)
        assert len(data) == 8
        return self._stream.write(data)

    def skipBytes(self, n):
        return self._stream.skip(n)

class ByteArrayOutputStream(OutputStream):
    def __init__(self):
        self._buffer = []
        self._count = 0

    def size(self):
        return self._count

    def toByteArray(self):
        return ''.join(self._buffer)

    def reset(self):
        self._buffer = []
        self._count = 0

    def close(self):
        pass

    def flush(self):
        pass

    def write(self, bytes):
        self._buffer.append(bytes)
        self._count += len(bytes)

class DataOutputBuffer(DataOutputStream):
    def __init__(self):
        super(DataOutputBuffer, self).__init__(ByteArrayOutputStream())

    def getData(self):
        return self._stream.toByteArray()

    def getSize(self):
        return self._stream.size()

    def reset(self):
        self._stream.reset()

    def writeStreamData(self, input_stream, length):
        self._stream.write(input_stream.read(length))

    def toByteArray(self):
        return self._stream.toByteArray()


########NEW FILE########
__FILENAME__ = SequenceFile
#!/usr/bin/env python
# ========================================================================
# Licensed to the Apache Software Foundation (ASF) under one
# or more contributor license agreements.  See the NOTICE file
# distributed with this work for additional information
# regarding copyright ownership.  The ASF licenses this file
# to you under the Apache License, Version 2.0 (the
# "License"); you may not use this file except in compliance
# with the License.  You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from hashlib import md5
from uuid import uuid1
from time import time
import os

from hadoop.util.ReflectionUtils import hadoopClassFromName, hadoopClassName

from compress import CodecPool

from WritableUtils import readVInt, writeVInt
from Writable import Writable
from OutputStream import FileOutputStream, DataOutputStream, DataOutputBuffer
from InputStream import FileInputStream, DataInputStream, DataInputBuffer
from VersionMismatchException import VersionMismatchException, VersionPrefixException

from Text import Text

BLOCK_COMPRESS_VERSION  = '\x04'
CUSTOM_COMPRESS_VERSION = '\x05'
VERSION_WITH_METADATA   = '\x06'
VERSION_PREFIX = 'SEQ'
VERSION = VERSION_PREFIX + VERSION_WITH_METADATA

SYNC_ESCAPE = -1
SYNC_HASH_SIZE = 16
SYNC_SIZE = 4 + SYNC_HASH_SIZE

SYNC_INTERVAL = 100 * SYNC_SIZE

class CompressionType:
    NONE = 0
    RECORD = 1
    BLOCK  = 2

class Metadata(Writable):
    def __init__(self, metadata=None):
        if metadata:
            self._meta = dict(metadata)
        else:
            self._meta = {}

    def get(self, name):
        return self._meta[name]

    def set(self, name, value):
        self._meta[name] = value

    def keys(self):
        return self._meta.keys()

    def iterkeys(self):
        return self._meta.iterkeys()

    def values(self):
        return self._meta.values()

    def itervalues(self):
        return self._meta.itervalues()

    def iteritems(self):
        return self._meta.iteritems()

    def __iter__(self):
        return self._meta.iteritems()

    def write(self, data_output):
        data_output.writeInt(len(self._meta))
        for key, value in self._meta.iteritems():
            Text.writeString(data_output, key)
            Text.writeString(data_output, value)

    def readFields(self, data_input):
        count = data_input.readInt()
        if count < 0:
            raise IOError("Invalid size: %d for file metadata object" % count)

        for i in xrange(count):
            key = Text.readString(data_input)
            value = Text.readString(data_input)
            self._meta[key] = value

def createWriter(path, key_class, value_class, metadata=None, compression_type=CompressionType.NONE):
    kwargs = {}

    if compression_type == CompressionType.NONE:
        pass
    elif compression_type == CompressionType.RECORD:
        kwargs['compress'] = True
    elif compression_type == CompressionType.BLOCK:
        kwargs['compress'] = True
        kwargs['block_compress'] = True
    else:
        raise NotImplementedError("Compression Type Not Supported")

    return Writer(path, key_class, value_class, metadata, **kwargs)

def createRecordWriter(path, key_class, value_class, metadata=None):
    return Writer(path, key_class, value_class, metadata, compress=True)

def createBlockWriter(path, key_class, value_class, metadata=None):
    return Writer(path, key_class, value_class, metadata, compress=True, block_compress=True)

class Writer(object):
    COMPRESSION_BLOCK_SIZE = 1000000

    def __init__(self, path, key_class, value_class, metadata, compress=False, block_compress=False):
        if os.path.exists(path):
            raise IOError("File %s already exists." % path)

        self._key_class = key_class
        self._value_class = value_class
        self._compress = compress
        self._block_compress = block_compress

        if not metadata:
            metadata = Metadata()
        self._metadata = metadata

        if self._compress or self._block_compress:
            self._codec = CodecPool().getCompressor()
        else:
            self._codec = None

        self._last_sync = 0
        self._block = None

        self._stream = DataOutputStream(FileOutputStream(path))

        # sync is 16 random bytes
        self._sync = md5('%s@%d' % (uuid1().bytes, int(time() * 1000))).digest()

        self._writeFileHeader()

    def close(self):
        if self._block_compress:
            self.sync()
        self._stream.close()

    def getCompressionCodec(self):
        return self._codec

    def getKeyClass(self):
        return self._key_class

    def getKeyClassName(self):
        return hadoopClassName(self._key_class)

    def getValueClass(self):
        return self._value_class

    def getValueClassName(self):
        return hadoopClassName(self._value_class)

    def isBlockCompressed(self):
        return self._block_compress

    def isCompressed(self):
        return self._compress

    def getLength(self):
        return self._stream.getPos()

    def append(self, key, value):
        if type(key) != self._key_class:
            raise IOError("Wrong key class %s is not %s" % (type(key), self._key_class))

        if type(value) != self._value_class:
            raise IOError("Wrong Value class %s is not %s" % (type(value), self._value_class))

        key_buffer = DataOutputBuffer()
        key.write(key_buffer)

        value_buffer = DataOutputBuffer()
        value.write(value_buffer)

        self.appendRaw(key_buffer.toByteArray(), value_buffer.toByteArray())

    def appendRaw(self, key, value):
        if self._block_compress:
            if self._block:
                records, keys_len, keys, values_len, values = self._block
            else:
                keys_len = DataOutputBuffer()
                keys = DataOutputBuffer()
                values_len = DataOutputBuffer()
                values = DataOutputBuffer()
                records = 0

            writeVInt(keys_len, len(key))
            keys.write(key)

            writeVInt(values_len, len(value))
            values.write(value)

            records += 1

            self._block = (records, keys_len, keys, values_len, values)

            current_block_size = keys.getSize() + values.getSize()
            if current_block_size >= self.COMPRESSION_BLOCK_SIZE:
                self.sync()
        else:
            if self._compress:
                value = self._codec.compress(value)

            key_length = len(key)
            value_length = len(value)

            self._checkAndWriteSync()
            self._stream.writeInt(key_length + value_length)
            self._stream.writeInt(key_length)
            self._stream.write(key)
            self._stream.write(value)

    def sync(self):
        if self._last_sync != self._stream.getPos():
            self._stream.writeInt(SYNC_ESCAPE)
            self._stream.write(self._sync)
            self._last_sync = self._stream.getPos()

        if self._block_compress and self._block:
            def _writeBuffer(data_buf):
                buf = self._codec.compress(data_buf.toByteArray())
                writeVInt(self._stream, len(buf))
                self._stream.write(buf)

            records, keys_len, keys, values_len, values = self._block

            writeVInt(self._stream, records)

            _writeBuffer(keys_len)
            _writeBuffer(keys)

            _writeBuffer(values_len)
            _writeBuffer(values)

            self._block = None

    def _writeFileHeader(self):
        self._stream.write(VERSION)
        Text.writeString(self._stream, self.getKeyClassName())
        Text.writeString(self._stream, self.getValueClassName())

        self._stream.writeBoolean(self._compress)
        self._stream.writeBoolean(self._block_compress)

        if self._codec:
            Text.writeString(self._stream, 'org.apache.hadoop.io.compress.DefaultCodec')

        self._metadata.write(self._stream)
        self._stream.write(self._sync)

    def _checkAndWriteSync(self):
        if self._stream.getPos() >= (self._last_sync + SYNC_INTERVAL):
            self.sync()

class Reader(object):
    def __init__(self, path, start=0, length=0):
        self._block_compressed = False
        self._decompress = False
        self._sync_seen = False

        self._value_class = None
        self._key_class = None
        self._codec = None

        self._metadata = None

        self._record = DataInputBuffer()
        self._initialize(path, start, length)

    def getStream(self, path):
        return DataInputStream(FileInputStream(path))

    def close(self):
        self._stream.close()

    def getCompressionCodec(self):
        return self._codec

    def getKeyClass(self):
        if not self._key_class:
          self._key_class = hadoopClassFromName(self._key_class_name)
        return self._key_class

    def getKeyClassName(self):
        return hadoopClassName(self.getKeyClass())

    def getValueClass(self):
        if not self._value_class:
          self._value_class = hadoopClassFromName(self._value_class_name)
        return self._value_class

    def getValueClassName(self):
        return hadoopClassName(self.getValueClass())

    def getPosition(self):
        return self._stream.getPos()

    def getMetadata(self):
        return self._metadata

    def isBlockCompressed(self):
        return self._block_compressed

    def isCompressed(self):
        return self._decompress

    def nextRawKey(self):
        if not self._block_compressed:
            record_length = self._readRecordLength()
            if record_length < 0:
                return None

            key_length = self._stream.readInt()
            key = DataInputBuffer(self._stream.read(key_length))
            self._record.reset(self._stream.read(record_length - key_length))
            return key
        else:
            if hasattr(self, '_block_index') and \
               self._block_index < self._record[0]:
                self._sync_seen = False
                records, keys_len, keys, values_len, values = self._record
                key_length = readVInt(keys_len)
                self._block_index += 1
                return DataInputBuffer(keys.read(key_length))

            if self._stream.getPos() >= self._end:
                return None

            # Read Sync
            self._stream.readInt() # -1
            sync_check = self._stream.read(SYNC_HASH_SIZE)
            if sync_check != self._sync:
                raise IOError("File is corrupt")
            self._sync_seen = True

            def _readBuffer():
                length = readVInt(self._stream)
                buf = self._stream.read(length)
                return self._codec.decompressInputStream(buf)

            records = readVInt(self._stream)
            keys_len = _readBuffer()
            keys = _readBuffer()

            values_len = _readBuffer()
            values = _readBuffer()

            self._record = (records, keys_len, keys, values_len, values)
            self._block_index = 1

            key_length = readVInt(keys_len)
            return DataInputBuffer(keys.read(key_length))

    def nextKey(self, key):
        buf = self.nextRawKey()
        if not buf:
          return False
        key.readFields(buf)
        return True

    def nextRawValue(self):
        if not self._block_compressed:
            if self._decompress:
                compress_data = self._record.read(self._record.size())
                return self._codec.decompressInputStream(compress_data)
            else:
                return self._record
        else:
            records, keys_len, keys, values_len, values = self._record
            value_length = readVInt(values_len)
            return DataInputBuffer(values.read(value_length))

    def next(self, key, value):
        more = self.nextKey(key)
        if more:
            self._getCurrentValue(value)
        return more

    def seek(self, position):
        self._stream.seek(position)
        if self._block_compressed:
            self._no_buffered_keys = 0
            self._values_decompressed = True

    def sync(self, position):
        if (position + SYNC_SIZE) > self._end:
            self.seek(self._end)
            return

        if position < self._header_end:
            self._stream.seek(self._header_end)
            self._sync_seen = True
            return

        self.seek(position + 4)
        sync_check = [x for x in self._stream.read(SYNC_HASH_SIZE)]

        i = 0
        while self._stream.getPos() < self._end:
            j = 0
            while j < SYNC_HASH_SIZE:
                if self._sync[j] != sync_check[(i + j) % SYNC_HASH_SIZE]:
                    break
                j += 1

            if j == SYNC_HASH_SIZE:
                self._stream.seek(self._stream.getPos() - SYNC_SIZE)
                return

            sync_check[i % SYNC_HASH_SIZE] = chr(self._stream.readByte())

            i += 1

    def syncSeen(self):
        return self._sync_seen

    def _initialize(self, path, start, length):
        self._stream = self.getStream(path)

        if length == 0:
            self._end = self._stream.getPos() + self._stream.length()
        else:
            self._end = self._stream.getPos() + length

        # Parse Header
        version_block = self._stream.read(len(VERSION))

        if not version_block.startswith(VERSION_PREFIX):
            raise VersionPrefixException(VERSION_PREFIX,
                                         version_block[0:len(VERSION_PREFIX)])

        self._version = version_block[len(VERSION_PREFIX)]
        if self._version > VERSION[len(VERSION_PREFIX)]:
            raise VersionMismatchException(VERSION[len(VERSION_PREFIX)],
                                           self._version)

        if self._version < BLOCK_COMPRESS_VERSION:
            # Same as below, but with UTF8 Deprecated Class
            raise NotImplementedError
        else:
            self._key_class_name = Text.readString(self._stream)
            self._value_class_name = Text.readString(self._stream)

        if ord(self._version) > 2:
            self._decompress = self._stream.readBoolean()
        else:
            self._decompress = False

        if self._version >= BLOCK_COMPRESS_VERSION:
            self._block_compressed = self._stream.readBoolean()
        else:
            self._block_compressed = False

        # setup compression codec
        if self._decompress:
            if self._version >= CUSTOM_COMPRESS_VERSION:
                codec_class = Text.readString(self._stream)
                self._codec = CodecPool().getDecompressor(codec_class)
            else:
                self._codec = CodecPool().getDecompressor()

        self._metadata = Metadata()
        if self._version >= VERSION_WITH_METADATA:
            self._metadata.readFields(self._stream)

        if self._version > 1:
            self._sync = self._stream.read(SYNC_HASH_SIZE)
            self._header_end = self._stream.getPos()

    def _readRecordLength(self):
        if self._stream.getPos() >= self._end:
            return -1

        length = self._stream.readInt()
        if self._version > 1 and self._sync is not None and length == SYNC_ESCAPE:
            sync_check = self._stream.read(SYNC_HASH_SIZE)
            if sync_check != self._sync:
                raise IOError("File is corrupt!")

            self._sync_seen = True
            if self._stream.getPos() >= self._end:
                return -1

            length = self._stream.readInt()
        else:
            self._sync_seen = False

        return length

    def _getCurrentValue(self, value):
        stream = self.nextRawValue()
        value.readFields(stream)
        if not self._block_compressed:
            assert self._record.size() == 0

########NEW FILE########
__FILENAME__ = SetFile
#!/usr/bin/env python
# ========================================================================
# Licensed to the Apache Software Foundation (ASF) under one
# or more contributor license agreements.  See the NOTICE file
# distributed with this work for additional information
# regarding copyright ownership.  The ASF licenses this file
# to you under the Apache License, Version 2.0 (the
# "License"); you may not use this file except in compliance
# with the License.  You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from NullWritable import NullWritable
import MapFile

class Writer(MapFile.Writer):
    def __init__(self, path, key_class):
        super(Writer, self).__init__(path, key_class, NullWritable)

    def append(self, key):
        return super(Writer, self).append(key, NullWritable())

class Reader(MapFile.Reader):
    def next(self, key):
        return super(Reader, self).next(key, NullWritable())

    def get(self, key):
        if self.seek(key):
            return self._next_key
        return None


########NEW FILE########
__FILENAME__ = Text
#!/usr/bin/env python
# ========================================================================
# Licensed to the Apache Software Foundation (ASF) under one
# or more contributor license agreements.  See the NOTICE file
# distributed with this work for additional information
# regarding copyright ownership.  The ASF licenses this file
# to you under the Apache License, Version 2.0 (the
# "License"); you may not use this file except in compliance
# with the License.  You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from Writable import WritableComparable
from WritableUtils import readVInt, writeVInt

class Text(WritableComparable):
    def __init__(self):
        self._bytes = ''
        self._length = 0

    def getBytes(self):
        return self._bytes

    def getLength(self):
        return self._length

    def set(self, value):
        self._bytes = Text.encode(value)
        self._length = len(self._bytes)

    def append(self, value):
        new_bytes = Text.encode(value)
        self._bytes += new_bytes
        self._length += len(new_bytes)

    def clear(self):
        self._length = 0
        self._bytes = ''

    def write(self, data_output):
        writeVInt(data_output, self._length)
        data_output.write(self._bytes)

    def readFields(self, data_input):
        self._length = readVInt(data_input)
        self._bytes = data_input.read(self._length)

    def equal(self, other):
        if not isinstance(other, Text):
            return False
        return self._bytes == other._bytes and self._length and other._length

    def toString(self):
        return self._bytes

    @staticmethod
    def readString(data_input):
        length = readVInt(data_input)
        bytes = data_input.read(length)
        return Text.decode(bytes)

    @staticmethod
    def writeString(data_output, bytes):
        bytes = Text.encode(bytes)
        writeVInt(data_output, len(bytes))
        data_output.write(bytes)

    @staticmethod
    def encode(bytes):
        return bytes.encode('utf-8')

    @staticmethod
    def decode(bytes):
        return bytes.decode('utf-8')


########NEW FILE########
__FILENAME__ = VersionMismatchException
#!/usr/bin/env python
# ========================================================================
# Licensed to the Apache Software Foundation (ASF) under one
# or more contributor license agreements.  See the NOTICE file
# distributed with this work for additional information
# regarding copyright ownership.  The ASF licenses this file
# to you under the Apache License, Version 2.0 (the
# "License"); you may not use this file except in compliance
# with the License.  You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
class VersionPrefixException(Exception):
    def __init__(self, expected, discovered):
        self.expected_prefix = expected
        self.discovered_prefix = discovered
    def __str__(self):
        return "Sequence file prefix found %r but expected %r" \
            % (self.discovered_prefix, self.expected_prefix)

class VersionMismatchException(Exception):
    def __init__(self, expected_version, founded_version):
        self.expected_version = expected_version
        self.founded_version = founded_version

    def toString(self):
        return "A record version mismatch occured. Expecting %r, found %r" \
            % (self.expected_version, self.founded_version)

    def __str__(self):
        self.toString()

########NEW FILE########
__FILENAME__ = Writable
#!/usr/bin/env python
# ========================================================================
# Licensed to the Apache Software Foundation (ASF) under one
# or more contributor license agreements.  See the NOTICE file
# distributed with this work for additional information
# regarding copyright ownership.  The ASF licenses this file
# to you under the Apache License, Version 2.0 (the
# "License"); you may not use this file except in compliance
# with the License.  You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

class Writable(object):
    def write(self, data_output):
        raise NotImplementedError

    def readFields(self, data_input):
        raise NotImplementedError

    def toString(self):
        return str(type(self))

    def __repr__(self):
        return self.toString()

class WritableComparable(Writable):
    def compareTo(self, other):
        raise NotImplementedError

class AbstractValueWritable(WritableComparable):
    def __init__(self, value=None):
        assert not isinstance(value, type(self)), (type(self._value))
        self._value = value

    def set(self, value):
        assert not isinstance(self._value, type(self)), (type(self._value))
        self._value = value

    def get(self):
        return self._value

    def equal(self, other):
        if not isinstance(other, type(self)):
            return False
        return self._value == other._value

    def compareTo(self, other):
        assert isinstance(other, type(self)), (type(self), type(other))
        a = self._value
        b = other._value
        if a < b:
            return -1
        if a > b:
            return 1
        return 0

    def hashCode(self):
        return int(self._value)

    def toString(self):
        assert not isinstance(self._value, type(self)), (type(self._value))
        return str(self._value)


########NEW FILE########
__FILENAME__ = WritableUtils
#!/usr/bin/env python
# ========================================================================
# Licensed to the Apache Software Foundation (ASF) under one
# or more contributor license agreements.  See the NOTICE file
# distributed with this work for additional information
# regarding copyright ownership.  The ASF licenses this file
# to you under the Apache License, Version 2.0 (the
# "License"); you may not use this file except in compliance
# with the License.  You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

def readVInt(data_input):
    return readVLong(data_input)

def readVLong(data_input):
    first_byte = data_input.readByte()
    length = decodeVIntSize(first_byte)
    if length == 1:
        return first_byte

    i = 0
    for idx in xrange(length - 1):
        b = data_input.readUByte()
        i = i << 8
        i = i | b

    return (i ^ -1) if isNegativeVInt(first_byte) else i

def writeVInt(data_output, value):
    return writeVLong(data_output, value)

def writeVLong(data_output, value):
    if value >= -112 and value <= 127:
        data_output.writeByte(value)
        return

    length = -112
    if value < 0:
        value ^= -1
        length -= 120

    temp = value
    while temp != 0:
        temp = temp >> 8
        length -= 1

    data_output.writeByte(length)
    length = -(length + 120) if (length < -120) else -(length + 112)
    for idx in reversed(range(length)):
        shiftbits = idx << 3
        mask = 0xFF << shiftbits

        x = (value & mask) >> shiftbits
        data_output.writeUByte(x)

def isNegativeVInt(value):
    return value < -120 or (value >= -112 and value < 0)

def decodeVIntSize(value):
    if value >= -112:
        return 1
    elif value < -120:
        return -119 - value
    return -111 - value

########NEW FILE########
__FILENAME__ = reader
"""pure-python implementation of pydoop-capable and sequencefile-capable
record reader.

Inclue pydoop as a dependency for this package by instructing pip or
setuptools that the `[pydoop]` extra is required:

    pip install Hadoop[pydoop]

Depends on recent implementations of pydoop, which support
custom python recordreaders.

TODO: profile this, and the rest of hadoop.io! cython speedups,
perhaps?

"""
import logging
logger = logging.getLogger(__name__)
try:
    import pydoop.pipes as pp
    from pydoop import hdfs
except ImportError as e:
    raise Exception("cannot load pydoop " +
                    "(not installed as Hadoop[pydoop]?): %s" % e)
from hadoop.io import SequenceFile, InputStream


class HdfsFileInputStream(InputStream.FileInputStream):
    """meets hadoop interface, at least all the bits that
    FileInputStream implements"""
    def __init__(self, path):
        logger.debug("FileInputStream path: %s", path)
        self._fd = hdfs.open(path, 'r') # todo: get user
        self._length = self._fd.size


class _HdfsSequenceFileReader(SequenceFile.Reader):
    def getStream(self, path):
        logger.debug("_HdfsSequenceFileReader path: %s", path)
        return InputStream.DataInputStream(HdfsFileInputStream(path))


class SequenceFileReader(pp.RecordReader):
    """custom python record reader that reads Java-style sequence
    files from HDFS. Caveat is that objects in the sequence file must
    be declared and in scope with the same namespace as Java.

    The Hadoop package (on which this depends) provides classes for
    the types org.apache.hadoop.io.Text etc, but other classes
    (e.g. com.intelius.avroidm.IDMArray) must be provided, and must
    meet the interfaces expected by the Hadoop package (see the Text
    implementation there)."""
    def __init__(self, context):
        super(SequenceFileReader, self).__init__()
        self.isplit = pp.InputSplit(context.getInputSplit())
        logger.debug("isplit filename: %s", self.isplit.filename)
        logger.debug("isplit offset: %s", self.isplit.offset)
        logger.debug("isplit length: %s", self.isplit.length)
        self.seq_file = _HdfsSequenceFileReader(path = self.isplit.filename,
                                                start = self.isplit.offset,
                                                length = self.isplit.length)

        key_class = self.seq_file.getKeyClass()
        value_class = self.seq_file.getValueClass()
        self._key = key_class()
        self._value = value_class()
        logger.debug("done initializing pydoop.reader.SequenceFileReader")

    def close(self):
        self.seq_file.close()

    def next(self):
        if (self.seq_file.next(self._key, self._value)):
            return (True, self._key.toString(), self._value.toString())
        else:
            return (False, "", "")

    def getProgress(self):
        result = float(self.seq_file.getPosition())/self.isplit.length
        return min(result, 1.0)

########NEW FILE########
__FILENAME__ = ReflectionUtils
#!/usr/bin/env python
# ========================================================================
# Licensed to the Apache Software Foundation (ASF) under one
# or more contributor license agreements.  See the NOTICE file
# distributed with this work for additional information
# regarding copyright ownership.  The ASF licenses this file
# to you under the Apache License, Version 2.0 (the
# "License"); you may not use this file except in compliance
# with the License.  You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from hadoop.io import *

def hadoopClassFromName(class_path):
    if class_path.startswith('org.apache.hadoop.'):
        class_path = class_path[11:]
    return classFromName(class_path)

def hadoopClassName(class_type):
    if hasattr(class_type, "hadoop_module_name") and \
       hasattr(class_type, "hadoop_class_name"):
        module_name = class_type.hadoop_module_name
        class_name = class_type.hadoop_class_name
    else:
        module_name = class_type.__module__
        class_name = class_type.__name__
    if module_name.startswith('hadoop.io.'):
        module_name, _, file_name = module_name.rpartition('.')
        return 'org.apache.%s.%s' % (module_name, class_name)
    return '%s.%s' % (module_name, class_name)

def classFromName(class_path):
    module_name, _, class_name = class_path.rpartition('.')
    if not module_name:
        raise ValueError('Class name must contain module part.')

    module = __import__(module_name, globals(), locals(), [str(class_name)], -1)
    return getattr(module, class_name)


########NEW FILE########
