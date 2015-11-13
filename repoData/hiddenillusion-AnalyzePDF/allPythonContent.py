__FILENAME__ = AnalyzePDF
#!/usr/bin/env python

"""
Analyzes PDF files by looking at their characteristics in order to add some intelligence into the determination of them being malicious or benign.

Usage:
$ AnalyzePDF.py [-h] [-m MOVE] [-y YARARULES] Path

Produces a high level overview of a PDF to quickly determine if further
analysis is needed based on it's characteristics

positional arguments:
  Path                  Path to directory/file(s) to be scanned

optional arguments:
  -h, --help            show this help message and exit
  -m MOVE, --move MOVE  Directory to move files triggering YARA hits to
  -y YARARULES, --yararules YARARULES
                        Path to YARA rules. Rules should contain a weighted
                        score in the metadata section. (i.e. weight = 3)

example: python AnalyzePDF.py -m tmp/badness -y foo/pdf.yara bar/getsome.pdf            
"""

# AnalyzePDF.py was created by Glenn P. Edwards Jr.
#	 	http://hiddenillusion.blogspot.com
# 				@hiddenillusion
# Version 0.2 
# Date: 10-11-2012
# Requirements:
#	- Python 2.x
#	- YARA (http://plusvic.github.io/yara/)
#	- pdfid (http://blog.didierstevens.com/programs/pdf-tools/)
# Optional:	
#	* This script will work without these but may miss some conditions to evaluate based on the missing data they would provide (i.e. - # of Pages) *
#	- pdfinfo (www.foolabs.com/xpdf/download.html)
#	- a "weight" field within the YARA's rule meta should be added to help in the final evaluation
#		i.e. - rule pdf_example {meta: weight = 3 strings: $s = "evil" condition: $s}
# To-Do:
#	- suppress pdfid's output log
#	- be able to print out which conditions it met in the rules

import os
import subprocess
import shutil
import sys
import datetime
import time
import argparse
import binascii
import re
import zipfile
import shutil 
import hashlib
from decimal import Decimal

"""
Chose to _import_ PDFiD instead of just using subprocess to spawn it so it can be statically compiled for use on Windows.  
If you don't have it installed on your system, you can just download it and have it in the same directory as this script.
"""
try:
    import pdfid 
except ImportError:
    print "[!] PDFiD not installed"
    sys.exit()
try:
    import yara
except ImportError:
    print "[!] Yara not installed"
    sys.exit()	
	
# Initialize the list(s) where PDF attribs will be added to
counter = []
page_counter = []
# Initialize the YARA scoring count
yscore = []
ydir = False

# Misc. formatting
trailer = ("=" * 35)
filler = ("-" * 35)

parser = argparse.ArgumentParser(description='Produces a high level overview of a PDF to quickly determine if further analysis is needed based on it\'s characteristics')
parser.add_argument('-m','--move', help='Directory to move files triggering YARA hits to', required=False)
parser.add_argument('-y','--yararules', help='Path to YARA rules.  Rules should contain a weighted score in the metadata section. (i.e. weight = 3)', required=False)
parser.add_argument('Path', help='Path to directory/file(s) to be scanned')
args = vars(parser.parse_args())

# Verify supplied path exists or die
if not os.path.exists(args['Path']):
    print "[!] The supplied path does not exist"
    sys.exit()
		
# Configure YARA rules
if args['yararules']:
    rules = args['yararules']
else:
    rules = '/usr/local/etc/capabilities.yara' # REMnux location
	
if not os.path.exists(rules):
    print "[!] Correct path to YARA rules?"
    sys.exit()
else:
    try:	
        r = yara.compile(rules)
        if args['move']:
            ydir = args['move']
    except Exception, msg:
        print "[!] YARA compile error: %s" % msg
        sys.exit()

def main():
    # Set the path to file(s)
    ploc = args['Path']
    if os.path.isfile(ploc):
        fileID(ploc)
    elif os.path.isdir(ploc):
        pwalk(ploc)	

# Quote idea credited to: https://github.com/marpaia/jadPY ... useful for Windows, what can I say...
def q(s):
	quote = "\""
	s = quote + s + quote
	return s

def sha256(pdf):
    try:
        f = open(pdf, "rb")
        data = f.read()
        sha256 =  hashlib.sha256(data).hexdigest()
        f.close()
    except Exception, msg:
        print msg

    return sha256
	
def fileID(pdf):
    """
	Generally the PDF header will be within the first (4) bytes but since the PDF specs say it 
	can be within the first (1024) bytes I'd rather check for atleast (1) instance 
	of it within that large range.  This limits the chance of the PDF using a header 
	evasion trick and then won't end up getting analyzed.  This evasion behavior could later 
	be detected with a YARA rule.
    """
    f = open(pdf,'rb')
    s = f.read(1024)
    if '\x25\x50\x44\x46' in s:
        print "\n" + trailer
        print "[+] Analyzing: %s" % pdf
        print filler
        print "[-] Sha256: %s" % sha256(pdf)
        info(pdf)
    elif os.path.isdir(pdf): pwalk(pdf)
    f.close()
	
def pwalk(ploc):
    # Recursivly walk the supplied path and process files accordingly
    for root, dirs, files in os.walk(ploc):
        for name in files: 
            f = os.path.join(root, name)
            fileID(f)
		
def info(pdf):
    command = "pdfinfo " + q(pdf)
    try:
        p = subprocess.Popen(command,shell=True,stdout=subprocess.PIPE,stderr=subprocess.PIPE)
        #for line in p.stdout:
        #    if re.match('Pages:\s+(0|1)$', line):
        #        counter.append("pages")
        #         print "[-] (1) page PDF"  
        for line in p.stderr:
            if re.search('Unterminated hex string|Loop in Pages tree|Illegal digit in hex char in name', line):
                counter.append("sketchy")
                print "[-] Sketchyness detected" 
            elif re.search('Unexpected end of file in flate stream|End of file inside array', line):
                counter.append("eof")
                print "[-] EoF problem" 
            elif re.search('Couldn\'t find trailer dictionary', line):
                counter.append("trailer")			
            elif re.search('Invalid XRef entry|No valid XRef size in trailer|Invalid XRef entry|Couldn\'t read xref table', line):
                counter.append("xref")
                print "[-] Invalid XREF"
                break
    except Exception, msg:
        print "[!] pdfinfo error: %s" % msg
        pass

    id(pdf)

