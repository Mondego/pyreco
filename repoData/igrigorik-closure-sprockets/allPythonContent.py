__FILENAME__ = closurebuilder
#!/usr/bin/env python
#
# Copyright 2009 The Closure Library Authors. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS-IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Utility for Closure Library dependency calculation.

ClosureBuilder scans source files to build dependency info.  From the
dependencies, the script can produce a deps.js file, a manifest in dependency
order, a concatenated script, or compiled output from the Closure Compiler.

Paths to files can be expressed as individual arguments to the tool (intended
for use with find and xargs).  As a convenience, --root can be used to specify
all JS files below a directory.

usage: %prog [options] [file1.js file2.js ...]
"""

__author__ = 'nnaze@google.com (Nathan Naze)'


import logging
import optparse
import os
import sys

import depstree
import jscompiler
import source
import treescan


def _GetOptionsParser():
  """Get the options parser."""

  parser = optparse.OptionParser(__doc__)
  parser.add_option('-i',
                    '--input',
                    dest='inputs',
                    action='append',
                    default=[],
                    help='One or more input files to calculate dependencies '
                    'for.  The namespaces in this file will be combined with '
                    'those given with the -n flag to form the set of '
                    'namespaces to find dependencies for.')
  parser.add_option('-n',
                    '--namespace',
                    dest='namespaces',
                    action='append',
                    default=[],
                    help='One or more namespaces to calculate dependencies '
                    'for.  These namespaces will be combined with those given '
                    'with the -i flag to form the set of namespaces to find '
                    'dependencies for.  A Closure namespace is a '
                    'dot-delimited path expression declared with a call to '
                    'goog.provide() (e.g. "goog.array" or "foo.bar").')
  parser.add_option('--root',
                    dest='roots',
                    action='append',
                    default=[],
                    help='The paths that should be traversed to build the '
                    'dependencies.')
  parser.add_option('-o',
                    '--output_mode',
                    dest='output_mode',
                    type='choice',
                    action='store',
                    choices=['list', 'script', 'compiled'],
                    default='list',
                    help='The type of output to generate from this script. '
                    'Options are "list" for a list of filenames, "script" '
                    'for a single script containing the contents of all the '
                    'files, or "compiled" to produce compiled output with '
                    'the Closure Compiler.  Default is "list".')
  parser.add_option('-c',
                    '--compiler_jar',
                    dest='compiler_jar',
                    action='store',
                    help='The location of the Closure compiler .jar file.')
  parser.add_option('-f',
                    '--compiler_flags',
                    dest='compiler_flags',
                    default=[],
                    action='append',
                    help='Additional flags to pass to the Closure compiler. '
                    'To pass multiple flags, --compiler_flags has to be '
                    'specified multiple times.')
  parser.add_option('--output_file',
                    dest='output_file',
                    action='store',
                    help=('If specified, write output to this path instead of '
                          'writing to standard output.'))

  return parser


def _GetInputByPath(path, sources):
  """Get the source identified by a path.

  Args:
    path: str, A path to a file that identifies a source.
    sources: An iterable collection of source objects.

  Returns:
    The source from sources identified by path, if found.  Converts to
    absolute paths for comparison.
  """
  for js_source in sources:
    # Convert both to absolute paths for comparison.
    if os.path.abspath(path) == os.path.abspath(js_source.GetPath()):
      return js_source


def _GetClosureBaseFile(sources):
  """Given a set of sources, returns the one base.js file.

  Note that if zero or two or more base.js files are found, an error message
  will be written and the program will be exited.

  Args:
    sources: An iterable of _PathSource objects.

  Returns:
    The _PathSource representing the base Closure file.
  """
  base_files = [
      js_source for js_source in sources if _IsClosureBaseFile(js_source)]

  if not base_files:
    logging.error('No Closure base.js file found.')
    sys.exit(1)
  if len(base_files) > 1:
    logging.error('More than one Closure base.js files found at these paths:')
    for base_file in base_files:
      logging.error(base_file.GetPath())
    sys.exit(1)
  return base_files[0]


def _IsClosureBaseFile(js_source):
  """Returns true if the given _PathSource is the Closure base.js source."""
  return (os.path.basename(js_source.GetPath()) == 'base.js' and
          js_source.provides == set(['goog']))


class _PathSource(source.Source):
  """Source file subclass that remembers its file path."""

  def __init__(self, path):
    """Initialize a source.

    Args:
      path: str, Path to a JavaScript file.  The source string will be read
        from this file.
    """
    super(_PathSource, self).__init__(source.GetFileContents(path))

    self._path = path

  def GetPath(self):
    """Returns the path."""
    return self._path


def main():
  logging.basicConfig(format=(sys.argv[0] + ': %(message)s'),
                      level=logging.INFO)
  options, args = _GetOptionsParser().parse_args()

  # Make our output pipe.
  if options.output_file:
    out = open(options.output_file, 'w')
  else:
    out = sys.stdout

  sources = set()

  logging.info('Scanning paths...')
  for path in options.roots:
    for js_path in treescan.ScanTreeForJsFiles(path):
      sources.add(_PathSource(js_path))

  # Add scripts specified on the command line.
  for js_path in args:
    sources.add(_PathSource(js_path))

  logging.info('%s sources scanned.', len(sources))

  # Though deps output doesn't need to query the tree, we still build it
  # to validate dependencies.
  logging.info('Building dependency tree..')
  tree = depstree.DepsTree(sources)

  input_namespaces = set()
  inputs = options.inputs or []
  for input_path in inputs:
    js_input = _GetInputByPath(input_path, sources)
    if not js_input:
      logging.error('No source matched input %s', input_path)
      sys.exit(1)
    input_namespaces.update(js_input.provides)

  input_namespaces.update(options.namespaces)

  if not input_namespaces:
    logging.error('No namespaces found. At least one namespace must be '
                  'specified with the --namespace or --input flags.')
    sys.exit(2)

  # The Closure Library base file must go first.
  base = _GetClosureBaseFile(sources)
  deps = [base] + tree.GetDependencies(input_namespaces)

  output_mode = options.output_mode
  if output_mode == 'list':
    out.writelines([js_source.GetPath() + '\n' for js_source in deps])
  elif output_mode == 'script':
    out.writelines([js_source.GetSource() for js_source in deps])
  elif output_mode == 'compiled':

    # Make sure a .jar is specified.
    if not options.compiler_jar:
      logging.error('--compiler_jar flag must be specified if --output is '
                    '"compiled"')
      sys.exit(2)

    compiled_source = jscompiler.Compile(
        options.compiler_jar,
        [js_source.GetPath() for js_source in deps],
        options.compiler_flags)

    if compiled_source is None:
      logging.error('JavaScript compilation failed.')
      sys.exit(1)
    else:
      logging.info('JavaScript compilation succeeded.')
      out.write(compiled_source)

  else:
    logging.error('Invalid value for --output flag.')
    sys.exit(2)


if __name__ == '__main__':
  main()

########NEW FILE########
__FILENAME__ = depstree
# Copyright 2009 The Closure Library Authors. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS-IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.


"""Class to represent a full Closure Library dependency tree.

