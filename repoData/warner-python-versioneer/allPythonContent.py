__FILENAME__ = cmdclass

class cmd_version(Command):
    description = "report generated version string"
    user_options = []
    boolean_options = []
    def initialize_options(self):
        pass
    def finalize_options(self):
        pass
    def run(self):
        ver = get_version(verbose=True)
        print("Version is currently: %s" % ver)


class cmd_build(_build):
    def run(self):
        versions = get_versions(verbose=True)
        _build.run(self)
        # now locate _version.py in the new build/ directory and replace it
        # with an updated value
        target_versionfile = os.path.join(self.build_lib, versionfile_build)
        print("UPDATING %s" % target_versionfile)
        os.unlink(target_versionfile)
        with open(target_versionfile, "w") as f:
            f.write(SHORT_VERSION_PY % versions)

if 'cx_Freeze' in sys.modules:  # cx_freeze enabled?
    from cx_Freeze.dist import build_exe as _build_exe

    class cmd_build_exe(_build_exe):
        def run(self):
            versions = get_versions(verbose=True)
            target_versionfile = versionfile_source
            print("UPDATING %s" % target_versionfile)
            os.unlink(target_versionfile)
            with open(target_versionfile, "w") as f:
                f.write(SHORT_VERSION_PY % versions)

            _build_exe.run(self)
            os.unlink(target_versionfile)
            with open(versionfile_source, "w") as f:
                assert VCS is not None, "please set versioneer.VCS"
                LONG = LONG_VERSION_PY[VCS]
                f.write(LONG % {"DOLLAR": "$",
                                "TAG_PREFIX": tag_prefix,
                                "PARENTDIR_PREFIX": parentdir_prefix,
                                "VERSIONFILE_SOURCE": versionfile_source,
                                })

class cmd_sdist(_sdist):
    def run(self):
        versions = get_versions(verbose=True)
        self._versioneer_generated_versions = versions
        # unless we update this, the command will keep using the old version
        self.distribution.metadata.version = versions["version"]
        return _sdist.run(self)

    def make_release_tree(self, base_dir, files):
        _sdist.make_release_tree(self, base_dir, files)
        # now locate _version.py in the new base_dir directory (remembering
        # that it may be a hardlink) and replace it with an updated value
        target_versionfile = os.path.join(base_dir, versionfile_source)
        print("UPDATING %s" % target_versionfile)
        os.unlink(target_versionfile)
        with open(target_versionfile, "w") as f:
            f.write(SHORT_VERSION_PY % self._versioneer_generated_versions)

INIT_PY_SNIPPET = """
from ._version import get_versions
__version__ = get_versions()['version']
del get_versions
"""

