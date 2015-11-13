__FILENAME__ = rez-config-list_
#!!REZ_PYTHON_BINARY!

#
# List information about a particular package, or the latest version of every package
# found in the given directory, or the default central packages directory if none is
# specified.
#

import os
import os.path
import sys
import optparse
import yaml
import sigint

import rez_filesys as fs


p = optparse.OptionParser()
p.add_option("-p", "--path", dest="path", default=os.environ["REZ_RELEASE_PACKAGES_PATH"], \
	help="path where packages are located [default = %default]")
p.add_option("--package", dest="package", default=None, \
	help="specific package to list info on [default = %default]")
p.add_option("-n", "--no-missing", dest="nomissing", action="store_true", default=False, \
	help="don't list packages that are missing any of the requested fields [default = %default]")
p.add_option("--auth", dest="auth", action="store_true", default=False, \
	help="list package authors [default = %default]")
p.add_option("--desc", dest="desc", action="store_true", default=False, \
	help="list package description [default = %default]")
p.add_option("--dep", dest="dep", action="store_true", default=False, \
	help="list package dependencies [default = %default]")

(opts, args) = p.parse_args()


if not os.path.isdir(opts.path):
	sys.stderr.write("'" + opts.path + "' is not a directory.\n")
	sys.exit(1)

pkg_paths = []

if opts.package:
	fullpath = os.path.join(opts.path, opts.package)
	if not os.path.isdir(fullpath):
		sys.stderr.write("'" + fullpath + "' is not a directory.\n")
		sys.exit(1)
	pkg_paths = [fullpath]
else:
	for f in os.listdir(opts.path):
		if (f == "rez"):
			continue

		fullpath = os.path.join(opts.path, f)
		if os.path.isdir(fullpath):
			pkg_paths.append(fullpath)


for fullpath in pkg_paths:

	vers = [x for x in fs.get_versions_in_directory(fullpath, False)]
	if vers:
		filename = fullpath + '/' + str(vers[-1][0]) + "/package.yaml"
		metadict = yaml.load(open(filename).read())

		ln = fullpath.split('/')[-1]

		if opts.auth:
			ln = ln + " | "
			if "authors" in metadict:
				ln = ln + str(" ").join(metadict["authors"])
			else:
				continue

		if opts.desc:
			ln = ln + " | "
			if "description" in metadict:
				descr = str(metadict["description"]).strip()
				descr = descr.replace('\n', "\\n")
				ln = ln + descr
			else:
				continue

		if opts.dep:
			ln = ln + " | "
			reqs = metadict["requires"] if ("requires" in metadict) else []
			vars = metadict["variants"] if ("variants" in metadict) else []
			if len(reqs) + len(vars) > 0:

				fn_unver = lambda pkg: pkg.split('-')[0]
				deps = set(map(fn_unver, reqs))
				for var in vars:
					deps = deps | set(map(fn_unver, var))

				if len(deps) > 0:
					ln = ln + "*" + str(" *").join(deps)

		print ln








#    Copyright 2008-2012 Dr D Studios Pty Limited (ACN 127 184 954) (Dr. D Studios)
#
#    This file is part of Rez.
#
#    Rez is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Lesser General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
#
#    Rez is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU Lesser General Public License
#    along with Rez.  If not, see <http://www.gnu.org/licenses/>.

########NEW FILE########
__FILENAME__ = rez-config_
#!!REZ_PYTHON_BINARY!

#
# rez-config
#
# A tool for resolving a configuration request. Output from this util can be used to setup
# said configuration (rez-env does this).
#

import os
import sys
import optparse



##########################################################################################
# parse arguments
##########################################################################################
usage = "usage: %prog [options] pkg1 pkg2 ... pkgN"
p = optparse.OptionParser(usage=usage)

p.add_option("-m", "--mode", dest="mode", default="latest", \
	help="set resolution mode (earliest, latest) [default = %default]")
p.add_option("-v", "--verbosity", dest="verbosity", type="int", default=0, \
	help="set verbosity (0..2) [default = %default]")
p.add_option("--version", dest="version", action="store_true", default=False, \
	help="print the rez version number and exit [default = %default]")
p.add_option("--quiet", dest="quiet", action="store_true", default=False, \
	help="hide unnecessary output [default = %default]")
p.add_option("--no-os", dest="no_os", action="store_true", default=False, \
	help="stop rez from implicitly requesting the operating system package [default = %default]")
p.add_option("-b", "--build-requires", dest="buildreqs", action="store_true", default=False, \
	help="include build-only required packages [default = %default]")
p.add_option("--max-fails", dest="max_fails", type="int", default=-1, \
	help="exit when the number of failed configuration attempts exceeds N [default = no limit]")
p.add_option("--no-cache", dest="no_cache", action="store_true", default=False, \
	help="disable caching [default = %default]")
p.add_option("--dot-file", dest="dot_file", type="string", default="", \
	help="write the dot-graph to the file specified (dot, gif, jpg, png, pdf supported). " + \
		"Note that if resolution fails, the last failed attempt will still produce an image. " + \
		"You can use --dot-file in combination with --max-fails to debug resolution failures.")
p.add_option("--print-env", dest="print_env", action="store_true", default=False, \
	help="print commands which, if run, would produce the configured environment [default = %default]")
p.add_option("--print-packages", dest="print_pkgs", action="store_true", default=False, \
	help="print resolved packages for this configuration [default = %default]")
p.add_option("--print-dot", dest="print_dot", action="store_true", default=False, \
	help="output a dot-graph representation of the configuration resolution [default = %default]")
p.add_option("--meta-info", dest="meta_info", type="string", \
    help="Bake metadata into env-vars. Eg: --meta-info=tools,priority")
p.add_option("--meta-info-shallow", dest="meta_info_shallow", type="string", \
    help="Same as --meta-info, but only bakes data for directly requested packages.")
p.add_option("--ignore-archiving", dest="ignore_archiving", action="store_true", default=False, \
	help="silently ignore packages that have been archived [default = %default]")
p.add_option("--ignore-blacklist", dest="ignore_blacklist", action="store_true", default=False, \
	help="include packages that are blacklisted [default = %default]")
p.add_option("--no-assume-dt", dest="no_assume_dt", action="store_true", default=False, \
	help="do not assume dependency transitivity [default = %default]")
p.add_option("--no-catch", dest="no_catch", action="store_true", default=False, \
	help="debugging option, turn on to see python exception on error [default = %default]")
p.add_option("-t", "--time", dest="time", default="0", \
	help="ignore packages newer than the given epoch time [default = current time]")
p.add_option("--no-path-append", dest="no_path_append", action="store_true", default=False, \
	help="don't append system-specific paths to PATH [default = %default]")
p.add_option("--wrapper", dest="wrapper", action="store_true", default=False, \
	help="set to true if creating a wrapper environment [default = %default]")
p.add_option("--no-local", dest="no_local", action="store_true", default=False, \
	help="don't load local packages")

if (len(sys.argv) == 1):
	(opts, extraArgs) = p.parse_args(["-h"])
	sys.exit(0)

(opts, pkgstrs) = p.parse_args()

if opts.version:
	print os.getenv("REZ_VERSION")
	sys.exit(0)

if (opts.verbosity < 0) or (opts.verbosity > 2):
	sys.stderr.write("rez-config: error: option -v: invalid integer value: " + str(opts.verbosity) + '\n')
	sys.exit(1)

# force quiet with some options
do_quiet = opts.quiet or opts.print_env or opts.print_pkgs or opts.print_dot

# validate time
time_epoch = int(opts.time)

# parse out meta bake
meta_vars = (opts.meta_info or '').replace(',',' ').strip().split()
shallow_meta_vars = (opts.meta_info_shallow or '').replace(',',' ').strip().split()

# hide local pkgs
if opts.no_local:
	localpath = os.getenv("REZ_LOCAL_PACKAGES_PATH").strip()
	if localpath:
		pkgpaths = os.getenv("REZ_PACKAGES_PATH","").strip().split(':')
		if localpath in pkgpaths:
			pkgpaths.remove(localpath)
			os.environ["REZ_PACKAGES_PATH"] = str(':').join(pkgpaths)

import rez_config as dc

mode = None
if (opts.mode == "none"):
	mode = dc.RESOLVE_MODE_NONE
elif (opts.mode == "latest"):
	mode = dc.RESOLVE_MODE_LATEST
elif (opts.mode == "earliest"):
	mode = dc.RESOLVE_MODE_EARLIEST
else:
	sys.stderr.write("rez-config: error: option -m: illegal resolution mode '" + opts.mode + "'\n")
	sys.exit(1)


##########################################################################################
# construct package request
##########################################################################################
resolver = dc.Resolver(mode, do_quiet, opts.verbosity, opts.max_fails, time_epoch, \
	opts.buildreqs, not opts.no_assume_dt, not opts.no_cache)

if opts.no_catch:
	pkg_reqs = [dc.str_to_pkg_req(x) for x in pkgstrs]
	pkg_ress, env_cmds, dot_graph, num_fails = resolver.resolve(pkg_reqs, opts.no_os, \
		opts.no_path_append, opts.wrapper, meta_vars, shallow_meta_vars)
else:
	result = resolver.guarded_resolve(pkgstrs, opts.no_os, opts.no_path_append, opts.wrapper, \
		meta_vars, shallow_meta_vars, opts.dot_file, opts.print_dot)

	if not result:
		sys.exit(1)
	pkg_ress, env_cmds, dot_graph, num_fails = result



##########################################################################################
# print result
##########################################################################################

if not do_quiet:
	print "\nsuccessful configuration found after " + str(num_fails) + " failed attempts."

if opts.print_env:
	for env_cmd in env_cmds:
		print env_cmd

if opts.print_pkgs:
	for pkg_res in pkg_ress:
		print pkg_res.short_name()



#    Copyright 2008-2012 Dr D Studios Pty Limited (ACN 127 184 954) (Dr. D Studios)
#
#    This file is part of Rez.
#
#    Rez is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Lesser General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
#
#    Rez is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU Lesser General Public License
#    along with Rez.  If not, see <http://www.gnu.org/licenses/>.

########NEW FILE########
__FILENAME__ = rez-depends_
#!!REZ_PYTHON_BINARY!

#
# Display unversioned dependency information of every package found in the given directory,
# or the default central packages directory if none is specified. Only information from the
# latest version of every package is used.
#
# examples:
#
# to print a list of packages that directly or indirectly use vacuum:
# rez-depends vacuum
#
# to print a list of packages that directly use vacuum:
# rez-depends --depth=1 vacuum
#
# to check for cyclic dependencies over all packages:
# rez-depends --cyclic-test-only
#
# to view a dot-graph showing all dependencies of boost:
# rez-depends --show-dot boost
#
# to view a dot-graph showing all dependencies of all packages (a BIG image):
# rez-depends --show-dot --all
#
# TODO rewrite to use find_package2, more robust.
#


import os
import os.path
import sys
import optparse
import yaml
import sigint
import rez_filesys as fs


#########################################################################################
# functions
#########################################################################################

def _detect_cycle(pkgmap, depchain, depset):
	pkg = depchain[-1]
	if pkg in pkgmap:
		for pkg2 in pkgmap[pkg]:
			if pkg2 in depset:
				depchain2 = depchain[:]
				while depchain2[0] != pkg2:
					del depchain2[0]
				depchain2.append(pkg2)
				return depchain2

			depchain2 = depchain[:]
			depset2 = depset.copy()
			depchain2.append(pkg2)
			depset2.add(pkg2)
			depchain3 = _detect_cycle(pkgmap, depchain2, depset2)
			if len(depchain3) > 0:
				return depchain3

	return []


def detect_cycle(pkg, pkgmap):
	return _detect_cycle(pkgmap, [pkg], set(pkg))



#########################################################################################
# command-line
#########################################################################################

usage = "usage: %prog [options] pkg1 pkg2 ... pkgN"
p = optparse.OptionParser(usage=usage)

p.add_option("-p", "--path", dest="path", default=os.environ["REZ_PACKAGES_PATH"], \
	help="path where packages are located [default = %default]")
p.add_option("-d", "--depth", dest="depth", type="int", default=0, \
	help="max recursion depth, defaults to no limit (0)")
p.add_option("-q", "--quiet", dest="quiet", action="store_true", default=False, \
	help="suppress unnecessary output [default = %default]")
p.add_option("-a", "--all", dest="all", action="store_true", default=False, \
	help="select all existing packages (pkg1 .. pkgN will be ignored) [default = %default]")
p.add_option("--cyclic-test-only", dest="ctest", action="store_true", default=False, \
	help="just perform cyclic dependency checks, then exit [default = %default]")
p.add_option("--print-dot", dest="printdot", action="store_true", default=False, \
	help="print dependency info in dot notation [default = %default]")
p.add_option("--show-dot", dest="showdot", action="store_true", default=False, \
	help="display dependency info in a dot graph [default = %default]")


if (len(sys.argv) == 1):
	p.parse_args(["-h"])
	sys.exit(0)

(opts, packages) = p.parse_args()
packages_set = set(packages)
if not packages_set:
	opts.all = True

paths = opts.path.split(':')

if opts.depth == 0:
	opts.depth = -1


#########################################################################################
# main
#########################################################################################

#----------------------------------------------------------------------------------------
# create a map of package dependency info
#----------------------------------------------------------------------------------------

dependsMap = {}

all_packages = set()

all_dirs = []
for path in paths:
	if os.path.isdir(path):
		for name in os.listdir(path):
			path2 = os.path.join(path, name)
			if os.path.isdir(path2):
				all_dirs.append(path2)
	else:
		print >> sys.stderr, "Warning: skipping nonexistent path %s..." % path

if not opts.quiet:
	print("gathering packages...")
	sys.stdout.write('[           ]\b\b\b\b\b\b\b\b\b\b\b\b.')
	sys.stdout.flush()
	progstep = len(all_dirs) / 10.0
	ndir = 0

for fullpath in all_dirs:
	f = os.path.basename(fullpath)

	if not opts.quiet:
		prog1 = ndir / progstep
		ndir = ndir + 1
		prog2 = ndir / progstep
		if int(prog1) < int(prog2):
			sys.stdout.write('.')
			sys.stdout.flush()

	# tmp until rez is bootstrapped with itself
	if (f == "rez"):
		continue

	all_packages.add(f)

	vers = [x[0] for x in fs.get_versions_in_directory(fullpath, False)]
	if vers:
		filename = fullpath + '/' + str(vers[-1][0]) + "/package.yaml"
		metadict = yaml.load(open(filename).read())

		reqs = metadict["requires"] if ("requires" in metadict) else []
		vars = metadict["variants"] if ("variants" in metadict) else []
		if len(reqs) + len(vars) > 0:

			fn_unver = lambda pkg: pkg.split('-')[0]
			deps = set(map(fn_unver, reqs))
			for var in vars:
				deps = deps | set(map(fn_unver, var))

			for dep in deps:
				if dep not in dependsMap:
					dependsMap[dep] = set()
				dependsMap[dep].add(f)

if not opts.quiet:
	print("\ndetecting cyclic dependencies...")

if opts.all:
	packages_set = all_packages


#----------------------------------------------------------------------------------------
# detect cyclic dependencies. Note that this has to be done over all packages, since we
# can't know ahead of time what packages will end up in the dependency tree
#----------------------------------------------------------------------------------------

cycles = set()
cycle_pkgs = set()

for pkg in all_packages:
	cycle = detect_cycle(pkg, dependsMap)
	if len(cycle) > 0:

		# A<--B<--A is the same as B<--A<--B so rotate the list until the smallest string
		# is at the front, so we don't get multiple reports of the same cycle
		del cycle[-1]
		smallest_str = cycle[0]
		for cpkg in cycle:
			if cpkg < smallest_str:
				smallest_str = cpkg
		while cycle[0] != smallest_str:
			cycle.append(cycle[0])
			del cycle[0]

		cycle_pkgs |= set(cycle)
		cycle.append(cycle[0])
		cycle_str = str("<--").join(cycle)
		cycles.add(cycle_str)

if len(cycles) > 0:
		if not opts.quiet:
			print("CYCLIC DEPENDENCY(S) DETECTED; ALL INVOLVED PACKAGES WILL BE REMOVED FROM FURTHER PROCESSING:")
			for c in cycles:
				print c

		if opts.ctest:
			sys.exit(1)

		if not opts.quiet:
			print

		for cpkg in cycle_pkgs:
			if cpkg in dependsMap:
				del dependsMap[cpkg]

		for dpkg in dependsMap:
			dependsMap[dpkg] -= cycle_pkgs


if opts.ctest:
	sys.exit(0)



#----------------------------------------------------------------------------------------
# find pkgs dependent on the given pkgs
#----------------------------------------------------------------------------------------

if not opts.quiet:
	print("identifying dependencies...")

deps = packages_set
deps2 = set()
depsAll = set()
depth = 0

dotout = None
if opts.printdot:
	dotout = sys.stdout
elif opts.showdot:
	import cStringIO
	dotout = cStringIO.StringIO()

if dotout:
	from rez_config import make_random_color_string
	dotout.write("digraph g { \n")
	dotpairs = set()

while (len(deps) > 0) and (depth != opts.depth):
	if not opts.quiet:
		print "@ depth " + str(depth) + " (" + str(len(deps)) + " packages)..."

	for dep in deps:
		if dep in dependsMap:
			mapentry = dependsMap[dep]
			deps2 |= mapentry
			depsAll |= mapentry
			del dependsMap[dep]

			if dotout:
				for pkg in mapentry:
					dotpair_str = pkg + " -> " + dep
					if dotpair_str not in dotpairs:
						rcol = make_random_color_string()
						dotout.write('    ' + dotpair_str + ' [color="' + rcol + '"];\n')
						dotpairs.add(dotpair_str)

	deps = deps2
	deps2 = set()
	depth = depth + 1

if dotout:
	dotout.write("} \n")
	dotout.flush()

	if opts.showdot:
		import pydot
		import tempfile

		g = pydot.graph_from_dot_data(dotout.getvalue())
		dotout.close()
		fd, jpgpath = tempfile.mkstemp('.jpg')
		os.close(fd)
		g.write_jpg(jpgpath)

		import subprocess
		cmd = os.getenv("REZ_DOT_IMAGE_VIEWER", "xnview") + " " + jpgpath
		if not opts.quiet:
			print("invoking: " + cmd)
		pret = subprocess.Popen(cmd, shell=True)
		pret.communicate()
		os.remove(jpgpath)


# print dependent packages
if not dotout:
	for dep in depsAll:
		print dep
















#    Copyright 2008-2012 Dr D Studios Pty Limited (ACN 127 184 954) (Dr. D Studios)
#
#    This file is part of Rez.
#
#    Rez is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Lesser General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
#
#    Rez is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU Lesser General Public License
#    along with Rez.  If not, see <http://www.gnu.org/licenses/>.

########NEW FILE########
__FILENAME__ = rez-diff_
#!!REZ_PYTHON_BINARY!
#
# A tool for listing information about the difference between two sets of packages, including
# packages that have been added, packages that have been removed, and packages whos versions
# have changed, in this case listing all the changelogs associated with the version change.
# This information can optionally be displated in HTML format for easy viewing.
#

import os
import sys
import optparse
import rez_config as dc
import sigint


#########################################################################################
# command-line
#########################################################################################

p = optparse.OptionParser(usage="Usage: rez-diff [options] oldpkg1 oldpkgN [ -- newpkg1 newpkgN ]")

p.add_option("--html", dest="html", action="store_true", default=False, \
	help="output in html format [default = %default]")
p.add_option("--view-html", dest="viewhtml", action="store_true", default=False, \
	help="view the output directly in a browser [default = %default]")

if (len(sys.argv) == 1):
	p.parse_args(["-h"])
	sys.exit(0)

# turn all old pkgs into 'pkg=e' to force start from earliest
argv = []
newgroup = False

for pkg in sys.argv[1:]:
	if pkg == "--":
		newgroup = True
	if (not newgroup) and (pkg[0] != '-'):
		if (not pkg.endswith("=e")) and (not pkg.endswith("=l")):
			pkg += "=e"
	argv.append(pkg)

septok = "__SEP__"

# add new pkgs as latest of each if they weren't supplied
if "--" in argv:
	argv[argv.index("--")] = septok
else:
	newpkgs = []
	for pkg in argv:
		if pkg[0] != '-':
			newpkgs.append(pkg.split('-',1)[0])
	argv.append(septok)
	argv += newpkgs

(opts, args) = p.parse_args(argv)

opts.html = opts.html or opts.viewhtml

pos = args.index(septok)
old_pkgs_list = args[:pos]
new_pkgs_list = args[pos+1:]


#########################################################################################
# determine which pkgs have been added, which removed, and which altered
#########################################################################################

# (family, pkg)
old_pkgs = {}
new_pkgs = {}

for pkg in old_pkgs_list:
	fam = pkg.split('=',1)[0].split("-",1)[0]
	if fam in old_pkgs:
		sys.stderr.write("Error: package '" + fam + "' appears more than once in old package group.\n")
		sys.exit(1)
	old_pkgs[fam] = pkg

for pkg in new_pkgs_list:
	fam = pkg.split('=',1)[0].split("-",1)[0]
	if fam in new_pkgs:
		sys.stderr.write("Error: package '" + fam + "' appears more than once in new package group.\n")
		sys.exit(1)
	new_pkgs[fam] = pkg

# removed packages
removed_pkgs = []
fams = set(old_pkgs.keys()) - set(new_pkgs.keys())
for fam in fams:
	removed_pkgs.append(old_pkgs[fam])

# added packages
added_pkgs = []
fams = set(new_pkgs.keys()) - set(old_pkgs.keys())
for fam in fams:
	added_pkgs.append(new_pkgs[fam])

# altered packages
updated_pkgs = []
rolledback_pkgs = []
fams = set(new_pkgs.keys()) & set(old_pkgs.keys())
for fam in fams:
	old_path = dc.get_base_path(old_pkgs[fam])
	new_path = dc.get_base_path(new_pkgs[fam])
	if old_path != new_path:
		oldverstr = old_path.rsplit("/",1)[-1]
		newverstr = new_path.rsplit("/",1)[-1]
		oldver = dc.Version(oldverstr)
		newver = dc.Version(newverstr)
		if oldver < newver:
			updated_pkgs.append( (fam, old_path, new_path) )
		else:
			rolledback_pkgs.append( (fam, new_path, old_path) )


#########################################################################################
# generate output
#########################################################################################

rowcolindex3 = 0

if opts.html:
	big_line_sep = ""
	small_line_sep = ""
	br = "<br>"

	table_bgcolor2 = "DDDDDD"
	table_bgcolor = "888888"
	rowcols3 = [ "FFE920", "FFBE28" ]
	rowcols = [ "7CE098", "86BCFF" ]
	rowcols2 = [ [ "A4F0B7", "BDF4CB" ], [ "A8CFFF", "99C7FF" ] ]

else:
	big_line_sep   = "#########################################################################################"
	small_line_sep = "========================================================================================="
	br = ""


def print_added_packages(pkgs, are_added):

	global rowcolindex3

	if len(pkgs) > 0:
		print big_line_sep
		if are_added:
			tok = "added packages:  "
		else:
			tok = "removed packages:"

		pkgs_ = []
		for pkg in pkgs:
			pkg_ = pkg.rsplit("=",1)[0]
			pkgs_.append(pkg_)

		pkglist = str(", ").join(pkgs_)
		if opts.html:
			print "<tr>"
			print '  <td align="center"><font size="2">' + tok + '</font></td>'
			print '  <td bgcolor=#' + rowcols3[rowcolindex3] + '>'
			print '      <table border="0" cellpadding="5" bgcolor=#' + rowcols3[rowcolindex3] + '><tr><td>'
			print "         <font size='2'>" + pkglist + "</font>"
			print "      </td></tr></table>"
			print "  </td>"
			print "</tr>"
			rowcolindex3 = 1 - rowcolindex3
		else:
			print(tok + "\t" + pkglist)


def print_altered_packages(pkgs, are_updated):

	global rowcolindex3

	if len(pkgs) > 0:
		print big_line_sep
		if are_updated:
			tok = "updated packages:"
		else:
			tok = "rolled-back packages:"

		if opts.html:
			print '<tr><td align="center"><font size="2">' + tok + '</font></td><td>'
			print '<table border="0">'
			rowcolindex = 0
		else:
			print tok

		for pkg in pkgs:
			print small_line_sep
			if opts.html:
				print '<tr><td bgcolor=#' + rowcols3[rowcolindex3] + '>'
				print '<table cellspacing="5" border="0"><tr><td align="center"><font size=2>'
				rowcolindex3 = 1 - rowcolindex3

			path = pkg[1].rsplit("/",1)[0]
			fam = pkg[0]
			oldverstr = pkg[1].rsplit("/",1)[-1]
			newverstr = pkg[2].rsplit("/",1)[-1]
			oldver = dc.Version(oldverstr)
			newver = dc.Version(newverstr)

			if are_updated:
				print fam + br + " [" + str(oldver) + " -> " + str(newver) + "]"
			else:
				print fam + br + " [" + str(newver) + " -> " + str(oldver) + "]"

			if opts.html:
				print '</font></td></tr></table></td><td width="100%"><table border="0" bgcolor=#' + \
					table_bgcolor + ' cellpadding="0" cellspacing="1" width="100%">'

			# list all changelogs between versions
			pkgpath = dc.get_base_path(fam + "-" + str(newver))
			currver = dc.Version(pkgpath.rsplit("/",1)[-1])

			while currver > oldver:

				if opts.html:
					rowcolindex = 1 - rowcolindex
					print '<tr bgcolor=#' + rowcols[rowcolindex] + \
						'><td align="center" width="5%"><font size=2>&nbsp;' + str(currver) + "&nbsp;</font></td><td>"
				else:
					print "\n" + fam + "-" + str(currver) + ":"

				chlogpath = pkgpath + "/.metadata/changelog.txt"
				if os.path.isfile(chlogpath):
					f = open(chlogpath)
					chlog = '\t' + f.read().strip().replace('\n', '\n\t')
					if opts.html:
						lines = chlog.split('\n')
						lines2 = []
						prev_row = False
						rowcolindex2 = 0
						td_cols = rowcols2[rowcolindex]

						for l in lines:
							l2 = l.strip()
							if len(l2) > 0:
								if l2.find("-----------------") == -1:
									if l2.find("Changelog since rev") == 0:
										l2 = "<tr><td bgcolor=#" + td_cols[rowcolindex2] + \
											"><font size=1>" + l2 + "</font></td></tr>"
									else:
										is_rev_line = False
										if l2[0] == 'r':
											toks = l2.split(' ')
											if ((toks[-1] == "lines") or (toks[-1] == "line")) and ("|" in toks):
												l2 = "<tr><td bgcolor=#" + td_cols[rowcolindex2] + "><font size=2><i>" + l2 + "</i>"
												rowcolindex2 = 1 - rowcolindex2
												if prev_row:
													l2 = "</font></td></tr>" + l2
												prev_row = True
												is_rev_line = True
										if not is_rev_line:
											l2 = "<br>" + l2

									lines2.append(l2)

						chlog = str('\n').join(lines2)
						chlog = '<table border="0" cellpadding="5" cellspacing="1" width="100%">' + chlog + '</table>'

					f.close()
					print chlog
				else:
					if opts.html:
						print '<table cellspacing="1"><tr><td><font size=2>&nbsp;'
					print "\tno changelog available."
					if opts.html:
						print "</td></tr></table></font>"

				if opts.html:
					print "</td></tr>"

				pkgpath = dc.get_base_path(fam + "-0+<" + str(currver))
				currver = dc.Version(pkgpath.rsplit("/",1)[-1])

			if opts.html:
				print "</table></td></tr>"
				print "<tr><td></td><td></td></tr>"

		if opts.html:
			print "</table></td></tr>"


if opts.html:
	print '<font face="Arial">'
	print '<table border="0" cellpadding="0" bgcolor=#' + table_bgcolor2 + '>'

print_added_packages(removed_pkgs, False)
print_added_packages(added_pkgs, True)
print_altered_packages(updated_pkgs, True)
print_altered_packages(rolledback_pkgs, False)

print big_line_sep

if opts.html:
	print "</table></font>"

























#    Copyright 2008-2012 Dr D Studios Pty Limited (ACN 127 184 954) (Dr. D Studios)
#
#    This file is part of Rez.
#
#    Rez is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Lesser General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
#
#    Rez is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU Lesser General Public License
#    along with Rez.  If not, see <http://www.gnu.org/licenses/>.

########NEW FILE########
__FILENAME__ = rez-dot_
#!!REZ_PYTHON_BINARY!

#
# Thin wrapper over pydot, so dot-files can be displayed from the command line
#

