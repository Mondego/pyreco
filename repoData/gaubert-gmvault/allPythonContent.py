__FILENAME__ = add_version
'''
    Gmvault: a tool to backup and restore your gmail account.
    Copyright (C) <2011-2013>  <guillaume Aubert (guillaume dot aubert at gmail do com)>

    This program is free software: you can redistribute it and/or modify
    it under the terms of the GNU Affero General Public License as
    published by the Free Software Foundation, either version 3 of the
    License, or (at your option) any later version.

    This program is distributed in the hope that it will be useful,
    but WITHOUT ANY WARRANTY; without even the implied warranty of
    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
    GNU Affero General Public License for more details.

    You should have received a copy of the GNU Affero General Public License
    along with this program.  If not, see <http://www.gnu.org/licenses/>.

'''

import sys
import re

def find_version(path):

    fd = open(path)

    for line in fd:
        index = line.find("GMVAULT_VERSION=\"")
        if index > -1:
            print(line[index+17:-2])
            return line[index+17:-2]

    raise Exception("Cannot find GMVAULT_VERSION in %s\n" % (path))

VERSION_PATTERN = r'###GMVAULTVERSION###' 
VERSION_RE      = re.compile(VERSION_PATTERN)

def add_version(a_input, a_output, a_version):
    """
	"""
    the_in  = open(a_input, 'r')
    the_out = open(a_output, 'w')
    for line in the_in:
        line = VERSION_RE.sub(a_version, line)
        the_out.write(line)

if __name__ == '__main__':

  if len(sys.argv) < 4:
     print("Error: need more parameters for %s." % (sys.argv[0]))
     print("Usage: add_version.py input_path output_path version.")
     exit(-1)

  #print("path = %s\n" % (sys.argv[1]))
  
  add_version(sys.argv[1], sys.argv[2], sys.argv[3])


########NEW FILE########
__FILENAME__ = find_version
'''
    Gmvault: a tool to backup and restore your gmail account.
    Copyright (C) <2011-2013>  <guillaume Aubert (guillaume dot aubert at gmail do com)>

    This program is free software: you can redistribute it and/or modify
    it under the terms of the GNU Affero General Public License as
    published by the Free Software Foundation, either version 3 of the
    License, or (at your option) any later version.

    This program is distributed in the hope that it will be useful,
    but WITHOUT ANY WARRANTY; without even the implied warranty of
    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
    GNU Affero General Public License for more details.

    You should have received a copy of the GNU Affero General Public License
    along with this program.  If not, see <http://www.gnu.org/licenses/>.

'''

import sys

def find_version(path):

    fd = open(path)

    for line in fd:
        index = line.find("GMVAULT_VERSION = \"")
        if index > -1:
            print(line[index+19:-2])
            res = line[index+19:-2]
            return res.strip()

    raise Exception("Cannot find GMVAULT_VERSION in %s\n" % (path))


if __name__ == '__main__':

  if len(sys.argv) < 2:
     print("Error: Need the path to gmv_cmd.py")
     exit(-1)

  #print("path = %s\n" % (sys.argv[1]))
  
  find_version(sys.argv[1])


########NEW FILE########
__FILENAME__ = flask_stats
from flask import Flask

import scrapping
import json
import datetime

app = Flask(__name__)

@app.route("/")
def hello():
    return "error 404"

@app.route("/stats")
def stats():
    return scrapping.get_stats("JSON")


if __name__ == "__main__":
    app.run(debug=False, host='0.0.0.0', port=8181)
    #app.run(debug=False, port=80)

########NEW FILE########
__FILENAME__ = reftree

import gc
import sys

from types import FrameType


class Tree:
    
    def __init__(self, obj):
        self.obj = obj
        self.filename = sys._getframe().f_code.co_filename
        self._ignore = {}
    
    def ignore(self, *objects):
        for obj in objects:
            self._ignore[id(obj)] = None
    
    def ignore_caller(self):
        f = sys._getframe()     # = this function
        cur = f.f_back          # = the function that called us (probably 'walk')
        self.ignore(cur, cur.f_builtins, cur.f_locals, cur.f_globals)
        caller = f.f_back       # = the 'real' caller
        self.ignore(caller, caller.f_builtins, caller.f_locals, caller.f_globals)
    
    def walk(self, maxresults=100, maxdepth=None):
        """Walk the object tree, ignoring duplicates and circular refs."""
        self.seen = {}
        self.ignore(self, self.__dict__, self.obj, self.seen, self._ignore)
        
        # Ignore the calling frame, its builtins, globals and locals
        self.ignore_caller()
        
        self.maxdepth = maxdepth
        count = 0
        for result in self._gen(self.obj):
            yield result
            count += 1
            if maxresults and count >= maxresults:
                yield 0, 0, "==== Max results reached ===="
                raise StopIteration
    
    def print_tree(self, maxresults=100, maxdepth=None):
        """Walk the object tree, pretty-printing each branch."""
        self.ignore_caller()
        for depth, refid, rep in self.walk(maxresults, maxdepth):
            print ("%9d" % refid), (" " * depth * 2), rep


def _repr_container(obj):
    return "%s of len %s: %r" % (type(obj).__name__, len(obj), obj)
repr_dict = _repr_container
repr_set = _repr_container
repr_list = _repr_container
repr_tuple = _repr_container

def repr_str(obj):
    return "%s of len %s: %r" % (type(obj).__name__, len(obj), obj)
repr_unicode = repr_str

def repr_frame(obj):
    return "frame from %s line %s" % (obj.f_code.co_filename, obj.f_lineno)

def get_repr(obj, limit=250):
    typename = getattr(type(obj), "__name__", None)
    handler = globals().get("repr_%s" % typename, repr)
    
    try:
        result = handler(obj)
    except:
        result = "unrepresentable object: %r" % sys.exc_info()[1]
    
    if len(result) > limit:
        result = result[:limit] + "..."
    
    return result


class ReferentTree(Tree):
    
    def _gen(self, obj, depth=0):
        if self.maxdepth and depth >= self.maxdepth:
            yield depth, 0, "---- Max depth reached ----"
            raise StopIteration
        
        for ref in gc.get_referents(obj):
            if id(ref) in self._ignore:
                continue
            elif id(ref) in self.seen:
                yield depth, id(ref), "!" + get_repr(ref)
                continue
            else:
                self.seen[id(ref)] = None
                yield depth, id(ref), get_repr(ref)
            
            for child in self._gen(ref, depth + 1):
                yield child


class ReferrerTree(Tree):
    
    def _gen(self, obj, depth=0):
        if self.maxdepth and depth >= self.maxdepth:
            yield depth, 0, "---- Max depth reached ----"
            raise StopIteration
        
        refs = gc.get_referrers(obj)
        refiter = iter(refs)
        self.ignore(refs, refiter)
        for ref in refiter:
            # Exclude all frames that are from this module.
            if isinstance(ref, FrameType):
                if ref.f_code.co_filename == self.filename:
                    continue
            
            if id(ref) in self._ignore:
                continue
            elif id(ref) in self.seen:
                yield depth, id(ref), "!" + get_repr(ref)
                continue
            else:
                self.seen[id(ref)] = None
                yield depth, id(ref), get_repr(ref)
            
            for parent in self._gen(ref, depth + 1):
                yield parent



class CircularReferents(Tree):
    
    def walk(self, maxresults=100, maxdepth=None):
        """Walk the object tree, showing circular referents."""
        self.stops = 0
        self.seen = {}
        self.ignore(self, self.__dict__, self.seen, self._ignore)
        
        # Ignore the calling frame, its builtins, globals and locals
        self.ignore_caller()
        
        self.maxdepth = maxdepth
        count = 0
        for result in self._gen(self.obj):
            yield result
            count += 1
            if maxresults and count >= maxresults:
                yield 0, 0, "==== Max results reached ===="
                raise StopIteration
    
    def _gen(self, obj, depth=0, trail=None):
        if self.maxdepth and depth >= self.maxdepth:
            self.stops += 1
            raise StopIteration
        
        if trail is None:
            trail = []
        
        for ref in gc.get_referents(obj):
            if id(ref) in self._ignore:
                continue
            elif id(ref) in self.seen:
                continue
            else:
                self.seen[id(ref)] = None
            
            refrepr = get_repr(ref)
            if id(ref) == id(self.obj):
                yield trail + [refrepr,]
            
            for child in self._gen(ref, depth + 1, trail + [refrepr,]):
                yield child
    
    def print_tree(self, maxresults=100, maxdepth=None):
        """Walk the object tree, pretty-printing each branch."""
        self.ignore_caller()
        for trail in self.walk(maxresults, maxdepth):
            print trail
        if self.stops:
            print "%s paths stopped because max depth reached" % self.stops


def count_objects():
    d = {}
    for obj in gc.get_objects():
        objtype = type(obj)
        d[objtype] = d.get(objtype, 0) + 1
    d = [(v, k) for k, v in d.iteritems()]
    d.sort()
    return d


########NEW FILE########
__FILENAME__ = memdebug
# memdebug.py

import cherrypy
import dowser

def start(port):
    cherrypy.tree.mount(dowser.Root())
    cherrypy.config.update({
        'environment': 'embedded',
        'server.socket_port': port
    })
    #cherrypy.quickstart()
    cherrypy.engine.start()

########NEW FILE########
__FILENAME__ = scrapping
'''
    Gmvault: a tool to backup and restore your gmail account.
    Copyright (C) <2011-2013>  <guillaume Aubert (guillaume dot aubert at gmail do com)>

    This program is free software: you can redistribute it and/or modify
    it under the terms of the GNU Affero General Public License as
    published by the Free Software Foundation, either version 3 of the
    License, or (at your option) any later version.

    This program is distributed in the hope that it will be useful,
    but WITHOUT ANY WARRANTY; without even the implied warranty of
    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
    GNU Affero General Public License for more details.

    You should have received a copy of the GNU Affero General Public License
    along with this program.  If not, see <http://www.gnu.org/licenses/>.

'''

#quick and dirty scrapper to get number of downloads

import json
import datetime
import mechanize
import BeautifulSoup as bs


def get_from_bitbucket():

    print("Get info from bitbucket\n")

    br = mechanize.Browser()
    br.open("https://bitbucket.org/gaubert/gmvault-official-download/downloads")

    response = br.response().read()

    #print("response = %s\n" % response)

    soup = bs.BeautifulSoup(response)

    #body_tag = soup.body
    all_tables = soup.findAll('table')

    table = soup.find(lambda tag: tag.name=='table' and tag.has_key('id') and tag['id']=="uploaded-files")

    rows = table.findAll(lambda tag: tag.name=='tr')

    res = {} 
    for row in rows:
       
       tds = row.findAll(lambda tag: tag.name == 'td')

       #print("tds = %s\n" %(tds))   

       td_number = 0
       name = None
       for td in tds:
           if td_number == 0:
              #print("td.a.string = %s\n" %(td.a.string))
              name = td.a.string
              res[name] = 0
           elif td_number == 3:
              #print("download nb = %s\n" %(td.string))
              res[name] = int(td.string)
           elif td_number == 4:
              #reset it
              td_number = 0
              name = None

           td_number += 1
           #print("td = %s\n" %(td))

    return res

def get_from_pypi(url):
 
    res = {}

    print("Get info from pypi (url= %s)\n" % (url))

    br = mechanize.Browser()
    br.open(url)

    response = br.response().read()

    soup = bs.BeautifulSoup(response)

    table = soup.find(lambda tag: tag.name == 'table')
    #print("all_tables = %s\n" % (all_tables))

    rows = table.findAll(lambda tag: tag.name == 'tr')

    #print("rows = %s\n" %(rows))

    for row in rows:
       
       tds = row.findAll(lambda tag: tag.name == 'td')

       #print("tds = %s\n" %(tds))   

       #ignore tds that are too small 
       if len(tds) < 6:
          #print("ignore td = %s\n" % (tds))
          continue

       td_number = 0
       name = None
       for td in tds:
           #print("td = %s\n" % (td))
           if td_number == 0:
              #print("td.a = %s\n" %(td.a))
              name = 'pypi-%s' % (td.a.string)
              res[name] = 0
           elif td_number == 5:
              #print("download nb = %s\n" %(td.string))
              res[name] = int(td.string)
           elif td_number == 6:
              #reset it
              td_number = 0
              name = None

           td_number += 1

    return res

V17W1_BETA_ON_GITHUB=7612
V17_BETA_SRC_ON_GITHUB=1264
V17_BETA_MAC_ON_GITHUB=2042

WIN_TOTAL_PREVIOUS_VERSIONS=2551+4303+3648+302+V17W1_BETA_ON_GITHUB
MAC_TOTAL_PREVIOUS_VERSIONS=2151+1806+1119+V17_BETA_MAC_ON_GITHUB
PYPI_TOTAL_PREVIOUS_VERSIONS=872+1065+826
SRC_TOTAL_PREVIOUS_VERSIONS=970+611+V17_BETA_SRC_ON_GITHUB
#LINUX is all Linux flavours available
LIN_TOTAL_PREVIOUS_VERSIONS=916+325+254+SRC_TOTAL_PREVIOUS_VERSIONS+PYPI_TOTAL_PREVIOUS_VERSIONS
TOTAL_PREVIOUS_VERSIONS=2551+2155+916+872+4303+1806+325+970+1065+3648+1119+254+611+826+302+V17_BETA_MAC_ON_GITHUB+V17_BETA_SRC_ON_GITHUB+V17W1_BETA_ON_GITHUB

def get_stats(return_type):
    """ return the stats """
    res = get_from_bitbucket()
    res.update(get_from_pypi("https://pypi.python.org/pypi/gmvault/1.8.1-beta"))
    res.update(get_from_pypi("https://pypi.python.org/pypi/gmvault/1.8-beta"))
    res.update(get_from_pypi("https://pypi.python.org/pypi/gmvault/1.7-beta"))

    #print("name , nb_downloads") 
    total = 0
    win_total   = 0
    lin_total   = 0
    mac_total   = 0
    v17_total   = 0
    v18_total   = 0 
    v181_total  = 0 
    pypi_total  = 0
    src_total   = 0
    for key in res.keys():
        #print("key= %s: (%s)\n" %(key, res[key]))
        if key.endswith(".exe"):
           win_total += res[key] 
        elif "macosx" in key:
           mac_total += res[key]
        else:
           lin_total += res[key]

        if "1.8" in key:
           #print("inv1.8: %s" % (key))
           v18_total += res[key]
        elif "1.7" in key:
           v17_total += res[key]

        if "src" in key:
           src_total += res[key]
        elif "pypi" in key:
           pypi_total += res[key]

        if "1.8.1" in key:
          v181_total += res[key]

        #print("%s, %s\n" % (key, res[key]))
        total += res[key]

    total      += TOTAL_PREVIOUS_VERSIONS 
    win_total  += WIN_TOTAL_PREVIOUS_VERSIONS
    lin_total  += LIN_TOTAL_PREVIOUS_VERSIONS
    mac_total  += MAC_TOTAL_PREVIOUS_VERSIONS
    pypi_total += PYPI_TOTAL_PREVIOUS_VERSIONS  
    src_total  += SRC_TOTAL_PREVIOUS_VERSIONS

    the_str = ""
    if return_type == "TEXT":

        the_str += "As of today %s, total of downloads (v1.7 and v1.8) = %s.\n" %(datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S'),total)
        the_str += "win total = %s,\nmac total = %s,\nlin total = %s.\n" % (win_total, mac_total, lin_total)
        the_str += "pypi total = %s, src total = %s since .\n" % (pypi_total, src_total)
        the_str += "v1.7x total = %s since (17-12-2012), v1.8x = %s since (19-03-2013).\n" % (v17_total, v18_total)
        the_str += "v1.8.1 total = %s since (28.04.2013).\n" % (v181_total)

        return the_str

    elif return_type == "JSON":
        return json.dumps({'total' : total, 'now' : datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S'), \
                    'win_total' : win_total, 'mac_total' : mac_total, 'lin_total' : lin_total, \
                    "pypi_total" : pypi_total, "src_total" : src_total, \
                    'v17x_total' : v17_total, 'v18x_total' : v18_total, 'v181_total': v181_total})

if __name__ == "__main__":

    print(get_stats("JSON"))



########NEW FILE########
__FILENAME__ = blowfish
#!/usr/bin/env python
# -*- coding: utf-8 -*-
 
# blowfish.py
# Copyright (C) 2002 Michael Gilfix <mgilfix@eecs.tufts.edu>
#
# This module is open source; you can redistribute it and/or
# modify it under the terms of the GPL or Artistic License.
# These licenses are available at http://www.opensource.org
#
# This software must be used and distributed in accordance
# with the law. The author claims no liability for its
# misuse.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.
#
 
# This software was modified by Ivan Voras: CTR cipher mode of
# operation was added, together with testing and example code.
# These changes are (c) 2007./08. Ivan Voras <ivoras@gmail.com>
# These changes can be used, modified ad distributed under the
# GPL or Artistic License, the same as the original module.
# All disclaimers of warranty from the original module also
# apply to these changes.
 
# Further modifications by Neil Tallim <flan@uguu.ca> to make use
# of more modern Python practises and features, improving
# performance and, in this maintainer's opinion, readability.
#
# New changes implemented (and copyrighted, I suppose),
# June 13, 2010, subject to the terms of the original module.
"""
Blowfish Encryption
 
This module is a pure python implementation of Bruce Schneier's
encryption scheme 'Blowfish'. Blowish is a 16-round Feistel Network
cipher and offers substantial speed gains over DES.
 
The key is a string of length anywhere between 64 and 448 bits, or
equivalently 8 and 56 bytes. The encryption and decryption functions operate
on 64-bit blocks, or 8-byte strings.
"""
import array
import struct
 
class Blowfish:
    """
    Implements the encryption and decryption functionality of the Blowfish
    cipher, as well as CTR processing for arbitrary-length strings.
    """
    # Key restrictions
    KEY_MIN_LEN = 8 #64 bits
    KEY_MAX_LEN = 56 #448 bits
 
    # Cipher directions
    ENCRYPT = 0
    DECRYPT = 1
 
    # For _round()
    _MODULUS = 2L ** 32
 
    # CTR constants
    _BLOCK_SIZE = 8
 
    def __init__(self, key):
        """
        Creates an instance of blowfish using 'key' as the encryption key.
 
        Key is a string of bytes, used to seed calculations.
        Once the instance of the object is created, the key is no longer necessary.
        """
        if not self.KEY_MIN_LEN <= len(key) <= self.KEY_MAX_LEN:
            raise ValueError("Attempted to initialize Blowfish cipher with key of invalid length: %(len)i" % {
             'len': len(key),
            })
 
        self._p_boxes = array.array('I', [
            0x243F6A88, 0x85A308D3, 0x13198A2E, 0x03707344,
            0xA4093822, 0x299F31D0, 0x082EFA98, 0xEC4E6C89,
            0x452821E6, 0x38D01377, 0xBE5466CF, 0x34E90C6C,
            0xC0AC29B7, 0xC97C50DD, 0x3F84D5B5, 0xB5470917,
            0x9216D5D9, 0x8979FB1B
        ])
 
        self._s_boxes = (
            array.array('I', [
                0xD1310BA6, 0x98DFB5AC, 0x2FFD72DB, 0xD01ADFB7,
                0xB8E1AFED, 0x6A267E96, 0xBA7C9045, 0xF12C7F99,
                0x24A19947, 0xB3916CF7, 0x0801F2E2, 0x858EFC16,
                0x636920D8, 0x71574E69, 0xA458FEA3, 0xF4933D7E,
                0x0D95748F, 0x728EB658, 0x718BCD58, 0x82154AEE,
                0x7B54A41D, 0xC25A59B5, 0x9C30D539, 0x2AF26013,
                0xC5D1B023, 0x286085F0, 0xCA417918, 0xB8DB38EF,
                0x8E79DCB0, 0x603A180E, 0x6C9E0E8B, 0xB01E8A3E,
                0xD71577C1, 0xBD314B27, 0x78AF2FDA, 0x55605C60,
                0xE65525F3, 0xAA55AB94, 0x57489862, 0x63E81440,
                0x55CA396A, 0x2AAB10B6, 0xB4CC5C34, 0x1141E8CE,
                0xA15486AF, 0x7C72E993, 0xB3EE1411, 0x636FBC2A,
                0x2BA9C55D, 0x741831F6, 0xCE5C3E16, 0x9B87931E,
                0xAFD6BA33, 0x6C24CF5C, 0x7A325381, 0x28958677,
                0x3B8F4898, 0x6B4BB9AF, 0xC4BFE81B, 0x66282193,
                0x61D809CC, 0xFB21A991, 0x487CAC60, 0x5DEC8032,
                0xEF845D5D, 0xE98575B1, 0xDC262302, 0xEB651B88,
                0x23893E81, 0xD396ACC5, 0x0F6D6FF3, 0x83F44239,
                0x2E0B4482, 0xA4842004, 0x69C8F04A, 0x9E1F9B5E,
                0x21C66842, 0xF6E96C9A, 0x670C9C61, 0xABD388F0,
                0x6A51A0D2, 0xD8542F68, 0x960FA728, 0xAB5133A3,
                0x6EEF0B6C, 0x137A3BE4, 0xBA3BF050, 0x7EFB2A98,
                0xA1F1651D, 0x39AF0176, 0x66CA593E, 0x82430E88,
                0x8CEE8619, 0x456F9FB4, 0x7D84A5C3, 0x3B8B5EBE,
                0xE06F75D8, 0x85C12073, 0x401A449F, 0x56C16AA6,
                0x4ED3AA62, 0x363F7706, 0x1BFEDF72, 0x429B023D,
                0x37D0D724, 0xD00A1248, 0xDB0FEAD3, 0x49F1C09B,
                0x075372C9, 0x80991B7B, 0x25D479D8, 0xF6E8DEF7,
                0xE3FE501A, 0xB6794C3B, 0x976CE0BD, 0x04C006BA,
                0xC1A94FB6, 0x409F60C4, 0x5E5C9EC2, 0x196A2463,
                0x68FB6FAF, 0x3E6C53B5, 0x1339B2EB, 0x3B52EC6F,
                0x6DFC511F, 0x9B30952C, 0xCC814544, 0xAF5EBD09,
                0xBEE3D004, 0xDE334AFD, 0x660F2807, 0x192E4BB3,
                0xC0CBA857, 0x45C8740F, 0xD20B5F39, 0xB9D3FBDB,
                0x5579C0BD, 0x1A60320A, 0xD6A100C6, 0x402C7279,
                0x679F25FE, 0xFB1FA3CC, 0x8EA5E9F8, 0xDB3222F8,
                0x3C7516DF, 0xFD616B15, 0x2F501EC8, 0xAD0552AB,
                0x323DB5FA, 0xFD238760, 0x53317B48, 0x3E00DF82,
                0x9E5C57BB, 0xCA6F8CA0, 0x1A87562E, 0xDF1769DB,
                0xD542A8F6, 0x287EFFC3, 0xAC6732C6, 0x8C4F5573,
                0x695B27B0, 0xBBCA58C8, 0xE1FFA35D, 0xB8F011A0,
                0x10FA3D98, 0xFD2183B8, 0x4AFCB56C, 0x2DD1D35B,
                0x9A53E479, 0xB6F84565, 0xD28E49BC, 0x4BFB9790,
                0xE1DDF2DA, 0xA4CB7E33, 0x62FB1341, 0xCEE4C6E8,
                0xEF20CADA, 0x36774C01, 0xD07E9EFE, 0x2BF11FB4,
                0x95DBDA4D, 0xAE909198, 0xEAAD8E71, 0x6B93D5A0,
                0xD08ED1D0, 0xAFC725E0, 0x8E3C5B2F, 0x8E7594B7,
                0x8FF6E2FB, 0xF2122B64, 0x8888B812, 0x900DF01C,
                0x4FAD5EA0, 0x688FC31C, 0xD1CFF191, 0xB3A8C1AD,
                0x2F2F2218, 0xBE0E1777, 0xEA752DFE, 0x8B021FA1,
                0xE5A0CC0F, 0xB56F74E8, 0x18ACF3D6, 0xCE89E299,
                0xB4A84FE0, 0xFD13E0B7, 0x7CC43B81, 0xD2ADA8D9,
                0x165FA266, 0x80957705, 0x93CC7314, 0x211A1477,
                0xE6AD2065, 0x77B5FA86, 0xC75442F5, 0xFB9D35CF,
                0xEBCDAF0C, 0x7B3E89A0, 0xD6411BD3, 0xAE1E7E49,
                0x00250E2D, 0x2071B35E, 0x226800BB, 0x57B8E0AF,
                0x2464369B, 0xF009B91E, 0x5563911D, 0x59DFA6AA,
                0x78C14389, 0xD95A537F, 0x207D5BA2, 0x02E5B9C5,
                0x83260376, 0x6295CFA9, 0x11C81968, 0x4E734A41,
                0xB3472DCA, 0x7B14A94A, 0x1B510052, 0x9A532915,
                0xD60F573F, 0xBC9BC6E4, 0x2B60A476, 0x81E67400,
                0x08BA6FB5, 0x571BE91F, 0xF296EC6B, 0x2A0DD915,
                0xB6636521, 0xE7B9F9B6, 0xFF34052E, 0xC5855664,
                0x53B02D5D, 0xA99F8FA1, 0x08BA4799, 0x6E85076A
            ]),
            array.array('I', [
                0x4B7A70E9, 0xB5B32944, 0xDB75092E, 0xC4192623,
                0xAD6EA6B0, 0x49A7DF7D, 0x9CEE60B8, 0x8FEDB266,
                0xECAA8C71, 0x699A17FF, 0x5664526C, 0xC2B19EE1,
                0x193602A5, 0x75094C29, 0xA0591340, 0xE4183A3E,
                0x3F54989A, 0x5B429D65, 0x6B8FE4D6, 0x99F73FD6,
                0xA1D29C07, 0xEFE830F5, 0x4D2D38E6, 0xF0255DC1,
                0x4CDD2086, 0x8470EB26, 0x6382E9C6, 0x021ECC5E,
                0x09686B3F, 0x3EBAEFC9, 0x3C971814, 0x6B6A70A1,
                0x687F3584, 0x52A0E286, 0xB79C5305, 0xAA500737,
                0x3E07841C, 0x7FDEAE5C, 0x8E7D44EC, 0x5716F2B8,
                0xB03ADA37, 0xF0500C0D, 0xF01C1F04, 0x0200B3FF,
                0xAE0CF51A, 0x3CB574B2, 0x25837A58, 0xDC0921BD,
                0xD19113F9, 0x7CA92FF6, 0x94324773, 0x22F54701,
                0x3AE5E581, 0x37C2DADC, 0xC8B57634, 0x9AF3DDA7,
                0xA9446146, 0x0FD0030E, 0xECC8C73E, 0xA4751E41,
                0xE238CD99, 0x3BEA0E2F, 0x3280BBA1, 0x183EB331,
                0x4E548B38, 0x4F6DB908, 0x6F420D03, 0xF60A04BF,
                0x2CB81290, 0x24977C79, 0x5679B072, 0xBCAF89AF,
                0xDE9A771F, 0xD9930810, 0xB38BAE12, 0xDCCF3F2E,
                0x5512721F, 0x2E6B7124, 0x501ADDE6, 0x9F84CD87,
                0x7A584718, 0x7408DA17, 0xBC9F9ABC, 0xE94B7D8C,
                0xEC7AEC3A, 0xDB851DFA, 0x63094366, 0xC464C3D2,
                0xEF1C1847, 0x3215D908, 0xDD433B37, 0x24C2BA16,
                0x12A14D43, 0x2A65C451, 0x50940002, 0x133AE4DD,
                0x71DFF89E, 0x10314E55, 0x81AC77D6, 0x5F11199B,
                0x043556F1, 0xD7A3C76B, 0x3C11183B, 0x5924A509,
                0xF28FE6ED, 0x97F1FBFA, 0x9EBABF2C, 0x1E153C6E,
                0x86E34570, 0xEAE96FB1, 0x860E5E0A, 0x5A3E2AB3,
                0x771FE71C, 0x4E3D06FA, 0x2965DCB9, 0x99E71D0F,
                0x803E89D6, 0x5266C825, 0x2E4CC978, 0x9C10B36A,
                0xC6150EBA, 0x94E2EA78, 0xA5FC3C53, 0x1E0A2DF4,
                0xF2F74EA7, 0x361D2B3D, 0x1939260F, 0x19C27960,
                0x5223A708, 0xF71312B6, 0xEBADFE6E, 0xEAC31F66,
                0xE3BC4595, 0xA67BC883, 0xB17F37D1, 0x018CFF28,
                0xC332DDEF, 0xBE6C5AA5, 0x65582185, 0x68AB9802,
                0xEECEA50F, 0xDB2F953B, 0x2AEF7DAD, 0x5B6E2F84,
                0x1521B628, 0x29076170, 0xECDD4775, 0x619F1510,
                0x13CCA830, 0xEB61BD96, 0x0334FE1E, 0xAA0363CF,
                0xB5735C90, 0x4C70A239, 0xD59E9E0B, 0xCBAADE14,
                0xEECC86BC, 0x60622CA7, 0x9CAB5CAB, 0xB2F3846E,
                0x648B1EAF, 0x19BDF0CA, 0xA02369B9, 0x655ABB50,
                0x40685A32, 0x3C2AB4B3, 0x319EE9D5, 0xC021B8F7,
                0x9B540B19, 0x875FA099, 0x95F7997E, 0x623D7DA8,
                0xF837889A, 0x97E32D77, 0x11ED935F, 0x16681281,
                0x0E358829, 0xC7E61FD6, 0x96DEDFA1, 0x7858BA99,
                0x57F584A5, 0x1B227263, 0x9B83C3FF, 0x1AC24696,
                0xCDB30AEB, 0x532E3054, 0x8FD948E4, 0x6DBC3128,
                0x58EBF2EF, 0x34C6FFEA, 0xFE28ED61, 0xEE7C3C73,
                0x5D4A14D9, 0xE864B7E3, 0x42105D14, 0x203E13E0,
                0x45EEE2B6, 0xA3AAABEA, 0xDB6C4F15, 0xFACB4FD0,
                0xC742F442, 0xEF6ABBB5, 0x654F3B1D, 0x41CD2105,
                0xD81E799E, 0x86854DC7, 0xE44B476A, 0x3D816250,
                0xCF62A1F2, 0x5B8D2646, 0xFC8883A0, 0xC1C7B6A3,
                0x7F1524C3, 0x69CB7492, 0x47848A0B, 0x5692B285,
                0x095BBF00, 0xAD19489D, 0x1462B174, 0x23820E00,
                0x58428D2A, 0x0C55F5EA, 0x1DADF43E, 0x233F7061,
                0x3372F092, 0x8D937E41, 0xD65FECF1, 0x6C223BDB,
                0x7CDE3759, 0xCBEE7460, 0x4085F2A7, 0xCE77326E,
                0xA6078084, 0x19F8509E, 0xE8EFD855, 0x61D99735,
                0xA969A7AA, 0xC50C06C2, 0x5A04ABFC, 0x800BCADC,
                0x9E447A2E, 0xC3453484, 0xFDD56705, 0x0E1E9EC9,
                0xDB73DBD3, 0x105588CD, 0x675FDA79, 0xE3674340,
                0xC5C43465, 0x713E38D8, 0x3D28F89E, 0xF16DFF20,
                0x153E21E7, 0x8FB03D4A, 0xE6E39F2B, 0xDB83ADF7
            ]),
            array.array('I', [
                0xE93D5A68, 0x948140F7, 0xF64C261C, 0x94692934,
                0x411520F7, 0x7602D4F7, 0xBCF46B2E, 0xD4A20068,
                0xD4082471, 0x3320F46A, 0x43B7D4B7, 0x500061AF,
                0x1E39F62E, 0x97244546, 0x14214F74, 0xBF8B8840,
                0x4D95FC1D, 0x96B591AF, 0x70F4DDD3, 0x66A02F45,
                0xBFBC09EC, 0x03BD9785, 0x7FAC6DD0, 0x31CB8504,
                0x96EB27B3, 0x55FD3941, 0xDA2547E6, 0xABCA0A9A,
                0x28507825, 0x530429F4, 0x0A2C86DA, 0xE9B66DFB,
                0x68DC1462, 0xD7486900, 0x680EC0A4, 0x27A18DEE,
                0x4F3FFEA2, 0xE887AD8C, 0xB58CE006, 0x7AF4D6B6,
                0xAACE1E7C, 0xD3375FEC, 0xCE78A399, 0x406B2A42,
                0x20FE9E35, 0xD9F385B9, 0xEE39D7AB, 0x3B124E8B,
                0x1DC9FAF7, 0x4B6D1856, 0x26A36631, 0xEAE397B2,
                0x3A6EFA74, 0xDD5B4332, 0x6841E7F7, 0xCA7820FB,
                0xFB0AF54E, 0xD8FEB397, 0x454056AC, 0xBA489527,
                0x55533A3A, 0x20838D87, 0xFE6BA9B7, 0xD096954B,
                0x55A867BC, 0xA1159A58, 0xCCA92963, 0x99E1DB33,
                0xA62A4A56, 0x3F3125F9, 0x5EF47E1C, 0x9029317C,
                0xFDF8E802, 0x04272F70, 0x80BB155C, 0x05282CE3,
                0x95C11548, 0xE4C66D22, 0x48C1133F, 0xC70F86DC,
                0x07F9C9EE, 0x41041F0F, 0x404779A4, 0x5D886E17,
                0x325F51EB, 0xD59BC0D1, 0xF2BCC18F, 0x41113564,
                0x257B7834, 0x602A9C60, 0xDFF8E8A3, 0x1F636C1B,
                0x0E12B4C2, 0x02E1329E, 0xAF664FD1, 0xCAD18115,
                0x6B2395E0, 0x333E92E1, 0x3B240B62, 0xEEBEB922,
                0x85B2A20E, 0xE6BA0D99, 0xDE720C8C, 0x2DA2F728,
                0xD0127845, 0x95B794FD, 0x647D0862, 0xE7CCF5F0,
                0x5449A36F, 0x877D48FA, 0xC39DFD27, 0xF33E8D1E,
                0x0A476341, 0x992EFF74, 0x3A6F6EAB, 0xF4F8FD37,
                0xA812DC60, 0xA1EBDDF8, 0x991BE14C, 0xDB6E6B0D,
                0xC67B5510, 0x6D672C37, 0x2765D43B, 0xDCD0E804,
                0xF1290DC7, 0xCC00FFA3, 0xB5390F92, 0x690FED0B,
                0x667B9FFB, 0xCEDB7D9C, 0xA091CF0B, 0xD9155EA3,
                0xBB132F88, 0x515BAD24, 0x7B9479BF, 0x763BD6EB,
                0x37392EB3, 0xCC115979, 0x8026E297, 0xF42E312D,
                0x6842ADA7, 0xC66A2B3B, 0x12754CCC, 0x782EF11C,
                0x6A124237, 0xB79251E7, 0x06A1BBE6, 0x4BFB6350,
                0x1A6B1018, 0x11CAEDFA, 0x3D25BDD8, 0xE2E1C3C9,
                0x44421659, 0x0A121386, 0xD90CEC6E, 0xD5ABEA2A,
                0x64AF674E, 0xDA86A85F, 0xBEBFE988, 0x64E4C3FE,
                0x9DBC8057, 0xF0F7C086, 0x60787BF8, 0x6003604D,
                0xD1FD8346, 0xF6381FB0, 0x7745AE04, 0xD736FCCC,
                0x83426B33, 0xF01EAB71, 0xB0804187, 0x3C005E5F,
                0x77A057BE, 0xBDE8AE24, 0x55464299, 0xBF582E61,
                0x4E58F48F, 0xF2DDFDA2, 0xF474EF38, 0x8789BDC2,
                0x5366F9C3, 0xC8B38E74, 0xB475F255, 0x46FCD9B9,
                0x7AEB2661, 0x8B1DDF84, 0x846A0E79, 0x915F95E2,
                0x466E598E, 0x20B45770, 0x8CD55591, 0xC902DE4C,
                0xB90BACE1, 0xBB8205D0, 0x11A86248, 0x7574A99E,
                0xB77F19B6, 0xE0A9DC09, 0x662D09A1, 0xC4324633,
                0xE85A1F02, 0x09F0BE8C, 0x4A99A025, 0x1D6EFE10,
                0x1AB93D1D, 0x0BA5A4DF, 0xA186F20F, 0x2868F169,
                0xDCB7DA83, 0x573906FE, 0xA1E2CE9B, 0x4FCD7F52,
                0x50115E01, 0xA70683FA, 0xA002B5C4, 0x0DE6D027,
                0x9AF88C27, 0x773F8641, 0xC3604C06, 0x61A806B5,
                0xF0177A28, 0xC0F586E0, 0x006058AA, 0x30DC7D62,
                0x11E69ED7, 0x2338EA63, 0x53C2DD94, 0xC2C21634,
                0xBBCBEE56, 0x90BCB6DE, 0xEBFC7DA1, 0xCE591D76,
                0x6F05E409, 0x4B7C0188, 0x39720A3D, 0x7C927C24,
                0x86E3725F, 0x724D9DB9, 0x1AC15BB4, 0xD39EB8FC,
                0xED545578, 0x08FCA5B5, 0xD83D7CD3, 0x4DAD0FC4,
                0x1E50EF5E, 0xB161E6F8, 0xA28514D9, 0x6C51133C,
                0x6FD5C7E7, 0x56E14EC4, 0x362ABFCE, 0xDDC6C837,
                0xD79A3234, 0x92638212, 0x670EFA8E, 0x406000E0
            ]),
            array.array('I', [
                0x3A39CE37, 0xD3FAF5CF, 0xABC27737, 0x5AC52D1B,
                0x5CB0679E, 0x4FA33742, 0xD3822740, 0x99BC9BBE,
                0xD5118E9D, 0xBF0F7315, 0xD62D1C7E, 0xC700C47B,
                0xB78C1B6B, 0x21A19045, 0xB26EB1BE, 0x6A366EB4,
                0x5748AB2F, 0xBC946E79, 0xC6A376D2, 0x6549C2C8,
                0x530FF8EE, 0x468DDE7D, 0xD5730A1D, 0x4CD04DC6,
                0x2939BBDB, 0xA9BA4650, 0xAC9526E8, 0xBE5EE304,
                0xA1FAD5F0, 0x6A2D519A, 0x63EF8CE2, 0x9A86EE22,
                0xC089C2B8, 0x43242EF6, 0xA51E03AA, 0x9CF2D0A4,
                0x83C061BA, 0x9BE96A4D, 0x8FE51550, 0xBA645BD6,
                0x2826A2F9, 0xA73A3AE1, 0x4BA99586, 0xEF5562E9,
                0xC72FEFD3, 0xF752F7DA, 0x3F046F69, 0x77FA0A59,
                0x80E4A915, 0x87B08601, 0x9B09E6AD, 0x3B3EE593,
                0xE990FD5A, 0x9E34D797, 0x2CF0B7D9, 0x022B8B51,
                0x96D5AC3A, 0x017DA67D, 0xD1CF3ED6, 0x7C7D2D28,
                0x1F9F25CF, 0xADF2B89B, 0x5AD6B472, 0x5A88F54C,
                0xE029AC71, 0xE019A5E6, 0x47B0ACFD, 0xED93FA9B,
                0xE8D3C48D, 0x283B57CC, 0xF8D56629, 0x79132E28,
                0x785F0191, 0xED756055, 0xF7960E44, 0xE3D35E8C,
                0x15056DD4, 0x88F46DBA, 0x03A16125, 0x0564F0BD,
                0xC3EB9E15, 0x3C9057A2, 0x97271AEC, 0xA93A072A,
                0x1B3F6D9B, 0x1E6321F5, 0xF59C66FB, 0x26DCF319,
                0x7533D928, 0xB155FDF5, 0x03563482, 0x8ABA3CBB,
                0x28517711, 0xC20AD9F8, 0xABCC5167, 0xCCAD925F,
                0x4DE81751, 0x3830DC8E, 0x379D5862, 0x9320F991,
                0xEA7A90C2, 0xFB3E7BCE, 0x5121CE64, 0x774FBE32,
                0xA8B6E37E, 0xC3293D46, 0x48DE5369, 0x6413E680,
                0xA2AE0810, 0xDD6DB224, 0x69852DFD, 0x09072166,
                0xB39A460A, 0x6445C0DD, 0x586CDECF, 0x1C20C8AE,
                0x5BBEF7DD, 0x1B588D40, 0xCCD2017F, 0x6BB4E3BB,
                0xDDA26A7E, 0x3A59FF45, 0x3E350A44, 0xBCB4CDD5,
                0x72EACEA8, 0xFA6484BB, 0x8D6612AE, 0xBF3C6F47,
                0xD29BE463, 0x542F5D9E, 0xAEC2771B, 0xF64E6370,
                0x740E0D8D, 0xE75B1357, 0xF8721671, 0xAF537D5D,
                0x4040CB08, 0x4EB4E2CC, 0x34D2466A, 0x0115AF84,
                0xE1B00428, 0x95983A1D, 0x06B89FB4, 0xCE6EA048,
                0x6F3F3B82, 0x3520AB82, 0x011A1D4B, 0x277227F8,
                0x611560B1, 0xE7933FDC, 0xBB3A792B, 0x344525BD,
                0xA08839E1, 0x51CE794B, 0x2F32C9B7, 0xA01FBAC9,
                0xE01CC87E, 0xBCC7D1F6, 0xCF0111C3, 0xA1E8AAC7,
                0x1A908749, 0xD44FBD9A, 0xD0DADECB, 0xD50ADA38,
                0x0339C32A, 0xC6913667, 0x8DF9317C, 0xE0B12B4F,
                0xF79E59B7, 0x43F5BB3A, 0xF2D519FF, 0x27D9459C,
                0xBF97222C, 0x15E6FC2A, 0x0F91FC71, 0x9B941525,
                0xFAE59361, 0xCEB69CEB, 0xC2A86459, 0x12BAA8D1,
                0xB6C1075E, 0xE3056A0C, 0x10D25065, 0xCB03A442,
                0xE0EC6E0E, 0x1698DB3B, 0x4C98A0BE, 0x3278E964,
                0x9F1F9532, 0xE0D392DF, 0xD3A0342B, 0x8971F21E,
                0x1B0A7441, 0x4BA3348C, 0xC5BE7120, 0xC37632D8,
                0xDF359F8D, 0x9B992F2E, 0xE60B6F47, 0x0FE3F11D,
                0xE54CDA54, 0x1EDAD891, 0xCE6279CF, 0xCD3E7E6F,
                0x1618B166, 0xFD2C1D05, 0x848FD2C5, 0xF6FB2299,
                0xF523F357, 0xA6327623, 0x93A83531, 0x56CCCD02,
                0xACF08162, 0x5A75EBB5, 0x6E163697, 0x88D273CC,
                0xDE966292, 0x81B949D0, 0x4C50901B, 0x71C65614,
                0xE6C6C7BD, 0x327A140A, 0x45E1D006, 0xC3F27B9A,
                0xC9AA53FD, 0x62A80F00, 0xBB25BFE2, 0x35BDD2F6,
                0x71126905, 0xB2040222, 0xB6CBCF7C, 0xCD769C2B,
                0x53113EC0, 0x1640E3D3, 0x38ABBD60, 0x2547ADF0,
                0xBA38209C, 0xF746CE76, 0x77AFA1C5, 0x20756060,
                0x85CBFE4E, 0x8AE88DD8, 0x7AAAF9B0, 0x4CF9AA7E,
                0x1948C25C, 0x02FB8A8C, 0x01C36AE4, 0xD6EBE1F9,
                0x90D4F869, 0xA65CDEA0, 0x3F09252D, 0xC208E69F,
                0xB74E6132, 0xCE77E25B, 0x578FDFE3, 0x3AC372E6
            ])
        )
 
        # Cycle through the p-boxes and round-robin XOR the
        # key with the p-boxes
        key_len = len(key)
        index = 0
        for i in xrange(len(self._p_boxes)):
            self._p_boxes[i] = self._p_boxes[i] ^ (
             (ord(key[index % key_len]) << 24) +
             (ord(key[(index + 1) % key_len]) << 16) +
             (ord(key[(index + 2) % key_len]) << 8) +
             (ord(key[(index + 3) % key_len]))
            )
            index += 4
 
        # For the chaining process
        l = r = 0
 
        # Begin chain replacing the p-boxes
        for i in xrange(0, len(self._p_boxes), 2):
            (l, r) = self.cipher(l, r, self.ENCRYPT)
            self._p_boxes[i] = l
            self._p_boxes[i + 1] = r
 
        # Chain replace the s-boxes
        for i in xrange(len(self._s_boxes)):
            for j in xrange(0, len(self._s_boxes[i]), 2):
                (l, r) = self.cipher(l, r, self.ENCRYPT)
                self._s_boxes[i][j] = l
                self._s_boxes[i][j + 1] = r
 
    def initCTR(self, iv=0):
        """
        Initializes CTR engine for encryption or decryption.
        """
        if not struct.calcsize("Q") == self._BLOCK_SIZE:
            raise ValueError("Struct-type 'Q' must have a length of %(target-len)i bytes, not %(q-len)i bytes; this module cannot be used on your platform" % {
             'target-len': self._BLOCK_SIZE,
             'q-len': struct.calcsize("Q"),
            })
 
        self._ctr_iv = iv
        self._calcCTRBuf()
 
    def cipher(self, xl, xr, direction):
        """
        Encrypts a 64-bit block of data where xl is the upper 32 bits and xr is
        the lower 32-bits.
 
        'direction' is the direction to apply the cipher, either ENCRYPT or
        DECRYPT class-constants.
 
        Returns a tuple of either encrypted or decrypted data of the left half
        and right half of the 64-bit block.
        """
        if direction == self.ENCRYPT:
            for i in self._p_boxes[:16]:
                xl = xl ^ i
                xr = self._round(xl) ^ xr
                (xl, xr) = (xr, xl)
            (xl, xr) = (xr, xl)
            xr = xr ^ self._p_boxes[16]
            xl = xl ^ self._p_boxes[17]
        else:
            for i in reversed(self._p_boxes[2:18]):
                xl = xl ^ i
                xr = self._round(xl) ^ xr
                (xl, xr) = (xr, xl)
            (xl, xr) = (xr, xl)
            xr = xr ^ self._p_boxes[1]
            xl = xl ^ self._p_boxes[0]
        return (xl, xr)
 
    def encrypt(self, data):
        """
        Encrypt an 8-byte (64-bit) block of text where 'data' is an 8 byte
        string.
 
        Returns an 8-byte encrypted string.
        """
        if not len(data) == 8:
            raise ValueError("Attempted to encrypt data of invalid block length: %(len)i" % {
             'len': len(data),
            })
 
        # Use big endianess since that's what everyone else uses
        xl = (ord(data[3])) | (ord(data[2]) << 8) | (ord(data[1]) << 16) | (ord(data[0]) << 24)
        xr = (ord(data[7])) | (ord(data[6]) << 8) | (ord(data[5]) << 16) | (ord(data[4]) << 24)
 
        (cl, cr) = self.cipher(xl, xr, self.ENCRYPT)
        chars = ''.join ([
         chr((cl >> 24) & 0xFF), chr((cl >> 16) & 0xFF), chr((cl >> 8) & 0xFF), chr(cl & 0xFF),
         chr((cr >> 24) & 0xFF), chr((cr >> 16) & 0xFF), chr((cr >> 8) & 0xFF), chr(cr & 0xFF)
        ])
        return chars
 
    def decrypt(self, data):
        """
        Decrypt an 8 byte (64-bit) encrypted block of text, where 'data' is the
        8-byte encrypted string.
 
        Returns an 8-byte string of plaintext.
        """
        if not len(data) == 8:
            raise ValueError("Attempted to encrypt data of invalid block length: %(len)i" % {
             'len': len(data),
            })
 
        # Use big endianess since that's what everyone else uses
        cl = (ord(data[3])) | (ord(data[2]) << 8) | (ord(data[1]) << 16) | (ord(data[0]) << 24)
        cr = (ord(data[7])) | (ord(data[6]) << 8) | (ord(data[5]) << 16) | (ord(data[4]) << 24)
 
        (xl, xr) = self.cipher (cl, cr, self.DECRYPT)
        return ''.join ([
         chr((xl >> 24) & 0xFF), chr((xl >> 16) & 0xFF), chr((xl >> 8) & 0xFF), chr(xl & 0xFF),
         chr((xr >> 24) & 0xFF), chr((xr >> 16) & 0xFF), chr((xr >> 8) & 0xFF), chr(xr & 0xFF)
        ])
 
    def encryptCTR(self, data):
        """
        Encrypts an arbitrary string and returns the encrypted string.
 
        This method can be called successively for multiple string blocks.
        """
        if not type(data) is str:
            raise TypeError("Only 8-bit strings are supported")
 
        return ''.join([chr(ord(ch) ^ self._nextCTRByte()) for ch in data])
 
    def decryptCTR(self, data):
        """
        Decrypts a string encrypted with encryptCTR() and returns the original
        string.
        """
        return self.encryptCTR(data)
 
    def _calcCTRBuf(self):
        """
        Calculates one block of CTR keystream.
        """
        self._ctr_cks = self.encrypt(struct.pack("Q", self._ctr_iv)) # keystream block
        self._ctr_iv += 1
        self._ctr_pos = 0
 
    def _nextCTRByte(self):
        """
        Returns one byte of CTR keystream.
        """
        b = ord(self._ctr_cks[self._ctr_pos])
        self._ctr_pos += 1
 
        if self._ctr_pos >= len(self._ctr_cks):
            self._calcCTRBuf()
        return b
 
    def _round(self, xl):
        """
        Performs an obscuring function on the 32-bit block of data, 'xl', which
        is the left half of the 64-bit block of data.
 
        Returns the 32-bit result as a long integer.
        """
        # Perform all ops as longs then and out the last 32-bits to
        # obtain the integer
        f = long(self._s_boxes[0][(xl & 0xFF000000) >> 24])
        f += long(self._s_boxes[1][(xl & 0x00FF0000) >> 16])
        f %= self._MODULUS
        f ^= long(self._s_boxes[2][(xl & 0x0000FF00) >> 8])
        f += long(self._s_boxes[3][(xl & 0x000000FF)])
        f %= self._MODULUS
        return f & 0xFFFFFFFF
 
# Sample usage
##############
if __name__ == '__main__':
    import time
 
    def _demo(heading, source, encrypted, decrypted):
        """demo method """
        print heading
        print "\tSource: %(source)s" % {
         'source': source,
        }
        print "\tEncrypted: %(encrypted)s" % {
         'encrypted': encrypted,
        }
        print "\tDecrypted: %(decrypted)s" % {
         'decrypted': decrypted,
        }
        print
 
    key = 'This is a test key'
    cipher = Blowfish(key)
 
    # Encryption processing
    (xl, xr) = (123456L, 654321L)
    (cl, cr) = cipher.cipher(xl, xr, cipher.ENCRYPT)
    (dl, dr) = cipher.cipher(cl, cr, cipher.DECRYPT)
    _demo("Testing encryption", (xl, xr), (cl, cr), (dl, dr))
 
    # Block processing
    text = 'testtest'
    crypted = cipher.encrypt(text)
    decrypted = cipher.decrypt(crypted)
    _demo("Testing block encrypt", text, repr(crypted), decrypted)
 
    # CTR ptocessing
    cipher.initCTR()
    text = "The quick brown fox jumps over the lazy dog"
    crypted = cipher.encryptCTR(text)
    cipher.initCTR()
    decrypted = cipher.decryptCTR(crypted)
    _demo("Testing CTR logic", text, repr(crypted), decrypted)
 
    # Test speed
    print "Testing speed"
    test_strings = [''.join(("The quick brown fox jumps over the lazy dog", str(i),)) for i in xrange(1000)]
    n = 0
    t1 = time.time()
    while True:
        for test_string in test_strings:
            cipher.encryptCTR(test_string)
        n += 1000
        t2 = time.time()
        if t2 - t1 >= 5.0:
            break
    print "%(count)i encryptions in %(time)0.1f seconds: %(throughput)0.1f enc/s" % {
     'count': n,
     'time': t2 - t1,
     'throughput': n / (t2 - t1),
    }

########NEW FILE########
__FILENAME__ = cmdline_utils
'''
    Gmvault: a tool to backup and restore your gmail account.
    Copyright (C) <2011-2013>  <guillaume Aubert (guillaume dot aubert at gmail do com)>

    This program is free software: you can redistribute it and/or modify
    it under the terms of the GNU Affero General Public License as
    published by the Free Software Foundation, either version 3 of the
    License, or (at your option) any later version.

    This program is distributed in the hope that it will be useful,
    but WITHOUT ANY WARRANTY; without even the implied warranty of
    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
    GNU Affero General Public License for more details.

    You should have received a copy of the GNU Affero General Public License
    along with this program.  If not, see <http://www.gnu.org/licenses/>.

'''

import argparse
import sys

import gmv.log_utils as log_utils

LOG = log_utils.LoggerFactory.get_logger('cmdline_utils')

class CmdLineParser(argparse.ArgumentParser): #pylint: disable=R0904
    """ 
        Added service to OptionParser.
       
        Comments regarding usability of the lib. 
        By default you want to print the default in the help if you had them so the default formatter should print them
        Also new lines are eaten in the epilogue strings. You would use an epilogue to show examples most of the time so you
        want to have the possiblity to go to a new line. There should be a way to format the epilogue differently from  the rest  

    """ 
    
    BOOL_TRUE  = ['yes', 'true', '1']
    BOOL_FALSE = ['no', 'false', '0']
    BOOL_VALS  = BOOL_TRUE + BOOL_FALSE
   
    def __init__(self, *args, **kwargs): 
        """ constructor """    
        argparse.ArgumentParser.__init__(self, *args, **kwargs) #pylint: disable=W0142
   
        # I like my help option message better than the default... 
        #self.remove_option('-h') 
        #self.add_option('-h', '--help', action='help', help='Show this message and exit.') 
           
        self.epilogue = None 
    
    @classmethod 
    def convert_to_boolean(cls, val):
        """
           Convert yes, True, true, YES to boolean True and
           no, False, false, NO to boolean NO
        """
        lower_val = val.lower()
        if lower_val in cls.BOOL_TRUE:
            return True
        elif lower_val in cls.BOOL_FALSE:
            return False
        else:
            raise Exception("val %s should be in %s to be convertible to a boolean." % (val, cls.BOOL_VALS))
   
    def print_help(self, out=sys.stderr): 
        """ 
          Print the help message, followed by the epilogue (if set), to the 
          specified output file. You can define an epilogue by setting the 
          ``epilogue`` field. 
           
          :param out: file desc where to write the usage message
         
        """ 
        super(CmdLineParser, self).print_help(out)
        if self.epilogue: 
            #print >> out, '\n%s' % textwrap.fill(self.epilogue, 100, replace_whitespace = False) 
            print >> out, '\n%s' % self.epilogue
            out.flush() 
   
    def show_usage(self, msg=None): 
        """
           Print usage message          
        """
        self.die_with_usage(msg) 
           
    def die_with_usage(self, msg=None, exit_code=2): 
        """ 
          Display a usage message and exit. 
   
          :Parameters: 
              msg : str 
                  If not set to ``None`` (the default), this message will be 
                  displayed before the usage message 
                   
              exit_code : int 
                  The process exit code. Defaults to 2. 
        """ 
        if msg != None: 
            print >> sys.stderr, msg 
        
        self.print_help(sys.stderr) 
        sys.exit(exit_code) 
   
    def error(self, msg): 
        """ 
          Overrides parent ``OptionParser`` class's ``error()`` method and 
          forces the full usage message on error. 
        """ 
        self.die_with_usage("%s: error: %s\n" % (self.prog, msg))
        
    def message(self, msg):
        """
           Print a message 
        """
        print("%s: %s\n" % (self.prog, msg))
        
        
SYNC_HELP_EPILOGUE = """Examples:

a) full synchronisation with email and password login

#> gmvault --email foo.bar@gmail.com --passwd vrysecrtpasswd 

b) full synchronisation for german users that have to use googlemail instead of gmail

#> gmvault --imap-server imap.googlemail.com --email foo.bar@gmail.com --passwd sosecrtpasswd

c) restrict synchronisation with an IMAP request

#> gmvault --imap-request 'Since 1-Nov-2011 Before 10-Nov-2011' --email foo.bar@gmail.com --passwd sosecrtpasswd 

"""

def test_command_parser():
    """
       Test the command parser
    """
    #parser = argparse.ArgumentParser()
    
    
    parser = CmdLineParser()
    
    subparsers = parser.add_subparsers(help='commands')
    
    # A sync command
    sync_parser = subparsers.add_parser('sync', formatter_class=argparse.ArgumentDefaultsHelpFormatter, \
                                        help='synchronize with given gmail account')
    #email argument can be optional so it should be an option
    sync_parser.add_argument('-l', '--email', action='store', dest='email', help='email to sync with')
    # sync typ
    sync_parser.add_argument('-t', '--type', action='store', default='full-sync', help='type of synchronisation')
    
    sync_parser.add_argument("-i", "--imap-server", metavar = "HOSTNAME", \
                          help="Gmail imap server hostname. (default: imap.gmail.com)",\
                          dest="host", default="imap.gmail.com")
        
    sync_parser.add_argument("-p", "--imap-port", metavar = "PORT", \
                          help="Gmail imap server port. (default: 993)",\
                          dest="port", default=993)
    
    sync_parser.set_defaults(verb='sync')

    
    sync_parser.epilogue = SYNC_HELP_EPILOGUE
    
    # A restore command
    restore_parser = subparsers.add_parser('restore', help='restore email to a given email account')
    restore_parser.add_argument('email', action='store', help='email to sync with')
    restore_parser.add_argument('--recursive', '-r', default=False, action='store_true',
                               help='Remove the contents of the directory, too',
                               )
    
    restore_parser.set_defaults(verb='restore')
    
    # A config command
    config_parser = subparsers.add_parser('config', help='add/delete/modify properties in configuration')
    config_parser.add_argument('dirname', action='store', help='New directory to create')
    config_parser.add_argument('--read-only', default=False, action='store_true',
                               help='Set permissions to prevent writing to the directory',
                               )
    
    config_parser.set_defaults(verb='config')
    
    
    
    
    # global help
    #print("================ Global Help (-h)================")
    sys.argv = ['gmvault.py']
    print(parser.parse_args())
    
    #print("================ Global Help (--help)================")
    #sys.argv = ['gmvault.py', '--help']
    #print(parser.parse_args())
    
    #print("================ Sync Help (--help)================")
    #sys.argv = ['gmvault.py', 'sync', '-h']
    #print(parser.parse_args())
    
    #sys.argv = ['gmvault.py', 'sync', 'guillaume.aubert@gmail.com', '--type', 'quick-sync']
    
    #print(parser.parse_args())
    #print("options = %s\n" % (options))
    #print("args = %s\n" % (args))
    

if __name__ == '__main__':
    
    test_command_parser()


    
    

########NEW FILE########
__FILENAME__ = collections_utils
'''
    Gmvault: a tool to backup and restore your gmail account.
    Copyright (C) <2011-2013>  <guillaume Aubert (guillaume dot aubert at gmail do com)>

    This program is free software: you can redistribute it and/or modify
    it under the terms of the GNU Affero General Public License as
    published by the Free Software Foundation, either version 3 of the
    License, or (at your option) any later version.

    This program is distributed in the hope that it will be useful,
    but WITHOUT ANY WARRANTY; without even the implied warranty of
    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
    GNU Affero General Public License for more details.

    You should have received a copy of the GNU Affero General Public License
    along with this program.  If not, see <http://www.gnu.org/licenses/>.

'''
import collections

## {{{ http://code.activestate.com/recipes/576669/ (r18)
class OrderedDict(dict, collections.MutableMapping):
    '''OrderedDict Class'''
    # Methods with direct access to underlying attributes

    def __init__(self, *args, **kwds):
        if len(args) > 1:
            raise TypeError('expected at 1 argument, got %d', len(args))
        if not hasattr(self, '_keys'):
            self._keys = []
        self.update(*args, **kwds)

    def clear(self):
        del self._keys[:]
        dict.clear(self)

    def __setitem__(self, key, value):
        if key not in self:
            self._keys.append(key)
        dict.__setitem__(self, key, value)

    def __delitem__(self, key):
        dict.__delitem__(self, key)
        self._keys.remove(key)

    def __iter__(self):
        return iter(self._keys)

    def __reversed__(self):
        return reversed(self._keys)

    def popitem(self):
        if not self:
            raise KeyError
        key = self._keys.pop()
        value = dict.pop(self, key)
        return key, value

    def __reduce__(self):
        items = [[k, self[k]] for k in self]
        inst_dict = vars(self).copy()
        inst_dict.pop('_keys', None)
        return (self.__class__, (items,), inst_dict)

    # Methods with indirect access via the above methods

    setdefault = collections.MutableMapping.setdefault
    update     = collections.MutableMapping.update
    pop        = collections.MutableMapping.pop
    keys       = collections.MutableMapping.keys
    values     = collections.MutableMapping.values
    items      = collections.MutableMapping.items

    def __repr__(self):
        pairs = ', '.join(map('%r: %r'.__mod__, self.items()))
        return '%s({%s})' % (self.__class__.__name__, pairs)

    def copy(self):
        return self.__class__(self)

    @classmethod
    def fromkeys(cls, iterable, value=None):
        '''fromkeys'''
        the_d = cls()
        for key in iterable:
            the_d[key] = value
        return the_d
## end of http://code.activestate.com/recipes/576669/ }}}
class Map(object):
    """ Map wraps a dictionary. It is essentially an abstract class from which
    specific multimaps are subclassed. """
    def __init__(self):
        self._dict = {}
        
    def __repr__(self):
        return "%s(%s)" % (self.__class__.__name__, repr(self._dict))
    
    __str__ = __repr__
        
    def __getitem__(self, key):
        return self._dict[key]
    
    def __setitem__(self, key, value):
        self._dict[key] = value
    
    def __delitem__(self, key):
        del self._dict[key]

    def __len__(self):
        return len(self._dict)
        
    def remove(self, key, value): #pylint: disable=W0613
        '''remove key from Map'''
        del self._dict[key]
    
    def keys(self):
        '''returns list of keys'''
        return self._dict.keys()
    
    def dict(self):
        """ Allows access to internal dictionary, if necessary. Caution: multimaps 
        will break if keys are not associated with proper container."""
        return self._dict

class ListMultimap(Map):
    """ ListMultimap is based on lists and allows multiple instances of same value. """
    def __init__(self):
        super(ListMultimap, self).__init__()
        self._dict = collections.defaultdict(list)
        
    def __setitem__(self, key, value):
        self._dict[key].append(value)

    def __len__(self):
        return len(self._dict)
    
    def remove(self, key, value):
        '''Remove key'''
        self._dict[key].remove(value)

class SetMultimap(Map):
    """ SetMultimap is based on sets and prevents multiple instances of same value. """
    def __init__(self):
        super(SetMultimap, self).__init__()
        self._dict = collections.defaultdict(set)
        
    def __setitem__(self, key, value):
        self._dict[key].add(value)

    def __len__(self):
        return len(self._dict)
    
    def remove(self, key, value):
        '''remove key'''
        self._dict[key].remove(value)

class DictMultimap(Map):
    """ DictMultimap is based on dicts and allows fast tests for membership. """
    def __init__(self):
        super(DictMultimap, self).__init__()
        self._dict = collections.defaultdict(dict)
        
    def __setitem__(self, key, value):
        self._dict[key][value] = True

    def __len__(self):
        return len(self._dict)
    
    def remove(self, key, value):
        """ remove key"""
        del self._dict[key][value]


########NEW FILE########
__FILENAME__ = conf_helper
'''
    Gmvault: a tool to backup and restore your gmail account.
    Copyright (C) <2011-2013>  <guillaume Aubert (guillaume dot aubert at gmail do com)>

    This program is free software: you can redistribute it and/or modify
    it under the terms of the GNU Affero General Public License as
    published by the Free Software Foundation, either version 3 of the
    License, or (at your option) any later version.

    This program is distributed in the hope that it will be useful,
    but WITHOUT ANY WARRANTY; without even the implied warranty of
    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
    GNU Affero General Public License for more details.

    You should have received a copy of the GNU Affero General Public License
    along with this program.  If not, see <http://www.gnu.org/licenses/>.

'''
import sys
import os
import re
import codecs

import gmv.conf.exceptions as exceptions
import gmv.conf.utils.struct_parser as struct_parser                                      

class ResourceError(Exception):
    """
        Base class for ressource exceptions 
    """

    def __init__(self, a_msg):
        
        super(ResourceError, self).__init__(a_msg)

class Resource(object):
    """
        Class read a ressource.
        It can be read first from the Command Line, then from the ENV as an env variable and finally from a conf file 
    """
    
    def __init__(self, a_cli_argument=None, a_env_variable=None, a_conf_property=None): 
        """ 
          Default Constructor.
          It is important to understand that there is precedence between the different ways to set the ressource:
          - get from the command line if defined otherwise get from the Env variable if defined otherwise get from the conf file otherwise error
       
           Args:
              a_cli_argument : The command line argument name
              a_env_variable : The env variable name used for this ressource
              a_conf_property: It should be a tuple containing two elements (group,property)
        """
      
        self._cli_arg   = a_cli_argument.lower() if a_cli_argument is not None else None
        self._env_var   = a_env_variable.upper() if a_env_variable is not None else None
      
        if a_conf_property is not None:
            (self._conf_group, self._conf_property) = a_conf_property
        else:
            self._conf_group    = None
            self._conf_property = None
      
    def set_cli_argument(self, a_cli_argument):
        """cli_argument setter"""
        self._cli_arg = a_cli_argument.lower()
        
    def set_env_variable(self, a_env_variable):
        """env_variable setter"""
        self._env_var = a_env_variable
    
    @classmethod
    def _get_srandardized_cli_argument(cls, a_tostrip):
        """
           remove -- or - from the command line argument and add a -- prefix to standardize the cli argument 
        """
        the_str = a_tostrip
        
        while the_str.startswith('-'):
            the_str = the_str[1:]
        
        return '--%s' % (the_str)
    
    def _get_value_from_command_line(self):
        """
          internal method for extracting the value from the command line.
          All command line agruments must be lower case (unix style).
          To Do support short and long cli args.
           
           Returns:
             the Value if defined otherwise None
        """
          
        # check precondition
        if self._cli_arg == None:
            return None
        

        the_s = Resource._get_srandardized_cli_argument(self._cli_arg)
    
        # look for cliArg in sys argv
        for arg in sys.argv:
            if arg.lower() == the_s:
                i = sys.argv.index(arg)
                #print "i = %d, val = %s\n"%(i,sys.argv[i])
                if len(sys.argv) <= i:
                    # No more thing to read in the command line so quit
                    print "Resource: Commandline argument %s has no value\n" % (self._cli_arg)
                    return None 
                else:
                    #print "i+1 = %d, val = %s\n"%(i+1,sys.argv[i+1])
                    return sys.argv[i+1]
            

    def _get_value_from_env(self):
        """
          internal method for extracting the value from the env.
          All support ENV Variables should be in uppercase.
           
           Returns:
             the Value if defined otherwise None
        """
      
        # precondition
        if self._env_var == None:
            return None
     
        return os.environ.get(self._env_var, None)
      
    def _get_from_conf(self):
        """
           Try to read the info from the Configuration if possible
        """
        if self._conf_group and self._conf_property:
            if Conf.can_be_instanciated():
                return Conf.get_instance().get(self._conf_group, self._conf_property)
        
        return None
          
        
    def get_value(self, a_raise_exception=True):
        """
           Return the value of the Resource as a string.
           - get from the command line if defined otherwise get from the Env variable if defined otherwise get from the conf file otherwise error
              
           Arguments:
              aRaiseException: flag indicating if an exception should be raise if value not found
           Returns:
              value of the Resource as a String
       
           Raises:
              exception CTBTOError if the aRaiseExceptionOnError flag is activated
        """
       
        # get a value using precedence rule 1) command-line, 2) ENV, 3) Conf
        val = self._get_value_from_command_line()
        if val is None:
            val = self._get_value_from_env()
            if val is None:
                val = self._get_from_conf()
                if (val is None) and a_raise_exception:
                    
                    the_str = "Cannot find "
                    add_nor = 0
                    
                    if self._cli_arg is not None:
                        the_str += "commandline argument %s" % (self._cli_arg)
                        add_nor += 1
                    
                    if self._env_var is not None:
                        
                        if add_nor > 0:
                            the_str += ", nor "
                    
                        the_str += "the Env Variable %s" % (self._env_var)
                        add_nor += 1
                    
                    if self._conf_group is not None:
                        if add_nor > 0:
                            the_str += ", nor "
                        
                        the_str += "the Conf Group:[%s] and Property=%s" % (self._conf_group, self._conf_property)
                        add_nor += 1
                        
                    if add_nor == 0:
                        the_str += " any defined commandline argument, nor any env variable or"\
                                   " Conf group and properties. They are all None, fatal error"
                    else:
                        the_str += ". One of them should be defined"
                    
                    raise ResourceError(the_str)
    
        return val
   
    def _get(self, conv):
        """
           Private _get method used to convert to the right expected type (int,float or boolean).
           Strongly inspired by ConfigParser.py
              
           Returns:
              value converted into the asked type
       
           Raises:
              exception ValueError if conversion issue
        """
        return conv(self.get_value())

    def get_value_as_int(self):
        """
           Return the value as an int
              
           Returns:
              value converted into the asked type
       
           Raises:
              exception ValueError if conversion issue
        """
        return self._get(int)

    def get_value_as_float(self):
        """
           Return the value as a float
              
           Returns:
              value converted into the asked type
       
           Raises:
              exception ValueError if conversion issue
        """
        return self._get(float)

    _boolean_states = {'1': True, 'yes': True, 'true': True, 'on': True,
                       '0': False, 'no': False, 'false': False, 'off': False}

    def get_value_as_boolean(self):
        """
           Return the value as a boolean
              
           Returns:
              value converted into the asked type
       
           Raises:
              exception ValueError if conversion issue
        """
        val = self.get_value()
        if val.lower() not in self._boolean_states:
            raise ValueError, 'Not a boolean: %s' % val
        return self._boolean_states[val.lower()]

class MockConf(object):
    """
       MockConf Object that returns only defaults
    """
    def __init__(self, use_resource=True):
        """
           default constructor
        """
        pass
    
    @classmethod
    def get(cls, section, option, default=None, fail_if_missing=False): #pylint: disable=W0613
        """ get one option from a section.
        """
        return default
    
    @classmethod
    def print_content(cls, substitute_values = True):#pylint: disable=W0613
        """ print all the options variables substituted.
        
            :param a_substitue_vals: bool for substituting values
            :returns: the string containing all sections and variables
        """
        raise exceptions.Error("Not implemented in MockupConf")            

    @classmethod
    def items(cls, section):#pylint: disable=W0613
        """ return all items from a section. Items is a list of tuples (option,value)
            
            Args:
               section. The section where to find the option
               
            Returns: a list of tuples (option,value)
        
            Raises:
               exception NoSectionError if the section cannot be found
        """
        raise exceptions.Error("Not implemented in MockupConf") 
  
    @classmethod
    def getint(cls, section, option, default=0, fail_if_missing=False):#pylint: disable=W0613
        """Return the int value of the option.
        Default value is 0, None value can't be used as default value"""
        return default

    @classmethod
    def getfloat(cls, section, option, default=0, fail_if_missing=False):#pylint: disable=W0613
        """Return the float value of the option. 
        Default value is 0, None value can't be used as default value"""
        return default

    @classmethod
    def getboolean(cls, section, option, default=False, fail_if_missing=False):#pylint: disable=W0613
        """get bool value """
        return default
    
    @classmethod
    def get_list(cls, section, option, default=None, fail_if_missing=False):#pylint: disable=W0613
        """ get a list of string, int  """
        return default
    
    @classmethod
    def getlist(cls, section, option, default=None, fail_if_missing=False):#pylint: disable=W0613
        """ Deprecated, use get_list instead"""
        return cls.get_list(section, option, default, fail_if_missing)

    @classmethod
    def getdict(cls, section, option, default=None, fail_if_missing=False):#pylint: disable=W0613
        """ Deprecated, use get_dict instead"""
        return cls.get_dict(section, option, default, fail_if_missing)
        
    
    @classmethod
    def get_dict(cls, section, option, default=None, fail_if_missing=False):#pylint: disable=W0613
        """ get a dict """
        return default
 
class Conf(object):
    """ Configuration Object with a several features:
    
         * get configuration info in different types
         * support for import
         * support for variables in configuration file
         * support for default values in all accessors
         * integrated with the resources object offering to get the configuration from an env var, a commandline option or the conf
         * to be done : support for blocs, list comprehension and dict comprehension, json 
         * to be done : define resources in the conf using the [Resource] group with A= { ENV:TESTVAR, CLI:--testvar, VAL:1.234 }
    
    """
    # command line and env resource stuff
    CLINAME = "--conf_file"
    ENVNAME = "CONF_FILE" 
    
    #class member
    _instance = None
    
    _CLIGROUP = "CLI"
    _ENVGROUP = "ENV"
    _MAX_INCLUDE_DEPTH = 10
    
    @classmethod
    def get_instance(cls):
        """ singleton method """
        if cls._instance == None:
            cls._instance = Conf()
        return cls._instance
    
    @classmethod
    def can_be_instanciated(cls):
        """Class method used by the Resource to check that the Conf can be instantiated. 
        
        These two objects have a special contract as they are strongly coupled. 
        A Resource can use the Conf to check for a Resource and the Conf uses a Resource to read Conf filepath.
        
        :returns: True if the Conf file has got a file.
           
        :except Error: Base Conf Error
        
        """
        #No conf info passed to the resource so the Resource will not look into the conf (to avoid recursive search)
        the_res = Resource(cls.CLINAME, cls.ENVNAME)
        
        filepath = the_res.get_value(a_raise_exception=False)
        
        if (filepath is not None) and os.path.exists(filepath):
            return True
        
        return False
            
    
    def __init__(self, use_resource=True):
        """
           Constructor
        """
        
        # create resource for the conf file
        self._conf_resource = Resource(Conf.CLINAME, Conf.ENVNAME)
        
        # list of sections
        self._sections = {}
        
        self._configuration_file_path = None
        
        # create config object 
        if use_resource:       
            self._load_config()
        

   
    def _load_config(self, a_file = None):
        """ _load the configuration file """
        try:  
            # get it from a Resource if not files are passed
            if a_file is None:
                a_file = self._conf_resource.get_value() 
             
            if a_file is None:
                raise exceptions.Error("Conf. Error, need a configuration file path")
            
            #f_desc = open(a_file, 'r') 
            f_desc = codecs.open(a_file, 'r', 'utf-8') 
             
                
            self._read(f_desc, a_file)
            
            # memorize conf file path
            self._configuration_file_path = a_file
            
        except Exception, exce:
            print "Can't read the config file %s" % (a_file)
            print "Current executing from dir = %s\n" % (os.getcwd())
            raise exce
            
    
    def get_conf_file_path(self):
        """return conf_file_path"""
        return self._configuration_file_path if self._configuration_file_path != None else "unknown"
       
    def sections(self):
        """Return a list of section names, excluding [DEFAULT]"""
        # self._sections will never have [DEFAULT] in it
        return self._sections.keys()
    
    @classmethod
    def _get_defaults(cls, section, option, default, fail_if_missing):
        """ To manage defaults.
            Args:
               default. The default value to return if fail_if_missing is False
               fail_if_missing. Throw an exception when the option is not found and fail_if_missing is true
               
            Returns: default if fail_if_missing is False
        
            Raises:
               exception NoOptionError if fail_if_missing is True
        """
        if fail_if_missing:
            raise exceptions.Error(2, "No option %s in section %s" %(option, section))
        else:
            if default is not None:
                return str(default)
            else:
                return None
    
    def get(self, section, option, default=None, fail_if_missing=False):
        """ get one option from a section.
        
            return the default if it is not found and if fail_if_missing is False, otherwise return NoOptionError
          
            :param section: Section where to find the option
            :type  section: str
            :param option:  Option to get
            :param default: Default value to return if fail_if_missing is False
            :param fail_if_missing: Will throw an exception when the option is not found and fail_if_missing is true
               
            :returns: the option as a string
            
            :except NoOptionError: Raised only when fail_is_missing set to True
        
        """
        # all options are kept in lowercase
        opt = self.optionxform(option)
        
        if section not in self._sections:
            #check if it is a ENV section
            dummy = None
            if section == Conf._ENVGROUP:
                the_r = Resource(a_cli_argument=None, a_env_variable=opt)
                dummy = the_r.get_value()
            elif section == Conf._CLIGROUP:
                the_r = Resource(a_cli_argument=opt, a_env_variable=None)
                dummy = the_r.get_value()
            #return default if dummy is None otherwise return dummy
            return ((self._get_defaults(section, opt, default, fail_if_missing)) if dummy == None else dummy)
        elif opt in self._sections[section]:
            return self._replace_vars(self._sections[section][opt], "%s[%s]" % (section, option), - 1)
        else:
            return self._get_defaults(section, opt, default, fail_if_missing)
        
    
    def print_content(self, substitute_values = True):
        """ print all the options variables substituted.
        
            :param a_substitue_vals: bool for substituting values
            :returns: the string containing all sections and variables
        """
        
        result_str = ""
        
        for section_name in self._sections:
            result_str += "[%s]\n" % (section_name)
            section = self._sections[section_name]
            for option in section:
                if option != '__name__':
                    if substitute_values:
                        result_str += "%s = %s\n" % (option, self.get(section_name, option))
                    else:
                        result_str += "%s = %s\n" % (option, self._sections[section_name][option])
            
            result_str += "\n"
        
        return result_str
            

    def items(self, section):
        """ return all items from a section. Items is a list of tuples (option,value)
            
            Args:
               section. The section where to find the option
               
            Returns: a list of tuples (option,value)
        
            Raises:
               exception NoSectionError if the section cannot be found
        """
        try:
            all_sec = self._sections[section]
            # make a copy
            a_copy = all_sec.copy()
            # remove __name__ from d
            if "__name__" in a_copy:
                del a_copy["__name__"]
                
            return a_copy.items()
        
        except KeyError:
            raise exceptions.NoSectionError(section)

    def has_option(self, section, option):
        """Check for the existence of a given option in a given section."""
        has_option = False
        if self.has_section(section):
            option = self.optionxform(option)
            has_option = (option in self._sections[section])
        return has_option
    
    def has_section(self, section):
        """Check for the existence of a given section in the configuration."""
        has_section = False
        if section in self._sections:
            has_section = True
        return has_section
        
    @classmethod
    def _get_closing_bracket_index(cls, index, the_str, location, lineno):
        """ private method used by _replace_vars to count the closing brackets.
            
            Args:
               index. The index from where to look for a closing bracket
               s. The string to parse
               group. group and options that are substituted. Mainly used to create a nice exception message
               option. option that is substituted. Mainly used to create a nice exception message
               
            Returns: the index of the found closing bracket
        
            Raises:
               exception NoSectionError if the section cannot be found
        """
        
        tolook = the_str[index + 2:]
   
        opening_brack = 1
        closing_brack_index = index + 2
    
        i = 0
        for _ch in tolook:
            if _ch == ')':
                if opening_brack == 1:
                    return closing_brack_index
                else:
                    opening_brack -= 1
     
            elif _ch == '(':
                if tolook[i - 1] == '%':
                    opening_brack += 1
        
            # inc index
            closing_brack_index += 1
            i += 1
    
        raise exceptions.SubstitutionError(lineno, location, "Missing a closing bracket in %s" % (tolook))

    # very permissive regex
    _SUBSGROUPRE = re.compile(r"%\((?P<group>\w*)\[(?P<option>(.*))\]\)")
    
    def _replace_vars(self, a_str, location, lineno= - 1):
        """ private replacing all variables. A variable will be in the from of %(group[option]).
            Multiple variables are supported, ex /foo/%(group1[opt1])/%(group2[opt2])/bar
            Nested variables are also supported, ex /foo/%(group[%(group1[opt1]].
            Note that the group part cannot be substituted, only the option can. This is because of the Regular Expression _SUBSGROUPRE that accepts only words as values.
            
            Args:
               index. The index from where to look for a closing bracket
               s. The string to parse
               
            Returns: the final string with the replacements
        
            Raises:
               exception NoSectionError if the section cannot be found
        """
 
        toparse = a_str
    
        index = toparse.find("%(")
    
        # if found opening %( look for end bracket)
        if index >= 0:
            # look for closing brackets while counting openings one
            closing_brack_index = self._get_closing_bracket_index(index, a_str, location, lineno)
        
            #print "closing bracket %d"%(closing_brack_index)
            var   = toparse[index:closing_brack_index + 1]
            
            dummy = None
            
            matched = self._SUBSGROUPRE.match(var)
        
            if matched == None:
                raise exceptions.SubstitutionError(lineno, location, \
                                                   "Cannot match a group[option] in %s "\
                                                   "but found an opening bracket (. Malformated expression " \
                                                   % (var))
            else:
            
                # recursive calls
                group = self._replace_vars(matched.group('group'), location, - 1)
                option = self._replace_vars(matched.group('option'), location, - 1)
            
                try:
                    # if it is in ENVGROUP then check ENV variables with a Resource object
                    # if it is in CLIGROUP then check CLI argument with a Resource object
                    # otherwise check in standard groups
                    if group == Conf._ENVGROUP:
                        res = Resource(a_cli_argument=None, a_env_variable=option)
                        dummy = res.get_value()
                    elif group == Conf._CLIGROUP:
                        res = Resource(a_cli_argument=option, a_env_variable=None)
                        dummy = res.get_value()
                    else:
                        dummy = self._sections[group][self.optionxform(option)]
                except KeyError, _: #IGNORE:W0612
                    raise exceptions.SubstitutionError(lineno, location, "Property %s[%s] "\
                                                       "doesn't exist in this configuration file \n" \
                                                       % (group, option))
            
            toparse = toparse.replace(var, dummy)
            
            return self._replace_vars(toparse, location, - 1)    
        else:   
            return toparse 


    def _get(self, section, conv, option, default, fail_if_missing):
        """ Internal getter """
        return conv(self.get(section, option, default, fail_if_missing))

    def getint(self, section, option, default=0, fail_if_missing=False):
        """Return the int value of the option.
        Default value is 0, None value can't be used as default value"""
        return self._get(section, int, option, default, fail_if_missing)
    
    def get_int(self, section, option, default=0, fail_if_missing=False):
        """Return the int value of the option.
        Default value is 0, None value can't be used as default value"""
        return self._get(section, int, option, default, fail_if_missing)

    def getfloat(self, section, option, default=0, fail_if_missing=False):
        """Return the float value of the option. 
        Default value is 0, None value can't be used as default value"""
        return self._get(section, float, option, default, fail_if_missing)
    
    def get_float(self, section, option, default=0, fail_if_missing=False):
        """Return the float value of the option. 
        Default value is 0, None value can't be used as default value"""
        return self._get(section, float, option, default, fail_if_missing)

    _boolean_states = {'1': True, 'yes': True, 'true': True, 'on': True,
                       '0': False, 'no': False, 'false': False, 'off': False}

    def getboolean(self, section, option, default=False, fail_if_missing=False):
        """getboolean value""" 
        val = self.get(section, option, default, fail_if_missing)
        if val.lower() not in self._boolean_states:
            raise ValueError, 'Not a boolean: %s' % val
        return self._boolean_states[val.lower()]
    
    def get_boolean(self, section, option, default=False, fail_if_missing=False):
        """get_boolean value"""
        val = self.get(section, option, default, fail_if_missing)
        if val.lower() not in self._boolean_states:
            raise ValueError, 'Not a boolean: %s' % val
        return self._boolean_states[val.lower()]
    
    def get_list(self, section, option, default=None, fail_if_missing=False):
        """ get a list of string, int  """
        
        val = self.get(section, option, default, fail_if_missing)
        
        # parse it and return an error if invalid
        try:
            compiler = struct_parser.Compiler()
            return compiler.compile_list(val)
        except struct_parser.CompilerError, err: 
            raise exceptions.Error(err.message)
    
    def getlist(self, section, option, default=None, fail_if_missing=False):
        """ Deprecated, use get_list instead"""
        return self.get_list(section, option, default, fail_if_missing)

    def getdict(self, section, option, default=None, fail_if_missing=False):
        """ Deprecated, use get_dict instead"""
        return self.get_dict(section, option, default, fail_if_missing)
        
    
    def get_dict(self, section, option, default=None, fail_if_missing=False):
        """ get a dict """
        
        val = self.get(section, option, default, fail_if_missing)
        
        # parse it and return an error if invalid
        try:
            compiler = struct_parser.Compiler()
            return compiler.compile_dict(val)
        except struct_parser.CompilerError, err: 
            raise exceptions.Error(err.message)
        
    @classmethod
    def optionxform(cls, optionstr):
        """optionxform"""
        return optionstr.lower()
    
    #
    # Regular expressions for parsing section headers and options.
    #
    SECTCRE = re.compile(
        r'\['                                 # [
        r'(?P<header>[^]]+)'                  # very permissive!
        r'\]'                                 # ]
        )
    OPTCRE = re.compile(
        r'(?P<option>[^:=\s][^:=]*)'          # very permissive!
        r'\s*(?P<vi>[:=])\s*'                 # any number of space/tab,
                                              # followed by separator
                                              # (either : or =), followed
                                              # by any # space/tab
        r'(?P<value>.*)$'                     # everything up to eol
        )
            
    def _read_include(self, lineno, line, origin, depth):
        """_read_include"""      
        # Error if depth is MAX_INCLUDE_DEPTH 
        if depth >= Conf._MAX_INCLUDE_DEPTH:
            raise exceptions.IncludeError("Error. Cannot do more than %d nested includes."\
                                          " It is probably a mistake as you might have created a loop of includes" \
                                          % (Conf._MAX_INCLUDE_DEPTH))
        
        # remove %include from the path and we should have a path
        i = line.find('%include')
        
        #check if there is a < for including config files from a different format
        #position after include
        i = i + 8
        
        # include file with a specific reading module
        if line[i] == '<':
            dummy = line[i+1:].strip()
            f_i = dummy.find('>')
            if f_i == -1:
                raise exceptions.IncludeError("Error. > is missing in the include line no %s: %s."\
                                              " It should be %%include<mode:group_name> path" \
                                                   % (line, lineno), origin )
            else:
                group_name = None
                the_format     = dummy[:f_i].strip()
                
                the_list = the_format.split(':')
                if len(the_list) != 2 :
                    raise exceptions.IncludeError("Error. The mode and the group_name are not in the include line no %s: %s."\
                                                       " It should be %%include<mode:group_name> path" \
                                                       % (line, lineno), origin )
                else:
                    the_format, group_name = the_list
                    #strip the group name
                    group_name = group_name.strip()
                    
                path = dummy[f_i+1:].strip()
                
                # replace variables if there are any
                path = self._replace_vars(path, line, lineno)
                
                raise exceptions.IncludeError("External Module reading not enabled in this ConfHelper")
                #self._read_with_module(group_name, format, path, origin)
        else:
            # normal include   
            path = line[i:].strip() 
            
            # replace variables if there are any
            path = self._replace_vars(path, line, lineno)
            
            # check if file exits
            if not os.path.exists(path):
                raise exceptions.IncludeError("the config file to include %s does not exits" % (path), origin)
            else:
                # add include file and populate the section hash
                self._read(codecs.open(path, 'r', 'utf-8'), path, depth + 1)
                #self._read(open(path, 'r'), path, depth + 1)

    def _read(self, fpointer, fpname, depth=0): #pylint: disable=R0912
        """Parse a sectioned setup file.

        The sections in setup file contains a title line at the top,
        indicated by a name in square brackets (`[]'), plus key/value
        options lines, indicated by `name: value' format lines.
        Continuations are represented by an embedded newline then
        leading whitespace.  Blank lines, lines beginning with a '#',
        and just about everything else are ignored.
        Depth for avoiding looping in the includes
        """
        cursect = None                            # None, or a dictionary
        optname = None
        lineno = 0
        err = None                                  # None, or an exception
        while True:
            line = fpointer.readline()
            if not line:
                break
            lineno = lineno + 1
            # include in this form %include
            if line.startswith('%include'):
                self._read_include(lineno, line, fpname, depth)
                continue
            # comment or blank line?
            if line.strip() == '' or line[0] in '#;':
                continue
            if line.split(None, 1)[0].lower() == 'rem' and line[0] in "rR":
                # no leading whitespace
                continue
            # continuation line?
            if line[0].isspace() and cursect is not None and optname:
                value = line.strip()
                if value:
                    cursect[optname] = "%s\n%s" % (cursect[optname], value)
            # a section header or option header?
            else:
                # is it a section header?
                matched = self.SECTCRE.match(line)
                if matched:
                    sectname = matched.group('header')
                    if sectname in self._sections:
                        cursect = self._sections[sectname]
                    else:
                        cursect = {'__name__': sectname}
                        self._sections[sectname] = cursect
                    # So sections can't start with a continuation line
                    optname = None
                # no section header in the file?
                elif cursect is None:
                    raise exceptions.MissingSectionHeaderError(fpname, lineno, line)
                # an option line?
                else:
                    matched = self.OPTCRE.match(line)
                    if matched:
                        optname, vio, optval = matched.group('option', 'vi', 'value')
                        if vio in ('=', ':') and ';' in optval:
                            # ';' is a comment delimiter only if it follows
                            # a spacing character
                            pos = optval.find(';')
                            if pos != - 1 and optval[pos - 1].isspace():
                                optval = optval[:pos]
                        optval = optval.strip()
                        # allow empty values
                        if optval == '""':
                            optval = ''
                        optname = self.optionxform(optname.rstrip())
                        cursect[optname] = optval
                    else:
                        # a non-fatal parsing error occurred.  set up the
                        # exception but keep going. the exception will be
                        # raised at the end of the file and will contain a
                        # list of all bogus lines
                        if not err:
                            err = exceptions.ParsingError(fpname)
                        err.append(lineno, repr(line))
        # if any parsing errors occurred, raise an exception
        if err:
            raise err.get_error()

########NEW FILE########
__FILENAME__ = conf_tests
# -*- coding: utf-8 -*-
'''
    Gmvault: a tool to backup and restore your gmail account.
    Copyright (C) <2011-2013>  <guillaume Aubert (guillaume dot aubert at gmail do com)>

    This program is free software: you can redistribute it and/or modify
    it under the terms of the GNU Affero General Public License as
    published by the Free Software Foundation, either version 3 of the
    License, or (at your option) any later version.

    This program is distributed in the hope that it will be useful,
    but WITHOUT ANY WARRANTY; without even the implied warranty of
    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
    GNU Affero General Public License for more details.

    You should have received a copy of the GNU Affero General Public License
    along with this program.  If not, see <http://www.gnu.org/licenses/>.

'''

# unit tests part
import unittest
import sys
import os
import codecs
import gmv.conf.conf_helper


class TestConf(unittest.TestCase): #pylint: disable=R0904
    """
       Test Class for the Conf Object
    """  
    @classmethod
    def _get_tests_dir_path(cls):
        """ get the org.ctbto.conf.tests path depending on where it is defined """
        
        fmod_path = gmv.conf.__path__
        
        test_dir = "%s/tests" % fmod_path[0]
        
        return test_dir
    
    def setUp(self): #pylint: disable=C0103
         
        # necessary for the include with the VAR ENV substitution
        os.environ["DIRCONFENV"] = TestConf._get_tests_dir_path()
         
        self.conf = gmv.conf.conf_helper.Conf(use_resource=False)
    
        #the_fp = open('%s/%s' % (TestConf._get_tests_dir_path(), "test.config"))
        the_fp = codecs.open('%s/%s' % (TestConf._get_tests_dir_path(), "test.config"), 'r', 'utf-8')
    
        self.conf._read(the_fp,"the file") #pylint: disable=W0212

    def tearDown(self): #pylint: disable=C0103

        if os.path.exists('/tmp/fake_conf.config'):
            os.remove('/tmp/fake_conf.config')
 
    def test_empty(self):
        """
          Do nothing
        """
        pass
        
    def test_get_objects(self):
        """testGetObjects: test getter from all types """
        # get simple string
        astring = self.conf.get("GroupTest1", "astring")
        
        self.assertEqual(astring,"oracle.jdbc.driver.OracleDriver")
        
        # get an int
        aint = self.conf.getint("GroupTest1", "aint")
        
        self.assertEqual(aint, 10)
        
        # get floatcompile the statements
        afloat = self.conf.getfloat("GroupTest1", "afloat")
        
        self.assertEqual(afloat, 5.24)
        
        # get different booleans form
        abool1 = self.conf.getboolean("GroupTest1", "abool1")
        
        self.assertEqual(abool1, True)
        
        abool2 = self.conf.getboolean("GroupTest1", "abool2")
        
        self.assertEqual(abool2, False)
        
        abool3 = self.conf.getboolean("GroupTest1", "abool3")
        
        self.assertEqual(abool3, True)
        
        abool4 = self.conf.getboolean("GroupTest1", "abool4")
        
        self.assertEqual(abool4 , False)
        
    def test_get_defaults(self):
        """testGetDefaults: test defaults values """
        
        # get all defaults
        astring = self.conf.get("GroupTest", "astring", "astring")
        
        self.assertEqual(astring, "astring")
        
        # get an default for int
        aint = self.conf.getint("GroupTest", "aint", 2)
        
        self.assertEqual(aint, 2)
        
        # get float
        afloat = self.conf.getfloat("GroupTest", "afloat", 10.541)
        
        self.assertEqual(afloat, 10.541)
        
        abool1 = self.conf.getboolean("GroupTest", "abool1", True)
        
        self.assertEqual(abool1, True)
        
        abool2 = self.conf.getboolean("GroupTest", "abool2", False)
        
        self.assertEqual(abool2, False)
        
        # existing group no option
        abool5 = self.conf.getboolean("GroupTest1", "abool32", False)
        
        self.assertEqual(abool5, False)
        
    def test_var_substitutions(self):
        """testVarSubstitutions: test variables substitutions"""
        
        # simple substitution
        apath = self.conf.get("GroupTestVars", "path")
        
        self.assertEqual(apath,"/foo/bar//tmp/foo/bar/bar/foo")
        
        # multiple substitution
        apath = self.conf.get("GroupTestVars", "path1")
        
        self.assertEqual(apath,"/foo//tmp/foo/bar//foo/bar//tmp/foo/bar/bar/foo/bar")
        
        # nested substitution
        nested = self.conf.get("GroupTestVars", "nested")
        
        self.assertEqual(nested, "this is done")  
        
    def test_include(self):
        """testInclude: test includes """
        val = self.conf.get("IncludedGroup", "hello")
        
        self.assertEqual(val, 'foo')
        
    @classmethod
    def _create_fake_conf_file_in_tmp(cls):
        """Create a fake conf file in tmp"""
        the_f = open('/tmp/fake_conf.config', 'w')
        
        the_f.write('\n[MainDatabaseAccess]\n')
        the_f.write('driverClassName=oracle.jdbc.driver.OracleDriver')
        the_f.flush()
        the_f.close()
    
    def ztest_use_conf_ENVNAME_resource(self): #pylint: disable=C0103
        """testUseConfENVNAMEResource: Use default resource ENVNAME to locate conf file"""
        self._create_fake_conf_file_in_tmp()

        # need to setup the ENV containing the the path to the conf file:
        os.environ[gmv.conf.conf_helper.Conf.ENVNAME] = "/tmp/fake_conf.config"
   
        self.conf = gmv.conf.conf_helper.Conf.get_instance()
        
        the_s = self.conf.get("MainDatabaseAccess", "driverClassName")
        
        self.assertEqual(the_s, 'oracle.jdbc.driver.OracleDriver')
    
    def test_read_from_CLI(self): #pylint: disable=C0103
        """testReadFromCLI: do substitutions from command line resources"""
        #set environment
        os.environ["TESTENV"] = "/tmp/foo/foo.bar"
        
        val = self.conf.get("GroupTest1", "fromenv")
   
        self.assertEqual(val, '/mydir//tmp/foo/foo.bar')
        
        #set cli arg
        sys.argv.append("--LongName")
        sys.argv.append("My Cli Value")
        
        val = self.conf.get("GroupTest1", "fromcli1")
   
        self.assertEqual(val, 'My Cli Value is embedded')
        
        #check with a more natural cli value
        val = self.conf.get("GroupTest1", "fromcli2")
   
        self.assertEqual(val, 'My Cli Value is embedded 2')
    
    def test_read_from_ENV(self): #pylint: disable=C0103
        """testReadFromENV: do substitutions from ENV resources"""
        #set environment
        os.environ["TESTENV"] = "/tmp/foo/foo.bar"
        
        val = self.conf.get("ENV", "TESTENV")
        
        self.assertEqual(val, "/tmp/foo/foo.bar")
        
        #set cli arg
        sys.argv.append("--LongName")
        sys.argv.append("My Cli Value")
        
        val = self.conf.get("CLI", "LongName")
        
        self.assertEqual(val, "My Cli Value")
        
        # get a float from env
        os.environ["TESTENV"] = "1.05"
        
        val = self.conf.getfloat("ENV", "TESTENV")
        
        self.assertEqual(val+1, 2.05) 
    
    def test_print_content(self):
        """ test print content """
        
        #set environment
        os.environ["TESTENV"] = "/tmp/foo/foo.bar"
        
        #set cli arg
        sys.argv.append("--LongName")
        sys.argv.append("My Cli Value")
        
        substitute_values = True
        
        result = self.conf.print_content( substitute_values )
        
        self.assertNotEqual(result, '')
        
    def test_value_as_List(self): #pylint: disable=C0103
        """ Value as List """
        
        the_list = self.conf.getlist('GroupTestValueStruct', 'list')
        
        self.assertEqual(the_list, ['a', 1, 3])
    
    def test_value_as_unicodeList(self): #pylint: disable=C0103
        """ Value as List """
        
        the_list = self.conf.getlist('GroupTestValueStruct', 'unicode_list')
        
        self.assertEqual(the_list, [ u'[Gmail]/Чаты', 'z' , 1 ])
    
    def test_value_as_dict(self):
        """Dict as Value """
        
        the_dict = self.conf.get_dict('GroupTestValueStruct', 'dict')
        
        self.assertEqual(the_dict, {'a': 2, 'b': 3})
    
    def test_complex_dict(self):
        """ complex dict """
        the_dict = self.conf.get_dict('GroupTestValueStruct', 'complex_dict')
        
        self.assertEqual(the_dict, {'a': 2, 'c': {'a': 1, 'c': [1, 2, 3], 'b': [1, 2, 3, 4, 5, 6, 7]}, 'b': 3})
    
    def test_dict_error(self):
        """ error with a dict """
        
        try:
            self.conf.get_dict('GroupTestValueStruct', 'dict_error')
        except Exception, err:
            self.assertEquals(err.message, "Expression \"{1:2,'v b': a\" cannot be converted as a dict.")
            return
        
        self.fail('Should never reach that point')
            
    def test_list_error(self):
        """ error with a list """
        
        try:
            the_list = self.conf.get_list('GroupTestValueStruct', 'list_error')
            print('the_list = %s\n' % (the_list))
        except Exception, err:
            self.assertEquals(err.message, 'Unsupported token (type: @, value : OP) (line=1,col=3).')
            return
         
        self.fail('Should never reach that point')
        
class TestResource(unittest.TestCase): #pylint: disable=R0904
    """
       Test Class for the Resource object
    """   
    def test_resource_simple_cli(self):
        """testResourceSimpleCli: read resource from CLI"""
        # set command line
        sys.argv.append("--LongName")
        sys.argv.append("My Cli Value")
        
        resource = gmv.conf.conf_helper.Resource(a_cli_argument = "--LongName", a_env_variable = None) 
        
        self.assertEqual("My Cli Value", resource.get_value())
        
        # look for LongName without --. It should be formalized by the Resource object
        resource = gmv.conf.conf_helper.Resource(a_cli_argument = "LongName", a_env_variable = None) 
        
        self.assertEqual("My Cli Value", resource.get_value())
    
    def test_resource_from_env(self): 
        """testResourceFromENV: read resource from ENV"""   
        #ENV 
        os.environ["MYENVVAR"] = "My ENV Value"
  
        resource = gmv.conf.conf_helper.Resource(a_cli_argument=None, a_env_variable="MYENVVAR")
        
        self.assertEqual("My ENV Value", resource.get_value())
        
    def ztest_resource_priority_rules(self):
        """testResourcePriorityRules: test priority rules"""   
        resource = gmv.conf.conf_helper.Resource(a_cli_argument="--LongName", a_env_variable="MYENVVAR")
  
        self.assertEqual("My Cli Value", resource.get_value())
  
    def test_resource_get_different_types(self): #pylint: disable=C0103
        """testResourceGetDifferentTypes: return resource in different types"""
        
        os.environ["MYENVVAR"] = "yes"
        resource = gmv.conf.conf_helper.Resource(a_cli_argument=None, a_env_variable="MYENVVAR")
        
        self.assertEqual(resource.get_value_as_boolean(), True)
        
        os.environ["MYENVVAR"] = "4"
  
        resource = gmv.conf.conf_helper.Resource(a_cli_argument=None, a_env_variable="MYENVVAR")
  
        self.assertEqual(resource.get_value_as_int()+1, 5)
        
        os.environ["MYENVVAR"] = "4.345"
  
        resource = gmv.conf.conf_helper.Resource(a_cli_argument=None, a_env_variable="MYENVVAR")
  
        self.assertEqual(resource.get_value_as_float()+1, 5.345)
        
def tests():
    """ global test method"""
    #suite = unittest.TestLoader().loadTestsFromModule(gmv.conf.conf_tests)
    suite = unittest.TestLoader().loadTestsFromTestCase(TestConf)
    unittest.TextTestRunner(verbosity=2).run(suite)
 
        
if __name__ == '__main__':
    tests()

########NEW FILE########
__FILENAME__ = exceptions
'''
    Gmvault: a tool to backup and restore your gmail account.
    Copyright (C) <2011-2013>  <guillaume Aubert (guillaume dot aubert at gmail do com)>

    This program is free software: you can redistribute it and/or modify
    it under the terms of the GNU Affero General Public License as
    published by the Free Software Foundation, either version 3 of the
    License, or (at your option) any later version.

    This program is distributed in the hope that it will be useful,
    but WITHOUT ANY WARRANTY; without even the implied warranty of
    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
    GNU Affero General Public License for more details.

    You should have received a copy of the GNU Affero General Public License
    along with this program.  If not, see <http://www.gnu.org/licenses/>.

'''
# exception classes
class Error(Exception):
    """Base class for Conf exceptions."""

    def __init__(self, msg=''):
        self.message = msg
        Exception.__init__(self, msg)

    def __repr__(self):
        return self.message

    __str__ = __repr__
    
class NoOptionError(Error):
    """A requested option was not found."""

    def __init__(self, option, section):
        Error.__init__(self, "No option %r in section: %r" % 
                       (option, section))
        self.option = option
        self.section = section

class NoSectionError(Error):
    """Raised when no section matches a requested option."""

    def __init__(self, section):
        Error.__init__(self, 'No section: %r' % (section,))
        self.section = section

class SubstitutionError(Error):
    """Base class for substitution-related exceptions."""

    def __init__(self, lineno, location, msg):
        Error.__init__(self, 'SubstitutionError on line %d: %s. %s' \
                       % (lineno, location, msg) if lineno != - 1 \
                       else 'SubstitutionError in %s. %s' % (lineno, location))
        
class IncludeError(Error):
    """ Raised when an include command is incorrect """
    
    def __init__(self, msg, origin):
        Error.__init__(self, msg)
        self.origin = origin
        self.errors = []


class ParsingError(Error):
    """Raised when a configuration file does not follow legal syntax."""
    def __init__(self, filename):
        Error.__init__(self, 'File contains parsing errors: %s' % filename)
        self.filename = filename
        self.errors = []

    def append(self, lineno, line):
        """ add error message """
        self.errors.append((lineno, line))
        self.message += '\n\t[line %2d]: %s' % (lineno, line)
        
    def get_error(self):
        """ return the error """
        return self
        
class MissingSectionHeaderError(ParsingError):
    """Raised when a key-value pair is found before any section header."""

    def __init__(self, filename, lineno, line):
        ParsingError.__init__(
            self,
            'File contains no section headers.\nfile: %s, line: %d\n%r' % 
            (filename, lineno, line))
        self.filename = filename
        self.lineno = lineno
        self.line = line

########NEW FILE########
__FILENAME__ = struct_parser
'''
    Gmvault: a tool to backup and restore your gmail account.
    Copyright (C) <2011-2013>  <guillaume Aubert (guillaume dot aubert at gmail do com)>

    This program is free software: you can redistribute it and/or modify
    it under the terms of the GNU Affero General Public License as
    published by the Free Software Foundation, either version 3 of the
    License, or (at your option) any later version.

    This program is distributed in the hope that it will be useful,
    but WITHOUT ANY WARRANTY; without even the implied warranty of
    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
    GNU Affero General Public License for more details.

    You should have received a copy of the GNU Affero General Public License
    along with this program.  If not, see <http://www.gnu.org/licenses/>.

'''
import tokenize
import token
import StringIO

class TokenizerError(Exception):
    """Base class for All exceptions"""

    def __init__(self, a_msg, a_line=None, a_col=None):
        
        self._line = a_line
        self._col  = a_col
        
        if self._line == None and self._col == None:
            extra = "" 
        else:
            extra = "(line=%s,col=%s)" % (self._line, self._col)
        
        super(TokenizerError, self).__init__("%s %s." % (a_msg, extra))
    

class Token(object):
    """ Token class """
    def __init__(self, a_type, num, value, begin, end, parsed_line):
        
        self._type  = a_type
        self._num   = num
        self._value = value
        self._begin = begin
        self._end   = end
        self._parsed_line  = parsed_line
    
    @property
    def type(self):
        """ Return the token type """
        return self._type

    @property
    def num(self):
        """ Return the token type num """
        return self._num

    @property
    def value(self):
        """ Return the token value """
        return self._value
    
    @property
    def begin(self):
        """ Return the token begin """
        return self._begin
    
    @property
    def end(self):
        """ Return the token end """
        return self._end
    
    @property
    def parsed_line(self):
        """ Return the token line """
        return self._parsed_line
    
    def __repr__(self):
        return "[type,num]=[%s,%s],value=[%s], parsed line=%s,[begin index,end index]=[%s,%s]" \
               % (self._type, self._num, self._value, self._parsed_line, self._begin, self._end)
         

class Tokenizer(object):
    """ 
        Create tokens for parsing the grammar. 
        This class is a wrapper around the python tokenizer adapt to the DSL that is going to be used.
    """    
    def __init__(self):
        """ constructor """
        # list of tokens
        self._tokens  = []
        
        self._index   = 0
        
        self._current = None
       
    def tokenize(self, a_program, a_eatable_token_types = ()):
        """ parse the expression.
            By default the parser eats space but some extra tokens by have to be eaten
        
            Args:
               a_expression: the expression to parser
               
            Returns:
               return dict containing the different parts of the request (spectrum, ....)
        
            Raises:
               exception TokenizerError if the syntax of the aString string is incorrect
        """
        g_info = tokenize.generate_tokens(StringIO.StringIO(a_program).readline)   # tokenize the string
        
        for toknum, tokval, tokbeg, tokend, tokline  in g_info:
            if token.tok_name[toknum] not in a_eatable_token_types:
                self._tokens.append(Token(token.tok_name[toknum], toknum, tokval, tokbeg, tokend, tokline))
            
        
            
    def __iter__(self):
        """ iterator implemented with a generator.
        """
        for tok in self._tokens:
            self._current = tok
            yield tok
        
    def next(self):
        """ get next token.
          
            Returns:
               return next token
        """
        
        self._current = self._tokens[self._index]
        self._index += 1
        return self._current
    
    def has_next(self):
        """ check it there are more tokens to consume.
        
            Returns:
               return True if more tokens to consume False otherwise
        """
        return self._index < len(self._tokens)
    
    def current_token(self):
        """ return the latest consumed token.
        
            Returns:
               return the latest consumerd token
        """
        return self._current
    
    def consume_token(self, what):
        """ consume the next token if it is what """
        if self._current.value != what :
            raise TokenizerError("Expected '%s' but instead found '%s'" % (what, self._current.value))
        else:
            return self.next()
        
    def consume_while_next_token_is_in(self, a_token_types_list):
        """
           Consume the next tokens as long as they have one of the passed types.
           This means that at least one token with one of the passed types needs to be matched.
           
           Args:
               a_token_types_list: the token types to consume
            
           Returns:
               return the next non matching token 
        """
        
        self.consume_next_tokens(a_token_types_list)
        
        while True:
        
            tok = self.next()
        
            if tok.type not in a_token_types_list:
                return tok
    
    def consume_while_current_token_is_in(self, a_token_types_list): #pylint: disable=C0103
        """
           Consume the tokens starting from the current token as long as they have one of the passed types.
           It is a classical token eater. It eats tokens as long as they are the specified type
           
           Args:
               a_token_types_list: the token types to consume
            
           Returns:
               return the next non matching token 
        """
        
        tok = self.current_token()
        
        while tok.type in a_token_types_list:
            tok = self.next()
        
        return tok
    
    def consume_next_tokens(self, a_token_types_list):
        """
           Consume one of the next token types given in the list and check that it is the expected type otherwise send an exception
            
           Args:
               a_tokens_list:  the token types to list 
               
           Returns:
               return next token 
           
           Raises:
               exception  BadTokenError if a Token Type that is not in a_token_types_list is found
        """
        
        tok = self.next()
        
        if tok.type not in a_token_types_list:
            raise TokenizerError("Expected '%s' but instead found '%s'" % (a_token_types_list, tok))
        else:
            return tok
    
    def advance(self, inc=1):
        """ return the next + inc token but do not consume it.
            Useful to check future tokens.
        
            Args:
               a_expression: increment + 1 is the default (just look one step forward)
               
            Returns:
               return lookhead token
        """
        return self._tokens[self._index-1 + inc]
    
class CompilerError(Exception):
    """Base class for All exceptions"""

    def __init__(self, a_msg, a_line=None, a_col=None):
        
        self._line = a_line
        self._col  = a_col
        
        msg = ''
        
        if self._line == None and self._col == None:
            extra = ""
            msg = "%s." % (a_msg) 
        else:
            extra = "(line=%s,col=%s)" % (self._line, self._col)
            msg = "%s %s." % (a_msg, extra)
        
        super(CompilerError, self).__init__(msg)
    
class Compiler(object):
    """ compile some python structures
    """
    
    def __init__(self):
        """ constructor """
        
        #default tokens to ignore
        self._tokens_to_ignore = ('INDENT', 'DEDENT', 'NEWLINE', 'NL')
    
    def compile_list(self, a_to_compile_str):
        """ compile a list object """
        
        try:
            tokenizer = Tokenizer()
            tokenizer.tokenize(a_to_compile_str, self._tokens_to_ignore)
        except tokenize.TokenError, err:
            
            #translate this error into something understandable. 
            #It is because the bloody tokenizer counts the brackets
            if err.args[0] == "EOF in multi-line statement":
                raise CompilerError("Expression \"%s\" cannot be converted as a list" % (a_to_compile_str))
            else:
                raise CompilerError(err)
            
            print("Err = %s\n" % (err))
        
        tokenizer.next()
        
        return self._compile_list(tokenizer)
    
    def compile_dict(self, a_to_compile_str):
        """ compile a dict object """
        
        try:
            tokenizer = Tokenizer()
            tokenizer.tokenize(a_to_compile_str, self._tokens_to_ignore)
        except tokenize.TokenError, err:
            
            #translate this error into something understandable. 
            #It is because the bloody tokenizer counts the brackets
            if err.args[0] == "EOF in multi-line statement":
                raise CompilerError("Expression \"%s\" cannot be converted as a dict" % (a_to_compile_str))
            else:
                raise CompilerError(err)
            
            print("Err = %s\n" % (err))
        
        tokenizer.next()
        
        return self._compile_dict(tokenizer)

    def _compile_dict(self, a_tokenizer):
        """ internal method for compiling a dict struct """
        result = {}
        
        the_token = a_tokenizer.current_token()
        
        while the_token.type != 'ENDMARKER':
            
            #look for an open bracket
            if the_token.type == 'OP' and the_token.value == '{':
               
                the_token = a_tokenizer.next()
                
                while True:
                   
                    if the_token.type == 'OP' and the_token.value == '}':
                        return result
                    else:
                        # get key values
                        (key, val) = self._compile_key_value(a_tokenizer)

                        result[key] = val  
                    
                    the_token = a_tokenizer.current_token()
                                   
            else:
                raise CompilerError("Unsupported token (type: %s, value : %s)" \
                                    % (the_token.type, the_token.value), the_token.begin[0], the_token.begin[1])
            
        #we should never reach that point (compilation error)
        raise CompilerError("End of line reached without finding a list. The line [%s] cannot be transformed as a list" \
                            % (the_token.parsed_line))
        
    def _compile_key_value(self, a_tokenizer):
        """ look for the pair key value component of a dict """
        
        the_token = a_tokenizer.current_token()
        
        key = None
        val = None
        
        # get key
        if the_token.type in ('STRING', 'NUMBER', 'NAME'):
            
            #next the_token is in _compile_litteral
            key = self._compile_litteral(a_tokenizer)
            
            the_token = a_tokenizer.current_token()
            
        else:
            raise CompilerError("unexpected token (type: %s, value : %s)" \
                                % (the_token.type, the_token.value), \
                                the_token.begin[0], the_token.begin[1])  
        
        #should have a comma now
        if the_token.type != 'OP' and the_token.value != ':':
            raise CompilerError("Expected a token (type:OP, value: :) but instead got (type: %s, value: %s)" \
                                % (the_token.type, the_token.value), the_token.begin[0], the_token.begin[1])
        else:
            #eat it
            the_token = a_tokenizer.next()
        
        #get value
        # it can be a
        if the_token.type in ('STRING', 'NUMBER', 'NAME'):
            #next the_token is in _compile_litteral
            val = self._compile_litteral(a_tokenizer)
            
            the_token = a_tokenizer.current_token()
        
        #check for a list
        elif the_token.value == '[' and the_token.type == 'OP':
            
            # look for a list
            val = self._compile_list(a_tokenizer)
            
            # positioning to the next token
            the_token = a_tokenizer.next()
            
        elif the_token.value == '{' and the_token.type == 'OP':
            
            # look for a dict
            val = self._compile_dict(a_tokenizer)
            
            # positioning to the next token
            the_token = a_tokenizer.next()
        
        elif the_token.value == '(' and the_token.type == 'OP':
            
            # look for a dict
            val = self._compile_tuple(a_tokenizer)
            
            # positioning to the next token
            the_token = a_tokenizer.next()
            
        else:
            raise CompilerError("unexpected token (type: %s, value : %s)" \
                                % (the_token.type, the_token.value), the_token.begin[0], \
                                the_token.begin[1])  
        
        #if we have a comma then eat it as it means that we will have more than one values
        if the_token.type == 'OP' and the_token.value == ',':
            the_token = a_tokenizer.next() 
            
        return (key, val)               
        
        
    def _compile_litteral(self, a_tokenizer):
        """ compile key. A key can be a NAME, STRING or NUMBER """
        
        val   = None
        
        dummy = None
        
        the_token = a_tokenizer.current_token()
        
        while the_token.type not in ('OP', 'ENDMARKER'):
            if the_token.type == 'STRING':  
                #check if the string is unicode
                if len(the_token.value) >= 3 and the_token.value[:2] == "u'":
                    #unicode string
                    #dummy = unicode(the_token.value[2:-1], 'utf_8') #decode from utf-8 encoding not necessary if read full utf-8 file
                    dummy = unicode(the_token.value[2:-1])
                else:
                    #ascii string
                    # the value contains the quote or double quotes so remove them always
                    dummy = the_token.value[1:-1]
                    
            elif the_token.type == 'NAME':
                # intepret all non quoted names as a string
                dummy = the_token.value
                    
            elif the_token.type == 'NUMBER':  
                     
                dummy = self._create_number(the_token.value)
                 
            else:
                raise CompilerError("unexpected token (type: %s, value : %s)" \
                                    % (the_token.type, the_token.value), \
                                    the_token.begin[0], the_token.begin[1])
           
            #if val is not None, it has to be a string
            if val:
                val = '%s %s' % (str(val), str(dummy))
            else:
                val = dummy
            
            the_token = a_tokenizer.next()
            
        return val
    
    
    def _compile_tuple(self, a_tokenizer):
        """ process tuple structure """
        result = []
        
        open_bracket = 0
        # this is the mode without [ & ] operator : 1,2,3,4
        simple_list_mode = 0
        
        the_token = a_tokenizer.current_token()
        
        while the_token.type != 'ENDMARKER':
            #look for an open bracket
            if the_token.value == '(' and the_token.type == 'OP':
                #first time we open a bracket and not in simple mode 
                if open_bracket == 0 and simple_list_mode == 0:
                    open_bracket += 1
                #recurse to create the imbricated list
                else:
                    result.append(self._compile_tuple(a_tokenizer))
                    
                the_token = a_tokenizer.next()
            
            elif the_token.value == '{' and the_token.type == 'OP':
               
                result.append(self._compile_dict(a_tokenizer))
                    
                the_token = a_tokenizer.next()
            
            elif the_token.value == '[' and the_token.type == 'OP':
               
                result.append(self._compile_list(a_tokenizer))
                    
                the_token = a_tokenizer.next()
                    
            elif the_token.type == 'OP' and the_token.value == ')':
                # end of list return result
                if open_bracket == 1:
                    return tuple(result)
                # cannot find a closing bracket and a simple list mode
                elif simple_list_mode == 1:
                    raise CompilerError("unexpected token (type: %s, value : %s)" \
                                        % (the_token.value, the_token.type), the_token.begin[0], \
                                        the_token.begin[1])
            # the comma case
            elif the_token.type == 'OP' and the_token.value == ',':
                # just eat it
                the_token = a_tokenizer.next()
                
            elif the_token.type in ('STRING', 'NUMBER', 'NAME'):
                
                # find values outside of a list 
                # this can be okay
                if open_bracket == 0:
                    simple_list_mode = 1
                    
                #next the_token is in _compile_litteral
                result.append(self._compile_litteral(a_tokenizer))
                
                the_token = a_tokenizer.current_token()
               
            else:
                raise CompilerError("Unsupported token (type: %s, value : %s)"\
                                    % (the_token.value, the_token.type), \
                                    the_token.begin[0], the_token.begin[1])
            
        
        # if we are in simple_list_mode return list else error
        if simple_list_mode == 1:
            return tuple(result)
            
        #we should never reach that point (compilation error)
        raise CompilerError("End of line reached without finding a list. The line [%s] cannot be transformed as a tuple" \
                            % (the_token.parsed_line))
    
    def _compile_list(self, a_tokenizer):
        """ process a list structure """
        result = []
        
        
        open_bracket = 0
        # this is the mode without [ & ] operator : 1,2,3,4
        simple_list_mode = 0
        
        the_token = a_tokenizer.current_token()
        
        while the_token.type != 'ENDMARKER':
            #look for an open bracket
            if the_token.value == '[' and the_token.type == 'OP':
                #first time we open a bracket and not in simple mode 
                if open_bracket == 0 and simple_list_mode == 0:
                    open_bracket += 1
                #recurse to create the imbricated list
                else:
                    result.append(self._compile_list(a_tokenizer))
                    
                the_token = a_tokenizer.next()
            
            elif the_token.value == '(' and the_token.type == 'OP':
               
                result.append(self._compile_tuple(a_tokenizer))
                    
                the_token = a_tokenizer.next()
            
            elif the_token.value == '{' and the_token.type == 'OP':
               
                result.append(self._compile_dict(a_tokenizer))
                    
                the_token = a_tokenizer.next()
                    
            elif the_token.type == 'OP' and the_token.value == ']':
                # end of list return result
                if open_bracket == 1:
                    return result
                # cannot find a closing bracket and a simple list mode
                elif simple_list_mode == 1:
                    raise CompilerError("unexpected token (type: %s, value : %s)" \
                                        % (the_token.value, the_token.type), the_token.begin[0], the_token.begin[1])
            # the comma case
            elif the_token.type == 'OP' and the_token.value == ',':
                # just eat it
                the_token = a_tokenizer.next()
                
            elif the_token.type in ('STRING', 'NUMBER', 'NAME'):
                
                # find values outside of a list 
                # this can be okay
                if open_bracket == 0:
                    simple_list_mode = 1
                    
                #next the_token is in _compile_litteral
                result.append(self._compile_litteral(a_tokenizer))
                
                the_token = a_tokenizer.current_token()
               
            else:
                raise CompilerError("Unsupported token (type: %s, value : %s)"\
                                    % (the_token.value, the_token.type), \
                                    the_token.begin[0], the_token.begin[1])
            
        
        # if we are in simple_list_mode return list else error
        if simple_list_mode == 1:
            return result
            
        #we should never reach that point (compilation error)
        raise CompilerError("End of line reached without finding a list. The line [%s] cannot be transformed as a list" \
                            % (the_token.parsed_line))
         
    @classmethod
    def _create_number(cls, a_number):
        """ depending on the value return a int or a float. 
            For the moment very simple: If there is . it is a float"""
        
        if a_number.find('.') > 0:
            return float(a_number)
        else:
            return int(a_number)

########NEW FILE########
__FILENAME__ = struct_parser_tests
# -*- coding: utf-8 -*-
'''
    Gmvault: a tool to backup and restore your gmail account.
    Copyright (C) <2011-2013>  <guillaume Aubert (guillaume dot aubert at gmail do com)>

    This program is free software: you can redistribute it and/or modify
    it under the terms of the GNU Affero General Public License as
    published by the Free Software Foundation, either version 3 of the
    License, or (at your option) any later version.

    This program is distributed in the hope that it will be useful,
    but WITHOUT ANY WARRANTY; without even the implied warranty of
    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
    GNU Affero General Public License for more details.

    You should have received a copy of the GNU Affero General Public License
    along with this program.  If not, see <http://www.gnu.org/licenses/>.

'''
# unit tests part
import unittest
from gmv.conf.utils.struct_parser import Compiler, CompilerError

class TestParser(unittest.TestCase): #pylint: disable=R0904
    """ TestParser Class """
    
    def setUp(self): #pylint: disable=C0103
        pass
        
    def test_simple_list_test(self):
        """ a first simple test with space and indent, dedents to eat"""
        
        the_string = "         [ 'a',     1.435, 3 ]"
        
        compiler = Compiler()
        
        the_result = compiler.compile_list(the_string)
        
        self.assertEqual(the_result, [ 'a', 1.435, 3])
    
    def test_negative_number_test(self):
        """ a negative number test """
        the_string = "         [ '-10.4',     1.435, 3 ]"
        
        compiler = Compiler()
        
        the_result = compiler.compile_list(the_string)
        
        self.assertEqual(the_result, [ '-10.4', 1.435, 3])
    
    def test_imbricated_lists_test(self):
        """ multiple lists within lists """
        
        the_string = "[a,b, [1,2,3,4, [456,6,'absdef'], 234, 2.456 ], aqwe, done]"
                
        compiler = Compiler()
        
        the_result = compiler.compile_list(the_string)
        
        self.assertEqual(the_result, ['a', 'b', [1, 2, 3, 4, [456, 6, 'absdef'], 234, 2.456 ]\
                                      , 'aqwe', 'done'])
  
    def test_list_without_bracket_test(self):
        """ simple list without bracket test """
        
        the_string = " 'a', b"
                
        compiler = Compiler()
        
        the_result = compiler.compile_list(the_string)
        
        self.assertEqual(the_result, ['a', 'b'])
    
    def test_list_without_bracket_test_2(self): #pylint: disable=C0103
        """ list without bracket test with a list inside """
        the_string = " 'a', b, ['a thing', 2]"
                
        compiler = Compiler()
        
        the_result = compiler.compile_list(the_string)
        
        self.assertEqual(the_result, ['a', 'b', ['a thing', 2] ])
        
    def test_list_error(self):
        """ list error """
        the_string = "  a ]"
        
        compiler = Compiler()
        
        try:
            compiler.compile_list(the_string)
        except CompilerError, err:
            self.assertEqual(err.message, 'Expression "  a ]" cannot be converted as a list.')
    
    def test_list_unicode_val(self):
        """ list unicode val """
        the_string = "[ u'[Gmail]/Чаты', 'z' ]".decode('utf-8')

        #to be in the same conditions as the conf object need to decode utf-8 as
        # it is done automatically with the os.open(...., 'uft-8')
        
        compiler = Compiler()
        
        compiler.compile_list(the_string)
        
        the_result = compiler.compile_list(the_string)
        
        self.assertEqual(the_result, [ u'[Gmail]/Чаты', 'z' ])
        
    def test_special_character_in_string(self):#pylint: disable=C0103
        """ simple list without bracket test """
        
        the_string = " 'a@', b"
                
        compiler = Compiler()
        
        the_result = compiler.compile_list(the_string)
        
        self.assertEqual(the_result, ['a@','b'])
        
    def test_list_error_2(self):
        """ unsupported char @ """
        the_string = " a @"
        
        compiler = Compiler()
        
        try:
            compiler.compile_list(the_string)
        except CompilerError, err:
            self.assertEqual(err.message, 'Unsupported token (type: @, value : OP) (line=1,col=3).')
        
    def test_simple_dict(self):
        """ simple dict """
        
        the_string = "{'a':1, b:2 }"
                
        compiler = Compiler()
        
        the_result = compiler.compile_dict(the_string)
        
        self.assertEqual(the_result, {'a':1, 'b':2 })
        
    def test_dict_error(self):
        """ dict error """
        the_string = "{'a':1, b:2 "
                
        compiler = Compiler()
        
        try:
            compiler.compile_dict(the_string)
        except CompilerError, err:
            self.assertEqual(err.message, 'Expression "{\'a\':1, b:2 " cannot be converted as a dict.')
        
    def test_dict_with_list(self):
        """ dict with list """
        
        the_string = "{'a':1, b:[1,2,3,4,5] }"
                
        compiler = Compiler()
        
        the_result = compiler.compile_dict(the_string)
        
        self.assertEqual(the_result, {'a':1, 'b':[1, 2, 3, 4, 5]})
        
    def test_list_with_dict(self):
        """ list with dict """
        
        the_string = "['a',1,'b',{2:3,4:5} ]"
                
        compiler = Compiler()
        
        the_result = compiler.compile_list(the_string)
        
        self.assertEqual(the_result, ['a', 1, 'b', { 2 : 3 , 4 : 5} ])
        
    def test_noquotes_dict(self):
        """ no quotes dict """
        
        the_string = "{ no12: a b , no10:a}"
                
        compiler = Compiler()
        
        the_result = compiler.compile_dict(the_string)
        
        self.assertEqual(the_result, { 'no12': 'a b' , 'no10':'a'})
        
    def test_everything(self):
        """ everything """
        
        the_string = "['a',1,'b',{2:3,4:[1,'hello', no quotes, [1,2,3,{1:2,3:4}]]} ]"
                
        compiler = Compiler()
        
        the_result = compiler.compile_list(the_string)
        
        self.assertEqual(the_result, ['a', 1, 'b', \
                                      {2 : 3, \
                                       4: [1, 'hello', 'no quotes', [1, 2, 3, {1:2, 3:4 }]]} ])
        
def tests():
    """ Global test method """
    #suite = unittest.TestLoader().loadTestsFromModule(struct_parser)
    suite = unittest.TestLoader().loadTestsFromTestCase(TestParser)
    unittest.TextTestRunner(verbosity=2).run(suite)
        
        
if __name__ == '__main__':
    tests()

########NEW FILE########
__FILENAME__ = credential_utils
'''
    Gmvault: a tool to backup and restore your gmail account.
    Copyright (C) <2011-2013>  <guillaume Aubert (guillaume dot aubert at gmail do com)>

    This program is free software: you can redistribute it and/or modify
    it under the terms of the GNU Affero General Public License as
    published by the Free Software Foundation, either version 3 of the
    License, or (at your option) any later version.

    This program is distributed in the hope that it will be useful,
    but WITHOUT ANY WARRANTY; without even the implied warranty of
    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
    GNU Affero General Public License for more details.

    You should have received a copy of the GNU Affero General Public License
    along with this program.  If not, see <http://www.gnu.org/licenses/>.

 Module handling the xauth authentication.
 Strongly influenced by http://code.google.com/p/googlecl/source/browse/trunk/src/googlecl/service.py
 and xauth part of gyb http://code.google.com/p/got-your-back/source/browse/trunk/gyb.py

'''
import gdata.service
import webbrowser
import random
import time
import atom
import urllib

import os
import getpass

import gmv.log_utils as log_utils
import gmv.blowfish as blowfish
import gmv.gmvault_utils as gmvault_utils

LOG = log_utils.LoggerFactory.get_logger('oauth')


def get_2_legged_oauth_tok_sec():
    '''
       Get 2 legged token and secret
    '''
    tok = raw_input('Enter your domain\'s OAuth consumer key: ')
  
    sec = raw_input('Enter your domain\'s OAuth consumer secret: ')
      
    return tok, sec, "two_legged"
    

def get_oauth_tok_sec(email, use_webbrowser = False, debug=False):
    '''
       Generate token and secret
    '''
    
    scopes = ['https://mail.google.com/', # IMAP/SMTP client access
              'https://www.googleapis.com/auth/userinfo#email'] # Email address access (verify token authorized by correct account
    
    gdata_serv = gdata.service.GDataService()
    gdata_serv.debug = debug
    gdata_serv.source = 'gmvault '
    
    gdata_serv.SetOAuthInputParameters(gdata.auth.OAuthSignatureMethod.HMAC_SHA1, \
                                       consumer_key = 'anonymous', consumer_secret = 'anonymous')
    
    params = {'xoauth_displayname':'Gmvault - Backup your Gmail account'}
    try:
        request_token = gdata_serv.FetchOAuthRequestToken(scopes=scopes, extra_parameters = params)
    except gdata.service.FetchingOAuthRequestTokenFailed, err:
        if str(err).find('Timestamp') != -1:
            LOG.critical('Is your system clock up to date? See the FAQ http://code.google.com/p/googlecl/wiki/FAQ'\
                         '#Timestamp_too_far_from_current_time\n')
            
        LOG.critical("Received Error: %s.\n" % (err) )
        LOG.critical("=== Exception traceback ===")
        LOG.critical(gmvault_utils.get_exception_traceback())
        LOG.critical("=== End of Exception traceback ===\n")
            
        return (None, None)
    
    url_params = {}
    domain = email[email.find('@')+1:]
    if domain.lower() != 'gmail.com' and domain.lower() != 'googlemail.com':
        url_params = {'hd': domain}
    
    auth_url = gdata_serv.GenerateOAuthAuthorizationURL(request_token=request_token, extra_params=url_params)
    
    #message to indicate that a browser will be opened
    raw_input('gmvault will now open a web browser page in order for you to grant gmvault access to your Gmail.\n'\
              'Please make sure you\'re logged into the correct Gmail account (%s) before granting access.\n'\
              'Press ENTER to open the browser. Once you\'ve granted access you can switch back to gmvault.' % (email))
    
    # run web browser otherwise print message with url
    if use_webbrowser:
        try:
            webbrowser.open(str(auth_url))  
        except Exception, err: #pylint: disable-msg=W0703
            LOG.critical("Error: %s.\n" % (err) )
            LOG.critical("=== Exception traceback ===")
            LOG.critical(gmvault_utils.get_exception_traceback())
            LOG.critical("=== End of Exception traceback ===\n")
        
        raw_input("You should now see the web page on your browser now.\n"\
                  "If you don\'t, you can manually open:\n\n%s\n\nOnce you've granted"\
                  " gmvault access, press the Enter key.\n" % (auth_url))
        
    else:
        raw_input('Please log in and/or grant access via your browser at %s '
                  'then hit enter.' % (auth_url))
    
    try:
        final_token = gdata_serv.UpgradeToOAuthAccessToken(request_token)
    except gdata.service.TokenUpgradeFailed:
        LOG.critical('Token upgrade failed! Could not get OAuth access token.\n Did you grant gmvault access in your browser ?')
        LOG.critical("=== Exception traceback ===")
        LOG.critical(gmvault_utils.get_exception_traceback())
        LOG.critical("=== End of Exception traceback ===\n")
        
        return (None, None)

    return (final_token.key, final_token.secret, "normal")

def generate_xoauth_req(a_token, a_secret, email, type):
    """
       generate the xoauth req from a user token and secret.
       Handle two_legged xoauth for admins.
    """
    nonce = str(random.randrange(2**64 - 1))
    timestamp = str(int(time.time()))
    if type == "two_legged": #2 legged oauth
        request = atom.http_core.HttpRequest('https://mail.google.com/mail/b/%s/imap/?xoauth_requestor_id=%s' \
                                             % (email, urllib.quote(email)), 'GET')
         
        signature = gdata.gauth.generate_hmac_signature(http_request=request, consumer_key=a_token, consumer_secret=a_secret, \
                                                        timestamp=timestamp, nonce=nonce, version='1.0', next=None)
        return '''GET https://mail.google.com/mail/b/%s/imap/?xoauth_requestor_id=%s oauth_consumer_key="%s",oauth_nonce="%s"'''\
               ''',oauth_signature="%s",oauth_signature_method="HMAC-SHA1",oauth_timestamp="%s",oauth_version="1.0"''' \
               % (email, urllib.quote(email), a_token, nonce, urllib.quote(signature), timestamp)
    else:
        request = atom.http_core.HttpRequest('https://mail.google.com/mail/b/%s/imap/' % email, 'GET')
        signature = gdata.gauth.generate_hmac_signature(
            http_request=request, consumer_key='anonymous', consumer_secret='anonymous', timestamp=timestamp,
            nonce=nonce, version='1.0', next=None, token = a_token, token_secret= a_secret)
        return '''GET https://mail.google.com/mail/b/%s/imap/ oauth_consumer_key="anonymous",oauth_nonce="%s"'''\
               ''',oauth_signature="%s",oauth_signature_method="HMAC-SHA1",oauth_timestamp="%s",oauth_token="%s"'''\
               ''',oauth_version="1.0"''' \
               % (email, nonce, urllib.quote(signature), timestamp, urllib.quote(a_token))




class CredentialHelper(object):
    """
       Helper handling all credentials
    """
    SECRET_FILEPATH = '%s/token.sec' 
    
    @classmethod
    def get_secret_key(cls, a_filepath):
        """
           Get secret key if it is in the file otherwise generate it and save it
        """
        if os.path.exists(a_filepath):
            secret = open(a_filepath).read()
        else:
            secret = gmvault_utils.make_password()
            
            fdesc = os.open(a_filepath, os.O_CREAT|os.O_WRONLY, 0600)
            
            the_bytes = os.write(fdesc, secret)
            os.close(fdesc) #close anyway
            
            if the_bytes < len(secret):
                raise Exception("Error: Cannot write secret in %s" % (a_filepath))

        return secret
    
    @classmethod
    def store_passwd(cls, email, passwd):
        """
           Encrypt and store gmail password
        """
        passwd_file = '%s/%s.passwd' % (gmvault_utils.get_home_dir_path(), email)
    
        fdesc = os.open(passwd_file, os.O_CREAT|os.O_WRONLY, 0600)
        
        cipher       = blowfish.Blowfish(cls.get_secret_key(cls.SECRET_FILEPATH % (gmvault_utils.get_home_dir_path())))
        cipher.initCTR()
    
        encrypted = cipher.encryptCTR(passwd)
        the_bytes = os.write(fdesc, encrypted)
    
        os.close(fdesc)
        
        if the_bytes < len(encrypted):
            raise Exception("Error: Cannot write password in %s" % (passwd_file))
        
    @classmethod
    def store_oauth_credentials(cls, email, token, secret, type):
        """
           store oauth_credentials
        """
        oauth_file = '%s/%s.oauth' % (gmvault_utils.get_home_dir_path(), email)
    
        fdesc = os.open(oauth_file, os.O_CREAT|os.O_WRONLY, 0600)
        
        os.write(fdesc, token)
        os.write(fdesc, '::')
        os.write(fdesc, secret)
        os.write(fdesc, '::')
        os.write(fdesc, type)
    
        os.close(fdesc)
    
    @classmethod
    def read_password(cls, email):
        """
           Read password credentials
           Look by default to ~/.gmvault
           Look for file ~/.gmvault/email.passwd
        """
        gmv_dir = gmvault_utils.get_home_dir_path()
        
        #look for email.passwed in GMV_DIR
        user_passwd_file_path = "%s/%s.passwd" % (gmv_dir, email)

        password = None
        if os.path.exists(user_passwd_file_path):
            passwd_file  = open(user_passwd_file_path)
            
            password     = passwd_file.read()
            cipher       = blowfish.Blowfish(cls.get_secret_key(cls.SECRET_FILEPATH % (gmvault_utils.get_home_dir_path())))
            cipher.initCTR()
            password     = cipher.decryptCTR(password)
        
        return password
    
    @classmethod
    def read_oauth_tok_sec(cls, email):
        """
           Read oauth token secret credential
           Look by default to ~/.gmvault
           Look for file ~/.gmvault/email.oauth
        """
        gmv_dir = gmvault_utils.get_home_dir_path()
        
        #look for email.passwed in GMV_DIR
        user_oauth_file_path = "%s/%s.oauth" % (gmv_dir, email)

        token  = None
        secret = None
        type   = None
        if os.path.exists(user_oauth_file_path):
            LOG.critical("Get XOAuth credential from %s.\n" % (user_oauth_file_path))
            
            oauth_file  = open(user_oauth_file_path)
            
            try:
                oauth_result = oauth_file.read()
                if oauth_result:
                    oauth_result = oauth_result.split('::')
                    if len(oauth_result) == 2:
                        token  = oauth_result[0]
                        secret = oauth_result[1]
                        type   = "normal"
                    elif len(oauth_result) == 3:
                        token  = oauth_result[0]
                        secret = oauth_result[1]
                        type   = oauth_result[2]
            except Exception, _: #pylint: disable-msg=W0703              
                LOG.critical("Cannot read oauth credentials from %s. Force oauth credentials renewal." % (user_oauth_file_path))
                LOG.critical("=== Exception traceback ===")
                LOG.critical(gmvault_utils.get_exception_traceback())
                LOG.critical("=== End of Exception traceback ===\n")
        
        if token: token   = token.strip() #pylint: disable-msg=C0321
        if secret: secret = secret.strip()  #pylint: disable-msg=C0321
        if type: type = type.strip()
        
        return token, secret, type
            
    @classmethod
    def get_credential(cls, args, test_mode = {'activate': False, 'value' : 'test_password'}): #pylint: disable-msg=W0102
        """
           Deal with the credentials.
           1) Password
           --passwd passed. If --passwd passed and not password given if no password saved go in interactive mode
           2) XOAuth Token
        """
        credential = { }
        
        #first check that there is an email
        if not args.get('email', None):
            raise Exception("No email passed, Need to pass an email")
        
        if args['passwd'] in ['empty', 'store', 'renew']: 
            # --passwd is here so look if there is a passwd in conf file 
            # or go in interactive mode
            
            LOG.critical("Authentication performed with Gmail password.\n")
            
            passwd = cls.read_password(args['email'])
            
            #password to be renewed so need an interactive phase to get the new pass
            if not passwd or args['passwd'] in ['renew', 'store']: # go to interactive mode
                if not test_mode.get('activate', False):
                    passwd = getpass.getpass('Please enter gmail password for %s and press ENTER:' % (args['email']))
                else:
                    passwd = test_mode.get('value', 'no_password_given')
                    
                credential = { 'type' : 'passwd', 'value' : passwd}
                
                #store it in dir if asked for --store-passwd or --renew-passwd
                if args['passwd'] in ['renew', 'store']:
                    LOG.critical("Store password for %s in $HOME/.gmvault." % (args['email']))
                    cls.store_passwd(args['email'], passwd)
                    credential['option'] = 'saved'
            else:
                LOG.critical("Use password stored in $HOME/.gmvault dir (Storing your password here is not recommended).")
                credential = { 'type' : 'passwd', 'value' : passwd, 'option':'read' }
                               
        #elif args['passwd'] == 'not_seen' and args['oauth']:
        elif args['passwd'] in ('not_seen', None) and args['oauth'] in (None, 'empty', 'renew', 'not_seen'):
            # get token secret
            # if they are in a file then no need to call get_oauth_tok_sec
            # will have to add 2 legged 
            LOG.critical("Authentication performed with Gmail XOAuth token.\n")
            
            two_legged = args.get('two_legged', False) # 2 legged oauth
            
            token, secret, type = cls.read_oauth_tok_sec(args['email'])
           
            if not token or args['oauth'] == 'renew':
                
                if args['oauth'] == 'renew':
                    LOG.critical("Renew XOAuth token (normal or 2-legged). Initiate interactive session to get it from Gmail.\n")
                else:
                    LOG.critical("Initiate interactive session to get XOAuth normal or 2-legged token from Gmail.\n")
                
                if two_legged:
                    token, secret, type = get_2_legged_oauth_tok_sec()
                else:
                    token, secret, type = get_oauth_tok_sec(args['email'], use_webbrowser = True)
                
                if not token:
                    raise Exception("Cannot get XOAuth token from Gmail. See Gmail error message")
                #store newly created token
                cls.store_oauth_credentials(args['email'], token, secret, type)
               
            xoauth_req = generate_xoauth_req(token, secret, args['email'], type)
            
            LOG.critical("Successfully read oauth credentials.\n")

            credential = { 'type' : 'xoauth', 'value' : xoauth_req, 'option':None }
                        
        return credential

    @classmethod
    def get_xoauth_req_from_email(cls, email):
        """
           This will be used to reconnect after a timeout
        """
        token, secret, type = cls.read_oauth_tok_sec(email)
        if not token: 
            raise Exception("Error cannot read token, secret from")
        
        xoauth_req = generate_xoauth_req(token, secret, email, type)
        
        return xoauth_req

########NEW FILE########
__FILENAME__ = gmvault
'''
    Gmvault: a tool to backup and restore your gmail account.
    Copyright (C) <2011-2013>  <guillaume Aubert (guillaume dot aubert at gmail do com)>

    This program is free software: you can redistribute it and/or modify
    it under the terms of the GNU Affero General Public License as
    published by the Free Software Foundation, either version 3 of the
    License, or (at your option) any later version.

    This program is distributed in the hope that it will be useful,
    but WITHOUT ANY WARRANTY; without even the implied warranty of
    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
    GNU Affero General Public License for more details.

    You should have received a copy of the GNU Affero General Public License
    along with this program.  If not, see <http://www.gnu.org/licenses/>.

'''
import json
import time
import datetime
import os
import itertools
import imaplib

import gmv.log_utils as log_utils
import gmv.collections_utils as collections_utils
import gmv.gmvault_utils as gmvault_utils
import gmv.imap_utils as imap_utils
import gmv.gmvault_db as gmvault_db

LOG = log_utils.LoggerFactory.get_logger('gmvault')

def handle_restore_imap_error(the_exception, gm_id, db_gmail_ids_info, gmvaulter):
    """
       function to handle restore IMAPError and OSError([Errno 2] No such file or directory) in restore functions 
    """
    if isinstance(the_exception, imaplib.IMAP4.abort):
        # if this is a Gmvault SSL Socket error quarantine the email and continue the restore
        if str(the_exception).find("=> Gmvault ssl socket error: EOF") >= 0:
            LOG.critical("Quarantine email with gm id %s from %s. GMAIL IMAP cannot restore it:"\
                         " err={%s}" % (gm_id, db_gmail_ids_info[gm_id], str(the_exception)))
            gmvaulter.gstorer.quarantine_email(gm_id)
            gmvaulter.error_report['emails_in_quarantine'].append(gm_id)
            LOG.critical("Disconnecting and reconnecting to restart cleanly.")
            gmvaulter.src.reconnect() #reconnect
        else:
            raise the_exception
    elif isinstance(the_exception, IOError) and str(the_exception).find('[Errno 2] No such file or directory:') >=0:
        LOG.critical("Quarantine email with gm id %s from %s. GMAIL IMAP cannot restore it:"\
                         " err={%s}" % (gm_id, db_gmail_ids_info[gm_id], str(the_exception)))  
        gmvaulter.gstorer.quarantine_email(gm_id)
        gmvaulter.error_report['emails_in_quarantine'].append(gm_id)
        LOG.critical("Disconnecting and reconnecting to restart cleanly.")
        gmvaulter.src.reconnect() #reconnect      
           
    elif isinstance(the_exception, imaplib.IMAP4.error): 
        LOG.error("Catched IMAP Error %s" % (str(the_exception)))
        LOG.exception(the_exception)
        
        #When the email cannot be read from Database because it was empty when returned by gmail imap
        #quarantine it.
        if str(the_exception) == "APPEND command error: BAD ['Invalid Arguments: Unable to parse message']":
            LOG.critical("Quarantine email with gm id %s from %s. GMAIL IMAP cannot restore it:"\
                         " err={%s}" % (gm_id, db_gmail_ids_info[gm_id], str(the_exception)))
            gmvaulter.gstorer.quarantine_email(gm_id)
            gmvaulter.error_report['emails_in_quarantine'].append(gm_id) 
        else:
            raise the_exception
    elif isinstance(the_exception, imap_utils.PushEmailError):
        LOG.error("Catch the following exception %s" % (str(the_exception)))
        LOG.exception(the_exception)
        
        if the_exception.quarantined():
            LOG.critical("Quarantine email with gm id %s from %s. GMAIL IMAP cannot restore it:"\
                         " err={%s}" % (gm_id, db_gmail_ids_info[gm_id], str(the_exception)))
            gmvaulter.gstorer.quarantine_email(gm_id)
            gmvaulter.error_report['emails_in_quarantine'].append(gm_id) 
        else:
            raise the_exception          
    else:
        LOG.error("Catch the following exception %s" % (str(the_exception)))
        LOG.exception(the_exception)
        raise the_exception

def handle_sync_imap_error(the_exception, the_id, error_report, src):
    """
      function to handle IMAPError in gmvault
      type = chat or email
    """    
    if isinstance(the_exception, imaplib.IMAP4.abort):
        # imap abort error 
        # ignore it 
        # will have to do something with these ignored messages
        LOG.critical("Error while fetching message with imap id %s." % (the_id))
        LOG.critical("\n=== Exception traceback ===\n")
        LOG.critical(gmvault_utils.get_exception_traceback())
        LOG.critical("=== End of Exception traceback ===\n")
        try:
            #try to get the gmail_id
            curr = src.fetch(the_id, imap_utils.GIMAPFetcher.GET_GMAIL_ID) 
        except Exception, _: #pylint:disable-msg=W0703
            curr = None
            LOG.critical("Error when trying to get gmail id for message with imap id %s." % (the_id))
            LOG.critical("Disconnect, wait for 20 sec then reconnect.")
            src.disconnect()
            #could not fetch the gm_id so disconnect and sleep
            #sleep 10 sec
            time.sleep(10)
            LOG.critical("Reconnecting ...")
            src.connect()
            
        if curr:
            gmail_id = curr[the_id][imap_utils.GIMAPFetcher.GMAIL_ID]
        else:
            gmail_id = None
            
        #add ignored id
        error_report['cannot_be_fetched'].append((the_id, gmail_id))
        
        LOG.critical("Forced to ignore message with imap id %s, (gmail id %s)." \
                     % (the_id, (gmail_id if gmail_id else "cannot be read")))
        
    elif isinstance(the_exception, imaplib.IMAP4.error):
        # check if this is a cannot be fetched error 
        # I do not like to do string guessing within an exception but I do not have any choice here
        LOG.critical("Error while fetching message with imap id %s." % (the_id))
        LOG.critical("\n=== Exception traceback ===\n")
        LOG.critical(gmvault_utils.get_exception_traceback())
        LOG.critical("=== End of Exception traceback ===\n")
         
        #quarantine emails that have raised an abort error
        if str(the_exception).find("'Some messages could not be FETCHed (Failure)'") >= 0:
            try:
                #try to get the gmail_id
                LOG.critical("One more attempt. Trying to fetch the Gmail ID for %s" % (the_id) )
                curr = src.fetch(the_id, imap_utils.GIMAPFetcher.GET_GMAIL_ID) 
            except Exception, _: #pylint:disable-msg=W0703
                curr = None
            
            if curr:
                gmail_id = curr[the_id][imap_utils.GIMAPFetcher.GMAIL_ID]
            else:
                gmail_id = None
            
            #add ignored id
            error_report['cannot_be_fetched'].append((the_id, gmail_id))
            
            LOG.critical("Ignore message with imap id %s, (gmail id %s)" % (the_id, (gmail_id if gmail_id else "cannot be read")))
        
        else:
            raise the_exception #rethrow error
    else:
        raise the_exception    

class IMAPBatchFetcher(object):
    """
       Fetch IMAP data in batch 
    """
    def __init__(self, src, imap_ids, error_report, request, default_batch_size = 100):
        """
           constructor
        """
        self.src                = src
        self.imap_ids           = imap_ids
        self.def_batch_size     = default_batch_size
        self.request            = request
        self.error_report       = error_report  
        
        self.to_fetch           = list(imap_ids)
    
    def individual_fetch(self, imap_ids):
        """
           Find the imap_id creating the issue
           return the data related to the imap_ids
        """
        new_data = {}
        for the_id in imap_ids:    
            try: 
                single_data = self.src.fetch(the_id, self.request)
                new_data.update(single_data)                
            except Exception, error:
                handle_sync_imap_error(error, the_id, self.error_report, self.src) #do everything in this handler

        return new_data
   
    def __iter__(self):
        return self     
    
    def next(self):
        """
            Return the next batch of elements
        """
        new_data = {}
        batch = self.to_fetch[:self.def_batch_size]
        
        if len(batch) <= 0:
            raise StopIteration
        
        try:
        
            new_data = self.src.fetch(batch, self.request)
            
            self.to_fetch = self.to_fetch[self.def_batch_size:]
            
            return new_data

        except imaplib.IMAP4.error, _:
            new_data = self.individual_fetch(batch) 
    
        return new_data
    
    def reset(self):
        """
           Restart from the beginning
        """
        self.to_fetch = self.imap_ids              
               
class GMVaulter(object):
    """
       Main object operating over gmail
    """ 
    NB_GRP_OF_ITEMS         = 1400
    EMAIL_RESTORE_PROGRESS  = 'email_last_id.restore'
    CHAT_RESTORE_PROGRESS   = 'chat_last_id.restore'
    EMAIL_SYNC_PROGRESS     = 'email_last_id.sync'
    CHAT_SYNC_PROGRESS      = 'chat_last_id.sync'
    
    OP_EMAIL_RESTORE = "EM_RESTORE"
    OP_EMAIL_SYNC    = "EM_SYNC"
    OP_CHAT_RESTORE  = "CH_RESTORE"
    OP_CHAT_SYNC    = "CH_SYNC"
    
    OP_TO_FILENAME = { OP_EMAIL_RESTORE : EMAIL_RESTORE_PROGRESS,
                       OP_EMAIL_SYNC    : EMAIL_SYNC_PROGRESS,
                       OP_CHAT_RESTORE  : CHAT_RESTORE_PROGRESS,
                       OP_CHAT_SYNC     : CHAT_SYNC_PROGRESS
                     }
    
    
    def __init__(self, db_root_dir, host, port, login, \
                 credential, read_only_access = True, use_encryption = False): #pylint:disable-msg=R0913,R0914
        """
           constructor
        """   
        self.db_root_dir = db_root_dir
        
        #create dir if it doesn't exist
        gmvault_utils.makedirs(self.db_root_dir)
        
        #keep track of login email
        self.login = login
            
        # create source and try to connect
        self.src = imap_utils.GIMAPFetcher(host, port, login, credential, \
                                           readonly_folder = read_only_access)
        
        self.src.connect()
        
        LOG.debug("Connected")
        
        self.use_encryption = use_encryption
        
        #to report gmail imap problems
        self.error_report = { 'empty' : [] ,
                              'cannot_be_fetched'  : [],
                              'emails_in_quarantine' : [],
                              'reconnections' : 0}
        
        #instantiate gstorer
        self.gstorer =  gmvault_db.GmailStorer(self.db_root_dir, self.use_encryption)
        
        #timer used to mesure time spent in the different values
        self.timer = gmvault_utils.Timer()
        
    @classmethod
    def get_imap_request_btw_2_dates(cls, begin_date, end_date):
        """
           Return the imap request for those 2 dates
        """
        imap_req = 'Since %s Before %s' % (gmvault_utils.datetime2imapdate(begin_date), gmvault_utils.datetime2imapdate(end_date))
        
        return imap_req
    
    def get_operation_report(self):
        """
           Return the error report
        """
        the_str = "\n================================================================\n"\
                  "%s operation performed in %s.\n" \
                  "Number of reconnections: %d.\nNumber of emails quarantined: %d.\n" \
                  "Number of emails that could not be fetched: %d.\n" \
                  "Number of emails that were returned empty by gmail: %d\n"\
                  "================================================================" \
              % (self.error_report['operation'], \
                 self.error_report['operation_time'], \
                 self.error_report['reconnections'], \
                 len(self.error_report['emails_in_quarantine']), \
                 len(self.error_report['cannot_be_fetched']), \
                 len(self.error_report['empty'])
                )
              
        LOG.debug("error_report complete structure = %s" % (self.error_report))
        
        return the_str
        
    @classmethod
    def _get_next_date(cls, a_current_date, start_month_beginning = False):
        """
           return the next date necessary to build the imap req
        """
        if start_month_beginning:
            dummy_date   = a_current_date.replace(day=1)
        else:
            dummy_date   = a_current_date
            
        # the next date = current date + 1 month
        return dummy_date + datetime.timedelta(days=31)
        
    @classmethod
    def check_email_on_disk(cls, a_gstorer, a_id, a_dir = None):
        """
           Factory method to create the object if it exists
        """
        try:
            a_dir = a_gstorer.get_directory_from_id(a_id, a_dir)
           
            if a_dir:
                return a_gstorer.unbury_metadata(a_id, a_dir) 
            
        except ValueError, json_error:
            LOG.exception("Cannot read file %s. Try to fetch the data again" % ('%s.meta' % (a_id)), json_error )
        
        return None
    
    @classmethod
    def _metadata_needs_update(cls, curr_metadata, new_metadata, chat_metadata = False):
        """
           Needs update
        """
        if curr_metadata[gmvault_db.GmailStorer.ID_K] != new_metadata['X-GM-MSGID']:
            raise Exception("Gmail id has changed for %s" % (curr_metadata['id']))
                
        #check flags   
        prev_set = set(new_metadata['FLAGS'])    
        
        for flag in curr_metadata['flags']:
            if flag not in prev_set:
                return True
            else:
                prev_set.remove(flag)
        
        if len(prev_set) > 0:
            return True
        
        #check labels
        prev_labels = set(new_metadata['X-GM-LABELS'])
        
        if chat_metadata: #add gmvault-chats labels
            prev_labels.add(gmvault_db.GmailStorer.CHAT_GM_LABEL)
            
        
        for label in curr_metadata['labels']:
            if label not in prev_labels:
                return True
            else:
                prev_labels.remove(label)
        
        if len(prev_labels) > 0:
            return True
        
        return False
    
    
    def _check_email_db_ownership(self, ownership_control):
        """
           Check email database ownership.
           If ownership control activated then fail if a new additional owner is added.
           Else if no ownership control allow one more user and save it in the list of owners
           
           Return the number of owner this will be used to activate or not the db clean.
           Activating a db cleaning on a multiownership db would be a catastrophy as it would delete all
           the emails from the others users.
        """
        #check that the gmvault-db is not associated with another user
        db_owners = self.gstorer.get_db_owners()
        if ownership_control:
            if len(db_owners) > 0 and self.login not in db_owners: #db owner should not be different unless bypass activated
                raise Exception("The email database %s is already associated with one or many logins: %s."\
                                " Use option (-m, --multiple-db-owner) if you want to link it with %s" \
                                % (self.db_root_dir, ", ".join(db_owners), self.login))
        else:
            if len(db_owners) == 0:
                LOG.critical("Establish %s as the owner of the Gmvault db %s." % (self.login, self.db_root_dir))  
            elif len(db_owners) > 0 and self.login not in db_owners:
                LOG.critical("The email database %s is hosting emails from %s. It will now also store emails from %s" \
                             % (self.db_root_dir, ", ".join(db_owners), self.login))
                
        #try to save db_owner in the list of owners
        self.gstorer.store_db_owner(self.login)
        
    def _sync_chats(self, imap_req, compress, restart):
        """
           sync emails
        """
        chat_dir = None
        
        timer = gmvault_utils.Timer() #start local timer for chat
        timer.start()
        
        LOG.debug("Before selection")
        if self.src.is_visible('CHATS'):
            chat_dir = self.src.select_folder('CHATS')
        
        LOG.debug("Selection is finished")

        if chat_dir:
            imap_ids = self._common_sync(timer, "chat", imap_req, compress, restart)
        else:
            imap_ids = []    
        
        LOG.critical("\nchats synchronisation operation performed in %s.\n" % (timer.seconds_to_human_time(timer.elapsed())))

        return imap_ids


    def _common_sync(self, a_timer, a_type, imap_req, compress, restart):
        """
           common syncing method for both emails and chats. 
        """
        # get all imap ids in All Mail
        imap_ids = self.src.search(imap_req)
        
        # check if there is a restart
        if restart:
            LOG.critical("Restart mode activated for emails. Need to find information in Gmail, be patient ...")
            imap_ids = self.get_gmails_ids_left_to_sync(self.OP_EMAIL_SYNC if a_type == "email" \
                                                        else self.OP_CHAT_SYNC, imap_ids, imap_req)
        
        total_nb_msgs_to_process = len(imap_ids) # total number of emails to get
        
        LOG.critical("%d %ss to be fetched." % (total_nb_msgs_to_process, a_type))
        
        nb_msgs_processed = 0
        
        to_fetch = set(imap_ids)
        batch_fetcher = IMAPBatchFetcher(self.src, imap_ids, self.error_report, imap_utils.GIMAPFetcher.GET_ALL_BUT_DATA, \
                                         default_batch_size = \
                                         gmvault_utils.get_conf_defaults().getint("General","nb_messages_per_batch",500))
        
        #choose different bury methods if it is an email or a chat
        if a_type == "email":
            bury_metadata_fn = self.gstorer.bury_metadata
            bury_data_fn     = self.gstorer.bury_email
            chat_metadata    = False
        elif a_type == "chat":
            bury_metadata_fn = self.gstorer.bury_chat_metadata
            bury_data_fn     = self.gstorer.bury_chat
            chat_metadata    = True
        else:
            raise Exception("Error a_type %s in _common_sync is unknown" % (a_type))
        
        #LAST Thing to do remove all found ids from imap_ids and if ids left add missing in report
        for new_data in batch_fetcher:            
            for the_id in new_data:
                if new_data.get(the_id, None):
                    LOG.debug("\nProcess imap id %s" % ( the_id ))
                        
                    gid      = new_data[the_id][imap_utils.GIMAPFetcher.GMAIL_ID]
                    eml_date = new_data[the_id][imap_utils.GIMAPFetcher.IMAP_INTERNALDATE]
                    
                    if a_type == "email":
                        the_dir = gmvault_utils.get_ym_from_datetime(eml_date)
                    elif a_type == "chat":
                        the_dir = self.gstorer.get_sub_chats_dir()
                    else:
                        raise Exception("Error a_type %s in _common_sync is unknown" % (a_type))
                    
                    LOG.critical("Process %s num %d (imap_id:%s) from %s." % (a_type, nb_msgs_processed, the_id, the_dir))
                    
                    #decode the labels that are received as utf7 => unicode
                    new_data[the_id][imap_utils.GIMAPFetcher.GMAIL_LABELS] = \
                    imap_utils.decode_labels(new_data[the_id][imap_utils.GIMAPFetcher.GMAIL_LABELS])

                    LOG.debug("metadata info collected: %s\n" % (new_data[the_id]))
                
                    #pass the dir and the ID
                    curr_metadata = GMVaulter.check_email_on_disk( self.gstorer , \
                                                                   new_data[the_id][imap_utils.GIMAPFetcher.GMAIL_ID], \
                                                                   the_dir)
                    
                    #if on disk check that the data is not different
                    if curr_metadata:
                        
                        LOG.debug("metadata for %s already exists. Check if different." % (gid))
                        
                        if self._metadata_needs_update(curr_metadata, new_data[the_id], chat_metadata):
                            
                            LOG.debug("%s with imap id %s and gmail id %s has changed. Updated it." % (a_type, the_id, gid))
                            
                            #restore everything at the moment
                            gid  = bury_metadata_fn(new_data[the_id], local_dir = the_dir)
                            
                            #update local index id gid => index per directory to be thought out
                        else:
                            LOG.debug("On disk metadata for %s is up to date." % (gid))
                    else:  
                        try:
                            #get the data
                            LOG.debug("Get Data for %s." % (gid))
                            email_data = self.src.fetch(the_id, imap_utils.GIMAPFetcher.GET_DATA_ONLY )
                            
                            new_data[the_id][imap_utils.GIMAPFetcher.EMAIL_BODY] = \
                            email_data[the_id][imap_utils.GIMAPFetcher.EMAIL_BODY]
                            
                            LOG.debug("Storing on disk data for %s" % (gid))
                            # store data on disk within year month dir 
                            gid  = bury_data_fn(new_data[the_id], local_dir = the_dir, compress = compress)
                            
                            #update local index id gid => index per directory to be thought out
                            LOG.debug("Create and store email with imap id %s, gmail id %s." % (the_id, gid))   
                        except Exception, error:
                            handle_sync_imap_error(error, the_id, self.error_report, self.src) #do everything in this handler    
                    
                    nb_msgs_processed += 1
                    
                    #indicate every 50 messages the number of messages left to process
                    left_emails = (total_nb_msgs_to_process - nb_msgs_processed)
                    
                    if (nb_msgs_processed % 50) == 0 and (left_emails > 0):
                        elapsed = a_timer.elapsed() #elapsed time in seconds
                        LOG.critical("\n== Processed %d emails in %s. %d left to be stored (time estimate %s).==\n" % \
                                     (nb_msgs_processed,  \
                                      a_timer.seconds_to_human_time(elapsed), left_emails, \
                                      a_timer.estimate_time_left(nb_msgs_processed, elapsed, left_emails)))
                    
                    # save id every 10 restored emails
                    if (nb_msgs_processed % 10) == 0:
                        if gid:
                            self.save_lastid(self.OP_EMAIL_SYNC, gid, eml_date, imap_req)
                else:
                    LOG.info("Could not process message with id %s. Ignore it\n" % (the_id))
                    self.error_report['empty'].append((the_id, gid if gid else None))
                    
            to_fetch -= set(new_data.keys()) #remove all found keys from to_fetch set
                
        for the_id in to_fetch:
            # case when gmail IMAP server returns OK without any data whatsoever
            # eg. imap uid 142221L ignore it
            LOG.info("Could not process imap with id %s. Ignore it\n" % (the_id))
            self.error_report['empty'].append((the_id, None))
        
        return imap_ids

    def _sync_emails(self, imap_req, compress, restart):
        """
           sync emails
        """
        timer = gmvault_utils.Timer()
        timer.start()

        #select all mail folder using the constant name defined in GIMAPFetcher
        self.src.select_folder('ALLMAIL')

        imap_ids = self._common_sync(timer, "email", imap_req, compress, restart)

        LOG.critical("\nEmails synchronisation operation performed in %s.\n" % (timer.seconds_to_human_time(timer.elapsed())))

        return imap_ids

        

    def sync(self, imap_req, compress_on_disk = True, \
             db_cleaning = False, ownership_checking = True, \
            restart = False, emails_only = False, chats_only = False):
        """
           sync mode 
        """
        #check ownership to have one email per db unless user wants different
        #save the owner if new
        self._check_email_db_ownership(ownership_checking)
          
        if not compress_on_disk:
            LOG.critical("Disable compression when storing emails.")
            
        if self.use_encryption:
            LOG.critical("Encryption activated. All emails will be encrypted before to be stored.")
            LOG.critical("Please take care of the encryption key stored in (%s) or all"\
                         " your stored emails will become unreadable." \
                         % (gmvault_db.GmailStorer.get_encryption_key_path(self.db_root_dir)))
        
        self.error_report['operation'] = 'Sync'
        
        self.timer.start() #start syncing emails
        
        now = datetime.datetime.now()
        LOG.critical("Start synchronization (%s).\n" % (now.strftime('%Y-%m-%dT%Hh%Mm%Ss')))
        
        if not chats_only:
            # backup emails
            LOG.critical("Start emails synchronization.")
            self._sync_emails(imap_req, compress = compress_on_disk, restart = restart)
        else:
            LOG.critical("Skip emails synchronization.\n")
        
        if not emails_only:
            # backup chats
            LOG.critical("Start chats synchronization.")
            self._sync_chats(imap_req, compress = compress_on_disk, restart = restart)
        else:
            LOG.critical("\nSkip chats synchronization.\n")
        
        #delete supress emails from DB since last sync
        self.check_clean_db(db_cleaning)
       
        LOG.debug("Sync operation performed in %s.\n" \
                     % (self.timer.seconds_to_human_time(self.timer.elapsed())))
        self.error_report["operation_time"] = self.timer.seconds_to_human_time(self.timer.elapsed())
        
        #update number of reconnections
        self.error_report["reconnections"] = self.src.total_nb_reconns
        
        return self.error_report

    
    def _delete_sync(self, imap_ids, db_gmail_ids, db_gmail_ids_info, msg_type):
        """
           Delete emails or chats from the database if necessary
           imap_ids      : all remote imap_ids to check
           db_gmail_ids_info : info read from metadata
           msg_type : email or chat
        """
        
        # optimize nb of items
        nb_items = self.NB_GRP_OF_ITEMS if len(imap_ids) >= self.NB_GRP_OF_ITEMS else len(imap_ids)
        
        LOG.critical("Call Gmail to check the stored %ss against the Gmail %ss ids and see which ones have been deleted.\n\n"\
                     "This might take a few minutes ...\n" % (msg_type, msg_type)) 
         
        #calculate the list elements to delete
        #query nb_items items in one query to minimise number of imap queries
        for group_imap_id in itertools.izip_longest(fillvalue=None, *[iter(imap_ids)]*nb_items):
            
            # if None in list remove it
            if None in group_imap_id: 
                group_imap_id = [ im_id for im_id in group_imap_id if im_id != None ]
            
            data = self.src.fetch(group_imap_id, imap_utils.GIMAPFetcher.GET_GMAIL_ID)
            
            # syntax for 2.7 set comprehension { data[key][imap_utils.GIMAPFetcher.GMAIL_ID] for key in data }
            # need to create a list for 2.6
            db_gmail_ids.difference_update([data[key][imap_utils.GIMAPFetcher.GMAIL_ID] for key in data ])
            
            if len(db_gmail_ids) == 0:
                break
        
        LOG.critical("Will delete %s %s(s) from gmvault db.\n" % (len(db_gmail_ids), msg_type) )
        for gm_id in db_gmail_ids:
            LOG.critical("gm_id %s not in the Gmail server. Delete it." % (gm_id))
            self.gstorer.delete_emails([(gm_id, db_gmail_ids_info[gm_id])], msg_type)
        
    def search_on_date(self, a_eml_date):
        """
           get eml_date and format it to search 
        """
        imap_date = gmvault_utils.datetime2imapdate(a_eml_date)
        
        imap_req = "SINCE %s" % (imap_date)

        imap_ids = self.src.search({'type':'imap', 'req': imap_req})
        
        return imap_ids
            
    def get_gmails_ids_left_to_sync(self, op_type, imap_ids, imap_req):#pylint:disable-msg=W0613
        """
           Get the ids that still needs to be sync
           Return a list of ids
        """
        filename = self.OP_TO_FILENAME.get(op_type, None)
        
        if not filename:
            raise Exception("Bad Operation (%s) in save_last_id. "\
                  "This should not happen, send the error to the software developers." % (op_type))
        
        filepath = '%s/%s_%s' % (self.gstorer.get_info_dir(), self.login, filename)
        
        if not os.path.exists(filepath):
            LOG.critical("last_id.sync file %s doesn't exist.\nSync the full list of backed up emails." %(filepath))
            return imap_ids
        
        json_obj = json.load(open(filepath, 'r'))
        
        last_id = json_obj['last_id']
        
        last_id_index = -1
        
        new_gmail_ids = imap_ids
        
        try:
            #get imap_id from stored gmail_id
            dummy = self.src.search({'type':'imap', 'req':'X-GM-MSGID %s' % (last_id)})
            
            imap_id = dummy[0]
            
            last_id_index = imap_ids.index(imap_id)
            
            LOG.critical("Restart from gmail id %s (imap id %s)." % (last_id, imap_id))
            
            new_gmail_ids = imap_ids[last_id_index:]   
        except Exception, _: #ignore any exception and try to get all ids in case of problems. pylint:disable=W0703
            #element not in keys return current set of keys
            LOG.critical("Error: Cannot restore from last restore gmail id. It is not in Gmail."\
                         " Sync the complete list of gmail ids requested from Gmail.")
        
        return new_gmail_ids
        
    def check_clean_db(self, db_cleaning):
        """
           Check and clean the database (remove file that are not anymore in Gmail)
        """
        owners = self.gstorer.get_db_owners()
        if not db_cleaning: #decouple the 2 conditions for activating cleaning
            LOG.debug("db_cleaning is off so ignore removing deleted emails from disk.")
            return
        elif len(owners) > 1:
            LOG.critical("The Gmvault db hosts emails from the following accounts: %s.\n"\
                         % (", ".join(owners)))
            
            LOG.critical("Deactivate database cleaning on a multi-owners Gmvault db.")
        
            return
        else:
            LOG.critical("Look for emails/chats that are in the Gmvault db but not in Gmail servers anymore.\n")
            
            #get gmail_ids from db
            LOG.critical("Read all gmail ids from the Gmvault db. It might take a bit of time ...\n")
            
            timer = gmvault_utils.Timer() # needed for enhancing the user information
            timer.start()
            
            db_gmail_ids_info = self.gstorer.get_all_existing_gmail_ids()
        
            LOG.critical("Found %s email(s) in the Gmvault db.\n" % (len(db_gmail_ids_info)) )
        
            #create a set of keys
            db_gmail_ids = set(db_gmail_ids_info.keys())
            
            # get all imap ids in All Mail
            self.src.select_folder('ALLMAIL') #go to all mail
            imap_ids = self.src.search(imap_utils.GIMAPFetcher.IMAP_ALL) #search all
            
            LOG.debug("Got %s emails imap_id(s) from the Gmail Server." % (len(imap_ids)))
            
            #delete supress emails from DB since last sync
            self._delete_sync(imap_ids, db_gmail_ids, db_gmail_ids_info, 'email')
            
            # get all chats ids
            if self.src.is_visible('CHATS'):
            
                db_gmail_ids_info = self.gstorer.get_all_chats_gmail_ids()
                
                LOG.critical("Found %s chat(s) in the Gmvault db.\n" % (len(db_gmail_ids_info)) )
                
                self.src.select_folder('CHATS') #go to chats
                chat_ids = self.src.search(imap_utils.GIMAPFetcher.IMAP_ALL)
                
                db_chat_ids = set(db_gmail_ids_info.keys())
                
                LOG.debug("Got %s chat imap_ids from the Gmail Server." % (len(chat_ids)))
            
                #delete supress emails from DB since last sync
                self._delete_sync(chat_ids, db_chat_ids, db_gmail_ids_info , 'chat')
            else:
                LOG.critical("Chats IMAP Directory not visible on Gmail. Ignore deletion of chats.")
                
            
            LOG.critical("\nDeletion checkup done in %s." % (timer.elapsed_human_time()))
            
    
    def remote_sync(self):
        """
           Sync with a remote source (IMAP mirror or cloud storage area)
        """
        #sync remotely 
        pass
        
    
    def save_lastid(self, op_type, gm_id, eml_date = None, imap_req = None):#pylint:disable-msg=W0613
        """
           Save the passed gmid in last_id.restore
           For the moment reopen the file every time
        """
        
        filename = self.OP_TO_FILENAME.get(op_type, None)
        
        if not filename:
            raise Exception("Bad Operation (%s) in save_last_id. "\
                            "This should not happen, send the error to the software developers." % (op_type))
        
        filepath = '%s/%s_%s' % (self.gstorer.get_info_dir(), self.login, filename)  
        
        the_fd = open(filepath, 'w')
        
        #json.dump({
        #            'last_id' : gm_id,
        #            'date'    : gmvault_utils.datetime2e(eml_date) if eml_date else None,
        #            'req'     : imap_req 
        #          }, the_fd)
        
        json.dump({
                    'last_id' : gm_id,
                  }, the_fd)
        
        the_fd.close()
        
    def get_gmails_ids_left_to_restore(self, op_type, db_gmail_ids_info):
        """
           Get the ids that still needs to be restored
           Return a dict key = gm_id, val = directory
        """
        filename = self.OP_TO_FILENAME.get(op_type, None)
        
        if not filename:
            raise Exception("Bad Operation (%s) in save_last_id. This should not happen,"\
                            " send the error to the software developers." % (op_type))
        
        
        #filepath = '%s/%s_%s' % (gmvault_utils.get_home_dir_path(), self.login, filename)
        filepath = '%s/%s_%s' % (self.gstorer.get_info_dir(), self.login, filename)
        
        if not os.path.exists(filepath):
            LOG.critical("last_id restore file %s doesn't exist.\nRestore the full list of backed up emails." %(filepath))
            return db_gmail_ids_info
        
        json_obj = json.load(open(filepath, 'r'))
        
        last_id = json_obj['last_id']
        
        last_id_index = -1
        try:
            keys = db_gmail_ids_info.keys()
            last_id_index = keys.index(last_id)
            LOG.critical("Restart from gmail id %s." % (last_id))
        except ValueError, _:
            #element not in keys return current set of keys
            LOG.error("Cannot restore from last restore gmail id. It is not in the disk database.")
        
        new_gmail_ids_info = collections_utils.OrderedDict()
        if last_id_index != -1:
            for key in db_gmail_ids_info.keys()[last_id_index+1:]:
                new_gmail_ids_info[key] =  db_gmail_ids_info[key]
        else:
            new_gmail_ids_info = db_gmail_ids_info    
            
        return new_gmail_ids_info 
           
    def restore(self, pivot_dir = None, extra_labels = [], \
                restart = False, emails_only = False, chats_only = False): #pylint:disable=W0102
        """
           Restore emails in a gmail account
        """
        
        self.error_report['operation'] = 'Sync'
        self.timer.start() #start restoring
        
        now = datetime.datetime.now()
        LOG.critical("Start restoration (%s).\n" % (now.strftime('%Y-%m-%dT%Hh%Mm%Ss')))
        
        if not chats_only:
            # backup emails
            LOG.critical("Start emails restoration.\n")
            
            if pivot_dir:
                LOG.critical("Quick mode activated. Will only restore all emails since %s.\n" % (pivot_dir))
            
            self.restore_emails(pivot_dir, extra_labels, restart)
        else:
            LOG.critical("Skip emails restoration.\n")
        
        if not emails_only:
            # backup chats
            LOG.critical("Start chats restoration.\n")
            self.restore_chats(extra_labels, restart)
        else:
            LOG.critical("Skip chats restoration.\n")
        
        LOG.debug("Restore operation performed in %s.\n" \
                     % (self.timer.seconds_to_human_time(self.timer.elapsed())))
        
        self.error_report["operation_time"] = self.timer.seconds_to_human_time(self.timer.elapsed())
        
        #update number of reconnections
        self.error_report["reconnections"] = self.src.total_nb_reconns
        
        return self.error_report
       
    def restore_chats(self, extra_labels = [], restart = False): #pylint:disable=W0102
        """
           restore chats
        """
        LOG.critical("Restore chats in gmail account %s." % (self.login) ) 
                
        LOG.critical("Read chats info from %s gmvault-db." % (self.db_root_dir))
        
        #get gmail_ids from db
        db_gmail_ids_info = self.gstorer.get_all_chats_gmail_ids()
        
        LOG.critical("Total number of chats to restore %s." % (len(db_gmail_ids_info.keys())))
        
        if restart:
            db_gmail_ids_info = self.get_gmails_ids_left_to_restore(self.OP_CHAT_RESTORE, db_gmail_ids_info)
        
        total_nb_emails_to_restore = len(db_gmail_ids_info)
        LOG.critical("Got all chats id left to restore. Still %s chats to do.\n" % (total_nb_emails_to_restore) )
        
        existing_labels     = set() #set of existing labels to not call create_gmail_labels all the time
        reserved_labels_map = gmvault_utils.get_conf_defaults().get_dict("Restore", "reserved_labels_map", \
                              { u'migrated' : u'gmv-migrated', u'\muted' : u'gmv-muted' })
        nb_emails_restored  = 0  #to count nb of emails restored
        labels_to_apply     = collections_utils.SetMultimap()

        #get all mail folder name
        all_mail_name = self.src.get_folder_name("ALLMAIL")
        
        # go to DRAFTS folder because if you are in ALL MAIL when uploading emails it is very slow
        folder_def_location = gmvault_utils.get_conf_defaults().get("General", "restore_default_location", "DRAFTS")
        self.src.select_folder(folder_def_location)
        
        timer = gmvault_utils.Timer() # local timer for restore emails
        timer.start()
        
        nb_items = gmvault_utils.get_conf_defaults().get_int("General", "nb_messages_per_restore_batch", 100) 
        
        for group_imap_ids in itertools.izip_longest(fillvalue=None, *[iter(db_gmail_ids_info)]*nb_items): 

            last_id = group_imap_ids[-1] #will be used to save the last id
            #remove all None elements from group_imap_ids
            group_imap_ids = itertools.ifilter(lambda x: x != None, group_imap_ids)
           
            labels_to_create    = set(extra_labels) #create label set, add xtra labels in set
            
            LOG.critical("Processing next batch of %s chats.\n" % (nb_items))
            
            # unbury the metadata for all these emails
            for gm_id in group_imap_ids:    
                try:
                    email_meta, email_data = self.gstorer.unbury_email(gm_id)
                    
                    LOG.critical("Pushing chat content with id %s." % (gm_id))
                    LOG.debug("Subject = %s." % (email_meta[self.gstorer.SUBJECT_K]))
                    
                    # push data in gmail account and get uids
                    imap_id = self.src.push_data(all_mail_name, email_data, \
                                    email_meta[self.gstorer.FLAGS_K] , \
                                    email_meta[self.gstorer.INT_DATE_K] )      
                
                    #labels for this email => real_labels U extra_labels
                    labels = set(email_meta[self.gstorer.LABELS_K])
                    
                    # add in the labels_to_create struct
                    for label in labels:
                        LOG.debug("label = %s\n" % (label))
                        if label.lower() in reserved_labels_map.keys(): #exclude creation of migrated label
                            n_label = reserved_labels_map.get(label.lower(), "gmv-default-label")
                            LOG.info("Apply label '%s' instead of '%s' (lower or uppercase)"\
                                     " because it is a Gmail reserved label." % (n_label, label))
                            label = n_label
                        labels_to_apply[str(label)] = imap_id #add in multimap
            
                    # get list of labels to create (do a union with labels to create)
                    #labels_to_create.update([ label for label in labels if label not in existing_labels]) 
                    labels_to_create.update([ label for label in labels_to_apply.keys() \
                                              if label not in existing_labels])                  

                    for ex_label in extra_labels: 
                        labels_to_apply[ex_label] = imap_id
                
                except Exception, err:
                    handle_restore_imap_error(err, gm_id, db_gmail_ids_info, self)

            #create the non existing labels and update existing labels
            if len(labels_to_create) > 0:
                LOG.debug("Labels creation tentative for chats ids %s." % (group_imap_ids))
                existing_labels = self.src.create_gmail_labels(labels_to_create, existing_labels)
                
            # associate labels with emails
            LOG.critical("Applying labels to the current batch of chats.")
            try:
                LOG.debug("Changing directory. Going into ALLMAIL")
                self.src.select_folder('ALLMAIL') #go to ALL MAIL to make STORE usable
                for label in labels_to_apply.keys():
                    self.src.apply_labels_to(labels_to_apply[label], [label]) 
            except Exception, err:
                LOG.error("Problem when applying labels %s to the following ids: %s" %(label, labels_to_apply[label]), err)
                if isinstance(err, imaplib.IMAP4.abort) and str(err).find("=> Gmvault ssl socket error: EOF") >= 0:
                    # if this is a Gmvault SSL Socket error ignore labelling and continue the restore
                    LOG.critical("Ignore labelling")
                    LOG.critical("Disconnecting and reconnecting to restart cleanly.")
                    self.src.reconnect() #reconnect
                else:
                    raise err
            finally:
                self.src.select_folder(folder_def_location) # go back to an empty DIR (Drafts) to be fast
                labels_to_apply = collections_utils.SetMultimap() #reset label to apply
            
            nb_emails_restored += nb_items
                
            #indicate every 10 messages the number of messages left to process
            left_emails = (total_nb_emails_to_restore - nb_emails_restored)
            
            if (left_emails > 0): 
                elapsed = timer.elapsed() #elapsed time in seconds
                LOG.critical("\n== Processed %d chats in %s. %d left to be restored "\
                             "(time estimate %s).==\n" % \
                             (nb_emails_restored, timer.seconds_to_human_time(elapsed), \
                              left_emails, timer.estimate_time_left(nb_emails_restored, elapsed, left_emails)))
            
            # save id every nb_items restored emails
            # add the last treated gm_id
            self.save_lastid(self.OP_EMAIL_RESTORE, last_id)
            
        return self.error_report 
                    
    def restore_emails(self, pivot_dir = None, extra_labels = [], restart = False):
        """
           restore emails in a gmail account using batching to group restore
           If you are not in "All Mail" Folder, it is extremely fast to push emails.
           But it is not possible to reapply labels if you are not in All Mail because the uid which is returned
           is dependant on the folder. On the other hand, you can restore labels in batch which would help gaining lots of time.
           The idea is to get a batch of 50 emails and push them all in the mailbox one by one and get the uid for each of them.
           Then create a dict of labels => uid_list and for each label send a unique store command after having changed dir
        """
        LOG.critical("Restore emails in gmail account %s." % (self.login) ) 
        
        LOG.critical("Read email info from %s gmvault-db." % (self.db_root_dir))
        
        #get gmail_ids from db
        db_gmail_ids_info = self.gstorer.get_all_existing_gmail_ids(pivot_dir)
        
        LOG.critical("Total number of elements to restore %s." % (len(db_gmail_ids_info.keys())))
        
        if restart:
            db_gmail_ids_info = self.get_gmails_ids_left_to_restore(self.OP_EMAIL_RESTORE, db_gmail_ids_info)
        
        total_nb_emails_to_restore = len(db_gmail_ids_info)
        
        LOG.critical("Got all emails id left to restore. Still %s emails to do.\n" % (total_nb_emails_to_restore) )
        
        existing_labels     = set() #set of existing labels to not call create_gmail_labels all the time
        reserved_labels_map = gmvault_utils.get_conf_defaults().get_dict("Restore", "reserved_labels_map", { u'migrated' : u'gmv-migrated', u'\muted' : u'gmv-muted' })
        nb_emails_restored  = 0  #to count nb of emails restored
        labels_to_apply     = collections_utils.SetMultimap()

        #get all mail folder name
        all_mail_name = self.src.get_folder_name("ALLMAIL")
        
        # go to DRAFTS folder because if you are in ALL MAIL when uploading emails it is very slow
        folder_def_location = gmvault_utils.get_conf_defaults().get("General", "restore_default_location", "DRAFTS")
        self.src.select_folder(folder_def_location)
        
        timer = gmvault_utils.Timer() # local timer for restore emails
        timer.start()
        
        nb_items = gmvault_utils.get_conf_defaults().get_int("General", "nb_messages_per_restore_batch", 80) 
        
        for group_imap_ids in itertools.izip_longest(fillvalue=None, *[iter(db_gmail_ids_info)]*nb_items): 
            
            last_id = group_imap_ids[-1] #will be used to save the last id
            #remove all None elements from group_imap_ids
            group_imap_ids = itertools.ifilter(lambda x: x != None, group_imap_ids)
           
            labels_to_create    = set(extra_labels) #create label set and add extra labels to apply to all emails
            
            LOG.critical("Processing next batch of %s emails.\n" % (nb_items))
            
            # unbury the metadata for all these emails
            for gm_id in group_imap_ids:    
                try:
                    email_meta, email_data = self.gstorer.unbury_email(gm_id)
                    
                    LOG.critical("Pushing email body with id %s." % (gm_id))
                    LOG.debug("Subject = %s." % (email_meta[self.gstorer.SUBJECT_K]))
                    
                    # push data in gmail account and get uids
                    imap_id = self.src.push_data(all_mail_name, email_data, \
                                    email_meta[self.gstorer.FLAGS_K] , \
                                    email_meta[self.gstorer.INT_DATE_K] )      
                
                    #labels for this email => real_labels U extra_labels
                    labels = set(email_meta[self.gstorer.LABELS_K])

                    # add in the labels_to_create struct
                    for label in labels:
                        if label != "\\Starred":
                            #LOG.debug("label = %s\n" % (label.encode('utf-8')))
                            LOG.debug("label = %s\n" % (label))
                            if label.lower() in reserved_labels_map.keys(): #exclude creation of migrated label
                                n_label = reserved_labels_map.get(label.lower(), "gmv-default-label")
                                LOG.info("Apply label '%s' instead of '%s' (lower or uppercase)"\
                                 " because it is a Gmail reserved label." % (n_label, label)) 
                                label = n_label
                            labels_to_apply[label] = imap_id #add item in multimap
            
                    # get list of labels to create (do a union with labels to create)
                    #labels_to_create.update([ label for label in labels if label not in existing_labels]) 
                    labels_to_create.update([ label for label in labels_to_apply.keys() \
                                              if label not in existing_labels])                      

                    for ex_label in extra_labels: 
                        labels_to_apply[ex_label] = imap_id
                
                except Exception, err:
                    handle_restore_imap_error(err, gm_id, db_gmail_ids_info, self)

            #create the non existing labels and update existing labels
            if len(labels_to_create) > 0:
                LOG.debug("Labels creation tentative for emails with ids %s." % (group_imap_ids))
                existing_labels = self.src.create_gmail_labels(labels_to_create, existing_labels)
                
            # associate labels with emails
            LOG.critical("Applying labels to the current batch of emails.")

            try:
                LOG.debug("Changing directory. Going into ALLMAIL")
                the_timer = gmvault_utils.Timer()
                the_timer.start()
                self.src.select_folder('ALLMAIL') #go to ALL MAIL to make STORE usable
                LOG.debug("Changed dir. Operation time = %s ms" % (the_timer.elapsed_ms()))
                for label in labels_to_apply.keys():
                    self.src.apply_labels_to(labels_to_apply[label], [label]) 
            except Exception, err:
                LOG.error("Problem when applying labels %s to the following ids: %s" %(label, labels_to_apply[label]), err)
                LOG.error("Problem when applying labels.", err)
                if isinstance(err, imaplib.IMAP4.abort) and str(err).find("=> Gmvault ssl socket error: EOF") >= 0:
                    # if this is a Gmvault SSL Socket error ignore labelling and continue the restore
                    LOG.critical("Ignore labelling")
                    LOG.critical("Disconnecting and reconnecting to restart cleanly.")
                    self.src.reconnect() #reconnect
                else:
                    raise err
            finally:
                self.src.select_folder(folder_def_location) # go back to an empty DIR (Drafts) to be fast
                labels_to_apply = collections_utils.SetMultimap() #reset label to apply
            
            nb_emails_restored += nb_items
                
            #indicate every 10 messages the number of messages left to process
            left_emails = (total_nb_emails_to_restore - nb_emails_restored)
            
            if (left_emails > 0): 
                elapsed = timer.elapsed() #elapsed time in seconds
                LOG.critical("\n== Processed %d emails in %s. %d left to be restored "\
                             "(time estimate %s). ==\n" % \
                             (nb_emails_restored, timer.seconds_to_human_time(elapsed), \
                              left_emails, timer.estimate_time_left(nb_emails_restored, elapsed, left_emails)))
            
            # save id every 50 restored emails
            # add the last treated gm_id
            self.save_lastid(self.OP_EMAIL_RESTORE, last_id)
            
        return self.error_report 
        

########NEW FILE########
__FILENAME__ = gmvault_const
# -*- coding: utf-8 -*-
'''
    Gmvault: a tool to backup and restore your gmail account.
    Copyright (C) <2011-2013>  <guillaume Aubert (guillaume dot aubert at gmail do com)>

    This program is free software: you can redistribute it and/or modify
    it under the terms of the GNU Affero General Public License as
    published by the Free Software Foundation, either version 3 of the
    License, or (at your option) any later version.

    This program is distributed in the hope that it will be useful,
    but WITHOUT ANY WARRANTY; without even the implied warranty of
    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
    GNU Affero General Public License for more details.

    You should have received a copy of the GNU Affero General Public License
    along with this program.  If not, see <http://www.gnu.org/licenses/>.

'''

# Gmvault constants

GMAIL_UNLOCAL_CHATS = [
                     u'[Gmail]/Chats', u'[Google Mail]/Chats', #en, es, ger, portuguese
                     u'[Gmail]/Chat', u'[Google Mail]/Chat', #it
                     u'[Google Mail]/Tous les chats', u'[Gmail]/Tous les chats', # french
                     u'[Gmail]/Чаты', u'[Google Mail]/Чаты', # russian
                     u'[Google Mail]/Czat', u'[Gmail]/Czat', # polish
                     u'[Google Mail]/Bate-papos', u'[Gmail]/Bate-papos', #portuguese brazil
                    ]   # unlocalised Chats names

#The default conf file
DEFAULT_CONF_FILE = """#~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
#  Gmvault Configuration file containing Gmvault defaults.
#  DO NOT CHANGE IT IF YOU ARE NOT AN ADVANCED USER
#~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

[Sync]
quick_days=10

[Restore]
# it is 10 days but currently it will always be the current month or the last 2 months
# the notion of days is not yet apparent in restore (only months).
quick_days=10
reserved_labels_map = { u'migrated' : u'gmv-migrated', u'\muted' : u'gmv-muted' }

[General]
limit_per_chat_dir=2000
errors_if_chat_not_visible=False
nb_messages_per_batch=500
nb_messages_per_restore_batch=80
restore_default_location=DRAFTS
keep_in_bin=False
enable_imap_compression=True

[Localisation]
#example with Russian
chat_folder=[ u'[Google Mail]/Чаты', u'[Gmail]/Чаты' ]
#uncomment if you need to force the term_encoding
#term_encoding='utf-8'

#Do not touch any parameters below as it could force an overwrite of this file
[VERSION]
conf_version=1.8.1

#set environment variables for the program locally
#they will be read only once the conf file has been loaded
[ENV]
#by default it is ~/.gmvault
GMV_IMAP_DEBUG=0

"""

########NEW FILE########
__FILENAME__ = gmvault_db
'''
    Gmvault: a tool to backup and restore your gmail account.
    Copyright (C) <2011-2013>  <guillaume Aubert (guillaume dot aubert at gmail do com)>

    This program is free software: you can redistribute it and/or modify
    it under the terms of the GNU Affero General Public License as
    published by the Free Software Foundation, either version 3 of the
    License, or (at your option) any later version.

    This program is distributed in the hope that it will be useful,
    but WITHOUT ANY WARRANTY; without even the implied warranty of
    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
    GNU Affero General Public License for more details.

    You should have received a copy of the GNU Affero General Public License
    along with this program.  If not, see <http://www.gnu.org/licenses/>.

'''
import json
import gzip
import re
import os
import itertools
import fnmatch
import shutil

import gmv.blowfish as blowfish
import gmv.log_utils as log_utils

import gmv.collections_utils as collections_utils
import gmv.gmvault_utils as gmvault_utils
import gmv.imap_utils as imap_utils
import gmv.credential_utils as credential_utils

LOG = log_utils.LoggerFactory.get_logger('gmvault_db')
            
class GmailStorer(object): #pylint:disable=R0902,R0904,R0914
    '''
       Store emails on disk
    ''' 
    DATA_FNAME     = "%s/%s.eml"
    METADATA_FNAME = "%s/%s.meta"
    CHAT_GM_LABEL  = "gmvault-chats"
    
    ID_K         = 'gm_id'
    EMAIL_K      = 'email'
    THREAD_IDS_K = 'thread_ids'
    LABELS_K     = 'labels'
    INT_DATE_K   = 'internal_date'
    FLAGS_K      = 'flags'
    SUBJECT_K    = 'subject'
    MSGID_K      = 'msg_id'
    XGM_RECV_K   = 'x_gmail_received'
     
    HF_MSGID_PATTERN       = r"[M,m][E,e][S,s][S,s][a,A][G,g][E,e]-[I,i][D,d]:\s+<(?P<msgid>.*)>"
    HF_SUB_PATTERN         = r"[S,s][U,u][b,B][J,j][E,e][C,c][T,t]:\s+(?P<subject>.*)\s*"
    HF_XGMAIL_RECV_PATTERN = r"[X,x]-[G,g][M,m][A,a][I,i][L,l]-[R,r][E,e][C,c][E,e][I,i][V,v][E,e][D,d]:\s+(?P<received>.*)\s*"
    
    HF_MSGID_RE          = re.compile(HF_MSGID_PATTERN)
    HF_SUB_RE            = re.compile(HF_SUB_PATTERN)
    HF_XGMAIL_RECV_RE    = re.compile(HF_XGMAIL_RECV_PATTERN)
    
    ENCRYPTED_PATTERN = r"[\w+,\.]+crypt[\w,\.]*"
    ENCRYPTED_RE      = re.compile(ENCRYPTED_PATTERN)
    
    
    DB_AREA                    = 'db'
    QUARANTINE_AREA            = 'quarantine'
    CHATS_AREA                 = 'chats'
    BIN_AREA                   = 'bin'
    SUB_CHAT_AREA              = 'chats/%s'
    INFO_AREA                  = '.info'  # contains metadata concerning the database
    ENCRYPTION_KEY_FILENAME    = '.storage_key.sec'
    OLD_EMAIL_OWNER            = '.email_account.info' #deprecated
    EMAIL_OWNER                = '.owner_account.info'
    GMVAULTDB_VERSION          = '.gmvault_db_version.info'   
    
    def __init__(self, a_storage_dir, encrypt_data = False):
        """
           Store on disks
           args:
              a_storage_dir: Storage directory
              a_use_encryption: Encryption key. If there then encrypt
        """
        self._top_dir = a_storage_dir
        
        self._db_dir          = '%s/%s' % (a_storage_dir, GmailStorer.DB_AREA)
        self._quarantine_dir  = '%s/%s' % (a_storage_dir, GmailStorer.QUARANTINE_AREA)
        self._info_dir        = '%s/%s' % (a_storage_dir, GmailStorer.INFO_AREA)
        self._chats_dir       = '%s/%s' % (self._db_dir, GmailStorer.CHATS_AREA)
        self._bin_dir         = '%s/%s' % (a_storage_dir, GmailStorer.BIN_AREA)
        
        self._sub_chats_dir   = None
        self._sub_chats_inc   = -1
        self._sub_chats_nb    = -1
        
        self._limit_per_chat_dir = gmvault_utils.get_conf_defaults().getint("General", "limit_per_chat_dir", 1500)
        
        #make dirs
        if not os.path.exists(self._db_dir):
            LOG.critical("No Storage DB in %s. Create it.\n" % (a_storage_dir))
        
        gmvault_utils.makedirs(self._db_dir)
        gmvault_utils.makedirs(self._chats_dir)
        gmvault_utils.makedirs(self._quarantine_dir)
        gmvault_utils.makedirs(self._info_dir)
        
        self.fsystem_info_cache = {}
        
        self._encrypt_data   = encrypt_data
        self._encryption_key = None
        self._cipher         = None
        
        #add version if it is needed to migrate gmvault-db in the future
        self._create_gmvault_db_version()
        
        
    def _init_sub_chats_dir(self):
        """
           get info from existing sub chats
        """
        nb_to_dir = {}
        
        LOG.debug("LIMIT_PER_CHAT_DIR = %s" % (self._limit_per_chat_dir) )
        
        if os.path.exists(self._chats_dir):
            dirs = os.listdir(self._chats_dir)
            for the_dir in dirs:
                the_split = the_dir.split("-")
                if len(the_split) != 2:
                    raise Exception("Should get 2 elements in %s" % (the_split))
                
                nb_to_dir[int(the_split[1])] = the_dir
                
            
            if len(nb_to_dir) == 0:
                # no sub dir yet. Set it up
                self._sub_chats_nb  = 0
                self._sub_chats_inc = 1
                self._sub_chats_dir = self.SUB_CHAT_AREA % ("subchats-%s" % (self._sub_chats_inc))
                gmvault_utils.makedirs("%s/%s" % (self._db_dir, self._sub_chats_dir))
            
            # treat when more than limit chats in max dir 
            # treat when no dirs
            # add limit  as attribute limit_per_dir = 2000
            else:
                the_max = max(nb_to_dir)
                files = os.listdir("%s/%s" % (self._chats_dir, nb_to_dir[the_max]))
                self._sub_chats_nb  = len(files)/2
                self._sub_chats_inc = the_max
                self._sub_chats_dir = self.SUB_CHAT_AREA % nb_to_dir[the_max] 
            
        
    def get_sub_chats_dir(self):
        """
           Get sub_chats_dir
        """
        if self._sub_chats_inc == -1:
            self._init_sub_chats_dir()
         
        if self._sub_chats_nb >= self._limit_per_chat_dir:
            self._sub_chats_inc += 1
            
            self._sub_chats_nb  = 1 
            
            self._sub_chats_dir = self.SUB_CHAT_AREA % ("subchats-%s" % (self._sub_chats_inc))
            gmvault_utils.makedirs('%s/%s' % (self._db_dir, self._sub_chats_dir))
            
            return self._sub_chats_dir
        else:
            self._sub_chats_nb += 1
            return self._sub_chats_dir
    
    def _create_gmvault_db_version(self):
        """
           Create the Gmvault database version if it doesn't already exist
        """
        version_file = '%s/%s' % (self._info_dir, self.GMVAULTDB_VERSION)
        if not os.path.exists(version_file):
            the_fd = open(version_file, "w+")
            the_fd.write(gmvault_utils.GMVAULT_VERSION)
            the_fd.close()
    
    def store_db_owner(self, email_owner):
        """
           Store the email owner in .info dir. This is used to avoid synchronizing multiple email accounts in gmvault-db.
           Always wipe out completly the file
        """
        owners = self.get_db_owners()
        
        if email_owner not in owners:
            owners.append(email_owner)
            the_fd = open('%s/%s' % (self._info_dir, self.EMAIL_OWNER), "w+")
            json.dump(owners, the_fd, ensure_ascii = False)
            the_fd.flush()
            the_fd.close()
        
    
    def get_db_owners(self):
        """
           Get the email owner for the gmvault-db. Because except in particular cases, the db will be only linked to one meail.
        """
        fname = '%s/%s' % (self._info_dir, self.EMAIL_OWNER)
        if os.path.exists(fname):    
            the_fd = open(fname)
            list_of_owners = json.load(the_fd)
            the_fd.close()
            return list_of_owners
        
        return []
   
    def get_info_dir(self):
        """
           Return the info dir of gmvault-db
        """ 
        return self._info_dir
        
    def get_encryption_cipher(self):
        """
           Return the cipher to encrypt an decrypt.
           If the secret key doesn't exist, it will be generated.
        """
        if not self._cipher:
            if not self._encryption_key:
                self._encryption_key = credential_utils.CredentialHelper.get_secret_key('%s/%s' \
                % (self._info_dir, self.ENCRYPTION_KEY_FILENAME))
            
            #create blowfish cipher if data needs to be encrypted
            self._cipher = blowfish.Blowfish(self._encryption_key)
        
        return self._cipher
        
    @classmethod
    def get_encryption_key_path(cls, a_root_dir):
        """
           Return the path of the encryption key.
           This is used to print that information to the user
        """
        return  '%s/%s/%s' % (a_root_dir, cls.INFO_AREA, cls.ENCRYPTION_KEY_FILENAME)
    
    @classmethod
    def get_encryption_key(cls, a_info_dir):
        """
           Return or generate the encryption key if it doesn't exist
        """
        return credential_utils.CredentialHelper.get_secret_key('%s/%s' % (a_info_dir, cls.ENCRYPTION_KEY_FILENAME))
    
    @classmethod
    def parse_header_fields(cls, header_fields):
        """
           extract subject and message ids from the given header fields 
        """
        subject = None
        msgid   = None
        x_gmail_recv = None
        
        # look for subject
        matched = GmailStorer.HF_SUB_RE.search(header_fields)
        if matched:
            subject = matched.group('subject').strip()
        
        # look for a msg id
        matched = GmailStorer.HF_MSGID_RE.search(header_fields)
        if matched:
            msgid = matched.group('msgid').strip()

        # look for received xgmail id
        matched = GmailStorer.HF_XGMAIL_RECV_RE.search(header_fields)
        if matched:
            x_gmail_recv = matched.group('received').strip()
        
        return (subject, msgid, x_gmail_recv)
    
    def get_all_chats_gmail_ids(self):
        """
           Get only chats dirs 
        """
        # first create a normal dir and sort it below with an OrderedDict
        # beware orderedDict preserve order by insertion and not by key order
        gmail_ids = {}
        
        chat_dir = '%s/%s' % (self._db_dir, self.CHATS_AREA)
        if os.path.exists(chat_dir):
            the_iter = gmvault_utils.ordered_dirwalk(chat_dir, "*.meta")
        
            #get all ids
            for filepath in the_iter:
                directory, fname = os.path.split(filepath)
                gmail_ids[long(os.path.splitext(fname)[0])] = os.path.basename(directory)

            #sort by key 
            #used own orderedDict to be compliant with version 2.5
            gmail_ids = collections_utils.OrderedDict(sorted(gmail_ids.items(), key=lambda t: t[0]))
        
        return gmail_ids
        
        
    def get_all_existing_gmail_ids(self, pivot_dir = None, ignore_sub_dir = ['chats']): #pylint:disable=W0102
        """
           get all existing gmail_ids from the database within the passed month 
           and all posterior months
        """
        # first create a normal dir and sort it below with an OrderedDict
        # beware orderedDict preserve order by insertion and not by key order
        gmail_ids = {}
        
        if pivot_dir == None:
            #the_iter = gmvault_utils.dirwalk(self._db_dir, "*.meta")
            the_iter = gmvault_utils.ordered_dirwalk(self._db_dir, "*.meta", ignore_sub_dir)
        else:
            
            # get all yy-mm dirs to list
            dirs = gmvault_utils.get_all_dirs_posterior_to(pivot_dir, \
                   gmvault_utils.get_all_dirs_under(self._db_dir, ignore_sub_dir))
            
            #create all iterators and chain them to keep the same interface
            iter_dirs = [gmvault_utils.ordered_dirwalk('%s/%s' \
                        % (self._db_dir, the_dir), "*.meta", ignore_sub_dir) for the_dir in dirs]
            
            the_iter = itertools.chain.from_iterable(iter_dirs)
        
        #get all ids
        for filepath in the_iter:
            directory, fname = os.path.split(filepath)
            gmail_ids[long(os.path.splitext(fname)[0])] = os.path.basename(directory)

        #sort by key 
        #used own orderedDict to be compliant with version 2.5
        gmail_ids = collections_utils.OrderedDict(sorted(gmail_ids.items(), key=lambda t: t[0]))
        
        return gmail_ids
    
    def bury_chat_metadata(self, email_info, local_dir = None):
        """
           Like bury metadata but with an extra label gmvault-chat
        """
        extra_labels = [GmailStorer.CHAT_GM_LABEL]
        return self.bury_metadata(email_info, local_dir, extra_labels)
    
    def bury_metadata(self, email_info, local_dir = None, extra_labels = []): #pylint:disable=W0102
        """
            Store metadata info in .meta file
            Arguments:
             email_info: metadata info
             local_dir : intermdiary dir (month dir)
        """
        if local_dir:
            the_dir = '%s/%s' % (self._db_dir, local_dir)
            gmvault_utils.makedirs(the_dir)
        else:
            the_dir = self._db_dir
         
        meta_path = self.METADATA_FNAME % (the_dir, email_info[imap_utils.GIMAPFetcher.GMAIL_ID])
       
        meta_desc = open(meta_path, 'w')
        
        # parse header fields to extract subject and msgid
        subject, msgid, received = self.parse_header_fields(email_info[imap_utils.GIMAPFetcher.IMAP_HEADER_FIELDS_KEY])
        
        # need to convert labels that are number as string
        # come from imap_lib when label is a number
        labels = []
        for label in  email_info[imap_utils.GIMAPFetcher.GMAIL_LABELS]:
            if isinstance(label, (int, long, float, complex)):
                label = str(label)

            labels.append(unicode(gmvault_utils.remove_consecutive_spaces_and_strip(label)))
        
        labels.extend(extra_labels) #add extra labels
        
        #create json structure for metadata
        meta_obj = { 
                     self.ID_K         : email_info[imap_utils.GIMAPFetcher.GMAIL_ID],
                     self.LABELS_K     : labels,
                     self.FLAGS_K      : email_info[imap_utils.GIMAPFetcher.IMAP_FLAGS],
                     self.THREAD_IDS_K : email_info[imap_utils.GIMAPFetcher.GMAIL_THREAD_ID],
                     self.INT_DATE_K   : gmvault_utils.datetime2e(email_info[imap_utils.GIMAPFetcher.IMAP_INTERNALDATE]),
                     self.FLAGS_K      : email_info[imap_utils.GIMAPFetcher.IMAP_FLAGS],
                     self.SUBJECT_K    : subject,
                     self.MSGID_K      : msgid,
                     self.XGM_RECV_K   : received
                   }
        
        json.dump(meta_obj, meta_desc)
        
        meta_desc.flush()
        meta_desc.close()
         
        return email_info[imap_utils.GIMAPFetcher.GMAIL_ID]
    
    def bury_chat(self, chat_info, local_dir = None, compress = False):   
        """
            Like bury email but with a special label: gmvault-chats
            Arguments:
            chat_info: the chat content
            local_dir: intermediary dir
            compress : if compress is True, use gzip compression
        """
        extra_labels = ['gmvault-chats']
        
        return self.bury_email(chat_info, local_dir, compress, extra_labels)
    
    def bury_email(self, email_info, local_dir = None, compress = False, extra_labels = []): #pylint:disable=W0102
        """
           store all email info in 2 files (.meta and .eml files)
           Arguments:
             email_info: the email content
             local_dir : intermdiary dir (month dir)
             compress  : if compress is True, use gzip compression
        """
        
        if local_dir:
            the_dir = '%s/%s' % (self._db_dir, local_dir)
            gmvault_utils.makedirs(the_dir)
        else:
            the_dir = self._db_dir
        
        data_path = self.DATA_FNAME % (the_dir, email_info[imap_utils.GIMAPFetcher.GMAIL_ID])
        
        # if the data has to be encrypted
        if self._encrypt_data:
            data_path = '%s.crypt' % (data_path)
        
        if compress:
            data_path = '%s.gz' % (data_path)
            data_desc = gzip.open(data_path, 'wb')
        else:
            data_desc = open(data_path, 'wb')
            
        if self._encrypt_data:
            # need to be done for every encryption
            cipher = self.get_encryption_cipher()
            cipher.initCTR()
            data     = cipher.encryptCTR(email_info[imap_utils.GIMAPFetcher.EMAIL_BODY])
            gmvault_utils.buffered_write(data_desc, data) if len(data) > 4194304 else data_desc.write(data)
        else:
            
            data = email_info[imap_utils.GIMAPFetcher.EMAIL_BODY]
            #data_desc.write(data)
            gmvault_utils.buffered_write(data_desc, data) if len(data) > 4194304 else data_desc.write(data)
 
 
        self.bury_metadata(email_info, local_dir, extra_labels)
            
        data_desc.flush()
        data_desc.close()
        
        return email_info[imap_utils.GIMAPFetcher.GMAIL_ID]
    
    def get_directory_from_id(self, a_id, a_local_dir = None):
        """
           If a_local_dir (yy_mm dir) is passed, check that metadata file exists and return dir
           Return the directory path if id located.
           Return None if not found
        """
        filename = '%s.meta' % (a_id)
        
        #local_dir can be passed to avoid scanning the filesystem (because of WIN7 fs weaknesses)
        if a_local_dir:
            the_dir = '%s/%s' % (self._db_dir, a_local_dir)
            if os.path.exists(self.METADATA_FNAME % (the_dir, a_id)):
                return the_dir
            else:
                return None
        
        # first look in cache
        for the_dir in self.fsystem_info_cache:
            if filename in self.fsystem_info_cache[the_dir]:
                return the_dir
        
        #walk the filesystem
        for the_dir, _, files in os.walk(os.path.abspath(self._db_dir)):
            self.fsystem_info_cache[the_dir] = files
            for filename in fnmatch.filter(files, filename):
                return the_dir
        
        return None
    
    def _get_data_file_from_id(self, a_dir, a_id):
        """
           Return data file from the id
        """
        data_p = self.DATA_FNAME % (a_dir, a_id)
        
        # check if encrypted and compressed or not
        if os.path.exists('%s.crypt.gz' % (data_p)):
            data_fd = gzip.open('%s.crypt.gz' % (data_p), 'r')
        elif os.path.exists('%s.gz' % (data_p)):
            data_fd = gzip.open('%s.gz' % (data_p), 'r')
        elif os.path.exists('%s.crypt' % (data_p)):
            data_fd = open('%s.crypt' % (data_p), 'r')
        else:
            data_fd = open(data_p)
        
        return data_fd
    
    def _get_metadata_file_from_id(self, a_dir, a_id):
        """
           metadata file
        """
        meta_p = self.METADATA_FNAME % (a_dir, a_id)
       
        return open(meta_p)
    
    def quarantine_email(self, a_id):
        """
           Quarantine the email
        """
        #get the dir where the email is stored
        the_dir = self.get_directory_from_id(a_id)
        
        data = self.DATA_FNAME % (the_dir, a_id)
        meta = self.METADATA_FNAME % (the_dir, a_id)
        
        # check if encrypted and compressed or not
        if os.path.exists('%s.crypt.gz' % (data)):
            data = '%s.crypt.gz' % (data)
        elif os.path.exists('%s.gz' % (data)):
            data = '%s.gz' % (data)
        elif os.path.exists('%s.crypt' % (data)):
            data = '%s.crypt' % (data)
        
        #remove files if already quarantined
        q_data_path = os.path.join(self._quarantine_dir, os.path.basename(data))
        q_meta_path = os.path.join(self._quarantine_dir, os.path.basename(meta))

        if os.path.exists(q_data_path):
            os.remove(q_data_path)        
        
        if os.path.exists(q_meta_path):
            os.remove(q_meta_path)

        if os.path.exists(data):
            shutil.move(data, self._quarantine_dir)
        else:
            LOG.info("Warning: %s file doesn't exist." % (data))
        
        if os.path.exists(meta):
            shutil.move(meta, self._quarantine_dir)
        else:
            LOG.info("Warning: %s file doesn't exist." % (meta))
        
    def email_encrypted(self, a_email_fn):
        """
           True is filename contains .crypt otherwise False
        """
        basename = os.path.basename(a_email_fn)
        if self.ENCRYPTED_RE.match(basename):
            return True
        else:
            return False
        
    def unbury_email(self, a_id):
        """
           Restore the complete email info from info stored on disk
           Return a tuple (meta, data)
        """
        the_dir = self.get_directory_from_id(a_id)

        data_fd = self._get_data_file_from_id(the_dir, a_id)
        
        if self.email_encrypted(data_fd.name):
            LOG.debug("Restore encrypted email %s" % (a_id))
            # need to be done for every encryption
            cipher = self.get_encryption_cipher()
            cipher.initCTR()
            data = cipher.decryptCTR(data_fd.read())
        else:
            data = data_fd.read()
        
        return (self.unbury_metadata(a_id, the_dir), data)
    
    def unbury_data(self, a_id, a_id_dir = None):
        """
           Get the only the email content from the DB
        """
        if not a_id_dir:
            a_id_dir = self.get_directory_from_id(a_id)
            
        data_fd = self._get_data_file_from_id(a_id_dir, a_id)
        
        if self.email_encrypted(data_fd.name):
            LOG.debug("Restore encrypted email %s" % (a_id))
            # need to be done for every encryption
            cipher = self.get_encryption_cipher()
            cipher.initCTR()
            data = cipher.decryptCTR(data_fd.read())
        else:
            data = data_fd.read()
            
        return data    
        
    def unbury_metadata(self, a_id, a_id_dir = None):
        """
           Get metadata info from DB
        """
        if not a_id_dir:
            a_id_dir = self.get_directory_from_id(a_id)
        
        meta_fd = self._get_metadata_file_from_id(a_id_dir, a_id)
    
        metadata = json.load(meta_fd)
        
        metadata[self.INT_DATE_K] =  gmvault_utils.e2datetime(metadata[self.INT_DATE_K])
        
        # force convertion of labels as string because IMAPClient
        # returns a num when the label is a number (ie. '00000') and handle utf-8
        new_labels = []

        for label in  metadata[self.LABELS_K]:
            if isinstance(label, (int, long, float, complex)):
                label = str(label)
            new_labels.append(unicode(label))
 
        metadata[self.LABELS_K] = new_labels

        return metadata
    
    def delete_emails(self, emails_info, msg_type):
        """
           Delete all emails and metadata with ids
        """
        if msg_type == 'email':
            db_dir = self._db_dir
        else:
            db_dir = self._chats_dir

        move_to_bin = gmvault_utils.get_conf_defaults().get_boolean("General", "keep_in_bin" , False)

        if move_to_bin:
            LOG.critical("Move emails to the bin:%s" % (self._bin_dir))
        
        for (a_id, date_dir) in emails_info:
            
            the_dir = '%s/%s' % (db_dir, date_dir)
            
            data_p      = self.DATA_FNAME % (the_dir, a_id)
            comp_data_p = '%s.gz' % (data_p)
            cryp_comp_data_p = '%s.crypt.gz' % (data_p)
            
            metadata_p  = self.METADATA_FNAME % (the_dir, a_id)

            if move_to_bin:
                #move files to the bin
                gmvault_utils.makedirs(self._bin_dir)

                # create bin filenames
                bin_p          = self.DATA_FNAME % (self._bin_dir, a_id)
                metadata_bin_p = self.METADATA_FNAME % (self._bin_dir, a_id)
                
                if os.path.exists(data_p):
                    os.rename(data_p, bin_p)
                elif os.path.exists(comp_data_p):
                    os.rename(comp_data_p, '%s.gz' % (bin_p))
                elif os.path.exists(cryp_comp_data_p):
                    os.rename(cryp_comp_data_p, '%s.crypt.gz' % bin_p)   
                
                if os.path.exists(metadata_p):
                    os.rename(metadata_p, metadata_bin_p)
            else:
                #delete files if they exists
                if os.path.exists(data_p):
                    os.remove(data_p)
                elif os.path.exists(comp_data_p):
                    os.remove(comp_data_p)
                elif os.path.exists(cryp_comp_data_p):
                    os.remove(cryp_comp_data_p)   
                
                if os.path.exists(metadata_p):
                    os.remove(metadata_p)

########NEW FILE########
__FILENAME__ = gmvault_export
'''
    Gmvault: a tool to backup and restore your gmail account.
    Copyright (C) <2011-2012>  <guillaume Aubert (guillaume dot aubert at gmail do com)>

    This program is free software: you can redistribute it and/or modify
    it under the terms of the GNU General Public License as published by
    the Free Software Foundation, either version 3 of the License, or
    (at your option) any later version.

    This program is distributed in the hope that it will be useful,
    but WITHOUT ANY WARRANTY; without even the implied warranty of
    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
    GNU General Public License for more details.

    You should have received a copy of the GNU General Public License
    along with this program.  If not, see <http://www.gnu.org/licenses/>.
'''
'''
   Export function of Gmvault created by dave@vasilevsky.ca
'''

import os
import re
import mailbox

import imapclient.imap_utf7 as imap_utf7

import gmv.imap_utils as imap_utils
import gmv.log_utils as log_utils
import gmv.gmvault_utils as gmvault_utils
import gmv.gmvault_db as gmvault_db

LOG = log_utils.LoggerFactory.get_logger('gmvault_export')

class GMVaultExporter(object):
    """
       Class hanlding the creation of exports in standard formats
       such as maildir, mbox
    """
    PROGRESS_INTERVAL = 200

    CHATS_FOLDER = 'Chats'
    ARCHIVED_FOLDER = 'Archived' # Mails only in 'All Mail'

    GM_ALL = re.sub(r'^\\', '', imap_utils.GIMAPFetcher.GENERIC_GMAIL_ALL)
    GM_INBOX = 'Inbox'
    GM_SEP = '/'

    GM_SEEN = '\\Seen'
    GM_FLAGGED = '\\Flagged'

    def __init__(self, db_dir, a_mailbox, labels = None):
        """
           constructor
        """
        self.storer = gmvault_db.GmailStorer(db_dir)
        self.mailbox = a_mailbox
        self.labels = labels

    def want_label(self, label):
        """ helper indicating is a label is needed"""
        if self.labels:
            return label in self.labels
        return label != self.GM_ALL

    def export(self):
        """core method for starting the export """
        self.export_ids('emails', self.storer.get_all_existing_gmail_ids(), \
            default_folder = self.GM_ALL, use_labels = True)
        self.export_ids('chats', self.storer.get_all_chats_gmail_ids(), \
            default_folder = self.CHATS_FOLDER, use_labels = False)

    def printable_label_list(self, labels):
        """helper to print a list of labels"""
        labels = [l.encode('ascii', 'backslashreplace') for l in labels]
        return u'; '.join(labels)

    def export_ids(self, kind, ids, default_folder, use_labels):
        """ export organised by ids """
        exported_labels = "default labels"
        if self.labels:
            exported_labels = "labels " + self.printable_label_list(self.labels)
        LOG.critical("Start %s export for %s." % (kind, exported_labels))

        timer = gmvault_utils.Timer()
        timer.start()
        done = 0

        for a_id in ids:
            meta, msg = self.storer.unbury_email(a_id)

            folders = [default_folder]
            if use_labels:
                add_labels = meta[gmvault_db.GmailStorer.LABELS_K]
                if not add_labels:
                    add_labels = [GMVaultExporter.ARCHIVED_FOLDER]
                folders.extend(add_labels)
            folders = [re.sub(r'^\\', '', f) for f in folders]
            folders = [f for f in folders if self.want_label(f)]

            LOG.debug("Processing id %s in labels %s." % \
                (a_id, self.printable_label_list(folders)))
            for folder in folders:
                self.mailbox.add(msg, folder, meta[gmvault_db.GmailStorer.FLAGS_K])

            done += 1
            left = len(ids) - done
            if done % self.PROGRESS_INTERVAL == 0 and left > 0:
                elapsed = timer.elapsed()
                LOG.critical("== Processed %d %s in %s, %d left (time estimate %s). ==\n" % \
                    (done, kind, timer.seconds_to_human_time(elapsed), \
                     left, timer.estimate_time_left(done, elapsed, left)))

        LOG.critical("Export completed in %s." % (timer.elapsed_human_time(),))


class Mailbox(object):
    """ Mailbox abstract class"""
    def add(self, msg, folder, flags):
        raise NotImplementedError('implement in subclass')
    def close(self):
        pass

class Maildir(Mailbox):
    """ Class delaing with the Maildir format """
    def __init__(self, path, separator = '/'):
        self.path = path
        self.subdirs = {}
        self.separator = separator
        if not self.root_is_maildir() and not os.path.exists(self.path):
            os.makedirs(self.path)

    @staticmethod
    def separate(folder, sep):
        """ separate method """
        return folder.replace(GMVaultExporter.GM_SEP, sep)

    def subdir_name(self, folder):
        """get subdir_name """
        return self.separate(folder, self.separator)

    def root_is_maildir(self):
        """check if root is maildir"""
        return False;

    def subdir(self, folder):
        """ return a subdir """
        if folder in self.subdirs:
            return self.subdirs[folder]

        if folder:
            parts = folder.split(GMVaultExporter.GM_SEP)
            parent = GMVaultExporter.GM_SEP.join(parts[:-1])
            self.subdir(parent)
            path = self.subdir_name(folder)
            path = imap_utf7.encode(path)
        else:
            if not self.root_is_maildir():
                return
            path = ''

        abspath = os.path.join(self.path, path)
        sub = mailbox.Maildir(abspath, create = True)
        self.subdirs[folder] = sub
        return sub

    def add(self, msg, folder, flags):
        """ add message in a given subdir """
        mmsg = mailbox.MaildirMessage(msg)

        if GMVaultExporter.GM_SEEN in flags:
            mmsg.set_subdir('cur')
            mmsg.add_flag('S')
        if mmsg.get_subdir() == 'cur' and GMVaultExporter.GM_FLAGGED in flags:
            mmsg.add_flag('F')

        self.subdir(folder).add(mmsg)

class OfflineIMAP(Maildir):
    """ Class dealing with offlineIMAP specificities """
    DEFAULT_SEPARATOR = '.'
    def __init__(self, path, separator = DEFAULT_SEPARATOR):
        super(OfflineIMAP, self).__init__(path, separator = separator)

class Dovecot(Maildir):
    """ Class dealing with Dovecot specificities """
    # See http://wiki2.dovecot.org/Namespaces
    class Layout(object):
        def join(self, parts):
            return self.SEPARATOR.join(parts)
    class FSLayout(Layout):
        SEPARATOR = '/'
    class MaildirPlusPlusLayout(Layout):
        SEPARATOR = '.'
        def join(self, parts):
            return '.' + super(Dovecot.MaildirPlusPlusLayout, self).join(parts)

    DEFAULT_NS_SEP = '.'
    DEFAULT_LISTESCAPE = '\\'

    # The namespace separator cannot be escaped with listescape.
    # Replace it with a two-character escape code.
    DEFAULT_SEP_ESCAPE = "*'"

    def __init__(self, path,
                 layout = MaildirPlusPlusLayout(),
                 ns_sep = DEFAULT_NS_SEP,
                 listescape = DEFAULT_LISTESCAPE,
                 sep_escape = DEFAULT_SEP_ESCAPE):
        super(Dovecot, self).__init__(path, separator = layout.SEPARATOR)
        self.layout = layout
        self.ns_sep = ns_sep
        self.listescape = listescape
        self.sep_escape = sep_escape

    # Escape one character
    def _listescape(self, s, char = None, pattern = None):
        pattern = pattern or re.escape(char)
        esc = "%s%02x" % (self.listescape, ord(char))
        return re.sub(pattern, lambda m: esc, s)

    def _munge_name(self, s):
        # Escape namespace separator: . => *', * => **
        esc = self.sep_escape[0]
        s = re.sub(re.escape(esc), esc * 2, s)
        s = re.sub(re.escape(self.ns_sep), self.sep_escape, s)

        if self.listescape:
            # See http://wiki2.dovecot.org/Plugins/Listescape
            if self.layout.SEPARATOR == '.':
                s = self._listescape(s, '.')
            s = self._listescape(s, '/')
            s = self._listescape(s, '~', r'^~')
        return s

    def subdir_name(self, folder):
        if folder == GMVaultExporter.GM_INBOX:
            return ''

        parts = folder.split(GMVaultExporter.GM_SEP)
        parts = [self._munge_name(n) for n in parts]
        return self.layout.join(parts)

    def root_is_maildir(self):
        return True

class MBox(Mailbox):
    """ Class dealing with MBox specificities """
    def __init__(self, folder):
        self.folder = folder
        self.open = dict()

    def close(self):
        for _, m in self.open.items():
            m.close()

    def subdir(self, label):
        segments = label.split(GMVaultExporter.GM_SEP)
        # Safety first: No unusable directory portions
        segments = [s for s in segments if s != '..' and s != '.']
        real_label = GMVaultExporter.GM_SEP.join(segments)
        if real_label in self.open:
            return self.open[real_label]

        cur_path = self.folder
        label_segments = []
        for s in segments:
            label_segments.append(s)
            cur_label = GMVaultExporter.GM_SEP.join(label_segments)
            if cur_label not in self.open:
                # Create an mbox for intermediate folders, to satisfy
                # Thunderbird import
                if not os.path.exists(cur_path):
                    os.makedirs(cur_path)
                mbox_path = os.path.join(cur_path, s)
                self.open[cur_label] = mailbox.mbox(mbox_path)
            # Use .sbd folders a la Thunderbird, to allow nested folders
            cur_path = os.path.join(cur_path, s + '.sbd')

        return self.open[real_label]

    def add(self, msg, folder, flags):
        mmsg = mailbox.mboxMessage(msg)
        if GMVaultExporter.GM_SEEN in flags:
            mmsg.add_flag('R')
        if GMVaultExporter.GM_FLAGGED in flags:
            mmsg.add_flag('F')
        self.subdir(folder).add(mmsg)

########NEW FILE########
__FILENAME__ = gmvault_utils
# -*- coding: utf-8 -*-
'''
    Gmvault: a tool to backup and restore your gmail account.
    Copyright (C) <2011-2013>  <guillaume Aubert (guillaume dot aubert at gmail do com)>

    This program is free software: you can redistribute it and/or modify
    it under the terms of the GNU Affero General Public License as
    published by the Free Software Foundation, either version 3 of the
    License, or (at your option) any later version.

    This program is distributed in the hope that it will be useful,
    but WITHOUT ANY WARRANTY; without even the implied warranty of
    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
    GNU Affero General Public License for more details.

    You should have received a copy of the GNU Affero General Public License
    along with this program.  If not, see <http://www.gnu.org/licenses/>.

'''
import os

import re
import datetime
import time
import calendar
import fnmatch
import functools

import StringIO
import sys
import traceback
import random 
import locale

import gmv.log_utils as log_utils
import gmv.conf.conf_helper
import gmv.gmvault_const as gmvault_const

LOG = log_utils.LoggerFactory.get_logger('gmvault_utils')

GMVAULT_VERSION = "1.8.1-beta"

class memoized(object): #pylint: disable=C0103
    """Decorator that caches a function's return value each time it is called.
    If called later with the same arguments, the cached value is returned, and
    not re-evaluated.
    """
    def __init__(self, func):
        self.func = func
        self.cache = {}
    def __call__(self, *args):
        try:
            return self.cache[args]
        except KeyError:
            value = self.func(*args)
            self.cache[args] = value
            return value
        except TypeError:
            # uncachable -- for instance, passing a list as an argument.
            # Better to not cache than to blow up entirely.
            return self.func(*args)
    def __repr__(self):
        """Return the function's docstring."""
        return self.func.__doc__
    def __get__(self, obj, objtype):
        """Support instance methods."""
        return functools.partial(self.__call__, obj)
    
class Curry:
    """ Class used to implement the currification (functional programming technic) :
        Create a function from another one by instanciating some of its parameters.
        For example double = curry(operator.mul,2), res = double(4) = 8
    """
    def __init__(self, fun, *args, **kwargs):
        self.fun = fun
        self.pending = args[:]
        self.kwargs = kwargs.copy()
        
    def __call__(self, *args, **kwargs):
        if kwargs and self.kwargs:
            the_kw = self.kwargs.copy()
            the_kw.update(kwargs)
        else:
            the_kw = kwargs or self.kwargs
        return self.fun(*(self.pending + args), **the_kw) #pylint: disable=W0142



LETTERS = 'abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ'
DIGITS = '0123456789'

def make_password(minlength=8, maxlength=16):  
    """
       generate randomw password
    """
    length = random.randint(minlength, maxlength)
    letters = LETTERS + DIGITS 
    return ''.join([random.choice(letters) for _ in range(length)])  



def get_exception_traceback():
    """
            return the exception traceback (stack info and so on) in a string
        
            Args:
               None
               
            Returns:
               return a string that contains the exception traceback
        
            Raises:
               
    """
   
    the_file = StringIO.StringIO()
    exception_type, exception_value, exception_traceback = sys.exc_info() #IGNORE:W0702
    traceback.print_exception(exception_type, exception_value, exception_traceback, file = the_file)
    return the_file.getvalue()


MULTI_SPACES_PATTERN = r"\s{2,}"
MULTI_SPACES_RE = re.compile(MULTI_SPACES_PATTERN, flags=re.U) #to support unicode

def remove_consecutive_spaces_and_strip(a_str):
    """
       Supress consecutive spaces to replace them with a unique one.
       e.g "two  spaces" = "two spaces"
    """
    #return re.sub("\s{2,}", " ", a_str, flags=re.U).strip()
    return MULTI_SPACES_RE.sub(u" ", a_str).strip()

def buffered_write(fd, data, buf_size = 1048576):
    """
       fd: file descriptor where to write
       data: data to write
       buf_size: size of the buffer (default 1MB)
       buffered write handling case when write returns nb of written bytes
       and when write returns None (Linux)
    """
    #LOG.critical("======= In buffered write")
    total_size = len(data)
    wr_bytes = 0
    while wr_bytes < total_size:
        written = fd.write(buffer(data, wr_bytes, buf_size))
        if written:
            wr_bytes += written
        else:
            #if buffer size > left then left else buffer size
            # else buffer size
            left = total_size - wr_bytes
            if left < buf_size:
                wr_bytes += left
            else:
                wr_bytes += buf_size
        
             

TIMER_SUFFIXES = ['y', 'w', 'd', 'h', 'm', 's']

class Timer(object):
    """
       Timer Class to mesure time.
       Possess also few time utilities
    """
    
 
    def __init__(self):
        
        self._start = None
        
    def start(self):
        """
           start the timer
        """
        self._start = time.time()
        
    def reset(self):
        """
           reset the timer to 0
        """
        self._start = time.time()
    
    def elapsed(self):
        """
           return elapsed time in sec
        """
        now = time.time()
        
        return int(round(now - self._start))
    
    def elapsed_ms(self):
        """
          return elapsed time up to micro second
        """
        return time.time() - self._start
    
    def elapsed_human_time(self, suffixes=TIMER_SUFFIXES, add_s=False, separator=' '):#pylint:disable=W0102
        """
        Takes an amount of seconds and turns it into a human-readable amount of time.
        """
        seconds = self.elapsed()
        
        return self.seconds_to_human_time(seconds, suffixes, add_s, separator)

    @classmethod
    def estimate_time_left(cls, nb_elem_done, in_sec, still_to_be_done, in_human_time = True):
        """
           Stupid estimate. Use current time to estimate how long it will take
        """
        if in_human_time:
            return cls.seconds_to_human_time(int(round(float(still_to_be_done * in_sec)/nb_elem_done)))
        else:
            return int(round(float(still_to_be_done * in_sec)/nb_elem_done))
    
    @classmethod
    def seconds_to_human_time(cls, seconds, suffixes=TIMER_SUFFIXES, add_s=False, separator=' '):#pylint:disable=W0102
        """
           convert seconds to human time
        """
        # the formatted time string to be returned
        the_time = []
        
        # the pieces of time to iterate over (days, hours, minutes, etc)
        # - the first piece in each tuple is the suffix (d, h, w)
        # - the second piece is the length in seconds (a day is 60s * 60m * 24h)
        parts = [(suffixes[0], 60 * 60 * 24 * 7 * 52),
              (suffixes[1], 60 * 60 * 24 * 7),
              (suffixes[2], 60 * 60 * 24),
              (suffixes[3], 60 * 60),
              (suffixes[4], 60),
              (suffixes[5], 1)]
        
        if seconds < 1: #less than a second case
            return "less than a second"
        
        # for each time piece, grab the value and remaining seconds, and add it to
        # the time string
        for suffix, length in parts:
            value = seconds / length
            if value > 0:
                seconds = seconds % length
                the_time.append('%s%s' % (str(value),
                               (suffix, (suffix, suffix + 's')[value > 1])[add_s]))
            if seconds < 1:
                break
        
        return separator.join(the_time)

ZERO = datetime.timedelta(0) 
# A UTC class.    
class UTC(datetime.tzinfo):    
    """UTC Timezone"""    
    
    def utcoffset(self, a_dt): #pylint: disable=W0613
        ''' return utcoffset '''  
        return ZERO    
    
    def tzname(self, a_dt): #pylint: disable=W0613
        ''' return tzname '''    
        return "UTC"    
        
    def dst(self, a_dt): #pylint: disable=W0613 
        ''' return dst '''      
        return ZERO  

# pylint: enable-msg=W0613    
UTC_TZ = UTC()

def get_ym_from_datetime(a_datetime):
    """
       return year month from datetime
    """
    if a_datetime:
        return a_datetime.strftime('%Y-%m')
    
    return None

MONTH_CONV = { 1: 'Jan', 4: 'Apr', 6: 'Jun', 7: 'Jul', 10: 'Oct' , 12: 'Dec',
               2: 'Feb', 5: 'May', 8: 'Aug', 9: 'Sep', 11: 'Nov',
               3: 'Mar'}

REVERSE_MONTH_CONV = { 'Jan' : 1, 'Apr' : 4, 'Jun' : 6, 'Jul': 7, 'Oct': 10 , 'Dec':12,
                   'Feb' : 2, 'May' : 5, 'Aug' : 8, 'Sep': 9, 'Nov': 11,
                   'Mar' : 3}


MONTH_YEAR_PATTERN = r'(?P<year>(18|19|[2-5][0-9])\d\d)[-/.](?P<month>(0[1-9]|1[012]|[1-9]))'
MONTH_YEAR_RE = re.compile(MONTH_YEAR_PATTERN)

def compare_yymm_dir(first, second):
    """
       Compare directory names in the form of Year-Month
       Return 1 if first > second
              0 if equal
              -1 if second > first
    """
    
    matched = MONTH_YEAR_RE.match(first)
    
    if matched:
        first_year  = int(matched.group('year'))
        first_month = int(matched.group('month'))
        
        first_val   = (first_year * 1000) + first_month
    else:
        raise Exception("Invalid Year-Month expression (%s). Please correct it to be yyyy-mm" % (first))
        
    matched = MONTH_YEAR_RE.match(second)
    
    if matched:
        second_year  = int(matched.group('year'))
        second_month = int(matched.group('month'))
        
        second_val   = (second_year * 1000) + second_month
    else:
        raise Exception("Invalid Year-Month expression (%s). Please correct it" % (second))
    
    if first_val > second_val:
        return 1
    elif first_val == second_val:
        return 0
    else:
        return -1
    
def cmp_to_key(mycmp):
    """
        Taken from functools. Not in all python versions so had to redefine it
        Convert a cmp= function into a key= function
    """
    class Key(object): #pylint: disable=R0903
        """Key class"""
        def __init__(self, obj, *args): #pylint: disable=W0613
            self.obj = obj
        def __lt__(self, other):
            return mycmp(self.obj, other.obj) < 0
        def __gt__(self, other):
            return mycmp(self.obj, other.obj) > 0
        def __eq__(self, other):
            return mycmp(self.obj, other.obj) == 0
        def __le__(self, other):
            return mycmp(self.obj, other.obj) <= 0
        def __ge__(self, other):
            return mycmp(self.obj, other.obj) >= 0
        def __ne__(self, other):
            return mycmp(self.obj, other.obj) != 0
        def __hash__(self):
            raise TypeError('hash not implemented')
    return Key
    
def get_all_dirs_posterior_to(a_dir, dirs):
    """
           get all directories posterior
    """
    #sort the passed dirs list and return all dirs posterior to a_dir
         
    return [ name for name in sorted(dirs, key=cmp_to_key(compare_yymm_dir))\
             if compare_yymm_dir(a_dir, name) <= 0 ]

def get_all_dirs_under(root_dir, ignored_dirs = []):#pylint:disable=W0102
    """
       Get all directory names under (1 level only) the root dir
       params:
          root_dir   : the dir to look under
          ignored_dir: ignore the dir if it is in this list of dirnames 
    """
    return [ name for name in os.listdir(root_dir) \
             if ( os.path.isdir(os.path.join(root_dir, name)) \
                and (name not in ignored_dirs) ) ]

def datetime2imapdate(a_datetime):
    """
       Transfrom in date format for IMAP Request
    """
    if a_datetime:
        
        month = MONTH_CONV[a_datetime.month]
        
        pattern = '%%d-%s-%%Y' % (month) 
        
        return a_datetime.strftime(pattern)
    

def e2datetime(a_epoch):
    """
        convert epoch time in datetime

            Args:
               a_epoch: the epoch time to convert

            Returns: a datetime
    """

    #utcfromtimestamp is not working properly with a decimals.
    # use floor to create the datetime
#    decim = decimal.Decimal('%s' % (a_epoch)).quantize(decimal.Decimal('.001'), rounding=decimal.ROUND_DOWN)

    new_date = datetime.datetime.utcfromtimestamp(a_epoch)

    return new_date

def datetime2e(a_date):
    """
        convert datetime in epoch
        Beware the datetime as to be in UTC otherwise you might have some surprises
            Args:
               a_date: the datertime to convert

            Returns: a epoch time
    """
    return calendar.timegm(a_date.timetuple())

def contains_any(string, char_set):
    """Check whether 'string' contains ANY of the chars in 'set'"""
    return 1 in [c in string for c in char_set]

def makedirs(a_path):
    """ my own version of makedir """
    
    if os.path.isdir(a_path):
        # it already exists so return
        return
    elif os.path.isfile(a_path):
        raise OSError("a file with the same name as the desired dir, '%s', already exists."%(a_path))

    os.makedirs(a_path)

def __rmgeneric(path, __func__):
    """ private function that is part of delete_all_under """
    try:
        __func__(path)
        #print 'Removed ', path
    except OSError, (_, strerror): #IGNORE:W0612
        print """Error removing %(path)s, %(error)s """ % {'path' : path, 'error': strerror }
            
def delete_all_under(path, delete_top_dir = False):
    """ delete all files and directories under path """

    if not os.path.isdir(path):
        return
    
    files = os.listdir(path)

    for the_f in files:
        fullpath = os.path.join(path, the_f)
        if os.path.isfile(fullpath):
            new_f = os.remove
            __rmgeneric(fullpath, new_f)
        elif os.path.isdir(fullpath):
            delete_all_under(fullpath)
            new_f = os.rmdir
            __rmgeneric(fullpath, new_f)
    
    if delete_top_dir:
        os.rmdir(path)
        
def ordered_dirwalk(a_dir, a_file_wildcards= '*', a_dir_ignore_list = [], sort_func = sorted):#pylint:disable=W0102
    """
        Walk a directory tree, using a generator.
        This implementation returns only the files in all the subdirectories.
        Beware, this is a generator.
        Args:
        a_dir: A root directory from where to list
        a_wildcards: Filtering wildcards a la unix
    """

    
    sub_dirs = []
    for the_file in sort_func(os.listdir(a_dir)):
        fullpath = os.path.join(a_dir, the_file)
        if os.path.isdir(fullpath):
            sub_dirs.append(fullpath) #it is a sub_dir
        elif fnmatch.fnmatch(fullpath, a_file_wildcards):
            yield fullpath
        
    #iterate over sub_dirs
    for sub_dir in sort_func(sub_dirs):
        if os.path.basename(sub_dir) not in a_dir_ignore_list:
            for p_elem in ordered_dirwalk(sub_dir, a_file_wildcards):
                yield p_elem 
        else:
            LOG.debug("Ignore subdir %s" % (sub_dir))
  
def dirwalk(a_dir, a_wildcards= '*'):
    """
       return all files and dirs in a directory
    """
    for root, _, files in os.walk(a_dir):
        for the_file in files:
            if fnmatch.fnmatch(the_file, a_wildcards):
                yield os.path.join(root, the_file)  

def ascii_hex(a_str):
    """
       transform any string in hexa values
    """
    new_str = ""
    for the_char in a_str:
        new_str += "%s=hex[%s]," % (the_char, hex(ord(the_char)))
    return new_str

def profile_this(fn):
    """ profiling decorator """
    def profiled_fn(*args, **kwargs):
        import cProfile
        fpath = fn.__name__ + ".profile"
        prof  = cProfile.Profile()
        ret   = prof.runcall(fn, *args, **kwargs)
        prof.dump_stats(fpath)
        return ret
    return profiled_fn
                
def convert_to_unicode(a_str):
    """
       Try to get the stdin encoding and use it to convert the input string into unicode.
       It is dependent on the platform (mac osx,linux, windows 
    """
    #encoding can be forced from conf
    term_encoding = get_conf_defaults().get('Localisation', 'term_encoding', None)
    if not term_encoding:
        term_encoding = locale.getpreferredencoding() #use it to find the encoding for text terminal
        if not term_encoding:
            loc = locale.getdefaultlocale() #try to get defaultlocale()
            if loc and len(loc) == 2:
                term_encoding = loc[1]
            else:
                LOG.debug("Odd. loc = %s. Do not specify the encoding, let Python do its own investigation" % (loc))
    else:
        LOG.debug("Encoding forced. Read it from [Localisation]:term_encoding=%s" % (term_encoding))
        
    try: #encode
        u_str = unicode(a_str, term_encoding, errors='ignore')
           
        LOG.debug("raw unicode     = %s." % (u_str))
        LOG.debug("chosen encoding = %s." % (term_encoding))
        LOG.debug("unicode_escape val = %s." % ( u_str.encode('unicode_escape')))
    except Exception, err:
        LOG.error(err)
        get_exception_traceback()
        LOG.debug("Cannot convert to unicode from encoding:%s" % (term_encoding)) #add error
        u_str = unicode(a_str, errors='ignore')

    LOG.debug("hexval %s" % (ascii_hex(u_str)))
    
    return u_str
                
@memoized
def get_home_dir_path():
    """
       Get the gmvault dir
    """
    gmvault_dir = os.getenv("GMVAULT_DIR", None)
    
    # check by default in user[HOME]
    if not gmvault_dir:
        LOG.debug("no ENV variable $GMVAULT_DIR defined. Set by default $GMVAULT_DIR to $HOME/.gmvault (%s/.gmvault)" \
                  % (os.getenv("HOME",".")))
        gmvault_dir = "%s/.gmvault" % (os.getenv("HOME", "."))
    
    #create dir if not there
    makedirs(gmvault_dir)
    
    return gmvault_dir

CONF_FILE = "gmvault_defaults.conf"

@memoized
def get_conf_defaults():
    """
       Return the conf object containing the defaults stored in HOME/gmvault_defaults.conf
       Beware it is memoized
    """
    filepath = get_conf_filepath()
    
    if filepath:
        
        os.environ[gmv.conf.conf_helper.Conf.ENVNAME] = filepath
    
        the_cf = gmv.conf.conf_helper.Conf.get_instance()
    
        LOG.debug("Load defaults from %s" % (filepath))
        
        return the_cf
    else:
        return gmv.conf.conf_helper.MockConf() #retrun MockObject that will play defaults
    
#VERSION DETECTION PATTERN
VERSION_PATTERN  = r'\s*conf_version=\s*(?P<version>\S*)\s*'
VERSION_RE  = re.compile(VERSION_PATTERN)

#list of version conf to not overwrite with the next
VERSIONS_TO_PRESERVE = [ '1.8.1' ]

def _get_version_from_conf(home_conf_file):
    """
       Check if the config file need to be replaced because it comes from an older version
    """
    #check version
    ver = None
    with open(home_conf_file) as curr_fd:
        for line in curr_fd:
            line = line.strip()
            matched = VERSION_RE.match(line)
            if matched:
                ver = matched.group('version')
                return ver.strip()
    
    return ver

def _create_default_conf_file(home_conf_file):
    """
       Write on disk the default file
    """
    LOG.critical("Create defaults in %s. Please touch this file only if you know what to do." % (home_conf_file))
    try:
        the_fd = open(home_conf_file, "w+")
        the_fd.write(gmvault_const.DEFAULT_CONF_FILE)
        the_fd.close()
        return home_conf_file
    except Exception, err:
        #catch all error and let run gmvault with defaults if needed
        LOG.critical("Ignore Error when trying to create conf file for defaults in %s:\n%s.\n" % (get_home_dir_path(), err) )
        LOG.debug("=== Exception traceback ===")
        LOG.debug(get_exception_traceback())
        LOG.debug("=== End of Exception traceback ===\n")
        #return default file instead
        return         

@memoized
def get_conf_filepath():
    """
       If default file is not present, generate it from scratch.
       If it cannot be created, then return None
    """
    home_conf_file = "%s/%s" % (get_home_dir_path(), CONF_FILE)
    
    if not os.path.exists(home_conf_file):
        return _create_default_conf_file(home_conf_file)
    else:
        # check if the conf file needs to be replaced
        version = _get_version_from_conf(home_conf_file)
        if version not in VERSIONS_TO_PRESERVE:
            LOG.debug("%s with version %s is too old, overwrite it with the latest file." \
                       % (home_conf_file, version))
            return _create_default_conf_file(home_conf_file)    
    
    return home_conf_file

########NEW FILE########
__FILENAME__ = gmv_cmd
# -*- coding: utf-8 -*-
'''
    Gmvault: a tool to backup and restore your gmail account.
    Copyright (C) <2011-2013>  <guillaume Aubert (guillaume dot aubert at gmail do com)>

    This program is free software: you can redistribute it and/or modify
    it under the terms of the GNU Affero General Public License as
    published by the Free Software Foundation, either version 3 of the
    License, or (at your option) any later version.

    This program is distributed in the hope that it will be useful,
    but WITHOUT ANY WARRANTY; without even the implied warranty of
    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
    GNU Affero General Public License for more details.

    You should have received a copy of the GNU Affero General Public License
    along with this program.  If not, see <http://www.gnu.org/licenses/>.

'''
import socket
import sys
import datetime
import os
import signal
import traceback

import argparse
import imaplib
import gmv.log_utils as log_utils
import gmv.gmvault_utils as gmvault_utils
import gmv.gmvault as gmvault
import gmv.gmvault_export as gmvault_export
import gmv.collections_utils as collections_utils

from gmv.cmdline_utils  import CmdLineParser
from gmv.credential_utils import CredentialHelper

GMVAULT_VERSION = gmvault_utils.GMVAULT_VERSION

GLOBAL_HELP_EPILOGUE = """Examples:

a) Get help for each of the individual commands

#> gmvault sync -h
#> gmvault restore --help
#> gmvault check -h
#> gmvault export -h

"""

REST_HELP_EPILOGUE = """Examples:

a) Complete restore of your gmail account (backed up in ~/gmvault-db) into anewfoo.bar@gmail.com 

#> gmvault restore -d ~/gmvault-db anewfoo.bar@gmail.com

b) Quick restore (restore only the last 2 months to make regular updates) of your gmail account into anewfoo.bar@gmail.com 

#> gmvault restore --type quick -d ~/gmvault-db foo.bar@gmail.com

c) Restart a restore after a previous error (Gmail can cut the connection if it is too long)

#> gmvault restore -d ~/gmvault-db anewfoo.bar@gmail.com --resume

d) Apply a label to all restored emails

#> gmvault restore --apply-label "20120422-gmvault" -d ~/gmvault-db anewfoo.bar@gmail.com
"""

SYNC_HELP_EPILOGUE = """Examples:

a) Full synchronisation with email and oauth login in ./gmvault-db

#> gmvault sync foo.bar@gmail.com

b) Quick daily synchronisation (only the last 2 months are scanned)

#> gmvault sync --type quick foo.bar@gmail.com

c) Resume Full synchronisation from where it failed to not go through your mailbox again

#> gmvault sync foo.bar@gmail.com --resume

d) Encrypt stored emails to save them safely anywhere

#> gmvault sync foo.bar@gmail.com --encrypt

d) Custom synchronisation with an IMAP request for advance users

#> gmvault sync --type custom --imap-req "Since 1-Nov-2011 Before 10-Nov-2011" foo.bar@gmail.com

e) Custom synchronisation with an Gmail request for advance users.
   Get all emails with label work and sent by foo.

#> gmvault sync --type custom --gmail-req "in:work from:foo" foo.bar@gmail.com

"""

EXPORT_HELP_EPILOGUE = """Warning: Experimental Functionality requiring more testing.

Examples:

a) Export default gmvault-db ($HOME/gmvault-db or %HOME$/gmvault-db) as a maildir mailbox.

#> gmvault export ~/my-mailbox-dir

b) Export a gmvault-db as a mbox mailbox (compliant with Thunderbird).

#> gmvault export -d /tmp/gmvault-db /tmp/a-mbox-dir

c) Export only a limited set of labels from the default gmvault-db as a mbox mailbox (compliant with Thunderbird).

#> gmvault export -l "label1" -l "TopLabel/LabelLev1" /tmp/a-mbox-dir

d) Use one of the export type dedicated to a specific tool (dovecot or offlineIMAP)

#> gmvault export -t dovecot /tmp/a-dovecot-dir
"""

LOG = log_utils.LoggerFactory.get_logger('gmv')

class NotSeenAction(argparse.Action): #pylint:disable=R0903,w0232
    """
       to differenciate between a seen and non seen command
    """
    def __call__(self, parser, namespace, values, option_string=None):
        if values:
            setattr(namespace, self.dest, 'empty')
        else:
            setattr(namespace, self.dest, values)

class GMVaultLauncher(object):
    """
       GMVault launcher handling the command parsing
    """
    
    SYNC_TYPES    = ['full', 'quick', 'custom']
    RESTORE_TYPES = ['full', 'quick']
    CHECK_TYPES   = ['full']
    EXPORT_TYPES  = collections_utils.OrderedDict([
                     ('offlineimap', gmvault_export.OfflineIMAP),
                     ('dovecot', gmvault_export.Dovecot),
                     ('maildir', gmvault_export.OfflineIMAP),
                     ('mbox', gmvault_export.MBox)])
    EXPORT_TYPE_NAMES = ", ".join(EXPORT_TYPES)
    
    DEFAULT_GMVAULT_DB = "%s/gmvault-db" % (os.getenv("HOME", "."))
    
    def __init__(self):
        """ constructor """
        super(GMVaultLauncher, self).__init__()
        
    @gmvault_utils.memoized
    def _create_parser(self): #pylint: disable=R0915
        """
           Create the argument parser
           Return the created parser
        """
        parser = CmdLineParser()
        
        parser.epilogue = GLOBAL_HELP_EPILOGUE

        parser.add_argument("-v", '--version', action='version', version='Gmvault v%s' % (GMVAULT_VERSION))
        
        subparsers = parser.add_subparsers(title='subcommands', help='valid subcommands.')
         
        # A sync command
        sync_parser = subparsers.add_parser('sync', \
                                            help='synchronize with a given gmail account.')
        #email argument can be optional so it should be an option
        sync_parser.add_argument('email', \
                                 action='store', default='empty_$_email', help='email to sync with.')
        # sync typ
        sync_parser.add_argument('-t', '-type', '--type', \
                                 action='store', dest='type', \
                                 default='full', help='type of synchronisation: full|quick|custom. (default: full)')
        
        sync_parser.add_argument("-d", "--db-dir", \
                                 action='store', help="Database root directory. (default: $HOME/gmvault-db)",\
                                 dest="db_dir", default= self.DEFAULT_GMVAULT_DB)
               
        # for both when seen add const empty otherwise not_seen
        # this allow to distinguish between an empty value and a non seen option
        
        
        sync_parser.add_argument("-o", "--oauth", \
                          help="use oauth for authentication. (default recommended method)",\
                          action='store_const', dest="oauth_token", const='empty', default='not_seen')
        
        sync_parser.add_argument("-p", "--passwd", \
                          help="use interactive password authentication. (not recommended)",
                          action= 'store_const' , dest="passwd", const='empty', default='not_seen')
        
        sync_parser.add_argument("-2", "--2-legged-oauth", \
                          help="use 2 legged oauth for authentication. (Google Apps Business or Education accounts)",\
                          action='store_const', dest="two_legged_oauth_token", const='empty', default='not_seen')
        
        sync_parser.add_argument("--renew-oauth-tok", \
                          help="renew the stored oauth token (two legged or normal) via an interactive authentication session.",
                          action= 'store_const' , dest="oauth_token", const='renew')
         
        sync_parser.add_argument("--renew-passwd", \
                          help="renew the stored password via an interactive authentication session. (not recommended)",
                          action= 'store_const' , dest="passwd", const='renew')
        
        sync_parser.add_argument("--store-passwd", \
                          help="use interactive password authentication, encrypt and store the password. (not recommended)",
                          action= 'store_const' , dest="passwd", const='store')
        
        sync_parser.add_argument("-r", "--imap-req", metavar = "REQ", \
                                 help="Imap request to restrict sync.",\
                                 dest="imap_request", default=None)
        
        sync_parser.add_argument("-g", "--gmail-req", metavar = "REQ", \
                                 help="Gmail search request to restrict sync as defined in"\
                                      "https://support.google.com/mail/bin/answer.py?hl=en&answer=7190",\
                                 dest="gmail_request", default=None)
        
        # activate the resume mode --restart is deprecated
        sync_parser.add_argument("--resume", "--restart", \
                                 action='store_true', dest='restart', \
                                 default=False, help= 'Resume the sync action from the last saved gmail id.')
        
        # activate the resume mode --restart is deprecated
        sync_parser.add_argument("--emails-only", \
                                 action='store_true', dest='only_emails', \
                                 default=False, help= 'Only sync emails.')
        
        # activate the resume mode --restart is deprecated
        sync_parser.add_argument("--chats-only", \
                                 action='store_true', dest='only_chats', \
                                 default=False, help= 'Only sync chats.')
        
        sync_parser.add_argument("-e", "--encrypt", \
                                 help="encrypt stored email messages in the database.",\
                                 action='store_true',dest="encrypt", default=False)
        
        sync_parser.add_argument("-c", "--check-db", metavar = "VAL", \
                          help="enable/disable the removal from the gmvault db of the emails "\
                               "that have been deleted from the given gmail account. VAL = yes or no.",\
                          dest="db_cleaning", default=None)
        
        sync_parser.add_argument("-m", "--multiple-db-owner", \
                                 help="Allow the email database to be synchronized with emails from multiple accounts.",\
                                 action='store_true',dest="allow_mult_owners", default=False)
        
        # activate the restart mode
        sync_parser.add_argument("--no-compression", \
                                 action='store_false', dest='compression', \
                                 default=True, help= 'disable email storage compression (gzip).')
        
        sync_parser.add_argument("--server", metavar = "HOSTNAME", \
                              action='store', help="Gmail imap server hostname. (default: imap.gmail.com)",\
                              dest="host", default="imap.gmail.com")
            
        sync_parser.add_argument("--port", metavar = "PORT", \
                              action='store', help="Gmail imap server port. (default: 993)",\
                              dest="port", default=993)
        
        sync_parser.add_argument("--debug", "-debug", \
                              action='store_true', help="Activate debugging info",\
                              dest="debug", default=False)
        
        
        sync_parser.set_defaults(verb='sync')
    
        sync_parser.epilogue = SYNC_HELP_EPILOGUE
        
        # restore command
        rest_parser = subparsers.add_parser('restore', \
                                            help='restore gmvault-db to a given email account.')
        #email argument can be optional so it should be an option
        rest_parser.add_argument('email', \
                                 action='store', default='empty_$_email', help='email account to restore.')
        
        # restore typ
        rest_parser.add_argument('-t', '-type', '--type', \
                                 action='store', dest='type', \
                                 default='full', help='type of restoration: full|quick. (default: full)')
        
        # add a label
        rest_parser.add_argument('-a', '--apply-label', \
                                 action='store', dest='apply_label', \
                                 default=None, help='Apply a label to restored emails')
        
        # activate the resume mode --restart is deprecated
        rest_parser.add_argument("--resume", "--restart", \
                                 action='store_true', dest='restart', \
                                 default=False, help= 'Restart from the last saved gmail id.')
                                 
        # activate the resume mode --restart is deprecated
        rest_parser.add_argument("--emails-only", \
                                 action='store_true', dest='only_emails', \
                                 default=False, help= 'Only sync emails.')
        
        # activate the resume mode --restart is deprecated
        rest_parser.add_argument("--chats-only", \
                                 action='store_true', dest='only_chats', \
                                 default=False, help= 'Only sync chats.')
        
        rest_parser.add_argument("-d", "--db-dir", \
                                 action='store', help="Database root directory. (default: $HOME/gmvault-db)",\
                                 dest="db_dir", default= self.DEFAULT_GMVAULT_DB)
               
        # for both when seen add const empty otherwise not_seen
        # this allow to distinguish between an empty value and a non seen option
        rest_parser.add_argument("-o", "--oauth", \
                          help="use oauth for authentication. (default method)",\
                          action='store_const', dest="oauth_token", const='empty', default='not_seen')
        
        rest_parser.add_argument("-p", "--passwd", \
                          help="use interactive password authentication. (not recommended)",
                          action='store_const', dest="passwd", const='empty', default='not_seen')
        
        rest_parser.add_argument("-2", "--2-legged-oauth", \
                          help="use 2 legged oauth for authentication. (Google Apps Business or Education accounts)",\
                          action='store_const', dest="two_legged_oauth_token", const='empty', default='not_seen')
        
        
        rest_parser.add_argument("--server", metavar = "HOSTNAME", \
                              action='store', help="Gmail imap server hostname. (default: imap.gmail.com)",\
                              dest="host", default="imap.gmail.com")
            
        rest_parser.add_argument("--port", metavar = "PORT", \
                              action='store', help="Gmail imap server port. (default: 993)",\
                              dest="port", default=993)
        
        rest_parser.add_argument("--debug", "-debug", \
                              action='store_true', help="Activate debugging info",\
                              dest="debug", default=False)
        
        rest_parser.set_defaults(verb='restore')
    
        rest_parser.epilogue = REST_HELP_EPILOGUE
        
        # check_db command
        check_parser = subparsers.add_parser('check', \
                                            help='check and clean the gmvault-db disk database.')

        #email argument
        check_parser.add_argument('email', \
                                 action='store', default='empty_$_email', help='gmail account against which to check.')
        
        check_parser.add_argument("-d", "--db-dir", \
                                 action='store', help="Database root directory. (default: $HOME/gmvault-db)",\
                                 dest="db_dir", default= self.DEFAULT_GMVAULT_DB)
     
        # for both when seen add const empty otherwise not_seen
        # this allow to distinguish between an empty value and a non seen option
        check_parser.add_argument("-o", "--oauth", \
                          help="use oauth for authentication. (default method)",\
                          action='store_const', dest="oauth_token", const='empty', default='not_seen')
        
        check_parser.add_argument("-p", "--passwd", \
                          help="use interactive password authentication. (not recommended)",
                          action='store_const', dest="passwd", const='empty', default='not_seen')
        
        check_parser.add_argument("-2", "--2-legged-oauth", \
                          help="use 2 legged oauth for authentication. (Google Apps Business or Education accounts)",\
                          action='store_const', dest="two_legged_oauth_token", const='empty', default='not_seen')
        
        
        check_parser.add_argument("--server", metavar = "HOSTNAME", \
                              action='store', help="Gmail imap server hostname. (default: imap.gmail.com)",\
                              dest="host", default="imap.gmail.com")
            
        check_parser.add_argument("--port", metavar = "PORT", \
                              action='store', help="Gmail imap server port. (default: 993)",\
                              dest="port", default=993)
        
        check_parser.add_argument("--debug", "-debug", \
                              action='store_true', help="Activate debugging info",\
                              dest="debug", default=False)
        
        check_parser.set_defaults(verb='check')
        
        # export command
        export_parser = subparsers.add_parser('export', \
                                            help='Export the gmvault-db database to another format.')

        export_parser.add_argument('output_dir', \
                                   action='store', help='destination directory to export to.')

        export_parser.add_argument("-d", "--db-dir", \
                                 action='store', help="Database root directory. (default: $HOME/gmvault-db)",\
                                 dest="db_dir", default= self.DEFAULT_GMVAULT_DB)

        export_parser.add_argument('-t', '-type', '--type', \
                          action='store', dest='type', \
                          default='mbox', help='type of export: %s. (default: mbox)' % self.EXPORT_TYPE_NAMES)

        export_parser.add_argument('-l', '--label', \
                                   action='append', dest='label', \
                                   default=None,
                                   help='specify a label to export')
        export_parser.add_argument("--debug", "-debug", \
                       action='store_true', help="Activate debugging info",\
                       dest="debug", default=False)

        export_parser.set_defaults(verb='export')
        
        export_parser.epilogue = EXPORT_HELP_EPILOGUE

        return parser
      
    @classmethod
    def _parse_common_args(cls, options, parser, parsed_args, list_of_types = []): #pylint:disable=W0102
        """
           Parse the common arguments for sync and restore
        """
        #add email
        parsed_args['email']            = options.email
        
        parsed_args['debug']            = options.debug
        
        parsed_args['restart']          = options.restart
        
        #user entered both authentication methods
        if options.passwd == 'empty' and (options.oauth_token == 'empty' or options.two_legged_oauth_token == 'empty'):
            parser.error('You have to use one authentication method. '\
                         'Please choose between XOAuth and password (recommend XOAuth).')
        
        # user entered no authentication methods => go to default oauth
        if options.passwd == 'not_seen' and options.oauth_token == 'not_seen' and options.two_legged_oauth_token == 'not_seen':
            #default to xoauth
            options.oauth_token = 'empty'
            
        # add passwd
        parsed_args['passwd']           = options.passwd
        
        # add oauth tok
        if options.oauth_token == 'empty':
            parsed_args['oauth']      = options.oauth_token
            parsed_args['two_legged'] = False
        elif options.oauth_token == 'renew':
            parsed_args['oauth'] = 'renew'
            parsed_args['two_legged'] = True if options.two_legged_oauth_token == 'empty' else False          
        elif options.two_legged_oauth_token == 'empty':
            parsed_args['oauth']      = options.two_legged_oauth_token
            parsed_args['two_legged'] = True
        
        #add ops type
        if options.type:
            tempo_list = ['auto']
            tempo_list.extend(list_of_types)
            if options.type.lower() in tempo_list:
                parsed_args['type'] = options.type.lower()
            else:
                parser.error('Unknown type for command %s. The type should be one of %s' \
                             % (parsed_args['command'], list_of_types))
        
        #add db_dir
        parsed_args['db-dir']           = options.db_dir

        LOG.critical("Use gmvault-db located in %s.\n" % (parsed_args['db-dir'])) 
        
        # add host
        parsed_args['host']             = options.host
        
        #convert to int if necessary
        port_type = type(options.port)
        
        try:
            if port_type == type('s') or port_type == type("s"):
                port = int(options.port)
            else:
                port = options.port
        except Exception, _: #pylint:disable=W0703
            parser.error("--port option %s is not a number. Please check the port value" % (port))
            
        # add port
        parsed_args['port']             = port
             
        return parsed_args
    
    def parse_args(self): #pylint: disable=R0912
        """ Parse command line arguments 
            
            :returns: a dict that contains the arguments
               
            :except Exception Error
            
        """
        
        parser = self._create_parser()
          
        options = parser.parse_args()
        
        LOG.debug("Namespace = %s\n" % (options))
        
        parsed_args = { }
                
        parsed_args['command'] = options.verb
        
        if parsed_args.get('command', '') == 'sync':
            
            # parse common arguments for sync and restore
            self._parse_common_args(options, parser, parsed_args, self.SYNC_TYPES)
            
            # handle the search requests (IMAP or GMAIL dialect)
            if options.imap_request and options.gmail_request:
                parser.error('Please use only one search request type. You can use --imap-req or --gmail-req.')
            elif not options.imap_request and not options.gmail_request:
                LOG.debug("No search request type passed: Get everything.")
                parsed_args['request']   = {'type': 'imap', 'req':'ALL'}
            elif options.gmail_request and not options.imap_request:
                parsed_args['request']  = { 'type': 'gmail', 'req' : self._clean_imap_or_gm_request(options.gmail_request)}
            else:
                parsed_args['request']  = { 'type':'imap',  'req' : self._clean_imap_or_gm_request(options.imap_request)}
                
            # handle emails or chats only
            if options.only_emails and options.only_chats:
                parser.error("--emails-only and --chats-only cannot be used together. Please choose one.")
           
            parsed_args['emails_only'] = options.only_emails
            parsed_args['chats_only']  = options.only_chats
        
            # add db-cleaning
            # if request passed put it False unless it has been forced by the user
            # default is True (db-cleaning done)
            #default 
            parsed_args['db-cleaning'] = True
            
            # if there is a value then it is forced
            if options.db_cleaning: 
                parsed_args['db-cleaning'] = parser.convert_to_boolean(options.db_cleaning)
            
            #elif parsed_args['request']['req'] != 'ALL' and not options.db_cleaning:
            #    #else if we have a request and not forced put it to false
            #    parsed_args['db-cleaning'] = False
                
            if parsed_args['db-cleaning']:
                LOG.critical("Activate Gmvault db cleaning.")
            else:
                LOG.critical("Disable deletion of emails that are in Gmvault db and not anymore in Gmail.")
                
            #add encryption option
            parsed_args['encrypt'] = options.encrypt

            #add ownership checking
            parsed_args['ownership_control'] = not options.allow_mult_owners
            
            #compression flag
            parsed_args['compression'] = options.compression
                
                
        elif parsed_args.get('command', '') == 'restore':
            
            # parse common arguments for sync and restore
            self._parse_common_args(options, parser, parsed_args, self.RESTORE_TYPES)
            
            # apply restore labels if there is any
            parsed_args['apply_label'] = options.apply_label
            
            parsed_args['restart'] = options.restart
            
            # handle emails or chats only
            if options.only_emails and options.only_chats:
                parser.error("--emails-only and --chats-only cannot be used together. Please choose one.")
           
            parsed_args['emails_only'] = options.only_emails
            parsed_args['chats_only']  = options.only_chats
            
        elif parsed_args.get('command', '') == 'check':
            
            #add defaults for type
            options.type    = 'full'
            options.restart = False
            
            # parse common arguments for sync and restore
            self._parse_common_args(options, parser, parsed_args, self.CHECK_TYPES)
    
        elif parsed_args.get('command', '') == 'export':
            parsed_args['labels']     = options.label
            parsed_args['db-dir']     = options.db_dir
            parsed_args['output-dir'] = options.output_dir
            if options.type.lower() in self.EXPORT_TYPES:
                parsed_args['type'] = options.type.lower()
            else:
                parser.error('Unknown type for command export. The type should be one of %s' % self.EXPORT_TYPE_NAMES)
            parsed_args['debug'] = options.debug

        elif parsed_args.get('command', '') == 'config':
            pass
    
        #add parser
        parsed_args['parser']           = parser
        
        return parsed_args
    
    @classmethod
    def _clean_imap_or_gm_request(cls, request):
        """
           Clean request passed by the user with the option --imap-req or --gmail-req.
           Windows batch script preserve the single quote and unix shell doesn't.
           If the request starts and ends with single quote eat them.
        """
        LOG.debug("clean_imap_or_gm_request. original request = %s\n" % (request))
        
        if request and (len(request) > 2) and (request[0] == "'" and request[-1] == "'"):
            request =  request[1:-1]
            
        LOG.debug("clean_imap_or_gm_request. processed request = %s\n" % (request))
        return request
    
    @classmethod
    def _export(cls, args):
        """
           Export gmvault-db into another format
        """
        export_type = cls.EXPORT_TYPES[args['type']]
        output_dir = export_type(args['output-dir'])
        LOG.critical("Export gmvault-db as a %s mailbox." % (args['type']))
        exporter = gmvault_export.GMVaultExporter(args['db-dir'], output_dir,
            labels=args['labels'])
        exporter.export()
        output_dir.close()

    @classmethod
    def _restore(cls, args, credential):
        """
           Execute All restore operations
        """
        LOG.critical("Connect to Gmail server.\n")
        # Create a gmvault releaving read_only_access
        restorer = gmvault.GMVaulter(args['db-dir'], args['host'], args['port'], \
                                       args['email'], credential, read_only_access = False)
        
        #full sync is the first one
        if args.get('type', '') == 'full':
            
            #call restore
            labels = [args['apply_label']] if args['apply_label'] else []
            restorer.restore(extra_labels = labels, restart = args['restart'], \
                             emails_only = args['emails_only'], chats_only = args['chats_only'])
            
        elif args.get('type', '') == 'quick':
            
            #take the last two to 3 months depending on the current date
            
            # today - 2 months
            today = datetime.date.today()
            begin = today - datetime.timedelta(gmvault_utils.get_conf_defaults().getint("Restore", "quick_days", 8))
            
            starting_dir = gmvault_utils.get_ym_from_datetime(begin)
            
            #call restore
            labels = [args['apply_label']] if args['apply_label'] else []
            restorer.restore(pivot_dir = starting_dir, extra_labels = labels, restart = args['restart'], \
                             emails_only = args['emails_only'], chats_only = args['chats_only'])
        
        else:
            raise ValueError("Unknown synchronisation mode %s. Please use full (default), quick.")
        
        #print error report
        LOG.critical(restorer.get_operation_report()) 
            
    @classmethod        
    def _sync(cls, args, credential):
        """
           Execute All synchronisation operations
        """
        LOG.critical("Connect to Gmail server.\n")
        
        # handle credential in all levels
        syncer = gmvault.GMVaulter(args['db-dir'], args['host'], args['port'], \
                                       args['email'], credential, read_only_access = True, use_encryption = args['encrypt'])
        
        
        
        #full sync is the first one
        if args.get('type', '') == 'full':
        
            #choose full sync. Ignore the request
            syncer.sync({ 'mode': 'full', 'type': 'imap', 'req': 'ALL' } , compress_on_disk = args['compression'], \
                        db_cleaning = args['db-cleaning'], ownership_checking = args['ownership_control'],\
                        restart = args['restart'], emails_only = args['emails_only'], chats_only = args['chats_only'])
        
        elif args.get('type', '') == 'auto':
        
            #choose auto sync. imap request = ALL and restart = True
            syncer.sync({ 'mode': 'auto', 'type': 'imap', 'req': 'ALL' } , compress_on_disk = args['compression'], \
                        db_cleaning = args['db-cleaning'], ownership_checking = args['ownership_control'],\
                        restart = True, emails_only = args['emails_only'], chats_only = args['chats_only'])
              
        elif args.get('type', '') == 'quick':
            
            #sync only the last x days (taken in defaults) in order to be quick 
            #(cleaning is import here because recent days might move again
            
            # today - 2 months
            today = datetime.date.today()
            begin = today - datetime.timedelta(gmvault_utils.get_conf_defaults().getint("Sync", "quick_days", 8))
            
            LOG.critical("Quick sync mode. Check for new emails since %s." % (begin.strftime('%d-%b-%Y')))
            
            # today + 1 day
            end   = today + datetime.timedelta(1)
            
            req   = { 'type' : 'imap', \
                      'req'  : syncer.get_imap_request_btw_2_dates(begin, end), \
                      'mode' : 'quick'}
            
            syncer.sync( req, \
                         compress_on_disk = args['compression'], \
                         db_cleaning = args['db-cleaning'], \
                         ownership_checking = args['ownership_control'], restart = args['restart'], \
                         emails_only = args['emails_only'], chats_only = args['chats_only'])
            
        elif args.get('type', '') == 'custom':
            
            #convert args to unicode
            args['request']['req']     = gmvault_utils.convert_to_unicode(args['request']['req'])
            args['request']['charset'] = 'utf-8' #for the moment always utf-8
            args['request']['mode']    = 'custom'

            # pass an imap request. Assume that the user know what to do here
            LOG.critical("Perform custom synchronisation with %s request: %s.\n" \
                         % (args['request']['type'], args['request']['req']))
            
            syncer.sync(args['request'], compress_on_disk = args['compression'], db_cleaning = args['db-cleaning'], \
                        ownership_checking = args['ownership_control'], restart = args['restart'], \
                        emails_only = args['emails_only'], chats_only = args['chats_only'])
        else:
            raise ValueError("Unknown synchronisation mode %s. Please use full (default), quick or custom.")
        
        
        #print error report
        LOG.critical(syncer.get_operation_report())
    
    @classmethod
    def _check_db(cls, args, credential):
        """
           Check DB
        """
        LOG.critical("Connect to Gmail server.\n")
        
        # handle credential in all levels
        checker = gmvault.GMVaulter(args['db-dir'], args['host'], args['port'], \
                                   args['email'], credential, read_only_access = True)
        
        checker.check_clean_db(db_cleaning = True)
            

    def run(self, args): #pylint:disable=R0912
        """
           Run the grep with the given args 
        """
        on_error       = True
        die_with_usage = True
        
        try:
            
            if args.get('command') not in ('export'):
                credential = CredentialHelper.get_credential(args)
            
            if args.get('command', '') == 'sync':
                
                self._sync(args, credential)
                
            elif args.get('command', '') == 'restore':
                
                self._restore(args, credential)
            
            elif args.get('command', '') == 'check':
                
                self._check_db(args, credential)
                
            elif args.get('command', '') == 'export':

                self._export(args)

            elif args.get('command', '') == 'config':
                
                LOG.critical("Configure something. TBD.\n")
            
            on_error = False
        
        except KeyboardInterrupt, _:
            LOG.critical("\nCTRL-C. Stop all operations.\n")
            on_error = False
        except socket.error:
            LOG.critical("Error: Network problem. Please check your gmail server hostname,"\
                         " the internet connection or your network setup.\n")
            LOG.critical("=== Exception traceback ===")
            LOG.critical(gmvault_utils.get_exception_traceback())
            LOG.critical("=== End of Exception traceback ===\n")
            die_with_usage = False
        except imaplib.IMAP4.error, imap_err:
            #bad login or password
            if str(imap_err) in ['[AUTHENTICATIONFAILED] Invalid credentials (Failure)', \
                                 '[ALERT] Web login required: http://support.google.com/'\
                                 'mail/bin/answer.py?answer=78754 (Failure)', \
                                 '[ALERT] Invalid credentials (Failure)'] :
                LOG.critical("ERROR: Invalid credentials, cannot login to the gmail server."\
                             " Please check your login and password or xoauth token.\n")
                die_with_usage = False
            else:
                LOG.critical("Error: %s. \n" % (imap_err) )
                LOG.critical("=== Exception traceback ===")
                LOG.critical(gmvault_utils.get_exception_traceback())
                LOG.critical("=== End of Exception traceback ===\n")
        except Exception, err:
            LOG.critical("Error: %s. \n" % (err) )
            LOG.critical("=== Exception traceback ===")
            LOG.critical(gmvault_utils.get_exception_traceback())
            LOG.critical("=== End of Exception traceback ===\n")
            die_with_usage = False
        finally: 
            if on_error and die_with_usage:
                args['parser'].die_with_usage()
 
def init_logging():
    """
       init logging infrastructure
    """       
    #setup application logs: one handler for stdout and one for a log file
    log_utils.LoggerFactory.setup_cli_app_handler(log_utils.STANDALONE, activate_log_file=False, file_path="./gmvault.log") 
    
def activate_debug_mode():
    """
       Activate debugging logging
    """
    LOG.critical("Debugging logs are going to be saved in file %s/gmvault.log.\n" % os.getenv("HOME","."))
    log_utils.LoggerFactory.setup_cli_app_handler(log_utils.STANDALONE, activate_log_file=True, \
                               console_level= 'DEBUG', file_path="%s/gmvault.log" % os.getenv("HOME","."))

def sigusr1_handler(signum, frame): #pylint:disable=W0613
    """
      Signal handler to get stack trace if the program is stuck
    """

    filename = './gmvault.traceback.txt'
    
    print("GMVAULT: Received SIGUSR1 -- Printing stack trace in %s..." % (os.path.abspath(filename)))

    the_f = open(filename, 'a')
    traceback.print_stack(file = the_f)
    the_f.close()

def register_traceback_signal():
    """ To register a USR1 signal allowing to get stack trace """
    signal.signal(signal.SIGUSR1, sigusr1_handler)

def setup_default_conf():
    """
       set the environment GMVAULT_CONF_FILE which is necessary for Conf object
    """
    gmvault_utils.get_conf_defaults() # force instanciation of conf to load the defaults

def bootstrap_run():
    """ temporary bootstrap """
    
    init_logging()
    
    #force argv[0] to gmvault
    sys.argv[0] = "gmvault"
    
    LOG.critical("")
    
    gmvlt = GMVaultLauncher()
    
    args = gmvlt.parse_args()
    
    #activate debug if enabled
    if args['debug']:
        LOG.critical("Activate debugging information.")
        activate_debug_mode()
    
    # force instanciation of conf to load the defaults
    gmvault_utils.get_conf_defaults() 
    
    gmvlt.run(args)
   
    
if __name__ == '__main__':
     
    #import memdebug
    
    #memdebug.start(8080)
    #import sys
    #print("sys.argv=[%s]" %(sys.argv))
    
    register_traceback_signal()
    
    bootstrap_run()
    
    sys.exit(0)

########NEW FILE########
__FILENAME__ = imap_utils
# -*- coding: utf-8 -*-
'''
    Gmvault: a tool to backup and restore your gmail account.
    Copyright (C) <2011-2013>  <guillaume Aubert (guillaume dot aubert at gmail do com)>

    This program is free software: you can redistribute it and/or modify
    it under the terms of the GNU Affero General Public License as
    published by the Free Software Foundation, either version 3 of the
    License, or (at your option) any later version.

    This program is distributed in the hope that it will be useful,
    but WITHOUT ANY WARRANTY; without even the implied warranty of
    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
    GNU Affero General Public License for more details.

    You should have received a copy of the GNU Affero General Public License
    along with this program.  If not, see <http://www.gnu.org/licenses/>.

Module containing the IMAPFetcher object which is the Wrapper around the modified IMAPClient object

'''
import math
import time
import socket
import re

import functools

import ssl
import imaplib

import gmv.gmvault_const as gmvault_const
import gmv.log_utils as log_utils
import gmv.credential_utils as credential_utils

import gmv.gmvault_utils as gmvault_utils
import gmv.mod_imap as mimap

LOG = log_utils.LoggerFactory.get_logger('imap_utils')

class PushEmailError(Exception):
    """
       PushEmail Error
    """
    def __init__(self, a_msg, quarantined = False):
        """
           Constructor
        """
        super(PushEmailError, self).__init__(a_msg)
        self._in_quarantine = quarantined
    
    def quarantined(self):
        """ Get email to quarantine """
        return self._in_quarantine

#retry decorator with nb of tries and sleep_time and backoff
def retry(a_nb_tries=3, a_sleep_time=1, a_backoff=1): #pylint:disable=R0912
    """
      Decorator for retrying command when it failed with a imap or socket error.
      Should be used exclusively on imap exchanges.
      Strategy, always retry on any imaplib or socket error. Wait few seconds before to retry
      backoff sets the factor by which the a_sleep_time should lengthen after each failure. backoff must be greater than 1,
      or else it isn't really a backoff
    """
    if a_backoff < 1:
        raise ValueError("a_backoff must be greater or equal to 1")

    a_nb_tries = math.floor(a_nb_tries)
    if a_nb_tries < 0:
        raise ValueError("a_nb_tries must be 0 or greater")

    if a_sleep_time <= 0:
        raise ValueError("a_sleep_time must be greater than 0")
    
    def reconnect(the_self, rec_nb_tries, total_nb_tries, rec_error, rec_sleep_time = [1]): #pylint: disable=W0102
        """
           Reconnect procedure. Sleep and try to reconnect
        """
        # go in retry mode if less than a_nb_tries
        while rec_nb_tries[0] < total_nb_tries:
            
            LOG.critical("Disconnecting from Gmail Server and sleeping ...")
            the_self.disconnect()            
            
            # add X sec of wait
            time.sleep(rec_sleep_time[0])
            rec_sleep_time[0] *= a_backoff #increase sleep time for next time
            
            rec_nb_tries[0] += 1
            
            #increase total nb of reconns
            the_self.total_nb_reconns += 1
           
            # go in retry mode: reconnect.
            # retry reconnect as long as we have tries left
            try:
                LOG.critical("Reconnecting to the from Gmail Server.")
                
                #reconnect to the current folder
                the_self.connect(go_to_current_folder = True )
                
                return 
            
            except Exception, ignored:
                # catch all errors and try as long as we have tries left
                LOG.exception(ignored)
        else:
            #cascade error
            raise rec_error
    
    def inner_retry(the_func): #pylint:disable=C0111,R0912
        def wrapper(*args, **kwargs): #pylint:disable=C0111,R0912
            nb_tries = [0] # make it mutable in reconnect
            m_sleep_time = [a_sleep_time]  #make it mutable in reconnect
            while True:
                try:
                    return the_func(*args, **kwargs)
                except PushEmailError, p_err:
                    
                    LOG.debug("error message = %s. traceback:%s" % (p_err, gmvault_utils.get_exception_traceback()))
                    
                    if nb_tries[0] < a_nb_tries:
                        LOG.critical("Cannot reach the Gmail server. Wait %s seconds and retrying." % (m_sleep_time[0]))
                    else:
                        LOG.critical("Stop retrying, tried too many times ...")
                    
                    reconnect(args[0], nb_tries, a_nb_tries, p_err, m_sleep_time)
                
                except imaplib.IMAP4.abort, err: #abort is recoverable and error is not
                    
                    LOG.debug("IMAP (abort) error message = %s. traceback:%s" % (err, gmvault_utils.get_exception_traceback()))
                    
                    if nb_tries[0] < a_nb_tries:
                        LOG.critical("Received an IMAP abort error. Wait %s seconds and retrying." % (m_sleep_time[0]))
                    else:
                        LOG.critical("Stop retrying, tried too many times ...")
                        
                    # problem with this email, put it in quarantine
                    reconnect(args[0], nb_tries, a_nb_tries, err, m_sleep_time)    
                    
                except socket.error, sock_err:
                    LOG.debug("error message = %s. traceback:%s" % (sock_err, gmvault_utils.get_exception_traceback()))
                    
                    if nb_tries[0] < a_nb_tries:
                        LOG.critical("Cannot reach the Gmail server. Wait %s seconds and retrying." % (m_sleep_time[0]))
                    else:
                        LOG.critical("Stop retrying, tried too many times ...")
                        
                    reconnect(args[0], nb_tries, a_nb_tries, sock_err, m_sleep_time)
                
                except ssl.SSLError, ssl_err:
                    LOG.debug("error message = %s. traceback:%s" % (ssl_err, gmvault_utils.get_exception_traceback()))
                    
                    if nb_tries[0] < a_nb_tries:
                        LOG.critical("Cannot reach the Gmail server. Wait %s seconds and retrying." % (m_sleep_time[0]))
                    else:
                        LOG.critical("Stop retrying, tried too many times ...")
                        
                    reconnect(args[0], nb_tries, a_nb_tries, sock_err, m_sleep_time)
                
                except imaplib.IMAP4.error, err:
                    
                    #just trace it back for the moment
                    LOG.debug("IMAP (normal) error message = %s. traceback:%s" % (err, gmvault_utils.get_exception_traceback()))
                    
                    if nb_tries[0] < a_nb_tries:
                        LOG.critical("Error when reaching Gmail server. Wait %s seconds and retry up to 2 times." \
                                     % (m_sleep_time[0]))
                    else:
                        LOG.critical("Stop retrying, tried too many times ...")
                    
                    #raise err
                    # retry 2 times before to quit
                    reconnect(args[0], nb_tries, 2, err, m_sleep_time)

        return functools.wraps(the_func)(wrapper)
        #return wrapper
    return inner_retry

class GIMAPFetcher(object): #pylint:disable=R0902,R0904
    '''
    IMAP Class reading the information
    '''
    GMAIL_EXTENSION     = 'X-GM-EXT-1'  # GMAIL capability
    GMAIL_ALL           = u'[Gmail]/All Mail' #GMAIL All Mail mailbox
    
    GENERIC_GMAIL_ALL   = u'\\AllMail' # unlocalised GMAIL ALL
    GENERIC_DRAFTS      = u'\\Drafts' # unlocalised DRAFTS
    GENERIC_GMAIL_CHATS = gmvault_const.GMAIL_UNLOCAL_CHATS   # unlocalised Chats names
    
    FOLDER_NAMES        = ['ALLMAIL', 'CHATS', 'DRAFTS']
    
    GMAIL_ID            = 'X-GM-MSGID' #GMAIL ID attribute
    GMAIL_THREAD_ID     = 'X-GM-THRID'
    GMAIL_LABELS        = 'X-GM-LABELS'
    
    IMAP_INTERNALDATE = 'INTERNALDATE'
    IMAP_FLAGS        = 'FLAGS'
    IMAP_ALL          = {'type':'imap', 'req':'ALL'}
    
    EMAIL_BODY        = 'BODY[]'
    
    GMAIL_SPECIAL_DIRS = ['\\Inbox', '\\Starred', '\\Sent', '\\Draft', '\\Important']
    
    #GMAIL_SPECIAL_DIRS_LOWER = ['\\inbox', '\\starred', '\\sent', '\\draft', '\\important']
    GMAIL_SPECIAL_DIRS_LOWER = ['\\inbox', '\\starred', '\\sent', '\\draft', '\\important', '\\trash']
    
    IMAP_BODY_PEEK     = 'BODY.PEEK[]' #get body without setting msg as seen

    #get the body info without setting msg as seen
    IMAP_HEADER_PEEK_FIELDS = 'BODY.PEEK[HEADER.FIELDS (MESSAGE-ID SUBJECT X-GMAIL-RECEIVED)]' 

    #key used to find these fields in the IMAP Response
    IMAP_HEADER_FIELDS_KEY      = 'BODY[HEADER.FIELDS (MESSAGE-ID SUBJECT X-GMAIL-RECEIVED)]'
    
    #GET_IM_UID_RE
    APPENDUID         = r'^[APPENDUID [0-9]* ([0-9]*)] \(Success\)$'
    
    APPENDUID_RE      = re.compile(APPENDUID)
    
    GET_ALL_INFO      = [ GMAIL_ID, GMAIL_THREAD_ID, GMAIL_LABELS, IMAP_INTERNALDATE, \
                          IMAP_BODY_PEEK, IMAP_FLAGS, IMAP_HEADER_PEEK_FIELDS]

    GET_ALL_BUT_DATA  = [ GMAIL_ID, GMAIL_THREAD_ID, GMAIL_LABELS, IMAP_INTERNALDATE, \
                          IMAP_FLAGS, IMAP_HEADER_PEEK_FIELDS]
    
    GET_DATA_ONLY     = [ GMAIL_ID, IMAP_BODY_PEEK]
 
    GET_GMAIL_ID      = [ GMAIL_ID ]
    
    GET_GMAIL_ID_DATE = [ GMAIL_ID,  IMAP_INTERNALDATE]

    def __init__(self, host, port, login, credential, readonly_folder = True): #pylint:disable=R0913
        '''
            Constructor
        '''
        self.host                   = host
        self.port                   = port
        self.login                  = login
        self.once_connected         = False
        self.credential             = credential
        self.ssl                    = True
        self.use_uid                = True
        self.readonly_folder        = readonly_folder
        
        self.localized_folders      = { 'ALLMAIL': { 'loc_dir' : None, 'friendly_name' : 'allmail'}, 
                                        'CHATS'  : { 'loc_dir' : None, 'friendly_name' : 'chats'}, 
                                        'DRAFTS' : { 'loc_dir' : None, 'friendly_name' : 'drafts'} }
        
        # memoize the current folder (All Mail or Chats) for reconnection management
        self.current_folder        = None
        
        self.server                 = None
        self.go_to_all_folder       = True
        self.total_nb_reconns       = 0
        # True when CHATS or other folder error msg has been already printed
        self.printed_folder_error_msg = { 'ALLMAIL' : False, 'CHATS': False , 'DRAFTS':False }
        
        #update GENERIC_GMAIL_CHATS. Should be done at the class level
        self.GENERIC_GMAIL_CHATS.extend(gmvault_utils.get_conf_defaults().get_list('Localisation', 'chat_folder', []))
        
    def spawn_connection(self):
        """
           spawn a connection with the same parameters
        """
        conn = GIMAPFetcher(self.host, self.port, self.login, self.credential, self.readonly_folder)
        conn.connect()
        return conn
        
    def connect(self, go_to_current_folder = False):
        """
           connect to the IMAP server
        """
        # create imap object
        self.server = mimap.MonkeyIMAPClient(self.host, port = self.port, use_uid= self.use_uid, need_ssl= self.ssl)
        # connect with password or xoauth
        if self.credential['type'] == 'passwd':
            self.server.login(self.login, self.credential['value'])
        elif self.credential['type'] == 'xoauth':
            #connect with xoauth 
            if self.once_connected:
                #already connected once so renew xoauth req because it can expire
                self.credential['value'] = credential_utils.CredentialHelper.get_xoauth_req_from_email(self.login)
                
            self.server.xoauth_login(self.credential['value']) 
        else:
            raise Exception("Unknown authentication method %s. Please use xoauth or passwd authentication " \
                            % (self.credential['type']))
            
        #set connected to True to handle reconnection in case of failure
        self.once_connected = True
        
        # check gmailness
        self.check_gmailness()
         
        # find allmail chats and drafts folders
        self.find_folder_names()

        if go_to_current_folder and self.current_folder:
            self.server.select_folder(self.current_folder, readonly = self.readonly_folder)
            
        #enable compression
        if gmvault_utils.get_conf_defaults().get_boolean('General', 'enable_imap_compression', True):
            self.enable_compression()
            LOG.debug("After Enabling compression.")
        else:
            LOG.debug("Do not enable imap compression.") 
            
    def disconnect(self):
        """
           disconnect to avoid too many simultaneous connection problem
        """
        if self.server:
            try:
                self.server.logout()
            except Exception, ignored: #ignored exception but still log it in log file if activated
                LOG.exception(ignored)
                
            self.server = None
    
    def reconnect(self):
        """
           disconnect and connect again
        """
        self.disconnect()
        self.connect()
    
    def enable_compression(self):
        """
           Try to enable the compression
        """
        self.server.enable_compression()
        
    @retry(3,1,2) # try 3 times to reconnect with a sleep time of 1 sec and a backoff of 2. The fourth time will wait 4 sec
    def find_folder_names(self):
        """
           depending on your account the all mail folder can be named 
           [GMAIL]/ALL Mail or [GoogleMail]/All Mail.
           Find and set the right one
        """      
        #use xlist because of localized dir names
        folders = self.server.xlist_folders()
        
        the_dir = None
        for (flags, _, the_dir) in folders:
            #non localised GMAIL_ALL
            if GIMAPFetcher.GENERIC_GMAIL_ALL in flags:
                #it could be a localized Dir name
                self.localized_folders['ALLMAIL']['loc_dir'] = the_dir
            elif the_dir in GIMAPFetcher.GENERIC_GMAIL_CHATS :
                #it could be a localized Dir name
                self.localized_folders['CHATS']['loc_dir'] = the_dir
            elif GIMAPFetcher.GENERIC_DRAFTS in flags:
                self.localized_folders['DRAFTS']['loc_dir'] = the_dir
                
        if not self.localized_folders['ALLMAIL']['loc_dir']: # all mail error
            raise Exception("Cannot find global 'All Mail' folder (maybe localized and translated into your language) ! "\
                            "Check whether 'Show in IMAP for 'All Mail' is enabled in Gmail (Go to Settings->Labels->All Mail)")
        elif not self.localized_folders['CHATS']['loc_dir'] and \
                 gmvault_utils.get_conf_defaults().getboolean("General","errors_if_chat_not_visible", False):
            raise Exception("Cannot find global 'Chats' folder ! Check whether 'Show in IMAP for 'Chats' "\
                            "is enabled in Gmail (Go to Settings->Labels->All Mail)") 
        elif not self.localized_folders['DRAFTS']['loc_dir']:
            raise Exception("Cannot find global 'Drafts' folder.")
    
    @retry(3,1,2) # try 3 times to reconnect with a sleep time of 1 sec and a backoff of 2. The fourth time will wait 4 sec
    def find_all_mail_folder(self):
        """
           depending on your account the all mail folder can be named 
           [GMAIL]/ALL Mail or [GoogleMail]/All Mail.
           Find and set the right one
        """      
        #use xlist because of localized dir names
        folders = self.server.xlist_folders()
        
        the_dir = None
        for (flags, _, the_dir) in folders:
            #non localised GMAIL_ALL
            if GIMAPFetcher.GENERIC_GMAIL_ALL in flags:
                #it could be a localized Dir name
                self.localized_folders['ALLMAIL']['loc_dir'] = the_dir
                return the_dir
        
        if not self.localized_folders['ALLMAIL']['loc_dir']:
            #Error
            raise Exception("Cannot find global 'All Mail' folder (maybe localized and translated into your language) !"\
                  " Check whether 'Show in IMAP for 'All Mail' is enabled in Gmail (Go to Settings->Labels->All Mail)")
        
    @retry(3,1,2) # try 3 times to reconnect with a sleep time of 1 sec and a backoff of 2. The fourth time will wait 4 sec
    def find_chats_folder(self):
        """
           depending on your account the chats folder can be named 
           [GMAIL]/Chats or [GoogleMail]/Chats, [GMAIL]/tous les chats ...
           Find and set the right one
           Npte: Cannot use the flags as Chats is not a system label. Thanks Google
        """
        #use xlist because of localized dir names
        folders = self.server.xlist_folders()
        
        LOG.debug("Folders = %s\n" % (folders))
        
        the_dir = None
        for (_, _, the_dir) in folders:
            #look for GMAIL Chats
            if the_dir in GIMAPFetcher.GENERIC_GMAIL_CHATS :
                #it could be a localized Dir name
                self.localized_folders['CHATS']['loc_dir'] = the_dir
                return the_dir
        
        #Error did not find Chats dir 
        if gmvault_utils.get_conf_defaults().getboolean("General", "errors_if_chat_not_visible", False):
            raise Exception("Cannot find global 'Chats' folder ! Check whether 'Show in IMAP for 'Chats' "\
                            "is enabled in Gmail (Go to Settings->Labels->All Mail)") 
       
        return None
    
    def is_visible(self, a_folder_name):
        """
           check if a folder is visible otherwise 
        """
        dummy = self.localized_folders.get(a_folder_name)
        
        if dummy and (dummy.get('loc_dir', None) is not None):
            return True
            
        if not self.printed_folder_error_msg.get(a_folder_name, None): 
            LOG.critical("Cannot find 'Chats' folder on Gmail Server. If you wish to backup your chats,"\
                         " look at the documentation to see how to configure your Gmail account.\n")
            self.printed_folder_error_msg[a_folder_name] = True
        
          
        return False

    def get_folder_name(self, a_folder_name):
        """return real folder name from generic ones"""        
        if a_folder_name not in self.FOLDER_NAMES:
            raise Exception("%s is not a predefined folder names. Please use one" % (a_folder_name) )
            
        folder = self.localized_folders.get(a_folder_name, {'loc_dir' : 'GMVNONAME'})['loc_dir']

        return folder
           
    @retry(3,1,2)  # try 3 times to reconnect with a sleep time of 1 sec and a backoff of 2. The fourth time will wait 4 sec
    def select_folder(self, a_folder_name, use_predef_names = True):
        """
           Select one of the existing folder
        """
        if use_predef_names:
            if a_folder_name not in self.FOLDER_NAMES:
                raise Exception("%s is not a predefined folder names. Please use one" % (a_folder_name) )
            
            folder = self.localized_folders.get(a_folder_name, {'loc_dir' : 'GMVNONAME'})['loc_dir']
            
            if self.current_folder != folder:
                self.server.select_folder(folder, readonly = self.readonly_folder)
                self.current_folder = folder
            
        elif self.current_folder != a_folder_name:
            self.server.select_folder(a_folder_name, readonly = self.readonly_folder)
            self.current_folder = a_folder_name
        
        return self.current_folder
        
    @retry(3,1,2) # try 3 times to reconnect with a sleep time of 1 sec and a backoff of 2. The fourth time will wait 4 sec
    def list_all_folders(self): 
        """
           Return all folders mainly for debuging purposes
        """
        return self.server.xlist_folders()
        
    @retry(3,1,2) # try 3 times to reconnect with a sleep time of 1 sec and a backoff of 2. The fourth time will wait 4 sec
    def get_capabilities(self):
        """
           return the server capabilities
        """
        if not self.server:
            raise Exception("GIMAPFetcher not connect to the GMAIL server")
        
        return self.server.capabilities()
    
    @retry(3,1,2) # try 3 times to reconnect with a sleep time of 1 sec and a backoff of 2. The fourth time will wait 4 sec
    def check_gmailness(self):
        """
           Check that the server is a gmail server
        """
        if not GIMAPFetcher.GMAIL_EXTENSION in self.get_capabilities():
            raise Exception("GIMAPFetcher is not connected to a IMAP GMAIL server. Please check host (%s) and port (%s)" \
                  % (self.host, self.port))
        
        return True
    
    @retry(3,1,2) # try 3 times to reconnect with a sleep time of 1 sec and a backoff of 2. The fourth time will wait 4 sec
    def search(self, a_criteria):
        """
           Return all found ids corresponding to the search
        """
        return self.server.search(a_criteria)
    
    @retry(3,1,2) # try 4 times to reconnect with a sleep time of 1 sec and a backoff of 2. The fourth time will wait 8 sec
    def fetch(self, a_ids, a_attributes):
        """
           Return all attributes associated to each message
        """
        return self.server.fetch(a_ids, a_attributes)
                
    
    @classmethod
    def _old_build_labels_str(cls, a_labels):
        """
           Create IMAP label string from list of given labels. 
           Convert the labels to utf7
           a_labels: List of labels
        """
        # add GMAIL LABELS
        labels_str = None
        if a_labels and len(a_labels) > 0:
            labels_str = '('
            for label in a_labels:
                if gmvault_utils.contains_any(label, ' "*'):
                    label = label.replace('"', '\\"') #replace quote with escaped quotes
                    labels_str += '\"%s\" ' % (label)
                else:
                    labels_str += '%s ' % (label)
                    #labels_str += '\"%s\" ' % (label) #check if this is always ok or not
            
            labels_str = '%s%s' % (labels_str[:-1],')')
        
        return labels_str

    @classmethod
    def _build_labels_str(cls, a_labels):
        """
           Create IMAP label string from list of given labels. 
           Convert the labels to utf7
           a_labels: List of labels
        """
        # add GMAIL LABELS
        labels_str = None
        if a_labels and len(a_labels) > 0:
            labels_str = '('
            for label in a_labels:
                label = gmvault_utils.remove_consecutive_spaces_and_strip(label)
                #add not in self.GMAIL_SPECIAL_DIRS_LOWER
                if label.lower() in cls.GMAIL_SPECIAL_DIRS_LOWER:
                    labels_str += '%s ' % (label)
                else:
                    label = label.replace('"', '\\"') #replace quote with escaped quotes
                    labels_str += '\"%s\" ' % (label)
            labels_str = '%s%s' % (labels_str[:-1],')')
        
        return labels_str
    
    @classmethod
    def _get_dir_from_labels(cls, label):
        """
           Get the dirs to create from the labels
           
           label: label name with / in it
        """
        
        dirs = []
        
        i = 0
        for lab in label.split('/'):
            lab = gmvault_utils.remove_consecutive_spaces_and_strip(lab)
            if i == 0:
                dirs.append(lab)
            else:
                dirs.append('%s/%s' % (dirs[i-1], lab))
            
            i += 1
        
        return dirs
    
    def create_gmail_labels(self, labels, existing_folders):
        """
           Create folders and subfolders on Gmail in order
           to recreate the label hierarchy before to upload emails
           Note that adding labels with +X-GM-LABELS create only nested labels
           but not nested ones. This is why this trick must be used to 
           recreate the label hierarchy
           
           labels: list of labels to create
           
        """
        
        #1.5-beta moved that out of the loop to minimize the number of calls
        #to that method. (Could go further and memoize it)
        
        #get existing directories (or label parts)
        # get in lower case because Gmail labels are case insensitive
        listed_folders   = set([ directory.lower() for (_, _, directory) in self.list_all_folders() ])
        existing_folders = listed_folders.union(existing_folders)
        reserved_labels_map = gmvault_utils.get_conf_defaults().get_dict("Restore", "reserved_labels_map", \
                              { u'migrated' : u'gmv-migrated', u'\muted' : u'gmv-muted' })
        
        

        LOG.debug("Labels to create: [%s]" % (labels))
            
        for lab in labels:
            #LOG.info("Reserved labels = %s\n" % (reserved_labels))
            #LOG.info("lab.lower = %s\n" % (lab.lower()))
            if lab.lower() in reserved_labels_map.keys(): #exclude creation of migrated label
                n_lab = reserved_labels_map.get(lab.lower(), "gmv-default-label")
                LOG.info("Warning ! label '%s' (lower or uppercase) is reserved by Gmail and cannot be used."\
                         "Use %s instead" % (lab, n_lab)) 
                lab = n_lab
                LOG.info("translated lab = %s\n" % (lab))
           
            #split all labels
            labs = self._get_dir_from_labels(lab) 
            
            for directory in labs:
                low_directory = directory.lower() #get lower case directory but store original label
                if (low_directory not in existing_folders) and (low_directory not in self.GMAIL_SPECIAL_DIRS_LOWER):
                    try:
                        if self.server.create_folder(directory) != 'Success':
                            raise Exception("Cannot create label %s: the directory %s cannot be created." % (lab, directory))
                        else:
                            LOG.debug("============== ####### Created Labels (%s)." % (directory))
                    except imaplib.IMAP4.error, error:
                        #log error in log file if it exists
                        LOG.debug(gmvault_utils.get_exception_traceback())
                        if str(error).startswith("create failed: '[ALREADYEXISTS] Duplicate folder"):
                            LOG.critical("Warning: label %s already exists on Gmail and Gmvault tried to create it."\
                                         " Ignore this issue." % (directory) )
                        else:
                            raise error
                    
                    #add created folder in folders
                    existing_folders.add(low_directory)

        #return all existing folders
        return existing_folders
    
    
    @retry(3,1,2)
    def apply_labels_to(self, imap_ids, labels):
        """
           apply one labels to x emails
        """
        # go to All Mail folder
        LOG.debug("Applying labels %s" % (labels))
        
        the_timer = gmvault_utils.Timer()
        the_timer.start()

        #utf7 the labels as they should be
        labels = [ utf7_encode(label) for label in labels ]

        labels_str = self._build_labels_str(labels) # create labels str
    
        if labels_str:  
            #has labels so update email  
            the_timer.start()
            #LOG.debug("Before to store labels %s" % (labels_str))
            id_list = ",".join(map(str, imap_ids))
            #+X-GM-LABELS.SILENT to have not returned data
            ret_code, data = self.server._imap.uid('STORE', id_list, '+X-GM-LABELS.SILENT', labels_str) #pylint: disable=W0212

            #ret_code, data = self.server._imap.uid('COPY', id_list, labels[0])
            LOG.debug("After storing labels %s. Operation time = %s s.\nret = %s\ndata=%s" \
                      % (labels_str, the_timer.elapsed_ms(),ret_code, data))

            # check if it is ok otherwise exception
            if ret_code != 'OK':
                # Try again to code the error message (do not use .SILENT)
                ret_code, data = self.server._imap.uid('STORE', id_list, '+X-GM-LABELS', labels_str) #pylint: disable=W0212
                if ret_code != 'OK':
                    raise PushEmailError("Cannot add Labels %s to emails with uids %d. Error:%s" % (labels_str, imap_ids, data))
            else:
                LOG.debug("Stored Labels %s for gm_ids %s" % (labels_str, imap_ids))
       
    def delete_gmail_labels(self, labels, force_delete = False):
        """
           Delete passed labels. Beware experimental and labels must be ordered
        """
        for label in reversed(labels):
            
            labs = self._get_dir_from_labels(label)
            
            for directory in reversed(labs):
                
                if force_delete or ( (directory.lower() not in self.GMAIL_SPECIAL_DIRS_LOWER) \
                   and self.server.folder_exists(directory) ): #call server exists each time
                    try:
                        self.server.delete_folder(directory)
                    except imaplib.IMAP4.error, _:
                        LOG.debug(gmvault_utils.get_exception_traceback())
    
    
    def erase_mailbox(self):
        """
           This is for testing purpose and cannot be used with my own mailbox
        """
        
        if self.login == "guillaume.aubert@gmail.com":
            raise Exception("Error cannot activate erase_mailbox with %s" % (self.login))

        LOG.info("Erase mailbox for account %s." % (self.login))

        LOG.info("Delete folders")

        #delete folders
        folders = self.server.xlist_folders()

        LOG.debug("Folders = %s.\n" %(folders))

        trash_folder_name = None

        for (flags, _, the_dir) in folders:
            if (u'\\Starred' in flags) or (u'\\Spam' in flags) or (u'\\Sent' in flags) \
               or (u'\\Important' in flags) or (the_dir == u'[Google Mail]/Chats') \
               or (the_dir == u'[Google Mail]') or (u'\\Trash' in flags) or \
               (u'\\Inbox' in flags) or (GIMAPFetcher.GENERIC_GMAIL_ALL in flags) or \
               (GIMAPFetcher.GENERIC_DRAFTS in flags) or (GIMAPFetcher.GENERIC_GMAIL_CHATS in flags):
                LOG.info("Ignore folder %s" % (the_dir))           

                if (u'\\Trash' in flags): #keep trash folder name
                    trash_folder_name = the_dir
            else:
                LOG.info("Delete folder %s" % (the_dir))
                self.server.delete_folder(the_dir)
        
        self.select_folder('ALLMAIL')

        #self.server.store("1:*",'+X-GM-LABELS', '\\Trash')
        #self.server._imap.uid('STORE', id_list, '+X-GM-LABELS.SILENT', '\\Trash')
        #self.server.add_gmail_labels(self, messages, labels)

        LOG.info("Move emails to Trash.")
        
        # get all imap ids in ALLMAIL
        imap_ids = self.search(GIMAPFetcher.IMAP_ALL)

        #flag all message as deleted
        #print(self.server.delete_messages(imap_ids))

        if len(imap_ids) > 0:
            self.apply_labels_to(imap_ids, ['\\Trash'])

            LOG.info("Got all imap_ids flagged to Trash : %s." % (imap_ids))

        
        else:
            LOG.info("No messages to erase.")

        LOG.info("Delete emails from Trash.")

        if trash_folder_name == None:
            raise Exception("No trash folder ???")

        self.select_folder(trash_folder_name, False)
        
        # get all imap ids in ALLMAIL
        imap_ids = self.search(GIMAPFetcher.IMAP_ALL)

        if len(imap_ids) > 0:
            res = self.server.delete_messages(imap_ids)
            LOG.debug("Delete messages result = %s" % (res))

        LOG.info("Expunge everything.")
        self.server.expunge()

    @retry(4,1,2) # try 4 times to reconnect with a sleep time of 1 sec and a backoff of 2. The fourth time will wait 8 sec    
    def push_data(self, a_folder, a_body, a_flags, a_internal_time):
        """
           Push the data
        """  
        # protection against myself
        if self.login == 'guillaume.aubert@gmail.com':
            raise Exception("Cannot push to this account")
        
        the_timer = gmvault_utils.Timer()
        the_timer.start()
        LOG.debug("Before to Append email contents")
        #import sys  #to print the msg in stdout
        #import codecs
        #sys.stdout = codecs.getwriter('utf-8')(sys.__stdout__) 
        #msg = "a_folder = %s, a_flags = %s" % (a_folder.encode('utf-8'), a_flags)
        #msg = "a_folder = %s" % (a_folder.encode('utf-8'))
        #msg = msg.encode('utf-8')
        #print(msg)
        res = self.server.append(a_folder, a_body, a_flags, a_internal_time)
    
        LOG.debug("Appended data with flags %s and internal time %s. Operation time = %s.\nres = %s\n" \
                  % (a_flags, a_internal_time, the_timer.elapsed_ms(), res))
        
        # check res otherwise Exception
        if '(Success)' not in res:
            raise PushEmailError("GIMAPFetcher cannot restore email in %s account." %(self.login))
        
        match = GIMAPFetcher.APPENDUID_RE.match(res)
        if match:
            result_uid = int(match.group(1))
            LOG.debug("result_uid = %s" %(result_uid))
        else:
            # do not quarantine it because it seems to be done by Google Mail to forbid data uploading.
            raise PushEmailError("No email id returned by IMAP APPEND command. Quarantine this email.", quarantined = True)
        
        return result_uid          
         
    @retry(4,1,2) # try 4 times to reconnect with a sleep time of 1 sec and a backoff of 2. The fourth time will wait 8 sec
    def push_email(self, a_body, a_flags, a_internal_time, a_labels):
        """
           Push a complete email body 
        """
        #protection against myself
        if self.login == 'guillaume.aubert@gmail.com':
            raise Exception("Cannot push to this account")
    
        the_t = gmvault_utils.Timer()
        the_t.start()
        LOG.debug("Before to Append email contents")
        #res = self.server.append(self.current_folder, a_body, a_flags, a_internal_time)
        res = self.server.append(u'[Google Mail]/All Mail', a_body, a_flags, a_internal_time)
    
        LOG.debug("Appended data with flags %s and internal time %s. Operation time = %s.\nres = %s\n" \
                  % (a_flags, a_internal_time, the_t.elapsed_ms(), res))
        
        # check res otherwise Exception
        if '(Success)' not in res:
            raise PushEmailError("GIMAPFetcher cannot restore email in %s account." %(self.login))
        
        match = GIMAPFetcher.APPENDUID_RE.match(res)
        if match:
            result_uid = int(match.group(1))
            LOG.debug("result_uid = %s" %(result_uid))
        else:
            # do not quarantine it because it seems to be done by Google Mail to forbid data uploading.
            raise PushEmailError("No email id returned by IMAP APPEND command. Quarantine this email.", quarantined = True)
        
        labels_str = self._build_labels_str(a_labels)
        
        if labels_str:  
            #has labels so update email  
            the_t.start()
            LOG.debug("Before to store labels %s" % (labels_str))
            self.server.select_folder(u'[Google Mail]/All Mail', readonly = self.readonly_folder) # go to current folder
            LOG.debug("Changing folders. elapsed %s s\n" % (the_t.elapsed_ms()))
            the_t.start()
            ret_code, data = self.server._imap.uid('STORE', result_uid, '+X-GM-LABELS', labels_str) #pylint: disable=W0212
            #ret_code = self.server._store('+X-GM-LABELS', [result_uid],labels_str)
            LOG.debug("After storing labels %s. Operation time = %s s.\nret = %s\ndata=%s" \
                      % (labels_str, the_t.elapsed_ms(),ret_code, data))
            
            LOG.debug("Stored Labels %s in gm_id %s" % (labels_str, result_uid))

            self.server.select_folder(u'[Google Mail]/Drafts', readonly = self.readonly_folder) # go to current folder
        
            # check if it is ok otherwise exception
            if ret_code != 'OK':
                raise PushEmailError("Cannot add Labels %s to email with uid %d. Error:%s" % (labels_str, result_uid, data))
        
        return result_uid

def decode_labels(labels):
    """
       Decode labels when they are received as utf7 entities or numbers
    """
    new_labels = []
    for label in labels:
        if isinstance(label, (int, long, float, complex)):
            label = str(label) 
        new_labels.append(utf7_decode(label))

    return new_labels

# utf7 conversion functions
def utf7_encode(s): #pylint: disable=C0103
    """encode in utf7"""
    if isinstance(s, str) and sum(n for n in (ord(c) for c in s) if n > 127):
        raise ValueError("%r contains characters not valid in a str folder name. "
                              "Convert to unicode first?" % s)

    r = [] #pylint: disable=C0103
    _in = []
    for c in s: #pylint: disable=C0103
        if ord(c) in (range(0x20, 0x26) + range(0x27, 0x7f)):
            if _in:
                r.extend(['&', utf7_modified_base64(''.join(_in)), '-'])
                del _in[:]
            r.append(str(c))
        elif c == '&':
            if _in:
                r.extend(['&', utf7_modified_base64(''.join(_in)), '-'])
                del _in[:]
            r.append('&-')
        else:
            _in.append(c)
    if _in:
        r.extend(['&', utf7_modified_base64(''.join(_in)), '-'])
    return ''.join(r)


def utf7_decode(s): #pylint: disable=C0103
    """decode utf7"""
    r = [] #pylint: disable=C0103
    decode = []
    for c in s: #pylint: disable=C0103
        if c == '&' and not decode:
            decode.append('&')
        elif c == '-' and decode:
            if len(decode) == 1:
                r.append('&')
            else:
                r.append(utf7_modified_unbase64(''.join(decode[1:])))
            decode = []
        elif decode:
            decode.append(c)
        else:
            r.append(c)
    if decode:
        r.append(utf7_modified_unbase64(''.join(decode[1:])))
    out = ''.join(r)

    if not isinstance(out, unicode):
        out = unicode(out, 'latin-1')
    return out


def utf7_modified_base64(s): #pylint: disable=C0103
    """utf7 base64"""
    s_utf7 = s.encode('utf-7')
    return s_utf7[1:-1].replace('/', ',')


def utf7_modified_unbase64(s): #pylint: disable=C0103
    """ utf7 unbase64"""
    s_utf7 = '+' + s.replace(',', '/') + '-'
    return s_utf7.decode('utf-7')


########NEW FILE########
__FILENAME__ = log_utils
'''
    Gmvault: a tool to backup and restore your gmail account.
    Copyright (C) <2011-2013>  <guillaume Aubert (guillaume dot aubert at gmail do com)>

    This program is free software: you can redistribute it and/or modify
    it under the terms of the GNU Affero General Public License as
    published by the Free Software Foundation, either version 3 of the
    License, or (at your option) any later version.

    This program is distributed in the hope that it will be useful,
    but WITHOUT ANY WARRANTY; without even the implied warranty of
    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
    GNU Affero General Public License for more details.

    You should have received a copy of the GNU Affero General Public License
    along with this program.  If not, see <http://www.gnu.org/licenses/>.

'''
import sys
import os

import logbook

#different types of LoggerFactory
STANDALONE = "STANDALONE"


class StdoutHandler(logbook.StreamHandler):
    """A handler that writes to what is currently at stdout. At the first
glace this appears to just be a :class:`StreamHandler` with the stream
set to :data:`sys.stdout` but there is a difference: if the handler is
created globally and :data:`sys.stdout` changes later, this handler will
point to the current `stdout`, whereas a stream handler would still
point to the old one.
"""

    def __init__(self, level=logbook.base.NOTSET, format_string=None, a_filter = None, bubble=False): #pylint: disable=W0212
        super(StdoutHandler, self).__init__(logbook.base._missing, level, \
                                            format_string, None, a_filter, bubble )

    @property
    def stream(self): #pylint: disable=W0212
        """
           Return the stream where to write
        """
        return sys.stdout

#default log file
DEFAULT_LOG = "%s/gmvault.log" % (os.getenv("HOME", "."))

class LogbookLoggerFactory(object):
    """
       Factory for creating the right logbook handler
    """
    
    def __init__(self):
        pass
    
    def setup_cli_app_handler(self, activate_log_file=False, console_level= 'CRITICAL', \
                              file_path=DEFAULT_LOG, log_file_level = 'DEBUG'):
        """
           Setup a handler for communicating with the user and still log everything in a logfile
        """
        null_handler = logbook.NullHandler()
        
        out_handler  = StdoutHandler(format_string='{record.message}', level = console_level , bubble = False)
        
        # first stack null handler to not have anything else logged 
        null_handler.push_application()
        
        # add output Handler
        out_handler.push_application() 
        
        # add file Handler
        if activate_log_file:
            file_handler = logbook.FileHandler(file_path, mode='w', format_string=\
                           '[{record.time:%Y-%m-%d %H:%M}]:{record.level_name}:{record.channel}:{record.message}',\
                                                level = log_file_level, bubble = True)
            
            file_handler.push_application()
    
    def setup_simple_file_handler(self, file_path):
        """
           Push a file handler logging only the message (no timestamp)
        """
        null_handler = logbook.NullHandler()
        
        handler      = logbook.FileHandler(file_path, format_string='{record.message}', level = 2, bubble = False)
         
        # first stack null handler to not have anything else logged 
        null_handler.push_application()
        # add Stderr Handler
        handler.push_application() 
    
    def setup_simple_stdout_handler(self):
        """
           Push a stderr handler logging only the message (no timestamp)
        """
        
        null_handler = logbook.NullHandler()
        
        handler      = StdoutHandler(format_string='{record.message}', level = 2, bubble = False)
         
        # first stack null handler to not have anything else logged 
        null_handler.push_application()
        # add Stderr Handler
        handler.push_application() 
    
    def setup_simple_stderr_handler(self):
        """
           Push a stderr handler logging only the message (no timestamp)
        """
        
        null_handler = logbook.NullHandler()
        
        handler      = logbook.StderrHandler(format_string='{record.message}', level = 2, bubble = False)
         
        # first stack null handler to not have anything else logged 
        null_handler.push_application()
        # add Stderr Handler
        handler.push_application() 
    
    def get_logger(self, name):
        """
           Return a logbook logger
        """
        return logbook.Logger(name)

class LoggerFactory(object):
    '''
       My Logger Factory
    '''
    _factory = LogbookLoggerFactory()
    _created = False
    
    @classmethod
    def get_factory(cls, the_type):
        """
           Get logger factory
        """
        
        if cls._created:
            return cls._factory
        
        if the_type == STANDALONE:
            cls._factory = LogbookLoggerFactory()
            cls._created = True
        else:
            raise Exception("LoggerFactory type %s is unknown." % (the_type))
        
        return cls._factory
    
    @classmethod
    def get_logger(cls, name):
        """
          Simply return a logger
        """
        return cls._factory.get_logger(name)
    
    
    @classmethod
    def setup_simple_stderr_handler(cls, the_type):
        """
           Push a stderr handler logging only the message (no timestamp)
        """
        cls.get_factory(the_type).setup_simple_stderr_handler()
    
    @classmethod
    def setup_simple_stdout_handler(cls, the_type):
        """
           Push a stderr handler logging only the message (no timestamp)
        """
        cls.get_factory(the_type).setup_simple_stdout_handler()
        
    @classmethod
    def setup_simple_file_handler(cls, the_type, file_path):
        """
           Push a file handler logging only the message (no timestamp)
        """
        cls.get_factory(the_type).setup_simple_file_handler(file_path)
        
    @classmethod
    def setup_cli_app_handler(cls, the_type, activate_log_file=False, \
                              console_level= 'CRITICAL', file_path=DEFAULT_LOG,\
                               log_file_level = 'DEBUG'):
        """
           init logging engine
        """
        cls.get_factory(the_type).setup_cli_app_handler(activate_log_file, \
                                                    console_level, \
                                                    file_path, log_file_level)
        

########NEW FILE########
__FILENAME__ = mod_imap
# -*- coding: utf-8 -*-
'''
    Gmvault: a tool to backup and restore your gmail account.
    Copyright (C) <2011-2013>  <guillaume Aubert (guillaume dot aubert at gmail do com)>

    This program is free software: you can redistribute it and/or modify
    it under the terms of the GNU Affero General Public License as
    published by the Free Software Foundation, either version 3 of the
    License, or (at your option) any later version.

    This program is distributed in the hope that it will be useful,
    but WITHOUT ANY WARRANTY; without even the implied warranty of
    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
    GNU Affero General Public License for more details.

    You should have received a copy of the GNU Affero General Public License
    along with this program.  If not, see <http://www.gnu.org/licenses/>.

    Contains the class monkey patching IMAPClient and imaplib

'''
import zlib
import time
import datetime
import re
import socket
import ssl
import cStringIO
import os

import imaplib  #for the exception
import imapclient

#enable imap debugging if GMV_IMAP_DEBUG is set 
if os.getenv("GMV_IMAP_DEBUG"):
    imaplib.Debug = 4 #enable debugging

#to enable imap debugging and see all command
#imaplib.Debug = 4 #enable debugging

INTERNALDATE_RE = re.compile(r'.*INTERNALDATE "'
r'(?P<day>[ 0123][0-9])-(?P<mon>[A-Z][a-z][a-z])-(?P<year>[0-9][0-9][0-9][0-9])'
r' (?P<hour>[0-9][0-9]):(?P<min>[0-9][0-9]):(?P<sec>[0-9][0-9])'
r' (?P<zonen>[-+])(?P<zoneh>[0-9][0-9])(?P<zonem>[0-9][0-9])'
r'"')

MON2NUM = {'Jan': 1, 'Feb': 2, 'Mar': 3, 'Apr': 4, 'May': 5, 'Jun': 6,
        'Jul': 7, 'Aug': 8, 'Sep': 9, 'Oct': 10, 'Nov': 11, 'Dec': 12}

#need to monkey patch _convert_INTERNALDATE to work with imaplib2
#modification of IMAPClient
def mod_convert_INTERNALDATE(date_string, normalise_times=True):#pylint: disable=C0103
    """
       monkey patched convert_INTERNALDATE
    """
    mon = INTERNALDATE_RE.match('INTERNALDATE "%s"' % date_string)
    if not mon:
        raise ValueError("couldn't parse date %r" % date_string)
    
    zoneh = int(mon.group('zoneh'))
    zonem = (zoneh * 60) + int(mon.group('zonem'))
    if mon.group('zonen') == '-':
        zonem = -zonem
    timez = imapclient.fixed_offset.FixedOffset(zonem)
    
    year    = int(mon.group('year'))
    the_mon = MON2NUM[mon.group('mon')]
    day     = int(mon.group('day'))
    hour    = int(mon.group('hour'))
    minute  = int(mon.group('min'))
    sec = int(mon.group('sec'))
    
    the_dt = datetime.datetime(year, the_mon, day, hour, minute, sec, 0, timez)
    
    if normalise_times:
        # Normalise to host system's timezone
        return the_dt.astimezone(imapclient.fixed_offset.FixedOffset.for_system()).replace(tzinfo=None)
    return the_dt

#monkey patching is done here
imapclient.response_parser._convert_INTERNALDATE = mod_convert_INTERNALDATE #pylint: disable=W0212

#monkey patching add compress in COMMANDS of imap
imaplib.Commands['COMPRESS'] = ('AUTH', 'SELECTED')

class IMAP4COMPSSL(imaplib.IMAP4_SSL): #pylint:disable=R0904
    """
       Add support for compression inspired by inspired by http://www.janeelix.com/piers/python/py2html.cgi/piers/python/imaplib2
    """
    SOCK_TIMEOUT = 70 # set a socket timeout of 70 sec to avoid for ever blockage in ssl.read

    def __init__(self, host = '', port = imaplib.IMAP4_SSL_PORT, keyfile = None, certfile = None):
        """
           constructor
        """
        self.compressor = None
        self.decompressor = None
        
        imaplib.IMAP4_SSL.__init__(self, host, port, keyfile, certfile)
        
    def activate_compression(self):
        """
           activate_compressing()
           Enable deflate compression on the socket (RFC 4978).
        """
        # rfc 1951 - pure DEFLATE, so use -15 for both windows
        self.decompressor = zlib.decompressobj(-15)
        self.compressor   = zlib.compressobj(zlib.Z_DEFAULT_COMPRESSION, zlib.DEFLATED, -15)
        
    def open(self, host = '', port = imaplib.IMAP4_SSL_PORT): 
        """Setup connection to remote server on "host:port".
           (default: localhost:standard IMAP4 SSL port).
           This connection will be used by the routines:
           read, readline, send, shutdown.
        """
        self.host   = host
        self.port   = port

        self.sock   = socket.create_connection((host, port), self.SOCK_TIMEOUT) #add so_timeout  

        #self.sock.setsockopt(socket.SOL_TCP, socket.TCP_NODELAY, 1) #try to set TCP NO DELAY to increase performances

        self.sslobj = ssl.wrap_socket(self.sock, self.keyfile, self.certfile)
        #self.sslobj = ssl.wrap_socket(self.sock, self.keyfile, self.certfile, suppress_ragged_eofs = False)
        
        # This is the last correction added to avoid memory fragmentation in imaplib
        # makefile creates a file object that makes use of cStringIO to avoid mem fragmentation
        # it could be used without the compression 
        # (maybe make 2 set of methods without compression and with compression)
        #self.file   = self.sslobj.makefile('rb')

    def new_read(self, size):
        """
            Read 'size' bytes from remote.
            Call _intern_read that takes care of the compression
        """
        
        chunks = cStringIO.StringIO() #use cStringIO.cStringIO to avoir too much fragmentation
        read = 0
        while read < size:
            try:
                data = self._intern_read(min(size-read, 16384)) #never ask more than 16384 because imaplib can do it
            except ssl.SSLError, err:
                print("************* SSLError received %s" % (err)) 
                raise self.abort('Gmvault ssl socket error: EOF. Connection lost, reconnect.')
            read += len(data)
            chunks.write(data)
        
        return chunks.getvalue() #return the cStringIO content
    
    def read(self, size):
        """
            Read 'size' bytes from remote.
            Call _intern_read that takes care of the compression
        """
        
        chunks = cStringIO.StringIO() #use cStringIO.cStringIO to avoir too much fragmentation
        read = 0
        while read < size:
            data = self._intern_read(min(size-read, 16384)) #never ask more than 16384 because imaplib can do it
            if not data: 
                #to avoid infinite looping due to empty string returned
                raise self.abort('Gmvault ssl socket error: EOF. Connection lost, reconnect.') 
            read += len(data)
            chunks.write(data)
        
        return chunks.getvalue() #return the cStringIO content
  
    def _intern_read(self, size):
        """
            Read at most 'size' bytes from remote.
            Takes care of the compression
        """
        if self.decompressor is None:
            return self.sslobj.read(size)

        if self.decompressor.unconsumed_tail:
            data = self.decompressor.unconsumed_tail
        else:
            data = self.sslobj.read(8192) #Fixed buffer size. maybe change to 16384

        return self.decompressor.decompress(data, size)
        
    def readline(self):
        """Read line from remote."""
        line = cStringIO.StringIO() #use cStringIO to avoid memory fragmentation
        while 1:
            #make use of read that takes care of the compression
            #it could be simplified without compression
            char = self.read(1) 
            line.write(char)
            if char in ("\n", ""): 
                return line.getvalue()
    
    def shutdown(self):
        """Close I/O established in "open"."""
        #self.file.close() #if file created
        self.sock.close()
        
      
    def send(self, data):
        """send(data)
        Send 'data' to remote."""
        if self.compressor is not None:
            data = self.compressor.compress(data)
            data += self.compressor.flush(zlib.Z_SYNC_FLUSH)
        self.sslobj.sendall(data)
       
def seq_to_parenlist(flags):
    """Convert a sequence of strings into parenthised list string for
    use with IMAP commands.
    """
    if isinstance(flags, str):
        flags = (flags,)
    elif not isinstance(flags, (tuple, list)):
        raise ValueError('invalid flags list: %r' % flags)
    return '(%s)' % ' '.join(flags)
    
class MonkeyIMAPClient(imapclient.IMAPClient): #pylint:disable=R0903,R0904
    """
       Need to extend the IMAPClient to do more things such as compression
       Compression inspired by http://www.janeelix.com/piers/python/py2html.cgi/piers/python/imaplib2
    """
    
    def __init__(self, host, port=None, use_uid=True, need_ssl=False):
        """
           constructor
        """
        super(MonkeyIMAPClient, self).__init__(host, port, use_uid, need_ssl)
    
    def _create_IMAP4(self): #pylint:disable=C0103
        """
           Factory method creating an IMAPCOMPSSL or a standard IMAP4 Class
        """
        imap_class = self.ssl and IMAP4COMPSSL or imaplib.IMAP4
        return imap_class(self.host, self.port)
    
    def xoauth_login(self, xoauth_cred ):
        """
           Connect with xoauth
           Redefine this method to suppress dependency to oauth2 (non-necessary)
        """

        typ, data = self._imap.authenticate('XOAUTH', lambda x: xoauth_cred)
        self._checkok('authenticate', typ, data)
        return data[0]  
    
    def search(self, criteria): #pylint: disable=W0221
        """
           Perform a imap search or gmail search
        """
        if criteria.get('type','') == 'imap':
            #encoding criteria in utf-8
            req     = criteria['req'].encode('utf-8')
            charset = 'utf-8'
            return super(MonkeyIMAPClient, self).search(req, charset)
        elif criteria.get('type','') == 'gmail':
            return self.gmail_search(criteria.get('req',''))
        else:
            raise Exception("Unknown search type %s" % (criteria.get('type','no request type passed')))
        
    def gmail_search(self, criteria):
        """
           perform a search with gmailsearch criteria.
           eg, subject:Hello World
        """  
        criteria = criteria.replace('\\', '\\\\')
        criteria = criteria.replace('"', '\\"')

        #working but cannot send that understand when non ascii chars are used
        #args = ['CHARSET', 'utf-8', 'X-GM-RAW', '"%s"' % (criteria)]
        #typ, data = self._imap.uid('SEARCH', *args)

        #working Literal search 
        self._imap.literal = '"%s"' % (criteria)
        self._imap.literal = imaplib.MapCRLF.sub(imaplib.CRLF, self._imap.literal)
        self._imap.literal = self._imap.literal.encode("utf-8")
 
        #use uid to keep the imap ids consistent
        args = ['CHARSET', 'utf-8', 'X-GM-RAW']
        typ, data = self._imap.uid('SEARCH', *args) #pylint: disable=W0142
        
        self._checkok('search', typ, data)
        if data == [None]: # no untagged responses...
            return [ ]

        return [ long(i) for i in data[0].split() ]
    
    def append(self, folder, msg, flags=(), msg_time=None):
        """Append a message to *folder*.

        *msg* should be a string contains the full message including
        headers.

        *flags* should be a sequence of message flags to set. If not
        specified no flags will be set.

        *msg_time* is an optional datetime instance specifying the
        date and time to set on the message. The server will set a
        time if it isn't specified. If *msg_time* contains timezone
        information (tzinfo), this will be honoured. Otherwise the
        local machine's time zone sent to the server.

        Returns the APPEND response as returned by the server.
        """
        if msg_time:
            time_val = time.mktime(msg_time.timetuple())
        else:
            time_val = None

        flags_list = seq_to_parenlist(flags)

        typ, data = self._imap.append(self._encode_folder_name(folder) if folder else None,
                                      flags_list, time_val, msg)
        self._checkok('append', typ, data)

        return data[0]
    
    def enable_compression(self):
        """
        enable_compression()
        Ask the server to start compressing the connection.
        Should be called from user of this class after instantiation, as in:
            if 'COMPRESS=DEFLATE' in imapobj.capabilities:
                imapobj.enable_compression()
        """
        ret_code, _ = self._imap._simple_command('COMPRESS', 'DEFLATE') #pylint: disable=W0212
        if ret_code == 'OK':
            self._imap.activate_compression()
        else:
            #no errors for the moment
            pass

        

########NEW FILE########
__FILENAME__ = progress_test
import time
import sys

def progress_2():
	"""
	"""
	percents = 0
	to_write = "Progress: [%s ]\r" % (percents)
	sys.stdout.write(to_write)
	sys.stdout.flush()

	steps = 100

	for i in xrange(steps):
		time.sleep(0.1)
		percents += 1
		#sys.stdout.write("\b" * (len(to_write)))
		to_write = "Progress: [%s percents]\r" % (percents)
		sys.stdout.write(to_write)
		sys.stdout.flush()



def progress_1():
	"""
	   progress_1
	"""
	toolbar_width = 100

	# setup toolbar
	sys.stdout.write("[%s]" % (" " * toolbar_width))
	sys.stdout.flush()
	sys.stdout.write("\b" * (toolbar_width+1)) # return to start of line, after '['

	for i in xrange(toolbar_width):
		time.sleep(0.1) # do real work here
		# update the bar
		sys.stdout.write("-")
		sys.stdout.flush()

	sys.stdout.write("\n")

if __name__ == '__main__':
	progress_2()

########NEW FILE########
__FILENAME__ = test_utils
# -*- coding: utf-8 -*-
'''
    Gmvault: a tool to backup and restore your gmail account.
    Copyright (C) <2011-2013>  <guillaume Aubert (guillaume dot aubert at gmail do com)>

    This program is free software: you can redistribute it and/or modify
    it under the terms of the GNU Affero General Public License as
    published by the Free Software Foundation, either version 3 of the
    License, or (at your option) any later version.

    This program is distributed in the hope that it will be useful,
    but WITHOUT ANY WARRANTY; without even the implied warranty of
    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
    GNU Affero General Public License for more details.

    You should have received a copy of the GNU Affero General Public License
    along with this program.  If not, see <http://www.gnu.org/licenses/>.

'''
import base64
import os
import datetime
import hashlib

import gmv.gmvault as gmvault
import gmv.imap_utils       as imap_utils
import gmv.credential_utils as cred_utils
import gmv.gmvault_db as gmvault_db
import gmv.gmvault_utils    as gmvault_utils


def check_remote_mailbox_identical_to_local(the_self, gmvaulter, extra_labels = []): #pylint: disable=C0103,R0912,R0914,R0915
    """
       Check that the remote mailbox is identical to the local one attached
       to gmvaulter
       Need a connected gmvaulter
    """
    # get all email data from gmvault-db
    pivot_dir  = None
    gmail_ids  = gmvaulter.gstorer.get_all_existing_gmail_ids(pivot_dir)

    print("gmail_ids = %s\n" % (gmail_ids))
    
    #need to check that all labels are there for emails in essential
    gmvaulter.src.select_folder('ALLMAIL')
    
    # check the number of id on disk 
    imap_ids = gmvaulter.src.search({ 'type' : 'imap', 'req' : 'ALL'}) #get everything
    
    the_self.assertEquals(len(imap_ids), \
                      len(gmail_ids), \
                      "Error. Should have the same number of emails: local nb of emails %d,"\
                      " remote nb of emails %d" % (len(gmail_ids), len(imap_ids)))

    for gm_id in gmail_ids:

        print("Fetching id %s with request %s" % (gm_id, imap_utils.GIMAPFetcher.GET_ALL_BUT_DATA))
        #get disk_metadata
        disk_metadata   = gmvaulter.gstorer.unbury_metadata(gm_id)

        print("disk metadata %s\n" % (disk_metadata))

        #date     = disk_metadata['internal_date'].strftime('"%d %b %Y"')
        subject  = disk_metadata.get('subject', None)
        msgid    = disk_metadata.get('msg_id', None)
        received = disk_metadata.get('x_gmail_received', None)

        req = "("
        has_something = False

        #if date:
        #    req += 'HEADER DATE {date}'.format(date=date)
        #    has_something = True

        if subject:
            #split on ' when contained in subject to keep only the first part
            subject = subject.split("'")[0]
            subject = subject.split('"')[0]
            if has_something: #add extra space if it has a date
                req += ' ' 
            req += 'SUBJECT "{subject}"'.format(subject=subject.strip().encode('utf-8'))
            has_something = True

        if msgid:
            if has_something: #add extra space if it has a date
                req += ' ' 
            req += 'HEADER MESSAGE-ID {msgid}'.format(msgid=msgid.strip())
            has_something = True
        
        if received:
            if has_something:
                req += ' '
                req += 'HEADER X-GMAIL-RECEIVED {received}'.format(received=received.strip())
                has_something = True
        
        req += ")"

        print("Req = %s\n" % (req))

        imap_ids = gmvaulter.src.search({ 'type' : 'imap', 'req': req, 'charset': 'utf-8'})

        print("imap_ids = %s\n" % (imap_ids))

        if len(imap_ids) != 1:
            the_self.fail("more than one imap_id (%s) retrieved for request %s" % (imap_ids, req))

        imap_id = imap_ids[0]
        
        # get online_metadata 
        online_metadata = gmvaulter.src.fetch(imap_id, \
                                              imap_utils.GIMAPFetcher.GET_ALL_BUT_DATA) 

        print("online_metadata = %s\n" % (online_metadata))
        print("disk_metadata = %s\n"   % (disk_metadata))

        header_fields = online_metadata[imap_id]['BODY[HEADER.FIELDS (MESSAGE-ID SUBJECT X-GMAIL-RECEIVED)]']
        
        subject, msgid, received = gmvault_db.GmailStorer.parse_header_fields(header_fields)

        #compare metadata
        the_self.assertEquals(subject, disk_metadata.get('subject', None))
        the_self.assertEquals(msgid,   disk_metadata.get('msg_id', None))
        the_self.assertEquals(received, disk_metadata.get('x_gmail_received', None))

        # check internal date it is plus or minus 1 hour
        online_date   = online_metadata[imap_id].get('INTERNALDATE', None) 
        disk_date     = disk_metadata.get('internal_date', None) 

        if online_date != disk_date:
            min_date = disk_date - datetime.timedelta(hours=1)
            max_date = disk_date + datetime.timedelta(hours=1)
            
            if min_date <= online_date <= max_date:
                print("online_date (%s) and disk_date (%s) differs but "\
                      "within one hour. This is OK (timezone pb) *****" % (online_date, disk_date))
            else:
                the_self.fail("online_date (%s) and disk_date (%s) are different" % (online_date, disk_date))

        #check labels
        disk_labels   = disk_metadata.get('labels', None)
        #add extra labels
        for x_lab in extra_labels:
            disk_labels.append(x_lab)

        online_labels = imap_utils.decode_labels(online_metadata[imap_id].get('X-GM-LABELS', None)) 

        #clean potential labels with multiple spaces
        disk_labels   = [ gmvault_utils.remove_consecutive_spaces_and_strip(label) for label in disk_labels ]
        online_labels = [ gmvault_utils.remove_consecutive_spaces_and_strip(label) for label in online_labels ]

        if not disk_labels: #no disk_labels check that there are no online_labels
            the_self.assertTrue(not online_labels)

        print("disk_labels = %s\n" % (disk_labels))
        print("online_labels = %s\n" % (online_labels))
        the_self.assertEquals(len(disk_labels), len(online_labels))

        for label in disk_labels:
            #change label Migrated (lower and uppercase) to gmv-migrated because reserved by Gmail
            if label.lower() == "migrated":
                label = "gmv-migrated"
            elif label.lower() == r"\muted":
                label = "gmv-muted"
            if label not in online_labels:
                the_self.fail("label %s should be in online_labels %s as"\
                              " it is in disk_labels %s" % (label, online_labels, disk_labels))

        # check flags
        disk_flags   = disk_metadata.get('flags', None)
        online_flags = online_metadata[imap_id].get('FLAGS', None) 

        if not disk_flags: #no disk flags
            the_self.assertTrue(not online_flags)

        the_self.assertEquals(len(disk_flags), len(online_flags))

        for flag in disk_flags:
            if flag not in online_flags:
                the_self.fail("flag %s should be in "\
                              "online_flags %s as it is in disk_flags %s" \
                              % (flag, online_flags, disk_flags))        

def find_identical_emails(gmvaulter_a): #pylint: disable=R0914
    """
       Find emails that are identical
    """
    # check all ids one by one
    gmvaulter_a.src.select_folder('ALLMAIL')
    
    # check the number of id on disk 
    imap_ids_a = gmvaulter_a.src.search({ 'type' : 'imap', 'req' : 'ALL'}) 
    
    batch_size = 1000

    batch_fetcher_a = gmvault.IMAPBatchFetcher(gmvaulter_a.src, imap_ids_a, \
                      gmvaulter_a.error_report, imap_utils.GIMAPFetcher.GET_ALL_BUT_DATA, \
                      default_batch_size = batch_size)
    
    print("Got %d emails in gmvault_a(%s).\n" % (len(imap_ids_a), gmvaulter_a.login))
    
    identicals = {}  

    in_db = {}
    
    total_processed = 0

    imap_ids = gmvaulter_a.src.search({ 'type' : 'imap', \
               'req' : '(HEADER MESSAGE-ID 1929235391.1106286872672.JavaMail.wserver@disvds016)'})

    print("Len(imap_ids): %d, imap_ids = %s" % (len(imap_ids), imap_ids))

    # get all gm_id for fetcher_b
    for gm_ids in batch_fetcher_a:
        cpt = 0
        #print("gm_ids = %s\n" % (gm_ids))
        print("Process a new batch (%d). Total processed:%d.\n" % (batch_size, total_processed))
        for one_id in gm_ids:
            if cpt % 50 == 0:
                print("look for %s" % (one_id))
            header_fields = gm_ids[one_id]['BODY[HEADER.FIELDS (MESSAGE-ID SUBJECT X-GMAIL-RECEIVED)]']
        
            subject, msgid, received = gmvault_db.GmailStorer.parse_header_fields(header_fields)
            labels        = gm_ids[one_id]['X-GM-LABELS']
            date_internal = gm_ids[one_id]['INTERNALDATE'] 

            if not in_db.get(msgid, None):
                in_db[msgid] = [{'subject': subject, 'received': received, \
                                 'gmid': gm_ids[one_id]['X-GM-MSGID'], \
                                 'date': date_internal , 'labels': labels}]  
            else:
                in_db[msgid].append({'subject': subject, 'received': received, \
                             'gmid': gm_ids[one_id]['X-GM-MSGID'], \
                             'date': date_internal , 'labels': labels}) 
                print("identical found msgid %s : %s" \
                      % (msgid, {'subject': subject, \
                        'received': received, \
                        'gmid': gm_ids[one_id]['X-GM-MSGID'],\
                        'date': date_internal , 'labels': labels}))
                
            cpt += 1 
        total_processed += batch_size

    #create list of identicals
    for msgid in in_db:
        if len(in_db[msgid]) > 1:
            identicals[msgid] = in_db[msgid]

    #print identicals
    print("Found %d identicals" % (len(identicals)))
    for msgid in identicals:
        print("== MSGID ==: %s" % (msgid))
        for vals in identicals[msgid]:
            print("===========> gmid: %s ### date: %s ### subject: %s ### "\
                  "labels: %s ### received: %s" \
                  % (vals.get('gmid',None), vals.get('date', None),\
                  vals.get('subject',None), vals.get('labels', None), \
                  vals.get('received',None)))
            #print("vals:%s" % (vals))
        print("\n")
        
    #print("Identical emails:\n%s" % (identicals))   

def diff_online_mailboxes(gmvaulter_a, gmvaulter_b): #pylint: disable=R0912, R0914
    """
       Diff 2 mailboxes
    """
    # check all ids one by one
    gmvaulter_a.src.select_folder('ALLMAIL')
    gmvaulter_b.src.select_folder('ALLMAIL')
    
    # check the number of id on disk 
    imap_ids_a = gmvaulter_a.src.search({ 'type' : 'imap', 'req' : 'ALL'}) 
    imap_ids_b = gmvaulter_b.src.search({ 'type' : 'imap', 'req' : 'ALL'}) 
    
    batch_size = 700

    batch_fetcher_a = gmvault.IMAPBatchFetcher(gmvaulter_a.src, imap_ids_a, gmvaulter_a.error_report, \
                                               imap_utils.GIMAPFetcher.GET_ALL_BUT_DATA, \
                                               default_batch_size = batch_size)
    
    batch_fetcher_b = gmvault.IMAPBatchFetcher(gmvaulter_b.src, imap_ids_b, gmvaulter_b.error_report, \
                                               imap_utils.GIMAPFetcher.GET_ALL_BUT_DATA, \
                                               default_batch_size = batch_size)
    
    print("Got %d emails in gmvault_a(%s).\n" % (len(imap_ids_a), gmvaulter_a.login))
    print("Got %d emails in gmvault_b(%s).\n" % (len(imap_ids_b), gmvaulter_b.login))
    
    if len(imap_ids_a) != len(imap_ids_b):
        print("Oh Oh, gmvault_a has %s emails and gmvault_b has %s emails\n" \
              % (len(imap_ids_a), len(imap_ids_b)))
    else:
        print("Both databases has %d emails." % (len(imap_ids_a)))
    
    diff_result = { "in_a" : {},
                    "in_b" : {},
                  }  
    
    gm_ids_b = {}
    total_processed = 0
    # get all gm_id for fetcher_b
    for gm_ids in batch_fetcher_b:
        #print("gm_ids = %s\n" % (gm_ids))
        print("Process a new batch (%d). Total processed:%d.\n" % (batch_size, total_processed))
        for one_id in gm_ids:
            gm_id = gm_ids[one_id]['X-GM-MSGID']
            
            header_fields = gm_ids[one_id]['BODY[HEADER.FIELDS (MESSAGE-ID SUBJECT X-GMAIL-RECEIVED)]']
        
            subject, msgid, received = gmvault_db.GmailStorer.parse_header_fields(header_fields)
            
            the_hash = hashlib.md5()
            if received:
                the_hash.update(received)
            
            if subject:
                the_hash.update(subject)
                
            if msgid:
                the_hash.update(msgid)

            id =  base64.encodestring(the_hash.digest())
    
            gm_ids_b[id] = [gm_id, subject, msgid]

        total_processed += batch_size

    #dumb search not optimisation
    #iterate over imap_ids_a and flag emails only in a but not in b
    #remove emails from imap_ids_b everytime they are found 
    for data_infos in batch_fetcher_a:
        for gm_info in data_infos:
            gm_id = data_infos[gm_info]['X-GM-MSGID']
            
            header_fields = data_infos[gm_info]['BODY[HEADER.FIELDS (MESSAGE-ID SUBJECT X-GMAIL-RECEIVED)]']
        
            subject, msgid, received = gmvault_db.GmailStorer.parse_header_fields(header_fields)
            
            the_hash = hashlib.md5()
            if received:
                the_hash.update(received)
            
            if subject:
                the_hash.update(subject)
                
            if msgid:
                the_hash.update(msgid)

            id =  base64.encodestring(the_hash.digest())
    
            if id not in gm_ids_b:
                diff_result["in_a"][received] = [gm_id, subject, msgid]
            else:
                del gm_ids_b[id]
    
    for recv_id in gm_ids_b:
        diff_result["in_b"][recv_id] = gm_ids_b[recv_id]
        
    
    # print report
    if (len(diff_result["in_a"]) > 0 or len(diff_result["in_b"]) > 0):
        print("emails only in gmv_a:\n") 
        print_diff_result(diff_result["in_a"])
        print("\n")
        print("emails only in gmv_b:%s\n") 
        print_diff_result(diff_result["in_b"])
    else:
        print("Mailbox %s and %s are identical.\n" % (gmvaulter_a.login, gmvaulter_b.login))
        
def print_diff_result(diff_result):
    """ print the diff_result structure
    """
    for key in diff_result:
        vals = diff_result[key]
        print("mailid:%s#####subject:%s#####%s." % (vals[2], vals[1], vals[0]))


def assert_login_is_protected(login):
    """
      Insure that the login is not my personnal mailbox
    """
    if login != 'gsync.mtester@gmail.com':
        raise Exception("Beware login should be gsync.mtester@gmail.com and it is %s" % (login)) 

def clean_mailbox(login , credential):
    """
       Delete all emails, destroy all labels
    """
    gimap = imap_utils.GIMAPFetcher('imap.gmail.com', 993, login, credential, readonly_folder = False)

    print("login = %s" % (login))

    assert_login_is_protected(login)

    gimap.connect()
    
    gimap.erase_mailbox()


def obfuscate_string(a_str):
    """ use base64 to obfuscate a string """
    return base64.b64encode(a_str)

def deobfuscate_string(a_str):
    """ deobfuscate a string """
    return base64.b64decode(a_str)

def read_password_file(a_path):
    """
       Read log:pass from a file in my home
    """
    pass_file = open(a_path)
    line = pass_file.readline()
    (login, passwd) = line.split(":")
    
    return (deobfuscate_string(login.strip()), deobfuscate_string(passwd.strip()))

def get_oauth_cred(email, cred_path):
    """
       Read oauth token secret credential
       Look by default to ~/.gmvault
       Look for file ~/.gmvault/email.oauth
    """
    user_oauth_file_path = cred_path

    token  = None
    secret = None
    if os.path.exists(user_oauth_file_path):
        print("Get XOAuth credential from %s.\n" % (user_oauth_file_path))
             
        oauth_file  = open(user_oauth_file_path)
             
        try:
            oauth_result = oauth_file.read()
            if oauth_result:
                oauth_result = oauth_result.split('::')
                if len(oauth_result) == 2:
                    token  = oauth_result[0]
                    secret = oauth_result[1]
        except Exception, _: #pylint: disable-msg=W0703              
            print("Cannot read oauth credentials from %s. Force oauth credentials renewal." % (user_oauth_file_path))
            print("=== Exception traceback ===")
            print(gmvault_utils.get_exception_traceback())
            print("=== End of Exception traceback ===\n")
         
        if token: token   = token.strip() #pylint: disable-msg=C0321
        if secret: secret = secret.strip()  #pylint: disable-msg=C0321
 
    return { 'type' : 'xoauth', 'value' : cred_utils.generate_xoauth_req(token, secret, email, 'normal'), 'option':None}

def delete_db_dir(a_db_dir):
    """
       delete the db directory
    """
    gmvault_utils.delete_all_under(a_db_dir, delete_top_dir = True)

########NEW FILE########
__FILENAME__ = validation_tests
'''
    Gmvault: a tool to backup and restore your gmail account.
    Copyright (C) <2011-2013>  <guillaume Aubert (guillaume dot aubert at gmail do com)>

    This program is free software: you can redistribute it and/or modify
    it under the terms of the GNU General Public License as published by
    the Free Software Foundation, either version 3 of the License, or
    (at your option) any later version.

    This program is distributed in the hope that it will be useful,
    but WITHOUT ANY WARRANTY; without even the implied warranty of
    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
    GNU General Public License for more details.

    You should have received a copy of the GNU General Public License
    along with this program.  If not, see <http://www.gnu.org/licenses/>.
'''

import unittest
import base64

import gmv.gmvault as gmvault
import gmv.gmvault_utils as gmvault_utils
import gmv.imap_utils as imap_utils

def obfuscate_string(a_str):
    """ use base64 to obfuscate a string """
    return base64.b64encode(a_str)

def deobfuscate_string(a_str):
    """ deobfuscate a string """
    return base64.b64decode(a_str)

def read_password_file(a_path):
    """
       Read log:pass from a file in my home
    """
    pass_file = open(a_path)
    line = pass_file.readline()
    (login, passwd) = line.split(":")
    
    return (deobfuscate_string(login.strip()), deobfuscate_string(passwd.strip()))

def delete_db_dir(a_db_dir):
    """
       delete the db directory
    """
    gmvault_utils.delete_all_under(a_db_dir, delete_top_dir = True)


class TestGMVaultValidation(unittest.TestCase): #pylint:disable=R0904
    """
       Validation Tests
    """

    def __init__(self, stuff):
        """ constructor """
        super(TestGMVaultValidation, self).__init__(stuff)
        
        self.test_login  = None
        self.test_passwd = None 
        
        self.default_dir = "/tmp/gmvault-tests"
    
    def setUp(self): #pylint:disable=C0103
        self.test_login, self.test_passwd = read_password_file('/homespace/gaubert/.ssh/gsync_passwd')
                
    def test_help_msg_spawned_by_def(self):
        """
           spawn python gmv_runner account > help_msg_spawned.txt
           check that res is 0 or 1
        """
        credential  = { 'type' : 'passwd', 'value': self.test_passwd}
        test_db_dir = "/tmp/gmvault-tests"
        
        restorer = gmvault.GMVaulter(test_db_dir, 'imap.gmail.com', 993, self.test_login, credential, \
                                     read_only_access = False)
        
        restorer.restore() #restore all emails from this essential-db
        
        #need to check that all labels are there for emails in essential
        gmail_ids = restorer.gstorer.get_all_existing_gmail_ids()
        
        for gm_id in gmail_ids:
            #get disk_metadata
            disk_metadata   = restorer.gstorer.unbury_metadata(gm_id)
            
            # get online_metadata 
            online_metadata = restorer.src.fetch(gm_id, imap_utils.GIMAPFetcher.GET_ALL_BUT_DATA) 
            
            #compare metadata
            for key in disk_metadata:
                self.assertEquals(disk_metadata[key], online_metadata[key])
            

def tests():
    """
       main test function
    """
    suite = unittest.TestLoader().loadTestsFromTestCase(TestGMVaultValidation)
    unittest.TextTestRunner(verbosity=2).run(suite)
 
if __name__ == '__main__':
    
    tests()

########NEW FILE########
__FILENAME__ = gmvault_essential_tests
'''
    Gmvault: a tool to backup and restore your gmail account.
    Copyright (C) <2011-2013>  <guillaume Aubert (guillaume dot aubert at gmail do com)>

    This program is free software: you can redistribute it and/or modify
    it under the terms of the GNU General Public License as published by
    the Free Software Foundation, either version 3 of the License, or
    (at your option) any later version.

    This program is distributed in the hope that it will be useful,
    but WITHOUT ANY WARRANTY; without even the implied warranty of
    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
    GNU General Public License for more details.

    You should have received a copy of the GNU General Public License
    along with this program.  If not, see <http://www.gnu.org/licenses/>.
'''
import unittest
import gmv.gmvault as gmvault
import gmv.gmvault_utils as gmvault_utils
import gmv.test_utils as test_utils


class TestEssentialGMVault(unittest.TestCase): #pylint:disable-msg=R0904
    """
       Current Main test class
    """

    def __init__(self, stuff):
        """ constructor """
        super(TestEssentialGMVault, self).__init__(stuff)
        
        self.gsync_login         = None
        self.gsync_passwd        = None 
        self.gmvault_test_login  = None
        self.gmvault_test_passwd = None
    
    def setUp(self): #pylint:disable-msg=C0103
        """setup"""
        self.gsync_login, self.gsync_passwd = test_utils.read_password_file('/homespace/gaubert/.ssh/gsync_passwd')
        self.gmvault_test_login, self.gmvault_test_passwd = test_utils.read_password_file('/homespace/gaubert/.ssh/gmvault_test_passwd')
        self.ba_login, self.ba_passwd = test_utils.read_password_file('/homespace/gaubert/.ssh/ba_passwd')

        #xoauth hanlding
        self.ga_login = 'guillaume.aubert@gmail.com'
        self.ga_cred  = test_utils.get_oauth_cred(self.ga_login, '/homespace/gaubert/.ssh/ga_oauth')

    def search_for_email(self, gmvaulter, req):
        """
           search for a particular email
        """
        #need to check that all labels are there for emails in essential
        gmvaulter.src.select_folder('ALLMAIL')

        imap_ids = gmvaulter.src.search({ 'type' : 'imap', 'req': req, 'charset': 'utf-8' })
 
        print("imap_ids = %s\n" % (imap_ids))
        
         
    def test_restore_tricky_emails(self):
        """ Test_restore_tricky_emails. Restore emails with some specificities (japanese characters) in the a mailbox """
        gsync_credential    = { 'type' : 'passwd', 'value': self.gsync_passwd }

        extra_labels = [u"My-Extra-Label"]

        test_utils.clean_mailbox(self.gsync_login, gsync_credential)

        # test restore
        test_db_dir = "/homespace/gaubert/gmvault-dbs/essential-dbs"
        #test_db_dir = "/home/gmv/Dev/projects/gmvault-develop/src/test-db"
        #test_db_dir = "/Users/gaubert/Dev/projects/gmvault-develop/src/test-db"
        
        restorer = gmvault.GMVaulter(test_db_dir, 'imap.gmail.com', 993, \
                                     self.gsync_login, gsync_credential, \
                                     read_only_access = False)
        
        restorer.restore(extra_labels = extra_labels) #restore all emails from this essential-db

        test_utils.check_remote_mailbox_identical_to_local(self, restorer, extra_labels)
        
    def test_backup_and_restore(self):
        """ Backup from gmvault_test and restore """
        gsync_credential        = { 'type' : 'passwd', 'value': self.gsync_passwd }
        gmvault_test_credential = { 'type' : 'passwd', 'value': self.gmvault_test_passwd }
        
        test_utils.clean_mailbox(self.gsync_login, gsync_credential)
        
        gmvault_test_db_dir = "/tmp/backup-restore"
        
        backuper = gmvault.GMVaulter(gmvault_test_db_dir, 'imap.gmail.com', 993, \
                                     self.gmvault_test_login, gmvault_test_credential, \
                                     read_only_access = False)
        
        backuper.sync({ 'mode': 'full', 'type': 'imap', 'req': 'ALL' })
        
        #check that we have x emails in the database
        restorer = gmvault.GMVaulter(gmvault_test_db_dir, 'imap.gmail.com', 993, \
                                     self.gsync_login, gsync_credential, \
                                     read_only_access = False)
        
        restorer.restore() #restore all emails from this essential-db

        test_utils.check_remote_mailbox_identical_to_local(self, restorer)

        test_utils.diff_online_mailboxes(backuper, restorer)
 
        gmvault_utils.delete_all_under(gmvault_test_db_dir, delete_top_dir = True)

    def ztest_delete_gsync(self):
        """
           Simply delete gsync
        """
        gsync_credential        = { 'type' : 'passwd', 'value': self.gsync_passwd }
        gmvault_test_credential = { 'type' : 'passwd', 'value': self.gmvault_test_passwd }

        test_utils.clean_mailbox(self.gsync_login, gsync_credential)
       
    def ztest_find_identicals(self):
        """
        """
        gsync_credential        = { 'type' : 'passwd', 'value': self.gsync_passwd }
        
        gmv_dir_a = "/tmp/a-db"
        gmv_a = gmvault.GMVaulter(gmv_dir_a, 'imap.gmail.com', 993, self.gsync_login, gsync_credential, read_only_access = True)
        
        test_utils.find_identical_emails(gmv_a)
         
    def ztest_difference(self):
        """
           
        """
        gsync_credential        = { 'type' : 'passwd', 'value': self.gsync_passwd }
        gmvault_test_credential = { 'type' : 'passwd', 'value': self.gmvault_test_passwd }
        ba_credential           = { 'type' : 'passwd', 'value': self.ba_passwd }

        gmv_dir_a = "/tmp/a-db"
        gmv_dir_b = "/tmp/b-db"

        gmv_a = gmvault.GMVaulter(gmv_dir_a, 'imap.gmail.com', 993, self.gsync_login, gsync_credential, read_only_access = True)
        
        #gmv_a = gmvault.GMVaulter(gmv_dir_a, 'imap.gmail.com', 993, self.gmvault_test_login, gmvault_test_credential, read_only_access = False)
        
        #gmv_b = gmvault.GMVaulter(gmv_dir_b, 'imap.gmail.com', 993, self.gmvault_test_login, gmvault_test_credential, read_only_access = False)

        #gmv_b = gmvault.GMVaulter(gmv_dir_b, 'imap.gmail.com', 993, self.ba_login, ba_credential, read_only_access = True)
        gmv_b = gmvault.GMVaulter(gmv_dir_b, 'imap.gmail.com', 993, self.ga_login, self.ga_cred, read_only_access = True)
        
        test_utils.diff_online_mailboxes(gmv_a, gmv_b)
        
def tests():
    """
       main test function
    """
    suite = unittest.TestLoader().loadTestsFromTestCase(TestEssentialGMVault)
    unittest.TextTestRunner(verbosity=2).run(suite)
 
if __name__ == '__main__':
    
    tests()

########NEW FILE########
__FILENAME__ = gmvault_tests
'''
    Gmvault: a tool to backup and restore your gmail account.
    Copyright (C) <2011-2013>  <guillaume Aubert (guillaume dot aubert at gmail do com)>

    This program is free software: you can redistribute it and/or modify
    it under the terms of the GNU General Public License as published by
    the Free Software Foundation, either version 3 of the License, or
    (at your option) any later version.

    This program is distributed in the hope that it will be useful,
    but WITHOUT ANY WARRANTY; without even the implied warranty of
    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
    GNU General Public License for more details.

    You should have received a copy of the GNU General Public License
    along with this program.  If not, see <http://www.gnu.org/licenses/>.
'''
import unittest
import base64
import shutil
import os

import ssl
import gmv.mod_imap as mod_imap
import gmv.gmvault as gmvault
import gmv.gmvault_utils as gmvault_utils
import gmv.imap_utils as imap_utils


def obfuscate_string(a_str):
    """ use base64 to obfuscate a string """
    return base64.b64encode(a_str)

def deobfuscate_string(a_str):
    """ deobfuscate a string """
    return base64.b64decode(a_str)

def read_password_file(a_path):
    """
       Read log:pass from a file in my home
    """
    pass_file = open(a_path)
    line = pass_file.readline()
    (login, passwd) = line.split(":")
    
    return (deobfuscate_string(login.strip()), deobfuscate_string(passwd.strip()))

def delete_db_dir(a_db_dir):
    """
       delete the db directory
    """
    gmvault_utils.delete_all_under(a_db_dir, delete_top_dir = True)


class TestGMVault(unittest.TestCase): #pylint:disable-msg=R0904
    """
       Current Main test class
    """

    def __init__(self, stuff):
        """ constructor """
        super(TestGMVault, self).__init__(stuff)
        
        self.login  = None
        self.passwd = None
        
        self.gmvault_login  = None
        self.gmvault_passwd = None 
    
    def setUp(self): #pylint:disable-msg=C0103
        self.login, self.passwd = read_password_file('/homespace/gaubert/.ssh/passwd')
        
        self.gmvault_login, self.gmvault_passwd = read_password_file('/homespace/gaubert/.ssh/gsync_passwd')
        
    
    def ztest_gmvault_connect_error(self):
        """
           Test connect error (connect to a wrong port). Too long to check
        """

        gimap = imap_utils.GIMAPFetcher('imap.gmafil.com', 80, "badlogin", "badpassword")
        
        try:
            gimap.connect()
        except ssl.SSLError, err:
            
            msg = str(err)
            
            if not msg.startswith('[Errno 8] _ssl.c:') or not msg.endswith('EOF occurred in violation of protocol'):
                self.fail('received %s. Bad error message' % (msg))
        
    def ztest_gmvault_get_capabilities(self):
        """
           Test simple retrieval
        """
        gimap = imap_utils.GIMAPFetcher('imap.gmail.com', 993, self.login, self.passwd)
        
        gimap.connect()
        
        self.assertEquals(('IMAP4REV1', 'UNSELECT', \
                           'IDLE', 'NAMESPACE', \
                           'QUOTA', 'ID', 'XLIST', \
                           'CHILDREN', 'X-GM-EXT-1', \
                           'XYZZY', 'SASL-IR', 'AUTH=XOAUTH') , gimap.get_capabilities())
    
    def ztest_gmvault_check_gmailness(self):
        """
           Test simple retrieval
        """
        gimap = imap_utils.GIMAPFetcher('imap.gmail.com', 993, self.login, self.passwd)
        
        gimap.connect()
        
        self.assertEquals( True , gimap.check_gmailness())
    
    def ztest_gmvault_compression(self):
        """
           Test simple retrieval
        """
        gimap = imap_utils.GIMAPFetcher('imap.gmail.com', 993, self.login, self.passwd)
        
        gimap.connect()
        
        gimap.enable_compression()
        
        self.assertEquals( True , gimap.check_gmailness())
        
        criteria = ['Before 1-Jan-2011']
        ids = gimap.search(criteria)
        
        self.assertEquals(len(ids), 33577)
        
    def ztest_created_nested_dirs(self):
        """ Try to create nested dirs """
        client = mod_imap.MonkeyIMAPClient('imap.gmail.com', port = 993, use_uid = True, ssl= True)
        
        client.login(self.gmvault_login, self.gmvault_passwd)
        
        folders_info = client.list_folders()
        
        print(folders_info)
        
        folders = [ the_dir for (_, _, the_dir) in folders_info ]
        
        print('folders %s\n' %(folders))
        the_dir = 'ECMWF-Archive'
        #dir = 'test'
        if the_dir not in folders:
            res = client.create_folder(dir)
            print(res)
        
        folders = [ the_dir for (_, _, dir) in folders_info ]
        
        print('folders %s\n' %(folders))
        the_dir = 'ECMWF-Archive/ecmwf-simdat'
        #dir = 'test/test-1'
        if the_dir not in folders:
            res = client.create_folder(the_dir)
            print(res)
    
    def zztest_create_gmail_labels_upper_case(self):
        """
           validate the label creation at the imap fetcher level.
           Use upper case
        """
        gs_credential = { 'type' : 'passwd', 'value': self.gmvault_passwd}
        gimap = imap_utils.GIMAPFetcher('imap.gmail.com', 993, self.gmvault_login, gs_credential)
        
        gimap.connect()
        
        
        print("\nCreate labels.\n")
        
        labels_to_create = ['0','A','a', 'B/C', 'B/C/d', 'B/C/d/e', 'c/d']
        
        existing_folders = set()
        
        existing_folders = gimap.create_gmail_labels(labels_to_create, existing_folders)
        
        print("folders = %s\n" % (existing_folders))
        for label in labels_to_create:
            self.assertTrue( (label.lower() in existing_folders) )   
            
        labels_to_create = ['0','A','a', 'B/C', 'B/C/d', 'B/C/d/e', 'c/d', 'diablo3', 'blizzard', 'blizzard/diablo']
        #labels_to_create = ['B/c', u'[Imap]/Trash', u'[Imap]/Sent', 'a', 'A', 'e/f/g', 'b/c/d', ]
        
        existing_folders = set()
        
        existing_folders = gimap.create_gmail_labels(labels_to_create, existing_folders)
        
        print("folders = %s\n" % (existing_folders))
        for label in labels_to_create:
            self.assertTrue( (label.lower() in existing_folders) )   
        
        print("Delete labels\n")
        
        gimap.delete_gmail_labels(labels_to_create)
        
        #get existing directories (or label parts)
        folders = [ directory.lower() for (_, _, directory) in gimap.get_all_folders() ]
        
        for label in labels_to_create: #check that they have been deleted
            self.assertFalse( (label.lower() in folders) )
    
    def zztest_create_gmail_labels_android(self):
        """
           Handle labels with [Imap]
        """
        gs_credential = { 'type' : 'passwd', 'value': self.gmvault_passwd}
        gimap = imap_utils.GIMAPFetcher('imap.gmail.com', 993, self.gmvault_login, gs_credential)
        
        gimap.connect()
        
        print("\nCreate labels.\n")
        
        labels_to_create = [u'[IMAP]/Trash', u'[IMAP]/Sent']
        
        existing_folders = set()
        
        existing_folders = gimap.create_gmail_labels(labels_to_create, existing_folders)
        
        #get existing directories (or label parts)
        #print("xlist folders = %s\n" % (gimap.get_all_folders()) )
        
        #folders = [ directory.lower() for (flags, delim, directory) in gimap.server.list_folders() ]
        folders = [ directory.lower() for directory in existing_folders ]
        
        print("folders = %s\n" % (folders))
        for label in labels_to_create:
            self.assertTrue( (label.lower() in folders) )   
            
        # second creation
        labels_to_create = [u'[RETEST]', u'[RETEST]/test', u'[RETEST]/Trash', u'[IMAP]/Trash', u'[IMAP]/Draft', u'[IMAP]/Sent', u'[IMAP]']
        
        existing_folders = gimap.create_gmail_labels(labels_to_create, existing_folders)
        
        folders = [ directory.lower() for directory in existing_folders ]
        
        print("folders = %s" % (folders))
        for label in labels_to_create:
            self.assertTrue( (label.lower() in folders) )  
            
        #it isn't possible to delete the [IMAP]/Sent, [IMAP]/Draft [IMAP]/Trash labels
        # I give up and do not delete them in the test
        labels_to_delete = [u'[RETEST]', u'[RETEST]/test', u'[RETEST]/Trash'] 
        
        print("Delete labels\n")
        
        # delete them
        gimap.delete_gmail_labels(labels_to_delete)
        
        #get existing directories (or label parts)
        folders = [ directory.lower() for (_, _, directory) in gimap.get_all_folders() ]
        
        for label in labels_to_delete: #check that they have been deleted
            self.assertFalse( (label.lower() in folders) )
            
        
        
    def ztest_gmvault_simple_search(self):
        """
           search all emails before 01.01.2005
        """
        gimap = imap_utils.GIMAPFetcher('imap.gmail.com', 993, self.login, self.passwd)
        
        gimap.connect()
       
        criteria = ['Before 1-Jan-2011']
        ids = gimap.search(criteria)
        
        self.assertEquals(len(ids), 33577)
        
    def ztest_retrieve_gmail_ids(self):
        """
           Get all uid before Sep 2004
           Retrieve all GMAIL IDs 
        """
        gimap = imap_utils.GIMAPFetcher('imap.gmail.com', 993, self.login, self.passwd)
        
        gimap.connect()
       
        criteria = ['Before 1-Oct-2004']
        #criteria = ['ALL']
        ids = gimap.search(criteria)
        
        res = gimap.fetch(ids, [gimap.GMAIL_ID])
        
        self.assertEquals(res, {27362: {'X-GM-MSGID': 1147537963432096749L, 'SEQ': 14535}, 27363: {'X-GM-MSGID': 1147537994018957026L, 'SEQ': 14536}})
        
    def ztest_retrieve_all_params(self):
        """
           Get all params for a uid
           Retrieve all parts for one email
        """
        gimap = imap_utils.GIMAPFetcher('imap.gmail.com', 993, self.login, self.passwd)
        
        gimap.connect()
       
        criteria = ['Before 1-Oct-2004']
        #criteria = ['ALL']
        ids = gimap.search(criteria)
        
        self.assertEquals(len(ids), 2)
        
        res = gimap.fetch(ids[0], [gimap.GMAIL_ID, gimap.EMAIL_BODY, gimap.GMAIL_THREAD_ID, gimap.GMAIL_LABELS])
        
        self.assertEquals(res[ids[0]][gimap.GMAIL_ID], 1147537963432096749L)
        
        self.assertEquals(res[ids[0]][gimap.EMAIL_BODY], \
                          'Message-ID: <6999505.1094377483218.JavaMail.wwwadm@chewbacca.ecmwf.int>\r\nDate: Sun, 5 Sep 2004 09:44:43 +0000 (GMT)\r\nFrom: Guillaume.Aubert@ecmwf.int\r\nReply-To: Guillaume.Aubert@ecmwf.int\r\nTo: aubert_guillaume@yahoo.fr\r\nSubject: Fwd: [Flickr] Guillaume Aubert wants you to see their photos\r\nMime-Version: 1.0\r\nContent-Type: text/plain; charset=us-ascii\r\nContent-Transfer-Encoding: 7bit\r\nX-Mailer: jwma\r\nStatus: RO\r\nX-Status: \r\nX-Keywords:                 \r\nX-UID: 1\r\n\r\n\r\n') #pylint:disable-msg=C0301
        
    def ztest_gmvault_retrieve_email_store_and_read(self): #pylint:disable-msg=C0103
        """
           Retrieve an email store it on disk and read it
        """
        storage_dir = '/tmp/gmail_bk'
        gmvault_utils.delete_all_under(storage_dir)
        
        gimap   = imap_utils.GIMAPFetcher('imap.gmail.com', 993, self.login, self.passwd)
        gstorer = gmvault.GmailStorer(storage_dir)
        
        gimap.connect()
        
        criteria = ['Before 1-Oct-2006']
        #criteria = ['ALL']
        ids = gimap.search(criteria)
        
        the_id = ids[124]
        
        res          = gimap.fetch(the_id, gimap.GET_ALL_INFO)
        
        gm_id = gstorer.bury_email(res[the_id])
        
        metadata, data = gstorer.unbury_email(gm_id)
        
        self.assertEquals(res[the_id][gimap.GMAIL_ID], metadata['gm_id'])
        self.assertEquals(res[the_id][gimap.EMAIL_BODY], data)
        self.assertEquals(res[the_id][gimap.GMAIL_THREAD_ID], metadata['thread_ids'])
        
        labels = []
        for label in res[the_id][gimap.GMAIL_LABELS]:
            labels.append(label)
            
        self.assertEquals(labels, metadata['labels'])
    
    def ztest_gmvault_compress_retrieve_email_store_and_read(self): #pylint:disable-msg=C0103
        """
           Activate compression and retrieve an email store it on disk and read it
        """
        storage_dir = '/tmp/gmail_bk'
        gmvault_utils.delete_all_under(storage_dir)
        
        gimap   = imap_utils.GIMAPFetcher('imap.gmail.com', 993, self.login, self.passwd)
        
        gstorer = gmvault.GmailStorer(storage_dir)
        
        gimap.connect()
        
        gimap.enable_compression()
        
        criteria = ['Before 1-Oct-2006']
        #criteria = ['ALL']
        ids = gimap.search(criteria)
        
        the_id = ids[124]
        
        res          = gimap.fetch(the_id, gimap.GET_ALL_INFO)
        
        gm_id = gstorer.bury_email(res[the_id])
        
        metadata, data = gstorer.unbury_email(gm_id)
        
        self.assertEquals(res[the_id][gimap.GMAIL_ID], metadata['gm_id'])
        self.assertEquals(res[the_id][gimap.EMAIL_BODY], data)
        self.assertEquals(res[the_id][gimap.GMAIL_THREAD_ID], metadata['thread_ids'])
        
        labels = []
        for label in res[the_id][gimap.GMAIL_LABELS]:
            labels.append(label)
            
        self.assertEquals(labels, metadata['labels'])
    
    def ztest_gmvault_retrieve_multiple_emails_store_and_read(self): #pylint:disable-msg=C0103
        """
           Retrieve emails store them it on disk and read it
        """
        storage_dir = '/tmp/gmail_bk'
        gmvault_utils.delete_all_under(storage_dir)
        gimap   = imap_utils.GIMAPFetcher('imap.gmail.com', 993, self.login, self.passwd)
        gstorer = gmvault.GmailStorer(storage_dir)
        
        gimap.connect()
        
        criteria = ['Before 1-Oct-2006']
        #criteria = ['ALL']
        ids = gimap.search(criteria)
        
        #get 30 emails
        for index in range(9, 40):
        
            print("retrieve email index %d\n" % (index))
            the_id = ids[index]
            
            res          = gimap.fetch(the_id, gimap.GET_ALL_INFO)
            
            gm_id = gstorer.bury_email(res[the_id])
            
            print("restore email index %d\n" % (index))
            metadata, data = gstorer.unbury_email(gm_id)
            
            self.assertEquals(res[the_id][gimap.GMAIL_ID], metadata['gm_id'])
            self.assertEquals(res[the_id][gimap.EMAIL_BODY], data)
            self.assertEquals(res[the_id][gimap.GMAIL_THREAD_ID], metadata['thread_ids'])
            
            labels = []
            for label in res[the_id][gimap.GMAIL_LABELS]:
                labels.append(label)
                
            self.assertEquals(labels, metadata['labels'])
        
    def ztest_gmvault_store_gzip_email_and_read(self): #pylint:disable-msg=C0103
        """
           Retrieve emails store them it on disk and read it
        """
        storage_dir = '/tmp/gmail_bk'
        gmvault_utils.delete_all_under(storage_dir)
        gimap   = imap_utils.GIMAPFetcher('imap.gmail.com', 993, self.login, self.passwd)
        
        gstorer = gmvault.GmailStorer(storage_dir)
        
        gimap.connect()
        
        criteria = ['Before 1-Oct-2006']
        #criteria = ['ALL']
        ids = gimap.search(criteria)
        
        #get 30 emails
        for index in range(9, 20):
        
            print("retrieve email index %d\n" % (index))
            the_id = ids[index]
            
            res          = gimap.fetch(the_id, gimap.GET_ALL_INFO)
            
            gm_id = gstorer.bury_email(res[the_id], compress = True)
            
            print("restore email index %d\n" % (index))
            metadata, data = gstorer.unbury_email(gm_id)
            
            self.assertEquals(res[the_id][gimap.GMAIL_ID], metadata['gm_id'])
            self.assertEquals(res[the_id][gimap.EMAIL_BODY], data)
            self.assertEquals(res[the_id][gimap.GMAIL_THREAD_ID], metadata['thread_ids'])
            
            labels = []
            for label in res[the_id][gimap.GMAIL_LABELS]:
                labels.append(label)
                
            self.assertEquals(labels, metadata['labels'])
            
    def ztest_restore_one_email(self):
        """
           get one email from one account and restore it
        """
        gsource      = imap_utils.GIMAPFetcher('imap.gmail.com', 993, self.login, self.passwd)
        gdestination = imap_utils.GIMAPFetcher('imap.gmail.com', 993, self.gmvault_login, self.gmvault_passwd, readonly_folder = False)
        
        gsource.connect()
        gdestination.connect()
        
        criteria = ['Before 1-Oct-2006']
        #criteria = ['ALL']
        ids = gsource.search(criteria)
        
        the_id = ids[0]
        
        source_email = gsource.fetch(the_id, gsource.GET_ALL_INFO)
        
        existing_labels = source_email[the_id][gsource.GMAIL_LABELS]
        
        test_labels = []
        for elem in existing_labels:
            test_labels.append(elem)
            
        #source_email[the_id][gsource.IMAP_INTERNALDATE] = source_email[the_id][gsource.IMAP_INTERNALDATE].replace(tzinfo= gmvault_utils.UTC_TZ)
            
        dest_id = gdestination.push_email(source_email[the_id][gsource.EMAIL_BODY], \
                                           source_email[the_id][gsource.IMAP_FLAGS] , \
                                           source_email[the_id][gsource.IMAP_INTERNALDATE], test_labels)
        
        dest_email = gdestination.fetch(dest_id, gsource.GET_ALL_INFO)
        
        # do the checkings
        self.assertEquals(dest_email[dest_id][gsource.IMAP_FLAGS], source_email[the_id][gsource.IMAP_FLAGS])
        self.assertEquals(dest_email[dest_id][gsource.EMAIL_BODY], source_email[the_id][gsource.EMAIL_BODY])
        self.assertEquals(dest_email[dest_id][gsource.GMAIL_LABELS], source_email[the_id][gsource.GMAIL_LABELS])
            
        #should be ok to be checked
        self.assertEquals(dest_email[dest_id][gsource.IMAP_INTERNALDATE], source_email[the_id][gsource.IMAP_INTERNALDATE])
        
    def ztest_restore_10_emails(self):
        """
           Restore 10 emails
        """
        gsource      = imap_utils.GIMAPFetcher('imap.gmail.com', 993, self.login, self.passwd)
        gdestination = imap_utils.GIMAPFetcher('imap.gmail.com', 993, self.gmvault_login, self.gmvault_passwd, \
                                             readonly_folder = False)
        
        gsource.connect()
        gdestination.connect()
        
        criteria = ['Before 1-Oct-2008']
        #criteria = ['ALL']
        ids = gsource.search(criteria)
        
        #get 30 emails
        for index in range(9, 20):
            
            print("email nb %d\n" % (index))
        
            the_id = ids[index]
             
            source_email = gsource.fetch(the_id, gsource.GET_ALL_INFO)
            
            existing_labels = source_email[the_id][gsource.GMAIL_LABELS]
            
            # get labels
            test_labels = []
            for elem in existing_labels:
                test_labels.append(elem)
                
            dest_id = gdestination.push_email(source_email[the_id][gsource.EMAIL_BODY], \
                                               source_email[the_id][gsource.IMAP_FLAGS] , \
                                               source_email[the_id][gsource.IMAP_INTERNALDATE], test_labels)
            
            #retrieve email from destination email account
            dest_email = gdestination.fetch(dest_id, gsource.GET_ALL_INFO)
            
            #check that it has the same
            # do the checkings
            self.assertEquals(dest_email[dest_id][gsource.IMAP_FLAGS], source_email[the_id][gsource.IMAP_FLAGS])
            self.assertEquals(dest_email[dest_id][gsource.EMAIL_BODY], source_email[the_id][gsource.EMAIL_BODY])
            
            dest_labels = []
            for elem in dest_email[dest_id][gsource.GMAIL_LABELS]:
                if not elem == '\\Important':
                    dest_labels.append(elem)
            
            src_labels = []
            for elem in source_email[the_id][gsource.GMAIL_LABELS]:
                if not elem == '\\Important':
                    src_labels.append(elem)
            
            self.assertEquals(dest_labels, src_labels)
        
    def ztest_few_days_syncer(self):
        """
           Test with the Syncer object
        """
        syncer = gmvault.GMVaulter('/tmp/gmail_bk', 'imap.gmail.com', 993, self.login, self.passwd)
        
        syncer.sync(imap_req = "Since 1-Nov-2011 Before 4-Nov-2011")
        
        storage_dir = "%s/%s" % ('/tmp/gmail_bk/db', '2011-11')
        
        gstorer = gmvault.GmailStorer('/tmp/gmail_bk')
        
        metadata = gmvault.GMVaulter.check_email_on_disk(gstorer, 1384313269332005293)
        
        self.assertEquals(metadata['gm_id'], 1384313269332005293)
        
        metadata = gmvault.GMVaulter.check_email_on_disk(gstorer, 1384403887202624608)
        
        self.assertEquals(metadata['gm_id'], 1384403887202624608)
            
        metadata = gmvault.GMVaulter.check_email_on_disk(gstorer, 1384486067720566818)
        
        self.assertEquals(metadata['gm_id'], 1384486067720566818)
        
    def ztest_few_days_syncer_with_deletion(self): #pylint:disable-msg=C0103
        """
           check that there was a deletion
        """
        db_dir = '/tmp/gmail_bk'
        #clean db dir
        delete_db_dir(db_dir)
        
        #copy test email in dest dir
        storage_dir = "%s/db/%s" % (db_dir, '2011-11')
        
        gmvault_utils.makedirs(storage_dir)
        
        shutil.copyfile('../etc/tests/test_few_days_syncer/2384403887202624608.eml.gz','%s/2384403887202624608.eml.gz' % (storage_dir))
        shutil.copyfile('../etc/tests/test_few_days_syncer/2384403887202624608.meta','%s/2384403887202624608.meta' % (storage_dir))
        
        syncer = gmvault.GMVaulter('/tmp/gmail_bk', 'imap.gmail.com', 993, self.login, self.passwd)
        
        syncer.sync(imap_req = "Since 1-Nov-2011 Before 2-Nov-2011", db_cleaning = True)
        
        self.assertFalse(os.path.exists('%s/2384403887202624608.eml.gz' % (storage_dir)))
        self.assertFalse(os.path.exists('%s/2384403887202624608.meta' % (storage_dir)))
        self.assertTrue(os.path.exists('%s/1384313269332005293.meta' % (storage_dir)))
        self.assertTrue(os.path.exists('%s/1384313269332005293.eml.gz' % (storage_dir)))
            
    def ztest_encrypt_restore_on_gmail(self):
        """
           Doesn't work to be fixed
           clean db disk
           sync with gmail for few emails
           restore them on gmail test
        """
        
        db_dir = '/tmp/gmail_bk'
        #clean db dir
        delete_db_dir(db_dir)
        
        credential    = { 'type' : 'passwd', 'value': self.passwd}
        search_req    = { 'type' : 'imap', 'req': "Since 1-Nov-2011 Before 3-Nov-2011"}
        
        use_encryption = True
        syncer = gmvault.GMVaulter(db_dir, 'imap.gmail.com', 993, self.login, credential, read_only_access = True, use_encryption = use_encryption)
        
        syncer.sync(imap_req = search_req)
        
        # check that the email can be read
        gstorer = gmvault.GmailStorer('/tmp/gmail_bk', use_encryption)
        
        metadata = gmvault.GMVaulter.check_email_on_disk(gstorer, 1384313269332005293)
        
        self.assertEquals(metadata['gm_id'], 1384313269332005293)
        
        email_meta, email_data = gstorer.unbury_email(1384313269332005293)
        
        self.assertTrue(email_data.startswith("Delivered-To: guillaume.aubert@gmail.com"))
        
        #print("Email Data = \n%s\n" % (email_data))
            
        print("Done \n")
        
    def ztest_fix_bug_search_broken_gm_id_and_quarantine(self):
        """
           Search with a gm_id and quarantine it
        """
        db_dir = '/tmp/gmail_bk'
        
        #clean db dir
        delete_db_dir(db_dir)
        
        credential    = { 'type' : 'passwd', 'value': self.passwd}
        gs_credential = { 'type' : 'passwd', 'value': self.gmvault_passwd}
        gstorer = gmvault.GmailStorer(db_dir)
        gimap = imap_utils.GIMAPFetcher('imap.gmail.com', 993, self.login, credential)
        
        gimap.connect()
       
        criteria = { 'type': 'imap', 'req' :['X-GM-MSGID 1254269417797093924']} #broken one
        #criteria = ['X-GM-MSGID 1254267782370534098']
        #criteria = ['ALL']
        ids = gimap.search(criteria)
        
        for the_id in ids:
            res          = gimap.fetch(the_id, gimap.GET_ALL_INFO)
          
            gm_id = gstorer.bury_email(res[the_id], compress = True)
            
            syncer = gmvault.GMVaulter(db_dir, 'imap.gmail.com', 993, self.gmvault_login, gs_credential)
        
            syncer.restore()
        
        
        #check that the file has been quarantine
        quarantine_dir = '%s/quarantine' %(db_dir)
        
        self.assertTrue(os.path.exists('%s/1254269417797093924.eml.gz' % (quarantine_dir)))
        self.assertTrue(os.path.exists('%s/1254269417797093924.meta' % (quarantine_dir)))
                
    def ztest_fix_bug(self):
        """
           bug with uid 142221L => empty email returned by gmail
        """
        db_dir = '/tmp/gmail_bk'
        credential = { 'type' : 'passwd', 'value': self.passwd}
        syncer = gmvault.GMVaulter(db_dir, 'imap.gmail.com', 993, self.login, credential, 'verySecRetKeY')
        
        syncer._create_update_sync([142221L], compress = True)
        
    def test_check_flags(self):
        """
           Check flags 
        """
        credential    = { 'type' : 'passwd', 'value': self.passwd}
        #print("credential %s\n" % (credential))
        gimap = imap_utils.GIMAPFetcher('imap.gmail.com', 993, self.login, credential)
        
        gimap.connect()
       
        imap_ids  = [155182]
        gmail_id = 1405877259414135030

        imap_ids = [155070]
        
        #res = gimap.fetch(imap_ids, [gimap.GMAIL_ID, gimap.IMAP_FLAGS])
        res = gimap.fetch(imap_ids, gimap.GET_ALL_BUT_DATA)
        
        print(res)
        
        

def tests():
    """
       main test function
    """
    suite = unittest.TestLoader().loadTestsFromTestCase(TestGMVault)
    unittest.TextTestRunner(verbosity=2).run(suite)
 
if __name__ == '__main__':
    
    tests()

########NEW FILE########
__FILENAME__ = gmv_cmd_tests
'''
    Gmvault: a tool to backup and restore your gmail account.
    Copyright (C) <2011-2013>  <guillaume Aubert (guillaume dot aubert at gmail do com)>

    This program is free software: you can redistribute it and/or modify
    it under the terms of the GNU General Public License as published by
    the Free Software Foundation, either version 3 of the License, or
    (at your option) any later version.

    This program is distributed in the hope that it will be useful,
    but WITHOUT ANY WARRANTY; without even the implied warranty of
    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
    GNU General Public License for more details.

    You should have received a copy of the GNU General Public License
    along with this program.  If not, see <http://www.gnu.org/licenses/>.
'''

import sys
import unittest
import base64
import shutil
import os

import ssl
import imaplib
import gmv.gmvault as gmvault
import gmv.gmvault_db as gmvault_db
import gmv.gmvault_utils as gmvault_utils
import gmv.gmv_cmd as gmv_cmd
import gmv.credential_utils as credential_utils


def obfuscate_string(a_str):
    """ use base64 to obfuscate a string """
    return base64.b64encode(a_str)

def deobfuscate_string(a_str):
    """ deobfuscate a string """
    return base64.b64decode(a_str)

def read_password_file(a_path):
    """
       Read log:pass from a file in my home
    """
    pass_file = open(a_path)
    line = pass_file.readline()
    (login, passwd) = line.split(":")
    
    return (deobfuscate_string(login.strip()), deobfuscate_string(passwd.strip()))

def delete_db_dir(a_db_dir):
    """
       delete the db directory
    """
    gmvault_utils.delete_all_under(a_db_dir, delete_top_dir = True)


class TestGMVCMD(unittest.TestCase): #pylint:disable-msg=R0904
    """
       Current Main test class
    """

    def __init__(self, stuff):
        """ constructor """
        super(TestGMVCMD, self).__init__(stuff)
        
        self.login  = None
        self.passwd = None
        
        self.gmvault_login  = None
        self.gmvault_passwd = None 
    
    def setUp(self): #pylint:disable-msg=C0103
        self.login, self.passwd = read_password_file('/homespace/gaubert/.ssh/passwd')
        
        self.gsync_login, self.gsync_passwd = read_password_file('/homespace/gaubert/.ssh/gsync_passwd')
        
    def test_commandline_args(self):
        """
           Test commandline args
        """
        gmv_cmd.init_logging()
        
        # test 1: default
        sys.argv = ['gmvault.py', 'sync', self.login]
        
        gmvlt = gmv_cmd.GMVaultLauncher()
    
        args = gmvlt.parse_args()
        
        #check args
        self.assertEquals(args['command'],  'sync')
        self.assertEquals(args['type'],     'full')
        self.assertEquals(args['email'],    self.login)
        self.assertEquals(args['passwd'],   'not_seen')
        self.assertEquals(args['oauth'],    'empty')
        self.assertEquals(args['request'], {'req': 'ALL', 'type': 'imap'})
        self.assertEquals(args['host'],'imap.gmail.com')
        self.assertEquals(args['port'], 993)
        self.assertEquals(args['db-cleaning'], True)
        self.assertEquals(args['db-dir'],'%s/gmvault-db' % (os.environ['HOME']))
            
        
        # test 2: do imap search
        sys.argv = ['gmvault.py', 'sync','-t', 'custom',
                    '-r', 'Since 1-Nov-2011 Before 4-Nov-2011', \
                    '--db-dir','/tmp/new-db-1', self.login]
        
        gmvlt = gmv_cmd.GMVaultLauncher()
    
        args = gmvlt.parse_args()
        
        #check args
        self.assertEquals(args['command'],  'sync')
        self.assertEquals(args['type'],     'custom')
        self.assertEquals(args['email'],    self.login)
        self.assertEquals(args['passwd'],   'not_seen')
        self.assertEquals(args['oauth'],    'empty')
        self.assertEquals(args['request'], {'req': 'Since 1-Nov-2011 Before 4-Nov-2011', 'type': 'imap'})
        self.assertEquals(args['host'],'imap.gmail.com')
        self.assertEquals(args['port'], 993)
        self.assertEquals(args['db-cleaning'], True)
        self.assertEquals(args['db-dir'],'/tmp/new-db-1')
        
        # test 2: do gmail search
        sys.argv = ['gmvault.py', 'sync','-t', 'custom',
                    '-g', 'subject:Chandeleur bis', \
                    '--db-dir','/tmp/new-db-1', self.login]
        
        #do same as in bootstrap
        gmvlt = gmv_cmd.GMVaultLauncher()
    
        args = gmvlt.parse_args()
        
        #check args
        self.assertEquals(args['command'],  'sync')
        self.assertEquals(args['type'],     'custom')
        self.assertEquals(args['email'],    self.login)
        self.assertEquals(args['passwd'],   'not_seen')
        self.assertEquals(args['oauth'],    'empty')
        self.assertEquals(args['request'], {'req': 'subject:Chandeleur bis', 'type': 'gmail'})
        self.assertEquals(args['host'],'imap.gmail.com')
        self.assertEquals(args['port'], 993)
        self.assertEquals(args['db-cleaning'], True)
        self.assertEquals(args['db-dir'],'/tmp/new-db-1')
        
        #test3 emails only
        sys.argv = ['gmvault.py', 'sync','-t', 'custom',
                    '-g', 'subject:Chandeleur bis', \
                    '--db-dir','/tmp/new-db-1', \
                    '--emails-only', self.login]
        
        #with emails only
        gmvlt = gmv_cmd.GMVaultLauncher()
    
        args = gmvlt.parse_args()
        
        #check args
        self.assertEquals(args['emails_only'], True)
        self.assertEquals(args['chats_only'], False)
        self.assertEquals(args['command'],  'sync')
        self.assertEquals(args['type'],     'custom')
        self.assertEquals(args['email'],    self.login)
        self.assertEquals(args['passwd'],   'not_seen')
        self.assertEquals(args['oauth'],    'empty')
        self.assertEquals(args['request'], {'req': 'subject:Chandeleur bis', 'type': 'gmail'})
        self.assertEquals(args['host'],'imap.gmail.com')
        self.assertEquals(args['port'], 993)
        self.assertEquals(args['db-cleaning'], True)
        self.assertEquals(args['db-dir'],'/tmp/new-db-1')
        
        #test chats only
        sys.argv = ['gmvault.py', 'sync','-t', 'custom',
                    '-g', 'subject:Chandeleur bis', \
                    '--db-dir','/tmp/new-db-1', \
                    '--chats-only', self.login]
        
        gmvlt = gmv_cmd.GMVaultLauncher()
    
        args = gmvlt.parse_args()
        
        #check args
        self.assertEquals(args['chats_only'], True)
        self.assertEquals(args['emails_only'], False)
        self.assertEquals(args['command'],  'sync')
        self.assertEquals(args['type'],     'custom')
        self.assertEquals(args['email'],    self.login)
        self.assertEquals(args['passwd'],   'not_seen')
        self.assertEquals(args['oauth'],    'empty')
        self.assertEquals(args['request'], {'req': 'subject:Chandeleur bis', 'type': 'gmail'})
        self.assertEquals(args['host'],'imap.gmail.com')
        self.assertEquals(args['port'], 993)
        self.assertEquals(args['db-cleaning'], True)
        self.assertEquals(args['db-dir'],'/tmp/new-db-1')
        self.assertEquals(args['ownership_control'], True)
        self.assertEquals(args['compression'], True)
        self.assertEquals(args['debug'], False)
        self.assertEquals(args['restart'], False)
 
 
        #test5 chats only
        sys.argv = ['gmvault.py', 'sync','-t', 'custom',
                    '-g', 'subject:Chandeleur bis', \
                    '--db-dir','/tmp/new-db-1', \
                    '--check-db', 'no', '--resume', '--debug',\
                    '--no-compression', self.login]
        
        #with emails only
        gmvlt = gmv_cmd.GMVaultLauncher()
    
        args = gmvlt.parse_args()
        
        #check args
        self.assertEquals(args['chats_only'], False)
        self.assertEquals(args['emails_only'], False)
        self.assertEquals(args['command'],  'sync')
        self.assertEquals(args['type'],     'custom')
        self.assertEquals(args['email'],    self.login)
        self.assertEquals(args['passwd'],   'not_seen')
        self.assertEquals(args['oauth'],    'empty')
        self.assertEquals(args['request'], {'req': 'subject:Chandeleur bis', 'type': 'gmail'})
        self.assertEquals(args['host'],'imap.gmail.com')
        self.assertEquals(args['port'], 993)
        self.assertEquals(args['db-cleaning'], False)
        self.assertEquals(args['db-dir'],'/tmp/new-db-1')
        self.assertEquals(args['compression'], False)
        self.assertEquals(args['debug'], True)
        self.assertEquals(args['restart'], True)
        
        
    def zztest_cli_bad_server(self):
        """
           Test the cli interface bad option
        """
        sys.argv = ['gmvault', 'sync',  '--server', 'imagp.gmail.com', \
                    '--port', '993', '--imap-req', \
                    'Since 1-Nov-2011 Before 4-Nov-2011', \
                    self.login]
    
        gmvaulter = gmv_cmd.GMVaultLauncher()
        
        args = gmvaulter.parse_args()
    
        try:
    
            gmvaulter.run(args)
        
        except SystemExit, _:
            print("In Error success")
            
    def ztest_cli_bad_passwd(self):
        """
           Test the cli interface bad option
        """
        sys.argv = ['gmvault', '--imap-server', 'imap.gmail.com', \
                    '--imap-port', 993, '--imap-request', \
                    'Since 1-Nov-2011 Before 4-Nov-2011', \
                    '--email', self.login, '--passwd', 'bar']
    
        gmvaulter = gmv_cmd.GMVaultLauncher()
        
        args = gmvaulter.parse_args()
    
        try:
    
            gmvaulter.run(args)
        
        except SystemExit, err:
            print("In Error success")
            
    def ztest_cli_bad_login(self):
        """
           Test the cli interface bad option
        """
        sys.argv = ['gmvault', '--imap-server', 'imap.gmail.com', \
                    '--imap-port', 993, '--imap-request', \
                    'Since 1-Nov-2011 Before 4-Nov-2011', \
                    '--passwd', ]
    
        gmvaulter = gmv_cmd.GMVaultLauncher()
        
        args = gmvaulter.parse_args()
    
        try:
    
            gmvaulter.run(args)
        
        except SystemExit, err:
            print("In Error success")
            
    
    
    def zztest_cli_host_error(self):
        """
           Test the cli interface bad option
        """
        sys.argv = ['gmvault.py', 'sync', '--host', \
                    'imap.gmail.com', '--port', '1452', \
                    self.login]
    
        gmvaulter = gmv_cmd.GMVaultLauncher()
    
        try:
            _ = gmvaulter.parse_args()
        except SystemExit, err:
            self.assertEquals(type(err), type(SystemExit()))
            self.assertEquals(err.code, 2)
        except Exception, err:
            self.fail('unexpected exception: %s' % err)
        else:
            self.fail('SystemExit exception expected')

    def zztest_cli_(self):
        """
           Test the cli interface bad option
        """
        sys.argv = ['gmvault', 'sync', '--server', 'imap.gmail.com', \
                    '--port', '993', '--imap-req', \
                    'Since 1-Nov-2011 Before 10-Nov-2011', \
                    '--passwd', self.login]
    
        gmvaulter = gmv_cmd.GMVaultLauncher()
    
        try:
            args = gmvaulter.parse_args()
            
            self.assertEquals(args['command'],'sync')
            self.assertEquals(args['type'],'full')
            self.assertEquals(args['email'], self.login)
            self.assertEquals(args['passwd'],'empty')
            self.assertEquals(args['request'], {'req': 'Since 1-Nov-2011 Before 10-Nov-2011', 'type': 'imap'})
            self.assertEquals(args['oauth'], 'not_seen')
            self.assertEquals(args['host'],'imap.gmail.com')
            self.assertEquals(args['port'], 993)
            self.assertEquals(args['db-dir'],'./gmvault-db')
            
        except SystemExit, err:
            self.fail("SystemExit Exception: %s"  % err)
        except Exception, err:
            self.fail('unexpected exception: %s' % err)
    
    def ztest_full_sync_gmv(self):
        """
           full test via the command line
        """
        sys.argv = ['gmvault.py', '--imap-server', 'imap.gmail.com', \
                    '--imap-port', '993', '--imap-request', \
                    'Since 1-Nov-2011 Before 5-Nov-2011', '--email', \
                    self.login, '--passwd', self.passwd]
    
        gmvault_launcher = gmv_cmd.GMVaultLauncher()
        
        args = gmvault_launcher.parse_args()
    
        gmvault_launcher.run(args)
        
        #check all stored gmail ids
        gstorer = gmvault.GmailStorer(args['db-dir'])
        
        ids = gstorer.get_all_existing_gmail_ids()
        
        self.assertEquals(len(ids), 5)
        
        self.assertEquals(ids, {1384403887202624608L: '2011-11', \
                                1384486067720566818L: '2011-11', \
                                1384313269332005293L: '2011-11', \
                                1384545182050901969L: '2011-11', \
                                1384578279292583731L: '2011-11'})
        
        #clean db dir
        delete_db_dir(args['db-dir'])
           
    def ztest_password_handling(self):
        """
           Test all credentials handling
        """
        gmv_cmd.init_logging()
        
        # test 1: enter passwd and go to interactive mode

        sys.argv = ['gmvault.py', '--imap-request', \
                    'Since 1-Nov-2011 Before 7-Nov-2011', \
                    '--email', self.login, \
                    '--passwd', '--interactive', '--db-dir', '/tmp/new-db-1']
    
        gmvault_launcher = gmv_cmd.GMVaultLauncher()
        
        args = gmvault_launcher.parse_args()
        
        credential = gmvault_launcher.get_credential(args, test_mode = {'activate': True, 'value' : 'a_password'}) #test_mode needed to avoid calling get_pass
    
        self.assertEquals(credential, {'type': 'passwd', 'value': 'a_password'})
        
        # store passwd and re-read it
        sys.argv = ['gmvault.py', '--imap-request', \
                    'Since 1-Nov-2011 Before 7-Nov-2011', \
                    '--email', self.login, \
                    '--passwd', '--save-passwd', '--db-dir', '/tmp/new-db-1']
        
        gmvault_launcher = gmv_cmd.GMVaultLauncher()
        
        args = gmvault_launcher.parse_args()
        
        credential = gmvault_launcher.get_credential(args, test_mode = {'activate': True, 'value' : 'a_new_password'})
        
        self.assertEquals(credential, {'type': 'passwd', 'option': 'saved', 'value': 'a_new_password'})
        
        # now read the password
        sys.argv = ['gmvault.py', 'sync', '--imap-req', \
                    'Since 1-Nov-2011 Before 7-Nov-2011', \
                    '-t', 'custom', \
                    '--passwd', '--db-dir', '/tmp/new-db-1', self.login]
        
        gmvault_launcher = gmv_cmd.GMVaultLauncher()
        
        args = gmvault_launcher.parse_args()
        
        credential = gmvault_launcher.get_credential(args, test_mode = {'activate': True, 'value' : "don't care"})
        
        self.assertEquals(credential, {'type': 'passwd', 'option': 'read', 'value': 'a_new_password'})
    
    
    def ztest_double_login(self):
        """
           double login
        """
        # now read the password
        sys.argv = ['gmvault.py', 'sync', '--db-dir', '/tmp/new-db-1', self.login]
        
        gmvault_launcher = gmv_cmd.GMVaultLauncher()
        
        args = gmvault_launcher.parse_args()
        
        credential = credential_utils.CredentialHelper.get_credential(args)
        
        syncer = gmvault.GMVaulter(args['db-dir'], args['host'], args['port'], \
                                       args['email'], credential)
        
        print("First connection \n")
        syncer.src.connect()
        
        import time
        time.sleep(60*10)
        
        print("Connection 10 min later")
        syncer.src.connect()
        
    def ztest_debug_restore(self):
        """
           double login
        """
        # now read the password
        sys.argv = ['gmvault.py', 'restore', '--db-dir', '/Users/gaubert/Dev/projects/gmvault/src/gmv/gmvault-db', 'gsync.mtester@gmail.com']
        
        gmv_cmd.bootstrap_run()
    
    def ztest_restore_with_labels(self):
        """
           Test restore with labels
        """
        
        sys.argv = ['gmvault.py', 'restore', '--restart', '--db-dir', '/Users/gaubert/Dev/projects/gmvault/src/gmv/gmvault-db', 'gsync.mtester@gmail.com']
        
        gmv_cmd.bootstrap_run()
        
    
    def ztest_quick_sync_with_labels(self):
        """
           Test quick sync
           --renew-passwd
        """
        sys.argv = ['gmvault.py', 'sync', self.login]
        
        gmv_cmd.bootstrap_run()
        
    def ztest_simple_get_and_restore(self):
        """
           get few emails and restore them
        """
        db_dir = '/tmp/gmail_bk'
        #clean db dir
        delete_db_dir(db_dir)
        
        print("Synchronize\n")
        
        sys.argv = ['gmvault.py', 'sync', '-t', 'custom', '-r', 'Since 1-Nov-2011 Before 3-Nov-2011', '--db-dir', db_dir, 'guillaume.aubert@gmail.com']

        gmv_cmd.bootstrap_run()
        
        print("Restore\n")
        
        sys.argv = ['gmvault.py', 'restore', '--db-dir', db_dir, 'gsync.mtester@gmail.com']

        gmv_cmd.bootstrap_run()
        
    def ztest_simple_get_encrypt_and_restore(self):
        """
           get few emails and restore them
        """
        db_dir = '/tmp/gmail_bk'
        #clean db dir
        delete_db_dir(db_dir)
        
        print("Synchronize\n")
        
        sys.argv = ['gmvault.py', 'sync', '-t', 'custom', '--encrypt','-r', 'Since 1-Nov-2011 Before 3-Nov-2011', '--db-dir', db_dir, 'guillaume.aubert@gmail.com']

        gmv_cmd.bootstrap_run()
        
        print("Restore\n")
        
        sys.argv = ['gmvault.py', 'restore', '--db-dir', db_dir, 'gsync.mtester@gmail.com']

        gmv_cmd.bootstrap_run()
        
    def ztest_delete_sync_gmv(self):
        """
           delete sync via command line
        """
        delete_db_dir('/tmp/new-db-1')
        
        #first request to have the extra dirs
        sys.argv = ['gmvault.py', 'sync', '-t', 'custom', '-r', \
                    'Since 1-Nov-2011 Before 7-Nov-2011', \
                    '--db-dir', '/tmp/new-db-1', 'guillaume.aubert@gmail.com']
        
        #check all stored gmail ids
        gstorer = gmvault_db.GmailStorer('/tmp/new-db-1')
        
        gmv_cmd.bootstrap_run()
        
        ids = gstorer.get_all_existing_gmail_ids()
        
        self.assertEquals(len(ids), 9)
        
        delete_db_dir('/tmp/new-db-1')
        
        #second requests so all files after the 5 should disappear 
        sys.argv = ['gmvault.py', 'sync', '-t', 'custom', '-r', \
                    'Since 1-Nov-2011 Before 5-Nov-2011', \
                    '--db-dir', '/tmp/new-db-1', '-c', 'yes', 'guillaume.aubert@gmail.com']
    
        gmv_cmd.bootstrap_run()
    
        gstorer = gmvault_db.GmailStorer('/tmp/new-db-1')
        
        ids = gstorer.get_all_existing_gmail_ids()
        
        self.assertEquals(len(ids), 5)
        
        self.assertEquals(ids, {1384403887202624608L: '2011-11', \
                                1384486067720566818L: '2011-11', \
                                1384313269332005293L: '2011-11', \
                                1384545182050901969L: '2011-11', \
                                1384578279292583731L: '2011-11'})
        
        #clean db dir
        delete_db_dir('/tmp/new-db-1')
               

def tests():
    """
       main test function
    """
    suite = unittest.TestLoader().loadTestsFromTestCase(TestGMVCMD)
    unittest.TextTestRunner(verbosity=2).run(suite)
 
if __name__ == '__main__':
    
    tests()

########NEW FILE########
__FILENAME__ = gmv_runner
'''
    Gmvault: a tool to backup and restore your gmail account.
    Copyright (C) <2011-2013>  <guillaume Aubert (guillaume dot aubert at gmail do com)>

    This program is free software: you can redistribute it and/or modify
    it under the terms of the GNU Affero General Public License as
    published by the Free Software Foundation, either version 3 of the
    License, or (at your option) any later version.

    This program is distributed in the hope that it will be useful,
    but WITHOUT ANY WARRANTY; without even the implied warranty of
    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
    GNU Affero General Public License for more details.

    You should have received a copy of the GNU Affero General Public License
    along with this program.  If not, see <http://www.gnu.org/licenses/>.

'''

import gmv.gmv_cmd

gmv.gmv_cmd.bootstrap_run()

########NEW FILE########
__FILENAME__ = perf_tests
'''
    Gmvault: a tool to backup and restore your gmail account.
    Copyright (C) <2011-2013>  <guillaume Aubert (guillaume dot aubert at gmail do com)>

    This program is free software: you can redistribute it and/or modify
    it under the terms of the GNU General Public License as published by
    the Free Software Foundation, either version 3 of the License, or
    (at your option) any later version.

    This program is distributed in the hope that it will be useful,
    but WITHOUT ANY WARRANTY; without even the implied warranty of
    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
    GNU General Public License for more details.

    You should have received a copy of the GNU General Public License
    along with this program.  If not, see <http://www.gnu.org/licenses/>.
'''

import unittest
import datetime
import os
import gmv.gmvault_utils as gmvault_utils
import gmv.collections_utils as collections_utils


class TestPerf(unittest.TestCase): #pylint:disable-msg=R0904
    """
       Current Main test class
    """

    def __init__(self, stuff):
        """ constructor """
        super(TestPerf, self).__init__(stuff)
        
    
    def setUp(self): #pylint:disable-msg=C0103
        pass
    
    def _create_dirs(self, working_dir, nb_dirs, nb_files_per_dir):
        """
           create all the dirs and files
        """
        dirname   = 'dir_%d'
        data_file = '%d.eml'
        meta_file = '%d.meta'
        
        for nb in xrange(0, nb_dirs):
            #make dir
            the_dir = '%s/%s' % (working_dir, dirname % (nb))
            gmvault_utils.makedirs(the_dir)
            
            for file_id in xrange(0,nb_files_per_dir):
                #create data file
                fd = open('%s/%s_%s' % (the_dir, dirname % (nb) , data_file % (file_id)), 'w')
                fd.write("something")
                fd.close()
                #create metadata file
                fd = open('%s/%s_%s' % (the_dir, dirname % (nb) , meta_file % (file_id)), 'w')
                fd.write("another info something")
                fd.close()
                
            
    
    def test_read_lots_of_files(self):
        """
           Test to mesure how long it takes to list over 100 000 files
           On server: 250 000 meta files in 50 dirs (50,5000) => 9.74  sec to list them 
                      100 000 meta files in 20 dirs (20,5000) => 3.068 sec to list them
                      60  000 meta files in 60 dirs (60,1000) => 1.826 sec to list them
           On linux macbook pro linux virtual machine:
                      250 000 meta files in 50 dirs (50,5000) => 9.91 sec to list them
                      100 000 meta files in 20 dirs (20,5000) => 6.59 sec to list them
                      60  000 meta files in 60 dirs (60,1000) => 2.26 sec to list them
           On Win7 laptop machine:
                      250 000 meta files in 50 dirs (50,5000) => 56.50 sec (3min 27 sec if dir created and listed afterward) to list them
                      100 000 meta files in 20 dirs (20,5000) => 20.1 sec to list them
                      60  000 meta files in 60 dirs (60,1000) => 9.96 sec to list them
           
        """
        root_dir = '/tmp/dirs'
        #create dirs and files
        #t1 = datetime.datetime.now()
        #self._create_dirs('/tmp/dirs', 50, 5000)
        #t2 = datetime.datetime.now()
        
        #print("\nTime to create dirs : %s\n" % (t2-t1))
        #print("\nFiles and dirs created.\n")
        
        the_iter = gmvault_utils.dirwalk(root_dir, a_wildcards= '*.meta')
        t1 = datetime.datetime.now()
        
        gmail_ids = collections_utils.OrderedDict()
        
        for filepath in the_iter:
            directory, fname = os.path.split(filepath)
            gmail_ids[os.path.splitext(fname)[0]] = os.path.basename(directory)
        t2 = datetime.datetime.now()
        
        print("\nnb of files = %s" % (len(gmail_ids.keys())))
        print("\nTime to read all meta files : %s\n" % (t2-t1))
        

def tests():
    """
       main test function
    """
    suite = unittest.TestLoader().loadTestsFromTestCase(TestPerf)
    unittest.TextTestRunner(verbosity=2).run(suite)
 
if __name__ == '__main__':
    
    tests()

########NEW FILE########
__FILENAME__ = chardet_test
# -*- coding: utf-8 -*-
import sys
import chardet
import codecs

print("system encoding: %s" % (sys.getfilesystemencoding()))
first_arg = sys.argv[1]
#first_arg="réception"
#first_arg="て感じでしょうか研"
print first_arg
print("chardet = %s\n" % chardet.detect(first_arg))
res_char = chardet.detect(first_arg)
print type(first_arg)
 

 
first_arg_unicode = first_arg.decode(res_char['encoding'])
print first_arg_unicode
print type(first_arg_unicode)
 
utf8_arg = first_arg_unicode.encode("utf-8")
print type(utf8_arg)
print utf8_arg
########NEW FILE########
__FILENAME__ = common_gmvault
'''
    Gmvault: a tool to backup and restore your gmail account.
    Copyright (C) <2011-2013>  <guillaume Aubert (guillaume dot aubert at gmail do com)>

    This program is free software: you can redistribute it and/or modify
    it under the terms of the GNU Affero General Public License as
    published by the Free Software Foundation, either version 3 of the
    License, or (at your option) any later version.

    This program is distributed in the hope that it will be useful,
    but WITHOUT ANY WARRANTY; without even the implied warranty of
    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
    GNU Affero General Public License for more details.

    You should have received a copy of the GNU Affero General Public License
    along with this program.  If not, see <http://www.gnu.org/licenses/>.

'''
import json
import time
import datetime
import os
import itertools
import imaplib

import gmv.log_utils as log_utils
import gmv.collections_utils as collections_utils
import gmv.gmvault_utils as gmvault_utils
import gmv.imap_utils as imap_utils
import gmv.gmvault_db as gmvault_db

LOG = log_utils.LoggerFactory.get_logger('gmvault')

def handle_restore_imap_error(the_exception, gm_id, db_gmail_ids_info, gmvaulter):
    """
       function to handle restore IMAPError in restore functions 
    """
    if isinstance(the_exception, imaplib.IMAP4.abort):
        # if this is a Gmvault SSL Socket error quarantine the email and continue the restore
        if str(the_exception).find("=> Gmvault ssl socket error: EOF") >= 0:
            LOG.critical("Quarantine email with gm id %s from %s. GMAIL IMAP cannot restore it:"\
                         " err={%s}" % (gm_id, db_gmail_ids_info[gm_id], str(the_exception)))
            gmvaulter.gstorer.quarantine_email(gm_id)
            gmvaulter.error_report['emails_in_quarantine'].append(gm_id)
            LOG.critical("Disconnecting and reconnecting to restart cleanly.")
            gmvaulter.src.reconnect() #reconnect
        else:
            raise the_exception
        
    elif isinstance(the_exception, imaplib.IMAP4.error): 
        LOG.error("Catched IMAP Error %s" % (str(the_exception)))
        LOG.exception(the_exception)
        
        #When the email cannot be read from Database because it was empty when returned by gmail imap
        #quarantine it.
        if str(the_exception) == "APPEND command error: BAD ['Invalid Arguments: Unable to parse message']":
            LOG.critical("Quarantine email with gm id %s from %s. GMAIL IMAP cannot restore it:"\
                         " err={%s}" % (gm_id, db_gmail_ids_info[gm_id], str(the_exception)))
            gmvaulter.gstorer.quarantine_email(gm_id)
            gmvaulter.error_report['emails_in_quarantine'].append(gm_id) 
        else:
            raise the_exception
    elif isinstance(the_exception, imap_utils.PushEmailError):
        LOG.error("Catch the following exception %s" % (str(the_exception)))
        LOG.exception(the_exception)
        
        if the_exception.quarantined():
            LOG.critical("Quarantine email with gm id %s from %s. GMAIL IMAP cannot restore it:"\
                         " err={%s}" % (gm_id, db_gmail_ids_info[gm_id], str(the_exception)))
            gmvaulter.gstorer.quarantine_email(gm_id)
            gmvaulter.error_report['emails_in_quarantine'].append(gm_id) 
        else:
            raise the_exception          
    else:
        LOG.error("Catch the following exception %s" % (str(the_exception)))
        LOG.exception(the_exception)
        raise the_exception

def handle_sync_imap_error(the_exception, the_id, error_report, src):
    """
      function to handle IMAPError in gmvault
      type = chat or email
    """    
    if isinstance(the_exception, imaplib.IMAP4.abort):
        # imap abort error 
        # ignore it 
        # will have to do something with these ignored messages
        LOG.critical("Error while fetching message with imap id %s." % (the_id))
        LOG.critical("\n=== Exception traceback ===\n")
        LOG.critical(gmvault_utils.get_exception_traceback())
        LOG.critical("=== End of Exception traceback ===\n")
        try:
            #try to get the gmail_id
            curr = src.fetch(the_id, imap_utils.GIMAPFetcher.GET_GMAIL_ID) 
        except Exception, _: #pylint:disable-msg=W0703
            curr = None
            LOG.critical("Error when trying to get gmail id for message with imap id %s." % (the_id))
            LOG.critical("Disconnect, wait for 20 sec then reconnect.")
            src.disconnect()
            #could not fetch the gm_id so disconnect and sleep
            #sleep 10 sec
            time.sleep(10)
            LOG.critical("Reconnecting ...")
            src.connect()
            
        if curr:
            gmail_id = curr[the_id][imap_utils.GIMAPFetcher.GMAIL_ID]
        else:
            gmail_id = None
            
        #add ignored id
        error_report['cannot_be_fetched'].append((the_id, gmail_id))
        
        LOG.critical("Forced to ignore message with imap id %s, (gmail id %s)." \
                     % (the_id, (gmail_id if gmail_id else "cannot be read")))
        
    elif isinstance(the_exception, imaplib.IMAP4.error):
        # check if this is a cannot be fetched error 
        # I do not like to do string guessing within an exception but I do not have any choice here
        LOG.critical("Error while fetching message with imap id %s." % (the_id))
        LOG.critical("\n=== Exception traceback ===\n")
        LOG.critical(gmvault_utils.get_exception_traceback())
        LOG.critical("=== End of Exception traceback ===\n")
         
        #quarantine emails that have raised an abort error
        if str(the_exception).find("'Some messages could not be FETCHed (Failure)'") >= 0:
            try:
                #try to get the gmail_id
                LOG.critical("One more attempt. Trying to fetch the Gmail ID for %s" % (the_id) )
                curr = src.fetch(the_id, imap_utils.GIMAPFetcher.GET_GMAIL_ID) 
            except Exception, _: #pylint:disable-msg=W0703
                curr = None
            
            if curr:
                gmail_id = curr[the_id][imap_utils.GIMAPFetcher.GMAIL_ID]
            else:
                gmail_id = None
            
            #add ignored id
            error_report['cannot_be_fetched'].append((the_id, gmail_id))
            
            LOG.critical("Ignore message with imap id %s, (gmail id %s)" % (the_id, (gmail_id if gmail_id else "cannot be read")))
        
        else:
            raise the_exception #rethrow error
    else:
        raise the_exception    

class IMAPBatchFetcher(object):
    """
       Fetch IMAP data in batch 
    """
    def __init__(self, src, imap_ids, error_report, request, default_batch_size = 100):
        """
           constructor
        """
        self.src                = src
        self.imap_ids           = imap_ids
        self.def_batch_size     = default_batch_size
        self.request            = request
        self.error_report       = error_report  
        
        self.to_fetch           = list(imap_ids)
    
    def individual_fetch(self, imap_ids):
        """
           Find the imap_id creating the issue
           return the data related to the imap_ids
        """
        new_data = {}
        for the_id in imap_ids:    
            try: 
                single_data = self.src.fetch(the_id, self.request)
                new_data.update(single_data)                
            except Exception, error:
                handle_sync_imap_error(error, the_id, self.error_report, self.src) #do everything in this handler

        return new_data
   
    def __iter__(self):
        return self     
    
    def next(self):
        """
            Return the next batch of elements
        """
        new_data = {}
        batch = self.to_fetch[:self.def_batch_size]
        
        if len(batch) <= 0:
            raise StopIteration
        
        try:
        
            new_data = self.src.fetch(batch, self.request)
            
            self.to_fetch = self.to_fetch[self.def_batch_size:]
            
            return new_data

        except imaplib.IMAP4.error, _:
            new_data = self.individual_fetch(batch) 
    
        return new_data
    
    def reset(self):
        """
           Restart from the beginning
        """
        self.to_fetch = self.imap_ids              
               
#Client to support imap serch with non ascii char (not working because of imaplibs limitations)
'''class MonkeyIMAPClient(imapclient.IMAPClient): #pylint:disable=R0903,R0904
    """
       Need to extend the IMAPClient to do more things such as compression
       Compression inspired by http://www.janeelix.com/piers/python/py2html.cgi/piers/python/imaplib2
    """
    
    def __init__(self, host, port=None, use_uid=True, need_ssl=False):
        """
           constructor
        """
        super(MonkeyIMAPClient, self).__init__(host, port, use_uid, need_ssl)
    
    def _create_IMAP4(self): #pylint:disable=C0103
        """
           Factory method creating an IMAPCOMPSSL or a standard IMAP4 Class
        """
        imap_class = self.ssl and IMAP4COMPSSL or imaplib.IMAP4
        return imap_class(self.host, self.port)
    
    def xoauth_login(self, xoauth_cred ):
        """
           Connect with xoauth
           Redefine this method to suppress dependency to oauth2 (non-necessary)
        """

        typ, data = self._imap.authenticate('XOAUTH', lambda x: xoauth_cred)
        self._checkok('authenticate', typ, data)
        return data[0]  
    
    def old_search(self, criteria):
        """
           Perform a imap search or gmail search
        """
        if criteria.get('type','') == 'imap':
            #encoding criteria in utf-8
            req     = criteria['req'].encode('utf-8')
            charset = 'utf-8'
            return super(MonkeyIMAPClient, self).search(req, charset)
        elif criteria.get('type','') == 'gmail':
            return self.gmail_search(criteria.get('req',''))
        else:
            raise Exception("Unknown search type %s" % (criteria.get('type','no request type passed')))
    
    def search(self, criteria):
        """
           Perform a imap search or gmail search
        """
        if criteria.get('type','') == 'imap':
            #encoding criteria in utf-8
            #req     = criteria['req'].encode('utf-8')
            req     = criteria['req']
            charset = 'utf-8'
            #return super(MonkeyIMAPClient, self).search(req, charset)
            return self.imap_search(req, charset)
        
        elif criteria.get('type','') == 'gmail':
            return self.gmail_search(criteria.get('req',''))
        else:
            raise Exception("Unknown search type %s" % (criteria.get('type','no request type passed')))
    
    
        
    def gmail_search(self, criteria):
        """
           perform a search with gmailsearch criteria.
           eg, subject:Hello World
        """  
        criteria = criteria.replace('\\', '\\\\')
        criteria = criteria.replace('"', '\\"')

        #working but cannot send that understand when non ascii chars are used
        #args = ['CHARSET', 'utf-8', 'X-GM-RAW', '"%s"' % (criteria)]
        #typ, data = self._imap.uid('SEARCH', *args)

        #working Literal search 
        self._imap.literal = '"%s"' % (criteria)
        self._imap.literal = imaplib.MapCRLF.sub(imaplib.CRLF, self._imap.literal)
        self._imap.literal = self._imap.literal.encode("utf-8")

        #args = ['X-GM-RAW']
        #typ, data = self._imap.search('utf-8',*args)
        
        #use uid to keep the imap ids consistent
        args = ['CHARSET', 'utf-8', 'X-GM-RAW']
        typ, data = self._imap.uid('SEARCH', *args)
        
        self._checkok('search', typ, data)
        if data == [None]: # no untagged responses...
            return [ ]

        return [ long(i) for i in data[0].split() ]
    
    def append(self, folder, msg, flags=(), msg_time=None):
        """Append a message to *folder*.

        *msg* should be a string contains the full message including
        headers.

        *flags* should be a sequence of message flags to set. If not
        specified no flags will be set.

        *msg_time* is an optional datetime instance specifying the
        date and time to set on the message. The server will set a
        time if it isn't specified. If *msg_time* contains timezone
        information (tzinfo), this will be honoured. Otherwise the
        local machine's time zone sent to the server.

        Returns the APPEND response as returned by the server.
        """
        if msg_time:
            time_val = time.mktime(msg_time.timetuple())
        else:
            time_val = None

        flags_list = seq_to_parenlist(flags)

        typ, data = self._imap.append(self._encode_folder_name(folder) if folder else None,
                                      flags_list, time_val, msg)
        self._checkok('append', typ, data)

        return data[0]
    
    def enable_compression(self):
        """
        enable_compression()
        Ask the server to start compressing the connection.
        Should be called from user of this class after instantiation, as in:
            if 'COMPRESS=DEFLATE' in imapobj.capabilities:
                imapobj.enable_compression()
        """
        ret_code, _ = self._imap._simple_command('COMPRESS', 'DEFLATE') #pylint: disable=W0212
        if ret_code == 'OK':
            self._imap.activate_compression()
        else:
            #no errors for the moment
            pass
'''
        

class GMVaulter(object):
    """
       Main object operating over gmail
    """ 
    NB_GRP_OF_ITEMS         = 1400
    EMAIL_RESTORE_PROGRESS  = 'email_last_id.restore'
    CHAT_RESTORE_PROGRESS   = 'chat_last_id.restore'
    EMAIL_SYNC_PROGRESS     = 'email_last_id.sync'
    CHAT_SYNC_PROGRESS      = 'chat_last_id.sync'
    
    OP_EMAIL_RESTORE = "EM_RESTORE"
    OP_EMAIL_SYNC    = "EM_SYNC"
    OP_CHAT_RESTORE  = "CH_RESTORE"
    OP_CHAT_SYNC    = "CH_SYNC"
    
    OP_TO_FILENAME = { OP_EMAIL_RESTORE : EMAIL_RESTORE_PROGRESS,
                       OP_EMAIL_SYNC    : EMAIL_SYNC_PROGRESS,
                       OP_CHAT_RESTORE  : CHAT_RESTORE_PROGRESS,
                       OP_CHAT_SYNC     : CHAT_SYNC_PROGRESS
                     }
    
    
    def __init__(self, db_root_dir, host, port, login, \
                 credential, read_only_access = True, use_encryption = False): #pylint:disable-msg=R0913,R0914
        """
           constructor
        """   
        self.db_root_dir = db_root_dir
        
        #create dir if it doesn't exist
        gmvault_utils.makedirs(self.db_root_dir)
        
        #keep track of login email
        self.login = login
            
        # create source and try to connect
        self.src = imap_utils.GIMAPFetcher(host, port, login, credential, \
                                           readonly_folder = read_only_access)
        
        self.src.connect()
        
        LOG.debug("Connected")
        
        self.use_encryption = use_encryption
        
        #to report gmail imap problems
        self.error_report = { 'empty' : [] ,
                              'cannot_be_fetched'  : [],
                              'emails_in_quarantine' : [],
                              'reconnections' : 0}
        
        #instantiate gstorer
        self.gstorer =  gmvault_db.GmailStorer(self.db_root_dir, self.use_encryption)
        
        #timer used to mesure time spent in the different values
        self.timer = gmvault_utils.Timer()
        
    @classmethod
    def get_imap_request_btw_2_dates(cls, begin_date, end_date):
        """
           Return the imap request for those 2 dates
        """
        imap_req = 'Since %s Before %s' % (gmvault_utils.datetime2imapdate(begin_date), gmvault_utils.datetime2imapdate(end_date))
        
        return imap_req
    
    def get_operation_report(self):
        """
           Return the error report
        """
        the_str = "\n================================================================\n"\
              "Number of reconnections: %d.\nNumber of emails quarantined: %d.\n" \
              "Number of emails that could not be fetched: %d.\n" \
              "Number of emails that were returned empty by gmail: %d\n"\
              "================================================================" \
              % (self.error_report['reconnections'], \
                 len(self.error_report['emails_in_quarantine']), \
                 len(self.error_report['cannot_be_fetched']), \
                 len(self.error_report['empty'])
                )
              
        LOG.debug("error_report complete structure = %s" % (self.error_report))
        
        return the_str
        
    @classmethod
    def _get_next_date(cls, a_current_date, start_month_beginning = False):
        """
           return the next date necessary to build the imap req
        """
        if start_month_beginning:
            dummy_date   = a_current_date.replace(day=1)
        else:
            dummy_date   = a_current_date
            
        # the next date = current date + 1 month
        return dummy_date + datetime.timedelta(days=31)
        
    @classmethod
    def check_email_on_disk(cls, a_gstorer, a_id, a_dir = None):
        """
           Factory method to create the object if it exists
        """
        try:
            a_dir = a_gstorer.get_directory_from_id(a_id, a_dir)
           
            if a_dir:
                return a_gstorer.unbury_metadata(a_id, a_dir) 
            
        except ValueError, json_error:
            LOG.exception("Cannot read file %s. Try to fetch the data again" % ('%s.meta' % (a_id)), json_error )
        
        return None
    
    @classmethod
    def _metadata_needs_update(cls, curr_metadata, new_metadata, chat_metadata = False):
        """
           Needs update
        """
        if curr_metadata[gmvault_db.GmailStorer.ID_K] != new_metadata['X-GM-MSGID']:
            raise Exception("Gmail id has changed for %s" % (curr_metadata['id']))
                
        #check flags   
        prev_set = set(new_metadata['FLAGS'])    
        
        for flag in curr_metadata['flags']:
            if flag not in prev_set:
                return True
            else:
                prev_set.remove(flag)
        
        if len(prev_set) > 0:
            return True
        
        #check labels
        prev_labels = set(new_metadata['X-GM-LABELS'])
        
        if chat_metadata: #add gmvault-chats labels
            prev_labels.add(gmvault_db.GmailStorer.CHAT_GM_LABEL)
            
        
        for label in curr_metadata['labels']:
            if label not in prev_labels:
                return True
            else:
                prev_labels.remove(label)
        
        if len(prev_labels) > 0:
            return True
        
        return False
    
    
    def _check_email_db_ownership(self, ownership_control):
        """
           Check email database ownership.
           If ownership control activated then fail if a new additional owner is added.
           Else if no ownership control allow one more user and save it in the list of owners
           
           Return the number of owner this will be used to activate or not the db clean.
           Activating a db cleaning on a multiownership db would be a catastrophy as it would delete all
           the emails from the others users.
        """
        #check that the gmvault-db is not associated with another user
        db_owners = self.gstorer.get_db_owners()
        if ownership_control:
            if len(db_owners) > 0 and self.login not in db_owners: #db owner should not be different unless bypass activated
                raise Exception("The email database %s is already associated with one or many logins: %s."\
                                " Use option (-m, --multiple-db-owner) if you want to link it with %s" \
                                % (self.db_root_dir, ", ".join(db_owners), self.login))
        else:
            if len(db_owners) == 0:
                LOG.critical("Establish %s as the owner of the Gmvault db %s." % (self.login, self.db_root_dir))  
            elif len(db_owners) > 0 and self.login not in db_owners:
                LOG.critical("The email database %s is hosting emails from %s. It will now also store emails from %s" \
                             % (self.db_root_dir, ", ".join(db_owners), self.login))
                
        #try to save db_owner in the list of owners
        self.gstorer.store_db_owner(self.login)
      
    def _sync_chats(self, imap_req, compress, restart):
        """
           Previous working sync for chats
           backup the chat messages
        """
        chat_dir = None
        
        timer = gmvault_utils.Timer() #start local timer for chat
        timer.start()
        
        LOG.debug("Before selection")
        if self.src.is_visible('CHATS'):
            chat_dir = self.src.select_folder('CHATS')
        
        LOG.debug("Selection is finished")

        if chat_dir:
            #imap_ids = self.src.search({ 'type': 'imap', 'req': 'ALL' })
            imap_ids = self.src.search(imap_req)
            
            # check if there is a restart
            if restart:
                LOG.critical("Restart mode activated. Need to find information in Gmail, be patient ...")
                imap_ids = self.get_gmails_ids_left_to_sync(self.OP_CHAT_SYNC, imap_ids)
            
            total_nb_chats_to_process = len(imap_ids) # total number of emails to get
            
            LOG.critical("%d chat messages to be fetched." % (total_nb_chats_to_process))
            
            nb_chats_processed = 0
            
            to_fetch = set(imap_ids)
            batch_fetcher = IMAPBatchFetcher(self.src, imap_ids, self.error_report, \
                                             imap_utils.GIMAPFetcher.GET_ALL_BUT_DATA, \
                                             default_batch_size = \
                                             gmvault_utils.get_conf_defaults().getint("General", \
                                             "nb_messages_per_batch", 500))
        
        
            for new_data in batch_fetcher:
                for the_id in new_data: 
                    if new_data.get(the_id, None):       
                        gid = None
                        
                        LOG.debug("\nProcess imap chat id %s" % ( the_id ))
                        
                        gid = new_data[the_id][imap_utils.GIMAPFetcher.GMAIL_ID]
                        
                        the_dir      = self.gstorer.get_sub_chats_dir()
                        
                        LOG.critical("Process chat num %d (imap_id:%s) into %s." % (nb_chats_processed, the_id, the_dir))
                    
                        #pass the dir and the ID
                        curr_metadata = GMVaulter.check_email_on_disk( self.gstorer , \
                                                                       new_data[the_id][imap_utils.GIMAPFetcher.GMAIL_ID], \
                                                                       the_dir)
                        
                        #if on disk check that the data is not different
                        if curr_metadata:
                            
                            if self._metadata_needs_update(curr_metadata, new_data[the_id], chat_metadata = True):
                                
                                LOG.debug("Chat with imap id %s and gmail id %s has changed. Updated it." % (the_id, gid))
                                
                                #restore everything at the moment
                                gid  = self.gstorer.bury_chat_metadata(new_data[the_id], local_dir = the_dir)
                                
                                #update local index id gid => index per directory to be thought out
                            else:
                                LOG.debug("The metadata for chat %s already exists and is identical to the one on GMail." % (gid))
                        else:  
                            try:
                                #get the data
                                email_data = self.src.fetch(the_id, imap_utils.GIMAPFetcher.GET_DATA_ONLY )
                                
                                new_data[the_id][imap_utils.GIMAPFetcher.EMAIL_BODY] = \
                                email_data[the_id][imap_utils.GIMAPFetcher.EMAIL_BODY]
                                
                                # store data on disk within year month dir 
                                gid  = self.gstorer.bury_chat(new_data[the_id], local_dir = the_dir, compress = compress)
                                
                                #update local index id gid => index per directory to be thought out
                                LOG.debug("Create and store chat with imap id %s, gmail id %s." % (the_id, gid))   
                            except Exception, error:
                                #do everything in this handler 
                                handle_sync_imap_error(error, the_id, self.error_report, self.src)    
                    
                        nb_chats_processed += 1    
                        
                        #indicate every 50 messages the number of messages left to process
                        left_emails = (total_nb_chats_to_process - nb_chats_processed)
                        
                        if (nb_chats_processed % 50) == 0 and (left_emails > 0):
                            elapsed = timer.elapsed() #elapsed time in seconds
                            LOG.critical("\n== Processed %d emails in %s. %d left to be stored (time estimate %s).==\n" % \
                                         (nb_chats_processed,  timer.seconds_to_human_time(elapsed), \
                                          left_emails, \
                                          timer.estimate_time_left(nb_chats_processed, elapsed, left_emails)))
                        
                        # save id every 10 restored emails
                        if (nb_chats_processed % 10) == 0:
                            if gid:
                                self.save_lastid(self.OP_CHAT_SYNC, gid)
                    else:
                        LOG.info("Could not process imap with id %s. Ignore it\n")
                        self.error_report['empty'].append((the_id, None)) 
                    
                to_fetch -= set(new_data.keys()) #remove all found keys from to_fetch set
                
            for the_id in to_fetch:
                # case when gmail IMAP server returns OK without any data whatsoever
                # eg. imap uid 142221L ignore it
                LOG.info("Could not process chat with id %s. Ignore it\n" % (the_id))
                self.error_report['empty_chats'].append((the_id, None))

        else:
            imap_ids = []    
        
        LOG.critical("\nChats synchronisation operation performed in %s.\n" % (timer.seconds_to_human_time(timer.elapsed())))
        return imap_ids

    def _sync_emails(self, imap_req, compress, restart):
        """
           Previous sync for emails
           First part of the double pass strategy: 
           - create and update emails in db
           
        """    
        timer = gmvault_utils.Timer()
        timer.start()
           
        #select all mail folder using the constant name defined in GIMAPFetcher
        self.src.select_folder('ALLMAIL')
        
        # get all imap ids in All Mail
        imap_ids = self.src.search(imap_req)
        
        # check if there is a restart
        if restart:
            LOG.critical("Restart mode activated for emails. Need to find information in Gmail, be patient ...")
            imap_ids = self.get_gmails_ids_left_to_sync(self.OP_EMAIL_SYNC, imap_ids)
        
        total_nb_emails_to_process = len(imap_ids) # total number of emails to get
        
        LOG.critical("%d emails to be fetched." % (total_nb_emails_to_process))
        
        nb_emails_processed = 0
        
        to_fetch = set(imap_ids)
        batch_fetcher = IMAPBatchFetcher(self.src, imap_ids, self.error_report, imap_utils.GIMAPFetcher.GET_ALL_BUT_DATA, \
                                         default_batch_size = \
                                         gmvault_utils.get_conf_defaults().getint("General","nb_messages_per_batch",500))
        
        #LAST Thing to do remove all found ids from imap_ids and if ids left add missing in report
        for new_data in batch_fetcher:            
            for the_id in new_data:
                #LOG.debug("new_data = %s\n" % (new_data))
                if new_data.get(the_id, None):
                    LOG.debug("\nProcess imap id %s" % ( the_id ))
                        
                    gid = new_data[the_id][imap_utils.GIMAPFetcher.GMAIL_ID]
                    
                    the_dir      = gmvault_utils.get_ym_from_datetime(new_data[the_id][imap_utils.GIMAPFetcher.IMAP_INTERNALDATE])
                    
                    LOG.critical("Process email num %d (imap_id:%s) from %s." % (nb_emails_processed, the_id, the_dir))
                    
                    #decode the labels that are received as utf7 => unicode
                    new_data[the_id][imap_utils.GIMAPFetcher.GMAIL_LABELS] = \
                    imap_utils.decode_labels(new_data[the_id][imap_utils.GIMAPFetcher.GMAIL_LABELS])
                
                    #pass the dir and the ID
                    curr_metadata = GMVaulter.check_email_on_disk( self.gstorer , \
                                                                   new_data[the_id][imap_utils.GIMAPFetcher.GMAIL_ID], \
                                                                   the_dir)
                    
                    #if on disk check that the data is not different
                    if curr_metadata:
                        
                        LOG.debug("metadata for %s already exists. Check if different." % (gid))
                        
                        if self._metadata_needs_update(curr_metadata, new_data[the_id]):
                            
                            LOG.debug("Email with imap id %s and gmail id %s has changed. Updated it." % (the_id, gid))
                            
                            #restore everything at the moment
                            gid  = self.gstorer.bury_metadata(new_data[the_id], local_dir = the_dir)
                            
                            #update local index id gid => index per directory to be thought out
                        else:
                            LOG.debug("On disk metadata for %s is up to date." % (gid))
                    else:  
                        try:
                            #get the data
                            LOG.debug("Get Data for %s." % (gid))
                            email_data = self.src.fetch(the_id, imap_utils.GIMAPFetcher.GET_DATA_ONLY )
                            
                            new_data[the_id][imap_utils.GIMAPFetcher.EMAIL_BODY] = \
                            email_data[the_id][imap_utils.GIMAPFetcher.EMAIL_BODY]
                            
                            # store data on disk within year month dir 
                            gid  = self.gstorer.bury_email(new_data[the_id], local_dir = the_dir, compress = compress)
                            
                            #update local index id gid => index per directory to be thought out
                            LOG.debug("Create and store email with imap id %s, gmail id %s." % (the_id, gid))   
                        except Exception, error:
                            handle_sync_imap_error(error, the_id, self.error_report, self.src) #do everything in this handler    
                    
                    nb_emails_processed += 1
                    
                    #indicate every 50 messages the number of messages left to process
                    left_emails = (total_nb_emails_to_process - nb_emails_processed)
                    
                    if (nb_emails_processed % 50) == 0 and (left_emails > 0):
                        elapsed = timer.elapsed() #elapsed time in seconds
                        LOG.critical("\n== Processed %d emails in %s. %d left to be stored (time estimate %s).==\n" % \
                                     (nb_emails_processed,  \
                                      timer.seconds_to_human_time(elapsed), left_emails, \
                                      timer.estimate_time_left(nb_emails_processed, elapsed, left_emails)))
                    
                    # save id every 10 restored emails
                    if (nb_emails_processed % 10) == 0:
                        if gid:
                            self.save_lastid(self.OP_EMAIL_SYNC, gid)
                else:
                    LOG.info("Could not process imap with id %s. Ignore it\n")
                    self.error_report['empty'].append((the_id, gid if gid else None))
                    
            to_fetch -= set(new_data.keys()) #remove all found keys from to_fetch set
                
        for the_id in to_fetch:
            # case when gmail IMAP server returns OK without any data whatsoever
            # eg. imap uid 142221L ignore it
            LOG.info("Could not process imap with id %s. Ignore it\n")
            self.error_report['empty'].append((the_id, None))
        
        LOG.critical("\nEmails synchronisation operation performed in %s.\n" % (timer.seconds_to_human_time(timer.elapsed())))
        
        return imap_ids
    
    def sync(self, imap_req = imap_utils.GIMAPFetcher.IMAP_ALL, compress_on_disk = True, \
             db_cleaning = False, ownership_checking = True, \
            restart = False, emails_only = False, chats_only = False):
        """
           sync mode 
        """
        #check ownership to have one email per db unless user wants different
        #save the owner if new
        self._check_email_db_ownership(ownership_checking)
                
        if not compress_on_disk:
            LOG.critical("Disable compression when storing emails.")
            
        if self.use_encryption:
            LOG.critical("Encryption activated. All emails will be encrypted before to be stored.")
            LOG.critical("Please take care of the encryption key stored in (%s) or all"\
                         " your stored emails will become unreadable." \
                         % (gmvault_db.GmailStorer.get_encryption_key_path(self.db_root_dir)))
        
        self.timer.start() #start syncing emails
        
        if not chats_only:
            # backup emails
            LOG.critical("Start emails synchronization.\n")
            self._sync_emails(imap_req, compress = compress_on_disk, restart = restart)
        else:
            LOG.critical("Skip emails synchronization.\n")
        
        if not emails_only:
            # backup chats
            LOG.critical("Start chats synchronization.\n")
            self._sync_chats(imap_req, compress = compress_on_disk, restart = restart)
        else:
            LOG.critical("\nSkip chats synchronization.\n")
        
        #delete supress emails from DB since last sync
        if len(self.gstorer.get_db_owners()) <= 1:
            self.check_clean_db(db_cleaning)
        else:
            LOG.critical("Deactivate database cleaning on a multi-owners Gmvault db.")
        
        LOG.critical("Synchronisation operation performed in %s.\n" \
                     % (self.timer.seconds_to_human_time(self.timer.elapsed())))
        
        #update number of reconnections
        self.error_report["reconnections"] = self.src.total_nb_reconns
        
        return self.error_report

    
    def _delete_sync(self, imap_ids, db_gmail_ids, db_gmail_ids_info, msg_type):
        """
           Delete emails from the database if necessary
           imap_ids      : all remote imap_ids to check
           db_gmail_ids_info : info read from metadata
           msg_type : email or chat
        """
        
        # optimize nb of items
        nb_items = self.NB_GRP_OF_ITEMS if len(imap_ids) >= self.NB_GRP_OF_ITEMS else len(imap_ids)
        
        LOG.critical("Call Gmail to check the stored %ss against the Gmail %ss ids and see which ones have been deleted.\n\n"\
                     "This might take a few minutes ...\n" % (msg_type, msg_type)) 
         
        #calculate the list elements to delete
        #query nb_items items in one query to minimise number of imap queries
        for group_imap_id in itertools.izip_longest(fillvalue=None, *[iter(imap_ids)]*nb_items):
            
            # if None in list remove it
            if None in group_imap_id: 
                group_imap_id = [ im_id for im_id in group_imap_id if im_id != None ]
            
            data = self.src.fetch(group_imap_id, imap_utils.GIMAPFetcher.GET_GMAIL_ID)
            
            # syntax for 2.7 set comprehension { data[key][imap_utils.GIMAPFetcher.GMAIL_ID] for key in data }
            # need to create a list for 2.6
            db_gmail_ids.difference_update([data[key][imap_utils.GIMAPFetcher.GMAIL_ID] for key in data ])
            
            if len(db_gmail_ids) == 0:
                break
        
        LOG.critical("Will delete %s %s(s) from gmvault db.\n" % (len(db_gmail_ids), msg_type) )
        for gm_id in db_gmail_ids:
            LOG.critical("gm_id %s not in the Gmail server. Delete it." % (gm_id))
            self.gstorer.delete_emails([(gm_id, db_gmail_ids_info[gm_id])], msg_type)
        
    def get_gmails_ids_left_to_sync(self, op_type, imap_ids):
        """
           Get the ids that still needs to be sync
           Return a list of ids
        """
        
        filename = self.OP_TO_FILENAME.get(op_type, None)
        
        if not filename:
            raise Exception("Bad Operation (%s) in save_last_id. "\
                  "This should not happen, send the error to the software developers." % (op_type))
        
        filepath = '%s/%s_%s' % (self.gstorer.get_info_dir(), self.login, filename)
        
        if not os.path.exists(filepath):
            LOG.critical("last_id.sync file %s doesn't exist.\nSync the full list of backed up emails." %(filepath))
            return imap_ids
        
        json_obj = json.load(open(filepath, 'r'))
        
        last_id = json_obj['last_id']
        
        last_id_index = -1
        
        new_gmail_ids = imap_ids
        
        try:
            #get imap_id from stored gmail_id
            dummy = self.src.search({'type':'imap', 'req':'X-GM-MSGID %s' % (last_id)})
            
            imap_id = dummy[0]
            last_id_index = imap_ids.index(imap_id)
            LOG.critical("Restart from gmail id %s (imap id %s)." % (last_id, imap_id))
            new_gmail_ids = imap_ids[last_id_index:]   
        except Exception, _: #ignore any exception and try to get all ids in case of problems. pylint:disable=W0703
            #element not in keys return current set of keys
            LOG.critical("Error: Cannot restore from last restore gmail id. It is not in Gmail."\
                         " Sync the complete list of gmail ids requested from Gmail.")
        
        return new_gmail_ids
        
    def check_clean_db(self, db_cleaning):
        """
           Check and clean the database (remove file that are not anymore in Gmail
        """
        owners = self.gstorer.get_db_owners()
        if not db_cleaning: #decouple the 2 conditions for activating cleaning
            LOG.debug("db_cleaning is off so ignore removing deleted emails from disk.")
            return
        elif len(owners) > 1:
            LOG.critical("Gmvault db hosting emails from different accounts: %s.\n"\
                         "Cannot activate database cleaning." % (", ".join(owners)))
            return
        else:
            LOG.critical("Look for emails/chats that are in the Gmvault db but not in Gmail servers anymore.\n")
            
            #get gmail_ids from db
            LOG.critical("Read all gmail ids from the Gmvault db. It might take a bit of time ...\n")
            
            timer = gmvault_utils.Timer() # needed for enhancing the user information
            timer.start()
            
            db_gmail_ids_info = self.gstorer.get_all_existing_gmail_ids()
        
            LOG.critical("Found %s email(s) in the Gmvault db.\n" % (len(db_gmail_ids_info)) )
        
            #create a set of keys
            db_gmail_ids = set(db_gmail_ids_info.keys())
            
            # get all imap ids in All Mail
            self.src.select_folder('ALLMAIL') #go to all mail
            imap_ids = self.src.search(imap_utils.GIMAPFetcher.IMAP_ALL) #search all
            
            LOG.debug("Got %s emails imap_id(s) from the Gmail Server." % (len(imap_ids)))
            
            #delete supress emails from DB since last sync
            self._delete_sync(imap_ids, db_gmail_ids, db_gmail_ids_info, 'email')
            
            # get all chats ids
            if self.src.is_visible('CHATS'):
            
                db_gmail_ids_info = self.gstorer.get_all_chats_gmail_ids()
                
                LOG.critical("Found %s chat(s) in the Gmvault db.\n" % (len(db_gmail_ids_info)) )
                
                self.src.select_folder('CHATS') #go to chats
                chat_ids = self.src.search(imap_utils.GIMAPFetcher.IMAP_ALL)
                
                db_chat_ids = set(db_gmail_ids_info.keys())
                
                LOG.debug("Got %s chat imap_ids from the Gmail Server." % (len(chat_ids)))
            
                #delete supress emails from DB since last sync
                self._delete_sync(chat_ids, db_chat_ids, db_gmail_ids_info , 'chat')
            else:
                LOG.critical("Chats IMAP Directory not visible on Gmail. Ignore deletion of chats.")
                
            
            LOG.critical("\nDeletion checkup done in %s." % (timer.elapsed_human_time()))
            
    
    def remote_sync(self):
        """
           Sync with a remote source (IMAP mirror or cloud storage area)
        """
        #sync remotely 
        pass
        
    
    def save_lastid(self, op_type, gm_id):
        """
           Save the passed gmid in last_id.restore
           For the moment reopen the file every time
        """
        
        filename = self.OP_TO_FILENAME.get(op_type, None)
        
        if not filename:
            raise Exception("Bad Operation (%s) in save_last_id. "\
                            "This should not happen, send the error to the software developers." % (op_type))
        
        #filepath = '%s/%s_%s' % (gmvault_utils.get_home_dir_path(), self.login, filename)  
        filepath = '%s/%s_%s' % (self.gstorer.get_info_dir(), self.login, filename)  
        
        the_fd = open(filepath, 'w')
        
        json.dump({
                    'last_id' : gm_id  
                  }, the_fd)
        
        the_fd.close()
        
    def get_gmails_ids_left_to_restore(self, op_type, db_gmail_ids_info):
        """
           Get the ids that still needs to be restored
           Return a dict key = gm_id, val = directory
        """
        filename = self.OP_TO_FILENAME.get(op_type, None)
        
        if not filename:
            raise Exception("Bad Operation (%s) in save_last_id. This should not happen,"\
                            " send the error to the software developers." % (op_type))
        
        
        #filepath = '%s/%s_%s' % (gmvault_utils.get_home_dir_path(), self.login, filename)
        filepath = '%s/%s_%s' % (self.gstorer.get_info_dir(), self.login, filename)
        
        if not os.path.exists(filepath):
            LOG.critical("last_id restore file %s doesn't exist.\nRestore the full list of backed up emails." %(filepath))
            return db_gmail_ids_info
        
        json_obj = json.load(open(filepath, 'r'))
        
        last_id = json_obj['last_id']
        
        last_id_index = -1
        try:
            keys = db_gmail_ids_info.keys()
            last_id_index = keys.index(last_id)
            LOG.critical("Restart from gmail id %s." % (last_id))
        except ValueError, _:
            #element not in keys return current set of keys
            LOG.error("Cannot restore from last restore gmail id. It is not in the disk database.")
        
        new_gmail_ids_info = collections_utils.OrderedDict()
        if last_id_index != -1:
            for key in db_gmail_ids_info.keys()[last_id_index+1:]:
                new_gmail_ids_info[key] =  db_gmail_ids_info[key]
        else:
            new_gmail_ids_info = db_gmail_ids_info    
            
        return new_gmail_ids_info 
           
    def restore(self, pivot_dir = None, extra_labels = [], \
                restart = False, emails_only = False, chats_only = False): #pylint:disable=W0102
        """
           Restore emails in a gmail account
        """
        self.timer.start() #start restoring
        
        #self.src.select_folder('ALLMAIL') #insure that Gmvault is in ALLMAIL
        
        if not chats_only:
            # backup emails
            LOG.critical("Start emails restoration.\n")
            
            if pivot_dir:
                LOG.critical("Quick mode activated. Will only restore all emails since %s.\n" % (pivot_dir))
            
            self.restore_emails(pivot_dir, extra_labels, restart)
        else:
            LOG.critical("Skip emails restoration.\n")
        
        if not emails_only:
            # backup chats
            LOG.critical("Start chats restoration.\n")
            self.restore_chats(extra_labels, restart)
        else:
            LOG.critical("Skip chats restoration.\n")
        
        LOG.critical("Restore operation performed in %s.\n" \
                     % (self.timer.seconds_to_human_time(self.timer.elapsed())))
        
        #update number of reconnections
        self.error_report["reconnections"] = self.src.total_nb_reconns
        
        return self.error_report
       
    def restore_chats(self, extra_labels = [], restart = False): #pylint:disable=W0102
        """
           restore chats
        """
        LOG.critical("Restore chats in gmail account %s." % (self.login) ) 
                
        LOG.critical("Read chats info from %s gmvault-db." % (self.db_root_dir))
        
        #get gmail_ids from db
        db_gmail_ids_info = self.gstorer.get_all_chats_gmail_ids()
        
        LOG.critical("Total number of chats to restore %s." % (len(db_gmail_ids_info.keys())))
        
        if restart:
            db_gmail_ids_info = self.get_gmails_ids_left_to_restore(self.OP_CHAT_RESTORE, db_gmail_ids_info)
        
        total_nb_emails_to_restore = len(db_gmail_ids_info)
        LOG.critical("Got all chats id left to restore. Still %s chats to do.\n" % (total_nb_emails_to_restore) )
        
        existing_labels     = set() #set of existing labels to not call create_gmail_labels all the time
        nb_emails_restored  = 0  #to count nb of emails restored
        labels_to_apply     = collections_utils.SetMultimap()

        #get all mail folder name
        all_mail_name = self.src.get_folder_name("ALLMAIL")
        
        # go to DRAFTS folder because if you are in ALL MAIL when uploading emails it is very slow
        folder_def_location = gmvault_utils.get_conf_defaults().get("General", "restore_default_location", "DRAFTS")
        self.src.select_folder(folder_def_location)
        
        timer = gmvault_utils.Timer() # local timer for restore emails
        timer.start()
        
        nb_items = gmvault_utils.get_conf_defaults().get_int("General", "nb_messages_per_restore_batch", 100) 
        
        for group_imap_ids in itertools.izip_longest(fillvalue=None, *[iter(db_gmail_ids_info)]*nb_items): 

            last_id = group_imap_ids[-1] #will be used to save the last id
            #remove all None elements from group_imap_ids
            group_imap_ids = itertools.ifilter(lambda x: x != None, group_imap_ids)
           
            labels_to_create    = set() #create label set
            labels_to_create.update(extra_labels) # add extra labels to applied to all emails
            
            LOG.critical("Processing next batch of %s chats.\n" % (nb_items))
            
            # unbury the metadata for all these emails
            for gm_id in group_imap_ids:    
                email_meta, email_data = self.gstorer.unbury_email(gm_id)
                
                LOG.critical("Pushing chat content with id %s." % (gm_id))
                LOG.debug("Subject = %s." % (email_meta[self.gstorer.SUBJECT_K]))
                try:
                    # push data in gmail account and get uids
                    imap_id = self.src.push_data(all_mail_name, email_data, \
                                    email_meta[self.gstorer.FLAGS_K] , \
                                    email_meta[self.gstorer.INT_DATE_K] )      
                
                    #labels for this email => real_labels U extra_labels
                    labels = set(email_meta[self.gstorer.LABELS_K])
                    
                    # add in the labels_to_create struct
                    for label in labels:
                        LOG.debug("label = %s\n" % (label))
                        labels_to_apply[str(label)] = imap_id
            
                    # get list of labels to create (do a union with labels to create)
                    labels_to_create.update([ label for label in labels if label not in existing_labels])                  
                
                except Exception, err:
                    handle_restore_imap_error(err, gm_id, db_gmail_ids_info, self)

            #create the non existing labels and update existing labels
            if len(labels_to_create) > 0:
                LOG.debug("Labels creation tentative for chats ids %s." % (group_imap_ids))
                existing_labels = self.src.create_gmail_labels(labels_to_create, existing_labels)
                
            # associate labels with emails
            LOG.critical("Applying labels to the current batch of chats.")
            try:
                LOG.debug("Changing directory. Going into ALLMAIL")
                self.src.select_folder('ALLMAIL') #go to ALL MAIL to make STORE usable
                for label in labels_to_apply.keys():
                    self.src.apply_labels_to(labels_to_apply[label], [label]) 
            except Exception, err:
                LOG.error("Problem when applying labels %s to the following ids: %s" %(label, labels_to_apply[label]), err)
                if isinstance(err, imaplib.IMAP4.abort) and str(err).find("=> Gmvault ssl socket error: EOF") >= 0:
                    # if this is a Gmvault SSL Socket error ignore labelling and continue the restore
                    LOG.critical("Ignore labelling")
                    LOG.critical("Disconnecting and reconnecting to restart cleanly.")
                    self.src.reconnect() #reconnect
                else:
                    raise err
            finally:
                self.src.select_folder(folder_def_location) # go back to an empty DIR (Drafts) to be fast
                labels_to_apply = collections_utils.SetMultimap() #reset label to apply
            
            nb_emails_restored += nb_items
                
            #indicate every 10 messages the number of messages left to process
            left_emails = (total_nb_emails_to_restore - nb_emails_restored)
            
            if (left_emails > 0): 
                elapsed = timer.elapsed() #elapsed time in seconds
                LOG.critical("\n== Processed %d chats in %s. %d left to be restored "\
                             "(time estimate %s).==\n" % \
                             (nb_emails_restored, timer.seconds_to_human_time(elapsed), \
                              left_emails, timer.estimate_time_left(nb_emails_restored, elapsed, left_emails)))
            
            # save id every nb_items restored emails
            # add the last treated gm_id
            self.save_lastid(self.OP_EMAIL_RESTORE, last_id)
            
        return self.error_report 
                    
    def restore_emails(self, pivot_dir = None, extra_labels = [], restart = False):
        """
           restore emails in a gmail account using batching to group restore
           If you are not in "All Mail" Folder, it is extremely fast to push emails.
           But it is not possible to reapply labels if you are not in All Mail because the uid which is returned
           is dependant on the folder. On the other hand, you can restore labels in batch which would help gaining lots of time.
           The idea is to get a batch of 50 emails and push them all in the mailbox one by one and get the uid for each of them.
           Then create a dict of labels => uid_list and for each label send a unique store command after having changed dir
        """
        LOG.critical("Restore emails in gmail account %s." % (self.login) ) 
        
        LOG.critical("Read email info from %s gmvault-db." % (self.db_root_dir))
        
        #get gmail_ids from db
        db_gmail_ids_info = self.gstorer.get_all_existing_gmail_ids(pivot_dir)
        
        LOG.critical("Total number of elements to restore %s." % (len(db_gmail_ids_info.keys())))
        
        if restart:
            db_gmail_ids_info = self.get_gmails_ids_left_to_restore(self.OP_EMAIL_RESTORE, db_gmail_ids_info)
        
        total_nb_emails_to_restore = len(db_gmail_ids_info)
        
        LOG.critical("Got all emails id left to restore. Still %s emails to do.\n" % (total_nb_emails_to_restore) )
        
        existing_labels     = set() #set of existing labels to not call create_gmail_labels all the time
        nb_emails_restored  = 0  #to count nb of emails restored
        labels_to_apply     = collections_utils.SetMultimap()

        #get all mail folder name
        all_mail_name = self.src.get_folder_name("ALLMAIL")
        
        # go to DRAFTS folder because if you are in ALL MAIL when uploading emails it is very slow
        folder_def_location = gmvault_utils.get_conf_defaults().get("General", "restore_default_location", "DRAFTS")
        self.src.select_folder(folder_def_location)
        
        timer = gmvault_utils.Timer() # local timer for restore emails
        timer.start()
        
        nb_items = gmvault_utils.get_conf_defaults().get_int("General", "nb_messages_per_restore_batch", 80) 
        
        for group_imap_ids in itertools.izip_longest(fillvalue=None, *[iter(db_gmail_ids_info)]*nb_items): 
            
            last_id = group_imap_ids[-1] #will be used to save the last id
            #remove all None elements from group_imap_ids
            group_imap_ids = itertools.ifilter(lambda x: x != None, group_imap_ids)
           
            labels_to_create    = set() #create label set
            labels_to_create.update(extra_labels) # add extra labels to applied to all emails
            
            LOG.critical("Processing next batch of %s emails.\n" % (nb_items))
            
            # unbury the metadata for all these emails
            for gm_id in group_imap_ids:    
                email_meta, email_data = self.gstorer.unbury_email(gm_id)
                
                LOG.critical("Pushing email body with id %s." % (gm_id))
                LOG.debug("Subject = %s." % (email_meta[self.gstorer.SUBJECT_K]))
                try:
                    # push data in gmail account and get uids
                    imap_id = self.src.push_data(all_mail_name, email_data, \
                                    email_meta[self.gstorer.FLAGS_K] , \
                                    email_meta[self.gstorer.INT_DATE_K] )      
                
                    #labels for this email => real_labels U extra_labels
                    labels = set(email_meta[self.gstorer.LABELS_K])
                    
                    # add in the labels_to_create struct
                    for label in labels:
                        if label != "\\Starred":
                            #LOG.debug("label = %s\n" % (label.encode('utf-8')))
                            LOG.debug("label = %s\n" % (label))
                            labels_to_apply[label] = imap_id
            
                    # get list of labels to create (do a union with labels to create)
                    labels_to_create.update([ label for label in labels if label not in existing_labels])                  
                
                except Exception, err:
                    handle_restore_imap_error(err, gm_id, db_gmail_ids_info, self)

            #create the non existing labels and update existing labels
            if len(labels_to_create) > 0:
                LOG.debug("Labels creation tentative for emails with ids %s." % (group_imap_ids))
                existing_labels = self.src.create_gmail_labels(labels_to_create, existing_labels)
                
            # associate labels with emails
            LOG.critical("Applying labels to the current batch of emails.")
            try:
                LOG.debug("Changing directory. Going into ALLMAIL")
                the_timer = gmvault_utils.Timer()
                the_timer.start()
                self.src.select_folder('ALLMAIL') #go to ALL MAIL to make STORE usable
                LOG.debug("Changed dir. Operation time = %s ms" % (the_timer.elapsed_ms()))
                for label in labels_to_apply.keys():
                    self.src.apply_labels_to(labels_to_apply[label], [label]) 
            except Exception, err:
                LOG.error("Problem when applying labels %s to the following ids: %s" %(label, labels_to_apply[label]), err)
                LOG.error("Problem when applying labels.", err)
                if isinstance(err, imaplib.IMAP4.abort) and str(err).find("=> Gmvault ssl socket error: EOF") >= 0:
                    # if this is a Gmvault SSL Socket error ignore labelling and continue the restore
                    LOG.critical("Ignore labelling")
                    LOG.critical("Disconnecting and reconnecting to restart cleanly.")
                    self.src.reconnect() #reconnect
                else:
                    raise err
            finally:
                self.src.select_folder(folder_def_location) # go back to an empty DIR (Drafts) to be fast
                labels_to_apply = collections_utils.SetMultimap() #reset label to apply
            
            nb_emails_restored += nb_items
                
            #indicate every 10 messages the number of messages left to process
            left_emails = (total_nb_emails_to_restore - nb_emails_restored)
            
            if (left_emails > 0): 
                elapsed = timer.elapsed() #elapsed time in seconds
                LOG.critical("\n== Processed %d emails in %s. %d left to be restored "\
                             "(time estimate %s).==\n" % \
                             (nb_emails_restored, timer.seconds_to_human_time(elapsed), \
                              left_emails, timer.estimate_time_left(nb_emails_restored, elapsed, left_emails)))
            
            # save id every 50 restored emails
            # add the last treated gm_id
            self.save_lastid(self.OP_EMAIL_RESTORE, last_id)
            
        return self.error_report 
        

########NEW FILE########
__FILENAME__ = gmvault_multiprocess
'''
    Gmvault: a tool to backup and restore your gmail account.
    Copyright (C) <2011-2013>  <guillaume Aubert (guillaume dot aubert at gmail do com)>

    This program is free software: you can redistribute it and/or modify
    it under the terms of the GNU Affero General Public License as
    published by the Free Software Foundation, either version 3 of the
    License, or (at your option) any later version.

    This program is distributed in the hope that it will be useful,
    but WITHOUT ANY WARRANTY; without even the implied warranty of
    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
    GNU Affero General Public License for more details.

    You should have received a copy of the GNU Affero General Public License
    along with this program.  If not, see <http://www.gnu.org/licenses/>.

'''
import json
import time
import datetime
import os
import itertools
import imaplib
from multiprocessing import Process, Queue

import log_utils

import collections_utils
import gmvault_utils
import imap_utils
import gmvault_db

LOG = log_utils.LoggerFactory.get_logger('gmvault')

def handle_restore_imap_error(the_exception, gm_id, db_gmail_ids_info, gmvaulter):
    """
       function to handle restore IMAPError in restore functions 
    """
    if isinstance(the_exception, imaplib.IMAP4.abort):
        # if this is a Gmvault SSL Socket error quarantine the email and continue the restore
        if str(the_exception).find("=> Gmvault ssl socket error: EOF") >= 0:
            LOG.critical("Quarantine email with gm id %s from %s. GMAIL IMAP cannot restore it:"\
                         " err={%s}" % (gm_id, db_gmail_ids_info[gm_id], str(the_exception)))
            gmvaulter.gstorer.quarantine_email(gm_id)
            gmvaulter.error_report['emails_in_quarantine'].append(gm_id)
            LOG.critical("Disconnecting and reconnecting to restart cleanly.")
            gmvaulter.src.reconnect() #reconnect
        else:
            raise the_exception
        
    elif isinstance(the_exception, imaplib.IMAP4.error): 
        LOG.error("Catched IMAP Error %s" % (str(the_exception)))
        LOG.exception(the_exception)
        
        #When the email cannot be read from Database because it was empty when returned by gmail imap
        #quarantine it.
        if str(the_exception) == "APPEND command error: BAD ['Invalid Arguments: Unable to parse message']":
            LOG.critical("Quarantine email with gm id %s from %s. GMAIL IMAP cannot restore it:"\
                         " err={%s}" % (gm_id, db_gmail_ids_info[gm_id], str(the_exception)))
            gmvaulter.gstorer.quarantine_email(gm_id)
            gmvaulter.error_report['emails_in_quarantine'].append(gm_id) 
        else:
            raise the_exception
    elif isinstance(the_exception, imap_utils.PushEmailError):
        LOG.error("Catch the following exception %s" % (str(the_exception)))
        LOG.exception(the_exception)
        
        if the_exception.quarantined():
            LOG.critical("Quarantine email with gm id %s from %s. GMAIL IMAP cannot restore it:"\
                         " err={%s}" % (gm_id, db_gmail_ids_info[gm_id], str(the_exception)))
            gmvaulter.gstorer.quarantine_email(gm_id)
            gmvaulter.error_report['emails_in_quarantine'].append(gm_id) 
        else:
            raise the_exception          
    else:
        LOG.error("Catch the following exception %s" % (str(the_exception)))
        LOG.exception(the_exception)
        raise the_exception

def handle_sync_imap_error(the_exception, the_id, error_report, src):
    """
      function to handle IMAPError in gmvault
      type = chat or email
    """    
    if isinstance(the_exception, imaplib.IMAP4.abort):
        # imap abort error 
        # ignore it 
        # will have to do something with these ignored messages
        LOG.critical("Error while fetching message with imap id %s." % (the_id))
        LOG.critical("\n=== Exception traceback ===\n")
        LOG.critical(gmvault_utils.get_exception_traceback())
        LOG.critical("=== End of Exception traceback ===\n")
        try:
            #try to get the gmail_id
            curr = src.fetch(the_id, imap_utils.GIMAPFetcher.GET_GMAIL_ID) 
        except Exception, _: #pylint:disable-msg=W0703
            curr = None
            LOG.critical("Error when trying to get gmail id for message with imap id %s." % (the_id))
            LOG.critical("Disconnect, wait for 20 sec then reconnect.")
            src.disconnect()
            #could not fetch the gm_id so disconnect and sleep
            #sleep 10 sec
            time.sleep(10)
            LOG.critical("Reconnecting ...")
            src.connect()
            
        if curr:
            gmail_id = curr[the_id][imap_utils.GIMAPFetcher.GMAIL_ID]
        else:
            gmail_id = None
            
        #add ignored id
        error_report['cannot_be_fetched'].append((the_id, gmail_id))
        
        LOG.critical("Forced to ignore message with imap id %s, (gmail id %s)." % (the_id, (gmail_id if gmail_id else "cannot be read")))
    elif isinstance(the_exception, imaplib.IMAP4.error):
        # check if this is a cannot be fetched error 
        # I do not like to do string guessing within an exception but I do not have any choice here
        LOG.critical("Error while fetching message with imap id %s." % (the_id))
        LOG.critical("\n=== Exception traceback ===\n")
        LOG.critical(gmvault_utils.get_exception_traceback())
        LOG.critical("=== End of Exception traceback ===\n")
         
        #quarantine emails that have raised an abort error
        if str(the_exception).find("'Some messages could not be FETCHed (Failure)'") >= 0:
            try:
                #try to get the gmail_id
                LOG.critical("One more attempt. Trying to fetch the Gmail ID for %s" % (the_id) )
                curr = src.fetch(the_id, imap_utils.GIMAPFetcher.GET_GMAIL_ID) 
            except Exception, _: #pylint:disable-msg=W0703
                curr = None
            
            if curr:
                gmail_id = curr[the_id][imap_utils.GIMAPFetcher.GMAIL_ID]
            else:
                gmail_id = None
            
            #add ignored id
            error_report['cannot_be_fetched'].append((the_id, gmail_id))
            
            LOG.critical("Ignore message with imap id %s, (gmail id %s)" % (the_id, (gmail_id if gmail_id else "cannot be read")))
        
        else:
            raise the_exception #rethrow error
    else:
        raise the_exception    

class IMAPBatchFetcher(object):
    """
       Fetch IMAP data in batch 
    """
    def __init__(self, src, imap_ids, error_report, request, default_batch_size = 100):
        """
           constructor
        """
        self.src                = src
        self.imap_ids           = imap_ids
        self.def_batch_size     = default_batch_size
        self.request            = request
        self.error_report       = error_report  
        
        self.to_fetch           = list(imap_ids)
    
    def individual_fetch(self, imap_ids):
        """
           Find the imap_id creating the issue
           return the data related to the imap_ids
        """
        new_data = {}
        for the_id in imap_ids:    
            try:
                
                single_data = self.src.fetch(the_id, self.request)
                new_data.update(single_data)
                
            except Exception, error:
                    handle_sync_imap_error(error, the_id, self.error_report, self.src) #do everything in this handler

        return new_data
   
    def __iter__(self):
        return self     
    
    def next(self):
        """
            Return the next batch of elements
        """
        new_data = {}
        batch = self.to_fetch[:self.def_batch_size]
        
        if len(batch) <= 0:
            raise StopIteration
        
        try:
        
            new_data = self.src.fetch(batch, self.request)
            
            self.to_fetch = self.to_fetch[self.def_batch_size:]
            
            return new_data

        except imaplib.IMAP4.error, _:
            new_data = self.individual_fetch(batch) 
    
        return new_data
    
    def reset(self):
        """
           Restart from the beginning
        """
        self.to_fetch = self.imap_ids              
               
class GMVaulter(object):
    """
       Main object operating over gmail
    """ 
    NB_GRP_OF_ITEMS         = 1400
    EMAIL_RESTORE_PROGRESS  = 'email_last_id.restore'
    CHAT_RESTORE_PROGRESS   = 'chat_last_id.restore'
    EMAIL_SYNC_PROGRESS     = 'email_last_id.sync'
    CHAT_SYNC_PROGRESS      = 'chat_last_id.sync'
    
    OP_EMAIL_RESTORE = "EM_RESTORE"
    OP_EMAIL_SYNC    = "EM_SYNC"
    OP_CHAT_RESTORE  = "CH_RESTORE"
    OP_CHAT_SYNC    = "CH_SYNC"
    
    OP_TO_FILENAME = { OP_EMAIL_RESTORE : EMAIL_RESTORE_PROGRESS,
                       OP_EMAIL_SYNC    : EMAIL_SYNC_PROGRESS,
                       OP_CHAT_RESTORE  : CHAT_RESTORE_PROGRESS,
                       OP_CHAT_SYNC     : CHAT_SYNC_PROGRESS
                     }
    
    
    def __init__(self, db_root_dir, host, port, login, credential, read_only_access = True, use_encryption = False): #pylint:disable-msg=R0913
        """
           constructor
        """   
        self.db_root_dir = db_root_dir
        
        #create dir if it doesn't exist
        gmvault_utils.makedirs(self.db_root_dir)
        
        #keep track of login email
        self.login = login
            
        # create source and try to connect
        self.src = imap_utils.GIMAPFetcher(host, port, login, credential, readonly_folder = read_only_access)
        
        self.src.connect()
        
        LOG.debug("Connected")
        
        self.use_encryption = use_encryption
        
        #to report gmail imap problems
        self.error_report = { 'empty' : [] ,
                              'cannot_be_fetched'  : [],
                              'emails_in_quarantine' : [],
                              'reconnections' : 0}
        
        #instantiate gstorer
        self.gstorer =  gmvault_db.GmailStorer(self.db_root_dir, self.use_encryption)
        
        #timer used to mesure time spent in the different values
        self.timer = gmvault_utils.Timer()
        
    @classmethod
    def get_imap_request_btw_2_dates(cls, begin_date, end_date):
        """
           Return the imap request for those 2 dates
        """
        imap_req = 'Since %s Before %s' % (gmvault_utils.datetime2imapdate(begin_date), gmvault_utils.datetime2imapdate(end_date))
        
        return imap_req
    
    def get_operation_report(self):
        """
           Return the error report
        """
        the_str = "\n================================================================\n"\
              "Number of reconnections: %d.\nNumber of emails quarantined: %d.\n" \
              "Number of emails that could not be fetched: %d.\n" \
              "Number of emails that were returned empty by gmail: %d\n================================================================" \
              % (self.error_report['reconnections'], \
                 len(self.error_report['emails_in_quarantine']), \
                 len(self.error_report['cannot_be_fetched']), \
                 len(self.error_report['empty'])
                )
              
        LOG.debug("error_report complete structure = %s" % (self.error_report))
        
        return the_str
        
    def _sync_between(self, begin_date, end_date, storage_dir, compress = True):
        """
           sync between 2 dates
        """
        #create storer
        gstorer = gmvault_db.GmailStorer(storage_dir, self.use_encryption)
        
        #search before the next month
        imap_req = self.get_imap_request_btw_2_dates(begin_date, end_date)
        
        ids = self.src.search(imap_req)
                              
        #loop over all ids, get email store email
        for the_id in ids:
            
            #retrieve email from destination email account
            data      = self.src.fetch(the_id, imap_utils.GIMAPFetcher.GET_ALL_INFO)
            
            file_path = gstorer.bury_email(data[the_id], compress = compress)
            
            LOG.critical("Stored email %d in %s" %(the_id, file_path))
        
    @classmethod
    def _get_next_date(cls, a_current_date, start_month_beginning = False):
        """
           return the next date necessary to build the imap req
        """
        if start_month_beginning:
            dummy_date   = a_current_date.replace(day=1)
        else:
            dummy_date   = a_current_date
            
        # the next date = current date + 1 month
        return dummy_date + datetime.timedelta(days=31)
        
    @classmethod
    def check_email_on_disk(cls, a_gstorer, a_id, a_dir = None):
        """
           Factory method to create the object if it exists
        """
        try:
            a_dir = a_gstorer.get_directory_from_id(a_id, a_dir)
           
            if a_dir:
                return a_gstorer.unbury_metadata(a_id, a_dir) 
            
        except ValueError, json_error:
            LOG.exception("Cannot read file %s. Try to fetch the data again" % ('%s.meta' % (a_id)), json_error )
        
        return None
    
    @classmethod
    def _metadata_needs_update(cls, curr_metadata, new_metadata, chat_metadata = False):
        """
           Needs update
        """
        if curr_metadata[gmvault_db.GmailStorer.ID_K] != new_metadata['X-GM-MSGID']:
            raise Exception("Gmail id has changed for %s" % (curr_metadata['id']))
                
        #check flags   
        prev_set = set(new_metadata['FLAGS'])    
        
        for flag in curr_metadata['flags']:
            if flag not in prev_set:
                return True
            else:
                prev_set.remove(flag)
        
        if len(prev_set) > 0:
            return True
        
        #check labels
        prev_labels = set(new_metadata['X-GM-LABELS'])
        
        if chat_metadata: #add gmvault-chats labels
            prev_labels.add(gmvault_db.GmailStorer.CHAT_GM_LABEL)
            
        
        for label in curr_metadata['labels']:
            if label not in prev_labels:
                return True
            else:
                prev_labels.remove(label)
        
        if len(prev_labels) > 0:
            return True
        
        return False
    
    
    def _check_email_db_ownership(self, ownership_control):
        """
           Check email database ownership.
           If ownership control activated then fail if a new additional owner is added.
           Else if no ownership control allow one more user and save it in the list of owners
           
           Return the number of owner this will be used to activate or not the db clean.
           Activating a db cleaning on a multiownership db would be a catastrophy as it would delete all
           the emails from the others users.
        """
        #check that the gmvault-db is not associated with another user
        db_owners = self.gstorer.get_db_owners()
        if ownership_control:
            if len(db_owners) > 0 and self.login not in db_owners: #db owner should not be different unless bypass activated
                raise Exception("The email database %s is already associated with one or many logins: %s."\
                                " Use option (-m, --multiple-db-owner) if you want to link it with %s" \
                                % (self.db_root_dir, ", ".join(db_owners), self.login))
        else:
            if len(db_owners) == 0:
                LOG.critical("Establish %s as the owner of the Gmvault db %s." % (self.login, self.db_root_dir))  
            elif len(db_owners) > 0 and self.login not in db_owners:
                LOG.critical("The email database %s is hosting emails from %s. It will now also store emails from %s" \
                             % (self.db_root_dir, ", ".join(db_owners), self.login))
                
        #try to save db_owner in the list of owners
        self.gstorer.store_db_owner(self.login)
        
    def _sync_chats(self, imap_req, compress, restart):
        """
           backup the chat messages
        """
        chat_dir = None
        
        timer = gmvault_utils.Timer() #start local timer for chat
        timer.start()
        
        LOG.debug("Before selection")
        if self.src.is_visible('CHATS'):
            chat_dir = self.src.select_folder('CHATS')
        
        LOG.debug("Selection is finished")

        if chat_dir:
            #imap_ids = self.src.search({ 'type': 'imap', 'req': 'ALL' })
            imap_ids = self.src.search(imap_req)
            
            # check if there is a restart
            if restart:
                LOG.critical("Restart mode activated. Need to find information in Gmail, be patient ...")
                imap_ids = self.get_gmails_ids_left_to_sync(self.OP_CHAT_SYNC, imap_ids)
            
            total_nb_chats_to_process = len(imap_ids) # total number of emails to get
            
            LOG.critical("%d chat messages to be fetched." % (total_nb_chats_to_process))
            
            nb_chats_processed = 0
            
            to_fetch = set(imap_ids)
            batch_fetcher = IMAPBatchFetcher(self.src, imap_ids, self.error_report, imap_utils.GIMAPFetcher.GET_ALL_BUT_DATA, \
                                       default_batch_size = gmvault_utils.get_conf_defaults().getint("General","nb_messages_per_batch",500))
        
        
            for new_data in batch_fetcher:
                for the_id in new_data: 
                    if new_data.get(the_id, None):       
                        gid = None
                        
                        LOG.debug("\nProcess imap chat id %s" % ( the_id ))
                        
                        d = new_data[the_id]
                        
                        gid = d[imap_utils.GIMAPFetcher.GMAIL_ID]
                            
                        gid = new_data[the_id][imap_utils.GIMAPFetcher.GMAIL_ID]
                        
                        the_dir      = self.gstorer.get_sub_chats_dir()
                        
                        LOG.critical("Process chat num %d (imap_id:%s) into %s." % (nb_chats_processed, the_id, the_dir))
                    
                        #pass the dir and the ID
                        curr_metadata = GMVaulter.check_email_on_disk( self.gstorer , \
                                                                       new_data[the_id][imap_utils.GIMAPFetcher.GMAIL_ID], \
                                                                       the_dir)
                        
                        #if on disk check that the data is not different
                        if curr_metadata:
                            
                            if self._metadata_needs_update(curr_metadata, new_data[the_id], chat_metadata = True):
                                
                                LOG.debug("Chat with imap id %s and gmail id %s has changed. Updated it." % (the_id, gid))
                                
                                #restore everything at the moment
                                gid  = self.gstorer.bury_chat_metadata(new_data[the_id], local_dir = the_dir)
                                
                                #update local index id gid => index per directory to be thought out
                            else:
                                LOG.debug("The metadata for chat %s already exists and is identical to the one on GMail." % (gid))
                        else:  
                            try:
                                #get the data
                                email_data = self.src.fetch(the_id, imap_utils.GIMAPFetcher.GET_DATA_ONLY )
                                
                                new_data[the_id][imap_utils.GIMAPFetcher.EMAIL_BODY] = email_data[the_id][imap_utils.GIMAPFetcher.EMAIL_BODY]
                                
                                # store data on disk within year month dir 
                                gid  = self.gstorer.bury_chat(new_data[the_id], local_dir = the_dir, compress = compress)
                                
                                #update local index id gid => index per directory to be thought out
                                LOG.debug("Create and store chat with imap id %s, gmail id %s." % (the_id, gid))   
                            except Exception, error:
                                handle_sync_imap_error(error, the_id, self.error_report, self.src) #do everything in this handler    
                    
                        nb_chats_processed += 1    
                        
                        #indicate every 50 messages the number of messages left to process
                        left_emails = (total_nb_chats_to_process - nb_chats_processed)
                        
                        if (nb_chats_processed % 50) == 0 and (left_emails > 0):
                            elapsed = timer.elapsed() #elapsed time in seconds
                            LOG.critical("\n== Processed %d emails in %s. %d left to be stored (time estimate %s).==\n" % \
                                         (nb_chats_processed,  timer.seconds_to_human_time(elapsed), \
                                          left_emails, \
                                          timer.estimate_time_left(nb_chats_processed, elapsed, left_emails)))
                        
                        # save id every 10 restored emails
                        if (nb_chats_processed % 10) == 0:
                            if gid:
                                self.save_lastid(self.OP_CHAT_SYNC, gid)
                    else:
                        LOG.info("Could not process imap with id %s. Ignore it\n")
                        self.error_report['empty'].append((the_id, None)) 
                    
                to_fetch -= set(new_data.keys()) #remove all found keys from to_fetch set
                
            for the_id in to_fetch:
                # case when gmail IMAP server returns OK without any data whatsoever
                # eg. imap uid 142221L ignore it
                LOG.info("Could not process chat with id %s. Ignore it\n")
                self.error_report['empty_chats'].append((the_id, None))

        else:
            imap_ids = []    
        
        LOG.critical("\nChats synchronisation operation performed in %s.\n" % (timer.seconds_to_human_time(timer.elapsed())))
        return imap_ids

    
    def _sync_emails(self, imap_req, compress, restart):
        """
           First part of the double pass strategy: 
           - create and update emails in db
           
        """    
        timer = gmvault_utils.Timer()
        timer.start()
           
        #select all mail folder using the constant name defined in GIMAPFetcher
        self.src.select_folder('ALLMAIL')
        
        # get all imap ids in All Mail
        imap_ids = self.src.search(imap_req)
        
        # check if there is a restart
        if restart:
            LOG.critical("Restart mode activated for emails. Need to find information in Gmail, be patient ...")
            imap_ids = self.get_gmails_ids_left_to_sync(self.OP_EMAIL_SYNC, imap_ids)
        
        total_nb_emails_to_process = len(imap_ids) # total number of emails to get
        
        LOG.critical("%d emails to be fetched." % (total_nb_emails_to_process))
        
        nb_emails_processed = 0
        
        to_fetch = set(imap_ids)
        batch_fetcher = IMAPBatchFetcher(self.src, imap_ids, self.error_report, imap_utils.GIMAPFetcher.GET_ALL_BUT_DATA, \
                                   default_batch_size = gmvault_utils.get_conf_defaults().getint("General","nb_messages_per_batch",500))
        
        #LAST Thing to do remove all found ids from imap_ids and if ids left add missing in report
        for new_data in batch_fetcher:            
            for the_id in new_data:
                if new_data.get(the_id, None):
                    LOG.debug("\nProcess imap id %s" % ( the_id ))
                        
                    gid = new_data[the_id][imap_utils.GIMAPFetcher.GMAIL_ID]
                    
                    the_dir      = gmvault_utils.get_ym_from_datetime(new_data[the_id][imap_utils.GIMAPFetcher.IMAP_INTERNALDATE])
                    
                    LOG.critical("Process email num %d (imap_id:%s) from %s." % (nb_emails_processed, the_id, the_dir))
                
                    #pass the dir and the ID
                    curr_metadata = GMVaulter.check_email_on_disk( self.gstorer , \
                                                                   new_data[the_id][imap_utils.GIMAPFetcher.GMAIL_ID], \
                                                                   the_dir)
                    
                    #if on disk check that the data is not different
                    if curr_metadata:
                        
                        LOG.debug("metadata for %s already exists. Check if different." % (gid))
                        
                        if self._metadata_needs_update(curr_metadata, new_data[the_id]):
                            
                            LOG.debug("Chat with imap id %s and gmail id %s has changed. Updated it." % (the_id, gid))
                            
                            #restore everything at the moment
                            gid  = self.gstorer.bury_metadata(new_data[the_id], local_dir = the_dir)
                            
                            #update local index id gid => index per directory to be thought out
                        else:
                            LOG.debug("On disk metadata for %s is up to date." % (gid))
                    else:  
                        try:
                            #get the data
                            LOG.debug("Get Data for %s." % (gid))
                            email_data = self.src.fetch(the_id, imap_utils.GIMAPFetcher.GET_DATA_ONLY )
                            
                            new_data[the_id][imap_utils.GIMAPFetcher.EMAIL_BODY] = email_data[the_id][imap_utils.GIMAPFetcher.EMAIL_BODY]
                            
                            # store data on disk within year month dir 
                            gid  = self.gstorer.bury_email(new_data[the_id], local_dir = the_dir, compress = compress)
                            
                            #update local index id gid => index per directory to be thought out
                            LOG.debug("Create and store email with imap id %s, gmail id %s." % (the_id, gid))   
                        except Exception, error:
                            handle_sync_imap_error(error, the_id, self.error_report, self.src) #do everything in this handler    
                    
                    nb_emails_processed += 1
                    
                    #indicate every 50 messages the number of messages left to process
                    left_emails = (total_nb_emails_to_process - nb_emails_processed)
                    
                    if (nb_emails_processed % 50) == 0 and (left_emails > 0):
                        elapsed = timer.elapsed() #elapsed time in seconds
                        LOG.critical("\n== Processed %d emails in %s. %d left to be stored (time estimate %s).==\n" % \
                                     (nb_emails_processed,  \
                                      timer.seconds_to_human_time(elapsed), left_emails, \
                                      timer.estimate_time_left(nb_emails_processed, elapsed, left_emails)))
                    
                    # save id every 10 restored emails
                    if (nb_emails_processed % 10) == 0:
                        if gid:
                            self.save_lastid(self.OP_EMAIL_SYNC, gid)
                else:
                    LOG.info("Could not process imap with id %s. Ignore it\n")
                    self.error_report['empty'].append((the_id, gid if gid else None))
                    
            to_fetch -= set(new_data.keys()) #remove all found keys from to_fetch set
                
        for the_id in to_fetch:
            # case when gmail IMAP server returns OK without any data whatsoever
            # eg. imap uid 142221L ignore it
            LOG.info("Could not process imap with id %s. Ignore it\n")
            self.error_report['empty'].append((the_id, None))
        
        LOG.critical("\nEmails synchronisation operation performed in %s.\n" % (timer.seconds_to_human_time(timer.elapsed())))
        
        return imap_ids
    
    def sync(self, imap_req = imap_utils.GIMAPFetcher.IMAP_ALL, compress_on_disk = True, db_cleaning = False, ownership_checking = True, \
            restart = False, emails_only = False, chats_only = False):
        """
           sync mode 
        """
        #check ownership to have one email per db unless user wants different
        #save the owner if new
        self._check_email_db_ownership(ownership_checking)
                
        if not compress_on_disk:
            LOG.critical("Disable compression when storing emails.")
            
        if self.use_encryption:
            LOG.critical("Encryption activated. All emails will be encrypted before to be stored.")
            LOG.critical("Please take care of the encryption key stored in (%s) or all"\
                         " your stored emails will become unreadable." % (gmvault_db.GmailStorer.get_encryption_key_path(self.db_root_dir)))
        
        self.timer.start() #start syncing emails
        
        if not chats_only:
            # backup emails
            LOG.critical("Start emails synchronization.\n")
            self._sync_emails(imap_req, compress = compress_on_disk, restart = restart)
        else:
            LOG.critical("Skip emails synchronization.\n")
        
        if not emails_only:
            # backup chats
            LOG.critical("Start chats synchronization.\n")
            self._sync_chats(imap_req, compress = compress_on_disk, restart = restart)
        else:
            LOG.critical("\nSkip chats synchronization.\n")
        
        #delete supress emails from DB since last sync
        if len(self.gstorer.get_db_owners()) <= 1:
            self.check_clean_db(db_cleaning)
        else:
            LOG.critical("Deactivate database cleaning on a multi-owners Gmvault db.")
        
        LOG.critical("Synchronisation operation performed in %s.\n" \
                     % (self.timer.seconds_to_human_time(self.timer.elapsed())))
        
        #update number of reconnections
        self.error_report["reconnections"] = self.src.total_nb_reconns
        
        return self.error_report

    
    def _delete_sync(self, imap_ids, db_gmail_ids, db_gmail_ids_info, msg_type):
        """
           Delete emails from the database if necessary
           imap_ids      : all remote imap_ids to check
           db_gmail_ids_info : info read from metadata
           msg_type : email or chat
        """
        
        # optimize nb of items
        nb_items = self.NB_GRP_OF_ITEMS if len(imap_ids) >= self.NB_GRP_OF_ITEMS else len(imap_ids)
        
        LOG.critical("Call Gmail to check the stored %ss against the Gmail %ss ids and see which ones have been deleted.\n\n"\
                     "This might take a few minutes ...\n" % (msg_type, msg_type)) 
         
        #calculate the list elements to delete
        #query nb_items items in one query to minimise number of imap queries
        for group_imap_id in itertools.izip_longest(fillvalue=None, *[iter(imap_ids)]*nb_items):
            
            # if None in list remove it
            if None in group_imap_id: 
                group_imap_id = [ im_id for im_id in group_imap_id if im_id != None ]
            
            #LOG.debug("Interrogate Gmail Server for %s" % (str(group_imap_id)))
            data = self.src.fetch(group_imap_id, imap_utils.GIMAPFetcher.GET_GMAIL_ID)
            
            # syntax for 2.7 set comprehension { data[key][imap_utils.GIMAPFetcher.GMAIL_ID] for key in data }
            # need to create a list for 2.6
            db_gmail_ids.difference_update([data[key][imap_utils.GIMAPFetcher.GMAIL_ID] for key in data ])
            
            if len(db_gmail_ids) == 0:
                break
        
        LOG.critical("Will delete %s %s(s) from gmvault db.\n" % (len(db_gmail_ids), msg_type) )
        for gm_id in db_gmail_ids:
            LOG.critical("gm_id %s not in the Gmail server. Delete it." % (gm_id))
            self.gstorer.delete_emails([(gm_id, db_gmail_ids_info[gm_id])], msg_type)
        
    def get_gmails_ids_left_to_sync(self, op_type, imap_ids):
        """
           Get the ids that still needs to be sync
           Return a list of ids
        """
        
        filename = self.OP_TO_FILENAME.get(op_type, None)
        
        if not filename:
            raise Exception("Bad Operation (%s) in save_last_id. This should not happen, send the error to the software developers." % (op_type))
        
        filepath = '%s/%s_%s' % (self.gstorer.get_info_dir(), self.login, filename)
        
        if not os.path.exists(filepath):
            LOG.critical("last_id.sync file %s doesn't exist.\nSync the full list of backed up emails." %(filepath))
            return imap_ids
        
        json_obj = json.load(open(filepath, 'r'))
        
        last_id = json_obj['last_id']
        
        last_id_index = -1
        
        new_gmail_ids = imap_ids
        
        try:
            #get imap_id from stored gmail_id
            dummy = self.src.search({'type':'imap', 'req':'X-GM-MSGID %s' % (last_id)})
            
            imap_id = dummy[0]
            last_id_index = imap_ids.index(imap_id)
            LOG.critical("Restart from gmail id %s (imap id %s)." % (last_id, imap_id))
            new_gmail_ids = imap_ids[last_id_index:]   
        except Exception, _: #ignore any exception and try to get all ids in case of problems. pylint:disable=W0703
            #element not in keys return current set of keys
            LOG.critical("Error: Cannot restore from last restore gmail id. It is not in Gmail."\
                         " Sync the complete list of gmail ids requested from Gmail.")
        
        return new_gmail_ids
        
    def check_clean_db(self, db_cleaning):
        """
           Check and clean the database (remove file that are not anymore in Gmail
        """
        owners = self.gstorer.get_db_owners()
        if not db_cleaning: #decouple the 2 conditions for activating cleaning
            LOG.debug("db_cleaning is off so ignore removing deleted emails from disk.")
            return
        elif len(owners) > 1:
            LOG.critical("Gmvault db hosting emails from different accounts: %s.\nCannot activate database cleaning." % (", ".join(owners)))
            return
        else:
            LOG.critical("Look for emails/chats that are in the Gmvault db but not in Gmail servers anymore.\n")
            
            #get gmail_ids from db
            LOG.critical("Read all gmail ids from the Gmvault db. It might take a bit of time ...\n")
            
            timer = gmvault_utils.Timer() # needed for enhancing the user information
            timer.start()
            
            db_gmail_ids_info = self.gstorer.get_all_existing_gmail_ids()
        
            LOG.critical("Found %s email(s) in the Gmvault db.\n" % (len(db_gmail_ids_info)) )
        
            #create a set of keys
            db_gmail_ids = set(db_gmail_ids_info.keys())
            
            # get all imap ids in All Mail
            self.src.select_folder('ALLMAIL') #go to all mail
            imap_ids = self.src.search(imap_utils.GIMAPFetcher.IMAP_ALL) #search all
            
            LOG.debug("Got %s emails imap_id(s) from the Gmail Server." % (len(imap_ids)))
            
            #delete supress emails from DB since last sync
            self._delete_sync(imap_ids, db_gmail_ids, db_gmail_ids_info, 'email')
            
            # get all chats ids
            if self.src.is_visible('CHATS'):
            
                db_gmail_ids_info = self.gstorer.get_all_chats_gmail_ids()
                
                LOG.critical("Found %s chat(s) in the Gmvault db.\n" % (len(db_gmail_ids_info)) )
                
                self.src.select_folder('CHATS') #go to chats
                chat_ids = self.src.search(imap_utils.GIMAPFetcher.IMAP_ALL)
                
                db_chat_ids = set(db_gmail_ids_info.keys())
                
                LOG.debug("Got %s chat imap_ids from the Gmail Server." % (len(chat_ids)))
            
                #delete supress emails from DB since last sync
                self._delete_sync(chat_ids, db_chat_ids, db_gmail_ids_info , 'chat')
            else:
                LOG.critical("Chats IMAP Directory not visible on Gmail. Ignore deletion of chats.")
                
            
            LOG.critical("\nDeletion checkup done in %s." % (timer.elapsed_human_time()))
            
    
    def remote_sync(self):
        """
           Sync with a remote source (IMAP mirror or cloud storage area)
        """
        #sync remotely 
        pass
        
    
    def save_lastid(self, op_type, gm_id):
        """
           Save the passed gmid in last_id.restore
           For the moment reopen the file every time
        """
        
        filename = self.OP_TO_FILENAME.get(op_type, None)
        
        if not filename:
            raise Exception("Bad Operation (%s) in save_last_id. This should not happen, send the error to the software developers." % (op_type))
        
        #filepath = '%s/%s_%s' % (gmvault_utils.get_home_dir_path(), self.login, filename)  
        filepath = '%s/%s_%s' % (self.gstorer.get_info_dir(), self.login, filename)  
        
        the_fd = open(filepath, 'w')
        
        json.dump({
                    'last_id' : gm_id  
                  }, the_fd)
        
        the_fd.close()
        
    def get_gmails_ids_left_to_restore(self, op_type, db_gmail_ids_info):
        """
           Get the ids that still needs to be restored
           Return a dict key = gm_id, val = directory
        """
        filename = self.OP_TO_FILENAME.get(op_type, None)
        
        if not filename:
            raise Exception("Bad Operation (%s) in save_last_id. This should not happen, send the error to the software developers." % (op_type))
        
        
        #filepath = '%s/%s_%s' % (gmvault_utils.get_home_dir_path(), self.login, filename)
        filepath = '%s/%s_%s' % (self.gstorer.get_info_dir(), self.login, filename)
        
        if not os.path.exists(filepath):
            LOG.critical("last_id restore file %s doesn't exist.\nRestore the full list of backed up emails." %(filepath))
            return db_gmail_ids_info
        
        json_obj = json.load(open(filepath, 'r'))
        
        last_id = json_obj['last_id']
        
        last_id_index = -1
        try:
            keys = db_gmail_ids_info.keys()
            last_id_index = keys.index(last_id)
            LOG.critical("Restart from gmail id %s." % (last_id))
        except ValueError, _:
            #element not in keys return current set of keys
            LOG.error("Cannot restore from last restore gmail id. It is not in the disk database.")
        
        new_gmail_ids_info = collections_utils.OrderedDict()
        if last_id_index != -1:
            for key in db_gmail_ids_info.keys()[last_id_index+1:]:
                new_gmail_ids_info[key] =  db_gmail_ids_info[key]
        else:
            new_gmail_ids_info = db_gmail_ids_info    
            
        return new_gmail_ids_info 
           
    def restore(self, pivot_dir = None, extra_labels = [], restart = False, emails_only = False, chats_only = False): #pylint:disable=W0102
        """
           Restore emails in a gmail account
        """
        self.timer.start() #start restoring
        
        #self.src.select_folder('ALLMAIL') #insure that Gmvault is in ALLMAIL
        
        if not chats_only:
            # backup emails
            LOG.critical("Start emails restoration.\n")
            
            if pivot_dir:
                LOG.critical("Quick mode activated. Will only restore all emails since %s.\n" % (pivot_dir))
            
            self.restore_emails(pivot_dir, extra_labels, restart)
        else:
            LOG.critical("Skip emails restoration.\n")
        
        if not emails_only:
            # backup chats
            LOG.critical("Start chats restoration.\n")
            self.restore_chats(extra_labels, restart)
        else:
            LOG.critical("Skip chats restoration.\n")
        
        LOG.critical("Restore operation performed in %s.\n" \
                     % (self.timer.seconds_to_human_time(self.timer.elapsed())))
        
        #update number of reconnections
        self.error_report["reconnections"] = self.src.total_nb_reconns
        
        return self.error_report
       
    def common_restore(self, the_type, db_gmail_ids_info, extra_labels = [], restart = False): #pylint:disable=W0102
        """
           common_restore 
        """
        if the_type == "chats":
            msg = "chats"
            op  = self.OP_CHAT_RESTORE
        elif the_type == "emails":
            msg = "emails"
            op  = self.OP_EMAIL_RESTORE
        
        LOG.critical("Restore %s in gmail account %s." % (msg, self.login) ) 
        
        LOG.critical("Read %s info from %s gmvault-db." % (msg, self.db_root_dir))
        
        LOG.critical("Total number of %s to restore %s." % (msg, len(db_gmail_ids_info.keys())))
        
        if restart:
            db_gmail_ids_info = self.get_gmails_ids_left_to_restore(op, db_gmail_ids_info)
        
        total_nb_emails_to_restore = len(db_gmail_ids_info)
        LOG.critical("Got all %s id left to restore. Still %s %s to do.\n" % (msg, total_nb_emails_to_restore, msg) )
        
        existing_labels = set() #set of existing labels to not call create_gmail_labels all the time
        nb_emails_restored = 0 #to count nb of emails restored
        timer = gmvault_utils.Timer() # needed for enhancing the user information
        timer.start()
        
        for gm_id in db_gmail_ids_info:
            
            LOG.critical("Restore %s with id %s." % (msg, gm_id))
            
            email_meta, email_data = self.unbury_email(gm_id)
            
            LOG.debug("Unburied %s with id %s." % (msg, gm_id))
            
            #labels for this email => real_labels U extra_labels
            labels = set(email_meta[self.gstorer.LABELS_K])
            labels = labels.union(extra_labels)
            
            # get list of labels to create 
            labels_to_create = [ label for label in labels if label not in existing_labels]
            
            #create the non existing labels
            if len(labels_to_create) > 0:
                LOG.debug("Labels creation tentative for %s with id %s." % (msg, gm_id))
                existing_labels = self.src.create_gmail_labels(labels_to_create, existing_labels)
            
            try:
                #restore email
                self.src.push_email(email_data, \
                                    email_meta[self.gstorer.FLAGS_K] , \
                                    email_meta[self.gstorer.INT_DATE_K], \
                                    labels)
                
                LOG.debug("Pushed %s with id %s." % (msg, gm_id))
                
                nb_emails_restored += 1
                
                #indicate every 10 messages the number of messages left to process
                left_emails = (total_nb_emails_to_restore - nb_emails_restored)
                
                if (nb_emails_restored % 50) == 0 and (left_emails > 0): 
                    elapsed = timer.elapsed() #elapsed time in seconds
                    LOG.critical("\n== Processed %d %s in %s. %d left to be restored (time estimate %s).==\n" % \
                                 (nb_emails_restored, msg, timer.seconds_to_human_time(elapsed), \
                                  left_emails, timer.estimate_time_left(nb_emails_restored, elapsed, left_emails)))
                
                # save id every 20 restored emails
                if (nb_emails_restored % 10) == 0:
                    self.save_lastid(self.OP_CHAT_RESTORE, gm_id)
                    
            except imaplib.IMAP4.abort, abort:
                
                # if this is a Gmvault SSL Socket error quarantine the email and continue the restore
                if str(abort).find("=> Gmvault ssl socket error: EOF") >= 0:
                    LOG.critical("Quarantine %s with gm id %s from %s. "\
                                 "GMAIL IMAP cannot restore it: err={%s}" % (msg, gm_id, db_gmail_ids_info[gm_id], str(abort)))
                    self.gstorer.quarantine_email(gm_id)
                    self.error_report['emails_in_quarantine'].append(gm_id)
                    LOG.critical("Disconnecting and reconnecting to restart cleanly.")
                    self.src.reconnect() #reconnect
                else:
                    raise abort
        
            except imaplib.IMAP4.error, err:
                
                LOG.error("Catched IMAP Error %s" % (str(err)))
                LOG.exception(err)
                
                #When the email cannot be read from Database because it was empty when returned by gmail imap
                #quarantine it.
                if str(err) == "APPEND command error: BAD ['Invalid Arguments: Unable to parse message']":
                    LOG.critical("Quarantine %s with gm id %s from %s. GMAIL IMAP cannot restore it:"\
                                 " err={%s}" % (msg, gm_id, db_gmail_ids_info[gm_id], str(err)))
                    self.gstorer.quarantine_email(gm_id)
                    self.error_report['emails_in_quarantine'].append(gm_id) 
                else:
                    raise err
            except imap_utils.PushEmailError, p_err:
                LOG.error("Catch the following exception %s" % (str(p_err)))
                LOG.exception(p_err)
                
                if p_err.quarantined():
                    LOG.critical("Quarantine %s with gm id %s from %s. GMAIL IMAP cannot restore it:"\
                                 " err={%s}" % (msg, gm_id, db_gmail_ids_info[gm_id], str(p_err)))
                    self.gstorer.quarantine_email(gm_id)
                    self.error_report['emails_in_quarantine'].append(gm_id) 
                else:
                    raise p_err          
            except Exception, err:
                LOG.error("Catch the following exception %s" % (str(err)))
                LOG.exception(err)
                raise err
            
            
        return self.error_report 
        
    def old_restore_chats(self, extra_labels = [], restart = False): #pylint:disable=W0102
        """
           restore chats
        """
        LOG.critical("Restore chats in gmail account %s." % (self.login) ) 
                
        LOG.critical("Read chats info from %s gmvault-db." % (self.db_root_dir))
        
        #for the restore (save last_restored_id in .gmvault/last_restored_id
        
        #get gmail_ids from db
        db_gmail_ids_info = self.gstorer.get_all_chats_gmail_ids()
        
        LOG.critical("Total number of chats to restore %s." % (len(db_gmail_ids_info.keys())))
        
        if restart:
            db_gmail_ids_info = self.get_gmails_ids_left_to_restore(self.OP_CHAT_RESTORE, db_gmail_ids_info)
        
        total_nb_emails_to_restore = len(db_gmail_ids_info)
        LOG.critical("Got all chats id left to restore. Still %s chats to do.\n" % (total_nb_emails_to_restore) )
        
        existing_labels = set() #set of existing labels to not call create_gmail_labels all the time
        nb_emails_restored = 0 #to count nb of emails restored
        timer = gmvault_utils.Timer() # needed for enhancing the user information
        timer.start()
        
        for gm_id in db_gmail_ids_info:
            
            LOG.critical("Restore chat with id %s." % (gm_id))
            
            email_meta, email_data = self.gstorer.unbury_email(gm_id)
            
            LOG.debug("Unburied chat with id %s." % (gm_id))
            
            #labels for this email => real_labels U extra_labels
            labels = set(email_meta[self.gstorer.LABELS_K])
            labels = labels.union(extra_labels)
            
            # get list of labels to create 
            labels_to_create = [ label for label in labels if label not in existing_labels]
            
            #create the non existing labels
            if len(labels_to_create) > 0:
                LOG.debug("Labels creation tentative for chat with id %s." % (gm_id))
                existing_labels = self.src.create_gmail_labels(labels_to_create, existing_labels)
            
            try:
                #restore email
                self.src.push_email(email_data, \
                                    email_meta[self.gstorer.FLAGS_K] , \
                                    email_meta[self.gstorer.INT_DATE_K], \
                                    labels)
                
                LOG.debug("Pushed chat with id %s." % (gm_id))
                
                nb_emails_restored += 1
                
                #indicate every 10 messages the number of messages left to process
                left_emails = (total_nb_emails_to_restore - nb_emails_restored)
                
                if (nb_emails_restored % 50) == 0 and (left_emails > 0): 
                    elapsed = timer.elapsed() #elapsed time in seconds
                    LOG.critical("\n== Processed %d chats in %s. %d left to be restored (time estimate %s).==\n" % \
                                 (nb_emails_restored, timer.seconds_to_human_time(elapsed), \
                                  left_emails, timer.estimate_time_left(nb_emails_restored, elapsed, left_emails)))
                
                # save id every 20 restored emails
                if (nb_emails_restored % 10) == 0:
                    self.save_lastid(self.OP_CHAT_RESTORE, gm_id)
                    
            except imaplib.IMAP4.abort, abort:
                
                # if this is a Gmvault SSL Socket error quarantine the email and continue the restore
                if str(abort).find("=> Gmvault ssl socket error: EOF") >= 0:
                    LOG.critical("Quarantine email with gm id %s from %s. "\
                                 "GMAIL IMAP cannot restore it: err={%s}" % (gm_id, db_gmail_ids_info[gm_id], str(abort)))
                    self.gstorer.quarantine_email(gm_id)
                    self.error_report['emails_in_quarantine'].append(gm_id)
                    LOG.critical("Disconnecting and reconnecting to restart cleanly.")
                    self.src.reconnect() #reconnect
                else:
                    raise abort
        
            except imaplib.IMAP4.error, err:
                
                LOG.error("Catched IMAP Error %s" % (str(err)))
                LOG.exception(err)
                
                #When the email cannot be read from Database because it was empty when returned by gmail imap
                #quarantine it.
                if str(err) == "APPEND command error: BAD ['Invalid Arguments: Unable to parse message']":
                    LOG.critical("Quarantine email with gm id %s from %s. GMAIL IMAP cannot restore it:"\
                                 " err={%s}" % (gm_id, db_gmail_ids_info[gm_id], str(err)))
                    self.gstorer.quarantine_email(gm_id)
                    self.error_report['emails_in_quarantine'].append(gm_id) 
                else:
                    raise err
            except imap_utils.PushEmailError, p_err:
                LOG.error("Catch the following exception %s" % (str(p_err)))
                LOG.exception(p_err)
                
                if p_err.quarantined():
                    LOG.critical("Quarantine email with gm id %s from %s. GMAIL IMAP cannot restore it:"\
                                 " err={%s}" % (gm_id, db_gmail_ids_info[gm_id], str(p_err)))
                    self.gstorer.quarantine_email(gm_id)
                    self.error_report['emails_in_quarantine'].append(gm_id) 
                else:
                    raise p_err          
            except Exception, err:
                LOG.error("Catch the following exception %s" % (str(err)))
                LOG.exception(err)
                raise err
            
            
        return self.error_report
    
    
    def restore_chats(self, extra_labels = [], restart = False): #pylint:disable=W0102
        """
           restore chats
        """
        LOG.critical("Restore chats in gmail account %s." % (self.login) ) 
                
        LOG.critical("Read chats info from %s gmvault-db." % (self.db_root_dir))
        
        #for the restore (save last_restored_id in .gmvault/last_restored_id
        
        #get gmail_ids from db
        db_gmail_ids_info = self.gstorer.get_all_chats_gmail_ids()
        
        LOG.critical("Total number of chats to restore %s." % (len(db_gmail_ids_info.keys())))
        
        if restart:
            db_gmail_ids_info = self.get_gmails_ids_left_to_restore(self.OP_CHAT_RESTORE, db_gmail_ids_info)
        
        total_nb_emails_to_restore = len(db_gmail_ids_info)
        LOG.critical("Got all chats id left to restore. Still %s chats to do.\n" % (total_nb_emails_to_restore) )
        
        existing_labels     = set() #set of existing labels to not call create_gmail_labels all the time
        nb_emails_restored  = 0  #to count nb of emails restored
        labels_to_apply     = collections_utils.SetMultimap()

        #get all mail folder name
        all_mail_name = self.src.get_folder_name("ALLMAIL")
        
        # go to DRAFTS folder because if you are in ALL MAIL when uploading emails it is very slow
        folder_def_location = gmvault_utils.get_conf_defaults().get("General","restore_default_location", "DRAFTS")
        self.src.select_folder(folder_def_location)
        
        timer = gmvault_utils.Timer() # local timer for restore emails
        timer.start()
        
        nb_items = gmvault_utils.get_conf_defaults().get_int("General","nb_messages_per_restore_batch", 100) 
        
        for group_imap_ids in itertools.izip_longest(fillvalue=None, *[iter(db_gmail_ids_info)]*nb_items): 

            last_id = group_imap_ids[-1] #will be used to save the last id
            #remove all None elements from group_imap_ids
            group_imap_ids = itertools.ifilter(lambda x: x != None, group_imap_ids)
           
            labels_to_create    = set() #create label set
            labels_to_create.update(extra_labels) # add extra labels to applied to all emails
            
            LOG.critical("Pushing the chats content of the current batch of %d emails.\n" % (nb_items))
            
            # unbury the metadata for all these emails
            for gm_id in group_imap_ids:    
                email_meta, email_data = self.gstorer.unbury_email(gm_id)
                
                LOG.critical("Pushing chat content with id %s." % (gm_id))
                LOG.debug("Subject = %s." % (email_meta[self.gstorer.SUBJECT_K]))
                try:
                    # push data in gmail account and get uids
                    imap_id = self.src.push_data(all_mail_name, email_data, \
                                    email_meta[self.gstorer.FLAGS_K] , \
                                    email_meta[self.gstorer.INT_DATE_K] )      
                
                    #labels for this email => real_labels U extra_labels
                    labels = set(email_meta[self.gstorer.LABELS_K])
                    
                    # add in the labels_to_create struct
                    for label in labels:
                        LOG.debug("label = %s\n" % (label))
                        labels_to_apply[str(label)] = imap_id
            
                    # get list of labels to create (do a union with labels to create)
                    labels_to_create.update([ label for label in labels if label not in existing_labels])                  
                
                except Exception, err:
                    handle_restore_imap_error(err, gm_id, db_gmail_ids_info, self)

            #create the non existing labels and update existing labels
            if len(labels_to_create) > 0:
                LOG.debug("Labels creation tentative for chat with id %s." % (gm_id))
                existing_labels = self.src.create_gmail_labels(labels_to_create, existing_labels)
                
            # associate labels with emails
            LOG.critical("Applying labels to the current batch of %d emails" % (nb_items))
            try:
                LOG.debug("Changing directory. Going into ALLMAIL")
                self.src.select_folder('ALLMAIL') #go to ALL MAIL to make STORE usable
                for label in labels_to_apply.keys():
                    self.src.apply_labels_to(labels_to_apply[label], [label]) 
            except Exception, err:
                LOG.error("Problem when applying labels %s to the following ids: %s" %(label, labels_to_apply[label]), err)
                if isinstance(err, imaplib.IMAP4.abort) and str(err).find("=> Gmvault ssl socket error: EOF") >= 0:
                    # if this is a Gmvault SSL Socket error quarantine the email and continue the restore
                    LOG.critical("Quarantine email with gm id %s from %s. GMAIL IMAP cannot restore it:"\
                         " err={%s}" % (gm_id, db_gmail_ids_info[gm_id], str(err)))
                    self.gstorer.quarantine_email(gm_id)
                    self.error_report['emails_in_quarantine'].append(gm_id)
                    LOG.critical("Disconnecting and reconnecting to restart cleanly.")
                    self.src.reconnect() #reconnect
                else:
                    raise err
            finally:
                self.src.select_folder(folder_def_location) # go back to an empty DIR (Drafts) to be fast
                labels_to_apply = collections_utils.SetMultimap() #reset label to apply
            
            nb_emails_restored += nb_items
                
            #indicate every 10 messages the number of messages left to process
            left_emails = (total_nb_emails_to_restore - nb_emails_restored)
            
            if (left_emails > 0): 
                elapsed = timer.elapsed() #elapsed time in seconds
                LOG.critical("\n== Processed %d chats in %s. %d left to be restored "\
                             "(time estimate %s).==\n" % \
                             (nb_emails_restored, timer.seconds_to_human_time(elapsed), \
                              left_emails, timer.estimate_time_left(nb_emails_restored, elapsed, left_emails)))
            
            # save id every nb_items restored emails
            # add the last treated gm_id
            self.save_lastid(self.OP_EMAIL_RESTORE, last_id)
            
        return self.error_report 
                    
    def restore_emails(self, pivot_dir = None, extra_labels = [], restart = False):
        """
           restore emails in a gmail account using batching to group restore
           If you are not in "All Mail" Folder, it is extremely fast to push emails.
           But it is not possible to reapply labels if you are not in All Mail because the uid which is returned
           is dependant on the folder. On the other hand, you can restore labels in batch which would help gaining lots of time.
           The idea is to get a batch of 50 emails and push them all in the mailbox one by one and get the uid for each of them.
           Then create a dict of labels => uid_list and for each label send a unique store command after having changed dir
        """
        LOG.critical("Restore emails in gmail account %s." % (self.login) ) 
        
        LOG.critical("Read email info from %s gmvault-db." % (self.db_root_dir))
        
        #get gmail_ids from db
        db_gmail_ids_info = self.gstorer.get_all_existing_gmail_ids(pivot_dir)
        
        LOG.critical("Total number of elements to restore %s." % (len(db_gmail_ids_info.keys())))
        
        if restart:
            db_gmail_ids_info = self.get_gmails_ids_left_to_restore(self.OP_EMAIL_RESTORE, db_gmail_ids_info)
        
        total_nb_emails_to_restore = len(db_gmail_ids_info)
        
        LOG.critical("Got all emails id left to restore. Still %s emails to do.\n" % (total_nb_emails_to_restore) )
        
        existing_labels     = set() #set of existing labels to not call create_gmail_labels all the time
        nb_emails_restored  = 0  #to count nb of emails restored
        labels_to_apply     = collections_utils.SetMultimap()

        #get all mail folder name
        all_mail_name = self.src.get_folder_name("ALLMAIL")
        
        # go to DRAFTS folder because if you are in ALL MAIL when uploading emails it is very slow
        folder_def_location = gmvault_utils.get_conf_defaults().get("General","restore_default_location", "DRAFTS")
        self.src.select_folder(folder_def_location)
        
        timer = gmvault_utils.Timer() # local timer for restore emails
        timer.start()
        
        nb_items = gmvault_utils.get_conf_defaults().get_int("General","nb_messages_per_restore_batch", 5) 
        
        for group_imap_ids in itertools.izip_longest(fillvalue=None, *[iter(db_gmail_ids_info)]*nb_items): 
            
            last_id = group_imap_ids[-1] #will be used to save the last id
            #remove all None elements from group_imap_ids
            group_imap_ids = itertools.ifilter(lambda x: x != None, group_imap_ids)
           
            labels_to_create    = set() #create label set
            labels_to_create.update(extra_labels) # add extra labels to applied to all emails
            
            LOG.critical("Pushing the email content of the current batch of %d emails.\n" % (nb_items))
            
            # unbury the metadata for all these emails
            for gm_id in group_imap_ids:    
                email_meta, email_data = self.gstorer.unbury_email(gm_id)
                
                LOG.critical("Pushing email body with id %s." % (gm_id))
                LOG.debug("Subject = %s." % (email_meta[self.gstorer.SUBJECT_K]))
                try:
                    # push data in gmail account and get uids
                    imap_id = self.src.push_data(all_mail_name, email_data, \
                                    email_meta[self.gstorer.FLAGS_K] , \
                                    email_meta[self.gstorer.INT_DATE_K] )      
                
                    #labels for this email => real_labels U extra_labels
                    labels = set(email_meta[self.gstorer.LABELS_K])
                    
                    # add in the labels_to_create struct
                    for label in labels:
                        LOG.debug("label = %s\n" % (label))
                        labels_to_apply[str(label)] = imap_id
            
                    # get list of labels to create (do a union with labels to create)
                    labels_to_create.update([ label for label in labels if label not in existing_labels])                  
                
                except Exception, err:
                    handle_restore_imap_error(err, gm_id, db_gmail_ids_info, self)

            #create the non existing labels and update existing labels
            if len(labels_to_create) > 0:
                LOG.debug("Labels creation tentative for email with id %s." % (gm_id))
                existing_labels = self.src.create_gmail_labels(labels_to_create, existing_labels)
                
            # associate labels with emails
            LOG.critical("Applying labels to the current batch of %d emails" % (nb_items))
            try:
                LOG.debug("Changing directory. Going into ALLMAIL")
                t = gmvault_utils.Timer()
                t.start()
                self.src.select_folder('ALLMAIL') #go to ALL MAIL to make STORE usable
                LOG.debug("Changed dir. Operation time = %s ms" % (t.elapsed_ms()))
                for label in labels_to_apply.keys():
                    self.src.apply_labels_to(labels_to_apply[label], [label]) 
            except Exception, err:
                LOG.error("Problem when applying labels %s to the following ids: %s" %(label, labels_to_apply[label]), err)
                if isinstance(err, imaplib.IMAP4.abort) and str(err).find("=> Gmvault ssl socket error: EOF") >= 0:
                    # if this is a Gmvault SSL Socket error quarantine the email and continue the restore
                    LOG.critical("Quarantine email with gm id %s from %s. GMAIL IMAP cannot restore it:"\
                         " err={%s}" % (gm_id, db_gmail_ids_info[gm_id], str(err)))
                    self.gstorer.quarantine_email(gm_id)
                    self.error_report['emails_in_quarantine'].append(gm_id)
                    LOG.critical("Disconnecting and reconnecting to restart cleanly.")
                    self.src.reconnect() #reconnect
                else:
                    raise err
            finally:
                self.src.select_folder(folder_def_location) # go back to an empty DIR (Drafts) to be fast
                labels_to_apply = collections_utils.SetMultimap() #reset label to apply
            
            nb_emails_restored += nb_items
                
            #indicate every 10 messages the number of messages left to process
            left_emails = (total_nb_emails_to_restore - nb_emails_restored)
            
            if (left_emails > 0): 
                elapsed = timer.elapsed() #elapsed time in seconds
                LOG.critical("\n== Processed %d emails in %s. %d left to be restored "\
                             "(time estimate %s).==\n" % \
                             (nb_emails_restored, timer.seconds_to_human_time(elapsed), \
                              left_emails, timer.estimate_time_left(nb_emails_restored, elapsed, left_emails)))
            
            # save id every 50 restored emails
            # add the last treated gm_id
            self.save_lastid(self.OP_EMAIL_RESTORE, last_id)
            
        return self.error_report 
    
    def old_restore_emails(self, pivot_dir = None, extra_labels = [], restart = False):
        """
           restore emails in a gmail account using batching to group restore
           If you are not in "All Mail" Folder, it is extremely fast to push emails.
           But it is not possible to reapply labels if you are not in All Mail because the uid which is returned
           is dependant on the folder. On the other hand, you can restore labels in batch which would help gaining lots of time.
           The idea is to get a batch of 50 emails and push them all in the mailbox one by one and get the uid for each of them.
           Then create a dict of labels => uid_list and for each label send a unique store command after having changed dir
        """
        LOG.critical("Restore emails in gmail account %s." % (self.login) ) 
        
        LOG.critical("Read email info from %s gmvault-db." % (self.db_root_dir))
        
        #get gmail_ids from db
        db_gmail_ids_info = self.gstorer.get_all_existing_gmail_ids(pivot_dir)
        
        LOG.critical("Total number of elements to restore %s." % (len(db_gmail_ids_info.keys())))
        
        if restart:
            db_gmail_ids_info = self.get_gmails_ids_left_to_restore(self.OP_EMAIL_RESTORE, db_gmail_ids_info)
        
        total_nb_emails_to_restore = len(db_gmail_ids_info)
        
        LOG.critical("Got all emails id left to restore. Still %s emails to do.\n" % (total_nb_emails_to_restore) )
        
        existing_labels     = set() #set of existing labels to not call create_gmail_labels all the time
        nb_emails_restored  = 0  #to count nb of emails restored
        labels_to_apply     = collections_utils.SetMultimap()
        
        new_conn  = self.src.spawn_connection()
        job_queue = Queue()
        job_nb    = 1
        
        timer = gmvault_utils.Timer() # local timer for restore emails
        timer.start()
        
        labelling_thread = LabellingThread(group=None, target=None, name="LabellingThread", args=(), kwargs={"queue" : job_queue, \
                                                                                                             "conn" : new_conn, \
                                                                                                             "gmvaulter" : self, \
                                                                                                             "total_nb_emails_to_restore": total_nb_emails_to_restore, 
                                                                                                             "timer": timer}, \
                                           verbose=None)
        labelling_thread.start()

        #get all mail folder name
        all_mail_name = self.src.get_folder_name("ALLMAIL")
        
        # go to DRAFTS folder because if you are in ALL MAIL when uploading emails it is very slow
        folder_def_location = gmvault_utils.get_conf_defaults().get("General","restore_default_location", "DRAFTS")
        self.src.select_folder(folder_def_location)
        
        nb_items = gmvault_utils.get_conf_defaults().get_int("General","nb_messages_per_restore_batch", 10) 
        
        for group_imap_ids in itertools.izip_longest(fillvalue=None, *[iter(db_gmail_ids_info)]*nb_items): 
            
            last_id = group_imap_ids[-1] #will be used to save the last id
            #remove all None elements from group_imap_ids
            group_imap_ids = itertools.ifilter(lambda x: x != None, group_imap_ids)
           
            labels_to_create    = set() #create label set
            labels_to_create.update(extra_labels) # add extra labels to applied to all emails
            
            LOG.critical("Pushing the email content of the current batch of %d emails.\n" % (nb_items))
            
            # unbury the metadata for all these emails
            for gm_id in group_imap_ids:    
                email_meta, email_data = self.gstorer.unbury_email(gm_id)
                
                LOG.critical("Pushing email body with id %s." % (gm_id))
                LOG.debug("Subject = %s." % (email_meta[self.gstorer.SUBJECT_K]))
                try:
                    # push data in gmail account and get uids
                    imap_id = self.src.push_data(all_mail_name, email_data, \
                                    email_meta[self.gstorer.FLAGS_K] , \
                                    email_meta[self.gstorer.INT_DATE_K] )      
                
                    #labels for this email => real_labels U extra_labels
                    labels = set(email_meta[self.gstorer.LABELS_K])
                    
                    # add in the labels_to_create struct
                    for label in labels:
                        LOG.debug("label = %s\n" % (label))
                        labels_to_apply[str(label)] = imap_id
            
                    # get list of labels to create (do a union with labels to create)
                    labels_to_create.update([ label for label in labels if label not in existing_labels])                  
                
                except Exception, err:
                    handle_restore_imap_error(err, gm_id, db_gmail_ids_info, self)

            #create the non existing labels and update existing labels
            if len(labels_to_create) > 0:
                LOG.debug("Labels creation tentative for email with id %s." % (gm_id))
                existing_labels = self.src.create_gmail_labels(labels_to_create, existing_labels)
                
            job_queue.put(LabelJob(1, "LabellingJob-%d" % (job_nb), labels_to_apply , last_id, nb_items, None))
            job_nb +=1
            labels_to_apply = collections_utils.SetMultimap()   
            
        return self.error_report 


class LabelJob(object):
    def __init__(self, priority, name, labels_to_create, last_id, nb_items, imapid_gmid_map):
        self.priority           = priority
        self.labels             = labels_to_create
        self.nb_items           = nb_items
        self.last_id            = last_id
        self.imap_to_gm         = imapid_gmid_map
        self.name               = name
        return
    
    def type(self):
        return "LABELJOB"
    
    def __cmp__(self, other):
        return cmp(self.priority, other.priority)

class StopJob(object):
    def __init__(self, priority):
        self.priority    = priority
        return
    
    def type(self):
        return "STOPJOB"
    
    def __cmp__(self, other):
        return cmp(self.priority, other.priority)
    
class LabellingThread(Process):

    def __init__(self, group=None, target=None, name=None,
                 args=(), kwargs=None, verbose=None):
        
        Process.__init__(self)
        self.args                       = args
        self.kwargs                     = kwargs
        self.queue                      = kwargs.get("queue", None)
        self.src                        = kwargs.get("conn", None)
        self.gmvaulter                  = kwargs.get("gmvaulter", None)
        self.total_nb_emails_to_restore = kwargs.get("total_nb_emails_to_restore", None)
        self.timer                      = kwargs.get("timer", None)
        self.nb_emails_restored = 0

    def run(self):
        
        """
           Listen to the queue
           When job label, apply labels to emails and save last_id
           If error quarantine it and continue (if 15 consecutive errors stop).
        """
        LOG.debug("Labelling Thread. Changing directory. Going into ALLMAIL")
        folder_def_location = gmvault_utils.get_conf_defaults().get("General","restore_default_location", "DRAFTS")
        t = gmvault_utils.Timer()
        t.start()
        self.src.select_folder('ALLMAIL') #go to ALL MAIL to make STORE usable
        LOG.debug("Changed dir. Operation time = %s ms" % (t.elapsed_ms()))
        
        running = True
        while running:
            job =self.queue.get(block = True, timeout = None)
            
            
            LOG.critical("==== (LabellingThread) ====. Received job %s ====" % (job.name))
            
            if job.type() == "LABELJOB":
                # associate labels with emails
                labels_to_apply = job.labels
                imap_to_gm      = job.imap_to_gm
                
                #LOG.critical("Applying labels to the current batch of %d emails" % (job.nb_items))
                try:
                    
                    #for i in range(1,10):
                    #   LOG.critical("Hello")
                    #   #time.sleep(1)
                    for label in labels_to_apply.keys():
                        LOG.critical("Apply %s to %s" % (label, labels_to_apply[label]))
                        self.src.apply_labels_to(labels_to_apply[label], [label]) 
                except Exception, err:
                    LOG.error("Problem when applying labels %s to the following ids: %s" %(label, labels_to_apply[label]), err)
                finally:
                    #self.queue.task_done()
                    pass
                
                #to be moved
                self.nb_emails_restored += job.nb_items
                
                #indicate every 10 messages the number of messages left to process
                left_emails = (self.total_nb_emails_to_restore - self.nb_emails_restored)
            
                if (left_emails > 0): 
                    elapsed = self.timer.elapsed() #elapsed time in seconds
                    LOG.critical("\n== Processed %d emails in %s. %d left to be restored "\
                             "(time estimate %s).==\n" % \
                             (self.nb_emails_restored, self.timer.seconds_to_human_time(elapsed), \
                              left_emails, self.timer.estimate_time_left(self.nb_emails_restored, elapsed, left_emails)))
            
                # save id every 50 restored emails
                # add the last treated gm_id
                self.gmvaulter.save_lastid(GMVaulter.OP_EMAIL_RESTORE, job.last_id)
            
            elif job.type() == "STOPJOB":
                self.queue.task_done()
                running = False
            
            #self.src.select_folder(folder_def_location)
            LOG.critical("==== (LabellingThread) ====. End of job %s ====" % (job.name))
        

########NEW FILE########
__FILENAME__ = json_tests
# -*- coding: utf-8 -*-
'''
Created on Nov 27, 2012

@author: aubert
'''
import json

string_to_test = u"Чаты"
labels = [ 0, string_to_test ]

def format(self, record):
        """
           Formats a record with the given formatter. If no formatter
           is set, the record message is returned. Generally speaking the
           return value is most likely a unicode string, but nothing in
           the handler interface requires a formatter to return a unicode
           string.

           The combination of a handler and formatter might have the
           formatter return an XML element tree for example.
        """
        # Decode the message to support non-ascii characters
        # We must choose the charset manually
        for record_charset in 'UTF-8', 'US-ASCII', 'ISO-8859-1':
            try:
                record.message = record.message.decode(record_charset)
                self.encoding = record_charset
            except UnicodeError:
                pass
            else:
                break
            
        if self.formatter is None:
            return record.message
        return self.formatter(record, self)

def data_to_test():
    """
       data to test
    """
    meta_obj = { 'labels' : labels }
    
    meta_desc = open("/tmp/test.json", 'w')
    
    json.dump(meta_obj, meta_desc)
        
    meta_desc.flush()
    meta_desc.close()
    
    print("Data stored")
    
    meta_desc = open("/tmp/test.json")
    
    metadata = json.load(meta_desc)
    
    new_labels = []
    
    for label in metadata['labels']:
        if isinstance(label, (int, long, float, complex)):
            label = unicode(str(label))
        
        new_labels.append(label)
    
    metadata['labels'] = new_labels
    
    print("metadata = %s\n" % (metadata))
    
    print("type(metadata['labels'][0]) = %s" % (type(metadata['labels'][0])))  
    
    print("metadata['labels'][0] = %s" % (metadata['labels'][0]))  
    
    print("type(metadata['labels'][1]) = %s" % (type(metadata['labels'][1])))  
    
    print("metadata['labels'][1] = %s" % (metadata['labels'][1]))  
    

def header_regexpr_test():
    """
    
    """ 
    #the_str = 'X-Gmail-Received: cef1a177794b2b6282967d22bcc2b6f49447a70d\r\nMessage-ID: <8b230a7105082305316d9c1a54@mail.gmail.com>\r\nSubject: Hessian ssl\r\n\r\n'
    the_str = 'Message-ID: <8b230a7105082305316d9c1a54@mail.gmail.com>\r\nX-Gmail-Received: cef1a177794b2b6282967d22bcc2b6f49447a70d\r\nSubject: Hessian ssl\r\n\r\n'
    
    
    import gmv.gmvault_db as gmvault_db
    
    matched = gmvault_db.GmailStorer.HF_SUB_RE.search(the_str)
    if matched:
        subject = matched.group('subject')
        print("subject matched = <%s>\n" % (subject))
        
    # look for a msg id
    matched = gmvault_db.GmailStorer.HF_MSGID_RE.search(the_str)
    if matched:
        msgid = matched.group('msgid')
        print("msgid matched = <%s>\n" % (msgid))

    
    matched = gmvault_db.GmailStorer.HF_XGMAIL_RECV_RE.search(the_str)
    if matched:
        received = matched.group('received').strip()
        print("matched = <%s>\n" % (received))

if __name__ == '__main__':
    header_regexpr_test()
    #data_to_test()
########NEW FILE########
__FILENAME__ = test_wx
# border.py

import wx

ID_NEW = 1
ID_RENAME = 2
ID_CLEAR = 3
ID_DELETE = 4

class Example(wx.Frame):
  
    def __init__(self, parent, title):
        super(Example, self).__init__(parent, title=title, 
            size=(260, 180))
            
        self.InitUI()
        self.Centre()
        self.Show()     
        
    def InitUI(self):
    
        panel = wx.Panel(self)

        panel.SetBackgroundColour('#4f5049')
        #hbox = wx.BoxSizer(wx.HORIZONTAL)

        #vbox = wx.BoxSizer(wx.VERTICAL)

        lbox = wx.BoxSizer(wx.VERTICAL)

        listbox = wx.ListBox(panel, -1, size=(100,50))


        #add button panel and its sizer
        btnPanel  = wx.Panel(panel, -1, size= (30,30))
        bbox = wx.BoxSizer(wx.HORIZONTAL)
        new       = wx.Button(btnPanel, ID_NEW, '+', size=(24, 24))
        ren       = wx.Button(btnPanel, ID_RENAME, '-', size=(24, 24))
        #dlt = wx.Button(btnPanel, ID_DELETE, 'D', size=(30, 30))
        #clr = wx.Button(btnPanel, ID_CLEAR, 'C', size=(30, 30))

        #hbox5 = wx.BoxSizer(wx.HORIZONTAL)
        #btn1 = wx.Button(panel, label='Ok', size=(70, 30))
        #hbox5.Add(btn1)
        #btn2 = wx.Button(panel, label='Close', size=(70, 30))
        #hbox5.Add(btn2, flag=wx.LEFT|wx.BOTTOM, border=5)
        #vbox.Add(hbox5, flag=wx.ALIGN_RIGHT|wx.RIGHT, border=10)

        #self.Bind(wx.EVT_BUTTON, self.NewItem, id=ID_NEW)
        #self.Bind(wx.EVT_BUTTON, self.OnRename, id=ID_RENAME)
        #self.Bind(wx.EVT_BUTTON, self.OnDelete, id=ID_DELETE)
        #self.Bind(wx.EVT_BUTTON, self.OnClear, id=ID_CLEAR)
        #self.Bind(wx.EVT_LISTBOX_DCLICK, self.OnRename)

        bbox.Add(new, flag= wx.LEFT, border=2)
        bbox.Add(ren, flag= wx.LEFT, border=2)
        #buttonbox.Add(dlt)
        #buttonbox.Add(clr)

        btnPanel.SetSizer(bbox)
        lbox.Add(listbox, 1, wx.EXPAND | wx.ALL, 1)
        lbox.Add(btnPanel, 0, wx.EXPAND | wx.ALL, 1)
        #lbox.Add(buttonbox, 1, wx.EXPAND | wx.ALL, 1)

        #hbox.Add(lbox, 1, wx.EXPAND | wx.ALL, 7)

        #midPan = wx.Panel(panel)
        #midPan.SetBackgroundColour('#ededed')

        #midPan1 = wx.Panel(panel)
        #midPan1.SetBackgroundColour('#ededed')

        #vbox.Add(midPan, 1, wx.EXPAND | wx.ALL, 5)
        #vbox.Add(midPan1, 1, wx.EXPAND | wx.ALL, 5)

        #hbox.Add(vbox, 1,  wx.EXPAND | wx.ALL, 5)

        panel.SetSizer(lbox)


if __name__ == '__main__':
  
    app = wx.App()
    Example(None, title='Gmvault-test')
    app.MainLoop()

########NEW FILE########
__FILENAME__ = unicode_test
# -*- coding: utf-8 -*-
import sys
import unicodedata

def ascii_hex(str):
   new_str = ""
   for c in str:
      new_str += "%s=hex[%s]," % (c,hex(ord(c)))
   return new_str
                
def convert_to_utf8(a_str):
    """
    """
    if type(a_str) != type(u'a'):
		#import chardet
		#char_enc = chardet.detect(a_str)
		#print("detected encoding = %s" % (char_enc))
		#print("system machine encoding = %s" % (sys.getdefaultencoding()))
		#u_str = unicode(a_str, char_enc['encoding'], errors='ignore')
		u_str = unicode(a_str, 'cp437', errors='ignore')
    else:
        print("Already unicode do not convert")
        u_str = a_str

    print("raw unicode = %s" % (u_str))
    #u_str = unicodedata.normalize('NFKC',u_str)
    u_str = u_str.encode('unicode_escape').decode('unicode_escape')
    print("unicode escape = %s" % (u_str))
    print("normalized unicode(NFKD) = %s" % (repr(unicodedata.normalize('NFKD',u_str))))
    print("normalized unicode(NFKC) = %s" % (repr(unicodedata.normalize('NFKC',u_str))))
    print("normalized unicode(NFC) = %s" % (repr(unicodedata.normalize('NFC',u_str))))
    print("normalized unicode(NFD) = %s" % (repr(unicodedata.normalize('NFD',u_str))))
    hex_s = ascii_hex(u_str)
    print("Hex ascii %s" % (hex_s))
    utf8_arg = u_str
    #utf8_arg = u_str.encode("utf-8")
    
    return utf8_arg

if __name__ == '__main__':

   u_str = u"label:èévader"
   convert_to_utf8(sys.argv[1])
   #convert_to_utf8(u_str)

########NEW FILE########
__FILENAME__ = sandbox_tests
'''
    Gmvault: a tool to backup and restore your gmail account.
    Copyright (C) <2011-2013>  <guillaume Aubert (guillaume dot aubert at gmail do com)>

    This program is free software: you can redistribute it and/or modify
    it under the terms of the GNU General Public License as published by
    the Free Software Foundation, either version 3 of the License, or
    (at your option) any later version.

    This program is distributed in the hope that it will be useful,
    but WITHOUT ANY WARRANTY; without even the implied warranty of
    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
    GNU General Public License for more details.

    You should have received a copy of the GNU General Public License
    along with this program.  If not, see <http://www.gnu.org/licenses/>.
'''

'''
Created on Feb 14, 2012

@author: guillaume.aubert@gmail.com

Experimentation and validation of internal mechanisms
'''

import unittest
import base64
import socket
import imaplib


import gmv.gmvault_utils as gmvault_utils
import gmv.imap_utils as imap_utils


def obfuscate_string(a_str):
    """ use base64 to obfuscate a string """
    return base64.b64encode(a_str)

def deobfuscate_string(a_str):
    """ deobfuscate a string """
    return base64.b64decode(a_str)

def read_password_file(a_path):
    """
       Read log:pass from a file in my home
    """
    pass_file = open(a_path)
    line = pass_file.readline()
    (login, passwd) = line.split(":")
    
    return (deobfuscate_string(login.strip()), deobfuscate_string(passwd.strip()))

def delete_db_dir(a_db_dir):
    """
       delete the db directory
    """
    gmvault_utils.delete_all_under(a_db_dir, delete_top_dir = True)


class TestSandbox(unittest.TestCase): #pylint:disable-msg=R0904
    """
       Current Main test class
    """

    def __init__(self, stuff):
        """ constructor """
        super(TestSandbox, self).__init__(stuff)
        
        self.login  = None
        self.passwd = None
        
        self.gmvault_login  = None
        self.gmvault_passwd = None 
    
    def setUp(self): #pylint:disable-msg=C0103
        self.login, self.passwd = read_password_file('/homespace/gaubert/.ssh/passwd')
        
        self.gmvault_login, self.gmvault_passwd = read_password_file('/homespace/gaubert/.ssh/gsync_passwd')
        
        
    def ztest_logger(self):
        """
           Test the logging mechanism
        """
        
        import gmv.log_utils as log_utils
        log_utils.LoggerFactory.setup_cli_app_handler('./gmv.log') 
        
        LOG = log_utils.LoggerFactory.get_logger('gmv') #pylint:disable-msg=C0103
        
        LOG.info("On Info")
        
        LOG.warning("On Warning")
        
        LOG.error("On Error")
        
        LOG.notice("On Notice")
        
        try:
            raise Exception("Exception. This is my exception")
            self.fail("Should never arrive here") #pylint:disable-msg=W0101
        except Exception, err: #pylint:disable-msg=W0101, W0703
            LOG.exception("error,", err)
        
        LOG.critical("On Critical")
        
    def ztest_encrypt_blowfish(self):
        """
           Test encryption with blowfish
        """
        file_path = '../etc/tests/test_few_days_syncer/2384403887202624608.eml.gz'
        
        import gzip
        import gmv.blowfish
        
        #create blowfish cipher
        cipher = gmv.blowfish.Blowfish('VerySeCretKey')
         
        gz_fd = gzip.open(file_path)
        
        content = gz_fd.read()
        
        cipher.initCTR()
        crypted = cipher.encryptCTR(content)
        
        cipher.initCTR()
        decrypted = cipher.decryptCTR(crypted)
        
        self.assertEquals(decrypted, content)
        
    def ztest_regexpr(self):
        """
           regexpr for 
        """
        import re
        the_str = "Subject: Marta Gutierrez commented on her Wall post.\nMessage-ID: <c5b5deee29e373ca42cec75e4ef8384e@www.facebook.com>"
        regexpr = "Subject:\s+(?P<subject>.*)\s+Message-ID:\s+<(?P<msgid>.*)>"
        reg = re.compile(regexpr)
        
        matched = reg.match(the_str)
        if matched:
            print("Matched")
            print("subject=[%s],messageid=[%s]" % (matched.group('subject'), matched.group('msgid')))
            
    def ztest_is_encrypted_regexpr(self):
        """
           Encrypted re
        """
        import re
        the_str ="1384313269332005293.eml.crypt.gz"
        regexpr ="[\w+,\.]+crypt[\w,\.]*"
        
        reg= re.compile(regexpr)
        matched = reg.match(the_str)
        if matched:
            print("\nMatched")
        else:
            print("\nUnmatched")
    
    
    def ztest_memory_error_bug(self):
        """
           Try to push the memory error
        """
        # now read the password
        import sys
        import gmv.gmv_cmd as gmv_cmd
        import email
        
        fd = open('/Users/gaubert/gmvault-data/gmvault-db-bug/db/2004-10/1399791159741721320.eml')
        email_body = fd.read()
        mail = email.message_from_string(email_body)

        print mail
        
        sys.argv = ['gmvault.py', 'restore', '--db-dir', '/Users/gaubert/gmvault-data/gmvault-db-bug', 'gsync.mtester@gmail.com']
        
        gmv_cmd.bootstrap_run()
        
    def ztest_retry_mode(self):
        """
           Test that the decorators are functionning properly
        """
        class MonkeyIMAPFetcher(imap_utils.GIMAPFetcher):
            
            def __init__(self, host, port, login, credential, readonly_folder = True):
                """
                   Constructor
                """
                super(MonkeyIMAPFetcher, self).__init__( host, port, login, credential, readonly_folder)
                self.connect_nb = 0
                
            def connect(self):
                """
                   connect
                """
                self.connect_nb += 1
            
            @imap_utils.retry(3,1,2)   
            def push_email(self, a_body, a_flags, a_internal_time, a_labels):
                """
                   Throw exceptions
                """
                #raise imaplib.IMAP4.error("GIMAPFetcher cannot restore email in %s account." %("myaccount@gmail.com"))
                #raise imaplib.IMAP4.abort("GIMAPFetcher cannot restore email in %s account." %("myaccount@gmail.com"))
                raise socket.error("Error")
                #raise imap_utils.PushEmailError("GIMAPFetcher cannot restore email in %s account." %("myaccount@gmail.com"))
            
        
        imap_fetch = MonkeyIMAPFetcher(host = None, port = None, login = None, credential = None)
        try:
            imap_fetch.push_email(None, None, None, None)
        #except Exception, err:
        except imaplib.IMAP4.error, err:
            self.assertEquals('GIMAPFetcher cannot restore email in myaccount@gmail.com account.', str(err))
        
        self.assertEquals(imap_fetch.connect_nb, 3)
    
    def ztest_os_walk(self):
        """
           test os walk
        """
        import os
        for root, dirs, files in os.walk('/Users/gaubert/Dev/projects/gmvault/src/gmv/gmvault-db/db'):
            print("root: %s, sub-dirs : %s, files = %s" % (root, dirs, files))
    
    def ztest_get_subdir_info(self):
        """
           test get subdir info
        """
        import gmv.gmvault as gmv
        
        storer = gmv.GmailStorer("/Users/gaubert/gmvault-db")
        
        storer.init_sub_chats_dir()
       
        
    
    def ztest_ordered_os_walk(self):
        """
           test ordered os walk
        """
        import gmv.gmvault_utils as gmvu
        
        for vals in gmvu.ordered_dirwalk('/home/aubert/gmvault-db.old/db', a_wildcards="*.meta"):
            print("vals = %s\n" % (vals))
            pass
        
        import os
        for root, dirs, files in os.walk('/Users/gaubert/Dev/projects/gmvault/src/gmv/gmvault-db/db'):
            print("root: %s, sub-dirs : %s, files = %s" % (root, dirs, files))
            
            
    
    
    def ztest_logging(self):
        """
           Test logging
        """
        #gmv_cmd.init_logging()
        import gmv.log_utils as log_utils
        log_utils.LoggerFactory.setup_cli_app_handler(activate_log_file=True, file_path="/tmp/gmvault.log") 
        LOG = log_utils.LoggerFactory.get_logger('gmv')
        LOG.critical("This is critical")
        LOG.info("This is info")
        LOG.error("This is error")
        LOG.debug("This is debug")
        

        

def tests():
    """
       main test function
    """
    suite = unittest.TestLoader().loadTestsFromTestCase(TestSandbox)
    unittest.TextTestRunner(verbosity=2).run(suite)
 
if __name__ == '__main__':
    
    tests()

########NEW FILE########
__FILENAME__ = validation_tests
'''
    Gmvault: a tool to backup and restore your gmail account.
    Copyright (C) <2011-2013>  <guillaume Aubert (guillaume dot aubert at gmail do com)>

    This program is free software: you can redistribute it and/or modify
    it under the terms of the GNU General Public License as published by
    the Free Software Foundation, either version 3 of the License, or
    (at your option) any later version.

    This program is distributed in the hope that it will be useful,
    but WITHOUT ANY WARRANTY; without even the implied warranty of
    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
    GNU General Public License for more details.

    You should have received a copy of the GNU General Public License
    along with this program.  If not, see <http://www.gnu.org/licenses/>.
'''

import sys
import unittest
import base64
import shutil
import os

import ssl
import gmv.gmvault as gmvault
import gmv.gmvault_utils as gmvault_utils

def obfuscate_string(a_str):
    """ use base64 to obfuscate a string """
    return base64.b64encode(a_str)

def deobfuscate_string(a_str):
    """ deobfuscate a string """
    return base64.b64decode(a_str)

def read_password_file(a_path):
    """
       Read log:pass from a file in my home
    """
    pass_file = open(a_path)
    line = pass_file.readline()
    (login, passwd) = line.split(":")
    
    return (deobfuscate_string(login.strip()), deobfuscate_string(passwd.strip()))

def delete_db_dir(a_db_dir):
    """
       delete the db directory
    """
    gmvault_utils.delete_all_under(a_db_dir, delete_top_dir = True)


class TestGMVaultValidation(unittest.TestCase): #pylint:disable-msg=R0904
    """
       Validation Tests
    """

    def __init__(self, stuff):
        """ constructor """
        super(TestGMVaultValidation, self).__init__(stuff)
        
        self.login  = None
        self.passwd = None
        
        self.gmvault_login  = None
        self.gmvault_passwd = None 
        
        self.default_dir = "/tmp/gmvault-tests"
    
    def setUp(self): #pylint:disable-msg=C0103
        self.login, self.passwd = read_password_file('/homespace/gaubert/.ssh/passwd')
        
        self.gmvault_test_login, self.gmvault_test_passwd = read_password_file('/homespace/gaubert/.ssh/gsync_passwd')
                
    def test_help_msg_spawned_by_def(self):
        """
           spawn python gmv_runner account > help_msg_spawned.txt
           check that res is 0 or 1
        """
        pass
   
    def test_backup_10_emails(self):
        """
           backup 10 emails and check that they are backed
           => spawn a process with the options
           => python gmv_runner.py sync account > checkfile
        """
        pass
    
    def test_restore_and_check(self):
        """
           Restore emails, retrieve them and compare with originals
        """
        db_dir = "/tmp/the_dir"
    
    
    def ztest_restore_on_gmail(self):
        """
           clean db disk
           sync with gmail for few emails
           restore them on gmail test
        """
        
        db_dir = '/tmp/gmail_bk'
        
        #clean db dir
        delete_db_dir(db_dir)
        credential    = { 'type' : 'passwd', 'value': self.passwd}
        gs_credential = { 'type' : 'passwd', 'value': self.gmvault_passwd}
        search_req    = { 'type' : 'imap', 'req': "Since 1-Nov-2011 Before 3-Nov-2011"}
        
        syncer = gmvault.GMVaulter(db_dir, 'imap.gmail.com', 993, self.login, credential, read_only_access = False, use_encryption = True)
        
        #syncer.sync(imap_req = "Since 1-Nov-2011 Before 4-Nov-2011")
        # Nov-2007 BigDataset
        syncer.sync(imap_req = search_req)
        
        restorer = gmvault.GMVaulter(db_dir, 'imap.gmail.com', 993, self.gmvault_login, gs_credential, read_only_access = False)
        restorer.restore()
            
        print("Done \n")    
        
        
        

def tests():
    """
       main test function
    """
    suite = unittest.TestLoader().loadTestsFromTestCase(TestGMVaultValidation)
    unittest.TextTestRunner(verbosity=2).run(suite)
 
if __name__ == '__main__':
    
    tests()

########NEW FILE########