def id(pdf):
    try:
        # (dir, allNames, extraData, disarm, force), force)
        command = pdfid.PDFiD2String(pdfid.PDFiD(pdf, True, True, False, True), True)
        extra = True
    except Exception:
        # I've observed some files raising errors with the 'extraData' switch
        command = pdfid.PDFiD2String(pdfid.PDFiD(pdf, True, False, False, True), True)
        print "[!] PDFiD couldn\'t parse extra data"
        extra = False

    for line in command.split('\n'):
        count = re.split(r'[\s]+', line)
        if "PDF Header" in line and not re.match('%PDF-1\.\d', count[3]):
            counter.append("header")
            print "[-] Invalid version number : \"%s\"" % count[3]
        elif "/Page " in line:
            page_counter.append(count[2])
        elif "/Pages " in line:
            page_counter.append(count[2])
        elif "/JS " in line and not re.match('0', count[2]):
            counter.append("js")
            print "[-] JavaScript count.......: %s" % count[2]
            if count[2] > "1":
                counter.append("mucho_javascript")
                print "\t[*] That\'s a lot of js ..."
        elif "/AcroForm " in line and not re.match('0', count[2]):
            counter.append("acroform")
            print "[-] AcroForm...............: %s" % count[2]
        elif "/AA " in line and not re.match('0', count[2]):
            counter.append("aa")
            print "[-] Additional Action......: %s" % count[2]
        elif "/OpenAction " in line and not re.match('0', count[2]):
            counter.append("oa")
            print "[-] Open Action............: %s" % count[2]
        elif "/Launch " in line and not re.match('0', count[2]):
            counter.append("launch")
            print "[-] Launch Action..........: %s" % count[2]
        elif "/EmbeddedFiles " in line and not re.match('0', count[2]):
            counter.append("embed")
            print "[-] Embedded File..........: %s" % count[2]
        #elif "trailer" in line and not re.match('0|1', count[2]):
        #    print "[-] Trailer count..........: %s" % count[2]
        #    print "\t[*] Multiple versions detected"
        elif "Total entropy:" in line:
            tentropy = count[3]		
            print "[-] Total Entropy..........: %7s" % count[3]
        elif "Entropy inside streams:" in line:
            ientropy = count[4]
            print "[-] Entropy inside streams : %7s" % count[4]
        elif "Entropy outside streams:" in line:
            oentropy = count[4]	
            print "[-] Entropy outside streams: %7s" % count[4]
    """
	Entropy levels:
	0 = orderly, 8 = random
	ASCII text file = ~2/4
	ZIP archive = ~ 7/8
    PDF Malicious
            - total   : 6.3
            - inside  : 6.6
            - outside : 4.9
    PDF Benign
            - total   : 6.7
            - inside  : 7.2
            - outside : 5.1
	Determine if Total Entropy & Entropy Inside Stream are significantly different than Entropy Outside Streams -> i.e. might indicate a payload w/ long, uncompressed NOP-sled
	ref = http://blog.didierstevens.com/2009/05/14/malformed-pdf-documents
    """		
    if not extra == False:	
        te_long = Decimal(tentropy)
        te_short = Decimal(tentropy[0:3])
        ie_long = Decimal(ientropy)	
        ie_short = Decimal(ientropy[0:3])	
        oe_long = Decimal(oentropy)	
        oe_short = Decimal(oentropy[0:3])	
        ent = (te_short + ie_short) / 2
        # I know 'entropy' might get added twice to the counter (doesn't matter) but I wanted to separate these to be alerted on them individually
        togo = (8 - oe_long) # Don't want to apply this if it goes over the max of 8
        if togo > 2:
            if oe_long + 2 > te_long:
                counter.append("entropy")		
                print "\t[*] Entropy of outside stream is questionable:"
                print "\t[-] Outside (%s) +2 (%s) > Total (%s)" % (oe_long,oe_long +2,te_long)
        elif oe_long > te_long:
            counter.append("entropy")		
            print "\t[*] Entropy of outside stream is questionable:"
            print "\t[-] Outside (%s) > Total (%s)" % (oe_long,te_long)
        if str(te_short) <= "2.0" or str(ie_short) <= "2.0":
            counter.append("entropy")		
            print "\t[*] LOW entropy detected:"
            print "\t[-] Total (%s) or Inside (%s) <= 2.0" % (te_short,ie_short)

    # Process the /Page(s) results here just to make sure they were both read
    if re.match('0', page_counter[0]) and re.match('0', page_counter[1]):
        counter.append("page")
        print "[-] Page count suspicious:"  
        print "\t[*] Both /Page (%s) and /Pages (%s) = 0" % (page_counter[0],page_counter[1])
    elif re.match('0', page_counter[0]) and not re.match('0', page_counter[1]):
        counter.append("page")
        print "[-] Page count suspicious, no individual pages defined:"  
        print "\t[*] /Page = (%s) , /Pages = (%s)" % (page_counter[0],page_counter[1])
    elif re.match('1$', page_counter[0]):
        counter.append("page")
        print "[-] (1) page PDF"  
            
    yarascan(pdf)

def yarascan(pdf):
    try:
        ymatch = r.match(pdf)
        if len(ymatch):
            print "[-] YARA hit(s): %s" % ymatch
            for rule in ymatch:
                meta = rule.meta
                for key, value in meta.iteritems():
                    # If the YARA rule has a weight in it's metadata then parse that for later calculation
                    if "weight" in key:
                      yscore.append(value)
                if not ydir == False:
                    print "[-] Moving malicious file to:",ydir
                    # This will move the file if _any_ YARA rule triggers...which might trick you if the
                    # rule that triggers on it doesn't have a weight or is displayed in the output
                    if not os.path.exists(ydir):
                        os.makedirs(ydir)
                    try:
                        shutil.move(pdf, ydir)
                    except Exception, msg:
                        continue
    except Exception, msg:
        print msg
    
    eval(counter)
	
def eval(counter):
    """ 
    Evaluate the discovered contents of the PDF and assign a severity rating
    based on the conditions configured below.

    Rating system: 0 (benign), >=2 (sketchy), >=3 (medium), >=5 (high)
    """
    print filler	
    ytotal = sum(yscore)
    print "[-] Total YARA score.......: %s" % ytotal
    sev = 0

    # Below are various combinations used to add some intelligence and help evaluate if a file is malicious or benign.  
    # This is where you can add your own thoughts or modify existing checks.
	
    # HIGH
    if "page" in counter and "launch" in counter and "js" in counter: sev = 5
    elif "page" in counter and "xref" in counter: sev += 5
    elif "page" in counter and "aa" in counter and "js" in counter: sev += 5
    elif "page" in counter and "oa" in counter and "js" in counter: sev += 5

    # MEDIUM
    if "header" in counter and "xref" in counter: sev += 3
    elif "header" in counter and "js" in counter and "page" in counter: sev += 3
    elif "header" in counter and "launch" in counter and "page" in counter: sev += 3
    elif "header" in counter and "aa" in counter and "page" in counter: sev += 3

    if "page" in counter and "mucho_javascript" in counter: sev += 3
    elif "page" in counter and "acroform" in counter and "embed" in counter: sev += 3
    elif "page" in counter and "acroform" in counter and "js" in counter: sev += 3

    if "entropy" in counter and "page" in counter: sev += 3	
    elif "entropy" in counter and "aa" in counter: sev += 3	
    elif "entropy" in counter and "oa" in counter: sev += 3	
    elif "entropy" in counter and "js" in counter: sev += 3	

    if "oa" in counter and "js" in counter: sev += 3
    if "aa" in counter and "mucho_javascript" in counter: sev += 3

    # Heuristically sketchy
    if "page" in counter and "js" in counter: sev += 2
    if "sketchy" in counter and "page" in counter: sev += 2
    elif "sketchy" in counter and "aa" in counter: sev += 2
    elif "sketchy" in counter and "oa" in counter: sev += 2
    elif "sketchy" in counter and "launch" in  counter: sev += 2
    elif "sketchy" in counter and "eof" in counter: sev += 1

    if "page" in counter and "aa" in counter: sev += 1
    if "page" in counter and "header" in counter: sev += 1	
    if "header" in counter and "embed" in counter: sev += 1
	
    print "[-] Total severity score...: %s" % sev
    sev = (ytotal + sev)
    print "[-] Overall score..........: %s" % sev
    
    if sev >= 5: print trailer + "\n[!] HIGH probability of being malicious"
    elif sev >= 3: print trailer + "\n[!] MEDIUM probability of being malicious"
    elif sev >= 2: print trailer + "\n[!] Heuristically sketchy"
    elif sev >= 0: print trailer + "\n[-] Scanning didn't determine anything warranting suspicion"

    # Clear out the scores to start fresh for the next analysis
    del counter[:]
    del page_counter[:]	
    del yscore[:]

if __name__ == "__main__":
	main()  

########NEW FILE########
__FILENAME__ = pdf_attib_parser
#    Created by Glenn P. Edwards Jr.
#	http://hiddenillusion.blogspot.com
# 			@hiddenillusion
# Version 0.1
# Date: 10-11-2012
#
# Requirements:
# 	- pdfid (http://blog.didierstevens.com/programs/pdf-tools/)
#	- pdfinfo (http://poppler.freedesktop.org/)