Offers a queryable tree of dependencies of a given set of sources.  The tree
will also do logical validation to prevent duplicate provides and circular
dependencies.
"""

__author__ = 'nnaze@google.com (Nathan Naze)'


class DepsTree(object):
  """Represents the set of dependencies between source files."""

  def __init__(self, sources):
    """Initializes the tree with a set of sources.

    Args:
      sources: A set of JavaScript sources.

    Raises:
      MultipleProvideError: A namespace is provided by muplitple sources.
      NamespaceNotFoundError: A namespace is required but never provided.
    """

    self._sources = sources
    self._provides_map = dict()

    # Ensure nothing was provided twice.
    for source in sources:
      for provide in source.provides:
        if provide in self._provides_map:
          raise MultipleProvideError(
              provide, [self._provides_map[provide], source])

        self._provides_map[provide] = source

    # Check that all required namespaces are provided.
    for source in sources:
      for require in source.requires:
        if require not in self._provides_map:
          raise NamespaceNotFoundError(require, source)

  def GetDependencies(self, required_namespaces):
    """Get source dependencies, in order, for the given namespaces.

    Args:
      required_namespaces: A string (for one) or list (for one or more) of
        namespaces.

    Returns:
      A list of source objects that provide those namespaces and all
      requirements, in dependency order.

    Raises:
      NamespaceNotFoundError: A namespace is requested but doesn't exist.
      CircularDependencyError: A cycle is detected in the dependency tree.
    """
    if isinstance(required_namespaces, str):
      required_namespaces = [required_namespaces]

    deps_sources = []

    for namespace in required_namespaces:
      for source in DepsTree._ResolveDependencies(
          namespace, [], self._provides_map, []):
        if source not in deps_sources:
          deps_sources.append(source)

    return deps_sources

  @staticmethod
  def _ResolveDependencies(required_namespace, deps_list, provides_map,
                           traversal_path):
    """Resolve dependencies for Closure source files.

    Follows the dependency tree down and builds a list of sources in dependency
    order.  This function will recursively call itself to fill all dependencies
    below the requested namespaces, and then append its sources at the end of
    the list.

    Args:
      required_namespace: String of required namespace.
      deps_list: List of sources in dependency order.  This function will append
        the required source once all of its dependencies are satisfied.
      provides_map: Map from namespace to source that provides it.
      traversal_path: List of namespaces of our path from the root down the
        dependency/recursion tree.  Used to identify cyclical dependencies.
        This is a list used as a stack -- when the function is entered, the
        current namespace is pushed and popped right before returning.
        Each recursive call will check that the current namespace does not
        appear in the list, throwing a CircularDependencyError if it does.

    Returns:
      The given deps_list object filled with sources in dependency order.

    Raises:
      NamespaceNotFoundError: A namespace is requested but doesn't exist.
      CircularDependencyError: A cycle is detected in the dependency tree.
    """

    source = provides_map.get(required_namespace)
    if not source:
      raise NamespaceNotFoundError(required_namespace)

    if required_namespace in traversal_path:
      traversal_path.append(required_namespace)  # do this *after* the test

      # This must be a cycle.
      raise CircularDependencyError(traversal_path)

    traversal_path.append(required_namespace)

    for require in source.requires:

      # Append all other dependencies before we append our own.
      DepsTree._ResolveDependencies(require, deps_list, provides_map,
                                    traversal_path)
    deps_list.append(source)

    traversal_path.pop()

    return deps_list


class BaseDepsTreeError(Exception):
  """Base DepsTree error."""

  def __init__(self):
    Exception.__init__(self)


class CircularDependencyError(BaseDepsTreeError):
  """Raised when a dependency cycle is encountered."""

  def __init__(self, dependency_list):
    BaseDepsTreeError.__init__(self)
    self._dependency_list = dependency_list

  def __str__(self):
    return ('Encountered circular dependency:\n%s\n' %
            '\n'.join(self._dependency_list))


class MultipleProvideError(BaseDepsTreeError):
  """Raised when a namespace is provided more than once."""

  def __init__(self, namespace, sources):
    BaseDepsTreeError.__init__(self)
    self._namespace = namespace
    self._sources = sources

  def __str__(self):
    source_strs = map(str, self._sources)

    return ('Namespace "%s" provided more than once in sources:\n%s\n' %
            (self._namespace, '\n'.join(source_strs)))


class NamespaceNotFoundError(BaseDepsTreeError):
  """Raised when a namespace is requested but not provided."""

  def __init__(self, namespace, source=None):
    BaseDepsTreeError.__init__(self)
    self._namespace = namespace
    self._source = source

  def __str__(self):
    msg = 'Namespace "%s" never provided.' % self._namespace
    if self._source:
      msg += ' Required in %s' % self._source
    return msg

########NEW FILE########
__FILENAME__ = depstree_test
#!/usr/bin/env python
#
# Copyright 2009 The Closure Library Authors. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS-IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.


"""Unit test for depstree."""

__author__ = 'nnaze@google.com (Nathan Naze)'


import unittest

import depstree


def _GetProvides(sources):
  """Get all namespaces provided by a collection of sources."""

  provides = set()
  for source in sources:
    provides.update(source.provides)
  return provides


class MockSource(object):
  """Mock Source file."""

  def __init__(self, provides, requires):
    self.provides = set(provides)
    self.requires = set(requires)

  def __repr__(self):
    return 'MockSource %s' % self.provides


class DepsTreeTestCase(unittest.TestCase):
  """Unit test for DepsTree.  Tests several common situations and errors."""

  def AssertValidDependencies(self, deps_list):
    """Validates a dependency list.

    Asserts that a dependency list is valid: For every source in the list,
    ensure that every require is provided by a source earlier in the list.

    Args:
      deps_list: A list of sources that should be in dependency order.
    """

    for i in range(len(deps_list)):
      source = deps_list[i]
      previous_provides = _GetProvides(deps_list[:i])
      for require in source.requires:
        self.assertTrue(
            require in previous_provides,
            'Namespace "%s" not provided before required by %s' % (
                require, source))

  def testSimpleDepsTree(self):
    a = MockSource(['A'], ['B', 'C'])
    b = MockSource(['B'], [])
    c = MockSource(['C'], ['D'])
    d = MockSource(['D'], ['E'])
    e = MockSource(['E'], [])

    tree = depstree.DepsTree([a, b, c, d, e])

    self.AssertValidDependencies(tree.GetDependencies('A'))
    self.AssertValidDependencies(tree.GetDependencies('B'))
    self.AssertValidDependencies(tree.GetDependencies('C'))
    self.AssertValidDependencies(tree.GetDependencies('D'))
    self.AssertValidDependencies(tree.GetDependencies('E'))

  def testCircularDependency(self):
    # Circular deps
    a = MockSource(['A'], ['B'])
    b = MockSource(['B'], ['C'])
    c = MockSource(['C'], ['A'])

    tree = depstree.DepsTree([a, b, c])

    self.assertRaises(depstree.CircularDependencyError,
                      tree.GetDependencies, 'A')

  def testRequiresUndefinedNamespace(self):
    a = MockSource(['A'], ['B'])
    b = MockSource(['B'], ['C'])
    c = MockSource(['C'], ['D'])  # But there is no D.

    def MakeDepsTree():
      return depstree.DepsTree([a, b, c])

    self.assertRaises(depstree.NamespaceNotFoundError, MakeDepsTree)

  def testDepsForMissingNamespace(self):
    a = MockSource(['A'], ['B'])
    b = MockSource(['B'], [])

    tree = depstree.DepsTree([a, b])

    # There is no C.
    self.assertRaises(depstree.NamespaceNotFoundError,
                      tree.GetDependencies, 'C')

  def testMultipleRequires(self):
    a = MockSource(['A'], ['B'])
    b = MockSource(['B'], ['C'])
    c = MockSource(['C'], [])
    d = MockSource(['D'], ['B'])

    tree = depstree.DepsTree([a, b, c, d])
    self.AssertValidDependencies(tree.GetDependencies(['D', 'A']))


if __name__ == '__main__':
  unittest.main()

########NEW FILE########
__FILENAME__ = depswriter
#!/usr/bin/env python
#
# Copyright 2009 The Closure Library Authors. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS-IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.


"""Generates out a Closure deps.js file given a list of JavaScript sources.

