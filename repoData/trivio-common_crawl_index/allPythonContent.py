__FILENAME__ = adaptor
# Copyright [2012] [Triv.io, Scott Robertson]
# 
#   Licensed under the Apache License, Version 2.0 (the "License");
#   you may not use this file except in compliance with the License.
#   You may obtain a copy of the License at
# 
#       http://www.apache.org/licenses/LICENSE-2.0
# 
#   Unless required by applicable law or agreed to in writing, software
#   distributed under the License is distributed on an "AS IS" BASIS,
#   WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#   See the License for the specific language governing permissions and
#   limitations under the License.
# 

import re
import struct


from triv.io import datasources
from .pbtree import PBTreeDictWriter, DataWriter, IndexWriter, DataBlockReader

BLOCK_SIZE   = 2**16
VALUE_FORMAT = "<QQIQ"
VALUE_SIZE   = struct.calcsize(VALUE_FORMAT)

ITEM_KEYS=(
  'arcSourceSegmentId',
  'arcFileDate',
  'arcFileParition',
  'arcFileOffset'
)


@datasources.write_mimetype('application/vnd.commoncrawl.org.url_index')
def output_stream(stream):
  return PBTreeDictWriter(stream, 
    value_format=VALUE_FORMAT,
    block_size =BLOCK_SIZE,
    item_keys=ITEM_KEYS
  )
  
  
@datasources.write_mimetype('application/vnd.commoncrawl.org.data_segment')
def output_stream(stream):
  class DictPacker(object):
    def __init__(self, item_keys, value_format):
      self.item_keys = item_keys
      self.value_format = value_format
      self.block_count = 0

    def pack_value(self, dict):
      value = [dict[k] for k in self.item_keys]      
      return struct.pack(self.value_format, *value)
    
    def on_new_block(self, key):
      self.block_count += 1
        
    def on_item_exceeds_block_size(self, key,value):
      print ""
  
  return DataWriter(stream, BLOCK_SIZE, '\0', DictPacker(ITEM_KEYS, VALUE_FORMAT))
  
@datasources.write_mimetype('application/vnd.commoncrawl.org.index_segment')
def output_stream(stream):
  return IndexWriter(stream, block_size=BLOCK_SIZE, terminator='\0')



@datasources.read_mimetype('application/vnd.commoncrawl.org.data_segment')
def data_block_reader(fd, size, url, params):
  part_number = "%04d" % int(re.search(':reduce:(\d+)\-',url).group(1))

  # read each block in the part, yielding the first key and part number
  
  params.last_key = None
  
  while True:
    block_buffer = fd.read(BLOCK_SIZE)
    if block_buffer == '':
      break
    block = iter(DataBlockReader(block_buffer, VALUE_SIZE))
    yield part_number, block
  
########NEW FILE########
__FILENAME__ = pbtree
# Copyright [2012] triv.io, Scott Robertson
# 
#   Licensed under the Apache License, Version 2.0 (the "License");
#   you may not use this file except in compliance with the License.
#   You may obtain a copy of the License at
# 
#       http://www.apache.org/licenses/LICENSE-2.0
# 
#   Unless required by applicable law or agreed to in writing, software
#   distributed under the License is distributed on an "AS IS" BASIS,
#   WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#   See the License for the specific language governing permissions and
#   limitations under the License.
# 

import bisect
import os
import mmap
import struct
import sys
from tempfile import TemporaryFile, SpooledTemporaryFile
from cStringIO import StringIO
import itertools

from .prefix import signifigant

MB = 1024**2
DISK_BLOCK_SIZE=1024 * 4

OFFSET_FMT = '<I'
OFFSET_SIZE = struct.calcsize(OFFSET_FMT)



