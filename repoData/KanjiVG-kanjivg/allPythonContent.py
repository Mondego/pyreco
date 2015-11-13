__FILENAME__ = harmonize-svg
#!/usr/bin/python2
# -*- coding: utf-8 -*-
#
#  Copyright (C) 2009  Alexandre Courbot
#
#  This program is free software: you can redistribute it and/or modify
#  it under the terms of the GNU General Public License as published by
#  the Free Software Foundation, either version 3 of the License, or
#  (at your option) any later version.
#
#  This program is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU General Public License for more details.
#
#  You should have received a copy of the GNU General Public License
#  along with this program.  If not, see <http://www.gnu.org/licenses/>.
from xml.etree.ElementTree import XMLID, tostring
import re, codecs, os, string, kanjivg, os.path, sys

def findText(elt):
	if elt.text: return elt.text
	else:
		childs = elt.getchildren()
		if len(childs): return findText(childs[0])
		else: return None

class Parser:
	def __init__(self, content):
		self.content = content

	def parse(self):
		while 1:
			match = re.search('\$\$(\w*)', self.content)
			if not match: break
			fname = 'callback_' + match.group(1)
			if hasattr(self, fname):
				rfunc = getattr(self, fname)
				ret = rfunc()
				self.content = self.content[:match.start(0)] + ret + self.content[match.end(0):]
			else: self.content = self.content[:match.start(0)] + self.content[match.end(0):]

class TemplateParser(Parser):
	def __init__(self, content, kanji, document, groups):
		Parser.__init__(self, content)
		self.kanji = kanji
		self.document = document
		self.groups = groups

	def callback_kanji(self):
		return self.kanji

	def callback_strokenumbers(self):
		if not self.groups.has_key("StrokeNumbers"):
			print "Error - no StrokeNumbers group for kanji %s (%s)" % (self.kanji, hex(kanjivg.realord(self.kanji)))
			return ""
		numbers = self.groups["StrokeNumbers"]
		elts = numbers.findall(".//{http://www.w3.org/2000/svg}text")
		strs = []
		for elt in elts:
			attrs = []
			if elt.attrib.has_key("transform"): attrs.append(' transform="%s"' % (elt.attrib["transform"],))
			if elt.attrib.has_key("x"): attrs.append(' x="%s"' % (elt.attrib["x"],))
			if elt.attrib.has_key("y"): attrs.append(' y="%s"' % (elt.attrib["y"],))
			strs.append('<text%s>%s</text>' % (''.join(attrs), findText(elt)))
		return "\n\t\t".join(strs)

	def callback_strokepaths(self):
		if not self.groups.has_key("StrokePaths"):
			print "Error - no StrokePaths group for kanji %s (%s)" % (self.kanji, hex(kanjivg.realord(self.kanji)))
			return ""
		paths = self.groups["StrokePaths"]
		elts = paths.findall(".//{http://www.w3.org/2000/svg}path")
		strs = []
		for elt in elts:
			d = elt.attrib["d"]
			d = re.sub('(\d) (\d)', '\\1,\\2', d)
			d = re.sub("[\n\t ]+", "", d)
			strs.append('<path d="%s"/>' % (d,))
		return "\n\t\t".join(strs)

if __name__ == "__main__":
	# Only process files given as argument...
	if len(sys.argv) > 1:
		filesToProceed = sys.argv[1:]
	# Or do the whole SVG set if no argument is given
	else:
		filesToProceed = []
		for f in os.listdir("SVG"):
			if not f.endswith(".svg"): continue
			filesToProceed.append(os.path.join("SVG", f))

	for f in filesToProceed:
		fname = f.split(os.path.sep)[-1]
		if fname[4] in "0123456789abcdef":
			kanji = kanjivg.realchr(int(fname[:5], 16))
		else: kanji = kanjivg.realchr(int(fname[:4], 16))

		document, groups = XMLID(open(f).read())
		tpp = TemplateParser(open("template.svg").read(), kanji, document, groups)
		tpp.parse()
		out = codecs.open(f, "w", "utf-8")
		out.write(tpp.content)

########NEW FILE########
__FILENAME__ = kanjivg
# -*- coding: utf-8 -*-
#
#  Copyright (C) 2009-2013 Alexandre Courbot
#
#  This program is free software: you can redistribute it and/or modify
#  it under the terms of the GNU General Public License as published by
#  the Free Software Foundation, either version 3 of the License, or
#  (at your option) any later version.
#
#  This program is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU General Public License for more details.
#
#  You should have received a copy of the GNU General Public License
#  along with this program.  If not, see <http://www.gnu.org/licenses/>.

from xmlhandler import *

# Sample licence header
licenseString = """Copyright (C) 2009-2013 Ulrich Apel.
This work is distributed under the conditions of the Creative Commons
Attribution-Share Alike 3.0 Licence. This means you are free:
* to Share - to copy, distribute and transmit the work
* to Remix - to adapt the work

Under the following conditions:
* Attribution. You must attribute the work by stating your use of KanjiVG in
  your own copyright header and linking to KanjiVG's website
  (http://kanjivg.tagaini.net)
* Share Alike. If you alter, transform, or build upon this work, you may
  distribute the resulting work only under the same or similar license to this
  one.

See http://creativecommons.org/licenses/by-sa/3.0/ for more details."""

def isKanji(v):
	return (v >= 0x4E00 and v <= 0x9FC3) or (v >= 0x3400 and v <= 0x4DBF) or (v >= 0xF900 and v <= 0xFAD9) or (v >= 0x2E80 and v <= 0x2EFF) or (v >= 0x20000 and v <= 0x2A6DF)

# Returns the unicode of a character in a unicode string, taking surrogate pairs into account
def realord(s, pos = 0):
	if s == None: return None
	code = ord(s[pos])
	if code >= 0xD800 and code < 0xDC00:
		if (len(s) <= pos + 1):
			print "realord warning: missing surrogate character"
			return 0
		code2 = ord(s[pos + 1])
		if code2 >= 0xDC00 and code < 0xE000:
			code = 0x10000 + ((code - 0xD800) << 10) + (code2 - 0xDC00)	
	return code

def realchr(i):
	if i < 0x10000: return unichr(i)
	else: return unichr(((i - 0x10000) >> 10) + 0xD800) + unichr(0xDC00 + (i & 0x3ff))

class Kanji:
	"""Describes a kanji. The root stroke group is accessible from the strokes member."""
	def __init__(self, code, variant):
		# Unicode of char being represented (int)
		self.code = code
		# Variant of the character, if any
		self.variant = variant
		self.strokes = None

	# String identifier used to uniquely identify the kanji
	def kId(self):
		ret = "%05x" % (self.code,)
		if self.variant: ret += "-%s" % (self.variant,)
		return ret

	def outputStrokesNumbers(self, out, indent = 0):
		strokes = self.getStrokes()
		cpt = 1
		for stroke in strokes:
			stroke.numberToSVG(out, cpt, indent + 1)
			cpt += 1

	def outputStrokes(self, out, indent = 0):
		self.strokes.toSVG(out, self.kId(), [0], [1])

	def simplify(self):
		self.strokes.simplify()

	def getStrokes(self):
		return self.strokes.getStrokes()


