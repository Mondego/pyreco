__FILENAME__ = ceres
# Copyright 2011 Chris Davis
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#   http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#
#

# Ceres requires Python 2.6 or newer
import os
import struct
import json
import errno
from math import isnan
from itertools import izip
from os.path import isdir, exists, join, dirname, abspath, getsize, getmtime
from glob import glob
from bisect import bisect_left


TIMESTAMP_FORMAT = "!L"
TIMESTAMP_SIZE = struct.calcsize(TIMESTAMP_FORMAT)
DATAPOINT_FORMAT = "!d"
DATAPOINT_SIZE = struct.calcsize(DATAPOINT_FORMAT)
NAN = float('nan')
PACKED_NAN = struct.pack(DATAPOINT_FORMAT, NAN)
MAX_SLICE_GAP = 80
DEFAULT_TIMESTEP = 60
DEFAULT_SLICE_CACHING_BEHAVIOR = 'none'
SLICE_PERMS = 0644
DIR_PERMS = 0755


class CeresTree(object):
  """Represents a tree of Ceres metrics contained within a single path on disk
  This is the primary Ceres API.

  :param root: The directory root of the Ceres tree

  See :func:`setDefaultSliceCachingBehavior` to adjust caching behavior
  """
  def __init__(self, root):
    if isdir(root):
      self.root = abspath(root)
    else:
      raise ValueError("Invalid root directory '%s'" % root)
    self.nodeCache = {}

  def __repr__(self):
    return "<CeresTree[0x%x]: %s>" % (id(self), self.root)
  __str__ = __repr__

  @classmethod
  def createTree(cls, root, **props):
    """Create and returns a new Ceres tree with the given properties

    :param root: The root directory of the new Ceres tree
    :keyword \*\*props: Arbitrary key-value properties to store as tree metadata

    :returns: :class:`CeresTree`
    """

    ceresDir = join(root, '.ceres-tree')
    if not isdir(ceresDir):
      os.makedirs(ceresDir, DIR_PERMS)

    for prop,value in props.items():
      propFile = join(ceresDir, prop)
      fh = open(propFile, 'w')
      fh.write(str(value))
      fh.close()

    return cls(root)

  def walk(self, **kwargs):
    """Iterate through the nodes contained in this :class:`CeresTree`

      :keyword \*\*kwargs: Options to pass to `os.walk`

      :returns: An iterator yielding :class:`CeresNode` objects
    """
    for (fsPath, subdirs, filenames) in os.walk(self.root, **kwargs):
      if CeresNode.isNodeDir(fsPath):
        nodePath = self.getNodePath(fsPath)
        yield CeresNode(self, nodePath, fsPath)

  def getFilesystemPath(self, nodePath):
    """Get the on-disk path of a Ceres node given a metric name"""
    return join(self.root, nodePath.replace('.', os.sep))

  def getNodePath(self, fsPath):
    """Get the metric name of a Ceres node given the on-disk path"""
    fsPath = abspath(fsPath)
    if not fsPath.startswith(self.root):
      raise ValueError("path '%s' not beneath tree root '%s'" % (fsPath, self.root))

    nodePath = fsPath[len(self.root):].strip(os.sep).replace(os.sep, '.')
    return nodePath

  def hasNode(self, nodePath):
    """Returns whether the Ceres tree contains the given metric"""
    return isdir(self.getFilesystemPath(nodePath))

  def getNode(self, nodePath):
    """Returns a Ceres node given a metric name

      :param nodePath: A metric name

      :returns: :class:`CeresNode` or `None`
    """
    if nodePath not in self.nodeCache:
      fsPath = self.getFilesystemPath(nodePath)
      if CeresNode.isNodeDir(fsPath):
        self.nodeCache[nodePath] = CeresNode(self, nodePath, fsPath)
      else:
        return None

    return self.nodeCache[nodePath]

  def find(self, nodePattern, fromTime=None, untilTime=None):
    """Find nodes which match a wildcard pattern, optionally filtering on
    a time range

      :keyword nodePattern: A glob-style metric wildcard
      :keyword fromTime: Optional interval start time in unix-epoch.
      :keyword untilTime: Optional interval end time in unix-epoch.

      :returns: An iterator yielding :class:`CeresNode` objects
    """
    for fsPath in glob(self.getFilesystemPath(nodePattern)):
      if CeresNode.isNodeDir(fsPath):
        nodePath = self.getNodePath(fsPath)
        node = self.getNode(nodePath)

        if fromTime is None and untilTime is None:
          yield node
        elif node.hasDataForInterval(fromTime, untilTime):
          yield node

  def createNode(self, nodePath, **properties):
    """Creates a new metric given a new metric name and optional per-node metadata
      :keyword nodePath: The new metric name.
      :keyword \*\*properties: Arbitrary key-value properties to store as metric metadata.

      :returns: :class:`CeresNode`
    """
    return CeresNode.create(self, nodePath, **properties)

  def store(self, nodePath, datapoints):
    """Store a list of datapoints associated with a metric
      :keyword nodePath: The metric name to write to
      :keyword datapoints: A list of datapoint tuples: (timestamp, value)
    """
    node = self.getNode(nodePath)

    if node is None:
      raise NodeNotFound("The node '%s' does not exist in this tree" % nodePath)

    node.write(datapoints)

  def fetch(self, nodePath, fromTime, untilTime):
    """Fetch data within a given interval from the given metric

      :keyword nodePath: The metric name to fetch from
      :keyword fromTime: Requested interval start time in unix-epoch.
      :keyword untilTime: Requested interval end time in unix-epoch.

      :returns: :class:`TimeSeriesData`
      :raises: :class:`NodeNotFound`, :class:`InvalidRequest`, :class:`NoData`
    """
    node = self.getNode(nodePath)

    if not node:
      raise NodeNotFound("the node '%s' does not exist in this tree" % nodePath)

    return node.read(fromTime, untilTime)