class cmd_update_files(Command):
    description = "install/upgrade Versioneer files: __init__.py SRC/_version.py"
    user_options = []
    boolean_options = []
    def initialize_options(self):
        pass
    def finalize_options(self):
        pass
    def run(self):
        print(" creating %s" % versionfile_source)
        with open(versionfile_source, "w") as f:
            assert VCS is not None, "please set versioneer.VCS"
            LONG = LONG_VERSION_PY[VCS]
            f.write(LONG % {"DOLLAR": "$",
                            "TAG_PREFIX": tag_prefix,
                            "PARENTDIR_PREFIX": parentdir_prefix,
                            "VERSIONFILE_SOURCE": versionfile_source,
                            })

        ipy = os.path.join(os.path.dirname(versionfile_source), "__init__.py")
        try:
            with open(ipy, "r") as f:
                old = f.read()
        except EnvironmentError:
            old = ""
        if INIT_PY_SNIPPET not in old:
            print(" appending to %s" % ipy)
            with open(ipy, "a") as f:
                f.write(INIT_PY_SNIPPET)
        else:
            print(" %s unmodified" % ipy)

        # Make sure both the top-level "versioneer.py" and versionfile_source
        # (PKG/_version.py, used by runtime code) are in MANIFEST.in, so
        # they'll be copied into source distributions. Pip won't be able to
        # install the package without this.
        manifest_in = os.path.join(get_root(), "MANIFEST.in")
        simple_includes = set()
        try:
            with open(manifest_in, "r") as f:
                for line in f:
                    if line.startswith("include "):
                        for include in line.split()[1:]:
                            simple_includes.add(include)
        except EnvironmentError:
            pass
        # That doesn't cover everything MANIFEST.in can do
        # (http://docs.python.org/2/distutils/sourcedist.html#commands), so
        # it might give some false negatives. Appending redundant 'include'
        # lines is safe, though.
        if "versioneer.py" not in simple_includes:
            print(" appending 'versioneer.py' to MANIFEST.in")
            with open(manifest_in, "a") as f:
                f.write("include versioneer.py\n")
        else:
            print(" 'versioneer.py' already in MANIFEST.in")
        if versionfile_source not in simple_includes:
            print(" appending versionfile_source ('%s') to MANIFEST.in" %
                  versionfile_source)
            with open(manifest_in, "a") as f:
                f.write("include %s\n" % versionfile_source)
        else:
            print(" versionfile_source already in MANIFEST.in")

        # Make VCS-specific changes. For git, this means creating/changing
        # .gitattributes to mark _version.py for export-time keyword
        # substitution.
        do_vcs_install(manifest_in, versionfile_source, ipy)

def get_cmdclass():
    cmds = {'version': cmd_version,
            'versioneer': cmd_update_files,
            'build': cmd_build,
            'sdist': cmd_sdist,
            }
    if 'cx_Freeze' in sys.modules:  # cx_freeze enabled?
        cmds['build_exe'] = cmd_build_exe
        del cmds['build']

    return cmds

########NEW FILE########
__FILENAME__ = from_file

SHORT_VERSION_PY = """
# This file was generated by 'versioneer.py' (@VERSIONEER-VERSION@) from
# revision-control system data, or from the parent directory name of an
# unpacked source archive. Distribution tarballs contain a pre-generated copy
# of this file.

version_version = '%(version)s'
version_full = '%(full)s'
def get_versions(default={}, verbose=False):
    return {'version': version_version, 'full': version_full}

"""

DEFAULT = {"version": "unknown", "full": "unknown"}

def versions_from_file(filename):
    versions = {}
    try:
        with open(filename) as f:
            for line in f.readlines():
                mo = re.match("version_version = '([^']+)'", line)
                if mo:
                    versions["version"] = mo.group(1)
                mo = re.match("version_full = '([^']+)'", line)
                if mo:
                    versions["full"] = mo.group(1)
    except EnvironmentError:
        return {}

    return versions

def write_to_version_file(filename, versions):
    with open(filename, "w") as f:
        f.write(SHORT_VERSION_PY % versions)

    print("set %s to '%s'" % (filename, versions["version"]))


########NEW FILE########
__FILENAME__ = from_parentdir

def versions_from_parentdir(parentdir_prefix, root, verbose=False):
    # Source tarballs conventionally unpack into a directory that includes
    # both the project name and a version string.
    dirname = os.path.basename(root)
    if not dirname.startswith(parentdir_prefix):
        if verbose:
            print("guessing rootdir is '%s', but '%s' doesn't start with prefix '%s'" %
                  (root, dirname, parentdir_prefix))
        return None
    return {"version": dirname[len(parentdir_prefix):], "full": ""}

########NEW FILE########
__FILENAME__ = get_versions
import sys

def get_root():
    try:
        return os.path.dirname(os.path.abspath(__file__))
    except NameError:
        return os.path.dirname(os.path.abspath(sys.argv[0]))

def vcs_function(vcs, suffix):
    return getattr(sys.modules[__name__], '%s_%s' % (vcs, suffix), None)

