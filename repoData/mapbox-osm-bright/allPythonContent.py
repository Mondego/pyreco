__FILENAME__ = imposm-mapping
# Copyright 2011 Omniscale (http://omniscale.com)
# 
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
# 
#     http://www.apache.org/licenses/LICENSE-2.0
# 
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from imposm.mapping import (
    Options,
    Points, LineStrings, Polygons,
    String, Bool, Integer, OneOfInt,
    set_default_name_type, LocalizedName,
    WayZOrder, ZOrder, Direction,
    GeneralizedTable, UnionView,
    PseudoArea, meter_to_mapunit, sqr_meter_to_mapunit,
)

# # internal configuration options
# # uncomment to make changes to the default values
import imposm.config
# 
# # import relations with missing rings
imposm.config.import_partial_relations = False
# 
# # select relation builder: union or contains
imposm.config.relation_builder = 'contains'
# 
# # log relation that take longer than x seconds
# imposm.config.imposm_multipolygon_report = 60
# 
# # skip relations with more rings (0 skip nothing)
# imposm.config.imposm_multipolygon_max_ring = 0


# # You can prefer a language other than the data's local language
# set_default_name_type(LocalizedName(['name:en', 'int_name', 'name']))

db_conf = Options(
    # db='osm',
    host='localhost',
    port=5432,
    user='osm',
    password='osm',
    sslmode='allow',
    prefix='osm_new_',
    proj='epsg:900913',
)

class Highway(LineStrings):
    fields = (
        ('tunnel', Bool()),
        ('bridge', Bool()),
        ('oneway', Direction()),
        ('ref', String()),
        ('layer', Integer()),
        ('z_order', WayZOrder()),
        ('access', String()),
    )
    field_filter = (
        ('area', Bool()),
    )

places = Points(
    name = 'places',
    mapping = {
        'place': (
            'country',
            'state',
            'region',
            'county',
            'city',
            'town',
            'village',
            'hamlet',
            'suburb',
            'neighbourhood',
            'locality',
        ),
    },
    fields = (
        ('z_order', ZOrder([
            'country',
            'state',
            'region',
            'county',
            'city',
            'town',
            'village',
            'hamlet',
            'suburb',
            'neighbourhood',
            'locality',
        ])),
        ('population', Integer()),
    ),
)

admin = Polygons(
    name = 'admin',
    mapping = {
        'boundary': (
            'administrative',
        ),
    },
    fields = (
        ('admin_level', OneOfInt('1 2 3 4 5 6'.split())),
    ),
)

motorways = Highway(
    name = 'motorways',
    mapping = {
        'highway': (
            'motorway',
            'motorway_link',
            'trunk',
            'trunk_link',
        ),
    }
)

mainroads = Highway(
    name = 'mainroads',
    mapping = {
        'highway': (
            'primary',
            'primary_link',
            'secondary',
            'secondary_link',
            'tertiary',
            'tertiary_link',
    )}
)

buildings = Polygons(
    name = 'buildings',
    fields = (
        ('area', PseudoArea()),
    ),
    mapping = {
        'building': (
            '__any__',
        ),
        'railway': (
            'station',
        ),
        'aeroway': (
            'terminal',
        ),
    }
)

minorroads = Highway(
    name = 'minorroads',
    mapping = {
        'highway': (
            'road',
            'path',
            'track',
            'service',
            'footway',
            'bridleway',
            'cycleway',
            'steps',
            'pedestrian',
            'living_street',
            'unclassified',
            'residential',
    )}
)

transport_points = Points(
    name = 'transport_points',
    fields = (
        ('ref', String()),
    ),
    mapping = {
        'highway': (
            'motorway_junction',
            'turning_circle',
            'bus_stop',
        ),
        'railway': (
            'station',
            'halt',
            'tram_stop',
            'crossing',
            'level_crossing',
            'subway_entrance',
        ),
        'aeroway': (
            'aerodrome',
            'terminal',
            'helipad',
            'gate',
    )}
)

railways = LineStrings(
    name = 'railways',
    fields = (
        ('tunnel', Bool()),
        ('bridge', Bool()),
        # ('ref', String()),
        ('layer', Integer()),
        ('z_order', WayZOrder()),
        ('access', String()),
    ),
    mapping = {
        'railway': (
            'rail',
            'tram',
            'light_rail',
            'subway',
            'narrow_gauge',
            'preserved',
            'funicular',
            'monorail',
    )}
)

