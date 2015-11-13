__FILENAME__ = benchmark
#!/usr/bin/env python

# Copyright 2011 The fast-python-pb Authors.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Compare JSON and protocol buffer serialization times."""

from timeit import Timer

import person_proto
import person_pb2
import json
import simplejson
import cPickle

try:
  import lwpb.codec
except ImportError:
  lwpb = None


GETTYSBURG = """
Four score and seven years ago our fathers brought forth on this continent, a new nation, conceived in
Liberty, and dedicated to the proposition that all men are created equal.

Now we are engaged in a great civil war, testing whether that nation, or any nation so conceived
and so dedicated, can long endure. We are met on a great battle-field of that war. We have come to dedicate
a portion of that field, as a final resting place for those who here gave their lives that that nation might
live. It is altogether fitting and proper that we should do this.

But, in a larger sense, we can not dedicate -- we can not consecrate -- we can not hallow -- this ground.
The brave men, living and dead, who struggled here, have consecrated it, far above our poor power to add or
detract. The world will little note, nor long remember what we say here, but it can never forget what they did
here. It is for us the living, rather, to be dedicated here to the unfinished work which they who fought here
have thus far so nobly advanced. It is rather for us to be here dedicated to the great task remaining before
us -- that from these honored dead we take increased devotion to that cause for which they gave the last full
measure of devotion -- that we here highly resolve that these dead shall not have died in vain -- that this
nation, under God, shall have a new birth of freedom -- and that government of the people, by the people, for
the people, shall not perish from the earth.
"""


def useJson():
  """Test serialization using JSON."""
  lincoln = {
    'name': 'Abraham Lincoln',
    'birth_year': 1809,
    'nicknames': ['Honest Abe', 'Abe'],
    'facts': {
      'Born In': 'Kentucky',
      'Died In': 'Washington D.C.',
      'Greatest Speech': GETTYSBURG
    }
  }

  serialized = json.dumps(lincoln)

  json.loads(serialized)


def useSimpleJson():
  """Test serialization using SimpleJSON."""
  lincoln = {
    'name': 'Abraham Lincoln',
    'birth_year': 1809,
    'nicknames': ['Honest Abe', 'Abe'],
    'facts': {
      'Born In': 'Kentucky',
      'Died In': 'Washington D.C.',
      'Greatest Speech': GETTYSBURG
    }
  }

  serialized = simplejson.dumps(lincoln)
  simplejson.loads(serialized)


def usePb():
  """Test protocol buffer serialization."""
  lincoln = person_proto.Person(name = 'Abraham Lincoln', birth_year = 1809)
  lincoln.nicknames = ['Honest Abe', 'Abe']
  lincoln.facts = [
      person_proto.Fact(name = 'Born In', content = 'Kentucky'),
      person_proto.Fact(name = 'Died In', content = 'Washington D.C.'),
      person_proto.Fact(name = 'Greatest Speech', content = GETTYSBURG)
  ]

  serializedLincoln = lincoln.SerializeToString()

  newLincoln = person_proto.Person()
  newLincoln.ParseFromString(serializedLincoln)


def useStandardPb():
  """Test protocol buffer serialization with native protocol buffers."""
  lincoln = person_pb2.Person(name = 'Abraham Lincoln', birth_year = 1809)
  lincoln.nicknames.extend(['Honest Abe', 'Abe'])

  fact = lincoln.facts.add()
  fact.name = 'Born In'
  fact.content = 'Kentucky'

  fact = lincoln.facts.add()
  fact.name = 'Died In'
  fact.content = 'Washington D.C.'

  fact = lincoln.facts.add()
  fact.name = 'Greatest Speech'
  fact.content = GETTYSBURG

  serializedLincoln = lincoln.SerializeToString()

  newLincoln = person_pb2.Person()
  newLincoln.ParseFromString(serializedLincoln)


def useLWPB(codec):
  """Test protocol buffer serialization with lwpb."""
  lincoln = {
    'name' : 'Abraham Lincoln',
    'birth_year' : 1809,
    'nicknames' : ['Honest Abe', 'Abe'],
    'facts' : [
      { 'name' : 'Born In', 'content' : 'Kentucky' },
      { 'name' : 'Died In', 'content' : 'Washington D.C.' },
      { 'name' : 'Greatest Speech', 'content' : GETTYSBURG },
    ]
  }

  serialized = codec.encode( lincoln )
  newlincoln = codec.decode( serialized )


