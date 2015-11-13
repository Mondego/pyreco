__FILENAME__ = cleanup
#!/usr/bin/python
import xml.etree.ElementTree as ET
import glob
import os
import hashlib
import sys
import datetime

# Variables to keep track of progress
fileschecked = 0
issues = 0
xmlerrors = 0
fileschanged = 0


# Calculate md5 hash to check for changes in file.
def md5_for_file(f, block_size=2 ** 20):
    md5 = hashlib.md5()
    while True:
        data = f.read(block_size)
        if not data:
            break
        md5.update(data)
    return md5.digest()


# Nicely indents the XML output
def indent(elem, level=0):
    i = "\n" + level * "\t"
    if len(elem):
        if not elem.text or not elem.text.strip():
            elem.text = i + "\t"
        if not elem.tail or not elem.tail.strip():
            elem.tail = i
        for elem in elem:
            indent(elem, level + 1)
        if not elem.tail or not elem.tail.strip():
            elem.tail = i
    else:
        if level and (not elem.tail or not elem.tail.strip()):
            elem.tail = i


# Removes empty nodes from the tree
def removeemptytags(elem):
    if elem.text:
        elem.text = elem.text.strip()
    toberemoved = []
    for child in elem:
        if len(child) == 0 and child.text is None and len(child.attrib) == 0:
            toberemoved.append(child)
    for child in toberemoved:
        elem.remove(child)
    for child in elem:
        removeemptytags(child)
        # Convert error to errorminus and errorplus
    if 'ep' in elem.attrib:
        err = elem.attrib['ep']
        del elem.attrib['ep']
        elem.attrib['errorplus'] = err
    if 'em' in elem.attrib:
        err = elem.attrib['em']
        del elem.attrib['em']
        elem.attrib['errorminus'] = err
    if 'error' in elem.attrib:
        err = elem.attrib['error']
        del elem.attrib['error']
        elem.attrib['errorminus'] = err
        elem.attrib['errorplus'] = err

# Check if an unknown tag is present (most likely an indication for a typo)
validtags = [
    "system", "name", "new", "description", "ascendingnode", "discoveryyear",
    "lastupdate", "list", "discoverymethod", "semimajoraxis", "period", "magV", "magJ",
    "magH", "magR", "magB", "magK", "magI", "distance",
    "longitude", "imagedescription", "image", "age", "declination", "rightascension",
    "metallicity", "inclination", "spectraltype", "binary", "planet", "periastron", "star",
    "mass", "eccentricity", "radius", "temperature", "videolink", "transittime", "spinorbitalignment",
    "istransiting"]
validattributes = [
    "error",
    "errorplus",
    "errorminus",
    "unit",
    "upperlimit",
    "lowerlimit",
    "type"]
validdiscoverymethods = ["RV", "transit", "timing", "imaging", "microlensing"]
tagsallowmultiple = ["list", "name", "planet", "star", "binary"]


def checkforvalidtags(elem):
    problematictag = None
    for child in elem:
        _tmp = checkforvalidtags(child)
        if _tmp:
            problematictag = _tmp
    if elem.tag not in validtags:
        problematictag = elem.tag
    for a in elem.attrib:
        if a not in validattributes:
            return a
    return problematictag


# Convert units (makes data entry easier)
def convertunitattrib(elem, attribname, factor):
    if attribname in elem.attrib:
        elem.attrib[attribname] = "%f" % ( float(elem.attrib[attribname]) * factor)


def convertunit(elem, factor):
    print "Converting unit of tag \"" + elem.tag + "\"."
    del elem.attrib['unit']
    if elem.text:
        elem.text = "%f" % (float(elem.text) * factor)
    convertunitattrib(elem, "error", factor)
    convertunitattrib(elem, "errorplus", factor)
    convertunitattrib(elem, "errorminus", factor)
    convertunitattrib(elem, "ep", factor)
    convertunitattrib(elem, "em", factor)
    convertunitattrib(elem, "upperlimit", factor)
    convertunitattrib(elem, "lowerlimit", factor)