class CeresNode(object):
  __slots__ = ('tree', 'nodePath', 'fsPath',
               'metadataFile', 'timeStep',
               'sliceCache', 'sliceCachingBehavior')

  def __init__(self, tree, nodePath, fsPath):
    self.tree = tree
    self.nodePath = nodePath
    self.fsPath = fsPath
    self.metadataFile = join(fsPath, '.ceres-node')
    self.timeStep = None
    self.sliceCache = None
    self.sliceCachingBehavior = DEFAULT_SLICE_CACHING_BEHAVIOR

  def __repr__(self):
    return "<CeresNode[0x%x]: %s>" % (id(self), self.nodePath)
  __str__ = __repr__

  @classmethod
  def create(cls, tree, nodePath, **properties):
    # Create the node directory
    fsPath = tree.getFilesystemPath(nodePath)
    os.makedirs(fsPath, DIR_PERMS)

    # Create the initial metadata
    timeStep = properties['timeStep'] = properties.get('timeStep', DEFAULT_TIMESTEP)
    node = cls(tree, nodePath, fsPath)
    node.writeMetadata(properties)

    # Create the initial data file
    #now = int( time.time() )
    #baseTime = now - (now % timeStep)
    #slice = CeresSlice.create(node, baseTime, timeStep)

    return node

  @staticmethod
  def isNodeDir(path):
    return isdir(path) and exists(join(path, '.ceres-node'))

  @classmethod
  def fromFilesystemPath(cls, fsPath):
    dirPath = dirname(fsPath)

    while True:
      ceresDir = join(dirPath, '.ceres-tree')
      if isdir(ceresDir):
        tree = CeresTree(dirPath)
        nodePath = tree.getNodePath(fsPath)
        return cls(tree, nodePath, fsPath)

      dirPath = dirname(dirPath)

      if dirPath == '/':
        raise ValueError("the path '%s' is not in a ceres tree" % fsPath)

  @property
  def slice_info(self):
    return [(slice.startTime, slice.endTime, slice.timeStep) for slice in self.slices]

  def readMetadata(self):
    metadata = json.load(open(self.metadataFile, 'r'))
    self.timeStep = int(metadata['timeStep'])
    return metadata

  def writeMetadata(self, metadata):
    self.timeStep = int(metadata['timeStep'])

    f = open(self.metadataFile, 'w')
    json.dump(metadata, f)
    f.close()

  @property
  def slices(self):
    if self.sliceCache:
      if self.sliceCachingBehavior == 'all':
        for slice in self.sliceCache:
          yield slice

      elif self.sliceCachingBehavior == 'latest':
        yield self.sliceCache
        infos = self.readSlices()
        for info in infos[1:]:
          yield CeresSlice(self, *info)

    else:
      if self.sliceCachingBehavior == 'all':
        self.sliceCache = [CeresSlice(self, *info) for info in self.readSlices()]
        for slice in self.sliceCache:
          yield slice

      elif self.sliceCachingBehavior == 'latest':
        infos = self.readSlices()
        if infos:
          self.sliceCache = CeresSlice(self, *infos[0])
          yield self.sliceCache

        for info in infos[1:]:
          yield CeresSlice(self, *info)

      elif self.sliceCachingBehavior == 'none':
        for info in self.readSlices():
          yield CeresSlice(self, *info)

      else:
        raise ValueError("invalid caching behavior configured '%s'" % self.sliceCachingBehavior)

  def readSlices(self):
    if not exists(self.fsPath):
      raise NodeDeleted()

    slice_info = []
    for filename in os.listdir(self.fsPath):
      if filename.endswith('.slice'):
        startTime, timeStep = filename[:-6].split('@')
        slice_info.append((int(startTime), int(timeStep)))

    slice_info.sort(reverse=True)
    return slice_info

  def setSliceCachingBehavior(self, behavior):
    behavior = behavior.lower()
    if behavior not in ('none', 'all', 'latest'):
      raise ValueError("invalid caching behavior '%s'" % behavior)

    self.sliceCachingBehavior = behavior
    self.sliceCache = None

  def clearSliceCache(self):
    self.sliceCache = None

  def hasDataForInterval(self, fromTime, untilTime):
    slices = list(self.slices)
    if not slices:
      return False

    earliestData = slices[-1].startTime
    latestData = slices[0].endTime

    return ((fromTime is None) or (fromTime < latestData)) and \
           ((untilTime is None) or (untilTime > earliestData))

  def read(self, fromTime, untilTime):
    if self.timeStep is None:
      self.readMetadata()

    # Normalize the timestamps to fit proper intervals
    fromTime = int(fromTime - (fromTime % self.timeStep) + self.timeStep)
    untilTime = int(untilTime - (untilTime % self.timeStep) + self.timeStep)

    sliceBoundary = None  # to know when to split up queries across slices
    resultValues = []
    earliestData = None

    for slice in self.slices:
      # if the requested interval starts after the start of this slice
      if fromTime >= slice.startTime:
        try:
          series = slice.read(fromTime, untilTime)
        except NoData:
          break

        earliestData = series.startTime

        rightMissing = (untilTime - series.endTime) / self.timeStep
        rightNulls = [None for i in range(rightMissing - len(resultValues))]
        resultValues = series.values + rightNulls + resultValues
        break

      # or if slice contains data for part of the requested interval
      elif untilTime >= slice.startTime:
        # Split the request up if it straddles a slice boundary
        if (sliceBoundary is not None) and untilTime > sliceBoundary:
          requestUntilTime = sliceBoundary
        else:
          requestUntilTime = untilTime

        try:
          series = slice.read(slice.startTime, requestUntilTime)
        except NoData:
          continue

        earliestData = series.startTime

        rightMissing = (requestUntilTime - series.endTime) / self.timeStep
        rightNulls = [None for i in range(rightMissing)]
        resultValues = series.values + rightNulls + resultValues

      # this is the right-side boundary on the next iteration
      sliceBoundary = slice.startTime

    # The end of the requested interval predates all slices
    if earliestData is None:
      missing = int(untilTime - fromTime) / self.timeStep
      resultValues = [None for i in range(missing)]

    # Left pad nulls if the start of the requested interval predates all slices
    else:
      leftMissing = (earliestData - fromTime) / self.timeStep
      leftNulls = [None for i in range(leftMissing)]
      resultValues = leftNulls + resultValues

    return TimeSeriesData(fromTime, untilTime, self.timeStep, resultValues)

  def write(self, datapoints):
    if self.timeStep is None:
      self.readMetadata()

    if not datapoints:
      return

    sequences = self.compact(datapoints)
    needsEarlierSlice = []  # keep track of sequences that precede all existing slices

    while sequences:
      sequence = sequences.pop()
      timestamps = [t for t,v in sequence]
      beginningTime = timestamps[0]
      endingTime = timestamps[-1]
      sliceBoundary = None  # used to prevent writing sequences across slice boundaries
      slicesExist = False

      for slice in self.slices:
        if slice.timeStep != self.timeStep:
          continue

        slicesExist = True

        # truncate sequence so it doesn't cross the slice boundaries
        if beginningTime >= slice.startTime:
          print slice.startTime
          if sliceBoundary is None:
            sequenceWithinSlice = sequence
          else:
            # index of highest timestamp that doesn't exceed sliceBoundary
            boundaryIndex = bisect_left(timestamps, sliceBoundary)
            sequenceWithinSlice = sequence[:boundaryIndex]

          try:
            slice.write(sequenceWithinSlice)
          except SliceGapTooLarge:
            newSlice = CeresSlice.create(self, beginningTime, slice.timeStep)
            newSlice.write(sequenceWithinSlice)
            self.sliceCache = None
          except SliceDeleted:
            self.sliceCache = None
            self.write(datapoints)  # recurse to retry
            return

          sequence = []
          break

        # sequence straddles the current slice, write the right side
        # left side will be taken up in the next slice down
        elif endingTime >= slice.startTime:
          # index of lowest timestamp that doesn't precede slice.startTime
          boundaryIndex = bisect_left(timestamps, slice.startTime)
          sequenceWithinSlice = sequence[boundaryIndex:]
          # write the leftovers on the next earlier slice
          sequence = sequence[:boundaryIndex]
          slice.write(sequenceWithinSlice)

        if not sequence:
          break

        sliceBoundary = slice.startTime

      else: # list exhausted with stuff still to write
        needsEarlierSlice.append(sequence)

      if not slicesExist:
        sequences.append(sequence)
        needsEarlierSlice = sequences
        break

    for sequence in needsEarlierSlice:
      slice = CeresSlice.create(self, int(sequence[0][0]), self.timeStep)
      slice.write(sequence)
      self.clearSliceCache()

  def compact(self, datapoints):
    datapoints = sorted((int(timestamp), float(value))
                         for timestamp, value in datapoints
                         if value is not None)
    sequences = []
    sequence = []
    minimumTimestamp = 0  # used to avoid duplicate intervals

    for timestamp, value in datapoints:
      timestamp -= timestamp % self.timeStep  # round it down to a proper interval

      if not sequence:
        sequence.append((timestamp, value))

      else:
        if not timestamp > minimumTimestamp:  # drop duplicate intervals
          continue

        if timestamp == sequence[-1][0] + self.timeStep:  # append contiguous datapoints
          sequence.append((timestamp, value))

        else:  # start a new sequence if not contiguous
          sequences.append(sequence)
          sequence = [(timestamp, value)]

      minimumTimestamp = timestamp

    if sequence:
      sequences.append(sequence)

    return sequences