Paths can be specified as arguments or (more commonly) specifying trees
with the flags (call with --help for descriptions).

Usage: depswriter.py [path/to/js1.js [path/to/js2.js] ...]
"""

import logging
import optparse
import os
import posixpath
import shlex
import sys

import source
import treescan


__author__ = 'nnaze@google.com (Nathan Naze)'


def MakeDepsFile(source_map):
  """Make a generated deps file.

  Args:
    source_map: A dict map of the source path to source.Source object.

  Returns:
    str, A generated deps file source.
  """

  # Write in path alphabetical order
  paths = sorted(source_map.keys())

  lines = []

  for path in paths:
    js_source = source_map[path]

    # We don't need to add entries that don't provide anything.
    if js_source.provides:
      lines.append(_GetDepsLine(path, js_source))

  return ''.join(lines)


def _GetDepsLine(path, js_source):
  """Get a deps.js file string for a source."""

  provides = sorted(js_source.provides)
  requires = sorted(js_source.requires)

  return 'goog.addDependency(\'%s\', %s, %s);\n' % (path, provides, requires)


def _GetOptionsParser():
  """Get the options parser."""

  parser = optparse.OptionParser(__doc__)

  parser.add_option('--output_file',
                    dest='output_file',
                    action='store',
                    help=('If specified, write output to this path instead of '
                          'writing to standard output.'))
  parser.add_option('--root',
                    dest='roots',
                    default=[],
                    action='append',
                    help='A root directory to scan for JS source files. '
                    'Paths of JS files in generated deps file will be '
                    'relative to this path.  This flag may be specified '
                    'multiple times.')
  parser.add_option('--root_with_prefix',
                    dest='roots_with_prefix',
                    default=[],
                    action='append',
                    help='A root directory to scan for JS source files, plus '
                    'a prefix (if either contains a space, surround with '
                    'quotes).  Paths in generated deps file will be relative '
                    'to the root, but preceded by the prefix.  This flag '
                    'may be specified multiple times.')
  parser.add_option('--path_with_depspath',
                    dest='paths_with_depspath',
                    default=[],
                    action='append',
                    help='A path to a source file and an alternate path to '
                    'the file in the generated deps file (if either contains '
                    'a space, surround with whitespace). This flag may be '
                    'specified multiple times.')
  return parser


def _NormalizePathSeparators(path):
  """Replaces OS-specific path separators with POSIX-style slashes.

  Args:
    path: str, A file path.

  Returns:
    str, The path with any OS-specific path separators (such as backslash on
      Windows) replaced with URL-compatible forward slashes. A no-op on systems
      that use POSIX paths.
  """
  return path.replace(os.sep, posixpath.sep)


def _GetRelativePathToSourceDict(root, prefix=''):
  """Scans a top root directory for .js sources.

  Args:
    root: str, Root directory.
    prefix: str, Prefix for returned paths.

  Returns:
    dict, A map of relative paths (with prefix, if given), to source.Source
      objects.
  """
  # Remember and restore the cwd when we're done. We work from the root so
  # that paths are relative from the root.
  start_wd = os.getcwd()
  os.chdir(root)

  path_to_source = {}
  for path in treescan.ScanTreeForJsFiles('.'):
    prefixed_path = _NormalizePathSeparators(os.path.join(prefix, path))
    path_to_source[prefixed_path] = source.Source(source.GetFileContents(path))

  os.chdir(start_wd)

  return path_to_source


def _GetPair(s):
  """Return a string as a shell-parsed tuple.  Two values expected."""
  try:
    # shlex uses '\' as an escape character, so they must be escaped.
    s = s.replace('\\', '\\\\')
    first, second = shlex.split(s)
    return (first, second)
  except:
    raise Exception('Unable to parse input line as a pair: %s' % s)


def main():
  """CLI frontend to MakeDepsFile."""
  logging.basicConfig(format=(sys.argv[0] + ': %(message)s'),
                      level=logging.INFO)
  options, args = _GetOptionsParser().parse_args()

  path_to_source = {}

  # Roots without prefixes
  for root in options.roots:
    path_to_source.update(_GetRelativePathToSourceDict(root))

  # Roots with prefixes
  for root_and_prefix in options.roots_with_prefix:
    root, prefix = _GetPair(root_and_prefix)
    path_to_source.update(_GetRelativePathToSourceDict(root, prefix=prefix))

  # Source paths
  for path in args:
    path_to_source[path] = source.Source(source.GetFileContents(path))

  # Source paths with alternate deps paths
  for path_with_depspath in options.paths_with_depspath:
    srcpath, depspath = _GetPair(path_with_depspath)
    path_to_source[depspath] = source.Source(source.GetFileContents(srcpath))

  # Make our output pipe.
  if options.output_file:
    out = open(options.output_file, 'w')
  else:
    out = sys.stdout

  out.write('// This file was autogenerated by %s.\n' % sys.argv[0])
  out.write('// Please do not edit.\n')

  out.write(MakeDepsFile(path_to_source))


if __name__ == '__main__':
  main()

########NEW FILE########
__FILENAME__ = jscompiler
# Copyright 2010 The Closure Library Authors. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS-IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Utility to use the Closure Compiler CLI from Python."""

