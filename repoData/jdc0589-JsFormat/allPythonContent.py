__FILENAME__ = js_formatter
import sublime, sublime_plugin, re, sys, os, json

directory = os.path.dirname(os.path.realpath(__file__))
libs_path = os.path.join(directory, "libs")
src_path = os.path.join(directory, "src")
is_py2k = sys.version_info < (3, 0)

# Python 2.x on Windows can't properly import from non-ASCII paths, so
# this code added the DOC 8.3 version of the lib folder to the path in
# case the user's username includes non-ASCII characters
def add_lib_path(lib_path):
	def _try_get_short_path(path):
		path = os.path.normpath(path)
		if is_py2k and os.name == 'nt' and isinstance(path, unicode):
			try:
				import locale
				path = path.encode(locale.getpreferredencoding())
			except:
				from ctypes import windll, create_unicode_buffer
				buf = create_unicode_buffer(512)
				if windll.kernel32.GetShortPathNameW(path, buf, len(buf)):
					path = buf.value
		return path
	lib_path = _try_get_short_path(lib_path)
	if lib_path not in sys.path:
		sys.path.append(lib_path)

# crazyness to get jsbeautifier.unpackers to actually import
# with sublime's weird hackery of the path and module loading
add_lib_path(libs_path)
add_lib_path(os.path.join(libs_path, "jsbeautifier"))
add_lib_path(os.path.join(libs_path, "jsbeautifier", "jsbeautifier"))
add_lib_path(src_path)

import jsbeautifier, jsbeautifier.unpackers
import jsf, jsf_activation, jsf_rc

s = None

def plugin_loaded():
	global s
	s = sublime.load_settings("JsFormat.sublime-settings")

if is_py2k:
	plugin_loaded()


class PreSaveFormatListner(sublime_plugin.EventListener):
	"""Event listener to run JsFormat during the presave event"""
	def on_pre_save(self, view):
		if(s.get("format_on_save") == True and jsf_activation.is_js_buffer(view)):
			view.run_command("js_format")


class JsFormatCommand(sublime_plugin.TextCommand):
	def run(self, edit):
		settings = self.view.settings()

		# settings
		opts = jsbeautifier.default_options()
		opts.indent_char = " " if settings.get("translate_tabs_to_spaces") else "\t"
		opts.indent_size = int(settings.get("tab_size")) if opts.indent_char == " " else 1
		opts = jsf_rc.augment_options(opts, s)

		if(s.get("jsbeautifyrc_files") == True):
			opts = jsf_rc.augment_options_by_rc_files(opts, self.view)

		selection = self.view.sel()[0]

		# formatting a selection/highlighted area
		if(len(selection) > 0):
			jsf.format_selection(self.view, edit, opts)
		else:
			jsf.format_whole_file(self.view, edit, opts)

	def is_visible(self):
		return jsf_activation.is_js_buffer(self.view)

########NEW FILE########
__FILENAME__ = diff_match_patch
#!/usr/bin/python2.4

from __future__ import division

"""Diff Match and Patch

Copyright 2006 Google Inc.
http://code.google.com/p/google-diff-match-patch/

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

  http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.
"""

"""Functions for diff, match and patch.

Computes the difference between two texts to create a patch.
Applies the patch onto another text, allowing for errors.
"""

__author__ = 'fraser@google.com (Neil Fraser)'

import math
import re
import sys
import time
import urllib