waterways = LineStrings(
    name = 'waterways',
    mapping = {  
        'barrier': (
            'ditch',
        ),
        'waterway': (
            'stream',
            'river',
            'canal',
            'drain',
            'ditch',
        ),
    },
    field_filter = (
        ('tunnel', Bool()),
    ),
)

waterareas = Polygons(
    name = 'waterareas',
    fields = (
        ('area', PseudoArea()),
    ),
    mapping = {
        'waterway': ('riverbank',),
        'natural': ('water',),
        'landuse': ('basin', 'reservoir'), 
    },
)

barrierpoints = Points(
    name = 'barrierpoints',
    mapping = {
        'barrier': (
            'block',
            'bollard',
            'cattle_grid',
            'chain',
            'cycle_barrier',
            'entrance',
            'horse_stile',
            'gate',
            'spikes',
            'lift_gate',
            'kissing_gate',
            'fence',
            'yes',
            'wire_fence',
            'toll_booth',
            'stile',
    )}
)
barrierways = LineStrings(
    name = 'barrierways',
    mapping = {
        'barrier': (
            'city_wall',
            'fence',
            'hedge',
            'retaining_wall',
            'wall',
            'bollard',
            'gate',
            'spikes',
            'lift_gate',
            'kissing_gate',
            'embankment',
            'yes',
            'wire_fence',
    )}
)

aeroways = LineStrings(
    name = 'aeroways',
    mapping = {
        'aeroway': (
            'runway',
            'taxiway',
    )}
)

landusages = Polygons(
    name = 'landusages',
    fields = (
        ('area', PseudoArea()),
        ('z_order', ZOrder([
            'pedestrian',
            'footway',
            'aerodrome',
            'helipad',
            'apron',
            'playground',
            'park',
            'forest',
            'cemetery',
            'farmyard',
            'farm',
            'farmland',
            'wood',
            'meadow',
            'grass',
            'wetland',
            'village_green',
            'recreation_ground',
            'garden',
            'sports_centre',
            'pitch',
            'common',
            'allotments',
            'golf_course',
            'university',
            'school',
            'college',
            'library',
            'fuel',
            'parking',
            'nature_reserve',
            'cinema',
            'theatre',
            'place_of_worship',
            'hospital',
            'scrub',
            'zoo',
            'quarry',
            'residential',
            'retail',
            'commercial',
            'industrial',
            'railway',
            'island',
            'land',
        ])),
    ),
    mapping = {
        'landuse': (
            'park',
            'forest',
            'residential',
            'retail',
            'commercial',
            'industrial',
            'railway',
            'cemetery',
            'grass',
            'farmyard',
            'farm',
            'farmland',
            'wood',
            'meadow',
            'village_green',
            'recreation_ground',
            'allotments',
            'quarry',
        ),
        'leisure': (
            'park',
            'garden',
            'playground',
            'golf_course',
            'sports_centre',
            'pitch',
            'stadium',
            'common',
            'nature_reserve',
        ),
        'natural': (
            'wood',
            'land',
            'scrub',
            'wetland',
        ),
        'highway': (
            'pedestrian',
            'footway',
        ),
        'amenity': (
            'university',
            'school',
            'college',
            'library',
            'fuel',
            'parking',
            'cinema',
            'theatre',
            'place_of_worship',
            'hospital',
        ),
        'place': (
            'island',
        ),
        'tourism': (
            'zoo',
        ),
        'aeroway': (
            'aerodrome',
            'helipad',
            'apron',
        ),
})

amenities = Points(
    name='amenities',
    mapping = {
        'amenity': (
            'university',
            'school',
            'library',
            'fuel',
            'hospital',
            'fire_station',
            'police',
            'townhall',
        ),
})

motorways_gen1 = GeneralizedTable(
    name = 'motorways_gen1',
    tolerance = meter_to_mapunit(50.0),
    origin = motorways,
)

mainroads_gen1 = GeneralizedTable(
    name = 'mainroads_gen1',
    tolerance = meter_to_mapunit(50.0),
    origin = mainroads,
)

railways_gen1 = GeneralizedTable(
    name = 'railways_gen1',
    tolerance = meter_to_mapunit(50.0),
    origin = railways,
)

motorways_gen0 = GeneralizedTable(
    name = 'motorways_gen0',
    tolerance = meter_to_mapunit(200.0),
    origin = motorways_gen1,
)