import distutils.version
import logging
import re
import subprocess


# Pulls a version number from the first line of 'java -version'
# See http://java.sun.com/j2se/versioning_naming.html to learn more about the
# command's output format.
_VERSION_REGEX = re.compile('"([0-9][.0-9]*)')


def _GetJavaVersion():
  """Returns the string for the current version of Java installed."""
  proc = subprocess.Popen(['java', '-version'], stderr=subprocess.PIPE)
  unused_stdoutdata, stderrdata = proc.communicate()
  version_line = stderrdata.splitlines()[0]
  return _VERSION_REGEX.search(version_line).group(1)


def Compile(compiler_jar_path, source_paths, flags=None):
  """Prepares command-line call to Closure Compiler.

  Args:
    compiler_jar_path: Path to the Closure compiler .jar file.
    source_paths: Source paths to build, in order.
    flags: A list of additional flags to pass on to Closure Compiler.

  Returns:
    The compiled source, as a string, or None if compilation failed.
  """

  # User friendly version check.
  if not (distutils.version.LooseVersion(_GetJavaVersion()) >=
          distutils.version.LooseVersion('1.6')):
    logging.error('Closure Compiler requires Java 1.6 or higher. '
                  'Please visit http://www.java.com/getjava')
    return

  args = ['java', '-jar', compiler_jar_path]
  for path in source_paths:
    args += ['--js', path]

  if flags:
    args += flags

  logging.info('Compiling with the following command: %s', ' '.join(args))

  proc = subprocess.Popen(args, stdout=subprocess.PIPE)
  stdoutdata, unused_stderrdata = proc.communicate()

  if proc.returncode != 0:
    return

  return stdoutdata

########NEW FILE########
__FILENAME__ = source
# Copyright 2009 The Closure Library Authors. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS-IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.


"""Scans a source JS file for its provided and required namespaces.

Simple class to scan a JavaScript file and express its dependencies.
"""

__author__ = 'nnaze@google.com'


import re

_BASE_REGEX_STRING = '^\s*goog\.%s\(\s*[\'"](.+)[\'"]\s*\)'
_PROVIDE_REGEX = re.compile(_BASE_REGEX_STRING % 'provide')
_REQUIRES_REGEX = re.compile(_BASE_REGEX_STRING % 'require')

# This line identifies base.js and should match the line in that file.
_GOOG_BASE_LINE = (
    'var goog = goog || {}; // Identifies this file as the Closure base.')


class Source(object):
  """Scans a JavaScript source for its provided and required namespaces."""

  def __init__(self, source):
    """Initialize a source.

    Args:
      source: str, The JavaScript source.
    """

    self.provides = set()
    self.requires = set()

    self._source = source
    self._ScanSource()

  def __str__(self):
    return 'Source %s' % self._path

  def GetSource(self):
    """Get the source as a string."""
    return self._source

  def _ScanSource(self):
    """Fill in provides and requires by scanning the source."""

    # TODO: Strip source comments first, as these might be in a comment
    # block.  RegExes can be borrowed from other projects.
    source = self.GetSource()

    source_lines = source.splitlines()
    for line in source_lines:
      match = _PROVIDE_REGEX.match(line)
      if match:
        self.provides.add(match.group(1))
      match = _REQUIRES_REGEX.match(line)
      if match:
        self.requires.add(match.group(1))

    # Closure's base file implicitly provides 'goog'.
    for line in source_lines:
      if line == _GOOG_BASE_LINE:
        if len(self.provides) or len(self.requires):
          raise Exception(
              'Base files should not provide or require namespaces.')
        self.provides.add('goog')


def GetFileContents(path):
  """Get a file's contents as a string.

  Args:
    path: str, Path to file.

  Returns:
    str, Contents of file.

  Raises:
    IOError: An error occurred opening or reading the file.

  """
  fileobj = open(path)
  try:
    return fileobj.read()
  finally:
    fileobj.close()

########NEW FILE########
__FILENAME__ = source_test
#!/usr/bin/env python
#
# Copyright 2010 The Closure Library Authors. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS-IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.