def get_versions(default=DEFAULT, verbose=False):
    # returns dict with two keys: 'version' and 'full'
    assert versionfile_source is not None, "please set versioneer.versionfile_source"
    assert tag_prefix is not None, "please set versioneer.tag_prefix"
    assert parentdir_prefix is not None, "please set versioneer.parentdir_prefix"
    assert VCS is not None, "please set versioneer.VCS"

    # I am in versioneer.py, which must live at the top of the source tree,
    # which we use to compute the root directory. py2exe/bbfreeze/non-CPython
    # don't have __file__, in which case we fall back to sys.argv[0] (which
    # ought to be the setup.py script). We prefer __file__ since that's more
    # robust in cases where setup.py was invoked in some weird way (e.g. pip)
    root = get_root()
    versionfile_abs = os.path.join(root, versionfile_source)

    # extract version from first of _version.py, VCS command (e.g. 'git
    # describe'), parentdir. This is meant to work for developers using a
    # source checkout, for users of a tarball created by 'setup.py sdist',
    # and for users of a tarball/zipball created by 'git archive' or github's
    # download-from-tag feature or the equivalent in other VCSes.

    get_keywords_f = vcs_function(VCS, "get_keywords")
    versions_from_keywords_f = vcs_function(VCS, "versions_from_keywords")
    if get_keywords_f and versions_from_keywords_f:
        vcs_keywords = get_keywords_f(versionfile_abs)
        ver = versions_from_keywords_f(vcs_keywords, tag_prefix)
        if ver:
            if verbose: print("got version from expanded keyword %s" % ver)
            return ver

    ver = versions_from_file(versionfile_abs)
    if ver:
        if verbose: print("got version from file %s %s" % (versionfile_abs,ver))
        return ver

    versions_from_vcs_f = vcs_function(VCS, "versions_from_vcs")
    if versions_from_vcs_f:
        ver = versions_from_vcs_f(tag_prefix, root, verbose)
        if ver:
            if verbose: print("got version from VCS %s" % ver)
            return ver

    ver = versions_from_parentdir(parentdir_prefix, root, verbose)
    if ver:
        if verbose: print("got version from parentdir %s" % ver)
        return ver

    if verbose: print("got version from default %s" % default)
    return default

def get_version(verbose=False):
    return get_versions(verbose=verbose)["version"]

########NEW FILE########
__FILENAME__ = from_keywords

import re

def git_get_keywords(versionfile_abs):
    # the code embedded in _version.py can just fetch the value of these
    # keywords. When used from setup.py, we don't want to import _version.py,
    # so we do it with a regexp instead. This function is not used from
    # _version.py.
    keywords = {}
    try:
        f = open(versionfile_abs,"r")
        for line in f.readlines():
            if line.strip().startswith("git_refnames ="):
                mo = re.search(r'=\s*"(.*)"', line)
                if mo:
                    keywords["refnames"] = mo.group(1)
            if line.strip().startswith("git_full ="):
                mo = re.search(r'=\s*"(.*)"', line)
                if mo:
                    keywords["full"] = mo.group(1)
        f.close()
    except EnvironmentError:
        pass
    return keywords

def git_versions_from_keywords(keywords, tag_prefix, verbose=False):
    if not keywords:
        return {} # keyword-finding function failed to find keywords
    refnames = keywords["refnames"].strip()
    if refnames.startswith("$Format"):
        if verbose:
            print("keywords are unexpanded, not using")
        return {} # unexpanded, so not in an unpacked git-archive tarball
    refs = set([r.strip() for r in refnames.strip("()").split(",")])
    # starting in git-1.8.3, tags are listed as "tag: foo-1.0" instead of
    # just "foo-1.0". If we see a "tag: " prefix, prefer those.
    TAG = "tag: "
    tags = set([r[len(TAG):] for r in refs if r.startswith(TAG)])
    if not tags:
        # Either we're using git < 1.8.3, or there really are no tags. We use
        # a heuristic: assume all version tags have a digit. The old git %d
        # expansion behaves like git log --decorate=short and strips out the
        # refs/heads/ and refs/tags/ prefixes that would let us distinguish
        # between branches and tags. By ignoring refnames without digits, we
        # filter out many common branch names like "release" and
        # "stabilization", as well as "HEAD" and "master".
        tags = set([r for r in refs if re.search(r'\d', r)])
        if verbose:
            print("discarding '%s', no digits" % ",".join(refs-tags))
    if verbose:
        print("likely tags: %s" % ",".join(sorted(tags)))
    for ref in sorted(tags):
        # sorting will prefer e.g. "2.0" over "2.0rc1"
        if ref.startswith(tag_prefix):
            r = ref[len(tag_prefix):]
            if verbose:
                print("picking %s" % r)
            return { "version": r,
                     "full": keywords["full"].strip() }
    # no suitable tags, so we use the full revision id
    if verbose:
        print("no suitable tags, using full revision id")
    return { "version": keywords["full"].strip(),
             "full": keywords["full"].strip() }