class StrokeGr:
	"""Describes a stroke group belonging to a kanji as closely as possible to the XML format. Sub-stroke groups or strokes are available in the childs member. They can either be of class StrokeGr or Stroke so their type should be checked."""
	def __init__(self, parent):
		self.parent = parent
		if parent: parent.childs.append(self)
		# Element of strokegr
		self.element = None
		# A more common, safer element this one derives of
		self.original = None
		self.part = None
		self.number = None
		self.variant = False
		self.partial = False
		self.tradForm = False
		self.radicalForm = False
		self.position = None
		self.radical = None
		self.phon = None
		
		self.childs = []

	def toSVG(self, out, rootId, groupCpt = [0], strCpt = [1], indent = 0):
		gid = rootId
		if groupCpt[0] != 0: gid += "-g" + str(groupCpt[0])
		groupCpt[0] += 1

		idString = ' id="kvg:%s"' % (gid)
		eltString = ""
		if self.element: eltString = ' kvg:element="%s"' % (self.element)
		variantString = ""
		if self.variant: variantString = ' kvg:variant="true"'
		partialString = ""
		if self.partial: partialString = ' kvg:partial="true"'
		origString = ""
		if self.original: origString = ' kvg:original="%s"' % (self.original)
		partString = ""
		if self.part: partString = ' kvg:part="%d"' % (self.part)
		numberString = ""
		if self.number: numberString = ' kvg:number="%d"' % (self.number)
		tradFormString = ""
		if self.tradForm: tradFormString = ' kvg:tradForm="true"'
		radicalFormString = ""
		if self.radicalForm: radicalFormString = ' kvg:radicalForm="true"'
		posString = ""
		if self.position: posString = ' kvg:position="%s"' % (self.position)
		radString = ""
		if self.radical: radString = ' kvg:radical="%s"' % (self.radical)
		phonString = ""
		if self.phon: phonString = ' kvg:phon="%s"' % (self.phon)
		out.write("\t" * indent + '<g%s%s%s%s%s%s%s%s%s%s%s%s>\n' % (idString, eltString, partString, numberString, variantString, origString, partialString, tradFormString, radicalFormString, posString, radString, phonString))

		for child in self.childs:
			child.toSVG(out, rootId, groupCpt, strCpt, indent + 1)

		out.write("\t" * indent + '</g>\n')


	def components(self, simplified = True, recursive = False, level = 0):
		ret = []
		childsComp = []
		for child in self.childs:
			if isinstance(child, StrokeGr):
				found = False
				# Can we find the component in the child?
				if simplified and child.original: ret.append(child.original); found = True
				elif child.element: ret.append(child.element); found = True
				# If not, the components we are looking for are the child's
				# components - we also do that if we asked all the sub-components of the group
				if not found or recursive:
					newLevel = level
					if found: newLevel += 1
					childsComp += child.components(simplified, recursive, newLevel)
		if recursive and not len(ret) == 0: ret = [ level ] + ret + childsComp
		return ret

	def simplify(self):
		for child in self.childs: 
			if isinstance(child, StrokeGr): child.simplify()
		if len(self.childs) == 1 and isinstance(self.childs[0], StrokeGr):
			# Check if there is no conflict
			if child.element and self.element and child.element != self.element: return
			if child.original and self.original and child.original != self.original: return
			# Parts cannot be merged
			if child.part and self.part and self.part != child.part: return
			if child.variant and self.variant and child.variant != self.variant: return
			if child.partial and self.partial and child.partial != self.partial: return
			if child.tradForm and self.tradForm and child.tradForm != self.tradForm: return
			if child.radicalForm and self.radicalForm and child.radicalForm != self.radicalForm: return
			# We want to preserve inner identical positions - we may have something at the top
			# of another top element, for instance.
			if child.position and self.position: return
			if child.radical and self.radical and child.radical != self.radical: return
			if child.phon and self.phon and child.phon != self.phon: return

			# Ok, let's merge!
			child = self.childs[0]
			self.childs = child.childs
			if child.element: self.element = child.element
			if child.original: self.original = child.original
			if child.part: self.part = child.part
			if child.variant: self.variant = child.variant
			if child.partial: self.partial = child.partial
			if child.tradForm: self.tradForm = child.tradForm
			if child.radicalForm: self.radicalForm = child.radicalForm
			if child.position: self.position = child.position
			if child.radical: self.radical = child.radical
			if child.phon: self.phon = child.phon

	def getStrokes(self):
		ret = []
		for child in self.childs: 
			if isinstance(child, StrokeGr): ret += child.getStrokes()
			else: ret.append(child)
		return ret
		

class Stroke:
	"""A single stroke, containing its type and (optionally) its SVG data."""
	def __init__(self, parent):
		self.stype = None
		self.svg = None
		self.numberPos = None
	
	def numberToSVG(self, out, number, indent = 0):
		if self.numberPos:
			out.write("\t" * indent + '<text transform="matrix(1 0 0 1 %.2f %.2f)">%d</text>\n' % (self.numberPos[0], self.numberPos[1], number)) 

	def toSVG(self, out, rootId, groupCpt, strCpt, indent = 0):
		pid = rootId + "-s" + str(strCpt[0])
		strCpt[0] += 1
		s = "\t" * indent + '<path id="kvg:%s"' % (pid,)
		if self.stype: s += ' kvg:type="%s"' % (self.stype,)
		if self.svg: s += ' d="%s"' % (self.svg)
		s += '/>\n'
		out.write(s)

class KanjisHandler(BasicHandler):
	"""XML handler for parsing kanji files. It can handle single-kanji files or aggregation files. After parsing, the kanjis are accessible through the kanjis member, indexed by their svg file name."""
	def __init__(self, code, variant):
		BasicHandler.__init__(self)
		self.kanji = Kanji(code, variant)
		self.groups = []
		self.compCpt = {}
		self.metComponents = set()

	def handle_start_kanji(self, attrs):
		pass

	def handle_end_kanji(self):
		if len(self.groups) != 0:
			print "WARNING: stroke groups remaining after reading kanji!"
		self.groups = []

	def handle_start_strokegr(self, attrs):
		if len(self.groups) == 0: parent = None
		else: parent = self.groups[-1]
		group = StrokeGr(parent)

		# Now parse group attributes
		if attrs.has_key("element"): group.element = unicode(attrs["element"])
		if attrs.has_key("variant"): group.variant = str(attrs["variant"])
		if attrs.has_key("partial"): group.partial = str(attrs["partial"])
		if attrs.has_key("original"): group.original = unicode(attrs["original"])
		if attrs.has_key("part"): group.part = int(attrs["part"])
		if attrs.has_key("number"): group.number = int(attrs["number"])
		if attrs.has_key("tradForm") and str(attrs["tradForm"]) == "true": group.tradForm = True
		if attrs.has_key("radicalForm") and str(attrs["radicalForm"]) == "true": group.radicalForm = True
		if attrs.has_key("position"): group.position = unicode(attrs["position"])
		if attrs.has_key("radical"): group.radical = unicode(attrs["radical"])
		if attrs.has_key("phon"): group.phon = unicode(attrs["phon"])

		self.groups.append(group)

		if group.element: self.metComponents.add(group.element)
		if group.original: self.metComponents.add(group.original)

		if group.number:
			if not group.part: print "%s: Number specified, but part missing" % (self.kanji.kId())
			# The group must exist already
			if group.part > 1:
				if not self.compCpt.has_key(group.element + str(group.number)):
					print "%s: Missing numbered group" % (self.kanji.kId())
				elif self.compCpt[group.element + str(group.number)] != group.part - 1:
					print "%s: Incorrectly numbered group" % (self.kanji.kId())
			# The group must not exist
			else:
				if self.compCpt.has_key(group.element + str(group.number)):
					print "%s: Duplicate numbered group" % (self.kanji.kId())
			self.compCpt[group.element + str(group.number)] = group.part
		# No number, just a part - groups restart with part 1, otherwise must
		# increase correctly
		elif group.part:
				# The group must exist already
			if group.part > 1:
				if not self.compCpt.has_key(group.element):
					print "%s: Incorrectly started multi-part group" % (self.kanji.kId())
				elif self.compCpt[group.element] != group.part - 1:
					print "%s: Incorrectly splitted multi-part group" % (self.kanji.kId())
			self.compCpt[group.element] = group.part

	def handle_end_strokegr(self):
		group = self.groups.pop()
		if len(self.groups) == 0:
			if self.kanji.strokes:
				print "WARNING: overwriting root of kanji!"
			self.kanji.strokes = group

	def handle_start_stroke(self, attrs):
		if len(self.groups) == 0: parent = None
		else: parent = self.groups[-1]
		stroke = Stroke(parent)
		stroke.stype = unicode(attrs["type"])
		if attrs.has_key("path"): stroke.svg = unicode(attrs["path"])
		self.groups[-1].childs.append(stroke)