def checkForBinaryPlanet(root, criteria, liststring):
    """ Checks if binary planets have been added to corresponding list
    """
    global fileschanged
    planets = root.findall(criteria)
    for planet in planets:
        plists = planet.findall(".//list")
        if liststring not in [plist.text for plist in plists]:
            ET.SubElement(planet, "list").text = liststring
            print "Added '" + filename + "' to list '" + liststring + "'."
            fileschanged += 1


def checkForTransitingPlanets(root):
    """ Checks for transisting planets by first seeing if there is a transittime and then checking the discovery
    method
    """
    global fileschanged
    global issues
    planets = root.findall(".//planet")
    for planet in planets:
        if not planet.findtext('.//istransiting'):
            addtag = 0
            hasTransittime = planet.findtext(".//transittime")
            discoveryMethod = planet.findtext(".//discoverymethod")
            planetRadius = planet.findtext(".//radius")
            if hasTransittime or 'transit' == discoveryMethod:
                addtag = 1
            else:
                if planetRadius:  # only measured from transits, imaging for now
                    planetName = planet.findtext(".//name")
                    excludeList = ('Mercury', 'Venus', 'Earth', 'Mars', 'Jupiter', 'Saturn', 'Uranus', 'Neptune', 'Pluto',
                    'PSR J1719-1438 b',  # radius estimated from  Roche Lobe radius
                    '',
                    )
                    if planetName not in excludeList:
                        if not discoveryMethod == 'imaging':
                            print '{} in {} has a radius but is is missing a istransiting tag'.format(planetName, filename)
                            issues += 1

            if addtag:
                ET.SubElement(planet, "istransiting").text = '1'
                print 'Added istransiting tag to {}'.format(filename)
                fileschanged += 1


# Loop over all files and  create new data
for filename in glob.glob("systems*/*.xml"):
    fileschecked += 1

    # Save md5 for later
    f = open(filename, 'rt')
    md5_orig = md5_for_file(f)

    # Open file
    f = open(filename, 'rt')

    # Try to parse file
    try:
        root = ET.parse(f).getroot()
        planets = root.findall(".//planet")
        stars = root.findall(".//star")
        binaries = root.findall(".//binary")
    except ET.ParseError as error:
        print '{}, {}'.format(filename, error)
        xmlerrors += 1
        issues += 1
        continue
    finally:
        f.close()

    # Find tags with range=1 and convert to default error format
    for elem in root.findall(".//*[@range='1']"):
        fragments = elem.text.split()
        elem.text = fragments[0]
        elem.attrib["errorminus"] = "%f" % (float(fragments[0]) - float(fragments[1]))
        elem.attrib["errorplus"] = "%f" % (float(fragments[2]) - float(fragments[0]))
        del elem.attrib["range"]
        print "Converted range to errorbars in tag '" + elem.tag + "'."

        # Convert units to default units
    for mass in root.findall(".//planet/mass[@unit='me']"):
        convertunit(mass, 0.0031457007)
    for radius in root.findall(".//planet/radius[@unit='re']"):
        convertunit(radius, 0.091130294)
    for angle in root.findall(".//*[@unit='rad']"):
        convertunit(angle, 57.2957795130823)

    # Check lastupdate tag for correctness
    for lastupdate in root.findall(".//planet/lastupdate"):
        la = lastupdate.text.split("/")
        if len(la) != 3 or len(lastupdate.text) != 8:
            print "Date format not following 'yy/mm/dd' convention: " + filename
            issues += 1
        if int(la[0]) + 2000 - datetime.date.today().year > 0 or int(la[1]) > 12 or int(la[2]) > 31:
            print "Date not valid: " + filename
            issues += 1

    # Check that names follow conventions
    if not root.findtext("./name") + ".xml" == os.path.basename(filename):
        print "Name of system not the same as filename: " + filename
        issues += 1
    for obj in planets + stars:
        name = obj.findtext("./name")
        if not name:
            print "Didn't find name tag for object \"" + obj.tag + "\" in file \"" + filename + "\"."
            issues += 1

    # Check if tags are valid and have valid attributes
    problematictag = checkforvalidtags(root)
    if problematictag:
        print "Problematic tag/attribute '" + problematictag + "' found in file \"" + filename + "\"."
        issues += 1
    discoverymethods = root.findall(".//discoverymethod")
    for dm in discoverymethods:
        if not (dm.text in validdiscoverymethods):
            print "Problematic discoverymethod '" + dm.text + "' found in file \"" + filename + "\"."
            issues += 1

    # Check if there are duplicate tags
    for obj in planets + stars + binaries:
        uniquetags = []
        for child in obj:
            if not child.tag in tagsallowmultiple:
                if child.tag in uniquetags:
                    print "Error: Found duplicate tag \"" + child.tag + "\" in file \"" + filename + "\"."
                    issues += 1
                else:
                    uniquetags.append(child.tag)

    # Check binary planet lists
    checkForBinaryPlanet(root, ".//binary/planet", "Planets in binary systems, P-type")
    checkForBinaryPlanet(root, ".//binary/star/planet", "Planets in binary systems, S-type")

    # Check transiting planets
    checkForTransitingPlanets(root)

    # Cleanup XML
    removeemptytags(root)
    indent(root)

    # Write XML to file.
    ET.ElementTree(root).write(filename, encoding="UTF-8", xml_declaration=False)

    # Check for new md5
    f = open(filename, 'rt')
    md5_new = md5_for_file(f)
    if md5_orig != md5_new:
        fileschanged += 1