import os
import subprocess
import shutil
import sys
import datetime
import time
import argparse
import binascii
import re
import zipfile
import shutil 
import hashlib
import pdfid 

dup_counter = []

def main():
    # Get program args
    parser = argparse.ArgumentParser(description='Runs pdfid/pdfinfo on PDF files.')
    parser.add_argument('Path', help='Path to directory/file(s) to be scanned')
    args = vars(parser.parse_args())	

    # Verify supplied path exists or die
    if not os.path.exists(args['Path']):
        print "[!] The supplied path does not exist"
        sys.exit()

    # Set the path to file(s)
    ploc = args['Path']
    if os.path.isfile(ploc):
        fileID(ploc)
    elif os.path.isdir(ploc):
        pwalk(ploc)	

# Quote idea credited to: https://github.com/marpaia/jadPY ... helps on Windows...		
def q(s):
	quote = "\""
	s = quote + s + quote
	return s

def sha256(pdf):
    try:
        f = open(pdf, "rb")
        data = f.read()
        sha256 =  hashlib.sha256(data).hexdigest()
        f.close()
    except Exception, msg:
        print msg
		
    return sha256
    
	
def fileID(pdf):
    """
	Generally this will within the first 4 bytes but since the PDF specs say it 
	can be within the first 1024 bytes I'd rather check for atleast (1) instance 
	of it within that large range.  This limits the chance of the PDF using a header 
	evasion trick and then won't end up getting analyzed.  This behavior could later 
	be detected with a YARA rule.
    """
    f = open(pdf,'rb')
    s = f.read(1024)
    if '\x25\x50\x44\x46' in s:
        print ("=" * 20)	
        print "[+] Analyzing: %s" % pdf
        print "[-] Sha256: %s" % sha256(pdf)
        print ("=" * 20)	
        info(pdf)
    elif os.path.isdir(pdf): pwalk(pdf)
    f.close()
	
def pwalk(ploc):
    # Recursivly walk the supplied path and process files accordingly
    for root, dirs, files in os.walk(ploc):
        for name in files: 
            f = os.path.join(root, name)
            fileID(f)
		
def info(pdf):
    command = "pdfinfo " + q(pdf)
    try:
        p = subprocess.Popen(command,shell=True,stdout=subprocess.PIPE,stderr=subprocess.PIPE)
        for line in p.stdout:
            if "PDF version:" in line:
                print line			
        for line in p.stderr:
            if re.search('Unexpected end of file in flate stream|End of file inside array', line):
                print "[-] EoF problem" 
            elif re.search('Unterminated hex string|Loop in Pages tree|Illegal digit in hex char in name', line):
                print "[-] Sketchyness detected" 
            elif re.search('Invalid XRef entry|No valid XRef size in trailer|Invalid XRef entry|Couldn\'t read xref table', line):
                print "[-] Invalid XREF"
                break
    except Exception, msg:
        print "[!] pdfinfo error: %s" % msg
        pass

    id(pdf)

def id(pdf):
    try:
        #(dir, allNames, extraData, disarm, force), force)
        command = pdfid.PDFiD2String(pdfid.PDFiD(pdf, True, True, False, True), True)
        print command		
    except Exception:
        # I've observed some files raising errors with the 'extraData' switch
        command = pdfid.PDFiD2String(pdfid.PDFiD(pdf, True, False, False, True), True)
        print "[!] PDFiD couldn\'t parse extra data"	
        print command		

if __name__ == "__main__":
	main()  

########NEW FILE########
__FILENAME__ = pdf_entropy_parser
#    Created by Glenn P. Edwards Jr.
#	http://hiddenillusion.blogspot.com
# 			@hiddenillusion
# Version 0.1
# Date: 10-11-2012

"""
To-Do:
    - Parse on individual base to determine frequency of inside vs. outside , total vs. outside etc.
"""

import os
import subprocess
import shutil
import sys
import datetime
import time
import argparse
import binascii
import re
import zipfile
import shutil 
import hashlib
import collections
from decimal import Decimal

combined = []
all_entropy = []
out_higher = []
combined_less = []
tentropy = []
te = []
ientropy = []
ie = []
oentropy = []
oe = []

def main():
    parser = argparse.ArgumentParser(description='Extracts entropy stats from PDFiD output')
    parser.add_argument('Path', help='Path to directory/file(s) to be scanned')
    args = vars(parser.parse_args())

    # Verify supplied path exists or die
    if not os.path.exists(args['Path']):
        print "[!] The supplied path does not exist"
        sys.exit()
	
    file = args['Path']   
	
    find_entropy(file)
		
def find_entropy(file):    
    #print "[+] Processing: %s" % file
    f = open(file,'r')
    for line in f:	
        num = re.split(r'[\s]+', line)        
        if "Total entropy:" in line:
            all_entropy.append(line)					
        elif "Entropy inside" in line:
            all_entropy.append(line)			
        elif "Entropy outside" in line:
            all_entropy.append(line)					

    all_o_over_t = []
    all_o_over_t_count = 0
    all_low = []
    all_low_count = 0
    all_o_over_i_count = 0
    #all_o_over_ti = []
    all_o_over_t2 = []
    all_o_over_t2_count = 0
    for e in all_entropy:	
        c = len(all_entropy) /3
        lines = [line for line in all_entropy]
        for l in lines:		
            l = l.strip()					
            line = re.split('[\s]+', l)	
            if "Total" in line:		
                tentropy.append(line[2])			
                combined.append(line[2])
            elif "inside" in line:
                ientropy.append(line[5])			
                combined.append(line[5])
            elif "outside" in line:
                oentropy.append(line[4])
                combined.append(line[4])
            if len(combined) == 3:
                print "[i] combined: %s" % combined
                print "[i] 0 : %s " % combined[0]
                print "[i] 1 : %s " % combined[1]
                print "[i] 2 : %s " % combined[2]
                tindiv = Decimal(combined[0])
                iindiv = Decimal(combined[1])
                oindiv = Decimal(combined[2])
                if str(oindiv)[0:3] > str(tindiv)[0:3]: 
                    add0 = (oindiv, tindiv)
                    all_o_over_t.append(add0)
                    all_o_over_t_count += 1
                if str(oindiv)[0:3] > str(iindiv)[0:3]: 
                    #add1 = (oindiv, iindiv)
                    #all_o_over_i.append(add1)
                    all_o_over_i_count += 1
                if oindiv > tindiv + 2: 
                    add2 = (oindiv, tindiv)
                    all_o_over_t2.append(add2)
                    all_o_over_t2_count += 1
                if str(tindiv)[0:3] <= "2.0" or str(iindiv)[0:3] <= "2.0": 
                    add3 = (tindiv, iindiv)
                    all_low.append(add3)
                    all_low_count += 1
                del combined[:]	
        eval(tentropy, ientropy, oentropy, all_o_over_t, all_o_over_t_count, all_o_over_i_count, all_o_over_t2, all_o_over_t2_count, all_low, all_low_count) 