class SVGHandler(BasicHandler):
	"""SVG handler for parsing final kanji files. It can handle single-kanji files or aggregation files. After parsing, the kanji are accessible through the kanjis member, indexed by their svg file name."""
	def __init__(self):
		BasicHandler.__init__(self)
		self.kanjis = {}
		self.currentKanji = None
		self.groups = []
		self.metComponents = set()

	def handle_start_g(self, attrs):
		# Special case for handling the root
		if len(self.groups) == 0:
			id = hex(realord(attrs["kvg:element"]))[2:]
			self.currentKanji = Kanji(id)
			self.kanjis[id] = self.currentKanji
			self.compCpt = {}
			parent = None
		else: parent = self.groups[-1]
	
		group = StrokeGr(parent)
		# Now parse group attributes
		if attrs.has_key("kvg:element"): group.element = unicode(attrs["kvg:element"])
		if attrs.has_key("kvg:variant"): group.variant = str(attrs["kvg:variant"])
		if attrs.has_key("kvg:partial"): group.partial = str(attrs["kvg:partial"])
		if attrs.has_key("kvg:original"): group.original = unicode(attrs["kvg:original"])
		if attrs.has_key("kvg:part"): group.part = int(attrs["kvg:part"])
		if attrs.has_key("kvg:number"): group.number = int(attrs["kvg:number"])
		if attrs.has_key("kvg:tradForm") and str(attrs["kvg:tradForm"]) == "true": group.tradForm = True
		if attrs.has_key("kvg:radicalForm") and str(attrs["kvg:radicalForm"]) == "true": group.radicalForm = True
		if attrs.has_key("kvg:position"): group.position = unicode(attrs["kvg:position"])
		if attrs.has_key("kvg:radical"): group.radical = unicode(attrs["kvg:radical"])
		if attrs.has_key("kvg:phon"): group.phon = unicode(attrs["kvg:phon"])

		self.groups.append(group)

		if group.element: self.metComponents.add(group.element)
		if group.original: self.metComponents.add(group.original)

		if group.number:
			if not group.part: print "%s: Number specified, but part missing" % (self.currentKanji.kId())
			# The group must exist already
			if group.part > 1:
				if not self.compCpt.has_key(group.element + str(group.number)):
					print "%s: Missing numbered group" % (self.currentKanji.kId())
				elif self.compCpt[group.element + str(group.number)] != group.part - 1:
					print "%s: Incorrectly numbered group" % (self.currentKanji.kId())
			# The group must not exist
			else:
				if self.compCpt.has_key(group.element + str(group.number)):
					print "%s: Duplicate numbered group" % (self.currentKanji.kId())
			self.compCpt[group.element + str(group.number)] = group.part
		# No number, just a part - groups restart with part 1, otherwise must
		# increase correctly
		elif group.part:
				# The group must exist already
			if group.part > 1:
				if not self.compCpt.has_key(group.element):
					print "%s: Incorrectly started multi-part group" % (self.currentKanji.kId())
				elif self.compCpt[group.element] != group.part - 1:
					print "%s: Incorrectly splitted multi-part group" % (self.currentKanji.kId())
			self.compCpt[group.element] = group.part

	def handle_end_g(self):
		group = self.groups.pop()
		# End of kanji?
		if len(self.groups) == 0:
			self.currentKanji.strokes = group
			self.currentKanji = None
			self.groups = []


	def handle_start_path(self, attrs):
		if len(self.groups) == 0: parent = None
		else: parent = self.groups[-1]
		stroke = Stroke(parent)
		stroke.stype = unicode(attrs["kvg:type"])
		if attrs.has_key("d"): stroke.svg = unicode(attrs["d"])
		self.groups[-1].childs.append(stroke)

########NEW FILE########
__FILENAME__ = kvg
#!/usr/bin/python2
# -*- coding: utf-8 -*-
#
#  Copyright (C) 2011-2013 Alexandre Courbot
#
#  This program is free software: you can redistribute it and/or modify
#  it under the terms of the GNU General Public License as published by
#  the Free Software Foundation, either version 3 of the License, or
#  (at your option) any later version.
#
#  This program is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU General Public License for more details.
#
#  You should have received a copy of the GNU General Public License
#  along with this program.  If not, see <http://www.gnu.org/licenses/>.

import os, os.path, sys, codecs, re, datetime
from kanjivg import licenseString

pathre = re.compile(r'<path .*d="([^"]*)".*/>')

helpString = """Usage: %s <command> [ kanji files ]
Recognized commands:
  split file1 [ file2 ... ]       extract path data into a -paths suffixed file
  merge file1 [ file2 ... ]       merge path data from -paths suffixed file
  release                         create single release file""" % (sys.argv[0],)

def createPathsSVG(f):
	s = codecs.open(f, "r", "utf-8").read()
	paths = pathre.findall(s)
	out = codecs.open(f[:-4] + "-paths.svg", "w", "utf-8")
	out.write("""<!DOCTYPE svg PUBLIC "-//W3C//DTD SVG 1.0//EN" "http://www.w3.org/TR/2001/REC-SVG-20010904/DTD/svg10.dtd" []>
<svg xmlns="http://www.w3.org/2000/svg" width="109" height="109" viewBox="0 0 109 109" style="fill:none;stroke:#000000;stroke-width:3;stroke-linecap:round;stroke-linejoin:round;">\n""")
	i = 1
	for path in paths:
		out.write('<!--%2d--><path d="%s"/>\n' % (i, path))
		i += 1
	out.write("</svg>")

def mergePathsSVG(f):
	pFile = f[:-4] + "-paths.svg"
	if not os.path.exists(pFile):
		print "%s does not exist!" % (pFile,)
		return
	s = codecs.open(pFile, "r", "utf-8").read()
	paths = pathre.findall(s)
	s = codecs.open(f, "r", "utf-8").read()
	pos = 0
	while True:
		match = pathre.search(s[pos:])
		if match and len(paths) == 0 or not match and len(paths) > 0:
			print "Paths count mismatch for %s" % (f,)
			return
		if not match and len(paths) == 0: break
		s = s[:pos + match.start(1)] + paths[0] + s[pos + match.end(1):]
		pos += match.start(1) + len(paths[0])
		del paths[0]
	codecs.open(f, "w", "utf-8").write(s)

def release():
	datadir = "kanji"
	idMatchString = "<g id=\"kvg:StrokePaths_"
	allfiles = os.listdir(datadir)
	files = []
	for f in allfiles:
		if len(f) == 9: files.append(f)
	del allfiles
	files.sort()
	
	out = open("kanjivg.xml", "w")
	out.write('<?xml version="1.0" encoding="UTF-8"?>\n')
	out.write("<!--\n")
	out.write(licenseString)
	out.write("\nThis file has been generated on %s, using the latest KanjiVG data\nto this date." % (datetime.date.today()))
	out.write("\n-->\n")
	out.write("<kanjivg>\n")
	for f in files:
		data = open(os.path.join(datadir, f)).read()
		data = data[data.find("<svg "):]
		data = data[data.find(idMatchString) + len(idMatchString):]
		kidend = data.find("\"")
		data = "<kanji id=\"kvg:kanji_%s\">" % (data[:kidend],) + data[data.find("\n"):data.find('<g id="kvg:StrokeNumbers_') - 5] + "</kanji>\n"
		out.write(data)
	out.write("</kanjivg>\n")
	out.close()
	print("%d kanji emitted" % len(files))

actions = {
	"split": (createPathsSVG, 2),
	"merge": (mergePathsSVG, 2),
	"release": (release, 1)
}

if __name__ == "__main__":
	if len(sys.argv) < 2 or sys.argv[1] not in actions.keys() or \
		len(sys.argv) <= actions[sys.argv[1]][1]:
		print helpString
		sys.exit(0)

	action = actions[sys.argv[1]][0]
	files = sys.argv[2:]

	if len(files) == 0: action()
	else:
		for f in files:
			if not os.path.exists(f):
				print "%s does not exist!" % (f,)
				continue
			action(f)

########NEW FILE########
__FILENAME__ = listmissingcomponents
#!/usr/bin/python2
# -*- coding: utf-8 -*-
#
#  Copyright (C) 2009  Alexandre Courbot
#
#  This program is free software: you can redistribute it and/or modify
#  it under the terms of the GNU General Public License as published by
#  the Free Software Foundation, either version 3 of the License, or
#  (at your option) any later version.
#
#  This program is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU General Public License for more details.
#
#  You should have received a copy of the GNU General Public License
#  along with this program.  If not, see <http://www.gnu.org/licenses/>.

import os, codecs, xml.sax
from kanjivg import *

def addComponents(strokegr, compSet):
	if strokegr.element: compSet.add(strokegr.element)
	if strokegr.original: compSet.add(strokegr.original)
	for child in strokegr.childs:
		if isinstance(child, StrokeGr):
			addComponents(child, compSet)
		