errorcode = 0
print "Cleanup script finished. %d files checked." % fileschecked
if fileschanged > 0:
    print "%d file(s) modified." % fileschanged
    errorcode = 1

if xmlerrors > 0:
    print "%d XML errors found." % xmlerrors
    errorcode = 2

if issues > 0:
    print "Number of issues: %d (see above)." % issues
    errorcode = 3
else:
    print "No issues found."

sys.exit(errorcode)


########NEW FILE########
__FILENAME__ = generate_systems_kepler
#!/usr/bin/python
# This script generates the systems_kepler data files.
# The input data comes from a csv files from the NASA Exoplanet Archive http://exoplanetarchive.ipac.caltech.edu.
import math,os
import xml.etree.ElementTree as ET, glob

# Delete old data files.
os.system("rm systems_kepler/*.xml")

# Read in csv file. This file is presorted according to the KOI Name (the default file they offer as a download is not). 
# This makes matching systems with multiple planets much easier, but it should be incorporated in this script.
os.system("sort -k3 -t',' cumulative.csv >cumulative.sorted")
csvfile = open("cumulative.sorted","r")

lastsystemname = ""
numcandidates = 0

# Each row corresponds to a planer
for row in csvfile:
	if row[0]=="#" or row[0]=="r": # ignore comments
		continue
	c = row.split(",")
	kepid = c[1]	# Kepler ID (KIC)
	koi = c[2]	# KOI Number
	koi1 = koi.split(".")[0][2:]	# First part of KOI (star)
	koi2 = koi.split(".")[1]	# Second part of KOI (planet)
	systemname = "KOI-"+koi1
	disposition = c[3]		# Status flag. 
	if disposition == "FALSE POSITIVE" or disposition=="NOT DISPOSITIONED":
		continue		# Do not include false positives and planets that have not yet been dispositioned.
	description = ""
	if disposition == "CANDIDATE":	# Add a default description
		description = "This is a Kepler Object of Interest from the Q1-Q12 dataset. It has been flagged as a possible transit event but has not been confirmed to be a planet yet."
	if disposition == "CONFIRMED":
		description = "This is a Kepler Object of Interest from the Q1-Q12 dataset. It has been flagged as a confirmed planet by the Kepler team and might have already appear in a peer reviewed paper."

	# Read in paramaters (not pretty, but works)
	period = c[5]
	perioderrorplus = c[6]
	perioderrorminus = c[7]
	transittime = float(c[8])+2454833.0	# Convert to JD
	transittimeerrorplus = c[9]
	transittimeerrorminus = c[10]
	inclination = c[23]
	inclinationerrorplus = c[24]
	inclinationerrorminus = c[25]
	semia = c[26]
	semiaerrorplus = c[27]
	semiaerrorminus = c[28]
	e = c[29]
	errrorplus = c[30]
	eerrorminus = c[31]
	radius = c[41] 			# earthradii
	radiuserrorplus = c[42] 	# earthradii
	radiuserrorminus = c[43] 	# earthradii
	tempplan = c[44]
	tempplanerrorplus = c[45]
	tempplanerrorminus = c[46]
	tempstar = c[47]
	tempstarerrorplus = c[48]
	tempstarerrorminus = c[49]
	radiusstar = c[53]
	radiusstarerrorplus = c[54]
	radiusstarerrorminus = c[55]
	metallicitystar = c[56]
	metallicitystarerrorplus = c[57]
	metallicitystarerrorminus = c[58]
	massstar = c[59]
	massstarerrorplus = c[60]
	massstarerrorminus = c[61]
	age = c[62]
	ageerrorplus = c[63]
	ageerrorminus = c[64]
	ra = float(c[68])/360.*24. 	# degree
	dec = float(c[69]) 		# degreee
	rastring = "%02d %02d %02d" %(math.floor(ra), math.floor((ra-math.floor(ra))*60.) ,(ra-math.floor(ra)-math.floor((ra-math.floor(ra))*60.)/60.)*60.*60.)
	decstring = "+%02d %02d %02d" %(math.floor(dec), math.floor((dec-math.floor(dec))*60.) ,(dec-math.floor(dec)-math.floor((dec-math.floor(dec))*60.)/60.)*60.*60.)
	keplermag = float(c[70])

	# Calculate a distance estimate based on the luminosity and the stellar temperature.
	if tempstar:
		luminosity = float(radiusstar)*float(radiusstar)*float(tempstar)*float(tempstar)*float(tempstar)*float(tempstar)/5778./5778./5778./5778.

		M = -2.5*math.log10(luminosity)+4.74

		mu = keplermag - M
		distance = math.pow(10.,mu/5.+1.)


	# If this is the first planet in the system, setup the system and star tags.
	if systemname != lastsystemname:
		root = ET.Element("system")

		ET.SubElement(root,"name").text = systemname
		ET.SubElement(root,"rightascension").text = rastring
		ET.SubElement(root,"declination").text = decstring
		if tempstar:
			ET.SubElement(root,"distance").text =  "%.2f" %distance

		star = ET.SubElement(root,"star")
		ET.SubElement(star,"name").text = systemname

		if tempstar:
			element = ET.SubElement(star,"temperature")
			element.text = tempstar
			element.attrib["errorplus"] = tempstarerrorplus
			element.attrib["errorminus"] = tempstarerrorminus[1:]

		if radiusstar:
			element = ET.SubElement(star,"radius")
			element.text = radiusstar
			element.attrib["errorplus"] = radiusstarerrorplus
			element.attrib["errorminus"] = radiusstarerrorminus[1:]

		if massstar:
			element = ET.SubElement(star,"mass")
			element.text = massstar
			element.attrib["errorplus"] = massstarerrorplus
			element.attrib["errorminus"] = massstarerrorminus[1:]

		if age:
			element = ET.SubElement(star,"age")
			element.text =  age
			element.attrib["errorplus"] = ageerrorplus
			element.attrib["errorminus"] = ageerrorminus[1:]
		
		if metallicitystar:
			element = ET.SubElement(star,"metallicity")
			element.text =  metallicitystar
			element.attrib["errorplus"] = metallicitystarerrorplus
			element.attrib["errorminus"] = metallicitystarerrorminus[1:]

	# Setup planet tags
	planet = ET.SubElement(star,"planet")
	planetname = systemname+" "+chr(int(koi2)+97) 		# Converts "KOI-10.01" to "KOI-10 b", etc.
	ET.SubElement(planet,"name").text = planetname
	ET.SubElement(planet,"name").text = systemname+" "+koi2
	
	if radius:
		element = ET.SubElement(planet,"radius")
		element.text = "%.5f" % (float(radius)*0.09113029)	# Convert to Jupiter radii
		if radiuserrorplus and radiuserrorminus:
			element.attrib["errorplus"] = "%.5f" % (float(radiuserrorplus)*0.09113029)
			element.attrib["errorminus"] = "%.5f" % (float(radiuserrorminus[1:])*0.09113029)

	if period:
		element = ET.SubElement(planet,"period")
		element.text = period
		element.attrib["errorplus"] = perioderrorplus
		element.attrib["errorminus"] = perioderrorminus[1:]
	
	if transittime:
		element = ET.SubElement(planet,"transittime")
		element.text = "%.7f" % transittime
		if transittimeerrorplus and transittimeerrorminus:
			element.attrib["errorplus"] = "%.7f" % float(transittimeerrorplus)
			element.attrib["errorminus"] = "%.7f" % float (transittimeerrorminus[1:])

	if semia:
		element = ET.SubElement(planet,"semimajoraxis")
		element.text = semia
		if semiaerrorplus and semiaerrorminus:
			element.attrib["errorplus"] = semiaerrorplus
			element.attrib["errorminus"] = semiaerrorminus[1:]
	
	if e and float(e)!=0.:
		element = ET.SubElement(planet,"eccentricity")
		element.text = e
		if eerrorplus and eerrorminus:
			element.attrib["errorplus"] = eerrorplus
			element.attrib["errorminus"] = eerrorminus[1:]
	
	if tempplan:
		element = ET.SubElement(planet,"temperature")
		element.text = tempplan
		if tempplanerrorplus and tempplanerrorminus:
			element.attrib["errorplus"] = tempplanerrorplus
			element.attrib["errorminus"] = tempplanerrorminus[1:]
	
	ET.SubElement(planet,"list").text = "Kepler Objects of Interest"
	ET.SubElement(planet,"description").text = description
	
	tree = ET.ElementTree(root)
	tree.write("./systems_kepler/"+systemname+".xml")
	lastsystemname = systemname
	numcandidates += 1