class PBTreeWriter(object):
  """
  Constructs a disk based prefixed btreefor a sacalr value.
  """
    
  def __init__(self, stream, block_size=MB, terminator='\0', value_format="<Q"):
    self.stream = stream
    
    assert len(terminator) == 1, "terminator must be of legth 1"
    
    self.value_format = value_format
    self.value_size = struct.calcsize(self.value_format)
      
    self.block_size = block_size

    self.last_key = ''
    
    self.data_segment  = DataWriter(TemporaryFile(), block_size, terminator, self)
    self.index_segment = IndexWriter(stream, block_size, terminator)

  
  def pack_value(self, value):
    return struct.pack(self.value_format, value)


  def add(self, key, value):
    self.data_segment.add(key,value)
    self.last_key = key
    

  def on_new_block(self, key):
    prefix_key = signifigant(self.last_key, key)
    self.index_segment.add(0, prefix_key)


  def on_item_exceeds_block_size(self,key,value):
    raise ValueError("key '%s'  exceeds block size" % key)


  def commit(self):
    out = self.stream
    
    self.index_segment.finish()    
    self.data_segment.finish()
    
    while True:
      bytes = self.data_segment.read(DISK_BLOCK_SIZE)
      if bytes == '':
        break
      else:
        out.write(bytes)

    
  def close(self):
    self.commit()
    self.stream.close()
  
class PBTreeSequenceWriter(PBTreeWriter):
  """
  Writes a sequence to a pbtree, it assumes that an appropriate value_format
  is specified and that every sequence passed to add() is the same length.
  
  """

  def  pack_value(self, value):
    # this assumes an appropriate value_format was specified
    return struct.pack(self.value_format, *value)
  
class PBTreeDictWriter(PBTreeWriter):
  """
  Writes a dictionary to a pbtree 
  """
  
  def __init__(self, stream, item_keys, **options):
    self.item_keys = item_keys
    super(PBTreeDictWriter, self).__init__(stream, **options)

  def pack_value(self, dict):
    value = [dict[k] for k in self.item_keys]      
    return struct.pack(self.value_format, *value)



class PBTreeReader(object):
  """
  Reads a prefixed btree
  """
  
  @classmethod
  def parse(cls, stream, block_size):
    while True:
      block = stream.read(block_size)
      if block == '':
        break
      for offset, key in IndexBlockReader(block):
        yield offset, key
    
  def __init__(self, mmap, terminator='\0', value_format="<Q"):
    self.mmap = mmap
    #self.mmap.seek(0)
    self.terminator = terminator
    self.value_format = value_format
    self.value_size = struct.calcsize(self.value_format)
    

    self.header_fmt = "<II"
    self.header_size = struct.calcsize(self.header_fmt)
    
    self.block_size, self.index_block_size = self.fetch_header()
  
  
  def fetch(self, start, end):
    return self.mmap[start:end]
    
  def fetch_header(self):
    return struct.unpack(self.header_fmt, self.fetch(0,self.header_size))
          
  def block(self, block_number):
    """
    Returns the block for given block number 
    """
    
    offset = self.block_offset(block_number)
    block = self.fetch(offset, offset+self.block_size)    
    return IndexBlockReader(block)
    
  def block_offset(self, block_number):
    return self.header_size + (self.block_size*block_number)
    
  def count_levels(self):
    """Return the number of 'levels' in the index. This number represents
    how many seeks have to be preformed before finding
    the starting data block"""
    
    
    block_number = 0
    block = self.block(block_number)
    levels = 1
    
    while True:
      buffer = StringIO(block.data)
      next_block_number = block.read_offset(buffer)
      if next_block_number < self.index_block_size:
        block_number = next_block_number
        block = self.block(block_number)
        levels += 1
      else:
        # it's the start of the data segments,
        return levels

    
  def expected_location(self, key):
    """
    Given a key, return the expected starting location for the key in the data
    segment. The return value is only the location  where the key "should" be
    not neccesarily where it is. This enables range queries
     
    """
    if key == '':
      start_block = self.index_block_size
      return self.block_offset(start_block)
    
    starting_block = self.find_starting_data_block(key)
    offset = self.block_offset(starting_block)
    data = self.fetch(offset,offset+self.block_size)

    
    # linear scan through the block, looking for the position of the stored key
    # that is greater than the given key
    
    start = 0
    loc = 0
    while True:
      pos = data.find(self.terminator, start)
      if pos == -1:
        # can this really happen?
        return len(data)
      stored = data[start:pos]
      if key <= stored:
        return start + offset
      else:
        start = pos + 1 + self.value_size
        


  def find_starting_data_block(self,key):
    """
    Return the number of the first data block where the key should be found.
    """

    block_number = 0
    block = self.block(block_number)
    
    while True:
      next_block_number = block.find(key)
      if next_block_number < self.index_block_size:
        block_number = next_block_number
        block = self.block(block_number)
      else:
        # it's the start of the data segments,
        return next_block_number
    
  def keys(self, prefix=''):
    return list(self.keyiter(prefix))

  def keyiter(self, prefix=''):
    for key, value in self.itemsiter(prefix):
      if key.startswith(prefix):
        yield key

  def values(self, prefix=''):
    return list(self.valueiter(prefix))
    
  def valueiter(self, prefix=''):
    for key, value in self.itemsiter(prefix):
      if key.startswith(prefix):
        yield value
      

  def items(self, prefix=''):
    return list(self.itemsiter(prefix))

  def itemsiter(self, prefix):
    starting_block = self.find_starting_data_block(prefix)
    blocks = self.blockiter(starting_block)

    # skip over keys in the first block
    first_block = blocks.next()
    for key,value in itertools.dropwhile(lambda (k,v): not k.startswith(prefix), self.dataiter(first_block)):
      if not key.startswith(prefix):
        return
      yield key,value

    for block in blocks:
      for key,value in self.dataiter(block):
        if not key.startswith(prefix):
          return
        else:
          yield key,value
    
    
  def parse_value(self, bytes):
    """
    Returns a scalar
    """
    return struct.unpack(
      self.value_format,
      bytes
    )[0]
    

  def blockiter(self, block_number):
    """
    Iterate over blocks starting with the given block_number
    """

    while True:
      offset = self.block_offset(block_number)
      block = self.mmap[offset:offset+self.block_size]
      if block:
        yield block
        block_number += 1
      else:
        break
        
  def dataiter(self, block):    
    for key, value in DataBlockReader(block, self.value_size, self.terminator):
      yield key, self.parse_value(value)