def useCPickle():
  """Test protocol buffer serialization with cPickle."""
  lincoln = {
    'name' : 'Abraham Lincoln',
    'birth_year' : 1809,
    'nicknames' : ['Honest Abe', 'Abe'],
    'facts' : [
      { 'name' : 'Born In', 'content' : 'Kentucky' },
      { 'name' : 'Died In', 'content' : 'Washington D.C.' },
      { 'name' : 'Greatest Speech', 'content' : GETTYSBURG },
    ]
  }

  serialized = cPickle.dumps( lincoln )
  newlincoln = cPickle.loads( serialized )


def main():
  """Runs the PB vs JSON benchmark."""
  print "JSON"
  timer = Timer("useJson()", "from __main__ import useJson")
  print timer.timeit(10000)

  """Runs the PB vs SimpleJSON benchmark."""
  print "SimpleJSON"
  timer = Timer("useSimpleJson()", "from __main__ import useSimpleJson")
  print timer.timeit(10000)

  print "Protocol Buffer (fast)"
  timer = Timer("usePb()", "from __main__ import usePb")
  print timer.timeit(10000)

  print "Protocol Buffer (standard)"
  timer = Timer("useStandardPb()", "from __main__ import useStandardPb")
  print timer.timeit(10000)

  if lwpb:
    print "Protocol Buffer (lwpb)"
    timer = Timer("useLWPB(lwpb_codec)", "from __main__ import useLWPB, lwpb_codec")
    print timer.timeit(10000)

  print "cPickle"
  timer = Timer("useCPickle()", "from __main__ import useCPickle")
  print timer.timeit(10000)


if __name__ == '__main__':
  main()

########NEW FILE########
__FILENAME__ = generator
#!/usr/bin/env python
# Copyright 2011 The fast-python-pb Authors.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.


"""Generates a Python wrapper for a C++ protocol buffer."""

import plugin_pb2

from google.protobuf import descriptor_pb2
from fastpb.util import order_dependencies
from jinja2 import Template

# pylint: disable=E0611
from pkg_resources import resource_string

import os.path
import sys


TYPE = {
  'STRING': descriptor_pb2.FieldDescriptorProto.TYPE_STRING,
  'DOUBLE': descriptor_pb2.FieldDescriptorProto.TYPE_DOUBLE,
  'FLOAT': descriptor_pb2.FieldDescriptorProto.TYPE_FLOAT,
  'INT32': descriptor_pb2.FieldDescriptorProto.TYPE_INT32,
  'SINT32': descriptor_pb2.FieldDescriptorProto.TYPE_SINT32,
  'UINT32': descriptor_pb2.FieldDescriptorProto.TYPE_UINT32,
  'INT64': descriptor_pb2.FieldDescriptorProto.TYPE_INT64,
  'SINT64': descriptor_pb2.FieldDescriptorProto.TYPE_SINT64,
  'UINT64': descriptor_pb2.FieldDescriptorProto.TYPE_UINT64,
  'MESSAGE': descriptor_pb2.FieldDescriptorProto.TYPE_MESSAGE,
  'BYTES': descriptor_pb2.FieldDescriptorProto.TYPE_BYTES,
  'BOOL': descriptor_pb2.FieldDescriptorProto.TYPE_BOOL,
  'ENUM': descriptor_pb2.FieldDescriptorProto.TYPE_ENUM,
  # TODO(robbyw): More types.
}

LABEL = {
  'REPEATED': descriptor_pb2.FieldDescriptorProto.LABEL_REPEATED
}


def template(name):
  """Gets a template of the given name."""
  return Template(resource_string(__name__, 'template/' + name))


