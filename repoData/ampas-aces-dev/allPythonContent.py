__FILENAME__ = v2_IDT_maker
#!/usr/bin/env python

import sys
from os import getenv
import os.path
from datetime import date
from numpy import *

# Globals
IDT_maker_version = "0.05"

nominalEI = 400.0
blackSignal = 0.003907
blackOffset = 0.000977
midGraySignal = 0.01
encodingGain = 0.256598
encodingOffset = 0.391007

def gainForEI(EI) :
    return EI / nominalEI

def encGainForEI(EI) :
    gain = gainForEI(EI)
    return (log(gain)/log(2) * (0.89 - 1.0) / 3 + 1) * encodingGain

def logExposure(EI, x) :
    gain = gainForEI(EI)
    encGain = encGainForEI(EI)
    midGray = midGraySignal + blackOffset
    return log10(((x - blackSignal) * gain + blackOffset) / midGray) * encGain + encodingOffset

def LogC2InverseParametersForEI(EI) :
    gain = gainForEI(EI)
    encGain = encGainForEI(EI)
    midGray = midGraySignal + blackOffset
    f16 = logExposure(EI, blackSignal)
    f17 = logExposure(EI, blackSignal + 1.0 / 4095.0)
    cut = f16
    d = encodingOffset
    c = encGain
    b = blackOffset / midGray
    a = (gain / midGray) / (gain * (0.18 / midGraySignal))
    f = f16
    e = 4095.0 * (f17 - f16) / (gain * (0.18 / midGraySignal))
    return { 'a' : a,
             'b' : b,
             'cut' : cut,
             'c' : c,
             'd' : d,
             'e' : e,
             'f' : f }

def emitLogC2InverseFunction(EI) :
    p = LogC2InverseParametersForEI(EI)
    print "float"
    print "normalizedLogC2ToRelativeExposure(float x) {"
    print "\tif (x > %f)" % p['cut']
    print "\t\treturn (pow(10,(x - %f) / %f) - %f) / %f;" % (p['d'], p['c'], p['b'], p['a'])
    print "\telse"
    print "\t\treturn (x - %f) / %f;" % (p['f'], p['e'])
    print "}"
    print ""

def emitHeader(myName, EI, CCT, logC) :
    print ""
    if logC == "logc" :
        print "// ARRI ALEXA IDT for ALEXA logC files"
    else :
        print "// ARRI ALEXA IDT for ALEXA linear files"
    print "//  with camera EI set to %d" % EI
    if CCT != "ignored" :
        print "//  and CCT of adopted white set to %dK" % CCT
    print "// Written by %s v%s on %s by %s" % (myName, IDT_maker_version, date.today().strftime("%A %d %B %Y"), getenv('USER'))
    print ""

def emitRawSupport(CCT) :
    print "const float EI = %4.1f;" % EI
    print "const float black = 256.0 / 65535.0;"
    print "const float exp_factor = 0.18 / (0.01 * (400.0/EI));"
    print ""

def emitMain(EI, CCT, logC) :
    print "void main"
    print "(\tinput varying float rIn,"
    print "\tinput varying float gIn,"
    print "\tinput varying float bIn,"
    print "\tinput varying float aIn,"
    print "\toutput varying float rOut,"
    print "\toutput varying float gOut,"
    print "\toutput varying float bOut,"
    print "\toutput varying float aOut)"
    print "{"
    print ""
    M = getIDTMatrix(CCT)
    if logC == "logc" :
        print "\tfloat r_lin = normalizedLogC2ToRelativeExposure(rIn);"
        print "\tfloat g_lin = normalizedLogC2ToRelativeExposure(gIn);"
        print "\tfloat b_lin = normalizedLogC2ToRelativeExposure(bIn);"
        print ""
        print "\trOut = r_lin * %f + g_lin * %f + b_lin * %f;" % (M[0,0], M[0,1], M[0,2])
        print "\tgOut = r_lin * %f + g_lin * %f + b_lin * %f;" % (M[1,0], M[1,1], M[1,2])
        print "\tbOut = r_lin * %f + g_lin * %f + b_lin * %f;" % (M[2,0], M[2,1], M[2,2])
        print "\taOut = 1.0;"
    else :
        print "\t// convert to white-balanced, black-subtracted linear values"
        print "\tfloat r_lin = (rIn - black) * exp_factor;"
        print "\tfloat g_lin = (gIn - black) * exp_factor;"
        print "\tfloat b_lin = (bIn - black) * exp_factor;"
        print ""
        print "\t// convert to ACES primaries using CCT-dependent matrix"
        print "\trOut = r_lin * %f + g_lin * %f + b_lin * %f;" % (M[0,0], M[0,1], M[0,2])
        print "\tgOut = r_lin * %f + g_lin * %f + b_lin * %f;" % (M[1,0], M[1,1], M[1,2])
        print "\tbOut = r_lin * %f + g_lin * %f + b_lin * %f;" % (M[2,0], M[2,1], M[2,2])
        print "\taOut = 1.0;"
    print ""
    print "}"