"""Unit test for source."""

__author__ = 'nnaze@google.com (Nathan Naze)'


import unittest

import source


class SourceTestCase(unittest.TestCase):
  """Unit test for source.  Tests the parser on a known source input."""

  def testSourceScan(self):
    test_source = source.Source(_TEST_SOURCE)

    self.assertEqual(set(['foo', 'foo.test']),
                     test_source.provides)
    self.assertEqual(set(['goog.dom', 'goog.events.EventType']),
                     test_source.requires)

  def testSourceScanBase(self):
    test_source = source.Source(_TEST_BASE_SOURCE)

    self.assertEqual(set(['goog']),
                     test_source.provides)
    self.assertEqual(test_source.requires, set())

  def testSourceScanBadBase(self):

    def MakeSource():
      source.Source(_TEST_BAD_BASE_SOURCE)

    self.assertRaises(Exception, MakeSource)


_TEST_SOURCE = """// Fake copyright notice

/** Very important comment. */

goog.provide('foo');
goog.provide('foo.test');

goog.require('goog.dom');
goog.require('goog.events.EventType');

function foo() {
  // Set bar to seventeen to increase performance.
  this.bar = 17;
}
"""

_TEST_BASE_SOURCE = """
var goog = goog || {}; // Identifies this file as the Closure base.
"""

_TEST_BAD_BASE_SOURCE = """
goog.provide('goog');

var goog = goog || {}; // Identifies this file as the Closure base.
"""


if __name__ == '__main__':
  unittest.main()

########NEW FILE########
__FILENAME__ = treescan
#!/usr/bin/env python
#
# Copyright 2010 The Closure Library Authors. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS-IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.


"""Shared utility functions for scanning directory trees."""

import os
import re


__author__ = 'nnaze@google.com (Nathan Naze)'


# Matches a .js file path.
_JS_FILE_REGEX = re.compile(r'^.+\.js(\..*)?$')


def ScanTreeForJsFiles(root):
  """Scans a directory tree for JavaScript files.

  Args:
    root: str, Path to a root directory.

  Returns:
    An iterable of paths to JS files, relative to cwd.
  """
  return ScanTree(root, path_filter=_JS_FILE_REGEX)


def ScanTree(root, path_filter=None, ignore_hidden=True):
  """Scans a directory tree for files.

  Args:
    root: str, Path to a root directory.
    path_filter: A regular expression filter.  If set, only paths matching
      the path_filter are returned.
    ignore_hidden: If True, do not follow or return hidden directories or files
      (those starting with a '.' character).

  Yields:
    A string path to files, relative to cwd.
  """

  def OnError(os_error):
    raise os_error

  for dirpath, dirnames, filenames in os.walk(root, onerror=OnError):
    # os.walk allows us to modify dirnames to prevent decent into particular
    # directories.  Avoid hidden directories.
    for dirname in dirnames:
      if ignore_hidden and dirname.startswith('.'):
        dirnames.remove(dirname)

    for filename in filenames:

      # nothing that starts with '.'
      if ignore_hidden and filename.startswith('.'):
        continue

      fullpath = os.path.join(dirpath, filename)

      if path_filter and not path_filter.match(fullpath):
        continue

      yield os.path.normpath(fullpath)

########NEW FILE########
__FILENAME__ = calcdeps
#!/usr/bin/env python
#
# Copyright 2006 The Closure Library Authors. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS-IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.


"""Calculates Javascript dependencies without requiring Google3.

It iterates over a number of search paths and builds a dependency tree.  With
the inputs provided, it walks the dependency tree and outputs all the files
required for compilation.\n
"""





try:
  import distutils.version
except ImportError:
  # distutils is not available in all environments
  distutils = None

import logging
import optparse
import os
import re
import subprocess
import sys



req_regex = re.compile('goog\.require\s*\(\s*[\'\"]([^\)]+)[\'\"]\s*\)')
prov_regex = re.compile('goog\.provide\s*\(\s*[\'\"]([^\)]+)[\'\"]\s*\)')
ns_regex = re.compile('^ns:((\w+\.)*(\w+))$')
version_regex = re.compile('[\.0-9]+')
js_file_regex = re.compile(r'^.+\.js(\..*)?$')


def IsValidFile(ref):
  """Returns true if the provided reference is a file and exists."""
  return os.path.isfile(ref)


def IsJsFile(ref):
  """Returns true if the provided reference is a Javascript file."""
  return js_file_regex.match(ref)
  # return ref.endswith('.js')


def IsNamespace(ref):
  """Returns true if the provided reference is a namespace."""
  return re.match(ns_regex, ref) is not None


def IsDirectory(ref):
  """Returns true if the provided reference is a directory."""
  return os.path.isdir(ref)


def ExpandDirectories(refs):
  """Expands any directory references into inputs.

  Description:
    Looks for any directories in the provided references.  Found directories
    are recursively searched for .js files, which are then added to the result
    list.

  Args:
    refs: a list of references such as files, directories, and namespaces

  Returns:
    A list of references with directories removed and replaced by any
    .js files that are found in them. Also, the paths will be normalized.
  """
  result = []
  for ref in refs:
    if IsDirectory(ref):
      # Disable 'Unused variable' for subdirs
      # pylint: disable-msg=W0612
      for (directory, subdirs, filenames) in os.walk(ref):
        for filename in filenames:
          if IsJsFile(filename):
            result.append(os.path.join(directory, filename))
    else:
      result.append(ref)
  return map(os.path.normpath, result)


class DependencyInfo(object):
  """Represents a dependency that is used to build and walk a tree."""

  def __init__(self, filename):
    self.filename = filename
    self.provides = []
    self.requires = []

  def __str__(self):
    return '%s Provides: %s Requires: %s' % (self.filename,
                                             repr(self.provides),
                                             repr(self.requires))


