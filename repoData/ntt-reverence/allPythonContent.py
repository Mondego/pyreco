__FILENAME__ = datadump
#-----------------------------------------------------------------------------
# Magic Hat - Cache dumping utility by Entity
# Freeware, use at your own risk.
#-----------------------------------------------------------------------------
# Make your own EVE SQL or XML data dump!
#
# Usage:
#
# - Edit the MODE below to XML or SQL depending on what you want
# - Edit the path to the correct location
# - Edit the output path to where you want the dumped data
# - Run script.
#
# Note that the SQL dumps produced are fairly simple and do not include the
# tables.
#-----------------------------------------------------------------------------

# want XML or SQL?
MODE = "XML"

# where is EVE?
EVEPATH = "E:/EVE"

# where to output the dump?
OUTPATH = "N:/temp"

#-----------------------------------------------------------------------------

from reverence import blue
import os

MODE = MODE.upper()
if MODE not in ("SQL", "XML"):
	raise RuntimeError("Unknown Mode:", MODE)

eve = blue.EVE(EVEPATH)
c = eve.getcachemgr()

cachedObjects = c.LoadCacheFolder("BulkData")
cachedObjects2 = c.LoadCacheFolder("CachedObjects")

# bulkdata updates may exist in cache folder. do version check and
# update when necessary.
while cachedObjects2:
	objID, obj = cachedObjects2.popitem()
	if objID in cachedObjects:
		if obj.version < cachedObjects[objID].version:
			continue  # skip, the object is an older version
	cachedObjects[objID] = obj
	
cachedObjects.update()

#-----------------------------------------------------------------------------

def xmlstr(value):
	# returns string that is safe to use in XML
	t = type(value)
	if t in (list, tuple, dict):
		raise ValueError("Unsupported type")
	if t is str:
		return repr(value.replace('&','&amp;').replace('<','&lt;').replace('>','&gt;').replace('"','&quot;').replace("'",'&apos;'))[1:-1]
	elif t is unicode:
		return repr(value.replace('&','&amp;').replace('<','&lt;').replace('>','&gt;').replace('"','&quot;').replace("'",'&apos;'))[2:-1]
	elif t == float:
		return value
	return repr(value)

def sqlstr(x):
	t = type(x)
	if t in (list, tuple, dict):
		raise ValueError("Unsupported type")
	if t is unicode:
		return repr(x)[1:]
	if t is str:
		return repr(x)
	if t is bool:
		return repr(x).lower()
	else:
		r = str(x)
		r = r.replace("e+", "E").replace("e-", "E-")
		if r.endswith(".0"):
			r = r[:-2]
		if r == "None":
			return "null"
		return r

#-----------------------------------------------------------------------------

# see what we can pull out of the hat...
for obj in cachedObjects.itervalues():

	name = filter(lambda x: x not in "()'\" ", str(obj.objectID).replace(",",".").replace('u"', "").replace("u'", ""))
	item = name.split(".")[-1]
	if item.isdigit():
		# stuff ending in numbers is pretty much irrelevant.
		continue

	if item.startswith("Get"):
		item = item[3:]

	print name, "...", 

	thing = obj.GetObject()

	# try to get "universal" header and lines lists by checking what
	# type the object is and grabbing the needed bits.
	header = lines = None
	guid = getattr(thing, "__guid__", None)
	if guid:
		if guid.startswith("util.Row"):
			header, lines = thing.header, thing.lines
		elif guid.startswith("util.IndexRow"):
			header, lines = thing.header, thing.items.values()
		elif guid == "dbutil.CRowset":
			header, lines = thing.header, thing
		elif guid == "dbutil.CIndexedRowset":
			header, lines = thing.header, thing.values()
		elif guid == "util.FilterRowset":
			header = thing.header
			lines = []	
			for stuff in thing.items.itervalues():  # bad way to do this.
				lines += stuff
		else:
			print "UNSUPPORTED (%s)" % guid

	elif type(thing) == tuple:
		if len(thing) == 2:
			header, lines = thing

	elif type(thing) == list:
		row = thing[0]
		if hasattr(row, "__guid__"):
			if row.__guid__ == "blue.DBRow":
				header = row.__header__
				lines = thing
	else:
		print "UNKNOWN (%s)" % type(thing)
		continue

	if not header:
		print "NO HEADER (%s)" % type(thing)
		continue

	if type(header) is blue.DBRowDescriptor:
		header = header.Keys()

	f = []

	# create XML file and dump the lines.
	try:
		if MODE == "XML":
			f.append("<?xml version='1.0' encoding='utf-8'?>\r\n<data>")
			for line in lines:
				f.append("\t<%s>" % item)
				for key,value in zip(header, line):
					if type(key) == tuple:
						key = key[0]
					f.append("\t\t<%s>%s</%s>" % (key, xmlstr(value), key))
				f.append("\t</%s>" % item)
			f.append("</data>")

		elif MODE == "SQL":
			f.append("-- ObjectID: %s" % str(obj.objectID))
			f.append("")
			for line in lines:
				line = ','.join([sqlstr(x) for x in line])
				f.append("INSERT INTO %s (%s) VALUES(%s)" % (item, ','.join(header), line))

		# dump to file
		f2 = open( os.path.join(OUTPATH, name) + "." + MODE.lower(), "w")
		for line in f:
			print >>f2, line
		del f
		f2.close()

		print "OK"
	except:
		print "FAILED"




########NEW FILE########
__FILENAME__ = implants
# Implant summary HTML dump - by Entity
# Spits out neat page for the EVE IGB showing implant hardwirings.
#
# usage: python implants.py >implants.html
#
# This script is freeware. Do whatever you want with it
# Disclaimer: Use at your own risk

evePath = "E:/EVE"

import sys

from reverence import blue, const
from collections import defaultdict

eve = blue.EVE(evePath)
cfg = eve.getconfigmgr()

cats = defaultdict(list)

ignoreGroups = (300, const.groupBooster)

for rec in cfg.invtypes:
	g = rec.Group()
	if g.categoryID == const.categoryImplant and rec.groupID not in ignoreGroups:
		slot = rec.GetTypeAttribute(const.attributeImplantness, 0)
		if slot >= 6 and slot <= 10:
			if rec.name.endswith("I"):
				continue
			if "test " in rec.description.lower():
				continue
			l = cats[g.id].append((slot, rec.name, rec))

print "<html><body>"
print "<H1><u>Entity's Nifty Implant Lookup Page</u></H1><br>"

def mangle(s, c):
	for d in "0123456789":
		s = s.replace(d+".", "%").replace(d, "%")
	while True:
		t = s.replace("%%", "%")
		if t == s:
			return s.replace("%", c)
		s = t

def sortkey(s):
	try:
		return (s[0], mangle(s[1], ""), float(filter("0123456789.".__contains__, s[1]).strip(".")))
	except ValueError:
		return s


def desc(rec, fltr=False):
	d = rec.description
	i = d.rfind("%")
	if i == -1:
		i = d.rfind("0", 0, i)

	if i > -1:
		i = d.rfind(".", 0, i)

	if i > -1:
		d = d[i+1:].strip()

	if fltr:
		for i in range(10):
			d = d.replace(str(i), "x")
		for s in ["x.x ", "+x% ", " x ", "-x%", "x%"]:
			d = d.replace(s, "")

	return d.strip().capitalize()


for groupID in sorted(cats, key=lambda id: cfg.invgroups.Get(id)):
	print "<h2>%s</h2>" % cfg.invgroups.Get(groupID).groupName
	print "<table>"

	last = -1
	lastPrefix = None
	models = []

	all = sorted(cats[groupID], key=sortkey)
	for slot, name, rec in all + [all[0]]:
		prefix = mangle(name, "")

		if lastPrefix and ((lastPrefix != prefix) or (last != -1 and last != slot)):
			models.reverse()

			if models[0].name[-2] != " ":
				print "<tr><td>%d</td><td><b>" % last
				print '<a href="javascript:CCPEVE.showInfo(%d)">%s</a>' % (models[0].typeID, models[0].name),
				if len(models)>1:
					links = [('<a href="javascript:CCPEVE.showInfo(%d)">%s</a>' % (rec2.typeID, rec2.name.rsplit(" ", 1)[1])) for rec2 in models[1:]]
					print " / " + " / ".join(links)

				print "</b><br>"

				print desc(models[0], len(models)>1)

				print "</td></tr>"


			models = []

		models.append(rec)

		if slot != last and last != -1:
			print "<tr><td><br></td><td><br></td></tr>"
		last = slot

		lastPrefix = prefix

	print "<tr><td><br></td><td><br></td></tr>"

	print "</table>"

print "</body></html>"

########NEW FILE########
__FILENAME__ = traits
# Traits printer - by Entity
#
# Lists traits of an item as they would appear ingame.
#
# This script is freeware. Do whatever you want with it
#
# Disclaimer: Use at your own risk
#

# Note: this code uses cfg._localization - this internal attr is subject to change without notice.

EVEROOT = "G:/EVE"  # change me.

import re
from reverence import blue

tags = re.compile("\<.+?\>")

ROLE_BONUS_TYPE = -1
MISC_BONUS_TYPE = -2


def striptags(text):
	return tags.sub("", text)

def printbonuses(bonusdata):
	for bla, data in bonusdata.iteritems():
		if hasattr(data, 'bonus'):
			value = round(data.bonus, 1)
			if int(data.bonus) == data.bonus:
				value = int(data.bonus)
			text = cfg._localization.GetByLabel('UI/InfoWindow/TraitWithNumber', color="", value=value, unit=cfg.dgmunits.Get(data.unitID).displayName, bonusText=cfg._localization.GetByMessageID(data.nameID))
		else:
			text = cfg._localization.GetByLabel('UI/InfoWindow/TraitWithoutNumber', color="", bonusText=cfg._localization.GetByMessageID(data.nameID))

		bonus, text = text.split("<t>")

		print "%8s %s" % (striptags(bonus), striptags(text))


def printtraits(typeID):
	fsdType = cfg.fsdTypeOverrides.Get(typeID)
	if hasattr(fsdType, 'infoBubbleTypeBonuses'):
		typeBonuses = fsdType.infoBubbleTypeBonuses
		for skillTypeID, skillData in typeBonuses.iteritems():
			if skillTypeID <= 0:
				continue

			print cfg._localization.GetByLabel('UI/ShipTree/SkillNameCaption', skillName=cfg.invtypes.Get(skillTypeID).name)
			printbonuses(skillData)

		if ROLE_BONUS_TYPE in typeBonuses:
			print cfg._localization.GetByLabel('UI/ShipTree/RoleBonus')
			printbonuses(typeBonuses[ROLE_BONUS_TYPE])

		elif MISC_BONUS_TYPE in typeBonuses:
			print cfg._localization.GetByLabel('UI/ShipTree/MiscBonus')
			printbonuses(typeBonuses[MISC_BONUS_TYPE])

		return True


if __name__ == "__main__":
	import sys

	if len(sys.argv) != 2:
		print "Usage: %s <typeName>"
		print "Note: typeName is case sensitive!"
		exit(1)

	what = sys.argv[1]

	eve = blue.EVE(EVEROOT, languageID="en-us")
	cfg = eve.getconfigmgr()

	typesByName = cfg.invtypes.IndexedBy("typeName")

	rec = typesByName.GetIfExists(what)
	if not rec:
		print "No such type found: %s" % what
		exit(1)

	if not printtraits(rec.typeID):
		print "No traits for %s" % rec.typeName
	

########NEW FILE########
__FILENAME__ = whmap
#
# K and W space wormhole target class map renderer - by Entity
#
# Renders color-coded wormhole destination map of New Eden and Sleeper galaxy.
#
# Requires:
# - Python Imaging Library
# - Reverence
#
# This map render script is freeware. Do whatever you want with it
#
# Disclaimer: Use at your own risk
#

#-----------------------------------------------------------------------------
# Change the following settings to suit your needs:

EVEROOT = r"E:\EVE"
OUT = r"C:\whtcmap.png"

WIDTH = 1920
HEIGHT = 1200

MARGIN = 20

#-----------------------------------------------------------------------------

mapLeft = MARGIN
mapTop = MARGIN
mapWidth = (WIDTH/2)-(MARGIN*2)
mapHeight = (HEIGHT)-(MARGIN*2)

mapScaleFactor = min(mapWidth, mapHeight) / 2.0

print mapWidth, mapHeight

#-----------------------------------------------------------------------------
from PIL import Image, ImageDraw, ImageFont
from reverence import blue, const

import time

print "Setting up EVE resources..."

eve = blue.EVE(EVEROOT)
cfg = eve.getconfigmgr()

print "Loading map data..."

f = blue.ResFile()
f.Open("res:/UI/Shared/Maps/mapcache.dat")
mapcache = blue.marshal.Load(f.Read())


# first, separate the 2 galaxies...

print "Separating galaxies..."

class DecoDict(dict):
	pass

kspace = DecoDict()
kspace.name = "kspace"

wspace = DecoDict()
wspace.name = "wspace"

for system in mapcache["items"].itervalues():
	if system.item.typeID != const.typeSolarSystem:
		continue

	if str(system.item.itemID)[1] != "1":
		kspace[system.item.itemID] = system
	else:
		wspace[system.item.itemID] = system

print "- kspace has %d systems" % len(kspace)
print "- wspace has %d systems" % len(wspace)

# first, get galaxy widths of both galaxies!

print "Measuring coordinates..."

for galaxy in (kspace, wspace):
	xMin = zMin = None
	xMax = zMax = None
	for system in galaxy.itervalues():
		row = system.item
		xMin, xMax = min(row.x, xMin) if xMin else row.x, max(row.x, xMax) if xMax else row.x
		zMin, zMax = min(row.z, zMin) if zMin else row.z, max(row.z, zMax) if zMax else row.z

	galaxy.xMin, galaxy.xMax = xMin, xMax
	galaxy.zMin, galaxy.zMax = zMin, zMax

	galaxy.width = xMax - xMin
	galaxy.height = zMax - zMin

	print "- %s has dimensions (%s, %s)" % (galaxy.name, galaxy.width, galaxy.height)


frameWidth = max(kspace.width, wspace.width)
frameHeight = max(kspace.height, wspace.height)

# center the coordinates around 0,0

print "Transforming coordinates..."

for idx, galaxy in enumerate((kspace, wspace)):
	for system in galaxy.itervalues():
		# translate
		system.x = system.item.x - galaxy.xMin - (galaxy.width / 2.0)
		system.z = system.item.z - galaxy.zMin - (galaxy.height / 2.0)

		# normalize to -1 .. 1 range
		system.x /= frameWidth / 2.0
		system.z /= frameHeight / 2.0

		if max(abs(system.x), abs(system.z)) > 1:
			print system.x, system.z
			raise "FRACK"

		# scale
		system.x *= mapScaleFactor
		system.z *= mapScaleFactor

		# offset
		system.x += mapWidth / 2.0 + (idx * WIDTH * 0.5)
		system.z += mapHeight / 2.0

		system.coords = (system.x, system.z)


s = time.time()

print "Rendering map..."


#-----------------------------------------------------------------------------
# Init canvas
img = Image.new("RGB", (WIDTH, HEIGHT))
pix = img.load()
draw = ImageDraw.Draw(img)
font = ImageFont.truetype('cour.ttf', 13)


#-----------------------------------------------------------------------------
# Render lines

if 0:
	line = draw.line
	for galaxy in (kspace, wspace):
		seen = {}
		for itemID, system in galaxy.iteritems():
			row, loc, jumps = system.item, system.hierarchy, system.jumps

			fromCoord = system.coords
			# region jumps
			for itemID in (itemID for itemID in jumps[0] if itemID not in seen):
				line([fromCoord, galaxy[itemID].coords], fill=0x7f007f)

			# const jumps
			for itemID in (itemID for itemID in jumps[2] if itemID not in seen):
				line([fromCoord, galaxy[itemID].coords], fill=0x7f0000)

			# normal jumps
			for itemID in (itemID for itemID in jumps[1] if itemID not in seen):
				line([fromCoord, galaxy[itemID].coords], fill=0x00007f)

#-----------------------------------------------------------------------------

classColor = {

	1: (255, 255,   0), # yellow
	2: (  0, 255, 255), # cyan
	3: (  0, 128, 255), # blue
	4: (208,   0, 208), # pink
	5: (128,   0, 224), # purple
	6: ( 64,   0, 128), # darker purple

	7: (  0, 255,   0), # green
	8: (255, 128,  64), # orange
	9: (224,   0,   0), # red

}


wormholes = []
for typeID, groupID, name in cfg.invtypes.Select("typeID", "groupID", "typeName"):
	if groupID != const.groupWormhole:
		continue

	attr = cfg.GetTypeAttrDict(typeID)
	if const.attributeWormholeTargetDistribution in attr:
		whclass = attr[const.attributeWormholeTargetSystemClass]
		wormholes.append((name, whclass))

wormholes.sort()

for whClass in range(1,10):
	y = whClass*15 + 30
	draw.text((1,y), "Class %d:" % whClass , fill=classColor[whClass], font=font)

	# collect wormholes...
	names = []
	for name, whtypeclass in wormholes:
		if whtypeclass == whClass:
			names.append(name[-4:])

	draw.text((80,y), "  ".join(names), fill=0xaaaaaa, font=font)


count = 0
x = 700
y = 15 + 30

tabwidth = font.getsize("XXXX  ")[0]
wordwidth = font.getsize("XXXX")[0]


draw.text((x,y), "Alphabetical list:", fill=0xaaaaaa, font=font)
y += 15

for name, whtypeclass in wormholes:
	if count == 9:
		x = 700
		y += 15
		count = 0

	count += 1
	draw.text((x,y), name[-4:], fill=classColor[whtypeclass], font=font)

	x += tabwidth




draw.text((0,0), "Wormhole Target System Class Map by Entity", fill=0xffffff, font=font)
draw.text((0,15), "The destination wormhole (K162) appears in a system of the same class as the source wormhole (listed below).", fill=0xaaaaaa, font=font)


# Render systems
for galaxy in (kspace, wspace):
	for system in galaxy.itervalues():
		whClass = cfg.GetLocationWormholeClass(system.hierarchy[2], system.hierarchy[1], system.hierarchy[0])
		pix[system.coords] = classColor.get(whClass, 0xffffff)




#-----------------------------------------------------------------------------
# Save

print "Render took %.2f seconds" % (time.time() - s)

print "Saving image to %s..." % OUT

img.save(OUT)

print "All done"
########NEW FILE########
__FILENAME__ = blue
"""Main interface to all the goodies.

Copyright (c) 2003-2012 Jamie "Entity" van den Berge <jamie@hlekkir.com>

This code is free software; you can redistribute it and/or modify
it under the terms of the BSD license (see the file LICENSE.txt
included with the distribution).
"""

import __builtin__
import sys
from time import sleep as _sleep

from ._blue import marshal, DBRow, DBRowDescriptor
from . import exceptions, cache, _os as os, _blue, pyFSD
from reverence.carbon.common.lib.utillib import KeyVal


__all__ = ["EVE", "marshal", "os", "pyos", "DBRow", "DBRowDescriptor"]


# Little hack to have our exceptions look pretty when raised; instead of
#   "reverence.blue.marshal.UnmarshalError: not enough kittens!"
# it will look like
#   "UnmarshalError: not enough kittens!"
# Yes I know this is naughty, but EVE presents them like this as well ;)
marshal.UnmarshalError.__module__ = None

# and because the exception class is accessible like this in EVE ...
exceptions.UnmarshalError = exceptions.SQLError = __builtin__.UnmarshalError = marshal.UnmarshalError

class boot:
	role = "client"

class pyos:
	class synchro:
		@staticmethod
		def Sleep(msec):
			_sleep(msec / 1000.0)


class statistics(object):
	# dummy for compatibility with CCP libs

	@staticmethod
	def EnterZone(*args):
		pass

	@staticmethod
	def LeaveZone():
		pass


class _ResFile(object):
	# read-only resource file handler.

	def __init__(self, rot):
		self.fh = None
		self.rot = rot

	def Open(self, filename):
		self.Close()
		try:
			if filename.startswith("res:"):
				# we gotta have to open a .stuff file...
				try:
					self.fh = self.rot.efs.open("res/" + filename[5:])
				except IndexError, e:
					return None
			elif filename.startswith("cache:"):
				self.fh = open(os.path.join(self.eve.root, "cache", filename[7:]), "rb") 
			else:
				self.fh = open(filename, "rb")
		except IOError:
			pass

		return self.fh

	def Read(self, *args):
		return self.fh.read(*args)

	def Close(self):
		if self.fh:
			self.fh.close()
			self.fh = None

	# ---- custom additions ----

	def read(self, *args):
		return self.fh.read(*args)

	def readline(self):
		return self.fh.readline()

	def seek(self, *args, **kw):
		return self.fh.seek(*args, **kw)


class _Rot(object):
	def __init__(self, eve):
		from . import embedfs
		self.eve = eve
		self.efs = embedfs.EmbedFSDirectory(eve.root)


# offline RemoteSvc wrappers

class _RemoteSvcWrap(object):
	def __init__(self, eve, name):
		self.eve = eve
		self.svcName = name

	def __getattr__(self, methodName):
		return _RemoteSvcMethod(self.eve, self.svcName, methodName)


class _RemoteSvcMethod(object):
	def __init__(self, eve, svcName, methodName):
		self.eve = eve
		self.svcName = svcName
		self.methodName = methodName

	def __call__(self, *args, **kw):
		key = (self.svcName, self.methodName) + args
		obj = self.eve.cache.LoadCachedMethodCall(key)
		return obj['lret']


ResFile = None

class EVE(object):
	"""Interface to an EVE installation's related data.

	provides the following methods:
	getconfigmgr() - creates interface to bulkdata. see config.ConfigMgr.
	getcachemgr() - creates interface to cache. see cache.CacheMgr.
	readstuff(name) - reads the specified file from EVE's virtual file system.
	RemoteSvc(service) - creates offline RemoteSvc wrapper for given service.
	"""

	def __init__(self, root, server="Tranquility", machoVersion=-1, languageID="en-us", cachepath=None, wineprefix=".wine"):
		self.root = root
		self.server = server
		self.rot = _Rot(self)
		self.languageID = languageID

		# default cache
		self.cache = cache.CacheMgr(self.root, self.server, machoVersion, cachepath, wineprefix)
		self.machoVersion = self.cache.machoVersion

		self.cfg = self.cache.getconfigmgr(languageID=self.languageID)
		self.cfg._eve = self

		# hack to make blue.ResFile() work. This obviously means that
		# when using multiple EVE versions, only the latest will be accessible
		# in that manner.
		global ResFile
		ResFile = lambda: _ResFile(self.rot)

	def RemoteSvc(self, service):
		"""Creates a wrapper through which offline remote service methods can be called"""
		return _RemoteSvcWrap(self, service)

	# --- custom additions ---

	def ResFile(self):
		return _ResFile(self.rot)

	def getcachemgr(self):
		"""Return CacheMgr instance through which this EVE's cache can be manually accessed"""
		return self.cache

	def getconfigmgr(self):
		"""Return ConfigMgr instance through which this EVE's bulkdata can be accessed"""
		return self.cfg

	def readstuff(self, name):
		"""Reads specified file in the virtual filesystem"""
		f = _ResFile(self.rot)
		f.Open(name)
		return f.read()




def _readstringstable():
	from . import strings

	marshal._stringtable[:] = strings.stringTable
	#marshal._stringtable_rev.clear()

	#c = 1
	#for line in strings.stringsTable:
	#	marshal._stringtable_rev[line] = c
	#	c+=1




def _find_global(module, name):
	# locates a global. used by marshal.Load and integrated unpickler

	# compatibility
	if module in ("util", "utillib") and name == "KeyVal":
		return KeyVal
	try:
		m = __import__(module, globals(), locals(), (), -1)
	except ImportError:
		raise RuntimeError("Unable to locate object: " + module + "." + name + " (import failed)")

	try:
		return getattr(m, name)
	except AttributeError:
		raise RuntimeError("Unable to locate object: " + module + "." + name + " (not in module)")


def _debug(*args):
	print >>sys.stderr, args[0].Keys(), args


# __str__ function for DBRow objects. This is done in python because it would
# take considerably more effort to implement in C. It's not the most efficient
# way to display DBRows, but quite useful for debugging or inspection.
_fmt = u"%s:%s".__mod__
def dbrow_str(row):
	return "DBRow(" + ','.join(map(_fmt, zip(row.__keys__, row))) + ")"
_blue.dbrow_str = dbrow_str


# set the helper functions in the marshaller and init strings table
marshal._set_find_global_func(_find_global)
marshal._set_debug_func(_debug)
_readstringstable()

# hack to make CCP zip libs accept our not-exactly-the-same environment
sys.modules["blue"] = sys.modules["reverence.blue"]

# and this one to make CCP's FSD loader import pyFSD succesfully
sys.modules["pyFSD"] = pyFSD

__builtin__.boot = boot


########NEW FILE########
__FILENAME__ = cache
"""Interface to cache and bulkdata. Primarily used by ConfigMgr.

Copyright (c) 2003-2012 Jamie "Entity" van den Berge <jamie@hlekkir.com>

This code is free software; you can redistribute it and/or modify
it under the terms of the BSD license (see the file LICENSE.txt
included with the distribution).
"""

from __future__ import with_statement

import sys
import os
import glob
import platform
import time
import cPickle
import binascii

from . import config
from . import _blue as blue  # can't simply import blue (circular import). only using marshal anyway.

__all__ = ["GetCacheFileName", "CacheMgr"]

_join = os.path.join
_exists = os.path.exists


def GetCacheFileName(key, machoVersion=99999):
	"""Returns filename for specified object name."""
	if machoVersion >= 213:
		# BEGIN UGLY HACK ----------------------------------------------------
		# CCP is relying on pickle to produce consistent output, which it does
		# not because pickle's output depends on the refcount of objects; an
		# object referenced only once will not get memoized. Cache keys are
		# seemingly always created by EVE with refcounts >1. When Reverence
		# decodes them, they only have a refcount of 1. This code ensures that
		# those refcounts are increased so cPickle produces the correct output
		# when you feed a decoded object's key to this function.
		# (and no, copy.deepcopy doesn't work as expected on tuples)
		memoize = [].append
		def increase_refcounts(k):
			if type(k) is tuple:
				for element in k:
					increase_refcounts(element)
			memoize(k)
		increase_refcounts(key)
		# END UGLY HACK ------------------------------------------------------

		return "%x.cache" % binascii.crc_hqx(cPickle.dumps(key), 0)
	else:
		raise RuntimeError("machoNet version 213 or higher required")


def _readfile(filename):
	with open(filename, "rb") as f:
		return f.read()


_localappdata = None

def _find_appdata_path(root, servername, wineprefix):
	# returns (root, appdatapath) tuple where eve stuff may be found.
	global _localappdata

	if os.name == "nt":
		cacheFolderName = root.lower().replace(":", "").replace("\\", "_").replace(" ", "_")
		cacheFolderName += "_"+servername.lower()

		if _localappdata is None:
			from ctypes import wintypes, windll, c_int
			CSIDL_LOCAL_APPDATA = 28
			path_buf = wintypes.create_unicode_buffer(wintypes.MAX_PATH)
			result = windll.shell32.SHGetFolderPathW(0, CSIDL_LOCAL_APPDATA, 0, 0, path_buf)
			if result:
				if result < 0:
					result += 0x100000000
				raise RuntimeError("SHGetFolderPath failed, error code 0x%08x" % result)
			_localappdata = path_buf.value

		appdatapath = _join(_localappdata, "CCP", "EVE", cacheFolderName)

	elif sys.platform == "darwin" or os.name == "mac":
		# slightly less untested. might still be wrong.
		home = os.path.expanduser('~')
		cacheFolderName = "c_program_files_ccp_eve_" + servername.lower()
		appdatapath = _join(home, "Library/Application Support/EVE Online/p_drive/Local Settings/Application Data/CCP/EVE", cacheFolderName)
		if not _exists(appdatapath):
			appdatapath = _join(home, "Library/Preferences/EVE Online Preferences/p_drive/Local Settings/Application Data/CCP/EVE", cacheFolderName)
		actualroot = _join(root, "Contents/Resources/transgaming/c_drive/Program Files/CCP/EVE")
		if _exists(actualroot):
			root = actualroot

	elif os.name == "posix" or os.name == "linux2":
		import pwd

		# Assuming a WINE install, we are now going to have to do
		# some black magic to figure out where the cache folder is.

		# get the name of the owner of this EVE folder. This is
		# quite likely to be the user used in WINE as well.
		stat_info = os.stat(root)
		user = pwd.getpwuid(stat_info.st_uid).pw_name

		# get the filesystem root for WINE
		x = root.find(_join(wineprefix, "drive_"))
		if x == -1:
			return (None, None)

		wineroot = root[:x+len(wineprefix)]  # all drive_ folders be here

		# now we can get the cache folder name (as produced by EVE
		# from the install path by mangling separators and spaces)
		cacheFolderName = root[x+len(wineprefix)+7:].replace("/", "_").replace(" ", "_")
		cacheFolderName += "_" + servername
		cacheFolderName = cacheFolderName.lower()

		# locate that cache folder. the names of the folders here
		# depend on the locale of the Windows version used, so we
		# cheat past that with a glob match.
		for appdataroot in [
			_join(wineroot, "drive_c/users", user),
			_join(wineroot, "drive_c/windows/profile", user),
			_join(wineroot, "drive_c/windows/profiles", user),
		]:
			if not _exists(appdataroot):
				continue

			for appdatapath in glob.iglob(_join(appdataroot, "*/*/CCP/EVE/" + cacheFolderName)):
				# this should only ever give one folder.
				break
			else:
				# no cache folder found? user must have a really
				# freakin' bizarre install. screw that!
				continue

			# cache folder found, no need to continue.
			break

	else:
		return (None, None)

	return (root, appdatapath)



class CacheMgr:
	"""Interface to an EVE Installation's cache and bulkdata."""

	def __init__(self, root, servername="Tranquility", machoversion=-1, appdatapath=None, wineprefix=".wine"):
		self.cfg = None
		self._time_load = 0.0

		# get cache folder servername and machonet server ip.
		# the servername should be equal to what was used in the /server option
		# of the EVE shortcut, even if it's an IP address.

		serveraliases = {
			"tranquility": "87.237.38.200",
			"singularity": "87.237.38.50",
			"duality": "87.237.38.60",
			"serenity":"211.144.214.68",
		}

		if servername.replace(".","").isdigit():
			serverip = servername
		else:
			serverip = serveraliases.get(servername.lower(), None)

		if serverip is None:
			raise ValueError("Invalid server name '%s'. Valid names are '%s' or an IP address." %\
				(servername, "', '".join((x.capitalize() for x in serveraliases))))

		if serverip == "87.237.38.200":
			servername = "Tranquility"
		elif serverip == "211.144.214.68":
			servername = "211.144.214.68"

		#---------------------

		if root is None:
			# I -was- going to put auto path discovery here but EVE's install
			# folder(s) can be pretty elusive :)
			raise ValueError("No EVE install root path specified")

		root = os.path.abspath(root)

		candidates = []
		discover = appdatapath is None  # used further down too.
		if discover:
			# auto-discovery of appdata path. try a few places...
			candidates = [
				(root, _join(root, "")),
				_find_appdata_path(root, servername, wineprefix),
			]
		else:
			# manually specified cachepath! only look there.
			candidates.append((root, appdatapath))

		#---------------------

		self.machoVersion = -1

		cachenotfound = machonotfound = False

		for root, appdatapath in candidates:
			if root is None:
				continue

			if not _exists(appdatapath):
				cachenotfound = True
				continue

			machopath = _join(appdatapath, "cache", "MachoNet", serverip)
			bulkcpath = _join(appdatapath, "cache", "bulkdata")

			if machoversion > -1:
				# machoversion was specified, so look for just that.
				machocachepath = _join(machopath, str(machoversion))
				bulkdatapath = _join(bulkcpath, str(machoversion))
				if _exists(machocachepath) or _exists(bulkdatapath):
					protocol = machoversion
				else:
					machonotfound = True
					continue
			else:
				# machoversion not specified, find highest.
				protocol = -1

				# look in cache/MachoNet as well as cache/bulkdata
				for scandir in (machopath, bulkcpath):
					for dirName in glob.glob(_join(scandir, "*")):
						candidate = os.path.basename(dirName)
						if candidate.isdigit():
							protocol = max(protocol, int(candidate))

				if protocol == -1:
					machonotfound = True

			if protocol > self.machoVersion:
				self.machoVersion = protocol
				self.root = root
				self.appdatapath = appdatapath
				self.cachepath = _join(appdatapath, "cache")
				self.settingspath = _join(appdatapath, "settings")
				self.machocachepath = _join(machopath, str(protocol))
				self.BULK_SYSTEM_PATH = _join(root, 'bulkdata')
				self.BULK_CACHE_PATH = _join(appdatapath, 'cache', 'bulkdata', str(protocol))
				return

		if self.machoVersion == -1:
			if machonotfound:
				if machoversion == -1:
					raise RuntimeError("Could not determine MachoNet protocol version.")
				else:
					raise RuntimeError("Specified protocol version (%d) not found in MachoNet cache." % machoversion)

			if cachenotfound:
				if discover:
					raise RuntimeError("Could not determine EVE cache folder location.")
				else:
					raise RuntimeError("Specified cache folder does not exist: '%s'" % cachepath)


	def GetCacheFileName(self, key):
		"""Returns the filename for specified object name."""
		return GetCacheFileName(key, self.machoVersion)


	def LoadCacheFolder(self, name, filter="*.cache"):
		"""Loads all .cache files from specified folder. Returns a dict keyed on object name."""

		# Note that this method is used mainly for debugging and testing,
		# and is subject to change without notice.
		crap = {}
		for filename in glob.glob(_join(name, filter)):
			what, obj = blue.marshal.Load(_readfile(filename))
			crap[what] = obj
		return crap


	def _loadobject(self, key, canraise=False, folder=None):
		name = _join(self.machocachepath, folder, self.GetCacheFileName(key))
		if not canraise:
			if not _exists(name):
				return None

		what, obj = blue.marshal.Load(_readfile(name))
		if what != key:
			# Oops. We did not get what we asked for...
			if canraise:
				raise RuntimeError("Hash collision: Wanted '%s' but got '%s'" % (key, what))
			return None

		return obj


	def LoadCachedMethodCall(self, key):
		"""Loads a named object from EVE's CachedMethodCalls folder."""
		return self._loadobject(key, True, "CachedMethodCalls")

	def LoadCachedObject(self, key):
		"""Loads a named object from EVE's CachedObjects folder."""
		return self._loadobject(key, True, "CachedObjects")

	def LoadObject(self, key):
		"""Load named object from cache, or None if it is not available."""
		return self._loadobject(key, False, "CachedObjects")


	def LoadBulk(self, bulkID):
		"""Loads bulkdata for the specified bulkID"""
		for folder in (self.BULK_CACHE_PATH, self.BULK_SYSTEM_PATH):
			cacheName = _join(folder, str(bulkID)+".cache2")
			if _exists(cacheName):
				# No version check required.
				_t = time.clock()
				obj = blue.marshal.Load(_readfile(cacheName))
				self._time_load += (time.clock() - _t)
				return obj


	def FindCacheFile(self, key):
		"""Attempts to locate a cache file in any of the cache locations."""
		fileName = self.GetCacheFileName(key)
		for cacheName in [
			_join(self.machocachepath, "CachedObjects", fileName),
			_join(self.machocachepath, "CachedMethodCalls", fileName),
			_join(self.machocachepath, "MethodCallCachingDetails", fileName),
		]:
			if _exists(cacheName):
				return cacheName
		return None


	def find(self, key):
		"""Locates and loads a cache object. will check version and contents."""
		fileName = self.GetCacheFileName(key)
		obj = (key, None)
		version = (0L, 0)
		for cacheName in [
			_join(self.machocachepath, "CachedObjects", fileName),
			_join(self.machocachepath, "CachedMethodCalls", fileName),
			_join(self.machocachepath, "MethodCallCachingDetails", fileName),
		]:
			if _exists(cacheName):
				blurb = _readfile(cacheName)
				_t = time.clock()
				what, obj2 = blue.marshal.Load(blurb)
				self._time_load += (time.clock() - _t)

				if what == key:
					if obj2.version > version:
						obj = (what, obj2)
						version = obj2.version

		return fileName, obj


	def findbulk(self, bulkID):
		"""Locates bulkdata file by ID."""
		for folder in (self.BULK_CACHE_PATH, self.BULK_SYSTEM_PATH):
			cacheName = _join(folder, str(bulkID)+".cache2")
			if _exists(cacheName):
				return cacheName


	def getconfigmgr(self, *args, **kw):
		"""Returns a ConfigMgr instance associated with this CacheMgr."""
		if not self.cfg:
			self.cfg = config.Config(self, *args, **kw)

		return self.cfg


########NEW FILE########
__FILENAME__ = utillib
"""Data container class

This code is free software; you can redistribute it and/or modify
it under the terms of the BSD license (see the file LICENSE.txt
included with the distribution).

Parts of code inspired by or based on EVE Online, with permission from CCP.
"""

class KeyVal:
	__guid__ = "util.KeyVal"
	def __repr__(self):
		return "Anonymous KeyVal: %s" % self.__dict__

########NEW FILE########
__FILENAME__ = cachedObject

class CachedObject:
	def __setstate__(self, state):
		pass



########NEW FILE########
__FILENAME__ = GPSExceptions
"""CCP Exception containers

This code is free software; you can redistribute it and/or modify
it under the terms of the BSD license (see the file LICENSE.txt
included with the distribution).

Parts of code inspired by or based on EVE Online, with permission from CCP.
"""

import types

from reverence import _blue as blue

class GPSException(StandardError):
	__guid__ = 'exceptions.GPSException'
	def __init__(self, reason):
		self.reason = reason

	def __str__(self):
		return repr(self)

	def __repr__(self):
		return "<%s: reason=%s>" % (self.__class__.__name__, self.reason)