if __name__ == "__main__":
	# Read all kanjis
	handler = KanjisHandler()
	xml.sax.parse("kanjivg.xml", handler)
	kanjis = handler.kanjis.values()

	kanjis.sort(lambda x,y: cmp(x.id, y.id))

	componentsList = set()
	for kanji in kanjis:
		addComponents(kanji.root, componentsList)
	print len(componentsList)

	missingComponents = set()
	for component in componentsList:
		key = hex(realord(component))[2:]
		if not handler.kanjis.has_key(key): missingComponents.add(component)
	print "Missing components:"
	for component in missingComponents:
		print component, hex(realord(component))
	print len(missingComponents), "missing components"

########NEW FILE########
__FILENAME__ = swap-strokes
#! /usr/bin/env python3
# -*- coding: utf-8 ; mode: python -*-
# © Copyright 2013 ospalh@gmail.com
# License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html

import argparse
import re

"""
Swap stroke data in KanjiVG files.

This is a helper script to fix problems where strokes or stroke
numbers are out of order. Run as script with --help for more info.

N.B.:
This is rather brittle. It does not use any kind of xml parser, but
looks for strings commonly found in the svg files. Use this only as a
support tool. Check that the script did what you expected after
running it.
"""

__version__ = '0.1.0'

number_text_pattern = '>{0}</text>'
stroke_re = '^\s.*-s{0}" kvg:type=".*" d="(.*)"/>'
stroke_text_pattern = '-s{0}" kvg:type="'


def swap_numbers(kanji, a, b):
    """Swap stroke numbers in a kanjivg file"""
    # We do hardly any checking. If something is wrong, just blow up.
    with open(kanji) as kf:
        lines = kf.readlines()
    num_a = -1
    num_b = -1
    line_a = ''
    line_b = ''
    line_a_pattern = number_text_pattern.format(a)
    line_b_pattern = number_text_pattern.format(b)
    for n, l in enumerate(lines):
        if line_a_pattern in l:
            num_a = n
            line_a = l
        if line_b_pattern in l:
            num_b = n
            line_b = l
    if num_a < 0 or num_b < 0:
        raise RuntimeError("Did not find both lines")
    lines[num_a] = line_b.replace(line_b_pattern, line_a_pattern)
    lines[num_b] = line_a.replace(line_a_pattern, line_b_pattern)
    with open(kanji, 'w') as kf:
        for l in lines:
            kf.write(l)


def swap_stroke_data(kanji, a, b):
    """Swap the stroke data in a kanjivg file"""
    # We do hardly any checking. If something is wrong, just blow up.
    with open(kanji) as kf:
        lines = kf.readlines()
    num_a = -1
    num_b = -1
    line_a_match = None
    line_b_match = None
    line_a_re = stroke_re.format(a)
    line_b_re = stroke_re.format(b)
    for n, l in enumerate(lines):
        m = re.search(line_a_re, l)
        if m:
            num_a = n
            line_a_match = m
        m = re.search(line_b_re, l)
        if m:
            num_b = n
            line_b_match = m
    if num_a < 0 or num_b < 0:
        raise RuntimeError("Did not find both lines")
    lines[num_a] = lines[num_a].replace(line_a_match.group(1),
                                        line_b_match.group(1))
    lines[num_b] = lines[num_b].replace(line_b_match.group(1),
                                        line_a_match.group(1))
    with open(kanji, 'w') as kf:
        for l in lines:
            kf.write(l)


def swap_strokes(kanji, a, b):
    """Swap strokes in a kanjivg file"""
    # We do hardly any checking. If something is wrong, just blow up.
    with open(kanji) as kf:
        lines = kf.readlines()
    num_a = -1
    num_b = -1
    line_a = ''
    line_b = ''
    line_a_pattern = stroke_text_pattern.format(a)
    line_b_pattern = stroke_text_pattern.format(b)
    for n, l in enumerate(lines):
        if line_a_pattern in l:
            num_a = n
            line_a = l
        if line_b_pattern in l:
            num_b = n
            line_b = l
    if num_a < 0 or num_b < 0:
        raise RuntimeError("Did not find both lines")
    lines[num_a] = line_b.replace(line_b_pattern, line_a_pattern)
    lines[num_b] = line_a.replace(line_a_pattern, line_b_pattern)
    with open(kanji, 'w') as kf:
        for l in lines:
            kf.write(l)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(
        description=u"""Swaps data for strokes a and b in the kanjivg svg
file "file".
Select one of the three options, number, data or stroke.
Look at the svg file with a text editor to determine which of the last two
options to use. When both stroke numbers and the strokes themselves are
out of order, run the script twice.""")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument('-n', '--number', action='store_const',
                       const=swap_numbers, dest='function',
                       help=u"""Swap the stroke numbers. Use this  when the
numbers seen are out of order.""")
    group.add_argument('-d', '--data',  action='store_const',
                       const=swap_stroke_data, dest='function',
                       help=u"""Swap only the vector data of the strokes.
Use this when the stroke types are correct in the original file, but the
graphical data doesn't match these types.""")
    group.add_argument('-s', '--stroke', action='store_const',
                       const=swap_strokes, dest='function',
                       help=u"""Swap the whole strokes, including the stroke
type. Use this if the graphical stroke data matches the stroke types in the
original file, but the strokes are in the wrong order.""")
    parser.add_argument('file', type=str, help='Kanji SVG file')
    parser.add_argument('stroke_a', type=int, help='First stroke to swap')
    parser.add_argument('stroke_b', type=int,
                        help='Second stroke to swap with the first stroke')
    args = parser.parse_args()
    args.function(args.file, args.stroke_a, args.stroke_b)

########NEW FILE########
__FILENAME__ = viewer
#!/usr/bin/python2
# -*- coding: utf-8 -*-
#
#  Copyright (C) 2010  Alexandre Courbot
#
#  This program is free software: you can redistribute it and/or modify
#  it under the terms of the GNU General Public License as published by
#  the Free Software Foundation, either version 3 of the License, or
#  (at your option) any later version.
#
#  This program is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU General Public License for more details.
#
#  You should have received a copy of the GNU General Public License
#  along with this program.  If not, see <http://www.gnu.org/licenses/>.

import sys, os, xml.sax, re, codecs, datetime
from PyQt4 import QtGui, QtCore
from kanjivg import *

def loadKanji(code):
	f = str(code)
	svgHandler = SVGHandler()
	parser = xml.sax.make_parser()
	parser.setContentHandler(svgHandler)
	parser.setFeature(xml.sax.handler.feature_external_ges, False)
	parser.setFeature(xml.sax.handler.feature_external_pes, False)
	parser.parse(os.path.join("data", f + ".svg"))

	kanji = svgHandler.kanjis.values()[0]
	return kanji

from PyQt4.QtCore import QPointF

def svg2Path(svg):
	'''Converts a SVG textual path into a QPainterPath'''
	retPath = QtGui.QPainterPath()

	# Add spaces between unseparated tokens
	t = svg
	t = re.sub(r"[a-zA-Z]\d|\d[a-zA-Z]", lambda(m): m.group(0)[0] + " " + m.group(0)[1], t)
	t = re.sub(r"[a-zA-Z]\d|\d[a-zA-Z]", lambda(m): m.group(0)[0] + " " + m.group(0)[1], t)
	t = re.sub(r"\-\d", lambda(m): " " + m.group(0), t)
	tokens = re.split("[ ,]+", t)

	# Convert to Qt path
	i = 0
	curAction = ''
	while i < len(tokens):
		if tokens[i] in ( "M", "m", "L", "l", "C", "c", "S", "s", "z", "Z" ):
			curAction = tokens[i]
			i += 1

		if curAction in ( "M", "m" ):
			dest = QPointF(float(tokens[i]), float(tokens[i + 1]))
			if curAction == "m": dest += retPath.currentPosition()
			retPath.moveTo(dest)
			i += 2
			lastControl = retPath.currentPosition()
		elif curAction in ( "L", "l" ):
			dest = QPointF(float(tokens[i]), float(tokens[i + 1]))
			if curAction == "l": dest += retPath.currentPosition()
			retPath.lineTo(dest)
			i += 2
			lastControl = retPath.currentPosition()
		elif curAction in ( "C", "c" ):
			p1 = QPointF(float(tokens[i]), float(tokens[i + 1]))
			p2 = QPointF(float(tokens[i + 2]), float(tokens[i + 3]))
			dest = QPointF(float(tokens[i + 4]), float(tokens[i + 5]))
			if curAction == "c":
				p1 += retPath.currentPosition()
				p2 += retPath.currentPosition()
				dest += retPath.currentPosition()
			retPath.cubicTo(p1, p2, dest)
			i += 6
			lastControl = p2
		elif curAction in ( "S", "s" ):
			p1 = retPath.currentPosition() * 2 - lastControl
			p2 = QPointF(float(tokens[i]), float(tokens[i + 1]))
			dest = QPointF(float(tokens[i + 2]), float(tokens[i + 3]))
			if curAction == "s":
				p2 += retPath.currentPosition()
				dest += retPath.currentPosition()
			retPath.cubicTo(p1, p2, dest)
			i += 4
			lastControl = p2
		elif curAction in ( "Z", "z" ):
			retPath.closeSubPath()
			lastControl = retPath.currentPosition()
		else:
			print "Unknown command %s while computing kanji path!" % ( tokens[i], )
			i += 1

	return retPath;