def getIDTMatrix(cct) :
    '''
    Load video matrix coefficients and interpolate for CCT
    '''
    alexaMatrixFile = pathInExecutableDir("AlexaParameters-2013-Nov-13/Alexa_aces_matrix.txt")
    mtab = loadtxt(alexaMatrixFile, skiprows=3)
    i = searchsorted(mtab[...,0], cct)
    if i == size(mtab, 0) - 1:
        m = mtab[i, 1:]
    else :
        a = (1.0/cct - 1.0/mtab[i,0]) / (1.0/mtab[i+1,0] - 1.0/mtab[i,0])
        m = (1- a) * mtab[i, 1:] + a * mtab[i+1, 1:]
    return m.reshape((3,3))

def executableName() :
    (head, tail) = os.path.split(os.path.abspath(sys.argv[0]))
    return tail

def pathInExecutableDir(fileName) :
    (head, tail) = os.path.split(os.path.abspath(sys.argv[0]))
    return head + '/' + fileName

def usage(myName) :
    print "%s: usage is" % myName
    print "\t%s EI CCT logC|raw" % myName

if __name__ == '__main__':
    myName = executableName()
    if len(sys.argv) != 4 :
        usage(myName)
        sys.exit(2)

    EI = float(sys.argv[1])
    CCT = float(sys.argv[2])
    logC = sys.argv[3].lower()

    emitHeader(myName, EI, CCT, logC)
    if logC == "logc" :
        emitLogC2InverseFunction(EI)
    elif logC == "raw" :
        emitRawSupport(CCT)
    else :
        usage(myName)
        sys.exit(2)

    emitMain(EI, CCT, logC)

########NEW FILE########
__FILENAME__ = v3_IDT_maker
#!/usr/bin/env python

import sys
from os import getenv
import os.path
from datetime import date
from numpy import *

# Globals
IDT_maker_version = "0.08"

nominalEI = 400.0
blackSignal = 0.003907
midGraySignal = 0.01
encodingGain = 0.256598
encodingOffset = 0.391007

def gainForEI(EI) :
    return (log(EI/nominalEI)/log(2) * (0.89 - 1) / 3 + 1) * encodingGain

def LogCInverseParametersForEI(EI) :
    cut = 1.0 / 9.0
    slope = 1.0 / (cut * log(10))
    offset = log10(cut) - slope * cut
    gain = EI / nominalEI
    gray = midGraySignal / gain
    # The higher the EI, the lower the gamma
    encGain = gainForEI(EI)
    encOffset = encodingOffset
    for i in range(0,3) :
        nz = ((95.0 / 1023.0 - encOffset) / encGain - offset) / slope
        encOffset = encodingOffset - log10(1 + nz) * encGain
    # Calculate some intermediate values
    a = 1.0 / gray
    b = nz - blackSignal / gray
    e = slope * a * encGain
    f = encGain * (slope * b + offset) + encOffset
    # Manipulations so we can return relative exposure
    s = 4 / (0.18 * EI)
    t = blackSignal
    b = b + a * t
    a = a * s
    f = f + e * t
    e = e * s
    return { 'a' : a,
             'b' : b,
             'cut' : (cut - b) / a,
             'c' : encGain,
             'd' : encOffset,
             'e' : e,
             'f' : f }

def emitLogCInverseFunction(EI) :
    p = LogCInverseParametersForEI(EI)
    print "float"
    print "normalizedLogCToRelativeExposure(float x) {"
    breakpoint = p['e'] * p['cut'] + p['f']
    print "\tif (x > %f)" % breakpoint
    print "\t\treturn (pow(10,(x - %f) / %f) - %f) / %f;" % (p['d'], p['c'], p['b'], p['a'])
    print "\telse"
    print "\t\treturn (x - %f) / %f;" % (p['f'], p['e'])
    print "}"
    print ""

def emitHeader(myName, EI, CCT, logC) :
    print ""
    if logC == "logc" :
        print "// ARRI ALEXA IDT for ALEXA logC files"
    else :
        print "// ARRI ALEXA IDT for ALEXA linear files"
    print "//  with camera EI set to %d" % EI
    if CCT != "ignored" :
        print "//  and CCT of adopted white set to %dK" % CCT
    print "// Written by %s v%s on %s by %s" % (myName, IDT_maker_version, date.today().strftime("%A %d %B %Y"), getenv('USER'))
    print ""

def emitRawSupport(CCT) :
    print "const float EI = %4.1f;" % EI
    print "const float black = 256.0 / 65535.0;"
    print "const float exp_factor = 0.18 / (0.01 * (400.0/EI));"
    print ""