class GPSTransportClosed(GPSException):
	__guid__ = 'exceptions.GPSTransportClosed'
	def __init__(self, reason):
		bootver = reason.rfind("bootver=")
		if bootver > 0:
			self.version, self.build, self.codename = blue.marshal.Load(reason[bootver+8:].decode("hex"))
			reason = reason[:bootver]
		GPSException.__init__(self,reason)


class GPSBadAddress(GPSException):
	__guid__ = 'exceptions.GPSBadAddress'
	def __init__(self, reason):
		GPSException.__init__(self, reason)


class GPSAddressOccupied(GPSException):
	__guid__ = 'exceptions.GPSAddressOccupied'
	def __init__(self, reason):
		GPSException.__init__(self, reason)

__all__ = [
	"GPSException",
	"GPSTransportClosed",
	"GPSBadAddress",
	"GPSAddressOccupied",
]


########NEW FILE########
__FILENAME__ = objectCaching
"""Cached object envelope classes.

This code is free software; you can redistribute it and/or modify
it under the terms of the BSD license (see the file LICENSE.txt
included with the distribution).

Parts of code inspired by or based on EVE Online, with permission from CCP.
"""

import zlib

from reverence import blue, util

class CachedMethodCallResult:
	__guid__ = "objectCaching.CachedMethodCallResult"
	__passbyvalue__ = 1

	def __setstate__(self, state):
		self.details, self.result, self.version = state

	def GetResult(self):
		if isinstance(self.result, util.CachedObject):
			return self.result.GetCachedObject()
		else:
			return blue.marshal.Load(self.result)

class CachedObject:
	__guid__ = "objectCaching.CachedObject"

	def __getstate__(self):
		if self.pickle is None:
			import blue
			if self.isCompressed:
				self.pickle = zlib.compress(blue.marshal.Save(self.object), 1)
			else:
				self.pickle = blue.marshal.Save(self.object)

		return (self.version, None, self.nodeID, self.shared, self.pickle, self.isCompressed, self.objectID,)

	def __setstate__(self,state):
		self.version, self.object, self.nodeID, self.shared, self.pickle, self.isCompressed, self.objectID = state

	def GetCachedObject(self):
		if self.object is None:
			if self.pickle is None:
				raise RuntimeError, "Wtf? no object?"
			if self.isCompressed:
				self.object = blue.marshal.Load(zlib.decompress(self.pickle))
			else:
				self.object = blue.marshal.Load(self.pickle)
			self.pickle = None
		return self.object

	GetObject = GetCachedObject


########NEW FILE########
__FILENAME__ = crowset
class CIndexedRowset(dict):
	__guid__ = "dbutil.CIndexedRowset"
    
	def __init__(self, header, columnName):
		self.header = header
		self.columnName = columnName


class CFilterRowset(dict):
	__guid__ = "dbutil.CFilterRowset"

	def __setstate__(self, data):
		self.__dict__.update(data)  # header and columnName

	def __getstate__(self):
		return {"header": self.header, "columnName": self.columnName}


class CRowset(list):
	__guid__ = "dbutil.CRowset"
	__passbyvalue__	 = 1
	
	def __init__(self, header, rows):
		list.__init__(self, rows)
		self.header = header

	def Sort(self, columnName, caseInsensitive = False):
		ix = self.header.Keys().index(columnName)
		if caseInsensitive:
			self.sort(key=lambda x: x[ix].upper())
		else:			
			self.sort(key=lambda x: x[ix])

	def Index(self, columnName):
		d = CIndexedRowset(self.header, columnName)

		if "." in columnName:		
			keys = columnName.split(".")
			c = 0

			for row in self:
				combinedKey = []
				for key in keys:
					combinedKey.append(row[key])
				d[tuple(combinedKey)] = row
	
			return d
		else:
			pass

	def Filter(self, columnName, indexName=None):
		fr = CFilterRowset(self.header, columnName)

		c = 0
		keyIdx = fr.header.Keys().index(columnName)
		_get = dict.get
		if indexName is None:
			for row in self:
				key = row[keyIdx]
				grp = _get(fr, key)
				if grp is None:
					fr[key] = [row]
				else:
					grp.append(row)
		else:
			key2Idx = fr.header.Keys().index(indexName)
			for row in self:
				key = row[keyIdx]
				key2 = row[key2Idx]
				if key not in fr:
					fr[key] = {}
				fr[key][key2] = row

		return  fr


########NEW FILE########
__FILENAME__ = row
"""Container classes for DBRow/DBRowset

Copyright (c) 2003-2013 Jamie "Entity" van den Berge <jamie@hlekkir.com>

This code is free software; you can redistribute it and/or modify
it under the terms of the BSD license (see the file LICENSE.txt
included with the distribution).

Part of this code is inspired by or based on EVE Online.
Used with permission from CCP.
"""

class Row:
	__guid__ = "util.Row"
	__passbyvalue__ = 1

	def __init__(self, header=None, line=None, cfgInstance=None):
		self.header = header or []
		self.line = line or []
		self.cfg = cfgInstance

	def __ne__(self, other):
		return self.__cmp__(other)

	def __eq__(self, other):
		return self.__cmp__(other) == 0

	def __cmp__(self, other):
		if not isinstance(other, Row):
			raise TypeError("Incompatible comparison type")
		return cmp(self.header, other.header) or cmp(self.line, other.line)

	def __str__(self):
		if self.__class__ is Row:
			# bare row class, use shortcut
			return "Row(" + ','.join(map(lambda k, v: "%s:%s" % (unicode(k), unicode(v)), self.header, self.line)) + ")"
		else:
			# assume it has custom attribute handling (e.g. invtypes)
			return "Row(" + ','.join(map(lambda k, v: "%s:%s" % (unicode(k), unicode(v)), self.header, map(self.__getattr__, self.header))) + ")"

	__repr__ = __str__

	def __nonzero__(self):
		return True

	def __getattr__(self, this):
		try:
			return self.line[self.header.index(this)]
		except ValueError:
			raise AttributeError, this

	def __getitem__(self, this):
		return self.line[self.header.index(this)]



########NEW FILE########
__FILENAME__ = config
"""Interface to bulkdata

- loads and prepares the bulkdata for use (on demand)
- provides container classes for record and row data.
- provides interface to the database tables

Copyright (c) 2003-2013 Jamie "Entity" van den Berge <jamie@hlekkir.com>

This code is free software; you can redistribute it and/or modify
it under the terms of the BSD license (see the file LICENSE.txt
included with the distribution).

Parts of code inspired by or based on EVE Online, with permission from CCP.
"""

import sys
import os
import time
import sqlite3
import glob
import logging

from . import _blue as blue
from . import const, util
from . import localization, fsd

# custom row containers are imported from this
from .eve.common.script.sys.eveCfg import *
from .eve.common.script.sys.rowset import IndexRowset, FilterRowset, IndexedRowLists



# used by GetLocationsLocalBySystem method
_solarSystemObjectRowDescriptor = blue.DBRowDescriptor((
	('groupID', const.DBTYPE_I4),
	('typeID', const.DBTYPE_I4),
	('itemID', const.DBTYPE_I4),
	('itemName', const.DBTYPE_WSTR),
	('locationID', const.DBTYPE_I4),
	('orbitID', const.DBTYPE_I4),
	('connector', const.DBTYPE_BOOL),
	('x', const.DBTYPE_R8),
	('y', const.DBTYPE_R8),
	('z', const.DBTYPE_R8),
))


# Warning: Code below may accidentally your whole brain.

class _memoize(object):
	# This class is a getter. On attribute access, it will call the method it
	# decorates and replace the attribute value (which is the getter instance)
	# with the value returned by that method. Used to implement the
	# load-on-access mechanism 

	__slots__ = ["method"]

	def __init__(self, func):
		self.method = func

	def __get__(self, obj, type=None):
		if obj is None:
			# class attribute (descriptor itself)
			return self
		else:
			# instance attribute (replaced by value)
			value = self.method(obj)
			setattr(obj, self.method.func_name, value)
			return value


def _loader(attrName):
	# Creates a closure used as a method in Config class (to be decorated with
	# _memoize) that loads a specific bulkdata table.
	def method(self):
		entry = self._tables[attrName]
		if len(entry) == 6:
			# bulkID loader
			ver, rem, storageClass, rowClass, primaryKey, bulkID = entry
			return self._loadbulkdata(tableName=attrName, storageClass=storageClass, rowClass=rowClass, primaryKey=primaryKey, bulkID=bulkID)

		if len(entry) == 4:
			# FSD loader
			ver, rem, (staticName, schemaName, optimize), cacheNum = entry
			return self._loadfsddata(staticName, schemaName, cacheNum, optimize=optimize)

	method.func_name = attrName
	return method


class _tablemgr(type):
	# Creates decorated methods in the Config class that handle loading of
	# bulkdata tables on accessing the attributes those methods are bound as.
	# Note: tables that require non-standard handling will need methods for
	# that (decorated with @_memoize) in Config class.

	def __init__(cls, name, bases, dict):
		type.__init__(cls, name, bases, dict)
		for attrName, x in cls.__tables__:
			if hasattr(cls, attrName):
				# specialized loader method exists.
				continue
			setattr(cls, attrName, _memoize(_loader(attrName)))


class Config(object):
	__metaclass__ = _tablemgr

	"""Interface to bulkdata.

	EVE's database is available as attributes of instances of this class.
    Tables are transparently loaded from bulkdata/cache upon accessing such an
    attribute. Because this automatic loading scheme is NOT thread-safe, the
    prime() method should be called prior to allowing other threads access to
    the instance.
    """

	__containercategories__ = (
		const.categoryStation,
		const.categoryShip,
		const.categoryTrading,
		const.categoryStructure,
	)

	__containergroups__ = (
		const.groupCargoContainer,
		const.groupSecureCargoContainer,
		const.groupAuditLogSecureContainer,
		const.groupFreightContainer,
		const.groupConstellation,
		const.groupRegion,
		const.groupSolarSystem,
		const.groupMissionContainer,
		const.groupSpewContainer,
	)

	__chargecompatiblegroups__ = (
		const.groupFrequencyMiningLaser,
		const.groupEnergyWeapon,
		const.groupProjectileWeapon,
		const.groupMissileLauncher,
		const.groupCapacitorBooster,
		const.groupHybridWeapon,
		const.groupScanProbeLauncher,
		const.groupComputerInterfaceNode,
		const.groupMissileLauncherBomb,
		const.groupMissileLauncherCruise,
		const.groupMissileLauncherDefender,
		const.groupMissileLauncherAssault,
		const.groupMissileLauncherSiege,
		const.groupMissileLauncherHeavy,
		const.groupMissileLauncherHeavyAssault,
		const.groupMissileLauncherRocket,
		const.groupMissileLauncherStandard,
		const.groupMissileLauncherCitadel,
		const.groupMissileLauncherFestival,
		const.groupBubbleProbeLauncher,
		const.groupSensorBooster,
		const.groupRemoteSensorBooster,
		const.groupRemoteSensorDamper,
		const.groupTrackingComputer,
		const.groupTrackingDisruptor,
		const.groupTrackingLink,
		const.groupWarpDisruptFieldGenerator,
		const.groupFueledShieldBooster,
		const.groupFueledArmorRepairer,
		const.groupSurveyProbeLauncher,
		const.groupMissileLauncherRapidHeavy,
		const.groupDroneTrackingModules,
	)


	#-------------------------------------------------------------------------------------------------------------------
	# BulkData Table Definitions.
	# ver            - minimum machoNet version required to load this table with prime() method
	# del            - starting from this machoNet version the table no longer exists
	# cfg attrib     - name the table is accessed with in cfg.* (e.g. cfg.invtypes)
	# bulkdata name  - name of the bulkdata in the cache file if not same as cfg attrib, else None.
	# storage class  - container class for the table data. can be string to generate FilterRowset from named table.
	# row class      - the class used to wrap rows with when they are requested.
	# primary key    - primary key
	# bulkID         - bulkdata file ID
	#
	# this table is filtered for every instance to create a table dict containing only those entries relevant
	# to its protocol version.
	__tables__ = (

#		( cfg attrib                  , (ver, del, storage class       , row class         , primary key           bulkID)),
		("invcategories"              , (  0,   0, IndexRowset         , InvCategory       , "categoryID"        , const.cacheInvCategories)),
		("invgroups"                  , (  0,   0, IndexRowset         , InvGroup          , "groupID"           , const.cacheInvGroups)),
		("invtypes"                   , (  0,   0, IndexRowset         , InvType           , "typeID"            , const.cacheInvTypes)),
		("invmetagroups"              , (  0,   0, IndexRowset         , InvMetaGroup      , "metaGroupID"       , const.cacheInvMetaGroups)),
		("invbptypes"                 , (  0,   0, IndexRowset         , Row               , "blueprintTypeID"   , const.cacheInvBlueprintTypes)),
		("invreactiontypes"           , (  0,   0, FilterRowset        , Row               , "reactionTypeID"    , const.cacheInvTypeReactions)),
		("shiptypes"                  , (  0,   0, IndexRowset         , Row               , "shipTypeID"        , const.cacheShipTypes)),

		("dgmattribs"                 , (  0,   0, IndexRowset         , DgmAttribute      , "attributeID"       , const.cacheDogmaAttributes)),
		("dgmeffects"                 , (  0,   0, IndexRowset         , DgmEffect         , "effectID"          , const.cacheDogmaEffects)),
		("dgmtypeattribs"             , (  0,   0, IndexedRowLists     , None              , ('typeID',)         , const.cacheDogmaTypeAttributes)),
		("dgmtypeeffects"             , (  0,   0, IndexedRowLists     , None              , ('typeID',)         , const.cacheDogmaTypeEffects)),
		("dgmexpressions"             , (297,   0, IndexRowset         , Row               , 'expressionID'      , const.cacheDogmaExpressions)),
		("dgmunits"                   , (299,   0, IndexRowset         , DgmUnit           , "unitID"            , const.cacheDogmaUnits)),

		("ramaltypes"                 , (  0,   0, IndexRowset         , Row               , "assemblyLineTypeID", const.cacheRamAssemblyLineTypes)),
		("ramactivities"              , (  0,   0, IndexRowset         , RamActivity       , "activityID"        , const.cacheRamActivities)),
		("ramcompletedstatuses"       , (276,   0, IndexRowset         , RamCompletedStatus, "completedStatus"   , const.cacheRamCompletedStatuses)),
		("ramaltypesdetailpercategory", (  0,   0, FilterRowset        , RamDetail         , "assemblyLineTypeID", const.cacheRamAssemblyLineTypesCategory)),
		("ramaltypesdetailpergroup"   , (  0,   0, FilterRowset        , RamDetail         , "assemblyLineTypeID", const.cacheRamAssemblyLineTypesGroup)),

		("billtypes"                  , (  0,   0, IndexRowset         , Billtype          , 'billTypeID'        , const.cacheActBillTypes)),

		("schematics"                 , (242,   0, IndexRowset         , Schematic         , 'schematicID'       , const.cachePlanetSchematics)),
		("ramtyperequirements"        , (242,   0, dict                , None              , ('typeID', 'activityID'), const.cacheRamTypeRequirements)),
		("invtypematerials"           , (254,   0, dict                , None              , 'typeID'            , const.cacheInvTypeMaterials)),

		# location/owner stuff.
		("factions"                   , (276,   0, IndexRowset         , Row               , "factionID"         , const.cacheChrFactions)),
		("npccorporations"            , (276,   0, IndexRowset         , Row               , "corporationID"     , const.cacheCrpNpcCorporations)),
		("corptickernames"            , (  0,   0, IndexRowset         , CrpTickerNames    , "corporationID"     , const.cacheCrpTickerNamesStatic)),

		("staoperationtypes"          , (299,   0, IndexRowset         , Row               , "operationID"       , const.cacheStaOperations)),
		("mapcelestialdescriptions"   , (276,   0, IndexRowset         , MapCelestialDescription, "itemID"       , const.cacheMapCelestialDescriptions)),
		("locationwormholeclasses"    , (  0,   0, IndexRowset         , Row               , "locationID"        , const.cacheMapLocationWormholeClasses)),

		("stations"                   , (299,   0, IndexRowset         , Row               , "stationID"         , const.cacheStaStationsStatic)),

		("nebulas"                    , (299,   0, IndexRowset         , Row               , "locationID"        , const.cacheMapNebulas)),

		# autogenerated FilterRowsets from some of the above tables
		("groupsByCategories"         , (  0,   0, "invgroups"         , None              , "categoryID"        , None)),
		("typesByGroups"              , (  0,   0, "invtypes"          , None              , "groupID"           , None)),
		("typesByMarketGroups"        , (  0,   0, "invtypes"          , None              , "marketGroupID"     , None)),

		# tables that have custom loaders
		("eveowners"                  , (299,   0)),
		("evelocations"               , (299,   0)),
		("invmetatypes"               , (  0,   0)),
		("invmetatypesByTypeID"       , (  0,   0)),
		("invcontrabandTypesByFaction", (  0,   0)),
		("invcontrabandTypesByType"   , (  0,   0)),
		("schematicstypemap"          , (242,   0)),
		("schematicsByType"           , (242,   0)),
		("schematicspinmap"           , (242,   0)),
		("schematicsByPin"            , (242,   0)),

		# FSD stuff ------------------- (ver, del,  static name       , schema name       , optimize   cache size)
		("messages"                   , (378,   0, ("dialogs"         , "dialogs"         , False)   , None)),

		("fsdTypeOverrides"           , (324,   0, ("typeIDs"         , "typeIDs"         , False)   , None)),

		("graphics"                   , (324,   0, ("graphicIDs"      , "graphicIDs"      , True)    , 100 )),
		("sounds"                     , (332,   0, ("soundIDs"        , "soundIDs"        , True)    , 100 )),
		("icons"                      , (332,   0, ("iconIDs"         , "iconIDs"         , True)    , 100 )),
		("fsdDustIcons"               , (378,   0, ("dustIcons"       , None              , None )   , None)),

		("certificates"               , (391,   0, ("certificates"    , "certificates"    , False)   , None)),

		("mapRegionCache"             , (393,   0, ("regions"         , "regions"         , False)   , None)),
		("mapConstellationCache"      , (393,   0, ("constellations"  , "constellations"  , False)   , None)),
		("mapSystemCache"             , (393,   0, ("systems"         , "systems"         , False)   , None)),

		("mapJumpCache"               , (393,   0, ("jumps"           , "jumps"           , False)   , None)),

		("mapFactionsOwningSolarSystems",(393,  0, ("factionsOwningSolarSystems", "factionsOwningSolarSystems", False), None)),
		("mapCelestialLocationCache"  , (393,   0, ("locationCache"   , None              , None )   , None)),

		("mapSolarSystemContentCache" , (393,   0, ("solarSystemContent", None            , None )   , None)),
	)


	# Custom table loader methods follow

	@_memoize
	def eveowners(self):
		bloodlinesToTypes = {
			const.bloodlineDeteis   : const.typeCharacterDeteis,
			const.bloodlineCivire   : const.typeCharacterCivire,
			const.bloodlineSebiestor: const.typeCharacterSebiestor,
			const.bloodlineBrutor   : const.typeCharacterBrutor,
			const.bloodlineAmarr    : const.typeCharacterAmarr,
			const.bloodlineNiKunni  : const.typeCharacterNiKunni,
			const.bloodlineGallente : const.typeCharacterGallente,
			const.bloodlineIntaki   : const.typeCharacterIntaki,
			const.bloodlineStatic   : const.typeCharacterStatic,
			const.bloodlineModifier : const.typeCharacterModifier,
			const.bloodlineAchura   : const.typeCharacterAchura,
			const.bloodlineJinMei   : const.typeCharacterJinMei,
			const.bloodlineKhanid   : const.typeCharacterKhanid,
			const.bloodlineVherokior: const.typeCharacterVherokior
		}

		rs = IndexRowset(['ownerID', 'ownerName', 'typeID', 'gender', 'ownerNameID'], None, key="ownerID", RowClass=EveOwners, cfgInstance=self)
		d = rs.items

		rd = blue.DBRowDescriptor((
			('ownerID', const.DBTYPE_I4),
			('ownerName', const.DBTYPE_WSTR),
			('typeID', const.DBTYPE_I2),
			('gender', const.DBTYPE_I2),
			('ownerNameID', const.DBTYPE_I4),
		))

		DBRow = blue.DBRow
		for row in self.factions:
			id_ = row.factionID
			d[id_] = DBRow(rd, [id_, row.factionName, const.typeFaction, 0, row.factionNameID])

		for row in self.npccorporations:
			id_ = row.corporationID
			d[id_] = DBRow(rd, [id_, row.corporationName, const.typeCorporation, 0, row.corporationNameID])

		for row in self.cache.LoadBulk(const.cacheChrNpcCharacters):
			id_ = row.characterID
			npcName = self._localization.GetImportantByMessageID(id_) or row.characterName
			d[id_] = DBRow(rd, [id_, row.characterName, bloodlinesToTypes[row.bloodlineID], row.gender, row.characterNameID])

		auraName = self._localization.GetImportantByLabel(_OWNER_NAME_OVERRIDES[_OWNER_AURA_IDENTIFIER])
		sysName = self._localization.GetByLabel(_OWNER_NAME_OVERRIDES[_OWNER_SYSTEM_IDENTIFIER])

		d[1] = blue.DBRow(rd, [1, sysName, 0, None, None])

		rs.lines = rs.items.values()
		return rs


	@_memoize
	def evelocations(self):
		rs = IndexRowset(['locationID', 'locationName', 'x', 'y', 'z', 'locationNameID'], None, key="locationID", RowClass=EveLocations, cfgInstance=self)

		rd = blue.DBRowDescriptor((
			('locationID', const.DBTYPE_I4),
			('locationName', const.DBTYPE_WSTR),
			('x', const.DBTYPE_R8),
			('y', const.DBTYPE_R8),
			('z', const.DBTYPE_R8),
			('locationNameID', const.DBTYPE_I4),
		))

		DBRow = blue.DBRow

		_trans = self._localization.GetImportantByMessageID
		d = rs.items
		for fsdtable in (self.mapRegionCache, self.mapConstellationCache, self.mapSystemCache):
			for itemID, item in fsdtable.iteritems():
				c = item.center
				d[itemID] = DBRow(rd, [itemID, _trans(item.nameID), c.x, c.y, c.z, item.nameID])

		# code below requires the partially completed table.
		self.evelocations = rs

#		# This stuff below takes 12 seconds on my i7.
#		# TODO: find solution (dynamic lookup, I suppose ...)
#
#		# get stars, planets, belts and moons.
#		for row in self.localdb.execute("SELECT * FROM celestials"):
#			celestialName = self.GetCelestialNameFromLocalRow(row)
#			cid = row["celestialID"]
#			d[cid] = blue.DBRow(rd, [cid, celestialName, row["x"], row["y"], row["z"], 0])
#
#		# stations
#		_gbm = self._localization.GetByMessageID
#		_gbl = self._localization.GetByLabel
#		_sot = self.staoperationtypes.Get
#		for row in self.localdb.execute("SELECT * FROM npcStations"):
#			if row["isConquerable"]:
#				continue
#			stationID = row["stationID"]
#			operationName = _gbm(_sot(row["operationID"]).operationNameID) if row["useOperationName"] else ""
#			stationName = _gbl('UI/Locations/LocationNPCStationFormatter', orbitID=row["orbitID"], corporationID=row["ownerID"], operationName=operationName)
#			d[stationID] = DBRow(rd, [stationID, stationName, row["x"], row["y"], row["z"], 0])

		rs.lines = rs.items.values()

		return rs


	#--

	def _invcontrabandtypes_load(self):
		byFaction = self.invcontrabandTypesByFaction = {}
		byType = self.invcontrabandFactionsByType = {}

		obj = self.cache.LoadBulk(const.cacheInvContrabandTypes)

		for each in obj:
			typeID = each.typeID
			factionID = each.factionID

			if factionID in byFaction:
				byFaction[factionID][typeID] = each
			else:
				byFaction[factionID] = {typeID:each}

			if typeID in byType:
				byType[typeID][factionID] = each
			else:
				byType[typeID] = {factionID: each}

	@_memoize
	def invcontrabandTypesByFaction(self):
		self._invcontrabandtypes_load()
		return self.invcontrabandTypesByFaction

	@_memoize
	def invcontrabandTypesByType(self):
		self._invcontrabandtypes_load()
		return self.invcontrabandFactionsByType


	#--

	def _schematicstypemap_load(self):
		obj = self.cache.LoadBulk(const.cachePlanetSchematicsTypeMap)
		header = obj.header.Keys()
		self.schematicstypemap = FilterRowset(header, obj, "schematicID")
		self.schematicsByType = FilterRowset(header, obj, "typeID")

	@_memoize
	def schematicstypemap(self):
		self._schematicstypemap_load()
		return self.schematicstypemap

	@_memoize
	def schematicsByType(self):
		self._schematicstypemap_load()
		return self.schematicsByType

	#--

	def _schematicspinmap_load(self):
		obj = self.cache.LoadBulk(const.cachePlanetSchematicsPinMap)
		header = obj.header.Keys()
		self.schematicspinmap = FilterRowset(header, obj, "schematicID")
		self.schematicsByPin = FilterRowset(header, obj, "pinTypeID")

	@_memoize
	def schematicspinmap(self):
		self._schematicspinmap_load()
		return self.schematicspinmap

	@_memoize
	def schematicsByPin(self):
		self._schematicspinmap_load()
		return self.schematicsByPin

	#--

	def _invmetatypes_load(self):
		obj = self.cache.LoadBulk(const.cacheInvMetaTypes)
		header = obj.header.Keys()
		self.invmetatypes = FilterRowset(header, obj, "parentTypeID")
		self.invmetatypesByTypeID = FilterRowset(header, obj, "typeID")

	@_memoize
	def invmetatypes(self):
		self._invmetatypes_load()
		return self.invmetatypes

	@_memoize
	def invmetatypesByTypeID(self):
		self._invmetatypes_load()
		return self.invmetatypesByTypeID

	#--

	@_memoize
	def _localization(self):
		return localization.Localization(self.cache.root, self._languageID, cfgInstance=self)

	@_memoize
	def _averageMarketPrice(self):
		return self._eve.RemoteSvc("config").GetAverageMarketPricesForClient()

	#--

	def __init__(self, cache, languageID=None):
		self.cache = cache
		self.callback = None
		protocol = self.protocol = self.cache.machoVersion
		self._languageID = languageID

		# Figure out the set of tables managed by this instance.
		# Only tables that are available for this instance's particular
		# machoNet version will be in this set, and are the only tables loaded
		# when prime() is called.
		self._tables = dict(((k, v) for k, v in self.__tables__ if protocol >= v[0] and protocol < (v[1] or 2147483647)))
		self.tables = frozenset(( \
			attrName for attrName in dir(self.__class__) \
			if attrName[0] != "_" \
			and attrName in self._tables \
			and isinstance(getattr(self.__class__, attrName), _memoize) \
			and protocol >= self._tables[attrName][0] \
			and protocol < (self._tables[attrName][1] or 2147483647) \
		))
		self._attrCache = {}

		self.localdb = sqlite3.connect(os.path.join(self.cache.root, "bin", "staticdata", "mapObjects.db"))
		self.localdb.row_factory = sqlite3.Row


		# DEPRECATED: look for fsd library in EVE install
		ccplibpath = os.path.join(self.cache.root, "lib")

		for fsdlib in glob.glob(os.path.join(ccplibpath, "fsdSchemas-*.zip")):
			break
		else:
			fsdlib = ccplibpath if os.path.exists(os.path.join(ccplibpath, "fsdCommon")) else None
		
		if fsdlib:
			sys.path.append(fsdlib)

			# import the important function!
			import fsdSchemas.binaryLoader as fsdBinaryLoader
			self._fsdBinaryLoader = fsdBinaryLoader

			fsdBinaryLoader.log.setLevel(-1)  # shut logging up

			# All set to use EVE's FSD code directly.
			# (patch the instance to use the alternative loader)
			self._loadfsddata = self._loadfsddata_usingccplib
		

	def release(self):
		# purge all loaded tables

		for tableList in (self.tables, ("_averageMarketPrice",)):
			for tableName in tableList:
				try:
					delattr(self, tableName)
				except AttributeError:
					pass

		self.cache._time_load = 0.0
		self._attrCache = {}


	def _loadfsddata_usingccplib(self, staticName, schemaName, cacheNum, optimize):
		# odyssey fsd loader (uses CCP code directly)
		# deprecated in ody1.1, but still works if fsd lib is present
		from . import blue as bloo

		# must patch our ResFile temporarily for CCP code to work.
		_rf = bloo.ResFile
		bloo.ResFile = self._eve.ResFile

		try:
			if optimize is None:
				optimize = True
			staticName = 'res:/staticdata/%s.static' % staticName
			schemaName = 'res:/staticdata/%s.schema' % schemaName if schemaName else None
			return self._fsdBinaryLoader.LoadFSDDataForCFG(staticName, schemaName, optimize=optimize)
		finally:
			bloo.ResFile = _rf


	def _loadfsddata(self, staticName, schemaName, cacheNum, optimize):
		# Custom FileStaticData loader.
		# Grabs schema and binary blob from .stuff file.
		res = self._eve.ResFile()

		schema = None
		if staticName:
			resFileName = "res:/staticdata/%s.schema" % schemaName
			if res.Open(resFileName):
				schema = fsd.LoadSchema(res.Read())
				if optimize:
					schema = fsd.OptimizeSchema(schema)

		resFileName = "res:/staticdata/%s.static" % staticName
		if not res.Open(resFileName):
			raise RuntimeError("Could not load FSD static data '%s'" % resFileName)

		try:
			# This will throw an error if there is no embedded schema.
			# As it is hardcoded in EVE whether a static data file comes
			# with an embedded schema, we just try to load it anyway.
			# if it fails, the previously loaded schema should still be there.
			schema, offset = fsd.LoadEmbeddedSchema(res.fh)
		except RuntimeError:
			offset = 0

		if schema is None:
			raise RuntimeError("No schema found for %s" % tableName)

		fsd.PrepareSchema(schema)

		if schema.get('multiIndex'):
			# Disk-based access for multi index tables because only the
			# FSD_MultiIndex class can handle them properly.
			return fsd.LoadIndexFromFile(res.fh, schema, cacheNum, offset=offset)

		# any other table will use memory-based access because they are pretty
		# small anyway, and they are considerably faster when used like this.
		return fsd.LoadFromString(res.Read(), schema)


	def _loadbulkdata(self, tableName=None, storageClass=None, rowClass=None, primaryKey=None, bulkID=None):

		if type(storageClass) is str:
			# create a FilterRowset from existing table named by storageClass.
			table = getattr(self, storageClass)
			rs = table.GroupedBy(primaryKey)
			return rs

		obj = self.cache.LoadBulk(bulkID)
		if obj is None:
			raise RuntimeError("Unable to load '%s' (bulkID:%d)" % (tableName, bulkID))
		
		if issubclass(storageClass, IndexRowset):
			rs = storageClass(obj.header.Keys(), obj, key=primaryKey, RowClass=rowClass, cfgInstance=self)

		elif issubclass(storageClass, FilterRowset):
			rs = storageClass(obj.header.Keys(), obj, primaryKey, RowClass=rowClass)

		elif issubclass(storageClass, IndexedRowLists):
			rs = storageClass(obj, keys=primaryKey)

		elif issubclass(storageClass, dict):
			rs = {}
			if type(primaryKey) is tuple:
				# composite key
				getkey = lambda r, k: tuple(map(r.__getitem__, k))
			else:
				getkey = getattr

			_get = rs.get
			for row in obj:
				key = getkey(row, primaryKey)
				li = _get(key)
				if li is None:
					rs[key] = [row]
				else:
					li.append(row)
		else:
			raise RuntimeError("Invalid storageClass: %s" % storageClass)

		return rs


	def prime(self, tables=None, callback=None, debug=False, onlyFSD=False):
		"""Loads the tables named in the tables sequence. If no tables are
specified, it will load all supported ones. A callback function can be provided
which will be called as func(current, total, tableName).

		This method should be used in the following situations:
		- The ConfigMgr instance is going to be used in a multi-threaded app.
		- The Application wants to load all data at once instead of on access.
		"""

		if debug:
			self._debug = True
			start = time.clock()
			print >>sys.stderr, "LOADING STATIC DATABASE"
			print >>sys.stderr, "  machoCachePath:", self.cache.machocachepath
			print >>sys.stderr, "  machoVersion:", self.cache.machoVersion
			print >>sys.stderr, "  bulk system path:", self.cache.BULK_SYSTEM_PATH
			print >>sys.stderr, "  bulk cache path:", self.cache.BULK_CACHE_PATH
		try:
			if tables is None:
				# preload everything.
				tables = self.tables
			else:
				# preload specified only.
				tables = frozenset(tables)
				invalid = tables - self.tables
				if invalid:
					raise ValueError("Unknown table(s): %s" % ", ".join(invalid))

			current = 0
			total = len(tables)
		
			for tableName in tables:
				if onlyFSD and len(self._tables[tableName]) != 4:
					continue

				if callback:
					callback(current, total, tableName)
					current += 1

				if debug:
					print >>sys.stderr, "  priming:", tableName
				# now simply trigger the property's getters
				getattr(self, tableName)

		finally:
			if debug:
				self._debug = False

		if debug:
			t = time.clock() - start
			print >>sys.stderr, "Priming took %ss (of which %.4f decoding)" % (t, self.cache._time_load)


	def GetTypeVolume(self, typeID, singleton=1, qty=1):
		"""Returns total volume of qty units of typeID. 
		Uses packaged volume if singleton is non-zero.
		"""
		if typeID == const.typePlasticWrap:
			raise RuntimeError("GetTypeVolume: cannot determine volume of plastic from type alone")

		rec = cfg.invtypes.Get(typeID)
		volume = rec.volume
		if not singleton and typeID != const.typeBHMegaCargoShip:
			volume = const.shipPackagedVolumesPerGroup.get(rec.groupID, volume)

		if volume != -1:
			return volume * qty

		return volume


	def GetTypeAttrDict(self, typeID):
		"""Returns (cached) dictionary of attributes for specified type."""
		attr = self._attrCache.get(typeID, None)
		if attr is None:
			self._attrCache[typeID] = attr = {}
			for row in self.dgmtypeattribs[typeID]:
				attr[row.attributeID] = row.value
		return attr


	def GetRequiredSkills(self, typeID):
		"""Returns list of (requiredSkillTypeID, requiredLevel) tuples."""
		attr = self.GetTypeAttrDict(typeID)
		reqs = []
		for i in xrange(1, 7):
			skillID = attr.get(getattr(const, "attributeRequiredSkill%s" % i), False)
			if skillID:
				lvl = attr.get(getattr(const, "attributeRequiredSkill%sLevel" % i), None)
				if lvl is not None:
					reqs.append((skillID, lvl))
		return reqs


	def GetTypeAttribute(self, typeID, attributeID, defaultValue=None):
		"""Return specified dogma attribute for given type, or custom default value."""
		attr = self.GetTypeAttrDict(typeID)
		return attr.get(attributeID, defaultValue)


	def GetTypeAttribute2(self, typeID, attributeID):
		"""Return specified dogma attribute for given type, or default attribute value."""
		attr = self.GetTypeAttrDict(typeID)
		value = attr.get(attributeID)
		if value is None:
			return self.dgmattribs.Get(attributeID).defaultValue
		return value


	def GetLocationWormholeClass(self, solarSystemID, constellationID, regionID):
		get = self.locationwormholeclasses.Get
		rec = get(solarSystemID) or get(constellationID) or get(regionID)
		if rec:
			return rec.wormholeClassID
		return 0


	def GetCelestialNameFromLocalRow(self, row):
		# row keys:
		# ['celestialID', 'celestialNameID', 'solarSystemID', 'typeID', 'groupID', 'radius', 'x', 'y', 'z', 'orbitID', 'orbitIndex', 'celestialIndex']

		celestialGroupID = row['groupID']
		celestialNameID = row['celestialNameID']

		if celestialNameID is not None and celestialGroupID != const.groupStargate:
			label = 'UI/Util/GenericText'
			param = {'text': celestialNameID}
		elif celestialGroupID == const.groupAsteroidBelt:
			label = 'UI/Locations/LocationAsteroidBeltFormatter'
			param = {'solarSystemID': row['solarSystemID'], 'romanCelestialIndex': util.IntToRoman(row['celestialIndex']), 'typeID': row['typeID'], 'orbitIndex': row['orbitIndex']}
		elif celestialGroupID == const.groupMoon:
			label = 'UI/Locations/LocationMoonFormatter'
			param = {'solarSystemID': row['solarSystemID'], 'romanCelestialIndex': util.IntToRoman(row['celestialIndex']), 'orbitIndex': row['orbitIndex']}
		elif celestialGroupID == const.groupPlanet:
			label = 'UI/Locations/LocationPlanetFormatter'
			param = {'solarSystemID': row['solarSystemID'], 'romanCelestialIndex': util.IntToRoman(row['celestialIndex'])}
		elif celestialGroupID == const.groupStargate:
			label = 'UI/Locations/LocationStargateFormatter'
			param = {'destinationSystemID': row['celestialNameID']}
		elif celestialGroupID == const.groupSun:
			label = 'UI/Locations/LocationStarFormatter'
			param = {'solarSystemID': row['solarSystemID']}
		else:
			label = None
			param = None

		return self._localization.GetByLabel(label, **param)


	def GetNPCStationNameFromLocalRow(self, row):
		operationName = self._localization.GetByMessageID(self.staoperationtypes.Get(row['operationID']).operationNameID) if row['useOperationName'] else ""
		return self._localization.GetByLabel('UI/Locations/LocationNPCStationFormatter', orbitID=row['orbitID'], corporationID=row['ownerID'], operationName=operationName)


	def GetLocationsLocalBySystem(self, solarSystemID):
		data = []

		# local aliasing ftw.
		append = data.append
		DBRow = blue.DBRow
		get = self.invtypes.Get

		sql = 'SELECT * FROM celestials WHERE solarSystemID=%d' % solarSystemID
		rs = self.localdb.execute(sql)
		for row in rs:
			celestialName = self.GetCelestialNameFromLocalRow(row)
			append(DBRow(_solarSystemObjectRowDescriptor, [
				row['groupID'], row['typeID'], row['celestialID'],
				celestialName, solarSystemID, row['orbitID'], None,
				row['x'], row['y'], row['z']
			]))

		sql = 'SELECT * FROM npcStations WHERE solarSystemID=%d' % solarSystemID
		rs = self.localdb.execute(sql)
		for row in rs:
			celestialName = self.GetNPCStationNameFromLocalRow(row)
			append(DBRow(_solarSystemObjectRowDescriptor, [
				get(row['typeID']).groupID, row['typeID'], row['stationID'],
				celestialName, solarSystemID, row['orbitID'], None,
				row['x'], row['y'], row['z']
			]))

		return dbutil.CRowset(_solarSystemObjectRowDescriptor, data)