def sort_messages(fileObject):
  """Return a sorted list of messages (sub-messages first).

  This avoids compilation problems involving declaration order.
  """
  dependencies = []
  msgDict = {}

  def visit(baseName, messages, parent=None):
    """Visitor for the message tree."""
    for msg in messages:
      # Build our type name (using the protocol buffer convention) and
      # use it to register this message type object in our dictionary.
      typeName = baseName + '.' + msg.name
      msgDict[typeName] = msg

      # If this is a nested message type, prepend our parent's name to
      # our name for all future name lookups (via template expansion).
      # This disambiguates nested message names so that two n-level
      # messages can both have nested message types with the same name.
      # This also matches the generated C++ code's naming convention.
      if parent is not None:
        msg.name = parent.name + '_' + msg.name

      # If this message has nested message types, recurse.
      if msg.nested_type:
        visit(typeName, msg.nested_type, parent=msg)

      # Generate the set of messages that this type is dependent upon.
      deps = set([field.type_name for field in msg.field
                  if field.type == TYPE['MESSAGE']])
      dependencies.append((typeName, deps))

  # Start by visiting the file's top-level message types.
  visit('.' + fileObject.package, fileObject.message_type)

  sortedMsgNames = order_dependencies(dependencies)
  return [msgDict[n] for n in sortedMsgNames]


def writeCFile(response, name, fileObject):
  """Writes a C file."""
  messages = sort_messages(fileObject)
  context = {
    'fileName': name,
    'moduleName': fileObject.package.lstrip('.'),
    'package': fileObject.package.replace('.', '::'),
    'packageName': fileObject.package.split('.')[-1],
    'messages': messages,
    'enums': fileObject.enum_type,
    'TYPE': TYPE,
    'LABEL': LABEL
  }

  cFile = response.file.add()
  cFile.name = name + '.cc'
  cFile.content = template('module.jinjacc').render(context)


def writeSetupPy(response, files, parents):
  """Writes the setup.py file."""
  setupFile = response.file.add()
  setupFile.name = 'setup.py'
  setupFile.content = template('setup.jinjapy').render({
    'files': files,
    'parents': parents
  })


def writeTests(response, files):
  """Writes the tests."""
  setupFile = response.file.add()
  setupFile.name = 'test.py'
  setupFile.content = template('test.jinjapy').render({
    'files': files,
    'TYPE': TYPE,
    'LABEL': LABEL
  })


def writeManifest(response, files):
  """Writes the manifest."""
  setupFile = response.file.add()
  setupFile.name = 'MANIFEST.in'
  setupFile.content = template('MANIFEST.jinjain').render({
    'files': files
  })


def main():
  """Main generation method."""
  request = plugin_pb2.CodeGeneratorRequest()
  request.ParseFromString(sys.stdin.read())

  response = plugin_pb2.CodeGeneratorResponse()

  parents = set()

  generateFiles = set(request.file_to_generate)
  files = []
  for fileObject in request.proto_file:
    if fileObject.name not in generateFiles:
      continue
    if not fileObject.package:
      sys.stderr.write('%s: package definition required, but not found\n' % fileObject.name)
      sys.exit(1)

    name = fileObject.name.split('.')[0]
    files.append({
      'name': name,
      'package': fileObject.package.lstrip('.'),
      'messages': fileObject.message_type
    })

    path = fileObject.package.lstrip('.').split('.')[:-1]
    for i in range(len(path)):
      filePathParts = path[:i+1]
      package = '.'.join(filePathParts)
      filePath = os.path.join(*filePathParts)
      if package not in parents:
        initPy = response.file.add()
        initPy.name = os.path.join('src', filePath, '__init__.py')
        initPy.content = """
import pkg_resources
pkg_resources.declare_namespace('%s')
""" % package
        parents.add(package)

    # Write the C file.
    writeCFile(response, name, fileObject)

  writeSetupPy(response, files, parents)
  writeTests(response, files)
  writeManifest(response, files)

  sys.stdout.write(response.SerializeToString())


if __name__ == '__main__':
  main()

########NEW FILE########
__FILENAME__ = plugin_pb2
# Generated by the protocol buffer compiler.  DO NOT EDIT!

from google.protobuf import descriptor
from google.protobuf import message
from google.protobuf import reflection
from google.protobuf import descriptor_pb2
# @@protoc_insertion_point(imports)