def eval(tentropy, ientropy, oentropy, all_o_over_t, all_o_over_t_count, all_o_over_i_count, all_o_over_t2, all_o_over_t2_count, all_low, all_low_count):      
    # Total Stats
    print "=" * 25
    print "[+] Total Stats"
    print "=" * 25
    for t in tentropy:
        t = t.strip()					
        te.append(t[0:3])

    tcount = collections.Counter(te)
    print "[-] Total count (%s)" % len(te)
    print "[-] Entropy | Occurence"
    print "-" * 25
    tt = 0
    tavg_high = []
    tavg_eq = []
    tavg_low = []
    for val, occur in tcount.most_common():
        tt += Decimal(val)
    tavg = str(tt / len(tcount))[0:3]
    for val, occur in tcount.most_common():
        print "%11s : %s" % (val, occur)
        if val > tavg: tavg_high.append(occur)
        elif val == tavg: tavg_eq.append(occur)
        elif val < tavg: tavg_low.append(occur)
    print "-" * 25
    print "%11s\n" % tt

    twhole = 0
    for val in tcount.elements():
        twhole += Decimal(val)
    twhole_avg = str(twhole / len(te))[0:3]

    # Inside Stats
    print "=" * 25
    print "[+] Inside Stats"
    print "=" * 25
    for i in ientropy:
        i = i.strip()					
        ie.append(i[0:3])

    icount = collections.Counter(ie)
    print "[-] Inside count (%s)" % len(ie)
    print "[-] Entropy | Occurence"
    print "-" * 25
    it = 0
    iavg_high = []
    iavg_eq = []
    iavg_low = []
    for val, occur in icount.most_common():
        it += Decimal(val)
    iavg = str(it / len(icount))[0:3]
    for val, occur in icount.most_common():
        print "%11s : %s" % (val, occur)
        if val > iavg: iavg_high.append(occur)
        elif val == iavg: iavg_eq.append(occur)
        elif val < iavg: iavg_low.append(occur)
    print "-" * 25
    print "%11s\n" % it

    iwhole = 0
    for val in icount.elements():
        iwhole += Decimal(val)
    iwhole_avg = str(iwhole / len(ie))[0:3]

    # Outside Stats
    print "=" * 25
    print "[+] Outside Stats"
    print "=" * 25
    for o in oentropy:
        o = o.strip()					
        oe.append(o[0:3])

    ocount = collections.Counter(oe)
    print "[-] Outside count (%s)" % len(oe)
    print "[-] Entropy | Occurence"
    print "-" * 25
    ot = 0
    oavg_high = []
    oavg_eq = []
    oavg_low = []
    for val, occur in ocount.most_common():
        ot += Decimal(val)
    oavg = str(ot / len(ocount))[0:3]
    for val, occur in ocount.most_common():
        print "%11s : %s" % (val, occur)
        if val > oavg: oavg_high.append(occur)
        elif val == oavg: oavg_eq.append(occur)
        elif val < oavg: oavg_low.append(occur)
    print "-" * 25
    print "%11s\n" % ot

    owhole = 0
    for val in ocount.elements():
        owhole += Decimal(val)
    owhole_avg = str(owhole / len(oe))[0:3]
 
    # Do work...
    print "=" * 30
    print "[+] Total unique   | Total whole"
    print "\t" + "-" * 16
    print "\tAvg.: %4s | %4s" % (tavg,twhole_avg)
    print "\tHigher: %s" % sum(tavg_high)
    print "\tExact: %4s" % sum(tavg_eq)
    print "\tLower: %4s" % sum(tavg_low)
    print "\t" + "-" * 16
    print "\tOverall: %7s" % sum(tavg_high + tavg_eq + tavg_low)
    print "[+] Inside unique  | Inside whole"
    print "\t" + "-" * 16
    print "\tAvg.: %4s | %4s" % (iavg,iwhole_avg)
    print "\tHigher: %s" % sum(iavg_high)
    print "\tExact: %4s" % sum(iavg_eq)
    print "\tLower: %4s" % sum(iavg_low)
    print "\t" + "-" * 16
    print "\tOverall: %7s" % sum(iavg_high + iavg_eq + iavg_low)
    print "[+] Outside unique | Outside whole"
    print "\t" + "-" * 16
    print "\tAvg.: %4s | %4s" % (oavg,owhole_avg)
    print "\tHigher: %s" % sum(oavg_high)
    print "\tExact: %4s" % sum(oavg_eq)
    print "\tLower: %4s" % sum(oavg_low)
    print "\t" + "-" * 16
    print "\tOverall: %7s" % sum(oavg_high + oavg_eq + oavg_low)
    print "\t" + "-" * 16
    all_low_perc = 100 * float(all_low_count) / float((len(te)))
    print "[+] LOW Total or Inside: %s (%s%%)" % (all_low_count,str(all_low_perc)[0:4])
    print "[-] Total   | Inside"
    all_l = collections.Counter(all_low)
    for t, i in all_l: 
        t = Decimal(t)
        i = Decimal(i)
        print "%11s or %s" % (str(t)[0:3],str(i)[0:3])
    all_o_over_t_perc = 100 * float(all_o_over_t_count) / float((len(te)))
    print "[+] Outside > Total: %6s (%s%%)" % (all_o_over_t_count,str(all_o_over_t_perc)[0:4])
    print "[-] Outside | Total"
    all_t = collections.Counter(all_o_over_t)
    for o, t in all_t: 
        o = Decimal(o)
        t = Decimal(t)
        print "%11s vs. %s" % (str(o)[0:3],str(t)[0:3])
    all_o_over_t2_perc = 100 * float(all_o_over_t2_count) / float((len(te)))
    print "[+] Outside > Total +2: %3s (%s%%)" % (all_o_over_t2_count,str(all_o_over_t2_perc)[0:4])
    all_t2 = collections.Counter(all_o_over_t2)
    for o, t in all_t2: 
        o = Decimal(o)
        t = Decimal(t)
        print "%11s vs. %s (+2)" % (str(o)[0:3],str(t)[0:3])
    all_o_over_i_perc = 100 * float(all_o_over_i_count) / float((len(te)))
    print "[+] Outside > Inside: %5s (%s%%)" % (all_o_over_i_count,str(all_o_over_i_perc)[0:4])

    del all_entropy[:]	
    del out_higher[:]
    del combined_less[:]		
	
if __name__ == "__main__":
	main()  		

########NEW FILE########
__FILENAME__ = pdf_identifier
#    Created by Glenn P. Edwards Jr.
#	http://hiddenillusion.blogspot.com
# 			@hiddenillusion
# Version 0.1
# Date: 10-11-2012

import os
import sys
import argparse
import binascii
import shutil 
import hashlib

def main():
    # Get program args
    parser = argparse.ArgumentParser(description='Looks for PDF files and copies them to specified directory named as their Sha256 hash')
    parser.add_argument('-d','--dir', help='Directory to move the identified PDF files to', required=True)	
    parser.add_argument('Path', help='Path to directory/file(s) to be scanned')
    args = vars(parser.parse_args())	

    # Verify supplied path(s) exists or die
    if not os.path.exists(args['Path']):
        print "[!] The supplied path does not exist"
        sys.exit()

    global mdir	
    mdir = args['dir']	
    if not os.path.exists(args['dir']):	
        try:			
            os.makedirs(mdir)		
        except Exception, msg:
            print msg
            sys.exit()			
		
    # Set the path to file(s)
    ploc = args['Path']
    if os.path.isfile(ploc):
        fileID(ploc)
    elif os.path.isdir(ploc):
        pwalk(ploc)	

def sha256(pdf):
    try:
        f = open(pdf, "rb")
        data = f.read()
        sha256 =  hashlib.sha256(data).hexdigest()
        f.close()
    except Exception, msg:
        print msg
		
    return sha256
    
	
def fileID(pdf):
    """
	Generally this will within the first 4 bytes but since the PDF specs say it 
	can be within the first 1024 bytes I'd rather check for atleast (1) instance 
	of it within that large range.  This limits the chance of the PDF using a header 
	evasion trick and then won't end up getting analyzed.  This behavior could later 
	be detected with a YARA rule.
    """
    f = open(pdf,'rb')
    s = f.read(1024)
    if '\x25\x50\x44\x46' in s:
        print ("=" * 20)	
        print "[+] Found: %s" % pdf
        print "[-] Sha256: %s" % sha256(pdf)	
        mover(pdf)
    elif os.path.isdir(pdf): pwalk(pdf)
    f.close()
	