mainroads_gen0 = GeneralizedTable(
    name = 'mainroads_gen0',
    tolerance = meter_to_mapunit(200.0),
    origin = mainroads_gen1,
)

railways_gen0 = GeneralizedTable(
    name = 'railways_gen0',
    tolerance = meter_to_mapunit(200.0),
    origin = railways_gen1,
)

landusages_gen0 = GeneralizedTable(
    name = 'landusages_gen0',
    tolerance = meter_to_mapunit(200.0),
    origin = landusages,
    where = "ST_Area(geometry)>%f" % sqr_meter_to_mapunit(500000),
)

landusages_gen1 = GeneralizedTable(
    name = 'landusages_gen1',
    tolerance = meter_to_mapunit(50.0),
    origin = landusages,
    where = "ST_Area(geometry)>%f" % sqr_meter_to_mapunit(50000),
)

waterareas_gen0 = GeneralizedTable(
    name = 'waterareas_gen0',
    tolerance = meter_to_mapunit(200.0),
    origin = waterareas,
    where = "ST_Area(geometry)>%f" % sqr_meter_to_mapunit(500000),
)

waterareas_gen1 = GeneralizedTable(
    name = 'waterareas_gen1',
    tolerance = meter_to_mapunit(50.0),
    origin = waterareas,
    where = "ST_Area(geometry)>%f" % sqr_meter_to_mapunit(50000),
)

roads = UnionView(
    name = 'roads',
    fields = (
        ('bridge', 0),
        ('ref', None),
        ('tunnel', 0),
        ('oneway', 0),
        ('layer', 0),
        ('z_order', 0),
        ('access', None),
    ),
    mappings = [motorways, mainroads, minorroads, railways],
)

roads_gen1 = UnionView(
    name = 'roads_gen1',
    fields = (
        ('bridge', 0),
        ('ref', None),
        ('tunnel', 0),
        ('oneway', 0),
        ('z_order', 0),
        ('access', None),
    ),
    mappings = [railways_gen1, mainroads_gen1, motorways_gen1],
)

roads_gen0 = UnionView(
    name = 'roads_gen0',
    fields = (
        ('bridge', 0),
        ('ref', None),
        ('tunnel', 0),
        ('oneway', 0),
        ('z_order', 0),
        ('access', None),
    ),
    mappings = [railways_gen0, mainroads_gen0, motorways_gen0],
)

########NEW FILE########
__FILENAME__ = utils
import os
from distutils.file_util import copy_file, DistutilsFileError
from distutils.dir_util import mkpath

def copy_tree(src, dst, ignores=()):
    """Copy an entire directory tree 'src' to a new location 'dst'.

    Both 'src' and 'dst' must be directory names.  If 'src' is not a
    directory, raise DistutilsFileError.  If 'dst' does not exist, it is
    created with 'mkpath()'.  The end result of the copy is that every
    file in 'src' is copied to 'dst', and directories under 'src' are
    recursively copied to 'dst'.  Return the list of files that were
    copied or might have been copied, using their output name.
    
    Ignore any file whose name is in the "ignores" iterable.

    This is a forked version of distutils.dir_util.copy_tree, which
    did not have a way to ignore the files I wanted to ignore.
    """
    if not os.path.isdir(src):
        raise DistutilsFileError, "cannot copy tree '%s': not a directory" % src

    try:
        names = os.listdir(src)
    except os.error, (errno, errstr):
        raise DistutilsFileError, "error listing files in '%s': %s" % (src, errstr)

    mkpath(dst)

    outputs = []

    for n in names:
        if n in ignores: continue

        src_name = os.path.join(src, n)
        dst_name = os.path.join(dst, n)

#def copy_tree(src, dst, preserve_mode=1, preserve_times=1,
#              preserve_symlinks=0, update=0, verbose=1, dry_run=0):

        if os.path.islink(src_name):
            continue
        elif os.path.isdir(src_name):
            outputs.extend(copy_tree(src_name, dst_name, ignores))
        else:
            copy_file(src_name, dst_name, verbose=1)
            outputs.append(dst_name)

    return outputs

########NEW FILE########
__FILENAME__ = make
#!/usr/bin/env python

import re
import sys

from os import unlink
from json import loads, dumps
from glob import glob
from shutil import rmtree
from os.path import join, isdir, expanduser, exists
from collections import defaultdict