import os
import sys
import optparse
import pydot
import subprocess
import tempfile


#########################################################################################
# command-line
#########################################################################################

usage = "usage: %prog [options] dot-file"
p = optparse.OptionParser(usage=usage)

default_viewer = os.getenv("REZ_DOT_IMAGE_VIEWER", "xnview")

p.add_option("-v", "--viewer", dest="viewer", type="string", default=default_viewer, \
	help="app to view image with [default = "+default_viewer+"]")
p.add_option("-q", "--quiet", dest="quiet", action="store_true", default=False, \
	help="suppress unnecessary output [default = %default]")
p.add_option("-c", "--conflict-only", dest="conflict_only", action="store_true", default=False, \
	help="only display nodes associated with a conflict [default = %default]")
p.add_option("-p", "--package", dest="package", type="string", default="", \
	help="only display nodes dependent (directly or indirectly) on the given package.")
p.add_option("-r", "--ratio", dest="ratio", type="float", default=-1, \
	help="image height / image width")
p.add_option("-f", "--filename", dest="filename", type="string", \
	help="write out the image to file and exit (won't delete it)")

if (len(sys.argv) == 1):
	(opts, extraArgs) = p.parse_args(["-h"])
	sys.exit(0)

(opts, dotfile) = p.parse_args()
if len(dotfile) != 1:
	p.error("Expected a single dot-file")
dotfile = dotfile[0]


if not os.path.isfile(dotfile):
	sys.stderr.write("File does not exist.\n")
	sys.exit(1)


#########################################################################################
# strip out all nodes not associated with a conflict / associated with a particular pkg
#########################################################################################

g = None

if (opts.conflict_only) or (opts.package != ""):

	oldg = pydot.graph_from_dot_file(dotfile)

	# group graph edges by dest pkg, and find 'seed' pkg(s)
	edges = {}
	seed_pkgs = set()
	opt_pkg_exists_as_source = False

	oldedges = oldg.get_edge_list()
	for e in oldedges:
		pkgsrc = e.get_source().replace('"','')
		pkgdest = e.get_destination()

		if pkgdest in edges:
			edges[pkgdest].add(e)
		else:
			s = set()
			s.add(e)
			edges[pkgdest] = s

		if opts.conflict_only and \
			"label" in e.get_attributes() and \
			e.get_attributes()["label"] == "CONFLICT":
			seed_pkgs.add(pkgdest)
		elif opts.package != "":
			pkgdest_ = pkgdest.replace('"','')
			if pkgdest_.startswith(opts.package):
				seed_pkgs.add(pkgdest)
			if pkgsrc.startswith(opts.package):
				opt_pkg_exists_as_source = True

	# extract all edges dependent (directly or not) on seed pkgs
	newg = pydot.Dot()
	consumed_edges = set()

	if len(seed_pkgs) > 0:
		while True:
			new_seed_pkgs = set()
			for seed_pkg in seed_pkgs:
				seed_edges = edges.get(seed_pkg)
				if seed_edges:
					for seededge in seed_edges:
						attribs = seededge.get_attributes()
						if "lp" in attribs:
							del attribs["lp"]
						if "pos" in attribs:
							del attribs["pos"]

						if seededge not in consumed_edges:
							newg.add_edge(seededge)
							consumed_edges.add(seededge)
						new_seed_pkgs.add(seededge.get_source())

			if len(new_seed_pkgs) == 0:
				break
			seed_pkgs = new_seed_pkgs

	if len(newg.get_edge_list()) > 0:
		g = newg
	elif opt_pkg_exists_as_source:
		# pkg was directly in the request list
		e = pydot.Edge("DIRECT REQUEST", opts.package)
		newg.add_edge(e)
		g = newg


#########################################################################################
# generate dot image
#########################################################################################

if opts.filename:
	imgfile = opts.filename
else:
	tmpf = tempfile.mkstemp(suffix='.jpg')
	os.close(tmpf[0])
	imgfile = tmpf[1]

if not opts.quiet:
	print "reading dot file..."
	sys.stdout.flush()

if not g:
	g = pydot.graph_from_dot_file(dotfile)


if opts.ratio > 0:
	g.set_ratio(str(opts.ratio))

if not opts.quiet:
	print "rendering image to " + imgfile + "..."
	sys.stdout.flush()

g.write_jpg(imgfile)


#########################################################################################
# view it then delete it or just exit if we're saving to a file
#########################################################################################

if not opts.filename:
	if not opts.quiet:
		print "loading viewer..."
	proc = subprocess.Popen(opts.viewer + " " + imgfile, shell=True)
	proc.wait()

	if proc.returncode != 0:
		subprocess.Popen("firefox " + imgfile, shell=True).wait()

	os.remove(imgfile)











#    Copyright 2008-2012 Dr D Studios Pty Limited (ACN 127 184 954) (Dr. D Studios)
#
#    This file is part of Rez.
#
#    Rez is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Lesser General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
#
#    Rez is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU Lesser General Public License
#    along with Rez.  If not, see <http://www.gnu.org/licenses/>.

########NEW FILE########
__FILENAME__ = rez-egg-install_
#!!REZ_PYTHON_BINARY!

#
# Install a python egg as a Rez package!
#

import optparse
import sys
import os
import re
import stat
import yaml
import time
import os.path
import shutil
import tempfile
import subprocess as sp


_g_r_stat = stat.S_IRUSR|stat.S_IRGRP|stat.S_IROTH
_g_x_stat = stat.S_IXUSR|stat.S_IXGRP|stat.S_IXOTH

_g_rez_egg_api_version  = 0
_g_rez_path             = os.getenv("REZ_PATH", "UNKNOWN_REZ_PATH")
_g_pkginfo_key_re       = re.compile("^[A-Z][a-z_-]+:")
_g_yaml_prettify_re     = re.compile("^([^: \\n]+):", re.MULTILINE)


# this is because rez doesn't have alphanumeric version support. It will have though, when
# ported to Certus. Just not yet. :(
def _convert_version(txt):
    txt = txt.lower()
    txt = txt.replace('alpha','a')
    txt = txt.replace('beta','b')
    txt = txt.replace("python",'p')
    txt = txt.replace("py",'p')    
    ver = ''

    for ch in txt:
        if ch>='0' and ch<='9':
            ver += ch
        elif ch>='a' and ch<='z':
            ver += ".%s." % ch
        elif ch=='.' or ch=='-':
            ver += '.'
        elif ch=='_':
            pass
        else:
            ver += ".%d." % ord(ch)

    ver = ver.replace("..",".")
    ver = ver.strip('.')
    return ver


def _convert_pkg_name(name, pkg_remappings):
    name2 = pkg_remappings.get(name)
    if name2:
        name = _convert_pkg_name(name2, {})
    return name.replace('-','_')


def _convert_requirement(req, pkg_remappings):
    pkg_name = _convert_pkg_name(req.project_name, pkg_remappings)
    if not req.specs:
        return [pkg_name]

    rezreqs = []
    for spec in req.specs:
        op,ver = spec
        rezver = _convert_version(ver)
        if op == "<":
            r = "%s-0+<%s" % (pkg_name, rezver)
            rezreqs.append(r)
        elif op == "<=":
            r = "%s-0+<%s|%s" % (pkg_name, rezver, rezver)
            rezreqs.append(r)
        elif op == "==":
            r = "%s-%s" % (pkg_name, rezver)
            rezreqs.append(r)
        elif op == ">=":
            r = "%s-%s+" % (pkg_name, rezver)
            rezreqs.append(r)
        elif op == ">":
            r1 = "%s-%s+" % (pkg_name, rezver)
            r2 = "!%s-%s" % (pkg_name, rezver)
            rezreqs.append(r1)
            rezreqs.append(r2)
        elif op == "!=":
            r = "!%s-%s" % (pkg_name, rezver)
            rezreqs.append(r)
        else:
            print >> sys.stderr, \
                "Warning: Can't understand op '%s', just depending on unversioned package..." % op
            rezreqs.append(pkg_name)

    return rezreqs


# some pkg-infos appear to be screwed
def _repair_pkg_info(s):
    s2 = ''
    lines = s2.split('\n')
    for line in lines:
        line = line.strip()
        if line.startswith('[') and not line.endswith(']'):
            line += ']'
        s2 += line + '\n'
    return s2


def _convert_metadata(distr):
    meta = {}
    if distr.has_metadata("PKG-INFO"):
        s = distr.get_metadata("PKG-INFO")
        s = _repair_pkg_info(s)
        sections = pkg_r.split_sections(s)
        print sections
        for section in sections:
            entries = section[1]
            for e in entries:
                if _g_pkginfo_key_re.match(e):
                    toks = e.split(':',1)
                    k = toks[0].strip()
                    v = toks[1].strip()
                    meta[k] = v
    return meta



#########################################################################################
# cmdlin
#########################################################################################
usage = "usage: rez-egg-install [options] <package_name> [-- <easy_install args>]\n\n" + \
    "  Rez-egg-install installs Python eggs as Rez packages, using the standard\n" + \
    "  'easy_install' python module installation tool. For example:\n" + \
    "  rez-egg-install pylint\n" + \
    "  If you need to use specific easy_install options, include the second\n" + \
    "  set of args - in this case you need to make sure that <package_name>\n" + \
    "  matches the egg that you're installing, for example:\n" + \
    "  rez-egg-install MyPackage -- http://somewhere/MyPackage-1.0.tgz\n" + \
    "  Rez will install the package into the current release path, set in\n" + \
    "  $REZ_EGG_PACKAGES_PATH, which is currently:\n" + \
    "  " + (os.getenv("REZ_EGG_PACKAGES_PATH") or "UNSET!")

rez_egg_remapping_file = os.getenv("REZ_EGG_MAPPING_FILE") or \
    ("%s/template/egg_remap.yaml" % _g_rez_path)

p = optparse.OptionParser(usage=usage)
p.add_option("--verbose", dest="verbose", action="store_true", default=False, \
    help="print out extra information")
p.add_option("--mapping-file", dest="mapping_file", type="str", default=rez_egg_remapping_file, \
    help="yaml file that remaps package names. Set $REZ_EGG_MAPPING_FILE to change the default " + \
    "[default = %default]")
p.add_option("--force-platform", dest="force_platform", type=str, \
    help="ignore egg platform and force packages (comma-separated). Eg: Linux,x86_64,centos-6.3")
p.add_option("--use-non-eggs", dest="use_non_eggs", default=False, \
    help="allow use of rez packages that already exist, but " + \
        "were not created by rez-egg-install")
p.add_option("--dry-run", dest="dry_run", action="store_true", default=False, \
    help="perform a dry run")
p.add_option("--local", dest="local", action="store_true", default=False, \
    help="install to local packages directory instead")
p.add_option("--no-clean", dest="no_clean", action="store_true", default=False, \
    help="don't delete temporary egg files afterwards")

help_args = set(["--help","-help","-h","--h"]) & set(sys.argv)
if help_args:
    p.parse_args()

rez_args = None
easy_install_args = None

if "--" in sys.argv:
    i = sys.argv.index("--")
    rez_args = sys.argv[1:i]
    easy_install_args = sys.argv[i+1:]
else:
    rez_args = sys.argv[1:]

(opts, args) = p.parse_args(rez_args)
if len(args) != 1:
    p.error("Expected package name")

pkg_name = args[0]

if not easy_install_args:
    easy_install_args = [pkg_name]

install_evar = "REZ_EGG_PACKAGES_PATH"
if opts.local:
    install_evar = "REZ_LOCAL_PACKAGES_PATH"

install_path = os.getenv(install_evar)
if not install_path:
    print >> sys.stderr, "Expected $%s to be set." % install_evar
    sys.exit(1)


remappings = {}
if opts.mapping_file:
    with open(opts.mapping_file, 'r') as f:
        s = f.read()
    remappings = yaml.load(s)
package_remappings = remappings.get("package_mappings") or {}

platre = remappings.get("platform_mappings") or {}
platform_remappings = {}
for k,v in platre.iteritems():
    platform_remappings[k.lower()] = v

safe_pkg_name = _convert_pkg_name(pkg_name, package_remappings)


#########################################################################################
# run easy_install
#########################################################################################

# find easy_install
proc = sp.Popen("which easy_install", shell=True, stdout=sp.PIPE, stderr=sp.PIPE)
proc.communicate()
if proc.returncode:
    print >> sys.stderr, "could not find easy_install."
    sys.exit(1)

# install the egg to a temp dir
eggs_path = tempfile.mkdtemp(prefix="rez-egg-download-")
print "INSTALLING EGG FOR PACKAGE '%s' TO %s..." % (pkg_name, eggs_path)

def _clean():
    if not opts.no_clean:
        print
        print "DELETING %s..." % eggs_path
        shutil.rmtree(eggs_path)

cmd = "export PYTHONPATH=$PYTHONPATH:%s" % eggs_path
cmd += " ; easy_install --always-copy --install-dir=%s %s" % \
    (eggs_path, str(' ').join(easy_install_args))

print "Running: %s" % cmd
proc = sp.Popen(cmd, shell=True)
proc.wait()
if proc.returncode:
    _clean()
    print
    print >> sys.stderr, "A problem occurred running easy_install, the command was:\n%s" % cmd
    sys.exit(proc.returncode)



#########################################################################################
# extract info from eggs
#########################################################################################

# find tools, if any
eggs_tools = set()
names = os.listdir(eggs_path)
for name in names:
    fpath = os.path.join(eggs_path, name)
    if not os.path.isfile(fpath):
        continue
    m = os.stat(fpath).st_mode
    if m & _g_x_stat:
        eggs_tools.add(name)

# add eggs to python path
sys.path = [eggs_path] + sys.path
try:
    import pkg_resources as pkg_r
except ImportError:
    print >> sys.stderr, "couldn't import pkg_resources. You probably need to install " + \
        "the python setuptools package, you can get it at http://pypi.python.org/pypi/setuptools."
    sys.exit(1)

distrs = pkg_r.find_distributions(eggs_path)
eggs = {}

# iterate over eggs
for distr in distrs:
    print
    print "EXTRACTING DATA FROM %s..." % distr.location

    name = _convert_pkg_name(distr.project_name, package_remappings)
    ver = _convert_version(distr.version)
    pyver = _convert_version(distr.py_version)

    d = {
        "config_version":   0,
        "name":             name,
        "unsafe_name":      distr.project_name,
        "version":          ver,
        "unsafe_version":   distr.version,
        "requires":         ["python-%s+" % pyver]
    }

    pkg_d = _convert_metadata(distr)
    d["EGG-INFO"] = pkg_d
    
    v = pkg_d.get("Summary")
    v2 = pkg_d.get("Description")
    if v:
        d["description"] = v
    elif v2:
        d["description"] = v2

    v = pkg_d.get("Author")
    if v:
        d["author"] = v

    v = pkg_d.get("Home-page")
    if v:
        d["help"] = "$BROWSER %s" % v

    reqs = distr.requires()
    for req in reqs:
        rezreqs = _convert_requirement(req, package_remappings)
        d["requires"] += rezreqs

    if opts.force_platform is None:
        v = pkg_d.get("Platform")
        if v:
            platform_pkgs = platform_remappings.get(v.lower())
            if platform_pkgs is None:
                print >> sys.stderr, ("No remappings are present for the platform '%s'. " + \
                    "Please use the --mapping-file option to provide the remapping, or " + \
                    "use the --force-platform option.") % v
                sys.exit(1)
            else:
                if platform_pkgs:
                    d["variants"] = platform_pkgs
    else:
        toks = opts.force_platform.replace(',',' ').strip().split()
        if toks:
            d["variants"] = toks

    eggs[name] = (distr, d)


# iterate over tools and assign to eggs. There doesn't seem to be consistency in how eggs specify
# their scripts (if at all), so we work it out by looking for the egg name in the script sources.
if eggs and eggs_tools:
    for tool in eggs_tools:
        with open(os.path.join(eggs_path, tool), 'r') as f:
            s = f.read()
        
        count_d = {}
        for egg_name,v in eggs.iteritems():
            distr, d = v
            n = s.count(d["unsafe_name"])
            count_d[n] = egg_name

        counts = count_d.keys()
        counts.sort()
        n = counts[-1]
        script_egg = count_d[n]

        d = eggs[script_egg][1]
        if "tools" not in d:
            d["tools"] = []
        d["tools"].append(tool)


if eggs:
    print
    print "FOUND EGGS: %s" % str(", ").join(eggs.keys())
    if eggs_tools:
        print "FOUND PROGRAMS: %s" % str(", ").join(eggs_tools)



#########################################################################################
# convert eggs to rez packages
#########################################################################################
destdirs = []

def _mkdir(path, make_ro=True):
    if not os.path.exists(path):
        if opts.verbose:
            print "creating %s..." % path
        if not opts.dry_run:
            os.makedirs(path)
            if make_ro:
                destdirs.append(path)

def _cpfile(filepath, destdir, make_ro=True, make_x=False):
    if opts.verbose:
        print "copying %s to %s..." % (filepath, destdir+'/')
    if not opts.dry_run:
        shutil.copy(filepath, destdir)
        if make_ro or make_x:
            st = 0
            if make_ro: st |= _g_r_stat
            if make_x:  st |= _g_x_stat
            destfile = os.path.join(destdir, os.path.basename(filepath))
            os.chmod(destfile, st)


if not opts.use_non_eggs:
    nnoneggs = 0
    for egg_name, v in eggs.iteritems():
        distr, d = v
        pkg_path = os.path.join(install_path, egg_name, d["version"])
        meta_path = os.path.join(pkg_path, ".metadata")    
        rezeggfile = os.path.join(meta_path, "rez_egg_info.txt")

        if os.path.exists(pkg_path) and not os.path.exists(rezeggfile):
            print
            print >> sys.stderr, (("package '%s' already exists, but was not created by " + \
                "rez-egg-install. Use the --use-non-eggs option to skip this error, but note " + \
                "that rez doesn't know if this package is properly configured.") % egg_name)
            nnoneggs += 1
    if nnoneggs:
        sys.exit(1)


added_pkgs = []
updated_pkgs = []
existing_pkgs = []

for egg_name, v in eggs.iteritems():
    print
    print "BUILDING REZ PACKAGE FOR '%s'..." % egg_name

    variants = d.get("variants") or []
    distr, d = v
    egg_path = distr.location
    egg_dir = os.path.basename(egg_path)
    egg_path = os.path.split(egg_path)[0]
    
    pkg_path = os.path.join(install_path, egg_name, d["version"])
    meta_path = os.path.join(pkg_path, ".metadata")    
    variant_path = os.path.join(pkg_path, *(variants))
    bin_path = os.path.join(variant_path, "bin")
    rezeggfile = os.path.join(meta_path, "rez_egg_info.txt")

    if os.path.exists(variant_path):
        print ("skipping installation of '%s', the current variant appears to exist already " + \
            "- %s already exists. Delete this directory to force a reinstall.") % \
            (egg_name, variant_path)
        existing_pkgs.append(egg_name)
        continue

    _mkdir(meta_path, False)
    _mkdir(variant_path, bool(variants))

    # copy files
    for root, dirs, files in os.walk(egg_path):
        subpath = root[len(egg_path):].strip('/')
        dest_root = os.path.join(variant_path, egg_dir, subpath)
        _mkdir(dest_root)

        for name in dirs:
            _mkdir(os.path.join(dest_root, name))

        for name in files:
            if not name.endswith(".pyc"):
                _cpfile(os.path.join(root, name), dest_root)

    tools = d.get("tools")
    if tools:
        _mkdir(bin_path)
        for tool in tools:
            _cpfile(os.path.join(eggs_path, tool), bin_path, make_ro=True, make_x=True)

    for path in reversed(destdirs):
        os.chmod(path, _g_r_stat|_g_x_stat)

    # create/update yaml
    print
    pkg_d = {}
    yaml_path = os.path.join(pkg_path, "package.yaml")
    if os.path.exists(yaml_path):
        print "UPDATING %s..." % yaml_path
        with open(yaml_path, 'r') as f:
            s = f.read()
        pkg_d = yaml.load(s) or {}
        updated_pkgs.append(egg_name)
    else:
        print "CREATING %s..." % yaml_path
        added_pkgs.append(egg_name)

    for k,v in d.iteritems():
        if k == "variants":
            continue
        if k not in pkg_d:
            pkg_d[k] = v

    if variants:
        if "variants" not in pkg_d:
            pkg_d["variants"] = []
        pkg_d["variants"].append(variants)
    
    if "commands" not in pkg_d:
        pkg_d["commands"] = []

    cmd = "export PYTHONPATH=$PYTHONPATH:!ROOT!/%s" % egg_dir
    if cmd not in pkg_d["commands"]:
        pkg_d["commands"].append(cmd)

    if tools:
        cmd = "export PATH=$PATH:!ROOT!/bin"
        if cmd not in pkg_d["commands"]:
            pkg_d["commands"].append(cmd)        

    s = yaml.dump(pkg_d, default_flow_style=False)
    pretty_s = re.sub(_g_yaml_prettify_re, "\\n\\1:", s).strip() + '\n'

    if opts.dry_run:
        print
        print "CONTENTS OF %s WOULD BE:" % yaml_path
        print pretty_s
    else:
        with open(yaml_path, 'w') as f:
            f.write(pretty_s)

        # timestamp
        timefile = os.path.join(meta_path, "release_time.txt")
        if not os.path.exists(timefile):
            with open(timefile, 'w') as f:
                f.write(str(int(time.time())))

        if not os.path.exists(rezeggfile):
            with open(rezeggfile, 'w') as f:
                f.write(str(_g_rez_egg_api_version))

_clean()

print
print "Success! %d packages were installed, %d were updated." % (len(added_pkgs), len(updated_pkgs))
if not opts.dry_run:
    if added_pkgs:
        print "Newly installed packages: %s" % str(", ").join(added_pkgs)
    if updated_pkgs:
        print "Updated packages: %s" % str(", ").join(updated_pkgs)
    if existing_pkgs:
        print "Pre-existing packages: %s" % str(", ").join(existing_pkgs)



#    Copyright 2008-2012 Dr D Studios Pty Limited (ACN 127 184 954) (Dr. D Studios)
#
#    This file is part of Rez.
#
#    Rez is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Lesser General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
#
#    Rez is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU Lesser General Public License
#    along with Rez.  If not, see <http://www.gnu.org/licenses/>.

########NEW FILE########
__FILENAME__ = rez-env-autowrappers_
#!!REZ_PYTHON_BINARY!

#
# rez-env-autowrappers
#
# Like rez-env, but is able to create wrappers on the fly. Rez-env automatically switches to this
# mode if it detects the syntax described below...
# Consider the following invocation of rez-env:
#
# ]$ rez-env (maya mutils-1.4) (houdini-11 hutils-3.2.2 mysops-5)
#
# Each one of the bracketed sections becomes its own subshell. Any package in that subshell that has
# executables listed in a 'tools' section of its package.yaml file, will have those executables
# exposed as 'alias' scripts. For example, after running the above command, running 'maya' would
# actually jump into the first subshell and then execute maya inside of it. Now consider:
#
# ]$ rez-env fx_(maya mfx-4.3) (maya manim-2.2)_anim
#
# Here, one subshell is given a prefix, and another a suffix. After running the above command, we
# would expect the executables "fx_maya" and "maya_anim" to exist. The prefix/suffix is applied to
# all tools found within that subshell.
#
# Each subshell has a name, by default this name is the pre/postfixed version of the first pkg in 
# the shell, so eg 'fx_maya' from above. To set this manually, do this:
#
# ]$ rez-env fx_(mayafx: maya mfx-4.3)
#
# Rez can also take a list of separate requests and 'merge' them together, use the pipe operator to
# do this. Later requests override earlier ones. For example, consider:
#
# rez-env (maya foo-1) | (maya foo-2)  # ==> becomes (maya foo-2)
#
# Here, the user was asking for 'foo-1' initially, but this was then overriden to 'foo-2' in the 
# second request. This functionality is provided for two reasons - (a) it's used internally when
# using patching; (b) it can be utilised by rez users, who want to implement their own environment 
# management system, and have a need to create a working environment based on a heirarchical series 
# of overriding config files.
#
# Lastly, the '^' operator can be used to *remove* packages from the request, eg:
#
# rez-env (maya foo-1) | (maya ^foo)  # ==> becomes (maya)
#

import os
import stat
import os.path
import sys
import shutil
import subprocess
import tempfile
import pyparsing as pp
import rez_env_cmdlin as rec
import rez_parse_request as rpr

_g_alias_context_filename = os.getenv('REZ_PATH') + '/template/wrapper.sh'
_g_context_filename     = 'package.context'
_g_packages_filename    = 'packages.txt'
_g_dot_filename         = _g_context_filename + '.dot'
_g_tools_filename       = _g_context_filename + '.tools'


# main
if __name__ == '__main__':

    # parse args
    p = rec.get_cmdlin_parser()

    (opts, args) = p.parse_args(sys.argv[2:])
    pkgs_str = str(' ').join(args).strip()
    if not pkgs_str:
        p.parse_args(['-h'])
        sys.exit(1)

    if opts.no_local:
        localpath = os.getenv("REZ_LOCAL_PACKAGES_PATH").strip()
        if localpath:
            pkgpaths = os.getenv("REZ_PACKAGES_PATH","").strip().split(':')
            if localpath in pkgpaths:
                pkgpaths.remove(localpath)
                os.environ["REZ_PACKAGES_PATH"] = str(':').join(pkgpaths)

    import rez_config as rc

    base_pkgs, subshells = rpr.parse_request(pkgs_str)
    all_pkgs = base_pkgs[:]

    tmpdir = sys.argv[1]
    if not opts.quiet and not opts.stdin:
        print 'Building into ' + tmpdir + '...'

    # make a copy of rcfile, if specified. We need to propogate this into the subshells
    rcfile_copy = None
    if opts.rcfile and opts.prop_rcfile and os.path.isfile(opts.rcfile):
        rcfile_copy = os.path.join(tmpdir, "rcfile.sh")
        shutil.copy(opts.rcfile, rcfile_copy)

    with open(_g_alias_context_filename, 'r') as f:
        wrapper_template_src = f.read()

    # create the local subshell packages
    for name,d in subshells.iteritems():
        s = name
        if d['prefix']:     s += '(prefix:' + d['prefix'] + ')'
        if d['suffix']:     s += '(suffix:' + d['suffix'] + ')'
        if not opts.stdin:
            print "Building subshell: " + s + ': ' + str(' ').join(d['pkgs'])

        pkgname = '__wrapper_' + name
        pkgdir = os.path.join(tmpdir, pkgname)
        os.mkdir(pkgdir)
        all_pkgs.append(pkgname)

        # do the resolve, creates the context and dot files
        contextfile = os.path.join(pkgdir, _g_context_filename)
        dotfile = os.path.join(pkgdir, _g_dot_filename)

        resolver = rc.Resolver(rc.RESOLVE_MODE_LATEST, quiet=opts.quiet, time_epoch=opts.time, \
            build_requires=opts.build, assume_dt=not opts.no_assume_dt, caching=not opts.no_cache)

        result = resolver.guarded_resolve(d['pkgs'], no_os=opts.no_os, is_wrapper=True, \
            meta_vars=["tools"], shallow_meta_vars=["tools"], dot_file=dotfile)

        if not result:
            sys.exit(1)

        commands = result[1]
        commands.append("export REZ_CONTEXT_FILE=%s" % contextfile)

        f = open(contextfile, 'w')
        f.write(str('\n').join(commands))
        f.close()

        # extract the tools from the context file, create the alias scripts
        tools = []
        f = open(contextfile, 'r')
        lines = f.read().strip().split('\n')
        for l in lines:
            if l.startswith("export REZ_META_SHALLOW_TOOLS="):
                toks = l.strip().split("'")[1].split()
                for tok in toks:
                    toks2 = tok.split(':')
                    aliases = toks2[1].split(',')
                    tools.extend(aliases)
                break

        for tool in tools:
            alias = d["prefix"] + tool + d["suffix"]
            aliasfile = os.path.join(pkgdir, alias)
            if os.path.exists(aliasfile):
                continue # early bird wins

            src = wrapper_template_src.replace("#CONTEXT#", _g_context_filename)
            src = src.replace("#CONTEXTNAME#", name)
            src = src.replace("#ALIAS#", tool)

            if rcfile_copy:
                src = src.replace("#RCFILE#", "../rcfile.sh")                
            
            f = open(aliasfile, 'w')
            f.write(src)
            f.close()
            os.chmod(aliasfile, stat.S_IXUSR|stat.S_IXGRP|stat.S_IRUSR|stat.S_IRGRP)

        # create the package.yaml
        f = open(os.path.join(pkgdir, 'package.yaml'), 'w')
        f.write( \
            'config_version : 0\n' \
            'name: ' + pkgname + '\n' \
            'commands:\n' \
            '- export PATH=$PATH:!ROOT!\n' \
            '- export REZ_WRAPPER_PATH=$REZ_WRAPPER_PATH:!ROOT!\n')

        if tools:
            f.write("tools:\n")
            for tool in tools:
                alias = d["prefix"] + tool + d["suffix"]
                f.write("- %s\n" % alias)
        f.close()

    fpath = os.path.join(tmpdir, _g_packages_filename)
    f = open(fpath, 'w')
    f.write(str(' ').join(all_pkgs))
    f.close()