DESCRIPTOR = descriptor.FileDescriptor(
  name='google/protobuf/compiler/plugin.proto',
  package='google.protobuf.compiler',
  serialized_pb='\n%google/protobuf/compiler/plugin.proto\x12\x18google.protobuf.compiler\x1a google/protobuf/descriptor.proto\"}\n\x14\x43odeGeneratorRequest\x12\x18\n\x10\x66ile_to_generate\x18\x01 \x03(\t\x12\x11\n\tparameter\x18\x02 \x01(\t\x12\x38\n\nproto_file\x18\x0f \x03(\x0b\x32$.google.protobuf.FileDescriptorProto\"\xaa\x01\n\x15\x43odeGeneratorResponse\x12\r\n\x05\x65rror\x18\x01 \x01(\t\x12\x42\n\x04\x66ile\x18\x0f \x03(\x0b\x32\x34.google.protobuf.compiler.CodeGeneratorResponse.File\x1a>\n\x04\x46ile\x12\x0c\n\x04name\x18\x01 \x01(\t\x12\x17\n\x0finsertion_point\x18\x02 \x01(\t\x12\x0f\n\x07\x63ontent\x18\x0f \x01(\t')




_CODEGENERATORREQUEST = descriptor.Descriptor(
  name='CodeGeneratorRequest',
  full_name='google.protobuf.compiler.CodeGeneratorRequest',
  filename=None,
  file=DESCRIPTOR,
  containing_type=None,
  fields=[
    descriptor.FieldDescriptor(
      name='file_to_generate', full_name='google.protobuf.compiler.CodeGeneratorRequest.file_to_generate', index=0,
      number=1, type=9, cpp_type=9, label=3,
      has_default_value=False, default_value=[],
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    descriptor.FieldDescriptor(
      name='parameter', full_name='google.protobuf.compiler.CodeGeneratorRequest.parameter', index=1,
      number=2, type=9, cpp_type=9, label=1,
      has_default_value=False, default_value=unicode("", "utf-8"),
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    descriptor.FieldDescriptor(
      name='proto_file', full_name='google.protobuf.compiler.CodeGeneratorRequest.proto_file', index=2,
      number=15, type=11, cpp_type=10, label=3,
      has_default_value=False, default_value=[],
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
  ],
  extensions=[
  ],
  nested_types=[],
  enum_types=[
  ],
  options=None,
  is_extendable=False,
  extension_ranges=[],
  serialized_start=101,
  serialized_end=226,
)


_CODEGENERATORRESPONSE_FILE = descriptor.Descriptor(
  name='File',
  full_name='google.protobuf.compiler.CodeGeneratorResponse.File',
  filename=None,
  file=DESCRIPTOR,
  containing_type=None,
  fields=[
    descriptor.FieldDescriptor(
      name='name', full_name='google.protobuf.compiler.CodeGeneratorResponse.File.name', index=0,
      number=1, type=9, cpp_type=9, label=1,
      has_default_value=False, default_value=unicode("", "utf-8"),
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    descriptor.FieldDescriptor(
      name='insertion_point', full_name='google.protobuf.compiler.CodeGeneratorResponse.File.insertion_point', index=1,
      number=2, type=9, cpp_type=9, label=1,
      has_default_value=False, default_value=unicode("", "utf-8"),
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    descriptor.FieldDescriptor(
      name='content', full_name='google.protobuf.compiler.CodeGeneratorResponse.File.content', index=2,
      number=15, type=9, cpp_type=9, label=1,
      has_default_value=False, default_value=unicode("", "utf-8"),
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
  ],
  extensions=[
  ],
  nested_types=[],
  enum_types=[
  ],
  options=None,
  is_extendable=False,
  extension_ranges=[],
  serialized_start=337,
  serialized_end=399,
)

_CODEGENERATORRESPONSE = descriptor.Descriptor(
  name='CodeGeneratorResponse',
  full_name='google.protobuf.compiler.CodeGeneratorResponse',
  filename=None,
  file=DESCRIPTOR,
  containing_type=None,
  fields=[
    descriptor.FieldDescriptor(
      name='error', full_name='google.protobuf.compiler.CodeGeneratorResponse.error', index=0,
      number=1, type=9, cpp_type=9, label=1,
      has_default_value=False, default_value=unicode("", "utf-8"),
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    descriptor.FieldDescriptor(
      name='file', full_name='google.protobuf.compiler.CodeGeneratorResponse.file', index=1,
      number=15, type=11, cpp_type=10, label=3,
      has_default_value=False, default_value=[],
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
  ],
  extensions=[
  ],
  nested_types=[_CODEGENERATORRESPONSE_FILE, ],
  enum_types=[
  ],
  options=None,
  is_extendable=False,
  extension_ranges=[],
  serialized_start=229,
  serialized_end=399,
)

import google.protobuf.descriptor_pb2

_CODEGENERATORREQUEST.fields_by_name['proto_file'].message_type = google.protobuf.descriptor_pb2._FILEDESCRIPTORPROTO
_CODEGENERATORRESPONSE_FILE.containing_type = _CODEGENERATORRESPONSE;
_CODEGENERATORRESPONSE.fields_by_name['file'].message_type = _CODEGENERATORRESPONSE_FILE

class CodeGeneratorRequest(message.Message):
  __metaclass__ = reflection.GeneratedProtocolMessageType
  DESCRIPTOR = _CODEGENERATORREQUEST
  
  # @@protoc_insertion_point(class_scope:google.protobuf.compiler.CodeGeneratorRequest)

class CodeGeneratorResponse(message.Message):
  __metaclass__ = reflection.GeneratedProtocolMessageType
  
  class File(message.Message):
    __metaclass__ = reflection.GeneratedProtocolMessageType
    DESCRIPTOR = _CODEGENERATORRESPONSE_FILE
    
    # @@protoc_insertion_point(class_scope:google.protobuf.compiler.CodeGeneratorResponse.File)
  DESCRIPTOR = _CODEGENERATORRESPONSE
  
  # @@protoc_insertion_point(class_scope:google.protobuf.compiler.CodeGeneratorResponse)

# @@protoc_insertion_point(module_scope)

########NEW FILE########
__FILENAME__ = util
# Copyright 2011 The fast-python-pb Authors.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from functools import reduce

try:
    from collections import OrderedDict
except ImportError:
    # just ignore the order with Python <2.7 for now
    OrderedDict = dict

class CyclicError(Exception):
    pass

def order_dependencies(dependencies):
    """Produce a topologically-sorted list of the given dependencies.

    >>> list(order_dependencies([
    ...     ('a', set(['b', 'c'])),
    ...     ('b', set(['c'])),
    ...     ('c', set()),
    ... ]))
    ['c', 'b', 'a']

    Flat dependencies simply yield the original order.

    >>> list(order_dependencies([
    ...     ('a', set()),
    ...     ('b', set()),
    ...     ('c', set()),
    ... ]))
    ['a', 'b', 'c']

    Nested and diamond dependencies are also supported.

    >>> list(order_dependencies([
    ...     ('a', set()),
    ...     ('b', set(['c', 'd'])),
    ...     ('c', set()),
    ... ]))
    ['a', 'c', 'd', 'b']
    >>> list(order_dependencies([
    ...     ('a', set(['b', 'c'])),
    ...     ('b', set(['d'])),
    ...     ('c', set(['d'])),
    ...     ('d', set()),
    ... ]))
    ['d', 'b', 'c', 'a']

    An empty dependency list results in an empty generator sequence.

    >>> list(order_dependencies([]))
    []

    Cyclic dependencies result in a CyclicError.

    >>> list(order_dependencies([
    ...     ('a', set(['b'])),
    ...     ('b', set(['c'])),
    ...     ('c', set(['a'])),
    ... ]))
    Traceback (most recent call last):
        ...
    CyclicError: A cyclic dependency exists amongst {'a': set(['b']), 'c': set(['a']), 'b': set(['c'])}

    Based on toposort2() by Paddy McCarthy.
    (see http://code.activestate.com/recipes/577413-topological-sort/)
    """
    data = OrderedDict(dependencies)

    # Ignore self dependencies.
    for k, v in data.items():
        v.discard(k)

    # If we're out of data, return (and produce an empty generator sequence).
    if not data:
        return

    # Add top-level keys for any unrepresented values.
    for item in reduce(set.union, data.values()) - set(data.keys()):
        data[item] = set()

    while True:
        ordered = set(item for item, dep in data.items() if not dep)
        if not ordered:
            break
        for dep in sorted(ordered):
            yield dep

        remaining = {}
        for item, dep in data.iteritems():
            if item not in ordered:
                remaining[item] = (dep - ordered)
        data = remaining

    if data:
        raise CyclicError('A cyclic dependency exists amongst %r' % dict(data))

if __name__ == "__main__":
    import doctest
    doctest.testmod()

########NEW FILE########