########NEW FILE########
__FILENAME__ = from_vcs

import sys
import os.path

def git_versions_from_vcs(tag_prefix, root, verbose=False):
    # this runs 'git' from the root of the source tree. This only gets called
    # if the git-archive 'subst' keywords were *not* expanded, and
    # _version.py hasn't already been rewritten with a short version string,
    # meaning we're inside a checked out source tree.

    if not os.path.exists(os.path.join(root, ".git")):
        if verbose:
            print("no .git in %s" % root)
        return {}

    GITS = ["git"]
    if sys.platform == "win32":
        GITS = ["git.cmd", "git.exe"]
    stdout = run_command(GITS, ["describe", "--tags", "--dirty", "--always"],
                         cwd=root)
    if stdout is None:
        return {}
    if not stdout.startswith(tag_prefix):
        if verbose:
            print("tag '%s' doesn't start with prefix '%s'" % (stdout, tag_prefix))
        return {}
    tag = stdout[len(tag_prefix):]
    stdout = run_command(GITS, ["rev-parse", "HEAD"], cwd=root)
    if stdout is None:
        return {}
    full = stdout.strip()
    if tag.endswith("-dirty"):
        full += "-dirty"
    return {"version": tag, "full": full}


########NEW FILE########
__FILENAME__ = install
import os.path
import sys

def do_vcs_install(manifest_in, versionfile_source, ipy):
    GITS = ["git"]
    if sys.platform == "win32":
        GITS = ["git.cmd", "git.exe"]
    files = [manifest_in, versionfile_source, ipy]
    try:
        me = __file__
        if me.endswith(".pyc") or me.endswith(".pyo"):
            me = os.path.splitext(me)[0] + ".py"
        versioneer_file = os.path.relpath(me)
    except NameError:
        versioneer_file = "versioneer.py"
    files.append(versioneer_file)
    present = False
    try:
        f = open(".gitattributes", "r")
        for line in f.readlines():
            if line.strip().startswith(versionfile_source):
                if "export-subst" in line.strip().split()[1:]:
                    present = True
        f.close()
    except EnvironmentError:
        pass    
    if not present:
        f = open(".gitattributes", "a+")
        f.write("%s export-subst\n" % versionfile_source)
        f.close()
        files.append(".gitattributes")
    run_command(GITS, ["add", "--"] + files)

########NEW FILE########
__FILENAME__ = long_get_versions
import os

def get_versions(default={"version": "unknown", "full": ""}, verbose=False):
    # I am in _version.py, which lives at ROOT/VERSIONFILE_SOURCE. If we have
    # __file__, we can work backwards from there to the root. Some
    # py2exe/bbfreeze/non-CPython implementations don't do __file__, in which
    # case we can only use expanded keywords.

    keywords = { "refnames": git_refnames, "full": git_full }
    ver = git_versions_from_keywords(keywords, tag_prefix, verbose)
    if ver:
        return ver

    try:
        root = os.path.abspath(__file__)
        # versionfile_source is the relative path from the top of the source
        # tree (where the .git directory might live) to this file. Invert
        # this to find the root from __file__.
        for i in range(len(versionfile_source.split(os.sep))):
            root = os.path.dirname(root)
    except NameError:
        return default

    return (git_versions_from_vcs(tag_prefix, root, verbose)
            or versions_from_parentdir(parentdir_prefix, root, verbose)
            or default)