########NEW FILE########
__FILENAME__ = const
"""EVE constants.

This code is free software; you can redistribute it and/or modify
it under the terms of the BSD license (see the file LICENSE.txt
included with the distribution).

Part of this code is inspired by or based on EVE Online.
Used with permission from CCP.
"""

minDustTypeID = 350000

ACT_IDX_START = 0
ACT_IDX_DURATION = 1
ACT_IDX_ENV = 2
ACT_IDX_REPEAT = 3

dgmAssPreAssignment = -1
dgmAssPreMul = 0
dgmAssPreDiv = 1
dgmAssModAdd = 2
dgmAssModSub = 3
dgmAssPostMul = 4
dgmAssPostDiv = 5
dgmAssPostPercent = 6
dgmAssPostAssignment = 7

dgmEnvSelf = 0
dgmEnvChar = 1
dgmEnvShip = 2
dgmEnvTarget = 3
dgmEnvOther = 4
dgmEnvArea = 5

dgmEffActivation = 1
dgmEffArea = 3
dgmEffOnline = 4
dgmEffPassive = 0
dgmEffTarget = 2
dgmEffOverload = 5
dgmEffDungeon = 6
dgmEffSystem = 7

dgmTauConstant = 10000

flagAutoFit = 0
flagBonus = 86
flagBooster = 88
flagBriefcase = 6
flagCapsule = 56
flagCargo = 5
flagCorpMarket = 62
flagCorpSAG2 = 116
flagCorpSAG3 = 117
flagCorpSAG4 = 118
flagCorpSAG5 = 119
flagCorpSAG6 = 120
flagCorpSAG7 = 121
flagDroneBay = 87
flagFactoryOperation = 100
flagFixedSlot = 35
flagHangar = 4
flagHangarAll = 1000
flagImplant = 89
flagLocked = 63
flagNone = 0
flagPilot = 57
flagReward = 8
flagSecondaryStorage = 122
flagShipHangar = 90
flagShipOffline = 91
flagSkill = 7
flagSkillInTraining = 61
flagSlotFirst = 11
flagSlotLast = 35
flagUnlocked = 64
flagWallet = 1
flagJunkyardReprocessed = 146
flagJunkyardTrashed = 147
flagWardrobe = 3

flagLoSlot0 = 11
flagLoSlot1 = 12
flagLoSlot2 = 13
flagLoSlot3 = 14
flagLoSlot4 = 15
flagLoSlot5 = 16
flagLoSlot6 = 17
flagLoSlot7 = 18

flagMedSlot0 = 19
flagMedSlot1 = 20
flagMedSlot2 = 21
flagMedSlot3 = 22
flagMedSlot4 = 23
flagMedSlot5 = 24
flagMedSlot6 = 25
flagMedSlot7 = 26

flagHiSlot0 = 27
flagHiSlot1 = 28
flagHiSlot2 = 29
flagHiSlot3 = 30
flagHiSlot4 = 31
flagHiSlot5 = 32
flagHiSlot6 = 33
flagHiSlot7 = 34

flagRigSlot0 = 92
flagRigSlot1 = 93
flagRigSlot2 = 94
flagRigSlot3 = 95
flagRigSlot4 = 96
flagRigSlot5 = 97
flagRigSlot6 = 98
flagRigSlot7 = 99

flagSubSystemSlot0 = 125
flagSubSystemSlot1 = 126
flagSubSystemSlot2 = 127
flagSubSystemSlot3 = 128
flagSubSystemSlot4 = 129
flagSubSystemSlot5 = 130
flagSubSystemSlot6 = 131
flagSubSystemSlot7 = 132


categoryAbstract = 29
categoryAccessories = 5
categoryAncientRelic = 34
categoryApparel = 30
categoryAsteroid = 25
categoryWorldSpace = 26
categoryBlueprint = 9
categoryBonus = 14
categoryCelestial = 2
categoryCharge = 8
categoryCommodity = 17
categoryDecryptors = 35
categoryDeployable = 22
categoryDrone = 18
categoryEntity = 11
categoryImplant = 20
categoryInfantry = 350001
categoryMaterial = 4
categoryModule = 7
categoryOrbital = 46
categoryOwner = 1
categoryPlaceables = 49
categoryPlanetaryCommodities = 43
categoryPlanetaryInteraction = 41
categoryPlanetaryResources = 42
categoryReaction = 24
categoryShip = 6
categorySkill = 16
categorySovereigntyStructure = 40
categoryStation = 3
categoryStructure = 23
categoryStructureUpgrade = 39
categorySubSystem = 32
categorySpecialEditionAssets = 63
categorySystem = 0
categoryTrading = 10

groupAccelerationGateKeys = 474
groupAfterBurner = 46
groupAgentsinSpace = 517
groupAlliance = 32
groupAncientCompressedIce = 903
groupAncientSalvage = 966
groupArkonor = 450
groupArmorPlatingEnergized = 326
groupArmorHardener = 328
groupArmorReinforcer = 329
groupArmorRepairUnit = 62
groupArmorRepairProjector = 325
groupArmorResistanceShiftHardener = 1150
groupAssemblyArray = 397
groupAsteroidAngelCartelBattleCruiser = 576
groupAsteroidAngelCartelBattleship = 552
groupAsteroidAngelCartelCommanderBattleCruiser = 793
groupAsteroidAngelCartelCommanderCruiser = 790
groupAsteroidAngelCartelCommanderDestroyer = 794
groupAsteroidAngelCartelCommanderFrigate = 789
groupAsteroidAngelCartelCruiser = 551
groupAsteroidAngelCartelDestroyer = 575
groupAsteroidAngelCartelFrigate = 550
groupAsteroidAngelCartelHauler = 554
groupAsteroidAngelCartelOfficer = 553
groupAsteroidBelt = 9
groupAsteroid = 25
groupAsteroidBloodRaidersBattleCruiser = 578
groupAsteroidBloodRaidersBattleship = 556
groupAsteroidBloodRaidersCommanderBattleCruiser = 795
groupAsteroidBloodRaidersCommanderCruiser = 791
groupAsteroidBloodRaidersCommanderDestroyer = 796
groupAsteroidBloodRaidersCommanderFrigate = 792
groupAsteroidBloodRaidersCruiser = 555
groupAsteroidBloodRaidersDestroyer = 577
groupAsteroidBloodRaidersFrigate = 557
groupAsteroidBloodRaidersHauler = 558
groupAsteroidBloodRaidersOfficer = 559
groupAsteroidGuristasBattleCruiser = 580
groupAsteroidGuristasBattleship = 560
groupAsteroidGuristasCommanderBattleCruiser = 797
groupAsteroidGuristasCommanderCruiser = 798
groupAsteroidGuristasCommanderDestroyer = 799
groupAsteroidGuristasCommanderFrigate = 800
groupAsteroidGuristasCruiser = 561
groupAsteroidGuristasDestroyer = 579
groupAsteroidGuristasFrigate = 562
groupAsteroidGuristasHauler = 563
groupAsteroidGuristasOfficer = 564
groupAsteroidRogueDroneBattleCruiser = 755
groupAsteroidRogueDroneBattleship = 756
groupAsteroidRogueDroneCruiser = 757
groupAsteroidRogueDroneDestroyer = 758
groupAsteroidRogueDroneFrigate = 759
groupAsteroidRogueDroneHauler = 760
groupAsteroidRogueDroneSwarm = 761
groupAsteroidRogueDroneOfficer = 1174
groupAsteroidSanshasNationBattleCruiser = 582
groupAsteroidSanshasNationBattleship = 565
groupAsteroidSanshasNationCommanderBattleCruiser = 807
groupAsteroidSanshasNationCommanderCruiser = 808
groupAsteroidSanshasNationCommanderDestroyer = 809
groupAsteroidSanshasNationCommanderFrigate = 810
groupAsteroidSanshasNationCruiser = 566
groupAsteroidSanshasNationDestroyer = 581
groupAsteroidSanshasNationFrigate = 567
groupAsteroidSanshasNationHauler = 568
groupAsteroidSanshasNationOfficer = 569
groupAsteroidSerpentisBattleCruiser = 584
groupAsteroidSerpentisBattleship = 570
groupAsteroidSerpentisCommanderBattleCruiser = 811
groupAsteroidSerpentisCommanderCruiser = 812
groupAsteroidSerpentisCommanderDestroyer = 813
groupAsteroidSerpentisCommanderFrigate = 814
groupAsteroidSerpentisCruiser = 571
groupAsteroidSerpentisDestroyer = 583
groupAsteroidSerpentisFrigate = 572
groupAsteroidSerpentisHauler = 573
groupAsteroidSerpentisOfficer = 574
groupAsteroidRogueDroneCommanderFrigate = 847
groupAsteroidRogueDroneCommanderDestroyer = 846
groupAsteroidRogueDroneCommanderCruiser = 845
groupAsteroidRogueDroneCommanderBattleCruiser = 843
groupAsteroidRogueDroneCommanderBattleship = 844
groupAsteroidAngelCartelCommanderBattleship = 848
groupAsteroidBloodRaidersCommanderBattleship = 849
groupAsteroidGuristasCommanderBattleship = 850
groupAsteroidSanshasNationCommanderBattleship = 851
groupAsteroidSerpentisCommanderBattleship = 852
groupMissionAmarrEmpireCarrier = 865
groupMissionCaldariStateCarrier = 866
groupMissionContainer = 952
groupMissionGallenteFederationCarrier = 867
groupMissionMinmatarRepublicCarrier = 868
groupMissionFighterDrone = 861
groupMissionGenericFreighters = 875
groupAssaultShip = 324
groupAttackBattlecruiser = 1201
groupAuditLogSecureContainer = 448
groupBattlecruiser = 419
groupBattleship = 27
groupBeacon = 310
groupBillboard = 323
groupBiohazard = 284
groupBiomass = 14
groupBistot = 451
groupBlackOps = 898
groupBlockadeRunner = 1202
groupBooster = 303
groupBubbleProbeLauncher = 589
groupCapDrainDrone = 544
groupCapacitorBooster = 76
groupCapacitorBoosterCharge = 87
groupCapitalIndustrialShip = 883
groupCapsule = 29
groupCapsuleerBases = 1082
groupCapturePointTower = 922
groupCargoContainer = 12
groupCarrier = 547
groupCharacter = 1
groupCheatModuleGroup = 225
groupCloakingDevice = 330
groupClone = 23
groupCloud = 227
groupCombatDrone = 100
groupComet = 305
groupCommandPins = 1027
groupCommandShip = 540
groupCommodities = 526
groupComposite = 429
groupComputerInterfaceNode = 317
groupConcordDrone = 301
groupConstellation = 4
groupConstructionPlatform = 307
groupControlBunker = 925
groupControlTower = 365
groupConvoy = 297
groupConvoyDrone = 298
groupCorporateHangarArray = 471
groupCorporation = 2
groupCosmicAnomaly = 885
groupCosmicSignature = 502
groupCovertBeacon = 897
groupCovertOps = 830
groupCrokite = 452
groupCruiser = 26
groupStrategicCruiser = 963
groupCustomsOfficial = 446
groupCynosuralGeneratorArray = 838
groupCynosuralSystemJammer = 839
groupDamageControl = 60
groupDarkOchre = 453
groupDataInterfaces = 716
groupDatacores = 333
groupDeadspaceAngelCartelBattleCruiser = 593
groupDeadspaceAngelCartelBattleship = 594
groupDeadspaceAngelCartelCruiser = 595
groupDeadspaceAngelCartelDestroyer = 596
groupDeadspaceAngelCartelFrigate = 597
groupDeadspaceBloodRaidersBattleCruiser = 602
groupDeadspaceBloodRaidersBattleship = 603
groupDeadspaceBloodRaidersCruiser = 604
groupDeadspaceBloodRaidersDestroyer = 605
groupDeadspaceBloodRaidersFrigate = 606
groupDeadspaceGuristasBattleCruiser = 611
groupDeadspaceGuristasBattleship = 612
groupDeadspaceGuristasCruiser = 613
groupDeadspaceGuristasDestroyer = 614
groupDeadspaceGuristasFrigate = 615
groupDeadspaceOverseer = 435
groupDeadspaceOverseersBelongings = 496
groupDeadspaceOverseersSentry = 495
groupDeadspaceOverseersStructure = 494
groupDeadspaceRogueDroneBattleCruiser = 801
groupDeadspaceRogueDroneBattleship = 802
groupDeadspaceRogueDroneCruiser = 803
groupDeadspaceRogueDroneDestroyer = 804
groupDeadspaceRogueDroneFrigate = 805
groupDeadspaceRogueDroneSwarm = 806
groupDeadspaceSanshasNationBattleCruiser = 620
groupDeadspaceSanshasNationBattleship = 621
groupDeadspaceSanshasNationCruiser = 622
groupDeadspaceSanshasNationDestroyer = 623
groupDeadspaceSanshasNationFrigate = 624
groupDeadspaceSerpentisBattleCruiser = 629
groupDeadspaceSerpentisBattleship = 630
groupDeadspaceSerpentisCruiser = 631
groupDeadspaceSerpentisDestroyer = 632
groupDeadspaceSerpentisFrigate = 633
groupDeadspaceSleeperSleeplessPatroller = 983
groupDeadspaceSleeperSleeplessSentinel = 959
groupDeadspaceSleeperSleeplessDefender = 982
groupDeadspaceSleeperAwakenedPatroller = 985
groupDeadspaceSleeperAwakenedSentinel = 960
groupDeadspaceSleeperAwakenedDefender = 984
groupDeadspaceSleeperEmergentPatroller = 987
groupDeadspaceSleeperEmergentSentinel = 961
groupDeadspaceSleeperEmergentDefender = 986
groupDefenseBunkers = 1004
groupDestroyer = 420
groupDestructibleAgentsInSpace = 715
groupDestructibleSentryGun = 383
groupDestructibleStationServices = 874
groupDreadnought = 485
groupDroneTrackingModules = 646
groupElectronicCounterCounterMeasures = 202
groupElectronicCounterMeasureBurst = 80
groupElectronicCounterMeasures = 201
groupEffectBeacon = 920
groupElectronicWarfareBattery = 439
groupElectronicWarfareDrone = 639
groupEliteBattleship = 381
groupEnergyDestabilizer = 71
groupEnergyNeutralizingBattery = 837
groupEnergyTransferArray = 67
groupEnergyWeapon = 53
groupEnergyVampire = 68
groupExhumer = 543
groupExtractionControlUnitPins = 1063
groupExtractorPins = 1026
groupFaction = 19
groupFactionDrone = 288
groupFakeSkills = 505
groupFighterBomber = 1023
groupFighterDrone = 549
groupFlashpoint = 1071
groupForceField = 411
groupForceFieldArray = 445
groupFreightContainer = 649
groupFreighter = 513
groupFrequencyCrystal = 86
groupFrequencyMiningLaser = 483
groupFrigate = 25
groupFrozen = 281
groupFueledArmorRepairer = 1199
groupFueledShieldBooster = 1156
groupGangCoordinator = 316
groupGasCloudHarvester = 737
groupGasIsotopes = 422
groupGeneral = 280
groupGlobalWarpDisruptor = 368
groupGneiss = 467
groupHarvestableCloud = 711
groupHeavyAssaultShip = 358
groupHedbergite = 454
groupHemorphite = 455
groupHullRepairUnit = 63
groupHybridAmmo = 85
groupHybridWeapon = 74
groupIce = 465
groupIceProduct = 423
groupIndustrial = 28
groupIndustrialCommandShip = 941
groupInfantryDropsuit = 351064
groupInfrastructureHub = 1012
groupInterceptor = 831
groupInterdictor = 541
groupIntermediateMaterials = 428
groupInvasionSanshaNationBattleship = 1056
groupInvasionSanshaNationCapital = 1052
groupInvasionSanshaNationCruiser = 1054
groupInvasionSanshaNationFrigate = 1053
groupInvasionSanshaNationIndustrial = 1051
groupJaspet = 456
groupJumpPortalArray = 707
groupJumpPortalGenerator = 590
groupKernite = 457
groupLCODrone = 279
groupLandmark = 318
groupLargeCollidableObject = 226
groupLargeCollidableShip = 784
groupLargeCollidableStructure = 319
groupLearning = 267
groupLease = 652
groupLivestock = 283
groupLogisticDrone = 640
groupLogistics = 832
groupLogisticsArray = 710
groupMercenaryBases = 1081
groupMercoxit = 468
groupMine = 92
groupMineral = 18
groupMiningBarge = 463
groupMiningDrone = 101
groupMiningLaser = 54
groupMissile = 84
groupMiscellaneous = 314
groupCitadelTorpedo = 476
groupCitadelCruise = 1019
groupBomb = 90
groupBombECM = 863
groupBombEnergy = 864
groupTorpedo = 89
groupAdvancedTorpedo = 657
groupCruiseMissile = 386
groupFOFCruiseMissile = 396
groupAdvancedCruiseMissile = 656
groupHeavyMissile = 385
groupFOFHeavyMissile = 395
groupAdvancedHeavyMissile = 655
groupAssaultMissile = 772
groupAdvancedAssaultMissile = 654
groupLightMissile = 384
groupFOFLightMissile = 394
groupAdvancedLightMissile = 653
groupRocket = 387
groupAdvancedRocket = 648
groupDefenderMissile = 88
groupHeavyDefenderMissile = 1158
groupFestivalMissile = 500
groupMissileLauncher = 56
groupMissileLauncherAssault = 511
groupMissileLauncherBomb = 862
groupMissileLauncherCitadel = 524
groupMissileLauncherCruise = 506
groupMissileLauncherDefender = 512
groupMissileLauncherHeavy = 510
groupMissileLauncherHeavyAssault = 771
groupMissileLauncherRocket = 507
groupMissileLauncherSiege = 508
groupMissileLauncherFestival = 501
groupMissileLauncherStandard = 509
groupMissileLauncherRapidHeavy = 1243
groupMissionAmarrEmpireBattlecruiser = 666
groupMissionAmarrEmpireBattleship = 667
groupMissionAmarrEmpireCruiser = 668
groupMissionAmarrEmpireDestroyer = 669
groupMissionAmarrEmpireFrigate = 665
groupMissionAmarrEmpireOther = 670
groupMissionCONCORDBattlecruiser = 696
groupMissionCONCORDBattleship = 697
groupMissionCONCORDCruiser = 695
groupMissionCONCORDDestroyer = 694
groupMissionCONCORDFrigate = 693
groupMissionCONCORDOther = 698
groupMissionCaldariStateBattlecruiser = 672
groupMissionCaldariStateBattleship = 674
groupMissionCaldariStateCruiser = 673
groupMissionCaldariStateDestroyer = 676
groupMissionCaldariStateFrigate = 671
groupMissionCaldariStateOther = 675
groupMissionDrone = 337
groupMissionFactionBattleships = 924
groupMissionFactionCruisers = 1006
groupMissionFactionFrigates = 1007
groupMissionFactionIndustrials = 927
groupMissionGallenteFederationBattlecruiser = 681
groupMissionGallenteFederationBattleship = 680
groupMissionGallenteFederationCruiser = 678
groupMissionGallenteFederationDestroyer = 679
groupMissionGallenteFederationFrigate = 677
groupMissionGallenteFederationOther = 682
groupMissionKhanidBattlecruiser = 690
groupMissionKhanidBattleship = 691
groupMissionKhanidCruiser = 689
groupMissionKhanidDestroyer = 688
groupMissionKhanidFrigate = 687
groupMissionKhanidOther = 692
groupMissionMinmatarRepublicBattlecruiser = 685
groupMissionMinmatarRepublicBattleship = 706
groupMissionMinmatarRepublicCruiser = 705
groupMissionMinmatarRepublicDestroyer = 684
groupMissionMinmatarRepublicFrigate = 683
groupMissionMinmatarRepublicOther = 686
groupMissionMorduBattlecruiser = 702
groupMissionMorduBattleship = 703
groupMissionMorduCruiser = 701
groupMissionMorduDestroyer = 700
groupMissionMorduFrigate = 699
groupMissionMorduOther = 704
groupMobileHybridSentry = 449
groupMobileLaboratory = 413
groupMobileLaserSentry = 430
groupMobileMissileSentry = 417
groupTransportShip = 380
groupJumpFreighter = 902
groupFWMinmatarRepublicFrigate = 1166
groupFWMinmatarRepublicDestroyer = 1178
groupFWMinmatarRepublicCruiser = 1182
groupFWMinmatarRepublicBattlecruiser = 1186
groupFWGallenteFederationFrigate = 1168
groupFWGallenteFederationDestroyer = 1177
groupFWGallenteFederationCruiser = 1181
groupFWGallenteFederationBattlecruiser = 1185
groupFWCaldariStateFrigate = 1167
groupFWCaldariStateDestroyer = 1176
groupFWCaldariStateCruiser = 1180
groupFWCaldariStateBattlecruiser = 1184
groupFWAmarrEmpireFrigate = 1169
groupFWAmarrEmpireDestroyer = 1175
groupFWAmarrEmpireCruiser = 1179
groupFWAmarrEmpireBattlecruiser = 1183
groupMiniContainer = 1208
groupMobilePowerCore = 414
groupMobileProjectileSentry = 426
groupMobileReactor = 438
groupMobileSentryGun = 336
groupMobileShieldGenerator = 418
groupMobileStorage = 364
groupMobileMicroJumpDisruptor = 1149
groupMobileWarpDisruptor = 361
groupMoney = 17
groupMoon = 8
groupMoonMaterials = 427
groupMoonMining = 416
groupSupercarrier = 659
groupOmber = 469
groupOrbitalConstructionPlatforms = 1106
groupOrbitalInfrastructure = 1025
groupOverseerPersonalEffects = 493
groupOutpostImprovements = 872
groupOutpostUpgrades = 876
groupPersonalHangar = 1212
groupPirateDrone = 185
groupPlagioclase = 458
groupPlanet = 7
groupPlanetaryCustomsOffices = 1025
groupPlanetaryCloud = 312
groupPlanetaryLinks = 1036
groupPledges = 1075
groupPoliceDrone = 182
groupProcessPins = 1028
groupProjectedElectronicCounterCounterMeasures = 289
groupProjectileAmmo = 83
groupProjectileWeapon = 55
groupProtectiveSentryGun = 180
groupPrototypeExplorationShip = 1022
groupProximityDrone = 97
groupPyroxeres = 459
groupRadioactive = 282
groupForceReconShip = 833
groupCombatReconShip = 906
groupRefinables = 355
groupRefiningArray = 311
groupRegion = 3
groupRemoteHullRepairer = 585
groupRemoteSensorBooster = 290
groupRemoteSensorDamper = 208
groupRepairDrone = 299
groupRing = 13
groupRogueDrone = 287
groupRookieship = 237
groupSalvagedMaterials = 754
groupSalvageDrone = 1159
groupSatellite = 1165
groupScanProbeLauncher = 481
groupScannerArray = 709
groupScannerProbe = 479
groupScordite = 460
groupSecureCargoContainer = 340
groupSecurityTags = 1206
groupSensorBooster = 212
groupSensorDampeningBattery = 440
groupSentryGun = 99
groupShieldBooster = 40
groupShieldHardener = 77
groupShieldHardeningArray = 444
groupShieldTransporter = 41
groupShipMaintenanceArray = 363
groupShippingCrates = 382
groupShuttle = 31
groupSiegeModule = 515
groupSilo = 404
groupSmartBomb = 72
groupSolarSystem = 5
groupSovereigntyClaimMarkers = 1003
groupSovereigntyDisruptionStructures = 1005
groupSovereigntyStructures = 1004
groupSpaceportPins = 1030
groupSpaceshipCommand = 257
groupSpawnContainer = 306
groupSpewContainer = 1207
groupSpodumain = 461
groupStargate = 10
groupStatisWeb = 65
groupStasisWebificationBattery = 441
groupStasisWebifyingDrone = 641
groupStation = 15
groupStationServices = 16
groupStationUpgradePlatform = 835
groupStationImprovementPlatform = 836
groupStealthBomber = 834
groupStealthEmitterArray = 480
groupStoragePins = 1029
groupStorylineBattleship = 523
groupStorylineCruiser = 522
groupStorylineFrigate = 520
groupStorylineMissionBattleship = 534
groupStorylineMissionCruiser = 533
groupStorylineMissionFrigate = 527
groupStripMiner = 464
groupStructureRepairArray = 840
groupSovUpgradeIndustrial = 1020
groupSovUpgradeMilitary = 1021
groupSun = 6
groupSuperWeapon = 588
groupSurveyProbe = 492
groupSurveyProbeLauncher = 1226
groupSystem = 0
groupTargetBreaker = 1154
groupTargetPainter = 379
groupTargetPaintingBattery = 877
groupTemporaryCloud = 335
groupTestOrbitals = 1073
groupTerranArtifacts = 519
groupTitan = 30
groupTool = 332
groupTrackingArray = 473
groupTrackingComputer = 213
groupTrackingDisruptor = 291
groupTrackingLink = 209
groupTractorBeam = 650
groupTradeSession = 95
groupTrading = 94
groupTutorialDrone = 286
groupUnanchoringDrone = 470
groupVeldspar = 462
groupVoucher = 24
groupWarpDisruptFieldGenerator = 899
groupWarpDisruptionProbe = 548
groupWarpGate = 366
groupWarpScrambler = 52
groupWarpScramblingBattery = 443
groupWarpScramblingDrone = 545
groupWreck = 186
groupZombieEntities = 934
groupMissionGenericBattleships = 816
groupMissionGenericCruisers = 817
groupMissionGenericFrigates = 818
groupMissionThukkerBattlecruiser = 822
groupMissionThukkerBattleship = 823
groupMissionThukkerCruiser = 824
groupMissionThukkerDestroyer = 825
groupMissionThukkerFrigate = 826
groupMissionThukkerOther = 827
groupMissionGenericBattleCruisers = 828
groupMissionGenericDestroyers = 829
groupDeadspaceOverseerFrigate = 819
groupDeadspaceOverseerCruiser = 820
groupDeadspaceOverseerBattleship = 821
groupElectronicAttackShips = 893
groupEnergyNeutralizingBattery = 837
groupHeavyInterdictors = 894
groupMarauders = 900
groupDecorations = 937
groupDefensiveSubSystems = 954
groupElectronicSubSystems = 955
groupEngineeringSubSystems = 958
groupOffensiveSubSystems = 956
groupPropulsionSubSystems = 957
groupWormhole = 988
groupSecondarySun = 995
groupGameTime = 943
groupWorldSpace = 935
groupSalvager = 1122
groupOrbitalTarget = 1198
groupMaterialsAndCompounds = 530

typeTicketFrigate = 30717
typeTicketDestroyer = 30718
typeTicketBattleship = 30721
typeTicketCruiser = 30722
typeTicketBattlecruiser = 30723
typeAccelerationGate = 17831
typeAccounting = 16622
typeAcolyteI = 2203
typeAdvancedLaboratoryOperation = 24624
typeAdvancedMassProduction = 24625
typeAdvancedPlanetology = 2403
typeAlliance = 16159
typeAmarrFreighterWreck = 26483
typeAmarrCaptainsQuarters = 32578
typeAmarrEliteFreighterWreck = 29033
typeApocalypse = 642
typeArchaeology = 13278
typeAstrometrics = 3412
typeAutomatedCentiiKeyholder = 22053
typeAutomatedCentiiTrainingVessel = 21849
typeAutomatedCoreliTrainingVessel = 21845
typeAutomatedCorpiiTrainingVessel = 21847
typeAutomatedGistiTrainingVessel = 21846
typeAutomatedPithiTrainingVessel = 21848
typeBHMegaCargoShip = 11019
typeBasicDamageControl = 521
typeBeacon = 10124
typeBiomass = 3779
typeBookmark = 51
typeBrokerRelations = 3446
typeBubbleProbeLauncher = 22782
typeCaldariFreighterWreck = 26505
typeCaldariCaptainsQuarters = 32581
typeCaldariEliteFreighterWreck = 29034
typeCapsule = 670
typeCapsuleGolden = 33328
typeCargoContainer = 23
typeCelestialAgentSiteBeacon = 25354
typeCelestialBeacon = 10645
typeCelestialBeaconII = 19706
typeCertificate = 29530
typeCharacterAchura = 1383
typeCharacterAmarr = 1373
typeCharacterBrutor = 1380
typeCharacterCivire = 1375
typeCharacterDeteis = 1376
typeCharacterGallente = 1377
typeCharacterIntaki = 1378
typeCharacterJinMei = 1384
typeCharacterKhanid = 1385
typeCharacterModifier = 1382
typeCharacterNiKunni = 1374
typeCharacterSebiestor = 1379
typeCharacterStatic = 1381
typeCharacterVherokior = 1386
typeCloneGradeAlpha = 164
typeCloneVatBayI = 23735
typeCloningService = 28158
typeCommandCenterUpgrade = 2505
typeCompanyShares = 50
typeConnections = 3359
typeConstellation = 4
typeContracting = 25235
typeCorporation = 2
typeCorporationContracting = 25233
typeCorporationManagement = 3363
typeCorpse = 25
typeCorpseFemale = 29148
typeCosmicAnomaly = 28356
typeCovertCynosuralFieldI = 28650
typeCredits = 29
typeCriminalConnections = 3361
typeCrowBlueprint = 11177
typeCynosuralFieldI = 21094
typeCynosuralJammerBeacon = 32798
typeDamageControlI = 2046
typeDaytrading = 16595
typeDeadspaceSignature = 19728
typeDefenderI = 265
typeDiplomacy = 3357
typeDistributionConnections = 3894
typeDistrictSatellite = 32884
typeDoomTorpedoIBlueprint = 17864
typeDuplicating = 10298
typeDustStreak = 10756
typeElectronics = 3426
typeEmpireControl = 3732
typeEngineering = 3413
typeEthnicRelations = 3368
typeFaction = 30
typeFactoryService = 28157
typeFittingService = 28155
typeFixedLinkAnnexationGenerator = 32226
typeFlashpoint = 3692
typeFleetCommand = 24764
typeForceField = 16103
typeGallenteFreighterWreck = 26527
typeGallenteCaptainsQuarters = 32579
typeGallenteEliteFreighterWreck = 29035
typeEnormousFreightContainer = 33003
typeGiantFreightContainer = 24445
typeHugeFreightContainer = 33005
typeLargeFreightContainer = 33007
typeMediumFreightContainer = 33009
typeSmallFreightContainer = 33011
typeSalvaging = 25863
typeGiantSecureContainer = 11489
typeGistiiHijacker = 16877
typeGoldenCapsuleImplant = 33329
typeHacking = 21718
typeHangarContainer = 3298
typeHugeSecureContainer = 11488
typeIndustry = 3380
typeInfrastructureHub = 32458
typeInterplanetaryConsolidation = 2495
typeIsogen = 37
typeJumpDriveOperation = 3456
typeJumpDriveCalibration = 21611
typeLaboratoryOperation = 3406
typeLaboratoryService = 28166
typeLargeAuditLogSecureContainer = 17365
typeLargeCratesOfQuafe = 4090
typeLargeCryoContainer = 3464
typeLargeLifeSupportContainer = 3459
typeLargeRadiationShieldedContainer = 3461
typeLargeSecureContainer = 3465
typeLargeStandardContainer = 3296
typeLeadership = 3348
typeLoyaltyPoints = 29247
typeMapLandmark = 11367
typeMarginTrading = 16597
typeMarketing = 16598
typeMassProduction = 3387
typeMedal = 29496
typeMediumAuditLogSecureContainer = 17364
typeMediumCryoContainer = 3463
typeMediumLifeSupportContainer = 3458
typeMediumRadiationShieldedContainer = 3460
typeMediumSecureContainer = 3466
typeMediumStandardContainer = 3293
typeMegacyte = 40
typeMetallurgy = 3409
typeMexallon = 36
typeMicroJumpDrive = 4383
typeMinmatarFreighterWreck = 26549
typeMinmatarEliteFreighterWreck = 29036
typeMiningConnections = 3893
typeMinmatarCaptainsQuarters = 32580
typeMissileLauncherOperation = 3319
typeMoon = 14
typeMorphite = 11399
typeNaniteRepairPaste = 28668
typeNegotiation = 3356
typeNocxium = 38
typeOffice = 27
typeOfficeFolder = 26
typeOmnipotent = 19430
typeOrbitalCommandCenter = 3964
typeOrbitalTarget = 33069
typePlanetaryCustomsOffice = 2233
typePlanetaryLaunchContainer = 2263
typePlanetEarthlike = 11
typePlanetGas = 13
typePlanetIce = 12
typePlanetLava = 2015
typePlanetOcean = 2014
typePlanetSandstorm = 2016
typePlanetShattered = 30889
typePlanetThunderstorm = 2017
typePlanetPlasma = 2063
typePlanetology = 2406
typePlasticWrap = 3468
typePlayerKill = 49
typePolarisCenturion = 9858
typePolarisCenturionFrigate = 9862
typePolarisInspectorFrigate = 9854
typePolarisLegatusFrigate = 9860
typePotequeProteusEY1005Implant = 27260
typeProcurement = 16594
typePyerite = 35
typeQuafe = 3699
typeQuafeUltra = 12865
typeQuafeUltraSpecialEdition = 12994
typeQuafeZero = 3898
typeRank = 29495
typeRegion = 3
typeRemoteSensing = 13279
typeRepairService = 28159
typeRepairSystems = 3393
typeReprocessingService = 28156
typeResearch = 3403
typeResearchProjectManagement = 12179
typeRetail = 3444
typeRibbon = 29497
typeSchematic = 2733
typeScience = 3402
typeScientificNetworking = 24270
typeScrapmetalProcessing = 12196
typeSecurityConnections = 3895
typeSecurityTagCloneSoldierNegotiator = 33141
typeSecurityTagCloneSoldierRecruiter = 33139
typeSecurityTagCloneSoldierTrainer = 33138
typeSecurityTagCloneSoldierTransporter = 33140
typeShieldOperations = 3416
typeShieldGenerator = 3860
typeSilo = 14343
typeSlaver = 12049
typeSmallAuditLogSecureContainer = 17363
typeSmallCryoContainer = 3462
typeSmallLifeSupportContainer = 3295
typeSmallRadiationShieldedContainer = 3294
typeSmallSecureContainer = 3467
typeSmallStandardContainer = 3297
typeSocial = 3355
typeSoftCloud = 10753
typeSolarSystem = 5
typeSpaceAnchor = 2528
typeSpikedQuafe = 21661
typeStationConquerable1 = 12242
typeStationConquerable2 = 12294
typeStationConquerable3 = 12295
typeStationContainer = 17366
typeStationVault = 17367
typeStationWarehouse = 17368
typeStrontiumClathrates = 16275
typeSupplyChainManagement = 24268
typeSystem = 0
typeTacticalEMPAmmoS = 32801
typeTacticalHybridAmmoS = 32803
typeTacticalLaserAmmoS = 32799
typeTargetedAccelerationGate = 4077
typeTestPlanetaryLink = 2280
typeTestSurfaceCommandCenter = 3936
typeThePrizeContainer = 19373
typeThermodynamics = 28164
typeTrade = 3443
typeTradeSession = 53
typeTrading = 52
typeTritanium = 34
typeTycoon = 18580
typeUniverse = 9
typeVeldspar = 1230
typeVisibility = 3447
typeWarpDisruptionFocusingScript = 29003
typeWholesale = 16596
typeWingCommand = 11574
typeWispyChlorineCloud = 10758
typeWispyOrangeCloud = 10754
typeWreck = 26468
typePilotLicence = 29668
typeAsteroidBelt = 15
typeAstrogeology = 3410
typeLetterOfRecommendation = 30906
typeWater = 3645
typeOxygen = 3683
typeZydrine = 39
typeAmarrBattlecruiser = 33095
typeAmarrBattleship = 3339
typeAmarrCarrier = 24311
typeAmarrCruiser = 3335
typeAmarrDestroyer = 33091
typeAmarrDreadnought = 20525
typeAmarrFreighter = 20524
typeAmarrFrigate = 3331
typeAmarrIndustrial = 3343
typeAmarrStrategicCruiser = 30650
typeAmarrTitan = 3347
typeCaldariBattlecruiser = 33096
typeCaldariBattleship = 3338
typeCaldariCarrier = 24312
typeCaldariCruiser = 3334
typeCaldariDestroyer = 33092
typeCaldariDreadnought = 20530
typeCaldariFreighter = 20526
typeCaldariFrigate = 3330
typeCaldariIndustrial = 3342
typeCaldariStrategicCruiser = 30651
typeCaldariTitan = 3346
typeGallenteBattlecruiser = 33097
typeGallenteBattleship = 3336
typeGallenteCarrier = 24313
typeGallenteCruiser = 3332
typeGallenteDestroyer = 33093
typeGallenteDreadnought = 20531
typeGallenteFreighter = 20527
typeGallenteFrigate = 3328
typeGallenteIndustrial = 3340
typeGallenteStrategicCruiser = 30652
typeGallenteTitan = 3344
typeMinmatarBattlecruiser = 33098
typeMinmatarBattleship = 3337
typeMinmatarCarrier = 24314
typeMinmatarCruiser = 3333
typeMinmatarDestroyer = 33094
typeMinmatarDreadnought = 20532
typeMinmatarFreighter = 20528
typeMinmatarFrigate = 3329
typeMinmatarIndustrial = 3341
typeMinmatarStrategicCruiser = 30653
typeMinmatarTitan = 3345
typeAdvancedSpaceshipCommand = 20342
typeAssaultShips = 12095
typeBattlecruisers = 12099
typeBlackOps = 28656
typeCapitalIndustrialShips = 28374
typeCapitalShips = 20533
typeCommandShips = 23950
typeCovertOps = 12093
typeDestroyers = 12097
typeElectronicAttackShips = 28615
typeExhumers = 22551
typeHeavyAssaultShips = 16591
typeHeavyInterdictors = 28609
typeIndustrialCommandShips = 29637
typeInterceptors = 12092
typeInterdictors = 12098
typeJumpFreighters = 29029
typeLogistics = 12096
typeMarauders = 28667
typeMiningBarge = 17940
typeMiningFrigate = 32918
typeOreIndustrial = 3184
typeReconShips = 22761
typeSpaceshipCommand = 3327
typeTransportShips = 19719
typeMiniContainer1 = 33148
typeMiniContainer2 = 33159
typeMiniContainer3 = 33160
typeMiniContainer4 = 33161
typeMiniContainer5 = 33162