class PBTreeDictReader(PBTreeReader):
  def __init__(self, stream, item_keys, **options):
    self.item_keys = item_keys
    super(PBTreeDictReader, self).__init__(stream, **options)
    
  def parse_value(self, bytes):
    """
    Returns a dictionary
    """
    
    return dict(zip(
      self.item_keys,
      struct.unpack(self.value_format,bytes)
    ))
    
####
# Lower level constructs whose functionality has been seperated out to make
# usabale within map/reduce constructs
###

class DataWriter(object):
  def __init__(self, stream, block_size, terminator, delegate):
    self.finalized = False
    self.delegate = delegate
    
    self.block_size = block_size
    self.remaining = self.block_size
        
    self.terminator = terminator
    self.term_length = len(self.terminator)
    
    self.stream = stream
    self.write_buffer = bytearray()
        
    
  def add(self, key, value):

    packet = self.delegate.pack_value(value)
    size = len(key) + self.term_length + len(packet)
    
    if size > self.block_size:
      self.delegate.on_item_exceeds_block_size(key,value)
      return
    
    if size > self.remaining:
      self.write_buffer.extend(self.terminator * self.remaining)
      self.stream.write(self.write_buffer)
      del self.write_buffer[:]
      self.remaining = self.block_size
      self.delegate.on_new_block(key)
      
    self.write_buffer.extend(key)
    self.write_buffer.extend(self.terminator)
    self.write_buffer.extend(packet)

    self.remaining -= size
 
  def close(self):
    if not self.finalized:
      self.finish()
    self.stream.close()
    
  def finish(self):
    if self.write_buffer:
      self.write_buffer.extend(self.terminator * self.remaining)
      self.stream.write(self.write_buffer)
    
    del self.write_buffer
    self.delegate = None
    self.stream.seek(0)
    self.finalized = True
    
  def read(self, bytes = None):
    """
    Returns bytes written to the stream.
    
    It is an error to call this method prior to calling DataWriter.finish()
    """
    return self.stream.read(bytes)
  