#    Copyright 2012 Allan Johns
#
#    This file is part of Rez.
#
#    Rez is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Lesser General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
#
#    Rez is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU Lesser General Public License
#    along with Rez.  If not, see <http://www.gnu.org/licenses/>.





















########NEW FILE########
__FILENAME__ = rez-help_
#!!REZ_PYTHON_BINARY!

import os
import os.path
import sys
import yaml
import optparse
import subprocess
import rez_config as dc
import sigint

suppress_notfound_err = False

def get_help(pkg):

	global suppress_notfound_err

	try:
		pkg_base_path = dc.get_base_path(pkg)
	except Exception:
		if not suppress_notfound_err:
			sys.stderr.write("Package not found: '" + pkg + "'\n")
		sys.exit(1)

	yaml_file = pkg_base_path + "/package.yaml"
	try:
		metadict = yaml.load(open(yaml_file).read())
	except Exception:
		return (pkg_base_path, pkg_base_path, None)

	pkg_path = pkg_base_path
	if "variants" in metadict:
		# just pick first variant, they should all have the same copy of docs...
		v0 = metadict["variants"][0]
		pkg_path = os.path.join(pkg_path, *v0)

	return (pkg_base_path, pkg_path, metadict.get("help"), metadict.get("description"))



##########################################################################################
# parse arguments
##########################################################################################

usage = "usage: rez-help [options] [section] package"
p = optparse.OptionParser(usage=usage)

p.add_option("-m", "--manual", dest="manual", action="store_true", default=False, \
	help="Load the rez technical user manual [default = %default]")
p.add_option("-e", "--entries", dest="entries", action="store_true", default=False, \
	help="Just print each help entry [default = %default]")

if (len(sys.argv) == 1):
	(opts, args) = p.parse_args(["-h"])
	sys.exit(0)

(opts, args) = p.parse_args()

if opts.manual:
	subprocess.Popen("kpdf "+os.environ["REZ_PATH"]+"/docs/technicalUserManual.pdf &", \
		shell=True).communicate()
	sys.exit(0)

section = 0

if len(args) == 1:
	pkg = args[0]
elif len(args) == 2:
	pkg = args[1]
	try:
		section = int(args[0])
	except Exception:
		pass
	if section < 1:
		p.error("invalid section '" + args[0] + "': must be a number >= 1")
else:
	p.error("incorrect number of arguments")


##########################################################################################
# find pkg and load help metadata
##########################################################################################

descr_printed = False
def _print_descr(descr):
	global descr_printed
	if descr and not descr_printed:
		print
		print "Description:"
		print descr.strip()
		print
		descr_printed = True

# attempt to load the latest
fam = pkg.split("=")[0].split("-",1)[0]
base_pkgpath, pkgpath, help, descr = get_help(pkg)
_print_descr(descr)
suppress_notfound_err = True

while not help:
	sys.stderr.write("Help not found in " + pkgpath + '\n')
	ver = pkgpath.rsplit('/')[-1]
	base_pkgpath, pkgpath, help, descr = get_help(fam + "-0+<" + ver)
	_print_descr(descr)

print "help found for " + pkgpath


##########################################################################################
# determine help command
##########################################################################################

cmds = []

if type(help) == type(''):
	cmds.append(["", help])
elif type(help) == type([]):
	for entry in help:
		if (type(entry) == type([])) and (len(entry) == 2) \
			and (type(entry[0]) == type('')) and (type(entry[1]) == type('')):
			cmds.append(entry)

if len(cmds) == 0:
	print "Malformed help info in '" + yaml_file + "'"
	sys.exit(1)

if section > len(cmds):
	print "Help for " + pkg + " has no section " + str(section)
	section = 0

if (len(cmds) == 1) and opts.entries:
	print "  1: help"
	sys.exit(0)

if section == 0:
	section = 1
 	if len(cmds) > 1:
 		if not opts.entries:
			print "sections:"
		sec = 1
		for entry in help:
			print "  " + str(sec) + ":\t" + entry[0]
			sec += 1
		sys.exit(0)


##########################################################################################
# run help command
##########################################################################################

cmd = cmds[section-1][1]
cmd = cmd.replace('!ROOT!', pkgpath)
cmd = cmd.replace('!BASE!', base_pkgpath)
cmd += " &"

subprocess.Popen(cmd, shell=True).communicate()





#    Copyright 2008-2012 Dr D Studios Pty Limited (ACN 127 184 954) (Dr. D Studios)
#
#    This file is part of Rez.
#
#    Rez is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Lesser General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
#
#    Rez is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU Lesser General Public License
#    along with Rez.  If not, see <http://www.gnu.org/licenses/>.

########NEW FILE########
__FILENAME__ = rez-info_
#!!REZ_PYTHON_BINARY!

import sys
import yaml
import optparse
import subprocess
import rez_config as dc
import sigint

##########################################################################################
# parse arguments
##########################################################################################

usage = "usage: rez-info package"
p = optparse.OptionParser(usage=usage)

if (len(sys.argv) == 1):
	(opts, args) = p.parse_args(["-h"])
	sys.exit(0)

(opts, args) = p.parse_args()

if len(args) == 1:
	pkg = args[0]
else:
	p.error("incorrect number of arguments")


##########################################################################################
# find pkg and load metadata
##########################################################################################

# attempt to load the latest
fam = pkg.split("=")[0].split("-",1)[0]
try:
	pkg_base_path = dc.get_base_path(pkg)
except Exception:
	sys.stderr.write("Package not found: '" + pkg + "'\n")
	sys.exit(1)

print
print "info @ " + pkg_base_path + ":"


try:
	pkg_info = open(pkg_base_path + "/.metadata/info.txt").readlines()
except Exception:
	pkg_info = None

if(pkg_info):
	yaml_file = pkg_base_path + "/package.yaml"
	try:
		metadict = yaml.load(open(yaml_file).read())
	except Exception:
		print "The package appears to be missing a package.yaml."
		sys.exit(1)

	print

	if "description" in metadict:
		print "Description:"
		print str(metadict["description"]).strip()
		print

	if "authors" in metadict:
		print "Authors:"
		for auth in metadict["authors"]:
			print auth
		print

	print "REPOSITORY URL:"
	svn_url = pkg_info[-1].split()[-1]
	print svn_url
	print

	release_date_secs = int(pkg_info[0].split()[-1])
	now_secs = subprocess.Popen("date +%s", shell=True, stdout=subprocess.PIPE).communicate()[0]
	now_secs = int(now_secs)
	days = (now_secs - release_date_secs) / (3600 * 24)

	print "Days since last release:"
	print days
else:
	yaml_file = pkg_base_path + "/package.yaml"
	try:
		metadict = yaml.load(open(yaml_file).read())
		print "The package appears to be external.\n"
		if "description" in metadict:
			print "Description:"
			print str(metadict["description"]).strip()
			print

	except Exception:
		print "The package was not released with rez-release."



print































#    Copyright 2008-2012 Dr D Studios Pty Limited (ACN 127 184 954) (Dr. D Studios)
#
#    This file is part of Rez.
#
#    Rez is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Lesser General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
#
#    Rez is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU Lesser General Public License
#    along with Rez.  If not, see <http://www.gnu.org/licenses/>.

########NEW FILE########
__FILENAME__ = rez-make-project_
#!!REZ_PYTHON_BINARY!

from optparse import OptionParser
import subprocess as sp
import sys
import os
import os.path
import shutil
import uuid


def _mkdir(dir):
	if not os.path.exists(dir):
		print "making %s..." % dir
		os.mkdir(dir)


bin_cmake_code_template = \
"""
file(GLOB_RECURSE bin_files "bin/*")
rez_install_files(
	${bin_files}
    DESTINATION .
    EXECUTABLE
)
"""


_cmake_templates = {
	"BIN_CMAKE_CODE": \
"""
file(GLOB_RECURSE bin_files "bin/*")
rez_install_files(
    ${bin_files}
    DESTINATION .
    EXECUTABLE
)
""",

	"DOXYGEN_CMAKE_CODE": \
"""
include(RezInstallDoxygen)
file(GLOB_RECURSE doc_files "docs/*")

rez_install_doxygen(
    doc
    FILES %(FILES)s ${doc_files}
    DESTINATION doc
    %(DOXYPY)s

    # remove this once your docs have stabilised, then they will only be built and 
    # installed when you're performing a central install (ie a rez-release).
    FORCE 
)
""",

	"PYTHON_CMAKE_CODE": \
"""
file(GLOB_RECURSE py_files "python/*.py")
rez_install_python(
    py
    FILES ${py_files}
    DESTINATION .
)
"""
}


_project_types = [
	"empty",
	"doxygen",
	"python"
]

_project_template_deps = {
	"empty":	[],
	"doxygen":	["empty"],
	"python":	["doxygen","empty"]
}

_project_requires = {
	"empty":	[],
	"doxygen":	[],
	"python":	["python"]
}

_project_build_requires = {
	"empty":	[],
	"doxygen":	["doxygen"],
	"python":	[]
}



###########################################################################
# cmdlin
###########################################################################

usage = "usage: rez-make-project <name> <version>"
proj_types_str = str(',').join(_project_types)

p = OptionParser(usage=usage)
p.add_option("--type", dest="type", type="string", default="empty", \
    help="Project type - one of [%s]. (default: empty)" % proj_types_str)
p.add_option("--tools", dest="tools", type="string", default="", \
    help="Optional set of programs to create, comma-separated.")

(opts, args) = p.parse_args()

if opts.type not in _project_types:
	p.error("'%s' is not a recognised project type. Choose one of: [%s]" \
		% opts.type, proj_types_str)

if len(args) != 2:
	p.error("Wrong argument count.")

proj_name = args[0]
proj_version = args[1]

cwd = os.getcwd()
proj_types = [opts.type]
proj_types += _project_template_deps[opts.type] or []
browser = os.getenv("BROWSER") or "firefox"



###########################################################################
# query system
###########################################################################

if "doxygen" in proj_types:
	doxygen_support = True
	doxypy_support = True
	doxygen_file_types = []
	string_repl_d = {"DOXYPY": ""}

	p = sp.Popen("rez-which doxygen", shell=True, stdout=sp.PIPE, stderr=sp.PIPE)
	p.communicate()
	if p.returncode != 0:
		_project_build_requires["doxygen"].remove("doxygen")
		doxygen_support = False

	if doxygen_support and "python" in proj_types:
		p = sp.Popen("rez-which doxypy", shell=True, stdout=sp.PIPE, stderr=sp.PIPE)
		p.communicate()
		if p.returncode == 0:
			_project_build_requires["doxygen"].append("doxypy")
			string_repl_d["DOXYPY"] = "DOXYPY"
			doxygen_file_types.append("py_files")
		else:
			print >> sys.stderr, "Skipped doxygen python support, 'doxypy' package not found!"
			doxypy_support = False

	doxy_files_str = str(' ').join([("${%s}" % x) for x in doxygen_file_types])
	string_repl_d["FILES"] = doxy_files_str
	code = _cmake_templates["DOXYGEN_CMAKE_CODE"] % string_repl_d
	_cmake_templates["DOXYGEN_CMAKE_CODE"] = code



###########################################################################
# create files and dirs
###########################################################################

print "creating files and directories for %s project %s-%s..." % \
	(opts.type, proj_name, proj_version)

str_repl = {
	"NAME":						proj_name,
	"VERSION":					proj_version,
	"USER":						os.getenv("USER"),
	"UUID":						str(uuid.uuid4()),
	"REZ_PATH":					os.getenv("REZ_PATH"),
	"BIN_CMAKE_CODE":			'',
	"PYTHON_CMAKE_CODE":		'',
	"DOXYGEN_CMAKE_CODE":		'',
	"COMMANDS":					'',
	"TOOLS":					'',
	"REQUIRES":					'',
	"BUILD_REQUIRES":			'',
	"HELP":						''
}

def _expand(s):
	return s % str_repl

def _expand_path(s):
	s = s.replace("_tokstart_", "%(")
	s = s.replace("_tokend_", ")s")
	return _expand(s)

def _gen_list(label, vals):
	s = ''
	if vals:
		s += label + ":\n"
		for val in vals:
			s += "- %s\n" % val
	return s


requires = []
build_requires = []
commands = []
tools = []

# insert tools
if opts.tools:
	tools = opts.tools.strip().split(',')
	str_repl["TOOLS"] = _gen_list("tools", tools)
	str_repl["BIN_CMAKE_CODE"] = bin_cmake_code_template
	commands.append("export PATH=$PATH:!ROOT!/bin")

# copy and string-replace the templates
for proj_type in proj_types:
	utype = proj_type.upper()

	cmake_code_tok = "%s_CMAKE_CODE" % utype
	cmake_code = _cmake_templates.get(cmake_code_tok)
	if cmake_code:
		str_repl[cmake_code_tok] = cmake_code

	if proj_type == "doxygen":
		str_repl["HELP"] = "help: %s file://!ROOT!/doc/html/index.html" % browser
	elif proj_type == "python":
		commands.append("export PYTHONPATH=$PYTHONPATH:!ROOT!/python")

	requires += _project_requires[proj_type]
	build_requires += _project_build_requires[proj_type]

	str_repl["COMMANDS"] 		= _gen_list("commands", commands)
	str_repl["REQUIRES"] 		= _gen_list("requires", requires)
	str_repl["BUILD_REQUIRES"] 	= _gen_list("build_requires", build_requires)

	template_dir = "%s/template/project_types/%s" % (os.getenv("REZ_PATH"), proj_type)
	if not os.path.exists(template_dir):
		print >> sys.stderr, "Internal error - path %s not found." % template_dir
		sys.exit(1)

	for root, dirs, files in os.walk(template_dir):
		dest_root = _expand_path(root.replace(template_dir, cwd))
		for dir in dirs:
			dest_dir = _expand_path(os.path.join(dest_root, dir))
			_mkdir(dest_dir)

		for file in files:
			fpath = os.path.join(root, file)
			f = open(fpath, 'r')
			s = f.read()
			f.close()
			
			# do string replacement, and remove extraneous blank lines
			s = _expand(s)
			while "\n\n\n" in s:
				s = s.replace("\n\n\n", "\n\n")

			dest_fpath = _expand(os.path.join(dest_root, file))
			print "making %s..." % dest_fpath
			f = open(dest_fpath, 'w')
			f.write(s)
			f.close()


# add programs, if applicable
if tools:
	shebang = '#!/bin/bash'
	if opts.type == "python":
		shebang = "#!/usr/bin/env python"
	_mkdir("./bin")

	for tool in tools:
		path = os.path.join("./bin", tool)
		print "creating %s..." % path
		f = open(path, 'w')
		f.write(shebang + '\n')
		f.close()

########NEW FILE########
__FILENAME__ = rez-merge-requests_
#!!REZ_PYTHON_BINARY!

import sys
import rez_parse_request as rpr


req_str = str(' ').join(sys.argv[1:])
base_pkgs, subshells = rpr.parse_request(req_str)

s = rpr.encode_request(base_pkgs, subshells)
print s

########NEW FILE########
__FILENAME__ = rez-release-git_
#!!REZ_PYTHON_BINARY!

import sys
import optparse
import rez_release_git as rezr
import sigint

#
# command-line
#

p = optparse.OptionParser(usage="Usage: rez-release [options]")
p.add_option("-m", "--message", dest="message", default=None, \
	help="specify commit message, do not prompt user. Repo log will still be appended.")
p.add_option("-n", "--no-message", dest="nomessage", action="store_true", default=False, \
	help="commit with no message. Repo log will still be appended [default = %default].")
p.add_option("-j", "--jobs", dest="jobs", type="int", default=1, \
	help="specifies the number of jobs (commands) to run simultaneously. [default = %default]")
p.add_option("--allow-not-latest", dest="nolatest", action="store_true", default=False, \
	help="allows release of version earlier than the latest release. Do NOT use this option \
unless you have to and you have good reason. [default = %default].")
p.add_option("-t", "--time", dest="time", default="0", \
	help="ignore packages newer than the given epoch time [default = current time]")

(opts, args) = p.parse_args()


#
# release
#

msg = opts.message
if (not msg) and (opts.nomessage):
	msg = ""

rezr.release_from_path(".", msg, opts.jobs, opts.time, opts.nolatest)

#    Copyright 2012 BlackGinger Pty Ltd (Cape Town, South Africa)
#
#    Copyright 2008-2012 Dr D Studios Pty Limited (ACN 127 184 954) (Dr. D Studios)
#
#    This file is part of Rez.
#
#    Rez is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Lesser General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
#
#    Rez is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU Lesser General Public License
#    along with Rez.  If not, see <http://www.gnu.org/licenses/>.

########NEW FILE########
__FILENAME__ = rez-release_
#!!REZ_PYTHON_BINARY!

import sys
import optparse
import rez_release as rezr
import sigint

#
# command-line
#

p = optparse.OptionParser(usage="Usage: rez-release [options]")
p.add_option("-m", "--message", dest="message", default=None, \
	help="specify commit message, do not prompt user. Svn log will still be appended.")
p.add_option("-n", "--no-message", dest="nomessage", action="store_true", default=False, \
	help="commit with no message. Svn log will still be appended [default = %default].")
p.add_option("-j", "--jobs", dest="jobs", type="int", default=1, \
	help="specifies the number of jobs (commands) to run simultaneously. [default = %default]")
p.add_option("--allow-not-latest", dest="nolatest", action="store_true", default=False, \
	help="allows release of version earlier than the latest release. Do NOT use this option \
unless you have to and you have good reason. [default = %default].")
p.add_option("-t", "--time", dest="time", default="0", \
	help="ignore packages newer than the given epoch time [default = current time]")

(opts, args) = p.parse_args()


#
# release
#

msg = opts.message
if (not msg) and (opts.nomessage):
	msg = ""

rezr.release_from_path(".", msg, opts.jobs, opts.time, opts.nolatest)

#    Copyright 2008-2012 Dr D Studios Pty Limited (ACN 127 184 954) (Dr. D Studios)
#
#    This file is part of Rez.
#
#    Rez is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Lesser General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
#
#    Rez is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU Lesser General Public License
#    along with Rez.  If not, see <http://www.gnu.org/licenses/>.

########NEW FILE########
__FILENAME__ = rez-which_
#!!REZ_PYTHON_BINARY!

import sys
import rez_config as rc

pkg = sys.argv[1]

try:
	print rc.get_base_path(pkg)
except Exception:
	print "package not found: '" + pkg + "'"
	sys.exit(1)


#    Copyright 2008-2012 Dr D Studios Pty Limited (ACN 127 184 954) (Dr. D Studios)
#
#    This file is part of Rez.
#
#    Rez is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Lesser General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
#
#    Rez is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU Lesser General Public License
#    along with Rez.  If not, see <http://www.gnu.org/licenses/>.

########NEW FILE########
__FILENAME__ = exclaim

def exclaim():
	print "Hello world(py)!"

########NEW FILE########
__FILENAME__ = env
"""
Simple API to extract information about the current rez-configured environment.
"""

import os
from rez_exceptions import PkgFamilyNotFoundError


class RezError(Exception):
    def __init__(self, value):
        self.value = value
    def __str__(self):
        return str(self.value)


def get_request(as_dict=False, parent_env=False):
    """
    @param as_dict If True, return value is in form { UPPER_PKG_NAME: (pkg-family, pkg-version) }
    @parent_env If true, return the request of the previous (parent) env. This is sometimes useful
        when a wrapped program needs to know information about the calling environment.
    @return the rez package request.
    """
    evar = "REZ_REQUEST"
    if parent_env:
        evar = "REZ_PREV_REQUEST"
    s = _get_rez_env_var(evar)
    pkgs = s.strip().split()
    if as_dict:     return _get_pkg_dict(pkgs)
    else:           return pkgs


def in_wrapper_env():
    """
    @returns True if the current environment is actually a wrapper, false otherwise.
    """
    return os.getenv("REZ_IN_WRAPPER") == "1"


def get_resolve(as_dict=False):
    """
    @param as_dict If True, return value is in form { UPPER_PKG_NAME: (pkg-family, pkg-version) }
    @return the rez package resolve.
    """
    s = _get_rez_env_var("REZ_RESOLVE")
    pkgs = s.strip().split()
    if as_dict:     return _get_pkg_dict(pkgs)
    else:           return pkgs


def get_resolve_timestamp():
    """
    @return the rez resolve timestamp.
    """
    s = _get_rez_env_var("REZ_REQUEST_TIME")
    return int(s)


def get_package_root(package_name):
    """
    @return Install path of the given package.
    """
    evar = "REZ_%s_ROOT" % package_name.upper()
    pkg_root = os.getenv(evar)
    if not pkg_root:
        raise PkgFamilyNotFoundError(package_name)
    return pkg_root


def get_context_path():
    """
    @return Filepath of the context file for the current environment.
    """
    return _get_rez_env_var("REZ_CONTEXT_FILE")


def get_context_dot_path():
    """
    @return Filepath of the context resolve graph dot-file for the current environment.
    """
    return get_context_path() + ".dot"


def _get_rez_env_var(var):
    val = os.getenv(var)
    if val is None:
        raise RezError("Not in a correctly-configured Rez environment")
    return val


def _get_pkg_dict(pkgs):
    d = {}
    for pkg in pkgs:
        toks = pkg.split('-',1)
        fam = toks[0]
        ver = ""
        if len(toks) > 1:
            ver = toks[1]
        d[fam.upper()] = (fam, ver)
    return d

########NEW FILE########
__FILENAME__ = memcached_client
import memcache
import hashlib
import pickle
import sys
import copy


class MemCacheClient():
    """
    Wrapper for memcache.Client class.
    """
    def __init__(self, client, verbose=True):
        self.mc = client
        self.verbose = verbose

    def _get_key(self, k):
        if isinstance(k, basestring) and len(k) < self.mc.server_max_key_length:
            return k.replace(' ','_')
        else:
            return hashlib.sha512(pickle.dumps(k)).hexdigest()

    def _set(self, k, v, fn):
        return fn(self._get_key(k), v, min_compress_len=self.mc.server_max_value_length/2)        

    def set(self, k, v):
        return self._set(k, v, self.mc.set)

    def cas(self, k, v):
        return self._set(k, v, self.mc.cas)

    def add(self, k, v):
        return self._set(k, v, self.mc.add)

    def get(self, k):
        return self.mc.get(self._get_key(k))

    def gets(self, k):
        return self.mc.gets(self._get_key(k))

    def update(self, k, fn, initial):
        """
        Atomic update function.
        """
        assert(initial is not None)
        while True:
            v = self.gets(k)
            if v is None:
                v = fn(copy.deepcopy(initial))
                if self.add(k, v):
                    return
            elif self.cas(k, fn(v)):
                return

    # convenience update functions
    @staticmethod
    def _add_to_set(v, item):
        v.add(item)
        return v

    def update_add_to_set(self, k, item):
        fn = lambda v: MemCacheClient._add_to_set(v, item)
        self.update(k, fn, set())

########NEW FILE########
__FILENAME__ = public_enums
"""
Public enums
"""

REZ_PACKAGES_PATH_ENVVAR = "REZ_PACKAGES_PATH"

PKG_METADATA_FILENAME = "package.yaml"


# Resolve modes, used in resolve_packages()
# If resolution of a package list results in packages with inexact versions, then:
#
# Check the file system - if packages exist within the inexact version range,
# then use the latest to disambiguate
RESOLVE_MODE_LATEST = 	0
# Check the file system - if packages exist within the inexact version range,
# then use the earliest to disambiguate
RESOLVE_MODE_EARLIEST =	1
# don't try and resolve further, and raise an exception
RESOLVE_MODE_NONE = 	2

#    Copyright 2008-2012 Dr D Studios Pty Limited (ACN 127 184 954) (Dr. D Studios)
#
#    This file is part of Rez.
#
#    Rez is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Lesser General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
#
#    Rez is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU Lesser General Public License
#    along with Rez.  If not, see <http://www.gnu.org/licenses/>.

########NEW FILE########
__FILENAME__ = rez_config
"""
rez-config

rez is a tool for managing package configuration.

'package': a unit of software, or configuration information, which is
installed under a common base path, and may be available as several
variants. A specific version of software is regarded as a package - ie,
'boost' is not a package, but 'boost-1.36' is.

'package family': label for a family of versioned packages. 'boost' is a
package family, whereas 'boost-1.36' is a package.

'package base path': The path under which all variants of a package are
installed. For example, boost-1.36 and its variants might be found under
'/server/boost/1.36/'.

NOTES
---------
'Dependency transitivity' is the assumption that if a package A has a dependent
package B, then an earlier versioned A will have a dependency on an equal or
earlier version of B. For example, given the relationship:
A-3.5 dependsOn B-6.4
then we assume that:
A-3.4 dependsOn B-<=6.4

It follows that we also assume that a later version of A will have a dependency
on an equal or later version of B:
A-3.5 dependsOn B-6.4
then we assume that:
A-3.6 dependsOb B->=6.4

Examples of cases where this assumption is wrong are:
let:
A-3.5 dependsOn B-6.4
then the following cases break the assumption:
'A-3.4 dependsOn B-7.0'
'A-3.4 dependsOn B' (since 'B' is the superset of all versions of B)
'A-3.4 NOT dependsOn B'
"""

import os
import time
import yaml
import sys
import random
import subprocess as sp
from versions import *
from public_enums import *
from rez_exceptions import *
from rez_metafile import *
from rez_memcached import *
import rez_filesys
import rez_util



##############################################################################
# Public Classes
##############################################################################

class PackageRequest:
	"""
	A request for a package. 'version' may be inexact (for eg '5.4+'). If mode
	is != NONE then the request will immediately attempt to resolve itself.

	If the package name starts with '!', then this is an ANTI-package request -
	ie, a requirement that this package, in this version range, is not allowed.
	This feature exists so that packages can describe conflicts with other packages,
	that can't be described by conflicting dependencies.

	If the package name starts with '~' then this is a WEAK package request. It
	means, "I don't need this package, but if it exists then it must fall within
	this version range." A weak request is actually converted to a normal anti-
	package: eg, "~foo-1.3" is equivalent to "!foo-0+<1.3|1.4+".
	"""
	def __init__(self, name, version, memcache=None, latest=True):
		self.name = name

		if self.is_weak():
			# convert into an anti-package
			vr = VersionRange(version)
			vr_inv = vr.get_inverse()
			version = str(vr_inv)
			self.name = '!' + self.name[1:]

		if memcache:
			# goto filesystem and resolve version immediately
			name_ = self.name
			if self.is_anti():
				name_ = name[1:]
			found_path, found_ver, found_epoch = memcache.find_package2( \
				rez_filesys._g_syspaths, name_, VersionRange(version), latest)

			if found_ver:
				self.version = str(found_ver)
			else:
				raise PkgsUnresolvedError( [ PackageRequest(name, version) ] )
		else:
			# normalise
			self.version = str(VersionRange(version))

	def is_anti(self):
		return (self.name[0] == '!')

	def is_weak(self):
		return (self.name[0] == '~')

	def short_name(self):
		if (len(self.version) == 0):
			return self.name
		else:
			return self.name + '-' + self.version

	def __str__(self):
		return str((self.name, self.version))


class PackageConflict:
	"""
	A package conflict. This can occur between a package (possibly a specific
	variant) and a package request
	"""
	def __init__(self, pkg_req_conflicting, pkg_req, variant = None ):
		self.pkg_req = pkg_req
		self.pkg_req_conflicting = pkg_req_conflicting
		self.variant = variant

	def __str__(self):
		tmpstr = str(self.pkg_req)
		if self.variant:
			tmpstr += " variant:" + str(self.variant)
		tmpstr += " <--!--> " + str(self.pkg_req_conflicting)
		return tmpstr


class ResolvedPackage:
	"""
	A resolved package
	"""
	def __init__(self, name, version, base, root, commands, metadata, timestamp):
		self.name = name
		self.version = version
		self.base = base
		self.root = root
		self.commands = commands
		self.metadata = metadata # original yaml data
		self.timestamp = timestamp

	def short_name(self):
		if (len(self.version) == 0):
			return self.name
		else:
			return self.name + '-' + str(self.version)

	def strip(self):
		# remove data that we don't want to cache
		self.commands = None

	def __str__(self):
		return str([self.name, self.version, self.root])