class CeresSlice(object):
  __slots__ = ('node', 'startTime', 'timeStep', 'fsPath')

  def __init__(self, node, startTime, timeStep):
    self.node = node
    self.startTime = startTime
    self.timeStep = timeStep
    self.fsPath = join(node.fsPath, '%d@%d.slice' % (startTime, timeStep))

  def __repr__(self):
    return "<CeresSlice[0x%x]: %s>" % (id(self), self.fsPath)
  __str__ = __repr__

  @property
  def isEmpty(self):
    return getsize(self.fsPath) == 0

  @property
  def endTime(self):
    return self.startTime + ((getsize(self.fsPath) / DATAPOINT_SIZE) * self.timeStep)

  @property
  def mtime(self):
    return getmtime(self.fsPath)

  @classmethod
  def create(cls, node, startTime, timeStep):
    slice = cls(node, startTime, timeStep)
    fileHandle = open(slice.fsPath, 'wb')
    fileHandle.close()
    os.chmod(slice.fsPath, SLICE_PERMS)
    return slice

  def read(self, fromTime, untilTime):
    timeOffset = int(fromTime) - self.startTime

    if timeOffset < 0:
      raise InvalidRequest("requested time range (%d, %d) precedes this slice: %d" % (fromTime, untilTime, self.startTime))

    pointOffset = timeOffset / self.timeStep
    byteOffset = pointOffset * DATAPOINT_SIZE

    if byteOffset >= getsize(self.fsPath):
      raise NoData()

    fileHandle = open(self.fsPath, 'rb')
    fileHandle.seek(byteOffset)

    timeRange = int(untilTime - fromTime)
    pointRange = timeRange / self.timeStep
    byteRange = pointRange * DATAPOINT_SIZE
    packedValues = fileHandle.read(byteRange)

    pointsReturned = len(packedValues) / DATAPOINT_SIZE
    format = '!' + ('d' * pointsReturned)
    values = struct.unpack(format, packedValues)
    values = [v if not isnan(v) else None for v in values]

    endTime = fromTime + (len(values) * self.timeStep)
    #print '[DEBUG slice.read] startTime=%s fromTime=%s untilTime=%s' % (self.startTime, fromTime, untilTime)
    #print '[DEBUG slice.read] timeInfo = (%s, %s, %s)' % (fromTime, endTime, self.timeStep)
    #print '[DEBUG slice.read] values = %s' % str(values)
    return TimeSeriesData(fromTime, endTime, self.timeStep, values)

  def write(self, sequence):
    beginningTime = sequence[0][0]
    timeOffset = beginningTime - self.startTime
    pointOffset = timeOffset / self.timeStep
    byteOffset = pointOffset * DATAPOINT_SIZE

    values = [v for t,v in sequence]
    format = '!' + ('d' * len(values))
    packedValues = struct.pack(format, *values)

    try:
      filesize = getsize(self.fsPath)
    except OSError, e:
      if e.errno == errno.ENOENT:
        raise SliceDeleted()
      else:
        raise

    byteGap = byteOffset - filesize
    if byteGap > 0:  # pad the allowable gap with nan's

      if byteGap > MAX_SLICE_GAP:
        raise SliceGapTooLarge()
      else:
        pointGap = byteGap / DATAPOINT_SIZE
        packedGap = PACKED_NAN * pointGap
        packedValues = packedGap + packedValues
        byteOffset -= byteGap

    with file(self.fsPath, 'r+b') as fileHandle:
      try:
        fileHandle.seek(byteOffset)
      except IOError:
        print " IOError: fsPath=%s byteOffset=%d size=%d sequence=%s" % (self.fsPath, byteOffset, filesize, sequence)
        raise
      fileHandle.write(packedValues)

  def deleteBefore(self, t):
    if not exists(self.fsPath):
      raise SliceDeleted()

    t = t - (t % self.timeStep)
    timeOffset = t - self.startTime
    if timeOffset < 0:
      return

    pointOffset = timeOffset / self.timeStep
    byteOffset = pointOffset * DATAPOINT_SIZE
    if not byteOffset:
      return

    self.node.clearSliceCache()
    with file(self.fsPath, 'r+b') as fileHandle:
      fileHandle.seek(byteOffset)
      fileData = fileHandle.read()
      if fileData:
        fileHandle.seek(0)
        fileHandle.write(fileData)
        fileHandle.truncate()
        fileHandle.close()
        newFsPath = join(dirname(self.fsPath), "%d@%d.slice" % (t, self.timeStep))
        os.rename(self.fsPath, newFsPath)
      else:
        os.unlink(self.fsPath)
        raise SliceDeleted()

  def __cmp__(self, other):
    return cmp(self.startTime, other.startTime)