def pwalk(ploc):
    # Recursivly walk the supplied path and process files accordingly
    for root, dirs, files in os.walk(ploc):
        for name in files: 
            f = os.path.join(root, name)
            fileID(f)

def mover(pdf):
    output_dir = os.path.join(mdir,sha256(pdf))
    dir = os.path.abspath(output_dir)

	# If the output directory already exists, increment its name
    count = 0
    if os.path.exists(output_dir):
        while os.path.exists(output_dir):
            count += 1
            output_dir = dir + '.' + str(count)
            continue
    try:
        shutil.copyfile(pdf, output_dir)
    except Exception, msg:
        print msg	

if __name__ == "__main__":
	main()  

########NEW FILE########
__FILENAME__ = pdf_keyword_parser
#    Created by Glenn P. Edwards Jr.
#	http://hiddenillusion.blogspot.com
# 			@hiddenillusion
# Version 0.1
# Date: 10-11-2012

import os
import subprocess
import sys
import argparse
import re
import collections
from decimal import Decimal

# Initialize the list(s) where PDF attribs will be added to
keys= []

def main():
    parser = argparse.ArgumentParser(description='Takes pdfid/pdfinfo output and produces a summary to show the most common and least common keywords/attributes with their values/counts')
    parser.add_argument('Path', help='Path to pdfid/pdfinfo output file(s)')
    args = vars(parser.parse_args())

    # Verify supplied path exists or die
    if not os.path.exists(args['Path']):
        print "[!] The supplied path does not exist"
        sys.exit()

	# Set the path to file(s)
    f = args['Path']
    if os.path.isfile(f):
        details(f)
    elif os.path.isdir(f):
        fwalk(f)	
		
def fwalk(floc):
    # Recursivly walk the supplied path and process files accordingly
    for root, dirs, files in os.walk(floc):
        for name in files: 
            fname = os.path.join(root, name)
            details(fname)
	
def details(f):
    l = open(f).read()
    for line in l.split('\n'):
        if not re.findall('===', line) and not re.findall('Analyzing:', line) and not re.findall('Sha256:', line) and not re.findall('[eE]ntropy', line) and not re.findall('PDFiD 0.0', line):
           keys.append(line)
    print "\n[+] PDF keywords/attributes"
    print "[-] Sorted by highest count"
    print "   Count | Keyword/Attribute"
    print "-" * 40
    c = collections.Counter(keys)
    for key,count in c.most_common():
        print "%8s | %s" % (count, key)

    print "[-] Sorted per keywords/attributes"
    print "   Count | Keyword/Attribute"
    print "-" * 40
    for key,count in sorted(c.most_common()):
        print "%8s | %s" % (count, key)

#    for e in sorted(keys):
#        print e


if __name__ == "__main__":
	main()  

########NEW FILE########
__FILENAME__ = pdfid
#!/usr/bin/env python

__description__ = 'Tool to test a PDF file'
__author__ = 'Didier Stevens'
__version__ = '0.0.12'
__date__ = '2012/03/03'
# slight mods by @hiddenillusion
"""

Tool to test a PDF file

Source code put in public domain by Didier Stevens, no Copyright
https://DidierStevens.com
Use at your own risk

History:
  2009/03/27: start
  2009/03/28: scan option
  2009/03/29: V0.0.2: xml output
  2009/03/31: V0.0.3: /ObjStm suggested by Dion
  2009/04/02: V0.0.4: added ErrorMessage
  2009/04/20: V0.0.5: added Dates
  2009/04/21: V0.0.6: added entropy
  2009/04/22: added disarm
  2009/04/29: finished disarm
  2009/05/13: V0.0.7: added cPDFEOF
  2009/07/24: V0.0.8: added /AcroForm and /RichMedia, simplified %PDF header regex, extra date format (without TZ)
  2009/07/25: added input redirection, option --force
  2009/10/13: V0.0.9: added detection for CVE-2009-3459; added /RichMedia to disarm
  2010/01/11: V0.0.10: relaxed %PDF header checking
  2010/04/28: V0.0.11: added /Launch
  2010/09/21: V0.0.12: fixed cntCharsAfterLastEOF bug; fix by Russell Holloway
  2011/12/29: updated for Python 3, added keyword /EmbeddedFile
  2012/03/03: added PDFiD2JSON; coded by Brandon Dixon

Todo:
  - update XML example (entropy, EOF)
  - code review, cleanup
"""

import optparse
import os
import re
import xml.dom.minidom
import traceback
import math
import operator
import os.path
import sys
import json

#Convert 2 Bytes If Python 3
def C2BIP3(string):
    if sys.version_info[0] > 2:
        return bytes([ord(x) for x in string])
    else:
        return string

class cBinaryFile:
    def __init__(self, file):
        self.file = file
        if file == "":
            self.infile = sys.stdin
        else:
            self.infile = open(file, 'rb')
        self.ungetted = []

    def byte(self):
        if len(self.ungetted) != 0:
            return self.ungetted.pop()
        inbyte = self.infile.read(1)
        if not inbyte:
            self.infile.close()
            return None
        return ord(inbyte)

    def bytes(self, size):
        if size <= len(self.ungetted):
            result = self.ungetted[0:size]
            del self.ungetted[0:size]
            return result
        inbytes = self.infile.read(size - len(self.ungetted))
        if inbytes == '':
            self.infile.close()
        if type(inbytes) == type(''):
            result = self.ungetted + [ord(b) for b in inbytes]
        else:
            result = self.ungetted + [b for b in inbytes]
        self.ungetted = []
        return result

    def unget(self, byte):
        self.ungetted.append(byte)

    def ungets(self, bytes):
        bytes.reverse()
        self.ungetted.extend(bytes)

class cPDFDate:
    def __init__(self):
        self.state = 0

    def parse(self, char):
        if char == 'D':
            self.state = 1
            return None
        elif self.state == 1:
            if char == ':':
                self.state = 2
                self.digits1 = ''
            else:
                self.state = 0
            return None
        elif self.state == 2:
            if len(self.digits1) < 14:
                if char >= '0' and char <= '9':
                    self.digits1 += char
                    return None
                else:
                    self.state = 0
                    return None
            elif char == '+' or char == '-' or char == 'Z':
                self.state = 3
                self.digits2 = ''
                self.TZ = char
                return None
            elif char == '"':
                self.state = 0
                self.date = 'D:' + self.digits1
                return self.date
            elif char < '0' or char > '9':
                self.state = 0
                self.date = 'D:' + self.digits1
                return self.date
            else:
                self.state = 0
                return None
        elif self.state == 3:
            if len(self.digits2) < 2:
                if char >= '0' and char <= '9':
                    self.digits2 += char
                    return None
                else:
                    self.state = 0
                    return None
            elif len(self.digits2) == 2:
                if char == "'":
                    self.digits2 += char
                    return None
                else:
                    self.state = 0
                    return None
            elif len(self.digits2) < 5:
                if char >= '0' and char <= '9':
                    self.digits2 += char
                    if len(self.digits2) == 5:
                        self.state = 0
                        self.date = 'D:' + self.digits1 + self.TZ + self.digits2
                        return self.date
                    else:
                        return None
                else:
                    self.state = 0
                    return None

def fEntropy(countByte, countTotal):
    x = float(countByte) / countTotal
    if x > 0:
        return - x * math.log(x, 2)
    else:
        return 0.0

class cEntropy:
    def __init__(self):
        self.allBucket = [0 for i in range(0, 256)]
        self.streamBucket = [0 for i in range(0, 256)]

    def add(self, byte, insideStream):
        self.allBucket[byte] += 1
        if insideStream:
            self.streamBucket[byte] += 1

    def removeInsideStream(self, byte):
        if self.streamBucket[byte] > 0:
            self.streamBucket[byte] -= 1

    def calc(self):
        self.nonStreamBucket = map(operator.sub, self.allBucket, self.streamBucket)
        allCount = sum(self.allBucket)
        streamCount = sum(self.streamBucket)
        nonStreamCount = sum(self.nonStreamBucket)
        return (allCount, sum(map(lambda x: fEntropy(x, allCount), self.allBucket)), streamCount, sum(map(lambda x: fEntropy(x, streamCount), self.streamBucket)), nonStreamCount, sum(map(lambda x: fEntropy(x, nonStreamCount), self.nonStreamBucket)))