class IndexWriter(object):
  def __init__(self, stream,  block_size, terminator, pointer_format='<I'):
    self.stream = stream
    self.block_size = block_size
    self.terminator = terminator
    self.term_size = len(terminator)
    
    self.pointer_format = pointer_format
    self.pointer_size = struct.calcsize(pointer_format)
    
    self.indexes = []
    self.push_index()
  
  def add(self, level, key):
    """
    Add's the key to the given index level
    """
    size = len(key) + self.term_size + self.pointer_size
    stream, pointers, remaining = self.indexes[level]
    
    
    if size > remaining:
      # pad the rest with null bytes
      stream.write(self.terminator * remaining)
      assert stream.tell() % self.block_size == 0
            
      # start the block off with the offset
      stream.write(struct.pack(self.pointer_format, pointers))
      
      next_level = level + 1
      if next_level > len(self.indexes)-1:
        self.push_index()
      self.add(next_level, key)
      remaining = self.block_size - self.pointer_size
    
    pointers += 1  
    stream.write(key)
    stream.write(self.terminator)
    stream.write(struct.pack(self.pointer_format, pointers))

    remaining = remaining - size 
    self.indexes[level] = stream, pointers, remaining

  def push_index(self):
    stream = SpooledTemporaryFile(max_size = 20*MB)
  
    pointers = 0
    stream.write(struct.pack(OFFSET_FMT,pointers))
  
    self.indexes.append([
      stream, pointers, self.block_size-self.pointer_size
    ])
    
  def finish(self):
    out = self.stream
    blocks_written = 0
    
    out.write(struct.pack(OFFSET_FMT, self.block_size))
    
    # blocks in the index
    out.write(struct.pack(OFFSET_FMT, 0))
        
    
    for stream, pointers, remaining in reversed(self.indexes):

      # pad the stream    
      stream.write(self.terminator * remaining)
      level_length = stream.tell()
      
      assert level_length % self.block_size == 0
      
      blocks_to_write = (level_length / self.block_size)
      
      stream.seek(0)

      # loop through each pointer and key writing
      for o, key in PBTreeReader.parse(stream, self.block_size):
        out.write(struct.pack(self.pointer_format, o+blocks_written+blocks_to_write))
        # note: the last key in the block returned by the reader will be all null bytes
        # pads
        out.write(key)

      blocks_written += blocks_to_write
      stream.close()
    
    out.seek(OFFSET_SIZE)
    out.write(struct.pack(OFFSET_FMT, blocks_written))
    out.seek(0,2) # move to the end of the file  

    self.blocks_written = blocks_written
  

  def close(self):
    self.finish()

class DataBlockReader(object):
  def __init__(self, bytes, value_size, terminator='\0'):
    self.bytes        = bytes
    self.terminator   = terminator
    self.value_size   = value_size
    
    
  def __iter__(self):
    block = self.bytes
    start = 0
    while True:
      pos = block.find(self.terminator, start)
      if pos == -1:
        break
      key = block[start:pos]
      start=pos+1

      if key == '':
        return
      else:
        value = block[start:start+self.value_size]
        start+=self.value_size

        yield key, value

  

class IndexBlockReader(object):
  def __init__(self, data):
    self.data = data


  def __iter__(self):
    end_of_block = False
    buffer = StringIO(self.data)
  
    while not end_of_block:
      offset = self.read_offset(buffer)

      key = self.read_key(buffer)
      # near the end of the block, eveything from here on should be null bytes
      if key == '':
        # ended on block boundry
        end_of_block = True
      elif key == '\0':
        # nothing but pad bytes left
        end_of_block = True
        key += self.read_rest_of_block(buffer)

      yield offset, key
  
  def find(self, key):
    pointers = []
    prefixes = []
    for pointer, prefix in self:
      pointers.append(pointer)
      prefixes.append(prefix)
      
    # discard padding
    prefixes.pop()
    
    index = bisect.bisect(prefixes, key)
    return pointers[index]
        

  def read_offset(self, buffer):

    bytes = buffer.read(OFFSET_SIZE)
    # bytes should never be empty when reading an offset if so the file
    # corrupt
    return struct.unpack(OFFSET_FMT, bytes)[0]


  def read_key(self, buffer):
    buff = bytearray()
    while True:
      c = buffer.read(1)
      if c == '':
        if len(buff):
          raise RuntimeError('EOF found when string was expected')
        else:
          break
      elif c == '\0':
        buff.append(c)
        break
      else:
        buff.append(c)
    return str(buff)
    
  def read_rest_of_block(self, buffer):
    return buffer.read()



    