print "Number of candidates: %d"%numcandidates

########NEW FILE########
__FILENAME__ = simbad_extractor
'''
From Marc-Antoine Martinod
No particular license or rights, you can change it as you feel, just be honest. :)
For python puritain, sorry if this script is not "pythonic".
'''


'''
This script picks up the magnitudes and the spectral type from Simbad website.
*How to use it:
    ***In variable "path", put the path of the repo where you have the XMLs.
    ***Run the script

*Structure:
    ***HTMLparser class to extract information from a webpage.
    ***Two main functions : magnitude : pick up magnitudes from Simbad
                            spectralType : pick up spectral type from Simbad, it is currently commented because I don't need to run it at the moment.
    ***A list generator function : create a file containing the name of the XML files in "path".

*Logs:
    ***Log_planet.txt has all files for which there was a 404 error. This file is not reset
    when the script is rerun. It works for both functions.

*Troubleshooting:
    ***If Simbad don't recognize this name, either you search manually or you create a list with the
    other names for a system (Kepler, 2MASS...) and you rename the file with this name to let the script
    writing in it.

*Improvements:
    ***You can improve this script by a multi-name recognition :for a system, if there is a 404 error on simbad web page
    the script can try another name picked up in the XMLs and try it.
    This would avoid to make a manual reasearch or rename the files, recreate a list and rerun the script.

    ***There can be a problem with binaries system. Simbad always has only SP (spectral type) and mag for one star (don't know which)
    or the whole system but if this information exists for each star of a binary system, this script doesn't deal with it.

    ***Adapt it for other kind of extraction or for other website.
'''