########NEW FILE########
__FILENAME__ = long_header
# This file helps to compute a version number in source trees obtained from
# git-archive tarball (such as those provided by githubs download-from-tag
# feature). Distribution tarballs (build by setup.py sdist) and build
# directories (produced by setup.py build) will contain a much shorter file
# that just contains the computed version number.

# This file is released into the public domain. Generated by
# versioneer-@VERSIONEER-VERSION@ (https://github.com/warner/python-versioneer)

# these strings will be replaced by git during git-archive
git_refnames = "%(DOLLAR)sFormat:%%d%(DOLLAR)s"
git_full = "%(DOLLAR)sFormat:%%H%(DOLLAR)s"

# these strings are filled in when 'setup.py versioneer' creates _version.py
tag_prefix = "%(TAG_PREFIX)s"
parentdir_prefix = "%(PARENTDIR_PREFIX)s"
versionfile_source = "%(VERSIONFILE_SOURCE)s"


########NEW FILE########
__FILENAME__ = header

# Version: @VERSIONEER-VERSION@

"""
@README@
"""

import os, sys, re
from distutils.core import Command
from distutils.command.sdist import sdist as _sdist
from distutils.command.build import build as _build

# these configuration settings will be overridden by setup.py after it
# imports us
versionfile_source = None
versionfile_build = None
tag_prefix = None
parentdir_prefix = None
VCS = None

# these dictionaries contain VCS-specific tools
LONG_VERSION_PY = {}

########NEW FILE########
__FILENAME__ = installer
#!/usr/bin/env python

import os, base64

VERSIONEER_b64 = """
@VERSIONEER-INSTALLER@
"""

v = base64.b64decode(VERSIONEER_b64)
if os.path.exists("versioneer.py"):
    print("overwriting existing versioneer.py")
with open("versioneer.py", "wb") as f:
    f.write(v)
print("versioneer.py (@VERSIONEER-VERSION@) installed into local tree")
print("Now please follow instructions in the docstring.")

########NEW FILE########
__FILENAME__ = subprocess_helper

import subprocess
import sys
import errno


def run_command(commands, args, cwd=None, verbose=False, hide_stderr=False):
    assert isinstance(commands, list)
    p = None
    for c in commands:
        try:
            # remember shell=False, so use git.cmd on windows, not just git
            p = subprocess.Popen([c] + args, cwd=cwd, stdout=subprocess.PIPE,
                                 stderr=(subprocess.PIPE if hide_stderr
                                         else None))
            break
        except EnvironmentError:
            e = sys.exc_info()[1]
            if e.errno == errno.ENOENT:
                continue
            if verbose:
                print("unable to run %s" % args[0])
                print(e)
            return None
    else:
        if verbose:
            print("unable to find command, tried %s" % (commands,))
        return None
    stdout = p.communicate()[0].strip()
    if sys.version >= '3':
        stdout = stdout.decode()
    if p.returncode != 0:
        if verbose:
            print("unable to run %s (error)" % args[0])
        return None
    return stdout


########NEW FILE########
__FILENAME__ = test_git
#! /usr/bin/python

import os, sys
import shutil
import tarfile
import unittest
import tempfile

sys.path.insert(0, "src")
from git.from_keywords import git_versions_from_keywords
from subprocess_helper import run_command

GITS = ["git"]
if sys.platform == "win32":
    GITS = ["git.cmd", "git.exe"]