########NEW FILE########
__FILENAME__ = prefix
# Copyright 2012 Triv.io, Scott Robertson
# 
#   Licensed under the Apache License, Version 2.0 (the "License");
#   you may not use this file except in compliance with the License.
#   You may obtain a copy of the License at
# 
#       http://www.apache.org/licenses/LICENSE-2.0
# 
#   Unless required by applicable law or agreed to in writing, software
#   distributed under the License is distributed on an "AS IS" BASIS,
#   WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#   See the License for the specific language governing permissions and
#   limitations under the License.
# 

from  itertools import izip_longest, dropwhile

def commonlen(s1,s2):
  """
  Returns the length of the common prefix
  """
      
  # given "hi", "hip"
  # izip_longest("hi", "hip") -> ('h','h'), ('i','i'), (None, 'p')
  # enumerate -> (0,('h','h')), (1,('i','i')), (2,(None, 'p'))
  # dropwhile(lambda (i,(x,y)): x == 5 -> (2,(None,'p')) ...
  
  try:  
    return dropwhile(lambda (i,(x,y)): x == y,enumerate(zip(s1, s2))).next()[0]
  except StopIteration:
    # strings are identical return the len of one of them
    return len(s1)

def common(s1,s2):
  """
  Returns the  common prefix
  """
  cl = commonlen(s1,s2)
  return s2[:cl]

def signifigant(s1,s2):
  """
  Given two strings s1 and s2, and assuming s2 > s1 returns the character
  that make s2 gerater.
  """  
  cl = commonlen(s1,s2)
  return s2[:cl+1]

########NEW FILE########
__FILENAME__ = test
# Copyright [2012] [Triv.io, Scott Robertson]
# 
#   Licensed under the Apache License, Version 2.0 (the "License");
#   you may not use this file except in compliance with the License.
#   You may obtain a copy of the License at
# 
#       http://www.apache.org/licenses/LICENSE-2.0
# 
#   Unless required by applicable law or agreed to in writing, software
#   distributed under the License is distributed on an "AS IS" BASIS,
#   WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#   See the License for the specific language governing permissions and
#   limitations under the License.
# 

from unittest import TestCase
from tempfile import NamedTemporaryFile
from functools import partial
from nose.tools import eq_
import mmap


class TestIndex(TestCase):
  def test_btree_index(self):
    from .pbtree import PBTreeWriter, PBTreeReader
    
    def data():
      """Returns an iterator of (url, linepos)"""
      return ((url.strip(), pos) for pos, url in enumerate(open('sorted_urls')))

    self.validate(
      PBTreeWriter,
      PBTreeReader,
      data(),
      prefix = 'http://natebeaty.com/',
      known_keys = [
        'http://natebeaty.com/illustration/4452349850',
        'http://natebeaty.com/illustration/4573016166',
        'http://natebeaty.com/illustration/4747271212',
        'http://natebeaty.com/illustration/4752986875',
      ],
      known_values =[
        1891,
        1892,
        1893,
        1894
      ]
    )
    
  def test_btree_dict_index(self):
    from .pbtree import PBTreeDictWriter, PBTreeDictReader
    
    writer = partial(PBTreeDictWriter, item_keys=("key1", "key2"), value_format="<QI")
    reader = partial(PBTreeDictReader, item_keys=("key1", "key2"), value_format="<QI")

    
    def data():
      for pos, url in enumerate(open('sorted_urls')):
        yield url.strip(), {'key1': pos, 'key2': pos}


    self.validate(
      writer,
      reader,
      data(),
      prefix = 'http://natebeaty.com/',
      known_keys = [
        'http://natebeaty.com/illustration/4452349850',
        'http://natebeaty.com/illustration/4573016166',
        'http://natebeaty.com/illustration/4747271212',
        'http://natebeaty.com/illustration/4752986875',
      ],
      known_values =[
        {'key1': 1891, 'key2': 1891},
        {'key1': 1892, 'key2': 1892},
        {'key1': 1893, 'key2': 1893},
        {'key1': 1894, 'key2': 1894}
      ]
    )
  
  
  def validate(self, writer, reader, data, prefix, known_keys, known_values):
    """
    Verify  given writer produces content that can be read by the given
    reader and  returns known keys and values for the given prefix
    
    """
  
    temp = NamedTemporaryFile(delete=False)
    index = writer(temp)

    keys_written = []
    for key, value in data:
      index.add(key, value)
      keys_written.append(key)
    index.close()

    ii = open(temp.name, 'r+')
    map = mmap.mmap(ii.fileno(),0)
    index = reader(map)
    keys = index.keys(prefix)

    self.assertListEqual(keys,known_keys)
    
    values = index.values(prefix)
    self.assertListEqual(values,known_values)
    
    items = index.items(prefix)

    self.assertListEqual(items, zip(known_keys, known_values))

    self.assertListEqual(index.keys(), keys_written)
  