class Resolver():
	"""
	Where all the action happens. This class performs a package resolve.
	"""
	def __init__(self, resolve_mode, quiet=False, verbosity=0, max_fails=-1, time_epoch=0, \
		build_requires=False, assume_dt=False, caching=True):
		"""
		resolve_mode: one of: RESOLVE_MODE_EARLIEST, RESOLVE_MODE_LATEST
		quiet: if True then hides unnecessary output (such as the progress dots)
		verbosity: print extra debugging info. One of: 0, 1, 2
		max_fails: return after N failed configuration attempts, default -1 (no limit)
		time_epoch: ignore packages newer than this time-date. Default = 0 which is a special
			case, meaning do not ignore any packages
		assume_dt: Assume dependency transitivity
		caching: If True, resolve info is read from and written to a memcache daemon if possible.
		"""
		if not time_epoch:
			time_epoch = int(time.time())

		self.rctxt = _ResolvingContext()
		self.rctxt.resolve_mode = resolve_mode
		self.rctxt.verbosity = verbosity
		self.rctxt.max_fails = max_fails
		self.rctxt.quiet = quiet
		self.rctxt.build_requires = build_requires
		self.rctxt.assume_dt = assume_dt
		self.rctxt.time_epoch = time_epoch
		self.rctxt.memcache = RezMemCache(time_epoch, caching)

	def get_memcache(self):
		return self.rctxt.memcache

	def guarded_resolve(self, pkg_req_strs, no_os=False, no_path_append=False, is_wrapper=False, \
		meta_vars=None, shallow_meta_vars=None, dot_file=None, print_dot=False):
		"""
		Just a wrapper for resolve() which does some command-line friendly stuff and has some 
		extra options for convenience.
		@return None on failure, same as resolve() otherwise.
		"""
		try:
			pkg_reqs = [str_to_pkg_req(x, self.rctxt.memcache) for x in pkg_req_strs]
			result = self.resolve(pkg_reqs, no_os, no_path_append, is_wrapper, \
				meta_vars, shallow_meta_vars)

		except PkgSystemError, e:
			sys.stderr.write(str(e)+'\n')
			return None
		except VersionError, e:
			sys.stderr.write(str(e)+'\n')
			return None
		except PkgFamilyNotFoundError, e:
			sys.stderr.write("Could not find the package family '" + e.family_name + "'\n")
			return None
		except PkgNotFoundError, e:
			sys.stderr.write("Could not find the package '" + e.pkg_req.short_name() + "'\n")
			return None
		except PkgConflictError, e:
			sys.stderr.write("The following conflicts occurred:\n")
			for c in e.pkg_conflicts:
				sys.stderr.write(str(c)+'\n')

			# we still produce a dot-graph on failure
			if e.last_dot_graph:
				if dot_file:
					rez_util.gen_dotgraph_image(e.last_dot_graph, dot_file)
				if print_dot:
					print(e.last_dot_graph)
			return None
		except PkgsUnresolvedError, e:
			sys.stderr.write("The following packages could not be resolved:\n")
			for p in e.pkg_reqs:
				sys.stderr.write(str(p)+'\n')
			return None
		except PkgCommandError, e:
			sys.stderr.write("There was a problem with the resolved command list:\n")
			sys.stderr.write(str(e)+'\n')
			return None
		except PkgCyclicDependency, e:
			sys.stderr.write("\nCyclic dependency(s) were detected:\n")
			sys.stderr.write(str(e) + "\n")

			# write graphs to file
			tmpf = tempfile.mkstemp(suffix='.dot')
			os.write(tmpf[0], str(e))
			os.close(tmpf[0])
			sys.stderr.write("\nThis graph has been written to:\n")
			sys.stderr.write(tmpf[1] + "\n")

			tmpf = tempfile.mkstemp(suffix='.dot')
			os.write(tmpf[0], e.dot_graph)
			os.close(tmpf[0])
			sys.stderr.write("\nThe whole graph (with cycles highlighted) has been written to:\n")
			sys.stderr.write(tmpf[1] + "\n")

			# we still produce a dot-graph on failure
			if dot_file:
				rez_util.gen_dotgraph_image(e.dot_graph, dot_file)
			if print_dot:
				print(e.dot_graph)

			return None

		except PkgConfigNotResolvedError, e:
			sys.stderr.write("The configuration could not be resolved:\n")
			for p in e.pkg_reqs:
				sys.stderr.write(str(p)+'\n')
			sys.stderr.write("The failed configuration attempts were:\n")
			for s in e.fail_config_list:
				sys.stderr.write(s+'\n')

			# we still produce a dot-graph on failure
			if dot_file:
				rez_util.gen_dotgraph_image(e.last_dot_graph, dot_file)
			if print_dot:
				print(e.last_dot_graph)

			return None

		pkg_res_list, env_cmds, dot_graph, nfails = result

		if print_dot:
			print(dot_graph)

		if dot_file:
			rez_util.gen_dotgraph_image(dot_graph, dot_file)

		return result

	def resolve(self, pkg_reqs, no_os=False, no_path_append=False, is_wrapper=False, \
		meta_vars=None, shallow_meta_vars=None):
		"""
		Perform a package resolve.
		Inputs:
		pkg_reqs: list of packages to resolve into a configuration
		no_os: don't include the OS package.
		no_path_append: don't append OS-specific paths to PATH when printing an environment
		is_wrapper: If this env is being resolved for a wrapper, then some very slight changes
			are needed to a normal env, so that wrappers can see one another.
		meta_vars: A list of strings, where each string is a key whos value will be saved into an
			env-var named REZ_META_<KEY> (lists are comma-separated).
		shallow_meta_vars: Same as meta-vars, but only the values from those packages directly
			requested are baked into the env var REZ_META_SHALLOW_<KEY>.
		@returns
		(a) a list of ResolvedPackage objects, representing the resolved config;
		(b) a list of commands which, when run, should configure the environment;
		(c) a dot-graph representation of the config resolution, as a string;
		(d) the number of failed config attempts before the successful one was found
		-OR-
		raise the relevant exception, if config resolution is not possible
		"""
		if not no_os:
			os_pkg_req = str_to_pkg_req(rez_filesys._g_os_pkg)
			pkg_reqs = [os_pkg_req] + pkg_reqs

		if not pkg_reqs:
			return ([], [], "digraph g{}", 0)

		# get the resolve, possibly read/write cache
		result = self.get_cached_resolve(pkg_reqs)
		if not result:
			result = self.resolve_base(pkg_reqs)
			self.set_cached_resolve(pkg_reqs, result)

		env_cmds = []

		if not is_wrapper:
			env_cmds.append("export REZ_IN_WRAPPER=")
			env_cmds.append("export REZ_WRAPPER_PATH=")

		pkg_res_list, env_cmds_, dot_graph, nfails = result
		env_cmds_ = env_cmds_[:]

		# we need to inject system paths here. They're not there already because they can't be cached
		sys_paths = [os.environ["REZ_PATH"]+"/bin"]
		if not no_path_append:
			sys_paths += rez_filesys._g_os_paths

		sys_paths_added = ("export PATH=" in env_cmds_)
		if sys_paths_added:
			i = env_cmds_.index("export PATH=")
			env_cmds_[i] = "export PATH=%s" % str(':').join(sys_paths)

		env_cmds += env_cmds_

		# add wrapper stuff
		if is_wrapper:
			env_cmds.append("export REZ_IN_WRAPPER=1")
			env_cmds.append("export PATH=$PATH:$REZ_WRAPPER_PATH")

		# add meta env vars
		pkg_req_fam_set = set([x.name for x in pkg_reqs if not x.is_anti()])
		meta_envvars = {}
		shallow_meta_envvars = {}

		for pkg_res in pkg_res_list:
			def _add_meta_vars(mvars, target):
				for key in mvars:
					if key in pkg_res.metadata.metadict:
						val = pkg_res.metadata.metadict[key]
						if type(val) == list:
							val = str(',').join(val)
						if key not in target:
							target[key] = []
						target[key].append(pkg_res.name + ':' + val)

			_add_meta_vars(meta_vars, meta_envvars)

			if shallow_meta_vars and pkg_res.name in pkg_req_fam_set:
				_add_meta_vars(shallow_meta_vars, shallow_meta_envvars)

		for k,v in meta_envvars.iteritems():
			env_cmds.append("export REZ_META_" + k.upper() + "='" + str(' ').join(v) + "'")
		for k,v in shallow_meta_envvars.iteritems():
			env_cmds.append("export REZ_META_SHALLOW_" + k.upper() + "='" + str(' ').join(v) + "'")

		# this here for backwards compatibility
		if not sys_paths_added:
			env_cmds.append("export PATH=$PATH:%s" % str(':').join(sys_paths))

		return pkg_res_list, env_cmds, dot_graph, nfails

	def resolve_base(self, pkg_reqs):
		config = _Configuration(self.rctxt)
		pkg_req_fam_set = set([x.name for x in pkg_reqs if not x.is_anti()])
		full_req_str = str(' ').join([x.short_name() for x in pkg_reqs])

		for pkg_req in pkg_reqs:
			normalise_pkg_req(pkg_req)
			config.add_package(pkg_req)

		for pkg_req in pkg_reqs:
			name = pkg_req.short_name()
			if name.startswith("__wrapper_"):
				name2 = name.replace("__wrapper_", "")
				config.add_dot_graph_verbatim('"' + name +
					'" [label="%s" style="filled" shape=folder fillcolor="rosybrown1"] ;' \
					% (name2))
			else:
				config.add_dot_graph_verbatim('"' + name +
					'" [style=filled shape=box fillcolor="rosybrown1"] ;')

		if (self.rctxt.verbosity != 0):
			print
			print "initial config:"
		if (self.rctxt.verbosity == 1):
			print str(config)
		elif (self.rctxt.verbosity == 2):
			config.dump()

		# do the config resolve - all the action happens here!
		pkg_res_list = config.resolve_packages()

		# color resolved packages in graph
		for pkg_res in pkg_res_list:
			config.add_dot_graph_verbatim('"' + pkg_res.short_name() + \
				'" [style=filled fillcolor="darkseagreen1"] ;')

		if (self.rctxt.verbosity != 0):
			print
			print "final config:"
		if (self.rctxt.verbosity == 1):
			print str(config)
			print
		elif (self.rctxt.verbosity == 2):
			config.dump()
			print

		# build the environment commands
		env_cmds = []
		res_pkg_strs = [x.short_name() for x in pkg_res_list]

		if (self.rctxt.resolve_mode == RESOLVE_MODE_LATEST):
			mode_str = "latest"
		elif (self.rctxt.resolve_mode == RESOLVE_MODE_EARLIEST):
			mode_str = "earliest"
		else:
			mode_str = "none"

		# special case env-vars
		env_cmds.append("export PATH=")
		env_cmds.append("export REZ_USED=" + rez_filesys._g_rez_path)
		env_cmds.append("export REZ_PREV_REQUEST=$REZ_REQUEST")
		env_cmds.append("export REZ_REQUEST='" + full_req_str + "'")
		env_cmds.append("export REZ_RAW_REQUEST='" + full_req_str + "'")
		env_cmds.append("export PYTHONPATH=%s/python" % rez_filesys._g_rez_path)
		env_cmds.append("export REZ_RESOLVE='"+ str(" ").join(res_pkg_strs)+"'")
		env_cmds.append("export REZ_RESOLVE_MODE=" + mode_str)
		env_cmds.append("export REZ_FAILED_ATTEMPTS=" + str(len(self.rctxt.config_fail_list)) )
		env_cmds.append("export REZ_REQUEST_TIME=" + str(self.rctxt.time_epoch))

		# packages: base/root/version, and commands
		env_cmds.append("#### START of package commands ####")

		for pkg_res in pkg_res_list:
			env_cmds.append("# Commands from package %s" % pkg_res.name)

			prefix = "REZ_" + pkg_res.name.upper()
			env_cmds.append("export " + prefix + "_VERSION=" + pkg_res.version)
			env_cmds.append("export " + prefix + "_BASE=" + pkg_res.base)
			env_cmds.append("export " + prefix + "_ROOT=" + pkg_res.root)

			if pkg_res.commands:
				for cmd in pkg_res.commands:
					env_cmds.append([cmd, pkg_res.short_name()])

		env_cmds.append("#### END of package commands ####")

		# process the commands
		env_cmds = process_commands(env_cmds)

		# build the dot-graph representation
		dot_graph = config.get_dot_graph_as_string()

		# here we remove unnecessary data, because if caching is on then it's gonna be sent over
		# the network, and we want to minimise traffic.
		for pkg_res in pkg_res_list:
			pkg_res.strip()

		result = (pkg_res_list, env_cmds, dot_graph, len(self.rctxt.config_fail_list))

		# we're done
		return result

	def set_cached_resolve(self, pkg_reqs, result):
		if not self.rctxt.memcache.mc:
			return

		# if any local packages are involved, don't cache
		pkg_res_list = result[0]
		for pkg_res in pkg_res_list:
			if pkg_res.base.startswith(rez_filesys._g_local_pkgs_path):
				return

		self.rctxt.memcache.store_resolve(rez_filesys._g_syspaths_nolocal, pkg_reqs, result)

	def get_cached_resolve(self, pkg_reqs):
		# the 'cache timestamp' is the most recent timestamp of all the resolved packages. Between
		# here and rctxt.time_epoch, the resolve will be the same.
		if not self.rctxt.memcache.mc:
			return None

		result, cache_timestamp = self.rctxt.memcache.get_resolve( \
			rez_filesys._g_syspaths_nolocal, pkg_reqs)
		
		if not result:
			return None

		pkg_res_list = result[0]

		# discard cache if any version of any resolved pkg is also present as a local pkg,
		# unless the versions fall outside of that pkg's max bounds.
		if rez_filesys._g_local_pkgs_path in rez_filesys._g_syspaths:
			for pkg_res in pkg_res_list:
				fam_path = os.path.join(rez_filesys._g_local_pkgs_path, pkg_res.name)
				if os.path.isdir(fam_path):
					# todo max bounds check
					print_cache_warning(("Presence of local package directory %s " + \
						"caused cache miss") % fam_path)
					return None

		"""
		# if any version of any resolved packages also appear in a local package path, and that 
		# path has been modified since the cache timestamp, then discard the cached resolve.
		# TODO incorrect, time has no effect. Can only discard based on 'pkg max bounds'
		if rez_filesys._g_local_pkgs_path in rez_filesys._g_syspaths:
			for pkg_res in pkg_res_list:
				fam_path = os.path.join(rez_filesys._g_local_pkgs_path, pkg_res.name)
				if os.path.isdir(fam_path):
					path_modtime = int(os.path.getmtime(fam_path))
					if path_modtime >= cache_timestamp:
						print >> sys.stderr, "LOCAL package forced no cache resolve!"
						return None
		"""

		env_cmds = result[1]
		env_cmds.append("export REZ_RESOLVE_FROM_CACHE=1")
		env_cmds.append("export REZ_CACHE_TIMESTAMP=%d" % cache_timestamp)

		return result


##############################################################################
# Public Functions
##############################################################################

def str_to_pkg_req(str_, memcache=None):
	"""
	Helper function: turns a package string (eg 'boost-1.36') into a PackageRequest.
	Note that a version string ending in '=e','=l' will result in a package request
	that immediately resolves to earliest/latest version.
	"""
	latest = True
	memcache2 = None
	if str_.endswith("=l"):
		if not memcache:
			raise Exception("Need memcache to resolve '%s'" % str_)
		memcache2 = memcache
	elif str_.endswith("=e"):
		if not memcache:
			raise Exception("Need memcache to resolve '%s'" % str_)
		latest = False
		memcache2 = memcache

	str_ = str_.split('=')[0]
	strs = str_.split('-', 1)
	dim = len(strs)
	if (dim == 1):
		return PackageRequest(str_, "", memcache2, latest)
	elif (dim == 2):
		return PackageRequest(strs[0], strs[1], memcache2, latest)
	else:
		raise PkgSystemError("Invalid package string '" + str_ + "'")



def get_base_path(pkg_str):
	"""
	NOTE: This is only used by auxilliary tools such as rez-diff, package searches are not
	cached! Use RezMemCache in preference to this function.
	"""
	latest = True
	if pkg_str.endswith("=l"):
		pkg_str = pkg_str[0:-2]
	elif pkg_str.endswith("=e"):
		pkg_str = pkg_str[0:-2]
		latest = False

	pkg_str = pkg_str.rsplit("=",1)[0]
	strs = pkg_str.split('-', 1)
	name = strs[0]
	if len(strs) == 1:
		verrange = ""
	else:
		verrange = strs[1]

	path,ver,pkg_epoch = \
		RezMemCache().find_package2(rez_filesys._g_syspaths, name, VersionRange(verrange), latest)
	if not path:
		raise PkgNotFoundError(pkg_str)

	verstr = str(ver)
	if len(verstr) > 0:
		return path + '/' + verstr
	else:
		return path



def make_random_color_string():
	cols = []
	cols.append(random.randint(0,255))
	cols.append(random.randint(0,255))
	cols.append(random.randint(0,255))
	if(cols[0]+cols[1]+cols[2] > 400):
		cols[random.randint(0,2)] = random.randint(0,100)
	s = "#"
	for c in cols:
		h = hex(c)[2:]
		if len(h) == 1:
			h = '0' + h
		s = s + h
	return s


##############################################################################
# Internal Classes
##############################################################################

class _ResolvingContext:
	"""
	Resolving context
	"""
	def __init__(self):
		self.resolve_mode = RESOLVE_MODE_NONE
		self.verbosity = 0
		self.max_fails = -1
		self.config_fail_list = []
		self.last_fail_dot_graph = None
		self.time_epoch = 0
		self.quiet = False
		self.build_requires = False
		self.assume_dt = False
		self.memcache = None


class _PackageVariant:
	"""
	A package variant. The 'working list' member is a list of dependencies that are
	removed during config resolution - a variant with an empty working_list is fully
	resolved. This class has been written with foward compatibility in mind - currently
	a variant is just a list of dependencies, but it may later become a dict, with
	more info than just dependencies.
	"""
	def __init__(self, metadata_node, _working_list=None):
		self.metadata = metadata_node
		if _working_list is not None:
			self.working_list = _working_list[:]
		elif type(self.metadata) == list:
			self.working_list = self.metadata[:]
		else:
			raise PkgSystemError("malformed variant metadata: " + str(self.metadata))

	def copy(self):
		return _PackageVariant(self.metadata, self.working_list)

	def __str__(self):
		return str(self.metadata)


class _Package:
	"""
	Internal package representation
	"""
	def __init__(self, pkg_req, memcache=None):
		self.is_transitivity = False
		self.has_added_transitivity = False
		if pkg_req:
			self.name = pkg_req.name
			self.version_range = VersionRange(pkg_req.version)
			self.base_path = None
			self.metadata = None
			self.variants = None
			self.root_path = None
			self.timestamp = None

			if not self.is_anti() and memcache and \
				not memcache.package_family_exists(rez_filesys._g_syspaths, self.name):
				raise PkgFamilyNotFoundError(self.name)

	def copy(self, skip_version_range=False):
		p = _Package(None)
		p.is_transitivity = self.is_transitivity
		p.has_added_transitivity = self.has_added_transitivity
		p.name = self.name
		p.base_path = self.base_path
		p.root_path = self.root_path
		p.metadata = self.metadata
		p.timestamp = self.timestamp

		if not skip_version_range:
			p.version_range = self.version_range.copy()

		p.variants = None
		if self.variants is not None:
			p.variants = [x.copy() for x in self.variants]
		return p

	def get_variants(self):
		"""
		Return package variants, if any
		"""
		return self.variants

	def as_package_request(self):
		"""
		Return this package as a package-request
		"""
		return PackageRequest(self.name, str(self.version_range))

	def is_anti(self):
		"""
		Return True if this is an anti-package
		"""
		return (self.name[0] == '!')

	def short_name(self):
		"""
		Return a short string representation, eg 'boost-1.36'
		"""
		if self.version_range.is_any():
			return self.name
		else:
			return self.name + '-' + str(self.version_range)

		return self.name + '-' + str(self.version_range)

	def is_metafile_resolved(self):
		"""
		Return True if this package has had its metafile resolved
		"""
		return (self.base_path != None)

	def is_resolved(self):
		"""
		Return True if this package has been resolved (ie, there are either no
		variants, or a specific variant has been chosen)
		"""
		return (self.root_path != None)

	def resolve(self, root_path):
		"""
		Resolve this package, ie set its root path

		.. todo::
			 optimisation: just do this right at the end of resolve_packages
		"""
		self.root_path = root_path

	# Get commands with string-replacement
	def get_resolved_commands(self):
		"""
		"""
		if self.is_resolved():
			cmds = self.metadata.get_string_replace_commands(str(self.version_range), \
				self.base_path, self.root_path)
			return cmds
		else:
			return None

	def resolve_metafile(self, memcache):
		"""
		attempt to resolve the metafile, the metadata member will be set if
		successful, and True will be returned. If the package has no variants,
		then its root-path is set and this package is regarded as fully-resolved.
		"""
		is_any = self.version_range.is_any()
		if not is_any and self.version_range.is_inexact():
			return False

		if not self.base_path:
			fam_path,ver,pkg_epoch = memcache.find_package2( \
				rez_filesys._g_syspaths, self.name, self.version_range, exact=True)
			if ver is not None:
				base_path = fam_path
				if not is_any:
					base_path = os.path.join(fam_path, str(self.version_range))
				
				metafile = os.path.join(base_path, PKG_METADATA_FILENAME)
				self.timestamp = pkg_epoch
				self.base_path = base_path
				self.metadata = memcache.get_metafile(metafile)
				metafile_variants = self.metadata.get_variants()
				if metafile_variants:
					# convert variants from metafile into _PackageVariants
					self.variants = []
					for metavar in metafile_variants:
						pkg_var = _PackageVariant(metavar)
						self.variants.append(pkg_var)
				else:
					# no variants, we're fully resolved
					self.resolve(self.base_path)

		return (self.base_path != None)

	def __str__(self):
		l = [ self.short_name() ]
		if self.root_path:
			l.append('R' + self.root_path)
		elif self.base_path:
			l.append('B' + self.base_path)
		if(self.is_transitivity):
			l.append('t')

		variants = self.get_variants()
		if (variants):
			vars = []
			for var in variants:
				vars.append(var.working_list)
			l.append("working_vars:" + str(vars))
		return str(l)




