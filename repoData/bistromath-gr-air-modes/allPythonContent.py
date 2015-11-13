__FILENAME__ = get_correlated_records
#!/usr/bin/env python
from air_modes import modes_parse, mlat
import numpy
import sys

#sffile = open("27augsf3.txt")
#rudifile = open("27augrudi3.txt")

#sfoutfile = open("sfout.txt", "w")
#rudioutfile = open("rudiout.txt", "w")

sfparse = modes_parse.modes_parse([37.762236,-122.442525])

sf_station = [37.762236,-122.442525, 100]
mv_station = [37.409348,-122.07732, 100]
bk_station = [37.854246, -122.266701, 100]

raw_stamps = []

#first iterate through both files to find the estimated time difference. doesn't have to be accurate to more than 1ms or so.
#to do this, look for type 17 position packets with the same data. assume they're unique. print the tdiff.

#collect a list of raw timestamps for each aircraft from each station
#the raw stamps have to be processed into corrected stamps OR distance has to be included in each
#then postprocess to find clock delay for each and determine drift rate for each aircraft separately
#then come up with an average clock drift rate
#then find an average drift-corrected clock delay
#then find rms error

#ok so get [ICAO, [raw stamps], [distance]] for each matched record

files = [open(arg) for arg in sys.argv[1:]]

#files = [sffile, rudifile]
stations = [sf_station, mv_station]#, bk_station]

records = []

for each_file in files:
    recordlist = []
    for line in each_file:
        [msgtype, shortdata, longdata, parity, ecc, reference, timestamp] = line.split()
        recordlist.append({"data": {"msgtype": long(msgtype, 10),\
                                    "shortdata": long(shortdata, 16),\
                                    "longdata": long(longdata, 16),\
                                    "parity": long(parity, 16),\
                                    "ecc": long(ecc, 16)},
                           "time": float(timestamp)\
                          })
    records.append(recordlist)

#ok now we have records parsed into something usable that we can == with

def feet_to_meters(feet):
    return feet * 0.3048006096012

all_heard = []
#gather list of reports which were heard by all stations
for station0_report in records[0]: #iterate over list of reports from station 0
    for other_reports in records[1:]:
        stamps = [station0_report["time"]]
        stamp = [report["time"] for report in other_reports if report["data"] == station0_report["data"]]# for other_reports in records[1:]]
        if len(stamp) > 0:
            stamps.append(stamp[0])
    if len(stamps) == len(records): #found same report in all records
        all_heard.append({"data": station0_report["data"], "times": stamps})

#print all_heard

#ok, now let's pull out the location-bearing packets so we can find our time offset
position_reports = [x for x in all_heard if x["data"]["msgtype"] == 17 and 9 <= (x["data"]["longdata"] >> 51) & 0x1F <= 18]
offset_list = []
#there's probably a way to list-comprehension-ify this but it looks hard
for msg in position_reports:
    data = msg["data"]
    [alt, lat, lon, rng, bearing] = sfparse.parseBDS05(data["shortdata"], data["longdata"], data["parity"], data["ecc"])
    ac_pos = [lat, lon, feet_to_meters(alt)]
    rel_times = []
    for time, station in zip(msg["times"], stations):
        #here we get the estimated time at the aircraft when it transmitted
        range_to_ac = numpy.linalg.norm(numpy.array(mlat.llh2ecef(station))-numpy.array(mlat.llh2ecef(ac_pos)))
        timestamp_at_ac = time - range_to_ac / mlat.c
        rel_times.append(timestamp_at_ac)
    offset_list.append({"aircraft": data["shortdata"] & 0xffffff, "times": rel_times})

#this is a list of unique aircraft, heard by all stations, which transmitted position packets
#we do drift calcs separately for each aircraft in the set because mixing them seems to screw things up
#i haven't really sat down and figured out why that is yet
unique_aircraft = list(set([x["aircraft"] for x in offset_list]))
print "Aircraft heard for clock drift estimate: %s" % [str("%x" % ac) for ac in unique_aircraft]
print "Total reports used: %d over %.2f seconds" % (len(position_reports), position_reports[-1]["times"][0]-position_reports[0]["times"][0])

#get a list of reported times gathered by the unique aircraft that transmitted them
#abs_unique_times = [report["times"] for ac in unique_aircraft for report in offset_list if report["aircraft"] == ac]
#print abs_unique_times
#todo: the below can probably be done cleaner with nested list comprehensions
clock_rate_corrections = [0]
for i in range(1,len(stations)):
    drift_error_limited = []
    for ac in unique_aircraft:
        times = [report["times"] for report in offset_list if report["aircraft"] == ac]

        s0_times = [report[0] for report in times]
        rel_times = [report[i]-report[0] for report in times]

        #find drift error rate
        drift_error = [(y-x)/(b-a) for x,y,a,b in zip(rel_times, rel_times[1:], s0_times[0:], s0_times[1:])]
        drift_error_limited.append([x for x in drift_error if abs(x) < 1e-5])

    #flatten the list of lists (tacky, there's a better way)
    drift_error_limited = [x for sublist in drift_error_limited for x in sublist]
    clock_rate_corrections.append(0-numpy.mean(drift_error_limited))

for i in range(len(clock_rate_corrections)):
    print "drift from %d relative to station 0: %.3fppm" % (i, clock_rate_corrections[i] * 1e6)

#let's get the average clock offset (based on drift-corrected, TDOA-corrected derived timestamps)
clock_offsets = [[numpy.mean([x["times"][i]*(1+clock_rate_corrections[i])-x["times"][0] for x in offset_list])][0] for i in range(0,len(stations))]
for i in range(len(clock_offsets)):
    print "mean offset from %d relative to station 0: %.3f seconds" % (i, clock_offsets[i])

#for the two-station case, let's now go back, armed with our clock drift and offset, and get the variance between expected and observed timestamps
error_list = []
for i in range(1,len(stations)):
    for report in offset_list:
        error = abs(((report["times"][i]*(1+clock_rate_corrections[i]) - report["times"][0]) - clock_offsets[i]) * mlat.c)
        error_list.append(error)
        #print error

rms_error = (numpy.mean([error**2 for error in error_list]))**0.5
print "RMS error in TDOA: %.1f meters" % rms_error

########NEW FILE########
__FILENAME__ = get_dupes
#!/usr/bin/env python

import sys, re

if __name__== '__main__':
    data = sys.stdin.readlines()
    icaos = []
    num_icaos = 0
    for line in data:
        match = re.match(".*Type.*from (\w+)", line)
        if match is not None:
            icao = int(match.group(1), 16)
            icaos.append(icao)

    #get dupes
    dupes = sorted([icao for icao in set(icaos) if icaos.count(icao) > 1])
    count = sum([icaos.count(icao) for icao in dupes])
    for icao in dupes:
        print "%x" % icao
    print "Found %i replies from %i non-unique aircraft, out of a total %i replies (%i likely spurious replies)." \
            % (count, len(dupes), len(icaos), len(icaos)-count)



########NEW FILE########
__FILENAME__ = uhd_modes
#!/usr/bin/env python

if __name__ == '__main__':
    print "ERROR: uhd_modes.py has been deprecated. The new application name is modes_rx."

########NEW FILE########
__FILENAME__ = FindPyQt
# Copyright (c) 2007, Simon Edwards <simon@simonzone.com>
# Redistribution and use is allowed according to the terms of the BSD license.
# For details see the accompanying COPYING-CMAKE-SCRIPTS file.

import PyQt4.pyqtconfig

pyqtcfg = PyQt4.pyqtconfig.Configuration()
print("pyqt_version:%06.0x" % pyqtcfg.pyqt_version)
print("pyqt_version_str:%s" % pyqtcfg.pyqt_version_str)

pyqt_version_tag = ""
in_t = False
for item in pyqtcfg.pyqt_sip_flags.split(' '):
    if item=="-t":
        in_t = True
    elif in_t:
        if item.startswith("Qt_4"):
            pyqt_version_tag = item
    else:
        in_t = False
print("pyqt_version_tag:%s" % pyqt_version_tag)

print("pyqt_sip_dir:%s" % pyqtcfg.pyqt_sip_dir)
print("pyqt_sip_flags:%s" % pyqtcfg.pyqt_sip_flags)

########NEW FILE########
__FILENAME__ = base
#
# Copyright 2010 Free Software Foundation, Inc.
# 
# This file is part of GNU Radio
# 
# GNU Radio is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 3, or (at your option)
# any later version.
# 
# GNU Radio is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
# 
# You should have received a copy of the GNU General Public License
# along with GNU Radio; see the file COPYING.  If not, write to
# the Free Software Foundation, Inc., 51 Franklin Street,
# Boston, MA 02110-1301, USA.
# 
"""
A base class is created.

Classes based upon this are used to make more user-friendly interfaces
to the doxygen xml docs than the generated classes provide.
"""

import os
import pdb

from xml.parsers.expat import ExpatError

from generated import compound


class Base(object):

    class Duplicate(StandardError):
        pass

    class NoSuchMember(StandardError):
        pass

    class ParsingError(StandardError):
        pass

    def __init__(self, parse_data, top=None):
        self._parsed = False
        self._error = False
        self._parse_data = parse_data
        self._members = []
        self._dict_members = {}
        self._in_category = {}
        self._data = {}
        if top is not None:
            self._xml_path = top._xml_path
            # Set up holder of references
        else:
            top = self
            self._refs = {}
            self._xml_path = parse_data
        self.top = top

    @classmethod
    def from_refid(cls, refid, top=None):
        """ Instantiate class from a refid rather than parsing object. """
        # First check to see if its already been instantiated.
        if top is not None and refid in top._refs:
            return top._refs[refid]
        # Otherwise create a new instance and set refid.
        inst = cls(None, top=top)
        inst.refid = refid
        inst.add_ref(inst)
        return inst

    @classmethod
    def from_parse_data(cls, parse_data, top=None):
        refid = getattr(parse_data, 'refid', None)
        if refid is not None and top is not None and refid in top._refs:
            return top._refs[refid]
        inst = cls(parse_data, top=top)
        if refid is not None:
            inst.refid = refid
            inst.add_ref(inst)
        return inst

    def add_ref(self, obj):
        if hasattr(obj, 'refid'):
            self.top._refs[obj.refid] = obj

    mem_classes = []

    def get_cls(self, mem):
        for cls in self.mem_classes:
            if cls.can_parse(mem):
                return cls
        raise StandardError(("Did not find a class for object '%s'." \
                                 % (mem.get_name())))

    def convert_mem(self, mem):
        try:
            cls = self.get_cls(mem)
            converted = cls.from_parse_data(mem, self.top)
            if converted is None:
                raise StandardError('No class matched this object.')
            self.add_ref(converted)
            return converted
        except StandardError, e:
            print e

    @classmethod
    def includes(cls, inst):
        return isinstance(inst, cls)

    @classmethod
    def can_parse(cls, obj):
        return False

    def _parse(self):
        self._parsed = True

    def _get_dict_members(self, cat=None):
        """
        For given category a dictionary is returned mapping member names to
        members of that category.  For names that are duplicated the name is
        mapped to None.
        """
        self.confirm_no_error()
        if cat not in self._dict_members:
            new_dict = {}
            for mem in self.in_category(cat):
                if mem.name() not in new_dict:
                    new_dict[mem.name()] = mem
                else:
                    new_dict[mem.name()] = self.Duplicate
            self._dict_members[cat] = new_dict
        return self._dict_members[cat]

    def in_category(self, cat):
        self.confirm_no_error()
        if cat is None:
            return self._members
        if cat not in self._in_category:
            self._in_category[cat] = [mem for mem in self._members
                                      if cat.includes(mem)]
        return self._in_category[cat]
        
    def get_member(self, name, cat=None):
        self.confirm_no_error()
        # Check if it's in a namespace or class.
        bits = name.split('::')
        first = bits[0]
        rest = '::'.join(bits[1:])
        member = self._get_dict_members(cat).get(first, self.NoSuchMember)
        # Raise any errors that are returned.
        if member in set([self.NoSuchMember, self.Duplicate]):
            raise member()
        if rest:
            return member.get_member(rest, cat=cat)
        return member

    def has_member(self, name, cat=None):
        try:
            mem = self.get_member(name, cat=cat)
            return True
        except self.NoSuchMember:
            return False

    def data(self):
        self.confirm_no_error()
        return self._data

    def members(self):
        self.confirm_no_error()
        return self._members
    
    def process_memberdefs(self):
        mdtss = []
        for sec in self._retrieved_data.compounddef.sectiondef:
            mdtss += sec.memberdef
        # At the moment we lose all information associated with sections.
        # Sometimes a memberdef is in several sectiondef.
        # We make sure we don't get duplicates here.
        uniques = set([])
        for mem in mdtss:
            converted = self.convert_mem(mem)
            pair = (mem.name, mem.__class__)
            if pair not in uniques:
                uniques.add(pair)
                self._members.append(converted)
        
    def retrieve_data(self):
        filename = os.path.join(self._xml_path, self.refid + '.xml')
        try:
            self._retrieved_data = compound.parse(filename)
        except ExpatError:
            print('Error in xml in file %s' % filename)
            self._error = True
            self._retrieved_data = None
            
    def check_parsed(self):
        if not self._parsed:
            self._parse()

    def confirm_no_error(self):
        self.check_parsed()
        if self._error:
            raise self.ParsingError()

    def error(self):
        self.check_parsed()
        return self._error

    def name(self):
        # first see if we can do it without processing.
        if self._parse_data is not None:
            return self._parse_data.name
        self.check_parsed()
        return self._retrieved_data.compounddef.name

########NEW FILE########
__FILENAME__ = doxyindex
#
# Copyright 2010 Free Software Foundation, Inc.
# 
# This file is part of GNU Radio
# 
# GNU Radio is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 3, or (at your option)
# any later version.
# 
# GNU Radio is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
# 
# You should have received a copy of the GNU General Public License
# along with GNU Radio; see the file COPYING.  If not, write to
# the Free Software Foundation, Inc., 51 Franklin Street,
# Boston, MA 02110-1301, USA.
# 
"""
Classes providing more user-friendly interfaces to the doxygen xml
docs than the generated classes provide.
"""

import os

from generated import index
from base import Base
from text import description

class DoxyIndex(Base):
    """
    Parses a doxygen xml directory.
    """

    __module__ = "gnuradio.utils.doxyxml"

    def _parse(self):
        if self._parsed:
            return
        super(DoxyIndex, self)._parse()
        self._root = index.parse(os.path.join(self._xml_path, 'index.xml'))      
        for mem in self._root.compound:
            converted = self.convert_mem(mem)
            # For files we want the contents to be accessible directly
            # from the parent rather than having to go through the file
            # object.
            if self.get_cls(mem) == DoxyFile:
                if mem.name.endswith('.h'):
                    self._members += converted.members()
                    self._members.append(converted)
            else:
                self._members.append(converted)


def generate_swig_doc_i(self):
    """
    %feature("docstring") gr_make_align_on_samplenumbers_ss::align_state "
    Wraps the C++: gr_align_on_samplenumbers_ss::align_state";
    """
    pass


class DoxyCompMem(Base):


    kind = None

    def __init__(self, *args, **kwargs):
        super(DoxyCompMem, self).__init__(*args, **kwargs)

    @classmethod
    def can_parse(cls, obj):
        return obj.kind == cls.kind

    def set_descriptions(self, parse_data):
        bd = description(getattr(parse_data, 'briefdescription', None))
        dd = description(getattr(parse_data, 'detaileddescription', None))
        self._data['brief_description'] = bd
        self._data['detailed_description'] = dd        

class DoxyCompound(DoxyCompMem):
    pass

class DoxyMember(DoxyCompMem):
    pass
    

class DoxyFunction(DoxyMember):

    __module__ = "gnuradio.utils.doxyxml"

    kind = 'function'

    def _parse(self):
        if self._parsed:
            return
        super(DoxyFunction, self)._parse()
        self.set_descriptions(self._parse_data)
        self._data['params'] = []
        prms = self._parse_data.param
        for prm in prms:
            self._data['params'].append(DoxyParam(prm))

    brief_description = property(lambda self: self.data()['brief_description'])
    detailed_description = property(lambda self: self.data()['detailed_description'])
    params = property(lambda self: self.data()['params'])

Base.mem_classes.append(DoxyFunction)


class DoxyParam(DoxyMember):
    
    __module__ = "gnuradio.utils.doxyxml"

    def _parse(self):
        if self._parsed:
            return
        super(DoxyParam, self)._parse()
        self.set_descriptions(self._parse_data)
        self._data['declname'] = self._parse_data.declname

    brief_description = property(lambda self: self.data()['brief_description'])
    detailed_description = property(lambda self: self.data()['detailed_description'])
    declname = property(lambda self: self.data()['declname'])

class DoxyClass(DoxyCompound):
    
    __module__ = "gnuradio.utils.doxyxml"

    kind = 'class'
    
    def _parse(self):
        if self._parsed:
            return
        super(DoxyClass, self)._parse()
        self.retrieve_data()
        if self._error:
            return
        self.set_descriptions(self._retrieved_data.compounddef)
        # Sectiondef.kind tells about whether private or public.
        # We just ignore this for now.
        self.process_memberdefs()

    brief_description = property(lambda self: self.data()['brief_description'])
    detailed_description = property(lambda self: self.data()['detailed_description'])

Base.mem_classes.append(DoxyClass)
        

class DoxyFile(DoxyCompound):
    
    __module__ = "gnuradio.utils.doxyxml"

    kind = 'file'
    
    def _parse(self):
        if self._parsed:
            return
        super(DoxyFile, self)._parse()
        self.retrieve_data()
        self.set_descriptions(self._retrieved_data.compounddef)
        if self._error:
            return
        self.process_memberdefs()
        
    brief_description = property(lambda self: self.data()['brief_description'])
    detailed_description = property(lambda self: self.data()['detailed_description'])

Base.mem_classes.append(DoxyFile)


class DoxyNamespace(DoxyCompound):
    
    __module__ = "gnuradio.utils.doxyxml"

    kind = 'namespace'
    
Base.mem_classes.append(DoxyNamespace)


class DoxyGroup(DoxyCompound):
    
    __module__ = "gnuradio.utils.doxyxml"

    kind = 'group'

    def _parse(self):
        if self._parsed:
            return
        super(DoxyGroup, self)._parse()
        self.retrieve_data()
        if self._error:
            return
        cdef = self._retrieved_data.compounddef
        self._data['title'] = description(cdef.title)
        # Process inner groups
        grps = cdef.innergroup
        for grp in grps:
            converted = DoxyGroup.from_refid(grp.refid, top=self.top)
            self._members.append(converted)
        # Process inner classes
        klasses = cdef.innerclass
        for kls in klasses:
            converted = DoxyClass.from_refid(kls.refid, top=self.top)
            self._members.append(converted)
        # Process normal members
        self.process_memberdefs()

    title = property(lambda self: self.data()['title'])
        

Base.mem_classes.append(DoxyGroup)


class DoxyFriend(DoxyMember):

    __module__ = "gnuradio.utils.doxyxml"

    kind = 'friend'

Base.mem_classes.append(DoxyFriend)


class DoxyOther(Base):
    
    __module__ = "gnuradio.utils.doxyxml"

    kinds = set(['variable', 'struct', 'union', 'define', 'typedef', 'enum', 'dir', 'page'])

    @classmethod
    def can_parse(cls, obj):
        return obj.kind in cls.kinds
    
Base.mem_classes.append(DoxyOther)


########NEW FILE########
__FILENAME__ = compound
#!/usr/bin/env python

"""
Generated Mon Feb  9 19:08:05 2009 by generateDS.py.
"""

from string import lower as str_lower
from xml.dom import minidom
from xml.dom import Node

import sys

import compoundsuper as supermod
from compoundsuper import MixedContainer


class DoxygenTypeSub(supermod.DoxygenType):
    def __init__(self, version=None, compounddef=None):
        supermod.DoxygenType.__init__(self, version, compounddef)

    def find(self, details):

        return self.compounddef.find(details)

supermod.DoxygenType.subclass = DoxygenTypeSub
# end class DoxygenTypeSub


class compounddefTypeSub(supermod.compounddefType):
    def __init__(self, kind=None, prot=None, id=None, compoundname='', title='', basecompoundref=None, derivedcompoundref=None, includes=None, includedby=None, incdepgraph=None, invincdepgraph=None, innerdir=None, innerfile=None, innerclass=None, innernamespace=None, innerpage=None, innergroup=None, templateparamlist=None, sectiondef=None, briefdescription=None, detaileddescription=None, inheritancegraph=None, collaborationgraph=None, programlisting=None, location=None, listofallmembers=None):
        supermod.compounddefType.__init__(self, kind, prot, id, compoundname, title, basecompoundref, derivedcompoundref, includes, includedby, incdepgraph, invincdepgraph, innerdir, innerfile, innerclass, innernamespace, innerpage, innergroup, templateparamlist, sectiondef, briefdescription, detaileddescription, inheritancegraph, collaborationgraph, programlisting, location, listofallmembers)

    def find(self, details):

        if self.id == details.refid:
            return self

        for sectiondef in self.sectiondef:
            result = sectiondef.find(details)
            if result:
                return result


supermod.compounddefType.subclass = compounddefTypeSub
# end class compounddefTypeSub


class listofallmembersTypeSub(supermod.listofallmembersType):
    def __init__(self, member=None):
        supermod.listofallmembersType.__init__(self, member)
supermod.listofallmembersType.subclass = listofallmembersTypeSub
# end class listofallmembersTypeSub


class memberRefTypeSub(supermod.memberRefType):
    def __init__(self, virt=None, prot=None, refid=None, ambiguityscope=None, scope='', name=''):
        supermod.memberRefType.__init__(self, virt, prot, refid, ambiguityscope, scope, name)
supermod.memberRefType.subclass = memberRefTypeSub
# end class memberRefTypeSub


class compoundRefTypeSub(supermod.compoundRefType):
    def __init__(self, virt=None, prot=None, refid=None, valueOf_='', mixedclass_=None, content_=None):
        supermod.compoundRefType.__init__(self, mixedclass_, content_)
supermod.compoundRefType.subclass = compoundRefTypeSub
# end class compoundRefTypeSub


class reimplementTypeSub(supermod.reimplementType):
    def __init__(self, refid=None, valueOf_='', mixedclass_=None, content_=None):
        supermod.reimplementType.__init__(self, mixedclass_, content_)
supermod.reimplementType.subclass = reimplementTypeSub
# end class reimplementTypeSub


class incTypeSub(supermod.incType):
    def __init__(self, local=None, refid=None, valueOf_='', mixedclass_=None, content_=None):
        supermod.incType.__init__(self, mixedclass_, content_)
supermod.incType.subclass = incTypeSub
# end class incTypeSub


class refTypeSub(supermod.refType):
    def __init__(self, prot=None, refid=None, valueOf_='', mixedclass_=None, content_=None):
        supermod.refType.__init__(self, mixedclass_, content_)
supermod.refType.subclass = refTypeSub
# end class refTypeSub



class refTextTypeSub(supermod.refTextType):
    def __init__(self, refid=None, kindref=None, external=None, valueOf_='', mixedclass_=None, content_=None):
        supermod.refTextType.__init__(self, mixedclass_, content_)

supermod.refTextType.subclass = refTextTypeSub
# end class refTextTypeSub

class sectiondefTypeSub(supermod.sectiondefType):


    def __init__(self, kind=None, header='', description=None, memberdef=None):
        supermod.sectiondefType.__init__(self, kind, header, description, memberdef)

    def find(self, details):

        for memberdef in self.memberdef:
            if memberdef.id == details.refid:
                return memberdef

        return None


supermod.sectiondefType.subclass = sectiondefTypeSub
# end class sectiondefTypeSub


class memberdefTypeSub(supermod.memberdefType):
    def __init__(self, initonly=None, kind=None, volatile=None, const=None, raise_=None, virt=None, readable=None, prot=None, explicit=None, new=None, final=None, writable=None, add=None, static=None, remove=None, sealed=None, mutable=None, gettable=None, inline=None, settable=None, id=None, templateparamlist=None, type_=None, definition='', argsstring='', name='', read='', write='', bitfield='', reimplements=None, reimplementedby=None, param=None, enumvalue=None, initializer=None, exceptions=None, briefdescription=None, detaileddescription=None, inbodydescription=None, location=None, references=None, referencedby=None):
        supermod.memberdefType.__init__(self, initonly, kind, volatile, const, raise_, virt, readable, prot, explicit, new, final, writable, add, static, remove, sealed, mutable, gettable, inline, settable, id, templateparamlist, type_, definition, argsstring, name, read, write, bitfield, reimplements, reimplementedby, param, enumvalue, initializer, exceptions, briefdescription, detaileddescription, inbodydescription, location, references, referencedby)
supermod.memberdefType.subclass = memberdefTypeSub
# end class memberdefTypeSub


class descriptionTypeSub(supermod.descriptionType):
    def __init__(self, title='', para=None, sect1=None, internal=None, mixedclass_=None, content_=None):
        supermod.descriptionType.__init__(self, mixedclass_, content_)
supermod.descriptionType.subclass = descriptionTypeSub
# end class descriptionTypeSub


class enumvalueTypeSub(supermod.enumvalueType):
    def __init__(self, prot=None, id=None, name='', initializer=None, briefdescription=None, detaileddescription=None, mixedclass_=None, content_=None):
        supermod.enumvalueType.__init__(self, mixedclass_, content_)
supermod.enumvalueType.subclass = enumvalueTypeSub
# end class enumvalueTypeSub


class templateparamlistTypeSub(supermod.templateparamlistType):
    def __init__(self, param=None):
        supermod.templateparamlistType.__init__(self, param)
supermod.templateparamlistType.subclass = templateparamlistTypeSub
# end class templateparamlistTypeSub


class paramTypeSub(supermod.paramType):
    def __init__(self, type_=None, declname='', defname='', array='', defval=None, briefdescription=None):
        supermod.paramType.__init__(self, type_, declname, defname, array, defval, briefdescription)
supermod.paramType.subclass = paramTypeSub
# end class paramTypeSub


class linkedTextTypeSub(supermod.linkedTextType):
    def __init__(self, ref=None, mixedclass_=None, content_=None):
        supermod.linkedTextType.__init__(self, mixedclass_, content_)
supermod.linkedTextType.subclass = linkedTextTypeSub
# end class linkedTextTypeSub


class graphTypeSub(supermod.graphType):
    def __init__(self, node=None):
        supermod.graphType.__init__(self, node)
supermod.graphType.subclass = graphTypeSub
# end class graphTypeSub


class nodeTypeSub(supermod.nodeType):
    def __init__(self, id=None, label='', link=None, childnode=None):
        supermod.nodeType.__init__(self, id, label, link, childnode)
supermod.nodeType.subclass = nodeTypeSub
# end class nodeTypeSub


class childnodeTypeSub(supermod.childnodeType):
    def __init__(self, relation=None, refid=None, edgelabel=None):
        supermod.childnodeType.__init__(self, relation, refid, edgelabel)
supermod.childnodeType.subclass = childnodeTypeSub
# end class childnodeTypeSub


class linkTypeSub(supermod.linkType):
    def __init__(self, refid=None, external=None, valueOf_=''):
        supermod.linkType.__init__(self, refid, external)
supermod.linkType.subclass = linkTypeSub
# end class linkTypeSub


class listingTypeSub(supermod.listingType):
    def __init__(self, codeline=None):
        supermod.listingType.__init__(self, codeline)
supermod.listingType.subclass = listingTypeSub
# end class listingTypeSub


class codelineTypeSub(supermod.codelineType):
    def __init__(self, external=None, lineno=None, refkind=None, refid=None, highlight=None):
        supermod.codelineType.__init__(self, external, lineno, refkind, refid, highlight)
supermod.codelineType.subclass = codelineTypeSub
# end class codelineTypeSub


class highlightTypeSub(supermod.highlightType):
    def __init__(self, class_=None, sp=None, ref=None, mixedclass_=None, content_=None):
        supermod.highlightType.__init__(self, mixedclass_, content_)
supermod.highlightType.subclass = highlightTypeSub
# end class highlightTypeSub


class referenceTypeSub(supermod.referenceType):
    def __init__(self, endline=None, startline=None, refid=None, compoundref=None, valueOf_='', mixedclass_=None, content_=None):
        supermod.referenceType.__init__(self, mixedclass_, content_)
supermod.referenceType.subclass = referenceTypeSub
# end class referenceTypeSub


class locationTypeSub(supermod.locationType):
    def __init__(self, bodystart=None, line=None, bodyend=None, bodyfile=None, file=None, valueOf_=''):
        supermod.locationType.__init__(self, bodystart, line, bodyend, bodyfile, file)
supermod.locationType.subclass = locationTypeSub
# end class locationTypeSub


class docSect1TypeSub(supermod.docSect1Type):
    def __init__(self, id=None, title='', para=None, sect2=None, internal=None, mixedclass_=None, content_=None):
        supermod.docSect1Type.__init__(self, mixedclass_, content_)
supermod.docSect1Type.subclass = docSect1TypeSub
# end class docSect1TypeSub


class docSect2TypeSub(supermod.docSect2Type):
    def __init__(self, id=None, title='', para=None, sect3=None, internal=None, mixedclass_=None, content_=None):
        supermod.docSect2Type.__init__(self, mixedclass_, content_)
supermod.docSect2Type.subclass = docSect2TypeSub
# end class docSect2TypeSub


class docSect3TypeSub(supermod.docSect3Type):
    def __init__(self, id=None, title='', para=None, sect4=None, internal=None, mixedclass_=None, content_=None):
        supermod.docSect3Type.__init__(self, mixedclass_, content_)
supermod.docSect3Type.subclass = docSect3TypeSub
# end class docSect3TypeSub


class docSect4TypeSub(supermod.docSect4Type):
    def __init__(self, id=None, title='', para=None, internal=None, mixedclass_=None, content_=None):
        supermod.docSect4Type.__init__(self, mixedclass_, content_)
supermod.docSect4Type.subclass = docSect4TypeSub
# end class docSect4TypeSub


class docInternalTypeSub(supermod.docInternalType):
    def __init__(self, para=None, sect1=None, mixedclass_=None, content_=None):
        supermod.docInternalType.__init__(self, mixedclass_, content_)
supermod.docInternalType.subclass = docInternalTypeSub
# end class docInternalTypeSub


class docInternalS1TypeSub(supermod.docInternalS1Type):
    def __init__(self, para=None, sect2=None, mixedclass_=None, content_=None):
        supermod.docInternalS1Type.__init__(self, mixedclass_, content_)
supermod.docInternalS1Type.subclass = docInternalS1TypeSub
# end class docInternalS1TypeSub


class docInternalS2TypeSub(supermod.docInternalS2Type):
    def __init__(self, para=None, sect3=None, mixedclass_=None, content_=None):
        supermod.docInternalS2Type.__init__(self, mixedclass_, content_)
supermod.docInternalS2Type.subclass = docInternalS2TypeSub
# end class docInternalS2TypeSub


class docInternalS3TypeSub(supermod.docInternalS3Type):
    def __init__(self, para=None, sect3=None, mixedclass_=None, content_=None):
        supermod.docInternalS3Type.__init__(self, mixedclass_, content_)
supermod.docInternalS3Type.subclass = docInternalS3TypeSub
# end class docInternalS3TypeSub


class docInternalS4TypeSub(supermod.docInternalS4Type):
    def __init__(self, para=None, mixedclass_=None, content_=None):
        supermod.docInternalS4Type.__init__(self, mixedclass_, content_)
supermod.docInternalS4Type.subclass = docInternalS4TypeSub
# end class docInternalS4TypeSub


class docURLLinkSub(supermod.docURLLink):
    def __init__(self, url=None, valueOf_='', mixedclass_=None, content_=None):
        supermod.docURLLink.__init__(self, mixedclass_, content_)
supermod.docURLLink.subclass = docURLLinkSub
# end class docURLLinkSub


class docAnchorTypeSub(supermod.docAnchorType):
    def __init__(self, id=None, valueOf_='', mixedclass_=None, content_=None):
        supermod.docAnchorType.__init__(self, mixedclass_, content_)
supermod.docAnchorType.subclass = docAnchorTypeSub
# end class docAnchorTypeSub


class docFormulaTypeSub(supermod.docFormulaType):
    def __init__(self, id=None, valueOf_='', mixedclass_=None, content_=None):
        supermod.docFormulaType.__init__(self, mixedclass_, content_)
supermod.docFormulaType.subclass = docFormulaTypeSub
# end class docFormulaTypeSub


class docIndexEntryTypeSub(supermod.docIndexEntryType):
    def __init__(self, primaryie='', secondaryie=''):
        supermod.docIndexEntryType.__init__(self, primaryie, secondaryie)
supermod.docIndexEntryType.subclass = docIndexEntryTypeSub
# end class docIndexEntryTypeSub


class docListTypeSub(supermod.docListType):
    def __init__(self, listitem=None):
        supermod.docListType.__init__(self, listitem)
supermod.docListType.subclass = docListTypeSub
# end class docListTypeSub


class docListItemTypeSub(supermod.docListItemType):
    def __init__(self, para=None):
        supermod.docListItemType.__init__(self, para)
supermod.docListItemType.subclass = docListItemTypeSub
# end class docListItemTypeSub


class docSimpleSectTypeSub(supermod.docSimpleSectType):
    def __init__(self, kind=None, title=None, para=None):
        supermod.docSimpleSectType.__init__(self, kind, title, para)
supermod.docSimpleSectType.subclass = docSimpleSectTypeSub
# end class docSimpleSectTypeSub


class docVarListEntryTypeSub(supermod.docVarListEntryType):
    def __init__(self, term=None):
        supermod.docVarListEntryType.__init__(self, term)
supermod.docVarListEntryType.subclass = docVarListEntryTypeSub
# end class docVarListEntryTypeSub


class docRefTextTypeSub(supermod.docRefTextType):
    def __init__(self, refid=None, kindref=None, external=None, valueOf_='', mixedclass_=None, content_=None):
        supermod.docRefTextType.__init__(self, mixedclass_, content_)
supermod.docRefTextType.subclass = docRefTextTypeSub
# end class docRefTextTypeSub


class docTableTypeSub(supermod.docTableType):
    def __init__(self, rows=None, cols=None, row=None, caption=None):
        supermod.docTableType.__init__(self, rows, cols, row, caption)
supermod.docTableType.subclass = docTableTypeSub
# end class docTableTypeSub


class docRowTypeSub(supermod.docRowType):
    def __init__(self, entry=None):
        supermod.docRowType.__init__(self, entry)
supermod.docRowType.subclass = docRowTypeSub
# end class docRowTypeSub


class docEntryTypeSub(supermod.docEntryType):
    def __init__(self, thead=None, para=None):
        supermod.docEntryType.__init__(self, thead, para)
supermod.docEntryType.subclass = docEntryTypeSub
# end class docEntryTypeSub


class docHeadingTypeSub(supermod.docHeadingType):
    def __init__(self, level=None, valueOf_='', mixedclass_=None, content_=None):
        supermod.docHeadingType.__init__(self, mixedclass_, content_)
supermod.docHeadingType.subclass = docHeadingTypeSub
# end class docHeadingTypeSub


class docImageTypeSub(supermod.docImageType):
    def __init__(self, width=None, type_=None, name=None, height=None, valueOf_='', mixedclass_=None, content_=None):
        supermod.docImageType.__init__(self, mixedclass_, content_)
supermod.docImageType.subclass = docImageTypeSub
# end class docImageTypeSub


class docDotFileTypeSub(supermod.docDotFileType):
    def __init__(self, name=None, valueOf_='', mixedclass_=None, content_=None):
        supermod.docDotFileType.__init__(self, mixedclass_, content_)
supermod.docDotFileType.subclass = docDotFileTypeSub
# end class docDotFileTypeSub


class docTocItemTypeSub(supermod.docTocItemType):
    def __init__(self, id=None, valueOf_='', mixedclass_=None, content_=None):
        supermod.docTocItemType.__init__(self, mixedclass_, content_)
supermod.docTocItemType.subclass = docTocItemTypeSub
# end class docTocItemTypeSub


class docTocListTypeSub(supermod.docTocListType):
    def __init__(self, tocitem=None):
        supermod.docTocListType.__init__(self, tocitem)
supermod.docTocListType.subclass = docTocListTypeSub
# end class docTocListTypeSub


class docLanguageTypeSub(supermod.docLanguageType):
    def __init__(self, langid=None, para=None):
        supermod.docLanguageType.__init__(self, langid, para)
supermod.docLanguageType.subclass = docLanguageTypeSub
# end class docLanguageTypeSub


class docParamListTypeSub(supermod.docParamListType):
    def __init__(self, kind=None, parameteritem=None):
        supermod.docParamListType.__init__(self, kind, parameteritem)
supermod.docParamListType.subclass = docParamListTypeSub
# end class docParamListTypeSub


class docParamListItemSub(supermod.docParamListItem):
    def __init__(self, parameternamelist=None, parameterdescription=None):
        supermod.docParamListItem.__init__(self, parameternamelist, parameterdescription)
supermod.docParamListItem.subclass = docParamListItemSub
# end class docParamListItemSub


class docParamNameListSub(supermod.docParamNameList):
    def __init__(self, parametername=None):
        supermod.docParamNameList.__init__(self, parametername)
supermod.docParamNameList.subclass = docParamNameListSub
# end class docParamNameListSub


class docParamNameSub(supermod.docParamName):
    def __init__(self, direction=None, ref=None, mixedclass_=None, content_=None):
        supermod.docParamName.__init__(self, mixedclass_, content_)
supermod.docParamName.subclass = docParamNameSub
# end class docParamNameSub


class docXRefSectTypeSub(supermod.docXRefSectType):
    def __init__(self, id=None, xreftitle=None, xrefdescription=None):
        supermod.docXRefSectType.__init__(self, id, xreftitle, xrefdescription)
supermod.docXRefSectType.subclass = docXRefSectTypeSub
# end class docXRefSectTypeSub


class docCopyTypeSub(supermod.docCopyType):
    def __init__(self, link=None, para=None, sect1=None, internal=None):
        supermod.docCopyType.__init__(self, link, para, sect1, internal)
supermod.docCopyType.subclass = docCopyTypeSub
# end class docCopyTypeSub


class docCharTypeSub(supermod.docCharType):
    def __init__(self, char=None, valueOf_=''):
        supermod.docCharType.__init__(self, char)
supermod.docCharType.subclass = docCharTypeSub
# end class docCharTypeSub

class docParaTypeSub(supermod.docParaType):
    def __init__(self, char=None, valueOf_=''):
        supermod.docParaType.__init__(self, char)

        self.parameterlist = []
        self.simplesects = []
        self.content = []

    def buildChildren(self, child_, nodeName_):
        supermod.docParaType.buildChildren(self, child_, nodeName_)

        if child_.nodeType == Node.TEXT_NODE:
            obj_ = self.mixedclass_(MixedContainer.CategoryText,
                MixedContainer.TypeNone, '', child_.nodeValue)
            self.content.append(obj_)
        elif child_.nodeType == Node.ELEMENT_NODE and \
                nodeName_ == "ref":
            obj_ = supermod.docRefTextType.factory()
            obj_.build(child_)
            self.content.append(obj_)
        elif child_.nodeType == Node.ELEMENT_NODE and \
                nodeName_ == 'parameterlist':
            obj_ = supermod.docParamListType.factory()
            obj_.build(child_)
            self.parameterlist.append(obj_)
        elif child_.nodeType == Node.ELEMENT_NODE and \
                nodeName_ == 'simplesect':
            obj_ = supermod.docSimpleSectType.factory()
            obj_.build(child_)
            self.simplesects.append(obj_)


supermod.docParaType.subclass = docParaTypeSub
# end class docParaTypeSub



def parse(inFilename):
    doc = minidom.parse(inFilename)
    rootNode = doc.documentElement
    rootObj = supermod.DoxygenType.factory()
    rootObj.build(rootNode)
    return rootObj



########NEW FILE########
__FILENAME__ = compoundsuper
#!/usr/bin/env python

#
# Generated Thu Jun 11 18:44:25 2009 by generateDS.py.
#

import sys
import getopt
from string import lower as str_lower
from xml.dom import minidom
from xml.dom import Node

#
# User methods
#
# Calls to the methods in these classes are generated by generateDS.py.
# You can replace these methods by re-implementing the following class
#   in a module named generatedssuper.py.

try:
    from generatedssuper import GeneratedsSuper
except ImportError, exp:

    class GeneratedsSuper:
        def format_string(self, input_data, input_name=''):
            return input_data
        def format_integer(self, input_data, input_name=''):
            return '%d' % input_data
        def format_float(self, input_data, input_name=''):
            return '%f' % input_data
        def format_double(self, input_data, input_name=''):
            return '%e' % input_data
        def format_boolean(self, input_data, input_name=''):
            return '%s' % input_data


#
# If you have installed IPython you can uncomment and use the following.
# IPython is available from http://ipython.scipy.org/.
#

## from IPython.Shell import IPShellEmbed
## args = ''
## ipshell = IPShellEmbed(args,
##     banner = 'Dropping into IPython',
##     exit_msg = 'Leaving Interpreter, back to program.')

# Then use the following line where and when you want to drop into the
# IPython shell:
#    ipshell('<some message> -- Entering ipshell.\nHit Ctrl-D to exit')

#
# Globals
#

ExternalEncoding = 'ascii'

#
# Support/utility functions.
#

def showIndent(outfile, level):
    for idx in range(level):
        outfile.write('    ')

def quote_xml(inStr):
    s1 = (isinstance(inStr, basestring) and inStr or
          '%s' % inStr)
    s1 = s1.replace('&', '&amp;')
    s1 = s1.replace('<', '&lt;')
    s1 = s1.replace('>', '&gt;')
    return s1

def quote_attrib(inStr):
    s1 = (isinstance(inStr, basestring) and inStr or
          '%s' % inStr)
    s1 = s1.replace('&', '&amp;')
    s1 = s1.replace('<', '&lt;')
    s1 = s1.replace('>', '&gt;')
    if '"' in s1:
        if "'" in s1:
            s1 = '"%s"' % s1.replace('"', "&quot;")
        else:
            s1 = "'%s'" % s1
    else:
        s1 = '"%s"' % s1
    return s1

def quote_python(inStr):
    s1 = inStr
    if s1.find("'") == -1:
        if s1.find('\n') == -1:
            return "'%s'" % s1
        else:
            return "'''%s'''" % s1
    else:
        if s1.find('"') != -1:
            s1 = s1.replace('"', '\\"')
        if s1.find('\n') == -1:
            return '"%s"' % s1
        else:
            return '"""%s"""' % s1


class MixedContainer:
    # Constants for category:
    CategoryNone = 0
    CategoryText = 1
    CategorySimple = 2
    CategoryComplex = 3
    # Constants for content_type:
    TypeNone = 0
    TypeText = 1
    TypeString = 2
    TypeInteger = 3
    TypeFloat = 4
    TypeDecimal = 5
    TypeDouble = 6
    TypeBoolean = 7
    def __init__(self, category, content_type, name, value):
        self.category = category
        self.content_type = content_type
        self.name = name
        self.value = value
    def getCategory(self):
        return self.category
    def getContenttype(self, content_type):
        return self.content_type
    def getValue(self):
        return self.value
    def getName(self):
        return self.name
    def export(self, outfile, level, name, namespace):
        if self.category == MixedContainer.CategoryText:
            outfile.write(self.value)
        elif self.category == MixedContainer.CategorySimple:
            self.exportSimple(outfile, level, name)
        else:    # category == MixedContainer.CategoryComplex
            self.value.export(outfile, level, namespace,name)
    def exportSimple(self, outfile, level, name):
        if self.content_type == MixedContainer.TypeString:
            outfile.write('<%s>%s</%s>' % (self.name, self.value, self.name))
        elif self.content_type == MixedContainer.TypeInteger or \
                self.content_type == MixedContainer.TypeBoolean:
            outfile.write('<%s>%d</%s>' % (self.name, self.value, self.name))
        elif self.content_type == MixedContainer.TypeFloat or \
                self.content_type == MixedContainer.TypeDecimal:
            outfile.write('<%s>%f</%s>' % (self.name, self.value, self.name))
        elif self.content_type == MixedContainer.TypeDouble:
            outfile.write('<%s>%g</%s>' % (self.name, self.value, self.name))
    def exportLiteral(self, outfile, level, name):
        if self.category == MixedContainer.CategoryText:
            showIndent(outfile, level)
            outfile.write('MixedContainer(%d, %d, "%s", "%s"),\n' % \
                (self.category, self.content_type, self.name, self.value))
        elif self.category == MixedContainer.CategorySimple:
            showIndent(outfile, level)
            outfile.write('MixedContainer(%d, %d, "%s", "%s"),\n' % \
                (self.category, self.content_type, self.name, self.value))
        else:    # category == MixedContainer.CategoryComplex
            showIndent(outfile, level)
            outfile.write('MixedContainer(%d, %d, "%s",\n' % \
                (self.category, self.content_type, self.name,))
            self.value.exportLiteral(outfile, level + 1)
            showIndent(outfile, level)
            outfile.write(')\n')


class _MemberSpec(object):
    def __init__(self, name='', data_type='', container=0):
        self.name = name
        self.data_type = data_type
        self.container = container
    def set_name(self, name): self.name = name
    def get_name(self): return self.name
    def set_data_type(self, data_type): self.data_type = data_type
    def get_data_type(self): return self.data_type
    def set_container(self, container): self.container = container
    def get_container(self): return self.container


#
# Data representation classes.
#

class DoxygenType(GeneratedsSuper):
    subclass = None
    superclass = None
    def __init__(self, version=None, compounddef=None):
        self.version = version
        self.compounddef = compounddef
    def factory(*args_, **kwargs_):
        if DoxygenType.subclass:
            return DoxygenType.subclass(*args_, **kwargs_)
        else:
            return DoxygenType(*args_, **kwargs_)
    factory = staticmethod(factory)
    def get_compounddef(self): return self.compounddef
    def set_compounddef(self, compounddef): self.compounddef = compounddef
    def get_version(self): return self.version
    def set_version(self, version): self.version = version
    def export(self, outfile, level, namespace_='', name_='DoxygenType', namespacedef_=''):
        showIndent(outfile, level)
        outfile.write('<%s%s %s' % (namespace_, name_, namespacedef_, ))
        self.exportAttributes(outfile, level, namespace_, name_='DoxygenType')
        if self.hasContent_():
            outfile.write('>\n')
            self.exportChildren(outfile, level + 1, namespace_, name_)
            showIndent(outfile, level)
            outfile.write('</%s%s>\n' % (namespace_, name_))
        else:
            outfile.write(' />\n')
    def exportAttributes(self, outfile, level, namespace_='', name_='DoxygenType'):
        outfile.write(' version=%s' % (quote_attrib(self.version), ))
    def exportChildren(self, outfile, level, namespace_='', name_='DoxygenType'):
        if self.compounddef:
            self.compounddef.export(outfile, level, namespace_, name_='compounddef')
    def hasContent_(self):
        if (
            self.compounddef is not None
            ):
            return True
        else:
            return False
    def exportLiteral(self, outfile, level, name_='DoxygenType'):
        level += 1
        self.exportLiteralAttributes(outfile, level, name_)
        if self.hasContent_():
            self.exportLiteralChildren(outfile, level, name_)
    def exportLiteralAttributes(self, outfile, level, name_):
        if self.version is not None:
            showIndent(outfile, level)
            outfile.write('version = "%s",\n' % (self.version,))
    def exportLiteralChildren(self, outfile, level, name_):
        if self.compounddef:
            showIndent(outfile, level)
            outfile.write('compounddef=model_.compounddefType(\n')
            self.compounddef.exportLiteral(outfile, level, name_='compounddef')
            showIndent(outfile, level)
            outfile.write('),\n')
    def build(self, node_):
        attrs = node_.attributes
        self.buildAttributes(attrs)
        for child_ in node_.childNodes:
            nodeName_ = child_.nodeName.split(':')[-1]
            self.buildChildren(child_, nodeName_)
    def buildAttributes(self, attrs):
        if attrs.get('version'):
            self.version = attrs.get('version').value
    def buildChildren(self, child_, nodeName_):
        if child_.nodeType == Node.ELEMENT_NODE and \
            nodeName_ == 'compounddef':
            obj_ = compounddefType.factory()
            obj_.build(child_)
            self.set_compounddef(obj_)
# end class DoxygenType


class compounddefType(GeneratedsSuper):
    subclass = None
    superclass = None
    def __init__(self, kind=None, prot=None, id=None, compoundname=None, title=None, basecompoundref=None, derivedcompoundref=None, includes=None, includedby=None, incdepgraph=None, invincdepgraph=None, innerdir=None, innerfile=None, innerclass=None, innernamespace=None, innerpage=None, innergroup=None, templateparamlist=None, sectiondef=None, briefdescription=None, detaileddescription=None, inheritancegraph=None, collaborationgraph=None, programlisting=None, location=None, listofallmembers=None):
        self.kind = kind
        self.prot = prot
        self.id = id
        self.compoundname = compoundname
        self.title = title
        if basecompoundref is None:
            self.basecompoundref = []
        else:
            self.basecompoundref = basecompoundref
        if derivedcompoundref is None:
            self.derivedcompoundref = []
        else:
            self.derivedcompoundref = derivedcompoundref
        if includes is None:
            self.includes = []
        else:
            self.includes = includes
        if includedby is None:
            self.includedby = []
        else:
            self.includedby = includedby
        self.incdepgraph = incdepgraph
        self.invincdepgraph = invincdepgraph
        if innerdir is None:
            self.innerdir = []
        else:
            self.innerdir = innerdir
        if innerfile is None:
            self.innerfile = []
        else:
            self.innerfile = innerfile
        if innerclass is None:
            self.innerclass = []
        else:
            self.innerclass = innerclass
        if innernamespace is None:
            self.innernamespace = []
        else:
            self.innernamespace = innernamespace
        if innerpage is None:
            self.innerpage = []
        else:
            self.innerpage = innerpage
        if innergroup is None:
            self.innergroup = []
        else:
            self.innergroup = innergroup
        self.templateparamlist = templateparamlist
        if sectiondef is None:
            self.sectiondef = []
        else:
            self.sectiondef = sectiondef
        self.briefdescription = briefdescription
        self.detaileddescription = detaileddescription
        self.inheritancegraph = inheritancegraph
        self.collaborationgraph = collaborationgraph
        self.programlisting = programlisting
        self.location = location
        self.listofallmembers = listofallmembers
    def factory(*args_, **kwargs_):
        if compounddefType.subclass:
            return compounddefType.subclass(*args_, **kwargs_)
        else:
            return compounddefType(*args_, **kwargs_)
    factory = staticmethod(factory)
    def get_compoundname(self): return self.compoundname
    def set_compoundname(self, compoundname): self.compoundname = compoundname
    def get_title(self): return self.title
    def set_title(self, title): self.title = title
    def get_basecompoundref(self): return self.basecompoundref
    def set_basecompoundref(self, basecompoundref): self.basecompoundref = basecompoundref
    def add_basecompoundref(self, value): self.basecompoundref.append(value)
    def insert_basecompoundref(self, index, value): self.basecompoundref[index] = value
    def get_derivedcompoundref(self): return self.derivedcompoundref
    def set_derivedcompoundref(self, derivedcompoundref): self.derivedcompoundref = derivedcompoundref
    def add_derivedcompoundref(self, value): self.derivedcompoundref.append(value)
    def insert_derivedcompoundref(self, index, value): self.derivedcompoundref[index] = value
    def get_includes(self): return self.includes
    def set_includes(self, includes): self.includes = includes
    def add_includes(self, value): self.includes.append(value)
    def insert_includes(self, index, value): self.includes[index] = value
    def get_includedby(self): return self.includedby
    def set_includedby(self, includedby): self.includedby = includedby
    def add_includedby(self, value): self.includedby.append(value)
    def insert_includedby(self, index, value): self.includedby[index] = value
    def get_incdepgraph(self): return self.incdepgraph
    def set_incdepgraph(self, incdepgraph): self.incdepgraph = incdepgraph
    def get_invincdepgraph(self): return self.invincdepgraph
    def set_invincdepgraph(self, invincdepgraph): self.invincdepgraph = invincdepgraph
    def get_innerdir(self): return self.innerdir
    def set_innerdir(self, innerdir): self.innerdir = innerdir
    def add_innerdir(self, value): self.innerdir.append(value)
    def insert_innerdir(self, index, value): self.innerdir[index] = value
    def get_innerfile(self): return self.innerfile
    def set_innerfile(self, innerfile): self.innerfile = innerfile
    def add_innerfile(self, value): self.innerfile.append(value)
    def insert_innerfile(self, index, value): self.innerfile[index] = value
    def get_innerclass(self): return self.innerclass
    def set_innerclass(self, innerclass): self.innerclass = innerclass
    def add_innerclass(self, value): self.innerclass.append(value)
    def insert_innerclass(self, index, value): self.innerclass[index] = value
    def get_innernamespace(self): return self.innernamespace
    def set_innernamespace(self, innernamespace): self.innernamespace = innernamespace
    def add_innernamespace(self, value): self.innernamespace.append(value)
    def insert_innernamespace(self, index, value): self.innernamespace[index] = value
    def get_innerpage(self): return self.innerpage
    def set_innerpage(self, innerpage): self.innerpage = innerpage
    def add_innerpage(self, value): self.innerpage.append(value)
    def insert_innerpage(self, index, value): self.innerpage[index] = value
    def get_innergroup(self): return self.innergroup
    def set_innergroup(self, innergroup): self.innergroup = innergroup
    def add_innergroup(self, value): self.innergroup.append(value)
    def insert_innergroup(self, index, value): self.innergroup[index] = value
    def get_templateparamlist(self): return self.templateparamlist
    def set_templateparamlist(self, templateparamlist): self.templateparamlist = templateparamlist
    def get_sectiondef(self): return self.sectiondef
    def set_sectiondef(self, sectiondef): self.sectiondef = sectiondef
    def add_sectiondef(self, value): self.sectiondef.append(value)
    def insert_sectiondef(self, index, value): self.sectiondef[index] = value
    def get_briefdescription(self): return self.briefdescription
    def set_briefdescription(self, briefdescription): self.briefdescription = briefdescription
    def get_detaileddescription(self): return self.detaileddescription
    def set_detaileddescription(self, detaileddescription): self.detaileddescription = detaileddescription
    def get_inheritancegraph(self): return self.inheritancegraph
    def set_inheritancegraph(self, inheritancegraph): self.inheritancegraph = inheritancegraph
    def get_collaborationgraph(self): return self.collaborationgraph
    def set_collaborationgraph(self, collaborationgraph): self.collaborationgraph = collaborationgraph
    def get_programlisting(self): return self.programlisting
    def set_programlisting(self, programlisting): self.programlisting = programlisting
    def get_location(self): return self.location
    def set_location(self, location): self.location = location
    def get_listofallmembers(self): return self.listofallmembers
    def set_listofallmembers(self, listofallmembers): self.listofallmembers = listofallmembers
    def get_kind(self): return self.kind
    def set_kind(self, kind): self.kind = kind
    def get_prot(self): return self.prot
    def set_prot(self, prot): self.prot = prot
    def get_id(self): return self.id
    def set_id(self, id): self.id = id
    def export(self, outfile, level, namespace_='', name_='compounddefType', namespacedef_=''):
        showIndent(outfile, level)
        outfile.write('<%s%s %s' % (namespace_, name_, namespacedef_, ))
        self.exportAttributes(outfile, level, namespace_, name_='compounddefType')
        if self.hasContent_():
            outfile.write('>\n')
            self.exportChildren(outfile, level + 1, namespace_, name_)
            showIndent(outfile, level)
            outfile.write('</%s%s>\n' % (namespace_, name_))
        else:
            outfile.write(' />\n')
    def exportAttributes(self, outfile, level, namespace_='', name_='compounddefType'):
        if self.kind is not None:
            outfile.write(' kind=%s' % (quote_attrib(self.kind), ))
        if self.prot is not None:
            outfile.write(' prot=%s' % (quote_attrib(self.prot), ))
        if self.id is not None:
            outfile.write(' id=%s' % (self.format_string(quote_attrib(self.id).encode(ExternalEncoding), input_name='id'), ))
    def exportChildren(self, outfile, level, namespace_='', name_='compounddefType'):
        if self.compoundname is not None:
            showIndent(outfile, level)
            outfile.write('<%scompoundname>%s</%scompoundname>\n' % (namespace_, self.format_string(quote_xml(self.compoundname).encode(ExternalEncoding), input_name='compoundname'), namespace_))
        if self.title is not None:
            showIndent(outfile, level)
            outfile.write('<%stitle>%s</%stitle>\n' % (namespace_, self.format_string(quote_xml(self.title).encode(ExternalEncoding), input_name='title'), namespace_))
        for basecompoundref_ in self.basecompoundref:
            basecompoundref_.export(outfile, level, namespace_, name_='basecompoundref')
        for derivedcompoundref_ in self.derivedcompoundref:
            derivedcompoundref_.export(outfile, level, namespace_, name_='derivedcompoundref')
        for includes_ in self.includes:
            includes_.export(outfile, level, namespace_, name_='includes')
        for includedby_ in self.includedby:
            includedby_.export(outfile, level, namespace_, name_='includedby')
        if self.incdepgraph:
            self.incdepgraph.export(outfile, level, namespace_, name_='incdepgraph')
        if self.invincdepgraph:
            self.invincdepgraph.export(outfile, level, namespace_, name_='invincdepgraph')
        for innerdir_ in self.innerdir:
            innerdir_.export(outfile, level, namespace_, name_='innerdir')
        for innerfile_ in self.innerfile:
            innerfile_.export(outfile, level, namespace_, name_='innerfile')
        for innerclass_ in self.innerclass:
            innerclass_.export(outfile, level, namespace_, name_='innerclass')
        for innernamespace_ in self.innernamespace:
            innernamespace_.export(outfile, level, namespace_, name_='innernamespace')
        for innerpage_ in self.innerpage:
            innerpage_.export(outfile, level, namespace_, name_='innerpage')
        for innergroup_ in self.innergroup:
            innergroup_.export(outfile, level, namespace_, name_='innergroup')
        if self.templateparamlist:
            self.templateparamlist.export(outfile, level, namespace_, name_='templateparamlist')
        for sectiondef_ in self.sectiondef:
            sectiondef_.export(outfile, level, namespace_, name_='sectiondef')
        if self.briefdescription:
            self.briefdescription.export(outfile, level, namespace_, name_='briefdescription')
        if self.detaileddescription:
            self.detaileddescription.export(outfile, level, namespace_, name_='detaileddescription')
        if self.inheritancegraph:
            self.inheritancegraph.export(outfile, level, namespace_, name_='inheritancegraph')
        if self.collaborationgraph:
            self.collaborationgraph.export(outfile, level, namespace_, name_='collaborationgraph')
        if self.programlisting:
            self.programlisting.export(outfile, level, namespace_, name_='programlisting')
        if self.location:
            self.location.export(outfile, level, namespace_, name_='location')
        if self.listofallmembers:
            self.listofallmembers.export(outfile, level, namespace_, name_='listofallmembers')
    def hasContent_(self):
        if (
            self.compoundname is not None or
            self.title is not None or
            self.basecompoundref is not None or
            self.derivedcompoundref is not None or
            self.includes is not None or
            self.includedby is not None or
            self.incdepgraph is not None or
            self.invincdepgraph is not None or
            self.innerdir is not None or
            self.innerfile is not None or
            self.innerclass is not None or
            self.innernamespace is not None or
            self.innerpage is not None or
            self.innergroup is not None or
            self.templateparamlist is not None or
            self.sectiondef is not None or
            self.briefdescription is not None or
            self.detaileddescription is not None or
            self.inheritancegraph is not None or
            self.collaborationgraph is not None or
            self.programlisting is not None or
            self.location is not None or
            self.listofallmembers is not None
            ):
            return True
        else:
            return False
    def exportLiteral(self, outfile, level, name_='compounddefType'):
        level += 1
        self.exportLiteralAttributes(outfile, level, name_)
        if self.hasContent_():
            self.exportLiteralChildren(outfile, level, name_)
    def exportLiteralAttributes(self, outfile, level, name_):
        if self.kind is not None:
            showIndent(outfile, level)
            outfile.write('kind = "%s",\n' % (self.kind,))
        if self.prot is not None:
            showIndent(outfile, level)
            outfile.write('prot = "%s",\n' % (self.prot,))
        if self.id is not None:
            showIndent(outfile, level)
            outfile.write('id = %s,\n' % (self.id,))
    def exportLiteralChildren(self, outfile, level, name_):
        showIndent(outfile, level)
        outfile.write('compoundname=%s,\n' % quote_python(self.compoundname).encode(ExternalEncoding))
        if self.title:
            showIndent(outfile, level)
            outfile.write('title=model_.xsd_string(\n')
            self.title.exportLiteral(outfile, level, name_='title')
            showIndent(outfile, level)
            outfile.write('),\n')
        showIndent(outfile, level)
        outfile.write('basecompoundref=[\n')
        level += 1
        for basecompoundref in self.basecompoundref:
            showIndent(outfile, level)
            outfile.write('model_.basecompoundref(\n')
            basecompoundref.exportLiteral(outfile, level, name_='basecompoundref')
            showIndent(outfile, level)
            outfile.write('),\n')
        level -= 1
        showIndent(outfile, level)
        outfile.write('],\n')
        showIndent(outfile, level)
        outfile.write('derivedcompoundref=[\n')
        level += 1
        for derivedcompoundref in self.derivedcompoundref:
            showIndent(outfile, level)
            outfile.write('model_.derivedcompoundref(\n')
            derivedcompoundref.exportLiteral(outfile, level, name_='derivedcompoundref')
            showIndent(outfile, level)
            outfile.write('),\n')
        level -= 1
        showIndent(outfile, level)
        outfile.write('],\n')
        showIndent(outfile, level)
        outfile.write('includes=[\n')
        level += 1
        for includes in self.includes:
            showIndent(outfile, level)
            outfile.write('model_.includes(\n')
            includes.exportLiteral(outfile, level, name_='includes')
            showIndent(outfile, level)
            outfile.write('),\n')
        level -= 1
        showIndent(outfile, level)
        outfile.write('],\n')
        showIndent(outfile, level)
        outfile.write('includedby=[\n')
        level += 1
        for includedby in self.includedby:
            showIndent(outfile, level)
            outfile.write('model_.includedby(\n')
            includedby.exportLiteral(outfile, level, name_='includedby')
            showIndent(outfile, level)
            outfile.write('),\n')
        level -= 1
        showIndent(outfile, level)
        outfile.write('],\n')
        if self.incdepgraph:
            showIndent(outfile, level)
            outfile.write('incdepgraph=model_.graphType(\n')
            self.incdepgraph.exportLiteral(outfile, level, name_='incdepgraph')
            showIndent(outfile, level)
            outfile.write('),\n')
        if self.invincdepgraph:
            showIndent(outfile, level)
            outfile.write('invincdepgraph=model_.graphType(\n')
            self.invincdepgraph.exportLiteral(outfile, level, name_='invincdepgraph')
            showIndent(outfile, level)
            outfile.write('),\n')
        showIndent(outfile, level)
        outfile.write('innerdir=[\n')
        level += 1
        for innerdir in self.innerdir:
            showIndent(outfile, level)
            outfile.write('model_.innerdir(\n')
            innerdir.exportLiteral(outfile, level, name_='innerdir')
            showIndent(outfile, level)
            outfile.write('),\n')
        level -= 1
        showIndent(outfile, level)
        outfile.write('],\n')
        showIndent(outfile, level)
        outfile.write('innerfile=[\n')
        level += 1
        for innerfile in self.innerfile:
            showIndent(outfile, level)
            outfile.write('model_.innerfile(\n')
            innerfile.exportLiteral(outfile, level, name_='innerfile')
            showIndent(outfile, level)
            outfile.write('),\n')
        level -= 1
        showIndent(outfile, level)
        outfile.write('],\n')
        showIndent(outfile, level)
        outfile.write('innerclass=[\n')
        level += 1
        for innerclass in self.innerclass:
            showIndent(outfile, level)
            outfile.write('model_.innerclass(\n')
            innerclass.exportLiteral(outfile, level, name_='innerclass')
            showIndent(outfile, level)
            outfile.write('),\n')
        level -= 1
        showIndent(outfile, level)
        outfile.write('],\n')
        showIndent(outfile, level)
        outfile.write('innernamespace=[\n')
        level += 1
        for innernamespace in self.innernamespace:
            showIndent(outfile, level)
            outfile.write('model_.innernamespace(\n')
            innernamespace.exportLiteral(outfile, level, name_='innernamespace')
            showIndent(outfile, level)
            outfile.write('),\n')
        level -= 1
        showIndent(outfile, level)
        outfile.write('],\n')
        showIndent(outfile, level)
        outfile.write('innerpage=[\n')
        level += 1
        for innerpage in self.innerpage:
            showIndent(outfile, level)
            outfile.write('model_.innerpage(\n')
            innerpage.exportLiteral(outfile, level, name_='innerpage')
            showIndent(outfile, level)
            outfile.write('),\n')
        level -= 1
        showIndent(outfile, level)
        outfile.write('],\n')
        showIndent(outfile, level)
        outfile.write('innergroup=[\n')
        level += 1
        for innergroup in self.innergroup:
            showIndent(outfile, level)
            outfile.write('model_.innergroup(\n')
            innergroup.exportLiteral(outfile, level, name_='innergroup')
            showIndent(outfile, level)
            outfile.write('),\n')
        level -= 1
        showIndent(outfile, level)
        outfile.write('],\n')
        if self.templateparamlist:
            showIndent(outfile, level)
            outfile.write('templateparamlist=model_.templateparamlistType(\n')
            self.templateparamlist.exportLiteral(outfile, level, name_='templateparamlist')
            showIndent(outfile, level)
            outfile.write('),\n')
        showIndent(outfile, level)
        outfile.write('sectiondef=[\n')
        level += 1
        for sectiondef in self.sectiondef:
            showIndent(outfile, level)
            outfile.write('model_.sectiondef(\n')
            sectiondef.exportLiteral(outfile, level, name_='sectiondef')
            showIndent(outfile, level)
            outfile.write('),\n')
        level -= 1
        showIndent(outfile, level)
        outfile.write('],\n')
        if self.briefdescription:
            showIndent(outfile, level)
            outfile.write('briefdescription=model_.descriptionType(\n')
            self.briefdescription.exportLiteral(outfile, level, name_='briefdescription')
            showIndent(outfile, level)
            outfile.write('),\n')
        if self.detaileddescription:
            showIndent(outfile, level)
            outfile.write('detaileddescription=model_.descriptionType(\n')
            self.detaileddescription.exportLiteral(outfile, level, name_='detaileddescription')
            showIndent(outfile, level)
            outfile.write('),\n')
        if self.inheritancegraph:
            showIndent(outfile, level)
            outfile.write('inheritancegraph=model_.graphType(\n')
            self.inheritancegraph.exportLiteral(outfile, level, name_='inheritancegraph')
            showIndent(outfile, level)
            outfile.write('),\n')
        if self.collaborationgraph:
            showIndent(outfile, level)
            outfile.write('collaborationgraph=model_.graphType(\n')
            self.collaborationgraph.exportLiteral(outfile, level, name_='collaborationgraph')
            showIndent(outfile, level)
            outfile.write('),\n')
        if self.programlisting:
            showIndent(outfile, level)
            outfile.write('programlisting=model_.listingType(\n')
            self.programlisting.exportLiteral(outfile, level, name_='programlisting')
            showIndent(outfile, level)
            outfile.write('),\n')
        if self.location:
            showIndent(outfile, level)
            outfile.write('location=model_.locationType(\n')
            self.location.exportLiteral(outfile, level, name_='location')
            showIndent(outfile, level)
            outfile.write('),\n')
        if self.listofallmembers:
            showIndent(outfile, level)
            outfile.write('listofallmembers=model_.listofallmembersType(\n')
            self.listofallmembers.exportLiteral(outfile, level, name_='listofallmembers')
            showIndent(outfile, level)
            outfile.write('),\n')
    def build(self, node_):
        attrs = node_.attributes
        self.buildAttributes(attrs)
        for child_ in node_.childNodes:
            nodeName_ = child_.nodeName.split(':')[-1]
            self.buildChildren(child_, nodeName_)
    def buildAttributes(self, attrs):
        if attrs.get('kind'):
            self.kind = attrs.get('kind').value
        if attrs.get('prot'):
            self.prot = attrs.get('prot').value
        if attrs.get('id'):
            self.id = attrs.get('id').value
    def buildChildren(self, child_, nodeName_):
        if child_.nodeType == Node.ELEMENT_NODE and \
            nodeName_ == 'compoundname':
            compoundname_ = ''
            for text__content_ in child_.childNodes:
                compoundname_ += text__content_.nodeValue
            self.compoundname = compoundname_
        elif child_.nodeType == Node.ELEMENT_NODE and \
            nodeName_ == 'title':
            obj_ = docTitleType.factory()
            obj_.build(child_)
            self.set_title(obj_)
        elif child_.nodeType == Node.ELEMENT_NODE and \
            nodeName_ == 'basecompoundref':
            obj_ = compoundRefType.factory()
            obj_.build(child_)
            self.basecompoundref.append(obj_)
        elif child_.nodeType == Node.ELEMENT_NODE and \
            nodeName_ == 'derivedcompoundref':
            obj_ = compoundRefType.factory()
            obj_.build(child_)
            self.derivedcompoundref.append(obj_)
        elif child_.nodeType == Node.ELEMENT_NODE and \
            nodeName_ == 'includes':
            obj_ = incType.factory()
            obj_.build(child_)
            self.includes.append(obj_)
        elif child_.nodeType == Node.ELEMENT_NODE and \
            nodeName_ == 'includedby':
            obj_ = incType.factory()
            obj_.build(child_)
            self.includedby.append(obj_)
        elif child_.nodeType == Node.ELEMENT_NODE and \
            nodeName_ == 'incdepgraph':
            obj_ = graphType.factory()
            obj_.build(child_)
            self.set_incdepgraph(obj_)
        elif child_.nodeType == Node.ELEMENT_NODE and \
            nodeName_ == 'invincdepgraph':
            obj_ = graphType.factory()
            obj_.build(child_)
            self.set_invincdepgraph(obj_)
        elif child_.nodeType == Node.ELEMENT_NODE and \
            nodeName_ == 'innerdir':
            obj_ = refType.factory()
            obj_.build(child_)
            self.innerdir.append(obj_)
        elif child_.nodeType == Node.ELEMENT_NODE and \
            nodeName_ == 'innerfile':
            obj_ = refType.factory()
            obj_.build(child_)
            self.innerfile.append(obj_)
        elif child_.nodeType == Node.ELEMENT_NODE and \
            nodeName_ == 'innerclass':
            obj_ = refType.factory()
            obj_.build(child_)
            self.innerclass.append(obj_)
        elif child_.nodeType == Node.ELEMENT_NODE and \
            nodeName_ == 'innernamespace':
            obj_ = refType.factory()
            obj_.build(child_)
            self.innernamespace.append(obj_)
        elif child_.nodeType == Node.ELEMENT_NODE and \
            nodeName_ == 'innerpage':
            obj_ = refType.factory()
            obj_.build(child_)
            self.innerpage.append(obj_)
        elif child_.nodeType == Node.ELEMENT_NODE and \
            nodeName_ == 'innergroup':
            obj_ = refType.factory()
            obj_.build(child_)
            self.innergroup.append(obj_)
        elif child_.nodeType == Node.ELEMENT_NODE and \
            nodeName_ == 'templateparamlist':
            obj_ = templateparamlistType.factory()
            obj_.build(child_)
            self.set_templateparamlist(obj_)
        elif child_.nodeType == Node.ELEMENT_NODE and \
            nodeName_ == 'sectiondef':
            obj_ = sectiondefType.factory()
            obj_.build(child_)
            self.sectiondef.append(obj_)
        elif child_.nodeType == Node.ELEMENT_NODE and \
            nodeName_ == 'briefdescription':
            obj_ = descriptionType.factory()
            obj_.build(child_)
            self.set_briefdescription(obj_)
        elif child_.nodeType == Node.ELEMENT_NODE and \
            nodeName_ == 'detaileddescription':
            obj_ = descriptionType.factory()
            obj_.build(child_)
            self.set_detaileddescription(obj_)
        elif child_.nodeType == Node.ELEMENT_NODE and \
            nodeName_ == 'inheritancegraph':
            obj_ = graphType.factory()
            obj_.build(child_)
            self.set_inheritancegraph(obj_)
        elif child_.nodeType == Node.ELEMENT_NODE and \
            nodeName_ == 'collaborationgraph':
            obj_ = graphType.factory()
            obj_.build(child_)
            self.set_collaborationgraph(obj_)
        elif child_.nodeType == Node.ELEMENT_NODE and \
            nodeName_ == 'programlisting':
            obj_ = listingType.factory()
            obj_.build(child_)
            self.set_programlisting(obj_)
        elif child_.nodeType == Node.ELEMENT_NODE and \
            nodeName_ == 'location':
            obj_ = locationType.factory()
            obj_.build(child_)
            self.set_location(obj_)
        elif child_.nodeType == Node.ELEMENT_NODE and \
            nodeName_ == 'listofallmembers':
            obj_ = listofallmembersType.factory()
            obj_.build(child_)
            self.set_listofallmembers(obj_)
# end class compounddefType


class listofallmembersType(GeneratedsSuper):
    subclass = None
    superclass = None
    def __init__(self, member=None):
        if member is None:
            self.member = []
        else:
            self.member = member
    def factory(*args_, **kwargs_):
        if listofallmembersType.subclass:
            return listofallmembersType.subclass(*args_, **kwargs_)
        else:
            return listofallmembersType(*args_, **kwargs_)
    factory = staticmethod(factory)
    def get_member(self): return self.member
    def set_member(self, member): self.member = member
    def add_member(self, value): self.member.append(value)
    def insert_member(self, index, value): self.member[index] = value
    def export(self, outfile, level, namespace_='', name_='listofallmembersType', namespacedef_=''):
        showIndent(outfile, level)
        outfile.write('<%s%s %s' % (namespace_, name_, namespacedef_, ))
        self.exportAttributes(outfile, level, namespace_, name_='listofallmembersType')
        if self.hasContent_():
            outfile.write('>\n')
            self.exportChildren(outfile, level + 1, namespace_, name_)
            showIndent(outfile, level)
            outfile.write('</%s%s>\n' % (namespace_, name_))
        else:
            outfile.write(' />\n')
    def exportAttributes(self, outfile, level, namespace_='', name_='listofallmembersType'):
        pass
    def exportChildren(self, outfile, level, namespace_='', name_='listofallmembersType'):
        for member_ in self.member:
            member_.export(outfile, level, namespace_, name_='member')
    def hasContent_(self):
        if (
            self.member is not None
            ):
            return True
        else:
            return False
    def exportLiteral(self, outfile, level, name_='listofallmembersType'):
        level += 1
        self.exportLiteralAttributes(outfile, level, name_)
        if self.hasContent_():
            self.exportLiteralChildren(outfile, level, name_)
    def exportLiteralAttributes(self, outfile, level, name_):
        pass
    def exportLiteralChildren(self, outfile, level, name_):
        showIndent(outfile, level)
        outfile.write('member=[\n')
        level += 1
        for member in self.member:
            showIndent(outfile, level)
            outfile.write('model_.member(\n')
            member.exportLiteral(outfile, level, name_='member')
            showIndent(outfile, level)
            outfile.write('),\n')
        level -= 1
        showIndent(outfile, level)
        outfile.write('],\n')
    def build(self, node_):
        attrs = node_.attributes
        self.buildAttributes(attrs)
        for child_ in node_.childNodes:
            nodeName_ = child_.nodeName.split(':')[-1]
            self.buildChildren(child_, nodeName_)
    def buildAttributes(self, attrs):
        pass
    def buildChildren(self, child_, nodeName_):
        if child_.nodeType == Node.ELEMENT_NODE and \
            nodeName_ == 'member':
            obj_ = memberRefType.factory()
            obj_.build(child_)
            self.member.append(obj_)
# end class listofallmembersType


class memberRefType(GeneratedsSuper):
    subclass = None
    superclass = None
    def __init__(self, virt=None, prot=None, refid=None, ambiguityscope=None, scope=None, name=None):
        self.virt = virt
        self.prot = prot
        self.refid = refid
        self.ambiguityscope = ambiguityscope
        self.scope = scope
        self.name = name
    def factory(*args_, **kwargs_):
        if memberRefType.subclass:
            return memberRefType.subclass(*args_, **kwargs_)
        else:
            return memberRefType(*args_, **kwargs_)
    factory = staticmethod(factory)
    def get_scope(self): return self.scope
    def set_scope(self, scope): self.scope = scope
    def get_name(self): return self.name
    def set_name(self, name): self.name = name
    def get_virt(self): return self.virt
    def set_virt(self, virt): self.virt = virt
    def get_prot(self): return self.prot
    def set_prot(self, prot): self.prot = prot
    def get_refid(self): return self.refid
    def set_refid(self, refid): self.refid = refid
    def get_ambiguityscope(self): return self.ambiguityscope
    def set_ambiguityscope(self, ambiguityscope): self.ambiguityscope = ambiguityscope
    def export(self, outfile, level, namespace_='', name_='memberRefType', namespacedef_=''):
        showIndent(outfile, level)
        outfile.write('<%s%s %s' % (namespace_, name_, namespacedef_, ))
        self.exportAttributes(outfile, level, namespace_, name_='memberRefType')
        if self.hasContent_():
            outfile.write('>\n')
            self.exportChildren(outfile, level + 1, namespace_, name_)
            showIndent(outfile, level)
            outfile.write('</%s%s>\n' % (namespace_, name_))
        else:
            outfile.write(' />\n')
    def exportAttributes(self, outfile, level, namespace_='', name_='memberRefType'):
        if self.virt is not None:
            outfile.write(' virt=%s' % (quote_attrib(self.virt), ))
        if self.prot is not None:
            outfile.write(' prot=%s' % (quote_attrib(self.prot), ))
        if self.refid is not None:
            outfile.write(' refid=%s' % (self.format_string(quote_attrib(self.refid).encode(ExternalEncoding), input_name='refid'), ))
        if self.ambiguityscope is not None:
            outfile.write(' ambiguityscope=%s' % (self.format_string(quote_attrib(self.ambiguityscope).encode(ExternalEncoding), input_name='ambiguityscope'), ))
    def exportChildren(self, outfile, level, namespace_='', name_='memberRefType'):
        if self.scope is not None:
            showIndent(outfile, level)
            outfile.write('<%sscope>%s</%sscope>\n' % (namespace_, self.format_string(quote_xml(self.scope).encode(ExternalEncoding), input_name='scope'), namespace_))
        if self.name is not None:
            showIndent(outfile, level)
            outfile.write('<%sname>%s</%sname>\n' % (namespace_, self.format_string(quote_xml(self.name).encode(ExternalEncoding), input_name='name'), namespace_))
    def hasContent_(self):
        if (
            self.scope is not None or
            self.name is not None
            ):
            return True
        else:
            return False
    def exportLiteral(self, outfile, level, name_='memberRefType'):
        level += 1
        self.exportLiteralAttributes(outfile, level, name_)
        if self.hasContent_():
            self.exportLiteralChildren(outfile, level, name_)
    def exportLiteralAttributes(self, outfile, level, name_):
        if self.virt is not None:
            showIndent(outfile, level)
            outfile.write('virt = "%s",\n' % (self.virt,))
        if self.prot is not None:
            showIndent(outfile, level)
            outfile.write('prot = "%s",\n' % (self.prot,))
        if self.refid is not None:
            showIndent(outfile, level)
            outfile.write('refid = %s,\n' % (self.refid,))
        if self.ambiguityscope is not None:
            showIndent(outfile, level)
            outfile.write('ambiguityscope = %s,\n' % (self.ambiguityscope,))
    def exportLiteralChildren(self, outfile, level, name_):
        showIndent(outfile, level)
        outfile.write('scope=%s,\n' % quote_python(self.scope).encode(ExternalEncoding))
        showIndent(outfile, level)
        outfile.write('name=%s,\n' % quote_python(self.name).encode(ExternalEncoding))
    def build(self, node_):
        attrs = node_.attributes
        self.buildAttributes(attrs)
        for child_ in node_.childNodes:
            nodeName_ = child_.nodeName.split(':')[-1]
            self.buildChildren(child_, nodeName_)
    def buildAttributes(self, attrs):
        if attrs.get('virt'):
            self.virt = attrs.get('virt').value
        if attrs.get('prot'):
            self.prot = attrs.get('prot').value
        if attrs.get('refid'):
            self.refid = attrs.get('refid').value
        if attrs.get('ambiguityscope'):
            self.ambiguityscope = attrs.get('ambiguityscope').value
    def buildChildren(self, child_, nodeName_):
        if child_.nodeType == Node.ELEMENT_NODE and \
            nodeName_ == 'scope':
            scope_ = ''
            for text__content_ in child_.childNodes:
                scope_ += text__content_.nodeValue
            self.scope = scope_
        elif child_.nodeType == Node.ELEMENT_NODE and \
            nodeName_ == 'name':
            name_ = ''
            for text__content_ in child_.childNodes:
                name_ += text__content_.nodeValue
            self.name = name_
# end class memberRefType


class scope(GeneratedsSuper):
    subclass = None
    superclass = None
    def __init__(self, valueOf_=''):
        self.valueOf_ = valueOf_
    def factory(*args_, **kwargs_):
        if scope.subclass:
            return scope.subclass(*args_, **kwargs_)
        else:
            return scope(*args_, **kwargs_)
    factory = staticmethod(factory)
    def getValueOf_(self): return self.valueOf_
    def setValueOf_(self, valueOf_): self.valueOf_ = valueOf_
    def export(self, outfile, level, namespace_='', name_='scope', namespacedef_=''):
        showIndent(outfile, level)
        outfile.write('<%s%s %s' % (namespace_, name_, namespacedef_, ))
        self.exportAttributes(outfile, level, namespace_, name_='scope')
        if self.hasContent_():
            outfile.write('>\n')
            self.exportChildren(outfile, level + 1, namespace_, name_)
            showIndent(outfile, level)
            outfile.write('</%s%s>\n' % (namespace_, name_))
        else:
            outfile.write(' />\n')
    def exportAttributes(self, outfile, level, namespace_='', name_='scope'):
        pass
    def exportChildren(self, outfile, level, namespace_='', name_='scope'):
        if self.valueOf_.find('![CDATA')>-1:
            value=quote_xml('%s' % self.valueOf_)
            value=value.replace('![CDATA','<![CDATA')
            value=value.replace(']]',']]>')
            outfile.write(value)
        else:
            outfile.write(quote_xml('%s' % self.valueOf_))
    def hasContent_(self):
        if (
            self.valueOf_ is not None
            ):
            return True
        else:
            return False
    def exportLiteral(self, outfile, level, name_='scope'):
        level += 1
        self.exportLiteralAttributes(outfile, level, name_)
        if self.hasContent_():
            self.exportLiteralChildren(outfile, level, name_)
    def exportLiteralAttributes(self, outfile, level, name_):
        pass
    def exportLiteralChildren(self, outfile, level, name_):
        showIndent(outfile, level)
        outfile.write('valueOf_ = "%s",\n' % (self.valueOf_,))
    def build(self, node_):
        attrs = node_.attributes
        self.buildAttributes(attrs)
        self.valueOf_ = ''
        for child_ in node_.childNodes:
            nodeName_ = child_.nodeName.split(':')[-1]
            self.buildChildren(child_, nodeName_)
    def buildAttributes(self, attrs):
        pass
    def buildChildren(self, child_, nodeName_):
        if child_.nodeType == Node.TEXT_NODE:
            self.valueOf_ += child_.nodeValue
        elif child_.nodeType == Node.CDATA_SECTION_NODE:
            self.valueOf_ += '![CDATA['+child_.nodeValue+']]'
# end class scope


class name(GeneratedsSuper):
    subclass = None
    superclass = None
    def __init__(self, valueOf_=''):
        self.valueOf_ = valueOf_
    def factory(*args_, **kwargs_):
        if name.subclass:
            return name.subclass(*args_, **kwargs_)
        else:
            return name(*args_, **kwargs_)
    factory = staticmethod(factory)
    def getValueOf_(self): return self.valueOf_
    def setValueOf_(self, valueOf_): self.valueOf_ = valueOf_
    def export(self, outfile, level, namespace_='', name_='name', namespacedef_=''):
        showIndent(outfile, level)
        outfile.write('<%s%s %s' % (namespace_, name_, namespacedef_, ))
        self.exportAttributes(outfile, level, namespace_, name_='name')
        if self.hasContent_():
            outfile.write('>\n')
            self.exportChildren(outfile, level + 1, namespace_, name_)
            showIndent(outfile, level)
            outfile.write('</%s%s>\n' % (namespace_, name_))
        else:
            outfile.write(' />\n')
    def exportAttributes(self, outfile, level, namespace_='', name_='name'):
        pass
    def exportChildren(self, outfile, level, namespace_='', name_='name'):
        if self.valueOf_.find('![CDATA')>-1:
            value=quote_xml('%s' % self.valueOf_)
            value=value.replace('![CDATA','<![CDATA')
            value=value.replace(']]',']]>')
            outfile.write(value)
        else:
            outfile.write(quote_xml('%s' % self.valueOf_))
    def hasContent_(self):
        if (
            self.valueOf_ is not None
            ):
            return True
        else:
            return False
    def exportLiteral(self, outfile, level, name_='name'):
        level += 1
        self.exportLiteralAttributes(outfile, level, name_)
        if self.hasContent_():
            self.exportLiteralChildren(outfile, level, name_)
    def exportLiteralAttributes(self, outfile, level, name_):
        pass
    def exportLiteralChildren(self, outfile, level, name_):
        showIndent(outfile, level)
        outfile.write('valueOf_ = "%s",\n' % (self.valueOf_,))
    def build(self, node_):
        attrs = node_.attributes
        self.buildAttributes(attrs)
        self.valueOf_ = ''
        for child_ in node_.childNodes:
            nodeName_ = child_.nodeName.split(':')[-1]
            self.buildChildren(child_, nodeName_)
    def buildAttributes(self, attrs):
        pass
    def buildChildren(self, child_, nodeName_):
        if child_.nodeType == Node.TEXT_NODE:
            self.valueOf_ += child_.nodeValue
        elif child_.nodeType == Node.CDATA_SECTION_NODE:
            self.valueOf_ += '![CDATA['+child_.nodeValue+']]'
# end class name


class compoundRefType(GeneratedsSuper):
    subclass = None
    superclass = None
    def __init__(self, virt=None, prot=None, refid=None, valueOf_='', mixedclass_=None, content_=None):
        self.virt = virt
        self.prot = prot
        self.refid = refid
        if mixedclass_ is None:
            self.mixedclass_ = MixedContainer
        else:
            self.mixedclass_ = mixedclass_
        if content_ is None:
            self.content_ = []
        else:
            self.content_ = content_
    def factory(*args_, **kwargs_):
        if compoundRefType.subclass:
            return compoundRefType.subclass(*args_, **kwargs_)
        else:
            return compoundRefType(*args_, **kwargs_)
    factory = staticmethod(factory)
    def get_virt(self): return self.virt
    def set_virt(self, virt): self.virt = virt
    def get_prot(self): return self.prot
    def set_prot(self, prot): self.prot = prot
    def get_refid(self): return self.refid
    def set_refid(self, refid): self.refid = refid
    def getValueOf_(self): return self.valueOf_
    def setValueOf_(self, valueOf_): self.valueOf_ = valueOf_
    def export(self, outfile, level, namespace_='', name_='compoundRefType', namespacedef_=''):
        showIndent(outfile, level)
        outfile.write('<%s%s %s' % (namespace_, name_, namespacedef_, ))
        self.exportAttributes(outfile, level, namespace_, name_='compoundRefType')
        outfile.write('>')
        self.exportChildren(outfile, level + 1, namespace_, name_)
        outfile.write('</%s%s>\n' % (namespace_, name_))
    def exportAttributes(self, outfile, level, namespace_='', name_='compoundRefType'):
        if self.virt is not None:
            outfile.write(' virt=%s' % (quote_attrib(self.virt), ))
        if self.prot is not None:
            outfile.write(' prot=%s' % (quote_attrib(self.prot), ))
        if self.refid is not None:
            outfile.write(' refid=%s' % (self.format_string(quote_attrib(self.refid).encode(ExternalEncoding), input_name='refid'), ))
    def exportChildren(self, outfile, level, namespace_='', name_='compoundRefType'):
        if self.valueOf_.find('![CDATA')>-1:
            value=quote_xml('%s' % self.valueOf_)
            value=value.replace('![CDATA','<![CDATA')
            value=value.replace(']]',']]>')
            outfile.write(value)
        else:
            outfile.write(quote_xml('%s' % self.valueOf_))
    def hasContent_(self):
        if (
            self.valueOf_ is not None
            ):
            return True
        else:
            return False
    def exportLiteral(self, outfile, level, name_='compoundRefType'):
        level += 1
        self.exportLiteralAttributes(outfile, level, name_)
        if self.hasContent_():
            self.exportLiteralChildren(outfile, level, name_)
    def exportLiteralAttributes(self, outfile, level, name_):
        if self.virt is not None:
            showIndent(outfile, level)
            outfile.write('virt = "%s",\n' % (self.virt,))
        if self.prot is not None:
            showIndent(outfile, level)
            outfile.write('prot = "%s",\n' % (self.prot,))
        if self.refid is not None:
            showIndent(outfile, level)
            outfile.write('refid = %s,\n' % (self.refid,))
    def exportLiteralChildren(self, outfile, level, name_):
        showIndent(outfile, level)
        outfile.write('valueOf_ = "%s",\n' % (self.valueOf_,))
    def build(self, node_):
        attrs = node_.attributes
        self.buildAttributes(attrs)
        self.valueOf_ = ''
        for child_ in node_.childNodes:
            nodeName_ = child_.nodeName.split(':')[-1]
            self.buildChildren(child_, nodeName_)
    def buildAttributes(self, attrs):
        if attrs.get('virt'):
            self.virt = attrs.get('virt').value
        if attrs.get('prot'):
            self.prot = attrs.get('prot').value
        if attrs.get('refid'):
            self.refid = attrs.get('refid').value
    def buildChildren(self, child_, nodeName_):
        if child_.nodeType == Node.TEXT_NODE:
            obj_ = self.mixedclass_(MixedContainer.CategoryText,
                MixedContainer.TypeNone, '', child_.nodeValue)
            self.content_.append(obj_)
        if child_.nodeType == Node.TEXT_NODE:
            self.valueOf_ += child_.nodeValue
        elif child_.nodeType == Node.CDATA_SECTION_NODE:
            self.valueOf_ += '![CDATA['+child_.nodeValue+']]'
# end class compoundRefType


class reimplementType(GeneratedsSuper):
    subclass = None
    superclass = None
    def __init__(self, refid=None, valueOf_='', mixedclass_=None, content_=None):
        self.refid = refid
        if mixedclass_ is None:
            self.mixedclass_ = MixedContainer
        else:
            self.mixedclass_ = mixedclass_
        if content_ is None:
            self.content_ = []
        else:
            self.content_ = content_
    def factory(*args_, **kwargs_):
        if reimplementType.subclass:
            return reimplementType.subclass(*args_, **kwargs_)
        else:
            return reimplementType(*args_, **kwargs_)
    factory = staticmethod(factory)
    def get_refid(self): return self.refid
    def set_refid(self, refid): self.refid = refid
    def getValueOf_(self): return self.valueOf_
    def setValueOf_(self, valueOf_): self.valueOf_ = valueOf_
    def export(self, outfile, level, namespace_='', name_='reimplementType', namespacedef_=''):
        showIndent(outfile, level)
        outfile.write('<%s%s %s' % (namespace_, name_, namespacedef_, ))
        self.exportAttributes(outfile, level, namespace_, name_='reimplementType')
        outfile.write('>')
        self.exportChildren(outfile, level + 1, namespace_, name_)
        outfile.write('</%s%s>\n' % (namespace_, name_))
    def exportAttributes(self, outfile, level, namespace_='', name_='reimplementType'):
        if self.refid is not None:
            outfile.write(' refid=%s' % (self.format_string(quote_attrib(self.refid).encode(ExternalEncoding), input_name='refid'), ))
    def exportChildren(self, outfile, level, namespace_='', name_='reimplementType'):
        if self.valueOf_.find('![CDATA')>-1:
            value=quote_xml('%s' % self.valueOf_)
            value=value.replace('![CDATA','<![CDATA')
            value=value.replace(']]',']]>')
            outfile.write(value)
        else:
            outfile.write(quote_xml('%s' % self.valueOf_))
    def hasContent_(self):
        if (
            self.valueOf_ is not None
            ):
            return True
        else:
            return False
    def exportLiteral(self, outfile, level, name_='reimplementType'):
        level += 1
        self.exportLiteralAttributes(outfile, level, name_)
        if self.hasContent_():
            self.exportLiteralChildren(outfile, level, name_)
    def exportLiteralAttributes(self, outfile, level, name_):
        if self.refid is not None:
            showIndent(outfile, level)
            outfile.write('refid = %s,\n' % (self.refid,))
    def exportLiteralChildren(self, outfile, level, name_):
        showIndent(outfile, level)
        outfile.write('valueOf_ = "%s",\n' % (self.valueOf_,))
    def build(self, node_):
        attrs = node_.attributes
        self.buildAttributes(attrs)
        self.valueOf_ = ''
        for child_ in node_.childNodes:
            nodeName_ = child_.nodeName.split(':')[-1]
            self.buildChildren(child_, nodeName_)
    def buildAttributes(self, attrs):
        if attrs.get('refid'):
            self.refid = attrs.get('refid').value
    def buildChildren(self, child_, nodeName_):
        if child_.nodeType == Node.TEXT_NODE:
            obj_ = self.mixedclass_(MixedContainer.CategoryText,
                MixedContainer.TypeNone, '', child_.nodeValue)
            self.content_.append(obj_)
        if child_.nodeType == Node.TEXT_NODE:
            self.valueOf_ += child_.nodeValue
        elif child_.nodeType == Node.CDATA_SECTION_NODE:
            self.valueOf_ += '![CDATA['+child_.nodeValue+']]'
# end class reimplementType


class incType(GeneratedsSuper):
    subclass = None
    superclass = None
    def __init__(self, local=None, refid=None, valueOf_='', mixedclass_=None, content_=None):
        self.local = local
        self.refid = refid
        if mixedclass_ is None:
            self.mixedclass_ = MixedContainer
        else:
            self.mixedclass_ = mixedclass_
        if content_ is None:
            self.content_ = []
        else:
            self.content_ = content_
    def factory(*args_, **kwargs_):
        if incType.subclass:
            return incType.subclass(*args_, **kwargs_)
        else:
            return incType(*args_, **kwargs_)
    factory = staticmethod(factory)
    def get_local(self): return self.local
    def set_local(self, local): self.local = local
    def get_refid(self): return self.refid
    def set_refid(self, refid): self.refid = refid
    def getValueOf_(self): return self.valueOf_
    def setValueOf_(self, valueOf_): self.valueOf_ = valueOf_
    def export(self, outfile, level, namespace_='', name_='incType', namespacedef_=''):
        showIndent(outfile, level)
        outfile.write('<%s%s %s' % (namespace_, name_, namespacedef_, ))
        self.exportAttributes(outfile, level, namespace_, name_='incType')
        outfile.write('>')
        self.exportChildren(outfile, level + 1, namespace_, name_)
        outfile.write('</%s%s>\n' % (namespace_, name_))
    def exportAttributes(self, outfile, level, namespace_='', name_='incType'):
        if self.local is not None:
            outfile.write(' local=%s' % (quote_attrib(self.local), ))
        if self.refid is not None:
            outfile.write(' refid=%s' % (self.format_string(quote_attrib(self.refid).encode(ExternalEncoding), input_name='refid'), ))
    def exportChildren(self, outfile, level, namespace_='', name_='incType'):
        if self.valueOf_.find('![CDATA')>-1:
            value=quote_xml('%s' % self.valueOf_)
            value=value.replace('![CDATA','<![CDATA')
            value=value.replace(']]',']]>')
            outfile.write(value)
        else:
            outfile.write(quote_xml('%s' % self.valueOf_))
    def hasContent_(self):
        if (
            self.valueOf_ is not None
            ):
            return True
        else:
            return False
    def exportLiteral(self, outfile, level, name_='incType'):
        level += 1
        self.exportLiteralAttributes(outfile, level, name_)
        if self.hasContent_():
            self.exportLiteralChildren(outfile, level, name_)
    def exportLiteralAttributes(self, outfile, level, name_):
        if self.local is not None:
            showIndent(outfile, level)
            outfile.write('local = "%s",\n' % (self.local,))
        if self.refid is not None:
            showIndent(outfile, level)
            outfile.write('refid = %s,\n' % (self.refid,))
    def exportLiteralChildren(self, outfile, level, name_):
        showIndent(outfile, level)
        outfile.write('valueOf_ = "%s",\n' % (self.valueOf_,))
    def build(self, node_):
        attrs = node_.attributes
        self.buildAttributes(attrs)
        self.valueOf_ = ''
        for child_ in node_.childNodes:
            nodeName_ = child_.nodeName.split(':')[-1]
            self.buildChildren(child_, nodeName_)
    def buildAttributes(self, attrs):
        if attrs.get('local'):
            self.local = attrs.get('local').value
        if attrs.get('refid'):
            self.refid = attrs.get('refid').value
    def buildChildren(self, child_, nodeName_):
        if child_.nodeType == Node.TEXT_NODE:
            obj_ = self.mixedclass_(MixedContainer.CategoryText,
                MixedContainer.TypeNone, '', child_.nodeValue)
            self.content_.append(obj_)
        if child_.nodeType == Node.TEXT_NODE:
            self.valueOf_ += child_.nodeValue
        elif child_.nodeType == Node.CDATA_SECTION_NODE:
            self.valueOf_ += '![CDATA['+child_.nodeValue+']]'
# end class incType


class refType(GeneratedsSuper):
    subclass = None
    superclass = None
    def __init__(self, prot=None, refid=None, valueOf_='', mixedclass_=None, content_=None):
        self.prot = prot
        self.refid = refid
        if mixedclass_ is None:
            self.mixedclass_ = MixedContainer
        else:
            self.mixedclass_ = mixedclass_
        if content_ is None:
            self.content_ = []
        else:
            self.content_ = content_
    def factory(*args_, **kwargs_):
        if refType.subclass:
            return refType.subclass(*args_, **kwargs_)
        else:
            return refType(*args_, **kwargs_)
    factory = staticmethod(factory)
    def get_prot(self): return self.prot
    def set_prot(self, prot): self.prot = prot
    def get_refid(self): return self.refid
    def set_refid(self, refid): self.refid = refid
    def getValueOf_(self): return self.valueOf_
    def setValueOf_(self, valueOf_): self.valueOf_ = valueOf_
    def export(self, outfile, level, namespace_='', name_='refType', namespacedef_=''):
        showIndent(outfile, level)
        outfile.write('<%s%s %s' % (namespace_, name_, namespacedef_, ))
        self.exportAttributes(outfile, level, namespace_, name_='refType')
        outfile.write('>')
        self.exportChildren(outfile, level + 1, namespace_, name_)
        outfile.write('</%s%s>\n' % (namespace_, name_))
    def exportAttributes(self, outfile, level, namespace_='', name_='refType'):
        if self.prot is not None:
            outfile.write(' prot=%s' % (quote_attrib(self.prot), ))
        if self.refid is not None:
            outfile.write(' refid=%s' % (self.format_string(quote_attrib(self.refid).encode(ExternalEncoding), input_name='refid'), ))
    def exportChildren(self, outfile, level, namespace_='', name_='refType'):
        if self.valueOf_.find('![CDATA')>-1:
            value=quote_xml('%s' % self.valueOf_)
            value=value.replace('![CDATA','<![CDATA')
            value=value.replace(']]',']]>')
            outfile.write(value)
        else:
            outfile.write(quote_xml('%s' % self.valueOf_))
    def hasContent_(self):
        if (
            self.valueOf_ is not None
            ):
            return True
        else:
            return False
    def exportLiteral(self, outfile, level, name_='refType'):
        level += 1
        self.exportLiteralAttributes(outfile, level, name_)
        if self.hasContent_():
            self.exportLiteralChildren(outfile, level, name_)
    def exportLiteralAttributes(self, outfile, level, name_):
        if self.prot is not None:
            showIndent(outfile, level)
            outfile.write('prot = "%s",\n' % (self.prot,))
        if self.refid is not None:
            showIndent(outfile, level)
            outfile.write('refid = %s,\n' % (self.refid,))
    def exportLiteralChildren(self, outfile, level, name_):
        showIndent(outfile, level)
        outfile.write('valueOf_ = "%s",\n' % (self.valueOf_,))
    def build(self, node_):
        attrs = node_.attributes
        self.buildAttributes(attrs)
        self.valueOf_ = ''
        for child_ in node_.childNodes:
            nodeName_ = child_.nodeName.split(':')[-1]
            self.buildChildren(child_, nodeName_)
    def buildAttributes(self, attrs):
        if attrs.get('prot'):
            self.prot = attrs.get('prot').value
        if attrs.get('refid'):
            self.refid = attrs.get('refid').value
    def buildChildren(self, child_, nodeName_):
        if child_.nodeType == Node.TEXT_NODE:
            obj_ = self.mixedclass_(MixedContainer.CategoryText,
                MixedContainer.TypeNone, '', child_.nodeValue)
            self.content_.append(obj_)
        if child_.nodeType == Node.TEXT_NODE:
            self.valueOf_ += child_.nodeValue
        elif child_.nodeType == Node.CDATA_SECTION_NODE:
            self.valueOf_ += '![CDATA['+child_.nodeValue+']]'
# end class refType


class refTextType(GeneratedsSuper):
    subclass = None
    superclass = None
    def __init__(self, refid=None, kindref=None, external=None, valueOf_='', mixedclass_=None, content_=None):
        self.refid = refid
        self.kindref = kindref
        self.external = external
        if mixedclass_ is None:
            self.mixedclass_ = MixedContainer
        else:
            self.mixedclass_ = mixedclass_
        if content_ is None:
            self.content_ = []
        else:
            self.content_ = content_
    def factory(*args_, **kwargs_):
        if refTextType.subclass:
            return refTextType.subclass(*args_, **kwargs_)
        else:
            return refTextType(*args_, **kwargs_)
    factory = staticmethod(factory)
    def get_refid(self): return self.refid
    def set_refid(self, refid): self.refid = refid
    def get_kindref(self): return self.kindref
    def set_kindref(self, kindref): self.kindref = kindref
    def get_external(self): return self.external
    def set_external(self, external): self.external = external
    def getValueOf_(self): return self.valueOf_
    def setValueOf_(self, valueOf_): self.valueOf_ = valueOf_
    def export(self, outfile, level, namespace_='', name_='refTextType', namespacedef_=''):
        showIndent(outfile, level)
        outfile.write('<%s%s %s' % (namespace_, name_, namespacedef_, ))
        self.exportAttributes(outfile, level, namespace_, name_='refTextType')
        outfile.write('>')
        self.exportChildren(outfile, level + 1, namespace_, name_)
        outfile.write('</%s%s>\n' % (namespace_, name_))
    def exportAttributes(self, outfile, level, namespace_='', name_='refTextType'):
        if self.refid is not None:
            outfile.write(' refid=%s' % (self.format_string(quote_attrib(self.refid).encode(ExternalEncoding), input_name='refid'), ))
        if self.kindref is not None:
            outfile.write(' kindref=%s' % (quote_attrib(self.kindref), ))
        if self.external is not None:
            outfile.write(' external=%s' % (self.format_string(quote_attrib(self.external).encode(ExternalEncoding), input_name='external'), ))
    def exportChildren(self, outfile, level, namespace_='', name_='refTextType'):
        if self.valueOf_.find('![CDATA')>-1:
            value=quote_xml('%s' % self.valueOf_)
            value=value.replace('![CDATA','<![CDATA')
            value=value.replace(']]',']]>')
            outfile.write(value)
        else:
            outfile.write(quote_xml('%s' % self.valueOf_))
    def hasContent_(self):
        if (
            self.valueOf_ is not None
            ):
            return True
        else:
            return False
    def exportLiteral(self, outfile, level, name_='refTextType'):
        level += 1
        self.exportLiteralAttributes(outfile, level, name_)
        if self.hasContent_():
            self.exportLiteralChildren(outfile, level, name_)
    def exportLiteralAttributes(self, outfile, level, name_):
        if self.refid is not None:
            showIndent(outfile, level)
            outfile.write('refid = %s,\n' % (self.refid,))
        if self.kindref is not None:
            showIndent(outfile, level)
            outfile.write('kindref = "%s",\n' % (self.kindref,))
        if self.external is not None:
            showIndent(outfile, level)
            outfile.write('external = %s,\n' % (self.external,))
    def exportLiteralChildren(self, outfile, level, name_):
        showIndent(outfile, level)
        outfile.write('valueOf_ = "%s",\n' % (self.valueOf_,))
    def build(self, node_):
        attrs = node_.attributes
        self.buildAttributes(attrs)
        self.valueOf_ = ''
        for child_ in node_.childNodes:
            nodeName_ = child_.nodeName.split(':')[-1]
            self.buildChildren(child_, nodeName_)
    def buildAttributes(self, attrs):
        if attrs.get('refid'):
            self.refid = attrs.get('refid').value
        if attrs.get('kindref'):
            self.kindref = attrs.get('kindref').value
        if attrs.get('external'):
            self.external = attrs.get('external').value
    def buildChildren(self, child_, nodeName_):
        if child_.nodeType == Node.TEXT_NODE:
            obj_ = self.mixedclass_(MixedContainer.CategoryText,
                MixedContainer.TypeNone, '', child_.nodeValue)
            self.content_.append(obj_)
        if child_.nodeType == Node.TEXT_NODE:
            self.valueOf_ += child_.nodeValue
        elif child_.nodeType == Node.CDATA_SECTION_NODE:
            self.valueOf_ += '![CDATA['+child_.nodeValue+']]'
# end class refTextType


class sectiondefType(GeneratedsSuper):
    subclass = None
    superclass = None
    def __init__(self, kind=None, header=None, description=None, memberdef=None):
        self.kind = kind
        self.header = header
        self.description = description
        if memberdef is None:
            self.memberdef = []
        else:
            self.memberdef = memberdef
    def factory(*args_, **kwargs_):
        if sectiondefType.subclass:
            return sectiondefType.subclass(*args_, **kwargs_)
        else:
            return sectiondefType(*args_, **kwargs_)
    factory = staticmethod(factory)
    def get_header(self): return self.header
    def set_header(self, header): self.header = header
    def get_description(self): return self.description
    def set_description(self, description): self.description = description
    def get_memberdef(self): return self.memberdef
    def set_memberdef(self, memberdef): self.memberdef = memberdef
    def add_memberdef(self, value): self.memberdef.append(value)
    def insert_memberdef(self, index, value): self.memberdef[index] = value
    def get_kind(self): return self.kind
    def set_kind(self, kind): self.kind = kind
    def export(self, outfile, level, namespace_='', name_='sectiondefType', namespacedef_=''):
        showIndent(outfile, level)
        outfile.write('<%s%s %s' % (namespace_, name_, namespacedef_, ))
        self.exportAttributes(outfile, level, namespace_, name_='sectiondefType')
        if self.hasContent_():
            outfile.write('>\n')
            self.exportChildren(outfile, level + 1, namespace_, name_)
            showIndent(outfile, level)
            outfile.write('</%s%s>\n' % (namespace_, name_))
        else:
            outfile.write(' />\n')
    def exportAttributes(self, outfile, level, namespace_='', name_='sectiondefType'):
        if self.kind is not None:
            outfile.write(' kind=%s' % (quote_attrib(self.kind), ))
    def exportChildren(self, outfile, level, namespace_='', name_='sectiondefType'):
        if self.header is not None:
            showIndent(outfile, level)
            outfile.write('<%sheader>%s</%sheader>\n' % (namespace_, self.format_string(quote_xml(self.header).encode(ExternalEncoding), input_name='header'), namespace_))
        if self.description:
            self.description.export(outfile, level, namespace_, name_='description')
        for memberdef_ in self.memberdef:
            memberdef_.export(outfile, level, namespace_, name_='memberdef')
    def hasContent_(self):
        if (
            self.header is not None or
            self.description is not None or
            self.memberdef is not None
            ):
            return True
        else:
            return False
    def exportLiteral(self, outfile, level, name_='sectiondefType'):
        level += 1
        self.exportLiteralAttributes(outfile, level, name_)
        if self.hasContent_():
            self.exportLiteralChildren(outfile, level, name_)
    def exportLiteralAttributes(self, outfile, level, name_):
        if self.kind is not None:
            showIndent(outfile, level)
            outfile.write('kind = "%s",\n' % (self.kind,))
    def exportLiteralChildren(self, outfile, level, name_):
        showIndent(outfile, level)
        outfile.write('header=%s,\n' % quote_python(self.header).encode(ExternalEncoding))
        if self.description:
            showIndent(outfile, level)
            outfile.write('description=model_.descriptionType(\n')
            self.description.exportLiteral(outfile, level, name_='description')
            showIndent(outfile, level)
            outfile.write('),\n')
        showIndent(outfile, level)
        outfile.write('memberdef=[\n')
        level += 1
        for memberdef in self.memberdef:
            showIndent(outfile, level)
            outfile.write('model_.memberdef(\n')
            memberdef.exportLiteral(outfile, level, name_='memberdef')
            showIndent(outfile, level)
            outfile.write('),\n')
        level -= 1
        showIndent(outfile, level)
        outfile.write('],\n')
    def build(self, node_):
        attrs = node_.attributes
        self.buildAttributes(attrs)
        for child_ in node_.childNodes:
            nodeName_ = child_.nodeName.split(':')[-1]
            self.buildChildren(child_, nodeName_)
    def buildAttributes(self, attrs):
        if attrs.get('kind'):
            self.kind = attrs.get('kind').value
    def buildChildren(self, child_, nodeName_):
        if child_.nodeType == Node.ELEMENT_NODE and \
            nodeName_ == 'header':
            header_ = ''
            for text__content_ in child_.childNodes:
                header_ += text__content_.nodeValue
            self.header = header_
        elif child_.nodeType == Node.ELEMENT_NODE and \
            nodeName_ == 'description':
            obj_ = descriptionType.factory()
            obj_.build(child_)
            self.set_description(obj_)
        elif child_.nodeType == Node.ELEMENT_NODE and \
            nodeName_ == 'memberdef':
            obj_ = memberdefType.factory()
            obj_.build(child_)
            self.memberdef.append(obj_)
# end class sectiondefType


class memberdefType(GeneratedsSuper):
    subclass = None
    superclass = None
    def __init__(self, initonly=None, kind=None, volatile=None, const=None, raisexx=None, virt=None, readable=None, prot=None, explicit=None, new=None, final=None, writable=None, add=None, static=None, remove=None, sealed=None, mutable=None, gettable=None, inline=None, settable=None, id=None, templateparamlist=None, type_=None, definition=None, argsstring=None, name=None, read=None, write=None, bitfield=None, reimplements=None, reimplementedby=None, param=None, enumvalue=None, initializer=None, exceptions=None, briefdescription=None, detaileddescription=None, inbodydescription=None, location=None, references=None, referencedby=None):
        self.initonly = initonly
        self.kind = kind
        self.volatile = volatile
        self.const = const
        self.raisexx = raisexx
        self.virt = virt
        self.readable = readable
        self.prot = prot
        self.explicit = explicit
        self.new = new
        self.final = final
        self.writable = writable
        self.add = add
        self.static = static
        self.remove = remove
        self.sealed = sealed
        self.mutable = mutable
        self.gettable = gettable
        self.inline = inline
        self.settable = settable
        self.id = id
        self.templateparamlist = templateparamlist
        self.type_ = type_
        self.definition = definition
        self.argsstring = argsstring
        self.name = name
        self.read = read
        self.write = write
        self.bitfield = bitfield
        if reimplements is None:
            self.reimplements = []
        else:
            self.reimplements = reimplements
        if reimplementedby is None:
            self.reimplementedby = []
        else:
            self.reimplementedby = reimplementedby
        if param is None:
            self.param = []
        else:
            self.param = param
        if enumvalue is None:
            self.enumvalue = []
        else:
            self.enumvalue = enumvalue
        self.initializer = initializer
        self.exceptions = exceptions
        self.briefdescription = briefdescription
        self.detaileddescription = detaileddescription
        self.inbodydescription = inbodydescription
        self.location = location
        if references is None:
            self.references = []
        else:
            self.references = references
        if referencedby is None:
            self.referencedby = []
        else:
            self.referencedby = referencedby
    def factory(*args_, **kwargs_):
        if memberdefType.subclass:
            return memberdefType.subclass(*args_, **kwargs_)
        else:
            return memberdefType(*args_, **kwargs_)
    factory = staticmethod(factory)
    def get_templateparamlist(self): return self.templateparamlist
    def set_templateparamlist(self, templateparamlist): self.templateparamlist = templateparamlist
    def get_type(self): return self.type_
    def set_type(self, type_): self.type_ = type_
    def get_definition(self): return self.definition
    def set_definition(self, definition): self.definition = definition
    def get_argsstring(self): return self.argsstring
    def set_argsstring(self, argsstring): self.argsstring = argsstring
    def get_name(self): return self.name
    def set_name(self, name): self.name = name
    def get_read(self): return self.read
    def set_read(self, read): self.read = read
    def get_write(self): return self.write
    def set_write(self, write): self.write = write
    def get_bitfield(self): return self.bitfield
    def set_bitfield(self, bitfield): self.bitfield = bitfield
    def get_reimplements(self): return self.reimplements
    def set_reimplements(self, reimplements): self.reimplements = reimplements
    def add_reimplements(self, value): self.reimplements.append(value)
    def insert_reimplements(self, index, value): self.reimplements[index] = value
    def get_reimplementedby(self): return self.reimplementedby
    def set_reimplementedby(self, reimplementedby): self.reimplementedby = reimplementedby
    def add_reimplementedby(self, value): self.reimplementedby.append(value)
    def insert_reimplementedby(self, index, value): self.reimplementedby[index] = value
    def get_param(self): return self.param
    def set_param(self, param): self.param = param
    def add_param(self, value): self.param.append(value)
    def insert_param(self, index, value): self.param[index] = value
    def get_enumvalue(self): return self.enumvalue
    def set_enumvalue(self, enumvalue): self.enumvalue = enumvalue
    def add_enumvalue(self, value): self.enumvalue.append(value)
    def insert_enumvalue(self, index, value): self.enumvalue[index] = value
    def get_initializer(self): return self.initializer
    def set_initializer(self, initializer): self.initializer = initializer
    def get_exceptions(self): return self.exceptions
    def set_exceptions(self, exceptions): self.exceptions = exceptions
    def get_briefdescription(self): return self.briefdescription
    def set_briefdescription(self, briefdescription): self.briefdescription = briefdescription
    def get_detaileddescription(self): return self.detaileddescription
    def set_detaileddescription(self, detaileddescription): self.detaileddescription = detaileddescription
    def get_inbodydescription(self): return self.inbodydescription
    def set_inbodydescription(self, inbodydescription): self.inbodydescription = inbodydescription
    def get_location(self): return self.location
    def set_location(self, location): self.location = location
    def get_references(self): return self.references
    def set_references(self, references): self.references = references
    def add_references(self, value): self.references.append(value)
    def insert_references(self, index, value): self.references[index] = value
    def get_referencedby(self): return self.referencedby
    def set_referencedby(self, referencedby): self.referencedby = referencedby
    def add_referencedby(self, value): self.referencedby.append(value)
    def insert_referencedby(self, index, value): self.referencedby[index] = value
    def get_initonly(self): return self.initonly
    def set_initonly(self, initonly): self.initonly = initonly
    def get_kind(self): return self.kind
    def set_kind(self, kind): self.kind = kind
    def get_volatile(self): return self.volatile
    def set_volatile(self, volatile): self.volatile = volatile
    def get_const(self): return self.const
    def set_const(self, const): self.const = const
    def get_raise(self): return self.raisexx
    def set_raise(self, raisexx): self.raisexx = raisexx
    def get_virt(self): return self.virt
    def set_virt(self, virt): self.virt = virt
    def get_readable(self): return self.readable
    def set_readable(self, readable): self.readable = readable
    def get_prot(self): return self.prot
    def set_prot(self, prot): self.prot = prot
    def get_explicit(self): return self.explicit
    def set_explicit(self, explicit): self.explicit = explicit
    def get_new(self): return self.new
    def set_new(self, new): self.new = new
    def get_final(self): return self.final
    def set_final(self, final): self.final = final
    def get_writable(self): return self.writable
    def set_writable(self, writable): self.writable = writable
    def get_add(self): return self.add
    def set_add(self, add): self.add = add
    def get_static(self): return self.static
    def set_static(self, static): self.static = static
    def get_remove(self): return self.remove
    def set_remove(self, remove): self.remove = remove
    def get_sealed(self): return self.sealed
    def set_sealed(self, sealed): self.sealed = sealed
    def get_mutable(self): return self.mutable
    def set_mutable(self, mutable): self.mutable = mutable
    def get_gettable(self): return self.gettable
    def set_gettable(self, gettable): self.gettable = gettable
    def get_inline(self): return self.inline
    def set_inline(self, inline): self.inline = inline
    def get_settable(self): return self.settable
    def set_settable(self, settable): self.settable = settable
    def get_id(self): return self.id
    def set_id(self, id): self.id = id
    def export(self, outfile, level, namespace_='', name_='memberdefType', namespacedef_=''):
        showIndent(outfile, level)
        outfile.write('<%s%s %s' % (namespace_, name_, namespacedef_, ))
        self.exportAttributes(outfile, level, namespace_, name_='memberdefType')
        if self.hasContent_():
            outfile.write('>\n')
            self.exportChildren(outfile, level + 1, namespace_, name_)
            showIndent(outfile, level)
            outfile.write('</%s%s>\n' % (namespace_, name_))
        else:
            outfile.write(' />\n')
    def exportAttributes(self, outfile, level, namespace_='', name_='memberdefType'):
        if self.initonly is not None:
            outfile.write(' initonly=%s' % (quote_attrib(self.initonly), ))
        if self.kind is not None:
            outfile.write(' kind=%s' % (quote_attrib(self.kind), ))
        if self.volatile is not None:
            outfile.write(' volatile=%s' % (quote_attrib(self.volatile), ))
        if self.const is not None:
            outfile.write(' const=%s' % (quote_attrib(self.const), ))
        if self.raisexx is not None:
            outfile.write(' raise=%s' % (quote_attrib(self.raisexx), ))
        if self.virt is not None:
            outfile.write(' virt=%s' % (quote_attrib(self.virt), ))
        if self.readable is not None:
            outfile.write(' readable=%s' % (quote_attrib(self.readable), ))
        if self.prot is not None:
            outfile.write(' prot=%s' % (quote_attrib(self.prot), ))
        if self.explicit is not None:
            outfile.write(' explicit=%s' % (quote_attrib(self.explicit), ))
        if self.new is not None:
            outfile.write(' new=%s' % (quote_attrib(self.new), ))
        if self.final is not None:
            outfile.write(' final=%s' % (quote_attrib(self.final), ))
        if self.writable is not None:
            outfile.write(' writable=%s' % (quote_attrib(self.writable), ))
        if self.add is not None:
            outfile.write(' add=%s' % (quote_attrib(self.add), ))
        if self.static is not None:
            outfile.write(' static=%s' % (quote_attrib(self.static), ))
        if self.remove is not None:
            outfile.write(' remove=%s' % (quote_attrib(self.remove), ))
        if self.sealed is not None:
            outfile.write(' sealed=%s' % (quote_attrib(self.sealed), ))
        if self.mutable is not None:
            outfile.write(' mutable=%s' % (quote_attrib(self.mutable), ))
        if self.gettable is not None:
            outfile.write(' gettable=%s' % (quote_attrib(self.gettable), ))
        if self.inline is not None:
            outfile.write(' inline=%s' % (quote_attrib(self.inline), ))
        if self.settable is not None:
            outfile.write(' settable=%s' % (quote_attrib(self.settable), ))
        if self.id is not None:
            outfile.write(' id=%s' % (self.format_string(quote_attrib(self.id).encode(ExternalEncoding), input_name='id'), ))
    def exportChildren(self, outfile, level, namespace_='', name_='memberdefType'):
        if self.templateparamlist:
            self.templateparamlist.export(outfile, level, namespace_, name_='templateparamlist')
        if self.type_:
            self.type_.export(outfile, level, namespace_, name_='type')
        if self.definition is not None:
            showIndent(outfile, level)
            outfile.write('<%sdefinition>%s</%sdefinition>\n' % (namespace_, self.format_string(quote_xml(self.definition).encode(ExternalEncoding), input_name='definition'), namespace_))
        if self.argsstring is not None:
            showIndent(outfile, level)
            outfile.write('<%sargsstring>%s</%sargsstring>\n' % (namespace_, self.format_string(quote_xml(self.argsstring).encode(ExternalEncoding), input_name='argsstring'), namespace_))
        if self.name is not None:
            showIndent(outfile, level)
            outfile.write('<%sname>%s</%sname>\n' % (namespace_, self.format_string(quote_xml(self.name).encode(ExternalEncoding), input_name='name'), namespace_))
        if self.read is not None:
            showIndent(outfile, level)
            outfile.write('<%sread>%s</%sread>\n' % (namespace_, self.format_string(quote_xml(self.read).encode(ExternalEncoding), input_name='read'), namespace_))
        if self.write is not None:
            showIndent(outfile, level)
            outfile.write('<%swrite>%s</%swrite>\n' % (namespace_, self.format_string(quote_xml(self.write).encode(ExternalEncoding), input_name='write'), namespace_))
        if self.bitfield is not None:
            showIndent(outfile, level)
            outfile.write('<%sbitfield>%s</%sbitfield>\n' % (namespace_, self.format_string(quote_xml(self.bitfield).encode(ExternalEncoding), input_name='bitfield'), namespace_))
        for reimplements_ in self.reimplements:
            reimplements_.export(outfile, level, namespace_, name_='reimplements')
        for reimplementedby_ in self.reimplementedby:
            reimplementedby_.export(outfile, level, namespace_, name_='reimplementedby')
        for param_ in self.param:
            param_.export(outfile, level, namespace_, name_='param')
        for enumvalue_ in self.enumvalue:
            enumvalue_.export(outfile, level, namespace_, name_='enumvalue')
        if self.initializer:
            self.initializer.export(outfile, level, namespace_, name_='initializer')
        if self.exceptions:
            self.exceptions.export(outfile, level, namespace_, name_='exceptions')
        if self.briefdescription:
            self.briefdescription.export(outfile, level, namespace_, name_='briefdescription')
        if self.detaileddescription:
            self.detaileddescription.export(outfile, level, namespace_, name_='detaileddescription')
        if self.inbodydescription:
            self.inbodydescription.export(outfile, level, namespace_, name_='inbodydescription')
        if self.location:
            self.location.export(outfile, level, namespace_, name_='location', )
        for references_ in self.references:
            references_.export(outfile, level, namespace_, name_='references')
        for referencedby_ in self.referencedby:
            referencedby_.export(outfile, level, namespace_, name_='referencedby')
    def hasContent_(self):
        if (
            self.templateparamlist is not None or
            self.type_ is not None or
            self.definition is not None or
            self.argsstring is not None or
            self.name is not None or
            self.read is not None or
            self.write is not None or
            self.bitfield is not None or
            self.reimplements is not None or
            self.reimplementedby is not None or
            self.param is not None or
            self.enumvalue is not None or
            self.initializer is not None or
            self.exceptions is not None or
            self.briefdescription is not None or
            self.detaileddescription is not None or
            self.inbodydescription is not None or
            self.location is not None or
            self.references is not None or
            self.referencedby is not None
            ):
            return True
        else:
            return False
    def exportLiteral(self, outfile, level, name_='memberdefType'):
        level += 1
        self.exportLiteralAttributes(outfile, level, name_)
        if self.hasContent_():
            self.exportLiteralChildren(outfile, level, name_)
    def exportLiteralAttributes(self, outfile, level, name_):
        if self.initonly is not None:
            showIndent(outfile, level)
            outfile.write('initonly = "%s",\n' % (self.initonly,))
        if self.kind is not None:
            showIndent(outfile, level)
            outfile.write('kind = "%s",\n' % (self.kind,))
        if self.volatile is not None:
            showIndent(outfile, level)
            outfile.write('volatile = "%s",\n' % (self.volatile,))
        if self.const is not None:
            showIndent(outfile, level)
            outfile.write('const = "%s",\n' % (self.const,))
        if self.raisexx is not None:
            showIndent(outfile, level)
            outfile.write('raisexx = "%s",\n' % (self.raisexx,))
        if self.virt is not None:
            showIndent(outfile, level)
            outfile.write('virt = "%s",\n' % (self.virt,))
        if self.readable is not None:
            showIndent(outfile, level)
            outfile.write('readable = "%s",\n' % (self.readable,))
        if self.prot is not None:
            showIndent(outfile, level)
            outfile.write('prot = "%s",\n' % (self.prot,))
        if self.explicit is not None:
            showIndent(outfile, level)
            outfile.write('explicit = "%s",\n' % (self.explicit,))
        if self.new is not None:
            showIndent(outfile, level)
            outfile.write('new = "%s",\n' % (self.new,))
        if self.final is not None:
            showIndent(outfile, level)
            outfile.write('final = "%s",\n' % (self.final,))
        if self.writable is not None:
            showIndent(outfile, level)
            outfile.write('writable = "%s",\n' % (self.writable,))
        if self.add is not None:
            showIndent(outfile, level)
            outfile.write('add = "%s",\n' % (self.add,))
        if self.static is not None:
            showIndent(outfile, level)
            outfile.write('static = "%s",\n' % (self.static,))
        if self.remove is not None:
            showIndent(outfile, level)
            outfile.write('remove = "%s",\n' % (self.remove,))
        if self.sealed is not None:
            showIndent(outfile, level)
            outfile.write('sealed = "%s",\n' % (self.sealed,))
        if self.mutable is not None:
            showIndent(outfile, level)
            outfile.write('mutable = "%s",\n' % (self.mutable,))
        if self.gettable is not None:
            showIndent(outfile, level)
            outfile.write('gettable = "%s",\n' % (self.gettable,))
        if self.inline is not None:
            showIndent(outfile, level)
            outfile.write('inline = "%s",\n' % (self.inline,))
        if self.settable is not None:
            showIndent(outfile, level)
            outfile.write('settable = "%s",\n' % (self.settable,))
        if self.id is not None:
            showIndent(outfile, level)
            outfile.write('id = %s,\n' % (self.id,))
    def exportLiteralChildren(self, outfile, level, name_):
        if self.templateparamlist:
            showIndent(outfile, level)
            outfile.write('templateparamlist=model_.templateparamlistType(\n')
            self.templateparamlist.exportLiteral(outfile, level, name_='templateparamlist')
            showIndent(outfile, level)
            outfile.write('),\n')
        if self.type_:
            showIndent(outfile, level)
            outfile.write('type_=model_.linkedTextType(\n')
            self.type_.exportLiteral(outfile, level, name_='type')
            showIndent(outfile, level)
            outfile.write('),\n')
        showIndent(outfile, level)
        outfile.write('definition=%s,\n' % quote_python(self.definition).encode(ExternalEncoding))
        showIndent(outfile, level)
        outfile.write('argsstring=%s,\n' % quote_python(self.argsstring).encode(ExternalEncoding))
        showIndent(outfile, level)
        outfile.write('name=%s,\n' % quote_python(self.name).encode(ExternalEncoding))
        showIndent(outfile, level)
        outfile.write('read=%s,\n' % quote_python(self.read).encode(ExternalEncoding))
        showIndent(outfile, level)
        outfile.write('write=%s,\n' % quote_python(self.write).encode(ExternalEncoding))
        showIndent(outfile, level)
        outfile.write('bitfield=%s,\n' % quote_python(self.bitfield).encode(ExternalEncoding))
        showIndent(outfile, level)
        outfile.write('reimplements=[\n')
        level += 1
        for reimplements in self.reimplements:
            showIndent(outfile, level)
            outfile.write('model_.reimplements(\n')
            reimplements.exportLiteral(outfile, level, name_='reimplements')
            showIndent(outfile, level)
            outfile.write('),\n')
        level -= 1
        showIndent(outfile, level)
        outfile.write('],\n')
        showIndent(outfile, level)
        outfile.write('reimplementedby=[\n')
        level += 1
        for reimplementedby in self.reimplementedby:
            showIndent(outfile, level)
            outfile.write('model_.reimplementedby(\n')
            reimplementedby.exportLiteral(outfile, level, name_='reimplementedby')
            showIndent(outfile, level)
            outfile.write('),\n')
        level -= 1
        showIndent(outfile, level)
        outfile.write('],\n')
        showIndent(outfile, level)
        outfile.write('param=[\n')
        level += 1
        for param in self.param:
            showIndent(outfile, level)
            outfile.write('model_.param(\n')
            param.exportLiteral(outfile, level, name_='param')
            showIndent(outfile, level)
            outfile.write('),\n')
        level -= 1
        showIndent(outfile, level)
        outfile.write('],\n')
        showIndent(outfile, level)
        outfile.write('enumvalue=[\n')
        level += 1
        for enumvalue in self.enumvalue:
            showIndent(outfile, level)
            outfile.write('model_.enumvalue(\n')
            enumvalue.exportLiteral(outfile, level, name_='enumvalue')
            showIndent(outfile, level)
            outfile.write('),\n')
        level -= 1
        showIndent(outfile, level)
        outfile.write('],\n')
        if self.initializer:
            showIndent(outfile, level)
            outfile.write('initializer=model_.linkedTextType(\n')
            self.initializer.exportLiteral(outfile, level, name_='initializer')
            showIndent(outfile, level)
            outfile.write('),\n')
        if self.exceptions:
            showIndent(outfile, level)
            outfile.write('exceptions=model_.linkedTextType(\n')
            self.exceptions.exportLiteral(outfile, level, name_='exceptions')
            showIndent(outfile, level)
            outfile.write('),\n')
        if self.briefdescription:
            showIndent(outfile, level)
            outfile.write('briefdescription=model_.descriptionType(\n')
            self.briefdescription.exportLiteral(outfile, level, name_='briefdescription')
            showIndent(outfile, level)
            outfile.write('),\n')
        if self.detaileddescription:
            showIndent(outfile, level)
            outfile.write('detaileddescription=model_.descriptionType(\n')
            self.detaileddescription.exportLiteral(outfile, level, name_='detaileddescription')
            showIndent(outfile, level)
            outfile.write('),\n')
        if self.inbodydescription:
            showIndent(outfile, level)
            outfile.write('inbodydescription=model_.descriptionType(\n')
            self.inbodydescription.exportLiteral(outfile, level, name_='inbodydescription')
            showIndent(outfile, level)
            outfile.write('),\n')
        if self.location:
            showIndent(outfile, level)
            outfile.write('location=model_.locationType(\n')
            self.location.exportLiteral(outfile, level, name_='location')
            showIndent(outfile, level)
            outfile.write('),\n')
        showIndent(outfile, level)
        outfile.write('references=[\n')
        level += 1
        for references in self.references:
            showIndent(outfile, level)
            outfile.write('model_.references(\n')
            references.exportLiteral(outfile, level, name_='references')
            showIndent(outfile, level)
            outfile.write('),\n')
        level -= 1
        showIndent(outfile, level)
        outfile.write('],\n')
        showIndent(outfile, level)
        outfile.write('referencedby=[\n')
        level += 1
        for referencedby in self.referencedby:
            showIndent(outfile, level)
            outfile.write('model_.referencedby(\n')
            referencedby.exportLiteral(outfile, level, name_='referencedby')
            showIndent(outfile, level)
            outfile.write('),\n')
        level -= 1
        showIndent(outfile, level)
        outfile.write('],\n')
    def build(self, node_):
        attrs = node_.attributes
        self.buildAttributes(attrs)
        for child_ in node_.childNodes:
            nodeName_ = child_.nodeName.split(':')[-1]
            self.buildChildren(child_, nodeName_)
    def buildAttributes(self, attrs):
        if attrs.get('initonly'):
            self.initonly = attrs.get('initonly').value
        if attrs.get('kind'):
            self.kind = attrs.get('kind').value
        if attrs.get('volatile'):
            self.volatile = attrs.get('volatile').value
        if attrs.get('const'):
            self.const = attrs.get('const').value
        if attrs.get('raise'):
            self.raisexx = attrs.get('raise').value
        if attrs.get('virt'):
            self.virt = attrs.get('virt').value
        if attrs.get('readable'):
            self.readable = attrs.get('readable').value
        if attrs.get('prot'):
            self.prot = attrs.get('prot').value
        if attrs.get('explicit'):
            self.explicit = attrs.get('explicit').value
        if attrs.get('new'):
            self.new = attrs.get('new').value
        if attrs.get('final'):
            self.final = attrs.get('final').value
        if attrs.get('writable'):
            self.writable = attrs.get('writable').value
        if attrs.get('add'):
            self.add = attrs.get('add').value
        if attrs.get('static'):
            self.static = attrs.get('static').value
        if attrs.get('remove'):
            self.remove = attrs.get('remove').value
        if attrs.get('sealed'):
            self.sealed = attrs.get('sealed').value
        if attrs.get('mutable'):
            self.mutable = attrs.get('mutable').value
        if attrs.get('gettable'):
            self.gettable = attrs.get('gettable').value
        if attrs.get('inline'):
            self.inline = attrs.get('inline').value
        if attrs.get('settable'):
            self.settable = attrs.get('settable').value
        if attrs.get('id'):
            self.id = attrs.get('id').value
    def buildChildren(self, child_, nodeName_):
        if child_.nodeType == Node.ELEMENT_NODE and \
            nodeName_ == 'templateparamlist':
            obj_ = templateparamlistType.factory()
            obj_.build(child_)
            self.set_templateparamlist(obj_)
        elif child_.nodeType == Node.ELEMENT_NODE and \
            nodeName_ == 'type':
            obj_ = linkedTextType.factory()
            obj_.build(child_)
            self.set_type(obj_)
        elif child_.nodeType == Node.ELEMENT_NODE and \
            nodeName_ == 'definition':
            definition_ = ''
            for text__content_ in child_.childNodes:
                definition_ += text__content_.nodeValue
            self.definition = definition_
        elif child_.nodeType == Node.ELEMENT_NODE and \
            nodeName_ == 'argsstring':
            argsstring_ = ''
            for text__content_ in child_.childNodes:
                argsstring_ += text__content_.nodeValue
            self.argsstring = argsstring_
        elif child_.nodeType == Node.ELEMENT_NODE and \
            nodeName_ == 'name':
            name_ = ''
            for text__content_ in child_.childNodes:
                name_ += text__content_.nodeValue
            self.name = name_
        elif child_.nodeType == Node.ELEMENT_NODE and \
            nodeName_ == 'read':
            read_ = ''
            for text__content_ in child_.childNodes:
                read_ += text__content_.nodeValue
            self.read = read_
        elif child_.nodeType == Node.ELEMENT_NODE and \
            nodeName_ == 'write':
            write_ = ''
            for text__content_ in child_.childNodes:
                write_ += text__content_.nodeValue
            self.write = write_
        elif child_.nodeType == Node.ELEMENT_NODE and \
            nodeName_ == 'bitfield':
            bitfield_ = ''
            for text__content_ in child_.childNodes:
                bitfield_ += text__content_.nodeValue
            self.bitfield = bitfield_
        elif child_.nodeType == Node.ELEMENT_NODE and \
            nodeName_ == 'reimplements':
            obj_ = reimplementType.factory()
            obj_.build(child_)
            self.reimplements.append(obj_)
        elif child_.nodeType == Node.ELEMENT_NODE and \
            nodeName_ == 'reimplementedby':
            obj_ = reimplementType.factory()
            obj_.build(child_)
            self.reimplementedby.append(obj_)
        elif child_.nodeType == Node.ELEMENT_NODE and \
            nodeName_ == 'param':
            obj_ = paramType.factory()
            obj_.build(child_)
            self.param.append(obj_)
        elif child_.nodeType == Node.ELEMENT_NODE and \
            nodeName_ == 'enumvalue':
            obj_ = enumvalueType.factory()
            obj_.build(child_)
            self.enumvalue.append(obj_)
        elif child_.nodeType == Node.ELEMENT_NODE and \
            nodeName_ == 'initializer':
            obj_ = linkedTextType.factory()
            obj_.build(child_)
            self.set_initializer(obj_)
        elif child_.nodeType == Node.ELEMENT_NODE and \
            nodeName_ == 'exceptions':
            obj_ = linkedTextType.factory()
            obj_.build(child_)
            self.set_exceptions(obj_)
        elif child_.nodeType == Node.ELEMENT_NODE and \
            nodeName_ == 'briefdescription':
            obj_ = descriptionType.factory()
            obj_.build(child_)
            self.set_briefdescription(obj_)
        elif child_.nodeType == Node.ELEMENT_NODE and \
            nodeName_ == 'detaileddescription':
            obj_ = descriptionType.factory()
            obj_.build(child_)
            self.set_detaileddescription(obj_)
        elif child_.nodeType == Node.ELEMENT_NODE and \
            nodeName_ == 'inbodydescription':
            obj_ = descriptionType.factory()
            obj_.build(child_)
            self.set_inbodydescription(obj_)
        elif child_.nodeType == Node.ELEMENT_NODE and \
            nodeName_ == 'location':
            obj_ = locationType.factory()
            obj_.build(child_)
            self.set_location(obj_)
        elif child_.nodeType == Node.ELEMENT_NODE and \
            nodeName_ == 'references':
            obj_ = referenceType.factory()
            obj_.build(child_)
            self.references.append(obj_)
        elif child_.nodeType == Node.ELEMENT_NODE and \
            nodeName_ == 'referencedby':
            obj_ = referenceType.factory()
            obj_.build(child_)
            self.referencedby.append(obj_)
# end class memberdefType


class definition(GeneratedsSuper):
    subclass = None
    superclass = None
    def __init__(self, valueOf_=''):
        self.valueOf_ = valueOf_
    def factory(*args_, **kwargs_):
        if definition.subclass:
            return definition.subclass(*args_, **kwargs_)
        else:
            return definition(*args_, **kwargs_)
    factory = staticmethod(factory)
    def getValueOf_(self): return self.valueOf_
    def setValueOf_(self, valueOf_): self.valueOf_ = valueOf_
    def export(self, outfile, level, namespace_='', name_='definition', namespacedef_=''):
        showIndent(outfile, level)
        outfile.write('<%s%s %s' % (namespace_, name_, namespacedef_, ))
        self.exportAttributes(outfile, level, namespace_, name_='definition')
        if self.hasContent_():
            outfile.write('>\n')
            self.exportChildren(outfile, level + 1, namespace_, name_)
            showIndent(outfile, level)
            outfile.write('</%s%s>\n' % (namespace_, name_))
        else:
            outfile.write(' />\n')
    def exportAttributes(self, outfile, level, namespace_='', name_='definition'):
        pass
    def exportChildren(self, outfile, level, namespace_='', name_='definition'):
        if self.valueOf_.find('![CDATA')>-1:
            value=quote_xml('%s' % self.valueOf_)
            value=value.replace('![CDATA','<![CDATA')
            value=value.replace(']]',']]>')
            outfile.write(value)
        else:
            outfile.write(quote_xml('%s' % self.valueOf_))
    def hasContent_(self):
        if (
            self.valueOf_ is not None
            ):
            return True
        else:
            return False
    def exportLiteral(self, outfile, level, name_='definition'):
        level += 1
        self.exportLiteralAttributes(outfile, level, name_)
        if self.hasContent_():
            self.exportLiteralChildren(outfile, level, name_)
    def exportLiteralAttributes(self, outfile, level, name_):
        pass
    def exportLiteralChildren(self, outfile, level, name_):
        showIndent(outfile, level)
        outfile.write('valueOf_ = "%s",\n' % (self.valueOf_,))
    def build(self, node_):
        attrs = node_.attributes
        self.buildAttributes(attrs)
        self.valueOf_ = ''
        for child_ in node_.childNodes:
            nodeName_ = child_.nodeName.split(':')[-1]
            self.buildChildren(child_, nodeName_)
    def buildAttributes(self, attrs):
        pass
    def buildChildren(self, child_, nodeName_):
        if child_.nodeType == Node.TEXT_NODE:
            self.valueOf_ += child_.nodeValue
        elif child_.nodeType == Node.CDATA_SECTION_NODE:
            self.valueOf_ += '![CDATA['+child_.nodeValue+']]'
# end class definition


class argsstring(GeneratedsSuper):
    subclass = None
    superclass = None
    def __init__(self, valueOf_=''):
        self.valueOf_ = valueOf_
    def factory(*args_, **kwargs_):
        if argsstring.subclass:
            return argsstring.subclass(*args_, **kwargs_)
        else:
            return argsstring(*args_, **kwargs_)
    factory = staticmethod(factory)
    def getValueOf_(self): return self.valueOf_
    def setValueOf_(self, valueOf_): self.valueOf_ = valueOf_
    def export(self, outfile, level, namespace_='', name_='argsstring', namespacedef_=''):
        showIndent(outfile, level)
        outfile.write('<%s%s %s' % (namespace_, name_, namespacedef_, ))
        self.exportAttributes(outfile, level, namespace_, name_='argsstring')
        if self.hasContent_():
            outfile.write('>\n')
            self.exportChildren(outfile, level + 1, namespace_, name_)
            showIndent(outfile, level)
            outfile.write('</%s%s>\n' % (namespace_, name_))
        else:
            outfile.write(' />\n')
    def exportAttributes(self, outfile, level, namespace_='', name_='argsstring'):
        pass
    def exportChildren(self, outfile, level, namespace_='', name_='argsstring'):
        if self.valueOf_.find('![CDATA')>-1:
            value=quote_xml('%s' % self.valueOf_)
            value=value.replace('![CDATA','<![CDATA')
            value=value.replace(']]',']]>')
            outfile.write(value)
        else:
            outfile.write(quote_xml('%s' % self.valueOf_))
    def hasContent_(self):
        if (
            self.valueOf_ is not None
            ):
            return True
        else:
            return False
    def exportLiteral(self, outfile, level, name_='argsstring'):
        level += 1
        self.exportLiteralAttributes(outfile, level, name_)
        if self.hasContent_():
            self.exportLiteralChildren(outfile, level, name_)
    def exportLiteralAttributes(self, outfile, level, name_):
        pass
    def exportLiteralChildren(self, outfile, level, name_):
        showIndent(outfile, level)
        outfile.write('valueOf_ = "%s",\n' % (self.valueOf_,))
    def build(self, node_):
        attrs = node_.attributes
        self.buildAttributes(attrs)
        self.valueOf_ = ''
        for child_ in node_.childNodes:
            nodeName_ = child_.nodeName.split(':')[-1]
            self.buildChildren(child_, nodeName_)
    def buildAttributes(self, attrs):
        pass
    def buildChildren(self, child_, nodeName_):
        if child_.nodeType == Node.TEXT_NODE:
            self.valueOf_ += child_.nodeValue
        elif child_.nodeType == Node.CDATA_SECTION_NODE:
            self.valueOf_ += '![CDATA['+child_.nodeValue+']]'
# end class argsstring


class read(GeneratedsSuper):
    subclass = None
    superclass = None
    def __init__(self, valueOf_=''):
        self.valueOf_ = valueOf_
    def factory(*args_, **kwargs_):
        if read.subclass:
            return read.subclass(*args_, **kwargs_)
        else:
            return read(*args_, **kwargs_)
    factory = staticmethod(factory)
    def getValueOf_(self): return self.valueOf_
    def setValueOf_(self, valueOf_): self.valueOf_ = valueOf_
    def export(self, outfile, level, namespace_='', name_='read', namespacedef_=''):
        showIndent(outfile, level)
        outfile.write('<%s%s %s' % (namespace_, name_, namespacedef_, ))
        self.exportAttributes(outfile, level, namespace_, name_='read')
        if self.hasContent_():
            outfile.write('>\n')
            self.exportChildren(outfile, level + 1, namespace_, name_)
            showIndent(outfile, level)
            outfile.write('</%s%s>\n' % (namespace_, name_))
        else:
            outfile.write(' />\n')
    def exportAttributes(self, outfile, level, namespace_='', name_='read'):
        pass
    def exportChildren(self, outfile, level, namespace_='', name_='read'):
        if self.valueOf_.find('![CDATA')>-1:
            value=quote_xml('%s' % self.valueOf_)
            value=value.replace('![CDATA','<![CDATA')
            value=value.replace(']]',']]>')
            outfile.write(value)
        else:
            outfile.write(quote_xml('%s' % self.valueOf_))
    def hasContent_(self):
        if (
            self.valueOf_ is not None
            ):
            return True
        else:
            return False
    def exportLiteral(self, outfile, level, name_='read'):
        level += 1
        self.exportLiteralAttributes(outfile, level, name_)
        if self.hasContent_():
            self.exportLiteralChildren(outfile, level, name_)
    def exportLiteralAttributes(self, outfile, level, name_):
        pass
    def exportLiteralChildren(self, outfile, level, name_):
        showIndent(outfile, level)
        outfile.write('valueOf_ = "%s",\n' % (self.valueOf_,))
    def build(self, node_):
        attrs = node_.attributes
        self.buildAttributes(attrs)
        self.valueOf_ = ''
        for child_ in node_.childNodes:
            nodeName_ = child_.nodeName.split(':')[-1]
            self.buildChildren(child_, nodeName_)
    def buildAttributes(self, attrs):
        pass
    def buildChildren(self, child_, nodeName_):
        if child_.nodeType == Node.TEXT_NODE:
            self.valueOf_ += child_.nodeValue
        elif child_.nodeType == Node.CDATA_SECTION_NODE:
            self.valueOf_ += '![CDATA['+child_.nodeValue+']]'
# end class read


class write(GeneratedsSuper):
    subclass = None
    superclass = None
    def __init__(self, valueOf_=''):
        self.valueOf_ = valueOf_
    def factory(*args_, **kwargs_):
        if write.subclass:
            return write.subclass(*args_, **kwargs_)
        else:
            return write(*args_, **kwargs_)
    factory = staticmethod(factory)
    def getValueOf_(self): return self.valueOf_
    def setValueOf_(self, valueOf_): self.valueOf_ = valueOf_
    def export(self, outfile, level, namespace_='', name_='write', namespacedef_=''):
        showIndent(outfile, level)
        outfile.write('<%s%s %s' % (namespace_, name_, namespacedef_, ))
        self.exportAttributes(outfile, level, namespace_, name_='write')
        if self.hasContent_():
            outfile.write('>\n')
            self.exportChildren(outfile, level + 1, namespace_, name_)
            showIndent(outfile, level)
            outfile.write('</%s%s>\n' % (namespace_, name_))
        else:
            outfile.write(' />\n')
    def exportAttributes(self, outfile, level, namespace_='', name_='write'):
        pass
    def exportChildren(self, outfile, level, namespace_='', name_='write'):
        if self.valueOf_.find('![CDATA')>-1:
            value=quote_xml('%s' % self.valueOf_)
            value=value.replace('![CDATA','<![CDATA')
            value=value.replace(']]',']]>')
            outfile.write(value)
        else:
            outfile.write(quote_xml('%s' % self.valueOf_))
    def hasContent_(self):
        if (
            self.valueOf_ is not None
            ):
            return True
        else:
            return False
    def exportLiteral(self, outfile, level, name_='write'):
        level += 1
        self.exportLiteralAttributes(outfile, level, name_)
        if self.hasContent_():
            self.exportLiteralChildren(outfile, level, name_)
    def exportLiteralAttributes(self, outfile, level, name_):
        pass
    def exportLiteralChildren(self, outfile, level, name_):
        showIndent(outfile, level)
        outfile.write('valueOf_ = "%s",\n' % (self.valueOf_,))
    def build(self, node_):
        attrs = node_.attributes
        self.buildAttributes(attrs)
        self.valueOf_ = ''
        for child_ in node_.childNodes:
            nodeName_ = child_.nodeName.split(':')[-1]
            self.buildChildren(child_, nodeName_)
    def buildAttributes(self, attrs):
        pass
    def buildChildren(self, child_, nodeName_):
        if child_.nodeType == Node.TEXT_NODE:
            self.valueOf_ += child_.nodeValue
        elif child_.nodeType == Node.CDATA_SECTION_NODE:
            self.valueOf_ += '![CDATA['+child_.nodeValue+']]'
# end class write


class bitfield(GeneratedsSuper):
    subclass = None
    superclass = None
    def __init__(self, valueOf_=''):
        self.valueOf_ = valueOf_
    def factory(*args_, **kwargs_):
        if bitfield.subclass:
            return bitfield.subclass(*args_, **kwargs_)
        else:
            return bitfield(*args_, **kwargs_)
    factory = staticmethod(factory)
    def getValueOf_(self): return self.valueOf_
    def setValueOf_(self, valueOf_): self.valueOf_ = valueOf_
    def export(self, outfile, level, namespace_='', name_='bitfield', namespacedef_=''):
        showIndent(outfile, level)
        outfile.write('<%s%s %s' % (namespace_, name_, namespacedef_, ))
        self.exportAttributes(outfile, level, namespace_, name_='bitfield')
        if self.hasContent_():
            outfile.write('>\n')
            self.exportChildren(outfile, level + 1, namespace_, name_)
            showIndent(outfile, level)
            outfile.write('</%s%s>\n' % (namespace_, name_))
        else:
            outfile.write(' />\n')
    def exportAttributes(self, outfile, level, namespace_='', name_='bitfield'):
        pass
    def exportChildren(self, outfile, level, namespace_='', name_='bitfield'):
        if self.valueOf_.find('![CDATA')>-1:
            value=quote_xml('%s' % self.valueOf_)
            value=value.replace('![CDATA','<![CDATA')
            value=value.replace(']]',']]>')
            outfile.write(value)
        else:
            outfile.write(quote_xml('%s' % self.valueOf_))
    def hasContent_(self):
        if (
            self.valueOf_ is not None
            ):
            return True
        else:
            return False
    def exportLiteral(self, outfile, level, name_='bitfield'):
        level += 1
        self.exportLiteralAttributes(outfile, level, name_)
        if self.hasContent_():
            self.exportLiteralChildren(outfile, level, name_)
    def exportLiteralAttributes(self, outfile, level, name_):
        pass
    def exportLiteralChildren(self, outfile, level, name_):
        showIndent(outfile, level)
        outfile.write('valueOf_ = "%s",\n' % (self.valueOf_,))
    def build(self, node_):
        attrs = node_.attributes
        self.buildAttributes(attrs)
        self.valueOf_ = ''
        for child_ in node_.childNodes:
            nodeName_ = child_.nodeName.split(':')[-1]
            self.buildChildren(child_, nodeName_)
    def buildAttributes(self, attrs):
        pass
    def buildChildren(self, child_, nodeName_):
        if child_.nodeType == Node.TEXT_NODE:
            self.valueOf_ += child_.nodeValue
        elif child_.nodeType == Node.CDATA_SECTION_NODE:
            self.valueOf_ += '![CDATA['+child_.nodeValue+']]'
# end class bitfield


class descriptionType(GeneratedsSuper):
    subclass = None
    superclass = None
    def __init__(self, title=None, para=None, sect1=None, internal=None, mixedclass_=None, content_=None):
        if mixedclass_ is None:
            self.mixedclass_ = MixedContainer
        else:
            self.mixedclass_ = mixedclass_
        if content_ is None:
            self.content_ = []
        else:
            self.content_ = content_
    def factory(*args_, **kwargs_):
        if descriptionType.subclass:
            return descriptionType.subclass(*args_, **kwargs_)
        else:
            return descriptionType(*args_, **kwargs_)
    factory = staticmethod(factory)
    def get_title(self): return self.title
    def set_title(self, title): self.title = title
    def get_para(self): return self.para
    def set_para(self, para): self.para = para
    def add_para(self, value): self.para.append(value)
    def insert_para(self, index, value): self.para[index] = value
    def get_sect1(self): return self.sect1
    def set_sect1(self, sect1): self.sect1 = sect1
    def add_sect1(self, value): self.sect1.append(value)
    def insert_sect1(self, index, value): self.sect1[index] = value
    def get_internal(self): return self.internal
    def set_internal(self, internal): self.internal = internal
    def export(self, outfile, level, namespace_='', name_='descriptionType', namespacedef_=''):
        showIndent(outfile, level)
        outfile.write('<%s%s %s' % (namespace_, name_, namespacedef_, ))
        self.exportAttributes(outfile, level, namespace_, name_='descriptionType')
        outfile.write('>')
        self.exportChildren(outfile, level + 1, namespace_, name_)
        outfile.write('</%s%s>\n' % (namespace_, name_))
    def exportAttributes(self, outfile, level, namespace_='', name_='descriptionType'):
        pass
    def exportChildren(self, outfile, level, namespace_='', name_='descriptionType'):
        for item_ in self.content_:
            item_.export(outfile, level, item_.name, namespace_)
    def hasContent_(self):
        if (
            self.title is not None or
            self.para is not None or
            self.sect1 is not None or
            self.internal is not None
            ):
            return True
        else:
            return False
    def exportLiteral(self, outfile, level, name_='descriptionType'):
        level += 1
        self.exportLiteralAttributes(outfile, level, name_)
        if self.hasContent_():
            self.exportLiteralChildren(outfile, level, name_)
    def exportLiteralAttributes(self, outfile, level, name_):
        pass
    def exportLiteralChildren(self, outfile, level, name_):
        showIndent(outfile, level)
        outfile.write('content_ = [\n')
        for item_ in self.content_:
            item_.exportLiteral(outfile, level, name_)
        showIndent(outfile, level)
        outfile.write('],\n')
        showIndent(outfile, level)
        outfile.write('content_ = [\n')
        for item_ in self.content_:
            item_.exportLiteral(outfile, level, name_)
        showIndent(outfile, level)
        outfile.write('],\n')
        showIndent(outfile, level)
        outfile.write('content_ = [\n')
        for item_ in self.content_:
            item_.exportLiteral(outfile, level, name_)
        showIndent(outfile, level)
        outfile.write('],\n')
        showIndent(outfile, level)
        outfile.write('content_ = [\n')
        for item_ in self.content_:
            item_.exportLiteral(outfile, level, name_)
        showIndent(outfile, level)
        outfile.write('],\n')
    def build(self, node_):
        attrs = node_.attributes
        self.buildAttributes(attrs)
        for child_ in node_.childNodes:
            nodeName_ = child_.nodeName.split(':')[-1]
            self.buildChildren(child_, nodeName_)
    def buildAttributes(self, attrs):
        pass
    def buildChildren(self, child_, nodeName_):
        if child_.nodeType == Node.ELEMENT_NODE and \
            nodeName_ == 'title':
            childobj_ = docTitleType.factory()
            childobj_.build(child_)
            obj_ = self.mixedclass_(MixedContainer.CategoryComplex,
                MixedContainer.TypeNone, 'title', childobj_)
            self.content_.append(obj_)
        elif child_.nodeType == Node.ELEMENT_NODE and \
            nodeName_ == 'para':
            childobj_ = docParaType.factory()
            childobj_.build(child_)
            obj_ = self.mixedclass_(MixedContainer.CategoryComplex,
                MixedContainer.TypeNone, 'para', childobj_)
            self.content_.append(obj_)
        elif child_.nodeType == Node.ELEMENT_NODE and \
            nodeName_ == 'sect1':
            childobj_ = docSect1Type.factory()
            childobj_.build(child_)
            obj_ = self.mixedclass_(MixedContainer.CategoryComplex,
                MixedContainer.TypeNone, 'sect1', childobj_)
            self.content_.append(obj_)
        elif child_.nodeType == Node.ELEMENT_NODE and \
            nodeName_ == 'internal':
            childobj_ = docInternalType.factory()
            childobj_.build(child_)
            obj_ = self.mixedclass_(MixedContainer.CategoryComplex,
                MixedContainer.TypeNone, 'internal', childobj_)
            self.content_.append(obj_)
        elif child_.nodeType == Node.TEXT_NODE:
            obj_ = self.mixedclass_(MixedContainer.CategoryText,
                MixedContainer.TypeNone, '', child_.nodeValue)
            self.content_.append(obj_)
# end class descriptionType


class enumvalueType(GeneratedsSuper):
    subclass = None
    superclass = None
    def __init__(self, prot=None, id=None, name=None, initializer=None, briefdescription=None, detaileddescription=None, mixedclass_=None, content_=None):
        self.prot = prot
        self.id = id
        if mixedclass_ is None:
            self.mixedclass_ = MixedContainer
        else:
            self.mixedclass_ = mixedclass_
        if content_ is None:
            self.content_ = []
        else:
            self.content_ = content_
    def factory(*args_, **kwargs_):
        if enumvalueType.subclass:
            return enumvalueType.subclass(*args_, **kwargs_)
        else:
            return enumvalueType(*args_, **kwargs_)
    factory = staticmethod(factory)
    def get_name(self): return self.name
    def set_name(self, name): self.name = name
    def get_initializer(self): return self.initializer
    def set_initializer(self, initializer): self.initializer = initializer
    def get_briefdescription(self): return self.briefdescription
    def set_briefdescription(self, briefdescription): self.briefdescription = briefdescription
    def get_detaileddescription(self): return self.detaileddescription
    def set_detaileddescription(self, detaileddescription): self.detaileddescription = detaileddescription
    def get_prot(self): return self.prot
    def set_prot(self, prot): self.prot = prot
    def get_id(self): return self.id
    def set_id(self, id): self.id = id
    def export(self, outfile, level, namespace_='', name_='enumvalueType', namespacedef_=''):
        showIndent(outfile, level)
        outfile.write('<%s%s %s' % (namespace_, name_, namespacedef_, ))
        self.exportAttributes(outfile, level, namespace_, name_='enumvalueType')
        outfile.write('>')
        self.exportChildren(outfile, level + 1, namespace_, name_)
        outfile.write('</%s%s>\n' % (namespace_, name_))
    def exportAttributes(self, outfile, level, namespace_='', name_='enumvalueType'):
        if self.prot is not None:
            outfile.write(' prot=%s' % (quote_attrib(self.prot), ))
        if self.id is not None:
            outfile.write(' id=%s' % (self.format_string(quote_attrib(self.id).encode(ExternalEncoding), input_name='id'), ))
    def exportChildren(self, outfile, level, namespace_='', name_='enumvalueType'):
        for item_ in self.content_:
            item_.export(outfile, level, item_.name, namespace_)
    def hasContent_(self):
        if (
            self.name is not None or
            self.initializer is not None or
            self.briefdescription is not None or
            self.detaileddescription is not None
            ):
            return True
        else:
            return False
    def exportLiteral(self, outfile, level, name_='enumvalueType'):
        level += 1
        self.exportLiteralAttributes(outfile, level, name_)
        if self.hasContent_():
            self.exportLiteralChildren(outfile, level, name_)
    def exportLiteralAttributes(self, outfile, level, name_):
        if self.prot is not None:
            showIndent(outfile, level)
            outfile.write('prot = "%s",\n' % (self.prot,))
        if self.id is not None:
            showIndent(outfile, level)
            outfile.write('id = %s,\n' % (self.id,))
    def exportLiteralChildren(self, outfile, level, name_):
        showIndent(outfile, level)
        outfile.write('content_ = [\n')
        for item_ in self.content_:
            item_.exportLiteral(outfile, level, name_)
        showIndent(outfile, level)
        outfile.write('],\n')
        showIndent(outfile, level)
        outfile.write('content_ = [\n')
        for item_ in self.content_:
            item_.exportLiteral(outfile, level, name_)
        showIndent(outfile, level)
        outfile.write('],\n')
        showIndent(outfile, level)
        outfile.write('content_ = [\n')
        for item_ in self.content_:
            item_.exportLiteral(outfile, level, name_)
        showIndent(outfile, level)
        outfile.write('],\n')
        showIndent(outfile, level)
        outfile.write('content_ = [\n')
        for item_ in self.content_:
            item_.exportLiteral(outfile, level, name_)
        showIndent(outfile, level)
        outfile.write('],\n')
    def build(self, node_):
        attrs = node_.attributes
        self.buildAttributes(attrs)
        for child_ in node_.childNodes:
            nodeName_ = child_.nodeName.split(':')[-1]
            self.buildChildren(child_, nodeName_)
    def buildAttributes(self, attrs):
        if attrs.get('prot'):
            self.prot = attrs.get('prot').value
        if attrs.get('id'):
            self.id = attrs.get('id').value
    def buildChildren(self, child_, nodeName_):
        if child_.nodeType == Node.ELEMENT_NODE and \
            nodeName_ == 'name':
            value_ = []
            for text_ in child_.childNodes:
                value_.append(text_.nodeValue)
            valuestr_ = ''.join(value_)
            obj_ = self.mixedclass_(MixedContainer.CategorySimple,
                MixedContainer.TypeString, 'name', valuestr_)
            self.content_.append(obj_)
        elif child_.nodeType == Node.ELEMENT_NODE and \
            nodeName_ == 'initializer':
            childobj_ = linkedTextType.factory()
            childobj_.build(child_)
            obj_ = self.mixedclass_(MixedContainer.CategoryComplex,
                MixedContainer.TypeNone, 'initializer', childobj_)
            self.content_.append(obj_)
        elif child_.nodeType == Node.ELEMENT_NODE and \
            nodeName_ == 'briefdescription':
            childobj_ = descriptionType.factory()
            childobj_.build(child_)
            obj_ = self.mixedclass_(MixedContainer.CategoryComplex,
                MixedContainer.TypeNone, 'briefdescription', childobj_)
            self.content_.append(obj_)
        elif child_.nodeType == Node.ELEMENT_NODE and \
            nodeName_ == 'detaileddescription':
            childobj_ = descriptionType.factory()
            childobj_.build(child_)
            obj_ = self.mixedclass_(MixedContainer.CategoryComplex,
                MixedContainer.TypeNone, 'detaileddescription', childobj_)
            self.content_.append(obj_)
        elif child_.nodeType == Node.TEXT_NODE:
            obj_ = self.mixedclass_(MixedContainer.CategoryText,
                MixedContainer.TypeNone, '', child_.nodeValue)
            self.content_.append(obj_)
# end class enumvalueType


class templateparamlistType(GeneratedsSuper):
    subclass = None
    superclass = None
    def __init__(self, param=None):
        if param is None:
            self.param = []
        else:
            self.param = param
    def factory(*args_, **kwargs_):
        if templateparamlistType.subclass:
            return templateparamlistType.subclass(*args_, **kwargs_)
        else:
            return templateparamlistType(*args_, **kwargs_)
    factory = staticmethod(factory)
    def get_param(self): return self.param
    def set_param(self, param): self.param = param
    def add_param(self, value): self.param.append(value)
    def insert_param(self, index, value): self.param[index] = value
    def export(self, outfile, level, namespace_='', name_='templateparamlistType', namespacedef_=''):
        showIndent(outfile, level)
        outfile.write('<%s%s %s' % (namespace_, name_, namespacedef_, ))
        self.exportAttributes(outfile, level, namespace_, name_='templateparamlistType')
        if self.hasContent_():
            outfile.write('>\n')
            self.exportChildren(outfile, level + 1, namespace_, name_)
            showIndent(outfile, level)
            outfile.write('</%s%s>\n' % (namespace_, name_))
        else:
            outfile.write(' />\n')
    def exportAttributes(self, outfile, level, namespace_='', name_='templateparamlistType'):
        pass
    def exportChildren(self, outfile, level, namespace_='', name_='templateparamlistType'):
        for param_ in self.param:
            param_.export(outfile, level, namespace_, name_='param')
    def hasContent_(self):
        if (
            self.param is not None
            ):
            return True
        else:
            return False
    def exportLiteral(self, outfile, level, name_='templateparamlistType'):
        level += 1
        self.exportLiteralAttributes(outfile, level, name_)
        if self.hasContent_():
            self.exportLiteralChildren(outfile, level, name_)
    def exportLiteralAttributes(self, outfile, level, name_):
        pass
    def exportLiteralChildren(self, outfile, level, name_):
        showIndent(outfile, level)
        outfile.write('param=[\n')
        level += 1
        for param in self.param:
            showIndent(outfile, level)
            outfile.write('model_.param(\n')
            param.exportLiteral(outfile, level, name_='param')
            showIndent(outfile, level)
            outfile.write('),\n')
        level -= 1
        showIndent(outfile, level)
        outfile.write('],\n')
    def build(self, node_):
        attrs = node_.attributes
        self.buildAttributes(attrs)
        for child_ in node_.childNodes:
            nodeName_ = child_.nodeName.split(':')[-1]
            self.buildChildren(child_, nodeName_)
    def buildAttributes(self, attrs):
        pass
    def buildChildren(self, child_, nodeName_):
        if child_.nodeType == Node.ELEMENT_NODE and \
            nodeName_ == 'param':
            obj_ = paramType.factory()
            obj_.build(child_)
            self.param.append(obj_)
# end class templateparamlistType


class paramType(GeneratedsSuper):
    subclass = None
    superclass = None
    def __init__(self, type_=None, declname=None, defname=None, array=None, defval=None, briefdescription=None):
        self.type_ = type_
        self.declname = declname
        self.defname = defname
        self.array = array
        self.defval = defval
        self.briefdescription = briefdescription
    def factory(*args_, **kwargs_):
        if paramType.subclass:
            return paramType.subclass(*args_, **kwargs_)
        else:
            return paramType(*args_, **kwargs_)
    factory = staticmethod(factory)
    def get_type(self): return self.type_
    def set_type(self, type_): self.type_ = type_
    def get_declname(self): return self.declname
    def set_declname(self, declname): self.declname = declname
    def get_defname(self): return self.defname
    def set_defname(self, defname): self.defname = defname
    def get_array(self): return self.array
    def set_array(self, array): self.array = array
    def get_defval(self): return self.defval
    def set_defval(self, defval): self.defval = defval
    def get_briefdescription(self): return self.briefdescription
    def set_briefdescription(self, briefdescription): self.briefdescription = briefdescription
    def export(self, outfile, level, namespace_='', name_='paramType', namespacedef_=''):
        showIndent(outfile, level)
        outfile.write('<%s%s %s' % (namespace_, name_, namespacedef_, ))
        self.exportAttributes(outfile, level, namespace_, name_='paramType')
        if self.hasContent_():
            outfile.write('>\n')
            self.exportChildren(outfile, level + 1, namespace_, name_)
            showIndent(outfile, level)
            outfile.write('</%s%s>\n' % (namespace_, name_))
        else:
            outfile.write(' />\n')
    def exportAttributes(self, outfile, level, namespace_='', name_='paramType'):
        pass
    def exportChildren(self, outfile, level, namespace_='', name_='paramType'):
        if self.type_:
            self.type_.export(outfile, level, namespace_, name_='type')
        if self.declname is not None:
            showIndent(outfile, level)
            outfile.write('<%sdeclname>%s</%sdeclname>\n' % (namespace_, self.format_string(quote_xml(self.declname).encode(ExternalEncoding), input_name='declname'), namespace_))
        if self.defname is not None:
            showIndent(outfile, level)
            outfile.write('<%sdefname>%s</%sdefname>\n' % (namespace_, self.format_string(quote_xml(self.defname).encode(ExternalEncoding), input_name='defname'), namespace_))
        if self.array is not None:
            showIndent(outfile, level)
            outfile.write('<%sarray>%s</%sarray>\n' % (namespace_, self.format_string(quote_xml(self.array).encode(ExternalEncoding), input_name='array'), namespace_))
        if self.defval:
            self.defval.export(outfile, level, namespace_, name_='defval')
        if self.briefdescription:
            self.briefdescription.export(outfile, level, namespace_, name_='briefdescription')
    def hasContent_(self):
        if (
            self.type_ is not None or
            self.declname is not None or
            self.defname is not None or
            self.array is not None or
            self.defval is not None or
            self.briefdescription is not None
            ):
            return True
        else:
            return False
    def exportLiteral(self, outfile, level, name_='paramType'):
        level += 1
        self.exportLiteralAttributes(outfile, level, name_)
        if self.hasContent_():
            self.exportLiteralChildren(outfile, level, name_)
    def exportLiteralAttributes(self, outfile, level, name_):
        pass
    def exportLiteralChildren(self, outfile, level, name_):
        if self.type_:
            showIndent(outfile, level)
            outfile.write('type_=model_.linkedTextType(\n')
            self.type_.exportLiteral(outfile, level, name_='type')
            showIndent(outfile, level)
            outfile.write('),\n')
        showIndent(outfile, level)
        outfile.write('declname=%s,\n' % quote_python(self.declname).encode(ExternalEncoding))
        showIndent(outfile, level)
        outfile.write('defname=%s,\n' % quote_python(self.defname).encode(ExternalEncoding))
        showIndent(outfile, level)
        outfile.write('array=%s,\n' % quote_python(self.array).encode(ExternalEncoding))
        if self.defval:
            showIndent(outfile, level)
            outfile.write('defval=model_.linkedTextType(\n')
            self.defval.exportLiteral(outfile, level, name_='defval')
            showIndent(outfile, level)
            outfile.write('),\n')
        if self.briefdescription:
            showIndent(outfile, level)
            outfile.write('briefdescription=model_.descriptionType(\n')
            self.briefdescription.exportLiteral(outfile, level, name_='briefdescription')
            showIndent(outfile, level)
            outfile.write('),\n')
    def build(self, node_):
        attrs = node_.attributes
        self.buildAttributes(attrs)
        for child_ in node_.childNodes:
            nodeName_ = child_.nodeName.split(':')[-1]
            self.buildChildren(child_, nodeName_)
    def buildAttributes(self, attrs):
        pass
    def buildChildren(self, child_, nodeName_):
        if child_.nodeType == Node.ELEMENT_NODE and \
            nodeName_ == 'type':
            obj_ = linkedTextType.factory()
            obj_.build(child_)
            self.set_type(obj_)
        elif child_.nodeType == Node.ELEMENT_NODE and \
            nodeName_ == 'declname':
            declname_ = ''
            for text__content_ in child_.childNodes:
                declname_ += text__content_.nodeValue
            self.declname = declname_
        elif child_.nodeType == Node.ELEMENT_NODE and \
            nodeName_ == 'defname':
            defname_ = ''
            for text__content_ in child_.childNodes:
                defname_ += text__content_.nodeValue
            self.defname = defname_
        elif child_.nodeType == Node.ELEMENT_NODE and \
            nodeName_ == 'array':
            array_ = ''
            for text__content_ in child_.childNodes:
                array_ += text__content_.nodeValue
            self.array = array_
        elif child_.nodeType == Node.ELEMENT_NODE and \
            nodeName_ == 'defval':
            obj_ = linkedTextType.factory()
            obj_.build(child_)
            self.set_defval(obj_)
        elif child_.nodeType == Node.ELEMENT_NODE and \
            nodeName_ == 'briefdescription':
            obj_ = descriptionType.factory()
            obj_.build(child_)
            self.set_briefdescription(obj_)
# end class paramType


class declname(GeneratedsSuper):
    subclass = None
    superclass = None
    def __init__(self, valueOf_=''):
        self.valueOf_ = valueOf_
    def factory(*args_, **kwargs_):
        if declname.subclass:
            return declname.subclass(*args_, **kwargs_)
        else:
            return declname(*args_, **kwargs_)
    factory = staticmethod(factory)
    def getValueOf_(self): return self.valueOf_
    def setValueOf_(self, valueOf_): self.valueOf_ = valueOf_
    def export(self, outfile, level, namespace_='', name_='declname', namespacedef_=''):
        showIndent(outfile, level)
        outfile.write('<%s%s %s' % (namespace_, name_, namespacedef_, ))
        self.exportAttributes(outfile, level, namespace_, name_='declname')
        if self.hasContent_():
            outfile.write('>\n')
            self.exportChildren(outfile, level + 1, namespace_, name_)
            showIndent(outfile, level)
            outfile.write('</%s%s>\n' % (namespace_, name_))
        else:
            outfile.write(' />\n')
    def exportAttributes(self, outfile, level, namespace_='', name_='declname'):
        pass
    def exportChildren(self, outfile, level, namespace_='', name_='declname'):
        if self.valueOf_.find('![CDATA')>-1:
            value=quote_xml('%s' % self.valueOf_)
            value=value.replace('![CDATA','<![CDATA')
            value=value.replace(']]',']]>')
            outfile.write(value)
        else:
            outfile.write(quote_xml('%s' % self.valueOf_))
    def hasContent_(self):
        if (
            self.valueOf_ is not None
            ):
            return True
        else:
            return False
    def exportLiteral(self, outfile, level, name_='declname'):
        level += 1
        self.exportLiteralAttributes(outfile, level, name_)
        if self.hasContent_():
            self.exportLiteralChildren(outfile, level, name_)
    def exportLiteralAttributes(self, outfile, level, name_):
        pass
    def exportLiteralChildren(self, outfile, level, name_):
        showIndent(outfile, level)
        outfile.write('valueOf_ = "%s",\n' % (self.valueOf_,))
    def build(self, node_):
        attrs = node_.attributes
        self.buildAttributes(attrs)
        self.valueOf_ = ''
        for child_ in node_.childNodes:
            nodeName_ = child_.nodeName.split(':')[-1]
            self.buildChildren(child_, nodeName_)
    def buildAttributes(self, attrs):
        pass
    def buildChildren(self, child_, nodeName_):
        if child_.nodeType == Node.TEXT_NODE:
            self.valueOf_ += child_.nodeValue
        elif child_.nodeType == Node.CDATA_SECTION_NODE:
            self.valueOf_ += '![CDATA['+child_.nodeValue+']]'
# end class declname


class defname(GeneratedsSuper):
    subclass = None
    superclass = None
    def __init__(self, valueOf_=''):
        self.valueOf_ = valueOf_
    def factory(*args_, **kwargs_):
        if defname.subclass:
            return defname.subclass(*args_, **kwargs_)
        else:
            return defname(*args_, **kwargs_)
    factory = staticmethod(factory)
    def getValueOf_(self): return self.valueOf_
    def setValueOf_(self, valueOf_): self.valueOf_ = valueOf_
    def export(self, outfile, level, namespace_='', name_='defname', namespacedef_=''):
        showIndent(outfile, level)
        outfile.write('<%s%s %s' % (namespace_, name_, namespacedef_, ))
        self.exportAttributes(outfile, level, namespace_, name_='defname')
        if self.hasContent_():
            outfile.write('>\n')
            self.exportChildren(outfile, level + 1, namespace_, name_)
            showIndent(outfile, level)
            outfile.write('</%s%s>\n' % (namespace_, name_))
        else:
            outfile.write(' />\n')
    def exportAttributes(self, outfile, level, namespace_='', name_='defname'):
        pass
    def exportChildren(self, outfile, level, namespace_='', name_='defname'):
        if self.valueOf_.find('![CDATA')>-1:
            value=quote_xml('%s' % self.valueOf_)
            value=value.replace('![CDATA','<![CDATA')
            value=value.replace(']]',']]>')
            outfile.write(value)
        else:
            outfile.write(quote_xml('%s' % self.valueOf_))
    def hasContent_(self):
        if (
            self.valueOf_ is not None
            ):
            return True
        else:
            return False
    def exportLiteral(self, outfile, level, name_='defname'):
        level += 1
        self.exportLiteralAttributes(outfile, level, name_)
        if self.hasContent_():
            self.exportLiteralChildren(outfile, level, name_)
    def exportLiteralAttributes(self, outfile, level, name_):
        pass
    def exportLiteralChildren(self, outfile, level, name_):
        showIndent(outfile, level)
        outfile.write('valueOf_ = "%s",\n' % (self.valueOf_,))
    def build(self, node_):
        attrs = node_.attributes
        self.buildAttributes(attrs)
        self.valueOf_ = ''
        for child_ in node_.childNodes:
            nodeName_ = child_.nodeName.split(':')[-1]
            self.buildChildren(child_, nodeName_)
    def buildAttributes(self, attrs):
        pass
    def buildChildren(self, child_, nodeName_):
        if child_.nodeType == Node.TEXT_NODE:
            self.valueOf_ += child_.nodeValue
        elif child_.nodeType == Node.CDATA_SECTION_NODE:
            self.valueOf_ += '![CDATA['+child_.nodeValue+']]'
# end class defname


class array(GeneratedsSuper):
    subclass = None
    superclass = None
    def __init__(self, valueOf_=''):
        self.valueOf_ = valueOf_
    def factory(*args_, **kwargs_):
        if array.subclass:
            return array.subclass(*args_, **kwargs_)
        else:
            return array(*args_, **kwargs_)
    factory = staticmethod(factory)
    def getValueOf_(self): return self.valueOf_
    def setValueOf_(self, valueOf_): self.valueOf_ = valueOf_
    def export(self, outfile, level, namespace_='', name_='array', namespacedef_=''):
        showIndent(outfile, level)
        outfile.write('<%s%s %s' % (namespace_, name_, namespacedef_, ))
        self.exportAttributes(outfile, level, namespace_, name_='array')
        if self.hasContent_():
            outfile.write('>\n')
            self.exportChildren(outfile, level + 1, namespace_, name_)
            showIndent(outfile, level)
            outfile.write('</%s%s>\n' % (namespace_, name_))
        else:
            outfile.write(' />\n')
    def exportAttributes(self, outfile, level, namespace_='', name_='array'):
        pass
    def exportChildren(self, outfile, level, namespace_='', name_='array'):
        if self.valueOf_.find('![CDATA')>-1:
            value=quote_xml('%s' % self.valueOf_)
            value=value.replace('![CDATA','<![CDATA')
            value=value.replace(']]',']]>')
            outfile.write(value)
        else:
            outfile.write(quote_xml('%s' % self.valueOf_))
    def hasContent_(self):
        if (
            self.valueOf_ is not None
            ):
            return True
        else:
            return False
    def exportLiteral(self, outfile, level, name_='array'):
        level += 1
        self.exportLiteralAttributes(outfile, level, name_)
        if self.hasContent_():
            self.exportLiteralChildren(outfile, level, name_)
    def exportLiteralAttributes(self, outfile, level, name_):
        pass
    def exportLiteralChildren(self, outfile, level, name_):
        showIndent(outfile, level)
        outfile.write('valueOf_ = "%s",\n' % (self.valueOf_,))
    def build(self, node_):
        attrs = node_.attributes
        self.buildAttributes(attrs)
        self.valueOf_ = ''
        for child_ in node_.childNodes:
            nodeName_ = child_.nodeName.split(':')[-1]
            self.buildChildren(child_, nodeName_)
    def buildAttributes(self, attrs):
        pass
    def buildChildren(self, child_, nodeName_):
        if child_.nodeType == Node.TEXT_NODE:
            self.valueOf_ += child_.nodeValue
        elif child_.nodeType == Node.CDATA_SECTION_NODE:
            self.valueOf_ += '![CDATA['+child_.nodeValue+']]'
# end class array


class linkedTextType(GeneratedsSuper):
    subclass = None
    superclass = None
    def __init__(self, ref=None, mixedclass_=None, content_=None):
        if mixedclass_ is None:
            self.mixedclass_ = MixedContainer
        else:
            self.mixedclass_ = mixedclass_
        if content_ is None:
            self.content_ = []
        else:
            self.content_ = content_
    def factory(*args_, **kwargs_):
        if linkedTextType.subclass:
            return linkedTextType.subclass(*args_, **kwargs_)
        else:
            return linkedTextType(*args_, **kwargs_)
    factory = staticmethod(factory)
    def get_ref(self): return self.ref
    def set_ref(self, ref): self.ref = ref
    def add_ref(self, value): self.ref.append(value)
    def insert_ref(self, index, value): self.ref[index] = value
    def export(self, outfile, level, namespace_='', name_='linkedTextType', namespacedef_=''):
        showIndent(outfile, level)
        outfile.write('<%s%s %s' % (namespace_, name_, namespacedef_, ))
        self.exportAttributes(outfile, level, namespace_, name_='linkedTextType')
        outfile.write('>')
        self.exportChildren(outfile, level + 1, namespace_, name_)
        outfile.write('</%s%s>\n' % (namespace_, name_))
    def exportAttributes(self, outfile, level, namespace_='', name_='linkedTextType'):
        pass
    def exportChildren(self, outfile, level, namespace_='', name_='linkedTextType'):
        for item_ in self.content_:
            item_.export(outfile, level, item_.name, namespace_)
    def hasContent_(self):
        if (
            self.ref is not None
            ):
            return True
        else:
            return False
    def exportLiteral(self, outfile, level, name_='linkedTextType'):
        level += 1
        self.exportLiteralAttributes(outfile, level, name_)
        if self.hasContent_():
            self.exportLiteralChildren(outfile, level, name_)
    def exportLiteralAttributes(self, outfile, level, name_):
        pass
    def exportLiteralChildren(self, outfile, level, name_):
        showIndent(outfile, level)
        outfile.write('content_ = [\n')
        for item_ in self.content_:
            item_.exportLiteral(outfile, level, name_)
        showIndent(outfile, level)
        outfile.write('],\n')
    def build(self, node_):
        attrs = node_.attributes
        self.buildAttributes(attrs)
        for child_ in node_.childNodes:
            nodeName_ = child_.nodeName.split(':')[-1]
            self.buildChildren(child_, nodeName_)
    def buildAttributes(self, attrs):
        pass
    def buildChildren(self, child_, nodeName_):
        if child_.nodeType == Node.ELEMENT_NODE and \
            nodeName_ == 'ref':
            childobj_ = docRefTextType.factory()
            childobj_.build(child_)
            obj_ = self.mixedclass_(MixedContainer.CategoryComplex,
                MixedContainer.TypeNone, 'ref', childobj_)
            self.content_.append(obj_)
        elif child_.nodeType == Node.TEXT_NODE:
            obj_ = self.mixedclass_(MixedContainer.CategoryText,
                MixedContainer.TypeNone, '', child_.nodeValue)
            self.content_.append(obj_)
# end class linkedTextType


class graphType(GeneratedsSuper):
    subclass = None
    superclass = None
    def __init__(self, node=None):
        if node is None:
            self.node = []
        else:
            self.node = node
    def factory(*args_, **kwargs_):
        if graphType.subclass:
            return graphType.subclass(*args_, **kwargs_)
        else:
            return graphType(*args_, **kwargs_)
    factory = staticmethod(factory)
    def get_node(self): return self.node
    def set_node(self, node): self.node = node
    def add_node(self, value): self.node.append(value)
    def insert_node(self, index, value): self.node[index] = value
    def export(self, outfile, level, namespace_='', name_='graphType', namespacedef_=''):
        showIndent(outfile, level)
        outfile.write('<%s%s %s' % (namespace_, name_, namespacedef_, ))
        self.exportAttributes(outfile, level, namespace_, name_='graphType')
        if self.hasContent_():
            outfile.write('>\n')
            self.exportChildren(outfile, level + 1, namespace_, name_)
            showIndent(outfile, level)
            outfile.write('</%s%s>\n' % (namespace_, name_))
        else:
            outfile.write(' />\n')
    def exportAttributes(self, outfile, level, namespace_='', name_='graphType'):
        pass
    def exportChildren(self, outfile, level, namespace_='', name_='graphType'):
        for node_ in self.node:
            node_.export(outfile, level, namespace_, name_='node')
    def hasContent_(self):
        if (
            self.node is not None
            ):
            return True
        else:
            return False
    def exportLiteral(self, outfile, level, name_='graphType'):
        level += 1
        self.exportLiteralAttributes(outfile, level, name_)
        if self.hasContent_():
            self.exportLiteralChildren(outfile, level, name_)
    def exportLiteralAttributes(self, outfile, level, name_):
        pass
    def exportLiteralChildren(self, outfile, level, name_):
        showIndent(outfile, level)
        outfile.write('node=[\n')
        level += 1
        for node in self.node:
            showIndent(outfile, level)
            outfile.write('model_.node(\n')
            node.exportLiteral(outfile, level, name_='node')
            showIndent(outfile, level)
            outfile.write('),\n')
        level -= 1
        showIndent(outfile, level)
        outfile.write('],\n')
    def build(self, node_):
        attrs = node_.attributes
        self.buildAttributes(attrs)
        for child_ in node_.childNodes:
            nodeName_ = child_.nodeName.split(':')[-1]
            self.buildChildren(child_, nodeName_)
    def buildAttributes(self, attrs):
        pass
    def buildChildren(self, child_, nodeName_):
        if child_.nodeType == Node.ELEMENT_NODE and \
            nodeName_ == 'node':
            obj_ = nodeType.factory()
            obj_.build(child_)
            self.node.append(obj_)
# end class graphType


class nodeType(GeneratedsSuper):
    subclass = None
    superclass = None
    def __init__(self, id=None, label=None, link=None, childnode=None):
        self.id = id
        self.label = label
        self.link = link
        if childnode is None:
            self.childnode = []
        else:
            self.childnode = childnode
    def factory(*args_, **kwargs_):
        if nodeType.subclass:
            return nodeType.subclass(*args_, **kwargs_)
        else:
            return nodeType(*args_, **kwargs_)
    factory = staticmethod(factory)
    def get_label(self): return self.label
    def set_label(self, label): self.label = label
    def get_link(self): return self.link
    def set_link(self, link): self.link = link
    def get_childnode(self): return self.childnode
    def set_childnode(self, childnode): self.childnode = childnode
    def add_childnode(self, value): self.childnode.append(value)
    def insert_childnode(self, index, value): self.childnode[index] = value
    def get_id(self): return self.id
    def set_id(self, id): self.id = id
    def export(self, outfile, level, namespace_='', name_='nodeType', namespacedef_=''):
        showIndent(outfile, level)
        outfile.write('<%s%s %s' % (namespace_, name_, namespacedef_, ))
        self.exportAttributes(outfile, level, namespace_, name_='nodeType')
        if self.hasContent_():
            outfile.write('>\n')
            self.exportChildren(outfile, level + 1, namespace_, name_)
            showIndent(outfile, level)
            outfile.write('</%s%s>\n' % (namespace_, name_))
        else:
            outfile.write(' />\n')
    def exportAttributes(self, outfile, level, namespace_='', name_='nodeType'):
        if self.id is not None:
            outfile.write(' id=%s' % (self.format_string(quote_attrib(self.id).encode(ExternalEncoding), input_name='id'), ))
    def exportChildren(self, outfile, level, namespace_='', name_='nodeType'):
        if self.label is not None:
            showIndent(outfile, level)
            outfile.write('<%slabel>%s</%slabel>\n' % (namespace_, self.format_string(quote_xml(self.label).encode(ExternalEncoding), input_name='label'), namespace_))
        if self.link:
            self.link.export(outfile, level, namespace_, name_='link')
        for childnode_ in self.childnode:
            childnode_.export(outfile, level, namespace_, name_='childnode')
    def hasContent_(self):
        if (
            self.label is not None or
            self.link is not None or
            self.childnode is not None
            ):
            return True
        else:
            return False
    def exportLiteral(self, outfile, level, name_='nodeType'):
        level += 1
        self.exportLiteralAttributes(outfile, level, name_)
        if self.hasContent_():
            self.exportLiteralChildren(outfile, level, name_)
    def exportLiteralAttributes(self, outfile, level, name_):
        if self.id is not None:
            showIndent(outfile, level)
            outfile.write('id = %s,\n' % (self.id,))
    def exportLiteralChildren(self, outfile, level, name_):
        showIndent(outfile, level)
        outfile.write('label=%s,\n' % quote_python(self.label).encode(ExternalEncoding))
        if self.link:
            showIndent(outfile, level)
            outfile.write('link=model_.linkType(\n')
            self.link.exportLiteral(outfile, level, name_='link')
            showIndent(outfile, level)
            outfile.write('),\n')
        showIndent(outfile, level)
        outfile.write('childnode=[\n')
        level += 1
        for childnode in self.childnode:
            showIndent(outfile, level)
            outfile.write('model_.childnode(\n')
            childnode.exportLiteral(outfile, level, name_='childnode')
            showIndent(outfile, level)
            outfile.write('),\n')
        level -= 1
        showIndent(outfile, level)
        outfile.write('],\n')
    def build(self, node_):
        attrs = node_.attributes
        self.buildAttributes(attrs)
        for child_ in node_.childNodes:
            nodeName_ = child_.nodeName.split(':')[-1]
            self.buildChildren(child_, nodeName_)
    def buildAttributes(self, attrs):
        if attrs.get('id'):
            self.id = attrs.get('id').value
    def buildChildren(self, child_, nodeName_):
        if child_.nodeType == Node.ELEMENT_NODE and \
            nodeName_ == 'label':
            label_ = ''
            for text__content_ in child_.childNodes:
                label_ += text__content_.nodeValue
            self.label = label_
        elif child_.nodeType == Node.ELEMENT_NODE and \
            nodeName_ == 'link':
            obj_ = linkType.factory()
            obj_.build(child_)
            self.set_link(obj_)
        elif child_.nodeType == Node.ELEMENT_NODE and \
            nodeName_ == 'childnode':
            obj_ = childnodeType.factory()
            obj_.build(child_)
            self.childnode.append(obj_)
# end class nodeType


class label(GeneratedsSuper):
    subclass = None
    superclass = None
    def __init__(self, valueOf_=''):
        self.valueOf_ = valueOf_
    def factory(*args_, **kwargs_):
        if label.subclass:
            return label.subclass(*args_, **kwargs_)
        else:
            return label(*args_, **kwargs_)
    factory = staticmethod(factory)
    def getValueOf_(self): return self.valueOf_
    def setValueOf_(self, valueOf_): self.valueOf_ = valueOf_
    def export(self, outfile, level, namespace_='', name_='label', namespacedef_=''):
        showIndent(outfile, level)
        outfile.write('<%s%s %s' % (namespace_, name_, namespacedef_, ))
        self.exportAttributes(outfile, level, namespace_, name_='label')
        if self.hasContent_():
            outfile.write('>\n')
            self.exportChildren(outfile, level + 1, namespace_, name_)
            showIndent(outfile, level)
            outfile.write('</%s%s>\n' % (namespace_, name_))
        else:
            outfile.write(' />\n')
    def exportAttributes(self, outfile, level, namespace_='', name_='label'):
        pass
    def exportChildren(self, outfile, level, namespace_='', name_='label'):
        if self.valueOf_.find('![CDATA')>-1:
            value=quote_xml('%s' % self.valueOf_)
            value=value.replace('![CDATA','<![CDATA')
            value=value.replace(']]',']]>')
            outfile.write(value)
        else:
            outfile.write(quote_xml('%s' % self.valueOf_))
    def hasContent_(self):
        if (
            self.valueOf_ is not None
            ):
            return True
        else:
            return False
    def exportLiteral(self, outfile, level, name_='label'):
        level += 1
        self.exportLiteralAttributes(outfile, level, name_)
        if self.hasContent_():
            self.exportLiteralChildren(outfile, level, name_)
    def exportLiteralAttributes(self, outfile, level, name_):
        pass
    def exportLiteralChildren(self, outfile, level, name_):
        showIndent(outfile, level)
        outfile.write('valueOf_ = "%s",\n' % (self.valueOf_,))
    def build(self, node_):
        attrs = node_.attributes
        self.buildAttributes(attrs)
        self.valueOf_ = ''
        for child_ in node_.childNodes:
            nodeName_ = child_.nodeName.split(':')[-1]
            self.buildChildren(child_, nodeName_)
    def buildAttributes(self, attrs):
        pass
    def buildChildren(self, child_, nodeName_):
        if child_.nodeType == Node.TEXT_NODE:
            self.valueOf_ += child_.nodeValue
        elif child_.nodeType == Node.CDATA_SECTION_NODE:
            self.valueOf_ += '![CDATA['+child_.nodeValue+']]'
# end class label


class childnodeType(GeneratedsSuper):
    subclass = None
    superclass = None
    def __init__(self, relation=None, refid=None, edgelabel=None):
        self.relation = relation
        self.refid = refid
        if edgelabel is None:
            self.edgelabel = []
        else:
            self.edgelabel = edgelabel
    def factory(*args_, **kwargs_):
        if childnodeType.subclass:
            return childnodeType.subclass(*args_, **kwargs_)
        else:
            return childnodeType(*args_, **kwargs_)
    factory = staticmethod(factory)
    def get_edgelabel(self): return self.edgelabel
    def set_edgelabel(self, edgelabel): self.edgelabel = edgelabel
    def add_edgelabel(self, value): self.edgelabel.append(value)
    def insert_edgelabel(self, index, value): self.edgelabel[index] = value
    def get_relation(self): return self.relation
    def set_relation(self, relation): self.relation = relation
    def get_refid(self): return self.refid
    def set_refid(self, refid): self.refid = refid
    def export(self, outfile, level, namespace_='', name_='childnodeType', namespacedef_=''):
        showIndent(outfile, level)
        outfile.write('<%s%s %s' % (namespace_, name_, namespacedef_, ))
        self.exportAttributes(outfile, level, namespace_, name_='childnodeType')
        if self.hasContent_():
            outfile.write('>\n')
            self.exportChildren(outfile, level + 1, namespace_, name_)
            showIndent(outfile, level)
            outfile.write('</%s%s>\n' % (namespace_, name_))
        else:
            outfile.write(' />\n')
    def exportAttributes(self, outfile, level, namespace_='', name_='childnodeType'):
        if self.relation is not None:
            outfile.write(' relation=%s' % (quote_attrib(self.relation), ))
        if self.refid is not None:
            outfile.write(' refid=%s' % (self.format_string(quote_attrib(self.refid).encode(ExternalEncoding), input_name='refid'), ))
    def exportChildren(self, outfile, level, namespace_='', name_='childnodeType'):
        for edgelabel_ in self.edgelabel:
            showIndent(outfile, level)
            outfile.write('<%sedgelabel>%s</%sedgelabel>\n' % (namespace_, self.format_string(quote_xml(edgelabel_).encode(ExternalEncoding), input_name='edgelabel'), namespace_))
    def hasContent_(self):
        if (
            self.edgelabel is not None
            ):
            return True
        else:
            return False
    def exportLiteral(self, outfile, level, name_='childnodeType'):
        level += 1
        self.exportLiteralAttributes(outfile, level, name_)
        if self.hasContent_():
            self.exportLiteralChildren(outfile, level, name_)
    def exportLiteralAttributes(self, outfile, level, name_):
        if self.relation is not None:
            showIndent(outfile, level)
            outfile.write('relation = "%s",\n' % (self.relation,))
        if self.refid is not None:
            showIndent(outfile, level)
            outfile.write('refid = %s,\n' % (self.refid,))
    def exportLiteralChildren(self, outfile, level, name_):
        showIndent(outfile, level)
        outfile.write('edgelabel=[\n')
        level += 1
        for edgelabel in self.edgelabel:
            showIndent(outfile, level)
            outfile.write('%s,\n' % quote_python(edgelabel).encode(ExternalEncoding))
        level -= 1
        showIndent(outfile, level)
        outfile.write('],\n')
    def build(self, node_):
        attrs = node_.attributes
        self.buildAttributes(attrs)
        for child_ in node_.childNodes:
            nodeName_ = child_.nodeName.split(':')[-1]
            self.buildChildren(child_, nodeName_)
    def buildAttributes(self, attrs):
        if attrs.get('relation'):
            self.relation = attrs.get('relation').value
        if attrs.get('refid'):
            self.refid = attrs.get('refid').value
    def buildChildren(self, child_, nodeName_):
        if child_.nodeType == Node.ELEMENT_NODE and \
            nodeName_ == 'edgelabel':
            edgelabel_ = ''
            for text__content_ in child_.childNodes:
                edgelabel_ += text__content_.nodeValue
            self.edgelabel.append(edgelabel_)
# end class childnodeType


class edgelabel(GeneratedsSuper):
    subclass = None
    superclass = None
    def __init__(self, valueOf_=''):
        self.valueOf_ = valueOf_
    def factory(*args_, **kwargs_):
        if edgelabel.subclass:
            return edgelabel.subclass(*args_, **kwargs_)
        else:
            return edgelabel(*args_, **kwargs_)
    factory = staticmethod(factory)
    def getValueOf_(self): return self.valueOf_
    def setValueOf_(self, valueOf_): self.valueOf_ = valueOf_
    def export(self, outfile, level, namespace_='', name_='edgelabel', namespacedef_=''):
        showIndent(outfile, level)
        outfile.write('<%s%s %s' % (namespace_, name_, namespacedef_, ))
        self.exportAttributes(outfile, level, namespace_, name_='edgelabel')
        if self.hasContent_():
            outfile.write('>\n')
            self.exportChildren(outfile, level + 1, namespace_, name_)
            showIndent(outfile, level)
            outfile.write('</%s%s>\n' % (namespace_, name_))
        else:
            outfile.write(' />\n')
    def exportAttributes(self, outfile, level, namespace_='', name_='edgelabel'):
        pass
    def exportChildren(self, outfile, level, namespace_='', name_='edgelabel'):
        if self.valueOf_.find('![CDATA')>-1:
            value=quote_xml('%s' % self.valueOf_)
            value=value.replace('![CDATA','<![CDATA')
            value=value.replace(']]',']]>')
            outfile.write(value)
        else:
            outfile.write(quote_xml('%s' % self.valueOf_))
    def hasContent_(self):
        if (
            self.valueOf_ is not None
            ):
            return True
        else:
            return False
    def exportLiteral(self, outfile, level, name_='edgelabel'):
        level += 1
        self.exportLiteralAttributes(outfile, level, name_)
        if self.hasContent_():
            self.exportLiteralChildren(outfile, level, name_)
    def exportLiteralAttributes(self, outfile, level, name_):
        pass
    def exportLiteralChildren(self, outfile, level, name_):
        showIndent(outfile, level)
        outfile.write('valueOf_ = "%s",\n' % (self.valueOf_,))
    def build(self, node_):
        attrs = node_.attributes
        self.buildAttributes(attrs)
        self.valueOf_ = ''
        for child_ in node_.childNodes:
            nodeName_ = child_.nodeName.split(':')[-1]
            self.buildChildren(child_, nodeName_)
    def buildAttributes(self, attrs):
        pass
    def buildChildren(self, child_, nodeName_):
        if child_.nodeType == Node.TEXT_NODE:
            self.valueOf_ += child_.nodeValue
        elif child_.nodeType == Node.CDATA_SECTION_NODE:
            self.valueOf_ += '![CDATA['+child_.nodeValue+']]'
# end class edgelabel


class linkType(GeneratedsSuper):
    subclass = None
    superclass = None
    def __init__(self, refid=None, external=None, valueOf_=''):
        self.refid = refid
        self.external = external
        self.valueOf_ = valueOf_
    def factory(*args_, **kwargs_):
        if linkType.subclass:
            return linkType.subclass(*args_, **kwargs_)
        else:
            return linkType(*args_, **kwargs_)
    factory = staticmethod(factory)
    def get_refid(self): return self.refid
    def set_refid(self, refid): self.refid = refid
    def get_external(self): return self.external
    def set_external(self, external): self.external = external
    def getValueOf_(self): return self.valueOf_
    def setValueOf_(self, valueOf_): self.valueOf_ = valueOf_
    def export(self, outfile, level, namespace_='', name_='linkType', namespacedef_=''):
        showIndent(outfile, level)
        outfile.write('<%s%s %s' % (namespace_, name_, namespacedef_, ))
        self.exportAttributes(outfile, level, namespace_, name_='linkType')
        if self.hasContent_():
            outfile.write('>\n')
            self.exportChildren(outfile, level + 1, namespace_, name_)
            showIndent(outfile, level)
            outfile.write('</%s%s>\n' % (namespace_, name_))
        else:
            outfile.write(' />\n')
    def exportAttributes(self, outfile, level, namespace_='', name_='linkType'):
        if self.refid is not None:
            outfile.write(' refid=%s' % (self.format_string(quote_attrib(self.refid).encode(ExternalEncoding), input_name='refid'), ))
        if self.external is not None:
            outfile.write(' external=%s' % (self.format_string(quote_attrib(self.external).encode(ExternalEncoding), input_name='external'), ))
    def exportChildren(self, outfile, level, namespace_='', name_='linkType'):
        if self.valueOf_.find('![CDATA')>-1:
            value=quote_xml('%s' % self.valueOf_)
            value=value.replace('![CDATA','<![CDATA')
            value=value.replace(']]',']]>')
            outfile.write(value)
        else:
            outfile.write(quote_xml('%s' % self.valueOf_))
    def hasContent_(self):
        if (
            self.valueOf_ is not None
            ):
            return True
        else:
            return False
    def exportLiteral(self, outfile, level, name_='linkType'):
        level += 1
        self.exportLiteralAttributes(outfile, level, name_)
        if self.hasContent_():
            self.exportLiteralChildren(outfile, level, name_)
    def exportLiteralAttributes(self, outfile, level, name_):
        if self.refid is not None:
            showIndent(outfile, level)
            outfile.write('refid = %s,\n' % (self.refid,))
        if self.external is not None:
            showIndent(outfile, level)
            outfile.write('external = %s,\n' % (self.external,))
    def exportLiteralChildren(self, outfile, level, name_):
        showIndent(outfile, level)
        outfile.write('valueOf_ = "%s",\n' % (self.valueOf_,))
    def build(self, node_):
        attrs = node_.attributes
        self.buildAttributes(attrs)
        self.valueOf_ = ''
        for child_ in node_.childNodes:
            nodeName_ = child_.nodeName.split(':')[-1]
            self.buildChildren(child_, nodeName_)
    def buildAttributes(self, attrs):
        if attrs.get('refid'):
            self.refid = attrs.get('refid').value
        if attrs.get('external'):
            self.external = attrs.get('external').value
    def buildChildren(self, child_, nodeName_):
        if child_.nodeType == Node.TEXT_NODE:
            self.valueOf_ += child_.nodeValue
        elif child_.nodeType == Node.CDATA_SECTION_NODE:
            self.valueOf_ += '![CDATA['+child_.nodeValue+']]'
# end class linkType


class listingType(GeneratedsSuper):
    subclass = None
    superclass = None
    def __init__(self, codeline=None):
        if codeline is None:
            self.codeline = []
        else:
            self.codeline = codeline
    def factory(*args_, **kwargs_):
        if listingType.subclass:
            return listingType.subclass(*args_, **kwargs_)
        else:
            return listingType(*args_, **kwargs_)
    factory = staticmethod(factory)
    def get_codeline(self): return self.codeline
    def set_codeline(self, codeline): self.codeline = codeline
    def add_codeline(self, value): self.codeline.append(value)
    def insert_codeline(self, index, value): self.codeline[index] = value
    def export(self, outfile, level, namespace_='', name_='listingType', namespacedef_=''):
        showIndent(outfile, level)
        outfile.write('<%s%s %s' % (namespace_, name_, namespacedef_, ))
        self.exportAttributes(outfile, level, namespace_, name_='listingType')
        if self.hasContent_():
            outfile.write('>\n')
            self.exportChildren(outfile, level + 1, namespace_, name_)
            showIndent(outfile, level)
            outfile.write('</%s%s>\n' % (namespace_, name_))
        else:
            outfile.write(' />\n')
    def exportAttributes(self, outfile, level, namespace_='', name_='listingType'):
        pass
    def exportChildren(self, outfile, level, namespace_='', name_='listingType'):
        for codeline_ in self.codeline:
            codeline_.export(outfile, level, namespace_, name_='codeline')
    def hasContent_(self):
        if (
            self.codeline is not None
            ):
            return True
        else:
            return False
    def exportLiteral(self, outfile, level, name_='listingType'):
        level += 1
        self.exportLiteralAttributes(outfile, level, name_)
        if self.hasContent_():
            self.exportLiteralChildren(outfile, level, name_)
    def exportLiteralAttributes(self, outfile, level, name_):
        pass
    def exportLiteralChildren(self, outfile, level, name_):
        showIndent(outfile, level)
        outfile.write('codeline=[\n')
        level += 1
        for codeline in self.codeline:
            showIndent(outfile, level)
            outfile.write('model_.codeline(\n')
            codeline.exportLiteral(outfile, level, name_='codeline')
            showIndent(outfile, level)
            outfile.write('),\n')
        level -= 1
        showIndent(outfile, level)
        outfile.write('],\n')
    def build(self, node_):
        attrs = node_.attributes
        self.buildAttributes(attrs)
        for child_ in node_.childNodes:
            nodeName_ = child_.nodeName.split(':')[-1]
            self.buildChildren(child_, nodeName_)
    def buildAttributes(self, attrs):
        pass
    def buildChildren(self, child_, nodeName_):
        if child_.nodeType == Node.ELEMENT_NODE and \
            nodeName_ == 'codeline':
            obj_ = codelineType.factory()
            obj_.build(child_)
            self.codeline.append(obj_)
# end class listingType


class codelineType(GeneratedsSuper):
    subclass = None
    superclass = None
    def __init__(self, external=None, lineno=None, refkind=None, refid=None, highlight=None):
        self.external = external
        self.lineno = lineno
        self.refkind = refkind
        self.refid = refid
        if highlight is None:
            self.highlight = []
        else:
            self.highlight = highlight
    def factory(*args_, **kwargs_):
        if codelineType.subclass:
            return codelineType.subclass(*args_, **kwargs_)
        else:
            return codelineType(*args_, **kwargs_)
    factory = staticmethod(factory)
    def get_highlight(self): return self.highlight
    def set_highlight(self, highlight): self.highlight = highlight
    def add_highlight(self, value): self.highlight.append(value)
    def insert_highlight(self, index, value): self.highlight[index] = value
    def get_external(self): return self.external
    def set_external(self, external): self.external = external
    def get_lineno(self): return self.lineno
    def set_lineno(self, lineno): self.lineno = lineno
    def get_refkind(self): return self.refkind
    def set_refkind(self, refkind): self.refkind = refkind
    def get_refid(self): return self.refid
    def set_refid(self, refid): self.refid = refid
    def export(self, outfile, level, namespace_='', name_='codelineType', namespacedef_=''):
        showIndent(outfile, level)
        outfile.write('<%s%s %s' % (namespace_, name_, namespacedef_, ))
        self.exportAttributes(outfile, level, namespace_, name_='codelineType')
        if self.hasContent_():
            outfile.write('>\n')
            self.exportChildren(outfile, level + 1, namespace_, name_)
            showIndent(outfile, level)
            outfile.write('</%s%s>\n' % (namespace_, name_))
        else:
            outfile.write(' />\n')
    def exportAttributes(self, outfile, level, namespace_='', name_='codelineType'):
        if self.external is not None:
            outfile.write(' external=%s' % (quote_attrib(self.external), ))
        if self.lineno is not None:
            outfile.write(' lineno="%s"' % self.format_integer(self.lineno, input_name='lineno'))
        if self.refkind is not None:
            outfile.write(' refkind=%s' % (quote_attrib(self.refkind), ))
        if self.refid is not None:
            outfile.write(' refid=%s' % (self.format_string(quote_attrib(self.refid).encode(ExternalEncoding), input_name='refid'), ))
    def exportChildren(self, outfile, level, namespace_='', name_='codelineType'):
        for highlight_ in self.highlight:
            highlight_.export(outfile, level, namespace_, name_='highlight')
    def hasContent_(self):
        if (
            self.highlight is not None
            ):
            return True
        else:
            return False
    def exportLiteral(self, outfile, level, name_='codelineType'):
        level += 1
        self.exportLiteralAttributes(outfile, level, name_)
        if self.hasContent_():
            self.exportLiteralChildren(outfile, level, name_)
    def exportLiteralAttributes(self, outfile, level, name_):
        if self.external is not None:
            showIndent(outfile, level)
            outfile.write('external = "%s",\n' % (self.external,))
        if self.lineno is not None:
            showIndent(outfile, level)
            outfile.write('lineno = %s,\n' % (self.lineno,))
        if self.refkind is not None:
            showIndent(outfile, level)
            outfile.write('refkind = "%s",\n' % (self.refkind,))
        if self.refid is not None:
            showIndent(outfile, level)
            outfile.write('refid = %s,\n' % (self.refid,))
    def exportLiteralChildren(self, outfile, level, name_):
        showIndent(outfile, level)
        outfile.write('highlight=[\n')
        level += 1
        for highlight in self.highlight:
            showIndent(outfile, level)
            outfile.write('model_.highlight(\n')
            highlight.exportLiteral(outfile, level, name_='highlight')
            showIndent(outfile, level)
            outfile.write('),\n')
        level -= 1
        showIndent(outfile, level)
        outfile.write('],\n')
    def build(self, node_):
        attrs = node_.attributes
        self.buildAttributes(attrs)
        for child_ in node_.childNodes:
            nodeName_ = child_.nodeName.split(':')[-1]
            self.buildChildren(child_, nodeName_)
    def buildAttributes(self, attrs):
        if attrs.get('external'):
            self.external = attrs.get('external').value
        if attrs.get('lineno'):
            try:
                self.lineno = int(attrs.get('lineno').value)
            except ValueError, exp:
                raise ValueError('Bad integer attribute (lineno): %s' % exp)
        if attrs.get('refkind'):
            self.refkind = attrs.get('refkind').value
        if attrs.get('refid'):
            self.refid = attrs.get('refid').value
    def buildChildren(self, child_, nodeName_):
        if child_.nodeType == Node.ELEMENT_NODE and \
            nodeName_ == 'highlight':
            obj_ = highlightType.factory()
            obj_.build(child_)
            self.highlight.append(obj_)
# end class codelineType


class highlightType(GeneratedsSuper):
    subclass = None
    superclass = None
    def __init__(self, classxx=None, sp=None, ref=None, mixedclass_=None, content_=None):
        self.classxx = classxx
        if mixedclass_ is None:
            self.mixedclass_ = MixedContainer
        else:
            self.mixedclass_ = mixedclass_
        if content_ is None:
            self.content_ = []
        else:
            self.content_ = content_
    def factory(*args_, **kwargs_):
        if highlightType.subclass:
            return highlightType.subclass(*args_, **kwargs_)
        else:
            return highlightType(*args_, **kwargs_)
    factory = staticmethod(factory)
    def get_sp(self): return self.sp
    def set_sp(self, sp): self.sp = sp
    def add_sp(self, value): self.sp.append(value)
    def insert_sp(self, index, value): self.sp[index] = value
    def get_ref(self): return self.ref
    def set_ref(self, ref): self.ref = ref
    def add_ref(self, value): self.ref.append(value)
    def insert_ref(self, index, value): self.ref[index] = value
    def get_class(self): return self.classxx
    def set_class(self, classxx): self.classxx = classxx
    def export(self, outfile, level, namespace_='', name_='highlightType', namespacedef_=''):
        showIndent(outfile, level)
        outfile.write('<%s%s %s' % (namespace_, name_, namespacedef_, ))
        self.exportAttributes(outfile, level, namespace_, name_='highlightType')
        outfile.write('>')
        self.exportChildren(outfile, level + 1, namespace_, name_)
        outfile.write('</%s%s>\n' % (namespace_, name_))
    def exportAttributes(self, outfile, level, namespace_='', name_='highlightType'):
        if self.classxx is not None:
            outfile.write(' class=%s' % (quote_attrib(self.classxx), ))
    def exportChildren(self, outfile, level, namespace_='', name_='highlightType'):
        for item_ in self.content_:
            item_.export(outfile, level, item_.name, namespace_)
    def hasContent_(self):
        if (
            self.sp is not None or
            self.ref is not None
            ):
            return True
        else:
            return False
    def exportLiteral(self, outfile, level, name_='highlightType'):
        level += 1
        self.exportLiteralAttributes(outfile, level, name_)
        if self.hasContent_():
            self.exportLiteralChildren(outfile, level, name_)
    def exportLiteralAttributes(self, outfile, level, name_):
        if self.classxx is not None:
            showIndent(outfile, level)
            outfile.write('classxx = "%s",\n' % (self.classxx,))
    def exportLiteralChildren(self, outfile, level, name_):
        showIndent(outfile, level)
        outfile.write('content_ = [\n')
        for item_ in self.content_:
            item_.exportLiteral(outfile, level, name_)
        showIndent(outfile, level)
        outfile.write('],\n')
        showIndent(outfile, level)
        outfile.write('content_ = [\n')
        for item_ in self.content_:
            item_.exportLiteral(outfile, level, name_)
        showIndent(outfile, level)
        outfile.write('],\n')
    def build(self, node_):
        attrs = node_.attributes
        self.buildAttributes(attrs)
        for child_ in node_.childNodes:
            nodeName_ = child_.nodeName.split(':')[-1]
            self.buildChildren(child_, nodeName_)
    def buildAttributes(self, attrs):
        if attrs.get('class'):
            self.classxx = attrs.get('class').value
    def buildChildren(self, child_, nodeName_):
        if child_.nodeType == Node.ELEMENT_NODE and \
            nodeName_ == 'sp':
            value_ = []
            for text_ in child_.childNodes:
                value_.append(text_.nodeValue)
            valuestr_ = ''.join(value_)
            obj_ = self.mixedclass_(MixedContainer.CategorySimple,
                MixedContainer.TypeString, 'sp', valuestr_)
            self.content_.append(obj_)
        elif child_.nodeType == Node.ELEMENT_NODE and \
            nodeName_ == 'ref':
            childobj_ = docRefTextType.factory()
            childobj_.build(child_)
            obj_ = self.mixedclass_(MixedContainer.CategoryComplex,
                MixedContainer.TypeNone, 'ref', childobj_)
            self.content_.append(obj_)
        elif child_.nodeType == Node.TEXT_NODE:
            obj_ = self.mixedclass_(MixedContainer.CategoryText,
                MixedContainer.TypeNone, '', child_.nodeValue)
            self.content_.append(obj_)
# end class highlightType


class sp(GeneratedsSuper):
    subclass = None
    superclass = None
    def __init__(self, valueOf_=''):
        self.valueOf_ = valueOf_
    def factory(*args_, **kwargs_):
        if sp.subclass:
            return sp.subclass(*args_, **kwargs_)
        else:
            return sp(*args_, **kwargs_)
    factory = staticmethod(factory)
    def getValueOf_(self): return self.valueOf_
    def setValueOf_(self, valueOf_): self.valueOf_ = valueOf_
    def export(self, outfile, level, namespace_='', name_='sp', namespacedef_=''):
        showIndent(outfile, level)
        outfile.write('<%s%s %s' % (namespace_, name_, namespacedef_, ))
        self.exportAttributes(outfile, level, namespace_, name_='sp')
        if self.hasContent_():
            outfile.write('>\n')
            self.exportChildren(outfile, level + 1, namespace_, name_)
            showIndent(outfile, level)
            outfile.write('</%s%s>\n' % (namespace_, name_))
        else:
            outfile.write(' />\n')
    def exportAttributes(self, outfile, level, namespace_='', name_='sp'):
        pass
    def exportChildren(self, outfile, level, namespace_='', name_='sp'):
        if self.valueOf_.find('![CDATA')>-1:
            value=quote_xml('%s' % self.valueOf_)
            value=value.replace('![CDATA','<![CDATA')
            value=value.replace(']]',']]>')
            outfile.write(value)
        else:
            outfile.write(quote_xml('%s' % self.valueOf_))
    def hasContent_(self):
        if (
            self.valueOf_ is not None
            ):
            return True
        else:
            return False
    def exportLiteral(self, outfile, level, name_='sp'):
        level += 1
        self.exportLiteralAttributes(outfile, level, name_)
        if self.hasContent_():
            self.exportLiteralChildren(outfile, level, name_)
    def exportLiteralAttributes(self, outfile, level, name_):
        pass
    def exportLiteralChildren(self, outfile, level, name_):
        showIndent(outfile, level)
        outfile.write('valueOf_ = "%s",\n' % (self.valueOf_,))
    def build(self, node_):
        attrs = node_.attributes
        self.buildAttributes(attrs)
        self.valueOf_ = ''
        for child_ in node_.childNodes:
            nodeName_ = child_.nodeName.split(':')[-1]
            self.buildChildren(child_, nodeName_)
    def buildAttributes(self, attrs):
        pass
    def buildChildren(self, child_, nodeName_):
        if child_.nodeType == Node.TEXT_NODE:
            self.valueOf_ += child_.nodeValue
        elif child_.nodeType == Node.CDATA_SECTION_NODE:
            self.valueOf_ += '![CDATA['+child_.nodeValue+']]'
# end class sp


class referenceType(GeneratedsSuper):
    subclass = None
    superclass = None
    def __init__(self, endline=None, startline=None, refid=None, compoundref=None, valueOf_='', mixedclass_=None, content_=None):
        self.endline = endline
        self.startline = startline
        self.refid = refid
        self.compoundref = compoundref
        if mixedclass_ is None:
            self.mixedclass_ = MixedContainer
        else:
            self.mixedclass_ = mixedclass_
        if content_ is None:
            self.content_ = []
        else:
            self.content_ = content_
    def factory(*args_, **kwargs_):
        if referenceType.subclass:
            return referenceType.subclass(*args_, **kwargs_)
        else:
            return referenceType(*args_, **kwargs_)
    factory = staticmethod(factory)
    def get_endline(self): return self.endline
    def set_endline(self, endline): self.endline = endline
    def get_startline(self): return self.startline
    def set_startline(self, startline): self.startline = startline
    def get_refid(self): return self.refid
    def set_refid(self, refid): self.refid = refid
    def get_compoundref(self): return self.compoundref
    def set_compoundref(self, compoundref): self.compoundref = compoundref
    def getValueOf_(self): return self.valueOf_
    def setValueOf_(self, valueOf_): self.valueOf_ = valueOf_
    def export(self, outfile, level, namespace_='', name_='referenceType', namespacedef_=''):
        showIndent(outfile, level)
        outfile.write('<%s%s %s' % (namespace_, name_, namespacedef_, ))
        self.exportAttributes(outfile, level, namespace_, name_='referenceType')
        outfile.write('>')
        self.exportChildren(outfile, level + 1, namespace_, name_)
        outfile.write('</%s%s>\n' % (namespace_, name_))
    def exportAttributes(self, outfile, level, namespace_='', name_='referenceType'):
        if self.endline is not None:
            outfile.write(' endline="%s"' % self.format_integer(self.endline, input_name='endline'))
        if self.startline is not None:
            outfile.write(' startline="%s"' % self.format_integer(self.startline, input_name='startline'))
        if self.refid is not None:
            outfile.write(' refid=%s' % (self.format_string(quote_attrib(self.refid).encode(ExternalEncoding), input_name='refid'), ))
        if self.compoundref is not None:
            outfile.write(' compoundref=%s' % (self.format_string(quote_attrib(self.compoundref).encode(ExternalEncoding), input_name='compoundref'), ))
    def exportChildren(self, outfile, level, namespace_='', name_='referenceType'):
        if self.valueOf_.find('![CDATA')>-1:
            value=quote_xml('%s' % self.valueOf_)
            value=value.replace('![CDATA','<![CDATA')
            value=value.replace(']]',']]>')
            outfile.write(value)
        else:
            outfile.write(quote_xml('%s' % self.valueOf_))
    def hasContent_(self):
        if (
            self.valueOf_ is not None
            ):
            return True
        else:
            return False
    def exportLiteral(self, outfile, level, name_='referenceType'):
        level += 1
        self.exportLiteralAttributes(outfile, level, name_)
        if self.hasContent_():
            self.exportLiteralChildren(outfile, level, name_)
    def exportLiteralAttributes(self, outfile, level, name_):
        if self.endline is not None:
            showIndent(outfile, level)
            outfile.write('endline = %s,\n' % (self.endline,))
        if self.startline is not None:
            showIndent(outfile, level)
            outfile.write('startline = %s,\n' % (self.startline,))
        if self.refid is not None:
            showIndent(outfile, level)
            outfile.write('refid = %s,\n' % (self.refid,))
        if self.compoundref is not None:
            showIndent(outfile, level)
            outfile.write('compoundref = %s,\n' % (self.compoundref,))
    def exportLiteralChildren(self, outfile, level, name_):
        showIndent(outfile, level)
        outfile.write('valueOf_ = "%s",\n' % (self.valueOf_,))
    def build(self, node_):
        attrs = node_.attributes
        self.buildAttributes(attrs)
        self.valueOf_ = ''
        for child_ in node_.childNodes:
            nodeName_ = child_.nodeName.split(':')[-1]
            self.buildChildren(child_, nodeName_)
    def buildAttributes(self, attrs):
        if attrs.get('endline'):
            try:
                self.endline = int(attrs.get('endline').value)
            except ValueError, exp:
                raise ValueError('Bad integer attribute (endline): %s' % exp)
        if attrs.get('startline'):
            try:
                self.startline = int(attrs.get('startline').value)
            except ValueError, exp:
                raise ValueError('Bad integer attribute (startline): %s' % exp)
        if attrs.get('refid'):
            self.refid = attrs.get('refid').value
        if attrs.get('compoundref'):
            self.compoundref = attrs.get('compoundref').value
    def buildChildren(self, child_, nodeName_):
        if child_.nodeType == Node.TEXT_NODE:
            obj_ = self.mixedclass_(MixedContainer.CategoryText,
                MixedContainer.TypeNone, '', child_.nodeValue)
            self.content_.append(obj_)
        if child_.nodeType == Node.TEXT_NODE:
            self.valueOf_ += child_.nodeValue
        elif child_.nodeType == Node.CDATA_SECTION_NODE:
            self.valueOf_ += '![CDATA['+child_.nodeValue+']]'
# end class referenceType


class locationType(GeneratedsSuper):
    subclass = None
    superclass = None
    def __init__(self, bodystart=None, line=None, bodyend=None, bodyfile=None, file=None, valueOf_=''):
        self.bodystart = bodystart
        self.line = line
        self.bodyend = bodyend
        self.bodyfile = bodyfile
        self.file = file
        self.valueOf_ = valueOf_
    def factory(*args_, **kwargs_):
        if locationType.subclass:
            return locationType.subclass(*args_, **kwargs_)
        else:
            return locationType(*args_, **kwargs_)
    factory = staticmethod(factory)
    def get_bodystart(self): return self.bodystart
    def set_bodystart(self, bodystart): self.bodystart = bodystart
    def get_line(self): return self.line
    def set_line(self, line): self.line = line
    def get_bodyend(self): return self.bodyend
    def set_bodyend(self, bodyend): self.bodyend = bodyend
    def get_bodyfile(self): return self.bodyfile
    def set_bodyfile(self, bodyfile): self.bodyfile = bodyfile
    def get_file(self): return self.file
    def set_file(self, file): self.file = file
    def getValueOf_(self): return self.valueOf_
    def setValueOf_(self, valueOf_): self.valueOf_ = valueOf_
    def export(self, outfile, level, namespace_='', name_='locationType', namespacedef_=''):
        showIndent(outfile, level)
        outfile.write('<%s%s %s' % (namespace_, name_, namespacedef_, ))
        self.exportAttributes(outfile, level, namespace_, name_='locationType')
        if self.hasContent_():
            outfile.write('>\n')
            self.exportChildren(outfile, level + 1, namespace_, name_)
            showIndent(outfile, level)
            outfile.write('</%s%s>\n' % (namespace_, name_))
        else:
            outfile.write(' />\n')
    def exportAttributes(self, outfile, level, namespace_='', name_='locationType'):
        if self.bodystart is not None:
            outfile.write(' bodystart="%s"' % self.format_integer(self.bodystart, input_name='bodystart'))
        if self.line is not None:
            outfile.write(' line="%s"' % self.format_integer(self.line, input_name='line'))
        if self.bodyend is not None:
            outfile.write(' bodyend="%s"' % self.format_integer(self.bodyend, input_name='bodyend'))
        if self.bodyfile is not None:
            outfile.write(' bodyfile=%s' % (self.format_string(quote_attrib(self.bodyfile).encode(ExternalEncoding), input_name='bodyfile'), ))
        if self.file is not None:
            outfile.write(' file=%s' % (self.format_string(quote_attrib(self.file).encode(ExternalEncoding), input_name='file'), ))
    def exportChildren(self, outfile, level, namespace_='', name_='locationType'):
        if self.valueOf_.find('![CDATA')>-1:
            value=quote_xml('%s' % self.valueOf_)
            value=value.replace('![CDATA','<![CDATA')
            value=value.replace(']]',']]>')
            outfile.write(value)
        else:
            outfile.write(quote_xml('%s' % self.valueOf_))
    def hasContent_(self):
        if (
            self.valueOf_ is not None
            ):
            return True
        else:
            return False
    def exportLiteral(self, outfile, level, name_='locationType'):
        level += 1
        self.exportLiteralAttributes(outfile, level, name_)
        if self.hasContent_():
            self.exportLiteralChildren(outfile, level, name_)
    def exportLiteralAttributes(self, outfile, level, name_):
        if self.bodystart is not None:
            showIndent(outfile, level)
            outfile.write('bodystart = %s,\n' % (self.bodystart,))
        if self.line is not None:
            showIndent(outfile, level)
            outfile.write('line = %s,\n' % (self.line,))
        if self.bodyend is not None:
            showIndent(outfile, level)
            outfile.write('bodyend = %s,\n' % (self.bodyend,))
        if self.bodyfile is not None:
            showIndent(outfile, level)
            outfile.write('bodyfile = %s,\n' % (self.bodyfile,))
        if self.file is not None:
            showIndent(outfile, level)
            outfile.write('file = %s,\n' % (self.file,))
    def exportLiteralChildren(self, outfile, level, name_):
        showIndent(outfile, level)
        outfile.write('valueOf_ = "%s",\n' % (self.valueOf_,))
    def build(self, node_):
        attrs = node_.attributes
        self.buildAttributes(attrs)
        self.valueOf_ = ''
        for child_ in node_.childNodes:
            nodeName_ = child_.nodeName.split(':')[-1]
            self.buildChildren(child_, nodeName_)
    def buildAttributes(self, attrs):
        if attrs.get('bodystart'):
            try:
                self.bodystart = int(attrs.get('bodystart').value)
            except ValueError, exp:
                raise ValueError('Bad integer attribute (bodystart): %s' % exp)
        if attrs.get('line'):
            try:
                self.line = int(attrs.get('line').value)
            except ValueError, exp:
                raise ValueError('Bad integer attribute (line): %s' % exp)
        if attrs.get('bodyend'):
            try:
                self.bodyend = int(attrs.get('bodyend').value)
            except ValueError, exp:
                raise ValueError('Bad integer attribute (bodyend): %s' % exp)
        if attrs.get('bodyfile'):
            self.bodyfile = attrs.get('bodyfile').value
        if attrs.get('file'):
            self.file = attrs.get('file').value
    def buildChildren(self, child_, nodeName_):
        if child_.nodeType == Node.TEXT_NODE:
            self.valueOf_ += child_.nodeValue
        elif child_.nodeType == Node.CDATA_SECTION_NODE:
            self.valueOf_ += '![CDATA['+child_.nodeValue+']]'
# end class locationType


class docSect1Type(GeneratedsSuper):
    subclass = None
    superclass = None
    def __init__(self, id=None, title=None, para=None, sect2=None, internal=None, mixedclass_=None, content_=None):
        self.id = id
        if mixedclass_ is None:
            self.mixedclass_ = MixedContainer
        else:
            self.mixedclass_ = mixedclass_
        if content_ is None:
            self.content_ = []
        else:
            self.content_ = content_
    def factory(*args_, **kwargs_):
        if docSect1Type.subclass:
            return docSect1Type.subclass(*args_, **kwargs_)
        else:
            return docSect1Type(*args_, **kwargs_)
    factory = staticmethod(factory)
    def get_title(self): return self.title
    def set_title(self, title): self.title = title
    def get_para(self): return self.para
    def set_para(self, para): self.para = para
    def add_para(self, value): self.para.append(value)
    def insert_para(self, index, value): self.para[index] = value
    def get_sect2(self): return self.sect2
    def set_sect2(self, sect2): self.sect2 = sect2
    def add_sect2(self, value): self.sect2.append(value)
    def insert_sect2(self, index, value): self.sect2[index] = value
    def get_internal(self): return self.internal
    def set_internal(self, internal): self.internal = internal
    def get_id(self): return self.id
    def set_id(self, id): self.id = id
    def export(self, outfile, level, namespace_='', name_='docSect1Type', namespacedef_=''):
        showIndent(outfile, level)
        outfile.write('<%s%s %s' % (namespace_, name_, namespacedef_, ))
        self.exportAttributes(outfile, level, namespace_, name_='docSect1Type')
        outfile.write('>')
        self.exportChildren(outfile, level + 1, namespace_, name_)
        outfile.write('</%s%s>\n' % (namespace_, name_))
    def exportAttributes(self, outfile, level, namespace_='', name_='docSect1Type'):
        if self.id is not None:
            outfile.write(' id=%s' % (self.format_string(quote_attrib(self.id).encode(ExternalEncoding), input_name='id'), ))
    def exportChildren(self, outfile, level, namespace_='', name_='docSect1Type'):
        for item_ in self.content_:
            item_.export(outfile, level, item_.name, namespace_)
    def hasContent_(self):
        if (
            self.title is not None or
            self.para is not None or
            self.sect2 is not None or
            self.internal is not None
            ):
            return True
        else:
            return False
    def exportLiteral(self, outfile, level, name_='docSect1Type'):
        level += 1
        self.exportLiteralAttributes(outfile, level, name_)
        if self.hasContent_():
            self.exportLiteralChildren(outfile, level, name_)
    def exportLiteralAttributes(self, outfile, level, name_):
        if self.id is not None:
            showIndent(outfile, level)
            outfile.write('id = %s,\n' % (self.id,))
    def exportLiteralChildren(self, outfile, level, name_):
        showIndent(outfile, level)
        outfile.write('content_ = [\n')
        for item_ in self.content_:
            item_.exportLiteral(outfile, level, name_)
        showIndent(outfile, level)
        outfile.write('],\n')
        showIndent(outfile, level)
        outfile.write('content_ = [\n')
        for item_ in self.content_:
            item_.exportLiteral(outfile, level, name_)
        showIndent(outfile, level)
        outfile.write('],\n')
        showIndent(outfile, level)
        outfile.write('content_ = [\n')
        for item_ in self.content_:
            item_.exportLiteral(outfile, level, name_)
        showIndent(outfile, level)
        outfile.write('],\n')
        showIndent(outfile, level)
        outfile.write('content_ = [\n')
        for item_ in self.content_:
            item_.exportLiteral(outfile, level, name_)
        showIndent(outfile, level)
        outfile.write('],\n')
    def build(self, node_):
        attrs = node_.attributes
        self.buildAttributes(attrs)
        for child_ in node_.childNodes:
            nodeName_ = child_.nodeName.split(':')[-1]
            self.buildChildren(child_, nodeName_)
    def buildAttributes(self, attrs):
        if attrs.get('id'):
            self.id = attrs.get('id').value
    def buildChildren(self, child_, nodeName_):
        if child_.nodeType == Node.ELEMENT_NODE and \
            nodeName_ == 'title':
            childobj_ = docTitleType.factory()
            childobj_.build(child_)
            obj_ = self.mixedclass_(MixedContainer.CategoryComplex,
                MixedContainer.TypeNone, 'title', childobj_)
            self.content_.append(obj_)
        elif child_.nodeType == Node.ELEMENT_NODE and \
            nodeName_ == 'para':
            childobj_ = docParaType.factory()
            childobj_.build(child_)
            obj_ = self.mixedclass_(MixedContainer.CategoryComplex,
                MixedContainer.TypeNone, 'para', childobj_)
            self.content_.append(obj_)
        elif child_.nodeType == Node.ELEMENT_NODE and \
            nodeName_ == 'sect2':
            childobj_ = docSect2Type.factory()
            childobj_.build(child_)
            obj_ = self.mixedclass_(MixedContainer.CategoryComplex,
                MixedContainer.TypeNone, 'sect2', childobj_)
            self.content_.append(obj_)
        elif child_.nodeType == Node.ELEMENT_NODE and \
            nodeName_ == 'internal':
            childobj_ = docInternalS1Type.factory()
            childobj_.build(child_)
            obj_ = self.mixedclass_(MixedContainer.CategoryComplex,
                MixedContainer.TypeNone, 'internal', childobj_)
            self.content_.append(obj_)
        elif child_.nodeType == Node.TEXT_NODE:
            obj_ = self.mixedclass_(MixedContainer.CategoryText,
                MixedContainer.TypeNone, '', child_.nodeValue)
            self.content_.append(obj_)
# end class docSect1Type


class docSect2Type(GeneratedsSuper):
    subclass = None
    superclass = None
    def __init__(self, id=None, title=None, para=None, sect3=None, internal=None, mixedclass_=None, content_=None):
        self.id = id
        if mixedclass_ is None:
            self.mixedclass_ = MixedContainer
        else:
            self.mixedclass_ = mixedclass_
        if content_ is None:
            self.content_ = []
        else:
            self.content_ = content_
    def factory(*args_, **kwargs_):
        if docSect2Type.subclass:
            return docSect2Type.subclass(*args_, **kwargs_)
        else:
            return docSect2Type(*args_, **kwargs_)
    factory = staticmethod(factory)
    def get_title(self): return self.title
    def set_title(self, title): self.title = title
    def get_para(self): return self.para
    def set_para(self, para): self.para = para
    def add_para(self, value): self.para.append(value)
    def insert_para(self, index, value): self.para[index] = value
    def get_sect3(self): return self.sect3
    def set_sect3(self, sect3): self.sect3 = sect3
    def add_sect3(self, value): self.sect3.append(value)
    def insert_sect3(self, index, value): self.sect3[index] = value
    def get_internal(self): return self.internal
    def set_internal(self, internal): self.internal = internal
    def get_id(self): return self.id
    def set_id(self, id): self.id = id
    def export(self, outfile, level, namespace_='', name_='docSect2Type', namespacedef_=''):
        showIndent(outfile, level)
        outfile.write('<%s%s %s' % (namespace_, name_, namespacedef_, ))
        self.exportAttributes(outfile, level, namespace_, name_='docSect2Type')
        outfile.write('>')
        self.exportChildren(outfile, level + 1, namespace_, name_)
        outfile.write('</%s%s>\n' % (namespace_, name_))
    def exportAttributes(self, outfile, level, namespace_='', name_='docSect2Type'):
        if self.id is not None:
            outfile.write(' id=%s' % (self.format_string(quote_attrib(self.id).encode(ExternalEncoding), input_name='id'), ))
    def exportChildren(self, outfile, level, namespace_='', name_='docSect2Type'):
        for item_ in self.content_:
            item_.export(outfile, level, item_.name, namespace_)
    def hasContent_(self):
        if (
            self.title is not None or
            self.para is not None or
            self.sect3 is not None or
            self.internal is not None
            ):
            return True
        else:
            return False
    def exportLiteral(self, outfile, level, name_='docSect2Type'):
        level += 1
        self.exportLiteralAttributes(outfile, level, name_)
        if self.hasContent_():
            self.exportLiteralChildren(outfile, level, name_)
    def exportLiteralAttributes(self, outfile, level, name_):
        if self.id is not None:
            showIndent(outfile, level)
            outfile.write('id = %s,\n' % (self.id,))
    def exportLiteralChildren(self, outfile, level, name_):
        showIndent(outfile, level)
        outfile.write('content_ = [\n')
        for item_ in self.content_:
            item_.exportLiteral(outfile, level, name_)
        showIndent(outfile, level)
        outfile.write('],\n')
        showIndent(outfile, level)
        outfile.write('content_ = [\n')
        for item_ in self.content_:
            item_.exportLiteral(outfile, level, name_)
        showIndent(outfile, level)
        outfile.write('],\n')
        showIndent(outfile, level)
        outfile.write('content_ = [\n')
        for item_ in self.content_:
            item_.exportLiteral(outfile, level, name_)
        showIndent(outfile, level)
        outfile.write('],\n')
        showIndent(outfile, level)
        outfile.write('content_ = [\n')
        for item_ in self.content_:
            item_.exportLiteral(outfile, level, name_)
        showIndent(outfile, level)
        outfile.write('],\n')
    def build(self, node_):
        attrs = node_.attributes
        self.buildAttributes(attrs)
        for child_ in node_.childNodes:
            nodeName_ = child_.nodeName.split(':')[-1]
            self.buildChildren(child_, nodeName_)
    def buildAttributes(self, attrs):
        if attrs.get('id'):
            self.id = attrs.get('id').value
    def buildChildren(self, child_, nodeName_):
        if child_.nodeType == Node.ELEMENT_NODE and \
            nodeName_ == 'title':
            childobj_ = docTitleType.factory()
            childobj_.build(child_)
            obj_ = self.mixedclass_(MixedContainer.CategoryComplex,
                MixedContainer.TypeNone, 'title', childobj_)
            self.content_.append(obj_)
        elif child_.nodeType == Node.ELEMENT_NODE and \
            nodeName_ == 'para':
            childobj_ = docParaType.factory()
            childobj_.build(child_)
            obj_ = self.mixedclass_(MixedContainer.CategoryComplex,
                MixedContainer.TypeNone, 'para', childobj_)
            self.content_.append(obj_)
        elif child_.nodeType == Node.ELEMENT_NODE and \
            nodeName_ == 'sect3':
            childobj_ = docSect3Type.factory()
            childobj_.build(child_)
            obj_ = self.mixedclass_(MixedContainer.CategoryComplex,
                MixedContainer.TypeNone, 'sect3', childobj_)
            self.content_.append(obj_)
        elif child_.nodeType == Node.ELEMENT_NODE and \
            nodeName_ == 'internal':
            childobj_ = docInternalS2Type.factory()
            childobj_.build(child_)
            obj_ = self.mixedclass_(MixedContainer.CategoryComplex,
                MixedContainer.TypeNone, 'internal', childobj_)
            self.content_.append(obj_)
        elif child_.nodeType == Node.TEXT_NODE:
            obj_ = self.mixedclass_(MixedContainer.CategoryText,
                MixedContainer.TypeNone, '', child_.nodeValue)
            self.content_.append(obj_)
# end class docSect2Type


class docSect3Type(GeneratedsSuper):
    subclass = None
    superclass = None
    def __init__(self, id=None, title=None, para=None, sect4=None, internal=None, mixedclass_=None, content_=None):
        self.id = id
        if mixedclass_ is None:
            self.mixedclass_ = MixedContainer
        else:
            self.mixedclass_ = mixedclass_
        if content_ is None:
            self.content_ = []
        else:
            self.content_ = content_
    def factory(*args_, **kwargs_):
        if docSect3Type.subclass:
            return docSect3Type.subclass(*args_, **kwargs_)
        else:
            return docSect3Type(*args_, **kwargs_)
    factory = staticmethod(factory)
    def get_title(self): return self.title
    def set_title(self, title): self.title = title
    def get_para(self): return self.para
    def set_para(self, para): self.para = para
    def add_para(self, value): self.para.append(value)
    def insert_para(self, index, value): self.para[index] = value
    def get_sect4(self): return self.sect4
    def set_sect4(self, sect4): self.sect4 = sect4
    def add_sect4(self, value): self.sect4.append(value)
    def insert_sect4(self, index, value): self.sect4[index] = value
    def get_internal(self): return self.internal
    def set_internal(self, internal): self.internal = internal
    def get_id(self): return self.id
    def set_id(self, id): self.id = id
    def export(self, outfile, level, namespace_='', name_='docSect3Type', namespacedef_=''):
        showIndent(outfile, level)
        outfile.write('<%s%s %s' % (namespace_, name_, namespacedef_, ))
        self.exportAttributes(outfile, level, namespace_, name_='docSect3Type')
        outfile.write('>')
        self.exportChildren(outfile, level + 1, namespace_, name_)
        outfile.write('</%s%s>\n' % (namespace_, name_))
    def exportAttributes(self, outfile, level, namespace_='', name_='docSect3Type'):
        if self.id is not None:
            outfile.write(' id=%s' % (self.format_string(quote_attrib(self.id).encode(ExternalEncoding), input_name='id'), ))
    def exportChildren(self, outfile, level, namespace_='', name_='docSect3Type'):
        for item_ in self.content_:
            item_.export(outfile, level, item_.name, namespace_)
    def hasContent_(self):
        if (
            self.title is not None or
            self.para is not None or
            self.sect4 is not None or
            self.internal is not None
            ):
            return True
        else:
            return False
    def exportLiteral(self, outfile, level, name_='docSect3Type'):
        level += 1
        self.exportLiteralAttributes(outfile, level, name_)
        if self.hasContent_():
            self.exportLiteralChildren(outfile, level, name_)
    def exportLiteralAttributes(self, outfile, level, name_):
        if self.id is not None:
            showIndent(outfile, level)
            outfile.write('id = %s,\n' % (self.id,))
    def exportLiteralChildren(self, outfile, level, name_):
        showIndent(outfile, level)
        outfile.write('content_ = [\n')
        for item_ in self.content_:
            item_.exportLiteral(outfile, level, name_)
        showIndent(outfile, level)
        outfile.write('],\n')
        showIndent(outfile, level)
        outfile.write('content_ = [\n')
        for item_ in self.content_:
            item_.exportLiteral(outfile, level, name_)
        showIndent(outfile, level)
        outfile.write('],\n')
        showIndent(outfile, level)
        outfile.write('content_ = [\n')
        for item_ in self.content_:
            item_.exportLiteral(outfile, level, name_)
        showIndent(outfile, level)
        outfile.write('],\n')
        showIndent(outfile, level)
        outfile.write('content_ = [\n')
        for item_ in self.content_:
            item_.exportLiteral(outfile, level, name_)
        showIndent(outfile, level)
        outfile.write('],\n')
    def build(self, node_):
        attrs = node_.attributes
        self.buildAttributes(attrs)
        for child_ in node_.childNodes:
            nodeName_ = child_.nodeName.split(':')[-1]
            self.buildChildren(child_, nodeName_)
    def buildAttributes(self, attrs):
        if attrs.get('id'):
            self.id = attrs.get('id').value
    def buildChildren(self, child_, nodeName_):
        if child_.nodeType == Node.ELEMENT_NODE and \
            nodeName_ == 'title':
            childobj_ = docTitleType.factory()
            childobj_.build(child_)
            obj_ = self.mixedclass_(MixedContainer.CategoryComplex,
                MixedContainer.TypeNone, 'title', childobj_)
            self.content_.append(obj_)
        elif child_.nodeType == Node.ELEMENT_NODE and \
            nodeName_ == 'para':
            childobj_ = docParaType.factory()
            childobj_.build(child_)
            obj_ = self.mixedclass_(MixedContainer.CategoryComplex,
                MixedContainer.TypeNone, 'para', childobj_)
            self.content_.append(obj_)
        elif child_.nodeType == Node.ELEMENT_NODE and \
            nodeName_ == 'sect4':
            childobj_ = docSect4Type.factory()
            childobj_.build(child_)
            obj_ = self.mixedclass_(MixedContainer.CategoryComplex,
                MixedContainer.TypeNone, 'sect4', childobj_)
            self.content_.append(obj_)
        elif child_.nodeType == Node.ELEMENT_NODE and \
            nodeName_ == 'internal':
            childobj_ = docInternalS3Type.factory()
            childobj_.build(child_)
            obj_ = self.mixedclass_(MixedContainer.CategoryComplex,
                MixedContainer.TypeNone, 'internal', childobj_)
            self.content_.append(obj_)
        elif child_.nodeType == Node.TEXT_NODE:
            obj_ = self.mixedclass_(MixedContainer.CategoryText,
                MixedContainer.TypeNone, '', child_.nodeValue)
            self.content_.append(obj_)
# end class docSect3Type


class docSect4Type(GeneratedsSuper):
    subclass = None
    superclass = None
    def __init__(self, id=None, title=None, para=None, internal=None, mixedclass_=None, content_=None):
        self.id = id
        if mixedclass_ is None:
            self.mixedclass_ = MixedContainer
        else:
            self.mixedclass_ = mixedclass_
        if content_ is None:
            self.content_ = []
        else:
            self.content_ = content_
    def factory(*args_, **kwargs_):
        if docSect4Type.subclass:
            return docSect4Type.subclass(*args_, **kwargs_)
        else:
            return docSect4Type(*args_, **kwargs_)
    factory = staticmethod(factory)
    def get_title(self): return self.title
    def set_title(self, title): self.title = title
    def get_para(self): return self.para
    def set_para(self, para): self.para = para
    def add_para(self, value): self.para.append(value)
    def insert_para(self, index, value): self.para[index] = value
    def get_internal(self): return self.internal
    def set_internal(self, internal): self.internal = internal
    def get_id(self): return self.id
    def set_id(self, id): self.id = id
    def export(self, outfile, level, namespace_='', name_='docSect4Type', namespacedef_=''):
        showIndent(outfile, level)
        outfile.write('<%s%s %s' % (namespace_, name_, namespacedef_, ))
        self.exportAttributes(outfile, level, namespace_, name_='docSect4Type')
        outfile.write('>')
        self.exportChildren(outfile, level + 1, namespace_, name_)
        outfile.write('</%s%s>\n' % (namespace_, name_))
    def exportAttributes(self, outfile, level, namespace_='', name_='docSect4Type'):
        if self.id is not None:
            outfile.write(' id=%s' % (self.format_string(quote_attrib(self.id).encode(ExternalEncoding), input_name='id'), ))
    def exportChildren(self, outfile, level, namespace_='', name_='docSect4Type'):
        for item_ in self.content_:
            item_.export(outfile, level, item_.name, namespace_)
    def hasContent_(self):
        if (
            self.title is not None or
            self.para is not None or
            self.internal is not None
            ):
            return True
        else:
            return False
    def exportLiteral(self, outfile, level, name_='docSect4Type'):
        level += 1
        self.exportLiteralAttributes(outfile, level, name_)
        if self.hasContent_():
            self.exportLiteralChildren(outfile, level, name_)
    def exportLiteralAttributes(self, outfile, level, name_):
        if self.id is not None:
            showIndent(outfile, level)
            outfile.write('id = %s,\n' % (self.id,))
    def exportLiteralChildren(self, outfile, level, name_):
        showIndent(outfile, level)
        outfile.write('content_ = [\n')
        for item_ in self.content_:
            item_.exportLiteral(outfile, level, name_)
        showIndent(outfile, level)
        outfile.write('],\n')
        showIndent(outfile, level)
        outfile.write('content_ = [\n')
        for item_ in self.content_:
            item_.exportLiteral(outfile, level, name_)
        showIndent(outfile, level)
        outfile.write('],\n')
        showIndent(outfile, level)
        outfile.write('content_ = [\n')
        for item_ in self.content_:
            item_.exportLiteral(outfile, level, name_)
        showIndent(outfile, level)
        outfile.write('],\n')
    def build(self, node_):
        attrs = node_.attributes
        self.buildAttributes(attrs)
        for child_ in node_.childNodes:
            nodeName_ = child_.nodeName.split(':')[-1]
            self.buildChildren(child_, nodeName_)
    def buildAttributes(self, attrs):
        if attrs.get('id'):
            self.id = attrs.get('id').value
    def buildChildren(self, child_, nodeName_):
        if child_.nodeType == Node.ELEMENT_NODE and \
            nodeName_ == 'title':
            childobj_ = docTitleType.factory()
            childobj_.build(child_)
            obj_ = self.mixedclass_(MixedContainer.CategoryComplex,
                MixedContainer.TypeNone, 'title', childobj_)
            self.content_.append(obj_)
        elif child_.nodeType == Node.ELEMENT_NODE and \
            nodeName_ == 'para':
            childobj_ = docParaType.factory()
            childobj_.build(child_)
            obj_ = self.mixedclass_(MixedContainer.CategoryComplex,
                MixedContainer.TypeNone, 'para', childobj_)
            self.content_.append(obj_)
        elif child_.nodeType == Node.ELEMENT_NODE and \
            nodeName_ == 'internal':
            childobj_ = docInternalS4Type.factory()
            childobj_.build(child_)
            obj_ = self.mixedclass_(MixedContainer.CategoryComplex,
                MixedContainer.TypeNone, 'internal', childobj_)
            self.content_.append(obj_)
        elif child_.nodeType == Node.TEXT_NODE:
            obj_ = self.mixedclass_(MixedContainer.CategoryText,
                MixedContainer.TypeNone, '', child_.nodeValue)
            self.content_.append(obj_)
# end class docSect4Type


class docInternalType(GeneratedsSuper):
    subclass = None
    superclass = None
    def __init__(self, para=None, sect1=None, mixedclass_=None, content_=None):
        if mixedclass_ is None:
            self.mixedclass_ = MixedContainer
        else:
            self.mixedclass_ = mixedclass_
        if content_ is None:
            self.content_ = []
        else:
            self.content_ = content_
    def factory(*args_, **kwargs_):
        if docInternalType.subclass:
            return docInternalType.subclass(*args_, **kwargs_)
        else:
            return docInternalType(*args_, **kwargs_)
    factory = staticmethod(factory)
    def get_para(self): return self.para
    def set_para(self, para): self.para = para
    def add_para(self, value): self.para.append(value)
    def insert_para(self, index, value): self.para[index] = value
    def get_sect1(self): return self.sect1
    def set_sect1(self, sect1): self.sect1 = sect1
    def add_sect1(self, value): self.sect1.append(value)
    def insert_sect1(self, index, value): self.sect1[index] = value
    def export(self, outfile, level, namespace_='', name_='docInternalType', namespacedef_=''):
        showIndent(outfile, level)
        outfile.write('<%s%s %s' % (namespace_, name_, namespacedef_, ))
        self.exportAttributes(outfile, level, namespace_, name_='docInternalType')
        outfile.write('>')
        self.exportChildren(outfile, level + 1, namespace_, name_)
        outfile.write('</%s%s>\n' % (namespace_, name_))
    def exportAttributes(self, outfile, level, namespace_='', name_='docInternalType'):
        pass
    def exportChildren(self, outfile, level, namespace_='', name_='docInternalType'):
        for item_ in self.content_:
            item_.export(outfile, level, item_.name, namespace_)
    def hasContent_(self):
        if (
            self.para is not None or
            self.sect1 is not None
            ):
            return True
        else:
            return False
    def exportLiteral(self, outfile, level, name_='docInternalType'):
        level += 1
        self.exportLiteralAttributes(outfile, level, name_)
        if self.hasContent_():
            self.exportLiteralChildren(outfile, level, name_)
    def exportLiteralAttributes(self, outfile, level, name_):
        pass
    def exportLiteralChildren(self, outfile, level, name_):
        showIndent(outfile, level)
        outfile.write('content_ = [\n')
        for item_ in self.content_:
            item_.exportLiteral(outfile, level, name_)
        showIndent(outfile, level)
        outfile.write('],\n')
        showIndent(outfile, level)
        outfile.write('content_ = [\n')
        for item_ in self.content_:
            item_.exportLiteral(outfile, level, name_)
        showIndent(outfile, level)
        outfile.write('],\n')
    def build(self, node_):
        attrs = node_.attributes
        self.buildAttributes(attrs)
        for child_ in node_.childNodes:
            nodeName_ = child_.nodeName.split(':')[-1]
            self.buildChildren(child_, nodeName_)
    def buildAttributes(self, attrs):
        pass
    def buildChildren(self, child_, nodeName_):
        if child_.nodeType == Node.ELEMENT_NODE and \
            nodeName_ == 'para':
            childobj_ = docParaType.factory()
            childobj_.build(child_)
            obj_ = self.mixedclass_(MixedContainer.CategoryComplex,
                MixedContainer.TypeNone, 'para', childobj_)
            self.content_.append(obj_)
        elif child_.nodeType == Node.ELEMENT_NODE and \
            nodeName_ == 'sect1':
            childobj_ = docSect1Type.factory()
            childobj_.build(child_)
            obj_ = self.mixedclass_(MixedContainer.CategoryComplex,
                MixedContainer.TypeNone, 'sect1', childobj_)
            self.content_.append(obj_)
        elif child_.nodeType == Node.TEXT_NODE:
            obj_ = self.mixedclass_(MixedContainer.CategoryText,
                MixedContainer.TypeNone, '', child_.nodeValue)
            self.content_.append(obj_)
# end class docInternalType


class docInternalS1Type(GeneratedsSuper):
    subclass = None
    superclass = None
    def __init__(self, para=None, sect2=None, mixedclass_=None, content_=None):
        if mixedclass_ is None:
            self.mixedclass_ = MixedContainer
        else:
            self.mixedclass_ = mixedclass_
        if content_ is None:
            self.content_ = []
        else:
            self.content_ = content_
    def factory(*args_, **kwargs_):
        if docInternalS1Type.subclass:
            return docInternalS1Type.subclass(*args_, **kwargs_)
        else:
            return docInternalS1Type(*args_, **kwargs_)
    factory = staticmethod(factory)
    def get_para(self): return self.para
    def set_para(self, para): self.para = para
    def add_para(self, value): self.para.append(value)
    def insert_para(self, index, value): self.para[index] = value
    def get_sect2(self): return self.sect2
    def set_sect2(self, sect2): self.sect2 = sect2
    def add_sect2(self, value): self.sect2.append(value)
    def insert_sect2(self, index, value): self.sect2[index] = value
    def export(self, outfile, level, namespace_='', name_='docInternalS1Type', namespacedef_=''):
        showIndent(outfile, level)
        outfile.write('<%s%s %s' % (namespace_, name_, namespacedef_, ))
        self.exportAttributes(outfile, level, namespace_, name_='docInternalS1Type')
        outfile.write('>')
        self.exportChildren(outfile, level + 1, namespace_, name_)
        outfile.write('</%s%s>\n' % (namespace_, name_))
    def exportAttributes(self, outfile, level, namespace_='', name_='docInternalS1Type'):
        pass
    def exportChildren(self, outfile, level, namespace_='', name_='docInternalS1Type'):
        for item_ in self.content_:
            item_.export(outfile, level, item_.name, namespace_)
    def hasContent_(self):
        if (
            self.para is not None or
            self.sect2 is not None
            ):
            return True
        else:
            return False
    def exportLiteral(self, outfile, level, name_='docInternalS1Type'):
        level += 1
        self.exportLiteralAttributes(outfile, level, name_)
        if self.hasContent_():
            self.exportLiteralChildren(outfile, level, name_)
    def exportLiteralAttributes(self, outfile, level, name_):
        pass
    def exportLiteralChildren(self, outfile, level, name_):
        showIndent(outfile, level)
        outfile.write('content_ = [\n')
        for item_ in self.content_:
            item_.exportLiteral(outfile, level, name_)
        showIndent(outfile, level)
        outfile.write('],\n')
        showIndent(outfile, level)
        outfile.write('content_ = [\n')
        for item_ in self.content_:
            item_.exportLiteral(outfile, level, name_)
        showIndent(outfile, level)
        outfile.write('],\n')
    def build(self, node_):
        attrs = node_.attributes
        self.buildAttributes(attrs)
        for child_ in node_.childNodes:
            nodeName_ = child_.nodeName.split(':')[-1]
            self.buildChildren(child_, nodeName_)
    def buildAttributes(self, attrs):
        pass
    def buildChildren(self, child_, nodeName_):
        if child_.nodeType == Node.ELEMENT_NODE and \
            nodeName_ == 'para':
            childobj_ = docParaType.factory()
            childobj_.build(child_)
            obj_ = self.mixedclass_(MixedContainer.CategoryComplex,
                MixedContainer.TypeNone, 'para', childobj_)
            self.content_.append(obj_)
        elif child_.nodeType == Node.ELEMENT_NODE and \
            nodeName_ == 'sect2':
            childobj_ = docSect2Type.factory()
            childobj_.build(child_)
            obj_ = self.mixedclass_(MixedContainer.CategoryComplex,
                MixedContainer.TypeNone, 'sect2', childobj_)
            self.content_.append(obj_)
        elif child_.nodeType == Node.TEXT_NODE:
            obj_ = self.mixedclass_(MixedContainer.CategoryText,
                MixedContainer.TypeNone, '', child_.nodeValue)
            self.content_.append(obj_)
# end class docInternalS1Type


class docInternalS2Type(GeneratedsSuper):
    subclass = None
    superclass = None
    def __init__(self, para=None, sect3=None, mixedclass_=None, content_=None):
        if mixedclass_ is None:
            self.mixedclass_ = MixedContainer
        else:
            self.mixedclass_ = mixedclass_
        if content_ is None:
            self.content_ = []
        else:
            self.content_ = content_
    def factory(*args_, **kwargs_):
        if docInternalS2Type.subclass:
            return docInternalS2Type.subclass(*args_, **kwargs_)
        else:
            return docInternalS2Type(*args_, **kwargs_)
    factory = staticmethod(factory)
    def get_para(self): return self.para
    def set_para(self, para): self.para = para
    def add_para(self, value): self.para.append(value)
    def insert_para(self, index, value): self.para[index] = value
    def get_sect3(self): return self.sect3
    def set_sect3(self, sect3): self.sect3 = sect3
    def add_sect3(self, value): self.sect3.append(value)
    def insert_sect3(self, index, value): self.sect3[index] = value
    def export(self, outfile, level, namespace_='', name_='docInternalS2Type', namespacedef_=''):
        showIndent(outfile, level)
        outfile.write('<%s%s %s' % (namespace_, name_, namespacedef_, ))
        self.exportAttributes(outfile, level, namespace_, name_='docInternalS2Type')
        outfile.write('>')
        self.exportChildren(outfile, level + 1, namespace_, name_)
        outfile.write('</%s%s>\n' % (namespace_, name_))
    def exportAttributes(self, outfile, level, namespace_='', name_='docInternalS2Type'):
        pass
    def exportChildren(self, outfile, level, namespace_='', name_='docInternalS2Type'):
        for item_ in self.content_:
            item_.export(outfile, level, item_.name, namespace_)
    def hasContent_(self):
        if (
            self.para is not None or
            self.sect3 is not None
            ):
            return True
        else:
            return False
    def exportLiteral(self, outfile, level, name_='docInternalS2Type'):
        level += 1
        self.exportLiteralAttributes(outfile, level, name_)
        if self.hasContent_():
            self.exportLiteralChildren(outfile, level, name_)
    def exportLiteralAttributes(self, outfile, level, name_):
        pass
    def exportLiteralChildren(self, outfile, level, name_):
        showIndent(outfile, level)
        outfile.write('content_ = [\n')
        for item_ in self.content_:
            item_.exportLiteral(outfile, level, name_)
        showIndent(outfile, level)
        outfile.write('],\n')
        showIndent(outfile, level)
        outfile.write('content_ = [\n')
        for item_ in self.content_:
            item_.exportLiteral(outfile, level, name_)
        showIndent(outfile, level)
        outfile.write('],\n')
    def build(self, node_):
        attrs = node_.attributes
        self.buildAttributes(attrs)
        for child_ in node_.childNodes:
            nodeName_ = child_.nodeName.split(':')[-1]
            self.buildChildren(child_, nodeName_)
    def buildAttributes(self, attrs):
        pass
    def buildChildren(self, child_, nodeName_):
        if child_.nodeType == Node.ELEMENT_NODE and \
            nodeName_ == 'para':
            childobj_ = docParaType.factory()
            childobj_.build(child_)
            obj_ = self.mixedclass_(MixedContainer.CategoryComplex,
                MixedContainer.TypeNone, 'para', childobj_)
            self.content_.append(obj_)
        elif child_.nodeType == Node.ELEMENT_NODE and \
            nodeName_ == 'sect3':
            childobj_ = docSect3Type.factory()
            childobj_.build(child_)
            obj_ = self.mixedclass_(MixedContainer.CategoryComplex,
                MixedContainer.TypeNone, 'sect3', childobj_)
            self.content_.append(obj_)
        elif child_.nodeType == Node.TEXT_NODE:
            obj_ = self.mixedclass_(MixedContainer.CategoryText,
                MixedContainer.TypeNone, '', child_.nodeValue)
            self.content_.append(obj_)
# end class docInternalS2Type


class docInternalS3Type(GeneratedsSuper):
    subclass = None
    superclass = None
    def __init__(self, para=None, sect3=None, mixedclass_=None, content_=None):
        if mixedclass_ is None:
            self.mixedclass_ = MixedContainer
        else:
            self.mixedclass_ = mixedclass_
        if content_ is None:
            self.content_ = []
        else:
            self.content_ = content_
    def factory(*args_, **kwargs_):
        if docInternalS3Type.subclass:
            return docInternalS3Type.subclass(*args_, **kwargs_)
        else:
            return docInternalS3Type(*args_, **kwargs_)
    factory = staticmethod(factory)
    def get_para(self): return self.para
    def set_para(self, para): self.para = para
    def add_para(self, value): self.para.append(value)
    def insert_para(self, index, value): self.para[index] = value
    def get_sect3(self): return self.sect3
    def set_sect3(self, sect3): self.sect3 = sect3
    def add_sect3(self, value): self.sect3.append(value)
    def insert_sect3(self, index, value): self.sect3[index] = value
    def export(self, outfile, level, namespace_='', name_='docInternalS3Type', namespacedef_=''):
        showIndent(outfile, level)
        outfile.write('<%s%s %s' % (namespace_, name_, namespacedef_, ))
        self.exportAttributes(outfile, level, namespace_, name_='docInternalS3Type')
        outfile.write('>')
        self.exportChildren(outfile, level + 1, namespace_, name_)
        outfile.write('</%s%s>\n' % (namespace_, name_))
    def exportAttributes(self, outfile, level, namespace_='', name_='docInternalS3Type'):
        pass
    def exportChildren(self, outfile, level, namespace_='', name_='docInternalS3Type'):
        for item_ in self.content_:
            item_.export(outfile, level, item_.name, namespace_)
    def hasContent_(self):
        if (
            self.para is not None or
            self.sect3 is not None
            ):
            return True
        else:
            return False
    def exportLiteral(self, outfile, level, name_='docInternalS3Type'):
        level += 1
        self.exportLiteralAttributes(outfile, level, name_)
        if self.hasContent_():
            self.exportLiteralChildren(outfile, level, name_)
    def exportLiteralAttributes(self, outfile, level, name_):
        pass
    def exportLiteralChildren(self, outfile, level, name_):
        showIndent(outfile, level)
        outfile.write('content_ = [\n')
        for item_ in self.content_:
            item_.exportLiteral(outfile, level, name_)
        showIndent(outfile, level)
        outfile.write('],\n')
        showIndent(outfile, level)
        outfile.write('content_ = [\n')
        for item_ in self.content_:
            item_.exportLiteral(outfile, level, name_)
        showIndent(outfile, level)
        outfile.write('],\n')
    def build(self, node_):
        attrs = node_.attributes
        self.buildAttributes(attrs)
        for child_ in node_.childNodes:
            nodeName_ = child_.nodeName.split(':')[-1]
            self.buildChildren(child_, nodeName_)
    def buildAttributes(self, attrs):
        pass
    def buildChildren(self, child_, nodeName_):
        if child_.nodeType == Node.ELEMENT_NODE and \
            nodeName_ == 'para':
            childobj_ = docParaType.factory()
            childobj_.build(child_)
            obj_ = self.mixedclass_(MixedContainer.CategoryComplex,
                MixedContainer.TypeNone, 'para', childobj_)
            self.content_.append(obj_)
        elif child_.nodeType == Node.ELEMENT_NODE and \
            nodeName_ == 'sect3':
            childobj_ = docSect4Type.factory()
            childobj_.build(child_)
            obj_ = self.mixedclass_(MixedContainer.CategoryComplex,
                MixedContainer.TypeNone, 'sect3', childobj_)
            self.content_.append(obj_)
        elif child_.nodeType == Node.TEXT_NODE:
            obj_ = self.mixedclass_(MixedContainer.CategoryText,
                MixedContainer.TypeNone, '', child_.nodeValue)
            self.content_.append(obj_)
# end class docInternalS3Type


class docInternalS4Type(GeneratedsSuper):
    subclass = None
    superclass = None
    def __init__(self, para=None, mixedclass_=None, content_=None):
        if mixedclass_ is None:
            self.mixedclass_ = MixedContainer
        else:
            self.mixedclass_ = mixedclass_
        if content_ is None:
            self.content_ = []
        else:
            self.content_ = content_
    def factory(*args_, **kwargs_):
        if docInternalS4Type.subclass:
            return docInternalS4Type.subclass(*args_, **kwargs_)
        else:
            return docInternalS4Type(*args_, **kwargs_)
    factory = staticmethod(factory)
    def get_para(self): return self.para
    def set_para(self, para): self.para = para
    def add_para(self, value): self.para.append(value)
    def insert_para(self, index, value): self.para[index] = value
    def export(self, outfile, level, namespace_='', name_='docInternalS4Type', namespacedef_=''):
        showIndent(outfile, level)
        outfile.write('<%s%s %s' % (namespace_, name_, namespacedef_, ))
        self.exportAttributes(outfile, level, namespace_, name_='docInternalS4Type')
        outfile.write('>')
        self.exportChildren(outfile, level + 1, namespace_, name_)
        outfile.write('</%s%s>\n' % (namespace_, name_))
    def exportAttributes(self, outfile, level, namespace_='', name_='docInternalS4Type'):
        pass
    def exportChildren(self, outfile, level, namespace_='', name_='docInternalS4Type'):
        for item_ in self.content_:
            item_.export(outfile, level, item_.name, namespace_)
    def hasContent_(self):
        if (
            self.para is not None
            ):
            return True
        else:
            return False
    def exportLiteral(self, outfile, level, name_='docInternalS4Type'):
        level += 1
        self.exportLiteralAttributes(outfile, level, name_)
        if self.hasContent_():
            self.exportLiteralChildren(outfile, level, name_)
    def exportLiteralAttributes(self, outfile, level, name_):
        pass
    def exportLiteralChildren(self, outfile, level, name_):
        showIndent(outfile, level)
        outfile.write('content_ = [\n')
        for item_ in self.content_:
            item_.exportLiteral(outfile, level, name_)
        showIndent(outfile, level)
        outfile.write('],\n')
    def build(self, node_):
        attrs = node_.attributes
        self.buildAttributes(attrs)
        for child_ in node_.childNodes:
            nodeName_ = child_.nodeName.split(':')[-1]
            self.buildChildren(child_, nodeName_)
    def buildAttributes(self, attrs):
        pass
    def buildChildren(self, child_, nodeName_):
        if child_.nodeType == Node.ELEMENT_NODE and \
            nodeName_ == 'para':
            childobj_ = docParaType.factory()
            childobj_.build(child_)
            obj_ = self.mixedclass_(MixedContainer.CategoryComplex,
                MixedContainer.TypeNone, 'para', childobj_)
            self.content_.append(obj_)
        elif child_.nodeType == Node.TEXT_NODE:
            obj_ = self.mixedclass_(MixedContainer.CategoryText,
                MixedContainer.TypeNone, '', child_.nodeValue)
            self.content_.append(obj_)
# end class docInternalS4Type


class docTitleType(GeneratedsSuper):
    subclass = None
    superclass = None
    def __init__(self, valueOf_='', mixedclass_=None, content_=None):
        if mixedclass_ is None:
            self.mixedclass_ = MixedContainer
        else:
            self.mixedclass_ = mixedclass_
        if content_ is None:
            self.content_ = []
        else:
            self.content_ = content_
    def factory(*args_, **kwargs_):
        if docTitleType.subclass:
            return docTitleType.subclass(*args_, **kwargs_)
        else:
            return docTitleType(*args_, **kwargs_)
    factory = staticmethod(factory)
    def getValueOf_(self): return self.valueOf_
    def setValueOf_(self, valueOf_): self.valueOf_ = valueOf_
    def export(self, outfile, level, namespace_='', name_='docTitleType', namespacedef_=''):
        showIndent(outfile, level)
        outfile.write('<%s%s %s' % (namespace_, name_, namespacedef_, ))
        self.exportAttributes(outfile, level, namespace_, name_='docTitleType')
        outfile.write('>')
        self.exportChildren(outfile, level + 1, namespace_, name_)
        outfile.write('</%s%s>\n' % (namespace_, name_))
    def exportAttributes(self, outfile, level, namespace_='', name_='docTitleType'):
        pass
    def exportChildren(self, outfile, level, namespace_='', name_='docTitleType'):
        if self.valueOf_.find('![CDATA')>-1:
            value=quote_xml('%s' % self.valueOf_)
            value=value.replace('![CDATA','<![CDATA')
            value=value.replace(']]',']]>')
            outfile.write(value)
        else:
            outfile.write(quote_xml('%s' % self.valueOf_))
    def hasContent_(self):
        if (
            self.valueOf_ is not None
            ):
            return True
        else:
            return False
    def exportLiteral(self, outfile, level, name_='docTitleType'):
        level += 1
        self.exportLiteralAttributes(outfile, level, name_)
        if self.hasContent_():
            self.exportLiteralChildren(outfile, level, name_)
    def exportLiteralAttributes(self, outfile, level, name_):
        pass
    def exportLiteralChildren(self, outfile, level, name_):
        showIndent(outfile, level)
        outfile.write('valueOf_ = "%s",\n' % (self.valueOf_,))
    def build(self, node_):
        attrs = node_.attributes
        self.buildAttributes(attrs)
        self.valueOf_ = ''
        for child_ in node_.childNodes:
            nodeName_ = child_.nodeName.split(':')[-1]
            self.buildChildren(child_, nodeName_)
    def buildAttributes(self, attrs):
        pass
    def buildChildren(self, child_, nodeName_):
        if child_.nodeType == Node.TEXT_NODE:
            obj_ = self.mixedclass_(MixedContainer.CategoryText,
                MixedContainer.TypeNone, '', child_.nodeValue)
            self.content_.append(obj_)
        if child_.nodeType == Node.TEXT_NODE:
            self.valueOf_ += child_.nodeValue
        elif child_.nodeType == Node.CDATA_SECTION_NODE:
            self.valueOf_ += '![CDATA['+child_.nodeValue+']]'
# end class docTitleType


class docParaType(GeneratedsSuper):
    subclass = None
    superclass = None
    def __init__(self, valueOf_='', mixedclass_=None, content_=None):
        if mixedclass_ is None:
            self.mixedclass_ = MixedContainer
        else:
            self.mixedclass_ = mixedclass_
        if content_ is None:
            self.content_ = []
        else:
            self.content_ = content_
    def factory(*args_, **kwargs_):
        if docParaType.subclass:
            return docParaType.subclass(*args_, **kwargs_)
        else:
            return docParaType(*args_, **kwargs_)
    factory = staticmethod(factory)
    def getValueOf_(self): return self.valueOf_
    def setValueOf_(self, valueOf_): self.valueOf_ = valueOf_
    def export(self, outfile, level, namespace_='', name_='docParaType', namespacedef_=''):
        showIndent(outfile, level)
        outfile.write('<%s%s %s' % (namespace_, name_, namespacedef_, ))
        self.exportAttributes(outfile, level, namespace_, name_='docParaType')
        outfile.write('>')
        self.exportChildren(outfile, level + 1, namespace_, name_)
        outfile.write('</%s%s>\n' % (namespace_, name_))
    def exportAttributes(self, outfile, level, namespace_='', name_='docParaType'):
        pass
    def exportChildren(self, outfile, level, namespace_='', name_='docParaType'):
        if self.valueOf_.find('![CDATA')>-1:
            value=quote_xml('%s' % self.valueOf_)
            value=value.replace('![CDATA','<![CDATA')
            value=value.replace(']]',']]>')
            outfile.write(value)
        else:
            outfile.write(quote_xml('%s' % self.valueOf_))
    def hasContent_(self):
        if (
            self.valueOf_ is not None
            ):
            return True
        else:
            return False
    def exportLiteral(self, outfile, level, name_='docParaType'):
        level += 1
        self.exportLiteralAttributes(outfile, level, name_)
        if self.hasContent_():
            self.exportLiteralChildren(outfile, level, name_)
    def exportLiteralAttributes(self, outfile, level, name_):
        pass
    def exportLiteralChildren(self, outfile, level, name_):
        showIndent(outfile, level)
        outfile.write('valueOf_ = "%s",\n' % (self.valueOf_,))
    def build(self, node_):
        attrs = node_.attributes
        self.buildAttributes(attrs)
        self.valueOf_ = ''
        for child_ in node_.childNodes:
            nodeName_ = child_.nodeName.split(':')[-1]
            self.buildChildren(child_, nodeName_)
    def buildAttributes(self, attrs):
        pass
    def buildChildren(self, child_, nodeName_):
        if child_.nodeType == Node.TEXT_NODE:
            obj_ = self.mixedclass_(MixedContainer.CategoryText,
                MixedContainer.TypeNone, '', child_.nodeValue)
            self.content_.append(obj_)
        if child_.nodeType == Node.TEXT_NODE:
            self.valueOf_ += child_.nodeValue
        elif child_.nodeType == Node.CDATA_SECTION_NODE:
            self.valueOf_ += '![CDATA['+child_.nodeValue+']]'
# end class docParaType


class docMarkupType(GeneratedsSuper):
    subclass = None
    superclass = None
    def __init__(self, valueOf_='', mixedclass_=None, content_=None):
        if mixedclass_ is None:
            self.mixedclass_ = MixedContainer
        else:
            self.mixedclass_ = mixedclass_
        if content_ is None:
            self.content_ = []
        else:
            self.content_ = content_
    def factory(*args_, **kwargs_):
        if docMarkupType.subclass:
            return docMarkupType.subclass(*args_, **kwargs_)
        else:
            return docMarkupType(*args_, **kwargs_)
    factory = staticmethod(factory)
    def getValueOf_(self): return self.valueOf_
    def setValueOf_(self, valueOf_): self.valueOf_ = valueOf_
    def export(self, outfile, level, namespace_='', name_='docMarkupType', namespacedef_=''):
        showIndent(outfile, level)
        outfile.write('<%s%s %s' % (namespace_, name_, namespacedef_, ))
        self.exportAttributes(outfile, level, namespace_, name_='docMarkupType')
        outfile.write('>')
        self.exportChildren(outfile, level + 1, namespace_, name_)
        outfile.write('</%s%s>\n' % (namespace_, name_))
    def exportAttributes(self, outfile, level, namespace_='', name_='docMarkupType'):
        pass
    def exportChildren(self, outfile, level, namespace_='', name_='docMarkupType'):
        if self.valueOf_.find('![CDATA')>-1:
            value=quote_xml('%s' % self.valueOf_)
            value=value.replace('![CDATA','<![CDATA')
            value=value.replace(']]',']]>')
            outfile.write(value)
        else:
            outfile.write(quote_xml('%s' % self.valueOf_))
    def hasContent_(self):
        if (
            self.valueOf_ is not None
            ):
            return True
        else:
            return False
    def exportLiteral(self, outfile, level, name_='docMarkupType'):
        level += 1
        self.exportLiteralAttributes(outfile, level, name_)
        if self.hasContent_():
            self.exportLiteralChildren(outfile, level, name_)
    def exportLiteralAttributes(self, outfile, level, name_):
        pass
    def exportLiteralChildren(self, outfile, level, name_):
        showIndent(outfile, level)
        outfile.write('valueOf_ = "%s",\n' % (self.valueOf_,))
    def build(self, node_):
        attrs = node_.attributes
        self.buildAttributes(attrs)
        self.valueOf_ = ''
        for child_ in node_.childNodes:
            nodeName_ = child_.nodeName.split(':')[-1]
            self.buildChildren(child_, nodeName_)
    def buildAttributes(self, attrs):
        pass
    def buildChildren(self, child_, nodeName_):
        if child_.nodeType == Node.TEXT_NODE:
            obj_ = self.mixedclass_(MixedContainer.CategoryText,
                MixedContainer.TypeNone, '', child_.nodeValue)
            self.content_.append(obj_)
        if child_.nodeType == Node.TEXT_NODE:
            self.valueOf_ += child_.nodeValue
        elif child_.nodeType == Node.CDATA_SECTION_NODE:
            self.valueOf_ += '![CDATA['+child_.nodeValue+']]'
# end class docMarkupType


class docURLLink(GeneratedsSuper):
    subclass = None
    superclass = None
    def __init__(self, url=None, valueOf_='', mixedclass_=None, content_=None):
        self.url = url
        if mixedclass_ is None:
            self.mixedclass_ = MixedContainer
        else:
            self.mixedclass_ = mixedclass_
        if content_ is None:
            self.content_ = []
        else:
            self.content_ = content_
    def factory(*args_, **kwargs_):
        if docURLLink.subclass:
            return docURLLink.subclass(*args_, **kwargs_)
        else:
            return docURLLink(*args_, **kwargs_)
    factory = staticmethod(factory)
    def get_url(self): return self.url
    def set_url(self, url): self.url = url
    def getValueOf_(self): return self.valueOf_
    def setValueOf_(self, valueOf_): self.valueOf_ = valueOf_
    def export(self, outfile, level, namespace_='', name_='docURLLink', namespacedef_=''):
        showIndent(outfile, level)
        outfile.write('<%s%s %s' % (namespace_, name_, namespacedef_, ))
        self.exportAttributes(outfile, level, namespace_, name_='docURLLink')
        outfile.write('>')
        self.exportChildren(outfile, level + 1, namespace_, name_)
        outfile.write('</%s%s>\n' % (namespace_, name_))
    def exportAttributes(self, outfile, level, namespace_='', name_='docURLLink'):
        if self.url is not None:
            outfile.write(' url=%s' % (self.format_string(quote_attrib(self.url).encode(ExternalEncoding), input_name='url'), ))
    def exportChildren(self, outfile, level, namespace_='', name_='docURLLink'):
        if self.valueOf_.find('![CDATA')>-1:
            value=quote_xml('%s' % self.valueOf_)
            value=value.replace('![CDATA','<![CDATA')
            value=value.replace(']]',']]>')
            outfile.write(value)
        else:
            outfile.write(quote_xml('%s' % self.valueOf_))
    def hasContent_(self):
        if (
            self.valueOf_ is not None
            ):
            return True
        else:
            return False
    def exportLiteral(self, outfile, level, name_='docURLLink'):
        level += 1
        self.exportLiteralAttributes(outfile, level, name_)
        if self.hasContent_():
            self.exportLiteralChildren(outfile, level, name_)
    def exportLiteralAttributes(self, outfile, level, name_):
        if self.url is not None:
            showIndent(outfile, level)
            outfile.write('url = %s,\n' % (self.url,))
    def exportLiteralChildren(self, outfile, level, name_):
        showIndent(outfile, level)
        outfile.write('valueOf_ = "%s",\n' % (self.valueOf_,))
    def build(self, node_):
        attrs = node_.attributes
        self.buildAttributes(attrs)
        self.valueOf_ = ''
        for child_ in node_.childNodes:
            nodeName_ = child_.nodeName.split(':')[-1]
            self.buildChildren(child_, nodeName_)
    def buildAttributes(self, attrs):
        if attrs.get('url'):
            self.url = attrs.get('url').value
    def buildChildren(self, child_, nodeName_):
        if child_.nodeType == Node.TEXT_NODE:
            obj_ = self.mixedclass_(MixedContainer.CategoryText,
                MixedContainer.TypeNone, '', child_.nodeValue)
            self.content_.append(obj_)
        if child_.nodeType == Node.TEXT_NODE:
            self.valueOf_ += child_.nodeValue
        elif child_.nodeType == Node.CDATA_SECTION_NODE:
            self.valueOf_ += '![CDATA['+child_.nodeValue+']]'
# end class docURLLink


class docAnchorType(GeneratedsSuper):
    subclass = None
    superclass = None
    def __init__(self, id=None, valueOf_='', mixedclass_=None, content_=None):
        self.id = id
        if mixedclass_ is None:
            self.mixedclass_ = MixedContainer
        else:
            self.mixedclass_ = mixedclass_
        if content_ is None:
            self.content_ = []
        else:
            self.content_ = content_
    def factory(*args_, **kwargs_):
        if docAnchorType.subclass:
            return docAnchorType.subclass(*args_, **kwargs_)
        else:
            return docAnchorType(*args_, **kwargs_)
    factory = staticmethod(factory)
    def get_id(self): return self.id
    def set_id(self, id): self.id = id
    def getValueOf_(self): return self.valueOf_
    def setValueOf_(self, valueOf_): self.valueOf_ = valueOf_
    def export(self, outfile, level, namespace_='', name_='docAnchorType', namespacedef_=''):
        showIndent(outfile, level)
        outfile.write('<%s%s %s' % (namespace_, name_, namespacedef_, ))
        self.exportAttributes(outfile, level, namespace_, name_='docAnchorType')
        outfile.write('>')
        self.exportChildren(outfile, level + 1, namespace_, name_)
        outfile.write('</%s%s>\n' % (namespace_, name_))
    def exportAttributes(self, outfile, level, namespace_='', name_='docAnchorType'):
        if self.id is not None:
            outfile.write(' id=%s' % (self.format_string(quote_attrib(self.id).encode(ExternalEncoding), input_name='id'), ))
    def exportChildren(self, outfile, level, namespace_='', name_='docAnchorType'):
        if self.valueOf_.find('![CDATA')>-1:
            value=quote_xml('%s' % self.valueOf_)
            value=value.replace('![CDATA','<![CDATA')
            value=value.replace(']]',']]>')
            outfile.write(value)
        else:
            outfile.write(quote_xml('%s' % self.valueOf_))
    def hasContent_(self):
        if (
            self.valueOf_ is not None
            ):
            return True
        else:
            return False
    def exportLiteral(self, outfile, level, name_='docAnchorType'):
        level += 1
        self.exportLiteralAttributes(outfile, level, name_)
        if self.hasContent_():
            self.exportLiteralChildren(outfile, level, name_)
    def exportLiteralAttributes(self, outfile, level, name_):
        if self.id is not None:
            showIndent(outfile, level)
            outfile.write('id = %s,\n' % (self.id,))
    def exportLiteralChildren(self, outfile, level, name_):
        showIndent(outfile, level)
        outfile.write('valueOf_ = "%s",\n' % (self.valueOf_,))
    def build(self, node_):
        attrs = node_.attributes
        self.buildAttributes(attrs)
        self.valueOf_ = ''
        for child_ in node_.childNodes:
            nodeName_ = child_.nodeName.split(':')[-1]
            self.buildChildren(child_, nodeName_)
    def buildAttributes(self, attrs):
        if attrs.get('id'):
            self.id = attrs.get('id').value
    def buildChildren(self, child_, nodeName_):
        if child_.nodeType == Node.TEXT_NODE:
            obj_ = self.mixedclass_(MixedContainer.CategoryText,
                MixedContainer.TypeNone, '', child_.nodeValue)
            self.content_.append(obj_)
        if child_.nodeType == Node.TEXT_NODE:
            self.valueOf_ += child_.nodeValue
        elif child_.nodeType == Node.CDATA_SECTION_NODE:
            self.valueOf_ += '![CDATA['+child_.nodeValue+']]'
# end class docAnchorType


class docFormulaType(GeneratedsSuper):
    subclass = None
    superclass = None
    def __init__(self, id=None, valueOf_='', mixedclass_=None, content_=None):
        self.id = id
        if mixedclass_ is None:
            self.mixedclass_ = MixedContainer
        else:
            self.mixedclass_ = mixedclass_
        if content_ is None:
            self.content_ = []
        else:
            self.content_ = content_
    def factory(*args_, **kwargs_):
        if docFormulaType.subclass:
            return docFormulaType.subclass(*args_, **kwargs_)
        else:
            return docFormulaType(*args_, **kwargs_)
    factory = staticmethod(factory)
    def get_id(self): return self.id
    def set_id(self, id): self.id = id
    def getValueOf_(self): return self.valueOf_
    def setValueOf_(self, valueOf_): self.valueOf_ = valueOf_
    def export(self, outfile, level, namespace_='', name_='docFormulaType', namespacedef_=''):
        showIndent(outfile, level)
        outfile.write('<%s%s %s' % (namespace_, name_, namespacedef_, ))
        self.exportAttributes(outfile, level, namespace_, name_='docFormulaType')
        outfile.write('>')
        self.exportChildren(outfile, level + 1, namespace_, name_)
        outfile.write('</%s%s>\n' % (namespace_, name_))
    def exportAttributes(self, outfile, level, namespace_='', name_='docFormulaType'):
        if self.id is not None:
            outfile.write(' id=%s' % (self.format_string(quote_attrib(self.id).encode(ExternalEncoding), input_name='id'), ))
    def exportChildren(self, outfile, level, namespace_='', name_='docFormulaType'):
        if self.valueOf_.find('![CDATA')>-1:
            value=quote_xml('%s' % self.valueOf_)
            value=value.replace('![CDATA','<![CDATA')
            value=value.replace(']]',']]>')
            outfile.write(value)
        else:
            outfile.write(quote_xml('%s' % self.valueOf_))
    def hasContent_(self):
        if (
            self.valueOf_ is not None
            ):
            return True
        else:
            return False
    def exportLiteral(self, outfile, level, name_='docFormulaType'):
        level += 1
        self.exportLiteralAttributes(outfile, level, name_)
        if self.hasContent_():
            self.exportLiteralChildren(outfile, level, name_)
    def exportLiteralAttributes(self, outfile, level, name_):
        if self.id is not None:
            showIndent(outfile, level)
            outfile.write('id = %s,\n' % (self.id,))
    def exportLiteralChildren(self, outfile, level, name_):
        showIndent(outfile, level)
        outfile.write('valueOf_ = "%s",\n' % (self.valueOf_,))
    def build(self, node_):
        attrs = node_.attributes
        self.buildAttributes(attrs)
        self.valueOf_ = ''
        for child_ in node_.childNodes:
            nodeName_ = child_.nodeName.split(':')[-1]
            self.buildChildren(child_, nodeName_)
    def buildAttributes(self, attrs):
        if attrs.get('id'):
            self.id = attrs.get('id').value
    def buildChildren(self, child_, nodeName_):
        if child_.nodeType == Node.TEXT_NODE:
            obj_ = self.mixedclass_(MixedContainer.CategoryText,
                MixedContainer.TypeNone, '', child_.nodeValue)
            self.content_.append(obj_)
        if child_.nodeType == Node.TEXT_NODE:
            self.valueOf_ += child_.nodeValue
        elif child_.nodeType == Node.CDATA_SECTION_NODE:
            self.valueOf_ += '![CDATA['+child_.nodeValue+']]'
# end class docFormulaType


class docIndexEntryType(GeneratedsSuper):
    subclass = None
    superclass = None
    def __init__(self, primaryie=None, secondaryie=None):
        self.primaryie = primaryie
        self.secondaryie = secondaryie
    def factory(*args_, **kwargs_):
        if docIndexEntryType.subclass:
            return docIndexEntryType.subclass(*args_, **kwargs_)
        else:
            return docIndexEntryType(*args_, **kwargs_)
    factory = staticmethod(factory)
    def get_primaryie(self): return self.primaryie
    def set_primaryie(self, primaryie): self.primaryie = primaryie
    def get_secondaryie(self): return self.secondaryie
    def set_secondaryie(self, secondaryie): self.secondaryie = secondaryie
    def export(self, outfile, level, namespace_='', name_='docIndexEntryType', namespacedef_=''):
        showIndent(outfile, level)
        outfile.write('<%s%s %s' % (namespace_, name_, namespacedef_, ))
        self.exportAttributes(outfile, level, namespace_, name_='docIndexEntryType')
        if self.hasContent_():
            outfile.write('>\n')
            self.exportChildren(outfile, level + 1, namespace_, name_)
            showIndent(outfile, level)
            outfile.write('</%s%s>\n' % (namespace_, name_))
        else:
            outfile.write(' />\n')
    def exportAttributes(self, outfile, level, namespace_='', name_='docIndexEntryType'):
        pass
    def exportChildren(self, outfile, level, namespace_='', name_='docIndexEntryType'):
        if self.primaryie is not None:
            showIndent(outfile, level)
            outfile.write('<%sprimaryie>%s</%sprimaryie>\n' % (namespace_, self.format_string(quote_xml(self.primaryie).encode(ExternalEncoding), input_name='primaryie'), namespace_))
        if self.secondaryie is not None:
            showIndent(outfile, level)
            outfile.write('<%ssecondaryie>%s</%ssecondaryie>\n' % (namespace_, self.format_string(quote_xml(self.secondaryie).encode(ExternalEncoding), input_name='secondaryie'), namespace_))
    def hasContent_(self):
        if (
            self.primaryie is not None or
            self.secondaryie is not None
            ):
            return True
        else:
            return False
    def exportLiteral(self, outfile, level, name_='docIndexEntryType'):
        level += 1
        self.exportLiteralAttributes(outfile, level, name_)
        if self.hasContent_():
            self.exportLiteralChildren(outfile, level, name_)
    def exportLiteralAttributes(self, outfile, level, name_):
        pass
    def exportLiteralChildren(self, outfile, level, name_):
        showIndent(outfile, level)
        outfile.write('primaryie=%s,\n' % quote_python(self.primaryie).encode(ExternalEncoding))
        showIndent(outfile, level)
        outfile.write('secondaryie=%s,\n' % quote_python(self.secondaryie).encode(ExternalEncoding))
    def build(self, node_):
        attrs = node_.attributes
        self.buildAttributes(attrs)
        for child_ in node_.childNodes:
            nodeName_ = child_.nodeName.split(':')[-1]
            self.buildChildren(child_, nodeName_)
    def buildAttributes(self, attrs):
        pass
    def buildChildren(self, child_, nodeName_):
        if child_.nodeType == Node.ELEMENT_NODE and \
            nodeName_ == 'primaryie':
            primaryie_ = ''
            for text__content_ in child_.childNodes:
                primaryie_ += text__content_.nodeValue
            self.primaryie = primaryie_
        elif child_.nodeType == Node.ELEMENT_NODE and \
            nodeName_ == 'secondaryie':
            secondaryie_ = ''
            for text__content_ in child_.childNodes:
                secondaryie_ += text__content_.nodeValue
            self.secondaryie = secondaryie_
# end class docIndexEntryType


class docListType(GeneratedsSuper):
    subclass = None
    superclass = None
    def __init__(self, listitem=None):
        if listitem is None:
            self.listitem = []
        else:
            self.listitem = listitem
    def factory(*args_, **kwargs_):
        if docListType.subclass:
            return docListType.subclass(*args_, **kwargs_)
        else:
            return docListType(*args_, **kwargs_)
    factory = staticmethod(factory)
    def get_listitem(self): return self.listitem
    def set_listitem(self, listitem): self.listitem = listitem
    def add_listitem(self, value): self.listitem.append(value)
    def insert_listitem(self, index, value): self.listitem[index] = value
    def export(self, outfile, level, namespace_='', name_='docListType', namespacedef_=''):
        showIndent(outfile, level)
        outfile.write('<%s%s %s' % (namespace_, name_, namespacedef_, ))
        self.exportAttributes(outfile, level, namespace_, name_='docListType')
        if self.hasContent_():
            outfile.write('>\n')
            self.exportChildren(outfile, level + 1, namespace_, name_)
            showIndent(outfile, level)
            outfile.write('</%s%s>\n' % (namespace_, name_))
        else:
            outfile.write(' />\n')
    def exportAttributes(self, outfile, level, namespace_='', name_='docListType'):
        pass
    def exportChildren(self, outfile, level, namespace_='', name_='docListType'):
        for listitem_ in self.listitem:
            listitem_.export(outfile, level, namespace_, name_='listitem')
    def hasContent_(self):
        if (
            self.listitem is not None
            ):
            return True
        else:
            return False
    def exportLiteral(self, outfile, level, name_='docListType'):
        level += 1
        self.exportLiteralAttributes(outfile, level, name_)
        if self.hasContent_():
            self.exportLiteralChildren(outfile, level, name_)
    def exportLiteralAttributes(self, outfile, level, name_):
        pass
    def exportLiteralChildren(self, outfile, level, name_):
        showIndent(outfile, level)
        outfile.write('listitem=[\n')
        level += 1
        for listitem in self.listitem:
            showIndent(outfile, level)
            outfile.write('model_.listitem(\n')
            listitem.exportLiteral(outfile, level, name_='listitem')
            showIndent(outfile, level)
            outfile.write('),\n')
        level -= 1
        showIndent(outfile, level)
        outfile.write('],\n')
    def build(self, node_):
        attrs = node_.attributes
        self.buildAttributes(attrs)
        for child_ in node_.childNodes:
            nodeName_ = child_.nodeName.split(':')[-1]
            self.buildChildren(child_, nodeName_)
    def buildAttributes(self, attrs):
        pass
    def buildChildren(self, child_, nodeName_):
        if child_.nodeType == Node.ELEMENT_NODE and \
            nodeName_ == 'listitem':
            obj_ = docListItemType.factory()
            obj_.build(child_)
            self.listitem.append(obj_)
# end class docListType


class docListItemType(GeneratedsSuper):
    subclass = None
    superclass = None
    def __init__(self, para=None):
        if para is None:
            self.para = []
        else:
            self.para = para
    def factory(*args_, **kwargs_):
        if docListItemType.subclass:
            return docListItemType.subclass(*args_, **kwargs_)
        else:
            return docListItemType(*args_, **kwargs_)
    factory = staticmethod(factory)
    def get_para(self): return self.para
    def set_para(self, para): self.para = para
    def add_para(self, value): self.para.append(value)
    def insert_para(self, index, value): self.para[index] = value
    def export(self, outfile, level, namespace_='', name_='docListItemType', namespacedef_=''):
        showIndent(outfile, level)
        outfile.write('<%s%s %s' % (namespace_, name_, namespacedef_, ))
        self.exportAttributes(outfile, level, namespace_, name_='docListItemType')
        if self.hasContent_():
            outfile.write('>\n')
            self.exportChildren(outfile, level + 1, namespace_, name_)
            showIndent(outfile, level)
            outfile.write('</%s%s>\n' % (namespace_, name_))
        else:
            outfile.write(' />\n')
    def exportAttributes(self, outfile, level, namespace_='', name_='docListItemType'):
        pass
    def exportChildren(self, outfile, level, namespace_='', name_='docListItemType'):
        for para_ in self.para:
            para_.export(outfile, level, namespace_, name_='para')
    def hasContent_(self):
        if (
            self.para is not None
            ):
            return True
        else:
            return False
    def exportLiteral(self, outfile, level, name_='docListItemType'):
        level += 1
        self.exportLiteralAttributes(outfile, level, name_)
        if self.hasContent_():
            self.exportLiteralChildren(outfile, level, name_)
    def exportLiteralAttributes(self, outfile, level, name_):
        pass
    def exportLiteralChildren(self, outfile, level, name_):
        showIndent(outfile, level)
        outfile.write('para=[\n')
        level += 1
        for para in self.para:
            showIndent(outfile, level)
            outfile.write('model_.para(\n')
            para.exportLiteral(outfile, level, name_='para')
            showIndent(outfile, level)
            outfile.write('),\n')
        level -= 1
        showIndent(outfile, level)
        outfile.write('],\n')
    def build(self, node_):
        attrs = node_.attributes
        self.buildAttributes(attrs)
        for child_ in node_.childNodes:
            nodeName_ = child_.nodeName.split(':')[-1]
            self.buildChildren(child_, nodeName_)
    def buildAttributes(self, attrs):
        pass
    def buildChildren(self, child_, nodeName_):
        if child_.nodeType == Node.ELEMENT_NODE and \
            nodeName_ == 'para':
            obj_ = docParaType.factory()
            obj_.build(child_)
            self.para.append(obj_)
# end class docListItemType


class docSimpleSectType(GeneratedsSuper):
    subclass = None
    superclass = None
    def __init__(self, kind=None, title=None, para=None):
        self.kind = kind
        self.title = title
        if para is None:
            self.para = []
        else:
            self.para = para
    def factory(*args_, **kwargs_):
        if docSimpleSectType.subclass:
            return docSimpleSectType.subclass(*args_, **kwargs_)
        else:
            return docSimpleSectType(*args_, **kwargs_)
    factory = staticmethod(factory)
    def get_title(self): return self.title
    def set_title(self, title): self.title = title
    def get_para(self): return self.para
    def set_para(self, para): self.para = para
    def add_para(self, value): self.para.append(value)
    def insert_para(self, index, value): self.para[index] = value
    def get_kind(self): return self.kind
    def set_kind(self, kind): self.kind = kind
    def export(self, outfile, level, namespace_='', name_='docSimpleSectType', namespacedef_=''):
        showIndent(outfile, level)
        outfile.write('<%s%s %s' % (namespace_, name_, namespacedef_, ))
        self.exportAttributes(outfile, level, namespace_, name_='docSimpleSectType')
        if self.hasContent_():
            outfile.write('>\n')
            self.exportChildren(outfile, level + 1, namespace_, name_)
            showIndent(outfile, level)
            outfile.write('</%s%s>\n' % (namespace_, name_))
        else:
            outfile.write(' />\n')
    def exportAttributes(self, outfile, level, namespace_='', name_='docSimpleSectType'):
        if self.kind is not None:
            outfile.write(' kind=%s' % (quote_attrib(self.kind), ))
    def exportChildren(self, outfile, level, namespace_='', name_='docSimpleSectType'):
        if self.title:
            self.title.export(outfile, level, namespace_, name_='title')
        for para_ in self.para:
            para_.export(outfile, level, namespace_, name_='para')
    def hasContent_(self):
        if (
            self.title is not None or
            self.para is not None
            ):
            return True
        else:
            return False
    def exportLiteral(self, outfile, level, name_='docSimpleSectType'):
        level += 1
        self.exportLiteralAttributes(outfile, level, name_)
        if self.hasContent_():
            self.exportLiteralChildren(outfile, level, name_)
    def exportLiteralAttributes(self, outfile, level, name_):
        if self.kind is not None:
            showIndent(outfile, level)
            outfile.write('kind = "%s",\n' % (self.kind,))
    def exportLiteralChildren(self, outfile, level, name_):
        if self.title:
            showIndent(outfile, level)
            outfile.write('title=model_.docTitleType(\n')
            self.title.exportLiteral(outfile, level, name_='title')
            showIndent(outfile, level)
            outfile.write('),\n')
        showIndent(outfile, level)
        outfile.write('para=[\n')
        level += 1
        for para in self.para:
            showIndent(outfile, level)
            outfile.write('model_.para(\n')
            para.exportLiteral(outfile, level, name_='para')
            showIndent(outfile, level)
            outfile.write('),\n')
        level -= 1
        showIndent(outfile, level)
        outfile.write('],\n')
    def build(self, node_):
        attrs = node_.attributes
        self.buildAttributes(attrs)
        for child_ in node_.childNodes:
            nodeName_ = child_.nodeName.split(':')[-1]
            self.buildChildren(child_, nodeName_)
    def buildAttributes(self, attrs):
        if attrs.get('kind'):
            self.kind = attrs.get('kind').value
    def buildChildren(self, child_, nodeName_):
        if child_.nodeType == Node.ELEMENT_NODE and \
            nodeName_ == 'title':
            obj_ = docTitleType.factory()
            obj_.build(child_)
            self.set_title(obj_)
        elif child_.nodeType == Node.ELEMENT_NODE and \
            nodeName_ == 'para':
            obj_ = docParaType.factory()
            obj_.build(child_)
            self.para.append(obj_)
# end class docSimpleSectType


class docVarListEntryType(GeneratedsSuper):
    subclass = None
    superclass = None
    def __init__(self, term=None):
        self.term = term
    def factory(*args_, **kwargs_):
        if docVarListEntryType.subclass:
            return docVarListEntryType.subclass(*args_, **kwargs_)
        else:
            return docVarListEntryType(*args_, **kwargs_)
    factory = staticmethod(factory)
    def get_term(self): return self.term
    def set_term(self, term): self.term = term
    def export(self, outfile, level, namespace_='', name_='docVarListEntryType', namespacedef_=''):
        showIndent(outfile, level)
        outfile.write('<%s%s %s' % (namespace_, name_, namespacedef_, ))
        self.exportAttributes(outfile, level, namespace_, name_='docVarListEntryType')
        if self.hasContent_():
            outfile.write('>\n')
            self.exportChildren(outfile, level + 1, namespace_, name_)
            showIndent(outfile, level)
            outfile.write('</%s%s>\n' % (namespace_, name_))
        else:
            outfile.write(' />\n')
    def exportAttributes(self, outfile, level, namespace_='', name_='docVarListEntryType'):
        pass
    def exportChildren(self, outfile, level, namespace_='', name_='docVarListEntryType'):
        if self.term:
            self.term.export(outfile, level, namespace_, name_='term', )
    def hasContent_(self):
        if (
            self.term is not None
            ):
            return True
        else:
            return False
    def exportLiteral(self, outfile, level, name_='docVarListEntryType'):
        level += 1
        self.exportLiteralAttributes(outfile, level, name_)
        if self.hasContent_():
            self.exportLiteralChildren(outfile, level, name_)
    def exportLiteralAttributes(self, outfile, level, name_):
        pass
    def exportLiteralChildren(self, outfile, level, name_):
        if self.term:
            showIndent(outfile, level)
            outfile.write('term=model_.docTitleType(\n')
            self.term.exportLiteral(outfile, level, name_='term')
            showIndent(outfile, level)
            outfile.write('),\n')
    def build(self, node_):
        attrs = node_.attributes
        self.buildAttributes(attrs)
        for child_ in node_.childNodes:
            nodeName_ = child_.nodeName.split(':')[-1]
            self.buildChildren(child_, nodeName_)
    def buildAttributes(self, attrs):
        pass
    def buildChildren(self, child_, nodeName_):
        if child_.nodeType == Node.ELEMENT_NODE and \
            nodeName_ == 'term':
            obj_ = docTitleType.factory()
            obj_.build(child_)
            self.set_term(obj_)
# end class docVarListEntryType


class docVariableListType(GeneratedsSuper):
    subclass = None
    superclass = None
    def __init__(self, valueOf_=''):
        self.valueOf_ = valueOf_
    def factory(*args_, **kwargs_):
        if docVariableListType.subclass:
            return docVariableListType.subclass(*args_, **kwargs_)
        else:
            return docVariableListType(*args_, **kwargs_)
    factory = staticmethod(factory)
    def getValueOf_(self): return self.valueOf_
    def setValueOf_(self, valueOf_): self.valueOf_ = valueOf_
    def export(self, outfile, level, namespace_='', name_='docVariableListType', namespacedef_=''):
        showIndent(outfile, level)
        outfile.write('<%s%s %s' % (namespace_, name_, namespacedef_, ))
        self.exportAttributes(outfile, level, namespace_, name_='docVariableListType')
        if self.hasContent_():
            outfile.write('>\n')
            self.exportChildren(outfile, level + 1, namespace_, name_)
            showIndent(outfile, level)
            outfile.write('</%s%s>\n' % (namespace_, name_))
        else:
            outfile.write(' />\n')
    def exportAttributes(self, outfile, level, namespace_='', name_='docVariableListType'):
        pass
    def exportChildren(self, outfile, level, namespace_='', name_='docVariableListType'):
        if self.valueOf_.find('![CDATA')>-1:
            value=quote_xml('%s' % self.valueOf_)
            value=value.replace('![CDATA','<![CDATA')
            value=value.replace(']]',']]>')
            outfile.write(value)
        else:
            outfile.write(quote_xml('%s' % self.valueOf_))
    def hasContent_(self):
        if (
            self.valueOf_ is not None
            ):
            return True
        else:
            return False
    def exportLiteral(self, outfile, level, name_='docVariableListType'):
        level += 1
        self.exportLiteralAttributes(outfile, level, name_)
        if self.hasContent_():
            self.exportLiteralChildren(outfile, level, name_)
    def exportLiteralAttributes(self, outfile, level, name_):
        pass
    def exportLiteralChildren(self, outfile, level, name_):
        showIndent(outfile, level)
        outfile.write('valueOf_ = "%s",\n' % (self.valueOf_,))
    def build(self, node_):
        attrs = node_.attributes
        self.buildAttributes(attrs)
        self.valueOf_ = ''
        for child_ in node_.childNodes:
            nodeName_ = child_.nodeName.split(':')[-1]
            self.buildChildren(child_, nodeName_)
    def buildAttributes(self, attrs):
        pass
    def buildChildren(self, child_, nodeName_):
        if child_.nodeType == Node.TEXT_NODE:
            self.valueOf_ += child_.nodeValue
        elif child_.nodeType == Node.CDATA_SECTION_NODE:
            self.valueOf_ += '![CDATA['+child_.nodeValue+']]'
# end class docVariableListType


class docRefTextType(GeneratedsSuper):
    subclass = None
    superclass = None
    def __init__(self, refid=None, kindref=None, external=None, valueOf_='', mixedclass_=None, content_=None):
        self.refid = refid
        self.kindref = kindref
        self.external = external
        if mixedclass_ is None:
            self.mixedclass_ = MixedContainer
        else:
            self.mixedclass_ = mixedclass_
        if content_ is None:
            self.content_ = []
        else:
            self.content_ = content_
    def factory(*args_, **kwargs_):
        if docRefTextType.subclass:
            return docRefTextType.subclass(*args_, **kwargs_)
        else:
            return docRefTextType(*args_, **kwargs_)
    factory = staticmethod(factory)
    def get_refid(self): return self.refid
    def set_refid(self, refid): self.refid = refid
    def get_kindref(self): return self.kindref
    def set_kindref(self, kindref): self.kindref = kindref
    def get_external(self): return self.external
    def set_external(self, external): self.external = external
    def getValueOf_(self): return self.valueOf_
    def setValueOf_(self, valueOf_): self.valueOf_ = valueOf_
    def export(self, outfile, level, namespace_='', name_='docRefTextType', namespacedef_=''):
        showIndent(outfile, level)
        outfile.write('<%s%s %s' % (namespace_, name_, namespacedef_, ))
        self.exportAttributes(outfile, level, namespace_, name_='docRefTextType')
        outfile.write('>')
        self.exportChildren(outfile, level + 1, namespace_, name_)
        outfile.write('</%s%s>\n' % (namespace_, name_))
    def exportAttributes(self, outfile, level, namespace_='', name_='docRefTextType'):
        if self.refid is not None:
            outfile.write(' refid=%s' % (self.format_string(quote_attrib(self.refid).encode(ExternalEncoding), input_name='refid'), ))
        if self.kindref is not None:
            outfile.write(' kindref=%s' % (quote_attrib(self.kindref), ))
        if self.external is not None:
            outfile.write(' external=%s' % (self.format_string(quote_attrib(self.external).encode(ExternalEncoding), input_name='external'), ))
    def exportChildren(self, outfile, level, namespace_='', name_='docRefTextType'):
        if self.valueOf_.find('![CDATA')>-1:
            value=quote_xml('%s' % self.valueOf_)
            value=value.replace('![CDATA','<![CDATA')
            value=value.replace(']]',']]>')
            outfile.write(value)
        else:
            outfile.write(quote_xml('%s' % self.valueOf_))
    def hasContent_(self):
        if (
            self.valueOf_ is not None
            ):
            return True
        else:
            return False
    def exportLiteral(self, outfile, level, name_='docRefTextType'):
        level += 1
        self.exportLiteralAttributes(outfile, level, name_)
        if self.hasContent_():
            self.exportLiteralChildren(outfile, level, name_)
    def exportLiteralAttributes(self, outfile, level, name_):
        if self.refid is not None:
            showIndent(outfile, level)
            outfile.write('refid = %s,\n' % (self.refid,))
        if self.kindref is not None:
            showIndent(outfile, level)
            outfile.write('kindref = "%s",\n' % (self.kindref,))
        if self.external is not None:
            showIndent(outfile, level)
            outfile.write('external = %s,\n' % (self.external,))
    def exportLiteralChildren(self, outfile, level, name_):
        showIndent(outfile, level)
        outfile.write('valueOf_ = "%s",\n' % (self.valueOf_,))
    def build(self, node_):
        attrs = node_.attributes
        self.buildAttributes(attrs)
        self.valueOf_ = ''
        for child_ in node_.childNodes:
            nodeName_ = child_.nodeName.split(':')[-1]
            self.buildChildren(child_, nodeName_)
    def buildAttributes(self, attrs):
        if attrs.get('refid'):
            self.refid = attrs.get('refid').value
        if attrs.get('kindref'):
            self.kindref = attrs.get('kindref').value
        if attrs.get('external'):
            self.external = attrs.get('external').value
    def buildChildren(self, child_, nodeName_):
        if child_.nodeType == Node.TEXT_NODE:
            obj_ = self.mixedclass_(MixedContainer.CategoryText,
                MixedContainer.TypeNone, '', child_.nodeValue)
            self.content_.append(obj_)
        if child_.nodeType == Node.TEXT_NODE:
            self.valueOf_ += child_.nodeValue
        elif child_.nodeType == Node.CDATA_SECTION_NODE:
            self.valueOf_ += '![CDATA['+child_.nodeValue+']]'
# end class docRefTextType


class docTableType(GeneratedsSuper):
    subclass = None
    superclass = None
    def __init__(self, rows=None, cols=None, row=None, caption=None):
        self.rows = rows
        self.cols = cols
        if row is None:
            self.row = []
        else:
            self.row = row
        self.caption = caption
    def factory(*args_, **kwargs_):
        if docTableType.subclass:
            return docTableType.subclass(*args_, **kwargs_)
        else:
            return docTableType(*args_, **kwargs_)
    factory = staticmethod(factory)
    def get_row(self): return self.row
    def set_row(self, row): self.row = row
    def add_row(self, value): self.row.append(value)
    def insert_row(self, index, value): self.row[index] = value
    def get_caption(self): return self.caption
    def set_caption(self, caption): self.caption = caption
    def get_rows(self): return self.rows
    def set_rows(self, rows): self.rows = rows
    def get_cols(self): return self.cols
    def set_cols(self, cols): self.cols = cols
    def export(self, outfile, level, namespace_='', name_='docTableType', namespacedef_=''):
        showIndent(outfile, level)
        outfile.write('<%s%s %s' % (namespace_, name_, namespacedef_, ))
        self.exportAttributes(outfile, level, namespace_, name_='docTableType')
        if self.hasContent_():
            outfile.write('>\n')
            self.exportChildren(outfile, level + 1, namespace_, name_)
            showIndent(outfile, level)
            outfile.write('</%s%s>\n' % (namespace_, name_))
        else:
            outfile.write(' />\n')
    def exportAttributes(self, outfile, level, namespace_='', name_='docTableType'):
        if self.rows is not None:
            outfile.write(' rows="%s"' % self.format_integer(self.rows, input_name='rows'))
        if self.cols is not None:
            outfile.write(' cols="%s"' % self.format_integer(self.cols, input_name='cols'))
    def exportChildren(self, outfile, level, namespace_='', name_='docTableType'):
        for row_ in self.row:
            row_.export(outfile, level, namespace_, name_='row')
        if self.caption:
            self.caption.export(outfile, level, namespace_, name_='caption')
    def hasContent_(self):
        if (
            self.row is not None or
            self.caption is not None
            ):
            return True
        else:
            return False
    def exportLiteral(self, outfile, level, name_='docTableType'):
        level += 1
        self.exportLiteralAttributes(outfile, level, name_)
        if self.hasContent_():
            self.exportLiteralChildren(outfile, level, name_)
    def exportLiteralAttributes(self, outfile, level, name_):
        if self.rows is not None:
            showIndent(outfile, level)
            outfile.write('rows = %s,\n' % (self.rows,))
        if self.cols is not None:
            showIndent(outfile, level)
            outfile.write('cols = %s,\n' % (self.cols,))
    def exportLiteralChildren(self, outfile, level, name_):
        showIndent(outfile, level)
        outfile.write('row=[\n')
        level += 1
        for row in self.row:
            showIndent(outfile, level)
            outfile.write('model_.row(\n')
            row.exportLiteral(outfile, level, name_='row')
            showIndent(outfile, level)
            outfile.write('),\n')
        level -= 1
        showIndent(outfile, level)
        outfile.write('],\n')
        if self.caption:
            showIndent(outfile, level)
            outfile.write('caption=model_.docCaptionType(\n')
            self.caption.exportLiteral(outfile, level, name_='caption')
            showIndent(outfile, level)
            outfile.write('),\n')
    def build(self, node_):
        attrs = node_.attributes
        self.buildAttributes(attrs)
        for child_ in node_.childNodes:
            nodeName_ = child_.nodeName.split(':')[-1]
            self.buildChildren(child_, nodeName_)
    def buildAttributes(self, attrs):
        if attrs.get('rows'):
            try:
                self.rows = int(attrs.get('rows').value)
            except ValueError, exp:
                raise ValueError('Bad integer attribute (rows): %s' % exp)
        if attrs.get('cols'):
            try:
                self.cols = int(attrs.get('cols').value)
            except ValueError, exp:
                raise ValueError('Bad integer attribute (cols): %s' % exp)
    def buildChildren(self, child_, nodeName_):
        if child_.nodeType == Node.ELEMENT_NODE and \
            nodeName_ == 'row':
            obj_ = docRowType.factory()
            obj_.build(child_)
            self.row.append(obj_)
        elif child_.nodeType == Node.ELEMENT_NODE and \
            nodeName_ == 'caption':
            obj_ = docCaptionType.factory()
            obj_.build(child_)
            self.set_caption(obj_)
# end class docTableType


class docRowType(GeneratedsSuper):
    subclass = None
    superclass = None
    def __init__(self, entry=None):
        if entry is None:
            self.entry = []
        else:
            self.entry = entry
    def factory(*args_, **kwargs_):
        if docRowType.subclass:
            return docRowType.subclass(*args_, **kwargs_)
        else:
            return docRowType(*args_, **kwargs_)
    factory = staticmethod(factory)
    def get_entry(self): return self.entry
    def set_entry(self, entry): self.entry = entry
    def add_entry(self, value): self.entry.append(value)
    def insert_entry(self, index, value): self.entry[index] = value
    def export(self, outfile, level, namespace_='', name_='docRowType', namespacedef_=''):
        showIndent(outfile, level)
        outfile.write('<%s%s %s' % (namespace_, name_, namespacedef_, ))
        self.exportAttributes(outfile, level, namespace_, name_='docRowType')
        if self.hasContent_():
            outfile.write('>\n')
            self.exportChildren(outfile, level + 1, namespace_, name_)
            showIndent(outfile, level)
            outfile.write('</%s%s>\n' % (namespace_, name_))
        else:
            outfile.write(' />\n')
    def exportAttributes(self, outfile, level, namespace_='', name_='docRowType'):
        pass
    def exportChildren(self, outfile, level, namespace_='', name_='docRowType'):
        for entry_ in self.entry:
            entry_.export(outfile, level, namespace_, name_='entry')
    def hasContent_(self):
        if (
            self.entry is not None
            ):
            return True
        else:
            return False
    def exportLiteral(self, outfile, level, name_='docRowType'):
        level += 1
        self.exportLiteralAttributes(outfile, level, name_)
        if self.hasContent_():
            self.exportLiteralChildren(outfile, level, name_)
    def exportLiteralAttributes(self, outfile, level, name_):
        pass
    def exportLiteralChildren(self, outfile, level, name_):
        showIndent(outfile, level)
        outfile.write('entry=[\n')
        level += 1
        for entry in self.entry:
            showIndent(outfile, level)
            outfile.write('model_.entry(\n')
            entry.exportLiteral(outfile, level, name_='entry')
            showIndent(outfile, level)
            outfile.write('),\n')
        level -= 1
        showIndent(outfile, level)
        outfile.write('],\n')
    def build(self, node_):
        attrs = node_.attributes
        self.buildAttributes(attrs)
        for child_ in node_.childNodes:
            nodeName_ = child_.nodeName.split(':')[-1]
            self.buildChildren(child_, nodeName_)
    def buildAttributes(self, attrs):
        pass
    def buildChildren(self, child_, nodeName_):
        if child_.nodeType == Node.ELEMENT_NODE and \
            nodeName_ == 'entry':
            obj_ = docEntryType.factory()
            obj_.build(child_)
            self.entry.append(obj_)
# end class docRowType


class docEntryType(GeneratedsSuper):
    subclass = None
    superclass = None
    def __init__(self, thead=None, para=None):
        self.thead = thead
        if para is None:
            self.para = []
        else:
            self.para = para
    def factory(*args_, **kwargs_):
        if docEntryType.subclass:
            return docEntryType.subclass(*args_, **kwargs_)
        else:
            return docEntryType(*args_, **kwargs_)
    factory = staticmethod(factory)
    def get_para(self): return self.para
    def set_para(self, para): self.para = para
    def add_para(self, value): self.para.append(value)
    def insert_para(self, index, value): self.para[index] = value
    def get_thead(self): return self.thead
    def set_thead(self, thead): self.thead = thead
    def export(self, outfile, level, namespace_='', name_='docEntryType', namespacedef_=''):
        showIndent(outfile, level)
        outfile.write('<%s%s %s' % (namespace_, name_, namespacedef_, ))
        self.exportAttributes(outfile, level, namespace_, name_='docEntryType')
        if self.hasContent_():
            outfile.write('>\n')
            self.exportChildren(outfile, level + 1, namespace_, name_)
            showIndent(outfile, level)
            outfile.write('</%s%s>\n' % (namespace_, name_))
        else:
            outfile.write(' />\n')
    def exportAttributes(self, outfile, level, namespace_='', name_='docEntryType'):
        if self.thead is not None:
            outfile.write(' thead=%s' % (quote_attrib(self.thead), ))
    def exportChildren(self, outfile, level, namespace_='', name_='docEntryType'):
        for para_ in self.para:
            para_.export(outfile, level, namespace_, name_='para')
    def hasContent_(self):
        if (
            self.para is not None
            ):
            return True
        else:
            return False
    def exportLiteral(self, outfile, level, name_='docEntryType'):
        level += 1
        self.exportLiteralAttributes(outfile, level, name_)
        if self.hasContent_():
            self.exportLiteralChildren(outfile, level, name_)
    def exportLiteralAttributes(self, outfile, level, name_):
        if self.thead is not None:
            showIndent(outfile, level)
            outfile.write('thead = "%s",\n' % (self.thead,))
    def exportLiteralChildren(self, outfile, level, name_):
        showIndent(outfile, level)
        outfile.write('para=[\n')
        level += 1
        for para in self.para:
            showIndent(outfile, level)
            outfile.write('model_.para(\n')
            para.exportLiteral(outfile, level, name_='para')
            showIndent(outfile, level)
            outfile.write('),\n')
        level -= 1
        showIndent(outfile, level)
        outfile.write('],\n')
    def build(self, node_):
        attrs = node_.attributes
        self.buildAttributes(attrs)
        for child_ in node_.childNodes:
            nodeName_ = child_.nodeName.split(':')[-1]
            self.buildChildren(child_, nodeName_)
    def buildAttributes(self, attrs):
        if attrs.get('thead'):
            self.thead = attrs.get('thead').value
    def buildChildren(self, child_, nodeName_):
        if child_.nodeType == Node.ELEMENT_NODE and \
            nodeName_ == 'para':
            obj_ = docParaType.factory()
            obj_.build(child_)
            self.para.append(obj_)
# end class docEntryType


class docCaptionType(GeneratedsSuper):
    subclass = None
    superclass = None
    def __init__(self, valueOf_='', mixedclass_=None, content_=None):
        if mixedclass_ is None:
            self.mixedclass_ = MixedContainer
        else:
            self.mixedclass_ = mixedclass_
        if content_ is None:
            self.content_ = []
        else:
            self.content_ = content_
    def factory(*args_, **kwargs_):
        if docCaptionType.subclass:
            return docCaptionType.subclass(*args_, **kwargs_)
        else:
            return docCaptionType(*args_, **kwargs_)
    factory = staticmethod(factory)
    def getValueOf_(self): return self.valueOf_
    def setValueOf_(self, valueOf_): self.valueOf_ = valueOf_
    def export(self, outfile, level, namespace_='', name_='docCaptionType', namespacedef_=''):
        showIndent(outfile, level)
        outfile.write('<%s%s %s' % (namespace_, name_, namespacedef_, ))
        self.exportAttributes(outfile, level, namespace_, name_='docCaptionType')
        outfile.write('>')
        self.exportChildren(outfile, level + 1, namespace_, name_)
        outfile.write('</%s%s>\n' % (namespace_, name_))
    def exportAttributes(self, outfile, level, namespace_='', name_='docCaptionType'):
        pass
    def exportChildren(self, outfile, level, namespace_='', name_='docCaptionType'):
        if self.valueOf_.find('![CDATA')>-1:
            value=quote_xml('%s' % self.valueOf_)
            value=value.replace('![CDATA','<![CDATA')
            value=value.replace(']]',']]>')
            outfile.write(value)
        else:
            outfile.write(quote_xml('%s' % self.valueOf_))
    def hasContent_(self):
        if (
            self.valueOf_ is not None
            ):
            return True
        else:
            return False
    def exportLiteral(self, outfile, level, name_='docCaptionType'):
        level += 1
        self.exportLiteralAttributes(outfile, level, name_)
        if self.hasContent_():
            self.exportLiteralChildren(outfile, level, name_)
    def exportLiteralAttributes(self, outfile, level, name_):
        pass
    def exportLiteralChildren(self, outfile, level, name_):
        showIndent(outfile, level)
        outfile.write('valueOf_ = "%s",\n' % (self.valueOf_,))
    def build(self, node_):
        attrs = node_.attributes
        self.buildAttributes(attrs)
        self.valueOf_ = ''
        for child_ in node_.childNodes:
            nodeName_ = child_.nodeName.split(':')[-1]
            self.buildChildren(child_, nodeName_)
    def buildAttributes(self, attrs):
        pass
    def buildChildren(self, child_, nodeName_):
        if child_.nodeType == Node.TEXT_NODE:
            obj_ = self.mixedclass_(MixedContainer.CategoryText,
                MixedContainer.TypeNone, '', child_.nodeValue)
            self.content_.append(obj_)
        if child_.nodeType == Node.TEXT_NODE:
            self.valueOf_ += child_.nodeValue
        elif child_.nodeType == Node.CDATA_SECTION_NODE:
            self.valueOf_ += '![CDATA['+child_.nodeValue+']]'
# end class docCaptionType


class docHeadingType(GeneratedsSuper):
    subclass = None
    superclass = None
    def __init__(self, level=None, valueOf_='', mixedclass_=None, content_=None):
        self.level = level
        if mixedclass_ is None:
            self.mixedclass_ = MixedContainer
        else:
            self.mixedclass_ = mixedclass_
        if content_ is None:
            self.content_ = []
        else:
            self.content_ = content_
    def factory(*args_, **kwargs_):
        if docHeadingType.subclass:
            return docHeadingType.subclass(*args_, **kwargs_)
        else:
            return docHeadingType(*args_, **kwargs_)
    factory = staticmethod(factory)
    def get_level(self): return self.level
    def set_level(self, level): self.level = level
    def getValueOf_(self): return self.valueOf_
    def setValueOf_(self, valueOf_): self.valueOf_ = valueOf_
    def export(self, outfile, level, namespace_='', name_='docHeadingType', namespacedef_=''):
        showIndent(outfile, level)
        outfile.write('<%s%s %s' % (namespace_, name_, namespacedef_, ))
        self.exportAttributes(outfile, level, namespace_, name_='docHeadingType')
        outfile.write('>')
        self.exportChildren(outfile, level + 1, namespace_, name_)
        outfile.write('</%s%s>\n' % (namespace_, name_))
    def exportAttributes(self, outfile, level, namespace_='', name_='docHeadingType'):
        if self.level is not None:
            outfile.write(' level="%s"' % self.format_integer(self.level, input_name='level'))
    def exportChildren(self, outfile, level, namespace_='', name_='docHeadingType'):
        if self.valueOf_.find('![CDATA')>-1:
            value=quote_xml('%s' % self.valueOf_)
            value=value.replace('![CDATA','<![CDATA')
            value=value.replace(']]',']]>')
            outfile.write(value)
        else:
            outfile.write(quote_xml('%s' % self.valueOf_))
    def hasContent_(self):
        if (
            self.valueOf_ is not None
            ):
            return True
        else:
            return False
    def exportLiteral(self, outfile, level, name_='docHeadingType'):
        level += 1
        self.exportLiteralAttributes(outfile, level, name_)
        if self.hasContent_():
            self.exportLiteralChildren(outfile, level, name_)
    def exportLiteralAttributes(self, outfile, level, name_):
        if self.level is not None:
            showIndent(outfile, level)
            outfile.write('level = %s,\n' % (self.level,))
    def exportLiteralChildren(self, outfile, level, name_):
        showIndent(outfile, level)
        outfile.write('valueOf_ = "%s",\n' % (self.valueOf_,))
    def build(self, node_):
        attrs = node_.attributes
        self.buildAttributes(attrs)
        self.valueOf_ = ''
        for child_ in node_.childNodes:
            nodeName_ = child_.nodeName.split(':')[-1]
            self.buildChildren(child_, nodeName_)
    def buildAttributes(self, attrs):
        if attrs.get('level'):
            try:
                self.level = int(attrs.get('level').value)
            except ValueError, exp:
                raise ValueError('Bad integer attribute (level): %s' % exp)
    def buildChildren(self, child_, nodeName_):
        if child_.nodeType == Node.TEXT_NODE:
            obj_ = self.mixedclass_(MixedContainer.CategoryText,
                MixedContainer.TypeNone, '', child_.nodeValue)
            self.content_.append(obj_)
        if child_.nodeType == Node.TEXT_NODE:
            self.valueOf_ += child_.nodeValue
        elif child_.nodeType == Node.CDATA_SECTION_NODE:
            self.valueOf_ += '![CDATA['+child_.nodeValue+']]'
# end class docHeadingType


class docImageType(GeneratedsSuper):
    subclass = None
    superclass = None
    def __init__(self, width=None, type_=None, name=None, height=None, valueOf_='', mixedclass_=None, content_=None):
        self.width = width
        self.type_ = type_
        self.name = name
        self.height = height
        if mixedclass_ is None:
            self.mixedclass_ = MixedContainer
        else:
            self.mixedclass_ = mixedclass_
        if content_ is None:
            self.content_ = []
        else:
            self.content_ = content_
    def factory(*args_, **kwargs_):
        if docImageType.subclass:
            return docImageType.subclass(*args_, **kwargs_)
        else:
            return docImageType(*args_, **kwargs_)
    factory = staticmethod(factory)
    def get_width(self): return self.width
    def set_width(self, width): self.width = width
    def get_type(self): return self.type_
    def set_type(self, type_): self.type_ = type_
    def get_name(self): return self.name
    def set_name(self, name): self.name = name
    def get_height(self): return self.height
    def set_height(self, height): self.height = height
    def getValueOf_(self): return self.valueOf_
    def setValueOf_(self, valueOf_): self.valueOf_ = valueOf_
    def export(self, outfile, level, namespace_='', name_='docImageType', namespacedef_=''):
        showIndent(outfile, level)
        outfile.write('<%s%s %s' % (namespace_, name_, namespacedef_, ))
        self.exportAttributes(outfile, level, namespace_, name_='docImageType')
        outfile.write('>')
        self.exportChildren(outfile, level + 1, namespace_, name_)
        outfile.write('</%s%s>\n' % (namespace_, name_))
    def exportAttributes(self, outfile, level, namespace_='', name_='docImageType'):
        if self.width is not None:
            outfile.write(' width=%s' % (self.format_string(quote_attrib(self.width).encode(ExternalEncoding), input_name='width'), ))
        if self.type_ is not None:
            outfile.write(' type=%s' % (quote_attrib(self.type_), ))
        if self.name is not None:
            outfile.write(' name=%s' % (self.format_string(quote_attrib(self.name).encode(ExternalEncoding), input_name='name'), ))
        if self.height is not None:
            outfile.write(' height=%s' % (self.format_string(quote_attrib(self.height).encode(ExternalEncoding), input_name='height'), ))
    def exportChildren(self, outfile, level, namespace_='', name_='docImageType'):
        if self.valueOf_.find('![CDATA')>-1:
            value=quote_xml('%s' % self.valueOf_)
            value=value.replace('![CDATA','<![CDATA')
            value=value.replace(']]',']]>')
            outfile.write(value)
        else:
            outfile.write(quote_xml('%s' % self.valueOf_))
    def hasContent_(self):
        if (
            self.valueOf_ is not None
            ):
            return True
        else:
            return False
    def exportLiteral(self, outfile, level, name_='docImageType'):
        level += 1
        self.exportLiteralAttributes(outfile, level, name_)
        if self.hasContent_():
            self.exportLiteralChildren(outfile, level, name_)
    def exportLiteralAttributes(self, outfile, level, name_):
        if self.width is not None:
            showIndent(outfile, level)
            outfile.write('width = %s,\n' % (self.width,))
        if self.type_ is not None:
            showIndent(outfile, level)
            outfile.write('type_ = "%s",\n' % (self.type_,))
        if self.name is not None:
            showIndent(outfile, level)
            outfile.write('name = %s,\n' % (self.name,))
        if self.height is not None:
            showIndent(outfile, level)
            outfile.write('height = %s,\n' % (self.height,))
    def exportLiteralChildren(self, outfile, level, name_):
        showIndent(outfile, level)
        outfile.write('valueOf_ = "%s",\n' % (self.valueOf_,))
    def build(self, node_):
        attrs = node_.attributes
        self.buildAttributes(attrs)
        self.valueOf_ = ''
        for child_ in node_.childNodes:
            nodeName_ = child_.nodeName.split(':')[-1]
            self.buildChildren(child_, nodeName_)
    def buildAttributes(self, attrs):
        if attrs.get('width'):
            self.width = attrs.get('width').value
        if attrs.get('type'):
            self.type_ = attrs.get('type').value
        if attrs.get('name'):
            self.name = attrs.get('name').value
        if attrs.get('height'):
            self.height = attrs.get('height').value
    def buildChildren(self, child_, nodeName_):
        if child_.nodeType == Node.TEXT_NODE:
            obj_ = self.mixedclass_(MixedContainer.CategoryText,
                MixedContainer.TypeNone, '', child_.nodeValue)
            self.content_.append(obj_)
        if child_.nodeType == Node.TEXT_NODE:
            self.valueOf_ += child_.nodeValue
        elif child_.nodeType == Node.CDATA_SECTION_NODE:
            self.valueOf_ += '![CDATA['+child_.nodeValue+']]'
# end class docImageType


class docDotFileType(GeneratedsSuper):
    subclass = None
    superclass = None
    def __init__(self, name=None, valueOf_='', mixedclass_=None, content_=None):
        self.name = name
        if mixedclass_ is None:
            self.mixedclass_ = MixedContainer
        else:
            self.mixedclass_ = mixedclass_
        if content_ is None:
            self.content_ = []
        else:
            self.content_ = content_
    def factory(*args_, **kwargs_):
        if docDotFileType.subclass:
            return docDotFileType.subclass(*args_, **kwargs_)
        else:
            return docDotFileType(*args_, **kwargs_)
    factory = staticmethod(factory)
    def get_name(self): return self.name
    def set_name(self, name): self.name = name
    def getValueOf_(self): return self.valueOf_
    def setValueOf_(self, valueOf_): self.valueOf_ = valueOf_
    def export(self, outfile, level, namespace_='', name_='docDotFileType', namespacedef_=''):
        showIndent(outfile, level)
        outfile.write('<%s%s %s' % (namespace_, name_, namespacedef_, ))
        self.exportAttributes(outfile, level, namespace_, name_='docDotFileType')
        outfile.write('>')
        self.exportChildren(outfile, level + 1, namespace_, name_)
        outfile.write('</%s%s>\n' % (namespace_, name_))
    def exportAttributes(self, outfile, level, namespace_='', name_='docDotFileType'):
        if self.name is not None:
            outfile.write(' name=%s' % (self.format_string(quote_attrib(self.name).encode(ExternalEncoding), input_name='name'), ))
    def exportChildren(self, outfile, level, namespace_='', name_='docDotFileType'):
        if self.valueOf_.find('![CDATA')>-1:
            value=quote_xml('%s' % self.valueOf_)
            value=value.replace('![CDATA','<![CDATA')
            value=value.replace(']]',']]>')
            outfile.write(value)
        else:
            outfile.write(quote_xml('%s' % self.valueOf_))
    def hasContent_(self):
        if (
            self.valueOf_ is not None
            ):
            return True
        else:
            return False
    def exportLiteral(self, outfile, level, name_='docDotFileType'):
        level += 1
        self.exportLiteralAttributes(outfile, level, name_)
        if self.hasContent_():
            self.exportLiteralChildren(outfile, level, name_)
    def exportLiteralAttributes(self, outfile, level, name_):
        if self.name is not None:
            showIndent(outfile, level)
            outfile.write('name = %s,\n' % (self.name,))
    def exportLiteralChildren(self, outfile, level, name_):
        showIndent(outfile, level)
        outfile.write('valueOf_ = "%s",\n' % (self.valueOf_,))
    def build(self, node_):
        attrs = node_.attributes
        self.buildAttributes(attrs)
        self.valueOf_ = ''
        for child_ in node_.childNodes:
            nodeName_ = child_.nodeName.split(':')[-1]
            self.buildChildren(child_, nodeName_)
    def buildAttributes(self, attrs):
        if attrs.get('name'):
            self.name = attrs.get('name').value
    def buildChildren(self, child_, nodeName_):
        if child_.nodeType == Node.TEXT_NODE:
            obj_ = self.mixedclass_(MixedContainer.CategoryText,
                MixedContainer.TypeNone, '', child_.nodeValue)
            self.content_.append(obj_)
        if child_.nodeType == Node.TEXT_NODE:
            self.valueOf_ += child_.nodeValue
        elif child_.nodeType == Node.CDATA_SECTION_NODE:
            self.valueOf_ += '![CDATA['+child_.nodeValue+']]'
# end class docDotFileType


class docTocItemType(GeneratedsSuper):
    subclass = None
    superclass = None
    def __init__(self, id=None, valueOf_='', mixedclass_=None, content_=None):
        self.id = id
        if mixedclass_ is None:
            self.mixedclass_ = MixedContainer
        else:
            self.mixedclass_ = mixedclass_
        if content_ is None:
            self.content_ = []
        else:
            self.content_ = content_
    def factory(*args_, **kwargs_):
        if docTocItemType.subclass:
            return docTocItemType.subclass(*args_, **kwargs_)
        else:
            return docTocItemType(*args_, **kwargs_)
    factory = staticmethod(factory)
    def get_id(self): return self.id
    def set_id(self, id): self.id = id
    def getValueOf_(self): return self.valueOf_
    def setValueOf_(self, valueOf_): self.valueOf_ = valueOf_
    def export(self, outfile, level, namespace_='', name_='docTocItemType', namespacedef_=''):
        showIndent(outfile, level)
        outfile.write('<%s%s %s' % (namespace_, name_, namespacedef_, ))
        self.exportAttributes(outfile, level, namespace_, name_='docTocItemType')
        outfile.write('>')
        self.exportChildren(outfile, level + 1, namespace_, name_)
        outfile.write('</%s%s>\n' % (namespace_, name_))
    def exportAttributes(self, outfile, level, namespace_='', name_='docTocItemType'):
        if self.id is not None:
            outfile.write(' id=%s' % (self.format_string(quote_attrib(self.id).encode(ExternalEncoding), input_name='id'), ))
    def exportChildren(self, outfile, level, namespace_='', name_='docTocItemType'):
        if self.valueOf_.find('![CDATA')>-1:
            value=quote_xml('%s' % self.valueOf_)
            value=value.replace('![CDATA','<![CDATA')
            value=value.replace(']]',']]>')
            outfile.write(value)
        else:
            outfile.write(quote_xml('%s' % self.valueOf_))
    def hasContent_(self):
        if (
            self.valueOf_ is not None
            ):
            return True
        else:
            return False
    def exportLiteral(self, outfile, level, name_='docTocItemType'):
        level += 1
        self.exportLiteralAttributes(outfile, level, name_)
        if self.hasContent_():
            self.exportLiteralChildren(outfile, level, name_)
    def exportLiteralAttributes(self, outfile, level, name_):
        if self.id is not None:
            showIndent(outfile, level)
            outfile.write('id = %s,\n' % (self.id,))
    def exportLiteralChildren(self, outfile, level, name_):
        showIndent(outfile, level)
        outfile.write('valueOf_ = "%s",\n' % (self.valueOf_,))
    def build(self, node_):
        attrs = node_.attributes
        self.buildAttributes(attrs)
        self.valueOf_ = ''
        for child_ in node_.childNodes:
            nodeName_ = child_.nodeName.split(':')[-1]
            self.buildChildren(child_, nodeName_)
    def buildAttributes(self, attrs):
        if attrs.get('id'):
            self.id = attrs.get('id').value
    def buildChildren(self, child_, nodeName_):
        if child_.nodeType == Node.TEXT_NODE:
            obj_ = self.mixedclass_(MixedContainer.CategoryText,
                MixedContainer.TypeNone, '', child_.nodeValue)
            self.content_.append(obj_)
        if child_.nodeType == Node.TEXT_NODE:
            self.valueOf_ += child_.nodeValue
        elif child_.nodeType == Node.CDATA_SECTION_NODE:
            self.valueOf_ += '![CDATA['+child_.nodeValue+']]'
# end class docTocItemType


class docTocListType(GeneratedsSuper):
    subclass = None
    superclass = None
    def __init__(self, tocitem=None):
        if tocitem is None:
            self.tocitem = []
        else:
            self.tocitem = tocitem
    def factory(*args_, **kwargs_):
        if docTocListType.subclass:
            return docTocListType.subclass(*args_, **kwargs_)
        else:
            return docTocListType(*args_, **kwargs_)
    factory = staticmethod(factory)
    def get_tocitem(self): return self.tocitem
    def set_tocitem(self, tocitem): self.tocitem = tocitem
    def add_tocitem(self, value): self.tocitem.append(value)
    def insert_tocitem(self, index, value): self.tocitem[index] = value
    def export(self, outfile, level, namespace_='', name_='docTocListType', namespacedef_=''):
        showIndent(outfile, level)
        outfile.write('<%s%s %s' % (namespace_, name_, namespacedef_, ))
        self.exportAttributes(outfile, level, namespace_, name_='docTocListType')
        if self.hasContent_():
            outfile.write('>\n')
            self.exportChildren(outfile, level + 1, namespace_, name_)
            showIndent(outfile, level)
            outfile.write('</%s%s>\n' % (namespace_, name_))
        else:
            outfile.write(' />\n')
    def exportAttributes(self, outfile, level, namespace_='', name_='docTocListType'):
        pass
    def exportChildren(self, outfile, level, namespace_='', name_='docTocListType'):
        for tocitem_ in self.tocitem:
            tocitem_.export(outfile, level, namespace_, name_='tocitem')
    def hasContent_(self):
        if (
            self.tocitem is not None
            ):
            return True
        else:
            return False
    def exportLiteral(self, outfile, level, name_='docTocListType'):
        level += 1
        self.exportLiteralAttributes(outfile, level, name_)
        if self.hasContent_():
            self.exportLiteralChildren(outfile, level, name_)
    def exportLiteralAttributes(self, outfile, level, name_):
        pass
    def exportLiteralChildren(self, outfile, level, name_):
        showIndent(outfile, level)
        outfile.write('tocitem=[\n')
        level += 1
        for tocitem in self.tocitem:
            showIndent(outfile, level)
            outfile.write('model_.tocitem(\n')
            tocitem.exportLiteral(outfile, level, name_='tocitem')
            showIndent(outfile, level)
            outfile.write('),\n')
        level -= 1
        showIndent(outfile, level)
        outfile.write('],\n')
    def build(self, node_):
        attrs = node_.attributes
        self.buildAttributes(attrs)
        for child_ in node_.childNodes:
            nodeName_ = child_.nodeName.split(':')[-1]
            self.buildChildren(child_, nodeName_)
    def buildAttributes(self, attrs):
        pass
    def buildChildren(self, child_, nodeName_):
        if child_.nodeType == Node.ELEMENT_NODE and \
            nodeName_ == 'tocitem':
            obj_ = docTocItemType.factory()
            obj_.build(child_)
            self.tocitem.append(obj_)
# end class docTocListType


class docLanguageType(GeneratedsSuper):
    subclass = None
    superclass = None
    def __init__(self, langid=None, para=None):
        self.langid = langid
        if para is None:
            self.para = []
        else:
            self.para = para
    def factory(*args_, **kwargs_):
        if docLanguageType.subclass:
            return docLanguageType.subclass(*args_, **kwargs_)
        else:
            return docLanguageType(*args_, **kwargs_)
    factory = staticmethod(factory)
    def get_para(self): return self.para
    def set_para(self, para): self.para = para
    def add_para(self, value): self.para.append(value)
    def insert_para(self, index, value): self.para[index] = value
    def get_langid(self): return self.langid
    def set_langid(self, langid): self.langid = langid
    def export(self, outfile, level, namespace_='', name_='docLanguageType', namespacedef_=''):
        showIndent(outfile, level)
        outfile.write('<%s%s %s' % (namespace_, name_, namespacedef_, ))
        self.exportAttributes(outfile, level, namespace_, name_='docLanguageType')
        if self.hasContent_():
            outfile.write('>\n')
            self.exportChildren(outfile, level + 1, namespace_, name_)
            showIndent(outfile, level)
            outfile.write('</%s%s>\n' % (namespace_, name_))
        else:
            outfile.write(' />\n')
    def exportAttributes(self, outfile, level, namespace_='', name_='docLanguageType'):
        if self.langid is not None:
            outfile.write(' langid=%s' % (self.format_string(quote_attrib(self.langid).encode(ExternalEncoding), input_name='langid'), ))
    def exportChildren(self, outfile, level, namespace_='', name_='docLanguageType'):
        for para_ in self.para:
            para_.export(outfile, level, namespace_, name_='para')
    def hasContent_(self):
        if (
            self.para is not None
            ):
            return True
        else:
            return False
    def exportLiteral(self, outfile, level, name_='docLanguageType'):
        level += 1
        self.exportLiteralAttributes(outfile, level, name_)
        if self.hasContent_():
            self.exportLiteralChildren(outfile, level, name_)
    def exportLiteralAttributes(self, outfile, level, name_):
        if self.langid is not None:
            showIndent(outfile, level)
            outfile.write('langid = %s,\n' % (self.langid,))
    def exportLiteralChildren(self, outfile, level, name_):
        showIndent(outfile, level)
        outfile.write('para=[\n')
        level += 1
        for para in self.para:
            showIndent(outfile, level)
            outfile.write('model_.para(\n')
            para.exportLiteral(outfile, level, name_='para')
            showIndent(outfile, level)
            outfile.write('),\n')
        level -= 1
        showIndent(outfile, level)
        outfile.write('],\n')
    def build(self, node_):
        attrs = node_.attributes
        self.buildAttributes(attrs)
        for child_ in node_.childNodes:
            nodeName_ = child_.nodeName.split(':')[-1]
            self.buildChildren(child_, nodeName_)
    def buildAttributes(self, attrs):
        if attrs.get('langid'):
            self.langid = attrs.get('langid').value
    def buildChildren(self, child_, nodeName_):
        if child_.nodeType == Node.ELEMENT_NODE and \
            nodeName_ == 'para':
            obj_ = docParaType.factory()
            obj_.build(child_)
            self.para.append(obj_)
# end class docLanguageType


class docParamListType(GeneratedsSuper):
    subclass = None
    superclass = None
    def __init__(self, kind=None, parameteritem=None):
        self.kind = kind
        if parameteritem is None:
            self.parameteritem = []
        else:
            self.parameteritem = parameteritem
    def factory(*args_, **kwargs_):
        if docParamListType.subclass:
            return docParamListType.subclass(*args_, **kwargs_)
        else:
            return docParamListType(*args_, **kwargs_)
    factory = staticmethod(factory)
    def get_parameteritem(self): return self.parameteritem
    def set_parameteritem(self, parameteritem): self.parameteritem = parameteritem
    def add_parameteritem(self, value): self.parameteritem.append(value)
    def insert_parameteritem(self, index, value): self.parameteritem[index] = value
    def get_kind(self): return self.kind
    def set_kind(self, kind): self.kind = kind
    def export(self, outfile, level, namespace_='', name_='docParamListType', namespacedef_=''):
        showIndent(outfile, level)
        outfile.write('<%s%s %s' % (namespace_, name_, namespacedef_, ))
        self.exportAttributes(outfile, level, namespace_, name_='docParamListType')
        if self.hasContent_():
            outfile.write('>\n')
            self.exportChildren(outfile, level + 1, namespace_, name_)
            showIndent(outfile, level)
            outfile.write('</%s%s>\n' % (namespace_, name_))
        else:
            outfile.write(' />\n')
    def exportAttributes(self, outfile, level, namespace_='', name_='docParamListType'):
        if self.kind is not None:
            outfile.write(' kind=%s' % (quote_attrib(self.kind), ))
    def exportChildren(self, outfile, level, namespace_='', name_='docParamListType'):
        for parameteritem_ in self.parameteritem:
            parameteritem_.export(outfile, level, namespace_, name_='parameteritem')
    def hasContent_(self):
        if (
            self.parameteritem is not None
            ):
            return True
        else:
            return False
    def exportLiteral(self, outfile, level, name_='docParamListType'):
        level += 1
        self.exportLiteralAttributes(outfile, level, name_)
        if self.hasContent_():
            self.exportLiteralChildren(outfile, level, name_)
    def exportLiteralAttributes(self, outfile, level, name_):
        if self.kind is not None:
            showIndent(outfile, level)
            outfile.write('kind = "%s",\n' % (self.kind,))
    def exportLiteralChildren(self, outfile, level, name_):
        showIndent(outfile, level)
        outfile.write('parameteritem=[\n')
        level += 1
        for parameteritem in self.parameteritem:
            showIndent(outfile, level)
            outfile.write('model_.parameteritem(\n')
            parameteritem.exportLiteral(outfile, level, name_='parameteritem')
            showIndent(outfile, level)
            outfile.write('),\n')
        level -= 1
        showIndent(outfile, level)
        outfile.write('],\n')
    def build(self, node_):
        attrs = node_.attributes
        self.buildAttributes(attrs)
        for child_ in node_.childNodes:
            nodeName_ = child_.nodeName.split(':')[-1]
            self.buildChildren(child_, nodeName_)
    def buildAttributes(self, attrs):
        if attrs.get('kind'):
            self.kind = attrs.get('kind').value
    def buildChildren(self, child_, nodeName_):
        if child_.nodeType == Node.ELEMENT_NODE and \
            nodeName_ == 'parameteritem':
            obj_ = docParamListItem.factory()
            obj_.build(child_)
            self.parameteritem.append(obj_)
# end class docParamListType


class docParamListItem(GeneratedsSuper):
    subclass = None
    superclass = None
    def __init__(self, parameternamelist=None, parameterdescription=None):
        if parameternamelist is None:
            self.parameternamelist = []
        else:
            self.parameternamelist = parameternamelist
        self.parameterdescription = parameterdescription
    def factory(*args_, **kwargs_):
        if docParamListItem.subclass:
            return docParamListItem.subclass(*args_, **kwargs_)
        else:
            return docParamListItem(*args_, **kwargs_)
    factory = staticmethod(factory)
    def get_parameternamelist(self): return self.parameternamelist
    def set_parameternamelist(self, parameternamelist): self.parameternamelist = parameternamelist
    def add_parameternamelist(self, value): self.parameternamelist.append(value)
    def insert_parameternamelist(self, index, value): self.parameternamelist[index] = value
    def get_parameterdescription(self): return self.parameterdescription
    def set_parameterdescription(self, parameterdescription): self.parameterdescription = parameterdescription
    def export(self, outfile, level, namespace_='', name_='docParamListItem', namespacedef_=''):
        showIndent(outfile, level)
        outfile.write('<%s%s %s' % (namespace_, name_, namespacedef_, ))
        self.exportAttributes(outfile, level, namespace_, name_='docParamListItem')
        if self.hasContent_():
            outfile.write('>\n')
            self.exportChildren(outfile, level + 1, namespace_, name_)
            showIndent(outfile, level)
            outfile.write('</%s%s>\n' % (namespace_, name_))
        else:
            outfile.write(' />\n')
    def exportAttributes(self, outfile, level, namespace_='', name_='docParamListItem'):
        pass
    def exportChildren(self, outfile, level, namespace_='', name_='docParamListItem'):
        for parameternamelist_ in self.parameternamelist:
            parameternamelist_.export(outfile, level, namespace_, name_='parameternamelist')
        if self.parameterdescription:
            self.parameterdescription.export(outfile, level, namespace_, name_='parameterdescription', )
    def hasContent_(self):
        if (
            self.parameternamelist is not None or
            self.parameterdescription is not None
            ):
            return True
        else:
            return False
    def exportLiteral(self, outfile, level, name_='docParamListItem'):
        level += 1
        self.exportLiteralAttributes(outfile, level, name_)
        if self.hasContent_():
            self.exportLiteralChildren(outfile, level, name_)
    def exportLiteralAttributes(self, outfile, level, name_):
        pass
    def exportLiteralChildren(self, outfile, level, name_):
        showIndent(outfile, level)
        outfile.write('parameternamelist=[\n')
        level += 1
        for parameternamelist in self.parameternamelist:
            showIndent(outfile, level)
            outfile.write('model_.parameternamelist(\n')
            parameternamelist.exportLiteral(outfile, level, name_='parameternamelist')
            showIndent(outfile, level)
            outfile.write('),\n')
        level -= 1
        showIndent(outfile, level)
        outfile.write('],\n')
        if self.parameterdescription:
            showIndent(outfile, level)
            outfile.write('parameterdescription=model_.descriptionType(\n')
            self.parameterdescription.exportLiteral(outfile, level, name_='parameterdescription')
            showIndent(outfile, level)
            outfile.write('),\n')
    def build(self, node_):
        attrs = node_.attributes
        self.buildAttributes(attrs)
        for child_ in node_.childNodes:
            nodeName_ = child_.nodeName.split(':')[-1]
            self.buildChildren(child_, nodeName_)
    def buildAttributes(self, attrs):
        pass
    def buildChildren(self, child_, nodeName_):
        if child_.nodeType == Node.ELEMENT_NODE and \
            nodeName_ == 'parameternamelist':
            obj_ = docParamNameList.factory()
            obj_.build(child_)
            self.parameternamelist.append(obj_)
        elif child_.nodeType == Node.ELEMENT_NODE and \
            nodeName_ == 'parameterdescription':
            obj_ = descriptionType.factory()
            obj_.build(child_)
            self.set_parameterdescription(obj_)
# end class docParamListItem


class docParamNameList(GeneratedsSuper):
    subclass = None
    superclass = None
    def __init__(self, parametername=None):
        if parametername is None:
            self.parametername = []
        else:
            self.parametername = parametername
    def factory(*args_, **kwargs_):
        if docParamNameList.subclass:
            return docParamNameList.subclass(*args_, **kwargs_)
        else:
            return docParamNameList(*args_, **kwargs_)
    factory = staticmethod(factory)
    def get_parametername(self): return self.parametername
    def set_parametername(self, parametername): self.parametername = parametername
    def add_parametername(self, value): self.parametername.append(value)
    def insert_parametername(self, index, value): self.parametername[index] = value
    def export(self, outfile, level, namespace_='', name_='docParamNameList', namespacedef_=''):
        showIndent(outfile, level)
        outfile.write('<%s%s %s' % (namespace_, name_, namespacedef_, ))
        self.exportAttributes(outfile, level, namespace_, name_='docParamNameList')
        if self.hasContent_():
            outfile.write('>\n')
            self.exportChildren(outfile, level + 1, namespace_, name_)
            showIndent(outfile, level)
            outfile.write('</%s%s>\n' % (namespace_, name_))
        else:
            outfile.write(' />\n')
    def exportAttributes(self, outfile, level, namespace_='', name_='docParamNameList'):
        pass
    def exportChildren(self, outfile, level, namespace_='', name_='docParamNameList'):
        for parametername_ in self.parametername:
            parametername_.export(outfile, level, namespace_, name_='parametername')
    def hasContent_(self):
        if (
            self.parametername is not None
            ):
            return True
        else:
            return False
    def exportLiteral(self, outfile, level, name_='docParamNameList'):
        level += 1
        self.exportLiteralAttributes(outfile, level, name_)
        if self.hasContent_():
            self.exportLiteralChildren(outfile, level, name_)
    def exportLiteralAttributes(self, outfile, level, name_):
        pass
    def exportLiteralChildren(self, outfile, level, name_):
        showIndent(outfile, level)
        outfile.write('parametername=[\n')
        level += 1
        for parametername in self.parametername:
            showIndent(outfile, level)
            outfile.write('model_.parametername(\n')
            parametername.exportLiteral(outfile, level, name_='parametername')
            showIndent(outfile, level)
            outfile.write('),\n')
        level -= 1
        showIndent(outfile, level)
        outfile.write('],\n')
    def build(self, node_):
        attrs = node_.attributes
        self.buildAttributes(attrs)
        for child_ in node_.childNodes:
            nodeName_ = child_.nodeName.split(':')[-1]
            self.buildChildren(child_, nodeName_)
    def buildAttributes(self, attrs):
        pass
    def buildChildren(self, child_, nodeName_):
        if child_.nodeType == Node.ELEMENT_NODE and \
            nodeName_ == 'parametername':
            obj_ = docParamName.factory()
            obj_.build(child_)
            self.parametername.append(obj_)
# end class docParamNameList


class docParamName(GeneratedsSuper):
    subclass = None
    superclass = None
    def __init__(self, direction=None, ref=None, mixedclass_=None, content_=None):
        self.direction = direction
        if mixedclass_ is None:
            self.mixedclass_ = MixedContainer
        else:
            self.mixedclass_ = mixedclass_
        if content_ is None:
            self.content_ = []
        else:
            self.content_ = content_
    def factory(*args_, **kwargs_):
        if docParamName.subclass:
            return docParamName.subclass(*args_, **kwargs_)
        else:
            return docParamName(*args_, **kwargs_)
    factory = staticmethod(factory)
    def get_ref(self): return self.ref
    def set_ref(self, ref): self.ref = ref
    def get_direction(self): return self.direction
    def set_direction(self, direction): self.direction = direction
    def export(self, outfile, level, namespace_='', name_='docParamName', namespacedef_=''):
        showIndent(outfile, level)
        outfile.write('<%s%s %s' % (namespace_, name_, namespacedef_, ))
        self.exportAttributes(outfile, level, namespace_, name_='docParamName')
        outfile.write('>')
        self.exportChildren(outfile, level + 1, namespace_, name_)
        outfile.write('</%s%s>\n' % (namespace_, name_))
    def exportAttributes(self, outfile, level, namespace_='', name_='docParamName'):
        if self.direction is not None:
            outfile.write(' direction=%s' % (quote_attrib(self.direction), ))
    def exportChildren(self, outfile, level, namespace_='', name_='docParamName'):
        for item_ in self.content_:
            item_.export(outfile, level, item_.name, namespace_)
    def hasContent_(self):
        if (
            self.ref is not None
            ):
            return True
        else:
            return False
    def exportLiteral(self, outfile, level, name_='docParamName'):
        level += 1
        self.exportLiteralAttributes(outfile, level, name_)
        if self.hasContent_():
            self.exportLiteralChildren(outfile, level, name_)
    def exportLiteralAttributes(self, outfile, level, name_):
        if self.direction is not None:
            showIndent(outfile, level)
            outfile.write('direction = "%s",\n' % (self.direction,))
    def exportLiteralChildren(self, outfile, level, name_):
        showIndent(outfile, level)
        outfile.write('content_ = [\n')
        for item_ in self.content_:
            item_.exportLiteral(outfile, level, name_)
        showIndent(outfile, level)
        outfile.write('],\n')
    def build(self, node_):
        attrs = node_.attributes
        self.buildAttributes(attrs)
        for child_ in node_.childNodes:
            nodeName_ = child_.nodeName.split(':')[-1]
            self.buildChildren(child_, nodeName_)
    def buildAttributes(self, attrs):
        if attrs.get('direction'):
            self.direction = attrs.get('direction').value
    def buildChildren(self, child_, nodeName_):
        if child_.nodeType == Node.ELEMENT_NODE and \
            nodeName_ == 'ref':
            childobj_ = docRefTextType.factory()
            childobj_.build(child_)
            obj_ = self.mixedclass_(MixedContainer.CategoryComplex,
                MixedContainer.TypeNone, 'ref', childobj_)
            self.content_.append(obj_)
        elif child_.nodeType == Node.TEXT_NODE:
            obj_ = self.mixedclass_(MixedContainer.CategoryText,
                MixedContainer.TypeNone, '', child_.nodeValue)
            self.content_.append(obj_)
# end class docParamName


class docXRefSectType(GeneratedsSuper):
    subclass = None
    superclass = None
    def __init__(self, id=None, xreftitle=None, xrefdescription=None):
        self.id = id
        if xreftitle is None:
            self.xreftitle = []
        else:
            self.xreftitle = xreftitle
        self.xrefdescription = xrefdescription
    def factory(*args_, **kwargs_):
        if docXRefSectType.subclass:
            return docXRefSectType.subclass(*args_, **kwargs_)
        else:
            return docXRefSectType(*args_, **kwargs_)
    factory = staticmethod(factory)
    def get_xreftitle(self): return self.xreftitle
    def set_xreftitle(self, xreftitle): self.xreftitle = xreftitle
    def add_xreftitle(self, value): self.xreftitle.append(value)
    def insert_xreftitle(self, index, value): self.xreftitle[index] = value
    def get_xrefdescription(self): return self.xrefdescription
    def set_xrefdescription(self, xrefdescription): self.xrefdescription = xrefdescription
    def get_id(self): return self.id
    def set_id(self, id): self.id = id
    def export(self, outfile, level, namespace_='', name_='docXRefSectType', namespacedef_=''):
        showIndent(outfile, level)
        outfile.write('<%s%s %s' % (namespace_, name_, namespacedef_, ))
        self.exportAttributes(outfile, level, namespace_, name_='docXRefSectType')
        if self.hasContent_():
            outfile.write('>\n')
            self.exportChildren(outfile, level + 1, namespace_, name_)
            showIndent(outfile, level)
            outfile.write('</%s%s>\n' % (namespace_, name_))
        else:
            outfile.write(' />\n')
    def exportAttributes(self, outfile, level, namespace_='', name_='docXRefSectType'):
        if self.id is not None:
            outfile.write(' id=%s' % (self.format_string(quote_attrib(self.id).encode(ExternalEncoding), input_name='id'), ))
    def exportChildren(self, outfile, level, namespace_='', name_='docXRefSectType'):
        for xreftitle_ in self.xreftitle:
            showIndent(outfile, level)
            outfile.write('<%sxreftitle>%s</%sxreftitle>\n' % (namespace_, self.format_string(quote_xml(xreftitle_).encode(ExternalEncoding), input_name='xreftitle'), namespace_))
        if self.xrefdescription:
            self.xrefdescription.export(outfile, level, namespace_, name_='xrefdescription', )
    def hasContent_(self):
        if (
            self.xreftitle is not None or
            self.xrefdescription is not None
            ):
            return True
        else:
            return False
    def exportLiteral(self, outfile, level, name_='docXRefSectType'):
        level += 1
        self.exportLiteralAttributes(outfile, level, name_)
        if self.hasContent_():
            self.exportLiteralChildren(outfile, level, name_)
    def exportLiteralAttributes(self, outfile, level, name_):
        if self.id is not None:
            showIndent(outfile, level)
            outfile.write('id = %s,\n' % (self.id,))
    def exportLiteralChildren(self, outfile, level, name_):
        showIndent(outfile, level)
        outfile.write('xreftitle=[\n')
        level += 1
        for xreftitle in self.xreftitle:
            showIndent(outfile, level)
            outfile.write('%s,\n' % quote_python(xreftitle).encode(ExternalEncoding))
        level -= 1
        showIndent(outfile, level)
        outfile.write('],\n')
        if self.xrefdescription:
            showIndent(outfile, level)
            outfile.write('xrefdescription=model_.descriptionType(\n')
            self.xrefdescription.exportLiteral(outfile, level, name_='xrefdescription')
            showIndent(outfile, level)
            outfile.write('),\n')
    def build(self, node_):
        attrs = node_.attributes
        self.buildAttributes(attrs)
        for child_ in node_.childNodes:
            nodeName_ = child_.nodeName.split(':')[-1]
            self.buildChildren(child_, nodeName_)
    def buildAttributes(self, attrs):
        if attrs.get('id'):
            self.id = attrs.get('id').value
    def buildChildren(self, child_, nodeName_):
        if child_.nodeType == Node.ELEMENT_NODE and \
            nodeName_ == 'xreftitle':
            xreftitle_ = ''
            for text__content_ in child_.childNodes:
                xreftitle_ += text__content_.nodeValue
            self.xreftitle.append(xreftitle_)
        elif child_.nodeType == Node.ELEMENT_NODE and \
            nodeName_ == 'xrefdescription':
            obj_ = descriptionType.factory()
            obj_.build(child_)
            self.set_xrefdescription(obj_)
# end class docXRefSectType


class docCopyType(GeneratedsSuper):
    subclass = None
    superclass = None
    def __init__(self, link=None, para=None, sect1=None, internal=None):
        self.link = link
        if para is None:
            self.para = []
        else:
            self.para = para
        if sect1 is None:
            self.sect1 = []
        else:
            self.sect1 = sect1
        self.internal = internal
    def factory(*args_, **kwargs_):
        if docCopyType.subclass:
            return docCopyType.subclass(*args_, **kwargs_)
        else:
            return docCopyType(*args_, **kwargs_)
    factory = staticmethod(factory)
    def get_para(self): return self.para
    def set_para(self, para): self.para = para
    def add_para(self, value): self.para.append(value)
    def insert_para(self, index, value): self.para[index] = value
    def get_sect1(self): return self.sect1
    def set_sect1(self, sect1): self.sect1 = sect1
    def add_sect1(self, value): self.sect1.append(value)
    def insert_sect1(self, index, value): self.sect1[index] = value
    def get_internal(self): return self.internal
    def set_internal(self, internal): self.internal = internal
    def get_link(self): return self.link
    def set_link(self, link): self.link = link
    def export(self, outfile, level, namespace_='', name_='docCopyType', namespacedef_=''):
        showIndent(outfile, level)
        outfile.write('<%s%s %s' % (namespace_, name_, namespacedef_, ))
        self.exportAttributes(outfile, level, namespace_, name_='docCopyType')
        if self.hasContent_():
            outfile.write('>\n')
            self.exportChildren(outfile, level + 1, namespace_, name_)
            showIndent(outfile, level)
            outfile.write('</%s%s>\n' % (namespace_, name_))
        else:
            outfile.write(' />\n')
    def exportAttributes(self, outfile, level, namespace_='', name_='docCopyType'):
        if self.link is not None:
            outfile.write(' link=%s' % (self.format_string(quote_attrib(self.link).encode(ExternalEncoding), input_name='link'), ))
    def exportChildren(self, outfile, level, namespace_='', name_='docCopyType'):
        for para_ in self.para:
            para_.export(outfile, level, namespace_, name_='para')
        for sect1_ in self.sect1:
            sect1_.export(outfile, level, namespace_, name_='sect1')
        if self.internal:
            self.internal.export(outfile, level, namespace_, name_='internal')
    def hasContent_(self):
        if (
            self.para is not None or
            self.sect1 is not None or
            self.internal is not None
            ):
            return True
        else:
            return False
    def exportLiteral(self, outfile, level, name_='docCopyType'):
        level += 1
        self.exportLiteralAttributes(outfile, level, name_)
        if self.hasContent_():
            self.exportLiteralChildren(outfile, level, name_)
    def exportLiteralAttributes(self, outfile, level, name_):
        if self.link is not None:
            showIndent(outfile, level)
            outfile.write('link = %s,\n' % (self.link,))
    def exportLiteralChildren(self, outfile, level, name_):
        showIndent(outfile, level)
        outfile.write('para=[\n')
        level += 1
        for para in self.para:
            showIndent(outfile, level)
            outfile.write('model_.para(\n')
            para.exportLiteral(outfile, level, name_='para')
            showIndent(outfile, level)
            outfile.write('),\n')
        level -= 1
        showIndent(outfile, level)
        outfile.write('],\n')
        showIndent(outfile, level)
        outfile.write('sect1=[\n')
        level += 1
        for sect1 in self.sect1:
            showIndent(outfile, level)
            outfile.write('model_.sect1(\n')
            sect1.exportLiteral(outfile, level, name_='sect1')
            showIndent(outfile, level)
            outfile.write('),\n')
        level -= 1
        showIndent(outfile, level)
        outfile.write('],\n')
        if self.internal:
            showIndent(outfile, level)
            outfile.write('internal=model_.docInternalType(\n')
            self.internal.exportLiteral(outfile, level, name_='internal')
            showIndent(outfile, level)
            outfile.write('),\n')
    def build(self, node_):
        attrs = node_.attributes
        self.buildAttributes(attrs)
        for child_ in node_.childNodes:
            nodeName_ = child_.nodeName.split(':')[-1]
            self.buildChildren(child_, nodeName_)
    def buildAttributes(self, attrs):
        if attrs.get('link'):
            self.link = attrs.get('link').value
    def buildChildren(self, child_, nodeName_):
        if child_.nodeType == Node.ELEMENT_NODE and \
            nodeName_ == 'para':
            obj_ = docParaType.factory()
            obj_.build(child_)
            self.para.append(obj_)
        elif child_.nodeType == Node.ELEMENT_NODE and \
            nodeName_ == 'sect1':
            obj_ = docSect1Type.factory()
            obj_.build(child_)
            self.sect1.append(obj_)
        elif child_.nodeType == Node.ELEMENT_NODE and \
            nodeName_ == 'internal':
            obj_ = docInternalType.factory()
            obj_.build(child_)
            self.set_internal(obj_)
# end class docCopyType


class docCharType(GeneratedsSuper):
    subclass = None
    superclass = None
    def __init__(self, char=None, valueOf_=''):
        self.char = char
        self.valueOf_ = valueOf_
    def factory(*args_, **kwargs_):
        if docCharType.subclass:
            return docCharType.subclass(*args_, **kwargs_)
        else:
            return docCharType(*args_, **kwargs_)
    factory = staticmethod(factory)
    def get_char(self): return self.char
    def set_char(self, char): self.char = char
    def getValueOf_(self): return self.valueOf_
    def setValueOf_(self, valueOf_): self.valueOf_ = valueOf_
    def export(self, outfile, level, namespace_='', name_='docCharType', namespacedef_=''):
        showIndent(outfile, level)
        outfile.write('<%s%s %s' % (namespace_, name_, namespacedef_, ))
        self.exportAttributes(outfile, level, namespace_, name_='docCharType')
        if self.hasContent_():
            outfile.write('>\n')
            self.exportChildren(outfile, level + 1, namespace_, name_)
            showIndent(outfile, level)
            outfile.write('</%s%s>\n' % (namespace_, name_))
        else:
            outfile.write(' />\n')
    def exportAttributes(self, outfile, level, namespace_='', name_='docCharType'):
        if self.char is not None:
            outfile.write(' char=%s' % (quote_attrib(self.char), ))
    def exportChildren(self, outfile, level, namespace_='', name_='docCharType'):
        if self.valueOf_.find('![CDATA')>-1:
            value=quote_xml('%s' % self.valueOf_)
            value=value.replace('![CDATA','<![CDATA')
            value=value.replace(']]',']]>')
            outfile.write(value)
        else:
            outfile.write(quote_xml('%s' % self.valueOf_))
    def hasContent_(self):
        if (
            self.valueOf_ is not None
            ):
            return True
        else:
            return False
    def exportLiteral(self, outfile, level, name_='docCharType'):
        level += 1
        self.exportLiteralAttributes(outfile, level, name_)
        if self.hasContent_():
            self.exportLiteralChildren(outfile, level, name_)
    def exportLiteralAttributes(self, outfile, level, name_):
        if self.char is not None:
            showIndent(outfile, level)
            outfile.write('char = "%s",\n' % (self.char,))
    def exportLiteralChildren(self, outfile, level, name_):
        showIndent(outfile, level)
        outfile.write('valueOf_ = "%s",\n' % (self.valueOf_,))
    def build(self, node_):
        attrs = node_.attributes
        self.buildAttributes(attrs)
        self.valueOf_ = ''
        for child_ in node_.childNodes:
            nodeName_ = child_.nodeName.split(':')[-1]
            self.buildChildren(child_, nodeName_)
    def buildAttributes(self, attrs):
        if attrs.get('char'):
            self.char = attrs.get('char').value
    def buildChildren(self, child_, nodeName_):
        if child_.nodeType == Node.TEXT_NODE:
            self.valueOf_ += child_.nodeValue
        elif child_.nodeType == Node.CDATA_SECTION_NODE:
            self.valueOf_ += '![CDATA['+child_.nodeValue+']]'
# end class docCharType


class docEmptyType(GeneratedsSuper):
    subclass = None
    superclass = None
    def __init__(self, valueOf_=''):
        self.valueOf_ = valueOf_
    def factory(*args_, **kwargs_):
        if docEmptyType.subclass:
            return docEmptyType.subclass(*args_, **kwargs_)
        else:
            return docEmptyType(*args_, **kwargs_)
    factory = staticmethod(factory)
    def getValueOf_(self): return self.valueOf_
    def setValueOf_(self, valueOf_): self.valueOf_ = valueOf_
    def export(self, outfile, level, namespace_='', name_='docEmptyType', namespacedef_=''):
        showIndent(outfile, level)
        outfile.write('<%s%s %s' % (namespace_, name_, namespacedef_, ))
        self.exportAttributes(outfile, level, namespace_, name_='docEmptyType')
        if self.hasContent_():
            outfile.write('>\n')
            self.exportChildren(outfile, level + 1, namespace_, name_)
            showIndent(outfile, level)
            outfile.write('</%s%s>\n' % (namespace_, name_))
        else:
            outfile.write(' />\n')
    def exportAttributes(self, outfile, level, namespace_='', name_='docEmptyType'):
        pass
    def exportChildren(self, outfile, level, namespace_='', name_='docEmptyType'):
        if self.valueOf_.find('![CDATA')>-1:
            value=quote_xml('%s' % self.valueOf_)
            value=value.replace('![CDATA','<![CDATA')
            value=value.replace(']]',']]>')
            outfile.write(value)
        else:
            outfile.write(quote_xml('%s' % self.valueOf_))
    def hasContent_(self):
        if (
            self.valueOf_ is not None
            ):
            return True
        else:
            return False
    def exportLiteral(self, outfile, level, name_='docEmptyType'):
        level += 1
        self.exportLiteralAttributes(outfile, level, name_)
        if self.hasContent_():
            self.exportLiteralChildren(outfile, level, name_)
    def exportLiteralAttributes(self, outfile, level, name_):
        pass
    def exportLiteralChildren(self, outfile, level, name_):
        showIndent(outfile, level)
        outfile.write('valueOf_ = "%s",\n' % (self.valueOf_,))
    def build(self, node_):
        attrs = node_.attributes
        self.buildAttributes(attrs)
        self.valueOf_ = ''
        for child_ in node_.childNodes:
            nodeName_ = child_.nodeName.split(':')[-1]
            self.buildChildren(child_, nodeName_)
    def buildAttributes(self, attrs):
        pass
    def buildChildren(self, child_, nodeName_):
        if child_.nodeType == Node.TEXT_NODE:
            self.valueOf_ += child_.nodeValue
        elif child_.nodeType == Node.CDATA_SECTION_NODE:
            self.valueOf_ += '![CDATA['+child_.nodeValue+']]'
# end class docEmptyType


USAGE_TEXT = """
Usage: python <Parser>.py [ -s ] <in_xml_file>
Options:
    -s        Use the SAX parser, not the minidom parser.
"""

def usage():
    print USAGE_TEXT
    sys.exit(1)


def parse(inFileName):
    doc = minidom.parse(inFileName)
    rootNode = doc.documentElement
    rootObj = DoxygenType.factory()
    rootObj.build(rootNode)
    # Enable Python to collect the space used by the DOM.
    doc = None
    sys.stdout.write('<?xml version="1.0" ?>\n')
    rootObj.export(sys.stdout, 0, name_="doxygen",
        namespacedef_='')
    return rootObj


def parseString(inString):
    doc = minidom.parseString(inString)
    rootNode = doc.documentElement
    rootObj = DoxygenType.factory()
    rootObj.build(rootNode)
    # Enable Python to collect the space used by the DOM.
    doc = None
    sys.stdout.write('<?xml version="1.0" ?>\n')
    rootObj.export(sys.stdout, 0, name_="doxygen",
        namespacedef_='')
    return rootObj


def parseLiteral(inFileName):
    doc = minidom.parse(inFileName)
    rootNode = doc.documentElement
    rootObj = DoxygenType.factory()
    rootObj.build(rootNode)
    # Enable Python to collect the space used by the DOM.
    doc = None
    sys.stdout.write('from compound import *\n\n')
    sys.stdout.write('rootObj = doxygen(\n')
    rootObj.exportLiteral(sys.stdout, 0, name_="doxygen")
    sys.stdout.write(')\n')
    return rootObj


def main():
    args = sys.argv[1:]
    if len(args) == 1:
        parse(args[0])
    else:
        usage()


if __name__ == '__main__':
    main()
    #import pdb
    #pdb.run('main()')


########NEW FILE########
__FILENAME__ = index
#!/usr/bin/env python

"""
Generated Mon Feb  9 19:08:05 2009 by generateDS.py.
"""

from xml.dom import minidom

import os
import sys
import compound

import indexsuper as supermod

class DoxygenTypeSub(supermod.DoxygenType):
    def __init__(self, version=None, compound=None):
        supermod.DoxygenType.__init__(self, version, compound)

    def find_compounds_and_members(self, details):
        """
        Returns a list of all compounds and their members which match details
        """

        results = []
        for compound in self.compound:
            members = compound.find_members(details)
            if members:
                results.append([compound, members])
            else:
                if details.match(compound):
                    results.append([compound, []])

        return results

supermod.DoxygenType.subclass = DoxygenTypeSub
# end class DoxygenTypeSub


class CompoundTypeSub(supermod.CompoundType):
    def __init__(self, kind=None, refid=None, name='', member=None):
        supermod.CompoundType.__init__(self, kind, refid, name, member)

    def find_members(self, details):
        """
        Returns a list of all members which match details
        """

        results = []

        for member in self.member:
            if details.match(member):
                results.append(member)

        return results

supermod.CompoundType.subclass = CompoundTypeSub
# end class CompoundTypeSub


class MemberTypeSub(supermod.MemberType):

    def __init__(self, kind=None, refid=None, name=''):
        supermod.MemberType.__init__(self, kind, refid, name)

supermod.MemberType.subclass = MemberTypeSub
# end class MemberTypeSub


def parse(inFilename):

    doc = minidom.parse(inFilename)
    rootNode = doc.documentElement
    rootObj = supermod.DoxygenType.factory()
    rootObj.build(rootNode)

    return rootObj


########NEW FILE########
__FILENAME__ = indexsuper
#!/usr/bin/env python

#
# Generated Thu Jun 11 18:43:54 2009 by generateDS.py.
#

import sys
import getopt
from string import lower as str_lower
from xml.dom import minidom
from xml.dom import Node

#
# User methods
#
# Calls to the methods in these classes are generated by generateDS.py.
# You can replace these methods by re-implementing the following class
#   in a module named generatedssuper.py.

try:
    from generatedssuper import GeneratedsSuper
except ImportError, exp:

    class GeneratedsSuper:
        def format_string(self, input_data, input_name=''):
            return input_data
        def format_integer(self, input_data, input_name=''):
            return '%d' % input_data
        def format_float(self, input_data, input_name=''):
            return '%f' % input_data
        def format_double(self, input_data, input_name=''):
            return '%e' % input_data
        def format_boolean(self, input_data, input_name=''):
            return '%s' % input_data


#
# If you have installed IPython you can uncomment and use the following.
# IPython is available from http://ipython.scipy.org/.
#

## from IPython.Shell import IPShellEmbed
## args = ''
## ipshell = IPShellEmbed(args,
##     banner = 'Dropping into IPython',
##     exit_msg = 'Leaving Interpreter, back to program.')

# Then use the following line where and when you want to drop into the
# IPython shell:
#    ipshell('<some message> -- Entering ipshell.\nHit Ctrl-D to exit')

#
# Globals
#

ExternalEncoding = 'ascii'

#
# Support/utility functions.
#

def showIndent(outfile, level):
    for idx in range(level):
        outfile.write('    ')

def quote_xml(inStr):
    s1 = (isinstance(inStr, basestring) and inStr or
          '%s' % inStr)
    s1 = s1.replace('&', '&amp;')
    s1 = s1.replace('<', '&lt;')
    s1 = s1.replace('>', '&gt;')
    return s1

def quote_attrib(inStr):
    s1 = (isinstance(inStr, basestring) and inStr or
          '%s' % inStr)
    s1 = s1.replace('&', '&amp;')
    s1 = s1.replace('<', '&lt;')
    s1 = s1.replace('>', '&gt;')
    if '"' in s1:
        if "'" in s1:
            s1 = '"%s"' % s1.replace('"', "&quot;")
        else:
            s1 = "'%s'" % s1
    else:
        s1 = '"%s"' % s1
    return s1

def quote_python(inStr):
    s1 = inStr
    if s1.find("'") == -1:
        if s1.find('\n') == -1:
            return "'%s'" % s1
        else:
            return "'''%s'''" % s1
    else:
        if s1.find('"') != -1:
            s1 = s1.replace('"', '\\"')
        if s1.find('\n') == -1:
            return '"%s"' % s1
        else:
            return '"""%s"""' % s1


class MixedContainer:
    # Constants for category:
    CategoryNone = 0
    CategoryText = 1
    CategorySimple = 2
    CategoryComplex = 3
    # Constants for content_type:
    TypeNone = 0
    TypeText = 1
    TypeString = 2
    TypeInteger = 3
    TypeFloat = 4
    TypeDecimal = 5
    TypeDouble = 6
    TypeBoolean = 7
    def __init__(self, category, content_type, name, value):
        self.category = category
        self.content_type = content_type
        self.name = name
        self.value = value
    def getCategory(self):
        return self.category
    def getContenttype(self, content_type):
        return self.content_type
    def getValue(self):
        return self.value
    def getName(self):
        return self.name
    def export(self, outfile, level, name, namespace):
        if self.category == MixedContainer.CategoryText:
            outfile.write(self.value)
        elif self.category == MixedContainer.CategorySimple:
            self.exportSimple(outfile, level, name)
        else:    # category == MixedContainer.CategoryComplex
            self.value.export(outfile, level, namespace,name)
    def exportSimple(self, outfile, level, name):
        if self.content_type == MixedContainer.TypeString:
            outfile.write('<%s>%s</%s>' % (self.name, self.value, self.name))
        elif self.content_type == MixedContainer.TypeInteger or \
                self.content_type == MixedContainer.TypeBoolean:
            outfile.write('<%s>%d</%s>' % (self.name, self.value, self.name))
        elif self.content_type == MixedContainer.TypeFloat or \
                self.content_type == MixedContainer.TypeDecimal:
            outfile.write('<%s>%f</%s>' % (self.name, self.value, self.name))
        elif self.content_type == MixedContainer.TypeDouble:
            outfile.write('<%s>%g</%s>' % (self.name, self.value, self.name))
    def exportLiteral(self, outfile, level, name):
        if self.category == MixedContainer.CategoryText:
            showIndent(outfile, level)
            outfile.write('MixedContainer(%d, %d, "%s", "%s"),\n' % \
                (self.category, self.content_type, self.name, self.value))
        elif self.category == MixedContainer.CategorySimple:
            showIndent(outfile, level)
            outfile.write('MixedContainer(%d, %d, "%s", "%s"),\n' % \
                (self.category, self.content_type, self.name, self.value))
        else:    # category == MixedContainer.CategoryComplex
            showIndent(outfile, level)
            outfile.write('MixedContainer(%d, %d, "%s",\n' % \
                (self.category, self.content_type, self.name,))
            self.value.exportLiteral(outfile, level + 1)
            showIndent(outfile, level)
            outfile.write(')\n')


class _MemberSpec(object):
    def __init__(self, name='', data_type='', container=0):
        self.name = name
        self.data_type = data_type
        self.container = container
    def set_name(self, name): self.name = name
    def get_name(self): return self.name
    def set_data_type(self, data_type): self.data_type = data_type
    def get_data_type(self): return self.data_type
    def set_container(self, container): self.container = container
    def get_container(self): return self.container


#
# Data representation classes.
#

class DoxygenType(GeneratedsSuper):
    subclass = None
    superclass = None
    def __init__(self, version=None, compound=None):
        self.version = version
        if compound is None:
            self.compound = []
        else:
            self.compound = compound
    def factory(*args_, **kwargs_):
        if DoxygenType.subclass:
            return DoxygenType.subclass(*args_, **kwargs_)
        else:
            return DoxygenType(*args_, **kwargs_)
    factory = staticmethod(factory)
    def get_compound(self): return self.compound
    def set_compound(self, compound): self.compound = compound
    def add_compound(self, value): self.compound.append(value)
    def insert_compound(self, index, value): self.compound[index] = value
    def get_version(self): return self.version
    def set_version(self, version): self.version = version
    def export(self, outfile, level, namespace_='', name_='DoxygenType', namespacedef_=''):
        showIndent(outfile, level)
        outfile.write('<%s%s %s' % (namespace_, name_, namespacedef_, ))
        self.exportAttributes(outfile, level, namespace_, name_='DoxygenType')
        if self.hasContent_():
            outfile.write('>\n')
            self.exportChildren(outfile, level + 1, namespace_, name_)
            showIndent(outfile, level)
            outfile.write('</%s%s>\n' % (namespace_, name_))
        else:
            outfile.write(' />\n')
    def exportAttributes(self, outfile, level, namespace_='', name_='DoxygenType'):
        outfile.write(' version=%s' % (self.format_string(quote_attrib(self.version).encode(ExternalEncoding), input_name='version'), ))
    def exportChildren(self, outfile, level, namespace_='', name_='DoxygenType'):
        for compound_ in self.compound:
            compound_.export(outfile, level, namespace_, name_='compound')
    def hasContent_(self):
        if (
            self.compound is not None
            ):
            return True
        else:
            return False
    def exportLiteral(self, outfile, level, name_='DoxygenType'):
        level += 1
        self.exportLiteralAttributes(outfile, level, name_)
        if self.hasContent_():
            self.exportLiteralChildren(outfile, level, name_)
    def exportLiteralAttributes(self, outfile, level, name_):
        if self.version is not None:
            showIndent(outfile, level)
            outfile.write('version = %s,\n' % (self.version,))
    def exportLiteralChildren(self, outfile, level, name_):
        showIndent(outfile, level)
        outfile.write('compound=[\n')
        level += 1
        for compound in self.compound:
            showIndent(outfile, level)
            outfile.write('model_.compound(\n')
            compound.exportLiteral(outfile, level, name_='compound')
            showIndent(outfile, level)
            outfile.write('),\n')
        level -= 1
        showIndent(outfile, level)
        outfile.write('],\n')
    def build(self, node_):
        attrs = node_.attributes
        self.buildAttributes(attrs)
        for child_ in node_.childNodes:
            nodeName_ = child_.nodeName.split(':')[-1]
            self.buildChildren(child_, nodeName_)
    def buildAttributes(self, attrs):
        if attrs.get('version'):
            self.version = attrs.get('version').value
    def buildChildren(self, child_, nodeName_):
        if child_.nodeType == Node.ELEMENT_NODE and \
            nodeName_ == 'compound':
            obj_ = CompoundType.factory()
            obj_.build(child_)
            self.compound.append(obj_)
# end class DoxygenType


class CompoundType(GeneratedsSuper):
    subclass = None
    superclass = None
    def __init__(self, kind=None, refid=None, name=None, member=None):
        self.kind = kind
        self.refid = refid
        self.name = name
        if member is None:
            self.member = []
        else:
            self.member = member
    def factory(*args_, **kwargs_):
        if CompoundType.subclass:
            return CompoundType.subclass(*args_, **kwargs_)
        else:
            return CompoundType(*args_, **kwargs_)
    factory = staticmethod(factory)
    def get_name(self): return self.name
    def set_name(self, name): self.name = name
    def get_member(self): return self.member
    def set_member(self, member): self.member = member
    def add_member(self, value): self.member.append(value)
    def insert_member(self, index, value): self.member[index] = value
    def get_kind(self): return self.kind
    def set_kind(self, kind): self.kind = kind
    def get_refid(self): return self.refid
    def set_refid(self, refid): self.refid = refid
    def export(self, outfile, level, namespace_='', name_='CompoundType', namespacedef_=''):
        showIndent(outfile, level)
        outfile.write('<%s%s %s' % (namespace_, name_, namespacedef_, ))
        self.exportAttributes(outfile, level, namespace_, name_='CompoundType')
        if self.hasContent_():
            outfile.write('>\n')
            self.exportChildren(outfile, level + 1, namespace_, name_)
            showIndent(outfile, level)
            outfile.write('</%s%s>\n' % (namespace_, name_))
        else:
            outfile.write(' />\n')
    def exportAttributes(self, outfile, level, namespace_='', name_='CompoundType'):
        outfile.write(' kind=%s' % (quote_attrib(self.kind), ))
        outfile.write(' refid=%s' % (self.format_string(quote_attrib(self.refid).encode(ExternalEncoding), input_name='refid'), ))
    def exportChildren(self, outfile, level, namespace_='', name_='CompoundType'):
        if self.name is not None:
            showIndent(outfile, level)
            outfile.write('<%sname>%s</%sname>\n' % (namespace_, self.format_string(quote_xml(self.name).encode(ExternalEncoding), input_name='name'), namespace_))
        for member_ in self.member:
            member_.export(outfile, level, namespace_, name_='member')
    def hasContent_(self):
        if (
            self.name is not None or
            self.member is not None
            ):
            return True
        else:
            return False
    def exportLiteral(self, outfile, level, name_='CompoundType'):
        level += 1
        self.exportLiteralAttributes(outfile, level, name_)
        if self.hasContent_():
            self.exportLiteralChildren(outfile, level, name_)
    def exportLiteralAttributes(self, outfile, level, name_):
        if self.kind is not None:
            showIndent(outfile, level)
            outfile.write('kind = "%s",\n' % (self.kind,))
        if self.refid is not None:
            showIndent(outfile, level)
            outfile.write('refid = %s,\n' % (self.refid,))
    def exportLiteralChildren(self, outfile, level, name_):
        showIndent(outfile, level)
        outfile.write('name=%s,\n' % quote_python(self.name).encode(ExternalEncoding))
        showIndent(outfile, level)
        outfile.write('member=[\n')
        level += 1
        for member in self.member:
            showIndent(outfile, level)
            outfile.write('model_.member(\n')
            member.exportLiteral(outfile, level, name_='member')
            showIndent(outfile, level)
            outfile.write('),\n')
        level -= 1
        showIndent(outfile, level)
        outfile.write('],\n')
    def build(self, node_):
        attrs = node_.attributes
        self.buildAttributes(attrs)
        for child_ in node_.childNodes:
            nodeName_ = child_.nodeName.split(':')[-1]
            self.buildChildren(child_, nodeName_)
    def buildAttributes(self, attrs):
        if attrs.get('kind'):
            self.kind = attrs.get('kind').value
        if attrs.get('refid'):
            self.refid = attrs.get('refid').value
    def buildChildren(self, child_, nodeName_):
        if child_.nodeType == Node.ELEMENT_NODE and \
            nodeName_ == 'name':
            name_ = ''
            for text__content_ in child_.childNodes:
                name_ += text__content_.nodeValue
            self.name = name_
        elif child_.nodeType == Node.ELEMENT_NODE and \
            nodeName_ == 'member':
            obj_ = MemberType.factory()
            obj_.build(child_)
            self.member.append(obj_)
# end class CompoundType


class MemberType(GeneratedsSuper):
    subclass = None
    superclass = None
    def __init__(self, kind=None, refid=None, name=None):
        self.kind = kind
        self.refid = refid
        self.name = name
    def factory(*args_, **kwargs_):
        if MemberType.subclass:
            return MemberType.subclass(*args_, **kwargs_)
        else:
            return MemberType(*args_, **kwargs_)
    factory = staticmethod(factory)
    def get_name(self): return self.name
    def set_name(self, name): self.name = name
    def get_kind(self): return self.kind
    def set_kind(self, kind): self.kind = kind
    def get_refid(self): return self.refid
    def set_refid(self, refid): self.refid = refid
    def export(self, outfile, level, namespace_='', name_='MemberType', namespacedef_=''):
        showIndent(outfile, level)
        outfile.write('<%s%s %s' % (namespace_, name_, namespacedef_, ))
        self.exportAttributes(outfile, level, namespace_, name_='MemberType')
        if self.hasContent_():
            outfile.write('>\n')
            self.exportChildren(outfile, level + 1, namespace_, name_)
            showIndent(outfile, level)
            outfile.write('</%s%s>\n' % (namespace_, name_))
        else:
            outfile.write(' />\n')
    def exportAttributes(self, outfile, level, namespace_='', name_='MemberType'):
        outfile.write(' kind=%s' % (quote_attrib(self.kind), ))
        outfile.write(' refid=%s' % (self.format_string(quote_attrib(self.refid).encode(ExternalEncoding), input_name='refid'), ))
    def exportChildren(self, outfile, level, namespace_='', name_='MemberType'):
        if self.name is not None:
            showIndent(outfile, level)
            outfile.write('<%sname>%s</%sname>\n' % (namespace_, self.format_string(quote_xml(self.name).encode(ExternalEncoding), input_name='name'), namespace_))
    def hasContent_(self):
        if (
            self.name is not None
            ):
            return True
        else:
            return False
    def exportLiteral(self, outfile, level, name_='MemberType'):
        level += 1
        self.exportLiteralAttributes(outfile, level, name_)
        if self.hasContent_():
            self.exportLiteralChildren(outfile, level, name_)
    def exportLiteralAttributes(self, outfile, level, name_):
        if self.kind is not None:
            showIndent(outfile, level)
            outfile.write('kind = "%s",\n' % (self.kind,))
        if self.refid is not None:
            showIndent(outfile, level)
            outfile.write('refid = %s,\n' % (self.refid,))
    def exportLiteralChildren(self, outfile, level, name_):
        showIndent(outfile, level)
        outfile.write('name=%s,\n' % quote_python(self.name).encode(ExternalEncoding))
    def build(self, node_):
        attrs = node_.attributes
        self.buildAttributes(attrs)
        for child_ in node_.childNodes:
            nodeName_ = child_.nodeName.split(':')[-1]
            self.buildChildren(child_, nodeName_)
    def buildAttributes(self, attrs):
        if attrs.get('kind'):
            self.kind = attrs.get('kind').value
        if attrs.get('refid'):
            self.refid = attrs.get('refid').value
    def buildChildren(self, child_, nodeName_):
        if child_.nodeType == Node.ELEMENT_NODE and \
            nodeName_ == 'name':
            name_ = ''
            for text__content_ in child_.childNodes:
                name_ += text__content_.nodeValue
            self.name = name_
# end class MemberType


USAGE_TEXT = """
Usage: python <Parser>.py [ -s ] <in_xml_file>
Options:
    -s        Use the SAX parser, not the minidom parser.
"""

def usage():
    print USAGE_TEXT
    sys.exit(1)


def parse(inFileName):
    doc = minidom.parse(inFileName)
    rootNode = doc.documentElement
    rootObj = DoxygenType.factory()
    rootObj.build(rootNode)
    # Enable Python to collect the space used by the DOM.
    doc = None
    sys.stdout.write('<?xml version="1.0" ?>\n')
    rootObj.export(sys.stdout, 0, name_="doxygenindex",
        namespacedef_='')
    return rootObj


def parseString(inString):
    doc = minidom.parseString(inString)
    rootNode = doc.documentElement
    rootObj = DoxygenType.factory()
    rootObj.build(rootNode)
    # Enable Python to collect the space used by the DOM.
    doc = None
    sys.stdout.write('<?xml version="1.0" ?>\n')
    rootObj.export(sys.stdout, 0, name_="doxygenindex",
        namespacedef_='')
    return rootObj


def parseLiteral(inFileName):
    doc = minidom.parse(inFileName)
    rootNode = doc.documentElement
    rootObj = DoxygenType.factory()
    rootObj.build(rootNode)
    # Enable Python to collect the space used by the DOM.
    doc = None
    sys.stdout.write('from index import *\n\n')
    sys.stdout.write('rootObj = doxygenindex(\n')
    rootObj.exportLiteral(sys.stdout, 0, name_="doxygenindex")
    sys.stdout.write(')\n')
    return rootObj


def main():
    args = sys.argv[1:]
    if len(args) == 1:
        parse(args[0])
    else:
        usage()




if __name__ == '__main__':
    main()
    #import pdb
    #pdb.run('main()')


########NEW FILE########
__FILENAME__ = text
#
# Copyright 2010 Free Software Foundation, Inc.
# 
# This file is part of GNU Radio
# 
# GNU Radio is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 3, or (at your option)
# any later version.
# 
# GNU Radio is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
# 
# You should have received a copy of the GNU General Public License
# along with GNU Radio; see the file COPYING.  If not, write to
# the Free Software Foundation, Inc., 51 Franklin Street,
# Boston, MA 02110-1301, USA.
# 
"""
Utilities for extracting text from generated classes.
"""

def is_string(txt):
    if isinstance(txt, str):
        return True
    try:
        if isinstance(txt, unicode):
            return True
    except NameError:
        pass
    return False

def description(obj):
    if obj is None:
        return None
    return description_bit(obj).strip()

def description_bit(obj):
    if hasattr(obj, 'content'):
        contents = [description_bit(item) for item in obj.content]
        result = ''.join(contents)
    elif hasattr(obj, 'content_'):
        contents = [description_bit(item) for item in obj.content_]
        result = ''.join(contents)
    elif hasattr(obj, 'value'):
        result = description_bit(obj.value)
    elif is_string(obj):
        return obj
    else:
        raise StandardError('Expecting a string or something with content, content_ or value attribute')
    # If this bit is a paragraph then add one some line breaks.
    if hasattr(obj, 'name') and obj.name == 'para':
        result += "\n\n"
    return result

########NEW FILE########
__FILENAME__ = swig_doc
#
# Copyright 2010,2011 Free Software Foundation, Inc.
# 
# This file is part of GNU Radio
# 
# GNU Radio is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 3, or (at your option)
# any later version.
# 
# GNU Radio is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
# 
# You should have received a copy of the GNU General Public License
# along with GNU Radio; see the file COPYING.  If not, write to
# the Free Software Foundation, Inc., 51 Franklin Street,
# Boston, MA 02110-1301, USA.
# 
"""
Creates the swig_doc.i SWIG interface file.
Execute using: python swig_doc.py xml_path outputfilename

The file instructs SWIG to transfer the doxygen comments into the
python docstrings.

"""

import sys

try:
    from doxyxml import DoxyIndex, DoxyClass, DoxyFriend, DoxyFunction, DoxyFile, base
except ImportError:
    from gnuradio.doxyxml import DoxyIndex, DoxyClass, DoxyFriend, DoxyFunction, DoxyFile, base


def py_name(name):
    bits = name.split('_')
    return '_'.join(bits[1:])

def make_name(name):
    bits = name.split('_')
    return bits[0] + '_make_' + '_'.join(bits[1:])


class Block(object):
    """
    Checks if doxyxml produced objects correspond to a gnuradio block.
    """

    @classmethod
    def includes(cls, item):
        if not isinstance(item, DoxyClass):
            return False
        # Check for a parsing error.
        if item.error():
            return False
        return item.has_member(make_name(item.name()), DoxyFriend)


def utoascii(text):
    """
    Convert unicode text into ascii and escape quotes.
    """
    if text is None:
        return ''
    out = text.encode('ascii', 'replace')
    out = out.replace('"', '\\"')
    return out


def combine_descriptions(obj):
    """
    Combines the brief and detailed descriptions of an object together.
    """
    description = []
    bd = obj.brief_description.strip()
    dd = obj.detailed_description.strip()
    if bd:
        description.append(bd)
    if dd:
        description.append(dd)
    return utoascii('\n\n'.join(description)).strip()
    

entry_templ = '%feature("docstring") {name} "{docstring}"'
def make_entry(obj, name=None, templ="{description}", description=None):
    """
    Create a docstring entry for a swig interface file.
    
    obj - a doxyxml object from which documentation will be extracted.
    name - the name of the C object (defaults to obj.name())
    templ - an optional template for the docstring containing only one
            variable named 'description'.
    description - if this optional variable is set then it's value is
            used as the description instead of extracting it from obj.
    """
    if name is None:
        name=obj.name()
    if description is None:
        description = combine_descriptions(obj)
    docstring = templ.format(description=description)
    if not docstring:
        return ''
    return entry_templ.format(
        name=name,
        docstring=docstring,
        )


def make_func_entry(func, name=None, description=None, params=None):
    """
    Create a function docstring entry for a swig interface file.

    func - a doxyxml object from which documentation will be extracted.
    name - the name of the C object (defaults to func.name())
    description - if this optional variable is set then it's value is
            used as the description instead of extracting it from func.
    params - a parameter list that overrides using func.params.
    """
    if params is None:
        params = func.params
    params = [prm.declname for prm in params]
    if params:
        sig = "Params: (%s)" % ", ".join(params)
    else:
        sig = "Params: (NONE)"
    templ = "{description}\n\n" + sig
    return make_entry(func, name=name, templ=utoascii(templ),
                      description=description)


def make_class_entry(klass, description=None):
    """
    Create a class docstring for a swig interface file.
    """
    output = []
    output.append(make_entry(klass, description=description))
    for func in klass.in_category(DoxyFunction):
        name = klass.name() + '::' + func.name()
        output.append(make_func_entry(func, name=name))
    return "\n\n".join(output)


def make_block_entry(di, block):
    """
    Create class and function docstrings of a gnuradio block for a
    swig interface file.
    """
    descriptions = []
    # Get the documentation associated with the class.
    class_desc = combine_descriptions(block)
    if class_desc:
        descriptions.append(class_desc)
    # Get the documentation associated with the make function
    make_func = di.get_member(make_name(block.name()), DoxyFunction)
    make_func_desc = combine_descriptions(make_func)
    if make_func_desc:
        descriptions.append(make_func_desc)
    # Get the documentation associated with the file
    try:
        block_file = di.get_member(block.name() + ".h", DoxyFile)
        file_desc = combine_descriptions(block_file)
        if file_desc:
            descriptions.append(file_desc)
    except base.Base.NoSuchMember:
        # Don't worry if we can't find a matching file.
        pass
    # And join them all together to make a super duper description.
    super_description = "\n\n".join(descriptions)
    # Associate the combined description with the class and
    # the make function.
    output = []
    output.append(make_class_entry(block, description=super_description))
    creator = block.get_member(block.name(), DoxyFunction)
    output.append(make_func_entry(make_func, description=super_description,
                                  params=creator.params))
    return "\n\n".join(output)


def make_swig_interface_file(di, swigdocfilename, custom_output=None):
    
    output = ["""
/*
 * This file was automatically generated using swig_doc.py.
 * 
 * Any changes to it will be lost next time it is regenerated.
 */
"""]

    if custom_output is not None:
        output.append(custom_output)

    # Create docstrings for the blocks.
    blocks = di.in_category(Block)
    make_funcs = set([])
    for block in blocks:
        try:
            make_func = di.get_member(make_name(block.name()), DoxyFunction)
            make_funcs.add(make_func.name())
            output.append(make_block_entry(di, block))
        except block.ParsingError:
            print('Parsing error for block %s' % block.name())

    # Create docstrings for functions
    # Don't include the make functions since they have already been dealt with.
    funcs = [f for f in di.in_category(DoxyFunction) if f.name() not in make_funcs]
    for f in funcs:
        try:
            output.append(make_func_entry(f))
        except f.ParsingError:
            print('Parsing error for function %s' % f.name())

    # Create docstrings for classes
    block_names = [block.name() for block in blocks]
    klasses = [k for k in di.in_category(DoxyClass) if k.name() not in block_names]
    for k in klasses:
        try:
            output.append(make_class_entry(k))
        except k.ParsingError:
            print('Parsing error for class %s' % k.name())

    # Docstrings are not created for anything that is not a function or a class.
    # If this excludes anything important please add it here.

    output = "\n\n".join(output)

    swig_doc = file(swigdocfilename, 'w')
    swig_doc.write(output)
    swig_doc.close()

if __name__ == "__main__":
    # Parse command line options and set up doxyxml.
    err_msg = "Execute using: python swig_doc.py xml_path outputfilename"
    if len(sys.argv) != 3:
        raise StandardError(err_msg)
    xml_path = sys.argv[1]
    swigdocfilename = sys.argv[2]
    di = DoxyIndex(xml_path)

    # gnuradio.gr.msq_queue.insert_tail and delete_head create errors unless docstrings are defined!
    # This is presumably a bug in SWIG.
    #msg_q = di.get_member(u'gr_msg_queue', DoxyClass)
    #insert_tail = msg_q.get_member(u'insert_tail', DoxyFunction)
    #delete_head = msg_q.get_member(u'delete_head', DoxyFunction)
    output = []
    #output.append(make_func_entry(insert_tail, name='gr_py_msg_queue__insert_tail'))
    #output.append(make_func_entry(delete_head, name='gr_py_msg_queue__delete_head'))
    custom_output = "\n\n".join(output)

    # Generate the docstrings interface file.
    make_swig_interface_file(di, swigdocfilename, custom_output=custom_output)

########NEW FILE########
__FILENAME__ = altitude
#!/usr/bin/env python
#
# Copyright 2010, 2012 Nick Foster
# 
# This file is part of gr-air-modes
# 
# gr-air-modes is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 3, or (at your option)
# any later version.
# 
# gr-air-modes is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
# 
# You should have received a copy of the GNU General Public License
# along with gr-air-modes; see the file COPYING.  If not, write to
# the Free Software Foundation, Inc., 51 Franklin Street,
# Boston, MA 02110-1301, USA.
#

# For reference into the methodology used to decode altitude,
# see RTCA DO-181D p.42

from air_modes.exceptions import *

def decode_alt(alt, bit13):
	mbit = alt & 0x0040
	qbit = alt & 0x0010
	
	if mbit and bit13:
		#nobody uses metric altitude: AFAIK, it's an orphaned part of
		#the spec. haven't seen it in three years. as a result, replies
		#with mbit set can be considered spurious, and so we discard them here.
		
		#bits 20-25, 27-31 encode alt in meters
		#remember that bits are LSB (bit 20 is MSB)
		#meters_alt = 0
		#for (shift, bit) in enumerate(range(31,26,-1)+range(25,19,-1)):
		#	meters_alt += ((alt & (1<<bit)) != 0) << shift
		#decoded_alt = meters_alt / 0.3048
		raise MetricAltError

	if qbit: #a mode S-style reply
		#bit13 is false for BDS0,5 ADS-B squitters, and is true otherwise
		if bit13:
			#in this representation, the altitude bits are as follows:
			# 12 11 10 9 8 7 (6) 5 (4) 3 2 1 0
			# so bits 6 and 4 are the M and Q bits, respectively.
			tmp1 = (alt & 0x3F80) >> 2
			tmp2 = (alt & 0x0020) >> 1
		else:
			tmp1 = (alt & 0x1FE0) >> 1
			tmp2 = 0

		decoded_alt = ((alt & 0x0F) | tmp1 | tmp2) * 25 - 1000

	else: #a mode C-style reply
		  #okay, the order they come in is:
		  #C1 A1 C2 A2 C4 A4 X B1 D1 B2 D2 B4 D4
    	  #the order we want them in is:
    	  #D2 D4 A1 A2 A4 B1 B2 B4
    	  #so we'll reassemble into a Gray-coded representation

		if bit13 is False:
			alt = (alt & 0x003F) | (alt & 0x0FC0 << 1)

		C1 = 0x1000
		A1 = 0x0800
		C2 = 0x0400
		A2 = 0x0200	#this represents the order in which the bits come
		C4 = 0x0100
		A4 = 0x0080
		B1 = 0x0020
		D1 = 0x0010
		B2 = 0x0008
		D2 = 0x0004
		B4 = 0x0002
		D4 = 0x0001

		bigpart =  ((alt & B4) >> 1) \
				 + ((alt & B2) >> 2) \
				 + ((alt & B1) >> 3) \
				 + ((alt & A4) >> 4) \
				 + ((alt & A2) >> 5) \
				 + ((alt & A1) >> 6) \
				 + ((alt & D4) << 6) \
				 + ((alt & D2) << 5)

		#bigpart is now the 500-foot-resolution Gray-coded binary part
		decoded_alt = gray2bin(bigpart)
		#real_alt is now the 500-foot-per-tick altitude

		cbits =   ((alt & C4) >> 8) + ((alt & C2) >> 9) + ((alt & C1) >> 10)
		cval = gray2bin(cbits) #turn them into a real number

		if cval == 7:
			cval = 5 #not a real gray code after all

		if decoded_alt % 2:
			cval = 6 - cval #since the code is symmetric this unwraps it to see whether to subtract the C bits or add them

		decoded_alt *= 500 #take care of the A,B,D data
		decoded_alt += cval * 100 #factor in the C data
		decoded_alt -= 1300 #subtract the offset

	return decoded_alt

def gray2bin(gray):
	i = gray >> 1

	while i != 0:
		gray ^= i
		i >>= 1

	return gray

def encode_alt_modes(alt, bit13):
	mbit = False
	qbit = True
	encalt = (int(alt) + 1000) / 25

	if bit13 is True:
		tmp1 = (encalt & 0xfe0) << 2
		tmp2 = (encalt & 0x010) << 1
		
	else:
		tmp1 = (encalt & 0xff8) << 1
		tmp2 = 0

	return (encalt & 0x0F) | tmp1 | tmp2 | (mbit << 6) | (qbit << 4)

if __name__ == "__main__":
	try:
		for alt in range(-1000, 101400, 25):
			dec = decode_alt(encode_alt_modes(alt, False), False)
			if dec != alt:
				print "Failure at %i with bit13 clear (got %s)" % (alt, dec)
		for alt in range(-1000, 101400, 25):
			dec = decode_alt(encode_alt_modes(alt, True), True)
			if dec != alt:
				print "Failure at %i with bit13 set (got %s)" % (alt, dec)
	except MetricAltError:
		print "Failure at %i due to metric alt bit" % alt

########NEW FILE########
__FILENAME__ = az_map
#!/usr/bin/env python
#
# Copyright 2012 Nick Foster
# 
# This file is part of gr-air-modes
# 
# gr-air-modes is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 3, or (at your option)
# any later version.
# 
# gr-air-modes is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
# 
# You should have received a copy of the GNU General Public License
# along with gr-air-modes; see the file COPYING.  If not, write to
# the Free Software Foundation, Inc., 51 Franklin Street,
# Boston, MA 02110-1301, USA.
#

# azimuthal projection widget to plot reception range vs. azimuth

from PyQt4 import QtCore, QtGui
import threading
import math
import air_modes
from air_modes.exceptions import *
import numpy as np

# model has max range vs. azimuth in n-degree increments
# contains separate max range for a variety of altitudes so
# you can determine your altitude dropouts by bearing
# assumes that if you can hear ac at 1000', you can hear at 5000'+.
class az_map_model(QtCore.QObject):
    dataChanged = QtCore.pyqtSignal(name='dataChanged')
    npoints = 360/5
    def __init__(self, parent=None):
        super(az_map_model, self).__init__(parent)
        self._data = []
        self.lock = threading.Lock()
        self._altitudes = [0, 1000, 2000, 5000, 10000, 15000, 20000, 25000, 30000]
        #initialize everything to 0
        for i in range(0,az_map_model.npoints):
            self._data.append([0] * len(self._altitudes))

    def rowCount(self):
        return len(self._data)

    def columnCount(self):
        return len(self._altitudes)

    def data(self, row, col):
        return self._data[row][col]

    def addRecord(self, bearing, altitude, distance):
        with self.lock:
            #round up to nearest altitude in altitudes list
            #there's probably another way to do it
            if altitude >= max(self._altitudes):
                col = self.columnCount()-1
            else:
                col = self._altitudes.index(min([alt for alt in self._altitudes if alt >= altitude]))

            #find which bearing row we sit in
            row = int(int(bearing+(180./az_map_model.npoints)) / (360./az_map_model.npoints)) % az_map_model.npoints
            #set max range for all alts >= the ac alt
            #this expresses the assumption that higher ac can be heard further
            update = False
            for i in range(col, len(self._altitudes)):
                if distance > self._data[row][i]:
                    self._data[row][i] = distance
                    update = True
        if update:
            self.dataChanged.emit()

    def reset(self):
        with self.lock:
            self._data = []
            for i in range(0,az_map_model.npoints):
                self._data.append([0] * len(self._altitudes))
        self.dataChanged.emit()


# the azimuth map widget
class az_map(QtGui.QWidget):
    maxrange = 200
    bgcolor = QtCore.Qt.black
    ringpen =  QtGui.QPen(QtGui.QColor(0,   96,  127, 255), 1.3)

    def __init__(self, parent=None):
        super(az_map, self).__init__(parent)
        self._model = None
        self._paths = []
        self.maxrange = az_map.maxrange

    def minimumSizeHint(self):
        return QtCore.QSize(50, 50)

    def sizeHint(self):
        return QtCore.QSize(300, 300)

    def setModel(self, model):
        self._model = model
        self._model.dataChanged.connect(self.repaint)

    def paintEvent(self, event):
        painter = QtGui.QPainter(self)
        painter.setRenderHint(QtGui.QPainter.Antialiasing)
        #TODO: make it not have to redraw paths EVERY repaint
        #drawing paths is VERY SLOW
        #maybe use a QTimer to limit repaints
        self.drawPaths()

        #set background
        painter.fillRect(event.rect(), QtGui.QBrush(az_map.bgcolor))

        #draw the range rings
        self.drawRangeRings(painter)
        for i in range(len(self._paths)):
            alpha = 230 * (i+1) / (len(self._paths)) + 25
            painter.setPen(QtGui.QPen(QtGui.QColor(alpha,alpha,0,255), 1.0))
            painter.drawPath(self._paths[i])

    def drawPaths(self):
        self._paths = []
        if(self._model):
            for alt in range(0, self._model.columnCount()):
                path = QtGui.QPainterPath()
                for i in range(az_map_model.npoints-1,-1,-1):
                    #bearing is to start point of arc (clockwise) 
                    bearing = (i+0.5) * 360./az_map_model.npoints
                    distance = self._model._data[i][alt]
                    radius = min(self.width(), self.height()) / 2.0
                    scale = radius * distance / self.get_range()
                    #convert bearing,distance to x,y
                    xpts = scale * math.sin(bearing * math.pi / 180)
                    ypts = scale * math.cos(bearing * math.pi / 180)
                    #get the bounding rectangle of the arc

                    arcrect = QtCore.QRectF(QtCore.QPointF(0-scale, 0-scale),
                                            QtCore.QPointF(scale, scale))

                    if path.isEmpty():
                        path.moveTo(xpts, 0-ypts) #so we don't get a line from 0,0 to the first point
                    else:
                        path.lineTo(xpts, 0-ypts)
                    path.arcTo(arcrect, 90-bearing, 360./az_map_model.npoints)

                self._paths.append(path)

    #this is just to add a little buffer space for showing the ring & range
    def get_range(self):
        return int(self.maxrange * 1.1)

    def drawRangeRings(self, painter):
        painter.translate(self.width()/2, self.height()/2)
        #choose intelligent range step -- keep it between 3-5 rings
        rangestep = 100
        while self.get_range() / rangestep < 3:
            rangestep /= 2.0
        for i in np.arange(rangestep, self.get_range(), rangestep): 
            diameter = (float(i) / self.get_range()) * min(self.width(), self.height())
            painter.setPen(az_map.ringpen)
            painter.drawEllipse(QtCore.QRectF(-diameter / 2.0,
                                -diameter / 2.0, diameter, diameter))
            painter.setPen(QtGui.QColor(255,127,0,255))

            painter.drawText(0-70/2.0, diameter/2.0, 70, 30, QtCore.Qt.AlignHCenter,
                             "%.1fnm" % i)

    def setMaxRange(self, maxrange):
        maxrange = max(3.25, maxrange)
        maxrange = min(500., maxrange)
        self.maxrange = maxrange
        self.repaint()

    def wheelEvent(self, event):
        self.setMaxRange(self.maxrange + (event.delta()/120.)*self.maxrange/4.)

class az_map_output:
    def __init__(self, cprdec, model, pub):
        self._cpr = cprdec
        self.model = model
        pub.subscribe("type17_dl", self.output)

    def output(self, msg):
        try:
            now = time.time()

            icao = msg.data["aa"]
            subtype = msg.data["ftc"]
            distance, altitude, bearing = [0,0,0]
            if 5 <= subtype <= 8:
                (ground_track, decoded_lat, decoded_lon, distance, bearing) = air_modes.parseBDS06(msg.data, self._cpr)
                altitude = 0
            elif 9 <= subtype <= 18:
                    (altitude, decoded_lat, decoded_lon, distance, bearing) = air_modes.parseBDS05(msg.data, self._cpr)

            self.model.addRecord(bearing, altitude, distance)
        except ADSBError:
            pass


##############################
# Test stuff
##############################
import random, time

class model_updater(threading.Thread):
    def __init__(self, model):
        super(model_updater, self).__init__()
        self.model = model
        self.setDaemon(1)
        self.done = False
        self.start()

    def run(self):
        for i in range(az_map_model.npoints):
            time.sleep(0.005)
            if(self.model):
                for alt in self.model._altitudes:
                    self.model.addRecord(i*360./az_map_model.npoints, alt, random.randint(0,az_map.maxrange)*alt / max(self.model._altitudes))
        self.done = True
        
class Window(QtGui.QWidget):
    def __init__(self):
        super(Window, self).__init__()
        layout = QtGui.QGridLayout()
        self.model = az_map_model()
        mymap = az_map(None)
        mymap.setModel(self.model)
        self.updater = model_updater(self.model)
        layout.addWidget(mymap, 0, 1)
        self.setLayout(layout)

if __name__ == '__main__':

    import sys

    app = QtGui.QApplication(sys.argv)
    window = Window()
    window.show()
    window.update()
    sys.exit(app.exec_())

########NEW FILE########
__FILENAME__ = cpr
#!/usr/bin/env python
#
# Copyright 2010, 2012 Nick Foster
# 
# This file is part of gr-air-modes
# 
# gr-air-modes is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 3, or (at your option)
# any later version.
# 
# gr-air-modes is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
# 
# You should have received a copy of the GNU General Public License
# along with gr-air-modes; see the file COPYING.  If not, write to
# the Free Software Foundation, Inc., 51 Franklin Street,
# Boston, MA 02110-1301, USA.
# 

import math, time
from air_modes.exceptions import *
#this implements CPR position decoding and encoding.
#the decoder is implemented as a class, cpr_decoder, which keeps state for local decoding.
#the encoder is cpr_encode([lat, lon], type (even=0, odd=1), and surface (0 for surface, 1 for airborne))

#TODO: remove range/bearing calc from CPR decoder class. you can do this outside of the decoder.

latz = 15

def nz(ctype):
	return 4 * latz - ctype

def dlat(ctype, surface):
	if surface == 1:
		tmp = 90.0
	else:
		tmp = 360.0

	nzcalc = nz(ctype)
	if nzcalc == 0:
		return tmp
	else:
		return tmp / nzcalc

def nl(declat_in):
	if abs(declat_in) >= 87.0:
		return 1.0
	return math.floor( (2.0*math.pi) * math.acos(1.0- (1.0-math.cos(math.pi/(2.0*latz))) / math.cos( (math.pi/180.0)*abs(declat_in) )**2 )**-1)

def dlon(declat_in, ctype, surface):
	if surface:
		tmp = 90.0
	else:
		tmp = 360.0
	nlcalc = max(nl(declat_in)-ctype, 1)
	return tmp / nlcalc

def decode_lat(enclat, ctype, my_lat, surface):
	tmp1 = dlat(ctype, surface)
	tmp2 = float(enclat) / (2**17)
	j = math.floor(my_lat/tmp1) + math.floor(0.5 + ((my_lat % tmp1) / tmp1) - tmp2)

	return tmp1 * (j + tmp2)

def decode_lon(declat, enclon, ctype, my_lon, surface):
	tmp1 = dlon(declat, ctype, surface)
	tmp2 = float(enclon) / (2**17)
	m = math.floor(my_lon / tmp1) + math.floor(0.5 + ((my_lon % tmp1) / tmp1) - tmp2)

	return tmp1 * (m + tmp2)

def cpr_resolve_local(my_location, encoded_location, ctype, surface):
	[my_lat, my_lon] = my_location
	[enclat, enclon] = encoded_location

	decoded_lat = decode_lat(enclat, ctype, my_lat, surface)
	decoded_lon = decode_lon(decoded_lat, enclon, ctype, my_lon, surface)

	return [decoded_lat, decoded_lon]

def cpr_resolve_global(evenpos, oddpos, mypos, mostrecent, surface):
	#cannot resolve surface positions unambiguously without knowing receiver position
	if surface and mypos is None:
		raise CPRNoPositionError
	
	dlateven = dlat(0, surface)
	dlatodd  = dlat(1, surface)

	evenpos = [float(evenpos[0]), float(evenpos[1])]
	oddpos = [float(oddpos[0]), float(oddpos[1])]
	
	j = math.floor(((nz(1)*evenpos[0] - nz(0)*oddpos[0])/2**17) + 0.5) #latitude index

	rlateven = dlateven * ((j % nz(0))+evenpos[0]/2**17)
	rlatodd  = dlatodd  * ((j % nz(1))+ oddpos[0]/2**17)

	#limit to -90, 90
	if rlateven > 270.0:
		rlateven -= 360.0
	if rlatodd > 270.0:
		rlatodd -= 360.0

	#This checks to see if the latitudes of the reports straddle a transition boundary
	#If so, you can't get a globally-resolvable location.
	if nl(rlateven) != nl(rlatodd):
		raise CPRBoundaryStraddleError

	if mostrecent == 0:
		rlat = rlateven
	else:
		rlat = rlatodd

	#disambiguate latitude
	if surface:
		if mypos[0] < 0:
			rlat -= 90

	dl = dlon(rlat, mostrecent, surface)
	nl_rlat = nl(rlat)

	m = math.floor(((evenpos[1]*(nl_rlat-1)-oddpos[1]*nl_rlat)/2**17)+0.5) #longitude index
	
	#when surface positions straddle a disambiguation boundary (90 degrees),
	#surface decoding will fail. this might never be a problem in real life, but it'll fail in the
	#test case. the documentation doesn't mention it.

	if mostrecent == 0:
		enclon = evenpos[1]
	else:
		enclon = oddpos[1]

	rlon = dl * ((m % max(nl_rlat-mostrecent,1)) + enclon/2.**17)

	#print "DL: %f nl: %f m: %f rlon: %f" % (dl, nl_rlat, m, rlon)
	#print "evenpos: %x, oddpos: %x, mostrecent: %i" % (evenpos[1], oddpos[1], mostrecent)

	if surface:
		#longitudes need to be resolved to the nearest 90 degree segment to the receiver.
		wat = mypos[1]
		if wat < 0:
			wat += 360
		zone = lambda lon: 90 * (int(lon) / 90)
		rlon += (zone(wat) - zone(rlon))

	#limit to (-180, 180)
	if rlon > 180:
		rlon -= 360.0

	return [rlat, rlon]


#calculate range and bearing between two lat/lon points
#should probably throw this in the mlat py somewhere or make another lib
def range_bearing(loc_a, loc_b):
	[a_lat, a_lon] = loc_a
	[b_lat, b_lon] = loc_b

	esquared = (1/298.257223563)*(2-(1/298.257223563))
	earth_radius_mi = 3963.19059 * (math.pi / 180)

	delta_lat = b_lat - a_lat
	delta_lon = b_lon - a_lon

	avg_lat = ((a_lat + b_lat) / 2.0) * math.pi / 180

	R1 = earth_radius_mi*(1.0-esquared)/pow((1.0-esquared*pow(math.sin(avg_lat),2)),1.5)

	R2 = earth_radius_mi/math.sqrt(1.0-esquared*pow(math.sin(avg_lat),2))

	distance_North = R1*delta_lat
	distance_East = R2*math.cos(avg_lat)*delta_lon

	bearing = math.atan2(distance_East,distance_North) * (180.0 / math.pi)
	if bearing < 0.0:
		bearing += 360.0

	rnge = math.hypot(distance_East,distance_North)
	return [rnge, bearing]

class cpr_decoder:
	def __init__(self, my_location):
		self.my_location = my_location
		self.evenlist = {}
		self.oddlist = {}
		self.evenlist_sfc = {}
		self.oddlist_sfc = {}

	def set_location(self, new_location):
		self.my_location = new_location

	def weed_poslists(self):
		for poslist in [self.evenlist, self.oddlist]:
			for key, item in poslist.items():
				if time.time() - item[2] > 10:
					del poslist[key]
		for poslist in [self.evenlist_sfc, self.oddlist_sfc]:
			for key, item in poslist.items():
				if time.time() - item[2] > 25:
					del poslist[key]

	def decode(self, icao24, encoded_lat, encoded_lon, cpr_format, surface):
		if surface:
			oddlist = self.oddlist_sfc
			evenlist = self.evenlist_sfc
		else:
			oddlist = self.oddlist
			evenlist = self.evenlist

		#add the info to the position reports list for global decoding
		if cpr_format==1:
			oddlist[icao24] = [encoded_lat, encoded_lon, time.time()]
		else:
			evenlist[icao24] = [encoded_lat, encoded_lon, time.time()]

		[decoded_lat, decoded_lon] = [None, None]

		#okay, let's traverse the lists and weed out those entries that are older than 10 seconds
		self.weed_poslists()

		if (icao24 in evenlist) \
		  and (icao24 in oddlist):
			newer = (oddlist[icao24][2] - evenlist[icao24][2]) > 0 #figure out which report is newer
   			[decoded_lat, decoded_lon] = cpr_resolve_global(evenlist[icao24][0:2], oddlist[icao24][0:2], self.my_location, newer, surface) #do a global decode
		else:
			raise CPRNoPositionError

		if self.my_location is not None:
			[rnge, bearing] = range_bearing(self.my_location, [decoded_lat, decoded_lon])
		else:
			rnge = None
			bearing = None

		return [decoded_lat, decoded_lon, rnge, bearing]

#encode CPR position
def cpr_encode(lat, lon, ctype, surface):
	if surface is True:
		scalar = 2.**19
	else:
		scalar = 2.**17

	#encode using 360 constant for segment size.
	dlati = dlat(ctype, False)
	yz = math.floor(scalar * ((lat % dlati)/dlati) + 0.5)
	rlat = dlati * ((yz / scalar) + math.floor(lat / dlati))

	#encode using 360 constant for segment size.
	dloni = dlon(lat, ctype, False)
	xz = math.floor(scalar * ((lon % dloni)/dloni) + 0.5)

	yz = int(yz) & (2**17-1)
	xz = int(xz) & (2**17-1)

	return (yz, xz) #lat, lon

if __name__ == '__main__':
	import sys, random
	
	rounds = 10001
	threshold = 1e-3 #0.001 deg lat/lon
	#this accuracy is highly dependent on latitude, since at high
	#latitudes the corresponding error in longitude is greater

	bs = 0
	surface = False

	lats = [i/(rounds/170.)-85 for i in range(0,rounds)]
	lons = [i/(rounds/360.)-180 for i in range(0,rounds)]

	for i in range(0, rounds):
		even_lat = lats[i]
		#even_lat = random.uniform(-85, 85)
		even_lon = lons[i]
		#even_lon = random.uniform(-180, 180)
		odd_lat = even_lat + 1e-3
		odd_lon = min(even_lon + 1e-3, 180)
		decoder = cpr_decoder([odd_lat, odd_lon])

		#encode that position
		(evenenclat, evenenclon) = cpr_encode(even_lat, even_lon, False, surface)
		(oddenclat, oddenclon)   = cpr_encode(odd_lat, odd_lon, True, surface)

		#try to perform a global decode -- this should fail since the decoder
		#only has heard one position. need two for global decoding.
		icao = random.randint(0, 0xffffff)
		try:
			evenpos = decoder.decode(icao, evenenclat, evenenclon, False, surface)
			raise Exception("CPR test failure: global decode with only one report")
		except CPRNoPositionError:
			pass

		#now try to do a real decode with the last packet's odd complement
		#watch for a boundary straddle -- this isn't fatal, it just indicates
		#that the even and odd reports lie on either side of a longitudinal boundary
		#and so you can't get a position
		try:
			(odddeclat, odddeclon, rng, brg) = decoder.decode(icao, oddenclat, oddenclon, True, surface)
		except CPRBoundaryStraddleError:
			bs += 1
			continue
		except CPRNoPositionError:
			raise Exception("CPR test failure: no decode after even/odd inputs")

		if abs(odddeclat - odd_lat) > threshold or abs(odddeclon - odd_lon) > threshold:
			print "F odddeclat: %f odd_lat: %f" % (odddeclat, odd_lat)
			print "F odddeclon: %f odd_lon: %f" % (odddeclon, odd_lon)
			raise Exception("CPR test failure: global decode error greater than threshold")
#		else:
#			print "S odddeclat: %f odd_lat: %f" % (odddeclat, odd_lat)
#			print "S odddeclon: %f odd_lon: %f" % (odddeclon, odd_lon)

		nexteven_lat = odd_lat + 1e-3
		nexteven_lon = min(odd_lon + 1e-3, 180)

		(nexteven_enclat, nexteven_enclon) = cpr_encode(nexteven_lat, nexteven_lon, False, surface)

		#try a locally-referenced decode
		try:
			(evendeclat, evendeclon) = cpr_resolve_local([even_lat, even_lon], [nexteven_enclat, nexteven_enclon], False, surface)
		except CPRNoPositionError:
			raise Exception("CPR test failure: local decode failure to resolve")

		#check to see if the positions were valid
		if abs(evendeclat - nexteven_lat) > threshold or abs(evendeclon - nexteven_lon) > threshold:
			print "F evendeclat: %f nexteven_lat: %f evenlat: %f" % (evendeclat, nexteven_lat, even_lat)
			print "F evendeclon: %f nexteven_lon: %f evenlon: %f" % (evendeclon, nexteven_lon, even_lon)
			raise Exception("CPR test failure: local decode error greater than threshold")

	print "CPR test successful. There were %i boundary straddles over %i rounds." % (bs, rounds)

########NEW FILE########
__FILENAME__ = exceptions
#
# Copyright 2012 Nick Foster
# 
# This file is part of gr-air-modes
# 
# gr-air-modes is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 3, or (at your option)
# any later version.
# 
# gr-air-modes is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
# 
# You should have received a copy of the GNU General Public License
# along with gr-air-modes; see the file COPYING.  If not, write to
# the Free Software Foundation, Inc., 51 Franklin Street,
# Boston, MA 02110-1301, USA.
# 

class ADSBError(Exception):
    pass

class MetricAltError(ADSBError):
    pass

class ParserError(ADSBError):
    pass

class NoHandlerError(ADSBError):
    def __init__(self, msgtype=None):
        self.msgtype = msgtype

class MlatNonConvergeError(ADSBError):
    pass

class CPRNoPositionError(ADSBError):
    pass

class CPRBoundaryStraddleError(CPRNoPositionError):
    pass

class FieldNotInPacket(ParserError):
    def __init__(self, item):
        self.item = item


########NEW FILE########
__FILENAME__ = flightgear
#!/usr/bin/env python

#flightgear interface to uhd_modes.py
#outputs UDP data to add traffic to FGFS

import struct
import socket
import air_modes
from air_modes import mlat
import sqlite3
import string, threading, math, time
from air_modes.sql import output_sql
from Quaternion import Quat
import numpy
from air_modes.exceptions import *

class output_flightgear:
    def __init__(self, cprdec, hostname, port, pub):
        self.hostname = hostname
        self.port = port
        self.positions = {}
        self.velocities = {}
        self.callsigns = {}
        self._cpr = cprdec

        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.sock.connect((self.hostname, self.port))
        pub.subscribe("type17_dl", self.output)

    def output(self, msg):
        try:
            msgtype = msg.data["df"]
            if msgtype == 17: #ADS-B report
                icao24 = msg.data["aa"]
                bdsreg = msg.data["me"].get_type()
                if bdsreg == 0x08: #ident packet
                    (ident, actype) = air_modes.parseBDS08(msg.data)
                    #select model based on actype
                    self.callsigns[icao24] = [ident, actype]

                elif bdsreg == 0x06: #BDS0,6 pos
                    [ground_track, decoded_lat, decoded_lon, rnge, bearing] = air_modes.parseBDS06(msg.data, self._cpr)
                    self.positions[icao24] = [decoded_lat, decoded_lon, 0]
                    self.update(icao24)

                elif bdsreg == 0x05: #BDS0,5 pos
                    [altitude, decoded_lat, decoded_lon, rnge, bearing] = air_modes.parseBDS05(msg.data, self._cpr)
                    self.positions[icao24] = [decoded_lat, decoded_lon, altitude]
                    self.update(icao24)

                elif bdsreg == 0x09: #velocity
                    subtype = msg.data["bds09"].get_type()
                    if subtype == 0:
                      [velocity, heading, vert_spd, turnrate] = air_modes.parseBDS09_0(msg.data)
                    elif subtype == 1:
                      [velocity, heading, vert_spd] = air_modes.parseBDS09_1(msg.data)
                      turnrate = 0
                    else:
                        return

                    self.velocities[icao24] = [velocity, heading, vert_spd, turnrate]

        except ADSBError:
            pass

    def update(self, icao24):
        #check to see that ICAO24 appears in all three records and that the data looks valid
        complete = (icao24 in self.positions)\
               and (icao24 in self.velocities)\
               and (icao24 in self.callsigns)
        if complete:
            print "FG update: %s" % (self.callsigns[icao24][0])
            msg = fg_posmsg(self.callsigns[icao24][0],
                            self.callsigns[icao24][1],
                            self.positions[icao24][0],
                            self.positions[icao24][1],
                            self.positions[icao24][2],
                            self.velocities[icao24][1],
                            self.velocities[icao24][0],
                            self.velocities[icao24][2],
                            self.velocities[icao24][3]).pack()

            self.sock.send(msg)

class fg_header:
    def __init__(self):
        self.magic = "FGFS"
        self.proto = 0x00010001
        self.msgid = 0
        self.msglen = 0 #in bytes, though they swear it isn't
        self.replyaddr = 0 #unused
        self.replyport = 0 #unused
        self.callsign = "UNKNOWN"
        self.data = None

    hdrfmt = '!4sLLLLL8s0L'

    def pack(self):
        self.msglen = 32 + len(self.data)
        packed = struct.pack(self.hdrfmt, self.magic, self.proto, self.msgid, self.msglen, self.replyaddr, self.replyport, self.callsign)
        return packed

#so this appears to work, but FGFS doesn't display it in flight for some reason. not in the chat window either. oh well.
class fg_chatmsg(fg_header):
    def __init__(self, msg):
        fg_header.__init__(self)
        self.chatmsg = msg
        self.msgid = 1

    def pack(self):
        self.chatfmt = '!' + str(len(self.chatmsg)) + 's'
        #print "Packing with strlen %i " % len(self.chatmsg)
        self.data = struct.pack(self.chatfmt, self.chatmsg)
        return fg_header.pack(self) + self.data

modelmap = { None:                       'Aircraft/777-200/Models/777-200ER.xml',
            "NO INFO":                   'Aircraft/777-200/Models/777-200ER.xml',
            "LIGHT":                     'Aircraft/c172p/Models/c172p.xml',
            "SMALL":                     'Aircraft/CitationX/Models/Citation-X.xml',
            "LARGE":                     'Aircraft/CRJ700-family/Models/CRJ700.xml',
            "LARGE HIGH VORTEX":         'Aircraft/757-200/Models/757-200.xml',
            "HEAVY":                     'Aircraft/747-200/Models/boeing747-200.xml',
            "HIGH PERFORMANCE":          'Aircraft/SR71-BlackBird/Models/Blackbird-SR71B.xml', #yeah i know
            "ROTORCRAFT":                'Aircraft/ec130/Models/ec130b4.xml',
            "GLIDER":                    'Aircraft/ASK21-MI/Models/ask21mi.xml',
            "BALLOON/BLIMP":             'Aircraft/ZLT-NT/Models/ZLT-NT.xml',
            "ULTRALIGHT":                'Aircraft/cri-cri/Models/MC-15.xml',
            "UAV":                       'Aircraft/YardStik/Models/yardstik.xml', #hahahaha
            "SPACECRAFT":                'Aircraft/SpaceShip-One/Models/spaceshipone.xml',
            "SURFACE EMERGENCY VEHICLE": 'Aircraft/followme/Models/follow_me.xml', #not the best
            "SURFACE SERVICE VEHICLE":   'Aircraft/pushback/Models/Pushback.xml'
}

class fg_posmsg(fg_header):
    def __init__(self, callsign, modelname, lat, lon, alt, hdg, vel, vs, turnrate):
        #from the above, calculate valid FGFS mp vals
        #this is the translation layer between ADS-B and FGFS
        fg_header.__init__(self)
        self.callsign = callsign
        if self.callsign is None:
            self.callsign = "UNKNOWN"
        self.modelname = modelname
        if self.modelname not in modelmap:
            #this should keep people on their toes when strange aircraft types are seen
            self.model = 'Aircraft/santa/Models/santa.xml'
        else:
            self.model = modelmap[self.modelname]
            
        self.lat = lat
        self.lon = lon
        self.alt = alt
        self.hdg = hdg
        self.vel = vel
        self.vs = vs
        self.turnrate = turnrate
        self.msgid = 7
        self.time = time.time()
        self.lag = 0

    def pack(self):
        #this is, in order:
        #model, time (time.time() is fine), lag, position, orientation, linear vel, angular vel, linear accel, angular accel (accels unused), 0
        #position is in ECEF format -- same as mlat uses. what luck!
        pos = mlat.llh2ecef([self.lat, self.lon, self.alt * 0.3048]) #alt is in meters!

        #get the rotation quaternion to rotate to local reference frame from lat/lon
        rotquat = Quat([self.lat, self.lon])
        #get the quaternion corresponding to aircraft orientation
        acquat = Quat([self.hdg, 0, 0])
        #rotate aircraft into ECEF frame
        ecefquat = rotquat * acquat
        #get it in angle/axis representation
        (angle, axis) = ecefquat._get_angle_axis()
        orientation = angle * axis
        
        kts_to_ms = 0.514444444 #convert kts to m/s
        vel_ms = self.vel * kts_to_ms
        velvec = (vel_ms,0,0) #velocity vector in m/s -- is this in the local frame? looks like [0] is fwd vel,
                                   #we'll pretend the a/c is always moving the dir it's pointing
        turnvec = (0,0,self.turnrate * (math.pi / 180.) ) #turn rates in rad/s [roll, pitch, yaw]
        accelvec = (0,0,0)
        turnaccelvec = (0,0,0)
        self.posfmt = '!96s' + 'd' + 'd' + '3d' + '3f' + '3f' + '3f' + '3f' + '3f' + 'I'
        self.data = struct.pack(self.posfmt,
                                self.model,
                                self.time,
                                self.lag,
                                pos[0], pos[1], pos[2],
                                orientation[0], orientation[1], orientation[2],
                                velvec[0], velvec[1], velvec[2],
                                turnvec[0], turnvec[1], turnvec[2],
                                accelvec[0], accelvec[1], accelvec[2],
                                turnaccelvec[0], turnaccelvec[1], turnaccelvec[2],
                                0)

        return fg_header.pack(self) + self.data
        

if __name__ == '__main__':
    timeoffset = time.time()
    iof = open('27augrudi3.txt')
    localpos = [37.409066,-122.077836]
    hostname = "localhost"
    port = 5000
    fgout = output_flightgear(localpos, hostname, port)

    for line in iof:
        timetosend = float(line.split()[6])
        while (time.time() - timeoffset) < timetosend:
            time.sleep(0.02)
        fgout.output(line)

########NEW FILE########
__FILENAME__ = get_uniq
#!/usr/bin/env python

import sys, re

if __name__== '__main__':
    data = sys.stdin.readlines()
    icaos = []
    num_icaos = 0
    for line in data:
        match = re.match(".*from (\w+)", line)
        if match is not None:
            icao = int(match.group(1), 16)
            icaos.append(icao)

    #get dupes
    dupes = sorted([icao for icao in set(icaos) if icaos.count(icao) > 1])
    for icao in dupes:        
        print "%x" % icao
    print "Found non-unique replies from %i aircraft" % len(dupes)



########NEW FILE########
__FILENAME__ = gui_model
#!/usr/bin/env python
# Copyright 2012 Nick Foster
# 
# This file is part of gr-air-modes
# 
# gr-air-modes is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 3, or (at your option)
# any later version.
# 
# gr-air-modes is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
# 
# You should have received a copy of the GNU General Public License
# along with gr-air-modes; see the file COPYING.  If not, write to
# the Free Software Foundation, Inc., 51 Franklin Street,
# Boston, MA 02110-1301, USA.
#

# This file contains data models, view delegates, and associated classes
# for handling the GUI back end data model.

from PyQt4 import QtCore, QtGui
import air_modes
import threading, math, time
from air_modes.exceptions import *

#fades the ICAOs out as their last report gets older,
#and display ident if available, ICAO otherwise
class ICAOViewDelegate(QtGui.QStyledItemDelegate):
    def paint(self, painter, option, index):
        #draw selection rectangle
        if option.state & QtGui.QStyle.State_Selected:
            painter.setBrush(QtGui.QPalette().highlight())
            painter.drawRect(option.rect)

        #if there's an ident available, use it. otherwise print the ICAO
        if index.model().data(index.model().index(index.row(), 9)) != QtCore.QVariant():
            paintstr = index.model().data(index.model().index(index.row(), 9)).toString()
        else:
            paintstr = index.model().data(index.model().index(index.row(), 0)).toString()
        last_report = index.model().data(index.model().index(index.row(), 1)).toDouble()[0]
        age = (time.time() - last_report)
        max_age = 60. #age at which it grays out
        #minimum alpha is 0x40 (oldest), max is 0xFF (newest)
        age = min(age, max_age)
        alpha = int(0xFF - (0xBF / max_age) * age)
        painter.setPen(QtGui.QColor(0, 0, 0, alpha))
        painter.drawText(option.rect.left()+3, option.rect.top(), option.rect.width(), option.rect.height(), option.displayAlignment, paintstr)

#the data model used to display dashboard data.
class dashboard_data_model(QtCore.QAbstractTableModel):
    def __init__(self, parent):
        QtCore.QAbstractTableModel.__init__(self, parent)
        self._data = []
        self.lock = threading.Lock()
        self._colnames = ["icao", "seen", "rssi", "latitude", "longitude", "altitude", "speed", "heading", "vertical", "ident", "type", "range", "bearing"]
        #custom precision limits for display
        self._precisions = [None, None, None, 6, 6, 0, 0, 0, 0, None, None, 2, 0]
        for field in self._colnames:
            self.setHeaderData(self._colnames.index(field), QtCore.Qt.Horizontal, field)
    def rowCount(self, parent=QtCore.QVariant()):
        return len(self._data)
    def columnCount(self, parent=QtCore.QVariant()):
        return len(self._colnames)
    def data(self, index, role=QtCore.Qt.DisplayRole):
        if not index.isValid():
            return QtCore.QVariant()
        if index.row() >= self.rowCount():
            return QtCore.QVariant()
        if index.column() >= self.columnCount():
            return QtCore.QVariant()
        if (role != QtCore.Qt.DisplayRole) and (role != QtCore.Qt.EditRole):
            return QtCore.QVariant()
        if self._data[index.row()][index.column()] is None:
            return QtCore.QVariant()
        else:
            #if there's a dedicated precision for that column, print it out with the specified precision.
            #this only works well if you DON'T have other views/widgets that depend on numeric data coming out.
            #i don't like this, but it works for now. unfortunately it seems like Qt doesn't give you a
            #good alternative.
            if self._precisions[index.column()] is not None:
                return QtCore.QVariant("%.*f" % (self._precisions[index.column()], self._data[index.row()][index.column()]))
            else:
                if self._colnames[index.column()] == "icao":
                    return QtCore.QVariant("%06x" % self._data[index.row()][index.column()]) #return as hex string
                else:
                    return QtCore.QVariant(self._data[index.row()][index.column()])

    def setData(self, index, value, role=QtCore.Qt.EditRole):
        self.lock.acquire()
        if not index.isValid():
            return False
        if index.row() >= self.rowCount():
            return False
        if index.column >= self.columnCount():
            return False
        if role != QtCore.Qt.EditRole:
            return False
        self._data[index.row()][index.column()] = value
        self.lock.release()

    #addRecord implements an upsert on self._data; that is,
    #it updates the row if the ICAO exists, or else it creates a new row.
    def addRecord(self, record):
        self.lock.acquire()
        icaos = [x[0] for x in self._data]
        if record["icao"] in icaos:
            row = icaos.index(record["icao"])
            for column in record:
                self._data[row][self._colnames.index(column)] = record[column]
            #create index to existing row and tell the model everything's changed in this row
            #or inside the for loop, use dataChanged on each changed field (might be better)
            self.dataChanged.emit(self.createIndex(row, 0), self.createIndex(row, len(self._colnames)-1))

        #only create records for ICAOs with ADS-B reports
        elif ("latitude" or "speed" or "ident") in record:
            #find new inserted row number
            icaos.append(record["icao"])
            newrowoffset = sorted(icaos).index(record["icao"])
            self.beginInsertRows(QtCore.QModelIndex(), newrowoffset, newrowoffset)
            newrecord = [None for x in xrange(len(self._colnames))]
            for col in xrange(0, len(self._colnames)):
                if self._colnames[col] in record:
                    newrecord[col] = record[self._colnames[col]]
            self._data.append(newrecord)
            self._data = sorted(self._data, key = lambda x: x[0]) #sort by icao
            self.endInsertRows()
        self.lock.release()
        self.prune()

    #weeds out ICAOs older than 1 minute
    def prune(self):
        self.lock.acquire()
        for (index,row) in enumerate(self._data):
            if time.time() - row[1] >= 60:
                self.beginRemoveRows(QtCore.QModelIndex(), index, index)
                self._data.pop(index)
                self.endRemoveRows()
        self.lock.release()
                
class dashboard_output:
    def __init__(self, cprdec, model, pub):
        self.model = model
        self._cpr = cprdec
        pub.subscribe("modes_dl", self.output)
    def output(self, msg):
        try:
            msgtype = msg.data["df"]
            now = time.time()
            newrow = {"rssi": msg.rssi, "seen": now}
            if msgtype in [0, 4, 20]:
                newrow["altitude"] = air_modes.altitude.decode_alt(msg.data["ac"], True)
                newrow["icao"] = msg.ecc
                self.model.addRecord(newrow)
            
            elif msgtype == 17:
                icao = msg.data["aa"]
                newrow["icao"] = icao
                subtype = msg.data["ftc"]
                if subtype == 4:
                    (ident, actype) = air_modes.parseBDS08(msg.data)
                    newrow["ident"] = ident
                    newrow["type"] = actype
                elif 5 <= subtype <= 8:
                    (ground_track, decoded_lat, decoded_lon, rnge, bearing) = air_modes.parseBDS06(msg.data, self._cpr)
                    newrow["heading"] = ground_track
                    newrow["latitude"] = decoded_lat
                    newrow["longitude"] = decoded_lon
                    newrow["altitude"] = 0
                    if rnge is not None:
                        newrow["range"] = rnge
                        newrow["bearing"] = bearing
                elif 9 <= subtype <= 18:
                    (altitude, decoded_lat, decoded_lon, rnge, bearing) = air_modes.parseBDS05(msg.data, self._cpr)
                    newrow["altitude"] = altitude
                    newrow["latitude"] = decoded_lat
                    newrow["longitude"] = decoded_lon
                    if rnge is not None:
                        newrow["range"] = rnge
                        newrow["bearing"] = bearing
                elif subtype == 19:
                    subsubtype = msg.data["sub"]
                    velocity = None
                    heading = None
                    vert_spd = None
                    if subsubtype == 0:
                        (velocity, heading, vert_spd) = air_modes.parseBDS09_0(msg.data)
                    elif 1 <= subsubtype <= 2:
                        (velocity, heading, vert_spd) = air_modes.parseBDS09_1(msg.data)
                    newrow["speed"] = velocity
                    newrow["heading"] = heading
                    newrow["vertical"] = vert_spd
    
                self.model.addRecord(newrow)

        except ADSBError:
            return


########NEW FILE########
__FILENAME__ = html_template
#!/usr/bin/env python
#HTML template for Mode S map display
#Nick Foster, 2013

def html_template(my_position, json_file):
    if my_position is None:
        my_position = [37, -122]

    return """
<html>
    <head>
        <title>ADS-B Aircraft Map</title>
        <meta name="viewport" content="initial-scale=1.0, user-scalable=no" />
        <meta http-equiv="content-type" content="text/html;charset=utf-8" />
        <style type="text/css">
            .labels {
                color: blue;
                background-color: white;
                font-family: "Lucida Grande", "Arial", sans-serif;
                font-size: 13px;
                font-weight: bold;
                text-align: center;
                width: 70px;
                border: none;
                white-space: nowrap;
            }
        </style>
        <script type="text/javascript" src="http://maps.google.com/maps/api/js?sensor=false">
        </script>
        <script type="text/javascript" src="http://google-maps-utility-library-v3.googlecode.com/svn/tags/markerwithlabel/1.1.9/src/markerwithlabel.js">
        </script>
        <script type="text/javascript">
            var map;
            var markers = [];
            var defaultLocation = new google.maps.LatLng(%f, %f);
            var defaultZoomLevel = 9;

            function requestJSONP() {
                var script = document.createElement("script");
                script.src = "%s?" + Math.random();
                script.params = Math.random();
                document.getElementsByTagName('head')[0].appendChild(script);
            };

            var planeMarker;
            var planes = [];

            function clearMarkers() {
                for (var i = 0; i < planes.length; i++) {
                    planes[i].setMap(null);
                }
                planes = [];
            };

            function jsonp_callback(results) { // from JSONP
                clearMarkers();
                airplanes = {};
                for (var i = 0; i < results.length; i++) {
                    airplanes[results[i].icao] = {
                        center: new google.maps.LatLng(results[i].lat, results[i].lon),
                        heading: results[i].hdg,
                        altitude: results[i].alt,
                        type: results[i].type,
                        ident: results[i].ident,
                        speed: results[i].speed,
                        vertical: results[i].vertical,
                        highlight: results[i].highlight
                    };
                }
                refreshIcons();
            }

            function refreshIcons() {
                for (var airplane in airplanes) {
                    if (airplanes[airplane].highlight != 0) {
                        icon_file = "http://www.nerdnetworks.org/~bistromath/airplane_sprite_highlight.png";
                    } else {
                        icon_file = "http://www.nerdnetworks.org/~bistromath/airplane_sprite.png";
                    };
                    var plane_icon = {
                        url: icon_file,
                        size: new google.maps.Size(128,128),
                        origin: new google.maps.Point(parseInt(airplanes[airplane].heading/10)*128,0),
                        anchor: new google.maps.Point(64,64),
                        //scaledSize: new google.maps.Size(4608,126)
                    };

                    if (airplanes[airplane].ident.length != 8) {
                        identstr = airplane; 
                    } else {
                        identstr = airplanes[airplane].ident;
                    };

                    var planeOptions = {
                        map: map,
                        position: airplanes[airplane].center,
                        icon: plane_icon,
                        labelContent: identstr,
                        labelAnchor: new google.maps.Point(35, -32),
                        labelClass: "labels",
                        labelStyle: {opacity: 0.75}
                    };
                    planeMarker = new MarkerWithLabel(planeOptions);
                    planes.push(planeMarker);
                };
            };

            function initialize()
            {
                var myOptions =
                {
                    zoom: defaultZoomLevel,
                    center: defaultLocation,
                    disableDefaultUI: true,
                    mapTypeId: google.maps.MapTypeId.TERRAIN
                };

                map = new google.maps.Map(document.getElementById("map_canvas"), myOptions);

                requestJSONP();
                setInterval("requestJSONP()", 1000);
            };
        </script>
    </head>
    <body onload="initialize()">
        <div id="map_canvas" style="width:100%%; height:100%%">
        </div>
    </body>
</html>""" % (my_position[0], my_position[1], json_file)

########NEW FILE########
__FILENAME__ = kml
#
# Copyright 2010 Nick Foster
# 
# This file is part of gr-air-modes
# 
# gr-air-modes is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 3, or (at your option)
# any later version.
# 
# gr-air-modes is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
# 
# You should have received a copy of the GNU General Public License
# along with gr-air-modes; see the file COPYING.  If not, write to
# the Free Software Foundation, Inc., 51 Franklin Street,
# Boston, MA 02110-1301, USA.
# 

import sqlite3
import string, math, threading, time

class output_kml(threading.Thread):
    def __init__(self, filename, dbname, localpos, lock, timeout=5):
        threading.Thread.__init__(self)
        self._dbname = dbname
        self._filename = filename
        self.my_coords = localpos
        self._timeout = timeout
        self._lock = lock

        self.shutdown = threading.Event()
        self.finished = threading.Event()
        self.setDaemon(1)
        self.start()

    def run(self):
        self._db = sqlite3.connect(self._dbname) #read from the db
        while self.shutdown.is_set() is False:
            time.sleep(self._timeout)
            self.writekml()

        self._db.close()
        self._db = None
        self.finished.set()

    def close(self):
        self.shutdown.set()
        self.finished.wait(0.2)
        #there's a bug here where self._timeout is long and close() has
        #to wait for the sleep to expire before closing. we just bail
        #instead with the 0.2 param above.


    def writekml(self):
        kmlstr = self.genkml()
        if kmlstr is not None:
            f = open(self._filename, 'w')
            f.write(kmlstr)
            f.close()

    def locked_execute(self, c, query):
        with self._lock:
            c.execute(query)

    def draw_circle(self, center, rng):
        retstr = ""
        steps=30
        #so we're going to do this by computing a bearing angle based on the steps, and then compute the coordinate of a line extended from the center point to that range.
        [center_lat, center_lon] = center
        esquared = (1/298.257223563)*(2-(1/298.257223563))
        earth_radius_mi = 3963.19059

        #here we figure out the circumference of the latitude ring
        #which tells us how wide one line of longitude is at our latitude
        lat_circ = earth_radius_mi * math.cos(center_lat)
        #the circumference of the longitude ring will be equal to the circumference of the earth

        lat_rad = math.radians(center_lat)
        lon_rad = math.radians(center_lon)

        tmp0 = rng / earth_radius_mi

        for i in range(0, steps+1):
            bearing = i*(2*math.pi/steps) #in radians
            lat_out = math.degrees(math.asin(math.sin(lat_rad)*math.cos(tmp0) + math.cos(lat_rad)*math.sin(tmp0)*math.cos(bearing)))
            lon_out = center_lon + math.degrees(math.atan2(math.sin(bearing)*math.sin(tmp0)*math.cos(lat_rad), math.cos(tmp0)-math.sin(lat_rad)*math.sin(math.radians(lat_out))))
            retstr += " %.8f,%.8f, 0" % (lon_out, lat_out,)

        retstr = string.lstrip(retstr)
        return retstr

    def genkml(self):
        #first let's draw the static content
        retstr="""<?xml version="1.0" encoding="UTF-8"?>\n<kml xmlns="http://www.opengis.net/kml/2.2">\n<Document>\n\t<Style id="airplane">\n\t\t<IconStyle>\n\t\t\t<Icon><href>airports.png</href></Icon>\n\t\t</IconStyle>\n\t</Style>\n\t<Style id="rangering">\n\t<LineStyle>\n\t\t<color>9f4f4faf</color>\n\t\t<width>2</width>\n\t</LineStyle>\n\t</Style>\n\t<Style id="track">\n\t<LineStyle>\n\t\t<color>5fff8f8f</color>\n\t\t<width>4</width>\n\t</LineStyle>\n\t</Style>"""

        if self.my_coords is not None:
            retstr += """\n\t<Folder>\n\t\t<name>Range rings</name>\n\t\t<open>0</open>"""
            for rng in [100, 200, 300]:     
                retstr += """\n\t\t<Placemark>\n\t\t\t<name>%inm</name>\n\t\t\t<styleUrl>#rangering</styleUrl>\n\t\t\t<LinearRing>\n\t\t\t\t<coordinates>%s</coordinates>\n\t\t\t</LinearRing>\n\t\t</Placemark>""" % (rng, self.draw_circle(self.my_coords, rng),)
            retstr += """\t</Folder>\n"""

        retstr +=  """\t<Folder>\n\t\t<name>Aircraft locations</name>\n\t\t<open>0</open>"""

        #read the database and add KML
        q = "select distinct icao from positions where seen > datetime('now', '-5 minute')"
        c = self._db.cursor()
        self.locked_execute(c, q)
        icaolist = c.fetchall()
        #now we have a list icaolist of all ICAOs seen in the last 5 minutes

        for icao in icaolist:
            #print "ICAO: %x" % icao
            q = "select * from positions where icao=%i and seen > datetime('now', '-2 hour') ORDER BY seen DESC" % icao
            self.locked_execute(c, q)
            track = c.fetchall()
            #print "Track length: %i" % len(track)
            if len(track) != 0:
                lat = track[0][3]
                if lat is None: lat = 0
                lon = track[0][4]
                if lon is None: lon = 0
                alt = track[0][2]
                if alt is None: alt = 0

                metric_alt = alt * 0.3048 #google earth takes meters, the commie bastards

                trackstr = ""

                for pos in track:
                    trackstr += " %f,%f,%f" % (pos[4], pos[3], pos[2]*0.3048)

                trackstr = string.lstrip(trackstr)
            else:
                alt = 0
                metric_alt = 0
                lat = 0
                lon = 0
                trackstr = str("")

            #now get metadata
            q = "select ident from ident where icao=%i" % icao
            self.locked_execute(c, q)
            r = c.fetchall()
            if len(r) != 0:
                ident = r[0][0]
            else: ident=""
            #if ident is None: ident = ""
            #get most recent speed/heading/vertical
            q = "select seen, speed, heading, vertical from vectors where icao=%i order by seen desc limit 1" % icao
            self.locked_execute(c, q)
            r = c.fetchall()
            if len(r) != 0:
                seen = r[0][0]
                speed = r[0][1]
                heading = r[0][2]
                vertical = r[0][3]

            else:
                seen = 0
                speed = 0
                heading = 0
                vertical = 0
            #now generate some KML
            retstr+= "\n\t\t<Placemark>\n\t\t\t<name>%s</name>\n\t\t\t<Style><IconStyle><heading>%i</heading></IconStyle></Style>\n\t\t\t<styleUrl>#airplane</styleUrl>\n\t\t\t<description>\n\t\t\t\t<![CDATA[Altitude: %s<br/>Heading: %i<br/>Speed: %i<br/>Vertical speed: %i<br/>ICAO: %x<br/>Last seen: %s]]>\n\t\t\t</description>\n\t\t\t<Point>\n\t\t\t\t<altitudeMode>absolute</altitudeMode>\n\t\t\t\t<extrude>1</extrude>\n\t\t\t\t<coordinates>%s,%s,%i</coordinates>\n\t\t\t</Point>\n\t\t</Placemark>" % (ident, heading, alt, heading, speed, vertical, icao[0], seen, lon, lat, metric_alt, )

            retstr+= "\n\t\t<Placemark>\n\t\t\t<styleUrl>#track</styleUrl>\n\t\t\t<LineString>\n\t\t\t\t<extrude>0</extrude>\n\t\t\t\t<altitudeMode>absolute</altitudeMode>\n\t\t\t\t<coordinates>%s</coordinates>\n\t\t\t</LineString>\n\t\t</Placemark>" % (trackstr,)

        retstr+= '\n\t</Folder>\n</Document>\n</kml>'
        return retstr

#we just inherit from output_kml because we're doing the same thing, only in a different format.
class output_jsonp(output_kml):
    def set_highlight(self, icao):
        self.highlight = icao

    def genkml(self):
        retstr="""jsonp_callback(["""

#        if self.my_coords is not None:
#            retstr += """\n\t<Folder>\n\t\t<name>Range rings</name>\n\t\t<open>0</open>"""
#            for rng in [100, 200, 300]:
#                retstr += """\n\t\t<Placemark>\n\t\t\t<name>%inm</name>\n\t\t\t<styleUrl>#rangering</styleUrl>\n\t\t\t<LinearRing>\n\t\t\t\t<coordinates>%s</coordinates>\n\t\t\t</LinearRing>\n\t\t</Placemark>""" % (rng, self.draw_circle(self.my_coords, rng),)
#            retstr += """\t</Folder>\n"""

#        retstr +=  """\t<Folder>\n\t\t<name>Aircraft locations</name>\n\t\t<open>0</open>"""

        #read the database and add KML
        q = "select distinct icao from positions where seen > datetime('now', '-1 minute')"
        c = self._db.cursor()
        self.locked_execute(c, q)
        icaolist = c.fetchall()
        #now we have a list icaolist of all ICAOs seen in the last 5 minutes

        for icao in icaolist:
            icao = icao[0]

            #now get metadata
            q = "select ident, type from ident where icao=%i" % icao
            self.locked_execute(c, q)
            r = c.fetchall()
            if len(r) != 0:
                ident = r[0][0]
                actype = r[0][1]
            else: 
                ident=""
                actype = ""
            if ident is None: ident = ""
            #get most recent speed/heading/vertical
            q = "select seen, speed, heading, vertical from vectors where icao=%i order by seen desc limit 1" % icao
            self.locked_execute(c, q)
            r = c.fetchall()
            if len(r) != 0:
                seen = r[0][0]
                speed = r[0][1]
                heading = r[0][2]
                vertical = r[0][3]

            else:
                seen = 0
                speed = 0
                heading = 0
                vertical = 0

            q = "select lat, lon, alt from positions where icao=%i order by seen desc limit 1" % icao
            self.locked_execute(c, q)
            r = c.fetchall()
            if len(r) != 0:
                lat = r[0][0]
                lon = r[0][1]
                alt = r[0][2]
            else:
                lat = 0
                lon = 0
                alt = 0

            highlight = 0
            if hasattr(self, 'highlight'):
                if self.highlight == icao:
                    highlight = 1

            #now generate some JSONP
            retstr+= """{"icao": "%.6x", "lat": %f, "lon": %f, "alt": %i, "hdg": %i, "speed": %i, "vertical": %i, "ident": "%s", "type": "%s", "highlight": %i},""" % (icao, lat, lon, alt, heading, speed, vertical, ident, actype, highlight)

        retstr+= """]);"""
        return retstr

########NEW FILE########
__FILENAME__ = mlat
#!/usr/bin/python
import math
import numpy
from scipy.ndimage import map_coordinates

#functions for multilateration.
#this library is more or less based around the so-called "GPS equation", the canonical
#iterative method for getting position from GPS satellite time difference of arrival data.
#here, instead of multiple orbiting satellites with known time reference and position,
#we have multiple fixed stations with known time references (GPSDO, hopefully) and known
#locations (again, GPSDO).

#NB: because of the way this solver works, at least 3 stations and timestamps
#are required. this function will not return hyperbolae for underconstrained systems.
#TODO: get HDOP out of this so we can draw circles of likely position and indicate constraint
########################END NOTES#######################################


#this is a 10x10-degree WGS84 geoid datum, in meters relative to the WGS84 reference ellipsoid. given the maximum slope, you should probably interpolate.
#NIMA suggests a 2x2 interpolation using four neighbors. we'll go cubic spline JUST BECAUSE WE CAN
wgs84_geoid = numpy.array([[13,13,13,13,13,13,13,13,13,13,13,13,13,13,13,13,13,13,13,13,13,13,13,13,13,13,13,13,13,13,13,13,13,13,13,13],                       #90N
               [3,1,-2,-3,-3,-3,-1,3,1,5,9,11,19,27,31,34,33,34,33,34,28,23,17,13,9,4,4,1,-2,-2,0,2,3,2,1,1],                                       #80N
               [2,2,1,-1,-3,-7,-14,-24,-27,-25,-19,3,24,37,47,60,61,58,51,43,29,20,12,5,-2,-10,-14,-12,-10,-14,-12,-6,-2,3,6,4],                    #70N
               [2,9,17,10,13,1,-14,-30,-39,-46,-42,-21,6,29,49,65,60,57,47,41,21,18,14,7,-3,-22,-29,-32,-32,-26,-15,-2,13,17,19,6],                 #60N
               [-8,8,8,1,-11,-19,-16,-18,-22,-35,-40,-26,-12,24,45,63,62,59,47,48,42,28,12,-10,-19,-33,-43,-42,-43,-29,-2,17,23,22,6,2],            #50N
               [-12,-10,-13,-20,-31,-34,-21,-16,-26,-34,-33,-35,-26,2,33,59,52,51,52,48,35,40,33,-9,-28,-39,-48,-59,-50,-28,3,23,37,18,-1,-11],     #40N
               [-7,-5,-8,-15,-28,-40,-42,-29,-22,-26,-32,-51,-40,-17,17,31,34,44,36,28,29,17,12,-20,-15,-40,-33,-34,-34,-28,7,29,43,20,4,-6],       #30N
               [5,10,7,-7,-23,-39,-47,-34,-9,-10,-20,-45,-48,-32,-9,17,25,31,31,26,15,6,1,-29,-44,-61,-67,-59,-36,-11,21,39,49,39,22,10],           #20N
               [13,12,11,2,-11,-28,-38,-29,-10,3,1,-11,-41,-42,-16,3,17,33,22,23,2,-3,-7,-36,-59,-90,-95,-63,-24,12,53,60,58,46,36,26],             #10N
               [22,16,17,13,1,-12,-23,-20,-14,-3,14,10,-15,-27,-18,3,12,20,18,12,-13,-9,-28,-49,-62,-89,-102,-63,-9,33,58,73,74,63,50,32],          #0
               [36,22,11,6,-1,-8,-10,-8,-11,-9,1,32,4,-18,-13,-9,4,14,12,13,-2,-14,-25,-32,-38,-60,-75,-63,-26,0,35,52,68,76,64,52],                #10S
               [51,27,10,0,-9,-11,-5,-2,-3,-1,9,35,20,-5,-6,-5,0,13,17,23,21,8,-9,-10,-11,-20,-40,-47,-45,-25,5,23,45,58,57,63],                    #20S
               [46,22,5,-2,-8,-13,-10,-7,-4,1,9,32,16,4,-8,4,12,15,22,27,34,29,14,15,15,7,-9,-25,-37,-39,-23,-14,15,33,34,45],                      #30S
               [21,6,1,-7,-12,-12,-12,-10,-7,-1,8,23,15,-2,-6,6,21,24,18,26,31,33,39,41,30,24,13,-2,-20,-32,-33,-27,-14,-2,5,20],                   #40S
               [-15,-18,-18,-16,-17,-15,-10,-10,-8,-2,6,14,13,3,3,10,20,27,25,26,34,39,45,45,38,39,28,13,-1,-15,-22,-22,-18,-15,-14,-10],           #50S
               [-45,-43,-37,-32,-30,-26,-23,-22,-16,-10,-2,10,20,20,21,24,22,17,16,19,25,30,35,35,33,30,27,10,-2,-14,-23,-30,-33,-29,-35,-43],      #60S
               [-61,-60,-61,-55,-49,-44,-38,-31,-25,-16,-6,1,4,5,4,2,6,12,16,16,17,21,20,26,26,22,16,10,-1,-16,-29,-36,-46,-55,-54,-59],            #70S
               [-53,-54,-55,-52,-48,-42,-38,-38,-29,-26,-26,-24,-23,-21,-19,-16,-12,-8,-4,-1,1,4,4,6,5,4,2,-6,-15,-24,-33,-40,-48,-50,-53,-52],     #80S
               [-30,-30,-30,-30,-30,-30,-30,-30,-30,-30,-30,-30,-30,-30,-30,-30,-30,-30,-30,-30,-30,-30,-30,-30,-30,-30,-30,-30,-30,-30,-30,-30,-30,-30,-30,-30]], #90S
               dtype=numpy.float)
               
#ok this calculates the geoid offset from the reference ellipsoid
#combined with LLH->ECEF this gets you XYZ for a ground-referenced point
def wgs84_height(lat, lon):
    yi = numpy.array([9-lat/10.0])
    xi = numpy.array([18+lon/10.0])
    return float(map_coordinates(wgs84_geoid, [yi, xi]))

#WGS84 reference ellipsoid constants
wgs84_a = 6378137.0
wgs84_b = 6356752.314245
wgs84_e2 = 0.0066943799901975848
wgs84_a2 = wgs84_a**2 #to speed things up a bit
wgs84_b2 = wgs84_b**2

#convert ECEF to lat/lon/alt without geoid correction
#returns alt in meters
def ecef2llh((x,y,z)):
    ep  = math.sqrt((wgs84_a2 - wgs84_b2) / wgs84_b2)
    p   = math.sqrt(x**2+y**2)
    th  = math.atan2(wgs84_a*z, wgs84_b*p)
    lon = math.atan2(y, x)
    lat = math.atan2(z+ep**2*wgs84_b*math.sin(th)**3, p-wgs84_e2*wgs84_a*math.cos(th)**3)
    N   = wgs84_a / math.sqrt(1-wgs84_e2*math.sin(lat)**2)
    alt = p / math.cos(lat) - N
    
    lon *= (180. / math.pi)
    lat *= (180. / math.pi)
    
    return [lat, lon, alt]

#convert lat/lon/alt coords to ECEF without geoid correction, WGS84 model
#remember that alt is in meters
def llh2ecef((lat, lon, alt)):
    lat *= (math.pi / 180.0)
    lon *= (math.pi / 180.0)
    
    n = lambda x: wgs84_a / math.sqrt(1 - wgs84_e2*(math.sin(x)**2))
    
    x = (n(lat) + alt)*math.cos(lat)*math.cos(lon)
    y = (n(lat) + alt)*math.cos(lat)*math.sin(lon)
    z = (n(lat)*(1-wgs84_e2)+alt)*math.sin(lat)
    
    return [x,y,z]
    
#do both of the above to get a geoid-corrected x,y,z position
def llh2geoid((lat, lon, alt)):
    (x,y,z) = llh2ecef((lat, lon, alt + wgs84_height(lat, lon)))
    return [x,y,z]


c = 299792458 / 1.0003 #modified for refractive index of air, why not

#this function is the iterative solver core of the mlat function below
#we use limit as a goal to stop solving when we get "close enough" (error magnitude in meters for that iteration)
#basically 20 meters is way less than the anticipated error of the system so it doesn't make sense to continue
#it's possible this could fail in situations where the solution converges slowly
#TODO: this fails to converge for some seriously advantageous geometry
def mlat_iter(rel_stations, prange_obs, xguess = [0,0,0], limit = 20, maxrounds = 100):
    xerr = [1e9, 1e9, 1e9]
    rounds = 0
    while numpy.linalg.norm(xerr) > limit:
        prange_est = [[numpy.linalg.norm(station - xguess)] for station in rel_stations]
        dphat = prange_obs - prange_est
        H = numpy.array([(numpy.array(-rel_stations[row,:])+xguess) / prange_est[row] for row in range(0,len(rel_stations))])
        #now we have H, the Jacobian, and can solve for residual error
        xerr = numpy.linalg.lstsq(H, dphat)[0].flatten()
        xguess += xerr
        #print xguess, xerr
        rounds += 1
        if rounds > maxrounds:
            raise Exception("Failed to converge!")
            break
    return xguess

#func mlat:
#uses a modified GPS pseudorange solver to locate aircraft by multilateration.
#replies is a list of reports, in ([lat, lon, alt], timestamp) format
#altitude is the barometric altitude of the aircraft as returned by the aircraft
#returns the estimated position of the aircraft in (lat, lon, alt) geoid-corrected WGS84.
#let's make it take a list of tuples so we can sort by them
def mlat(replies, altitude):
    sorted_replies = sorted(replies, key=lambda time: time[1])

    stations = [sorted_reply[0] for sorted_reply in sorted_replies]
    timestamps = [sorted_reply[1] for sorted_reply in sorted_replies]

    me_llh = stations[0]
    me = llh2geoid(stations[0])

    
    #list of stations in XYZ relative to me
    rel_stations = [numpy.array(llh2geoid(station)) - numpy.array(me) for station in stations[1:]]
    rel_stations.append([0,0,0] - numpy.array(me))
    rel_stations = numpy.array(rel_stations) #convert list of arrays to 2d array

    #differentiate the timestamps to get TDOA, multiply by c to get pseudorange
    prange_obs = [[c*(stamp-timestamps[0])] for stamp in timestamps[1:]]

    #so here we calc the estimated pseudorange to the center of the earth, using station[0] as a reference point for the geoid
    #in other words, we say "if the aircraft were directly overhead of station[0], this is the prange to the center of the earth"
    #this is a necessary approximation since we don't know the location of the aircraft yet
    #if the dang earth were actually round this wouldn't be an issue
    prange_obs.append( [numpy.linalg.norm(llh2ecef((me_llh[0], me_llh[1], altitude)))] ) #use ECEF not geoid since alt is MSL not GPS
    prange_obs = numpy.array(prange_obs)

    #xguess = llh2ecef([37.617175,-122.400843, 8000])-numpy.array(me)
    #xguess = [0,0,0]
    #start our guess directly overhead, who cares
    xguess = numpy.array(llh2ecef([me_llh[0], me_llh[1], altitude])) - numpy.array(me)
    
    xyzpos = mlat_iter(rel_stations, prange_obs, xguess)
    llhpos = ecef2llh(xyzpos+me)
    
    #now, we could return llhpos right now and be done with it.
    #but the assumption we made above, namely that the aircraft is directly above the
    #nearest station, results in significant error due to the oblateness of the Earth's geometry.
    #so now we solve AGAIN, but this time with the corrected pseudorange of the aircraft altitude
    #this might not be really useful in practice but the sim shows >50m errors without it
    #and <4cm errors with it, not that we'll get that close in reality but hey let's do it right
    prange_obs[-1] = [numpy.linalg.norm(llh2ecef((llhpos[0], llhpos[1], altitude)))]
    xyzpos_corr = mlat_iter(rel_stations, prange_obs, xyzpos) #start off with a really close guess
    llhpos = ecef2llh(xyzpos_corr+me)

    #and now, what the hell, let's try to get dilution of precision data
    #avec is the unit vector of relative ranges to the aircraft from each of the stations
#    for i in range(len(avec)):
#        avec[i] = numpy.array(avec[i]) / numpy.linalg.norm(numpy.array(avec[i]))
#    numpy.append(avec, [[-1],[-1],[-1],[-1]], 1) #must be # of stations
#    doparray = numpy.linalg.inv(avec.T*avec)
#the diagonal elements of doparray will be the x, y, z DOPs.
    
    return llhpos


if __name__ == '__main__':
    #here's some test data to validate the algorithm
    teststations = [[37.76225, -122.44254, 100], [37.680016,-121.772461, 100], [37.385844,-122.083082, 100], [37.701207,-122.309418, 100]]
    testalt      = 8000
    testplane    = numpy.array(llh2ecef([37.617175,-122.400843, testalt]))
    testme       = llh2geoid(teststations[0])
    teststamps   = [10, 
                    10 + numpy.linalg.norm(testplane-numpy.array(llh2geoid(teststations[1]))) / c,
                    10 + numpy.linalg.norm(testplane-numpy.array(llh2geoid(teststations[2]))) / c,
                    10 + numpy.linalg.norm(testplane-numpy.array(llh2geoid(teststations[3]))) / c,
                ]

    print teststamps

    replies = []
    for i in range(0, len(teststations)):
        replies.append((teststations[i], teststamps[i]))
    ans = mlat(replies, testalt)
    error = numpy.linalg.norm(numpy.array(llh2ecef(ans))-numpy.array(testplane))
    range = numpy.linalg.norm(llh2geoid(ans)-numpy.array(testme))
    print testplane-testme
    print ans
    print "Error: %.2fm" % (error)
    print "Range: %.2fkm (from first station in list)" % (range/1000)

########NEW FILE########
__FILENAME__ = mlat_client
#!/usr/bin/env python
#
# Copyright 2012 Nick Foster
# 
# This file is part of gr-air-modes
# 
# gr-air-modes is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 3, or (at your option)
# any later version.
# 
# gr-air-modes is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
# 
# You should have received a copy of the GNU General Public License
# along with gr-air-modes; see the file COPYING.  If not, write to
# the Free Software Foundation, Inc., 51 Franklin Street,
# Boston, MA 02110-1301, USA.
#

#multilateration client
#outputs stamps to server, receives multilaterated outputs back

import socket, pickle, time, sys
import air_modes
from gnuradio import gr

pickle_prot = 0
#pickle_prot = pickle.HIGHEST_PROTOCOL

class client_info:
    def __init__(self):
        self.name = ""
        self.position = []
        self.offset_secs = 0
        self.offset_frac_secs = 0.0
        self.time_source = None  

class mlat_client:
    def __init__(self, queue, position, server_addr, time_source):
        self._queue = queue
        self._pos = position
        self._name = socket.gethostname()
        #connect to server
        self._sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self._sock.setblocking(1)
        self._sock.connect((server_addr, 19005))
        info = client_info()
        info.name = self._name
        info.position = self._pos
        info.time_source = time_source #"gpsdo" or None
        self._sock.send(pickle.dumps(info))
        reply = self._sock.recv(1024)
        if reply != "HELO": #i know, shut up
            raise Exception("Invalid reply from server: %s" % reply)
        self._sock.setblocking(0)
        self._remnant = None

    def __del__(self):
        self._sock.close()

    #send a stamped report to the server
    def output(self, message):
        self._sock.send(message+"\n")

    #this is called from the update() method list of the main app thread
    def get_mlat_positions(self):
        msg = None
        try:
            msg = self._sock.recv(1024)
        except socket.error:
            pass
        if msg:
            for line in msg.splitlines(True):
                if line.endswith("\n"):
                    if self._remnant:
                        line = self._remnant + line
                        self._remnant = None
                    self._queue.insert_tail(gr.message_from_string(line))

                else:
                    if self._remnant is not None:
                        raise Exception("Malformed data: " + line)
                    else:
                        self._remnant = line

########NEW FILE########
__FILENAME__ = mlat_types


########NEW FILE########
__FILENAME__ = msprint
#
# Copyright 2010, 2012 Nick Foster
# 
# This file is part of gr-air-modes
# 
# gr-air-modes is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 3, or (at your option)
# any later version.
# 
# gr-air-modes is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
# 
# You should have received a copy of the GNU General Public License
# along with gr-air-modes; see the file COPYING.  If not, write to
# the Free Software Foundation, Inc., 51 Franklin Street,
# Boston, MA 02110-1301, USA.
# 

import time, os, sys
from string import split, join
import air_modes
from air_modes.exceptions import *
import math

#TODO get rid of class and convert to functions
#no need for class here
class output_print:
  def __init__(self, cpr, publisher, callback=None):
    self._cpr = cpr
    self._callback = callback
    #sub to every function that starts with "handle"
    self._fns = [int(l[6:]) for l in dir(self) if l.startswith("handle")]
    for i in self._fns:
      publisher.subscribe("type%i_dl" % i, getattr(self, "handle%i" % i))
    
    publisher.subscribe("modes_dl", self.catch_nohandler)

  @staticmethod
  def prefix(msg):
    return "(%i %.8f) " % (msg.rssi, msg.timestamp)

  def _print(self, msg):
    if self._callback is None:
        print msg
    else:
        self._callback(msg)

  def catch_nohandler(self, msg):
    if msg.data.get_type() not in self._fns:
      retstr = output_print.prefix(msg)
      retstr += "No handler for message type %i" % msg.data.get_type()
      if "aa" not in msg.data.fields:
        retstr += " from %.6x" % msg.ecc
      else:
        retstr += " from %.6x" % msg.data["aa"]
      self._print(retstr)
      
  def handle0(self, msg):
    try:
      retstr = output_print.prefix(msg)
      retstr += "Type 0 (short A-A surveillance) from %x at %ift" % (msg.ecc, air_modes.decode_alt(msg.data["ac"], True))
      ri = msg.data["ri"]
      if ri == 0:
        retstr += " (No TCAS)"
      elif ri == 2:
        retstr += " (TCAS resolution inhibited)"
      elif ri == 3:
        retstr += " (Vertical TCAS resolution only)"
      elif ri == 4:
        retstr += " (Full TCAS resolution)"
      elif ri == 9:
        retstr += " (speed <75kt)"
      elif ri > 9:
        retstr += " (speed %i-%ikt)" % (75 * (1 << (ri-10)), 75 * (1 << (ri-9)))
      else:
        raise ADSBError

    except ADSBError:
        return

    if msg.data["vs"] is 1:
      retstr += " (aircraft is on the ground)"

    self._print(retstr)

  @staticmethod
  def fs_text(fs):
    if fs == 1:
      return " (aircraft is on the ground)"
    elif fs == 2:
      return " (AIRBORNE ALERT)"
    elif fs == 3:
      return " (GROUND ALERT)"
    elif fs == 4:
      return " (SPI ALERT)"
    elif fs == 5:
      return " (SPI)"
    else:
      raise ADSBError

  def handle4(self, msg):
    try:
      retstr = output_print.prefix(msg)
      retstr += "Type 4 (short surveillance altitude reply) from %x at %ift" % (msg.ecc, air_modes.decode_alt(msg.data["ac"], True))
      retstr += output_print.fs_text(msg.data["fs"])    
    except ADSBError:
      return
    self._print(retstr)

  def handle5(self, msg):
    try:
      retstr = output_print.prefix(msg)
      retstr += "Type 5 (short surveillance ident reply) from %x with ident %i" % (msg.ecc, air_modes.decode_id(msg.data["id"]))
      retstr += output_print.fs_text(msg.data["fs"])
    except ADSBError:
      return
    self._print(retstr)

  def handle11(self, msg):
    try:
      retstr = output_print.prefix(msg)
      retstr += "Type 11 (all call reply) from %x in reply to interrogator %i with capability level %i" % (msg.data["aa"], msg.ecc & 0xF, msg.data["ca"]+1)
    except ADSBError:
      return
    self._print(retstr)

  #the only one which requires state
  def handle17(self, msg):
    icao24 = msg.data["aa"]
    bdsreg = msg.data["me"].get_type()

    retstr = output_print.prefix(msg)
    try:
        if bdsreg == 0x08:
          (ident, typestring) = air_modes.parseBDS08(msg.data)
          retstr += "Type 17 BDS0,8 (ident) from %x type %s ident %s" % (icao24, typestring, ident)

        elif bdsreg == 0x06:
          [ground_track, decoded_lat, decoded_lon, rnge, bearing] = air_modes.parseBDS06(msg.data, self._cpr)
          retstr += "Type 17 BDS0,6 (surface report) from %x at (%.6f, %.6f) ground track %i" % (icao24, decoded_lat, decoded_lon, ground_track)
          if rnge is not None and bearing is not None:
            retstr += " (%.2f @ %.0f)" % (rnge, bearing)

        elif bdsreg == 0x05:
          [altitude, decoded_lat, decoded_lon, rnge, bearing] = air_modes.parseBDS05(msg.data, self._cpr)
          retstr += "Type 17 BDS0,5 (position report) from %x at (%.6f, %.6f)" % (icao24, decoded_lat, decoded_lon)
          if rnge is not None and bearing is not None:
            retstr += " (" + "%.2f" % rnge + " @ " + "%.0f" % bearing + ")"
          retstr += " at " + str(altitude) + "ft"

        elif bdsreg == 0x09:
          subtype = msg.data["bds09"].get_type()
          if subtype == 0:
            [velocity, heading, vert_spd, turnrate] = air_modes.parseBDS09_0(msg.data)
            retstr += "Type 17 BDS0,9-%i (track report) from %x with velocity %.0fkt heading %.0f VS %.0f turn rate %.0f" \
                     % (subtype, icao24, velocity, heading, vert_spd, turnrate)
          elif subtype == 1:
            [velocity, heading, vert_spd] = air_modes.parseBDS09_1(msg.data)
            retstr += "Type 17 BDS0,9-%i (track report) from %x with velocity %.0fkt heading %.0f VS %.0f" % (subtype, icao24, velocity, heading, vert_spd)
          elif subtype == 3:
            [mag_hdg, vel_src, vel, vert_spd, geo_diff] = air_modes.parseBDS09_3(msg.data)
            retstr += "Type 17 BDS0,9-%i (air course report) from %x with %s %.0fkt magnetic heading %.0f VS %.0f geo. diff. from baro. alt. %.0fft" \
                     % (subtype, icao24, vel_src, vel, mag_hdg, vert_spd, geo_diff)

          else:
            retstr += "Type 17 BDS0,9-%i from %x not implemented" % (subtype, icao24)

        elif bdsreg == 0x62:
          emerg_str = air_modes.parseBDS62(data)
          retstr += "Type 17 BDS6,2 (emergency) from %x type %s" % (icao24, emerg_str)

        else:
          retstr += "Type 17 with FTC=%i from %x not implemented" % (msg.data["ftc"], icao24)
    except ADSBError:
        return

    self._print(retstr)

  def printTCAS(self, msg):
    msgtype = msg.data["df"]

    if msgtype == 16:
      bds1 = msg.data["vds1"]
      bds2 = msg.data["vds2"]
    else:
      bds1 = msg.data["bds1"]
      bds2 = msg.data["bds2"]

    retstr = output_print.prefix(msg)

    if bds2 != 0:
      retstr += "No handler in type %i for BDS2 == %i from %x" % (msgtype, bds2, msg.ecc)

    elif bds1 == 0:
      retstr += "No handler in type %i for BDS1 == 0 from %x" % (msgtype, msg.ecc)
    elif bds1 == 1:
      retstr += "Type %i link capability report from %x: ACS: 0x%x, BCS: 0x%x, ECS: 0x%x, continues %i" \
                % (msgtype, msg.ecc, msg.data["acs"], msg.data["bcs"], msg.data["ecs"], msg.data["cfs"])
    elif bds1 == 2:
      retstr += "Type %i identification from %x with text %s" % (msgtype, msg.ecc, air_modes.parseMB_id(msg.data))
    elif bds1 == 3:
      retstr += "Type %i TCAS report from %x: " % (msgtype, msg.ecc)
      tti = msg.data["tti"]
      if msgtype == 16:
        (resolutions, complements, rat, mte) = air_modes.parse_TCAS_CRM(msg.data)
        retstr += "advised: %s complement: %s" % (resolutions, complements)
      else:
          if tti == 1:
            (resolutions, complements, rat, mte, threat_id) = air_modes.parseMB_TCAS_threatid(msg.data)
            retstr += "threat ID: %x advised: %s complement: %s" % (threat_id, resolutions, complements)
          elif tti == 2:
            (resolutions, complements, rat, mte, threat_alt, threat_range, threat_bearing) = air_modes.parseMB_TCAS_threatloc(msg.data)
            retstr += "range: %i bearing: %i alt: %i advised: %s complement: %s" % (threat_range, threat_bearing, threat_alt, resolutions, complements)
          else:
            rat = 0
            mte = 0
            retstr += " (no handler for TTI=%i)" % tti
      if mte == 1:
        retstr += " (multiple threats)"
      if rat == 1:
        retstr += " (resolved)"
    else:
      retstr += "No handler for type %i, BDS1 == %i from %x" % (msgtype, bds1, msg.ecc)

    if(msgtype == 20 or msgtype == 16):
      retstr += " at %ift" % air_modes.decode_alt(msg.data["ac"], True)
    else:
      retstr += " ident %x" % air_modes.decode_id(msg.data["id"])

    self._print(retstr)

  handle16 = printTCAS
  handle20 = printTCAS
  handle21 = printTCAS

########NEW FILE########
__FILENAME__ = parse
#
# Copyright 2010, 2012 Nick Foster
# 
# This file is part of gr-air-modes
# 
# gr-air-modes is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 3, or (at your option)
# any later version.
# 
# gr-air-modes is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
# 
# You should have received a copy of the GNU General Public License
# along with gr-air-modes; see the file COPYING.  If not, write to
# the Free Software Foundation, Inc., 51 Franklin Street,
# Boston, MA 02110-1301, USA.
#

import time, os, sys
from string import split, join
from altitude import decode_alt
import math
import air_modes
from air_modes.exceptions import *

#this implements a packet class which can retrieve its own fields.
class data_field:
  def __init__(self, data):
    self.data = data
    self.fields = self.parse()

  types = { }
  offset = 1   #field offset applied to all fields. used for offsetting
               #subtypes to reconcile with the spec. Really just for readability.

  #get a particular field from the data
  def __getitem__(self, fieldname):
    mytype = self.get_type()
    if mytype in self.types:
      if fieldname in self.fields: #verify it exists in this packet type
        return self.fields[fieldname]
      else:
        raise FieldNotInPacket(fieldname)
    else:
      raise NoHandlerError(mytype)

  #grab all the fields in the packet as a dict
  #done once on init so you don't have to iterate down every time you grab a field
  def parse(self):
    fields = {}
    mytype = self.get_type()
    if mytype in self.types:
      for field in self.types[mytype]:
        bits = self.types[self.get_type()][field]
        if len(bits) == 3:
          obj = bits[2](self.get_bits(bits[0], bits[1]))
          fields.update(obj.parse())
          fields.update({field: obj})
        else:
          fields.update({field: self.get_bits(bits[0], bits[1])})
    else:
      raise NoHandlerError(mytype)
    return fields

  def get_type(self):
    raise NotImplementedError

  def get_numbits(self):
    raise NotImplementedError

  #retrieve bits from data given the offset and number of bits.
  #the offset is both left-justified (LSB) and starts at 1, to
  #correspond to the Mode S spec. Blame them.
  def get_bits(self, *args):
    startbit = args[0]
    num = args[1]
    bits = 0
    try:
      bits = (self.data \
        >> (self.get_numbits() - startbit - num + self.offset)) \
         & ((1 << num) - 1)
    #the exception handler catches instances when you try to shift more than
    #the number of bits. this can happen when a garbage packet gets through
    #which reports itself as a short packet but of type long.
    #TODO: should find more productive way to throw this out
    except ValueError:
      pass
      #print "Short packet received for long packet type: %x" % self.data
    return bits

class bds09_reply(data_field):
  offset = 6
  types = {  #BDS0,9 subtype 0
             0: {"sub": (6,3), "dew": (10,1), "vew": (11,11), "dns": (22,1),
                 "vns": (23,11), "str": (34,1), "tr": (35,6), "dvr": (41,1),
                 "vr": (42,9)},
             #BDS0,9 subtypes 1-2 (differ only in velocity encoding)
             1: {"sub": (6,3), "icf": (9,1), "ifr": (10,1), "nuc": (11,3),
                 "dew": (14,1), "vew": (15,10), "dns": (25,1), "vns": (26,10),
                 "vrsrc": (36,1), "dvr": (37,1), "vr": (38,9), "dhd": (49,1), "hd": (50,6)},
             #BDS0,9 subtype 3-4 (airspeed and heading)
             3: {"sub": (6,3), "icf": (9,1), "ifr": (10,1), "nuc": (11,3), "mhs": (14,1),
                 "hdg": (15,10), "ast": (25,1), "spd": (26,10), "vrsrc": (36,1),
                 "dvr": (37,1), "vr": (38,9), "dhd": (49,1), "hd": (50,6)}
          }

  def get_type(self):
    sub = self.get_bits(6,3)
    if sub == 0:
      return 0
    if 1 <= sub <= 2:
      return 1
    if 3 <= sub <= 4:
      return 3

  def get_numbits(self):
    return 51

#type 17 extended squitter data
class me_reply(data_field):
  #types in this format are listed by BDS register
  #TODO: add comments explaining these fields
  types = { 0x05: {"ftc": (1,5), "ss": (6,2), "saf": (8,1), "alt": (9,12), "time": (21,1), "cpr": (22,1), "lat": (23,17), "lon": (40,17)}, #airborne position
            0x06: {"ftc": (1,5), "mvt": (6,7), "gts": (13,1), "gtk": (14,7), "time": (21,1), "cpr": (22,1), "lat": (23,17), "lon": (40,17)}, #surface position
            0x07: {"ftc": (1,5),}, #TODO extended squitter status
            0x08: {"ftc": (1,5), "cat": (6,3), "ident": (9,48)}, #extended squitter identification and type
            0x09: {"ftc": (1,5), "bds09": (6,51, bds09_reply)},
            #0x0A: data link capability report
            #0x17: common usage capability report
            #0x18-0x1F: Mode S specific services capability report
            #0x20: aircraft identification
            0x61: {"ftc": (1,5), "eps": (9,3)}
          }

  #maps ftc to BDS register
  def get_type(self):
    ftc = self.get_bits(1,5)
    if 1 <= ftc <= 4:
      return 0x08
    elif 5 <= ftc <= 8:
      return 0x06
    elif 9 <= ftc <= 18 and ftc != 15: #FTC 15 does not appear to be valid
      return 0x05
    elif ftc == 19:
      return 0x09
    elif ftc == 28:
      return 0x61
    else:
      return NoHandlerError(ftc)
    
  def get_numbits(self):
    return 56

#resolves the TCAS reply types from TTI info
class tcas_reply(data_field):
  offset = 61
  types = { 0: {"tti": (61,2)}, #UNKNOWN
            1: {"tti": (61,2), "tid": (63,26)},
            2: {"tti": (61,2), "tida": (63,13), "tidr": (76,7), "tidb": (83,6)}
          }
  def get_type(self):
    return self.get_bits(61,2)

  def get_numbits(self):
    return 28

#extended squitter types 20,21 MB subfield
class mb_reply(data_field):
  offset = 33 #fields offset by 33 to match documentation
  #types are based on bds1 subfield
  types = { 0: {"bds1": (33,4), "bds2": (37,4)}, #TODO
            1: {"bds1": (33,4), "bds2": (37,4), "cfs": (41,4), "acs": (45,20), "bcs": (65,16), "ecs": (81,8)},
            2: {"bds1": (33,4), "bds2": (37,4), "ais": (41,48)},
            3: {"bds1": (33,4), "bds2": (37,4), "ara": (41,14), "rac": (55,4), "rat": (59,1),
                "mte": (60,1), "tcas": (61, 28, tcas_reply)}
          }

  def get_type(self):
    bds1 = self.get_bits(33,4)
    bds2 = self.get_bits(37,4)
    if bds1 not in (0,1,2,3) or bds2 not in (0,):
      raise NoHandlerError(bds1)
    return int(bds1)

  def get_numbits(self):
    return 56

#  #type MV (extended squitter type 16) subfields
#  mv_fields = { "ara": (41,14), "mte": (60,1),  "rac": (55,4), "rat": (59,1),
#                "vds": (33,8),  "vds1": (33,4), "vds2": (37,4)
#              }

class mv_reply(data_field):
  offset = 33
  types = { "ara": (41,14), "mte": (60,1),  "rac": (55,4), "rat": (59,1),
            "vds": (33,8),  "vds1": (33,4), "vds2": (37,4)
          }

  def get_type(self):
    vds1 = self.get_bits(33,4)
    vds2 = self.get_bits(37,4)
    if vds1 not in (3,) or vds2 not in (0,):
      raise NoHandlerError(bds1)
    return int(vds1)

  def get_numbits(self):
    return 56

#the whole Mode S packet type
class modes_reply(data_field):
  types = { 0: {"df": (1,5), "vs": (6,1), "cc": (7,1), "sl": (9,3), "ri": (14,4), "ac": (20,13), "ap": (33,24)},
            4: {"df": (1,5), "fs": (6,3), "dr": (9,5), "um": (14,6), "ac": (20,13), "ap": (33,24)},
            5: {"df": (1,5), "fs": (6,3), "dr": (9,5), "um": (14,6), "id": (20,13), "ap": (33,24)},
           11: {"df": (1,5), "ca": (6,3), "aa": (9,24), "pi": (33,24)},
           16: {"df": (1,5), "vs": (6,1), "sl": (9,3), "ri": (14,4), "ac": (20,13), "mv": (33,56), "ap": (88,24)},
           17: {"df": (1,5), "ca": (6,3), "aa": (9,24), "me": (33,56, me_reply), "pi": (88,24)},
           20: {"df": (1,5), "fs": (6,3), "dr": (9,5), "um": (14,6), "ac": (20,13), "mb": (33,56, mb_reply), "ap": (88,24)},
           21: {"df": (1,5), "fs": (6,3), "dr": (9,5), "um": (14,6), "id": (20,13), "mb": (33,56, mb_reply), "ap": (88,24)},
           24: {"df": (1,5), "ke": (6,1), "nd": (7,4), "md": (11,80), "ap": (88,24)}
          }

  def is_long(self):
    return self.data > (1 << 56)

  def get_numbits(self):
    return 112 if self.is_long() else 56

  def get_type(self):
    return self.get_bits(1,5)

#unscramble mode A/C-style squawk codes for type 5 replies below
def decode_id(id):
  
  C1 = 0x1000
  A1 = 0x0800
  C2 = 0x0400
  A2 = 0x0200	#this represents the order in which the bits come
  C4 = 0x0100
  A4 = 0x0080
  B1 = 0x0020
  D1 = 0x0010
  B2 = 0x0008
  D2 = 0x0004
  B4 = 0x0002
  D4 = 0x0001
  
  a = ((id & A1) >> 11) + ((id & A2) >> 8) + ((id & A4) >> 5)
  b = ((id & B1) >> 5)  + ((id & B2) >> 2) + ((id & B4) << 1)
  c = ((id & C1) >> 12) + ((id & C2) >> 9) + ((id & C4) >> 6)
  d = ((id & D1) >> 2)  + ((id & D2) >> 1) + ((id & D4) << 2)
   
  return (a * 1000) + (b * 100) + (c * 10) + d

#decode ident squawks
def charmap(d):
  if d > 0 and d < 27:
    retval = chr(ord("A")+d-1)
  elif d == 32:
    retval = " "
  elif d > 47 and d < 58:
    retval = chr(ord("0")+d-48)
  else:
    retval = " "

  return retval

def parseBDS08(data):
  categories = [["NO INFO", "RESERVED", "RESERVED", "RESERVED", "RESERVED", "RESERVED", "RESERVED", "RESERVED"],\
                ["NO INFO", "SURFACE EMERGENCY VEHICLE", "SURFACE SERVICE VEHICLE", "FIXED OBSTRUCTION", "CLUSTER OBSTRUCTION", "LINE OBSTRUCTION", "RESERVED"],\
                ["NO INFO", "GLIDER", "BALLOON/BLIMP", "PARACHUTE", "ULTRALIGHT", "RESERVED", "UAV", "SPACECRAFT"],\
                ["NO INFO", "LIGHT", "SMALL", "LARGE", "LARGE HIGH VORTEX", "HEAVY", "HIGH PERFORMANCE", "ROTORCRAFT"]]

  catstring = categories[data["ftc"]-1][data["cat"]]

  msg = ""
  for i in range(0, 8):
    msg += charmap(data["ident"] >> (42-6*i) & 0x3F)
  return (msg, catstring)

#NOTE: this is stateful -- requires CPR decoder
def parseBDS05(data, cprdec):
  altitude = decode_alt(data["alt"], False)
  [decoded_lat, decoded_lon, rnge, bearing] = cprdec.decode(data["aa"], data["lat"], data["lon"], data["cpr"], 0)
  return [altitude, decoded_lat, decoded_lon, rnge, bearing]

#NOTE: this is stateful -- requires CPR decoder
def parseBDS06(data, cprdec):
  ground_track = data["gtk"] * 360. / 128
  [decoded_lat, decoded_lon, rnge, bearing] = cprdec.decode(data["aa"], data["lat"], data["lon"], data["cpr"], 1)
  return [ground_track, decoded_lat, decoded_lon, rnge, bearing]

def parseBDS09_0(data):
  #0: ["sub", "dew", "vew", "dns", "vns", "str", "tr", "svr", "vr"],
  vert_spd = data["vr"] * 32
  ud = bool(data["dvr"])
  if ud:
    vert_spd = 0 - vert_spd
  turn_rate = data["tr"] * 15/62
  rl = data["str"]
  if rl:
    turn_rate = 0 - turn_rate
  ns_vel = data["vns"] - 1
  ns = bool(data["dns"])
  ew_vel = data["vew"] - 1
  ew = bool(data["dew"])
    
  velocity = math.hypot(ns_vel, ew_vel)
  if ew:
    ew_vel = 0 - ew_vel
  if ns:
    ns_vel = 0 - ns_vel
  heading = math.atan2(ew_vel, ns_vel) * (180.0 / math.pi)
  if heading < 0:
    heading += 360

  return [velocity, heading, vert_spd, turn_rate]

def parseBDS09_1(data):
  #1: ["sub", "icf", "ifr", "nuc", "dew", "vew", "dns", "vns", "vrsrc", "dvr", "vr", "dhd", "hd"],
  alt_geo_diff = data["hd"] * 25
  above_below = bool(data["dhd"])
  if above_below:
    alt_geo_diff = 0 - alt_geo_diff;
  vert_spd = float(data["vr"] - 1) * 64
  ud = bool(data["dvr"])
  if ud:
    vert_spd = 0 - vert_spd
  vert_src = bool(data["vrsrc"])
  ns_vel = float(data["vns"])
  ns = bool(data["dns"])
  ew_vel = float(data["vew"])
  ew = bool(data["dew"])
  subtype = data["sub"]
  if subtype == 0x02:
    ns_vel <<= 2
    ew_vel <<= 2

  velocity = math.hypot(ns_vel, ew_vel)
  if ew:
    ew_vel = 0 - ew_vel
	
  if ns_vel == 0:
    heading = 0
  else:
    heading = math.atan(float(ew_vel) / float(ns_vel)) * (180.0 / math.pi)
  if ns:
    heading = 180 - heading
  if heading < 0:
    heading += 360

  return [velocity, heading, vert_spd]

def parseBDS09_3(data):
    #3: {"sub", "icf", "ifr", "nuc", "mhs", "hdg", "ast", "spd", "vrsrc",
    #    "dvr", "vr", "dhd", "hd"}
  mag_hdg = data["mhs"] * 360. / 1024
  vel_src = "TAS" if data["ast"] == 1 else "IAS"
  vel = data["spd"]
  if data["sub"] == 4:
      vel *= 4
  vert_spd = float(data["vr"] - 1) * 64
  if data["dvr"] == 1:
      vert_spd = 0 - vert_spd
  geo_diff = float(data["hd"] - 1) * 25
  return [mag_hdg, vel_src, vel, vert_spd, geo_diff]
      

def parseBDS62(data):
  eps_strings = ["NO EMERGENCY", "GENERAL EMERGENCY", "LIFEGUARD/MEDICAL", "FUEL EMERGENCY",
                 "NO COMMUNICATIONS", "UNLAWFUL INTERFERENCE", "RESERVED", "RESERVED"]
  return eps_strings[data["eps"]]

def parseMB_id(data): #bds1 == 2, bds2 == 0
  msg = ""
  for i in range(0, 8):
    msg += charmap( data["ais"] >> (42-6*i) & 0x3F)
  return (msg)

def parseMB_TCAS_resolutions(data):
  #these are LSB because the ICAO are asshats
  ara_bits    = {41: "CLIMB", 42: "DON'T DESCEND", 43: "DON'T DESCEND >500FPM", 44: "DON'T DESCEND >1000FPM",
                 45: "DON'T DESCEND >2000FPM", 46: "DESCEND", 47: "DON'T CLIMB", 48: "DON'T CLIMB >500FPM",
                 49: "DON'T CLIMB >1000FPM", 50: "DON'T CLIMB >2000FPM", 51: "TURN LEFT", 52: "TURN RIGHT",
                 53: "DON'T TURN LEFT", 54: "DON'T TURN RIGHT"}
  rac_bits    = {55: "DON'T DESCEND", 56: "DON'T CLIMB", 57: "DON'T TURN LEFT", 58: "DON'T TURN RIGHT"}
  ara = data["ara"]
  rac = data["rac"]
  #check to see which bits are set
  resolutions = ""
  for bit in ara_bits:
    if ara & (1 << (54-bit)):
      resolutions += " " + ara_bits[bit]
  complements = ""
  for bit in rac_bits:
    if rac & (1 << (58-bit)):
      complements += " " + rac_bits[bit]
  return (resolutions, complements)

#rat is 1 if resolution advisory terminated <18s ago
#mte is 1 if multiple threats indicated
#tti is threat type: 1 if ID, 2 if range/brg/alt
#tida is threat altitude in Mode C format
def parseMB_TCAS_threatid(data): #bds1==3, bds2==0, TTI==1
  #3: {"bds1": (33,4), "bds2": (37,4), "ara": (41,14), "rac": (55,4), "rat": (59,1),
  #    "mte": (60,1), "tti": (61,2),  "tida": (63,13), "tidr": (76,7), "tidb": (83,6)}
  (resolutions, complements) = parseMB_TCAS_resolutions(data)
  return (resolutions, complements, data["rat"], data["mte"], data["tid"])

def parseMB_TCAS_threatloc(data): #bds1==3, bds2==0, TTI==2
  (resolutions, complements) = parseMB_TCAS_resolutions(data)
  threat_alt = decode_alt(data["tida"], True)
  return (resolutions, complements, data["rat"], data["mte"], threat_alt, data["tidr"], data["tidb"])

#type 16 Coordination Reply Message
def parse_TCAS_CRM(data):
  (resolutions, complements) = parseMB_TCAS_resolutions(data)
  return (resolutions, complements, data["rat"], data["mte"])

#this decorator takes a pubsub and returns a function which parses and publishes messages
def make_parser(pub):
  publisher = pub
  def publish(message):
    [data, ecc, reference, timestamp] = message.split()
    try:
      ret = air_modes.modes_report(modes_reply(int(data, 16)),
                                   int(ecc, 16),
                                   10.0*math.log10(max(1e-8,float(reference))),
                                   air_modes.stamp(0, float(timestamp)))
      pub["modes_dl"] = ret
      pub["type%i_dl" % ret.data.get_type()] = ret
    except ADSBError:
      pass

  return publish

########NEW FILE########
__FILENAME__ = qa_gr-air-modes
#!/usr/bin/env python
#
# Copyright 2004,2007 Free Software Foundation, Inc.
# 
# This file is part of GNU Radio
# 
# GNU Radio is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 3, or (at your option)
# any later version.
# 
# GNU Radio is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
# 
# You should have received a copy of the GNU General Public License
# along with GNU Radio; see the file COPYING.  If not, write to
# the Free Software Foundation, Inc., 51 Franklin Street,
# Boston, MA 02110-1301, USA.
# 

from gnuradio import gr, gr_unittest
import gr-air-modes_swig

class qa_gr-air-modes (gr_unittest.TestCase):

    def setUp (self):
        self.tb = gr.top_block ()

    def tearDown (self):
        self.tb = None

    def test_001_square_ff (self):
        src_data = (-3, 4, -5.5, 2, 3)
        expected_result = (9, 16, 30.25, 4, 9)
        src = gr.vector_source_f (src_data)
        sqr = gr-air-modes_swig.square_ff ()
        dst = gr.vector_sink_f ()
        self.tb.connect (src, sqr)
        self.tb.connect (sqr, dst)
        self.tb.run ()
        result_data = dst.data ()
        self.assertFloatTuplesAlmostEqual (expected_result, result_data, 6)

    def test_002_square2_ff (self):
        src_data = (-3, 4, -5.5, 2, 3)
        expected_result = (9, 16, 30.25, 4, 9)
        src = gr.vector_source_f (src_data)
        sqr = gr-air-modes_swig.square2_ff ()
        dst = gr.vector_sink_f ()
        self.tb.connect (src, sqr)
        self.tb.connect (sqr, dst)
        self.tb.run ()
        result_data = dst.data ()
        self.assertFloatTuplesAlmostEqual (expected_result, result_data, 6)
        
if __name__ == '__main__':
    gr_unittest.main ()

########NEW FILE########
__FILENAME__ = Quaternion
"""
Quaternion provides a class for manipulating quaternion objects.  This class provides:

   - a convenient constructor to convert to/from Euler Angles (RA,Dec,Roll) 
       to/from quaternions
   - class methods to multiply and divide quaternions 
"""

"""Copyright 2009 Smithsonian Astrophysical Observatory
   Released under New BSD / 3-Clause BSD License
   All rights reserved
"""
"""
   Modified 2012 by Nick Foster
   Modified from version 0.3.1
   http://pypi.python.org/pypi/Quaternion/0.03
   Added _get_angle_axis to get the angle-axis representation
   Added _latlontoquat to get a rotation quat to ECEF from lat/lon
"""


      
import numpy as np
from math import cos, sin, radians, degrees, atan2, sqrt, acos, pi

class Quat(object):
   """
   Quaternion class
   
   Example usage::

    >>> from Quaternion import Quat
    >>> quat = Quat((12,45,45))
    >>> quat.ra, quat.dec, quat.roll
    (12, 45, 45)
    >>> quat.q
    array([ 0.38857298, -0.3146602 ,  0.23486498,  0.8335697 ])
    >>> q2 = Quat([ 0.38857298, -0.3146602 ,  0.23486498,  0.8335697])
    >>> q2.ra
    11.999999315925008


   Multiplication and division operators are overloaded for the class to 
   perform appropriate quaternion multiplication and division.

   Example usage::
   
    >>> q1 = Quat((20,30,40))
    >>> q2 = Quat((30,40,50))
    >>> q = q1 / q2

   Performs the operation as q1 * inverse q2

   Example usage::

    >>> q1 = Quat((20,30,40))
    >>> q2 = Quat((30,40,50))
    >>> q = q1 * q2


   :param attitude: initialization attitude for quat

   ``attitude`` may be:
     * another Quat
     * a 4 element array (expects x,y,z,w quat form)
     * a 3 element array (expects ra,dec,roll in degrees)
     * a 3x3 transform/rotation matrix

   """
   def __init__(self, attitude):
      self._q = None
      self._equatorial = None
      self._T = None
      # checks to see if we've been passed a Quat 
      if isinstance(attitude, Quat):
         self._set_q(attitude.q)
      else:
         # make it an array and check to see if it is a supported shape
         attitude = np.array(attitude)
         if len(attitude) == 4:
            self._set_q(attitude)
         elif attitude.shape == (3,3):
            self._set_transform(attitude)
         elif attitude.shape == (3,):
            self._set_equatorial(attitude)
         elif attitude.shape == (2,):
            self._set_latlon(attitude)
         else:
            raise TypeError("attitude is not one of possible types (2, 3 or 4 elements, Quat, or 3x3 matrix)")
         

   def _set_q(self, q):
      """
      Set the value of the 4 element quaternion vector 

      :param q: list or array of normalized quaternion elements
      """
      q = np.array(q)
      if abs(np.sum(q**2) - 1.0) > 1e-6:
         raise ValueError('Quaternion must be normalized so sum(q**2) == 1; use Quaternion.normalize')
      self._q = (q if q[3] > 0 else -q)
      # Erase internal values of other representations
      self._equatorial = None
      self._T = None

   def _get_q(self):
      """
      Retrieve 4-vector of quaternion elements in [x, y, z, w] form
      
      :rtype: numpy array

      """
      if self._q is None:
         # Figure out q from available values, doing nothing others are not defined
         if self._equatorial is not None:
            self._q = self._equatorial2quat()
         elif self._T is not None:
            self._q = self._transform2quat()
      return self._q

   # use property to make this get/set automatic
   q = property(_get_q, _set_q)

   def _set_equatorial(self, equatorial):
      """Set the value of the 3 element equatorial coordinate list [RA,Dec,Roll]
         expects values in degrees
         bounds are not checked
      
         :param equatorial: list or array [ RA, Dec, Roll] in degrees
         
      """
      att = np.array(equatorial)
      ra, dec, roll = att
      self._ra0 = ra
      if ( ra > 180 ):
         self._ra0 = ra - 360
         self._roll0 = roll
      if ( roll > 180):
         self._roll0 = roll - 360
      self._equatorial = att

   def _set_latlon(self, latlon):
      self._q = self._latlontoquat(latlon)
    
   def _get_equatorial(self):
      """Retrieve [RA, Dec, Roll]

      :rtype: numpy array
      """
      if self._equatorial is None:
         if self._q is not None:
            self._equatorial = self._quat2equatorial()
         elif self._T is not None:
            self._q = self._transform2quat()
            self._equatorial = self._quat2equatorial()
      return self._equatorial

   equatorial = property(_get_equatorial,_set_equatorial)

   def _get_ra(self):
      """Retrieve RA term from equatorial system in degrees"""
      return self.equatorial[0]
        
   def _get_dec(self):
      """Retrieve Dec term from equatorial system in degrees"""
      return self.equatorial[1]
        
   def _get_roll(self):
      """Retrieve Roll term from equatorial system in degrees"""
      return self.equatorial[2]

   ra = property(_get_ra)
   dec = property(_get_dec)
   roll = property(_get_roll)

   def _set_transform(self, T):
      """
      Set the value of the 3x3 rotation/transform matrix
      
      :param T: 3x3 array/numpy array
      """
      transform = np.array(T)
      self._T = transform

   def _get_transform(self):
      """
      Retrieve the value of the 3x3 rotation/transform matrix

      :returns: 3x3 rotation/transform matrix
      :rtype: numpy array
      
      """
      if self._T is None:
         if self._q is not None:
            self._T = self._quat2transform()
         elif self._equatorial is not None:
            self._T = self._equatorial2transform()
      return self._T

   transform = property(_get_transform, _set_transform)

   def _quat2equatorial(self):
      """
      Determine Right Ascension, Declination, and Roll for the object quaternion
      
      :returns: RA, Dec, Roll
      :rtype: numpy array [ra,dec,roll]
      """
      
      q = self.q
      q2 = self.q**2

      ## calculate direction cosine matrix elements from $quaternions
      xa = q2[0] - q2[1] - q2[2] + q2[3] 
      xb = 2 * (q[0] * q[1] + q[2] * q[3]) 
      xn = 2 * (q[0] * q[2] - q[1] * q[3]) 
      yn = 2 * (q[1] * q[2] + q[0] * q[3]) 
      zn = q2[3] + q2[2] - q2[0] - q2[1] 

      ##; calculate RA, Dec, Roll from cosine matrix elements
      ra   = degrees(atan2(xb , xa)) ;
      dec  = degrees(atan2(xn , sqrt(1 - xn**2)));
      roll = degrees(atan2(yn , zn)) ;
      if ( ra < 0 ):
         ra += 360
      if ( roll < 0 ):
         roll += 360

      return np.array([ra, dec, roll])


   def _quat2transform(self):
      """
      Transform a unit quaternion into its corresponding rotation matrix (to
      be applied on the right side).
      
      :returns: transform matrix
      :rtype: numpy array
      
      """
      x, y, z, w = self.q
      xx2 = 2 * x * x
      yy2 = 2 * y * y
      zz2 = 2 * z * z
      xy2 = 2 * x * y
      wz2 = 2 * w * z
      zx2 = 2 * z * x
      wy2 = 2 * w * y
      yz2 = 2 * y * z
      wx2 = 2 * w * x
      
      rmat = np.empty((3, 3), float)
      rmat[0,0] = 1. - yy2 - zz2
      rmat[0,1] = xy2 - wz2
      rmat[0,2] = zx2 + wy2
      rmat[1,0] = xy2 + wz2
      rmat[1,1] = 1. - xx2 - zz2
      rmat[1,2] = yz2 - wx2
      rmat[2,0] = zx2 - wy2
      rmat[2,1] = yz2 + wx2
      rmat[2,2] = 1. - xx2 - yy2
      
      return rmat

   def _equatorial2quat( self ):
      """Dummy method to return return quat. 

      :returns: quaternion
      :rtype: Quat
      
      """
      return self._transform2quat()
   
   def _equatorial2transform( self ):
      """Construct the transform/rotation matrix from RA,Dec,Roll

      :returns: transform matrix
      :rtype: 3x3 numpy array

      """
      ra = radians(self._get_ra())
      dec = radians(self._get_dec())
      roll = radians(self._get_roll())
      ca = cos(ra)
      sa = sin(ra)
      cd = cos(dec)
      sd = sin(dec)
      cr = cos(roll)
      sr = sin(roll)
      
      # This is the transpose of the transformation matrix (related to translation
      # of original perl code
      rmat = np.array([[ca * cd,                    sa * cd,                  sd     ],
                       [-ca * sd * sr - sa * cr,   -sa * sd * sr + ca * cr,   cd * sr],
                       [-ca * sd * cr + sa * sr,   -sa * sd * cr - ca * sr,   cd * cr]])

      return rmat.transpose()

   def _transform2quat( self ):
      """Construct quaternion from the transform/rotation matrix 

      :returns: quaternion formed from transform matrix
      :rtype: numpy array
      """

      # Code was copied from perl PDL code that uses backwards index ordering
      T = self.transform.transpose()  
      den = np.array([ 1.0 + T[0,0] - T[1,1] - T[2,2],
                       1.0 - T[0,0] + T[1,1] - T[2,2],
                       1.0 - T[0,0] - T[1,1] + T[2,2],
                       1.0 + T[0,0] + T[1,1] + T[2,2]])
      
      max_idx = np.flatnonzero(den == max(den))[0]

      q = np.zeros(4)
      q[max_idx] = 0.5 * sqrt(max(den))
      denom = 4.0 * q[max_idx]
      if (max_idx == 0):
         q[1] =  (T[1,0] + T[0,1]) / denom 
         q[2] =  (T[2,0] + T[0,2]) / denom 
         q[3] = -(T[2,1] - T[1,2]) / denom 
      if (max_idx == 1):
         q[0] =  (T[1,0] + T[0,1]) / denom 
         q[2] =  (T[2,1] + T[1,2]) / denom 
         q[3] = -(T[0,2] - T[2,0]) / denom 
      if (max_idx == 2):
         q[0] =  (T[2,0] + T[0,2]) / denom 
         q[1] =  (T[2,1] + T[1,2]) / denom 
         q[3] = -(T[1,0] - T[0,1]) / denom 
      if (max_idx == 3):
         q[0] = -(T[2,1] - T[1,2]) / denom 
         q[1] = -(T[0,2] - T[2,0]) / denom 
         q[2] = -(T[1,0] - T[0,1]) / denom 

      return q
      
   def _get_angle_axis(self):
      lim = 1e-12
      norm = np.linalg.norm(self.q)
      if norm < lim:
         angle = 0
         axis = [0,0,0]
      else:
         rnorm = 1.0 / norm
         angle = acos(max(-1, min(1, rnorm*self.q[3])));
         sangle = sin(angle)
         if sangle < lim:
            axis = [0,0,0]
         else:
            axis = (rnorm / sangle) * np.array(self.q[0:3])

         angle *= 2

      return (angle, axis)

   def _latlontoquat ( self, latlon ):
      q = np.zeros(4)
      
      lon = latlon[1]*(pi/180.)
      lat = latlon[0]*(pi/180.)
      zd2 = 0.5*lon
      yd2 = -0.25*pi - 0.5*lat
      Szd2 = sin(zd2)
      Syd2 = sin(yd2)
      Czd2 = cos(zd2)
      Cyd2 = cos(yd2)
      q[0] = -Szd2*Syd2
      q[1] = Czd2*Syd2
      q[2] = Szd2*Cyd2
      q[3] = Czd2*Cyd2

      return q

   def __div__(self, quat2):
      """
      Divide one quaternion by another.
      
      Example usage::

       >>> q1 = Quat((20,30,40))
       >>> q2 = Quat((30,40,50))
       >>> q = q1 / q2

      Performs the operation as q1 * inverse q2

      :returns: product q1 * inverse q2
      :rtype: Quat

      """
      return self * quat2.inv()


   def __mul__(self, quat2):
      """
      Multiply quaternion by another.

      Example usage::

        >>> q1 = Quat((20,30,40))
        >>> q2 = Quat((30,40,50))
        >>> (q1 * q2).equatorial
        array([ 349.73395729,   76.25393056,  127.61636727])

      :returns: product q1 * q2
      :rtype: Quat

      """
      q1 = self.q
      q2 = quat2.q
      mult = np.zeros(4)
      mult[0] = q1[3]*q2[0] - q1[2]*q2[1] + q1[1]*q2[2] + q1[0]*q2[3]
      mult[1] = q1[2]*q2[0] + q1[3]*q2[1] - q1[0]*q2[2] + q1[1]*q2[3]
      mult[2] = -q1[1]*q2[0] + q1[0]*q2[1] + q1[3]*q2[2] + q1[2]*q2[3]
      mult[3] = -q1[0]*q2[0] - q1[1]*q2[1] - q1[2]*q2[2] + q1[3]*q2[3]
      return Quat(mult)

   def inv(self):
      """
      Invert the quaternion 

      :returns: inverted quaternion
      :rtype: Quat
      """
      return Quat([self.q[0], self.q[1], self.q[2], -self.q[3]])

        
        


def normalize(array):
   """ 
   Normalize a 4 element array/list/numpy.array for use as a quaternion
   
   :param quat_array: 4 element list/array
   :returns: normalized array
   :rtype: numpy array

   """
   quat = np.array(array)
   return quat / np.sqrt(np.dot(quat, quat))


########NEW FILE########
__FILENAME__ = radio
# Copyright 2013 Nick Foster
# 
# This file is part of gr-air-modes
# 
# gr-air-modes is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 3, or (at your option)
# any later version.
# 
# gr-air-modes is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
# 
# You should have received a copy of the GNU General Public License
# along with gr-air-modes; see the file COPYING.  If not, write to
# the Free Software Foundation, Inc., 51 Franklin Street,
# Boston, MA 02110-1301, USA.
#

# Radio interface for Mode S RX.
# Handles all hardware- and source-related functionality
# You pass it options, it gives you data.
# It uses the pubsub interface to allow clients to subscribe to its data feeds.

from gnuradio import gr, gru, eng_notation, filter, blocks
from gnuradio.filter import optfir
from gnuradio.eng_option import eng_option
from gnuradio.gr.pubsub import pubsub
from optparse import OptionParser, OptionGroup
import air_modes
import zmq
import threading
import time
import re

class modes_radio (gr.top_block, pubsub):
  def __init__(self, options, context):
    gr.top_block.__init__(self)
    pubsub.__init__(self)
    self._options = options
    self._queue = gr.msg_queue()
    self._rate = int(options.rate)

    self._resample = None
    self._setup_source(options)

    self._rx_path = air_modes.rx_path(self._rate, options.threshold,
                                      self._queue, options.pmf, options.dcblock)

    #now subscribe to set various options via pubsub
    self.subscribe("freq", self.set_freq)
    self.subscribe("gain", self.set_gain)
    self.subscribe("rate", self.set_rate)
    self.subscribe("rate", self._rx_path.set_rate)
    self.subscribe("threshold", self._rx_path.set_threshold)
    self.subscribe("pmf", self._rx_path.set_pmf)

    self.publish("freq", self.get_freq)
    self.publish("gain", self.get_gain)
    self.publish("rate", self.get_rate)
    self.publish("threshold", self._rx_path.get_threshold)
    self.publish("pmf", self._rx_path.get_pmf)

    if self._resample is not None:
        self.connect(self._u, self._resample, self._rx_path)
    else:
        self.connect(self._u, self._rx_path)

    #Publish messages when they come back off the queue
    server_addr = ["inproc://modes-radio-pub"]
    if options.tcp is not None:
        server_addr += ["tcp://*:%i" % options.tcp]

    self._sender = air_modes.zmq_pubsub_iface(context, subaddr=None, pubaddr=server_addr)
    self._async_sender = gru.msgq_runner(self._queue, self.send)

  def send(self, msg):
    self._sender["dl_data"] = msg.to_string()

  @staticmethod
  def add_radio_options(parser):
    group = OptionGroup(parser, "Receiver setup options")

    #Choose source
    group.add_option("-s","--source", type="string", default="uhd",
                      help="Choose source: uhd, osmocom, <filename>, or <ip:port> [default=%default]")
    group.add_option("-t","--tcp", type="int", default=None, metavar="PORT",
                      help="Open a TCP server on this port to publish reports")

    #UHD/Osmocom args
    group.add_option("-R", "--subdev", type="string",
                      help="select USRP Rx side A or B", metavar="SUBDEV")
    group.add_option("-A", "--antenna", type="string",
                      help="select which antenna to use on daughterboard")
    group.add_option("-D", "--args", type="string",
                      help="arguments to pass to radio constructor", default="")
    group.add_option("-f", "--freq", type="eng_float", default=1090e6,
                      help="set receive frequency in Hz [default=%default]", metavar="FREQ")
    group.add_option("-g", "--gain", type="int", default=None,
                      help="set RF gain", metavar="dB")

    #RX path args
    group.add_option("-r", "--rate", type="eng_float", default=4e6,
                      help="set sample rate [default=%default]")
    group.add_option("-T", "--threshold", type="eng_float", default=7.0,
                      help="set pulse detection threshold above noise in dB [default=%default]")
    group.add_option("-p","--pmf", action="store_true", default=False,
                      help="Use pulse matched filtering [default=%default]")
    group.add_option("-d","--dcblock", action="store_true", default=False,
                      help="Use a DC blocking filter (best for HackRF Jawbreaker) [default=%default]")

    parser.add_option_group(group)

  def live_source(self):
    return self._options.source=="uhd" or self._options.source=="osmocom"

  def set_freq(self, freq):
    return self._u.set_center_freq(freq, 0) if self.live_source() else 0

  def set_gain(self, gain):
    if self.live_source():
        self._u.set_gain(gain)
        print "Gain is %f" % self.get_gain()
    return self.get_gain()

  def set_rate(self, rate):
    self._rx_path.set_rate(rate)
    return self._u.set_rate(rate) if self.live_source() else 0

  def set_threshold(self, threshold):
    self._rx_path.set_threshold(threshold)

  def get_freq(self, freq):
    return self._u.get_center_freq(freq, 0) if self.live_source() else 1090e6

  def get_gain(self):
    return self._u.get_gain() if self.live_source() else 0

  def get_rate(self):
    return self._u.get_rate() if self.live_source() else self._rate

  def _setup_source(self, options):
    if options.source == "uhd":
      #UHD source by default
      from gnuradio import uhd
      self._u = uhd.single_usrp_source(options.args, uhd.io_type_t.COMPLEX_FLOAT32, 1)

      if(options.subdev):
        self._u.set_subdev_spec(options.subdev, 0)

      if not self._u.set_center_freq(options.freq):
        print "Failed to set initial frequency"

      #check for GPSDO
      #if you have a GPSDO, UHD will automatically set the timestamp to UTC time
      #as well as automatically set the clock to lock to GPSDO.
      if self._u.get_time_source(0) != 'gpsdo':
        self._u.set_time_now(uhd.time_spec(0.0))

      if options.antenna is not None:
        self._u.set_antenna(options.antenna)

      self._u.set_samp_rate(options.rate)
      options.rate = int(self._u.get_samp_rate()) #retrieve actual

      if options.gain is None: #set to halfway
        g = self._u.get_gain_range()
        options.gain = (g.start()+g.stop()) / 2.0

      print "Setting gain to %i" % options.gain
      self._u.set_gain(options.gain)
      print "Gain is %i" % self._u.get_gain()

    #TODO: detect if you're using an RTLSDR or Jawbreaker
    #and set up accordingly.
    elif options.source == "osmocom": #RTLSDR dongle or HackRF Jawbreaker
        import osmosdr
        self._u = osmosdr.source(options.args)
#        self._u.set_sample_rate(3.2e6) #fixed for RTL dongles
        self._u.set_sample_rate(options.rate)
        if not self._u.set_center_freq(options.freq):
            print "Failed to set initial frequency"

#        self._u.set_gain_mode(0) #manual gain mode
        if options.gain is None:
            options.gain = 34
        self._u.set_gain(options.gain)
        print "Gain is %i" % self._u.get_gain()

        #Note: this should only come into play if using an RTLSDR.
#        lpfiltcoeffs = gr.firdes.low_pass(1, 5*3.2e6, 1.6e6, 300e3)
#        self._resample = filter.rational_resampler_ccf(interpolation=5, decimation=4, taps=lpfiltcoeffs)

    else:
      #semantically detect whether it's ip.ip.ip.ip:port or filename
      if ':' in options.source:
        try:
          ip, port = re.search("(.*)\:(\d{1,5})", options.source).groups()
        except:
          raise Exception("Please input UDP source e.g. 192.168.10.1:12345")
        self._u = gr.udp_source(gr.sizeof_gr_complex, ip, int(port))
        print "Using UDP source %s:%s" % (ip, port)
      else:
        self._u = blocks.file_source(gr.sizeof_gr_complex, options.source)
        print "Using file source %s" % options.source

    print "Rate is %i" % (options.rate,)

  def close(self):
    self._sender.close()
    self._u = None

########NEW FILE########
__FILENAME__ = raw_server
#
# Copyright 2010 Nick Foster
# 
# This file is part of gr-air-modes
# 
# gr-air-modes is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 3, or (at your option)
# any later version.
# 
# gr-air-modes is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
# 
# You should have received a copy of the GNU General Public License
# along with gr-air-modes; see the file COPYING.  If not, write to
# the Free Software Foundation, Inc., 51 Franklin Street,
# Boston, MA 02110-1301, USA.
# 


import time, os, sys, socket
from string import split, join
from datetime import *

class raw_server:
  def __init__(self, port):
    self._s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    self._s.bind(('', port))
    self._s.listen(1)
    self._s.setblocking(0) #nonblocking
    self._conns = [] #list of active connections

  def __del__(self):
    self._s.close()

  def output(self, msg):
    for conn in self._conns[:]: #iterate over a copy of the list
      try:
        conn.send(msg)
      except socket.error:
        self._conns.remove(conn)
        print "Connections: ", len(self._conns)

  def add_pending_conns(self):
    try:
      conn, addr = self._s.accept()
      self._conns.append(conn)
      print "Connections: ", len(self._conns)
    except socket.error:
      pass

########NEW FILE########
__FILENAME__ = rx_path
#
# Copyright 2012, 2013 Corgan Labs, Nick Foster
# 
# This file is part of gr-air-modes
# 
# gr-air-modes is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 3, or (at your option)
# any later version.
# 
# gr-air-modes is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
# 
# You should have received a copy of the GNU General Public License
# along with gr-air-modes; see the file COPYING.  If not, write to
# the Free Software Foundation, Inc., 51 Franklin Street,
# Boston, MA 02110-1301, USA.
# 

from gnuradio import gr, blocks, filter
import air_modes_swig

class rx_path(gr.hier_block2):

    def __init__(self, rate, threshold, queue, use_pmf=False, use_dcblock=False):
        gr.hier_block2.__init__(self, "modes_rx_path",
                                gr.io_signature(1, 1, gr.sizeof_gr_complex),
                                gr.io_signature(0,0,0))

        self._rate = int(rate)
        self._threshold = threshold
        self._queue = queue
        self._spc = int(rate/2e6)

        # Convert incoming I/Q baseband to amplitude
        self._demod = blocks.complex_to_mag_squared()
        if use_dcblock:
            self._dcblock = filter.dc_blocker_cc(100*self._spc,True)
            self.connect(self, self._dcblock, self._demod)
        else:
            self.connect(self, self._demod)
            self._dcblock = None

        self._bb = self._demod
        # Pulse matched filter for 0.5us pulses
        if use_pmf:
            self._pmf = blocks.moving_average_ff(self._spc, 1.0/self._spc)#, self._rate)
            self.connect(self._demod, self._pmf)
            self._bb = self._pmf

        # Establish baseline amplitude (noise, interference)
        self._avg = blocks.moving_average_ff(48*self._spc, 1.0/(48*self._spc))#, self._rate) # 3 preambles

        # Synchronize to Mode-S preamble
        self._sync = air_modes_swig.preamble(self._rate, self._threshold)

        # Slice Mode-S bits and send to message queue
        self._slicer = air_modes_swig.slicer(self._queue)

        # Wire up the flowgraph
        self.connect(self._bb, (self._sync, 0))
        self.connect(self._bb, self._avg, (self._sync, 1))
        self.connect(self._sync, self._slicer)

    def set_rate(self, rate):
        self._sync.set_rate(rate)
        self._spc = int(rate/2e6)
        self._avg.set_length_and_scale(48*self._spc, 1.0/(48*self._spc))
        if self._bb != self._demod:
            self._pmf.set_length_and_scale(self._spc, 1.0/self._spc)
        if self._dcblock is not None:
            self._dcblock.set_length(100*self._spc)

    def set_threshold(self, threshold):
        self._sync.set_threshold(threshold)

    def set_pmf(self, pmf):
        #TODO must be done when top block is stopped
        pass

    def get_pmf(self, pmf):
        return not (self._bb == self._demod)

    def get_threshold(self, threshold):
        return self._sync.get_threshold()


########NEW FILE########
__FILENAME__ = sbs1
#
# Copyright 2010 Nick Foster
# 
# This file is part of gr-air-modes
# 
# gr-air-modes is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 3, or (at your option)
# any later version.
# 
# gr-air-modes is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
# 
# You should have received a copy of the GNU General Public License
# along with gr-air-modes; see the file COPYING.  If not, write to
# the Free Software Foundation, Inc., 51 Franklin Street,
# Boston, MA 02110-1301, USA.
# 


import time, os, sys, socket
from string import split, join
import air_modes
import datetime
from air_modes.exceptions import *
import threading

class dumb_task_runner(threading.Thread):
    def __init__(self, task, interval):
        threading.Thread.__init__(self)
        self._task = task
        self._interval = interval
        self.shutdown = threading.Event()
        self.finished = threading.Event()
        self.setDaemon(True)
        self.start()

    def run(self):
        while not self.shutdown.is_set():
            self._task()
            time.sleep(self._interval)
        self.finished.set()

    def close(self):
        self.shutdown.set()
        self.finished.wait(self._interval)

class output_sbs1:
  def __init__(self, cprdec, port, pub):
    self._s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    self._s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    self._s.bind(('', port))
    self._s.listen(1)
    self._s.setblocking(0) #nonblocking
    self._conns = [] #list of active connections
    self._aircraft_id_map = {} # dictionary of icao24 to aircraft IDs
    self._aircraft_id_count = 0 # Current Aircraft ID count

    self._cpr = cprdec

    #it could be cleaner if there were separate output_* fns
    #but this works
    for i in (0, 4, 5, 11, 17):
        pub.subscribe("type%i_dl" % i, self.output)

    #spawn thread to add new connections as they come in
    self._runner = dumb_task_runner(self.add_pending_conns, 0.1)

  def __del__(self):
    self._s.close()

  def get_aircraft_id(self, icao24):
    if icao24 in self._aircraft_id_map:
      return self._aircraft_id_map[icao24]

    # Adding this new ID to the dictionary
    self._aircraft_id_count += 1
    self._aircraft_id_map[icao24] = self._aircraft_id_count

    # Checking to see if we need to clean up in the event that the
    # dictionary is getting too large.
    if len(self._aircraft_id_map) > 1e4:
      minimum = min(self._aircraft_id_map.values()) + (len(self._aircraft_id_map) - 1e4)
      for icao, _id in self._aircraft_id_map.iteritems():
        if _id < minimum:
            del self._aircraft_id_map[icao]

    # Finally return the new pair
    return self._aircraft_id_count

  def output(self, msg):
    try:
      sbs1_msg = self.parse(msg)
      if sbs1_msg is not None:
        for conn in self._conns[:]: #iterate over a copy of the list
          conn.send(sbs1_msg)
    except socket.error:
      self._conns.remove(conn)
      print "Connections: ", len(self._conns)
    except ADSBError:
      pass

  def add_pending_conns(self):
    try:
      conn, addr = self._s.accept()
      self._conns.append(conn)
      print "Connections: ", len(self._conns)
    except socket.error:
      pass

  def current_time(self):
    timenow = datetime.datetime.now()
    return [timenow.strftime("%Y/%m/%d"), timenow.strftime("%H:%M:%S.%f")[0:-3]]

  def decode_fs(self, fs):
    if fs == 0:
      return "0,0,0,0"
    elif fs == 1:
      return "0,0,0,1"
    elif fs == 2:
      return "1,0,0,0"
    elif fs == 3:
      return "1,0,0,1"
    elif fs == 4:
      return "1,0,1,"
    elif fs == 5:
      return "0,0,1,"
    else:
      return ",,,"

  def parse(self, msg):
    #assembles a SBS-1-style output string from the received message

    msgtype = msg.data["df"]
    outmsg = None

    if msgtype == 0:
      outmsg = self.pp0(msg.data, msg.ecc)
    elif msgtype == 4:
      outmsg = self.pp4(msg.data, msg.ecc)
    elif msgtype == 5:
      outmsg = self.pp5(msg.data, msg.ecc)
    elif msgtype == 11:
      outmsg = self.pp11(msg.data, msg.ecc)
    elif msgtype == 17:
      outmsg = self.pp17(msg.data)
    else:
      raise NoHandlerError(msgtype)
    return outmsg

  def pp0(self, shortdata, ecc):
    [datestr, timestr] = self.current_time()
    aircraft_id = self.get_aircraft_id(ecc)
    retstr = "MSG,7,0,%i,%06X,%i,%s,%s,%s,%s,,%s,,,,,,,,,," % (aircraft_id, ecc, aircraft_id+100, datestr, timestr, datestr, timestr, air_modes.decode_alt(shortdata["ac"], True))
    if shortdata["vs"]:
      retstr += "1\r\n"
    else:
      retstr += "0\r\n"
    return retstr

  def pp4(self, shortdata, ecc):
    [datestr, timestr] = self.current_time()
    aircraft_id = self.get_aircraft_id(ecc)
    retstr = "MSG,5,0,%i,%06X,%i,%s,%s,%s,%s,,%s,,,,,,," % (aircraft_id, ecc, aircraft_id+100, datestr, timestr, datestr, timestr, air_modes.decode_alt(shortdata["ac"], True))
    return retstr + self.decode_fs(shortdata["fs"]) + "\r\n"

  def pp5(self, shortdata, ecc):
    [datestr, timestr] = self.current_time()
    aircraft_id = self.get_aircraft_id(ecc)
    retstr = "MSG,6,0,%i,%06X,%i,%s,%s,%s,%s,,,,,,,,%04i," % (aircraft_id, ecc, aircraft_id+100, datestr, timestr, datestr, timestr, air_modes.decode_id(shortdata["id"]))
    return retstr + self.decode_fs(shortdata["fs"]) + "\r\n"

  def pp11(self, shortdata, ecc):
    [datestr, timestr] = self.current_time()
    aircraft_id = self.get_aircraft_id(shortdata["aa"])
    return "MSG,8,0,%i,%06X,%i,%s,%s,%s,%s,,,,,,,,,,,,\r\n" % (aircraft_id, shortdata["aa"], aircraft_id+100, datestr, timestr, datestr, timestr)

  def pp17(self, data):
    icao24 = data["aa"]
    aircraft_id = self.get_aircraft_id(icao24)
    bdsreg = data["me"].get_type()

    retstr = None
    #we'll get better timestamps later, hopefully with actual VRT time
    #in them
    [datestr, timestr] = self.current_time()

    if bdsreg == 0x08:
      # Aircraft Identification
      (msg, typestring) = air_modes.parseBDS08(data)
      retstr = "MSG,1,0,%i,%06X,%i,%s,%s,%s,%s,%s,,,,,,,,,,,\r\n" % (aircraft_id, icao24, aircraft_id+100, datestr, timestr, datestr, timestr, msg)

    elif bdsreg == 0x06:
      # Surface position measurement
      [ground_track, decoded_lat, decoded_lon, rnge, bearing] = air_modes.parseBDS06(data, self._cpr)
      altitude = 0
      if decoded_lat is None: #no unambiguously valid position available
        retstr = None
      else:
        retstr = "MSG,2,0,%i,%06X,%i,%s,%s,%s,%s,,%i,,,%.5f,%.5f,,,,0,0,0\r\n" % (aircraft_id, icao24, aircraft_id+100, datestr, timestr, datestr, timestr, altitude, decoded_lat, decoded_lon)

    elif bdsreg == 0x05:
      # Airborne position measurements
      # WRONG (rnge, bearing), is this still true?
      [altitude, decoded_lat, decoded_lon, rnge, bearing] = air_modes.parseBDS05(data, self._cpr)
      if decoded_lat is None: #no unambiguously valid position available
        retstr = None
      else:
        retstr = "MSG,3,0,%i,%06X,%i,%s,%s,%s,%s,,%i,,,%.5f,%.5f,,,,0,0,0\r\n" % (aircraft_id, icao24, aircraft_id+100, datestr, timestr, datestr, timestr, altitude, decoded_lat, decoded_lon)

    elif bdsreg == 0x09:
      # Airborne velocity measurements
      # WRONG (heading, vert_spd), Is this still true?
      subtype = data["bds09"].get_type()
      if subtype == 0 or subtype == 1:
        parser = air_modes.parseBDS09_0 if subtype == 0 else air_modes.parseBDS09_1
        [velocity, heading, vert_spd] = parser(data)
        retstr = "MSG,4,0,%i,%06X,%i,%s,%s,%s,%s,,,%.1f,%.1f,,,%i,,,,,\r\n" % (aircraft_id, icao24, aircraft_id+100, datestr, timestr, datestr, timestr, velocity, heading, vert_spd)

    return retstr

########NEW FILE########
__FILENAME__ = sql
#
# Copyright 2010 Nick Foster
# 
# This file is part of gr-air-modes
# 
# gr-air-modes is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 3, or (at your option)
# any later version.
# 
# gr-air-modes is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
# 
# You should have received a copy of the GNU General Public License
# along with gr-air-modes; see the file COPYING.  If not, write to
# the Free Software Foundation, Inc., 51 Franklin Street,
# Boston, MA 02110-1301, USA.
# 

import time, os, sys, threading
from string import split, join
import air_modes
import sqlite3
from air_modes.exceptions import *
from gnuradio.gr.pubsub import pubsub

class output_sql:
  def __init__(self, cpr, filename, lock, publisher):
    #pubsub.__init__(self)
    self._cpr = cpr
    self._lock = lock;
    #create the database
    self.filename = filename
    self._db = sqlite3.connect(filename)
    #now execute a schema to create the tables you need
    c = self._db.cursor()
    query = """CREATE TABLE IF NOT EXISTS "positions" (
              "icao" INTEGER KEY NOT NULL,
              "seen" TEXT NOT NULL,
              "alt"  INTEGER,
              "lat"  REAL,
              "lon"  REAL
          );"""
    c.execute(query)
    query = """CREATE TABLE IF NOT EXISTS "vectors" (
              "icao"     INTEGER KEY NOT NULL,
              "seen"     TEXT NOT NULL,
              "speed"    REAL,
              "heading"  REAL,
              "vertical" REAL
          );"""
    c.execute(query)
    query = """CREATE TABLE IF NOT EXISTS "ident" (
              "icao"     INTEGER PRIMARY KEY NOT NULL,
              "ident"    TEXT NOT NULL,
              "type"     TEXT NOT NULL
          );"""
    c.execute(query)
    c.close()
    self._db.commit()
    #we close the db conn now to reopen it in the output() thread context.
    self._db.close()
    self._db = None
    publisher.subscribe("type17_dl", self.insert)

  def insert(self, message):
    with self._lock:
      try:
        #we're checking to see if the db is empty, and creating the db object
        #if it is. the reason for this is so that the db writing is done within
        #the thread context of output(), rather than the thread context of the
        #constructor.
        if self._db is None:
          self._db = sqlite3.connect(self.filename)

        query = self.make_insert_query(message)
        if query is not None:
            c = self._db.cursor()
            c.execute(query)
            c.close()
            self._db.commit()

      except ADSBError:
        pass

  def make_insert_query(self, msg):
    #assembles a SQL query tailored to our database
    #this version ignores anything that isn't Type 17 for now, because we just don't care
    query = None
    msgtype = msg.data["df"]
    if msgtype == 17:
      query = self.sql17(msg.data)
      #self["new_adsb"] = data["aa"] #publish change notification

    return query

#TODO: if there's a way to publish selective reports on upsert to distinguish,
#for instance, between a new ICAO that's just been heard, and a refresh of an
#existing ICAO, both of those would be useful publishers for the GUI model.
#otherwise, worst-case you can just refresh everything every time a report
#comes in, but it's going to use more CPU. Not likely a problem if you're only
#looking at ADS-B (no mode S) data.
#It's probably time to look back at the Qt SQL table model and see if it can be
#bent into shape for you.
  def sql17(self, data):
    icao24 = data["aa"]
    bdsreg = data["me"].get_type()
    #self["bds%.2i" % bdsreg] = icao24 #publish under "bds08", "bds06", etc.

    if bdsreg == 0x08:
      (msg, typename) = air_modes.parseBDS08(data)
      return "INSERT OR REPLACE INTO ident (icao, ident, type) VALUES (" + "%i" % icao24 + ", '" + msg + "', '" + typename + "')"
    elif bdsreg == 0x06:
      [ground_track, decoded_lat, decoded_lon, rnge, bearing] = air_modes.parseBDS06(data, self._cpr)
      altitude = 0
      if decoded_lat is None: #no unambiguously valid position available
        raise CPRNoPositionError
      else:
        return "INSERT INTO positions (icao, seen, alt, lat, lon) VALUES (" + "%i" % icao24 + ", datetime('now'), " + str(altitude) + ", " + "%.6f" % decoded_lat + ", " + "%.6f" % decoded_lon + ")"
    elif bdsreg == 0x05:
      [altitude, decoded_lat, decoded_lon, rnge, bearing] = air_modes.parseBDS05(data, self._cpr)
      if decoded_lat is None: #no unambiguously valid position available
        raise CPRNoPositionError
      else:
        return "INSERT INTO positions (icao, seen, alt, lat, lon) VALUES (" + "%i" % icao24 + ", datetime('now'), " + str(altitude) + ", " + "%.6f" % decoded_lat + ", " + "%.6f" % decoded_lon + ")"
    elif bdsreg == 0x09:
      subtype = data["bds09"].get_type()
      if subtype == 0:
        [velocity, heading, vert_spd, turnrate] = air_modes.parseBDS09_0(data)
        return "INSERT INTO vectors (icao, seen, speed, heading, vertical) VALUES (" + "%i" % icao24 + ", datetime('now'), " + "%.0f" % velocity + ", " + "%.0f" % heading + ", " + "%.0f" % vert_spd + ")"
      elif subtype == 1:
        [velocity, heading, vert_spd] = air_modes.parseBDS09_1(data)
        return "INSERT INTO vectors (icao, seen, speed, heading, vertical) VALUES (" + "%i" % icao24 + ", datetime('now'), " + "%.0f" % velocity + ", " + "%.0f" % heading + ", " + "%.0f" % vert_spd + ")"
      else:
        raise NoHandlerError

########NEW FILE########
__FILENAME__ = types
#
# Copyright 2013 Nick Foster
# 
# This file is part of gr-air-modes
# 
# gr-air-modes is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 3, or (at your option)
# any later version.
# 
# gr-air-modes is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
# 
# You should have received a copy of the GNU General Public License
# along with gr-air-modes; see the file COPYING.  If not, write to
# the Free Software Foundation, Inc., 51 Franklin Street,
# Boston, MA 02110-1301, USA.
#

from collections import namedtuple

#this is a timestamp that preserves precision when used with UTC timestamps.
#ordinary double-precision timestamps lose significant fractional precision
#when the exponent is as large as necessary for UTC.
class stamp:
    def __init__(self, secs, frac_secs):
        self.secs = secs
        self.frac_secs = frac_secs
        self.secs += int(self.frac_secs)
        self.frac_secs -= int(self.frac_secs)
    def __lt__(self, other):
        if isinstance(other, self.__class__):
            if self.secs == other.secs:
                return self.frac_secs < other.frac_secs
            else:
                return self.secs < other.secs
        elif isinstance(other, float):
            return float(self) > other
        else:
            raise TypeError
    def __gt__(self, other):
        if type(other) is type(self):
            if self.secs == other.secs:
                return self.frac_secs > other.frac_secs
            else:
                return self.secs > other.secs
        elif type(other) is type(float):
            return float(self) > other
        else:
            raise TypeError
    def __eq__(self, other):
        if isinstance(other, self.__class__):
            return self.secs == other.secs and self.frac_secs == other.frac_secs
        elif isinstance(other, float):
            return float(self) == other
        else:
            raise TypeError
    def __ne__(self, other):
        return not (self == other)
    def __le__(self, other):
        return (self == other) or (self < other)
    def __ge__(self, other):
        return (self == other) or (self > other)

    def __add__(self, other):
        if isinstance(other, self.__class__):
            ipart = self.secs + other.secs
            fpart = self.frac_secs + other.frac_secs
            return stamp(ipart, fpart)
        elif isinstance(other, float):
            return self + stamp(0, other)
        elif isinstance(other, int):
            return self + stamp(other, 0)            
        else:
            raise TypeError
            
    def __sub__(self, other):
        if isinstance(other, self.__class__):
            ipart = self.secs - other.secs
            fpart = self.frac_secs - other.frac_secs
            return stamp(ipart, fpart)
        elif isinstance(other, float):
            return self - stamp(0, other)
        elif isinstance(other, int):
            return self - stamp(other, 0)
        else:
            raise TypeError

    #to ensure we don't hash by stamp
    #TODO fixme with a reasonable hash in case you feel like you'd hash by stamp
    __hash__ = None
    
    #good to within ms for comparison
    def __float__(self):
        return self.secs + self.frac_secs

    def __str__(self):
        return "%f" % float(self)

#a Mode S report including the modes_reply data object
modes_report = namedtuple('modes_report', ['data', 'ecc', 'rssi', 'timestamp'])
#lat, lon, alt
#TODO: a position class internally represented as ECEF XYZ which can easily be used for multilateration and distance calculation
llh = namedtuple('llh', ['lat', 'lon', 'alt'])
mlat_report = namedtuple('mlat_report', ['data', 'nreps', 'timestamp', 'llh', 'hdop', 'vdop'])

########NEW FILE########
__FILENAME__ = zmq_socket
# Copyright 2013 Nick Foster
# 
# This file is part of gr-air-modes
# 
# gr-air-modes is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 3, or (at your option)
# any later version.
# 
# gr-air-modes is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
# 
# You should have received a copy of the GNU General Public License
# along with gr-air-modes; see the file COPYING.  If not, write to
# the Free Software Foundation, Inc., 51 Franklin Street,
# Boston, MA 02110-1301, USA.

#this serves as a bridge between ZMQ subscriber and the GR pubsub callbacks interface
#creates a thread, publishes socket data to pubsub subscribers
#just a convenient way to create an aggregating socket with callbacks on receive
#can use this for inproc:// signalling with minimal overhead
#not sure if it's a good idea to use this yet

import time
import threading
import zmq
from gnuradio.gr.pubsub import pubsub
import Queue

class zmq_pubsub_iface(threading.Thread):
    def __init__(self, context, subaddr=None, pubaddr=None):
        threading.Thread.__init__(self)
        #private data
        self._queue = Queue.Queue()
        self._subsocket = context.socket(zmq.SUB)
        self._pubsocket = context.socket(zmq.PUB)
        self._subaddr = subaddr
        self._pubaddr = pubaddr
        if type(self._subaddr) is str:
            self._subaddr = [self._subaddr]
        if type(self._pubaddr) is str:
            self._pubaddr = [self._pubaddr]
        self._sub_connected = False
        self._pubsub = pubsub()
        if self._pubaddr is not None:
            for addr in self._pubaddr:
                self._pubsocket.bind(addr)

        self._poller = zmq.Poller()
        self._poller.register(self._subsocket, zmq.POLLIN)
        
        #public data
        self.shutdown = threading.Event()
        self.finished = threading.Event()
        #init
        self.setDaemon(True)
        self.start()

    def subscribe(self, key, subscriber):
        if not self._sub_connected:
            if not self._subaddr:
                raise Exception("No subscriber address set")
            for addr in self._subaddr:
                self._subsocket.connect(addr)
            self._sub_connected = True
        self._subsocket.setsockopt(zmq.SUBSCRIBE, key)
        self._pubsub.subscribe(key, subscriber)

    def unsubscribe(self, key, subscriber):
        self._subsocket.setsockopt(zmq.UNSUBSCRIBE, key)
        self._pubsub.unsubscribe(key, subscriber)

    #executed from the thread context(s) of the caller(s)
    #so we use a queue to push sending into the run loop
    #since sockets must be used in the thread they were created in
    def __setitem__(self, key, val):
        if not self._pubaddr:
            raise Exception("No publisher address set")
        if not self.shutdown.is_set():
            self._queue.put([key, val])

    def __getitem__(self, key):
        return self._pubsub[key]

    def run(self):
        done = False
        while not self.shutdown.is_set() and not done:
            if self.shutdown.is_set():
                done = True
            #send
            while not self._queue.empty():
                self._pubsocket.send_multipart(self._queue.get())
            #receive
            if self._sub_connected:
                socks = dict(self._poller.poll(timeout=0))
                while self._subsocket in socks \
                  and socks[self._subsocket] == zmq.POLLIN:
                    [address, msg] = self._subsocket.recv_multipart()
                    self._pubsub[address] = msg
                    socks = dict(self._poller.poll(timeout=0))
            #snooze
            if not done:
                time.sleep(0.1)

        self._subsocket.close()
        self._pubsocket.close()
        self.finished.set()

    def close(self):
        self.shutdown.set()
        #self._queue.join() #why does this block forever
        self.finished.wait(0.2)

def pr(x):
    print x

if __name__ == "__main__":
    #create socket pair
    context = zmq.Context(1)
    sock1 = zmq_pubsub_iface(context, subaddr="inproc://sock2-pub", pubaddr="inproc://sock1-pub")
    sock2 = zmq_pubsub_iface(context, subaddr="inproc://sock1-pub", pubaddr=["inproc://sock2-pub", "tcp://*:5433"])
    sock3 = zmq_pubsub_iface(context, subaddr="tcp://localhost:5433", pubaddr=None)

    sock1.subscribe("data1", pr)
    sock2.subscribe("data2", pr)
    sock3.subscribe("data3", pr)

    for i in range(10):
        sock1["data2"] = "HOWDY"
        sock2["data3"] = "DRAW"
        sock2["data1"] = "PARDNER"
        time.sleep(0.1)

    time.sleep(0.1)

    sock1.close()
    sock2.close()
    sock3.close()

########NEW FILE########
