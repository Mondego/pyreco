__FILENAME__ = conf
# -*- coding: utf-8 -*-
#
# Pysolar documentation build configuration file

import sys, os

# General configuration
# ---------------------

# Add any Sphinx extension module names here, as strings. They can be extensions
# coming with Sphinx (named 'sphinx.ext.*') or your custom ones.
extensions = ['sphinx.ext.autodoc', 'numpydoc']

# Add any paths that contain templates here, relative to this directory.
templates_path = ['.templates']

# The suffix of source filenames.
source_suffix = '.rst'

# The master toctree document.
master_doc = 'index'

# General substitutions.
project = 'Pysolar'
copyright = '2008-2010, Brandon Stafford'

# The default replacements for |version| and |release|, also used in various
# other places throughout the built documents.
#
# The short X.Y version.
version = '0.4.2'
# The full version, including alpha/beta/rc tags.
release = '0.4.2'

# There are two options for replacing |today|: either, you set today to some
# non-false value, then it is used:
#today = ''
# Else, today_fmt is used as the format for a strftime call.
today_fmt = '%B %d, %Y'

# The name of the Pygments (syntax highlighting) style to use.
pygments_style = 'sphinx'

# Options for HTML output
# -----------------------

# The style sheet to use for HTML and HTML Help pages. A file of that name
# must exist either in Sphinx' static/ path, or in one of the custom paths
# given in html_static_path.
html_style = 'default.css'

# Add any paths that contain custom static files (such as style sheets) here,
# relative to this directory. They are copied after the builtin static files,
# so a file named "default.css" will overwrite the builtin "default.css".
html_static_path = ['.static']

# If not '', a 'Last updated on:' timestamp is inserted at every page bottom,
# using the given strftime format.
html_last_updated_fmt = '%b %d, %Y'

# Output file base name for HTML help builder.
htmlhelp_basename = 'Pysolardoc'

# Options for LaTeX output
# ------------------------

# Grouping the document tree into LaTeX files. List of tuples
# (source start file, target name, title, author, document class [howto/manual]).
latex_documents = [
  ('index', 'Pysolar.tex', 'Pysolar Documentation',
   'Brandon Stafford', 'manual'),
]

########NEW FILE########
__FILENAME__ = constants
#!/usr/bin/python

#    Copyright Brandon Stafford
#
#    This file is part of Pysolar.
#
#    Pysolar is free software; you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation; either version 3 of the License, or
#    (at your option) any later version.
#
#    Pysolar is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU General Public License along
#    with Pysolar. If not, see <http://www.gnu.org/licenses/>.

"""This file is consists of numerical constants for calculating corrections,
such as the wiggling ("nutation") of the axis of the earth. It also includes
functions for building dictionaries of polynomial functions for rapid
calculation of corrections.

Most of the constants come from a 2005 paper by Reda and Andreas:

I. Reda and A. Andreas, "Solar Position Algorithm for Solar Radiation
Applications," National Renewable Energy Laboratory, NREL/TP-560-34302,
revised November 2005.

http://www.osti.gov/bridge/servlets/purl/15003974-iP3z6k/native/15003974.PDF

However, it seems that Reda and Andreas took the bulk of the constants
(L0, etc.) from Pierre Bretagnon and Gerard Francou's Variations Seculaires
des Orbites Planetaires, or VSOP87:

http://en.wikipedia.org/wiki/Secular_variations_of_the_planetary_orbits#VSOP87

See also ftp://ftp.imcce.fr/pub/ephem/planets/vsop87/VSOP87D.ear

"""

def buildPolyFit(params): 
    (a, b, c, d) = params
    return (lambda x: a + b * x + c * x ** 2 + (x ** 3) / d)

def buildPolyDict():
    """This function builds a dictionary of polynomial functions from a list of
    coefficients, so that the functions can be called by name. This is used in
    calculating nutation.

    """
    return dict([(name, buildPolyFit(coeffs)) for (name, coeffs) in coeff_list])


coeff_list = [
		('ArgumentOfLatitudeOfMoon', (93.27191, 483202.017538, -0.0036825, 327270.0)),
		('LongitudeOfAscendingNode', (125.04452, -1934.136261, 0.0020708, 450000.0)),
		('MeanElongationOfMoon', (297.85036, 445267.111480, -0.0019142, 189474.0)),
		('MeanAnomalyOfMoon', (134.96298, 477198.867398, 0.0086972, 56250.0)),
		('MeanAnomalyOfSun', (357.52772, 35999.050340, -0.0001603, -300000.0))
	]

earth_radius = 6378140.0 # meters

aberration_sin_terms = [[0,0,0,0,1],
	[-2,0,0,2,2],
	[0,0,0,2,2],
	[0,0,0,0,2],
	[0,1,0,0,0],
	[0,0,1,0,0],
	[-2,1,0,2,2],
	[0,0,0,2,1],
	[0,0,1,2,2],
	[-2,-1,0,2,2],
	[-2,0,1,0,0],
	[-2,0,0,2,1],
	[0,0,-1,2,2],
	[2,0,0,0,0],
	[0,0,1,0,1],
	[2,0,-1,2,2],
	[0,0,-1,0,1],
	[0,0,1,2,1],
	[-2,0,2,0,0],
	[0,0,-2,2,1],
	[2,0,0,2,2],
	[0,0,2,2,2],
	[0,0,2,0,0],
	[-2,0,1,2,2],
	[0,0,0,2,0],
	[-2,0,0,2,0],
	[0,0,-1,2,1],
	[0,2,0,0,0],
	[2,0,-1,0,1],
	[-2,2,0,2,2],
	[0,1,0,0,1],
	[-2,0,1,0,1],
	[0,-1,0,0,1],
	[0,0,2,-2,0],
	[2,0,-1,2,1],
	[2,0,1,2,2],
	[0,1,0,2,2],
	[-2,1,1,0,0],
	[0,-1,0,2,2],
	[2,0,0,2,1],
	[2,0,1,0,0],
	[-2,0,2,2,2],
	[-2,0,1,2,1],
	[2,0,-2,0,1],
	[2,0,0,0,1],
	[0,-1,1,0,0],
	[-2,-1,0,2,1],
	[-2,0,0,0,1],
	[0,0,2,2,1],
	[-2,0,2,0,1],
	[-2,1,0,2,1],
	[0,0,1,-2,0],
	[-1,0,1,0,0],
	[-2,1,0,0,0],
	[1,0,0,0,0],
	[0,0,1,2,0],
	[0,0,-2,2,2],
	[-1,-1,1,0,0],
	[0,1,1,0,0],
	[0,-1,1,2,2],
	[2,-1,-1,2,2],
	[0,0,3,2,2],
	[2,-1,0,2,2]]
	
nutation_coefficients = [[-171996,-174.2,92025,8.9],
	[-13187,-1.6,5736,-3.1],
	[-2274,-0.2,977,-0.5],
	[2062,0.2,-895,0.5],
	[1426,-3.4,54,-0.1],
	[712,0.1,-7,0],
	[-517,1.2,224,-0.6],
	[-386,-0.4,200,0],
	[-301,0,129,-0.1],
	[217,-0.5,-95,0.3],
	[-158,0,0,0],
	[129,0.1,-70,0],
	[123,0,-53,0],
	[63,0,0,0],
	[63,0.1,-33,0],
	[-59,0,26,0],
	[-58,-0.1,32,0],
	[-51,0,27,0],
	[48,0,0,0],
	[46,0,-24,0],
	[-38,0,16,0],
	[-31,0,13,0],
	[29,0,0,0],
	[29,0,-12,0],
	[26,0,0,0],
	[-22,0,0,0],
	[21,0,-10,0],
	[17,-0.1,0,0],
	[16,0,-8,0],
	[-16,0.1,7,0],
	[-15,0,9,0],
	[-13,0,7,0],
	[-12,0,6,0],
	[11,0,0,0],
	[-10,0,5,0],
	[-8,0,3,0],
	[7,0,-3,0],
	[-7,0,0,0],
	[-7,0,3,0],
	[-7,0,3,0],
	[6,0,0,0],
	[6,0,-3,0],
	[6,0,-3,0],
	[-6,0,3,0],
	[-6,0,3,0],
	[5,0,0,0],
	[-5,0,3,0],
	[-5,0,3,0],
	[-5,0,3,0],
	[4,0,0,0],
	[4,0,0,0],
	[4,0,0,0],
	[-4,0,0,0],
	[-4,0,0,0],
	[-4,0,0,0],
	[3,0,0,0],
	[-3,0,0,0],
	[-3,0,0,0],
	[-3,0,0,0],
	[-3,0,0,0],
	[-3,0,0,0],
	[-3,0,0,0],
	[-3,0,0,0]]

L0 = [[175347046.0,0,0],
[3341656.0,4.6692568,6283.07585],
[34894.0,4.6261,12566.1517],
[3497.0,2.7441,5753.3849],
[3418.0,2.8289,3.5231],
[3136.0,3.6277,77713.7715],
[2676.0,4.4181,7860.4194],
[2343.0,6.1352,3930.2097],
[1324.0,0.7425,11506.7698],
[1273.0,2.0371,529.691],
[1199.0,1.1096,1577.3435],
[990,5.233,5884.927],
[902,2.045,26.298],
[857,3.508,398.149],
[780,1.179,5223.694],
[753,2.533,5507.553],
[505,4.583,18849.228],
[492,4.205,775.523],
[357,2.92,0.067],
[317,5.849,11790.629],
[284,1.899,796.298],
[271,0.315,10977.079],
[243,0.345,5486.778],
[206,4.806,2544.314],
[205,1.869,5573.143],
[202,2.4458,6069.777],
[156,0.833,213.299],
[132,3.411,2942.463],
[126,1.083,20.775],
[115,0.645,0.98],
[103,0.636,4694.003],
[102,0.976,15720.839],
[102,4.267,7.114],
[99,6.21,2146.17],
[98,0.68,155.42],
[86,5.98,161000.69],
[85,1.3,6275.96],
[85,3.67,71430.7],
[80,1.81,17260.15],
[79,3.04,12036.46],
[71,1.76,5088.63],
[74,3.5,3154.69],
[74,4.68,801.82],
[70,0.83,9437.76],
[62,3.98,8827.39],
[61,1.82,7084.9],
[57,2.78,6286.6],
[56,4.39,14143.5],
[56,3.47,6279.55],
[52,0.19,12139.55],
[52,1.33,1748.02],
[51,0.28,5856.48],
[49,0.49,1194.45],
[41,5.37,8429.24],
[41,2.4,19651.05],
[39,6.17,10447.39],
[37,6.04,10213.29],
[37,2.57,1059.38],
[36,1.71,2352.87],
[36,1.78,6812.77],
[33,0.59,17789.85],
[30,0.44,83996.85],
[30,2.74,1349.87],
[25,3.16,4690.48]]

L1 = [[628331966747.0,0,0],
[206059.0,2.678235,6283.07585],
[4303.0,2.6351,12566.1517],
[425.0,1.59,3.523],
[119.0,5.796,26.298],
[109.0,2.966,1577.344],
[93,2.59,18849.23],
[72,1.14,529.69],
[68,1.87,398.15],
[67,4.41,5507.55],
[59,2.89,5223.69],
[56,2.17,155.42],
[45,0.4,796.3],
[36,0.47,775.52],
[29,2.65,7.11],
[21,5.34,0.98],
[19,1.85,5486.78],
[19,4.97,213.3],
[17,2.99,6275.96],
[16,0.03,2544.31],
[16,1.43,2146.17],
[15,1.21,10977.08],
[12,2.83,1748.02],
[12,3.26,5088.63],
[12,5.27,1194.45],
[12,2.08,4694],
[11,0.77,553.57],
[10,1.3,3286.6],
[10,4.24,1349.87],
[9,2.7,242.73],
[9,5.64,951.72],
[8,5.3,2352.87],
[6,2.65,9437.76],
[6,4.67,4690.48]]

L2 = [[52919.0,0,0],
[8720.0,1.0721,6283.0758],
[309.0,0.867,12566.152],
[27,0.05,3.52],
[16,5.19,26.3],
[16,3.68,155.42],
[10,0.76,18849.23],
[9,2.06,77713.77],
[7,0.83,775.52],
[5,4.66,1577.34],
[4,1.03,7.11],
[4,3.44,5573.14],
[3,5.14,796.3],
[3,6.05,5507.55],
[3,1.19,242.73],
[3,6.12,529.69],
[3,0.31,398.15],
[3,2.28,553.57],
[2,4.38,5223.69],
[2,3.75,0.98]]