class cPDFEOF:
    def __init__(self):
        self.token = ''
        self.cntEOFs = 0
        self.cntCharsAfterLastEOF = 0 # fixed

    def parse(self, char):
        if self.cntEOFs > 0:
            self.cntCharsAfterLastEOF += 1
        if self.token == '' and char == '%':
            self.token += char
            return
        elif self.token == '%' and char == '%':
            self.token += char
            return
        elif self.token == '%%' and char == 'E':
            self.token += char
            return
        elif self.token == '%%E' and char == 'O':
            self.token += char
            return
        elif self.token == '%%EO' and char == 'F':
            self.token += char
            return
        elif self.token == '%%EOF' and (char == '\n' or char == '\r' or char == ' ' or char == '\t'):
            self.cntEOFs += 1
            self.cntCharsAfterLastEOF = 0
            if char == '\n':
                self.token = ''
            else:
                self.token += char
            return
        elif self.token == '%%EOF\r':
            if char == '\n':
                self.cntCharsAfterLastEOF = 0
            self.token = ''
        else:
            self.token = ''

def FindPDFHeaderRelaxed(oBinaryFile):
    bytes = oBinaryFile.bytes(1024)
    index = ''.join([chr(byte) for byte in bytes]).find('%PDF')
    if index == -1:
        oBinaryFile.ungets(bytes)
        return ([], None)
    for endHeader in range(index + 4, index + 4 + 10):
        if bytes[endHeader] == 10 or bytes[endHeader] == 13:
            break
    oBinaryFile.ungets(bytes[endHeader:])
    return (bytes[0:endHeader], ''.join([chr(byte) for byte in bytes[index:endHeader]]))

def Hexcode2String(char):
    if type(char) == int:
        return '#%02x' % char
    else:
        return char

def SwapCase(char):
    if type(char) == int:
        return ord(chr(char).swapcase())
    else:
        return char.swapcase()

def HexcodeName2String(hexcodeName):
    return ''.join(map(Hexcode2String, hexcodeName))

def SwapName(wordExact):
    return map(SwapCase, wordExact)

def UpdateWords(word, wordExact, slash, words, hexcode, allNames, lastName, insideStream, oEntropy, fOut):
    if word != '':
        if slash + word in words:
            words[slash + word][0] += 1
            if hexcode:
                words[slash + word][1] += 1
        elif slash == '/' and allNames:
            words[slash + word] = [1, 0]
            if hexcode:
                words[slash + word][1] += 1
        if slash == '/':
            lastName = slash + word
        if slash == '':
            if word == 'stream':
                insideStream = True
            if word == 'endstream':
                if insideStream == True and oEntropy != None:
                    for char in 'endstream':
                        oEntropy.removeInsideStream(ord(char))
                insideStream = False
        if fOut != None:
            if slash == '/' and '/' + word in ('/JS', '/JavaScript', '/AA', '/OpenAction', '/JBIG2Decode', '/RichMedia', '/Launch'):
                wordExactSwapped = HexcodeName2String(SwapName(wordExact))
                fOut.write(C2BIP3(wordExactSwapped))
                print('/%s -> /%s' % (HexcodeName2String(wordExact), wordExactSwapped))
            else:
                fOut.write(C2BIP3(HexcodeName2String(wordExact)))
    return ('', [], False, lastName, insideStream)

class cCVE_2009_3459:
    def __init__(self):
        self.count = 0

    def Check(self, lastName, word):
        if (lastName == '/Colors' and word.isdigit() and int(word) > 2^24): # decided to alert when the number of colors is expressed with more than 3 bytes
            self.count += 1