class diff_match_patch:
  """Class containing the diff, match and patch methods.

  Also contains the behaviour settings.
  """

  def __init__(self):
    """Inits a diff_match_patch object with default settings.
    Redefine these in your program to override the defaults.
    """

    # Number of seconds to map a diff before giving up (0 for infinity).
    self.Diff_Timeout = 1.0
    # Cost of an empty edit operation in terms of edit characters.
    self.Diff_EditCost = 4
    # At what point is no match declared (0.0 = perfection, 1.0 = very loose).
    self.Match_Threshold = 0.5
    # How far to search for a match (0 = exact location, 1000+ = broad match).
    # A match this many characters away from the expected location will add
    # 1.0 to the score (0.0 is a perfect match).
    self.Match_Distance = 1000
    # When deleting a large block of text (over ~64 characters), how close do
    # the contents have to be to match the expected contents. (0.0 = perfection,
    # 1.0 = very loose).  Note that Match_Threshold controls how closely the
    # end points of a delete need to match.
    self.Patch_DeleteThreshold = 0.5
    # Chunk size for context length.
    self.Patch_Margin = 4

    # The number of bits in an int.
    # Python has no maximum, thus to disable patch splitting set to 0.
    # However to avoid long patches in certain pathological cases, use 32.
    # Multiple short patches (using native ints) are much faster than long ones.
    self.Match_MaxBits = 32

  #  DIFF FUNCTIONS

  # The data structure representing a diff is an array of tuples:
  # [(DIFF_DELETE, "Hello"), (DIFF_INSERT, "Goodbye"), (DIFF_EQUAL, " world.")]
  # which means: delete "Hello", add "Goodbye" and keep " world."
  DIFF_DELETE = -1
  DIFF_INSERT = 1
  DIFF_EQUAL = 0

  def diff_main(self, text1, text2, checklines=True, deadline=None):
    """Find the differences between two texts.  Simplifies the problem by
      stripping any common prefix or suffix off the texts before diffing.

    Args:
      text1: Old string to be diffed.
      text2: New string to be diffed.
      checklines: Optional speedup flag.  If present and false, then don't run
        a line-level diff first to identify the changed areas.
        Defaults to true, which does a faster, slightly less optimal diff.
      deadline: Optional time when the diff should be complete by.  Used
        internally for recursive calls.  Users should set DiffTimeout instead.

    Returns:
      Array of changes.
    """
    # Set a deadline by which time the diff must be complete.
    if deadline == None:
      # Unlike in most languages, Python counts time in seconds.
      if self.Diff_Timeout <= 0:
        deadline = sys.maxint
      else:
        deadline = time.time() + self.Diff_Timeout

    # Check for null inputs.
    if text1 == None or text2 == None:
      raise ValueError("Null inputs. (diff_main)")

    # Check for equality (speedup).
    if text1 == text2:
      if text1:
        return [(self.DIFF_EQUAL, text1)]
      return []

    # Trim off common prefix (speedup).
    commonlength = self.diff_commonPrefix(text1, text2)
    commonprefix = text1[:commonlength]
    text1 = text1[commonlength:]
    text2 = text2[commonlength:]

    # Trim off common suffix (speedup).
    commonlength = self.diff_commonSuffix(text1, text2)
    if commonlength == 0:
      commonsuffix = ''
    else:
      commonsuffix = text1[-commonlength:]
      text1 = text1[:-commonlength]
      text2 = text2[:-commonlength]

    # Compute the diff on the middle block.
    diffs = self.diff_compute(text1, text2, checklines, deadline)

    # Restore the prefix and suffix.
    if commonprefix:
      diffs[:0] = [(self.DIFF_EQUAL, commonprefix)]
    if commonsuffix:
      diffs.append((self.DIFF_EQUAL, commonsuffix))
    self.diff_cleanupMerge(diffs)
    return diffs

  def diff_compute(self, text1, text2, checklines, deadline):
    """Find the differences between two texts.  Assumes that the texts do not
      have any common prefix or suffix.

    Args:
      text1: Old string to be diffed.
      text2: New string to be diffed.
      checklines: Speedup flag.  If false, then don't run a line-level diff
        first to identify the changed areas.
        If true, then run a faster, slightly less optimal diff.
      deadline: Time when the diff should be complete by.

    Returns:
      Array of changes.
    """
    if not text1:
      # Just add some text (speedup).
      return [(self.DIFF_INSERT, text2)]

    if not text2:
      # Just delete some text (speedup).
      return [(self.DIFF_DELETE, text1)]

    if len(text1) > len(text2):
      (longtext, shorttext) = (text1, text2)
    else:
      (shorttext, longtext) = (text1, text2)
    i = longtext.find(shorttext)
    if i != -1:
      # Shorter text is inside the longer text (speedup).
      diffs = [(self.DIFF_INSERT, longtext[:i]), (self.DIFF_EQUAL, shorttext),
               (self.DIFF_INSERT, longtext[i + len(shorttext):])]
      # Swap insertions for deletions if diff is reversed.
      if len(text1) > len(text2):
        diffs[0] = (self.DIFF_DELETE, diffs[0][1])
        diffs[2] = (self.DIFF_DELETE, diffs[2][1])
      return diffs

    if len(shorttext) == 1:
      # Single character string.
      # After the previous speedup, the character can't be an equality.
      return [(self.DIFF_DELETE, text1), (self.DIFF_INSERT, text2)]

    # Check to see if the problem can be split in two.
    hm = self.diff_halfMatch(text1, text2)
    if hm:
      # A half-match was found, sort out the return data.
      (text1_a, text1_b, text2_a, text2_b, mid_common) = hm
      # Send both pairs off for separate processing.
      diffs_a = self.diff_main(text1_a, text2_a, checklines, deadline)
      diffs_b = self.diff_main(text1_b, text2_b, checklines, deadline)
      # Merge the results.
      return diffs_a + [(self.DIFF_EQUAL, mid_common)] + diffs_b

    if checklines and len(text1) > 100 and len(text2) > 100:
      return self.diff_lineMode(text1, text2, deadline)

    return self.diff_bisect(text1, text2, deadline)

  def diff_lineMode(self, text1, text2, deadline):
    """Do a quick line-level diff on both strings, then rediff the parts for
      greater accuracy.
      This speedup can produce non-minimal diffs.

    Args:
      text1: Old string to be diffed.
      text2: New string to be diffed.
      deadline: Time when the diff should be complete by.

    Returns:
      Array of changes.
    """

    # Scan the text on a line-by-line basis first.
    (text1, text2, linearray) = self.diff_linesToChars(text1, text2)

    diffs = self.diff_main(text1, text2, False, deadline)

    # Convert the diff back to original text.
    self.diff_charsToLines(diffs, linearray)
    # Eliminate freak matches (e.g. blank lines)
    self.diff_cleanupSemantic(diffs)

    # Rediff any replacement blocks, this time character-by-character.
    # Add a dummy entry at the end.
    diffs.append((self.DIFF_EQUAL, ''))
    pointer = 0
    count_delete = 0
    count_insert = 0
    text_delete = ''
    text_insert = ''
    while pointer < len(diffs):
      if diffs[pointer][0] == self.DIFF_INSERT:
        count_insert += 1
        text_insert += diffs[pointer][1]
      elif diffs[pointer][0] == self.DIFF_DELETE:
        count_delete += 1
        text_delete += diffs[pointer][1]
      elif diffs[pointer][0] == self.DIFF_EQUAL:
        # Upon reaching an equality, check for prior redundancies.
        if count_delete >= 1 and count_insert >= 1:
          # Delete the offending records and add the merged ones.
          a = self.diff_main(text_delete, text_insert, False, deadline)
          diffs[pointer - count_delete - count_insert : pointer] = a
          pointer = pointer - count_delete - count_insert + len(a)
        count_insert = 0
        count_delete = 0
        text_delete = ''
        text_insert = ''

      pointer += 1

    diffs.pop()  # Remove the dummy entry at the end.

    return diffs

  def diff_bisect(self, text1, text2, deadline):
    """Find the 'middle snake' of a diff, split the problem in two
      and return the recursively constructed diff.
      See Myers 1986 paper: An O(ND) Difference Algorithm and Its Variations.

    Args:
      text1: Old string to be diffed.
      text2: New string to be diffed.
      deadline: Time at which to bail if not yet complete.

    Returns:
      Array of diff tuples.
    """

    # Cache the text lengths to prevent multiple calls.
    text1_length = len(text1)
    text2_length = len(text2)
    max_d = (text1_length + text2_length + 1) // 2
    v_offset = max_d
    v_length = 2 * max_d
    v1 = [-1] * v_length
    v1[v_offset + 1] = 0
    v2 = v1[:]
    delta = text1_length - text2_length
    # If the total number of characters is odd, then the front path will
    # collide with the reverse path.
    front = (delta % 2 != 0)
    # Offsets for start and end of k loop.
    # Prevents mapping of space beyond the grid.
    k1start = 0
    k1end = 0
    k2start = 0
    k2end = 0
    for d in xrange(max_d):
      # Bail out if deadline is reached.
      if time.time() > deadline:
        break

      # Walk the front path one step.
      for k1 in xrange(-d + k1start, d + 1 - k1end, 2):
        k1_offset = v_offset + k1
        if k1 == -d or (k1 != d and
            v1[k1_offset - 1] < v1[k1_offset + 1]):
          x1 = v1[k1_offset + 1]
        else:
          x1 = v1[k1_offset - 1] + 1
        y1 = x1 - k1
        while (x1 < text1_length and y1 < text2_length and
               text1[x1] == text2[y1]):
          x1 += 1
          y1 += 1
        v1[k1_offset] = x1
        if x1 > text1_length:
          # Ran off the right of the graph.
          k1end += 2
        elif y1 > text2_length:
          # Ran off the bottom of the graph.
          k1start += 2
        elif front:
          k2_offset = v_offset + delta - k1
          if k2_offset >= 0 and k2_offset < v_length and v2[k2_offset] != -1:
            # Mirror x2 onto top-left coordinate system.
            x2 = text1_length - v2[k2_offset]
            if x1 >= x2:
              # Overlap detected.
              return self.diff_bisectSplit(text1, text2, x1, y1, deadline)

      # Walk the reverse path one step.
      for k2 in xrange(-d + k2start, d + 1 - k2end, 2):
        k2_offset = v_offset + k2
        if k2 == -d or (k2 != d and
            v2[k2_offset - 1] < v2[k2_offset + 1]):
          x2 = v2[k2_offset + 1]
        else:
          x2 = v2[k2_offset - 1] + 1
        y2 = x2 - k2
        while (x2 < text1_length and y2 < text2_length and
               text1[-x2 - 1] == text2[-y2 - 1]):
          x2 += 1
          y2 += 1
        v2[k2_offset] = x2
        if x2 > text1_length:
          # Ran off the left of the graph.
          k2end += 2
        elif y2 > text2_length:
          # Ran off the top of the graph.
          k2start += 2
        elif not front:
          k1_offset = v_offset + delta - k2
          if k1_offset >= 0 and k1_offset < v_length and v1[k1_offset] != -1:
            x1 = v1[k1_offset]
            y1 = v_offset + x1 - k1_offset
            # Mirror x2 onto top-left coordinate system.
            x2 = text1_length - x2
            if x1 >= x2:
              # Overlap detected.
              return self.diff_bisectSplit(text1, text2, x1, y1, deadline)

    # Diff took too long and hit the deadline or
    # number of diffs equals number of characters, no commonality at all.
    return [(self.DIFF_DELETE, text1), (self.DIFF_INSERT, text2)]

  def diff_bisectSplit(self, text1, text2, x, y, deadline):
    """Given the location of the 'middle snake', split the diff in two parts
    and recurse.

    Args:
      text1: Old string to be diffed.
      text2: New string to be diffed.
      x: Index of split point in text1.
      y: Index of split point in text2.
      deadline: Time at which to bail if not yet complete.

    Returns:
      Array of diff tuples.
    """
    text1a = text1[:x]
    text2a = text2[:y]
    text1b = text1[x:]
    text2b = text2[y:]

    # Compute both diffs serially.
    diffs = self.diff_main(text1a, text2a, False, deadline)
    diffsb = self.diff_main(text1b, text2b, False, deadline)

    return diffs + diffsb

  def diff_linesToChars(self, text1, text2):
    """Split two texts into an array of strings.  Reduce the texts to a string
    of hashes where each Unicode character represents one line.

    Args:
      text1: First string.
      text2: Second string.

    Returns:
      Three element tuple, containing the encoded text1, the encoded text2 and
      the array of unique strings.  The zeroth element of the array of unique
      strings is intentionally blank.
    """
    lineArray = []  # e.g. lineArray[4] == "Hello\n"
    lineHash = {}   # e.g. lineHash["Hello\n"] == 4

    # "\x00" is a valid character, but various debuggers don't like it.
    # So we'll insert a junk entry to avoid generating a null character.
    lineArray.append('')

    def diff_linesToCharsMunge(text):
      """Split a text into an array of strings.  Reduce the texts to a string
      of hashes where each Unicode character represents one line.
      Modifies linearray and linehash through being a closure.

      Args:
        text: String to encode.

      Returns:
        Encoded string.
      """
      chars = []
      # Walk the text, pulling out a substring for each line.
      # text.split('\n') would would temporarily double our memory footprint.
      # Modifying text would create many large strings to garbage collect.
      lineStart = 0
      lineEnd = -1
      while lineEnd < len(text) - 1:
        lineEnd = text.find('\n', lineStart)
        if lineEnd == -1:
          lineEnd = len(text) - 1
        line = text[lineStart:lineEnd + 1]
        lineStart = lineEnd + 1

        if line in lineHash:
          chars.append(unichr(lineHash[line]))
        else:
          lineArray.append(line)
          lineHash[line] = len(lineArray) - 1
          chars.append(unichr(len(lineArray) - 1))
      return "".join(chars)

    chars1 = diff_linesToCharsMunge(text1)
    chars2 = diff_linesToCharsMunge(text2)
    return (chars1, chars2, lineArray)

  def diff_charsToLines(self, diffs, lineArray):
    """Rehydrate the text in a diff from a string of line hashes to real lines
    of text.

    Args:
      diffs: Array of diff tuples.
      lineArray: Array of unique strings.
    """
    for x in xrange(len(diffs)):
      text = []
      for char in diffs[x][1]:
        text.append(lineArray[ord(char)])
      diffs[x] = (diffs[x][0], "".join(text))

  def diff_commonPrefix(self, text1, text2):
    """Determine the common prefix of two strings.

    Args:
      text1: First string.
      text2: Second string.

    Returns:
      The number of characters common to the start of each string.
    """
    # Quick check for common null cases.
    if not text1 or not text2 or text1[0] != text2[0]:
      return 0
    # Binary search.
    # Performance analysis: http://neil.fraser.name/news/2007/10/09/
    pointermin = 0
    pointermax = min(len(text1), len(text2))
    pointermid = pointermax
    pointerstart = 0
    while pointermin < pointermid:
      if text1[pointerstart:pointermid] == text2[pointerstart:pointermid]:
        pointermin = pointermid
        pointerstart = pointermin
      else:
        pointermax = pointermid
      pointermid = (pointermax - pointermin) // 2 + pointermin
    return pointermid

  def diff_commonSuffix(self, text1, text2):
    """Determine the common suffix of two strings.

    Args:
      text1: First string.
      text2: Second string.

    Returns:
      The number of characters common to the end of each string.
    """
    # Quick check for common null cases.
    if not text1 or not text2 or text1[-1] != text2[-1]:
      return 0
    # Binary search.
    # Performance analysis: http://neil.fraser.name/news/2007/10/09/
    pointermin = 0
    pointermax = min(len(text1), len(text2))
    pointermid = pointermax
    pointerend = 0
    while pointermin < pointermid:
      if (text1[-pointermid:len(text1) - pointerend] ==
          text2[-pointermid:len(text2) - pointerend]):
        pointermin = pointermid
        pointerend = pointermin
      else:
        pointermax = pointermid
      pointermid = (pointermax - pointermin) // 2 + pointermin
    return pointermid

  def diff_commonOverlap(self, text1, text2):
    """Determine if the suffix of one string is the prefix of another.

    Args:
      text1 First string.
      text2 Second string.

    Returns:
      The number of characters common to the end of the first
      string and the start of the second string.
    """
    # Cache the text lengths to prevent multiple calls.
    text1_length = len(text1)
    text2_length = len(text2)
    # Eliminate the null case.
    if text1_length == 0 or text2_length == 0:
      return 0
    # Truncate the longer string.
    if text1_length > text2_length:
      text1 = text1[-text2_length:]
    elif text1_length < text2_length:
      text2 = text2[:text1_length]
    text_length = min(text1_length, text2_length)
    # Quick check for the worst case.
    if text1 == text2:
      return text_length

    # Start by looking for a single character match
    # and increase length until no match is found.
    # Performance analysis: http://neil.fraser.name/news/2010/11/04/
    best = 0
    length = 1
    while True:
      pattern = text1[-length:]
      found = text2.find(pattern)
      if found == -1:
        return best
      length += found
      if found == 0 or text1[-length:] == text2[:length]:
        best = length
        length += 1

  def diff_halfMatch(self, text1, text2):
    """Do the two texts share a substring which is at least half the length of
    the longer text?
    This speedup can produce non-minimal diffs.

    Args:
      text1: First string.
      text2: Second string.

    Returns:
      Five element Array, containing the prefix of text1, the suffix of text1,
      the prefix of text2, the suffix of text2 and the common middle.  Or None
      if there was no match.
    """
    if self.Diff_Timeout <= 0:
      # Don't risk returning a non-optimal diff if we have unlimited time.
      return None
    if len(text1) > len(text2):
      (longtext, shorttext) = (text1, text2)
    else:
      (shorttext, longtext) = (text1, text2)
    if len(longtext) < 4 or len(shorttext) * 2 < len(longtext):
      return None  # Pointless.

    def diff_halfMatchI(longtext, shorttext, i):
      """Does a substring of shorttext exist within longtext such that the
      substring is at least half the length of longtext?
      Closure, but does not reference any external variables.

      Args:
        longtext: Longer string.
        shorttext: Shorter string.
        i: Start index of quarter length substring within longtext.

      Returns:
        Five element Array, containing the prefix of longtext, the suffix of
        longtext, the prefix of shorttext, the suffix of shorttext and the
        common middle.  Or None if there was no match.
      """
      seed = longtext[i:i + len(longtext) // 4]
      best_common = ''
      j = shorttext.find(seed)
      while j != -1:
        prefixLength = self.diff_commonPrefix(longtext[i:], shorttext[j:])
        suffixLength = self.diff_commonSuffix(longtext[:i], shorttext[:j])
        if len(best_common) < suffixLength + prefixLength:
          best_common = (shorttext[j - suffixLength:j] +
              shorttext[j:j + prefixLength])
          best_longtext_a = longtext[:i - suffixLength]
          best_longtext_b = longtext[i + prefixLength:]
          best_shorttext_a = shorttext[:j - suffixLength]
          best_shorttext_b = shorttext[j + prefixLength:]
        j = shorttext.find(seed, j + 1)

      if len(best_common) * 2 >= len(longtext):
        return (best_longtext_a, best_longtext_b,
                best_shorttext_a, best_shorttext_b, best_common)
      else:
        return None

    # First check if the second quarter is the seed for a half-match.
    hm1 = diff_halfMatchI(longtext, shorttext, (len(longtext) + 3) // 4)
    # Check again based on the third quarter.
    hm2 = diff_halfMatchI(longtext, shorttext, (len(longtext) + 1) // 2)
    if not hm1 and not hm2:
      return None
    elif not hm2:
      hm = hm1
    elif not hm1:
      hm = hm2
    else:
      # Both matched.  Select the longest.
      if len(hm1[4]) > len(hm2[4]):
        hm = hm1
      else:
        hm = hm2

    # A half-match was found, sort out the return data.
    if len(text1) > len(text2):
      (text1_a, text1_b, text2_a, text2_b, mid_common) = hm
    else:
      (text2_a, text2_b, text1_a, text1_b, mid_common) = hm
    return (text1_a, text1_b, text2_a, text2_b, mid_common)

  def diff_cleanupSemantic(self, diffs):
    """Reduce the number of edits by eliminating semantically trivial
    equalities.

    Args:
      diffs: Array of diff tuples.
    """
    changes = False
    equalities = []  # Stack of indices where equalities are found.
    lastequality = None  # Always equal to diffs[equalities[-1]][1]
    pointer = 0  # Index of current position.
    # Number of chars that changed prior to the equality.
    length_insertions1, length_deletions1 = 0, 0
    # Number of chars that changed after the equality.
    length_insertions2, length_deletions2 = 0, 0
    while pointer < len(diffs):
      if diffs[pointer][0] == self.DIFF_EQUAL:  # Equality found.
        equalities.append(pointer)
        length_insertions1, length_insertions2 = length_insertions2, 0
        length_deletions1, length_deletions2 = length_deletions2, 0
        lastequality = diffs[pointer][1]
      else:  # An insertion or deletion.
        if diffs[pointer][0] == self.DIFF_INSERT:
          length_insertions2 += len(diffs[pointer][1])
        else:
          length_deletions2 += len(diffs[pointer][1])
        # Eliminate an equality that is smaller or equal to the edits on both
        # sides of it.
        if (lastequality and (len(lastequality) <=
            max(length_insertions1, length_deletions1)) and
            (len(lastequality) <= max(length_insertions2, length_deletions2))):
          # Duplicate record.
          diffs.insert(equalities[-1], (self.DIFF_DELETE, lastequality))
          # Change second copy to insert.
          diffs[equalities[-1] + 1] = (self.DIFF_INSERT,
              diffs[equalities[-1] + 1][1])
          # Throw away the equality we just deleted.
          equalities.pop()
          # Throw away the previous equality (it needs to be reevaluated).
          if len(equalities):
            equalities.pop()
          if len(equalities):
            pointer = equalities[-1]
          else:
            pointer = -1
          # Reset the counters.
          length_insertions1, length_deletions1 = 0, 0
          length_insertions2, length_deletions2 = 0, 0
          lastequality = None
          changes = True
      pointer += 1

    # Normalize the diff.
    if changes:
      self.diff_cleanupMerge(diffs)
    self.diff_cleanupSemanticLossless(diffs)

    # Find any overlaps between deletions and insertions.
    # e.g: <del>abcxxx</del><ins>xxxdef</ins>
    #   -> <del>abc</del>xxx<ins>def</ins>
    # e.g: <del>xxxabc</del><ins>defxxx</ins>
    #   -> <ins>def</ins>xxx<del>abc</del>
    # Only extract an overlap if it is as big as the edit ahead or behind it.
    pointer = 1
    while pointer < len(diffs):
      if (diffs[pointer - 1][0] == self.DIFF_DELETE and
          diffs[pointer][0] == self.DIFF_INSERT):
        deletion = diffs[pointer - 1][1]
        insertion = diffs[pointer][1]
        overlap_length1 = self.diff_commonOverlap(deletion, insertion)
        overlap_length2 = self.diff_commonOverlap(insertion, deletion)
        if overlap_length1 >= overlap_length2:
          if (overlap_length1 >= len(deletion) / 2.0 or
              overlap_length1 >= len(insertion) / 2.0):
            # Overlap found.  Insert an equality and trim the surrounding edits.
            diffs.insert(pointer, (self.DIFF_EQUAL,
                                   insertion[:overlap_length1]))
            diffs[pointer - 1] = (self.DIFF_DELETE,
                                  deletion[:len(deletion) - overlap_length1])
            diffs[pointer + 1] = (self.DIFF_INSERT,
                                  insertion[overlap_length1:])
            pointer += 1
        else:
          if (overlap_length2 >= len(deletion) / 2.0 or
              overlap_length2 >= len(insertion) / 2.0):
            # Reverse overlap found.
            # Insert an equality and swap and trim the surrounding edits.
            diffs.insert(pointer, (self.DIFF_EQUAL, deletion[:overlap_length2]))
            diffs[pointer - 1] = (self.DIFF_INSERT,
                                  insertion[:len(insertion) - overlap_length2])
            diffs[pointer + 1] = (self.DIFF_DELETE, deletion[overlap_length2:])
            pointer += 1
        pointer += 1
      pointer += 1

  def diff_cleanupSemanticLossless(self, diffs):
    """Look for single edits surrounded on both sides by equalities
    which can be shifted sideways to align the edit to a word boundary.
    e.g: The c<ins>at c</ins>ame. -> The <ins>cat </ins>came.

    Args:
      diffs: Array of diff tuples.
    """

    def diff_cleanupSemanticScore(one, two):
      """Given two strings, compute a score representing whether the
      internal boundary falls on logical boundaries.
      Scores range from 6 (best) to 0 (worst).
      Closure, but does not reference any external variables.

      Args:
        one: First string.
        two: Second string.

      Returns:
        The score.
      """
      if not one or not two:
        # Edges are the best.
        return 6

      # Each port of this function behaves slightly differently due to
      # subtle differences in each language's definition of things like
      # 'whitespace'.  Since this function's purpose is largely cosmetic,
      # the choice has been made to use each language's native features
      # rather than force total conformity.
      char1 = one[-1]
      char2 = two[0]
      nonAlphaNumeric1 = not char1.isalnum()
      nonAlphaNumeric2 = not char2.isalnum()
      whitespace1 = nonAlphaNumeric1 and char1.isspace()
      whitespace2 = nonAlphaNumeric2 and char2.isspace()
      lineBreak1 = whitespace1 and (char1 == "\r" or char1 == "\n")
      lineBreak2 = whitespace2 and (char2 == "\r" or char2 == "\n")
      blankLine1 = lineBreak1 and self.BLANKLINEEND.search(one)
      blankLine2 = lineBreak2 and self.BLANKLINESTART.match(two)

      if blankLine1 or blankLine2:
        # Five points for blank lines.
        return 5
      elif lineBreak1 or lineBreak2:
        # Four points for line breaks.
        return 4
      elif nonAlphaNumeric1 and not whitespace1 and whitespace2:
        # Three points for end of sentences.
        return 3
      elif whitespace1 or whitespace2:
        # Two points for whitespace.
        return 2
      elif nonAlphaNumeric1 or nonAlphaNumeric2:
        # One point for non-alphanumeric.
        return 1
      return 0

    pointer = 1
    # Intentionally ignore the first and last element (don't need checking).
    while pointer < len(diffs) - 1:
      if (diffs[pointer - 1][0] == self.DIFF_EQUAL and
          diffs[pointer + 1][0] == self.DIFF_EQUAL):
        # This is a single edit surrounded by equalities.
        equality1 = diffs[pointer - 1][1]
        edit = diffs[pointer][1]
        equality2 = diffs[pointer + 1][1]

        # First, shift the edit as far left as possible.
        commonOffset = self.diff_commonSuffix(equality1, edit)
        if commonOffset:
          commonString = edit[-commonOffset:]
          equality1 = equality1[:-commonOffset]
          edit = commonString + edit[:-commonOffset]
          equality2 = commonString + equality2

        # Second, step character by character right, looking for the best fit.
        bestEquality1 = equality1
        bestEdit = edit
        bestEquality2 = equality2
        bestScore = (diff_cleanupSemanticScore(equality1, edit) +
            diff_cleanupSemanticScore(edit, equality2))
        while edit and equality2 and edit[0] == equality2[0]:
          equality1 += edit[0]
          edit = edit[1:] + equality2[0]
          equality2 = equality2[1:]
          score = (diff_cleanupSemanticScore(equality1, edit) +
              diff_cleanupSemanticScore(edit, equality2))
          # The >= encourages trailing rather than leading whitespace on edits.
          if score >= bestScore:
            bestScore = score
            bestEquality1 = equality1
            bestEdit = edit
            bestEquality2 = equality2

        if diffs[pointer - 1][1] != bestEquality1:
          # We have an improvement, save it back to the diff.
          if bestEquality1:
            diffs[pointer - 1] = (diffs[pointer - 1][0], bestEquality1)
          else:
            del diffs[pointer - 1]
            pointer -= 1
          diffs[pointer] = (diffs[pointer][0], bestEdit)
          if bestEquality2:
            diffs[pointer + 1] = (diffs[pointer + 1][0], bestEquality2)
          else:
            del diffs[pointer + 1]
            pointer -= 1
      pointer += 1

  # Define some regex patterns for matching boundaries.
  BLANKLINEEND = re.compile(r"\n\r?\n$");
  BLANKLINESTART = re.compile(r"^\r?\n\r?\n");

  def diff_cleanupEfficiency(self, diffs):
    """Reduce the number of edits by eliminating operationally trivial
    equalities.

    Args:
      diffs: Array of diff tuples.
    """
    changes = False
    equalities = []  # Stack of indices where equalities are found.
    lastequality = None  # Always equal to diffs[equalities[-1]][1]
    pointer = 0  # Index of current position.
    pre_ins = False  # Is there an insertion operation before the last equality.
    pre_del = False  # Is there a deletion operation before the last equality.
    post_ins = False  # Is there an insertion operation after the last equality.
    post_del = False  # Is there a deletion operation after the last equality.
    while pointer < len(diffs):
      if diffs[pointer][0] == self.DIFF_EQUAL:  # Equality found.
        if (len(diffs[pointer][1]) < self.Diff_EditCost and
            (post_ins or post_del)):
          # Candidate found.
          equalities.append(pointer)
          pre_ins = post_ins
          pre_del = post_del
          lastequality = diffs[pointer][1]
        else:
          # Not a candidate, and can never become one.
          equalities = []
          lastequality = None

        post_ins = post_del = False
      else:  # An insertion or deletion.
        if diffs[pointer][0] == self.DIFF_DELETE:
          post_del = True
        else:
          post_ins = True

        # Five types to be split:
        # <ins>A</ins><del>B</del>XY<ins>C</ins><del>D</del>
        # <ins>A</ins>X<ins>C</ins><del>D</del>
        # <ins>A</ins><del>B</del>X<ins>C</ins>
        # <ins>A</del>X<ins>C</ins><del>D</del>
        # <ins>A</ins><del>B</del>X<del>C</del>

        if lastequality and ((pre_ins and pre_del and post_ins and post_del) or
                             ((len(lastequality) < self.Diff_EditCost / 2) and
                              (pre_ins + pre_del + post_ins + post_del) == 3)):
          # Duplicate record.
          diffs.insert(equalities[-1], (self.DIFF_DELETE, lastequality))
          # Change second copy to insert.
          diffs[equalities[-1] + 1] = (self.DIFF_INSERT,
              diffs[equalities[-1] + 1][1])
          equalities.pop()  # Throw away the equality we just deleted.
          lastequality = None
          if pre_ins and pre_del:
            # No changes made which could affect previous entry, keep going.
            post_ins = post_del = True
            equalities = []
          else:
            if len(equalities):
              equalities.pop()  # Throw away the previous equality.
            if len(equalities):
              pointer = equalities[-1]
            else:
              pointer = -1
            post_ins = post_del = False
          changes = True
      pointer += 1

    if changes:
      self.diff_cleanupMerge(diffs)

  def diff_cleanupMerge(self, diffs):
    """Reorder and merge like edit sections.  Merge equalities.
    Any edit section can move as long as it doesn't cross an equality.

    Args:
      diffs: Array of diff tuples.
    """
    diffs.append((self.DIFF_EQUAL, ''))  # Add a dummy entry at the end.
    pointer = 0
    count_delete = 0
    count_insert = 0
    text_delete = ''
    text_insert = ''
    while pointer < len(diffs):
      if diffs[pointer][0] == self.DIFF_INSERT:
        count_insert += 1
        text_insert += diffs[pointer][1]
        pointer += 1
      elif diffs[pointer][0] == self.DIFF_DELETE:
        count_delete += 1
        text_delete += diffs[pointer][1]
        pointer += 1
      elif diffs[pointer][0] == self.DIFF_EQUAL:
        # Upon reaching an equality, check for prior redundancies.
        if count_delete + count_insert > 1:
          if count_delete != 0 and count_insert != 0:
            # Factor out any common prefixies.
            commonlength = self.diff_commonPrefix(text_insert, text_delete)
            if commonlength != 0:
              x = pointer - count_delete - count_insert - 1
              if x >= 0 and diffs[x][0] == self.DIFF_EQUAL:
                diffs[x] = (diffs[x][0], diffs[x][1] +
                            text_insert[:commonlength])
              else:
                diffs.insert(0, (self.DIFF_EQUAL, text_insert[:commonlength]))
                pointer += 1
              text_insert = text_insert[commonlength:]
              text_delete = text_delete[commonlength:]
            # Factor out any common suffixies.
            commonlength = self.diff_commonSuffix(text_insert, text_delete)
            if commonlength != 0:
              diffs[pointer] = (diffs[pointer][0], text_insert[-commonlength:] +
                  diffs[pointer][1])
              text_insert = text_insert[:-commonlength]
              text_delete = text_delete[:-commonlength]
          # Delete the offending records and add the merged ones.
          if count_delete == 0:
            diffs[pointer - count_insert : pointer] = [
                (self.DIFF_INSERT, text_insert)]
          elif count_insert == 0:
            diffs[pointer - count_delete : pointer] = [
                (self.DIFF_DELETE, text_delete)]
          else:
            diffs[pointer - count_delete - count_insert : pointer] = [
                (self.DIFF_DELETE, text_delete),
                (self.DIFF_INSERT, text_insert)]
          pointer = pointer - count_delete - count_insert + 1
          if count_delete != 0:
            pointer += 1
          if count_insert != 0:
            pointer += 1
        elif pointer != 0 and diffs[pointer - 1][0] == self.DIFF_EQUAL:
          # Merge this equality with the previous one.
          diffs[pointer - 1] = (diffs[pointer - 1][0],
                                diffs[pointer - 1][1] + diffs[pointer][1])
          del diffs[pointer]
        else:
          pointer += 1

        count_insert = 0
        count_delete = 0
        text_delete = ''
        text_insert = ''

    if diffs[-1][1] == '':
      diffs.pop()  # Remove the dummy entry at the end.

    # Second pass: look for single edits surrounded on both sides by equalities
    # which can be shifted sideways to eliminate an equality.
    # e.g: A<ins>BA</ins>C -> <ins>AB</ins>AC
    changes = False
    pointer = 1
    # Intentionally ignore the first and last element (don't need checking).
    while pointer < len(diffs) - 1:
      if (diffs[pointer - 1][0] == self.DIFF_EQUAL and
          diffs[pointer + 1][0] == self.DIFF_EQUAL):
        # This is a single edit surrounded by equalities.
        if diffs[pointer][1].endswith(diffs[pointer - 1][1]):
          # Shift the edit over the previous equality.
          diffs[pointer] = (diffs[pointer][0],
              diffs[pointer - 1][1] +
              diffs[pointer][1][:-len(diffs[pointer - 1][1])])
          diffs[pointer + 1] = (diffs[pointer + 1][0],
                                diffs[pointer - 1][1] + diffs[pointer + 1][1])
          del diffs[pointer - 1]
          changes = True
        elif diffs[pointer][1].startswith(diffs[pointer + 1][1]):
          # Shift the edit over the next equality.
          diffs[pointer - 1] = (diffs[pointer - 1][0],
                                diffs[pointer - 1][1] + diffs[pointer + 1][1])
          diffs[pointer] = (diffs[pointer][0],
              diffs[pointer][1][len(diffs[pointer + 1][1]):] +
              diffs[pointer + 1][1])
          del diffs[pointer + 1]
          changes = True
      pointer += 1

    # If shifts were made, the diff needs reordering and another shift sweep.
    if changes:
      self.diff_cleanupMerge(diffs)

  def diff_xIndex(self, diffs, loc):
    """loc is a location in text1, compute and return the equivalent location
    in text2.  e.g. "The cat" vs "The big cat", 1->1, 5->8

    Args:
      diffs: Array of diff tuples.
      loc: Location within text1.

    Returns:
      Location within text2.
    """
    chars1 = 0
    chars2 = 0
    last_chars1 = 0
    last_chars2 = 0
    for x in xrange(len(diffs)):
      (op, text) = diffs[x]
      if op != self.DIFF_INSERT:  # Equality or deletion.
        chars1 += len(text)
      if op != self.DIFF_DELETE:  # Equality or insertion.
        chars2 += len(text)
      if chars1 > loc:  # Overshot the location.
        break
      last_chars1 = chars1
      last_chars2 = chars2

    if len(diffs) != x and diffs[x][0] == self.DIFF_DELETE:
      # The location was deleted.
      return last_chars2
    # Add the remaining len(character).
    return last_chars2 + (loc - last_chars1)

  def diff_prettyHtml(self, diffs):
    """Convert a diff array into a pretty HTML report.

    Args:
      diffs: Array of diff tuples.

    Returns:
      HTML representation.
    """
    html = []
    for (op, data) in diffs:
      text = (data.replace("&", "&amp;").replace("<", "&lt;")
                 .replace(">", "&gt;").replace("\n", "&para;<br>"))
      if op == self.DIFF_INSERT:
        html.append("<ins style=\"background:#e6ffe6;\">%s</ins>" % text)
      elif op == self.DIFF_DELETE:
        html.append("<del style=\"background:#ffe6e6;\">%s</del>" % text)
      elif op == self.DIFF_EQUAL:
        html.append("<span>%s</span>" % text)
    return "".join(html)

  def diff_text1(self, diffs):
    """Compute and return the source text (all equalities and deletions).

    Args:
      diffs: Array of diff tuples.

    Returns:
      Source text.
    """
    text = []
    for (op, data) in diffs:
      if op != self.DIFF_INSERT:
        text.append(data)
    return "".join(text)

  def diff_text2(self, diffs):
    """Compute and return the destination text (all equalities and insertions).

    Args:
      diffs: Array of diff tuples.

    Returns:
      Destination text.
    """
    text = []
    for (op, data) in diffs:
      if op != self.DIFF_DELETE:
        text.append(data)
    return "".join(text)

  def diff_levenshtein(self, diffs):
    """Compute the Levenshtein distance; the number of inserted, deleted or
    substituted characters.

    Args:
      diffs: Array of diff tuples.

    Returns:
      Number of changes.
    """
    levenshtein = 0
    insertions = 0
    deletions = 0
    for (op, data) in diffs:
      if op == self.DIFF_INSERT:
        insertions += len(data)
      elif op == self.DIFF_DELETE:
        deletions += len(data)
      elif op == self.DIFF_EQUAL:
        # A deletion and an insertion is one substitution.
        levenshtein += max(insertions, deletions)
        insertions = 0
        deletions = 0
    levenshtein += max(insertions, deletions)
    return levenshtein

  def diff_toDelta(self, diffs):
    """Crush the diff into an encoded string which describes the operations
    required to transform text1 into text2.
    E.g. =3\t-2\t+ing  -> Keep 3 chars, delete 2 chars, insert 'ing'.
    Operations are tab-separated.  Inserted text is escaped using %xx notation.

    Args:
      diffs: Array of diff tuples.

    Returns:
      Delta text.
    """
    text = []
    for (op, data) in diffs:
      if op == self.DIFF_INSERT:
        # High ascii will raise UnicodeDecodeError.  Use Unicode instead.
        data = data.encode("utf-8")
        text.append("+" + urllib.quote(data, "!~*'();/?:@&=+$,# "))
      elif op == self.DIFF_DELETE:
        text.append("-%d" % len(data))
      elif op == self.DIFF_EQUAL:
        text.append("=%d" % len(data))
    return "\t".join(text)

  def diff_fromDelta(self, text1, delta):
    """Given the original text1, and an encoded string which describes the
    operations required to transform text1 into text2, compute the full diff.

    Args:
      text1: Source string for the diff.
      delta: Delta text.

    Returns:
      Array of diff tuples.

    Raises:
      ValueError: If invalid input.
    """
    if type(delta) == unicode:
      # Deltas should be composed of a subset of ascii chars, Unicode not
      # required.  If this encode raises UnicodeEncodeError, delta is invalid.
      delta = delta.encode("ascii")
    diffs = []
    pointer = 0  # Cursor in text1
    tokens = delta.split("\t")
    for token in tokens:
      if token == "":
        # Blank tokens are ok (from a trailing \t).
        continue
      # Each token begins with a one character parameter which specifies the
      # operation of this token (delete, insert, equality).
      param = token[1:]
      if token[0] == "+":
        param = urllib.unquote(param).decode("utf-8")
        diffs.append((self.DIFF_INSERT, param))
      elif token[0] == "-" or token[0] == "=":
        try:
          n = int(param)
        except ValueError:
          raise ValueError("Invalid number in diff_fromDelta: " + param)
        if n < 0:
          raise ValueError("Negative number in diff_fromDelta: " + param)
        text = text1[pointer : pointer + n]
        pointer += n
        if token[0] == "=":
          diffs.append((self.DIFF_EQUAL, text))
        else:
          diffs.append((self.DIFF_DELETE, text))
      else:
        # Anything else is an error.
        raise ValueError("Invalid diff operation in diff_fromDelta: " +
            token[0])
    if pointer != len(text1):
      raise ValueError(
          "Delta length (%d) does not equal source text length (%d)." %
         (pointer, len(text1)))
    return diffs

  #  MATCH FUNCTIONS

  def match_main(self, text, pattern, loc):
    """Locate the best instance of 'pattern' in 'text' near 'loc'.

    Args:
      text: The text to search.
      pattern: The pattern to search for.
      loc: The location to search around.

    Returns:
      Best match index or -1.
    """
    # Check for null inputs.
    if text == None or pattern == None:
      raise ValueError("Null inputs. (match_main)")

    loc = max(0, min(loc, len(text)))
    if text == pattern:
      # Shortcut (potentially not guaranteed by the algorithm)
      return 0
    elif not text:
      # Nothing to match.
      return -1
    elif text[loc:loc + len(pattern)] == pattern:
      # Perfect match at the perfect spot!  (Includes case of null pattern)
      return loc
    else:
      # Do a fuzzy compare.
      match = self.match_bitap(text, pattern, loc)
      return match

  def match_bitap(self, text, pattern, loc):
    """Locate the best instance of 'pattern' in 'text' near 'loc' using the
    Bitap algorithm.

    Args:
      text: The text to search.
      pattern: The pattern to search for.
      loc: The location to search around.

    Returns:
      Best match index or -1.
    """
    # Python doesn't have a maxint limit, so ignore this check.
    #if self.Match_MaxBits != 0 and len(pattern) > self.Match_MaxBits:
    #  raise ValueError("Pattern too long for this application.")

    # Initialise the alphabet.
    s = self.match_alphabet(pattern)

    def match_bitapScore(e, x):
      """Compute and return the score for a match with e errors and x location.
      Accesses loc and pattern through being a closure.

      Args:
        e: Number of errors in match.
        x: Location of match.

      Returns:
        Overall score for match (0.0 = good, 1.0 = bad).
      """
      accuracy = float(e) / len(pattern)
      proximity = abs(loc - x)
      if not self.Match_Distance:
        # Dodge divide by zero error.
        return proximity and 1.0 or accuracy
      return accuracy + (proximity / float(self.Match_Distance))

    # Highest score beyond which we give up.
    score_threshold = self.Match_Threshold
    # Is there a nearby exact match? (speedup)
    best_loc = text.find(pattern, loc)
    if best_loc != -1:
      score_threshold = min(match_bitapScore(0, best_loc), score_threshold)
      # What about in the other direction? (speedup)
      best_loc = text.rfind(pattern, loc + len(pattern))
      if best_loc != -1:
        score_threshold = min(match_bitapScore(0, best_loc), score_threshold)

    # Initialise the bit arrays.
    matchmask = 1 << (len(pattern) - 1)
    best_loc = -1

    bin_max = len(pattern) + len(text)
    # Empty initialization added to appease pychecker.
    last_rd = None
    for d in xrange(len(pattern)):
      # Scan for the best match each iteration allows for one more error.
      # Run a binary search to determine how far from 'loc' we can stray at
      # this error level.
      bin_min = 0
      bin_mid = bin_max
      while bin_min < bin_mid:
        if match_bitapScore(d, loc + bin_mid) <= score_threshold:
          bin_min = bin_mid
        else:
          bin_max = bin_mid
        bin_mid = (bin_max - bin_min) // 2 + bin_min

      # Use the result from this iteration as the maximum for the next.
      bin_max = bin_mid
      start = max(1, loc - bin_mid + 1)
      finish = min(loc + bin_mid, len(text)) + len(pattern)

      rd = [0] * (finish + 2)
      rd[finish + 1] = (1 << d) - 1
      for j in xrange(finish, start - 1, -1):
        if len(text) <= j - 1:
          # Out of range.
          charMatch = 0
        else:
          charMatch = s.get(text[j - 1], 0)
        if d == 0:  # First pass: exact match.
          rd[j] = ((rd[j + 1] << 1) | 1) & charMatch
        else:  # Subsequent passes: fuzzy match.
          rd[j] = (((rd[j + 1] << 1) | 1) & charMatch) | (
              ((last_rd[j + 1] | last_rd[j]) << 1) | 1) | last_rd[j + 1]
        if rd[j] & matchmask:
          score = match_bitapScore(d, j - 1)
          # This match will almost certainly be better than any existing match.
          # But check anyway.
          if score <= score_threshold:
            # Told you so.
            score_threshold = score
            best_loc = j - 1
            if best_loc > loc:
              # When passing loc, don't exceed our current distance from loc.
              start = max(1, 2 * loc - best_loc)
            else:
              # Already passed loc, downhill from here on in.
              break
      # No hope for a (better) match at greater error levels.
      if match_bitapScore(d + 1, loc) > score_threshold:
        break
      last_rd = rd
    return best_loc

  def match_alphabet(self, pattern):
    """Initialise the alphabet for the Bitap algorithm.

    Args:
      pattern: The text to encode.

    Returns:
      Hash of character locations.
    """
    s = {}
    for char in pattern:
      s[char] = 0
    for i in xrange(len(pattern)):
      s[pattern[i]] |= 1 << (len(pattern) - i - 1)
    return s

  #  PATCH FUNCTIONS

  def patch_addContext(self, patch, text):
    """Increase the context until it is unique,
    but don't let the pattern expand beyond Match_MaxBits.

    Args:
      patch: The patch to grow.
      text: Source text.
    """
    if len(text) == 0:
      return
    pattern = text[patch.start2 : patch.start2 + patch.length1]
    padding = 0

    # Look for the first and last matches of pattern in text.  If two different
    # matches are found, increase the pattern length.
    while (text.find(pattern) != text.rfind(pattern) and (self.Match_MaxBits ==
        0 or len(pattern) < self.Match_MaxBits - self.Patch_Margin -
        self.Patch_Margin)):
      padding += self.Patch_Margin
      pattern = text[max(0, patch.start2 - padding) :
                     patch.start2 + patch.length1 + padding]
    # Add one chunk for good luck.
    padding += self.Patch_Margin

    # Add the prefix.
    prefix = text[max(0, patch.start2 - padding) : patch.start2]
    if prefix:
      patch.diffs[:0] = [(self.DIFF_EQUAL, prefix)]
    # Add the suffix.
    suffix = text[patch.start2 + patch.length1 :
                  patch.start2 + patch.length1 + padding]
    if suffix:
      patch.diffs.append((self.DIFF_EQUAL, suffix))

    # Roll back the start points.
    patch.start1 -= len(prefix)
    patch.start2 -= len(prefix)
    # Extend lengths.
    patch.length1 += len(prefix) + len(suffix)
    patch.length2 += len(prefix) + len(suffix)

  def patch_make(self, a, b=None, c=None):
    """Compute a list of patches to turn text1 into text2.
    Use diffs if provided, otherwise compute it ourselves.
    There are four ways to call this function, depending on what data is
    available to the caller:
    Method 1:
    a = text1, b = text2
    Method 2:
    a = diffs
    Method 3 (optimal):
    a = text1, b = diffs
    Method 4 (deprecated, use method 3):
    a = text1, b = text2, c = diffs

    Args:
      a: text1 (methods 1,3,4) or Array of diff tuples for text1 to
          text2 (method 2).
      b: text2 (methods 1,4) or Array of diff tuples for text1 to
          text2 (method 3) or undefined (method 2).
      c: Array of diff tuples for text1 to text2 (method 4) or
          undefined (methods 1,2,3).

    Returns:
      Array of Patch objects.
    """
    text1 = None
    diffs = None
    # Note that texts may arrive as 'str' or 'unicode'.
    if isinstance(a, basestring) and isinstance(b, basestring) and c is None:
      # Method 1: text1, text2
      # Compute diffs from text1 and text2.
      text1 = a
      diffs = self.diff_main(text1, b, True)
      if len(diffs) > 2:
        self.diff_cleanupSemantic(diffs)
        self.diff_cleanupEfficiency(diffs)
    elif isinstance(a, list) and b is None and c is None:
      # Method 2: diffs
      # Compute text1 from diffs.
      diffs = a
      text1 = self.diff_text1(diffs)
    elif isinstance(a, basestring) and isinstance(b, list) and c is None:
      # Method 3: text1, diffs
      text1 = a
      diffs = b
    elif (isinstance(a, basestring) and isinstance(b, basestring) and
          isinstance(c, list)):
      # Method 4: text1, text2, diffs
      # text2 is not used.
      text1 = a
      diffs = c
    else:
      raise ValueError("Unknown call format to patch_make.")

    if not diffs:
      return []  # Get rid of the None case.
    patches = []
    patch = patch_obj()
    char_count1 = 0  # Number of characters into the text1 string.
    char_count2 = 0  # Number of characters into the text2 string.
    prepatch_text = text1  # Recreate the patches to determine context info.
    postpatch_text = text1
    for x in xrange(len(diffs)):
      (diff_type, diff_text) = diffs[x]
      if len(patch.diffs) == 0 and diff_type != self.DIFF_EQUAL:
        # A new patch starts here.
        patch.start1 = char_count1
        patch.start2 = char_count2
      if diff_type == self.DIFF_INSERT:
        # Insertion
        patch.diffs.append(diffs[x])
        patch.length2 += len(diff_text)
        postpatch_text = (postpatch_text[:char_count2] + diff_text +
                          postpatch_text[char_count2:])
      elif diff_type == self.DIFF_DELETE:
        # Deletion.
        patch.length1 += len(diff_text)
        patch.diffs.append(diffs[x])
        postpatch_text = (postpatch_text[:char_count2] +
                          postpatch_text[char_count2 + len(diff_text):])
      elif (diff_type == self.DIFF_EQUAL and
            len(diff_text) <= 2 * self.Patch_Margin and
            len(patch.diffs) != 0 and len(diffs) != x + 1):
        # Small equality inside a patch.
        patch.diffs.append(diffs[x])
        patch.length1 += len(diff_text)
        patch.length2 += len(diff_text)

      if (diff_type == self.DIFF_EQUAL and
          len(diff_text) >= 2 * self.Patch_Margin):
        # Time for a new patch.
        if len(patch.diffs) != 0:
          self.patch_addContext(patch, prepatch_text)
          patches.append(patch)
          patch = patch_obj()
          # Unlike Unidiff, our patch lists have a rolling context.
          # http://code.google.com/p/google-diff-match-patch/wiki/Unidiff
          # Update prepatch text & pos to reflect the application of the
          # just completed patch.
          prepatch_text = postpatch_text
          char_count1 = char_count2

      # Update the current character count.
      if diff_type != self.DIFF_INSERT:
        char_count1 += len(diff_text)
      if diff_type != self.DIFF_DELETE:
        char_count2 += len(diff_text)

    # Pick up the leftover patch if not empty.
    if len(patch.diffs) != 0:
      self.patch_addContext(patch, prepatch_text)
      patches.append(patch)
    return patches

  def patch_deepCopy(self, patches):
    """Given an array of patches, return another array that is identical.

    Args:
      patches: Array of Patch objects.

    Returns:
      Array of Patch objects.
    """
    patchesCopy = []
    for patch in patches:
      patchCopy = patch_obj()
      # No need to deep copy the tuples since they are immutable.
      patchCopy.diffs = patch.diffs[:]
      patchCopy.start1 = patch.start1
      patchCopy.start2 = patch.start2
      patchCopy.length1 = patch.length1
      patchCopy.length2 = patch.length2
      patchesCopy.append(patchCopy)
    return patchesCopy

  def patch_apply(self, patches, text):
    """Merge a set of patches onto the text.  Return a patched text, as well
    as a list of true/false values indicating which patches were applied.

    Args:
      patches: Array of Patch objects.
      text: Old text.

    Returns:
      Two element Array, containing the new text and an array of boolean values.
    """
    if not patches:
      return (text, [])

    # Deep copy the patches so that no changes are made to originals.
    patches = self.patch_deepCopy(patches)

    nullPadding = self.patch_addPadding(patches)
    text = nullPadding + text + nullPadding
    self.patch_splitMax(patches)

    # delta keeps track of the offset between the expected and actual location
    # of the previous patch.  If there are patches expected at positions 10 and
    # 20, but the first patch was found at 12, delta is 2 and the second patch
    # has an effective expected position of 22.
    delta = 0
    results = []
    for patch in patches:
      expected_loc = patch.start2 + delta
      text1 = self.diff_text1(patch.diffs)
      end_loc = -1
      if len(text1) > self.Match_MaxBits:
        # patch_splitMax will only provide an oversized pattern in the case of
        # a monster delete.
        start_loc = self.match_main(text, text1[:self.Match_MaxBits],
                                    expected_loc)
        if start_loc != -1:
          end_loc = self.match_main(text, text1[-self.Match_MaxBits:],
              expected_loc + len(text1) - self.Match_MaxBits)
          if end_loc == -1 or start_loc >= end_loc:
            # Can't find valid trailing context.  Drop this patch.
            start_loc = -1
      else:
        start_loc = self.match_main(text, text1, expected_loc)
      if start_loc == -1:
        # No match found.  :(
        results.append(False)
        # Subtract the delta for this failed patch from subsequent patches.
        delta -= patch.length2 - patch.length1
      else:
        # Found a match.  :)
        results.append(True)
        delta = start_loc - expected_loc
        if end_loc == -1:
          text2 = text[start_loc : start_loc + len(text1)]
        else:
          text2 = text[start_loc : end_loc + self.Match_MaxBits]
        if text1 == text2:
          # Perfect match, just shove the replacement text in.
          text = (text[:start_loc] + self.diff_text2(patch.diffs) +
                      text[start_loc + len(text1):])
        else:
          # Imperfect match.
          # Run a diff to get a framework of equivalent indices.
          diffs = self.diff_main(text1, text2, False)
          if (len(text1) > self.Match_MaxBits and
              self.diff_levenshtein(diffs) / float(len(text1)) >
              self.Patch_DeleteThreshold):
            # The end points match, but the content is unacceptably bad.
            results[-1] = False
          else:
            self.diff_cleanupSemanticLossless(diffs)
            index1 = 0
            for (op, data) in patch.diffs:
              if op != self.DIFF_EQUAL:
                index2 = self.diff_xIndex(diffs, index1)
              if op == self.DIFF_INSERT:  # Insertion
                text = text[:start_loc + index2] + data + text[start_loc +
                                                               index2:]
              elif op == self.DIFF_DELETE:  # Deletion
                text = text[:start_loc + index2] + text[start_loc +
                    self.diff_xIndex(diffs, index1 + len(data)):]
              if op != self.DIFF_DELETE:
                index1 += len(data)
    # Strip the padding off.
    text = text[len(nullPadding):-len(nullPadding)]
    return (text, results)

  def patch_addPadding(self, patches):
    """Add some padding on text start and end so that edges can match
    something.  Intended to be called only from within patch_apply.

    Args:
      patches: Array of Patch objects.

    Returns:
      The padding string added to each side.
    """
    paddingLength = self.Patch_Margin
    nullPadding = ""
    for x in xrange(1, paddingLength + 1):
      nullPadding += chr(x)

    # Bump all the patches forward.
    for patch in patches:
      patch.start1 += paddingLength
      patch.start2 += paddingLength

    # Add some padding on start of first diff.
    patch = patches[0]
    diffs = patch.diffs
    if not diffs or diffs[0][0] != self.DIFF_EQUAL:
      # Add nullPadding equality.
      diffs.insert(0, (self.DIFF_EQUAL, nullPadding))
      patch.start1 -= paddingLength  # Should be 0.
      patch.start2 -= paddingLength  # Should be 0.
      patch.length1 += paddingLength
      patch.length2 += paddingLength
    elif paddingLength > len(diffs[0][1]):
      # Grow first equality.
      extraLength = paddingLength - len(diffs[0][1])
      newText = nullPadding[len(diffs[0][1]):] + diffs[0][1]
      diffs[0] = (diffs[0][0], newText)
      patch.start1 -= extraLength
      patch.start2 -= extraLength
      patch.length1 += extraLength
      patch.length2 += extraLength

    # Add some padding on end of last diff.
    patch = patches[-1]
    diffs = patch.diffs
    if not diffs or diffs[-1][0] != self.DIFF_EQUAL:
      # Add nullPadding equality.
      diffs.append((self.DIFF_EQUAL, nullPadding))
      patch.length1 += paddingLength
      patch.length2 += paddingLength
    elif paddingLength > len(diffs[-1][1]):
      # Grow last equality.
      extraLength = paddingLength - len(diffs[-1][1])
      newText = diffs[-1][1] + nullPadding[:extraLength]
      diffs[-1] = (diffs[-1][0], newText)
      patch.length1 += extraLength
      patch.length2 += extraLength

    return nullPadding

  def patch_splitMax(self, patches):
    """Look through the patches and break up any which are longer than the
    maximum limit of the match algorithm.
    Intended to be called only from within patch_apply.

    Args:
      patches: Array of Patch objects.
    """
    patch_size = self.Match_MaxBits
    if patch_size == 0:
      # Python has the option of not splitting strings due to its ability
      # to handle integers of arbitrary precision.
      return
    for x in xrange(len(patches)):
      if patches[x].length1 <= patch_size:
        continue
      bigpatch = patches[x]
      # Remove the big old patch.
      del patches[x]
      x -= 1
      start1 = bigpatch.start1
      start2 = bigpatch.start2
      precontext = ''
      while len(bigpatch.diffs) != 0:
        # Create one of several smaller patches.
        patch = patch_obj()
        empty = True
        patch.start1 = start1 - len(precontext)
        patch.start2 = start2 - len(precontext)
        if precontext:
          patch.length1 = patch.length2 = len(precontext)
          patch.diffs.append((self.DIFF_EQUAL, precontext))

        while (len(bigpatch.diffs) != 0 and
               patch.length1 < patch_size - self.Patch_Margin):
          (diff_type, diff_text) = bigpatch.diffs[0]
          if diff_type == self.DIFF_INSERT:
            # Insertions are harmless.
            patch.length2 += len(diff_text)
            start2 += len(diff_text)
            patch.diffs.append(bigpatch.diffs.pop(0))
            empty = False
          elif (diff_type == self.DIFF_DELETE and len(patch.diffs) == 1 and
              patch.diffs[0][0] == self.DIFF_EQUAL and
              len(diff_text) > 2 * patch_size):
            # This is a large deletion.  Let it pass in one chunk.
            patch.length1 += len(diff_text)
            start1 += len(diff_text)
            empty = False
            patch.diffs.append((diff_type, diff_text))
            del bigpatch.diffs[0]
          else:
            # Deletion or equality.  Only take as much as we can stomach.
            diff_text = diff_text[:patch_size - patch.length1 -
                                  self.Patch_Margin]
            patch.length1 += len(diff_text)
            start1 += len(diff_text)
            if diff_type == self.DIFF_EQUAL:
              patch.length2 += len(diff_text)
              start2 += len(diff_text)
            else:
              empty = False

            patch.diffs.append((diff_type, diff_text))
            if diff_text == bigpatch.diffs[0][1]:
              del bigpatch.diffs[0]
            else:
              bigpatch.diffs[0] = (bigpatch.diffs[0][0],
                                   bigpatch.diffs[0][1][len(diff_text):])

        # Compute the head context for the next patch.
        precontext = self.diff_text2(patch.diffs)
        precontext = precontext[-self.Patch_Margin:]
        # Append the end context for this patch.
        postcontext = self.diff_text1(bigpatch.diffs)[:self.Patch_Margin]
        if postcontext:
          patch.length1 += len(postcontext)
          patch.length2 += len(postcontext)
          if len(patch.diffs) != 0 and patch.diffs[-1][0] == self.DIFF_EQUAL:
            patch.diffs[-1] = (self.DIFF_EQUAL, patch.diffs[-1][1] +
                               postcontext)
          else:
            patch.diffs.append((self.DIFF_EQUAL, postcontext))

        if not empty:
          x += 1
          patches.insert(x, patch)

  def patch_toText(self, patches):
    """Take a list of patches and return a textual representation.

    Args:
      patches: Array of Patch objects.

    Returns:
      Text representation of patches.
    """
    text = []
    for patch in patches:
      text.append(str(patch))
    return "".join(text)

  def patch_fromText(self, textline):
    """Parse a textual representation of patches and return a list of patch
    objects.

    Args:
      textline: Text representation of patches.

    Returns:
      Array of Patch objects.

    Raises:
      ValueError: If invalid input.
    """
    if type(textline) == unicode:
      # Patches should be composed of a subset of ascii chars, Unicode not
      # required.  If this encode raises UnicodeEncodeError, patch is invalid.
      textline = textline.encode("ascii")
    patches = []
    if not textline:
      return patches
    text = textline.split('\n')
    while len(text) != 0:
      m = re.match("^@@ -(\d+),?(\d*) \+(\d+),?(\d*) @@$", text[0])
      if not m:
        raise ValueError("Invalid patch string: " + text[0])
      patch = patch_obj()
      patches.append(patch)
      patch.start1 = int(m.group(1))
      if m.group(2) == '':
        patch.start1 -= 1
        patch.length1 = 1
      elif m.group(2) == '0':
        patch.length1 = 0
      else:
        patch.start1 -= 1
        patch.length1 = int(m.group(2))

      patch.start2 = int(m.group(3))
      if m.group(4) == '':
        patch.start2 -= 1
        patch.length2 = 1
      elif m.group(4) == '0':
        patch.length2 = 0
      else:
        patch.start2 -= 1
        patch.length2 = int(m.group(4))

      del text[0]

      while len(text) != 0:
        if text[0]:
          sign = text[0][0]
        else:
          sign = ''
        line = urllib.unquote(text[0][1:])
        line = line.decode("utf-8")
        if sign == '+':
          # Insertion.
          patch.diffs.append((self.DIFF_INSERT, line))
        elif sign == '-':
          # Deletion.
          patch.diffs.append((self.DIFF_DELETE, line))
        elif sign == ' ':
          # Minor equality.
          patch.diffs.append((self.DIFF_EQUAL, line))
        elif sign == '@':
          # Start of next patch.
          break
        elif sign == '':
          # Blank line?  Whatever.
          pass
        else:
          # WTF?
          raise ValueError("Invalid patch mode: '%s'\n%s" % (sign, line))
        del text[0]
    return patches


class patch_obj:
  """Class representing one patch operation.
  """

  def __init__(self):
    """Initializes with an empty list of diffs.
    """
    self.diffs = []
    self.start1 = None
    self.start2 = None
    self.length1 = 0
    self.length2 = 0

  def __str__(self):
    """Emmulate GNU diff's format.
    Header: @@ -382,8 +481,9 @@
    Indicies are printed as 1-based, not 0-based.

    Returns:
      The GNU diff string.
    """
    if self.length1 == 0:
      coords1 = str(self.start1) + ",0"
    elif self.length1 == 1:
      coords1 = str(self.start1 + 1)
    else:
      coords1 = str(self.start1 + 1) + "," + str(self.length1)
    if self.length2 == 0:
      coords2 = str(self.start2) + ",0"
    elif self.length2 == 1:
      coords2 = str(self.start2 + 1)
    else:
      coords2 = str(self.start2 + 1) + "," + str(self.length2)
    text = ["@@ -", coords1, " +", coords2, " @@\n"]
    # Escape the body of the patch with %xx notation.
    for (op, data) in self.diffs:
      if op == diff_match_patch.DIFF_INSERT:
        text.append("+")
      elif op == diff_match_patch.DIFF_DELETE:
        text.append("-")
      elif op == diff_match_patch.DIFF_EQUAL:
        text.append(" ")
      # High ascii will raise UnicodeDecodeError.  Use Unicode instead.
      data = data.encode("utf-8")
      text.append(urllib.quote(data, "!~*'();/?:@&=+$,# ") + "\n")
    return "".join(text)

########NEW FILE########
__FILENAME__ = diff_match_patch
#!/usr/bin/python3

"""Diff Match and Patch

Copyright 2006 Google Inc.
http://code.google.com/p/google-diff-match-patch/

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

  http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.
"""

"""Functions for diff, match and patch.

Computes the difference between two texts to create a patch.
Applies the patch onto another text, allowing for errors.
"""

__author__ = 'fraser@google.com (Neil Fraser)'

import math
import re
import sys
import time
import urllib.parse

class diff_match_patch:
  """Class containing the diff, match and patch methods.

  Also contains the behaviour settings.
  """

  def __init__(self):
    """Inits a diff_match_patch object with default settings.
    Redefine these in your program to override the defaults.
    """

    # Number of seconds to map a diff before giving up (0 for infinity).
    self.Diff_Timeout = 1.0
    # Cost of an empty edit operation in terms of edit characters.
    self.Diff_EditCost = 4
    # At what point is no match declared (0.0 = perfection, 1.0 = very loose).
    self.Match_Threshold = 0.5
    # How far to search for a match (0 = exact location, 1000+ = broad match).
    # A match this many characters away from the expected location will add
    # 1.0 to the score (0.0 is a perfect match).
    self.Match_Distance = 1000
    # When deleting a large block of text (over ~64 characters), how close do
    # the contents have to be to match the expected contents. (0.0 = perfection,
    # 1.0 = very loose).  Note that Match_Threshold controls how closely the
    # end points of a delete need to match.
    self.Patch_DeleteThreshold = 0.5
    # Chunk size for context length.
    self.Patch_Margin = 4

    # The number of bits in an int.
    # Python has no maximum, thus to disable patch splitting set to 0.
    # However to avoid long patches in certain pathological cases, use 32.
    # Multiple short patches (using native ints) are much faster than long ones.
    self.Match_MaxBits = 32

  #  DIFF FUNCTIONS

  # The data structure representing a diff is an array of tuples:
  # [(DIFF_DELETE, "Hello"), (DIFF_INSERT, "Goodbye"), (DIFF_EQUAL, " world.")]
  # which means: delete "Hello", add "Goodbye" and keep " world."
  DIFF_DELETE = -1
  DIFF_INSERT = 1
  DIFF_EQUAL = 0

  def diff_main(self, text1, text2, checklines=True, deadline=None):
    """Find the differences between two texts.  Simplifies the problem by
      stripping any common prefix or suffix off the texts before diffing.

    Args:
      text1: Old string to be diffed.
      text2: New string to be diffed.
      checklines: Optional speedup flag.  If present and false, then don't run
        a line-level diff first to identify the changed areas.
        Defaults to true, which does a faster, slightly less optimal diff.
      deadline: Optional time when the diff should be complete by.  Used
        internally for recursive calls.  Users should set DiffTimeout instead.

    Returns:
      Array of changes.
    """
    # Set a deadline by which time the diff must be complete.
    if deadline == None:
      # Unlike in most languages, Python counts time in seconds.
      if self.Diff_Timeout <= 0:
        deadline = sys.maxsize
      else:
        deadline = time.time() + self.Diff_Timeout

    # Check for null inputs.
    if text1 == None or text2 == None:
      raise ValueError("Null inputs. (diff_main)")

    # Check for equality (speedup).
    if text1 == text2:
      if text1:
        return [(self.DIFF_EQUAL, text1)]
      return []

    # Trim off common prefix (speedup).
    commonlength = self.diff_commonPrefix(text1, text2)
    commonprefix = text1[:commonlength]
    text1 = text1[commonlength:]
    text2 = text2[commonlength:]

    # Trim off common suffix (speedup).
    commonlength = self.diff_commonSuffix(text1, text2)
    if commonlength == 0:
      commonsuffix = ''
    else:
      commonsuffix = text1[-commonlength:]
      text1 = text1[:-commonlength]
      text2 = text2[:-commonlength]

    # Compute the diff on the middle block.
    diffs = self.diff_compute(text1, text2, checklines, deadline)

    # Restore the prefix and suffix.
    if commonprefix:
      diffs[:0] = [(self.DIFF_EQUAL, commonprefix)]
    if commonsuffix:
      diffs.append((self.DIFF_EQUAL, commonsuffix))
    self.diff_cleanupMerge(diffs)
    return diffs

  def diff_compute(self, text1, text2, checklines, deadline):
    """Find the differences between two texts.  Assumes that the texts do not
      have any common prefix or suffix.

    Args:
      text1: Old string to be diffed.
      text2: New string to be diffed.
      checklines: Speedup flag.  If false, then don't run a line-level diff
        first to identify the changed areas.
        If true, then run a faster, slightly less optimal diff.
      deadline: Time when the diff should be complete by.

    Returns:
      Array of changes.
    """
    if not text1:
      # Just add some text (speedup).
      return [(self.DIFF_INSERT, text2)]

    if not text2:
      # Just delete some text (speedup).
      return [(self.DIFF_DELETE, text1)]

    if len(text1) > len(text2):
      (longtext, shorttext) = (text1, text2)
    else:
      (shorttext, longtext) = (text1, text2)
    i = longtext.find(shorttext)
    if i != -1:
      # Shorter text is inside the longer text (speedup).
      diffs = [(self.DIFF_INSERT, longtext[:i]), (self.DIFF_EQUAL, shorttext),
               (self.DIFF_INSERT, longtext[i + len(shorttext):])]
      # Swap insertions for deletions if diff is reversed.
      if len(text1) > len(text2):
        diffs[0] = (self.DIFF_DELETE, diffs[0][1])
        diffs[2] = (self.DIFF_DELETE, diffs[2][1])
      return diffs

    if len(shorttext) == 1:
      # Single character string.
      # After the previous speedup, the character can't be an equality.
      return [(self.DIFF_DELETE, text1), (self.DIFF_INSERT, text2)]

    # Check to see if the problem can be split in two.
    hm = self.diff_halfMatch(text1, text2)
    if hm:
      # A half-match was found, sort out the return data.
      (text1_a, text1_b, text2_a, text2_b, mid_common) = hm
      # Send both pairs off for separate processing.
      diffs_a = self.diff_main(text1_a, text2_a, checklines, deadline)
      diffs_b = self.diff_main(text1_b, text2_b, checklines, deadline)
      # Merge the results.
      return diffs_a + [(self.DIFF_EQUAL, mid_common)] + diffs_b

    if checklines and len(text1) > 100 and len(text2) > 100:
      return self.diff_lineMode(text1, text2, deadline)

    return self.diff_bisect(text1, text2, deadline)

  def diff_lineMode(self, text1, text2, deadline):
    """Do a quick line-level diff on both strings, then rediff the parts for
      greater accuracy.
      This speedup can produce non-minimal diffs.

    Args:
      text1: Old string to be diffed.
      text2: New string to be diffed.
      deadline: Time when the diff should be complete by.

    Returns:
      Array of changes.
    """

    # Scan the text on a line-by-line basis first.
    (text1, text2, linearray) = self.diff_linesToChars(text1, text2)

    diffs = self.diff_main(text1, text2, False, deadline)

    # Convert the diff back to original text.
    self.diff_charsToLines(diffs, linearray)
    # Eliminate freak matches (e.g. blank lines)
    self.diff_cleanupSemantic(diffs)

    # Rediff any replacement blocks, this time character-by-character.
    # Add a dummy entry at the end.
    diffs.append((self.DIFF_EQUAL, ''))
    pointer = 0
    count_delete = 0
    count_insert = 0
    text_delete = ''
    text_insert = ''
    while pointer < len(diffs):
      if diffs[pointer][0] == self.DIFF_INSERT:
        count_insert += 1
        text_insert += diffs[pointer][1]
      elif diffs[pointer][0] == self.DIFF_DELETE:
        count_delete += 1
        text_delete += diffs[pointer][1]
      elif diffs[pointer][0] == self.DIFF_EQUAL:
        # Upon reaching an equality, check for prior redundancies.
        if count_delete >= 1 and count_insert >= 1:
          # Delete the offending records and add the merged ones.
          a = self.diff_main(text_delete, text_insert, False, deadline)
          diffs[pointer - count_delete - count_insert : pointer] = a
          pointer = pointer - count_delete - count_insert + len(a)
        count_insert = 0
        count_delete = 0
        text_delete = ''
        text_insert = ''

      pointer += 1

    diffs.pop()  # Remove the dummy entry at the end.

    return diffs

  def diff_bisect(self, text1, text2, deadline):
    """Find the 'middle snake' of a diff, split the problem in two
      and return the recursively constructed diff.
      See Myers 1986 paper: An O(ND) Difference Algorithm and Its Variations.

    Args:
      text1: Old string to be diffed.
      text2: New string to be diffed.
      deadline: Time at which to bail if not yet complete.

    Returns:
      Array of diff tuples.
    """

    # Cache the text lengths to prevent multiple calls.
    text1_length = len(text1)
    text2_length = len(text2)
    max_d = (text1_length + text2_length + 1) // 2
    v_offset = max_d
    v_length = 2 * max_d
    v1 = [-1] * v_length
    v1[v_offset + 1] = 0
    v2 = v1[:]
    delta = text1_length - text2_length
    # If the total number of characters is odd, then the front path will
    # collide with the reverse path.
    front = (delta % 2 != 0)
    # Offsets for start and end of k loop.
    # Prevents mapping of space beyond the grid.
    k1start = 0
    k1end = 0
    k2start = 0
    k2end = 0
    for d in range(max_d):
      # Bail out if deadline is reached.
      if time.time() > deadline:
        break

      # Walk the front path one step.
      for k1 in range(-d + k1start, d + 1 - k1end, 2):
        k1_offset = v_offset + k1
        if k1 == -d or (k1 != d and
            v1[k1_offset - 1] < v1[k1_offset + 1]):
          x1 = v1[k1_offset + 1]
        else:
          x1 = v1[k1_offset - 1] + 1
        y1 = x1 - k1
        while (x1 < text1_length and y1 < text2_length and
               text1[x1] == text2[y1]):
          x1 += 1
          y1 += 1
        v1[k1_offset] = x1
        if x1 > text1_length:
          # Ran off the right of the graph.
          k1end += 2
        elif y1 > text2_length:
          # Ran off the bottom of the graph.
          k1start += 2
        elif front:
          k2_offset = v_offset + delta - k1
          if k2_offset >= 0 and k2_offset < v_length and v2[k2_offset] != -1:
            # Mirror x2 onto top-left coordinate system.
            x2 = text1_length - v2[k2_offset]
            if x1 >= x2:
              # Overlap detected.
              return self.diff_bisectSplit(text1, text2, x1, y1, deadline)

      # Walk the reverse path one step.
      for k2 in range(-d + k2start, d + 1 - k2end, 2):
        k2_offset = v_offset + k2
        if k2 == -d or (k2 != d and
            v2[k2_offset - 1] < v2[k2_offset + 1]):
          x2 = v2[k2_offset + 1]
        else:
          x2 = v2[k2_offset - 1] + 1
        y2 = x2 - k2
        while (x2 < text1_length and y2 < text2_length and
               text1[-x2 - 1] == text2[-y2 - 1]):
          x2 += 1
          y2 += 1
        v2[k2_offset] = x2
        if x2 > text1_length:
          # Ran off the left of the graph.
          k2end += 2
        elif y2 > text2_length:
          # Ran off the top of the graph.
          k2start += 2
        elif not front:
          k1_offset = v_offset + delta - k2
          if k1_offset >= 0 and k1_offset < v_length and v1[k1_offset] != -1:
            x1 = v1[k1_offset]
            y1 = v_offset + x1 - k1_offset
            # Mirror x2 onto top-left coordinate system.
            x2 = text1_length - x2
            if x1 >= x2:
              # Overlap detected.
              return self.diff_bisectSplit(text1, text2, x1, y1, deadline)

    # Diff took too long and hit the deadline or
    # number of diffs equals number of characters, no commonality at all.
    return [(self.DIFF_DELETE, text1), (self.DIFF_INSERT, text2)]

  def diff_bisectSplit(self, text1, text2, x, y, deadline):
    """Given the location of the 'middle snake', split the diff in two parts
    and recurse.

    Args:
      text1: Old string to be diffed.
      text2: New string to be diffed.
      x: Index of split point in text1.
      y: Index of split point in text2.
      deadline: Time at which to bail if not yet complete.

    Returns:
      Array of diff tuples.
    """
    text1a = text1[:x]
    text2a = text2[:y]
    text1b = text1[x:]
    text2b = text2[y:]

    # Compute both diffs serially.
    diffs = self.diff_main(text1a, text2a, False, deadline)
    diffsb = self.diff_main(text1b, text2b, False, deadline)

    return diffs + diffsb

  def diff_linesToChars(self, text1, text2):
    """Split two texts into an array of strings.  Reduce the texts to a string
    of hashes where each Unicode character represents one line.

    Args:
      text1: First string.
      text2: Second string.

    Returns:
      Three element tuple, containing the encoded text1, the encoded text2 and
      the array of unique strings.  The zeroth element of the array of unique
      strings is intentionally blank.
    """
    lineArray = []  # e.g. lineArray[4] == "Hello\n"
    lineHash = {}   # e.g. lineHash["Hello\n"] == 4

    # "\x00" is a valid character, but various debuggers don't like it.
    # So we'll insert a junk entry to avoid generating a null character.
    lineArray.append('')

    def diff_linesToCharsMunge(text):
      """Split a text into an array of strings.  Reduce the texts to a string
      of hashes where each Unicode character represents one line.
      Modifies linearray and linehash through being a closure.

      Args:
        text: String to encode.

      Returns:
        Encoded string.
      """
      chars = []
      # Walk the text, pulling out a substring for each line.
      # text.split('\n') would would temporarily double our memory footprint.
      # Modifying text would create many large strings to garbage collect.
      lineStart = 0
      lineEnd = -1
      while lineEnd < len(text) - 1:
        lineEnd = text.find('\n', lineStart)
        if lineEnd == -1:
          lineEnd = len(text) - 1
        line = text[lineStart:lineEnd + 1]
        lineStart = lineEnd + 1

        if line in lineHash:
          chars.append(chr(lineHash[line]))
        else:
          lineArray.append(line)
          lineHash[line] = len(lineArray) - 1
          chars.append(chr(len(lineArray) - 1))
      return "".join(chars)

    chars1 = diff_linesToCharsMunge(text1)
    chars2 = diff_linesToCharsMunge(text2)
    return (chars1, chars2, lineArray)

  def diff_charsToLines(self, diffs, lineArray):
    """Rehydrate the text in a diff from a string of line hashes to real lines
    of text.

    Args:
      diffs: Array of diff tuples.
      lineArray: Array of unique strings.
    """
    for x in range(len(diffs)):
      text = []
      for char in diffs[x][1]:
        text.append(lineArray[ord(char)])
      diffs[x] = (diffs[x][0], "".join(text))

  def diff_commonPrefix(self, text1, text2):
    """Determine the common prefix of two strings.

    Args:
      text1: First string.
      text2: Second string.

    Returns:
      The number of characters common to the start of each string.
    """
    # Quick check for common null cases.
    if not text1 or not text2 or text1[0] != text2[0]:
      return 0
    # Binary search.
    # Performance analysis: http://neil.fraser.name/news/2007/10/09/
    pointermin = 0
    pointermax = min(len(text1), len(text2))
    pointermid = pointermax
    pointerstart = 0
    while pointermin < pointermid:
      if text1[pointerstart:pointermid] == text2[pointerstart:pointermid]:
        pointermin = pointermid
        pointerstart = pointermin
      else:
        pointermax = pointermid
      pointermid = (pointermax - pointermin) // 2 + pointermin
    return pointermid

  def diff_commonSuffix(self, text1, text2):
    """Determine the common suffix of two strings.

    Args:
      text1: First string.
      text2: Second string.

    Returns:
      The number of characters common to the end of each string.
    """
    # Quick check for common null cases.
    if not text1 or not text2 or text1[-1] != text2[-1]:
      return 0
    # Binary search.
    # Performance analysis: http://neil.fraser.name/news/2007/10/09/
    pointermin = 0
    pointermax = min(len(text1), len(text2))
    pointermid = pointermax
    pointerend = 0
    while pointermin < pointermid:
      if (text1[-pointermid:len(text1) - pointerend] ==
          text2[-pointermid:len(text2) - pointerend]):
        pointermin = pointermid
        pointerend = pointermin
      else:
        pointermax = pointermid
      pointermid = (pointermax - pointermin) // 2 + pointermin
    return pointermid

  def diff_commonOverlap(self, text1, text2):
    """Determine if the suffix of one string is the prefix of another.

    Args:
      text1 First string.
      text2 Second string.

    Returns:
      The number of characters common to the end of the first
      string and the start of the second string.
    """
    # Cache the text lengths to prevent multiple calls.
    text1_length = len(text1)
    text2_length = len(text2)
    # Eliminate the null case.
    if text1_length == 0 or text2_length == 0:
      return 0
    # Truncate the longer string.
    if text1_length > text2_length:
      text1 = text1[-text2_length:]
    elif text1_length < text2_length:
      text2 = text2[:text1_length]
    text_length = min(text1_length, text2_length)
    # Quick check for the worst case.
    if text1 == text2:
      return text_length

    # Start by looking for a single character match
    # and increase length until no match is found.
    # Performance analysis: http://neil.fraser.name/news/2010/11/04/
    best = 0
    length = 1
    while True:
      pattern = text1[-length:]
      found = text2.find(pattern)
      if found == -1:
        return best
      length += found
      if found == 0 or text1[-length:] == text2[:length]:
        best = length
        length += 1

  def diff_halfMatch(self, text1, text2):
    """Do the two texts share a substring which is at least half the length of
    the longer text?
    This speedup can produce non-minimal diffs.

    Args:
      text1: First string.
      text2: Second string.

    Returns:
      Five element Array, containing the prefix of text1, the suffix of text1,
      the prefix of text2, the suffix of text2 and the common middle.  Or None
      if there was no match.
    """
    if self.Diff_Timeout <= 0:
      # Don't risk returning a non-optimal diff if we have unlimited time.
      return None
    if len(text1) > len(text2):
      (longtext, shorttext) = (text1, text2)
    else:
      (shorttext, longtext) = (text1, text2)
    if len(longtext) < 4 or len(shorttext) * 2 < len(longtext):
      return None  # Pointless.

    def diff_halfMatchI(longtext, shorttext, i):
      """Does a substring of shorttext exist within longtext such that the
      substring is at least half the length of longtext?
      Closure, but does not reference any external variables.

      Args:
        longtext: Longer string.
        shorttext: Shorter string.
        i: Start index of quarter length substring within longtext.

      Returns:
        Five element Array, containing the prefix of longtext, the suffix of
        longtext, the prefix of shorttext, the suffix of shorttext and the
        common middle.  Or None if there was no match.
      """
      seed = longtext[i:i + len(longtext) // 4]
      best_common = ''
      j = shorttext.find(seed)
      while j != -1:
        prefixLength = self.diff_commonPrefix(longtext[i:], shorttext[j:])
        suffixLength = self.diff_commonSuffix(longtext[:i], shorttext[:j])
        if len(best_common) < suffixLength + prefixLength:
          best_common = (shorttext[j - suffixLength:j] +
              shorttext[j:j + prefixLength])
          best_longtext_a = longtext[:i - suffixLength]
          best_longtext_b = longtext[i + prefixLength:]
          best_shorttext_a = shorttext[:j - suffixLength]
          best_shorttext_b = shorttext[j + prefixLength:]
        j = shorttext.find(seed, j + 1)

      if len(best_common) * 2 >= len(longtext):
        return (best_longtext_a, best_longtext_b,
                best_shorttext_a, best_shorttext_b, best_common)
      else:
        return None

    # First check if the second quarter is the seed for a half-match.
    hm1 = diff_halfMatchI(longtext, shorttext, (len(longtext) + 3) // 4)
    # Check again based on the third quarter.
    hm2 = diff_halfMatchI(longtext, shorttext, (len(longtext) + 1) // 2)
    if not hm1 and not hm2:
      return None
    elif not hm2:
      hm = hm1
    elif not hm1:
      hm = hm2
    else:
      # Both matched.  Select the longest.
      if len(hm1[4]) > len(hm2[4]):
        hm = hm1
      else:
        hm = hm2

    # A half-match was found, sort out the return data.
    if len(text1) > len(text2):
      (text1_a, text1_b, text2_a, text2_b, mid_common) = hm
    else:
      (text2_a, text2_b, text1_a, text1_b, mid_common) = hm
    return (text1_a, text1_b, text2_a, text2_b, mid_common)

  def diff_cleanupSemantic(self, diffs):
    """Reduce the number of edits by eliminating semantically trivial
    equalities.

    Args:
      diffs: Array of diff tuples.
    """
    changes = False
    equalities = []  # Stack of indices where equalities are found.
    lastequality = None  # Always equal to diffs[equalities[-1]][1]
    pointer = 0  # Index of current position.
    # Number of chars that changed prior to the equality.
    length_insertions1, length_deletions1 = 0, 0
    # Number of chars that changed after the equality.
    length_insertions2, length_deletions2 = 0, 0
    while pointer < len(diffs):
      if diffs[pointer][0] == self.DIFF_EQUAL:  # Equality found.
        equalities.append(pointer)
        length_insertions1, length_insertions2 = length_insertions2, 0
        length_deletions1, length_deletions2 = length_deletions2, 0
        lastequality = diffs[pointer][1]
      else:  # An insertion or deletion.
        if diffs[pointer][0] == self.DIFF_INSERT:
          length_insertions2 += len(diffs[pointer][1])
        else:
          length_deletions2 += len(diffs[pointer][1])
        # Eliminate an equality that is smaller or equal to the edits on both
        # sides of it.
        if (lastequality and (len(lastequality) <=
            max(length_insertions1, length_deletions1)) and
            (len(lastequality) <= max(length_insertions2, length_deletions2))):
          # Duplicate record.
          diffs.insert(equalities[-1], (self.DIFF_DELETE, lastequality))
          # Change second copy to insert.
          diffs[equalities[-1] + 1] = (self.DIFF_INSERT,
              diffs[equalities[-1] + 1][1])
          # Throw away the equality we just deleted.
          equalities.pop()
          # Throw away the previous equality (it needs to be reevaluated).
          if len(equalities):
            equalities.pop()
          if len(equalities):
            pointer = equalities[-1]
          else:
            pointer = -1
          # Reset the counters.
          length_insertions1, length_deletions1 = 0, 0
          length_insertions2, length_deletions2 = 0, 0
          lastequality = None
          changes = True
      pointer += 1

    # Normalize the diff.
    if changes:
      self.diff_cleanupMerge(diffs)
    self.diff_cleanupSemanticLossless(diffs)

    # Find any overlaps between deletions and insertions.
    # e.g: <del>abcxxx</del><ins>xxxdef</ins>
    #   -> <del>abc</del>xxx<ins>def</ins>
    # e.g: <del>xxxabc</del><ins>defxxx</ins>
    #   -> <ins>def</ins>xxx<del>abc</del>
    # Only extract an overlap if it is as big as the edit ahead or behind it.
    pointer = 1
    while pointer < len(diffs):
      if (diffs[pointer - 1][0] == self.DIFF_DELETE and
          diffs[pointer][0] == self.DIFF_INSERT):
        deletion = diffs[pointer - 1][1]
        insertion = diffs[pointer][1]
        overlap_length1 = self.diff_commonOverlap(deletion, insertion)
        overlap_length2 = self.diff_commonOverlap(insertion, deletion)
        if overlap_length1 >= overlap_length2:
          if (overlap_length1 >= len(deletion) / 2.0 or
              overlap_length1 >= len(insertion) / 2.0):
            # Overlap found.  Insert an equality and trim the surrounding edits.
            diffs.insert(pointer, (self.DIFF_EQUAL,
                                   insertion[:overlap_length1]))
            diffs[pointer - 1] = (self.DIFF_DELETE,
                                  deletion[:len(deletion) - overlap_length1])
            diffs[pointer + 1] = (self.DIFF_INSERT,
                                  insertion[overlap_length1:])
            pointer += 1
        else:
          if (overlap_length2 >= len(deletion) / 2.0 or
              overlap_length2 >= len(insertion) / 2.0):
            # Reverse overlap found.
            # Insert an equality and swap and trim the surrounding edits.
            diffs.insert(pointer, (self.DIFF_EQUAL, deletion[:overlap_length2]))
            diffs[pointer - 1] = (self.DIFF_INSERT,
                                  insertion[:len(insertion) - overlap_length2])
            diffs[pointer + 1] = (self.DIFF_DELETE, deletion[overlap_length2:])
            pointer += 1
        pointer += 1
      pointer += 1

  def diff_cleanupSemanticLossless(self, diffs):
    """Look for single edits surrounded on both sides by equalities
    which can be shifted sideways to align the edit to a word boundary.
    e.g: The c<ins>at c</ins>ame. -> The <ins>cat </ins>came.

    Args:
      diffs: Array of diff tuples.
    """

    def diff_cleanupSemanticScore(one, two):
      """Given two strings, compute a score representing whether the
      internal boundary falls on logical boundaries.
      Scores range from 6 (best) to 0 (worst).
      Closure, but does not reference any external variables.

      Args:
        one: First string.
        two: Second string.

      Returns:
        The score.
      """
      if not one or not two:
        # Edges are the best.
        return 6

      # Each port of this function behaves slightly differently due to
      # subtle differences in each language's definition of things like
      # 'whitespace'.  Since this function's purpose is largely cosmetic,
      # the choice has been made to use each language's native features
      # rather than force total conformity.
      char1 = one[-1]
      char2 = two[0]
      nonAlphaNumeric1 = not char1.isalnum()
      nonAlphaNumeric2 = not char2.isalnum()
      whitespace1 = nonAlphaNumeric1 and char1.isspace()
      whitespace2 = nonAlphaNumeric2 and char2.isspace()
      lineBreak1 = whitespace1 and (char1 == "\r" or char1 == "\n")
      lineBreak2 = whitespace2 and (char2 == "\r" or char2 == "\n")
      blankLine1 = lineBreak1 and self.BLANKLINEEND.search(one)
      blankLine2 = lineBreak2 and self.BLANKLINESTART.match(two)

      if blankLine1 or blankLine2:
        # Five points for blank lines.
        return 5
      elif lineBreak1 or lineBreak2:
        # Four points for line breaks.
        return 4
      elif nonAlphaNumeric1 and not whitespace1 and whitespace2:
        # Three points for end of sentences.
        return 3
      elif whitespace1 or whitespace2:
        # Two points for whitespace.
        return 2
      elif nonAlphaNumeric1 or nonAlphaNumeric2:
        # One point for non-alphanumeric.
        return 1
      return 0

    pointer = 1
    # Intentionally ignore the first and last element (don't need checking).
    while pointer < len(diffs) - 1:
      if (diffs[pointer - 1][0] == self.DIFF_EQUAL and
          diffs[pointer + 1][0] == self.DIFF_EQUAL):
        # This is a single edit surrounded by equalities.
        equality1 = diffs[pointer - 1][1]
        edit = diffs[pointer][1]
        equality2 = diffs[pointer + 1][1]

        # First, shift the edit as far left as possible.
        commonOffset = self.diff_commonSuffix(equality1, edit)
        if commonOffset:
          commonString = edit[-commonOffset:]
          equality1 = equality1[:-commonOffset]
          edit = commonString + edit[:-commonOffset]
          equality2 = commonString + equality2

        # Second, step character by character right, looking for the best fit.
        bestEquality1 = equality1
        bestEdit = edit
        bestEquality2 = equality2
        bestScore = (diff_cleanupSemanticScore(equality1, edit) +
            diff_cleanupSemanticScore(edit, equality2))
        while edit and equality2 and edit[0] == equality2[0]:
          equality1 += edit[0]
          edit = edit[1:] + equality2[0]
          equality2 = equality2[1:]
          score = (diff_cleanupSemanticScore(equality1, edit) +
              diff_cleanupSemanticScore(edit, equality2))
          # The >= encourages trailing rather than leading whitespace on edits.
          if score >= bestScore:
            bestScore = score
            bestEquality1 = equality1
            bestEdit = edit
            bestEquality2 = equality2

        if diffs[pointer - 1][1] != bestEquality1:
          # We have an improvement, save it back to the diff.
          if bestEquality1:
            diffs[pointer - 1] = (diffs[pointer - 1][0], bestEquality1)
          else:
            del diffs[pointer - 1]
            pointer -= 1
          diffs[pointer] = (diffs[pointer][0], bestEdit)
          if bestEquality2:
            diffs[pointer + 1] = (diffs[pointer + 1][0], bestEquality2)
          else:
            del diffs[pointer + 1]
            pointer -= 1
      pointer += 1

  # Define some regex patterns for matching boundaries.
  BLANKLINEEND = re.compile(r"\n\r?\n$");
  BLANKLINESTART = re.compile(r"^\r?\n\r?\n");

  def diff_cleanupEfficiency(self, diffs):
    """Reduce the number of edits by eliminating operationally trivial
    equalities.

    Args:
      diffs: Array of diff tuples.
    """
    changes = False
    equalities = []  # Stack of indices where equalities are found.
    lastequality = None  # Always equal to diffs[equalities[-1]][1]
    pointer = 0  # Index of current position.
    pre_ins = False  # Is there an insertion operation before the last equality.
    pre_del = False  # Is there a deletion operation before the last equality.
    post_ins = False  # Is there an insertion operation after the last equality.
    post_del = False  # Is there a deletion operation after the last equality.
    while pointer < len(diffs):
      if diffs[pointer][0] == self.DIFF_EQUAL:  # Equality found.
        if (len(diffs[pointer][1]) < self.Diff_EditCost and
            (post_ins or post_del)):
          # Candidate found.
          equalities.append(pointer)
          pre_ins = post_ins
          pre_del = post_del
          lastequality = diffs[pointer][1]
        else:
          # Not a candidate, and can never become one.
          equalities = []
          lastequality = None

        post_ins = post_del = False
      else:  # An insertion or deletion.
        if diffs[pointer][0] == self.DIFF_DELETE:
          post_del = True
        else:
          post_ins = True

        # Five types to be split:
        # <ins>A</ins><del>B</del>XY<ins>C</ins><del>D</del>
        # <ins>A</ins>X<ins>C</ins><del>D</del>
        # <ins>A</ins><del>B</del>X<ins>C</ins>
        # <ins>A</del>X<ins>C</ins><del>D</del>
        # <ins>A</ins><del>B</del>X<del>C</del>

        if lastequality and ((pre_ins and pre_del and post_ins and post_del) or
                             ((len(lastequality) < self.Diff_EditCost / 2) and
                              (pre_ins + pre_del + post_ins + post_del) == 3)):
          # Duplicate record.
          diffs.insert(equalities[-1], (self.DIFF_DELETE, lastequality))
          # Change second copy to insert.
          diffs[equalities[-1] + 1] = (self.DIFF_INSERT,
              diffs[equalities[-1] + 1][1])
          equalities.pop()  # Throw away the equality we just deleted.
          lastequality = None
          if pre_ins and pre_del:
            # No changes made which could affect previous entry, keep going.
            post_ins = post_del = True
            equalities = []
          else:
            if len(equalities):
              equalities.pop()  # Throw away the previous equality.
            if len(equalities):
              pointer = equalities[-1]
            else:
              pointer = -1
            post_ins = post_del = False
          changes = True
      pointer += 1

    if changes:
      self.diff_cleanupMerge(diffs)

  def diff_cleanupMerge(self, diffs):
    """Reorder and merge like edit sections.  Merge equalities.
    Any edit section can move as long as it doesn't cross an equality.

    Args:
      diffs: Array of diff tuples.
    """
    diffs.append((self.DIFF_EQUAL, ''))  # Add a dummy entry at the end.
    pointer = 0
    count_delete = 0
    count_insert = 0
    text_delete = ''
    text_insert = ''
    while pointer < len(diffs):
      if diffs[pointer][0] == self.DIFF_INSERT:
        count_insert += 1
        text_insert += diffs[pointer][1]
        pointer += 1
      elif diffs[pointer][0] == self.DIFF_DELETE:
        count_delete += 1
        text_delete += diffs[pointer][1]
        pointer += 1
      elif diffs[pointer][0] == self.DIFF_EQUAL:
        # Upon reaching an equality, check for prior redundancies.
        if count_delete + count_insert > 1:
          if count_delete != 0 and count_insert != 0:
            # Factor out any common prefixies.
            commonlength = self.diff_commonPrefix(text_insert, text_delete)
            if commonlength != 0:
              x = pointer - count_delete - count_insert - 1
              if x >= 0 and diffs[x][0] == self.DIFF_EQUAL:
                diffs[x] = (diffs[x][0], diffs[x][1] +
                            text_insert[:commonlength])
              else:
                diffs.insert(0, (self.DIFF_EQUAL, text_insert[:commonlength]))
                pointer += 1
              text_insert = text_insert[commonlength:]
              text_delete = text_delete[commonlength:]
            # Factor out any common suffixies.
            commonlength = self.diff_commonSuffix(text_insert, text_delete)
            if commonlength != 0:
              diffs[pointer] = (diffs[pointer][0], text_insert[-commonlength:] +
                  diffs[pointer][1])
              text_insert = text_insert[:-commonlength]
              text_delete = text_delete[:-commonlength]
          # Delete the offending records and add the merged ones.
          if count_delete == 0:
            diffs[pointer - count_insert : pointer] = [
                (self.DIFF_INSERT, text_insert)]
          elif count_insert == 0:
            diffs[pointer - count_delete : pointer] = [
                (self.DIFF_DELETE, text_delete)]
          else:
            diffs[pointer - count_delete - count_insert : pointer] = [
                (self.DIFF_DELETE, text_delete),
                (self.DIFF_INSERT, text_insert)]
          pointer = pointer - count_delete - count_insert + 1
          if count_delete != 0:
            pointer += 1
          if count_insert != 0:
            pointer += 1
        elif pointer != 0 and diffs[pointer - 1][0] == self.DIFF_EQUAL:
          # Merge this equality with the previous one.
          diffs[pointer - 1] = (diffs[pointer - 1][0],
                                diffs[pointer - 1][1] + diffs[pointer][1])
          del diffs[pointer]
        else:
          pointer += 1

        count_insert = 0
        count_delete = 0
        text_delete = ''
        text_insert = ''

    if diffs[-1][1] == '':
      diffs.pop()  # Remove the dummy entry at the end.

    # Second pass: look for single edits surrounded on both sides by equalities
    # which can be shifted sideways to eliminate an equality.
    # e.g: A<ins>BA</ins>C -> <ins>AB</ins>AC
    changes = False
    pointer = 1
    # Intentionally ignore the first and last element (don't need checking).
    while pointer < len(diffs) - 1:
      if (diffs[pointer - 1][0] == self.DIFF_EQUAL and
          diffs[pointer + 1][0] == self.DIFF_EQUAL):
        # This is a single edit surrounded by equalities.
        if diffs[pointer][1].endswith(diffs[pointer - 1][1]):
          # Shift the edit over the previous equality.
          diffs[pointer] = (diffs[pointer][0],
              diffs[pointer - 1][1] +
              diffs[pointer][1][:-len(diffs[pointer - 1][1])])
          diffs[pointer + 1] = (diffs[pointer + 1][0],
                                diffs[pointer - 1][1] + diffs[pointer + 1][1])
          del diffs[pointer - 1]
          changes = True
        elif diffs[pointer][1].startswith(diffs[pointer + 1][1]):
          # Shift the edit over the next equality.
          diffs[pointer - 1] = (diffs[pointer - 1][0],
                                diffs[pointer - 1][1] + diffs[pointer + 1][1])
          diffs[pointer] = (diffs[pointer][0],
              diffs[pointer][1][len(diffs[pointer + 1][1]):] +
              diffs[pointer + 1][1])
          del diffs[pointer + 1]
          changes = True
      pointer += 1

    # If shifts were made, the diff needs reordering and another shift sweep.
    if changes:
      self.diff_cleanupMerge(diffs)

  def diff_xIndex(self, diffs, loc):
    """loc is a location in text1, compute and return the equivalent location
    in text2.  e.g. "The cat" vs "The big cat", 1->1, 5->8

    Args:
      diffs: Array of diff tuples.
      loc: Location within text1.

    Returns:
      Location within text2.
    """
    chars1 = 0
    chars2 = 0
    last_chars1 = 0
    last_chars2 = 0
    for x in range(len(diffs)):
      (op, text) = diffs[x]
      if op != self.DIFF_INSERT:  # Equality or deletion.
        chars1 += len(text)
      if op != self.DIFF_DELETE:  # Equality or insertion.
        chars2 += len(text)
      if chars1 > loc:  # Overshot the location.
        break
      last_chars1 = chars1
      last_chars2 = chars2

    if len(diffs) != x and diffs[x][0] == self.DIFF_DELETE:
      # The location was deleted.
      return last_chars2
    # Add the remaining len(character).
    return last_chars2 + (loc - last_chars1)

  def diff_prettyHtml(self, diffs):
    """Convert a diff array into a pretty HTML report.

    Args:
      diffs: Array of diff tuples.

    Returns:
      HTML representation.
    """
    html = []
    for (op, data) in diffs:
      text = (data.replace("&", "&amp;").replace("<", "&lt;")
                 .replace(">", "&gt;").replace("\n", "&para;<br>"))
      if op == self.DIFF_INSERT:
        html.append("<ins style=\"background:#e6ffe6;\">%s</ins>" % text)
      elif op == self.DIFF_DELETE:
        html.append("<del style=\"background:#ffe6e6;\">%s</del>" % text)
      elif op == self.DIFF_EQUAL:
        html.append("<span>%s</span>" % text)
    return "".join(html)

  def diff_text1(self, diffs):
    """Compute and return the source text (all equalities and deletions).

    Args:
      diffs: Array of diff tuples.

    Returns:
      Source text.
    """
    text = []
    for (op, data) in diffs:
      if op != self.DIFF_INSERT:
        text.append(data)
    return "".join(text)

  def diff_text2(self, diffs):
    """Compute and return the destination text (all equalities and insertions).

    Args:
      diffs: Array of diff tuples.

    Returns:
      Destination text.
    """
    text = []
    for (op, data) in diffs:
      if op != self.DIFF_DELETE:
        text.append(data)
    return "".join(text)

  def diff_levenshtein(self, diffs):
    """Compute the Levenshtein distance; the number of inserted, deleted or
    substituted characters.

    Args:
      diffs: Array of diff tuples.

    Returns:
      Number of changes.
    """
    levenshtein = 0
    insertions = 0
    deletions = 0
    for (op, data) in diffs:
      if op == self.DIFF_INSERT:
        insertions += len(data)
      elif op == self.DIFF_DELETE:
        deletions += len(data)
      elif op == self.DIFF_EQUAL:
        # A deletion and an insertion is one substitution.
        levenshtein += max(insertions, deletions)
        insertions = 0
        deletions = 0
    levenshtein += max(insertions, deletions)
    return levenshtein

  def diff_toDelta(self, diffs):
    """Crush the diff into an encoded string which describes the operations
    required to transform text1 into text2.
    E.g. =3\t-2\t+ing  -> Keep 3 chars, delete 2 chars, insert 'ing'.
    Operations are tab-separated.  Inserted text is escaped using %xx notation.

    Args:
      diffs: Array of diff tuples.

    Returns:
      Delta text.
    """
    text = []
    for (op, data) in diffs:
      if op == self.DIFF_INSERT:
        # High ascii will raise UnicodeDecodeError.  Use Unicode instead.
        data = data.encode("utf-8")
        text.append("+" + urllib.parse.quote(data, "!~*'();/?:@&=+$,# "))
      elif op == self.DIFF_DELETE:
        text.append("-%d" % len(data))
      elif op == self.DIFF_EQUAL:
        text.append("=%d" % len(data))
    return "\t".join(text)

  def diff_fromDelta(self, text1, delta):
    """Given the original text1, and an encoded string which describes the
    operations required to transform text1 into text2, compute the full diff.

    Args:
      text1: Source string for the diff.
      delta: Delta text.

    Returns:
      Array of diff tuples.

    Raises:
      ValueError: If invalid input.
    """
    diffs = []
    pointer = 0  # Cursor in text1
    tokens = delta.split("\t")
    for token in tokens:
      if token == "":
        # Blank tokens are ok (from a trailing \t).
        continue
      # Each token begins with a one character parameter which specifies the
      # operation of this token (delete, insert, equality).
      param = token[1:]
      if token[0] == "+":
        param = urllib.parse.unquote(param)
        diffs.append((self.DIFF_INSERT, param))
      elif token[0] == "-" or token[0] == "=":
        try:
          n = int(param)
        except ValueError:
          raise ValueError("Invalid number in diff_fromDelta: " + param)
        if n < 0:
          raise ValueError("Negative number in diff_fromDelta: " + param)
        text = text1[pointer : pointer + n]
        pointer += n
        if token[0] == "=":
          diffs.append((self.DIFF_EQUAL, text))
        else:
          diffs.append((self.DIFF_DELETE, text))
      else:
        # Anything else is an error.
        raise ValueError("Invalid diff operation in diff_fromDelta: " +
            token[0])
    if pointer != len(text1):
      raise ValueError(
          "Delta length (%d) does not equal source text length (%d)." %
         (pointer, len(text1)))
    return diffs

  #  MATCH FUNCTIONS

  def match_main(self, text, pattern, loc):
    """Locate the best instance of 'pattern' in 'text' near 'loc'.

    Args:
      text: The text to search.
      pattern: The pattern to search for.
      loc: The location to search around.

    Returns:
      Best match index or -1.
    """
    # Check for null inputs.
    if text == None or pattern == None:
      raise ValueError("Null inputs. (match_main)")

    loc = max(0, min(loc, len(text)))
    if text == pattern:
      # Shortcut (potentially not guaranteed by the algorithm)
      return 0
    elif not text:
      # Nothing to match.
      return -1
    elif text[loc:loc + len(pattern)] == pattern:
      # Perfect match at the perfect spot!  (Includes case of null pattern)
      return loc
    else:
      # Do a fuzzy compare.
      match = self.match_bitap(text, pattern, loc)
      return match

  def match_bitap(self, text, pattern, loc):
    """Locate the best instance of 'pattern' in 'text' near 'loc' using the
    Bitap algorithm.

    Args:
      text: The text to search.
      pattern: The pattern to search for.
      loc: The location to search around.

    Returns:
      Best match index or -1.
    """
    # Python doesn't have a maxint limit, so ignore this check.
    #if self.Match_MaxBits != 0 and len(pattern) > self.Match_MaxBits:
    #  raise ValueError("Pattern too long for this application.")

    # Initialise the alphabet.
    s = self.match_alphabet(pattern)

    def match_bitapScore(e, x):
      """Compute and return the score for a match with e errors and x location.
      Accesses loc and pattern through being a closure.

      Args:
        e: Number of errors in match.
        x: Location of match.

      Returns:
        Overall score for match (0.0 = good, 1.0 = bad).
      """
      accuracy = float(e) / len(pattern)
      proximity = abs(loc - x)
      if not self.Match_Distance:
        # Dodge divide by zero error.
        return proximity and 1.0 or accuracy
      return accuracy + (proximity / float(self.Match_Distance))

    # Highest score beyond which we give up.
    score_threshold = self.Match_Threshold
    # Is there a nearby exact match? (speedup)
    best_loc = text.find(pattern, loc)
    if best_loc != -1:
      score_threshold = min(match_bitapScore(0, best_loc), score_threshold)
      # What about in the other direction? (speedup)
      best_loc = text.rfind(pattern, loc + len(pattern))
      if best_loc != -1:
        score_threshold = min(match_bitapScore(0, best_loc), score_threshold)

    # Initialise the bit arrays.
    matchmask = 1 << (len(pattern) - 1)
    best_loc = -1

    bin_max = len(pattern) + len(text)
    # Empty initialization added to appease pychecker.
    last_rd = None
    for d in range(len(pattern)):
      # Scan for the best match each iteration allows for one more error.
      # Run a binary search to determine how far from 'loc' we can stray at
      # this error level.
      bin_min = 0
      bin_mid = bin_max
      while bin_min < bin_mid:
        if match_bitapScore(d, loc + bin_mid) <= score_threshold:
          bin_min = bin_mid
        else:
          bin_max = bin_mid
        bin_mid = (bin_max - bin_min) // 2 + bin_min

      # Use the result from this iteration as the maximum for the next.
      bin_max = bin_mid
      start = max(1, loc - bin_mid + 1)
      finish = min(loc + bin_mid, len(text)) + len(pattern)

      rd = [0] * (finish + 2)
      rd[finish + 1] = (1 << d) - 1
      for j in range(finish, start - 1, -1):
        if len(text) <= j - 1:
          # Out of range.
          charMatch = 0
        else:
          charMatch = s.get(text[j - 1], 0)
        if d == 0:  # First pass: exact match.
          rd[j] = ((rd[j + 1] << 1) | 1) & charMatch
        else:  # Subsequent passes: fuzzy match.
          rd[j] = (((rd[j + 1] << 1) | 1) & charMatch) | (
              ((last_rd[j + 1] | last_rd[j]) << 1) | 1) | last_rd[j + 1]
        if rd[j] & matchmask:
          score = match_bitapScore(d, j - 1)
          # This match will almost certainly be better than any existing match.
          # But check anyway.
          if score <= score_threshold:
            # Told you so.
            score_threshold = score
            best_loc = j - 1
            if best_loc > loc:
              # When passing loc, don't exceed our current distance from loc.
              start = max(1, 2 * loc - best_loc)
            else:
              # Already passed loc, downhill from here on in.
              break
      # No hope for a (better) match at greater error levels.
      if match_bitapScore(d + 1, loc) > score_threshold:
        break
      last_rd = rd
    return best_loc

  def match_alphabet(self, pattern):
    """Initialise the alphabet for the Bitap algorithm.

    Args:
      pattern: The text to encode.

    Returns:
      Hash of character locations.
    """
    s = {}
    for char in pattern:
      s[char] = 0
    for i in range(len(pattern)):
      s[pattern[i]] |= 1 << (len(pattern) - i - 1)
    return s

  #  PATCH FUNCTIONS

  def patch_addContext(self, patch, text):
    """Increase the context until it is unique,
    but don't let the pattern expand beyond Match_MaxBits.

    Args:
      patch: The patch to grow.
      text: Source text.
    """
    if len(text) == 0:
      return
    pattern = text[patch.start2 : patch.start2 + patch.length1]
    padding = 0

    # Look for the first and last matches of pattern in text.  If two different
    # matches are found, increase the pattern length.
    while (text.find(pattern) != text.rfind(pattern) and (self.Match_MaxBits ==
        0 or len(pattern) < self.Match_MaxBits - self.Patch_Margin -
        self.Patch_Margin)):
      padding += self.Patch_Margin
      pattern = text[max(0, patch.start2 - padding) :
                     patch.start2 + patch.length1 + padding]
    # Add one chunk for good luck.
    padding += self.Patch_Margin

    # Add the prefix.
    prefix = text[max(0, patch.start2 - padding) : patch.start2]
    if prefix:
      patch.diffs[:0] = [(self.DIFF_EQUAL, prefix)]
    # Add the suffix.
    suffix = text[patch.start2 + patch.length1 :
                  patch.start2 + patch.length1 + padding]
    if suffix:
      patch.diffs.append((self.DIFF_EQUAL, suffix))

    # Roll back the start points.
    patch.start1 -= len(prefix)
    patch.start2 -= len(prefix)
    # Extend lengths.
    patch.length1 += len(prefix) + len(suffix)
    patch.length2 += len(prefix) + len(suffix)

  def patch_make(self, a, b=None, c=None):
    """Compute a list of patches to turn text1 into text2.
    Use diffs if provided, otherwise compute it ourselves.
    There are four ways to call this function, depending on what data is
    available to the caller:
    Method 1:
    a = text1, b = text2
    Method 2:
    a = diffs
    Method 3 (optimal):
    a = text1, b = diffs
    Method 4 (deprecated, use method 3):
    a = text1, b = text2, c = diffs

    Args:
      a: text1 (methods 1,3,4) or Array of diff tuples for text1 to
          text2 (method 2).
      b: text2 (methods 1,4) or Array of diff tuples for text1 to
          text2 (method 3) or undefined (method 2).
      c: Array of diff tuples for text1 to text2 (method 4) or
          undefined (methods 1,2,3).

    Returns:
      Array of Patch objects.
    """
    text1 = None
    diffs = None
    if isinstance(a, str) and isinstance(b, str) and c is None:
      # Method 1: text1, text2
      # Compute diffs from text1 and text2.
      text1 = a
      diffs = self.diff_main(text1, b, True)
      if len(diffs) > 2:
        self.diff_cleanupSemantic(diffs)
        self.diff_cleanupEfficiency(diffs)
    elif isinstance(a, list) and b is None and c is None:
      # Method 2: diffs
      # Compute text1 from diffs.
      diffs = a
      text1 = self.diff_text1(diffs)
    elif isinstance(a, str) and isinstance(b, list) and c is None:
      # Method 3: text1, diffs
      text1 = a
      diffs = b
    elif (isinstance(a, str) and isinstance(b, str) and
          isinstance(c, list)):
      # Method 4: text1, text2, diffs
      # text2 is not used.
      text1 = a
      diffs = c
    else:
      raise ValueError("Unknown call format to patch_make.")

    if not diffs:
      return []  # Get rid of the None case.
    patches = []
    patch = patch_obj()
    char_count1 = 0  # Number of characters into the text1 string.
    char_count2 = 0  # Number of characters into the text2 string.
    prepatch_text = text1  # Recreate the patches to determine context info.
    postpatch_text = text1
    for x in range(len(diffs)):
      (diff_type, diff_text) = diffs[x]
      if len(patch.diffs) == 0 and diff_type != self.DIFF_EQUAL:
        # A new patch starts here.
        patch.start1 = char_count1
        patch.start2 = char_count2
      if diff_type == self.DIFF_INSERT:
        # Insertion
        patch.diffs.append(diffs[x])
        patch.length2 += len(diff_text)
        postpatch_text = (postpatch_text[:char_count2] + diff_text +
                          postpatch_text[char_count2:])
      elif diff_type == self.DIFF_DELETE:
        # Deletion.
        patch.length1 += len(diff_text)
        patch.diffs.append(diffs[x])
        postpatch_text = (postpatch_text[:char_count2] +
                          postpatch_text[char_count2 + len(diff_text):])
      elif (diff_type == self.DIFF_EQUAL and
            len(diff_text) <= 2 * self.Patch_Margin and
            len(patch.diffs) != 0 and len(diffs) != x + 1):
        # Small equality inside a patch.
        patch.diffs.append(diffs[x])
        patch.length1 += len(diff_text)
        patch.length2 += len(diff_text)

      if (diff_type == self.DIFF_EQUAL and
          len(diff_text) >= 2 * self.Patch_Margin):
        # Time for a new patch.
        if len(patch.diffs) != 0:
          self.patch_addContext(patch, prepatch_text)
          patches.append(patch)
          patch = patch_obj()
          # Unlike Unidiff, our patch lists have a rolling context.
          # http://code.google.com/p/google-diff-match-patch/wiki/Unidiff
          # Update prepatch text & pos to reflect the application of the
          # just completed patch.
          prepatch_text = postpatch_text
          char_count1 = char_count2

      # Update the current character count.
      if diff_type != self.DIFF_INSERT:
        char_count1 += len(diff_text)
      if diff_type != self.DIFF_DELETE:
        char_count2 += len(diff_text)

    # Pick up the leftover patch if not empty.
    if len(patch.diffs) != 0:
      self.patch_addContext(patch, prepatch_text)
      patches.append(patch)
    return patches

  def patch_deepCopy(self, patches):
    """Given an array of patches, return another array that is identical.

    Args:
      patches: Array of Patch objects.

    Returns:
      Array of Patch objects.
    """
    patchesCopy = []
    for patch in patches:
      patchCopy = patch_obj()
      # No need to deep copy the tuples since they are immutable.
      patchCopy.diffs = patch.diffs[:]
      patchCopy.start1 = patch.start1
      patchCopy.start2 = patch.start2
      patchCopy.length1 = patch.length1
      patchCopy.length2 = patch.length2
      patchesCopy.append(patchCopy)
    return patchesCopy

  def patch_apply(self, patches, text):
    """Merge a set of patches onto the text.  Return a patched text, as well
    as a list of true/false values indicating which patches were applied.

    Args:
      patches: Array of Patch objects.
      text: Old text.

    Returns:
      Two element Array, containing the new text and an array of boolean values.
    """
    if not patches:
      return (text, [])

    # Deep copy the patches so that no changes are made to originals.
    patches = self.patch_deepCopy(patches)

    nullPadding = self.patch_addPadding(patches)
    text = nullPadding + text + nullPadding
    self.patch_splitMax(patches)

    # delta keeps track of the offset between the expected and actual location
    # of the previous patch.  If there are patches expected at positions 10 and
    # 20, but the first patch was found at 12, delta is 2 and the second patch
    # has an effective expected position of 22.
    delta = 0
    results = []
    for patch in patches:
      expected_loc = patch.start2 + delta
      text1 = self.diff_text1(patch.diffs)
      end_loc = -1
      if len(text1) > self.Match_MaxBits:
        # patch_splitMax will only provide an oversized pattern in the case of
        # a monster delete.
        start_loc = self.match_main(text, text1[:self.Match_MaxBits],
                                    expected_loc)
        if start_loc != -1:
          end_loc = self.match_main(text, text1[-self.Match_MaxBits:],
              expected_loc + len(text1) - self.Match_MaxBits)
          if end_loc == -1 or start_loc >= end_loc:
            # Can't find valid trailing context.  Drop this patch.
            start_loc = -1
      else:
        start_loc = self.match_main(text, text1, expected_loc)
      if start_loc == -1:
        # No match found.  :(
        results.append(False)
        # Subtract the delta for this failed patch from subsequent patches.
        delta -= patch.length2 - patch.length1
      else:
        # Found a match.  :)
        results.append(True)
        delta = start_loc - expected_loc
        if end_loc == -1:
          text2 = text[start_loc : start_loc + len(text1)]
        else:
          text2 = text[start_loc : end_loc + self.Match_MaxBits]
        if text1 == text2:
          # Perfect match, just shove the replacement text in.
          text = (text[:start_loc] + self.diff_text2(patch.diffs) +
                      text[start_loc + len(text1):])
        else:
          # Imperfect match.
          # Run a diff to get a framework of equivalent indices.
          diffs = self.diff_main(text1, text2, False)
          if (len(text1) > self.Match_MaxBits and
              self.diff_levenshtein(diffs) / float(len(text1)) >
              self.Patch_DeleteThreshold):
            # The end points match, but the content is unacceptably bad.
            results[-1] = False
          else:
            self.diff_cleanupSemanticLossless(diffs)
            index1 = 0
            for (op, data) in patch.diffs:
              if op != self.DIFF_EQUAL:
                index2 = self.diff_xIndex(diffs, index1)
              if op == self.DIFF_INSERT:  # Insertion
                text = text[:start_loc + index2] + data + text[start_loc +
                                                               index2:]
              elif op == self.DIFF_DELETE:  # Deletion
                text = text[:start_loc + index2] + text[start_loc +
                    self.diff_xIndex(diffs, index1 + len(data)):]
              if op != self.DIFF_DELETE:
                index1 += len(data)
    # Strip the padding off.
    text = text[len(nullPadding):-len(nullPadding)]
    return (text, results)

  def patch_addPadding(self, patches):
    """Add some padding on text start and end so that edges can match
    something.  Intended to be called only from within patch_apply.

    Args:
      patches: Array of Patch objects.

    Returns:
      The padding string added to each side.
    """
    paddingLength = self.Patch_Margin
    nullPadding = ""
    for x in range(1, paddingLength + 1):
      nullPadding += chr(x)

    # Bump all the patches forward.
    for patch in patches:
      patch.start1 += paddingLength
      patch.start2 += paddingLength

    # Add some padding on start of first diff.
    patch = patches[0]
    diffs = patch.diffs
    if not diffs or diffs[0][0] != self.DIFF_EQUAL:
      # Add nullPadding equality.
      diffs.insert(0, (self.DIFF_EQUAL, nullPadding))
      patch.start1 -= paddingLength  # Should be 0.
      patch.start2 -= paddingLength  # Should be 0.
      patch.length1 += paddingLength
      patch.length2 += paddingLength
    elif paddingLength > len(diffs[0][1]):
      # Grow first equality.
      extraLength = paddingLength - len(diffs[0][1])
      newText = nullPadding[len(diffs[0][1]):] + diffs[0][1]
      diffs[0] = (diffs[0][0], newText)
      patch.start1 -= extraLength
      patch.start2 -= extraLength
      patch.length1 += extraLength
      patch.length2 += extraLength

    # Add some padding on end of last diff.
    patch = patches[-1]
    diffs = patch.diffs
    if not diffs or diffs[-1][0] != self.DIFF_EQUAL:
      # Add nullPadding equality.
      diffs.append((self.DIFF_EQUAL, nullPadding))
      patch.length1 += paddingLength
      patch.length2 += paddingLength
    elif paddingLength > len(diffs[-1][1]):
      # Grow last equality.
      extraLength = paddingLength - len(diffs[-1][1])
      newText = diffs[-1][1] + nullPadding[:extraLength]
      diffs[-1] = (diffs[-1][0], newText)
      patch.length1 += extraLength
      patch.length2 += extraLength

    return nullPadding

  def patch_splitMax(self, patches):
    """Look through the patches and break up any which are longer than the
    maximum limit of the match algorithm.
    Intended to be called only from within patch_apply.

    Args:
      patches: Array of Patch objects.
    """
    patch_size = self.Match_MaxBits
    if patch_size == 0:
      # Python has the option of not splitting strings due to its ability
      # to handle integers of arbitrary precision.
      return
    for x in range(len(patches)):
      if patches[x].length1 <= patch_size:
        continue
      bigpatch = patches[x]
      # Remove the big old patch.
      del patches[x]
      x -= 1
      start1 = bigpatch.start1
      start2 = bigpatch.start2
      precontext = ''
      while len(bigpatch.diffs) != 0:
        # Create one of several smaller patches.
        patch = patch_obj()
        empty = True
        patch.start1 = start1 - len(precontext)
        patch.start2 = start2 - len(precontext)
        if precontext:
          patch.length1 = patch.length2 = len(precontext)
          patch.diffs.append((self.DIFF_EQUAL, precontext))

        while (len(bigpatch.diffs) != 0 and
               patch.length1 < patch_size - self.Patch_Margin):
          (diff_type, diff_text) = bigpatch.diffs[0]
          if diff_type == self.DIFF_INSERT:
            # Insertions are harmless.
            patch.length2 += len(diff_text)
            start2 += len(diff_text)
            patch.diffs.append(bigpatch.diffs.pop(0))
            empty = False
          elif (diff_type == self.DIFF_DELETE and len(patch.diffs) == 1 and
              patch.diffs[0][0] == self.DIFF_EQUAL and
              len(diff_text) > 2 * patch_size):
            # This is a large deletion.  Let it pass in one chunk.
            patch.length1 += len(diff_text)
            start1 += len(diff_text)
            empty = False
            patch.diffs.append((diff_type, diff_text))
            del bigpatch.diffs[0]
          else:
            # Deletion or equality.  Only take as much as we can stomach.
            diff_text = diff_text[:patch_size - patch.length1 -
                                  self.Patch_Margin]
            patch.length1 += len(diff_text)
            start1 += len(diff_text)
            if diff_type == self.DIFF_EQUAL:
              patch.length2 += len(diff_text)
              start2 += len(diff_text)
            else:
              empty = False

            patch.diffs.append((diff_type, diff_text))
            if diff_text == bigpatch.diffs[0][1]:
              del bigpatch.diffs[0]
            else:
              bigpatch.diffs[0] = (bigpatch.diffs[0][0],
                                   bigpatch.diffs[0][1][len(diff_text):])

        # Compute the head context for the next patch.
        precontext = self.diff_text2(patch.diffs)
        precontext = precontext[-self.Patch_Margin:]
        # Append the end context for this patch.
        postcontext = self.diff_text1(bigpatch.diffs)[:self.Patch_Margin]
        if postcontext:
          patch.length1 += len(postcontext)
          patch.length2 += len(postcontext)
          if len(patch.diffs) != 0 and patch.diffs[-1][0] == self.DIFF_EQUAL:
            patch.diffs[-1] = (self.DIFF_EQUAL, patch.diffs[-1][1] +
                               postcontext)
          else:
            patch.diffs.append((self.DIFF_EQUAL, postcontext))

        if not empty:
          x += 1
          patches.insert(x, patch)

  def patch_toText(self, patches):
    """Take a list of patches and return a textual representation.

    Args:
      patches: Array of Patch objects.

    Returns:
      Text representation of patches.
    """
    text = []
    for patch in patches:
      text.append(str(patch))
    return "".join(text)

  def patch_fromText(self, textline):
    """Parse a textual representation of patches and return a list of patch
    objects.

    Args:
      textline: Text representation of patches.

    Returns:
      Array of Patch objects.

    Raises:
      ValueError: If invalid input.
    """
    patches = []
    if not textline:
      return patches
    text = textline.split('\n')
    while len(text) != 0:
      m = re.match("^@@ -(\d+),?(\d*) \+(\d+),?(\d*) @@$", text[0])
      if not m:
        raise ValueError("Invalid patch string: " + text[0])
      patch = patch_obj()
      patches.append(patch)
      patch.start1 = int(m.group(1))
      if m.group(2) == '':
        patch.start1 -= 1
        patch.length1 = 1
      elif m.group(2) == '0':
        patch.length1 = 0
      else:
        patch.start1 -= 1
        patch.length1 = int(m.group(2))

      patch.start2 = int(m.group(3))
      if m.group(4) == '':
        patch.start2 -= 1
        patch.length2 = 1
      elif m.group(4) == '0':
        patch.length2 = 0
      else:
        patch.start2 -= 1
        patch.length2 = int(m.group(4))

      del text[0]

      while len(text) != 0:
        if text[0]:
          sign = text[0][0]
        else:
          sign = ''
        line = urllib.parse.unquote(text[0][1:])
        if sign == '+':
          # Insertion.
          patch.diffs.append((self.DIFF_INSERT, line))
        elif sign == '-':
          # Deletion.
          patch.diffs.append((self.DIFF_DELETE, line))
        elif sign == ' ':
          # Minor equality.
          patch.diffs.append((self.DIFF_EQUAL, line))
        elif sign == '@':
          # Start of next patch.
          break
        elif sign == '':
          # Blank line?  Whatever.
          pass
        else:
          # WTF?
          raise ValueError("Invalid patch mode: '%s'\n%s" % (sign, line))
        del text[0]
    return patches


class patch_obj:
  """Class representing one patch operation.
  """

  def __init__(self):
    """Initializes with an empty list of diffs.
    """
    self.diffs = []
    self.start1 = None
    self.start2 = None
    self.length1 = 0
    self.length2 = 0

  def __str__(self):
    """Emmulate GNU diff's format.
    Header: @@ -382,8 +481,9 @@
    Indicies are printed as 1-based, not 0-based.

    Returns:
      The GNU diff string.
    """
    if self.length1 == 0:
      coords1 = str(self.start1) + ",0"
    elif self.length1 == 1:
      coords1 = str(self.start1 + 1)
    else:
      coords1 = str(self.start1 + 1) + "," + str(self.length1)
    if self.length2 == 0:
      coords2 = str(self.start2) + ",0"
    elif self.length2 == 1:
      coords2 = str(self.start2 + 1)
    else:
      coords2 = str(self.start2 + 1) + "," + str(self.length2)
    text = ["@@ -", coords1, " +", coords2, " @@\n"]
    # Escape the body of the patch with %xx notation.
    for (op, data) in self.diffs:
      if op == diff_match_patch.DIFF_INSERT:
        text.append("+")
      elif op == diff_match_patch.DIFF_DELETE:
        text.append("-")
      elif op == diff_match_patch.DIFF_EQUAL:
        text.append(" ")
      # High ascii will raise UnicodeDecodeError.  Use Unicode instead.
      data = data.encode("utf-8")
      text.append(urllib.parse.quote(data, "!~*'();/?:@&=+$,# ") + "\n")
    return "".join(text)

########NEW FILE########
__FILENAME__ = test
import unittest
import cssbeautifier


class CSSBeautifierTest(unittest.TestCase):

    def resetOptions(self):
      self.options = cssbeautifier.default_options()
      self.options.indent_size = 1
      self.options.indent_char = '\t'
      self.options.selector_separator_newline = True
      self.options.end_with_newline = True

    def testBasics(self):
        self.resetOptions()
        t = self.decodesto

        t("", "\n")
        t(".tabs{}", ".tabs {}\n")
        t(".tabs{color:red}", ".tabs {\n\tcolor: red\n}\n")
        t(".tabs{color:rgb(255, 255, 0)}", ".tabs {\n\tcolor: rgb(255, 255, 0)\n}\n")
        t(".tabs{background:url('back.jpg')}", ".tabs {\n\tbackground: url('back.jpg')\n}\n")
        t("#bla, #foo{color:red}", "#bla,\n#foo {\n\tcolor: red\n}\n")
        t("@media print {.tab{}}", "@media print {\n\t.tab {}\n}\n")


    def testComments(self):
        self.resetOptions()
        t = self.decodesto

        t("/* test */", "/* test */\n\n")
        t(".tabs{/* test */}", ".tabs {\n\t/* test */\n}\n")
        t("/* header */.tabs {}", "/* header */\n\n.tabs {}\n")

        #single line comment support (less/sass)
        t(".tabs{\n// comment\nwidth:10px;\n}", ".tabs {\n\t// comment\n\twidth: 10px;\n}\n")
        t(".tabs{// comment\nwidth:10px;\n}", ".tabs {\n\t// comment\n\twidth: 10px;\n}\n")
        t("//comment\n.tabs{width:10px;}", "//comment\n.tabs {\n\twidth: 10px;\n}\n")
        t(".tabs{//comment\n//2nd single line comment\nwidth:10px;}", ".tabs {\n\t//comment\n\t//2nd single line comment\n\twidth: 10px;\n}\n")
        t(".tabs{width:10px;//end of line comment\n}", ".tabs {\n\twidth: 10px;//end of line comment\n}\n")
        t(".tabs{width:10px;//end of line comment\nheight:10px;}", ".tabs {\n\twidth: 10px;//end of line comment\n\theight: 10px;\n}\n")
        t(".tabs{width:10px;//end of line comment\nheight:10px;//another\n}", ".tabs {\n\twidth: 10px;//end of line comment\n\theight: 10px;//another\n}\n")


    def testSeperateSelectors(self):
        self.resetOptions()
        t = self.decodesto

        t("#bla, #foo{color:red}", "#bla,\n#foo {\n\tcolor: red\n}\n")
        t("a, img {padding: 0.2px}", "a,\nimg {\n\tpadding: 0.2px\n}\n")


    def testOptions(self):
        self.resetOptions()
        self.options.indent_size = 2
        self.options.indent_char = ' '
        self.options.selector_separator_newline = False
        t = self.decodesto

        t("#bla, #foo{color:green}", "#bla, #foo {\n  color: green\n}\n")
        t("@media print {.tab{}}", "@media print {\n  .tab {}\n}\n")
        t("#bla, #foo{color:black}", "#bla, #foo {\n  color: black\n}\n")

    def decodesto(self, input, expectation=None):
        self.assertEqual(
            cssbeautifier.beautify(input, self.options), expectation or input)

if __name__ == '__main__':
    unittest.main()

########NEW FILE########
__FILENAME__ = __version__
__version__ = '1.0.0'

########NEW FILE########
__FILENAME__ = testindentation
import re
import unittest
import jsbeautifier

class TestJSBeautifierIndentation(unittest.TestCase):
    def test_tabs(self):
        test_fragment = self.decodesto

        self.options.indent_with_tabs = 1;
        test_fragment('{tabs()}', "{\n\ttabs()\n}");

    def test_function_indent(self):
        test_fragment = self.decodesto

        self.options.indent_with_tabs = 1;
        self.options.keep_function_indentation = 1;
        test_fragment('var foo = function(){ bar() }();', "var foo = function() {\n\tbar()\n}();");

        self.options.tabs = 1;
        self.options.keep_function_indentation = 0;
        test_fragment('var foo = function(){ baz() }();', "var foo = function() {\n\tbaz()\n}();");

    def decodesto(self, input, expectation=None):
        self.assertEqual(
            jsbeautifier.beautify(input, self.options), expectation or input)

    @classmethod
    def setUpClass(cls):
        options = jsbeautifier.default_options()
        options.indent_size = 4
        options.indent_char = ' '
        options.preserve_newlines = True
        options.jslint_happy = False
        options.keep_array_indentation = False
        options.brace_style = 'collapse'
        options.indent_level = 0

        cls.options = options
        cls.wrapregex = re.compile('^(.+)$', re.MULTILINE)


if __name__ == '__main__':
    unittest.main()

########NEW FILE########
__FILENAME__ = testjsbeautifier
#!/usr/bin/env python
# -*- coding: utf-8 -*-

import re
import unittest
import jsbeautifier
import six

class TestJSBeautifier(unittest.TestCase):
    def test_unescape(self):
        # Test cases contributed by <chrisjshull on GitHub.com>
        test_fragment = self.decodesto
        bt = self.bt

        bt('"\\\\s"'); # == "\\s" in the js source
        bt("'\\\\s'"); # == '\\s' in the js source
        bt("'\\\\\\s'"); # == '\\\s' in the js source
        bt("'\\s'"); # == '\s' in the js source
        bt('"•"');
        bt('"—"');
        bt('"\\x41\\x42\\x43\\x01"', '"\\x41\\x42\\x43\\x01"');
        bt('"\\u2022"', '"\\u2022"');
        bt('a = /\s+/')
        #bt('a = /\\x41/','a = /A/')
        bt('"\\u2022";a = /\s+/;"\\x41\\x42\\x43\\x01".match(/\\x41/);','"\\u2022";\na = /\s+/;\n"\\x41\\x42\\x43\\x01".match(/\\x41/);')
        bt('"\\x22\\x27",\'\\x22\\x27\',"\\x5c",\'\\x5c\',"\\xff and \\xzz","unicode \\u0000 \\u0022 \\u0027 \\u005c \\uffff \\uzzzz"', '"\\x22\\x27", \'\\x22\\x27\', "\\x5c", \'\\x5c\', "\\xff and \\xzz", "unicode \\u0000 \\u0022 \\u0027 \\u005c \\uffff \\uzzzz"');

        self.options.unescape_strings = True

        bt('"\\x41\\x42\\x43\\x01"', '"ABC\\x01"');
        bt('"\\u2022"', '"\\u2022"');
        bt('a = /\s+/')
        bt('"\\u2022";a = /\s+/;"\\x41\\x42\\x43\\x01".match(/\\x41/);','"\\u2022";\na = /\s+/;\n"ABC\\x01".match(/\\x41/);')
        bt('"\\x22\\x27",\'\\x22\\x27\',"\\x5c",\'\\x5c\',"\\xff and \\xzz","unicode \\u0000 \\u0022 \\u0027 \\u005c \\uffff \\uzzzz"', '"\\"\'", \'"\\\'\', "\\\\", \'\\\\\', "\\xff and \\xzz", "unicode \\u0000 \\" \' \\\\ \\uffff \\uzzzz"');

        self.options.unescape_strings = False

    def test_beautifier(self):
        test_fragment = self.decodesto
        bt = self.bt

        # unicode support
        bt('var ' + six.unichr(3232) + '_' + six.unichr(3232) + ' = "hi";');
        bt('var ' + six.unichr(228) + 'x = {\n    ' + six.unichr(228) + 'rgerlich: true\n};');

        bt('');
        bt('return .5');
        test_fragment('    return .5');
        bt('a        =          1', 'a = 1');
        bt('a=1', 'a = 1');
        bt("a();\n\nb();", "a();\n\nb();");
        bt('var a = 1 var b = 2', "var a = 1\nvar b = 2");
        bt('var a=1, b=c[d], e=6;', 'var a = 1,\n    b = c[d],\n    e = 6;');
        bt('let a = 1 let b = 2', "let a = 1\nlet b = 2");
        bt('let a=1, b=c[d], e=6;', 'let a = 1,\n    b = c[d],\n    e = 6;');
        bt('const a = 1 const b = 2', "const a = 1\nconst b = 2");
        bt('const a=1, b=c[d], e=6;', 'const a = 1,\n    b = c[d],\n    e = 6;');
        bt('a = " 12345 "');
        bt("a = ' 12345 '");
        bt('if (a == 1) b = 2;', "if (a == 1) b = 2;");
        bt('if(1){2}else{3}', "if (1) {\n    2\n} else {\n    3\n}");
        bt('if(1||2);', 'if (1 || 2);');
        bt('(a==1)||(b==2)', '(a == 1) || (b == 2)');
        bt('var a = 1 if (2) 3;', "var a = 1\nif (2) 3;");
        bt('a = a + 1');
        bt('a = a == 1');
        bt('/12345[^678]*9+/.match(a)');
        bt('a /= 5');
        bt('a = 0.5 * 3');
        bt('a *= 10.55');
        bt('a < .5');
        bt('a <= .5');
        bt('a<.5', 'a < .5');
        bt('a<=.5', 'a <= .5');
        bt('a = 0xff;');
        bt('a=0xff+4', 'a = 0xff + 4');
        bt('a = [1, 2, 3, 4]');
        bt('F*(g/=f)*g+b', 'F * (g /= f) * g + b');
        bt('a.b({c:d})', 'a.b({\n    c: d\n})');
        bt('a.b\n(\n{\nc:\nd\n}\n)', 'a.b({\n    c: d\n})');
        bt('a.b({c:"d"})', 'a.b({\n    c: "d"\n})');
        bt('a.b\n(\n{\nc:\n"d"\n}\n)', 'a.b({\n    c: "d"\n})');
        bt('a=!b', 'a = !b');
        bt('a=!!b', 'a = !!b');
        bt('a?b:c', 'a ? b : c');
        bt('a?1:2', 'a ? 1 : 2');
        bt('a?(b):c', 'a ? (b) : c');
        bt('x={a:1,b:w=="foo"?x:y,c:z}', 'x = {\n    a: 1,\n    b: w == "foo" ? x : y,\n    c: z\n}');
        bt('x=a?b?c?d:e:f:g;', 'x = a ? b ? c ? d : e : f : g;');
        bt('x=a?b?c?d:{e1:1,e2:2}:f:g;', 'x = a ? b ? c ? d : {\n    e1: 1,\n    e2: 2\n} : f : g;');
        bt('function void(void) {}');
        bt('if(!a)foo();', 'if (!a) foo();');
        bt('a=~a', 'a = ~a');
        bt('a;/*comment*/b;', "a; /*comment*/\nb;");
        bt('a;/* comment */b;', "a; /* comment */\nb;");
        test_fragment('a;/*\ncomment\n*/b;', "a;\n/*\ncomment\n*/\nb;"); # simple comments don't get touched at all
        bt('a;/**\n* javadoc\n*/b;', "a;\n/**\n * javadoc\n */\nb;");
        test_fragment('a;/**\n\nno javadoc\n*/b;', "a;\n/**\n\nno javadoc\n*/\nb;");
        bt('a;/*\n* javadoc\n*/b;', "a;\n/*\n * javadoc\n */\nb;"); # comment blocks detected and reindented even w/o javadoc starter

        bt('if(a)break;', "if (a) break;");
        bt('if(a){break}', "if (a) {\n    break\n}");
        bt('if((a))foo();', 'if ((a)) foo();');
        bt('for(var i=0;;) a', 'for (var i = 0;;) a');
        bt('for(var i=0;;)\na', 'for (var i = 0;;)\n    a');
        bt('a++;', 'a++;');
        bt('for(;;i++)a()', 'for (;; i++) a()');
        bt('for(;;i++)\na()', 'for (;; i++)\n    a()');
        bt('for(;;++i)a', 'for (;; ++i) a');
        bt('return(1)', 'return (1)');
        bt('try{a();}catch(b){c();}finally{d();}', "try {\n    a();\n} catch (b) {\n    c();\n} finally {\n    d();\n}");
        bt('(xx)()'); # magic function call
        bt('a[1]()'); # another magic function call
        bt('if(a){b();}else if(c) foo();', "if (a) {\n    b();\n} else if (c) foo();");
        bt('switch(x) {case 0: case 1: a(); break; default: break}', "switch (x) {\n    case 0:\n    case 1:\n        a();\n        break;\n    default:\n        break\n}");
        bt('switch(x){case -1:break;case !y:break;}', 'switch (x) {\n    case -1:\n        break;\n    case !y:\n        break;\n}');
        bt('a !== b');
        bt('if (a) b(); else c();', "if (a) b();\nelse c();");
        bt("// comment\n(function something() {})"); # typical greasemonkey start
        bt("{\n\n    x();\n\n}"); # was: duplicating newlines
        bt('if (a in b) foo();');
        bt('var a, b;');
        # bt('var a, b');
        bt('{a:1, b:2}', "{\n    a: 1,\n    b: 2\n}");
        bt('a={1:[-1],2:[+1]}', 'a = {\n    1: [-1],\n    2: [+1]\n}');
        bt('var l = {\'a\':\'1\', \'b\':\'2\'}', "var l = {\n    'a': '1',\n    'b': '2'\n}");
        bt('if (template.user[n] in bk) foo();');
        bt('{{}/z/}', "{\n    {}\n    /z/\n}");
        bt('return 45', "return 45");
        bt('return this.prevObject ||\n\n    this.constructor(null);');
        bt('If[1]', "If[1]");
        bt('Then[1]', "Then[1]");
        bt('a = 1e10', "a = 1e10");
        bt('a = 1.3e10', "a = 1.3e10");
        bt('a = 1.3e-10', "a = 1.3e-10");
        bt('a = -1.3e-10', "a = -1.3e-10");
        bt('a = 1e-10', "a = 1e-10");
        bt('a = e - 10', "a = e - 10");
        bt('a = 11-10', "a = 11 - 10");
        bt("a = 1;// comment", "a = 1; // comment");
        bt("a = 1; // comment", "a = 1; // comment");
        bt("a = 1;\n // comment", "a = 1;\n// comment");
        bt('a = [-1, -1, -1]');

        # The exact formatting these should have is open for discussion, but they are at least reasonable
        bt('a = [ // comment\n    -1, -1, -1\n]');
        bt('var a = [ // comment\n    -1, -1, -1\n]');
        bt('a = [ // comment\n    -1, // comment\n    -1, -1\n]');
        bt('var a = [ // comment\n    -1, // comment\n    -1, -1\n]');

        bt('o = [{a:b},{c:d}]', 'o = [{\n    a: b\n}, {\n    c: d\n}]');

        bt("if (a) {\n    do();\n}"); # was: extra space appended

        bt("if (a) {\n// comment\n}else{\n// comment\n}", "if (a) {\n    // comment\n} else {\n    // comment\n}"); # if/else statement with empty body
        bt("if (a) {\n// comment\n// comment\n}", "if (a) {\n    // comment\n    // comment\n}"); # multiple comments indentation
        bt("if (a) b() else c();", "if (a) b()\nelse c();");
        bt("if (a) b() else if c() d();", "if (a) b()\nelse if c() d();");

        bt("{}");
        bt("{\n\n}");
        bt("do { a(); } while ( 1 );", "do {\n    a();\n} while (1);");
        bt("do {} while (1);");
        bt("do {\n} while (1);", "do {} while (1);");
        bt("do {\n\n} while (1);");
        bt("var a = x(a, b, c)");
        bt("delete x if (a) b();", "delete x\nif (a) b();");
        bt("delete x[x] if (a) b();", "delete x[x]\nif (a) b();");
        bt("for(var a=1,b=2)d", "for (var a = 1, b = 2) d");
        bt("for(var a=1,b=2,c=3) d", "for (var a = 1, b = 2, c = 3) d");
        bt("for(var a=1,b=2,c=3;d<3;d++)\ne", "for (var a = 1, b = 2, c = 3; d < 3; d++)\n    e");
        bt("function x(){(a||b).c()}", "function x() {\n    (a || b).c()\n}");
        bt("function x(){return - 1}", "function x() {\n    return -1\n}");
        bt("function x(){return ! a}", "function x() {\n    return !a\n}");
        bt("x => x", "x => x");
        bt("(x) => x", "(x) => x");
        bt("x => { x }", "x => {\n    x\n}");
        bt("(x) => { x }", "(x) => {\n    x\n}");

        # a common snippet in jQuery plugins
        bt("settings = $.extend({},defaults,settings);", "settings = $.extend({}, defaults, settings);");

        # reserved words used as property names
        bt("$http().then().finally().default()", "$http().then().finally().default()");
        bt("$http()\n.then()\n.finally()\n.default()", "$http()\n    .then()\n    .finally()\n    .default()");
        bt("$http().when.in.new.catch().throw()", "$http().when.in.new.catch().throw()");
        bt("$http()\n.when\n.in\n.new\n.catch()\n.throw()", "$http()\n    .when\n    .in\n    .new\n    .catch()\n    .throw()");

        bt('{xxx;}()', '{\n    xxx;\n}()');

        bt("a = 'a'\nb = 'b'");
        bt("a = /reg/exp");
        bt("a = /reg/");
        bt('/abc/.test()');
        bt('/abc/i.test()');
        bt("{/abc/i.test()}", "{\n    /abc/i.test()\n}");
        bt('var x=(a)/a;', 'var x = (a) / a;');

        bt('x != -1', 'x != -1');

        bt('for (; s-->0;)t', 'for (; s-- > 0;) t');
        bt('for (; s++>0;)u', 'for (; s++ > 0;) u');
        bt('a = s++>s--;', 'a = s++ > s--;');
        bt('a = s++>--s;', 'a = s++ > --s;');

        bt('{x=#1=[]}', '{\n    x = #1=[]\n}');
        bt('{a:#1={}}', '{\n    a: #1={}\n}');
        bt('{a:#1#}', '{\n    a: #1#\n}');

        test_fragment('"incomplete-string');
        test_fragment("'incomplete-string");
        test_fragment('/incomplete-regex');
        test_fragment('`incomplete-regex');

        test_fragment('{a:1},{a:2}', '{\n    a: 1\n}, {\n    a: 2\n}');
        test_fragment('var ary=[{a:1}, {a:2}];', 'var ary = [{\n    a: 1\n}, {\n    a: 2\n}];');

        test_fragment('{a:#1', '{\n    a: #1'); # incomplete
        test_fragment('{a:#', '{\n    a: #'); # incomplete

        test_fragment('}}}', '}\n}\n}'); # incomplete

        test_fragment('<!--\nvoid();\n// -->', '<!--\nvoid();\n// -->');

        test_fragment('a=/regexp', 'a = /regexp'); # incomplete regexp

        bt('{a:#1=[],b:#1#,c:#999999#}', '{\n    a: #1=[],\n    b: #1#,\n    c: #999999#\n}');

        bt("a = 1e+2");
        bt("a = 1e-2");
        bt("do{x()}while(a>1)", "do {\n    x()\n} while (a > 1)");

        bt("x(); /reg/exp.match(something)", "x();\n/reg/exp.match(something)");

        test_fragment("something();(", "something();\n(");
        test_fragment("#!she/bangs, she bangs\nf=1", "#!she/bangs, she bangs\n\nf = 1");
        test_fragment("#!she/bangs, she bangs\n\nf=1", "#!she/bangs, she bangs\n\nf = 1");
        test_fragment("#!she/bangs, she bangs\n\n/* comment */", "#!she/bangs, she bangs\n\n/* comment */");
        test_fragment("#!she/bangs, she bangs\n\n\n/* comment */", "#!she/bangs, she bangs\n\n\n/* comment */");
        test_fragment("#", "#");
        test_fragment("#!", "#!");

        bt("function namespace::something()");

        test_fragment("<!--\nsomething();\n-->", "<!--\nsomething();\n-->");
        test_fragment("<!--\nif(i<0){bla();}\n-->", "<!--\nif (i < 0) {\n    bla();\n}\n-->");

        bt('{foo();--bar;}', '{\n    foo();\n    --bar;\n}');
        bt('{foo();++bar;}', '{\n    foo();\n    ++bar;\n}');
        bt('{--bar;}', '{\n    --bar;\n}');
        bt('{++bar;}', '{\n    ++bar;\n}');

        # Handling of newlines around unary ++ and -- operators
        bt('{foo\n++bar;}', '{\n    foo\n    ++bar;\n}');
        bt('{foo++\nbar;}', '{\n    foo++\n    bar;\n}');

        # This is invalid, but harder to guard against. Issue #203.
        bt('{foo\n++\nbar;}', '{\n    foo\n    ++\n    bar;\n}');


        # regexps
        bt('a(/abc\\/\\/def/);b()', "a(/abc\\/\\/def/);\nb()");
        bt('a(/a[b\\[\\]c]d/);b()', "a(/a[b\\[\\]c]d/);\nb()");
        test_fragment('a(/a[b\\[', "a(/a[b\\["); # incomplete char class
        # allow unescaped / in char classes
        bt('a(/[a/b]/);b()', "a(/[a/b]/);\nb()");

        bt('function foo() {\n    return [\n        "one",\n        "two"\n    ];\n}');
        bt('a=[[1,2],[4,5],[7,8]]', "a = [\n    [1, 2],\n    [4, 5],\n    [7, 8]\n]");
        bt('a=[[1,2],[4,5],function(){},[7,8]]',
            "a = [\n    [1, 2],\n    [4, 5],\n    function() {},\n    [7, 8]\n]");
        bt('a=[[1,2],[4,5],function(){},function(){},[7,8]]',
            "a = [\n    [1, 2],\n    [4, 5],\n    function() {},\n    function() {},\n    [7, 8]\n]");
        bt('a=[[1,2],[4,5],function(){},[7,8]]',
            "a = [\n    [1, 2],\n    [4, 5],\n    function() {},\n    [7, 8]\n]");
        bt('a=[b,c,function(){},function(){},d]',
            "a = [b, c,\n    function() {},\n    function() {},\n    d\n]");
        bt('a=[a[1],b[4],c[d[7]]]', "a = [a[1], b[4], c[d[7]]]");
        bt('[1,2,[3,4,[5,6],7],8]', "[1, 2, [3, 4, [5, 6], 7], 8]");

        bt('[[["1","2"],["3","4"]],[["5","6","7"],["8","9","0"]],[["1","2","3"],["4","5","6","7"],["8","9","0"]]]',
            '[\n    [\n        ["1", "2"],\n        ["3", "4"]\n    ],\n    [\n        ["5", "6", "7"],\n        ["8", "9", "0"]\n    ],\n    [\n        ["1", "2", "3"],\n        ["4", "5", "6", "7"],\n        ["8", "9", "0"]\n    ]\n]');

        bt('{[x()[0]];indent;}', '{\n    [x()[0]];\n    indent;\n}');

        bt('return ++i', 'return ++i');
        bt('return !!x', 'return !!x');
        bt('return !x', 'return !x');
        bt('return [1,2]', 'return [1, 2]');
        bt('return;', 'return;');
        bt('return\nfunc', 'return\nfunc');
        bt('catch(e)', 'catch (e)');

        bt('var a=1,b={foo:2,bar:3},{baz:4,wham:5},c=4;',
            'var a = 1,\n    b = {\n        foo: 2,\n        bar: 3\n    },\n    {\n        baz: 4,\n        wham: 5\n    }, c = 4;');
        bt('var a=1,b={foo:2,bar:3},{baz:4,wham:5},\nc=4;',
            'var a = 1,\n    b = {\n        foo: 2,\n        bar: 3\n    },\n    {\n        baz: 4,\n        wham: 5\n    },\n    c = 4;');

        # inline comment
        bt('function x(/*int*/ start, /*string*/ foo)', 'function x( /*int*/ start, /*string*/ foo)');

        # javadoc comment
        bt('/**\n* foo\n*/', '/**\n * foo\n */');
        bt('{\n/**\n* foo\n*/\n}', '{\n    /**\n     * foo\n     */\n}');

        bt('var a,b,c=1,d,e,f=2;', 'var a, b, c = 1,\n    d, e, f = 2;');
        bt('var a,b,c=[],d,e,f=2;', 'var a, b, c = [],\n    d, e, f = 2;');
        bt('function() {\n    var a, b, c, d, e = [],\n        f;\n}');

        bt('do/regexp/;\nwhile(1);', 'do /regexp/;\nwhile (1);'); # hmmm

        bt('var a = a,\na;\nb = {\nb\n}', 'var a = a,\n    a;\nb = {\n    b\n}');

        bt('var a = a,\n    /* c */\n    b;');
        bt('var a = a,\n    // c\n    b;');

        bt('foo.("bar");'); # weird element referencing


        bt('if (a) a()\nelse b()\nnewline()');
        bt('if (a) a()\nnewline()');
        bt('a=typeof(x)', 'a = typeof(x)');

        bt('var a = function() {\n        return null;\n    },\n    b = false;');

        bt('var a = function() {\n    func1()\n}');
        bt('var a = function() {\n    func1()\n}\nvar b = function() {\n    func2()\n}');

        # code with and without semicolons
        bt( 'var whatever = require("whatever");\nfunction() {\n    a = 6;\n}',
            'var whatever = require("whatever");\n\nfunction() {\n    a = 6;\n}');
        bt( 'var whatever = require("whatever")\nfunction() {\n    a = 6\n}',
            'var whatever = require("whatever")\n\nfunction() {\n    a = 6\n}');


        self.options.jslint_happy = True

        bt('x();\n\nfunction(){}', 'x();\n\nfunction () {}');
        bt('function () {\n    var a, b, c, d, e = [],\n        f;\n}');
        bt('switch(x) {case 0: case 1: a(); break; default: break}',
            "switch (x) {\ncase 0:\ncase 1:\n    a();\n    break;\ndefault:\n    break\n}");
        bt('switch(x){case -1:break;case !y:break;}',
            'switch (x) {\ncase -1:\n    break;\ncase !y:\n    break;\n}');
        test_fragment("// comment 1\n(function()", "// comment 1\n(function ()"); # typical greasemonkey start
        bt('var o1=$.extend(a);function(){alert(x);}', 'var o1 = $.extend(a);\n\nfunction () {\n    alert(x);\n}');
        bt('a=typeof(x)', 'a = typeof (x)');

        self.options.jslint_happy = False

        bt('switch(x) {case 0: case 1: a(); break; default: break}',
            "switch (x) {\n    case 0:\n    case 1:\n        a();\n        break;\n    default:\n        break\n}");
        bt('switch(x){case -1:break;case !y:break;}',
            'switch (x) {\n    case -1:\n        break;\n    case !y:\n        break;\n}');
        test_fragment("// comment 2\n(function()", "// comment 2\n(function()"); # typical greasemonkey start
        bt("var a2, b2, c2, d2 = 0, c = function() {}, d = '';", "var a2, b2, c2, d2 = 0,\n    c = function() {},\n    d = '';");
        bt("var a2, b2, c2, d2 = 0, c = function() {},\nd = '';", "var a2, b2, c2, d2 = 0,\n    c = function() {},\n    d = '';");
        bt('var o2=$.extend(a);function(){alert(x);}', 'var o2 = $.extend(a);\n\nfunction() {\n    alert(x);\n}');

        bt('{"x":[{"a":1,"b":3},7,8,8,8,8,{"b":99},{"a":11}]}', '{\n    "x": [{\n            "a": 1,\n            "b": 3\n        },\n        7, 8, 8, 8, 8, {\n            "b": 99\n        }, {\n            "a": 11\n        }\n    ]\n}');

        bt('{"1":{"1a":"1b"},"2"}', '{\n    "1": {\n        "1a": "1b"\n    },\n    "2"\n}');
        bt('{a:{a:b},c}', '{\n    a: {\n        a: b\n    },\n    c\n}');

        bt('{[y[a]];keep_indent;}', '{\n    [y[a]];\n    keep_indent;\n}');

        bt('if (x) {y} else { if (x) {y}}', 'if (x) {\n    y\n} else {\n    if (x) {\n        y\n    }\n}');

        bt('if (foo) one()\ntwo()\nthree()');
        bt('if (1 + foo() && bar(baz()) / 2) one()\ntwo()\nthree()');
        bt('if (1 + foo() && bar(baz()) / 2) one();\ntwo();\nthree();');

        self.options.indent_size = 1;
        self.options.indent_char = ' ';
        bt('{ one_char() }', "{\n one_char()\n}");

        bt('var a,b=1,c=2', 'var a, b = 1,\n c = 2');

        self.options.indent_size = 4;
        self.options.indent_char = ' ';
        bt('{ one_char() }', "{\n    one_char()\n}");

        self.options.indent_size = 1;
        self.options.indent_char = "\t";
        bt('{ one_char() }', "{\n\tone_char()\n}");
        bt('x = a ? b : c; x;', 'x = a ? b : c;\nx;');

        #set to something else than it should change to, but with tabs on, should override
        self.options.indent_size = 5;
        self.options.indent_char = ' ';
        self.options.indent_with_tabs = True;

        bt('{ one_char() }', "{\n\tone_char()\n}");
        bt('x = a ? b : c; x;', 'x = a ? b : c;\nx;');

        self.options.indent_size = 4;
        self.options.indent_char = ' ';
        self.options.indent_with_tabs = False;

        self.options.preserve_newlines = False;
        bt('var\na=dont_preserve_newlines;', 'var a = dont_preserve_newlines;');

        # make sure the blank line between function definitions stays
        # even when preserve_newlines = False
        bt('function foo() {\n    return 1;\n}\n\nfunction foo() {\n    return 1;\n}');
        bt('function foo() {\n    return 1;\n}\nfunction foo() {\n    return 1;\n}',
        'function foo() {\n    return 1;\n}\n\nfunction foo() {\n    return 1;\n}'
        );
        bt('function foo() {\n    return 1;\n}\n\n\nfunction foo() {\n    return 1;\n}',
        'function foo() {\n    return 1;\n}\n\nfunction foo() {\n    return 1;\n}'
        );


        self.options.preserve_newlines = True;
        bt('var\na=do_preserve_newlines;', 'var\n    a = do_preserve_newlines;')
        bt('// a\n// b\n\n// c\n// d')
        bt('if (foo) //  comment\n{\n    bar();\n}')


        self.options.keep_array_indentation = False;
        bt("a = ['a', 'b', 'c',\n    'd', 'e', 'f']",
            "a = ['a', 'b', 'c',\n    'd', 'e', 'f'\n]");
        bt("a = ['a', 'b', 'c',\n    'd', 'e', 'f',\n        'g', 'h', 'i']",
            "a = ['a', 'b', 'c',\n    'd', 'e', 'f',\n    'g', 'h', 'i'\n]");
        bt("a = ['a', 'b', 'c',\n        'd', 'e', 'f',\n            'g', 'h', 'i']",
            "a = ['a', 'b', 'c',\n    'd', 'e', 'f',\n    'g', 'h', 'i'\n]");
        bt('var x = [{}\n]', 'var x = [{}]');
        bt('var x = [{foo:bar}\n]', 'var x = [{\n    foo: bar\n}]');
        bt("a = ['something',\n    'completely',\n    'different'];\nif (x);",
            "a = ['something',\n    'completely',\n    'different'\n];\nif (x);");
        bt("a = ['a','b','c']", "a = ['a', 'b', 'c']");
        bt("a = ['a',   'b','c']", "a = ['a', 'b', 'c']");
        bt("x = [{'a':0}]",
            "x = [{\n    'a': 0\n}]");
        bt('{a([[a1]], {b;});}',
            '{\n    a([\n        [a1]\n    ], {\n        b;\n    });\n}');
        bt("a();\n   [\n   ['sdfsdfsd'],\n        ['sdfsdfsdf']\n   ].toString();",
            "a();\n[\n    ['sdfsdfsd'],\n    ['sdfsdfsdf']\n].toString();");
        bt("a();\na = [\n   ['sdfsdfsd'],\n        ['sdfsdfsdf']\n   ].toString();",
            "a();\na = [\n    ['sdfsdfsd'],\n    ['sdfsdfsdf']\n].toString();");
        bt("function() {\n    Foo([\n        ['sdfsdfsd'],\n        ['sdfsdfsdf']\n    ]);\n}",
            "function() {\n    Foo([\n        ['sdfsdfsd'],\n        ['sdfsdfsdf']\n    ]);\n}");
        bt('function foo() {\n    return [\n        "one",\n        "two"\n    ];\n}');
        # 4 spaces per indent input, processed with 4-spaces per indent
        bt( "function foo() {\n" +
            "    return [\n" +
            "        {\n" +
            "            one: 'x',\n" +
            "            two: [\n" +
            "                {\n" +
            "                    id: 'a',\n" +
            "                    name: 'apple'\n" +
            "                }, {\n" +
            "                    id: 'b',\n" +
            "                    name: 'banana'\n" +
            "                }\n" +
            "            ]\n" +
            "        }\n" +
            "    ];\n" +
            "}",
            "function foo() {\n" +
            "    return [{\n" +
            "        one: 'x',\n" +
            "        two: [{\n" +
            "            id: 'a',\n" +
            "            name: 'apple'\n" +
            "        }, {\n" +
            "            id: 'b',\n" +
            "            name: 'banana'\n" +
            "        }]\n" +
            "    }];\n" +
            "}");
        # 3 spaces per indent input, processed with 4-spaces per indent
        bt( "function foo() {\n" +
            "   return [\n" +
            "      {\n" +
            "         one: 'x',\n" +
            "         two: [\n" +
            "            {\n" +
            "               id: 'a',\n" +
            "               name: 'apple'\n" +
            "            }, {\n" +
            "               id: 'b',\n" +
            "               name: 'banana'\n" +
            "            }\n" +
            "         ]\n" +
            "      }\n" +
            "   ];\n" +
            "}",
            "function foo() {\n" +
            "    return [{\n" +
            "        one: 'x',\n" +
            "        two: [{\n" +
            "            id: 'a',\n" +
            "            name: 'apple'\n" +
            "        }, {\n" +
            "            id: 'b',\n" +
            "            name: 'banana'\n" +
            "        }]\n" +
            "    }];\n" +
            "}");

        self.options.keep_array_indentation = True;
        bt("a = ['a', 'b', 'c',\n    'd', 'e', 'f']");
        bt("a = ['a', 'b', 'c',\n    'd', 'e', 'f',\n        'g', 'h', 'i']");
        bt("a = ['a', 'b', 'c',\n        'd', 'e', 'f',\n            'g', 'h', 'i']");
        bt('var x = [{}\n]', 'var x = [{}\n]');
        bt('var x = [{foo:bar}\n]', 'var x = [{\n        foo: bar\n    }\n]');
        bt("a = ['something',\n    'completely',\n    'different'];\nif (x);");
        bt("a = ['a','b','c']", "a = ['a', 'b', 'c']");
        bt("a = ['a',   'b','c']", "a = ['a', 'b', 'c']");
        bt("x = [{'a':0}]",
            "x = [{\n    'a': 0\n}]");
        bt('{a([[a1]], {b;});}',
            '{\n    a([[a1]], {\n        b;\n    });\n}');
        bt("a();\n   [\n   ['sdfsdfsd'],\n        ['sdfsdfsdf']\n   ].toString();",
            "a();\n   [\n   ['sdfsdfsd'],\n        ['sdfsdfsdf']\n   ].toString();");
        bt("a();\na = [\n   ['sdfsdfsd'],\n        ['sdfsdfsdf']\n   ].toString();",
            "a();\na = [\n   ['sdfsdfsd'],\n        ['sdfsdfsdf']\n   ].toString();");
        bt("function() {\n    Foo([\n        ['sdfsdfsd'],\n        ['sdfsdfsdf']\n    ]);\n}",
            "function() {\n    Foo([\n        ['sdfsdfsd'],\n        ['sdfsdfsdf']\n    ]);\n}");
        bt('function foo() {\n    return [\n        "one",\n        "two"\n    ];\n}');
        # 4 spaces per indent input, processed with 4-spaces per indent
        bt( "function foo() {\n" +
            "    return [\n" +
            "        {\n" +
            "            one: 'x',\n" +
            "            two: [\n" +
            "                {\n" +
            "                    id: 'a',\n" +
            "                    name: 'apple'\n" +
            "                }, {\n" +
            "                    id: 'b',\n" +
            "                    name: 'banana'\n" +
            "                }\n" +
            "            ]\n" +
            "        }\n" +
            "    ];\n" +
            "}");
        # 3 spaces per indent input, processed with 4-spaces per indent
        # Should be unchanged, but is not - #445
#         bt( "function foo() {\n" +
#             "   return [\n" +
#             "      {\n" +
#             "         one: 'x',\n" +
#             "         two: [\n" +
#             "            {\n" +
#             "               id: 'a',\n" +
#             "               name: 'apple'\n" +
#             "            }, {\n" +
#             "               id: 'b',\n" +
#             "               name: 'banana'\n" +
#             "            }\n" +
#             "         ]\n" +
#             "      }\n" +
#             "   ];\n" +
#             "}");

        self.options.keep_array_indentation = False;

        bt('a = //comment\n/regex/;');

        test_fragment('/*\n * X\n */');
        test_fragment('/*\r\n * X\r\n */', '/*\n * X\n */');

        bt('if (a)\n{\nb;\n}\nelse\n{\nc;\n}', 'if (a) {\n    b;\n} else {\n    c;\n}');

        bt('var a = new function();');
        test_fragment('new function');

        self.options.brace_style = 'expand';

        bt('//case 1\nif (a == 1)\n{}\n//case 2\nelse if (a == 2)\n{}');
        bt('if(1){2}else{3}', "if (1)\n{\n    2\n}\nelse\n{\n    3\n}");
        bt('try{a();}catch(b){c();}catch(d){}finally{e();}',
            "try\n{\n    a();\n}\ncatch (b)\n{\n    c();\n}\ncatch (d)\n{}\nfinally\n{\n    e();\n}");
        bt('if(a){b();}else if(c) foo();',
            "if (a)\n{\n    b();\n}\nelse if (c) foo();");
        bt('if(X)if(Y)a();else b();else c();',
            "if (X)\n    if (Y) a();\n    else b();\nelse c();");
        bt("if (a) {\n// comment\n}else{\n// comment\n}",
            "if (a)\n{\n    // comment\n}\nelse\n{\n    // comment\n}"); # if/else statement with empty body
        bt('if (x) {y} else { if (x) {y}}',
            'if (x)\n{\n    y\n}\nelse\n{\n    if (x)\n    {\n        y\n    }\n}');
        bt('if (a)\n{\nb;\n}\nelse\n{\nc;\n}',
            'if (a)\n{\n    b;\n}\nelse\n{\n    c;\n}');
        test_fragment('    /*\n* xx\n*/\n// xx\nif (foo) {\n    bar();\n}',
                      '    /*\n     * xx\n     */\n    // xx\n    if (foo)\n    {\n        bar();\n    }');
        bt('if (foo)\n{}\nelse /regex/.test();');
        bt('if (foo) /regex/.test();');
        bt('if (a)\n{\nb;\n}\nelse\n{\nc;\n}', 'if (a)\n{\n    b;\n}\nelse\n{\n    c;\n}');
        test_fragment('if (foo) {', 'if (foo)\n{');
        test_fragment('foo {', 'foo\n{');
        test_fragment('return {', 'return {'); # return needs the brace.
        test_fragment('return /* inline */ {', 'return /* inline */ {');
        # test_fragment('return\n{', 'return\n{'); # can't support this?, but that's an improbable and extreme case anyway.
        test_fragment('return;\n{', 'return;\n{');
        bt("throw {}");
        bt("throw {\n    foo;\n}");
        bt('var foo = {}');
        bt('if (foo) bar();\nelse break');
        bt('function x() {\n    foo();\n}zzz', 'function x()\n{\n    foo();\n}\nzzz');
        bt('a: do {} while (); xxx', 'a: do {} while ();\nxxx');
        bt('var a = new function();');
        bt('var a = new function() {};');
        bt('var a = new function()\n{};', 'var a = new function() {};');
        bt('var a = new function a()\n{};');
        bt('var a = new function a()\n    {},\n    b = new function b()\n    {};');
        test_fragment('new function');
        bt("foo({\n    'a': 1\n},\n10);",
            "foo(\n    {\n        'a': 1\n    },\n    10);");
        bt('(["foo","bar"]).each(function(i) {return i;});',
            '(["foo", "bar"]).each(function(i)\n{\n    return i;\n});');
        bt('(function(i) {return i;})();',
            '(function(i)\n{\n    return i;\n})();');
        bt( "test( /*Argument 1*/ {\n" +
            "    'Value1': '1'\n" +
            "}, /*Argument 2\n" +
            " */ {\n" +
            "    'Value2': '2'\n" +
            "});",
            # expected
            "test( /*Argument 1*/\n" +
            "    {\n" +
            "        'Value1': '1'\n" +
            "    },\n" +
            "    /*Argument 2\n" +
            "     */\n" +
            "    {\n" +
            "        'Value2': '2'\n" +
            "    });");
        bt( "test(\n" +
            "/*Argument 1*/ {\n" +
            "    'Value1': '1'\n" +
            "},\n" +
            "/*Argument 2\n" +
            " */ {\n" +
            "    'Value2': '2'\n" +
            "});",
            # expected
            "test(\n" +
            "    /*Argument 1*/\n" +
            "    {\n" +
            "        'Value1': '1'\n" +
            "    },\n" +
            "    /*Argument 2\n" +
            "     */\n" +
            "    {\n" +
            "        'Value2': '2'\n" +
            "    });");
        bt( "test( /*Argument 1*/\n" +
            "{\n" +
            "    'Value1': '1'\n" +
            "}, /*Argument 2\n" +
            " */\n" +
            "{\n" +
            "    'Value2': '2'\n" +
            "});",
            # expected
            "test( /*Argument 1*/\n" +
            "    {\n" +
            "        'Value1': '1'\n" +
            "    },\n" +
            "    /*Argument 2\n" +
            "     */\n" +
            "    {\n" +
            "        'Value2': '2'\n" +
            "    });");

        self.options.brace_style = 'collapse';

        bt('//case 1\nif (a == 1) {}\n//case 2\nelse if (a == 2) {}');
        bt('if(1){2}else{3}', "if (1) {\n    2\n} else {\n    3\n}");
        bt('try{a();}catch(b){c();}catch(d){}finally{e();}',
             "try {\n    a();\n} catch (b) {\n    c();\n} catch (d) {} finally {\n    e();\n}");
        bt('if(a){b();}else if(c) foo();',
            "if (a) {\n    b();\n} else if (c) foo();");
        bt("if (a) {\n// comment\n}else{\n// comment\n}",
            "if (a) {\n    // comment\n} else {\n    // comment\n}"); # if/else statement with empty body
        bt('if (x) {y} else { if (x) {y}}',
            'if (x) {\n    y\n} else {\n    if (x) {\n        y\n    }\n}');
        bt('if (a)\n{\nb;\n}\nelse\n{\nc;\n}',
            'if (a) {\n    b;\n} else {\n    c;\n}');
        test_fragment('    /*\n* xx\n*/\n// xx\nif (foo) {\n    bar();\n}',
                      '    /*\n     * xx\n     */\n    // xx\n    if (foo) {\n        bar();\n    }');
        bt('if (foo) {} else /regex/.test();');
        bt('if (foo) /regex/.test();');
        bt('if (a)\n{\nb;\n}\nelse\n{\nc;\n}', 'if (a) {\n    b;\n} else {\n    c;\n}');
        test_fragment('if (foo) {', 'if (foo) {');
        test_fragment('foo {', 'foo {');
        test_fragment('return {', 'return {'); # return needs the brace.
        test_fragment('return /* inline */ {', 'return /* inline */ {');
        # test_fragment('return\n{', 'return\n{'); # can't support this?, but that's an improbable and extreme case anyway.
        test_fragment('return;\n{', 'return; {');
        bt("throw {}");
        bt("throw {\n    foo;\n}");
        bt('var foo = {}');
        bt('if (foo) bar();\nelse break');
        bt('function x() {\n    foo();\n}zzz', 'function x() {\n    foo();\n}\nzzz');
        bt('a: do {} while (); xxx', 'a: do {} while ();\nxxx');
        bt('var a = new function();');
        bt('var a = new function() {};');
        bt('var a = new function a() {};');
        test_fragment('new function');
        bt("foo({\n    'a': 1\n},\n10);",
            "foo({\n        'a': 1\n    },\n    10);");
        bt('(["foo","bar"]).each(function(i) {return i;});',
            '(["foo", "bar"]).each(function(i) {\n    return i;\n});');
        bt('(function(i) {return i;})();',
            '(function(i) {\n    return i;\n})();');
        bt( "test( /*Argument 1*/ {\n" +
            "    'Value1': '1'\n" +
            "}, /*Argument 2\n" +
            " */ {\n" +
            "    'Value2': '2'\n" +
            "});",
            # expected
            "test( /*Argument 1*/ {\n" +
            "        'Value1': '1'\n" +
            "    },\n" +
            "    /*Argument 2\n" +
            "     */\n" +
            "    {\n" +
            "        'Value2': '2'\n" +
            "    });");
        bt( "test(\n" +
            "/*Argument 1*/ {\n" +
            "    'Value1': '1'\n" +
            "},\n" +
            "/*Argument 2\n" +
            " */ {\n" +
            "    'Value2': '2'\n" +
            "});",
            # expected
            "test(\n" +
            "    /*Argument 1*/\n" +
            "    {\n" +
            "        'Value1': '1'\n" +
            "    },\n" +
            "    /*Argument 2\n" +
            "     */\n" +
            "    {\n" +
            "        'Value2': '2'\n" +
            "    });");
        bt( "test( /*Argument 1*/\n" +
            "{\n" +
            "    'Value1': '1'\n" +
            "}, /*Argument 2\n" +
            " */\n" +
            "{\n" +
            "    'Value2': '2'\n" +
            "});",
            # expected
            "test( /*Argument 1*/ {\n" +
            "        'Value1': '1'\n" +
            "    },\n" +
            "    /*Argument 2\n" +
            "     */\n" +
            "    {\n" +
            "        'Value2': '2'\n" +
            "    });");

        self.options.brace_style = "end-expand";

        bt('//case 1\nif (a == 1) {}\n//case 2\nelse if (a == 2) {}');
        bt('if(1){2}else{3}', "if (1) {\n    2\n}\nelse {\n    3\n}");
        bt('try{a();}catch(b){c();}catch(d){}finally{e();}',
            "try {\n    a();\n}\ncatch (b) {\n    c();\n}\ncatch (d) {}\nfinally {\n    e();\n}");
        bt('if(a){b();}else if(c) foo();',
            "if (a) {\n    b();\n}\nelse if (c) foo();");
        bt("if (a) {\n// comment\n}else{\n// comment\n}",
            "if (a) {\n    // comment\n}\nelse {\n    // comment\n}"); # if/else statement with empty body
        bt('if (x) {y} else { if (x) {y}}',
            'if (x) {\n    y\n}\nelse {\n    if (x) {\n        y\n    }\n}');
        bt('if (a)\n{\nb;\n}\nelse\n{\nc;\n}',
            'if (a) {\n    b;\n}\nelse {\n    c;\n}');
        test_fragment('    /*\n* xx\n*/\n// xx\nif (foo) {\n    bar();\n}',
                      '    /*\n     * xx\n     */\n    // xx\n    if (foo) {\n        bar();\n    }');
        bt('if (foo) {}\nelse /regex/.test();');
        bt('if (foo) /regex/.test();');
        bt('if (a)\n{\nb;\n}\nelse\n{\nc;\n}', 'if (a) {\n    b;\n}\nelse {\n    c;\n}');
        test_fragment('if (foo) {', 'if (foo) {');
        test_fragment('foo {', 'foo {');
        test_fragment('return {', 'return {'); # return needs the brace.
        test_fragment('return /* inline */ {', 'return /* inline */ {');
        # test_fragment('return\n{', 'return\n{'); # can't support this?, but that's an improbable and extreme case anyway.
        test_fragment('return;\n{', 'return; {');
        bt("throw {}");
        bt("throw {\n    foo;\n}");
        bt('var foo = {}');
        bt('if (foo) bar();\nelse break');
        bt('function x() {\n    foo();\n}zzz', 'function x() {\n    foo();\n}\nzzz');
        bt('a: do {} while (); xxx', 'a: do {} while ();\nxxx');
        bt('var a = new function();');
        bt('var a = new function() {};');
        bt('var a = new function a() {};');
        test_fragment('new function');
        bt("foo({\n    'a': 1\n},\n10);",
            "foo({\n        'a': 1\n    },\n    10);");
        bt('(["foo","bar"]).each(function(i) {return i;});',
            '(["foo", "bar"]).each(function(i) {\n    return i;\n});');
        bt('(function(i) {return i;})();',
            '(function(i) {\n    return i;\n})();');
        bt( "test( /*Argument 1*/ {\n" +
            "    'Value1': '1'\n" +
            "}, /*Argument 2\n" +
            " */ {\n" +
            "    'Value2': '2'\n" +
            "});",
            # expected
            "test( /*Argument 1*/ {\n" +
            "        'Value1': '1'\n" +
            "    },\n" +
            "    /*Argument 2\n" +
            "     */\n" +
            "    {\n" +
            "        'Value2': '2'\n" +
            "    });");
        bt( "test(\n" +
            "/*Argument 1*/ {\n" +
            "    'Value1': '1'\n" +
            "},\n" +
            "/*Argument 2\n" +
            " */ {\n" +
            "    'Value2': '2'\n" +
            "});",
            # expected
            "test(\n" +
            "    /*Argument 1*/\n" +
            "    {\n" +
            "        'Value1': '1'\n" +
            "    },\n" +
            "    /*Argument 2\n" +
            "     */\n" +
            "    {\n" +
            "        'Value2': '2'\n" +
            "    });");
        bt( "test( /*Argument 1*/\n" +
            "{\n" +
            "    'Value1': '1'\n" +
            "}, /*Argument 2\n" +
            " */\n" +
            "{\n" +
            "    'Value2': '2'\n" +
            "});",
            # expected
            "test( /*Argument 1*/ {\n" +
            "        'Value1': '1'\n" +
            "    },\n" +
            "    /*Argument 2\n" +
            "     */\n" +
            "    {\n" +
            "        'Value2': '2'\n" +
            "    });");

        self.options.brace_style = 'collapse';

        bt('a = <?= external() ?> ;'); # not the most perfect thing in the world, but you're the weirdo beaufifying php mix-ins with javascript beautifier
        bt('a = <%= external() %> ;');

        test_fragment('roo = {\n    /*\n    ****\n      FOO\n    ****\n    */\n    BAR: 0\n};');
        test_fragment("if (zz) {\n    // ....\n}\n(function");

        self.options.preserve_newlines = True;
        bt('var a = 42; // foo\n\nvar b;')
        bt('var a = 42; // foo\n\n\nvar b;')
        bt("var a = 'foo' +\n    'bar';");
        bt("var a = \"foo\" +\n    \"bar\";");

        bt('"foo""bar""baz"', '"foo"\n"bar"\n"baz"')
        bt("'foo''bar''baz'", "'foo'\n'bar'\n'baz'")
        bt("{\n    get foo() {}\n}")
        bt("{\n    var a = get\n    foo();\n}")
        bt("{\n    set foo() {}\n}")
        bt("{\n    var a = set\n    foo();\n}")
        bt("var x = {\n    get function()\n}")
        bt("var x = {\n    set function()\n}")
        bt("var x = set\n\na() {}", "var x = set\n\n    a() {}");
        bt("var x = set\n\nfunction() {}", "var x = set\n\n    function() {}")

        bt('<!-- foo\nbar();\n-->')
        bt('<!-- dont crash')
        bt('for () /abc/.test()')
        bt('if (k) /aaa/m.test(v) && l();')
        bt('switch (true) {\n    case /swf/i.test(foo):\n        bar();\n}')
        bt('createdAt = {\n    type: Date,\n    default: Date.now\n}')
        bt('switch (createdAt) {\n    case a:\n        Date,\n    default:\n        Date.now\n}')

        bt('return function();')
        bt('var a = function();')
        bt('var a = 5 + function();')

        bt('{\n    foo // something\n    ,\n    bar // something\n    baz\n}')
        bt('function a(a) {} function b(b) {} function c(c) {}', 'function a(a) {}\n\nfunction b(b) {}\n\nfunction c(c) {}')


        bt('3.*7;', '3. * 7;')
        bt('import foo.*;', 'import foo.*;') # actionscript's import
        test_fragment('function f(a: a, b: b)') # actionscript
        bt('foo(a, function() {})');
        bt('foo(a, /regex/)');

        bt('/* foo */\n"x"');

        self.options.break_chained_methods = False
        self.options.preserve_newlines = False
        bt('foo\n.bar()\n.baz().cucumber(fat)', 'foo.bar().baz().cucumber(fat)');
        bt('foo\n.bar()\n.baz().cucumber(fat); foo.bar().baz().cucumber(fat)', 'foo.bar().baz().cucumber(fat);\nfoo.bar().baz().cucumber(fat)');
        bt('foo\n.bar()\n.baz().cucumber(fat)\n foo.bar().baz().cucumber(fat)', 'foo.bar().baz().cucumber(fat)\nfoo.bar().baz().cucumber(fat)');
        bt('this\n.something = foo.bar()\n.baz().cucumber(fat)', 'this.something = foo.bar().baz().cucumber(fat)');
        bt('this.something.xxx = foo.moo.bar()');
        bt('this\n.something\n.xxx = foo.moo\n.bar()', 'this.something.xxx = foo.moo.bar()');

        self.options.break_chained_methods = False
        self.options.preserve_newlines = True
        bt('foo\n.bar()\n.baz().cucumber(fat)', 'foo\n    .bar()\n    .baz().cucumber(fat)');
        bt('foo\n.bar()\n.baz().cucumber(fat); foo.bar().baz().cucumber(fat)', 'foo\n    .bar()\n    .baz().cucumber(fat);\nfoo.bar().baz().cucumber(fat)');
        bt('foo\n.bar()\n.baz().cucumber(fat)\n foo.bar().baz().cucumber(fat)', 'foo\n    .bar()\n    .baz().cucumber(fat)\nfoo.bar().baz().cucumber(fat)');
        bt('this\n.something = foo.bar()\n.baz().cucumber(fat)', 'this\n    .something = foo.bar()\n    .baz().cucumber(fat)');
        bt('this.something.xxx = foo.moo.bar()');
        bt('this\n.something\n.xxx = foo.moo\n.bar()', 'this\n    .something\n    .xxx = foo.moo\n    .bar()');

        self.options.break_chained_methods = True
        self.options.preserve_newlines = False
        bt('foo\n.bar()\n.baz().cucumber(fat)', 'foo.bar()\n    .baz()\n    .cucumber(fat)');
        bt('foo\n.bar()\n.baz().cucumber(fat); foo.bar().baz().cucumber(fat)', 'foo.bar()\n    .baz()\n    .cucumber(fat);\nfoo.bar()\n    .baz()\n    .cucumber(fat)');
        bt('foo\n.bar()\n.baz().cucumber(fat)\n foo.bar().baz().cucumber(fat)', 'foo.bar()\n    .baz()\n    .cucumber(fat)\nfoo.bar()\n    .baz()\n    .cucumber(fat)');
        bt('this\n.something = foo.bar()\n.baz().cucumber(fat)', 'this.something = foo.bar()\n    .baz()\n    .cucumber(fat)');
        bt('this.something.xxx = foo.moo.bar()');
        bt('this\n.something\n.xxx = foo.moo\n.bar()', 'this.something.xxx = foo.moo.bar()');

        self.options.break_chained_methods = True
        self.options.preserve_newlines = True
        bt('foo\n.bar()\n.baz().cucumber(fat)', 'foo\n    .bar()\n    .baz()\n    .cucumber(fat)');
        bt('foo\n.bar()\n.baz().cucumber(fat); foo.bar().baz().cucumber(fat)', 'foo\n    .bar()\n    .baz()\n    .cucumber(fat);\nfoo.bar()\n    .baz()\n    .cucumber(fat)');
        bt('foo\n.bar()\n.baz().cucumber(fat)\n foo.bar().baz().cucumber(fat)', 'foo\n    .bar()\n    .baz()\n    .cucumber(fat)\nfoo.bar()\n    .baz()\n    .cucumber(fat)');
        bt('this\n.something = foo.bar()\n.baz().cucumber(fat)', 'this\n    .something = foo.bar()\n    .baz()\n    .cucumber(fat)');
        bt('this.something.xxx = foo.moo.bar()');
        bt('this\n.something\n.xxx = foo.moo\n.bar()', 'this\n    .something\n    .xxx = foo.moo\n    .bar()');
        self.options.break_chained_methods = False
        self.options.preserve_newlines = False


        # Line wrap test intputs
        #..............---------1---------2---------3---------4---------5---------6---------7
        #..............1234567890123456789012345678901234567890123456789012345678901234567890
        wrap_input_1=('foo.bar().baz().cucumber((fat && "sassy") || (leans\n&& mean));\n' +
                      'Test_very_long_variable_name_this_should_never_wrap\n.but_this_can\n' +
                      'if (wraps_can_occur && inside_an_if_block) that_is_\n.okay();\n' +
                      'object_literal = {\n' +
                      '    property: first_token_should_never_wrap + but_this_can,\n' +
                      '    propertz: first_token_should_never_wrap + !but_this_can,\n' +
                      '    proper: "first_token_should_never_wrap" + "but_this_can"\n' +
                      '}')

        #..............---------1---------2---------3---------4---------5---------6---------7
        #..............1234567890123456789012345678901234567890123456789012345678901234567890
        wrap_input_2=('{\n' +
                      '    foo.bar().baz().cucumber((fat && "sassy") || (leans\n&& mean));\n' +
                      '    Test_very_long_variable_name_this_should_never_wrap\n.but_this_can\n' +
                      '    if (wraps_can_occur && inside_an_if_block) that_is_\n.okay();\n' +
                      '    object_literal = {\n' +
                      '        property: first_token_should_never_wrap + but_this_can,\n' +
                      '        propertz: first_token_should_never_wrap + !but_this_can,\n' +
                      '        proper: "first_token_should_never_wrap" + "but_this_can"\n' +
                      '    }' +
                      '}')

        self.options.preserve_newlines = False
        self.options.wrap_line_length = 0
        #..............---------1---------2---------3---------4---------5---------6---------7
        #..............1234567890123456789012345678901234567890123456789012345678901234567890
        test_fragment(wrap_input_1,
                      # expected #
                      'foo.bar().baz().cucumber((fat && "sassy") || (leans && mean));\n' +
                      'Test_very_long_variable_name_this_should_never_wrap.but_this_can\n' +
                      'if (wraps_can_occur && inside_an_if_block) that_is_.okay();\n' +
                      'object_literal = {\n' +
                      '    property: first_token_should_never_wrap + but_this_can,\n' +
                      '    propertz: first_token_should_never_wrap + !but_this_can,\n' +
                      '    proper: "first_token_should_never_wrap" + "but_this_can"\n' +
                      '}');

        self.options.wrap_line_length = 70
        #..............---------1---------2---------3---------4---------5---------6---------7
        #..............1234567890123456789012345678901234567890123456789012345678901234567890
        test_fragment(wrap_input_1,
                      # expected #
                      'foo.bar().baz().cucumber((fat && "sassy") || (leans && mean));\n' +
                      'Test_very_long_variable_name_this_should_never_wrap.but_this_can\n' +
                      'if (wraps_can_occur && inside_an_if_block) that_is_.okay();\n' +
                      'object_literal = {\n' +
                      '    property: first_token_should_never_wrap + but_this_can,\n' +
                      '    propertz: first_token_should_never_wrap + !but_this_can,\n' +
                      '    proper: "first_token_should_never_wrap" + "but_this_can"\n' +
                      '}');

        self.options.wrap_line_length = 40
        #..............---------1---------2---------3---------4---------5---------6---------7
        #..............1234567890123456789012345678901234567890123456789012345678901234567890
        test_fragment(wrap_input_1,
                      # expected #
                      'foo.bar().baz().cucumber((fat &&\n' +
                      '    "sassy") || (leans && mean));\n' +
                      'Test_very_long_variable_name_this_should_never_wrap\n' +
                      '    .but_this_can\n' +
                      'if (wraps_can_occur &&\n' +
                      '    inside_an_if_block) that_is_.okay();\n' +
                      'object_literal = {\n' +
                      '    property: first_token_should_never_wrap +\n' +
                      '        but_this_can,\n' +
                      '    propertz: first_token_should_never_wrap +\n' +
                      '        !but_this_can,\n' +
                      '    proper: "first_token_should_never_wrap" +\n' +
                      '        "but_this_can"\n' +
                      '}');

        self.options.wrap_line_length = 41
        # NOTE: wrap is only best effort - line continues until next wrap point is found.
        #..............---------1---------2---------3---------4---------5---------6---------7
        #..............1234567890123456789012345678901234567890123456789012345678901234567890
        test_fragment(wrap_input_1,
                      # expected #
                      'foo.bar().baz().cucumber((fat && "sassy") ||\n' +
                      '    (leans && mean));\n' +
                      'Test_very_long_variable_name_this_should_never_wrap\n' +
                      '    .but_this_can\n' +
                      'if (wraps_can_occur &&\n' +
                      '    inside_an_if_block) that_is_.okay();\n' +
                      'object_literal = {\n' +
                      '    property: first_token_should_never_wrap +\n' +
                      '        but_this_can,\n' +
                      '    propertz: first_token_should_never_wrap +\n' +
                      '        !but_this_can,\n' +
                      '    proper: "first_token_should_never_wrap" +\n' +
                      '        "but_this_can"\n' +
                      '}');


        self.options.wrap_line_length = 45
        # NOTE: wrap is only best effort - line continues until next wrap point is found.
        #..............---------1---------2---------3---------4---------5---------6---------7
        #..............1234567890123456789012345678901234567890123456789012345678901234567890
        test_fragment(wrap_input_2,
                      # expected #
                      '{\n' +
                      '    foo.bar().baz().cucumber((fat && "sassy") ||\n' +
                      '        (leans && mean));\n' +
                      '    Test_very_long_variable_name_this_should_never_wrap\n' +
                      '        .but_this_can\n' +
                      '    if (wraps_can_occur &&\n' +
                      '        inside_an_if_block) that_is_.okay();\n' +
                      '    object_literal = {\n' +
                      '        property: first_token_should_never_wrap +\n' +
                      '            but_this_can,\n' +
                      '        propertz: first_token_should_never_wrap +\n' +
                      '            !but_this_can,\n' +
                      '        proper: "first_token_should_never_wrap" +\n' +
                      '            "but_this_can"\n' +
                      '    }\n'+
                      '}');

        self.options.preserve_newlines = True
        self.options.wrap_line_length = 0
        #..............---------1---------2---------3---------4---------5---------6---------7
        #..............1234567890123456789012345678901234567890123456789012345678901234567890
        test_fragment(wrap_input_1,
                      # expected #
                      'foo.bar().baz().cucumber((fat && "sassy") || (leans && mean));\n' +
                      'Test_very_long_variable_name_this_should_never_wrap\n' +
                      '    .but_this_can\n' +
                      'if (wraps_can_occur && inside_an_if_block) that_is_\n' +
                      '    .okay();\n' +
                      'object_literal = {\n' +
                      '    property: first_token_should_never_wrap + but_this_can,\n' +
                      '    propertz: first_token_should_never_wrap + !but_this_can,\n' +
                      '    proper: "first_token_should_never_wrap" + "but_this_can"\n' +
                      '}');


        self.options.wrap_line_length = 70
        #..............---------1---------2---------3---------4---------5---------6---------7
        #..............1234567890123456789012345678901234567890123456789012345678901234567890
        test_fragment(wrap_input_1,
                      # expected #
                      'foo.bar().baz().cucumber((fat && "sassy") || (leans && mean));\n' +
                      'Test_very_long_variable_name_this_should_never_wrap\n' +
                      '    .but_this_can\n' +
                      'if (wraps_can_occur && inside_an_if_block) that_is_\n' +
                      '    .okay();\n' +
                      'object_literal = {\n' +
                      '    property: first_token_should_never_wrap + but_this_can,\n' +
                      '    propertz: first_token_should_never_wrap + !but_this_can,\n' +
                      '    proper: "first_token_should_never_wrap" + "but_this_can"\n' +
                      '}');


        self.options.wrap_line_length = 40
        #..............---------1---------2---------3---------4---------5---------6---------7
        #..............1234567890123456789012345678901234567890123456789012345678901234567890
        test_fragment(wrap_input_1,
                      # expected #
                      'foo.bar().baz().cucumber((fat &&\n' +
                      '    "sassy") || (leans && mean));\n' +
                      'Test_very_long_variable_name_this_should_never_wrap\n' +
                      '    .but_this_can\n' +
                      'if (wraps_can_occur &&\n' +
                      '    inside_an_if_block) that_is_\n' +
                      '    .okay();\n' +
                      'object_literal = {\n' +
                      '    property: first_token_should_never_wrap +\n' +
                      '        but_this_can,\n' +
                      '    propertz: first_token_should_never_wrap +\n' +
                      '        !but_this_can,\n' +
                      '    proper: "first_token_should_never_wrap" +\n' +
                      '        "but_this_can"\n' +
                      '}');

        self.options.wrap_line_length = 41
        # NOTE: wrap is only best effort - line continues until next wrap point is found.
        #..............---------1---------2---------3---------4---------5---------6---------7
        #..............1234567890123456789012345678901234567890123456789012345678901234567890
        test_fragment(wrap_input_1,
                      # expected #
                      'foo.bar().baz().cucumber((fat && "sassy") ||\n' +
                      '    (leans && mean));\n' +
                      'Test_very_long_variable_name_this_should_never_wrap\n' +
                      '    .but_this_can\n' +
                      'if (wraps_can_occur &&\n' +
                      '    inside_an_if_block) that_is_\n' +
                      '    .okay();\n' +
                      'object_literal = {\n' +
                      '    property: first_token_should_never_wrap +\n' +
                      '        but_this_can,\n' +
                      '    propertz: first_token_should_never_wrap +\n' +
                      '        !but_this_can,\n' +
                      '    proper: "first_token_should_never_wrap" +\n' +
                      '        "but_this_can"\n' +
                      '}');

        self.options.wrap_line_length = 45
        # NOTE: wrap is only best effort - line continues until next wrap point is found.
        #..............---------1---------2---------3---------4---------5---------6---------7
        #..............1234567890123456789012345678901234567890123456789012345678901234567890
        test_fragment(wrap_input_2,
                      # expected #
                      '{\n' +
                      '    foo.bar().baz().cucumber((fat && "sassy") ||\n' +
                      '        (leans && mean));\n' +
                      '    Test_very_long_variable_name_this_should_never_wrap\n' +
                      '        .but_this_can\n' +
                      '    if (wraps_can_occur &&\n' +
                      '        inside_an_if_block) that_is_\n' +
                      '        .okay();\n' +
                      '    object_literal = {\n' +
                      '        property: first_token_should_never_wrap +\n' +
                      '            but_this_can,\n' +
                      '        propertz: first_token_should_never_wrap +\n' +
                      '            !but_this_can,\n' +
                      '        proper: "first_token_should_never_wrap" +\n' +
                      '            "but_this_can"\n' +
                      '    }\n'+
                      '}');

        self.options.wrap_line_length = 0

        self.options.preserve_newlines = False
        bt('if (foo) // comment\n    bar();');
        bt('if (foo) // comment\n    (bar());');
        bt('if (foo) // comment\n    (bar());');
        bt('if (foo) // comment\n    /asdf/;');
        bt('this.oa = new OAuth(\n' +
           '    _requestToken,\n' +
           '    _accessToken,\n' +
           '    consumer_key\n' +
           ');',
           'this.oa = new OAuth(_requestToken, _accessToken, consumer_key);');
        bt('foo = {\n    x: y, // #44\n    w: z // #44\n}');
        bt('switch (x) {\n    case "a":\n        // comment on newline\n        break;\n    case "b": // comment on same line\n        break;\n}');

        bt('if (true ||\n!true) return;', 'if (true || !true) return;');

        # these aren't ready yet.
        #bt('if (foo) // comment\n    bar() /*i*/ + baz() /*j\n*/ + asdf();');
        bt('if\n(foo)\nif\n(bar)\nif\n(baz)\nwhee();\na();',
            'if (foo)\n    if (bar)\n        if (baz) whee();\na();');
        bt('if\n(foo)\nif\n(bar)\nif\n(baz)\nwhee();\nelse\na();',
            'if (foo)\n    if (bar)\n        if (baz) whee();\n        else a();');
        bt('if (foo)\nbar();\nelse\ncar();',
            'if (foo) bar();\nelse car();');

        bt('if (foo) if (bar) if (baz);\na();',
            'if (foo)\n    if (bar)\n        if (baz);\na();');
        bt('if (foo) if (bar) if (baz) whee();\na();',
            'if (foo)\n    if (bar)\n        if (baz) whee();\na();');
        bt('if (foo) a()\nif (bar) if (baz) whee();\na();',
            'if (foo) a()\nif (bar)\n    if (baz) whee();\na();');
        bt('if (foo);\nif (bar) if (baz) whee();\na();',
            'if (foo);\nif (bar)\n    if (baz) whee();\na();');
        bt('if (options)\n' +
           '    for (var p in options)\n' +
           '        this[p] = options[p];',
           'if (options)\n'+
           '    for (var p in options) this[p] = options[p];');
        bt('if (options) for (var p in options) this[p] = options[p];',
           'if (options)\n    for (var p in options) this[p] = options[p];');

        bt('if (options) do q(); while (b());',
           'if (options)\n    do q(); while (b());');
        bt('if (options) while (b()) q();',
           'if (options)\n    while (b()) q();');
        bt('if (options) do while (b()) q(); while (a());',
           'if (options)\n    do\n        while (b()) q(); while (a());');

        bt('function f(a, b, c,\nd, e) {}',
            'function f(a, b, c, d, e) {}');

        bt('function f(a,b) {if(a) b()}function g(a,b) {if(!a) b()}',
            'function f(a, b) {\n    if (a) b()\n}\n\nfunction g(a, b) {\n    if (!a) b()\n}');
        bt('function f(a,b) {if(a) b()}\n\n\n\nfunction g(a,b) {if(!a) b()}',
            'function f(a, b) {\n    if (a) b()\n}\n\nfunction g(a, b) {\n    if (!a) b()\n}');
        # This is not valid syntax, but still want to behave reasonably and not side-effect
        bt('(if(a) b())(if(a) b())',
            '(\n    if (a) b())(\n    if (a) b())');
        bt('(if(a) b())\n\n\n(if(a) b())',
            '(\n    if (a) b())\n(\n    if (a) b())');

        # space between functions
        bt('/*\n * foo\n */\nfunction foo() {}');
        bt('// a nice function\nfunction foo() {}');
        bt('function foo() {}\nfunction foo() {}',
            'function foo() {}\n\nfunction foo() {}'
        );



        bt("if\n(a)\nb();", "if (a) b();");
        bt('var a =\nfoo', 'var a = foo');
        bt('var a = {\n"a":1,\n"b":2}', "var a = {\n    \"a\": 1,\n    \"b\": 2\n}");
        bt("var a = {\n'a':1,\n'b':2}", "var a = {\n    'a': 1,\n    'b': 2\n}");
        bt('var a = /*i*/ "b";');
        bt('var a = /*i*/\n"b";', 'var a = /*i*/ "b";');
        bt('var a = /*i*/\nb;', 'var a = /*i*/ b;');
        bt('{\n\n\n"x"\n}', '{\n    "x"\n}');
        bt('if(a &&\nb\n||\nc\n||d\n&&\ne) e = f', 'if (a && b || c || d && e) e = f');
        bt('if(a &&\n(b\n||\nc\n||d)\n&&\ne) e = f', 'if (a && (b || c || d) && e) e = f');
        test_fragment('\n\n"x"', '"x"');
        bt('a = 1;\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\nb = 2;',
            'a = 1;\nb = 2;');


        self.options.preserve_newlines = True
        bt('if (foo) // comment\n    bar();');
        bt('if (foo) // comment\n    (bar());');
        bt('if (foo) // comment\n    (bar());');
        bt('if (foo) // comment\n    /asdf/;');
        bt('this.oa = new OAuth(\n' +
           '    _requestToken,\n' +
           '    _accessToken,\n' +
           '    consumer_key\n' +
           ');');
        bt('foo = {\n    x: y, // #44\n    w: z // #44\n}');
        bt('switch (x) {\n    case "a":\n        // comment on newline\n        break;\n    case "b": // comment on same line\n        break;\n}');

        bt('if (true ||\n!true) return;', 'if (true ||\n    !true) return;');

        # these aren't ready yet.
        # bt('if (foo) // comment\n    bar() /*i*/ + baz() /*j\n*/ + asdf();');
        bt('if\n(foo)\nif\n(bar)\nif\n(baz)\nwhee();\na();',
            'if (foo)\n    if (bar)\n        if (baz)\n            whee();\na();');
        bt('if\n(foo)\nif\n(bar)\nif\n(baz)\nwhee();\nelse\na();',
            'if (foo)\n    if (bar)\n        if (baz)\n            whee();\n        else\n            a();');
        bt('if (foo) bar();\nelse\ncar();',
            'if (foo) bar();\nelse\n    car();');

        bt('if (foo) if (bar) if (baz);\na();',
            'if (foo)\n    if (bar)\n        if (baz);\na();');
        bt('if (foo) if (bar) if (baz) whee();\na();',
            'if (foo)\n    if (bar)\n        if (baz) whee();\na();');
        bt('if (foo) a()\nif (bar) if (baz) whee();\na();',
            'if (foo) a()\nif (bar)\n    if (baz) whee();\na();');
        bt('if (foo);\nif (bar) if (baz) whee();\na();',
            'if (foo);\nif (bar)\n    if (baz) whee();\na();');
        bt('if (options)\n' +
           '    for (var p in options)\n' +
           '        this[p] = options[p];');
        bt('if (options) for (var p in options) this[p] = options[p];',
           'if (options)\n    for (var p in options) this[p] = options[p];');

        bt('if (options) do q(); while (b());',
           'if (options)\n    do q(); while (b());');
        bt('if (options) do; while (b());',
           'if (options)\n    do; while (b());');
        bt('if (options) while (b()) q();',
           'if (options)\n    while (b()) q();');
        bt('if (options) do while (b()) q(); while (a());',
           'if (options)\n    do\n        while (b()) q(); while (a());');

        bt('function f(a, b, c,\nd, e) {}',
            'function f(a, b, c,\n    d, e) {}');

        bt('function f(a,b) {if(a) b()}function g(a,b) {if(!a) b()}',
            'function f(a, b) {\n    if (a) b()\n}\n\nfunction g(a, b) {\n    if (!a) b()\n}');
        bt('function f(a,b) {if(a) b()}\n\n\n\nfunction g(a,b) {if(!a) b()}',
            'function f(a, b) {\n    if (a) b()\n}\n\n\n\nfunction g(a, b) {\n    if (!a) b()\n}');
        # This is not valid syntax, but still want to behave reasonably and not side-effect
        bt('(if(a) b())(if(a) b())',
            '(\n    if (a) b())(\n    if (a) b())');
        bt('(if(a) b())\n\n\n(if(a) b())',
            '(\n    if (a) b())\n\n\n(\n    if (a) b())');


        bt("if\n(a)\nb();", "if (a)\n    b();");
        bt('var a =\nfoo', 'var a =\n    foo');
        bt('var a = {\n"a":1,\n"b":2}', "var a = {\n    \"a\": 1,\n    \"b\": 2\n}");
        bt("var a = {\n'a':1,\n'b':2}", "var a = {\n    'a': 1,\n    'b': 2\n}");
        bt('var a = /*i*/ "b";');
        bt('var a = /*i*/\n"b";', 'var a = /*i*/\n    "b";');
        bt('var a = /*i*/\nb;', 'var a = /*i*/\n    b;');
        bt('{\n\n\n"x"\n}', '{\n\n\n    "x"\n}');
        bt('if(a &&\nb\n||\nc\n||d\n&&\ne) e = f', 'if (a &&\n    b ||\n    c || d &&\n    e) e = f');
        bt('if(a &&\n(b\n||\nc\n||d)\n&&\ne) e = f', 'if (a &&\n    (b ||\n        c || d) &&\n    e) e = f');
        test_fragment('\n\n"x"', '"x"');
        # this beavior differs between js and python, defaults to unlimited in js, 10 in python
        bt('a = 1;\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\nb = 2;',
            'a = 1;\n\n\n\n\n\n\n\n\n\nb = 2;');
        self.options.max_preserve_newlines = 8;
        bt('a = 1;\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\nb = 2;',
            'a = 1;\n\n\n\n\n\n\n\nb = 2;');

        # Test the option to have spaces within parens
        self.options.space_in_paren = False
        self.options.space_in_empty_paren = False
        bt('if(p) foo(a,b)', 'if (p) foo(a, b)');
        bt('try{while(true){willThrow()}}catch(result)switch(result){case 1:++result }',
           'try {\n    while (true) {\n        willThrow()\n    }\n} catch (result) switch (result) {\n    case 1:\n        ++result\n}');
        bt('((e/((a+(b)*c)-d))^2)*5;', '((e / ((a + (b) * c) - d)) ^ 2) * 5;');
        bt('function f(a,b) {if(a) b()}function g(a,b) {if(!a) b()}',
            'function f(a, b) {\n    if (a) b()\n}\n\nfunction g(a, b) {\n    if (!a) b()\n}');
        bt('a=[];',
            'a = [];');
        bt('a=[b,c,d];',
            'a = [b, c, d];');
        bt('a= f[b];',
            'a = f[b];');

        self.options.space_in_paren = True
        bt('if(p) foo(a,b)', 'if ( p ) foo( a, b )');
        bt('try{while(true){willThrow()}}catch(result)switch(result){case 1:++result }',
           'try {\n    while ( true ) {\n        willThrow()\n    }\n} catch ( result ) switch ( result ) {\n    case 1:\n        ++result\n}');
        bt('((e/((a+(b)*c)-d))^2)*5;', '( ( e / ( ( a + ( b ) * c ) - d ) ) ^ 2 ) * 5;');
        bt('function f(a,b) {if(a) b()}function g(a,b) {if(!a) b()}',
            'function f( a, b ) {\n    if ( a ) b()\n}\n\nfunction g( a, b ) {\n    if ( !a ) b()\n}');
        bt('a=[ ];',
            'a = [];');
        bt('a=[b,c,d];',
            'a = [ b, c, d ];');
        bt('a= f[b];',
            'a = f[ b ];');

        self.options.space_in_empty_paren = True
        bt('if(p) foo(a,b)', 'if ( p ) foo( a, b )');
        bt('try{while(true){willThrow()}}catch(result)switch(result){case 1:++result }',
           'try {\n    while ( true ) {\n        willThrow( )\n    }\n} catch ( result ) switch ( result ) {\n    case 1:\n        ++result\n}');
        bt('((e/((a+(b)*c)-d))^2)*5;', '( ( e / ( ( a + ( b ) * c ) - d ) ) ^ 2 ) * 5;');
        bt('function f(a,b) {if(a) b()}function g(a,b) {if(!a) b()}',
            'function f( a, b ) {\n    if ( a ) b( )\n}\n\nfunction g( a, b ) {\n    if ( !a ) b( )\n}');
        bt('a=[ ];',
            'a = [ ];');
        bt('a=[b,c,d];',
            'a = [ b, c, d ];');
        bt('a= f[b];',
            'a = f[ b ];');

        self.options.space_in_paren = False
        self.options.space_in_empty_paren = False

        # Test template strings
        bt('`This is a ${template} string.`', '`This is a ${template} string.`');
        bt('`This\n  is\n  a\n  ${template}\n  string.`', '`This\n  is\n  a\n  ${template}\n  string.`');

        # Test that e4x literals passed through when e4x-option is enabled
        bt('xml=<a b="c"><d/><e>\n foo</e>x</a>;', 'xml = < a b = "c" > < d / > < e >\n    foo < /e>x</a > ;');
        self.options.e4x = True
        bt('xml=<a b="c"><d/><e>\n foo</e>x</a>;', 'xml = <a b="c"><d/><e>\n foo</e>x</a>;');
        bt('<a b=\'This is a quoted "c".\'/>', '<a b=\'This is a quoted "c".\'/>');
        bt('<a b="This is a quoted \'c\'."/>', '<a b="This is a quoted \'c\'."/>');
        bt('<a b="A quote \' inside string."/>', '<a b="A quote \' inside string."/>');
        bt('<a b=\'A quote " inside string.\'/>', '<a b=\'A quote " inside string.\'/>');
        bt('<a b=\'Some """ quotes ""  inside string.\'/>', '<a b=\'Some """ quotes ""  inside string.\'/>');
        # Handles inline expressions
        bt('xml=<{a} b="c"><d/><e v={z}>\n foo</e>x</{a}>;', 'xml = <{a} b="c"><d/><e v={z}>\n foo</e>x</{a}>;');
        # xml literals with special characters in elem names
        bt('xml = <_:.valid.xml- _:.valid.xml-="123"/>;', 'xml = <_:.valid.xml- _:.valid.xml-="123"/>;');
        # Handles CDATA
        bt('xml=<a b="c"><![CDATA[d/>\n</a></{}]]></a>;', 'xml = <a b="c"><![CDATA[d/>\n</a></{}]]></a>;');
        bt('xml=<![CDATA[]]>;', 'xml = <![CDATA[]]>;');
        bt('xml=<![CDATA[ b="c"><d/><e v={z}>\n foo</e>x/]]>;', 'xml = <![CDATA[ b="c"><d/><e v={z}>\n foo</e>x/]]>;');
        # Handles messed up tags, as long as it isn't the same name
        # as the root tag. Also handles tags of same name as root tag
        # as long as nesting matches.
        bt('xml=<a x="jn"><c></b></f><a><d jnj="jnn"><f></a ></nj></a>;',
         'xml = <a x="jn"><c></b></f><a><d jnj="jnn"><f></a ></nj></a>;');
        # If xml is not terminated, the remainder of the file is treated
        # as part of the xml-literal (passed through unaltered)
        test_fragment('xml=<a></b>\nc<b;', 'xml = <a></b>\nc<b;');
        self.options.e4x = False

        # START tests for issue 241
        bt('obj\n' +
           '    .last({\n' +
           '        foo: 1,\n' +
           '        bar: 2\n' +
           '    });\n' +
           'var test = 1;');

        bt('obj\n' +
           '    .last(a, function() {\n' +
           '        var test;\n' +
           '    });\n' +
           'var test = 1;');

        bt('obj.first()\n' +
           '    .second()\n' +
           '    .last(function(err, response) {\n' +
           '        console.log(err);\n' +
           '    });');

        # END tests for issue 241


        # START tests for issue 268 and 275
        bt('obj.last(a, function() {\n' +
           '    var test;\n' +
           '});\n' +
           'var test = 1;');

        bt('obj.last(a,\n' +
           '    function() {\n' +
           '        var test;\n' +
           '    });\n' +
           'var test = 1;');

        bt('(function() {if (!window.FOO) window.FOO || (window.FOO = function() {var b = {bar: "zort"};});})();',
           '(function() {\n' +
           '    if (!window.FOO) window.FOO || (window.FOO = function() {\n' +
           '        var b = {\n' +
           '            bar: "zort"\n' +
           '        };\n' +
           '    });\n' +
           '})();');
        # END tests for issue 268 and 275

        # START tests for issue 281
        bt('define(["dojo/_base/declare", "my/Employee", "dijit/form/Button",\n' +
           '    "dojo/_base/lang", "dojo/Deferred"\n' +
           '], function(declare, Employee, Button, lang, Deferred) {\n' +
           '    return declare(Employee, {\n' +
           '        constructor: function() {\n' +
           '            new Button({\n' +
           '                onClick: lang.hitch(this, function() {\n' +
           '                    new Deferred().then(lang.hitch(this, function() {\n' +
           '                        this.salary * 0.25;\n' +
           '                    }));\n' +
           '                })\n' +
           '            });\n' +
           '        }\n' +
           '    });\n' +
           '});');
        bt('define(["dojo/_base/declare", "my/Employee", "dijit/form/Button",\n' +
           '        "dojo/_base/lang", "dojo/Deferred"\n' +
           '    ],\n' +
           '    function(declare, Employee, Button, lang, Deferred) {\n' +
           '        return declare(Employee, {\n' +
           '            constructor: function() {\n' +
           '                new Button({\n' +
           '                    onClick: lang.hitch(this, function() {\n' +
           '                        new Deferred().then(lang.hitch(this, function() {\n' +
           '                            this.salary * 0.25;\n' +
           '                        }));\n' +
           '                    })\n' +
           '                });\n' +
           '            }\n' +
           '        });\n' +
           '    });');
        # END tests for issue 281

        bt('var a=1,b={bang:2},c=3;',
            'var a = 1,\n    b = {\n        bang: 2\n    },\n    c = 3;');
        bt('var a={bing:1},b=2,c=3;',
            'var a = {\n        bing: 1\n    },\n    b = 2,\n    c = 3;');



    def decodesto(self, input, expectation=None):
        self.assertEqual(
            jsbeautifier.beautify(input, self.options), expectation or input)

        # if the expected is different from input, run it again
        # expected output should be unchanged when run twice.
        if not expectation == None:
            self.assertEqual(
                jsbeautifier.beautify(expectation, self.options), expectation)

    def wrap(self, text):
        return self.wrapregex.sub('    \\1', text)

    def bt(self, input, expectation=None):
        expectation = expectation or input
        self.decodesto(input, expectation)
        if self.options.indent_size == 4 and input:
            wrapped_input = '{\n%s\nfoo=bar;}' % self.wrap(input)
            wrapped_expect = '{\n%s\n    foo = bar;\n}' % self.wrap(expectation)
            self.decodesto(wrapped_input, wrapped_expect)

    @classmethod
    def setUpClass(cls):
        options = jsbeautifier.default_options()
        options.indent_size = 4
        options.indent_char = ' '
        options.preserve_newlines = True
        options.jslint_happy = False
        options.keep_array_indentation = False
        options.brace_style = 'collapse'
        options.indent_level = 0
        options.break_chained_methods = False

        cls.options = options
        cls.wrapregex = re.compile('^(.+)$', re.MULTILINE)


if __name__ == '__main__':
    unittest.main()

########NEW FILE########
__FILENAME__ = evalbased
#
# Unpacker for eval() based packers, a part of javascript beautifier
# by Einar Lielmanis <einar@jsbeautifier.org>
#
#     written by Stefano Sanfilippo <a.little.coder@gmail.com>
#
# usage:
#
# if detect(some_string):
#     unpacked = unpack(some_string)
#

"""Unpacker for eval() based packers: runs JS code and returns result.
Works only if a JS interpreter (e.g. Mozilla's Rhino) is installed and
properly set up on host."""

from subprocess import PIPE, Popen

PRIORITY = 3

def detect(source):
    """Detects if source is likely to be eval() packed."""
    return source.strip().lower().startswith('eval(function(')

def unpack(source):
    """Runs source and return resulting code."""
    return jseval('print %s;' % source[4:]) if detect(source) else source

# In case of failure, we'll just return the original, without crashing on user.
def jseval(script):
    """Run code in the JS interpreter and return output."""
    try:
        interpreter = Popen(['js'], stdin=PIPE, stdout=PIPE)
    except OSError:
        return script
    result, errors = interpreter.communicate(script)
    if interpreter.poll() or errors:
        return script
    return result

########NEW FILE########
__FILENAME__ = javascriptobfuscator
#
# simple unpacker/deobfuscator for scripts messed up with
# javascriptobfuscator.com
#
#     written by Einar Lielmanis <einar@jsbeautifier.org>
#     rewritten in Python by Stefano Sanfilippo <a.little.coder@gmail.com>
#
# Will always return valid javascript: if `detect()` is false, `code` is
# returned, unmodified.
#
# usage:
#
# if javascriptobfuscator.detect(some_string):
#     some_string = javascriptobfuscator.unpack(some_string)
#

"""deobfuscator for scripts messed up with JavascriptObfuscator.com"""

import re

PRIORITY = 1

def smartsplit(code):
    """Split `code` at " symbol, only if it is not escaped."""
    strings = []
    pos = 0
    while pos < len(code):
        if code[pos] == '"':
            word = '' # new word
            pos += 1
            while pos < len(code):
                if code[pos] == '"':
                    break
                if code[pos] == '\\':
                    word += '\\'
                    pos += 1
                word += code[pos]
                pos += 1
            strings.append('"%s"' % word)
        pos += 1
    return strings

def detect(code):
    """Detects if `code` is JavascriptObfuscator.com packed."""
    # prefer `is not` idiom, so that a true boolean is returned
    return (re.search(r'^var _0x[a-f0-9]+ ?\= ?\[', code) is not None)

def unpack(code):
    """Unpacks JavascriptObfuscator.com packed code."""
    if detect(code):
        matches = re.search(r'var (_0x[a-f\d]+) ?\= ?\[(.*?)\];', code)
        if matches:
            variable = matches.group(1)
            dictionary = smartsplit(matches.group(2))
            code = code[len(matches.group(0)):]
            for key, value in enumerate(dictionary):
                code = code.replace(r'%s[%s]' % (variable, key), value)
    return code

########NEW FILE########
__FILENAME__ = myobfuscate
#
# deobfuscator for scripts messed up with myobfuscate.com
# by Einar Lielmanis <einar@jsbeautifier.org>
#
#     written by Stefano Sanfilippo <a.little.coder@gmail.com>
#
# usage:
#
# if detect(some_string):
#     unpacked = unpack(some_string)
#

# CAVEAT by Einar Lielmanis

#
# You really don't want to obfuscate your scripts there: they're tracking
# your unpackings, your script gets turned into something like this,
# as of 2011-08-26:
#
#   var _escape = 'your_script_escaped';
#   var _111 = document.createElement('script');
#   _111.src = 'http://api.www.myobfuscate.com/?getsrc=ok' +
#              '&ref=' + encodeURIComponent(document.referrer) +
#              '&url=' + encodeURIComponent(document.URL);
#   var 000 = document.getElementsByTagName('head')[0];
#   000.appendChild(_111);
#   document.write(unescape(_escape));
#

"""Deobfuscator for scripts messed up with MyObfuscate.com"""

import re
import base64

# Python 2 retrocompatibility
# pylint: disable=F0401
# pylint: disable=E0611
try:
    from urllib import unquote
except ImportError:
    from urllib.parse import unquote

from jsbeautifier.unpackers import UnpackingError

PRIORITY = 1

CAVEAT = """//
// Unpacker warning: be careful when using myobfuscate.com for your projects:
// scripts obfuscated by the free online version call back home.
//

"""

SIGNATURE = (r'["\x41\x42\x43\x44\x45\x46\x47\x48\x49\x4A\x4B\x4C\x4D\x4E\x4F'
             r'\x50\x51\x52\x53\x54\x55\x56\x57\x58\x59\x5A\x61\x62\x63\x64\x65'
             r'\x66\x67\x68\x69\x6A\x6B\x6C\x6D\x6E\x6F\x70\x71\x72\x73\x74\x75'
             r'\x76\x77\x78\x79\x7A\x30\x31\x32\x33\x34\x35\x36\x37\x38\x39\x2B'
             r'\x2F\x3D","","\x63\x68\x61\x72\x41\x74","\x69\x6E\x64\x65\x78'
             r'\x4F\x66","\x66\x72\x6F\x6D\x43\x68\x61\x72\x43\x6F\x64\x65","'
             r'\x6C\x65\x6E\x67\x74\x68"]')

def detect(source):
    """Detects MyObfuscate.com packer."""
    return SIGNATURE in source

def unpack(source):
    """Unpacks js code packed with MyObfuscate.com"""
    if not detect(source):
        return source
    payload = unquote(_filter(source))
    match = re.search(r"^var _escape\='<script>(.*)<\/script>'",
                      payload, re.DOTALL)
    polished = match.group(1) if match else source
    return CAVEAT + polished

def _filter(source):
    """Extracts and decode payload (original file) from `source`"""
    try:
        varname = re.search(r'eval\(\w+\(\w+\((\w+)\)\)\);', source).group(1)
        reverse = re.search(r"var +%s *\= *'(.*)';" % varname, source).group(1)
    except AttributeError:
        raise UnpackingError('Malformed MyObfuscate data.')
    try:
        return base64.b64decode(reverse[::-1].encode('utf8')).decode('utf8')
    except TypeError:
        raise UnpackingError('MyObfuscate payload is not base64-encoded.')

########NEW FILE########
__FILENAME__ = packer
#
# Unpacker for Dean Edward's p.a.c.k.e.r, a part of javascript beautifier
# by Einar Lielmanis <einar@jsbeautifier.org>
#
#     written by Stefano Sanfilippo <a.little.coder@gmail.com>
#
# usage:
#
# if detect(some_string):
#     unpacked = unpack(some_string)
#

"""Unpacker for Dean Edward's p.a.c.k.e.r"""

import re
import string
from jsbeautifier.unpackers import UnpackingError

PRIORITY = 1

def detect(source):
    """Detects whether `source` is P.A.C.K.E.R. coded."""
    return source.replace(' ', '').startswith('eval(function(p,a,c,k,e,')

def unpack(source):
    """Unpacks P.A.C.K.E.R. packed js code."""
    payload, symtab, radix, count = _filterargs(source)

    if count != len(symtab):
        raise UnpackingError('Malformed p.a.c.k.e.r. symtab.')

    try:
        unbase = Unbaser(radix)
    except TypeError:
        raise UnpackingError('Unknown p.a.c.k.e.r. encoding.')

    def lookup(match):
        """Look up symbols in the synthetic symtab."""
        word  = match.group(0)
        return symtab[unbase(word)] or word

    source = re.sub(r'\b\w+\b', lookup, payload)
    return _replacestrings(source)

def _filterargs(source):
    """Juice from a source file the four args needed by decoder."""
    argsregex = (r"}\('(.*)', *(\d+), *(\d+), *'(.*)'\."
                 r"split\('\|'\), *(\d+), *(.*)\)\)")
    args = re.search(argsregex, source, re.DOTALL).groups()

    try:
        return args[0], args[3].split('|'), int(args[1]), int(args[2])
    except ValueError:
        raise UnpackingError('Corrupted p.a.c.k.e.r. data.')

def _replacestrings(source):
    """Strip string lookup table (list) and replace values in source."""
    match = re.search(r'var *(_\w+)\=\["(.*?)"\];', source, re.DOTALL)

    if match:
        varname, strings = match.groups()
        startpoint = len(match.group(0))
        lookup = strings.split('","')
        variable = '%s[%%d]' % varname
        for index, value in enumerate(lookup):
            source = source.replace(variable % index, '"%s"' % value)
        return source[startpoint:]
    return source


class Unbaser(object):
    """Functor for a given base. Will efficiently convert
    strings to natural numbers."""
    ALPHABET  = {
        62 : '0123456789abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ',
        95 : (' !"#$%&\'()*+,-./0123456789:;<=>?@ABCDEFGHIJKLMNOPQRSTUVWXYZ'
              '[\]^_`abcdefghijklmnopqrstuvwxyz{|}~')
    }

    def __init__(self, base):
        self.base = base

        # If base can be handled by int() builtin, let it do it for us
        if 2 <= base <= 36:
            self.unbase = lambda string: int(string, base)
        else:
            # Build conversion dictionary cache
            try:
                self.dictionary = dict((cipher, index) for
                    index, cipher in enumerate(self.ALPHABET[base]))
            except KeyError:
                raise TypeError('Unsupported base encoding.')

            self.unbase = self._dictunbaser

    def __call__(self, string):
        return self.unbase(string)

    def _dictunbaser(self, string):
        """Decodes a  value to an integer."""
        ret = 0
        for index, cipher in enumerate(string[::-1]):
            ret += (self.base ** index) * self.dictionary[cipher]
        return ret

########NEW FILE########
__FILENAME__ = testjavascriptobfuscator
#
#     written by Stefano Sanfilippo <a.little.coder@gmail.com>
#

"""Tests for JavaScriptObfuscator unpacker."""

import unittest
from jsbeautifier.unpackers.javascriptobfuscator import (
    unpack, detect, smartsplit)

# pylint: disable=R0904
class TestJavascriptObfuscator(unittest.TestCase):
    """JavascriptObfuscator.com test case."""
    def test_smartsplit(self):
        """Test smartsplit() function."""
        split = smartsplit
        equals = lambda data, result: self.assertEqual(split(data), result)

        equals('', [])
        equals('"a", "b"', ['"a"', '"b"'])
        equals('"aaa","bbbb"', ['"aaa"', '"bbbb"'])
        equals('"a", "b\\\""', ['"a"', '"b\\\""'])

    def test_detect(self):
        """Test detect() function."""
        positive = lambda source: self.assertTrue(detect(source))
        negative = lambda source: self.assertFalse(detect(source))

        negative('')
        negative('abcd')
        negative('var _0xaaaa')
        positive('var _0xaaaa = ["a", "b"]')
        positive('var _0xaaaa=["a", "b"]')
        positive('var _0x1234=["a","b"]')

    def test_unpack(self):
        """Test unpack() function."""
        decodeto = lambda ob, original: self.assertEqual(unpack(ob), original)

        decodeto('var _0x8df3=[];var a=10;', 'var a=10;')
        decodeto('var _0xb2a7=["\x74\x27\x65\x73\x74"];var i;for(i=0;i<10;++i)'
                 '{alert(_0xb2a7[0]);} ;', 'var i;for(i=0;i<10;++i){alert'
                 '("t\'est");} ;')

if __name__ == '__main__':
    unittest.main()

########NEW FILE########
__FILENAME__ = testmyobfuscate
#
#     written by Stefano Sanfilippo <a.little.coder@gmail.com>
#

"""Tests for MyObfuscate unpacker."""

import unittest
import os
from jsbeautifier.unpackers.myobfuscate import detect, unpack
from jsbeautifier.unpackers.tests import __path__ as path

INPUT = os.path.join(path[0], 'test-myobfuscate-input.js')
OUTPUT = os.path.join(path[0], 'test-myobfuscate-output.js')

# pylint: disable=R0904
class TestMyObfuscate(unittest.TestCase):
    # pylint: disable=C0103
    """MyObfuscate obfuscator testcase."""
    @classmethod
    def setUpClass(cls):
        """Load source files (encoded and decoded version) for tests."""
        with open(INPUT, 'r') as data:
            cls.input = data.read()
        with open(OUTPUT, 'r') as data:
            cls.output = data.read()

    def test_detect(self):
        """Test detect() function."""
        detected = lambda source: self.assertTrue(detect(source))

        detected(self.input)

    def test_unpack(self):
        """Test unpack() function."""
        check = lambda inp, out: self.assertEqual(unpack(inp), out)

        check(self.input, self.output)

if __name__ == '__main__':
    unittest.main()

########NEW FILE########
__FILENAME__ = testpacker
#
#     written by Stefano Sanfilippo <a.little.coder@gmail.com>
#

"""Tests for P.A.C.K.E.R. unpacker."""

import unittest
from jsbeautifier.unpackers.packer import detect, unpack

# pylint: disable=R0904
class TestPacker(unittest.TestCase):
    """P.A.C.K.E.R. testcase."""
    def test_detect(self):
        """Test detect() function."""
        positive = lambda source: self.assertTrue(detect(source))
        negative = lambda source: self.assertFalse(detect(source))

        negative('')
        negative('var a = b')
        positive('eval(function(p,a,c,k,e,r')
        positive('eval ( function(p, a, c, k, e, r')

    def test_unpack(self):
        """Test unpack() function."""
        check = lambda inp, out: self.assertEqual(unpack(inp), out)

        check("eval(function(p,a,c,k,e,r){e=String;if(!''.replace(/^/,String)"
              "){while(c--)r[c]=k[c]||c;k=[function(e){return r[e]}];e="
              "function(){return'\\\\w+'};c=1};while(c--)if(k[c])p=p.replace("
              "new RegExp('\\\\b'+e(c)+'\\\\b','g'),k[c]);return p}('0 2=1',"
              "62,3,'var||a'.split('|'),0,{}))", 'var a=1')

if __name__ == '__main__':
    unittest.main()

########NEW FILE########
__FILENAME__ = testurlencode
#
#     written by Stefano Sanfilippo <a.little.coder@gmail.com>
#

"""Tests for urlencoded unpacker."""

import unittest

from jsbeautifier.unpackers.urlencode import detect, unpack

# pylint: disable=R0904
class TestUrlencode(unittest.TestCase):
    """urlencode test case."""
    def test_detect(self):
        """Test detect() function."""
        encoded = lambda source: self.assertTrue(detect(source))
        unencoded = lambda source: self.assertFalse(detect(source))

        unencoded('')
        unencoded('var a = b')
        encoded('var%20a+=+b')
        encoded('var%20a=b')
        encoded('var%20%21%22')

    def test_unpack(self):
        """Test unpack function."""
        equals = lambda source, result: self.assertEqual(unpack(source), result)

        equals('', '')
        equals('abcd', 'abcd')
        equals('var a = b', 'var a = b')
        equals('var%20a=b', 'var a=b')
        equals('var%20a+=+b', 'var a = b')

if __name__ == '__main__':
    unittest.main()

########NEW FILE########
__FILENAME__ = urlencode
#
# Trivial bookmarklet/escaped script detector for the javascript beautifier
#     written by Einar Lielmanis <einar@jsbeautifier.org>
#     rewritten in Python by Stefano Sanfilippo <a.little.coder@gmail.com>
#
# Will always return valid javascript: if `detect()` is false, `code` is
# returned, unmodified.
#
# usage:
#
# some_string = urlencode.unpack(some_string)
#

"""Bookmarklet/escaped script unpacker."""

# Python 2 retrocompatibility
# pylint: disable=F0401
# pylint: disable=E0611
try:
    from urllib import unquote_plus
except ImportError:
    from urllib.parse import unquote_plus

PRIORITY = 0

def detect(code):
    """Detects if a scriptlet is urlencoded."""
    # the fact that script doesn't contain any space, but has %20 instead
    # should be sufficient check for now.
    return ' ' not in code and ('%20' in code or code.count('%') > 3)

def unpack(code):
    """URL decode `code` source string."""
    return unquote_plus(code) if detect(code) else code

########NEW FILE########
__FILENAME__ = __version__
__version__ = '1.5.0'

########NEW FILE########
__FILENAME__ = six
"""Utilities for writing code that runs on Python 2 and 3"""

# Copyright (c) 2010-2014 Benjamin Peterson
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.

import operator
import sys
import types

__author__ = "Benjamin Peterson <benjamin@python.org>"
__version__ = "1.6.1"


# Useful for very coarse version differentiation.
PY2 = sys.version_info[0] == 2
PY3 = sys.version_info[0] == 3

if PY3:
    string_types = str,
    integer_types = int,
    class_types = type,
    text_type = str
    binary_type = bytes

    MAXSIZE = sys.maxsize
else:
    string_types = basestring,
    integer_types = (int, long)
    class_types = (type, types.ClassType)
    text_type = unicode
    binary_type = str

    if sys.platform.startswith("java"):
        # Jython always uses 32 bits.
        MAXSIZE = int((1 << 31) - 1)
    else:
        # It's possible to have sizeof(long) != sizeof(Py_ssize_t).
        class X(object):
            def __len__(self):
                return 1 << 31
        try:
            len(X())
        except OverflowError:
            # 32-bit
            MAXSIZE = int((1 << 31) - 1)
        else:
            # 64-bit
            MAXSIZE = int((1 << 63) - 1)
        del X


def _add_doc(func, doc):
    """Add documentation to a function."""
    func.__doc__ = doc


def _import_module(name):
    """Import module, returning the module after the last dot."""
    __import__(name)
    return sys.modules[name]


class _LazyDescr(object):

    def __init__(self, name):
        self.name = name

    def __get__(self, obj, tp):
        try:
            result = self._resolve()
        except ImportError:
            # See the nice big comment in MovedModule.__getattr__.
            raise AttributeError("%s could not be imported " % self.name)
        setattr(obj, self.name, result) # Invokes __set__.
        # This is a bit ugly, but it avoids running this again.
        delattr(obj.__class__, self.name)
        return result


class MovedModule(_LazyDescr):

    def __init__(self, name, old, new=None):
        super(MovedModule, self).__init__(name)
        if PY3:
            if new is None:
                new = name
            self.mod = new
        else:
            self.mod = old

    def _resolve(self):
        return _import_module(self.mod)

    def __getattr__(self, attr):
        # It turns out many Python frameworks like to traverse sys.modules and
        # try to load various attributes. This causes problems if this is a
        # platform-specific module on the wrong platform, like _winreg on
        # Unixes. Therefore, we silently pretend unimportable modules do not
        # have any attributes. See issues #51, #53, #56, and #63 for the full
        # tales of woe.
        #
        # First, if possible, avoid loading the module just to look at __file__,
        # __name__, or __path__.
        if (attr in ("__file__", "__name__", "__path__") and
            self.mod not in sys.modules):
            raise AttributeError(attr)
        try:
            _module = self._resolve()
        except ImportError:
            raise AttributeError(attr)
        value = getattr(_module, attr)
        setattr(self, attr, value)
        return value


class _LazyModule(types.ModuleType):

    def __init__(self, name):
        super(_LazyModule, self).__init__(name)
        self.__doc__ = self.__class__.__doc__

    def __dir__(self):
        attrs = ["__doc__", "__name__"]
        attrs += [attr.name for attr in self._moved_attributes]
        return attrs

    # Subclasses should override this
    _moved_attributes = []


class MovedAttribute(_LazyDescr):

    def __init__(self, name, old_mod, new_mod, old_attr=None, new_attr=None):
        super(MovedAttribute, self).__init__(name)
        if PY3:
            if new_mod is None:
                new_mod = name
            self.mod = new_mod
            if new_attr is None:
                if old_attr is None:
                    new_attr = name
                else:
                    new_attr = old_attr
            self.attr = new_attr
        else:
            self.mod = old_mod
            if old_attr is None:
                old_attr = name
            self.attr = old_attr

    def _resolve(self):
        module = _import_module(self.mod)
        return getattr(module, self.attr)



class _MovedItems(_LazyModule):
    """Lazy loading of moved objects"""


_moved_attributes = [
    MovedAttribute("cStringIO", "cStringIO", "io", "StringIO"),
    MovedAttribute("filter", "itertools", "builtins", "ifilter", "filter"),
    MovedAttribute("filterfalse", "itertools", "itertools", "ifilterfalse", "filterfalse"),
    MovedAttribute("input", "__builtin__", "builtins", "raw_input", "input"),
    MovedAttribute("map", "itertools", "builtins", "imap", "map"),
    MovedAttribute("range", "__builtin__", "builtins", "xrange", "range"),
    MovedAttribute("reload_module", "__builtin__", "imp", "reload"),
    MovedAttribute("reduce", "__builtin__", "functools"),
    MovedAttribute("StringIO", "StringIO", "io"),
    MovedAttribute("UserString", "UserString", "collections"),
    MovedAttribute("xrange", "__builtin__", "builtins", "xrange", "range"),
    MovedAttribute("zip", "itertools", "builtins", "izip", "zip"),
    MovedAttribute("zip_longest", "itertools", "itertools", "izip_longest", "zip_longest"),

    MovedModule("builtins", "__builtin__"),
    MovedModule("configparser", "ConfigParser"),
    MovedModule("copyreg", "copy_reg"),
    MovedModule("dbm_gnu", "gdbm", "dbm.gnu"),
    MovedModule("http_cookiejar", "cookielib", "http.cookiejar"),
    MovedModule("http_cookies", "Cookie", "http.cookies"),
    MovedModule("html_entities", "htmlentitydefs", "html.entities"),
    MovedModule("html_parser", "HTMLParser", "html.parser"),
    MovedModule("http_client", "httplib", "http.client"),
    MovedModule("email_mime_multipart", "email.MIMEMultipart", "email.mime.multipart"),
    MovedModule("email_mime_text", "email.MIMEText", "email.mime.text"),
    MovedModule("email_mime_base", "email.MIMEBase", "email.mime.base"),
    MovedModule("BaseHTTPServer", "BaseHTTPServer", "http.server"),
    MovedModule("CGIHTTPServer", "CGIHTTPServer", "http.server"),
    MovedModule("SimpleHTTPServer", "SimpleHTTPServer", "http.server"),
    MovedModule("cPickle", "cPickle", "pickle"),
    MovedModule("queue", "Queue"),
    MovedModule("reprlib", "repr"),
    MovedModule("socketserver", "SocketServer"),
    MovedModule("_thread", "thread", "_thread"),
    MovedModule("tkinter", "Tkinter"),
    MovedModule("tkinter_dialog", "Dialog", "tkinter.dialog"),
    MovedModule("tkinter_filedialog", "FileDialog", "tkinter.filedialog"),
    MovedModule("tkinter_scrolledtext", "ScrolledText", "tkinter.scrolledtext"),
    MovedModule("tkinter_simpledialog", "SimpleDialog", "tkinter.simpledialog"),
    MovedModule("tkinter_tix", "Tix", "tkinter.tix"),
    MovedModule("tkinter_ttk", "ttk", "tkinter.ttk"),
    MovedModule("tkinter_constants", "Tkconstants", "tkinter.constants"),
    MovedModule("tkinter_dnd", "Tkdnd", "tkinter.dnd"),
    MovedModule("tkinter_colorchooser", "tkColorChooser",
                "tkinter.colorchooser"),
    MovedModule("tkinter_commondialog", "tkCommonDialog",
                "tkinter.commondialog"),
    MovedModule("tkinter_tkfiledialog", "tkFileDialog", "tkinter.filedialog"),
    MovedModule("tkinter_font", "tkFont", "tkinter.font"),
    MovedModule("tkinter_messagebox", "tkMessageBox", "tkinter.messagebox"),
    MovedModule("tkinter_tksimpledialog", "tkSimpleDialog",
                "tkinter.simpledialog"),
    MovedModule("urllib_parse", __name__ + ".moves.urllib_parse", "urllib.parse"),
    MovedModule("urllib_error", __name__ + ".moves.urllib_error", "urllib.error"),
    MovedModule("urllib", __name__ + ".moves.urllib", __name__ + ".moves.urllib"),
    MovedModule("urllib_robotparser", "robotparser", "urllib.robotparser"),
    MovedModule("xmlrpc_client", "xmlrpclib", "xmlrpc.client"),
    MovedModule("xmlrpc_server", "xmlrpclib", "xmlrpc.server"),
    MovedModule("winreg", "_winreg"),
]
for attr in _moved_attributes:
    setattr(_MovedItems, attr.name, attr)
    if isinstance(attr, MovedModule):
        sys.modules[__name__ + ".moves." + attr.name] = attr
del attr

_MovedItems._moved_attributes = _moved_attributes

moves = sys.modules[__name__ + ".moves"] = _MovedItems(__name__ + ".moves")


class Module_six_moves_urllib_parse(_LazyModule):
    """Lazy loading of moved objects in six.moves.urllib_parse"""


_urllib_parse_moved_attributes = [
    MovedAttribute("ParseResult", "urlparse", "urllib.parse"),
    MovedAttribute("SplitResult", "urlparse", "urllib.parse"),
    MovedAttribute("parse_qs", "urlparse", "urllib.parse"),
    MovedAttribute("parse_qsl", "urlparse", "urllib.parse"),
    MovedAttribute("urldefrag", "urlparse", "urllib.parse"),
    MovedAttribute("urljoin", "urlparse", "urllib.parse"),
    MovedAttribute("urlparse", "urlparse", "urllib.parse"),
    MovedAttribute("urlsplit", "urlparse", "urllib.parse"),
    MovedAttribute("urlunparse", "urlparse", "urllib.parse"),
    MovedAttribute("urlunsplit", "urlparse", "urllib.parse"),
    MovedAttribute("quote", "urllib", "urllib.parse"),
    MovedAttribute("quote_plus", "urllib", "urllib.parse"),
    MovedAttribute("unquote", "urllib", "urllib.parse"),
    MovedAttribute("unquote_plus", "urllib", "urllib.parse"),
    MovedAttribute("urlencode", "urllib", "urllib.parse"),
    MovedAttribute("splitquery", "urllib", "urllib.parse"),
]
for attr in _urllib_parse_moved_attributes:
    setattr(Module_six_moves_urllib_parse, attr.name, attr)
del attr

Module_six_moves_urllib_parse._moved_attributes = _urllib_parse_moved_attributes

sys.modules[__name__ + ".moves.urllib_parse"] = sys.modules[__name__ + ".moves.urllib.parse"] = Module_six_moves_urllib_parse(__name__ + ".moves.urllib_parse")


class Module_six_moves_urllib_error(_LazyModule):
    """Lazy loading of moved objects in six.moves.urllib_error"""


_urllib_error_moved_attributes = [
    MovedAttribute("URLError", "urllib2", "urllib.error"),
    MovedAttribute("HTTPError", "urllib2", "urllib.error"),
    MovedAttribute("ContentTooShortError", "urllib", "urllib.error"),
]
for attr in _urllib_error_moved_attributes:
    setattr(Module_six_moves_urllib_error, attr.name, attr)
del attr

Module_six_moves_urllib_error._moved_attributes = _urllib_error_moved_attributes

sys.modules[__name__ + ".moves.urllib_error"] = sys.modules[__name__ + ".moves.urllib.error"] = Module_six_moves_urllib_error(__name__ + ".moves.urllib.error")


class Module_six_moves_urllib_request(_LazyModule):
    """Lazy loading of moved objects in six.moves.urllib_request"""


_urllib_request_moved_attributes = [
    MovedAttribute("urlopen", "urllib2", "urllib.request"),
    MovedAttribute("install_opener", "urllib2", "urllib.request"),
    MovedAttribute("build_opener", "urllib2", "urllib.request"),
    MovedAttribute("pathname2url", "urllib", "urllib.request"),
    MovedAttribute("url2pathname", "urllib", "urllib.request"),
    MovedAttribute("getproxies", "urllib", "urllib.request"),
    MovedAttribute("Request", "urllib2", "urllib.request"),
    MovedAttribute("OpenerDirector", "urllib2", "urllib.request"),
    MovedAttribute("HTTPDefaultErrorHandler", "urllib2", "urllib.request"),
    MovedAttribute("HTTPRedirectHandler", "urllib2", "urllib.request"),
    MovedAttribute("HTTPCookieProcessor", "urllib2", "urllib.request"),
    MovedAttribute("ProxyHandler", "urllib2", "urllib.request"),
    MovedAttribute("BaseHandler", "urllib2", "urllib.request"),
    MovedAttribute("HTTPPasswordMgr", "urllib2", "urllib.request"),
    MovedAttribute("HTTPPasswordMgrWithDefaultRealm", "urllib2", "urllib.request"),
    MovedAttribute("AbstractBasicAuthHandler", "urllib2", "urllib.request"),
    MovedAttribute("HTTPBasicAuthHandler", "urllib2", "urllib.request"),
    MovedAttribute("ProxyBasicAuthHandler", "urllib2", "urllib.request"),
    MovedAttribute("AbstractDigestAuthHandler", "urllib2", "urllib.request"),
    MovedAttribute("HTTPDigestAuthHandler", "urllib2", "urllib.request"),
    MovedAttribute("ProxyDigestAuthHandler", "urllib2", "urllib.request"),
    MovedAttribute("HTTPHandler", "urllib2", "urllib.request"),
    MovedAttribute("HTTPSHandler", "urllib2", "urllib.request"),
    MovedAttribute("FileHandler", "urllib2", "urllib.request"),
    MovedAttribute("FTPHandler", "urllib2", "urllib.request"),
    MovedAttribute("CacheFTPHandler", "urllib2", "urllib.request"),
    MovedAttribute("UnknownHandler", "urllib2", "urllib.request"),
    MovedAttribute("HTTPErrorProcessor", "urllib2", "urllib.request"),
    MovedAttribute("urlretrieve", "urllib", "urllib.request"),
    MovedAttribute("urlcleanup", "urllib", "urllib.request"),
    MovedAttribute("URLopener", "urllib", "urllib.request"),
    MovedAttribute("FancyURLopener", "urllib", "urllib.request"),
    MovedAttribute("proxy_bypass", "urllib", "urllib.request"),
]
for attr in _urllib_request_moved_attributes:
    setattr(Module_six_moves_urllib_request, attr.name, attr)
del attr

Module_six_moves_urllib_request._moved_attributes = _urllib_request_moved_attributes

sys.modules[__name__ + ".moves.urllib_request"] = sys.modules[__name__ + ".moves.urllib.request"] = Module_six_moves_urllib_request(__name__ + ".moves.urllib.request")


class Module_six_moves_urllib_response(_LazyModule):
    """Lazy loading of moved objects in six.moves.urllib_response"""


_urllib_response_moved_attributes = [
    MovedAttribute("addbase", "urllib", "urllib.response"),
    MovedAttribute("addclosehook", "urllib", "urllib.response"),
    MovedAttribute("addinfo", "urllib", "urllib.response"),
    MovedAttribute("addinfourl", "urllib", "urllib.response"),
]
for attr in _urllib_response_moved_attributes:
    setattr(Module_six_moves_urllib_response, attr.name, attr)
del attr

Module_six_moves_urllib_response._moved_attributes = _urllib_response_moved_attributes

sys.modules[__name__ + ".moves.urllib_response"] = sys.modules[__name__ + ".moves.urllib.response"] = Module_six_moves_urllib_response(__name__ + ".moves.urllib.response")


class Module_six_moves_urllib_robotparser(_LazyModule):
    """Lazy loading of moved objects in six.moves.urllib_robotparser"""


_urllib_robotparser_moved_attributes = [
    MovedAttribute("RobotFileParser", "robotparser", "urllib.robotparser"),
]
for attr in _urllib_robotparser_moved_attributes:
    setattr(Module_six_moves_urllib_robotparser, attr.name, attr)
del attr

Module_six_moves_urllib_robotparser._moved_attributes = _urllib_robotparser_moved_attributes

sys.modules[__name__ + ".moves.urllib_robotparser"] = sys.modules[__name__ + ".moves.urllib.robotparser"] = Module_six_moves_urllib_robotparser(__name__ + ".moves.urllib.robotparser")


class Module_six_moves_urllib(types.ModuleType):
    """Create a six.moves.urllib namespace that resembles the Python 3 namespace"""
    parse = sys.modules[__name__ + ".moves.urllib_parse"]
    error = sys.modules[__name__ + ".moves.urllib_error"]
    request = sys.modules[__name__ + ".moves.urllib_request"]
    response = sys.modules[__name__ + ".moves.urllib_response"]
    robotparser = sys.modules[__name__ + ".moves.urllib_robotparser"]

    def __dir__(self):
        return ['parse', 'error', 'request', 'response', 'robotparser']


sys.modules[__name__ + ".moves.urllib"] = Module_six_moves_urllib(__name__ + ".moves.urllib")


def add_move(move):
    """Add an item to six.moves."""
    setattr(_MovedItems, move.name, move)


def remove_move(name):
    """Remove item from six.moves."""
    try:
        delattr(_MovedItems, name)
    except AttributeError:
        try:
            del moves.__dict__[name]
        except KeyError:
            raise AttributeError("no such move, %r" % (name,))


if PY3:
    _meth_func = "__func__"
    _meth_self = "__self__"

    _func_closure = "__closure__"
    _func_code = "__code__"
    _func_defaults = "__defaults__"
    _func_globals = "__globals__"

    _iterkeys = "keys"
    _itervalues = "values"
    _iteritems = "items"
    _iterlists = "lists"
else:
    _meth_func = "im_func"
    _meth_self = "im_self"

    _func_closure = "func_closure"
    _func_code = "func_code"
    _func_defaults = "func_defaults"
    _func_globals = "func_globals"

    _iterkeys = "iterkeys"
    _itervalues = "itervalues"
    _iteritems = "iteritems"
    _iterlists = "iterlists"


try:
    advance_iterator = next
except NameError:
    def advance_iterator(it):
        return it.next()
next = advance_iterator


try:
    callable = callable
except NameError:
    def callable(obj):
        return any("__call__" in klass.__dict__ for klass in type(obj).__mro__)


if PY3:
    def get_unbound_function(unbound):
        return unbound

    create_bound_method = types.MethodType

    Iterator = object
else:
    def get_unbound_function(unbound):
        return unbound.im_func

    def create_bound_method(func, obj):
        return types.MethodType(func, obj, obj.__class__)

    class Iterator(object):

        def next(self):
            return type(self).__next__(self)

    callable = callable
_add_doc(get_unbound_function,
         """Get the function out of a possibly unbound function""")


get_method_function = operator.attrgetter(_meth_func)
get_method_self = operator.attrgetter(_meth_self)
get_function_closure = operator.attrgetter(_func_closure)
get_function_code = operator.attrgetter(_func_code)
get_function_defaults = operator.attrgetter(_func_defaults)
get_function_globals = operator.attrgetter(_func_globals)


def iterkeys(d, **kw):
    """Return an iterator over the keys of a dictionary."""
    return iter(getattr(d, _iterkeys)(**kw))

def itervalues(d, **kw):
    """Return an iterator over the values of a dictionary."""
    return iter(getattr(d, _itervalues)(**kw))

def iteritems(d, **kw):
    """Return an iterator over the (key, value) pairs of a dictionary."""
    return iter(getattr(d, _iteritems)(**kw))

def iterlists(d, **kw):
    """Return an iterator over the (key, [values]) pairs of a dictionary."""
    return iter(getattr(d, _iterlists)(**kw))


if PY3:
    def b(s):
        return s.encode("latin-1")
    def u(s):
        return s
    unichr = chr
    if sys.version_info[1] <= 1:
        def int2byte(i):
            return bytes((i,))
    else:
        # This is about 2x faster than the implementation above on 3.2+
        int2byte = operator.methodcaller("to_bytes", 1, "big")
    byte2int = operator.itemgetter(0)
    indexbytes = operator.getitem
    iterbytes = iter
    import io
    StringIO = io.StringIO
    BytesIO = io.BytesIO
else:
    def b(s):
        return s
    # Workaround for standalone backslash
    def u(s):
        return unicode(s.replace(r'\\', r'\\\\'), "unicode_escape")
    unichr = unichr
    int2byte = chr
    def byte2int(bs):
        return ord(bs[0])
    def indexbytes(buf, i):
        return ord(buf[i])
    def iterbytes(buf):
        return (ord(byte) for byte in buf)
    import StringIO
    StringIO = BytesIO = StringIO.StringIO
_add_doc(b, """Byte literal""")
_add_doc(u, """Text literal""")


if PY3:
    exec_ = getattr(moves.builtins, "exec")


    def reraise(tp, value, tb=None):
        if value.__traceback__ is not tb:
            raise value.with_traceback(tb)
        raise value

else:
    def exec_(_code_, _globs_=None, _locs_=None):
        """Execute code in a namespace."""
        if _globs_ is None:
            frame = sys._getframe(1)
            _globs_ = frame.f_globals
            if _locs_ is None:
                _locs_ = frame.f_locals
            del frame
        elif _locs_ is None:
            _locs_ = _globs_
        exec("""exec _code_ in _globs_, _locs_""")


    exec_("""def reraise(tp, value, tb=None):
    raise tp, value, tb
""")


print_ = getattr(moves.builtins, "print", None)
if print_ is None:
    def print_(*args, **kwargs):
        """The new-style print function for Python 2.4 and 2.5."""
        fp = kwargs.pop("file", sys.stdout)
        if fp is None:
            return
        def write(data):
            if not isinstance(data, basestring):
                data = str(data)
            # If the file has an encoding, encode unicode with it.
            if (isinstance(fp, file) and
                isinstance(data, unicode) and
                fp.encoding is not None):
                errors = getattr(fp, "errors", None)
                if errors is None:
                    errors = "strict"
                data = data.encode(fp.encoding, errors)
            fp.write(data)
        want_unicode = False
        sep = kwargs.pop("sep", None)
        if sep is not None:
            if isinstance(sep, unicode):
                want_unicode = True
            elif not isinstance(sep, str):
                raise TypeError("sep must be None or a string")
        end = kwargs.pop("end", None)
        if end is not None:
            if isinstance(end, unicode):
                want_unicode = True
            elif not isinstance(end, str):
                raise TypeError("end must be None or a string")
        if kwargs:
            raise TypeError("invalid keyword arguments to print()")
        if not want_unicode:
            for arg in args:
                if isinstance(arg, unicode):
                    want_unicode = True
                    break
        if want_unicode:
            newline = unicode("\n")
            space = unicode(" ")
        else:
            newline = "\n"
            space = " "
        if sep is None:
            sep = space
        if end is None:
            end = newline
        for i, arg in enumerate(args):
            if i:
                write(sep)
            write(arg)
        write(end)

_add_doc(reraise, """Reraise an exception.""")


def with_metaclass(meta, *bases):
    """Create a base class with a metaclass."""
    return meta("NewBase", bases, {})

def add_metaclass(metaclass):
    """Class decorator for creating a class with a metaclass."""
    def wrapper(cls):
        orig_vars = cls.__dict__.copy()
        orig_vars.pop('__dict__', None)
        orig_vars.pop('__weakref__', None)
        slots = orig_vars.get('__slots__')
        if slots is not None:
            if isinstance(slots, str):
                slots = [slots]
            for slots_var in slots:
                orig_vars.pop(slots_var)
        return metaclass(cls.__name__, cls.__bases__, orig_vars)
    return wrapper

########NEW FILE########
__FILENAME__ = merge_utils
"""
Copyright (c) 2012 The GoSublime Authors

Permission is hereby granted, free of charge, to any person obtaining a copy of
this software and associated documentation files (the "Software"), to deal in
the Software without restriction, including without limitation the rights to
use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies
of the Software, and to permit persons to whom the Software is furnished to do
so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
"""

# Borrowed from GoSublime

import sublime

from diff_match_patch import diff_match_patch


class MergeException(Exception):
    pass


def _merge_code(view, edit, code, formatted):
    def ss(start, end):
        return view.substr(sublime.Region(start, end))

    dmp = diff_match_patch()
    diffs = dmp.diff_main(code, formatted)
    dmp.diff_cleanupEfficiency(diffs)
    i = 0
    dirty = False
    for k, s in diffs:
        l = len(s)
        if k == 0:
            # match
            l = len(s)
            if ss(i, i + l) != s:
                raise MergeException('mismatch', dirty)
            i += l
        else:
            dirty = True
            if k > 0:
                # insert
                view.insert(edit, i, s)
                i += l
            else:
                # delete
                if ss(i, i + l) != s:
                    raise MergeException('mismatch', dirty)
                view.erase(edit, sublime.Region(i, i + l))
    return dirty


def merge_code(view, edit, code, formatted_code):
    vs = view.settings()
    ttts = vs.get("translate_tabs_to_spaces")
    vs.set("translate_tabs_to_spaces", False)
    if not code.strip():
        return (False, '')

    dirty = False
    err = ''
    try:
        dirty = _merge_code(view, edit, code, formatted_code)
    except MergeException as exc:
        dirty = True
        err = "Could not merge changes into the buffer, edit aborted: %s" % exc
        view.replace(edit, sublime.Region(0, view.size()), code)
    except Exception as ex:
        err = "Unknown exception: %s" % ex
    finally:
        vs.set("translate_tabs_to_spaces", ttts)
        return (dirty, err)

########NEW FILE########
__FILENAME__ = jsf
import sublime, re

# if you don't explicitly import jsbeautifier.unpackers here things will bomb out,
# even though we don't use it directly.....
import jsbeautifier, jsbeautifier.unpackers
import merge_utils

def format_selection(view, edit, opts):
	def get_line_indentation_pos(view, point):
		line_region = view.line(point)
		pos = line_region.a
		end = line_region.b
		while pos < end:
			ch = view.substr(pos)
			if ch != ' ' and ch != '\t':
				break
			pos += 1
		return pos

	def get_indentation_count(view, start):
		indent_count = 0
		i = start - 1
		while i > 0:
			ch = view.substr(i)
			scope = view.scope_name(i)
			# Skip preprocessors, strings, characaters and comments
			if 'string.quoted' in scope or 'comment' in scope or 'preprocessor' in scope:
				extent = view.extract_scope(i)
				i = extent.a - 1
				continue
			else:
				i -= 1

			if ch == '}':
				indent_count -= 1
			elif ch == '{':
				indent_count += 1
		return indent_count

	regions = []
	for sel in view.sel():
		start = get_line_indentation_pos(view, min(sel.a, sel.b))
		region = sublime.Region(
			view.line(start).a,  # line start of first line
			view.line(max(sel.a, sel.b)).b)  # line end of last line
		indent_count = get_indentation_count(view, start)
		# Add braces for indentation hack
		code = '{' * indent_count
		if indent_count > 0:
			code += '\n'
		code += view.substr(region)
		# Performing astyle formatter
		formatted_code = jsbeautifier.beautify(code, opts)
		if indent_count > 0:
			for _ in range(indent_count):
				index = formatted_code.find('{') + 1
				formatted_code = formatted_code[index:]
			formatted_code = re.sub(r'[ \t]*\n([^\r\n])', r'\1', formatted_code, 1)
		else:
			# HACK: While no identation, a '{' will generate a blank line, so strip it.
			search = "\n{"
			if search not in code:
				formatted_code = formatted_code.replace(search, '{', 1)
		# Applying formatted code
		view.replace(edit, region, formatted_code)
		# Region for replaced code
		if sel.a <= sel.b:
			regions.append(sublime.Region(region.a, region.a + len(formatted_code)))
		else:
			regions.append(sublime.Region(region.a + len(formatted_code), region.a))
	view.sel().clear()
	# Add regions of formatted code
	[view.sel().add(region) for region in regions]

def format_whole_file(view, edit, opts):
	settings = view.settings()
	region = sublime.Region(0, view.size())
	code = view.substr(region)
	formatted_code = jsbeautifier.beautify(code, opts)

	if(settings.get("ensure_newline_at_eof_on_save") and not formatted_code.endswith("\n")):
		formatted_code = formatted_code + "\n"

	_, err = merge_utils.merge_code(view, edit, code, formatted_code)
	if err:
		sublime.error_message("JsFormat: Merge failure: '%s'" % err)
########NEW FILE########
__FILENAME__ = jsf_activation
import os

def is_js_buffer(view):
	fName = view.file_name()
	vSettings = view.settings()
	syntaxPath = vSettings.get('syntax')
	syntax = ""
	ext = ""

	if (fName != None): # file exists, pull syntax type from extension
		ext = os.path.splitext(fName)[1][1:]
	if(syntaxPath != None):
		syntax = os.path.splitext(syntaxPath)[0].split('/')[-1].lower()

	return ext in ['js', 'json'] or "javascript" in syntax or "json" in syntax
########NEW FILE########
__FILENAME__ = jsf_rc
import os, json

def get_rc_paths(cwd):
	result = []
	subs = cwd.split(os.sep)
	fullPath = ""

	for value in subs:
		fullPath += value + os.sep
		result.append(fullPath + '.jsbeautifyrc')

	return result

def filter_existing_files(paths):
	result = []

	for value in paths:
		if (os.path.isfile(value)):
			result.append(value)

	return result

def read_json(path):
	f = open(path, 'r');
	result = None

	try:
		result = json.load(f);
	except:
		sublime.error_message("JsFormat Error.\nInvalid JSON: " + path)
	finally:
		f.close();

	return result

def augment_options(options, subset):
	"""	augment @options with defined values in @subset

		options -- a regular old class with public attributes
	   	subset -- anything with a 'get' callable (json style)
	"""
	fields = [attr for attr in dir(options) if not callable(getattr(options, attr)) and not attr.startswith("__")]

	for field in fields:
		value = subset.get(field)
		if value != None:
			setattr(options, field, value)

	return options

def augment_options_by_rc_files(options, view):
	fileName = view.file_name()

	if (fileName != None):
		files = filter_existing_files(get_rc_paths(os.path.dirname(fileName)))
		for value in files:
			jsonOptions = read_json(value)
			options = augment_options(options, jsonOptions)

	return options
########NEW FILE########