class Keywords(unittest.TestCase):
    def parse(self, refnames, full, prefix=""):
        return git_versions_from_keywords({"refnames": refnames, "full": full},
                                          prefix)

    def test_parse(self):
        v = self.parse(" (HEAD, 2.0,master  , otherbranch ) ", " full ")
        self.assertEqual(v["version"], "2.0")
        self.assertEqual(v["full"], "full")

    def test_prefer_short(self):
        v = self.parse(" (HEAD, 2.0rc1, 2.0, 2.0rc2) ", " full ")
        self.assertEqual(v["version"], "2.0")
        self.assertEqual(v["full"], "full")

    def test_prefix(self):
        v = self.parse(" (HEAD, projectname-2.0) ", " full ", "projectname-")
        self.assertEqual(v["version"], "2.0")
        self.assertEqual(v["full"], "full")

    def test_unexpanded(self):
        v = self.parse(" $Format$ ", " full ", "projectname-")
        self.assertEqual(v, {})

    def test_no_tags(self):
        v = self.parse("(HEAD, master)", "full")
        self.assertEqual(v["version"], "full")
        self.assertEqual(v["full"], "full")

    def test_no_prefix(self):
        v = self.parse("(HEAD, master, 1.23)", "full", "missingprefix-")
        self.assertEqual(v["version"], "full")
        self.assertEqual(v["full"], "full")

VERBOSE = False

