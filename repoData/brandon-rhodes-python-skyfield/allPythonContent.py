__FILENAME__ = api
"""Top-level objects and functions offered by the Skyfield library.

Importing this ``skyfield.api`` module causes Skyfield to load up the
default JPL planetary ephemeris ``de421`` and create planet objects like
``earth`` and ``mars`` that are ready for your use.

"""
import de421
from datetime import datetime
from .starlib import Star
from .timelib import JulianDate, now, utc

def build_ephemeris():
    from .data.horizons import festoon_ephemeris
    from .jpllib import Ephemeris
    ephemeris = Ephemeris(de421)
    festoon_ephemeris(ephemeris)
    return ephemeris

ephemeris = build_ephemeris()
del build_ephemeris

sun = ephemeris.sun
mercury = ephemeris.mercury
venus = ephemeris.venus
earth = ephemeris.earth
moon = ephemeris.moon
mars = ephemeris.mars
jupiter = ephemeris.jupiter
saturn = ephemeris.saturn
uranus = ephemeris.uranus
neptune = ephemeris.neptune
pluto = ephemeris.pluto

eight_planets = [mercury, venus, earth, mars, jupiter, saturn, uranus, neptune]
nine_planets = eight_planets + [pluto]

########NEW FILE########
__FILENAME__ = benchmark
"""Run a series of timing tests on core Skyfield atoms."""

import gc
import sys
from numpy import array, mean, std, zeros
from skyfield import earthlib, nutationlib, planets, starlib

from skyfield.constants import T0
from skyfield.timelib import julian_date, JulianDate
from timeit import default_timer

TA = julian_date(1969, 7, 20, 20., 18.)
TB = julian_date(2012, 12, 21)

D0 = 63.8285
DA = 39.707
DB = 66.8779

earth = planets.earth
jupiter = planets.jupiter
star = starlib.Star(
    ra=1.59132070233, dec=8.5958876464,
    pm_ra=0.0, pm_dec=0.0,
    parallax=0.0, radial_velocity=0.0,
)


class BM(object):
    def __init__(self, times, bm_fn, t):
        self.name = bm_fn.__name__
        self.times = times
        self.bm_fn = bm_fn
        self.t = t

    def __call__(self):
        self.bm_fn(self.times, self.t)


def run_benchmark(times, fn, *args, **kwargs):
    data = zeros(times)
    for i in xrange(times):
        gc.disable()
        start = default_timer()
        fn(*args, **kwargs)
        end = default_timer()
        gc.enable()

        data[i] = end - start

    avg, stdev, least = mean(data), std(data), min(data)
    suite_name = "{}.{}".format(fn.__module__, fn.__name__)
    factor = 1e6
    print('{} times  {:10.2f} avg  {:10.2f} least  {}'.format(
        times, avg * factor, least * factor, suite_name))


def bm_earth_rotation_angle(times, t):
    run_benchmark(times, earthlib.earth_rotation_angle, t)


def bm_star_observe_from(times, t):
    run_benchmark(times, star.observe_from, earth(t))


def bm_planet_observe_from(times, t):
    run_benchmark(times, jupiter.observe_from, earth(t))


def bm_topo_planet_observe(times, t):
    ggr = earth.topos('75 W', '45 N', 0.0, temperature=10.0, pressure=1010.0)
    run_benchmark(times, ggr(t).observe, jupiter)


def bm_earth_tilt(times, t):
    run_benchmark(times, nutationlib.earth_tilt, t)


def bm_equation_of_the_equinoxes(times, t):
    run_benchmark(times, nutationlib.equation_of_the_equinoxes_complimentary_terms, t)


def bm_fundamental_arguments(times, t):
    run_benchmark(times, nutationlib.fundamental_arguments, t)


def bm_coordinate_to_astrometric(times, t):
    coordinate = star.observe_from(earth(t))
    run_benchmark(times, coordinate.radec)


def bm_coordinate_to_apparent(times, t):
    coordinate = star.observe_from(earth(t))
    run_benchmark(times, coordinate.apparent)


def bm_coordinate_horizontal(times, t):
    ggr = earth.topos('75 W', '45 N', 0.0, temperature=10.0, pressure=1010.0)
    run_benchmark(times, ggr(t).observe(jupiter).apparent().horizontal)


BENCHMARKS = (
    BM(times=100, bm_fn=bm_earth_rotation_angle, t=array([T0, TA, TB])),

    BM(times=100, bm_fn=bm_star_observe_from, t=JulianDate(tt=T0)),
    BM(times=100, bm_fn=bm_star_observe_from, t=JulianDate(tt=TA)),
    BM(times=100, bm_fn=bm_star_observe_from, t=JulianDate(tt=TB)),

    BM(times=100, bm_fn=bm_planet_observe_from, t=JulianDate(tt=T0)),
    BM(times=100, bm_fn=bm_planet_observe_from, t=JulianDate(tt=TA)),
    BM(times=100, bm_fn=bm_planet_observe_from, t=JulianDate(tt=TB)),

    BM(times=100, bm_fn=bm_topo_planet_observe, t=JulianDate(tt=T0)),
    BM(times=100, bm_fn=bm_topo_planet_observe, t=JulianDate(tt=TA)),
    BM(times=100, bm_fn=bm_topo_planet_observe, t=JulianDate(tt=TB)),

    BM(times=100, bm_fn=bm_earth_tilt, t=JulianDate(tt=T0)),
    BM(times=100, bm_fn=bm_earth_tilt, t=JulianDate(tt=TA)),
    BM(times=100, bm_fn=bm_earth_tilt, t=JulianDate(tt=TB)),

    BM(times=100, bm_fn=bm_equation_of_the_equinoxes, t=array([T0, TA, TB])),

    BM(times=100, bm_fn=bm_fundamental_arguments, t=array([T0, TA, TB])),

    BM(times=100, bm_fn=bm_coordinate_to_astrometric, t=JulianDate(tt=T0)),
    BM(times=100, bm_fn=bm_coordinate_to_astrometric, t=JulianDate(tt=TA)),
    BM(times=100, bm_fn=bm_coordinate_to_astrometric, t=JulianDate(tt=TB)),

    BM(times=100, bm_fn=bm_coordinate_to_apparent, t=JulianDate(tt=T0)),
    BM(times=100, bm_fn=bm_coordinate_to_apparent, t=JulianDate(tt=TA)),
    BM(times=100, bm_fn=bm_coordinate_to_apparent, t=JulianDate(tt=TB)),

    BM(times=100, bm_fn=bm_coordinate_horizontal, t=JulianDate(tt=TB)),
)

if __name__ == "__main__":
    patterns = sys.argv[1:]
    for bm in BENCHMARKS:
        if any(pattern not in bm.name for pattern in patterns):
            continue
        bm()

########NEW FILE########
__FILENAME__ = constants
"""Various constants required by Skyfield."""

# Angles.
ASEC360 = 1296000.0
ASEC2RAD = 4.848136811095359935899141e-6
DEG2RAD = 0.017453292519943296
RAD2DEG = 57.295779513082321
TAU = 6.283185307179586476925287
tau = TAU  # lower case, for symmetry with math.pi

# Physics.
C_AUDAY = 173.1446326846693
C = 299792458.0

# Earth and its orbit.
ANGVEL = 7.2921150e-5
AU = 1.4959787069098932e+11
AU_KM = 1.4959787069098932e+8
ERAD = 6378136.6
IERS_2010_INVERSE_EARTH_FLATTENING = 298.25642

PSI_COR = 0.0
EPS_COR = 0.0

# Heliocentric gravitational constant in meters^3 / second^2, from DE-405.
GS = 1.32712440017987e+20

# Time.
T0 = 2451545.0
B1950 = 2433282.4235
DAY_S = 86400.0

########NEW FILE########
__FILENAME__ = horizons
"""Physical data for the planets from the JPL HORIZONS system.

To rebuild this data, consult the following IPython Notebook:

https://github.com/brandon-rhodes/astronomy-notebooks/blob/master/Utils-HORIZONS-data.ipynb

"""
from skyfield.units import Distance

radii_km = [
    ('Sun', 695500.0),
    ('Mercury', 2440.0),
    ('Venus', 6051.8),
    ('Earth', 6371.01),
    ('Mars', 3389.9),
    ('Jupiter', 69911.0),
    ('Saturn', 58232.0),
    ('Uranus', 25362.0),
    ('Neptune', 24624.0),
    ('134340 Pluto', 1195.0),
    ]

def festoon_ephemeris(ephemeris):
    for name, radius_km in radii_km:
        name = name.lower().split()[-1]
        getattr(ephemeris, name).radius = Distance(km=radius_km)

########NEW FILE########
__FILENAME__ = __main__
import skyfield.data
skyfield.data.rebuild()

########NEW FILE########
__FILENAME__ = conf
# -*- coding: utf-8 -*-
#
# Skyfield documentation build configuration file, created by
# sphinx-quickstart on Sun Feb 17 11:09:09 2013.
#
# This file is execfile()d with the current directory set to its containing dir.
#
# Note that not all possible configuration values are present in this
# autogenerated file.
#
# All configuration values have a default; values that are commented out
# serve to show the default.

import sys, os

# If extensions (or modules to document with autodoc) are in another directory,
# add these directories to sys.path here. If the directory is relative to the
# documentation root, use os.path.abspath to make it absolute, like shown here.
#sys.path.insert(0, os.path.abspath('.'))

# -- General configuration -----------------------------------------------------

# If your documentation needs a minimal Sphinx version, state it here.
#needs_sphinx = '1.0'

# Add any Sphinx extension module names here, as strings. They can be extensions
# coming with Sphinx (named 'sphinx.ext.*') or your custom ones.
extensions = ['sphinx.ext.autodoc', 'sphinx.ext.doctest', 'sphinx.ext.coverage', 'sphinx.ext.mathjax', 'sphinx.ext.viewcode']

# Add any paths that contain templates here, relative to this directory.
templates_path = ['_templates']

# The suffix of source filenames.
source_suffix = '.rst'

# The encoding of source files.
#source_encoding = 'utf-8-sig'

# The master toctree document.
master_doc = 'index'

# General information about the project.
project = u'Skyfield'
copyright = u'2013, Brandon Rhodes'

# The version info for the project you're documenting, acts as replacement for
# |version| and |release|, also used in various other places throughout the
# built documents.
#
# The short X.Y version.
import skyfield
version = skyfield.__version__
# The full version, including alpha/beta/rc tags.
release = skyfield.__version__

# The language for content autogenerated by Sphinx. Refer to documentation
# for a list of supported languages.
#language = None

# There are two options for replacing |today|: either, you set today to some
# non-false value, then it is used:
#today = ''
# Else, today_fmt is used as the format for a strftime call.
#today_fmt = '%B %d, %Y'

# List of patterns, relative to source directory, that match files and
# directories to ignore when looking for source files.
exclude_patterns = ['_build']

# The reST default role (used for this markup: `text`) to use for all documents.
#default_role = None

# If true, '()' will be appended to :func: etc. cross-reference text.
#add_function_parentheses = True

# If true, the current module name will be prepended to all description
# unit titles (such as .. function::).
#add_module_names = True

# If true, sectionauthor and moduleauthor directives will be shown in the
# output. They are ignored by default.
#show_authors = False

# The name of the Pygments (syntax highlighting) style to use.
pygments_style = 'sphinx'

# A list of ignored prefixes for module index sorting.
#modindex_common_prefix = []


# -- Options for HTML output ---------------------------------------------------

# The theme to use for HTML and HTML Help pages.  See the documentation for
# a list of builtin themes.
html_theme = 'default'

# Theme options are theme-specific and customize the look and feel of a theme
# further.  For a list of options available for each theme, see the
# documentation.
#html_theme_options = {}

# Add any paths that contain custom themes here, relative to this directory.
#html_theme_path = []

# The name for this set of Sphinx documents.  If None, it defaults to
# "<project> v<release> documentation".
#html_title = None

# A shorter title for the navigation bar.  Default is the same as html_title.
#html_short_title = None

# The name of an image file (relative to this directory) to place at the top
# of the sidebar.
#html_logo = None

# The name of an image file (within the static path) to use as favicon of the
# docs.  This file should be a Windows icon file (.ico) being 16x16 or 32x32
# pixels large.
#html_favicon = None

# Add any paths that contain custom static files (such as style sheets) here,
# relative to this directory. They are copied after the builtin static files,
# so a file named "default.css" will overwrite the builtin "default.css".
html_static_path = ['_static']

# If not '', a 'Last updated on:' timestamp is inserted at every page bottom,
# using the given strftime format.
#html_last_updated_fmt = '%b %d, %Y'

# If true, SmartyPants will be used to convert quotes and dashes to
# typographically correct entities.
#html_use_smartypants = True

# Custom sidebar templates, maps document names to template names.
#html_sidebars = {}

# Additional templates that should be rendered to pages, maps page names to
# template names.
#html_additional_pages = {}

# If false, no module index is generated.
#html_domain_indices = True

# If false, no index is generated.
#html_use_index = True

# If true, the index is split into individual pages for each letter.
#html_split_index = False

# If true, links to the reST sources are added to the pages.
#html_show_sourcelink = True

# If true, "Created using Sphinx" is shown in the HTML footer. Default is True.
#html_show_sphinx = True

# If true, "(C) Copyright ..." is shown in the HTML footer. Default is True.
#html_show_copyright = True

# If true, an OpenSearch description file will be output, and all pages will
# contain a <link> tag referring to it.  The value of this option must be the
# base URL from which the finished HTML is served.
#html_use_opensearch = ''

# This is the file name suffix for HTML files (e.g. ".xhtml").
#html_file_suffix = None

# Output file base name for HTML help builder.
htmlhelp_basename = 'Skyfielddoc'


# -- Options for LaTeX output --------------------------------------------------

latex_elements = {
# The paper size ('letterpaper' or 'a4paper').
#'papersize': 'letterpaper',

# The font size ('10pt', '11pt' or '12pt').
#'pointsize': '10pt',

# Additional stuff for the LaTeX preamble.
#'preamble': '',
}

# Grouping the document tree into LaTeX files. List of tuples
# (source start file, target name, title, author, documentclass [howto/manual]).
latex_documents = [
  ('index', 'Skyfield.tex', u'Skyfield Documentation',
   u'Brandon Rhodes', 'manual'),
]

# The name of an image file (relative to this directory) to place at the top of
# the title page.
#latex_logo = None

# For "manual" documents, if this is true, then toplevel headings are parts,
# not chapters.
#latex_use_parts = False

# If true, show page references after internal links.
#latex_show_pagerefs = False

# If true, show URL addresses after external links.
#latex_show_urls = False

# Documents to append as an appendix to all manuals.
#latex_appendices = []

# If false, no module index is generated.
#latex_domain_indices = True


# -- Options for manual page output --------------------------------------------

# One entry per manual page. List of tuples
# (source start file, name, description, authors, manual section).
man_pages = [
    ('index', 'skyfield', u'Skyfield Documentation',
     [u'Brandon Rhodes'], 1)
]

# If true, show URL addresses after external links.
#man_show_urls = False


# -- Options for Texinfo output ------------------------------------------------

# Grouping the document tree into Texinfo files. List of tuples
# (source start file, target name, title, author,
#  dir menu entry, description, category)
texinfo_documents = [
  ('index', 'Skyfield', u'Skyfield Documentation',
   u'Brandon Rhodes', 'Skyfield', 'One line description of project.',
   'Miscellaneous'),
]

# Documents to append as an appendix to all manuals.
#texinfo_appendices = []

# If false, no module index is generated.
#texinfo_domain_indices = True

# How to display URL addresses: 'footnote', 'no', or 'inline'.
#texinfo_show_urls = 'footnote'

########NEW FILE########
__FILENAME__ = logo
# -*- coding: utf-8 -*-

"""Build the Skyfield logo."""

# To build the logo and make a PNG:
#
# wget http://tdc-www.harvard.edu/catalogs/bsc5.dat.gz
# gunzip bsc5.dat.gz
#
# wget http://www.impallari.com/media/releases/dosis-v1.7.zip
# [extract Dosis-Medium.ttf]
#
# python logo.py
#
# convert -density 480 logo.pdf logo.png

from math import cos, pi, sin
from reportlab.pdfgen.canvas import Canvas
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

tau = pi * 2.0
quarter_tau = pi / 2.0

alpha_star_color = '#BC243C'
bright_star_color = '#002664'
dim_star_color = '#aaaaaa'
text_color = '#002664'
greek_color = 'black'

greeks = {
    'Alp': (u'α', 1.0),
    'Bet': (u'β', 1.0),
    'Gam': (u'γ', 1.3),
    'Del': (u'δ', 0.9),
    'Eps': (u'ε', 1.0),
    'Zet': (u'ζ', 1.0),
    'Eta': (u'η', 1.0),
    }

def main():
    pdfmetrics.registerFont(TTFont('Dosis', 'Dosis-Medium.ttf'))

    stars = []
    with open('bsc5.dat', 'rb') as f:
        for line in f:
            line = '.' + line  # switch to 1-based indexing
            if not line[62].strip():
                continue  # skip coordinate-less novas
            letter = intern(line[8:11])
            if letter == '   ':
                letter = None
            h, m, s = float(line[61:63]), float(line[63:65]), float(line[65:69])
            ra = (h + (m + s / 60.0) / 60.0) * tau / 24.0
            d, m, s = float(line[69:72]), float(line[72:74]), float(line[76:78])
            dec = (d + (m + s / 60.0) / 60.0) * tau / 360.0
            mag = float(line[103:108])
            stars.append((letter, ra, dec, mag))

    h, w = 48, 96
    c = Canvas('logo.pdf', pagesize=(w, h))

    c.setFillColor('white')
    c.rect(0, 0, w, h, stroke=0, fill=1)

    c.setFillColor(bright_star_color)

    rotation = 10.0 * tau / 360.0
    # magscale = 0.1
    # For 10 degrees:
    x_offset = 96 -33.5
    y_offset = h  +37.5
    # For 15 degrees:
    # x_offset = 96 -28.5
    # y_offset = 96 +0.5
    # for 45 degrees:
    # x_offset = 96 -13.5
    # y_offset = 96 -10

    small_glyphs = []
    c.setFont('Helvetica', 2)

    for letter, ra, dec, mag in stars:
        # if mag > 4.0:
        #     continue
        d = - (dec - quarter_tau) * 100
        ra += rotation
        x = d * sin(ra)
        y = d * cos(ra)

        if y < -63.0 or y > -39.0:
            continue
        if x < -43.0 or x > 19.0:
            continue

        x += x_offset
        y += y_offset

        r = ((13.0 - mag) / 10.0) ** 4.0 #* magscale
        r = min(r, 1.0)

        if r < 0.5:
            small_glyphs.append((x, y, r))
        else:
            if letter is not None:
                c.saveState()
                greek_letter, offset = greeks[letter]
                c.setFillColor(greek_color)
                c.drawString(x+offset, y+0.5, greek_letter)
                if letter == 'Alp':
                    c.setFillColor(alpha_star_color)
                    c.circle(x, y, r, stroke=0, fill=1)
                c.restoreState()
                if letter != 'Alp':
                    c.circle(x, y, r, stroke=0, fill=1)
            else:
                c.circle(x, y, r, stroke=0, fill=1)


    c.setFillColor(dim_star_color)
    for x, y, r in small_glyphs:
        c.circle(x, y, r, stroke=0, fill=1)

    c.setFillColor(text_color) #, alpha=0.5)
    c.setFont('Dosis', 24)
    sw = c.stringWidth('Skyfield')
    c.drawString(w // 2 - sw // 2, h - 40, 'Skyfield')

    c.showPage()
    with open('logo.pdf', 'wb') as f:
        f.write(c.getpdfdata())

if __name__ == '__main__':
    main()

########NEW FILE########
__FILENAME__ = earthlib
"""Formulae for specific earth behaviors and effects."""

from numpy import (arcsin, arccos, array, clip, cos, einsum, fmod,
                   minimum, pi, sin, sqrt, zeros_like)

from .constants import (AU, ANGVEL, DAY_S, DEG2RAD, ERAD,
                        IERS_2010_INVERSE_EARTH_FLATTENING, RAD2DEG, T0)
from .functions import dots
from .nutationlib import earth_tilt

rade = ERAD / AU
one_minus_flattening = 1.0 - 1.0 / IERS_2010_INVERSE_EARTH_FLATTENING
one_minus_flattening_squared = one_minus_flattening * one_minus_flattening


def geocentric_position_and_velocity(topos, jd):
    """Compute the GCRS position and velocity of a terrestrial observer.

    `topos` - `Topos` object describing a location.
    `jd` - a JulianDate.

    The return value is a 2-element tuple `(pos, vel)` of 3-vectors
    which each measure position in AU long the axes of the ICRS.

    """
    gmst = sidereal_time(jd)
    x1, x2, eqeq, x3, x4 = earth_tilt(jd)
    gast = gmst + eqeq / 3600.0

    pos, vel = terra(topos, gast)

    pos = einsum('ij...,j...->i...', jd.MT, pos)
    vel = einsum('ij...,j...->i...', jd.MT, vel)

    return pos, vel


def terra(topos, st):
    """Compute the position and velocity of a terrestrial observer.

    `topos` - `Topos` object describing a geographic position.
    `st` - Array of sidereal times in floating-point hours.

    The return value is a tuple of two 3-vectors `(pos, vel)` in the
    dynamical reference system whose components are measured in AU with
    respect to the center of the Earth.

    """
    zero = zeros_like(st)
    phi = topos.latitude
    sinphi = sin(phi)
    cosphi = cos(phi)
    c = 1.0 / sqrt(cosphi * cosphi +
                   sinphi * sinphi * one_minus_flattening_squared)
    s = one_minus_flattening_squared * c
    ht = topos.elevation
    ach = ERAD * c + ht
    ash = ERAD * s + ht

    # Compute local sidereal time factors at the observer's longitude.

    stlocl = st * 15.0 * DEG2RAD + topos.longitude
    sinst = sin(stlocl)
    cosst = cos(stlocl)

    # Compute position vector components in kilometers.

    ac = ach * cosphi
    pos = array((ac * cosst, ac * sinst, zero + ash * sinphi)) / AU

    # Compute velocity vector components in kilometers/sec.

    aac = ANGVEL * ach * cosphi
    vel = array((-aac * sinst, aac * cosst, zero)) / AU * DAY_S

    return pos, vel


def compute_limb_angle(position, observer):
    """Determine the angle of an object above or below the Earth's limb.

    Given an object's GCRS `position` [x,y,z] in AU and the position of
    an `observer` in the same coordinate system, return a tuple that is
    composed of `(limb_ang, nadir_ang)`:

    limb_angle
        Angle of observed object above (+) or below (-) limb in degrees.
    nadir_angle
        Nadir angle of observed object as a fraction of apparent radius
        of limb: <1.0 means below the limb, =1.0 means on the limb, and
        >1.0 means above the limb.

    """
    # Compute the distance to the object and the distance to the observer.

    disobj = sqrt(dots(position, position))
    disobs = sqrt(dots(observer, observer))

    # Compute apparent angular radius of Earth's limb.

    aprad = arcsin(minimum(rade / disobs, 1.0))

    # Compute zenith distance of Earth's limb.

    zdlim = pi - aprad

    # Compute zenith distance of observed object.

    coszd = dots(position, observer) / (disobj * disobs)
    coszd = clip(coszd, -1.0, 1.0)
    zdobj = arccos(coszd)

    # Angle of object wrt limb is difference in zenith distances.

    limb_angle = (zdlim - zdobj) * RAD2DEG

    # Nadir angle of object as a fraction of angular radius of limb.

    nadir_angle = (pi - zdobj) / aprad

    return limb_angle, nadir_angle


def sidereal_time(jd, use_eqeq=False):
    """Compute Greenwich sidereal time at Julian date `jd_ut1`."""

    t = (jd.tdb - T0) / 36525.0

    # Equation of equinoxes.

    if use_eqeq:
        ee = earth_tilt(jd)[2]
        eqeq = ee * 15.0
    else:
        eqeq = 0.0

    # Compute the Earth Rotation Angle.  Time argument is UT1.

    theta = earth_rotation_angle(jd.ut1)

    # The equinox method.  See Circular 179, Section 2.6.2.
    # Precession-in-RA terms in mean sidereal time taken from third
    # reference, eq. (42), with coefficients in arcseconds.

    st = eqeq + ( 0.014506 +
        (((( -    0.0000000368   * t
             -    0.000029956  ) * t
             -    0.00000044   ) * t
             +    1.3915817    ) * t
             + 4612.156534     ) * t)

    # Form the Greenwich sidereal time.

    gst = fmod((st / 3600.0 + theta), 360.0) / 15.0

    gst += 24.0 * (gst < 0.0)

    return gst


def earth_rotation_angle(jd_ut1):
    """Return the value of the Earth Rotation Angle (theta) for a UT1 date.

    Uses the expression from the note to IAU Resolution B1.8 of 2000.

    """
    thet1 = 0.7790572732640 + 0.00273781191135448 * (jd_ut1 - T0)
    thet3 = jd_ut1 % 1.0
    return (thet1 + thet3) % 1.0 * 360.0

########NEW FILE########
__FILENAME__ = framelib
"""Raw transforms between coordinate frames, as NumPy matrices."""

from numpy import array
from .constants import ASEC2RAD

def build_matrix():
    # 'xi0', 'eta0', and 'da0' are ICRS frame biases in arcseconds taken
    # from IERS (2003) Conventions, Chapter 5.

    xi0  = -0.0166170 * ASEC2RAD
    eta0 = -0.0068192 * ASEC2RAD
    da0  = -0.01460   * ASEC2RAD

    # Compute elements of rotation matrix.

    yx = -da0
    zx =  xi0
    xy =  da0
    zy =  eta0
    xz = -xi0
    yz = -eta0

    # Include second-order corrections to diagonal elements.

    xx = 1.0 - 0.5 * (yx * yx + zx * zx)
    yy = 1.0 - 0.5 * (yx * yx + zy * zy)
    zz = 1.0 - 0.5 * (zy * zy + zx * zx)

    return array(((xx, xy, xz), (yx, yy, yz), (zx, zy, zz)))

ICRS_to_J2000 = build_matrix()
del build_matrix

########NEW FILE########
__FILENAME__ = functions
from numpy import array, cos, ones_like, sin, sqrt, zeros_like

def dots(v, u):
    """Given one or more vectors in `v` and `u`, return their dot products.

    This works whether `v` and `u` each have the shape ``(3,)``, or
    whether they are each whole arrays of corresponding x, y, and z
    coordinates and have shape ``(3, N)``.

    """
    return (v * u).sum(axis=0)

def length_of(xyz):
    """Given a 3-element array `[x y z]`, return its length.

    The three elements can be simple scalars, or the array can be two
    dimensions and offer three whole series of x, y, and z coordinates.

    """
    return sqrt((xyz * xyz).sum(axis=0))

def spin_x(theta):
    z = zeros_like(theta)
    u = ones_like(theta)
    c = cos(theta)
    s = sin(theta)
    return array(((c, -s, z), (s, c, z), (z, z, u)))

def rot_x(theta):
    c = cos(theta)
    s = sin(theta)
    return array([(1.0, 0.0, 0.0), (0.0, c, s), (0.0, -s, c)])

def rot_y(theta):
    c = cos(theta)
    s = sin(theta)
    return array([(c, 0.0, -s), (0.0, 1.0, 0.0), (s, 0.0, c)])

def rot_z(theta):
    c = cos(theta)
    s = sin(theta)
    return array([(c, -s, 0.0), (s, c, 0.0), (0.0, 0.0, 1.0)])

########NEW FILE########
__FILENAME__ = io
import requests
import os
from datetime import datetime, timedelta
from numpy import load

_missing = object()

class Cache(object):
    def __init__(self, cache_path, days_old=0):
        self.cache_path = cache_path
        self.days_old = days_old
        self.ram_cache = {}
        self.npy_dirname = None

    def open_url(self, url, days_old=None):
        filename = url[url.rindex('/') + 1:]
        path = os.path.join(self.cache_path, filename)
        if days_old is None:
            days_old = self.days_old
        download_file(url, path, days_old)
        return open(path)

    def run(self, function):
        """Return the result of running `function(this_cache)` one time only.

        If this cache has already been asked to run `function`, then the
        return value of its first run is returned without re-running it.

        """
        result = self.ram_cache.get(function, _missing)
        if result is not _missing:
            return result

        if self.npy_dirname:
            path = os.path.join(self.npy_dirname, function.__name__ + '.npy')
            if os.path.exists(path):
                # TODO: check whether data is recent enough
                result = load(path)
                self.ram_cache[function] = result
                return result

        result = function(self)
        self.ram_cache[function] = result
        return result


def download_file(url, filename, days_old=0):
    if os.path.exists(filename):
        if not is_days_old(filename, days_old):
            return

    response = requests.get(url, stream=True)
    f = open(filename, 'wb')
    for chunk in response.iter_content(1024):
        f.write(chunk)

    f.close()

def is_days_old(filename, days_old):
    min_old = datetime.now()-timedelta(days=days_old)
    modified = datetime.fromtimestamp(os.path.getmtime(filename))
    return modified < min_old

########NEW FILE########
__FILENAME__ = jpllib
import jplephem
from numpy import max, min

from .constants import AU_KM, C_AUDAY
from .functions import length_of
from .positionlib import Barycentric, Astrometric, Topos
from .timelib import takes_julian_date

class Planet(object):
    def __init__(self, ephemeris, jplephemeris, jplname):
        self.ephemeris = ephemeris
        self.jplephemeris = jplephemeris
        self.jplname = jplname

    def __repr__(self):
        return '<Planet %s>' % (self.jplname,)

    @takes_julian_date
    def __call__(self, jd):
        """Return the x,y,z position of this planet at the given time."""
        position, velocity = self._position_and_velocity(jd.tdb)
        i = Barycentric(position, velocity, jd)
        i.ephemeris = self.ephemeris
        return i

    def _position(self, jd_tdb):
        e = self.jplephemeris
        c = e.position
        if self.jplname == 'earth':
            p = c('earthmoon', jd_tdb) - c('moon', jd_tdb) * e.earth_share
        elif self.jplname == 'moon':
            p = c('earthmoon', jd_tdb) + c('moon', jd_tdb) * e.moon_share
        else:
            p = c(self.jplname, jd_tdb)
        p /= AU_KM
        if getattr(jd_tdb, 'shape', ()) == ():
            # Skyfield, unlike jplephem, is willing to accept and return
            # plain scalars instead of only trafficking in NumPy arrays.
            p = p[:,0]
        return p

    def _position_and_velocity(self, jd_tdb):
        e = self.jplephemeris
        c = e.compute
        if self.jplname == 'earth':
            pv = c('earthmoon', jd_tdb) - c('moon', jd_tdb) * e.earth_share
        elif self.jplname == 'moon':
            pv = c('earthmoon', jd_tdb) + c('moon', jd_tdb) * e.moon_share
        else:
            pv = c(self.jplname, jd_tdb)
        pv /= AU_KM
        if getattr(jd_tdb, 'shape', ()) == ():
            # Skyfield, unlike jplephem, is willing to accept and return
            # plain scalars instead of only trafficking in NumPy arrays.
            pv = pv[:,0]
        return pv[:3], pv[3:]

    def observe_from(self, observer):
        # TODO: should also accept another ICRS?

        jd_tdb = observer.jd.tdb
        lighttime0 = 0.0
        position, velocity = self._position_and_velocity(jd_tdb)
        vector = position - observer.position.AU
        euclidian_distance = distance = length_of(vector)

        for i in range(10):
            lighttime = distance / C_AUDAY
            delta = lighttime - lighttime0
            if -1e-12 < min(delta) and max(delta) < 1e-12:
                break
            lighttime0 = lighttime
            position, velocity = self._position_and_velocity(jd_tdb - lighttime)
            vector = position - observer.position.AU
            distance = length_of(vector)
        else:
            raise ValueError('observe_from() light-travel time'
                             ' failed to converge')

        g = Astrometric(vector, velocity - observer.velocity.AU_per_d,
                        observer.jd)
        g.observer = observer
        g.distance = euclidian_distance
        g.lighttime = lighttime
        return g

class Earth(Planet):

    def topos(self, *args, **kw):  # TODO: args and docs like of Topos object?
        t = Topos(*args, **kw)
        t.ephemeris = self.ephemeris
        return t

    def satellite(self, text):
        from .sgp4lib import EarthSatellite
        lines = text.splitlines()
        return EarthSatellite(lines, self)

class Ephemeris(object):

    def __init__(self, module):

        self.jplephemeris = jplephem.Ephemeris(module)

        self.sun = Planet(self, self.jplephemeris, 'sun')
        self.mercury = Planet(self, self.jplephemeris, 'mercury')
        self.venus = Planet(self, self.jplephemeris, 'venus')
        self.earth = Earth(self, self.jplephemeris, 'earth')
        self.moon = Planet(self, self.jplephemeris, 'moon')
        self.mars = Planet(self, self.jplephemeris, 'mars')
        self.jupiter = Planet(self, self.jplephemeris, 'jupiter')
        self.saturn = Planet(self, self.jplephemeris, 'saturn')
        self.uranus = Planet(self, self.jplephemeris, 'uranus')
        self.neptune = Planet(self, self.jplephemeris, 'neptune')
        self.pluto = Planet(self, self.jplephemeris, 'pluto')

    def _position(self, name, jd):
        return getattr(self, name)._position(jd)

    def _position_and_velocity(self, name, jd):
        return getattr(self, name)._position_and_velocity(jd)

########NEW FILE########
__FILENAME__ = keplerianlib
from math import sin, cos
import math
from . import constants
from .positionlib import ICRCoordinates

def semimajorAxisToOrbitalPeriod(axis):
    return (axis ** 3) ** 0.5

def orbitalPeriodToSemimajorAxis(period):
    return (period ** 2) ** (1.0 / 3.0)

def convergeEccentricAnomaly(mean_anomaly, eccentricity, precision):
    # calculate the delta
    delta = 10 ** -precision

    # normalize the mean anomaly
    m = mean_anomaly % constants.TAU

    # set up the first guess
    eccentric_anomaly = constants.TAU
    if eccentricity < 0.8:
        eccentric_anomaly = m

    # do the initial test
    test = eccentric_anomaly - eccentricity * sin(m) - m

    # while we're not happy with the result, and we haven't been dawdling too long
    max_iterations = 30
    count = 0
    while ((math.fabs(test) > delta) and (count < max_iterations)):
        # calculate the next guess for an eccentric anomaly
        eccentric_anomaly = (
            eccentric_anomaly - test /
            (1.0 - eccentricity * cos(eccentric_anomaly))
        )

        # try it
        test = eccentric_anomaly - eccentricity * sin(eccentric_anomaly) - m

        # count the runs, so we don't go forever
        count += 1

    # convert to degrees
    return eccentric_anomaly

def calculateMeanAnomaly(L, wb):
    return L - wb

class KeplerianOrbit:
    def __init__(
            self,
            semimajor_axis,
            eccentricity,
            inclination,
            longitude_ascending,
            argument_perihelion,
            mean_anomaly,
            epoch
        ):
        self.semimajor_axis = semimajor_axis
        self.eccentricity = eccentricity
        self.inclination = inclination
        self.longitude_ascending = longitude_ascending
        self.argument_perihelion = argument_perihelion
        self.mean_anomaly = mean_anomaly
        self.epoch = epoch

    def getECLCoordinatesOnJulianDate(self, date):
         # localize the orbital parameters
        a = self.semimajor_axis
        e = self.eccentricity
        I = self.inclination
        Om = self.longitude_ascending
        #n = 0.230605479
        n = 0.230652907

        w = self.argument_perihelion

        M = self.mean_anomaly
        d = date.tdb - self.epoch.tdb

        Om = Om / 360.0 * constants.TAU
        w = w / 360.0 * constants.TAU
        I = I / 360.0 * constants.TAU
        M = M / 360.0 * constants.TAU
        n = n / 360.0 * constants.TAU

        M += d * n

        # calculate the mean anomaly in rads
        E = convergeEccentricAnomaly(M, e, 30)

        # calculate the initial primes
        x_prime = a * (cos(E) - e)
        y_prime = a * (1 - e ** 2.0) ** (0.5) * sin(E)

        """
        http://ssd.jpl.nasa.gov/txt/aprx_pos_planets.pdf
        x_ecl = cos(w)cos(Om)-sin(w)sin(Om)cos(I) * x_prime +
            (-sin(w)cos(Om) - cos(w)sin(Om)cos(I)) * y_prime
        y_ecl = cos(w)sin(Om)-sin(w)cos(Om)cos(I) * x_prime +
            (-sin(w)cos(Om) - cos(w)sin(Om)cos(I)) * y_prime
        z_ecl = (sin(w)sin(I)) * x_prime +
            (cos(w)sin(I)) * y_prime
        """

        # calculate the ecliptic coordinates
        x_ecl = ((cos(w) * cos(Om) - sin(w) * sin(Om) * cos(I)) * x_prime +
                (-1 * sin(w) * cos(Om) - cos(w) * sin(Om) * cos(I)) * y_prime)
        y_ecl = ((cos(w) * sin(Om) + sin(w) * cos(Om) * cos(I)) * x_prime +
                (-1 * sin(w) * sin(Om) + cos(w) * cos(Om) * cos(I)) * y_prime)
        z_ecl = ((sin(w) * sin(I)) * x_prime + (cos(w) * sin(I)) * y_prime)

        return ICRCoordinates(x_ecl, y_ecl, z_ecl)

    def getICRSCoordinatesOnJulianDate(self, date):
        # J2000 obliquity
        e = 23.43928 * math.pi / 180.0

        # get the ecliptic coords
        ecliptic = self.getECLCoordinatesonJulianDate(date);

        # calculate the equatorial (ICRS) coordinates
        x_eq = ecliptic.x;
        y_eq = cos(e) * ecliptic.y - sin(e) * ecliptic.z
        z_eq = sin(e) * ecliptic.y + cos(e) * ecliptic.z


########NEW FILE########
__FILENAME__ = nutationlib
"""Routines that compute Earth nutation."""
from numpy import array, cos, fmod, sin, outer, tensordot, zeros
from .constants import ASEC2RAD, ASEC360, DEG2RAD, TAU, PSI_COR, EPS_COR, T0

def compute_nutation(jd):
    """Generate the nutation rotations for JulianDate `jd`.

    If the Julian date is scalar, a simple ``(3, 3)`` matrix is
    returned; if the date is an array of length ``n``, then an array of
    matrices is returned with dimensions ``(3, 3, n)``.

    """
    oblm, oblt, eqeq, psi, eps = earth_tilt(jd)

    cobm = cos(oblm * DEG2RAD)
    sobm = sin(oblm * DEG2RAD)
    cobt = cos(oblt * DEG2RAD)
    sobt = sin(oblt * DEG2RAD)
    cpsi = cos(psi * ASEC2RAD)
    spsi = sin(psi * ASEC2RAD)

    return array(((cpsi,
                  -spsi * cobm,
                  -spsi * sobm),
                  (spsi * cobt,
                   cpsi * cobm * cobt + sobm * sobt,
                   cpsi * sobm * cobt - cobm * sobt),
                  (spsi * sobt,
                   cpsi * cobm * sobt - sobm * cobt,
                   cpsi * sobm * sobt + cobm * cobt)))

def earth_tilt(jd):
    """Return a tuple of information about the earth's axis and position.

    `jd` - A JulianDate object.

    The returned tuple contains five items:

    ``mean_ob`` - Mean obliquity of the ecliptic in degrees.
    ``true_ob`` - True obliquity of the ecliptic in degrees.
    ``eq_eq`` - Equation of the equinoxes in seconds of time.
    ``d_psi`` - Nutation in longitude in arcseconds.
    ``d_eps`` - Nutation in obliquity in arcseconds.

    """
    dp, de = iau2000a(jd.tt)
    c_terms = equation_of_the_equinoxes_complimentary_terms(jd.tt) / ASEC2RAD

    d_psi = dp * 1e-7 + PSI_COR
    d_eps = de * 1e-7 + EPS_COR

    mean_ob = mean_obliquity(jd.tdb)
    true_ob = mean_ob + d_eps

    mean_ob /= 3600.0
    true_ob /= 3600.0

    eq_eq = d_psi * cos(mean_ob * DEG2RAD) + c_terms
    eq_eq /= 15.0

    return mean_ob, true_ob, eq_eq, d_psi, d_eps

#

def mean_obliquity(jd_tdb):
    """Return the mean obliquity of the ecliptic in arcseconds.

    `jd_tt` - TDB time as a Julian date float, or NumPy array of floats

    """
    # Compute time in Julian centuries from epoch J2000.0.

    t = (jd_tdb - T0) / 36525.0

    # Compute the mean obliquity in arcseconds.  Use expression from the
    # reference's eq. (39) with obliquity at J2000.0 taken from eq. (37)
    # or Table 8.

    epsilon = (((( -  0.0000000434   * t
                   -  0.000000576  ) * t
                   +  0.00200340   ) * t
                   -  0.0001831    ) * t
                   - 46.836769     ) * t + 84381.406

    return epsilon

def equation_of_the_equinoxes_complimentary_terms(jd_tt):
    """Compute the complementary terms of the equation of the equinoxes.

    `jd_tt` - Terrestrial Time: Julian date float, or NumPy array of floats

    """
    # Interval between fundamental epoch J2000.0 and current date.

    t = (jd_tt - T0) / 36525.0

    # Build array for intermediate results.

    shape = getattr(jd_tt, 'shape', ())
    fa = zeros((14,) if shape == () else (14, shape[0]))

    # Mean Anomaly of the Moon.

    fa[0] = ((485868.249036 +
              (715923.2178 +
              (    31.8792 +
              (     0.051635 +
              (    -0.00024470)
              * t) * t) * t) * t) * ASEC2RAD
              + (1325.0*t % 1.0) * TAU)

    # Mean Anomaly of the Sun.

    fa[1] = ((1287104.793048 +
              (1292581.0481 +
              (     -0.5532 +
              (     +0.000136 +
              (     -0.00001149)
              * t) * t) * t) * t) * ASEC2RAD
              + (99.0*t % 1.0) * TAU)

    # Mean Longitude of the Moon minus Mean Longitude of the Ascending
    # Node of the Moon.

    fa[2] = (( 335779.526232 +
              ( 295262.8478 +
              (    -12.7512 +
              (     -0.001037 +
              (      0.00000417)
              * t) * t) * t) * t) * ASEC2RAD
              + (1342.0*t % 1.0) * TAU)

    # Mean Elongation of the Moon from the Sun.

    fa[3] = ((1072260.703692 +
              (1105601.2090 +
              (     -6.3706 +
              (      0.006593 +
              (     -0.00003169)
              * t) * t) * t) * t) * ASEC2RAD
              + (1236.0*t % 1.0) * TAU)

    # Mean Longitude of the Ascending Node of the Moon.

    fa[4] = (( 450160.398036 +
              (-482890.5431 +
              (      7.4722 +
              (      0.007702 +
              (     -0.00005939)
              * t) * t) * t) * t) * ASEC2RAD
              + (-5.0*t % 1.0) * TAU)

    fa[ 5] = (4.402608842 + 2608.7903141574 * t)
    fa[ 6] = (3.176146697 + 1021.3285546211 * t)
    fa[ 7] = (1.753470314 +  628.3075849991 * t)
    fa[ 8] = (6.203480913 +  334.0612426700 * t)
    fa[ 9] = (0.599546497 +   52.9690962641 * t)
    fa[10] = (0.874016757 +   21.3299104960 * t)
    fa[11] = (5.481293872 +    7.4781598567 * t)
    fa[12] = (5.311886287 +    3.8133035638 * t)
    fa[13] = (0.024381750 +    0.00000538691 * t) * t

    fa %= TAU

    # Evaluate the complementary terms.

    a = ke0_t.dot(fa)
    s0 = se0_t_0.dot(sin(a)) + se0_t_1.dot(cos(a))

    a = ke1.dot(fa)
    s1 = se1_0 * sin(a) + se1_1 * cos(a)

    c_terms = s0 + s1 * t
    c_terms *= ASEC2RAD
    return c_terms

anomaly_constant, anomaly_coefficient = array([

    # Mean anomaly of the Moon.
    (2.35555598, 8328.6914269554),

    # Mean anomaly of the Sun.
    (6.24006013, 628.301955),

    # Mean argument of the latitude of the Moon.
    (1.627905234, 8433.466158131),

    # Mean elongation of the Moon from the Sun.
    (5.198466741, 7771.3771468121),

    # Mean longitude of the ascending node of the Moon.
    (2.18243920, - 33.757045),

    # Planetary longitudes, Mercury through Neptune (Souchay et al. 1999).
    (4.402608842, 2608.7903141574),
    (3.176146697, 1021.3285546211),
    (1.753470314,  628.3075849991),
    (6.203480913,  334.0612426700),
    (0.599546497,   52.9690962641),
    (0.874016757,   21.3299104960),
    (5.481293871,    7.4781598567),
    (5.321159000,    3.8127774000),

    # General accumulated precession in longitude (gets multiplied by t).
    (0.02438175, 0.00000538691),
    ]).T

def iau2000a(jd_tt):
    """Compute Earth nutation based on the IAU 2000A nutation model.

    `jd_tt` - Terrestrial Time: Julian date float, or NumPy array of floats

    Returns a tuple ``(delta_psi, delta_epsilon)`` measured in tenths of
    a micro-arcsecond.  Each value is either a float, or a NumPy array
    with the same dimensions as the input argument.

    """
    # Interval between fundamental epoch J2000.0 and given date.

    t = (jd_tt - T0) / 36525.0

    # Compute fundamental arguments from Simon et al. (1994), in radians.

    a = fundamental_arguments(t)

    # ** Luni-solar nutation **
    # Summation of luni-solar nutation series (in reverse order).

    arg = nals_t.dot(a)
    fmod(arg, TAU, out=arg)

    sarg = sin(arg)
    carg = cos(arg)

    stsc = array((sarg, t * sarg, carg)).T
    ctcs = array((carg, t * carg, sarg)).T

    dpsi = tensordot(stsc, lunisolar_longitude_coefficients)
    deps = tensordot(ctcs, lunisolar_obliquity_coefficients)

    # Compute and add in planetary components.

    if getattr(t, 'shape', ()) == ():
        a = t * anomaly_coefficient + anomaly_constant
    else:
        a = (outer(anomaly_coefficient, t).T + anomaly_constant).T
    a[-1] *= t

    fmod(a, TAU, out=a)
    arg = napl_t.dot(a)
    fmod(arg, TAU, out=arg)
    sc = array((sin(arg), cos(arg))).T

    dpsi += tensordot(sc, nutation_coefficients_longitude)
    deps += tensordot(sc, nutation_coefficients_obliquity)

    return dpsi, deps

#

fa0, fa1, fa2, fa3, fa4 = array([

    # Mean Anomaly of the Moon.
    (485868.249036, 1717915923.2178, 31.8792, 0.051635, - .00024470),

    # Mean Anomaly of the Sun.
    (1287104.79305,  129596581.0481, - 0.5532, 0.000136, - 0.00001149),

    # Mean Longitude of the Moon minus Mean Longitude of the Ascending
    # Node of the Moon.
    (335779.526232, 1739527262.8478, - 12.7512, -  0.001037, 0.00000417),

    # Mean Elongation of the Moon from the Sun.
    (1072260.70369, 1602961601.2090, - 6.3706, 0.006593, - 0.00003169),

    # Mean Longitude of the Ascending Node of the Moon.
    (450160.398036, - 6962890.5431, 7.4722, 0.007702, - 0.00005939),

    ]).T[:,:,None]

def fundamental_arguments(t):
    """Compute the fundamental arguments (mean elements) of Sun and Moon.

    `t` - TDB time in Julian centuries since J2000.0, as float or NumPy array

    Outputs fundamental arguments, in radians:
          a[0] = l (mean anomaly of the Moon)
          a[1] = l' (mean anomaly of the Sun)
          a[2] = F (mean argument of the latitude of the Moon)
          a[3] = D (mean elongation of the Moon from the Sun)
          a[4] = Omega (mean longitude of the Moon's ascending node);
                 from Simon section 3.4(b.3),
                 precession = 5028.8200 arcsec/cy)

    """
    a = fa4 * t
    a += fa3
    a *= t
    a += fa2
    a *= t
    a += fa1
    a *= t
    a += fa0
    fmod(a, ASEC360, out=a)
    a *= ASEC2RAD
    if getattr(t, 'shape', ()):
        return a
    return a[:,0]

# Argument coefficients for t^0.

ke0_t = array([
      (0,  0,  0,  0,  1,  0,  0,  0,  0,  0,  0,  0,  0,  0),
      (0,  0,  0,  0,  2,  0,  0,  0,  0,  0,  0,  0,  0,  0),
      (0,  0,  2, -2,  3,  0,  0,  0,  0,  0,  0,  0,  0,  0),
      (0,  0,  2, -2,  1,  0,  0,  0,  0,  0,  0,  0,  0,  0),
      (0,  0,  2, -2,  2,  0,  0,  0,  0,  0,  0,  0,  0,  0),
      (0,  0,  2,  0,  3,  0,  0,  0,  0,  0,  0,  0,  0,  0),
      (0,  0,  2,  0,  1,  0,  0,  0,  0,  0,  0,  0,  0,  0),
      (0,  0,  0,  0,  3,  0,  0,  0,  0,  0,  0,  0,  0,  0),
      (0,  1,  0,  0,  1,  0,  0,  0,  0,  0,  0,  0,  0,  0),
      (0,  1,  0,  0, -1,  0,  0,  0,  0,  0,  0,  0,  0,  0),
      (1,  0,  0,  0, -1,  0,  0,  0,  0,  0,  0,  0,  0,  0),
      (1,  0,  0,  0,  1,  0,  0,  0,  0,  0,  0,  0,  0,  0),
      (0,  1,  2, -2,  3,  0,  0,  0,  0,  0,  0,  0,  0,  0),
      (0,  1,  2, -2,  1,  0,  0,  0,  0,  0,  0,  0,  0,  0),
      (0,  0,  4, -4,  4,  0,  0,  0,  0,  0,  0,  0,  0,  0),
      (0,  0,  1, -1,  1,  0, -8, 12,  0,  0,  0,  0,  0,  0),
      (0,  0,  2,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0),
      (0,  0,  2,  0,  2,  0,  0,  0,  0,  0,  0,  0,  0,  0),
      (1,  0,  2,  0,  3,  0,  0,  0,  0,  0,  0,  0,  0,  0),
      (1,  0,  2,  0,  1,  0,  0,  0,  0,  0,  0,  0,  0,  0),
      (0,  0,  2, -2,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0),
      (0,  1, -2,  2, -3,  0,  0,  0,  0,  0,  0,  0,  0,  0),
      (0,  1, -2,  2, -1,  0,  0,  0,  0,  0,  0,  0,  0,  0),
      (0,  0,  0,  0,  0,  0,  8,-13,  0,  0,  0,  0,  0, -1),
      (0,  0,  0,  2,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0),
      (2,  0, -2,  0, -1,  0,  0,  0,  0,  0,  0,  0,  0,  0),
      (1,  0,  0, -2,  1,  0,  0,  0,  0,  0,  0,  0,  0,  0),
      (0,  1,  2, -2,  2,  0,  0,  0,  0,  0,  0,  0,  0,  0),
      (1,  0,  0, -2, -1,  0,  0,  0,  0,  0,  0,  0,  0,  0),
      (0,  0,  4, -2,  4,  0,  0,  0,  0,  0,  0,  0,  0,  0),
      (0,  0,  2, -2,  4,  0,  0,  0,  0,  0,  0,  0,  0,  0),
      (1,  0, -2,  0, -3,  0,  0,  0,  0,  0,  0,  0,  0,  0),
      (1,  0, -2,  0, -1,  0,  0,  0,  0,  0,  0,  0,  0,  0),
      ])

# Argument coefficients for t^1.

ke1 = array([0,  0,  0,  0,  1,  0,  0,  0,  0,  0,  0,  0,  0,  0])

# Sine and cosine coefficients for t^0.

se0_t = array([
      (+2640.96e-6,          -0.39e-6),
      (  +63.52e-6,          -0.02e-6),
      (  +11.75e-6,          +0.01e-6),
      (  +11.21e-6,          +0.01e-6),
      (   -4.55e-6,          +0.00e-6),
      (   +2.02e-6,          +0.00e-6),
      (   +1.98e-6,          +0.00e-6),
      (   -1.72e-6,          +0.00e-6),
      (   -1.41e-6,          -0.01e-6),
      (   -1.26e-6,          -0.01e-6),
      (   -0.63e-6,          +0.00e-6),
      (   -0.63e-6,          +0.00e-6),
      (   +0.46e-6,          +0.00e-6),
      (   +0.45e-6,          +0.00e-6),
      (   +0.36e-6,          +0.00e-6),
      (   -0.24e-6,          -0.12e-6),
      (   +0.32e-6,          +0.00e-6),
      (   +0.28e-6,          +0.00e-6),
      (   +0.27e-6,          +0.00e-6),
      (   +0.26e-6,          +0.00e-6),
      (   -0.21e-6,          +0.00e-6),
      (   +0.19e-6,          +0.00e-6),
      (   +0.18e-6,          +0.00e-6),
      (   -0.10e-6,          +0.05e-6),
      (   +0.15e-6,          +0.00e-6),
      (   -0.14e-6,          +0.00e-6),
      (   +0.14e-6,          +0.00e-6),
      (   -0.14e-6,          +0.00e-6),
      (   +0.14e-6,          +0.00e-6),
      (   +0.13e-6,          +0.00e-6),
      (   -0.11e-6,          +0.00e-6),
      (   +0.11e-6,          +0.00e-6),
      (   +0.11e-6,          +0.00e-6),
      ])

se0_t_0, se0_t_1 = se0_t.T

# Sine and cosine coefficients for t^1.

se1 = (   -0.87e-6,          +0.00e-6)
se1_0 = se1[0]
se1_1 = se1[1]

# Luni-Solar argument multipliers:
#      L     L'    F     D     Om

nals_t = array((
      ( 0,    0,    0,    0,    1),
      ( 0,    0,    2,   -2,    2),
      ( 0,    0,    2,    0,    2),
      ( 0,    0,    0,    0,    2),
      ( 0,    1,    0,    0,    0),
      ( 0,    1,    2,   -2,    2),
      ( 1,    0,    0,    0,    0),
      ( 0,    0,    2,    0,    1),
      ( 1,    0,    2,    0,    2),
      ( 0,   -1,    2,   -2,    2),
      ( 0,    0,    2,   -2,    1),
      (-1,    0,    2,    0,    2),
      (-1,    0,    0,    2,    0),
      ( 1,    0,    0,    0,    1),
      (-1,    0,    0,    0,    1),
      (-1,    0,    2,    2,    2),
      ( 1,    0,    2,    0,    1),
      (-2,    0,    2,    0,    1),
      ( 0,    0,    0,    2,    0),
      ( 0,    0,    2,    2,    2),
      ( 0,   -2,    2,   -2,    2),
      (-2,    0,    0,    2,    0),
      ( 2,    0,    2,    0,    2),
      ( 1,    0,    2,   -2,    2),
      (-1,    0,    2,    0,    1),
      ( 2,    0,    0,    0,    0),
      ( 0,    0,    2,    0,    0),
      ( 0,    1,    0,    0,    1),
      (-1,    0,    0,    2,    1),
      ( 0,    2,    2,   -2,    2),
      ( 0,    0,   -2,    2,    0),
      ( 1,    0,    0,   -2,    1),
      ( 0,   -1,    0,    0,    1),
      (-1,    0,    2,    2,    1),
      ( 0,    2,    0,    0,    0),
      ( 1,    0,    2,    2,    2),
      (-2,    0,    2,    0,    0),
      ( 0,    1,    2,    0,    2),
      ( 0,    0,    2,    2,    1),
      ( 0,   -1,    2,    0,    2),
      ( 0,    0,    0,    2,    1),
      ( 1,    0,    2,   -2,    1),
      ( 2,    0,    2,   -2,    2),
      (-2,    0,    0,    2,    1),
      ( 2,    0,    2,    0,    1),
      ( 0,   -1,    2,   -2,    1),
      ( 0,    0,    0,   -2,    1),
      (-1,   -1,    0,    2,    0),
      ( 2,    0,    0,   -2,    1),
      ( 1,    0,    0,    2,    0),
      ( 0,    1,    2,   -2,    1),
      ( 1,   -1,    0,    0,    0),
      (-2,    0,    2,    0,    2),
      ( 3,    0,    2,    0,    2),
      ( 0,   -1,    0,    2,    0),
      ( 1,   -1,    2,    0,    2),
      ( 0,    0,    0,    1,    0),
      (-1,   -1,    2,    2,    2),
      (-1,    0,    2,    0,    0),
      ( 0,   -1,    2,    2,    2),
      (-2,    0,    0,    0,    1),
      ( 1,    1,    2,    0,    2),
      ( 2,    0,    0,    0,    1),
      (-1,    1,    0,    1,    0),
      ( 1,    1,    0,    0,    0),
      ( 1,    0,    2,    0,    0),
      (-1,    0,    2,   -2,    1),
      ( 1,    0,    0,    0,    2),
      (-1,    0,    0,    1,    0),
      ( 0,    0,    2,    1,    2),
      (-1,    0,    2,    4,    2),
      (-1,    1,    0,    1,    1),
      ( 0,   -2,    2,   -2,    1),
      ( 1,    0,    2,    2,    1),
      (-2,    0,    2,    2,    2),
      (-1,    0,    0,    0,    2),
      ( 1,    1,    2,   -2,    2),
      (-2,    0,    2,    4,    2),
      (-1,    0,    4,    0,    2),
      ( 2,    0,    2,   -2,    1),
      ( 2,    0,    2,    2,    2),
      ( 1,    0,    0,    2,    1),
      ( 3,    0,    0,    0,    0),
      ( 3,    0,    2,   -2,    2),
      ( 0,    0,    4,   -2,    2),
      ( 0,    1,    2,    0,    1),
      ( 0,    0,   -2,    2,    1),
      ( 0,    0,    2,   -2,    3),
      (-1,    0,    0,    4,    0),
      ( 2,    0,   -2,    0,    1),
      (-2,    0,    0,    4,    0),
      (-1,   -1,    0,    2,    1),
      (-1,    0,    0,    1,    1),
      ( 0,    1,    0,    0,    2),
      ( 0,    0,   -2,    0,    1),
      ( 0,   -1,    2,    0,    1),
      ( 0,    0,    2,   -1,    2),
      ( 0,    0,    2,    4,    2),
      (-2,   -1,    0,    2,    0),
      ( 1,    1,    0,   -2,    1),
      (-1,    1,    0,    2,    0),
      (-1,    1,    0,    1,    2),
      ( 1,   -1,    0,    0,    1),
      ( 1,   -1,    2,    2,    2),
      (-1,    1,    2,    2,    2),
      ( 3,    0,    2,    0,    1),
      ( 0,    1,   -2,    2,    0),
      (-1,    0,    0,   -2,    1),
      ( 0,    1,    2,    2,    2),
      (-1,   -1,    2,    2,    1),
      ( 0,   -1,    0,    0,    2),
      ( 1,    0,    2,   -4,    1),
      (-1,    0,   -2,    2,    0),
      ( 0,   -1,    2,    2,    1),
      ( 2,   -1,    2,    0,    2),
      ( 0,    0,    0,    2,    2),
      ( 1,   -1,    2,    0,    1),
      (-1,    1,    2,    0,    2),
      ( 0,    1,    0,    2,    0),
      ( 0,   -1,   -2,    2,    0),
      ( 0,    3,    2,   -2,    2),
      ( 0,    0,    0,    1,    1),
      (-1,    0,    2,    2,    0),
      ( 2,    1,    2,    0,    2),
      ( 1,    1,    0,    0,    1),
      ( 1,    1,    2,    0,    1),
      ( 2,    0,    0,    2,    0),
      ( 1,    0,   -2,    2,    0),
      (-1,    0,    0,    2,    2),
      ( 0,    1,    0,    1,    0),
      ( 0,    1,    0,   -2,    1),
      (-1,    0,    2,   -2,    2),
      ( 0,    0,    0,   -1,    1),
      (-1,    1,    0,    0,    1),
      ( 1,    0,    2,   -1,    2),
      ( 1,   -1,    0,    2,    0),
      ( 0,    0,    0,    4,    0),
      ( 1,    0,    2,    1,    2),
      ( 0,    0,    2,    1,    1),
      ( 1,    0,    0,   -2,    2),
      (-1,    0,    2,    4,    1),
      ( 1,    0,   -2,    0,    1),
      ( 1,    1,    2,   -2,    1),
      ( 0,    0,    2,    2,    0),
      (-1,    0,    2,   -1,    1),
      (-2,    0,    2,    2,    1),
      ( 4,    0,    2,    0,    2),
      ( 2,   -1,    0,    0,    0),
      ( 2,    1,    2,   -2,    2),
      ( 0,    1,    2,    1,    2),
      ( 1,    0,    4,   -2,    2),
      (-1,   -1,    0,    0,    1),
      ( 0,    1,    0,    2,    1),
      (-2,    0,    2,    4,    1),
      ( 2,    0,    2,    0,    0),
      ( 1,    0,    0,    1,    0),
      (-1,    0,    0,    4,    1),
      (-1,    0,    4,    0,    1),
      ( 2,    0,    2,    2,    1),
      ( 0,    0,    2,   -3,    2),
      (-1,   -2,    0,    2,    0),
      ( 2,    1,    0,    0,    0),
      ( 0,    0,    4,    0,    2),
      ( 0,    0,    0,    0,    3),
      ( 0,    3,    0,    0,    0),
      ( 0,    0,    2,   -4,    1),
      ( 0,   -1,    0,    2,    1),
      ( 0,    0,    0,    4,    1),
      (-1,   -1,    2,    4,    2),
      ( 1,    0,    2,    4,    2),
      (-2,    2,    0,    2,    0),
      (-2,   -1,    2,    0,    1),
      (-2,    0,    0,    2,    2),
      (-1,   -1,    2,    0,    2),
      ( 0,    0,    4,   -2,    1),
      ( 3,    0,    2,   -2,    1),
      (-2,   -1,    0,    2,    1),
      ( 1,    0,    0,   -1,    1),
      ( 0,   -2,    0,    2,    0),
      (-2,    0,    0,    4,    1),
      (-3,    0,    0,    0,    1),
      ( 1,    1,    2,    2,    2),
      ( 0,    0,    2,    4,    1),
      ( 3,    0,    2,    2,    2),
      (-1,    1,    2,   -2,    1),
      ( 2,    0,    0,   -4,    1),
      ( 0,    0,    0,   -2,    2),
      ( 2,    0,    2,   -4,    1),
      (-1,    1,    0,    2,    1),
      ( 0,    0,    2,   -1,    1),
      ( 0,   -2,    2,    2,    2),
      ( 2,    0,    0,    2,    1),
      ( 4,    0,    2,   -2,    2),
      ( 2,    0,    0,   -2,    2),
      ( 0,    2,    0,    0,    1),
      ( 1,    0,    0,   -4,    1),
      ( 0,    2,    2,   -2,    1),
      (-3,    0,    0,    4,    0),
      (-1,    1,    2,    0,    1),
      (-1,   -1,    0,    4,    0),
      (-1,   -2,    2,    2,    2),
      (-2,   -1,    2,    4,    2),
      ( 1,   -1,    2,    2,    1),
      (-2,    1,    0,    2,    0),
      (-2,    1,    2,    0,    1),
      ( 2,    1,    0,   -2,    1),
      (-3,    0,    2,    0,    1),
      (-2,    0,    2,   -2,    1),
      (-1,    1,    0,    2,    2),
      ( 0,   -1,    2,   -1,    2),
      (-1,    0,    4,   -2,    2),
      ( 0,   -2,    2,    0,    2),
      (-1,    0,    2,    1,    2),
      ( 2,    0,    0,    0,    2),
      ( 0,    0,    2,    0,    3),
      (-2,    0,    4,    0,    2),
      (-1,    0,   -2,    0,    1),
      (-1,    1,    2,    2,    1),
      ( 3,    0,    0,    0,    1),
      (-1,    0,    2,    3,    2),
      ( 2,   -1,    2,    0,    1),
      ( 0,    1,    2,    2,    1),
      ( 0,   -1,    2,    4,    2),
      ( 2,   -1,    2,    2,    2),
      ( 0,    2,   -2,    2,    0),
      (-1,   -1,    2,   -1,    1),
      ( 0,   -2,    0,    0,    1),
      ( 1,    0,    2,   -4,    2),
      ( 1,   -1,    0,   -2,    1),
      (-1,   -1,    2,    0,    1),
      ( 1,   -1,    2,   -2,    2),
      (-2,   -1,    0,    4,    0),
      (-1,    0,    0,    3,    0),
      (-2,   -1,    2,    2,    2),
      ( 0,    2,    2,    0,    2),
      ( 1,    1,    0,    2,    0),
      ( 2,    0,    2,   -1,    2),
      ( 1,    0,    2,    1,    1),
      ( 4,    0,    0,    0,    0),
      ( 2,    1,    2,    0,    1),
      ( 3,   -1,    2,    0,    2),
      (-2,    2,    0,    2,    1),
      ( 1,    0,    2,   -3,    1),
      ( 1,    1,    2,   -4,    1),
      (-1,   -1,    2,   -2,    1),
      ( 0,   -1,    0,   -1,    1),
      ( 0,   -1,    0,   -2,    1),
      (-2,    0,    0,    0,    2),
      (-2,    0,   -2,    2,    0),
      (-1,    0,   -2,    4,    0),
      ( 1,   -2,    0,    0,    0),
      ( 0,    1,    0,    1,    1),
      (-1,    2,    0,    2,    0),
      ( 1,   -1,    2,   -2,    1),
      ( 1,    2,    2,   -2,    2),
      ( 2,   -1,    2,   -2,    2),
      ( 1,    0,    2,   -1,    1),
      ( 2,    1,    2,   -2,    1),
      (-2,    0,    0,   -2,    1),
      ( 1,   -2,    2,    0,    2),
      ( 0,    1,    2,    1,    1),
      ( 1,    0,    4,   -2,    1),
      (-2,    0,    4,    2,    2),
      ( 1,    1,    2,    1,    2),
      ( 1,    0,    0,    4,    0),
      ( 1,    0,    2,    2,    0),
      ( 2,    0,    2,    1,    2),
      ( 3,    1,    2,    0,    2),
      ( 4,    0,    2,    0,    1),
      (-2,   -1,    2,    0,    0),
      ( 0,    1,   -2,    2,    1),
      ( 1,    0,   -2,    1,    0),
      ( 0,   -1,   -2,    2,    1),
      ( 2,   -1,    0,   -2,    1),
      (-1,    0,    2,   -1,    2),
      ( 1,    0,    2,   -3,    2),
      ( 0,    1,    2,   -2,    3),
      ( 0,    0,    2,   -3,    1),
      (-1,    0,   -2,    2,    1),
      ( 0,    0,    2,   -4,    2),
      (-2,    1,    0,    0,    1),
      (-1,    0,    0,   -1,    1),
      ( 2,    0,    2,   -4,    2),
      ( 0,    0,    4,   -4,    4),
      ( 0,    0,    4,   -4,    2),
      (-1,   -2,    0,    2,    1),
      (-2,    0,    0,    3,    0),
      ( 1,    0,   -2,    2,    1),
      (-3,    0,    2,    2,    2),
      (-3,    0,    2,    2,    1),
      (-2,    0,    2,    2,    0),
      ( 2,   -1,    0,    0,    1),
      (-2,    1,    2,    2,    2),
      ( 1,    1,    0,    1,    0),
      ( 0,    1,    4,   -2,    2),
      (-1,    1,    0,   -2,    1),
      ( 0,    0,    0,   -4,    1),
      ( 1,   -1,    0,    2,    1),
      ( 1,    1,    0,    2,    1),
      (-1,    2,    2,    2,    2),
      ( 3,    1,    2,   -2,    2),
      ( 0,   -1,    0,    4,    0),
      ( 2,   -1,    0,    2,    0),
      ( 0,    0,    4,    0,    1),
      ( 2,    0,    4,   -2,    2),
      (-1,   -1,    2,    4,    1),
      ( 1,    0,    0,    4,    1),
      ( 1,   -2,    2,    2,    2),
      ( 0,    0,    2,    3,    2),
      (-1,    1,    2,    4,    2),
      ( 3,    0,    0,    2,    0),
      (-1,    0,    4,    2,    2),
      ( 1,    1,    2,    2,    1),
      (-2,    0,    2,    6,    2),
      ( 2,    1,    2,    2,    2),
      (-1,    0,    2,    6,    2),
      ( 1,    0,    2,    4,    1),
      ( 2,    0,    2,    4,    2),
      ( 1,    1,   -2,    1,    0),
      (-3,    1,    2,    1,    2),
      ( 2,    0,   -2,    0,    2),
      (-1,    0,    0,    1,    2),
      (-4,    0,    2,    2,    1),
      (-1,   -1,    0,    1,    0),
      ( 0,    0,   -2,    2,    2),
      ( 1,    0,    0,   -1,    2),
      ( 0,   -1,    2,   -2,    3),
      (-2,    1,    2,    0,    0),
      ( 0,    0,    2,   -2,    4),
      (-2,   -2,    0,    2,    0),
      (-2,    0,   -2,    4,    0),
      ( 0,   -2,   -2,    2,    0),
      ( 1,    2,    0,   -2,    1),
      ( 3,    0,    0,   -4,    1),
      (-1,    1,    2,   -2,    2),
      ( 1,   -1,    2,   -4,    1),
      ( 1,    1,    0,   -2,    2),
      (-3,    0,    2,    0,    0),
      (-3,    0,    2,    0,    2),
      (-2,    0,    0,    1,    0),
      ( 0,    0,   -2,    1,    0),
      (-3,    0,    0,    2,    1),
      (-1,   -1,   -2,    2,    0),
      ( 0,    1,    2,   -4,    1),
      ( 2,    1,    0,   -4,    1),
      ( 0,    2,    0,   -2,    1),
      ( 1,    0,    0,   -3,    1),
      (-2,    0,    2,   -2,    2),
      (-2,   -1,    0,    0,    1),
      (-4,    0,    0,    2,    0),
      ( 1,    1,    0,   -4,    1),
      (-1,    0,    2,   -4,    1),
      ( 0,    0,    4,   -4,    1),
      ( 0,    3,    2,   -2,    2),
      (-3,   -1,    0,    4,    0),
      (-3,    0,    0,    4,    1),
      ( 1,   -1,   -2,    2,    0),
      (-1,   -1,    0,    2,    2),
      ( 1,   -2,    0,    0,    1),
      ( 1,   -1,    0,    0,    2),
      ( 0,    0,    0,    1,    2),
      (-1,   -1,    2,    0,    0),
      ( 1,   -2,    2,   -2,    2),
      ( 0,   -1,    2,   -1,    1),
      (-1,    0,    2,    0,    3),
      ( 1,    1,    0,    0,    2),
      (-1,    1,    2,    0,    0),
      ( 1,    2,    0,    0,    0),
      (-1,    2,    2,    0,    2),
      (-1,    0,    4,   -2,    1),
      ( 3,    0,    2,   -4,    2),
      ( 1,    2,    2,   -2,    1),
      ( 1,    0,    4,   -4,    2),
      (-2,   -1,    0,    4,    1),
      ( 0,   -1,    0,    2,    2),
      (-2,    1,    0,    4,    0),
      (-2,   -1,    2,    2,    1),
      ( 2,    0,   -2,    2,    0),
      ( 1,    0,    0,    1,    1),
      ( 0,    1,    0,    2,    2),
      ( 1,   -1,    2,   -1,    2),
      (-2,    0,    4,    0,    1),
      ( 2,    1,    0,    0,    1),
      ( 0,    1,    2,    0,    0),
      ( 0,   -1,    4,   -2,    2),
      ( 0,    0,    4,   -2,    4),
      ( 0,    2,    2,    0,    1),
      (-3,    0,    0,    6,    0),
      (-1,   -1,    0,    4,    1),
      ( 1,   -2,    0,    2,    0),
      (-1,    0,    0,    4,    2),
      (-1,   -2,    2,    2,    1),
      (-1,    0,    0,   -2,    2),
      ( 1,    0,   -2,   -2,    1),
      ( 0,    0,   -2,   -2,    1),
      (-2,    0,   -2,    0,    1),
      ( 0,    0,    0,    3,    1),
      ( 0,    0,    0,    3,    0),
      (-1,    1,    0,    4,    0),
      (-1,   -1,    2,    2,    0),
      (-2,    0,    2,    3,    2),
      ( 1,    0,    0,    2,    2),
      ( 0,   -1,    2,    1,    2),
      ( 3,   -1,    0,    0,    0),
      ( 2,    0,    0,    1,    0),
      ( 1,   -1,    2,    0,    0),
      ( 0,    0,    2,    1,    0),
      ( 1,    0,    2,    0,    3),
      ( 3,    1,    0,    0,    0),
      ( 3,   -1,    2,   -2,    2),
      ( 2,    0,    2,   -1,    1),
      ( 1,    1,    2,    0,    0),
      ( 0,    0,    4,   -1,    2),
      ( 1,    2,    2,    0,    2),
      (-2,    0,    0,    6,    0),
      ( 0,   -1,    0,    4,    1),
      (-2,   -1,    2,    4,    1),
      ( 0,   -2,    2,    2,    1),
      ( 0,   -1,    2,    2,    0),
      (-1,    0,    2,    3,    1),
      (-2,    1,    2,    4,    2),
      ( 2,    0,    0,    2,    2),
      ( 2,   -2,    2,    0,    2),
      (-1,    1,    2,    3,    2),
      ( 3,    0,    2,   -1,    2),
      ( 4,    0,    2,   -2,    1),
      (-1,    0,    0,    6,    0),
      (-1,   -2,    2,    4,    2),
      (-3,    0,    2,    6,    2),
      (-1,    0,    2,    4,    0),
      ( 3,    0,    0,    2,    1),
      ( 3,   -1,    2,    0,    1),
      ( 3,    0,    2,    0,    0),
      ( 1,    0,    4,    0,    2),
      ( 5,    0,    2,   -2,    2),
      ( 0,   -1,    2,    4,    1),
      ( 2,   -1,    2,    2,    1),
      ( 0,    1,    2,    4,    2),
      ( 1,   -1,    2,    4,    2),
      ( 3,   -1,    2,    2,    2),
      ( 3,    0,    2,    2,    1),
      ( 5,    0,    2,    0,    2),
      ( 0,    0,    2,    6,    2),
      ( 4,    0,    2,    2,    2),
      ( 0,   -1,    1,   -1,    1),
      (-1,    0,    1,    0,    3),
      ( 0,   -2,    2,   -2,    3),
      ( 1,    0,   -1,    0,    1),
      ( 2,   -2,    0,   -2,    1),
      (-1,    0,    1,    0,    2),
      (-1,    0,    1,    0,    1),
      (-1,   -1,    2,   -1,    2),
      (-2,    2,    0,    2,    2),
      (-1,    0,    1,    0,    0),
      (-4,    1,    2,    2,    2),
      (-3,    0,    2,    1,    1),
      (-2,   -1,    2,    0,    2),
      ( 1,    0,   -2,    1,    1),
      ( 2,   -1,   -2,    0,    1),
      (-4,    0,    2,    2,    0),
      (-3,    1,    0,    3,    0),
      (-1,    0,   -1,    2,    0),
      ( 0,   -2,    0,    0,    2),
      ( 0,   -2,    0,    0,    2),
      (-3,    0,    0,    3,    0),
      (-2,   -1,    0,    2,    2),
      (-1,    0,   -2,    3,    0),
      (-4,    0,    0,    4,    0),
      ( 2,    1,   -2,    0,    1),
      ( 2,   -1,    0,   -2,    2),
      ( 0,    0,    1,   -1,    0),
      (-1,    2,    0,    1,    0),
      (-2,    1,    2,    0,    2),
      ( 1,    1,    0,   -1,    1),
      ( 1,    0,    1,   -2,    1),
      ( 0,    2,    0,    0,    2),
      ( 1,   -1,    2,   -3,    1),
      (-1,    1,    2,   -1,    1),
      (-2,    0,    4,   -2,    2),
      (-2,    0,    4,   -2,    1),
      (-2,   -2,    0,    2,    1),
      (-2,    0,   -2,    4,    0),
      ( 1,    2,    2,   -4,    1),
      ( 1,    1,    2,   -4,    2),
      (-1,    2,    2,   -2,    1),
      ( 2,    0,    0,   -3,    1),
      (-1,    2,    0,    0,    1),
      ( 0,    0,    0,   -2,    0),
      (-1,   -1,    2,   -2,    2),
      (-1,    1,    0,    0,    2),
      ( 0,    0,    0,   -1,    2),
      (-2,    1,    0,    1,    0),
      ( 1,   -2,    0,   -2,    1),
      ( 1,    0,   -2,    0,    2),
      (-3,    1,    0,    2,    0),
      (-1,    1,   -2,    2,    0),
      (-1,   -1,    0,    0,    2),
      (-3,    0,    0,    2,    0),
      (-3,   -1,    0,    2,    0),
      ( 2,    0,    2,   -6,    1),
      ( 0,    1,    2,   -4,    2),
      ( 2,    0,    0,   -4,    2),
      (-2,    1,    2,   -2,    1),
      ( 0,   -1,    2,   -4,    1),
      ( 0,    1,    0,   -2,    2),
      (-1,    0,    0,   -2,    0),
      ( 2,    0,   -2,   -2,    1),
      (-4,    0,    2,    0,    1),
      (-1,   -1,    0,   -1,    1),
      ( 0,    0,   -2,    0,    2),
      (-3,    0,    0,    1,    0),
      (-1,    0,   -2,    1,    0),
      (-2,    0,   -2,    2,    1),
      ( 0,    0,   -4,    2,    0),
      (-2,   -1,   -2,    2,    0),
      ( 1,    0,    2,   -6,    1),
      (-1,    0,    2,   -4,    2),
      ( 1,    0,    0,   -4,    2),
      ( 2,    1,    2,   -4,    2),
      ( 2,    1,    2,   -4,    1),
      ( 0,    1,    4,   -4,    4),
      ( 0,    1,    4,   -4,    2),
      (-1,   -1,   -2,    4,    0),
      (-1,   -3,    0,    2,    0),
      (-1,    0,   -2,    4,    1),
      (-2,   -1,    0,    3,    0),
      ( 0,    0,   -2,    3,    0),
      (-2,    0,    0,    3,    1),
      ( 0,   -1,    0,    1,    0),
      (-3,    0,    2,    2,    0),
      ( 1,    1,   -2,    2,    0),
      (-1,    1,    0,    2,    2),
      ( 1,   -2,    2,   -2,    1),
      ( 0,    0,    1,    0,    2),
      ( 0,    0,    1,    0,    1),
      ( 0,    0,    1,    0,    0),
      (-1,    2,    0,    2,    1),
      ( 0,    0,    2,    0,    2),
      (-2,    0,    2,    0,    2),
      ( 2,    0,    0,   -1,    1),
      ( 3,    0,    0,   -2,    1),
      ( 1,    0,    2,   -2,    3),
      ( 1,    2,    0,    0,    1),
      ( 2,    0,    2,   -3,    2),
      (-1,    1,    4,   -2,    2),
      (-2,   -2,    0,    4,    0),
      ( 0,   -3,    0,    2,    0),
      ( 0,    0,   -2,    4,    0),
      (-1,   -1,    0,    3,    0),
      (-2,    0,    0,    4,    2),
      (-1,    0,    0,    3,    1),
      ( 2,   -2,    0,    0,    0),
      ( 1,   -1,    0,    1,    0),
      (-1,    0,    0,    2,    0),
      ( 0,   -2,    2,    0,    1),
      (-1,    0,    1,    2,    1),
      (-1,    1,    0,    3,    0),
      (-1,   -1,    2,    1,    2),
      ( 0,   -1,    2,    0,    0),
      (-2,    1,    2,    2,    1),
      ( 2,   -2,    2,   -2,    2),
      ( 1,    1,    0,    1,    1),
      ( 1,    0,    1,    0,    1),
      ( 1,    0,    1,    0,    0),
      ( 0,    2,    0,    2,    0),
      ( 2,   -1,    2,   -2,    1),
      ( 0,   -1,    4,   -2,    1),
      ( 0,    0,    4,   -2,    3),
      ( 0,    1,    4,   -2,    1),
      ( 4,    0,    2,   -4,    2),
      ( 2,    2,    2,   -2,    2),
      ( 2,    0,    4,   -4,    2),
      (-1,   -2,    0,    4,    0),
      (-1,   -3,    2,    2,    2),
      (-3,    0,    2,    4,    2),
      (-3,    0,    2,   -2,    1),
      (-1,   -1,    0,   -2,    1),
      (-3,    0,    0,    0,    2),
      (-3,    0,   -2,    2,    0),
      ( 0,    1,    0,   -4,    1),
      (-2,    1,    0,   -2,    1),
      (-4,    0,    0,    0,    1),
      (-1,    0,    0,   -4,    1),
      (-3,    0,    0,   -2,    1),
      ( 0,    0,    0,    3,    2),
      (-1,    1,    0,    4,    1),
      ( 1,   -2,    2,    0,    1),
      ( 0,    1,    0,    3,    0),
      (-1,    0,    2,    2,    3),
      ( 0,    0,    2,    2,    2),
      (-2,    0,    2,    2,    2),
      (-1,    1,    2,    2,    0),
      ( 3,    0,    0,    0,    2),
      ( 2,    1,    0,    1,    0),
      ( 2,   -1,    2,   -1,    2),
      ( 0,    0,    2,    0,    1),
      ( 0,    0,    3,    0,    3),
      ( 0,    0,    3,    0,    2),
      (-1,    2,    2,    2,    1),
      (-1,    0,    4,    0,    0),
      ( 1,    2,    2,    0,    1),
      ( 3,    1,    2,   -2,    1),
      ( 1,    1,    4,   -2,    2),
      (-2,   -1,    0,    6,    0),
      ( 0,   -2,    0,    4,    0),
      (-2,    0,    0,    6,    1),
      (-2,   -2,    2,    4,    2),
      ( 0,   -3,    2,    2,    2),
      ( 0,    0,    0,    4,    2),
      (-1,   -1,    2,    3,    2),
      (-2,    0,    2,    4,    0),
      ( 2,   -1,    0,    2,    1),
      ( 1,    0,    0,    3,    0),
      ( 0,    1,    0,    4,    1),
      ( 0,    1,    0,    4,    0),
      ( 1,   -1,    2,    1,    2),
      ( 0,    0,    2,    2,    3),
      ( 1,    0,    2,    2,    2),
      (-1,    0,    2,    2,    2),
      (-2,    0,    4,    2,    1),
      ( 2,    1,    0,    2,    1),
      ( 2,    1,    0,    2,    0),
      ( 2,   -1,    2,    0,    0),
      ( 1,    0,    2,    1,    0),
      ( 0,    1,    2,    2,    0),
      ( 2,    0,    2,    0,    3),
      ( 3,    0,    2,    0,    2),
      ( 1,    0,    2,    0,    2),
      ( 1,    0,    3,    0,    3),
      ( 1,    1,    2,    1,    1),
      ( 0,    2,    2,    2,    2),
      ( 2,    1,    2,    0,    0),
      ( 2,    0,    4,   -2,    1),
      ( 4,    1,    2,   -2,    2),
      (-1,   -1,    0,    6,    0),
      (-3,   -1,    2,    6,    2),
      (-1,    0,    0,    6,    1),
      (-3,    0,    2,    6,    1),
      ( 1,   -1,    0,    4,    1),
      ( 1,   -1,    0,    4,    0),
      (-2,    0,    2,    5,    2),
      ( 1,   -2,    2,    2,    1),
      ( 3,   -1,    0,    2,    0),
      ( 1,   -1,    2,    2,    0),
      ( 0,    0,    2,    3,    1),
      (-1,    1,    2,    4,    1),
      ( 0,    1,    2,    3,    2),
      (-1,    0,    4,    2,    1),
      ( 2,    0,    2,    1,    1),
      ( 5,    0,    0,    0,    0),
      ( 2,    1,    2,    1,    2),
      ( 1,    0,    4,    0,    1),
      ( 3,    1,    2,    0,    1),
      ( 3,    0,    4,   -2,    2),
      (-2,   -1,    2,    6,    2),
      ( 0,    0,    0,    6,    0),
      ( 0,   -2,    2,    4,    2),
      (-2,    0,    2,    6,    1),
      ( 2,    0,    0,    4,    1),
      ( 2,    0,    0,    4,    0),
      ( 2,   -2,    2,    2,    2),
      ( 0,    0,    2,    4,    0),
      ( 1,    0,    2,    3,    2),
      ( 4,    0,    0,    2,    0),
      ( 2,    0,    2,    2,    0),
      ( 0,    0,    4,    2,    2),
      ( 4,   -1,    2,    0,    2),
      ( 3,    0,    2,    1,    2),
      ( 2,    1,    2,    2,    1),
      ( 4,    1,    2,    0,    2),
      (-1,   -1,    2,    6,    2),
      (-1,    0,    2,    6,    1),
      ( 1,   -1,    2,    4,    1),
      ( 1,    1,    2,    4,    2),
      ( 3,    1,    2,    2,    2),
      ( 5,    0,    2,    0,    1),
      ( 2,   -1,    2,    4,    2),
      ( 2,    0,    2,    4,    1),
      ))

# Luni-Solar nutation coefficients, unit 1e-7 arcsec:
# longitude (sin, t*sin, cos), obliquity (cos, t*cos, sin)

# Each row of coefficients belongs with the corresponding row of
# fundamental-argument multipliers in 'nals_t'.

lunisolar_coefficients = array((
      (-172064161.0, -174666.0,  33386.0, 92052331.0,  9086.0, 15377.0),
      ( -13170906.0,   -1675.0, -13696.0,  5730336.0, -3015.0, -4587.0),
      (  -2276413.0,    -234.0,   2796.0,   978459.0,  -485.0,  1374.0),
      (   2074554.0,     207.0,   -698.0,  -897492.0,   470.0,  -291.0),
      (   1475877.0,   -3633.0,  11817.0,    73871.0,  -184.0, -1924.0),
      (   -516821.0,    1226.0,   -524.0,   224386.0,  -677.0,  -174.0),
      (    711159.0,      73.0,   -872.0,    -6750.0,     0.0,   358.0),
      (   -387298.0,    -367.0,    380.0,   200728.0,    18.0,   318.0),
      (   -301461.0,     -36.0,    816.0,   129025.0,   -63.0,   367.0),
      (    215829.0,    -494.0,    111.0,   -95929.0,   299.0,   132.0),
      (    128227.0,     137.0,    181.0,   -68982.0,    -9.0,    39.0),
      (    123457.0,      11.0,     19.0,   -53311.0,    32.0,    -4.0),
      (    156994.0,      10.0,   -168.0,    -1235.0,     0.0,    82.0),
      (     63110.0,      63.0,     27.0,   -33228.0,     0.0,    -9.0),
      (    -57976.0,     -63.0,   -189.0,    31429.0,     0.0,   -75.0),
      (    -59641.0,     -11.0,    149.0,    25543.0,   -11.0,    66.0),
      (    -51613.0,     -42.0,    129.0,    26366.0,     0.0,    78.0),
      (     45893.0,      50.0,     31.0,   -24236.0,   -10.0,    20.0),
      (     63384.0,      11.0,   -150.0,    -1220.0,     0.0,    29.0),
      (    -38571.0,      -1.0,    158.0,    16452.0,   -11.0,    68.0),
      (     32481.0,       0.0,      0.0,   -13870.0,     0.0,     0.0),
      (    -47722.0,       0.0,    -18.0,      477.0,     0.0,   -25.0),
      (    -31046.0,      -1.0,    131.0,    13238.0,   -11.0,    59.0),
      (     28593.0,       0.0,     -1.0,   -12338.0,    10.0,    -3.0),
      (     20441.0,      21.0,     10.0,   -10758.0,     0.0,    -3.0),
      (     29243.0,       0.0,    -74.0,     -609.0,     0.0,    13.0),
      (     25887.0,       0.0,    -66.0,     -550.0,     0.0,    11.0),
      (    -14053.0,     -25.0,     79.0,     8551.0,    -2.0,   -45.0),
      (     15164.0,      10.0,     11.0,    -8001.0,     0.0,    -1.0),
      (    -15794.0,      72.0,    -16.0,     6850.0,   -42.0,    -5.0),
      (     21783.0,       0.0,     13.0,     -167.0,     0.0,    13.0),
      (    -12873.0,     -10.0,    -37.0,     6953.0,     0.0,   -14.0),
      (    -12654.0,      11.0,     63.0,     6415.0,     0.0,    26.0),
      (    -10204.0,       0.0,     25.0,     5222.0,     0.0,    15.0),
      (     16707.0,     -85.0,    -10.0,      168.0,    -1.0,    10.0),
      (     -7691.0,       0.0,     44.0,     3268.0,     0.0,    19.0),
      (    -11024.0,       0.0,    -14.0,      104.0,     0.0,     2.0),
      (      7566.0,     -21.0,    -11.0,    -3250.0,     0.0,    -5.0),
      (     -6637.0,     -11.0,     25.0,     3353.0,     0.0,    14.0),
      (     -7141.0,      21.0,      8.0,     3070.0,     0.0,     4.0),
      (     -6302.0,     -11.0,      2.0,     3272.0,     0.0,     4.0),
      (      5800.0,      10.0,      2.0,    -3045.0,     0.0,    -1.0),
      (      6443.0,       0.0,     -7.0,    -2768.0,     0.0,    -4.0),
      (     -5774.0,     -11.0,    -15.0,     3041.0,     0.0,    -5.0),
      (     -5350.0,       0.0,     21.0,     2695.0,     0.0,    12.0),
      (     -4752.0,     -11.0,     -3.0,     2719.0,     0.0,    -3.0),
      (     -4940.0,     -11.0,    -21.0,     2720.0,     0.0,    -9.0),
      (      7350.0,       0.0,     -8.0,      -51.0,     0.0,     4.0),
      (      4065.0,       0.0,      6.0,    -2206.0,     0.0,     1.0),
      (      6579.0,       0.0,    -24.0,     -199.0,     0.0,     2.0),
      (      3579.0,       0.0,      5.0,    -1900.0,     0.0,     1.0),
      (      4725.0,       0.0,     -6.0,      -41.0,     0.0,     3.0),
      (     -3075.0,       0.0,     -2.0,     1313.0,     0.0,    -1.0),
      (     -2904.0,       0.0,     15.0,     1233.0,     0.0,     7.0),
      (      4348.0,       0.0,    -10.0,      -81.0,     0.0,     2.0),
      (     -2878.0,       0.0,      8.0,     1232.0,     0.0,     4.0),
      (     -4230.0,       0.0,      5.0,      -20.0,     0.0,    -2.0),
      (     -2819.0,       0.0,      7.0,     1207.0,     0.0,     3.0),
      (     -4056.0,       0.0,      5.0,       40.0,     0.0,    -2.0),
      (     -2647.0,       0.0,     11.0,     1129.0,     0.0,     5.0),
      (     -2294.0,       0.0,    -10.0,     1266.0,     0.0,    -4.0),
      (      2481.0,       0.0,     -7.0,    -1062.0,     0.0,    -3.0),
      (      2179.0,       0.0,     -2.0,    -1129.0,     0.0,    -2.0),
      (      3276.0,       0.0,      1.0,       -9.0,     0.0,     0.0),
      (     -3389.0,       0.0,      5.0,       35.0,     0.0,    -2.0),
      (      3339.0,       0.0,    -13.0,     -107.0,     0.0,     1.0),
      (     -1987.0,       0.0,     -6.0,     1073.0,     0.0,    -2.0),
      (     -1981.0,       0.0,      0.0,      854.0,     0.0,     0.0),
      (      4026.0,       0.0,   -353.0,     -553.0,     0.0,  -139.0),
      (      1660.0,       0.0,     -5.0,     -710.0,     0.0,    -2.0),
      (     -1521.0,       0.0,      9.0,      647.0,     0.0,     4.0),
      (      1314.0,       0.0,      0.0,     -700.0,     0.0,     0.0),
      (     -1283.0,       0.0,      0.0,      672.0,     0.0,     0.0),
      (     -1331.0,       0.0,      8.0,      663.0,     0.0,     4.0),
      (      1383.0,       0.0,     -2.0,     -594.0,     0.0,    -2.0),
      (      1405.0,       0.0,      4.0,     -610.0,     0.0,     2.0),
      (      1290.0,       0.0,      0.0,     -556.0,     0.0,     0.0),
      (     -1214.0,       0.0,      5.0,      518.0,     0.0,     2.0),
      (      1146.0,       0.0,     -3.0,     -490.0,     0.0,    -1.0),
      (      1019.0,       0.0,     -1.0,     -527.0,     0.0,    -1.0),
      (     -1100.0,       0.0,      9.0,      465.0,     0.0,     4.0),
      (      -970.0,       0.0,      2.0,      496.0,     0.0,     1.0),
      (      1575.0,       0.0,     -6.0,      -50.0,     0.0,     0.0),
      (       934.0,       0.0,     -3.0,     -399.0,     0.0,    -1.0),
      (       922.0,       0.0,     -1.0,     -395.0,     0.0,    -1.0),
      (       815.0,       0.0,     -1.0,     -422.0,     0.0,    -1.0),
      (       834.0,       0.0,      2.0,     -440.0,     0.0,     1.0),
      (      1248.0,       0.0,      0.0,     -170.0,     0.0,     1.0),
      (      1338.0,       0.0,     -5.0,      -39.0,     0.0,     0.0),
      (       716.0,       0.0,     -2.0,     -389.0,     0.0,    -1.0),
      (      1282.0,       0.0,     -3.0,      -23.0,     0.0,     1.0),
      (       742.0,       0.0,      1.0,     -391.0,     0.0,     0.0),
      (      1020.0,       0.0,    -25.0,     -495.0,     0.0,   -10.0),
      (       715.0,       0.0,     -4.0,     -326.0,     0.0,     2.0),
      (      -666.0,       0.0,     -3.0,      369.0,     0.0,    -1.0),
      (      -667.0,       0.0,      1.0,      346.0,     0.0,     1.0),
      (      -704.0,       0.0,      0.0,      304.0,     0.0,     0.0),
      (      -694.0,       0.0,      5.0,      294.0,     0.0,     2.0),
      (     -1014.0,       0.0,     -1.0,        4.0,     0.0,    -1.0),
      (      -585.0,       0.0,     -2.0,      316.0,     0.0,    -1.0),
      (      -949.0,       0.0,      1.0,        8.0,     0.0,    -1.0),
      (      -595.0,       0.0,      0.0,      258.0,     0.0,     0.0),
      (       528.0,       0.0,      0.0,     -279.0,     0.0,     0.0),
      (      -590.0,       0.0,      4.0,      252.0,     0.0,     2.0),
      (       570.0,       0.0,     -2.0,     -244.0,     0.0,    -1.0),
      (      -502.0,       0.0,      3.0,      250.0,     0.0,     2.0),
      (      -875.0,       0.0,      1.0,       29.0,     0.0,     0.0),
      (      -492.0,       0.0,     -3.0,      275.0,     0.0,    -1.0),
      (       535.0,       0.0,     -2.0,     -228.0,     0.0,    -1.0),
      (      -467.0,       0.0,      1.0,      240.0,     0.0,     1.0),
      (       591.0,       0.0,      0.0,     -253.0,     0.0,     0.0),
      (      -453.0,       0.0,     -1.0,      244.0,     0.0,    -1.0),
      (       766.0,       0.0,      1.0,        9.0,     0.0,     0.0),
      (      -446.0,       0.0,      2.0,      225.0,     0.0,     1.0),
      (      -488.0,       0.0,      2.0,      207.0,     0.0,     1.0),
      (      -468.0,       0.0,      0.0,      201.0,     0.0,     0.0),
      (      -421.0,       0.0,      1.0,      216.0,     0.0,     1.0),
      (       463.0,       0.0,      0.0,     -200.0,     0.0,     0.0),
      (      -673.0,       0.0,      2.0,       14.0,     0.0,     0.0),
      (       658.0,       0.0,      0.0,       -2.0,     0.0,     0.0),
      (      -438.0,       0.0,      0.0,      188.0,     0.0,     0.0),
      (      -390.0,       0.0,      0.0,      205.0,     0.0,     0.0),
      (       639.0,     -11.0,     -2.0,      -19.0,     0.0,     0.0),
      (       412.0,       0.0,     -2.0,     -176.0,     0.0,    -1.0),
      (      -361.0,       0.0,      0.0,      189.0,     0.0,     0.0),
      (       360.0,       0.0,     -1.0,     -185.0,     0.0,    -1.0),
      (       588.0,       0.0,     -3.0,      -24.0,     0.0,     0.0),
      (      -578.0,       0.0,      1.0,        5.0,     0.0,     0.0),
      (      -396.0,       0.0,      0.0,      171.0,     0.0,     0.0),
      (       565.0,       0.0,     -1.0,       -6.0,     0.0,     0.0),
      (      -335.0,       0.0,     -1.0,      184.0,     0.0,    -1.0),
      (       357.0,       0.0,      1.0,     -154.0,     0.0,     0.0),
      (       321.0,       0.0,      1.0,     -174.0,     0.0,     0.0),
      (      -301.0,       0.0,     -1.0,      162.0,     0.0,     0.0),
      (      -334.0,       0.0,      0.0,      144.0,     0.0,     0.0),
      (       493.0,       0.0,     -2.0,      -15.0,     0.0,     0.0),
      (       494.0,       0.0,     -2.0,      -19.0,     0.0,     0.0),
      (       337.0,       0.0,     -1.0,     -143.0,     0.0,    -1.0),
      (       280.0,       0.0,     -1.0,     -144.0,     0.0,     0.0),
      (       309.0,       0.0,      1.0,     -134.0,     0.0,     0.0),
      (      -263.0,       0.0,      2.0,      131.0,     0.0,     1.0),
      (       253.0,       0.0,      1.0,     -138.0,     0.0,     0.0),
      (       245.0,       0.0,      0.0,     -128.0,     0.0,     0.0),
      (       416.0,       0.0,     -2.0,      -17.0,     0.0,     0.0),
      (      -229.0,       0.0,      0.0,      128.0,     0.0,     0.0),
      (       231.0,       0.0,      0.0,     -120.0,     0.0,     0.0),
      (      -259.0,       0.0,      2.0,      109.0,     0.0,     1.0),
      (       375.0,       0.0,     -1.0,       -8.0,     0.0,     0.0),
      (       252.0,       0.0,      0.0,     -108.0,     0.0,     0.0),
      (      -245.0,       0.0,      1.0,      104.0,     0.0,     0.0),
      (       243.0,       0.0,     -1.0,     -104.0,     0.0,     0.0),
      (       208.0,       0.0,      1.0,     -112.0,     0.0,     0.0),
      (       199.0,       0.0,      0.0,     -102.0,     0.0,     0.0),
      (      -208.0,       0.0,      1.0,      105.0,     0.0,     0.0),
      (       335.0,       0.0,     -2.0,      -14.0,     0.0,     0.0),
      (      -325.0,       0.0,      1.0,        7.0,     0.0,     0.0),
      (      -187.0,       0.0,      0.0,       96.0,     0.0,     0.0),
      (       197.0,       0.0,     -1.0,     -100.0,     0.0,     0.0),
      (      -192.0,       0.0,      2.0,       94.0,     0.0,     1.0),
      (      -188.0,       0.0,      0.0,       83.0,     0.0,     0.0),
      (       276.0,       0.0,      0.0,       -2.0,     0.0,     0.0),
      (      -286.0,       0.0,      1.0,        6.0,     0.0,     0.0),
      (       186.0,       0.0,     -1.0,      -79.0,     0.0,     0.0),
      (      -219.0,       0.0,      0.0,       43.0,     0.0,     0.0),
      (       276.0,       0.0,      0.0,        2.0,     0.0,     0.0),
      (      -153.0,       0.0,     -1.0,       84.0,     0.0,     0.0),
      (      -156.0,       0.0,      0.0,       81.0,     0.0,     0.0),
      (      -154.0,       0.0,      1.0,       78.0,     0.0,     0.0),
      (      -174.0,       0.0,      1.0,       75.0,     0.0,     0.0),
      (      -163.0,       0.0,      2.0,       69.0,     0.0,     1.0),
      (      -228.0,       0.0,      0.0,        1.0,     0.0,     0.0),
      (        91.0,       0.0,     -4.0,      -54.0,     0.0,    -2.0),
      (       175.0,       0.0,      0.0,      -75.0,     0.0,     0.0),
      (      -159.0,       0.0,      0.0,       69.0,     0.0,     0.0),
      (       141.0,       0.0,      0.0,      -72.0,     0.0,     0.0),
      (       147.0,       0.0,      0.0,      -75.0,     0.0,     0.0),
      (      -132.0,       0.0,      0.0,       69.0,     0.0,     0.0),
      (       159.0,       0.0,    -28.0,      -54.0,     0.0,    11.0),
      (       213.0,       0.0,      0.0,       -4.0,     0.0,     0.0),
      (       123.0,       0.0,      0.0,      -64.0,     0.0,     0.0),
      (      -118.0,       0.0,     -1.0,       66.0,     0.0,     0.0),
      (       144.0,       0.0,     -1.0,      -61.0,     0.0,     0.0),
      (      -121.0,       0.0,      1.0,       60.0,     0.0,     0.0),
      (      -134.0,       0.0,      1.0,       56.0,     0.0,     1.0),
      (      -105.0,       0.0,      0.0,       57.0,     0.0,     0.0),
      (      -102.0,       0.0,      0.0,       56.0,     0.0,     0.0),
      (       120.0,       0.0,      0.0,      -52.0,     0.0,     0.0),
      (       101.0,       0.0,      0.0,      -54.0,     0.0,     0.0),
      (      -113.0,       0.0,      0.0,       59.0,     0.0,     0.0),
      (      -106.0,       0.0,      0.0,       61.0,     0.0,     0.0),
      (      -129.0,       0.0,      1.0,       55.0,     0.0,     0.0),
      (      -114.0,       0.0,      0.0,       57.0,     0.0,     0.0),
      (       113.0,       0.0,     -1.0,      -49.0,     0.0,     0.0),
      (      -102.0,       0.0,      0.0,       44.0,     0.0,     0.0),
      (       -94.0,       0.0,      0.0,       51.0,     0.0,     0.0),
      (      -100.0,       0.0,     -1.0,       56.0,     0.0,     0.0),
      (        87.0,       0.0,      0.0,      -47.0,     0.0,     0.0),
      (       161.0,       0.0,      0.0,       -1.0,     0.0,     0.0),
      (        96.0,       0.0,      0.0,      -50.0,     0.0,     0.0),
      (       151.0,       0.0,     -1.0,       -5.0,     0.0,     0.0),
      (      -104.0,       0.0,      0.0,       44.0,     0.0,     0.0),
      (      -110.0,       0.0,      0.0,       48.0,     0.0,     0.0),
      (      -100.0,       0.0,      1.0,       50.0,     0.0,     0.0),
      (        92.0,       0.0,     -5.0,       12.0,     0.0,    -2.0),
      (        82.0,       0.0,      0.0,      -45.0,     0.0,     0.0),
      (        82.0,       0.0,      0.0,      -45.0,     0.0,     0.0),
      (       -78.0,       0.0,      0.0,       41.0,     0.0,     0.0),
      (       -77.0,       0.0,      0.0,       43.0,     0.0,     0.0),
      (         2.0,       0.0,      0.0,       54.0,     0.0,     0.0),
      (        94.0,       0.0,      0.0,      -40.0,     0.0,     0.0),
      (       -93.0,       0.0,      0.0,       40.0,     0.0,     0.0),
      (       -83.0,       0.0,     10.0,       40.0,     0.0,    -2.0),
      (        83.0,       0.0,      0.0,      -36.0,     0.0,     0.0),
      (       -91.0,       0.0,      0.0,       39.0,     0.0,     0.0),
      (       128.0,       0.0,      0.0,       -1.0,     0.0,     0.0),
      (       -79.0,       0.0,      0.0,       34.0,     0.0,     0.0),
      (       -83.0,       0.0,      0.0,       47.0,     0.0,     0.0),
      (        84.0,       0.0,      0.0,      -44.0,     0.0,     0.0),
      (        83.0,       0.0,      0.0,      -43.0,     0.0,     0.0),
      (        91.0,       0.0,      0.0,      -39.0,     0.0,     0.0),
      (       -77.0,       0.0,      0.0,       39.0,     0.0,     0.0),
      (        84.0,       0.0,      0.0,      -43.0,     0.0,     0.0),
      (       -92.0,       0.0,      1.0,       39.0,     0.0,     0.0),
      (       -92.0,       0.0,      1.0,       39.0,     0.0,     0.0),
      (       -94.0,       0.0,      0.0,        0.0,     0.0,     0.0),
      (        68.0,       0.0,      0.0,      -36.0,     0.0,     0.0),
      (       -61.0,       0.0,      0.0,       32.0,     0.0,     0.0),
      (        71.0,       0.0,      0.0,      -31.0,     0.0,     0.0),
      (        62.0,       0.0,      0.0,      -34.0,     0.0,     0.0),
      (       -63.0,       0.0,      0.0,       33.0,     0.0,     0.0),
      (       -73.0,       0.0,      0.0,       32.0,     0.0,     0.0),
      (       115.0,       0.0,      0.0,       -2.0,     0.0,     0.0),
      (      -103.0,       0.0,      0.0,        2.0,     0.0,     0.0),
      (        63.0,       0.0,      0.0,      -28.0,     0.0,     0.0),
      (        74.0,       0.0,      0.0,      -32.0,     0.0,     0.0),
      (      -103.0,       0.0,     -3.0,        3.0,     0.0,    -1.0),
      (       -69.0,       0.0,      0.0,       30.0,     0.0,     0.0),
      (        57.0,       0.0,      0.0,      -29.0,     0.0,     0.0),
      (        94.0,       0.0,      0.0,       -4.0,     0.0,     0.0),
      (        64.0,       0.0,      0.0,      -33.0,     0.0,     0.0),
      (       -63.0,       0.0,      0.0,       26.0,     0.0,     0.0),
      (       -38.0,       0.0,      0.0,       20.0,     0.0,     0.0),
      (       -43.0,       0.0,      0.0,       24.0,     0.0,     0.0),
      (       -45.0,       0.0,      0.0,       23.0,     0.0,     0.0),
      (        47.0,       0.0,      0.0,      -24.0,     0.0,     0.0),
      (       -48.0,       0.0,      0.0,       25.0,     0.0,     0.0),
      (        45.0,       0.0,      0.0,      -26.0,     0.0,     0.0),
      (        56.0,       0.0,      0.0,      -25.0,     0.0,     0.0),
      (        88.0,       0.0,      0.0,        2.0,     0.0,     0.0),
      (       -75.0,       0.0,      0.0,        0.0,     0.0,     0.0),
      (        85.0,       0.0,      0.0,        0.0,     0.0,     0.0),
      (        49.0,       0.0,      0.0,      -26.0,     0.0,     0.0),
      (       -74.0,       0.0,     -3.0,       -1.0,     0.0,    -1.0),
      (       -39.0,       0.0,      0.0,       21.0,     0.0,     0.0),
      (        45.0,       0.0,      0.0,      -20.0,     0.0,     0.0),
      (        51.0,       0.0,      0.0,      -22.0,     0.0,     0.0),
      (       -40.0,       0.0,      0.0,       21.0,     0.0,     0.0),
      (        41.0,       0.0,      0.0,      -21.0,     0.0,     0.0),
      (       -42.0,       0.0,      0.0,       24.0,     0.0,     0.0),
      (       -51.0,       0.0,      0.0,       22.0,     0.0,     0.0),
      (       -42.0,       0.0,      0.0,       22.0,     0.0,     0.0),
      (        39.0,       0.0,      0.0,      -21.0,     0.0,     0.0),
      (        46.0,       0.0,      0.0,      -18.0,     0.0,     0.0),
      (       -53.0,       0.0,      0.0,       22.0,     0.0,     0.0),
      (        82.0,       0.0,      0.0,       -4.0,     0.0,     0.0),
      (        81.0,       0.0,     -1.0,       -4.0,     0.0,     0.0),
      (        47.0,       0.0,      0.0,      -19.0,     0.0,     0.0),
      (        53.0,       0.0,      0.0,      -23.0,     0.0,     0.0),
      (       -45.0,       0.0,      0.0,       22.0,     0.0,     0.0),
      (       -44.0,       0.0,      0.0,       -2.0,     0.0,     0.0),
      (       -33.0,       0.0,      0.0,       16.0,     0.0,     0.0),
      (       -61.0,       0.0,      0.0,        1.0,     0.0,     0.0),
      (        28.0,       0.0,      0.0,      -15.0,     0.0,     0.0),
      (       -38.0,       0.0,      0.0,       19.0,     0.0,     0.0),
      (       -33.0,       0.0,      0.0,       21.0,     0.0,     0.0),
      (       -60.0,       0.0,      0.0,        0.0,     0.0,     0.0),
      (        48.0,       0.0,      0.0,      -10.0,     0.0,     0.0),
      (        27.0,       0.0,      0.0,      -14.0,     0.0,     0.0),
      (        38.0,       0.0,      0.0,      -20.0,     0.0,     0.0),
      (        31.0,       0.0,      0.0,      -13.0,     0.0,     0.0),
      (       -29.0,       0.0,      0.0,       15.0,     0.0,     0.0),
      (        28.0,       0.0,      0.0,      -15.0,     0.0,     0.0),
      (       -32.0,       0.0,      0.0,       15.0,     0.0,     0.0),
      (        45.0,       0.0,      0.0,       -8.0,     0.0,     0.0),
      (       -44.0,       0.0,      0.0,       19.0,     0.0,     0.0),
      (        28.0,       0.0,      0.0,      -15.0,     0.0,     0.0),
      (       -51.0,       0.0,      0.0,        0.0,     0.0,     0.0),
      (       -36.0,       0.0,      0.0,       20.0,     0.0,     0.0),
      (        44.0,       0.0,      0.0,      -19.0,     0.0,     0.0),
      (        26.0,       0.0,      0.0,      -14.0,     0.0,     0.0),
      (       -60.0,       0.0,      0.0,        2.0,     0.0,     0.0),
      (        35.0,       0.0,      0.0,      -18.0,     0.0,     0.0),
      (       -27.0,       0.0,      0.0,       11.0,     0.0,     0.0),
      (        47.0,       0.0,      0.0,       -1.0,     0.0,     0.0),
      (        36.0,       0.0,      0.0,      -15.0,     0.0,     0.0),
      (       -36.0,       0.0,      0.0,       20.0,     0.0,     0.0),
      (       -35.0,       0.0,      0.0,       19.0,     0.0,     0.0),
      (       -37.0,       0.0,      0.0,       19.0,     0.0,     0.0),
      (        32.0,       0.0,      0.0,      -16.0,     0.0,     0.0),
      (        35.0,       0.0,      0.0,      -14.0,     0.0,     0.0),
      (        32.0,       0.0,      0.0,      -13.0,     0.0,     0.0),
      (        65.0,       0.0,      0.0,       -2.0,     0.0,     0.0),
      (        47.0,       0.0,      0.0,       -1.0,     0.0,     0.0),
      (        32.0,       0.0,      0.0,      -16.0,     0.0,     0.0),
      (        37.0,       0.0,      0.0,      -16.0,     0.0,     0.0),
      (       -30.0,       0.0,      0.0,       15.0,     0.0,     0.0),
      (       -32.0,       0.0,      0.0,       16.0,     0.0,     0.0),
      (       -31.0,       0.0,      0.0,       13.0,     0.0,     0.0),
      (        37.0,       0.0,      0.0,      -16.0,     0.0,     0.0),
      (        31.0,       0.0,      0.0,      -13.0,     0.0,     0.0),
      (        49.0,       0.0,      0.0,       -2.0,     0.0,     0.0),
      (        32.0,       0.0,      0.0,      -13.0,     0.0,     0.0),
      (        23.0,       0.0,      0.0,      -12.0,     0.0,     0.0),
      (       -43.0,       0.0,      0.0,       18.0,     0.0,     0.0),
      (        26.0,       0.0,      0.0,      -11.0,     0.0,     0.0),
      (       -32.0,       0.0,      0.0,       14.0,     0.0,     0.0),
      (       -29.0,       0.0,      0.0,       14.0,     0.0,     0.0),
      (       -27.0,       0.0,      0.0,       12.0,     0.0,     0.0),
      (        30.0,       0.0,      0.0,        0.0,     0.0,     0.0),
      (       -11.0,       0.0,      0.0,        5.0,     0.0,     0.0),
      (       -21.0,       0.0,      0.0,       10.0,     0.0,     0.0),
      (       -34.0,       0.0,      0.0,       15.0,     0.0,     0.0),
      (       -10.0,       0.0,      0.0,        6.0,     0.0,     0.0),
      (       -36.0,       0.0,      0.0,        0.0,     0.0,     0.0),
      (        -9.0,       0.0,      0.0,        4.0,     0.0,     0.0),
      (       -12.0,       0.0,      0.0,        5.0,     0.0,     0.0),
      (       -21.0,       0.0,      0.0,        5.0,     0.0,     0.0),
      (       -29.0,       0.0,      0.0,       -1.0,     0.0,     0.0),
      (       -15.0,       0.0,      0.0,        3.0,     0.0,     0.0),
      (       -20.0,       0.0,      0.0,        0.0,     0.0,     0.0),
      (        28.0,       0.0,      0.0,        0.0,     0.0,    -2.0),
      (        17.0,       0.0,      0.0,        0.0,     0.0,     0.0),
      (       -22.0,       0.0,      0.0,       12.0,     0.0,     0.0),
      (       -14.0,       0.0,      0.0,        7.0,     0.0,     0.0),
      (        24.0,       0.0,      0.0,      -11.0,     0.0,     0.0),
      (        11.0,       0.0,      0.0,       -6.0,     0.0,     0.0),
      (        14.0,       0.0,      0.0,       -6.0,     0.0,     0.0),
      (        24.0,       0.0,      0.0,        0.0,     0.0,     0.0),
      (        18.0,       0.0,      0.0,       -8.0,     0.0,     0.0),
      (       -38.0,       0.0,      0.0,        0.0,     0.0,     0.0),
      (       -31.0,       0.0,      0.0,        0.0,     0.0,     0.0),
      (       -16.0,       0.0,      0.0,        8.0,     0.0,     0.0),
      (        29.0,       0.0,      0.0,        0.0,     0.0,     0.0),
      (       -18.0,       0.0,      0.0,       10.0,     0.0,     0.0),
      (       -10.0,       0.0,      0.0,        5.0,     0.0,     0.0),
      (       -17.0,       0.0,      0.0,       10.0,     0.0,     0.0),
      (         9.0,       0.0,      0.0,       -4.0,     0.0,     0.0),
      (        16.0,       0.0,      0.0,       -6.0,     0.0,     0.0),
      (        22.0,       0.0,      0.0,      -12.0,     0.0,     0.0),
      (        20.0,       0.0,      0.0,        0.0,     0.0,     0.0),
      (       -13.0,       0.0,      0.0,        6.0,     0.0,     0.0),
      (       -17.0,       0.0,      0.0,        9.0,     0.0,     0.0),
      (       -14.0,       0.0,      0.0,        8.0,     0.0,     0.0),
      (         0.0,       0.0,      0.0,       -7.0,     0.0,     0.0),
      (        14.0,       0.0,      0.0,        0.0,     0.0,     0.0),
      (        19.0,       0.0,      0.0,      -10.0,     0.0,     0.0),
      (       -34.0,       0.0,      0.0,        0.0,     0.0,     0.0),
      (       -20.0,       0.0,      0.0,        8.0,     0.0,     0.0),
      (         9.0,       0.0,      0.0,       -5.0,     0.0,     0.0),
      (       -18.0,       0.0,      0.0,        7.0,     0.0,     0.0),
      (        13.0,       0.0,      0.0,       -6.0,     0.0,     0.0),
      (        17.0,       0.0,      0.0,        0.0,     0.0,     0.0),
      (       -12.0,       0.0,      0.0,        5.0,     0.0,     0.0),
      (        15.0,       0.0,      0.0,       -8.0,     0.0,     0.0),
      (       -11.0,       0.0,      0.0,        3.0,     0.0,     0.0),
      (        13.0,       0.0,      0.0,       -5.0,     0.0,     0.0),
      (       -18.0,       0.0,      0.0,        0.0,     0.0,     0.0),
      (       -35.0,       0.0,      0.0,        0.0,     0.0,     0.0),
      (         9.0,       0.0,      0.0,       -4.0,     0.0,     0.0),
      (       -19.0,       0.0,      0.0,       10.0,     0.0,     0.0),
      (       -26.0,       0.0,      0.0,       11.0,     0.0,     0.0),
      (         8.0,       0.0,      0.0,       -4.0,     0.0,     0.0),
      (       -10.0,       0.0,      0.0,        4.0,     0.0,     0.0),
      (        10.0,       0.0,      0.0,       -6.0,     0.0,     0.0),
      (       -21.0,       0.0,      0.0,        9.0,     0.0,     0.0),
      (       -15.0,       0.0,      0.0,        0.0,     0.0,     0.0),
      (         9.0,       0.0,      0.0,       -5.0,     0.0,     0.0),
      (       -29.0,       0.0,      0.0,        0.0,     0.0,     0.0),
      (       -19.0,       0.0,      0.0,       10.0,     0.0,     0.0),
      (        12.0,       0.0,      0.0,       -5.0,     0.0,     0.0),
      (        22.0,       0.0,      0.0,       -9.0,     0.0,     0.0),
      (       -10.0,       0.0,      0.0,        5.0,     0.0,     0.0),
      (       -20.0,       0.0,      0.0,       11.0,     0.0,     0.0),
      (       -20.0,       0.0,      0.0,        0.0,     0.0,     0.0),
      (       -17.0,       0.0,      0.0,        7.0,     0.0,     0.0),
      (        15.0,       0.0,      0.0,       -3.0,     0.0,     0.0),
      (         8.0,       0.0,      0.0,       -4.0,     0.0,     0.0),
      (        14.0,       0.0,      0.0,        0.0,     0.0,     0.0),
      (       -12.0,       0.0,      0.0,        6.0,     0.0,     0.0),
      (        25.0,       0.0,      0.0,        0.0,     0.0,     0.0),
      (       -13.0,       0.0,      0.0,        6.0,     0.0,     0.0),
      (       -14.0,       0.0,      0.0,        8.0,     0.0,     0.0),
      (        13.0,       0.0,      0.0,       -5.0,     0.0,     0.0),
      (       -17.0,       0.0,      0.0,        9.0,     0.0,     0.0),
      (       -12.0,       0.0,      0.0,        6.0,     0.0,     0.0),
      (       -10.0,       0.0,      0.0,        5.0,     0.0,     0.0),
      (        10.0,       0.0,      0.0,       -6.0,     0.0,     0.0),
      (       -15.0,       0.0,      0.0,        0.0,     0.0,     0.0),
      (       -22.0,       0.0,      0.0,        0.0,     0.0,     0.0),
      (        28.0,       0.0,      0.0,       -1.0,     0.0,     0.0),
      (        15.0,       0.0,      0.0,       -7.0,     0.0,     0.0),
      (        23.0,       0.0,      0.0,      -10.0,     0.0,     0.0),
      (        12.0,       0.0,      0.0,       -5.0,     0.0,     0.0),
      (        29.0,       0.0,      0.0,       -1.0,     0.0,     0.0),
      (       -25.0,       0.0,      0.0,        1.0,     0.0,     0.0),
      (        22.0,       0.0,      0.0,        0.0,     0.0,     0.0),
      (       -18.0,       0.0,      0.0,        0.0,     0.0,     0.0),
      (        15.0,       0.0,      0.0,        3.0,     0.0,     0.0),
      (       -23.0,       0.0,      0.0,        0.0,     0.0,     0.0),
      (        12.0,       0.0,      0.0,       -5.0,     0.0,     0.0),
      (        -8.0,       0.0,      0.0,        4.0,     0.0,     0.0),
      (       -19.0,       0.0,      0.0,        0.0,     0.0,     0.0),
      (       -10.0,       0.0,      0.0,        4.0,     0.0,     0.0),
      (        21.0,       0.0,      0.0,       -9.0,     0.0,     0.0),
      (        23.0,       0.0,      0.0,       -1.0,     0.0,     0.0),
      (       -16.0,       0.0,      0.0,        8.0,     0.0,     0.0),
      (       -19.0,       0.0,      0.0,        9.0,     0.0,     0.0),
      (       -22.0,       0.0,      0.0,       10.0,     0.0,     0.0),
      (        27.0,       0.0,      0.0,       -1.0,     0.0,     0.0),
      (        16.0,       0.0,      0.0,       -8.0,     0.0,     0.0),
      (        19.0,       0.0,      0.0,       -8.0,     0.0,     0.0),
      (         9.0,       0.0,      0.0,       -4.0,     0.0,     0.0),
      (        -9.0,       0.0,      0.0,        4.0,     0.0,     0.0),
      (        -9.0,       0.0,      0.0,        4.0,     0.0,     0.0),
      (        -8.0,       0.0,      0.0,        4.0,     0.0,     0.0),
      (        18.0,       0.0,      0.0,       -9.0,     0.0,     0.0),
      (        16.0,       0.0,      0.0,       -1.0,     0.0,     0.0),
      (       -10.0,       0.0,      0.0,        4.0,     0.0,     0.0),
      (       -23.0,       0.0,      0.0,        9.0,     0.0,     0.0),
      (        16.0,       0.0,      0.0,       -1.0,     0.0,     0.0),
      (       -12.0,       0.0,      0.0,        6.0,     0.0,     0.0),
      (        -8.0,       0.0,      0.0,        4.0,     0.0,     0.0),
      (        30.0,       0.0,      0.0,       -2.0,     0.0,     0.0),
      (        24.0,       0.0,      0.0,      -10.0,     0.0,     0.0),
      (        10.0,       0.0,      0.0,       -4.0,     0.0,     0.0),
      (       -16.0,       0.0,      0.0,        7.0,     0.0,     0.0),
      (       -16.0,       0.0,      0.0,        7.0,     0.0,     0.0),
      (        17.0,       0.0,      0.0,       -7.0,     0.0,     0.0),
      (       -24.0,       0.0,      0.0,       10.0,     0.0,     0.0),
      (       -12.0,       0.0,      0.0,        5.0,     0.0,     0.0),
      (       -24.0,       0.0,      0.0,       11.0,     0.0,     0.0),
      (       -23.0,       0.0,      0.0,        9.0,     0.0,     0.0),
      (       -13.0,       0.0,      0.0,        5.0,     0.0,     0.0),
      (       -15.0,       0.0,      0.0,        7.0,     0.0,     0.0),
      (         0.0,       0.0,  -1988.0,        0.0,     0.0, -1679.0),
      (         0.0,       0.0,    -63.0,        0.0,     0.0,   -27.0),
      (        -4.0,       0.0,      0.0,        0.0,     0.0,     0.0),
      (         0.0,       0.0,      5.0,        0.0,     0.0,     4.0),
      (         5.0,       0.0,      0.0,       -3.0,     0.0,     0.0),
      (         0.0,       0.0,    364.0,        0.0,     0.0,   176.0),
      (         0.0,       0.0,  -1044.0,        0.0,     0.0,  -891.0),
      (        -3.0,       0.0,      0.0,        1.0,     0.0,     0.0),
      (         4.0,       0.0,      0.0,       -2.0,     0.0,     0.0),
      (         0.0,       0.0,    330.0,        0.0,     0.0,     0.0),
      (         5.0,       0.0,      0.0,       -2.0,     0.0,     0.0),
      (         3.0,       0.0,      0.0,       -2.0,     0.0,     0.0),
      (        -3.0,       0.0,      0.0,        1.0,     0.0,     0.0),
      (        -5.0,       0.0,      0.0,        2.0,     0.0,     0.0),
      (         3.0,       0.0,      0.0,       -1.0,     0.0,     0.0),
      (         3.0,       0.0,      0.0,        0.0,     0.0,     0.0),
      (         3.0,       0.0,      0.0,        0.0,     0.0,     0.0),
      (         0.0,       0.0,      5.0,        0.0,     0.0,     0.0),
      (         0.0,       0.0,      0.0,        1.0,     0.0,     0.0),
      (         4.0,       0.0,      0.0,       -2.0,     0.0,     0.0),
      (         6.0,       0.0,      0.0,        0.0,     0.0,     0.0),
      (         5.0,       0.0,      0.0,       -2.0,     0.0,     0.0),
      (        -7.0,       0.0,      0.0,        0.0,     0.0,     0.0),
      (       -12.0,       0.0,      0.0,        0.0,     0.0,     0.0),
      (         5.0,       0.0,      0.0,       -3.0,     0.0,     0.0),
      (         3.0,       0.0,      0.0,       -1.0,     0.0,     0.0),
      (        -5.0,       0.0,      0.0,        0.0,     0.0,     0.0),
      (         3.0,       0.0,      0.0,        0.0,     0.0,     0.0),
      (        -7.0,       0.0,      0.0,        3.0,     0.0,     0.0),
      (         7.0,       0.0,      0.0,       -4.0,     0.0,     0.0),
      (         0.0,       0.0,    -12.0,        0.0,     0.0,   -10.0),
      (         4.0,       0.0,      0.0,       -2.0,     0.0,     0.0),
      (         3.0,       0.0,      0.0,       -2.0,     0.0,     0.0),
      (        -3.0,       0.0,      0.0,        2.0,     0.0,     0.0),
      (        -7.0,       0.0,      0.0,        3.0,     0.0,     0.0),
      (        -4.0,       0.0,      0.0,        2.0,     0.0,     0.0),
      (        -3.0,       0.0,      0.0,        1.0,     0.0,     0.0),
      (         0.0,       0.0,      0.0,        0.0,     0.0,     0.0),
      (        -3.0,       0.0,      0.0,        1.0,     0.0,     0.0),
      (         7.0,       0.0,      0.0,       -3.0,     0.0,     0.0),
      (        -4.0,       0.0,      0.0,        2.0,     0.0,     0.0),
      (         4.0,       0.0,      0.0,       -2.0,     0.0,     0.0),
      (        -5.0,       0.0,      0.0,        3.0,     0.0,     0.0),
      (         5.0,       0.0,      0.0,        0.0,     0.0,     0.0),
      (        -5.0,       0.0,      0.0,        2.0,     0.0,     0.0),
      (         5.0,       0.0,      0.0,       -2.0,     0.0,     0.0),
      (        -8.0,       0.0,      0.0,        3.0,     0.0,     0.0),
      (         9.0,       0.0,      0.0,        0.0,     0.0,     0.0),
      (         6.0,       0.0,      0.0,       -3.0,     0.0,     0.0),
      (        -5.0,       0.0,      0.0,        2.0,     0.0,     0.0),
      (         3.0,       0.0,      0.0,        0.0,     0.0,     0.0),
      (        -7.0,       0.0,      0.0,        0.0,     0.0,     0.0),
      (        -3.0,       0.0,      0.0,        1.0,     0.0,     0.0),
      (         5.0,       0.0,      0.0,        0.0,     0.0,     0.0),
      (         3.0,       0.0,      0.0,        0.0,     0.0,     0.0),
      (        -3.0,       0.0,      0.0,        2.0,     0.0,     0.0),
      (         4.0,       0.0,      0.0,       -2.0,     0.0,     0.0),
      (         3.0,       0.0,      0.0,       -1.0,     0.0,     0.0),
      (        -5.0,       0.0,      0.0,        2.0,     0.0,     0.0),
      (         4.0,       0.0,      0.0,       -2.0,     0.0,     0.0),
      (         9.0,       0.0,      0.0,       -3.0,     0.0,     0.0),
      (         4.0,       0.0,      0.0,        0.0,     0.0,     0.0),
      (         4.0,       0.0,      0.0,       -2.0,     0.0,     0.0),
      (        -3.0,       0.0,      0.0,        2.0,     0.0,     0.0),
      (        -4.0,       0.0,      0.0,        2.0,     0.0,     0.0),
      (         9.0,       0.0,      0.0,       -3.0,     0.0,     0.0),
      (        -4.0,       0.0,      0.0,        0.0,     0.0,     0.0),
      (        -4.0,       0.0,      0.0,        0.0,     0.0,     0.0),
      (         3.0,       0.0,      0.0,       -2.0,     0.0,     0.0),
      (         8.0,       0.0,      0.0,        0.0,     0.0,     0.0),
      (         3.0,       0.0,      0.0,        0.0,     0.0,     0.0),
      (        -3.0,       0.0,      0.0,        2.0,     0.0,     0.0),
      (         3.0,       0.0,      0.0,       -1.0,     0.0,     0.0),
      (         3.0,       0.0,      0.0,       -1.0,     0.0,     0.0),
      (        -3.0,       0.0,      0.0,        1.0,     0.0,     0.0),
      (         6.0,       0.0,      0.0,       -3.0,     0.0,     0.0),
      (         3.0,       0.0,      0.0,        0.0,     0.0,     0.0),
      (        -3.0,       0.0,      0.0,        1.0,     0.0,     0.0),
      (        -7.0,       0.0,      0.0,        0.0,     0.0,     0.0),
      (         9.0,       0.0,      0.0,        0.0,     0.0,     0.0),
      (        -3.0,       0.0,      0.0,        2.0,     0.0,     0.0),
      (        -3.0,       0.0,      0.0,        0.0,     0.0,     0.0),
      (        -4.0,       0.0,      0.0,        0.0,     0.0,     0.0),
      (        -5.0,       0.0,      0.0,        3.0,     0.0,     0.0),
      (       -13.0,       0.0,      0.0,        0.0,     0.0,     0.0),
      (        -7.0,       0.0,      0.0,        0.0,     0.0,     0.0),
      (        10.0,       0.0,      0.0,        0.0,     0.0,     0.0),
      (         3.0,       0.0,      0.0,       -1.0,     0.0,     0.0),
      (        10.0,       0.0,     13.0,        6.0,     0.0,    -5.0),
      (         0.0,       0.0,     30.0,        0.0,     0.0,    14.0),
      (         0.0,       0.0,   -162.0,        0.0,     0.0,  -138.0),
      (         0.0,       0.0,     75.0,        0.0,     0.0,     0.0),
      (        -7.0,       0.0,      0.0,        4.0,     0.0,     0.0),
      (        -4.0,       0.0,      0.0,        2.0,     0.0,     0.0),
      (         4.0,       0.0,      0.0,       -2.0,     0.0,     0.0),
      (         5.0,       0.0,      0.0,       -2.0,     0.0,     0.0),
      (         5.0,       0.0,      0.0,       -3.0,     0.0,     0.0),
      (        -3.0,       0.0,      0.0,        0.0,     0.0,     0.0),
      (        -3.0,       0.0,      0.0,        2.0,     0.0,     0.0),
      (        -4.0,       0.0,      0.0,        2.0,     0.0,     0.0),
      (        -5.0,       0.0,      0.0,        2.0,     0.0,     0.0),
      (         6.0,       0.0,      0.0,        0.0,     0.0,     0.0),
      (         9.0,       0.0,      0.0,        0.0,     0.0,     0.0),
      (         5.0,       0.0,      0.0,        0.0,     0.0,     0.0),
      (        -7.0,       0.0,      0.0,        0.0,     0.0,     0.0),
      (        -3.0,       0.0,      0.0,        1.0,     0.0,     0.0),
      (        -4.0,       0.0,      0.0,        2.0,     0.0,     0.0),
      (         7.0,       0.0,      0.0,        0.0,     0.0,     0.0),
      (        -4.0,       0.0,      0.0,        0.0,     0.0,     0.0),
      (         4.0,       0.0,      0.0,        0.0,     0.0,     0.0),
      (        -6.0,       0.0,     -3.0,        3.0,     0.0,     1.0),
      (         0.0,       0.0,     -3.0,        0.0,     0.0,    -2.0),
      (        11.0,       0.0,      0.0,        0.0,     0.0,     0.0),
      (         3.0,       0.0,      0.0,       -1.0,     0.0,     0.0),
      (        11.0,       0.0,      0.0,        0.0,     0.0,     0.0),
      (        -3.0,       0.0,      0.0,        2.0,     0.0,     0.0),
      (        -1.0,       0.0,      3.0,        3.0,     0.0,    -1.0),
      (         4.0,       0.0,      0.0,       -2.0,     0.0,     0.0),
      (         0.0,       0.0,    -13.0,        0.0,     0.0,   -11.0),
      (         3.0,       0.0,      6.0,        0.0,     0.0,     0.0),
      (        -7.0,       0.0,      0.0,        0.0,     0.0,     0.0),
      (         5.0,       0.0,      0.0,       -3.0,     0.0,     0.0),
      (        -3.0,       0.0,      0.0,        1.0,     0.0,     0.0),
      (         3.0,       0.0,      0.0,        0.0,     0.0,     0.0),
      (         5.0,       0.0,      0.0,       -3.0,     0.0,     0.0),
      (        -7.0,       0.0,      0.0,        3.0,     0.0,     0.0),
      (         8.0,       0.0,      0.0,       -3.0,     0.0,     0.0),
      (        -4.0,       0.0,      0.0,        2.0,     0.0,     0.0),
      (        11.0,       0.0,      0.0,        0.0,     0.0,     0.0),
      (        -3.0,       0.0,      0.0,        1.0,     0.0,     0.0),
      (         3.0,       0.0,      0.0,       -1.0,     0.0,     0.0),
      (        -4.0,       0.0,      0.0,        2.0,     0.0,     0.0),
      (         8.0,       0.0,      0.0,       -4.0,     0.0,     0.0),
      (         3.0,       0.0,      0.0,       -1.0,     0.0,     0.0),
      (        11.0,       0.0,      0.0,        0.0,     0.0,     0.0),
      (        -6.0,       0.0,      0.0,        3.0,     0.0,     0.0),
      (        -4.0,       0.0,      0.0,        2.0,     0.0,     0.0),
      (        -8.0,       0.0,      0.0,        4.0,     0.0,     0.0),
      (        -7.0,       0.0,      0.0,        3.0,     0.0,     0.0),
      (        -4.0,       0.0,      0.0,        2.0,     0.0,     0.0),
      (         3.0,       0.0,      0.0,       -1.0,     0.0,     0.0),
      (         6.0,       0.0,      0.0,       -3.0,     0.0,     0.0),
      (        -6.0,       0.0,      0.0,        3.0,     0.0,     0.0),
      (         6.0,       0.0,      0.0,        0.0,     0.0,     0.0),
      (         6.0,       0.0,      0.0,       -1.0,     0.0,     0.0),
      (         5.0,       0.0,      0.0,       -2.0,     0.0,     0.0),
      (        -5.0,       0.0,      0.0,        2.0,     0.0,     0.0),
      (        -4.0,       0.0,      0.0,        0.0,     0.0,     0.0),
      (        -4.0,       0.0,      0.0,        2.0,     0.0,     0.0),
      (         4.0,       0.0,      0.0,        0.0,     0.0,     0.0),
      (         6.0,       0.0,      0.0,       -3.0,     0.0,     0.0),
      (        -4.0,       0.0,      0.0,        2.0,     0.0,     0.0),
      (         0.0,       0.0,    -26.0,        0.0,     0.0,   -11.0),
      (         0.0,       0.0,    -10.0,        0.0,     0.0,    -5.0),
      (         5.0,       0.0,      0.0,       -3.0,     0.0,     0.0),
      (       -13.0,       0.0,      0.0,        0.0,     0.0,     0.0),
      (         3.0,       0.0,      0.0,       -2.0,     0.0,     0.0),
      (         4.0,       0.0,      0.0,       -2.0,     0.0,     0.0),
      (         7.0,       0.0,      0.0,       -3.0,     0.0,     0.0),
      (         4.0,       0.0,      0.0,        0.0,     0.0,     0.0),
      (         5.0,       0.0,      0.0,        0.0,     0.0,     0.0),
      (        -3.0,       0.0,      0.0,        2.0,     0.0,     0.0),
      (        -6.0,       0.0,      0.0,        2.0,     0.0,     0.0),
      (        -5.0,       0.0,      0.0,        2.0,     0.0,     0.0),
      (        -7.0,       0.0,      0.0,        3.0,     0.0,     0.0),
      (         5.0,       0.0,      0.0,       -2.0,     0.0,     0.0),
      (        13.0,       0.0,      0.0,        0.0,     0.0,     0.0),
      (        -4.0,       0.0,      0.0,        2.0,     0.0,     0.0),
      (        -3.0,       0.0,      0.0,        0.0,     0.0,     0.0),
      (         5.0,       0.0,      0.0,       -2.0,     0.0,     0.0),
      (       -11.0,       0.0,      0.0,        0.0,     0.0,     0.0),
      (         5.0,       0.0,      0.0,       -2.0,     0.0,     0.0),
      (         4.0,       0.0,      0.0,        0.0,     0.0,     0.0),
      (         4.0,       0.0,      0.0,       -2.0,     0.0,     0.0),
      (        -4.0,       0.0,      0.0,        2.0,     0.0,     0.0),
      (         6.0,       0.0,      0.0,       -3.0,     0.0,     0.0),
      (         3.0,       0.0,      0.0,       -2.0,     0.0,     0.0),
      (       -12.0,       0.0,      0.0,        0.0,     0.0,     0.0),
      (         4.0,       0.0,      0.0,        0.0,     0.0,     0.0),
      (        -3.0,       0.0,      0.0,        0.0,     0.0,     0.0),
      (        -4.0,       0.0,      0.0,        0.0,     0.0,     0.0),
      (         3.0,       0.0,      0.0,        0.0,     0.0,     0.0),
      (         3.0,       0.0,      0.0,       -1.0,     0.0,     0.0),
      (        -3.0,       0.0,      0.0,        1.0,     0.0,     0.0),
      (         0.0,       0.0,     -5.0,        0.0,     0.0,    -2.0),
      (        -7.0,       0.0,      0.0,        4.0,     0.0,     0.0),
      (         6.0,       0.0,      0.0,       -3.0,     0.0,     0.0),
      (        -3.0,       0.0,      0.0,        0.0,     0.0,     0.0),
      (         5.0,       0.0,      0.0,       -3.0,     0.0,     0.0),
      (         3.0,       0.0,      0.0,       -1.0,     0.0,     0.0),
      (         3.0,       0.0,      0.0,        0.0,     0.0,     0.0),
      (        -3.0,       0.0,      0.0,        1.0,     0.0,     0.0),
      (        -5.0,       0.0,      0.0,        3.0,     0.0,     0.0),
      (        -3.0,       0.0,      0.0,        2.0,     0.0,     0.0),
      (        -3.0,       0.0,      0.0,        2.0,     0.0,     0.0),
      (        12.0,       0.0,      0.0,        0.0,     0.0,     0.0),
      (         3.0,       0.0,      0.0,       -1.0,     0.0,     0.0),
      (        -4.0,       0.0,      0.0,        2.0,     0.0,     0.0),
      (         4.0,       0.0,      0.0,        0.0,     0.0,     0.0),
      (         6.0,       0.0,      0.0,        0.0,     0.0,     0.0),
      (         5.0,       0.0,      0.0,       -3.0,     0.0,     0.0),
      (         4.0,       0.0,      0.0,       -2.0,     0.0,     0.0),
      (        -6.0,       0.0,      0.0,        3.0,     0.0,     0.0),
      (         4.0,       0.0,      0.0,       -2.0,     0.0,     0.0),
      (         6.0,       0.0,      0.0,       -3.0,     0.0,     0.0),
      (         6.0,       0.0,      0.0,        0.0,     0.0,     0.0),
      (        -6.0,       0.0,      0.0,        3.0,     0.0,     0.0),
      (         3.0,       0.0,      0.0,       -2.0,     0.0,     0.0),
      (         7.0,       0.0,      0.0,       -4.0,     0.0,     0.0),
      (         4.0,       0.0,      0.0,       -2.0,     0.0,     0.0),
      (        -5.0,       0.0,      0.0,        2.0,     0.0,     0.0),
      (         5.0,       0.0,      0.0,        0.0,     0.0,     0.0),
      (        -6.0,       0.0,      0.0,        3.0,     0.0,     0.0),
      (        -6.0,       0.0,      0.0,        3.0,     0.0,     0.0),
      (        -4.0,       0.0,      0.0,        2.0,     0.0,     0.0),
      (        10.0,       0.0,      0.0,        0.0,     0.0,     0.0),
      (        -4.0,       0.0,      0.0,        2.0,     0.0,     0.0),
      (         7.0,       0.0,      0.0,        0.0,     0.0,     0.0),
      (         7.0,       0.0,      0.0,       -3.0,     0.0,     0.0),
      (         4.0,       0.0,      0.0,        0.0,     0.0,     0.0),
      (        11.0,       0.0,      0.0,        0.0,     0.0,     0.0),
      (         5.0,       0.0,      0.0,       -2.0,     0.0,     0.0),
      (        -6.0,       0.0,      0.0,        2.0,     0.0,     0.0),
      (         4.0,       0.0,      0.0,       -2.0,     0.0,     0.0),
      (         3.0,       0.0,      0.0,       -2.0,     0.0,     0.0),
      (         5.0,       0.0,      0.0,       -2.0,     0.0,     0.0),
      (        -4.0,       0.0,      0.0,        2.0,     0.0,     0.0),
      (        -4.0,       0.0,      0.0,        2.0,     0.0,     0.0),
      (        -3.0,       0.0,      0.0,        2.0,     0.0,     0.0),
      (         4.0,       0.0,      0.0,       -2.0,     0.0,     0.0),
      (         3.0,       0.0,      0.0,       -1.0,     0.0,     0.0),
      (        -3.0,       0.0,      0.0,        1.0,     0.0,     0.0),
      (        -3.0,       0.0,      0.0,        1.0,     0.0,     0.0),
      (        -3.0,       0.0,      0.0,        2.0,     0.0,     0.0),
      ))

lunisolar_longitude_coefficients = lunisolar_coefficients[:,:3]
lunisolar_obliquity_coefficients = lunisolar_coefficients[:,3:]

# Planetary argument multipliers:
#      L   L'  F   D   Om  Me  Ve  E  Ma  Ju  Sa  Ur  Ne  pre

napl_t = array((
      ( 0,  0,  0,  0,  0,  0,  0,  8,-16,  4,  5,  0,  0,  0),
      ( 0,  0,  0,  0,  0,  0,  0, -8, 16, -4, -5,  0,  0,  2),
      ( 0,  0,  0,  0,  0,  0,  0,  8,-16,  4,  5,  0,  0,  2),
      ( 0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0, -1,  2,  2),
      ( 0,  0,  0,  0,  0,  0,  0, -4,  8, -1, -5,  0,  0,  2),
      ( 0,  0,  0,  0,  0,  0,  0,  4, -8,  3,  0,  0,  0,  1),
      ( 0,  0,  1, -1,  1,  0,  0,  3, -8,  3,  0,  0,  0,  0),
      (-1,  0,  0,  0,  0,  0, 10, -3,  0,  0,  0,  0,  0,  0),
      ( 0,  0,  0,  0,  0,  0,  0,  0,  0, -2,  6, -3,  0,  2),
      ( 0,  0,  0,  0,  0,  0,  0,  4, -8,  3,  0,  0,  0,  0),
      ( 0,  0,  1, -1,  1,  0,  0, -5,  8, -3,  0,  0,  0,  0),
      ( 0,  0,  0,  0,  0,  0,  0, -4,  8, -3,  0,  0,  0,  1),
      ( 0,  0,  0,  0,  0,  0,  0,  4, -8,  1,  5,  0,  0,  2),
      ( 0,  0,  0,  0,  0,  0, -5,  6,  4,  0,  0,  0,  0,  2),
      ( 0,  0,  0,  0,  0,  0,  0,  0,  0,  2, -5,  0,  0,  2),
      ( 0,  0,  0,  0,  0,  0,  0,  0,  0,  2, -5,  0,  0,  1),
      ( 0,  0,  1, -1,  1,  0,  0, -1,  0,  2, -5,  0,  0,  0),
      ( 0,  0,  0,  0,  0,  0,  0,  0,  0,  2, -5,  0,  0,  0),
      ( 0,  0,  1, -1,  1,  0,  0, -1,  0, -2,  5,  0,  0,  0),
      ( 0,  0,  0,  0,  0,  0,  0,  0,  0, -2,  5,  0,  0,  1),
      ( 0,  0,  0,  0,  0,  0,  0,  0,  0, -2,  5,  0,  0,  2),
      ( 2,  0, -1, -1,  0,  0,  0,  3, -7,  0,  0,  0,  0,  0),
      ( 1,  0,  0, -2,  0,  0, 19,-21,  3,  0,  0,  0,  0,  0),
      ( 0,  0,  1, -1,  1,  0,  2, -4,  0, -3,  0,  0,  0,  0),
      ( 1,  0,  0, -1,  1,  0,  0, -1,  0,  2,  0,  0,  0,  0),
      ( 0,  0,  1, -1,  1,  0,  0, -1,  0, -4, 10,  0,  0,  0),
      (-2,  0,  0,  2,  1,  0,  0,  2,  0,  0, -5,  0,  0,  0),
      ( 0,  0,  0,  0,  0,  0,  3, -7,  4,  0,  0,  0,  0,  0),
      ( 0,  0, -1,  1,  0,  0,  0,  1,  0,  1, -1,  0,  0,  0),
      (-2,  0,  0,  2,  1,  0,  0,  2,  0, -2,  0,  0,  0,  0),
      (-1,  0,  0,  0,  0,  0, 18,-16,  0,  0,  0,  0,  0,  0),
      (-2,  0,  1,  1,  2,  0,  0,  1,  0, -2,  0,  0,  0,  0),
      (-1,  0,  1, -1,  1,  0, 18,-17,  0,  0,  0,  0,  0,  0),
      (-1,  0,  0,  1,  1,  0,  0,  2, -2,  0,  0,  0,  0,  0),
      ( 0,  0,  0,  0,  0,  0, -8, 13,  0,  0,  0,  0,  0,  2),
      ( 0,  0,  2, -2,  2,  0, -8, 11,  0,  0,  0,  0,  0,  0),
      ( 0,  0,  0,  0,  0,  0, -8, 13,  0,  0,  0,  0,  0,  1),
      ( 0,  0,  1, -1,  1,  0, -8, 12,  0,  0,  0,  0,  0,  0),
      ( 0,  0,  0,  0,  0,  0,  8,-13,  0,  0,  0,  0,  0,  0),
      ( 0,  0,  1, -1,  1,  0,  8,-14,  0,  0,  0,  0,  0,  0),
      ( 0,  0,  0,  0,  0,  0,  8,-13,  0,  0,  0,  0,  0,  1),
      (-2,  0,  0,  2,  1,  0,  0,  2,  0, -4,  5,  0,  0,  0),
      (-2,  0,  0,  2,  2,  0,  3, -3,  0,  0,  0,  0,  0,  0),
      (-2,  0,  0,  2,  0,  0,  0,  2,  0, -3,  1,  0,  0,  0),
      ( 0,  0,  0,  0,  1,  0,  3, -5,  0,  2,  0,  0,  0,  0),
      (-2,  0,  0,  2,  0,  0,  0,  2,  0, -4,  3,  0,  0,  0),
      ( 0,  0, -1,  1,  0,  0,  0,  0,  2,  0,  0,  0,  0,  0),
      ( 0,  0,  0,  0,  1,  0,  0, -1,  2,  0,  0,  0,  0,  0),
      ( 0,  0,  1, -1,  2,  0,  0, -2,  2,  0,  0,  0,  0,  0),
      (-1,  0,  1,  0,  1,  0,  3, -5,  0,  0,  0,  0,  0,  0),
      (-1,  0,  0,  1,  0,  0,  3, -4,  0,  0,  0,  0,  0,  0),
      (-2,  0,  0,  2,  0,  0,  0,  2,  0, -2, -2,  0,  0,  0),
      (-2,  0,  2,  0,  2,  0,  0, -5,  9,  0,  0,  0,  0,  0),
      ( 0,  0,  1, -1,  1,  0,  0, -1,  0,  0,  0, -1,  0,  0),
      ( 0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  1,  0,  0),
      ( 0,  0,  1, -1,  1,  0,  0, -1,  0,  0,  0,  0,  2,  0),
      ( 0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  2,  1),
      ( 0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  2,  2),
      (-1,  0,  0,  1,  0,  0,  0,  3, -4,  0,  0,  0,  0,  0),
      ( 0,  0, -1,  1,  0,  0,  0,  1,  0,  0,  2,  0,  0,  0),
      ( 0,  0,  1, -1,  2,  0,  0, -1,  0,  0,  2,  0,  0,  0),
      ( 0,  0,  0,  0,  1,  0,  0, -9, 17,  0,  0,  0,  0,  0),
      ( 0,  0,  0,  0,  2,  0, -3,  5,  0,  0,  0,  0,  0,  0),
      ( 0,  0,  1, -1,  1,  0,  0, -1,  0, -1,  2,  0,  0,  0),
      ( 0,  0,  0,  0,  0,  0,  0,  0,  0,  1, -2,  0,  0,  0),
      ( 1,  0,  0, -2,  0,  0, 17,-16,  0, -2,  0,  0,  0,  0),
      ( 0,  0,  1, -1,  1,  0,  0, -1,  0,  1, -3,  0,  0,  0),
      (-2,  0,  0,  2,  1,  0,  0,  5, -6,  0,  0,  0,  0,  0),
      ( 0,  0, -2,  2,  0,  0,  0,  9,-13,  0,  0,  0,  0,  0),
      ( 0,  0,  1, -1,  2,  0,  0, -1,  0,  0,  1,  0,  0,  0),
      ( 0,  0,  0,  0,  1,  0,  0,  0,  0,  0,  1,  0,  0,  0),
      ( 0,  0, -1,  1,  0,  0,  0,  1,  0,  0,  1,  0,  0,  0),
      ( 0,  0, -2,  2,  0,  0,  5, -6,  0,  0,  0,  0,  0,  0),
      ( 0,  0, -1,  1,  1,  0,  5, -7,  0,  0,  0,  0,  0,  0),
      (-2,  0,  0,  2,  0,  0,  6, -8,  0,  0,  0,  0,  0,  0),
      ( 2,  0,  1, -3,  1,  0, -6,  7,  0,  0,  0,  0,  0,  0),
      ( 0,  0,  0,  0,  2,  0,  0,  0,  0,  1,  0,  0,  0,  0),
      ( 0,  0, -1,  1,  1,  0,  0,  1,  0,  1,  0,  0,  0,  0),
      ( 0,  0,  1, -1,  1,  0,  0, -1,  0,  0,  0,  2,  0,  0),
      ( 0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  2,  0,  1),
      ( 0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  2,  0,  2),
      ( 0,  0,  0,  0,  0,  0,  0, -8, 15,  0,  0,  0,  0,  2),
      ( 0,  0,  0,  0,  0,  0,  0, -8, 15,  0,  0,  0,  0,  1),
      ( 0,  0,  1, -1,  1,  0,  0, -9, 15,  0,  0,  0,  0,  0),
      ( 0,  0,  0,  0,  0,  0,  0,  8,-15,  0,  0,  0,  0,  0),
      ( 1,  0, -1, -1,  0,  0,  0,  8,-15,  0,  0,  0,  0,  0),
      ( 2,  0,  0, -2,  0,  0,  2, -5,  0,  0,  0,  0,  0,  0),
      (-2,  0,  0,  2,  0,  0,  0,  2,  0, -5,  5,  0,  0,  0),
      ( 2,  0,  0, -2,  1,  0,  0, -6,  8,  0,  0,  0,  0,  0),
      ( 2,  0,  0, -2,  1,  0,  0, -2,  0,  3,  0,  0,  0,  0),
      (-2,  0,  1,  1,  0,  0,  0,  1,  0, -3,  0,  0,  0,  0),
      (-2,  0,  1,  1,  1,  0,  0,  1,  0, -3,  0,  0,  0,  0),
      (-2,  0,  0,  2,  0,  0,  0,  2,  0, -3,  0,  0,  0,  0),
      (-2,  0,  0,  2,  0,  0,  0,  6, -8,  0,  0,  0,  0,  0),
      (-2,  0,  0,  2,  0,  0,  0,  2,  0, -1, -5,  0,  0,  0),
      (-1,  0,  0,  1,  0,  0,  0,  1,  0, -1,  0,  0,  0,  0),
      (-1,  0,  1,  1,  1,  0,-20, 20,  0,  0,  0,  0,  0,  0),
      ( 1,  0,  0, -2,  0,  0, 20,-21,  0,  0,  0,  0,  0,  0),
      ( 0,  0,  0,  0,  1,  0,  0,  8,-15,  0,  0,  0,  0,  0),
      ( 0,  0,  2, -2,  1,  0,  0,-10, 15,  0,  0,  0,  0,  0),
      ( 0,  0, -1,  1,  0,  0,  0,  1,  0,  1,  0,  0,  0,  0),
      ( 0,  0,  0,  0,  1,  0,  0,  0,  0,  1,  0,  0,  0,  0),
      ( 0,  0,  1, -1,  2,  0,  0, -1,  0,  1,  0,  0,  0,  0),
      ( 0,  0,  1, -1,  1,  0,  0, -1,  0, -2,  4,  0,  0,  0),
      ( 2,  0,  0, -2,  1,  0, -6,  8,  0,  0,  0,  0,  0,  0),
      ( 0,  0, -2,  2,  1,  0,  5, -6,  0,  0,  0,  0,  0,  0),
      ( 0,  0,  0,  0,  0,  0,  0,  0,  0,  0, -1,  0,  0,  1),
      ( 0,  0,  1, -1,  1,  0,  0, -1,  0,  0, -1,  0,  0,  0),
      ( 0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  1,  0,  0,  0),
      ( 0,  0,  1, -1,  1,  0,  0, -1,  0,  0,  1,  0,  0,  0),
      ( 0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  1,  0,  0,  1),
      ( 0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  1,  0,  0,  2),
      ( 0,  0,  2, -2,  1,  0,  0, -9, 13,  0,  0,  0,  0,  0),
      ( 0,  0,  0,  0,  1,  0,  0,  7,-13,  0,  0,  0,  0,  0),
      (-2,  0,  0,  2,  0,  0,  0,  5, -6,  0,  0,  0,  0,  0),
      ( 0,  0,  0,  0,  0,  0,  0,  9,-17,  0,  0,  0,  0,  0),
      ( 0,  0,  0,  0,  0,  0,  0, -9, 17,  0,  0,  0,  0,  2),
      ( 1,  0,  0, -1,  1,  0,  0, -3,  4,  0,  0,  0,  0,  0),
      ( 1,  0,  0, -1,  1,  0, -3,  4,  0,  0,  0,  0,  0,  0),
      ( 0,  0,  0,  0,  2,  0,  0, -1,  2,  0,  0,  0,  0,  0),
      ( 0,  0, -1,  1,  1,  0,  0,  0,  2,  0,  0,  0,  0,  0),
      ( 0,  0, -2,  2,  0,  1,  0, -2,  0,  0,  0,  0,  0,  0),
      ( 0,  0,  0,  0,  0,  0,  3, -5,  0,  2,  0,  0,  0,  0),
      (-2,  0,  0,  2,  1,  0,  0,  2,  0, -3,  1,  0,  0,  0),
      (-2,  0,  0,  2,  1,  0,  3, -3,  0,  0,  0,  0,  0,  0),
      ( 0,  0,  0,  0,  1,  0,  8,-13,  0,  0,  0,  0,  0,  0),
      ( 0,  0, -1,  1,  0,  0,  8,-12,  0,  0,  0,  0,  0,  0),
      ( 0,  0,  2, -2,  1,  0, -8, 11,  0,  0,  0,  0,  0,  0),
      (-1,  0,  0,  1,  0,  0,  0,  2, -2,  0,  0,  0,  0,  0),
      (-1,  0,  0,  0,  1,  0, 18,-16,  0,  0,  0,  0,  0,  0),
      ( 0,  0,  1, -1,  1,  0,  0, -1,  0, -1,  1,  0,  0,  0),
      ( 0,  0,  0,  0,  1,  0,  3, -7,  4,  0,  0,  0,  0,  0),
      (-2,  0,  1,  1,  1,  0,  0, -3,  7,  0,  0,  0,  0,  0),
      ( 0,  0,  1, -1,  2,  0,  0, -1,  0, -2,  5,  0,  0,  0),
      ( 0,  0,  0,  0,  1,  0,  0,  0,  0, -2,  5,  0,  0,  0),
      ( 0,  0,  0,  0,  1,  0,  0, -4,  8, -3,  0,  0,  0,  0),
      ( 1,  0,  0,  0,  1,  0,-10,  3,  0,  0,  0,  0,  0,  0),
      ( 0,  0,  2, -2,  1,  0,  0, -2,  0,  0,  0,  0,  0,  0),
      (-1,  0,  0,  0,  1,  0, 10, -3,  0,  0,  0,  0,  0,  0),
      ( 0,  0,  0,  0,  1,  0,  0,  4, -8,  3,  0,  0,  0,  0),
      ( 0,  0,  0,  0,  1,  0,  0,  0,  0,  2, -5,  0,  0,  0),
      ( 0,  0, -1,  1,  0,  0,  0,  1,  0,  2, -5,  0,  0,  0),
      ( 2,  0, -1, -1,  1,  0,  0,  3, -7,  0,  0,  0,  0,  0),
      (-2,  0,  0,  2,  0,  0,  0,  2,  0,  0, -5,  0,  0,  0),
      ( 0,  0,  0,  0,  1,  0, -3,  7, -4,  0,  0,  0,  0,  0),
      (-2,  0,  0,  2,  0,  0,  0,  2,  0, -2,  0,  0,  0,  0),
      ( 1,  0,  0,  0,  1,  0,-18, 16,  0,  0,  0,  0,  0,  0),
      (-2,  0,  1,  1,  1,  0,  0,  1,  0, -2,  0,  0,  0,  0),
      ( 0,  0,  1, -1,  2,  0, -8, 12,  0,  0,  0,  0,  0,  0),
      ( 0,  0,  0,  0,  1,  0, -8, 13,  0,  0,  0,  0,  0,  0),
      ( 0,  0,  0,  0,  0,  0,  0,  1, -2,  0,  0,  0,  0,  1),
      ( 0,  0,  1, -1,  1,  0,  0,  0, -2,  0,  0,  0,  0,  0),
      ( 0,  0,  0,  0,  0,  0,  0,  1, -2,  0,  0,  0,  0,  0),
      ( 0,  0,  1, -1,  1,  0,  0, -2,  2,  0,  0,  0,  0,  0),
      ( 0,  0,  0,  0,  0,  0,  0, -1,  2,  0,  0,  0,  0,  1),
      (-1,  0,  0,  1,  1,  0,  3, -4,  0,  0,  0,  0,  0,  0),
      (-1,  0,  0,  1,  1,  0,  0,  3, -4,  0,  0,  0,  0,  0),
      ( 0,  0,  1, -1,  1,  0,  0, -1,  0,  0, -2,  0,  0,  0),
      ( 0,  0,  1, -1,  1,  0,  0, -1,  0,  0,  2,  0,  0,  0),
      ( 0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  2,  0,  0,  1),
      ( 0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  2,  0,  0,  2),
      ( 0,  0,  1, -1,  0,  0,  3, -6,  0,  0,  0,  0,  0,  0),
      ( 0,  0,  0,  0,  1,  0, -3,  5,  0,  0,  0,  0,  0,  0),
      ( 0,  0,  1, -1,  2,  0, -3,  4,  0,  0,  0,  0,  0,  0),
      ( 0,  0,  0,  0,  1,  0,  0, -2,  4,  0,  0,  0,  0,  0),
      ( 0,  0,  2, -2,  1,  0, -5,  6,  0,  0,  0,  0,  0,  0),
      ( 0,  0, -1,  1,  0,  0,  5, -7,  0,  0,  0,  0,  0,  0),
      ( 0,  0,  0,  0,  1,  0,  5, -8,  0,  0,  0,  0,  0,  0),
      (-2,  0,  0,  2,  1,  0,  6, -8,  0,  0,  0,  0,  0,  0),
      ( 0,  0,  0,  0,  1,  0,  0, -8, 15,  0,  0,  0,  0,  0),
      (-2,  0,  0,  2,  1,  0,  0,  2,  0, -3,  0,  0,  0,  0),
      (-2,  0,  0,  2,  1,  0,  0,  6, -8,  0,  0,  0,  0,  0),
      ( 1,  0,  0, -1,  1,  0,  0, -1,  0,  1,  0,  0,  0,  0),
      ( 0,  0,  0,  0,  0,  0,  0,  0,  0,  3, -5,  0,  0,  0),
      ( 0,  0,  1, -1,  1,  0,  0, -1,  0, -1,  0,  0,  0,  0),
      ( 0,  0,  0,  0,  0,  0,  0,  0,  0, -1,  0,  0,  0,  1),
      ( 0,  0,  0,  0,  0,  0,  0,  0,  0,  1,  0,  0,  0,  0),
      ( 0,  0,  0,  0,  0,  0,  0,  0,  0,  1,  0,  0,  0,  1),
      ( 0,  0,  1, -1,  1,  0,  0, -1,  0,  1,  0,  0,  0,  0),
      ( 0,  0,  0,  0,  0,  0,  0,  0,  0,  1,  0,  0,  0,  1),
      ( 0,  0,  0,  0,  0,  0,  0,  0,  0,  1,  0,  0,  0,  2),
      ( 0,  0,  1, -1,  2,  0,  0, -1,  0,  0, -1,  0,  0,  0),
      ( 0,  0,  0,  0,  1,  0,  0,  0,  0,  0, -1,  0,  0,  0),
      ( 0,  0, -1,  1,  0,  0,  0,  1,  0,  0, -1,  0,  0,  0),
      ( 0,  0,  0,  0,  0,  0,  0, -7, 13,  0,  0,  0,  0,  2),
      ( 0,  0,  0,  0,  0,  0,  0,  7,-13,  0,  0,  0,  0,  0),
      ( 2,  0,  0, -2,  1,  0,  0, -5,  6,  0,  0,  0,  0,  0),
      ( 0,  0,  2, -2,  1,  0,  0, -8, 11,  0,  0,  0,  0,  0),
      ( 0,  0,  2, -2,  1, -1,  0,  2,  0,  0,  0,  0,  0,  0),
      (-2,  0,  0,  2,  0,  0,  0,  4, -4,  0,  0,  0,  0,  0),
      ( 0,  0,  0,  0,  0,  0,  0,  0,  0,  2, -2,  0,  0,  0),
      ( 0,  0,  1, -1,  1,  0,  0, -1,  0,  0,  3,  0,  0,  0),
      ( 0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  3,  0,  0,  1),
      ( 0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  3,  0,  0,  2),
      (-2,  0,  0,  2,  0,  0,  3, -3,  0,  0,  0,  0,  0,  0),
      ( 0,  0,  0,  0,  2,  0,  0, -4,  8, -3,  0,  0,  0,  0),
      ( 0,  0,  0,  0,  2,  0,  0,  4, -8,  3,  0,  0,  0,  0),
      ( 2,  0,  0, -2,  1,  0,  0, -2,  0,  2,  0,  0,  0,  0),
      ( 0,  0,  1, -1,  2,  0,  0, -1,  0,  2,  0,  0,  0,  0),
      ( 0,  0,  1, -1,  2,  0,  0,  0, -2,  0,  0,  0,  0,  0),
      ( 0,  0,  0,  0,  1,  0,  0,  1, -2,  0,  0,  0,  0,  0),
      ( 0,  0, -1,  1,  0,  0,  0,  2, -2,  0,  0,  0,  0,  0),
      ( 0,  0, -1,  1,  0,  0,  0,  1,  0,  0, -2,  0,  0,  0),
      ( 0,  0,  2, -2,  1,  0,  0, -2,  0,  0,  2,  0,  0,  0),
      ( 0,  0,  1, -1,  1,  0,  3, -6,  0,  0,  0,  0,  0,  0),
      ( 0,  0,  0,  0,  0,  0,  3, -5,  0,  0,  0,  0,  0,  1),
      ( 0,  0,  0,  0,  0,  0,  3, -5,  0,  0,  0,  0,  0,  0),
      ( 0,  0,  1, -1,  1,  0, -3,  4,  0,  0,  0,  0,  0,  0),
      ( 0,  0,  0,  0,  0,  0, -3,  5,  0,  0,  0,  0,  0,  1),
      ( 0,  0,  0,  0,  0,  0, -3,  5,  0,  0,  0,  0,  0,  2),
      ( 0,  0,  2, -2,  2,  0, -3,  3,  0,  0,  0,  0,  0,  0),
      ( 0,  0,  0,  0,  0,  0, -3,  5,  0,  0,  0,  0,  0,  2),
      ( 0,  0,  0,  0,  0,  0,  0,  2, -4,  0,  0,  0,  0,  1),
      ( 0,  0,  1, -1,  1,  0,  0,  1, -4,  0,  0,  0,  0,  0),
      ( 0,  0,  0,  0,  0,  0,  0,  2, -4,  0,  0,  0,  0,  0),
      ( 0,  0,  0,  0,  0,  0,  0, -2,  4,  0,  0,  0,  0,  1),
      ( 0,  0,  1, -1,  1,  0,  0, -3,  4,  0,  0,  0,  0,  0),
      ( 0,  0,  0,  0,  0,  0,  0, -2,  4,  0,  0,  0,  0,  1),
      ( 0,  0,  0,  0,  0,  0,  0, -2,  4,  0,  0,  0,  0,  2),
      ( 0,  0,  0,  0,  0,  0, -5,  8,  0,  0,  0,  0,  0,  2),
      ( 0,  0,  2, -2,  2,  0, -5,  6,  0,  0,  0,  0,  0,  0),
      ( 0,  0,  0,  0,  0,  0, -5,  8,  0,  0,  0,  0,  0,  2),
      ( 0,  0,  0,  0,  0,  0, -5,  8,  0,  0,  0,  0,  0,  1),
      ( 0,  0,  1, -1,  1,  0, -5,  7,  0,  0,  0,  0,  0,  0),
      ( 0,  0,  0,  0,  0,  0, -5,  8,  0,  0,  0,  0,  0,  1),
      ( 0,  0,  0,  0,  0,  0,  5, -8,  0,  0,  0,  0,  0,  0),
      ( 0,  0,  1, -1,  2,  0,  0, -1,  0, -1,  0,  0,  0,  0),
      ( 0,  0,  0,  0,  1,  0,  0,  0,  0, -1,  0,  0,  0,  0),
      ( 0,  0, -1,  1,  0,  0,  0,  1,  0, -1,  0,  0,  0,  0),
      ( 0,  0,  2, -2,  1,  0,  0, -2,  0,  1,  0,  0,  0,  0),
      ( 0,  0,  0,  0,  0,  0,  0, -6, 11,  0,  0,  0,  0,  2),
      ( 0,  0,  0,  0,  0,  0,  0,  6,-11,  0,  0,  0,  0,  0),
      ( 0,  0,  0,  0,  0, -1,  0,  4,  0,  0,  0,  0,  0,  2),
      ( 0,  0,  0,  0,  0,  1,  0, -4,  0,  0,  0,  0,  0,  0),
      ( 2,  0,  0, -2,  1,  0, -3,  3,  0,  0,  0,  0,  0,  0),
      (-2,  0,  0,  2,  0,  0,  0,  2,  0,  0, -2,  0,  0,  0),
      ( 0,  0,  2, -2,  1,  0,  0, -7,  9,  0,  0,  0,  0,  0),
      ( 0,  0,  0,  0,  0,  0,  0,  0,  0,  4, -5,  0,  0,  2),
      ( 0,  0,  0,  0,  0,  0,  0,  0,  0,  2,  0,  0,  0,  0),
      ( 0,  0,  0,  0,  0,  0,  0,  0,  0,  2,  0,  0,  0,  1),
      ( 0,  0,  1, -1,  1,  0,  0, -1,  0,  2,  0,  0,  0,  0),
      ( 0,  0,  0,  0,  0,  0,  0,  0,  0,  2,  0,  0,  0,  1),
      ( 0,  0,  0,  0,  0,  0,  0,  0,  0,  2,  0,  0,  0,  2),
      ( 0,  0,  2, -2,  2,  0,  0, -2,  0,  2,  0,  0,  0,  0),
      ( 0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  5,  0,  0,  2),
      ( 0,  0,  0,  0,  1,  0,  3, -5,  0,  0,  0,  0,  0,  0),
      ( 0,  0, -1,  1,  0,  0,  3, -4,  0,  0,  0,  0,  0,  0),
      ( 0,  0,  2, -2,  1,  0, -3,  3,  0,  0,  0,  0,  0,  0),
      ( 0,  0,  0,  0,  1,  0,  0,  2, -4,  0,  0,  0,  0,  0),
      ( 0,  0,  2, -2,  1,  0,  0, -4,  4,  0,  0,  0,  0,  0),
      ( 0,  0,  1, -1,  2,  0, -5,  7,  0,  0,  0,  0,  0,  0),
      ( 0,  0,  0,  0,  0,  0,  0,  3, -6,  0,  0,  0,  0,  0),
      ( 0,  0,  0,  0,  0,  0,  0, -3,  6,  0,  0,  0,  0,  1),
      ( 0,  0,  1, -1,  1,  0,  0, -4,  6,  0,  0,  0,  0,  0),
      ( 0,  0,  0,  0,  0,  0,  0, -3,  6,  0,  0,  0,  0,  1),
      ( 0,  0,  0,  0,  0,  0,  0, -3,  6,  0,  0,  0,  0,  2),
      ( 0,  0, -1,  1,  0,  0,  2, -2,  0,  0,  0,  0,  0,  0),
      ( 0,  0,  0,  0,  1,  0,  2, -3,  0,  0,  0,  0,  0,  0),
      ( 0,  0,  0,  0,  0,  0,  0, -5,  9,  0,  0,  0,  0,  2),
      ( 0,  0,  0,  0,  0,  0,  0, -5,  9,  0,  0,  0,  0,  1),
      ( 0,  0,  0,  0,  0,  0,  0,  5, -9,  0,  0,  0,  0,  0),
      ( 0,  0, -1,  1,  0,  0,  0,  1,  0, -2,  0,  0,  0,  0),
      ( 0,  0,  2, -2,  1,  0,  0, -2,  0,  2,  0,  0,  0,  0),
      (-2,  0,  1,  1,  1,  0,  0,  1,  0,  0,  0,  0,  0,  0),
      ( 0,  0, -2,  2,  0,  0,  3, -3,  0,  0,  0,  0,  0,  0),
      ( 0,  0,  0,  0,  0,  0, -6, 10,  0,  0,  0,  0,  0,  1),
      ( 0,  0,  0,  0,  0,  0, -6, 10,  0,  0,  0,  0,  0,  2),
      ( 0,  0,  0,  0,  0,  0, -2,  3,  0,  0,  0,  0,  0,  2),
      ( 0,  0,  0,  0,  0,  0, -2,  3,  0,  0,  0,  0,  0,  1),
      ( 0,  0,  1, -1,  1,  0, -2,  2,  0,  0,  0,  0,  0,  0),
      ( 0,  0,  0,  0,  0,  0,  2, -3,  0,  0,  0,  0,  0,  0),
      ( 0,  0,  0,  0,  0,  0,  2, -3,  0,  0,  0,  0,  0,  1),
      ( 0,  0,  0,  0,  0,  0,  0,  0,  0,  3,  0,  0,  0,  1),
      ( 0,  0,  1, -1,  1,  0,  0, -1,  0,  3,  0,  0,  0,  0),
      ( 0,  0,  0,  0,  0,  0,  0,  0,  0,  3,  0,  0,  0,  1),
      ( 0,  0,  0,  0,  0,  0,  0,  0,  0,  3,  0,  0,  0,  2),
      ( 0,  0,  0,  0,  0,  0,  0,  4, -8,  0,  0,  0,  0,  0),
      ( 0,  0,  0,  0,  0,  0,  0, -4,  8,  0,  0,  0,  0,  2),
      ( 0,  0, -2,  2,  0,  0,  0,  2,  0, -2,  0,  0,  0,  0),
      ( 0,  0,  0,  0,  0,  0,  0, -4,  7,  0,  0,  0,  0,  2),
      ( 0,  0,  0,  0,  0,  0,  0, -4,  7,  0,  0,  0,  0,  1),
      ( 0,  0,  0,  0,  0,  0,  0,  4, -7,  0,  0,  0,  0,  0),
      ( 0,  0,  0,  0,  1,  0, -2,  3,  0,  0,  0,  0,  0,  0),
      ( 0,  0,  2, -2,  1,  0,  0, -2,  0,  3,  0,  0,  0,  0),
      ( 0,  0,  0,  0,  0,  0,  0, -5, 10,  0,  0,  0,  0,  2),
      ( 0,  0,  0,  0,  1,  0, -1,  2,  0,  0,  0,  0,  0,  0),
      ( 0,  0,  0,  0,  0,  0,  0,  0,  0,  4,  0,  0,  0,  2),
      ( 0,  0,  0,  0,  0,  0,  0, -3,  5,  0,  0,  0,  0,  2),
      ( 0,  0,  0,  0,  0,  0,  0, -3,  5,  0,  0,  0,  0,  1),
      ( 0,  0,  0,  0,  0,  0,  0,  3, -5,  0,  0,  0,  0,  0),
      ( 0,  0,  0,  0,  0,  0,  1, -2,  0,  0,  0,  0,  0,  1),
      ( 0,  0,  1, -1,  1,  0,  1, -3,  0,  0,  0,  0,  0,  0),
      ( 0,  0,  0,  0,  0,  0,  1, -2,  0,  0,  0,  0,  0,  0),
      ( 0,  0,  0,  0,  0,  0, -1,  2,  0,  0,  0,  0,  0,  1),
      ( 0,  0,  0,  0,  0,  0, -1,  2,  0,  0,  0,  0,  0,  2),
      ( 0,  0,  0,  0,  0,  0, -7, 11,  0,  0,  0,  0,  0,  2),
      ( 0,  0,  0,  0,  0,  0, -7, 11,  0,  0,  0,  0,  0,  1),
      ( 0,  0, -2,  2,  0,  0,  4, -4,  0,  0,  0,  0,  0,  0),
      ( 0,  0,  0,  0,  0,  0,  0,  2, -3,  0,  0,  0,  0,  0),
      ( 0,  0,  2, -2,  1,  0, -4,  4,  0,  0,  0,  0,  0,  0),
      ( 0,  0, -1,  1,  0,  0,  4, -5,  0,  0,  0,  0,  0,  0),
      ( 0,  0,  0,  0,  0,  0,  0,  1, -1,  0,  0,  0,  0,  0),
      ( 0,  0,  0,  0,  0,  0, -4,  7,  0,  0,  0,  0,  0,  1),
      ( 0,  0,  1, -1,  1,  0, -4,  6,  0,  0,  0,  0,  0,  0),
      ( 0,  0,  0,  0,  0,  0, -4,  7,  0,  0,  0,  0,  0,  2),
      ( 0,  0,  0,  0,  0,  0, -4,  6,  0,  0,  0,  0,  0,  2),
      ( 0,  0,  0,  0,  0,  0, -4,  6,  0,  0,  0,  0,  0,  1),
      ( 0,  0,  1, -1,  1,  0, -4,  5,  0,  0,  0,  0,  0,  0),
      ( 0,  0,  0,  0,  0,  0, -4,  6,  0,  0,  0,  0,  0,  1),
      ( 0,  0,  0,  0,  0,  0,  4, -6,  0,  0,  0,  0,  0,  0),
      (-2,  0,  0,  2,  0,  0,  2, -2,  0,  0,  0,  0,  0,  0),
      ( 0,  0,  0,  0,  0,  0,  0,  0,  1,  0,  0,  0,  0,  0),
      ( 0,  0, -1,  1,  0,  0,  1,  0,  0,  0,  0,  0,  0,  0),
      ( 0,  0,  0,  0,  1,  0,  1, -1,  0,  0,  0,  0,  0,  0),
      ( 0,  0,  0,  0,  0,  0,  0, -1,  0,  5,  0,  0,  0,  2),
      ( 0,  0,  0,  0,  0,  0,  0,  1, -3,  0,  0,  0,  0,  0),
      ( 0,  0,  0,  0,  0,  0,  0, -1,  3,  0,  0,  0,  0,  2),
      ( 0,  0,  0,  0,  0,  0,  0, -7, 12,  0,  0,  0,  0,  2),
      ( 0,  0,  0,  0,  0,  0, -1,  1,  0,  0,  0,  0,  0,  2),
      ( 0,  0,  0,  0,  0,  0, -1,  1,  0,  0,  0,  0,  0,  1),
      ( 0,  0,  1, -1,  1,  0, -1,  0,  0,  0,  0,  0,  0,  0),
      ( 0,  0,  0,  0,  0,  0,  1, -1,  0,  0,  0,  0,  0,  0),
      ( 0,  0,  0,  0,  0,  0,  1, -1,  0,  0,  0,  0,  0,  1),
      ( 0,  0,  1, -1,  1,  0,  1, -2,  0,  0,  0,  0,  0,  0),
      ( 0,  0,  0,  0,  0,  0,  0, -2,  5,  0,  0,  0,  0,  2),
      ( 0,  0,  0,  0,  0,  0,  0, -1,  0,  4,  0,  0,  0,  2),
      ( 0,  0,  0,  0,  0,  0,  0,  1,  0, -4,  0,  0,  0,  0),
      ( 0,  0,  0,  0,  1,  0, -1,  1,  0,  0,  0,  0,  0,  0),
      ( 0,  0,  0,  0,  0,  0,  0, -6, 10,  0,  0,  0,  0,  2),
      ( 0,  0,  0,  0,  0,  0,  0, -6, 10,  0,  0,  0,  0,  0),
      ( 0,  0,  2, -2,  1,  0,  0, -3,  0,  3,  0,  0,  0,  0),
      ( 0,  0,  0,  0,  0,  0,  0, -3,  7,  0,  0,  0,  0,  2),
      (-2,  0,  0,  2,  0,  0,  4, -4,  0,  0,  0,  0,  0,  0),
      ( 0,  0,  0,  0,  0,  0,  0, -5,  8,  0,  0,  0,  0,  2),
      ( 0,  0,  0,  0,  0,  0,  0,  5, -8,  0,  0,  0,  0,  0),
      ( 0,  0,  0,  0,  0,  0,  0, -1,  0,  3,  0,  0,  0,  2),
      ( 0,  0,  0,  0,  0,  0,  0, -1,  0,  3,  0,  0,  0,  1),
      ( 0,  0,  0,  0,  0,  0,  0,  1,  0, -3,  0,  0,  0,  0),
      ( 0,  0,  0,  0,  0,  0,  2, -4,  0,  0,  0,  0,  0,  0),
      ( 0,  0,  0,  0,  0,  0, -2,  4,  0,  0,  0,  0,  0,  1),
      ( 0,  0,  1, -1,  1,  0, -2,  3,  0,  0,  0,  0,  0,  0),
      ( 0,  0,  0,  0,  0,  0, -2,  4,  0,  0,  0,  0,  0,  2),
      ( 0,  0,  0,  0,  0,  0, -6,  9,  0,  0,  0,  0,  0,  2),
      ( 0,  0,  0,  0,  0,  0, -6,  9,  0,  0,  0,  0,  0,  1),
      ( 0,  0,  0,  0,  0,  0,  6, -9,  0,  0,  0,  0,  0,  0),
      ( 0,  0,  0,  0,  1,  0,  0,  1,  0, -2,  0,  0,  0,  0),
      ( 0,  0,  2, -2,  1,  0, -2,  2,  0,  0,  0,  0,  0,  0),
      ( 0,  0,  0,  0,  0,  0,  0, -4,  6,  0,  0,  0,  0,  2),
      ( 0,  0,  0,  0,  0,  0,  0,  4, -6,  0,  0,  0,  0,  0),
      ( 0,  0,  0,  0,  1,  0,  3, -4,  0,  0,  0,  0,  0,  0),
      ( 0,  0,  0,  0,  0,  0,  0, -1,  0,  2,  0,  0,  0,  2),
      ( 0,  0,  0,  0,  0,  0,  0,  1,  0, -2,  0,  0,  0,  0),
      ( 0,  0,  0,  0,  1,  0,  0,  1,  0, -1,  0,  0,  0,  0),
      ( 0,  0,  0,  0,  0,  0, -5,  9,  0,  0,  0,  0,  0,  2),
      ( 0,  0,  0,  0,  0,  0,  0,  3, -4,  0,  0,  0,  0,  0),
      ( 0,  0,  0,  0,  0,  0, -3,  4,  0,  0,  0,  0,  0,  2),
      ( 0,  0,  0,  0,  0,  0, -3,  4,  0,  0,  0,  0,  0,  1),
      ( 0,  0,  0,  0,  0,  0,  3, -4,  0,  0,  0,  0,  0,  0),
      ( 0,  0,  0,  0,  0,  0,  3, -4,  0,  0,  0,  0,  0,  1),
      ( 0,  0,  0,  0,  1,  0,  0,  2, -2,  0,  0,  0,  0,  0),
      ( 0,  0,  0,  0,  1,  0,  0, -1,  0,  2,  0,  0,  0,  0),
      ( 0,  0,  0,  0,  0,  0,  0,  1,  0,  0, -3,  0,  0,  0),
      ( 0,  0,  0,  0,  0,  0,  0,  1,  0,  1, -5,  0,  0,  0),
      ( 0,  0,  0,  0,  0,  0,  0, -1,  0,  1,  0,  0,  0,  1),
      ( 0,  0,  0,  0,  0,  0,  0,  1,  0, -1,  0,  0,  0,  0),
      ( 0,  0,  0,  0,  0,  0,  0,  1,  0, -1,  0,  0,  0,  1),
      ( 0,  0,  0,  0,  0,  0,  0,  1,  0, -3,  5,  0,  0,  0),
      ( 0,  0,  0,  0,  1,  0, -3,  4,  0,  0,  0,  0,  0,  0),
      ( 0,  0,  0,  0,  0,  0,  0,  1,  0,  0, -2,  0,  0,  0),
      ( 0,  0,  0,  0,  0,  0,  0,  2, -2,  0,  0,  0,  0,  0),
      ( 0,  0,  0,  0,  0,  0,  0,  1,  0,  0, -1,  0,  0,  0),
      ( 0,  0,  0,  0,  1,  0,  0, -1,  0,  1,  0,  0,  0,  0),
      ( 0,  0,  0,  0,  1,  0,  0, -2,  2,  0,  0,  0,  0,  0),
      ( 0,  0,  0,  0,  0,  0, -8, 14,  0,  0,  0,  0,  0,  2),
      ( 0,  0,  0,  0,  0,  0,  0,  1,  0,  2, -5,  0,  0,  0),
      ( 0,  0,  0,  0,  0,  0,  0,  5, -8,  3,  0,  0,  0,  0),
      ( 0,  0,  0,  0,  0,  0,  0,  5, -8,  3,  0,  0,  0,  2),
      ( 0,  0,  0,  0,  0,  0,  0, -1,  0,  0,  0,  0,  0,  1),
      ( 0,  0,  0,  0,  0,  0,  0,  1,  0,  0,  0,  0,  0,  0),
      ( 0,  0,  0,  0,  0,  0,  0,  3, -8,  3,  0,  0,  0,  0),
      ( 0,  0,  0,  0,  0,  0,  0, -3,  8, -3,  0,  0,  0,  2),
      ( 0,  0,  0,  0,  0,  0,  0,  1,  0, -2,  5,  0,  0,  2),
      ( 0,  0,  0,  0,  0,  0, -8, 12,  0,  0,  0,  0,  0,  2),
      ( 0,  0,  0,  0,  0,  0, -8, 12,  0,  0,  0,  0,  0,  0),
      ( 0,  0,  0,  0,  0,  0,  0,  1,  0,  1, -2,  0,  0,  0),
      ( 0,  0,  0,  0,  0,  0,  0,  1,  0,  0,  1,  0,  0,  2),
      ( 0,  0,  0,  0,  0,  0,  0,  0,  2,  0,  0,  0,  0,  0),
      ( 0,  0,  0,  0,  0,  0,  0,  0,  2,  0,  0,  0,  0,  2),
      ( 0,  0,  0,  0,  0,  0,  0,  1,  0,  0,  2,  0,  0,  2),
      ( 0,  0,  2, -2,  1,  0, -5,  5,  0,  0,  0,  0,  0,  0),
      ( 0,  0,  0,  0,  0,  0,  0,  1,  0,  1,  0,  0,  0,  0),
      ( 0,  0,  0,  0,  0,  0,  0,  1,  0,  1,  0,  0,  0,  1),
      ( 0,  0,  0,  0,  0,  0,  0,  1,  0,  1,  0,  0,  0,  2),
      ( 0,  0,  0,  0,  0,  0,  3, -6,  0,  0,  0,  0,  0,  0),
      ( 0,  0,  0,  0,  0,  0, -3,  6,  0,  0,  0,  0,  0,  1),
      ( 0,  0,  0,  0,  0,  0, -3,  6,  0,  0,  0,  0,  0,  2),
      ( 0,  0,  0,  0,  0,  0,  0, -1,  4,  0,  0,  0,  0,  2),
      ( 0,  0,  0,  0,  0,  0, -5,  7,  0,  0,  0,  0,  0,  2),
      ( 0,  0,  0,  0,  0,  0, -5,  7,  0,  0,  0,  0,  0,  1),
      ( 0,  0,  1, -1,  1,  0, -5,  6,  0,  0,  0,  0,  0,  0),
      ( 0,  0,  0,  0,  0,  0,  5, -7,  0,  0,  0,  0,  0,  0),
      ( 0,  0,  2, -2,  1,  0,  0, -1,  0,  1,  0,  0,  0,  0),
      ( 0,  0,  0,  0,  0,  0,  0, -1,  0,  1,  0,  0,  0,  0),
      ( 0,  0,  0,  0,  0, -1,  0,  3,  0,  0,  0,  0,  0,  2),
      ( 0,  0,  0,  0,  0,  0,  0,  1,  0,  2,  0,  0,  0,  2),
      ( 0,  0,  0,  0,  0,  0,  0, -2,  6,  0,  0,  0,  0,  2),
      ( 0,  0,  0,  0,  1,  0,  2, -2,  0,  0,  0,  0,  0,  0),
      ( 0,  0,  0,  0,  0,  0,  0, -6,  9,  0,  0,  0,  0,  2),
      ( 0,  0,  0,  0,  0,  0,  0,  6, -9,  0,  0,  0,  0,  0),
      ( 0,  0,  0,  0,  0,  0, -2,  2,  0,  0,  0,  0,  0,  1),
      ( 0,  0,  1, -1,  1,  0, -2,  1,  0,  0,  0,  0,  0,  0),
      ( 0,  0,  0,  0,  0,  0,  2, -2,  0,  0,  0,  0,  0,  0),
      ( 0,  0,  0,  0,  0,  0,  2, -2,  0,  0,  0,  0,  0,  1),
      ( 0,  0,  0,  0,  0,  0,  0,  1,  0,  3,  0,  0,  0,  2),
      ( 0,  0,  0,  0,  0,  0,  0, -5,  7,  0,  0,  0,  0,  2),
      ( 0,  0,  0,  0,  0,  0,  0,  5, -7,  0,  0,  0,  0,  0),
      ( 0,  0,  0,  0,  1,  0, -2,  2,  0,  0,  0,  0,  0,  0),
      ( 0,  0,  0,  0,  0,  0,  0,  4, -5,  0,  0,  0,  0,  0),
      ( 0,  0,  0,  0,  0,  0,  1, -3,  0,  0,  0,  0,  0,  0),
      ( 0,  0,  0,  0,  0,  0, -1,  3,  0,  0,  0,  0,  0,  1),
      ( 0,  0,  1, -1,  1,  0, -1,  2,  0,  0,  0,  0,  0,  0),
      ( 0,  0,  0,  0,  0,  0, -1,  3,  0,  0,  0,  0,  0,  2),
      ( 0,  0,  0,  0,  0,  0, -7, 10,  0,  0,  0,  0,  0,  2),
      ( 0,  0,  0,  0,  0,  0, -7, 10,  0,  0,  0,  0,  0,  1),
      ( 0,  0,  0,  0,  0,  0,  0,  3, -3,  0,  0,  0,  0,  0),
      ( 0,  0,  0,  0,  0,  0, -4,  8,  0,  0,  0,  0,  0,  2),
      ( 0,  0,  0,  0,  0,  0, -4,  5,  0,  0,  0,  0,  0,  2),
      ( 0,  0,  0,  0,  0,  0, -4,  5,  0,  0,  0,  0,  0,  1),
      ( 0,  0,  0,  0,  0,  0,  4, -5,  0,  0,  0,  0,  0,  0),
      ( 0,  0,  0,  0,  0,  0,  0,  1,  1,  0,  0,  0,  0,  2),
      ( 0,  0,  0,  0,  0,  0,  0, -2,  0,  5,  0,  0,  0,  2),
      ( 0,  0,  0,  0,  0,  0,  0,  0,  3,  0,  0,  0,  0,  2),
      ( 0,  0,  0,  0,  0,  0,  1,  0,  0,  0,  0,  0,  0,  0),
      ( 0,  0,  0,  0,  0,  0,  1,  0,  0,  0,  0,  0,  0,  2),
      ( 0,  0,  0,  0,  0,  0, -9, 13,  0,  0,  0,  0,  0,  2),
      ( 0,  0,  0,  0,  0,  0,  0, -1,  5,  0,  0,  0,  0,  2),
      ( 0,  0,  0,  0,  0,  0,  0, -2,  0,  4,  0,  0,  0,  2),
      ( 0,  0,  0,  0,  0,  0,  0,  2,  0, -4,  0,  0,  0,  0),
      ( 0,  0,  0,  0,  0,  0,  0, -2,  7,  0,  0,  0,  0,  2),
      ( 0,  0,  0,  0,  0,  0,  0,  2,  0, -3,  0,  0,  0,  0),
      ( 0,  0,  0,  0,  0,  0, -2,  5,  0,  0,  0,  0,  0,  1),
      ( 0,  0,  0,  0,  0,  0, -2,  5,  0,  0,  0,  0,  0,  2),
      ( 0,  0,  0,  0,  0,  0, -6,  8,  0,  0,  0,  0,  0,  2),
      ( 0,  0,  0,  0,  0,  0, -6,  8,  0,  0,  0,  0,  0,  1),
      ( 0,  0,  0,  0,  0,  0,  6, -8,  0,  0,  0,  0,  0,  0),
      ( 0,  0,  0,  0,  1,  0,  0,  2,  0, -2,  0,  0,  0,  0),
      ( 0,  0,  0,  0,  0,  0,  0, -3,  9,  0,  0,  0,  0,  2),
      ( 0,  0,  0,  0,  0,  0,  0,  5, -6,  0,  0,  0,  0,  0),
      ( 0,  0,  0,  0,  0,  0,  0,  5, -6,  0,  0,  0,  0,  2),
      ( 0,  0,  0,  0,  0,  0,  0,  2,  0, -2,  0,  0,  0,  0),
      ( 0,  0,  0,  0,  0,  0,  0,  2,  0, -2,  0,  0,  0,  1),
      ( 0,  0,  0,  0,  0,  0,  0,  2,  0, -2,  0,  0,  0,  2),
      ( 0,  0,  0,  0,  0,  0, -5, 10,  0,  0,  0,  0,  0,  2),
      ( 0,  0,  0,  0,  0,  0,  0,  4, -4,  0,  0,  0,  0,  0),
      ( 0,  0,  0,  0,  0,  0,  0,  4, -4,  0,  0,  0,  0,  2),
      ( 0,  0,  0,  0,  0,  0, -3,  3,  0,  0,  0,  0,  0,  1),
      ( 0,  0,  0,  0,  0,  0,  3, -3,  0,  0,  0,  0,  0,  0),
      ( 0,  0,  0,  0,  0,  0,  3, -3,  0,  0,  0,  0,  0,  1),
      ( 0,  0,  0,  0,  0,  0,  3, -3,  0,  0,  0,  0,  0,  2),
      ( 0,  0,  0,  0,  0,  0,  0,  2,  0,  0, -3,  0,  0,  0),
      ( 0,  0,  0,  0,  0,  0,  0, -5, 13,  0,  0,  0,  0,  2),
      ( 0,  0,  0,  0,  0,  0,  0,  2,  0, -1,  0,  0,  0,  0),
      ( 0,  0,  0,  0,  0,  0,  0,  2,  0, -1,  0,  0,  0,  2),
      ( 0,  0,  0,  0,  0,  0,  0,  2,  0,  0, -2,  0,  0,  0),
      ( 0,  0,  0,  0,  0,  0,  0,  2,  0,  0, -2,  0,  0,  1),
      ( 0,  0,  0,  0,  0,  0,  0,  3, -2,  0,  0,  0,  0,  0),
      ( 0,  0,  0,  0,  0,  0,  0,  3, -2,  0,  0,  0,  0,  2),
      ( 0,  0,  0,  0,  0,  0,  0,  2,  0,  0, -1,  0,  0,  2),
      ( 0,  0,  0,  0,  0,  0,  0, -6, 15,  0,  0,  0,  0,  2),
      ( 0,  0,  0,  0,  0,  0, -8, 15,  0,  0,  0,  0,  0,  2),
      ( 0,  0,  0,  0,  0,  0, -3,  9, -4,  0,  0,  0,  0,  2),
      ( 0,  0,  0,  0,  0,  0,  0,  2,  0,  2, -5,  0,  0,  2),
      ( 0,  0,  0,  0,  0,  0,  0, -2,  8, -1, -5,  0,  0,  2),
      ( 0,  0,  0,  0,  0,  0,  0,  6, -8,  3,  0,  0,  0,  2),
      ( 0,  0,  0,  0,  0,  0,  0,  2,  0,  0,  0,  0,  0,  0),
      ( 0,  0,  0,  0,  0,  0,  0,  2,  0,  0,  0,  0,  0,  0),
      ( 0,  0,  0,  0,  0,  0,  0,  2,  0,  0,  0,  0,  0,  1),
      ( 0,  0,  1, -1,  1,  0,  0,  1,  0,  0,  0,  0,  0,  0),
      ( 0,  0,  0,  0,  0,  0,  0,  2,  0,  0,  0,  0,  0,  1),
      ( 0,  0,  0,  0,  0,  0,  0,  2,  0,  0,  0,  0,  0,  2),
      ( 0,  0,  0,  0,  0,  0,  0, -6, 16, -4, -5,  0,  0,  2),
      ( 0,  0,  0,  0,  0,  0,  0, -2,  8, -3,  0,  0,  0,  2),
      ( 0,  0,  0,  0,  0,  0,  0, -2,  8, -3,  0,  0,  0,  2),
      ( 0,  0,  0,  0,  0,  0,  0,  6, -8,  1,  5,  0,  0,  2),
      ( 0,  0,  0,  0,  0,  0,  0,  2,  0, -2,  5,  0,  0,  2),
      ( 0,  0,  0,  0,  0,  0,  3, -5,  4,  0,  0,  0,  0,  2),
      ( 0,  0,  0,  0,  0,  0, -8, 11,  0,  0,  0,  0,  0,  2),
      ( 0,  0,  0,  0,  0,  0, -8, 11,  0,  0,  0,  0,  0,  1),
      ( 0,  0,  0,  0,  0,  0, -8, 11,  0,  0,  0,  0,  0,  2),
      ( 0,  0,  0,  0,  0,  0,  0, 11,  0,  0,  0,  0,  0,  2),
      ( 0,  0,  0,  0,  0,  0,  0,  2,  0,  0,  1,  0,  0,  2),
      ( 0,  0,  0,  0,  0,  0,  3, -3,  0,  2,  0,  0,  0,  2),
      ( 0,  0,  2, -2,  1,  0,  0,  4, -8,  3,  0,  0,  0,  0),
      ( 0,  0,  1, -1,  0,  0,  0,  1,  0,  0,  0,  0,  0,  0),
      ( 0,  0,  2, -2,  1,  0,  0, -4,  8, -3,  0,  0,  0,  0),
      ( 0,  0,  0,  0,  0,  0,  0,  1,  2,  0,  0,  0,  0,  2),
      ( 0,  0,  0,  0,  0,  0,  0,  2,  0,  1,  0,  0,  0,  2),
      ( 0,  0,  0,  0,  0,  0, -3,  7,  0,  0,  0,  0,  0,  2),
      ( 0,  0,  0,  0,  0,  0,  0,  0,  4,  0,  0,  0,  0,  2),
      ( 0,  0,  0,  0,  0,  0, -5,  6,  0,  0,  0,  0,  0,  2),
      ( 0,  0,  0,  0,  0,  0, -5,  6,  0,  0,  0,  0,  0,  1),
      ( 0,  0,  0,  0,  0,  0,  5, -6,  0,  0,  0,  0,  0,  0),
      ( 0,  0,  0,  0,  0,  0,  5, -6,  0,  0,  0,  0,  0,  2),
      ( 0,  0,  0,  0,  0,  0,  0,  2,  0,  2,  0,  0,  0,  2),
      ( 0,  0,  0,  0,  0,  0,  0, -1,  6,  0,  0,  0,  0,  2),
      ( 0,  0,  0,  0,  0,  0,  0,  7, -9,  0,  0,  0,  0,  2),
      ( 0,  0,  0,  0,  0,  0,  2, -1,  0,  0,  0,  0,  0,  0),
      ( 0,  0,  0,  0,  0,  0,  2, -1,  0,  0,  0,  0,  0,  2),
      ( 0,  0,  0,  0,  0,  0,  0,  6, -7,  0,  0,  0,  0,  2),
      ( 0,  0,  0,  0,  0,  0,  0,  5, -5,  0,  0,  0,  0,  2),
      ( 0,  0,  0,  0,  0,  0, -1,  4,  0,  0,  0,  0,  0,  1),
      ( 0,  0,  0,  0,  0,  0, -1,  4,  0,  0,  0,  0,  0,  2),
      ( 0,  0,  0,  0,  0,  0, -7,  9,  0,  0,  0,  0,  0,  2),
      ( 0,  0,  0,  0,  0,  0, -7,  9,  0,  0,  0,  0,  0,  1),
      ( 0,  0,  0,  0,  0,  0,  0,  4, -3,  0,  0,  0,  0,  2),
      ( 0,  0,  0,  0,  0,  0,  0,  3, -1,  0,  0,  0,  0,  2),
      ( 0,  0,  0,  0,  0,  0, -4,  4,  0,  0,  0,  0,  0,  1),
      ( 0,  0,  0,  0,  0,  0,  4, -4,  0,  0,  0,  0,  0,  0),
      ( 0,  0,  0,  0,  0,  0,  4, -4,  0,  0,  0,  0,  0,  1),
      ( 0,  0,  0,  0,  0,  0,  4, -4,  0,  0,  0,  0,  0,  2),
      ( 0,  0,  0,  0,  0,  0,  0,  2,  1,  0,  0,  0,  0,  2),
      ( 0,  0,  0,  0,  0,  0,  0, -3,  0,  5,  0,  0,  0,  2),
      ( 0,  0,  0,  0,  0,  0,  1,  1,  0,  0,  0,  0,  0,  0),
      ( 0,  0,  0,  0,  0,  0,  1,  1,  0,  0,  0,  0,  0,  1),
      ( 0,  0,  0,  0,  0,  0,  1,  1,  0,  0,  0,  0,  0,  2),
      ( 0,  0,  0,  0,  0,  0, -9, 12,  0,  0,  0,  0,  0,  2),
      ( 0,  0,  0,  0,  0,  0,  0,  3,  0, -4,  0,  0,  0,  0),
      ( 0,  0,  2, -2,  1,  0,  1, -1,  0,  0,  0,  0,  0,  0),
      ( 0,  0,  0,  0,  0,  0,  0,  7, -8,  0,  0,  0,  0,  2),
      ( 0,  0,  0,  0,  0,  0,  0,  3,  0, -3,  0,  0,  0,  0),
      ( 0,  0,  0,  0,  0,  0,  0,  3,  0, -3,  0,  0,  0,  2),
      ( 0,  0,  0,  0,  0,  0, -2,  6,  0,  0,  0,  0,  0,  2),
      ( 0,  0,  0,  0,  0,  0, -6,  7,  0,  0,  0,  0,  0,  1),
      ( 0,  0,  0,  0,  0,  0,  6, -7,  0,  0,  0,  0,  0,  0),
      ( 0,  0,  0,  0,  0,  0,  0,  6, -6,  0,  0,  0,  0,  2),
      ( 0,  0,  0,  0,  0,  0,  0,  3,  0, -2,  0,  0,  0,  0),
      ( 0,  0,  0,  0,  0,  0,  0,  3,  0, -2,  0,  0,  0,  2),
      ( 0,  0,  0,  0,  0,  0,  0,  5, -4,  0,  0,  0,  0,  2),
      ( 0,  0,  0,  0,  0,  0,  3, -2,  0,  0,  0,  0,  0,  0),
      ( 0,  0,  0,  0,  0,  0,  3, -2,  0,  0,  0,  0,  0,  2),
      ( 0,  0,  0,  0,  0,  0,  0,  3,  0, -1,  0,  0,  0,  2),
      ( 0,  0,  0,  0,  0,  0,  0,  3,  0, -1,  0,  0,  0,  2),
      ( 0,  0,  0,  0,  0,  0,  0,  3,  0,  0, -2,  0,  0,  2),
      ( 0,  0,  0,  0,  0,  0,  0,  4, -2,  0,  0,  0,  0,  2),
      ( 0,  0,  0,  0,  0,  0,  0,  3,  0,  0, -1,  0,  0,  2),
      ( 0,  0,  2, -2,  1,  0,  0,  1,  0, -1,  0,  0,  0,  0),
      ( 0,  0,  0,  0,  0,  0, -8, 16,  0,  0,  0,  0,  0,  2),
      ( 0,  0,  0,  0,  0,  0,  0,  3,  0,  2, -5,  0,  0,  2),
      ( 0,  0,  0,  0,  0,  0,  0,  7, -8,  3,  0,  0,  0,  2),
      ( 0,  0,  0,  0,  0,  0,  0, -5, 16, -4, -5,  0,  0,  2),
      ( 0,  0,  0,  0,  0,  0,  0,  3,  0,  0,  0,  0,  0,  2),
      ( 0,  0,  0,  0,  0,  0,  0, -1,  8, -3,  0,  0,  0,  2),
      ( 0,  0,  0,  0,  0,  0, -8, 10,  0,  0,  0,  0,  0,  2),
      ( 0,  0,  0,  0,  0,  0, -8, 10,  0,  0,  0,  0,  0,  1),
      ( 0,  0,  0,  0,  0,  0, -8, 10,  0,  0,  0,  0,  0,  2),
      ( 0,  0,  0,  0,  0,  0,  0,  2,  2,  0,  0,  0,  0,  2),
      ( 0,  0,  0,  0,  0,  0,  0,  3,  0,  1,  0,  0,  0,  2),
      ( 0,  0,  0,  0,  0,  0, -3,  8,  0,  0,  0,  0,  0,  2),
      ( 0,  0,  0,  0,  0,  0, -5,  5,  0,  0,  0,  0,  0,  1),
      ( 0,  0,  0,  0,  0,  0,  5, -5,  0,  0,  0,  0,  0,  0),
      ( 0,  0,  0,  0,  0,  0,  5, -5,  0,  0,  0,  0,  0,  1),
      ( 0,  0,  0,  0,  0,  0,  5, -5,  0,  0,  0,  0,  0,  2),
      ( 0,  0,  0,  0,  0,  0,  2,  0,  0,  0,  0,  0,  0,  0),
      ( 0,  0,  0,  0,  0,  0,  2,  0,  0,  0,  0,  0,  0,  1),
      ( 0,  0,  0,  0,  0,  0,  2,  0,  0,  0,  0,  0,  0,  2),
      ( 0,  0,  0,  0,  0,  0,  0,  7, -7,  0,  0,  0,  0,  2),
      ( 0,  0,  0,  0,  0,  0,  0,  7, -7,  0,  0,  0,  0,  2),
      ( 0,  0,  0,  0,  0,  0,  0,  6, -5,  0,  0,  0,  0,  2),
      ( 0,  0,  0,  0,  0,  0,  7, -8,  0,  0,  0,  0,  0,  0),
      ( 0,  0,  0,  0,  0,  0,  0,  5, -3,  0,  0,  0,  0,  2),
      ( 0,  0,  0,  0,  0,  0,  4, -3,  0,  0,  0,  0,  0,  2),
      ( 0,  0,  0,  0,  0,  0,  1,  2,  0,  0,  0,  0,  0,  2),
      ( 0,  0,  0,  0,  0,  0, -9, 11,  0,  0,  0,  0,  0,  2),
      ( 0,  0,  0,  0,  0,  0, -9, 11,  0,  0,  0,  0,  0,  1),
      ( 0,  0,  0,  0,  0,  0,  0,  4,  0, -4,  0,  0,  0,  2),
      ( 0,  0,  0,  0,  0,  0,  0,  4,  0, -3,  0,  0,  0,  2),
      ( 0,  0,  0,  0,  0,  0, -6,  6,  0,  0,  0,  0,  0,  1),
      ( 0,  0,  0,  0,  0,  0,  6, -6,  0,  0,  0,  0,  0,  0),
      ( 0,  0,  0,  0,  0,  0,  6, -6,  0,  0,  0,  0,  0,  1),
      ( 0,  0,  0,  0,  0,  0,  0,  4,  0, -2,  0,  0,  0,  2),
      ( 0,  0,  0,  0,  0,  0,  0,  6, -4,  0,  0,  0,  0,  2),
      ( 0,  0,  0,  0,  0,  0,  3, -1,  0,  0,  0,  0,  0,  0),
      ( 0,  0,  0,  0,  0,  0,  3, -1,  0,  0,  0,  0,  0,  1),
      ( 0,  0,  0,  0,  0,  0,  3, -1,  0,  0,  0,  0,  0,  2),
      ( 0,  0,  0,  0,  0,  0,  0,  4,  0, -1,  0,  0,  0,  2),
      ( 0,  0,  0,  0,  0,  0,  0,  4,  0,  0, -2,  0,  0,  2),
      ( 0,  0,  0,  0,  0,  0,  0,  5, -2,  0,  0,  0,  0,  2),
      ( 0,  0,  0,  0,  0,  0,  0,  4,  0,  0,  0,  0,  0,  0),
      ( 0,  0,  0,  0,  0,  0,  8, -9,  0,  0,  0,  0,  0,  0),
      ( 0,  0,  0,  0,  0,  0,  5, -4,  0,  0,  0,  0,  0,  2),
      ( 0,  0,  0,  0,  0,  0,  2,  1,  0,  0,  0,  0,  0,  2),
      ( 0,  0,  0,  0,  0,  0,  2,  1,  0,  0,  0,  0,  0,  1),
      ( 0,  0,  0,  0,  0,  0,  2,  1,  0,  0,  0,  0,  0,  1),
      ( 0,  0,  0,  0,  0,  0, -7,  7,  0,  0,  0,  0,  0,  1),
      ( 0,  0,  0,  0,  0,  0,  7, -7,  0,  0,  0,  0,  0,  0),
      ( 0,  0,  0,  0,  0,  0,  4, -2,  0,  0,  0,  0,  0,  1),
      ( 0,  0,  0,  0,  0,  0,  4, -2,  0,  0,  0,  0,  0,  2),
      ( 0,  0,  0,  0,  0,  0,  4, -2,  0,  0,  0,  0,  0,  0),
      ( 0,  0,  0,  0,  0,  0,  4, -2,  0,  0,  0,  0,  0,  0),
      ( 0,  0,  0,  0,  0,  0,  0,  5,  0, -4,  0,  0,  0,  2),
      ( 0,  0,  0,  0,  0,  0,  0,  5,  0, -3,  0,  0,  0,  2),
      ( 0,  0,  0,  0,  0,  0,  0,  5,  0, -2,  0,  0,  0,  2),
      ( 0,  0,  0,  0,  0,  0,  3,  0,  0,  0,  0,  0,  0,  2),
      ( 0,  0,  0,  0,  0,  0, -8,  8,  0,  0,  0,  0,  0,  1),
      ( 0,  0,  0,  0,  0,  0,  8, -8,  0,  0,  0,  0,  0,  0),
      ( 0,  0,  0,  0,  0,  0,  5, -3,  0,  0,  0,  0,  0,  1),
      ( 0,  0,  0,  0,  0,  0,  5, -3,  0,  0,  0,  0,  0,  2),
      ( 0,  0,  0,  0,  0,  0, -9,  9,  0,  0,  0,  0,  0,  1),
      ( 0,  0,  0,  0,  0,  0, -9,  9,  0,  0,  0,  0,  0,  1),
      ( 0,  0,  0,  0,  0,  0, -9,  9,  0,  0,  0,  0,  0,  1),
      ( 0,  0,  0,  0,  0,  0,  9, -9,  0,  0,  0,  0,  0,  0),
      ( 0,  0,  0,  0,  0,  0,  6, -4,  0,  0,  0,  0,  0,  1),
      ( 0,  0,  0,  0,  0,  0,  0,  6,  0,  0,  0,  0,  0,  2),
      ( 0,  0,  0,  0,  0,  0,  0,  6,  0,  0,  0,  0,  0,  0),
      ( 0,  0,  0,  0,  0,  0,  0,  6,  0,  0,  0,  0,  0,  0),
      ( 0,  0,  0,  0,  0,  0,  0,  6,  0,  0,  0,  0,  0,  1),
      ( 0,  0,  0,  0,  0,  0,  0,  6,  0,  0,  0,  0,  0,  2),
      ( 0,  0,  0,  0,  0,  0,  0,  6,  0,  0,  0,  0,  0,  0),
      ( 0,  0,  0,  0,  0,  0,  0,  6,  0,  0,  0,  0,  0,  1),
      ( 0,  0,  0,  0,  0,  0,  0,  6,  0,  0,  0,  0,  0,  2),
      ( 0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  2),
      ( 1,  0,  0, -2,  0,  0,  0,  2,  0, -2,  0,  0,  0,  0),
      ( 1,  0,  0, -2,  0,  0,  2, -2,  0,  0,  0,  0,  0,  0),
      ( 1,  0,  0, -2,  0,  0,  0,  1,  0, -1,  0,  0,  0,  0),
      ( 1,  0,  0, -2,  0,  0,  1, -1,  0,  0,  0,  0,  0,  0),
      (-1,  0,  0,  0,  0,  0,  3, -3,  0,  0,  0,  0,  0,  0),
      (-1,  0,  0,  0,  0,  0,  0,  2,  0, -2,  0,  0,  0,  0),
      (-1,  0,  0,  2,  0,  0,  0,  4, -8,  3,  0,  0,  0,  0),
      ( 1,  0,  0, -2,  0,  0,  0,  4, -8,  3,  0,  0,  0,  0),
      (-2,  0,  0,  2,  0,  0,  0,  4, -8,  3,  0,  0,  0,  0),
      (-1,  0,  0,  0,  0,  0,  0,  2,  0, -3,  0,  0,  0,  0),
      (-1,  0,  0,  0,  0,  0,  0,  1,  0, -1,  0,  0,  0,  0),
      (-1,  0,  0,  0,  0,  0,  1, -1,  0,  0,  0,  0,  0,  0),
      (-1,  0,  0,  2,  0,  0,  2, -2,  0,  0,  0,  0,  0,  0),
      ( 1,  0, -1,  1,  0,  0,  0,  1,  0,  0,  0,  0,  0,  0),
      (-1,  0,  0,  2,  0,  0,  0,  2,  0, -3,  0,  0,  0,  0),
      (-2,  0,  0,  0,  0,  0,  0,  2,  0, -3,  0,  0,  0,  0),
      ( 1,  0,  0,  0,  0,  0,  0,  4, -8,  3,  0,  0,  0,  0),
      (-1,  0,  1, -1,  1,  0,  0, -1,  0,  0,  0,  0,  0,  0),
      ( 1,  0,  1, -1,  1,  0,  0, -1,  0,  0,  0,  0,  0,  0),
      (-1,  0,  0,  0,  0,  0,  0,  4, -8,  3,  0,  0,  0,  0),
      (-1,  0,  0,  2,  1,  0,  0,  2,  0, -2,  0,  0,  0,  0),
      ( 0,  0,  0,  0,  0,  0,  0,  2,  0, -2,  0,  0,  0,  0),
      (-1,  0,  0,  2,  0,  0,  0,  2,  0, -2,  0,  0,  0,  0),
      (-1,  0,  0,  2,  0,  0,  3, -3,  0,  0,  0,  0,  0,  0),
      ( 1,  0,  0, -2,  1,  0,  0, -2,  0,  2,  0,  0,  0,  0),
      ( 1,  0,  2, -2,  2,  0, -3,  3,  0,  0,  0,  0,  0,  0),
      ( 1,  0,  2, -2,  2,  0,  0, -2,  0,  2,  0,  0,  0,  0),
      ( 1,  0,  0,  0,  0,  0,  1, -1,  0,  0,  0,  0,  0,  0),
      ( 1,  0,  0,  0,  0,  0,  0,  1,  0, -1,  0,  0,  0,  0),
      ( 0,  0,  0, -2,  0,  0,  2, -2,  0,  0,  0,  0,  0,  0),
      ( 0,  0,  0, -2,  0,  0,  0,  1,  0, -1,  0,  0,  0,  0),
      ( 0,  0,  2,  0,  2,  0, -2,  2,  0,  0,  0,  0,  0,  0),
      ( 0,  0,  2,  0,  2,  0,  0, -1,  0,  1,  0,  0,  0,  0),
      ( 0,  0,  2,  0,  2,  0, -1,  1,  0,  0,  0,  0,  0,  0),
      ( 0,  0,  2,  0,  2,  0, -2,  3,  0,  0,  0,  0,  0,  0),
      ( 0,  0,  0,  2,  0,  0,  0,  2,  0, -2,  0,  0,  0,  0),
      ( 0,  0,  1,  1,  2,  0,  0,  1,  0,  0,  0,  0,  0,  0),
      ( 1,  0,  2,  0,  2,  0,  0,  1,  0,  0,  0,  0,  0,  0),
      (-1,  0,  2,  0,  2,  0, 10, -3,  0,  0,  0,  0,  0,  0),
      ( 0,  0,  1,  1,  1,  0,  0,  1,  0,  0,  0,  0,  0,  0),
      ( 1,  0,  2,  0,  2,  0,  0,  1,  0,  0,  0,  0,  0,  0),
      ( 0,  0,  2,  0,  2,  0,  0,  4, -8,  3,  0,  0,  0,  0),
      ( 0,  0,  2,  0,  2,  0,  0, -4,  8, -3,  0,  0,  0,  0),
      (-1,  0,  2,  0,  2,  0,  0, -4,  8, -3,  0,  0,  0,  0),
      ( 2,  0,  2, -2,  2,  0,  0, -2,  0,  3,  0,  0,  0,  0),
      ( 1,  0,  2,  0,  1,  0,  0, -2,  0,  3,  0,  0,  0,  0),
      ( 0,  0,  1,  1,  0,  0,  0,  1,  0,  0,  0,  0,  0,  0),
      (-1,  0,  2,  0,  1,  0,  0,  1,  0,  0,  0,  0,  0,  0),
      (-2,  0,  2,  2,  2,  0,  0,  2,  0, -2,  0,  0,  0,  0),
      ( 0,  0,  2,  0,  2,  0,  2, -3,  0,  0,  0,  0,  0,  0),
      ( 0,  0,  2,  0,  2,  0,  1, -1,  0,  0,  0,  0,  0,  0),
      ( 0,  0,  2,  0,  2,  0,  0,  1,  0, -1,  0,  0,  0,  0),
      ( 0,  0,  2,  0,  2,  0,  2, -2,  0,  0,  0,  0,  0,  0),
      (-1,  0,  2,  2,  2,  0,  0, -1,  0,  1,  0,  0,  0,  0),
      ( 1,  0,  2,  0,  2,  0, -1,  1,  0,  0,  0,  0,  0,  0),
      (-1,  0,  2,  2,  2,  0,  0,  2,  0, -3,  0,  0,  0,  0),
      ( 2,  0,  2,  0,  2,  0,  0,  2,  0, -3,  0,  0,  0,  0),
      ( 1,  0,  2,  0,  2,  0,  0, -4,  8, -3,  0,  0,  0,  0),
      ( 1,  0,  2,  0,  2,  0,  0,  4, -8,  3,  0,  0,  0,  0),
      ( 1,  0,  1,  1,  1,  0,  0,  1,  0,  0,  0,  0,  0,  0),
      ( 0,  0,  2,  0,  2,  0,  0,  1,  0,  0,  0,  0,  0,  0),
      ( 2,  0,  2,  0,  1,  0,  0,  1,  0,  0,  0,  0,  0,  0),
      (-1,  0,  2,  2,  2,  0,  0,  2,  0, -2,  0,  0,  0,  0),
      (-1,  0,  2,  2,  2,  0,  3, -3,  0,  0,  0,  0,  0,  0),
      ( 1,  0,  2,  0,  2,  0,  1, -1,  0,  0,  0,  0,  0,  0),
      ( 0,  0,  2,  2,  2,  0,  0,  2,  0, -2,  0,  0,  0,  0),
      ))

# Planetary nutation coefficients, unit 1e-7 arcsec:
# longitude (sin, cos), obliquity (sin, cos)

# Each row of coefficients in 'cpl_t' belongs with the corresponding
# row of fundamental-argument multipliers in 'napl_t'.

nutation_coefficients = array((
      ( 1440.0,          0.0,          0.0,          0.0),
      (   56.0,       -117.0,        -42.0,        -40.0),
      (  125.0,        -43.0,          0.0,        -54.0),
      (    0.0,          5.0,          0.0,          0.0),
      (    3.0,         -7.0,         -3.0,          0.0),
      (    3.0,          0.0,          0.0,         -2.0),
      ( -114.0,          0.0,          0.0,         61.0),
      ( -219.0,         89.0,          0.0,          0.0),
      (   -3.0,          0.0,          0.0,          0.0),
      ( -462.0,       1604.0,          0.0,          0.0),
      (   99.0,          0.0,          0.0,        -53.0),
      (   -3.0,          0.0,          0.0,          2.0),
      (    0.0,          6.0,          2.0,          0.0),
      (    3.0,          0.0,          0.0,          0.0),
      (  -12.0,          0.0,          0.0,          0.0),
      (   14.0,       -218.0,        117.0,          8.0),
      (   31.0,       -481.0,       -257.0,        -17.0),
      ( -491.0,        128.0,          0.0,          0.0),
      (-3084.0,       5123.0,       2735.0,       1647.0),
      (-1444.0,       2409.0,      -1286.0,       -771.0),
      (   11.0,        -24.0,        -11.0,         -9.0),
      (   26.0,         -9.0,          0.0,          0.0),
      (  103.0,        -60.0,          0.0,          0.0),
      (    0.0,        -13.0,         -7.0,          0.0),
      (  -26.0,        -29.0,        -16.0,         14.0),
      (    9.0,        -27.0,        -14.0,         -5.0),
      (   12.0,          0.0,          0.0,         -6.0),
      (   -7.0,          0.0,          0.0,          0.0),
      (    0.0,         24.0,          0.0,          0.0),
      (  284.0,          0.0,          0.0,       -151.0),
      (  226.0,        101.0,          0.0,          0.0),
      (    0.0,         -8.0,         -2.0,          0.0),
      (    0.0,         -6.0,         -3.0,          0.0),
      (    5.0,          0.0,          0.0,         -3.0),
      (  -41.0,        175.0,         76.0,         17.0),
      (    0.0,         15.0,          6.0,          0.0),
      (  425.0,        212.0,       -133.0,        269.0),
      ( 1200.0,        598.0,        319.0,       -641.0),
      (  235.0,        334.0,          0.0,          0.0),
      (   11.0,        -12.0,         -7.0,         -6.0),
      (    5.0,         -6.0,          3.0,          3.0),
      (   -5.0,          0.0,          0.0,          3.0),
      (    6.0,          0.0,          0.0,         -3.0),
      (   15.0,          0.0,          0.0,          0.0),
      (   13.0,          0.0,          0.0,         -7.0),
      (   -6.0,         -9.0,          0.0,          0.0),
      (  266.0,        -78.0,          0.0,          0.0),
      ( -460.0,       -435.0,       -232.0,        246.0),
      (    0.0,         15.0,          7.0,          0.0),
      (   -3.0,          0.0,          0.0,          2.0),
      (    0.0,        131.0,          0.0,          0.0),
      (    4.0,          0.0,          0.0,          0.0),
      (    0.0,          3.0,          0.0,          0.0),
      (    0.0,          4.0,          2.0,          0.0),
      (    0.0,          3.0,          0.0,          0.0),
      (  -17.0,        -19.0,        -10.0,          9.0),
      (   -9.0,        -11.0,          6.0,         -5.0),
      (   -6.0,          0.0,          0.0,          3.0),
      (  -16.0,          8.0,          0.0,          0.0),
      (    0.0,          3.0,          0.0,          0.0),
      (   11.0,         24.0,         11.0,         -5.0),
      (   -3.0,         -4.0,         -2.0,          1.0),
      (    3.0,          0.0,          0.0,         -1.0),
      (    0.0,         -8.0,         -4.0,          0.0),
      (    0.0,          3.0,          0.0,          0.0),
      (    0.0,          5.0,          0.0,          0.0),
      (    0.0,          3.0,          2.0,          0.0),
      (   -6.0,          4.0,          2.0,          3.0),
      (   -3.0,         -5.0,          0.0,          0.0),
      (   -5.0,          0.0,          0.0,          2.0),
      (    4.0,         24.0,         13.0,         -2.0),
      (  -42.0,         20.0,          0.0,          0.0),
      (  -10.0,        233.0,          0.0,          0.0),
      (   -3.0,          0.0,          0.0,          1.0),
      (   78.0,        -18.0,          0.0,          0.0),
      (    0.0,          3.0,          1.0,          0.0),
      (    0.0,         -3.0,         -1.0,          0.0),
      (    0.0,         -4.0,         -2.0,          1.0),
      (    0.0,         -8.0,         -4.0,         -1.0),
      (    0.0,         -5.0,          3.0,          0.0),
      (   -7.0,          0.0,          0.0,          3.0),
      (  -14.0,          8.0,          3.0,          6.0),
      (    0.0,          8.0,         -4.0,          0.0),
      (    0.0,         19.0,         10.0,          0.0),
      (   45.0,        -22.0,          0.0,          0.0),
      (   -3.0,          0.0,          0.0,          0.0),
      (    0.0,         -3.0,          0.0,          0.0),
      (    0.0,          3.0,          0.0,          0.0),
      (    3.0,          5.0,          3.0,         -2.0),
      (   89.0,        -16.0,         -9.0,        -48.0),
      (    0.0,          3.0,          0.0,          0.0),
      (   -3.0,          7.0,          4.0,          2.0),
      ( -349.0,        -62.0,          0.0,          0.0),
      (  -15.0,         22.0,          0.0,          0.0),
      (   -3.0,          0.0,          0.0,          0.0),
      (  -53.0,          0.0,          0.0,          0.0),
      (    5.0,          0.0,          0.0,         -3.0),
      (    0.0,         -8.0,          0.0,          0.0),
      (   15.0,         -7.0,         -4.0,         -8.0),
      (   -3.0,          0.0,          0.0,          1.0),
      (  -21.0,        -78.0,          0.0,          0.0),
      (   20.0,        -70.0,        -37.0,        -11.0),
      (    0.0,          6.0,          3.0,          0.0),
      (    5.0,          3.0,          2.0,         -2.0),
      (  -17.0,         -4.0,         -2.0,          9.0),
      (    0.0,          6.0,          3.0,          0.0),
      (   32.0,         15.0,         -8.0,         17.0),
      (  174.0,         84.0,         45.0,        -93.0),
      (   11.0,         56.0,          0.0,          0.0),
      (  -66.0,        -12.0,         -6.0,         35.0),
      (   47.0,          8.0,          4.0,        -25.0),
      (    0.0,          8.0,          4.0,          0.0),
      (   10.0,        -22.0,        -12.0,         -5.0),
      (   -3.0,          0.0,          0.0,          2.0),
      (  -24.0,         12.0,          0.0,          0.0),
      (    5.0,         -6.0,          0.0,          0.0),
      (    3.0,          0.0,          0.0,         -2.0),
      (    4.0,          3.0,          1.0,         -2.0),
      (    0.0,         29.0,         15.0,          0.0),
      (   -5.0,         -4.0,         -2.0,          2.0),
      (    8.0,         -3.0,         -1.0,         -5.0),
      (    0.0,         -3.0,          0.0,          0.0),
      (   10.0,          0.0,          0.0,          0.0),
      (    3.0,          0.0,          0.0,         -2.0),
      (   -5.0,          0.0,          0.0,          3.0),
      (   46.0,         66.0,         35.0,        -25.0),
      (  -14.0,          7.0,          0.0,          0.0),
      (    0.0,          3.0,          2.0,          0.0),
      (   -5.0,          0.0,          0.0,          0.0),
      (  -68.0,        -34.0,        -18.0,         36.0),
      (    0.0,         14.0,          7.0,          0.0),
      (   10.0,         -6.0,         -3.0,         -5.0),
      (   -5.0,         -4.0,         -2.0,          3.0),
      (   -3.0,          5.0,          2.0,          1.0),
      (   76.0,         17.0,          9.0,        -41.0),
      (   84.0,        298.0,        159.0,        -45.0),
      (    3.0,          0.0,          0.0,         -1.0),
      (   -3.0,          0.0,          0.0,          2.0),
      (   -3.0,          0.0,          0.0,          1.0),
      (  -82.0,        292.0,        156.0,         44.0),
      (  -73.0,         17.0,          9.0,         39.0),
      (   -9.0,        -16.0,          0.0,          0.0),
      (    3.0,          0.0,         -1.0,         -2.0),
      (   -3.0,          0.0,          0.0,          0.0),
      (   -9.0,         -5.0,         -3.0,          5.0),
      ( -439.0,          0.0,          0.0,          0.0),
      (   57.0,        -28.0,        -15.0,        -30.0),
      (    0.0,         -6.0,         -3.0,          0.0),
      (   -4.0,          0.0,          0.0,          2.0),
      (  -40.0,         57.0,         30.0,         21.0),
      (   23.0,          7.0,          3.0,        -13.0),
      (  273.0,         80.0,         43.0,       -146.0),
      ( -449.0,        430.0,          0.0,          0.0),
      (   -8.0,        -47.0,        -25.0,          4.0),
      (    6.0,         47.0,         25.0,         -3.0),
      (    0.0,         23.0,         13.0,          0.0),
      (   -3.0,          0.0,          0.0,          2.0),
      (    3.0,         -4.0,         -2.0,         -2.0),
      (  -48.0,       -110.0,        -59.0,         26.0),
      (   51.0,        114.0,         61.0,        -27.0),
      ( -133.0,          0.0,          0.0,         57.0),
      (    0.0,          4.0,          0.0,          0.0),
      (  -21.0,         -6.0,         -3.0,         11.0),
      (    0.0,         -3.0,         -1.0,          0.0),
      (  -11.0,        -21.0,        -11.0,          6.0),
      (  -18.0,       -436.0,       -233.0,          9.0),
      (   35.0,         -7.0,          0.0,          0.0),
      (    0.0,          5.0,          3.0,          0.0),
      (   11.0,         -3.0,         -1.0,         -6.0),
      (   -5.0,         -3.0,         -1.0,          3.0),
      (  -53.0,         -9.0,         -5.0,         28.0),
      (    0.0,          3.0,          2.0,          1.0),
      (    4.0,          0.0,          0.0,         -2.0),
      (    0.0,         -4.0,          0.0,          0.0),
      (  -50.0,        194.0,        103.0,         27.0),
      (  -13.0,         52.0,         28.0,          7.0),
      (  -91.0,        248.0,          0.0,          0.0),
      (    6.0,         49.0,         26.0,         -3.0),
      (   -6.0,        -47.0,        -25.0,          3.0),
      (    0.0,          5.0,          3.0,          0.0),
      (   52.0,         23.0,         10.0,        -23.0),
      (   -3.0,          0.0,          0.0,          1.0),
      (    0.0,          5.0,          3.0,          0.0),
      (   -4.0,          0.0,          0.0,          0.0),
      (   -4.0,          8.0,          3.0,          2.0),
      (   10.0,          0.0,          0.0,          0.0),
      (    3.0,          0.0,          0.0,         -2.0),
      (    0.0,          8.0,          4.0,          0.0),
      (    0.0,          8.0,          4.0,          1.0),
      (   -4.0,          0.0,          0.0,          0.0),
      (   -4.0,          0.0,          0.0,          0.0),
      (   -8.0,          4.0,          2.0,          4.0),
      (    8.0,         -4.0,         -2.0,         -4.0),
      (    0.0,         15.0,          7.0,          0.0),
      ( -138.0,          0.0,          0.0,          0.0),
      (    0.0,         -7.0,         -3.0,          0.0),
      (    0.0,         -7.0,         -3.0,          0.0),
      (   54.0,          0.0,          0.0,        -29.0),
      (    0.0,         10.0,          4.0,          0.0),
      (   -7.0,          0.0,          0.0,          3.0),
      (  -37.0,         35.0,         19.0,         20.0),
      (    0.0,          4.0,          0.0,          0.0),
      (   -4.0,          9.0,          0.0,          0.0),
      (    8.0,          0.0,          0.0,         -4.0),
      (   -9.0,        -14.0,         -8.0,          5.0),
      (   -3.0,         -9.0,         -5.0,          3.0),
      ( -145.0,         47.0,          0.0,          0.0),
      (  -10.0,         40.0,         21.0,          5.0),
      (   11.0,        -49.0,        -26.0,         -7.0),
      (-2150.0,          0.0,          0.0,        932.0),
      (  -12.0,          0.0,          0.0,          5.0),
      (   85.0,          0.0,          0.0,        -37.0),
      (    4.0,          0.0,          0.0,         -2.0),
      (    3.0,          0.0,          0.0,         -2.0),
      (  -86.0,        153.0,          0.0,          0.0),
      (   -6.0,          9.0,          5.0,          3.0),
      (    9.0,        -13.0,         -7.0,         -5.0),
      (   -8.0,         12.0,          6.0,          4.0),
      (  -51.0,          0.0,          0.0,         22.0),
      (  -11.0,       -268.0,       -116.0,          5.0),
      (    0.0,         12.0,          5.0,          0.0),
      (    0.0,          7.0,          3.0,          0.0),
      (   31.0,          6.0,          3.0,        -17.0),
      (  140.0,         27.0,         14.0,        -75.0),
      (   57.0,         11.0,          6.0,        -30.0),
      (  -14.0,        -39.0,          0.0,          0.0),
      (    0.0,         -6.0,         -2.0,          0.0),
      (    4.0,         15.0,          8.0,         -2.0),
      (    0.0,          4.0,          0.0,          0.0),
      (   -3.0,          0.0,          0.0,          1.0),
      (    0.0,         11.0,          5.0,          0.0),
      (    9.0,          6.0,          0.0,          0.0),
      (   -4.0,         10.0,          4.0,          2.0),
      (    5.0,          3.0,          0.0,          0.0),
      (   16.0,          0.0,          0.0,         -9.0),
      (   -3.0,          0.0,          0.0,          0.0),
      (    0.0,          3.0,          2.0,         -1.0),
      (    7.0,          0.0,          0.0,         -3.0),
      (  -25.0,         22.0,          0.0,          0.0),
      (   42.0,        223.0,        119.0,        -22.0),
      (  -27.0,       -143.0,        -77.0,         14.0),
      (    9.0,         49.0,         26.0,         -5.0),
      (-1166.0,          0.0,          0.0,        505.0),
      (   -5.0,          0.0,          0.0,          2.0),
      (   -6.0,          0.0,          0.0,          3.0),
      (   -8.0,          0.0,          1.0,          4.0),
      (    0.0,         -4.0,          0.0,          0.0),
      (  117.0,          0.0,          0.0,        -63.0),
      (   -4.0,          8.0,          4.0,          2.0),
      (    3.0,          0.0,          0.0,         -2.0),
      (   -5.0,          0.0,          0.0,          2.0),
      (    0.0,         31.0,          0.0,          0.0),
      (   -5.0,          0.0,          1.0,          3.0),
      (    4.0,          0.0,          0.0,         -2.0),
      (   -4.0,          0.0,          0.0,          2.0),
      (  -24.0,        -13.0,         -6.0,         10.0),
      (    3.0,          0.0,          0.0,          0.0),
      (    0.0,        -32.0,        -17.0,          0.0),
      (    8.0,         12.0,          5.0,         -3.0),
      (    3.0,          0.0,          0.0,         -1.0),
      (    7.0,         13.0,          0.0,          0.0),
      (   -3.0,         16.0,          0.0,          0.0),
      (   50.0,          0.0,          0.0,        -27.0),
      (    0.0,         -5.0,         -3.0,          0.0),
      (   13.0,          0.0,          0.0,          0.0),
      (    0.0,          5.0,          3.0,          1.0),
      (   24.0,          5.0,          2.0,        -11.0),
      (    5.0,        -11.0,         -5.0,         -2.0),
      (   30.0,         -3.0,         -2.0,        -16.0),
      (   18.0,          0.0,          0.0,         -9.0),
      (    8.0,        614.0,          0.0,          0.0),
      (    3.0,         -3.0,         -1.0,         -2.0),
      (    6.0,         17.0,          9.0,         -3.0),
      (   -3.0,         -9.0,         -5.0,          2.0),
      (    0.0,          6.0,          3.0,         -1.0),
      ( -127.0,         21.0,          9.0,         55.0),
      (    3.0,          5.0,          0.0,          0.0),
      (   -6.0,        -10.0,         -4.0,          3.0),
      (    5.0,          0.0,          0.0,          0.0),
      (   16.0,          9.0,          4.0,         -7.0),
      (    3.0,          0.0,          0.0,         -2.0),
      (    0.0,         22.0,          0.0,          0.0),
      (    0.0,         19.0,         10.0,          0.0),
      (    7.0,          0.0,          0.0,         -4.0),
      (    0.0,         -5.0,         -2.0,          0.0),
      (    0.0,          3.0,          1.0,          0.0),
      (   -9.0,          3.0,          1.0,          4.0),
      (   17.0,          0.0,          0.0,         -7.0),
      (    0.0,         -3.0,         -2.0,         -1.0),
      (  -20.0,         34.0,          0.0,          0.0),
      (  -10.0,          0.0,          1.0,          5.0),
      (   -4.0,          0.0,          0.0,          2.0),
      (   22.0,        -87.0,          0.0,          0.0),
      (   -4.0,          0.0,          0.0,          2.0),
      (   -3.0,         -6.0,         -2.0,          1.0),
      (  -16.0,         -3.0,         -1.0,          7.0),
      (    0.0,         -3.0,         -2.0,          0.0),
      (    4.0,          0.0,          0.0,          0.0),
      (  -68.0,         39.0,          0.0,          0.0),
      (   27.0,          0.0,          0.0,        -14.0),
      (    0.0,         -4.0,          0.0,          0.0),
      (  -25.0,          0.0,          0.0,          0.0),
      (  -12.0,         -3.0,         -2.0,          6.0),
      (    3.0,          0.0,          0.0,         -1.0),
      (    3.0,         66.0,         29.0,         -1.0),
      (  490.0,          0.0,          0.0,       -213.0),
      (  -22.0,         93.0,         49.0,         12.0),
      (   -7.0,         28.0,         15.0,          4.0),
      (   -3.0,         13.0,          7.0,          2.0),
      (  -46.0,         14.0,          0.0,          0.0),
      (   -5.0,          0.0,          0.0,          0.0),
      (    2.0,          1.0,          0.0,          0.0),
      (    0.0,         -3.0,          0.0,          0.0),
      (  -28.0,          0.0,          0.0,         15.0),
      (    5.0,          0.0,          0.0,         -2.0),
      (    0.0,          3.0,          0.0,          0.0),
      (  -11.0,          0.0,          0.0,          5.0),
      (    0.0,          3.0,          1.0,          0.0),
      (   -3.0,          0.0,          0.0,          1.0),
      (   25.0,        106.0,         57.0,        -13.0),
      (    5.0,         21.0,         11.0,         -3.0),
      ( 1485.0,          0.0,          0.0,          0.0),
      (   -7.0,        -32.0,        -17.0,          4.0),
      (    0.0,          5.0,          3.0,          0.0),
      (   -6.0,         -3.0,         -2.0,          3.0),
      (   30.0,         -6.0,         -2.0,        -13.0),
      (   -4.0,          4.0,          0.0,          0.0),
      (  -19.0,          0.0,          0.0,         10.0),
      (    0.0,          4.0,          2.0,         -1.0),
      (    0.0,          3.0,          0.0,          0.0),
      (    4.0,          0.0,          0.0,         -2.0),
      (    0.0,         -3.0,         -1.0,          0.0),
      (   -3.0,          0.0,          0.0,          0.0),
      (    5.0,          3.0,          1.0,         -2.0),
      (    0.0,         11.0,          0.0,          0.0),
      (  118.0,          0.0,          0.0,        -52.0),
      (    0.0,         -5.0,         -3.0,          0.0),
      (  -28.0,         36.0,          0.0,          0.0),
      (    5.0,         -5.0,          0.0,          0.0),
      (   14.0,        -59.0,        -31.0,         -8.0),
      (    0.0,          9.0,          5.0,          1.0),
      ( -458.0,          0.0,          0.0,        198.0),
      (    0.0,        -45.0,        -20.0,          0.0),
      (    9.0,          0.0,          0.0,         -5.0),
      (    0.0,         -3.0,          0.0,          0.0),
      (    0.0,         -4.0,         -2.0,         -1.0),
      (   11.0,          0.0,          0.0,         -6.0),
      (    6.0,          0.0,          0.0,         -2.0),
      (  -16.0,         23.0,          0.0,          0.0),
      (    0.0,         -4.0,         -2.0,          0.0),
      (   -5.0,          0.0,          0.0,          2.0),
      ( -166.0,        269.0,          0.0,          0.0),
      (   15.0,          0.0,          0.0,         -8.0),
      (   10.0,          0.0,          0.0,         -4.0),
      (  -78.0,         45.0,          0.0,          0.0),
      (    0.0,         -5.0,         -2.0,          0.0),
      (    7.0,          0.0,          0.0,         -4.0),
      (   -5.0,        328.0,          0.0,          0.0),
      (    3.0,          0.0,          0.0,         -2.0),
      (    5.0,          0.0,          0.0,         -2.0),
      (    0.0,          3.0,          1.0,          0.0),
      (   -3.0,          0.0,          0.0,          0.0),
      (   -3.0,          0.0,          0.0,          0.0),
      (    0.0,         -4.0,         -2.0,          0.0),
      (-1223.0,        -26.0,          0.0,          0.0),
      (    0.0,          7.0,          3.0,          0.0),
      (    3.0,          0.0,          0.0,          0.0),
      (    0.0,          3.0,          2.0,          0.0),
      (   -6.0,         20.0,          0.0,          0.0),
      ( -368.0,          0.0,          0.0,          0.0),
      (  -75.0,          0.0,          0.0,          0.0),
      (   11.0,          0.0,          0.0,         -6.0),
      (    3.0,          0.0,          0.0,         -2.0),
      (   -3.0,          0.0,          0.0,          1.0),
      (  -13.0,        -30.0,          0.0,          0.0),
      (   21.0,          3.0,          0.0,          0.0),
      (   -3.0,          0.0,          0.0,          1.0),
      (   -4.0,          0.0,          0.0,          2.0),
      (    8.0,        -27.0,          0.0,          0.0),
      (  -19.0,        -11.0,          0.0,          0.0),
      (   -4.0,          0.0,          0.0,          2.0),
      (    0.0,          5.0,          2.0,          0.0),
      (   -6.0,          0.0,          0.0,          2.0),
      (   -8.0,          0.0,          0.0,          0.0),
      (   -1.0,          0.0,          0.0,          0.0),
      (  -14.0,          0.0,          0.0,          6.0),
      (    6.0,          0.0,          0.0,          0.0),
      (  -74.0,          0.0,          0.0,         32.0),
      (    0.0,         -3.0,         -1.0,          0.0),
      (    4.0,          0.0,          0.0,         -2.0),
      (    8.0,         11.0,          0.0,          0.0),
      (    0.0,          3.0,          2.0,          0.0),
      ( -262.0,          0.0,          0.0,        114.0),
      (    0.0,         -4.0,          0.0,          0.0),
      (   -7.0,          0.0,          0.0,          4.0),
      (    0.0,        -27.0,        -12.0,          0.0),
      (  -19.0,         -8.0,         -4.0,          8.0),
      (  202.0,          0.0,          0.0,        -87.0),
      (   -8.0,         35.0,         19.0,          5.0),
      (    0.0,          4.0,          2.0,          0.0),
      (   16.0,         -5.0,          0.0,          0.0),
      (    5.0,          0.0,          0.0,         -3.0),
      (    0.0,         -3.0,          0.0,          0.0),
      (    1.0,          0.0,          0.0,          0.0),
      (  -35.0,        -48.0,        -21.0,         15.0),
      (   -3.0,         -5.0,         -2.0,          1.0),
      (    6.0,          0.0,          0.0,         -3.0),
      (    3.0,          0.0,          0.0,         -1.0),
      (    0.0,         -5.0,          0.0,          0.0),
      (   12.0,         55.0,         29.0,         -6.0),
      (    0.0,          5.0,          3.0,          0.0),
      ( -598.0,          0.0,          0.0,          0.0),
      (   -3.0,        -13.0,         -7.0,          1.0),
      (   -5.0,         -7.0,         -3.0,          2.0),
      (    3.0,          0.0,          0.0,         -1.0),
      (    5.0,         -7.0,          0.0,          0.0),
      (    4.0,          0.0,          0.0,         -2.0),
      (   16.0,         -6.0,          0.0,          0.0),
      (    8.0,         -3.0,          0.0,          0.0),
      (    8.0,        -31.0,        -16.0,         -4.0),
      (    0.0,          3.0,          1.0,          0.0),
      (  113.0,          0.0,          0.0,        -49.0),
      (    0.0,        -24.0,        -10.0,          0.0),
      (    4.0,          0.0,          0.0,         -2.0),
      (   27.0,          0.0,          0.0,          0.0),
      (   -3.0,          0.0,          0.0,          1.0),
      (    0.0,         -4.0,         -2.0,          0.0),
      (    5.0,          0.0,          0.0,         -2.0),
      (    0.0,         -3.0,          0.0,          0.0),
      (  -13.0,          0.0,          0.0,          6.0),
      (    5.0,          0.0,          0.0,         -2.0),
      (  -18.0,        -10.0,         -4.0,          8.0),
      (   -4.0,        -28.0,          0.0,          0.0),
      (   -5.0,          6.0,          3.0,          2.0),
      (   -3.0,          0.0,          0.0,          1.0),
      (   -5.0,         -9.0,         -4.0,          2.0),
      (   17.0,          0.0,          0.0,         -7.0),
      (   11.0,          4.0,          0.0,          0.0),
      (    0.0,         -6.0,         -2.0,          0.0),
      (   83.0,         15.0,          0.0,          0.0),
      (   -4.0,          0.0,          0.0,          2.0),
      (    0.0,       -114.0,        -49.0,          0.0),
      (  117.0,          0.0,          0.0,        -51.0),
      (   -5.0,         19.0,         10.0,          2.0),
      (   -3.0,          0.0,          0.0,          0.0),
      (   -3.0,          0.0,          0.0,          2.0),
      (    0.0,         -3.0,         -1.0,          0.0),
      (    3.0,          0.0,          0.0,          0.0),
      (    0.0,         -6.0,         -2.0,          0.0),
      (  393.0,          3.0,          0.0,          0.0),
      (   -4.0,         21.0,         11.0,          2.0),
      (   -6.0,          0.0,         -1.0,          3.0),
      (   -3.0,          8.0,          4.0,          1.0),
      (    8.0,          0.0,          0.0,          0.0),
      (   18.0,        -29.0,        -13.0,         -8.0),
      (    8.0,         34.0,         18.0,         -4.0),
      (   89.0,          0.0,          0.0,          0.0),
      (    3.0,         12.0,          6.0,         -1.0),
      (   54.0,        -15.0,         -7.0,        -24.0),
      (    0.0,          3.0,          0.0,          0.0),
      (    3.0,          0.0,          0.0,         -1.0),
      (    0.0,         35.0,          0.0,          0.0),
      ( -154.0,        -30.0,        -13.0,         67.0),
      (   15.0,          0.0,          0.0,          0.0),
      (    0.0,          4.0,          2.0,          0.0),
      (    0.0,          9.0,          0.0,          0.0),
      (   80.0,        -71.0,        -31.0,        -35.0),
      (    0.0,        -20.0,         -9.0,          0.0),
      (   11.0,          5.0,          2.0,         -5.0),
      (   61.0,        -96.0,        -42.0,        -27.0),
      (   14.0,          9.0,          4.0,         -6.0),
      (  -11.0,         -6.0,         -3.0,          5.0),
      (    0.0,         -3.0,         -1.0,          0.0),
      (  123.0,       -415.0,       -180.0,        -53.0),
      (    0.0,          0.0,          0.0,        -35.0),
      (   -5.0,          0.0,          0.0,          0.0),
      (    7.0,        -32.0,        -17.0,         -4.0),
      (    0.0,         -9.0,         -5.0,          0.0),
      (    0.0,         -4.0,          2.0,          0.0),
      (  -89.0,          0.0,          0.0,         38.0),
      (    0.0,        -86.0,        -19.0,         -6.0),
      (    0.0,          0.0,        -19.0,          6.0),
      ( -123.0,       -416.0,       -180.0,         53.0),
      (    0.0,         -3.0,         -1.0,          0.0),
      (   12.0,         -6.0,         -3.0,         -5.0),
      (  -13.0,          9.0,          4.0,          6.0),
      (    0.0,        -15.0,         -7.0,          0.0),
      (    3.0,          0.0,          0.0,         -1.0),
      (  -62.0,        -97.0,        -42.0,         27.0),
      (  -11.0,          5.0,          2.0,          5.0),
      (    0.0,        -19.0,         -8.0,          0.0),
      (   -3.0,          0.0,          0.0,          1.0),
      (    0.0,          4.0,          2.0,          0.0),
      (    0.0,          3.0,          0.0,          0.0),
      (    0.0,          4.0,          2.0,          0.0),
      (  -85.0,        -70.0,        -31.0,         37.0),
      (  163.0,        -12.0,         -5.0,        -72.0),
      (  -63.0,        -16.0,         -7.0,         28.0),
      (  -21.0,        -32.0,        -14.0,          9.0),
      (    0.0,         -3.0,         -1.0,          0.0),
      (    3.0,          0.0,          0.0,         -2.0),
      (    0.0,          8.0,          0.0,          0.0),
      (    3.0,         10.0,          4.0,         -1.0),
      (    3.0,          0.0,          0.0,         -1.0),
      (    0.0,         -7.0,         -3.0,          0.0),
      (    0.0,         -4.0,         -2.0,          0.0),
      (    6.0,         19.0,          0.0,          0.0),
      (    5.0,       -173.0,        -75.0,         -2.0),
      (    0.0,         -7.0,         -3.0,          0.0),
      (    7.0,        -12.0,         -5.0,         -3.0),
      (   -3.0,          0.0,          0.0,          2.0),
      (    3.0,         -4.0,         -2.0,         -1.0),
      (   74.0,          0.0,          0.0,        -32.0),
      (   -3.0,         12.0,          6.0,          2.0),
      (   26.0,        -14.0,         -6.0,        -11.0),
      (   19.0,          0.0,          0.0,         -8.0),
      (    6.0,         24.0,         13.0,         -3.0),
      (   83.0,          0.0,          0.0,          0.0),
      (    0.0,        -10.0,         -5.0,          0.0),
      (   11.0,         -3.0,         -1.0,         -5.0),
      (    3.0,          0.0,          1.0,         -1.0),
      (    3.0,          0.0,          0.0,         -1.0),
      (   -4.0,          0.0,          0.0,          0.0),
      (    5.0,        -23.0,        -12.0,         -3.0),
      ( -339.0,          0.0,          0.0,        147.0),
      (    0.0,        -10.0,         -5.0,          0.0),
      (    5.0,          0.0,          0.0,          0.0),
      (    3.0,          0.0,          0.0,         -1.0),
      (    0.0,         -4.0,         -2.0,          0.0),
      (   18.0,         -3.0,          0.0,          0.0),
      (    9.0,        -11.0,         -5.0,         -4.0),
      (   -8.0,          0.0,          0.0,          4.0),
      (    3.0,          0.0,          0.0,         -1.0),
      (    0.0,          9.0,          0.0,          0.0),
      (    6.0,         -9.0,         -4.0,         -2.0),
      (   -4.0,        -12.0,          0.0,          0.0),
      (   67.0,        -91.0,        -39.0,        -29.0),
      (   30.0,        -18.0,         -8.0,        -13.0),
      (    0.0,          0.0,          0.0,          0.0),
      (    0.0,       -114.0,        -50.0,          0.0),
      (    0.0,          0.0,          0.0,         23.0),
      (  517.0,         16.0,          7.0,       -224.0),
      (    0.0,         -7.0,         -3.0,          0.0),
      (  143.0,         -3.0,         -1.0,        -62.0),
      (   29.0,          0.0,          0.0,        -13.0),
      (   -4.0,          0.0,          0.0,          2.0),
      (   -6.0,          0.0,          0.0,          3.0),
      (    5.0,         12.0,          5.0,         -2.0),
      (  -25.0,          0.0,          0.0,         11.0),
      (   -3.0,          0.0,          0.0,          1.0),
      (    0.0,          4.0,          2.0,          0.0),
      (  -22.0,         12.0,          5.0,         10.0),
      (   50.0,          0.0,          0.0,        -22.0),
      (    0.0,          7.0,          4.0,          0.0),
      (    0.0,          3.0,          1.0,          0.0),
      (   -4.0,          4.0,          2.0,          2.0),
      (   -5.0,        -11.0,         -5.0,          2.0),
      (    0.0,          4.0,          2.0,          0.0),
      (    4.0,         17.0,          9.0,         -2.0),
      (   59.0,          0.0,          0.0,          0.0),
      (    0.0,         -4.0,         -2.0,          0.0),
      (   -8.0,          0.0,          0.0,          4.0),
      (   -3.0,          0.0,          0.0,          0.0),
      (    4.0,        -15.0,         -8.0,         -2.0),
      (  370.0,         -8.0,          0.0,       -160.0),
      (    0.0,          0.0,         -3.0,          0.0),
      (    0.0,          3.0,          1.0,          0.0),
      (   -6.0,          3.0,          1.0,          3.0),
      (    0.0,          6.0,          0.0,          0.0),
      (  -10.0,          0.0,          0.0,          4.0),
      (    0.0,          9.0,          4.0,          0.0),
      (    4.0,         17.0,          7.0,         -2.0),
      (   34.0,          0.0,          0.0,        -15.0),
      (    0.0,          5.0,          3.0,          0.0),
      (   -5.0,          0.0,          0.0,          2.0),
      (  -37.0,         -7.0,         -3.0,         16.0),
      (    3.0,         13.0,          7.0,         -2.0),
      (   40.0,          0.0,          0.0,          0.0),
      (    0.0,         -3.0,         -2.0,          0.0),
      ( -184.0,         -3.0,         -1.0,         80.0),
      (   -3.0,          0.0,          0.0,          1.0),
      (   -3.0,          0.0,          0.0,          0.0),
      (    0.0,        -10.0,         -6.0,         -1.0),
      (   31.0,         -6.0,          0.0,        -13.0),
      (   -3.0,        -32.0,        -14.0,          1.0),
      (   -7.0,          0.0,          0.0,          3.0),
      (    0.0,         -8.0,         -4.0,          0.0),
      (    3.0,         -4.0,          0.0,          0.0),
      (    0.0,          4.0,          0.0,          0.0),
      (    0.0,          3.0,          1.0,          0.0),
      (   19.0,        -23.0,        -10.0,          2.0),
      (    0.0,          0.0,          0.0,        -10.0),
      (    0.0,          3.0,          2.0,          0.0),
      (    0.0,          9.0,          5.0,         -1.0),
      (   28.0,          0.0,          0.0,          0.0),
      (    0.0,         -7.0,         -4.0,          0.0),
      (    8.0,         -4.0,          0.0,         -4.0),
      (    0.0,          0.0,         -2.0,          0.0),
      (    0.0,          3.0,          0.0,          0.0),
      (   -3.0,          0.0,          0.0,          1.0),
      (   -9.0,          0.0,          1.0,          4.0),
      (    3.0,         12.0,          5.0,         -1.0),
      (   17.0,         -3.0,         -1.0,          0.0),
      (    0.0,          7.0,          4.0,          0.0),
      (   19.0,          0.0,          0.0,          0.0),
      (    0.0,         -5.0,         -3.0,          0.0),
      (   14.0,         -3.0,          0.0,         -1.0),
      (    0.0,          0.0,         -1.0,          0.0),
      (    0.0,          0.0,          0.0,         -5.0),
      (    0.0,          5.0,          3.0,          0.0),
      (   13.0,          0.0,          0.0,          0.0),
      (    0.0,         -3.0,         -2.0,          0.0),
      (    2.0,          9.0,          4.0,          3.0),
      (    0.0,          0.0,          0.0,         -4.0),
      (    8.0,          0.0,          0.0,          0.0),
      (    0.0,          4.0,          2.0,          0.0),
      (    6.0,          0.0,          0.0,         -3.0),
      (    6.0,          0.0,          0.0,          0.0),
      (    0.0,          3.0,          1.0,          0.0),
      (    5.0,          0.0,          0.0,         -2.0),
      (    3.0,          0.0,          0.0,         -1.0),
      (   -3.0,          0.0,          0.0,          0.0),
      (    6.0,          0.0,          0.0,          0.0),
      (    7.0,          0.0,          0.0,          0.0),
      (   -4.0,          0.0,          0.0,          0.0),
      (    4.0,          0.0,          0.0,          0.0),
      (    6.0,          0.0,          0.0,          0.0),
      (    0.0,         -4.0,          0.0,          0.0),
      (    0.0,         -4.0,          0.0,          0.0),
      (    5.0,          0.0,          0.0,          0.0),
      (   -3.0,          0.0,          0.0,          0.0),
      (    4.0,          0.0,          0.0,          0.0),
      (   -5.0,          0.0,          0.0,          0.0),
      (    4.0,          0.0,          0.0,          0.0),
      (    0.0,          3.0,          0.0,          0.0),
      (   13.0,          0.0,          0.0,          0.0),
      (   21.0,         11.0,          0.0,          0.0),
      (    0.0,         -5.0,          0.0,          0.0),
      (    0.0,         -5.0,         -2.0,          0.0),
      (    0.0,          5.0,          3.0,          0.0),
      (    0.0,         -5.0,          0.0,          0.0),
      (   -3.0,          0.0,          0.0,          2.0),
      (   20.0,         10.0,          0.0,          0.0),
      (  -34.0,          0.0,          0.0,          0.0),
      (  -19.0,          0.0,          0.0,          0.0),
      (    3.0,          0.0,          0.0,         -2.0),
      (   -3.0,          0.0,          0.0,          1.0),
      (   -6.0,          0.0,          0.0,          3.0),
      (   -4.0,          0.0,          0.0,          0.0),
      (    3.0,          0.0,          0.0,          0.0),
      (    3.0,          0.0,          0.0,          0.0),
      (    4.0,          0.0,          0.0,          0.0),
      (    3.0,          0.0,          0.0,         -1.0),
      (    6.0,          0.0,          0.0,         -3.0),
      (   -8.0,          0.0,          0.0,          3.0),
      (    0.0,          3.0,          1.0,          0.0),
      (   -3.0,          0.0,          0.0,          0.0),
      (    0.0,         -3.0,         -2.0,          0.0),
      (  126.0,        -63.0,        -27.0,        -55.0),
      (   -5.0,          0.0,          1.0,          2.0),
      (   -3.0,         28.0,         15.0,          2.0),
      (    5.0,          0.0,          1.0,         -2.0),
      (    0.0,          9.0,          4.0,          1.0),
      (    0.0,          9.0,          4.0,         -1.0),
      ( -126.0,        -63.0,        -27.0,         55.0),
      (    3.0,          0.0,          0.0,         -1.0),
      (   21.0,        -11.0,         -6.0,        -11.0),
      (    0.0,         -4.0,          0.0,          0.0),
      (  -21.0,        -11.0,         -6.0,         11.0),
      (   -3.0,          0.0,          0.0,          1.0),
      (    0.0,          3.0,          1.0,          0.0),
      (    8.0,          0.0,          0.0,         -4.0),
      (   -6.0,          0.0,          0.0,          3.0),
      (   -3.0,          0.0,          0.0,          1.0),
      (    3.0,          0.0,          0.0,         -1.0),
      (   -3.0,          0.0,          0.0,          1.0),
      (   -5.0,          0.0,          0.0,          2.0),
      (   24.0,        -12.0,         -5.0,        -11.0),
      (    0.0,          3.0,          1.0,          0.0),
      (    0.0,          3.0,          1.0,          0.0),
      (    0.0,          3.0,          2.0,          0.0),
      (  -24.0,        -12.0,         -5.0,         10.0),
      (    4.0,          0.0,         -1.0,         -2.0),
      (   13.0,          0.0,          0.0,         -6.0),
      (    7.0,          0.0,          0.0,         -3.0),
      (    3.0,          0.0,          0.0,         -1.0),
      (    3.0,          0.0,          0.0,         -1.0),
      ))

nutation_coefficients_longitude = nutation_coefficients[:,:2]
nutation_coefficients_obliquity = nutation_coefficients[:,2:]

########NEW FILE########
__FILENAME__ = positionlib
"""Classes representing different kinds of astronomical position."""

from numpy import arcsin, arctan2, array, cos, einsum, pi, sin

from .constants import TAU
from .functions import length_of, spin_x
from .earthlib import (compute_limb_angle, geocentric_position_and_velocity,
                       sidereal_time)
from .functions import dots
from .relativity import add_aberration, add_deflection
from .timelib import JulianDate, takes_julian_date
from .units import (Distance, Velocity, Angle, HourAngle, SignedAngle,
                    interpret_longitude, interpret_latitude)

ecliptic_obliquity = (23 + (26/60.) + (21.406/3600.)) * pi / 180.
quarter_tau = 0.25 * TAU

class ICRS(object):
    """An x,y,z position whose axes are oriented to the ICRS system.

    The ICRS is a permanent coordinate system that has superseded the
    old series of equinox-based systems like B1900, B1950, and J2000.

    """
    geocentric = True  # TODO: figure out what this meant and get rid of it

    def __init__(self, position_AU, velocity_AU_per_d=None, jd=None):
        self.jd = jd
        self.position = Distance(position_AU)
        if velocity_AU_per_d is None:
            self.velocity = None
        else:
            self.velocity = Velocity(velocity_AU_per_d)

    def __repr__(self):
        return '<%s position x,y,z AU%s%s>' % (
            self.__class__.__name__,
            '' if (self.velocity is None) else
            ' and velocity xdot,ydot,zdot AU/day',
            '' if self.jd is None else ' at date jd',
            )

    def __sub__(self, body):
        """Subtract two ICRS vectors to produce a third."""
        p = self.position.AU - body.position.AU
        if self.velocity is None or body.velocity is None:
            v = None
        else:
            v = body.velocity.AU_per_d - self.velocity.AU_per_d
        return ICRS(p, v, self.jd)

    def observe(self, body):
        return body.observe_from(self)

    def radec(self, epoch=None):
        position_AU = self.position.AU
        if epoch is not None:
            if isinstance(epoch, JulianDate):
                pass
            elif isinstance(epoch, float):
                epoch = JulianDate(tt=epoch)
            elif epoch == 'date':
                epoch = self.jd
            else:
                raise ValueError('the epoch= must be a Julian date,'
                                 ' a floating point Terrestrial Time (TT),'
                                 ' or the string "date" for epoch-of-date')
            position_AU = einsum('ij...,j...->i...', epoch.M, position_AU)
        r_AU, dec, ra = to_polar(position_AU)
        return HourAngle(radians=ra), SignedAngle(radians=dec), Distance(r_AU)

# class to represent a point in the IC reference frame
class ICRCoordinates:
    def __init__(self, x, y, z):
        self.x = x
        self.y = y
        self.z = z

    def equalTo(self, other):
        # TODO: override ==, and add epsilons here
        return (self.x == other.x) and (self.y == other.y) and (self.z == other.z)

    def __repr__(self):
        return '(%s, %s, %s)' % (self.x, self.y, self.z)

class Topos(object):

    def __init__(self, latitude, longitude, elevation=0.,
                 temperature=10.0, pressure=1010.0):
        self.latitude = lat = interpret_latitude(latitude)
        self.longitude = lon = interpret_longitude(longitude)
        self.elevation = elevation

        sinlat = sin(lat)
        coslat = cos(lat)
        sinlon = sin(lon)
        coslon = cos(lon)

        self.up = array([coslat * coslon, coslat * sinlon, sinlat])
        self.north = array([-sinlat * coslon, -sinlat * sinlon, coslat])
        self.west = array([sinlon, -coslon, 0.0])

    @takes_julian_date
    def __call__(self, jd):
        """Compute where this Earth location was in space on a given date."""
        e = self.ephemeris.earth(jd)
        tpos_AU, tvel_AU_per_d = geocentric_position_and_velocity(self, jd)
        t = ToposICRS(e.position.AU + tpos_AU,
                      e.velocity.AU_per_d + tvel_AU_per_d,
                      jd)
        t.rGCRS = tpos_AU
        t.vGCRS = tvel_AU_per_d
        t.topos = self
        t.ephemeris = self.ephemeris
        return t

class ToposICRS(ICRS):
    """In ICRS, right?"""

    geocentric = False

class Barycentric(ICRS):
    """An ICRS x,y,z position referenced to the Solar System barycenter."""

class Astrometric(ICRS):
    """An astrometric position as an x,y,z vector in the ICRS.

    The *astrometric position* of a body is its position relative to an
    observer, adjusted for light-time delay: the position of the body
    back when it emitted (or reflected) the light or other radiation
    that is just now reaching the observer's eyes or telescope.  This is
    always a difference between two BCRS vectors.

    """
    def apparent(self):
        """Return the corresponding apparent position."""
        jd = self.jd
        position_AU = self.position.AU.copy()
        observer = self.observer

        if observer.geocentric:
            include_earth_deflection = array((False,))
        else:
            limb_angle, nadir_angle = compute_limb_angle(
                position_AU, observer.position.AU)
            include_earth_deflection = limb_angle >= 0.8

        add_deflection(position_AU, observer.position.AU, observer.ephemeris,
                       jd.tdb, include_earth_deflection)
        add_aberration(position_AU, observer.velocity.AU_per_d, self.lighttime)

        a = Apparent(position_AU, jd=jd)
        a.observer = self.observer
        return a

class Apparent(ICRS):
    """An apparent position as an x,y,z vector in the GCRS.

    The *apparent position* of a body is its position relative to an
    observer, adjusted not only for the light-time delay between the
    body and an observer (which was already accounted for in the
    object's astrometric position), but also adjusted for deflection
    (its light rays bending as they pass large masses like the Sun or
    Jupiter) and aberration (light slanting because of the observer's
    motion through space).

    Included in aberration is the relativistic transformation that takes
    the position out of the BCRS centered on the solar system barycenter
    and into the GCRS centered on the Earth.

    If the observer was a planet or satellite with its own orbit around
    the Sun, then this apparent position is not really a GCRS position,
    but belongs to a GCRS-like system centered on that observer instead.

    """
    def altaz(self):
        """Return the position as a tuple ``(alt, az, d)``.

        `alt` - Altitude in degrees above the horizon.
        `az` - Azimuth angle east around the horizon from due-north.
        `d` - Distance to the object.

        """
        try:
            topos = self.observer.topos
            uze = topos.up
            une = topos.north
            uwe = topos.west
        except AttributeError:
            raise ValueError('to compute an apparent position, you must'
                             ' observe from a specific Earth location that'
                             ' you specify using a Topos instance')

        # TODO: wobble

        gast = sidereal_time(self.jd, use_eqeq=True)
        spin = spin_x(-gast * TAU / 24.0)
        uz = einsum('i...,ij...->j...', uze, spin)
        un = einsum('i...,ij...->j...', une, spin)
        uw = einsum('i...,ij...->j...', uwe, spin)

        p = einsum('ij...,j...->i...', self.jd.M, self.position.AU)

        pz = dots(p, uz)
        pn = dots(p, un)
        pw = dots(p, uw)

        position_AU = array([pn, -pw, pz])

        r_AU, alt, az = to_polar(position_AU)
        return Angle(radians=alt), Angle(radians=az), Distance(r_AU)


def to_polar(xyz):
    """Convert ``[x y z]`` into spherical coordinates ``(r, theta, phi)``.

    ``r`` - vector length
    ``theta`` - angle above (+) or below (-) the xy-plane
    ``phi`` - angle around the z-axis

    The order of the three return values is intended to match ISO 31-11.

    """
    r = length_of(xyz)
    theta = arcsin(xyz[2] / r)
    phi = arctan2(-xyz[1], -xyz[0]) + pi
    return r, theta, phi

def ITRF_to_GCRS(jd, rITRF):  # todo: velocity

    # Todo: wobble

    gast = sidereal_time(jd, use_eqeq=True)
    spin = spin_x(-gast * TAU / 24.0)
    position = einsum('i...,ij...->j...', array(rITRF), spin)
    return einsum('ij...,j...->i...', jd.MT, position)

########NEW FILE########
__FILENAME__ = precessionlib
from numpy import array, cos, sin

from .constants import ASEC2RAD, T0

def compute_precession(jd_tdb):
    """Return the rotation matrices for precessing to an array of epochs.

    `jd_tdb` - array of TDB Julian dates

    The array returned has the shape `(3, 3, n)` where `n` is the number
    of dates that have been provided as input.

    """
    eps0 = 84381.406

    # 't' is time in TDB centuries.

    t = (jd_tdb - T0) / 36525.0

    # Numerical coefficients of psi_a, omega_a, and chi_a, along with
    # epsilon_0, the obliquity at J2000.0, are 4-angle formulation from
    # Capitaine et al. (2003), eqs. (4), (37), & (39).

    psia   = ((((-    0.0000000951  * t
                 +    0.000132851 ) * t
                 -    0.00114045  ) * t
                 -    1.0790069   ) * t
                 + 5038.481507    ) * t

    omegaa = ((((+    0.0000003337  * t
                 -    0.000000467 ) * t
                 -    0.00772503  ) * t
                 +    0.0512623   ) * t
                 -    0.025754    ) * t + eps0

    chia   = ((((-    0.0000000560  * t
                 +    0.000170663 ) * t
                 -    0.00121197  ) * t
                 -    2.3814292   ) * t
                 +   10.556403    ) * t

    eps0 = eps0 * ASEC2RAD
    psia = psia * ASEC2RAD
    omegaa = omegaa * ASEC2RAD
    chia = chia * ASEC2RAD

    sa = sin(eps0)
    ca = cos(eps0)
    sb = sin(-psia)
    cb = cos(-psia)
    sc = sin(-omegaa)
    cc = cos(-omegaa)
    sd = sin(chia)
    cd = cos(chia)

    # Compute elements of precession rotation matrix equivalent to
    # R3(chi_a) R1(-omega_a) R3(-psi_a) R1(epsilon_0).

    rot3 = array(((cd * cb - sb * sd * cc,
                   cd * sb * ca + sd * cc * cb * ca - sa * sd * sc,
                   cd * sb * sa + sd * cc * cb * sa + ca * sd * sc),
                  (-sd * cb - sb * cd * cc,
                   -sd * sb * ca + cd * cc * cb * ca - sa * cd * sc,
                   -sd * sb * sa + cd * cc * cb * sa + ca * cd * sc),
                  (sb * sc,
                   -sc * cb * ca - sa * cc,
                   -sc * cb * sa + cc * ca)))

    return rot3

########NEW FILE########
__FILENAME__ = relativity
from numpy import abs, einsum, sqrt, where

from .constants import C, AU, C_AUDAY, GS
from .functions import dots, length_of


deflectors = ['sun', 'jupiter', 'saturn', 'moon', 'venus', 'uranus', 'neptune']
rmasses = {
    # earth-moon barycenter: 328900.561400
    'mercury': 6023600.0,
    'venus': 408523.71,
    'earth': 332946.050895,
    'mars': 3098708.0,
    'jupiter': 1047.3486,
    'saturn': 3497.898,
    'uranus': 22902.98,
    'neptune': 19412.24,
    'pluto': 135200000.0,
    'sun': 1.0,
    'moon': 27068700.387534,
    }

def add_deflection(position, observer, ephemeris, jd_tdb,
                   include_earth_deflection, count=3):
    """Update `position` for how solar system masses will deflect its light.

    Given the ICRS `position` [x,y,z] of an object (AU) that is being
    viewed from the `observer` also expressed as [x,y,z], and given an
    ephemeris that can be used to determine solar system body positions,
    and given the time `jd` and Boolean `apply_earth` indicating whether
    to worry about the effect of Earth's mass, and a `count` of how many
    major solar system bodies to worry about, this function updates
    `position` in-place to show how the masses in the solar system will
    deflect its image.

    """
    # Compute light-time to observed object.

    tlt = length_of(position) / C_AUDAY

    # Cycle through gravitating bodies.

    for name in deflectors[:count]:

        # Get position of gravitating body wrt ss barycenter at time 'jd_tdb'.

        bposition = ephemeris._position(name, jd_tdb)

        # Get position of gravitating body wrt observer at time 'jd_tdb'.

        gpv = bposition - observer

        # Compute light-time from point on incoming light ray that is closest
        # to gravitating body.

        dlt = light_time_difference(position, gpv)

        # Get position of gravitating body wrt ss barycenter at time when
        # incoming photons were closest to it.

        tclose = jd_tdb

        # if dlt > 0.0:
        #     tclose = jd - dlt

        tclose = where(dlt > 0.0, jd_tdb - dlt, tclose)
        tclose = where(tlt < dlt, jd_tdb - tlt, tclose)

        # if tlt < dlt:
        #     tclose = jd - tlt

        bposition = ephemeris._position(name, tclose)
        rmass = rmasses[name]
        _add_deflection(position, observer, bposition, rmass)

    # If observer is not at geocenter, add in deflection due to Earth.

    if include_earth_deflection.any():
        bposition = ephemeris._position('earth', tclose)
        rmass = rmasses['earth']
        _add_deflection(position, observer, bposition, rmass)

#

def light_time_difference(position, observer_position):
    """Returns the difference in light-time, for a star,
      between the barycenter of the solar system and the observer (or
      the geocenter).

    """
    # From 'pos1', form unit vector 'u1' in direction of star or light
    # source.

    dis = length_of(position)
    u1 = position / dis

    # Light-time returned is the projection of vector 'pos_obs' onto the
    # unit vector 'u1' (formed from 'pos1'), divided by the speed of light.

    diflt = einsum('a...,a...', u1, observer_position) / C_AUDAY
    return diflt

#

def _add_deflection(position, observer, deflector, rmass):
    """Correct a position vector for how one particular mass deflects light.

    Given the ICRS `position` [x,y,z] of an object (AU) together with
    the positions of an `observer` and a `deflector` of reciprocal mass
    `rmass`, this function updates `position` in-place to show how much
    the presence of the deflector will deflect the image of the object.

    """
    # Construct vector 'pq' from gravitating body to observed object and
    # construct vector 'pe' from gravitating body to observer.

    pq = observer + position - deflector
    pe = observer - deflector

    # Compute vector magnitudes and unit vectors.

    pmag = length_of(position)
    qmag = length_of(pq)
    emag = length_of(pe)

    phat = position / pmag
    qhat = pq / qmag
    ehat = pe / emag

    # Compute dot products of vectors.

    pdotq = dots(phat, qhat)
    qdote = dots(qhat, ehat)
    edotp = dots(ehat, phat)

    # If gravitating body is observed object, or is on a straight line
    # toward or away from observed object to within 1 arcsec, deflection
    # is set to zero set 'pos2' equal to 'pos1'.

    make_no_correction = abs(edotp) > 0.99999999999

    # Compute scalar factors.

    fac1 = 2.0 * GS / (C * C * emag * AU * rmass)
    fac2 = 1.0 + qdote

    # Correct position vector.

    position += where(make_no_correction, 0.0,
                      fac1 * (pdotq * ehat - edotp * qhat) / fac2 * pmag)

#

def add_aberration(position, velocity, lighttime):
    """Correct a relative position vector for aberration of light.

    Given the relative `position` [x,y,z] of an object (AU) from a
    particular observer, the `velocity` [dx,dy,dz] at which the observer
    is traveling (AU/day), and the light propagation delay `lighttime`
    to the object (days), this function updates `position` in-place to
    give the object's apparent position due to the aberration of light.

    """
    p1mag = lighttime * C_AUDAY
    vemag = length_of(velocity)
    beta = vemag / C_AUDAY
    dot = dots(position, velocity)

    cosd = dot / (p1mag * vemag)
    gammai = sqrt(1.0 - beta * beta)
    p = beta * cosd
    q = (1.0 + p / (1.0 + gammai)) * lighttime
    r = 1.0 + p

    position *= gammai
    position += q * velocity
    position /= r

########NEW FILE########
__FILENAME__ = sgp4lib
"""An object representing an Earth-orbiting satellite."""

from numpy import array, cross
from sgp4.earth_gravity import wgs72
from sgp4.io import twoline2rv
from sgp4.propagation import sgp4

from .constants import AU_KM, DAY_S, T0, tau
from .functions import rot_x, rot_y, rot_z
from .positionlib import Apparent, ITRF_to_GCRS

_minutes_per_day = 1440.

class EarthSatellite(object):
    """An Earth satellite loaded from a TLE file and propagated with SGP4."""

    def __init__(self, lines, earth):
        self._earth = earth
        self._sgp4_satellite = twoline2rv(*lines[-2:], whichconst=wgs72)

    def _position_and_velocity_TEME_km(self, jd):
        """Return the raw true equator mean equinox (TEME) vectors from SGP4.

        Returns a tuple of NumPy arrays ``([x y z], [xdot ydot zdot])``
        expressed in kilometers and kilometers per second.

        """
        minutes_past_epoch = (jd.ut1 - self._sgp4_satellite.jdsatepoch) * 1440.
        position, velocity = sgp4(self._sgp4_satellite, minutes_past_epoch)
        return (array(position), array(velocity))

    def _compute_GCRS(self, jd):
        """Compute where satellite is in space on a given date."""

        rTEME, vTEME = self._position_and_velocity_TEME_km(jd)
        rTEME /= AU_KM
        vTEME /= AU_KM
        vTEME *= DAY_S

        rITRF, vITRF = TEME_to_ITRF(jd.ut1, rTEME, vTEME)
        rGCRS = ITRF_to_GCRS(jd, rITRF)
        vGCRS = array((0.0, 0.0, 0.0))  # todo: someday also compute vGCRS?

        return rGCRS, vGCRS

    def observe_from(self, observer):
        # TODO: what if someone on Mars tries to look at the ISS?

        rGCRS, vGCRS = self._compute_GCRS(observer.jd)
        g = Apparent(rGCRS - observer.rGCRS,
                     vGCRS - observer.vGCRS,
                     observer.jd)
        g.observer = observer
        # g.distance = euclidian_distance
        return g


_second = 1.0 / (24.0 * 60.0 * 60.0)

def theta_GMST1982(jd_ut1):
    """Return the angle of Greenwich Mean Standard Time 1982 given the JD.

    This angle defines the difference between the idiosyncratic True
    Equator Mean Equinox (TEME) frame of reference used by SGP4 and the
    more standard Pseudo Earth Fixed (PEF) frame of reference.

    From AIAA 2006-6753 Appendix C.

    """
    t = (jd_ut1 - T0) / 36525.0
    g = 67310.54841 + (8640184.812866 + (0.093104 + (-6.2e-6) * t) * t) * t
    dg = 8640184.812866 + (0.093104 * 2.0 + (-6.2e-6 * 3.0) * t) * t
    theta = (jd_ut1 % 1.0 + g * _second % 1.0) * tau
    theta_dot = (1.0 + dg * _second / 36525.0) * tau
    return theta, theta_dot

def TEME_to_ITRF(jd_ut1, rTEME, vTEME, xp=0.0, yp=0.0):
    """Convert TEME position and velocity into standard ITRS coordinates.

    This converts a position and velocity vector in the idiosyncratic
    True Equator Mean Equinox (TEME) frame of reference used by the SGP4
    theory into vectors into the more standard ITRS frame of reference.
    The velocity should be provided in units per day, not per second.

    From AIAA 2006-6753 Appendix C.

    """
    theta, theta_dot = theta_GMST1982(jd_ut1)
    angular_velocity = array([0, 0, -theta_dot])
    R = rot_z(-theta)
    rPEF = (R).dot(rTEME)
    vPEF = (R).dot(vTEME) + cross(angular_velocity, rPEF)
    if xp == 0.0 and yp == 0.0:
        rITRF = rPEF
        vITRF = vPEF
    else:
        W = (rot_x(-yp)).dot(rot_y(-xp))
        rITRF = (W).dot(rPEF)
        vITRF = (W).dot(vPEF)
    return rITRF, vITRF

########NEW FILE########
__FILENAME__ = starlib
"""Python classes that represent various classes of star."""

from numpy import array, cos, outer, sin
from .constants import AU_KM, ASEC2RAD, C, C_AUDAY, DAY_S, T0
from .functions import length_of
from .positionlib import Astrometric
from .relativity import light_time_difference
from .units import Angle


class Star(object):

    def __init__(self, ra=None, dec=None, ra_hours=None, dec_degrees=None,
                 ra_mas_per_year=0.0, dec_mas_per_year=0.0,
                 parallax=0.0, radial_km_per_s=0.0):

        if ra_hours is not None:
            self.ra = Angle(hours=ra_hours)
        elif isinstance(ra, Angle):
            self.ra = ra
        else:
            raise TypeError('please provide ra_hours=h or ra=angle_object')

        if dec_degrees is not None:
            self.dec = Angle(degrees=dec_degrees)
        elif isinstance(dec, Angle):
            self.dec = dec
        else:
            raise TypeError('please provide dec_degrees=d or dec=angle_object')

        self.ra_mas_per_year = ra_mas_per_year
        self.dec_mas_per_year = dec_mas_per_year
        self.parallax = parallax
        self.radial_km_per_s = radial_km_per_s

        self._compute_vectors()

    def observe_from(self, observer):
        position, velocity = self._position, self._velocity
        jd = observer.jd
        dt = light_time_difference(position, observer.position.AU)
        if jd.shape:
            position = (outer(velocity, T0 - jd.tdb - dt).T + position).T
        else:
            position = position + velocity * (T0 - jd.tdb - dt)
        vector = position - observer.position.AU
        distance = length_of(vector)
        lighttime = distance / C_AUDAY

        g = Astrometric(vector, (observer.velocity.AU_per_d.T - velocity).T, jd)
        g.observer = observer
        g.distance = distance
        g.lighttime = lighttime
        return g

    def _compute_vectors(self):
        """Compute the star's position as an ICRS position and velocity."""

        # Use 1 gigaparsec for stars whose parallax is zero.

        parallax = self.parallax
        if parallax <= 0.0:
            parallax = 1.0e-6

        # Convert right ascension, declination, and parallax to position
        # vector in equatorial system with units of AU.

        dist = 1.0 / sin(parallax * 1.0e-3 * ASEC2RAD)
        r = self.ra.radians()
        d = self.dec.radians()
        cra = cos(r)
        sra = sin(r)
        cdc = cos(d)
        sdc = sin(d)

        self._position = array((
            dist * cdc * cra,
            dist * cdc * sra,
            dist * sdc,
            ))

        # Compute Doppler factor, which accounts for change in light
        # travel time to star.

        k = 1.0 / (1.0 - self.radial_km_per_s / C * 1000.0)

        # Convert proper motion and radial velocity to orthogonal
        # components of motion with units of AU/Day.

        pmr = self.ra_mas_per_year / (parallax * 365.25) * k
        pmd = self.dec_mas_per_year / (parallax * 365.25) * k
        rvl = self.radial_km_per_s * DAY_S / AU_KM * k

        # Transform motion vector to equatorial system.

        self._velocity = array((
            - pmr * sra - pmd * sdc * cra + rvl * cdc * cra,
              pmr * cra - pmd * sdc * sra + rvl * cdc * sra,
              pmd * cdc + rvl * sdc,
              ))

########NEW FILE########
__FILENAME__ = test_angles
from skyfield.units import Angle, HourAngle

def test_degree_rounding():
    tenth = 0.1 / 60.0 / 60.0  # of an arcsecond

    assert str(Angle(degrees=tenth * -600.75)) == '-00deg 01\' 00.1"'
    assert str(Angle(degrees=tenth * -600.25)) == '-00deg 01\' 00.0"'
    assert str(Angle(degrees=tenth * -599.75)) == '-00deg 01\' 00.0"'
    assert str(Angle(degrees=tenth * -599.25)) == '-00deg 00\' 59.9"'

    assert str(Angle(degrees=tenth * -1.75)) == '-00deg 00\' 00.2"'
    assert str(Angle(degrees=tenth * -1.25)) == '-00deg 00\' 00.1"'
    assert str(Angle(degrees=tenth * -0.75)) == '-00deg 00\' 00.1"'
    assert str(Angle(degrees=tenth * -0.25)) == '-00deg 00\' 00.0"'

    assert str(Angle(degrees=0.0)) == '00deg 00\' 00.0"'

    assert str(Angle(degrees=tenth * 0.25)) == '00deg 00\' 00.0"'
    assert str(Angle(degrees=tenth * 0.75)) == '00deg 00\' 00.1"'
    assert str(Angle(degrees=tenth * 1.25)) == '00deg 00\' 00.1"'
    assert str(Angle(degrees=tenth * 1.75)) == '00deg 00\' 00.2"'

    assert str(Angle(degrees=tenth * 599.25)) == '00deg 00\' 59.9"'
    assert str(Angle(degrees=tenth * 599.75)) == '00deg 01\' 00.0"'
    assert str(Angle(degrees=tenth * 600.25)) == '00deg 01\' 00.0"'
    assert str(Angle(degrees=tenth * 600.75)) == '00deg 01\' 00.1"'

########NEW FILE########
__FILENAME__ = test_api
"""Basic tests of the Skyfield API module and its contents."""

from skyfield import api
from skyfield import positionlib

def test_whether_planets_have_radii():
    assert api.mercury.radius.km == 2440.0
    for planet in api.nine_planets:
        assert planet.radius.km > 0.0

def test_apparent_position_class():
    p = api.earth(utc=(2014, 2, 9, 14, 50)).observe(api.mars).apparent()
    assert isinstance(p, positionlib.Apparent)

def test_astrometric_position_class():
    p = api.earth(utc=(2014, 2, 9, 14, 50)).observe(api.mars)
    assert isinstance(p, positionlib.Astrometric)

def test_planet_position_class():
    p = api.mars(utc=(2014, 2, 9, 14, 50))
    assert isinstance(p, positionlib.Barycentric)

def test_star_position_class():
    star = api.Star(ra_hours=0, dec_degrees=0)
    p = api.earth(utc=(2014, 2, 9, 15, 1)).observe(star)
    assert isinstance(p, positionlib.Astrometric)

########NEW FILE########
__FILENAME__ = test_datalib
from skyfield.io import download_file, is_days_old
from datetime import datetime, timedelta
import httpretty
import os

@httpretty.activate
def test_simple_download():
    httpretty.register_uri(httpretty.GET, 'http://foo.com/data.txt',
                           body='FOOBAR')

    download_file(url='http://foo.com/data.txt', filename='data.txt')
    assert os.path.exists('data.txt')
    assert open('data.txt', 'rb').read() == b'FOOBAR'
    os.remove('data.txt')

@httpretty.activate
def test_simple_download_days_old_0():
    httpretty.register_uri(httpretty.GET, 'http://foo.com/data.txt',
                           body='FOOBAR')
    write_file('data.txt', 'BAZ')

    download_file(url='http://foo.com/data.txt', filename='data.txt', days_old=0)
    assert open('data.txt', 'rb').read() == b'FOOBAR'
    os.remove('data.txt')

@httpretty.activate
def test_simple_download_days_old_1():
    httpretty.register_uri(httpretty.GET, 'http://foo.com/data.txt',
                           body='FOOBAR')

    write_file('data.txt', 'BAZ')

    download_file(url='http://foo.com/data.txt', filename='data.txt', days_old=1)
    assert open('data.txt', 'rb').read() == b'BAZ'
    os.remove('data.txt')

def test_is_days_old_true():
    write_file('data.txt', 'BAZ')
    d = datetime.today()-timedelta(hours=6)
    unix_ago = int(d.strftime('%s'))
    os.utime('data.txt', (unix_ago, unix_ago))

    assert is_days_old('data.txt', 1) == False
    os.remove('data.txt')

def test_is_days_old_false():
    write_file('data.txt', 'BAZ')
    d = datetime.today()-timedelta(hours=48)
    unix_ago = int(d.strftime('%s'))
    os.utime('data.txt', (unix_ago, unix_ago))

    assert is_days_old('data.txt', 1) == True
    os.remove('data.txt')

def write_file(filename, data):
    f = open(filename, 'w')
    f.write(data)
    f.close()


########NEW FILE########
__FILENAME__ = test_earth_satellites
# -*- coding: utf-8 -*-

import pytest
import sys
from datetime import datetime, timedelta
from numpy import array
from skyfield.api import earth
from skyfield.sgp4lib import EarthSatellite, TEME_to_ITRF
from skyfield.timelib import JulianDate, utc

iss_tle = ("""\
ISS (ZARYA)             \n\
1 25544U 98067A   13330.58127943  .00000814  00000-0  21834-4 0  1064\n\
2 25544  51.6484  23.7537 0001246  74.1647  18.7420 15.50540527859894\n\
""")

heavens_above_transits = """\
26 Nov	-1.7	04:55:55	29°	NNE	04:55:55	29°	NNE	04:58:45	10°	E	visible
27 Nov	0.1	04:09:07	12°	ENE	04:09:07	12°	ENE	04:09:25	10°	ENE	visible
27 Nov	-3.4	05:42:00	26°	WNW	05:43:45	86°	SW	05:47:05	10°	SE	visible
28 Nov	-2.6	04:55:15	52°	ENE	04:55:15	52°	ENE	04:58:07	10°	ESE	visible
29 Nov	0.1	04:08:35	13°	E	04:08:35	13°	E	04:08:58	10°	E	visible
29 Nov	-2.2	05:41:28	25°	WSW	05:42:30	31°	SW	05:45:28	10°	SSE	visible
30 Nov	-1.9	04:54:52	33°	SSE	04:54:52	33°	SSE	04:56:55	10°	SE	visible
01 Dec	-0.9	05:41:13	12°	SW	05:41:13	12°	SW	05:42:15	10°	SSW	visible
02 Dec	-0.4	04:54:46	10°	S	04:54:46	10°	S	04:54:49	10°	S	visible
"""
if sys.version_info < (3,):
    heavens_above_transits = heavens_above_transits.decode('utf-8')

@pytest.fixture(params=heavens_above_transits.splitlines())
def iss_transit(request):
    line = request.param
    fields = line.split()
    dt = datetime.strptime('2013 {0} {1} {6}'.format(*fields),
                           '%Y %d %b %H:%M:%S').replace(tzinfo=utc)
    altitude = float(fields[7][:-1])
    return dt, altitude

def test_iss_altitude(iss_transit):
    dt, their_altitude = iss_transit

    cst = timedelta(hours=-6) #, minutes=1)
    dt = dt - cst
    jd = JulianDate(utc=dt, delta_t=67.2091)

    lines = iss_tle.splitlines()
    s = EarthSatellite(lines, earth)
    lake_zurich = earth.topos('42.2 N', '88.1 W')
    alt, az, d = lake_zurich(jd).observe(s).altaz()
    print(dt, their_altitude, alt.degrees(), their_altitude - alt.degrees())
    assert abs(alt.degrees() - their_altitude) < 2.5  # TODO: tighten this up?

# The following tests are based on the text of
# http://www.celestrak.com/publications/AIAA/2006-6753/AIAA-2006-6753-Rev2.pdf

appendix_c_example = """\
TEME EXAMPLE
1 00005U 58002B   00179.78495062  .00000023  00000-0  28098-4 0  4753
2 00005  34.2682 348.7242 1859667 331.7664  19.3264 10.82419157413667
"""

from ..constants import DEG2RAD

arcminute = DEG2RAD / 60.0
arcsecond = arcminute / 60.0
second = 1.0 / (24.0 * 60.0 * 60.0)

def test_appendix_c_conversion_from_TEME_to_ITRF():
    rTEME = array([5094.18016210, 6127.64465950, 6380.34453270])
    vTEME = array([-4.746131487, 0.785818041, 5.531931288])
    vTEME = vTEME * 24.0 * 60.0 * 60.0  # km/s to km/day

    jd_ut1 = JulianDate(tt=(2004, 4, 6, 7, 51, 28.386 - 0.439961)).tt

    xp = -0.140682 * arcsecond
    yp = 0.333309 * arcsecond

    rITRF, vITRF = TEME_to_ITRF(jd_ut1, rTEME, vTEME, xp, yp)

    meter = 1e-3

    assert abs(-1033.47938300 - rITRF[0]) < 0.1 * meter
    assert abs(+7901.29527540 - rITRF[1]) < 0.1 * meter
    assert abs(+6380.35659580 - rITRF[2]) < 0.1 * meter

    vITRF_per_second = vITRF * second

    assert abs(-3.225636520 - vITRF_per_second[0]) < 1e-4 * meter
    assert abs(-2.872451450 - vITRF_per_second[1]) < 1e-4 * meter
    assert abs(+5.531924446 - vITRF_per_second[2]) < 1e-4 * meter

def test_appendix_c_satellite():
    lines = appendix_c_example.splitlines()
    sat = EarthSatellite(lines, earth)

    jd_epoch = sat._sgp4_satellite.jdsatepoch
    three_days_later = jd_epoch + 3.0
    jd = JulianDate(tt=three_days_later)
    jd.ut1 = array(three_days_later)

    # First, a crucial sanity check (which is, technically, a test of
    # the `sgp4` package and not of Skyfield): are the right coordinates
    # being produced by our Python SGP4 propagator for this satellite?

    rTEME, vTEME = sat._position_and_velocity_TEME_km(jd)

    assert abs(-9060.47373569 - rTEME[0]) < 1e-8
    assert abs(4658.70952502 - rTEME[1]) < 1e-8
    assert abs(813.68673153 - rTEME[2]) < 1e-8

    assert abs(-2.232832783 - vTEME[0]) < 1e-9
    assert abs(-4.110453490 - vTEME[1]) < 1e-9
    assert abs(-3.157345433 - vTEME[2]) < 1e-9

########NEW FILE########
__FILENAME__ = test_keplerian
"""Compare the output of Skyfield with the routines from NOVAS for keplerian orbiting bodies"""

import skyfield.keplerianlib
from skyfield.keplerianlib import KeplerianOrbit
from skyfield.positionlib import ICRCoordinates

from ..timelib import JulianDate, julian_date

DISTANCE_EPSILON = 0.026

def test_semimajorAxisToOrbitalPeriod():
    assert skyfield.keplerianlib.semimajorAxisToOrbitalPeriod(1) == 1
    assert skyfield.keplerianlib.semimajorAxisToOrbitalPeriod(1.523679) == 1.8807896358663763
    assert skyfield.keplerianlib.semimajorAxisToOrbitalPeriod(4.27371348392) == 8.835031547398543

def test_orbitalPeriodToSemimajorAxis():
    assert skyfield.keplerianlib.orbitalPeriodToSemimajorAxis(1) == 1
    assert skyfield.keplerianlib.orbitalPeriodToSemimajorAxis(1.8807896358663763) == 1.523679
    assert skyfield.keplerianlib.orbitalPeriodToSemimajorAxis(8.835031547398543) == 4.27371348392

def test_convergeEccentricAnomaly():
    test = skyfield.keplerianlib.convergeEccentricAnomaly(
        hoyle_8077['mean_anomaly'],
        hoyle_8077['eccentricity'],
        15
    )
    assert test == hoyle_8077['eccentric_anomaly']

def test_instantiate_8077_hoyle():
    hoyle = KeplerianOrbit( hoyle_8077['semimajor_axis'],
                            hoyle_8077['eccentricity'],
                            hoyle_8077['inclination'],
                            hoyle_8077['longitude_ascending'],
                            hoyle_8077['argument_perihelion'],
                            hoyle_8077['mean_anomaly'],
                            hoyle_8077['epoch'])

    assert hoyle != None

def test_instantiate_coordinates():
    coords = ICRCoordinates(x=500.25, y=10.76, z=0.1125)

    assert coords != None

def test_coordinatesEquivalence():
    coords_the_first = ICRCoordinates(x=500.25, y=10.76, z=0.1125)
    coords_the_second = ICRCoordinates(x=500.25, y=10.76, z=0.1125)

    assert coords_the_first.equalTo(coords_the_second)

"""
 data gotten from Horizons
date: 2456517.500000000 = A.D. 2013-Aug-13 00:00:00.0000 (CT)
expected coords (AU) 2.421251132790093E+00 -1.918893156489506E+00 -9.813409585464707E-02

 Horizon Params
Ephemeris Type [change] :   VECTORS
Target Body [change] :  Asteroid 8077 Hoyle (1986 AW2)
Coordinate Origin [change] :    Solar System Barycenter (SSB) [500@0]
Time Span [change] :    Start=2013-08-13, Stop=2013-09-12, Step=1 d
Table Settings [change] :   defaults
Display/Output [change] :   default (formatted HTML)

EPOCH=  2453995.5 ! 2006-Sep-17.00 (CT)          Residual RMS= .43359
   EC= .2110946491840378   QR= 2.077692130214496   TP= 2454360.1855338747
   OM= 135.855972529608    W=  34.4378477722205    IN= 17.25814783060462
   A= 2.633639292806857    MA= 275.9015153135912   ADIST= 3.189586455399217
   PER= 4.27408            N= .230605479           ANGMOM= .027287332
   DAN= 2.14316            DDN= 3.04671            L= 169.07331
   B= 9.658454799999999    MOID= 1.10581994        TP= 2007-Sep-16.6855338747

"""

hoyle_8077 = {
    'semimajor_axis' : 2.633278254269645,
    'eccentricity' : .2109947010748546,
    'inclination' : 17.25945395594321,
    'longitude_ascending' : 135.8512354853258,
    'argument_perihelion' : 34.46503170092878,
    'mean_anomaly' : 330.9918926661418,
    'eccentric_anomaly' : 4.0942988262501965,
    'epoch' : JulianDate(tt=(2007, 5, 14)),
}


def test_get_8077_hoyle_ecliptic_on_dev_sprint_day_2():
    hoyle = KeplerianOrbit( hoyle_8077['semimajor_axis'],
                            hoyle_8077['eccentricity'],
                            hoyle_8077['inclination'],
                            hoyle_8077['longitude_ascending'],
                            hoyle_8077['argument_perihelion'],
                            hoyle_8077['mean_anomaly'],
                            hoyle_8077['epoch'])

    date = JulianDate(tt=(2013, 8, 13))
    # print date.tt

    test = hoyle.getECLCoordinatesOnJulianDate(date)

    #print test
    epsilon = 2e-2
    assert abs(test.x - 2.421251271197979) < epsilon
    assert abs(test.y - -1.918893007049262) < epsilon
    assert abs(test.z - -0.09813403009731327) < epsilon

########NEW FILE########
__FILENAME__ = test_timelib
import numpy as np
import pytest
from skyfield.constants import DAY_S
from skyfield.timelib import JulianDate, utc
from datetime import datetime

one_second = 1.0 / DAY_S
epsilon = one_second * 42.0e-6  # 20.1e-6 is theoretical best precision


@pytest.fixture(params=['tai', 'tt', 'tdb'])
def time_parameter(request):
    return request.param

@pytest.fixture(params=[(1973, 1, 18, 1, 35, 37.5), 2441700.56640625])
def time_value(request):
    return request.param


def test_JulianDate_init(time_parameter, time_value):
    kw = {time_parameter: time_value}
    jd = JulianDate(**kw)
    assert getattr(jd, time_parameter) == 2441700.56640625

def test_building_JulianDate_from_utc_tuple_with_array_inside():
    seconds = np.arange(48.0, 58.0, 1.0)
    jd = JulianDate(utc=(1973, 12, 29, 23, 59, seconds))
    assert seconds.shape == jd.shape
    for i, second in enumerate(seconds):
        assert jd.tai[i] == JulianDate(utc=(1973, 12, 29, 23, 59, second)).tai

def test_building_JulianDate_from_naive_datetime_raises_exception():
    with pytest.raises(ValueError) as excinfo:
        JulianDate(utc=datetime(1973, 12, 29, 23, 59, 48))
    assert 'import timezone' in str(excinfo.value)

def test_building_JulianDate_from_single_utc_datetime():
    jd = JulianDate(utc=datetime(1973, 12, 29, 23, 59, 48, tzinfo=utc))
    assert jd.tai == 2442046.5

def test_building_JulianDate_from_list_of_utc_datetimes():
    jd = JulianDate(utc=[
        datetime(1973, 12, 29, 23, 59, 48, tzinfo=utc),
        datetime(1973, 12, 30, 23, 59, 48, tzinfo=utc),
        datetime(1973, 12, 31, 23, 59, 48, tzinfo=utc),
        datetime(1974, 1, 1, 23, 59, 47, tzinfo=utc),
        datetime(1974, 1, 2, 23, 59, 47, tzinfo=utc),
        datetime(1974, 1, 3, 23, 59, 47, tzinfo=utc),
        ])
    assert (jd.tai == [
        2442046.5, 2442047.5, 2442048.5, 2442049.5, 2442050.5, 2442051.5,
        ]).all()

def test_indexing_julian_date():
    jd = JulianDate(utc=(1974, 10, range(1, 6)))
    assert jd.shape == (5,)
    jd0 = jd[0]
    assert jd.tai[0] == jd0.tai
    assert jd.tt[0] == jd0.tt
    assert jd.tdb[0] == jd0.tdb
    assert jd.ut1[0] == jd0.ut1
    assert jd.delta_t == jd0.delta_t

def test_slicing_julian_date():
    jd = JulianDate(utc=(1974, 10, range(1, 6)))
    assert jd.shape == (5,)
    jd24 = jd[2:4]
    assert jd24.shape == (2,)
    assert (jd.tai[2:4] == jd24.tai).all()
    assert (jd.tt[2:4] == jd24.tt).all()
    assert (jd.tdb[2:4] == jd24.tdb).all()
    assert (jd.ut1[2:4] == jd24.ut1).all()
    assert jd.delta_t == jd24.delta_t

def test_early_utc():
    jd = JulianDate(utc=(1915, 12, 2, 3, 4, 5.6786786))
    assert abs(jd.tt - 2420833.6283317441) < epsilon
    assert jd.utc_iso() == '1915-12-02T03:04:06Z'

def test_iso_of_decimal_that_rounds_up():
    jd = JulianDate(utc=(1915, 12, 2, 3, 4, 5.6786786))
    assert jd.utc_iso(places=0) == '1915-12-02T03:04:06Z'
    assert jd.utc_iso(places=1) == '1915-12-02T03:04:05.7Z'
    assert jd.utc_iso(places=2) == '1915-12-02T03:04:05.68Z'
    assert jd.utc_iso(places=3) == '1915-12-02T03:04:05.679Z'
    assert jd.utc_iso(places=4) == '1915-12-02T03:04:05.6787Z'

def test_iso_of_decimal_that_rounds_down():
    jd = JulianDate(utc=(2014, 12, 21, 6, 3, 1.234234))
    assert jd.utc_iso(places=0) == '2014-12-21T06:03:01Z'
    assert jd.utc_iso(places=1) == '2014-12-21T06:03:01.2Z'
    assert jd.utc_iso(places=2) == '2014-12-21T06:03:01.23Z'
    assert jd.utc_iso(places=3) == '2014-12-21T06:03:01.234Z'
    assert jd.utc_iso(places=4) == '2014-12-21T06:03:01.2342Z'

def test_iso_of_leap_second_with_fraction():
    jd = JulianDate(utc=(1973, 12, 31, 23, 59, 60.12349))
    assert jd.utc_iso(places=0) == '1973-12-31T23:59:60Z'
    assert jd.utc_iso(places=1) == '1973-12-31T23:59:60.1Z'
    assert jd.utc_iso(places=2) == '1973-12-31T23:59:60.12Z'
    assert jd.utc_iso(places=3) == '1973-12-31T23:59:60.123Z'
    assert jd.utc_iso(places=4) == '1973-12-31T23:59:60.1235Z'

def test_iso_of_array_showing_whole_seconds():
    jd = JulianDate(utc=(1973, 12, 31, 23, 59, np.arange(58.75, 63.1, 0.5)))
    assert jd.utc_iso(places=0) == [
        '1973-12-31T23:59:59Z',
        '1973-12-31T23:59:59Z',
        '1973-12-31T23:59:60Z',
        '1973-12-31T23:59:60Z',
        '1974-01-01T00:00:00Z',
        '1974-01-01T00:00:00Z',
        '1974-01-01T00:00:01Z',
        '1974-01-01T00:00:01Z',
        '1974-01-01T00:00:02Z',
        ]

def test_iso_of_array_showing_fractions():
    jd = JulianDate(utc=(1973, 12, 31, 23, 59, np.arange(58.75, 63.1, 0.5)))
    assert jd.utc_iso(places=2) == [
        '1973-12-31T23:59:58.75Z',
        '1973-12-31T23:59:59.25Z',
        '1973-12-31T23:59:59.75Z',
        '1973-12-31T23:59:60.25Z',
        '1973-12-31T23:59:60.75Z',
        '1974-01-01T00:00:00.25Z',
        '1974-01-01T00:00:00.75Z',
        '1974-01-01T00:00:01.25Z',
        '1974-01-01T00:00:01.75Z',
        ]

def test_jpl_format():
    jd = JulianDate(utc=(range(-300, 301, 100), 7, 1))
    assert jd.utc_jpl() == [
        'B.C. 0301-Jul-01 00:00:00.0000 UT',
        'B.C. 0201-Jul-01 00:00:00.0000 UT',
        'B.C. 0101-Jul-01 00:00:00.0000 UT',
        'B.C. 0001-Jul-01 00:00:00.0000 UT',
        'A.D. 0100-Jul-01 00:00:00.0000 UT',
        'A.D. 0200-Jul-01 00:00:00.0000 UT',
        'A.D. 0300-Jul-01 00:00:00.0000 UT',
        ]

def test_stftime_of_single_date():
    jd = JulianDate(utc=(1973, 12, 31, 23, 59, 60))
    assert jd.utc_strftime('%Y %m %d %H %M %S') == '1973 12 31 23 59 60'

def test_stftime_of_date_array():
    jd = JulianDate(utc=(1973, 12, 31, 23, 59, np.arange(59.0, 61.1, 1.0)))
    assert jd.utc_strftime('%Y %m %d %H %M %S') == [
        '1973 12 31 23 59 59',
        '1973 12 31 23 59 60',
        '1974 01 01 00 00 00',
        ]

def test_leap_second():

    # During 1973 the offset between UTC and TAI was 12.0 seconds, so
    # TAI should reach the first moment of 1974 while the UTC clock is
    # still reading 12s before midnight (60 - 12 = 48).  Happily, the
    # fraction 0.5 can be precisely represented in floating point, so we
    # can use a bare `==` in this assert:

    t0 = JulianDate(utc=(1973, 12, 31, 23, 59, 48.0)).tai
    assert t0 == 2442048.5

    # Here are some more interesting values:

    t1 = JulianDate(utc=(1973, 12, 31, 23, 59, 58.0)).tai
    t2 = JulianDate(utc=(1973, 12, 31, 23, 59, 59.0)).tai
    t3 = JulianDate(utc=(1973, 12, 31, 23, 59, 60.0)).tai
    t4 = JulianDate(utc=(1974, 1, 1, 0, 0, 0.0)).tai
    t5 = JulianDate(utc=(1974, 1, 1, 0, 0, 1.0)).tai

    # The step from 23:59:59 to 0:00:00 is here a two-second step,
    # because of the leap second 23:59:60 that falls in between:

    assert abs(t4 - t2 - 2.0 * one_second) < epsilon

    # Thus, the five dates given above are all one second apart:

    assert abs(t2 - t1 - one_second) < epsilon
    assert abs(t3 - t2 - one_second) < epsilon
    assert abs(t4 - t3 - one_second) < epsilon
    assert abs(t5 - t4 - one_second) < epsilon

    # And all these dates can be converted back to UTC.

    assert JulianDate(tai=t0).utc_iso() == '1973-12-31T23:59:48Z'
    assert JulianDate(tai=t1).utc_iso() == '1973-12-31T23:59:58Z'
    assert JulianDate(tai=t2).utc_iso() == '1973-12-31T23:59:59Z'
    assert JulianDate(tai=t3).utc_iso() == '1973-12-31T23:59:60Z'
    assert JulianDate(tai=t4).utc_iso() == '1974-01-01T00:00:00Z'
    assert JulianDate(tai=t5).utc_iso() == '1974-01-01T00:00:01Z'

########NEW FILE########
__FILENAME__ = test_units
"""Tests of whether units behave."""

import pytest
from skyfield import units

try:
    from astropy import units as u
except ImportError:
    u = None

needs_astropy = pytest.mark.skipif(u is None, reason='cannot import AstroPy')

def test_iterating_over_raw_measurement():
    distance = units.Distance(AU=1.234)
    with pytest.raises(units.UnpackingError):
        x, y, z = distance

def test_iterating_over_raw_velocity():
    velocity = units.Velocity(AU_per_d=1.234)
    with pytest.raises(units.UnpackingError):
        x, y, z = velocity

@needs_astropy
def test_converting_distance_with_astropy():
    distance = units.Distance(AU=1.234)
    value1 = distance.km
    value2 = distance.to(u.km)
    epsilon = 0.02         # definitions of AU seem to disagree slightly
    assert abs(value1 - value2.value) < epsilon

@needs_astropy
def test_converting_velocity_with_astropy():
    velocity = units.Velocity(AU_per_d=1.234)
    value1 = velocity.km_per_s
    value2 = velocity.to(u.km / u.s)
    epsilon = 1e-6
    assert abs(value1 - value2.value) < epsilon

########NEW FILE########
__FILENAME__ = test_vectorization
"""Determine whether arrays work as well as individual inputs."""

import sys
from numpy import array, rollaxis
from .. import starlib
from ..constants import T0, B1950
from ..api import earth, mars
from ..positionlib import Topos
from ..timelib import JulianDate, julian_date

if sys.version_info < (3,):
    from itertools import izip
else:
    izip = zip

dates = array([
    julian_date(1969, 7, 20) + (20.0 + 18.0 / 60.0) / 24.0,
    T0,
    julian_date(2012, 12, 21),
    julian_date(2027, 8, 2) + (10.0 + (7.0 + 50.0 / 60.0) / 60.0) / 24.0,
    ])

deltas = array([39.707, 63.8285, 66.8779, 72.])

def compute_times_and_equinox_matrices(tt, delta_t):
    jd = JulianDate(tt=tt, delta_t=delta_t)

    yield jd.ut1
    yield jd.tt
    yield jd.tdb

    yield jd.P
    yield jd.N
    yield jd.M

def observe_planet_from_geocenter(tt, delta_t):
    jd = JulianDate(tt=tt, delta_t=delta_t)
    observer = earth(jd)

    yield observer.position.AU
    yield observer.position.km
    yield observer.velocity.AU_per_d
    yield observer.velocity.km_per_s
    yield observer.jd.ut1
    yield observer.jd.tt
    yield observer.jd.tdb

    astrometric = observer.observe(mars)

    yield astrometric.position.AU
    yield astrometric.velocity.AU_per_d

    ra, dec, distance = astrometric.radec()

    yield ra.hours()
    yield dec.degrees()
    yield distance.AU

    ra, dec, distance = astrometric.radec(epoch=B1950)

    yield ra.hours()
    yield dec.degrees()
    yield distance.AU

    apparent = astrometric.apparent()

    yield apparent.position.AU
    #yield apparent.velocity  # = None?

    ra, dec, distance = apparent.radec()

    yield ra.hours()
    yield dec.degrees()
    yield distance.AU

    ra, dec, distance = apparent.radec(epoch=B1950)

    yield ra.hours()
    yield dec.degrees()
    yield distance.AU

def observe_planet_from_topos(tt, delta_t):
    jd = JulianDate(tt=tt, delta_t=delta_t)

    yield jd.ut1
    yield jd.tt
    yield jd.tdb

    topos = Topos('71.1375 W', '42.6583 N', 0.0)
    topos.ephemeris = earth.ephemeris
    observer = topos(jd)

    yield observer.position.AU
    yield observer.velocity.AU_per_d
    yield observer.jd.ut1
    yield observer.jd.tt
    yield observer.jd.tdb

    astrometric = observer.observe(mars)

    yield astrometric.position.AU
    yield astrometric.velocity.AU_per_d

    ra, dec, distance = astrometric.radec()

    yield ra.hours()
    yield dec.degrees()
    yield distance.AU

    ra, dec, distance = astrometric.radec(epoch=B1950)

    yield ra.hours()
    yield dec.degrees()
    yield distance.AU

    apparent = astrometric.apparent()

    yield apparent.position.AU
    #yield apparent.velocity  # = None?

    ra, dec, distance = apparent.radec()

    yield ra.hours()
    yield dec.degrees()
    yield distance.AU

    ra, dec, distance = apparent.radec(epoch=B1950)

    yield ra.hours()
    yield dec.degrees()
    yield distance.AU

def compute_stellar_position(tt, delta_t):
    star = starlib.Star(ra_hours=1.59132070233, dec_degrees=8.5958876464)
    observer = earth(tt=tt, delta_t=delta_t)
    astrometric = observer.observe(star)

    yield astrometric.position.AU
    yield astrometric.velocity.AU_per_d

    ra, dec, distance = astrometric.radec()

    yield ra.hours()
    yield dec.degrees()
    yield distance.AU

def pytest_generate_tests(metafunc):
    if 'vector_vs_scalar' in metafunc.fixturenames:
        metafunc.parametrize(
            'vector_vs_scalar',
            list(generate_comparisons(compute_times_and_equinox_matrices)) +
            list(generate_comparisons(observe_planet_from_geocenter)) +
            list(generate_comparisons(observe_planet_from_topos)) +
            list(generate_comparisons(compute_stellar_position)))

def generate_comparisons(computation):
    """Set up comparisons between vector and scalar outputs of `computation`.

    The `computation` should be a generator that accepts both vector and
    scalar input, and that yields a series of values whose shape
    corresponds to its input's shape.

    """
    vector_results = list(computation(dates, deltas))
    for i, (date, delta_t) in enumerate(zip(dates, deltas)):
        g = computation(date, delta_t)
        for vector, scalar in izip(vector_results, g):
            f = g.gi_frame
            location = '{}:{}'.format(f.f_code.co_filename, f.f_lineno)
            yield location, vector, i, scalar

def test_vector_vs_scalar(vector_vs_scalar):
    location, vector, i, scalar = vector_vs_scalar
    vectorT = rollaxis(vector, -1)
    assert vector is not None, (
        '{}:\n  vector is None'.format(location))
    assert vectorT[i].shape == scalar.shape, (
        '{}:\n  {}[{}].shape != {}.shape\n  shapes: {} {}'.format(
            location, vector.T, i, scalar, vector.T[i].shape, scalar.shape))

    vectorTi = vectorT[i]

    # Yes, an auto-generated epsilon with no physical significance!
    # Why?  Because we are comparing the rounding differences in two
    # (hopefully!) identical floating-point computations, not thinking
    # of the results as two physical calculations.

    epsilon = abs(1e-15 * max(vectorTi.max(), scalar.max()))
    difference = abs(vectorTi - scalar)

    assert (difference <= epsilon).all(), (
        '{}:\n vector[{}] = {}\n'
        ' scalar    = {}\n'
        ' difference= {}\n'
        ' epsilon   = {}'
        .format(location, i, vectorTi, scalar, difference, epsilon))

########NEW FILE########
__FILENAME__ = test_vs_novas
"""Compare the output of Skyfield with the same routines from NOVAS."""

import pytest
from numpy import array, einsum

from skyfield import (positionlib, earthlib, framelib, nutationlib,
                      jpllib, precessionlib, starlib, timelib)

from ..constants import ASEC2RAD, AU, DEG2RAD, T0
from ..functions import length_of
from ..timelib import JulianDate

# Since some users might run these tests without having installed our
# test dependencies, we detect import errors and skip these tests if the
# resources they need are not available.

try:
    import de405
    de405 = jpllib.Ephemeris(de405)
except ImportError:
    de405 = None

try:
    import novas
    import novas_de405
except ImportError:
    novas = None
else:
    import novas.compat as c
    import novas.compat.eph_manager

    jd_start, jd_end, number = c.eph_manager.ephem_open()  # needs novas_de405

    c_nutation = c.nutation
    import novas.compat.nutation  # overwrites nutation() function with module!

    TA = c.julian_date(1969, 7, 20, 20. + 18. / 60.)
    TB = c.julian_date(2012, 12, 21)
    TC = c.julian_date(2027, 8, 2, 10. + 7. / 60. + 50. / 3600.)

    D0 = 63.8285
    DA = 39.707
    DB = 66.8779
    DC = 72.  # http://maia.usno.navy.mil/ser7/deltat.preds

    P0 = (T0, D0)  # "pair 0"
    PA = (TA, DA)
    PB = (TB, DB)

arcminute = DEG2RAD / 60.0
arcsecond = arcminute / 60.0
arcsecond_in_hours = 24.0 / 360.0 / 60.0 / 60.0
arcsecond_in_degrees = 1.0 / 60.0 / 60.0
meter = 1.0 / AU

planet_codes = {
    'mercury': 1,
    'venus': 2,
    'mars': 4,
    'jupiter': 5,
    'saturn': 6,
    'uranus': 7,
    'neptune': 8,
    'pluto': 9,
    'sun': 10,
    'moon': 11,
    }

# Fixtures.

@pytest.fixture(params=[
    {'tt': T0, 'delta_t': D0},
    {'tt': TA, 'delta_t': DA},
    {'tt': TB, 'delta_t': DB},
    {'tt': TC, 'delta_t': DC},
    ])
def jd(request):
    # Build a new JulianDate each time, because some test cases need to
    # adjust the value of the date they are passed.
    return JulianDate(**request.param)

@pytest.fixture(params=[T0, TA, TB, TC])
def jd_float_or_vector(request):
    return request.param

@pytest.fixture(params=planet_codes.items())
def planet_name_and_code(request):
    return request.param

# Tests.

def eq(first, second, epsilon=None):
    """Test whether two floats are within `epsilon` of one another."""
    #print 'Significance of epsilon:', epsilon / second
    difference = abs(first - second)
    # if epsilon:
    #     print 'Difference relative to epsilon:', difference / epsilon
    if hasattr(first, 'shape') or hasattr(second, 'shape'):
        failed = difference.max() > epsilon
    else:
        failed = difference > epsilon
    if failed:
        appendix = ('\nbecause the difference is\n%r\ntimes too big'
                    % (abs(first - second) / epsilon)) if epsilon else ''
        raise AssertionError(
            '\n%r does not equal\n%r\nwithin the error bound\n%r%s'
            % (first, second, epsilon, appendix))


def test_star_deflected_by_jupiter(jd):
    star = c.make_cat_entry(
        star_name='Star', catalog='cat', star_num=101,
        ra=1.59132070233, dec=8.5958876464,
        pm_ra=0.0, pm_dec=0.0,
        parallax=0.0, rad_vel=0.0,
        )
    ra0, dec0 = c.app_star(jd.tt, star)

    earth = de405.earth
    star = starlib.Star(
        ra_hours=1.59132070233, dec_degrees=8.5958876464,
        ra_mas_per_year=0.0, dec_mas_per_year=0.0,
        parallax=0.0, radial_km_per_s=0.0,
        )
    ra, dec, distance = earth(jd).observe(star).apparent().radec(epoch=jd)

    eq(ra0, ra.hours(), 1e-9 * arcsecond_in_hours)
    eq(dec0, dec.degrees(), 1e-9 * arcsecond_in_degrees)

# Tests of generating a full position or coordinate.

def test_astro_planet(jd, planet_name_and_code):
    planet_name, planet_code = planet_name_and_code

    obj = c.make_object(0, planet_code, 'planet', None)
    ra0, dec0, distance0 = c.astro_planet(jd.tt, obj)

    earth = de405.earth
    planet = getattr(de405, planet_name)
    e = earth(jd)
    distance = length_of((e - planet(jd)).position.AU)
    ra, dec, d = e.observe(planet).radec()

    eq(ra0, ra.hours(), 1e-3 * arcsecond_in_hours)
    eq(dec0, dec.degrees(), 1e-3 * arcsecond_in_degrees)
    eq(distance0, distance, 0.5 * meter)

def test_virtual_planet(jd, planet_name_and_code):
    planet_name, planet_code = planet_name_and_code

    obj = c.make_object(0, planet_code, 'planet', None)
    ra0, dec0, distance0 = c.virtual_planet(jd.tt, obj)

    earth = de405.earth
    planet = getattr(de405, planet_name)
    e = earth(jd)
    distance = length_of((e - planet(jd)).position.AU)
    ra, dec, d = e.observe(planet).apparent().radec()

    eq(ra0, ra.hours(), 0.001 * arcsecond_in_hours)
    eq(dec0, dec.degrees(), 0.001 * arcsecond_in_degrees)
    eq(distance0, distance, 0.5 * meter)

def test_app_planet(jd, planet_name_and_code):
    planet_name, planet_code = planet_name_and_code

    obj = c.make_object(0, planet_code, 'planet', None)
    ra0, dec0, distance0 = c.app_planet(jd.tt, obj)

    earth = de405.earth
    planet = getattr(de405, planet_name)
    e = earth(jd)
    distance = length_of((e - planet(jd)).position.AU)
    ra, dec, d = e.observe(planet).apparent().radec(epoch=jd)

    eq(ra0, ra.hours(), 0.001 * arcsecond_in_hours)
    eq(dec0, dec.degrees(), 0.001 * arcsecond_in_degrees)
    eq(distance0, distance, 0.5 * meter)

def test_local_planet(jd, planet_name_and_code):
    position = c.make_on_surface(45.0, -75.0, 0.0, 10.0, 1010.0)
    ggr = positionlib.Topos('45 N', '75 W', 0.0,
                            temperature=10.0, pressure=1010.0)
    ggr.ephemeris = de405

    planet_name, planet_code = planet_name_and_code

    obj = c.make_object(0, planet_code, 'planet', None)
    ra0, dec0, distance0 = c.local_planet(jd.tt, jd.delta_t, obj, position)

    planet = getattr(de405, planet_name)
    g = ggr(jd)
    distance = length_of((g - planet(jd)).position.AU)
    ra, dec, d = g.observe(planet).apparent().radec()

    eq(ra0, ra.hours(), 0.001 * arcsecond_in_hours)
    eq(dec0, dec.degrees(), 0.001 * arcsecond_in_degrees)
    eq(distance0, distance, 0.5 * meter)

def test_topo_planet(jd, planet_name_and_code):
    position = c.make_on_surface(45.0, -75.0, 0.0, 10.0, 1010.0)
    ggr = positionlib.Topos('45 N', '75 W', 0.0,
                            temperature=10.0, pressure=1010.0)
    ggr.ephemeris = de405

    planet_name, planet_code = planet_name_and_code

    obj = c.make_object(0, planet_code, 'planet', None)
    ra0, dec0, distance0 = c.topo_planet(jd.tt, jd.delta_t, obj, position)

    planet = getattr(de405, planet_name)
    g = ggr(jd)
    distance = length_of((g - planet(jd)).position.AU)
    ra, dec, d = g.observe(planet).apparent().radec(epoch=jd)

    eq(ra0, ra.hours(), 0.001 * arcsecond_in_hours)
    eq(dec0, dec.degrees(), 0.001 * arcsecond_in_degrees)
    eq(distance0, distance, 0.5 * meter)

def test_altaz(jd, planet_name_and_code):
    """ Tests of generating a full position in altaz coordinates. Uses
        fixtures to iterate through date pairs and planets to generate
        individual tests.
    """
    planet_name, planet_code = planet_name_and_code
    position = c.make_on_surface(45.0, -75.0, 0.0, 10.0, 1010.0)
    ggr = positionlib.Topos('45 N', '75 W', 0.0,
                            temperature=10.0, pressure=1010.0)
    ggr.ephemeris = de405
    xp = yp = 0.0

    obj = c.make_object(0, planet_code, 'planet', None)
    ra, dec, dis = c.topo_planet(jd.tt, jd.delta_t, obj, position)
    (zd0, az0), (ra, dec) = c.equ2hor(jd.ut1, jd.delta_t, xp, yp,
                                      position, ra, dec)
    alt0 = 90.0 - zd0

    planet = getattr(de405, planet_name)
    g = ggr(jd)
    distance = length_of((g - planet(jd)).position.AU)
    alt, az, d = g.observe(planet).apparent().altaz()

    eq(az0, az.degrees(), 0.001 * arcsecond_in_degrees)
    eq(alt0, alt.degrees(), 0.001 * arcsecond_in_degrees)
    eq(dis, distance, 0.5 * meter)

# Tests for Basic Functions

def test_cal_date():
    for jd in 0.0, 2414988.5, 2415020.31352, 2442249.5, 2456335.2428472:
        whole, fraction = divmod((jd + 0.5), 1.0)
        y, m, d = timelib.calendar_date(int(whole))
        assert c.cal_date(jd) == (y, m, d, 24.0 * fraction)

def test_earth_rotation_angle(jd_float_or_vector):
    jd_ut1 = jd_float_or_vector
    u = c.era(jd_ut1)
    v = earthlib.earth_rotation_angle(jd_ut1)
    epsilon = 1e-12  # degrees; 14 to 15 digits of agreement
    eq(u, v, epsilon)

def test_earth_tilt(jd):
    u = c.e_tilt(jd.tdb)
    v = nutationlib.earth_tilt(jd)
    epsilon = 1e-9  # 9 to 11 digits of agreement; why not more?
    eq(array(u), array(v), epsilon)

def test_equation_of_the_equinoxes_complimentary_terms(jd_float_or_vector):
    jd_tt = jd_float_or_vector
    u = c.ee_ct(jd_tt, 0.0, 0)
    v = nutationlib.equation_of_the_equinoxes_complimentary_terms(jd_tt)

    epsilon = 1e-22  # radians; 14 digits of agreement
    eq(u, v, epsilon)

def test_frame_tie():
    xyz = array([1.1, 1.2, 1.3])
    epsilon = 1e-15  # but can be 0.0 when running outside of tox!
    eq(c.frame_tie(xyz, 0), framelib.ICRS_to_J2000.dot(xyz), epsilon)
    eq(c.frame_tie(xyz, -1), framelib.ICRS_to_J2000.T.dot(xyz), epsilon)

def test_fundamental_arguments(jd_float_or_vector):
    jd_tdb = jd_float_or_vector
    t = jcentury(jd_tdb)
    u = c.fund_args(t)
    v = nutationlib.fundamental_arguments(t)

    epsilon = 1e-12  # radians; 13 digits of agreement
    eq(u, v, epsilon)

def test_geocentric_position_and_velocity(jd):
    observer = c.make_observer_on_surface(45.0, -75.0, 0.0, 10.0, 1010.0)
    posu, velu = c.geo_posvel(jd.tt, jd.delta_t, observer)

    topos = positionlib.Topos('45 N', '75 W', elevation=0.0,
                              temperature=10.0, pressure=1010.0)
    posv, velv = earthlib.geocentric_position_and_velocity(topos, jd)

    epsilon = 1e-6 * meter  # 13 to 14 digits of agreement

    eq(posu, posv, epsilon)
    eq(velu, velv, epsilon)

def test_iau2000a(jd_float_or_vector):
    jd_tt = jd_float_or_vector
    psi0, eps0 = c.nutation.iau2000a(jd_tt, 0.0)
    psi1, eps1 = nutationlib.iau2000a(jd_tt)
    to_tenths_of_microarcseconds = 1e7 / ASEC2RAD

    epsilon = 4e-6  # tenths of micro arcseconds; 13 digits of precision

    eq(psi0 * to_tenths_of_microarcseconds, psi1, epsilon)
    eq(eps0 * to_tenths_of_microarcseconds, eps1, epsilon)

def test_julian_date():
    epsilon = 0.0  # perfect
    for args in (
          (-4712, 1, 1, 0.0),
          (-4712, 3, 1, 0.0),
          (-4712, 12, 31, 0.5),
          (-241, 3, 25, 19.0),
          (530, 9, 27, 23.5),
          (1976, 3, 7, 12.5),
          (2000, 1, 1, 0.0),
          ):
        eq(c.julian_date(*args), timelib.julian_date(*args), epsilon)

def test_mean_obliq(jd_float_or_vector):
    jd_tdb = jd_float_or_vector
    u = c.mean_obliq(jd_tdb)
    v = nutationlib.mean_obliquity(jd_tdb)
    epsilon = 0.0  # perfect
    eq(u, v, epsilon)

def test_nutation(jd):
    xyz = [1.1, 1.2, 1.3]
    u = c_nutation(jd.tdb, xyz)
    xyz = array(xyz)
    v = einsum('ij...,j...->i...', nutationlib.compute_nutation(jd), xyz)
    epsilon = 1e-14  # 14 digits of agreement
    eq(u, v, epsilon)

def test_precession(jd_float_or_vector):
    jd_tdb = jd_float_or_vector
    xyz = [1.1, 1.2, 1.3]
    u = c.precession(T0, xyz, jd_tdb)
    matrix_or_matrices = precessionlib.compute_precession(jd_tdb)
    v = einsum('ij...,j...->i...', matrix_or_matrices, array(xyz))
    epsilon = 1e-15  # 15 digits of agreement
    eq(u, v, epsilon)

def test_sidereal_time_with_zero_delta_t(jd):
    jd.delta_t = 0.0
    u = c.sidereal_time(jd.ut1, 0.0, 0.0, False, True)
    v = earthlib.sidereal_time(jd)
    epsilon = 1e-13  # days; 14 digits of agreement
    eq(u, v, epsilon)

def test_sidereal_time_with_nonzero_delta_t(jd):
    u = c.sidereal_time(jd.ut1, 0.0, jd.delta_t, False, True)
    v = earthlib.sidereal_time(jd)
    epsilon = 1e-13  # days; 14 digits of agreement
    eq(u, v, epsilon)

def test_starvectors():
    p, v = c.starvectors(c.make_cat_entry(
            'POLARIS', 'HIP', 0, 2.530301028, 89.264109444,
            44.22, -11.75, 7.56, -17.4))

    star = starlib.Star(ra_hours=2.530301028, dec_degrees=89.264109444,
                        ra_mas_per_year=44.22, dec_mas_per_year=-11.75,
                        parallax=7.56, radial_km_per_s=-17.4)

    p_epsilon = 1e-10  # AU; 16 digits of agreement
    v_epsilon = 1e-17  # AU/day; 15 digits of agreement

    eq(p, star._position, p_epsilon)
    eq(v, star._velocity, v_epsilon)

def test_ter2cel(jd):
    jd_low = 0.0
    xp = yp = 0.0

    position = array([1.1, 1.2, 1.3])

    theirs = c.ter2cel(jd.ut1, jd_low, jd.delta_t, xp, yp, position)
    ours = positionlib.ITRF_to_GCRS(jd, position)

    epsilon = 1e-13  # 13 digits of agreement
    eq(theirs, ours, epsilon)

def test_terra():
    observer = c.make_on_surface(45.0, -75.0, 0.0, 10.0, 1010.0)

    # Note that this class stands in for a NOVAS Topos structure, but
    # not for our own Topos class!
    class Topos(object):
        latitude = 45.0 * DEG2RAD
        longitude = -75.0 * DEG2RAD
        elevation = 0.0
    topos = Topos()

    pos0, vel0 = array(c.terra(observer, 11.0))
    pos1, vel1 = array(c.terra(observer, 23.9))

    posn, veln = earthlib.terra(topos, array([11.0, 23.9]))

    epsilon = 1e-8 * meter  # 14 digits of agreement

    eq(pos0, posn[:,0], epsilon)
    eq(pos1, posn[:,1], epsilon)
    eq(vel0, veln[:,0], epsilon)
    eq(vel1, veln[:,1], epsilon)

def test_tdb2tt(jd_float_or_vector):
    jd_tdb = jd_float_or_vector
    u = c.tdb2tt(jd_tdb)[1]
    v = timelib.tdb_minus_tt(jd_tdb)
    epsilon_seconds = 1e-16  # 11 or 12 digits of agreement; why not more?
    eq(u, v, epsilon_seconds)

def jcentury(t):
    return (t - T0) / 36525.0

########NEW FILE########
__FILENAME__ = timelib
from datetime import date, datetime, timedelta, tzinfo
from numpy import array, einsum, rollaxis, searchsorted, sin, where, zeros_like
from time import strftime
from .constants import T0, DAY_S
from .framelib import ICRS_to_J2000 as B
from .nutationlib import compute_nutation
from .precessionlib import compute_precession

try:
    from pytz import utc
except ImportError:

    class UTC(tzinfo):
        'UTC'
        zero = timedelta(0)
        def utcoffset(self, dt):
            return self.zero
        def tzname(self, dt):
            return 'UTC'
        def dst(self, dt):
            return self.zero

    utc = UTC()

# Much of the following code is adapted from the USNO's "novas.c".

_half_second = 0.5 / DAY_S
_half_millisecond = 0.5e-3 / DAY_S
_half_microsecond = 0.5e-6 / DAY_S
_months = array(['Month zero', 'Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun',
                 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'])

extra_documentation = """

        This routine takes a date as its argument.  You can either
        provide a `jd=` keyword argument with a `JulianDate` you have
        built yourself, or use one of these keyword arguments::

            # Coordinated Universal Time
            utc=(1973, 12, 29, 23, 59, 48.0)
            utc=datetime(1973, 12, 29, 23, 59, 48.0)

            # International Atomic Time
            tai=2442046.5

            # Terrestrial Time
            tt=2442046.5

"""

def takes_julian_date(function):
    """Wrap `function` so it accepts the standard Julian date arguments.

    A function that takes two arguments, `self` and `jd`, may be wrapped
    with this decorator if it wants to support optional auto-creation of
    its `jd` argument by accepting all of the same keyword arguments
    that the JulianDate constructor itself supports.

    """
    def wrapper(self, jd=None, utc=None, tai=None, tt=None,
                delta_t=0.0, cache=None):
        if jd is None:
            jd = JulianDate(utc=utc, tai=tai, tt=tt,
                            delta_t=delta_t, cache=cache)
        else:
            pass  # TODO: verify that they provided a JulianDate instance
        return function(self, jd)
    wrapper.__name__ = function.__name__
    synopsis, blank_line, description = function.__doc__.partition('\n\n')
    wrapper.__doc__ = ''.join(synopsis + extra_documentation + description)
    return wrapper

def _to_array(value):
    """When `value` is a plain Python sequence, return it as a NumPy array."""
    if not hasattr(value, 'shape') and hasattr(value, '__len__'):
        return array(value)
    else:
        return value

tt_minus_tai = array(32.184 / DAY_S)

class JulianDate(object):
    """Julian date.

    :param utc: Coordinated Universal Time
    :param tai: International Atomic Time
    :param tt: Terrestrial Time
    :param delta_t: Difference between Terrestrial Time and UT1
    :param cache: Cache for automatically fetching `delta_t` table

    """
    def __init__(self, utc=None, tai=None, tt=None, tdb=None,
                 delta_t=0.0, cache=None):

        self.delta_t = _to_array(delta_t)

        if cache is None:
            from skyfield.data import cache
        self.cache = cache

        if tai is None and utc is not None:
            leap_dates, leap_offsets = cache.run(usno_leapseconds)
            if isinstance(utc, datetime):
                tai = _utc_datetime_to_tai(leap_dates, leap_offsets, utc)
            elif isinstance(utc, date):
                tai = _utc_date_to_tai(leap_dates, leap_offsets, utc)
            elif isinstance(utc, tuple):
                values = [_to_array(value) for value in utc]
                tai = _utc_to_tai(leap_dates, leap_offsets, *values)
            else:
                tai = array([
                    _utc_datetime_to_tai(leap_dates, leap_offsets, dt)
                    for dt in utc])

        if tai is not None:
            if isinstance(tai, tuple):
                tai = julian_date(*tai)
            self.tai = _to_array(tai)
            if tt is None:
                tt = tai + tt_minus_tai

        if tdb is not None:
            if isinstance(tdb, tuple):
                tdb = julian_date(*tdb)
            self.tdb = _to_array(tdb)
            if tt is None:
                tt = tdb - tdb_minus_tt(tdb) / DAY_S

        if tt is None:
            raise ValueError('You must supply either utc, tai, tt, or tdb'
                             ' when building a JulianDate')
        elif isinstance(tt, tuple):
            tt = julian_date(*tt)

        self.tt = _to_array(tt)
        self.shape = getattr(self.tt, 'shape', ())
        self.delta_t = delta_t

    def __getitem__(self, index):
        # TODO: also copy cached matrices?
        jd = JulianDate(tt=self.tt[index])
        for name in 'utc', 'tai', 'tdb', 'ut1', 'delta_t':
            value = getattr(self, name, None)
            if value is not None:
                if getattr(value, 'shape', None):
                    value = value[index]
                setattr(jd, name, value)
        return jd

    def astimezone(self, tz):
        """Return a ``datetime`` for this value in a ``pytz`` timezone.

        The third-party ``pytz`` package must be installed separately.
        If this value is a date array, then a sequence of datetimes is
        returned.

        """
        dt, leap_second = self.utc_datetime()
        normalize = getattr(tz, 'normalize', lambda d: d)
        if self.shape:
            dt = [normalize(d.astimezone(tz)) for d in dt]
        else:
            dt = normalize(dt.astimezone(tz))
        return dt, leap_second

    def utc_datetime(self):
        """Return a UTC ``datetime`` for this value.

        If the third-party ``pytz`` package is available, then its
        ``utc`` timezone is used.  Otherwise, a Skyfield built-in
        alternative is used; the result should be the same either way.
        If this value is a date array, then a sequence of datetimes is
        returned.

        """
        year, month, day, hour, minute, second = self._utc(_half_millisecond)
        second, fraction = divmod(second, 1.0)
        second = second.astype(int)
        leap_second = second // 60
        second -= leap_second
        milli = (fraction * 1000).astype(int) * 1000
        if self.shape:
            utcs = [utc] * self.shape[0]
            argsets = zip(year, month, day, hour, minute, second, milli, utcs)
            dt = [datetime(*args) for args in argsets]
        else:
            dt = datetime(year, month, day, hour, minute, second, milli, utc)
        return dt, leap_second

    def utc_iso(self, places=0):
        """Return this UTC value as an ISO 8601 string or array of strings.

        For example: ``2014-01-18T01:35:38Z``

        """
        if places:
            power_of_ten = 10 ** places
            offset = _half_second / power_of_ten
            year, month, day, hour, minute, second = self._utc(offset)
            second, fraction = divmod(second, 1.0)
            fraction *= power_of_ten
            format = '%%04d-%%02d-%%02dT%%02d:%%02d:%%02d.%%0%ddZ' % places
            args = (year, month, day, hour, minute, second, fraction)
        else:
            format = '%04d-%02d-%02dT%02d:%02d:%02dZ'
            args = self._utc(_half_second)

        if self.shape:
            return [format % tup for tup in zip(*args)]
        else:
            return format % args

    def utc_jpl(self):
        """Return UTC in the format used by the JPL HORIZONS system.

        For example: ``A.D. 2014-Jan-18 01:35:37.5000 UT``

        """
        offset = _half_second / 1e4
        year, month, day, hour, minute, second = self._utc(offset)
        second, fraction = divmod(second, 1.0)
        fraction *= 1e4
        bc = year < 1
        year = abs(year - bc)
        era = where(bc, 'B.C.', 'A.D.')
        format = '%s %04d-%s-%02d %02d:%02d:%02d.%04d UT'
        args = (era, year, _months[month], day, hour, minute, second, fraction)

        if self.shape:
            return [format % tup for tup in zip(*args)]
        else:
            return format % args

    def utc_strftime(self, format):
        """Format this UTC time according to a standard format string.

        This internally calls the Python ``strftime()`` routine from the
        Standard Library ``time()`` module, for which you can find a
        quick reference at http://strftime.org/.

        """
        tup = self._utc(_half_second)
        year, month, day, hour, minute, second = tup
        second = second.astype(int)
        zero = zeros_like(year)
        tup = (year, month, day, hour, minute, second, zero, zero, zero)
        if self.shape:
            return [strftime(format, item) for item in zip(*tup)]
        else:
            return strftime(format, tup)

    def _utc(self, offset=0.0):
        """Return UTC as (year, month, day, hour, minute, second.fraction).

        The `offset` is added to the UTC time before it is split into
        its components.  This is useful if the user is going to round
        the result before displaying it.  If the result is going to be
        displayed as seconds, for example, set `offset` to half a second
        and then throw away the fraction; if the result is going to be
        displayed as minutes, set `offset` to thirty seconds and then
        throw away the seconds; and so forth.

        """
        tai = self.tai + offset
        leap_dates, leap_offsets = self.cache.run(usno_leapseconds)
        leap_reverse_dates = leap_dates + leap_offsets / DAY_S
        i = searchsorted(leap_reverse_dates, tai, 'right')
        j = tai - leap_offsets[i] / DAY_S
        whole, fraction = divmod(j + 0.5, 1.0)
        whole = whole.astype(int)
        year, month, day = calendar_date(whole)
        hour, hfrac = divmod(fraction * 24.0, 1.0)
        minute, second = divmod(hfrac * 3600.0, 60.0)
        is_leap_second = j < leap_dates[i-1]
        second += is_leap_second
        return year, month, day, hour.astype(int), minute.astype(int), second

    def __getattr__(self, name):

        # Cache of several expensive functions of time.

        if name == 'P':
            self.P = P = compute_precession(self.tdb)
            return P

        if name == 'PT':
            self.PT = PT = rollaxis(self.P, 1)
            return PT

        if name == 'N':
            self.N = N = compute_nutation(self)
            return N

        if name == 'NT':
            self.NT = NT = rollaxis(self.N, 1)
            return NT

        if name == 'M':
            self.M = M = einsum('ij...,jk...,kl...->il...', self.N, self.P, B)
            return M

        if name == 'MT':
            self.MT = MT = rollaxis(self.M, 1)
            return MT

        # Conversion between timescales.

        if name == 'tai':
            self.tai = tai = self.tt - tt_minus_tai
            return tai

        if name == 'utc':
            utc = self._utc()
            utc = array(utc) if self.shape else utc
            self.utc = utc = utc
            return utc

        if name == 'tdb':
            tt = self.tt
            self.tdb = tdb = tt + tdb_minus_tt(tt) / DAY_S
            return tdb

        if name == 'ut1':
            self.ut1 = ut1 = self.tt - self.delta_t / DAY_S
            return ut1

        raise AttributeError('no such attribute %r' % name)

    def __eq__(self, other_jd):
        return self.tt == other_jd.tt


def now():
    """Return the current date and time as a `JulianDate` object.

    For the return value to be correct, your operating system time and
    timezone settings must be set so that the Python Standard Library
    constructor ``datetime.datetime.utcnow()`` returns a correct UTC
    date and time.

    """
    return JulianDate(utc=datetime.utcnow().replace(tzinfo=utc))

def julian_day(year, month=1, day=1):
    """Given a proleptic Gregorian calendar date, return a Julian day int."""
    janfeb = month < 3
    return (day
            + 1461 * (year + 4800 - janfeb) // 4
            + 367 * (month - 2 + janfeb * 12) // 12
            - 3 * ((year + 4900 - janfeb) // 100) // 4
            - 32075)

def julian_date(year, month=1, day=1, hour=0, minute=0, second=0.0):
    """Given a proleptic Gregorian calendar date, return a Julian date float."""
    return julian_day(year, month, day) - 0.5 + (
        second + minute * 60.0 + hour * 3600.0) / DAY_S

def calendar_date(jd_integer):
    """Convert Julian Day `jd_integer` into a Gregorian (year, month, day)."""

    k = jd_integer + 68569
    n = 4 * k // 146097

    k = k - (146097 * n + 3) // 4
    m = 4000 * (k + 1) // 1461001
    k = k - 1461 * m // 4 + 31
    month = 80 * k // 2447
    day = k - 2447 * month // 80
    k = month // 11

    month = month + 2 - 12 * k
    year = 100 * (n - 49) + m + k

    return year, month, day

def tdb_minus_tt(jd_tdb):
    """Computes how far TDB is in advance of TT, given TDB.

    Given that the two time scales never diverge by more than 2ms, TT
    can also be given as the argument to perform the conversion in the
    other direction.

    """
    t = (jd_tdb - T0) / 36525.0

    # USNO Circular 179, eq. 2.6.
    return (0.001657 * sin ( 628.3076 * t + 6.2401)
          + 0.000022 * sin ( 575.3385 * t + 4.2970)
          + 0.000014 * sin (1256.6152 * t + 6.1969)
          + 0.000005 * sin ( 606.9777 * t + 4.0212)
          + 0.000005 * sin (  52.9691 * t + 0.4444)
          + 0.000002 * sin (  21.3299 * t + 5.5431)
          + 0.000010 * t * sin ( 628.3076 * t + 4.2490))

def usno_leapseconds(cache):
    """Download the USNO table of leap seconds as a ``(2, N+1)`` NumPy array.

    The array has two rows ``[leap_dates leap_offsets]``.  The first row
    is used to find where a given date ``jd`` falls in the table::

        index = np.searchsorted(leap_dates, jd, 'right')

    This can return a value from ``0`` to ``N``, allowing the
    corresponding UTC offset to be fetched with::

        offset = leap_offsets[index]

    The offset is the number of seconds that must be added to a UTC time
    to build the corresponding TAI time.

    """
    with cache.open_url('http://maia.usno.navy.mil/ser7/leapsec.dat') as f:
        lines = f.readlines()

    linefields = [line.split() for line in lines]
    dates = [float(fields[4]) for fields in linefields]
    offsets = [float(fields[6]) for fields in linefields]

    dates.insert(0, float('-inf'))
    dates.append(float('inf'))

    offsets.insert(0, offsets[0])
    offsets.insert(1, offsets[0])

    return array([dates, offsets])

def _utc_datetime_to_tai(leap_dates, leap_offsets, dt):
    try:
        utc_datetime = dt.astimezone(utc)
    except ValueError:
        raise ValueError(_naive_complaint)
    tup = utc_datetime.utctimetuple()
    year, month, day, hour, minute, second, wday, yday, dst = tup
    return _utc_to_tai(leap_dates, leap_offsets, year, month, day,
                       hour, minute, second + dt.microsecond / 1000000.00)

def _utc_date_to_tai(leap_dates, leap_offsets, d):
    return _utc_to_tai(leap_dates, leap_offsets, d.year, d.month, d.day)

def _utc_to_tai(leap_dates, leap_offsets, year, month=1, day=1,
                hour=0, minute=0, second=0.0):
    j = julian_day(year, month, day) - 0.5
    i = searchsorted(leap_dates, j, 'right')
    return j + (second + leap_offsets[i]
                + minute * 60.0
                + hour * 3600.0) / DAY_S


_naive_complaint = """cannot interpret a datetime that lacks a timezone

You must either specify that your datetime is in UTC:

    from skyfield.api import utc
    d = datetime(..., tzinfo=utc)  # to build a new datetime
    d = d.replace(tzinfo=utc)      # to fix an existing datetime

Or install the third-party `pytz` library and use any of its timezones:

    from pytz import timezone
    eastern = timezone('US/Eastern')
    d = eastern.localize(datetime(2014, 1, 16, 1, 32, 9))
"""

########NEW FILE########
__FILENAME__ = units
"""Simple distance, velocity, and angle support for Skyfield.

"""
import numpy as np
from .constants import AU_KM, DAY_S, tau

# Distance and velocity.

class UnpackingError(Exception):
    """You cannot iterate directly over a Skyfield measurement object."""

class Distance(object):
    """A distance, stored internally as AU and available in other units.

    You can initialize a ``Distance`` by providing a single float or a
    float array as either an ``AU=`` parameter or a ``km=`` parameter
    when building a ``Distance`` object.

    """
    def __init__(self, AU=None, km=None):
        if AU is not None:
            self.AU = AU
        elif km is not None:
            self.km = km
            self.AU = km / AU_KM

    def __getattr__(self, name):
        if name == 'km':
            self.km = self.AU * AU_KM
            return self.km
        raise AttributeError('no attribute named %r' % (name,))

    def __str__(self):
        return '%s AU' % self.AU

    def __iter__(self):
        raise UnpackingError(_iter_message % {
            'class': self.__class__.__name__, 'values': 'x, y, z',
            'attr1': 'AU', 'attr2': 'km'})

    def to(self, unit):
        """Return this distance in the given AstroPy units."""
        from astropy.units import AU
        return (self.AU * AU).to(unit)

class Velocity(object):
    """A velocity, stored internally as AU/day and available in other units.

    You can initialize a ``Velocity`` by providing a single float or a
    float array as either an ``AU_per_d=`` parameter.

    """
    def __init__(self, AU_per_d):
        self.AU_per_d = AU_per_d

    def __getattr__(self, name):
        if name == 'km_per_s':
            self.km_per_s = self.AU_per_d * AU_KM / DAY_S
            return self.km_per_s
        raise AttributeError('no attribute named %r' % (name,))

    def __iter__(self):
        raise UnpackingError(_iter_message % {
            'class': self.__class__.__name__, 'values': 'xdot, ydot, zdot',
            'attr1': 'AU_per_d', 'attr2': 'km_per_s'})

    def to(self, unit):
        """Return this velocity in the given AstroPy units."""
        from astropy.units import AU, d
        return (self.AU_per_d * AU / d).to(unit)

_iter_message = """\
cannot directly unpack a %(class)s into several values

To unpack a %(class)s into three components, you need to ask for its
value in specific units through an attribute or method:

    %(values)s = velocity.%(attr1)s
    %(values)s = velocity.%(attr2)s
    %(values)s = velocity.to(astropy_unit)
"""

# Angle units.

_to_degrees = 360.0 / tau
_from_degrees = tau / 360.0

_to_hours = 24.0 / tau
_from_hours = tau / 24.0

_instantiation_instructions = """to instantiate an Angle, try one of:

Angle(angle=another_angle)
Angle(radians=value)
Angle(degrees=value)
Angle(hours=value)

where `value` can be either a Python float or a NumPy array of floats"""

class BaseAngle(object):

    _unary_plus = False

    def __init__(self, angle=None, radians=None, degrees=None, hours=None):
        if angle is not None:
            if not isinstance(angle, BaseAngle):
                raise ValueError(_instantiation_instructions)
            self._radians = angle._radians
        elif radians is not None:
            self._radians = radians
        elif degrees is not None:
            self._radians = degrees * _from_degrees
        elif hours is not None:
            self._radians = hours * _from_hours

    def __format__(self, format_spec):
        return self.dstr()

    def radians(self):
        return self._radians

    def hours(self):
        return self._radians * _to_hours

    def hms(self):
        return _sexagesimalize(self.hours())

    def hstr(self, places=2, plus=False):
        sgn, h, m, s, etc = _sexagesimalize(self.hours(), places)
        sign = '-' if sgn < 0.0 else '+' if (plus or self._unary_plus) else ''
        return '%s%02dh %02dm %02d.%0*ds' % (sign, h, m, s, places, etc)

    def degrees(self):
        return self._radians * _to_degrees

    def dms(self):
        return _sexagesimalize(self.degrees())

    def dstr(self, places=1, plus=False):
        sgn, d, m, s, etc = _sexagesimalize(self.degrees(), places)
        sign = '-' if sgn < 0.0 else '+' if (plus or self._unary_plus) else ''
        return '%s%02ddeg %02d\' %02d.%0*d"' % (sign, d, m, s, places, etc)

    hours_anyway = hours
    hms_anyway = hms
    hstr_anyway = hstr

    degrees_anyway = degrees
    dms_anyway = dms
    dstr_anyway = dstr

class WrongUnitError(ValueError):

    def __init__(self, name, unit):
        usual = 'hours' if (unit == 'degrees') else 'degrees'
        self.args = ('This angle is usually expressed in {}, not {};'
                     ' if you want to express it in {} anyway, use'
                     ' {}_anyway()'.format(usual, unit, unit, name),)

class Angle(BaseAngle):

    __str__ = BaseAngle.dstr

    # Protect naive users from accidentally calling hour methods.

    def hours(self):
        raise WrongUnitError('hours', 'hours')

    def hms(self):
        raise WrongUnitError('hms', 'hours')

    def hstr(self):
        raise WrongUnitError('hstr', 'hours')

class SignedAngle(Angle):
    """An Angle that prints a unary ``'+'`` when positive."""

    _unary_plus = True

class HourAngle(BaseAngle):

    __str__ = BaseAngle.hstr

    # Protect naive users from accidentally calling degree methods.

    def degrees(self):
        raise WrongUnitError('degrees', 'degrees')

    def dms(self):
        raise WrongUnitError('dms', 'degrees')

    def dstr(self):
        raise WrongUnitError('dstr', 'degrees')

def _sexagesimalize(value, places=0):
    sign = int(np.sign(value))
    value = np.absolute(value)
    power = 10 ** places
    n = int(7200 * power * value + 1) // 2
    n, fraction = divmod(n, power)
    n, seconds = divmod(n, 60)
    n, minutes = divmod(n, 60)
    return sign, n, minutes, seconds, fraction

def interpret_longitude(value):
    split = getattr(value, 'split', None)
    if split is not None:
        pieces = split()
        degrees = float(pieces[0])
        if len(pieces) > 1 and pieces[1].lower() == 'w':
            degrees = - degrees
        return degrees / 360. * tau
    else:
        return value

def interpret_latitude(value):
    split = getattr(value, 'split', None)
    if split is not None:
        pieces = split()
        degrees = float(pieces[0])
        if len(pieces) > 1 and pieces[1].lower() == 's':
            degrees = - degrees
        return degrees / 360. * tau
    else:
        return value

########NEW FILE########