class TimeSeriesData(object):
  __slots__ = ('startTime', 'endTime', 'timeStep', 'values')

  def __init__(self, startTime, endTime, timeStep, values):
    self.startTime = startTime
    self.endTime = endTime
    self.timeStep = timeStep
    self.values = values

  @property
  def timestamps(self):
    return xrange(self.startTime, self.endTime, self.timeStep)

  def __iter__(self):
    return izip(self.timestamps, self.values)

  def __len__(self):
    return len(self.values)

  def merge(self, other):
    for timestamp, value in other:
      if value is None:
        continue

      timestamp -= timestamp % self.timeStep
      if timestamp < self.startTime:
        continue

      index = int((timestamp - self.startTime) / self.timeStep)

      try:
        if self.values[index] is None:
          self.values[index] = value
      except IndexError:
        continue


class CorruptNode(Exception):
  def __init__(self, node, problem):
    Exception.__init__(self, problem)
    self.node = node
    self.problem = problem


class NoData(Exception):
  pass


class NodeNotFound(Exception):
  pass


class NodeDeleted(Exception):
  pass


class InvalidRequest(Exception):
  pass


class SliceGapTooLarge(Exception):
  "For internal use only"


class SliceDeleted(Exception):
  pass


def getTree(path):
  while path not in (os.sep, ''):
    if isdir(join(path, '.ceres-tree')):
      return CeresTree(path)

    path = dirname(path)


def setDefaultSliceCachingBehavior(behavior):
  global DEFAULT_SLICE_CACHING_BEHAVIOR

  behavior = behavior.lower()
  if behavior not in ('none', 'all', 'latest'):
    raise ValueError("invalid caching behavior '%s'" % behavior)

  DEFAULT_SLICE_CACHING_BEHAVIOR = behavior

########NEW FILE########
__FILENAME__ = conf
# -*- coding: utf-8 -*-
#
# ceres documentation build configuration file, created by
# sphinx-quickstart on Thu Jan  3 04:15:28 2013.
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
sys.path.insert(0, os.path.abspath('..'))

# -- General configuration -----------------------------------------------------

# If your documentation needs a minimal Sphinx version, state it here.
#needs_sphinx = '1.0'

# Add any Sphinx extension module names here, as strings. They can be extensions
# coming with Sphinx (named 'sphinx.ext.*') or your custom ones.
extensions = ['sphinx.ext.autodoc', 'sphinx.ext.intersphinx', 'sphinx.ext.coverage', 'sphinx.ext.ifconfig', 'sphinx.ext.viewcode']

# Add any paths that contain templates here, relative to this directory.
templates_path = ['.templates']

# The suffix of source filenames.
source_suffix = '.rst'

# The encoding of source files.
#source_encoding = 'utf-8-sig'

# The master toctree document.
master_doc = 'index'

# General information about the project.
project = u'ceres'
copyright = u'2011, Chris Davis'

# The version info for the project you're documenting, acts as replacement for
# |version| and |release|, also used in various other places throughout the
# built documents.
#
# The short X.Y version.
version = '0.10.0'
# The full version, including alpha/beta/rc tags.
release = '0.10.0'

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
htmlhelp_basename = 'ceresdoc'


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
  ('index', 'ceres.tex', u'ceres Documentation',
   u'Chris Davis', 'manual'),
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
    ('index', 'ceres', u'ceres Documentation',
     [u'Chris Davis'], 1)
]

# If true, show URL addresses after external links.
#man_show_urls = False


# -- Options for Texinfo output ------------------------------------------------

# Grouping the document tree into Texinfo files. List of tuples
# (source start file, target name, title, author,
#  dir menu entry, description, category)
texinfo_documents = [
  ('index', 'ceres', u'ceres Documentation',
   u'Chris Davis', 'ceres', 'One line description of project.',
   'Miscellaneous'),
]

# Documents to append as an appendix to all manuals.
#texinfo_appendices = []

# If false, no module index is generated.
#texinfo_domain_indices = True

# How to display URL addresses: 'footnote', 'no', or 'inline'.
#texinfo_show_urls = 'footnote'


# Example configuration for intersphinx: refer to the Python standard library.
intersphinx_mapping = {'http://docs.python.org/': None}

########NEW FILE########
__FILENAME__ = test_ceres
from unittest import TestCase
from mock import ANY, Mock, call, mock_open, patch

from ceres import *


def fetch_mock_open_writes(open_mock):
  handle = open_mock()
  return ''.join([ c[0][0] for c in handle.write.call_args_list])

class ModuleFunctionsTest(TestCase):
  @patch('ceres.isdir', new=Mock(return_value=False))
  @patch('ceres.CeresTree', new=Mock(spec=CeresTree))
  def test_get_tree_with_no_tree(self):
    tree = getTree('/graphite/storage/ceres/foo/bar')
    self.assertEqual(None, tree)

  @patch('ceres.CeresTree', spec=CeresTree)
  @patch('ceres.isdir')
  def test_get_tree_with_tree_samedir(self, isdir_mock, ceres_tree_mock):
    isdir_mock.return_value = True
    tree = getTree('/graphite/storage/ceres')
    self.assertNotEqual(None, tree)
    isdir_mock.assert_called_once_with('/graphite/storage/ceres/.ceres-tree')
    ceres_tree_mock.assert_called_once_with('/graphite/storage/ceres')