########NEW FILE########
__FILENAME__ = test_map
# <data segment> :: = <item> (<item> | ( {<null>} <null>))
# <item> ::= <key> <null> <location pointer>

# 
#

from unittest import TestCase
from .prefix import signifigant


class TestIndexMapCase(TestCase):
  def test(self):
    class P():
      pass
    params = P()
  
    results =[]
    for partition_number, input in enumerate(inputs):
      params.last_key = None
      params.partition_number = partition_number
      for block in input:
        for item in map_block(iter(block), params):
          results.append(item)

    self.assertSequenceEqual(results, final)  



file1 = [
  [
    'key01',
    'key02',
    'key03a',
    'key03ac',
  ],
  [
    'key03bc'
    'key06',
    'key07',
    'key08z',
  ],
  [
    'key08zafz'
    'key10',
    'key11',
    'key12',
  ],
]

file2= [
  [
    'key13feee',
    'key14',
    'key16',
    'key16a',
  ],
  [
    'key16b'
    'key18',
    'key19',
    'key20',
  ]
]


final=(
  (0,"key01"),
  (0,"key03b"),
  (0,"key08za"),
  (1,"key13feee"),
  (1,"key16b")
)

inputs = [file1, file2]

def map_block(block, params):
  # yield first item and last

  first_key = block.next()
  assert first_key.find('\0') == -1
  
  if params.last_key is None:
    yield params.partition_number, first_key
  else:
    yield params.partition_number, signifigant(params.last_key, first_key)

  second_to_last = None
  for key in block:
    if not key.startswith('\0'):
      second_to_last = key

  if second_to_last is not None:
    params.last_key = second_to_last
  else:
    params.last_key = first_key
  
  
  
  
  
########NEW FILE########
__FILENAME__ = test_pbtree
# Copyright 2012 Triv.io, Scott Robertson]
# 
#   Licensed under the Apache License, Version 2.0 (the "License");
#   you may not use this file except in compliance with the License.
#   You may obtain a copy of the License at
# 
#       http://www.apache.org/licenses/LICENSE-2.0
# 
#   Unless required by applicable law or agreed to in writing, software
#   distributed under the License is distributed on an "AS IS" BASIS,
#   WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#   See the License for the specific language governing permissions and
#   limitations under the License.
# 

from unittest import TestCase

from nose.tools import eq_

from .pbtree import PBTreeWriter, PBTreeReader, IndexWriter
from tempfile import TemporaryFile

class TestPBTree(TestCase):
  def test_btree_index(self):
    t = TemporaryFile()
    pbtree = PBTreeWriter(t)
    pbtree.add("blah", 1)
    #pbtree.commit()
    
    #t.seek(0)
    packet = pbtree.data_segment.write_buffer #t.read()
    
    eq_(packet, 'blah\x00\x01\x00\x00\x00\x00\x00\x00\x00')
    
  def test_one_key_per_block_writer(self):
    # 2 pointers and a 1 byte string null terminated string = 10 bytes
    stream = TemporaryFile()
    
    i = IndexWriter(stream, block_size=10, terminator='\0')
    i.add(0, 'b')
    eq_(len(i.indexes), 1)
    
    i.add(0, 'c')
    eq_(len(i.indexes), 2)
    i.finish()


    stream.seek(0)
    packet = stream.read()
    eq_(len(packet), 30)
    

    root_block = packet[:10]
    eq_(root_block, '\x01\x00\x00\x00c\x00\x02\x00\x00\x00')
    
    block_1 = packet[10:20]
    eq_(block_1, '\x03\x00\x00\x00b\x00\x04\x00\x00\x00')
    
    block_2 = packet[20:]
    eq_(block_2, '\x04\x00\x00\x00c\x00\x05\x00\x00\x00')
########NEW FILE########