def PDFiD(file, allNames=False, extraData=False, disarm=False, force=False):
    """Example of XML output:
    <PDFiD ErrorOccured="False" ErrorMessage="" Filename="test.pdf" Header="%PDF-1.1" IsPDF="True" Version="0.0.4" Entropy="4.28">
            <Keywords>
                    <Keyword Count="7" HexcodeCount="0" Name="obj"/>
                    <Keyword Count="7" HexcodeCount="0" Name="endobj"/>
                    <Keyword Count="1" HexcodeCount="0" Name="stream"/>
                    <Keyword Count="1" HexcodeCount="0" Name="endstream"/>
                    <Keyword Count="1" HexcodeCount="0" Name="xref"/>
                    <Keyword Count="1" HexcodeCount="0" Name="trailer"/>
                    <Keyword Count="1" HexcodeCount="0" Name="startxref"/>
                    <Keyword Count="1" HexcodeCount="0" Name="/Page"/>
                    <Keyword Count="0" HexcodeCount="0" Name="/Encrypt"/>
                    <Keyword Count="1" HexcodeCount="0" Name="/JS"/>
                    <Keyword Count="1" HexcodeCount="0" Name="/JavaScript"/>
                    <Keyword Count="0" HexcodeCount="0" Name="/AA"/>
                    <Keyword Count="1" HexcodeCount="0" Name="/OpenAction"/>
                    <Keyword Count="0" HexcodeCount="0" Name="/JBIG2Decode"/>
            </Keywords>
            <Dates>
                    <Date Value="D:20090128132916+01'00" Name="/ModDate"/>
            </Dates>
    </PDFiD>
    """

    word = ''
    wordExact = []
    hexcode = False
    lastName = ''
    insideStream = False
    keywords = ('obj',
                'endobj',
                'stream',
                'endstream',
                'xref',
                'trailer',
                'startxref',
                '/Page',
                '/Encrypt',
                '/ObjStm',
                '/JS',
                '/JavaScript',
                '/AA',
                '/OpenAction',
                '/AcroForm',
                '/JBIG2Decode',
                '/RichMedia',
                '/Launch',
                '/EmbeddedFile',
               )
    words = {}
    dates = []
    for keyword in keywords:
        words[keyword] = [0, 0]
    slash = ''
    xmlDoc = xml.dom.minidom.getDOMImplementation().createDocument(None, "PDFiD", None)
    att = xmlDoc.createAttribute('Version')
    att.nodeValue = __version__
    xmlDoc.documentElement.setAttributeNode(att)
    att = xmlDoc.createAttribute('Filename')
    att.nodeValue = file
    xmlDoc.documentElement.setAttributeNode(att)
    attErrorOccured = xmlDoc.createAttribute('ErrorOccured')
    xmlDoc.documentElement.setAttributeNode(attErrorOccured)
    attErrorOccured.nodeValue = 'False'
    attErrorMessage = xmlDoc.createAttribute('ErrorMessage')
    xmlDoc.documentElement.setAttributeNode(attErrorMessage)
    attErrorMessage.nodeValue = ''

    oPDFDate = None
    oEntropy = None
    oPDFEOF = None
    oCVE_2009_3459 = cCVE_2009_3459()
    try:
        attIsPDF = xmlDoc.createAttribute('IsPDF')
        xmlDoc.documentElement.setAttributeNode(attIsPDF)
        oBinaryFile = cBinaryFile(file)
        if extraData:
            oPDFDate = cPDFDate()
            oEntropy = cEntropy()
            oPDFEOF = cPDFEOF()
        (bytesHeader, pdfHeader) = FindPDFHeaderRelaxed(oBinaryFile)
        if disarm:
            (pathfile, extension) = os.path.splitext(file)
            fOut = open(pathfile + '.disarmed' + extension, 'wb')
            for byteHeader in bytesHeader:
                fOut.write(C2BIP3(chr(byteHeader)))
        else:
            fOut = None
        if oEntropy != None:
            for byteHeader in bytesHeader:
                oEntropy.add(byteHeader, insideStream)
        if pdfHeader == None and not force:
            attIsPDF.nodeValue = 'False'
            return xmlDoc
        else:
            if pdfHeader == None:
                attIsPDF.nodeValue = 'False'
                pdfHeader = ''
            else:
                attIsPDF.nodeValue = 'True'
            att = xmlDoc.createAttribute('Header')
            att.nodeValue = repr(pdfHeader[0:10]).strip("'")
            xmlDoc.documentElement.setAttributeNode(att)
        byte = oBinaryFile.byte()
        while byte != None:
            char = chr(byte)
            charUpper = char.upper()
            if charUpper >= 'A' and charUpper <= 'Z' or charUpper >= '0' and charUpper <= '9':
                word += char
                wordExact.append(char)
            elif slash == '/' and char == '#':
                d1 = oBinaryFile.byte()
                if d1 != None:
                    d2 = oBinaryFile.byte()
                    if d2 != None and (chr(d1) >= '0' and chr(d1) <= '9' or chr(d1).upper() >= 'A' and chr(d1).upper() <= 'F') and (chr(d2) >= '0' and chr(d2) <= '9' or chr(d2).upper() >= 'A' and chr(d2).upper() <= 'F'):
                        word += chr(int(chr(d1) + chr(d2), 16))
                        wordExact.append(int(chr(d1) + chr(d2), 16))
                        hexcode = True
                        if oEntropy != None:
                            oEntropy.add(d1, insideStream)
                            oEntropy.add(d2, insideStream)
                        if oPDFEOF != None:
                            oPDFEOF.parse(d1)
                            oPDFEOF.parse(d2)
                    else:
                        oBinaryFile.unget(d2)
                        oBinaryFile.unget(d1)
                        (word, wordExact, hexcode, lastName, insideStream) = UpdateWords(word, wordExact, slash, words, hexcode, allNames, lastName, insideStream, oEntropy, fOut)
                        if disarm:
                            fOut.write(C2BIP3(char))
                else:
                    oBinaryFile.unget(d1)
                    (word, wordExact, hexcode, lastName, insideStream) = UpdateWords(word, wordExact, slash, words, hexcode, allNames, lastName, insideStream, oEntropy, fOut)
                    if disarm:
                        fOut.write(C2BIP3(char))
            else:
                oCVE_2009_3459.Check(lastName, word)

                (word, wordExact, hexcode, lastName, insideStream) = UpdateWords(word, wordExact, slash, words, hexcode, allNames, lastName, insideStream, oEntropy, fOut)
                if char == '/':
                    slash = '/'
                else:
                    slash = ''
                if disarm:
                    fOut.write(C2BIP3(char))

            if oPDFDate != None and oPDFDate.parse(char) != None:
                dates.append([oPDFDate.date, lastName])

            if oEntropy != None:
                oEntropy.add(byte, insideStream)

            if oPDFEOF != None:
                oPDFEOF.parse(char)

            byte = oBinaryFile.byte()
        (word, wordExact, hexcode, lastName, insideStream) = UpdateWords(word, wordExact, slash, words, hexcode, allNames, lastName, insideStream, oEntropy, fOut)

        # check to see if file ended with %%EOF.  If so, we can reset charsAfterLastEOF and add one to EOF count.  This is never performed in
        # the parse function because it never gets called due to hitting the end of file.
        if byte == None and oPDFEOF != None:
            if oPDFEOF.token == "%%EOF":
                oPDFEOF.cntEOFs += 1
                oPDFEOF.cntCharsAfterLastEOF = 0
                oPDFEOF.token = ''

    except:
        attErrorOccured.nodeValue = 'True'
        attErrorMessage.nodeValue = traceback.format_exc()

    if disarm:
        fOut.close()

    attEntropyAll = xmlDoc.createAttribute('TotalEntropy')
    xmlDoc.documentElement.setAttributeNode(attEntropyAll)
    attCountAll = xmlDoc.createAttribute('TotalCount')
    xmlDoc.documentElement.setAttributeNode(attCountAll)
    attEntropyStream = xmlDoc.createAttribute('StreamEntropy')
    xmlDoc.documentElement.setAttributeNode(attEntropyStream)
    attCountStream = xmlDoc.createAttribute('StreamCount')
    xmlDoc.documentElement.setAttributeNode(attCountStream)
    attEntropyNonStream = xmlDoc.createAttribute('NonStreamEntropy')
    xmlDoc.documentElement.setAttributeNode(attEntropyNonStream)
    attCountNonStream = xmlDoc.createAttribute('NonStreamCount')
    xmlDoc.documentElement.setAttributeNode(attCountNonStream)
    if oEntropy != None:
        (countAll, entropyAll , countStream, entropyStream, countNonStream, entropyNonStream) = oEntropy.calc()
        attEntropyAll.nodeValue = '%f' % entropyAll
        attCountAll.nodeValue = '%d' % countAll
        attEntropyStream.nodeValue = '%f' % entropyStream
        attCountStream.nodeValue = '%d' % countStream
        attEntropyNonStream.nodeValue = '%f' % entropyNonStream
        attCountNonStream.nodeValue = '%d' % countNonStream
    else:
        attEntropyAll.nodeValue = ''
        attCountAll.nodeValue = ''
        attEntropyStream.nodeValue = ''
        attCountStream.nodeValue = ''
        attEntropyNonStream.nodeValue = ''
        attCountNonStream.nodeValue = ''
    attCountEOF = xmlDoc.createAttribute('CountEOF')
    xmlDoc.documentElement.setAttributeNode(attCountEOF)
    attCountCharsAfterLastEOF = xmlDoc.createAttribute('CountCharsAfterLastEOF')
    xmlDoc.documentElement.setAttributeNode(attCountCharsAfterLastEOF)
    if oPDFEOF != None:
        attCountEOF.nodeValue = '%d' % oPDFEOF.cntEOFs
        attCountCharsAfterLastEOF.nodeValue = '%d' % oPDFEOF.cntCharsAfterLastEOF
    else:
        attCountEOF.nodeValue = ''
        attCountCharsAfterLastEOF.nodeValue = ''

    eleKeywords = xmlDoc.createElement('Keywords')
    xmlDoc.documentElement.appendChild(eleKeywords)
    for keyword in keywords:
        eleKeyword = xmlDoc.createElement('Keyword')
        eleKeywords.appendChild(eleKeyword)
        att = xmlDoc.createAttribute('Name')
        att.nodeValue = keyword
        eleKeyword.setAttributeNode(att)
        att = xmlDoc.createAttribute('Count')
        att.nodeValue = str(words[keyword][0])
        eleKeyword.setAttributeNode(att)
        att = xmlDoc.createAttribute('HexcodeCount')
        att.nodeValue = str(words[keyword][1])
        eleKeyword.setAttributeNode(att)
    eleKeyword = xmlDoc.createElement('Keyword')
    eleKeywords.appendChild(eleKeyword)
    att = xmlDoc.createAttribute('Name')
    att.nodeValue = '/Colors > 2^24'
    eleKeyword.setAttributeNode(att)
    att = xmlDoc.createAttribute('Count')
    att.nodeValue = str(oCVE_2009_3459.count)
    eleKeyword.setAttributeNode(att)
    att = xmlDoc.createAttribute('HexcodeCount')
    att.nodeValue = str(0)
    eleKeyword.setAttributeNode(att)
    if allNames:
        keys = sorted(words.keys())
        for word in keys:
            if not word in keywords:
                eleKeyword = xmlDoc.createElement('Keyword')
                eleKeywords.appendChild(eleKeyword)
                att = xmlDoc.createAttribute('Name')
                att.nodeValue = word
                eleKeyword.setAttributeNode(att)
                att = xmlDoc.createAttribute('Count')
                att.nodeValue = str(words[word][0])
                eleKeyword.setAttributeNode(att)
                att = xmlDoc.createAttribute('HexcodeCount')
                att.nodeValue = str(words[word][1])
                eleKeyword.setAttributeNode(att)
    eleDates = xmlDoc.createElement('Dates')
    xmlDoc.documentElement.appendChild(eleDates)
    dates.sort(key=lambda x: x[0])
    for date in dates:
        eleDate = xmlDoc.createElement('Date')
        eleDates.appendChild(eleDate)
        att = xmlDoc.createAttribute('Value')
        att.nodeValue = date[0]
        eleDate.setAttributeNode(att)
        att = xmlDoc.createAttribute('Name')
        att.nodeValue = date[1]
        eleDate.setAttributeNode(att)
    return xmlDoc