def BuildDependenciesFromFiles(files):
  """Build a list of dependencies from a list of files.

  Description:
    Takes a list of files, extracts their provides and requires, and builds
    out a list of dependency objects.

  Args:
    files: a list of files to be parsed for goog.provides and goog.requires.

  Returns:
    A list of dependency objects, one for each file in the files argument.
  """
  result = []
  filenames = set()
  for filename in files:
    if filename in filenames:
      continue

    # Python 3 requires the file encoding to be specified
    if (sys.version_info[0] < 3):
      file_handle = open(filename, 'r')
    else:
      file_handle = open(filename, 'r', encoding='utf8')
    dep = DependencyInfo(filename)
    try:
      for line in file_handle:
        if re.match(req_regex, line):
          dep.requires.append(re.search(req_regex, line).group(1))
        if re.match(prov_regex, line):
          dep.provides.append(re.search(prov_regex, line).group(1))
    finally:
      file_handle.close()
    result.append(dep)
    filenames.add(filename)

  return result


def BuildDependencyHashFromDependencies(deps):
  """Builds a hash for searching dependencies by the namespaces they provide.

  Description:
    Dependency objects can provide multiple namespaces.  This method enumerates
    the provides of each dependency and adds them to a hash that can be used
    to easily resolve a given dependency by a namespace it provides.

  Args:
    deps: a list of dependency objects used to build the hash.

  Raises:
    Exception: If a multiple files try to provide the same namepace.

  Returns:
    A hash table { namespace: dependency } that can be used to resolve a
    dependency by a namespace it provides.
  """
  dep_hash = {}
  for dep in deps:
    for provide in dep.provides:
      if provide in dep_hash:
        raise Exception('Duplicate provide (%s) in (%s, %s)' % (
            provide,
            dep_hash[provide].filename,
            dep.filename))
      dep_hash[provide] = dep
  return dep_hash


def CalculateDependencies(paths, inputs):
  """Calculates the dependencies for given inputs.

  Description:
    This method takes a list of paths (files, directories) and builds a
    searchable data structure based on the namespaces that each .js file
    provides.  It then parses through each input, resolving dependencies
    against this data structure.  The final output is a list of files,
    including the inputs, that represent all of the code that is needed to
    compile the given inputs.

  Args:
    paths: the references (files, directories) that are used to build the
      dependency hash.
    inputs: the inputs (files, directories, namespaces) that have dependencies
      that need to be calculated.

  Raises:
    Exception: if a provided input is invalid.

  Returns:
    A list of all files, including inputs, that are needed to compile the given
    inputs.
  """
  deps = BuildDependenciesFromFiles(paths + inputs)
  search_hash = BuildDependencyHashFromDependencies(deps)
  result_list = []
  seen_list = []
  for input_file in inputs:
    if IsNamespace(input_file):
      namespace = re.search(ns_regex, input_file).group(1)
      if namespace not in search_hash:
        raise Exception('Invalid namespace (%s)' % namespace)
      input_file = search_hash[namespace].filename
    if not IsValidFile(input_file) or not IsJsFile(input_file):
      raise Exception('Invalid file (%s)' % input_file)
    seen_list.append(input_file)
    file_handle = open(input_file, 'r')
    try:
      for line in file_handle:
        if re.match(req_regex, line):
          require = re.search(req_regex, line).group(1)
          ResolveDependencies(require, search_hash, result_list, seen_list)
    finally:
      file_handle.close()
    result_list.append(input_file)

  # All files depend on base.js, so put it first.
  base_js_path = FindClosureBasePath(paths)
  if base_js_path:
    result_list.insert(0, base_js_path)
  else:
    logging.warning('Closure Library base.js not found.')

  return result_list


def FindClosureBasePath(paths):
  """Given a list of file paths, return Closure base.js path, if any.

  Args:
    paths: A list of paths.

  Returns:
    The path to Closure's base.js file including filename, if found.
  """

  for path in paths:
    pathname, filename = os.path.split(path)

    if filename == 'base.js':
      f = open(path)

      is_base = False

      # Sanity check that this is the Closure base file.  Check that this
      # is where goog is defined.
      for line in f:
        if line.startswith('var goog = goog || {};'):
          is_base = True
          break

      f.close()

      if is_base:
        return path

def ResolveDependencies(require, search_hash, result_list, seen_list):
  """Takes a given requirement and resolves all of the dependencies for it.

  Description:
    A given requirement may require other dependencies.  This method
    recursively resolves all dependencies for the given requirement.

  Raises:
    Exception: when require does not exist in the search_hash.

  Args:
    require: the namespace to resolve dependencies for.
    search_hash: the data structure used for resolving dependencies.
    result_list: a list of filenames that have been calculated as dependencies.
      This variable is the output for this function.
    seen_list: a list of filenames that have been 'seen'.  This is required
      for the dependency->dependant ordering.
  """
  if require not in search_hash:
    raise Exception('Missing provider for (%s)' % require)

  dep = search_hash[require]
  if not dep.filename in seen_list:
    seen_list.append(dep.filename)
    for sub_require in dep.requires:
      ResolveDependencies(sub_require, search_hash, result_list, seen_list)
    result_list.append(dep.filename)


def GetDepsLine(dep, base_path):
  """Returns a JS string for a dependency statement in the deps.js file.

  Args:
    dep: The dependency that we're printing.
    base_path: The path to Closure's base.js including filename.
  """
  return 'goog.addDependency("%s", %s, %s);' % (
      GetRelpath(dep.filename, base_path), dep.provides, dep.requires)


def GetRelpath(path, start):
  """Return a relative path to |path| from |start|."""
  # NOTE: Python 2.6 provides os.path.relpath, which has almost the same
  # functionality as this function. Since we want to support 2.4, we have
  # to implement it manually. :(
  path_list = os.path.abspath(os.path.normpath(path)).split(os.sep)
  start_list = os.path.abspath(
      os.path.normpath(os.path.dirname(start))).split(os.sep)

  common_prefix_count = 0
  for i in range(0, min(len(path_list), len(start_list))):
    if path_list[i] != start_list[i]:
      break
    common_prefix_count += 1

  # Always use forward slashes, because this will get expanded to a url,
  # not a file path.
  return '/'.join(['..'] * (len(start_list) - common_prefix_count) +
                  path_list[common_prefix_count:])


def PrintLine(msg, out):
  out.write(msg)
  out.write('\n')