L3 = [[289.0,5.844,6283.076],
[35,0,0],
[17,5.49,12566.15],
[3,5.2,155.42],
[1,4.72,3.52],
[1,5.3,18849.23],
[1,5.97,242.73]]

L4 = [[114.0,3.142,0],
[8,4.13,6283.08],
[1,3.84,12566.15]]

L5 = [[1,3.14,0]]

B0 = [[280.0,3.199,84334.662],
[102.0,5.422,5507.553],
[80,3.88,5223.69],
[44,3.7,2352.87],
[32,4,1577.34]]

B1 = [[9,3.9,5507.55],
[6,1.73,5223.69]]


R0 = [[100013989.0,0,0],
[1670700.0,3.0984635,6283.07585],
[13956.0,3.05525,12566.1517],
[3084.0,5.1985,77713.7715],
[1628.0,1.1739,5753.3849],
[1576.0,2.8469,7860.4194],
[925.0,5.453,11506.77],
[542.0,4.564,3930.21],
[472.0,3.661,5884.927],
[346.0,0.964,5507.553],
[329.0,5.9,5223.694],
[307.0,0.299,5573.143],
[243.0,4.273,11790.629],
[212.0,5.847,1577.344],
[186.0,5.022,10977.079],
[175.0,3.012,18849.228],
[110.0,5.055,5486.778],
[98,0.89,6069.78],
[86,5.69,15720.84],
[86,1.27,161000.69],
[85,0.27,17260.15],
[63,0.92,529.69],
[57,2.01,83996.85],
[56,5.24,71430.7],
[49,3.25,2544.31],
[47,2.58,775.52],
[45,5.54,9437.76],
[43,6.01,6275.96],     
[39,5.36,4694],
[38,2.39,8827.39],
[37,0.83,19651.05],
[37,4.9,12139.55],
[36,1.67,12036.46],
[35,1.84,2942.46],
[33,0.24,7084.9],
[32,0.18,5088.63], 
[32,1.78,398.15],
[28,1.21,6286.6],
[28,1.9,6279.55],
[26,4.59,10447.39]]

R1 = [[103019.0,1.10749,6283.07585],
[1721.0,1.0644,12566.1517],
[702.0,3.142,0],
[32,1.02,18849.23],
[31,2.84,5507.55],
[25,1.32,5223.69],
[18,1.42,1577.34],
[10,5.91,10977.08],
[9,1.42,6275.96],
[9,0.27,5486.78]]

R2 = [[4359.0,5.7846,6283.0758],
[124.0,5.579,12566.152],
[12,3.14,0],
[9,3.63,77713.77],
[6,1.87,5573.14],
[3,5.47,18849]]

R3 = [[145.0,4.273,6283.076],
[7,3.92,12566.15]]

R4 = [[4,2.56,6283.08]]


########NEW FILE########
__FILENAME__ = elevation
#!/usr/bin/python

#    Copyright Sean T. Hammond
#
#    This file is part of Pysolar.
#
#    Pysolar is free software; you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation; either version 3 of the License, or
#    (at your option) any later version.
#
#    Pysolar is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU General Public License along
#    with Pysolar. If not, see <http://www.gnu.org/licenses/>.

"""Various elevation-related calculations

"""
import math

def GetPressureWithElevation(h, Ps=101325.00, Ts=288.15, Tl=-0.0065, Hb=0.0, R=8.31432, g=9.80665, M=0.0289644):
	#This function returns an estimate of the pressure in pascals as a function of elevation above sea level
	#NOTE: This equation is only accurate up to 11,000 meters
	#NOTE: results might be odd for elevations below 0 (sea level), like Dead Sea.
	#h=elevation relative to sea level (m)
	#Ps= static pressure (pascals) = 101325.00 P
	#Ts= standard temperature (kelvin) = 288.15 K
	#Tl= temperature lapse rate (kelvin/meter) = -0.0065 K/m
	#Hb= height at the bottom of the layer = 0
	#R= universal gas constant for air = 8.31432 N*m/s^2
	#g= gravitational acceleration for earth = 9.80665 m/s^2
	#M= Molar mass of Earth's atmosphere = 0.0289644 kg/mol
	#P=Ps*(Ts/((Ts+Tl)*(h-Hb)))^((g*M)/(R*Tl))
	#returns pressure in pascals
	if h>11000.0: print("WARNING: Elevation used exceeds the recommended maximum elevation for this function (11,000m)")
	theDenominator = Ts+(Tl*(h-Hb))
	theExponent=(g*M)/(R*Tl)
	return Ps*(Ts/theDenominator)**theExponent

def GetTemperatureWithElevation(h, Ts=288.15, Tl=-0.0065):
	#This function returns an estimate of temperature as a function above sea level
	#NOTE: this is only accurate up to 11,000m
	#NOTE: results might be odd for elevations below 0 (sea level), like Dead Sea.
	#Ts= standard temperature (kelvin) = 288.15 K
	#Tl= temperature lapse rate (kelvin/meter) = -0.0065 K/m
	#returns temp in kelvin
	return Ts+(h*Tl)

def ElevationTest():
	print("Elevation(m) Pressure(Pa) Temperature(K)")
	h=0
	for i in range(11):
		P=GetPressureWithElevation(h)
		T=GetTemperatureWithElevation(h)
		print("%i %i %i" % (h, P, T))
		h=h+1000



########NEW FILE########
__FILENAME__ = julian
#!/usr/bin/python

#    Copyright Brandon Stafford
#
#    This file is part of Pysolar.
#
#    Pysolar is free software; you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation; either version 3 of the License, or
#    (at your option) any later version.
#
#    Pysolar is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU General Public License along
#    with Pysolar. If not, see <http://www.gnu.org/licenses/>.

"""This file contains all the functions related to the Julian calendar, which
are used in calculating the position of the sun relative to the earth

"""
import math

def GetJulianCentury(julian_day):
    return (julian_day - 2451545.0) / 36525.0