def PDFiD2String(xmlDoc, force):
    result = 'PDFiD %s %s\n' % (xmlDoc.documentElement.getAttribute('Version'), xmlDoc.documentElement.getAttribute('Filename'))
    if xmlDoc.documentElement.getAttribute('ErrorOccured') == 'True':
        return result + '***Error occured***\n%s\n' % xmlDoc.documentElement.getAttribute('ErrorMessage')
    if not force and xmlDoc.documentElement.getAttribute('IsPDF') == 'False':
        return result + ' Not a PDF document\n'
    result += ' PDF Header: %s\n' % xmlDoc.documentElement.getAttribute('Header')
    for node in xmlDoc.documentElement.getElementsByTagName('Keywords')[0].childNodes:
        result += ' %-16s %7d' % (node.getAttribute('Name'), int(node.getAttribute('Count')))
        if int(node.getAttribute('HexcodeCount')) > 0:
            result += '(%d)' % int(node.getAttribute('HexcodeCount'))
        result += '\n'
    if xmlDoc.documentElement.getAttribute('CountEOF') != '':
        result += ' %-16s %7d\n' % ('%%EOF', int(xmlDoc.documentElement.getAttribute('CountEOF')))
    if xmlDoc.documentElement.getAttribute('CountCharsAfterLastEOF') != '':
        result += ' %-16s %7d\n' % ('After last %%EOF', int(xmlDoc.documentElement.getAttribute('CountCharsAfterLastEOF')))
    for node in xmlDoc.documentElement.getElementsByTagName('Dates')[0].childNodes:
        result += ' %-23s %s\n' % (node.getAttribute('Value'), node.getAttribute('Name'))
    if xmlDoc.documentElement.getAttribute('TotalEntropy') != '':
        result += ' Total entropy:           %s (%10s bytes)\n' % (xmlDoc.documentElement.getAttribute('TotalEntropy'), xmlDoc.documentElement.getAttribute('TotalCount'))
    if xmlDoc.documentElement.getAttribute('StreamEntropy') != '':
        result += ' Entropy inside streams:  %s (%10s bytes)\n' % (xmlDoc.documentElement.getAttribute('StreamEntropy'), xmlDoc.documentElement.getAttribute('StreamCount'))
    if xmlDoc.documentElement.getAttribute('NonStreamEntropy') != '':
        result += ' Entropy outside streams: %s (%10s bytes)\n' % (xmlDoc.documentElement.getAttribute('NonStreamEntropy'), xmlDoc.documentElement.getAttribute('NonStreamCount'))
    return result

def Scan(directory, allNames, extraData, disarm, force):
    try:
        if os.path.isdir(directory):
            for entry in os.listdir(directory):
                Scan(os.path.join(directory, entry), allNames, extraData, disarm, force)
        else:
            result = PDFiD2String(PDFiD(directory, allNames, extraData, disarm, force), force)
            print(result)
            logfile = open('PDFiD.log', 'a')
            logfile.write(result + '\n')
            logfile.close()
    except:
        pass

#function derived from: http://blog.9bplus.com/pdfidpy-output-to-json
def PDFiD2JSON(xmlDoc, force): 
    #Get Top Layer Data
    errorOccured = xmlDoc.documentElement.getAttribute('ErrorOccured')
    errorMessage = xmlDoc.documentElement.getAttribute('ErrorMessage')
    filename = xmlDoc.documentElement.getAttribute('Filename')
    header = xmlDoc.documentElement.getAttribute('Header')
    isPdf = xmlDoc.documentElement.getAttribute('IsPDF')
    version = xmlDoc.documentElement.getAttribute('Version')
    entropy = xmlDoc.documentElement.getAttribute('Entropy')

    #extra data
    countEof = xmlDoc.documentElement.getAttribute('CountEOF')
    countChatAfterLastEof = xmlDoc.documentElement.getAttribute('CountCharsAfterLastEOF')
    totalEntropy = xmlDoc.documentElement.getAttribute('TotalEntropy')
    streamEntropy = xmlDoc.documentElement.getAttribute('StreamEntropy')
    nonStreamEntropy = xmlDoc.documentElement.getAttribute('NonStreamEntropy')
    
    keywords = []
    dates = []

    #grab all keywords
    for node in xmlDoc.documentElement.getElementsByTagName('Keywords')[0].childNodes:
        name = node.getAttribute('Name')
        count = int(node.getAttribute('Count'))
        if int(node.getAttribute('HexcodeCount')) > 0:
            hexCount = int(node.getAttribute('HexcodeCount'))
        else:
            hexCount = 0
        keyword = { 'count':count, 'hexcodecount':hexCount, 'name':name }
        keywords.append(keyword)

    #grab all date information
    for node in xmlDoc.documentElement.getElementsByTagName('Dates')[0].childNodes:
        name = node.getAttribute('Name')
        value = node.getAttribute('Value')
        date = { 'name':name, 'value':value }
        dates.append(date)

    data = { 'countEof':countEof, 'countChatAfterLastEof':countChatAfterLastEof, 'totalEntropy':totalEntropy, 'streamEntropy':streamEntropy, 'nonStreamEntropy':nonStreamEntropy, 'errorOccured':errorOccured, 'errorMessage':errorMessage, 'filename':filename, 'header':header, 'isPdf':isPdf, 'version':version, 'entropy':entropy, 'keywords': { 'keyword': keywords }, 'dates': { 'date':dates} }
    complete = [ { 'pdfid' : data} ]
    result = json.dumps(complete)
    return result

def Main():
    oParser = optparse.OptionParser(usage='usage: %prog [options] [pdf-file]\n' + __description__, version='%prog ' + __version__)
    oParser.add_option('-s', '--scan', action='store_true', default=False, help='scan the given directory')
    oParser.add_option('-a', '--all', action='store_true', default=False, help='display all the names')
    oParser.add_option('-e', '--extra', action='store_true', default=False, help='display extra data, like dates')
    oParser.add_option('-f', '--force', action='store_true', default=False, help='force the scan of the file, even without proper %PDF header')
    oParser.add_option('-d', '--disarm', action='store_true', default=False, help='disable JavaScript and auto launch')
    (options, args) = oParser.parse_args()

    if len(args) == 0:
        if options.disarm:
            print('Option disarm not supported with stdin')
            options.disarm = False
        print(PDFiD2String(PDFiD('', options.all, options.extra, options.disarm, options.force), options.force))
    elif len(args) == 1:
        if options.scan:
            Scan(args[0], options.all, options.extra, options.disarm, options.force)
        else:
            print(PDFiD2String(PDFiD(args[0], options.all, options.extra, options.disarm, options.force), options.force))
    else:
        oParser.print_help()
        print('')
        print('  %s' % __description__)
        print('  Source code put in the public domain by Didier Stevens, no Copyright')
        print('  Use at your own risk')
        print('  https://DidierStevens.com')
        return

if __name__ == '__main__':
    Main()

########NEW FILE########