def PrintDeps(source_paths, deps, out):
  """Print out a deps.js file from a list of source paths.

  Args:
    source_paths: Paths that we should generate dependency info for.
    deps: Paths that provide dependency info. Their dependency info should
        not appear in the deps file.
    out: The output file.

  Returns:
    True on success, false if it was unable to find the base path
    to generate deps relative to.
  """
  base_path = FindClosureBasePath(source_paths + deps)
  if not base_path:
    return False

  PrintLine('// This file was autogenerated by calcdeps.py', out)
  excludesSet = set(deps)

  for dep in BuildDependenciesFromFiles(source_paths + deps):
    if not dep.filename in excludesSet:
      PrintLine(GetDepsLine(dep, base_path), out)

  return True


def PrintScript(source_paths, out):
  for index, dep in enumerate(source_paths):
    PrintLine('// Input %d' % index, out)
    f = open(dep, 'r')
    PrintLine(f.read(), out)
    f.close()


def GetJavaVersion():
  """Returns the string for the current version of Java installed."""
  proc = subprocess.Popen(['java', '-version'], stderr=subprocess.PIPE)
  proc.wait()
  version_line = proc.stderr.read().splitlines()[0]
  return version_regex.search(version_line).group()


def FilterByExcludes(options, files):
  """Filters the given files by the exlusions specified at the command line.

  Args:
    options: The flags to calcdeps.
    files: The files to filter.
  Returns:
    A list of files.
  """
  excludes = []
  if options.excludes:
    excludes = ExpandDirectories(options.excludes)

  excludesSet = set(excludes)
  return [i for i in files if not i in excludesSet]


def GetPathsFromOptions(options):
  """Generates the path files from flag options.

  Args:
    options: The flags to calcdeps.
  Returns:
    A list of files in the specified paths. (strings).
  """

  search_paths = options.paths
  if not search_paths:
    search_paths = ['.']  # Add default folder if no path is specified.

  search_paths = ExpandDirectories(search_paths)
  return FilterByExcludes(options, search_paths)


def GetInputsFromOptions(options):
  """Generates the inputs from flag options.

  Args:
    options: The flags to calcdeps.
  Returns:
    A list of inputs (strings).
  """
  inputs = options.inputs
  if not inputs:  # Parse stdin
    logging.info('No inputs specified. Reading from stdin...')
    inputs = filter(None, [line.strip('\n') for line in sys.stdin.readlines()])

  logging.info('Scanning files...')
  inputs = ExpandDirectories(inputs)

  return FilterByExcludes(options, inputs)


def Compile(compiler_jar_path, source_paths, out, flags=None):
  """Prepares command-line call to Closure compiler.

  Args:
    compiler_jar_path: Path to the Closure compiler .jar file.
    source_paths: Source paths to build, in order.
    flags: A list of additional flags to pass on to Closure compiler.
  """
  args = ['java', '-jar', compiler_jar_path]
  for path in source_paths:
    args += ['--js', path]

  if flags:
    args += flags

  logging.info('Compiling with the following command: %s', ' '.join(args))
  proc = subprocess.Popen(args, stdout=subprocess.PIPE)
  (stdoutdata, stderrdata) = proc.communicate()
  if proc.returncode != 0:
    logging.error('JavaScript compilation failed.')
    sys.exit(1)
  else:
    out.write(stdoutdata)


def main():
  """The entrypoint for this script."""

  logging.basicConfig(format='calcdeps.py: %(message)s', level=logging.INFO)

  usage = 'usage: %prog [options] arg'
  parser = optparse.OptionParser(usage)
  parser.add_option('-i',
                    '--input',
                    dest='inputs',
                    action='append',
                    help='The inputs to calculate dependencies for. Valid '
                    'values can be files, directories, or namespaces '
                    '(ns:goog.net.XhrLite).  Only relevant to "list" and '
                    '"script" output.')
  parser.add_option('-p',
                    '--path',
                    dest='paths',
                    action='append',
                    help='The paths that should be traversed to build the '
                    'dependencies.')
  parser.add_option('-d',
                    '--dep',
                    dest='deps',
                    action='append',
                    help='Directories or files that should be traversed to '
                    'find required dependencies for the deps file. '
                    'Does not generate dependency information for names '
                    'provided by these files. Only useful in "deps" mode.')
  parser.add_option('-e',
                    '--exclude',
                    dest='excludes',
                    action='append',
                    help='Files or directories to exclude from the --path '
                    'and --input flags')
  parser.add_option('-o',
                    '--output_mode',
                    dest='output_mode',
                    action='store',
                    default='list',
                    help='The type of output to generate from this script. '
                    'Options are "list" for a list of filenames, "script" '
                    'for a single script containing the contents of all the '
                    'file, "deps" to generate a deps.js file for all '
                    'paths, or "compiled" to produce compiled output with '
                    'the Closure compiler.')
  parser.add_option('-c',
                    '--compiler_jar',
                    dest='compiler_jar',
                    action='store',
                    help='The location of the Closure compiler .jar file.')
  parser.add_option('-f',
                    '--compiler_flag',
                    '--compiler_flags', # for backwards compatability
                    dest='compiler_flags',
                    action='append',
                    help='Additional flag to pass to the Closure compiler. '
                    'May be specified multiple times to pass multiple flags.')
  parser.add_option('--output_file',
                    dest='output_file',
                    action='store',
                    help=('If specified, write output to this path instead of '
                          'writing to standard output.'))

  (options, args) = parser.parse_args()

  search_paths = GetPathsFromOptions(options)

  if options.output_file:
    out = open(options.output_file, 'w')
  else:
    out = sys.stdout

  if options.output_mode == 'deps':
    result = PrintDeps(search_paths, ExpandDirectories(options.deps or []), out)
    if not result:
      logging.error('Could not find Closure Library in the specified paths')
      sys.exit(1)

    return

  inputs = GetInputsFromOptions(options)

  logging.info('Finding Closure dependencies...')
  deps = CalculateDependencies(search_paths, inputs)
  output_mode = options.output_mode

  if output_mode == 'script':
    PrintScript(deps, out)
  elif output_mode == 'list':
    # Just print out a dep per line
    for dep in deps:
      PrintLine(dep, out)
  elif output_mode == 'compiled':
    # Make sure a .jar is specified.
    if not options.compiler_jar:
      logging.error('--compiler_jar flag must be specified if --output is '
                    '"compiled"')
      sys.exit(1)

    # User friendly version check.
    if distutils and not (distutils.version.LooseVersion(GetJavaVersion()) >
        distutils.version.LooseVersion('1.6')):
      logging.error('Closure Compiler requires Java 1.6 or higher.')
      logging.error('Please visit http://www.java.com/getjava')
      sys.exit(1)

    Compile(options.compiler_jar, deps, out, options.compiler_flags)

  else:
    logging.error('Invalid value for --output flag.')
    sys.exit(1)