class Repo(unittest.TestCase):
    def git(self, *args, **kwargs):
        workdir = kwargs.pop("workdir", self.subpath("demoapp"))
        assert not kwargs, kwargs.keys()
        output = run_command(GITS, list(args), workdir, True)
        if output is None:
            self.fail("problem running git")
        return output
    def python(self, *args, **kwargs):
        workdir = kwargs.pop("workdir", self.subpath("demoapp"))
        assert not kwargs, kwargs.keys()
        output = run_command([sys.executable], list(args), workdir, True)
        if output is None:
            self.fail("problem running python")
        return output
    def subpath(self, path):
        return os.path.join(self.testdir, path)

    # There are three tree states we're interested in:
    #  SA: sitting on the 1.0 tag
    #  SB: dirtying the tree after 1.0
    #  SC: making a new commit after 1.0, clean tree
    #
    # Then we're interested in 5 kinds of trees:
    #  TA: source tree (with .git)
    #  TB: source tree without .git (should get 'unknown')
    #  TC: source tree without .git unpacked into prefixdir
    #  TD: git-archive tarball
    #  TE: unpacked sdist tarball
    #
    # In three runtime situations:
    #  RA1: setup.py --version
    #  RA2: ...path/to/setup.py --version (from outside the source tree)
    #  RB: setup.py build;  demoapp --version
    #
    # We can only detect dirty files in real git trees, so we don't examine
    # SB for TB/TC/TD/TE, or RB.

    def test_full(self):
        self.testdir = tempfile.mkdtemp()
        if VERBOSE: print("testdir: %s" % (self.testdir,))
        if os.path.exists(self.testdir):
            shutil.rmtree(self.testdir)

        # create an unrelated git tree above the testdir. Some tests will run
        # from this directory, and they should use the demoapp git
        # environment instead of the deceptive parent
        os.mkdir(self.testdir)
        self.git("init", workdir=self.testdir)
        f = open(os.path.join(self.testdir, "false-repo"), "w")
        f.write("don't look at me\n")
        f.close()
        self.git("add", "false-repo", workdir=self.testdir)
        self.git("commit", "-m", "first false commit", workdir=self.testdir)
        self.git("tag", "demo-4.0", workdir=self.testdir)

        shutil.copytree("test/demoapp", self.subpath("demoapp"))
        setup_py_fn = os.path.join(self.subpath("demoapp"), "setup.py")
        with open(setup_py_fn, "r") as f:
            setup_py = f.read()
        setup_py = setup_py.replace("@VCS@", "git")
        with open(setup_py_fn, "w") as f:
            f.write(setup_py)
        shutil.copyfile("versioneer.py", self.subpath("demoapp/versioneer.py"))
        self.git("init")
        self.git("add", "--all")
        self.git("commit", "-m", "comment")

        v = self.python("setup.py", "--version")
        self.assertEqual(v, "unknown")
        v = self.python(os.path.join(self.subpath("demoapp"), "setup.py"),
                        "--version", workdir=self.testdir)
        self.assertEqual(v, "unknown")

        out = self.python("setup.py", "versioneer").splitlines()
        self.assertEqual(out[0], "running versioneer")
        self.assertEqual(out[1], " creating src/demo/_version.py")
        self.assertEqual(out[2], " appending to src/demo/__init__.py")
        self.assertEqual(out[3], " appending 'versioneer.py' to MANIFEST.in")
        self.assertEqual(out[4], " appending versionfile_source ('src/demo/_version.py') to MANIFEST.in")
        out = set(self.git("status", "--porcelain").splitlines())
        # Many folks have a ~/.gitignore with ignores .pyc files, but if they
        # don't, it will show up in the status here. Ignore it.
        out.discard("?? versioneer.pyc")
        out.discard("?? __pycache__/")
        self.assertEqual(out, set(["A  .gitattributes",
                                   "A  MANIFEST.in",
                                   "M  src/demo/__init__.py",
                                   "A  src/demo/_version.py"]))
        f = open(self.subpath("demoapp/src/demo/__init__.py"))
        i = f.read().splitlines()
        f.close()
        self.assertEqual(i[-3], "from ._version import get_versions")
        self.assertEqual(i[-2], "__version__ = get_versions()['version']")
        self.assertEqual(i[-1], "del get_versions")
        self.git("commit", "-m", "add _version stuff")

        # "setup.py versioneer" should be idempotent
        out = self.python("setup.py", "versioneer").splitlines()
        self.assertEqual(out[0], "running versioneer")
        self.assertEqual(out[1], " creating src/demo/_version.py")
        self.assertEqual(out[2], " src/demo/__init__.py unmodified")
        self.assertEqual(out[3], " 'versioneer.py' already in MANIFEST.in")
        self.assertEqual(out[4], " versionfile_source already in MANIFEST.in")
        out = set(self.git("status", "--porcelain").splitlines())
        out.discard("?? versioneer.pyc")
        out.discard("?? __pycache__/")
        self.assertEqual(out, set([]))

        self.git("tag", "demo-1.0")
        short = "1.0"
        full = self.git("rev-parse", "HEAD")
        if VERBOSE: print("FULL %s" % full)
        # SA: the tree is now sitting on the 1.0 tag
        self.do_checks(short, full, dirty=False, state="SA")

        # SB: now we dirty the tree
        f = open(self.subpath("demoapp/setup.py"),"a")
        f.write("# dirty\n")
        f.close()
        self.do_checks("1.0-dirty", full+"-dirty", dirty=True, state="SB")

        # SC: now we make one commit past the tag
        self.git("add", "setup.py")
        self.git("commit", "-m", "dirty")
        full = self.git("rev-parse", "HEAD")
        short = "1.0-1-g%s" % full[:7]
        self.do_checks(short, full, dirty=False, state="SC")


    def do_checks(self, exp_short, exp_long, dirty, state):
        if os.path.exists(self.subpath("out")):
            shutil.rmtree(self.subpath("out"))
        # TA: source tree
        self.check_version(self.subpath("demoapp"), exp_short, exp_long,
                           dirty, state, tree="TA")
        if dirty:
            return

        # TB: .git-less copy of source tree
        target = self.subpath("out/demoapp-TB")
        shutil.copytree(self.subpath("demoapp"), target)
        shutil.rmtree(os.path.join(target, ".git"))
        self.check_version(target, "unknown", "unknown", False, state, tree="TB")

        # TC: source tree in versionprefix-named parentdir
        target = self.subpath("out/demo-1.1")
        shutil.copytree(self.subpath("demoapp"), target)
        shutil.rmtree(os.path.join(target, ".git"))
        self.check_version(target, "1.1", "", False, state, tree="TC")

        # TD: unpacked git-archive tarball
        target = self.subpath("out/TD/demoapp-TD")
        self.git("archive", "--format=tar", "--prefix=demoapp-TD/",
                 "--output=../demo.tar", "HEAD")
        os.mkdir(self.subpath("out/TD"))
        t = tarfile.TarFile(self.subpath("demo.tar"))
        t.extractall(path=self.subpath("out/TD"))
        t.close()
        exp_short_TD = exp_short
        if state == "SC":
            # expanded keywords only tell us about tags and full revisionids,
            # not how many patches we are beyond a tag. So we can't expect
            # the short version to be like 1.0-1-gHEXID. The code falls back
            # to short=long
            exp_short_TD = exp_long
        self.check_version(target, exp_short_TD, exp_long, False, state, tree="TD")

        # TE: unpacked setup.py sdist tarball
        if os.path.exists(self.subpath("demoapp/dist")):
            shutil.rmtree(self.subpath("demoapp/dist"))
        self.python("setup.py", "sdist", "--formats=tar")
        files = os.listdir(self.subpath("demoapp/dist"))
        self.assertTrue(len(files)==1, files)
        distfile = files[0]
        self.assertEqual(distfile, "demo-%s.tar" % exp_short)
        fn = os.path.join(self.subpath("demoapp/dist"), distfile)
        os.mkdir(self.subpath("out/TE"))
        t = tarfile.TarFile(fn)
        t.extractall(path=self.subpath("out/TE"))
        t.close()
        target = self.subpath("out/TE/demo-%s" % exp_short)
        self.assertTrue(os.path.isdir(target))
        self.check_version(target, exp_short, exp_long, False, state, tree="TE")

    def compare(self, got, expected, state, tree, runtime):
        where = "/".join([state, tree, runtime])
        self.assertEqual(got, expected, "%s: got '%s' != expected '%s'"
                         % (where, got, expected))
        if VERBOSE: print(" good %s" % where)

    def check_version(self, workdir, exp_short, exp_long, dirty, state, tree):
        if VERBOSE: print("== starting %s %s" % (state, tree))
        # RA: setup.py --version
        if VERBOSE:
            # setup.py version invokes cmd_version, which uses verbose=True
            # and has more boilerplate.
            print(self.python("setup.py", "version", workdir=workdir))
        # setup.py --version gives us get_version() with verbose=False.
        v = self.python("setup.py", "--version", workdir=workdir)
        self.compare(v, exp_short, state, tree, "RA1")
        # and test again from outside the tree
        v = self.python(os.path.join(workdir, "setup.py"), "--version",
                        workdir=self.testdir)
        self.compare(v, exp_short, state, tree, "RA2")

        if dirty:
            return # cannot detect dirty files in a build

        # RB: setup.py build; rundemo --version
        if os.path.exists(os.path.join(workdir, "build")):
            shutil.rmtree(os.path.join(workdir, "build"))
        self.python("setup.py", "build", "--build-lib=build/lib",
                    "--build-scripts=build/lib", workdir=workdir)
        build_lib = os.path.join(workdir, "build", "lib")
        # copy bin/rundemo into the build libdir, so we don't have to muck
        # with PYTHONPATH when we execute it
        shutil.copyfile(os.path.join(workdir, "bin", "rundemo"),
                        os.path.join(build_lib, "rundemo"))
        out = self.python("rundemo", "--version", workdir=build_lib)
        data = dict([line.split(":",1) for line in out.splitlines()])
        self.compare(data["__version__"], exp_short, state, tree, "RB")
        self.compare(data["shortversion"], exp_short, state, tree, "RB")
        self.compare(data["longversion"], exp_long, state, tree, "RB")


if __name__ == '__main__':
    ver = run_command(GITS, ["--version"], ".", True)
    print("git --version: %s" % ver.strip())
    unittest.main()

########NEW FILE########