class SimpleStrokeRenderer:
	def __init__(self):
		self.strokesPen = QtGui.QPen()
		self.strokesPen.setWidth(2)
	
	def renderStroke(self, painter, stroke):
		painter.setPen(self.strokesPen)
		painter.drawPath(stroke.qPath)

class FancyStrokeRenderer:
	basicWeight = 1
	weightFactor = 1

	weights = {
		u'㇔' : (19, 18, 17, 16, 15, 14, 13, 12, 11, 10, 9, 8, 7, 7, 6, 6),
		u'㇔a' : (17, 16, 15, 14, 13, 12, 11, 10, 9, 8, 7, 6, 8, 10, 12, 14),
		u'㇐' : (9, 9, 9, 9, 9, 9, 10, 10, 10, 10, 10, 10, 10, 11, 11, 11, 11, 12, 12, 13, 13, 14, 14, 15, 15, 16, 15, 15, 14, 13, 12, 11, 10, 10, 10, 10, 10, 9, 9, 9, 9, 9, 9, 8, 8, 8, 8, 8),
		u'㇐a' : (11, 11, 12, 12, 13, 13, 14, 14, 15, 15, 14, 14, 13, 12, 11, 10),
		u'㇐b' : (10, 10, 11, 11, 11, 12, 12, 12, 12, 13, 13, 14, 14, 13, 12, 11, 11, 11, 10, 10, 10, 10, 9, 9, 9, 9, 9, 9, 8, 8, 8, 8),
		u'㇐c' : (9, 9, 9, 9, 9, 9, 10, 10,10, 10, 10, 10, 10, 11, 11, 11, 12, 12, 13, 13, 14, 14, 15, 15, 16, 15, 14, 13, 12, 11, 10, 9),
		u'㇑' : (8, 8, 8, 8, 8, 8, 8, 9, 9, 9, 9, 9, 9, 10, 10, 11, 11, 12, 12, 13, 13, 14, 14, 15, 15, 15, 15, 14, 14, 13, 13, 12, 12, 11, 11, 11, 11, 10, 10, 10, 10, 10, 9, 9, 9, 9, 9, 9),
		u'㇑a' : (9, 9, 9, 9, 9, 9, 9, 10, 10, 10, 10, 10, 10, 10, 11, 11, 12, 12, 12, 13, 13, 13, 14, 14, 14, 13, 13, 13, 12, 12, 12, 12),
		u'㇒' : (8, 8, 8, 8, 8, 9, 9, 9, 9, 9, 10, 10, 10, 10, 11, 11, 12, 12, 13, 14, 15, 16, 17, 18, 19, 20, 21, 22, 23, 24, 25, 26),
		u'㇏' : (19, 19, 18, 18, 17, 16, 15, 14, 13, 12, 11, 10, 9, 8, 7, 6, 5, 4, 4, 3, 3, 3, 2, 2, 2, 2, 1, 1, 1, 1, 1, 1),
		u'㇏a' : (20, 20, 20, 20, 20, 19, 19, 19, 19, 19, 18, 18, 18, 18, 17, 17, 16, 16, 15, 14, 14, 13, 12, 12, 11, 10, 10, 9, 8, 7, 6, 5, 4, 3, 3, 3, 3, 2, 2, 2, 2, 2, 1, 1, 1, 1, 1, 1),
		u'㇀' : (8, 8, 8, 8, 8, 9, 9, 9, 9, 9, 10, 10, 10, 10, 11, 11, 12, 12, 13, 14, 15, 16, 17, 18, 19, 20, 21, 22, 23, 24, 25, 26),
		u'㇖' : (8, 8, 8, 8, 8, 8, 8, 9, 9, 9, 9, 9, 9, 10, 10, 11, 11, 12, 12, 13, 13, 14, 14, 15, 15, 16, 16, 16, 16, 15, 15, 14, 13, 12, 11, 11, 11, 11, 11, 11, 11, 11, 10, 10, 10, 10, 9, 9, 10, 10, 11, 12, 13, 13, 14, 14, 15, 15, 16, 16, 17, 17, 18, 18),
		u'㇖a' : (10, 10, 10, 10, 10, 10, 10, 10, 11, 11, 11, 11, 11, 11, 11, 12, 12, 12, 13, 13, 13, 14, 14, 15, 15, 16, 16, 16, 15, 15, 14, 13, 12, 11, 10, 9, 7, 8, 9, 10, 12, 13, 14, 15, 16, 17, 18, 19),
		u'㇖b' : (12, 12, 12, 13, 13, 13, 14, 14, 14, 15, 15, 15, 14, 14, 13, 12, 11, 10, 9, 8, 7, 7, 8, 9, 10, 11, 12, 13, 14, 16, 18, 20),
		u'㇚' : (8, 8, 8, 8, 8, 8, 8, 9, 9, 9, 9, 9, 9, 10, 10, 11, 11, 12, 12, 13, 13, 14, 14, 15, 15, 15, 15, 14, 14, 13, 13, 12, 12, 11, 11, 11, 11, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 20),
		u'㇚a' : (18, 18, 17, 17, 16, 16, 15, 15, 14, 14, 13, 12, 11, 10, 9, 8, 8, 9, 9, 10, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 20),
		u'㇚b' : (17, 16, 15, 14, 13, 12, 11, 10, 9, 8, 7, 6, 8, 10, 12, 14),
		u'㇂' : (9, 9, 9, 9, 9, 9, 10, 10, 10, 10, 10, 10, 11, 11, 11, 11, 12, 12, 13, 14, 14, 15, 15, 16, 16, 15, 15, 14, 13, 12, 11, 10, 9, 8, 7, 6, 5, 4, 4, 5, 7, 9, 13, 15, 17, 19, 21, 23),
		u'㇙' : (8, 8, 8, 8, 8, 8, 8, 9, 9, 9, 9, 9, 9, 10, 10, 11, 12, 12, 13, 14, 14, 15, 15, 14, 14, 13, 13, 12, 12, 11, 11, 10, 10, 9, 9, 9, 8, 8, 8, 8, 9, 9, 9, 9, 10, 10, 10, 10, 11, 11, 12, 13, 13, 14, 15, 15, 16, 17, 17, 18, 19, 19, 20, 20),
		u'㇕' : (9, 9, 9, 9, 9, 10, 10, 10, 10, 10, 11, 11, 11, 11, 11, 12, 12, 12, 13, 13, 13, 14, 14, 14, 15, 15, 15, 14, 14, 13, 13, 13, 12, 12, 12, 11, 11, 11, 11, 11, 11, 11, 10, 10, 10, 10, 9, 9, 10, 10, 11, 12, 13, 13, 14, 14, 15, 15, 16, 15, 14, 13, 12, 11, 11, 11, 11, 10, 10, 10, 10, 10, 10, 10, 10, 10, 9, 9, 9, 9),
		u'㇕a' : (10, 10, 11, 11, 12, 12, 13, 13, 14, 14, 15, 15, 14, 13, 13, 12, 12, 12, 12, 11, 11, 11, 11, 11, 11, 11, 10, 10, 10, 10, 8, 8, 9, 10, 11, 12, 13, 13, 14, 14, 15, 15, 16, 15, 14, 13, 12, 11, 11, 11, 11, 10, 10, 10, 10, 10, 10, 10, 10, 10, 9, 9, 9, 9),
		u'㇕b' : (10, 10, 11, 11, 12, 12, 13, 13, 14, 14, 15, 15, 14, 13, 13, 12, 12, 12, 12, 11, 11, 11, 11, 11, 11, 11, 10, 10, 10, 10, 8, 8, 9, 10, 11, 12, 13, 13, 14, 14, 15, 15, 14, 14, 13, 12, 11, 10),
		u'㇕c' : (9, 9, 9, 9, 9, 10, 10, 10, 10, 10, 11, 11, 11, 11, 11, 12, 12, 12, 13, 13, 13, 14, 14, 14, 15, 15, 15, 14, 14, 13, 13, 13, 12, 12, 12, 11, 11, 11, 11, 11, 11, 11, 10, 10, 10, 10, 9, 9, 10, 10, 11, 12, 13, 13, 14, 14, 15, 15, 14, 13, 12, 11, 10, 10),
		u'㇗' : (8, 8, 8, 8, 8, 8, 8, 9, 9, 9, 9, 9, 9, 10, 10, 11, 11, 12, 12, 13, 13, 14, 14, 15, 15, 16, 16, 16, 16, 15, 15, 14, 13, 12, 11, 11, 11, 11, 11, 11, 11, 11, 10, 10, 10, 9, 9, 10, 10, 10, 11, 11, 11, 12, 12, 12, 13, 13, 12, 12, 12, 11, 11, 11, 10, 10, 10, 10, 9, 9, 9, 9, 9, 9, 8, 8, 8, 8, 8, 8),
		u'㇗a' : (8, 8, 8, 8, 8, 8, 8, 9, 9, 9, 9, 9, 9, 10, 10, 11, 11, 12, 12, 13, 13, 14, 14, 15, 15, 16, 16, 16, 16, 15, 15, 14, 13, 12, 11, 11, 11, 11, 11, 11, 11, 11, 10, 10, 10, 9, 9, 10, 10, 10, 11, 11, 11, 12, 12, 12, 13, 13, 12, 12, 12, 11, 11, 11),
		u'㇛' : (8, 8, 8, 8, 8, 8, 8, 9, 9, 9, 9, 9, 9, 10, 10, 11, 11, 12, 12, 13, 13, 14, 14, 15, 15, 16, 16, 16, 16, 15, 15, 14, 13, 12, 11, 11, 11, 11, 11, 11, 11, 11, 10, 10, 10, 9, 9, 9, 10, 11, 12, 13, 14, 15, 14, 14, 13, 12, 11, 10, 9, 8, 7, 6, 6, 5, 5, 4, 4, 4, 4, 4, 5, 5, 5, 6, 6, 6, 7, 7),
		u'㇜' : (8, 8, 8, 8, 8, 8, 8, 9, 9, 9, 9, 9, 9, 10, 10, 11, 11, 12, 12, 13, 13, 14, 14, 15, 15, 16, 16, 16, 16, 15, 15, 14, 13, 12, 11, 11, 11, 11, 11, 11, 11, 11, 10, 10, 10, 10, 9, 9, 10, 10, 11, 12, 13, 13, 14, 14, 15, 15, 16, 16, 17, 17, 18, 18),
		u'㇇' : (8, 8, 8, 9, 9, 9, 9, 10, 10, 10, 10, 11, 11, 11, 12, 12, 12, 13, 13, 13, 14, 14, 14, 15, 15, 16, 16, 16, 16, 15, 15, 14, 13, 12, 11, 11, 11, 11, 11, 11, 10, 10, 9, 9, 8, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 21, 22, 23, 24, 25, 26),
		u'㇇a' : (10, 10, 10, 10, 10, 10, 10, 10, 11, 11, 11, 11, 11, 11, 11, 12, 12, 12, 13, 13, 13, 14, 14, 15, 15, 16, 16, 16, 15, 15, 14, 13, 12, 11, 10, 9, 7, 8, 9, 10, 12, 13, 14, 15, 16, 17, 18, 19),
		u'㇄' : (8, 8, 8, 8, 8, 8, 8, 9, 9, 9, 9, 9, 9, 10, 10, 11, 11, 12, 12, 13, 13, 14, 14, 15, 15, 15, 15, 14, 14, 13, 13, 12, 12, 12, 11, 11, 11, 11, 11, 10, 10, 10, 9, 9, 9, 9, 9, 9, 9, 9, 10, 10, 10, 11, 11, 12, 12, 13, 13, 14, 14, 13, 13, 13, 12, 12, 12, 11, 11, 10, 10, 10, 10, 10, 9, 9, 9, 9, 8, 8),
		u'㇄a' : (8, 8, 8, 8, 8, 8, 8, 9, 9, 9, 9, 9, 9, 10, 10, 11, 11, 12, 12, 13, 13, 14, 14, 15, 15, 15, 15, 14, 14, 13, 13, 12, 12, 12, 11, 11, 11, 11, 11, 10, 10, 10, 9, 9, 9, 9, 9, 9, 9, 9, 10, 10, 10, 11, 11, 12, 12, 13, 13, 14, 13, 12, 11, 10),
		u'㇆' : (8, 8, 8, 8, 8, 8, 8, 9, 9, 9, 9, 9, 9, 10, 10, 11, 11, 12, 12, 13, 13, 14, 14, 15, 15, 16, 16, 16, 16, 15, 15, 14, 13, 12, 11, 11, 11, 11, 11, 11, 11, 11, 10, 10, 10, 10, 9, 9, 10, 10, 11, 11, 12, 12, 13, 13, 13, 13, 12, 12, 11, 11, 10, 10, 9, 9, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 21, 21),
		u'㇆a' : (10, 10, 11, 11, 12, 13, 14, 15, 15, 16, 16, 16, 16, 15, 15, 14, 13, 12, 11, 11, 11, 11, 11, 11, 11, 11, 10, 10, 10, 10, 9, 9, 10, 10, 11, 11, 12, 12, 13, 13, 13, 13, 12, 12, 11, 11, 10, 10, 9, 9, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 21, 21),
		u'㇆b' : (8, 8, 8, 8, 8, 8, 8, 9, 9, 9, 9, 9, 9, 10, 10, 11, 11, 12, 12, 13, 13, 14, 14, 15, 15, 16, 16, 16, 16, 15, 15, 14, 13, 12, 11, 11, 11, 11, 11, 11, 11, 11, 10, 10, 10, 10, 9, 9, 9, 10, 10, 11, 11, 12, 12, 12, 11, 11, 11, 10, 10, 9, 9, 8, 8, 9, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 21, 22),
		u'㇟' : (8, 8, 8, 8, 8, 8, 8, 9, 9, 9, 9, 9, 9, 10, 10, 11, 11, 12, 12, 13, 13, 14, 14, 15, 15, 15, 15, 14, 14, 14, 13, 13, 13, 12, 12, 12, 12, 12, 12, 12, 12, 12, 12, 12, 11, 11, 11, 10, 9, 8, 7, 6, 5, 4, 5, 7, 9, 11, 13, 15, 17, 19, 21, 23),
		u'㇟a' : (8, 8, 8, 8, 8, 8, 8, 9, 9, 9, 9, 9, 9, 10, 10, 11, 11, 12, 12, 13, 13, 14, 14, 15, 15, 15, 15, 14, 14, 14, 13, 13, 13, 12, 12, 12, 12, 12, 12, 12, 12, 12, 12, 12, 11, 11, 11, 11, 10, 10, 10, 10, 10, 10, 10, 10, 10, 10, 9, 9, 9, 9, 9, 9),
		u'㇟b' : (19, 18, 17, 16, 15, 14, 13, 12, 11, 10, 9, 8, 7, 6, 5, 4, 3, 2, 1, 1, 2, 3, 5, 7, 9, 11, 13, 15, 17, 19, 21, 23),
		u'㇊' : (),
		u'㇉' : (8, 8, 8, 8, 8, 8, 8, 9, 9, 9, 9, 9, 9, 10, 10, 11, 11, 12, 12, 13, 13, 14, 14, 15, 15, 15, 15, 14, 14, 13, 13, 12, 12, 12, 11, 11, 11, 11, 11, 10, 9, 10, 9, 9, 9, 9, 9, 9, 9, 10, 11, 12, 13, 14, 14, 15, 15, 16, 16, 16, 16, 15, 15, 14, 13, 12, 11, 11, 11, 11, 11, 11, 11, 11, 10, 10, 9, 9, 9, 10, 10, 11, 11, 12, 12, 14, 14, 13, 13, 12, 12, 11, 13, 11, 10, 10, 9, 9, 9, 10, 11, 12, 13, 14, 15, 16, 17, 17, 18, 18, 19, 19),
		u'㇋' : (8, 8, 8, 8, 8, 8, 8, 9, 9, 9, 9, 9, 9, 10, 10, 11, 11, 12, 12, 13, 13, 14, 14, 15, 15, 16, 16, 16, 16, 15, 15, 14, 13, 12, 11, 11, 11, 11, 10, 10, 10, 10, 10, 9, 9, 8, 8, 8, 9, 9, 10, 10, 11, 11, 12, 12, 13, 13, 14, 14, 13, 12, 11, 11, 10, 10, 9, 9, 8, 8, 7, 7, 8, 8, 9, 9, 10, 10, 11, 11, 12, 12, 13, 13, 13, 13, 14, 14, 15, 15, 16, 16, 17, 17, 18, 18),
		u'㇌' : (8, 8, 8, 8, 8, 8, 8, 9, 9, 9, 9, 9, 9, 10, 10, 11, 11, 12, 12, 13, 13, 14, 14, 15, 15, 16, 16, 16, 16, 15, 15, 14, 13, 12, 11, 11, 11, 11, 10, 10, 10, 10, 10, 9, 9, 8, 8, 8, 9, 9, 10, 10, 11, 11, 12, 12, 13, 13, 14, 14, 13, 12, 11, 11, 10, 10, 10, 11, 11, 12, 12, 13, 13, 13, 12, 12, 11, 11, 10, 10, 9, 9, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 21, 21),
		u'㇈' : (8, 8, 8, 8, 8, 8, 8, 9, 9, 9, 9, 9, 9, 10, 10, 11, 11, 12, 12, 13, 13, 14, 14, 15, 15, 16, 16, 16, 16, 15, 15, 14, 13, 12, 11, 11, 11, 11, 11, 11, 11, 11, 10, 10, 10, 10, 9, 9, 10, 10, 10, 11, 11, 12, 12, 13, 13, 12, 12, 11, 11, 10, 10, 9, 9, 10, 10, 10, 11, 11, 11, 11, 12, 12, 12, 12, 11, 11, 11, 10, 9, 8, 7, 6, 5, 4, 5, 7, 9, 11, 13, 15, 17, 19, 21, 23),
		u'㇈a' : (8, 8, 8, 8, 8, 8, 8, 9, 9, 9, 9, 9, 9, 10, 10, 11, 11, 12, 12, 13, 13, 14, 14, 15, 15, 16, 16, 16, 16, 15, 15, 14, 13, 12, 11, 11, 11, 11, 11, 11, 11, 11, 10, 10, 10, 10, 9, 9, 10, 11, 12, 13, 13, 14, 14, 15, 15, 16, 16, 15, 14, 13, 12, 11, 10, 9, 8, 7, 6, 5, 4, 5, 7, 9, 13, 15, 17, 19, 21, 23),
		u'㇈b' : (9, 9, 10, 11, 11, 12, 13, 13, 14, 15, 15, 16, 16, 15, 15, 14, 13, 12, 11, 11, 11, 11, 11, 11, 11, 11, 10, 10, 10, 10, 9, 9, 10, 10, 10, 11, 11, 12, 12, 13, 13, 12, 12, 11, 11, 10, 10, 9, 9, 10, 10, 10, 11, 11, 11, 11, 12, 12, 12, 12, 11, 11, 11, 10, 9, 8, 7, 6, 5, 4, 5, 7, 9, 11, 13, 15, 17, 19, 21, 23),
		u'㇅' : (8, 8, 8, 8, 8, 8, 8, 9, 9, 9, 9, 9, 9, 10, 10, 11, 11, 12, 12, 13, 13, 14, 14, 15, 15, 15, 15, 14, 14, 13, 13, 12, 12, 12, 11, 11, 11, 11, 11, 10, 9, 10, 9, 9, 9, 9, 9, 9, 9, 10, 11, 12, 13, 14, 14, 15, 15, 16, 16, 16, 16, 15, 15, 14, 13, 12, 11, 11, 11, 11, 11, 11, 11, 11, 10, 10, 9, 9, 9, 10, 10, 11, 11, 12, 12, 14, 14, 13, 13, 12, 12, 11, 13, 11, 10, 10),


	}

	def __init__(self):
		self.fallback = SimpleStrokeRenderer()
		self.strokesPen = QtGui.QPen()
		self.strokesPen.setWidth(2)
	
	def renderStroke(self, painter, stroke):
		if stroke.stype in self.weights: layout = self.weights[stroke.stype]
		elif stroke.stype[0] in self.weights: layout = self.weights[stroke.stype[0]]
		else:
			self.fallback.renderStroke(painter, stroke)
			return
			
		ppen = QtGui.QPen(self.strokesPen)
		ppen.setCapStyle(QtCore.Qt.RoundCap)
		segmentLength = stroke.qPath.length() / len(layout)
		startPoint = 0.0
		for i in range(len(layout)):
			ppen.setWidthF(self.basicWeight + (3.8 - 0.1 * layout[i]) * self.weightFactor)
			self.renderPartialStroke(painter, ppen, stroke.qPath, startPoint, segmentLength)
			startPoint += segmentLength

	def renderPartialStroke(self, painter, pen, stroke, startPoint, segmentLength):
		painter.save()
		ppen = QtGui.QPen(pen)
		dashes = [ 0.0, startPoint / ppen.widthF(), segmentLength / ppen.widthF(), stroke.length() / ppen.widthF() ]
		ppen.setDashPattern(dashes)
		painter.setPen(ppen)
		painter.drawPath(stroke)
		painter.restore()