class _Configuration:
	"""
	Internal configuration representation
	"""
	s_uid = 0

	def __init__(self, rctxt, inc_uid = False):
		# resolving context
		self.rctxt = rctxt
		# packages map, for quick lookup
		self.pkgs = {}
		# packages list, for order retention wrt resolving
		self.families = []
		# connections in a dot graph
		self.dot_graph = []
		# uid
		if inc_uid:
			_Configuration.s_uid += 1
		self.uid = _Configuration.s_uid

	def get_num_packages(self):
		"""
		return number of packages
		"""
		num = 0
		for name,pkg in self.pkgs.iteritems():
			if not pkg.is_anti():
				num += 1
		return num

	def get_num_resolved_packages(self):
		"""
		return number of resolved packages
		"""
		num = 0
		for name,pkg in self.pkgs.iteritems():
			if pkg.is_resolved():
				num += 1
		return num

	def all_resolved(self):
		"""
		returns True if all packages are resolved
		"""
		return (self.get_num_resolved_packages() == self.get_num_packages())

	ADDPKG_CONFLICT 	= 0
	ADDPKG_ADD 			= 1
	ADDPKG_NOEFFECT		= 2

	def test_pkg_req_add(self, pkg_req, create_pkg_add):
		"""
		test the water to see what adding a package request would do to the config. Possible results are:
		(ADDPKG_CONFLICT, pkg_conflicting):
		The package cannot be added because it would conflict with pkg_conflicting
		(ADDPKG_NOEFFECT, None):
		The package doesn't need to be added, there is an identical package already there
		(ADDPKG_ADD, pkg_add):
		The package can be added, and the config updated accordingly by adding pkg_add (replacing
		a package with the same family name if it already exists in the config)

		.. note::
			that if 'create_pkg_add' is False, then 'pkg_add' will always be None.
		"""

		# do a shortcut and test pkg short-names, if they're identical then we can often
		# return 'NOEFFECT'. Sometimes short names can mismatch, but actually be identical,
		# but this is of no real consequence, and testing on short-name is a good optimisation
		# (testing VersionRanges for equality is not trivial)
		pkg_shortname = pkg_req.short_name()

		pkg_req_ver_range = VersionRange(pkg_req.version)

		if pkg_req.is_anti():

			if pkg_req.name[1:] in self.pkgs:
				config_pkg = self.pkgs[pkg_req.name[1:] ]

				# if anti and existing non-anti don't overlap then no effect
				ver_range_intersect = config_pkg.version_range.get_intersection(pkg_req_ver_range)
				if not ver_range_intersect:
					return (_Configuration.ADDPKG_NOEFFECT, None)

				# if (inverse of anti) and non-anti intersect, then reduce existing non-anti,
				# otherwise there is a conflict
				pkg_req_inv_ver_range = pkg_req_ver_range.get_inverse()
				ver_range_intersect = config_pkg.version_range.get_intersection(pkg_req_inv_ver_range)
				if ver_range_intersect:
					pkg_add = None
					if create_pkg_add:
						pkg_add = config_pkg.copy(True)
						pkg_add.version_range = ver_range_intersect
						return (_Configuration.ADDPKG_ADD, pkg_add)
				else:
					return (_Configuration.ADDPKG_CONFLICT, config_pkg)

			# union with anti if one already exists
			if pkg_req.name in self.pkgs:
				config_pkg = self.pkgs[pkg_req.name]
				if (config_pkg.short_name() == pkg_shortname):
					return (_Configuration.ADDPKG_NOEFFECT, None)

				ver_range_union = config_pkg.version_range.get_union(pkg_req_ver_range)
				pkg_add = None
				if create_pkg_add:
					pkg_add = config_pkg.copy(True)
					pkg_add.version_range = ver_range_union
				return (_Configuration.ADDPKG_ADD, pkg_add)
		else:
			if ('!' + pkg_req.name) in self.pkgs:
				config_pkg = self.pkgs['!' + pkg_req.name]

				# if non-anti and existing anti don't overlap then pkg can be added
				ver_range_intersect = config_pkg.version_range.get_intersection(pkg_req_ver_range)
				if not ver_range_intersect:
					pkg_add = None
					if create_pkg_add:
						pkg_add = _Package(pkg_req, self.rctxt.memcache)
					return (_Configuration.ADDPKG_ADD, pkg_add)

				# if non-anti and (inverse of anti) intersect, then add reduced anti,
				# otherwise there is a conflict
				config_pkg_inv_ver_range = config_pkg.version_range.get_inverse()
				ver_range_intersect = config_pkg_inv_ver_range.get_intersection(pkg_req_ver_range)
				if ver_range_intersect:
					pkg_add = None
					if create_pkg_add:
						pkg_add = _Package(pkg_req, self.rctxt.memcache)
						pkg_add.version_range = ver_range_intersect
						return (_Configuration.ADDPKG_ADD, pkg_add)
				else:
					return (_Configuration.ADDPKG_CONFLICT, config_pkg)

			# intersect with non-anti if one already exists, and conflict if no intersection
			if pkg_req.name in self.pkgs:
				config_pkg = self.pkgs[pkg_req.name]
				if (config_pkg.short_name() == pkg_shortname):
					return (_Configuration.ADDPKG_NOEFFECT, None)

				ver_range_intersect = config_pkg.version_range.get_intersection(pkg_req_ver_range)
				if ver_range_intersect:
					pkg_add = None
					if create_pkg_add:
						pkg_add = config_pkg.copy(True)
						pkg_add.version_range = ver_range_intersect
					return (_Configuration.ADDPKG_ADD, pkg_add)
				else:
					return (_Configuration.ADDPKG_CONFLICT, config_pkg)

		# package can be added directly, doesn't overlap with anything
		pkg_add = None
		if create_pkg_add:
			pkg_add = _Package(pkg_req, self.rctxt.memcache)
		return (_Configuration.ADDPKG_ADD, pkg_add)

	def get_conflicting_package(self, pkg_req):
		"""
		return a package in the current configuration that 'pkg' would conflict with, or
		None if no conflict would occur
		"""
		result, pkg_conflict = self.test_pkg_req_add(pkg_req, False)
		if (result == _Configuration.ADDPKG_CONFLICT):
			return pkg_conflict
		else:
			return None

	PKGCONN_REDUCE 		= 0
	PKGCONN_RESOLVE 	= 1
	PKGCONN_REQUIRES 	= 2
	PKGCONN_CONFLICT	= 3
	PKGCONN_VARIANT		= 4
	PKGCONN_CYCLIC		= 5
	PKGCONN_TRANSITIVE	= 6

	def add_package(self, pkg_req, parent_pkg=None, dot_connection_type=0):
		"""
		add a package request to this configuration, optionally describing the 'parent'
		package (ie the package that requires it), and the type of dot-graph connection,
		if the pkg has a parent pkg.
		"""
		if parent_pkg:
			connt = _Configuration.PKGCONN_REQUIRES
			if dot_connection_type == _Configuration.PKGCONN_TRANSITIVE:
				connt = _Configuration.PKGCONN_TRANSITIVE
				self.add_dot_graph_verbatim('"' + pkg_req.short_name() + \
					'" [ shape=octagon ] ;')

			self.dot_graph.append( ( parent_pkg.short_name(), ( pkg_req.short_name(), connt ) ) )

		# test to see what adding this package would do
		result, pkg = self.test_pkg_req_add(pkg_req, True)

		if (result == _Configuration.ADDPKG_CONFLICT):

			self.dot_graph.append( ( pkg.short_name(), ( pkg_req.short_name(), \
				_Configuration.PKGCONN_CONFLICT ) ) )
			self.rctxt.last_fail_dot_graph = self.get_dot_graph_as_string()

			pkg_conflict = PackageConflict(pkg_to_pkg_req(pkg), pkg_req)
			raise PkgConflictError([ pkg_conflict ], self.rctxt.last_fail_dot_graph)

		elif (result == _Configuration.ADDPKG_ADD) and pkg:

			# update dot-graph
			pkgname = pkg.short_name()
			if pkg.name in self.pkgs:
				connt = dot_connection_type
				if (connt != _Configuration.PKGCONN_RESOLVE):
					connt = _Configuration.PKGCONN_REDUCE

				pkgname_existing = self.pkgs[pkg.name].short_name()
				# if pkg and pkg-existing have same short-name, then a further-reduced package was already
				# in the config (eg, we added 'python' to a config with 'python-2.5')
				if (pkgname_existing == pkgname):
					self.dot_graph.append( ( pkg_req.short_name(), ( pkgname_existing, connt ) ) )
				else:
					self.dot_graph.append( ( pkgname_existing, ( pkgname, connt ) ) )
			self.dot_graph.append( ( pkgname, None ) )

			if dot_connection_type == _Configuration.PKGCONN_TRANSITIVE:
				pkg.is_transitivity = True

			# add pkg, possibly replacing existing pkg. This is to retain order of package addition,
			# since package resolution is sensitive to this
			if (not pkg.is_anti()) and (not (pkg.name in self.pkgs)):
				self.families.append(pkg.name)
			self.pkgs[pkg.name] = pkg

			# if pkg is non-anti then remove its anti from the config, if it's there. Adding a
			# non-anti pkg to the config without a conflict occurring always means we can safely
			# remove the anti pkg, if it exists.
			if not pkg.is_anti():
				if ('!' + pkg.name) in self.pkgs:
					del self.pkgs['!' + pkg.name]


	def get_dot_graph_as_string(self):
		"""
		return a string-representation of the dot-graph. You should be able to
		write this to file, and view it in a dot viewer, such as dotty or graphviz
		"""
		dotstr = "digraph g { \n"
		conns = set()

		for connection in self.dot_graph:
			if type(connection) == type(""):
				verbatim_txt = connection
				dotstr += verbatim_txt + '\n';
			else:
				if connection not in conns:
					if connection[1]:
						dep, conntype = connection[1]
						dotstr += '"' + connection[0] + '" -> "' + dep + '" '
						if(conntype == _Configuration.PKGCONN_REQUIRES):
							col = make_random_color_string()
							conn_style = '[label=needs color="' + col + '" fontcolor="' + col + '"]'
						elif(conntype == _Configuration.PKGCONN_TRANSITIVE):
							col = make_random_color_string()
							conn_style = '[label=willneed color="' + col + '" fontcolor="' + col + '"]'
						elif(conntype == _Configuration.PKGCONN_RESOLVE):
							conn_style = '[label=resolve color="green4" fontcolor="green4" style="bold"]'
						elif(conntype == _Configuration.PKGCONN_REDUCE):
							conn_style = '[label=reduce color="grey30" fontcolor="grey30" style="dashed"]'
						elif(conntype == _Configuration.PKGCONN_VARIANT):
							conn_style = '[label=variant color="grey30" fontcolor="grey30" style="dashed"]'
						elif(conntype == _Configuration.PKGCONN_CYCLIC):
							conn_style = '[label=CYCLE color="red" fontcolor="red" fontsize="30" style="bold"]'
						else:
							conn_style = '[label=CONFLICT color="red" fontcolor="red" fontsize="30" style="bold"]'
						dotstr += conn_style + ' ;\n'
					else:
						dotstr += '"' + connection[0] + '" ;\n'
					conns.add(connection)

		dotstr += "}\n"
		return dotstr

	def add_dot_graph_verbatim(self, txt):
		"""
		add a verbatim string to the dot-graph output
		"""
		self.dot_graph.append(txt)

	def copy(self):
		"""
		return a shallow copy
		"""
		confcopy = _Configuration(self.rctxt)
		confcopy.pkgs = self.pkgs.copy()
		confcopy.families = self.families[:]
		confcopy.dot_graph = self.dot_graph[:]
		return confcopy

	def deep_copy(self):
		confcopy = _Configuration(self.rctxt)
		confcopy.families = self.families[:]
		confcopy.dot_graph = self.dot_graph[:]

		confcopy.pkgs = {}
		for k,v in self.pkgs.iteritems():
			confcopy.pkgs[k] = v.copy()

		return confcopy

	def swap(self, a):
		"""
		swap this config's contents with another
		"""
		self.pkgs, a.pkgs = a.pkgs, self.pkgs
		self.families, a.families = a.families, self.families
		self.dot_graph, a.dot_graph = a.dot_graph, self.dot_graph

	def get_unresolved_packages_as_package_requests(self):
		"""
		return a list of unresolved packages as package requests
		"""
		pkg_reqs = []
		for name,pkg in self.pkgs.iteritems():
			if (not pkg.is_resolved()) and (not pkg.is_anti()):
				pkg_reqs.append(pkg_to_pkg_req(pkg))
		return pkg_reqs

	def get_all_packages_as_package_requests(self):
		"""
		return a list of all packages as package requests
		"""
		pkg_reqs = []
		for name,pkg in self.pkgs.iteritems():
			pkg_reqs.append(pkg_to_pkg_req(pkg))
		return pkg_reqs

	def resolve_packages(self):
		"""
		resolve the current configuration - all the action happens here. On success,
		a resolved package list is returned. This function should only fail via an
		exception - if an infinite loop results then there is a bug somewheres.
		Please note that the returned list order is important. Required packages appear
		first, and requirees later... since a package's commands may refer to env-vars set
		in a required package's commands.
		"""

		while (not self.all_resolved()) and \
		    ((self.rctxt.max_fails == -1) or (len(self.rctxt.config_fail_list) <= self.rctxt.max_fails)):

			# do an initial resolve pass
			self.resolve_packages_no_filesys()
			if self.all_resolved():
				break

			# fail if not all resolved and mode=none
			if (not self.all_resolved()) and (self.rctxt.resolve_mode == RESOLVE_MODE_NONE):
				pkg_reqs = self.get_unresolved_packages_as_package_requests()
				raise PkgsUnresolvedError(pkg_reqs)

			# add transitive dependencies
			self.add_transitive_dependencies()

			# this shouldn't happen here but just in case...
			if self.all_resolved():
				break

			# find first package with unresolved metafile. Note that self.families exists in
			# order to retain package order, because different package order can result
			# in different configuration resolution.
			pkg = None
			for name in self.families:
				pkg_ = self.pkgs[name]
				if not pkg_.is_metafile_resolved():
					pkg = pkg_
					break

			if not pkg:
				# The remaining unresolved packages must have more than one variant each. So
				# find that variant, out of all remaining packages, that is 'least suitable',
				# and remove it. 'least suitable' means that the variant has largest number
				# of packages that do not intersect with anything in the config.
				if (self.rctxt.verbosity != 0):
					print
					print "Ran out of concrete resolution choices, yet unresolved packages still remain:"
					if (self.rctxt.verbosity == 1):
						print str(self)
					elif (self.rctxt.verbosity == 2):
						self.dump()

				self.remove_least_suitable_variant()

			else:

				ver_range_valid = pkg.version_range
				valid_config_found = False

				# attempt to resolve a copy of the current config with this package resolved
				# as closely as possible to desired (eg in mode=latest, start with latest and
				# work down). The first config to resolve represents the most desirable. Note
				# that resolve_packages will be called recursively
				num_version_searches = 0
				while (not (ver_range_valid == None)) and \
		            ((self.rctxt.max_fails == -1) or \
		            	(len(self.rctxt.config_fail_list) <= self.rctxt.max_fails)):

					num_version_searches += 1

					# resolve package to as closely desired as possible
					try:
						pkg_req_ = PackageRequest(pkg.name, str(ver_range_valid), \
							self.rctxt.memcache, self.rctxt.resolve_mode==RESOLVE_MODE_LATEST)
					except PkgsUnresolvedError, e:

						if(num_version_searches == 1):
							# this means that rather than running out of versions of this lib to try, there
							# were never any versions found at all - which means this package doesn't exist
							self.add_dot_graph_verbatim('"' + \
								e.pkg_reqs[0].short_name() + ' NOT FOUND' + \
								'" [style=filled fillcolor="orangered"] ;')
							self.add_dot_graph_verbatim('"' + \
								e.pkg_reqs[0].short_name() + '" -> "' + \
								e.pkg_reqs[0].short_name() + ' NOT FOUND" ;')
							self.rctxt.last_fail_dot_graph = self.get_dot_graph_as_string()

							sys.stderr.write("Warning! Package not found: " + str(e.pkg_reqs[0]) + "\n")
							raise PkgNotFoundError(e.pkg_reqs[0])

						if (self.uid == 0):
							# we're the topmost configuration, and there are no more packages to try -
							# all possible configuration attempts have failed at this point
							break
						else:
							raise e

					pkg_resolve_str = pkg.short_name() + " --> " + pkg_req_.short_name()

					# restrict next package search to one version less desirable
					try:
						if (self.rctxt.resolve_mode == RESOLVE_MODE_LATEST):
							ver_range_valid = ver_range_valid.get_intersection(VersionRange("0+<" + pkg_req_.version))
						else:
							ver_inc = Version(pkg_req_.version).get_inc()
							ver_range_valid = ver_range_valid.get_intersection(VersionRange(str(ver_inc) + '+'))
					except VersionError:
						ver_range_valid = None

					# create config copy, bit of fiddling though cause we want a proper guid
					config2 =_Configuration(self.rctxt, True)
					guid_ = config2.uid

					config2 = self.deep_copy()
					config2.uid = guid_

					if (self.rctxt.verbosity != 0):
						print
						print "SPAWNED NEW CONFIG #" + str(config2.uid) + " FROM PARENT #" + str(self.uid) + \
							" BASED ON FILESYS RESOLUTION: " + pkg_resolve_str

					# attempt to add package to config copy
					try:
						config2.add_package(pkg_req_, None, _Configuration.PKGCONN_RESOLVE)
					except PkgConflictError, e:
						self.rctxt.last_fail_dot_graph = config2.get_dot_graph_as_string()

						if (self.rctxt.verbosity != 0):
							print
							print "CONFIG #" + str(config2.uid) + " FAILED (" + e.__class__.__name__ + "):"
							print str(e)
							print
							print "ROLLING BACK TO CONFIG #" + self.uid
						continue

					if (self.rctxt.verbosity != 0):
						print
						print "config after applying: " + pkg_resolve_str
						if (self.rctxt.verbosity == 1):
							print str(config2)
						elif (self.rctxt.verbosity == 2):
							config2.dump()

					# now fully resolve config copy
					try:
						config2.resolve_packages()
					except ( \
						PkgConfigNotResolvedError, \
						PkgsUnresolvedError, \
						PkgConflictError, \
						PkgNotFoundError, \
						PkgFamilyNotFoundError, \
						PkgSystemError), e:

						# store fail reason into list, unless it's a PkgConfigNotResolvedError - this error just
						# tells us that the sub-config failed because its sub-config failed.
						if (type(e) not in [PkgConfigNotResolvedError, PkgsUnresolvedError]):

							sys.stderr.write("conflict " + str(len(self.rctxt.config_fail_list)) + \
								": " + config2.short_str() + '\n')
							sys.stderr.flush()

							this_fail = "config: (" + str(config2).strip() + "): " + \
								e.__class__.__name__ + ": " + str(e)

							if(self.rctxt.max_fails >= 0):
								if(len(self.rctxt.config_fail_list) <= self.rctxt.max_fails):
									self.rctxt.config_fail_list.append(this_fail)
									if(len(self.rctxt.config_fail_list) > self.rctxt.max_fails):
										self.rctxt.config_fail_list.append( \
											"Maximum configuration failures reached.")
										pkg_reqs_ = self.get_all_packages_as_package_requests()
										raise PkgConfigNotResolvedError(pkg_reqs_, \
											self.rctxt.config_fail_list, self.rctxt.last_fail_dot_graph)
							else:
								self.rctxt.config_fail_list.append(this_fail)

						if (self.rctxt.verbosity != 0):
							print
							print "CONFIG #" + str(config2.uid) + " FAILED (" + e.__class__.__name__ + "):"
							print str(e)
							print
							print "ROLLING BACK TO CONFIG #" + str(self.uid)

						continue

					# if we got here then we have a valid config yay!
					self.swap(config2)
					valid_config_found = True
					break

				if not valid_config_found:
					# we're exhausted the possible versions of this package to try
					fail_msg = "No more versions to be found on filesys: " + pkg.short_name()
					if (self.rctxt.verbosity != 0):
						print
						print fail_msg

					pkg_reqs_ = self.get_all_packages_as_package_requests()
					raise PkgConfigNotResolvedError(pkg_reqs_, \
						self.rctxt.config_fail_list, self.rctxt.last_fail_dot_graph)

		#################################################
		# woohoo, we have a fully resolved configuration!
		#################################################

		# check for cyclic dependencies
		cyclic_deps = self.detect_cyclic_dependencies()
		if len(cyclic_deps) > 0:
			# highlight cycles in the dot-graph
			for pkg1, pkg2 in cyclic_deps:
				self.dot_graph.append( ( pkg1, ( pkg2, _Configuration.PKGCONN_CYCLIC ) ) )

			dot_str = self.get_dot_graph_as_string()
			raise PkgCyclicDependency(cyclic_deps, dot_str)

		# convert packages into a list of package resolutions, forcing them into the correct 
		# order wrt command sourcing
		ordered_fams = self.get_ordered_families()

		pkg_ress = []
		for name in ordered_fams:
			pkg = self.pkgs[name]
			if not pkg.is_anti():
				resolved_cmds = pkg.get_resolved_commands()
				pkg_res = ResolvedPackage(name, str(pkg.version_range), pkg.base_path, \
                    pkg.root_path, resolved_cmds, pkg.metadata, pkg.timestamp)
				pkg_ress.append(pkg_res)

		return pkg_ress

	def _create_family_dependency_tree(self):
		"""
		From the dot-graph, extract a dependency tree containing unversioned pkgs (ie families),
		and a set of all existing families
		"""
		deps = set()
		fams = set()
		for conn in self.dot_graph:
			if (type(conn) != type("")) and \
				(conn[0][0] != '!'):
				fam1 = conn[0].split('-',1)[0]
				fams.add(fam1)
				if (conn[1] != None) and \
					(conn[1][1] == _Configuration.PKGCONN_REQUIRES) and \
					(conn[1][0][0] != '!'):
					fam2 = conn[1][0].split('-',1)[0]
					fams.add(fam2)
					if fam1 != fam2:
						deps.add( (fam1, fam2) )

		return deps, fams

	def get_ordered_families(self):
		"""
		Return the families of all packages in such an order that required packages appear
		before requirees. This means we can properly order package command construction -
		if A requires B, then A's commands might refer to an env-var set in B's commands.
		"""
		fam_list = []
		deps, fams = self._create_family_dependency_tree()

		while len(deps) > 0:
			parents = set()
			children = set()
			for dep in deps:
				parents.add(dep[0])
				children.add(dep[1])

			leaf_fams = children - parents
			if len(leaf_fams) == 0:
				break 	# if we hit this then there are cycle(s) somewhere

			for fam in leaf_fams:
				fam_list.append(fam)

			del_deps = set()
			for dep in deps:
				if dep[1] in leaf_fams:
					del_deps.add(dep)
			deps -= del_deps

			fams -= leaf_fams

		# anything left in the fam set is a topmost node
		for fam in fams:
			fam_list.append(fam)

		return fam_list


	def detect_cyclic_dependencies(self):
		"""
		detect cyclic dependencies, if they exist
		"""
		# extract dependency tree from dot-graph
		deps = self._create_family_dependency_tree()[0]

		# remove leaf nodes
		while len(deps) > 0:
			parents = set()
			children = set()
			for dep in deps:
				parents.add(dep[0])
				children.add(dep[1])

			leaf_fams = children - parents
			if len(leaf_fams) == 0:
				break

			del_deps = set()
			for dep in deps:
				if dep[1] in leaf_fams:
					del_deps.add(dep)
			deps -= del_deps

		# remove topmost nodes
		while len(deps) > 0:
			parents = set()
			children = set()
			for dep in deps:
				parents.add(dep[0])
				children.add(dep[1])

			top_fams = parents - children
			if len(top_fams) == 0:
				break

			del_deps = set()
			for dep in deps:
				if dep[0] in top_fams:
					del_deps.add(dep)
			deps -= del_deps

		# anything left is part of a cyclic loop...

		if len(deps) > 0:
			# inject pkg versions into deps list
			deps2 = set()
			for dep in deps:
				pkg1 = self.pkgs[ dep[0] ].short_name()
				pkg2 = self.pkgs[ dep[1] ].short_name()
				deps2.add( (pkg1, pkg2) )
			deps = deps2

		return deps

	def resolve_packages_no_filesys(self):
		"""
		resolve current packages as far as possible without querying the file system
		"""

		nresolved_metafiles = -1
		nresolved_common_variant_pkgs = -1
		nconflicting_variants_removed = -1
		nresolved_single_variant_pkgs = -1

		while ((( \
				nresolved_metafiles + \
				nresolved_common_variant_pkgs + \
				nconflicting_variants_removed + \
				nresolved_single_variant_pkgs) != 0) and
				(not self.all_resolved())):

			# resolve metafiles
			nresolved_metafiles = self.resolve_metafiles()

			# remove conflicting variants
			nconflicting_variants_removed = self.remove_conflicting_variants()

			# resolve common variant packages
			nresolved_common_variant_pkgs = self.resolve_common_variants()

			# resolve packages with a single, fully-resolved variant
			nresolved_single_variant_pkgs = self.resolve_single_variant_packages()

	def remove_least_suitable_variant(self):
		"""
		remove one variant from any remaining unresolved packages, such that that variant is
		'least suitable' - that is, has the greatest number of packages which do not appear
		in the current configuration
		TODO remove this I think, error instead
		"""

		bad_pkg = None
		bad_variant = None
		bad_variant_score = -1

		for name,pkg in self.pkgs.iteritems():
			if (not pkg.is_resolved()) and (not pkg.is_anti()):
				for variant in pkg.get_variants():
					sc = self.get_num_unknown_pkgs(variant.working_list)
					if (sc > bad_variant_score):
						bad_pkg = pkg
						bad_variant = variant
						bad_variant_score = sc

		bad_pkg.get_variants().remove(bad_variant)

		if (self.rctxt.verbosity != 0):
			print
			print "removed least suitable variant:"
			print bad_pkg.short_name() + " variant:" + str(bad_variant)

	def get_num_unknown_pkgs(self, pkg_strs):
		"""
		given a list of package strings, return the number of packages in the list
		which do not appear in the current configuration
		"""
		num = 0
		for pkg_str in pkg_strs:
			pkg_req = str_to_pkg_req(pkg_str, self.rctxt.memcache)
			if pkg_req.name not in self.pkgs:
				num += 1

		return num

	def resolve_metafiles(self):
		"""
		for each package, resolve metafiles until no more can be resolved, returning
		the number of metafiles that were resolved.
		"""
		num = 0
		config2 = None

		for name, pkg in self.pkgs.iteritems():
			if (pkg.metadata == None):
				if pkg.resolve_metafile(self.rctxt.memcache):
					num += 1

					if (self.rctxt.verbosity != 0):
						print
						print "resolved metafile for " + pkg.short_name() + ":"
					if (self.rctxt.verbosity == 2):
						print str(pkg)

					# add required packages to the configuration, this may
					# reduce wrt existing packages (eg: foo-1 -> foo-1.2 is a reduction)
					requires = pkg.metadata.get_requires(self.rctxt.build_requires)

					if requires:
						for pkg_str in requires:
							pkg_req = str_to_pkg_req(pkg_str, self.rctxt.memcache)

							if (self.rctxt.verbosity != 0):
								print
								print "adding " + pkg.short_name() + \
									"'s required package " + pkg_req.short_name() + '...'

							if not config2:
								config2 = self.copy()
							config2.add_package(pkg_req, pkg)

							if (self.rctxt.verbosity != 0):
								print "config after adding " + pkg.short_name() + \
									"'s required package " + pkg_req.short_name() + ':'
							if (self.rctxt.verbosity == 1):
								print str(config2)
							elif (self.rctxt.verbosity == 2):
								config2.dump()

		if config2:
			self.swap(config2)
		return num


	def add_transitive_dependencies(self):
		"""
		for each package that is inexact and not resolved, calculate the package ranges that
		it must eventually pull in anyway, assuming dependency transitivity, and add those to
		the current configuration.
		"""
		if not self.rctxt.assume_dt:
			return
		while (self._add_transitive_dependencies() > 0):
			pass


	def _add_transitive_dependencies(self):

		num = 0
		config2 = None

		for name, pkg in self.pkgs.iteritems():
			if pkg.is_metafile_resolved():
				continue
			if pkg.is_anti():
				continue
			if pkg.has_added_transitivity:
				continue

			# get the requires lists for the earliest and latest versions of this pkg
			found_path, found_ver, found_epoch = self.rctxt.memcache.find_package2( \
				rez_filesys._g_syspaths, pkg.name, pkg.version_range, False)

			if (not found_path) or (not found_ver):
				continue
			metafile_e = self.rctxt.memcache.get_metafile( \
				found_path + "/" + str(found_ver) + "/package.yaml")
			if not metafile_e:
				continue

			found_path, found_ver, found_epoch = \
				self.rctxt.memcache.find_package2( \
					rez_filesys._g_syspaths, pkg.name, pkg.version_range, True)

			if (not found_path) or (not found_ver):
				continue
			metafile_l = self.rctxt.memcache.get_metafile( \
				found_path + "/" + str(found_ver) + "/package.yaml")
			if not metafile_l:
				continue

			pkg.has_added_transitivity = True

			requires_e = metafile_e.get_requires()
			requires_l = metafile_l.get_requires()
			if (not requires_e) or (not requires_l):
				continue

			# find pkgs that exist in the requires of both, and add these to the current
			# config as 'transitivity' packages
			for pkg_str_e in requires_e:
				if (pkg_str_e[0] == '!') or (pkg_str_e[0] == '~'):
					continue

				pkg_req_e = str_to_pkg_req(pkg_str_e, self.rctxt.memcache)

				for pkg_str_l in requires_l:
					pkg_req_l = str_to_pkg_req(pkg_str_l, self.rctxt.memcache)
					if (pkg_req_e.name == pkg_req_l.name):
						pkg_req = pkg_req_e
						if (pkg_req_e.version != pkg_req_l.version):
							# calc version range
							v_e = Version(pkg_req_e.version)
							v_l = Version(pkg_req_l.version)
							if(not v_e.ge < v_l.lt):
								continue
							v = Version()
							v.ge = v_e.ge
							v.lt = v_l.lt
							if (v.ge == Version.NEG_INF) and (v.lt != Version.INF):
								v.ge = [0]
							pkg_req = PackageRequest(pkg_req_e.name, str(v))

						if not config2:
							config2 = self.copy()
						config2.add_package(pkg_req, pkg, _Configuration.PKGCONN_TRANSITIVE)
						num = num + 1

			# find common variants that exist in both. Note that this code is somewhat redundant,
			# v similar work is done in resolve_common_variants - fix this in rez V2
			variants_e = metafile_e.get_variants()
			variants_l = metafile_l.get_variants()
			if (not variants_e) or (not variants_l):
				continue

			common_pkg_fams = None
			pkg_vers = {}

			for variant in (variants_e + variants_l):
				comm_fams = set()
				for pkgstr in variant:
					pkgreq = str_to_pkg_req(pkgstr, self.rctxt.memcache)
					comm_fams.add(pkgreq.name)
					if pkgreq.name in pkg_vers:
						pkg_vers[pkgreq.name].append(pkgreq.version)
					else:
						pkg_vers[pkgreq.name] = [ pkgreq.version ]

				if (common_pkg_fams == None):
					common_pkg_fams = comm_fams
				else:
					common_pkg_fams &= comm_fams

				if len(common_pkg_fams) == 0:
					break

			if (common_pkg_fams != None):
				for pkg_fam in common_pkg_fams:
					ver_range = VersionRange(str("|").join(pkg_vers[pkg_fam]))
					v = Version()
					if len(ver_range.versions) > 0:
						v.ge = ver_range.versions[0].ge
						v.lt = ver_range.versions[-1].lt
						if (v.ge == Version.NEG_INF) and (v.lt != Version.INF):
							v.ge = [0]

						pkg_req = PackageRequest(pkg_fam, str(v))

						if not config2:
							config2 = self.copy()
						config2.add_package(pkg_req, pkg, _Configuration.PKGCONN_TRANSITIVE)
						num = num + 1

		if config2:
			self.swap(config2)
		return num


	def remove_conflicting_variants(self):
		"""
		for each package, remove those variants which contain one or more packages which
		conflict with the current configuration. If a package has all of its variants
		removed in this way, then a pkg-conflict exception will be raised.
		"""

		if (self.rctxt.verbosity == 2):
			print
			print "removing conflicting variants..."

		num = 0

		for name,pkg in self.pkgs.iteritems():

			variants = pkg.get_variants()
			if variants != None:
				conflicts = []

				conflicting_variants = set()
				for variant in variants:
					for pkgstr in variant.metadata:
						pkg_req_ = str_to_pkg_req(pkgstr, self.rctxt.memcache)
						pkg_conflicting = self.get_conflicting_package(pkg_req_)
						if pkg_conflicting:
							pkg_req_conflicting = pkg_conflicting.as_package_request()
							pkg_req_this = pkg.as_package_request()
							pc = PackageConflict(pkg_req_conflicting, pkg_req_this, variant.metadata)
							conflicts.append(pc)
							conflicting_variants.add(variant)
							num += 1
							break

				if (len(conflicts) > 0):
					if (len(conflicts) == len(variants)):	# all variants conflict

						self.add_dot_graph_verbatim(\
							'subgraph cluster_variants {\n' + \
							'style=filled ;\n' + \
							'label=variants ;\n' + \
							'fillcolor="lightcyan1" ;' )

						# show all variants and conflicts in dot-graph
						for variant in variants:
							varstr = str(", ").join(variant.metadata)
							self.add_dot_graph_verbatim('"' + varstr + '" [style=filled fillcolor="white"] ;')

						self.add_dot_graph_verbatim('}')

						for variant in variants:
							varstr = str(", ").join(variant.metadata)
							self.dot_graph.append( ( pkg_req_this.short_name(), \
								( varstr, _Configuration.PKGCONN_VARIANT ) ) )
							self.dot_graph.append( ( pkg_req_conflicting.short_name(), \
								( varstr, _Configuration.PKGCONN_CONFLICT ) ) )

						self.rctxt.last_fail_dot_graph = self.get_dot_graph_as_string()
						raise PkgConflictError(conflicts)
					else:
						for cv in conflicting_variants:
							variants.remove(cv)

						if (self.rctxt.verbosity == 2):
							print
							print "removed conflicting variants from " + pkg.short_name() + ':'
							for conflict in conflicts:
								print str(conflict)
		return num


	def resolve_common_variants(self):
		"""
		for each package, find common package families within its variants, and add these to
		the configuration. For eg, if a pkg has 2 variants 'python-2.5' and 'python-2.6',
		then the inexact package 'python-2.5|2.6' will be added to the configuration
		(but only if ALL variants reference a 'python' package). Return the number of
		common package families resolved. Note that if a package contains a single variant,
		this this function will add every package in the variant to the configuration.
		"""

		num = 0
		config2 = self.copy()

		for name,pkg in self.pkgs.iteritems():

			variants = pkg.get_variants()
			if variants != None:

				# find common package families
				pkgname_sets = []
				pkgname_versions = {}
				pkgname_entries = {}

				for variant in variants:
					if (len(variant.working_list) > 0):
						pkgname_set = set()
						for pkgstr in variant.working_list:
							pkg_req = str_to_pkg_req(pkgstr, self.rctxt.memcache)
							pkgname_set.add(pkg_req.name)
							if not (pkg_req.name in pkgname_versions):
								pkgname_versions[pkg_req.name] = []
								pkgname_entries[pkg_req.name] = []
							pkgname_versions[pkg_req.name].append(pkg_req.version)
							pkgname_entries[pkg_req.name].append([ variant.working_list, pkgstr ])
						pkgname_sets.append(pkgname_set)

				if (len(pkgname_sets) > 0):
					common_pkgnames = pkgname_sets[0]
					for pkgname_set in pkgname_sets[1:]:
						common_pkgnames = common_pkgnames.intersection(pkgname_set)

					num += len(common_pkgnames)

					# add the union of each common package to the configuration,
					# and remove the packages from the variants' working lists
					for common_pkgname in common_pkgnames:
						ored_pkgs_str = common_pkgname + '-' +str('|').join(pkgname_versions[common_pkgname])
						pkg_req_ = str_to_pkg_req(ored_pkgs_str, self.rctxt.memcache)

						normalise_pkg_req(pkg_req_)
						config2.add_package(pkg_req_, pkg)

						for entry in pkgname_entries[common_pkgname]:
							entry[0].remove(entry[1])

						if (self.rctxt.verbosity != 0):
							print
							print "removed common package family '" + common_pkgname + "' from " + pkg.short_name() + \
								"'s variants; config after adding " + pkg_req_.short_name() + ':'
						if (self.rctxt.verbosity == 1):
							print str(config2)
						elif (self.rctxt.verbosity == 2):
							config2.dump()

		self.swap(config2)
		return num

	def resolve_single_variant_packages(self):
		"""
		find packages which have one non-conflicting, fully-resolved variant. These
		packages can now be fully resolved
		"""

		num = 0
		for name,pkg in self.pkgs.iteritems():
			if pkg.is_resolved():
				continue

			variants = pkg.get_variants()
			if (variants != None) and (len(variants) == 1):
				variant = variants[0]
				if (len(variant.working_list) == 0):

					# check resolved path exists
					root_path = pkg.base_path + '/' + str('/').join(variant.metadata)
					if not os.path.isdir(root_path):
						pkg_req_ = pkg.as_package_request()

						self.add_dot_graph_verbatim('"' + \
							pkg_req_.short_name() + ' NOT FOUND' + \
							'" [style=filled fillcolor="orangered"] ;')
						self.add_dot_graph_verbatim('"' + \
							pkg_req_.short_name() + '" -> "' + \
							pkg_req_.short_name() + ' NOT FOUND" ;')
						self.rctxt.last_fail_dot_graph = self.get_dot_graph_as_string()

						sys.stderr.write("Warning! Package not found: " + str(pkg_req_) + "\n")
						raise PkgNotFoundError(pkg_req_, root_path)

					pkg.resolve(root_path)
					num += 1

					if (self.rctxt.verbosity != 0):
						print
						print "resolved single-variant package " + pkg.short_name() + ':'
					if (self.rctxt.verbosity == 1):
						print str(self)
					elif (self.rctxt.verbosity == 2):
						print str(pkg)
		return num

	def dump(self):
		"""
		debug printout
		"""
		for name in self.families:
			pkg = self.pkgs[name]
			if (pkg.metadata == None):
				print pkg.short_name()
			else:
				print str(pkg)

	def __str__(self):
		"""
		short printout
		"""
		str_ = ""
		for name in self.families:
			pkg = self.pkgs[name]
			str_ += pkg.short_name()

			modif="("
			if pkg.is_resolved():
				modif += "r"
			elif pkg.is_metafile_resolved():
				modif += "b"
			else:
				modif += "u"
			if pkg.is_transitivity:
				modif += "t"
			str_ += modif + ") "

		return str_

	def short_str(self):
		"""
		even shorter printout
		"""
		str_ = ""
		for name in self.families:
			pkg = self.pkgs[name]
			str_ += pkg.short_name() + " "
		return str_