class TimeSeriesDataTest(TestCase):
  def setUp(self):
    self.time_series = TimeSeriesData(0, 50, 5, [float(x) for x in xrange(0, 10)])

  def test_timestamps_property(self):
    self.assertEqual(10, len(self.time_series.timestamps))
    self.assertEqual(0, self.time_series.timestamps[0])
    self.assertEqual(45, self.time_series.timestamps[-1])

  def test_iter_values(self):
    values = list(self.time_series)
    self.assertEqual(10, len(values))
    self.assertEqual((0, 0.0), values[0])
    self.assertEqual((45, 9.0), values[-1])

  def test_merge_no_missing(self):
    # merge only has effect if time series has no gaps
    other_series = TimeSeriesData(0, 25, 5, [float(x * x) for x in xrange(1, 6)])
    original_values = list(self.time_series)
    self.time_series.merge(other_series)
    self.assertEqual(original_values, list(self.time_series))

  def test_merge_with_empty(self):
    new_series = TimeSeriesData(0, 50, 5, [None] * 10)
    new_series.merge(self.time_series)
    self.assertEqual(list(self.time_series), list(new_series))

  def test_merge_with_holes(self):
    values = []
    for x in xrange(0, 10):
      if x % 2 == 0:
        values.append(x)
      else:
        values.append(None)
    new_series = TimeSeriesData(0, 50, 5, values)
    new_series.merge(self.time_series)
    self.assertEqual(list(self.time_series), list(new_series))


class CeresTreeTest(TestCase):
  def setUp(self):
    with patch('ceres.isdir', new=Mock(return_value=True)):
      self.ceres_tree = CeresTree('/graphite/storage/ceres')

  @patch('ceres.isdir', new=Mock(return_value=False))
  def test_init_invalid(self):
    self.assertRaises(ValueError, CeresTree, '/nonexistent_path')

  @patch('ceres.isdir', new=Mock(return_value=True))
  @patch('ceres.abspath')
  def test_init_valid(self, abspath_mock):
    abspath_mock.return_value = '/var/graphite/storage/ceres'
    tree = CeresTree('/graphite/storage/ceres')
    abspath_mock.assert_called_once_with('/graphite/storage/ceres')
    self.assertEqual('/var/graphite/storage/ceres', tree.root)

  @patch('ceres.isdir', new=Mock(return_value=False))
  @patch.object(CeresTree, '__init__')
  @patch('os.makedirs')
  def test_create_tree_new_dir(self, makedirs_mock, ceres_tree_init_mock):
    ceres_tree_init_mock.return_value = None
    with patch('__builtin__.open', mock_open()) as open_mock:
      CeresTree.createTree('/graphite/storage/ceres')
      makedirs_mock.assert_called_once_with('/graphite/storage/ceres/.ceres-tree', DIR_PERMS)
      self.assertFalse(open_mock.called)
      ceres_tree_init_mock.assert_called_once_with('/graphite/storage/ceres')

  @patch('ceres.isdir', new=Mock(return_value=True))
  @patch.object(CeresTree, '__init__')
  @patch('os.makedirs')
  def test_create_tree_existing_dir(self, makedirs_mock, ceres_tree_init_mock):
    ceres_tree_init_mock.return_value = None
    with patch('__builtin__.open', mock_open()) as open_mock:
      CeresTree.createTree('/graphite/storage/ceres')
      self.assertFalse(makedirs_mock.called)
      self.assertFalse(open_mock.called)
      ceres_tree_init_mock.assert_called_once_with('/graphite/storage/ceres')

  @patch('ceres.isdir', new=Mock(return_value=True))
  @patch.object(CeresTree, '__init__', new=Mock(return_value=None))
  @patch('os.makedirs', new=Mock())
  def test_create_tree_write_props(self):
    props = {
      "foo_prop": "foo_value",
      "bar_prop": "bar_value"}
    with patch('__builtin__.open', mock_open()) as open_mock:
      CeresTree.createTree('/graphite/storage/ceres', **props)
      for (prop,value) in props.items():
        open_mock.assert_any_call(join('/graphite/storage/ceres', '.ceres-tree', prop), 'w')
        open_mock.return_value.write.assert_any_call(value)

  @patch('ceres.abspath', new=Mock(side_effect=lambda x: x))
  def test_get_node_path_clean(self):
    result = self.ceres_tree.getNodePath('/graphite/storage/ceres/metric/foo')
    self.assertEqual('metric.foo', result)

  @patch('ceres.abspath', new=Mock(side_effect=lambda x: x))
  def test_get_node_path_trailing_slash(self):
    result = self.ceres_tree.getNodePath('/graphite/storage/ceres/metric/foo/')
    self.assertEqual('metric.foo', result)

  @patch('ceres.abspath', new=Mock(side_effect=lambda x: x))
  def test_get_node_path_outside_tree(self):
    self.assertRaises(ValueError, self.ceres_tree.getNodePath, '/metric/foo')

  @patch('ceres.CeresNode', spec=CeresNode)
  def test_get_node_uncached(self, ceres_node_mock):
    ceres_node_mock.isNodeDir.return_value = True
    result = self.ceres_tree.getNode('metrics.foo')
    ceres_node_mock.assert_called_once_with(
      self.ceres_tree,
      'metrics.foo',
      '/graphite/storage/ceres/metrics/foo')
    self.assertEqual(result, ceres_node_mock())

  @patch('ceres.CeresNode', spec=CeresNode)
  @patch('ceres.abspath', new=Mock(side_effect=lambda x: x))
  @patch('ceres.glob', new=Mock(side_effect=lambda x: [x]))
  def test_find_explicit_metric(self, ceres_node_mock):
    ceres_node_mock.isNodeDir.return_value = True
    result = list(self.ceres_tree.find('metrics.foo'))
    self.assertEqual(1, len(result))
    self.assertEqual(result[0], ceres_node_mock())

  @patch('ceres.CeresNode', spec=CeresNode)
  @patch('ceres.abspath', new=Mock(side_effect=lambda x: x))
  @patch('ceres.glob')
  def test_find_wildcard(self, glob_mock, ceres_node_mock):
    matches = ['foo', 'bar', 'baz']
    glob_mock.side_effect = lambda x: [x.replace('*', m) for m in matches]
    ceres_node_mock.isNodeDir.return_value = True
    result = list(self.ceres_tree.find('metrics.*'))
    self.assertEqual(3, len(result))
    ceres_node_mock.assert_any_call(self.ceres_tree, 'metrics.foo', ANY)
    ceres_node_mock.assert_any_call(self.ceres_tree, 'metrics.bar', ANY)
    ceres_node_mock.assert_any_call(self.ceres_tree, 'metrics.baz', ANY)

  @patch('ceres.CeresNode', spec=CeresNode)
  @patch('ceres.abspath', new=Mock(side_effect=lambda x: x))
  @patch('ceres.glob', new=Mock(return_value=[]))
  def test_find_wildcard_no_matches(self, ceres_node_mock):
    ceres_node_mock.isNodeDir.return_value = False
    result = list(self.ceres_tree.find('metrics.*'))
    self.assertEqual(0, len(result))
    self.assertFalse(ceres_node_mock.called)

  @patch('ceres.CeresNode', spec=CeresNode)
  @patch('ceres.abspath', new=Mock(side_effect=lambda x: x))
  @patch('ceres.glob', new=Mock(side_effect=lambda x: [x]))
  def test_find_metric_with_interval(self, ceres_node_mock):
    ceres_node_mock.isNodeDir.return_value = True
    ceres_node_mock.return_value.hasDataForInterval.return_value = False
    result = list(self.ceres_tree.find('metrics.foo', 0, 1000))
    self.assertEqual(0, len(result))
    ceres_node_mock.return_value.hasDataForInterval.assert_called_once_with(0, 1000)

  @patch('ceres.CeresNode', spec=CeresNode)
  @patch('ceres.abspath', new=Mock(side_effect=lambda x: x))
  @patch('ceres.glob', new=Mock(side_effect=lambda x: [x]))
  def test_find_metric_with_interval_not_found(self, ceres_node_mock):
    ceres_node_mock.isNodeDir.return_value = True
    ceres_node_mock.return_value.hasDataForInterval.return_value = True
    result = list(self.ceres_tree.find('metrics.foo', 0, 1000))
    self.assertEqual(result[0], ceres_node_mock())
    ceres_node_mock.return_value.hasDataForInterval.assert_called_once_with(0, 1000)

  def test_store_invalid_node(self):
    with patch.object(self.ceres_tree, 'getNode', new=Mock(return_value=None)):
      datapoints = [(100, 1.0)]
      self.assertRaises(NodeNotFound, self.ceres_tree.store, 'metrics.foo', datapoints)

  @patch('ceres.CeresNode', spec=CeresNode)
  def test_store_valid_node(self, ceres_node_mock):
    datapoints = [(100, 1.0)]
    self.ceres_tree.store('metrics.foo', datapoints)
    ceres_node_mock.assert_called_once_with(self.ceres_tree, 'metrics.foo', ANY)
    ceres_node_mock.return_value.write.assert_called_once_with(datapoints)

  def fetch_invalid_node(self):
    with patch.object(self.ceres_tree, 'getNode', new=Mock(return_value=None)):
      self.assertRaises(NodeNotFound, self.ceres_tree.fetch, 'metrics.foo')

  @patch('ceres.CeresNode', spec=CeresNode)
  def fetch_metric(self, ceres_node_mock):
    read_mock = ceres_node_mock.return_value.read
    read_mock.return_value = Mock(spec=TimeSeriesData)
    result = self.ceres_tree.fetch('metrics.foo', 0, 1000)
    ceres_node_mock.assert_called_once_with(self.ceres_tree, 'metrics.foo', ANY)
    read_mock.assert_called_once_with(0, 1000)
    self.assertEqual(Mock(spec=TimeSeriesData), result)