class StrokesWidget(QtGui.QWidget):
	def __init__(self, parent = None):
		QtGui.QWidget.__init__(self, parent)
		self.strokesRenderer = FancyStrokeRenderer()

		self.setSizePolicy(QtGui.QSizePolicy.MinimumExpanding, QtGui.QSizePolicy.MinimumExpanding);
	
		self.selectedStrokesPen = QtGui.QPen()
		self.selectedStrokesPen.setWidth(2)
		self.selectedStrokesPen.setColor(QtCore.Qt.red)

		self.boundingPen = QtGui.QPen()
		self.boundingPen.setStyle(QtCore.Qt.DotLine)

	def setKanji(self, kanji):
		self.kanji = kanji
		self.__loadGroup(self.kanji.root)

	def __loadGroup(self, group):
		rect = QtCore.QRectF()
		pwidth = 1.0
		for child in group.childs:
			if isinstance(child, StrokeGr):
				self.__loadGroup(child)
			else:
				child.qPath = svg2Path(child.svg)
				child.boundingRect = child.qPath.controlPointRect().adjusted(-pwidth, -pwidth, pwidth, pwidth)
			rect |= child.boundingRect
		group.boundingRect = rect

	def paintEvent(self, event):
		if not self.kanji: return
		painter = QtGui.QPainter(self)
		painter.setRenderHint(QtGui.QPainter.Antialiasing)
		size = self.size()
		painter.scale(size.width() / 109.0, size.height() / 109.0)

		drawLater = []
		self.__renderGroup(self.kanji.root, painter, drawLater)

		painter.setPen(self.selectedStrokesPen)
		for child in drawLater:
			painter.drawPath(child.qPath)
			# Also draw a tip to indicate the direction
			lastPoint = child.qPath.pointAtPercent(1)
			lastAngle = child.qPath.angleAtPercent(0.95)
			line = QtCore.QLineF(0, 0, 4, 4)
			line.translate(lastPoint)
			line.setAngle(lastAngle + 150)
			painter.drawLine(line)
			line.setAngle(lastAngle - 150)
			painter.drawLine(line)
			

	def __renderGroup(self, group, painter, drawLater):
		for child in group.childs:
			if isinstance(child, StrokeGr):
				self.__renderGroup(child, painter, drawLater)
				if child in self.selection:
					painter.setPen(self.boundingPen)
					painter.drawRect(child.boundingRect)
			else:
				if child in self.selection: drawLater.append(child)
				else:
					self.strokesRenderer.renderStroke(painter, child)