def GetJulianDay(utc_datetime):
    """This function is based on NREL/TP-560-34302 by Andreas and Reda

    This function does not accept years before 0 because of the bounds check
    on Python's datetime.year field.

    """
    year = utc_datetime.year
    month = utc_datetime.month
    if(month <= 2.0):        # shift to accomodate leap years?
        year = year - 1.0
        month = month + 12.0
    day = utc_datetime.day + (((utc_datetime.hour * 3600.0) + (utc_datetime.minute * 60.0) + utc_datetime.second + (utc_datetime.microsecond / 1000000.0)) / 86400.0)
    gregorian_offset = 2.0 - (year // 100.0) + ((year // 100.0) // 4.0)
    julian_day = math.floor(365.25 * (year + 4716.0)) + math.floor(30.6001 * (month + 1.0)) + day - 1524.5
    if (julian_day <= 2299160.0):
        return julian_day # before October 5, 1852
    else:
        return julian_day + gregorian_offset # after October 5, 1852

def GetJulianEphemerisCentury(julian_ephemeris_day):
    return (julian_ephemeris_day - 2451545.0) / 36525.0

def GetJulianEphemerisDay(julian_day, delta_seconds = 66.0):
    """delta_seconds is the value referred to by astronomers as Delta-T, defined as the difference between
    Dynamical Time (TD) and Universal Time (UT). In 2007, it's around 65 seconds.
    A list of values for Delta-T can be found here: ftp://maia.usno.navy.mil/ser7/deltat.data

    More details: http://en.wikipedia.org/wiki/DeltaT

    """
    return julian_day + (delta_seconds / 86400.0)

def GetJulianEphemerisMillenium(julian_ephemeris_century):
    return (julian_ephemeris_century / 10.0)

########NEW FILE########
__FILENAME__ = query_usno
#!/usr/bin/python
 
# Copyright Brandon Stafford
#
# This file is part of Pysolar.
#
# Pysolar is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 3 of the License, or
# (at your option) any later version.
#
# Pysolar is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License along
# with Pysolar. If not, see <http://www.gnu.org/licenses/>.

"""Tool for requesting data from US Naval Observatory

"""
import datetime, random, time

try:
  from urllib.request import Request,urlopen
  from urllib.parse import urlencode
except:
  from urllib2 import Request,urlopen
  from urllib import urlencode

import Pysolar as solar



class Ephemeris:
    def __init__(self, timestamp, latitude, longitude, elevation, azimuth=0, altitude=0):
        self.timestamp = timestamp
        self.latitude = latitude
        self.longitude = longitude
        self.elevation = float(elevation)
        self.azimuth = float(azimuth)
        self.altitude = float(altitude)

class EphemerisComparison:
    def __init__(self, name1, eph1, name2, eph2):
        self.timestamp = eph1.timestamp
        self.latitude = eph1.latitude
        self.longitude = eph1.longitude
        self.elevation = eph1.elevation
        self.name1 = name1
        self.alt1 = eph1.altitude
        self.az1 = eph1.azimuth
        self.name2 = name2
        self.alt2 = eph2.altitude
        self.az2 = eph2.azimuth
        self.alt_error = abs(eph1.altitude - eph2.altitude)
        self.az_error = abs(eph1.azimuth - eph2.azimuth)

def RequestEphemerisData(datum):
    data = EncodeRequest(datum.latitude, datum.longitude, datum.timestamp, datum.elevation)
    url = 'http://aa.usno.navy.mil/cgi-bin/aa_topocentric2.pl'
    if type(data) == str:
      req = Request(url, data.encode())
    else:
      req = Request(url, data)
    response = urlopen(req)

    lines = response.readlines()
    response.close()
    #print lines
    #print lines[21] # should not we do some try catch here?
    result = lines[21]
    tokens = [x for x in result.split(b' ') if x not in b' ']
    print('Tokens: \n', tokens)

    usno_alt = float(tokens[4]) + float(tokens[5])/60.0 + float(tokens[6])/3600.0
    usno_az = float(tokens[7]) + float(tokens[8])/60.0 + float(tokens[9])/3600.0

#   print usno_alt
#   print usno_az

    result  = Ephemeris(datum.timestamp, datum.latitude, datum.longitude, datum.elevation, usno_az, usno_alt)

    return result

def ComparePysolarToUSNO(datum):
    alt = solar.GetAltitude(float(datum.latitude), float(datum.longitude), datum.timestamp, datum.elevation)
    pysolar_alt = (90.0 - alt)
    az = solar.GetAzimuth(float(datum.latitude), float(datum.longitude), datum.timestamp, datum.elevation)
    pysolar_az = (180.0 - az)%360.0

#   print pysolar_alt
#   print pysolar_az

    pysolar = Ephemeris(datum.timestamp, datum.latitude, datum.longitude, datum.elevation, pysolar_az, pysolar_alt)
    c = EphemerisComparison('pysolar', pysolar, 'usno', datum)
    return c

def EncodeRequest(latitude, longitude, timestamp, elevation):
    """Builds a string of arguments to be passed to the Perl script at the USNO
    
    Note that the degree arguments must be integers, or the USNO script chokes."""
    params = {}
    params['FFX'] = '2' # use worldwide locations script
    params['ID'] = 'Pysolar'
    params['pos'] = '9'
    params['obj'] = '10' # Sun
    params['xxy'] = str(timestamp.year)
    params['xxm'] = str(timestamp.month)
    params['xxd'] = str(timestamp.day)
    params['t1'] = str(timestamp.hour)
    params['t2'] = str(timestamp.minute)
    params['t3'] = str(timestamp.second)
    params['intd'] = '1.0'
    params['unit'] = '1'
    params['rep'] = '1'
    params['place'] = 'Name omitted'

    sign = lambda x: ('1', '-1')[x < 0]
    (deg, rem) = divmod(longitude, 1)
    (min, sec) = divmod(rem, 1.0/60.0)
    params['xx0'] = sign(deg)# longitude (1 = east, -1 = west)
    params['xx1'] = str(abs(int(deg))) # degrees
    params['xx2'] = str(int(min)) # minutes
    params['xx3'] = str(sec) # seconds

    (deg, rem) = divmod(latitude, 1)
    (min, sec) = divmod(rem, 1.0/60.0)  
    params['yy0'] = sign(deg) # latitude (1 = north, -1 = south)
    params['yy1'] = str(abs(int(deg))) # degrees
    params['yy2'] = str(int(min)) # minutes
    params['yy3'] = str(sec) # seconds
    
    params['hh1'] = str(elevation) # height above sea level in meters
    params['ZZZ'] = 'END'
    data = urlencode(params)
    return data

def GatherRandomEphemeris():
    latitude = random.randrange(-90, 90)
    longitude = random.randrange(0, 360)
    elevation = 0.0
    t = datetime.datetime(random.randrange(2013,2014), random.randrange(1, 13), random.randrange(1, 28), random.randrange(0, 24), random.randrange(0, 60), random.randrange(0,60))
    query = Ephemeris(t, latitude, longitude, elevation)
    PrintEphemerisDatum(query)
    d = RequestEphemerisData(query)
    PrintEphemerisDatum(d)
    WriteEphemerisDatumToFile(d, 'usno_data.txt')

def PrintEphemerisDatum(datum):
    print(datum.timestamp, datum.latitude, datum.longitude, datum.elevation, datum.azimuth, datum.altitude)

def ReadEphemeridesLog(logname):
    data = []
    log = open(logname, 'r')
    lines = log.readlines()
    log.close()
    for line in lines:
        args = line.split(' ')
        d = datetime.datetime(*(time.strptime(args[0] + ' ' + args[1], '%Y-%m-%d %H:%M:%S')[0:6]))
        e = Ephemeris(d, args[2], args[3], args[4], args[5], args[6])
        data.append(e)
    return data

def WriteEphemerisDatumToFile(d, filename):
    log = open(filename, 'a')
    log.write('%s %s %s %s %s %s\n' % (d.timestamp, d.latitude, d.longitude, d.elevation, d.azimuth, d.altitude))
    log.close()

def WriteComparisonsToCSV(comps, filename):
    out = open(filename, 'a')
    for c in comps:
        out.write('%s,%s,%s,%s,%s,%s,%s,%s,%s,%s\n' % (c.timestamp, c.latitude, c.longitude, c.elevation, c.alt1, c.alt2, c.alt_error, c.az1, c.az2, c.az_error))
    out.close()


if __name__ == '__main__':
    from scipy import stats
    import numpy as np
    import sys
    
    if len(sys.argv) >= 2:
                ephemerides = ReadEphemeridesLog(sys.argv[1])
    else:
        for i in range(100):
            GatherRandomEphemeris()
            ephemerides = ReadEphemeridesLog('usno_data.txt')

    comps = []
    for e in ephemerides:
        c = ComparePysolarToUSNO(e)
        comps.append(c)

    az_errors = np.array([c.az_error for c in comps])
    alt_errors = np.array([c.alt_error for c in comps])

    print('---------------------')
    print('Azimuth stats')
    print('Mean error: ' + str(np.mean(az_errors)))
    print('Std dev: ' + str(np.std(az_errors)))
    print('Min error: ' + str(stats.tmin(az_errors, None)))
    print('Max error: ' + str(stats.tmax(az_errors, None)))

    print('----------------------')
    print('Altitude stats')
    
    print('Mean error: ' + str(np.mean(alt_errors)))
    print('Std dev: '+ str(np.std(alt_errors)))
    print('Min error: ' + str(stats.tmin(alt_errors, None)))
    print('Max error: ' + str(stats.tmax(alt_errors, None)))

    WriteComparisonsToCSV(comps, 'pysolar_v_usno.csv')

########NEW FILE########
__FILENAME__ = radiation
#!/usr/bin/python

#    Copyright Brandon Stafford
#
#    This file is part of Pysolar.
#
#    Pysolar is free software; you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation; either version 3 of the License, or
#    (at your option) any later version.
#
#    Pysolar is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU General Public License along
#    with Pysolar. If not, see <http://www.gnu.org/licenses/>.

"""Calculate different kinds of radiation components via default values

"""
#from . import solar
import math

def GetAirMassRatio(altitude_deg):
	# from Masters, p. 412
	# warning: pukes on input of zero
	return (1/math.sin(math.radians(altitude_deg)))

def GetApparentExtraterrestrialFlux(day):
	# from Masters, p. 412
	return 1160 + (75 * math.sin(math.radians((360./365) * (day - 275))))

def GetOpticalDepth(day):
	# from Masters, p. 412
	return 0.174 + (0.035 * math.sin(math.radians((360./365) * (day - 100))))

def GetRadiationDirect(utc_datetime, altitude_deg):
	# from Masters, p. 412
	
	if(altitude_deg > 0):
		day = solar.GetDayOfYear(utc_datetime)
		flux = GetApparentExtraterrestrialFlux(day)
		optical_depth = GetOpticalDepth(day)
		air_mass_ratio = GetAirMassRatio(altitude_deg)
		return flux * math.exp(-1 * optical_depth * air_mass_ratio)
	else:
		return 0.0

########NEW FILE########
__FILENAME__ = rest
#!/usr/bin/python

#    Copyright Brandon Stafford
#
#    This file is part of Pysolar.
#
#    Pysolar is free software; you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation; either version 3 of the License, or
#    (at your option) any later version.
#
#    Pysolar is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU General Public License along
#    with Pysolar. If not, see <http://www.gnu.org/licenses/>.

import math

albedo = {} # single-scattering albedo used to calculate aerosol scattering transmittance

albedo["high-frequency"] = 0.92
albedo["low-frequency"] = 0.84

rhogi = 0.150 # mean ground albedo from [Gueymard, 2008], Table 1

E0n = {"high-frequency": 635.4, # extra-atmospheric irradiance, 290-700 nm (UV and visible)
       "low-frequency":  709.7} # extra-atmospheric irradiance, 700-4000 nm (short infrared)

def GetAerosolForwardScatteranceFactor(altitude_deg):
	Z = 90 - altitude_deg
	return 1 - math.e ** (-0.6931 - 1.8326 * math.cos(math.radians(Z)))

def GetAerosolOpticalDepth(turbidity_beta, effective_wavelength, turbidity_alpha):
	# returns tau_a
	print("effective_wavelength: ")
	print effective_wavelength
	return turbidity_beta * effective_wavelength ** -turbidity_alpha

def GetAerosolScatteringCorrectionFactor(band, ma, tau_a):
	# returns F
	if band == "high-frequency":
		g0 = (3.715 + 0.368 * ma + 0.036294 * ma ** 2)/(1 + 0.0009391 * ma ** 2)
		g1 = (-0.164 - 0.72567 * ma + 0.20701 * ma ** 2)/(1 + 0.001901 * ma ** 2)
		g2 = (-0.052288 + 0.31902 * ma + 0.17871 * ma ** 2)/(1 + 0.0069592 * ma ** 2)
		return (g0 + g1 * tau_a)/(1 + g2 * tau_a)
	else:
		h0 = (3.4352 +  0.65267 * ma + 0.00034328 * ma ** 2)/(1 + 0.034388 * ma ** 1.5)
		h1 = (1.231 - 1.63853 * ma + 0.20667 * ma ** 2)/(1 + 0.1451 * ma ** 1.5)
		h2 = (0.8889 - 0.55063 * ma + 0.50152 * ma ** 2)/(1 + 0.14865 * ma ** 1.5)
		return (h0 + h1 * tau_a)/(1 + h2 * tau_a)

def GetAerosolTransmittance(band, ma, tau_a):
	# returns Ta
	return math.exp(-ma * tau_a)

def GetAerosolScatteringTransmittance(band, ma, tau_a):
	# returns Tas
	return math.exp(-ma * albedo[band] * tau_a)

def GetBeamBroadbandIrradiance(Ebn, altitude_deg):
	Z = 90 - altitude_deg
	return Ebn * math.cos(math.radians(Z))

def GetDiffuseIrradiance():
	return GetDiffuseIrradianceByBand("high-frequency") + GetDiffuseIrradianceByBand("low-frequency")

def GetDiffuseIrradianceByBand(band, air_mass=1.66, turbidity_alpha=1.3, turbidity_beta=0.6):
	Z = 90 - altitude_deg
	effective_wavelength = GetEffectiveAerosolWavelength(band, turbidity_alpha)
	tau_a = GetAerosolOpticalDepth(turbidity_beta, effective_wavelength, turbidity_alpha)
	rhosi = GetSkyAlbedo(band, turbidity_alpha, turbidity_beta)

	ma = GetOpticalMassAerosol(altitude_deg)
	mo = GetOpticalMassOzone(altitude_deg)
	mR = GetOpticalMassRayleigh(altitude_deg, pressure_millibars)

	To = GetOzoneTransmittance(band, mo)
	Tg = GetGasTransmittance(band, mR)
	Tn = GetNitrogenTransmittance(band, 1.66)
	Tw = GetWaterVaporTransmittance(band, 1.66)
	TR = GetRayleighTransmittance(band, mR)
	Ta = GetAerosolTransmittance(band, ma, tau_a)
	Tas = GetAerosolScatteringTransmittance(band, ma, tau_a)

	BR = GetRayleighExtinctionForwardScatteringFraction(band, air_mass)
	Ba = GetAerosolForwardScatteranceFactor(altitude_deg)
	F = GetAerosolScatteringCorrectionFactor(band, ma, tau_a)

	Edp = To * Tg * Tn * Tw * (BR * (1 - TR) * Ta ** 0.25 + Ba * F * TR * (1 - Tas ** 0.25)) * E0n[band]
	Edd = rhogi * rhosi * (Eb + Edp)/(1 - rhogi * rhosi)
	return Edp + Edd

def GetDirectNormalIrradiance(altitude_deg, pressure_millibars=1013.25, ozone_atm_cm=0.35, nitrogen_atm_cm=0.0002, precipitable_water_cm=5.0, turbidity_alpha=1.3, turbidity_beta=0.6):
	high = GetDirectNormalIrradianceByBand("high-frequency", altitude_deg, pressure_millibars, ozone_atm_cm, nitrogen_atm_cm, precipitable_water_cm, turbidity_alpha, turbidity_beta)
	low = GetDirectNormalIrradianceByBand("low-frequency", altitude_deg, pressure_millibars, ozone_atm_cm, nitrogen_atm_cm, precipitable_water_cm, turbidity_alpha, turbidity_beta)
	return high + low

def GetDirectNormalIrradianceByBand(band, altitude_deg, pressure_millibars=1013.25, ozone_atm_cm=0.35, nitrogen_atm_cm=0.0002, precipitable_water_cm=5.0, turbidity_alpha=1.3, turbidity_beta=0.6):
	ma = GetOpticalMassAerosol(altitude_deg)
	mo = GetOpticalMassOzone(altitude_deg)
	mR = GetOpticalMassRayleigh(altitude_deg, pressure_millibars)
	mRprime = mR * pressure_millibars / 1013.25
	mw = GetOpticalMassWater(altitude_deg)

	effective_wavelength = GetEffectiveAerosolWavelength(band, ma, turbidity_alpha, turbidity_beta)
	tau_a = GetAerosolOpticalDepth(turbidity_beta, effective_wavelength, turbidity_alpha)

	TR = GetRayleighTransmittance(band, mRprime)
	Tg = GetGasTransmittance(band, mRprime)
	To = GetOzoneTransmittance(band, mo, ozone_atm_cm)
	Tn = GetNitrogenTransmittance(band, mw, nitrogen_atm_cm) # is water_optical_mass really used for nitrogen calc?
	Tw = GetWaterVaporTransmittance(band, mw, precipitable_water_cm)
	Ta = GetAerosolTransmittance(band, ma, tau_a)
	return E0n[band] * TR * Tg * To * Tn * Tw * Ta

def GetEffectiveAerosolWavelength(band, ma, turbidity_alpha, turbidity_beta):
	ua = math.log(1 + ma * turbidity_beta)
	if band == "high-frequency":
		a1 = turbidity_alpha # just renaming to keep equations short
		d0 = 0.57664 - 0.024743 * a1
		d1 = (0.093942 - 0.2269 * a1 + 0.12848 * a1 ** 2)/(1 + 0.6418 * a1)
		d2 = (-0.093819 + 0.36668 * a1 - 0.12775 * a1 ** 2)/(1 - 0.11651 * a1)
		d3 = a1 * (0.15232 - 0.087214 * a1 + 0.012664 * a1 ** 2)/(1 - 0.90454 * a1 + 0.26167 * a1 ** 2)
		return (d0 + d1 * ua + d2 * ua ** 2)/(1 + d3 * ua ** 2)
	else:
		a2 = turbidity_alpha
		e0 = (1.183 - 0.022989 * a2 + 0.020829 * a2 ** 2)/(1 + 0.11133 * a2)
		e1 = (-0.50003 - 0.18329 * a2 + 0.23835 * a2 ** 2)/(1 + 1.6756 * a2)
		e2 = (-0.50001 + 1.1414 * a2 + 0.0083589 * a2 ** 2)/(1 + 11.168 * a2)
		e3 = (-0.70003 - 0.73587 * a2 + 0.51509 * a2 ** 2)/(1 + 4.7665 * a2)
		return (e0 + e1 * ua + e2 * ua ** 2)/(1 + e3 * ua ** 2)

def GetGasTransmittance(band, mRprime):
	if band == "high-frequency":
		return (1 + 0.95885 * mRprime + 0.012871 * mRprime ** 2)/(1 + 0.96321 * mRprime + 0.015455 * mRprime ** 2)
	else:
		return (1 + 0.27284 * mRprime - 0.00063699 * mRprime ** 2)/(1 + 0.30306 * mRprime)

def GetBroadbandGlobalIrradiance(Ebn, altitude_deg, Ed):
	return GetBeamBroadbandIrradiance(Ebn, altitude_deg) + Ed

def GetNitrogenTransmittance(band, mw, nitrogen_atm_cm):
	if band == "high-frequency":
		g1 = (0.17499 + 41.654 * un - 2146.4 * un ** 2)/(1 + 22295.0 * un ** 2)
		g2 = un * (-1.2134 + 59.324 * un)/(1 + 8847.8 * un ** 2)
		g3 = (0.17499 + 61.658 * un + 9196.4 * un ** 2)/(1 + 74109.0 * un ** 2)
		return min (1, (1 + g1 * mw + g2 * mw ** 2)/(1 + g3 * mw))
	else:
		return 1.0

def GetOpticalMassRayleigh(altitude_deg, pressure_millibars): # from Appendix B of [Gueymard, 2003]
	Z = 90 - altitude_deg
	Z_rad = math.radians(Z)
	return (pressure_millibars / 1013.25)/((math.cos(Z_rad) + 0.48353 * Z_rad ** 0.095846)/(96.741 - Z_rad) ** 1.754)

def GetOpticalMassOzone(altitude_deg): # from Appendix B of [Gueymard, 2003]
	Z = 90 - altitude_deg
	Z_rad = math.radians(Z)
	return 1/((math.cos(Z_rad) + 1.0651 * Z_rad ** 0.6379)/(101.8 - Z_rad) ** 2.2694)

def GetOpticalMassWater(altitude_deg): # from Appendix B of [Gueymard, 2003]
	Z = 90 - altitude_deg
	Z_rad = math.radians(Z)
	return 1/((math.cos(Z_rad) + 0.10648 * Z_rad ** 0.11423)/(93.781 - Z_rad) ** 1.9203)

def GetOpticalMassAerosol(altitude_deg): # from Appendix B of [Gueymard, 2003]
	Z = 90 - altitude_deg
	Z_rad = math.radians(Z)
	return 1/((math.cos(Z_rad) + 0.16851 * Z_rad ** 0.18198)/(95.318 - Z_rad) ** 1.9542)

def GetOzoneTransmittance(band, mo, uo):
	if band == "high-frequency":
		f1 = uo(10.979 - 8.5421 * uo)/(1 + 2.0115 * uo + 40.189 * uo **2)
		f2 = uo(-0.027589 - 0.005138 * uo)/(1 - 2.4857 * uo + 13.942 * uo **2)
		f3 = uo(10.995 - 5.5001 * uo)/(1 + 1.6784 * uo + 42.406 * uo **2)
		return (1 + f1 * mo + f2 * mo ** 2)/(1 + f3 * mo)
	else:
		return 1.0

def GetRayleighExtinctionForwardScatteringFraction(band, mR):
	# returns BR
	if band == "high-frequency":
		return 0.5 * (0.89013 - 0.049558 * mR + 0.000045721 * mR ** 2)
	else:
		return 0.5

def GetRayleighTransmittance(band, mRprime):
	if band == "high-frequency":
		return (1 + 1.8169 * mRprime + 0.033454 * mRprime ** 2)/(1 + 2.063 * mRprime + 0.31978 * mRprime ** 2)
	else:
		return (1 - 0.010394 * mRprime)/(1 - 0.00011042 * mRprime ** 2)

def GetSkyAlbedo(band, turbidity_alpha, turbidity_beta):
	if band == "high-frequency":
		a1 = turbidity_alpha # just renaming to keep equations short
		b1 = turbidity_beta
		rhos = (0.13363 + 0.00077358 * a1 + b1 * (0.37567
		+ 0.22946 * a1)/(1 - 0.10832 * a1))/(1 + b1 * (0.84057
		+ 0.68683 * a1)/(1 - 0.08158 * a1))
	else:
		a2 = turbidity_alpha # just renaming to keep equations short
		b2 = turbidity_beta
		rhos = (0.010191 + 0.00085547 * a2 + b2 * (0.14618
		+ 0.062758 * a2)/(1 - 0.19402 * a2))/(1 + b2 * (0.58101
		+ 0.17426 * a2)/(1 - 0.17586 * a2))
	return rhos

def GetWaterVaporTransmittance(band, mw, w):
	if band == "high-frequency":
		h = GetWaterVaporTransmittanceCoefficients(band, w)
		return (1 + h[1] * mw)/(1 + h[2] * mw)
	else:
		c = GetWaterVaporTransmittanceCoefficients(band, w)
		return (1 + c[1] * mw + c[2] * mw ** 2)/(1 + c[3] * mw + c[4] * mw ** 2)

def GetWaterVaporTransmittanceCoefficients(band, w):
	if band == "high-frequency":
		h1 = w * (0.065445 + 0.00029901 * w)/(1 + 1.2728 * w)
		h2 = w * (0.065687 + 0.0013218 * w)/(1 + 1.2008 * w)
		return [float('NaN'), h1, h2]
	else:
		c1 = w * (19.566 - 1.6506 * w + 1.0672 * w ** 2)/(1 + 5.4248 * w + 1.6005 * w ** 2)
		c2 = w * (0.50158 - 0.14732 * w + 0.047584 * w ** 2)/(1 + 1.1811 * w + 1.0699 * w ** 2)
		c3 = w * (21.286 - 0.39232 * w + 1.2692 * w ** 2)/(1 + 4.8318 * w + 1.412 * w ** 2)
		c4 = w * (0.70992 - 0.23155 * w + 0.096514 * w ** 2)/(1 + 0.44907 * w + 0.75425 * w ** 2)
		return [float('NaN'), c1, c2, c3, c4]

########NEW FILE########
__FILENAME__ = simulate
#!/usr/bin/python

#    Copyright Brandon Stafford
#
#    This file is part of Pysolar.
#
#    Pysolar is free software; you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation; either version 3 of the License, or
#    (at your option) any later version.
#
#    Pysolar is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU General Public License along
#    with Pysolar. If not, see <http://www.gnu.org/licenses/>.

"""Support functions for horizon calculation 

"""
import datetime
from . import radiation
from . import solar
from math import *

def BuildTimeList(start_utc_datetime, end_utc_datetime, step_minutes):
	'''Create a list of sample points evenly spaced apart by step_minutes.'''
	step = step_minutes * 60
	time_list = []
	span = end_utc_datetime - start_utc_datetime
	dt = datetime.timedelta(seconds = step)
	return [start_utc_datetime + dt * n for n in range((span.days * 86400 + span.seconds) / step)]

def CheckAgainstHorizon(power):
    (time, alt, az, radiation, shade) = power
    alt_zero = 380

    if shade < alt_zero - int(alt_zero * sin(radians(alt))):
        radiation = 0

    return (time, alt, az, radiation, shade)

def SimulateSpan(latitude_deg, longitude_deg, horizon, start_utc_datetime, end_utc_datetime, step_minutes, elevation = 0, temperature_celsius = 25, pressure_millibars = 1013.25):
	'''Simulate the motion of the sun over a time span and location of your choosing.
	
	The start and end points are set by datetime objects, which can be created with
	the standard Python datetime module like this:
	import datetime
	start = datetime.datetime(2008, 12, 23, 23, 14, 0)
	'''
	time_list = BuildTimeList(start_utc_datetime, end_utc_datetime, step_minutes)
	
	angles_list = [(
		time,
		solar.GetAltitude(latitude_deg, longitude_deg, time, elevation, temperature_celsius, pressure_millibars),
		solar.GetAzimuth(latitude_deg, longitude_deg, time, elevation)
		) for time in time_list]	
	power_list = [(time, alt, az, radiation.GetRadiationDirect(time, alt), horizon[int(az)]) for (time, alt, az) in angles_list]
	return list(filter(CheckAgainstHorizon, power_list))
		
#		xs = shade.GetXShade(width, 120, azimuth_deg)
#		ys = shade.GetYShade(height, 120, altitude_deg)
#		shaded_area = xs * ys
#		shaded_percentage = shaded_area/area
# import simulate, datetime; s = datetime.datetime(2008,1,1); e = datetime.datetime(2008,1,5); simulate.SimulateSpan(42.0, -70.0, s, e, 30)

########NEW FILE########
__FILENAME__ = solar
#!/usr/bin/python

#    Copyright Brandon Stafford
#
#    This file is part of Pysolar.
#
#    Pysolar is free software; you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation; either version 3 of the License, or
#    (at your option) any later version.
#
#    Pysolar is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU General Public License along
#    with Pysolar. If not, see <http://www.gnu.org/licenses/>.

"""Solar geometry functions

This module contains the most important functions for calculation of the position of the sun.

"""
import math
import datetime
from . import constants
from . import julian
from . import radiation

#if __name__ == "__main__":
def SolarTest():
	latitude_deg = 42.364908
	longitude_deg = -71.112828
	d = datetime.datetime.utcnow()
	thirty_minutes = datetime.timedelta(hours = 0.5)
	for i in range(48):
		timestamp = d.ctime()
		altitude_deg = GetAltitude(latitude_deg, longitude_deg, d)
		azimuth_deg = GetAzimuth(latitude_deg, longitude_deg, d)
		power = radiation.GetRadiationDirect(d, altitude_deg)
		if (altitude_deg > 0):
			print(timestamp, "UTC", altitude_deg, azimuth_deg, power)
		d = d + thirty_minutes

def EquationOfTime(day):
	b = (2 * math.pi / 364.0) * (day - 81)
	return (9.87 * math.sin(2 *b)) - (7.53 * math.cos(b)) - (1.5 * math.sin(b))

def GetAberrationCorrection(radius_vector): 	# r is earth radius vector [astronomical units]
	return -20.4898/(3600.0 * radius_vector)

def GetAltitude(latitude_deg, longitude_deg, utc_datetime, elevation = 0, temperature_celsius = 25, pressure_millibars = 1013.25):
	'''See also the faster, but less accurate, GetAltitudeFast()'''
	# location-dependent calculations	
	projected_radial_distance = GetProjectedRadialDistance(elevation, latitude_deg)
	projected_axial_distance = GetProjectedAxialDistance(elevation, latitude_deg)

	# time-dependent calculations	
	jd = julian.GetJulianDay(utc_datetime)
	jde = julian.GetJulianEphemerisDay(jd, 65)
	jce = julian.GetJulianEphemerisCentury(jde)
	jme = julian.GetJulianEphemerisMillenium(jce)
	geocentric_latitude = GetGeocentricLatitude(jme)
	geocentric_longitude = GetGeocentricLongitude(jme)
	radius_vector = GetRadiusVector(jme)
	aberration_correction = GetAberrationCorrection(radius_vector)
	equatorial_horizontal_parallax = GetEquatorialHorizontalParallax(radius_vector)
	nutation = GetNutation(jde)
	apparent_sidereal_time = GetApparentSiderealTime(jd, jme, nutation)
	true_ecliptic_obliquity = GetTrueEclipticObliquity(jme, nutation)
	
	# calculations dependent on location and time
	apparent_sun_longitude = GetApparentSunLongitude(geocentric_longitude, nutation, aberration_correction)
	geocentric_sun_right_ascension = GetGeocentricSunRightAscension(apparent_sun_longitude, true_ecliptic_obliquity, geocentric_latitude)
	geocentric_sun_declination = GetGeocentricSunDeclination(apparent_sun_longitude, true_ecliptic_obliquity, geocentric_latitude)
	local_hour_angle = GetLocalHourAngle(apparent_sidereal_time, longitude_deg, geocentric_sun_right_ascension)
	parallax_sun_right_ascension = GetParallaxSunRightAscension(projected_radial_distance, equatorial_horizontal_parallax, local_hour_angle, geocentric_sun_declination)
	topocentric_local_hour_angle = GetTopocentricLocalHourAngle(local_hour_angle, parallax_sun_right_ascension)
	topocentric_sun_declination = GetTopocentricSunDeclination(geocentric_sun_declination, projected_axial_distance, equatorial_horizontal_parallax, parallax_sun_right_ascension, local_hour_angle)
	topocentric_elevation_angle = GetTopocentricElevationAngle(latitude_deg, topocentric_sun_declination, topocentric_local_hour_angle)
	refraction_correction = GetRefractionCorrection(pressure_millibars, temperature_celsius, topocentric_elevation_angle)
	return topocentric_elevation_angle + refraction_correction

def GetAltitudeFast(latitude_deg, longitude_deg, utc_datetime):

# expect 19 degrees for solar.GetAltitude(42.364908,-71.112828,datetime.datetime(2007, 2, 18, 20, 13, 1, 130320))

	day = GetDayOfYear(utc_datetime)
	declination_rad = math.radians(GetDeclination(day))
	latitude_rad = math.radians(latitude_deg)
	hour_angle = GetHourAngle(utc_datetime, longitude_deg)

	first_term = math.cos(latitude_rad) * math.cos(declination_rad) * math.cos(math.radians(hour_angle))
	second_term = math.sin(latitude_rad) * math.sin(declination_rad)
	return math.degrees(math.asin(first_term + second_term))

def GetApparentSiderealTime(julian_day, jme, nutation):
	return GetMeanSiderealTime(julian_day) + nutation['longitude'] * math.cos(GetTrueEclipticObliquity(jme, nutation))

def GetApparentSunLongitude(geocentric_longitude, nutation, ab_correction):
	return geocentric_longitude + nutation['longitude'] + ab_correction

def GetAzimuth(latitude_deg, longitude_deg, utc_datetime, elevation = 0):

	# location-dependent calculations	
	projected_radial_distance = GetProjectedRadialDistance(elevation, latitude_deg)
	projected_axial_distance = GetProjectedAxialDistance(elevation, latitude_deg)

	# time-dependent calculations	
	jd = julian.GetJulianDay(utc_datetime)
	jde = julian.GetJulianEphemerisDay(jd, 65)
	jce = julian.GetJulianEphemerisCentury(jde)
	jme = julian.GetJulianEphemerisMillenium(jce)
	geocentric_latitude = GetGeocentricLatitude(jme)
	geocentric_longitude = GetGeocentricLongitude(jme)
	radius_vector = GetRadiusVector(jme)
	aberration_correction = GetAberrationCorrection(radius_vector)
	equatorial_horizontal_parallax = GetEquatorialHorizontalParallax(radius_vector)
	nutation = GetNutation(jde)
	apparent_sidereal_time = GetApparentSiderealTime(jd, jme, nutation)
	true_ecliptic_obliquity = GetTrueEclipticObliquity(jme, nutation)
	
	# calculations dependent on location and time
	apparent_sun_longitude = GetApparentSunLongitude(geocentric_longitude, nutation, aberration_correction)
	geocentric_sun_right_ascension = GetGeocentricSunRightAscension(apparent_sun_longitude, true_ecliptic_obliquity, geocentric_latitude)
	geocentric_sun_declination = GetGeocentricSunDeclination(apparent_sun_longitude, true_ecliptic_obliquity, geocentric_latitude)
	local_hour_angle = GetLocalHourAngle(apparent_sidereal_time, longitude_deg, geocentric_sun_right_ascension)
	parallax_sun_right_ascension = GetParallaxSunRightAscension(projected_radial_distance, equatorial_horizontal_parallax, local_hour_angle, geocentric_sun_declination)
	topocentric_local_hour_angle = GetTopocentricLocalHourAngle(local_hour_angle, parallax_sun_right_ascension)
	topocentric_sun_declination = GetTopocentricSunDeclination(geocentric_sun_declination, projected_axial_distance, equatorial_horizontal_parallax, parallax_sun_right_ascension, local_hour_angle)
	return 180 - GetTopocentricAzimuthAngle(topocentric_local_hour_angle, latitude_deg, topocentric_sun_declination)

def GetAzimuthFast(latitude_deg, longitude_deg, utc_datetime):
# expect -50 degrees for solar.GetAzimuth(42.364908,-71.112828,datetime.datetime(2007, 2, 18, 20, 18, 0, 0))
	day = GetDayOfYear(utc_datetime)
	declination_rad = math.radians(GetDeclination(day))
	latitude_rad = math.radians(latitude_deg)
	hour_angle_rad = math.radians(GetHourAngle(utc_datetime, longitude_deg))
	altitude_rad = math.radians(GetAltitude(latitude_deg, longitude_deg, utc_datetime))

	azimuth_rad = math.asin(math.cos(declination_rad) * math.sin(hour_angle_rad) / math.cos(altitude_rad))

	if(math.cos(hour_angle_rad) >= (math.tan(declination_rad) / math.tan(latitude_rad))):
		return math.degrees(azimuth_rad)
	else:
		return (180 - math.degrees(azimuth_rad))

def GetCoefficient(jme, constant_array):
	return sum([constant_array[i-1][0] * math.cos(constant_array[i-1][1] + (constant_array[i-1][2] * jme)) for i in range(len(constant_array))])

def GetDayOfYear(utc_datetime):
	year_start = datetime.datetime(utc_datetime.year, 1, 1, tzinfo=utc_datetime.tzinfo)
	delta = (utc_datetime - year_start)
	return delta.days

def GetDeclination(day):
	'''The declination of the sun is the angle between
	Earth's equatorial plane and a line between the Earth and the sun.
	The declination of the sun varies between 23.45 degrees and -23.45 degrees,
	hitting zero on the equinoxes and peaking on the solstices.
	'''
	return 23.45 * math.sin((2 * math.pi / 365.0) * (day - 81))

def GetEquatorialHorizontalParallax(radius_vector):
	return 8.794 / (3600 / radius_vector)

def GetFlattenedLatitude(latitude):
	latitude_rad = math.radians(latitude)
	return math.degrees(math.atan(0.99664719 * math.tan(latitude_rad)))

# Geocentric functions calculate angles relative to the center of the earth.

def GetGeocentricLatitude(jme):
	return -1 * GetHeliocentricLatitude(jme)

def GetGeocentricLongitude(jme):
	return (GetHeliocentricLongitude(jme) + 180) % 360

def GetGeocentricSunDeclination(apparent_sun_longitude, true_ecliptic_obliquity, geocentric_latitude):
	apparent_sun_longitude_rad = math.radians(apparent_sun_longitude)
	true_ecliptic_obliquity_rad = math.radians(true_ecliptic_obliquity)
	geocentric_latitude_rad = math.radians(geocentric_latitude)

	a = math.sin(geocentric_latitude_rad) * math.cos(true_ecliptic_obliquity_rad)
	b = math.cos(geocentric_latitude_rad) * math.sin(true_ecliptic_obliquity_rad) * math.sin(apparent_sun_longitude_rad)
	delta = math.asin(a + b)
	return math.degrees(delta)

def GetGeocentricSunRightAscension(apparent_sun_longitude, true_ecliptic_obliquity, geocentric_latitude):
	apparent_sun_longitude_rad = math.radians(apparent_sun_longitude)
	true_ecliptic_obliquity_rad = math.radians(true_ecliptic_obliquity)
	geocentric_latitude_rad = math.radians(geocentric_latitude)

	a = math.sin(apparent_sun_longitude_rad) * math.cos(true_ecliptic_obliquity_rad)
	b = math.tan(geocentric_latitude_rad) * math.sin(true_ecliptic_obliquity_rad)
	c = math.cos(apparent_sun_longitude_rad)
	alpha = math.atan2((a - b),  c)
	return math.degrees(alpha) % 360

# Heliocentric functions calculate angles relative to the center of the sun.

def GetHeliocentricLatitude(jme):
	b0 = GetCoefficient(jme, constants.B0)
	b1 = GetCoefficient(jme, constants.B1)
	return math.degrees((b0 + (b1 * jme)) / 10 ** 8)

def GetHeliocentricLongitude(jme):
	l0 = GetCoefficient(jme, constants.L0)
	l1 = GetCoefficient(jme, constants.L1)
	l2 = GetCoefficient(jme, constants.L2)
	l3 = GetCoefficient(jme, constants.L3)
	l4 = GetCoefficient(jme, constants.L4)
	l5 = GetCoefficient(jme, constants.L5)

	l = (l0 + l1 * jme + l2 * jme ** 2 + l3 * jme ** 3 + l4 * jme ** 4 + l5 * jme ** 5) / 10 ** 8
	return math.degrees(l) % 360

def GetHourAngle(utc_datetime, longitude_deg):
	solar_time = GetSolarTime(longitude_deg, utc_datetime)
	return 15 * (12 - solar_time)

def GetIncidenceAngle(topocentric_zenith_angle, slope, slope_orientation, topocentric_azimuth_angle):
    tza_rad = math.radians(topocentric_zenith_angle)
    slope_rad = math.radians(slope)
    so_rad = math.radians(slope_orientation)
    taa_rad = math.radians(topocentric_azimuth_angle)
    return math.degrees(math.acos(math.cos(tza_rad) * math.cos(slope_rad) + math.sin(slope_rad) * math.sin(tza_rad) * math.cos(taa_rad - math.pi - so_rad)))

def GetLocalHourAngle(apparent_sidereal_time, longitude, geocentric_sun_right_ascension):
	return (apparent_sidereal_time + longitude - geocentric_sun_right_ascension) % 360

def GetMeanSiderealTime(julian_day):
	# This function doesn't agree with Andreas and Reda as well as it should. Works to ~5 sig figs in current unit test
	jc = julian.GetJulianCentury(julian_day)
	sidereal_time =  280.46061837 + (360.98564736629 * (julian_day - 2451545.0)) + (0.000387933 * jc ** 2) - (jc ** 3 / 38710000)
	return sidereal_time % 360

def GetNutationAberrationXY(jce, i, x):
	y = constants.aberration_sin_terms
	sigmaxy = 0.0
	for j in range(len(x)):
		sigmaxy += x[j] * y[i][j]
	return sigmaxy

def GetNutation(jde):
	abcd = constants.nutation_coefficients
	jce = julian.GetJulianEphemerisCentury(jde)
	nutation_long = []
	nutation_oblique = []
	x = PrecalculateAberrations(constants.buildPolyDict(), jce)

	for i in range(len(abcd)):
		sigmaxy = GetNutationAberrationXY(jce, i, x)
		nutation_long.append((abcd[i][0] + (abcd[i][1] * jce)) * math.sin(math.radians(sigmaxy)))
		nutation_oblique.append((abcd[i][2] + (abcd[i][3] * jce)) * math.cos(math.radians(sigmaxy)))

	# 36000000 scales from 0.0001 arcseconds to degrees
	nutation = {'longitude' : sum(nutation_long)/36000000.0, 'obliquity' : sum(nutation_oblique)/36000000.0}

	return nutation

def GetParallaxSunRightAscension(projected_radial_distance, equatorial_horizontal_parallax, local_hour_angle, geocentric_sun_declination):
	prd = projected_radial_distance
	ehp_rad = math.radians(equatorial_horizontal_parallax)
	lha_rad = math.radians(local_hour_angle)
	gsd_rad = math.radians(geocentric_sun_declination)
	a = -1 * prd * math.sin(ehp_rad) * math.sin(lha_rad)
	b =  math.cos(gsd_rad) - prd * math.sin(ehp_rad) * math.cos(lha_rad)
	parallax = math.atan2(a, b)
	return math.degrees(parallax)

def GetProjectedRadialDistance(elevation, latitude):
	flattened_latitude_rad = math.radians(GetFlattenedLatitude(latitude))
	latitude_rad = math.radians(latitude)
	return math.cos(flattened_latitude_rad) + (elevation * math.cos(latitude_rad) / constants.earth_radius)

def GetProjectedAxialDistance(elevation, latitude):
	flattened_latitude_rad = math.radians(GetFlattenedLatitude(latitude))
	latitude_rad = math.radians(latitude)
	return 0.99664719 * math.sin(flattened_latitude_rad) + (elevation * math.sin(latitude_rad) / constants.earth_radius)

def GetRadiusVector(jme):
	r0 = GetCoefficient(jme, constants.R0)
	r1 = GetCoefficient(jme, constants.R1)
	r2 = GetCoefficient(jme, constants.R2)
	r3 = GetCoefficient(jme, constants.R3)
	r4 = GetCoefficient(jme, constants.R4)

	return (r0 + r1 * jme + r2 * jme ** 2 + r3 * jme ** 3 + r4 * jme ** 4) / 10 ** 8

def GetRefractionCorrection(pressure_millibars, temperature_celsius, topocentric_elevation_angle):
    tea = topocentric_elevation_angle
    temperature_kelvin = temperature_celsius + 273.15
    a = pressure_millibars * 283.0 * 1.02
    b = 1010.0 * temperature_kelvin * 60.0 * math.tan(math.radians(tea + (10.3/(tea + 5.11))))
    return a / b

def GetSolarTime(longitude_deg, utc_datetime):
    day = GetDayOfYear(utc_datetime)
    return (((utc_datetime.hour * 60) + utc_datetime.minute + (4 * longitude_deg) + EquationOfTime(day))/60)

# Topocentric functions calculate angles relative to a location on the surface of the earth.

def GetTopocentricAzimuthAngle(topocentric_local_hour_angle, latitude, topocentric_sun_declination):
    """Measured eastward from north"""
    tlha_rad = math.radians(topocentric_local_hour_angle)
    latitude_rad = math.radians(latitude)
    tsd_rad = math.radians(topocentric_sun_declination)
    a = math.sin(tlha_rad)
    b = math.cos(tlha_rad) * math.sin(latitude_rad) - math.tan(tsd_rad) * math.cos(latitude_rad)
    return 180.0 + math.degrees(math.atan2(a, b)) % 360

def GetTopocentricElevationAngle(latitude, topocentric_sun_declination, topocentric_local_hour_angle):
    latitude_rad = math.radians(latitude)
    tsd_rad = math.radians(topocentric_sun_declination)
    tlha_rad = math.radians(topocentric_local_hour_angle)
    return math.degrees(math.asin((math.sin(latitude_rad) * math.sin(tsd_rad)) + math.cos(latitude_rad) * math.cos(tsd_rad) * math.cos(tlha_rad)))

def GetTopocentricLocalHourAngle(local_hour_angle, parallax_sun_right_ascension):
    return local_hour_angle - parallax_sun_right_ascension

def GetTopocentricSunDeclination(geocentric_sun_declination, projected_axial_distance, equatorial_horizontal_parallax, parallax_sun_right_ascension, local_hour_angle):
    gsd_rad = math.radians(geocentric_sun_declination)
    pad = projected_axial_distance
    ehp_rad = math.radians(equatorial_horizontal_parallax)
    psra_rad = math.radians(parallax_sun_right_ascension)
    lha_rad = math.radians(local_hour_angle)
    a = (math.sin(gsd_rad) - pad * math.sin(ehp_rad)) * math.cos(psra_rad)
    b = math.cos(gsd_rad) - (pad * math.sin(ehp_rad) * math.cos(lha_rad))
    return math.degrees(math.atan2(a, b))

def GetTopocentricSunRightAscension(projected_radial_distance, equatorial_horizontal_parallax, local_hour_angle,
        apparent_sun_longitude, true_ecliptic_obliquity, geocentric_latitude):
    gsd = GetGeocentricSunDeclination(apparent_sun_longitude, true_ecliptic_obliquity, geocentric_latitude)
    psra = GetParallaxSunRightAscension(projected_radial_distance, equatorial_horizontal_parallax, local_hour_angle, gsd)
    gsra = GetGeocentricSunRightAscension(apparent_sun_longitude, true_ecliptic_obliquity, geocentric_latitude)
    return psra + gsra

def GetTopocentricZenithAngle(latitude, topocentric_sun_declination, topocentric_local_hour_angle, pressure_millibars, temperature_celsius):
    tea = GetTopocentricElevationAngle(latitude, topocentric_sun_declination, topocentric_local_hour_angle)
    return 90 - tea - GetRefractionCorrection(pressure_millibars, temperature_celsius, tea)

def GetTrueEclipticObliquity(jme, nutation):
	u = jme/10.0
	mean_obliquity = 84381.448 - (4680.93 * u) - (1.55 * u ** 2) + (1999.25 * u ** 3) \
	- (51.38 * u ** 4) -(249.67 * u ** 5) - (39.05 * u ** 6) + (7.12 * u ** 7) \
	+ (27.87 * u ** 8) + (5.79 * u ** 9) + (2.45 * u ** 10)
	return (mean_obliquity / 3600.0) + nutation['obliquity']

def PrecalculateAberrations(p, jce):
	x = []
	# order of 5 x.append lines below is important
	x.append(p['MeanElongationOfMoon'](jce))
	x.append(p['MeanAnomalyOfSun'](jce))
	x.append(p['MeanAnomalyOfMoon'](jce))
	x.append(p['ArgumentOfLatitudeOfMoon'](jce))
	x.append(p['LongitudeOfAscendingNode'](jce))
	return x

########NEW FILE########
__FILENAME__ = testsolar
#!/usr/bin/python

#    Library for calculating location of the sun

#    Copyright Brandon Stafford
#
#    This file is part of Pysolar.
#
#    Pysolar is free software; you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation; either version 3 of the License, or
#    (at your option) any later version.
#
#    Pysolar is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU General Public License along
#    with Pysolar. If not, see <http://www.gnu.org/licenses/>.

from . import solar
from . import constants
from . import julian
from . import elevation
import datetime
import unittest

class testSolar(unittest.TestCase):

	def setUp(self):
		self.d = datetime.datetime(2003, 10, 17, 19, 30, 30)
		self.longitude = -105.1786
		self.latitude = 39.742476
		self.pressure = 820.0 # millibars
		self.elevation = 1830.14 # meters
		self.temperature = 11.0 # degrees Celsius
		self.slope = 30.0 # degrees
		self.slope_orientation = -10.0 # degrees east from south
		self.jd = julian.GetJulianDay(self.d)
		self.jc = julian.GetJulianCentury(self.jd)
		self.jde = julian.GetJulianEphemerisDay(self.jd, 67.0)
		self.jce = julian.GetJulianEphemerisCentury(self.jde)
		self.jme = julian.GetJulianEphemerisMillenium(self.jce)
		self.geocentric_longitude = solar.GetGeocentricLongitude(self.jme)
		self.geocentric_latitude = solar.GetGeocentricLatitude(self.jme)
		self.nutation = solar.GetNutation(self.jde)
		self.radius_vector = solar.GetRadiusVector(self.jme)
		self.true_ecliptic_obliquity = solar.GetTrueEclipticObliquity(self.jme, self.nutation)
		self.aberration_correction = solar.GetAberrationCorrection(self.radius_vector)
		self.apparent_sun_longitude = solar.GetApparentSunLongitude(self.geocentric_longitude, self.nutation, self.aberration_correction)
		self.apparent_sidereal_time = solar.GetApparentSiderealTime(self.jd, self.jme, self.nutation)
		self.geocentric_sun_right_ascension = solar.GetGeocentricSunRightAscension(self.apparent_sun_longitude, self.true_ecliptic_obliquity, self.geocentric_latitude)
		self.geocentric_sun_declination = solar.GetGeocentricSunDeclination(self.apparent_sun_longitude, self.true_ecliptic_obliquity, self.geocentric_latitude)
		self.local_hour_angle = solar.GetLocalHourAngle(318.5119, self.longitude, self.geocentric_sun_right_ascension) #self.apparent_sidereal_time only correct to 5 sig figs, so override
		self.equatorial_horizontal_parallax = solar.GetEquatorialHorizontalParallax(self.radius_vector)
		self.projected_radial_distance = solar.GetProjectedRadialDistance(self.elevation, self.latitude)
		self.projected_axial_distance = solar.GetProjectedAxialDistance(self.elevation, self.latitude)
		self.topocentric_sun_right_ascension = solar.GetTopocentricSunRightAscension(self.projected_radial_distance,
		self.equatorial_horizontal_parallax, self.local_hour_angle, self.apparent_sun_longitude, self.true_ecliptic_obliquity, self.geocentric_latitude)
		self.parallax_sun_right_ascension = solar.GetParallaxSunRightAscension(self.projected_radial_distance, self.equatorial_horizontal_parallax, self.local_hour_angle, self.geocentric_sun_declination)
		self.topocentric_sun_declination = solar.GetTopocentricSunDeclination(self.geocentric_sun_declination, self.projected_axial_distance, self.equatorial_horizontal_parallax, self.parallax_sun_right_ascension, self.local_hour_angle)
		self.topocentric_local_hour_angle = solar.GetTopocentricLocalHourAngle(self.local_hour_angle, self.parallax_sun_right_ascension)
		self.topocentric_zenith_angle = solar.GetTopocentricZenithAngle(self.latitude, self.topocentric_sun_declination, self.topocentric_local_hour_angle, self.pressure, self.temperature)
		self.topocentric_azimuth_angle = solar.GetTopocentricAzimuthAngle(self.topocentric_local_hour_angle, self.latitude, self.topocentric_sun_declination)
		self.incidence_angle = solar.GetIncidenceAngle(self.topocentric_zenith_angle, self.slope, self.slope_orientation, self.topocentric_azimuth_angle)
		self.pressure_with_elevation = elevation.GetPressureWithElevation(1567.7)
		self.temperature_with_elevation = elevation.GetTemperatureWithElevation(1567.7)

	def testGetJulianDay(self):
		self.assertAlmostEqual(2452930.312847, self.jd, 6) # value from Reda and Andreas (2005)

	def testGetJulianEphemerisDay(self):
		self.assertAlmostEqual(2452930.3136, self.jde, 4) # value not validated

	def testGetJulianCentury(self):
		self.assertAlmostEqual(0.03792779869191517, self.jc, 12) # value not validated

	def testGetJulianEphemerisMillenium(self):
		self.assertAlmostEqual(0.0037927819922933584, self.jme, 12) # value not validated

	def testGetGeocentricLongitude(self):
		self.assertAlmostEqual(204.0182635175, self.geocentric_longitude, 10) # value from Reda and Andreas (2005)

	def testGetGeocentricLatitude(self):
		self.assertAlmostEqual(0.0001011219, self.geocentric_latitude, 9) # value from Reda and Andreas (2005)

	def testGetNutation(self):
		self.assertAlmostEqual(0.00166657, self.nutation['obliquity'], 8) # value from Reda and Andreas (2005)
		self.assertAlmostEqual(-0.00399840, self.nutation['longitude'], 8) # value from Reda and Andreas (2005)

	def testGetRadiusVector(self):
		self.assertAlmostEqual(0.9965421031, self.radius_vector, 7) # value from Reda and Andreas (2005)

	def testGetTrueEclipticObliquity(self):
		self.assertAlmostEqual(23.440465, self.true_ecliptic_obliquity, 6) # value from Reda and Andreas (2005)

	def testGetAberrationCorrection(self):
		self.assertAlmostEqual(-0.0057113603, self.aberration_correction, 9) # value not validated

	def testGetApparentSunLongitude(self):
		self.assertAlmostEqual(204.0085537528, self.apparent_sun_longitude, 10) # value from Reda and Andreas (2005)

	def testGetApparentSiderealTime(self):
		self.assertAlmostEqual(318.5119, self.apparent_sidereal_time, 2) # value derived from Reda and Andreas (2005)

	def testGetGeocentricSunRightAscension(self):
		self.assertAlmostEqual(202.22741, self.geocentric_sun_right_ascension, 4) # value from Reda and Andreas (2005)

	def testGetGeocentricSunDeclination(self):
		self.assertAlmostEqual(-9.31434, self.geocentric_sun_declination, 4) # value from Reda and Andreas (2005)

	def testGetLocalHourAngle(self):
		self.assertAlmostEqual(11.105900, self.local_hour_angle, 4) # value from Reda and Andreas (2005)

	def testGetProjectedRadialDistance(self):
		self.assertAlmostEqual(0.7702006, self.projected_radial_distance, 6) # value not validated

	def testGetTopocentricSunRightAscension(self):
		self.assertAlmostEqual(202.22741, self.topocentric_sun_right_ascension, 3) # value from Reda and Andreas (2005)

	def testGetParallaxSunRightAscension(self):
		self.assertAlmostEqual(-0.00036599029186055283, self.parallax_sun_right_ascension, 12) # value not validated
		
	def testGetTopocentricSunDeclination(self):
		self.assertAlmostEqual(-9.316179, self.topocentric_sun_declination, 3) # value from Reda and Andreas (2005)

	def testGetTopocentricLocalHourAngle(self):
		self.assertAlmostEqual(11.10629, self.topocentric_local_hour_angle, 4) # value from Reda and Andreas (2005)

	def testGetTopocentricZenithAngle(self):
		self.assertAlmostEqual(50.11162, self.topocentric_zenith_angle, 3) # value from Reda and Andreas (2005)

	def testGetTopocentricAzimuthAngle(self):
		self.assertAlmostEqual(194.34024, self.topocentric_azimuth_angle, 5) # value from Reda and Andreas (2005)

	def testGetIncidenceAngle(self):
		self.assertAlmostEqual(25.18700, self.incidence_angle, 3) # value from Reda and Andreas (2005)

	def testPressureWithElevation(self):
		self.assertAlmostEqual(83855.90228, self.pressure_with_elevation, 4)

	def testTemperatureWithElevation(self):
		self.assertAlmostEqual(277.9600, self.temperature_with_elevation, 4)

suite = unittest.TestLoader().loadTestsFromTestCase(testSolar)
unittest.TextTestRunner(verbosity=2).run(suite)

# if __name__ == "__main__":
#	unittest.main()


########NEW FILE########
__FILENAME__ = util
#!/usr/bin/env python

# -*- coding: utf-8 -*-

#    Copyright Brandon Stafford
#
#    This file is part of Pysolar.
#
#    Pysolar is free software; you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation; either version 3 of the License, or
#    (at your option) any later version.
#
#    Pysolar is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU General Public License along
#    with Pysolar. If not, see <http://www.gnu.org/licenses/>.

"""Additional support functions for solar geometry, astronomy, radiation correlation

:Original author: Simeon Nwaogaidu
:Contact: SimeonObinna.Nwaogaidu AT lahmeyer DOT de

:Additional author: Holger Zebner
:Contact: holger.zebner AT lahmeyer DOT de

:Additional author: Brandon Stafford

"""
from datetime import datetime as dt
from datetime import timedelta
import math
import pytz
from pytz import all_timezones
from . import solar

# Some default constants

AM_default = 2.0             # Default air mass is 2.0
TL_default = 1.0             # Default Linke turbidity factor is 1.0 
SC_default = 1367.0          # Solar constant in W/m^2 is 1367.0. Note that this value could vary by +/-4 W/m^2 
TY_default = 365             # Total year number from 1 to 365 days
elevation_default = 0.0      # Default elevation is 0.0

# Useful equations for analysis

def GetSunriseSunset(latitude_deg, longitude_deg, utc_datetime, timezone):
    """This function calculates the astronomical sunrise and sunset times in local time.
    
    Parameters
    ----------
    latitude_deg : float
        latitude in decimal degree. A geographical term denoting 
        the north/south angular location of a place on a sphere.            
    longitude_deg : float
        longitude in decimal degree. Longitude shows your location 
        in an east-west direction,relative to the Greenwich meridian.        
    utc_datetime : date_object
        utc_datetime. UTC DateTime is for Universal Time ( i.e. like a GMT+0 )        
    timezone : float
        timezone as numerical value: GMT offset in hours. A time zone is a region of 
        the earth that has uniform standard time, usually referred to as the local time.
               
    Returns
    -------
    sunrise_time_dt : datetime.datetime
        Sunrise time in local time as datetime_obj.
    sunset_time_dt : datetime.datetime
        Sunset time in local time as datetime_obj.
            
    References
    ----------
    .. [1] http://www.skypowerinternational.com/pdf/Radiation/7.1415.01.121_cm121_bed-anleitung_engl.pdf
    .. [2] http://pysolar.org/
        
    Examples
    --------
    >>> gmt_offset = 1
    >>> lat = 50.111512
    >>> lon = 8.680506
    >>> timezone_local = 'Europe/Berlin'
    >>> utct = dt.datetime.utcnow()
    >>> sr, ss = sb.GetSunriseSunset(lat, lon, utct, gmt_offset)
    >>> print 'sunrise: ', sr
    >>> print 'sunset:', ss
   
    """

    # Day of the year
    day = solar.GetDayOfYear(utc_datetime)

    # Solar hour angle
    SHA = ((timezone)* 15.0 - longitude_deg)

    # Time adjustment
    TT = (279.134+0.985647*day)*math.pi/180

    # Time adjustment in hours
    time_adst = ((5.0323 - 100.976*math.sin(TT)+595.275*math.sin(2*TT)+
                  3.6858*math.sin(3*TT) - 12.47*math.sin(4*TT) - 430.847*math.cos(TT)+
                  12.5024*math.cos(2*TT) + 18.25*math.cos(3*TT))/3600)
 
    # Time of noon
    TON = (12 + (SHA/15.0) - time_adst)
    
    sunn = (math.pi/2-(23.45*math.pi/180)*math.tan(latitude_deg*math.pi/180)*
            math.cos(2*math.pi*day/365.25))*(180/(math.pi*15))

    # Sunrise_time in hours
    sunrise_time = (TON - sunn + time_adst)
 
    # Sunset_time in hours
    sunset_time = (TON + sunn - time_adst) 

    sunrise_time_dt = date_with_decimal_hour(utc_datetime, sunrise_time)    
    sunset_time_dt = date_with_decimal_hour(utc_datetime, sunset_time)    

    return sunrise_time_dt, sunset_time_dt

def GetSunriseTime(latitude_deg, longitude_deg, utc_datetime, timezone):
    "Wrapper for GetSunriseSunset that returns just the sunrise time" 
    sr, ss = GetSunriseSunset(latitude_deg, longitude_deg, utc_datetime, timezone)
    
    return sr

def GetSunsetTime(latitude_deg, longitude_deg, utc_datetime, timezone):
    "Wrapper for GetSunriseSunset that returns just the sunset time" 
    sr, ss = GetSunriseSunset(latitude_deg, longitude_deg, utc_datetime, timezone)    
    return ss

def mean_earth_sun_distance(utc_datetime):
    """Mean Earth-Sun distance is the arithmetical mean of the maximum and minimum distances
    between a planet (Earth) and the object about which it revolves (Sun). However, 
    the function is used to  calculate the Mean earth sun distance.
    
    Parameters
    ----------
    utc_datetime : date_object
        utc_datetime. UTC DateTime is for Universal Time ( i.e. like a GMT+0 ) 
                         
    Returns
    -------
    KD : float
        Mean earth sun distance
    
    References
    ----------
    .. [1] http://sunbird.jrc.it/pvgis/solres/solmod3.htm#clear-sky%20radiation
    .. [2] R. aguiar and et al, "The ESRA user guidebook, vol. 2. database", models and exploitation software-Solar 
            radiation models, p.113
    """   

    return (1 - (0.0335 * math.sin(360 * ((solar.GetDayOfYear(utc_datetime)) - 94)) / (365)))

def extraterrestrial_irrad(utc_datetime, latitude_deg, longitude_deg,SC=SC_default):
    """Equation calculates Extratrestrial radiation. Solar radiation incident outside the earth's
    atmosphere is called extraterrestrial radiation. On average the extraterrestrial irradiance
    is 1367 Watts/meter2 (W/m2). This value varies by + or - 3 percent as the earth orbits the sun. 
    The earth's closest approach to the sun occurs around January 4th and it is furthest
    from the sun around July 5th.
    
    Parameters
    ----------
    utc_datetime : date_object
        utc_datetime. UTC DateTime is for Universal Time ( i.e. like a GMT+0 )                   
    latitude_deg : float
        latitude in decimal degree. A geographical term denoting the north/south angular location 
        of a place on a sphere.    
    longitude_deg : float
        longitude in decimal degree. Longitude shows your location in an east-west direction,relative
        to the Greenwich meridian.    
    SC : float
        The solar constant is the amount of incoming solar electromagnetic radiation per unit area, measured 
        on the outer surface of Earth's atmosphere in a plane perpendicular to the rays.It is measured by 
        satellite to be roughly 1366 watts per square meter (W/m^2)
    
    Returns
    -------
    EXTR1 : float
        Extraterrestrial irradiation
    
    References
    ----------
    .. [1] http://solardat.uoregon.edu/SolarRadiationBasics.html
    .. [2] Dr. J. Schumacher and et al,"INSEL LE(Integrated Simulation Environment Language)Block reference",p.68
        
    """
    day = solar.GetDayOfYear(utc_datetime)
    ab = math.cos(2 * math.pi * (solar.GetDayOfYear(utc_datetime) - 1.0)/(365.0))
    bc = math.sin(2 * math.pi * (solar.GetDayOfYear(utc_datetime) - 1.0)/(365.0))
    cd = math.cos(2 * (2 * math.pi * (solar.GetDayOfYear(utc_datetime) - 1.0)/(365.0)))
    df = math.sin(2 * (2 * math.pi * (solar.GetDayOfYear(utc_datetime) - 1.0)/(365.0)))
    decl = solar.GetDeclination(day)
    ha = solar.GetHourAngle(utc_datetime, longitude_deg)
    ZA = math.sin(latitude_deg) * math.sin(decl) + math.cos(latitude_deg) * math.cos(decl) * math.cos(ha)
    
    return SC * ZA * (1.00010 + 0.034221 * ab + 0.001280 * bc + 0.000719 * cd + 0.000077 * df)


def declination_degree(utc_datetime, TY = TY_default ):
    """The declination of the sun is the angle between Earth's equatorial plane and a line 
    between the Earth and the sun. It varies between 23.45 degrees and -23.45 degrees,
    hitting zero on the equinoxes and peaking on the solstices.
    
    Parameters
    ----------
    utc_datetime : date_object
        utc_datetime. UTC DateTime is for Universal Time ( i.e. like a GMT+0 )        
    TY : float
        Total number of days in a year. eg. 365 days per year,(no leap days)
    
    Returns
    -------
    DEC : float
        The declination of the Sun 
    
    References
    ----------
    .. [1] http://pysolar.org/
             
    """    
    return 23.45 * math.sin((2 * math.pi / (TY)) * ((solar.GetDayOfYear(utc_datetime)) - 81))


def solarelevation_function_clear(latitude_deg, longitude_deg, utc_datetime,temperature_celsius = 25,
                                  pressure_millibars = 1013.25,  elevation = elevation_default):
    """Equation calculates Solar elevation function for clear sky type.
    
    Parameters
    ----------
    latitude_deg : float
        latitude in decimal degree. A geographical term denoting 
        the north/south angular location of a place on a sphere.            
    longitude_deg : float
        longitude in decimal degree. Longitude shows your location 
        in an east-west direction,relative to the Greenwich meridian.        
    utc_datetime : date_object
        utc_datetime. UTC DateTime is for Universal Time ( i.e. like a GMT+0 )         
    temperature_celsius : float
        Temperature is a physical property of a system that underlies the common notions of hot and cold.    
    pressure_millibars : float
        pressure_millibars    
    elevation : float
        The elevation of a geographic location is its height above a fixed reference point, often the mean
        sea level.
    
    Returns
    -------
    SOLALTC : float
        Solar elevation function clear sky 
        
    References
    ----------
    .. [1] S. Younes, R.Claywell and el al,"Quality control of solar radiation data: present status 
            and proposed new approaches", energy 30 (2005), pp 1533 - 1549.
    
    """
    altitude = solar.GetAltitude(latitude_deg, longitude_deg,utc_datetime, elevation, temperature_celsius,pressure_millibars)        
    return (0.038175 + (1.5458 * (math.sin(altitude))) + ((-0.59980) * (0.5 * (1 - math.cos(2 * (altitude))))))

def solarelevation_function_overcast(latitude_deg, longitude_deg, utc_datetime,
                                     elevation = elevation_default, temperature_celsius = 25,
                                     pressure_millibars = 1013.25):
    """ The function calculates solar elevation function for overcast sky type. 
    This associated hourly overcast radiation model is based on the estimation of the 
    overcast sky transmittance with the sun directly overhead combined with the application 
    of an over sky elavation function to estimate the overcast day global irradiation 
    value at any solar elevation.
    
    Parameters
    ----------
    latitude_deg : float
        latitude in decimal degree. A geographical term denoting the north/south angular location of a place on a 
        sphere.            
    longitude_deg : float
        longitude in decimal degree. Longitude shows your location in an east-west direction,relative to the 
        Greenwich meridian.        
    utc_datetime : date_object 
        utc_datetime. UTC DateTime is for Universal Time ( i.e. like a GMT+0 ) 
    elevation : float 
        The elevation of a geographic location is its height above a fixed reference point, often the mean sea level.        
    temperature_celsius : float 
        Temperature is a physical property of a system that underlies the common notions of hot and cold.    
    pressure_millibars : float
        pressure_millibars  
                               
    Returns
    -------
    SOLALTO : float
        Solar elevation function overcast
    
    References
    ----------
    .. [1] Prof. Peter Tregenza,"Solar radiation and daylight models", p.89.
    
    .. [2] Also accessible through Google Books: http://tinyurl.com/5kdbwu
        Tariq Muneer, "Solar Radiation and Daylight Models, Second Edition: For the Energy Efficient 
        Design of Buildings"  
            
    """
    altitude = solar.GetAltitude(latitude_deg, longitude_deg,utc_datetime, elevation, temperature_celsius,pressure_millibars)
    return ((-0.0067133) + (0.78600 * (math.sin(altitude)))) + (0.22401 * (0.5 * (1 - math.cos(2 * altitude))))


def diffuse_transmittance(TL = TL_default):
    """Equation calculates the Diffuse_transmittance and the is the Theoretical Diffuse Irradiance on a horizontal 
    surface when the sun is at the zenith.
    
    Parameters
    ----------
    TL : float
        Linke turbidity factor 
        
    Returns
    -------
    DT : float
        diffuse_transmittance
    
    References
    ----------
    .. [1] S. Younes, R.Claywell and el al,"Quality control of solar radiation data: present status and proposed 
            new approaches", energy 30 (2005), pp 1533 - 1549.
    
    """
    return ((-21.657) + (41.752 * (TL)) + (0.51905 * (TL) * (TL)))


def diffuse_underclear(latitude_deg, longitude_deg, utc_datetime, elevation = elevation_default, 
                       temperature_celsius = 25, pressure_millibars = 1013.25, TL=TL_default):    
    """Equation calculates diffuse radiation under clear sky conditions.
    
    Parameters
    ----------
    latitude_deg : float
        latitude in decimal degree. A geographical term denoting the north/south angular location of a place on 
        a sphere.            
    longitude_deg : float
        longitude in decimal degree. Longitude shows your location in an east-west direction,relative to the 
        Greenwich meridian.        
    utc_datetime : date_object
        utc_datetime. UTC DateTime is for Universal Time ( i.e. like a GMT+0 )
    elevation : float
        The elevation of a geographic location is its height above a fixed reference point, often the mean sea level.         
    temperature_celsius : float
        Temperature is a physical property of a system that underlies the common notions of hot and cold.    
    pressure_millibars : float
        pressure_millibars
    TL : float
        Linke turbidity factor     
    
    Returns
    -------
    DIFFC : float
        Diffuse Irradiation under clear sky
    
    References
    ----------
    .. [1] S. Younes, R.Claywell and el al,"Quality control of solar radiation data: present status and proposed 
            new approaches", energy 30 (2005), pp 1533 - 1549.
    
    """    
    DT = ((-21.657) + (41.752 * (TL)) + (0.51905 * (TL) * (TL)))
    altitude = solar.GetAltitude(latitude_deg, longitude_deg,utc_datetime, elevation, temperature_celsius,pressure_millibars)

    return mean_earth_sun_distance(utc_datetime) * DT * altitude

def diffuse_underovercast(latitude_deg, longitude_deg, utc_datetime, elevation = elevation_default,
                          temperature_celsius = 25, pressure_millibars = 1013.25,TL=TL_default):    
    """Function calculates the diffuse radiation under overcast conditions.
    
    Parameters
    ----------
    latitude_deg : float
        latitude in decimal degree. A geographical term denoting the north/south angular location of a place on a 
        sphere.            
    longitude_deg : float 
        longitude in decimal degree. Longitude shows your location in an east-west direction,relative to the 
        Greenwich meridian.        
    utc_datetime : date_object
        utc_datetime. UTC DateTime is for Universal Time ( i.e. like a GMT+0 )
    elevation : float
        The elevation of a geographic location is its height above a fixed reference point, often the mean sea level.         
    temperature_celsius : float
        Temperature is a physical property of a system that underlies the common notions of hot and cold.    
    pressure_millibars : float
        pressure_millibars
    TL : float
        Linke turbidity factor       
    
    Returns
    -------
    DIFOC : float
        Diffuse Irradiation under overcast
    
    References
    ----------
    .. [1] S. Younes, R.Claywell and el al,"Quality control of solar radiation data: present status and proposed 
            new approaches", energy 30 (2005), pp 1533 - 1549.
    
    """    
    DT = ((-21.657) + (41.752 * (TL)) + (0.51905 * (TL) * (TL)))
        
    DIFOC = ((mean_earth_sun_distance(utc_datetime)
              )*(DT)*(solar.GetAltitude(latitude_deg,longitude_deg, utc_datetime, elevation, 
                                        temperature_celsius, pressure_millibars)))    
    return DIFOC

def direct_underclear(latitude_deg, longitude_deg, utc_datetime, 
                      temperature_celsius = 25, pressure_millibars = 1013.25, TY = TY_default, 
                      AM = AM_default, TL = TL_default,elevation = elevation_default):    
    """Equation calculates direct radiation under clear sky conditions.
    
    Parameters
    ----------
    latitude_deg : float
        latitude in decimal degree. A geographical term denoting the north/south angular location of a 
        place on a sphere.            
    longitude_deg : float
        longitude in decimal degree. Longitude shows your location in an east-west direction,relative to the 
        Greenwich meridian.        
    utc_datetime : date_object
        utc_datetime. UTC DateTime is for Universal Time ( i.e. like a GMT+0 )           
    temperature_celsius : float
        Temperature is a physical property of a system that underlies the common notions of hot and cold.    
    pressure_millibars : float
        pressure_millibars
    TY : float
        Total number of days in a year. eg. 365 days per year,(no leap days)
    AM : float
        Air mass. An Air Mass is a measure of how far light travels through the Earth's atmosphere. One air mass,
        or AM1, is the thickness of the Earth's atmosphere. Air mass zero (AM0) describes solar irradiance in space,
        where it is unaffected by the atmosphere. The power density of AM1 light is about 1,000 W/m^2
    TL : float
        Linke turbidity factor 
    elevation : float
        The elevation of a geographic location is its height above a fixed reference point, often the mean 
        sea level.        
    
    Returns
    -------
    DIRC : float
        Direct Irradiation under clear
        
    References
    ----------
    .. [1] S. Younes, R.Claywell and el al,"Quality control of solar radiation data: present status and proposed 
           new approaches", energy 30 (2005), pp 1533 - 1549.
    
    """
    KD = mean_earth_sun_distance(utc_datetime)
    
    DEC = declination_degree(utc_datetime,TY)
    
    DIRC = (1367 * KD * math.exp(-0.8662 * (AM) * (TL) * (DEC)
                             ) * math.sin(solar.GetAltitude(latitude_deg,longitude_deg, 
                                                          utc_datetime,elevation , 
                                                          temperature_celsius , pressure_millibars )))
    
    return DIRC

def global_irradiance_clear(DIRC, DIFFC, latitude_deg, longitude_deg, utc_datetime, 
                            temperature_celsius = 25, pressure_millibars = 1013.25, TY = TY_default, 
                            AM = AM_default, TL = TL_default, elevation = elevation_default):
    
    """Equation calculates global irradiance under clear sky conditions.
    
    Parameters
    ----------
    DIRC : float
        Direct Irradiation under clear        
    DIFFC : float
        Diffuse Irradiation under clear sky
    
    latitude_deg : float
        latitude in decimal degree. A geographical term denoting the north/south angular location of a place
        on a sphere.            
    longitude_deg : float
        longitude in decimal degree. Longitude shows your location in an east-west direction,relative to 
        the Greenwich meridian.        
    utc_datetime : date_object
        utc_datetime. UTC DateTime is for Universal Time ( i.e. like a GMT+0 )
    temperature_celsius : float
        Temperature is a physical property of a system that underlies the common notions of hot and cold. 
    pressure_millibars : float
        pressure_millibars
    elevation : float
        The elevation of a geographic location is its height above a fixed reference point, often the 
        mean sea level.
    TY : float
        Total number of days in a year. eg. 365 days per year,(no leap days)
    AM : float
        Air mass. An Air Mass is a measure of how far light travels through the Earth's atmosphere. One air mass, 
        or AM1, is the thickness of the Earth's atmosphere. Air mass zero (AM0) describes solar irradiance in 
        space, where it is unaffected by the atmosphere. The power density of AM1 light is about 1,000 W/m.
        
    TL : float
        Linke turbidity factor 
    elevation : float
        The elevation of a geographic location is its height above a fixed reference point, often the mean sea 
        level.     
    
    Returns
    -------
    ghic : float
        Global Irradiation under clear sky
    
    References
    ----------
    .. [1] S. Younes, R.Claywell and el al,"Quality control of solar radiation data: present status and proposed 
            new approaches", energy 30 (2005), pp 1533 - 1549.
            
    """
    DIRC =  direct_underclear(latitude_deg, longitude_deg, utc_datetime, 
                              TY, AM, TL, elevation, temperature_celsius = 25, 
                              pressure_millibars = 1013.25)
    
    DIFFC = diffuse_underclear(latitude_deg, longitude_deg, utc_datetime, 
                               elevation, temperature_celsius = 25, pressure_millibars= 1013.25)
    
    ghic = (DIRC + DIFFC)
    
    return ghic
    

def global_irradiance_overcast(latitude_deg, longitude_deg, utc_datetime, 
                               elevation = elevation_default, temperature_celsius = 25, 
                               pressure_millibars = 1013.25):
    """Calculated Global is used to compare to the Diffuse under overcast conditions.
    Under overcast skies, global and diffuse are expected to be equal due to the absence of the beam 
    component.
    
    Parameters
    ----------
    latitude_deg : float
        latitude in decimal degree. A geographical term denoting the north/south angular location of a 
        place on a sphere.            
    longitude_deg : float
        longitude in decimal degree. Longitude shows your location in an east-west direction,relative 
        to the Greenwich meridian.        
    utc_datetime : date_object
        utc_datetime. UTC DateTime is for Universal Time ( i.e. like a GMT+0 )
    elevation : float
        The elevation of a geographic location is its height above a fixed reference point, often the 
        mean sea level.         
    temperature_celsius : float
        Temperature is a physical property of a system that underlies the common notions of hot and 
        cold.    
    pressure_millibars : float
        pressure_millibars    
    
    Returns
    -------
    ghioc : float
        Global Irradiation under overcast sky
    
    References
    ----------
    .. [1] S. Younes, R.Claywell and el al, "Quality
            control of solar radiation data: present status
            and proposed new approaches", energy 30
            (2005), pp 1533 - 1549.

    """    
    ghioc = (572 * (solar.GetAltitude(latitude_deg, longitude_deg, utc_datetime, 
                                    elevation , temperature_celsius , pressure_millibars )))
    
    return ghioc
    

def diffuse_ratio(DIFF_data,ghi_data):
    """Function calculates the Diffuse ratio.
    
    Parameters
    ----------
    DIFF_data : array_like
        Diffuse horizontal irradiation data 
    ghi_data : array_like
        global horizontal irradiation data array    
    
    Returns
    -------
    K : float
        diffuse_ratio
    
    References
    ----------
    .. [1] S. Younes, R.Claywell and el al,"Quality control of solar radiation data: present status and proposed 
            new approaches", energy 30 (2005), pp 1533 - 1549.
           
    """    
    K = DIFF_data/ghi_data
    
    return K 
    

def clear_index(ghi_data, utc_datetime, latitude_deg, longitude_deg):
   
    """This calculates the clear index ratio.
    
    Parameters
    ----------
    ghi_data : array_like
        global horizontal irradiation data array    
    utc_datetime : date_object
        utc_datetime. UTC DateTime is for Universal Time ( i.e. like a GMT+0 )        
    latitude_deg : float
        latitude in decimal degree. A geographical term denoting the north/south angular location of a place 
        on a sphere.            
    longitude_deg : float
        longitude in decimal degree. Longitude shows your location in an east-west direction,relative to the 
        Greenwich meridian.        
        
    Returns
    -------
    KT : float
        Clear index ratio
    
    References
    ----------
    .. [1] S. Younes, R.Claywell and el al,"Quality control of solar radiation data: present status and proposed 
            new approaches", energy 30 (2005), pp 1533 - 1549.
            
    """    
    EXTR1 = extraterrestrial_irrad(utc_datetime, latitude_deg, longitude_deg)
    
    KT = (ghi_data/EXTR1)
    
    return KT
  
def date_with_decimal_hour(date_utc, hour_decimal):    
    """This converts dates with decimal hour to datetime_hour.
    An improved version :mod:`conversions_time`
    
    Parameters
    ----------
    datetime : datetime.datetime
        A datetime object is a single object containing all the information from a 
        date object and a time object.              
    hour_decimal : datetime.datetime
        An hour is a unit of time 60 minutes, or 3,600 seconds in length.
    
    Returns
    -------.
    datetime_hour : datetime.datetime
        datetime_hour
    
    """
    # Backwards compatibility: round down to nearest round minute
    offset_seconds = int(hour_decimal * 60) * 60
    datetime_utc = dt(date_utc.year, date_utc.month, date_utc.day)
    
    return datetime_utc + timedelta(seconds=offset_seconds)


########NEW FILE########