if not exists('./configure.py'):
    sys.stderr.write('Error: configure.py does not exist, did you forget to create it from the sample (configure.py.sample)?\n')
    sys.exit(1)
elif exists('./configure.pyc'):
    unlink('./configure.pyc')

from configure import config
from lib.utils import copy_tree

config["path"] = expanduser(config["path"])

def clean():
  if isdir("build"):
    rmtree("build")

  for f in glob("build/*.html"): unlink(f)

def build():
  #copy the osm-bright tree to a build dir
  copy_tree("osm-bright", "build")

  #remove the mml templates
  for f in glob("build/*.mml"):
    unlink(f)

  #load the project template
  templatefile = open(join('osm-bright', 'osm-bright.%s.mml' % config["importer"]))
  template = loads(templatefile.read())

  #fill in the project template
  for layer in template["Layer"]:
    if layer["id"] == "shoreline_300":
      layer["Datasource"]["file"] = config["shoreline_300"]
    elif layer["id"] in ("processed_p", "processed_p_outline"):
      layer["Datasource"]["file"] = config["processed_p"]
    elif layer["id"] in ("land"):
      layer["Datasource"]["file"] = config["land"]
    else:
      # Assume all other layers are PostGIS layers
      for opt, val in config["postgis"].iteritems():
        if (val == ""):
          if (opt in layer["Datasource"]):
            del layer["Datasource"][opt]
        else:
          layer["Datasource"][opt] = val

  template["name"] = config["name"]

  #dump the filled-in project template to the build dir
  with open(join('build', 'project.mml'), 'w') as output:
    output.write(dumps(template, sort_keys=True, indent=2))

def install():
  assert isdir(config["path"]), "Config.path does not point to your mapbox projects directory; please fix and re-run"
  sanitized_name = re.sub("[^\w]", "", config["name"])
  output_dir = join(config["path"], sanitized_name)
  print "installing to %s" % output_dir
  copy_tree("build", output_dir)

def pull():
  #copy the project from mapbox to osm-bright
  sanitized_name = re.sub("[^\w]", "", config["name"])
  output_dir = join(config["path"], sanitized_name)
  copy_tree(output_dir, "osm-bright", ("layers", ".thumb.png"))

  #load the project file
  project = loads(open(join("osm-bright", "project.mml")).read())

  #Make sure we reset postgis data in the project file back to its default values
  defaultconfig = defaultdict(defaultdict)
  defaultconfig["postgis"]["host"]     = ""
  defaultconfig["postgis"]["port"]     = ""
  defaultconfig["postgis"]["dbname"]   = "osm"
  defaultconfig["postgis"]["user"]     = ""
  defaultconfig["postgis"]["password"] = ""
  defaultconfig["postgis"]["extent"] = "-20037508.34 -20037508.34 20037508.34 20037508.34"
  defaultconfig["name"] = "OSM Bright"
  defaultconfig["processed_p"] = "http://tilemill-data.s3.amazonaws.com/osm/coastline-good.zip"
  defaultconfig["shoreline_300"] = "http://tilemill-data.s3.amazonaws.com/osm/shoreline_300.zip"
  defaultconfig["land"] = "http://mapbox-geodata.s3.amazonaws.com/natural-earth-1.3.0/physical/10m-land.zip"

  project["name"] = defaultconfig["name"]
  for layer in project["Layer"]:
    if layer["id"] == "shoreline_300":
      layer["Datasource"]["file"] = defaultconfig["shoreline_300"]
    elif layer["id"] in ("processed_p", "processed_p_outline"):
      layer["Datasource"]["file"] = defaultconfig["processed_p"]
    else:
      # Assume all other layers are PostGIS layers
      for opt, val in defaultconfig["postgis"].iteritems():
        if val and opt in layer["Datasource"]:
          layer["Datasource"][opt] = val
        elif opt in layer["Datasource"]:
          del layer["Datasource"][opt]

  project_template = open(join("osm-bright", "osm-bright.%s.mml") % config["importer"], 'w')
  project_template.write(dumps(project, sort_keys=True, indent=2))

  #now delete project.mml
  unlink(join("osm-bright", "project.mml"))

if __name__ == "__main__":
  if sys.argv[-1] == "clean":
    clean()
  elif sys.argv[-1] == "build":
    build()
  elif sys.argv[-1] == "install":
    install()
  elif sys.argv[-1] == "pull":
    pull()
  else:
    clean()
    build()
    install()

########NEW FILE########