class KanjiStructModel(QtCore.QAbstractItemModel):
	columns = [ 'Element', 'Original', 'Position', 'Phon', 'Part' ]
	StrokeRole = QtCore.Qt.UserRole

	def __init__(self, kanji = None, parent = None):
		QtCore.QAbstractItemModel.__init__(self, parent)
		self.setKanji(kanji)

	def setKanji(self, kanji):
		self.kanji = kanji

	def index(self, row, column, parent):
		if not self.kanji: return QtCore.QModelIndex()

		if not parent.isValid(): return self.createIndex(row, column, kanji.root)
		group = parent.internalPointer().childs[parent.row()]
		if not isinstance(group, StrokeGr) or row >= len(group.childs) or column >= len(KanjiStructModel.columns):
			return QtCore.QModelIndex()
		return self.createIndex(row, column, group)

	def data(self, index, role):
		if not self.kanji or not index.isValid(): return QtCore.QVariant()

		item = index.internalPointer().childs[index.row()]
		if role == KanjiStructModel.StrokeRole:
			return item
		column = index.column()
		if isinstance(item, StrokeGr) and role in (QtCore.Qt.DisplayRole, QtCore.Qt.EditRole):
			if column == 0: return item.element
			elif column == 1: return item.original
			elif column == 2: return item.position
			elif column == 3: return item.phon
			elif column == 4: return item.part
		elif isinstance(item, Stroke) and role in (QtCore.Qt.DisplayRole, QtCore.Qt.EditRole):
			if column == 0: return item.stype
		return QtCore.QVariant()

	def setData(self, index, value, role):
		if not self.kanji or not index.isValid(): return QtCore.QVariant()
		item = index.internalPointer().childs[index.row()]
		column = index.column()
		if isinstance(item, StrokeGr) and role == QtCore.Qt.EditRole:
			if column == 0: item.element = value
			elif column == 1: item.original = value
			elif column == 2: item.position = value
			elif column == 3: item.phon = value
			elif column == 4: item.part = value
			else: return False
			return True
		elif isinstance(item, Stroke) and role == QtCore.Qt.EditRole:
			if column == 0: item.type = value
			else: return False
			return True
		return False

	def headerData(self, section, orientation, role):
		if orientation == QtCore.Qt.Horizontal and role == QtCore.Qt.DisplayRole and section < len(KanjiStructModel.columns):
			return KanjiStructModel.columns[section]
		else: return QtCore.QVariant()

	def flags(self, index):
		if not index.isValid(): return 0
		return QtCore.Qt.ItemIsEnabled | QtCore.Qt.ItemIsSelectable | QtCore.Qt.ItemIsEditable

	def parent(self, index):
		if not self.kanji or not index.isValid(): return QtCore.QModelIndex()
		p = index.internalPointer()
		if p == self.kanji.root: return QtCore.QModelIndex()
		else: return self.createIndex(p.parent.childs.index(p), 0, p.parent)

	def rowCount(self, parent):
		if not self.kanji: return 0
		if not parent.isValid(): return len(kanji.root.childs)
		group = parent.internalPointer().childs[parent.row()]
		if not isinstance(group, StrokeGr): return 0
		return len(group.childs)

	def columnCount(self, parent):
		return len(KanjiStructModel.columns)