class CeresNodeTest(TestCase):
  def setUp(self):
    with patch('ceres.isdir', new=Mock(return_value=True)):
      with patch('ceres.exists', new=Mock(return_value=True)):
        self.ceres_tree = CeresTree('/graphite/storage/ceres')
        self.ceres_node = CeresNode(self.ceres_tree, 'sample_metric', '/graphite/storage/ceres/sample_metric')
        self.ceres_node.timeStep = 60

    slice_configs = [
      ( 1200, 1800, 60 ),
      ( 600, 1200, 60 )]

    self.ceres_slices = []
    for start, end, step in slice_configs:
      slice_mock = Mock(spec=CeresSlice)
      slice_mock.startTime = start
      slice_mock.endTime = end
      slice_mock.timeStep = step

      self.ceres_slices.append(slice_mock)


  def test_init_sets_default_cache_behavior(self):
    ceres_node = CeresNode(self.ceres_tree, 'sample_metric', '/graphite/storage/ceres/sample_metric')
    self.assertEqual(DEFAULT_SLICE_CACHING_BEHAVIOR, ceres_node.sliceCachingBehavior)

  @patch('ceres.os.makedirs', new=Mock())
  @patch('ceres.CeresNode.writeMetadata')
  def test_create_sets_a_default_timestep(self, write_metadata_mock):
    ceres_node = CeresNode.create(self.ceres_tree, 'sample_metric')
    write_metadata_mock.assert_called_with(dict(timeStep=DEFAULT_TIMESTEP))

  @patch('ceres.os.makedirs', new=Mock())
  @patch('ceres.CeresNode.writeMetadata', new=Mock())
  def test_create_returns_new_ceres_node(self):
    ceres_node = CeresNode.create(self.ceres_tree, 'sample_metric')
    self.assertTrue(isinstance(ceres_node, CeresNode))

  def test_write_metadata(self):
    import json

    open_mock = mock_open()
    metadata = dict(timeStep=60, aggregationMethod='avg')
    with patch('__builtin__.open', open_mock):
      self.ceres_node.writeMetadata(metadata)
    self.assertEquals(json.dumps(metadata), fetch_mock_open_writes(open_mock))

  def test_read_metadata_sets_timestep(self):
    import json

    metadata = dict(timeStep=60, aggregationMethod='avg')
    json_metadata = json.dumps(metadata)
    open_mock = mock_open(read_data=json_metadata)
    with patch('__builtin__.open', open_mock):
      self.ceres_node.readMetadata()
    open_mock().read.assert_called_once()
    self.assertEqual(60, self.ceres_node.timeStep)

  def test_set_slice_caching_behavior_validates_names(self):
    self.ceres_node.setSliceCachingBehavior('none')
    self.assertEquals('none', self.ceres_node.sliceCachingBehavior)
    self.ceres_node.setSliceCachingBehavior('all')
    self.assertEquals('all', self.ceres_node.sliceCachingBehavior)
    self.ceres_node.setSliceCachingBehavior('latest')
    self.assertEquals('latest', self.ceres_node.sliceCachingBehavior)
    self.assertRaises(ValueError, self.ceres_node.setSliceCachingBehavior, 'foo')
    # Assert unchanged
    self.assertEquals('latest', self.ceres_node.sliceCachingBehavior)

  def test_slices_is_a_generator(self):
    from types import GeneratorType

    self.assertTrue(isinstance(self.ceres_node.slices, GeneratorType))

  def test_slices_returns_cached_set_when_behavior_is_all(self):
    def mock_slice():
      return Mock(spec=CeresSlice)

    self.ceres_node.setSliceCachingBehavior('all')
    cached_contents = [ mock_slice for c in range(4) ]
    self.ceres_node.sliceCache = cached_contents
    with patch('ceres.CeresNode.readSlices') as read_slices_mock:
      slice_list = list(self.ceres_node.slices)
      self.assertFalse(read_slices_mock.called)

    self.assertEquals(cached_contents, slice_list)

  def test_slices_returns_first_cached_when_behavior_is_latest(self):
    self.ceres_node.setSliceCachingBehavior('latest')
    cached_contents = Mock(spec=CeresSlice)
    self.ceres_node.sliceCache = cached_contents

    read_slices_mock = Mock(return_value=[])
    with patch('ceres.CeresNode.readSlices', new=read_slices_mock):
      slice_iter = self.ceres_node.slices
      self.assertEquals(cached_contents, slice_iter.next())
      # We should be yielding cached before trying to read
      self.assertFalse(read_slices_mock.called)

  def test_slices_reads_remaining_when_behavior_is_latest(self):
    self.ceres_node.setSliceCachingBehavior('latest')
    cached_contents = Mock(spec=CeresSlice)
    self.ceres_node.sliceCache = cached_contents

    read_slices_mock = Mock(return_value=[(0,60)])
    with patch('ceres.CeresNode.readSlices', new=read_slices_mock):
      slice_iter = self.ceres_node.slices
      slice_iter.next()

      # *now* we expect to read from disk
      try:
        while True:
          slice_iter.next()
      except StopIteration:
        pass

    read_slices_mock.assert_called_once_with()

  def test_slices_reads_from_disk_when_behavior_is_none(self):
    self.ceres_node.setSliceCachingBehavior('none')
    read_slices_mock = Mock(return_value=[(0,60)])
    with patch('ceres.CeresNode.readSlices', new=read_slices_mock):
      slice_iter = self.ceres_node.slices
      slice_iter.next()

    read_slices_mock.assert_called_once_with()

  def test_slices_reads_from_disk_when_cache_empty_and_behavior_all(self):
    self.ceres_node.setSliceCachingBehavior('all')
    read_slices_mock = Mock(return_value=[(0,60)])
    with patch('ceres.CeresNode.readSlices', new=read_slices_mock):
      slice_iter = self.ceres_node.slices
      slice_iter.next()

    read_slices_mock.assert_called_once_with()

  def test_slices_reads_from_disk_when_cache_empty_and_behavior_latest(self):
    self.ceres_node.setSliceCachingBehavior('all')
    read_slices_mock = Mock(return_value=[(0,60)])
    with patch('ceres.CeresNode.readSlices', new=read_slices_mock):
      slice_iter = self.ceres_node.slices
      slice_iter.next()

    read_slices_mock.assert_called_once_with()

  @patch('ceres.exists', new=Mock(return_value=False))
  def test_read_slices_raises_when_node_doesnt_exist(self):
    self.assertRaises(NodeDeleted, self.ceres_node.readSlices)

  @patch('ceres.exists', new=Mock(return_Value=True))
  def test_read_slices_ignores_not_slices(self):
    listdir_mock = Mock(return_value=['0@60.slice', '0@300.slice', 'foo'])
    with patch('ceres.os.listdir', new=listdir_mock):
      self.assertEquals(2, len(self.ceres_node.readSlices()))

  @patch('ceres.exists', new=Mock(return_Value=True))
  def test_read_slices_parses_slice_filenames(self):
    listdir_mock = Mock(return_value=['0@60.slice', '0@300.slice'])
    with patch('ceres.os.listdir', new=listdir_mock):
      slice_infos = self.ceres_node.readSlices()
      self.assertTrue((0,60) in slice_infos)
      self.assertTrue((0,300) in slice_infos)

  @patch('ceres.exists', new=Mock(return_Value=True))
  def test_read_slices_reverse_sorts_by_time(self):
    listdir_mock = Mock(return_value=[
      '0@60.slice',
      '320@300.slice',
      '120@120.slice',
      '0@120.slice',
      '600@300.slice'])

    with patch('ceres.os.listdir', new=listdir_mock):
      slice_infos = self.ceres_node.readSlices()
      slice_timestamps = [ s[0] for s in slice_infos ]
      self.assertEqual([600,320,120,0,0], slice_timestamps)

  def test_no_data_exists_if_no_slices_exist(self):
    with patch('ceres.CeresNode.readSlices', new=Mock(return_value=[])):
      self.assertFalse(self.ceres_node.hasDataForInterval(0,60))

  def test_no_data_exists_if_no_slices_exist_and_no_time_specified(self):
    with patch('ceres.CeresNode.readSlices', new=Mock(return_value=[])):
      self.assertFalse(self.ceres_node.hasDataForInterval(None,None))

  def test_data_exists_if_slices_exist_and_no_time_specified(self):
    with patch('ceres.CeresNode.slices', new=self.ceres_slices):
      self.assertTrue(self.ceres_node.hasDataForInterval(None,None))

  def test_data_exists_if_slice_covers_interval_completely(self):
    with patch('ceres.CeresNode.slices', new=[self.ceres_slices[0]]):
      self.assertTrue(self.ceres_node.hasDataForInterval(1200,1800))

  def test_data_exists_if_slice_covers_interval_end(self):
    with patch('ceres.CeresNode.slices', new=[self.ceres_slices[0]]):
      self.assertTrue(self.ceres_node.hasDataForInterval(600, 1260))

  def test_data_exists_if_slice_covers_interval_start(self):
    with patch('ceres.CeresNode.slices', new=[self.ceres_slices[0]]):
      self.assertTrue(self.ceres_node.hasDataForInterval(1740, 2100))

  def test_no_data_exists_if_slice_touches_interval_end(self):
    with patch('ceres.CeresNode.slices', new=[self.ceres_slices[0]]):
      self.assertFalse(self.ceres_node.hasDataForInterval(600, 1200))

  def test_no_data_exists_if_slice_touches_interval_start(self):
    with patch('ceres.CeresNode.slices', new=[self.ceres_slices[0]]):
      self.assertFalse(self.ceres_node.hasDataForInterval(1800, 2100))

  def test_compact_returns_empty_if_passed_empty(self):
    self.assertEqual([], self.ceres_node.compact([]))

  def test_compact_filters_null_values(self):
    self.assertEqual([], self.ceres_node.compact([(60,None)]))

  def test_compact_rounds_timestamps_down_to_step(self):
    self.assertEqual([[(600,0)]], self.ceres_node.compact([(605,0)]))

  def test_compact_drops_duplicate_timestamps(self):
    datapoints = [ (600, 0), (600, 0) ]
    compacted = self.ceres_node.compact(datapoints)
    self.assertEqual([[(600, 0)]], compacted)

  def test_compact_groups_contiguous_points(self):
    datapoints = [ (600, 0), (660, 0), (840,0) ]
    compacted = self.ceres_node.compact(datapoints)
    self.assertEqual([[(600, 0), (660,0)], [(840,0)]], compacted)

  def test_write_noops_if_no_datapoints(self):
    with patch('ceres.CeresNode.slices', new=self.ceres_slices):
      self.ceres_node.write([])
      self.assertFalse(self.ceres_slices[0].write.called)

  def test_write_within_first_slice(self):
    datapoints = [(1200, 0.0), (1260, 1.0), (1320, 2.0)]

    with patch('ceres.CeresNode.slices', new=self.ceres_slices):
      self.ceres_node.write(datapoints)
      self.ceres_slices[0].write.assert_called_once_with(datapoints)

  @patch('ceres.CeresSlice.create')
  def test_write_within_first_slice_doesnt_create(self, slice_create_mock):
    datapoints = [(1200, 0.0), (1260, 1.0), (1320, 2.0)]

    with patch('ceres.CeresNode.slices', new=self.ceres_slices):
      self.ceres_node.write(datapoints)
      self.assertFalse(slice_create_mock.called)

  @patch('ceres.CeresSlice.create', new=Mock())
  def test_write_within_first_slice_with_gaps(self):
    datapoints = [ (1200,0.0), (1320,2.0) ]

    with patch('ceres.CeresNode.slices', new=self.ceres_slices):
      self.ceres_node.write(datapoints)

      # sorted most recent first
      calls = [call.write([datapoints[1]]), call.write([datapoints[0]])]
      self.ceres_slices[0].assert_has_calls(calls)

  @patch('ceres.CeresSlice.create', new=Mock())
  def test_write_within_previous_slice(self):
    datapoints = [ (720,0.0), (780,2.0) ]

    with patch('ceres.CeresNode.slices', new=self.ceres_slices):
      self.ceres_node.write(datapoints)

      # 2nd slice has this range
      self.ceres_slices[1].write.assert_called_once_with(datapoints)

  @patch('ceres.CeresSlice.create')
  def test_write_within_previous_slice_doesnt_create(self, slice_create_mock):
    datapoints = [ (720,0.0), (780,2.0) ]

    with patch('ceres.CeresNode.slices', new=self.ceres_slices):
      self.ceres_node.write(datapoints)
      self.assertFalse(slice_create_mock.called)

  @patch('ceres.CeresSlice.create', new=Mock())
  def test_write_within_previous_slice_with_gaps(self):
    datapoints = [ (720,0.0), (840,2.0) ]

    with patch('ceres.CeresNode.slices', new=self.ceres_slices):
      self.ceres_node.write(datapoints)

      calls = [call.write([datapoints[1]]), call.write([datapoints[0]])]
      self.ceres_slices[1].assert_has_calls(calls)

  @patch('ceres.CeresSlice.create', new=Mock())
  def test_write_across_slice_boundaries(self):
    datapoints = [ (1080,0.0), (1140,1.0), (1200, 2.0), (1260, 3.0) ]

    with patch('ceres.CeresNode.slices', new=self.ceres_slices):
      self.ceres_node.write(datapoints)
      self.ceres_slices[0].write.assert_called_once_with(datapoints[2:4])
      self.ceres_slices[1].write.assert_called_once_with(datapoints[0:2])

  @patch('ceres.CeresSlice.create')
  def test_write_before_earliest_slice_creates_new(self, slice_create_mock):
    datapoints = [ (300, 0.0) ]
    with patch('ceres.CeresNode.slices', new=self.ceres_slices):
      self.ceres_node.write(datapoints)
      slice_create_mock.assert_called_once_with(self.ceres_node, 300, 60)

  @patch('ceres.CeresSlice.create')
  def test_write_before_earliest_slice_writes_to_new_one(self, slice_create_mock):
    datapoints = [ (300, 0.0) ]
    with patch('ceres.CeresNode.slices', new=self.ceres_slices):
      self.ceres_node.write(datapoints)
      slice_create_mock.return_value.write.assert_called_once_with(datapoints)

  @patch('ceres.CeresSlice.create')
  def test_create_during_write_clears_slice_cache(self, slice_create_mock):
    self.ceres_node.setSliceCachingBehavior('all')
    self.ceres_node.sliceCache = self.ceres_slices
    datapoints = [ (300, 0.0) ]
    with patch('ceres.CeresNode.slices', new=self.ceres_slices):
      self.ceres_node.write(datapoints)
      self.assertEquals(None, self.ceres_node.sliceCache)


class CeresSliceTest(TestCase):
  def setUp(self):
    with patch('ceres.isdir', new=Mock(return_value=True)):
      with patch('ceres.exists', new=Mock(return_value=True)):
        self.ceres_tree = CeresTree('/graphite/storage/ceres')
        self.ceres_node = CeresNode(self.ceres_tree, 'sample_metric', '/graphite/storage/ceres/sample_metric')

  def test_init_sets_fspath_name(self):
    ceres_slice = CeresSlice(self.ceres_node, 0, 60)
    self.assertTrue(ceres_slice.fsPath.endswith('0@60.slice'))



########NEW FILE########