def emitMain(EI, CCT, logC, ND) :
    print "void main"
    print "(\tinput varying float rIn,"
    print "\tinput varying float gIn,"
    print "\tinput varying float bIn,"
    print "\tinput varying float aIn,"
    print "\toutput varying float rOut,"
    print "\toutput varying float gOut,"
    print "\toutput varying float bOut,"
    print "\toutput varying float aOut)"
    print "{"
    print ""
    if logC == "logc" :
        # chromatically adapt (using CAT02) from ALEXA WG primaries and D65 white point
        # to ACES RGB primaries & ACES white point
        WG2A = array( [ (0.680206, 0.236137, 0.083658),
                        (0.085415, 1.017471, -0.102886),
                        (0.002057, -0.062563, 1.060506) ] );
        print "\tfloat r_lin = normalizedLogCToRelativeExposure(rIn);"
        print "\tfloat g_lin = normalizedLogCToRelativeExposure(gIn);"
        print "\tfloat b_lin = normalizedLogCToRelativeExposure(bIn);"
        print ""
        print "\trOut = r_lin * %f + g_lin * %f + b_lin * %f;" % (WG2A[0,0], WG2A[0,1], WG2A[0,2])
        print "\tgOut = r_lin * %f + g_lin * %f + b_lin * %f;" % (WG2A[1,0], WG2A[1,1], WG2A[1,2])
        print "\tbOut = r_lin * %f + g_lin * %f + b_lin * %f;" % (WG2A[2,0], WG2A[2,1], WG2A[2,2])
        print "\taOut = 1.0;"
    else :
        M = getIDTMatrix(CCT, ND)
        print "\t// convert to white-balanced, black-subtracted linear values"
        print "\tfloat r_lin = (rIn - black) * exp_factor;"
        print "\tfloat g_lin = (gIn - black) * exp_factor;"
        print "\tfloat b_lin = (bIn - black) * exp_factor;"
        print ""
        print "\t// convert to ACES primaries using CCT-dependent matrix"
        print "\trOut = r_lin * %f + g_lin * %f + b_lin * %f;" % (M[0,0], M[0,1], M[0,2])
        print "\tgOut = r_lin * %f + g_lin * %f + b_lin * %f;" % (M[1,0], M[1,1], M[1,2])
        print "\tbOut = r_lin * %f + g_lin * %f + b_lin * %f;" % (M[2,0], M[2,1], M[2,2])
        print "\taOut = 1.0;"
    print ""
    print "}"

def getIDTMatrix(cct, ND) :
    '''
    Load video matrix coefficients and interpolate for CCT
    '''
    alexaMatrixFile = pathInExecutableDir("AlexaParameters-2013-Nov-13/Alexa-st-nd-aces_matrix.txt" if ND == "nd-1pt3" else "AlexaParameters-2013-Nov-13/Alexa_aces_matrix.txt")
    mtab = loadtxt(alexaMatrixFile, skiprows=3)
    i = searchsorted(mtab[...,0], cct)
    if i == size(mtab, 0) - 1:
        m = mtab[i, 1:]
    else :
        a = (1.0/cct - 1.0/mtab[i,0]) / (1.0/mtab[i+1,0] - 1.0/mtab[i,0])
        m = (1- a) * mtab[i, 1:] + a * mtab[i+1, 1:]
    return m.reshape((3,3))

def executableName() :
    (head, tail) = os.path.split(os.path.abspath(sys.argv[0]))
    return tail

def pathInExecutableDir(fileName) :
    (head, tail) = os.path.split(os.path.abspath(sys.argv[0]))
    return head + '/' + fileName

def usage(myName) :
    print "%s: usage is" % myName
    print "\t%s EI CCT logC|raw [nd-1pt3]" % myName

if __name__ == '__main__':
    myName = executableName()
    if len(sys.argv) < 4 or len(sys.argv) > 5:
        usage(myName)
        sys.exit(2)

    EI = float(sys.argv[1])
    logC = sys.argv[3].lower()

    if logC == "raw" :
        CCT = float(sys.argv[2])
    else :
        CCT = "ignored"

    if logC != "logc" and logC != "raw" :
        usage(myName)
        sys.exit(2)

    if len(sys.argv) == 4 :
        ND = False
    else :
        ND = sys.argv[4].lower()
        if ND != "nd-1pt3" :
            usage(myName)
            sys.exit(2)

    if logC == "logc" :
        emitHeader(myName, EI, CCT, logC)
        emitLogCInverseFunction(EI)
    elif logC == "raw" :
        emitHeader(myName, EI, CCT, logC)
        emitRawSupport(CCT)
    else :
        usage(myName)
        sys.exit(2)

    emitMain(EI, CCT, logC, ND)

########NEW FILE########