from HTMLParser import HTMLParser
import urllib
import re
import os
import glob
import time

class MyHTMLParser(HTMLParser):#HTML parser to get the information from the webpage
    def handle_starttag(self, tag, attrs): #get start tag and may store its attributes
        global boolean, dictio, data2
        if boolean == 1:# and tag == "a":
            dictio.append(data2)
            boolean = 0

    def handle_endtag(self, tag):
        pass

    def handle_data(self, data):
        global data2, boolean, spectre
        if re.findall("[A-Z] *\d*\.?\d*? *\[+.+\]", data):#Search magnitude
            data2 = data
            data2 = data2.replace("\n", "").replace(" ","")
            boolean = 1

#set magnitude values in XML file
def magnitude(dic, filename, path):
    #The idea is to read the file to have a big string then concatenate the magnitudes then rewrite the whole file
    if os.path.isfile(path+"/"+filename+".xml"):
        with open(path+"/"+filename+".xml","r") as readable:
            read_file = readable.read()

            tabulation = ""
            try:
                #positionning the magnitudes in the file
                if "</magV>" in read_file:
                    elt_index = read_file.index("</magV>")
                    elt_len = len("</magV>")
                    if "<binary>" in read_file:
                        tabulation = "\t"
                elif "<binary>" in read_file:
                    elt_index = read_file.index("<binary>")
                    elt_len = len("<binary>")
                else:
                    elt_index = read_file.index("<star>")
                    elt_len = len("<star>")
            except ValueError: # ie free floating planet (no star or parent)
                print '{} failed (no parent object tag'.format(filename)
                return False


        with open(path+"/"+filename+".xml", "w") as writable:#Write mag in the file
            dic2 = dic
            dic2.sort()

            magJ = ""
            magH = ""
            magK = ""
            magV = ""
            magB = ""
            magR = ""
            magI = ""

            for key in dic2:#concatenate magnitudes in the string from XML
                expr = key
                if not "[~]" in expr:
                    sigma = re.findall('\[+.+\]', expr)
                    sigma = str(sigma[0].replace('[','').replace(']',''))
                else:
                    sigma = ""

                expr = re.sub('\[+.+\]', '', expr)#Remove uncertainty from string

                expr2 = re.sub('[A-Z]', '', expr)#Remove letters from string, just mag left.
                if "J" in expr and not "magJ" in read_file:
                    if sigma != "":
                        magJ = "\n"+tabulation+"\t\t<magJ errorminus=\""+sigma+"\" errorplus=\""+sigma+"\">"+expr2+"</magJ>"
                    else:
                        magJ = "\n"+tabulation+"\t\t<magJ>"+expr2+"</magJ>"
                elif "H" in expr and not "magH" in read_file:
                    if sigma != "":
                        magH = "\n"+tabulation+"\t\t<magH errorminus=\""+sigma+"\" errorplus=\""+sigma+"\">"+expr2+"</magH>"
                    else:
                        magH = "\n"+tabulation+"\t\t<magH>"+expr2+"</magH>"
                elif "K" in expr and not "magK" in read_file:
                    if sigma != "":
                        magK = "\n"+tabulation+"\t\t<magK errorminus=\""+sigma+"\" errorplus=\""+sigma+"\">"+expr2+"</magK>"
                    else:
                        magK = "\n"+tabulation+"\t\t<magK>"+expr2+"</magK>"
                elif "V" in expr and not "magV" in read_file:
                    if sigma != "":
                        magV = "\n"+tabulation+"\t\t<magV errorminus=\""+sigma+"\" errorplus=\""+sigma+"\">"+expr2+"</magV>"
                    else:
                        magV = "\n"+tabulation+"\t\t<magV>"+expr2+"</magV>"
                elif "B" in expr and not "magB" in read_file:
                    if sigma != "":
                        magB = "\n"+tabulation+"\t\t<magB errorminus=\""+sigma+"\" errorplus=\""+sigma+"\">"+expr2+"</magB>"
                    else:
                        magB = "\n"+tabulation+"\t\t<magB>"+expr2+"</magB>"
                elif "R" in expr and not "magR" in read_file:
                    if sigma != "":
                        magR = "\n"+tabulation+"\t\t<magR errorminus=\""+sigma+"\" errorplus=\""+sigma+"\">"+expr2+"</magR>"
                    else:
                        magR = "\n"+tabulation+"\t\t<magR>"+expr2+"</magR>"
                elif "I" in expr and not "magI" in read_file:
                    if sigma != "":
                        magI = "\n"+tabulation+"\t\t<magI errorminus=\""+sigma+"\" errorplus=\""+sigma+"\">"+expr2+"</magI>"
                    else:
                        magI = "\n"+tabulation+"\t\t<magI>"+expr2+"</magI>"

            #check if mag already exists or not on simbad
            if magJ != "" or magH != "" or magK != "" or magV != "" or magB != "" or magR != "" or magI != "":
                print elt,"\t mag done."
            else:
                print elt," Mag error or already exists."

            read_file = read_file[0:elt_index+elt_len]+magB+magV+magR+magI+magJ+magH+magK+read_file[elt_index+elt_len:]
            writable.write(read_file)

    else:
        print filename," not found."