##############################################################################
# Internal Functions
##############################################################################


def pkg_to_pkg_req(pkg):
	"""
	Helper fn to convert a _Package to a PackageRequest
	"""
	return PackageRequest(pkg.name, str(pkg.version_range))


# todo remove, this now in pkgReq constr
def normalise_pkg_req(pkg_req):
	"""
	Helper fn to turn a PackageRequest into a regular representation. It is possible
	to describe a package in a way that is not the same as it will end up in the
	system. This is perfectly fine, but it can result in confusing dot-graphs. For
	example, the package 'foo-1|1' is equivalent to 'foo-1'.
	"""
	version_range = VersionRange(pkg_req.version)
	pkg_req.version = str(version_range)


def process_commands(cmds):
	"""
	Given a list of commands which represent a configuration context,

	a) Find the first forms of X=$X:<something_else>, and drop the leading $X so
		that values aren't inherited from the existing environment;
	b) Find variable overwrites and raise an exception if found (ie, consecutive
		commands of form "X=something, X=something_else".

	This function returns the altered commands. Order of commands is retained.
	"""
	set_vars = {}
	new_cmds = []

	for cmd_ in cmds:

		if type(cmd_) == type([]):
			cmd = cmd_[0]
			pkgname = cmd_[1]
		else:
			cmd = cmd_
			pkgname = None

		if cmd.split()[0] == "export":

			# parse name, value
			var_val = cmd[len("export"):].split('=',1)
			if (len(var_val) != 2):
				raise PkgCommandError("invalid command:'" + cmd + "'")
			varname = var_val[0].split()[0]
			val = var_val[1]

			# has value already been set?
			val_is_set = (varname in set_vars)

			# check for variable self-reference (eg X=$X:foo etc)
			pos = val.find('$'+varname)
			if (pos == -1):
				if val_is_set:
					# no self-ref but previous val, this is a val overwrite
					raise PkgCommandError("the command set by '" + str(pkgname) + "':\n" + cmd + \
						"\noverwrites the variable set in a previous command by '" + str(set_vars[varname]) + "'")
			elif not val_is_set:
				# self-ref but no previous val, so strip self-ref out
				val = val.replace('$'+varname,'')

			# special case. CMAKE_MODULE_PATH is such a common case, but unusually uses ';' rather
			# than ':' to delineate, that I just allow ':' and do the switch here. Using ';' causes
			# probs because in bash it needs to be single-quoted, and users will forget to do that
			# in their package.yamls.
			if(varname == "CMAKE_MODULE_PATH"):
				val = val.strip(':;')
				val = val.replace(':', "';'")

			set_vars[varname] = pkgname
			new_cmds.append("export " + varname + '=' + val)

		else:
			new_cmds.append(cmd)

	return new_cmds





#    Copyright 2008-2012 Dr D Studios Pty Limited (ACN 127 184 954) (Dr. D Studios)
#
#    This file is part of Rez.
#
#    Rez is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Lesser General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
#
#    Rez is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU Lesser General Public License
#    along with Rez.  If not, see <http://www.gnu.org/licenses/>.

########NEW FILE########
__FILENAME__ = rez_env_cmdlin
#
# Module for dealing just with command-line options for rez-env. This is needed because the
# autowrapper stuff needs to share some of this code. Also it means we get nice optparse behaviour
# in bash.
#

import optparse
import sys

_g_usage = "rez-env [options] pkg1 pkg2 ... pkgN"


class OptionParser2(optparse.OptionParser):
    def exit(self, status=0, msg=None):
        if msg:
            sys.stderr.write(msg)
        sys.exit(1)


def get_cmdlin_parser():
    p = OptionParser2(usage=_g_usage)

    p.add_option("-q", "--quiet", dest="quiet", action="store_true", default=False, \
        help="Suppress unnecessary output [default = %default]")
    p.add_option("-b", "--build", dest="build", action="store_true", default=False, \
        help="Include build-only package requirements [default = %default]")
    p.add_option("-o", "--no_os", dest="no_os", action="store_true", default=False, \
        help="Stop rez-env from implicitly requesting the operating system package [default = %default]")
    p.add_option("--no-cache", dest="no_cache", action="store_true", default=False, \
        help="disable caching [default = %default]")
    p.add_option("-u", "--ignore_blacklist", dest="ignore_blacklist", action="store_true", default=False, \
        help="Include blacklisted packages [default = %default]")
    p.add_option("-g", "--ignore_archiving", dest="ignore_archiving", action="store_true", default=False, \
        help="Include archived packages [default = %default]")
    p.add_option("-d", "--no_assume_dt", dest="no_assume_dt", action="store_true", default=False, \
        help="Do not assume dependency transitivity [default = %default]")
    p.add_option("-m", "--mode", dest="mode", type="string", default="latest", \
        help="Set the package resolution mode [default=%default]")
    p.add_option("-p", "--prompt", dest="prompt", type="string", default=">", \
        help="Set the prompt decorator [default=%default]")
    p.add_option("-i", "--time", dest="time", type="int", default=0, \
        help="Ignore packages newer than the given epoch time")
    p.add_option("-r", "--rcfile", dest="rcfile", type="string", default='', \
        help="Source this file after the new shell is invoked")
    p.add_option("--tmpdir", dest="tmpdir", type="string", default='', \
        help="Set the temp directory manually, /tmp otherwise")    
    p.add_option("--propogate-rcfile", dest="prop_rcfile", action="store_true", default=False, \
        help="Propogate rcfile into subshells")
    p.add_option("-c", "--cmd", dest="cmd", type="string", default='', \
        help="Run the given command")
    p.add_option("-s", "--stdin", dest="stdin", action="store_true", default=False, \
        help="Read commands from stdin, rather than starting an interactive shell [default = %default]")
    p.add_option("-a", "--add_loose", dest="add_loose", action="store_true", default=False, \
        help="Add mode (loose). Packages will override or add to the existing request list [default = %default]")
    p.add_option("-t", "--add_strict", dest="add_strict", action="store_true", default=False, \
        help="Add mode (strict). Packages will override or add to the existing resolve list [default = %default]")
    p.add_option("-f", "--view_fail", dest="view_fail", type=int, default=-1, \
        help="View the dotgraph for the Nth failed config attempt")
    p.add_option("--no-local", dest="no_local", action="store_true", default=False, \
        help="don't load local packages")

    return p


# rez-env uses this, nothing else
if __name__ == "__main__":

    p = get_cmdlin_parser()
    (opts, args) = p.parse_args()
    print str(' ').join(args)

    d = eval(str(opts))
    for k,v in d.iteritems():
        ku = k.upper()
        print "_REZ_ENV_OPT_%s='%s'" % (ku, str(v))



#    Copyright 2008-2012 Dr D Studios Pty Limited (ACN 127 184 954) (Dr. D Studios)
#
#    This file is part of Rez.
#
#    Rez is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Lesser General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
#
#    Rez is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU Lesser General Public License
#    along with Rez.  If not, see <http://www.gnu.org/licenses/>.

########NEW FILE########
__FILENAME__ = rez_exceptions
"""
Exceptions.
Note: Every exception class can be default-constructed (ie all args default to None) because of
a serialisation issue with the exception class, see:
http://irmen.home.xs4all.nl/pyro3/troubleshooting.html
"""


class RezError(Exception):
    """
    Base-class Rez error.
    """
    def __init__(self, value=None):
        self.value = value
    def __str__(self):
        return str(self.value)


class PkgSystemError(RezError):
    """
    rez system error
    """
    def __init__(self, value):
        RezError.__init__(self, value)


class PkgFamilyNotFoundError(RezError):
    """
    A package family could not be found
    """
    def __init__(self, family_name=None):
        RezError.__init__(self)
        self.family_name = family_name
    def __str__(self):
        return str(self.family_name)


class PkgNotFoundError(RezError):
    """
    A package could not be found
    """
    def __init__(self, pkg_req=None, resolve_path=None):
        RezError.__init__(self)
        self.pkg_req = pkg_req
        self.resolve_path = resolve_path
    def __str__(self):
        return str( (str(self.pkg_req), self.resolve_path) )


class PkgConflictError(RezError):
    """
    A package conflicts with another. A list of conflicts is provided -
    this is for cases where all of a package's variants conflict with various
    packages
    """
    def __init__(self, pkg_conflicts=None, last_dot_graph=""):
        RezError.__init__(self)
        self.pkg_conflicts = pkg_conflicts
        self.last_dot_graph = last_dot_graph
    def __str__(self):
        strs = []
        for pkg_conflict in self.pkg_conflicts:
            strs.append(str(pkg_conflict))
        return str(strs)


class PkgsUnresolvedError(RezError):
    """
    One or more packages are not resolved
    """
    def __init__(self, pkg_reqs=None):
        RezError.__init__(self)
        self.pkg_reqs = pkg_reqs
    def __str__(self):
        strs = []
        for pkg_req in self.pkg_reqs:
            strs.append(str(pkg_req))
        return str(strs)


class PkgConfigNotResolvedError(RezError):
    """
    The configuration could not be resolved. 'fail_config_list' is a list of
    strings indicating failed configuration attempts.
    """
    def __init__(self, pkg_reqs=None, fail_config_list=None, last_dot_graph=None):
        RezError.__init__(self)
        self.pkg_reqs = pkg_reqs
        self.fail_config_list = fail_config_list
        self.last_dot_graph = last_dot_graph
    def __str__(self):
        strs = []
        for pkg_req in self.pkg_reqs:
            strs.append(str(pkg_req))
        return str(strs)


class PkgCommandError(RezError):
    """
    There is an error in a command or list of commands
    """
    def __init__(self, value=None):
        RezError.__init__(self, value)


class PkgCyclicDependency(RezError):
    """
    One or more cyclic dependencies have been detected in a set of packages
    """
    def __init__(self, dependencies=None, dot_graph=None):
        """
        dependencies is a list of (requiree, required) pairs.
        dot_graph_str is a string describing the dot-graph of the whole environment resolution -
        it is required because the user will want to have context, to determine how the cyclic
        list of packages was generated in the first place
        """
        RezError.__init__(self)
        self.deps = dependencies
        self.dot_graph = dot_graph

    def __str__(self):
        # print out as a dot-graph
        s = "digraph g {\n"
        for dep in self.deps:
            s += '"' + dep[0] + '" -> "' + dep[1] + '"\n'
        s += "}"
        return s













#    Copyright 2008-2012 Dr D Studios Pty Limited (ACN 127 184 954) (Dr. D Studios)
#
#    This file is part of Rez.
#
#    Rez is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Lesser General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
#
#    Rez is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU Lesser General Public License
#    along with Rez.  If not, see <http://www.gnu.org/licenses/>.

########NEW FILE########
__FILENAME__ = rez_filesys
# TODO add blacklisting/archiving, is anyone using that though?

import os
import sys
import os.path
import subprocess as sp
from versions import *
from public_enums import *
from rez_exceptions import *


_g_rez_path                 = os.getenv("REZ_PATH")
_g_local_pkgs_path          = os.getenv("REZ_LOCAL_PACKAGES_PATH")
_g_new_timestamp_behaviour  = os.getenv("REZ_NEW_TIMESTAMP_BEHAVIOUR")
_g_os_paths                 = []


# get os
_g_os_pkg = None
osname = os.getenv("REZ_PLATFORM")
if osname:
    _g_os_pkg = osname
else:
    import platform
    osname = platform.system()
    _g_os_pkg = ""

    if osname == "Linux":
        _g_os_pkg = "Linux"
    elif osname == "Darwin":
        _g_os_pkg = "Darwin"

if _g_os_pkg == "":
    sys.stderr.write("Rez warning: Unknown operating system '" + _g_os_pkg + "'\n")


# get os-specific paths
try:
    p = sp.Popen("_rez_get_PATH", stdout=sp.PIPE, stderr=sp.PIPE)
    out,err = p.communicate()
    _g_os_paths = out.strip().split(':')
except:
    pass


def get_system_package_paths():
    """
    Get the system roots for package installations. REZ_PACKAGES_PATH is a colon-
    separated string, and the paths will be searched in order of appearance.
    """
    syspathstr = os.getenv(REZ_PACKAGES_PATH_ENVVAR)
    if syspathstr:
        toks = syspathstr.split(':')
        syspaths = []
        for tok in toks:
            if tok:
                syspaths.append(tok.strip())
        return syspaths
    else:
        raise PkgSystemError(REZ_PACKAGES_PATH_ENVVAR + " is not set")

_g_syspaths = get_system_package_paths()

_g_syspaths_nolocal = _g_syspaths[:]
if _g_local_pkgs_path in _g_syspaths_nolocal:
    _g_syspaths_nolocal.remove(_g_local_pkgs_path)


def get_versions_in_directory(path, warnings):
    is_local_pkgs = path.startswith(_g_local_pkgs_path)
    vers = []

    for f in os.listdir(path):
        fullpath = os.path.join(path, f)
        if os.path.isdir(fullpath):
            try:
                ver = Version(f)
            except:
                continue

            yaml_file = os.path.join(fullpath, PKG_METADATA_FILENAME)
            if not os.path.isfile(yaml_file):
                if warnings:
                    sys.stderr.write("Warning: ignoring package with missing " + \
                        PKG_METADATA_FILENAME + ": " + fullpath + '\n')
                continue

            timestamp = 0
            if not is_local_pkgs:
                release_time_f = fullpath + '/.metadata/release_time.txt'
                if os.path.isfile(release_time_f):
                    with open(release_time_f, 'r') as f:
                        timestamp = int(f.read().strip())
                elif _g_new_timestamp_behaviour:
                    s = "Warning: The package at %s is not timestamped and will be ignored. " + \
                        "To timestamp it manually, use the rez-timestamp utility."
                    print >> sys.stderr, s % fullpath
                    continue

            vers.append((ver, timestamp))

    vers.sort()
    return vers

########NEW FILE########
__FILENAME__ = rez_memcached
import sys
import os
import time
import rez_filesys
import rez_metafile
from versions import *
from public_enums import *
from rez_exceptions import *



_g_caching_enabled = True
_g_memcached_server = os.getenv("REZ_MEMCACHED_SERVER") or "127.0.0.1:11211"


def _create_client():
    if not _g_caching_enabled:
        return None
    return memcache.Client([_g_memcached_server], cache_cas=True)


def print_cache_warning(msg):
    print >> sys.stderr, "Cache Warning: %s" % msg


# init
_g_caching_enabled = not os.getenv("REZ_DISABLE_CACHING")
if _g_caching_enabled:
    try:
        import memcache
        from memcached_client import *
    except:
        _g_caching_enabled = False
if _g_caching_enabled:
    mc = _create_client()
    if not mc.set("test_set", "success"):
        _g_caching_enabled = False
    mc = None


class RezMemCache():
    """
    Cache for filesystem access and resolves.
    """
    def __init__(self, time_epoch=0, use_caching=True):
        self.epoch = time_epoch or int(time.time())
        self.families = set()
        self.versions = {} # (path,order): [versions]
        self.metafiles = {} # path, ConfigMetadata
        self.mc = None
        if use_caching and _g_caching_enabled:
            mc = _create_client()
            self.mc = MemCacheClient(mc)

    def get_metafile(self, path):
        """
        Load the yaml metadata in the given file.
        """
        d = self.metafiles.get(path)
        if d is not None:
            return d

        k = ("PKGYAML", path)
        path_modtime = os.path.getmtime(path)

        if self.mc:
            t = self.mc.get(k)
            if t is not None:
                mtime,d = t
                if path_modtime == mtime:
                    self.metafiles[path] = d
                    return d

        d = rez_metafile.ConfigMetadata(path)
        d.delete_nonessentials()

        if self.mc:
            self.mc.set(k, (path_modtime, d))
        self.metafiles[path] = d
        return d

    def get_versions_in_directory(self, path, warnings=True):
        """
        For a given directory, return a list of (Version,epoch), which match version directories 
        found in the given directory.
        """
        vers = self.versions.get(path)
        if vers is not None:
            return vers

        if not os.path.isdir(path):
            return []

        k = ("VERSIONS", path)
        path_modtime = os.path.getmtime(path)

        if self.mc:
            t = self.mc.get(k)
            if t is not None:
                mtime,tvers = t
                if path_modtime == mtime:
                    vers = [x for x in tvers if x[1] <= self.epoch]
                    self.versions[path] = vers
                    return vers

        tvers = rez_filesys.get_versions_in_directory(path, warnings)
        if self.mc:
            self.mc.set(k, (path_modtime, tvers))
        vers = [x for x in tvers if x[1] <= self.epoch]
        self.versions[path] = vers
        return vers

    def find_package(self, path, ver_range, latest=True, exact=False):
        """
        Given a path to a package family and a version range, return (resolved version, epoch)
        or None if not found.
        """
        vers = self.get_versions_in_directory(path)

        # check for special case - unversioned package
        # todo subtle bug here, unversioned pkg's timestamp not taken into account. In practice
        # though this should not cause any problems.
        if not vers and ver_range.is_any() and os.path.isfile(os.path.join(path, PKG_METADATA_FILENAME)):
            return (Version(""), 0)

        if not ver_range.is_inexact():
            exact_ver = [x for x in vers if x[0] == ver_range.versions[0]]
            if exact_ver:
                return exact_ver[0]

        if exact:
            return None

        # find the earliest/latest version on disk that falls within ver
        if latest:
            vers = reversed(vers)
        for ver in vers:
            if ver_range.contains_version(ver[0].ge):
                return ver

        return None

    def find_package2(self, paths, family_name, ver_range, latest=True, exact=False):
        """
        Given a list of package paths, a family name and a version range, return (family path,
        resolved version, epoch), or (None,None,None) if not found. If two versions in two different 
        paths are the same, then the package in the first path is returned in preference.
        """
        maxminver = None
        fpath = None

        for pkg_path in paths:
            family_path = os.path.join(pkg_path, family_name)
            ver2 = self.find_package(family_path, ver_range, latest, exact)
            if ver2:
                if exact:
                    return family_path, ver2[0], ver2[1]
                elif latest:
                    if maxminver:
                        if (maxminver[0].ge < ver2[0].ge):
                            maxminver = ver2
                            fpath = family_path
                    else:
                        maxminver = ver2
                        fpath = family_path
                else:   # earliest
                    if maxminver:
                        if (maxminver[0].ge > ver2[0].ge):
                            maxminver = ver2
                            fpath = family_path
                    else:
                        maxminver = ver2
                        fpath = family_path

        if maxminver:
            return fpath, maxminver[0], maxminver[1]
        else:
            return (None,None,None)

    def package_family_exists(self, paths, family_name):
        """
        Determines if the package family exists. This involves only quite light file system 
        access, so isn't memcached.
        """
        if family_name in self.families:
            return True

        for path in paths:
            if os.path.isdir(os.path.join(path, family_name)):
                self.families.add(family_name)
                return True

        return False

    def store_resolve(self, paths, pkg_reqs, result):
        """
        Store a resolve in the cache.
        """
        if not self.mc:
            return

        pkg_res_list = result[0]

        # find most recent pkg timestamp, we store the cache entry on this
        max_epoch = 0
        for pkg_res in pkg_res_list:
            max_epoch = max(pkg_res.timestamp, max_epoch)

        # construct cache keys
        k_base = (paths, pkg_reqs)
        k_no_timestamp = ("RESOLVE-NO-TS", k_base)
        k_timestamped = ("RESOLVE", max_epoch, k_base)

        # store
        self.mc.update_add_to_set(k_no_timestamp, max_epoch)
        self.mc.set(k_timestamped, (self.epoch,result))

    def package_fam_modified_during(self, paths, family_name, start_epoch, end_epoch):
        for path in paths:
            famp = os.path.join(path, family_name)
            if os.path.isdir(famp):
                mtime = int(os.path.getmtime(famp))
                if mtime >= start_epoch and mtime <= end_epoch:
                    return famp

    def get_resolve(self, paths, pkg_reqs):
        """
        Return a cached resolve, or None if the resolve is not found or possibly stale.
        """
        if not self.mc:
            return None,None

        k_base = (paths, pkg_reqs)

        # get most recent cache of this resolve that is < current resolve time
        k_no_timestamp = ("RESOLVE-NO-TS", k_base)
        timestamps = self.mc.get(k_no_timestamp)
        if not timestamps:
            return None,None

        older_timestamps = [x for x in timestamps if x < self.epoch]
        if not older_timestamps:
            return None,None

        cache_timestamp = sorted(older_timestamps)[-1]
        k_timestamped = ("RESOLVE", cache_timestamp, k_base)
        t = self.mc.get(k_timestamped)
        if not t:
            return None,None

        # trim down list of resolve pkgs to those that may invalidate the cache
        result_epoch,result = t

        # cache cannot be stale in this case
        if self.epoch <= result_epoch:
            return result, cache_timestamp

        pkg_res_list = result[0]
        pkgs = {}
        for pkg_res in pkg_res_list:
            pkgs[pkg_res.name] = pkg_res

        # check for new package versions released before the current resolve time, but after the
        # cache resolve time. These may invalidate the cache.
        for pkg_name,pkg in pkgs.items():
            if not self.package_fam_modified_during(paths, pkg_name, result_epoch, self.epoch):
                del pkgs[pkg_name]

        if not pkgs:
            return result, result_epoch

        # remove pkgs where new versions have been released after the cache was written, but none
        # of these versions fall within the 'max bounds' of that pkg. This can be simplified to 
        # checking only the earliest version in this set.
        # TODO NOT YET IMPLEMENTED
        #for pkg_name,pkg in pkgs.items():
        #    pass

        if pkgs:
            print_cache_warning("Newer released package(s) caused cache miss: %s" % \
                str(", ").join(pkgs.keys()))
            return None,None
        else:
            return result, cache_timestamp


        """
        # check if there are any versions of the resolved packages that are newer than the resolved
        # version, but older than the current time - if so, this resolve may be out of date, and
        # must be discarded.
        print "checking for newer versions..."

        pkg_res_list = result[0]
        for pkg_res in pkg_res_list:
            pkg_res_ver = Version(pkg_res.version)
            fam_path,ver,pkg_epoch = self.find_package2(paths, pkg_res.name, VersionRange(""))
            if ver is not None and ver > pkg_res_ver and pkg_epoch <= self.epoch:
                print fam_path
                print "newer pkg: " + str(ver)
                print "existing pkg: " + str(pkg_res_ver)
                return None,None

        return result, cache_timestamp
        """

########NEW FILE########
__FILENAME__ = rez_metafile
"""
Class for loading and verifying rez metafiles
"""

import yaml
import subprocess
import os


class ConfigMetadataError(Exception):
	def __init__(self, value):
		self.value = value
	def __str__(self):
		return str(self.value)