miniContainerTypes = (
	typeMiniContainer1,
	typeMiniContainer2,
	typeMiniContainer3,
	typeMiniContainer4,
	typeMiniContainer5,
)


shipPackagedVolumesPerGroup = {
 groupAssaultShip: 2500.0,
 groupAttackBattlecruiser: 15000.0,
 groupBattlecruiser: 15000.0,
 groupBattleship: 50000.0,
 groupBlackOps: 50000.0,
 groupBlockadeRunner: 20000.0,
 groupCapitalIndustrialShip: 1000000.0,
 groupCapsule: 500.0,
 groupCarrier: 1000000.0,
 groupCombatReconShip: 10000.0,
 groupCommandShip: 15000.0,
 groupCovertOps: 2500.0,
 groupCruiser: 10000.0,
 groupDestroyer: 5000.0,
 groupDreadnought: 1000000.0,
 groupElectronicAttackShips: 2500.0,
 groupEliteBattleship: 50000.0,
 groupExhumer: 3750.0,
 groupForceReconShip: 10000.0,
 groupFreighter: 1000000.0,
 groupFrigate: 2500.0,
 groupHeavyAssaultShip: 10000.0,
 groupHeavyInterdictors: 10000.0,
 groupIndustrial: 20000.0,
 groupIndustrialCommandShip: 500000.0,
 groupInterceptor: 2500.0,
 groupInterdictor: 5000.0,
 groupJumpFreighter: 1000000.0,
 groupLogistics: 10000.0,
 groupMarauders: 50000.0,
 groupMiningBarge: 3750.0,
 groupSupercarrier: 1000000.0,
 groupPrototypeExplorationShip: 500.0,
 groupRookieship: 2500.0,
 groupShuttle: 500.0,
 groupStealthBomber: 2500.0,
 groupStrategicCruiser: 5000,
 groupTitan: 10000000.0,
 groupTransportShip: 20000.0
}

containerPackagedVolumesPerType = {
 typeGiantSecureContainer: 300,
 typeHugeSecureContainer: 150,
 typeLargeSecureContainer: 65,
 typeMediumSecureContainer: 33,
 typeSmallSecureContainer: 10,
 typeLargeAuditLogSecureContainer: 65,
 typeMediumAuditLogSecureContainer: 33,
 typeSmallAuditLogSecureContainer: 10,
 typeEnormousFreightContainer: 2500,
 typeGiantFreightContainer: 1200,
 typeHugeFreightContainer: 5000,
 typeLargeFreightContainer: 1000,
 typeMediumFreightContainer: 500,
 typeSmallFreightContainer: 100,
 typeLargeStandardContainer: 65,
 typeMediumStandardContainer: 33,
 typeSmallStandardContainer: 10,
 typeStationContainer: 10000,
 typeStationVault: 50000,
 typeStationWarehouse: 100000
}

accountingKeyCash = 1000
accountingKeyCash2 = 1001
accountingKeyCash3 = 1002
accountingKeyCash4 = 1003
accountingKeyCash5 = 1004
accountingKeyCash6 = 1005
accountingKeyCash7 = 1006
accountingKeyProperty = 1100
accountingKeyAUR = 1200
accountingKeyAUR2 = 1201
accountingKeyAUR3 = 1202
accountingKeyAUR4 = 1203
accountingKeyAUR5 = 1204
accountingKeyAUR6 = 1205
accountingKeyAUR7 = 1206
accountingKeyEscrow = 1500
accountingKeyReceivables = 1800
accountingKeyPayables = 2000
accountingKeyGold = 2010
accountingKeyEquity = 2900
accountingKeySales = 3000
accountingKeyPurchases = 4000
accountingKeyDustISK = 10000
accountingKeyDustAUR = 11000

cashAccounts = set([
 accountingKeyCash,
 accountingKeyCash2,
 accountingKeyCash3,
 accountingKeyCash4,
 accountingKeyCash5,
 accountingKeyCash6,
 accountingKeyCash7
])

aurAccounts = set([
 accountingKeyAUR,
 accountingKeyAUR2,
 accountingKeyAUR3,
 accountingKeyAUR4,
 accountingKeyAUR5,
 accountingKeyAUR6,
 accountingKeyAUR7
])

loSlotFlags = [flagLoSlot0, flagLoSlot1, flagLoSlot2, flagLoSlot3, flagLoSlot4, flagLoSlot5, flagLoSlot6, flagLoSlot7]
medSlotFlags = [flagMedSlot0, flagMedSlot1, flagMedSlot2, flagMedSlot3, flagMedSlot4, flagMedSlot5, flagMedSlot6, flagMedSlot7]
hiSlotFlags = [flagHiSlot0, flagHiSlot1, flagHiSlot2, flagHiSlot3, flagHiSlot4, flagHiSlot5, flagHiSlot6, flagHiSlot7]
subSystemSlotFlags = [flagSubSystemSlot0, flagSubSystemSlot1, flagSubSystemSlot2, flagSubSystemSlot3, flagSubSystemSlot4]
rigSlotFlags = [flagRigSlot0, flagRigSlot1, flagRigSlot2]

ALSCActionAdd = 6
ALSCActionAssemble = 1
ALSCActionConfigure = 10
ALSCActionEnterPassword = 9
ALSCActionLock = 7
ALSCActionMove = 4
ALSCActionRepackage = 2
ALSCActionSetName = 3
ALSCActionSetPassword = 5
ALSCActionUnlock = 8
ALSCPasswordNeededToLock = 2
ALSCPasswordNeededToOpen = 1
ALSCPasswordNeededToUnlock = 4
ALSCPasswordNeededToViewAuditLog = 8

CTPC_CHAT = 8
CTPC_MAIL = 9
CTPG_CASH = 6
CTPG_SHARES = 7
CTV_ADD = 1
CTV_COMMS = 5
CTV_GIVE = 4
CTV_REMOVE = 2
CTV_SET = 3
SCCPasswordTypeConfig = 2
SCCPasswordTypeGeneral = 1

agentTypeBasicAgent = 2
agentTypeEventMissionAgent = 8
agentTypeGenericStorylineMissionAgent = 6
agentTypeNonAgent = 1
agentTypeResearchAgent = 4
agentTypeStorylineMissionAgent = 7
agentTypeTutorialAgent = 3
agentTypeFactionalWarfareAgent = 9
agentTypeEpicArcAgent = 10
agentTypeAura = 11
auraAgentIDs = [
	3019499, 3019493, 3019495, 3019490,
	3019497, 3019496, 3019486, 3019498,
	3019492, 3019500, 3019489, 3019494,
]


agentRangeNearestEnemyCombatZone = 11
agentRangeNeighboringConstellation = 10
agentRangeNeighboringConstellationSameRegion = 9
agentRangeNeighboringSystem = 5
agentRangeNeighboringSystemSameConstellation = 4
agentRangeSameConstellation = 6
agentRangeSameOrNeighboringConstellation = 8
agentRangeSameOrNeighboringConstellationSameRegion = 7
agentRangeSameOrNeighboringSystem = 3
agentRangeSameOrNeighboringSystemSameConstellation = 2
agentRangeSameSystem = 1

agentIskMultiplierLevel1 = 1
agentIskMultiplierLevel2 = 2
agentIskMultiplierLevel3 = 4
agentIskMultiplierLevel4 = 8
agentIskMultiplierLevel5 = 16

agentLpMultiplierLevel1 = 20
agentLpMultiplierLevel2 = 60
agentLpMultiplierLevel3 = 180
agentLpMultiplierLevel4 = 540
agentLpMultiplierLevel5 = 4860

agentLpMultipliers = (agentLpMultiplierLevel1,
 agentLpMultiplierLevel2,
 agentLpMultiplierLevel3,
 agentLpMultiplierLevel4,
 agentLpMultiplierLevel5)


agentIskRandomLowValue  = 11000
agentIskRandomHighValue = 16500

agentIskCapValueLevel1 = 250000
agentIskCapValueLevel2 = 500000
agentIskCapValueLevel3 = 1000000
agentIskCapValueLevel4 = 5000000
agentIskCapValueLevel5 = 9000000

allianceApplicationAccepted = 2
allianceApplicationEffective = 3
allianceApplicationNew = 1
allianceApplicationRejected = 4
allianceCreationCost = 1000000000
allianceMembershipCost = 2000000
allianceRelationshipCompetitor = 3
allianceRelationshipEnemy = 4
allianceRelationshipFriend = 2
allianceRelationshipNAP = 1

dgmTauConstant = 10000

attributeAccessDifficulty = 901
attributeAccessDifficultyBonus = 902
attributeAccuracyMultiplier = 205
attributeActivationBlocked = 1349
attributeActivationTargetLoss = 855
attributeAgentAutoPopupRange = 844
attributeAgentCommRange = 841
attributeAgentID = 840
attributeAgility = 70
attributeIgnoreDronesBelowSignatureRadius = 1855
attributeAimedLaunch = 644
attributeAllowsCloneJumpsWhenActive = 981
attributeAllowedInCapIndustrialMaintenanceBay = 1891
attributeAmmoLoaded = 127
attributeAnchoringDelay = 556
attributeAnchorDistanceMax = 1591
attributeAnchorDistanceMin = 1590
attributeAnchoringRequiresSovereignty = 1033
attributeAnchoringRequiresSovUpgrade1 = 1595
attributeAnchoringSecurityLevelMax = 1032
attributeAoeCloudSize = 654
attributeAoeDamageReductionFactor = 1353
attributeAoeDamageReductionSensitivity = 1354
attributeAoeFalloff = 655
attributeAoeVelocity = 653
attributeArmorBonus = 65
attributeArmorDamage = 266
attributeArmorDamageAmount = 84
attributeArmorEmDamageResonance = 267
attributeArmorEmDamageResistanceBonus = 1465
attributeArmorExplosiveDamageResonance = 268
attributeArmorExplosiveDamageResistanceBonus = 1468
attributeArmorHP = 265
attributeArmorHPBonusAdd = 1159
attributeArmorHPMultiplier = 148
attributeArmorHpBonus = 335
attributeArmorKineticDamageResonance = 269
attributeArmorKineticDamageResistanceBonus = 1466
attributeArmorThermalDamageResonance = 270
attributeArmorThermalDamageResistanceBonus = 1467
attributeArmorUniformity = 524
attributeAttributePoints = 185
attributeAurumConversionRate = 1818
attributeBarrageDmgMultiplier = 326
attributeBaseDefenderAllyCost = 1820
attributeBaseMaxScanDeviation = 1372
attributeBaseSensorStrength = 1371
attributeBaseScanRange = 1370
attributeBoosterDuration = 330
attributeBoosterness = 1087
attributeBoosterMaxCharAgeHours = 1647
attributeBrokenRepairCostMultiplier = 1264
attributeCanBeJettisoned = 1852
attributeCanCloak = 1163
attributeCanJump = 861
attributeCanNotBeTrainedOnTrial = 1047
attributeCanNotUseStargates = 1254
attributeCanReceiveCloneJumps = 982
attributeCapacitorBonus = 67
attributeCapacitorCapacity = 482
attributeCapacitorCapacityBonus = 1079
attributeCapacitorCapacityMultiplier = 147
attributeCapacitorCharge = 18
attributeCapacitorRechargeRateMultiplier = 144
attributeCapacity = 38
attributeCapacitySecondary = 1233
attributeCapacityBonus = 72
attributeCapRechargeBonus = 314
attributeCaptureProximityRange = 1337
attributeCargoCapacityMultiplier = 149
attributeCargoGroup = 629
attributeCargoGroup2 = 1846
attributeCargoScanResistance = 188
attributeChanceToNotTargetSwitch = 1651
attributeCharge = 18
attributeChargedArmorDamageMultiplier = 1886
attributeChargeGroup1 = 604
attributeChargeRate = 56
attributeChargeSize = 128
attributeCharisma = 164
attributeCloakingTargetingDelay = 560
attributeCloneJumpCoolDown = 1921
attributeClothingAlsoCoversCategory = 1797
attributeCloudDuration = 545
attributeCloudEffectDelay = 544
attributeColor = 1417
attributeCommandbonus = 833
attributeConstructionType = 1771
attributeConsumptionQuantity = 714
attributeConsumptionType = 713
attributeContrabandDetectionChance = 723
attributeControlTowerMinimumDistance = 1165
attributeCopySpeedPercent = 387
attributeFleetHangarCapacity = 912
attributeCorporateHangarCapacity = 912
attributeCorporationMemberLimit = 190
attributeCpu = 50
attributeCpuLoad = 49
attributeCpuLoadLevelModifier = 1635
attributeCpuLoadPerKm = 1634
attributeCpuMultiplier = 202
attributeCpuOutput = 48
attributeCrystalVolatilityChance = 783
attributeCrystalVolatilityDamage = 784
attributeCrystalsGetDamaged = 786
attributeDamage = 3
attributeDamageCloudChance = 522
attributeDamageCloudType = 546
attributeDamageMultiplier = 64
attributeDeadspaceUnsafe = 801
attributeDecloakFieldRange = 651
attributeDecryptorID = 1115
attributeDefaultCustomsOfficeTaxRate = 1781
attributeDevIndexMilitary = 1583
attributeDevIndexIndustrial = 1584
attributeDevIndexSovereignty = 1615
attributeDevIndexUpgrade = 1616
attributeDisallowActivateInForcefield = 1920
attributeDisallowAssistance = 854
attributeDisallowEarlyDeactivation = 906
attributeDisallowInEmpireSpace = 1074
attributeDisallowOffensiveModifiers = 872
attributeDisallowRepeatingActivation = 1014
attributeDistributionID01 = 1755
attributeDistributionID02 = 1756
attributeDistributionID03 = 1757
attributeDistributionID04 = 1758
attributeDistributionID05 = 1759
attributeDistributionID06 = 1760
attributeDistributionID07 = 1761
attributeDistributionID08 = 1762
attributeDistributionID09 = 1763
attributeDistributionID10 = 1764
attributeDistributionIDAngel01 = 1695
attributeDistributionIDAngel02 = 1696
attributeDistributionIDAngel03 = 1697
attributeDistributionIDAngel04 = 1698
attributeDistributionIDAngel05 = 1699
attributeDistributionIDAngel06 = 1700
attributeDistributionIDAngel07 = 1701
attributeDistributionIDAngel08 = 1702
attributeDistributionIDAngel09 = 1703
attributeDistributionIDAngel10 = 1704
attributeDistributionIDBlood01 = 1705
attributeDistributionIDBlood02 = 1706
attributeDistributionIDBlood03 = 1707
attributeDistributionIDBlood04 = 1708
attributeDistributionIDBlood05 = 1709
attributeDistributionIDBlood06 = 1710
attributeDistributionIDBlood07 = 1711
attributeDistributionIDBlood08 = 1712
attributeDistributionIDBlood09 = 1713
attributeDistributionIDBlood10 = 1714
attributeDistributionIDGurista01 = 1715
attributeDistributionIDGurista02 = 1716
attributeDistributionIDGurista03 = 1717
attributeDistributionIDGurista04 = 1718
attributeDistributionIDGurista05 = 1719
attributeDistributionIDGurista06 = 1720
attributeDistributionIDGurista07 = 1721
attributeDistributionIDGurista08 = 1722
attributeDistributionIDGurista09 = 1723
attributeDistributionIDGurista10 = 1724
attributeDistributionIDRogueDrone01 = 1725
attributeDistributionIDRogueDrone02 = 1726
attributeDistributionIDRogueDrone03 = 1727
attributeDistributionIDRogueDrone04 = 1728
attributeDistributionIDRogueDrone05 = 1729
attributeDistributionIDRogueDrone06 = 1730
attributeDistributionIDRogueDrone07 = 1731
attributeDistributionIDRogueDrone08 = 1732
attributeDistributionIDRogueDrone09 = 1733
attributeDistributionIDRogueDrone10 = 1734
attributeDistributionIDSansha01 = 1735
attributeDistributionIDSansha02 = 1736
attributeDistributionIDSansha03 = 1737
attributeDistributionIDSansha04 = 1738
attributeDistributionIDSansha05 = 1739
attributeDistributionIDSansha06 = 1740
attributeDistributionIDSansha07 = 1741
attributeDistributionIDSansha08 = 1742
attributeDistributionIDSansha09 = 1743
attributeDistributionIDSansha10 = 1744
attributeDistributionIDSerpentis01 = 1745
attributeDistributionIDSerpentis02 = 1746
attributeDistributionIDSerpentis03 = 1747
attributeDistributionIDSerpentis04 = 1748
attributeDistributionIDSerpentis05 = 1749
attributeDistributionIDSerpentis06 = 1750
attributeDistributionIDSerpentis07 = 1751
attributeDistributionIDSerpentis08 = 1752
attributeDistributionIDSerpentis09 = 1753
attributeDistributionIDSerpentis10 = 1754
attributeDoesNotEmergencyWarp = 1854
attributeDrawback = 1138
attributeDroneBandwidth = 1271
attributeDroneBandwidthLoad = 1273
attributeDroneBandwidthUsed = 1272
attributeDroneCapacity = 283
attributeDroneControlDistance = 458
attributeDroneFocusFire = 1297
attributeDroneIsAggressive = 1275
attributeDroneIsChaotic = 1278
attributeDuplicatingChance = 399
attributeDuration = 73
attributeEcmBurstRange = 142
attributeEcuAreaOfInfluence = 1689
attributeEcuDecayFactor = 1683
attributeExtractorHeadCPU = 1690
attributeExtractorHeadPower = 1691
attributeEcuMaxVolume = 1684
attributeEcuOverlapFactor = 1685
attributeEcuNoiseFactor = 1687
attributeEffectDeactivationDelay = 1579
attributeEmDamage = 114
attributeEmDamageResistanceBonus = 984
attributeEmDamageResonance = 113
attributeEmDamageResonanceMultiplier = 133
attributeEmpFieldRange = 99
attributeEnergyDestabilizationAmount = 97
attributeEntityArmorRepairAmount = 631
attributeEntityArmorRepairAmountPerSecond = 1892
attributeEntityArmorRepairDelayChanceSmall = 1009
attributeEntityArmorRepairDelayChanceMedium = 1010
attributeEntityArmorRepairDelayChanceLarge = 1011
attributeEntityArmorRepairDuration = 630
attributeEntityAttackDelayMax = 476
attributeEntityAttackDelayMin = 475
attributeEntityAttackRange = 247
attributeEntityBracketColour = 798
attributeEntityCapacitorLevel = 1894
attributeEntityCapacitorLevelModifierSmall = 1895
attributeEntityCapacitorLevelModifierMedium = 1896
attributeEntityCapacitorLevelModifierLarge = 1897
attributeEntityChaseMaxDelay = 580
attributeEntityChaseMaxDelayChance = 581
attributeEntityChaseMaxDistance = 665
attributeEntityChaseMaxDuration = 582
attributeEntityChaseMaxDurationChance = 583
attributeEntityCruiseSpeed = 508
attributeEntityDefenderChance = 497
attributeEntityEquipmentGroupMax = 465
attributeEntityEquipmentMax = 457
attributeEntityEquipmentMin = 456
attributeEntityFactionLoss = 562
attributeEntityFlyRange = 416
attributeEntityFlyRangeFactor = 772
attributeEntityGroupRespawnChance = 640
attributeEntityGroupArmorResistanceBonus = 1676
attributeEntityGroupArmorResistanceActivationChance = 1682
attributeEntityGroupArmorResistanceDuration = 1681
attributeEntityGroupPropJamBonus = 1675
attributeEntityGroupPropJamActivationChance = 1680
attributeEntityGroupPropJamDuration = 1679
attributeEntityGroupShieldResistanceBonus = 1671
attributeEntityGroupShieldResistanceActivationChance = 1673
attributeEntityGroupShieldResistanceDuration = 1672
attributeEntityGroupSpeedBonus = 1674
attributeEntityGroupSpeedActivationChance = 1678
attributeEntityGroupSpeedDuration = 1677
attributeEntityKillBounty = 481
attributeEntityLootCountMax = 251
attributeEntityLootCountMin = 250
attributeEntityLootValueMax = 249
attributeEntityLootValueMin = 248
attributeEntityMaxVelocitySignatureRadiusMultiplier = 1133
attributeEntityMaxWanderRange = 584
attributeEntityMissileTypeID = 507
attributeEntityRemoteECMBaseDuration = 1661
attributeEntityRemoteECMChanceOfActivation = 1664
attributeEntityRemoteECMDuration = 1658
attributeEntityRemoteECMDurationScale = 1660
attributeEntityRemoteECMExtraPlayerScale = 1662
attributeEntityRemoteECMIntendedNumPlayers = 1663
attributeEntityRemoteECMMinDuration = 1659
attributeEntitySecurityMaxGain = 563
attributeEntitySecurityStatusKillBonus = 252
attributeEntityShieldBoostAmount = 637
attributeEntityShieldBoostAmountPerSecond = 1893
attributeEntityShieldBoostDelayChanceSmall = 1006
attributeEntityShieldBoostDelayChanceMedium = 1007
attributeEntityShieldBoostDelayChanceLarge = 1008
attributeEntityShieldBoostDuration = 636
attributeEntityWarpScrambleChance = 504
attributeExpiryTime = 1088
attributeExplosionDelay = 281
attributeExplosionDelayWreck = 1162
attributeExplosionRange = 107
attributeExplosiveDamage = 116
attributeExplosiveDamageResistanceBonus = 985
attributeExplosiveDamageResonance = 111
attributeExplosiveDamageResonanceMultiplier = 132
attributeExportTax = 1639
attributeExportTaxMultiplier = 1641
attributeExtractorDepletionRange = 1644
attributeExtractorDepletionRate = 1645
attributeFactionID = 1341
attributeFalloff = 158
attributeFalloffBonus = 349
attributeFastTalkPercentage = 359
attributeFighterAttackAndFollow = 1283
attributeFitsToShipType = 1380
attributeFollowsJumpClones = 1916
attributeFwLpKill = 1555
attributeGfxBoosterID = 246
attributeGfxTurretID = 245
attributeHarvesterQuality = 710
attributeHarvesterType = 709
attributeHasFleetHangars = 911
attributeHasCorporateHangars = 911
attributeHasShipMaintenanceBay = 907
attributeHeatAbsorbtionRateHi = 1182
attributeHeatAbsorbtionRateLow = 1184
attributeHeatAbsorbtionRateMed = 1183
attributeHeatAttenuationHi = 1259
attributeHeatAttenuationLow = 1262
attributeHeatAttenuationMed = 1261
attributeHeatCapacityHi = 1178
attributeHeatCapacityLow = 1200
attributeHeatCapacityMed = 1199
attributeHeatDamage = 1211
attributeHeatDissipationRateHi = 1179
attributeHeatDissipationRateLow = 1198
attributeHeatDissipationRateMed = 1196
attributeHeatGenerationMultiplier = 1224
attributeHeatAbsorbtionRateModifier = 1180
attributeHeatHi = 1175
attributeHeatLow = 1177
attributeHeatMed = 1176
attributeHiSlotModifier = 1374
attributeHiSlots = 14
attributeHitsMissilesOnly = 823
attributeHp = 9
attributeHullEmDamageResonance = 974
attributeHullExplosiveDamageResonance = 975
attributeHullKineticDamageResonance = 976
attributeHullThermalDamageResonance = 977
attributeImmuneToSuperWeapon = 1654
attributeDamageDelayDuration = 1839
attributeImpactDamage = 660
attributeImplantness = 331
attributeImportTax = 1638
attributeImportTaxMultiplier = 1640
attributeIncapacitationRatio = 156
attributeIntelligence = 165
attributeInventionMEModifier = 1113
attributeInventionMaxRunModifier = 1124
attributeInventionPEModifier = 1114
attributeInventionPropabilityMultiplier = 1112
attributeIsIncapacitated = 1168
attributeIsArcheology = 1331
attributeIsCapitalSize = 1785
attributeIsCovert = 1252
attributeIsGlobal = 1207
attributeIsHacking = 1330
attributeIsOnline = 2
attributeIsPlayerOwnable = 589
attributeIsRAMcompatible = 998
attributeJumpClonesLeft = 1336
attributeJumpDriveCapacitorNeed = 898
attributeJumpDriveConsumptionAmount = 868
attributeJumpDriveConsumptionType = 866
attributeJumpDriveDuration = 869
attributeJumpDriveRange = 867
attributeJumpHarmonics = 1253
attributeJumpPortalCapacitorNeed = 1005
attributeJumpPortalConsumptionMassFactor = 1001
attributeJumpPortalDuration = 1002
attributejumpDelayDuration = 1221
attributeKineticDamage = 117
attributeKineticDamageResistanceBonus = 986
attributeKineticDamageResonance = 109
attributeKineticDamageResonanceMultiplier = 131
attributeLauncherGroup = 137
attributeLauncherHardPointModifier = 1369
attributeLauncherSlotsLeft = 101
attributeLogisticalCapacity = 1631
attributeLootRespawnTime = 470
attributeLowSlotModifier = 1376
attributeLowSlots = 12
attributeManufactureCostMultiplier = 369
attributeManufactureSlotLimit = 196
attributeManufactureTimeMultiplier = 219
attributeManufacturingTimeResearchSpeed = 385
attributeMass = 4
attributeMassAddition = 796
attributeMaxActiveDrones = 352
attributeMaxDefenseBunkers = 1580
attributeMaxDirectionalVelocity = 661
attributeMaxGangModules = 435
attributeMaxGroupActive = 763
attributeMaxGroupFitted = 1544
attributeMaxJumpClones = 979
attributeMaxLaborotorySlots = 467
attributeMaxLockedTargets = 192
attributeMaxLockedTargetsBonus = 235
attributeMaxMissileVelocity = 664
attributeMaxOperationalDistance = 715
attributeMaxOperationalUsers = 716
attributeMaxRange = 54
attributeMaxRangeBonus = 351
attributeMaxScanDeviation = 788
attributeMaxScanGroups = 1122
attributeMaxShipGroupActive = 910
attributeMaxShipGroupActiveID = 909
attributeMaxStructureDistance = 650
attributeMaxSubSystems = 1367
attributeMaxTargetRange = 76
attributeMaxTargetRangeMultiplier = 237
attributeMaxTractorVelocity = 1045
attributeMaxVelocity = 37
attributeMaxVelocityActivationLimit = 1334
attributeMaxVelocityLimited = 1333
attributeMaxVelocityBonus = 306
attributeMedSlotModifier = 1375
attributeMedSlots = 13
attributeMemory = 166
attributeMetaGroupID = 1692
attributeMetaLevel = 633
attributeMinMissileVelDmgMultiplier = 663
attributeMinScanDeviation = 787
attributeMinTargetVelDmgMultiplier = 662
attributeMineralNeedResearchSpeed = 398
attributeMiningAmount = 77
attributeMiningDroneAmountPercent = 428
attributeMissileDamageMultiplier = 212
attributeMissileEntityAoeCloudSizeMultiplier = 858
attributeMissileEntityAoeFalloffMultiplier = 860
attributeMissileEntityAoeVelocityMultiplier = 859
attributeMissileEntityFlightTimeMultiplier = 646
attributeMissileEntityVelocityMultiplier = 645
attributeMissileNeverDoesDamage = 1075
attributeModifyTargetSpeedChance = 512
attributeModifyTargetSpeedRange = 514
attributeModuleReactivationDelay = 669
attributeModuleRepairRate = 1267
attributeMoonAnchorDistance = 711
attributeMoonMiningAmount = 726
attributeNeutReflectAmount = 1815
attributeNeutReflector = 1809
attributeNonBrokenModuleRepairCostMultiplier = 1276
attributeNonDestructible = 1890
attributeNosReflectAmount = 1814
attributeNosReflector = 1808
attributeNPCAssistancePriority = 1451
attributeNPCAssistanceRange = 1464
attributeNpcCustomsOfficeTaxRate = 1780
attributeNPCRemoteArmorRepairAmount = 1455
attributeNPCRemoteArmorRepairDuration = 1454
attributeNPCRemoteArmorRepairMaxTargets = 1501
attributeNPCRemoteArmorRepairThreshold = 1456
attributeNPCRemoteShieldBoostAmount = 1460
attributeNPCRemoteShieldBoostDuration = 1458
attributeNPCRemoteShieldBoostMaxTargets = 1502
attributeNPCRemoteShieldBoostThreshold = 1462
attributeOnliningDelay = 677
attributeOnliningRequiresSovUpgrade1 = 1601
attributeOrbitalStrikeAccuracy = 1844
attributeOrbitalStrikeDamage = 1845
attributeEntityOverviewShipGroupID = 1766
attributePinCycleTime = 1643
attributePinExtractionQuantity = 1642
attributePosAnchoredPerSolarSystemAmount = 1195
attributePowerTransferAmount = 90
attributeProbeCanScanShips = 1413
attributeOperationalDuration = 719
attributeOptimalSigRadius = 620
attributePackageRadius = 690
attributePerception = 167
attributePassiveEmDamageResistanceBonus = 994
attributePassiveExplosiveDamageResistanceBonus = 995
attributePassiveKineticDamageResistanceBonus = 996
attributePassiveThermicDamageResistanceBonus = 997
attributePlanetAnchorDistance = 865
attributePlanetRestriction = 1632
attributePosCargobayAcceptGroup = 1352
attributePosCargobayAcceptType = 1351
attributePosControlTowerPeriod = 722
attributePosPlayerControlStructure = 1167
attributePosStructureControlAmount = 1174
attributePosStructureControlDistanceMax = 1214
attributePower = 30
attributePowerEngineeringOutputBonus = 313
attributePowerIncrease = 549
attributePowerLoad = 15
attributePowerLoadLevelModifier = 1636
attributePowerLoadPerKm = 1633
attributePowerOutput = 11
attributePowerOutputMultiplier = 145
attributePowerTransferRange = 91
attributeMaxNeutralizationRange = 98
attributePreferredSignatureRadius = 1655
attributePrereqimplant = 641
attributePrimaryAttribute = 180
attributePropulsionFusionStrength = 819
attributePropulsionFusionStrengthBonus = 815
attributePropulsionIonStrength = 820
attributePropulsionIonStrengthBonus = 816
attributePropulsionMagpulseStrength = 821
attributePropulsionMagpulseStrengthBonus = 817
attributePropulsionPlasmaStrength = 822
attributePropulsionPlasmaStrengthBonus = 818
attributeProximityRange = 154
attributeQuantity = 805
attributeRaceID = 195
attributeRadius = 162
attributeRangeFactor = 1373
attributeReactionGroup1 = 842
attributeReactionGroup2 = 843
attributeRechargeRate = 55
attributeRefineryCapacity = 720
attributeRefiningDelayMultiplier = 721
attributeRefiningYieldMultiplier = 717
attributeRefiningYieldPercentage = 378
attributeReloadTime = 1795
attributeReinforcementDuration = 1612
attributeReinforcementVariance = 1613
attributeRepairCostMultiplier = 187
attributeReprocessingSkillType = 790
attributeRequiredSkill1 = 182
attributeRequiredSkill1Level = 277
attributeRequiredSkill2 = 183
attributeRequiredSkill2Level = 278
attributeRequiredSkill3 = 184
attributeRequiredSkill3Level = 279
attributeRequiredSkill4 = 1285
attributeRequiredSkill4Level = 1286
attributeRequiredSkill5 = 1289
attributeRequiredSkill5Level = 1287
attributeRequiredSkill6 = 1290
attributeRequiredSkill6Level = 1288
attributeRequiredThermoDynamicsSkill = 1212
attributeResistanceShiftAmount = 1849
attributeRigSize = 1547
attributeRigSlots = 1137
attributeScanAllStrength = 1136
attributeScanFrequencyResult = 1161
attributeScanGravimetricStrength = 211
attributeScanGravimetricStrengthBonus = 238
attributeScanGravimetricStrengthPercent = 1027
attributeScanLadarStrength = 209
attributeScanLadarStrengthBonus = 239
attributeScanLadarStrengthPercent = 1028
attributeScanMagnetometricStrength = 210
attributeScanMagnetometricStrengthBonus = 240
attributeScanMagnetometricStrengthPercent = 1029
attributeScanRadarStrength = 208
attributeScanRadarStrengthBonus = 241
attributeScanRadarStrengthPercent = 1030
attributeScanWormholeStrength = 1908
attributeScanRange = 765
attributeScanResolution = 564
attributeScanResolutionBonus = 566
attributeScanResolutionMultiplier = 565
attributeScanSpeed = 79
attributeSecondaryAttribute = 181
attributeSecurityProcessingFee = 1904
attributeShieldBonus = 68
attributeShieldCapacity = 263
attributeShieldCapacityMultiplier = 146
attributeShieldCharge = 264
attributeShieldEmDamageResonance = 271
attributeShieldEmDamageResistanceBonus = 1489
attributeShieldExplosiveDamageResonance = 272
attributeShieldExplosiveDamageResistanceBonus = 1490
attributeShieldKineticDamageResonance = 273
attributeShieldKineticDamageResistanceBonus = 1491
attributeShieldRadius = 680
attributeShieldRechargeRate = 479
attributeShieldRechargeRateMultiplier = 134
attributeShieldThermalDamageResonance = 274
attributeShieldThermalDamageResistanceBonus = 1492
attributeShieldUniformity = 484
attributeShipBrokenModuleRepairCostMultiplier = 1277
attributeShipMaintenanceBayCapacity = 908
attributeShipScanResistance = 511
attributeShouldUseEffectMultiplier = 1652
attributeShouldUseEvasiveManeuver = 1414
attributeShouldUseTargetSwitching = 1648
attributeShouldUseSecondaryTarget = 1649
attributeShouldUseSignatureRadius = 1650
attributeSiegeModeWarpStatus = 852
attributeSignatureRadius = 552
attributeSignatureRadiusAdd = 983
attributeSignatureRadiusBonus = 554
attributeSignatureRadiusBonusPercent = 973
attributeSkillLevel = 280
attributeSkillPoints = 276
attributeSkillPointsSaved = 419
attributeSkillTimeConstant = 275
attributeSlots = 47
attributeSmugglingChance = 445
attributeSovBillSystemCost = 1603
attributeSovUpgradeBlockingUpgradeID = 1598
attributeSovUpgradeSovereigntyHeldFor = 1597
attributeSovUpgradeRequiredOutpostUpgradeLevel = 1600
attributeSovUpgradeRequiredUpgradeID = 1599
attributeSpawnWithoutGuardsToo = 903
attributeSpecialCommandCenterHoldCapacity = 1646
attributeSpecialPlanetaryCommoditiesHoldCapacity = 1653
attributeSpecialAmmoHoldCapacity = 1573
attributeSpecialFuelBayCapacity = 1549
attributeSpecialGasHoldCapacity = 1557
attributeSpecialIndustrialShipHoldCapacity = 1564
attributeSpecialLargeShipHoldCapacity = 1563
attributeSpecialMediumShipHoldCapacity = 1562
attributeSpecialMineralHoldCapacity = 1558
attributeSpecialOreHoldCapacity = 1556
attributeSpecialSalvageHoldCapacity = 1559
attributeSpecialShipHoldCapacity = 1560
attributeSpecialSmallShipHoldCapacity = 1561
attributeSpecialTutorialLootRespawnTime = 1582
attributeSpecialMaterialBayCapacity = 1770
attributeSpecialQuafeHoldCapacity = 1804
attributeSpecialisationAsteroidGroup = 781
attributeSpecialisationAsteroidYieldMultiplier = 782
attributeSpeedBonus = 80
attributeSpeedBoostFactor = 567
attributeSpeedFactor = 20
attributeStationTypeID = 472
attributeStructureBonus = 82
attributeStructureDamageAmount = 83
attributeStructureHPMultiplier = 150
attributeStructureUniformity = 525
attributeSubSystemSlot = 1366
attributeSurveyScanRange = 197
attributeSystemEffectDamageReduction = 1686
attributeTypeColorScheme = 1768
attributeTankingModifier = 1657
attributeTankingModifierDrone = 1656
attributeTargetGroup = 189
attributeTargetHostileRange = 143
attributeTargetSwitchDelay = 691
attributeTargetSwitchTimer = 1416
attributeTechLevel = 422
attributeThermalDamage = 118
attributeThermalDamageResistanceBonus = 987
attributeThermalDamageResonance = 110
attributeThermalDamageResonanceMultiplier = 130
attributeTrackingSpeedBonus = 767
attributeDisallowAgainstEwImmuneTarget = 1798
attributeTurretDamageScalingRadius = 1812
attributeTurretHardpointModifier = 1368
attributeTurretSlotsLeft = 102
attributeUnanchoringDelay = 676
attributeUnfitCapCost = 785
attributeUntargetable = 1158
attributeUpgradeCapacity = 1132
attributeUpgradeCost = 1153
attributeUpgradeLoad = 1152
attributeUpgradeSlotsLeft = 1154
attributeUsageWeighting = 862
attributeVolume = 161
attributeVelocityModifier = 1076
attributeWarpBubbleImmune = 1538
attributeWarpCapacitorNeed = 153
attributeWarpScrambleRange = 103
attributeWarpScrambleStatus = 104
attributeWarpScrambleStrength = 105
attributeWarpSpeedMultiplier = 600
attributeWillpower = 168
attributeDisallowActivateOnWarp = 1245
attributeBaseWarpSpeed = 1281
attributeMaxTargetRangeBonus = 309
attributeRateOfFire = 51
attributeWormholeMassRegeneration = 1384
attributeWormholeMaxJumpMass = 1385
attributeWormholeMaxStableMass = 1383
attributeWormholeMaxStableTime = 1382
attributeWormholeTargetSystemClass = 1381
attributeWormholeTargetDistribution = 1457
attributeNumDays = 1551
attributeCharismaBonus = 175
attributeIntelligenceBonus = 176
attributeMemoryBonus = 177
attributePerceptionBonus = 178
attributeWillpowerBonus = 179
attributeVirusCoherence = 1909
attributeVirusStrength = 1910
attributeVirusUtilityElementSlots = 1911
attributeSpewContainerCount = 1912
attributeDefaultJunkLootTypeID = 1913
attributeSpewVelocity = 1914
attributeSpewContainerLifeExtension = 1917
attributeTierDifficulty = 1919