#set spectral type in the XML file.
def spectralType(spectre, filename, path):
    #Check if the file exists
    if os.path.isfile(path+"/"+filename+".xml"):
            with open(path+"/"+filename+".xml","r") as readable:
                read_file = readable.read()
                tabulation = ""
                back_line = ""

                #Positionning of the information in the file.
                try:
                    if not "<binary>" in read_file:
                        if not "<spectraltype>" in read_file:
                            elt_index = read_file.index("<star>")
                            elt_len = len("<star>")
                            back_line = "\n"

                            #Writing the SP (spectral type) in the file
                            with open(path+"/"+filename+".xml","w") as writable:
                                    spectre = back_line+"\t\t"+tabulation+"<spectraltype>"+spectre+"</spectraltype>"
                                    read_file = read_file[0:elt_index+elt_len]+spectre+read_file[elt_index+elt_len:]
                                    writable.write(read_file)
                                    print filename+"\tSP done."
                        else:
                            print filename, " has already a spectral type."
                    else:
                        print filename, " is a binary system."
                        log.write(filename+"\t:\tbinary system\n")

                except ValueError: # ie free floating planet (no star or parent)
                    print '{} failed (no parent object tag - probably)'.format(filename)
    else:
        print filename, "not found."

#Another script exists for that. Splitting the two functions lets me to control
#the list is in correct format and won't bring any troubles.
#However, as it is a copy/paste of the script, it should work.
def generateList(path):
    planet_list = open("list.txt", "w")
    for filename in glob.glob(path+"/*.xml"):
        # Open file
        name = os.path.split(filename)
        name = name[1]
        name = name.replace(".xml","")
        planet_list.write(name+"\n")
    planet_list.close()



