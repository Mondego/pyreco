__FILENAME__ = configure.py.sample
#!/usr/bin/env python

from os import path
from collections import defaultdict
config = defaultdict(defaultdict)

# The name given to the style. This is the name it will have in the TileMill
# project list, and a sanitized version will be used as the directory name
# in which the project is stored
config["name"] = "Toner for Tilemill"

# The absolute path to your MapBox projects directory. You should 
# not need to change this unless you have configured TileMill specially
config["path"] = path.expanduser("~/Documents/MapBox/project")

# PostGIS connection setup
# Leave empty for Mapnik defaults. The only required parameter is dbname.
config["postgis"]["host"]     = ""
config["postgis"]["port"]     = ""
config["postgis"]["dbname"]   = "osm"
config["postgis"]["user"]     = ""
config["postgis"]["password"] = ""

# Increase performance if you are only rendering a particular area by
# specifying a bounding box to restrict queries. Format is "XMIN,YMIN,XMAX,YMAX"
# in the same units as the database (probably spherical mercator meters). The
# whole world is "-20037508.34 -20037508.34 20037508.34 20037508.34".
# Leave blank to let Mapnik estimate.
config["postgis"]["extent"] = "-20037508.34 -20037508.34 20037508.34 20037508.34"

# Coastline shapefile, for #land.
# another source: http://data.openstreetmapdata.com/coastlines-split-3857.zip
# or reproject the original (though there are often errors) http://tile.openstreetmap.org/processed_p.tar.bz2
config["processed_p"] = "http://tilemill-data.s3.amazonaws.com/osm/coastline-good.zip"
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
	#copy the toner4tilemill tree to a build dir
	copy_tree("toner4tilemill", "build")

	#remove the mml templates
	for f in glob("build/*.mml"):
		unlink(f)

	#load the project template
	templatefile = open(join('toner4tilemill', 'project.mml'))
	template = loads(templatefile.read())

	#fill in the project template
	for layer in template["Layer"]:
		if layer["id"] in ("land"):
			layer["Datasource"]["file"] = config["processed_p"]
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
	#copy the project from mapbox to toner4tilemill
	sanitized_name = re.sub("[^\w]", "", config["name"])
	output_dir = join(config["path"], sanitized_name)
	copy_tree(output_dir, "toner4tilemill", ("layers", ".thumb.png"))

	#load the project file
	project = loads(open(join("toner4tilemill", "project.mml")).read())

	#Make sure we reset postgis data in the project file back to its default values
	defaultconfig = defaultdict(defaultdict)
	defaultconfig["postgis"]["host"]     = ""
	defaultconfig["postgis"]["port"]     = ""
	defaultconfig["postgis"]["dbname"]   = "osm"
	defaultconfig["postgis"]["user"]     = ""
	defaultconfig["postgis"]["password"] = ""
	defaultconfig["postgis"]["extent"] = "-20037508.34 -20037508.34 20037508.34 20037508.34"
	defaultconfig["name"] = "Toner for Tilemill"
	defaultconfig["processed_p"] = "http://tile.openstreetmap.org/processed_p.tar.bz2"

	project["name"] = defaultconfig["name"]
	for layer in project["Layer"]:
		if layer["id"] in ("land"):
			layer["Datasource"]["file"] = defaultconfig["processed_p"]
		else:
			# Assume all other layers are PostGIS layers
			for opt, val in defaultconfig["postgis"].iteritems():
				if val and opt in layer["Datasource"]:
					layer["Datasource"][opt] = val
				elif opt in layer["Datasource"]:
					del layer["Datasource"][opt]

	project_template = open(join('toner4tilemill', 'project.mml'), 'w')
	project_template.write(dumps(project, sort_keys=True, indent=2))

	#now delete project.mml
	unlink(join("toner4tilemill", "project.mml"))

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