effectAdaptiveArmorHardener = 4928
effectAnchorDrop = 649
effectAnchorDropForStructures = 1022
effectAnchorLift = 650
effectAnchorLiftForStructures = 1023
effectArmorRepair = 27
effectBarrage = 263
effectBombLaunching = 2971
effectCloaking = 607
effectCloakingWarpSafe = 980
effectCloneVatBay = 2858
effectCynosuralGeneration = 2857
effectConcordWarpScramble = 3713
effectConcordModifyTargetSpeed = 3714
effectConcordTargetJam = 3710
effectDecreaseTargetSpeed = 586
effectDecreaseTargetSpeedForStructures = 2480
effectDefenderMissileLaunching = 103
effectDeployPledge = 4774
effectECMBurst = 53
effectEmpWave = 38
effectEmpWaveGrid = 2071
effectEnergyDestabilizationForStructure = 3003
effectEnergyDestabilizationNew = 2303
effectEnergyTransfer = 31
effectEntityArmorRepairing = 5370
effectEntityCapacitorDrain = 1872
effectEntitySensorDampen = 1878
effectEntityShieldBoosting = 5371
effectEntityTargetJam = 1871
effectEntityTargetPaint = 1879
effectEntityTrackingDisrupt = 4982
effectEwTargetPaint = 1549
effectEwTestEffectWs = 1355
effectEwTestEffectJam = 1358
effectFighterMissile = 4729
effectFlagshipmultiRelayEffect = 1495
effectFofMissileLaunching = 104
effectFueledArmorRepair = 5275
effectFueledShieldBoosting = 4936
effectGangBonusSignature = 1411
effectGangShieldBoosterAndTransporterSpeed = 2415
effectGangShieldBoosteAndTransporterCapacitorNeed = 2418
effectGangIceHarvestingDurationBonus = 2441
effectGangInformationWarfareRangeBonus = 2642
effectGangArmorHardening = 1510
effectGangPropulsionJammingBoost = 1546
effectGangShieldHardening = 1548
effectGangECCMfixed = 1648
effectGangArmorRepairCapReducerSelfAndProjected = 3165
effectGangArmorRepairSpeedAmplifierSelfAndProjected = 3167
effectGangMiningLaserAndIceHarvesterAndGasCloudHarvesterMaxRangeBonus = 3296
effectGangGasHarvesterAndIceHarvesterAndMiningLaserDurationBonus = 3302
effectGangGasHarvesterAndIceHarvesterAndMiningLaserCapNeedBonus = 3307
effectGangInformationWarfareSuperiority = 3647
effectGangAbMwdFactorBoost = 1755
effectHackOrbital = 4773
effectHardPointModifier = 3773
effectHiPower = 12
effectIndustrialCoreEffect = 4575
effectJumpPortalGeneration = 2152
effectJumpPortalGenerationBO = 3674
effectLauncherFitted = 40
effectLeech = 3250
effectLoPower = 11
effectMedPower = 13
effectMicroJumpDrive = 4921
effectMineLaying = 102
effectMining = 17
effectMiningClouds = 2726
effectMiningLaser = 67
effectMissileLaunching = 9
effectMissileLaunchingForEntity = 569
effectModifyTargetSpeed2 = 575
effectNPCGroupArmorAssist = 4689
effectNPCGroupPropJamAssist = 4688
effectNPCGroupShieldAssist = 4686
effectNPCGroupSpeedAssist = 4687
effectNPCRemoteArmorRepair = 3852
effectNPCRemoteShieldBoost = 3855
effectNPCRemoteECM = 4656
effectOffensiveDefensiveReduction = 4728
effectOnline = 16
effectOnlineForStructures = 901
effectOpenSpawnContainer = 1738
effectOrbitalStrike = 5141
effectProbeLaunching = 3793
effectProjectileFired = 34
effectProjectileFiredForEntities = 1086
effectRemoteHullRepair = 3041
effectRemoteEcmBurst = 2913
effectRigSlot = 2663
effectSalvageDroneEffect = 5163
effectSalvaging = 2757
effectScanStrengthBonusTarget = 124
effectscanStrengthTargetPercentBonus = 2246
effectShieldBoosting = 4
effectShieldTransfer = 18
effectShieldResonanceMultiplyOnline = 105
effectSiegeModeEffect = 4877
effectSkillEffect = 132
effectSlotModifier = 3774
effectSnowBallLaunching = 2413
effectStructureUnanchorForced = 1129
effectStructureRepair = 26
effectSubSystem = 3772
effectSuicideBomb = 885
effectSuperWeaponAmarr = 4489
effectSuperWeaponCaldari = 4490
effectSuperWeaponGallente = 4491
effectSuperWeaponMinmatar = 4492
effectTargetArmorRepair = 592
effectTargetAttack = 10
effectTargetAttackForStructures = 1199
effectTargetBreaker = 4942
effectTargetTrackingDisruptorCombinedGunneryAndMissileEffect = 4932
effectTargetGunneryMaxRangeAndTrackingSpeedBonusHostile = 3555
effectTargetGunneryMaxRangeAndTrackingSpeedAndFalloffBonusHostile = 3690
effectTargetMaxTargetRangeAndScanResolutionBonusHostile = 3584
effectTargetGunneryMaxRangeAndTrackingSpeedBonusAssistance = 3556
effectTargetMaxTargetRangeAndScanResolutionBonusAssistance = 3583
effectTargetPassively = 54
effectTorpedoLaunching = 127
effectTorpedoLaunchingIsOffensive = 2576
effectTractorBeamCan = 2255
effectTriageMode = 4839
effectTriageMode7 = 4893
effectTurretFitted = 42
effectTurretWeaponRangeFalloffTrackingSpeedMultiplyTargetHostile = 3697
effectUseMissiles = 101
effectWarpDisruptSphere = 3380
effectWarpScramble = 39
effectWarpScrambleForEntity = 563
effectWarpScrambleForStructure = 2481
effectWarpScrambleTargetMWDBlockActivation = 3725
effectModifyShieldResonancePostPercent = 2052
effectModifyArmorResonancePostPercent = 2041
effectModifyHullResonancePostPercent = 3791
effectShipMaxTargetRangeBonusOnline = 3659
effectSensorBoostTargetedHostile = 837
effectmaxTargetRangeBonus = 2646

dgmUnnerfedCategories = [
	categorySkill,
	categoryImplant,
	categoryShip,
	categoryCharge,
	categorySubSystem
]

bloodlineAchura = 11
bloodlineAmarr = 5
bloodlineBrutor = 4
bloodlineCivire = 2
bloodlineDeteis = 1
bloodlineGallente = 7
bloodlineIntaki = 8
bloodlineJinMei = 12
bloodlineKhanid = 13
bloodlineModifier = 10
bloodlineNiKunni = 6
bloodlineSebiestor = 3
bloodlineStatic = 9
bloodlineVherokior = 14

raceAmarr = 4
raceCaldari = 1
raceGallente = 8
raceJove = 16
raceMinmatar = 2

cacheAccRefTypes                        = 102
cacheLogEventTypes                      = 105
cacheMktOrderStates                     = 106
cachePetCategories                      = 107
cachePetQueues                          = 108
cacheChrRaces                           = 111
cacheChrBloodlines                      = 112
cacheChrAncestries                      = 113
cacheChrSchools                         = 114
cacheChrAttributes                      = 115
cacheChrCareers                         = 116
cacheChrSpecialities                    = 117
cacheCrpRegistryGroups                  = 119
cacheCrpRegistryTypes                   = 120
cacheDungeonTriggerTypes                = 121
cacheDungeonEventTypes                  = 122
cacheDungeonEventMessageTypes           = 123
cacheStaOperations                      = 127
cacheCrpActivities                      = 128
cacheDungeonArchetypes                  = 129
cacheTutCriterias                       = 133
cacheTutTutorials                       = 134
cacheTutContextHelp                     = 135
cacheTutCategories                      = 136
cacheSystemEventTypes                   = 138
cacheUserEventTypes                     = 139
cacheUserColumns                        = 140
cacheSystemProcedures                   = 141
cacheStaticSettings                     = 142

cacheChrFactions                        = 201
cacheDungeonDungeons                    = 202
cacheMapSolarSystemJumpIDs              = 203
cacheMapSolarSystemPseudoSecurities     = 204
cacheInvTypeMaterials                   = 205
cacheMapCelestialDescriptions           = 206
cacheGMQueueOrder                       = 207
cacheStaStationUpgradeTypes             = 208
cacheStaStationImprovementTypes         = 209
cacheStaSIDAssemblyLineType             = 210
cacheStaSIDAssemblyLineTypeQuantity     = 211
cacheStaSIDAssemblyLineQuantity         = 212
cacheStaSIDReprocessingEfficiency       = 213
cacheStaSIDOfficeSlots                  = 214
cacheStaSIDServiceMask                  = 215
cacheDogmaTypeAttributes                = 216
cacheDogmaTypeEffects                   = 217
cacheMapRegions                         = 218
cacheMapConstellations                  = 219
cacheMapSolarSystems                    = 220
cacheStaStations                        = 221
cacheMapPlanets                         = 222
cacheRamTypeRequirements                = 223
cacheInvWreckUsage                      = 224
cacheAgentEpicArcs                      = 226
cacheReverseEngineeringTables           = 227
cacheReverseEngineeringTableTypes       = 228
cacheAgentEpicArcJournalData            = 229
cacheAgentEpicMissionMessages           = 230
cacheAgentEpicMissionsStarting          = 231
cacheAgentEpicMissionsBranching         = 232
cacheAgentCorporations                  = 233
cacheAgentCorporationActivities         = 234
cacheAgentEpicMissionsNonEnd            = 235
cacheLocationWormholeClasses            = 236
cacheAgentEpicArcMissions               = 237
cacheAgentEpicArcConnections            = 238

cacheCrpNpcDivisions                    = 303
cacheMapSolarSystemLoadRatios           = 304
cacheStaServices                        = 305
cacheStaOperationServices               = 306

cacheInvCategories                      = 401
cacheInvGroups                          = 402
cacheInvTypes                           = 403
cacheInvBlueprintTypes                  = 404
cacheCrpNpcCorporations                 = 405
cacheAgentAgents                        = 406
cacheDogmaExpressionCategories          = 407
cacheDogmaExpressions                   = 408
cacheDogmaOperands                      = 409
cacheDogmaAttributes                    = 410
cacheDogmaEffects                       = 411
cacheEveMessages                        = 419
cacheEveGraphics                        = 420
cacheMapTypeBalls                       = 421
cacheNpcTypeLoots                       = 423
cacheNpcLootTableFrequencies            = 424
cacheNpcSupplyDemand                    = 425
cacheNpcTypeGroupingClasses             = 427
cacheNpcTypeGroupings                   = 428
cacheNpcTypeGroupingTypes               = 429
cacheNpcTypeGroupingClassSettings       = 430
cacheCrpNpcMembers                      = 431
cacheCrpCorporations                    = 432
cacheAgtContentTemplates                = 433
cacheAgtContentFlowControl              = 434
cacheAgentMissionsKill                  = 435
cacheAgtContentCourierMissions          = 436
cacheAgtContentExchangeOffers           = 437
cacheCrpPlayerCorporationIDs            = 438
cacheEosNpcToNpcStandings               = 439
cacheRamActivities                      = 440
cacheRamAssemblyLineTypes               = 441
cacheRamAssemblyLineTypesCategory       = 442
cacheRamAssemblyLineTypesGroup          = 443
cacheRamInstallationTypes               = 444
cacheRamSkillInfo                       = 445
cacheMktNpcMarketData                   = 446
cacheNpcCommands                        = 447
cacheNpcDirectorCommands                = 448
cacheNpcDirectorCommandParameters       = 449
cacheNpcCommandLocations                = 450
cacheEvePrimeOwners                     = 451
cacheEvePrimeLocations                  = 452
cacheInvTypeReactions                   = 453
cacheAgtPrices                          = 454
cacheAgtResearchStartupData             = 455
cacheAgtOfferDetails                    = 456
cacheAgtStorylineMissions               = 457
cacheAgtOfferTableContents              = 458
cacheFacWarCombatZones                  = 459
cacheFacWarCombatZoneSystems            = 460
cacheAgtContentAgentInteractionMissions = 461
cacheAgtContentTalkToAgentMissions      = 462
cacheAgtContentMissionTutorials         = 463

cacheEspCharacters      = 10002
cacheEspCorporations    = 10003
cacheEspAlliances       = 10004
cacheEspSolarSystems    = 10005
cacheSolarSystemObjects = 10006
cacheCargoContainers    = 10007
cachePriceHistory       = 10008
cacheTutorialVersions   = 10009
cacheSolarSystemOffices = 10010

tableTutorialTutorials = 200001
tableDungeonDungeons   = 300005
tableAgentMissions     = 3000002

corpLogoChangeCost = 100
corpRoleAccountCanQuery1 = 17179869184
corpRoleAccountCanQuery2 = 34359738368
corpRoleAccountCanQuery3 = 68719476736
corpRoleAccountCanQuery4 = 137438953472
corpRoleAccountCanQuery5 = 274877906944
corpRoleAccountCanQuery6 = 549755813888
corpRoleAccountCanQuery7 = 1099511627776
corpRoleAccountCanTake1 = 134217728
corpRoleAccountCanTake2 = 268435456
corpRoleAccountCanTake3 = 536870912
corpRoleAccountCanTake4 = 1073741824
corpRoleAccountCanTake5 = 2147483648
corpRoleAccountCanTake6 = 4294967296
corpRoleAccountCanTake7 = 8589934592
corpRoleAccountant = 256
corpRoleAuditor = 4096
corpRoleCanRentFactorySlot = 1125899906842624
corpRoleCanRentOffice = 562949953421312
corpRoleCanRentResearchSlot = 2251799813685248
corpRoleChatManager = 36028797018963968
corpRoleContainerCanTake1 = 4398046511104
corpRoleContainerCanTake2 = 8796093022208
corpRoleContainerCanTake3 = 17592186044416
corpRoleContainerCanTake4 = 35184372088832
corpRoleContainerCanTake5 = 70368744177664
corpRoleContainerCanTake6 = 140737488355328
corpRoleContainerCanTake7 = 281474976710656
corpRoleContractManager = 72057594037927936
corpRoleStarbaseCaretaker = 288230376151711744
corpRoleDirector = 1
corpRoleEquipmentConfig = 2199023255552
corpRoleFactoryManager = 1024
corpRoleFittingManager = 576460752303423488
corpRoleHangarCanQuery1 = 1048576
corpRoleHangarCanQuery2 = 2097152
corpRoleHangarCanQuery3 = 4194304
corpRoleHangarCanQuery4 = 8388608
corpRoleHangarCanQuery5 = 16777216
corpRoleHangarCanQuery6 = 33554432
corpRoleHangarCanQuery7 = 67108864
corpRoleHangarCanTake1 = 8192
corpRoleHangarCanTake2 = 16384
corpRoleHangarCanTake3 = 32768
corpRoleHangarCanTake4 = 65536
corpRoleHangarCanTake5 = 131072
corpRoleHangarCanTake6 = 262144
corpRoleHangarCanTake7 = 524288
corpRoleJuniorAccountant = 4503599627370496
corpRoleLocationTypeBase = 2
corpRoleLocationTypeHQ = 1
corpRoleLocationTypeOther = 3
corpRolePersonnelManager = 128
corpRoleSecurityOfficer = 512
corpRoleStarbaseConfig = 9007199254740992
corpRoleStationManager = 2048
corpRoleTrader = 18014398509481984
corpRoleInfrastructureTacticalOfficer = 144115188075855872
corpStationMgrGraceMinutes = 60
corpactivityEducation = 18
corpactivityEntertainment = 8
corpactivityMilitary = 5
corpactivitySecurity = 16
corpactivityTrading = 12
corpactivityWarehouse = 10
corpdivisionAccounting = 1
corpdivisionAdministration = 2
corpdivisionAdvisory = 3
corpdivisionArchives = 4
corpdivisionAstrosurveying = 5
corpdivisionCommand = 6
corpdivisionDistribution = 7
corpdivisionFinancial = 8
corpdivisionIntelligence = 9
corpdivisionInternalSecurity = 10
corpdivisionLegal = 11
corpdivisionManufacturing = 12
corpdivisionMarketing = 13
corpdivisionMining = 14
corpdivisionPersonnel = 15
corpdivisionProduction = 16
corpdivisionPublicRelations = 17
corpdivisionSecurity = 19
corpdivisionStorage = 20
corpdivisionSurveillance = 21
corporationStartupCost = 1599800
corporationAdvertisementFlatFee = 500000
corporationAdvertisementDailyRate = 250000

dunArchetypeAgentMissionDungeon = 20
dunArchetypeFacwarDefensive = 32
dunArchetypeFacwarOffensive = 35
dunArchetypeFacwarDungeons = (dunArchetypeFacwarDefensive, dunArchetypeFacwarOffensive)
dunArchetypeWormhole = 38
dunArchetypeZTest = 19
dunEventMessageEnvironment = 3
dunEventMessageImminentDanger = 1
dunEventMessageMissionInstruction = 7
dunEventMessageMissionObjective = 6
dunEventMessageMood = 4
dunEventMessageNPC = 2
dunEventMessageStory = 5
dunEventMessageWarning = 8
dunExpirationDelay = 48
dunTriggerArchaeologyFailure = 16
dunTriggerArchaeologySuccess = 15
dunTriggerArmorConditionLevel = 5
dunTriggerAttacked = 1
dunTriggerEventActivateGate = 1
dunTriggerEventAgentMessage = 23
dunTriggerEventAgentTalkTo = 22
dunTriggerEventDropLoot = 24
dunTriggerEventDungeonCompletion = 11
dunTriggerEventEffectBeaconActivate = 13
dunTriggerEventEffectBeaconDeactivate = 14
dunTriggerEventEntityDespawn = 18
dunTriggerEventEntityExplode = 19
dunTriggerFacWarVictoryPointsGranted = 20
dunTriggerEventMessage = 10
dunTriggerEventMissionCompletion = 9
dunTriggerEventObjectDespawn = 15
dunTriggerEventObjectExplode = 16
dunTriggerEventRangedNPCHealing = 4
dunTriggerEventRangedPlayerDamageEM = 5
dunTriggerEventRangedPlayerDamageExplosive = 6
dunTriggerEventRangedPlayerDamageKinetic = 7
dunTriggerEventRangedPlayerDamageThermal = 8
dunTriggerEventSpawnGuardObject = 3
dunTriggerEventSpawnGuards = 2
dunTriggerExploding = 3
dunTriggerFWProximityEntered = 21
dunTriggerHackingFailure = 12
dunTriggerHackingSuccess = 11
dunTriggerItemPlacedInMissionContainer = 23
dunTriggerMined = 7
dunTriggerProximityEntered = 2
dunTriggerRoomCapturedAlliance = 19
dunTriggerRoomCapturedFacWar = 20
dunTriggerRoomCapturedCorp = 18
dunTriggerRoomEntered = 8
dunTriggerRoomMined = 10
dunTriggerRoomMinedOut = 9
dunTriggerSalvagingFailure = 14
dunTriggerSalvagingSuccess = 13
dunTriggerShieldConditionLevel = 4
dunTriggerShipEnteredBubble = 17
dunTriggerStructureConditionLevel = 6
dungeonGateUnlockPeriod = 66

DUNGEON_ORIGIN_UNDEFINED = None
DUNGEON_ORIGIN_STATIC = 1
DUNGEON_ORIGIN_AGENT = 2
DUNGEON_ORIGIN_PLAYTEST = 3
DUNGEON_ORIGIN_EDIT = 4
DUNGEON_ORIGIN_DISTRIBUTION = 5
DUNGEON_ORIGIN_PATH = 6
DUNGEON_ORIGIN_TUTORIAL = 7

ixItemID = 0
ixTypeID = 1
ixOwnerID = 2
ixLocationID = 3
ixFlag = 4
ixContraband = 5
ixSingleton = 6
ixQuantity = 7
ixGroupID = 8
ixCategoryID = 9
ixCustomInfo = 10

ownerBank = 2
ownerCONCORD = 1000125
ownerNone = 0
ownerSCC = 1000132
ownerStation = 4
ownerSystem = 1
ownerUnknown = 3006
ownerCombatSimulator = 5

locationAbstract = 0
locationSystem = 1
locationBank = 2
locationTemp = 5
locationRecycler = 6
locationTrading = 7
locationGraveyard = 8
locationUniverse = 9
locationHiddenSpace = 9000001
locationJunkyard = 10
locationCorporation = 13
locationSingletonJunkyard = 25
locationTradeSessionJunkyard = 1008
locationCharacterGraveyard = 1501
locationCorporationGraveyard = 1502
locationRAMInstalledItems = 2003
locationAlliance = 3007

minFaction = 500000
maxFaction = 599999
minNPCCorporation = 1000000
maxNPCCorporation = 1999999
minAgent = 3000000
maxAgent = 3999999
minRegion = 10000000
maxRegion = 19999999
minConstellation = 20000000
maxConstellation = 29999999
minSolarSystem = 30000000
maxSolarSystem = 39999999
minValidLocation = 30000000
minValidShipLocation = 30000000
minUniverseCelestial = 40000000
maxUniverseCelestial = 49999999
minStargate = 50000000
maxStargate = 59999999
minStation = 60000000
maxStation = 69999999
minValidCharLocation = 60000000
minUniverseAsteroid = 70000000
maxUniverseAsteroid = 79999999
minPlayerItem = 100000000
maxPlayerItem = 2099999999
minFakeItem = 2100000000
maxNonCapitalModuleSize = 500

factionAmarrEmpire = 500003
factionAmmatar = 500007
factionAngelCartel = 500011
factionCONCORDAssembly = 500006
factionCaldariState = 500001
factionGallenteFederation = 500004
factionGuristasPirates = 500010
factionInterBus = 500013
factionJoveEmpire = 500005
factionKhanidKingdom = 500008
factionMinmatarRepublic = 500002
factionMordusLegion = 500018
factionORE = 500014
factionOuterRingExcavations = 500014
factionSanshasNation = 500019
factionSerpentis = 500020
factionSistersOfEVE = 500016
factionSocietyOfConsciousThought = 500017
factionTheBloodRaiderCovenant = 500012
factionTheServantSistersofEVE = 500016
factionTheSyndicate = 500009
factionThukkerTribe = 500015
factionUnknown = 500021
factionMordusLegionCommand = 500018
factionTheInterBus = 500013
factionAmmatarMandate = 500007
factionTheSociety = 500017

eventCertificateGranted = 231
eventCertificateGrantedGM = 232
eventCertificateRevokedGM = 233
eventDungeonActivategate = 147
eventDungeonCompleteAgent = 146
eventDungeonCompleteDistribution = 176
eventDungeonCompletePathDungeon = 179
eventDungeonEnter = 143
eventDungeonEnterAgent = 144
eventDungeonEnterDistribution = 175
eventDungeonEnterPathDungeon = 178
eventDungeonExpireDistribution = 186
eventDungeonExpirePathDungeon = 180
eventDungeonGivenPathDungeon = 181
eventDungeonSpawnBlockedByOther = 59
eventMissionAccepted = 88
eventMissionAllocationFailure_ItemDeclarationError = 124
eventMissionAllocationFailure_ItemResolutionFailure = 123
eventMissionAllocationFailure_SanityCheckFailure = 122
eventMissionAllocationFailure_UnexpectedException = 125
eventMissionDeclined = 120
eventMissionFailed = 87
eventMissionOfferExpired = 121
eventMissionOfferRemoved = 122
eventMissionOffered = 118
eventMissionQuit = 119
eventMissionSucceeded = 86
eventEpicArcStarted = 243
eventEpicArcCompleted = 244
eventResearchBlueprintAccepted = 106
eventResearchBlueprintOfferExpired = 105
eventResearchBlueprintOfferInvalid = 111
eventResearchBlueprintOfferRejectedIncompatibleAgent = 110
eventResearchBlueprintOfferRejectedInvalidBlueprint = 109
eventResearchBlueprintOfferRejectedRecently = 108
eventResearchBlueprintOfferRejectedTooLowStandings = 107
eventResearchBlueprintOffered = 101
eventResearchBlueprintRejected = 102
eventResearchStarted = 103
eventResearchStopped = 104
eventStandingAgentBuyOff = 71
eventStandingAgentDonation = 72
eventStandingAgentMissionBonus = 80
eventStandingAgentMissionCompleted = 73
eventStandingAgentMissionDeclined = 75
eventStandingAgentMissionFailed = 74
eventStandingAgentMissionOfferExpired = 90
eventStandingCombatAggression = 76
eventStandingCombatAssistance = 112
eventStandingCombatOther = 79
eventStandingCombatPodKill = 78
eventStandingCombatShipKill = 77
eventStandingContrabandTrafficking = 126
eventStandingDecay = 49
eventStandingDerivedModificationNegative = 83
eventStandingDerivedModificationPositive = 82
eventStandingInitialCorpAgent = 52
eventStandingInitialFactionAlly = 70
eventStandingInitialFactionCorp = 54
eventStandingInitialFactionEnemy = 69
eventStandingPirateKillSecurityStatus = 89
eventStandingPlayerCorpSetStanding = 68
eventStandingPlayerSetStanding = 65
eventStandingPropertyDamage = 154
eventStandingReCalcEntityKills = 58
eventStandingReCalcMissionFailure = 61
eventStandingReCalcMissionSuccess = 55
eventStandingReCalcPirateKills = 57
eventStandingReCalcPlayerSetStanding = 67
eventStandingSlashSet = 84
eventStandingStandingreset = 25
eventStandingTutorialAgentInitial = 81
eventStandingUpdatestanding = 45
eventStandingPromotionStandingIncrease = 216
eventStationMoveSystemFull = 234

eventStandingCombatShipKill_OwnFaction = 223
eventStandingCombatPodKill_OwnFaction = 224
eventStandingCombatAggression_OwnFaction = 225
eventStandingCombatAssistance_OwnFaction = 226
eventStandingPropertyDamage_OwnFaction = 227
eventStandingCombatOther_OwnFaction = 228
eventStandingTacticalSiteDefended = 229
eventStandingTacticalSiteConquered = 230

eventStandingRecommendationLetterUsed = 60

eventUnspecifiedAddOffice = 46
eventSlashSetqty = 30
eventSlashSpawn = 28
eventSlashUnspawn = 29
eventUnspecifiedLootgift = 23
eventUnspecifiedContractDelete = 187
eventResearchPointsEdited = 189
eventLPGain = 203
eventLPLoss = 204
eventLPGMChange = 205
eventUnrentOfficeGM = 211
eventUnspecifiedContractMarkFinished = 212

eventCharacterAttributeRespecScheduled = 50
eventCharacterAttributeRespecFree = 51

refSkipLog = -1
refUndefined = 0
refPlayerTrading = 1
refMarketTransaction = 2
refGMCashTransfer = 3
refATMWithdraw = 4
refATMDeposit = 5
refBackwardCompatible = 6
refMissionReward = 7
refCloneActivation = 8
refInheritance = 9
refPlayerDonation = 10
refCorporationPayment = 11
refDockingFee = 12
refOfficeRentalFee = 13
refFactorySlotRentalFee = 14
refRepairBill = 15
refBounty = 16
refBountyPrize = 17
refInsurance = 19
refMissionExpiration = 20
refMissionCompletion = 21
refShares = 22
refCourierMissionEscrow = 23
refMissionCost = 24
refAgentMiscellaneous = 25
refPaymentToLPStore = 26
refAgentLocationServices = 27
refAgentDonation = 28
refAgentSecurityServices = 29
refAgentMissionCollateralPaid = 30
refAgentMissionCollateralRefunded = 31
refAgentMissionReward = 33
refAgentMissionTimeBonusReward = 34
refCSPA = 35
refCSPAOfflineRefund = 36
refCorporationAccountWithdrawal = 37
refCorporationDividendPayment = 38
refCorporationRegistrationFee = 39
refCorporationLogoChangeCost = 40
refReleaseOfImpoundedProperty = 41
refMarketEscrow = 42
refMarketFinePaid = 44
refBrokerfee = 46
refAllianceRegistrationFee = 48
refWarFee = 49
refAllianceMaintainanceFee = 50
refContrabandFine = 51
refCloneTransfer = 52
refAccelerationGateFee = 53
refTransactionTax = 54
refJumpCloneInstallationFee = 55
refManufacturing = 56
refResearchingTechnology = 57
refResearchingTimeProductivity = 58
refResearchingMaterialProductivity = 59
refCopying = 60
refDuplicating = 61
refReverseEngineering = 62
refContractAuctionBid = 63
refContractAuctionBidRefund = 64
refContractCollateral = 65
refContractRewardRefund = 66
refContractAuctionSold = 67
refContractReward = 68
refContractCollateralRefund = 69
refContractCollateralPayout = 70
refContractPrice = 71
refContractBrokersFee = 72
refContractSalesTax = 73
refContractDeposit = 74
refContractDepositSalesTax = 75
refSecureEVETimeCodeExchange = 76
refContractAuctionBidCorp = 77
refContractCollateralCorp = 78
refContractPriceCorp = 79
refContractBrokersFeeCorp = 80
refContractDepositCorp = 81
refContractDepositRefund = 82
refContractRewardAdded = 83
refContractRewardAddedCorp = 84
refBountyPrizes = 85
refCorporationAdvertisementFee = 86
refMedalCreation = 87
refMedalIssuing = 88
refAttributeRespecification = 90
refSovereignityRegistrarFee = 91
refSovereignityUpkeepAdjustment = 95
refPlanetaryImportTax = 96
refPlanetaryExportTax = 97
refPlanetaryConstruction = 98
refRewardManager = 99
refBountySurcharge = 101
refContractReversal = 102
refStorePurchase = 106
refStoreRefund = 107
refPlexConversion = 108
refAurumGiveAway = 109
refAurumTokenConversion = 111
refDatacoreFee = 112
refWarSurrenderFee = 113
refWarAllyContract = 114
refBountyReimbursement = 115
refKillRightBuy = 116
refSecurityTagProcessingFee = 117
refMaxEve = 10000
refCorporationTaxNpcBounties = 92
refCorporationTaxAgentRewards = 93
refCorporationTaxAgentBonusRewards = 94
refCorporationTaxRewards = 103

stationServiceBountyMissions        =         1
stationServiceAssassinationMissions =         2
stationServiceCourierMission        =         4
stationServiceInterbus              =         8
stationServiceReprocessingPlant     =        16
stationServiceRefinery              =        32
stationServiceMarket                =        64
stationServiceBlackMarket           =       128
stationServiceStockExchange         =       256
stationServiceCloning               =       512
stationServiceSurgery               =      1024
stationServiceDNATherapy            =      2048
stationServiceRepairFacilities      =      4096
stationServiceFactory               =      8192
stationServiceLaboratory            =     16384
stationServiceGambling              =     32768
stationServiceFitting               =     65536
stationServiceNews                  =    262144
stationServiceStorage               =    524288
stationServiceInsurance             =   1048576
stationServiceDocking               =   2097152
stationServiceOfficeRental          =   4194304
stationServiceJumpCloneFacility     =   8388608
stationServiceLoyaltyPointStore     =  16777216
stationServiceNavyOffices           =  33554432
stationServiceStorefronts           =  67108864
stationServiceCombatSimulator       = 134217728

unitAbsolutePercent = 127
unitAttributeID = 119
unitAttributePoints = 120
unitGroupID = 115
unitInverseAbsolutePercent = 108
unitInversedModifierPercent = 111
unitLength = 1 
unitMass = 2
unitMilliseconds = 101
unitModifierPercent = 109
unitSizeclass = 117
unitTime = 3
unitTypeID = 116
unitVolume = 9
unitCapacitorUnits = 114

billTypeMarketFine = 1
billTypeRentalBill = 2
billTypeBrokerBill = 3
billTypeWarBill = 4
billTypeAllianceMaintainanceBill = 5

chrattrIntelligence = 1
chrattrCharisma = 2
chrattrPerception = 3
chrattrMemory = 4
chrattrWillpower = 5

completedStatusAborted = 2
completedStatusUnanchored = 4
completedStatusDestroyed = 5

ramActivityCopying = 5
ramActivityDuplicating = 6
ramActivityInvention = 8
ramActivityManufacturing = 1
ramActivityNone = 0
ramActivityResearchingMaterialProductivity = 4
ramActivityResearchingTimeProductivity = 3
ramActivityReverseEngineering = 7

ramJobStatusPending = 1
ramJobStatusInProgress = 2
ramJobStatusReady = 3
ramJobStatusDelivered = 4
ramMaxCopyRuns = 20
ramMaxProductionTimeInDays = 30
ramRestrictNone = 0
ramRestrictBySecurity = 1
ramRestrictByStanding = 2
ramRestrictByCorp = 4
ramRestrictByAlliance = 8

activityCopying = 5
activityDuplicating = 6
activityInvention = 8
activityManufacturing = 1
activityNone = 0
activityResearchingMaterialProductivity = 4
activityResearchingTechnology = 2
activityResearchingTimeProductivity = 3
activityReverseEngineering = 7

conAvailPrivate = 1
conAvailPublic = 0

conStatusOutstanding = 0
conStatusInProgress = 1
conStatusFinishedIssuer = 2
conStatusFinishedContractor = 3
conStatusFinished = 4
conStatusCancelled = 5
conStatusRejected = 6
conStatusFailed = 7

conTypeNothing = 0
conTypeItemExchange = 1
conTypeAuction = 2
conTypeCourier = 3
conTypeLoan = 4
conTypeFreeform = 5

facwarCorporationJoining = 0
facwarCorporationActive = 1
facwarCorporationLeaving = 2
facwarStandingPerVictoryPoint = 0.0015
facwarWarningStandingCharacter = 0
facwarWarningStandingCorporation = 1
facwarOccupierVictoryPointBonus = 0.1
facwarStatTypeKill = 0
facwarStatTypeLoss = 1

averageManufacturingCostPerUnitTime = 0
blockAmarrCaldari = 1
blockGallenteMinmatar = 2
blockSmugglingCartel = 3
blockTerrorist = 4
cargoContainerLifetime = 120

containerBank = 10007
containerCharacter = 10011
containerCorpMarket = 10012
containerGlobal = 10002
containerHangar = 10004
containerOffices = 10009
containerRecycler = 10008
containerScrapHeap = 10005
containerSolarSystem = 10003
containerStationCharacters = 10010
containerWallet = 10001
costCloneContract = 5600
costJumpClone = 100000
crpApplicationAcceptedByCharacter = 2
crpApplicationAcceptedByCorporation = 6
crpApplicationAppliedByCharacter = 0
crpApplicationRejectedByCharacter = 3
crpApplicationRejectedByCorporation = 4
crpApplicationRenegotiatedByCharacter = 1
crpApplicationRenegotiatedByCorporation = 5
deftypeCapsule = 670
deftypeHouseWarmingGift = 34
directorConcordSecurityLevelMax = 1000
directorConcordSecurityLevelMin = 450
directorConvoySecurityLevelMin = 450
directorPirateGateSecurityLevelMax = 349
directorPirateGateSecurityLevelMin = -1000
directorPirateSecurityLevelMax = 849
directorPirateSecurityLevelMin = -1000
entityApproaching = 3
entityCombat = 1
entityDeparting = 4
entityDeparting2 = 5
entityEngage = 10
entityFleeing = 7
entityIdle = 0
entityMining = 2
entityOperating = 9
entityPursuit = 6
gangGroupingRange = 300
gangJobCreator = 2
gangJobNone = 0
gangJobScout = 1
gangLeaderRole = 1

gangRoleLeader = 1
gangRoleMember = 4
gangRoleSquadCmdr = 3
gangRoleWingCmdr = 2

gangBoosterNone = 0
gangBoosterFleet = 1
gangBoosterWing = 2
gangBoosterSquad = 3