# TODO this class is too heavy
class ConfigMetadata:
	"""
	metafile. An incorrectly-formatted file will result in either a yaml exception (if
	the syntax is wrong) or a ConfigMetadataError (if the content is wrong). An empty
	metafile is acceptable, and is supported for fast integration of 3rd-party packages
	"""

	# file format versioning, only update this if the package.yamls have to change
	# format in a way that is not backwards compatible
	METAFILE_VERSION = 0

	def __init__(self, filename):
		self.filename = filename
		self.config_version = ConfigMetadata.METAFILE_VERSION
		self.uuid = None
		self.authors = None
		self.description = None
		self.name = None
		self.version = None
		self.help = None
		self.requires = None
		self.build_requires = None
		self.variants = None
		self.commands = None

		with open(filename) as f:
			self.metadict = yaml.load(f.read()) or {}

		if self.metadict:
			###############################
			# Common content
			###############################

			if (type(self.metadict) != dict):
				raise ConfigMetadataError("package metafile '" + self.filename + \
					"' contains non-dictionary root node")

			# config_version
			if not ("config_version" in self.metadict):
				raise ConfigMetadataError("package metafile '" + self.filename + \
					"' is missing 'config_version'")
			else:
				sysver = self.metadict["config_version"]
				try:
					self.config_version = int(sysver)
				except (ValueError, TypeError):
					raise ConfigMetadataError("package metafile '" + self.filename + \
						"' contains invalid config version '" + str(sysver) + "'")

				if (self.config_version < 0) or (self.config_version > ConfigMetadata.METAFILE_VERSION):
					raise ConfigMetadataError("package metafile '" + self.filename + \
						"' contains invalid config version '" + str(self.config_version) + "'")

			def _get_str(label):
				val = self.metadict.get(label)
				if val is not None:
					return str(val).strip()
				return None

			self.uuid			= _get_str("uuid")
			self.description 	= _get_str("description")
			self.version 		= _get_str("version")
			self.name 			= _get_str("name")
			self.help 			= _get_str("help")

			# authors
			if "authors" in self.metadict:
				self.authors = self.metadict["authors"]
				if (type(self.authors) != list):
					raise ConfigMetadataError("package metafile '" + self.filename + \
						"' contains 'authors' entry which is not a list")

			# config-version-specific content
			if (self.config_version == 0):
				self.load_0();

	def delete_nonessentials(self):
		"""
		Delete everything not needed for package resolving.
		"""
		if self.uuid:
			del self.metadict["uuid"]
			self.uuid = None
		if self.description:
			del self.metadict["description"]
			self.description = None
		if self.help:
			del self.metadict["help"]
			self.help = None
		if self.authors:
			del self.metadict["authors"]
			self.authors = None

	def get_requires(self, include_build_reqs = False):
		"""
		Returns the required package names, if any
		"""
		if include_build_reqs:
			reqs = []
			# add build-reqs beforehand since they will tend to be more specifically-
			# versioned, this will speed up resolution times
			if self.build_requires:
				reqs += self.build_requires
			if self.requires:
				reqs += self.requires

			if len(reqs) > 0:
				return reqs
			else:
				return None
		else:
			return self.requires

	def get_build_requires(self):
		"""
		Returns the build-required package names, if any
		"""
		return self.build_requires

	def get_variants(self):
		"""
		Returns the variants, if any
		"""
		return self.variants

	def get_commands(self):
		"""
		Returns the commands, if any
		"""
		return self.commands

	def get_string_replace_commands(self, version, base, root):
		"""
		Get commands with string replacement
		"""
		if self.commands:

			vernums = version.split('.') + [ '', '' ]
			major_version = vernums[0]
			minor_version = vernums[1]
			user = os.getenv("USER", "UNKNOWN_USER")

			new_cmds = []
			for cmd in self.commands:
				cmd = cmd.replace("!VERSION!", version)
				cmd = cmd.replace("!MAJOR_VERSION!", major_version)
				cmd = cmd.replace("!MINOR_VERSION!", minor_version)
				cmd = cmd.replace("!BASE!", base)
				cmd = cmd.replace("!ROOT!", root)
				cmd = cmd.replace("!USER!", user)
				new_cmds.append(cmd)
			return new_cmds
		return None

	def load_0(self):
		"""
		Load config_version=0
		"""
		# requires
		if "requires" in self.metadict:
			self.requires = self.metadict["requires"]
			if (type(self.requires) != list):
				raise ConfigMetadataError("package metafile '" + self.filename + \
					"' contains non-list 'requires' node")
			if (len(self.requires) == 0):
				self.requires = None
			else:
				req0 = self.requires[0]
				if (type(req0) != str):
					raise ConfigMetadataError("package metafile '" + self.filename + \
						"' contains non-string 'requires' entries")

		# build_requires
		if "build_requires" in self.metadict:
			self.build_requires = self.metadict["build_requires"]
			if (type(self.build_requires) != list):
				raise ConfigMetadataError("package metafile '" + self.filename + \
					"' contains non-list 'build_requires' node")
			if (len(self.build_requires) == 0):
				self.build_requires = None
			else:
				req0 = self.build_requires[0]
				if (type(req0) != str):
					raise ConfigMetadataError("package metafile '" + self.filename + \
						"' contains non-string 'build_requires' entries")

		# variants
		if "variants" in self.metadict:
			self.variants = self.metadict["variants"]
			if (type(self.variants) != list):
				raise ConfigMetadataError("package metafile '" + self.filename + \
					"' contains non-list 'variants' node")
			if (len(self.variants) == 0):
				self.variants = None
			else:
				var0 = self.variants[0]
				if (type(var0) != list):
					raise ConfigMetadataError("package metafile '" + self.filename + \
						"' contains non-list 'variants' entries")

		# commands
		if "commands" in self.metadict:
			self.commands = self.metadict["commands"]
			if (type(self.commands) != list):
				raise ConfigMetadataError("package metafile '" + self.filename + \
					"' contains non-list 'commands' node")
			if (len(self.commands) == 0):
				self.commands = None



#    Copyright 2008-2012 Dr D Studios Pty Limited (ACN 127 184 954) (Dr. D Studios)
#
#    This file is part of Rez.
#
#    Rez is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Lesser General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
#
#    Rez is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU Lesser General Public License
#    along with Rez.  If not, see <http://www.gnu.org/licenses/>.

########NEW FILE########
__FILENAME__ = rez_parse_request
"""
Functions for parsing rez parenthesised syntax, used to create subshells on the fly (see the comments
in bin/rez-env-autowrappers_.py)
"""

import pyparsing as pp



# split pkgs string into separate subshells
base_pkgs = None
subshells = None
curr_ss = None
merged_base_pkgs = None
merged_subshells = None

def parse_request(s):
    """
    Parses any request string, including parenthesised form, and merging (pipe operator).
    @return (base_pkgs, subshells). base_pkgs is a list of packages in the 'master' shell, ie 
        outside of any parenthesised subshell. 'subshells' is a dict of subshells, keyed on the
        subshell name.
    """

    global base_pkgs
    global subshells
    global curr_ss
    global merged_base_pkgs
    global merged_subshells

    base_pkgs = []
    subshells = {}
    merged_base_pkgs = []
    merged_subshells = {}
    curr_ss = None

    def _parse_pkg(s, loc, toks):
        global curr_ss
        pkg_str = str('').join(toks)
        if curr_ss is None:
            base_pkgs.append(pkg_str)
        else:
            curr_ss["pkgs"].append(pkg_str)

    def _parse_ss_label(s, loc, toks):
        curr_ss["label"] = toks[0]

    def _parse_ss_prefix(s, loc, toks):
        global curr_ss
        curr_ss = {
            "pkgs": [],
            "prefix": '',
            "suffix": ''
        }
        prefix_str = toks[0][:-1]
        if prefix_str:
            curr_ss["prefix"] = prefix_str

    def _parse_ss_suffix(s, loc, toks):
        global curr_ss
        suffix_str = toks[0][1:]
        if suffix_str:
            curr_ss["suffix"] = suffix_str
        if "label" not in curr_ss:
            pkg_fam = curr_ss["pkgs"][0].split('-')[0]
            label_str = curr_ss["prefix"] + pkg_fam + curr_ss["suffix"]
            curr_ss["label"] = label_str

        subshell_name = curr_ss["label"]
        if subshell_name in subshells:
            print >> sys.stderr, "Error: subshell '%s' is defined more than once!" % subshell_name
            sys.exit(1)

        subshells[subshell_name] = curr_ss
        curr_ss = None

    def _parse_ss_request(s, loc, toks):
        global base_pkgs
        global subshells
        global merged_base_pkgs
        global merged_subshells
        merged_base_pkgs = _merge_pkgs(merged_base_pkgs, base_pkgs)
        merged_subshells = _merge_subshells(merged_subshells, subshells)
        base_pkgs = []
        subshells = {}        

    _pkg = pp.Regex("[a-zA-Z_0-9~<=^\\.\\-\\!\\+]+").setParseAction(_parse_pkg)

    _subshell_label = pp.Regex("[a-zA-Z0-9_]+")
    _subshell_label_decl = (_subshell_label + ':').setParseAction(_parse_ss_label)
    _subshell_body = (_subshell_label_decl * (0,1)) + pp.OneOrMore(_pkg)
    _subshell_prefix = (pp.Regex("[a-zA-Z0-9_]+\\(") ^ '(').setParseAction(_parse_ss_prefix)
    _subshell_suffix = (pp.Regex("\\)[a-zA-Z0-9_]+") ^ ')').setParseAction(_parse_ss_suffix)
    _subshell = _subshell_prefix + _subshell_body + _subshell_suffix

    _request = pp.OneOrMore(_pkg ^ _subshell).setParseAction(_parse_ss_request)
    _expr = _request + pp.ZeroOrMore('|' + _request)

    pr = _expr.parseString(s, parseAll=True)
    return (merged_base_pkgs, merged_subshells)


def _merge_pkgs(pkgs, override_pkgs):

    def _parse_pkg(pkg):
        rm = pkg.startswith('^')
        if rm:
            if len(pkg.split('-')) > 1:
                raise Exception("Only unversioned package allowed with the remove operator '^'")
            pkg = pkg[1:]
        return (pkg.split('-')[0], rm)

    merged_pkgs = []
    override_pkgs2 = override_pkgs[:]

    opkgs = {}
    for pkg in override_pkgs:
        name,rm = _parse_pkg(pkg)
        opkgs[name] = (pkg,rm)

    for pkg in pkgs:
        name,rm = _parse_pkg(pkg)
        opkg = opkgs.get(name)
        if opkg:
            if not opkg[1]:
                merged_pkgs.append(opkg[0])
            override_pkgs2.remove(opkg[0])
        else:
            merged_pkgs.append(pkg)

    merged_pkgs.extend(override_pkgs2)
    return merged_pkgs


def _merge_subshells(subshells, override_subshells):

    merged_subshells = {}
    override_subshells2 = override_subshells.copy()

    for name,ss in subshells.iteritems():
        oss = override_subshells.get(name)
        if oss:
            merged_pkgs = _merge_pkgs(ss["pkgs"], oss["pkgs"])
            new_ss = ss.copy()
            new_ss.update(oss)
            new_ss["pkgs"] = merged_pkgs
            merged_subshells[name] = new_ss
            del override_subshells2[name]
        else:
            merged_subshells[name] = ss

    merged_subshells.update(override_subshells2)
    return merged_subshells


def encode_request(base_pkgs, subshells):
    """
    Take base packages and subshells (that parse_request() generates), and re-encode back into
        a string. Returns this string.
    """
    toks = base_pkgs[:]
    for ss in subshells.itervalues():
        toks.append(_encode_subshell(ss))
    return str(' ').join(toks)


def _encode_subshell(ss):
    s = ''
    prefix = ss.get("prefix") or ''
    s += prefix

    s += '(%s: ' % ss["label"]
    s += str(' ').join(ss["pkgs"])

    suffix = ss.get("suffix") or ''
    s += ")%s" % suffix
    
    return s

########NEW FILE########
__FILENAME__ = rez_release
"""
rez-release

A tool for releasing rez - compatible projects centrally
"""

import sys
import os
import time
import pysvn
import subprocess
import rez_release_base as rrb
from rez_metafile import *
import versions


##############################################################################
# Exceptions
##############################################################################

class RezReleaseError(Exception):
	def __init__(self, value):
		self.value = value
	def __str__(self):
		return str(self.value)


##############################################################################
# Globals
##############################################################################

REZ_RELEASE_PATH_ENV_VAR = 		"REZ_RELEASE_PACKAGES_PATH"
EDITOR_ENV_VAR		 	= 		"REZ_RELEASE_EDITOR"
RELEASE_COMMIT_FILE 	= 		"rez-release-svn-commit.tmp"


##############################################################################
# Public Functions
##############################################################################


