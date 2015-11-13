__FILENAME__ = make_projection
# (C) British Crown Copyright 2011 - 2012, Met Office
#
# This file is part of cartopy.
#
# cartopy is free software: you can redistribute it and/or modify it under
# the terms of the GNU Lesser General Public License as published by the
# Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# cartopy is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Lesser General Public License for more details.
#
# You should have received a copy of the GNU Lesser General Public License
# along with cartopy.  If not, see <http://www.gnu.org/licenses/>.

import itertools
import os

import numpy as np

import cartopy.crs as ccrs


def find_projections():
    for obj_name, o in vars(ccrs).copy().iteritems():
#        o = getattr(ccrs, obj_name)
        if (isinstance(o, type) and issubclass(o, ccrs.Projection) and
            not obj_name.startswith('_') and obj_name not in ['Projection']):

            # yield the projections
            yield o

def projection_rst(projection_cls):
    name = projection_cls.__name__
    print name


SPECIAL_CASES = {ccrs.PlateCarree: ['PlateCarree()', 'PlateCarree(central_longitude=180)'],
                 ccrs.RotatedPole: ['RotatedPole(pole_longitude=177.5, pole_latitude=37.5)'],
                 }


COASTLINE_RESOLUTION = {ccrs.OSNI: '10m',
                        ccrs.OSGB: '50m',
                        ccrs.EuroPP: '50m'}

PRJ_SORT_ORDER = {'PlateCarree': 1, 'Mercator': 2, 'Mollweide': 2, 'Robinson': 2,
                  'TransverseMercator': 2, 'LambertCylindrical': 2,
                  'LambertConformal': 2, 'Stereographic': 2, 'Miller': 2,
                  'Orthographic': 2, 'InterruptedGoodeHomolosine': 3,
                  'RotatedPole': 3, 'OSGB': 4}


groups = [('cylindrical', [ccrs.PlateCarree, ccrs.Mercator, ccrs.TransverseMercator,
                           ccrs.OSGB, ccrs.LambertCylindrical, ccrs.Miller, ccrs.RotatedPole]),
          ('pseudo-cylindrical', [ccrs.Mollweide, ccrs.Robinson]),
#          ('conic', [ccrs.aed]),
          ('azimuthal', [ccrs.Stereographic, ccrs.NorthPolarStereo,
                         ccrs.SouthPolarStereo, ccrs.Gnomonic, ccrs.Orthographic
                         ]),
          ('misc', [ccrs.InterruptedGoodeHomolosine]),
          ]


all_projections_in_groups = list(itertools.chain.from_iterable([g[1] for g in groups]))


if __name__ == '__main__':
    fname = os.path.join(os.path.dirname(__file__), 'source',
                         'crs', 'projections.rst')
    table = open(fname, 'w')

    table.write('.. _cartopy_projections:\n\n')
    table.write('Cartopy projection list\n')
    table.write('=======================\n\n\n')

    prj_class_sorter = lambda cls: (PRJ_SORT_ORDER.get(cls.__name__, []), cls.__name__)
    for prj in sorted(find_projections(), key=prj_class_sorter):
        name = prj.__name__
#        print prj in SPECIAL_CASES, prj in all_projections_in_groups, prj

        # put the class documentation on the left, and a sidebar on the right.

        aspect = (np.diff(prj().x_limits) / np.diff(prj().y_limits))[0]
        width = 3 * aspect
        if width == int(width):
            width = int(width)

        table.write(name + '\n')
        table.write('-' * len(name) + '\n\n')

        table.write('.. autoclass:: cartopy.crs.%s\n' % name)

#        table.write('Ipsum lorum....')

#        table.write("""\n\n
#
#.. sidebar:: Example
#""")

        for instance_creation_code in SPECIAL_CASES.get(prj, ['%s()' % name]):
            code = """
.. plot::

    import matplotlib.pyplot as plt
    import cartopy.crs as ccrs

    plt.figure(figsize=({width}, 3))
    ax = plt.axes(projection=ccrs.{proj_constructor})
    ax.coastlines(resolution={coastline_resolution!r})
    ax.gridlines()

\n""".format(width=width, proj_constructor=instance_creation_code,
             coastline_resolution=COASTLINE_RESOLUTION.get(prj, '110m'))

            table.write(code)

########NEW FILE########
__FILENAME__ = conf
# (C) British Crown Copyright 2011 - 2013, Met Office
#
# This file is part of cartopy.
#
# cartopy is free software: you can redistribute it and/or modify it under
# the terms of the GNU Lesser General Public License as published by the
# Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# cartopy is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Lesser General Public License for more details.
#
# You should have received a copy of the GNU Lesser General Public License
# along with cartopy.  If not, see <http://www.gnu.org/licenses/>.


# -*- coding: utf-8 -*-
#
# cartopy documentation build configuration file, created by
# sphinx-quickstart on Thu Aug 16 09:41:05 2012.
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
extensions = [
              'cartopy.sphinxext.summarise_package',
              'cartopy.sphinxext.gallery',
              'sphinx.ext.autodoc',
              'sphinx.ext.doctest',
              'sphinx.ext.intersphinx',
              'sphinx.ext.coverage',
              'sphinx.ext.viewcode',
              'sphinx.ext.extlinks',
              'matplotlib.sphinxext.plot_directive'
              ]

import matplotlib
matplotlib.use('Agg')

# Add any paths that contain templates here, relative to this directory.
templates_path = ['_templates']

# The suffix of source filenames.
source_suffix = '.rst'

# The encoding of source files.
#source_encoding = 'utf-8-sig'

# The master toctree document.
master_doc = 'index'

# General information about the project.
project = u'cartopy'
copyright = u'2011 - 2013 British Crown Copyright' # the template will need updating if this is changed

# The version info for the project you're documenting, acts as replacement for
# |version| and |release|, also used in various other places throughout the
# built documents.
#
# The short X.Y version.
import cartopy
version = cartopy.__version__
# The full version, including alpha/beta/rc tags.
release = cartopy.__version__

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
exclude_patterns = []

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
html_theme = 'sphinxdoc'

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
html_show_sphinx = False

# If true, "(C) Copyright ..." is shown in the HTML footer. Default is True.
#html_show_copyright = True

# If true, an OpenSearch description file will be output, and all pages will
# contain a <link> tag referring to it.  The value of this option must be the
# base URL from which the finished HTML is served.
#html_use_opensearch = ''

# This is the file name suffix for HTML files (e.g. ".xhtml").
#html_file_suffix = None

# Output file base name for HTML help builder.
htmlhelp_basename = 'cartopydoc'

html_context = {'rellinks': [('genindex', 'General Index', 'I', 'index'),
                             ('cartopy_outline', 'Module outline', 'O', 'outline')]}


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
  ('index', 'cartopy.tex', u'Cartopy Introduction',
   u'Philip Elson, Richard Hattersley', 'manual', False),
  ('introductory_examples/index', 'cartopy_examples.tex', u'Cartopy examples',
   u'Philip Elson, Richard Hattersley', 'manual', True)
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
    ('index', 'cartopy', u'cartopy Documentation',
     [u'Philip Elson, Richard Hattersley'], 1)
]

# If true, show URL addresses after external links.
#man_show_urls = False


# -- Options for Texinfo output ------------------------------------------------

# Grouping the document tree into Texinfo files. List of tuples
# (source start file, target name, title, author,
#  dir menu entry, description, category)
texinfo_documents = [
  ('index', 'cartopy', u'cartopy Documentation',
   u'Philip Elson, Richard Hattersley', 'cartopy', 'One line description of project.',
   'Miscellaneous'),
]

# Documents to append as an appendix to all manuals.
#texinfo_appendices = []

# If false, no module index is generated.
#texinfo_domain_indices = True

# How to display URL addresses: 'footnote', 'no', or 'inline'.
#texinfo_show_urls = 'footnote'


# -- Options for Epub output ---------------------------------------------------

# Bibliographic Dublin Core info.
epub_title = u'cartopy'
epub_author = u'Philip Elson, Richard Hattersley'
epub_publisher = u'Philip Elson, Richard Hattersley'
epub_copyright = u'2012, Philip Elson, Richard Hattersley'

# The language of the text. It defaults to the language option
# or en if the language is not set.
#epub_language = ''

# The scheme of the identifier. Typical schemes are ISBN or URL.
#epub_scheme = ''

# The unique identifier of the text. This can be a ISBN number
# or the project homepage.
#epub_identifier = ''

# A unique identification for the text.
#epub_uid = ''

# A tuple containing the cover image and cover page html template filenames.
#epub_cover = ()

# HTML files that should be inserted before the pages created by sphinx.
# The format is a list of tuples containing the path and title.
#epub_pre_files = []

# HTML files shat should be inserted after the pages created by sphinx.
# The format is a list of tuples containing the path and title.
#epub_post_files = []

# A list of files that should not be packed into the epub file.
#epub_exclude_files = []

# The depth of the table of contents in toc.ncx.
#epub_tocdepth = 3

# Allow duplicate toc entries.
#epub_tocdup = True


# Example configuration for intersphinx: refer to the Python standard library.
intersphinx_mapping = {'python': ('http://docs.python.org/2', None),
                       'matplotlib': ('http://matplotlib.org', None)}





############ extlinks extension ############
extlinks = {'issues': ('https://github.com/SciTools/cartopy/issues?milestone=&state=open&labels=%s',
                      'issues labeled with '),
            'issue': ('https://github.com/SciTools/cartopy/issues/%s', 'Issue #'),
            'pull': ('https://github.com/SciTools/cartopy/pull/%s', 'PR #'),
            }



############ package summary extension ###########

summarise_package_names = ['cartopy']
summarise_package_exclude_directories = [['tests', 'examples', 'sphinxext']]
summarise_package_fnames = ['cartopy_outline.rst']


############ gallery/examples extension ###########

#gallery_allowed_tags = None
#gallery_tag_order = None
gallery_name = 'gallery.rst'
examples_package_name = 'cartopy.examples'


############ plot directive ##############

plot_html_show_formats = False
plot_rcparams = {'figure.autolayout': True}
plot_formats = (('thumb.png', 20),
                'png',
                'pdf'
                )


############ autodoc config ##############

autoclass_content = 'both'

########NEW FILE########
__FILENAME__ = crs
# (C) British Crown Copyright 2011 - 2012, Met Office
#
# This file is part of cartopy.
#
# cartopy is free software: you can redistribute it and/or modify it under
# the terms of the GNU Lesser General Public License as published by the
# Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# cartopy is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Lesser General Public License for more details.
#
# You should have received a copy of the GNU Lesser General Public License
# along with cartopy.  If not, see <http://www.gnu.org/licenses/>.


"""
The crs module defines Coordinate Reference Systems and the transformations
between them.

"""
from abc import ABCMeta, abstractproperty
import math
import warnings

import numpy as np
import shapely.geometry as sgeom
from shapely.geometry.polygon import LinearRing
from shapely.prepared import prep

from cartopy._crs import CRS, Geocentric, Geodetic, Globe, PROJ4_RELEASE
import cartopy.trace


__document_these__ = ['CRS', 'Geocentric', 'Geodetic', 'Globe']


class RotatedGeodetic(CRS):
    """
    Defines a rotated latitude/longitude coordinate system with spherical
    topology and geographical distance.

    Coordinates are measured in degrees.

    """
    def __init__(self, pole_longitude, pole_latitude, globe=None):
        """
        Create a RotatedGeodetic CRS.

        Args:

            * pole_longitude - Pole longitude position, in unrotated degrees.
            * pole_latitude - Pole latitude position, in unrotated degrees.

        Kwargs:

            * globe - An optional :class:`cartopy.crs.Globe`.
                      Defaults to a "WGS84" datum.

        """
        proj4_params = [('proj', 'ob_tran'), ('o_proj', 'latlon'),
                        ('o_lon_p', 0), ('o_lat_p', pole_latitude),
                        ('lon_0', 180 + pole_longitude),
                        ('to_meter', math.radians(1))]
        globe = globe or Globe(datum='WGS84')
        super(RotatedGeodetic, self).__init__(proj4_params, globe=globe)


class Projection(CRS):
    """
    Defines a projected coordinate system with flat topology and Euclidean
    distance.

    """
    __metaclass__ = ABCMeta

    _method_map = {
        'Point': '_project_point',
        'LineString': '_project_line_string',
        'LinearRing': '_project_linear_ring',
        'Polygon': '_project_polygon',
        'MultiPoint': '_project_multipoint',
        'MultiLineString': '_project_multiline',
        'MultiPolygon': '_project_multipolygon',
    }

    @abstractproperty
    def boundary(self):
        pass

    @abstractproperty
    def threshold(self):
        pass

    @abstractproperty
    def x_limits(self):
        pass

    @abstractproperty
    def y_limits(self):
        pass

    @property
    def cw_boundary(self):
        try:
            boundary = self._cw_boundary
        except AttributeError:
            boundary = sgeom.LineString(self.boundary)
            self._cw_boundary = boundary
        return boundary

    @property
    def ccw_boundary(self):
        try:
            boundary = self._ccw_boundary
        except AttributeError:
            boundary = sgeom.LineString(list(self.boundary.coords)[::-1])
            self._ccw_boundary = boundary
        return boundary

    @property
    def domain(self):
        try:
            domain = self._domain
        except AttributeError:
            domain = self._domain = sgeom.Polygon(self.boundary)
        return domain

    def _as_mpl_axes(self):
        import cartopy.mpl.geoaxes as geoaxes
        return geoaxes.GeoAxes, {'map_projection': self}

    def project_geometry(self, geometry, src_crs=None):
        """
        Projects the given geometry into this projection.

        :param geometry: The geometry to (re-)project.
        :param src_crs: The source CRS, or geodetic CRS if None.
        :rtype: Shapely geometry.

        If src_crs is None, the source CRS is assumed to be a geodetic
        version of the target CRS.

        """
        if src_crs is None:
            src_crs = self.as_geodetic()
        elif not isinstance(src_crs, CRS):
            raise TypeError('Source CRS must be an instance of CRS'
                            ' or one of its subclasses, or None.')
        geom_type = geometry.geom_type
        method_name = self._method_map.get(geom_type)
        if not method_name:
            raise ValueError('Unsupported geometry '
                             'type {!r}'.format(geom_type))
        return getattr(self, method_name)(geometry, src_crs)

    def _project_point(self, point, src_crs):
        return sgeom.Point(*self.transform_point(point.x, point.y, src_crs))

    def _project_line_string(self, geometry, src_crs):
        return cartopy.trace.project_linear(geometry, src_crs, self)

    def _project_linear_ring(self, linear_ring, src_crs):
        """
        Projects the given LinearRing from the src_crs into this CRS and
        returns the resultant LinearRing or MultiLineString.

        """
        # 1) Resolve the initial lines into projected segments
        # 1abc
        # def23ghi
        # jkl41
        multi_line_string = cartopy.trace.project_linear(linear_ring,
                                                         src_crs, self)

        # 2) Simplify the segments where appropriate.
        if len(multi_line_string) > 1:
            # Stitch together segments which are close to continuous.
            # This is important when:
            # 1) The first source point projects into the map and the
            # ring has been cut by the boundary.
            # Continuing the example from above this gives:
            #   def23ghi
            #   jkl41abc
            # 2) The cut ends of segments are too close to reliably
            # place into an order along the boundary.

            # Threshold for whether a point is close enough to be the same
            # point as another.
            threshold = max(np.abs(self.x_limits + self.y_limits)) * 1e-5

            line_strings = list(multi_line_string)
            any_modified = False
            i = 0
            while i < len(line_strings):
                modified = False
                j = 0
                while j < len(line_strings):
                    if i != j and np.allclose(line_strings[i].coords[0],
                                              line_strings[j].coords[-1],
                                              atol=threshold):
                        last_coords = list(line_strings[j].coords)
                        first_coords = list(line_strings[i].coords)[1:]
                        combo = sgeom.LineString(last_coords + first_coords)
                        if j < i:
                            i, j = j, i
                        del line_strings[j], line_strings[i]
                        line_strings.append(combo)
                        modified = True
                        any_modified = True
                        break
                    else:
                        j += 1
                if not modified:
                    i += 1
            if any_modified:
                multi_line_string = sgeom.MultiLineString(line_strings)

        # 3) Check for a single resulting ring.
        if (len(multi_line_string) == 1 and
                len(multi_line_string[0].coords) > 3 and
                np.allclose(multi_line_string[0].coords[0],
                            multi_line_string[0].coords[-1])):
            result_geometry = LinearRing(multi_line_string[0].coords[:-1])
        else:
            result_geometry = multi_line_string

        return result_geometry

    def _project_multipoint(self, geometry, src_crs):
        geoms = []
        for geom in geometry.geoms:
            geoms.append(self._project_point(geom, src_crs))
        if geoms:
            return sgeom.MultiPoint(geoms)
        else:
            return sgeom.MultiPoint()

    def _project_multiline(self, geometry, src_crs):
        geoms = []
        for geom in geometry.geoms:
            r = self._project_line_string(geom, src_crs)
            if r:
                geoms.extend(r.geoms)
        if geoms:
            return sgeom.MultiLineString(geoms)
        else:
            return []

    def _project_multipolygon(self, geometry, src_crs):
        geoms = []
        for geom in geometry.geoms:
            r = self._project_polygon(geom, src_crs)
            if r:
                geoms.extend(r.geoms)
        if geoms:
            result = sgeom.MultiPolygon(geoms)
        else:
            result = sgeom.MultiPolygon()
        return result

    def _project_polygon(self, polygon, src_crs):
        """
        Returns the projected polygon(s) derived from the given polygon.

        """
        # Determine orientation of polygon.
        # TODO: Consider checking the internal rings have the opposite
        # orientation to the external rings?
        if src_crs.is_geodetic():
            is_ccw = True
        else:
            is_ccw = polygon.exterior.is_ccw

        # Project the polygon exterior/interior rings.
        # Each source ring will result in either a ring, or one or more
        # lines.
        rings = []
        multi_lines = []
        for src_ring in [polygon.exterior] + list(polygon.interiors):
            geometry = self._project_linear_ring(src_ring, src_crs)
            if geometry.geom_type == 'LinearRing':
                rings.append(geometry)
            else:
                multi_lines.append(geometry)

        # Convert any lines to rings by attaching them to the boundary.
        if multi_lines:
            rings.extend(self._attach_lines_to_boundary(multi_lines, is_ccw))

        # Resolve all the inside vs. outside rings, and convert to the
        # final MultiPolygon.
        return self._rings_to_multi_polygon(rings, is_ccw)

    def _attach_lines_to_boundary(self, multi_line_strings, is_ccw):
        """
        Returns a list of LinearRings by attaching the ends of the given lines
        to the boundary, paying attention to the traversal directions of the
        lines and boundary.

        """
        # Accumulate all the boundary and segment end points, along with
        # their distance along the boundary.
        edge_things = []

        # Get the boundary as a LineString of the correct orientation
        # so we can compute distances along it.
        if is_ccw:
            boundary = self.ccw_boundary
        else:
            boundary = self.cw_boundary

        def boundary_distance(xy):
            return boundary.project(sgeom.Point(*xy))

        # Squash all the LineStrings into a single list.
        line_strings = []
        for multi_line_string in multi_line_strings:
            line_strings.extend(multi_line_string)

        # Record the positions of all the segment ends
        for i, line_string in enumerate(line_strings):
            first_dist = boundary_distance(line_string.coords[0])
            thing = _Thing(first_dist, False,
                           (i, 'first', line_string.coords[0]))
            edge_things.append(thing)
            last_dist = boundary_distance(line_string.coords[-1])
            thing = _Thing(last_dist, False,
                           (i, 'last', line_string.coords[-1]))
            edge_things.append(thing)

        # Record the positions of all the boundary vertices
        for xy in list(boundary.coords)[:-1]:
            point = sgeom.Point(*xy)
            dist = boundary.project(point)
            thing = _Thing(dist, True, point)
            edge_things.append(thing)

        # Order everything as if walking around the boundary.
        # NB. We make line end-points take precedence over boundary points
        # to ensure that end-points are still found and followed when they
        # coincide.
        edge_things.sort(key=lambda thing: (thing.distance, thing.kind))
        debug = 0
        if debug:
            print
            print 'Edge things'
            for thing in edge_things:
                print '   ', thing

        to_do = {i: line_string for i, line_string in enumerate(line_strings)}
        done = []
        while to_do:
            i, line_string = to_do.popitem()
            if debug:
                import sys
                sys.stdout.write('+')
                sys.stdout.flush()
                print
                print 'Processing: %s, %s' % (i, line_string)
            filter_fn = lambda t: (t.kind or
                                   t.data[0] != i or
                                   t.data[1] != 'last')
            edge_things = filter(filter_fn, edge_things)

            added_linestring = set()
            while True:
                # Find the distance of the last point
                d_last = boundary_distance(line_string.coords[-1])
                if debug:
                    print '   d_last:', d_last
                next_thing = _find_gt(edge_things, d_last)
                if debug:
                    print '   next_thing:', next_thing
                if next_thing.kind:
                    if debug:
                        print '   adding boundary point'
                    boundary_point = next_thing.data
                    combined_coords = (list(line_string.coords) +
                                       [(boundary_point.x, boundary_point.y)])
                    line_string = sgeom.LineString(combined_coords)
                    # XXX
                    #edge_things.remove(next_thing)
                elif next_thing.data[0] == i:
                    if debug:
                        print '   close loop'
                    done.append(line_string)
                    break
                else:
                    if debug:
                        print '   adding line'
                    j = next_thing.data[0]
                    line_to_append = line_strings[j]
                    # XXX pelson: I think this if statement can be removed
                    if j in to_do:
                        del to_do[j]
                    coords_to_append = list(line_to_append.coords)
                    if next_thing.data[1] == 'last':
                        coords_to_append = coords_to_append[::-1]
                    line_string = sgeom.LineString((list(line_string.coords) +
                                                    coords_to_append))

                    # Catch getting stuck in an infinite loop by checking that
                    # linestring only added once
                    if j not in added_linestring:
                        added_linestring.add(j)
                    else:
                        raise RuntimeError('Unidentified problem with '
                                           'geometry, linestring being '
                                           're-added')

        # filter out any non-valid linear rings
        done = filter(lambda linear_ring: len(linear_ring.coords) > 2, done)

        # XXX Is the last point in each ring actually the same as the first?
        linear_rings = [LinearRing(line) for line in done]

        if debug:
            print '   DONE'

        return linear_rings

    def _rings_to_multi_polygon(self, rings, is_ccw):
        exterior_rings = []
        interior_rings = []
        for ring in rings:
            if ring.is_ccw != is_ccw:
                interior_rings.append(ring)
            else:
                exterior_rings.append(ring)

        polygon_bits = []

        # Turn all the exterior rings into polygon definitions,
        # "slurping up" any interior rings they contain.
        for exterior_ring in exterior_rings:
            polygon = sgeom.Polygon(exterior_ring)
            prep_polygon = prep(polygon)
            holes = []
            for interior_ring in interior_rings[:]:
                if prep_polygon.contains(interior_ring):
                    holes.append(interior_ring)
                    interior_rings.remove(interior_ring)
            polygon_bits.append((exterior_ring.coords,
                                 [ring.coords for ring in holes]))

        # Any left over "interior" rings need "inverting" with respect
        # to the boundary.
        if interior_rings:
            boundary_poly = self.domain
            x3, y3, x4, y4 = boundary_poly.bounds
            bx = (x4 - x3) * 0.1
            by = (y4 - y3) * 0.1
            x3 -= bx
            y3 -= by
            x4 += bx
            y4 += by
            for ring in interior_rings:
                polygon = sgeom.Polygon(ring)
                if polygon.is_valid:
                    x1, y1, x2, y2 = polygon.bounds
                    bx = (x2 - x1) * 0.1
                    by = (y2 - y1) * 0.1
                    x1 -= bx
                    y1 -= by
                    x2 += bx
                    y2 += by
                    box = sgeom.box(min(x1, x3), min(y1, y3),
                                    max(x2, x4), max(y2, y4))

                    # Invert the polygon
                    polygon = box.difference(polygon)

                    # Intersect the inverted polygon with the boundary
                    polygon = boundary_poly.intersection(polygon)

                    if not polygon.is_empty:
                        polygon_bits.append(polygon)

        if polygon_bits:
            multi_poly = sgeom.MultiPolygon(polygon_bits)
        else:
            multi_poly = sgeom.MultiPolygon()
        return multi_poly

    def quick_vertices_transform(self, vertices, src_crs):
        """
        Where possible, return a vertices array transformed to this CRS from
        the given vertices array of shape ``(n, 2)`` and the source CRS.

        .. important::

            This method may return None to indicate that the vertices cannot
            be transformed quickly, and a more complex geometry transformation
            is required (see :meth:`cartopy.crs.Projection.project_geometry`).

        """
        return_value = None

        if self == src_crs:
            x = vertices[:, 0]
            y = vertices[:, 1]
            x_limits = self.x_limits
            y_limits = self.y_limits
            if (x.min() >= x_limits[0] and x.max() <= x_limits[1]
                    and y.min() >= y_limits[0] and y.max() <= y_limits[1]):
                return_value = vertices

        return return_value


class _RectangularProjection(Projection):
    """
    The abstract superclass of projections with a rectangular domain which
    is symmetric about the origin.

    """
    def __init__(self, proj4_params, half_width, half_height, globe=None):
        self._half_width = half_width
        self._half_height = half_height
        super(_RectangularProjection, self).__init__(proj4_params, globe=globe)

    @property
    def boundary(self):
        # XXX Should this be a LinearRing?
        w, h = self._half_width, self._half_height
        return sgeom.LineString([(-w, -h), (-w, h), (w, h), (w, -h), (-w, -h)])

    @property
    def x_limits(self):
        return (-self._half_width, self._half_width)

    @property
    def y_limits(self):
        return (-self._half_height, self._half_height)


class _CylindricalProjection(_RectangularProjection):
    """
    The abstract class which denotes cylindrical projections where we
    want to allow x values to wrap around.

    """


class PlateCarree(_CylindricalProjection):
    def __init__(self, central_longitude=0.0, globe=None):
        proj4_params = [('proj', 'eqc'), ('lon_0', central_longitude)]
        if globe is None:
            globe = Globe(semimajor_axis=math.degrees(1))
        x_max = math.radians(globe.semimajor_axis or 6378137.0) * 180
        y_max = math.radians(globe.semimajor_axis or 6378137.0) * 90
        # Set the threshold around 0.5 if the x max is 180.
        self._threshold = x_max / 360.
        super(PlateCarree, self).__init__(proj4_params, x_max, y_max,
                                          globe=globe)

    @property
    def threshold(self):
        return self._threshold

    def _bbox_and_offset(self, other_plate_carree):
        """
        Returns a pair of (xmin, xmax) pairs and an offset which can be used
        for identification of whether data in ``other_plate_carree`` needs
        to be transformed to wrap appropriately.

        >>> import cartopy.crs as ccrs
        >>> src = ccrs.PlateCarree(central_longitude=10)
        >>> bboxes, offset = ccrs.PlateCarree()._bbox_and_offset(src)
        >>> print bboxes
        [[-180.0, -170.0], [-170.0, 180.0]]
        >>> print offset
        10.0

        The returned values are longitudes in ``other_plate_carree``'s
        coordinate system.

        .. important::

            The two CRSs must be identical in every way, other than their
            central longitudes. No checking of this is done.

        """
        self_lon_0 = self.proj4_params['lon_0']
        other_lon_0 = other_plate_carree.proj4_params['lon_0']

        lon_0_offset = other_lon_0 - self_lon_0

        lon_lower_bound_0 = self.x_limits[0]
        lon_lower_bound_1 = (other_plate_carree.x_limits[0] + lon_0_offset)

        if lon_lower_bound_1 < self.x_limits[0]:
            lon_lower_bound_1 += np.diff(self.x_limits)[0]

        lon_lower_bound_0, lon_lower_bound_1 = sorted(
            [lon_lower_bound_0, lon_lower_bound_1])

        bbox = [[lon_lower_bound_0, lon_lower_bound_1],
                [lon_lower_bound_1, lon_lower_bound_0]]

        bbox[1][1] += np.diff(self.x_limits)[0]

        return bbox, lon_0_offset

    def quick_vertices_transform(self, vertices, src_crs):
        return_value = super(PlateCarree,
                             self).quick_vertices_transform(vertices, src_crs)

        # Optimise the PlateCarree -> PlateCarree case where no
        # wrapping or interpolation needs to take place.
        if return_value is None and isinstance(src_crs, PlateCarree):
            self_params = self.proj4_params.copy()
            src_params = src_crs.proj4_params.copy()
            self_params.pop('lon_0'), src_params.pop('lon_0')

            xs, ys = vertices[:, 0], vertices[:, 1]

            potential = (self_params == src_params and
                         self.y_limits[0] <= ys.min() and
                         self.y_limits[1] >= ys.max())

            if potential:
                mod = np.diff(src_crs.x_limits)[0]
                bboxes, proj_offset = self._bbox_and_offset(src_crs)
                x_lim = xs.min(), xs.max()
                y_lim = ys.min(), ys.max()
                for poly in bboxes:
                    # Arbitrarily choose the number of moduli to look
                    # above and below the -180->180 range. If data is beyond
                    # this range, we're not going to transform it quickly.
                    for i in [-1, 0, 1, 2]:
                        offset = mod * i - proj_offset
                        if ((poly[0] + offset) <= x_lim[0]
                                and (poly[1] + offset) >= x_lim[1]):
                            return_value = vertices + [[-offset, 0]]
                            break
                    if return_value is not None:
                        break

        return return_value


class TransverseMercator(Projection):
    """
    A Transverse Mercator projection.

    """
    def __init__(self, central_longitude=0.0, central_latitude=0.0,
                 false_easting=0.0, false_northing=0.0,
                 scale_factor=1.0, globe=None):
        """
        Kwargs:

            * central_longitude - The true longitude of the central meridian in
                                  degrees. Defaults to 0.
            * central_latitude - The true latitude of the planar origin in
                                 degrees. Defaults to 0.
            * false_easting - X offset from the planar origin in metres.
                              Defaults to 0.
            * false_northing - Y offset from the planar origin in metres.
                               Defaults to 0.
            * scale_factor - Scale factor at the central meridian. Defaults
                             to 1.
            * globe - An instance of :class:`cartopy.crs.Globe`. If omitted, a
                      default globe is created.

        """
        proj4_params = [('proj', 'tmerc'), ('lon_0', central_longitude),
                        ('lat_0', central_latitude), ('k', scale_factor),
                        ('x_0', false_easting), ('y_0', false_northing),
                        ('units', 'm')]
        super(TransverseMercator, self).__init__(proj4_params, globe=globe)

    @property
    def threshold(self):
        return 1e4

    @property
    def boundary(self):
        x0, x1 = self.x_limits
        y0, y1 = self.y_limits
        return sgeom.LineString([(x0, y0), (x0, y1),
                                 (x1, y1), (x1, y0),
                                 (x0, y0)])

    @property
    def x_limits(self):
        return (-2e7, 2e7)

    @property
    def y_limits(self):
        return (-1e7, 1e7)


class OSGB(TransverseMercator):
    def __init__(self):
        super(OSGB, self).__init__(central_longitude=-2, central_latitude=49,
                                   scale_factor=0.9996012717,
                                   false_easting=400000,
                                   false_northing=-100000,
                                   globe=Globe(datum='OSGB36', ellipse='airy'))

    @property
    def boundary(self):
        w = self.x_limits[1] - self.x_limits[0]
        h = self.y_limits[1] - self.y_limits[0]
        return sgeom.LineString([(0, 0), (0, h), (w, h), (w, 0), (0, 0)])

    @property
    def x_limits(self):
        return (0, 7e5)

    @property
    def y_limits(self):
        return (0, 13e5)


class OSNI(TransverseMercator):
    def __init__(self):
        globe = Globe(semimajor_axis=6377340.189,
                      semiminor_axis=6356034.447938534)
        super(OSNI, self).__init__(central_longitude=-8,
                                   central_latitude=53.5,
                                   scale_factor=1.000035,
                                   false_easting=200000,
                                   false_northing=250000,
                                   globe=globe)

    @property
    def boundary(self):
        w = self.x_limits[1] - self.x_limits[0]
        h = self.y_limits[1] - self.y_limits[0]
        return sgeom.LineString([(0, 0), (0, h), (w, h), (w, 0), (0, 0)])

    @property
    def x_limits(self):
        return (18814.9667, 386062.3293)

    @property
    def y_limits(self):
        return (11764.8481, 464720.9559)


class UTM(Projection):
    """
    Universal Transverse Mercator projection.

    """
    def __init__(self, zone, southern_hemisphere=False, globe=None):
        """
        Kwargs:

            * zone - the numeric zone of the UTM required.

            * globe - An instance of :class:`cartopy.crs.Globe`. If omitted, a
                      default globe is created.

            * southern_hemisphere - set to True if the zone is in the southern
                                    hemisphere, defaults to False.

        """
        proj4_params = [('proj', 'utm'),
                        ('units', 'm'),
                        ('zone', zone)]
        if southern_hemisphere:
            proj4_params.append(('south', None))
        super(UTM, self).__init__(proj4_params, globe=globe)

    @property
    def boundary(self):
        x0, x1 = self.x_limits
        y0, y1 = self.y_limits
        return sgeom.LineString([(x0, y0), (x0, y1),
                                 (x1, y1), (x1, y0),
                                 (x0, y0)])

    @property
    def threshold(self):
        return 1e2

    @property
    def x_limits(self):
        easting = 5e5
        # allow 50% overflow
        return (0 - easting/2, 2 * easting + easting/2)

    @property
    def y_limits(self):
        northing = 1e7
        # allow 50% overflow
        return (0 - northing, 2 * northing + northing/2)


class EuroPP(UTM):
    """
    UTM Zone 32 projection for EuroPP domain.

    Ellipsoid is International 1924, Datum is ED50.

    """
    def __init__(self):
        globe = Globe(ellipse='intl')
        super(EuroPP, self).__init__(32, globe=globe)


class Mercator(Projection):
    """
    A Mercator projection.

    """

    def __init__(self, central_longitude=0.0,
                 min_latitude=-80.0, max_latitude=84.0,
                 globe=None):
        """
        Kwargs:

            * central_longitude - the central longitude. Defaults to 0.
            * min_latitude - the maximum southerly extent of the projection.
                             Defaults to -80 degrees.
            * max_latitude - the maximum northerly extent of the projection.
                             Defaults to 84 degrees.
            * globe - A :class:`cartopy.crs.Globe`.
                      If omitted, a default globe is created.

        """
        proj4_params = [('proj', 'merc'),
                        ('lon_0', central_longitude),
                        ('k', 1),
                        ('units', 'm')]
        super(Mercator, self).__init__(proj4_params, globe=globe)

        # Calculate limits.
        limits = self.transform_points(Geodetic(),
                                       np.array([-180., 180.]),
                                       np.array([min_latitude, max_latitude]))
        self._xlimits = tuple(limits[..., 0])
        self._ylimits = tuple(limits[..., 1])
        self._threshold = np.diff(self.x_limits)[0] / 720

    def __eq__(self, other):
        res = super(Mercator, self).__eq__(other)
        if hasattr(other, "_ylimits") and hasattr(other, "_xlimits"):
            res = res and self._ylimits == other._ylimits and \
                self._xlimits == other._xlimits
        return res

    def __ne__(self, other):
        return not self == other

    def __hash__(self):
        return hash((self.proj4_init, self._xlimits, self._ylimits))

    @property
    def threshold(self):
        return self._threshold

    @property
    def boundary(self):
        x0, x1 = self.x_limits
        y0, y1 = self.y_limits
        return sgeom.LineString([(x0, y0), (x0, y1),
                                 (x1, y1), (x1, y0),
                                 (x0, y0)])

    @property
    def x_limits(self):
        return self._xlimits

    @property
    def y_limits(self):
        return self._ylimits


GOOGLE_MERCATOR = Mercator(min_latitude=-85.0511287798066,
                           max_latitude=85.0511287798066,
                           globe=Globe(ellipse=None,
                                       semimajor_axis=6378137,
                                       semiminor_axis=6378137,
                                       nadgrids='@null'))


class LambertCylindrical(_RectangularProjection):
    def __init__(self, central_longitude=0.0):
        proj4_params = [('proj', 'cea'), ('lon_0', central_longitude)]
        globe = Globe(semimajor_axis=math.degrees(1))
        super(LambertCylindrical, self).__init__(proj4_params, 180,
                                                 math.degrees(1), globe=globe)

    @property
    def threshold(self):
        return 0.5


class LambertConformal(Projection):
    """
    A Lambert Conformal conic projection.

    """

    def __init__(self, central_longitude=-96.0, central_latitude=39.0,
                 false_easting=0.0, false_northing=0.0,
                 secant_latitudes=(33, 45), globe=None, cutoff=-30):
        """
        Kwargs:

            * central_longitude - The central longitude. Defaults to 0.
            * central_latitude - The central latitude. Defaults to 0.
            * false_easting - X offset from planar origin in metres.
                              Defaults to 0.
            * false_northing - Y offset from planar origin in metres.
                               Defaults to 0.
            * secant_latitudes - The two latitudes of secant intersection.
                                 Defaults to (33, 45).
            * globe - A :class:`cartopy.crs.Globe`.
                      If omitted, a default globe is created.
            * cutoff - Latitude of map cutoff.
                       The map extends to infinity opposite the central pole
                       so we must cut off the map drawing before then.
                       A value of 0 will draw half the globe. Defaults to -30.

        """
        proj4_params = [('proj', 'lcc'),
                        ('lon_0', central_longitude),
                        ('lat_0', central_latitude),
                        ('x_0', false_easting),
                        ('y_0', false_northing)]
        if secant_latitudes is not None:
            proj4_params.append(('lat_1', secant_latitudes[0]))
            proj4_params.append(('lat_2', secant_latitudes[1]))
        super(LambertConformal, self).__init__(proj4_params, globe=globe)

        # are we north or south polar?
        if abs(secant_latitudes[0]) > abs(secant_latitudes[1]):
            poliest_sec = secant_latitudes[0]
        else:
            poliest_sec = secant_latitudes[1]
        plat = 90 if poliest_sec > 0 else -90

        # bounds
        self.cutoff = cutoff
        n = 91
        lons = [0]
        lats = [plat]
        lons.extend(np.linspace(central_longitude - 180 + 0.001,
                                central_longitude + 180 - 0.001, n))
        lats.extend(np.array([cutoff] * n))
        lons.append(0)
        lats.append(plat)

        points = self.transform_points(PlateCarree(),
                                       np.array(lons), np.array(lats))

        self._boundary = sgeom.LineString(points)
        bounds = self._boundary.bounds
        self._x_limits = bounds[0], bounds[2]
        self._y_limits = bounds[1], bounds[3]

    def __eq__(self, other):
        res = super(LambertConformal, self).__eq__(other)
        if hasattr(other, "cutoff"):
            res = res and self.cutoff == other.cutoff
        return res

    def __ne__(self, other):
        return not self == other

    def __hash__(self):
        return hash((self.proj4_init, self.cutoff))

    @property
    def boundary(self):
        return self._boundary

    @property
    def threshold(self):
        return 1e5

    @property
    def x_limits(self):
        return self._x_limits

    @property
    def y_limits(self):
        return self._y_limits


class Miller(_RectangularProjection):
    def __init__(self, central_longitude=0.0):
        proj4_params = [('proj', 'mill'), ('lon_0', central_longitude)]
        globe = Globe(semimajor_axis=math.degrees(1))
        # XXX How can we derive the vertical limit of 131.98?
        super(Miller, self).__init__(proj4_params, 180, 131.98, globe=globe)

    @property
    def threshold(self):
        return 0.5


class RotatedPole(_CylindricalProjection):
    def __init__(self, pole_longitude=0.0, pole_latitude=90.0, globe=None):
        proj4_params = [('proj', 'ob_tran'), ('o_proj', 'latlon'),
                        ('o_lon_p', 0), ('o_lat_p', pole_latitude),
                        ('lon_0', 180 + pole_longitude),
                        ('to_meter', math.radians(1))]
        super(RotatedPole, self).__init__(proj4_params, 180, 90, globe=globe)

    @property
    def threshold(self):
        return 0.5


class Gnomonic(Projection):
    def __init__(self, central_latitude=0.0, globe=None):
        proj4_params = [('proj', 'gnom'), ('lat_0', central_latitude)]
        super(Gnomonic, self).__init__(proj4_params, globe=globe)
        self._max = 5e7

    @property
    def boundary(self):
        return sgeom.Point(0, 0).buffer(self._max).exterior

    @property
    def threshold(self):
        return 1e5

    @property
    def x_limits(self):
        return (-self._max, self._max)

    @property
    def y_limits(self):
        return (-self._max, self._max)


class Stereographic(Projection):
    def __init__(self, central_latitude=0.0, central_longitude=0.0,
                 false_easting=0.0, false_northing=0.0,
                 true_scale_latitude=None, globe=None):
        proj4_params = [('proj', 'stere'), ('lat_0', central_latitude),
                        ('lon_0', central_longitude),
                        ('x_0', false_easting), ('y_0', false_northing)]
        if true_scale_latitude:
            proj4_params.append(('lat_ts', true_scale_latitude))
        super(Stereographic, self).__init__(proj4_params, globe=globe)

        # TODO: Factor this out, particularly if there are other places using
        # it (currently: Stereographic & Geostationary). (#340)
        def ellipse(semimajor=2, semiminor=1, easting=0, northing=0, n=200):
            t = np.linspace(0, 2 * np.pi, n)
            coords = np.vstack([semimajor * np.cos(t), semiminor * np.sin(t)])
            coords += ([easting], [northing])
            return coords

        # TODO: Let the globe return the semimajor axis always.
        a = np.float(self.globe.semimajor_axis or 6378137.0)
        b = np.float(self.globe.semiminor_axis or 6356752.3142)

        # Note: The magic number has been picked to maintain consistent
        # behaviour with a wgs84 globe. There is no guarantee that the scaling
        # should even be linear.
        x_axis_offset = 5e7 / 6378137.
        y_axis_offset = 5e7 / 6356752.3142
        self._x_limits = (-a * x_axis_offset + false_easting,
                          a * x_axis_offset + false_easting)
        self._y_limits = (-b * y_axis_offset + false_northing,
                          b * y_axis_offset + false_northing)
        if self._x_limits[1] == self._y_limits[1]:
            point = sgeom.Point(false_easting, false_northing)
            self._boundary = point.buffer(self._x_limits[1]).exterior
        else:
            coords = ellipse(self._x_limits[1], self._y_limits[1],
                             false_easting, false_northing, 90)
            coords = tuple(tuple(pair) for pair in coords.T)
            self._boundary = sgeom.polygon.LinearRing(coords)
        self._threshold = np.diff(self._x_limits)[0] * 1e-3

    @property
    def boundary(self):
        return self._boundary

    @property
    def threshold(self):
        return self._threshold

    @property
    def x_limits(self):
        return self._x_limits

    @property
    def y_limits(self):
        return self._y_limits


class NorthPolarStereo(Stereographic):
    def __init__(self, central_longitude=0.0, globe=None):
        super(NorthPolarStereo, self).__init__(
            central_latitude=90,
            central_longitude=central_longitude, globe=globe)


class SouthPolarStereo(Stereographic):
    def __init__(self, central_longitude=0.0, globe=None):
        super(SouthPolarStereo, self).__init__(
            central_latitude=-90,
            central_longitude=central_longitude, globe=globe)


class Orthographic(Projection):
    def __init__(self, central_longitude=0.0, central_latitude=0.0,
                 globe=None):
        proj4_params = [('proj', 'ortho'), ('lon_0', central_longitude),
                        ('lat_0', central_latitude)]
        super(Orthographic, self).__init__(proj4_params, globe=globe)
        self._max = 6.4e6

    @property
    def boundary(self):
        return sgeom.Point(0, 0).buffer(self._max).exterior

    @property
    def threshold(self):
        return 1e5

    @property
    def x_limits(self):
        return (-self._max, self._max)

    @property
    def y_limits(self):
        return (-self._max, self._max)


class _WarpedRectangularProjection(Projection):
    def __init__(self, proj4_params, central_longitude, globe=None):
        super(_WarpedRectangularProjection, self).__init__(proj4_params,
                                                           globe=globe)

        # Obtain boundary points
        points = []
        n = 91
        geodetic_crs = self.as_geodetic()
        for lat in np.linspace(-90, 90, n):
            points.append(
                self.transform_point(180 + central_longitude,
                                     lat, geodetic_crs)
            )
        for lat in np.linspace(90, -90, n):
            points.append(
                self.transform_point(-180 + central_longitude,
                                     lat, geodetic_crs)
            )
        points.append(
            self.transform_point(180 + central_longitude, -90, geodetic_crs))

        self._boundary = sgeom.LineString(points[::-1])

        x = [p[0] for p in points]
        y = [p[1] for p in points]
        self._x_limits = min(x), max(x)
        self._y_limits = min(y), max(y)

    @property
    def boundary(self):
        return self._boundary

    @property
    def x_limits(self):
        return self._x_limits

    @property
    def y_limits(self):
        return self._y_limits


class Mollweide(_WarpedRectangularProjection):
    def __init__(self, central_longitude=0, globe=None):
        proj4_params = [('proj', 'moll'), ('lon_0', central_longitude)]
        super(Mollweide, self).__init__(proj4_params, central_longitude,
                                        globe=globe)

    @property
    def threshold(self):
        return 1e5


class Robinson(_WarpedRectangularProjection):
    def __init__(self, central_longitude=0, globe=None):
        # Warn when using Robinson with proj4 4.8 due to discontinuity at
        # 40 deg N introduced by incomplete fix to issue #113 (see
        # https://trac.osgeo.org/proj/ticket/113).
        import re
        match = re.search(r"\d\.\d", PROJ4_RELEASE)
        if match is not None:
            proj4_version = float(match.group())
            if 4.8 <= proj4_version < 4.9:
                warnings.warn('The Robinson projection in the v4.8.x series '
                              'of Proj.4 contains a discontinuity at '
                              '40 deg latitude. Use this projection with '
                              'caution.')
        else:
            warnings.warn('Cannot determine Proj.4 version. The Robinson '
                          'projection may be unreliable and should be used '
                          'with caution.')

        proj4_params = [('proj', 'robin'), ('lon_0', central_longitude)]
        super(Robinson, self).__init__(proj4_params, central_longitude,
                                       globe=globe)

    @property
    def threshold(self):
        return 1e4

    def transform_point(self, x, y, src_crs):
        """
        Capture and handle any input NaNs, else invoke parent function,
        :meth:`_WarpedRectangularProjection.transform_point`.

        Needed because input NaNs can trigger a fatal error in the underlying
        implementation of the Robinson projection.

        .. note::

            Although the original can in fact translate (nan, lat) into
            (nan, y-value), this patched version doesn't support that.

        """
        if np.isnan(x) or np.isnan(y):
            result = (np.nan, np.nan)
        else:
            result = super(Robinson, self).transform_point(x, y, src_crs)
        return result

    def transform_points(self, src_crs, x, y, z=None):
        """
        Capture and handle NaNs in input points -- else as parent function,
        :meth:`_WarpedRectangularProjection.transform_points`.

        Needed because input NaNs can trigger a fatal error in the underlying
        implementation of the Robinson projection.

        .. note::

            Although the original can in fact translate (nan, lat) into
            (nan, y-value), this patched version doesn't support that.
            Instead, we invalidate any of the points that contain a NaN.

        """
        input_point_nans = np.isnan(x) | np.isnan(y)
        if z is not None:
            input_point_nans |= np.isnan(z)
        handle_nans = np.any(input_point_nans)
        if handle_nans:
            # Remove NaN points from input data to avoid the error.
            x[input_point_nans] = 0.0
            y[input_point_nans] = 0.0
            if z is not None:
                z[input_point_nans] = 0.0
        result = super(Robinson, self).transform_points(src_crs, x, y, z)
        if handle_nans:
            # Result always has shape (N, 3).
            # Blank out each (whole) point where we had a NaN in the input.
            result[input_point_nans] = np.nan
        return result


class InterruptedGoodeHomolosine(Projection):
    def __init__(self, central_longitude=0, globe=None):
        proj4_params = [('proj', 'igh'), ('lon_0', central_longitude)]
        super(InterruptedGoodeHomolosine, self).__init__(proj4_params,
                                                         globe=globe)

        # Obtain boundary points
        points = []
        n = 31
        geodetic_crs = self.as_geodetic()

        # Right boundary
        for lat in np.linspace(-90, 90, n):
            points.append(self.transform_point(180 + central_longitude,
                                               lat, geodetic_crs))

        # Top boundary
        interrupted_lons = (-40.0,)
        delta = 0.001
        for lon in interrupted_lons:
            for lat in np.linspace(90, 0, n):
                points.append(self.transform_point(lon + delta +
                                                   central_longitude,
                                                   lat, geodetic_crs))
            for lat in np.linspace(0, 90, n):
                points.append(self.transform_point(lon - delta +
                                                   central_longitude,
                                                   lat, geodetic_crs))

        # Left boundary
        for lat in np.linspace(90, -90, n):
            points.append(self.transform_point(-180 + central_longitude,
                                               lat, geodetic_crs))

        # Bottom boundary
        interrupted_lons = (-100.0, -20.0, 80.0)
        delta = 0.001
        for lon in interrupted_lons:
            for lat in np.linspace(-90, 0, n):
                points.append(self.transform_point(lon - delta +
                                                   central_longitude,
                                                   lat, geodetic_crs))
            for lat in np.linspace(0, -90, n):
                points.append(self.transform_point(lon + delta +
                                                   central_longitude,
                                                   lat, geodetic_crs))

        # Close loop
        points.append(self.transform_point(180 + central_longitude, -90,
                                           geodetic_crs))

        self._boundary = sgeom.LineString(points[::-1])

        x = [p[0] for p in points]
        y = [p[1] for p in points]
        self._x_limits = min(x), max(x)
        self._y_limits = min(y), max(y)

    @property
    def boundary(self):
        return self._boundary

    @property
    def threshold(self):
        return 2e4

    @property
    def x_limits(self):
        return self._x_limits

    @property
    def y_limits(self):
        return self._y_limits


class Geostationary(Projection):
    def __init__(self, central_longitude=0.0, satellite_height=35785831,
                 false_easting=0, false_northing=0, globe=None):
        proj4_params = [('proj', 'geos'), ('lon_0', central_longitude),
                        ('lat_0', 0), ('h', satellite_height),
                        ('x_0', false_easting), ('y_0', false_northing),
                        ('units', 'm')]
        super(Geostationary, self).__init__(proj4_params, globe=globe)

        # TODO: Factor this out, particularly if there are other places using
        # it (currently: Stereographic & Geostationary). (#340)
        def ellipse(semimajor=2, semiminor=1, easting=0, northing=0, n=200):
            t = np.linspace(0, 2 * np.pi, n)
            coords = np.vstack([semimajor * np.cos(t), semiminor * np.sin(t)])
            coords += ([easting], [northing])
            return coords

        # TODO: Let the globe return the semimajor axis always.
        a = np.float(self.globe.semimajor_axis or 6378137.0)
        b = np.float(self.globe.semiminor_axis or 6378137.0)
        h = np.float(satellite_height)
        max_x = h * math.atan(a / (a + h))
        max_y = h * math.atan(b / (b + h))

        coords = ellipse(max_x, max_y,
                         false_easting, false_northing, 60)
        coords = tuple(tuple(pair) for pair in coords.T)
        self._boundary = sgeom.polygon.LinearRing(coords)
        self._xlim = self._boundary.bounds[::2]
        self._ylim = self._boundary.bounds[1::2]
        self._threshold = np.diff(self._xlim)[0] * 0.02

    @property
    def boundary(self):
        return self._boundary

    @property
    def threshold(self):
        return self._threshold

    @property
    def x_limits(self):
        return self._xlim

    @property
    def y_limits(self):
        return self._ylim


class _Thing(object):
    def __init__(self, distance, kind, data):
        self.distance = distance
        self.kind = kind
        self.data = data

    def __repr__(self):
        return '_Thing(%r, %r, %s)' % (self.distance, self.kind, self.data)


def _find_gt(a, x):
    for v in a:
        # TODO: Fix the problem of co-incident boundary & line points
        #if v.distance >= x:
        if v.distance > x:
            return v
    return a[0]

########NEW FILE########
__FILENAME__ = arrows
__tags__ = ['Vector data']
import matplotlib.pyplot as plt
import numpy as np

import cartopy
import cartopy.crs as ccrs


def sample_data(shape=(20, 30)):
    """
    Returns ``(x, y, u, v, crs)`` of some vector data
    computed mathematically. The returned crs will be a rotated
    pole CRS, meaning that the vectors will be unevenly spaced in
    regular PlateCarree space.

    """
    crs = ccrs.RotatedPole(pole_longitude=177.5, pole_latitude=37.5)

    x = np.linspace(311.9, 391.1, shape[1])
    y = np.linspace(-23.6, 24.8, shape[0])

    x2d, y2d = np.meshgrid(x, y)
    u = 10 * (2 * np.cos(2 * np.deg2rad(x2d) + 3 * np.deg2rad(y2d + 30)) ** 2)
    v = 20 * np.cos(6 * np.deg2rad(x2d))

    return x, y, u, v, crs


def main():
    ax = plt.axes(projection=ccrs.Orthographic(-10, 45))

    ax.add_feature(cartopy.feature.OCEAN, zorder=0)
    ax.add_feature(cartopy.feature.LAND, zorder=0, edgecolor='black')

    ax.set_global()
    ax.gridlines()

    x, y, u, v, vector_crs = sample_data()
    ax.quiver(x, y, u, v, transform=vector_crs)

    plt.show()


if __name__ == '__main__':
    main()

########NEW FILE########
__FILENAME__ = barbs
__tags__ = ['Vector data']
import matplotlib.pyplot as plt

import cartopy.crs as ccrs
from cartopy.examples.arrows import sample_data


def main():
    ax = plt.axes(projection=ccrs.PlateCarree())
    ax.set_extent([-90, 75, 10, 60])
    ax.stock_img()
    ax.coastlines()

    x, y, u, v, vector_crs = sample_data(shape=(10, 14))
    ax.barbs(x, y, u, v, length=5,
             sizes=dict(emptybarb=0.25, spacing=0.2, height=0.5),
             linewidth=0.95, transform=vector_crs)

    plt.show()


if __name__ == '__main__':
    main()

########NEW FILE########
__FILENAME__ = effects_of_the_ellipse
"""
The effect of badly referencing an ellipse
------------------------------------------

This example demonstrates the effect of referencing your data to an incorrect
ellipse.

First we define two coordinate systems - one using the World Geodetic System
established in 1984 and the other using a spherical globe. Next we extract
data from the Natural Earth land dataset and convert the Geodetic
coordinates (referenced in WGS84) into the respective coordinate systems
that we have defined. Finally, we plot these datasets onto a map assuming
that they are both referenced to the WGS84 ellipse and compare how the
coastlines are shifted as a result of referencing the incorrect ellipse.

"""
__tags__ = ['Lines and polygons']
import cartopy.crs as ccrs
import cartopy.feature
from cartopy.io.img_tiles import MapQuestOpenAerial
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D as Line
from matplotlib.patheffects import Stroke
import numpy as np
import shapely.geometry as sgeom
from shapely.ops import transform as geom_transform


def transform_fn_factory(target_crs, source_crs):
    """
    Return a function which can be used by ``shapely.op.transform``
    to transform the coordinate points of a geometry.

    The function explicitly *does not* do any interpolation or clever
    transformation of the coordinate points, so there is no guarantee
    that the resulting geometry would make any sense.

    """
    def transform_fn(x, y, z=None):
        new_coords = target_crs.transform_points(source_crs,
                                                 np.asanyarray(x),
                                                 np.asanyarray(y))
        return new_coords[:, 0], new_coords[:, 1], new_coords[:, 2]

    return transform_fn


def main():
    # Define the two coordinate systems with different ellipses.
    wgs84 = ccrs.PlateCarree(globe=ccrs.Globe(datum='WGS84',
                                              ellipse='WGS84'))
    sphere = ccrs.PlateCarree(globe=ccrs.Globe(datum='WGS84',
                                               ellipse='sphere'))

    # Define the coordinate system of the data we have from Natural Earth and
    # acquire the 1:10m physical coastline shapefile.
    geodetic = ccrs.Geodetic(globe=ccrs.Globe(datum='WGS84'))
    dataset = cartopy.feature.NaturalEarthFeature(category='physical',
                                                  name='coastline',
                                                  scale='10m')

    # Create a MapQuest map tiler instance, and use its CRS for the GeoAxes.
    tiler = MapQuestOpenAerial()
    ax = plt.axes(projection=tiler.crs)
    plt.title('The effect of incorrectly referencing the Solomon Islands')

    # Pick the area of interest. In our case, roughly the Solomon Islands, and
    # get hold of the coastlines for that area.
    extent = (155, 163, -11.5, -6)
    ax.set_extent(extent, geodetic)
    geoms = list(dataset.intersecting_geometries(extent))

    # Add the MapQuest aerial imagery at zoom level 7.
    ax.add_image(tiler, 7)

    # Transform the geodetic coordinates of the coastlines into the two
    # projections of differing ellipses.
    wgs84_geoms = [geom_transform(transform_fn_factory(wgs84, geodetic),
                                  geom) for geom in geoms]
    sphere_geoms = [geom_transform(transform_fn_factory(sphere, geodetic),
                                   geom) for geom in geoms]

    # Using these differently referenced geometries, assume that they are
    # both referenced to WGS84.
    ax.add_geometries(wgs84_geoms, wgs84, edgecolor='white', color='none')
    ax.add_geometries(sphere_geoms, wgs84, edgecolor='gray', color='none')

    # Create a legend for the coastlines.
    legend_artists = [Line([0], [0], color=color, linewidth=3)
                      for color in ('white', 'gray')]
    legend_texts = ['Correct ellipse\n(WGS84)', 'Incorrect ellipse\n(sphere)']
    legend = plt.legend(legend_artists, legend_texts, fancybox=True,
                        loc='lower left', framealpha=0.75)
    legend.legendPatch.set_facecolor('wheat')

    # Create an inset GeoAxes showing the location of the Solomon Islands.
    sub_ax = plt.axes([0.7, 0.625, 0.2, 0.2], projection=ccrs.PlateCarree())
    sub_ax.set_extent([110, 180, -50, 10], geodetic)

    # Make a nice border around the inset axes.
    effect = Stroke(linewidth=4, foreground='wheat', alpha=0.5)
    sub_ax.outline_patch.set_path_effects([effect])

    # Add the land, coastlines and the extent of the Solomon Islands.
    sub_ax.add_feature(cartopy.feature.LAND)
    sub_ax.coastlines()
    extent_box = sgeom.box(extent[0], extent[2], extent[1], extent[3])
    sub_ax.add_geometries([extent_box], ccrs.PlateCarree(), color='none',
                          edgecolor='blue', linewidth=2)

    plt.show()


if __name__ == '__main__':
    main()

########NEW FILE########
__FILENAME__ = eyja_volcano
# -*- coding: utf-8 -*-
"""
Map tile acquisition
--------------------

Demonstrates cartopy's ability to draw map tiles which are downloaded on
demand from the MapQuest tile server. Internally these tiles are then combined
into a single image and displayed in the cartopy GeoAxes.

"""
__tags__ = ["Scalar data"]
import matplotlib.pyplot as plt
from matplotlib.transforms import offset_copy

import cartopy.crs as ccrs
import cartopy.io.img_tiles as cimgt


def main():
    # Create a MapQuest open aerial instance.
    map_quest_aerial = cimgt.MapQuestOpenAerial()

    # Create a GeoAxes in the tile's projection.
    ax = plt.axes(projection=map_quest_aerial.crs)

    # Limit the extent of the map to a small longitude/latitude range.
    ax.set_extent([-22, -15, 63, 65])

    # Add the MapQuest data at zoom level 8.
    ax.add_image(map_quest_aerial, 8)

    # Add a marker for the Eyjafjallajökull volcano.
    plt.plot(-19.613333, 63.62, marker='o', color='yellow', markersize=12,
             alpha=0.7, transform=ccrs.Geodetic())

    # Use the cartopy interface to create a matplotlib transform object
    # for the Geodetic coordinate system. We will use this along with
    # matplotlib's offset_copy function to define a coordinate system which
    # translates the text by 25 pixels to the left.
    geodetic_transform = ccrs.Geodetic()._as_mpl_transform(ax)
    text_transform = offset_copy(geodetic_transform, units='dots', x=-25)

    # Add text 25 pixels to the left of the volcano.
    plt.text(-19.613333, 63.62, u'Eyjafjallajökull',
             verticalalignment='center', horizontalalignment='right',
             transform=text_transform,
             bbox=dict(facecolor='wheat', alpha=0.5, boxstyle='round'))
    plt.show()


if __name__ == '__main__':
    main()

########NEW FILE########
__FILENAME__ = favicon
__tags__ = ['Miscellanea']
import cartopy.crs as ccrs
import matplotlib.pyplot as plt
import matplotlib.textpath
import matplotlib.patches
from matplotlib.font_manager import FontProperties
import numpy as np


def main():
    plt.figure(figsize=[8, 8])
    ax = plt.axes(projection=ccrs.SouthPolarStereo())

    ax.coastlines()
    ax.gridlines()

    im = ax.stock_img()

    def on_draw(event=None):
        """
        Hooks into matplotlib's event mechanism to define the clip path of the
        background image.

        """
        # Clip the image to the current background boundary.
        im.set_clip_path(ax.background_patch.get_path(),
                         transform=ax.background_patch.get_transform())

    # Register the on_draw method and call it once now.
    plt.gcf().canvas.mpl_connect('draw_event', on_draw)
    on_draw()

    # Generate a matplotlib path representing the character "C".
    fp = FontProperties(family='Arial', weight='bold')
    logo_path = matplotlib.textpath.TextPath((-4.5e7, -3.7e7),
                                             'C', size=1, prop=fp)

    # Scale the letter up to an appropriate X and Y scale.
    logo_path._vertices *= np.array([123500000, 103250000])

    # Add the path as a patch, drawing black outlines around the text.
    patch = matplotlib.patches.PathPatch(logo_path, facecolor='white',
                                         edgecolor='black', linewidth=10,
                                         transform=ccrs.SouthPolarStereo())
    ax.add_patch(patch)
    plt.show()


if __name__ == '__main__':
    main()

########NEW FILE########
__FILENAME__ = features
__tags__ = ['Lines and polygons']
import cartopy
import matplotlib.pyplot as plt


def main():

    ax = plt.axes(projection=cartopy.crs.PlateCarree())

    ax.add_feature(cartopy.feature.LAND)
    ax.add_feature(cartopy.feature.OCEAN)
    ax.add_feature(cartopy.feature.COASTLINE)
    ax.add_feature(cartopy.feature.BORDERS, linestyle=':')
    ax.add_feature(cartopy.feature.LAKES, alpha=0.5)
    ax.add_feature(cartopy.feature.RIVERS)

    ax.set_extent([-20, 60, -40, 40])

    plt.show()


if __name__ == '__main__':
    main()

########NEW FILE########
__FILENAME__ = feature_creation
__tags__ = ['Lines and polygons']
import matplotlib.pyplot as plt

import cartopy.crs as ccrs
import cartopy.feature as cfeature


def main():
    ax = plt.axes(projection=ccrs.PlateCarree())
    ax.set_extent([80, 170, -45, 30])

    # Put a background image on for nice sea rendering.
    ax.stock_img()

    # Create a feature for States/Admin 1 regions at 1:50m from Natural Earth
    states_provinces = cfeature.NaturalEarthFeature(
        category='cultural',
        name='admin_1_states_provinces_lines',
        scale='50m',
        facecolor='none')

    ax.add_feature(cfeature.LAND)
    ax.add_feature(cfeature.COASTLINE)
    ax.add_feature(states_provinces, edgecolor='gray')

    plt.show()


if __name__ == '__main__':
    main()

########NEW FILE########
__FILENAME__ = geostationary
"""
Reprojecting images from a Geostationary projection
---------------------------------------------------

This example demonstrates Cartopy's ability to project images into the desired
projection on-the-fly. The image itself is retrieved from a URL and is loaded
directly into memory without storing it intermediately into a file. It
represents pre-processed data from Moderate-Resolution Imaging
Spectroradiometer (MODIS) which has been put into an image in the data's
native Geostationary coordinate system - it is then projected by cartopy
into a global Miller map.

"""
__tags__ = ["Scalar data"]
import urllib2
from io import BytesIO

import cartopy.crs as ccrs
import matplotlib.pyplot as plt


def geos_image():
    """
    Return a specific MODIS image by retrieving it from a github gist URL.

    Returns
    -------
    img : numpy array
        The pixels of the image in a numpy array.
    img_proj : cartopy CRS
        The rectangular coordinate system of the image.
    img_extent : tuple of floats
        The extent of the image ``(x0, y0, x1, y1)`` referenced in
        the ``img_proj`` coordinate system.
    origin : str
        The origin of the image to be passed through to matplotlib's imshow.

    """
    url = ('https://gist.github.com/pelson/5871263/raw/'
           'EIDA50_201211061300_clip2.png')
    img_handle = BytesIO(urllib2.urlopen(url).read())
    img = plt.imread(img_handle)
    img_proj = ccrs.Geostationary(satellite_height=35786000)
    img_extent = (-5500000, 5500000, -5500000, 5500000)
    return img, img_proj, img_extent, 'upper'


def main():
    ax = plt.axes(projection=ccrs.Miller())
    ax.coastlines()
    ax.set_global()
    img, crs, extent, origin = geos_image()
    plt.imshow(img, transform=crs, extent=extent, origin=origin, cmap='gray')
    plt.show()


if __name__ == '__main__':
    main()

########NEW FILE########
__FILENAME__ = global_map
__tags__ = ['Lines and polygons']
import matplotlib.pyplot as plt

import cartopy.crs as ccrs


def main():
    ax = plt.axes(projection=ccrs.Robinson())

    # make the map global rather than have it zoom in to
    # the extents of any plotted data
    ax.set_global()

    ax.stock_img()
    ax.coastlines()

    plt.plot(-0.08, 51.53, 'o', transform=ccrs.PlateCarree())
    plt.plot([-0.08, 132], [51.53, 43.17], transform=ccrs.PlateCarree())
    plt.plot([-0.08, 132], [51.53, 43.17], transform=ccrs.Geodetic())

    plt.show()


if __name__ == '__main__':
    main()

########NEW FILE########
__FILENAME__ = hurricane_katrina
__tags__ = ['Lines and polygons']
import matplotlib.patches as mpatches
import matplotlib.pyplot as plt
import shapely.geometry as sgeom

import cartopy.crs as ccrs
import cartopy.io.shapereader as shpreader


def sample_data():
    """
    Returns a list of latitudes and a list of longitudes (lons, lats)
    for Hurricane Katrina (2005).

    The data was originally sourced from the HURDAT2 dataset from AOML/NOAA:
    http://www.aoml.noaa.gov/hrd/hurdat/newhurdat-all.html on 14th Dec 2012.

    """
    lons = [-75.1, -75.7, -76.2, -76.5, -76.9, -77.7, -78.4, -79.0,
            -79.6, -80.1, -80.3, -81.3, -82.0, -82.6, -83.3, -84.0,
            -84.7, -85.3, -85.9, -86.7, -87.7, -88.6, -89.2, -89.6,
            -89.6, -89.6, -89.6, -89.6, -89.1, -88.6, -88.0, -87.0,
            -85.3, -82.9]

    lats = [23.1, 23.4, 23.8, 24.5, 25.4, 26.0, 26.1, 26.2, 26.2, 26.0,
            25.9, 25.4, 25.1, 24.9, 24.6, 24.4, 24.4, 24.5, 24.8, 25.2,
            25.7, 26.3, 27.2, 28.2, 29.3, 29.5, 30.2, 31.1, 32.6, 34.1,
            35.6, 37.0, 38.6, 40.1]

    return lons, lats


def main():
    ax = plt.axes([0, 0, 1, 1],
                  projection=ccrs.LambertConformal())

    ax.set_extent([-125, -66.5, 20, 50], ccrs.Geodetic())

    shapename = 'admin_1_states_provinces_lakes_shp'
    states_shp = shpreader.natural_earth(resolution='110m',
                                         category='cultural', name=shapename)

    lons, lats = sample_data()

    # to get the effect of having just the states without a map "background"
    # turn off the outline and background patches
    ax.background_patch.set_visible(False)
    ax.outline_patch.set_visible(False)

    plt.title('US States which intersect the track '
              'of Hurricane Katrina (2005)')

    # turn the lons and lats into a shapely LineString
    track = sgeom.LineString(zip(lons, lats))

    # buffer the linestring by two degrees (note: this is a non-physical
    # distance)
    track_buffer = track.buffer(2)

    for state in shpreader.Reader(states_shp).geometries():
        # pick a default color for the land with a black outline,
        # this will change if the storm intersects with our track
        facecolor = [0.9375, 0.9375, 0.859375]
        edgecolor = 'black'

        if state.intersects(track):
            facecolor = 'red'
        elif state.intersects(track_buffer):
            facecolor = '#FF7E00'

        ax.add_geometries([state], ccrs.PlateCarree(),
                          facecolor=facecolor, edgecolor=edgecolor)

    ax.add_geometries([track_buffer], ccrs.PlateCarree(),
                      facecolor='#C8A2C8', alpha=0.5)
    ax.add_geometries([track], ccrs.PlateCarree(),
                      facecolor='none')

    # make two proxy artists to add to a legend
    direct_hit = mpatches.Rectangle((0, 0), 1, 1, facecolor="red")
    within_2_deg = mpatches.Rectangle((0, 0), 1, 1, facecolor="#FF7E00")
    labels = ['State directly intersects\nwith track',
              'State is within \n2 degrees of track']
    plt.legend([direct_hit, within_2_deg], labels,
               loc='lower left', bbox_to_anchor=(0.025, -0.1), fancybox=True)

    plt.show()


if __name__ == '__main__':
    main()

########NEW FILE########
__FILENAME__ = logo
__tags__ = ['Miscellanea']
import cartopy.crs as ccrs
import matplotlib.pyplot as plt
import matplotlib.textpath
import matplotlib.patches
from matplotlib.font_manager import FontProperties
import numpy as np


def main():
    plt.figure(figsize=[12, 6])
    ax = plt.axes(projection=ccrs.Robinson())

    ax.coastlines()
    ax.gridlines()

    # generate a matplotlib path representing the word "cartopy"
    fp = FontProperties(family='Arial', weight='bold')
    logo_path = matplotlib.textpath.TextPath((-175, -35), 'cartopy',
                                             size=1, prop=fp)
    # scale the letters up to sensible longitude and latitude sizes
    logo_path._vertices *= np.array([95, 160])

    # add a background image
    im = ax.stock_img()
    # clip the image according to the logo_path. mpl v1.2.0 does not support
    # the transform API that cartopy makes use of, so we have to convert the
    # projection into a transform manually
    plate_carree_transform = ccrs.PlateCarree()._as_mpl_transform(ax)
    im.set_clip_path(logo_path, transform=plate_carree_transform)

    # add the path as a patch, drawing black outlines around the text
    patch = matplotlib.patches.PathPatch(logo_path,
                                         facecolor='none', edgecolor='black',
                                         transform=ccrs.PlateCarree())
    ax.add_patch(patch)

    plt.show()


if __name__ == '__main__':
    main()

########NEW FILE########
__FILENAME__ = regridding_arrows
"""
Regridding vectors with quiver
------------------------------

This example demonstrates the regridding functionality in quiver (there exists
equivalent functionality in :meth:`cartopy.mpl.geoaxes.GeoAxes.barbs`).

Regridding can be an effective way of visualising a vector field, particularly
if the data is dense or warped.
"""
__tags__ = ['Vector data']
import matplotlib.pyplot as plt
import numpy as np

import cartopy.crs as ccrs


def sample_data(shape=(20, 30)):
    """
    Returns ``(x, y, u, v, crs)`` of some vector data
    computed mathematically. The returned CRS will be a North Polar
    Stereographic projection, meaning that the vectors will be unevenly
    spaced in a PlateCarree projection.

    """
    crs = ccrs.NorthPolarStereo()
    scale = 1e7
    x = np.linspace(-scale, scale, shape[1])
    y = np.linspace(-scale, scale, shape[0])

    x2d, y2d = np.meshgrid(x, y)
    u = 10 * np.cos(2 * x2d / scale + 3 * y2d / scale)
    v = 20 * np.cos(6 * x2d / scale)

    return x, y, u, v, crs


def main():
    plt.figure(figsize=(8, 10))

    x, y, u, v, vector_crs = sample_data(shape=(50, 50))
    ax1 = plt.subplot(2, 1, 1, projection=ccrs.PlateCarree())
    ax1.coastlines('50m')
    ax1.set_extent([-45, 55, 20, 80], ccrs.PlateCarree())
    ax1.quiver(x, y, u, v, transform=vector_crs)

    ax2 = plt.subplot(2, 1, 2, projection=ccrs.PlateCarree())
    plt.title('The same vector field regridded')
    ax2.coastlines('50m')
    ax2.set_extent([-45, 55, 20, 80], ccrs.PlateCarree())
    ax2.quiver(x, y, u, v, transform=vector_crs, regrid_shape=20)

    plt.show()


if __name__ == '__main__':
    main()

########NEW FILE########
__FILENAME__ = rotated_pole
"""
Rotated pole boxes
------------------

This example demonstrates the way a box is warped when it is defined
in a rotated pole coordinate system.

Try changing the ``box_top`` to ``44``, ``46`` and ``75`` to see the effect
that including the pole in the polygon has.

"""

__tags__ = ['Lines and polygons']
import matplotlib.pyplot as plt

import cartopy.crs as ccrs


def main():
    rotated_pole = ccrs.RotatedPole(pole_latitude=45, pole_longitude=180)

    box_top = 45
    x, y = [-44, -44, 45, 45, -44], [-45, box_top, box_top, -45, -45]

    ax = plt.subplot(211, projection=rotated_pole)
    ax.stock_img()
    ax.coastlines()
    ax.plot(x, y, marker='o', transform=rotated_pole)
    ax.fill(x, y, color='coral', transform=rotated_pole, alpha=0.4)
    ax.gridlines()

    ax = plt.subplot(212, projection=ccrs.PlateCarree())
    ax.stock_img()
    ax.coastlines()
    ax.plot(x, y, marker='o', transform=rotated_pole)
    ax.fill(x, y, transform=rotated_pole, color='coral', alpha=0.4)
    ax.gridlines()

    plt.show()


if __name__ == '__main__':
    main()

########NEW FILE########
__FILENAME__ = srtm_shading
__tags__ = ['Scalar data']
"""
This example illustrates the automatic download of
STRM data, gap filling (using gdal) and adding shading
to create a so-called "Shaded Relief SRTM"

Contributed by: Thomas Lecocq (http://geophysique.be)
"""

import cartopy.crs as ccrs
from cartopy.io import srtm
import matplotlib.pyplot as plt


def main():
    ax = plt.axes(projection=ccrs.PlateCarree())

    # Get the 1x1 degree SRTM tile for 12E, 47N
    elev, crs, extent = srtm.srtm_composite(12, 47, 1, 1)

    # Fill the gaps present in the elevation data
    elev_filled = srtm.fill_gaps(elev, 15)

    # Add shading simulating the Sun at 10am (South-East)
    # and with a low angle (15 degrees above horizon)
    shaded = srtm.add_shading(elev_filled, 135.0, 15.0)

    # The plot the result :
    plt.imshow(shaded, extent=extent, transform=crs,
               cmap='Greys', origin='lower')

    plt.title("SRTM Shaded Relief Map")

    gl = ax.gridlines(draw_labels=True,)
    gl.xlabels_top = False
    gl.ylabels_left = False

    plt.show()


if __name__ == '__main__':
    main()

########NEW FILE########
__FILENAME__ = streamplot
__tags__ = ['Vector data']
import matplotlib.pyplot as plt

import cartopy.crs as ccrs
from cartopy.examples.arrows import sample_data


def main():
    ax = plt.axes(projection=ccrs.PlateCarree())
    ax.set_extent([-90, 75, 10, 60])
    ax.coastlines()

    x, y, u, v, vector_crs = sample_data(shape=(80, 100))
    magnitude = (u ** 2 + v ** 2) ** 0.5
    ax.streamplot(x, y, u, v, transform=vector_crs,
                  linewidth=2, density=2, color=magnitude)
    plt.show()


if __name__ == '__main__':
    main()

########NEW FILE########
__FILENAME__ = waves
__tags__ = ['Scalar data']
import matplotlib.pyplot as plt
import numpy as np

import cartopy.crs as ccrs


def sample_data(shape=(73, 145)):
    """Returns ``lons``, ``lats`` and ``data`` of some fake data."""
    nlats, nlons = shape
    lats = np.linspace(-np.pi / 2, np.pi / 2, nlats)
    lons = np.linspace(0, 2 * np.pi, nlons)
    lons, lats = np.meshgrid(lons, lats)
    wave = 0.75 * (np.sin(2 * lats) ** 8) * np.cos(4 * lons)
    mean = 0.5 * np.cos(2 * lats) * ((np.sin(2 * lats)) ** 2 + 2)

    lats = np.rad2deg(lats)
    lons = np.rad2deg(lons)
    data = wave + mean

    return lons, lats, data


def main():
    ax = plt.axes(projection=ccrs.Mollweide())

    lons, lats, data = sample_data()

    ax.contourf(lons, lats, data,
                transform=ccrs.PlateCarree(),
                cmap='spectral')
    ax.coastlines()
    ax.set_global()
    plt.show()


if __name__ == '__main__':
    main()

########NEW FILE########
__FILENAME__ = feature
# (C) British Crown Copyright 2011 - 2012, Met Office
#
# This file is part of cartopy.
#
# cartopy is free software: you can redistribute it and/or modify it under
# the terms of the GNU Lesser General Public License as published by the
# Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# cartopy is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Lesser General Public License for more details.
#
# You should have received a copy of the GNU Lesser General Public License
# along with cartopy.  If not, see <http://www.gnu.org/licenses/>.
"""
This module defines :class:`Feature` instances, for use with
ax.add_feature().

"""
from abc import ABCMeta, abstractmethod
import os.path

import numpy as np
import shapely.geometry

import cartopy.io.shapereader as shapereader
import cartopy.crs


COLORS = {'land': np.array((240, 240, 220)) / 256.,
          'land_alt1': np.array((220, 220, 220)) / 256.,
          'water': np.array((152, 183, 226)) / 256.}
"""
A dictionary of colors useful for drawing Features.

The named keys in this dictionary represent the "type" of
feature being plotted.

"""


_NATURAL_EARTH_GEOM_CACHE = {}
"""
Caches a mapping between (name, category, scale) and a tuple of the
resulting geometries.

Provides a significant performance benefit (when combined with object id
caching in GeoAxes.add_geometries) when producing multiple maps of the
same projection.

"""


class Feature(object):
    """
    Represents a collection of points, lines and polygons with convenience
    methods for common drawing and filtering operations.

    Args:

        * crs - the coordinate reference system of this Feature

    Kwargs:
        Keyword arguments to be used when drawing this feature.

    .. seealso::

        To add features to the current matplotlib axes, see
        :func:`GeoAxes <cartopy.mpl.geoaxes.GeoAxes.add_feature>`.

    """
    __metaclass__ = ABCMeta

    def __init__(self, crs, **kwargs):
        self._crs = crs
        self._kwargs = dict(kwargs)

    @property
    def crs(self):
        """The cartopy CRS for the geometries in this feature."""
        return self._crs

    @property
    def kwargs(self):
        """
        The read-only dictionary of keyword arguments that are used when
        creating the matplotlib artists for this feature.

        """
        return dict(self._kwargs)

    @abstractmethod
    def geometries(self):
        """
        Returns an iterator of (shapely) geometries for this feature.

        """
        pass

    def intersecting_geometries(self, extent):
        """
        Returns an iterator of shapely geometries that intersect with
        the given extent. The extent is assumed to be in the CRS of
        the feature. If extent is None, the method returns all
        geometries for this dataset.

        """
        if extent is not None:
            extent_geom = shapely.geometry.box(extent[0], extent[2],
                                               extent[1], extent[3])
            return (geom for geom in self.geometries() if
                    extent_geom.intersects(geom))
        else:
            return self.geometries()


class ShapelyFeature(Feature):
    """
    A class capable of drawing a collection of
    shapely geometries.

    """
    def __init__(self, geometries, crs, **kwargs):
        """
        Args:

        * geometries:
            A collection of shapely geometries.
        * crs:
            The cartopy CRS in which the provided geometries are defined.

        Kwargs:
            Keyword arguments to be used when drawing this feature.

        """
        super(ShapelyFeature, self).__init__(crs, **kwargs)
        self._geoms = tuple(geometries)

    def geometries(self):
        return iter(self._geoms)


class NaturalEarthFeature(Feature):
    """
    A simple interface to Natural Earth shapefiles.

    See http://www.naturalearthdata.com/

    """
    def __init__(self, category, name, scale, **kwargs):
        """
        Args:

        * category:
            The category of the dataset, i.e. either 'cultural' or 'physical'.
        * name:
            The name of the dataset, e.g. 'admin_0_boundary_lines_land'.
        * scale:
            The dataset scale, i.e. one of '10m', '50m', or '110m'.
            Corresponding to 1:10,000,000, 1:50,000,000, and 1:110,000,000
            respectively.

        Kwargs:
            Keyword arguments to be used when drawing this feature.

        """
        super(NaturalEarthFeature, self).__init__(cartopy.crs.PlateCarree(),
                                                  **kwargs)
        self.category = category
        self.name = name
        self.scale = scale

    def geometries(self):
        key = (self.name, self.category, self.scale)
        if key not in _NATURAL_EARTH_GEOM_CACHE:
            path = shapereader.natural_earth(resolution=self.scale,
                                             category=self.category,
                                             name=self.name)
            geometries = tuple(shapereader.Reader(path).geometries())
            _NATURAL_EARTH_GEOM_CACHE[key] = geometries
        else:
            geometries = _NATURAL_EARTH_GEOM_CACHE[key]

        return iter(geometries)


class GSHHSFeature(Feature):
    """
    An interface to the GSHHS dataset.

    See http://www.ngdc.noaa.gov/mgg/shorelines/gshhs.html

    Args:

    * scale:
        The dataset scale. One of 'auto', 'coarse', 'low', 'intermediate',
        'high, or 'full' (default is 'auto').
    * levels:
        A list of integers 1-4 corresponding to the desired GSHHS feature
        levels to draw (default is [1] which corresponds to coastlines).

    Kwargs:
        Keyword arguments to be used when drawing the feature. Defaults
        are edgecolor='black' and facecolor='none'.

    """

    _geometries_cache = {}
    """
    A mapping from scale and level to GSHHS shapely geometry::

        {(scale, level): geom}

    This provides a perfomance boost when plotting in interactive mode or
    instantiating multiple GSHHS artists, by reducing repeated file IO.

    """
    def __init__(self, scale='auto', levels=None, **kwargs):
        super(GSHHSFeature, self).__init__(cartopy.crs.PlateCarree(), **kwargs)

        if scale not in ('auto', 'a', 'coarse', 'c', 'low', 'l',
                         'intermediate', 'i', 'high', 'h', 'full', 'f'):
            raise ValueError("Unknown GSHHS scale '{}'.".format(scale))
        self._scale = scale

        if levels is None:
            levels = [1]
        self._levels = set(levels)
        unknown_levels = self._levels.difference([1, 2, 3, 4])
        if unknown_levels:
            raise ValueError("Unknown GSHHS levels "
                             "'{}'.".format(unknown_levels))

        # Default kwargs
        self._kwargs.setdefault('edgecolor', 'black')
        self._kwargs.setdefault('facecolor', 'none')

    def _scale_from_extent(self, extent):
        """
        Returns the appropriate scale (e.g. 'i') for the given extent
        expressed in PlateCarree CRS.

        """
        # Default to coarse scale
        scale = 'c'

        if extent is not None:
            # Upper limit on extent in degrees.
            scale_limits = (('c', 20.0),
                            ('l', 10.0),
                            ('i', 2.0),
                            ('h', 0.5),
                            ('f', 0.1))

            width = abs(extent[1] - extent[0])
            height = abs(extent[3] - extent[2])
            min_extent = min(width, height)
            if min_extent != 0:
                for scale, limit in scale_limits:
                    if min_extent > limit:
                        break

        return scale

    def geometries(self):
        return self.intersecting_geometries(extent=None)

    def intersecting_geometries(self, extent):
        if self._scale == 'auto':
            scale = self._scale_from_extent(extent)
        else:
            scale = self._scale[0]

        if extent is not None:
            extent_geom = shapely.geometry.box(extent[0], extent[2],
                                               extent[1], extent[3])
        for level in self._levels:
            geoms = GSHHSFeature._geometries_cache.get((scale, level))
            if geoms is None:
                # Load GSHHS geometries from appropriate shape file.
                # TODO selective load based on bbox of each geom in file.
                path = shapereader.gshhs(scale, level)
                geoms = tuple(shapereader.Reader(path).geometries())
                GSHHSFeature._geometries_cache[(scale, level)] = geoms
            for geom in geoms:
                if extent is None or extent_geom.intersects(geom):
                    yield geom


BORDERS = NaturalEarthFeature('cultural', 'admin_0_boundary_lines_land',
                              '110m', edgecolor='black', facecolor='none')
"""Small scale (1:110m) country boundaries."""


COASTLINE = NaturalEarthFeature('physical', 'coastline', '110m',
                                edgecolor='black', facecolor='none')
"""Small scale (1:110m) coastline, including major islands."""


LAKES = NaturalEarthFeature('physical', 'lakes', '110m',
                            edgecolor='face',
                            facecolor=COLORS['water'])
"""Small scale (1:110m) natural and artificial lakes."""


LAND = NaturalEarthFeature('physical', 'land', '110m',
                           edgecolor='face',
                           facecolor=COLORS['land'])
"""Small scale (1:110m) land polygons, including major islands."""


OCEAN = NaturalEarthFeature('physical', 'ocean', '110m',
                            edgecolor='face',
                            facecolor=COLORS['water'])
"""Small scale (1:110m) ocean polygons."""


RIVERS = NaturalEarthFeature('physical', 'rivers_lake_centerlines', '110m',
                             edgecolor=COLORS['water'],
                             facecolor='none')
"""Small scale (1:110m) single-line drainages, including lake centerlines."""

########NEW FILE########
__FILENAME__ = img_transform
# (C) British Crown Copyright 2011 - 2014, Met Office
#
# This file is part of cartopy.
#
# cartopy is free software: you can redistribute it and/or modify it under
# the terms of the GNU Lesser General Public License as published by the
# Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# cartopy is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Lesser General Public License for more details.
#
# You should have received a copy of the GNU Lesser General Public License
# along with cartopy.  If not, see <http://www.gnu.org/licenses/>.
"""
This module contains generic functionality to support Cartopy image
transformations.

"""

import numpy as np
import scipy.spatial

import cartopy.crs as ccrs


def mesh_projection(projection, nx, ny,
                    x_extents=[None, None],
                    y_extents=[None, None]):
    """
    Returns sample points in the given projection which span the entire
    projection range evenly.

    The range of the x-direction and y-direction sample points will be
    within the bounds of the projection or specified extents.

    Args:

    * projection:
        A :class:`~cartopy.crs.Projection` instance.

    * nx:
        The number of sample points in the projection x-direction.

    * ny:
        The number of sample points in the projection y-direction.

    Kwargs:

    * x_extents:
        The (lower, upper) x-direction extent of the projection.
        Defaults to the :attribute:`~cartopy.crs.Projection.x_limits`.

    * y_extents:
        The (lower, upper) y-direction extent of the projection.
        Defaults to the :attribute:`~cartopy.crs.Projection.y_limits`.

    Returns:
        A tuple of three items. The x-direction sample points
        :class:`numpy.ndarray` of shape (nx, ny), y-direction
        sample points :class:`numpy.ndarray` of shape (nx, ny),
        and the extent of the projection range as
        ``(x-lower, x-upper, y-lower, y-upper)``.

    """

    # Establish the x-direction and y-direction extents.
    x_lower = x_extents[0] or projection.x_limits[0]
    x_upper = x_extents[1] or projection.x_limits[1]
    y_lower = y_extents[0] or projection.y_limits[0]
    y_upper = y_extents[1] or projection.y_limits[1]

    # Calculate evenly spaced sample points spanning the
    # extent - excluding endpoint.
    x, xstep = np.linspace(x_lower, x_upper, nx, retstep=True,
                           endpoint=False)
    y, ystep = np.linspace(y_lower, y_upper, ny, retstep=True,
                           endpoint=False)

    # Offset the sample points to be within the extent range.
    x += 0.5 * xstep
    y += 0.5 * ystep

    # Generate the x-direction and y-direction meshgrids.
    x, y = np.meshgrid(x, y)
    return x, y, [x_lower, x_upper, y_lower, y_upper]


def warp_img(fname, target_proj, source_proj=None, target_res=(400, 200)):
    """
    Regrid the image file from the source projection to the target projection.

    Args:

    * fname:
        Image filename to be loaded and warped.

    * target_proj:
        The target :class:`~cartopy.crs.Projection` instance for the image.

    Kwargs:

    * source_proj:
        The source :class:`~cartopy.crs.Projection` instance of the image.
        Defaults to a :class:`~cartopy.crs.PlateCarree` projection.

    * target_res:
        The (nx, ny) resolution of the target projection. Where nx defaults to
        400 sample points, and ny defaults to 200 sample points.

    """

    if source_proj is None:
        source_proj = ccrs.PlateCarree()

    raise NotImplementedError('Not yet implemented.')


def warp_array(array, target_proj, source_proj=None, target_res=(400, 200),
               source_extent=None, target_extent=None,
               mask_extrapolated=False):
    """
    Regrid the data array from the source projection to the target projection.

    Also see, :function:`~cartopy.img_transform.regrid`.

    Args:

    * array:
        The :class:`numpy.ndarray` of data to be regridded to the target
        projection.

    * target_proj:
        The target :class:`~cartopy.crs.Projection` instance for the data.

    Kwargs:

    * source_proj:
        The source :class:`~cartopy.crs.Projection' instance of the data.
        Defaults to a :class:`~cartopy.crs.PlateCarree` projection.

    * target_res:
        The (nx, ny) resolution of the target projection. Where nx defaults to
        400 sample points, and ny defaults to 200 sample points.

    * source_extent:
        The (x-lower, x-upper, y-lower, y-upper) extent in native
        source projection coordinates.

    * target_extent:
        The (x-lower, x-upper, y-lower, y-upper) extent in native
        target projection coordinates.

    Kwargs:

    * mask_extrapolated:
        Assume that the source coordinate is rectilinear and so mask the
        resulting target grid values which lie outside the source grid
        domain.

    Returns:
        A tuple of the regridded :class:`numpy.ndarray` in the target
        projection and the (x-lower, x-upper, y-lower, y-upper) target
        projection extent.

    """

    # source_extent is in source coordinates.
    if source_extent is None:
        source_extent = [None] * 4
    # target_extent is in target coordinates.
    if target_extent is None:
        target_extent = [None] * 4

    source_x_extents = source_extent[:2]
    source_y_extents = source_extent[2:]

    target_x_extents = target_extent[:2]
    target_y_extents = target_extent[2:]

    if source_proj is None:
        source_proj = ccrs.PlateCarree()

    ny, nx = array.shape[:2]
    source_native_xy = mesh_projection(source_proj, nx, ny,
                                       x_extents=source_x_extents,
                                       y_extents=source_y_extents)

    # XXX Take into account the extents of the original to determine
    # target_extents?
    target_native_x, target_native_y, extent = mesh_projection(
        target_proj, target_res[0], target_res[1],
        x_extents=target_x_extents, y_extents=target_y_extents)

    array = regrid(array, source_native_xy[0], source_native_xy[1],
                   source_proj, target_proj,
                   target_native_x, target_native_y,
                   mask_extrapolated)
    return array, extent


def _determine_bounds(x_coords, y_coords, source_cs):
    # Returns bounds corresponding to one or two rectangles depending on
    # transformation between ranges.
    bounds = dict(x=[])
    half_px = abs(np.diff(x_coords[:2])).max() / 2.

    if (((hasattr(source_cs, 'is_geodetic') and
            source_cs.is_geodetic()) or
            isinstance(source_cs, ccrs.PlateCarree)) and x_coords.max() > 180):
        if x_coords.min() < 180:
            bounds['x'].append([x_coords.min() - half_px, 180])
            bounds['x'].append([-180, x_coords.max() - 360 + half_px])
        else:
            bounds['x'].append([x_coords.min() - 180 - half_px,
                                x_coords.max() - 180 + half_px])
    else:
        bounds['x'].append([x_coords.min() - half_px,
                            x_coords.max() + half_px])

    bounds['y'] = [y_coords.min(), y_coords.max()]
    return bounds


def regrid(array, source_x_coords, source_y_coords, source_cs, target_proj,
           target_x_points, target_y_points, mask_extrapolated=False):
    """
    Regrid the data array from the source projection to the target projection.

    Args:

    * array:
        The :class:`numpy.ndarray` of data to be regridded to the
        target projection.

    * source_x_coords:
        A 2-dimensional source projection :class:`numpy.ndarray` of
        x-direction sample points.

    * source_y_coords:
        A 2-dimensional source projection :class:`numpy.ndarray` of
        y-direction sample points.

    * source_cs:
        The source :class:`~cartopy.crs.Projection` instance.

    * target_cs:
        The target :class:`~cartopy.crs.Projection` instance.

    * target_x_points:
        A 2-dimensional target projection :class:`numpy.ndarray` of
        x-direction sample points.

    * target_y_points:
        A 2-dimensional target projection :class:`numpy.ndarray` of
        y-direction sample points.

    Kwargs:

    * mask_extrapolated:
        Assume that the source coordinate is rectilinear and so mask the
        resulting target grid values which lie outside the source grid domain.

    Returns:
        The data array regridded in the target projection.

    """

    # n.b. source_cs is actually a projection (the coord system of the
    # source coordinates), but not necessarily the native projection of
    # the source array (i.e. you can provide a warped image with lat lon
    # coordinates).

    #XXX NB. target_x and target_y must currently be rectangular (i.e.
    # be a 2d np array)
    geo_cent = source_cs.as_geocentric()
    xyz = geo_cent.transform_points(source_cs,
                                    source_x_coords.flatten(),
                                    source_y_coords.flatten())
    target_xyz = geo_cent.transform_points(target_proj,
                                           target_x_points.flatten(),
                                           target_y_points.flatten())

    kdtree = scipy.spatial.cKDTree(xyz)
    distances, indices = kdtree.query(target_xyz, k=1)
    mask = np.isinf(distances)

    desired_ny, desired_nx = target_x_points.shape
    if array.ndim == 1:
        if np.any(mask):
            array_1d = np.ma.array(array[indices], mask=mask)
        else:
            array_1d = array[indices]
        new_array = array_1d.reshape(desired_ny, desired_nx)
    elif array.ndim == 2:
        # Handle missing neighbours using a masked array
        if np.any(mask):
            indices = np.where(np.logical_not(mask), indices, 0)
            array_1d = np.ma.array(array.reshape(-1)[indices], mask=mask)
        else:
            array_1d = array.reshape(-1)[indices]

        new_array = array_1d.reshape(desired_ny, desired_nx)
    elif array.ndim == 3:
        # Handle missing neighbours using a masked array
        if np.any(mask):
            indices = np.where(np.logical_not(mask), indices, 0)
            array_2d = array.reshape(-1, array.shape[-1])[indices]
            mask, array_2d = np.broadcast_arrays(
                mask.reshape(-1, 1), array_2d)
            array_2d = np.ma.array(array_2d, mask=mask)
        else:
            array_2d = array.reshape(-1, array.shape[-1])[indices]

        new_array = array_2d.reshape(desired_ny, desired_nx, array.shape[-1])
    else:
        raise ValueError(
            'Expected array.ndim to be 1, 2 or 3, got {}'.format(array.ndim))

    # Do double transform to clip points that do not map back and forth
    # to the same point to within a fixed fractional offset.
    # XXX THIS ONLY NEEDS TO BE DONE FOR (PSEUDO-)CYLINDRICAL PROJECTIONS
    # (OR ANY OTHERS WHICH HAVE THE CONCEPT OF WRAPPING)
    source_desired_xyz = source_cs.transform_points(target_proj,
                                                    target_x_points.flatten(),
                                                    target_y_points.flatten())
    back_to_target_xyz = target_proj.transform_points(source_cs,
                                                      source_desired_xyz[:, 0],
                                                      source_desired_xyz[:, 1])
    back_to_target_x = back_to_target_xyz[:, 0].reshape(desired_ny,
                                                        desired_nx)
    back_to_target_y = back_to_target_xyz[:, 1].reshape(desired_ny,
                                                        desired_nx)
    FRACTIONAL_OFFSET_THRESHOLD = 0.1  # data has moved by 10% of the map

    x_extent = np.abs(target_proj.x_limits[1] - target_proj.x_limits[0])
    y_extent = np.abs(target_proj.y_limits[1] - target_proj.y_limits[0])

    non_self_inverse_points = (np.abs(target_x_points - back_to_target_x) /
                               x_extent) > FRACTIONAL_OFFSET_THRESHOLD
    if np.any(non_self_inverse_points):
        if np.ma.isMaskedArray(new_array):
            new_array[non_self_inverse_points] = np.ma.masked
        else:
            new_array = np.ma.array(new_array, mask=False)
            if new_array.ndim == 3:
                for i in range(new_array.shape[2]):
                    new_array[non_self_inverse_points, i] = np.ma.masked
            else:
                new_array[non_self_inverse_points] = np.ma.masked
    non_self_inverse_points = (np.abs(target_y_points - back_to_target_y) /
                               y_extent) > FRACTIONAL_OFFSET_THRESHOLD
    if np.any(non_self_inverse_points):
        if np.ma.isMaskedArray(new_array):
            new_array[non_self_inverse_points] = np.ma.masked
        else:
            new_array = np.ma.array(new_array, mask=non_self_inverse_points)

    # Transform the target points to the source projection and mask any points
    # that fall outside the original source domain.
    if mask_extrapolated:
        target_in_source_xyz = source_cs.transform_points(
            target_proj, target_x_points, target_y_points)
        target_in_source_x = target_in_source_xyz[..., 0]
        target_in_source_y = target_in_source_xyz[..., 1]

        bounds = _determine_bounds(source_x_coords, source_y_coords, source_cs)

        outside_source_domain = ((target_in_source_y >= bounds['y'][1]) |
                                 (target_in_source_y <= bounds['y'][0]))

        tmp_inside = np.zeros_like(outside_source_domain)
        for bound_x in bounds['x']:
            tmp_inside = tmp_inside | ((target_in_source_x <= bound_x[1]) &
                                       (target_in_source_x >= bound_x[0]))
        outside_source_domain = outside_source_domain | ~tmp_inside

        if np.ma.isMaskedArray(new_array):
            if np.any(outside_source_domain):
                new_array[outside_source_domain] = np.ma.masked
        else:
            new_array = np.ma.array(new_array, mask=False)
            if new_array.ndim == 3:
                for i in range(new_array.shape[2]):
                    new_array[outside_source_domain, i] = np.ma.masked
            else:
                new_array[outside_source_domain] = np.ma.masked
    return new_array

########NEW FILE########
__FILENAME__ = img_nest
# (C) British Crown Copyright 2011 - 2014, Met Office
#
# This file is part of cartopy.
#
# cartopy is free software: you can redistribute it and/or modify it under
# the terms of the GNU Lesser General Public License as published by the
# Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# cartopy is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Lesser General Public License for more details.
#
# You should have received a copy of the GNU Lesser General Public License
# along with cartopy.  If not, see <http://www.gnu.org/licenses/>.


import collections
import glob
import itertools
import os.path

import numpy as np
import PIL.Image
from shapely.geometry import box


_img_class_attrs = ['filename', 'extent', 'origin', 'pixel_size']


class Img(collections.namedtuple('Img', _img_class_attrs)):
    def __new__(cls, *args, **kwargs):
        # ensure any lists given as args or kwargs are turned into tuples.
        new_args = []
        for item in args:
            if isinstance(item, list):
                item = tuple(item)
            new_args.append(item)
        new_kwargs = {}
        for k, item in kwargs.items():
            if isinstance(item, list):
                item = tuple(item)
            new_kwargs[k] = item
        return super(Img, cls).__new__(cls, *new_args, **new_kwargs)

    def __init__(self, *args, **kwargs):
        """
        Represents a simple geo-located image.

        Args:

        * filename:
            Filename of the image tile.

        * extent:
            The (x_lower, x_upper, y_lower, y_upper) extent of the image
            in units of the native projection.

        * origin:
            Name of the origin.

        * pixel_size:
            The (x_scale, y_scale) pixel width, in units of the native
            projection per pixel.

        .. note::
            API is likely to change in the future to include a CRS.

        """
        self._bbox = None

    def __getstate__(self):
        """
        Override the default to ensure when pickling that any new attributes
        introduced are included in the pickled object.

        """
        return self.__dict__

    def bbox(self):
        """
        Return a :class:`~shapely.geometry.polygon.Polygon` instance for
        this image's extents.

        """
        if self._bbox is None:
            x0, x1, y0, y1 = self.extent
            self._bbox = box(x0, y0, x1, y1)
        return self._bbox

    @staticmethod
    def world_files(fname):
        """
        Determine potential world filename combinations, without checking
        their existence.

        For example, a '*.tif' file may have one of the following
        popular conventions for world file extensions '*.tifw',
        '*.tfw', '*.TIFW' or '*.TFW'.

        Given the possible world file extensions, the upper case basename
        combinations are also generated. For example, the file 'map.tif'
        will generate the following world file variations, 'map.tifw',
        'map.tfw', 'map.TIFW', 'map.TFW', 'MAP.tifw', 'MAP.tfw', 'MAP.TIFW'
        and 'MAP.TFW'.

        Args:

        * fname:
            Name of the file for which to get all the possible world
            filename combinations.

        Returns:
            A list of possible world filename combinations.

        Examples:

        >>> from cartopy.io.img_nest import Img
        >>> Img.world_files('img.png')[:6]
        ['img.pngw', 'img.pgw', 'img.PNGW', 'img.PGW', 'IMG.pngw', 'IMG.pgw']
        >>> Img.world_files('/path/to/img.TIF')[:2]
        ['/path/to/img.tifw', '/path/to/img.tfw']
        >>> Img.world_files('/path/to/img/with_no_extension')[0]
        '/path/to/img/with_no_extension.w'

        """
        froot, fext = os.path.splitext(fname)
        # If there was no extension to the filename.
        if froot == fname:
            result = ['{}.{}'.format(fname, 'w'),
                      '{}.{}'.format(fname, 'W')]
        else:
            fext = fext[1::].lower()
            if len(fext) < 3:
                result = ['{}.{}'.format(fname, 'w'),
                          '{}.{}'.format(fname, 'W')]
            else:
                fext_types = [fext + 'w', fext[0] + fext[-1] + 'w']
                fext_types.extend([ext.upper() for ext in fext_types])
                result = ['{}.{}'.format(froot, ext) for ext in fext_types]

        def _convert_basename(name):
            dirname, basename = os.path.dirname(name), os.path.basename(name)
            base, ext = os.path.splitext(basename)
            if base == base.upper():
                result = base.lower() + ext
            else:
                result = base.upper() + ext
            if dirname:
                result = os.path.join(dirname, result)
            return result

        result.extend(map(_convert_basename, result))
        return result

    def __array__(self):
        return np.array(PIL.Image.open(self.filename))

    @classmethod
    def from_world_file(cls, img_fname, world_fname):
        """
        Return an Img instance from the given image filename and
        worldfile filename.

        """
        im = PIL.Image.open(img_fname)
        with open(world_fname) as world_fh:
            extent, pix_size = cls.world_file_extent(world_fh, im.size)
        return cls(img_fname, extent, 'lower', pix_size)

    @staticmethod
    def world_file_extent(worldfile_handle, im_shape):
        """
        Return the extent ``(x0, x1, y0, y1)`` and pixel size
        ``(x_width, y_width)`` as defined in the given worldfile file handle
        and associated image shape ``(x, y)``.

        """
        lines = worldfile_handle.readlines()
        if len(lines) != 6:
            raise ValueError('Only world files with 6 lines are supported.')

        pix_size = (float(lines[0]), float(lines[3]))
        pix_rotation = (float(lines[1]), float(lines[2]))
        if pix_rotation != (0., 0.):
            raise ValueError('Rotated pixels in world files is not currently '
                             'supported.')
        ul_corner = (float(lines[4]), float(lines[5]))

        min_x, max_x = (ul_corner[0] - pix_size[0]/2.,
                        ul_corner[0] + pix_size[0]*im_shape[0] -
                        pix_size[0]/2.)
        min_y, max_y = (ul_corner[1] - pix_size[1]/2.,
                        ul_corner[1] + pix_size[1]*im_shape[1] -
                        pix_size[1]/2.)
        return (min_x, max_x, min_y, max_y), pix_size


class ImageCollection(object):
    def __init__(self, name, crs, images=None):
        """
        Represents a collection of images at the same logical level.

        Typically these are images at the same zoom level or resolution.

        Args:

        * name:
            The name of the image collection.

        * crs:
            The :class:`~cartopy.crs.Projection` instance.

        Kwargs:

        * images:
            A list of one or more :class:`~cartopy.io.img_nest.Img` instances.

        """
        self.name = name
        self.crs = crs
        self.images = images or []

    def scan_dir_for_imgs(self, directory, glob_pattern='*.tif',
                          img_class=Img):
        """
        Search the given directory for the associated world files
        of the image files.

        Args:

        * directory:
            The directory path to search for image files.

        Kwargs:

        * glob_pattern:
            The image filename glob pattern to search with.
            Defaults to '*.tif'.

        * img_class
            The class used to construct each image in the Collection.

        .. note::
            Does not recursively search sub-directories.

        """
        imgs = glob.glob(os.path.join(directory, glob_pattern))

        for img in imgs:
            dirname, fname = os.path.split(img)
            worlds = img_class.world_files(fname)
            for fworld in worlds:
                fworld = os.path.join(dirname, fworld)
                if os.path.exists(fworld):
                    break
            else:
                msg = 'Image file {!r} has no associated world file'
                raise ValueError(msg.format(img))

            self.images.append(img_class.from_world_file(img, fworld))


class NestedImageCollection(object):
    def __init__(self, name, crs, collections, _ancestry=None):
        """
        Represents a complex nest of ImageCollections.

        On construction, the image collections are scanned for ancestry,
        leading to fast image finding capabilities.

        A complex (and time consuming to create) NestedImageCollection instance
        can be saved as a pickle file and subsequently be (quickly) restored.

        There is a simplified creation interface for NestedImageCollection
        ``from_configuration`` for more detail.

        Args:

        * name:
            The name of the nested image collection.

        * crs:
            The native :class:`~cartopy.crs.Projection` of all the image
            collections.

        * collections:
            A list of one or more :class:`~cartopy.io.img_nest.ImageCollection`
            instances.

        """
        # NOTE: all collections must have the same crs.
        _names = set([collection.name for collection in collections])
        assert len(_names) == len(collections), \
            'The collections must have unique names.'

        self.name = name
        self.crs = crs
        self._collections_by_name = {collection.name: collection
                                     for collection in collections}
        sort_func = lambda c: np.max([image.bbox().area for image in c.images])
        self._collections = sorted(collections, key=sort_func, reverse=True)
        self._ancestry = {}
        """
        maps (collection name, image) to a list of children
        (collection name, image).
        """
        if _ancestry is not None:
            self._ancestry = _ancestry
        else:
            parent_wth_children = itertools.izip(self._collections,
                                                 self._collections[1:])
            for parent_collection, collection in parent_wth_children:
                for parent_image in parent_collection.images:
                    for image in collection.images:
                        if self._is_parent(parent_image, image):
                            # append the child image to the parent's ancestry
                            key = (parent_collection.name, parent_image)
                            self._ancestry.setdefault(key, []).append(
                                (collection.name, image))

            # TODO check that the ancestry is in a good state (i.e. that each
            # collection has child images)

    @staticmethod
    def _is_parent(parent, child):
        """
        Returns whether the given Image is the parent of image.
        Used by __init__.

        """
        result = False
        pbox = parent.bbox()
        cbox = child.bbox()
        if pbox.area > cbox.area:
            result = pbox.intersects(cbox) and not pbox.touches(cbox)
        return result

    def image_for_domain(self, target_domain, target_z):
        """
        Determine the image that provides complete coverage of target location.

        The composed image is merged from one or more image tiles that overlay
        the target location and provide complete image coverage of the target
        location.

        Args:

        * target_domain:
            A :class:`~shapely.geometry.linestring.LineString` instance that
            specifies the target location requiring image coverage.

        * target_z:
            The name of the target
            :class`~cartopy.io.img_nest.ImageCollection` which specifies the
            target zoom level (resolution) of the required images.

        Returns:
            A tuple containing three items, consisting of the target
            location :class:`numpy.ndarray` image data, the
            (x-lower, x-upper, y-lower, y-upper) extent of the image, and the
            origin for the target location.

        """
        # XXX Copied from cartopy.io.img_tiles
        if target_z not in self._collections_by_name:
            # TODO: Handle integer depths also?
            msg = '{!r} is not one of the possible collections.'
            raise ValueError(msg.format(target_z))

        tiles = []
        for tile in self.find_images(target_domain, target_z):
            try:
                img, extent, origin = self.get_image(tile)
            except IOError:
                continue

            img = np.array(img)

            x = np.linspace(extent[0], extent[1], img.shape[1],
                            endpoint=False)
            y = np.linspace(extent[2], extent[3], img.shape[0],
                            endpoint=False)
            tiles.append([np.array(img), x, y, origin])

        from cartopy.io.img_tiles import _merge_tiles
        img, extent, origin = _merge_tiles(tiles)
        return img, extent, origin

    def find_images(self, target_domain, target_z, start_tiles=None):
        """
        A generator that finds all images that overlap the bounded
        target location.

        Args:

        * target_domain:
            A :class:`~shapely.geometry.linestring.LineString` instance that
            specifies the target location requiring image coverage.

        * target_z:
            The name of the target
            :class:`~cartopy.io.img_nest.ImageCollection` which specifies
            the target zoom level (resolution) of the required images.

        Kwargs:

        * start_tiles:
            A list of one or more tuple pairs, composed of a
            :class:`~cartopy.io.img_nest.ImageCollection` name and an
            :class:`~cartopy.io.img_nest.Img` instance, from which to search
            for the target images.

        Returns:
            A generator tuple pair composed of a
            :class:`~cartopy.io.img_nest.ImageCollection` name and an
            :class:`~cartopy.io.img_nest.Img` instance.

        """
        # XXX Copied from cartopy.io.img_tiles
        if target_z not in self._collections_by_name:
            # TODO: Handle integer depths also?
            msg = '{!r} is not one of the possible collections.'
            raise ValueError(msg.format(target_z))

        if start_tiles is None:
            start_tiles = ((self._collections[0].name, img)
                           for img in self._collections[0].images)

        for start_tile in start_tiles:
            # recursively drill down to the images at the target zoom
            domain = start_tile[1].bbox()
            if target_domain.intersects(domain) and \
                    not target_domain.touches(domain):
                if start_tile[0] == target_z:
                        yield start_tile
                else:
                    for tile in self.subtiles(start_tile):
                        for result in self.find_images(target_domain,
                                                       target_z,
                                                       start_tiles=[tile]):
                            yield result

    def subtiles(self, collection_image):
        """
        Find the higher resolution image tiles that compose this parent
        image tile.

        Args:

        * collection_image:
            A tuple pair containing the parent
            :class:`~cartopy.io.img_nest.ImageCollection` name and
            :class:`~cartopy.io.img_nest.Img` instance.

        Returns:
            An iterator of tuple pairs containing the higher resolution child
            :class:`~cartopy.io.img_nest.ImageCollection` name and
            :class:`~cartopy.io.img_nest.Img` instance that compose the parent.

        """
        return iter(self._ancestry.get(collection_image, []))

    desired_tile_form = 'RGB'

    def get_image(self, collection_image):
        """
        Retrieve the data of the target image from file.

        .. note::
          The format of the retrieved image file data is controlled by
          :attr:`~cartopy.io.img_nest.NestedImageCollection.desired_tile_form`,
          which defaults to 'RGB' format.

        Args:

        * collection_image:
            A tuple pair containing the target
            :class:`~cartopy.io.img_nest.ImageCollection` name and
            :class:`~cartopy.io.img_nest.Img` instance.

        Returns:
            A tuple containing three items, consisting of the associated image
            file data, the (x_lower, x_upper, y_lower, y_upper) extent of the
            image, and the image origin.

        """
        img = collection_image[1]
        img_data = PIL.Image.open(img.filename)
        img_data = img_data.convert(self.desired_tile_form)
        return img_data, img.extent, img.origin

    @classmethod
    def from_configuration(cls, name, crs, name_dir_pairs,
                           glob_pattern='*.tif',
                           img_class=Img):
        """
        Creates a :class:`~cartopy.io.img_nest.NestedImageCollection` instance
        given the list of image collection name and directory path pairs.

        This is very convenient functionality for simple configuration level
        creation of this complex object.

        For example, to produce a nested collection of OS map tiles::

            files = [['OS 1:1,000,000', '/directory/to/1_to_1m'],
                     ['OS 1:250,000', '/directory/to/1_to_250k'],
                     ['OS 1:50,000', '/directory/to/1_to_50k'],
                    ]
            r = NestedImageCollection.from_configuration('os',
                                                         ccrs.OSGB(),
                                                         files)

        .. important::
            The list of image collection name and directory path pairs must be
            given in increasing resolution order i.e. from low resolution to
            high resolution.

        Args:

        * name:
            The name for the
            :class:`~cartopy.io.img_nest.NestedImageCollection` instance.

        * crs:
            The :class:`~cartopy.crs.Projection` of the image collection.

        * name_dir_pairs:
            A list of image collection name and directory path pairs.

        Kwargs:

        * glob_pattern:
            The image collection filename glob pattern.
            Defaults to '*.tif'.

        * img_class:
            The class of images created in the image collection.

        Returns:
            A :class:`~cartopy.io.img_nest.NestedImageCollection` instance.

        """
        collections = []
        for collection_name, collection_dir in name_dir_pairs:
            collection = ImageCollection(collection_name, crs)
            collection.scan_dir_for_imgs(collection_dir,
                                         glob_pattern=glob_pattern,
                                         img_class=img_class)
            collections.append(collection)
        return cls(name, crs, collections)

########NEW FILE########
__FILENAME__ = img_tiles
# (C) British Crown Copyright 2011 - 2012, Met Office
#
# This file is part of cartopy.
#
# cartopy is free software: you can redistribute it and/or modify it under
# the terms of the GNU Lesser General Public License as published by the
# Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# cartopy is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Lesser General Public License for more details.
#
# You should have received a copy of the GNU Lesser General Public License
# along with cartopy.  If not, see <http://www.gnu.org/licenses/>.


"""
Implements image tile identification and fetching from various sources.

Tile generation is explicitly not yet implemented.

"""
from __future__ import division

import PIL.Image as Image
import shapely.geometry as sgeom
import numpy as np

import cartopy.crs as ccrs


class GoogleTiles(object):
    """
    Implements web tile retrieval using the Google WTS coordinate system.

    A "tile" in this class refers to the coordinates (x, y, z).

    """
    def __init__(self, desired_tile_form='RGB', style="street"):
        """
        :param desired_tile_form:
        :param style: The style for the Google Maps tiles. One of 'street',
            'satellite', 'terrain', and 'only_streets'.
            Defaults to 'street'.
        """
        # Only streets are partly transparent tiles that can be overlayed over
        # the satellite map to create the known hybrid style from google.
        styles = ["street", "satellite", "terrain", "only_streets"]
        style = style.lower()
        if style not in styles:
            msg = "Invalid style '%s'. Valid styles: %s" % \
                (style, ", ".join(styles))
            raise ValueError(msg)
        self.style = style

        # The 'satellite' and 'terrain' styles require pillow with a jpeg
        # decoder.
        if self.style in ["satellite", "terrain"] and \
                not hasattr(Image.core, "jpeg_decoder") or \
                not Image.core.jpeg_decoder:
            msg = "The '%s' style requires pillow with jpeg decoding support."
            raise ValueError(msg % self.style)

        self.imgs = []
        self.crs = ccrs.GOOGLE_MERCATOR
        self.desired_tile_form = desired_tile_form

    def image_for_domain(self, target_domain, target_z):
        tiles = []
        for tile in self.find_images(target_domain, target_z):
            try:
                img, extent, origin = self.get_image(tile)
            except IOError:
                continue
            img = np.array(img)
            x = np.linspace(extent[0], extent[1], img.shape[1])
            y = np.linspace(extent[2], extent[3], img.shape[0])
            tiles.append([img, x, y, origin])

        img, extent, origin = _merge_tiles(tiles)
        return img, extent, origin

    def _find_images(self, target_domain, target_z, start_tile=(0, 0, 0)):
        """Target domain is a shapely polygon in native coordinates."""

        assert isinstance(target_z, int) and target_z >= 0, ('target_z must '
                                                             'be an integer '
                                                             '>=0.')

        # Recursively drill down to the images at the target zoom.
        x0, x1, y0, y1 = self._tileextent(start_tile)
        domain = sgeom.box(x0, y0, x1, y1)
        if domain.intersects(target_domain):
            if start_tile[2] == target_z:
                    yield start_tile
            else:
                for tile in self._subtiles(start_tile):
                    for result in self._find_images(target_domain, target_z,
                                                    start_tile=tile):
                        yield result

    find_images = _find_images

    def subtiles(self, x_y_z):
        x, y, z = x_y_z
        # Google tile specific (i.e. up->down).
        for xi in range(0, 2):
            for yi in range(0, 2):
                yield x * 2 + xi, y * 2 + yi, z + 1

    _subtiles = subtiles

    def tile_bbox(self, x, y, z, y0_at_north_pole=True):
        """
        Returns the ``(x0, x1), (y0, y1)`` bounding box for the given x, y, z
        tile position.

        Parameters
        ----------
        x, y, z : int
            The x, y, z tile coordinates in the Google tile numbering system
            (with y=0 being at the north pole), unless `y0_at_north_pole` is
            set to ``False``, in which case `y` is in the TMS numbering system
            (with y=0 being at the south pole).
        y0_at_north_pole : bool
            Whether the numbering of the y coordinate starts at the north
            pole (as is the convention for Google tiles), or the south
            pole (as is the convention for TMS).

        """
        n = 2 ** z
        assert 0 <= x <= (n - 1), ("Tile's x index is out of range. Upper "
                                   "limit %s. Got %s" % (n, x))
        assert 0 <= y <= (n - 1), ("Tile's y index is out of range. Upper "
                                   "limit %s. Got %s" % (n, y))

        x0, x1 = self.crs.x_limits
        y0, y1 = self.crs.y_limits

        # Compute the box height and width in native coordinates
        # for this zoom level.
        box_h = (y1 - y0) / n
        box_w = (x1 - x0) / n

        # Compute the native x & y extents of the tile.
        n_xs = x0 + (x + np.arange(0, 2, dtype=np.float64)) * box_w
        n_ys = y0 + (y + np.arange(0, 2, dtype=np.float64)) * box_h

        if y0_at_north_pole:
            n_ys = -1 * n_ys[::-1]

        return n_xs, n_ys

    def tileextent(self, x_y_z):
        """Returns extent tuple ``(x0,x1,y0,y1)`` in Mercator coordinates."""
        x, y, z = x_y_z
        x_lim, y_lim = self.tile_bbox(x, y, z, y0_at_north_pole=True)
        return tuple(x_lim) + tuple(y_lim)

    _tileextent = tileextent

    def _image_url(self, tile):
        style_dict = {
            "street": "m",
            "satellite": "s",
            "terrain": "t",
            "only_streets": "h"}
        url = ('http://mts0.google.com/vt/lyrs={style}@177000000&hl=en&'
               'src=api&x={tile_x}&y={tile_y}&z={tile_z}&s=G'.format(
                   style=style_dict[self.style],
                   tile_x=tile[0],
                   tile_y=tile[1],
                   tile_z=tile[2]))
        return url

    def get_image(self, tile):
        import cStringIO  # *much* faster than StringIO
        import urllib

        url = self._image_url(tile)

        fh = urllib.urlopen(url)
        im_data = cStringIO.StringIO(fh.read())
        fh.close()
        img = Image.open(im_data)

        img = img.convert(self.desired_tile_form)

        return img, self.tileextent(tile), 'lower'


class MapQuestOSM(GoogleTiles):
    # http://developer.mapquest.com/web/products/open/map for terms of use
    def _image_url(self, tile):
        x, y, z = tile
        url = 'http://otile1.mqcdn.com/tiles/1.0.0/osm/%s/%s/%s.jpg' % (
            z, x, y)
        return url


class MapQuestOpenAerial(GoogleTiles):
    # http://developer.mapquest.com/web/products/open/map for terms of use
    # The following attribution should be included in the resulting image:
    # "Portions Courtesy NASA/JPL-Caltech and U.S. Depart. of Agriculture,
    #  Farm Service Agency"
    def _image_url(self, tile):
        x, y, z = tile
        url = 'http://oatile1.mqcdn.com/tiles/1.0.0/sat/%s/%s/%s.jpg' % (
            z, x, y)
        return url


class OSM(GoogleTiles):
    # http://developer.mapquest.com/web/products/open/map for terms of use
    def _image_url(self, tile):
        x, y, z = tile
        url = 'http://a.tile.openstreetmap.org/%s/%s/%s.png' % (z, x, y)
        return url


class StamenTerrain(GoogleTiles):
    """
    Terrain tiles defined for the continental United States, and include land
    color and shaded hills. The land colors are a custom palette developed by
    Gem Spear for the National Atlas 1km land cover data set, which defines
    twenty-four land classifications including five kinds of forest,
    combinations of shrubs, grasses and crops, and a few tundras and wetlands.
    The colors are at their highest contrast when fully zoomed-out to the
    whole U.S., and they slowly fade out to pale off-white as you zoom in to
    leave room for foreground data and break up the weirdness of large areas
    of flat, dark green.

    Additional info:
    http://mike.teczno.com/notes/osm-us-terrain-layer/background.html
    http://maps.stamen.com/#terrain/12/37.6902/-122.3600
    http://wiki.openstreetmap.org/wiki/List_of_OSM_based_Services
    https://github.com/migurski/DEM-Tools
    """
    def _image_url(self, tile):
        x, y, z = tile
        url = 'http://tile.stamen.com/terrain-background/%s/%s/%s.png' % (
            z, x, y)
        return url


class QuadtreeTiles(GoogleTiles):
    """
    Implements web tile retrieval using the Microsoft WTS quadkey coordinate
    system.

    A "tile" in this class refers to a quadkey such as "1", "14" or "141"
    where the length of the quatree is the zoom level in Google Tile terms.

    """
    def _image_url(self, tile):
        url = ('http://ecn.dynamic.t1.tiles.virtualearth.net/comp/'
               'CompositionHandler/{tile}?mkt=en-'
               'gb&it=A,G,L&shading=hill&n=z'.format(tile=tile))
        return url

    def tms_to_quadkey(self, tms, google=False):
        quadKey = ""
        x, y, z = tms
        # this algorithm works with google tiles, rather than tms, so convert
        # to those first.
        if not google:
            y = (2 ** z - 1) - y
        for i in range(z, 0, -1):
            digit = 0
            mask = 1 << (i - 1)
            if (x & mask) != 0:
                digit += 1
            if (y & mask) != 0:
                digit += 2
            quadKey += str(digit)
        return quadKey

    def quadkey_to_tms(self, quadkey, google=False):
        # algorithm ported from
        # http://msdn.microsoft.com/en-us/library/bb259689.aspx
        assert isinstance(quadkey, basestring), 'quadkey must be a string'

        x = y = 0
        z = len(quadkey)
        for i in range(z, 0, -1):
            mask = 1 << (i - 1)
            if quadkey[z - i] == '0':
                pass
            elif quadkey[z - i] == '1':
                x |= mask
            elif quadkey[z - i] == '2':
                y |= mask
            elif quadkey[z - i] == '3':
                x |= mask
                y |= mask
            else:
                raise ValueError('Invalid QuadKey digit '
                                 'sequence.' + str(quadkey))
        # the algorithm works to google tiles, so convert to tms
        if not google:
            y = (2 ** z - 1) - y
        return (x, y, z)

    def subtiles(self, quadkey):
        for i in range(4):
            yield quadkey + str(i)

    def tileextent(self, quadkey):
        x_y_z = self.quadkey_to_tms(quadkey, google=True)
        return GoogleTiles.tileextent(self, x_y_z)

    def find_images(self, target_domain, target_z, start_tile=None):
        """
        Find all the quadtree's at the given target zoom, in the given
        target domain.

        target_z must be a value >= 1.
        """
        if target_z == 0:
            raise ValueError('The empty quadtree cannot be returned.')

        if start_tile is None:
            start_tiles = ['0', '1', '2', '3']
        else:
            start_tiles = [start_tile]

        for start_tile in start_tiles:
            start_tile = self.quadkey_to_tms(start_tile, google=True)
            for tile in GoogleTiles.find_images(self, target_domain, target_z,
                                                start_tile=start_tile):
                yield self.tms_to_quadkey(tile, google=True)


def _merge_tiles(tiles):
    """Return a single image, merging the given images."""
    if not tiles:
        raise ValueError('A non-empty list of tiles should '
                         'be provided to merge.')
    xset = [set(x) for i, x, y, _ in tiles]
    yset = [set(y) for i, x, y, _ in tiles]

    xs = xset[0]
    xs.update(*xset[1:])
    ys = yset[0]
    ys.update(*yset[1:])
    xs = sorted(xs)
    ys = sorted(ys)

    other_len = tiles[0][0].shape[2:]
    img = np.zeros((len(ys), len(xs)) + other_len, dtype=np.uint8) - 1

    for tile_img, x, y, origin in tiles:
        y_first, y_last = y[0], y[-1]
        yi0, yi1 = np.where((y_first == ys) | (y_last == ys))[0]
        if origin == 'upper':
            yi0 = tile_img.shape[0] - yi0 - 1
            yi1 = tile_img.shape[0] - yi1 - 1
        start, stop, step = yi0, yi1, 1 if yi0 < yi1 else -1
        if step == 1 and stop == img.shape[0] - 1:
            stop = None
        elif step == -1 and stop == 0:
            stop = None
        else:
            stop += step
        y_slice = slice(start, stop, step)

        xi0, xi1 = np.where((x[0] == xs) | (x[-1] == xs))[0]

        start, stop, step = xi0, xi1, 1 if xi0 < xi1 else -1

        if step == 1 and stop == img.shape[1] - 1:
            stop = None
        elif step == -1 and stop == 0:
            stop = None
        else:
            stop += step

        x_slice = slice(start, stop, step)

        img_slice = (y_slice, x_slice, Ellipsis)

        if origin == 'lower':
            tile_img = tile_img[::-1, ::]

        img[img_slice] = tile_img

    return img, [min(xs), max(xs), min(ys), max(ys)], 'lower'

########NEW FILE########
__FILENAME__ = ogc_clients
# (C) British Crown Copyright 2014, Met Office
#
# This file is part of cartopy.
#
# cartopy is free software: you can redistribute it and/or modify it under
# the terms of the GNU Lesser General Public License as published by the
# Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# cartopy is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Lesser General Public License for more details.
#
# You should have received a copy of the GNU Lesser General Public License
# along with cartopy.  If not, see <http://www.gnu.org/licenses/>.
"""
Implements RasterSource classes which can retrieve imagery from web services
such as WMS and WMTS.

"""
from __future__ import absolute_import, division

import io
import math
import weakref

from owslib.wms import WebMapService
import PIL.Image
import owslib.util
import owslib.wmts

from cartopy.io import RasterSource
import cartopy.crs as ccrs


# Hardcode some known EPSG codes for now.
_CRS_TO_OGC_SRS = {ccrs.PlateCarree(): 'EPSG:4326'
                   }

# Standard pixel size of 0.28 mm as defined by WMTS.
METERS_PER_PIXEL = 0.28e-3

_WGS84_METERS_PER_UNIT = 2 * math.pi * 6378137 / 360

METERS_PER_UNIT = {
    'urn:ogc:def:crs:EPSG::900913': 1,
    'urn:ogc:def:crs:OGC:1.3:CRS84': _WGS84_METERS_PER_UNIT,
}

_URN_TO_CRS = {
    'urn:ogc:def:crs:EPSG::900913': ccrs.GOOGLE_MERCATOR,
    'urn:ogc:def:crs:OGC:1.3:CRS84': ccrs.PlateCarree(),
}


class WMSRasterSource(RasterSource):
    """
    A WMS imagery retriever which can be added to a map.

    .. note:: Requires owslib and PIL to work.

    .. note::

        No caching of retrieved maps is done with this WMSRasterSource.

        To reduce load on the WMS server it is encouraged to tile
        map requests and subsequently stitch them together to recreate
        a single raster, thus allowing for a more aggressive caching scheme,
        but this WMSRasterSource does not currently implement WMS tile
        fetching.

        Whilst not the same service, there is also a WMTSRasterSource which
        makes use of tiles and comes with built-in caching for fast repeated
        map retrievals.

    """

    def __init__(self, service, layers, getmap_extra_kwargs=None):
        """
        Parameters
        ----------
        service : string or WebMapService instance
            The WebMapService instance, or URL of a WMS service, from whence
            to retrieve the image.
        layers : string or list of strings
            The name(s) of layers to use from the WMS service.
        getmap_extra_kwargs : dict or None
            Extra keywords to pass through to the service's getmap method.
            If None, a dictionary with ``{'transparent': True}`` will
            be defined.

        """
        if isinstance(service, basestring):
            service = WebMapService(service)

        if isinstance(layers, basestring):
            layers = [layers]

        if getmap_extra_kwargs is None:
            getmap_extra_kwargs = {'transparent': True}

        if len(layers) == 0:
            raise ValueError('One or more layers must be defined.')
        for layer in layers:
            if layer not in service.contents:
                raise ValueError('The {!r} layer does not exist in '
                                 'this service.'.format(layer))

        #: The OWSLib WebMapService instance.
        self.service = service

        #: The names of the layers to fetch.
        self.layers = layers

        #: Extra kwargs passed through to the service's getmap request.
        self.getmap_extra_kwargs = getmap_extra_kwargs

        self._srs_for_projection_id = {}

    def _srs(self, projection):
        key = id(projection)
        srs = self._srs_for_projection_id.get(key)
        if srs is None:
            srs = _CRS_TO_OGC_SRS.get(projection)
            if srs is None:
                raise ValueError('The projection {!r} was not convertible to '
                                 'a suitable WMS SRS.'.format(projection))
            for layer in self.layers:
                if srs not in self.service.contents[layer].crsOptions:
                    raise ValueError('The SRS {} is not a valid SRS for the '
                                     '{!r} WMS layer.'.format(srs, layer))
            self._srs_for_projection_id[key] = srs
        return srs

    def validate_projection(self, projection):
        self._srs(projection)

    def fetch_raster(self, projection, extent, target_resolution):
        service = self.service
        min_x, max_x, min_y, max_y = extent
        wms_image = service.getmap(layers=self.layers,
                                   srs=self._srs(projection),
                                   bbox=(min_x, min_y, max_x, max_y),
                                   size=target_resolution, format='image/png',
                                   **self.getmap_extra_kwargs)
        wms_image = PIL.Image.open(io.BytesIO(wms_image.read()))
        return wms_image, extent


class WMTSRasterSource(RasterSource):
    """
    A WMTS imagery retriever which can be added to a map.

    Uses tile caching for fast repeated map retrievals.

    .. note:: Requires owslib and PIL to work.

    """

    _shared_image_cache = weakref.WeakKeyDictionary()
    """
    A nested mapping from WMTS, layer name, tile matrix name, tile row
    and tile column to the resulting PIL image::

        {wmts: {(layer_name, tile_matrix_name): {(row, column): Image}}}

    This provides a significant boost when producing multiple maps of the
    same projection or with an interactive figure.

    """

    def __init__(self, wmts, layer_name):
        """
        Args:

            * wmts - The URL of the WMTS, or an
                     owslib.wmts.WebMapTileService instance.
            * layer_name - The name of the layer to use.

        """
        if not (hasattr(wmts, 'tilematrixsets') and
                hasattr(wmts, 'contents') and
                hasattr(wmts, 'gettile')):
            wmts = owslib.wmts.WebMapTileService(wmts)

        #: The OWSLib WebMapTileService instance.
        self.wmts = wmts

        #: The name of the layer to fetch.
        self.layer_name = layer_name

        self._matrix_set_name_map = {}

    def _matrix_set_name(self, projection):
        key = id(projection)
        matrix_set_name = self._matrix_set_name_map.get(key)
        if matrix_set_name is None:
            wmts = self.wmts
            layer = wmts.contents[self.layer_name]
            for tile_matrix_set_name in layer.tilematrixsets:
                tile_matrix_set = wmts.tilematrixsets[tile_matrix_set_name]
                crs_urn = tile_matrix_set.crs
                if crs_urn in _URN_TO_CRS:
                    tms_crs = _URN_TO_CRS[crs_urn]
                    if tms_crs == projection:
                        matrix_set_name = tile_matrix_set_name
                        break
            if matrix_set_name is None:
                available_urns = sorted(set(
                    wmts.tilematrixsets[name].crs for name in
                    layer.tilematrixsets))
                msg = 'Unable to find tile matrix for projection.'
                msg += '\n    Projection: ' + str(projection)
                msg += '\n    Available tile CRS URNs:'
                msg += '\n        ' + '\n        '.join(available_urns)
                raise ValueError(msg)
            self._matrix_set_name_map[key] = matrix_set_name
        return matrix_set_name

    def validate_projection(self, projection):
        self._matrix_set_name(projection)

    def fetch_raster(self, projection, extent, target_resolution):
        matrix_set_name = self._matrix_set_name(projection)
        min_x, max_x, min_y, max_y = extent
        width, height = target_resolution
        max_pixel_span = min((max_x - min_x) / width,
                             (max_y - min_y) / height)
        image, extent = self._wmts_images(
            self.wmts, self.layer_name, matrix_set_name,
            extent, max_pixel_span)
        return image, extent

    def _choose_matrix(self, tile_matrices, meters_per_unit, max_pixel_span):
        # Get the tile matrices in order of increasing resolution.
        tile_matrices = sorted(tile_matrices,
                               key=lambda tm: tm.scaledenominator,
                               reverse=True)

        # Find which tile matrix has the appropriate resolution.
        max_scale = max_pixel_span * meters_per_unit / METERS_PER_PIXEL
        ok_tile_matrices = filter(lambda tm: tm.scaledenominator <= max_scale,
                                  tile_matrices)
        if ok_tile_matrices:
            tile_matrix = ok_tile_matrices[0]
        else:
            tile_matrix = tile_matrices[-1]
        return tile_matrix

    def _tile_span(self, tile_matrix, meters_per_unit):
        pixel_span = tile_matrix.scaledenominator * (
            METERS_PER_PIXEL / meters_per_unit)
        tile_span_x = tile_matrix.tilewidth * pixel_span
        tile_span_y = tile_matrix.tileheight * pixel_span
        return tile_span_x, tile_span_y

    def _select_tiles(self, tile_matrix, tile_span_x, tile_span_y, extent):
        # Convert the requested extent from CRS coordinates to tile
        # indices. See annex H of the WMTS v1.0.0 spec.
        # NB. The epsilons get rid of any tiles which only just
        # (i.e. one part in a million) intrude into the requested
        # extent. Since these wouldn't be visible anyway there's nothing
        # to be gained by spending the time downloading them.
        min_x, max_x, min_y, max_y = extent
        matrix_min_x, matrix_max_y = tile_matrix.topleftcorner
        epsilon = 1e-6
        min_col = int((min_x - matrix_min_x) / tile_span_x + epsilon)
        max_col = int((max_x - matrix_min_x) / tile_span_x - epsilon)
        min_row = int((matrix_max_y - max_y) / tile_span_y + epsilon)
        max_row = int((matrix_max_y - min_y) / tile_span_y - epsilon)
        # Clamp to the limits of the tile matrix.
        min_col = max(min_col, 0)
        max_col = min(max_col, tile_matrix.matrixwidth - 1)
        min_row = max(min_row, 0)
        max_row = min(max_row, tile_matrix.matrixheight - 1)
        return min_col, max_col, min_row, max_row

    def _wmts_images(self, wmts, layer_name, matrix_set_name, extent,
                     max_pixel_span):
        """
        Add images from the specified WMTS layer and matrix set to cover
        the specified extent at an appropriate resolution.

        The zoom level (aka. tile matrix) is chosen to give the lowest
        possible resolution which still provides the requested quality.
        If insufficient resolution is available, the highest available
        resolution is used.

        Args:

            * wmts - The owslib.wmts.WebMapTileService providing the tiles.
            * layer_name - The name of the layer to use.
            * matrix_set_name - The name of the matrix set to use.
            * extent - Tuple of (left, right, bottom, top) in Axes coordinates.
            * max_pixel_span - Preferred maximum pixel width or height
                               in Axes coordinates.

        """

        # Find which tile matrix has the appropriate resolution.
        tile_matrix_set = wmts.tilematrixsets[matrix_set_name]
        tile_matrices = tile_matrix_set.tilematrix.values()
        meters_per_unit = METERS_PER_UNIT[tile_matrix_set.crs]
        tile_matrix = self._choose_matrix(tile_matrices, meters_per_unit,
                                          max_pixel_span)

        # Determine which tiles are required to cover the requested extent.
        tile_span_x, tile_span_y = self._tile_span(tile_matrix,
                                                   meters_per_unit)
        min_col, max_col, min_row, max_row = self._select_tiles(
            tile_matrix, tile_span_x, tile_span_y, extent)

        # Find the relevant section of the image cache.
        tile_matrix_id = tile_matrix.identifier
        cache_by_wmts = WMTSRasterSource._shared_image_cache
        cache_by_layer_matrix = cache_by_wmts.setdefault(wmts, {})
        image_cache = cache_by_layer_matrix.setdefault((layer_name,
                                                        tile_matrix_id), {})

        # To avoid nasty seams between the individual tiles, we
        # accumulate the tile images into a single image.
        big_img = None
        n_rows = 1 + max_row - min_row
        n_cols = 1 + max_col - min_col
        for row in range(min_row, max_row + 1):
            for col in range(min_col, max_col + 1):
                # Get the tile's Image from the cache if possible.
                img_key = (row, col)
                img = image_cache.get(img_key)
                if img is None:
                    try:
                        tile = wmts.gettile(
                            layer=layer_name,
                            tilematrixset=matrix_set_name,
                            tilematrix=tile_matrix_id,
                            row=row, column=col)
                    except owslib.util.ServiceException as e:
                        if 'TileOutOfRange' in e.message:
                            continue
                        raise e
                    img = PIL.Image.open(io.BytesIO(tile.read()))
                    image_cache[img_key] = img
                if big_img is None:
                    size = (img.size[0] * n_cols, img.size[1] * n_rows)
                    big_img = PIL.Image.new('RGBA', size, (255, 255, 255, 255))
                top = (row - min_row) * tile_matrix.tileheight
                left = (col - min_col) * tile_matrix.tilewidth
                big_img.paste(img, (left, top))

        if big_img is None:
            img_extent = None
        else:
            matrix_min_x, matrix_max_y = tile_matrix.topleftcorner
            min_img_x = matrix_min_x + tile_span_x * min_col
            max_img_y = matrix_max_y - tile_span_y * min_row
            img_extent = (min_img_x, min_img_x + n_cols * tile_span_x,
                          max_img_y - n_rows * tile_span_y, max_img_y)
        return big_img, img_extent

########NEW FILE########
__FILENAME__ = shapereader
# (C) British Crown Copyright 2011 - 2012, Met Office
#
# This file is part of cartopy.
#
# cartopy is free software: you can redistribute it and/or modify it under
# the terms of the GNU Lesser General Public License as published by the
# Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# cartopy is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Lesser General Public License for more details.
#
# You should have received a copy of the GNU Lesser General Public License
# along with cartopy.  If not, see <http://www.gnu.org/licenses/>.


"""
Combines the shapefile access of pyshp with the
geometry representation of shapely:

    >>> import os.path
    >>> import cartopy.io.shapereader as shapereader
    >>> filename = natural_earth(resolution='110m',
    ...                          category='physical',
    ...                          name='geography_regions_points')
    >>> reader = shapereader.Reader(filename)
    >>> len(reader)
    3
    >>> records = list(reader.records())
    >>> print type(records[0])
    <class 'cartopy.io.shapereader.Record'>
    >>> print records[0].attributes.keys()
    ['comment', 'scalerank', 'region', 'name', 'subregion', 'lat_y', \
'featurecla', 'long_x', 'name_alt']
    >>> print records[0].attributes['name']
    Niagara Falls
    >>> geoms = list(reader.geometries())
    >>> print type(geoms[0])
    <class 'shapely.geometry.point.Point'>

"""
import glob
import itertools
import os

from shapely.geometry import MultiLineString, MultiPolygon, Point, Polygon
import shapefile

from cartopy.io import Downloader
from cartopy import config


__all__ = ['Reader', 'Record']


def _create_point(shape):
    return Point(shape.points[0])


def _create_polyline(shape):
    if not shape.points:
        return MultiLineString()

    parts = list(shape.parts) + [None]
    bounds = zip(parts[:-1], parts[1:])
    lines = [shape.points[slice(lower, upper)] for lower, upper in bounds]
    return MultiLineString(lines)


def _create_polygon(shape):
    if not shape.points:
        return MultiPolygon()

    # Partition the shapefile rings into outer rings/polygons (clockwise) and
    # inner rings/holes (anti-clockwise).
    parts = list(shape.parts) + [None]
    bounds = zip(parts[:-1], parts[1:])
    outer_polygons_and_holes = []
    inner_polygons = []
    for lower, upper in bounds:
        polygon = Polygon(shape.points[slice(lower, upper)])
        if polygon.exterior.is_ccw:
            inner_polygons.append(polygon)
        else:
            outer_polygons_and_holes.append((polygon, []))

    # Find the appropriate outer ring for each inner ring.
    # aka. Group the holes with their containing polygons.
    for inner_polygon in inner_polygons:
        for outer_polygon, holes in outer_polygons_and_holes:
            if outer_polygon.contains(inner_polygon):
                holes.append(inner_polygon.exterior.coords)
                break

    polygon_defns = [(outer_polygon.exterior.coords, holes)
                     for outer_polygon, holes in outer_polygons_and_holes]
    return MultiPolygon(polygon_defns)


def _make_geometry(geometry_factory, shape):
    geometry = None
    if shape.shapeType != shapefile.NULL:
        geometry = geometry_factory(shape)
    return geometry


# The mapping from shapefile shapeType values to geometry creation functions.
GEOMETRY_FACTORIES = {
    shapefile.POINT: _create_point,
    shapefile.POLYLINE: _create_polyline,
    shapefile.POLYGON: _create_polygon,
}


class Record(object):
    """
    A single logical entry from a shapefile, combining the attributes with
    their associated geometry.

    """
    def __init__(self, shape, geometry_factory, attributes, fields):
        self._shape = shape
        self._geometry_factory = geometry_factory

        self._bounds = None
        # if the record defines a bbox, then use that for the shape's bounds,
        # rather than using the full geometry in the bounds property
        if hasattr(shape, 'bbox'):
            self._bounds = tuple(shape.bbox)

        self._geometry = False
        """The cached geometry instance for this Record."""

        self.attributes = attributes
        """A dictionary mapping attribute names to attribute values."""

        self._fields = fields

    def __repr__(self):
        return '<Record: %r, %r, <fields>>' % (self.geometry, self.attributes)

    def __str__(self):
        return 'Record(%s, %s, <fields>)' % (self.geometry, self.attributes)

    @property
    def bounds(self):
        """
        The bounds of this Record's
        :meth:`~Record.geometry`.

        """
        if self._bounds is None:
            self._bounds = self.geometry.bounds
        return self._bounds

    @property
    def geometry(self):
        """
        A shapely.geometry instance for this Record.

        The geometry may be ``None`` if a null shape is defined in the
        shapefile.

        """
        if self._geometry is False:
            self._geometry = _make_geometry(self._geometry_factory,
                                            self._shape)
        return self._geometry


class Reader(object):
    """
    Provides an interface for accessing the contents of a shapefile.

    The primary methods used on a Reader instance are
    :meth:`~Reader.records` and :meth:`~Reader.geometries`.

    """
    def __init__(self, filename):
        # Validate the filename/shapefile
        self._reader = reader = shapefile.Reader(filename)
        if reader.shp is None or reader.shx is None or reader.dbf is None:
            raise ValueError("Incomplete shapefile definition "
                             "in '%s'." % filename)

        # Figure out how to make appropriate shapely geometry instances
        shapeType = reader.shapeType
        self._geometry_factory = GEOMETRY_FACTORIES.get(shapeType)
        if self._geometry_factory is None:
            raise ValueError('Unsupported shape type: %s' % shapeType)

        self._fields = self._reader.fields

    def __len__(self):
        return self._reader.numRecords

    def geometries(self):
        """
        Returns an iterator of shapely geometries from the shapefile.

        This interface is useful for accessing the geometries of the
        shapefile where knowledge of the associated metadata is desired.
        In the case where further metadata is needed use the
        :meth:`~Reader.records`
        interface instead, extracting the geometry from the record with the
        :meth:`~Record.geometry` method.

        """
        geometry_factory = self._geometry_factory
        for i in xrange(self._reader.numRecords):
            shape = self._reader.shape(i)
            yield _make_geometry(geometry_factory, shape)

    def records(self):
        """
        Returns an iterator of :class:`~Record` instances.

        """
        geometry_factory = self._geometry_factory
        # Ignore the "DeletionFlag" field which always comes first
        fields = self._reader.fields[1:]
        field_names = [field[0] for field in fields]
        for i in xrange(self._reader.numRecords):
            shape_record = self._reader.shapeRecord(i)
            attributes = dict(zip(field_names, shape_record.record))
            yield Record(shape_record.shape, geometry_factory, attributes,
                         fields)


def natural_earth(resolution='110m', category='physical', name='coastline'):
    """
    Returns the path to the requested natural earth shapefile,
    downloading and unziping if necessary.

    """
    # get hold of the Downloader (typically a NEShpDownloader instance)
    # which we can then simply call its path method to get the appropriate
    # shapefile (it will download if necessary)
    ne_downloader = Downloader.from_config(('shapefiles', 'natural_earth',
                                            resolution, category, name))
    format_dict = {'config': config, 'category': category,
                   'name': name, 'resolution': resolution}
    return ne_downloader.path(format_dict)


class NEShpDownloader(Downloader):
    """
    Specialises :class:`cartopy.io.Downloader` to download the zipped
    Natural Earth shapefiles and extract them to the defined location
    (typically user configurable).

    The keys which should be passed through when using the ``format_dict``
    are typically ``category``, ``resolution`` and ``name``.

    """
    FORMAT_KEYS = ('config', 'resolution', 'category', 'name')

    # define the NaturalEarth url template. The natural earth website
    # returns a 302 status if accessing directly, so we use the nacis
    # url directly
    _NE_URL_TEMPLATE = ('http://www.nacis.org/naturalearth/{resolution}'
                        '/{category}/ne_{resolution}_{name}.zip')

    def __init__(self,
                 url_template=_NE_URL_TEMPLATE,
                 target_path_template=None,
                 pre_downloaded_path_template='',
                 ):
        # adds some NE defaults to the __init__ of a Downloader
        Downloader.__init__(self, url_template,
                            target_path_template,
                            pre_downloaded_path_template)

    def zip_file_contents(self, format_dict):
        """
        Returns a generator of the filenames to be found in the downloaded
        natural earth zip file.

        """
        for ext in ['.shp', '.dbf', '.shx']:
            yield ('ne_{resolution}_{name}'
                   '{extension}'.format(extension=ext, **format_dict))

    def acquire_resource(self, target_path, format_dict):
        """
        Downloads the zip file and extracts the files listed in
        :meth:`zip_file_contents` to the target path.

        """
        import cStringIO as StringIO
        from zipfile import ZipFile

        target_dir = os.path.dirname(target_path)
        if not os.path.isdir(target_dir):
            os.makedirs(target_dir)

        url = self.url(format_dict)

        shapefile_online = self._urlopen(url)

        zfh = ZipFile(StringIO.StringIO(shapefile_online.read()), 'r')

        for member_path in self.zip_file_contents(format_dict):
            ext = os.path.splitext(member_path)[1]
            target = os.path.splitext(target_path)[0] + ext
            member = zfh.getinfo(member_path)
            with open(target, 'wb') as fh:
                fh.write(zfh.open(member).read())

        shapefile_online.close()
        zfh.close()

        return target_path

    @staticmethod
    def default_downloader():
        """
        Returns a generic, standard, NEShpDownloader instance.

        Typically, a user will not need to call this staticmethod.

        To find the path template of the NEShpDownloader:

            >>> ne_dnldr = NEShpDownloader.default_downloader()
            >>> print ne_dnldr.target_path_template
            {config[data_dir]}/shapefiles/natural_earth/{category}/\
{resolution}_{name}.shp

        """
        default_spec = ('shapefiles', 'natural_earth', '{category}',
                        '{resolution}_{name}.shp')
        ne_path_template = os.path.join('{config[data_dir]}', *default_spec)
        pre_path_template = os.path.join('{config[pre_existing_data_dir]}',
                                         *default_spec)
        return NEShpDownloader(target_path_template=ne_path_template,
                               pre_downloaded_path_template=pre_path_template)


# add a generic Natural Earth shapefile downloader to the config dictionary's
# 'downloaders' section.
_ne_key = ('shapefiles', 'natural_earth')
config['downloaders'].setdefault(_ne_key,
                                 NEShpDownloader.default_downloader())


def gshhs(scale='c', level=1):
    """
    Returns the path to the requested GSHHS shapefile,
    downloading and unziping if necessary.

    """
    # Get hold of the Downloader (typically a GSHHSShpDownloader instance)
    # and call its path method to get the appropriate shapefile (it will
    # download it if necessary).
    gshhs_downloader = Downloader.from_config(('shapefiles', 'gshhs',
                                               scale, level))
    format_dict = {'config': config, 'scale': scale, 'level': level}
    return gshhs_downloader.path(format_dict)


class GSHHSShpDownloader(Downloader):
    """
    Specialises :class:`cartopy.io.Downloader` to download the zipped
    GSHHS shapefiles and extract them to the defined location.

    The keys which should be passed through when using the ``format_dict``
    are ``scale`` (a single character indicating the resolution) and ``level``
    (a number indicating the type of feature).

    """
    FORMAT_KEYS = ('config', 'scale', 'level')

    _GSHHS_URL_TEMPLATE = ('http://www.ngdc.noaa.gov/mgg/shorelines/data/'
                           'gshhs/oldversions/version2.2.0/'
                           'GSHHS_shp_2.2.0.zip')

    def __init__(self,
                 url_template=_GSHHS_URL_TEMPLATE,
                 target_path_template=None,
                 pre_downloaded_path_template=''):
        super(GSHHSShpDownloader, self).__init__(url_template,
                                                 target_path_template,
                                                 pre_downloaded_path_template)

    def zip_file_contents(self, format_dict):
        """
        Returns a generator of the filenames to be found in the downloaded
        GSHHS zip file for the specified resource.

        """
        for ext in ['.shp', '.dbf', '.shx']:
            yield (os.path.join('GSHHS_shp', '{scale}',
                                'GSHHS_{scale}_L{level}{extension}'
                                ).format(extension=ext, **format_dict))

    def acquire_all_resources(self, format_dict):
        import cStringIO as StringIO
        from zipfile import ZipFile

        # Download archive.
        url = self.url(format_dict)
        shapefile_online = self._urlopen(url)
        zfh = ZipFile(StringIO.StringIO(shapefile_online.read()), 'r')
        shapefile_online.close()

        # Iterate through all scales and levels and extract relevant files.
        modified_format_dict = dict(format_dict)
        scales = ('c', 'l', 'i', 'h', 'f')
        levels = (1, 2, 3, 4)
        for scale, level in itertools.product(scales, levels):
            modified_format_dict.update({'scale': scale, 'level': level})
            target_path = self.target_path(modified_format_dict)
            target_dir = os.path.dirname(target_path)
            if not os.path.isdir(target_dir):
                os.makedirs(target_dir)

            for member_path in self.zip_file_contents(modified_format_dict):
                ext = os.path.splitext(member_path)[1]
                target = os.path.splitext(target_path)[0] + ext
                member = zfh.getinfo(member_path)
                with open(target, 'wb') as fh:
                    fh.write(zfh.open(member).read())

        zfh.close()

    def acquire_resource(self, target_path, format_dict):
        """
        Downloads the zip file and extracts the files listed in
        :meth:`zip_file_contents` to the target path.

        .. note:

            Because some of the GSHSS data is available with the cartopy
            repository, scales of "l" or "c" will not be downloaded if they
            exist in the ``cartopy.config['repo_data_dir']`` directory.

        """
        repo_fname_pattern = os.path.join(config['repo_data_dir'],
                                          'shapefiles', 'gshhs', '{scale}',
                                          'GSHHS_{scale}_L?.shp')
        repo_fname_pattern = repo_fname_pattern.format(**format_dict)
        repo_fnames = glob.glob(repo_fname_pattern)
        if repo_fnames:
            assert len(repo_fnames) == 1, '>1 repo files found for GSHHS'
            return repo_fnames[0]
        self.acquire_all_resources(format_dict)
        if not os.path.exists(target_path):
            raise RuntimeError('Failed to download and extract GSHHS '
                               'shapefile to {!r}.'.format(target_path))
        return target_path

    @staticmethod
    def default_downloader():
        """
        Returns a GSHHSShpDownloader instance that expects (and if necessary
        downloads and installs) shapefiles in the data directory of the
        cartopy installation.

        Typically, a user will not need to call this staticmethod.

        To find the path template of the GSHHSShpDownloader:

            >>> gshhs_dnldr = GSHHSShpDownloader.default_downloader()
            >>> print gshhs_dnldr.target_path_template
            {config[data_dir]}/shapefiles/gshhs/{scale}/\
GSHHS_{scale}_L{level}.shp

        """
        default_spec = ('shapefiles', 'gshhs', '{scale}',
                        'GSHHS_{scale}_L{level}.shp')
        gshhs_path_template = os.path.join('{config[data_dir]}',
                                           *default_spec)
        pre_path_tmplt = os.path.join('{config[pre_existing_data_dir]}',
                                      *default_spec)
        return GSHHSShpDownloader(target_path_template=gshhs_path_template,
                                  pre_downloaded_path_template=pre_path_tmplt)


# Add a GSHHS shapefile downloader to the config dictionary's
# 'downloaders' section.
_gshhs_key = ('shapefiles', 'gshhs')
config['downloaders'].setdefault(_gshhs_key,
                                 GSHHSShpDownloader.default_downloader())

########NEW FILE########
__FILENAME__ = srtm
# (C) British Crown Copyright 2011 - 2012, Met Office
#
# This file is part of cartopy.
#
# cartopy is free software: you can redistribute it and/or modify it under
# the terms of the GNU Lesser General Public License as published by the
# Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# cartopy is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Lesser General Public License for more details.
#
# You should have received a copy of the GNU Lesser General Public License
# along with cartopy.  If not, see <http://www.gnu.org/licenses/>.


"""
The Shuttle Radar Topography Mission (SRTM) is an international research
effort that obtained digital elevation models on a near-global scale from
56S to 60N, to generate the most complete high-resolution digital topographic
database of Earth prior to the release of the ASTER GDEM in 2009.

   - Wikipedia (August 2012)

"""
import json
import os

import numpy as np

from cartopy import config
import cartopy.crs as ccrs
from cartopy.io import fh_getter, Downloader


def srtm(lon, lat):
    """
    Return (elevation, crs, extent) for the given longitude latitude.
    Elevation is in meters.
    """
    fname = SRTM3_retrieve(lon, lat)
    if fname is None:
        raise ValueError('No srtm tile found for those coordinates.')
    return read_SRTM3(fname)


def add_shading(elevation, azimuth, altitude):
    """Adds shading to SRTM elevation data, using azimuth and altitude
    of the sun.

    :type elevation: numpy.ndarray
    :param elevation: SRTM elevation data (in meters)
    :type azimuth: float
    :param azimuth: azimuth of the Sun (in degrees)
    :type altitude: float
    :param altitude: altitude of the Sun (in degrees)

    :rtype: numpy.ndarray
    :return: shaded SRTM relief map.
    """
    azimuth = np.deg2rad(azimuth)
    altitude = np.deg2rad(altitude)
    x, y = np.gradient(elevation)
    slope = np.pi/2. - np.arctan(np.sqrt(x*x + y*y))
    # -x here because of pixel orders in the SRTM tile
    aspect = np.arctan2(-x, y)
    shaded = np.sin(altitude) * np.sin(slope)\
        + np.cos(altitude) * np.cos(slope)\
        * np.cos((azimuth - np.pi/2.) - aspect)
    return shaded


def fill_gaps(elevation, max_distance=10):
    """Fills gaps in SRTM elevation data for which the distance from
    missing pixel to nearest existing one is smaller than `max_distance`.

    This function requires osgeo/gdal to work.

    :type elevation: numpy.ndarray
    :param elevation: SRTM elevation data (in meters)
    :type max_distance: int
    :param max_distance: maximal distance (in pixels) between a missing point
    and the nearest valid one.

    :rtype: numpy.ndarray
    :return: SRTM elevation data with filled gaps..
    """
    # Lazily import osgeo - it is only an optional dependency for cartopy.
    from osgeo import gdal
    from osgeo import gdal_array

    src_ds = gdal_array.OpenArray(elevation)
    srcband = src_ds.GetRasterBand(1)
    dstband = srcband
    maskband = srcband
    smoothing_iterations = 0
    options = []
    gdal.FillNodata(dstband, maskband,
                    max_distance, smoothing_iterations, options,
                    callback=None)
    elevation = dstband.ReadAsArray()
    return elevation


def srtm_composite(lon_min, lat_min, nx, ny):

    # XXX nx and ny have got confused in the code (numpy array ordering?).
    # However, the interface works well.

    bottom_left_ll = (lon_min, lat_min)
    shape = np.array([1201, 1201])
    img = np.empty(shape * (nx, ny))

    for i in range(nx):
        for j in range(ny):
            x_img_slice = slice(i * shape[0], (i + 1) * shape[0])
            y_img_slice = slice(j * shape[1], (j + 1) * shape[1])

            tile_img, crs, extent = srtm(bottom_left_ll[0] + j,
                                         bottom_left_ll[1] + i)
            img[x_img_slice, y_img_slice] = tile_img

    extent = (bottom_left_ll[0], bottom_left_ll[0] + ny,
              bottom_left_ll[1], bottom_left_ll[1] + nx)

    return img, crs, extent


def read_SRTM3(fh):
    fh, fname = fh_getter(fh, needs_filename=True)
    if fname.endswith('.zip'):
        from zipfile import ZipFile
        zfh = ZipFile(fh, 'r')
        fh = zfh.open(os.path.basename(fname[:-4]), 'r')

    elev = np.fromfile(fh, dtype=np.dtype('>i2'))
    elev.shape = (1201, 1201)

    fname = os.path.basename(fname)
    y_dir, y, x_dir, x = fname[0], int(fname[1:3]), fname[3], int(fname[4:7])

    if y_dir == 'S':
        y *= -1

    if x_dir == 'W':
        x *= -1

    # xxx extent may need to be wider by half a pixel
    return elev[::-1, ...], ccrs.PlateCarree(), [x, x + 1, y, y + 1]


def SRTM3_retrieve(lon, lat):
    x = '%s%03d' % ('E' if lon > 0 else 'W', abs(int(lon)))
    y = '%s%02d' % ('N' if lat > 0 else 'S', abs(int(lat)))

    srtm_downloader = Downloader.from_config(('SRTM', 'SRTM3'))
    return srtm_downloader.path({'config': config, 'x': x, 'y': y})


class SRTM3Downloader(Downloader):
    """
    Provides a SRTM3 download mechanism.

    """
    FORMAT_KEYS = ('config', 'x', 'y')

    _JSON_SRTM3_LOOKUP = os.path.join(os.path.dirname(__file__),
                                      'srtm.json')
    _SRTM3_LOOKUP_URL = json.load(open(_JSON_SRTM3_LOOKUP, 'r'))
    """
    The SRTM3 url lookup dictionary maps keys such as 'N43E043' to the url
    of the file to download.

    """

    def __init__(self,
                 target_path_template,
                 pre_downloaded_path_template='',
                 ):
        # adds some SRTM3 defaults to the __init__ of a Downloader
        # namely, the URl is determined on the fly using the
        # ``SRTM3Downloader._SRTM3_LOOKUP_URL`` dictionary
        Downloader.__init__(self, None,
                            target_path_template,
                            pre_downloaded_path_template)

    def url(self, format_dict):
        # override the url method, looking up the url from the
        # ``SRTM3Downloader._SRTM3_LOOKUP_URL`` dictionary
        key = u'{y}{x}'.format(**format_dict)
        url = SRTM3Downloader._SRTM3_LOOKUP_URL.get(key, None)
        return url

    def acquire_resource(self, target_path, format_dict):
        import cStringIO as StringIO
        from zipfile import ZipFile

        target_dir = os.path.dirname(target_path)
        if not os.path.isdir(target_dir):
            os.makedirs(target_dir)

        url = self.url(format_dict)

        srtm_online = self._urlopen(url)
        zfh = ZipFile(StringIO.StringIO(srtm_online.read()), 'r')

        zip_member_path = u'{y}{x}.hgt'.format(**format_dict)
        member = zfh.getinfo(zip_member_path)
        with open(target_path, 'wb') as fh:
            fh.write(zfh.open(member).read())

        srtm_online.close()
        zfh.close()

        return target_path

    @staticmethod
    def _create_srtm3_dict():
        """
        Returns a dictionary mapping srtm filename to the URL of the file.

        This is slow as it must query the SRTM server to identify the
        continent from which the tile comes. Hence a json file with this
        content exists in ``SRTM3Downloader._JSON_SRTM3_LOOKUP``.

        The json file was created with::

            import cartopy.io.srtm as srtm
            import json
            fh = open(srtm.SRTM3Downloader._JSON_SRTM3_LOOKUP, 'w')
            json.dump(srtm.SRTM3Downloader._create_srtm3_dict(), fh)

        """
        # lazy imports. In most situations, these are not
        # dependencies of cartopy.
        import urllib
        from BeautifulSoup import BeautifulSoup

        files = {}

        for continent in ['Australia', 'Africa', 'Eurasia', 'Islands',
                          'North_America', 'South_America']:

            url = "http://dds.cr.usgs.gov/srtm/version2_1/SRTM3/%s" % continent
            f = urllib.urlopen(url)
            html = f.read()
            soup = BeautifulSoup(html)

            for link in soup('li'):
                name = str(link.text)
                if name != ' Parent Directory':
                    # remove the '.hgt.zip'
                    files[name[:-8]] = url + '/' + name
            f.close()
        return files

    @classmethod
    def default_downloader(cls):
        """
        Returns a typical downloader for this class. In general, this static
        method is used to create the default configuration in cartopy.config

        """
        default_spec = ('SRTM', 'SRTM3', '{y}{x}.hgt')
        target_path_template = os.path.join('{config[data_dir]}',
                                            *default_spec)
        pre_path_template = os.path.join('{config[pre_existing_data_dir]}',
                                         *default_spec)
        return cls(target_path_template=target_path_template,
                   pre_downloaded_path_template=pre_path_template)


# add a generic SRTM downloader to the config 'downloaders' section.
config['downloaders'].setdefault(('SRTM', 'SRTM3'),
                                 SRTM3Downloader.default_downloader())

########NEW FILE########
__FILENAME__ = clip_path
# (C) British Crown Copyright 2013, Met Office
#
# This file is part of cartopy.
#
# cartopy is free software: you can redistribute it and/or modify it under
# the terms of the GNU Lesser General Public License as published by the
# Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# cartopy is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Lesser General Public License for more details.
#
# You should have received a copy of the GNU Lesser General Public License
# along with cartopy.  If not, see <http://www.gnu.org/licenses/>.
from __future__ import division

import matplotlib.path as mpath
import numpy as np


def clip_path_python(subject, clip, point_inside_clip_path):
    """
    Clip the subject path with the given clip path using the
    Sutherland-Hodgman polygon clipping algorithm.

    Args:

    * subject - The subject path to be clipped. Must be a simple, single
                polygon path with straight line segments only.
    * clip - The clip path to use. Must be a simple, single
             polygon path with straight line segments only.
    * point_inside_clip_path - a point which can be found inside the clip path
                               polygon.

    """
    inside_pt = point_inside_clip_path

    output_verts = subject.vertices

    for i in xrange(clip.vertices.shape[0] - 1):
        clip_edge = clip.vertices[i:i + 2, :]
        input_verts = output_verts
        output_verts = []
        inside = np.cross(clip_edge[1, :] - clip_edge[0, :],
                          inside_pt - clip_edge[0, :])

        try:
            s = input_verts[-1]
        except IndexError:
            break

        for e in input_verts:
            e_clip_cross = np.cross(clip_edge[1, :] - clip_edge[0, :],
                                    e - clip_edge[0, :])
            s_clip_cross = np.cross(clip_edge[1, :] - clip_edge[0, :],
                                    s - clip_edge[0, :])

            if np.sign(e_clip_cross) == np.sign(inside):
                if np.sign(s_clip_cross) != np.sign(inside):
                    p = intersection_point(clip_edge[0, :], clip_edge[1, :],
                                           e, s)
                    output_verts.append(p)
                output_verts.append(e)
            elif np.sign(s_clip_cross) == np.sign(inside):
                p = intersection_point(clip_edge[0, :], clip_edge[1, :],
                                       e, s)
                output_verts.append(p)
            s = e

    if output_verts == []:
        path = mpath.Path([[0, 0]], codes=[mpath.Path.MOVETO])
    else:
        # If the subject polygon was closed, then the return should be too.
        if np.all(subject.vertices[0, :] == subject.vertices[-1, :]):
            output_verts.append(output_verts[0])
        path = mpath.Path(np.array(output_verts))
    return path


def intersection_point(p0, p1, p2, p3):
    """
    Return the intersection point of the two infinite lines that pass through
    point p0->p1 and p2->p3 respectively.

    """
    x_1, y_1 = p0
    x_2, y_2 = p1
    x_3, y_3 = p2
    x_4, y_4 = p3

    div = (x_1 - x_2) * (y_3 - y_4) - (y_1 - y_2) * (x_3 - x_4)

    if div == 0:
        raise ValueError('Lines are parallel and cannot '
                         'intersect at any one point.')

    x = ((x_1 * y_2 - y_1 * x_2) * (x_3 - x_4) - (x_1 - x_2) * (x_3 *
         y_4 - y_3 * x_4)) / div
    y = ((x_1 * y_2 - y_1 * x_2) * (y_3 - y_4) - (y_1 - y_2) * (x_3 *
         y_4 - y_3 * x_4)) / div

    return x, y


# Provide a clip_path function which clips the given path to the given Bbox.
# There is inbuilt mpl functionality with v1.2.1 and beyond, but we provide
# a shim here for older mpl versions.
if hasattr(mpath.Path, 'clip_to_bbox'):
    def clip_path(subject, clip_bbox):
        """
        Clip the given path to the given bounding box.

        """
        return subject.clip_to_bbox(clip_bbox)
else:
    def clip_path(subject, clip_bbox):
        """
        Clip the given path to the given bounding box.

        """
        #A shim on clip_path_python to support Bbox path clipping.

        bbox_patch = bbox_to_path(clip_bbox)
        bbox_center = ((clip_bbox.x0 + clip_bbox.x1) / 2,
                       (clip_bbox.y0 + clip_bbox.y1) / 2)
        return clip_path_python(subject, bbox_patch, bbox_center)


def lines_intersect(p0, p1, p2, p3):
    """
    Return whether the two lines defined by p0->p1 and p2->p3 intersect.
    """
    x_1, y_1 = p0
    x_2, y_2 = p1
    x_3, y_3 = p2
    x_4, y_4 = p3

    return (x_1 - x_2) * (y_3 - y_4) - (y_1 - y_2) * (x_3 - x_4) != 0
    cp1 = np.cross(p1 - p0, p2 - p0)
    cp2 = np.cross(p1 - p0, p3 - p0)
    return np.sign(cp1) == np.sign(cp2) and cp1 != 0


def bbox_to_path(bbox):
    """
    Turn the given :class:`matplotlib.transforms.Bbox` instance into
    a :class:`matplotlib.path.Path` instance.

    """
    verts = np.array([[bbox.x0, bbox.y0], [bbox.x1, bbox.y0],
                      [bbox.x1, bbox.y1], [bbox.x0, bbox.y1],
                      [bbox.x0, bbox.y0]])
    return mpath.Path(verts)

########NEW FILE########
__FILENAME__ = feature_artist
# (C) British Crown Copyright 2011 - 2014, Met Office
#
# This file is part of cartopy.
#
# cartopy is free software: you can redistribute it and/or modify it under
# the terms of the GNU Lesser General Public License as published by the
# Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# cartopy is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Lesser General Public License for more details.
#
# You should have received a copy of the GNU Lesser General Public License
# along with cartopy.  If not, see <http://www.gnu.org/licenses/>.
"""
This module defines the :class:`FeatureArtist` class, for drawing
:class:`Feature` instances with matplotlib.

"""
import warnings
import weakref

import matplotlib.artist
import matplotlib.collections

import cartopy.mpl.patch


class FeatureArtist(matplotlib.artist.Artist):
    """
    A subclass of :class:`~matplotlib.artist.Artist` capable of
    drawing a :class:`cartopy.feature.Feature`.

    """
    _geometry_to_path_cache = weakref.WeakKeyDictionary()
    """
    A nested mapping from geometry and target projection to the
    resulting transformed matplotlib paths::

        {geom: {target_projection: list_of_paths}}

    This provides a significant boost when producing multiple maps of the
    same projection.

    """
    def __init__(self, feature, **kwargs):
        """
        Args:

        * feature:
            an instance of :class:`cartopy.feature.Feature` to draw.
        * kwargs:
            keyword arguments to be used when drawing the feature. These
            will override those shared with the feature.

        """
        super(FeatureArtist, self).__init__()

        if kwargs is None:
            kwargs = {}
        self._kwargs = dict(kwargs)

        # Set default zorder so that features are drawn before
        # lines e.g. contours but after images.
        # Note that the zorder of Patch, PatchCollection and PathCollection
        # are all 1 by default. Assuming equal zorder drawing takes place in
        # the following order: collections, patches, lines (default zorder=2),
        # text (default zorder=3), then other artists e.g. FeatureArtist.
        if self._kwargs.get('zorder') is not None:
            self.set_zorder(self._kwargs['zorder'])
        elif feature.kwargs.get('zorder') is not None:
            self.set_zorder(feature.kwargs['zorder'])
        else:
            # The class attribute matplotlib.collections.PathCollection.zorder
            # was removed after mpl v1.2.0, so the hard-coded value of 1 is
            # used instead.
            self.set_zorder(1)

        self._feature = feature

    @matplotlib.artist.allow_rasterization
    def draw(self, renderer, *args, **kwargs):
        """
        Draws the geometries of the feature that intersect with the extent of
        the :class:`cartopy.mpl.GeoAxes` instance to which this
        object has been added.

        """
        if not self.get_visible():
            return

        ax = self.get_axes()
        feature_crs = self._feature.crs

        # Get geometries that we need to draw.
        extent = None
        try:
            extent = ax.get_extent(feature_crs)
        except ValueError:
            warnings.warn('Unable to determine extent. Defaulting to global.')
        geoms = self._feature.intersecting_geometries(extent)

        # Project (if necessary) and convert geometries to matplotlib paths.
        paths = []
        key = ax.projection
        for geom in geoms:
            mapping = FeatureArtist._geometry_to_path_cache.setdefault(geom,
                                                                       {})
            geom_paths = mapping.get(key)
            if geom_paths is None:
                if ax.projection != feature_crs:
                    projected_geom = ax.projection.project_geometry(
                        geom, feature_crs)
                else:
                    projected_geom = geom
                geom_paths = cartopy.mpl.patch.geos_to_path(
                    projected_geom)
                mapping[key] = geom_paths
            paths.extend(geom_paths)

        # Build path collection and draw it.
        transform = ax.projection._as_mpl_transform(ax)
        # Combine all the keyword args in priority order
        final_kwargs = dict(self._feature.kwargs)
        final_kwargs.update(self._kwargs)
        final_kwargs.update(kwargs)
        c = matplotlib.collections.PathCollection(paths,
                                                  transform=transform,
                                                  **final_kwargs)
        c.set_clip_path(ax.patch)
        c.set_figure(ax.figure)
        return c.draw(renderer)

########NEW FILE########
__FILENAME__ = geoaxes
# (C) British Crown Copyright 2011 - 2014, Met Office
#
# This file is part of cartopy.
#
# cartopy is free software: you can redistribute it and/or modify it under
# the terms of the GNU Lesser General Public License as published by the
# Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# cartopy is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Lesser General Public License for more details.
#
# You should have received a copy of the GNU Lesser General Public License
# along with cartopy.  If not, see <http://www.gnu.org/licenses/>.
"""
This module defines the :class:`GeoAxes` class, for use with matplotlib.

When a matplotlib figure contains a GeoAxes the plotting commands can transform
plot results from source coordinates to the GeoAxes' target projection.

"""
import collections
import contextlib
import warnings
import weakref

import matplotlib.artist
import matplotlib.axes
from matplotlib.image import imread
import matplotlib.transforms as mtransforms
import matplotlib.patches as mpatches
import matplotlib.path as mpath
import numpy as np
import numpy.ma as ma
import shapely.geometry as sgeom

from cartopy import config
import cartopy.crs as ccrs
import cartopy.feature
import cartopy.img_transform
from cartopy.mpl.clip_path import clip_path
import cartopy.mpl.feature_artist as feature_artist
import cartopy.mpl.patch as cpatch
from cartopy.mpl.slippy_image_artist import SlippyImageArtist
from cartopy.vector_transform import vector_scalar_to_grid


assert matplotlib.__version__ >= '1.2', ('Cartopy can only work with '
                                         'matplotlib 1.2 or greater.')


_PATH_TRANSFORM_CACHE = weakref.WeakKeyDictionary()
"""
A nested mapping from path, source CRS, and target projection to the
resulting transformed paths::

    {path: {(source_crs, target_projection): list_of_paths}}

Provides a significant performance boost for contours which, at
matplotlib 1.2.0 called transform_path_non_affine twice unnecessarily.

"""


# XXX call this InterCRSTransform
class InterProjectionTransform(mtransforms.Transform):
    """
    Transforms coordinates from the source_projection to
    the ``target_projection``.

    """
    input_dims = 2
    output_dims = 2
    is_separable = False
    has_inverse = True

    def __init__(self, source_projection, target_projection):
        """
        Create the transform object from the given projections.

        Args:

            * source_projection - A :class:`~cartopy.crs.CRS`.
            * target_projection - A :class:`~cartopy.crs.CRS`.

        """
        # assert target_projection is cartopy.crs.Projection
        # assert source_projection is cartopy.crs.CRS
        self.source_projection = source_projection
        self.target_projection = target_projection
        mtransforms.Transform.__init__(self)

    def __repr__(self):
        return ('< {!s} {!s} -> {!s} >'.format(self.__class__.__name__,
                                               self.source_projection,
                                               self.target_projection))

    def transform_non_affine(self, xy):
        """
        Transforms from source to target coordinates.

        Args:

            * xy - An (n,2) array of points in source coordinates.

        Returns:

            * An (n,2) array of transformed points in target coordinates.

        """
        prj = self.target_projection
        if isinstance(xy, np.ndarray):
            return prj.transform_points(self.source_projection,
                                        xy[:, 0], xy[:, 1])[:, 0:2]
        else:
            x, y = xy
            x, y = prj.transform_point(x, y, self.source_projection)
            return x, y

    def transform_path_non_affine(self, src_path):
        """
        Transforms from source to target coordinates.

        Caches results, so subsequent calls with the same *src_path* argument
        (and the same source and target projections) are faster.

        Args:

            * src_path - A matplotlib :class:`~matplotlib.path.Path` object
                         with vertices in source coordinates.

        Returns

            * A matplotlib :class:`~matplotlib.path.Path` with vertices
              in target coordinates.

        """
        mapping = _PATH_TRANSFORM_CACHE.get(src_path)
        if mapping is not None:
            key = (self.source_projection, self.target_projection)
            result = mapping.get(key)
            if result is not None:
                return result

        # Allow the vertices to be quickly transformed, if
        # quick_vertices_transform allows it.
        new_vertices = self.target_projection.quick_vertices_transform(
            src_path.vertices, self.source_projection)
        if new_vertices is not None:
            if new_vertices is src_path.vertices:
                return src_path
            else:
                return mpath.Path(new_vertices, src_path.codes)

        if src_path.vertices.shape == (1, 2):
            return mpath.Path(self.transform(src_path.vertices))

        transformed_geoms = []
        # Check whether this transform has the "force_path_ccw" attribute set.
        # This is a cartopy extension to the Transform API to allow finer
        # control of Path orientation handling (Path ordering is not important
        # in matplotlib, but is in Cartopy).
        geoms = cpatch.path_to_geos(src_path,
                                    getattr(self, 'force_path_ccw', False))

        for geom in geoms:
            proj_geom = self.target_projection.project_geometry(
                geom, self.source_projection)
            transformed_geoms.append(proj_geom)

        if not transformed_geoms:
            result = mpath.Path(np.empty([0, 2]))
        else:
            paths = cpatch.geos_to_path(transformed_geoms)
            if not paths:
                return mpath.Path(np.empty([0, 2]))
            points, codes = zip(*[cpatch.path_segments(path, curves=False,
                                                       simplify=False)
                                  for path in paths])
            result = mpath.Path(np.concatenate(points, 0),
                                np.concatenate(codes))

        # store the result in the cache for future performance boosts
        key = (self.source_projection, self.target_projection)
        if mapping is None:
            _PATH_TRANSFORM_CACHE[src_path] = {key: result}
        else:
            mapping[key] = result

        return result

    def inverted(self):
        """
        Return a matplotlib :class:`~matplotlib.transforms.Transform`
        from target to source coordinates.

        """
        return InterProjectionTransform(self.target_projection,
                                        self.source_projection)


class GeoAxes(matplotlib.axes.Axes):
    """
    A subclass of :class:`matplotlib.axes.Axes` which represents a
    map :class:`~cartopy.crs.Projection`.

    This class replaces the matplotlib :class:`~matplotlib.axes.Axes` class
    when created with the *projection* keyword. For example::

        # Set up a standard map for latlon data.
        geo_axes = pyplot.axes(projection=cartopy.crs.PlateCarree())

        # Set up an OSGB map.
        geo_axes = pyplot.subplot(2, 2, 1, projection=cartopy.crs.OSGB())

    When a source projection is provided to one of it's plotting methods,
    using the *transform* keyword, the standard matplotlib plot result is
    transformed from source coordinates to the target projection. For example::

        # Plot latlon data on an OSGB map.
        pyplot.axes(projection=cartopy.crs.OSGB())
        pyplot.contourf(x, y, data, transform=cartopy.crs.PlateCarree())

    """
    def __init__(self, *args, **kwargs):
        """
        Create a GeoAxes object using standard matplotlib
        :class:`~matplotlib.axes.Axes` args and kwargs.

        Kwargs:

            * map_projection - The target :class:`~cartopy.crs.Projection` of
                               this Axes object.

        All other args and keywords are passed through to
        :class:`matplotlib.axes.Axes`.

        """
        self.projection = kwargs.pop('map_projection')
        """The :class:`cartopy.crs.Projection` of this GeoAxes."""

        self.outline_patch = None
        """The patch that provides the line bordering the projection."""

        self.background_patch = None
        """The patch that provides the filled background of the projection."""

        super(GeoAxes, self).__init__(*args, **kwargs)
        self._gridliners = []
        self.img_factories = []
        self._done_img_factory = False

    def add_image(self, factory, *args, **kwargs):
        """
        Adds an image "factory" to the Axes.

        Any image "factory" added, will be asked to retrieve an image
        with associated metadata for a given bounding box at draw time.
        The advantage of this approach is that the limits of the map
        do not need to be known when adding the image factory, but can
        be deferred until everything which can effect the limits has been
        added.

        Currently an image "factory" is just an object with
        a ``image_for_domain`` method. Examples of image factories
        are :class:`cartopy.io.img_nest.NestedImageCollection` and
        :class:`cartopy.io.image_tiles.GoogleTiles`.

        """
        if hasattr(factory, 'image_for_domain'):
            # XXX TODO: Needs deprecating.
            self.img_factories.append([factory, args, kwargs])
        else:
            # Args and kwargs not allowed.
            assert not bool(args) and not bool(kwargs)
            image = factory
            try:
                super(GeoAxes, self).add_image(image)
            except AttributeError:
                # If add_image method doesn't exist (only available from
                # v1.4 onwards) we implement it ourselves.
                self._set_artist_props(image)
                self.images.append(image)
                image._remove_method = lambda h: self.images.remove(h)
            return image

    @contextlib.contextmanager
    def hold_limits(self, hold=True):
        """
        Keep track of the original view and data limits for the life of this
        context manager, optionally reverting any changes back to the original
        values after the manager exits.

        Parameters
        ----------
        hold : bool (default True)
            Whether to revert the data and view limits after the context
            manager exits.

        """
        data_lim = self.dataLim.frozen().get_points()
        view_lim = self.viewLim.frozen().get_points()
        other = (self.ignore_existing_data_limits,
                 self._autoscaleXon, self._autoscaleYon)
        try:
            yield
        finally:
            if hold:
                self.dataLim.set_points(data_lim)
                self.viewLim.set_points(view_lim)
                (self.ignore_existing_data_limits,
                    self._autoscaleXon, self._autoscaleYon) = other

    @matplotlib.artist.allow_rasterization
    def draw(self, renderer=None, inframe=False):
        """
        Extends the standard behaviour of :func:`matplotlib.axes.Axes.draw`.

        Draws grid lines and image factory results before invoking standard
        matplotlib drawing. A global range is used if no limits have yet
        been set.

        """
        # If data has been added (i.e. autoscale hasn't been turned off)
        # then we should autoscale the view.
        if self.get_autoscale_on() and self.ignore_existing_data_limits:
            self.autoscale_view()

        if self.outline_patch.reclip or self.background_patch.reclip:
            clipped_path = clip_path(self.outline_patch.orig_path,
                                     self.viewLim)
            self.outline_patch._path = clipped_path
            self.background_patch._path = clipped_path

        for gl in self._gridliners:
            gl._draw_gridliner(background_patch=self.background_patch)
        self._gridliners = []

        # XXX This interface needs a tidy up:
        #       image drawing on pan/zoom;
        #       caching the resulting image;
        #       buffering the result by 10%...;
        if not self._done_img_factory:
            for factory, args, kwargs in self.img_factories:
                img, extent, origin = factory.image_for_domain(
                    self._get_extent_geom(factory.crs), args[0])
                self.imshow(img, extent=extent, origin=origin,
                            transform=factory.crs, *args[1:], **kwargs)
        self._done_img_factory = True

        return matplotlib.axes.Axes.draw(self, renderer=renderer,
                                         inframe=inframe)

    def __str__(self):
        return '< GeoAxes: %s >' % self.projection

    def cla(self):
        """Clears the current axes and adds boundary lines."""
        result = matplotlib.axes.Axes.cla(self)
        self.xaxis.set_visible(False)
        self.yaxis.set_visible(False)
        # Enable tight autoscaling.
        self._tight = True
        self.set_aspect('equal')

        with self.hold_limits():
            self._boundary()

        # XXX consider a margin - but only when the map is not global...
        # self._xmargin = 0.15
        # self._ymargin = 0.15

        self.dataLim.intervalx = self.projection.x_limits
        self.dataLim.intervaly = self.projection.y_limits

        return result

    def format_coord(self, x, y):
        """Return a string formatted for the matplotlib GUI status bar."""
        lon, lat = ccrs.Geodetic().transform_point(x, y, self.projection)

        ns = 'N' if lat >= 0.0 else 'S'
        ew = 'E' if lon >= 0.0 else 'W'

        return u'%.4g, %.4g (%f\u00b0%s, %f\u00b0%s)' % (x, y, abs(lat),
                                                         ns, abs(lon), ew)

    def coastlines(self, resolution='110m', color='black', **kwargs):
        """
        Adds coastal **outlines** to the current axes from the Natural Earth
        "coastline" shapefile collection.

        Kwargs:

            * resolution - a named resolution to use from the Natural Earth
                           dataset. Currently can be one of "110m", "50m", and
                           "10m".

        .. note::

            Currently no clipping is done on the coastlines before adding
            them to the axes. This means, if very high resolution coastlines
            are being used, performance is likely to be severely effected.
            This should be resolved transparently by v0.5.

        """
        kwargs['edgecolor'] = color
        kwargs['facecolor'] = 'none'
        feature = cartopy.feature.NaturalEarthFeature('physical', 'coastline',
                                                      resolution, **kwargs)
        return self.add_feature(feature)

    def natural_earth_shp(self, name='land', resolution='110m',
                          category='physical', **kwargs):
        """
        Adds the geometries from the specified Natural Earth shapefile to the
        Axes as a :class:`~matplotlib.collections.PathCollection`.

        ``**kwargs`` are passed through to the
        :class:`~matplotlib.collections.PathCollection` constructor.

        Returns the created :class:`~matplotlib.collections.PathCollection`.

        .. note::

            Currently no clipping is done on the geometries before adding them
            to the axes. This means, if very high resolution geometries are
            being used, performance is likely to be severely effected. This
            should be resolved transparently by v0.5.

        """
        warnings.warn('This method has been deprecated.'
                      ' Please use `add_feature` instead.')
        kwargs.setdefault('edgecolor', 'face')
        kwargs.setdefault('facecolor', cartopy.feature.COLORS['land'])
        feature = cartopy.feature.NaturalEarthFeature(category, name,
                                                      resolution, **kwargs)
        return self.add_feature(feature)

    def add_feature(self, feature, **kwargs):
        """
        Adds the given :class:`~cartopy.feature.Feature` instance to the axes.

        Args:

        * feature:
            An instance of :class:`~cartopy.feature.Feature`.

        Kwargs:
            Keyword arguments to be used when drawing the feature. This allows
            standard matplotlib control over aspects such as 'facecolor',
            'alpha', etc.

        Returns:
            * A :class:`cartopy.mpl.feature_artist.FeatureArtist`
              instance responsible for drawing the feature.

        """
        # Instantiate an artist to draw the feature and add it to the axes.
        artist = feature_artist.FeatureArtist(feature, **kwargs)
        return self.add_artist(artist)

    def add_geometries(self, geoms, crs, **kwargs):
        """
        Add the given shapely geometries (in the given crs) to the axes.

        Args:

        * geoms:
            A collection of shapely geometries.
        * crs:
            The cartopy CRS in which the provided geometries are defined.

        Kwargs:
            Keyword arguments to be used when drawing this feature.

        Returns:
             * A :class:`cartopy.mpl.feature_artist.FeatureArtist`
               instance responsible for drawing the geometries.

        """
        feature = cartopy.feature.ShapelyFeature(geoms, crs, **kwargs)
        return self.add_feature(feature)

    def get_extent(self, crs=None):
        """
        Get the extent (x0, x1, y0, y1) of the map in the given coordinate
        system.

        If no crs is given, the returned extents' coordinate system will be
        the CRS of this Axes.

        """
        p = self._get_extent_geom(crs)
        r = p.bounds
        x1, y1, x2, y2 = r
        return x1, x2, y1, y2

    def _get_extent_geom(self, crs=None):
        # Perform the calculations for get_extent(), which just repackages it.
        with self.hold_limits():
            if self.get_autoscale_on():
                self.autoscale_view()
            [x1, y1], [x2, y2] = self.viewLim.get_points()

        domain_in_src_proj = sgeom.Polygon([[x1, y1], [x2, y1],
                                            [x2, y2], [x1, y2],
                                            [x1, y1]])

        # Determine target projection based on requested CRS.
        if crs is None:
            proj = self.projection
        elif isinstance(crs, ccrs.Projection):
            proj = crs
        else:
            # Attempt to select suitable projection for
            # non-projection CRS.
            if isinstance(crs, ccrs.RotatedGeodetic):
                proj = ccrs.RotatedPole(crs.proj4_params['lon_0'] - 180,
                                        crs.proj4_params['o_lat_p'])
                warnings.warn('Approximating coordinate system {!r} with a '
                              'RotatedPole projection.'.format(crs))
            elif hasattr(crs, 'is_geodetic') and crs.is_geodetic():
                proj = ccrs.PlateCarree(crs.globe)
                warnings.warn('Approximating coordinate system {!r} with the '
                              'PlateCarree projection.'.format(crs))
            else:
                raise ValueError('Cannot determine extent in'
                                 ' coordinate system {!r}'.format(crs))

        # Calculate intersection with boundary and project if necesary.
        boundary_poly = sgeom.Polygon(self.projection.boundary)
        if proj != self.projection:
            # Erode boundary by threshold to avoid transform issues.
            # This is a workaround for numerical issues at the boundary.
            eroded_boundary = boundary_poly.buffer(-self.projection.threshold)
            geom_in_src_proj = eroded_boundary.intersection(
                domain_in_src_proj)
            geom_in_crs = proj.project_geometry(geom_in_src_proj,
                                                self.projection)
        else:
            geom_in_crs = boundary_poly.intersection(domain_in_src_proj)

        return geom_in_crs

    def set_extent(self, extents, crs=None):
        """
        Set the extent (x0, x1, y0, y1) of the map in the given
        coordinate system.

        If no crs is given, the extents' coordinate system will be assumed
        to be the Geodetic version of this axes' projection.

        """
        # TODO: Implement the same semantics as plt.xlim and
        # plt.ylim - allowing users to set None for a minimum and/or
        # maximum value
        x1, x2, y1, y2 = extents
        domain_in_crs = sgeom.polygon.LineString([[x1, y1], [x2, y1],
                                                  [x2, y2], [x1, y2],
                                                  [x1, y1]])

        projected = None

        # Sometimes numerical issues cause the projected vertices of the
        # requested extents to appear outside the projection domain.
        # This results in an empty geometry, which has an empty `bounds`
        # tuple, which causes an unpack error.
        # This workaround avoids using the projection when the requested
        # extents are obviously the same as the projection domain.
        try_workaround = ((crs is None and
                           isinstance(self.projection, ccrs.PlateCarree)) or
                          crs == self.projection)
        if try_workaround:
            boundary = self.projection.boundary
            if boundary.equals(domain_in_crs):
                projected = boundary

        if projected is None:
            projected = self.projection.project_geometry(domain_in_crs, crs)
        x1, y1, x2, y2 = projected.bounds
        self.set_xlim([x1, x2])
        self.set_ylim([y1, y2])

    def set_global(self):
        """
        Set the extent of the Axes to the limits of the projection.

        .. note::

            In some cases where the projection has a limited sensible range
            the ``set_global`` method does not actually make the whole globe
            visible. Instead, the most appropriate extents will be used (e.g.
            Ordnance Survey UK will set the extents to be around the British
            Isles.

        """
        self.set_xlim(self.projection.x_limits)
        self.set_ylim(self.projection.y_limits)

    def set_xticks(self, ticks, minor=False, crs=None):
        """
        Set the x ticks.

        Args:

            * ticks - list of floats denoting the desired position of x ticks.

        Kwargs:

            * minor - boolean flag indicating whether the ticks should be minor
                      ticks i.e. small and unlabelled (default is False).

            * crs - An instance of :class:`~cartopy.crs.CRS` indicating the
                    coordinate system of the provided tick values. If no
                    coordinate system is specified then the values are assumed
                    to be in the coordinate system of the projection.
                    Only transformations from one rectangular coordinate system
                    to another rectangular coordinate system are supported.

        .. note::

            This interface is subject to change whilst functionality is added
            to support other map projections.

        """
        # Project ticks if crs differs from axes' projection
        if crs is not None and crs != self.projection:
            if not isinstance(crs, (ccrs._RectangularProjection,
                                    ccrs.Mercator)) or \
                    not isinstance(self.projection,
                                   (ccrs._RectangularProjection,
                                    ccrs.Mercator)):
                raise RuntimeError('Cannot handle non-rectangular coordinate '
                                   'systems.')
            proj_xyz = self.projection.transform_points(crs,
                                                        np.asarray(ticks),
                                                        np.zeros(len(ticks)))
            xticks = proj_xyz[..., 0]
        else:
            xticks = ticks

        # Switch on drawing of x axis
        self.xaxis.set_visible(True)

        return super(GeoAxes, self).set_xticks(xticks, minor)

    def set_yticks(self, ticks, minor=False, crs=None):
        """
        Set the y ticks.

        Args:

            * ticks - list of floats denoting the desired position of y ticks.

        Kwargs:

            * minor - boolean flag indicating whether the ticks should be minor
                      ticks i.e. small and unlabelled (default is False).

            * crs - An instance of :class:`~cartopy.crs.CRS` indicating the
                    coordinate system of the provided tick values. If no
                    coordinate system is specified then the values are assumed
                    to be in the coordinate system of the projection.
                    Only transformations from one rectangular coordinate system
                    to another rectangular coordinate system are supported.

        .. note::

            This interface is subject to change whilst functionality is added
            to support other map projections.

        """
        # Project ticks if crs differs from axes' projection
        if crs is not None and crs != self.projection:
            if not isinstance(crs, (ccrs._RectangularProjection,
                                    ccrs.Mercator)) or \
                    not isinstance(self.projection,
                                   (ccrs._RectangularProjection,
                                    ccrs.Mercator)):
                raise RuntimeError('Cannot handle non-rectangular coordinate '
                                   'systems.')
            proj_xyz = self.projection.transform_points(crs,
                                                        np.zeros(len(ticks)),
                                                        np.asarray(ticks))
            yticks = proj_xyz[..., 1]
        else:
            yticks = ticks

        # Switch on drawing of y axis
        self.yaxis.set_visible(True)

        return super(GeoAxes, self).set_yticks(yticks, minor)

    def stock_img(self, name='ne_shaded'):
        """
        Add a standard image to the map.

        Currently, the only (and default) option is a downsampled version of
        the Natural Earth shaded relief raster.

        """
        if name == 'ne_shaded':
            import os
            source_proj = ccrs.PlateCarree()
            fname = os.path.join(config["repo_data_dir"],
                                 'raster', 'natural_earth',
                                 '50-natural-earth-1-downsampled.png')

            return self.imshow(imread(fname), origin='upper',
                               transform=source_proj,
                               extent=[-180, 180, -90, 90])
        else:
            raise ValueError('Unknown stock image %r.' % name)

    def add_raster(self, raster_source, **slippy_image_kwargs):
        """
        Add the given raster source to the GeoAxes.

        Parameters
        ----------
        raster_source : :class:`cartopy.io.RasterSource` like instance
            ``raster_source`` may be any object which implements the
            RasterSource interface, including instances of objects such as
            :class:`~cartopy.io.ogc_clients.WMSRasterSource` and
            :class:`~cartopy.io.ogc_clients.WMTSRasterSource`. Note that image
            retrievals are done at draw time, not at creation time.

        """
        # Allow a fail-fast error if the raster source cannot provide
        # images in the current projection.
        raster_source.validate_projection(self.projection)
        img = SlippyImageArtist(self, raster_source, **slippy_image_kwargs)
        with self.hold_limits():
            self.add_image(img)
        return img

    def _regrid_shape_aspect(self, regrid_shape, target_extent):
        """
        Helper for setting regridding shape which is used in several
        plotting methods.

        """
        if not isinstance(regrid_shape, collections.Sequence):
            target_size = int(regrid_shape)
            x_range, y_range = np.diff(target_extent)[::2]
            desired_aspect = x_range / y_range
            if x_range >= y_range:
                regrid_shape = (target_size * desired_aspect, target_size)
            else:
                regrid_shape = (target_size, target_size / desired_aspect)
        return regrid_shape

    def imshow(self, img, *args, **kwargs):
        """
        Add the "transform" keyword to :func:`~matplotlib.pyplot.imshow'.

        Parameters
        ----------

        transform : :class:`~cartopy.crs.Projection` or matplotlib transform
            The coordinate system in which the given image is rectangular.
        regrid_shape : int or pair of ints
            The shape of the desired image if it needs to be transformed.
            If a single integer is given then that will be used as the minimum
            length dimension, while the other dimension will be scaled up
            according to the target extent's aspect ratio. The default is for
            the minimum dimension of a transformed image to have length 750,
            so for an image being transformed into a global PlateCarree
            projection the resulting transformed image would have a shape of
            ``(750, 1500)``.
        extent : tuple
            The corner coordinates of the image in the form
            ``(left, right, bottom, top)``. The coordinates should be in the
            coordinate system passed to the transform keyword.
        target_extent : tuple
            The corner coordinate of the desired image in the form
            ``(left, right, bottom, top)``. The coordinates should be in the
            coordinate system passed to the transform keyword.
        origin : {'lower', 'upper'}
            The origin of the vertical pixels. See
            :func:`matplotlib.pyplot.imshow` for further details. Default
            is ``'lower'``.

        """
        transform = kwargs.pop('transform', None)
        if 'update_datalim' in kwargs:
            raise ValueError('The update_datalim keyword has been removed in '
                             'imshow. To hold the data and view limits see '
                             'GeoAxes.hold_limits.')

        kwargs.setdefault('origin', 'lower')

        same_projection = (isinstance(transform, ccrs.Projection) and
                           self.projection == transform)

        if transform is None or transform == self.transData or same_projection:
            if isinstance(transform, ccrs.Projection):
                transform = transform._as_mpl_transform(self)
            result = matplotlib.axes.Axes.imshow(self, img, *args, **kwargs)
        else:
            extent = kwargs.pop('extent', None)
            img = np.asanyarray(img)
            if kwargs['origin'] == 'upper':
                # It is implicitly assumed by the regridding operation that the
                # origin of the image is 'lower', so simply adjust for that
                # here.
                img = img[::-1]
                kwargs['origin'] = 'lower'

            if not isinstance(transform, ccrs.Projection):
                raise ValueError('Expected a projection subclass. Cannot '
                                 'handle a %s in imshow.' % type(transform))

            target_extent = self.get_extent(self.projection)
            regrid_shape = kwargs.pop('regrid_shape', 750)
            regrid_shape = self._regrid_shape_aspect(regrid_shape,
                                                     target_extent)
            warp_array = cartopy.img_transform.warp_array
            img, extent = warp_array(img,
                                     source_proj=transform,
                                     source_extent=extent,
                                     target_proj=self.projection,
                                     target_res=regrid_shape,
                                     target_extent=target_extent,
                                     mask_extrapolated=True,
                                     )

            # As a workaround to a matplotlib limitation, turn any images
            # which are RGB with a mask into RGBA images with an alpha
            # channel.
            if (isinstance(img, np.ma.MaskedArray) and
                    img.shape[2:3] == (3, ) and
                    img.mask is not False):
                old_img = img
                img = np.zeros(img.shape[:2] + (4, ), dtype=img.dtype)
                img[:, :, 0:3] = old_img
                # Put an alpha channel in if the image was masked.
                img[:, :, 3] = ~ np.any(old_img.mask, axis=2)
                if img.dtype.kind == 'u':
                    img[:, :, 3] *= 255

            result = matplotlib.axes.Axes.imshow(self, img, *args,
                                                 extent=extent, **kwargs)

        # clip the image. This does not work as the patch moves with mouse
        # movement, but the clip path doesn't
        # This could definitely be fixed in matplotlib
#        if result.get_clip_path() in [None, self.patch]:
#            # image does not already have clipping set, clip to axes patch
#            result.set_clip_path(self.outline_patch)
        return result

    def gridlines(self, crs=None, draw_labels=False, **kwargs):
        """
        Automatically adds gridlines to the axes, in the given coordinate
        system, at draw time.

        Kwargs:

        * crs
            The :class:`cartopy._crs.CRS` defining the coordinate system in
            which gridlines are drawn.
            Default is :class:`cartopy.crs.PlateCarree`.

        * draw_labels
            Label gridlines like axis ticks, around the edge.

        Returns:

            A :class:`cartopy.mpl.gridliner.Gridliner` instance.

        All other keywords control line properties.  These are passed through
        to :class:`matplotlib.collections.Collection`.

        """
        if crs is None:
            crs = ccrs.PlateCarree()
        from cartopy.mpl.gridliner import Gridliner
        gl = Gridliner(
            self, crs=crs, draw_labels=draw_labels, collection_kwargs=kwargs)
        self._gridliners.append(gl)
        return gl

    def _gen_axes_spines(self, locations=None, offset=0.0, units='inches'):
        # generate some axes spines, as some Axes super class machinery
        # requires them. Just make them invisible
        spines = matplotlib.axes.Axes._gen_axes_spines(self,
                                                       locations=locations,
                                                       offset=offset,
                                                       units=units)
        for spine in spines.itervalues():
            spine.set_visible(False)
        return spines

    def _boundary(self):
        """
        Adds the map's boundary to this GeoAxes, attaching the appropriate
        artists to :data:`.outline_patch` and :data:`.background_patch`.

        .. note::

            The boundary is not the ``axes.patch``. ``axes.patch``
            is made invisible by this method - its only remaining
            purpose is to provide a rectilinear clip patch for
            all Axes artists.

        """
        path, = cpatch.geos_to_path(self.projection.boundary)

        # Get the outline path in terms of self.transData
        proj_to_data = self.projection._as_mpl_transform(self) - self.transData
        tp = proj_to_data.transform_path(path)

        outline_patch = mpatches.PathPatch(tp,
                                           facecolor='none', edgecolor='k',
                                           zorder=2.5, clip_on=False,
                                           transform=self.transData)

        background_patch = mpatches.PathPatch(tp,
                                              facecolor='w', edgecolor='none',
                                              zorder=-1, clip_on=False,
                                              transform=self.transData)

        # Attach the original path to the patches. This will be used each time
        # a new clipped path is calculated.
        outline_patch.orig_path = tp
        background_patch.orig_path = tp

        # Attach a "reclip" attribute, which determines if the patch's path is
        # reclipped before drawing. A callback is used to change the "reclip"
        # state.
        outline_patch.reclip = False
        background_patch.reclip = False

        # Add the patches to the axes, and also make them available as
        # attributes.
        self.add_patch(outline_patch)
        self.outline_patch = outline_patch
        self.add_patch(background_patch)
        self.background_patch = background_patch

        # Attach callback events for when the xlim or ylim are changed. This
        # is what triggers the patches to be re-clipped at draw time.
        self.callbacks.connect('xlim_changed', _trigger_patch_reclip)
        self.callbacks.connect('ylim_changed', _trigger_patch_reclip)

        # Hide the old "background" patch. It is not used by GeoAxes.
        self.patch.set_facecolor((1, 1, 1, 0))
        self.patch.set_edgecolor((0.5, 0.5, 0.5))
        self.patch.set_visible(False)

    def contour(self, *args, **kwargs):
        """
        Add the "transform" keyword to :func:`~matplotlib.pyplot.contour'.

        Extra kwargs:

            transform - a :class:`~cartopy.crs.Projection`.

        """
        t = kwargs.get('transform', None)
        if t is None:
            t = self.projection
        if isinstance(t, ccrs.CRS) and not isinstance(t, ccrs.Projection):
            raise ValueError('invalid transform:'
                             ' Spherical contouring is not supported - '
                             ' consider using PlateCarree/RotatedPole.')
        if isinstance(t, ccrs.Projection):
            kwargs['transform'] = t._as_mpl_transform(self)
        else:
            kwargs['transform'] = t
        result = matplotlib.axes.Axes.contour(self, *args, **kwargs)
        self.autoscale_view()
        return result

    def contourf(self, *args, **kwargs):
        """
        Add the "transform" keyword to :func:`~matplotlib.pyplot.contourf'.

        Extra kwargs:

            transform - a :class:`~cartopy.crs.Projection`.

        """
        t = kwargs.get('transform', None)
        if t is None:
            t = self.projection
        if isinstance(t, ccrs.CRS) and not isinstance(t, ccrs.Projection):
            raise ValueError('invalid transform:'
                             ' Spherical contouring is not supported - '
                             ' consider using PlateCarree/RotatedPole.')
        if isinstance(t, ccrs.Projection):
            kwargs['transform'] = t = t._as_mpl_transform(self)
        else:
            kwargs['transform'] = t

        # Set flag to indicate correcting orientation of paths if not ccw
        if isinstance(t, mtransforms.Transform):
            for sub_trans, _ in t._iter_break_from_left_to_right():
                if isinstance(sub_trans, InterProjectionTransform):
                    if not hasattr(sub_trans, 'force_path_ccw'):
                        sub_trans.force_path_ccw = True

        result = matplotlib.axes.Axes.contourf(self, *args, **kwargs)
        self.autoscale_view()
        return result

    def scatter(self, *args, **kwargs):
        """
        Add the "transform" keyword to :func:`~matplotlib.pyplot.scatter'.

        Extra kwargs:

            transform - a :class:`~cartopy.crs.Projection`.

        """
        t = kwargs.get('transform', None)
        # Keep this bit - even at mpl v1.2
        if t is None:
            t = self.projection
        if hasattr(t, '_as_mpl_transform'):
            kwargs['transform'] = t._as_mpl_transform(self)

        # exclude Geodetic as a vaild source CS
        if (isinstance(kwargs.get('transform', None),
                       InterProjectionTransform) and
                kwargs['transform'].source_projection.is_geodetic()):
            raise ValueError('Cartopy cannot currently do spherical '
                             'contouring. The source CRS cannot be a '
                             'geodetic, consider using the cyllindrical form '
                             '(PlateCarree or RotatedPole).')

        result = matplotlib.axes.Axes.scatter(self, *args, **kwargs)
        self.autoscale_view()
        return result

    def pcolormesh(self, *args, **kwargs):
        """
        Add the "transform" keyword to :func:`~matplotlib.pyplot.pcolormesh'.

        Extra kwargs:

            transform - a :class:`~cartopy.crs.Projection`.

        """
        t = kwargs.get('transform', None)
        if t is None:
            t = self.projection
        if isinstance(t, ccrs.CRS) and not isinstance(t, ccrs.Projection):
            raise ValueError('invalid transform:'
                             ' Spherical pcolormesh is not supported - '
                             ' consider using PlateCarree/RotatedPole.')
        kwargs.setdefault('transform', t)
        result = self._pcolormesh_patched(*args, **kwargs)
        self.autoscale_view()
        return result

    # mpl 1.2.0rc2 compatibility. To be removed once 1.2 is released
    def _pcolormesh_patched(self, *args, **kwargs):
        """
        A temporary, modified duplicate of
        :func:`~matplotlib.pyplot.pcolormesh'.

        This function contains a workaround for a matplotlib issue
        and will be removed once the issue has been resolved.
        https://github.com/matplotlib/matplotlib/pull/1314

        """
        import warnings
        import numpy as np
        import numpy.ma as ma
        import matplotlib as mpl
        import matplotlib.cbook as cbook
        import matplotlib.colors as mcolors
        import matplotlib.cm as cm
        from matplotlib import docstring
        import matplotlib.transforms as transforms
        import matplotlib.artist as artist
        from matplotlib.artist import allow_rasterization
        import matplotlib.backend_bases as backend_bases
        import matplotlib.path as mpath
        import matplotlib.mlab as mlab
        import matplotlib.collections as mcoll

        if not self._hold:
            self.cla()

        alpha = kwargs.pop('alpha', None)
        norm = kwargs.pop('norm', None)
        cmap = kwargs.pop('cmap', None)
        vmin = kwargs.pop('vmin', None)
        vmax = kwargs.pop('vmax', None)
        shading = kwargs.pop('shading', 'flat').lower()
        antialiased = kwargs.pop('antialiased', False)
        kwargs.setdefault('edgecolors', 'None')

        X, Y, C = self._pcolorargs('pcolormesh', *args)
        Ny, Nx = X.shape

        # convert to one dimensional arrays
        if shading != 'gouraud':
            # data point in each cell is value at lower left corner
            C = ma.ravel(C[0:Ny - 1, 0:Nx - 1])
        else:
            C = C.ravel()
        X = X.ravel()
        Y = Y.ravel()

        coords = np.zeros(((Nx * Ny), 2), dtype=float)
        coords[:, 0] = X
        coords[:, 1] = Y

        collection = mcoll.QuadMesh(
            Nx - 1, Ny - 1, coords,
            antialiased=antialiased, shading=shading, **kwargs)
        collection.set_alpha(alpha)
        collection.set_array(C)
        if norm is not None:
            assert(isinstance(norm, mcolors.Normalize))
        collection.set_cmap(cmap)
        collection.set_norm(norm)
        collection.set_clim(vmin, vmax)
        collection.autoscale_None()

        self.grid(False)

        ########################
        # PATCH FOR MPL 1.2.0rc2

        # Transform from native to data coordinates?
        t = collection._transform
        if (not isinstance(t, mtransforms.Transform)
                and hasattr(t, '_as_mpl_transform')):
            t = t._as_mpl_transform(self.axes)

        if t and any(t.contains_branch_seperately(self.transData)):
            trans_to_data = t - self.transData
            pts = np.vstack([X, Y]).T.astype(np.float)
            transformed_pts = trans_to_data.transform(pts)

            X = transformed_pts[..., 0]
            Y = transformed_pts[..., 1]

            # XXX Not a mpl 1.2 thing...
            no_inf = (X != np.inf) & (Y != np.inf)
            X = X[no_inf]
            Y = Y[no_inf]

        # END OF PATCH
        ##############

        minx = np.amin(X)
        maxx = np.amax(X)
        miny = np.amin(Y)
        maxy = np.amax(Y)

        corners = (minx, miny), (maxx, maxy)
        self.update_datalim(corners)
        self.autoscale_view()
        self.add_collection(collection)

        # XXX Non-standard matplotlib 1.2 thing.
        # Handle a possible wrap around for rectangular projections.
        t = kwargs.get('transform', None)
        if isinstance(t, ccrs.CRS):
            wrap_proj_types = (ccrs._RectangularProjection,
                               ccrs._WarpedRectangularProjection,
                               ccrs.InterruptedGoodeHomolosine)
            if isinstance(t, wrap_proj_types) and \
                    isinstance(self.projection, wrap_proj_types):

                C = C.reshape((Ny - 1, Nx - 1))
                transformed_pts = transformed_pts.reshape((Ny, Nx, 2))

                # compute the vertical line angles of the pcolor in
                # transformed coordinates
                with np.errstate(invalid='ignore'):
                    horizontal_vert_angles = np.arctan2(
                        np.diff(transformed_pts[..., 0], axis=1),
                        np.diff(transformed_pts[..., 1], axis=1)
                    )

                # if the change in angle is greater than 90 degrees (absolute),
                # then mark it for masking later on.
                dx_horizontal = np.diff(horizontal_vert_angles)
                to_mask = ((np.abs(dx_horizontal) > np.pi / 2) |
                           np.isnan(dx_horizontal))

                if np.any(to_mask):
                    if collection.get_cmap()._rgba_bad[3] != 0.0:
                        warnings.warn("The colormap's 'bad' has been set, but "
                                      "in order to wrap pcolormesh across the "
                                      "map it must be fully transparent.")

                    # at this point C has a shape of (Ny-1, Nx-1), to_mask has
                    # a shape of (Ny, Nx-2) and pts has a shape of (Ny*Nx, 2)

                    mask = np.zeros(C.shape, dtype=np.bool)

                    # mask out the neighbouring cells if there was a cell
                    # found with an angle change of more than pi/2 . NB.
                    # Masking too much only has a detrimental impact on
                    # performance.
                    to_mask_y_shift = to_mask[:-1, :]
                    mask[:, :-1][to_mask_y_shift] = True
                    mask[:, 1:][to_mask_y_shift] = True

                    to_mask_x_shift = to_mask[1:, :]
                    mask[:, :-1][to_mask_x_shift] = True
                    mask[:, 1:][to_mask_x_shift] = True

                    C_mask = getattr(C, 'mask', None)
                    if C_mask is not None:
                        dmask = mask | C_mask
                    else:
                        dmask = mask

                    # print 'Ratio of masked data: ',
                    # print np.sum(mask) / float(np.product(mask.shape))

                    # create the masked array to be used with this pcolormesh
                    pcolormesh_data = np.ma.array(C, mask=mask)

                    collection.set_array(pcolormesh_data.ravel())

                    # now that the pcolormesh has masked the bad values,
                    # create a pcolor with just those values that were masked
                    pcolor_data = pcolormesh_data.copy()
                    # invert the mask
                    pcolor_data.mask = ~pcolor_data.mask

                    # remember to re-apply the original data mask to the array
                    if C_mask is not None:
                        pcolor_data.mask = pcolor_data.mask | C_mask

                    pts = pts.reshape((Ny, Nx, 2))
                    if np.any(~pcolor_data.mask):
                        # plot with slightly lower zorder to avoid odd issue
                        # where the main plot is obscured
                        zorder = collection.zorder - .1
                        kwargs.pop('zorder', None)
                        kwargs.setdefault('snap', False)
                        pcolor_col = self.pcolor(pts[..., 0], pts[..., 1],
                                                 pcolor_data, zorder=zorder,
                                                 **kwargs)

                        pcolor_col.set_cmap(cmap)
                        pcolor_col.set_norm(norm)
                        pcolor_col.set_clim(vmin, vmax)
                        # scale the data according to the *original* data
                        pcolor_col.norm.autoscale_None(C)

                        # put the pcolor_col on the pcolormesh collection so
                        # that if really necessary, users can do things post
                        # this method
                        collection._wrapped_collection_fix = pcolor_col

            # Clip the QuadMesh to the projection boundary, which is required
            # to keep the shading inside the projection bounds.
            collection.set_clip_path(self.outline_patch)

        return collection

    def pcolor(self, *args, **kwargs):
        """
        Add the "transform" keyword to :func:`~matplotlib.pyplot.pcolor'.

        Extra kwargs:

            transform - a :class:`~cartopy.crs.Projection`.

        """
        t = kwargs.get('transform', None)
        if t is None:
            t = self.projection
        if isinstance(t, ccrs.CRS) and not isinstance(t, ccrs.Projection):
            raise ValueError('invalid transform:'
                             ' Spherical pcolor is not supported - '
                             ' consider using PlateCarree/RotatedPole.')
        kwargs.setdefault('transform', t)
        result = matplotlib.axes.Axes.pcolor(self, *args, **kwargs)
        self.autoscale_view()
        return result

    def quiver(self, x, y, u, v, *args, **kwargs):
        """
        Plot a 2-D field of arrows.

        Extra Kwargs:

        * transform: :class:`cartopy.crs.Projection` or matplotlib transform
            The coordinate system in which the vectors are defined.

        * regrid_shape: int or 2-tuple of ints
            If given, specifies that the points where the arrows are
            located will be interpolated onto a regular grid in
            projection space. If a single integer is given then that
            will be used as the minimum grid length dimension, while the
            other dimension will be scaled up according to the target
            extent's aspect ratio. If a pair of ints are given they
            determine the grid length in the x and y directions
            respectively.

        * target_extent: 4-tuple
            If given, specifies the extent in the target CRS that the
            regular grid defined by *regrid_shape* will have. Defaults
            to the current extent of the map projection.

        See :func:`matplotlib.pyplot.quiver` for details on arguments
        and other keyword arguments.

        .. note::

           The vector components must be defined as grid eastward and
           grid northward.

        """
        t = kwargs.get('transform', None)
        if t is None:
            t = self.projection
        if isinstance(t, ccrs.CRS) and not isinstance(t, ccrs.Projection):
            raise ValueError('invalid transform:'
                             ' Spherical quiver is not supported - '
                             ' consider using PlateCarree/RotatedPole.')
        if isinstance(t, ccrs.Projection):
            kwargs['transform'] = t._as_mpl_transform(self)
        else:
            kwargs['transform'] = t
        regrid_shape = kwargs.pop('regrid_shape', None)
        target_extent = kwargs.pop('target_extent',
                                   self.get_extent(self.projection))
        if regrid_shape is not None:
            # If regridding is required then we'll be handling transforms
            # manually and plotting in native coordinates.
            regrid_shape = self._regrid_shape_aspect(regrid_shape,
                                                     target_extent)
            if args:
                # Interpolate color array as well as vector components.
                x, y, u, v, c = vector_scalar_to_grid(
                    t, self.projection, regrid_shape, x, y, u, v, args[0],
                    target_extent=target_extent)
                args = (c,) + args[1:]
            else:
                x, y, u, v = vector_scalar_to_grid(
                    t, self.projection, regrid_shape, x, y, u, v,
                    target_extent=target_extent)
            kwargs.pop('transform', None)
        elif t != self.projection:
            # Transform the vectors if the projection is not the same as the
            # data transform.
            if x.ndim == 1 and y.ndim == 1:
                x, y = np.meshgrid(x, y)
            u, v = self.projection.transform_vectors(t, x, y, u, v)
        return matplotlib.axes.Axes.quiver(self, x, y, u, v, *args, **kwargs)

    def barbs(self, x, y, u, v, *args, **kwargs):
        """
        Plot a 2-D field of barbs.

        Extra Kwargs:

        * transform: :class:`cartopy.crs.Projection` or matplotlib transform
            The coordinate system in which the vectors are defined.

        * regrid_shape: int or 2-tuple of ints
            If given, specifies that the points where the arrows are
            located will be interpolated onto a regular grid in
            projection space. If a single integer is given then that
            will be used as the minimum grid length dimension, while the
            other dimension will be scaled up according to the target
            extent's aspect ratio. If a pair of ints are given they
            determine the grid length in the x and y directions
            respectively.

        * target_extent: 4-tuple
            If given, specifies the extent in the target CRS that the
            regular grid defined by *regrid_shape* will have. Defaults
            to the current extent of the map projection.

        See :func:`matplotlib.pyplot.barbs` for details on arguments
        and keyword arguments.

        .. note::

           The vector components must be defined as grid eastward and
           grid northward.

        """
        t = kwargs.get('transform', None)
        if t is None:
            t = self.projection
        if isinstance(t, ccrs.CRS) and not isinstance(t, ccrs.Projection):
            raise ValueError('invalid transform:'
                             ' Spherical barbs are not supported - '
                             ' consider using PlateCarree/RotatedPole.')
        if isinstance(t, ccrs.Projection):
            kwargs['transform'] = t._as_mpl_transform(self)
        else:
            kwargs['transform'] = t
        regrid_shape = kwargs.pop('regrid_shape', None)
        target_extent = kwargs.pop('target_extent',
                                   self.get_extent(self.projection))
        if regrid_shape is not None:
            # If regridding is required then we'll be handling transforms
            # manually and plotting in native coordinates.
            regrid_shape = self._regrid_shape_aspect(regrid_shape,
                                                     target_extent)
            if args:
                # Interpolate color array as well as vector components.
                x, y, u, v, c = vector_scalar_to_grid(
                    t, self.projection, regrid_shape, x, y, u, v, args[0],
                    target_extent=target_extent)
                args = (c,) + args[1:]
            else:
                x, y, u, v = vector_scalar_to_grid(
                    t, self.projection, regrid_shape, x, y, u, v,
                    target_extent=target_extent)
            kwargs.pop('transform', None)
        elif t != self.projection:
            # Transform the vectors if the projection is not the same as the
            # data transform.
            if x.ndim == 1 and y.ndim == 1:
                x, y = np.meshgrid(x, y)
            u, v = self.projection.transform_vectors(t, x, y, u, v)
        return matplotlib.axes.Axes.barbs(self, x, y, u, v, *args, **kwargs)

    def streamplot(self, x, y, u, v, **kwargs):
        """
        Draws streamlines of a vector flow.

        Extra Kwargs:

        * transform: :class:`cartopy.crs.Projection` or matplotlib transform
            The coordinate system in which the vector field is defined.

        See :func:`matplotlib.pyplot.streamplot` for details on arguments
        and keyword arguments.

        .. note::

           The vector components must be defined as grid eastward and
           grid northward.

        """
        t = kwargs.pop('transform', None)
        if t is None:
            t = self.projection
        if isinstance(t, ccrs.CRS) and not isinstance(t, ccrs.Projection):
            raise ValueError('invalid transform:'
                             ' Spherical streamplot is not supported - '
                             ' consider using PlateCarree/RotatedPole.')
        # Regridding is required for streamplot, it must have an evenly spaced
        # grid to work correctly. Choose our destination grid based on the
        # density keyword. The grid need not be bigger than the grid used by
        # the streamplot integrator.
        density = kwargs.get('density', 1)
        if np.isscalar(density):
            regrid_shape = [int(30 * density)] * 2
        else:
            regrid_shape = [int(25 * d) for d in density]
        # The color and linewidth keyword arguments can be arrays so they will
        # need to be gridded also.
        c = kwargs.get('color', None)
        l = kwargs.get('linewidth', None)
        scalars = []
        color_array = isinstance(c, np.ndarray)
        linewidth_array = isinstance(l, np.ndarray)
        if color_array:
            scalars.append(c)
        if linewidth_array:
            scalars.append(l)
        # Do the regridding including any scalar fields.
        target_extent = self.get_extent(self.projection)
        gridded = vector_scalar_to_grid(t, self.projection, regrid_shape,
                                        x, y, u, v, *scalars,
                                        target_extent=target_extent)
        x, y, u, v = gridded[:4]
        # If scalar fields were regridded then replace the appropriate keyword
        # arguments with the gridded arrays.
        scalars = list(gridded[4:])
        if linewidth_array:
            kwargs['linewidth'] = scalars.pop()
        if color_array:
            kwargs['color'] = ma.masked_invalid(scalars.pop())
        with warnings.catch_warnings():
            # The workaround for nan values in streamplot colors gives rise to
            # a warning which is not at all important so it is hidden from the
            # user to avoid confusion.
            message = 'Warning: converting a masked element to nan.'
            warnings.filterwarnings('ignore', message=message,
                                    category=UserWarning)
            sp = matplotlib.axes.Axes.streamplot(self, x, y, u, v, **kwargs)
        return sp

    def add_wmts(self, wmts, layer_name, **kwargs):
        """
        Add the specified WMTS layer to the axes.

        This function requires owslib and PIL to work.

        Args:

            * wmts - The URL of the WMTS, or an
                     owslib.wmts.WebMapTileService instance.
            * layer_name - The name of the layer to use.

        All other keywords are passed through to the construction of the
        image artist. See :meth:`~matplotlib.axes.Axes.imshow()` for
        more details.

        """
        from cartopy.io.ogc_clients import WMTSRasterSource
        wmts = WMTSRasterSource(wmts, layer_name)
        return self.add_raster(wmts, **kwargs)

    def add_wms(self, wms, layers, wms_kwargs=None, **kwargs):
        """
        Add the specified WMS layer to the axes.

        This function requires owslib and PIL to work.

        Parameters
        ----------
        wms : string or :class:`owslib.wms.WebMapService` instance
            The web map service URL or owslib WMS instance to use.
        layers : string or iterable of string
            The name of the layer(s) to use.
        wms_kwargs : dict or None
            Passed through to the
            :class:`~cartopy.io.ogc_clients.WMSRasterSource`
            constructor's ``getmap_extra_kwargs`` for defining getmap time
            keyword arguments.

        All other keywords are passed through to the construction of the
        image artist. See :meth:`~matplotlib.axes.Axes.imshow()` for
        more details.

        """
        from cartopy.io.ogc_clients import WMSRasterSource
        wms = WMSRasterSource(wms, layers, getmap_extra_kwargs=wms_kwargs)
        return self.add_raster(wms, **kwargs)


def _trigger_patch_reclip(event):
    """
    Defines an event callback for a GeoAxes which forces the outline and
    background patches to be re-clipped next time they are drawn.

    """
    axes = event.axes
    # trigger the outline and background patches to be re-clipped
    axes.outline_patch.reclip = True
    axes.background_patch.reclip = True

########NEW FILE########
__FILENAME__ = gridliner
# (C) British Crown Copyright 2011 - 2013, Met Office
#
# This file is part of cartopy.
#
# cartopy is free software: you can redistribute it and/or modify it under
# the terms of the GNU Lesser General Public License as published by the
# Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# cartopy is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Lesser General Public License for more details.
#
# You should have received a copy of the GNU Lesser General Public License
# along with cartopy.  If not, see <http://www.gnu.org/licenses/>.

import matplotlib
import matplotlib.collections as mcollections
import matplotlib.text as mtext
import matplotlib.ticker as mticker
import matplotlib.transforms as mtrans
import numpy as np

import cartopy
from cartopy.crs import Projection, _RectangularProjection


degree_locator = mticker.MaxNLocator(nbins=9, steps=[1, 2, 3, 6, 15, 18])

_DEGREE_SYMBOL = u'\u00B0'


def _fix_lons(lons):
    """
    Fix the given longitudes into the range ``[-180, 180]``.

    """
    lons = np.array(lons, copy=False, ndmin=1)
    fixed_lons = ((lons + 180) % 360) - 180
    # Make the positive 180s positive again.
    fixed_lons[(fixed_lons == -180) & (lons > 0)] *= -1
    return fixed_lons


def _lon_heimisphere(longitude):
    """Return the hemisphere (E, W or '' for 0) for the given longitude."""
    longitude = _fix_lons(longitude)
    if longitude > 0:
        hemisphere = 'E'
    elif longitude < 0:
        hemisphere = 'W'
    else:
        hemisphere = ''
    return hemisphere


def _lat_heimisphere(latitude):
    """Return the hemisphere (N, S or '' for 0) for the given latitude."""
    if latitude > 0:
        hemisphere = 'N'
    elif latitude < 0:
        hemisphere = 'S'
    else:
        hemisphere = ''
    return hemisphere


def _east_west_formatted(longitude, num_format='g'):
    fmt_string = u'{longitude:{num_format}}{degree}{hemisphere}'
    return fmt_string.format(longitude=abs(longitude), num_format=num_format,
                             hemisphere=_lon_heimisphere(longitude),
                             degree=_DEGREE_SYMBOL)


def _north_south_formatted(latitude, num_format='g'):
    fmt_string = u'{latitude:{num_format}}{degree}{hemisphere}'
    return fmt_string.format(latitude=abs(latitude), num_format=num_format,
                             hemisphere=_lat_heimisphere(latitude),
                             degree=_DEGREE_SYMBOL)

#: A formatter which turns longitude values into nice longitudes such as 110W
LONGITUDE_FORMATTER = mticker.FuncFormatter(lambda v, pos:
                                            _east_west_formatted(v))
#: A formatter which turns longitude values into nice longitudes such as 45S
LATITUDE_FORMATTER = mticker.FuncFormatter(lambda v, pos:
                                           _north_south_formatted(v))


class Gridliner(object):
    # NOTE: In future, one of these objects will be add-able to a GeoAxes (and
    # maybe even a plain old mpl axes) and it will call the "_draw_gridliner"
    # method on draw. This will enable automatic gridline resolution
    # determination on zoom/pan.
    def __init__(self, axes, crs, draw_labels=False, collection_kwargs=None):
        """
        Object used by :meth:`cartopy.mpl.geoaxes.GeoAxes.gridlines`
        to add gridlines and tick labels to a map.

        Args:

        * axes
            The :class:`cartopy.mpl.geoaxes.GeoAxes` object to be drawn on.

        * crs
            The :class:`cartopy.crs.CRS` defining the coordinate system that
            the gridlines are drawn in.

        * draw_labels
            Toggle whether to draw labels. For finer control, attributes of
            :class:`Gridliner` may be modified individually.

        * collection_kwargs
            Dictionary controlling line properties, passed to
            :class:`matplotlib.collections.Collection`.

        """
        self.axes = axes

        #: The :class:`~matplotlib.ticker.Locator` to use for the x
        #: gridlines and labels.
        self.xlocator = degree_locator

        #: The :class:`~matplotlib.ticker.Locator` to use for the y
        #: gridlines and labels.
        self.ylocator = degree_locator

        #: The :class:`~matplotlib.ticker.Formatter` to use for the x labels.
        self.xformatter = mticker.ScalarFormatter()
        self.xformatter.create_dummy_axis()

        #: The :class:`~matplotlib.ticker.Formatter` to use for the y labels.
        self.yformatter = mticker.ScalarFormatter()
        self.yformatter.create_dummy_axis()

        #: Whether to draw labels on the top of the map.
        self.xlabels_top = draw_labels

        #: Whether to draw labels on the bottom of the map.
        self.xlabels_bottom = draw_labels

        #: Whether to draw labels on the left hand side of the map.
        self.ylabels_left = draw_labels

        #: Whether to draw labels on the right hand side of the map.
        self.ylabels_right = draw_labels

        #: Whether to draw the x gridlines.
        self.xlines = True

        #: Whether to draw the y gridlines.
        self.ylines = True

        #: A dictionary passed through to ``ax.text`` on x label creation
        #: for styling of the text labels.
        self.xlabel_style = {}

        #: A dictionary passed through to ``ax.text`` on y label creation
        #: for styling of the text labels.
        self.ylabel_style = {}

        self.crs = crs

        # if the user specifies tick labels at this point, check if they can
        # be drawn. The same check will take place at draw time in case
        # public attributes are changed after instantiation.
        if draw_labels:
            self._assert_can_draw_ticks()

        #: The number of interpolation points which are used to draw the
        #: gridlines.
        self.n_steps = 30

        #: A dictionary passed through to
        #: ``matplotlib.collections.LineCollection`` on grid line creation.
        self.collection_kwargs = collection_kwargs

        #: The x gridlines which were created at draw time.
        self.xline_artists = []

        #: The y gridlines which were created at draw time.
        self.yline_artists = []

        #: The x labels which were created at draw time.
        self.xlabel_artists = []

        #: The y labels which were created at draw time.
        self.ylabel_artists = []

    def _crs_transform(self):
        """
        Get the drawing transform for our gridlines.

        .. note::
            this depends on the transform of our 'axes', so it may change
            dynamically.

        """
        transform = self.crs
        if not isinstance(transform, mtrans.Transform):
            transform = transform._as_mpl_transform(self.axes)
        return transform

    def _add_gridline_label(self, value, axis, upper_end):
        """
        Create a Text artist on our axes for a gridline label.

        Args:

        * value
            Coordinate value of this gridline.  The text contains this
            value, and is positioned centred at that point.

        * axis
            which axis the label is on: 'x' or 'y'.

        * upper_end
            If True, place at the maximum of the "other" coordinate (Axes
            coordinate == 1.0).  Else 'lower' end (Axes coord = 0.0).

        """
        transform = self._crs_transform()
        shift_dist_points = 5     # A margin from the map edge.
        if upper_end is False:
            shift_dist_points = -shift_dist_points
        if axis == 'x':
            x = value
            y = 1.0 if upper_end else 0.0
            h_align = 'center'
            v_align = 'bottom' if upper_end else 'top'
            tr_x = transform
            tr_y = self.axes.transAxes + \
                mtrans.ScaledTranslation(
                    0.0,
                    shift_dist_points * (1.0 / 72),
                    self.axes.figure.dpi_scale_trans)
            str_value = self.xformatter(value)
            user_label_style = self.xlabel_style
        elif axis == 'y':
            y = value
            x = 1.0 if upper_end else 0.0
            v_align = 'center'
            h_align = 'left' if upper_end else 'right'
            tr_y = transform
            tr_x = self.axes.transAxes + \
                mtrans.ScaledTranslation(
                    shift_dist_points * (1.0 / 72),
                    0.0,
                    self.axes.figure.dpi_scale_trans)
            str_value = self.yformatter(value)
            user_label_style = self.ylabel_style
        else:
            raise ValueError(
                "Unknown axis, {!r}, must be either 'x' or 'y'".format(axis))

        # Make a 'blended' transform for label text positioning.
        # One coord is geographic, and the other a plain Axes
        # coordinate with an appropriate offset.
        label_transform = mtrans.blended_transform_factory(
            x_transform=tr_x, y_transform=tr_y)

        label_style = {'verticalalignment': v_align,
                       'horizontalalignment': h_align,
                       }
        label_style.update(user_label_style)

        # Create and add a Text artist with these properties
        text_artist = mtext.Text(x, y, str_value,
                                 clip_on=False,
                                 transform=label_transform, **label_style)
        if axis == 'x':
            self.xlabel_artists.append(text_artist)
        elif axis == 'y':
            self.ylabel_artists.append(text_artist)
        self.axes.add_artist(text_artist)

    def _draw_gridliner(self, nx=None, ny=None, background_patch=None):
        """Create Artists for all visible elements and add to our Axes."""
        x_lim, y_lim = self._axes_domain(nx=nx, ny=ny,
                                         background_patch=background_patch)

        transform = self._crs_transform()

        rc_params = matplotlib.rcParams

        n_steps = self.n_steps

        x_ticks = self.xlocator.tick_values(x_lim[0], x_lim[1])
        y_ticks = self.ylocator.tick_values(y_lim[0], y_lim[1])

        # XXX this bit is cartopy specific. (for circular longitudes)
        # Purpose: omit plotting the last x line, as it may overlap the first.
        x_gridline_points = x_ticks[:]
        crs = self.crs
        if (isinstance(crs, Projection) and
                isinstance(crs, _RectangularProjection) and
                abs(np.diff(x_lim)) == abs(np.diff(crs.x_limits))):
            x_gridline_points = x_gridline_points[:-1]

        collection_kwargs = self.collection_kwargs
        if collection_kwargs is None:
            collection_kwargs = {}
        collection_kwargs = collection_kwargs.copy()
        collection_kwargs['transform'] = transform
        # XXX doesn't gracefully handle lw vs linewidth aliases...
        collection_kwargs.setdefault('color', rc_params['grid.color'])
        collection_kwargs.setdefault('linestyle', rc_params['grid.linestyle'])
        collection_kwargs.setdefault('linewidth', rc_params['grid.linewidth'])

        if self.xlines:
            lines = []
            for x in x_gridline_points:
                l = zip(np.zeros(n_steps) + x,
                        np.linspace(min(y_ticks), max(y_ticks),
                                    n_steps)
                        )
                lines.append(l)

            x_lc = mcollections.LineCollection(lines, **collection_kwargs)
            self.xline_artists.append(x_lc)
            self.axes.add_collection(x_lc, autolim=False)

        if self.ylines:
            lines = []
            for y in y_ticks:
                l = zip(np.linspace(min(x_ticks), max(x_ticks), n_steps),
                        np.zeros(n_steps) + y)
                lines.append(l)

            y_lc = mcollections.LineCollection(lines, **collection_kwargs)
            self.yline_artists.append(y_lc)
            self.axes.add_collection(y_lc, autolim=False)

        #################
        # Label drawing #
        #################

        # Trim outside-area points from the label coords.
        # Tickers may round *up* the desired range to something tidy, not
        # all of which is necessarily visible.  We must be stricter with
        # our texts, as they are drawn *without clipping*.
        x_label_points = [x for x in x_ticks if x_lim[0] <= x <= x_lim[1]]
        y_label_points = [y for y in y_ticks if y_lim[0] <= y <= y_lim[1]]

        if self.xlabels_bottom or self.xlabels_top:
            self._assert_can_draw_ticks()
            self.xformatter.set_locs(x_label_points)
            for x in x_label_points:
                if self.xlabels_bottom:
                    self._add_gridline_label(x, axis='x', upper_end=False)
                if self.xlabels_top:
                    self._add_gridline_label(x, axis='x', upper_end=True)

        if self.ylabels_left or self.ylabels_right:
            self._assert_can_draw_ticks()
            self.yformatter.set_locs(y_label_points)
            for y in y_label_points:
                if self.ylabels_left:
                    self._add_gridline_label(y, axis='y', upper_end=False)
                if self.ylabels_right:
                    self._add_gridline_label(y, axis='y', upper_end=True)

    def _assert_can_draw_ticks(self):
        """
        Check to see if ticks can be drawn. Either returns True or raises
        an exception.

        """
        # Check labelling is supported, currently a limited set of options.
        if not isinstance(self.crs, cartopy.crs.PlateCarree):
            raise TypeError('Cannot label {crs.__class__.__name__} gridlines.'
                            ' Only PlateCarree gridlines are currently '
                            'supported.'.format(crs=self.crs))
        if not isinstance(self.axes.projection,
                          (cartopy.crs.PlateCarree, cartopy.crs.Mercator)):
            raise TypeError('Cannot label gridlines on a '
                            '{prj.__class__.__name__} plot.  Only PlateCarree'
                            ' and Mercator plots are currently '
                            'supported.'.format(prj=self.axes.projection))
        return True

    def _axes_domain(self, nx=None, ny=None, background_patch=None):
        """Returns x_range, y_range"""
        DEBUG = False

        transform = self._crs_transform()

        ax_transform = self.axes.transAxes
        desired_trans = ax_transform - transform

        nx = nx or 30
        ny = ny or 30
        x = np.linspace(1e-9, 1 - 1e-9, nx)
        y = np.linspace(1e-9, 1 - 1e-9, ny)
        x, y = np.meshgrid(x, y)

        coords = np.concatenate([x.flatten()[:, None],
                                 y.flatten()[:, None]],
                                1)

        in_data = desired_trans.transform(coords)

        ax_to_bkg_patch = self.axes.transAxes - \
            background_patch.get_transform()

        ok = np.zeros(in_data.shape[:-1], dtype=np.bool)
        # XXX Vectorise contains_point
        for i, val in enumerate(in_data):
            # convert the coordinates of the data to the background
            # patches coordinates
            background_coord = ax_to_bkg_patch.transform(coords[i:i + 1, :])
            bkg_patch_contains = background_patch.get_path().contains_point
            if bkg_patch_contains(background_coord[0, :]):
                color = 'r'
                ok[i] = True
            else:
                color = 'b'

            if DEBUG:
                import matplotlib.pyplot as plt
                plt.plot(coords[i, 0], coords[i, 1], 'o' + color,
                         clip_on=False, transform=ax_transform)
#                plt.text(coords[i, 0], coords[i, 1], str(val), clip_on=False,
#                         transform=ax_transform, rotation=23,
#                         horizontalalignment='right')

        inside = in_data[ok, :]
        x_range = np.nanmin(inside[:, 0]), np.nanmax(inside[:, 0])
        y_range = np.nanmin(inside[:, 1]), np.nanmax(inside[:, 1])

        # XXX Cartopy specific thing. Perhaps make this bit a specialisation
        # in a subclass...
        crs = self.crs
        if isinstance(crs, Projection):
            x_range = np.clip(x_range, *crs.x_limits)
            y_range = np.clip(y_range, *crs.y_limits)

            # if the limit is >90 of the full x limit, then just use the full
            # x limit (this makes circular handling better)
            prct = np.abs(np.diff(x_range) / np.diff(crs.x_limits))
            if prct > 0.9:
                x_range = crs.x_limits

        return x_range, y_range

########NEW FILE########
__FILENAME__ = patch
# (C) British Crown Copyright 2011 - 2012, Met Office
#
# This file is part of cartopy.
#
# cartopy is free software: you can redistribute it and/or modify it under
# the terms of the GNU Lesser General Public License as published by the
# Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# cartopy is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Lesser General Public License for more details.
#
# You should have received a copy of the GNU Lesser General Public License
# along with cartopy.  If not, see <http://www.gnu.org/licenses/>.
"""
Provides shapely geometry <-> matplotlib path support.


See also `Shapely Geometric Objects <see_also_shapely>`_
and `Matplotlib Path API <http://matplotlib.org/api/path_api.html>`_.

.. see_also_shapely:
   http://toblerity.github.com/shapely/manual.html#geometric-objects

"""
import numpy as np
import matplotlib.path
from matplotlib.path import Path
import shapely
from shapely.geometry.collection import GeometryCollection
from shapely.geometry.linestring import LineString
from shapely.geometry.point import Point
from shapely.geometry.polygon import Polygon
from shapely.geometry.multilinestring import MultiLineString
from shapely.geometry.multipoint import MultiPoint
from shapely.geometry.multipolygon import MultiPolygon


def geos_to_path(shape):
    """
    Creates a list of :class:`matplotlib.path.Path` objects that describe
    a shape.

    Args:

    * shape
        A list, tuple or single instance of any of the following
        types: :class:`shapely.geometry.point.Point`,
        :class:`shapely.geometry.linestring.LineString`,
        :class:`shapely.geometry.polygon.Polygon`,
        :class:`shapely.geometry.multipoint.MultiPoint`,
        :class:`shapely.geometry.multipolygon.MultiPolygon`,
        :class:`shapely.geometry.multilinestring.MultiLineString`,
        :class:`shapely.geometry.collection.GeometryCollection`,
        or any type with a _as_mpl_path() method.

    Returns:
        A list of :class:`matplotlib.path.Path` objects.

    """
    if isinstance(shape, (list, tuple)):
        paths = []
        for shp in shape:
            paths.extend(geos_to_path(shp))
        return paths

    if isinstance(shape, (LineString, Point)):
        return [Path(np.vstack(shape.xy).T)]
    elif isinstance(shape, Polygon):
        def poly_codes(poly):
            codes = np.ones(len(poly.xy[0])) * Path.LINETO
            codes[0] = Path.MOVETO
            return codes

        vertices = np.concatenate([np.array(shape.exterior.xy)] +
                                  [np.array(ring.xy) for ring in
                                   shape.interiors], 1).T
        codes = np.concatenate([poly_codes(shape.exterior)] +
                               [poly_codes(ring) for ring in shape.interiors])
        return [Path(vertices, codes)]
    elif isinstance(shape, (MultiPolygon, GeometryCollection, MultiLineString,
                            MultiPoint)):
        paths = []
        for geom in shape.geoms:
            paths.extend(geos_to_path(geom))
        return paths
    elif hasattr(shape, '_as_mpl_path'):
        vertices, codes = shape._as_mpl_path()
        return [Path(vertices, codes)]
    else:
        raise ValueError('Unsupported shape type {}.'.format(type(shape)))


def path_segments(path, transform=None, remove_nans=False, clip=None,
                  quantize=False, simplify=False, curves=False,
                  stroke_width=1.0, snap=False):
    """
    Creates an array of vertices and a corresponding array of codes from a
    :class:`matplotlib.path.Path`.

    Args:

    * path
        A :class:`matplotlib.path.Path` instance.

    Kwargs:
        See :func:`matplotlib.path.iter_segments` for details of the keyword
        arguments.

    Returns:
        A (vertices, codes) tuple, where vertices is a numpy array of
        coordinates, and codes is a numpy array of matplotlib path codes.
        See :class:`matplotlib.path.Path` for information on the types of
        codes and their meanings.

    """
    # XXX assigned to avoid a ValueError inside the mpl C code...
    a = transform, remove_nans, clip, quantize, simplify, curves

    # Series of cleanups and conversions to the path e.g. it
    # can convert curved segments to line segments.
    vertices, codes = matplotlib.path.cleanup_path(path, transform,
                                                   remove_nans, clip,
                                                   snap, stroke_width,
                                                   simplify, curves)

    # Remove the final vertex (with code 0)
    return vertices[:-1, :], codes[:-1]


# Matplotlib v1.3+ deprecates the use of matplotlib.path.cleanup_path. Instead
# there is a method on a Path instance to simplify this.
if hasattr(matplotlib.path.Path, 'cleaned'):
    _path_segments_doc = path_segments.__doc__

    def path_segments(path, **kwargs):
        pth = path.cleaned(**kwargs)
        return pth.vertices[:-1, :], pth.codes[:-1]

    path_segments.__doc__ = _path_segments_doc


def path_to_geos(path, force_ccw=False):
    """
    Creates a list of Shapely geometric objects from a
    :class:`matplotlib.path.Path`.

    Args:

    * path
        A :class:`matplotlib.path.Path` instance.

    Kwargs:

    * force_ccw
        Boolean flag determining whether the path can be inverted to enforce
        ccw.

    Returns:
        A list of :class:`shapely.geometry.polygon.Polygon`,
        :class:`shapely.geometry.linestring.LineString` and/or
        :class:`shapely.geometry.multilinestring.MultiLineString` instances.

    """
    # Convert path into numpy array of vertices (and associated codes)
    path_verts, path_codes = path_segments(path, curves=False)

    # Split into subarrays such that each subarray consists of connected
    # line segments based on the start of each one being marked by a
    # matplotlib MOVETO code.
    verts_split_inds = np.where(path_codes == Path.MOVETO)[0]
    verts_split = np.split(path_verts, verts_split_inds)
    codes_split = np.split(path_codes, verts_split_inds)

    # Iterate through the vertices generating a list of
    # (external_geom, [internal_polygons]) tuples.
    collection = []
    for path_verts, path_codes in zip(verts_split, codes_split):
        if len(path_verts) == 0:
            continue

        # XXX A path can be given which does not end with close poly, in that
        # situation, we have to guess?
        # XXX Implement a point
        if (path_verts.shape[0] > 2 and
                (path_codes[-1] == Path.CLOSEPOLY or
                 all(path_verts[0, :] == path_verts[-1, :]))):
            if path_codes[-1] == Path.CLOSEPOLY:
                geom = Polygon(path_verts[:-1, :])
            else:
                geom = Polygon(path_verts)
        else:
            geom = LineString(path_verts)

        # If geom is a Polygon and is contained within the last geom in
        # collection, add it to its list of internal polygons, otherwise
        # simple append it as a  new external geom.
        if (len(collection) > 0 and
                isinstance(collection[-1][0], Polygon) and
                isinstance(geom, Polygon) and
                collection[-1][0].contains(geom.exterior)):
            collection[-1][1].append(geom.exterior)
        else:
            collection.append((geom, []))

    # Convert each (external_geom, [internal_polygons]) pair into a
    # a shapely Polygon that encapsulates the internal polygons, if the
    # external geom is a LineSting leave it alone.
    geom_collection = []
    for external_geom, internal_polys in collection:
        if internal_polys:
            # XXX worry about islands within lakes
            geom = Polygon(external_geom.exterior, internal_polys)
        else:
            geom = external_geom

        # Correctly orientate the polygon (ccw)
        if force_ccw and not geom.exterior.is_ccw:
            geom = shapely.geometry.polygon.orient(geom)

        geom_collection.append(geom)

    # If the geom_collection only contains LineStrings combine them
    # into a single MultiLinestring.
    if geom_collection and all(isinstance(geom, LineString) for
                               geom in geom_collection):
        geom_collection = [MultiLineString(geom_collection)]

    # Remove any zero area Polygons
    not_zero_poly = lambda geom: ((isinstance(geom, Polygon) and
                                   not geom._is_empty and geom.area != 0) or
                                  not isinstance(geom, Polygon))
    result = filter(not_zero_poly, geom_collection)

    return result

########NEW FILE########
__FILENAME__ = slippy_image_artist
# (C) British Crown Copyright 2014, Met Office
#
# This file is part of cartopy.
#
# cartopy is free software: you can redistribute it and/or modify it under
# the terms of the GNU Lesser General Public License as published by the
# Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# cartopy is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Lesser General Public License for more details.
#
# You should have received a copy of the GNU Lesser General Public License
# along with cartopy.  If not, see <http://www.gnu.org/licenses/>.
"""
Defines the SlippyImageArtist class, which interfaces with
:class:`cartopy.io.RasterSource` instances at draw time, for interactive
dragging and zooming of raster data.

"""
from matplotlib.image import AxesImage
import matplotlib.artist


class SlippyImageArtist(AxesImage):

    """
    A subclass of :class:`~matplotlib.image.AxesImage` which provides an
    interface for getting a raster from the given object with interactive
    slippy map type functionality.

    Kwargs are passed to the AxesImage constructor.

    """
    def __init__(self, ax, raster_source, **kwargs):
        self.raster_source = raster_source
        super(SlippyImageArtist, self).__init__(ax, **kwargs)
        self.set_clip_path(ax.outline_patch)

    @matplotlib.artist.allow_rasterization
    def draw(self, renderer, *args, **kwargs):
        if not self.get_visible():
            return

        ax = self.get_axes()
        window_extent = ax.get_window_extent()
        [x1, y1], [x2, y2] = ax.viewLim.get_points()
        img, extent = self.raster_source.fetch_raster(
            ax.projection, extent=[x1, x2, y1, y2],
            target_resolution=(window_extent.width, window_extent.height))
        if img is None or extent is None:
            return
        self.set_array(img)
        with ax.hold_limits():
            self.set_extent(extent)

        super(SlippyImageArtist, self).draw(renderer, *args, **kwargs)

########NEW FILE########
__FILENAME__ = gallery
# (C) British Crown Copyright 2013, Met Office
#
# This file is part of cartopy.
#
# cartopy is free software: you can redistribute it and/or modify it under
# the terms of the GNU Lesser General Public License as published by the
# Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# cartopy is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Lesser General Public License for more details.
#
# You should have received a copy of the GNU Lesser General Public License
# along with cartopy.  If not, see <http://www.gnu.org/licenses/>.

import os.path
import sys

from cartopy.sphinxext.summarise_package import walk_module
import cartopy.tests


def out_of_date(original_fname, target_fname):
    """
    Checks to see if the ``target_fname`` exists, and if so, whether
    the modification timestamp suggests that ``original_fname`` is newer
    than ``target_fname``.

    """
    return (not os.path.exists(target_fname) or
            os.path.getmtime(original_fname) > os.path.getmtime(target_fname))


def same_contents(fname, contents_str):
    """
    Checks to see if the given fname contains the contents given by
    ``contents_str``. The result could be used to determine if the
    contents need to be written to the given fname.

    """
    if os.path.exists(fname):
        with open(fname, 'r') as fh:
            return fh.read() == contents_str
    return False


def parent_module(module):
    """
    Returns the direct module ascendent of the given module.

    For example, giving a module ``a.b.c`` would return the
    ``a.b`` module.

    If the module is a top level package, None will be returned.

    .. note::

        Requires the __name__ attribute on the given module
        to be correctly defined and the parent module to be importable.

    >>> import numpy.ma.core
    >>> from cartopy.sphinxext.gallery import parent_module
    >>> parent_module(numpy.ma.core) # doctest: +ELLIPSIS
    <module 'numpy.ma' from '...'>

    """
    result = None

    name = module.__name__
    by_dot = name.split('.')
    if len(by_dot) > 1:
        parent_name = '.'.join(by_dot[:-1])
        result = get_module(parent_name)

    return result


def get_module(mod_name):
    """
    Return the module instance of the given name, by importing
    it into the system.

    """
    __import__(mod_name)
    return sys.modules[mod_name]


def safe_mod_name_and_fname(module_name, ancestor_module_name):
    """
    Returns a safe module name (for linking too) and safe filename (suffixed
    with ".rst") for the given module name, relative to the given ancestor
    module.


    >>> from cartopy.sphinxext.gallery import safe_mod_name_and_fname
    >>> safe_mod_name_and_fname('numpy.ma.core', 'numpy')
    ('ma-core', 'ma/core.rst')

    """
    mod = get_module(module_name)
    ancestor_package = get_module(ancestor_module_name)

    safe_fname = os.path.relpath(os.path.splitext(mod.__file__)[0],
                                 os.path.dirname(ancestor_package.__file__))
    safe_name = safe_fname.replace(os.path.sep, '-')
    safe_fname = safe_fname + '.rst'
    return safe_name, safe_fname


def examples_code(examples_mod_name,
                  source_directory,
                  output_directory='examples'):
    """
    Generates the rst code for the given examples module.

    examples_mod_name - the name of the parent (importable) module which
                        should be recursively walked when looking for
                        examples

    source_directory - the path to the top level source directory containing
                       the rst content of the documentation

    output_directory - the directory for the output to be put in. Should be
                       relative to the source_directory

    """
    for mod_name, root_dir, fname, _ in walk_module(examples_mod_name):
        if fname.startswith('__init__'):
            continue

        rst, rst_fname = individual_example_rst(mod_name, examples_mod_name,
                                                output_directory)
        rst_fname = os.path.join(source_directory, output_directory, rst_fname)

        py_fname = os.path.join(source_directory, output_directory,
                                os.path.splitext(rst_fname)[0] + '.py')

        if not os.path.isdir(os.path.dirname(py_fname)):
            os.makedirs(os.path.dirname(py_fname))

        if out_of_date(os.path.join(root_dir, fname), py_fname):
            with open(os.path.join(root_dir, fname), 'r') as in_fh:
                with open(py_fname, 'w') as out_fh:
                    for line in in_fh:
                        # Crudely remove the __tags__ line.
                        if line.startswith('__tags__ = '):
                            continue
                        out_fh.write(line)

        if not same_contents(rst_fname, rst):
            with open(rst_fname, 'w') as fh:
                fh.write(rst)


def gallery_code(examples_mod_name):
    """
    Returns rst code suitable for generating a html gallery using sphinx.

    examples_mod_name - the name of the importable (sub)module which contains
                        the examples

    """
    # Store a dictionary mapping tag_name to (mod_name, mod_instance, tags)
    examples_by_tag = {}

    for mod_name, _, _, _ in walk_module(examples_mod_name):
        if mod_name != examples_mod_name:
            __import__(mod_name)
            mod = sys.modules[mod_name]
            tags = getattr(mod, '__tags__', ['Miscellanea'])

            for tag in tags:
                examples_by_tag.setdefault(tag, []).append((mod_name, mod))

    result = ['Gallery',
              '=======',
              'Tags:\n',
              '.. container:: inline-paragraphs\n'
              ]

    examples_by_tag = sorted(examples_by_tag.iteritems(),
                             key=lambda pair: (pair[0] == 'Miscellanea',
                                               pair[0]))

    for tag, _ in examples_by_tag:
        result.append('\t:ref:`gallery-tag-{}`\n'.format(tag))

    for tag, mod_list in examples_by_tag:
        result.extend(['.. _gallery-tag-{}:\n'.format(tag),
                       '{}'.format(tag),
                       '-' * len(tag) + '\n',
                       '.. container:: gallery_images\n'])

        for (mod_name, mod) in mod_list:
            safe_name, _ = safe_mod_name_and_fname(mod_name,
                                                   examples_mod_name)

            # XXX The path is currently determined out of process by
            # the plot directive. It would be nice to figure out the
            # naming scheme to handle multiple plots in a single example.
            img_path = 'examples/{}_01_00.png'.format(
                mod_name.split('.')[-1])
            thumb_path = 'examples/{}_01_00.thumb.png'.format(
                mod_name.split('.')[-1])

            entry = ["|image_{}|_\n".format(safe_name),
                     ".. |image_{}| image:: {}".format(safe_name, thumb_path),
                     # XXX Hard-codes the html - rst cannot do nested inline
                     # elements (very well).
                     ".. _image_{}: examples/{}.html".format(
                         safe_name, safe_name)]

            result.extend(['\n\n\t' + line for line in entry])

    return '\n'.join(result)


def individual_example_rst(example_mod_name, examples_mod_name,
                           output_directory):
    """
    Generates the rst code for the given example and suggests a sensible
    rst filename.

    example_mod_name - the name of the importable submodule which contains
                       the individual example which is to be documented

    examples_mod_name - the name of the importable (sub)module which contains
                        the examples

    output_directory - is a path to the examples output directory, relative
                       to the source directory.

    """
    mod = get_module(example_mod_name)
    safe_name, safe_fname = safe_mod_name_and_fname(example_mod_name,
                                                    examples_mod_name)
    fname_base = os.path.splitext(safe_fname)[0] + '.py'
    example_code_fname = os.path.join(output_directory, fname_base)

    result = ['.. _examples-{}:\n'.format(safe_name)]

    if mod.__doc__:
        result.append(mod.__doc__ + '\n')
    else:
        result.extend(['{} example'.format(safe_name),
                       '-' * (len(safe_name) + 8) + '\n'])

    result.extend(['.. plot:: {}\n'.format(example_code_fname),
                   '.. literalinclude:: {}\n'.format(fname_base)])

    return '\n'.join(result), safe_fname


def gen_gallery(app):
    """Produces the gallery rst file."""
    example_package_name = app.config.examples_package_name
    fname = app.config.gallery_name

    if example_package_name is None:
        raise ValueError('A config value for gallery_package_name should be '
                         'defined.')

    outdir = app.builder.srcdir
    fname = os.path.join(outdir, fname)

    gallery_rst = gallery_code(example_package_name)

    if not same_contents(fname, gallery_rst):
        with open(fname, 'w') as fh:
            fh.write(gallery_rst)


def gen_examples(app):
    """Produces the examples directory."""
    example_package_name = app.config.examples_package_name

    source_dir = app.builder.srcdir

    examples_code(example_package_name, source_dir, 'examples')


@cartopy.tests.not_a_nose_fixture
def setup(app):
    app.connect('builder-inited', gen_gallery)
    app.connect('builder-inited', gen_examples)

    # Allow users to define a config value to determine the name of the
    # gallery rst file (with file extension included)
    app.add_config_value('gallery_name', 'gallery.rst', 'env')

    # Allow users to define a config value to determine the name of the
    # importable examples (sub)package
    app.add_config_value('examples_package_name', None, 'env')

########NEW FILE########
__FILENAME__ = summarise_package
# (C) British Crown Copyright 2011 - 2013, Met Office
#
# This file is part of cartopy.
#
# cartopy is free software: you can redistribute it and/or modify it under
# the terms of the GNU Lesser General Public License as published by the
# Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# cartopy is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Lesser General Public License for more details.
#
# You should have received a copy of the GNU Lesser General Public License
# along with cartopy.  If not, see <http://www.gnu.org/licenses/>.

import inspect
import itertools
import os
import sys
import warnings

import cartopy.tests


def walk_module(mod_name, exclude_folders=None):
    """
    Recursively walks the given module name.

    Returns:

        A generator of::

            (fully_qualified_import_name,
             root_directory_of_subpackage,
             fname_in_root_directory,
             sub_folders_in_root_directory)

    """
    __import__(mod_name)
    mod = sys.modules[mod_name]
    mod_dir = os.path.dirname(mod.__file__)
    exclude_folders = exclude_folders or []

    for root, folders, files in os.walk(mod_dir):
        for folder in exclude_folders:
            try:
                folders.remove(folder)
            except ValueError:
                pass

        # only allow python packages
        if not '__init__.py' in files:
            del folders[:]
            continue

        # Sort by filename and folder name.
        files.sort()
        folders.sort()

        is_py_src = lambda fname: fname.endswith(
            '.py') or fname.endswith('.so')
        files = filter(is_py_src, files)

        for fname in files:
            sub_mod_name = mod_name
            relpath = os.path.relpath(root, mod_dir)
            if relpath == '.':
                relpath = ''

            for sub_mod in filter(None, relpath.split(os.path.sep)):
                sub_mod_name += '.' + sub_mod

            if fname != '__init__.py':
                sub_mod_name += '.' + os.path.splitext(fname)[0]

            yield sub_mod_name, root, fname, folders


def objects_to_document(module_name):
    """
    Creates a generator of (obj_name, obj) that the given module of the
    given name should document.

    The module name may be any importable, including submodules
    (e.g. ``cartopy.io```)

    """
    try:
        __import__(module_name)
    except ImportError:
        warnings.warn('Failed to document {}'.format(module_name))
        return []
    module = sys.modules[module_name]
    elems = dir(module)

    if '__all__' in elems:
        document_these = [(obj, getattr(module, obj))
                          for obj in module.__all__]
    else:
        document_these = [(obj, getattr(module, obj)) for obj in elems
                          if not inspect.ismodule(getattr(module, obj)) and
                          not obj.startswith('_')]

        is_from_this_module = lambda x: (
            getattr(x[1], '__module__', '') == module_name)

        document_these = filter(is_from_this_module, document_these)
        document_these = sorted(document_these,
                                key=lambda x: (type(x[1]),
                                               not x[0].isupper(),
                                               x[0]))

    # allow a developer to add other things to the documentation
    if hasattr(module, '__document_these__'):
        extra_objects_to_document = tuple((obj, getattr(module, obj))
                                          for obj in module.__document_these__)
        document_these = extra_objects_to_document + tuple(document_these)

    return document_these


def main(package_name, exclude_folders=None):
    """
    Return a string containing the rst that documents the given package name.

    """
    result = ''
    mod_walk = walk_module(package_name, exclude_folders=exclude_folders)
    for mod, _, fname, folders in mod_walk:
        for folder in folders:
            if folder.startswith('_'):
                folders.remove(folder)
        if fname.startswith('_') and fname != '__init__.py':
            continue

        result += '\n'
        result += mod + '\n'
        result += '*' * len(mod) + '\n'

        result += '\n'
        result += '.. currentmodule:: {}\n'.format(mod) + '\n'

        mod_objects = objects_to_document(mod)
        if mod_objects:
            result += '.. csv-table::\n' + '\n'

        table_elements = itertools.cycle(('\n\t', ) + (', ', ) * 3)
        for table_elem, (obj_name, _) in zip(table_elements, mod_objects):
            result += '{}:py:obj:`{}`'.format(table_elem, obj_name)

        result += '\n'

    return result


def gen_summary_rst(app):
    """
    Creates the rst file to summarise the desired packages.

    """
    package_names = app.config.summarise_package_names
    exclude_dirs = app.config.summarise_package_exclude_directories
    fnames = app.config.summarise_package_fnames

    if isinstance(package_names, basestring):
        package_names = [package_names]

    if package_names is None:
        raise ValueError('Please define a config value containing a list '
                         'of packages to summarise.')

    if exclude_dirs is None:
        exclude_dirs = [None] * len(package_names)
    else:
        exception = ValueError('Please provide a list of exclude directory '
                               'lists (one list for each package to '
                               'summarise).')

        if len(exclude_dirs) != len(package_names):
            raise exception

        for exclude_dirs_individual in exclude_dirs:
            if isinstance(exclude_dirs_individual, basestring):
                raise exception

    if fnames is None:
        fnames = ['outline_of_{}.rst'.format(package_name)
                  for package_name in package_names]
    else:
        if isinstance(fnames, basestring) or len(fnames) != len(package_names):
            raise TypeError('Please provide a list of filenames for each of '
                            'the packages which are to be summarised.')

    outdir = app.builder.srcdir

    for package_name, out_fname, exclude_folders in zip(package_names,
                                                        fnames,
                                                        exclude_dirs):
        out_fpath = os.path.join(outdir, out_fname)
        content = main(package_name, exclude_folders=exclude_folders)
        with open(out_fpath, 'w') as fh:
            fh.write(content)


@cartopy.tests.not_a_nose_fixture
def setup(app):
    """
    Defined the Sphinx application interface for the summary generation.

    """
    app.connect('builder-inited', gen_summary_rst)

    # Allow users to define a config value to determine the names to summarise
    app.add_config_value('summarise_package_names', None, 'env')

    # Allow users to define a config value to determine the folders to exclude
    app.add_config_value('summarise_package_exclude_directories', None, 'env')

    # Allow users to define a config value to determine name of the output file
    app.add_config_value('summarise_package_fnames', None, 'env')

########NEW FILE########
__FILENAME__ = test_geostationary
# (C) British Crown Copyright 2013, Met Office
#
# This file is part of cartopy.
#
# cartopy is free software: you can redistribute it and/or modify it under
# the terms of the GNU Lesser General Public License as published by the
# Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# cartopy is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Lesser General Public License for more details.
#
# You should have received a copy of the GNU Lesser General Public License
# along with cartopy.  If not, see <http://www.gnu.org/licenses/>.
"""
Tests for the Transverse Mercator projection, including OSGB and OSNI.

"""

import unittest

from numpy.testing import assert_almost_equal
from nose.tools import assert_equal

import cartopy.crs as ccrs


class TestGeostationary(unittest.TestCase):
    def check_proj4_params(self, crs, expected):
        pro4_params = sorted(crs.proj4_init.split(' +'))
        assert_equal(expected, pro4_params)

    def test_default(self):
        geos = ccrs.Geostationary()
        expected = ['+ellps=WGS84', 'h=35785831', 'lat_0=0', 'lon_0=0.0',
                    'no_defs', 'proj=geos', 'units=m', 'x_0=0', 'y_0=0']
        self.check_proj4_params(geos, expected)

        assert_almost_equal(geos.boundary.bounds,
                            (-5364970.19679699, -5370680.80015303,
                             5372584.78443894, 5370680.80015303),
                            decimal=4)

    def test_eccentric_globe(self):
        globe = ccrs.Globe(semimajor_axis=10000, semiminor_axis=5000,
                           ellipse=None)
        geos = ccrs.Geostationary(satellite_height=50000,
                                  globe=globe)
        expected = ['+a=10000', 'b=5000', 'h=50000', 'lat_0=0', 'lon_0=0.0',
                    'no_defs', 'proj=geos', 'units=m', 'x_0=0', 'y_0=0']
        self.check_proj4_params(geos, expected)

        assert_almost_equal(geos.boundary.bounds,
                            (-8245.7306, -4531.3879, 8257.4339, 4531.3879),
                            decimal=4)

    def test_eastings(self):
        geos = ccrs.Geostationary(false_easting=5000000,
                                  false_northing=-125000,)
        expected = ['+ellps=WGS84', 'h=35785831', 'lat_0=0', 'lon_0=0.0',
                    'no_defs', 'proj=geos', 'units=m', 'x_0=5000000',
                    'y_0=-125000']
        self.check_proj4_params(geos, expected)

        assert_almost_equal(geos.boundary.bounds,
                            (-364970.19679699, -5495680.80015303,
                             10372584.78443894, 5245680.80015303),
                            decimal=4)

if __name__ == '__main__':
    import nose
    nose.runmodule(argv=['-s', '--with-doctest'], exit=False)

########NEW FILE########
__FILENAME__ = test_lambert_conformal
# (C) British Crown Copyright 2011 - 2013, Met Office
#
# This file is part of cartopy.
#
# cartopy is free software: you can redistribute it and/or modify it under
# the terms of the GNU Lesser General Public License as published by the
# Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# cartopy is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Lesser General Public License for more details.
#
# You should have received a copy of the GNU Lesser General Public License
# along with cartopy.  If not, see <http://www.gnu.org/licenses/>.

from numpy.testing import assert_array_almost_equal
from nose.tools import assert_equal, assert_not_equal, assert_true

import cartopy.crs as ccrs


def test_defaults():
    crs = ccrs.LambertConformal()
    assert_equal(crs.proj4_init, ('+ellps=WGS84 +proj=lcc +lon_0=-96.0 '
                                  '+lat_0=39.0 +x_0=0.0 +y_0=0.0 +lat_1=33 '
                                  '+lat_2=45 +no_defs'))


def test_default_with_cutoff():
    crs = ccrs.LambertConformal(cutoff=-80)
    crs2 = ccrs.LambertConformal(cutoff=-80)
    default = ccrs.LambertConformal()

    assert_equal(crs.proj4_init, ('+ellps=WGS84 +proj=lcc +lon_0=-96.0 '
                                  '+lat_0=39.0 +x_0=0.0 +y_0=0.0 +lat_1=33 '
                                  '+lat_2=45 +no_defs'))

    # Check the behaviour of !=, == and (not ==) for the different cutoffs.
    assert_equal(crs, crs2)
    assert_true(crs != default)
    assert_not_equal(crs, default)

    assert_not_equal(hash(crs), hash(default))
    assert_equal(hash(crs), hash(crs2))

    assert_array_almost_equal(crs.y_limits,
                              (-49788019.81822971, 30793476.084826108))


def test_specific_lambert():
    # This projection comes from EPSG Projection 3034 - ETRS89 / ETRS-LCC.
    crs = ccrs.LambertConformal(central_longitude=10,
                                secant_latitudes=(35, 65),
                                central_latitude=52,
                                false_easting=4000000,
                                false_northing=2800000,
                                globe=ccrs.Globe(ellipse='GRS80'))
    assert_equal(crs.proj4_init, ('+ellps=GRS80 +proj=lcc +lon_0=10 '
                                  '+lat_0=52 +x_0=4000000 +y_0=2800000 '
                                  '+lat_1=35 +lat_2=65 +no_defs'))


if __name__ == '__main__':
    import nose
    nose.runmodule(argv=['-s', '--with-doctest'], exit=False)

########NEW FILE########
__FILENAME__ = test_mercator
# (C) British Crown Copyright 2013, Met Office
#
# This file is part of cartopy.
#
# cartopy is free software: you can redistribute it and/or modify it under
# the terms of the GNU Lesser General Public License as published by the
# Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# cartopy is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Lesser General Public License for more details.
#
# You should have received a copy of the GNU Lesser General Public License
# along with cartopy.  If not, see <http://www.gnu.org/licenses/>.
import unittest

from numpy.testing import assert_almost_equal
from nose.tools import assert_equal, assert_true, assert_not_equal

import cartopy.crs as ccrs


def test_default():
    crs = ccrs.Mercator()

    assert_equal(crs.proj4_init, ('+ellps=WGS84 +proj=merc +lon_0=0.0 +k=1 '
                                  '+units=m +no_defs'))
    assert_almost_equal(crs.boundary.bounds,
                        [-20037508, -15496571, 20037508, 18764656], decimal=0)


def test_eccentric_globe():
    globe = ccrs.Globe(semimajor_axis=10000, semiminor_axis=5000,
                       ellipse=None)
    crs = ccrs.Mercator(globe=globe, min_latitude=-40, max_latitude=40)
    assert_equal(crs.proj4_init, ('+a=10000 +b=5000 +proj=merc +lon_0=0.0 '
                                  '+k=1 +units=m +no_defs'))

    assert_almost_equal(crs.boundary.bounds,
                        [-31415.93, -2190.5, 31415.93, 2190.5], decimal=2)

    assert_almost_equal(crs.x_limits, [-31415.93, 31415.93], decimal=2)
    assert_almost_equal(crs.y_limits, [-2190.5, 2190.5], decimal=2)


def test_equality():
    default = ccrs.Mercator()
    crs = ccrs.Mercator(min_latitude=0)
    crs2 = ccrs.Mercator(min_latitude=0)

    # Check the == and != operators.
    assert_equal(crs, crs2)
    assert_not_equal(crs, default)
    assert_true(crs != default)
    assert_not_equal(hash(crs), hash(default))
    assert_equal(hash(crs), hash(crs2))


if __name__ == '__main__':
    import nose
    nose.runmodule(argv=['-s', '--with-doctest'], exit=False)

########NEW FILE########
__FILENAME__ = test_robinson
# (C) British Crown Copyright 2013, Met Office
#
# This file is part of cartopy.
#
# cartopy is free software: you can redistribute it and/or modify it under
# the terms of the GNU Lesser General Public License as published by the
# Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# cartopy is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Lesser General Public License for more details.
#
# You should have received a copy of the GNU Lesser General Public License
# along with cartopy.  If not, see <http://www.gnu.org/licenses/>.
'''
Tests for Robinson projection.

For now, mostly tests the workaround for a specific problem.
Problem report in : https://github.com/SciTools/cartopy/issues/23
Fix covered in : https://github.com/SciTools/cartopy/pull/277

'''
import sys
import unittest

from nose.tools import assert_true, assert_false, assert_equal
import numpy as np
from numpy.testing import assert_array_almost_equal as assert_arr_almost_eq

import cartopy.crs as ccrs


_NAN = float('nan')
_CRS_PC = ccrs.PlateCarree()
_CRS_ROB = ccrs.Robinson()


def test_transform_point():
    # this way has always worked
    result = _CRS_ROB.transform_point(35.0, 70.0, _CRS_PC)
    assert_arr_almost_eq(result, (2376187.159105642, 7275318.947140937))

    # this always did something, but result has altered
    result = _CRS_ROB.transform_point(_NAN, 70.0, _CRS_PC)
    assert_true(np.all(np.isnan(result)))

    # this used to crash + is now fixed
    result = _CRS_ROB.transform_point(35.0, _NAN, _CRS_PC)
    assert_true(np.all(np.isnan(result)))


def test_transform_points():
    # these always worked
    result = _CRS_ROB.transform_points(_CRS_PC,
                                       np.array([35.0]),
                                       np.array([70.0]))
    assert_arr_almost_eq(result,
                         [[2376187.159105642, 7275318.947140937, 0]])

    result = _CRS_ROB.transform_points(_CRS_PC,
                                       np.array([35.0]),
                                       np.array([70.0]),
                                       np.array([0.0]))
    assert_arr_almost_eq(result,
                         [[2376187.159105642, 7275318.947140937, 0]])

    # this always did something, but result has altered
    result = _CRS_ROB.transform_points(_CRS_PC,
                                       np.array([_NAN]),
                                       np.array([70.0]))
    assert_true(np.all(np.isnan(result)))

    # this used to crash + is now fixed
    result = _CRS_ROB.transform_points(_CRS_PC,
                                       np.array([35.0]),
                                       np.array([_NAN]))
    assert_true(np.all(np.isnan(result)))

    # multipoint case
    x = np.array([10.0, 21.0, 0.0, 77.7, _NAN, 0.0])
    y = np.array([10.0, _NAN, 10.0, 77.7, 55.5, 0.0])
    z = np.array([10.0, 0.0, 0.0, _NAN, 55.5, 0.0])
    expect_result = np.array(
        [[9.40422591e+05, 1.06952091e+06, 1.00000000e+01],
         [11.1, 11.2, 11.3],
         [0.0, 1069520.91213902, 0.0],
         [22.1, 22.2, 22.3],
         [33.1, 33.2, 33.3],
         [0.0, 0.0, 0.0]])
    result = _CRS_ROB.transform_points(_CRS_PC, x, y, z)
    assert_equal(result.shape, (6, 3))
    assert_true(np.all(np.isnan(result[[1, 3, 4], :])))
    result[[1, 3, 4], :] = expect_result[[1, 3, 4], :]
    assert_false(np.any(np.isnan(result)))
    assert_true(np.allclose(result, expect_result))


if __name__ == '__main__':
    import nose
    nose.runmodule(argv=['-s', '--with-doctest'], exit=False)

########NEW FILE########
__FILENAME__ = test_stereographic
# (C) British Crown Copyright 2013, Met Office
#
# This file is part of cartopy.
#
# cartopy is free software: you can redistribute it and/or modify it under
# the terms of the GNU Lesser General Public License as published by the
# Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# cartopy is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Lesser General Public License for more details.
#
# You should have received a copy of the GNU Lesser General Public License
# along with cartopy.  If not, see <http://www.gnu.org/licenses/>.
import unittest

import numpy as np
from numpy.testing import assert_almost_equal
from nose.tools import assert_equal

import cartopy.crs as ccrs


class TestStereographic(unittest.TestCase):
    def test_default(self):
        stereo = ccrs.Stereographic()
        expected = ('+ellps=WGS84 +proj=stere +lat_0=0.0 '
                    '+lon_0=0.0 +x_0=0.0 +y_0=0.0 +no_defs')
        assert_equal(stereo.proj4_init, expected)

        assert_almost_equal(np.array(stereo.x_limits),
                            [-5e7, 5e7], decimal=4)
        assert_almost_equal(np.array(stereo.y_limits),
                            [-5e7, 5e7], decimal=4)

    def test_eccentric_globe(self):
        globe = ccrs.Globe(semimajor_axis=1000, semiminor_axis=500,
                           ellipse=None)
        stereo = ccrs.Stereographic(globe=globe)
        expected = ('+a=1000 +b=500 +proj=stere +lat_0=0.0 +lon_0=0.0 '
                    '+x_0=0.0 +y_0=0.0 +no_defs')
        assert_equal(stereo.proj4_init, expected)

        # The limits in this test are sensible values, but are by no means
        # a "correct" answer - they mean that plotting the crs results in a
        # reasonable map.
        assert_almost_equal(np.array(stereo.x_limits),
                            [-7839.27971444, 7839.27971444], decimal=4)
        assert_almost_equal(np.array(stereo.y_limits),
                            [-3932.82587779, 3932.82587779], decimal=4)

    def test_true_scale(self):
        # The "true_scale_latitude" parameter to Stereographic appears
        # meaningless. This test just ensures that the correct proj4
        # string is being created. (#339)
        stereo = ccrs.Stereographic(true_scale_latitude=10)
        expected = ('+ellps=WGS84 +proj=stere +lat_0=0.0 +lon_0=0.0 '
                    '+x_0=0.0 +y_0=0.0 +lat_ts=10 +no_defs')
        assert_equal(stereo.proj4_init, expected)

    def test_eastings(self):
        stereo = ccrs.Stereographic()
        stereo_offset = ccrs.Stereographic(false_easting=1234,
                                           false_northing=-4321)

        expected = ('+ellps=WGS84 +proj=stere +lat_0=0.0 +lon_0=0.0 '
                    '+x_0=1234 +y_0=-4321 +no_defs')
        assert_equal(stereo_offset.proj4_init, expected)
        assert_equal(tuple(np.array(stereo.x_limits) + 1234),
                     stereo_offset.x_limits)


if __name__ == '__main__':
    import nose
    nose.runmodule(argv=['-s', '--with-doctest'], exit=False)

########NEW FILE########
__FILENAME__ = test_transverse_mercator
# (C) British Crown Copyright 2013, Met Office
#
# This file is part of cartopy.
#
# cartopy is free software: you can redistribute it and/or modify it under
# the terms of the GNU Lesser General Public License as published by the
# Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# cartopy is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Lesser General Public License for more details.
#
# You should have received a copy of the GNU Lesser General Public License
# along with cartopy.  If not, see <http://www.gnu.org/licenses/>.
"""
Tests for the Transverse Mercator projection, including OSGB and OSNI.

"""

import unittest

import numpy as np
import numpy.testing

import cartopy.crs as ccrs


class TestTransverseMercator(unittest.TestCase):
    def setUp(self):
        self.point_a = (-3.474083, 50.727301)
        self.point_b = (0.5, 50.5)
        self.src_crs = ccrs.PlateCarree()

    def test_default(self):
        proj = ccrs.TransverseMercator()
        res = proj.transform_point(*self.point_a, src_crs=self.src_crs)
        np.testing.assert_array_almost_equal(res, (-245269.531806,
                                                   5627508.743548))
        res = proj.transform_point(*self.point_b, src_crs=self.src_crs)
        np.testing.assert_array_almost_equal(res, (35474.635666,
                                                   5596583.419497))

    def test_osgb_vals(self):
        proj = ccrs.TransverseMercator(central_longitude=-2,
                                       central_latitude=49,
                                       scale_factor=0.9996012717,
                                       false_easting=400000,
                                       false_northing=-100000,
                                       globe=ccrs.Globe(datum='OSGB36',
                                                        ellipse='airy'))
        res = proj.transform_point(*self.point_a, src_crs=self.src_crs)
        np.testing.assert_array_almost_equal(res, (295971.286677,
                                                   93064.276662))
        res = proj.transform_point(*self.point_b, src_crs=self.src_crs)
        np.testing.assert_array_almost_equal(res, (577274.983801,
                                                   69740.492270))

    def test_nan(self):
        proj = ccrs.TransverseMercator()
        res = proj.transform_point(0.0, float('nan'), src_crs=self.src_crs)
        self.assertTrue(np.all(np.isnan(res)))
        res = proj.transform_point(float('nan'), 0.0, src_crs=self.src_crs)
        self.assertTrue(np.all(np.isnan(res)))


class TestOSGB(unittest.TestCase):
    def setUp(self):
        self.point_a = (-3.474083, 50.727301)
        self.point_b = (0.5, 50.5)
        self.src_crs = ccrs.PlateCarree()
        self.nan = float('nan')

    def test_default(self):
        proj = ccrs.OSGB()
        res = proj.transform_point(*self.point_a, src_crs=self.src_crs)
        np.testing.assert_array_almost_equal(res, (295971.286677,
                                                   93064.276662))
        res = proj.transform_point(*self.point_b, src_crs=self.src_crs)
        np.testing.assert_array_almost_equal(res, (577274.983801,
                                                   69740.492270))

    def test_nan(self):
        proj = ccrs.OSGB()
        res = proj.transform_point(0.0, float('nan'), src_crs=self.src_crs)
        self.assertTrue(np.all(np.isnan(res)))
        res = proj.transform_point(float('nan'), 0.0, src_crs=self.src_crs)
        self.assertTrue(np.all(np.isnan(res)))


class TestOSNI(unittest.TestCase):
    def setUp(self):
        self.point_a = (-6.826286, 54.725116)
        self.src_crs = ccrs.PlateCarree()
        self.nan = float('nan')

    def test_default(self):
        proj = ccrs.OSNI()
        res = proj.transform_point(*self.point_a, src_crs=self.src_crs)
        np.testing.assert_array_almost_equal(res, (275614.871056,
                                                   386984.153472))

    def test_nan(self):
        proj = ccrs.OSNI()
        res = proj.transform_point(0.0, float('nan'), src_crs=self.src_crs)
        self.assertTrue(np.all(np.isnan(res)))
        res = proj.transform_point(float('nan'), 0.0, src_crs=self.src_crs)
        self.assertTrue(np.all(np.isnan(res)))


if __name__ == '__main__':
    import nose
    nose.runmodule(argv=['-s', '--with-doctest'], exit=False)

########NEW FILE########
__FILENAME__ = test_downloaders
# (C) British Crown Copyright 2011 - 2012, Met Office
#
# This file is part of cartopy.
#
# cartopy is free software: you can redistribute it and/or modify it under
# the terms of the GNU Lesser General Public License as published by the
# Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# cartopy is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Lesser General Public License for more details.
#
# You should have received a copy of the GNU Lesser General Public License
# along with cartopy.  If not, see <http://www.gnu.org/licenses/>.
from __future__ import absolute_import

import contextlib
import os
import shutil
import tempfile
import warnings

from nose.tools import assert_equal, assert_raises

import cartopy
import cartopy.io as cio
from cartopy.io.shapereader import NEShpDownloader
from cartopy.tests.mpl.test_caching import CallCounter


def test_Downloader_data():
    di = cio.Downloader('http://testing.com/{category}/{name}.zip',
                        os.path.join('{data_dir}', '{category}',
                                     'shape.shp'),
                        '/project/foobar/{category}/sample.shp')

    replacement_dict = {'category': 'example',
                        'name': 'test',
                        'data_dir': os.path.join('/wibble', 'foo', 'bar')}

    assert_equal(di.url(replacement_dict),
                 'http://testing.com/example/test.zip')

    assert_equal(di.target_path(replacement_dict),
                 os.path.join('/wibble', 'foo', 'bar', 'example', 'shape.shp')
                 )

    assert_equal(di.pre_downloaded_path(replacement_dict),
                 '/project/foobar/example/sample.shp'
                 )


@contextlib.contextmanager
def config_replace(replacement_dict):
    """
    Provides a context manager to replace the ``cartopy.config['downloaders']``
    dict with the given dictionary. Great for testing purposes!

    """
    downloads_orig = cartopy.config['downloaders']
    cartopy.config['downloaders'] = replacement_dict
    yield
    cartopy.config['downloaders'] = downloads_orig


@contextlib.contextmanager
def download_to_temp():
    """
    Context manager which defaults the "data_dir" to a temporary directory
    which is automatically cleaned up on exit.

    """
    old_downloads_dict = cartopy.config['downloaders'].copy()
    old_dir = cartopy.config['data_dir']

    tmp_dir = tempfile.mkdtemp(suffix='_cartopy_data')
    cartopy.config['data_dir'] = tmp_dir
    try:
        yield tmp_dir
        cartopy.config['downloaders'] = old_downloads_dict
        cartopy.config['data_dir'] = old_dir
    finally:
        shutil.rmtree(tmp_dir)


def test_from_config():
    generic_url = 'http://example.com/generic_ne/{name}.zip'

    land_downloader = cio.Downloader(generic_url, '', '')
    generic_ne_downloader = cio.Downloader(generic_url, '', '')

    ocean_spec = ('shapefile', 'natural_earth', '110m', 'physical', 'ocean')
    land_spec = ('shapefile', 'natural_earth', '110m', 'physical', 'land')
    generic_spec = ('shapefile', 'natural_earth')

    target_config = {land_spec: land_downloader,
                     generic_spec: generic_ne_downloader,
                     }

    with config_replace(target_config):
        # ocean spec is not explicitly in the config, but a subset of it is,
        # so check that an appropriate downloader is returned
        r = cio.Downloader.from_config(ocean_spec)

        # check the resulting download item produces a sensible url.
        assert_equal(r.url({'name': 'ocean'}),
                     'http://example.com/generic_ne/ocean.zip')

        downloaders = cio.config['downloaders']

        r = cio.Downloader.from_config(land_spec)
        assert r is land_downloader


def test_downloading_simple_ascii():
    # downloads a file from the Google APIs. (very high uptime and file will
    # always be there - if this goes down, most of the internet would break!)
    # to test the downloading mechanisms.
    file_url = 'http://ajax.googleapis.com/ajax/libs/jquery/1.8.2/{name}.js'

    format_dict = {'name': 'jquery'}

    with download_to_temp() as tmp_dir:
        target_template = os.path.join(tmp_dir, '{name}.txt')
        tmp_fname = target_template.format(**format_dict)

        dnld_item = cio.Downloader(file_url, target_template)

        assert_equal(dnld_item.target_path(format_dict), tmp_fname)

        with warnings.catch_warnings(record=True) as w:
            assert_equal(dnld_item.path(format_dict), tmp_fname)

            assert len(w) == 1, ('Expected a single download warning to be '
                                 'raised. Got {}.'.format(len(w)))
            assert issubclass(w[0].category, cio.DownloadWarning)

        with open(tmp_fname, 'r') as fh:
            _ = fh.readline()
            assert_equal(" * jQuery JavaScript Library v1.8.2\n",
                         fh.readline())

        # check that calling path again doesn't try re-downloading
        with CallCounter(dnld_item, 'acquire_resource') as counter:
            assert_equal(dnld_item.path(format_dict), tmp_fname)
        assert counter.count == 0, 'Item was re-downloaded.'


def test_natural_earth_downloader():
    # downloads a file to a temporary location, and uses that temporary
    # location, then:
    #   * Checks that the file is only downloaded once even when calling
    #     multiple times
    #   * Checks that shapefiles have all the necessary files when downloaded
    #   * Checks that providing a path in a download item gets used rather
    #     than triggering another download

    tmp_dir = tempfile.mkdtemp()

    shp_path_template = os.path.join(tmp_dir,
                                     '{category}_{resolution}_{name}.shp')

    # picking a small-ish file to speed up download times, the file itself
    # isn't important - it is the download mechanism that is.
    format_dict = {'category': 'physical',
                   'name': 'rivers_lake_centerlines',
                   'resolution': '110m'}

    try:
        dnld_item = NEShpDownloader(target_path_template=shp_path_template)

        # check that the file gets downloaded the first time path is called
        with CallCounter(dnld_item, 'acquire_resource') as counter:
            shp_path = dnld_item.path(format_dict)
        assert counter.count == 1, 'Item not downloaded.'

        assert_equal(shp_path_template.format(**format_dict), shp_path)

        # check that calling path again doesn't try re-downloading
        with CallCounter(dnld_item, 'acquire_resource') as counter:
            assert_equal(dnld_item.path(format_dict), shp_path)
        assert counter.count == 0, 'Item was re-downloaded.'

        # check that we have the shp and the shx
        exts = ['.shp', '.shx']
        for ext in exts:
            stem = os.path.splitext(shp_path)[0]
            msg = "Shapefile's {0} file doesn't exist in {1}{0}".format(ext,
                                                                        stem)
            assert os.path.exists(stem + ext), msg

        # check that providing a pre downloaded path actually works
        pre_dnld = NEShpDownloader(target_path_template='/not/a/real/file.txt',
                                   pre_downloaded_path_template=shp_path
                                   )
        # check that the pre_dnld downloader doesn't re-download, but instead
        # uses the path of the previously downloaded item

        with CallCounter(pre_dnld, 'acquire_resource') as counter:
            assert_equal(pre_dnld.path(format_dict), shp_path)
        assert counter.count == 0, 'Aquire resource called more than once.'

    finally:
        shutil.rmtree(tmp_dir)


if __name__ == '__main__':
    import nose
    nose.runmodule(argv=['-s', '--with-doctest'], exit=False)

########NEW FILE########
__FILENAME__ = test_ogc_clients
# (C) British Crown Copyright 2011 - 2012, Met Office
#
# This file is part of cartopy.
#
# cartopy is free software: you can redistribute it and/or modify it under
# the terms of the GNU Lesser General Public License as published by the
# Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# cartopy is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Lesser General Public License for more details.
#
# You should have received a copy of the GNU Lesser General Public License
# along with cartopy.  If not, see <http://www.gnu.org/licenses/>.
from __future__ import absolute_import

import cartopy.io.ogc_clients as ogc
from owslib.wms import WebMapService
from owslib.wmts import WebMapTileService
import unittest
import cartopy.crs as ccrs
import numpy as np


class test_WMSRasterSource(unittest.TestCase):
    URI = 'http://vmap0.tiles.osgeo.org/wms/vmap0'
    layer = 'basic'
    layers = ['basic', 'ocean']
    projection = ccrs.PlateCarree()

    def test_string_service(self):
        source = ogc.WMSRasterSource(self.URI, self.layer)
        self.assertIsInstance(source.service, WebMapService)
        self.assertIsInstance(source.layers, list)
        self.assertEqual(source.layers, [self.layer])

    def test_wms_service_instance(self):
        service = WebMapService(self.URI)
        source = ogc.WMSRasterSource(service, self.layer)
        self.assertIs(source.service, service)

    def test_multiple_layers(self):
        source = ogc.WMSRasterSource(self.URI, self.layers)
        self.assertEqual(source.layers, self.layers)

    def test_no_layers(self):
        msg = 'One or more layers must be defined.'
        with self.assertRaisesRegexp(ValueError, msg):
            ogc.WMSRasterSource(self.URI, [])

    def test_extra_kwargs_empty(self):
        source = ogc.WMSRasterSource(self.URI, self.layer,
                                     getmap_extra_kwargs={})
        self.assertEqual(source.getmap_extra_kwargs, {})

    def test_extra_kwargs_None(self):
        source = ogc.WMSRasterSource(self.URI, self.layer,
                                     getmap_extra_kwargs=None)
        self.assertEqual(source.getmap_extra_kwargs, {'transparent': True})

    def test_extra_kwargs_non_empty(self):
        kwargs = {'another': 'kwarg'}
        source = ogc.WMSRasterSource(self.URI, self.layer,
                                     getmap_extra_kwargs=kwargs)
        self.assertEqual(source.getmap_extra_kwargs, kwargs)

    def test_supported_projection(self):
        source = ogc.WMSRasterSource(self.URI, self.layer)
        source.validate_projection(self.projection)

    def test_unsupported_projection(self):
        source = ogc.WMSRasterSource(self.URI, self.layer)
        msg = 'was not convertible to a suitable WMS SRS.'
        with self.assertRaisesRegexp(ValueError, msg):
            source.validate_projection(ccrs.Miller())

    def test_fetch_img(self):
        source = ogc.WMSRasterSource(self.URI, self.layer)
        extent = [-10, 10, 40, 60]
        img, extent_out = source.fetch_raster(self.projection, extent,
                                              (30, 30))
        img = np.array(img)
        self.assertEqual(img.shape, (30, 30, 4))
        # No transparency in this image.
        self.assertEqual(img[:, :, 3].min(), 255)
        self.assertEqual(extent, extent_out)


class test_WMTSRasterSource(unittest.TestCase):
    URI = 'http://map1c.vis.earthdata.nasa.gov/wmts-geo/wmts.cgi'
    layer_name = 'VIIRS_CityLights_2012'
    projection = ccrs.PlateCarree()

    def test_string_service(self):
        source = ogc.WMTSRasterSource(self.URI, self.layer_name)
        self.assertIsInstance(source.wmts, WebMapTileService)
        self.assertIsInstance(source.layer_name, basestring)
        self.assertEqual(source.layer_name, self.layer_name)

    def test_wmts_service_instance(self):
        service = WebMapTileService(self.URI)
        source = ogc.WMTSRasterSource(service, self.layer_name)
        self.assertIs(source.wmts, service)

    def test_supported_projection(self):
        source = ogc.WMTSRasterSource(self.URI, self.layer_name)
        source.validate_projection(self.projection)

    def test_unsupported_projection(self):
        source = ogc.WMTSRasterSource(self.URI, self.layer_name)
        msg = 'Unable to find tile matrix for projection.'
        with self.assertRaisesRegexp(ValueError, msg):
            source.validate_projection(ccrs.Miller())

    def test_fetch_img(self):
        source = ogc.WMTSRasterSource(self.URI, self.layer_name)
        extent = [-10, 10, 40, 60]
        img, extent_out = source.fetch_raster(self.projection, extent,
                                              (30, 30))
        img = np.array(img)
        self.assertEqual(img.shape, (512, 512, 4))
        # No transparency in this image.
        self.assertEqual(img[:, :, 3].min(), 255)
        self.assertEqual((-180.0, 107.99999999999994,
                          -197.99999999999994, 90.0), extent_out)


if __name__ == '__main__':
    import nose
    nose.runmodule(argv=['-sv', '--with-doctest'], exit=False)

########NEW FILE########
__FILENAME__ = test_srtm
# (C) British Crown Copyright 2011 - 2012, Met Office
#
# This file is part of cartopy.
#
# cartopy is free software: you can redistribute it and/or modify it under
# the terms of the GNU Lesser General Public License as published by the
# Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# cartopy is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Lesser General Public License for more details.
#
# You should have received a copy of the GNU Lesser General Public License
# along with cartopy.  If not, see <http://www.gnu.org/licenses/>.
from __future__ import absolute_import

import warnings

import cartopy.io.srtm
from cartopy.tests.io.test_downloaders import download_to_temp


def test_srtm3_retrieve():
    # test that the download mechanism for srtm3 works
    with download_to_temp() as tmp_dir:
        with warnings.catch_warnings(record=True) as w:
            r = cartopy.io.srtm.SRTM3_retrieve(-4, 50)
            assert len(w) == 1
            assert issubclass(w[0].category, cartopy.io.DownloadWarning)

        assert r.startswith(tmp_dir), 'File not downloaded to tmp dir'

        img, _, _ = cartopy.io.srtm.read_SRTM3(r)

        # check that the data is fairly sensible
        msg = 'srtm data has changed. arbitrary value testing failed.'
        assert img.max() == 602, msg
        assert img.min() == -32768, msg
        assert img[-10, 12] == 78, msg + 'Got {}'.format(img[-10, 12])


if __name__ == '__main__':
    import nose
    nose.runmodule(argv=['-sv', '--with-doctest'], exit=False)

########NEW FILE########
__FILENAME__ = test_axes
# (C) British Crown Copyright 2011 - 2012, Met Office
#
# This file is part of cartopy.
#
# cartopy is free software: you can redistribute it and/or modify it under
# the terms of the GNU Lesser General Public License as published by the
# Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# cartopy is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Lesser General Public License for more details.
#
# You should have received a copy of the GNU Lesser General Public License
# along with cartopy.  If not, see <http://www.gnu.org/licenses/>.

import unittest


import matplotlib.path as mpath
import matplotlib.pyplot as plt
from nose.tools import assert_equal
import numpy as np


import cartopy.crs as ccrs
from cartopy.mpl.geoaxes import InterProjectionTransform
from .test_caching import CallCounter


class TestNoSpherical(unittest.TestCase):
    def setUp(self):
        self.ax = plt.axes(projection=ccrs.PlateCarree())
        self.data = np.arange(12).reshape((3, 4))

    def tearDown(self):
        plt.clf()
        plt.close()

    def test_contour(self):
        with self.assertRaises(ValueError):
            self.ax.contour(self.data, transform=ccrs.Geodetic())

    def test_contourf(self):
        with self.assertRaises(ValueError):
            self.ax.contourf(self.data, transform=ccrs.Geodetic())

    def test_pcolor(self):
        with self.assertRaises(ValueError):
            self.ax.pcolor(self.data, transform=ccrs.Geodetic())

    def test_pcolormesh(self):
        with self.assertRaises(ValueError):
            self.ax.pcolormesh(self.data, transform=ccrs.Geodetic())


def test_transform_PlateCarree_shortcut():
    src = ccrs.PlateCarree(central_longitude=0)
    target = ccrs.PlateCarree(central_longitude=180)

    # of the 3 paths, 2 of them cannot be short-cutted.
    pth1 = mpath.Path([[0.5, 0], [10, 10]])
    pth2 = mpath.Path([[0.5, 91], [10, 10]])
    pth3 = mpath.Path([[-0.5, 0], [10, 10]])

    trans = InterProjectionTransform(src, target)

    counter = CallCounter(target, 'project_geometry')

    with counter:
        trans.transform_path(pth1)
        # pth1 should allow a short-cut.
        assert_equal(counter.count, 0)

    with counter:
        trans.transform_path(pth2)
        assert_equal(counter.count, 1)

    with counter:
        trans.transform_path(pth3)
        assert_equal(counter.count, 2)


if __name__ == '__main__':
    import nose
    nose.runmodule(argv=['-s', '--with-doctest'], exit=False)

########NEW FILE########
__FILENAME__ = test_caching
# (C) British Crown Copyright 2011 - 2012, Met Office
#
# This file is part of cartopy.
#
# cartopy is free software: you can redistribute it and/or modify it under
# the terms of the GNU Lesser General Public License as published by the
# Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# cartopy is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Lesser General Public License for more details.
#
# You should have received a copy of the GNU Lesser General Public License
# along with cartopy.  If not, see <http://www.gnu.org/licenses/>.
import gc

from owslib.wmts import WebMapTileService
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from matplotlib.collections import PatchCollection
from matplotlib.path import Path
import shapely.geometry

import cartopy.crs as ccrs
from cartopy.mpl.feature_artist import FeatureArtist
from cartopy.io.ogc_clients import WMTSRasterSource
import cartopy.io.shapereader
import cartopy.mpl.geoaxes as cgeoaxes
import cartopy.mpl.patch
from cartopy.examples.waves import sample_data


class CallCounter(object):
    """
    Exposes a context manager which can count the number of calls to a specific
    function. (useful for cache checking!)

    Internally, the target function is replaced with a new one created
    by this context manager which then increments ``self.count`` every
    time it is called.

    Example usage::

        show_counter = CallCounter(plt, 'show')
        with show_counter:
            plt.show()
            plt.show()
            plt.show()

        print show_counter.count    # <--- outputs 3


    """
    def __init__(self, parent, function_name):
        self.count = 0
        self.parent = parent
        self.function_name = function_name
        self.orig_fn = getattr(parent, function_name)

    def __enter__(self):
        def replacement_fn(*args, **kwargs):
            self.count += 1
            return self.orig_fn(*args, **kwargs)

        setattr(self.parent, self.function_name, replacement_fn)
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        setattr(self.parent, self.function_name, self.orig_fn)


def test_coastline_loading_cache():
    # a5caae040ee11e72a62a53100fe5edc355304419 added coastline caching.
    # This test ensures it is working.

    # Create coastlines to ensure they are cached.
    ax1 = plt.subplot(2, 1, 1, projection=ccrs.PlateCarree())
    ax1.coastlines()
    plt.draw()
    # Create another instance of the coastlines and count
    # the number of times shapereader.Reader is created.
    counter = CallCounter(cartopy.io.shapereader.Reader, '__init__')
    with counter:
        ax2 = plt.subplot(2, 1, 1, projection=ccrs.Robinson())
        ax2.coastlines()
        plt.draw()

    assert counter.count == 0, ('The shapereader Reader class was created {} '
                                'times, indicating that the caching is not '
                                'working.'.format(counter.count))

    plt.close()


def test_shapefile_transform_cache():
    # a5caae040ee11e72a62a53100fe5edc355304419 added shapefile mpl
    # geometry caching based on geometry object id. This test ensures
    # it is working.
    coastline_path = cartopy.io.shapereader.natural_earth(resolution="50m",
                                                          category='physical',
                                                          name='coastline')
    geoms = cartopy.io.shapereader.Reader(coastline_path).geometries()
    # Use the first 10 of them.
    geoms = tuple(geoms)[:10]
    n_geom = len(geoms)

    ax = plt.axes(projection=ccrs.Robinson())

    # Empty the cache.
    FeatureArtist._geometry_to_path_cache.clear()
    assert len(FeatureArtist._geometry_to_path_cache) == 0

    counter = CallCounter(ax.projection, 'project_geometry')
    with counter:
        ax.add_geometries(geoms, ccrs.PlateCarree())
        ax.add_geometries(geoms, ccrs.PlateCarree())
        ax.add_geometries(geoms[:], ccrs.PlateCarree())
        plt.draw()

    # Without caching the count would have been
    # n_calls * n_geom, but should now be just n_geom.
    assert counter.count == n_geom, ('The given geometry was transformed too '
                                     'many times (expected: %s; got %s) - the'
                                     ' caching is not working.'
                                     ''.format(n_geom, n_geom, counter.count))

    # Check the cache has an entry for each geometry.
    assert len(FeatureArtist._geometry_to_path_cache) == n_geom

    # Check that the cache is empty again once we've dropped all references
    # to the source paths.
    plt.clf()
    del geoms
    gc.collect()
    assert len(FeatureArtist._geometry_to_path_cache) == 0

    plt.close()


def test_contourf_transform_path_counting():
    ax = plt.axes(projection=ccrs.Robinson())
    plt.draw()

    # Capture the size of the cache before our test.
    gc.collect()
    initial_cache_size = len(cgeoaxes._PATH_TRANSFORM_CACHE)

    path_to_geos_counter = CallCounter(cartopy.mpl.patch, 'path_to_geos')
    with path_to_geos_counter:
        x, y, z = sample_data((30, 60))
        cs = plt.contourf(x, y, z, 5, transform=ccrs.PlateCarree())
        n_geom = sum([len(c.get_paths()) for c in cs.collections])
        del cs, c
        plt.draw()

    # Before the performance enhancement, the count would have been 2 * n_geom,
    # but should now be just n_geom.
    msg = ('The given geometry was transformed too many times (expected: %s; '
           'got %s) - the caching is not working.'
           '' % (n_geom, path_to_geos_counter.count))
    assert path_to_geos_counter.count == n_geom, msg

    # Check the cache has an entry for each geometry.
    assert len(cgeoaxes._PATH_TRANSFORM_CACHE) == initial_cache_size + n_geom

    # Check that the cache is empty again once we've dropped all references
    # to the source paths.
    plt.clf()
    gc.collect()
    assert len(cgeoaxes._PATH_TRANSFORM_CACHE) == initial_cache_size

    plt.close()


def test_wmts_tile_caching():
    image_cache = WMTSRasterSource._shared_image_cache
    image_cache.clear()
    assert len(image_cache) == 0

    url = 'http://map1c.vis.earthdata.nasa.gov/wmts-geo/wmts.cgi'
    wmts = WebMapTileService(url)
    layer_name = 'MODIS_Terra_CorrectedReflectance_TrueColor'

    source = WMTSRasterSource(wmts, layer_name)

    gettile_counter = CallCounter(wmts, 'gettile')
    crs = ccrs.PlateCarree()
    extent = (-180, 180, -90, 90)
    resolution = (20, 10)
    with gettile_counter:
        source.fetch_raster(crs, extent, resolution)
    n_tiles = 2
    assert gettile_counter.count == n_tiles, ('Too many tile requests - '
                                              'expected {}, got {}.'.format(
                                                  n_tiles,
                                                  gettile_counter.count)
                                              )
    gc.collect()
    assert len(image_cache) == 1
    assert len(image_cache[wmts]) == 1
    tiles_key = (layer_name, '0')
    assert len(image_cache[wmts][tiles_key]) == n_tiles

    # Second time around we shouldn't request any more tiles so the
    # call count will stay the same.
    with gettile_counter:
        source.fetch_raster(crs, extent, resolution)
    assert gettile_counter.count == n_tiles, ('Too many tile requests - '
                                              'expected {}, got {}.'.format(
                                                  n_tiles,
                                                  gettile_counter.count)
                                              )
    gc.collect()
    assert len(image_cache) == 1
    assert len(image_cache[wmts]) == 1
    tiles_key = (layer_name, '0')
    assert len(image_cache[wmts][tiles_key]) == n_tiles

    # Once there are no live references the weak-ref cache should clear.
    del source, wmts, gettile_counter
    gc.collect()
    assert len(image_cache) == 0


if __name__ == '__main__':
    import nose
    nose.runmodule(argv=['-s', '--with-doctest'], exit=False)

########NEW FILE########
__FILENAME__ = test_crs
# (C) British Crown Copyright 2013, Met Office
#
# This file is part of cartopy.
#
# cartopy is free software: you can redistribute it and/or modify it under
# the terms of the GNU Lesser General Public License as published by the
# Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# cartopy is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Lesser General Public License for more details.
#
# You should have received a copy of the GNU Lesser General Public License
# along with cartopy.  If not, see <http://www.gnu.org/licenses/>.

import matplotlib.pyplot as plt

import cartopy.crs as ccrs
from cartopy.tests.mpl import ImageTesting


@ImageTesting(['lambert_conformal_south'])
def test_lambert_south():
    # Reference image: http://www.icsm.gov.au/mapping/map_projections.html
    crs = ccrs.LambertConformal(central_longitude=140, cutoff=65,
                                secant_latitudes=(-30, -60))
    ax = plt.axes(projection=crs)
    ax.coastlines()
    ax.gridlines()


@ImageTesting(['mercator_squashed'])
def test_mercator_squashed():
    globe = ccrs.Globe(semimajor_axis=10000, semiminor_axis=9000,
                       ellipse=None)
    crs = ccrs.Mercator(globe=globe, min_latitude=-40, max_latitude=40)
    ax = plt.axes(projection=crs)
    ax.coastlines()
    ax.gridlines()


if __name__ == '__main__':
    import nose
    nose.runmodule(argv=['-s', '--with-doctest'], exit=False)

########NEW FILE########
__FILENAME__ = test_examples
# (C) British Crown Copyright 2011 - 2012, Met Office
#
# This file is part of cartopy.
#
# cartopy is free software: you can redistribute it and/or modify it under
# the terms of the GNU Lesser General Public License as published by the
# Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# cartopy is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Lesser General Public License for more details.
#
# You should have received a copy of the GNU Lesser General Public License
# along with cartopy.  If not, see <http://www.gnu.org/licenses/>.

import numpy as np
import matplotlib.pyplot as plt

from cartopy.tests.mpl import ImageTesting


class ExampleImageTesting(ImageTesting):
    """Subclasses ImageTesting to nullify the plt.show commands."""
    def __call__(self, test_func):
        fn = ImageTesting.__call__(self, test_func)

        def new_fn(*args, **kwargs):
            try:
                show = plt.show
                plt.show = lambda *args, **kwargs: None
                r = fn(*args, **kwargs)
            finally:
                plt.show = show
            return r

        new_fn.__name__ = fn.__name__
        return new_fn


@ExampleImageTesting(['global_map'])
def test_global_map():
    import cartopy.examples.global_map as c
    c.main()


if __name__ == '__main__':
    import nose
    nose.runmodule(argv=['-s', '--with-doctest'], exit=False)

########NEW FILE########
__FILENAME__ = test_features
# (C) British Crown Copyright 2011 - 2012, Met Office
#
# This file is part of cartopy.
#
# cartopy is free software: you can redistribute it and/or modify it under
# the terms of the GNU Lesser General Public License as published by the
# Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# cartopy is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Lesser General Public License for more details.
#
# You should have received a copy of the GNU Lesser General Public License
# along with cartopy.  If not, see <http://www.gnu.org/licenses/>.

import matplotlib.pyplot as plt

import cartopy.crs as ccrs
import cartopy.feature as cfeature

from cartopy.tests.mpl import ImageTesting


@ImageTesting(['natural_earth'])
def test_natural_earth():
    ax = plt.axes(projection=ccrs.PlateCarree())
    ax.add_feature(cfeature.LAND)
    ax.add_feature(cfeature.OCEAN)
    ax.coastlines()
    ax.add_feature(cfeature.BORDERS, linestyle=':')
    ax.add_feature(cfeature.LAKES, alpha=0.5)
    ax.add_feature(cfeature.RIVERS)
    ax.set_xlim((-20, 60))
    ax.set_ylim((-40, 40))


@ImageTesting(['natural_earth_custom'])
def test_natural_earth_custom():
    ax = plt.axes(projection=ccrs.PlateCarree())
    feature = cfeature.NaturalEarthFeature('physical', 'coastline', '50m',
                                           edgecolor='black',
                                           facecolor='none')
    ax.add_feature(feature)
    ax.set_xlim((-26, -12))
    ax.set_ylim((58, 72))


@ImageTesting(['gshhs_coastlines'])
def test_gshhs():
    ax = plt.axes(projection=ccrs.Mollweide())
    ax.set_extent([138, 142, 32, 42], ccrs.Geodetic())

    ax.stock_img()
    # Draw coastlines.
    ax.add_feature(cfeature.GSHHSFeature('coarse', edgecolor='red'))
    # Draw higher resolution lakes (and test overriding of kwargs)
    ax.add_feature(cfeature.GSHHSFeature('low', levels=[2],
                                         facecolor='green'), facecolor='blue')


if __name__ == '__main__':
    import nose
    nose.runmodule(argv=['-s', '--with-doctest'], exit=False)

########NEW FILE########
__FILENAME__ = test_gridliner
# (C) British Crown Copyright 2011 - 2014, Met Office
#
# This file is part of cartopy.
#
# cartopy is free software: you can redistribute it and/or modify it under
# the terms of the GNU Lesser General Public License as published by the
# Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# cartopy is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Lesser General Public License for more details.
#
# You should have received a copy of the GNU Lesser General Public License
# along with cartopy.  If not, see <http://www.gnu.org/licenses/>.

import unittest
import warnings

import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
from nose.tools import assert_raises

import cartopy.crs as ccrs
from cartopy.tests.mpl import ImageTesting
from cartopy.mpl.gridliner import LATITUDE_FORMATTER, LONGITUDE_FORMATTER


@ImageTesting(['gridliner1'])
def test_gridliner():
    ny, nx = 2, 4

    plt.figure(figsize=(10, 10))

    ax = plt.subplot(nx, ny, 1, projection=ccrs.PlateCarree())
    ax.set_global()
    ax.coastlines()
    ax.gridlines()

    ax = plt.subplot(nx, ny, 2, projection=ccrs.OSGB())
    ax.set_global()
    ax.coastlines()
    ax.gridlines()

    ax = plt.subplot(nx, ny, 3, projection=ccrs.OSGB())
    ax.set_global()
    ax.coastlines()
    ax.gridlines(ccrs.PlateCarree(), color='blue', linestyle='-')
    ax.gridlines(ccrs.OSGB())

    ax = plt.subplot(nx, ny, 4, projection=ccrs.PlateCarree())
    ax.set_global()
    ax.coastlines()
    ax.gridlines(ccrs.NorthPolarStereo(), alpha=0.5,
                 linewidth=1.5, linestyle='-')

    ax = plt.subplot(nx, ny, 5, projection=ccrs.PlateCarree())
    ax.set_global()
    ax.coastlines()
    osgb = ccrs.OSGB()
    ax.set_extent(tuple(osgb.x_limits) + tuple(osgb.y_limits), crs=osgb)
    ax.gridlines(osgb)

    ax = plt.subplot(nx, ny, 6, projection=ccrs.NorthPolarStereo())
    ax.set_global()
    ax.coastlines()
    ax.gridlines(alpha=0.5, linewidth=1.5, linestyle='-')

    ax = plt.subplot(nx, ny, 7, projection=ccrs.NorthPolarStereo())
    ax.set_global()
    ax.coastlines()
    osgb = ccrs.OSGB()
    ax.set_extent(tuple(osgb.x_limits) + tuple(osgb.y_limits), crs=osgb)
    ax.gridlines(osgb)

    ax = plt.subplot(nx, ny, 8,
                     projection=ccrs.Robinson(central_longitude=135))
    ax.set_global()
    ax.coastlines()
    ax.gridlines(ccrs.PlateCarree(), alpha=0.5, linewidth=1.5, linestyle='-')

    delta = 1.5e-2
    plt.subplots_adjust(left=0 + delta, right=1 - delta,
                        top=1 - delta, bottom=0 + delta)


# The tolerance on this test is particularly high because of the high number
# of text objects. A new testing stratergy is needed for this kind of test.
@ImageTesting(['gridliner_labels'], tolerance=2.6)
def test_grid_labels():
    plt.figure(figsize=(8, 10))

    crs_pc = ccrs.PlateCarree()
    crs_merc = ccrs.Mercator()
    crs_osgb = ccrs.OSGB()

    ax = plt.subplot(3, 2, 1, projection=crs_pc)
    ax.coastlines()
    ax.gridlines(draw_labels=True)

    # Check that adding labels to Mercator gridlines gives an error.
    # (Currently can only label PlateCarree gridlines.)
    ax = plt.subplot(3, 2, 2,
                     projection=ccrs.PlateCarree(central_longitude=180))
    ax.coastlines()
    with assert_raises(TypeError):
        ax.gridlines(crs=crs_merc, draw_labels=True)

    ax.set_title('Known bug')
    gl = ax.gridlines(crs=crs_pc, draw_labels=True)
    gl.xlabels_top = False
    gl.ylabels_left = False
    gl.xlines = False

    ax = plt.subplot(3, 2, 3, projection=crs_merc)
    ax.coastlines()
    ax.gridlines(draw_labels=True)

    # Check that labelling the gridlines on an OSGB plot gives an error.
    # (Currently can only draw these on PlateCarree or Mercator plots.)
    ax = plt.subplot(3, 2, 4, projection=crs_osgb)
    ax.coastlines()
    with assert_raises(TypeError):
        ax.gridlines(draw_labels=True)

    ax = plt.subplot(3, 2, 4, projection=crs_pc)
    ax.coastlines()
    gl = ax.gridlines(
        crs=crs_pc, linewidth=2, color='gray', alpha=0.5, linestyle='--')
    gl.xlabels_bottom = True
    gl.ylabels_right = True
    gl.xlines = False
    gl.xlocator = mticker.FixedLocator([-180, -45, 45, 180])
    gl.xformatter = LONGITUDE_FORMATTER
    gl.yformatter = LATITUDE_FORMATTER
    gl.xlabel_style = {'size': 15, 'color': 'gray'}
    gl.xlabel_style = {'color': 'red'}

    # trigger a draw at this point and check the appropriate artists are
    # populated on the gridliner instance
    plt.draw()
    assert len(gl.xlabel_artists) == 4
    assert len(gl.ylabel_artists) == 5
    assert len(gl.ylabel_artists) == 5
    assert len(gl.xline_artists) == 0

    ax = plt.subplot(3, 2, 5, projection=crs_pc)
    ax.set_extent([-20, 10.0, 45.0, 70.0])
    ax.coastlines()
    ax.gridlines(draw_labels=True)

    ax = plt.subplot(3, 2, 6, projection=crs_merc)
    ax.set_extent([-20, 10.0, 45.0, 70.0], crs=crs_pc)
    ax.coastlines()
    ax.gridlines(draw_labels=True)

    # Increase margins between plots to stop them bumping into one another.
    plt.subplots_adjust(wspace=0.25, hspace=0.25)


if __name__ == '__main__':
    import nose
    nose.runmodule(argv=['-s', '--with-doctest'], exit=False)

########NEW FILE########
__FILENAME__ = test_images
# (C) British Crown Copyright 2011 - 2014, Met Office
#
# This file is part of cartopy.
#
# cartopy is free software: you can redistribute it and/or modify it under
# the terms of the GNU Lesser General Public License as published by the
# Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# cartopy is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Lesser General Public License for more details.
#
# You should have received a copy of the GNU Lesser General Public License
# along with cartopy.  If not, see <http://www.gnu.org/licenses/>.

import os
import types

import numpy as np
import matplotlib.pyplot as plt
import PIL.Image
import shapely.geometry

from cartopy import config
import cartopy.crs as ccrs
import cartopy.io.img_tiles as cimgt

from cartopy.tests.mpl import ImageTesting
import cartopy.tests.test_img_nest as ctest_nest
import cartopy.tests.test_img_tiles as ctest_tiles


NATURAL_EARTH_IMG = os.path.join(config["repo_data_dir"],
                                 'raster', 'natural_earth',
                                 '50-natural-earth-1-downsampled.png')
REGIONAL_IMG = os.path.join(config['repo_data_dir'], 'raster', 'sample',
                            'Miriam.A2012270.2050.2km.jpg')


@ImageTesting(['web_tiles'])
def test_web_tiles():
    extent = [-15, 0.1, 50, 60]
    target_domain = shapely.geometry.Polygon([[extent[0], extent[1]],
                                              [extent[2], extent[1]],
                                              [extent[2], extent[3]],
                                              [extent[0], extent[3]],
                                              [extent[0], extent[1]]])
    map_prj = cimgt.GoogleTiles().crs

    ax = plt.subplot(3, 2, 1, projection=map_prj)
    gt = cimgt.GoogleTiles()
    gt._image_url = types.MethodType(ctest_tiles.GOOGLE_IMAGE_URL_REPLACEMENT,
                                     gt)
    img, extent, origin = gt.image_for_domain(target_domain, 1)
    ax.imshow(np.array(img), extent=extent, transform=gt.crs,
              interpolation='bilinear', origin=origin)
    ax.coastlines(color='white')

    ax = plt.subplot(3, 2, 2, projection=map_prj)
    qt = cimgt.QuadtreeTiles()
    img, extent, origin = qt.image_for_domain(target_domain, 1)
    ax.imshow(np.array(img), extent=extent, transform=qt.crs,
              interpolation='bilinear', origin=origin)
    ax.coastlines(color='white')

    ax = plt.subplot(3, 2, 3, projection=map_prj)
    mq_osm = cimgt.MapQuestOSM()
    img, extent, origin = mq_osm.image_for_domain(target_domain, 1)
    ax.imshow(np.array(img), extent=extent, transform=mq_osm.crs,
              interpolation='bilinear', origin=origin)
    ax.coastlines()

    ax = plt.subplot(3, 2, 4, projection=map_prj)
    mq_oa = cimgt.MapQuestOpenAerial()
    img, extent, origin = mq_oa.image_for_domain(target_domain, 1)
    ax.imshow(np.array(img), extent=extent, transform=mq_oa.crs,
              interpolation='bilinear', origin=origin)
    ax.coastlines()

    ax = plt.subplot(3, 2, 5, projection=map_prj)
    osm = cimgt.OSM()
    img, extent, origin = osm.image_for_domain(target_domain, 1)
    ax.imshow(np.array(img), extent=extent, transform=osm.crs,
              interpolation='bilinear', origin=origin)
    ax.coastlines()


@ImageTesting(['image_nest'], tolerance=17)
def test_image_nest():
    nest_z0_z1 = ctest_nest.gen_nest()

    ax = plt.axes(projection=ccrs.Mercator())
    shper_globe = ccrs.Globe(semimajor_axis=np.rad2deg(1))
    spher_merc = ccrs.Mercator(globe=shper_globe)
    ax.set_extent([-45, 45, -45, 90], spher_merc)
    ax.coastlines()
    ax.add_image(nest_z0_z1, 'aerial z1 test')


@ImageTesting(['image_merge'])
def test_image_merge():
    # tests the basic image merging functionality
    tiles = []
    for i in range(1, 4):
        for j in range(0, 3):
            tiles.append((i, j, 2))

    gt = cimgt.GoogleTiles()
    gt._image_url = types.MethodType(ctest_tiles.GOOGLE_IMAGE_URL_REPLACEMENT,
                                     gt)
    images_to_merge = []
    for tile in tiles:
        img, extent, origin = gt.get_image(tile)
        img = np.array(img)
        x = np.linspace(extent[0], extent[1], img.shape[1], endpoint=False)
        y = np.linspace(extent[2], extent[3], img.shape[0], endpoint=False)
        images_to_merge.append([img, x, y, origin])

    img, extent, origin = cimgt._merge_tiles(images_to_merge)
    ax = plt.axes(projection=gt.crs)
    ax.set_global()
    ax.coastlines()
    plt.imshow(img, origin=origin, extent=extent, alpha=0.5)


@ImageTesting(['imshow_natural_earth_ortho'], tolerance=0.45)
def test_imshow():
    source_proj = ccrs.PlateCarree()
    img = plt.imread(NATURAL_EARTH_IMG)
    # Convert the image to a byte array, rather than float, which is the
    # form that JPG images would be loaded with imread.
    img = (img * 255).astype('uint8')
    ax = plt.axes(projection=ccrs.Orthographic())
    ax.imshow(img, origin='upper', transform=source_proj,
              extent=[-180, 180, -90, 90])


@ImageTesting(['imshow_regional_projected'])
def test_imshow_projected():
    source_proj = ccrs.PlateCarree()
    img_extent = (-120.67660000000001, -106.32104523100001,
                  13.2301484511245, 30.766899999999502)
    img = plt.imread(REGIONAL_IMG)
    ax = plt.axes(projection=ccrs.LambertConformal())
    ax.set_extent(img_extent, crs=source_proj)
    ax.coastlines(resolution='50m')
    ax.imshow(img, extent=img_extent, origin='upper', transform=source_proj)


@ImageTesting(['imshow_natural_earth_ortho'])
def test_stock_img():
    ax = plt.axes(projection=ccrs.Orthographic())
    ax.stock_img()


@ImageTesting(['imshow_natural_earth_ortho'], tolerance=0.44)
def test_pil_Image():
    img = PIL.Image.open(NATURAL_EARTH_IMG)
    source_proj = ccrs.PlateCarree()
    ax = plt.axes(projection=ccrs.Orthographic())
    ax.imshow(img, origin='upper', transform=source_proj,
              extent=[-180, 180, -90, 90])


if __name__ == '__main__':
    import nose
    nose.runmodule(argv=['-sv', '--with-doctest'], exit=False)

########NEW FILE########
__FILENAME__ = test_img_transform
# (C) British Crown Copyright 2011 - 2012, Met Office
#
# This file is part of cartopy.
#
# cartopy is free software: you can redistribute it and/or modify it under
# the terms of the GNU Lesser General Public License as published by the
# Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# cartopy is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Lesser General Public License for more details.
#
# You should have received a copy of the GNU Lesser General Public License
# along with cartopy.  If not, see <http://www.gnu.org/licenses/>.

import operator
import os
import unittest

import matplotlib
import matplotlib.pyplot as plt
import numpy as np

from cartopy import config
from cartopy.tests.mpl import ImageTesting
import cartopy.crs as ccrs
import cartopy.img_transform as im_trans


class TestRegrid(unittest.TestCase):
    def test_array_dims(self):
        # Source data
        source_nx = 100
        source_ny = 100
        source_x = np.linspace(-180.0,
                               180.0,
                               source_nx).astype(np.float64)
        source_y = np.linspace(-90, 90.0, source_ny).astype(np.float64)
        source_x, source_y = np.meshgrid(source_x, source_y)
        data = np.arange(source_nx * source_ny,
                         dtype=np.int32).reshape(source_ny, source_nx)
        source_cs = ccrs.Geodetic()

        # Target grid
        target_nx = 23
        target_ny = 45
        target_proj = ccrs.PlateCarree()
        target_x, target_y, extent = im_trans.mesh_projection(target_proj,
                                                              target_nx,
                                                              target_ny)

        # Perform regrid
        new_array = im_trans.regrid(data, source_x, source_y, source_cs,
                                    target_proj, target_x, target_y)

        # Check dimensions of return array
        self.assertEqual(new_array.shape, target_x.shape)
        self.assertEqual(new_array.shape, target_y.shape)
        self.assertEqual(new_array.shape, (target_ny, target_nx))

    def test_different_dims(self):
        # Source data
        source_nx = 100
        source_ny = 100
        source_x = np.linspace(-180.0, 180.0,
                               source_nx).astype(np.float64)
        source_y = np.linspace(-90, 90.0,
                               source_ny).astype(np.float64)
        source_x, source_y = np.meshgrid(source_x, source_y)
        data = np.arange(source_nx * source_ny,
                         dtype=np.int32).reshape(source_ny, source_nx)
        source_cs = ccrs.Geodetic()

        # Target grids (different shapes)
        target_x_shape = (23, 45)
        target_y_shape = (23, 44)
        target_x = np.arange(reduce(operator.mul, target_x_shape),
                             dtype=np.float64).reshape(target_x_shape)
        target_y = np.arange(reduce(operator.mul, target_y_shape),
                             dtype=np.float64).reshape(target_y_shape)
        target_proj = ccrs.PlateCarree()

        # Attempt regrid
        with self.assertRaises(ValueError):
            im_trans.regrid(data, source_x, source_y, source_cs,
                            target_proj, target_x, target_y)


@ImageTesting(['regrid_image'])
def test_regrid_image():
    # Source data
    fname = os.path.join(config["repo_data_dir"], 'raster', 'natural_earth',
                         '50-natural-earth-1-downsampled.png')
    nx = 720
    ny = 360
    source_proj = ccrs.PlateCarree()
    source_x, source_y, _ = im_trans.mesh_projection(source_proj, nx, ny)
    data = plt.imread(fname)
    # Flip vertically to match source_x/source_y orientation
    data = data[::-1]

    # Target grid
    target_nx = 300
    target_ny = 300
    target_proj = ccrs.InterruptedGoodeHomolosine()
    target_x, target_y, target_extent = im_trans.mesh_projection(target_proj,
                                                                 target_nx,
                                                                 target_ny)

    # Perform regrid
    new_array = im_trans.regrid(data, source_x, source_y, source_proj,
                                target_proj, target_x, target_y)

    # Plot
    fig = plt.figure(figsize=(10, 10))
    gs = matplotlib.gridspec.GridSpec(nrows=4, ncols=1,
                                      hspace=1.5, wspace=0.5)
    # Set up axes and title
    ax = plt.subplot(gs[0], frameon=False, projection=target_proj)
    plt.imshow(new_array, origin='lower', extent=target_extent)
    ax.coastlines()
    # Plot each color slice (tests masking)
    cmaps = {'red': 'Reds', 'green': 'Greens', 'blue': 'Blues'}
    for i, color in enumerate(['red', 'green', 'blue']):
        ax = plt.subplot(gs[i + 1], frameon=False, projection=target_proj)
        ax.set_title(color)
        plt.imshow(new_array[:, :, i], extent=target_extent, origin='lower',
                   cmap=cmaps[color])
        ax.coastlines()

    # Tighten up layout
    gs.tight_layout(plt.gcf())


if __name__ == '__main__':
    import nose
    nose.runmodule(argv=['-s', '--with-doctest'], exit=False)

########NEW FILE########
__FILENAME__ = test_mpl_integration
# (C) British Crown Copyright 2011 - 2012, Met Office
#
# This file is part of cartopy.
#
# cartopy is free software: you can redistribute it and/or modify it under
# the terms of the GNU Lesser General Public License as published by the
# Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# cartopy is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Lesser General Public License for more details.
#
# You should have received a copy of the GNU Lesser General Public License
# along with cartopy.  If not, see <http://www.gnu.org/licenses/>.

import math
import warnings

from nose.tools import assert_equal
import numpy as np
import matplotlib.pyplot as plt

import cartopy.crs as ccrs

from cartopy.tests.mpl import ImageTesting


@ImageTesting(['global_contour_wrap'])
def test_global_contour_wrap_new_transform():
    ax = plt.axes(projection=ccrs.PlateCarree())
    ax.coastlines()
    x, y = np.meshgrid(np.linspace(0, 360), np.linspace(-90, 90))
    data = np.sin(np.sqrt(x ** 2 + y ** 2))
    plt.contour(x, y, data, transform=ccrs.PlateCarree())


@ImageTesting(['global_contour_wrap'])
def test_global_contour_wrap_no_transform():
    ax = plt.axes(projection=ccrs.PlateCarree())
    ax.coastlines()
    x, y = np.meshgrid(np.linspace(0, 360), np.linspace(-90, 90))
    data = np.sin(np.sqrt(x ** 2 + y ** 2))
    plt.contour(x, y, data)


@ImageTesting(['global_contourf_wrap'])
def test_global_contourf_wrap_new_transform():
    ax = plt.axes(projection=ccrs.PlateCarree())
    ax.coastlines()
    x, y = np.meshgrid(np.linspace(0, 360), np.linspace(-90, 90))
    data = np.sin(np.sqrt(x ** 2 + y ** 2))
    plt.contourf(x, y, data, transform=ccrs.PlateCarree())


@ImageTesting(['global_contourf_wrap'])
def test_global_contourf_wrap_no_transform():
    ax = plt.axes(projection=ccrs.PlateCarree())
    ax.coastlines()
    x, y = np.meshgrid(np.linspace(0, 360), np.linspace(-90, 90))
    data = np.sin(np.sqrt(x ** 2 + y ** 2))
    plt.contourf(x, y, data)


@ImageTesting(['global_pcolor_wrap'])
def test_global_pcolor_wrap_new_transform():
    ax = plt.axes(projection=ccrs.PlateCarree())
    ax.coastlines()
    x, y = np.meshgrid(np.linspace(0, 360), np.linspace(-90, 90))
    data = np.sin(np.sqrt(x ** 2 + y ** 2))
    plt.pcolor(x, y, data, transform=ccrs.PlateCarree())


@ImageTesting(['global_pcolor_wrap'])
def test_global_pcolor_wrap_no_transform():
    ax = plt.axes(projection=ccrs.PlateCarree())
    ax.coastlines()
    x, y = np.meshgrid(np.linspace(0, 360), np.linspace(-90, 90))
    data = np.sin(np.sqrt(x ** 2 + y ** 2))
    plt.pcolor(x, y, data)


@ImageTesting(['global_scatter_wrap'])
def test_global_scatter_wrap_new_transform():
    ax = plt.axes(projection=ccrs.PlateCarree())
    # By default the coastline feature will be drawn after patches.
    # By setting zorder we can ensure our scatter points are drawn
    # after the coastlines.
    ax.coastlines(zorder=0)
    x, y = np.meshgrid(np.linspace(0, 360), np.linspace(-90, 90))
    data = np.sin(np.sqrt(x ** 2 + y ** 2))
    plt.scatter(x, y, c=data, transform=ccrs.PlateCarree())


@ImageTesting(['global_scatter_wrap'])
def test_global_scatter_wrap_no_transform():
    ax = plt.axes(projection=ccrs.PlateCarree())
    ax.coastlines(zorder=0)
    x, y = np.meshgrid(np.linspace(0, 360), np.linspace(-90, 90))
    data = np.sin(np.sqrt(x ** 2 + y ** 2))
    plt.scatter(x, y, c=data)


@ImageTesting(['global_map'])
def test_global_map():
    ax = plt.axes(projection=ccrs.Robinson())
#    ax.coastlines()
#    ax.gridlines(5)

    plt.plot(-0.08, 51.53, 'o', transform=ccrs.PlateCarree())

    plt.plot([-0.08, 132], [51.53, 43.17], color='red',
             transform=ccrs.PlateCarree())

    plt.plot([-0.08, 132], [51.53, 43.17], color='blue',
             transform=ccrs.Geodetic())


@ImageTesting(['simple_global'])
def test_simple_global():
    plt.axes(projection=ccrs.PlateCarree())
    plt.gca().coastlines()
    # produces a global map, despite not having needed to set the limits


@ImageTesting(['multiple_projections1'])
def test_multiple_projections():

    projections = [ccrs.PlateCarree(),
                   ccrs.Robinson(),
                   ccrs.RotatedPole(pole_latitude=45, pole_longitude=180),
                   ccrs.OSGB(),
                   ccrs.TransverseMercator(),
                   ccrs.Mercator(
                       globe=ccrs.Globe(semimajor_axis=math.degrees(1)),
                       min_latitude=-85., max_latitude=85.),
                   ccrs.LambertCylindrical(),
                   ccrs.Miller(),
                   ccrs.Gnomonic(),
                   ccrs.Stereographic(),
                   ccrs.NorthPolarStereo(),
                   ccrs.SouthPolarStereo(),
                   ccrs.Orthographic(),
                   ccrs.Mollweide(),
                   ccrs.InterruptedGoodeHomolosine(),
                   ]

    fig = plt.figure(figsize=(10, 10))
    for i, prj in enumerate(projections, 1):
        ax = fig.add_subplot(5, 5, i, projection=prj)

        ax.set_global()

        ax.coastlines()

        plt.plot(-0.08, 51.53, 'o', transform=ccrs.PlateCarree())

        plt.plot([-0.08, 132], [51.53, 43.17], color='red',
                 transform=ccrs.PlateCarree())

        plt.plot([-0.08, 132], [51.53, 43.17], color='blue',
                 transform=ccrs.Geodetic())


def test_cursor_values():
    ax = plt.axes(projection=ccrs.NorthPolarStereo())
    x, y = np.array([-969100.]), np.array([-4457000.])
    r = ax.format_coord(x, y)
    assert_equal(r.encode('ascii', 'ignore'),
                 '-9.691e+05, -4.457e+06 (50.716617N, 12.267069W)')

    ax = plt.axes(projection=ccrs.PlateCarree())
    x, y = np.array([-181.5]), np.array([50.])
    r = ax.format_coord(x, y)
    assert_equal(r.encode('ascii', 'ignore'),
                 '-181.5, 50 (50.000000N, 178.500000E)')

    ax = plt.axes(projection=ccrs.Robinson())
    x, y = np.array([16060595.2]), np.array([2363093.4])
    r = ax.format_coord(x, y)
    assert_equal(r.encode('ascii', 'ignore'),
                 '1.606e+07, 2.363e+06 (22.095524N, 173.709136E)')

    plt.close()


@ImageTesting(['natural_earth_interface'])
def test_axes_natural_earth_interface():
    rob = ccrs.Robinson()

    ax = plt.axes(projection=rob)

    with warnings.catch_warnings(record=True) as all_warnings:
        warnings.simplefilter('always')

        ax.natural_earth_shp('rivers_lake_centerlines', edgecolor='black',
                             facecolor='none')
        ax.natural_earth_shp('lakes', facecolor='blue')

    assert_equal(len(all_warnings), 2)
    for warning in all_warnings:
        msg = str(warning.message)
        assert 'deprecated' in msg
        assert 'add_feature' in msg


@ImageTesting(['pcolormesh_global_wrap1'])
def test_pcolormesh_global_with_wrap1():
    # make up some realistic data with bounds (such as data from the UM)
    nx, ny = 36, 18
    xbnds = np.linspace(0, 360, nx, endpoint=True)
    ybnds = np.linspace(-90, 90, ny, endpoint=True)

    x, y = np.meshgrid(xbnds, ybnds)
    data = np.exp(np.sin(np.deg2rad(x)) + np.cos(np.deg2rad(y)))
    data = data[:-1, :-1]

    ax = plt.subplot(211, projection=ccrs.PlateCarree())
    plt.pcolormesh(xbnds, ybnds, data, transform=ccrs.PlateCarree())
    ax.coastlines()
    ax.set_global()  # make sure everything is visible

    ax = plt.subplot(212, projection=ccrs.PlateCarree(180))
    plt.pcolormesh(xbnds, ybnds, data, transform=ccrs.PlateCarree())
    ax.coastlines()
    ax.set_global()  # make sure everything is visible


@ImageTesting(['pcolormesh_global_wrap2'])
def test_pcolormesh_global_with_wrap2():
    # make up some realistic data with bounds (such as data from the UM)
    nx, ny = 36, 18
    xbnds, xstep = np.linspace(0, 360, nx - 1, retstep=True, endpoint=True)
    ybnds, ystep = np.linspace(-90, 90, nx - 1, retstep=True, endpoint=True)
    xbnds -= xstep / 2
    ybnds -= ystep / 2
    xbnds = np.append(xbnds, xbnds[-1] + xstep)
    ybnds = np.append(ybnds, ybnds[-1] + ystep)

    x, y = np.meshgrid(xbnds, ybnds)
    data = np.exp(np.sin(np.deg2rad(x)) + np.cos(np.deg2rad(y)))
    data = data[:-1, :-1]

    ax = plt.subplot(211, projection=ccrs.PlateCarree())
    plt.pcolormesh(xbnds, ybnds, data, transform=ccrs.PlateCarree())
    ax.coastlines()
    ax.set_global()  # make sure everything is visible

    ax = plt.subplot(212, projection=ccrs.PlateCarree(180))
    plt.pcolormesh(xbnds, ybnds, data, transform=ccrs.PlateCarree())
    ax.coastlines()
    ax.set_global()  # make sure everything is visible


@ImageTesting(['pcolormesh_global_wrap3'])
def test_pcolormesh_global_with_wrap3():
    nx, ny = 33, 17
    xbnds = np.linspace(-1.875, 358.125, nx, endpoint=True)
    ybnds = np.linspace(91.25, -91.25, ny, endpoint=True)
    xbnds, ybnds = np.meshgrid(xbnds, ybnds)

    data = np.exp(np.sin(np.deg2rad(xbnds)) + np.cos(np.deg2rad(ybnds)))

    # this step is not necessary, but makes the plot even harder to do (i.e.
    # it really puts cartopy through its paces)
    ybnds = np.append(ybnds, ybnds[:, 1:2], axis=1)
    xbnds = np.append(xbnds, xbnds[:, 1:2] + 360, axis=1)
    data = np.ma.concatenate([data, data[:, 0:1]], axis=1)

    data = data[:-1, :-1]
    data = np.ma.masked_greater(data, 2.6)

    ax = plt.subplot(311, projection=ccrs.PlateCarree(-45))
    c = plt.pcolormesh(xbnds, ybnds, data, transform=ccrs.PlateCarree())
    assert c._wrapped_collection_fix is not None, \
        'No pcolormesh wrapping was done when it should have been.'

    ax.coastlines()
    ax.set_global()  # make sure everything is visible

    ax = plt.subplot(312, projection=ccrs.PlateCarree(-1.87499952))
    plt.pcolormesh(xbnds, ybnds, data, transform=ccrs.PlateCarree())
    ax.coastlines()
    ax.set_global()  # make sure everything is visible

    ax = plt.subplot(313, projection=ccrs.Robinson(-2))
    plt.pcolormesh(xbnds, ybnds, data, transform=ccrs.PlateCarree())
    ax.coastlines()
    ax.set_global()  # make sure everything is visible


@ImageTesting(['pcolormesh_limited_area_wrap'])
def test_pcolormesh_limited_area_wrap():
    # make up some realistic data with bounds (such as data from the UM's North
    # Atlantic Europe model)
    nx, ny = 22, 36
    xbnds = np.linspace(311.91998291, 391.11999512, nx, endpoint=True)
    ybnds = np.linspace(-23.59000015, 24.81000137, ny, endpoint=True)
    x, y = np.meshgrid(xbnds, ybnds)
    data = ((np.sin(np.deg2rad(x))) / 10. + np.exp(np.cos(np.deg2rad(y))))
    data = data[:-1, :-1]

    rp = ccrs.RotatedPole(pole_longitude=177.5, pole_latitude=37.5)

    plt.figure(figsize=(10, 6))

    ax = plt.subplot(221, projection=ccrs.PlateCarree())
    plt.pcolormesh(xbnds, ybnds, data, transform=rp, cmap='Set1')
    ax.coastlines()

    ax = plt.subplot(222, projection=ccrs.PlateCarree(180))
    plt.pcolormesh(xbnds, ybnds, data, transform=rp, cmap='Set1')
    ax.coastlines()
    ax.set_global()

    # draw the same plot, only more zoomed in, and using the 2d versions
    # of the coordinates (just to test that 1d and 2d are both suitably
    # being fixed)
    ax = plt.subplot(223, projection=ccrs.PlateCarree(180))
    plt.pcolormesh(x, y, data, transform=rp, cmap='Set1')
    ax.coastlines()
    ax.set_extent([-70, 0, 0, 80])

    ax = plt.subplot(224, projection=rp)
    plt.pcolormesh(xbnds, ybnds, data, transform=rp, cmap='Set1')
    ax.coastlines()


@ImageTesting(['pcolormesh_goode_wrap'])
def test_pcolormesh_goode_wrap():
    # global data on an Interrupted Goode Homolosine projection
    # shouldn't spill outside projection boundary
    x = np.linspace(0, 360, 73)
    y = np.linspace(-87.5, 87.5, 36)
    X, Y = np.meshgrid(*[np.deg2rad(c) for c in (x, y)])
    Z = np.cos(Y) + 0.375 * np.sin(2. * X)
    Z = Z[:-1, :-1]
    ax = plt.axes(projection=ccrs.InterruptedGoodeHomolosine())
    ax.coastlines()
    ax.pcolormesh(x, y, Z, transform=ccrs.PlateCarree())


@ImageTesting(['quiver_plate_carree'])
def test_quiver_plate_carree():
    x = np.arange(-60, 42.5, 2.5)
    y = np.arange(30, 72.5, 2.5)
    x2d, y2d = np.meshgrid(x, y)
    u = np.cos(np.deg2rad(y2d))
    v = np.cos(2. * np.deg2rad(x2d))
    mag = (u**2 + v**2)**.5
    plot_extent = [-60, 40, 30, 70]
    plt.figure(figsize=(6, 6))
    # plot on native projection
    ax = plt.subplot(211, projection=ccrs.PlateCarree())
    ax.set_extent(plot_extent, crs=ccrs.PlateCarree())
    ax.coastlines()
    ax.quiver(x, y, u, v, mag)
    # plot on a different projection
    ax = plt.subplot(212, projection=ccrs.NorthPolarStereo())
    ax.set_extent(plot_extent, crs=ccrs.PlateCarree())
    ax.coastlines()
    ax.quiver(x, y, u, v, mag, transform=ccrs.PlateCarree())


@ImageTesting(['quiver_rotated_pole'])
def test_quiver_rotated_pole():
    nx, ny = 22, 36
    x = np.linspace(311.91998291, 391.11999512, nx, endpoint=True)
    y = np.linspace(-23.59000015, 24.81000137, ny, endpoint=True)
    x2d, y2d = np.meshgrid(x, y)
    u = np.cos(np.deg2rad(y2d))
    v = -2. * np.cos(2. * np.deg2rad(y2d)) * np.sin(np.deg2rad(x2d))
    mag = (u**2 + v**2)**.5
    rp = ccrs.RotatedPole(pole_longitude=177.5, pole_latitude=37.5)
    plot_extent = [x[0], x[-1], y[0], y[-1]]
    # plot on native projection
    plt.figure(figsize=(6, 6))
    ax = plt.subplot(211, projection=rp)
    ax.set_extent(plot_extent, crs=rp)
    ax.coastlines()
    ax.quiver(x, y, u, v, mag)
    # plot on different projection
    ax = plt.subplot(212, projection=ccrs.PlateCarree())
    ax.set_extent(plot_extent, crs=rp)
    ax.coastlines()
    ax.quiver(x, y, u, v, mag, transform=rp)


@ImageTesting(['quiver_regrid'])
def test_quiver_regrid():
    x = np.arange(-60, 42.5, 2.5)
    y = np.arange(30, 72.5, 2.5)
    x2d, y2d = np.meshgrid(x, y)
    u = np.cos(np.deg2rad(y2d))
    v = np.cos(2. * np.deg2rad(x2d))
    mag = (u**2 + v**2)**.5
    plot_extent = [-60, 40, 30, 70]
    plt.figure(figsize=(6, 3))
    ax = plt.axes(projection=ccrs.NorthPolarStereo())
    ax.set_extent(plot_extent, crs=ccrs.PlateCarree())
    ax.coastlines()
    ax.quiver(x, y, u, v, mag, transform=ccrs.PlateCarree(),
              regrid_shape=30)


@ImageTesting(['quiver_regrid_with_extent'])
def test_quiver_regrid_with_extent():
    x = np.arange(-60, 42.5, 2.5)
    y = np.arange(30, 72.5, 2.5)
    x2d, y2d = np.meshgrid(x, y)
    u = np.cos(np.deg2rad(y2d))
    v = np.cos(2. * np.deg2rad(x2d))
    mag = (u**2 + v**2)**.5
    plot_extent = [-60, 40, 30, 70]
    target_extent = [-3e6, 2e6, -6e6, -2.5e6]
    plt.figure(figsize=(6, 3))
    ax = plt.axes(projection=ccrs.NorthPolarStereo())
    ax.set_extent(plot_extent, crs=ccrs.PlateCarree())
    ax.coastlines()
    ax.quiver(x, y, u, v, mag, transform=ccrs.PlateCarree(),
              regrid_shape=10, target_extent=target_extent)


@ImageTesting(['barbs_plate_carree'])
def test_barbs():
    x = np.arange(-60, 45, 5)
    y = np.arange(30, 75, 5)
    x2d, y2d = np.meshgrid(x, y)
    u = 40 * np.cos(np.deg2rad(y2d))
    v = 40 * np.cos(2. * np.deg2rad(x2d))
    mag = (u**2 + v**2)**.5
    plot_extent = [-60, 40, 30, 70]
    plt.figure(figsize=(6, 6))
    # plot on native projection
    ax = plt.subplot(211, projection=ccrs.PlateCarree())
    ax.set_extent(plot_extent, crs=ccrs.PlateCarree())
    ax.coastlines()
    ax.barbs(x, y, u, v, length=4, linewidth=.25)
    # plot on a different projection
    ax = plt.subplot(212, projection=ccrs.NorthPolarStereo())
    ax.set_extent(plot_extent, crs=ccrs.PlateCarree())
    ax.coastlines()
    ax.barbs(x, y, u, v, transform=ccrs.PlateCarree(), length=4, linewidth=.25)


@ImageTesting(['barbs_regrid'])
def test_barbs_regrid():
    x = np.arange(-60, 42.5, 2.5)
    y = np.arange(30, 72.5, 2.5)
    x2d, y2d = np.meshgrid(x, y)
    u = 40 * np.cos(np.deg2rad(y2d))
    v = 40 * np.cos(2. * np.deg2rad(x2d))
    mag = (u**2 + v**2)**.5
    plot_extent = [-60, 40, 30, 70]
    plt.figure(figsize=(6, 3))
    ax = plt.axes(projection=ccrs.NorthPolarStereo())
    ax.set_extent(plot_extent, crs=ccrs.PlateCarree())
    ax.coastlines()
    ax.barbs(x, y, u, v, mag, transform=ccrs.PlateCarree(),
             length=4, linewidth=.4, regrid_shape=20)


@ImageTesting(['barbs_regrid_with_extent'])
def test_barbs_regrid_with_extent():
    x = np.arange(-60, 42.5, 2.5)
    y = np.arange(30, 72.5, 2.5)
    x2d, y2d = np.meshgrid(x, y)
    u = 40 * np.cos(np.deg2rad(y2d))
    v = 40 * np.cos(2. * np.deg2rad(x2d))
    mag = (u**2 + v**2)**.5
    plot_extent = [-60, 40, 30, 70]
    target_extent = [-3e6, 2e6, -6e6, -2.5e6]
    plt.figure(figsize=(6, 3))
    ax = plt.axes(projection=ccrs.NorthPolarStereo())
    ax.set_extent(plot_extent, crs=ccrs.PlateCarree())
    ax.coastlines()
    ax.barbs(x, y, u, v, mag, transform=ccrs.PlateCarree(),
             length=4, linewidth=.25, regrid_shape=10,
             target_extent=target_extent)


@ImageTesting(['streamplot'])
def test_streamplot():
    x = np.arange(-60, 42.5, 2.5)
    y = np.arange(30, 72.5, 2.5)
    x2d, y2d = np.meshgrid(x, y)
    u = np.cos(np.deg2rad(y2d))
    v = np.cos(2. * np.deg2rad(x2d))
    mag = (u**2 + v**2)**.5
    plot_extent = [-60, 40, 30, 70]
    plt.figure(figsize=(6, 3))
    ax = plt.axes(projection=ccrs.NorthPolarStereo())
    ax.set_extent(plot_extent, crs=ccrs.PlateCarree())
    ax.coastlines()
    ax.streamplot(x, y, u, v, transform=ccrs.PlateCarree(),
                  density=(1.5, 2), color=mag, linewidth=2*mag)


if __name__ == '__main__':
    import nose
    nose.runmodule(argv=['-s', '--with-doctest'], exit=False)

########NEW FILE########
__FILENAME__ = test_pseudo_color
# (C) British Crown Copyright 2013, Met Office
#
# This file is part of cartopy.
#
# cartopy is free software: you can redistribute it and/or modify it under
# the terms of the GNU Lesser General Public License as published by the
# Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# cartopy is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Lesser General Public License for more details.
#
# You should have received a copy of the GNU Lesser General Public License
# along with cartopy.  If not, see <http://www.gnu.org/licenses/>.

import matplotlib.pyplot as plt
import mock
from nose.tools import assert_equal
import numpy as np

import cartopy.crs as ccrs


def test_pcolormesh_fully_masked():
    data = np.ma.masked_all((30, 40))

    # Check that a fully masked data array doesn't trigger a pcolor call.
    with mock.patch('cartopy.mpl.geoaxes.GeoAxes.pcolor') as pcolor:
        ax = plt.axes(projection=ccrs.PlateCarree())
        ax.pcolormesh(np.linspace(-90, 90, 40), np.linspace(0, 360, 30), data)
        assert_equal(pcolor.call_count, 0, ("pcolor shouldn't have been "
                                            "called, but was."))


def test_pcolormesh_partially_masked():
    data = np.ma.masked_all((30, 40))
    data[0:100] = 10

    # Check that a partially masked data array does trigger a pcolor call.
    with mock.patch('cartopy.mpl.geoaxes.GeoAxes.pcolor') as pcolor:
        ax = plt.axes(projection=ccrs.PlateCarree())
        ax.pcolormesh(np.linspace(-90, 90, 40), np.linspace(0, 360, 30), data)
        assert_equal(pcolor.call_count, 1, ("pcolor should have been "
                                            "called exactly once."))


if __name__ == '__main__':
    import nose
    nose.runmodule(argv=['-sv', '--with-doctest'], exit=False)

########NEW FILE########
__FILENAME__ = test_set_extent
# (C) British Crown Copyright 2011 - 2012, Met Office
#
# This file is part of cartopy.
#
# cartopy is free software: you can redistribute it and/or modify it under
# the terms of the GNU Lesser General Public License as published by the
# Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# cartopy is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Lesser General Public License for more details.
#
# You should have received a copy of the GNU Lesser General Public License
# along with cartopy.  If not, see <http://www.gnu.org/licenses/>.

import tempfile

from matplotlib.testing.decorators import cleanup
import matplotlib.pyplot as plt
import numpy as np
from numpy.testing import assert_array_almost_equal, assert_array_equal

import cartopy.crs as ccrs


@cleanup
def test_extents():
    # tests that one can set the extents of a map in a variety of coordinate
    # systems, for a variety of projection
    uk = [-12.5, 4, 49, 60]
    uk_crs = ccrs.Geodetic()

    ax = plt.axes(projection=ccrs.PlateCarree())
    ax.set_extent(uk, crs=uk_crs)
    # enable to see what is going on (and to make sure it is a plot of the uk)
    # ax.coastlines()
    assert_array_almost_equal(ax.viewLim.get_points(),
                              np.array([[-12.5, 49.], [4., 60.]]))

    ax = plt.axes(projection=ccrs.NorthPolarStereo())
    ax.set_extent(uk, crs=uk_crs)
    # enable to see what is going on (and to make sure it is a plot of the uk)
    # ax.coastlines()
    assert_array_almost_equal(ax.viewLim.get_points(),
                              np.array([[-1034046.22566261, -4765889.76601514],
                                        [333263.47741164, -3345219.0594531]])
                              )

    # given that we know the PolarStereo coordinates of the UK, try using
    # those in a PlateCarree plot
    ax = plt.axes(projection=ccrs.PlateCarree())
    ax.set_extent([-1034046, 333263, -4765889, -3345219],
                  crs=ccrs.NorthPolarStereo())
    # enable to see what is going on (and to make sure it is a plot of the uk)
    # ax.coastlines()
    assert_array_almost_equal(ax.viewLim.get_points(),
                              np.array([[-17.17698577, 48.21879707],
                                        [5.68924381, 60.54218893]])
                              )


@cleanup
def test_domain_extents():
    # Setting the extent to global or the domain limits.
    ax = plt.axes(projection=ccrs.PlateCarree())
    ax.set_extent((-180, 180, -90, 90))
    assert_array_equal(ax.viewLim.get_points(), [[-180, -90], [180, 90]])
    ax.set_extent((-180, 180, -90, 90), ccrs.PlateCarree())
    assert_array_equal(ax.viewLim.get_points(), [[-180, -90], [180, 90]])

    ax = plt.axes(projection=ccrs.PlateCarree(90))
    ax.set_extent((-180, 180, -90, 90))
    assert_array_equal(ax.viewLim.get_points(), [[-180, -90], [180, 90]])
    ax.set_extent((-180, 180, -90, 90), ccrs.PlateCarree(90))
    assert_array_equal(ax.viewLim.get_points(), [[-180, -90], [180, 90]])

    ax = plt.axes(projection=ccrs.OSGB())
    ax.set_extent((0, 7e5, 0, 13e5), ccrs.OSGB())
    assert_array_equal(ax.viewLim.get_points(), [[0, 0], [7e5, 13e5]])


def test_update_lim():
    # check that the standard data lim setting works
    ax = plt.axes(projection=ccrs.PlateCarree())
    ax.update_datalim([(-10, -10), (-5, -5)])
    assert_array_almost_equal(ax.dataLim.get_points(),
                              np.array([[-10., -10.], [-5., -5.]]))
    plt.close()


def test_limits_contour():
    xs, ys = np.meshgrid(np.linspace(250, 350, 15), np.linspace(-45, 45, 20))
    data = np.sin((xs * ys) * 1.e7)

    resulting_extent = np.array([[250 - 180, -45.], [-10. + 180, 45.]])

    ax = plt.axes(projection=ccrs.PlateCarree())
    ax.coastlines()
    plt.contourf(xs, ys, data, transform=ccrs.PlateCarree(180))
    assert_array_almost_equal(ax.dataLim, resulting_extent)
    plt.close()

    ax = plt.axes(projection=ccrs.PlateCarree())
    ax.coastlines()
    plt.contour(xs, ys, data, transform=ccrs.PlateCarree(180))
    assert_array_almost_equal(ax.dataLim, resulting_extent)
    plt.close()


def test_limits_pcolor():
    xs, ys = np.meshgrid(np.linspace(250, 350, 15), np.linspace(-45, 45, 20))
    data = (np.sin((xs * ys) * 1.e7))[:-1, :-1]

    resulting_extent = np.array([[250 - 180, -45.], [-10. + 180, 45.]])

    ax = plt.axes(projection=ccrs.PlateCarree())
    ax.coastlines()
    plt.pcolor(xs, ys, data, transform=ccrs.PlateCarree(180))
    assert_array_almost_equal(ax.dataLim, resulting_extent)
    plt.close()

    ax = plt.axes(projection=ccrs.PlateCarree())
    ax.coastlines()
    plt.pcolormesh(xs, ys, data, transform=ccrs.PlateCarree(180))
    assert_array_almost_equal(ax.dataLim, resulting_extent)
    plt.close()


def test_view_lim_autoscaling():
    x = np.linspace(0.12910209, 0.42141822)
    y = np.linspace(0.03739792, 0.33029076)
    x, y = np.meshgrid(x, y)
    ax = plt.axes(projection=ccrs.RotatedPole(37.5, 357.5))

    plt.scatter(x, y, x * y, transform=ccrs.PlateCarree())

    expected = np.array([[86.12433701, 52.51570463],
                         [86.69696603, 52.86372057]])

    assert_array_almost_equal(ax.viewLim.frozen().get_points(), expected)
    plt.draw()
    assert_array_almost_equal(ax.viewLim.frozen().get_points(), expected)
    ax.relim()
    ax.autoscale_view(tight=False)
    expected_non_tight = np.array([[86, 52.45], [86.8, 52.9]])
    assert_array_almost_equal(ax.viewLim.frozen().get_points(),
                              expected_non_tight)


def test_view_lim_default_global():
    ax = plt.axes(projection=ccrs.PlateCarree())
    # The view lim should be the default unit bbox until it is drawn.
    assert_array_almost_equal(ax.viewLim.frozen().get_points(),
                              [[0, 0], [1, 1]])
    with tempfile.TemporaryFile() as tmp:
        plt.savefig(tmp)
    expected = np.array([[-180, -90], [180, 90]])
    assert_array_almost_equal(ax.viewLim.frozen().get_points(),
                              expected)


if __name__ == '__main__':
    import nose
    nose.runmodule(argv=['-s', '--with-doctest'], exit=False)

########NEW FILE########
__FILENAME__ = test_shapely_to_mpl
# (C) British Crown Copyright 2011 - 2014, Met Office
#
# This file is part of cartopy.
#
# cartopy is free software: you can redistribute it and/or modify it under
# the terms of the GNU Lesser General Public License as published by the
# Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# cartopy is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Lesser General Public License for more details.
#
# You should have received a copy of the GNU Lesser General Public License
# along with cartopy.  If not, see <http://www.gnu.org/licenses/>.

import numpy as np
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from matplotlib.collections import PatchCollection
from matplotlib.path import Path
import shapely.geometry as sgeom

import cartopy.crs as ccrs
import cartopy.mpl.patch as cpatch

from cartopy.tests.mpl import ImageTesting


@ImageTesting(['poly_interiors'])
def test_polygon_interiors():

    ax = plt.subplot(211, projection=ccrs.PlateCarree())
    ax.coastlines()
    ax.set_global()

    pth = Path([[0, -45], [60, -45], [60, 45], [0, 45], [0, 45],
                [10, -20], [10, 20], [40, 20], [40, -20], [10, 20]],
               [1, 2, 2, 2, 79, 1, 2, 2, 2, 79])

    patches_native = []
    patches = []
    for geos in cpatch.path_to_geos(pth):
        for pth in cpatch.geos_to_path(geos):
            patches.append(mpatches.PathPatch(pth))

        # buffer by 10 degrees (leaves a small hole in the middle)
        geos_buffered = geos.buffer(10)
        for pth in cpatch.geos_to_path(geos_buffered):
            patches_native.append(mpatches.PathPatch(pth))

    # Set high zorder to ensure the polygons are drawn on top of coastlines.
    collection = PatchCollection(patches_native, facecolor='red', alpha=0.4,
                                 transform=ax.projection, zorder=10)
    ax.add_collection(collection)

    collection = PatchCollection(patches, facecolor='yellow', alpha=0.4,
                                 transform=ccrs.Geodetic(), zorder=10)

    ax.add_collection(collection)

    # test multiple interior polygons
    ax = plt.subplot(212, projection=ccrs.PlateCarree(),
                     xlim=[-5, 15], ylim=[-5, 15])
    ax.coastlines()

    exterior = np.array(sgeom.box(0, 0, 12, 12).exterior.coords)
    interiors = [np.array(sgeom.box(1, 1, 2, 2, ccw=False).exterior.coords),
                 np.array(sgeom.box(1, 8, 2, 9, ccw=False).exterior.coords)]
    poly = sgeom.Polygon(exterior, interiors)

    patches = []
    for pth in cpatch.geos_to_path(poly):
        patches.append(mpatches.PathPatch(pth))

    collection = PatchCollection(patches, facecolor='yellow', alpha=0.4,
                                 transform=ccrs.Geodetic(), zorder=10)
    ax.add_collection(collection)


def test_null_geometry():
    pth = Path([[358.27203369, 3.56399965],
                [358.27203369, 3.56399965],
                [358.27203369, 3.56399965]])
    geoms = cpatch.path_to_geos(pth)

    assert len(geoms) == 0


@ImageTesting(['contour_with_interiors'], tolerance=0.3)
def test_contour_interiors():
    ############### produces a polygon with multiple holes:
    nx, ny = 10, 10
    numlev = 2
    lons, lats = np.meshgrid(np.linspace(-50, 50, nx),
                             np.linspace(-45, 45, ny))
    data = np.sin(np.sqrt(lons ** 2 + lats ** 2))

    ax = plt.subplot(221, projection=ccrs.PlateCarree())
    ax.set_global()
    plt.title("Native projection")
    plt.contourf(lons, lats, data, numlev, transform=ccrs.PlateCarree())
    ax.coastlines()

    plt.subplot(222, projection=ccrs.Robinson())
    plt.title("Non-native projection")
    ax = plt.gca()
    ax.set_global()
    plt.contourf(lons, lats, data, numlev, transform=ccrs.PlateCarree())
    ax.coastlines()

    ############## produces singular polygons (zero area polygons)

    numlev = 2
    x, y = np.meshgrid(np.arange(-5.5, 5.5, 0.25), np.arange(-5.5, 5.5, 0.25))
    dim = x.shape[0]
    data = np.sin(np.sqrt(x ** 2 + y ** 2))
    lats = np.arange(dim) + 30
    lons = np.arange(dim) - 20

    ax = plt.subplot(223, projection=ccrs.PlateCarree())
    ax.set_global()
    plt.title("Native projection")
    plt.contourf(lons, lats, data, numlev, transform=ccrs.PlateCarree())
    ax.coastlines()

    plt.subplot(224, projection=ccrs.Robinson())
    plt.title("Non-native projection")
    ax = plt.gca()
    ax.set_global()
    plt.contourf(lons, lats, data, numlev, transform=ccrs.PlateCarree())
    ax.coastlines()


if __name__ == '__main__':
    import nose
    nose.runmodule(argv=['-s', '--with-doctest'], exit=False)

########NEW FILE########
__FILENAME__ = test_ticks
# (C) British Crown Copyright 2011 - 2014, Met Office
#
# This file is part of cartopy.
#
# cartopy is free software: you can redistribute it and/or modify it under
# the terms of the GNU Lesser General Public License as published by the
# Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# cartopy is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Lesser General Public License for more details.
#
# You should have received a copy of the GNU Lesser General Public License
# along with cartopy.  If not, see <http://www.gnu.org/licenses/>.

import math

import matplotlib.pyplot as plt
import matplotlib.ticker
import nose.tools

import cartopy.crs as ccrs
from cartopy.tests.mpl import ImageTesting


def _format_lat(val, i):
    if val > 0:
        return '%.0fN' % val
    elif val < 0:
        return '%.0fS' % abs(val)
    else:
        return '0'


def _format_lon(val, i):
    # Apply periodic boundary conditions, with an almost equal test on 180 lon.
    while val > 180:
        val -= 360
    while val < -180:
        val += 360
    if abs(abs(val) - 180.) <= 1e-06 or val == 0:
        return '%.0f' % abs(val)
    elif val > 0:
        return '%.0fE' % val
    elif val < 0:
        return '%.0fW' % abs(val)


@ImageTesting(['xticks_no_transform'], tolerance=0.12)
def test_set_xticks_no_transform():
    ax = plt.axes(projection=ccrs.PlateCarree())
    ax.coastlines('110m')
    ax.xaxis.set_major_formatter(matplotlib.ticker.FuncFormatter(_format_lon))
    ax.yaxis.set_major_formatter(matplotlib.ticker.FuncFormatter(_format_lat))
    ax.set_xticks([-180, -90, 0, 90, 180])
    ax.set_xticks([-135, -45, 45, 135], minor=True)


@ImageTesting(['xticks_cylindrical'], tolerance=0.12)
def test_set_xticks_cylindrical():
    ax = plt.axes(projection=ccrs.Mercator(
                  min_latitude=-85.,
                  max_latitude=85.,
                  globe=ccrs.Globe(semimajor_axis=math.degrees(1))))
    ax.coastlines('110m')
    ax.xaxis.set_major_formatter(matplotlib.ticker.FuncFormatter(_format_lon))
    ax.yaxis.set_major_formatter(matplotlib.ticker.FuncFormatter(_format_lat))
    ax.set_xticks([-180, -90, 0, 90, 180], crs=ccrs.PlateCarree())
    ax.set_xticks([-135, -45, 45, 135], minor=True, crs=ccrs.PlateCarree())


def test_set_xticks_non_cylindrical():
    ax = plt.axes(projection=ccrs.Orthographic())
    with nose.tools.assert_raises(RuntimeError):
        ax.set_xticks([-180, -90, 0, 90, 180], crs=ccrs.Geodetic())
    with nose.tools.assert_raises(RuntimeError):
        ax.set_xticks([-135, -45, 45, 135], minor=True, crs=ccrs.Geodetic())


@ImageTesting(['yticks_no_transform'], tolerance=0.125)
def test_set_yticks_no_transform():
    ax = plt.axes(projection=ccrs.PlateCarree())
    ax.coastlines('110m')
    ax.xaxis.set_major_formatter(matplotlib.ticker.FuncFormatter(_format_lon))
    ax.yaxis.set_major_formatter(matplotlib.ticker.FuncFormatter(_format_lat))
    ax.set_yticks([-60, -30, 0, 30, 60])
    ax.set_yticks([-75, -45, 15, 45, 75], minor=True)


@ImageTesting(['yticks_cylindrical'], tolerance=0.12)
def test_set_yticks_cylindrical():
    ax = plt.axes(projection=ccrs.Mercator(
                  min_latitude=-85.,
                  max_latitude=85.,
                  globe=ccrs.Globe(semimajor_axis=math.degrees(1))))
    ax.coastlines('110m')
    ax.xaxis.set_major_formatter(matplotlib.ticker.FuncFormatter(_format_lon))
    ax.yaxis.set_major_formatter(matplotlib.ticker.FuncFormatter(_format_lat))
    ax.set_yticks([-60, -30, 0, 30, 60], crs=ccrs.PlateCarree())
    ax.set_yticks([-75, -45, 15, 45, 75], minor=True, crs=ccrs.PlateCarree())


def test_set_yticks_non_cylindrical():
    ax = plt.axes(projection=ccrs.Orthographic())
    with nose.tools.assert_raises(RuntimeError):
        ax.set_yticks([-60, -30, 0, 30, 60], crs=ccrs.Geodetic())
    with nose.tools.assert_raises(RuntimeError):
        ax.set_yticks([-75, -45, 15, 45, 75], minor=True, crs=ccrs.Geodetic())


@ImageTesting(['xyticks'], tolerance=0.17)
def test_set_xyticks():
    fig = plt.figure(figsize=(10, 10))
    projections = (ccrs.PlateCarree(),
                   ccrs.Mercator(globe=ccrs.Globe(
                       semimajor_axis=math.degrees(1))),
                   ccrs.TransverseMercator())
    x = -3.275024
    y = 50.753998
    for i, prj in enumerate(projections, 1):
        ax = fig.add_subplot(3, 1, i, projection=prj)
        ax.set_extent([-12.5, 4, 49, 60], ccrs.Geodetic())
        ax.coastlines('110m')
        p, q = prj.transform_point(x, y, ccrs.Geodetic())
        ax.set_xticks([p])
        ax.set_yticks([q])


if __name__ == '__main__':
    import nose
    nose.runmodule(argv=['-s', '--with-doctest'], exit=False)

########NEW FILE########
__FILENAME__ = test_web_services
# (C) British Crown Copyright 2014, Met Office
#
# This file is part of cartopy.
#
# cartopy is free software: you can redistribute it and/or modify it under
# the terms of the GNU Lesser General Public License as published by the
# Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# cartopy is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Lesser General Public License for more details.
#
# You should have received a copy of the GNU Lesser General Public License
# along with cartopy.  If not, see <http://www.gnu.org/licenses/>.

import matplotlib.pyplot as plt

from cartopy.tests.mpl import ImageTesting
import cartopy.crs as ccrs


@ImageTesting(['wmts'])
def test_wmts():
    ax = plt.axes(projection=ccrs.PlateCarree())
    url = 'http://map1c.vis.earthdata.nasa.gov/wmts-geo/wmts.cgi'
    # Use a layer which doesn't change over time.
    ax.add_wmts(url, 'MODIS_Water_Mask')


if __name__ == '__main__':
    import nose
    nose.runmodule(argv=['-s', '--with-doctest'], exit=False)

########NEW FILE########
__FILENAME__ = rhattersley_quickrun_DELME
# (C) British Crown Copyright 2011 - 2012, Met Office
#
# This file is part of cartopy.
#
# cartopy is free software: you can redistribute it and/or modify it under
# the terms of the GNU Lesser General Public License as published by the
# Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# cartopy is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Lesser General Public License for more details.
#
# You should have received a copy of the GNU Lesser General Public License
# along with cartopy.  If not, see <http://www.gnu.org/licenses/>.


import itertools
import math
import os.path
import sys

import matplotlib.patches as mpatches
import matplotlib.pyplot as plt
import shapely.geometry as sgeom

import cartopy.crs as ccrs
import cartopy.io.shapereader as shapereader

COASTLINE_PATH = shapereader.natural_earth(name='coastline')
LAND_PATH = shapereader.natural_earth(name='land')


def _arrows(projection, geometry):
    coords = list(geometry.coords)
    for i, xyxy in enumerate(zip(coords[:-1], coords[1:])):
        if i % 11 == 0:
            start, end = xyxy
            dx = end[0] - start[0]
            dy = end[1] - start[1]
            s = 4
            #width = math.sqrt(dx*dx+dy*dy)*0.5*s
            #arrow = mpatches.Arrow(start[0], start[1], dx*s,
            #                       dy*s, width=width, alpha=0.4)
            mag = math.sqrt(dx * dx + dy * dy)
            length = projection.threshold * s
            try:
                dx = length * dx / mag
                dy = length * dy / mag
                width = projection.threshold * s * 0.5
                arrow = mpatches.Arrow(start[0], start[1], dx, dy,
                                       width=width, alpha=0.4)
                plt.gca().add_patch(arrow)
            except ZeroDivisionError:
                pass


def draw_line_string(projection, line_string, color='black', linestyle='-'):
    multi_line_string = projection.project_geometry(line_string)
    for line_string in multi_line_string:
        plt.plot(*zip(*line_string.coords),
                 marker='', color=color, linestyle=linestyle)
        #_arrows(projection, line_string)


def draw_polygon(projection, polygon, color=None):
    multi_polygon = projection.project_geometry(polygon)
    for polygon in multi_polygon:
        #plt.plot(*zip(*polygon.exterior.coords), marker='+', color=color)
        #_arrows(projection, polygon.exterior)
        #continue
        import cartopy.mpl.patch as patch
        paths = patch.geos_to_path(polygon)
        for pth in paths:
            patch = mpatches.PathPatch(pth, edgecolor='none',
                                       alpha=0.5, facecolor=color, lw=0)
            plt.gca().add_patch(patch)
        #plt.fill(*zip(*polygon.exterior.coords), edgecolor='none',
        #         alpha=0.5, facecolor=color)


def wave_data():
    import numpy as np
    # make up some data on a regular lat/lon grid.
    nlats = 73
    nlons = 145
    delta = 2. * np.pi / (nlons - 1)
    lats = (0.5 * np.pi - delta * np.indices((nlats, nlons))[0, :, :])
    lons = (delta * np.indices((nlats, nlons))[1, :, :])
    wave = 0.75 * (np.sin(2. * lats) ** 8 * np.cos(4. * lons))
    mean = 0.5 * np.cos(2. * lats) * ((np.sin(2. * lats)) ** 2 + 2.)
    lats = np.rad2deg(lats)
    lons = np.rad2deg(lons)
    data = wave + mean
    return lons, lats, data


def test(projections):
    coords = [(-0.08, 51.53), (132.00, 43.17)]  # London to Vladivostock
    orig_line_string = sgeom.LineString(coords)

    n_rows = math.ceil(math.sqrt(len(projections)))
    n_cols = math.ceil(len(projections) / n_rows)

    figure, axes_grid = plt.subplots(int(n_rows), int(n_cols))
    if n_rows == 1 and n_cols == 1:
        axes_list = [axes_grid]
    else:
        axes_list = axes_grid.flat

    for projection, axes in zip(projections, axes_list):
        plt.sca(axes)

        colors = itertools.cycle(['b', 'g', 'r', 'c', 'm', 'y', 'k'])

        bits = (
            #'contour',
            #'contourf',
            'boundary',
            #'line',
            #'grid',
            'coastline',
            #'polygons',
            'continents',
        )

        if 'contour' in bits:
            # Contours - placeholder for MPL integration
            cs = plt.contour(*wave_data())
            plt.cla()
            for c in cs.collections:
            #for c in cs.collections[2:3]:
                for p in c.get_paths():
                #for p in c.get_paths()[1:]:
                    xy = [segment[0] for segment in p.iter_segments()]
                    line_string = sgeom.LineString(xy)
                    #line_string = sgeom.LineString(xy[:3])
                    draw_line_string(projection, line_string,
                                     color=c.get_color()[0])

        if 'contourf' in bits:
            # Filled contours - placeholder for MPL integration
            cs = plt.contourf(*wave_data())
            plt.cla()
            for c in cs.collections:
            #for i, c in enumerate(cs.collections[2:3]):
                for p in c.get_paths():
                #for j, p in enumerate(c.get_paths()[1:2]):
                    xy = [segment[0] for segment in p.iter_segments()]
                    xy = filter(lambda xy: xy[1] > -90, xy)
                    polygon = sgeom.Polygon(xy)
                    #polygon = sgeom.Polygon(xy[53:56])
                    draw_polygon(projection, polygon,
                                 color=c.get_facecolor()[0])

        if 'boundary' in bits:
            plt.plot(*zip(*projection.boundary.coords), marker='')

        if 'line' in bits:
            draw_line_string(projection, orig_line_string, color='red')
            polygon = sgeom.LineString([(-50, -80), (90, -80)])
            draw_line_string(projection, polygon)

        if 'grid' in bits:
            # Grid lines
            step = 15
            lons = range(0, 360, step)
            for lon in lons:
                line_string = sgeom.LineString(
                    [(lon, -75), (lon, 0), (lon, 75)])
                draw_line_string(projection, line_string, linestyle=':')
            lons = lons + [lons[0]]
            lats = range(-90 + step, 90, step)
            for lat in lats:
                line_string = sgeom.LineString([(lon, lat) for lon in lons])
                draw_line_string(projection, line_string, linestyle=':')

        if 'coastline' in bits:
            reader = shapereader.Reader(COASTLINE_PATH)
            print 'Reading coastline ...'
            all_geometries = list(reader.geometries())
            print '   ... done.'
            geometries = []
            geometries += all_geometries
            #geometries += all_geometries[48:52] # Aus & Taz
            #geometries += all_geometries[72:73] # GB
            #for geometry in geometries:
            for i, geometry in enumerate(geometries):
                for line_string in geometry:
                    try:
                        draw_line_string(projection, line_string)
                    except ValueError:
                        print i
                        print geometry
                        raise
                import sys
                sys.stdout.write('.')
                sys.stdout.flush()

        if 'polygons' in bits:
            # Square over pole (CW)
            polygon = sgeom.Polygon(
                [(0, 75), (-90, 75), (-180, 75), (-270, 75)])
            draw_polygon(projection, polygon)

            # Square (CW)
            polygon = sgeom.Polygon(
                [(150, 75), (-150, 75), (-150, 55), (150, 55)])
            draw_polygon(projection, polygon)

            # Wedge - demonstrates removal of interior when split (CW)
            polygon = sgeom.Polygon([(-5, 10), (20, 0), (-5, -10), (10, 0)])
            draw_polygon(projection, polygon)

            # "Antarctica" (incl. non-physical boundary segments) (CW)
            polygon = sgeom.Polygon([(-50, -80), (90, -80), (160, -70),
                                     (160, -90), (-160, -90), (-160, -70)])
            draw_polygon(projection, polygon)

            # Wedge
            polygon = sgeom.Polygon([(-10, 30), (10, 60), (10, 50)])
            draw_polygon(projection, polygon)

        if 'continents' in bits:
            reader = shapereader.Reader(LAND_PATH)
            print 'Reading continents ...'
            all_geometries = list(reader.geometries())
            print '   ... done.'
            geometries = []
            geometries += all_geometries

            #geometries += all_geometries[7:8] # Antarctica
            #geometries += all_geometries[16:17] # Some E-equatorial island
            #geometries += all_geometries[93:94] # Some NE island
            #geometries += all_geometries[112:113] # Africa & Asia

            #geometries += all_geometries[95:96] # North and South America
            #geometries += all_geometries[126:] # Greenland

            #geometries += all_geometries[0:7]
            #geometries += all_geometries[8:]
            #geometries += all_geometries[8:16]
            #geometries += all_geometries[17:93]
            #geometries += all_geometries[94:112]
            #geometries += all_geometries[113:]

            for i, multi_polygon in enumerate(geometries):
                for polygon in multi_polygon:
                    polygon = sgeom.Polygon(filter(
                        lambda xy: xy[1] > -90, polygon.exterior.coords))
                    draw_polygon(projection, polygon, color=colors.next())
                    #draw_line_string(projection, polygon)
                import sys
                sys.stdout.write('.')
                sys.stdout.flush()

        plt.title(type(projection).__name__)
        plt.xlim(projection.x_limits)
        plt.ylim(projection.y_limits)


if __name__ == '__main__':
    if 'anim' not in sys.argv:
        projections = [
            ccrs.PlateCarree(-105),
            #ccrs.PlateCarree(20),
            #ccrs.TransverseMercator(central_longitude=-90),
            #ccrs.NorthPolarStereo(),
            #ccrs.Mercator(),
            #ccrs.LambertCylindrical(),
            #ccrs.Robinson(),
            #ccrs.Robinson(170.5),
            #ccrs.Miller(),
            #ccrs.Mollweide(),
            #ccrs.Stereographic(),
            #ccrs.RotatedPole(pole_longitude=177.5, pole_latitude=37.5),
            #ccrs.OSGB(),

            # Incorrect lat/lon grid lines
            #ccrs.Orthographic(central_longitude=-90, central_latitude=45),

            # Not fully implemented (e.g. missing boundary definition)
            #ccrs.InterruptedGoodeHomolosine(),
        ]
        test(projections)
        plt.show()
    else:
        plt.figure(figsize=(15, 6))
        plt.ion()
        while True:
            for lon in range(0, 360, 10):
                print lon
                projections = [
                    ccrs.PlateCarree(lon),
                    ccrs.NorthPolarStereo(),
                    ccrs.Robinson(lon),
                ]
                plt.clf()
                plt.suptitle(lon)
                test(projections)
                plt.draw()
                import time
                #time.sleep(1)

########NEW FILE########
__FILENAME__ = test_coastline
# (C) British Crown Copyright 2011 - 2012, Met Office
#
# This file is part of cartopy.
#
# cartopy is free software: you can redistribute it and/or modify it under
# the terms of the GNU Lesser General Public License as published by the
# Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# cartopy is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Lesser General Public License for more details.
#
# You should have received a copy of the GNU Lesser General Public License
# along with cartopy.  If not, see <http://www.gnu.org/licenses/>.
import unittest

import cartopy
import cartopy.io.shapereader as shp

COASTLINE_PATH = shp.natural_earth()


class TestCoastline(unittest.TestCase):
    def test_robust(self):
        # Make sure all the coastlines can be projected without raising any
        # exceptions.
        projection = cartopy.crs.TransverseMercator(central_longitude=-90)
        reader = shp.Reader(COASTLINE_PATH)
        all_geometries = list(reader.geometries())
        geometries = []
        geometries += all_geometries
        #geometries += all_geometries[48:52] # Aus & Taz
        #geometries += all_geometries[72:73] # GB
        #for geometry in geometries:
        for i, geometry in enumerate(geometries[93:]):
            for line_string in geometry:
                multi_line_string = projection.project_geometry(line_string)

if __name__ == '__main__':
    unittest.main()

########NEW FILE########
__FILENAME__ = test_crs
# (C) British Crown Copyright 2011 - 2012, Met Office
#
# This file is part of cartopy.
#
# cartopy is free software: you can redistribute it and/or modify it under
# the terms of the GNU Lesser General Public License as published by the
# Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# cartopy is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Lesser General Public License for more details.
#
# You should have received a copy of the GNU Lesser General Public License
# along with cartopy.  If not, see <http://www.gnu.org/licenses/>.
from __future__ import absolute_import

from io import BytesIO
import pickle
import unittest

import numpy as np
from numpy.testing import assert_array_almost_equal as assert_arr_almost_eq
from nose.tools import assert_equal
import shapely.geometry as sgeom

import cartopy.crs as ccrs


class TestCRS(unittest.TestCase):
    def test_hash(self):
        stereo = ccrs.Stereographic(90)
        north = ccrs.NorthPolarStereo()
        self.assertEqual(stereo, north)
        self.assertFalse(stereo != north)
        self.assertEqual(hash(stereo), hash(north))

        self.assertEqual(ccrs.Geodetic(), ccrs.Geodetic())

    def test_osni(self):
        osni = ccrs.OSNI()
        ll = ccrs.Geodetic()

        # results obtained by nearby.org.uk.
        lat, lon = np.array([54.5622169298669, -5.54159863617957],
                            dtype=np.double)
        east, north = np.array([359000, 371000], dtype=np.double)

        assert_arr_almost_eq(osni.transform_point(lon, lat, ll),
                             np.array([east, north]),
                             -1)
        assert_arr_almost_eq(ll.transform_point(east, north, osni),
                             np.array([lon, lat]),
                             3)

    def test_osgb(self):
        osgb = ccrs.OSGB()
        ll = ccrs.Geodetic()

        # results obtained by streetmap.co.uk.
        lat, lon = np.array([50.462023, -3.478831], dtype=np.double)
        east, north = np.array([295131, 63511], dtype=np.double)

        # note the handling of precision here...
        assert_arr_almost_eq(np.array(osgb.transform_point(lon, lat, ll)),
                             np.array([east, north]),
                             1)
        assert_arr_almost_eq(ll.transform_point(east, north, osgb),
                             [lon, lat],
                             2)

        r_lon, r_lat = ll.transform_point(east, north, osgb)
        r_inverted = np.array(osgb.transform_point(r_lon, r_lat, ll))
        assert_arr_almost_eq(r_inverted, [east, north], 3)

        r_east, r_north = osgb.transform_point(lon, lat, ll)
        r_inverted = np.array(ll.transform_point(r_east, r_north, osgb))
        assert_arr_almost_eq(r_inverted, [lon, lat])

    def test_europp(self):
        europp = ccrs.EuroPP()
        proj4_init = europp.proj4_init
        # Transverse Mercator, UTM zone 32,
        self.assertTrue('+proj=utm' in proj4_init)
        self.assertTrue('+zone=32' in proj4_init)
        # International 1924 ellipsoid.
        self.assertTrue('+ellps=intl' in proj4_init)

    def test_transform_points_nD(self):
        rlons = np.array([[350., 352., 354.], [350., 352., 354.]])
        rlats = np.array([[-5., -0., 1.], [-4., -1., 0.]])

        src_proj = ccrs.RotatedGeodetic(pole_longitude=178.0,
                                        pole_latitude=38.0)
        target_proj = ccrs.Geodetic()
        res = target_proj.transform_points(x=rlons, y=rlats,
                                           src_crs=src_proj)
        unrotated_lon = res[..., 0]
        unrotated_lat = res[..., 1]

        # Solutions derived by proj4 direct.
        solx = np.array([[-16.42176094, -14.85892262, -11.90627520],
                         [-16.71055023, -14.58434624, -11.68799988]])
        soly = np.array([[46.00724251, 51.29188893, 52.59101488],
                         [46.98728486, 50.30706042, 51.60004528]])
        assert_arr_almost_eq(unrotated_lon, solx)
        assert_arr_almost_eq(unrotated_lat, soly)

    def test_transform_points_1D(self):
        rlons = np.array([350., 352., 354., 356.])
        rlats = np.array([-5., -0., 5., 10.])

        src_proj = ccrs.RotatedGeodetic(pole_longitude=178.0,
                                        pole_latitude=38.0)
        target_proj = ccrs.Geodetic()
        res = target_proj.transform_points(x=rlons, y=rlats,
                                           src_crs=src_proj)
        unrotated_lon = res[..., 0]
        unrotated_lat = res[..., 1]

        # Solutions derived by proj4 direct.
        solx = np.array([-16.42176094, -14.85892262,
                         -12.88946157, -10.35078336])
        soly = np.array([46.00724251, 51.29188893,
                         56.55031485, 61.77015703])

        assert_arr_almost_eq(unrotated_lon, solx)
        assert_arr_almost_eq(unrotated_lat, soly)

    def test_globe(self):
        # Ensure the globe affects output.
        rugby_globe = ccrs.Globe(semimajor_axis=9000000,
                                 semiminor_axis=1000000)
        footy_globe = ccrs.Globe(semimajor_axis=1000000,
                                 semiminor_axis=1000000)

        rugby_moll = ccrs.Mollweide(globe=rugby_globe)
        footy_moll = ccrs.Mollweide(globe=footy_globe)

        rugby_pt = rugby_moll.transform_point(10, 10, ccrs.Geodetic())
        footy_pt = footy_moll.transform_point(10, 10, ccrs.Geodetic())

        assert_arr_almost_eq(rugby_pt, (1400915, 1741319), decimal=0)
        assert_arr_almost_eq(footy_pt, (155657, 193479), decimal=0)

    def test_project_point(self):
        point = sgeom.Point([0, 45])
        multi_point = sgeom.MultiPoint([point, sgeom.Point([180, 45])])

        pc = ccrs.PlateCarree()
        pc_rotated = ccrs.PlateCarree(central_longitude=180)

        result = pc_rotated.project_geometry(point, pc)
        assert_arr_almost_eq(result.xy, [[-180.], [45.]])

        result = pc_rotated.project_geometry(multi_point, pc)
        self.assertIsInstance(result, sgeom.MultiPoint)
        self.assertEqual(len(result), 2)
        assert_arr_almost_eq(result[0].xy, [[-180.], [45.]])
        assert_arr_almost_eq(result[1].xy, [[0], [45.]])

    def test_utm(self):
        utm30n = ccrs.UTM(30)
        ll = ccrs.Geodetic()
        lat, lon = np.array([51.5, -3.0], dtype=np.double)
        east, north = np.array([500000, 5705429.2], dtype=np.double)
        assert_arr_almost_eq(utm30n.transform_point(lon, lat, ll),
                             [east, north],
                             decimal=1)
        assert_arr_almost_eq(ll.transform_point(east, north, utm30n),
                             [lon, lat],
                             decimal=1)
        utm38s = ccrs.UTM(38, southern_hemisphere=True)
        lat, lon = np.array([-18.92, 47.5], dtype=np.double)
        east, north = np.array([763316.7, 7906160.8], dtype=np.double)
        assert_arr_almost_eq(utm38s.transform_point(lon, lat, ll),
                             [east, north],
                             decimal=1)
        assert_arr_almost_eq(ll.transform_point(east, north, utm38s),
                             [lon, lat],
                             decimal=1)


def test_pickle():
    # check that we can pickle a simple CRS
    fh = BytesIO()
    pickle.dump(ccrs.PlateCarree(), fh)
    fh.seek(0)
    pc = pickle.load(fh)
    assert pc == ccrs.PlateCarree()


def test_PlateCarree_shortcut():
    central_lons = [[0, 0], [0, 180], [0, 10], [10, 0], [-180, 180], [
        180, -180]]

    target = [([[-180, -180], [-180, 180]], 0),
              ([[-180, 0], [0, 180]], 180),
              ([[-180, -170], [-170, 180]], 10),
              ([[-180, 170], [170, 180]], -10),
              ([[-180, 180], [180, 180]], 360),
              ([[-180, -180], [-180, 180]], -360),
              ]

    assert len(target) == len(central_lons)

    for expected, (s_lon0, t_lon0) in zip(target, central_lons):
        expected_bboxes, expected_offset = expected

        src = ccrs.PlateCarree(central_longitude=s_lon0)
        target = ccrs.PlateCarree(central_longitude=t_lon0)

        bbox, offset = src._bbox_and_offset(target)

        assert_equal(offset, expected_offset)
        assert_equal(bbox, expected_bboxes)


if __name__ == '__main__':
    import nose
    nose.runmodule(argv=['-s', '--with-doctest'], exit=False)

########NEW FILE########
__FILENAME__ = test_crs_transform_vectors
# (C) British Crown Copyright 2013, Met Office
#
# This file is part of cartopy.
#
# cartopy is free software: you can redistribute it and/or modify it under
# the terms of the GNU Lesser General Public License as published by the
# Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# cartopy is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Lesser General Public License for more details.
#
# You should have received a copy of the GNU Lesser General Public License
# along with cartopy.  If not, see <http://www.gnu.org/licenses/>.


import unittest
import warnings

import numpy as np
from numpy.testing import assert_array_almost_equal

import cartopy.crs as ccrs


class TestTransformVectors(unittest.TestCase):

    def test_transform(self):
        # Test some simple vectors to make sure they are transformed
        # correctly.
        rlons = np.array([-90., 0, 90., 180.])
        rlats = np.array([0., 0., 0., 0.])
        src_proj = ccrs.PlateCarree()
        target_proj = ccrs.Stereographic(central_latitude=90,
                                         central_longitude=0)
        # transform grid eastward vectors
        ut, vt = target_proj.transform_vectors(src_proj,
                                               rlons,
                                               rlats,
                                               np.ones([4]),
                                               np.zeros([4]))
        assert_array_almost_equal(ut, np.array([0, 1, 0, -1]), decimal=2)
        assert_array_almost_equal(vt, np.array([-1, 0, 1, 0]), decimal=2)
        # transform grid northward vectors
        ut, vt = target_proj.transform_vectors(src_proj,
                                               rlons,
                                               rlats,
                                               np.zeros([4]),
                                               np.ones([4]))
        assert_array_almost_equal(ut, np.array([1, 0, -1, 0]), decimal=2)
        assert_array_almost_equal(vt, np.array([0, 1, 0, -1]), decimal=2)
        # transform grid north-eastward vectors
        ut, vt = target_proj.transform_vectors(src_proj,
                                               rlons,
                                               rlats,
                                               np.ones([4]),
                                               np.ones([4]))
        assert_array_almost_equal(ut, np.array([1, 1, -1, -1]), decimal=2)
        assert_array_almost_equal(vt, np.array([-1, 1, 1, -1]), decimal=2)

    def test_transform_and_inverse(self):
        # Check a full circle transform back to the native projection.
        x = np.arange(-60, 42.5, 2.5)
        y = np.arange(30, 72.5, 2.5)
        x2d, y2d = np.meshgrid(x, y)
        u = np.cos(np.deg2rad(y2d))
        v = np.cos(2. * np.deg2rad(x2d))
        src_proj = ccrs.PlateCarree()
        target_proj = ccrs.Stereographic(central_latitude=90,
                                         central_longitude=0)
        proj_xyz = target_proj.transform_points(src_proj, x2d, y2d)
        xt, yt = proj_xyz[..., 0], proj_xyz[..., 1]
        ut, vt = target_proj.transform_vectors(src_proj, x2d, y2d, u, v)
        utt, vtt = src_proj.transform_vectors(target_proj, xt, yt, ut, vt)
        assert_array_almost_equal(u, utt, decimal=4)
        assert_array_almost_equal(v, vtt, decimal=4)

    def test_invalid_input_domain(self):
        # If an input coordinate is outside the input projection domain
        # we should be able to handle it correctly.
        rlon = np.array([270.])
        rlat = np.array([0.])
        u = np.array([1.])
        v = np.array([0.])
        src_proj = ccrs.PlateCarree()
        target_proj = ccrs.Stereographic(central_latitude=90,
                                         central_longitude=0)
        ut, vt = target_proj.transform_vectors(src_proj, rlon, rlat, u, v)
        assert_array_almost_equal(ut, np.array([0]), decimal=2)
        assert_array_almost_equal(vt, np.array([-1]), decimal=2)

    def test_invalid_x_domain(self):
        # If the point we need to calculate the vector angle falls outside the
        # source projection x-domain it should be handled correctly as long as
        # it is not a corner point.
        rlon = np.array([180.])
        rlat = np.array([0.])
        u = np.array([1.])
        v = np.array([0.])
        src_proj = ccrs.PlateCarree()
        target_proj = ccrs.Stereographic(central_latitude=90,
                                         central_longitude=0)
        ut, vt = target_proj.transform_vectors(src_proj, rlon, rlat, u, v)
        assert_array_almost_equal(ut, np.array([-1]), decimal=2)
        assert_array_almost_equal(vt, np.array([0.]), decimal=2)

    def test_invalid_y_domain(self):
        # If the point we need to calculate the vector angle falls outside the
        # source projection y-domain it should be handled correctly as long as
        # it is not a corner point.
        rlon = np.array([0.])
        rlat = np.array([90.])
        u = np.array([0.])
        v = np.array([1.])
        src_proj = ccrs.PlateCarree()
        target_proj = ccrs.Stereographic(central_latitude=90,
                                         central_longitude=0)
        ut, vt = target_proj.transform_vectors(src_proj, rlon, rlat, u, v)
        assert_array_almost_equal(ut, np.array([0.]), decimal=2)
        assert_array_almost_equal(vt, np.array([1.]), decimal=2)

    def test_invalid_xy_domain_corner(self):
        # If the point we need to calculate the vector angle falls outside the
        # source projection x and y-domain it should be handled correctly.
        rlon = np.array([180.])
        rlat = np.array([90.])
        u = np.array([1.])
        v = np.array([1.])
        src_proj = ccrs.PlateCarree()
        target_proj = ccrs.Stereographic(central_latitude=90,
                                         central_longitude=0)
        ut, vt = target_proj.transform_vectors(src_proj, rlon, rlat, u, v)
        assert_array_almost_equal(ut, np.array([0.]), decimal=2)
        assert_array_almost_equal(vt, np.array([-2**.5]), decimal=2)

    def test_invalid_x_domain_corner(self):
        # If the point we need to calculate the vector angle falls outside the
        # source projection x-domain and is a corner point, it may be handled
        # incorrectly and a warning should be raised.
        rlon = np.array([180.])
        rlat = np.array([90.])
        u = np.array([1.])
        v = np.array([-1.])
        src_proj = ccrs.PlateCarree()
        target_proj = ccrs.Stereographic(central_latitude=90,
                                         central_longitude=0)
        with warnings.catch_warnings():
            warnings.simplefilter('error')
            with self.assertRaises(UserWarning):
                ut, vt = target_proj.transform_vectors(
                    src_proj, rlon, rlat, u, v)

    def test_invalid_y_domain_corner(self):
        # If the point we need to calculate the vector angle falls outside the
        # source projection y-domain and is a corner point, it may be handled
        # incorrectly and a warning should be raised.
        rlon = np.array([180.])
        rlat = np.array([90.])
        u = np.array([-1.])
        v = np.array([1.])
        src_proj = ccrs.PlateCarree()
        target_proj = ccrs.Stereographic(central_latitude=90,
                                         central_longitude=0)
        with warnings.catch_warnings():
            warnings.simplefilter('error')
            with self.assertRaises(UserWarning):
                ut, vt = target_proj.transform_vectors(
                    src_proj, rlon, rlat, u, v)

########NEW FILE########
__FILENAME__ = test_img_nest
# (C) British Crown Copyright 2011 - 2014, Met Office
#
# This file is part of cartopy.
#
# cartopy is free software: you can redistribute it and/or modify it under
# the terms of the GNU Lesser General Public License as published by the
# Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# cartopy is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Lesser General Public License for more details.
#
# You should have received a copy of the GNU Lesser General Public License
# along with cartopy.  If not, see <http://www.gnu.org/licenses/>.
from __future__ import division, absolute_import

import io
import cPickle as pickle
import os
import shutil
import warnings

from nose.tools import assert_equal, assert_in, assert_true
import numpy as np
from numpy.testing import assert_array_equal, assert_array_almost_equal
import PIL.Image
import shapely.geometry as sgeom

from cartopy import config
import cartopy.crs as ccrs
import cartopy.io.img_tiles as cimgt
import cartopy.io.img_nest as cimg_nest
import cartopy.tests as tests


#: An integer version which should be increased if the test data needs
#: to change in some way.
_TEST_DATA_VERSION = 1
_TEST_DATA_DIR = os.path.join(config["data_dir"],
                              'wmts', 'aerial')
#: A global to determine whether the test data has already been made available
#: in this session.
_TEST_DATA_AVAILABLE = False


def test_world_files():
    func = cimg_nest.Img.world_files
    fname = 'one'
    expected = ['one.w', 'one.W', 'ONE.w', 'ONE.W']
    assert_equal(func(fname), expected)

    fname = 'one.png'
    expected = ['one.pngw', 'one.pgw', 'one.PNGW', 'one.PGW',
                'ONE.pngw', 'ONE.pgw', 'ONE.PNGW', 'ONE.PGW']
    assert_equal(func(fname), expected)

    fname = '/one.png'
    expected = ['/one.pngw', '/one.pgw', '/one.PNGW', '/one.PGW',
                '/ONE.pngw', '/ONE.pgw', '/ONE.PNGW', '/ONE.PGW']
    assert_equal(func(fname), expected)

    fname = '/one/two.png'
    expected = ['/one/two.pngw', '/one/two.pgw',
                '/one/two.PNGW', '/one/two.PGW',
                '/one/TWO.pngw', '/one/TWO.pgw',
                '/one/TWO.PNGW', '/one/TWO.PGW']
    assert_equal(func(fname), expected)

    fname = '/one/two/THREE.png'
    expected = ['/one/two/THREE.pngw', '/one/two/THREE.pgw',
                '/one/two/THREE.PNGW', '/one/two/THREE.PGW',
                '/one/two/three.pngw', '/one/two/three.pgw',
                '/one/two/three.PNGW', '/one/two/three.PGW']
    assert_equal(func(fname), expected)


def _save_world(fname, args):
    _world = ('{x_pix_size}\n'
              '{y_rotation}\n'
              '{x_rotation}\n'
              '{y_pix_size}\n'
              '{x_center}\n'
              '{y_center}\n')
    with open(fname, 'w') as fh:
        fh.write(_world.format(**args))


def test_intersect():
    with tests.temp_dir() as base_dir:
        # Zoom level zero.
        # File 1: Parent space of all images.
        z_0_dir = os.path.join(base_dir, 'z_0')
        os.mkdir(z_0_dir)
        world = dict(x_pix_size=2, y_rotation=0, x_rotation=0,
                     y_pix_size=2, x_center=1, y_center=1)
        im = PIL.Image.new('RGB', (50, 50))
        fname = os.path.join(z_0_dir, 'p0.tfw')
        _save_world(fname, world)
        fname = os.path.join(z_0_dir, 'p0.tif')
        im.save(fname)

        # Zoom level one.
        # File 1: complete containment within p0.
        z_1_dir = os.path.join(base_dir, 'z_1')
        os.mkdir(z_1_dir)
        world = dict(x_pix_size=2, y_rotation=0, x_rotation=0,
                     y_pix_size=2, x_center=21, y_center=21)
        im = PIL.Image.new('RGB', (30, 30))
        fname = os.path.join(z_1_dir, 'p1.tfw')
        _save_world(fname, world)
        fname = os.path.join(z_1_dir, 'p1.tif')
        im.save(fname)

        # Zoom level two.
        # File 1: intersect right edge with p1 left edge.
        z_2_dir = os.path.join(base_dir, 'z_2')
        os.mkdir(z_2_dir)
        world = dict(x_pix_size=2, y_rotation=0, x_rotation=0,
                     y_pix_size=2, x_center=6, y_center=21)
        im = PIL.Image.new('RGB', (5, 5))
        fname = os.path.join(z_2_dir, 'p2-1.tfw')
        _save_world(fname, world)
        fname = os.path.join(z_2_dir, 'p2-1.tif')
        im.save(fname)
        # File 2: intersect upper right corner with p1
        #         lower left corner.
        world = dict(x_pix_size=2, y_rotation=0, x_rotation=0,
                     y_pix_size=2, x_center=6, y_center=6)
        im = PIL.Image.new('RGB', (5, 5))
        fname = os.path.join(z_2_dir, 'p2-2.tfw')
        _save_world(fname, world)
        fname = os.path.join(z_2_dir, 'p2-2.tif')
        im.save(fname)
        # File 3: complete containment within p1.
        world = dict(x_pix_size=2, y_rotation=0, x_rotation=0,
                     y_pix_size=2, x_center=41, y_center=41)
        im = PIL.Image.new('RGB', (5, 5))
        fname = os.path.join(z_2_dir, 'p2-3.tfw')
        _save_world(fname, world)
        fname = os.path.join(z_2_dir, 'p2-3.tif')
        im.save(fname)
        # File 4: overlap with p1 right edge.
        world = dict(x_pix_size=2, y_rotation=0, x_rotation=0,
                     y_pix_size=2, x_center=76, y_center=61)
        im = PIL.Image.new('RGB', (5, 5))
        fname = os.path.join(z_2_dir, 'p2-4.tfw')
        _save_world(fname, world)
        fname = os.path.join(z_2_dir, 'p2-4.tif')
        im.save(fname)
        # File 5: overlap with p1 bottom right corner.
        world = dict(x_pix_size=2, y_rotation=0, x_rotation=0,
                     y_pix_size=2, x_center=76, y_center=76)
        im = PIL.Image.new('RGB', (5, 5))
        fname = os.path.join(z_2_dir, 'p2-5.tfw')
        _save_world(fname, world)
        fname = os.path.join(z_2_dir, 'p2-5.tif')
        im.save(fname)

        # Provided in reverse order in order to test the area sorting.
        items = [('dummy-z-2', z_2_dir),
                 ('dummy-z-1', z_1_dir),
                 ('dummy-z-0', z_0_dir)]
        nic = cimg_nest.NestedImageCollection.from_configuration('dummy',
                                                                 None,
                                                                 items)

        names = [collection.name for collection in nic._collections]
        zoom_levels = ['dummy-z-0', 'dummy-z-1', 'dummy-z-2']
        assert_true(names, zoom_levels)

        # Check all images are loaded.
        for zoom, expected_image_count in zip(zoom_levels, [1, 1, 5]):
            images = nic._collections_by_name[zoom].images
            assert_equal(len(images), expected_image_count)

        # Check the image ancestry.
        zoom_levels = ['dummy-z-0', 'dummy-z-1']
        assert_equal(sorted(k[0] for k in nic._ancestry.keys()),
                     zoom_levels)

        expected = [('dummy-z-0', ['p1.tif']),
                    ('dummy-z-1', ['p2-3.tif', 'p2-4.tif', 'p2-5.tif'])]
        for zoom, image_names in expected:
            key = [k for k in nic._ancestry.keys() if k[0] == zoom][0]
            ancestry = nic._ancestry[key]
            fnames = sorted([os.path.basename(item[1].filename)
                             for item in ancestry])
            assert_equal(image_names, fnames)

        # Check image retrieval for specific domain.
        items = [(sgeom.box(20, 20, 80, 80), 3),
                 (sgeom.box(20, 20, 75, 75), 1),
                 (sgeom.box(40, 40, 85, 85), 3)]
        for domain, expected in items:
            result = [image for image in nic.find_images(domain,
                                                         'dummy-z-2')]
            assert_equal(len(result), expected)


def _tile_from_img(img):
    """
    Turns an img into the appropriate x, y, z tile based on its filename.

    Imgs have a filename attribute which is something
    like "lib/cartopy/data/wmts/aerial/z_0/x_0_y0.png"

    """
    _, z = os.path.basename(os.path.dirname(img.filename)).split('_')
    xy, _ = os.path.splitext(os.path.basename(img.filename))
    _, x, _, y = xy.split('_')
    return int(x), int(y), int(z)


class RoundedImg(cimg_nest.Img):
    @staticmethod
    def world_file_extent(*args, **kwargs):
        """
        Takes account for the fact that the image tiles are stored with
        imprecise tfw files.

        """
        extent, pix_size = cimg_nest.Img.world_file_extent(*args, **kwargs)
        # round the extent
        extent = tuple(round(v, 4) for v in extent)
        pix_size = tuple(round(v, 4) for v in pix_size)
        return extent, pix_size


def test_nest():
    crs = cimgt.GoogleTiles().crs
    z0 = cimg_nest.ImageCollection('aerial z0 test', crs)
    z0.scan_dir_for_imgs(os.path.join(_TEST_DATA_DIR, 'z_0'),
                         glob_pattern='*.png', img_class=RoundedImg)

    z1 = cimg_nest.ImageCollection('aerial z1 test', crs)
    z1.scan_dir_for_imgs(os.path.join(_TEST_DATA_DIR, 'z_1'),
                         glob_pattern='*.png', img_class=RoundedImg)

    z2 = cimg_nest.ImageCollection('aerial z2 test', crs)
    z2.scan_dir_for_imgs(os.path.join(_TEST_DATA_DIR, 'z_2'),
                         glob_pattern='*.png', img_class=RoundedImg)

    # make sure all the images from z1 are contained by the z0 image. The
    # only reason this might occur is if the tfw files are handling
    # floating point values badly
    for img in z1.images:
        if not z0.images[0].bbox().contains(img.bbox()):
            raise IOError('The test images aren\'t all "contained" by the '
                          'z0 images, the nest cannot possibly work.\n '
                          'img {!s} not contained by {!s}\nExtents: {!s}; '
                          '{!s}'.format(img, z0.images[0], img.extent,
                                        z0.images[0].extent))
    nest_z0_z1 = cimg_nest.NestedImageCollection('aerial test',
                                                 crs,
                                                 [z0, z1])

    nest = cimg_nest.NestedImageCollection('aerial test', crs, [z0, z1, z2])

    z0_key = ('aerial z0 test', z0.images[0])

    assert_true(z0_key in nest_z0_z1._ancestry.keys())
    assert_equal(len(nest_z0_z1._ancestry), 1)

    # check that it has figured out that all the z1 images are children of
    # the only z0 image
    for img in z1.images:
        key = ('aerial z0 test', z0.images[0])
        assert_in(('aerial z1 test', img), nest_z0_z1._ancestry[key])

    x1_y0_z1, = [img for img in z1.images
                 if img.filename.endswith('z_1/x_1_y_0.png')]

    assert_equal((1, 0, 1), _tile_from_img(x1_y0_z1))

    assert_equal([(2, 0, 2), (2, 1, 2), (3, 0, 2), (3, 1, 2)],
                 sorted([_tile_from_img(img) for z, img in
                         nest.subtiles(('aerial z1 test', x1_y0_z1))]))

    nest_from_config = gen_nest()
    # check that the the images in the nest from configuration are the
    # same as those created by hand.
    for name in nest_z0_z1._collections_by_name.keys():
        for img in nest_z0_z1._collections_by_name[name].images:
            collection = nest_from_config._collections_by_name[name]
            assert_in(img, collection.images)

    assert_equal(nest_z0_z1._ancestry, nest_from_config._ancestry)

    # check that a nest can be pickled and unpickled easily.
    s = io.BytesIO()
    pickle.dump(nest_z0_z1, s)
    s.seek(0)
    nest_z0_z1_from_pickle = pickle.load(s)

    assert_equal(nest_z0_z1._ancestry,
                 nest_z0_z1_from_pickle._ancestry)


def test_img_pickle_round_trip():
    """Check that __getstate__ for Img instances is working correctly."""

    img = cimg_nest.Img('imaginary file', (0, 1, 2, 3), 'lower', (1, 2))
    img_from_pickle = pickle.loads(pickle.dumps(img))
    assert_equal(img, img_from_pickle)
    assert_equal(hasattr(img_from_pickle, '_bbox'), True)


def requires_wmts_data(function):
    """
    A decorator which ensures that the WMTS data is available for
    use in testing.

    """
    aerial = cimgt.MapQuestOpenAerial()

    # get web tiles upto 3 zoom levels deep
    tiles = [(0, 0, 0)]
    for tile in aerial.subtiles((0, 0, 0)):
        tiles.append(tile)
    for tile in tiles[1:]:
        for sub_tile in aerial.subtiles(tile):
            tiles.append(sub_tile)

    fname_template = os.path.join(_TEST_DATA_DIR, 'z_{}', 'x_{}_y_{}.png')

    if not os.path.isdir(_TEST_DATA_DIR):
        os.makedirs(_TEST_DATA_DIR)

    data_version_fname = os.path.join(_TEST_DATA_DIR, 'version.txt')

    test_data_version = None
    try:
        with open(data_version_fname, 'r') as fh:
            test_data_version = int(fh.read().strip())
    except IOError:
        pass
    finally:
        if test_data_version != _TEST_DATA_VERSION:
            warnings.warn('WMTS test data is out of date, regenerating at '
                          '{}.'.format(_TEST_DATA_DIR))
            shutil.rmtree(_TEST_DATA_DIR)
            os.makedirs(_TEST_DATA_DIR)
            with open(data_version_fname, 'w') as fh:
                fh.write(str(_TEST_DATA_VERSION))

    # Download the tiles.
    for tile in tiles:
        x, y, z = tile
        fname = fname_template.format(z, x, y)
        if not os.path.exists(fname):
            if not os.path.isdir(os.path.dirname(fname)):
                os.makedirs(os.path.dirname(fname))

            img, extent, _ = aerial.get_image(tile)
            nx, ny = 256, 256
            x_rng = extent[1] - extent[0]
            y_rng = extent[3] - extent[2]

            pix_size_x = x_rng / nx
            pix_size_y = y_rng / ny

            upper_left_center = (extent[0] + pix_size_x / 2,
                                 extent[2] + pix_size_y / 2)

            pgw_fname = fname[:-4] + '.pgw'
            pgw_keys = {'x_pix_size': np.float64(pix_size_x),
                        'y_rotation': 0,
                        'x_rotation': 0,
                        'y_pix_size': np.float64(pix_size_y),
                        'x_center': np.float64(upper_left_center[0]),
                        'y_center': np.float64(upper_left_center[1]),
                        }
            _save_world(pgw_fname, pgw_keys)
            img.save(fname)

    global _TEST_DATA_AVAILABLE
    _TEST_DATA_AVAILABLE = True

    return function


@requires_wmts_data
def test_find_images():
    z2_dir = os.path.join(_TEST_DATA_DIR, 'z_2')
    img_fname = os.path.join(z2_dir, 'x_2_y_0.png')
    world_file_fname = os.path.join(z2_dir, 'x_2_y_0.pgw')
    img = RoundedImg.from_world_file(img_fname, world_file_fname)

    assert_equal(img.filename, img_fname)
    assert_array_almost_equal(img.extent,
                              (0., 10018754.17139462,
                               10018754.17139462, 20037508.342789244),
                              decimal=4)
    assert_equal(img.origin, 'lower')
    assert_array_equal(img, np.array(PIL.Image.open(img.filename)))
    assert_equal(img.pixel_size, (39135.7585, 39135.7585))


@requires_wmts_data
def gen_nest():
    from_config = cimg_nest.NestedImageCollection.from_configuration

    files = [['aerial z0 test', os.path.join(_TEST_DATA_DIR, 'z_0')],
             ['aerial z1 test', os.path.join(_TEST_DATA_DIR, 'z_1')],
             ]

    crs = cimgt.GoogleTiles().crs

    nest_z0_z1 = from_config('aerial test',
                             crs, files, glob_pattern='*.png',
                             img_class=RoundedImg)
    return nest_z0_z1


if __name__ == '__main__':
    import nose
    nose.runmodule(argv=['-s', '--with-doctest'], exit=False)

########NEW FILE########
__FILENAME__ = test_img_tiles
# (C) British Crown Copyright 2011 - 2012, Met Office
#
# This file is part of cartopy.
#
# cartopy is free software: you can redistribute it and/or modify it under
# the terms of the GNU Lesser General Public License as published by the
# Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# cartopy is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Lesser General Public License for more details.
#
# You should have received a copy of the GNU Lesser General Public License
# along with cartopy.  If not, see <http://www.gnu.org/licenses/>.

import types

from nose.tools import assert_equal, assert_raises
import numpy as np
from numpy.testing import assert_array_almost_equal as assert_arr_almost
import shapely.geometry as sgeom

import cartopy.crs as ccrs
import cartopy.io.img_tiles as cimgt


#: Maps Google tile coordinates to native mercator coordinates as defined
#: by http://goo.gl/pgJi.
KNOWN_EXTENTS = {(0, 0, 0): (-20037508.342789244, 20037508.342789244,
                             -20037508.342789244, 20037508.342789244),
                 (2, 0, 2): (0., 10018754.17139462,
                             10018754.17139462, 20037508.342789244),
                 (0, 2, 2): (-20037508.342789244, -10018754.171394622,
                             -10018754.171394622, 0),
                 (2, 2, 2): (0, 10018754.17139462,
                             -10018754.171394622, 0),
                 (8, 9, 4): (0, 2504688.542848654,
                             -5009377.085697312, -2504688.542848654),
                 }


def GOOGLE_IMAGE_URL_REPLACEMENT(self, tile):
    url = ('http://chart.apis.google.com/chart?chst=d_text_outline&'
           'chs=256x256&chf=bg,s,00000055&chld=FFFFFF|16|h|000000|b||||'
           'Google:%20%20(' + str(tile[0]) + ',' + str(tile[1]) + ')'
           '|Zoom%20' + str(tile[2]) + '||||||______________________'
           '______')
    return url


def test_google_tile_styles():
    """
    Tests that settings the Google Maps tile style works as expected.

    This is essentially just assures information is properly propagated through
    the class structure.
    """
    reference_url = ("http://mts0.google.com/vt/lyrs={style}@177000000&hl=en"
                     "&src=api&x=1&y=2&z=3&s=G")
    tile = ["1", "2", "3"]

    # Default is street.
    gt = cimgt.GoogleTiles()
    url = gt._image_url(tile)
    assert_equal(reference_url.format(style="m"), url)

    # Street
    gt = cimgt.GoogleTiles(style="street")
    url = gt._image_url(tile)
    assert_equal(reference_url.format(style="m"), url)

    # Satellite
    gt = cimgt.GoogleTiles(style="satellite")
    url = gt._image_url(tile)
    assert_equal(reference_url.format(style="s"), url)

    # Terrain
    gt = cimgt.GoogleTiles(style="terrain")
    url = gt._image_url(tile)
    assert_equal(reference_url.format(style="t"), url)

    # Streets only
    gt = cimgt.GoogleTiles(style="only_streets")
    url = gt._image_url(tile)
    assert_equal(reference_url.format(style="h"), url)

    # Exception is raised if unknown style is passed.
    with assert_raises(ValueError):
        cimgt.GoogleTiles(style="random_style")


def test_google_wts():
    gt = cimgt.GoogleTiles()

    ll_target_domain = sgeom.box(-15, 50, 0, 60)
    multi_poly = gt.crs.project_geometry(ll_target_domain, ccrs.PlateCarree())
    target_domain = multi_poly.geoms[0]

    with assert_raises(AssertionError):
        list(gt.find_images(target_domain, -1))
    assert_equal(tuple(gt.find_images(target_domain, 0)),
                 ((0, 0, 0),))
    assert_equal(tuple(gt.find_images(target_domain, 2)),
                 ((1, 1, 2), (2, 1, 2)))

    assert_equal(list(gt.subtiles((0, 0, 0))),
                 [(0, 0, 1), (0, 1, 1), (1, 0, 1), (1, 1, 1)])
    assert_equal(list(gt.subtiles((1, 0, 1))),
                 [(2, 0, 2), (2, 1, 2), (3, 0, 2), (3, 1, 2)])

    with assert_raises(AssertionError):
        gt.tileextent((0, 1, 0))

    assert_arr_almost(gt.tileextent((0, 0, 0)), KNOWN_EXTENTS[(0, 0, 0)])
    assert_arr_almost(gt.tileextent((2, 0, 2)), KNOWN_EXTENTS[(2, 0, 2)])
    assert_arr_almost(gt.tileextent((0, 2, 2)), KNOWN_EXTENTS[(0, 2, 2)])
    assert_arr_almost(gt.tileextent((2, 2, 2)), KNOWN_EXTENTS[(2, 2, 2)])
    assert_arr_almost(gt.tileextent((8, 9, 4)), KNOWN_EXTENTS[(8, 9, 4)])


def test_tile_bbox_y0_at_south_pole():
    tms = cimgt.MapQuestOpenAerial()

    # Check the y0_at_north_pole keywords returns the appropriate bounds.
    assert_arr_almost(tms.tile_bbox(8, 6, 4, y0_at_north_pole=False),
                      np.array(KNOWN_EXTENTS[(8, 9, 4)]).reshape([2, 2]))


def test_tile_find_images():
    gt = cimgt.GoogleTiles()
    # Test the find_images method on a GoogleTiles instance.
    ll_target_domain = sgeom.box(-10, 50, 10, 60)
    multi_poly = gt.crs.project_geometry(ll_target_domain, ccrs.PlateCarree())
    target_domain = multi_poly.geoms[0]

    assert_equal([(7, 4, 4), (7, 5, 4), (8, 4, 4), (8, 5, 4)],
                 list(gt.find_images(target_domain, 4)))


def test_image_for_domain():
    gt = cimgt.GoogleTiles()
    gt._image_url = types.MethodType(GOOGLE_IMAGE_URL_REPLACEMENT, gt)

    ll_target_domain = sgeom.box(-10, 50, 10, 60)
    multi_poly = gt.crs.project_geometry(ll_target_domain, ccrs.PlateCarree())
    target_domain = multi_poly.geoms[0]

    _, extent, _ = gt.image_for_domain(target_domain, 6)

    ll_extent = ccrs.Geodetic().transform_points(gt.crs,
                                                 np.array(extent[:2]),
                                                 np.array(extent[2:]))
    assert_arr_almost(ll_extent[:, :2],
                      [[-11.25, 48.92249926],
                       [11.25, 61.60639637]])


def test_quadtree_wts():
    qt = cimgt.QuadtreeTiles()

    ll_target_domain = sgeom.box(-15, 50, 0, 60)
    multi_poly = qt.crs.project_geometry(ll_target_domain, ccrs.PlateCarree())
    target_domain = multi_poly.geoms[0]

    with assert_raises(ValueError):
        list(qt.find_images(target_domain, 0))

    assert_equal(qt.tms_to_quadkey((1, 1, 1)), '1')
    assert_equal(qt.quadkey_to_tms('1'), (1, 1, 1))

    assert_equal(qt.tms_to_quadkey((8, 9, 4)), '1220')
    assert_equal(qt.quadkey_to_tms('1220'), (8, 9, 4))

    assert_equal(tuple(qt.find_images(target_domain, 1)), ('0', '1'))
    assert_equal(tuple(qt.find_images(target_domain, 2)), ('03', '12'))

    assert_equal(list(qt.subtiles('0')), ['00', '01', '02', '03'])
    assert_equal(list(qt.subtiles('11')), ['110', '111', '112', '113'])

    with assert_raises(ValueError):
        qt.tileextent('4')

    assert_arr_almost(qt.tileextent(''), KNOWN_EXTENTS[(0, 0, 0)])
    assert_arr_almost(qt.tileextent(qt.tms_to_quadkey((2, 0, 2), google=True)),
                      KNOWN_EXTENTS[(2, 0, 2)])
    assert_arr_almost(qt.tileextent(qt.tms_to_quadkey((0, 2, 2), google=True)),
                      KNOWN_EXTENTS[(0, 2, 2)])
    assert_arr_almost(qt.tileextent(qt.tms_to_quadkey((2, 0, 2), google=True)),
                      KNOWN_EXTENTS[(2, 0, 2)])
    assert_arr_almost(qt.tileextent(qt.tms_to_quadkey((2, 2, 2), google=True)),
                      KNOWN_EXTENTS[(2, 2, 2)])
    assert_arr_almost(qt.tileextent(qt.tms_to_quadkey((8, 9, 4), google=True)),
                      KNOWN_EXTENTS[(8, 9, 4)])


if __name__ == '__main__':
    import nose
    nose.runmodule(argv=['-s', '--with-doctest'], exit=False)

########NEW FILE########
__FILENAME__ = test_img_transform
# (C) British Crown Copyright 2014, Met Office
#
# This file is part of cartopy.
#
# cartopy is free software: you can redistribute it and/or modify it under
# the terms of the GNU Lesser General Public License as published by the
# Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# cartopy is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Lesser General Public License for more details.
#
# You should have received a copy of the GNU Lesser General Public License
# along with cartopy.  If not, see <http://www.gnu.org/licenses/>.
import numpy as np
from numpy.testing import assert_array_equal

import cartopy.img_transform as img_trans
import cartopy.crs as ccrs


def test_griding_data_std_range():
    # Data which exists inside the standard projection bounds i.e.
    # [-180, 180].
    target_prj = ccrs.PlateCarree()
    # create 3 data points
    lats = np.array([65, 10, -45])
    lons = np.array([-90, 0, 90])
    data = np.array([1, 2, 3])
    data_trans = ccrs.Geodetic()

    target_x, target_y, extent = img_trans.mesh_projection(target_prj, 8, 4)

    image = img_trans.regrid(data, lons, lats, data_trans, target_prj,
                             target_x, target_y,
                             mask_extrapolated=True)

    # The expected image. n.b. on a map the data is reversed in the y axis.
    expected = np.array([[3, 3, 3, 3, 3, 3, 3, 3],
                         [3, 1, 2, 2, 2, 3, 3, 3],
                         [1, 1, 1, 2, 2, 2, 3, 1],
                         [1, 1, 1, 1, 1, 1, 1, 1]], dtype=np.float64)

    expected_mask = np.array(
        [[True, True, True, True, True, True, True, True],
         [True, False, False, False, False, False, False, True],
         [True, False, False, False, False, False, False, True],
         [True, True, True, True, True, True, True, True]])

    assert_array_equal([-180, 180, -90, 90], extent)
    assert_array_equal(expected, image)
    assert_array_equal(expected_mask, image.mask)


def test_griding_data_outside_projection():
    # Data which exists outside the standard projection e.g. [0, 360] rather
    # than [-180, 180].
    target_prj = ccrs.PlateCarree()
    # create 3 data points
    lats = np.array([65, 10, -45])
    lons = np.array([120, 180, 240])
    data = np.array([1, 2, 3])
    data_trans = ccrs.Geodetic()

    target_x, target_y, extent = img_trans.mesh_projection(target_prj, 8, 4)

    image = img_trans.regrid(data, lons, lats, data_trans, target_prj,
                             target_x, target_y,
                             mask_extrapolated=True)

    # The expected image. n.b. on a map the data is reversed in the y axis.
    expected = np.array(
        [[3, 3, 3, 3, 3, 3, 3, 3],
         [3, 3, 3, 3, 3, 1, 2, 2],
         [2, 2, 3, 1, 1, 1, 1, 2],
         [1, 1, 1, 1, 1, 1, 1, 1]], dtype=np.float64)

    expected_mask = np.array(
        [[True, True, True, True, True, True, True, True],
         [False, False, True, True, True, True, False, False],
         [False, False, True, True, True, True, False, False],
         [True, True, True, True, True, True, True, True]])

    assert_array_equal([-180, 180, -90, 90], extent)
    assert_array_equal(expected, image)
    assert_array_equal(expected_mask, image.mask)


if __name__ == '__main__':
    import nose
    nose.runmodule(argv=['-sv', '--with-doctest'], exit=False)

########NEW FILE########
__FILENAME__ = test_linear_ring
# (C) British Crown Copyright 2011 - 2012, Met Office
#
# This file is part of cartopy.
#
# cartopy is free software: you can redistribute it and/or modify it under
# the terms of the GNU Lesser General Public License as published by the
# Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# cartopy is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Lesser General Public License for more details.
#
# You should have received a copy of the GNU Lesser General Public License
# along with cartopy.  If not, see <http://www.gnu.org/licenses/>.


import unittest

from shapely import geometry
import numpy as np

import cartopy.crs as ccrs


class TestBoundary(unittest.TestCase):
    def test_cuts(self):
        # Check that fragments do not start or end with one of the
        # original ... ?
        linear_ring = geometry.polygon.LinearRing([(-10, 30),
                                                   (10, 60),
                                                   (10, 50)])
        projection = ccrs.Robinson(170.5)
        multi_line_string = projection.project_geometry(linear_ring)
        from cartopy.tests import show
        #show(projection, multi_line_string)

        # The original ring should have been split into multiple pieces.
        self.assertGreater(len(multi_line_string), 1)

        def assert_intersection_with_boundary(segment_coords):
            # Double the length of the segment.
            start = segment_coords[0]
            end = segment_coords[1]
            end = [end[i] + 2 * (end[i] - start[i]) for i in (0, 1)]
            extended_segment = geometry.LineString([start, end])
            # And see if it crosses the boundary.
            intersection = extended_segment.intersection(projection.boundary)
            self.assertFalse(intersection.is_empty,
                             'Bad topology near boundary')

        # Each line resulting from the split should start and end with a
        # segment that crosses the boundary when extended to double length.
        # (This is important when considering polygon rings which need to be
        # attached to the boundary.)
        for line_string in multi_line_string:
            coords = list(line_string.coords)
            self.assertGreaterEqual(len(coords), 2)
            assert_intersection_with_boundary(coords[1::-1])
            assert_intersection_with_boundary(coords[-2:])

    def test_out_of_bounds(self):
        # Check that a ring that is completely out of the map boundary
        # produces an empty result.
        # XXX Check efficiency?
        projection = ccrs.TransverseMercator(central_longitude=0)

        rings = [
            # All valid
            ([(86, 1), (86, -1), (88, -1), (88, 1)], -1),
            # One NaN
            ([(86, 1), (86, -1), (130, -1), (88, 1)], 1),
            # A NaN segment
            ([(86, 1), (86, -1), (130, -1), (130, 1)], 1),
            # All NaN
            ([(120, 1), (120, -1), (130, -1), (130, 1)], 0),
        ]

        # Try all four combinations of valid/NaN vs valid/NaN.
        for coords, expected_n_lines in rings:
            linear_ring = geometry.polygon.LinearRing(coords)
            projected = projection.project_geometry(linear_ring)
            if expected_n_lines == -1:
                self.assertIsInstance(projected, geometry.polygon.LinearRing)
            else:
                self.assertEqual(len(projected), expected_n_lines)
                if expected_n_lines == 0:
                    self.assertTrue(projected.is_empty)


class TestMisc(unittest.TestCase):
    def test_misc(self):
        projection = ccrs.TransverseMercator(central_longitude=-90)
        linear_ring = geometry.polygon.LinearRing([(-10, 30),
                                                   (10, 60),
                                                   (10, 50)])
        multi_line_string = projection.project_geometry(linear_ring)
        #from cartopy.tests import show
        #show(projection, multi_line_string)
        # XXX not a test...

    def test_small(self):
        # What happens when a small (i.e. < threshold) feature crosses the
        # boundary?
        projection = ccrs.Mercator()
        linear_ring = geometry.polygon.LinearRing([
            (-179.9173693847652942, -16.5017831356493616),
            (-180.0000000000000000, -16.0671326636424396),
            (-179.7933201090486079, -16.0208822567412312),
        ])
        multi_line_string = projection.project_geometry(linear_ring)
        # there should be one, and only one, returned line:
        assert isinstance(multi_line_string, geometry.polygon.LinearRing)

        #from cartopy.tests import show
        #show(projection, multi_line_string)

    def test_three_points(self):
        # The following LinearRing when projected from PlateCarree() to
        # PlateCarree(180.0) results in three points all in close proximity.
        # If an attempt is made to form a LinearRing from the three points
        # by combining the first and last an exception will be raised.
        # Check that this object can be projected without error.
        coords = [(0.0, -45.0),
                  (0.0, -44.99974961593933),
                  (0.000727869825138, -45.0),
                  (0.0, -45.000105851567454),
                  (0.0, -45.0)]
        linear_ring = geometry.polygon.LinearRing(coords)
        src_proj = ccrs.PlateCarree()
        target_proj = ccrs.PlateCarree(180.0)
        try:
            result = target_proj.project_geometry(linear_ring, src_proj)
        except ValueError:
            self.fail("Failed to project LinearRing.")

    def test_stitch(self):
        # The following LinearRing wanders in/out of the map domain
        # but importantly the "vertical" lines at 0'E and 360'E are both
        # chopped by the map boundary. This results in their ends being
        # *very* close to each other and confusion over which occurs
        # first when navigating around the boundary.
        # Check that these ends are stitched together to avoid the
        # boundary ordering ambiguity.
        # NB. This kind of polygon often occurs with MPL's contouring.
        coords = [(0.0, -70.70499926182919),
                  (0.0, -71.25),
                  (0.0, -72.5),
                  (0.0, -73.49076371657017),
                  (360.0, -73.49076371657017),
                  (360.0, -72.5),
                  (360.0, -71.25),
                  (360.0, -70.70499926182919),
                  (350, -73),
                  (10, -73)]
        src_proj = ccrs.PlateCarree()
        target_proj = ccrs.Stereographic(80)
        linear_ring = geometry.polygon.LinearRing(coords)
        result = target_proj.project_geometry(linear_ring, src_proj)
        self.assertEqual(len(result), 1)

        # Check the stitch works in either direction.
        linear_ring = geometry.polygon.LinearRing(coords[::-1])
        result = target_proj.project_geometry(linear_ring, src_proj)
        self.assertEqual(len(result), 1)

    def test_at_boundary(self):
        # Check that a polygon is split and recombined correctly
        # as a result of being on the boundary, determined by tolerance.

        exterior = np.array(
            [[177.5, -79.912],
             [178.333, -79.946],
             [181.666, -83.494],
             [180.833, -83.570],
             [180., -83.620],
             [178.438, -83.333],
             [178.333, -83.312],
             [177.956, -83.888],
             [180.,  -84.086],
             [180.833, -84.318],
             [183., -86.],
             [183., -78.],
             [177.5, -79.912]])
        tring = geometry.polygon.LinearRing(exterior)

        tcrs = ccrs.PlateCarree()
        scrs = ccrs.PlateCarree()

        r = tcrs._project_linear_ring(tring, scrs)

        # Number of linearstrings
        self.assertEqual(len(r), 4)

        # Test area of smallest Polygon that contains all the points in the
        # geometry.
        self.assertAlmostEqual(r.convex_hull.area, 2347.75619258)


if __name__ == '__main__':
    unittest.main()

########NEW FILE########
__FILENAME__ = test_line_string
# (C) British Crown Copyright 2011 - 2012, Met Office
#
# This file is part of cartopy.
#
# cartopy is free software: you can redistribute it and/or modify it under
# the terms of the GNU Lesser General Public License as published by the
# Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# cartopy is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Lesser General Public License for more details.
#
# You should have received a copy of the GNU Lesser General Public License
# along with cartopy.  If not, see <http://www.gnu.org/licenses/>.


import itertools
import time
import unittest

import numpy as np
from shapely import geometry

import cartopy.crs as ccrs


class TestLineString(unittest.TestCase):
    def test_out_of_bounds(self):
        # Check that a line that is completely out of the map boundary produces
        # a valid LineString
        projection = ccrs.TransverseMercator(central_longitude=0)

        # For both start & end, define a point that results in well-defined
        # projection coordinates and one that results in NaN.
        start_points = [(86, 0), (130, 0)]
        end_points = [(88, 0), (120, 0)]

        # Try all four combinations of valid/NaN vs valid/NaN.
        for start, end in itertools.product(start_points, end_points):
            line_string = geometry.LineString([start, end])
            multi_line_string = projection.project_geometry(line_string)
            if start[0] == 130 and end[0] == 120:
                expected = 0
            else:
                expected = 1
            self.assertEqual(len(multi_line_string), expected,
                             'Unexpected line when working from {} '
                             'to {}'.format(start, end))

    def test_simple_fragment_count(self):
        projection = ccrs.PlateCarree()

        tests = [
            ([(150, 0), (-150, 0)], 2),
            ([(10, 0), (90, 0), (180, 0), (-90, 0), (-10, 0)], 2),
            ([(-10, 0), (10, 0)], 1),
            ([(-45, 0), (45, 30)], 1),
        ]

        for coords, pieces in tests:
            line_string = geometry.LineString(coords)
            multi_line_string = projection.project_geometry(line_string)
            #from cartopy.tests import show
            #show(projection, multi_line_string)
            self.assertEqual(len(multi_line_string), pieces)

    def test_split(self):
        projection = ccrs.Robinson(170.5)
        line_string = geometry.LineString([(-10, 30), (10, 60)])
        multi_line_string = projection.project_geometry(line_string)
        from cartopy.tests import show
        #show(projection, multi_line_string)
        self.assertEqual(len(multi_line_string), 2)

    def test_out_of_domain_efficiency(self):
        # Check we're efficiently dealing with lines that project
        # outside the map domain.
        # Because the south pole projects to an *enormous* circle
        # (radius ~ 1e23) this will take a *long* time to project if the
        # within-domain exactness criteria are used.
        line_string = geometry.LineString([(0, -90), (2, -90)])
        tgt_proj = ccrs.NorthPolarStereo()
        src_proj = ccrs.PlateCarree()
        cutoff_time = time.time() + 1
        tgt_proj.project_geometry(line_string, src_proj)
        self.assertLess(time.time(), cutoff_time, 'Projection took too long')


class FakeProjection(ccrs.PlateCarree):
    def __init__(self, left_offset=0, right_offset=0):
        self.left_offset = left_offset
        self.right_offset = right_offset

        self._half_width = 180
        self._half_height = 90
        ccrs.PlateCarree.__init__(self)

    @property
    def boundary(self):
        # XXX Should this be a LinearRing?
        w, h = self._half_width, self._half_height
        from shapely import geometry
        return geometry.LineString([(-w + self.left_offset, -h),
                                    (-w + self.left_offset, h),
                                    (w - self.right_offset, h),
                                    (w - self.right_offset, -h),
                                    (-w + self.left_offset, -h)])


class TestBisect(unittest.TestCase):
    # A bunch of tests to check the bisection algorithm is robust for a
    # variety of simple and/or pathological cases.

    def test_repeated_point(self):
        projection = FakeProjection()
        line_string = geometry.LineString([(10, 0), (10, 0)])
        multi_line_string = projection.project_geometry(line_string)
        self.assertEqual(len(multi_line_string), 1)
        self.assertEqual(len(multi_line_string[0].coords), 2)

    def test_interior_repeated_point(self):
        projection = FakeProjection()
        line_string = geometry.LineString([(0, 0), (10, 0), (10, 0), (20, 0)])
        multi_line_string = projection.project_geometry(line_string)
        self.assertEqual(len(multi_line_string), 1)
        self.assertEqual(len(multi_line_string[0].coords), 4)

    def test_circular_repeated_point(self):
        projection = FakeProjection()
        line_string = geometry.LineString([(0, 0), (360, 0)])
        multi_line_string = projection.project_geometry(line_string)
        self.assertEqual(len(multi_line_string), 1)
        self.assertEqual(len(multi_line_string[0].coords), 2)

    def test_short(self):
        projection = FakeProjection()
        line_string = geometry.LineString([(0, 0), (1e-12, 0)])
        multi_line_string = projection.project_geometry(line_string)
        self.assertEqual(len(multi_line_string), 1)
        self.assertEqual(len(multi_line_string[0].coords), 2)

    def test_empty(self):
        projection = FakeProjection(right_offset=10)
        line_string = geometry.LineString([(175, 0), (175, 10)])
        multi_line_string = projection.project_geometry(line_string)
        self.assertEqual(len(multi_line_string), 0)

    def test_simple_run_in(self):
        projection = FakeProjection(right_offset=10)
        line_string = geometry.LineString([(160, 0), (175, 0)])
        multi_line_string = projection.project_geometry(line_string)
        self.assertEqual(len(multi_line_string), 1)
        self.assertEqual(len(multi_line_string[0].coords), 2)

    def test_simple_wrap(self):
        projection = FakeProjection()
        line_string = geometry.LineString([(160, 0), (-160, 0)])
        multi_line_string = projection.project_geometry(line_string)
        self.assertEqual(len(multi_line_string), 2)
        self.assertEqual(len(multi_line_string[0].coords), 2)
        self.assertEqual(len(multi_line_string[1].coords), 2)

    def test_simple_run_out(self):
        projection = FakeProjection(left_offset=10)
        line_string = geometry.LineString([(-175, 0), (-160, 0)])
        multi_line_string = projection.project_geometry(line_string)
        self.assertEqual(len(multi_line_string), 1)
        self.assertEqual(len(multi_line_string[0].coords), 2)

    def test_point_on_boundary(self):
        projection = FakeProjection()
        line_string = geometry.LineString([(180, 0), (-160, 0)])
        multi_line_string = projection.project_geometry(line_string)
        self.assertEqual(len(multi_line_string), 1)
        self.assertEqual(len(multi_line_string[0].coords), 2)

        # Add a small offset to the left-hand boundary to make things
        # even more pathological.
        projection = FakeProjection(left_offset=5)
        line_string = geometry.LineString([(180, 0), (-160, 0)])
        multi_line_string = projection.project_geometry(line_string)
        self.assertEqual(len(multi_line_string), 1)
        self.assertEqual(len(multi_line_string[0].coords), 2)

    def test_nan_start(self):
        projection = ccrs.TransverseMercator(central_longitude=-90)
        line_string = geometry.LineString([(10, 50), (-10, 30)])
        multi_line_string = projection.project_geometry(line_string)
        self.assertEqual(len(multi_line_string), 1)
        for line_string in multi_line_string:
            for coord in line_string.coords:
                self.assertFalse(any(np.isnan(coord)),
                                 'Unexpected NaN in projected coords.')

    def test_nan_end(self):
        projection = ccrs.TransverseMercator(central_longitude=-90)
        line_string = geometry.LineString([(-10, 30), (10, 50)])
        multi_line_string = projection.project_geometry(line_string)
        from cartopy.tests import show
        #show(projection, multi_line_string)
        self.assertEqual(len(multi_line_string), 1)
        for line_string in multi_line_string:
            for coord in line_string.coords:
                self.assertFalse(any(np.isnan(coord)),
                                 'Unexpected NaN in projected coords.')


class TestMisc(unittest.TestCase):
    def test_misc(self):
        projection = ccrs.TransverseMercator(central_longitude=-90)
        line_string = geometry.LineString([(10, 50), (-10, 30)])
        multi_line_string = projection.project_geometry(line_string)
        from cartopy.tests import show
        #show(projection, multi_line_string)
        for line_string in multi_line_string:
            for coord in line_string.coords:
                self.assertFalse(any(np.isnan(coord)),
                                 'Unexpected NaN in projected coords.')

    def test_something(self):
        projection = ccrs.RotatedPole(pole_longitude=177.5,
                                      pole_latitude=37.5)
        line_string = geometry.LineString([(0, 0), (1e-14, 0)])
        multi_line_string = projection.project_geometry(line_string)
        self.assertEqual(len(multi_line_string), 1)
        self.assertEqual(len(multi_line_string[0].coords), 2)

    def test_global_boundary(self):
        linear_ring = geometry.LineString([(-180, -180), (-180, 180),
                                           (180, 180), (180, -180)])
        pc = ccrs.PlateCarree()
        merc = ccrs.Mercator()
        multi_line_string = pc.project_geometry(linear_ring, merc)
        assert len(multi_line_string) > 0

        # check the identity transform
        multi_line_string = merc.project_geometry(linear_ring, merc)
        assert len(multi_line_string) > 0


class TestSymmetry(unittest.TestCase):
    @unittest.expectedFailure
    def test_curve(self):
        # Obtain a simple, curved path.
        projection = ccrs.PlateCarree()
        coords = [(-0.08, 51.53), (132.00, 43.17)]  # London to Vladivostock
        line_string = geometry.LineString(coords)
        multi_line_string = projection.project_geometry(line_string)

        # Compute the reverse path.
        line_string = geometry.LineString(coords[::-1])
        multi_line_string2 = projection.project_geometry(line_string)

        # Make sure that they generated the same points.
        # (Although obviously they will be in the opposite order!)
        self.assertEqual(len(multi_line_string), 1)
        self.assertEqual(len(multi_line_string2), 1)
        coords = multi_line_string[0].coords
        coords2 = multi_line_string2[0].coords
        np.testing.assert_allclose(coords, coords2[::-1],
                                   err_msg='Asymmetric curve generation')


if __name__ == '__main__':
    unittest.main()

########NEW FILE########
__FILENAME__ = test_pep8
import os
import unittest

import pep8

import cartopy


class TestCodeFormat(unittest.TestCase):
    def test_pep8_conformance(self):
#
#        Tests the cartopy codebase against the "pep8" tool.
#
#        Users can add their own excluded files (should files exist in the
#        local directory which is not in the repository) by adding a
#        ".pep8_test_exclude.txt" file in the same directory as this test.
#        The file should be a line separated list of filenames/directories
#        as can be passed to the "pep8" tool's exclude list.
#
        pep8style = pep8.StyleGuide(quiet=False)
        pep8style.options.exclude.extend([])

        # allow users to add their own exclude list
        extra_exclude_file = os.path.join(os.path.dirname(__file__),
                                          '.pep8_test_exclude.txt')
        if os.path.exists(extra_exclude_file):
            with open(extra_exclude_file, 'r') as fh:
                extra_exclude = [line.strip() for line in fh if line.strip()]
            pep8style.options.exclude.extend(extra_exclude)

        result = pep8style.check_files([os.path.dirname(cartopy.__file__)])
        self.assertEqual(result.total_errors, 0, "Found code syntax "
                                                 "errors (and warnings).")


if __name__ == '__main__':
    unittest.main()

########NEW FILE########
__FILENAME__ = test_polygon
# (C) British Crown Copyright 2011 - 2012, Met Office
#
# This file is part of cartopy.
#
# cartopy is free software: you can redistribute it and/or modify it under
# the terms of the GNU Lesser General Public License as published by the
# Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# cartopy is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Lesser General Public License for more details.
#
# You should have received a copy of the GNU Lesser General Public License
# along with cartopy.  If not, see <http://www.gnu.org/licenses/>.


import unittest

import numpy as np
import shapely.geometry as sgeom
import shapely.wkt


import cartopy.crs as ccrs


class TestBoundary(unittest.TestCase):
    def test_no_polygon_boundary_reversal(self):
        # Check that polygons preserve their clockwise or counter-clockwise
        # ordering when they are attached to the boundary.
        # Failure to do so will result in invalid polygons (their boundaries
        # cross-over).
        polygon = sgeom.Polygon([(-10, 30), (10, 60), (10, 50)])
        projection = ccrs.Robinson(170.5)
        multi_polygon = projection.project_geometry(polygon)
        for polygon in multi_polygon:
            self.assertTrue(polygon.is_valid)

    def test_polygon_boundary_attachment(self):
        # Check the polygon is attached to the boundary even when no
        # intermediate point for one of the crossing segments would normally
        # exist.
        polygon = sgeom.Polygon([(-10, 30), (10, 60), (10, 50)])
        projection = ccrs.Robinson(170.6)
        # This will raise an exception if the polygon/boundary intersection
        # fails.
        multi_polygon = projection.project_geometry(polygon)

    def test_out_of_bounds(self):
        # Check that a polygon that is completely out of the map boundary
        # doesn't produce an empty result.
        projection = ccrs.TransverseMercator(central_longitude=0)

        polys = [
            # All valid
            ([(86, -1), (86, 1), (88, 1), (88, -1)], 1),
            # One out of backwards projection range
            ([(86, -1), (86, 1), (130, 1), (88, -1)], 1),
            # An out of backwards projection range segment
            ([(86, -1), (86, 1), (130, 1), (130, -1)], 1),
            # All out of backwards projection range
            ([(120, -1), (120, 1), (130, 1), (130, -1)], 0),
        ]

        # Try all four combinations of valid/NaN vs valid/NaN.
        for coords, expected_polys in polys:
            polygon = sgeom.Polygon(coords)
            multi_polygon = projection.project_geometry(polygon)
            self.assertEqual(len(multi_polygon), expected_polys)


class TestMisc(unittest.TestCase):
    def test_misc(self):
        projection = ccrs.TransverseMercator(central_longitude=-90)
        polygon = sgeom.Polygon([(-10, 30), (10, 60), (10, 50)])
        multi_polygon = projection.project_geometry(polygon)

    def test_small(self):
        projection = ccrs.Mercator()
        polygon = sgeom.Polygon([
            (-179.7933201090486079, -16.0208822567412312),
            (-180.0000000000000000, -16.0671326636424396),
            (-179.9173693847652942, -16.5017831356493616),
        ])
        multi_polygon = projection.project_geometry(polygon)
        self.assertEqual(len(multi_polygon), 1)
        self.assertEqual(len(multi_polygon[0].exterior.coords), 4)

    def test_former_infloop_case(self):
        # test a polygon which used to get stuck in an infinite loop
        # see https://github.com/SciTools/cartopy/issues/60
        coords = [(260.625, 68.90383337092122), (360.0, 79.8556091996901),
                  (360.0, 77.76848175458498), (0.0, 88.79068047337279),
                  (210.0, 90.0), (135.0, 88.79068047337279),
                  (260.625, 68.90383337092122)]
        geom = sgeom.Polygon(coords)

        target_projection = ccrs.PlateCarree()
        source_crs = ccrs.Geodetic()

        multi_polygon = target_projection.project_geometry(geom, source_crs)
        # check the result is non-empty
        self.assertFalse(multi_polygon.is_empty)

    def test_catch_infinite_loop(self):
        # Known bug resulting in an infinite loop occurring, ensure exception
        # is raised.  If this multilinestring does not result in an inf. loop
        # (raised exception), then you've fixed a bug and this test can be
        # updated.
        mstring1 = shapely.wkt.loads(
            'MULTILINESTRING ('
            '(-179.9999990464349651 -80.2000000000000171, '
            '-179.5000000001111005 -80.2000000000000171, '
            '-179.5000000001111005 -79.9000000000000199, '
            '-179.9999995232739138 -79.9499999523163041, '
            '-179.8000000001110550 -80.0000000000000000, '
            '-179.8000000001110550 -80.0999999999999943, '
            '-179.9999999047436177 -80.0999999999999943), '
            '(179.9999995231628702 -79.9499999523163041, '
            '179.5000000000000000 -79.9000000000000199, '
            '179.5000000000000000 -80.0000000000000000, '
            '179.9999995231628702 -80.0499999523162842, '
            '179.5000000000000000 -80.0999999999999943, '
            '179.5000000000000000 -80.2000000000000171, '
            '179.9999990463256836 -80.2000000000000171))')
        mstring2 = shapely.wkt.loads(
            'MULTILINESTRING ('
            '(179.9999996185302678 -79.9999999904632659, '
            '179.5999999999999943 -79.9899999999999949, '
            '179.5999999999999943 -79.9399999999999977, '
            '179.9999996185302678 -79.9599999809265114), '
            '(-179.9999999047436177 -79.9600000000000080, '
            '-179.9000000001110777 -79.9600000000000080, '
            '-179.9000000001110777 -80.0000000000000000, '
            '-179.9999999047436177 -80.0000000000000000))')
        multi_line_strings = [mstring1, mstring2]

        src = ccrs.PlateCarree()
        with self.assertRaises(RuntimeError):
            src._attach_lines_to_boundary(multi_line_strings, True)

    def test_3pt_poly(self):
        projection = ccrs.OSGB()
        polygon = sgeom.Polygon([(-1000, -1000),
                                 (-1000, 200000),
                                 (200000, -1000)])
        multi_polygon = projection.project_geometry(polygon, ccrs.OSGB())
        self.assertEqual(len(multi_polygon), 1)
        self.assertEqual(len(multi_polygon[0].exterior.coords), 4)


class TestQuality(unittest.TestCase):
    def setUp(self):
        projection = ccrs.RotatedPole(pole_longitude=177.5,
                                      pole_latitude=37.5)
        polygon = sgeom.Polygon([
            (177.5, -57.38460319),
            (180.0, -57.445077),
            (175.0, -57.19913331),
        ])
        self.multi_polygon = projection.project_geometry(polygon)
        #from cartopy.tests import show
        #show(projection, self.multi_polygon)

    def test_split(self):
        # Start simple ... there should be two projected polygons.
        self.assertEqual(len(self.multi_polygon), 2)

    def test_repeats(self):
        # Make sure we don't have repeated points at the boundary, because
        # they mess up the linear extrapolation to the boundary.

        # Make sure there aren't any repeated points.
        xy = np.array(self.multi_polygon[0].exterior.coords)
        same = (xy[1:] == xy[:-1]).all(axis=1)
        self.assertFalse(any(same), 'Repeated points in projected geometry.')

    def test_symmetry(self):
        # Make sure the number of points added on the way towards the
        # boundary is similar to the number of points added on the way away
        # from the boundary.

        # Identify all the contiguous sets of non-boundary points.
        xy = np.array(self.multi_polygon[0].exterior.coords)
        boundary = np.logical_or(xy[:, 1] == 90, xy[:, 1] == -90)
        regions = (boundary[1:] != boundary[:-1]).cumsum()
        regions = np.insert(regions, 0, 0)

        # For each region, check if the number of increasing steps is roughly
        # equal to the number of decreasing steps.
        for i in range(boundary[0], regions.max(), 2):
            indices = np.where(regions == i)
            x = xy[indices, 0]
            delta = np.diff(x)
            num_incr = np.count_nonzero(delta > 0)
            num_decr = np.count_nonzero(delta < 0)
            self.assertLess(abs(num_incr - num_decr), 3,
                            'Too much asymmetry.')


class PolygonTests(unittest.TestCase):
    def _assert_bounds(self, bounds, x1, y1, x2, y2, delta=1):
        self.assertAlmostEqual(bounds[0], x1, delta=delta)
        self.assertAlmostEqual(bounds[1], y1, delta=delta)
        self.assertAlmostEqual(bounds[2], x2, delta=delta)
        self.assertAlmostEqual(bounds[3], y2, delta=delta)


class TestWrap(PolygonTests):
    # Test that Plate Carree projection "does the right thing"(tm) with
    # source data tha extends outside the [-180, 180] range.
    def test_plate_carree_no_wrap(self):
        proj = ccrs.PlateCarree()
        poly = sgeom.box(0, 0, 10, 10)
        multi_polygon = proj.project_geometry(poly, proj)
        # Check the structure
        self.assertEqual(len(multi_polygon), 1)
        # Check the rough shape
        polygon = multi_polygon[0]
        self._assert_bounds(polygon.bounds, 0, 0, 10, 10)

    def test_plate_carree_partial_wrap(self):
        proj = ccrs.PlateCarree()
        poly = sgeom.box(170, 0, 190, 10)
        multi_polygon = proj.project_geometry(poly, proj)
        # Check the structure
        self.assertEqual(len(multi_polygon), 2)
        # Check the rough shape
        polygon = multi_polygon[0]
        self._assert_bounds(polygon.bounds, 170, 0, 180, 10)
        polygon = multi_polygon[1]
        self._assert_bounds(polygon.bounds, -180, 0, -170, 10)

    def test_plate_carree_wrap(self):
        proj = ccrs.PlateCarree()
        poly = sgeom.box(200, 0, 220, 10)
        multi_polygon = proj.project_geometry(poly, proj)
        # Check the structure
        self.assertEqual(len(multi_polygon), 1)
        # Check the rough shape
        polygon = multi_polygon[0]
        self._assert_bounds(polygon.bounds, -160, 0, -140, 10)


def ring(minx, miny, maxx, maxy, ccw):
    box = sgeom.box(minx, miny, maxx, maxy, ccw)
    return np.array(box.exterior.coords)


class TestHoles(PolygonTests):
    def test_simple(self):
        proj = ccrs.PlateCarree()
        poly = sgeom.Polygon(ring(-40, -40, 40, 40, True),
                             [ring(-20, -20, 20, 20, False)])
        multi_polygon = proj.project_geometry(poly)
        # Check the structure
        self.assertEqual(len(multi_polygon), 1)
        self.assertEqual(len(multi_polygon[0].interiors), 1)
        # Check the rough shape
        polygon = multi_polygon[0]
        self._assert_bounds(polygon.bounds, -40, -47, 40, 47)
        self._assert_bounds(polygon.interiors[0].bounds, -20, -21, 20, 21)

    def test_wrapped_poly_simple_hole(self):
        proj = ccrs.PlateCarree(-150)
        poly = sgeom.Polygon(ring(-40, -40, 40, 40, True),
                             [ring(-20, -20, 20, 20, False)])
        multi_polygon = proj.project_geometry(poly)
        # Check the structure
        self.assertEqual(len(multi_polygon), 2)
        self.assertEqual(len(multi_polygon[0].interiors), 1)
        self.assertEqual(len(multi_polygon[1].interiors), 0)
        # Check the rough shape
        polygon = multi_polygon[0]
        self._assert_bounds(polygon.bounds, 110, -47, 180, 47)
        self._assert_bounds(polygon.interiors[0].bounds, 130, -21, 170, 21)
        polygon = multi_polygon[1]
        self._assert_bounds(polygon.bounds, -180, -43, -170, 43)

    def test_wrapped_poly_wrapped_hole(self):
        proj = ccrs.PlateCarree(-180)
        poly = sgeom.Polygon(ring(-40, -40, 40, 40, True),
                             [ring(-20, -20, 20, 20, False)])
        multi_polygon = proj.project_geometry(poly)
        # Check the structure
        self.assertEqual(len(multi_polygon), 2)
        self.assertEqual(len(multi_polygon[0].interiors), 0)
        self.assertEqual(len(multi_polygon[1].interiors), 0)
        # Check the rough shape
        polygon = multi_polygon[0]
        self._assert_bounds(polygon.bounds, 140, -47, 180, 47)
        polygon = multi_polygon[1]
        self._assert_bounds(polygon.bounds, -180, -47, -140, 47)

    def test_inverted_poly_simple_hole(self):
        proj = ccrs.NorthPolarStereo()
        poly = sgeom.Polygon([(0, 0), (-90, 0), (-180, 0), (-270, 0)],
                             [[(0, -30), (90, -30), (180, -30), (270, -30)]])
        multi_polygon = proj.project_geometry(poly)
        # Check the structure
        self.assertEqual(len(multi_polygon), 1)
        self.assertEqual(len(multi_polygon[0].interiors), 1)
        # Check the rough shape
        polygon = multi_polygon[0]
        self._assert_bounds(polygon.bounds, -2.4e7, -2.4e7, 2.4e7, 2.4e7, 1e6)
        self._assert_bounds(polygon.interiors[0].bounds,
                            - 1.2e7, -1.2e7, 1.2e7, 1.2e7, 1e6)

    def test_inverted_poly_clipped_hole(self):
        proj = ccrs.NorthPolarStereo()
        poly = sgeom.Polygon([(0, 0), (-90, 0), (-180, 0), (-270, 0)],
                             [[(-135, -60), (-45, -60),
                               (45, -60), (135, -60)]])
        multi_polygon = proj.project_geometry(poly)
        # Check the structure
        self.assertEqual(len(multi_polygon), 1)
        self.assertEqual(len(multi_polygon[0].interiors), 1)
        # Check the rough shape
        polygon = multi_polygon[0]
        self._assert_bounds(polygon.bounds, -5.0e7, -5.0e7, 5.0e7, 5.0e7, 1e6)
        self._assert_bounds(polygon.interiors[0].bounds,
                            - 1.2e7, -1.2e7, 1.2e7, 1.2e7, 1e6)
        self.assertAlmostEqual(polygon.area, 7.30e15, delta=1e13)

    def test_inverted_poly_removed_hole(self):
        proj = ccrs.NorthPolarStereo(globe=ccrs.Globe(ellipse='WGS84'))
        poly = sgeom.Polygon([(0, 0), (-90, 0), (-180, 0), (-270, 0)],
                             [[(-135, -75), (-45, -75),
                               (45, -75), (135, -75)]])
        multi_polygon = proj.project_geometry(poly)
        # Check the structure
        self.assertEqual(len(multi_polygon), 1)
        self.assertEqual(len(multi_polygon[0].interiors), 1)
        # Check the rough shape
        polygon = multi_polygon[0]
        self._assert_bounds(polygon.bounds, -5.0e7, -5.0e7, 5.0e7, 5.0e7, 1e6)
        self._assert_bounds(polygon.interiors[0].bounds,
                            - 1.2e7, -1.2e7, 1.2e7, 1.2e7, 1e6)
        self.assertAlmostEqual(polygon.area, 7.34e15, delta=1e13)

    def test_multiple_interiors(self):
        exterior = ring(0, 0, 12, 12, True)
        interiors = [ring(1, 1, 2, 2, False), ring(1, 8, 2, 9, False)]

        poly = sgeom.Polygon(exterior, interiors)

        target = ccrs.PlateCarree()
        source = ccrs.Geodetic()

        assert len(list(target.project_geometry(poly, source))) == 1


if __name__ == '__main__':
    unittest.main()

########NEW FILE########
__FILENAME__ = test_shapereader
# (C) British Crown Copyright 2011 - 2012, Met Office
#
# This file is part of cartopy.
#
# cartopy is free software: you can redistribute it and/or modify it under
# the terms of the GNU Lesser General Public License as published by the
# Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# cartopy is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Lesser General Public License for more details.
#
# You should have received a copy of the GNU Lesser General Public License
# along with cartopy.  If not, see <http://www.gnu.org/licenses/>.

import os.path
import unittest

import numpy as np
from numpy.testing import assert_array_almost_equal
from shapely.geometry import MultiPolygon, Polygon

import cartopy.io.shapereader as shp


LAKES_PATH = shp.natural_earth(resolution='110m',
                               category='physical',
                               name='lakes')
RIVERS_PATH = shp.natural_earth(resolution='110m',
                                category='physical',
                                name='rivers_lake_centerlines')


class TestLakes(unittest.TestCase):
    def setUp(self):
        self.reader = shp.Reader(LAKES_PATH)

    def _assert_geometry(self, geometry):
        self.assertEqual(geometry.type, 'MultiPolygon')
        self.assertEqual(len(geometry), 1)

        polygon = geometry[0]

        expected = np.array([(-84.85548682324658, 11.147898667846633),
                             (-85.29013729525353, 11.176165676310276),
                             (-85.79132117383625, 11.509737046754324),
                             (-85.8851655748783, 11.900100816287136),
                             (-85.5653401354239, 11.940330918826362),
                             (-85.03684526237491, 11.5216484643976),
                             (-84.85548682324658, 11.147898667846633),
                             (-84.85548682324658, 11.147898667846633)])

        assert_array_almost_equal(expected, polygon.exterior.coords)

        self.assertEqual(len(polygon.interiors), 0)

    def test_geometry(self):
        geometries = list(self.reader.geometries())
        self.assertEqual(len(geometries), len(self.reader))

        # Choose a nice small lake
        lake = geometries[14]
        self._assert_geometry(lake)

    def test_record(self):
        records = list(self.reader.records())
        self.assertEqual(len(records), len(self.reader))

        # Choose a nice small lake
        lake_record = records[14]
        self.assertEqual(lake_record.attributes.get('name'),
                         'Lago de\rNicaragua')
        self.assertEqual(lake_record.attributes.keys(),
                         ['admin', 'featurecla', 'scalerank',
                          'name_alt', 'name'])
        lake = lake_record.geometry
        self._assert_geometry(lake)

    def test_bounds(self):
        # tests that a file which has a record with a bbox can
        # use the bbox without first creating the geometry
        record = self.reader.records().next()
        self.assertEqual(record._geometry, False, ('The geometry was loaded '
                                                   'before it was needed.'))
        self.assertEqual(len(record._bounds), 4)
        self.assertEqual(record._bounds, record.bounds)
        self.assertEqual(record._geometry, False, ('The geometry was loaded '
                                                   'in order to create the '
                                                   'bounds.'))


class TestRivers(unittest.TestCase):
    def setUp(self):
        self.reader = shp.Reader(RIVERS_PATH)

    def _assert_geometry(self, geometry):
        self.assertEqual(geometry.type, 'MultiLineString')
        self.assertEqual(len(geometry), 1)

        linestring = geometry[0]
        coords = linestring.coords
        self.assertAlmostEqual(coords[0][0], -113.823382738076)
        self.assertAlmostEqual(coords[0][1], 58.7102151556671)
        self.assertAlmostEqual(coords[1][0], -113.71351864302348)
        self.assertAlmostEqual(coords[1][1], 58.669261583075794)

    def test_geometry(self):
        geometries = list(self.reader.geometries())
        self.assertEqual(len(geometries), len(self.reader))

        # Choose a nice small river
        river = geometries[6]
        self._assert_geometry(river)

    def test_record(self):
        records = list(self.reader.records())
        self.assertEqual(len(records), len(self.reader))

        # Choose a nice small lake
        river_record = records[6]
        self.assertEqual(
            river_record.attributes,
            {'featurecla': 'River', 'scalerank': 2, 'name': 'Peace',
             'name_alt': ' ' * 254})
        river = river_record.geometry
        self._assert_geometry(river)


if __name__ == '__main__':
    unittest.main()

########NEW FILE########
__FILENAME__ = test_util
# (C) British Crown Copyright 2014, Met Office
#
# This file is part of cartopy.
#
# cartopy is free software: you can redistribute it and/or modify it under
# the terms of the GNU Lesser General Public License as published by the
# Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# cartopy is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Lesser General Public License for more details.
#
# You should have received a copy of the GNU Lesser General Public License
# along with cartopy.  If not, see <http://www.gnu.org/licenses/>.
from nose.tools import raises
import numpy as np
import numpy.ma as ma
from numpy.testing import assert_array_equal

from cartopy.util import add_cyclic_point


class Test_add_cyclic_point(object):

    @classmethod
    def setup_class(cls):
        cls.lons = np.arange(0, 360, 60)
        cls.data2d = np.ones([3, 6]) * np.arange(6)
        cls.data4d = np.ones([4, 6, 2, 3]) * \
            np.arange(6)[..., np.newaxis, np.newaxis]

    def test_data_only(self):
        c_data = add_cyclic_point(self.data2d)
        r_data = np.concatenate((self.data2d, self.data2d[:, :1]), axis=1)
        assert_array_equal(c_data, r_data)

    def test_data_and_coord(self):
        c_data, c_lons = add_cyclic_point(self.data2d, coord=self.lons)
        r_data = np.concatenate((self.data2d, self.data2d[:, :1]), axis=1)
        r_lons = np.concatenate((self.lons, np.array([360.])))
        assert_array_equal(c_data, r_data)
        assert_array_equal(c_lons, r_lons)

    def test_data_only_with_axis(self):
        c_data = add_cyclic_point(self.data4d, axis=1)
        r_data = np.concatenate((self.data4d, self.data4d[:, :1]), axis=1)
        assert_array_equal(c_data, r_data)

    def test_data_and_coord_with_axis(self):
        c_data, c_lons = add_cyclic_point(self.data4d, coord=self.lons, axis=1)
        r_data = np.concatenate((self.data4d, self.data4d[:, :1]), axis=1)
        r_lons = np.concatenate((self.lons, np.array([360.])))
        assert_array_equal(c_data, r_data)
        assert_array_equal(c_lons, r_lons)

    def test_masked_data(self):
        new_data = ma.masked_less(self.data2d, 3)
        c_data = add_cyclic_point(new_data)
        r_data = ma.concatenate((self.data2d, self.data2d[:, :1]), axis=1)
        assert_array_equal(c_data, r_data)

    @raises(ValueError)
    def test_invalid_coord_dimensionality(self):
        lons2d = np.repeat(self.lons[np.newaxis], 3, axis=0)
        c_data, c_lons = add_cyclic_point(self.data2d, coord=lons2d)

    @raises(ValueError)
    def test_invalid_coord_size(self):
        c_data, c_lons = add_cyclic_point(self.data2d, coord=self.lons[:-1])

    @raises(ValueError)
    def test_invalid_axis(self):
        c_data = add_cyclic_point(self.data2d, axis=-3)

########NEW FILE########
__FILENAME__ = test_vector_transform
# (C) British Crown Copyright 2013, Met Office
#
# This file is part of cartopy.
#
# cartopy is free software: you can redistribute it and/or modify it under
# the terms of the GNU Lesser General Public License as published by the
# Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# cartopy is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Lesser General Public License for more details.
#
# You should have received a copy of the GNU Lesser General Public License
# along with cartopy.  If not, see <http://www.gnu.org/licenses/>.
import numpy as np
from numpy.testing import assert_array_equal, assert_array_almost_equal

import cartopy.vector_transform as vec_trans
import cartopy.crs as ccrs


def _sample_plate_carree_coordinates():
    x = np.array([-10, 0, 10, -9, 0, 9])
    y = np.array([10, 10, 10, 5, 5, 5])
    return x, y


def _sample_plate_carree_scalar_field():
    return np.array([2, 4, 2, 1.2, 3, 1.2])


def _sample_plate_carree_vector_field():
    u = np.array([2, 4, 2, 1.2, 3, 1.2])
    v = np.array([5.5, 4, 5.5, 1.2, .3, 1.2])
    return u, v


class Test_interpolate_to_grid(object):

    @classmethod
    def setup_class(cls):
        cls.x, cls.y = _sample_plate_carree_coordinates()
        cls.s = _sample_plate_carree_scalar_field()

    def test_data_extent(self):
        # Interpolation to a grid with extents of the input data.
        expected_x_grid = np.array([[-10., -5., 0., 5., 10.],
                                    [-10., -5., 0., 5., 10.],
                                    [-10., -5., 0., 5., 10.]])
        expected_y_grid = np.array([[5., 5., 5., 5., 5.],
                                    [7.5, 7.5, 7.5, 7.5, 7.5],
                                    [10., 10., 10., 10., 10]])
        expected_s_grid = np.array([[np.nan, 2., 3., 2., np.nan],
                                    [np.nan, 2.5, 3.5, 2.5, np.nan],
                                    [2., 3., 4., 3., 2.]])

        x_grid, y_grid, s_grid = vec_trans._interpolate_to_grid(
            5, 3, self.x, self.y, self.s)

        assert_array_equal(x_grid, expected_x_grid)
        assert_array_equal(y_grid, expected_y_grid)
        assert_array_almost_equal(s_grid, expected_s_grid)

    def test_explicit_extent(self):
        # Interpolation to a grid with explicit extents.
        expected_x_grid = np.array([[-5., 0., 5., 10.],
                                    [-5., 0., 5., 10.]])
        expected_y_grid = np.array([[7.5, 7.5, 7.5, 7.5],
                                    [10., 10., 10., 10]])
        expected_s_grid = np.array([[2.5, 3.5, 2.5, np.nan],
                                    [3., 4., 3., 2.]])

        extent = (-5, 10, 7.5, 10)
        x_grid, y_grid, s_grid = vec_trans._interpolate_to_grid(
            4, 2, self.x, self.y, self.s, target_extent=extent)

        assert_array_equal(x_grid, expected_x_grid)
        assert_array_equal(y_grid, expected_y_grid)
        assert_array_almost_equal(s_grid, expected_s_grid)

    def test_multiple_fields(self):
        # Interpolation of multiple fields in one go.
        expected_x_grid = np.array([[-10., -5., 0., 5., 10.],
                                    [-10., -5., 0., 5., 10.],
                                    [-10., -5., 0., 5., 10.]])
        expected_y_grid = np.array([[5., 5., 5., 5., 5.],
                                    [7.5, 7.5, 7.5, 7.5, 7.5],
                                    [10., 10., 10., 10., 10]])
        expected_s_grid = np.array([[np.nan, 2., 3., 2., np.nan],
                                    [np.nan, 2.5, 3.5, 2.5, np.nan],
                                    [2., 3., 4., 3., 2.]])

        x_grid, y_grid, s_grid1, s_grid2, s_grid3 = \
            vec_trans._interpolate_to_grid(5, 3, self.x, self.y,
                                           self.s, self.s, self.s)

        assert_array_equal(x_grid, expected_x_grid)
        assert_array_equal(y_grid, expected_y_grid)
        assert_array_almost_equal(s_grid1, expected_s_grid)
        assert_array_almost_equal(s_grid2, expected_s_grid)
        assert_array_almost_equal(s_grid3, expected_s_grid)


class Test_vector_scalar_to_grid(object):

    @classmethod
    def setup_class(cls):
        cls.x, cls.y = _sample_plate_carree_coordinates()
        cls.u, cls.v = _sample_plate_carree_vector_field()
        cls.s = _sample_plate_carree_scalar_field()

    def test_no_transform(self):
        # Transform and regrid vector (with no projection transform).
        expected_x_grid = np.array([[-10., -5., 0., 5., 10.],
                                    [-10., -5., 0., 5., 10.],
                                    [-10., -5., 0., 5., 10.]])
        expected_y_grid = np.array([[5., 5., 5., 5., 5.],
                                    [7.5, 7.5, 7.5, 7.5, 7.5],
                                    [10., 10., 10., 10., 10]])
        expected_u_grid = np.array([[np.nan, 2., 3., 2., np.nan],
                                    [np.nan, 2.5, 3.5, 2.5, np.nan],
                                    [2., 3., 4., 3., 2.]])
        expected_v_grid = np.array([[np.nan, .8, .3, .8, np.nan],
                                    [np.nan, 2.675, 2.15, 2.675, np.nan],
                                    [5.5, 4.75, 4., 4.75, 5.5]])

        src_crs = target_crs = ccrs.PlateCarree()
        x_grid, y_grid, u_grid, v_grid = vec_trans.vector_scalar_to_grid(
            src_crs, target_crs, (5, 3), self.x, self.y, self.u, self.v)

        assert_array_equal(x_grid, expected_x_grid)
        assert_array_equal(y_grid, expected_y_grid)
        assert_array_almost_equal(u_grid, expected_u_grid)
        assert_array_almost_equal(v_grid, expected_v_grid)

    def test_with_transform(self):
        # Transform and regrid vector.
        target_crs = ccrs.PlateCarree()
        src_crs = ccrs.NorthPolarStereo()

        input_coords = [src_crs.transform_point(xp, yp, target_crs)
                        for xp, yp in zip(self.x, self.y)]
        x_nps = np.array([ic[0] for ic in input_coords])
        y_nps = np.array([ic[1] for ic in input_coords])
        u_nps, v_nps = src_crs.transform_vectors(target_crs, self.x, self.y,
                                                 self.u, self.v)

        expected_x_grid = np.array([[-10., -5., 0., 5., 10.],
                                    [-10., -5., 0., 5., 10.],
                                    [-10., -5., 0., 5., 10.]])
        expected_y_grid = np.array([[5., 5., 5., 5., 5.],
                                    [7.5, 7.5, 7.5, 7.5, 7.5],
                                    [10., 10., 10., 10., 10]])
        expected_u_grid = np.array([[np.nan, 2., 3., 2., np.nan],
                                    [np.nan, 2.5, 3.5, 2.5, np.nan],
                                    [2., 3., 4., 3., 2.]])
        expected_v_grid = np.array([[np.nan, .8, .3, .8, np.nan],
                                    [np.nan, 2.675, 2.15, 2.675, np.nan],
                                    [5.5, 4.75, 4., 4.75, 5.5]])

        x_grid, y_grid, u_grid, v_grid = vec_trans.vector_scalar_to_grid(
            src_crs, target_crs, (5, 3), x_nps, y_nps, u_nps, v_nps)

        assert_array_almost_equal(x_grid, expected_x_grid)
        assert_array_almost_equal(y_grid, expected_y_grid)
        # Vector transforms are somewhat approximate, so we are more lenient
        # with the returned values since we have transformed twice.
        assert_array_almost_equal(u_grid, expected_u_grid, decimal=4)
        assert_array_almost_equal(v_grid, expected_v_grid, decimal=4)

    def test_with_scalar_field(self):
        # Transform and regrid vector (with no projection transform) with an
        # additional scalar field.
        expected_x_grid = np.array([[-10., -5., 0., 5., 10.],
                                    [-10., -5., 0., 5., 10.],
                                    [-10., -5., 0., 5., 10.]])
        expected_y_grid = np.array([[5., 5., 5., 5., 5.],
                                    [7.5, 7.5, 7.5, 7.5, 7.5],
                                    [10., 10., 10., 10., 10]])
        expected_u_grid = np.array([[np.nan, 2., 3., 2., np.nan],
                                    [np.nan, 2.5, 3.5, 2.5, np.nan],
                                    [2., 3., 4., 3., 2.]])
        expected_v_grid = np.array([[np.nan, .8, .3, .8, np.nan],
                                    [np.nan, 2.675, 2.15, 2.675, np.nan],
                                    [5.5, 4.75, 4., 4.75, 5.5]])
        expected_s_grid = np.array([[np.nan, 2., 3., 2., np.nan],
                                    [np.nan, 2.5, 3.5, 2.5, np.nan],
                                    [2., 3., 4., 3., 2.]])

        src_crs = target_crs = ccrs.PlateCarree()
        x_grid, y_grid, u_grid, v_grid, s_grid = \
            vec_trans.vector_scalar_to_grid(src_crs, target_crs, (5, 3),
                                            self.x, self.y,
                                            self.u, self.v, self.s)

        assert_array_equal(x_grid, expected_x_grid)
        assert_array_equal(y_grid, expected_y_grid)
        assert_array_almost_equal(u_grid, expected_u_grid)
        assert_array_almost_equal(v_grid, expected_v_grid)
        assert_array_almost_equal(s_grid, expected_s_grid)


if __name__ == '__main__':
    import nose
    nose.runmodule(argv=['-sv', '--with-doctest'], exit=False)

########NEW FILE########
__FILENAME__ = util
# (C) British Crown Copyright 2014, Met Office
#
# This file is part of cartopy.
#
# cartopy is free software: you can redistribute it and/or modify it under
# the terms of the GNU Lesser General Public License as published by the
# Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# cartopy is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Lesser General Public License for more details.
#
# You should have received a copy of the GNU Lesser General Public License
# along with cartopy.  If not, see <http://www.gnu.org/licenses/>.
"""
This module contains utilities that are useful in conjunction with
cartopy.

"""
import numpy as np
import numpy.ma as ma


def add_cyclic_point(data, coord=None, axis=-1):
    """
    Add a cyclic point to an array and optionally a corresponding
    coordinate.

    Args:

    * data:
        An n-dimensional array of data to add a cyclic point to.

    Kwargs:

    * coord:
        A 1-dimensional array which specifies the coordinate values for
        the dimension the cyclic point is to be added to. The coordinate
        values must be regularly spaced.

    * axis:
        Specifies the axis of the data array to add the cyclic point to.
        Defaults to the right-most axis.

    Returns:

    * cyclic_data:
        The data array with a cyclic point added.

    * cyclic_coord:
        The coordinate with a cyclic point, only returned if the coord
        keyword was supplied.

    Examples:

    Adding a cyclic point to a data array, where the cyclic dimension is
    the right-most dimension

    >>> import numpy as np
    >>> data = np.ones([5, 6]) * np.arange(6)
    >>> cyclic_data = add_cyclic_point(data)
    >>> print cyclic_data
    [[ 0.  1.  2.  3.  4.  5.  0.]
     [ 0.  1.  2.  3.  4.  5.  0.]
     [ 0.  1.  2.  3.  4.  5.  0.]
     [ 0.  1.  2.  3.  4.  5.  0.]
     [ 0.  1.  2.  3.  4.  5.  0.]]

    Adding a cyclic point to a data array and an associated coordinate

    >>> lons = np.arange(0, 360, 60)
    >>> cyclic_data, cyclic_lons = add_cyclic_point(data, coord=lons)
    >>> print cyclic_data
    [[ 0.  1.  2.  3.  4.  5.  0.]
     [ 0.  1.  2.  3.  4.  5.  0.]
     [ 0.  1.  2.  3.  4.  5.  0.]
     [ 0.  1.  2.  3.  4.  5.  0.]
     [ 0.  1.  2.  3.  4.  5.  0.]]
    >>> print cyclic_lons
    [  0  60 120 180 240 300 360]

    """
    if coord is not None:
        if coord.ndim != 1:
            raise ValueError('The coordinate must be 1-dimensional.')
        if len(coord) != data.shape[axis]:
            raise ValueError('The length of the coordinate does not match '
                             'the size of the corresponding dimension of '
                             'the data array: len(coord) = {}, '
                             'data.shape[{}] = {}.'.format(
                                 len(coord), axis, data.shape[axis]))
        delta_coord = np.diff(coord)
        if not np.allclose(delta_coord, delta_coord[0]):
            raise ValueError('The coordinate must be equally spaced.')
        new_coord = ma.concatenate((coord, coord[-1:] + delta_coord[0]))
    slicer = [slice(None)] * data.ndim
    try:
        slicer[axis] = slice(0, 1)
    except IndexError:
        raise ValueError('The specified axis does not correspond to an '
                         'array dimension.')
    new_data = ma.concatenate((data, data[slicer]), axis=axis)
    if coord is None:
        return_value = new_data
    else:
        return_value = new_data, new_coord
    return return_value

########NEW FILE########
__FILENAME__ = vector_transform
# (C) British Crown Copyright 2013, Met Office
#
# This file is part of cartopy.
#
# cartopy is free software: you can redistribute it and/or modify it under
# the terms of the GNU Lesser General Public License as published by the
# Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# cartopy is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Lesser General Public License for more details.
#
# You should have received a copy of the GNU Lesser General Public License
# along with cartopy.  If not, see <http://www.gnu.org/licenses/>.
"""
This module contains generic functionality to support Cartopy vector
transforms.

"""
import numpy as np
from scipy.interpolate import griddata


def _interpolate_to_grid(nx, ny, x, y, *scalars, **kwargs):
    """
    Interpolates two vector components and zero or more scalar fields,
    which can be irregular, to a regular grid.

    Kwargs:

    * target_extent:
        The extent in the target CRS that the grid should occupy, in the
        form ``(x-lower, x-upper, y-lower, y-upper)``. Defaults to cover
        the full extent of the vector field.

    """
    target_extent = kwargs.get('target_extent', None)
    if target_extent is None:
        target_extent = (x.min(), x.max(), y.min(), y.max())
    points = np.array([x.ravel(), y.ravel()]).T
    x0, x1, y0, y1 = target_extent
    x_grid, y_grid = np.meshgrid(np.linspace(x0, x1, nx),
                                 np.linspace(y0, y1, ny))
    s_grid_tuple = tuple()
    for s in scalars:
        s_grid_tuple += (griddata(points, s.ravel(), (x_grid, y_grid),
                                  method='linear'),)
    return (x_grid, y_grid) + s_grid_tuple


def vector_scalar_to_grid(src_crs, target_proj, regrid_shape, x, y, u, v,
                          *scalars, **kwargs):
    """
    Transform and interpolate a vector field to a regular grid in the
    target projection.

    Args:

    * src_crs:
        The :class:`~cartopy.crs.CRS` that represents the coordinate
        system the vectors are defined in.

    * target_proj:
        The :class:`~cartopy.crs.Projection` that represents the
        projection the vectors are to be transformed to.

    * regrid_shape:
        The regular grid dimensions. If a single integer then the grid
        will have that number of points in the x and y directions. A
        2-tuple of integers specify the size of the regular grid in the
        x and y directions respectively.

    * x, y:
        The x and y coordinates, in the source CRS coordinates,
        where the vector components are located.

    * u, v:
        The grid eastward and grid northward components of the
        vector field respectively. Their shapes must match.

    * scalars:
        Zero or more scalar fields to regrid along with the vector
        components. Each scalar field must have the same shape as the
        vector components.

    Kwargs:

    * target_extent:
        The extent in the target CRS that the grid should occupy, in the
        form ``(x-lower, x-upper, y-lower, y-upper)``. Defaults to cover
        the full extent of the vector field.

    Returns:

    * x_grid, y_grid:
        The x and y coordinates of the regular grid points as
        2-dimensional arrays.

    * u_grid, v_grid:
        The eastward and northward components of the vector field on
        the regular grid.

    * scalars_grid:
        The scalar fields on the regular grid. The number of returned
        scalar fields is the same as the number that were passed in.

    """
    if u.shape != v.shape:
        raise ValueError('u and v must be the same shape')
    if x.shape != u.shape:
        x, y = np.meshgrid(x, y)
        if not (x.shape == y.shape == u.shape):
            raise ValueError('x and y coordinates are not compatible '
                             'with the shape of the vector components')
    if scalars:
        for s in scalars:
            if s.shape != u.shape:
                raise ValueError('scalar fields must have the same '
                                 'shape as the vector components')
    try:
        nx, ny = regrid_shape
    except TypeError:
        nx = ny = regrid_shape
    if target_proj != src_crs:
        # Transform the vectors to the target CRS.
        u, v = target_proj.transform_vectors(src_crs, x, y, u, v)
        # Convert Coordinates to the target CRS.
        proj_xyz = target_proj.transform_points(src_crs, x, y)
        x, y = proj_xyz[..., 0], proj_xyz[..., 1]
    # Now interpolate to a regular grid in projection space, treating each
    # component as a scalar field.
    return _interpolate_to_grid(nx, ny, x, y, u, v, *scalars, **kwargs)

########NEW FILE########
__FILENAME__ = download
#!/usr/bin/env python
# (C) British Crown Copyright 2011 - 2012, Met Office
#
# This file is part of cartopy.
#
# cartopy is free software: you can redistribute it and/or modify it under
# the terms of the GNU Lesser General Public License as published by the
# Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# cartopy is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Lesser General Public License for more details.
#
# You should have received a copy of the GNU Lesser General Public License
# along with cartopy.  If not, see <http://www.gnu.org/licenses/>.
"""
This module provides a command-line tool for triggering the download of
the data used by various Feature instances.

For detail on how to use this tool, execute it with the `-h` option:

    python download.py -h

"""
import argparse

from cartopy.feature import Feature, GSHHSFeature, NaturalEarthFeature
from cartopy.crs import PlateCarree
import matplotlib.pyplot as plt


ALL_SCALES = ('110m', '50m', '10m')


FEATURE_DEFN_GROUPS = {
    # Only need one GSHHS resolution because they *all* get downloaded
    # from one file.
    'gshhs': GSHHSFeature(scale='c'),
    'physical': (
        ('physical', 'coastline', ALL_SCALES),
        ('physical', 'land', ALL_SCALES),
        ('physical', 'ocean', ALL_SCALES),
        ('physical', 'rivers_lake_centerlines', ALL_SCALES),
        ('physical', 'lakes', ALL_SCALES),
        ('physical', 'geography_regions_polys', ALL_SCALES),
        ('physical', 'geography_regions_points', ALL_SCALES),
        ('physical', 'geography_marine_polys', ALL_SCALES),
        ('physical', 'glaciated_areas', ALL_SCALES)
    ),
    'cultural': (
        ('cultural', 'admin_0_countries', ALL_SCALES),
        ('cultural', 'admin_0_countries_lakes', ALL_SCALES),
        ('cultural', 'admin_0_sovereignty', ALL_SCALES),
        ('cultural', 'admin_0_boundary_lines_land', ALL_SCALES),

        ('cultural', 'urban_areas', ('50m', '10m')),

        #('cultural', 'roads', '10m'), # ERROR in NE dataset?
        ('cultural', 'roads_north_america', '10m'),
        ('cultural', 'railroads', '10m'),
        ('cultural', 'railroads_north_america', '10m'),
    ),
    'cultural-extra': (
        ('cultural', 'admin_0_map_units', '110m'),
        ('cultural', 'admin_0_scale_rank', '110m'),
        ('cultural', 'admin_0_tiny_countries', '110m'),
        ('cultural', 'admin_0_pacific_groupings', '110m'),
        ('cultural', 'admin_1_states_provinces_shp', '110m'),
        ('cultural', 'admin_1_states_provinces_lines', '110m'),
    ),
}


def download_features(group_names, hold):
    plt.ion()
    ax = plt.axes(projection=PlateCarree())
    ax.set_global()
    for group_name in group_names:
        feature_defns = FEATURE_DEFN_GROUPS[group_name]
        if isinstance(feature_defns, Feature):
            features = [feature_defns]
        else:
            features = []
            for category, name, scales in feature_defns:
                if not isinstance(scales, tuple):
                    scales = (scales,)
                for scale in scales:
                    features.append(NaturalEarthFeature(category, name, scale))
        for feature in features:
            ax.add_feature(feature)
            plt.draw()

    plt.ioff()
    if hold:
        plt.show()


if __name__ == '__main__':
    def group_name(string):
        if string not in FEATURE_DEFN_GROUPS:
            msg = '{!r} is not a valid feature group (choose from {!s})'
            msg = msg.format(string, FEATURE_DEFN_GROUPS.keys())
            raise argparse.ArgumentTypeError(msg)
        return string

    parser = argparse.ArgumentParser(description='Download feature datasets.')
    parser.add_argument('group_names', nargs='*',
                        type=group_name,
                        metavar='GROUP_NAME',
                        help='Feature group name')
    parser.add_argument('--hold', action='store_true',
                        help='keep the matplotlib window open')
    parser.add_argument('--show', action='store_true',
                        help='show the list of valid feature group names')
    args = parser.parse_args()
    if args.show:
        print 'Feature group names:'
        for name in sorted(FEATURE_DEFN_GROUPS.keys()):
            print '   ', name
    elif not args.group_names:
       parser.error('Please supply one or more feature group names.')
    download_features(args.group_names, args.hold)

########NEW FILE########