graphicShipLayerColor0 = 671
graphicShipLayerShape0 = 415
graphicUnknown = 0
invulnerabilityDocking = 3000
invulnerabilityJumping = 5000
invulnerabilityRestoring = 60000
invulnerabilityUndocking = 30000
invulnerabilityWarpingIn = 10000
invulnerabilityWarpingOut = 5000
jumpRadiusFactor = 130
jumpRadiusRandom = 15000
lifetimeOfDefaultContainer = 120
lifetimeOfDurableContainers = 43200
limitCloneJumpHours = 24
lockedContainerAccessTime = 180000
marketCommissionPercentage = 1
maxBoardingDistance = 6550
maxBuildDistance = 10000
maxCargoContainerTransferDistance = 1500
maxConfigureDistance = 5000
maxDockingDistance = 50000
maxDungeonPlacementDistance = 300
maxItemCountPerLocation = 1000
maxJumpInDistance = 13000
maxPetitionsPerDay = 2
maxSelfDestruct = 15000
maxStargateJumpingDistance = 2500
maxWormholeEnterDistance = 5000
maxWarpEndDistance = 100000
maxWarpSpeed = 30
minAutoPilotWarpInDistance = 15000
minDungeonPlacementDistance = 25
minJumpInDistance = 12000
minSpawnContainerDelay = 300000
minWarpDistance = 150000
minWarpEndDistance = 0
mktMinimumFee = 100
mktModificationDelay = 300
mktOrderCancelled = 3
mktOrderExpired = 2
mktTransactionTax = 1
npcCorpMax = 1999999
npcCorpMin = 1000000
npcDivisionAccounting = 1
npcDivisionAdministration = 2
npcDivisionAdvisory = 3
npcDivisionArchives = 4
npcDivisionAstrosurveying = 5
npcDivisionCommand = 6
npcDivisionDistribution = 7
npcDivisionFinancial = 8
npcDivisionIntelligence = 9
npcDivisionInternalSecurity = 10
npcDivisionLegal = 11
npcDivisionManufacturing = 12
npcDivisionMarketing = 13
npcDivisionMining = 14
npcDivisionPersonnel = 15
npcDivisionProduction = 16
npcDivisionPublicRelations = 17
npcDivisionRD = 18
npcDivisionSecurity = 19
npcDivisionStorage = 20
npcDivisionSurveillance = 21
onlineCapacitorChargeRatio = 95
onlineCapacitorRemainderRatio = 33
outlawSecurityStatus = -5
petitionMaxChatLogSize = 200000
petitionMaxCombatLogSize = 200000
posShieldStartLevel = 0.505
posMaxShieldPercentageForWatch = 0.95
posMinDamageDiffToPersist = 0.05
rangeConstellation = 4
rangeRegion = 32767
rangeSolarSystem = 0
rangeStation = -1
rentalPeriodOffice = 30
repairCostPercentage = 100
secLevelForBounty = -1
sentryTargetSwitchDelay = 40000
shipHidingCombatDelay = 120000
shipHidingDelay = 60000
shipHidingPvpCombatDelay = 900000
simulationTimeStep = 1000
skillEventCharCreation = 33
skillEventClonePenalty = 34
skillEventGMGive = 39
skillEventTaskMaster = 35
skillEventTrainingCancelled = 38
skillEventTrainingComplete = 37
skillEventTrainingStarted = 36
skillEventQueueTrainingCompleted = 53
skillEventSkillInjected = 56
skillPointMultiplier = 250
solarsystemTimeout = 86400
starbaseSecurityLimit = 800
terminalExplosionDelay = 30
visibleSubSystems = 5
voteCEO = 0
voteGeneral = 4
voteItemLockdown = 5
voteItemUnlock = 6
voteKickMember = 3
voteShares = 2
voteWar = 1
warRelationshipAtWar = 3
warRelationshipAtWarCanFight = 4
warRelationshipUnknown = 0
warRelationshipYourAlliance = 2
warRelationshipYourCorp = 1
warpJitterRadius = 2500
scanProbeNumberOfRangeSteps = 8
scanProbeBaseNumberOfProbes = 4
solarSystemPolaris = 30000380

leaderboardShipTypeAll = 0
leaderboardShipTypeTopFrigate=1
leaderboardShipTypeTopDestroyer=2
leaderboardShipTypeTopCruiser=3
leaderboardShipTypeTopBattlecruiser=4
leaderboardShipTypeTopBattleship=5

leaderboardPeopleBuddies=1
leaderboardPeopleCorpMembers=2
leaderboardPeopleAllianceMembers=3
leaderboardPeoplePlayersInSim=4

securityClassZeroSec = 0
securityClassLowSec = 1
securityClassHighSec = 2

contestionStateNone = 0
contestionStateContested = 1
contestionStateVulnerable = 2
contestionStateCaptured = 3

aggressionTime = 15

reloadTimer = 10000

certificateGradeBasic = 1
certificateGradeStandard = 2
certificateGradeImproved = 3
certificateGradeAdvanced = 4
certificateGradeElite = 5

medalMinNameLength        = 3
medalMaxNameLength        = 100
medalMaxDescriptionLength = 1000

respecTimeInterval = 365 * DAY
respecMinimumAttributeValue = 5
respecMaximumAttributeValue = 15
respecTotalRespecPoints = 39

probeStateInactive    = 0
probeStateIdle        = 1
probeStateMoving      = 2
probeStateWarping     = 3
probeStateScanning    = 4
probeStateReturning   = 5

probeResultPerfect = 1.0
probeResultInformative = 0.75
probeResultGood = 0.25
probeResultUnusable = 0.001

# scanner group types
probeScanGroupScrap           = 1
probeScanGroupSignatures      = 4
probeScanGroupShips           = 8
probeScanGroupStructures      = 16
probeScanGroupDronesAndProbes = 32
probeScanGroupCelestials      = 64
probeScanGroupAnomalies       = 128

probeScanGroups = {}
probeScanGroups[probeScanGroupScrap] = set([
    groupBiomass,
    groupCargoContainer,
    groupWreck,
    groupSecureCargoContainer,
    groupAuditLogSecureContainer,
])

probeScanGroups[probeScanGroupSignatures] = set([groupCosmicSignature])

probeScanGroups[probeScanGroupAnomalies] = set([groupCosmicAnomaly])

probeScanGroups[probeScanGroupShips] = set([
    groupAssaultShip,
    groupBattlecruiser,
    groupBattleship,
    groupBlackOps,
    groupCapitalIndustrialShip,
    groupCapsule,
    groupCarrier,
    groupCombatReconShip,
    groupCommandShip,
    groupCovertOps,
    groupCruiser,
    groupDestroyer,
    groupDreadnought,
    groupElectronicAttackShips,
    groupEliteBattleship,
    groupExhumer,
    groupForceReconShip,
    groupFreighter,
    groupFrigate,
    groupHeavyAssaultShip,
    groupHeavyInterdictors,
    groupIndustrial,
    groupIndustrialCommandShip,
    groupInterceptor,
    groupInterdictor,
    groupJumpFreighter,
    groupLogistics,
    groupMarauders,
    groupMiningBarge,
    groupSupercarrier,
    groupRookieship,
    groupShuttle,
    groupStealthBomber,
    groupTitan,
    groupTransportShip,
    groupStrategicCruiser,
])

probeScanGroups[probeScanGroupStructures] = set([
    groupConstructionPlatform,
    groupStationUpgradePlatform,
    groupStationImprovementPlatform,
    groupMobileWarpDisruptor,
    groupAssemblyArray,
    groupControlTower,
    groupCorporateHangarArray,
    groupElectronicWarfareBattery,
    groupEnergyNeutralizingBattery,
    groupForceFieldArray,
    groupJumpPortalArray,
    groupLogisticsArray,
    groupMobileHybridSentry,
    groupMobileLaboratory,
    groupMobileLaserSentry,
    groupMobileMissileSentry,
    groupMobilePowerCore,
    groupMobileProjectileSentry,
    groupMobileReactor,
    groupMobileShieldGenerator,
    groupMobileStorage,
    groupMoonMining,
    groupRefiningArray,
    groupScannerArray,
    groupSensorDampeningBattery,
    groupShieldHardeningArray,
    groupShipMaintenanceArray,
    groupSilo,
    groupStasisWebificationBattery,
    groupStealthEmitterArray,
    groupTrackingArray,
    groupWarpScramblingBattery,
    groupCynosuralSystemJammer,
    groupCynosuralGeneratorArray,
])

probeScanGroups[probeScanGroupDronesAndProbes] = set([
    groupCapDrainDrone,
    groupCombatDrone,
    groupElectronicWarfareDrone,
    groupFighterDrone,
    groupLogisticDrone,
    groupMiningDrone,
    groupProximityDrone,
    groupRepairDrone,
    groupStasisWebifyingDrone,
    groupUnanchoringDrone,
    groupWarpScramblingDrone,
    groupScannerProbe,
    groupSurveyProbe,
    groupWarpDisruptionProbe,
])

probeScanGroups[probeScanGroupCelestials] = set([
    groupAsteroidBelt,
    groupForceField,
    groupMoon,
    groupPlanet,
    groupStargate,
    groupSun,
    groupStation,
])


mapWormholeRegionMin = 11000000
mapWormholeRegionMax = 11999999
mapWormholeConstellationMin = 21000000
mapWormholeConstellationMax = 21999999
mapWormholeSystemMin = 31000000
mapWormholeSystemMax = 31999999

skillQueueTime = 864000000000L
skillQueueMaxSkills = 50

agentMissionOffered = "offered"
agentMissionOfferAccepted = "offer_accepted"
agentMissionOfferDeclined = "offer_declined"
agentMissionOfferExpired = "offer_expired"
agentMissionOfferRemoved = "offer_removed"
agentMissionAccepted = "accepted"
agentMissionDeclined = "declined"
agentMissionCompleted = "completed"
agentMissionQuit = "quit"
agentMissionFailed = "failed"
agentMissionResearchUpdatePPD = "research_update_ppd"
agentMissionResearchStarted = "research_started"
agentMissionProlonged = "prolong"
agentMissionReset = "reset"
agentMissionModified = "modified"

agentMissionStateAllocated = 0
agentMissionStateOffered = 1
agentMissionStateAccepted = 2

rookieAgentList = [
	3018681, 3018821, 3018822, 3018823,
	3018824, 3018680, 3018817, 3018818,
	3018819, 3018820, 3018682, 3018809,
	3018810, 3018811, 3018812, 3018678,
	3018837, 3018838, 3018839, 3018840,
	3018679, 3018841, 3018842, 3018843,
	3018844, 3018677, 3018845, 3018846,
	3018847, 3018848, 3018676, 3018825,
	3018826, 3018827, 3018828, 3018675,
	3018805, 3018806, 3018807, 3018808,
	3018672, 3018801, 3018802, 3018803,
	3018804, 3018684, 3018829, 3018830,
	3018831, 3018832, 3018685, 3018813,
	3018814, 3018815, 3018816, 3018683,
	3018833, 3018834, 3018835, 3018836,
]

petitionPropertyAgentMissionReq = 2
petitionPropertyAgentMissionNoReq = 3
petitionPropertyAgents = 4
petitionPropertyShipID = 5
petitionPropertyStarbaseLocation = 6
petitionPropertyCharacter = 7
petitionPropertyUserCharacters = 8
petitionPropertyWebAddress = 9
petitionPropertyCorporations = 10
petitionPropertyChrAgent = 11
petitionPropertyOS = 12
petitionPropertyChrEpicArc = 13

tutorialPagesActionOpenCareerFunnel = 1

marketCategoryBluePrints = 2
marketCategoryShips = 4
marketCategoryShipEquipment = 9
marketCategoryAmmunitionAndCharges = 11
marketCategoryTradeGoods = 19
marketCategoryImplantesAndBoosters = 24
marketCategorySkills = 150
marketCategoryDrones = 157
marketCategoryManufactureAndResearch = 475
marketCategoryStarBaseStructures = 477
marketCategoryShipModifications = 955

maxCharFittings = 20
maxCorpFittings = 50

dungeonCompletionDestroyLCS = 0
dungeonCompletionDestroyGuards = 1
dungeonCompletionDestroyLCSandGuards = 2

turretModuleGroups = [
 groupEnergyWeapon,
 groupGasCloudHarvester,
 groupHybridWeapon,
 groupMiningLaser,
 groupProjectileWeapon,
 groupStripMiner,
 groupFrequencyMiningLaser,
 groupTractorBeam,
 groupSalvager
]

previewCategories = [
 categoryDrone,
 categoryShip,
 categoryStructure,
 categoryStation,
 categorySovereigntyStructure,
 categoryApparel
]

previewGroups = [
 groupStargate,
 groupFreightContainer,
 groupSecureCargoContainer,
 groupCargoContainer,
 groupAuditLogSecureContainer
] + turretModuleGroups


dgmGroupableGroupIDs = set([
 groupEnergyWeapon,
 groupProjectileWeapon,
 groupHybridWeapon,
 groupMissileLauncher,
 groupMissileLauncherAssault,
 groupMissileLauncherCitadel,
 groupMissileLauncherCruise,
 groupMissileLauncherDefender,
 groupMissileLauncherHeavy,
 groupMissileLauncherHeavyAssault,
 groupMissileLauncherRocket,
 groupMissileLauncherSiege,
 groupMissileLauncherStandard
])

singletonBlueprintOriginal = 1
singletonBlueprintCopy = 2



cacheEspCorporations = 1
cacheEspAlliances = 2
cacheEspSolarSystems = 3
cacheSolarSystemObjects = 4
cacheCargoContainers = 5
cachePriceHistory = 6
cacheTutorialVersions = 7
cacheSolarSystemOffices = 8

cacheEosNpcToNpcStandings = 109998
cacheAutAffiliates = 109997
cacheAutCdkeyTypes = 109996
cacheTutCategories = 200006
cacheTutCriterias = 200003
cacheTutTutorials = 200001
cacheTutActions = 200009
cacheDungeonArchetypes = 300001
cacheDungeonDungeons = 300005
cacheDungeonEntityGroupTypes = 300004
cacheDungeonEventMessageTypes = 300017
cacheDungeonEventTypes = 300015
cacheDungeonSpawnpoints = 300012
cacheDungeonTriggerTypes = 300013
cacheInvCategories = 600001
cacheInvContrabandTypes = 600008
cacheInvGroups = 600002
cacheInvTypes = 600004
cacheInvTypeMaterials = 600005
cacheInvTypeReactions = 600010
cacheInvWreckUsage = 600009
cacheInvMetaGroups = 600006
cacheInvMetaTypes = 600007
cacheDogmaAttributes = 800004
cacheDogmaEffects = 800005
cacheDogmaExpressionCategories = 800001
cacheDogmaExpressions = 800003
cacheDogmaOperands = 800002
cacheDogmaTypeAttributes = 800006
cacheDogmaTypeEffects = 800007
cacheDogmaUnits = 800009
cacheEveMessages = 1000001
cacheInvBlueprintTypes = 1200001
cacheMapRegions = 1409999
cacheMapConstellations = 1409998
cacheMapSolarSystems = 1409997
cacheMapSolarSystemLoadRatios = 1409996
cacheLocationWormholeClasses = 1409994
cacheMapPlanets = 1409993
cacheMapSolarSystemJumpIDs = 1409992
cacheMapTypeBalls = 1400001
cacheMapCelestialDescriptions = 1400008
cacheMapNebulas = 1400016
cacheMapLocationWormholeClasses = 1400002
cacheMapRegionsTable = 1400009
cacheMapConstellationsTable = 1400010
cacheMapSolarSystemsTable = 1400011
cacheNpcCommandLocations = 1600009
cacheNpcCommands = 1600005
cacheNpcDirectorCommandParameters = 1600007
cacheNpcDirectorCommands = 1600006
cacheNpcLootTableFrequencies = 1600004
cacheNpcCommandParameters = 1600008
cacheNpcTypeGroupingClassSettings = 1600016
cacheNpcTypeGroupingClasses = 1600015
cacheNpcTypeGroupingTypes = 1600017
cacheNpcTypeGroupings = 1600014
cacheNpcTypeLoots = 1600001
cacheRamSkillInfo = 1809999
cacheRamActivities = 1800003
cacheRamAssemblyLineTypes = 1800006
cacheRamAssemblyLineTypesCategory = 1800004
cacheRamAssemblyLineTypesGroup = 1800005
cacheRamCompletedStatuses = 1800007
cacheRamInstallationTypes = 1800002
cacheRamTypeRequirements = 1800001
cacheReverseEngineeringTableTypes = 1800009
cacheReverseEngineeringTables = 1800008
cacheShipInsurancePrices = 2000007
cacheShipTypes = 2000001
cacheStaOperations = 2209999
cacheStaServices = 2209998
cacheStaOperationServices = 2209997
cacheStaSIDAssemblyLineQuantity = 2209996
cacheStaSIDAssemblyLineType = 2209995
cacheStaSIDAssemblyLineTypeQuantity = 2209994
cacheStaSIDOfficeSlots = 2209993
cacheStaSIDReprocessingEfficiency = 2209992
cacheStaSIDServiceMask = 2209991
cacheStaStationImprovementTypes = 2209990
cacheStaStationUpgradeTypes = 2209989
cacheStaStations = 2209988
cacheStaStationsStatic = 2209987
cacheMktOrderStates = 2409999
cacheMktNpcMarketData = 2400001
cacheCrpRoles = 2809999
cacheCrpActivities = 2809998
cacheCrpNpcDivisions = 2809997
cacheCrpCorporations = 2809996
cacheCrpNpcMembers = 2809994
cacheCrpPlayerCorporationIDs = 2809993
cacheCrpTickerNamesStatic = 2809992
cacheNpcSupplyDemand = 2800001
cacheCrpRegistryGroups = 2800002
cacheCrpRegistryTypes = 2800003
cacheCrpNpcCorporations = 2800006
cacheAgentAgents = 3009999
cacheAgentCorporationActivities = 3009998
cacheAgentCorporations = 3009997
cacheAgentEpicMissionMessages = 3009996
cacheAgentEpicMissionsBranching = 3009995
cacheAgentEpicMissionsNonEnd = 3009994
cacheAgtContentAgentInteractionMissions = 3009992
cacheAgtContentFlowControl = 3009991
cacheAgtContentTalkToAgentMissions = 3009990
cacheAgtPrices = 3009989
cacheAgtResearchStartupData = 3009988
cacheAgtContentTemplates = 3000001
cacheAgentMissionsKill = 3000006
cacheAgtStorylineMissions = 3000008
cacheAgtContentCourierMissions = 3000003
cacheAgtContentExchangeOffers = 3000005
cacheAgentEpicArcConnections = 3000013
cacheAgentEpicArcMissions = 3000015
cacheAgentEpicArcs = 3000012
cacheAgtContentMissionExtraStandings = 3000020
cacheAgtContentMissionTutorials = 3000018
cacheAgtContentMissionLocationFilters = 3000021
cacheAgtOfferDetails = 3000004
cacheAgtOfferTableContents = 3000010
cacheChrSchools = 3209997
cacheChrRaces = 3200001
cacheChrBloodlines = 3200002
cacheChrAncestries = 3200003
cacheChrCareers = 3200004
cacheChrSpecialities = 3200005
cacheChrBloodlineNames = 3200010
cacheChrAttributes = 3200014
cacheChrFactions = 3200015
cacheChrDefaultOverviews = 3200011
cacheChrDefaultOverviewGroups = 3200012
cacheChrNpcCharacters = 3200016
cacheUserEspTagTypes = 4309999
cacheFacWarCombatZoneSystems = 4500006
cacheFacWarCombatZones = 4500005
cacheActBillTypes = 6400004
cachePetCategories = 8109999
cachePetQueues = 8109998
cachePetCategoriesVisible = 8109997
cacheGMQueueOrder = 8109996
cacheCertificates = 5100001
cacheCertificateRelationships = 5100004
cachePlanetSchematics = 7300004
cachePlanetSchematicsTypeMap = 7300005
cachePlanetSchematicsPinMap = 7300003
cacheBattleStatuses = 100509999
cacheBattleResults = 100509998
cacheBattleServerStatuses = 100509997
cacheBattleMachines = 100509996
cacheBattleClusters = 100509995
cacheMapDistrictCelestials = 100309999
cacheMapDistricts = 100300014
cacheMapBattlefields = 100300015
cacheMapLevels = 100300020
cacheMapOutposts = 100300022
cacheMapLandmarks = 100300023

cacheSystemIntervals = 2000109999
cacheSystemSettings = 2000100001
cacheSystemSchemas = 2000100003
cacheSystemTables = 2000100004
cacheSystemProcedures = 2000100006
cacheSystemEventTypes = 2000100013
cacheUserEventTypes = 2000209999
cacheUserColumns = 2000209998
cacheUserRegions = 2000209997
cacheUserTimeZones = 2000209996
cacheUserCountries = 2000209995
cacheUserTypes = 2000209994
cacheUserStatuses = 2000209993
cacheUserRoles = 2000209992
cacheUserConnectTypes = 2000209991
cacheUserOperatingSystems = 2000209990
cacheStaticSettings = 2000309999
cacheStaticBranches = 2000300001
cacheStaticReleases = 2000300006
cacheStaticIntegrateOptions = 2000300008
cacheMlsLanguages = 2000409999
cacheMlsTranslationStatuses = 2000409998
cacheMlsTextGroupTypes = 2000409997
cacheMlsTextStatuses = 2000409996
cacheMlsTaskStatuses = 2000409995
cacheClusterServices = 2000909999
cacheClusterMachines = 2000909998
cacheClusterProxies = 2000909997
cacheClientBrowserSiteFlags = 2003009999
cacheAccountingKeys = 2001100001
cacheAccountingEntryTypes = 2001100002
cacheInventoryCategories = 2001300001
cacheInventoryGroups = 2001300002
cacheInventoryTypes = 2001300003
cacheInventoryFlags = 2001300012
cacheEventGroups = 2001500002
cacheEventTypes = 2001500003
cacheWorldSpaces = 2001700035
cacheWorldSpaceDistricts = 2001700001
cacheResGraphics = 2001800001
cacheResSounds = 2001800002
cacheResDirectories = 2001800003
cacheResIcons = 2001800004
cacheResDetailMeshes = 2001800005
cacheActionTreeSteps = 2001900002
cacheActionTreeProcs = 2001900003
cacheEntityIngredients = 2002200001
cacheEntityIngredientInitialValues = 2002200002
cacheEntitySpawns = 2002200006
cacheEntityRecipes = 2002200009
cacheEntitySpawnGroups = 2002200010
cacheEntitySpawnGroupLinks = 2002200011
cacheActionObjects = 2002400001
cacheActionStations = 2002400002
cacheActionStationActions = 2002400003
cacheActionObjectStations = 2002400004
cacheActionObjectExits = 2002400005
cacheTreeNodes = 2002500001
cacheTreeLinks = 2002500002
cacheTreeProperties = 2002500005
cachePerceptionSenses = 2002600001
cachePerceptionStimTypes = 2002600002
cachePerceptionSubjects = 2002600004
cachePerceptionTargets = 2002600005
cachePerceptionBehaviorSenses = 2002600010
cachePerceptionBehaviorFilters = 2002600011
cachePerceptionBehaviorDecays = 2002600012
cachePaperdollModifierLocations = 2001600002
cachePaperdollResources = 2001600003
cachePaperdollSculptingLocations = 2001600004
cachePaperdollColors = 2001600005
cachePaperdollColorNames = 2001600006
cachePaperdollColorRestrictions = 2001600007
cacheEncounterEncounters = 2003100001
cacheEncounterCoordinates = 2003100002
cacheEncounterCoordinateSets = 2003100003
cacheStaticUsers = 2000000001
cacheUsersDataset = 2000000002
cacheCharactersDataset = 2000000003
cacheNameNames = 2000000004





cacheEspCorporations = 1
cacheEspAlliances = 2
cacheEspSolarSystems = 3
cacheSolarSystemObjects = 4
cacheCargoContainers = 5
cachePriceHistory = 6
cacheTutorialVersions = 7
cacheSolarSystemOffices = 8


cacheMapLocationScenes = 1400006  # deprecated, here for backwards compatibility


DBTYPE_BOOL = 11
DBTYPE_I2 = 2
DBTYPE_I4 = 3
DBTYPE_R8 = 5
DBTYPE_WSTR = 130

_NAMED_CELESTIALS = {
40002444: 'Uplingur IV (Ndoria)',
40002445: 'Uplingur IV (Ndoria) - Moon 1',
40002446: 'Uplingur IV (Ndoria) - Moon 2',
40002447: 'Uplingur IV (Ndoria) - Moon 3',
40002448: 'Uplingur IV (Ndoria) - Moon 4',
40002449: 'Uplingur IV (Ndoria) - Moon 5',
40002450: 'Uplingur IV (Ndoria) - Moon 6',
40002451: 'Uplingur IV (Ndoria) - Moon 7',
40002452: 'Uplingur IV (Ndoria) - Moon 8',
40002453: 'Uplingur IV (Ndoria) - Moon 9',
40002454: 'Uplingur IV (Ndoria) - Moon 10',
40002455: 'Uplingur IV (Ndoria) - Moon 11',
40002456: 'Uplingur IV (Ndoria) - Asteroid Belt 1',
40002457: 'Uplingur IV (Ndoria) - Moon 12',
40002458: 'Uplingur IV (Ndoria) - Moon 13',
40002459: 'Uplingur IV (Ndoria) - Moon 14',
40002460: 'Uplingur IV (Ndoria) - Moon 15',
40002461: 'Uplingur IV (Ndoria) - Moon 16',
40002462: 'Uplingur IV (Ndoria) - Asteroid Belt 2',
40002463: 'Uplingur IV (Ndoria) - Asteroid Belt 3',
40002464: 'Uplingur IV (Ndoria) - Asteroid Belt 4',
40002465: 'Uplingur IV (Ndoria) - Moon 17',
40002466: 'Uplingur IV (Ndoria) - Moon 18',
40002467: 'Uplingur IV (Ndoria) - Asteroid Belt 5',
40002468: 'Uplingur IV (Ndoria) - Asteroid Belt 6',
40002469: 'Uplingur IV (Ndoria) - Asteroid Belt 7',
40002470: 'Uplingur IV (Ndoria) - Moon 19',
40002471: 'Uplingur IV (Ndoria) - Asteroid Belt 8',
40002472: 'Uplingur IV (Ndoria) - Asteroid Belt 9',
40002473: 'Uplingur IV (Ndoria) - Moon 20',
40002474: 'Uplingur IV (Ndoria) - Asteroid Belt 10',
40002475: 'Uplingur IV (Ndoria) - Moon 21',
40002476: 'Uplingur IV (Ndoria) - Moon 22',
40009253: 'New Caldari I (Matigu)',
40009254: 'New Caldari I (Matigu) - Moon 1',
40009255: 'New Caldari II (Matias)',
40009256: 'New Caldari II (Matias) - Asteroid Belt 1',
40009257: 'New Caldari III (Orieku)',
40009258: 'New Caldari III (Orieku) - Asteroid Belt 1',
40009259: 'New Caldari III (Orieku) - Moon 1',
40009260: 'New Caldari Prime',
40009261: 'New Caldari Prime - Moon 1',
40009262: 'New Caldari Prime - Moon 2',
40009263: 'New Caldari Prime - Moon 3',
40009264: 'New Caldari V (Oniteseru)',
40009265: 'New Caldari V (Oniteseru) - Moon 1',
40009266: 'New Caldari V (Oniteseru) - Moon 2',
40009267: 'New Caldari V (Oniteseru) - Moon 3',
40092199: 'Taisy VIII (Kyonoke Pit)',
40092200: 'Taisy VIII (Kyonoke Pit) - Moon 1',
40139384: 'Amarr I (Mikew)',
40139385: 'Amarr II (Mikeb)',
40139386: 'Amarr II (Mikeb) - Asteroid Belt 1',
40139387: 'Amarr Prime',
40139388: 'Amarr Prime - Asteroid Belt 1',
40139389: 'Amarr IV (Tamiroth)',
40139390: 'Amarr IV (Tamiroth) - Asteroid Belt 1',
40139391: 'Amarr V (Sek)',
40139392: 'Amarr V (Sek) - Asteroid Belt 1',
40139393: 'Amarr V (Sek) - Moon 1',
40139394: 'Amarr VI (Zorast)',
40139395: 'Amarr VI (Zorast) - Asteroid Belt 1',
40139396: 'Amarr VI (Zorast) - Moon 1',
40139397: 'Amarr VI (Zorast) - Moon 2',
40139398: 'Amarr VII (Nemantizor)',
40139399: 'Amarr VII (Nemantizor) - Asteroid Belt 1',
40139400: 'Amarr VII (Nemantizor) - Moon 1',
40139401: 'Amarr VII (Nemantizor) - Moon 2',
40139402: 'Amarr VII (Nemantizor) - Moon 3',
40139403: 'Amarr VIII (Oris)',
40139404: 'Amarr VIII (Oris) - Asteroid Belt 1',
40139405: 'Amarr VIII (Oris) - Moon 1',
40139406: 'Amarr VIII (Oris) - Moon 2',
40139407: 'Amarr VIII (Oris) - Asteroid Belt 2',
40139408: 'Amarr VIII (Oris) - Moon 3',
40139409: 'Amarr VIII (Oris) - Moon 4',
40139410: 'Amarr VIII (Oris) - Moon 5',
40139411: 'Amarr VIII (Oris) - Moon 6',
40139412: 'Amarr VIII (Oris) - Moon 7',
40139413: 'Amarr VIII (Oris) - Moon 8',
40139414: 'Amarr VIII (Oris) - Moon 9',
40139415: 'Amarr VIII (Oris) - Moon 10',
40139416: 'Amarr VIII (Oris) - Asteroid Belt 3',
40139417: 'Amarr VIII (Oris) - Moon 11',
40139418: 'Amarr VIII (Oris) - Asteroid Belt 4',
40139419: 'Amarr VIII (Oris) - Moon 12',
40139420: 'Amarr VIII (Oris) - Asteroid Belt 5',
40139421: 'Amarr VIII (Oris) - Moon 13',
40139422: 'Amarr VIII (Oris) - Asteroid Belt 6',
40139423: 'Amarr VIII (Oris) - Asteroid Belt 7',
40139424: 'Amarr IX (Derdainys)',
40139425: 'Amarr IX (Derdainys) - Asteroid Belt 1',
40139426: 'Amarr IX (Derdainys) - Asteroid Belt 2',
40139427: 'Amarr IX (Derdainys) - Moon 1',
40139428: 'Amarr IX (Derdainys) - Moon 2',
40139429: 'Amarr IX (Derdainys) - Moon 3',
40139430: 'Amarr IX (Derdainys) - Moon 4',
40139431: 'Amarr IX (Derdainys) - Moon 5',
40139432: 'Amarr IX (Derdainys) - Moon 6',
40139433: 'Amarr IX (Derdainys) - Moon 7',
40139434: 'Amarr IX (Derdainys) - Moon 8',
40139435: 'Amarr IX (Derdainys) - Moon 9',
40139436: 'Amarr IX (Derdainys) - Moon 10',
40139437: 'Amarr IX (Derdainys) - Moon 11',
40139438: 'Amarr IX (Derdainys) - Moon 12',
40139439: 'Amarr IX (Derdainys) - Moon 13',
40142176: 'Ardishapur Prime III (Radonis)',
40161832: 'Pator I (Istinn)',
40161833: 'Pator II (Belogor)',
40161834: 'Pator III (Huggar)',
40161835: 'Pator III (Huggar) - Moon 1',
40161836: 'Pator III (Huggar) - Moon 2',
40161837: 'Pator IV (Matar)',
40161838: 'Pator IV (Matar) - Asteroid Belt 1',
40161839: 'Pator IV (Matar) - Moon 1',
40161840: 'Pator V (Vakir)',
40161841: 'Pator V (Vakir) - Asteroid Belt 1',
40161842: 'Pator V (Vakir) - Moon 1',
40161843: 'Pator VI (Varkal)',
40161844: 'Pator VI (Varkal) - Asteroid Belt 1',
40161845: 'Pator VII (Kulheim)',
40161846: 'Pator VII (Kulheim) - Asteroid Belt 1',
40161847: 'Pator VII (Kulheim) - Moon 1',
40161848: 'Pator VIII (Orinn)',
40161849: 'Pator VIII (Orinn) - Moon 1',
40161850: 'Pator IX (Syld)',
40236011: 'Shintaht IV (Konrakas)',
40236012: 'Shintaht IV (Konrakas) - Moon 1',
40236013: 'Shintaht IV (Konrakas) - Moon 2',
40314535: 'Luminaire I (Noya)',
40314536: 'Luminaire I (Noya) - Asteroid Belt 1',
40314537: 'Luminaire II (Corufeu)',
40314538: 'Luminaire II (Corufeu) - Asteroid Belt 1',
40314539: 'Luminaire II (Corufeu) - Moon 1',
40314540: 'Luminaire III (Astrin)',
40314541: 'Luminaire III (Astrin) - Asteroid Belt 1',
40314542: 'Luminaire III (Astrin) - Moon 1',
40314543: 'Luminaire IV (Malloc)',
40314544: 'Luminaire IV (Malloc) - Asteroid Belt 1',
40314545: 'Luminaire IV (Malloc) - Moon 1',
40314546: 'Luminaire V (Tanet)',
40314547: 'Luminaire V (Tanet) - Moon 1',
40314548: 'Luminaire V (Tanet) - Moon 2',
40314549: 'Luminaire VI (Gallente Prime)',
40314550: 'Luminaire VI (Gallente Prime) - Moon 1',
40314551: 'Luminaire VI (Gallente Prime) - Asteroid Belt 1',
40314552: 'Luminaire VI (Gallente Prime) - Moon 2',
40314553: 'Luminaire VI (Gallente Prime) - Moon 3',
40314554: 'Luminaire VI (Gallente Prime) - Moon 4',
40314555: 'Luminaire VI (Gallente Prime) - Moon 5',
40314556: 'Luminaire VI (Gallente Prime) - Moon 6',
40314557: 'Luminaire VI (Gallente Prime) - Asteroid Belt 2',
40314558: 'Luminaire VI (Gallente Prime) - Moon 7',
40314559: 'Luminaire VI (Gallente Prime) - Asteroid Belt 3',
40314560: 'Luminaire VI (Gallente Prime) - Moon 8',
40314561: 'Luminaire VI (Gallente Prime) - Moon 9',
40314562: 'Luminaire VI (Gallente Prime) - Moon 10',
40314563: 'Luminaire VI (Gallente Prime) - Moon 11',
40314564: 'Luminaire VI (Gallente Prime) - Moon 12',
40314565: 'Luminaire VI (Gallente Prime) - Moon 13',
40314566: 'Luminaire VI (Gallente Prime) - Moon 14',
40314567: 'Luminaire VI (Gallente Prime) - Asteroid Belt 4',
40314568: 'Luminaire VI (Gallente Prime) - Asteroid Belt 5',
40314569: 'Luminaire VI (Gallente Prime) - Moon 15',
40314570: 'Luminaire VI (Gallente Prime) - Asteroid Belt 6',
40314571: 'Luminaire VI (Gallente Prime) - Moon 16',
40314572: 'Luminaire VI (Gallente Prime) - Moon 17',
40314573: 'Luminaire VII (Caldari Prime)',
40314574: 'Luminaire VII (Caldari Prime) - Moon 1',
40314575: 'Luminaire VII (Caldari Prime) - Moon 2',
40314576: 'Luminaire VII (Caldari Prime) - Moon 3',
40314577: 'Luminaire VII (Caldari Prime) - Moon 4',
40314578: 'Luminaire VII (Caldari Prime) - Asteroid Belt 1',
40314579: 'Luminaire VII (Caldari Prime) - Moon 5',
40314580: 'Luminaire VII (Caldari Prime) - Moon 6',
40314581: 'Luminaire VII (Caldari Prime) - Moon 7',
40314582: 'Luminaire VII (Caldari Prime) - Moon 8',
40314583: 'Luminaire VII (Caldari Prime) - Moon 9',
40314584: 'Luminaire VII (Caldari Prime) - Moon 10',
40314585: 'Luminaire VII (Caldari Prime) - Moon 11',
40314586: 'Luminaire VII (Caldari Prime) - Asteroid Belt 2',
40314587: 'Luminaire VII (Caldari Prime) - Moon 12',
40314588: 'Luminaire VII (Caldari Prime) - Moon 13',
40314589: 'Luminaire VII (Caldari Prime) - Moon 14',
40314590: 'Luminaire VII (Caldari Prime) - Moon 15',
40314591: 'Luminaire VII (Caldari Prime) - Asteroid Belt 3',
40314592: 'Luminaire VIII (Ortange)',
40314593: 'Luminaire VIII (Ortange) - Asteroid Belt 1',
40314594: 'Luminaire VIII (Ortange) - Asteroid Belt 2',
40314595: 'Luminaire VIII (Ortange) - Moon 1',
40319254: 'Kor-Azor Prime IV (Eclipticum)',
40319255: 'Kor-Azor Prime IV (Eclipticum) - Moon Griklaeum',
40319256: 'Kor-Azor Prime IV (Eclipticum) - Moon Black Viperia',
40319257: 'Kor-Azor Prime IV (Eclipticum) - Moon Kileakum',
40467692: 'Eyjafjallajokull II',
}


########NEW FILE########
__FILENAME__ = embedfs
"""EmbedFS manager (handles .stuff files).

Copyright (c) 2003-2012 Jamie "Entity" van den Berge <jamie@hlekkir.com>

This code is free software; you can redistribute it and/or modify
it under the terms of the BSD license (see the file LICENSE.txt
included with the distribution).
"""


import struct
import glob
import os

from ._blue import _VirtualFile


_idString = "EmbedFs 1.0"

class EmbedFS(object):
	"""Manages a single EmbedFS file."""

	def __init__(self, fileName):
		self.offsets = []
		self.lengths = []
		self.files = files = {}
		self.filenames = []

		addo = self.offsets.append
		addl = self.lengths.append
		addf = self.filenames.append

		# open file and check
		f = open(fileName, "rb")

		self.name = fileName
		f.seek(-len(_idString)-1, 2)
		if _idString != f.read(len(_idString)):
			raise RuntimeError("Invalid id string in EmbedFS file")
		f.seek(0)
		self.numFiles, = struct.unpack("<L", f.read(4))

		# read directory
		for i in range(self.numFiles):
			length, nameLength = struct.unpack("<2L", f.read(8))
			name = f.read(nameLength+1).replace('\\', '/').rstrip("\0")
			addf(name)
			addl(length)
			files[name.lower()] = i

		# calculate offsets
		offset = f.tell()
		for length in self.lengths:
			addo(offset)
			offset += length

		# keep the stuff file open to prevent changes to it (patches?)
		# invalidating the offsets/lengths.
		self._filehandle = f


	def open(self, name):
		f = self._open(name)
		if f:
			return f
		raise KeyError("File not found")

	def __getitem__(self, ix):
		return self.filenames[ix]

	def __contains__(self, this):
		return this.lower() in self.files

	def __len__(self):
		return len(self.filenames)

	def _open(self, name, mode="rb", buffering=-1):
		# internal open.
		ix = self.files.get(name.lower(), -1)
		if ix == -1:
			return None

		return _VirtualFile(self.name, mode, buffering, self.offsets[ix], self.lengths[ix])