def release_from_path(path, commit_message, njobs, build_time, allow_not_latest):
	"""
	release a package from the given path on disk, copying to the relevant tag,
	and performing a fresh build before installing it centrally. If 'commit_message'
	is None, then the user will be prompted for input using the editor specified
	by $REZ_RELEASE_EDITOR.
	path: filepath containing the project to be released
	commit_message: None, or message string to write to svn, along with changelog
	njobs: number of threads to build with; passed to make via -j flag
	build_time: epoch time to build at. If 0, use current time
	allow_not_latest: if True, allows for releasing a tag that is not > the latest tag version
	"""
	# check for ./package.yaml
	if not os.access(path + "/package.yaml", os.F_OK):
		raise RezReleaseError(path + "/package.yaml not found")

	# check we're in an svn working copy
	svnc = pysvn.Client()
	svnc.set_interactive( True )
	svnc.set_auth_cache( False )
	svnc.set_store_passwords( False )
	svnc.callback_get_login = getSvnLogin

	svn_entry = svnc.info(path)
	if not svn_entry:
		raise RezReleaseError("'" + path + "' is not an svn working copy")
	this_url = str(svn_entry["url"])

	# check that ./package.yaml is under svn control
	if not svn_url_exists(svnc, this_url + "/package.yaml"):
		raise RezReleaseError(path + "/package.yaml is not under source control")

	if (commit_message == None):
		# get preferred editor for commit message
		editor = os.getenv(EDITOR_ENV_VAR)
		if not editor:
			raise RezReleaseError("rez-release: $" + EDITOR_ENV_VAR + " is not set.")

	# load the package metadata
	metadata = ConfigMetadata(path + "/package.yaml")
	if (not metadata.version):
		raise RezReleaseError(path + "/package.yaml does not specify a version")
	try:
		this_version = versions.Version(metadata.version)
	except VersionError:
		raise RezReleaseError(path + "/package.yaml contains illegal version number")

	# metadata must have name
	if not metadata.name:
		raise RezReleaseError(path + "/package.yaml is missing name")

	# metadata must have uuid
	if not metadata.uuid:
		raise RezReleaseError(path + "/package.yaml is missing uuid")

	# metadata must have description
	if not metadata.description:
		raise RezReleaseError(path + "/package.yaml is missing a description")

	# metadata must have authors
	if not metadata.authors:
		raise RezReleaseError(path + "/package.yaml is missing authors")

	pkg_release_path = os.getenv(REZ_RELEASE_PATH_ENV_VAR)
	if not pkg_release_path:
		raise RezReleaseError("$" + REZ_RELEASE_PATH_ENV_VAR + " is not set.")

	# check uuid against central uuid for this package family, to ensure that
	# we are not releasing over the top of a totally different package due to naming clash
	existing_uuid = None
	package_uuid_dir = pkg_release_path + '/' + metadata.name
	package_uuid_file = package_uuid_dir + "/package.uuid"
	package_uuid_exists = True

	try:
		existing_uuid = open(package_uuid_file).read().strip()
	except Exception:
		package_uuid_exists = False
		existing_uuid = metadata.uuid

	if(existing_uuid != metadata.uuid):
		raise RezReleaseError("the uuid in '" + package_uuid_file + \
			"' does not match this package's uuid - you may have a package name clash. All package " + \
			"names must be unique.")

	# find the base path, ie where 'trunk', 'branches', 'tags' should be
	pos_tr = this_url.find("/trunk")
	pos_br = this_url.find("/branches")
	pos = max(pos_tr, pos_br)
	if (pos == -1):
		raise RezReleaseError(path + "is not in a branch or trunk")
	base_url = this_url[:pos]

	# check we're in a state to release (no modified/out-of-date files etc)
	status_list = svnc.status(path, get_all=False, update=True)
	status_list_known = []
	for status in status_list:
		if status.entry:
			status_list_known.append(status)
	if len(status_list_known) > 0:
		raise RezReleaseError("'" + path + "' is not in a state to release - you may need to " + \
			"svn-checkin and/or svn-update: " + str(status_list_known))

	# do an update
	print("rez-release: svn-updating...")
	svnc.update(path)

	tags_url = base_url + "/tags"
	latest_tag = []
	latest_tag_str = ''
	changeLog = ''

	tag_url = tags_url + '/' + str(this_version)

	# check that this tag does not already exist
	if svn_url_exists(svnc, tag_url):
		raise RezReleaseError("cannot release: the tag '" + tag_url + "' already exists in svn." + \
			" You may need to up your version, svn-checkin and try again.")

	# find latest tag, if it exists. Get the changelog at the same time.
	pret = subprocess.Popen("rez-svn-changelog", stdout=subprocess.PIPE, stderr=subprocess.PIPE)
	changeLog, changeLog_err = pret.communicate()

	if (pret.returncode == 0) and (not allow_not_latest):
		last_tag_str = changeLog.splitlines()[0].split()[-1].replace('/',' ').replace(':',' ').split()[-1]
		if (last_tag_str != "(NONE)") and (last_tag_str[0] != 'v'):
			# make sure our version is newer than the last tagged release
			last_tag_version = versions.Version(last_tag_str)
			if this_version <= last_tag_version:
				raise RezReleaseError("cannot release: current version '" + metadata.version + \
					"' is not greater than the latest tag '" + last_tag_str + \
					"'. You may need to up your version, svn-checkin and try again.")

	# create base dir to do clean builds from
	base_dir = os.getcwd() + "/build/rez-release"
	pret = subprocess.Popen("rm -rf " + base_dir, shell=True)
	pret.communicate()
	pret = subprocess.Popen("mkdir -p " + base_dir, shell=True)
	pret.communicate()

	# write the changelog to file, so that rez-build can install it as metadata
	changelogFile = os.getcwd() + '/build/rez-release-changelog.txt'
	chlogf = open(changelogFile, 'w')
	chlogf.write(changeLog)
	chlogf.close()

	# svn-export each variant out to a clean directory, and build it locally. If any
	# builds fail then this release is aborted
	varnum = -1
	variants = metadata.get_variants()
	variants_ = variants
	varname = "project"

	if not variants:
		variants_ = [ None ]
		varnum = ''
		vararg = ''

	print
	print("---------------------------------------------------------")
	print("rez-release: building...")
	print("---------------------------------------------------------")

	# take note of the current time, and use it as the build time for all variants. This ensures
	# that all variants will find the same packages, in case some new packages are released
	# during the build.
	if str(build_time) == "0":
		build_time = subprocess.Popen("date +%s", stdout=subprocess.PIPE, shell=True).communicate()[0]
		build_time = build_time.strip()

	timearg = "-t " + str(build_time)

	for variant in variants_:
		if variant:
			varnum += 1
			varname = "project variant #" + str(varnum)
			vararg = "-v " + str(varnum)

		subdir = base_dir + '/' + str(varnum) + '/'
		print
		print("rez-release: svn-exporting clean copy of " + varname + " to " + subdir + "...")

		# remove subdir in case it already exists
		pret = subprocess.Popen("rm -rf " + subdir, shell=True)
		pret.communicate()
		if (pret.returncode != 0):
			raise RezReleaseError("rez-release: deletion of '" + subdir + "' failed")

		# svn-export it. pysvn is giving me some false assertion crap on 'is_canonical(path)' here, hence shell
		pret = subprocess.Popen(["svn","export",this_url,subdir])
		pret.communicate()
		if (pret.returncode != 0):
			raise RezReleaseError("rez-release: svn export failed")

		# build it
		build_cmd = "rez-build" + \
			" " + timearg + \
			" " + vararg + \
			" -s " + tag_url + \
			" -c " + changelogFile + \
			" -- -- -j" + str(njobs)

		print
		print("rez-release: building " + varname + " in " + subdir + "...")
		print("rez-release: invoking: " + build_cmd)

		build_cmd = "cd " + subdir + " ; " + build_cmd
		pret = subprocess.Popen(build_cmd, shell=True)
		pret.communicate()
		if (pret.returncode != 0):
			raise RezReleaseError("rez-release: build failed")

	# now install the variants
	varnum = -1

	if not variants:
		variants_ = [ None ]
		varnum = ''
		vararg = ''

	print
	print("---------------------------------------------------------")
	print("rez-release: installing...")
	print("---------------------------------------------------------")

	# create the package.uuid file, if it doesn't exist
	if not package_uuid_exists:
		pret = subprocess.Popen("mkdir -p " + package_uuid_dir, shell=True)
		pret.wait()

		pret = subprocess.Popen("echo " + metadata.uuid + " > " + package_uuid_file, \
			stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
		pret.communicate()

	# install the variants
	for variant in variants_:
		if variant:
			varnum += 1
			varname = "project variant #" + str(varnum)
			vararg = "-v " + str(varnum)

		subdir = base_dir + '/' + str(varnum) + '/'

		# determine install path
		pret = subprocess.Popen("cd " + subdir + " ; rez-build -i " + vararg, \
			stdout=subprocess.PIPE, shell=True)
		instpath, instpath_err = pret.communicate()
		if (pret.returncode != 0):
			raise RezReleaseError("rez-release: install failed!! A partial central installation may " + \
				"have resulted, please see to this immediately - it should probably be removed.")
		instpath = instpath.strip()

		print
		print("rez-release: installing " + varname + " from " + subdir + " to " + instpath + "...")

		# run rez-build, and:
		# * manually specify the svn-url to write into metadata;
		# * manually specify the changelog file to use
		# these steps are needed because the code we're building has been svn-exported, thus
		# we don't have any svn context.
		pret = subprocess.Popen("cd " + subdir + " ; rez-build -n" + \
			" " + timearg + \
			" " + vararg + \
			" -s " + tag_url + \
			" -c " + changelogFile + \
			" -- -c -- install", shell=True)

		pret.wait()
		if (pret.returncode != 0):
			raise RezReleaseError("rez-release: install failed!! A partial central installation may " + \
				"have resulted, please see to this immediately - it should probably be removed.")

		# Prior to locking down the installation, remove any .pyc files that may have been spawned
		pret = subprocess.Popen("cd " + instpath + " ; rm -f `find -type f | grep '\.pyc$'`", shell=True)
		pret.wait()

		# Remove write permissions from all installed files.
		pret = subprocess.Popen("cd " + instpath + " ; chmod a-w `find -type f | grep -v '\.metadata'`", shell=True)
		pret.wait()

		# Remove write permissions on dirs that contain py files
		pret = subprocess.Popen("cd " + instpath + " ; find -name '*.py'", shell=True, stdout=subprocess.PIPE)
		cmdout, cmderr = pret.communicate()
		if len(cmdout.strip()) > 0:
			pret = subprocess.Popen("cd " + instpath + " ; chmod a-w `find -name '*.py' | xargs -n 1 dirname | sort | uniq`", shell=True)
			pret.wait()

	if (commit_message != None):
		commit_message += '\n' + changeLog
	else:
		# prompt for tag comment, automatically setting to the change-log
		commit_message = "\n\n" + changeLog

		tmpf = base_dir + '/' + RELEASE_COMMIT_FILE
		f = open(tmpf, 'w')
		f.write(commit_message)
		f.close()

		pret = subprocess.Popen(editor + " " + tmpf, shell=True)
		pret.wait()
		if (pret.returncode == 0):
			# if commit file was unchanged, then give a chance to abort the release
			new_commit_message = open(tmpf).read()
			if (new_commit_message == commit_message):
				pret = subprocess.Popen( \
					'read -p "Commit message unchanged - (a)bort or (c)ontinue? "' + \
					' ; if [ "$REPLY" != "c" ]; then exit 1 ; fi', shell=True)
				pret.wait()
				if (pret.returncode != 0):
					print("release aborted by user")
					pret = subprocess.Popen("rm -f " + tmpf, shell=True)
					pret.wait()
					sys.exit(1)

			commit_message = new_commit_message

		pret = subprocess.Popen("rm -f " + tmpf, shell=True)
		pret.wait()

	print
	print("---------------------------------------------------------")
	print("rez-release: tagging...")
	print("---------------------------------------------------------")
	print

	# at this point all variants have built and installed successfully. Copy to the new tag
	print("rez-release: creating project tag in: " + tag_url + "...")
	svnc.callback_get_log_message = SvnValueCallback(commit_message)

	svnc.copy2([ (this_url,) ], \
		tag_url, make_parents=True )

	# the very last thing we do is write out the current date-time to a metafile. This is
	# used by rez to specify when a package 'officially' comes into existence.
	this_pkg_release_path = pkg_release_path + '/' + metadata.name + '/' + metadata.version
	time_metafile = this_pkg_release_path + '/.metadata/release_time.txt'
	timef = open(time_metafile, 'w')
	time_epoch = int(time.mktime(time.localtime()))
	timef.write(str(time_epoch) + '\n')
	timef.close()

	# email
	usr = os.getenv("USER", "unknown.user")
	pkgname = "%s-%s" % (metadata.name, str(this_version))
	subject = "[rez] [release] %s released %s" % (usr, pkgname)
	if len(variants_) > 1:
		subject += " (%d variants)" % len(variants_)
	rrb.send_release_email(subject, commit_message)

	print
	print("rez-release: your package was released successfully.")
	print




##############################################################################
# Utilities
##############################################################################

class SvnValueCallback:
	"""
	simple functor class
	"""
	def __init__(self, value):
		self.value = value
	def __call__(self):
		return True, self.value


def svn_url_exists(client, url):
	"""
	return True if the svn url exists
	"""
	try:
		svnlist = client.info2(url, recurse = False)
		return len( svnlist ) > 0
	except pysvn.ClientError:
		return False


def get_last_changed_revision(client, url):
	"""
	util func, get last revision of url
	"""
	try:
		svn_entries = client.info2(url, pysvn.Revision(pysvn.opt_revision_kind.head), recurse=False)
		if len(svn_entries) == 0:
			raise RezReleaseError("svn.info2() returned no results on url '" + url + "'")
		return svn_entries[0][1].last_changed_rev
	except pysvn.ClientError, ce:
		raise RezReleaseError("svn.info2() raised ClientError: %s"%ce)


def getSvnLogin(realm, username, may_save):
	"""
	provide svn with permissions. @TODO this will have to be updated to take
	into account automated releases etc.
	"""
	import getpass

	print "svn requires a password for the user '" + username + "':"
	pwd = ''
	while(pwd.strip() == ''):
		pwd = getpass.getpass("--> ")

	return True, username, pwd, False














#    Copyright 2008-2012 Dr D Studios Pty Limited (ACN 127 184 954) (Dr. D Studios)
#
#    This file is part of Rez.
#
#    Rez is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Lesser General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
#
#    Rez is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU Lesser General Public License
#    along with Rez.  If not, see <http://www.gnu.org/licenses/>.

########NEW FILE########
__FILENAME__ = rez_release_base
# todo rewrite svn/git rez-release and move reused code into this file

import os
import sys
import smtplib
from email.mime.text import MIMEText


def send_release_email(subject, body):
    from_ = os.getenv("REZ_RELEASE_EMAIL_FROM", "rez")
    to_ = os.getenv("REZ_RELEASE_EMAIL_TO")
    if not to_:
        return
    recipients = to_.replace(':',' ').replace(';',' ').replace(',',' ')
    recipients = recipients.strip().split()
    if not recipients:
        return

    print
    print("---------------------------------------------------------")
    print("rez-release: sending notification emails...")
    print("---------------------------------------------------------")
    print
    print "sending to:\n%s" % str('\n').join(recipients)

    smtphost = os.getenv("REZ_RELEASE_EMAIL_SMTP_HOST", "localhost")
    smtpport = os.getenv("REZ_RELEASE_EMAIL_SMTP_PORT")

    msg = MIMEText(body)
    msg["Subject"] = subject
    msg["From"] = from_
    msg["To"] = str(',').join(recipients)

    try:
        s = smtplib.SMTP(smtphost, smtpport)
        s.sendmail(from_, recipients, msg.as_string())
        print 'email(s) sent.'
    except Exception as e:
        print  >> sys.stderr, "Emailing failed: %s" % str(e)

########NEW FILE########
__FILENAME__ = rez_release_git
"""
rez-release-git

A tool for releasing rez - compatible projects centrally. This version uses git for version control.
"""

import sys
import os
import time
import re
import git
import subprocess
from rez_metafile import *
import rez_release_base as rrb
import versions


##############################################################################
# Exceptions
##############################################################################

class RezReleaseError(Exception):
	def __init__(self, value):
		self.value = value
	def __str__(self):
		return str(self.value)


##############################################################################
# Globals
##############################################################################

REZ_RELEASE_PATH_ENV_VAR = 		"REZ_RELEASE_PACKAGES_PATH"
EDITOR_ENV_VAR		 	= 		"REZ_RELEASE_EDITOR"
RELEASE_COMMIT_FILE 	= 		"rez-release-git-commit.tmp"


##############################################################################
# Public Functions
##############################################################################


def release_from_path(path, commit_message, njobs, build_time, allow_not_latest):
	"""
	release a package from the given path on disk, copying to the relevant tag,
	and performing a fresh build before installing it centrally. If 'commit_message'
	is None, then the user will be prompted for input using the editor specified
	by $REZ_RELEASE_EDITOR.
	path: filepath containing the project to be released
	commit_message: None, or message string to write to svn, along with changelog
	njobs: number of threads to build with; passed to make via -j flag
	build_time: epoch time to build at. If 0, use current time
	allow_not_latest: if True, allows for releasing a tag that is not > the latest tag version
	"""
	# check for ./package.yaml
	if not os.access(path + "/package.yaml", os.F_OK):
		raise RezReleaseError(path + "/package.yaml not found")

	# check we're in an git repository
	try:
		repo = git.Repo(path, odbt=git.GitCmdObjectDB)
	except git.exc.InvalidGitRepositoryError:
		raise RezReleaseError("'" + path + "' is not a git repository")
	# and that it is not bare
	if repo.bare:
		raise RezReleaseError("'" + path + "' is a bare git repository")

	# check that ./package.yaml is under git control
	# in order to do that we get the current head
	try:
		repo.head.reference.commit.tree["package.yaml"]
	except KeyError:
		raise RezReleaseError(path + "/package.yaml is not under source control")

	if (commit_message == None):
		# get preferred editor for commit message
		editor = os.getenv(EDITOR_ENV_VAR)
		if not editor:
			raise RezReleaseError("rez-release: $" + EDITOR_ENV_VAR + " is not set.")

	# load the package metadata
	metadata = ConfigMetadata(path + "/package.yaml")
	if (not metadata.version):
		raise RezReleaseError(path + "/package.yaml does not specify a version")
	try:
		this_version = versions.Version(metadata.version)
	except VersionError:
		raise RezReleaseError(path + "/package.yaml contains illegal version number")

	# metadata must have name
	if not metadata.name:
		raise RezReleaseError(path + "/package.yaml is missing name")

	# metadata must have uuid
	if not metadata.uuid:
		raise RezReleaseError(path + "/package.yaml is missing uuid")

	# metadata must have description
	if not metadata.description:
		raise RezReleaseError(path + "/package.yaml is missing a description")

	# metadata must have authors
	if not metadata.authors:
		raise RezReleaseError(path + "/package.yaml is missing authors")

	pkg_release_path = os.getenv(REZ_RELEASE_PATH_ENV_VAR)
	if not pkg_release_path:
		raise RezReleaseError("$" + REZ_RELEASE_PATH_ENV_VAR + " is not set.")

	# check uuid against central uuid for this package family, to ensure that
	# we are not releasing over the top of a totally different package due to naming clash
	existing_uuid = None
	package_uuid_dir = pkg_release_path + '/' + metadata.name
	package_uuid_file = package_uuid_dir + "/package.uuid"
	package_uuid_exists = True

	try:
		existing_uuid = open(package_uuid_file).read().strip()
	except Exception:
		package_uuid_exists = False
		existing_uuid = metadata.uuid

	if(existing_uuid != metadata.uuid):
		raise RezReleaseError("the uuid in '" + package_uuid_file + \
			"' does not match this package's uuid - you may have a package name clash. All package " + \
			"names must be unique.")

	base_url = path

	# check we're in a state to release (no modified/out-of-date files, and that we are 0 commits ahead of the remote etc)
	if repo.is_dirty() or git_ahead_of_remote(repo):
		raise RezReleaseError("'" + path + "' is not in a state to release - you may need to " + \
			"git commit and/or git push and/or git pull:\n" + repo.git.status())

	# do a pull, at the moment we assume everything is in order (default remotes and branches set up)
	# to just be able to run 'git pull'
	print("rez-release: git-pulling...")
	repo.remote().pull()

	latest_tag = []
	latest_tag_str = ''
	changeLog = ''

	tag_id = str(this_version)

	# check that this tag does not already exist
	try:
		# if this doesn't raise IndexError, then tag_id already exists
		tag = repo.tags[tag_id]
		raise RezReleaseError("cannot release: the tag '" + tag_id + "' already exists in git." + \
			" You may need to up your version, git-commit and try again.")
	except IndexError, e:
		# tag does not exist, so we can just continue
		pass

	# find latest tag, if it exists. Get the changelog at the same time.
	pret = subprocess.Popen("rez-git-changelog", stdout=subprocess.PIPE, stderr=subprocess.PIPE)
	changeLog, changeLog_err = pret.communicate()

	if (pret.returncode == 0) and (not allow_not_latest):
		last_tag_str = changeLog.splitlines()[0].split()[-1].replace('/',' ').replace(':',' ').split()[-1]
		if (last_tag_str != "(NONE)") and (last_tag_str[0] != 'v'):
			# make sure our version is newer than the last tagged release
			last_tag_version = versions.Version(last_tag_str)
			if this_version <= last_tag_version:
				raise RezReleaseError("cannot release: current version '" + metadata.version + \
					"' is not greater than the latest tag '" + last_tag_str + \
					"'. You may need to up your version, git-commit and try again.")

	# create base dir to do clean builds from
	base_dir = os.getcwd() + "/build/rez-release"
	pret = subprocess.Popen("rm -rf " + base_dir, shell=True)
	pret.communicate()
	pret = subprocess.Popen("mkdir -p " + base_dir, shell=True)
	pret.communicate()

	# write the changelog to file, so that rez-build can install it as metadata
	changelogFile = os.getcwd() + '/build/rez-release-changelog.txt'
	chlogf = open(changelogFile, 'w')
	chlogf.write(changeLog)
	chlogf.close()

	# git checkout-index (analogous to svn-export) each variant out to a clean directory, and build it locally. If any
	# builds fail then this release is aborted
	varnum = -1
	variants = metadata.get_variants()
	variants_ = variants
	varname = "project"

	if not variants:
		variants_ = [ None ]
		varnum = ''
		vararg = ''

	print
	print("---------------------------------------------------------")
	print("rez-release: building...")
	print("---------------------------------------------------------")

	# take note of the current time, and use it as the build time for all variants. This ensures
	# that all variants will find the same packages, in case some new packages are released
	# during the build.
	if str(build_time) == "0":
		build_time = subprocess.Popen("date +%s", stdout=subprocess.PIPE, shell=True).communicate()[0]
		build_time = build_time.strip()

	timearg = "-t " + str(build_time)

	tag_url = repo.remote().url + "#" + repo.active_branch.tracking_branch().name.split("/")[-1] \
		+ "#" + repo.head.reference.commit.hexsha + "#(refs/tags/" + tag_id + ")"

	for variant in variants_:
		if variant:
			varnum += 1
			varname = "project variant #" + str(varnum)
			vararg = "-v " + str(varnum)

		subdir = base_dir + '/' + str(varnum) + '/'
		print
		print("rez-release: git-exporting (checkout-index) clean copy of " + varname + " to " + subdir + "...")

		# remove subdir in case it already exists
		pret = subprocess.Popen("rm -rf " + subdir, shell=True)
		pret.communicate()
		if (pret.returncode != 0):
			raise RezReleaseError("rez-release: deletion of '" + subdir + "' failed")

		# git checkout-index it
		try:
			repo.git.checkout_index(a=True, prefix=subdir)
			# We might have submodules, so we have to recursively visit each submodule and do a checkout-index
			# for that submodule as well
			git_checkout_index_submodules(varname, repo.submodules, subdir)
		except Exception, e:
			raise RezReleaseError("rez-release: git checkout-index failed: " + str(e))

		# build it
		build_cmd = "rez-build" + \
			" " + timearg + \
			" " + vararg + \
			" -s '" + tag_url + \
			"' -c " + changelogFile + \
			" -- -- -j" + str(njobs)

		print
		print("rez-release: building " + varname + " in " + subdir + "...")
		print("rez-release: invoking: " + build_cmd)

		build_cmd = "cd " + subdir + " ; " + build_cmd
		pret = subprocess.Popen(build_cmd, shell=True)
		pret.communicate()
		if (pret.returncode != 0):
			raise RezReleaseError("rez-release: build failed")

	# now install the variants
	varnum = -1

	if not variants:
		variants_ = [ None ]
		varnum = ''
		vararg = ''

	print
	print("---------------------------------------------------------")
	print("rez-release: installing...")
	print("---------------------------------------------------------")

	# create the package.uuid file, if it doesn't exist
	if not package_uuid_exists:
		pret = subprocess.Popen("mkdir -p " + package_uuid_dir, shell=True)
		pret.wait()

		pret = subprocess.Popen("echo " + metadata.uuid + " > " + package_uuid_file, \
			stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
		pret.communicate()

	# install the variants
	for variant in variants_:
		if variant:
			varnum += 1
			varname = "project variant #" + str(varnum)
			vararg = "-v " + str(varnum)

		subdir = base_dir + '/' + str(varnum) + '/'

		# determine install path
		pret = subprocess.Popen("cd " + subdir + " ; rez-build -i " + vararg, \
			stdout=subprocess.PIPE, shell=True)
		instpath, instpath_err = pret.communicate()
		if (pret.returncode != 0):
			raise RezReleaseError("rez-release: install failed!! A partial central installation may " + \
				"have resulted, please see to this immediately - it should probably be removed.")
		instpath = instpath.strip()

		print
		print("rez-release: installing " + varname + " from " + subdir + " to " + instpath + "...")

		# run rez-build, and:
		# * manually specify the git-url to write into metadata;
		# * manually specify the changelog file to use
		# these steps are needed because the code we're building has been git-exported, thus
		# we don't have any git context.
		# we use # instead of spaces in tag_url since rez-build doesn't like parameters with spaces in them,
		# even if it is enclosed in quotes. The # should be changed to spaces once the issue in rez-build is
		# resolved.
		pret = subprocess.Popen("cd " + subdir + " ; rez-build -n" + \
			" " + timearg + \
			" " + vararg + \
			" -s '" + tag_url + \
			"' -c " + changelogFile + \
			" -- -c -- install", shell=True)

		pret.wait()
		if (pret.returncode != 0):
			raise RezReleaseError("rez-release: install failed!! A partial central installation may " + \
				"have resulted, please see to this immediately - it should probably be removed.")

		# Prior to locking down the installation, remove any .pyc files that may have been spawned
		pret = subprocess.Popen("cd " + instpath + " ; rm -f `find -type f | grep '\.pyc$'`", shell=True)
		pret.wait()

		# Remove write permissions from all installed files.
		pret = subprocess.Popen("cd " + instpath + " ; chmod a-w `find -type f | grep -v '\.metadata'`", shell=True)
		pret.wait()

		# Remove write permissions on dirs that contain py files
		pret = subprocess.Popen("cd " + instpath + " ; find -name '*.py'", shell=True, stdout=subprocess.PIPE)
		cmdout, cmderr = pret.communicate()
		if len(cmdout.strip()) > 0:
			pret = subprocess.Popen("cd " + instpath + " ; chmod a-w `find -name '*.py' | xargs -n 1 dirname | sort | uniq`", shell=True)
			pret.wait()

	tmpf = base_dir + '/' + RELEASE_COMMIT_FILE
	f = open(tmpf, 'w')
	if (commit_message != None):
		commit_message += '\n' + changeLog
		f.write(commit_message)
		f.close()
	else:
		# prompt for tag comment, automatically setting to the change-log
		commit_message = "\n\n" + changeLog

		f.write(commit_message)
		f.close()

		pret = subprocess.Popen(editor + " " + tmpf, shell=True)
		pret.wait()
		if (pret.returncode == 0):
			# if commit file was unchanged, then give a chance to abort the release
			new_commit_message = open(tmpf).read()
			if (new_commit_message == commit_message):
				pret = subprocess.Popen( \
					'read -p "Commit message unchanged - (a)bort or (c)ontinue? "' + \
					' ; if [ "$REPLY" != "c" ]; then exit 1 ; fi', shell=True)
				pret.wait()
				if (pret.returncode != 0):
					print("release aborted by user")
					pret = subprocess.Popen("rm -f " + tmpf, shell=True)
					pret.wait()
					sys.exit(1)

			commit_message = new_commit_message

	print
	print("---------------------------------------------------------")
	print("rez-release: tagging...")
	print("---------------------------------------------------------")
	print

	remote = repo.remote()
	# at this point all variants have built and installed successfully. Copy to the new tag
	print("rez-release: creating project tag: " + tag_id + " and pushing to: " + remote.url + "...")

	repo.create_tag(tag_id, a=True, F=tmpf)
	# delete the temp commit message file
	pret = subprocess.Popen("rm -f " + tmpf, shell=True)
	pret.wait()

	# git-push any changes to the remote
	push_result = remote.push()
	if len(push_result) == 0:
		print("failed to push to remote, you have to run 'git push' manually.")
	# git-push the new tag to the remote
	push_result = remote.push(tags=True)
	if len(push_result) == 0:
		print("failed to push the new tag to the remote, you have to run 'git push --tags' manually.")

	# the very last thing we do is write out the current date-time to a metafile. This is
	# used by rez to specify when a package 'officially' comes into existence.
	this_pkg_release_path = pkg_release_path + '/' + metadata.name + '/' + metadata.version
	time_metafile = this_pkg_release_path + '/.metadata/release_time.txt'
	timef = open(time_metafile, 'w')
	time_epoch = int(time.mktime(time.localtime()))
	timef.write(str(time_epoch) + '\n')
	timef.close()

	# email
	usr = os.getenv("USER", "unknown.user")
	pkgname = "%s-%s" % (metadata.name, str(this_version))
	subject = "[rez] [release] %s released %s" % (usr, pkgname)
	if len(variants_) > 1:
		subject += " (%d variants)" % len(variants_)
	rrb.send_release_email(subject, commit_message)

	print
	print("rez-release: your package was released successfully.")
	print




##############################################################################
# Utilities
##############################################################################

def git_ahead_of_remote(repo):
	"""
	Checks that the git repo (git.Repo instance) is
	not ahead of its configured remote. Specifically we
	check that the message that git status returns does not
	contain "# Your branch is ahead of '[a-zA-Z/]+' by \d+ commit"
	"""
	status_message = repo.git.status()
	return re.search(r"# Your branch is ahead of '.+' by \d+ commit", status_message) != None

def git_checkout_index_submodules(varname, submodules, subdir):
	"""
	Recursively runs checkout-index on each submodule and its submodules and so forth,
	duplicating the submodule directory tree in subdir
	varname - The name of the current variant
	submodules - Iterable list of submodules
	subdir - The target base directory that should contain each
			 of the checkout-indexed submodules
	"""
	for submodule in submodules:
		submodule_subdir = os.path.join(subdir, submodule.path) + os.sep
		if not os.path.exists(submodule_subdir):
			os.mkdir(submodule_subdir)
		submodule_repo = git.Repo(submodule.abspath)
		print("rez-release: git-exporting (checkout-index) clean copy of " + varname + " (submodule: " + submodule.path + ") to " + submodule_subdir + "...")
		submodule_repo.git.checkout_index(a=True, prefix=submodule_subdir)
		# Recurse
		git_checkout_index_submodules(varname, submodule_repo.submodules, submodule_subdir)












#    Copyright 2012 BlackGinger Pty Ltd (Cape Town, South Africa)
#
#    Copyright 2008-2012 Dr D Studios Pty Limited (ACN 127 184 954) (Dr. D Studios)
#
#    This file is part of Rez.
#
#    Rez is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Lesser General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
#
#    Rez is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU Lesser General Public License
#    along with Rez.  If not, see <http://www.gnu.org/licenses/>.

########NEW FILE########
__FILENAME__ = rez_util
"""
Misc useful stuff.
"""

def gen_dotgraph_image(dot_data, out_file):

    # shortcut if writing .dot file
    if out_file.endswith(".dot"):
        with open(out_file, 'w') as f:
            f.write(dot_data)
        return

    import pydot
    graph = pydot.graph_from_dot_data(dot_data)

    # assume write format from image extension
    ext = "jpg"
    if(out_file.rfind('.') != -1):
        ext = out_file.split('.')[-1]

    try:
        fn = getattr(graph, "write_"+ext)
    except Exception:
        sys.stderr.write("could not write to '" + out_file + "': unknown format specified")
        sys.exit(1)

    fn(out_file)


def readable_time_duration(secs, approx=True):
    divs = ((24*60*60, "days"), (60*60, "hours"), (60, "minutes"), (1, "seconds"))

    if secs == 0:
        return "0 seconds"
    neg = (secs < 0)
    if neg:
        secs = -secs

    if approx:
        for i,s in enumerate([x[0] for x in divs[:-1]]):
            ss = float(s) * 0.9
            if secs >= ss:
                n = secs / s
                frac = float((secs+s) % s) / float(s)
                if frac < 0.1:
                    secs = n * s
                elif frac > 0.9:
                    secs = (n+1) * s
                else:
                    s2 = divs[i+1][0]
                    secs -= secs % s2
                break

    toks = []
    for d in divs:
        if secs >= d[0]:
            n = secs/d[0]
            count = n*d[0]
            label = d[1]
            if n == 1:
                label = label[:-1]
            toks.append((n, label))
            secs -= count

    s = str(", ").join([("%d %s" % (x[0],x[1])) for x in toks])
    if neg:
        s = '-' + s
    return s

########NEW FILE########
__FILENAME__ = sigint

import sys
import signal

# exit gracefully on ctrl-C
def sigint_handler(signum, frame):
	sys.stderr.write('\nInterrupted by user\n')
	sys.exit(1)

signal.signal(signal.SIGINT, sigint_handler)

#    Copyright 2008-2012 Dr D Studios Pty Limited (ACN 127 184 954) (Dr. D Studios)
#
#    This file is part of Rez.
#
#    Rez is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Lesser General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
#
#    Rez is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU Lesser General Public License
#    along with Rez.  If not, see <http://www.gnu.org/licenses/>.

########NEW FILE########
__FILENAME__ = versions
"""
This module contains classes which operate on version strings. Example version strings include:
'', '1', '1.2.3', '3.5+', '3.5+<4', '10.5|11.2', '10.5|11+', '1.2.a'.
Character components are allowed, and are ordered alphabetically, ie '1.b' > '1.a', however if
a component is a valid number then it is treated numerically, not alphabetically. Only single
characters 'a'-'z' are allowed.

Operations such as unions and intersections are possible. For example, the version '10.5' is
considered the superset of any version of the form '10.5.x', so union(10.5, 10.5.4) would be
'10.5'.

A single version string can describe sets of disparate version ranges - for example, '10.5|5.4|7'.
A version is said to be 'inexact' if it definitely describes a range of versions, for example
'4.5+', '1.0|2.0', '', '4.5+<5.0'. A version string is never said to be 'exact', because whether
this is true depends on context - for example the version '10.5' may represent an exact version
in one case, but may represent the superset of all versions '10.5.x' in another.
"""

import re


class VersionError(Exception):
	"""
	Exception
	"""
	def __init__(self, value=None):
		self.value = value
	def __str__(self):
		return "Invalid version: %s" % self.value

class Version:
	"""
	A version string. Note that disparate version ranges (separated with '|'s) are not supported -
	use a VersionRange for this.
	"""

	INF 	= [  999999 ]
	NEG_INF = [ -999999 ]
	valid_char = re.compile("^[a-z]$")

	def __init__(self, version_str=None, ge_lt=None):
		if version_str:
			try:
				version_str = str(version_str)
			except UnicodeEncodeError:
				raise VersionError("Non-ASCII characters in version string")

			rangepos = version_str.find("+<")
			if (rangepos == -1):
				plus = version_str.endswith('+')
				tokens = version_str.rstrip('+').replace('-', '.').split('.')
				self.ge = []
				for tok in tokens:
					self.to_comp(tok, version_str)

				if plus:
					self.lt = Version.INF
				else:
					self.lt = self.get_ge_plus_one()

				if len(self.ge) == 0:
					self.ge = Version.NEG_INF

			else:
				v1 = Version(version_str[:rangepos])
				v2 = Version(version_str[rangepos+2:])
				self.ge = v1.ge
				self.lt = v2.ge

				# remove trailing zeros on lt bound (think: 'A < 1.0.0' == 'A < 1')
				# this also makes this version invalid: '1+<1.0.0'
				while (len(self.lt) > 1) and (self.lt[-1] == 0):
					self.lt.pop()

				if self.lt <= self.ge:
					raise VersionError("lt<=ge: "+version_str)
		elif ge_lt:
			self.ge = ge_lt[0][:]
			self.lt = ge_lt[1][:]
		else:
			self.ge = Version.NEG_INF
			self.lt = Version.INF

	def copy(self):
		return Version(ge_lt=(self.ge, self.lt))

	def to_comp(self, tok, version_str):
		if len(tok) == 0:
			raise VersionError(version_str)

		if (tok[0] == '0') and (tok != '0'):  # zero-padding is not allowed, eg '03'
			raise VersionError(version_str)

		try:
			i = int(tok)
			if i < 0:
				raise VersionError("Can't have negative components: "+version_str)
			self.ge.append(i)
		except ValueError:
			if self.is_tok_single_letter(tok):
				self.ge.append(tok)
			else:
				raise VersionError("Invalid version '%s'" % version_str)

	def is_tok_single_letter(self, tok):
		return Version.valid_char.match(tok) is not None

	def get_ge_plus_one(self):
		if len(self.ge) == 0:
			return Version.INF
		if self.ge == Version.NEG_INF:
			return Version.INF
		v = self.ge[:]
		v.append(self.inc_comp(v.pop()))
		return v

	def is_inexact(self):
		"""
		Return true if version is inexact. !is_inexact does not imply exact - for
		eg, the version '10.5' may refer to any version of '10.5.x'.
		"""
		if len(self.lt)==0 and len(self.ge)==0:
			return True
		return self.lt != self.get_ge_plus_one()

	def is_any(self):
		"""
		Return true if version is 'any', ie was created from an empty string
		"""
		return self.ge == Version.NEG_INF and self.lt == Version.INF

	def inc_comp(self,comp):
		"""
		increment a number or single character by 1
		"""
		if type(comp) == type(1):
			return comp + 1
		else:
			return chr(ord(comp) + 1)

	def contains_version(self, ge):
		"""
		Returns True if the exact version ge (eg 1.0.0) is contained within this range.
		"""
		return (ge >= self.ge) and (ge < self.lt)

	def get_union(self, ver):
		"""
		Return new version(s) representing the union of this and another version.
		The result may be more than one version, so a version list is returned.
		"""
		if self.ge >= ver.lt or self.lt <= ver.ge:
			return [ self.copy(), ver.copy() ]
		v = Version('')
		v.ge = min( [self.ge, ver.ge] )[:]
		v.lt = max( [self.lt, ver.lt] )[:]
		return [v]

	def get_intersection(self, ver):
		"""
		Return a new version representing the intersection between this and
		another version, or None if the versions do not overlap
		"""
		if ver.ge >= self.lt or ver.lt <= self.ge:
			return None

		ver_int = Version('')
		if ver.ge > self.ge:
			ver_int.ge = ver.ge[:]
		else:
			ver_int.ge = self.ge[:]
		if ver.lt < self.lt:
			ver_int.lt = ver.lt[:]
		else:
			ver_int.lt = self.lt[:]
		return ver_int

	def __str__(self):
		def get_str(parts):
			return ".".join([str(part) for part in parts])

		if self.lt == Version.INF:
			if self.ge == Version.NEG_INF:
				return ""
			else:
				return get_str(self.ge) + "+"
		elif self.is_inexact():
			return get_str(self.ge) + "+<" + get_str(self.lt)
		else:
			return get_str(self.ge)

	def __lt__(self, ver):
		"""
		less-than test. Version A is < B if A's ge bound is < B's. If the ge
		bounds are the same, the lt bounds are then tested, and A is < B if its
		lt bound is < B's.
		"""
		return self.lt < ver.lt if self.ge == ver.ge else self.ge < ver.ge

	def __eq__(self, ver):
		return self.ge == ver.ge and self.lt == ver.lt

	def __le__(self, ver):
		return self.__lt__(ver) or self.__eq__(ver)


class VersionRange:
	"""
	A collection of zero or more inexact versions, which do not overlap. If a
	VersionRange is initialised with disparate version ranges which do overlap
	(eg '10.5+|10.5.2'), these will be resolved at initialization.
	"""

	def __init__(self, v="", _versions=None):
		if _versions:
			self.versions = [x.copy() for x in _versions]
		else:
			# just make sure it's a string, because sometimes we pass in a Version instance
			version_str = str(v)
			version_strs = version_str.split("|")
			versions = []
			for vstr in version_strs:
				versions.append(Version(vstr))

			self.versions = get_versions_union(versions)

	def copy(self):
		return VersionRange(_versions=self.versions)

	def contains_version(self, ge):
		"""
		Returns True if the exact version ge (eg 1.0.0) is contained within this range.
		"""
		for ver in self.versions:
			if ver.contains_version(ge):
				return True
		return False

	def get_union(self, vers):
		"""
		get union
		"""
		vers_union = VersionRange('')
		vers_union.versions = get_versions_union(self.versions + vers.versions)
		vers_union.versions.sort()
		return vers_union

	def get_intersection(self, vers):
		"""
		get intersection, return None if there are no intersections
		"""
		vers_int = VersionRange('')
		vers_int.versions = []
		for ver in self.versions:
			for ver2 in vers.versions:
				vint = ver.get_intersection(ver2)
				if vint:
					vers_int.versions.append(vint)

		if (len(vers_int.versions) == 0):
			return None
		else:
			vers_int.versions.sort()
			return vers_int


	def get_inverse(self):
		"""
		get the inverse of this version range
		"""
		if self.is_any():
			vers_none = VersionRange('')
			vers_none.versions = []
			return vers_none

		# the inverse of none is any
		if self.is_none():
			return VersionRange('')

		# inverse is the ranges between existing ranges
		vers_inv = VersionRange('')
		vers_inv.versions = []

		ver_front = Version("")
		ver_front.ge = Version.NEG_INF
		ver_front.lt = [Version.NEG_INF[0] + 1]
		ver_back = Version("")
		ver_back.ge = Version.INF
		ver_back.lt = [Version.INF[0] + 1]

		vers = [ver_front] + self.versions + [ver_back]
		for i in range(0, len(vers)-1):
			v0 = vers[i]
			v1 = vers[i+1]
			if v0.lt < v1.ge:
				v = Version("")
				v.ge, v.lt = v0.lt, v1.ge
				vers_inv.versions.append(v)

		if len(vers_inv.versions) > 0:
			# clamp ge limits back to zero
			if vers_inv.versions[0].lt <= [0]:
				vers_inv.versions = vers_inv.versions[1:]

			if len(vers_inv.versions) > 0 and vers_inv.versions[0].ge < [0]:
				vers_inv.versions[0].ge = [0]
				# we may get something like this when clamping: 0+<0.0, which
				# is not valid, so detect it and remove it
				while (len(vers_inv.versions[0].lt) > 1) and (vers_inv.versions[0].lt[-1] == 0):
					vers_inv.versions[0].lt.pop()
				if vers_inv.versions[0].lt == vers_inv.versions[0].ge:
					vers_inv.versions.pop(0)

		return vers_inv

	def is_greater_no_overlap(self, ver):
		"""
		return True if the given version range is greater than this one,
		and there is no overlap
		"""
		if len(self.versions) == 0 and len(ver.versions) == 0:
			return False
		elif len(self.versions) == 0 or len(ver.versions) == 0:
			return True
		return ver.versions[0].ge >= self.versions[-1].lt

	def is_inexact(self):
		"""
		return True if the version range is inexact
		"""
		if len(self.versions) == 0:
			return False
		return (len(self.versions) > 1) or self.versions[0].is_inexact()

	def is_any(self):
		"""
		Return true if version is 'any', ie was created from an empty string
		"""
		return (len(self.versions) == 1) and self.versions[0].is_any()

	def is_none(self):
		"""
		Return true if this range describes no versions
		"""
		return len(self.versions) == 0

	def get_dim(self):
		"""
		Returns the number of distinct versions in the range
		"""
		return len(self.versions)

	def __str__(self):
		return "|".join(str(v) for v in self.versions)

	def __eq__(self, ver):
		"""
		equality test
		"""
		if ver is None:
			return False
		return self.versions == ver.versions

	def __ne__(self, ver):
		"""
		inequality test
		"""
		return not self == ver

def get_versions_union(versions):
	nvers = len(versions)
	if nvers == 0:
		return []
	elif nvers == 1:
		return [x.copy() for x in versions]
	elif nvers == 2:
		return versions[0].get_union(versions[1])
	else:
		new_versions = []
		idx = 1
		versions_tmp = sorted([x.copy() for x in versions])
		for ver1 in versions_tmp:
			overlap = False
			for ver2 in versions_tmp[idx:]:
				ver_union = ver1.get_union(ver2)
				if len(ver_union) == 1:
					ver2.ge, ver2.lt = ver_union[0].ge, ver_union[0].lt
					overlap = True
					break
			if not overlap:
				new_versions.append(ver1)
			idx += 1
		return new_versions



#    Copyright 2008-2012 Dr D Studios Pty Limited (ACN 127 184 954) (Dr. D Studios)
#
#    This file is part of Rez.
#
#    Rez is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Lesser General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
#
#    Rez is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU Lesser General Public License
#    along with Rez.  If not, see <http://www.gnu.org/licenses/>.

########NEW FILE########
__FILENAME__ = _common

def get_version():
    """
    @return The version of %(NAME)s.
    """
    return '%(VERSION)s'

########NEW FILE########