if __name__ == '__main__':
  main()

########NEW FILE########
__FILENAME__ = scopify
#!/usr/bin/python2.4
#
# Copyright 2010 The Closure Library Authors. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS-IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.


"""Automatically converts codebases over to goog.scope.

Usage:
cd path/to/my/dir;
../../../../javascript/closure/bin/scopify.py

Scans every file in this directory, recursively. Looks for existing
goog.scope calls, and goog.require'd symbols. If it makes sense to
generate a goog.scope call for the file, then we will do so, and
try to auto-generate some aliases based on the goog.require'd symbols.

Known Issues:

  When a file is goog.scope'd, the file contents will be indented +2.
  This may put some lines over 80 chars. These will need to be fixed manually.

  We will only try to create aliases for capitalized names. We do not check
  to see if those names will conflict with any existing locals.

  This creates merge conflicts for every line of every outstanding change.
  If you intend to run this on your codebase, make sure your team members
  know. Better yet, send them this script so that they can scopify their
  outstanding changes and "accept theirs".

  When an alias is "captured", it can no longer be stubbed out for testing.
  Run your tests.

"""

__author__ = 'nicksantos@google.com (Nick Santos)'

import os.path
import re
import sys

REQUIRES_RE = re.compile(r"goog.require\('([^']*)'\)")

# Edit this manually if you want something to "always" be aliased.
# TODO(nicksantos): Add a flag for this.
DEFAULT_ALIASES = {}

def Transform(lines):
  """Converts the contents of a file into javascript that uses goog.scope.

  Arguments:
    lines: A list of strings, corresponding to each line of the file.
  Returns:
    A new list of strings, or None if the file was not modified.
  """
  requires = []

  # Do an initial scan to be sure that this file can be processed.
  for line in lines:
    # Skip this file if it has already been scopified.
    if line.find('goog.scope') != -1:
      return None

    # If there are any global vars or functions, then we also have
    # to skip the whole file. We might be able to deal with this
    # more elegantly.
    if line.find('var ') == 0 or line.find('function ') == 0:
      return None

    for match in REQUIRES_RE.finditer(line):
      requires.append(match.group(1))

  if len(requires) == 0:
    return None

  # Backwards-sort the requires, so that when one is a substring of another,
  # we match the longer one first.
  for val in DEFAULT_ALIASES.values():
    if requires.count(val) == 0:
      requires.append(val)

  requires.sort()
  requires.reverse()

  # Generate a map of requires to their aliases
  aliases_to_globals = DEFAULT_ALIASES.copy()
  for req in requires:
    index = req.rfind('.')
    if index == -1:
      alias = req
    else:
      alias = req[(index + 1):]

    # Don't scopify lowercase namespaces, because they may conflict with
    # local variables.
    if alias[0].isupper():
      aliases_to_globals[alias] = req

  aliases_to_matchers = {}
  globals_to_aliases = {}
  for alias, symbol in aliases_to_globals.items():
    globals_to_aliases[symbol] = alias
    aliases_to_matchers[alias] = re.compile('\\b%s\\b' % symbol)

  # Insert a goog.scope that aliases all required symbols.
  result = []

  START = 0
  SEEN_REQUIRES = 1
  IN_SCOPE = 2

  mode = START
  aliases_used = set()
  insertion_index = None
  for line in lines:
    if mode == START:
      result.append(line)

      if re.search(REQUIRES_RE, line):
        mode = SEEN_REQUIRES

    elif mode == SEEN_REQUIRES:
      if (line and
          not re.search(REQUIRES_RE, line) and
          not line.isspace()):
        result.append('goog.scope(function() {\n')
        insertion_index = len(result)
        result.append('\n')
        mode = IN_SCOPE
      else:
        result.append(line)

    if mode == IN_SCOPE:
      for symbol in requires:
        if not symbol in globals_to_aliases:
          continue

        alias = globals_to_aliases[symbol]
        matcher = aliases_to_matchers[alias]
        for match in matcher.finditer(line):
          # Check to make sure we're not in a string.
          # We do this by being as conservative as possible:
          # if there are any quote or double quote characters
          # before the symbol on this line, then bail out.
          before_symbol = line[:match.start(0)]
          if before_symbol.count('"') > 0 or before_symbol.count("'") > 0:
            continue

          line = line.replace(match.group(0), alias)
          aliases_used.add(alias)

      if line.isspace():
        # Truncate all-whitespace lines
        result.append('\n')
      else:
        result.append('  ' + line)

  if len(aliases_used):
    aliases_used = [alias for alias in aliases_used]
    aliases_used.sort()
    aliases_used.reverse()
    for alias in aliases_used:
      symbol = aliases_to_globals[alias]
      result.insert(insertion_index,
                    '  var %s = %s;\n' % (alias, symbol))
    result.append('});\n')
    return result
  else:
    return None

def TransformFileAt(path):
  """Converts a file into javascript that uses goog.scope.

  Arguments:
    path: A path to a file.
  """
  f = open(path)
  lines = Transform(f.readlines())
  if lines:
    f = open(path, 'w')
    for l in lines:
      f.write(l)
    f.close()

if __name__ == '__main__':
  args = sys.argv[1:]
  if not len(args):
    args = '.'

  for file_name in args:
    if os.path.isdir(file_name):
      for root, dirs, files in os.walk(file_name):
        for name in files:
          if name.endswith('.js') and \
              not os.path.islink(os.path.join(root, name)):
            TransformFileAt(os.path.join(root, name))
    else:
      if file_name.endswith('.js') and \
          not os.path.islink(file_name):
        TransformFileAt(file_name)

########NEW FILE########