class EmbedFSDirectory(object):
	"""Manages folder with EFS files"""
	def __init__(self, path="."):
		self.stuff = []
		for stuffFile in glob.glob(os.path.join(path, "*.stuff")):
			self.stuff.append(EmbedFS(stuffFile))

	def __getitem__(self, ix):
		return self.stuff[ix]

	def open(self, name):
		for efs in self.stuff:
			f = efs._open(name)
			if f:
				return f
		raise IndexError("File not found: '%s'" % name)



########NEW FILE########
__FILENAME__ = eveCfg
"""Bulk Static Data container classes

Copyright (c) 2003-2014 Jamie "Entity" van den Berge <jamie@hlekkir.com>

This code is free software; you can redistribute it and/or modify
it under the terms of the BSD license (see the file LICENSE.txt
included with the distribution).

Parts of code inspired by or based on EVE Online, with permission from CCP.
"""

from reverence.carbon.common.script.sys.row import Row

_get = Row.__getattr__

def _localized(row, attr, messageID):
	_cfg = (row.cfg or cfg)
	return _cfg._localization.GetByMessageID(messageID)

def _localized_important(row, attr, messageID):
	_cfg = (row.cfg or cfg)
	return _cfg._localization.GetImportantByMessageID(messageID)


_OWNER_AURA_IDENTIFIER = -1
_OWNER_SYSTEM_IDENTIFIER = -2
_OWNER_NAME_OVERRIDES = {
	_OWNER_AURA_IDENTIFIER: 'UI/Agents/AuraAgentName',
	_OWNER_SYSTEM_IDENTIFIER: 'UI/Chat/ChatEngine/EveSystem'
}


def Singleton(dbrow):
	# used as property getter by certain cache objects
	if dbrow.quantity < 0:
		return 1
	else:
		if 30000000 <= dbrow.locationID < 40000000:
			return 1
	return 0


def StackSize(dbrow):
	# used as property getter by certain cache objects
	qty = dbrow.quantity
	return qty if qty >= 0 else 1


def RamActivityVirtualColumn(dbrow):
# this does not work because the dbrow does not have a cfg attrib and we don't have a global one.
# the RamDetail class will handle it.
#   return cfg.ramaltypes.Get(dbrow.assemblyLineTypeID).activityID
	return None




class Billtype(Row):
	__guid__ = 'cfg.Billtype'

	def __getattr__(self, name):
		value = _get(self, name)
#		if name == 'billTypeName':
#			value = Tr(value, 'dbo.actBillTypes.billTypeName', self.billTypeID)
		return value

	def __str__(self):
		return 'Billtype ID: %d' % self.billTypeID


class InvType(Row):
	__guid__ = "sys.InvType"

	def __getattr__(self, attr):
		if attr in ("name", "typeName"):
			return _localized_important(self, "typeName", self.typeNameID)
		if attr == 'categoryID':
			return (self.cfg or cfg).invgroups.Get(self.groupID).categoryID
		if attr == "description":
			return _localized(self, "description", self.descriptionID)

		# check overrides
		if attr in ('graphicID', 'soundID', 'iconID', 'radius'):
			try:
				fsd = (self.cfg or cfg).fsdTypeOverrides
				return getattr(fsd.Get(self.typeID), attr)
			except (AttributeError, KeyError):
				pass

		return _get(self, attr)

	def Group(self):
		return (self.cfg or cfg).invgroups.Get(self.groupID)

	def GetRawName(self, languageID):
		return (self.cfg or cfg)._localization.GetByMessageID(self.typeNameID, languageID)

	def Icon(self):
		if self.typeID >= const.minDustTypeID:
			return (self.cfg or cfg).fsdDustIcons.get(self.typeID, None)
		elif self.iconID is not None:
			return (self.cfg or cfg).icons.GetIfExists(self.iconID)
		return

	def IconFile(self):
		return getattr((self.cfg or cfg).icons.Get(self.iconID), "iconFile", "")

	def Graphic(self):
		gid = self.graphicID
		if gid is not None:
			return (self.cfg or cfg).graphics.Get(gid)
		return None

	def GraphicFile(self):
		return getattr((self.cfg or cfg).Graphic(), "graphicFile", "")

	def Sound(self):
		sid = self.soundID
		if sid is not None:
			print (self.cfg or cfg).sounds.keys()
			return (self.cfg or cfg).sounds.GetIfExists(sid)

	@property
	def averagePrice(self):
		try:
			return (self.cfg or cfg)._averageMarketPrice[self.typeID].averagePrice
		except KeyError:
			return None

	# ---- custom additions ----

	@property
	def packagedvolume(self):
		return (self.cfg or cfg).GetTypeVolume(self.typeID)

	def GetRequiredSkills(self):
		return (self.cfg or cfg).GetRequiredSkills(self.typeID)

	def GetTypeAttrDict(self):
		return (self.cfg or cfg).GetTypeAttrDict(self.typeID)

	def GetTypeAttribute(self, attributeID, defaultValue=None):
		return (self.cfg or cfg).GetTypeAttribute(self.typeID, attributeID, defaultValue)

	def GetTypeAttribute2(self, attributeID):
		return (self.cfg or cfg).GetTypeAttribute2(self.typeID, attributeID)


class InvGroup(Row):
	__guid__ = "sys.InvGroup"

	def Category(self):
		return (self.cfg or cfg).invcategories.Get(self.categoryID)

	def __getattr__(self, attr):
		if attr in ("name", "groupName", "description"):
			return _localized(self, "groupName", self.groupNameID)
		if attr == "id":
			return _get(self, "groupID")
		return _get(self, attr)


class InvCategory(Row):
	__guid__ = "sys.InvCategory"

	def __getattr__(self, attr):
		if attr in ("name", "categoryName", "description"):
			return _localized(self, "categoryName", self.categoryNameID)
		if attr == "id":
			return _get(self, "categoryID")
		return _get(self, attr)

	def IsHardware(self):
		return self.categoryID == const.categoryModule


class InvMetaGroup(Row):
	__guid__ = "cfg.InvMetaGroup"

	def __getattr__(self, name):
		if name == "_metaGroupName":
			return _get(self, "metaGroupName")

		if name == "name":
			name = "metaGroupName"

		return _get(self, name)


class DgmAttribute(Row):
	__guid__ = "cfg.DgmAttribute"

	def __getattr__(self, name):
		if name == 'displayName':
			return _localized(self, "displayName", self.displayNameID)
		return _get(self, name)


class DgmEffect(Row):
	__guid__ = "cfg.DgmEffect"

	def __getattr__(self, name):
		if name == "displayName":
			return _localized(self, "displayName", self.displayNameID)
		if name == "description":
			return _localized(self, "description", self.descriptionID)
		return _get(self, name)


class DgmUnit(Row):
	__guid__ = 'cfg.DgmUnit'

	def __getattr__(self, name):
		if name == 'displayName':
			return _localized(self, "displayName", self.displayNameID)
		if name == 'description':
			return _localized(self, "description", self.descriptionID)
		return _get(self, name)


class EveOwners(Row):
	__guid__ = "cfg.EveOwners"

	def __getattr__(self, name):
		if name in ("name", "description", "ownerName"):
			return _get(self, "ownerName")
		if name == "groupID":
			return self.cfg.invtypes.Get(self.typeID).groupID
		return _get(self, name)

	def GetRawName(self, languageID):
		if self.ownerNameID:
			if self.ownerNameID in _OWNER_NAME_OVERRIDES:
				return (self.cfg or cfg)._localization.GetByLabel(_OWNER_NAME_OVERRIDES[self.ownerNameID], languageID)
			return (self.cfg or cfg)._localization.GetByMessageID(self.ownerNameID, languageID)
		return self.name

	def __str__(self):
		return 'EveOwner ID: %d, "%s"' % (self.ownerID, self.ownerName)

	def Type(self):
		return self.cfg.invtypes.Get(self.typeID)

	def Group(self):
		return self.cfg.invgroups.Get(self.groupID)


class EveLocations(Row):
	__guid__ = "dbrow.Location"

	def __getattr__(self, name):
		if name in ("name", "description", "locationName"):
			locationName = _get(self, 'locationName')
			_cfg = (self.cfg or cfg)
			if (not locationName) and self.locationNameID is not None:
				if isinstance(self.locationNameID, (int, long)):
					locationName = _cfg._localization.GetByMessageID(self.locationNameID)
				elif isinstance(self.locationNameID, tuple):
					locationName = _cfg._localization.GetByLabel(self.locationNameID[0], **self.locationNameID[1])
				setattr(self, 'locationName', locationName)
			return locationName

		return _get(self, name)

	def __str__(self):
		return 'EveLocation ID: %d, "%s"' % (self.locationID, self.locationName)

	def GetRawName(self, languageID):
		if self.locationNameID:
			return (self.cfg or cfg)._localization.GetByMessageID(self.locationNameID, languageID)
#		if self.locationID in cfg.rawCelestialCache:
#			(lbl, kwargs,) = cfg.rawCelestialCache[self.locationID]
#			return self.cfg._localization.GetByLabel(lbl, languageID, **kwargs)
		return self.locationName

#	def Station(self):
#		return self.cfg.GetSvc("stationSvc").GetStation(self.id)


class RamCompletedStatus(Row):
	__guid__ = 'cfg.RamCompletedStatus'

	def __getattr__(self, name):
		if name in ("name", "completedStatusName"):
			return _localized(self, "completedStatusName", self.completedStatusTextID)
		if name == "description":
			return _localized(self, "description", self.descriptionID)
		return _get(self, name)

	def __str__(self):
		try:
			return 'RamCompletedStatus ID: %d, "%s"' % (self.completedStatus, self.completedStatusName)
		except:
			sys.exc_clear()
			return "RamCompletedStatus containing crappy data"


class RamActivity(Row):
	__guid__ = 'cfg.RamActivity'

	def __getattr__(self, name):
		if name in ("name", "activityName"):
			return _localized(self, "activityName", self.activityNameID)
		if name == "description":
			return _localized(self, "description", self.descriptionID)
		return _get(self, name)

	def __str__(self):
		try:
			return 'RamActivity ID: %d, "%s"' % (self.activityID, self.activityName)
		except:
			sys.exc_clear()
			return "RamActivity containing crappy data"


class RamDetail(Row):
	__guid__ = 'cfg.RamDetail'

	def __getattr__(self, name):
   		if name == "activityID":
			return self.cfg.ramaltypes.Get(self.assemblyLineTypeID).activityID
   		return _get(self, name)


class MapCelestialDescription(Row):
	__guid__ = 'cfg.MapCelestialDescription'

	def __getattr__(self, name):
		if name == "description":
			return _localized(self, "description", self.descriptionID)
		return _get(self, name)

	def __str__(self):
		return "MapCelestialDescriptions ID: %d" % (self.itemID)


class CrpTickerNames(Row):
	__guid__ = 'cfg.CrpTickerNames'

	def __getattr__(self, name):
		if name in ("name", "description"):
			return _get(self, "tickerName")
		return _get(self, name)

	def __str__(self):
		return "CorpTicker ID: %d, \"%s\"" % (self.corporationID, self.tickerName)


class AllShortNames(Row):
	__guid__ = 'cfg.AllShortNames'

	def __getattr__(self, name):
		if name in ("name", "description"):
			return _get(self, "shortName")
		return _get(self, name)

	def __str__(self):
		return "AllianceShortName ID: %d, \"%s\"" % (self.allianceID, self.shortName)


class Certificate(Row):
	__guid__ = 'cfg.Schematic'

	def __getattr__(self, name):
		if name == "description":
			return _localized(self, "description", self.descriptionID)
		return _get(self, name)

	def __str__(self):
		return "Certificate ID: %d" % (self.certificateID)


class Schematic(Row):
	__guid__ = 'cfg.Schematic'

	def __getattr__(self, name):
		if name == "schematicName":
			return _localized(self, "schematicName", self.schematicNameID)
		return _get(self, name)

	def __str__(self):
		return 'Schematic: %s (%d)' % (self.schematicName, self.schematicID)

	def __cmp__(self, other):
		if type(other) is int:
			return int.__cmp__(self.schematicID, other)
		else:
			return Row.__cmp__(self, other)

__all__ = ["Singleton", "StackSize", "RamActivityVirtualColumn", "_OWNER_AURA_IDENTIFIER", "_OWNER_SYSTEM_IDENTIFIER", "_OWNER_NAME_OVERRIDES"]
__all__.extend([name for name, cls in locals().items() if getattr(cls, "__guid__", False)])


########NEW FILE########
__FILENAME__ = rowset
"""Container classes for DBRow/DBRowset

Copyright (c) 2003-2013 Jamie "Entity" van den Berge <jamie@hlekkir.com>

This code is free software; you can redistribute it and/or modify
it under the terms of the BSD license (see the file LICENSE.txt
included with the distribution).

Part of this code is inspired by or based on EVE Online.
Used with permission from CCP.
"""

from reverence import _blue as blue

from reverence.carbon.common.script.sys.row import Row

def RowsInit(rows, columns):
	header = None
	if type(rows) is types.TupleType:
		header = rows[0]
		rows = rows[1]

	if rows:
		first = rows[0]
		if type(first) != blue.DBRow:
			raise AttributeError('Not DBRow. Initialization requires a non-empty list of DBRows')
		header = first.__header__
	elif header:
		if type(header) != blue.DBRowDescriptor:
			raise AttributeError('expected (DBRowDesciptor, [])')
	if header:
		columns = header.Keys()
	return rows, columns, header


class RowDict(dict):
	__guid__ = 'dbutil.RowDict'
	__passbyvalue__ = 1
	slots = ["columns", "header", "key"]

	def __init__(self, rowList, key, columns = None):
		dict.__init__(self)

		rows, self.columns, self.header = RowsInit(rowList, columns)

		if key not in self.columns:
			raise AttributeError('Indexing key not found in columns')

		self.key = key
		for row in rows:
			self[row[key]] = row


	def ReIndex(self, key):
		if key not in self.columns:
			raise AttributeError('Indexing key not found in columns')

		vals = self.values()

		self.clear()

		self.key = key
		for row in vals:
			self[row[key]] = row

	def Add(self, row):

		if type(row) != blue.DBRow:
			raise AttributeError('Not DBRow')

		if row.__keys__ != self.columns:
			raise ValueError('Incompatible rows')

		if self.header is None:
			self.header = row.__header__

		self[row[self.key]] = row


class RowList(list):
	__guid__ = 'dbutil.RowList'
	__passbyvalue__ = 1
	slots = ["header", "columns"]

	def __init__(self, rowList, columns = None):
		list.__init__(self)
		rows, self.columns, self.header = RowsInit(rowList, columns)
		self[:] = rows

	def append(self, row):
		if not isinstance(row, blue.DBRow):
			raise ValueError('Not DBRow: %s' % row )

		if row.__header__ is not self.header:
			raise ValueError('Incompatible headers')

		if self.header is None:
			self.header = row.__header__

		list.append(self, row)


class Rowset:
	__passbyvalue__ = 1
	__guid__ = "util.Rowset"

	cfg = None

	def __init__(self, header=None, lines=None, rowclass=Row, cfgInstance=None):
		self.header = header or []
		self.lines = lines or []
		self.RowClass = rowclass
		self.cfg = cfgInstance

	def __nonzero__(self):
		return True

	def __getitem__(self, index):
		if type(index) is slice:
			return Rowset(self.header, self.lines[index], self.RowClass, cfgInstance=self.cfg)
		return self.RowClass(self.header, self.lines[index], cfgInstance=self.cfg)

	def __len__(self):
		return len(self.lines)

	def sort(self, *args, **kw):
		self.lines.sort(*args, **kw)

	def GroupedBy(self, column):
		"""Returns new FilterRowset grouped on specified column."""
		return FilterRowset(self.header, self.lines, idName=column, RowClass=self.RowClass, cfgInstance=self.cfg)

	def IndexedBy(self, column):
		"""Returns new IndexRowset indexed on specified column."""
		return IndexRowset(self.header, self.lines, key=column, RowClass=self.RowClass, cfgInstance=self.cfg)

	def SortBy(self, column, reverse=False):
		"""Sorts the rowset in place."""
		ix = self.header.index(column)
		self.sort(key=lambda e: e[ix], reverse=reverse)

	def SortedBy(self, column, reverse=False):
		"""Returns a sorted shallow copy of the rowset."""
		rs = Rowset(header=self.header, lines=self.lines[:], rowclass=self.RowClass, cfgInstance=self.cfg)
		rs.SortBy(column, reverse)
		return rs

	def Select(self, *columns, **options):
		if len(columns) == 1:
			i = self.header.index(columns[0])
			if options.get("line", False):
				for line in self.lines:
					yield (line, line[i])
			else:
				for line in self.lines:
					yield line[i]
		else:
			i = map(self.header.index, columns)
			if options.get("line", False):
				for line in self.lines:
					yield line, [line[x] for x in i]
			else:
				for line in self.lines:
					yield [line[x] for x in i]


class IndexRowset(Rowset):
	__guid__ = "util.IndexRowset"

	def __init__(self, header=None, lines=None, key=None, RowClass=Row, dict=None, cfgInstance=None, fetcher=None):
		if not key:
			raise ValueError, "Crap key"

		Rowset.__init__(self, header, lines, RowClass, cfgInstance=cfgInstance)

		ki = header.index(key)
		if dict is None:
			self.items = d = {}
			self.key = ki
			for line in self.lines:
				d[line[ki]] = line
		else:
			self.items = dict

		self._fetcher = fetcher

	def has_key(self, key):
		return key in self.items

	def __contains__(self, key):
		return key in self.items

	def values(self):
		return self  #Rowset(self.header,self.items.values(),self.RowClass)

	def itervalues(self):
		return self

	def Get(self, *args):
		row = self.items.get(*args)
		if row:
			return self.RowClass(self.header, row, cfgInstance=self.cfg)
		return None

	def GetIfExists(self, *args):
		row = self.items.get(args[0], None)
		if row is None:
			return None
		return self.RowClass(self.header, row, cfgInstance=self.cfg)

	def SortedBy(self, column, reverse=False):
		"""Returns a sorted shallow copy of the rowset."""
		rs = self.IndexedBy(column)
		rs.SortBy(column, reverse)
		return rs

	def Prime(self, keys):
		wanted = set(keys) - set(self.items)
		lines = self._fetcher(wanted)
		self.lines.extend(lines)
		d = self.items
		ki = self.key
		for line in lines:
			d[line[ki]] = line

	get = Get  # compatibility


class IndexedRowLists(dict):
	__guid__ = 'util.IndexedRowLists'
	__passbyvalue__ = 1
	__slots__ = ("header",)

	def __init__(self, rows=[], keys=None):
		if rows:
			self.header = rows[0].__header__.Keys()
		self.InsertMany(keys, rows)

	def Insert(self, keys, row):
		self.InsertMany(keys, [row])

	def InsertMany(self, keys, rows):
		rkeys = keys[1:]
		k = keys[0]
		_get = dict.get
		if rkeys:
			for row in rows:
				key = row[k]
				grp = _get(self, key)
				if grp is None:
					grp = self[key] = self.__class__()
				grp.InsertMany(rkeys, [row])
		else:
			for row in rows:
				key = row[k]
				grp = _get(self, key)
				if grp is None:
					self[key] = [row]
				else:
					grp.append(row)


	def __getitem__(self, key):
		return dict.get(self, key) or []


class IndexedRows(IndexedRowLists):
	__guid__ = 'util.IndexedRows'


class FilterRowset:
	__guid__ = "util.FilterRowset"
	__passbyvalue__ = 1

	RowClass = Row

	cfg = None

	def __init__(self,header=None, li=None, idName=None, RowClass=Row, idName2=None, dict=None, cfgInstance=None):
		self.cfg = cfgInstance

		self.RowClass = RowClass

		if dict is not None:
			items = dict
		elif header is not None:
			items = {}
			_get = items.get
			idfield = header.index(idName)
			if idName2:
				idfield2 = header.index(idName2)
				for i in li:
					id = i[idfield]
					_items = _get(id)
					if _items is None:
						items[id] = {i[idfield2]:i}
					else:
						_items[i[idfield2]] = i
			else:
				for i in li:
					id = i[idfield]
					_items = _get(id)
					if _items is None:
						items[id] = [i]
					else:
						_items.append(i)
		else:
			items = {}

		self.items = items
		self.header = header
		self.idName = idName
		self.idName2 = idName2

	def Clone(self):
		return FilterRowset(copy.copy(self.header), None, self.idName, self.RowClass, self.idName2, dict=copy.deepcopy(self.items))

	def __contains__(self, key):
		return key in self.items

	def has_key(self, key):
		return key in self.items

	def get(self, key, val):
		try:
			return self[key]
		except:
			sys.exc_clear()
			return val

	def keys(self):
		return self.items.keys()

	def iterkeys(self):
		return self.items.iterkeys()

	def __getitem__(self, i):
		if self.idName2:
			return IndexRowset(self.header, None, self.idName2, self.RowClass, self.items.get(i, {}), cfgInstance=self.cfg)
		return Rowset(self.header, self.items.get(i, []), self.RowClass, cfgInstance=self.cfg)

	def __len__(self):
		return len(self.items)

	def Sort(self, colname):
		ret = Rowset(self.header, self.items.values(), self.RowClass)
		return ret.Sort(colname)

	def __iter__(self):
		return (self[key] for key in self.iterkeys())



__all__ = [
	"RowDict",
	"RowList",
	"Rowset",
	"IndexedRowLists",
	"IndexRowset",
	"FilterRowset",
]


########NEW FILE########
__FILENAME__ = locationWrapper
class SolarSystemWrapper(int):
	__guid__ = 'universe.SolarSystemWrapper'

########NEW FILE########
__FILENAME__ = exceptions
import types

from reverence.carbon.common.script.net.GPSExceptions import *

class UserError(StandardError):
	__guid__ = 'exceptions.UserError'

	def __init__(self, msg=None, *args):
		if type(msg) == types.InstanceType and msg.__class__ == UserError:
			self.msg = msg.msg
			self.dict = msg.dict
			self.args = (self.msg, self.dict)
			return

		if type(msg) not in [types.StringType, types.NoneType]:
			raise RuntimeError("Invalid argument, msg must be a string", msg)

		self.msg = msg or "<NO MESSAGE>"
		if len(args) and type(args[0]) == dict:
			self.dict = args[0]
			self.args = (self.msg or self.dict)
		else:
			self.dict = None
			self.args = (self.msg,) + args


	def __str__(self):
		try:
			msg = cfg.GetMessage(self.msg, self.dict)
			return "[%s] %s - %s" % (msg.type, msg.title, msg.text)
		except:
			return "User error, msg=%s, dict=%s" % (self.msg, self.dict)

########NEW FILE########
__FILENAME__ = fsd
"""
FileStaticData decoder stuff

Copyright (c) 2003-2014 Jamie "Entity" van den Berge <jamie@hlekkir.com

This code is free software; you can redistribute it and/or modify
it under the terms of the BSD license (see the file LICENSE.txt
included with the distribution).

Part of this code is inspired by or based on EVE Online.
Used with permission from CCP.
"""
#
# So apparently CCP added yet another static data format, using YAML for the
# schema and binary blobs for data.
#
# Also, this stuff should totally be implemented in C.
#

import struct
import collections
import os
import cPickle
import itertools

try:
	import yaml
except ImportError:
	raise RuntimeError("Reverence requires the PyYAML library")

import pyFSD

from reverence import _pyFSD
_uint32 = _pyFSD._uint32_from  # used for decoding in the various containers
_make_offsets_table = _pyFSD._make_offsets_table
_unpack_from = struct.unpack_from

FLOAT_PRECISION_DEFAULT = 'single'


#-----------------------------------------------------------------------------
# Schema Loaders
#-----------------------------------------------------------------------------

class _SchemaLoader(yaml.SafeLoader):
	pass

_SchemaLoader.add_constructor(u'tag:yaml.org,2002:map',
	lambda loader, node: collections.OrderedDict(map(loader.construct_object, kv) for kv in node.value))

def LoadSchema(f):
	return yaml.load(f, Loader=_SchemaLoader)

def LoadEmbeddedSchema(f):
	pos = f.tell()
	size = _uint32(f.read(4))
	try:
		# there's a possibility this blind unpickle goes spectacularly wrong.
		return cPickle.load(f), size
	except cPickle.UnpicklingError:
		# it is not a pickle, restore position in file.
		f.seek(pos)
		raise RuntimeError("LoadEmbeddedSchema called on file without embedded schema")
	finally:
		# update filehandle state after cPickle.load() (see virtualfile.c)
		f.tell()


#-----------------------------------------------------------------------------
# Schema Optimizer
#-----------------------------------------------------------------------------

_typeSizes = {
 'int'     : struct.calcsize("I"),
 'typeID'  : struct.calcsize("I"),
 'localizationID' : struct.calcsize("I"),
 'float'   : struct.calcsize("f"),
 'single'  : struct.calcsize("f"),
 'vector2' : struct.calcsize("ff"),
 'vector3' : struct.calcsize("fff"),
 'vector4' : struct.calcsize("ffff"),
 'double'  : struct.calcsize("d"),
 'vector2d': struct.calcsize("dd"),
 'vector3d': struct.calcsize("ddd"),
 'vector4d': struct.calcsize("dddd"),
 'bool'    : struct.calcsize("B"),
}


def IsFixedSize(schema):
	t = schema['type']
	if t in _typeSizes:
		return True
	if t == 'object':
		attributes = schema['attributes']
		for attr in attributes:
			sa = attributes[attr]
			if sa.get('usage', "Client") == "Client":
				if sa.get('isOptional', False) or not IsFixedSize(sa):
					return False
		return True
	return False


class _SchemaOptimizer:
	@classmethod
	def optimize(cls, schema):
		schemaType = schema['type']
		optimizefunc = getattr(cls, "_"+schemaType, None)
		if optimizefunc:
			newSchema = optimizefunc(schema)
			newSchema['type'] = schemaType
		else:
			size = _typeSizes.get(schemaType)
			if size:
				newSchema = {'type': schemaType, 'size': size}
			else:
				newSchema = {'type': schemaType}

		if 'isOptional' not in newSchema:
			newSchema['isOptional'] = schema.get('isOptional', False)

		if 'default' in schema:
			newSchema['default'] = schema['default']

		return newSchema

	@staticmethod
	def _generic(schema):

		return {}

	@staticmethod
	def _dict(schema):
		newSchema = {
			'keyTypes': _OptimizeSchema(schema['keyTypes']),
			'valueTypes': _OptimizeSchema(schema['valueTypes']),
			'buildIndex': schema.get('buildIndex', False),
		}

		if 'multiIndex' in schema:
#			newSchema['multiIndex'] = schema['multiIndex']
#			newSchema['subIndexOffsetLookup'] = _OptimizeSchema(_subIndexOffsetLookupSchema)
#			SetNestedIndexIdInformationToRootSchema(newSchema)
			raise RuntimeError("fsd.py is not equipped to handle unoptimized multi-index schemas.")

		return newSchema

	@staticmethod
	def _list(schema):
		newSchema = {'itemTypes': _OptimizeSchema(schema['itemTypes'])}
		if 'size' in newSchema['itemTypes']:
			newSchema['fixedItemSize'] = newSchema['itemTypes']['size']
		if 'length' in schema:
			newSchema['length'] = schema['length']
		return newSchema

	@staticmethod
	def _object(schema):
		newSchema = {'attributes': collections.OrderedDict()}
		_constantAttributeOffsets = newSchema['constantAttributeOffsets'] = {}
		_attributesWithVariableOffsets = newSchema['attributesWithVariableOffsets'] = []
		_optionalValueLookups = newSchema['optionalValueLookups'] = {}

		offset = 0
		attr_bit = 1
		fixedsize = True

		attributes = schema["attributes"]
		for attr in attributes:
			sa = attributes[attr]
			if not sa.get('usage', "Client") == "Client":
				continue
			oschema = _OptimizeSchema(sa)
			newSchema['attributes'][attr] = oschema
			if sa.get('isOptional', False):
				fixedsize = False
				_optionalValueLookups[attr] = attr_bit
				_attributesWithVariableOffsets.append(attr)
				attr_bit <<= 1
			elif not IsFixedSize(sa):
				fixedsize = False
				_attributesWithVariableOffsets.append(attr)
			else:
				_constantAttributeOffsets[attr] = offset
				offset += oschema['size']

		if fixedsize:
			newSchema['endOfFixedSizeData'] = newSchema['size'] = offset
		else:
			newSchema['endOfFixedSizeData'] = offset

		return newSchema

	@staticmethod
	def _enum(schema):
		return {
			'readEnumValue': schema.get('readEnumValue', False),
			'values': schema['values'],
		}

	@staticmethod
	def _int(schema):
		newSchema = {'size': struct.calcsize("i")}
		if 'min' in schema:
			newSchema['min'] = schema['min']
		if 'exclusiveMin' in schema:
			newSchema['exclusiveMin'] = schema['exclusiveMin']
		return newSchema

	@staticmethod
	def _vector(schema, size=None):
		newSchema = {}
		if 'aliases' in schema:
			newSchema['aliases'] = schema['aliases']
		if 'precision' in schema:
			prec = newSchema['precision'] = schema['precision']
		else:
			prec = FLOAT_PRECISION_DEFAULT
		newSchema['size'] = _typeSizes[prec] * size
		return newSchema

	@staticmethod
	def _vector2(schema):
		return _SchemaOptimizer._vector(schema, 2)

	@staticmethod
	def _vector3(schema):
		return _SchemaOptimizer._vector(schema, 3)

	@staticmethod
	def _vector4(schema):
		return _SchemaOptimizer._vector(schema, 4)

	@staticmethod
	def _union(schema):
		newSchema = {'optionTypes': []}
		for unionType in schema['optionTypes']:
			newSchema['optionTypes'].append(_OptimizeSchema(unionType))
		return newSchema

	@staticmethod
	def _float(schema):
		newSchema = {}
		if 'precision' in schema:
			prec = newSchema['precision'] = schema['precision']
		else:
			prec = FLOAT_PRECISION_DEFAULT
		newSchema['size'] = _typeSizes[prec]
		return newSchema

_OptimizeSchema = _SchemaOptimizer.optimize


#-----------------------------------------------------------------------------
# Deserialization stuff
#-----------------------------------------------------------------------------

_vectorUnpackers = {}
_vectorUnpackers["vector4"] = _vector4 = struct.Struct("ffff").unpack_from
_vectorUnpackers["vector3"] = _vector3 = struct.Struct("fff").unpack_from
_vectorUnpackers["vector2"] = _vector2 = struct.Struct("ff").unpack_from
_vectorUnpackers["vector4d"] = _vector4d = struct.Struct("dddd").unpack_from
_vectorUnpackers["vector3d"] = _vector3d = struct.Struct("ddd").unpack_from
_vectorUnpackers["vector2d"] = _vector2d = struct.Struct("dd").unpack_from

class _FixedSizeList(object):

	def __init__(self, data, offset, itemSchema, knownLength = None):
		self.data = data
		self.itemSchema = itemSchema

		if knownLength is None:
			self.count = _uint32(data, offset)
			self.offset = offset + 4
		else:
			self.count = knownLength
			self.offset = offset
		self.itemSize = itemSchema['size']

	def __iter__(self):
		d = self.data; s = self.itemSchema; loader = self.itemSchema['loader']
		return (loader(d, offset, s) for offset in xrange(self.offset, self.offset + self.count*self.itemSize, self.itemSize))

	def __len__(self):
		return self.count

	def __getitem__(self, idx):
		if type(idx) not in (int, long):
			raise TypeError('Invalid key type')
		if idx < 0 or idx >= self.count:
			raise IndexError('Invalid item index %i for list of length %i' % (idx, self.count))
		return self.itemSchema['loader'](self.data, self.offset + self.itemSize * idx, self.itemSchema)

	def __repr__(self):
		return "<FixedSizeList(values:%s,size:%d)>" % (self.itemSchema['type'], self.count)


class _VariableSizedList(object):

	def __init__(self, data, offset, itemSchema, knownLength = None):
		self.data = data
		self.itemSchema = itemSchema

		if knownLength is None:
			self.count = _uint32(data, offset)
			self.start = offset
			self.offset = offset + 4
		else:
			self.count = knownLength
			self.start = self.offset = offset

	def __iter__(self):
		d = self.data; s = self.itemSchema; loader = self.itemSchema['loader']
		start = self.start; offset = self.offset
		return (loader(d, start + _uint32(d, offset + idx*4), s) for idx in xrange(self.count))

	def __len__(self):
		return self.count

	def __getitem__(self, idx):
		if type(idx) not in (int, long):
			raise TypeError('Invalid key type')
		if idx < 0 or idx >= self.count:
			raise IndexError('Invalid item index %i for list of length %i' % (idx, self.count))
		return self.itemSchema['loader'](self.data, self.start + _uint32(self.data, self.offset + idx*4), self.itemSchema)

	def __repr__(self):
		return "<VariableSizedList(values:%s,size:%d)>" % (self.itemSchema['type'], self.count)

def FSD_List(data, offset, schema):
	return (_FixedSizeList if 'fixedItemSize' in schema else _VariableSizedList)(data, offset, schema['itemTypes'], schema.get('length'))


class FSD_NamedVector(object):
	def __init__(self, data, offset, schema):
		self.data = data
		self.offset = offset
		self.schema = schema
		self.data = schema['unpacker'](data, offset)
		self._getKeyIndex = self.schema['aliases'].get

	def __getitem__(self, key):
		return self.data[self._getKeyIndex(key, key)]

	def __getattr__(self, name):
		try:
			return self.data[self._getKeyIndex(name)]
		except (KeyError, IndexError) as e:
			raise AttributeError(str(e))

	def __repr__(self):
		return "FSD_NamedVector(" + ",".join(map("%s:%s".__mod__, zip(self.schema['aliases'], self.data))) + ")"


def Load_Enum(data, offset, schema):
	dataValue = schema['unpacker'](data, offset)[0]
	if schema['readEnumValue']:
		return dataValue
	for k, v in schema['values'].iteritems():
		if v == dataValue:
			return k


class _DictFooter(object):
	def __init__(self, data, offset, schema):
		self.footer = FSD_List(data, offset, schema)

	def Get(self, key):
		minIndex = 0
		maxIndex = len(self.footer) - 1
		while 1:
			if maxIndex < minIndex:
				return None
			meanIndex = (minIndex + maxIndex) / 2
			item = self.footer[meanIndex]
			if item.key < key:
				minIndex = meanIndex + 1
			elif item.key > key:
				maxIndex = meanIndex - 1
			else:
				return (item.offset, getattr(item, 'size', 0))

	def _iterspecial(self, mode):
		if mode == 4: return ((item.key, item.offset) for item in self.footer)
		if mode == 3: return (item.offset for item in self.footer)
		raise RuntimeError("iterspecial mode has to be 3 or 4")

	def keys(self)      : return [item.key for item in self.footer]
	def iterkeys(self)  : return (item.key for item in self.footer)
	def itervalues(self): return ((item.offset, getattr(item, 'size', 0)) for item in self.footer)
	def iteritems(self) : return ((item.key, (item.offset, getattr(item, 'size', 0))) for item in self.footer)
	def __len__(self)   : return len(self.footer)


class FSD_Dict(object):

	def __init__(self, data, offset, schema):
		self.data = data
		self.offset = offset + 4
		endOfFooter = offset + _uint32(data, offset)
		footerOffset = endOfFooter - _uint32(data, endOfFooter)
		self.schema = schema
		if schema['keyTypes']['type'] in 'int':
			hassize = ('size' in schema['keyFooter']['itemTypes']['attributes']) if ('keyFooter' in schema) else True
			self.footer = pyFSD.FsdUnsignedIntegerKeyMap()
			self.footer.Initialize(data, footerOffset, hassize, True)
		else:
			self.footer = _DictFooter(data, footerOffset, schema['keyFooter'])
		self.valueSchema = schema['valueTypes']
		self.loader = self.valueSchema['loader']
		self.header = schema['header']
		self.index = {}

	def __GetItem__(self, offset):
		return self.valueSchema["loader"](self.data, self.offset + offset, self.valueSchema)

	def __len__(self):
		return len(self.footer)

	def __contains__(self, item):
		try:
			return self._Search(item) is not None
		except TypeError:
			return False

	def _Search(self, key):
		v = self.index.get(key, self)  # abusing self
		if v is self:
			v = self.index[key] = self.footer.Get(key)
		return v

	def __getitem__(self, key):
		v = self._Search(key)
		if v is None:
			raise KeyError('key (%s) not found' % (str(key)))
		return self.loader(self.data, self.offset + v[0], self.valueSchema)

	def get(self, key, default=None):
		v = self._Search(key)
		if v is None:
			return default
		return self.loader(self.data, self.offset + v[0], self.valueSchema)

	def keys(self):
		return list(self.footer.iterkeys())

	def iteritems(self):
		d = self.data; a = self.offset; s = self.valueSchema; loader = s["loader"]
		return ((key, loader(d, a+offset, s)) for key, offset in self.footer._iterspecial(4))

	def itervalues(self):
		d = self.data; a = self.offset; s = self.valueSchema; loader = s["loader"]
		return (loader(d, a+offset, s) for offset in self.footer._iterspecial(3))

	def iterkeys(self):
		return self.footer.iterkeys()

	def __repr__(self):
		return "<FSD_Dict(keys:%s,values:%s,size:%d)>" % (self.schema['keyTypes']['type'], self.valueSchema['type'], len(self.footer))

	__iter__ = iterkeys

	Get = __getitem__
	GetIfExists = get