#****************************MAIN*********************************
parser = MyHTMLParser()

path = "systems_kepler"
generateList(path)
system_list = open("list.txt","r") #list of the systems to process
line = system_list.readlines()
line = [elt.replace('\n','') for elt in line]

log = open("log_planet.log", "a")#log 404 web error and binary systems error
log.write("\n*****"+time.strftime("%A %d %B %Y %H:%M:%S")+"*****\n")

for elt in line:#read all the list of systems and run the parser class and the magnitude function for each one
    dictio = []
    boolean = 0
    data2 = ""
    spectre = ""

    planet = elt
    try:
        code_source = urllib.urlopen('http://simbad.u-strasbg.fr/simbad/sim-basic?Ident='+planet).read()
    except IOError:
        print('Lookup failed - sleeping for 10 seconds')
        time.sleep(10)

        try:
            code_source = urllib.urlopen('http://simbad.u-strasbg.fr/simbad/sim-basic?Ident='+planet).read()
        except IOError:
            print('Lookup failed again for {} - skipping'.format(planet))
            log.write('Lookup failed for {}'.format(planet))

    #First check its existence on simbad
    if not re.findall("Identifier not found in the database", code_source):
        parser.feed(code_source)
        magnitude(dictio, planet, path)
        #if re.search('Spectral type:( *<.*?>\n){5}\w*/?\w*', code_source):
        #    extraction_spectre = re.search('Spectral type:( *<.*?>\n){5}\w*/?\w*', code_source).group(0)
        #    spectre = re.search('(?<=<TT>\n)\w*/?\w*', extraction_spectre).group(0)
        #    spectralType(spectre, planet, path)
        #else:
        #    print elt, " has no spectral type."
        #    log.write(elt+"\t:\tno spectral type\n")
        #
    else:
        print planet,"\t:\t404 page not found"
        log.write(planet+" 404 page not found\n")

log.close()
system_list.close()

########NEW FILE########