class KanjiStructDelegate(QtGui.QStyledItemDelegate):
	positions = [ "", "top", "bottom", "left", "right", "tare" ]
	def __init__(self, parent=None):
		QtGui.QStyledItemDelegate.__init__(self, parent)

	def createEditor(self, parent, option, index):
		item = index.internalPointer().childs[index.row()]
		if isinstance(item, StrokeGr):
			if index.column() in (0, 1, 3):
				ret = QtGui.QStyledItemDelegate.createEditor(self, parent, option, index)
			elif index.column() == 2:
				ret = QtGui.QComboBox(parent)
				ret.addItems(KanjiStructDelegate.positions)
			elif index.column() == 4:
				ret = QtGui.QSpinBox(parent)
				ret.setSpecialValueText("None")
				ret.setMinimum(0)
				ret.setMaximum(10)
		elif isinstance(item, Stroke):
			ret = QtGui.QStyledItemDelegate.createEditor(self, parent, option, index)
		return ret

	def setEditorData(self, editor, index):
		item = index.internalPointer().childs[index.row()]
		if isinstance(item, StrokeGr):
			if index.column() in (0, 1, 3):
				QtGui.QStyledItemDelegate.setEditorData(self, editor, index)
			elif index.column() == 2:
				pos = index.model().data(index, QtCore.Qt.EditRole)
				if pos in KanjiStructDelegate.positions:
					editor.setCurrentIndex(KanjiStructDelegate.positions.index(pos))
			elif index.column() == 4:
				val = index.model().data(index, QtCore.Qt.EditRole)
				editor.setValue(val)
		elif isinstance(item, Stroke):
			QtGui.QStyledItemDelegate.setEditorData(self, editor, index)

	def setModelData(self, editor, model, index):
		if index.column() in (0, 1, 3):
			QtGui.QStyledItemDelegate.setModelData(self, editor, model, index)
		elif index.column() == 2:
			model.setData(index, editor.currentText(), QtCore.Qt.EditRole)
		elif index.column() == 4:
			val = editor.value()
			if val == 0: val = None
			model.setData(index, val, QtCore.Qt.EditRole)

	def updateEditorGeometry(self, editor, option, index):
		editor.setGeometry(option.rect)


class KanjiStructView(QtGui.QTreeView):
	__pyqtSignals__ = ("selectionChanged()")

	def __init__(self, parent=None):
		QtGui.QTreeView.__init__(self, parent)

	def selectionChanged(self, selected, deselected):
		QtGui.QTreeView.selectionChanged(self, selected, deselected)
		self.emit(QtCore.SIGNAL("selectionChanged()"))

class MainWindow(QtGui.QWidget):
	def __init__(self, parent=None):
		QtGui.QWidget.__init__(self, parent)

		self.setWindowTitle('KanjiVG viewer')

		self.canvas = StrokesWidget(self)
		self.canvas.selection = []

		self.kanjiModel = KanjiStructModel(self)
		self.structure = KanjiStructView(self)
		self.structure.setItemDelegate(KanjiStructDelegate())
		self.structure.setModel(self.kanjiModel)

		hLayout = QtGui.QHBoxLayout()
		hLayout.addWidget(self.canvas)
		hLayout.addWidget(self.structure)

		self.setLayout(hLayout)

		self.connect(self.structure, QtCore.SIGNAL('selectionChanged()'), self.onSelectionChanged)

	def setKanji(self, kanji):
		self.canvas.setKanji(kanji)
		self.kanjiModel.setKanji(kanji)

	def onSelectionChanged(self):
		self.canvas.selection = []
		for index in self.structure.selectedIndexes():
			self.canvas.selection.append(index.model().data(index, KanjiStructModel.StrokeRole))
		self.canvas.update()


from createsvgfiles import createSVG

if __name__ == "__main__":
	if len(sys.argv) != 2:
		sys.exit(0)

	kanji = loadKanji(sys.argv[1])

	app = QtGui.QApplication(sys.argv)
	mw = MainWindow()
	mw.resize(500, 400)
	mw.setKanji(kanji)

	mw.show()
	ret = app.exec_()
	createSVG(codecs.open('out.svg', 'w', 'utf-8'), kanji)
	sys.exit(ret)

########NEW FILE########
__FILENAME__ = xmlhandler
#!/usr/bin/python
# -*- coding: utf-8 -*-
#
#  Copyright (C) 2008  Alexandre Courbot
#
#  This program is free software: you can redistribute it and/or modify
#  it under the terms of the GNU General Public License as published by
#  the Free Software Foundation, either version 3 of the License, or
#  (at your option) any later version.
#
#  This program is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU General Public License for more details.
#
#  You should have received a copy of the GNU General Public License
#  along with this program.  If not, see <http://www.gnu.org/licenses/>.

import xml.sax.handler

class BasicHandler(xml.sax.handler.ContentHandler):
	def __init__(self):
		xml.sax.handler.ContentHandler.__init__(self)
		self.elementsTree = []
	
	def currentElement(self):
		return str(self.elementsTree[-1])
		
	def startElement(self, qName, atts):
		self.elementsTree.append(str(qName))
		attrName = "handle_start_" + str(qName)
		if hasattr(self, attrName):
			rfunc = getattr(self, attrName)
			rfunc(atts)
		self.characters = ""
		return True
	
	def endElement(self, qName):
		attrName = "handle_data_" + qName
		if hasattr(self, attrName):
			rfunc = getattr(self, attrName)
			rfunc(self.characters)
		attrName = "handle_end_" + str(qName)
		if hasattr(self, attrName):
			rfunc = getattr(self, attrName)
			rfunc()
		self.elementsTree.pop()
		return True
	
	def characters(self, string):
		self.characters += string
		return True

########NEW FILE########