class FSD_Index(object):

	def __init__(self, f, cacheSize, schema, offset=0, offsetToFooter=0):
		self.file = f
		self.cacheSize = cacheSize
		self.offset = offset = offset+4 if offset else 0
		self.index = {}
		self.header = schema['header']

		# read the footer blob and put it in an appropriate container
		f.seek(offset)
		self.fileSize = _uint32(f.read(4))

		f.seek(offset + self.fileSize)
		footerSize = self.footerSize = _uint32(f.read(4))

		f.seek(-(4+footerSize), os.SEEK_CUR)
		if schema['keyTypes']['type'] == 'int':
			self.footer = pyFSD.FsdUnsignedIntegerKeyMap()
			self.footer.Initialize(f.read(footerSize))
		else:
			self.footer = _DictFooter(f.read(footerSize), 0, schema['keyFooter'])

		self.cache = collections.OrderedDict()

		s = self.valueSchema = schema['valueTypes']
		self._load = s['loader']
		if (s.get('buildIndex', False)) and (s['type'] == 'dict'):
			self._getitem = self.__GetIndex__ 
		else:
			self._getitem = self.__GetItem__

	def keys(self):
		return list(self.footer.iterkeys())

	def iterkeys(self):
		return self.footer.iterkeys()

	def iteritems(self):
		_get = self._getitem
		return ((key, _get(offset, size)) for key, (offset, size) in self.footer.iteritems())

	def itervalues(self):
		_get = self._getitem
		return (_get(offset, size) for (offset, size) in self.footer.itervalues())

	def _Search(self, key):
		v = self.index.get(key, self)  # abusing self
		if v is self:
			v = self.index[key] = self.footer.Get(key)
		return v

	def __getitem__(self, key):
		v = self.cache.pop(key, self)  # abusing self
		if v is self:
			# item wasnt cached. grab it and do so.
			try:
				itemOffset, itemSize = self._Search(key)
			except TypeError:
				# can be thrown by _Search returning None or being passed wrong type
				raise KeyError('Key (%s) not found' % str(key))

			v = self._getitem(itemOffset, itemSize)

			if len(self.cache) > self.cacheSize:
				self.cache.popitem(last=False)

		self.cache[key] = v
		return v

	def __GetItem__(self, offset, size):
		self.file.seek(self.offset+offset)
		return self._load(self.file.read(size), 0, self.valueSchema)

	def __GetIndex__(self, offset, size):
		return FSD_Index(self.file, self.cacheSize, self.valueSchema, offset=self.offset+offset)

	def __contains__(self, item):
		try:
			return self._Search(item) is not None
		except TypeError:
			return False

	def __len__(self):
		return len(self.footer)

	def get(self, key, default=None):
		try:
			return self.__getitem__(key)
		except (KeyError, IndexError):
			return default

	def __repr__(self):
		return "<FSD_Index(type:%s,size:%s)" % (self.valueSchema['type'], len(self.footer))

	__iter__ = iterkeys

	Get = __getitem__
	GetIfExists = get


class _subindex(object):
	# one index in a multiindex table

	def __init__(self, f, indexedOffsetTable, valueSchema):
		self.file = f
		self.offsetTable = indexedOffsetTable
		self.valueSchema = valueSchema
		self.fsdindex = self.valueSchema.get("buildIndex", False)
		self.loader = self.valueSchema["loader"]

		# aliases for speed
		self._getkey = self.offsetTable.Get
		self._seek = self.file.seek
		self._read = self.file.read

	def __getitem__(self, key):
		offsetAndSize = self._getkey(key)
		if offsetAndSize is None:
			raise KeyError('Key (%s) not found in subindex' % str(key))
		if self.fsdindex:
			return FSD_Index(self.file, 100, self.valueSchema, offset=offsetAndSize[0], offsetToFooter=offsetAndSize[0]+offsetAndSize[1])
		self._seek(offsetAndSize[0])
		return self.loader(self._read(offsetAndSize[1]), 0, self.valueSchema)

	def get(self, key, default=None):
		offsetAndSize = self._getkey(key)
		if offsetAndSize is None:
			return default
		if self.fsdindex:
			return FSD_Index(self.file, 100, self.valueSchema, offset=offsetAndSize[0], offsetToFooter=offsetAndSize[0]+offsetAndSize[1])
		self._seek(offsetAndSize[0])
		return self.loader(self._read(offsetAndSize[1]), 0, self.valueSchema)

	def iterkeys(self)    : return self.offsetTable.iterkeys()
	def itervalues(self)  : return (self[key] for key in self.offsetTable.iterkeys())
	def iteritems(self)   : return ((key, self[key]) for key in self.offsetTable.iterkeys())
	def __len__(self)     : return len(self.offsetTable)
	def __contains__(self): return key in self.offsetTable

	__iter__ = iterkeys

	Get = __getitem__
	GetIfExists = get


_chain = itertools.chain.from_iterable

class _indexgroup(object):
	# a group of subindex instances treated as one index.
	__slots__ = ("indices",)

	def __init__(self, indices):
		self.indices = indices

	def __getitem__(self, key):
		for index in self.indices:
			if key in index:
				return index[key]
		raise KeyError('Key (%s) not found in indexgroup' % str(key))

	def get(self, key, default=None):
		for index in self.indices:
			if key in index:
				return index[key]
		return default

	def iterkeys(self)  : return _chain(self.indices)
	def itervalues(self): return (v for index in self.indices for v in index.itervalues())
	def iteritems(self) : return (kv for index in self.indices for kv in index.iteritems())
	def __len__(self)   : return sum(len(index) for index in self.indices)
	
	def __contains__(self, item):
		for index in self.indices:
			if key in index:
				return True
		return False

	__iter__ = iterkeys

	Get = __getitem__
	GetIfExists = get


class FSD_MultiIndex(FSD_Index):
	# clever multiple indices on the same collection of data

	def __init__(self, f, cacheSize, schema, offset=0, offsetToFooter=0):
		FSD_Index.__init__(self, f, cacheSize, schema, offset, offsetToFooter)

		f.seek(offset + self.fileSize - self.footerSize)
		attributeLookupTableSize = _uint32(f.read(4))

		f.seek(-(4+attributeLookupTableSize), os.SEEK_CUR)
		attributeLookupTable = f.read(attributeLookupTableSize)

		# create the subindices
		subindices = {}
		for index, offsetAndSize in load(attributeLookupTable, 0, schema['subIndexOffsetLookup']).iteritems():
			f.seek(offset + 4 + offsetAndSize.offset)
			offsetTable = pyFSD.FsdUnsignedIntegerKeyMap()
			offsetTable.Initialize(f.read(offsetAndSize.size), 0, True, False, offset+8)
			subindices[index] = _subindex(f, offsetTable, schema['indexableSchemas'][index]['valueTypes'])

		# assign either indexgroup or subindex to relevant attributes.
		for indexName, indices in schema['indexNameToIds'].iteritems():
			index = _indexgroup(map(subindices.__getitem__, indices)) if len(indices)>1 else subindices[indices[0]]
			setattr(self, indexName, index)

		self._indices = schema['indexNameToIds'].keys()

	def __repr__(self):
		indexsummary = map("%s:%d".__mod__, ((name, len(getattr(self, name))) for name in self._indices))
		return "<FSD_MultiIndex(type:%s,size:%d,indices:{%s})>" % (self.valueSchema['type'], len(self.footer), ','.join(indexsummary))


class FSD_Object(object):

	def __init__(self, data, offset, schema):
		self.__data__ = data
		self.__offset__ = offset
		self.attributes = schema['attributes']
		self._get_schema = schema['attributes'].get

		if 'size' in schema:
			# fixed size object. skip all the scary stuff.
			self._get_offset = schema['constantAttributeOffsets'].get
		else:
			# variable sized object. figure out what optional attributes we have.
			if schema['optionalValueLookups']:
				attr_bits = _uint32(data, offset + schema['endOfFixedSizeData'])
				if attr_bits:
					# some attribute bits are set. figure out what attributes are actually there ...
					_oa = schema.get(attr_bits)
					if not _oa:
						lookup = schema['optionalValueLookups'].get
						# filter out optional attributes that are not given
						_oa = schema[attr_bits] = \
							[attr for attr in schema['attributesWithVariableOffsets'] if lookup(attr, -1) & attr_bits]
				else:
					# no attribute bits set, so this set is going to be empty anyway.
					_oa = ()

			else:
				# looks like there's just the required attributes.
				_oa = schema['attributesWithVariableOffsets']

			if _oa:
				_offsets = _make_offsets_table(_oa, data, offset, schema['endOfFixedSizeData'] + 4)
				_offsets.update(schema['constantAttributeOffsets'])
				self._get_offset = _offsets.get
			else:
				self._get_offset = schema['constantAttributeOffsets'].get


	def __getitem__(self, key):
		schema = self._get_schema(key)
		if schema is None:
			raise KeyError("Attribute '%s' is not in the schema for this object." % key)

		off = self._get_offset(key)
		if off is None:
			if 'default' in schema:
				return schema['default']
			raise schema['KeyError']
		return schema['loader'](self.__data__, self.__offset__ + off, schema)

	def __getattr__(self, key):
		schema = self._get_schema(key)
		if schema is None:
			raise AttributeError("Attribute '%s' is not in the schema for this object." % key)

		off = self._get_offset(key)
		if off is None:
			if 'default' in schema:
				return schema['default']
			raise schema['AttributeError']
		return schema['loader'](self.__data__, self.__offset__ + off, schema)


	def __str__(self):
		# detailed representation
		header = self.attributes
		_getoffset = self._get_offset
		stuff = []
		_a = stuff.append
		for attr, schema in header.iteritems():
			offset = _getoffset(attr)
			if offset is None:
				v = schema.get("default", self)
				v = "NULL" if v is self else repr(v)
			else:
				v = repr(schema['loader'](self.__data__, self.__offset__ + offset, schema))
			_a(v)

		return "FSD_Object(" + ','.join(map(u"%s:%s".__mod__, zip(header, stuff))) + ")"

	def __repr__(self):
		# lightweight representation that doesn't decode any information
		return "<FSD_Object(" + ','.join(map(u"%s:%s".__mod__, ((k, v['type']) for k,v in self.attributes.iteritems()) )) + ")>"



_loaders = {
	# scalars
	'int'     : _pyFSD._int32_from,
	'typeID'  : _pyFSD._int32_from,
	'bool'    : _pyFSD._bool_from,
	'float'   : _pyFSD._float_from,
	'double'  : _pyFSD._double_from,
	'string'  : _pyFSD._string_from,
	'resPath' : _pyFSD._string_from,
	'unicode' : lambda data, offset, schema: _string(data, offset).decode('utf-8'),
	'enum'    : Load_Enum,

	'localizationID' : _pyFSD._int32_from,  # rubicon 1.1
	
	# compounds
	'vector4' : lambda data, offset, schema: _vector4(data, offset),
	'vector3' : lambda data, offset, schema: _vector3(data, offset),
	'vector2' : lambda data, offset, schema: _vector2(data, offset),
	'vector4d': lambda data, offset, schema: _vector4d(data, offset),
	'vector3d': lambda data, offset, schema: _vector3d(data, offset),
	'vector2d': lambda data, offset, schema: _vector2d(data, offset),
	'union'   : lambda data, offset, schema: load(data, offset+4, schema['optionTypes'][_uint32(data, offset)]),
	
	# containers
	'list'   : FSD_List,
	'dict'   : FSD_Dict,
	'object' : FSD_Object,
}


def load(data, offset, schema):
	return schema['loader'](data, offset, schema)


#-----------------------------------------------------------------------------
# Exposed stuff
#-----------------------------------------------------------------------------

def OptimizeSchema(schema):
	return _OptimizeSchema(schema['schemas'][schema['runtimeSchema']])


def PrepareSchema(schema):
	# Adds required decoding information to a schema
	# THIS -MUST- BE USED ON EVERY SCHEMA (AFTER OPTIMIZING, IF ANY)

	t = schema.get('type')
	schema['loader'] = _loaders[t]

	if t in _typeSizes:
		schema['size'] = _typeSizes[t]

	if t.startswith("vector"):
		if schema.get('precision') == 'double':
			t = schema['type']+"d"

		# figure out correct loader.
		if schema.get('aliases'):
			schema['loader'] = FSD_NamedVector
			schema['unpacker'] = _vectorUnpackers[t]
		else:
			schema['loader'] = _loaders[t]

	elif t == 'list':
		PrepareSchema(schema['itemTypes'])

	elif t == 'dict':
		PrepareSchema(schema['keyTypes'])
		PrepareSchema(schema['valueTypes'])

		if 'subIndexOffsetLookup' in schema:
			PrepareSchema(schema['subIndexOffsetLookup'])

		if "keyFooter" in schema:
			PrepareSchema(schema['keyFooter'])
		try:
			schema['header'] = schema['valueTypes']['attributes'].keys()
		except KeyError:
			# apparently this info is gone from some fsd dicts in Rubicon
			schema['header'] = ()

	elif t == 'object':
		if "endOfFixedSizeData" not in schema:
			schema["endOfFixedSizeData"] = 0

		for key, attrschema in schema["attributes"].iteritems():
			PrepareSchema(attrschema)
			attrschema['AttributeError'] = AttributeError("Object instance does not have attribute '%s'" % key)
			attrschema['KeyError'] = KeyError("Object instance does not have attribute '%s'" % key)

	elif t == 'binary':
		PrepareSchema(schema["schema"])

	elif t == 'int':
		if schema.get("min", -1) >= 0 or schema.get("exclusiveMin", -2) >= -1:
			schema['loader'] = _uint32

	elif t == 'union':
		for s in newSchema['optionTypes'].itervalues():
			PrepareSchema(s)

	elif t == 'float':
		if schema.get('precision') == 'double':
			schema['loader'] = _loaders['double']

	elif t == 'enum':
		_max = max(schema['values'].values())
		if _max <= 255:
			_type = struct.Struct("B")
		elif _max <= 65536:
			_type = struct.Struct("H")
		else:
			_type = struct.Struct("I")

		schema['unpacker'] = _type.unpack_from
		schema['size'] = _type.size
		if 'readEnumValue' not in schema:
			schema['readEnumValue'] = False


def LoadFromString(dataString, optimizedSchema=None):
	if optimizedSchema is None:
		size = uint32(dataString, 0)
		optimizedSchema = cPickle.loads(dataString[4:size+4])
		PrepareSchema(optimizedSchema)
		return load(dataString, size+4, optimizedSchema)
	else:
		return load(dataString, 0, optimizedSchema)


def LoadIndexFromFile(f, optimizedSchema, cacheItems=None, offset=0):
	if optimizedSchema.get("multiIndex", False):
		return FSD_MultiIndex(f, cacheItems, optimizedSchema, offset=offset)
	return FSD_Index(f, cacheItems, optimizedSchema, offset=offset)




########NEW FILE########
__FILENAME__ = localization
"""
Minimal Cerberus (localization subsystem) implementation.

This code is free software; you can redistribute it and/or modify
it under the terms of the BSD license (see the file LICENSE.txt
included with the distribution).

Part of this code is inspired by or based on EVE Online.
Used with permission from CCP.
"""

# Note: If I had to write about all the stuff that is wrong with the Cerberus
# code in the EVE client, this script file would probably be twice as big.

# Note2: This is not a full featured Cerberus. The primary purpose of this
# minimal version is to provide translations for EVE's static content,
# such as names and descriptions.

import os
import cPickle

import gc

from . import embedfs


class BasePropertyHandler(object):
	__id__ = 10

	def __init__(self, localizationInstance, cfgInstance):
		self.cfg = cfgInstance
		self.localization = localizationInstance

	def default(self, value, languageID, **kwargs):
		return value


class MessageIDPropertyHandler(BasePropertyHandler):
	__id__ = 5

	def default(self, value, languageID, **kwargs):
		return self.localization.GetByMessageID(value, languageID)


class LocationPropertyHandler(BasePropertyHandler):
	__id__ = 3

	def name(self, locationID, languageID, *args, **kwargs):
		return self.cfg.evelocations.Get(locationID).locationName or 'None'

	def rawName(self, locationID, languageID, *args, **kwargs):
		return self.cfg.evelocations.Get(locationID).GetRawName(languageID)


class ItemPropertyHandler(BasePropertyHandler):
	__id__ = 2

	def name(self, itemID, languageID, *args, **kwargs):
		return self.cfg.invtypes.Get(itemID).typeName or 'None'

	def rawName(self, itemID, languageID, *args, **kwargs):
		return self.cfg.invtypes.Get(itemID).GetRawName(languageID)


class NpcOrganizationPropertyHandler(BasePropertyHandler):
	__id__ = 1

	def name(self, npcOrganizationID, languageID, *args, **kwargs):
		#if const.minFaction <= npcOrganizationID <= const.maxFaction or const.minNPCCorporation <= npcOrganizationID <= const.maxNPCCorporation:
		return self.cfg.eveowners.Get(npcOrganizationID).name


	def rawName(self, npcOrganizationID, languageID, *args, **kwargs):
		#if const.minFaction <= npcOrganizationID <= const.maxFaction or const.minNPCCorporation <= npcOrganizationID <= const.maxNPCCorporation:
		return self.cfg.eveowners.Get(npcOrganizationID).GetRawName(languageID)


class NumericPropertyHandler(BasePropertyHandler):
	__id__ = 9


class Localization(object):

	def __init__(self, root, languageID="en-us", cfgInstance=None):
		self.cfg = cfgInstance or cfg

		self._propertyHandlers = {}
		for cls in globals().itervalues():
			if isinstance(cls, type) and issubclass(cls, BasePropertyHandler):
				self._propertyHandlers[cls.__id__] = cls(self, cfgInstance)

		stuff = embedfs.EmbedFS(os.path.join(root, "resLocalization.stuff"))
		stuffFSD = embedfs.EmbedFS(os.path.join(root, "resLocalizationFSD.stuff"))

		def _loadlanguage(languageID, s1, s2):
			x, data = cPickle.loads(s1.open("res/localization/localization_%s.pickle" % languageID).read())
			data.update(cPickle.loads(s2.open("res/localizationFSD/localization_fsd_%s.pickle" % languageID).read())[1])
			return data

		self.languageID = languageID

		# load primary language
		self.primary = _loadlanguage(languageID, stuff, stuffFSD)

		# if the primary language isn't english, load the english pack as fallback
		if languageID != "en-us":
			self.fallback = _loadlanguage("en-us", stuff, stuffFSD)
		else:
			self.fallback = None

		self.languageLabels = {}

		# load labels
		for efs, resname in (
			(stuff, "res/localization/localization_main.pickle"),
			(stuffFSD, "res/localizationFSD/localization_fsd_main.pickle"),
		):
			unPickledObject = cPickle.loads(efs.open(resname).read())
			for messageID, dataRow in unPickledObject['labels'].iteritems():
				fp = dataRow['FullPath']
				label = fp + '/' + dataRow['label'] if fp else dataRow['label']
				self.languageLabels[label.encode('ascii')] = messageID

		# clean up some stuff immediately (frees ~4MB)
		del unPickledObject, stuff, stuffFSD
		gc.collect()


	def _format(self, fmt, param, languageID):
		raw, noclue, tokens = fmt
		try:
			for token, data in tokens.iteritems():
				handler = self._propertyHandlers[data['variableType']]
				getter = getattr(handler, data['propertyName'] or "default")
				replacement = getter(param[data['variableName']], languageID, **data['kwargs'])
				raw = raw.replace(token, unicode(replacement))
		except KeyError:
			print "NO HANDLER FOR:"
			print "- token:", token
			print "- data:", data
			print "- param:", param
			print "- format:", raw
			raise

		return raw


	def GetByMessageID(self, messageID, languageID=None, **kwarg):
		if messageID is None:
			return ""

		tr = self.primary.get(messageID, False)
		if tr == False and self.fallback:
			tr = self.fallback.get(messageID)
		if tr:
			if kwarg or tr[2]:
				return self._format(tr, kwarg, languageID)
			return tr[0]

		return "<NO TEXT, messageID=%d, param=%s>" % (messageID, kwarg)


	def GetByLabel(self, label, languageID=None, **kwarg):
		try:
			messageID = self.languageLabels[label]
		except KeyError:
			return '[no label: %s]' % label

		return self.GetByMessageID(messageID, languageID, **kwarg)


	# The special handling of important names in EVE isn't necessary for Reverence.
	GetImportantByMessageID = GetByMessageID
	GetImportantByLabel = GetByLabel


########NEW FILE########
__FILENAME__ = pyFSD
"""Odyssey pyFSD module

- implements the functionality of bin\pyFSD.pyd in the EVE install.

Copyright (c) 2003-2013 Jamie "Entity" van den Berge <jamie@hlekkir.com>

This code is free software; you can redistribute it and/or modify
it under the terms of the BSD license (see the file LICENSE.txt
included with the distribution).
"""

from reverence import _pyFSD
FsdUnsignedIntegerKeyMap = _pyFSD.FsdUnsignedIntegerKeyMap

########NEW FILE########
__FILENAME__ = strings
"""Strings table for TYPE_STRINGR

Copyright (c) 2003-2012 Jamie "Entity" van den Berge <jamie@hlekkir.com>

This code is free software; you can redistribute it and/or modify
it under the terms of the BSD license (see the file LICENSE.txt
included with the distribution).
"""

stringTable = [
None,
"*corpid",
"*locationid",
"age",
"Asteroid",
"authentication",
"ballID",
"beyonce",
"bloodlineID",
"capacity",
"categoryID",
"character",
"characterID",
"characterName",
"characterType",
"charID",
"chatx",
"clientID",
"config",
"contraband",
"corporationDateTime",
"corporationID",
"createDateTime",
"customInfo",
"description",
"divisionID",
"DoDestinyUpdate",
"dogmaIM",
"EVE System",
"flag",
"foo.SlimItem",
"gangID",
"Gemini",
"gender",
"graphicID",
"groupID",
"header",
"idName",
"invbroker",
"itemID",
"items",
"jumps",
"line",
"lines",
"locationID",
"locationName",
"macho.CallReq",
"macho.CallRsp",
"macho.MachoAddress",
"macho.Notification",
"macho.SessionChangeNotification",
"modules",
"name",
"objectCaching",
"objectCaching.CachedObject",
"OnChatJoin",
"OnChatLeave",
"OnChatSpeak",
"OnGodmaShipEffect",
"OnItemChange",
"OnModuleAttributeChange",
"OnMultiEvent",
"orbitID",
"ownerID",
"ownerName",
"quantity",
"raceID",
"RowClass",
"securityStatus",
"Sentry Gun",
"sessionchange",
"singleton",
"skillEffect",
"squadronID",
"typeID",
"used",
"userID",
"util.CachedObject",
"util.IndexRowset",
"util.Moniker",
"util.Row",
"util.Rowset",
"*multicastID",
"AddBalls",
"AttackHit3",
"AttackHit3R",
"AttackHit4R",
"DoDestinyUpdates",
"GetLocationsEx",
"InvalidateCachedObjects",
"JoinChannel",
"LSC",
"LaunchMissile",
"LeaveChannel",
"OID+",
"OID-",
"OnAggressionChange",
"OnCharGangChange",
"OnCharNoLongerInStation",
"OnCharNowInStation",
"OnDamageMessage",
"OnDamageStateChange",
"OnEffectHit",
"OnGangDamageStateChange",
"OnLSC",
"OnSpecialFX",
"OnTarget",
"RemoveBalls",
"SendMessage",
"SetMaxSpeed",
"SetSpeedFraction",
"TerminalExplosion",
"address",
"alert",
"allianceID",
"allianceid",
"bid",
"bookmark",
"bounty",
"channel",
"charid",
"constellationid",
"corpID",
"corpid",
"corprole",
"damage",
"duration",
"effects.Laser",
"gangid",
"gangrole",
"hqID",
"issued",
"jit",
"languageID",
"locationid",
"machoVersion",
"marketProxy",
"minVolume",
"orderID",
"price",
"range",
"regionID",
"regionid",
"role",
"rolesAtAll",
"rolesAtBase",
"rolesAtHQ",
"rolesAtOther",
"shipid",
"sn",
"solarSystemID",
"solarsystemid",
"solarsystemid2",
"source",
"splash",
"stationID",
"stationid",
"target",
"userType",
"userid",
"volEntered",
"volRemaining",
"weapon",
"agent.missionTemplatizedContent_BasicKillMission",
"agent.missionTemplatizedContent_ResearchKillMission",
"agent.missionTemplatizedContent_StorylineKillMission",
"agent.missionTemplatizedContent_GenericStorylineKillMission",
"agent.missionTemplatizedContent_BasicCourierMission",
"agent.missionTemplatizedContent_ResearchCourierMission",
"agent.missionTemplatizedContent_StorylineCourierMission",
"agent.missionTemplatizedContent_GenericStorylineCourierMission",
"agent.missionTemplatizedContent_BasicTradeMission",
"agent.missionTemplatizedContent_ResearchTradeMission",
"agent.missionTemplatizedContent_StorylineTradeMission",
"agent.missionTemplatizedContent_GenericStorylineTradeMission",
"agent.offerTemplatizedContent_BasicExchangeOffer",
"agent.offerTemplatizedContent_BasicExchangeOffer_ContrabandDemand",
"agent.offerTemplatizedContent_BasicExchangeOffer_Crafting",
"agent.LoyaltyPoints",
"agent.ResearchPoints",
"agent.Credits",
"agent.Item",
"agent.Entity",
"agent.Objective",
"agent.FetchObjective",
"agent.EncounterObjective",
"agent.DungeonObjective",
"agent.TransportObjective",
"agent.Reward",
"agent.TimeBonusReward",
"agent.MissionReferral",
"agent.Location",
"agent.StandardMissionDetails",
"agent.OfferDetails",
"agent.ResearchMissionDetails",
"agent.StorylineMissionDetails",
"#196",
"#197",
"#198",
"#199",
"#200",
"#201",
"#202",
"#203",
"#204",
"#205",
"#206",
"#207",
"#208",
"#209",
"#210",
"#211",
"#212",
"#213",
"#214",
"#215",
"#216",
"#217",
"#218",
"#219",
"#220",
"#221",
"#222",
"#223",
"#224",
"#225",
"#226",
"#227",
"#228",
"#229",
"#230",
"#231",
"#232",
"#233",
"#234",
"#235",
"#236",
"#237",
"#238",
"#239",
"#240",
"#241",
"#242",
"#243",
"#244",
"#245",
"#246",
"#247",
"#248",
"#249",
"#250",
"#251",
"#252",
"#253",
"#254",
"#255",
]

########NEW FILE########
__FILENAME__ = util
"""Data container classes, text formatting and item type checking functions

Copyright (c) 2003-2013 Jamie "Entity" van den Berge <jamie@hlekkir.com>

This code is free software; you can redistribute it and/or modify
it under the terms of the BSD license (see the file LICENSE.txt
included with the distribution).

Parts of code inspired by or based on EVE Online, with permission from CCP.
"""

import __builtin__
import types
import os
import time
import math
import cPickle
import _weakref

from . import _os


DECIMAL = "."  # decimal point for currency. 
DIGIT = ","	# thousands separator

#-----------------------------------------------------------------------------
# Data containers
#-----------------------------------------------------------------------------

class Object:
	pass


#-----------------------------------------------------------------------------
# Formatting and stuff
#-----------------------------------------------------------------------------

def FmtDate(blueTime):
	sec = _os.FileTimeToSystemTime(blueTime)
	return time.strftime("%Y.%m.%d %H:%M:%S", time.gmtime(sec))

def FmtTimeInterval(interval, breakAt=None):
	if interval < 10000L:
		return "a short amount of time"

	year, month, wd, day, hour, min, sec, ms = _os.GetTimeParts(interval + _os.epoch_offset)
	year -= 1970
	month -= 1
	day -= 1
	items = []

	_s = ['','s']

	while 1:

		if year:
			items.append(str(year) + " year" + _s[year>1])
		if breakAt == "year":
			break

		if month:
			items.append(str(month) + " month" + _s[month>1])
		if breakAt == "month":
			break

		if day:
			items.append(str(day) + " day" + _s[day>1])
		if breakAt == "day":
			break

		if hour:
			items.append(str(hour) + " hour" + _s[hour>1])
		if breakAt == "hour":
			break

		if min:
			items.append(str(min) + " minute" + _s[min>1])
		if breakAt == "min":
			break

		if sec:
			items.append(str(sec) + " second" + _s[sec>1])
		if breakAt == "sec":
			break

		if ms:
			items.append(str(ms) + " millisecond" + _s[ms>1])
		break

	if items:
		if len(items) == 1:
			return items[0]
		else:
			lastItem = items.pop()
			return ", ".join(items) + " and " + lastItem
	else:
		if breakAt == "sec":
			return "less than a second"
		elif breakAt == "min":
			return "less than a minute"
		else:
			return "less than a " + breakAt


# todo, translation stuff.
_fmtOrder = {
	3: ("K", (" thousand", " thousands")),
	6: ("M", (" million" , " millions")),
	9: ("B", (" billion" , " billions")),
   12: ("T", (" trillion", " trillions")),
}
	

def FmtAmt(amount, fmt="ln", showFraction=0, fillWithZero=0):
	if amount == None:
		amount = 0
	else:
		try:
			long(amount)
		except:
			raise RuntimeError("AmountMustBeInteger", (amount))

	sign = "-" if float(amount) < 0.0 else ""
	amount = abs(amount)

	if fmt[0] == "l":
		amount, fraction = str(float(amount)).split(".")
		amount = amount.rjust((len(amount)+2)//3*3)
		amount = DIGIT.join((amount[x:x+3] for x in xrange(0, len(amount), 3))).strip()
		if fillWithZero:
			fraction = fraction.ljust(showFraction, "0")
		fraction = fraction[:showFraction]
		if fraction:
			amount += DECIMAL + fraction

	elif fmt[0] == "s":
		if amount >= 10000:
			order = min(len(str(long(amount)))//3*3, 12)
			symbol, canonical = _fmtOrder[order]
			amount = TruncateAmt(amount, 10**order) + (symbol if (fmt[1]!="l") else canonical[str(amount)[0]!="1"])

	else:
		amount = long(amount)

	return sign + str(amount)


def TruncateAmt(val, unit):
	rest = (val % unit) / (unit/100L)
	ret = str(val / unit)
	if rest > 0:
		ret += DECIMAL + ('%02d' % rest).rstrip("0")
	return ret

def TruncateDecimals(s, maxdecimals):
	ix = s.rfind(DECIMAL)
	if ix == -1 or maxdecimals is None:
		return s
	return s[:ix+max(0, maxdecimals)+1]


def FmtDist(dist, maxdecimals=3):
	dist = max(0, dist)
	if dist < 1.0:
		return TruncateDecimals(str(dist)[:5], maxdecimals) + " m"
	if dist < 10000.0:
		return TruncateDecimals(FmtAmt(long(dist)), maxdecimals) + " m"
	elif dist < 10000000000.0:
		return TruncateDecimals(FmtAmt(long(dist/1000.0)), maxdecimals) + " km"
	else:
		dist /= 149597870700.0
		if dist > 1000.0:
			return TruncateDecimals(FmtAmt(long(dist)), maxdecimals) + " AU"
		else:
			return TruncateDecimals((str(dist)[:5]).replace(".", DECIMAL), maxdecimals) + " AU"


def FmtISK(isk, showAurarAlways=1, sign=" ISK"):
	if not showAurarAlways:
		if long(isk) == isk:
			return FmtAmt(long(isk)) + sign
	return FmtAmt(round(isk, 2), showFraction=2, fillWithZero=True) + sign


_roman = {}
class preproman:
	for i in xrange(1, 40):
		n = i
		result = ""
		for (numeral, length, integer,) in (('X', 1, 10),('IX', 2, 9),('V', 1, 5),('IV', 2, 4),('I', 1, 1)):
			while i >= integer:
				result += numeral
				i -= integer
		_roman[n] = result
del preproman

def IntToRoman(n):
	return _roman.get(int(n), str(n))



#-----------------------------------------------------------------------------
# Type checking functions
#-----------------------------------------------------------------------------

def IsSystem(ownerID):
	return ownerID <= 10000

def IsNPC(ownerID):
	return (ownerID < 100000000) and (ownerID > 10000)

def IsSystemOrNPC(ownerID):
	return (ownerID < 100000000)

def IsFaction(ownerID):
	if (ownerID >= 500000) and (ownerID < 1000000):
		return 1
	else:
		return 0

def IsCorporation(ownerID):
	if (ownerID >= 1000000) and (ownerID < 2000000):
		return 1
	elif ownerID < 100000000:
		return 0
	else:
		return cfg.eveowners.Get(ownerID).IsCorporation()

def IsCharacter(ownerID):
	if (ownerID >= 3000000) and (ownerID < 4000000):
		return 1
	elif ownerID < 100000000:
		return 0
	else:
		return cfg.eveowners.Get(ownerID).IsCharacter()

def IsOwner(ownerID, fetch=0):
	if ((ownerID >=  500000) and (ownerID < 1000000))\
	or ((ownerID >= 1000000) and (ownerID < 2000000))\
	or ((ownerID >= 3000000) and (ownerID < 4000000)):
		return 1
	if IsNPC(ownerID):
		return 0
	if fetch:
		return cfg.eveowners.Get(ownerID).groupID in (const.groupCharacter, const.groupCorporation)
	return 0

def IsAlliance(ownerID):
	if ownerID < 100000000:
		return 0
	else:
		return cfg.eveowners.Get(ownerID).IsAlliance()

def IsRegion(itemID):
	return (itemID >= 10000000) and (itemID < 20000000)

def IsConstellation(itemID):
	return (itemID >= 20000000) and (itemID < 30000000)

def IsSolarSystem(itemID):
	return (itemID >= 30000000) and (itemID < 40000000)

def IsWormholeSystem(itemID):
	return (itemID >= const.mapWormholeSystemMin) and (itemID < const.mapWormholeSystemMax)
	
def IsWormholeConstellation(constellationID):
	return (constellationID >= const.mapWormholeConstellationMin) and (constellationID < const.mapWormholeConstellationMax)
	
def IsWormholeRegion(regionID):
	return (regionID >= const.mapWormholeRegionMin) and (regionID < const.mapWormholeRegionMax)

def IsUniverseCelestial(itemID):
	return (itemID >= const.minUniverseCelestial) and (itemID <= const.maxUniverseCelestial)
	
def IsStargate(itemID):
	return (itemID >= 50000000) and (itemID < 60000000)

def IsStation(itemID):
	return (itemID >= 60000000) and (itemID < 64000000)

def IsOutpost(itemID):
	return (itemID >= 61000000) and (itemID < 64000000)

def IsTrading(itemID):
	return (itemID >= 64000000) and (itemID < 66000000)

def IsOfficeFolder(itemID):
	return (itemID >= 66000000) and (itemID < 68000000)

def IsFactoryFolder(itemID):
	return (itemID >= 68000000) and (itemID < 70000000)

def IsUniverseAsteroid(itemID):
	return (itemID >= 70000000) and (itemID < 80000000)

def IsJunkLocation(locationID):
	if locationID >= 2000:
		return 0
	elif locationID in [6, 8, 10, 23, 25]:
		return 1
	elif locationID > 1000 and locationID < 2000:
		return 1
	else:
		return 0

def IsControlBunker(itemID):
	return (itemID >= 80000000) and (itemID < 80100000)

def IsPlayerItem(itemID):
	return (itemID >= const.minPlayerItem and itemID < const.maxPlayerItem)

def IsNewbieSystem(itemID):
	default = [
		30002547, 30001392, 30002715,
		30003489, 30005305, 30004971,
		30001672, 30002505, 30000141,
		30003410, 30005042, 30001407,
	]

#	   
#	optional = [
#		30001722, 30002518, 30003388, 30003524,
#		30005015, 30010141, 30011392, 30011407,
#		30011672, 30012505, 30012547, 30012715,
#		30013410, 30013489, 30014971, 30015042,
#		30015305, 30020141, 30021392, 30021407,
#		30021672, 30022505, 30022547, 30022715,
#		30023410, 30023489, 30024971, 30025042,
#		30025305, 30030141, 30031392, 30031407,
#		30031672, 30032505, 30032547, 30032715,
#		30033410, 30033489, 30034971, 30035042,
#		30035305, 30040141, 30041392, 30041407,
#		30041672, 30042505, 30042547, 30042715,
#		30043410, 30043489, 30044971, 30045042,
#		30045305,
#	]
#
#	if boot.region == "optic":
#		return itemID in (default + optional)

	return itemID in default


########NEW FILE########
__FILENAME__ = _os
"""Miscellaneous time functions for blue module.

Copyright (c) 2003-2012 Jamie "Entity" van den Berge <jamie@hlekkir.com>

This code is free software; you can redistribute it and/or modify
it under the terms of the BSD license (see the file LICENSE.txt
included with the distribution).
"""

from time import time, gmtime
import operator

_offset = 0L

epoch_offset = 116444736000000000L

def GetTime():
	return long((time() * 10000000L) + epoch_offset) - _offset

def FileTimeToSystemTime(t):
    return (t-epoch_offset) / 10000000L

def SyncTime(list):
	global _offset
	_offset = 0
	deltas = [(localTime-remoteTime) for localTime, remoteTime in list]
	_offset = long(reduce(operator.add, deltas) / len(deltas))

def GetTimeParts(date):
	assert date >= epoch_offset
	date -= epoch_offset
	# date==0 should yield [1970, 1, 4, 1, 0, 0, 0, 0]
	seconds, ms = divmod(date/10000, 1000)
	s = gmtime(seconds)
	return [s.tm_year, s.tm_mon, s.tm_wday+1, s.tm_mday, s.tm_hour, s.tm_min, s.tm_sec, int(ms)]



########NEW FILE########
