__FILENAME__ = djangoutils
# -*- coding: utf-8 -*-
import hotshot
import os
import urllib
import time
from django.conf import settings
from django.template.loader import render_to_string
from django.core.urlresolvers import reverse
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from django.utils.html import urlize

# TODO: move this module to base app

def get_or_none(model, **kwargs):
    try:
        return model.objects.get(**kwargs)
    except model.DoesNotExist:
        return None

def get_query(params):
    if not params: return ""
    return "?" + "&".join(["%s=%s" % (key,
                                      urllib.quote(val.encode("utf-8")))
                           for key, val in params.iteritems()])

class Pagination(object):
    def __init__(self, paginator, page, link_name, link_kwargs, get_params):
        self.paginator = paginator
        self.page = page
        self.link_name = link_name
        self.link_kwargs = dict(link_kwargs)
        self.get_params = get_query(get_params)

    def link_with_page(self, page):
        self.link_kwargs["page"] = page
        return (reverse(self.link_name, kwargs=self.link_kwargs) +
                self.get_params)

    def render(self):
        num_pages = self.paginator.num_pages
        lo = max(1, self.page.number - settings.PAGINATOR_RANGE)
        hi = min(num_pages, self.page.number + settings.PAGINATOR_RANGE)
        links = [(page_no, self.link_with_page(page_no), page_no == self.page.number)
                 for page_no in xrange(lo, hi+1)]
        first = ({"link": self.link_with_page(1), "label": 1} if lo != 1 else None)
        last = ({"link": self.link_with_page(num_pages), "label": num_pages}
                if hi < num_pages else None)
        return render_to_string("pagination.html",
                                {"links": links, "first": first, "last": last})

    def __unicode__(self):
        return self.render()


def setup_paginator(objects, page, link_name, link_kwargs, get_params={}):
    paginator = Paginator(objects, settings.ITEMS_PER_PAGE)
    try:
        page = paginator.page(page)
    except PageNotAnInteger:
        page = paginator.page(1)
    except EmptyPage:
        page = paginator.page(paginator.num_pages)
    return Pagination(paginator, page, link_name, link_kwargs, get_params)

try:
    PROFILE_LOG_BASE = settings.PROFILE_LOG_BASE
except:
    PROFILE_LOG_BASE = None


def profile(log_file):
    """Profile some callable.

    This decorator uses the hotshot profiler to profile some callable (like
    a view function or method) and dumps the profile data somewhere sensible
    for later processing and examination.

    It takes one argument, the profile log name. If it's a relative path, it
    places it under the PROFILE_LOG_BASE. It also inserts a time stamp into the
    file name, such that 'my_view.prof' become 'my_view-20100211T170321.prof',
    where the time stamp is in UTC. This makes it easy to run and compare
    multiple trials.
    """

    if not PROFILE_LOG_BASE: return lambda f: f

    if not os.path.isabs(log_file):
        log_file = os.path.join(PROFILE_LOG_BASE, log_file)

    def _outer(f):
        def _inner(*args, **kwargs):
            # Add a timestamp to the profile output when the callable
            # is actually called.
            (base, ext) = os.path.splitext(log_file)
            base = base + "-" + time.strftime("%Y%m%dT%H%M%S", time.gmtime())
            final_log_file = base + ext

            prof = hotshot.Profile(final_log_file)
            try:
                ret = prof.runcall(f, *args, **kwargs)
            finally:
                prof.close()
            return ret

        return _inner
    return _outer


########NEW FILE########
__FILENAME__ = rendertext
# -*- coding: utf-8 -*-
import re
import string
import random
import misaka
from django.utils.html import escape
from pygments import highlight
from pygments.lexers import get_lexer_by_name, guess_lexer
from pygments.formatters import HtmlFormatter
from judge.utils import link_to_problem
from wiki.utils import link_to_page

def render_text(text):
    ext = misaka.EXT_NO_INTRA_EMPHASIS \
        | misaka.EXT_AUTOLINK \
        | misaka.EXT_FENCED_CODE \
        | misaka.EXT_TABLES \
        | misaka.EXT_STRIKETHROUGH \
        | misaka.EXT_SUPERSCRIPT \
        | misaka.EXT_SUBSCRIPT \
        | misaka.EXT_LAX_SPACING \
        | misaka.EXT_MATHJAX_SUPPORT
    render = misaka.HTML_HARD_WRAP \
            | misaka.HTML_TOC

    md = misaka.Markdown(CustomRenderer(render), \
            extensions = ext)

    return md.render(text)

def render_latex(text):
    ext = misaka.EXT_NO_INTRA_EMPHASIS \
        | misaka.EXT_AUTOLINK \
        | misaka.EXT_FENCED_CODE \
        | misaka.EXT_TABLES \
        | misaka.EXT_STRIKETHROUGH \
        | misaka.EXT_SUPERSCRIPT \
        | misaka.EXT_SUBSCRIPT \
        | misaka.EXT_LAX_SPACING \
        | misaka.EXT_MATHJAX_SUPPORT
    md = misaka.Markdown(AlgospotLatexRenderer(), \
            extensions = ext)
    
    return md.render(text)

def random_id(size):
    str = string.ascii_uppercase + string.ascii_lowercase + string.digits
    return ''.join(random.choice(str) for x in range(size))

class AlgospotLatexRenderer(misaka.BaseRenderer):
    def block_math(self, math):
        ret = "\\[\n"
        if text:
            ret += math
        ret += "\\]\n"
        return ret

    def block_code(self, text, lang):
        ret = "\\begin{lstlisting}"
        if lang:
            ret += "[language=" + lang + "]\n"
        else:
        	ret += "\n"
        if text:
            ret += text
        ret += "\\end{lstlisting}\n"
        return ret

    def block_quote(self, quote):
        ret = "\\begin{quote}\n"
        if quote:
            ret += quote + ""
        ret += "\\end{quote}\n"
        return ret

    def block_html(self, html):
        ret = "\\begin{lstlisting}\n"
        ret += "HTML Block here\n"
        if html:
            ret += html
        ret += "\\end{lstlisting}\n"
        return ret

    def header(self, text, level):
        grp = ''
        if level == 1:
            grp = 'section'
        elif level == 2:
            grp = 'subsection'
        else:
            grp = 'subsubsection'
        ret = "\\" + grp + "{"
        if text:
            ret += text
        ret += "}\n"
        return ret

    def hrule(self):
        return "\n\n\\hrule\n\n"

    def list(self, contents, is_ordered):
        env_name = is_ordered and 'enumerate' or 'itemize'
        ret = "\\begin{" + env_name + "}\n"
        if contents:
            ret += contents + "\n"
        ret += "\\end{" + env_name + "}\n"
        return ret

    def list_item(self, text, is_ordered):
        return "\\item " + text or '' + "\n"

    def paragraph(self, text):
        return text + "\n\n";

    def table(self, header, body):
        ret = "\\begin{center}\n\\begin{tabular}\n"
        if header:
            ret += header + "\n"
        if body:
            ret += body + "\n"
        ret += "\\end{tabular}\n\\end{center}\n"
        return ret

    def table_row(self, content):
        return re.sub(r' & $', '', content or '') + "\\\\"

    def table_cell(self, content, flags):
        return (content or '') + ' & '

    def autolink(self, link, is_email):
        return "\\url{" + (link or '') + "}"

    def codespan(self, code):
        return "\\lstinline|" + (code or '') + "|"

    def mathspan(self, math):
        return "$" + (math or '') + "$"

    def double_emphasis(self, text):
        return "\\textbf{" + (text or '') + "}"

    def emphasis(self, text):
        return "\\textit{" + (text or '') + "}"

    def image(self, link, title, alt_text):
        ret = "\colorbox{SkyBlue}{IMAGE HERE}"
        return ret

    def linebreak(self):
        return "\n\n"

    def link(self, link, title, content):
        return "\colorbox{Thistle}{LINK HERE}"

    def raw_html(self, raw_html):
        return "\colorbox{GreenYellow}{SOME RAW HTML}"

    def triple_emphasis(self, text):
        return "\\textit{\\textbf{" + (text or '') + "}}"

    def strikethrough(self, text):
        return "\\sout{" + (text or '') + "}"

    def superscript(self, text):
        return "$^{" + (text or '').replace("\\{", "").replace("\\}", "") + "}$"

    def subscript(self, text):
        return "$_{" + (text or '').replace("\\{", "").replace("\\}", "") + "}$"

    def entity(self, text):
        return text

    def normal_text(self, text):
        return text.replace('$', "\\$") \
                   .replace('#', "\\#") \
                   .replace('%', "\\%") \
                   .replace('&', "\\&") \
                   .replace('_', "\\_") \
                   .replace('{', "\\{") \
                   .replace('}', "\\}") \
                   .replace('^', "\\^{}") \
                   .replace('~', "\\~{}") \
                   .replace('. ', ".\n") # adding some line breaks

class CustomRenderer(misaka.HtmlRenderer):
    LINK_REGEX = re.compile("\[\[(?:([^|\]]+)\|)?(?:([^:\]]+):)?([^\]]+)\]\]")

    def preprocess(self, doc):
        while True:
            self.spoiler_open_key = '{{%s}}' % random_id(16)
            if doc.find(self.spoiler_open_key) != -1:
                continue
            self.spoiler_close_key = '{{%s}}' % random_id(16)
            if self.spoiler_open_key == self.spoiler_close_key or doc.find(self.spoiler_close_key) != -1:
                continue
            break
        doc = self.substitute_spoiler_tags(doc)
        doc = self.link_to_entities(doc)
        return doc
    def postprocess(self, doc):
        doc = self.revert_spoiler_tags(doc)
        return doc
    def block_code(self, text, lang):
        text = text.replace('\t', '  ')
        try:
            lexer = get_lexer_by_name(lang, stripall=False)
        except:
            if lang:
                return u'\n<pre><code># 지정된 언어 %s를 찾을 수 없습니다.<br>%s</code></pre>\n' % \
                    (lang, escape(text.strip()))
            else:
                return u'\n<pre><code>%s</code></pre>\n' % \
                    escape(text.strip())
        formatter = HtmlFormatter(style='colorful')
        return highlight(text, lexer, formatter)
    def substitute_spoiler_tags(self, doc):
        doc = doc.replace('<spoiler>', self.spoiler_open_key + "\n")
        doc = doc.replace('</spoiler>', "\n" + self.spoiler_close_key)
        return doc
    def revert_spoiler_tags(self, doc):
        doc = doc.replace(self.spoiler_open_key, '<div class="spoiler">')
        doc = doc.replace(self.spoiler_close_key, '</div>')
        return doc
    def link_to_entities(self, doc):
        def replace(match):
            display = match.group(1)
            namespace = match.group(2) or ''
            title = match.group(3)
            try:
                if namespace == 'problem':
                    return link_to_problem(title, display)
                elif namespace == '':
                    return link_to_page(title, display)
            except:
                return match.group(0)
        return self.LINK_REGEX.sub(replace, doc)

########NEW FILE########
__FILENAME__ = diff_match_patch
#!/usr/bin/python2.4

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
import time
import urllib
import re
import sys

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
    # When deleting a large block of text (over ~64 characters), how close does
    # the contents have to match the expected contents. (0.0 = perfection,
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
    longtext = shorttext = None  # Garbage collect.

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
    max_d = (text1_length + text2_length + 1) / 2
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
        if (k1 == -d or k1 != d and
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
        if (k2 == -d or k2 != d and
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
      pointermid = int((pointermax - pointermin) / 2 + pointermin)
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
      pointermid = int((pointermax - pointermin) / 2 + pointermin)
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
      seed = longtext[i:i + len(longtext) / 4]
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
    hm1 = diff_halfMatchI(longtext, shorttext, (len(longtext) + 3) / 4)
    # Check again based on the third quarter.
    hm2 = diff_halfMatchI(longtext, shorttext, (len(longtext) + 1) / 2)
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
    lastequality = None  # Always equal to equalities[-1][1]
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
        if (lastequality != None and (len(lastequality) <=
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
    # Only extract an overlap if it is as big as the edit ahead or behind it.
    pointer = 1
    while pointer < len(diffs):
      if (diffs[pointer - 1][0] == self.DIFF_DELETE and
          diffs[pointer][0] == self.DIFF_INSERT):
        deletion = diffs[pointer - 1][1]
        insertion = diffs[pointer][1]
        overlap_length = self.diff_commonOverlap(deletion, insertion)
        if (overlap_length >= len(deletion) / 2.0 or
            overlap_length >= len(insertion) / 2.0):
          # Overlap found.  Insert an equality and trim the surrounding edits.
          diffs.insert(pointer, (self.DIFF_EQUAL, insertion[:overlap_length]))
          diffs[pointer - 1] = (self.DIFF_DELETE,
                                deletion[:len(deletion) - overlap_length])
          diffs[pointer + 1] = (self.DIFF_INSERT, insertion[overlap_length:])
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
      Scores range from 5 (best) to 0 (worst).
      Closure, but does not reference any external variables.

      Args:
        one: First string.
        two: Second string.

      Returns:
        The score.
      """
      if not one or not two:
        # Edges are the best.
        return 5

      # Each port of this function behaves slightly differently due to
      # subtle differences in each language's definition of things like
      # 'whitespace'.  Since this function's purpose is largely cosmetic,
      # the choice has been made to use each language's native features
      # rather than force total conformity.
      score = 0
      # One point for non-alphanumeric.
      if not one[-1].isalnum() or not two[0].isalnum():
        score += 1
        # Two points for whitespace.
        if one[-1].isspace() or two[0].isspace():
          score += 1
          # Three points for line breaks.
          if (one[-1] == "\r" or one[-1] == "\n" or
              two[0] == "\r" or two[0] == "\n"):
            score += 1
            # Four points for blank lines.
            if (re.search("\\n\\r?\\n$", one) or
                re.match("^\\r?\\n\\r?\\n", two)):
              score += 1
      return score

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

  def diff_cleanupEfficiency(self, diffs):
    """Reduce the number of edits by eliminating operationally trivial
    equalities.

    Args:
      diffs: Array of diff tuples.
    """
    changes = False
    equalities = []  # Stack of indices where equalities are found.
    lastequality = ''  # Always equal to equalities[-1][1]
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
          lastequality = ''

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
          lastequality = ''
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
    i = 0
    for (op, data) in diffs:
      text = (data.replace("&", "&amp;").replace("<", "&lt;")
                 .replace(">", "&gt;").replace("\n", "&para;<br>"))
      if op == self.DIFF_INSERT:
        html.append("<ins style=\"background:#e6ffe6;\">%s</ins>" % text)
      elif op == self.DIFF_DELETE:
        html.append("<del style=\"background:#ffe6e6;\">%s</del>" % text)
      elif op == self.DIFF_EQUAL:
        html.append("<span>%s</span>" % text)
      if op != self.DIFF_DELETE:
        i += len(data)
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
        bin_mid = (bin_max - bin_min) / 2 + bin_min

      # Use the result from this iteration as the maximum for the next.
      bin_max = bin_mid
      start = max(1, loc - bin_mid + 1)
      finish = min(loc + bin_mid, len(text)) + len(pattern)

      rd = range(finish + 1)
      rd.append((1 << d) - 1)
      for j in xrange(finish, start - 1, -1):
        if len(text) <= j - 1:
          # Out of range.
          charMatch = 0
        else:
          charMatch = s.get(text[j - 1], 0)
        if d == 0:  # First pass: exact match.
          rd[j] = ((rd[j + 1] << 1) | 1) & charMatch
        else:  # Subsequent passes: fuzzy match.
          rd[j] = ((rd[j + 1] << 1) | 1) & charMatch | (
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
      Array of patch objects.
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
      patches: Array of patch objects.

    Returns:
      Array of patch objects.
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
      patches: Array of patch objects.
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
      patches: Array of patch objects.

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
      patches: Array of patch objects.
    """
    patch_size = self.Match_MaxBits
    if patch_size == 0:
      # Python has the option of not splitting strings due to its ability
      # to handle integers of arbitrary precision.
      return
    for x in xrange(len(patches)):
      if patches[x].length1 > patch_size:
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
      patches: Array of patch objects.

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
      Array of patch objects.

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
__FILENAME__ = diff_match_patch_test
#!/usr/bin/python2.4

"""Test harness for diff_match_patch.py

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

import sys
import time
import unittest
import diff_match_patch as dmp_module
# Force a module reload.  Allows one to edit the DMP module and rerun the tests
# without leaving the Python interpreter.
reload(dmp_module)

class DiffMatchPatchTest(unittest.TestCase):

  def setUp(self):
    "Test harness for dmp_module."
    self.dmp = dmp_module.diff_match_patch()

  def diff_rebuildtexts(self, diffs):
    # Construct the two texts which made up the diff originally.
    text1 = ""
    text2 = ""
    for x in xrange(0, len(diffs)):
      if diffs[x][0] != dmp_module.diff_match_patch.DIFF_INSERT:
        text1 += diffs[x][1]
      if diffs[x][0] != dmp_module.diff_match_patch.DIFF_DELETE:
        text2 += diffs[x][1]
    return (text1, text2)


class DiffTest(DiffMatchPatchTest):
  """DIFF TEST FUNCTIONS"""

  def testDiffCommonPrefix(self):
    # Detect any common prefix.
    # Null case.
    self.assertEquals(0, self.dmp.diff_commonPrefix("abc", "xyz"))

    # Non-null case.
    self.assertEquals(4, self.dmp.diff_commonPrefix("1234abcdef", "1234xyz"))

    # Whole case.
    self.assertEquals(4, self.dmp.diff_commonPrefix("1234", "1234xyz"))

  def testDiffCommonSuffix(self):
    # Detect any common suffix.
    # Null case.
    self.assertEquals(0, self.dmp.diff_commonSuffix("abc", "xyz"))

    # Non-null case.
    self.assertEquals(4, self.dmp.diff_commonSuffix("abcdef1234", "xyz1234"))

    # Whole case.
    self.assertEquals(4, self.dmp.diff_commonSuffix("1234", "xyz1234"))

  def testDiffCommonOverlap(self):
    # Null case.
    self.assertEquals(0, self.dmp.diff_commonOverlap("", "abcd"))

    # Whole case.
    self.assertEquals(3, self.dmp.diff_commonOverlap("abc", "abcd"))

    # No overlap.
    self.assertEquals(0, self.dmp.diff_commonOverlap("123456", "abcd"))

    # Overlap.
    self.assertEquals(3, self.dmp.diff_commonOverlap("123456xxx", "xxxabcd"))

  def testDiffHalfMatch(self):
    # Detect a halfmatch.
    self.dmp.Diff_Timeout = 1
    # No match.
    self.assertEquals(None, self.dmp.diff_halfMatch("1234567890", "abcdef"))

    self.assertEquals(None, self.dmp.diff_halfMatch("12345", "23"))

    # Single Match.
    self.assertEquals(("12", "90", "a", "z", "345678"), self.dmp.diff_halfMatch("1234567890", "a345678z"))

    self.assertEquals(("a", "z", "12", "90", "345678"), self.dmp.diff_halfMatch("a345678z", "1234567890"))

    self.assertEquals(("abc", "z", "1234", "0", "56789"), self.dmp.diff_halfMatch("abc56789z", "1234567890"))

    self.assertEquals(("a", "xyz", "1", "7890", "23456"), self.dmp.diff_halfMatch("a23456xyz", "1234567890"))

    # Multiple Matches.
    self.assertEquals(("12123", "123121", "a", "z", "1234123451234"), self.dmp.diff_halfMatch("121231234123451234123121", "a1234123451234z"))

    self.assertEquals(("", "-=-=-=-=-=", "x", "", "x-=-=-=-=-=-=-="), self.dmp.diff_halfMatch("x-=-=-=-=-=-=-=-=-=-=-=-=", "xx-=-=-=-=-=-=-="))

    self.assertEquals(("-=-=-=-=-=", "", "", "y", "-=-=-=-=-=-=-=y"), self.dmp.diff_halfMatch("-=-=-=-=-=-=-=-=-=-=-=-=y", "-=-=-=-=-=-=-=yy"))

    # Non-optimal halfmatch.
    # Optimal diff would be -q+x=H-i+e=lloHe+Hu=llo-Hew+y not -qHillo+x=HelloHe-w+Hulloy
    self.assertEquals(("qHillo", "w", "x", "Hulloy", "HelloHe"), self.dmp.diff_halfMatch("qHilloHelloHew", "xHelloHeHulloy"))

    # Optimal no halfmatch.
    self.dmp.Diff_Timeout = 0
    self.assertEquals(None, self.dmp.diff_halfMatch("qHilloHelloHew", "xHelloHeHulloy"))

  def testDiffLinesToChars(self):
    # Convert lines down to characters.
    self.assertEquals(("\x01\x02\x01", "\x02\x01\x02", ["", "alpha\n", "beta\n"]), self.dmp.diff_linesToChars("alpha\nbeta\nalpha\n", "beta\nalpha\nbeta\n"))

    self.assertEquals(("", "\x01\x02\x03\x03", ["", "alpha\r\n", "beta\r\n", "\r\n"]), self.dmp.diff_linesToChars("", "alpha\r\nbeta\r\n\r\n\r\n"))

    self.assertEquals(("\x01", "\x02", ["", "a", "b"]), self.dmp.diff_linesToChars("a", "b"))

    # More than 256 to reveal any 8-bit limitations.
    n = 300
    lineList = []
    charList = []
    for x in range(1, n + 1):
      lineList.append(str(x) + "\n")
      charList.append(unichr(x))
    self.assertEquals(n, len(lineList))
    lines = "".join(lineList)
    chars = "".join(charList)
    self.assertEquals(n, len(chars))
    lineList.insert(0, "")
    self.assertEquals((chars, "", lineList), self.dmp.diff_linesToChars(lines, ""))

  def testDiffCharsToLines(self):
    # Convert chars up to lines.
    diffs = [(self.dmp.DIFF_EQUAL, "\x01\x02\x01"), (self.dmp.DIFF_INSERT, "\x02\x01\x02")]
    self.dmp.diff_charsToLines(diffs, ["", "alpha\n", "beta\n"])
    self.assertEquals([(self.dmp.DIFF_EQUAL, "alpha\nbeta\nalpha\n"), (self.dmp.DIFF_INSERT, "beta\nalpha\nbeta\n")], diffs)

    # More than 256 to reveal any 8-bit limitations.
    n = 300
    lineList = []
    charList = []
    for x in range(1, n + 1):
      lineList.append(str(x) + "\n")
      charList.append(unichr(x))
    self.assertEquals(n, len(lineList))
    lines = "".join(lineList)
    chars = "".join(charList)
    self.assertEquals(n, len(chars))
    lineList.insert(0, "")
    diffs = [(self.dmp.DIFF_DELETE, chars)]
    self.dmp.diff_charsToLines(diffs, lineList)
    self.assertEquals([(self.dmp.DIFF_DELETE, lines)], diffs)

  def testDiffCleanupMerge(self):
    # Cleanup a messy diff.
    # Null case.
    diffs = []
    self.dmp.diff_cleanupMerge(diffs)
    self.assertEquals([], diffs)

    # No change case.
    diffs = [(self.dmp.DIFF_EQUAL, "a"), (self.dmp.DIFF_DELETE, "b"), (self.dmp.DIFF_INSERT, "c")]
    self.dmp.diff_cleanupMerge(diffs)
    self.assertEquals([(self.dmp.DIFF_EQUAL, "a"), (self.dmp.DIFF_DELETE, "b"), (self.dmp.DIFF_INSERT, "c")], diffs)

    # Merge equalities.
    diffs = [(self.dmp.DIFF_EQUAL, "a"), (self.dmp.DIFF_EQUAL, "b"), (self.dmp.DIFF_EQUAL, "c")]
    self.dmp.diff_cleanupMerge(diffs)
    self.assertEquals([(self.dmp.DIFF_EQUAL, "abc")], diffs)

    # Merge deletions.
    diffs = [(self.dmp.DIFF_DELETE, "a"), (self.dmp.DIFF_DELETE, "b"), (self.dmp.DIFF_DELETE, "c")]
    self.dmp.diff_cleanupMerge(diffs)
    self.assertEquals([(self.dmp.DIFF_DELETE, "abc")], diffs)

    # Merge insertions.
    diffs = [(self.dmp.DIFF_INSERT, "a"), (self.dmp.DIFF_INSERT, "b"), (self.dmp.DIFF_INSERT, "c")]
    self.dmp.diff_cleanupMerge(diffs)
    self.assertEquals([(self.dmp.DIFF_INSERT, "abc")], diffs)

    # Merge interweave.
    diffs = [(self.dmp.DIFF_DELETE, "a"), (self.dmp.DIFF_INSERT, "b"), (self.dmp.DIFF_DELETE, "c"), (self.dmp.DIFF_INSERT, "d"), (self.dmp.DIFF_EQUAL, "e"), (self.dmp.DIFF_EQUAL, "f")]
    self.dmp.diff_cleanupMerge(diffs)
    self.assertEquals([(self.dmp.DIFF_DELETE, "ac"), (self.dmp.DIFF_INSERT, "bd"), (self.dmp.DIFF_EQUAL, "ef")], diffs)

    # Prefix and suffix detection.
    diffs = [(self.dmp.DIFF_DELETE, "a"), (self.dmp.DIFF_INSERT, "abc"), (self.dmp.DIFF_DELETE, "dc")]
    self.dmp.diff_cleanupMerge(diffs)
    self.assertEquals([(self.dmp.DIFF_EQUAL, "a"), (self.dmp.DIFF_DELETE, "d"), (self.dmp.DIFF_INSERT, "b"), (self.dmp.DIFF_EQUAL, "c")], diffs)

    # Prefix and suffix detection with equalities.
    diffs = [(self.dmp.DIFF_EQUAL, "x"), (self.dmp.DIFF_DELETE, "a"), (self.dmp.DIFF_INSERT, "abc"), (self.dmp.DIFF_DELETE, "dc"), (self.dmp.DIFF_EQUAL, "y")]
    self.dmp.diff_cleanupMerge(diffs)
    self.assertEquals([(self.dmp.DIFF_EQUAL, "xa"), (self.dmp.DIFF_DELETE, "d"), (self.dmp.DIFF_INSERT, "b"), (self.dmp.DIFF_EQUAL, "cy")], diffs)

    # Slide edit left.
    diffs = [(self.dmp.DIFF_EQUAL, "a"), (self.dmp.DIFF_INSERT, "ba"), (self.dmp.DIFF_EQUAL, "c")]
    self.dmp.diff_cleanupMerge(diffs)
    self.assertEquals([(self.dmp.DIFF_INSERT, "ab"), (self.dmp.DIFF_EQUAL, "ac")], diffs)

    # Slide edit right.
    diffs = [(self.dmp.DIFF_EQUAL, "c"), (self.dmp.DIFF_INSERT, "ab"), (self.dmp.DIFF_EQUAL, "a")]
    self.dmp.diff_cleanupMerge(diffs)
    self.assertEquals([(self.dmp.DIFF_EQUAL, "ca"), (self.dmp.DIFF_INSERT, "ba")], diffs)

    # Slide edit left recursive.
    diffs = [(self.dmp.DIFF_EQUAL, "a"), (self.dmp.DIFF_DELETE, "b"), (self.dmp.DIFF_EQUAL, "c"), (self.dmp.DIFF_DELETE, "ac"), (self.dmp.DIFF_EQUAL, "x")]
    self.dmp.diff_cleanupMerge(diffs)
    self.assertEquals([(self.dmp.DIFF_DELETE, "abc"), (self.dmp.DIFF_EQUAL, "acx")], diffs)

    # Slide edit right recursive.
    diffs = [(self.dmp.DIFF_EQUAL, "x"), (self.dmp.DIFF_DELETE, "ca"), (self.dmp.DIFF_EQUAL, "c"), (self.dmp.DIFF_DELETE, "b"), (self.dmp.DIFF_EQUAL, "a")]
    self.dmp.diff_cleanupMerge(diffs)
    self.assertEquals([(self.dmp.DIFF_EQUAL, "xca"), (self.dmp.DIFF_DELETE, "cba")], diffs)

  def testDiffCleanupSemanticLossless(self):
    # Slide diffs to match logical boundaries.
    # Null case.
    diffs = []
    self.dmp.diff_cleanupSemanticLossless(diffs)
    self.assertEquals([], diffs)

    # Blank lines.
    diffs = [(self.dmp.DIFF_EQUAL, "AAA\r\n\r\nBBB"), (self.dmp.DIFF_INSERT, "\r\nDDD\r\n\r\nBBB"), (self.dmp.DIFF_EQUAL, "\r\nEEE")]
    self.dmp.diff_cleanupSemanticLossless(diffs)
    self.assertEquals([(self.dmp.DIFF_EQUAL, "AAA\r\n\r\n"), (self.dmp.DIFF_INSERT, "BBB\r\nDDD\r\n\r\n"), (self.dmp.DIFF_EQUAL, "BBB\r\nEEE")], diffs)

    # Line boundaries.
    diffs = [(self.dmp.DIFF_EQUAL, "AAA\r\nBBB"), (self.dmp.DIFF_INSERT, " DDD\r\nBBB"), (self.dmp.DIFF_EQUAL, " EEE")]
    self.dmp.diff_cleanupSemanticLossless(diffs)
    self.assertEquals([(self.dmp.DIFF_EQUAL, "AAA\r\n"), (self.dmp.DIFF_INSERT, "BBB DDD\r\n"), (self.dmp.DIFF_EQUAL, "BBB EEE")], diffs)

    # Word boundaries.
    diffs = [(self.dmp.DIFF_EQUAL, "The c"), (self.dmp.DIFF_INSERT, "ow and the c"), (self.dmp.DIFF_EQUAL, "at.")]
    self.dmp.diff_cleanupSemanticLossless(diffs)
    self.assertEquals([(self.dmp.DIFF_EQUAL, "The "), (self.dmp.DIFF_INSERT, "cow and the "), (self.dmp.DIFF_EQUAL, "cat.")], diffs)

    # Alphanumeric boundaries.
    diffs = [(self.dmp.DIFF_EQUAL, "The-c"), (self.dmp.DIFF_INSERT, "ow-and-the-c"), (self.dmp.DIFF_EQUAL, "at.")]
    self.dmp.diff_cleanupSemanticLossless(diffs)
    self.assertEquals([(self.dmp.DIFF_EQUAL, "The-"), (self.dmp.DIFF_INSERT, "cow-and-the-"), (self.dmp.DIFF_EQUAL, "cat.")], diffs)

    # Hitting the start.
    diffs = [(self.dmp.DIFF_EQUAL, "a"), (self.dmp.DIFF_DELETE, "a"), (self.dmp.DIFF_EQUAL, "ax")]
    self.dmp.diff_cleanupSemanticLossless(diffs)
    self.assertEquals([(self.dmp.DIFF_DELETE, "a"), (self.dmp.DIFF_EQUAL, "aax")], diffs)

    # Hitting the end.
    diffs = [(self.dmp.DIFF_EQUAL, "xa"), (self.dmp.DIFF_DELETE, "a"), (self.dmp.DIFF_EQUAL, "a")]
    self.dmp.diff_cleanupSemanticLossless(diffs)
    self.assertEquals([(self.dmp.DIFF_EQUAL, "xaa"), (self.dmp.DIFF_DELETE, "a")], diffs)

  def testDiffCleanupSemantic(self):
    # Cleanup semantically trivial equalities.
    # Null case.
    diffs = []
    self.dmp.diff_cleanupSemantic(diffs)
    self.assertEquals([], diffs)

    # No elimination #1.
    diffs = [(self.dmp.DIFF_DELETE, "ab"), (self.dmp.DIFF_INSERT, "cd"), (self.dmp.DIFF_EQUAL, "12"), (self.dmp.DIFF_DELETE, "e")]
    self.dmp.diff_cleanupSemantic(diffs)
    self.assertEquals([(self.dmp.DIFF_DELETE, "ab"), (self.dmp.DIFF_INSERT, "cd"), (self.dmp.DIFF_EQUAL, "12"), (self.dmp.DIFF_DELETE, "e")], diffs)

    # No elimination #2.
    diffs = [(self.dmp.DIFF_DELETE, "abc"), (self.dmp.DIFF_INSERT, "ABC"), (self.dmp.DIFF_EQUAL, "1234"), (self.dmp.DIFF_DELETE, "wxyz")]
    self.dmp.diff_cleanupSemantic(diffs)
    self.assertEquals([(self.dmp.DIFF_DELETE, "abc"), (self.dmp.DIFF_INSERT, "ABC"), (self.dmp.DIFF_EQUAL, "1234"), (self.dmp.DIFF_DELETE, "wxyz")], diffs)

    # Simple elimination.
    diffs = [(self.dmp.DIFF_DELETE, "a"), (self.dmp.DIFF_EQUAL, "b"), (self.dmp.DIFF_DELETE, "c")]
    self.dmp.diff_cleanupSemantic(diffs)
    self.assertEquals([(self.dmp.DIFF_DELETE, "abc"), (self.dmp.DIFF_INSERT, "b")], diffs)

    # Backpass elimination.
    diffs = [(self.dmp.DIFF_DELETE, "ab"), (self.dmp.DIFF_EQUAL, "cd"), (self.dmp.DIFF_DELETE, "e"), (self.dmp.DIFF_EQUAL, "f"), (self.dmp.DIFF_INSERT, "g")]
    self.dmp.diff_cleanupSemantic(diffs)
    self.assertEquals([(self.dmp.DIFF_DELETE, "abcdef"), (self.dmp.DIFF_INSERT, "cdfg")], diffs)

    # Multiple eliminations.
    diffs = [(self.dmp.DIFF_INSERT, "1"), (self.dmp.DIFF_EQUAL, "A"), (self.dmp.DIFF_DELETE, "B"), (self.dmp.DIFF_INSERT, "2"), (self.dmp.DIFF_EQUAL, "_"), (self.dmp.DIFF_INSERT, "1"), (self.dmp.DIFF_EQUAL, "A"), (self.dmp.DIFF_DELETE, "B"), (self.dmp.DIFF_INSERT, "2")]
    self.dmp.diff_cleanupSemantic(diffs)
    self.assertEquals([(self.dmp.DIFF_DELETE, "AB_AB"), (self.dmp.DIFF_INSERT, "1A2_1A2")], diffs)

    # Word boundaries.
    diffs = [(self.dmp.DIFF_EQUAL, "The c"), (self.dmp.DIFF_DELETE, "ow and the c"), (self.dmp.DIFF_EQUAL, "at.")]
    self.dmp.diff_cleanupSemantic(diffs)
    self.assertEquals([(self.dmp.DIFF_EQUAL, "The "), (self.dmp.DIFF_DELETE, "cow and the "), (self.dmp.DIFF_EQUAL, "cat.")], diffs)

    # No overlap elimination.
    diffs = [(self.dmp.DIFF_DELETE, "abcxx"), (self.dmp.DIFF_INSERT, "xxdef")]
    self.dmp.diff_cleanupSemantic(diffs)
    self.assertEquals([(self.dmp.DIFF_DELETE, "abcxx"), (self.dmp.DIFF_INSERT, "xxdef")], diffs)

    # Overlap elimination.
    diffs = [(self.dmp.DIFF_DELETE, "abcxxx"), (self.dmp.DIFF_INSERT, "xxxdef")]
    self.dmp.diff_cleanupSemantic(diffs)
    self.assertEquals([(self.dmp.DIFF_DELETE, "abc"), (self.dmp.DIFF_EQUAL, "xxx"), (self.dmp.DIFF_INSERT, "def")], diffs)

    # Two overlap eliminations.
    diffs = [(self.dmp.DIFF_DELETE, "abcd1212"), (self.dmp.DIFF_INSERT, "1212efghi"), (self.dmp.DIFF_EQUAL, "----"), (self.dmp.DIFF_DELETE, "A3"), (self.dmp.DIFF_INSERT, "3BC")]
    self.dmp.diff_cleanupSemantic(diffs)
    self.assertEquals([(self.dmp.DIFF_DELETE, "abcd"), (self.dmp.DIFF_EQUAL, "1212"), (self.dmp.DIFF_INSERT, "efghi"), (self.dmp.DIFF_EQUAL, "----"), (self.dmp.DIFF_DELETE, "A"), (self.dmp.DIFF_EQUAL, "3"), (self.dmp.DIFF_INSERT, "BC")], diffs)

  def testDiffCleanupEfficiency(self):
    # Cleanup operationally trivial equalities.
    self.dmp.Diff_EditCost = 4
    # Null case.
    diffs = []
    self.dmp.diff_cleanupEfficiency(diffs)
    self.assertEquals([], diffs)

    # No elimination.
    diffs = [(self.dmp.DIFF_DELETE, "ab"), (self.dmp.DIFF_INSERT, "12"), (self.dmp.DIFF_EQUAL, "wxyz"), (self.dmp.DIFF_DELETE, "cd"), (self.dmp.DIFF_INSERT, "34")]
    self.dmp.diff_cleanupEfficiency(diffs)
    self.assertEquals([(self.dmp.DIFF_DELETE, "ab"), (self.dmp.DIFF_INSERT, "12"), (self.dmp.DIFF_EQUAL, "wxyz"), (self.dmp.DIFF_DELETE, "cd"), (self.dmp.DIFF_INSERT, "34")], diffs)

    # Four-edit elimination.
    diffs = [(self.dmp.DIFF_DELETE, "ab"), (self.dmp.DIFF_INSERT, "12"), (self.dmp.DIFF_EQUAL, "xyz"), (self.dmp.DIFF_DELETE, "cd"), (self.dmp.DIFF_INSERT, "34")]
    self.dmp.diff_cleanupEfficiency(diffs)
    self.assertEquals([(self.dmp.DIFF_DELETE, "abxyzcd"), (self.dmp.DIFF_INSERT, "12xyz34")], diffs)

    # Three-edit elimination.
    diffs = [(self.dmp.DIFF_INSERT, "12"), (self.dmp.DIFF_EQUAL, "x"), (self.dmp.DIFF_DELETE, "cd"), (self.dmp.DIFF_INSERT, "34")]
    self.dmp.diff_cleanupEfficiency(diffs)
    self.assertEquals([(self.dmp.DIFF_DELETE, "xcd"), (self.dmp.DIFF_INSERT, "12x34")], diffs)

    # Backpass elimination.
    diffs = [(self.dmp.DIFF_DELETE, "ab"), (self.dmp.DIFF_INSERT, "12"), (self.dmp.DIFF_EQUAL, "xy"), (self.dmp.DIFF_INSERT, "34"), (self.dmp.DIFF_EQUAL, "z"), (self.dmp.DIFF_DELETE, "cd"), (self.dmp.DIFF_INSERT, "56")]
    self.dmp.diff_cleanupEfficiency(diffs)
    self.assertEquals([(self.dmp.DIFF_DELETE, "abxyzcd"), (self.dmp.DIFF_INSERT, "12xy34z56")], diffs)

    # High cost elimination.
    self.dmp.Diff_EditCost = 5
    diffs = [(self.dmp.DIFF_DELETE, "ab"), (self.dmp.DIFF_INSERT, "12"), (self.dmp.DIFF_EQUAL, "wxyz"), (self.dmp.DIFF_DELETE, "cd"), (self.dmp.DIFF_INSERT, "34")]
    self.dmp.diff_cleanupEfficiency(diffs)
    self.assertEquals([(self.dmp.DIFF_DELETE, "abwxyzcd"), (self.dmp.DIFF_INSERT, "12wxyz34")], diffs)
    self.dmp.Diff_EditCost = 4

  def testDiffPrettyHtml(self):
    # Pretty print.
    diffs = [(self.dmp.DIFF_EQUAL, "a\n"), (self.dmp.DIFF_DELETE, "<B>b</B>"), (self.dmp.DIFF_INSERT, "c&d")]
    self.assertEquals("<span>a&para;<br></span><del style=\"background:#ffe6e6;\">&lt;B&gt;b&lt;/B&gt;</del><ins style=\"background:#e6ffe6;\">c&amp;d</ins>", self.dmp.diff_prettyHtml(diffs))

  def testDiffText(self):
    # Compute the source and destination texts.
    diffs = [(self.dmp.DIFF_EQUAL, "jump"), (self.dmp.DIFF_DELETE, "s"), (self.dmp.DIFF_INSERT, "ed"), (self.dmp.DIFF_EQUAL, " over "), (self.dmp.DIFF_DELETE, "the"), (self.dmp.DIFF_INSERT, "a"), (self.dmp.DIFF_EQUAL, " lazy")]
    self.assertEquals("jumps over the lazy", self.dmp.diff_text1(diffs))

    self.assertEquals("jumped over a lazy", self.dmp.diff_text2(diffs))

  def testDiffDelta(self):
    # Convert a diff into delta string.
    diffs = [(self.dmp.DIFF_EQUAL, "jump"), (self.dmp.DIFF_DELETE, "s"), (self.dmp.DIFF_INSERT, "ed"), (self.dmp.DIFF_EQUAL, " over "), (self.dmp.DIFF_DELETE, "the"), (self.dmp.DIFF_INSERT, "a"), (self.dmp.DIFF_EQUAL, " lazy"), (self.dmp.DIFF_INSERT, "old dog")]
    text1 = self.dmp.diff_text1(diffs)
    self.assertEquals("jumps over the lazy", text1)

    delta = self.dmp.diff_toDelta(diffs)
    self.assertEquals("=4\t-1\t+ed\t=6\t-3\t+a\t=5\t+old dog", delta)

    # Convert delta string into a diff.
    self.assertEquals(diffs, self.dmp.diff_fromDelta(text1, delta))

    # Generates error (19 != 20).
    try:
      self.dmp.diff_fromDelta(text1 + "x", delta)
      self.assertFalse(True)
    except ValueError:
      # Exception expected.
      pass

    # Generates error (19 != 18).
    try:
      self.dmp.diff_fromDelta(text1[1:], delta)
      self.assertFalse(True)
    except ValueError:
      # Exception expected.
      pass

    # Generates error (%c3%xy invalid Unicode).
    try:
      self.dmp.diff_fromDelta("", "+%c3xy")
      self.assertFalse(True)
    except ValueError:
      # Exception expected.
      pass

    # Test deltas with special characters.
    diffs = [(self.dmp.DIFF_EQUAL, u"\u0680 \x00 \t %"), (self.dmp.DIFF_DELETE, u"\u0681 \x01 \n ^"), (self.dmp.DIFF_INSERT, u"\u0682 \x02 \\ |")]
    text1 = self.dmp.diff_text1(diffs)
    self.assertEquals(u"\u0680 \x00 \t %\u0681 \x01 \n ^", text1)

    delta = self.dmp.diff_toDelta(diffs)
    self.assertEquals("=7\t-7\t+%DA%82 %02 %5C %7C", delta)

    # Convert delta string into a diff.
    self.assertEquals(diffs, self.dmp.diff_fromDelta(text1, delta))

    # Verify pool of unchanged characters.
    diffs = [(self.dmp.DIFF_INSERT, "A-Z a-z 0-9 - _ . ! ~ * ' ( ) ; / ? : @ & = + $ , # ")]
    text2 = self.dmp.diff_text2(diffs)
    self.assertEquals("A-Z a-z 0-9 - _ . ! ~ * \' ( ) ; / ? : @ & = + $ , # ", text2)

    delta = self.dmp.diff_toDelta(diffs)
    self.assertEquals("+A-Z a-z 0-9 - _ . ! ~ * \' ( ) ; / ? : @ & = + $ , # ", delta)

    # Convert delta string into a diff.
    self.assertEquals(diffs, self.dmp.diff_fromDelta("", delta))

  def testDiffXIndex(self):
    # Translate a location in text1 to text2.
    self.assertEquals(5, self.dmp.diff_xIndex([(self.dmp.DIFF_DELETE, "a"), (self.dmp.DIFF_INSERT, "1234"), (self.dmp.DIFF_EQUAL, "xyz")], 2))

    # Translation on deletion.
    self.assertEquals(1, self.dmp.diff_xIndex([(self.dmp.DIFF_EQUAL, "a"), (self.dmp.DIFF_DELETE, "1234"), (self.dmp.DIFF_EQUAL, "xyz")], 3))

  def testDiffLevenshtein(self):
    # Levenshtein with trailing equality.
    self.assertEquals(4, self.dmp.diff_levenshtein([(self.dmp.DIFF_DELETE, "abc"), (self.dmp.DIFF_INSERT, "1234"), (self.dmp.DIFF_EQUAL, "xyz")]))
    # Levenshtein with leading equality.
    self.assertEquals(4, self.dmp.diff_levenshtein([(self.dmp.DIFF_EQUAL, "xyz"), (self.dmp.DIFF_DELETE, "abc"), (self.dmp.DIFF_INSERT, "1234")]))
    # Levenshtein with middle equality.
    self.assertEquals(7, self.dmp.diff_levenshtein([(self.dmp.DIFF_DELETE, "abc"), (self.dmp.DIFF_EQUAL, "xyz"), (self.dmp.DIFF_INSERT, "1234")]))

  def testDiffBisect(self):
    # Normal.
    a = "cat"
    b = "map"
    # Since the resulting diff hasn't been normalized, it would be ok if
    # the insertion and deletion pairs are swapped.
    # If the order changes, tweak this test as required.
    self.assertEquals([(self.dmp.DIFF_DELETE, "c"), (self.dmp.DIFF_INSERT, "m"), (self.dmp.DIFF_EQUAL, "a"), (self.dmp.DIFF_DELETE, "t"), (self.dmp.DIFF_INSERT, "p")], self.dmp.diff_bisect(a, b, sys.maxint))

    # Timeout.
    self.assertEquals([(self.dmp.DIFF_DELETE, "cat"), (self.dmp.DIFF_INSERT, "map")], self.dmp.diff_bisect(a, b, 0))

  def testDiffMain(self):
    # Perform a trivial diff.
    # Null case.
    self.assertEquals([], self.dmp.diff_main("", "", False))

    # Equality.
    self.assertEquals([(self.dmp.DIFF_EQUAL, "abc")], self.dmp.diff_main("abc", "abc", False))

    # Simple insertion.
    self.assertEquals([(self.dmp.DIFF_EQUAL, "ab"), (self.dmp.DIFF_INSERT, "123"), (self.dmp.DIFF_EQUAL, "c")], self.dmp.diff_main("abc", "ab123c", False))

    # Simple deletion.
    self.assertEquals([(self.dmp.DIFF_EQUAL, "a"), (self.dmp.DIFF_DELETE, "123"), (self.dmp.DIFF_EQUAL, "bc")], self.dmp.diff_main("a123bc", "abc", False))

    # Two insertions.
    self.assertEquals([(self.dmp.DIFF_EQUAL, "a"), (self.dmp.DIFF_INSERT, "123"), (self.dmp.DIFF_EQUAL, "b"), (self.dmp.DIFF_INSERT, "456"), (self.dmp.DIFF_EQUAL, "c")], self.dmp.diff_main("abc", "a123b456c", False))

    # Two deletions.
    self.assertEquals([(self.dmp.DIFF_EQUAL, "a"), (self.dmp.DIFF_DELETE, "123"), (self.dmp.DIFF_EQUAL, "b"), (self.dmp.DIFF_DELETE, "456"), (self.dmp.DIFF_EQUAL, "c")], self.dmp.diff_main("a123b456c", "abc", False))

    # Perform a real diff.
    # Switch off the timeout.
    self.dmp.Diff_Timeout = 0
    # Simple cases.
    self.assertEquals([(self.dmp.DIFF_DELETE, "a"), (self.dmp.DIFF_INSERT, "b")], self.dmp.diff_main("a", "b", False))

    self.assertEquals([(self.dmp.DIFF_DELETE, "Apple"), (self.dmp.DIFF_INSERT, "Banana"), (self.dmp.DIFF_EQUAL, "s are a"), (self.dmp.DIFF_INSERT, "lso"), (self.dmp.DIFF_EQUAL, " fruit.")], self.dmp.diff_main("Apples are a fruit.", "Bananas are also fruit.", False))

    self.assertEquals([(self.dmp.DIFF_DELETE, "a"), (self.dmp.DIFF_INSERT, u"\u0680"), (self.dmp.DIFF_EQUAL, "x"), (self.dmp.DIFF_DELETE, "\t"), (self.dmp.DIFF_INSERT, u"\x00")], self.dmp.diff_main("ax\t", u"\u0680x\x00", False))

    # Overlaps.
    self.assertEquals([(self.dmp.DIFF_DELETE, "1"), (self.dmp.DIFF_EQUAL, "a"), (self.dmp.DIFF_DELETE, "y"), (self.dmp.DIFF_EQUAL, "b"), (self.dmp.DIFF_DELETE, "2"), (self.dmp.DIFF_INSERT, "xab")], self.dmp.diff_main("1ayb2", "abxab", False))

    self.assertEquals([(self.dmp.DIFF_INSERT, "xaxcx"), (self.dmp.DIFF_EQUAL, "abc"), (self.dmp.DIFF_DELETE, "y")], self.dmp.diff_main("abcy", "xaxcxabc", False))

    self.assertEquals([(self.dmp.DIFF_DELETE, "ABCD"), (self.dmp.DIFF_EQUAL, "a"), (self.dmp.DIFF_DELETE, "="), (self.dmp.DIFF_INSERT, "-"), (self.dmp.DIFF_EQUAL, "bcd"), (self.dmp.DIFF_DELETE, "="), (self.dmp.DIFF_INSERT, "-"), (self.dmp.DIFF_EQUAL, "efghijklmnopqrs"), (self.dmp.DIFF_DELETE, "EFGHIJKLMNOefg")], self.dmp.diff_main("ABCDa=bcd=efghijklmnopqrsEFGHIJKLMNOefg", "a-bcd-efghijklmnopqrs", False))

    # Large equality.
    self.assertEquals([(self.dmp.DIFF_INSERT, " "), (self.dmp.DIFF_EQUAL,"a"), (self.dmp.DIFF_INSERT,"nd"), (self.dmp.DIFF_EQUAL," [[Pennsylvania]]"), (self.dmp.DIFF_DELETE," and [[New")], self.dmp.diff_main("a [[Pennsylvania]] and [[New", " and [[Pennsylvania]]", False))

    # Timeout.
    self.dmp.Diff_Timeout = 0.1  # 100ms
    a = "`Twas brillig, and the slithy toves\nDid gyre and gimble in the wabe:\nAll mimsy were the borogoves,\nAnd the mome raths outgrabe.\n"
    b = "I am the very model of a modern major general,\nI've information vegetable, animal, and mineral,\nI know the kings of England, and I quote the fights historical,\nFrom Marathon to Waterloo, in order categorical.\n"
    # Increase the text lengths by 1024 times to ensure a timeout.
    for x in xrange(10):
      a = a + a
      b = b + b
    startTime = time.time()
    self.dmp.diff_main(a, b)
    endTime = time.time()
    # Test that we took at least the timeout period.
    self.assertTrue(self.dmp.Diff_Timeout <= endTime - startTime)
    # Test that we didn't take forever (be forgiving).
    # Theoretically this test could fail very occasionally if the
    # OS task swaps or locks up for a second at the wrong moment.
    self.assertTrue(self.dmp.Diff_Timeout * 2 > endTime - startTime)
    self.dmp.Diff_Timeout = 0

    # Test the linemode speedup.
    # Must be long to pass the 100 char cutoff.
    # Simple line-mode.
    a = "1234567890\n" * 13
    b = "abcdefghij\n" * 13
    self.assertEquals(self.dmp.diff_main(a, b, False), self.dmp.diff_main(a, b, True))

    # Single line-mode.
    a = "1234567890" * 13
    b = "abcdefghij" * 13
    self.assertEquals(self.dmp.diff_main(a, b, False), self.dmp.diff_main(a, b, True))

    # Overlap line-mode.
    a = "1234567890\n" * 13
    b = "abcdefghij\n1234567890\n1234567890\n1234567890\nabcdefghij\n1234567890\n1234567890\n1234567890\nabcdefghij\n1234567890\n1234567890\n1234567890\nabcdefghij\n"
    texts_linemode = self.diff_rebuildtexts(self.dmp.diff_main(a, b, True))
    texts_textmode = self.diff_rebuildtexts(self.dmp.diff_main(a, b, False))
    self.assertEquals(texts_textmode, texts_linemode)

    # Test null inputs.
    try:
      self.dmp.diff_main(None, None)
      self.assertFalse(True)
    except ValueError:
      # Exception expected.
      pass


class MatchTest(DiffMatchPatchTest):
  """MATCH TEST FUNCTIONS"""

  def testMatchAlphabet(self):
    # Initialise the bitmasks for Bitap.
    self.assertEquals({"a":4, "b":2, "c":1}, self.dmp.match_alphabet("abc"))

    self.assertEquals({"a":37, "b":18, "c":8}, self.dmp.match_alphabet("abcaba"))

  def testMatchBitap(self):
    self.dmp.Match_Distance = 100
    self.dmp.Match_Threshold = 0.5
    # Exact matches.
    self.assertEquals(5, self.dmp.match_bitap("abcdefghijk", "fgh", 5))

    self.assertEquals(5, self.dmp.match_bitap("abcdefghijk", "fgh", 0))

    # Fuzzy matches.
    self.assertEquals(4, self.dmp.match_bitap("abcdefghijk", "efxhi", 0))

    self.assertEquals(2, self.dmp.match_bitap("abcdefghijk", "cdefxyhijk", 5))

    self.assertEquals(-1, self.dmp.match_bitap("abcdefghijk", "bxy", 1))

    # Overflow.
    self.assertEquals(2, self.dmp.match_bitap("123456789xx0", "3456789x0", 2))

    self.assertEquals(0, self.dmp.match_bitap("abcdef", "xxabc", 4))

    self.assertEquals(3, self.dmp.match_bitap("abcdef", "defyy", 4))

    self.assertEquals(0, self.dmp.match_bitap("abcdef", "xabcdefy", 0))

    # Threshold test.
    self.dmp.Match_Threshold = 0.4
    self.assertEquals(4, self.dmp.match_bitap("abcdefghijk", "efxyhi", 1))

    self.dmp.Match_Threshold = 0.3
    self.assertEquals(-1, self.dmp.match_bitap("abcdefghijk", "efxyhi", 1))

    self.dmp.Match_Threshold = 0.0
    self.assertEquals(1, self.dmp.match_bitap("abcdefghijk", "bcdef", 1))
    self.dmp.Match_Threshold = 0.5

    # Multiple select.
    self.assertEquals(0, self.dmp.match_bitap("abcdexyzabcde", "abccde", 3))

    self.assertEquals(8, self.dmp.match_bitap("abcdexyzabcde", "abccde", 5))

    # Distance test.
    self.dmp.Match_Distance = 10  # Strict location.
    self.assertEquals(-1, self.dmp.match_bitap("abcdefghijklmnopqrstuvwxyz", "abcdefg", 24))

    self.assertEquals(0, self.dmp.match_bitap("abcdefghijklmnopqrstuvwxyz", "abcdxxefg", 1))

    self.dmp.Match_Distance = 1000  # Loose location.
    self.assertEquals(0, self.dmp.match_bitap("abcdefghijklmnopqrstuvwxyz", "abcdefg", 24))


  def testMatchMain(self):
    # Full match.
    # Shortcut matches.
    self.assertEquals(0, self.dmp.match_main("abcdef", "abcdef", 1000))

    self.assertEquals(-1, self.dmp.match_main("", "abcdef", 1))

    self.assertEquals(3, self.dmp.match_main("abcdef", "", 3))

    self.assertEquals(3, self.dmp.match_main("abcdef", "de", 3))

    self.assertEquals(3, self.dmp.match_main("abcdef", "defy", 4))

    self.assertEquals(0, self.dmp.match_main("abcdef", "abcdefy", 0))

    # Complex match.
    self.dmp.Match_Threshold = 0.7
    self.assertEquals(4, self.dmp.match_main("I am the very model of a modern major general.", " that berry ", 5))
    self.dmp.Match_Threshold = 0.5

    # Test null inputs.
    try:
      self.dmp.match_main(None, None, 0)
      self.assertFalse(True)
    except ValueError:
      # Exception expected.
      pass


class PatchTest(DiffMatchPatchTest):
  """PATCH TEST FUNCTIONS"""

  def testPatchObj(self):
    # Patch Object.
    p = dmp_module.patch_obj()
    p.start1 = 20
    p.start2 = 21
    p.length1 = 18
    p.length2 = 17
    p.diffs = [(self.dmp.DIFF_EQUAL, "jump"), (self.dmp.DIFF_DELETE, "s"), (self.dmp.DIFF_INSERT, "ed"), (self.dmp.DIFF_EQUAL, " over "), (self.dmp.DIFF_DELETE, "the"), (self.dmp.DIFF_INSERT, "a"), (self.dmp.DIFF_EQUAL, "\nlaz")]
    strp = str(p)
    self.assertEquals("@@ -21,18 +22,17 @@\n jump\n-s\n+ed\n  over \n-the\n+a\n %0Alaz\n", strp)

  def testPatchFromText(self):
    self.assertEquals([], self.dmp.patch_fromText(""))

    strp = "@@ -21,18 +22,17 @@\n jump\n-s\n+ed\n  over \n-the\n+a\n %0Alaz\n"
    self.assertEquals(strp, str(self.dmp.patch_fromText(strp)[0]))

    self.assertEquals("@@ -1 +1 @@\n-a\n+b\n", str(self.dmp.patch_fromText("@@ -1 +1 @@\n-a\n+b\n")[0]))

    self.assertEquals("@@ -1,3 +0,0 @@\n-abc\n", str(self.dmp.patch_fromText("@@ -1,3 +0,0 @@\n-abc\n")[0]))

    self.assertEquals("@@ -0,0 +1,3 @@\n+abc\n", str(self.dmp.patch_fromText("@@ -0,0 +1,3 @@\n+abc\n")[0]))

    # Generates error.
    try:
      self.dmp.patch_fromText("Bad\nPatch\n")
      self.assertFalse(True)
    except ValueError:
      # Exception expected.
      pass

  def testPatchToText(self):
    strp = "@@ -21,18 +22,17 @@\n jump\n-s\n+ed\n  over \n-the\n+a\n  laz\n"
    p = self.dmp.patch_fromText(strp)
    self.assertEquals(strp, self.dmp.patch_toText(p))

    strp = "@@ -1,9 +1,9 @@\n-f\n+F\n oo+fooba\n@@ -7,9 +7,9 @@\n obar\n-,\n+.\n tes\n"
    p = self.dmp.patch_fromText(strp)
    self.assertEquals(strp, self.dmp.patch_toText(p))

  def testPatchAddContext(self):
    self.dmp.Patch_Margin = 4
    p = self.dmp.patch_fromText("@@ -21,4 +21,10 @@\n-jump\n+somersault\n")[0]
    self.dmp.patch_addContext(p, "The quick brown fox jumps over the lazy dog.")
    self.assertEquals("@@ -17,12 +17,18 @@\n fox \n-jump\n+somersault\n s ov\n", str(p))

    # Same, but not enough trailing context.
    p = self.dmp.patch_fromText("@@ -21,4 +21,10 @@\n-jump\n+somersault\n")[0]
    self.dmp.patch_addContext(p, "The quick brown fox jumps.")
    self.assertEquals("@@ -17,10 +17,16 @@\n fox \n-jump\n+somersault\n s.\n", str(p))

    # Same, but not enough leading context.
    p = self.dmp.patch_fromText("@@ -3 +3,2 @@\n-e\n+at\n")[0]
    self.dmp.patch_addContext(p, "The quick brown fox jumps.")
    self.assertEquals("@@ -1,7 +1,8 @@\n Th\n-e\n+at\n  qui\n", str(p))

    # Same, but with ambiguity.
    p = self.dmp.patch_fromText("@@ -3 +3,2 @@\n-e\n+at\n")[0]
    self.dmp.patch_addContext(p, "The quick brown fox jumps.  The quick brown fox crashes.")
    self.assertEquals("@@ -1,27 +1,28 @@\n Th\n-e\n+at\n  quick brown fox jumps. \n", str(p))

  def testPatchMake(self):
    # Null case.
    patches = self.dmp.patch_make("", "")
    self.assertEquals("", self.dmp.patch_toText(patches))

    text1 = "The quick brown fox jumps over the lazy dog."
    text2 = "That quick brown fox jumped over a lazy dog."
    # Text2+Text1 inputs.
    expectedPatch = "@@ -1,8 +1,7 @@\n Th\n-at\n+e\n  qui\n@@ -21,17 +21,18 @@\n jump\n-ed\n+s\n  over \n-a\n+the\n  laz\n"
    # The second patch must be "-21,17 +21,18", not "-22,17 +21,18" due to rolling context.
    patches = self.dmp.patch_make(text2, text1)
    self.assertEquals(expectedPatch, self.dmp.patch_toText(patches))

    # Text1+Text2 inputs.
    expectedPatch = "@@ -1,11 +1,12 @@\n Th\n-e\n+at\n  quick b\n@@ -22,18 +22,17 @@\n jump\n-s\n+ed\n  over \n-the\n+a\n  laz\n"
    patches = self.dmp.patch_make(text1, text2)
    self.assertEquals(expectedPatch, self.dmp.patch_toText(patches))

    # Diff input.
    diffs = self.dmp.diff_main(text1, text2, False)
    patches = self.dmp.patch_make(diffs)
    self.assertEquals(expectedPatch, self.dmp.patch_toText(patches))

    # Text1+Diff inputs.
    patches = self.dmp.patch_make(text1, diffs)
    self.assertEquals(expectedPatch, self.dmp.patch_toText(patches))

    # Text1+Text2+Diff inputs (deprecated).
    patches = self.dmp.patch_make(text1, text2, diffs)
    self.assertEquals(expectedPatch, self.dmp.patch_toText(patches))

    # Character encoding.
    patches = self.dmp.patch_make("`1234567890-=[]\\;',./", "~!@#$%^&*()_+{}|:\"<>?")
    self.assertEquals("@@ -1,21 +1,21 @@\n-%601234567890-=%5B%5D%5C;',./\n+~!@#$%25%5E&*()_+%7B%7D%7C:%22%3C%3E?\n", self.dmp.patch_toText(patches))

    # Character decoding.
    diffs = [(self.dmp.DIFF_DELETE, "`1234567890-=[]\\;',./"), (self.dmp.DIFF_INSERT, "~!@#$%^&*()_+{}|:\"<>?")]
    self.assertEquals(diffs, self.dmp.patch_fromText("@@ -1,21 +1,21 @@\n-%601234567890-=%5B%5D%5C;',./\n+~!@#$%25%5E&*()_+%7B%7D%7C:%22%3C%3E?\n")[0].diffs)

    # Long string with repeats.
    text1 = ""
    for x in range(100):
      text1 += "abcdef"
    text2 = text1 + "123"
    expectedPatch = "@@ -573,28 +573,31 @@\n cdefabcdefabcdefabcdefabcdef\n+123\n"
    patches = self.dmp.patch_make(text1, text2)
    self.assertEquals(expectedPatch, self.dmp.patch_toText(patches))

    # Test null inputs.
    try:
      self.dmp.patch_make(None, None)
      self.assertFalse(True)
    except ValueError:
      # Exception expected.
      pass

  def testPatchSplitMax(self):
    # Assumes that Match_MaxBits is 32.
    patches = self.dmp.patch_make("abcdefghijklmnopqrstuvwxyz01234567890", "XabXcdXefXghXijXklXmnXopXqrXstXuvXwxXyzX01X23X45X67X89X0")
    self.dmp.patch_splitMax(patches)
    self.assertEquals("@@ -1,32 +1,46 @@\n+X\n ab\n+X\n cd\n+X\n ef\n+X\n gh\n+X\n ij\n+X\n kl\n+X\n mn\n+X\n op\n+X\n qr\n+X\n st\n+X\n uv\n+X\n wx\n+X\n yz\n+X\n 012345\n@@ -25,13 +39,18 @@\n zX01\n+X\n 23\n+X\n 45\n+X\n 67\n+X\n 89\n+X\n 0\n", self.dmp.patch_toText(patches))

    patches = self.dmp.patch_make("abcdef1234567890123456789012345678901234567890123456789012345678901234567890uvwxyz", "abcdefuvwxyz")
    oldToText = self.dmp.patch_toText(patches)
    self.dmp.patch_splitMax(patches)
    self.assertEquals(oldToText, self.dmp.patch_toText(patches))

    patches = self.dmp.patch_make("1234567890123456789012345678901234567890123456789012345678901234567890", "abc")
    self.dmp.patch_splitMax(patches)
    self.assertEquals("@@ -1,32 +1,4 @@\n-1234567890123456789012345678\n 9012\n@@ -29,32 +1,4 @@\n-9012345678901234567890123456\n 7890\n@@ -57,14 +1,3 @@\n-78901234567890\n+abc\n", self.dmp.patch_toText(patches))

    patches = self.dmp.patch_make("abcdefghij , h : 0 , t : 1 abcdefghij , h : 0 , t : 1 abcdefghij , h : 0 , t : 1", "abcdefghij , h : 1 , t : 1 abcdefghij , h : 1 , t : 1 abcdefghij , h : 0 , t : 1")
    self.dmp.patch_splitMax(patches)
    self.assertEquals("@@ -2,32 +2,32 @@\n bcdefghij , h : \n-0\n+1\n  , t : 1 abcdef\n@@ -29,32 +29,32 @@\n bcdefghij , h : \n-0\n+1\n  , t : 1 abcdef\n", self.dmp.patch_toText(patches))

  def testPatchAddPadding(self):
    # Both edges full.
    patches = self.dmp.patch_make("", "test")
    self.assertEquals("@@ -0,0 +1,4 @@\n+test\n", self.dmp.patch_toText(patches))
    self.dmp.patch_addPadding(patches)
    self.assertEquals("@@ -1,8 +1,12 @@\n %01%02%03%04\n+test\n %01%02%03%04\n", self.dmp.patch_toText(patches))

    # Both edges partial.
    patches = self.dmp.patch_make("XY", "XtestY")
    self.assertEquals("@@ -1,2 +1,6 @@\n X\n+test\n Y\n", self.dmp.patch_toText(patches))
    self.dmp.patch_addPadding(patches)
    self.assertEquals("@@ -2,8 +2,12 @@\n %02%03%04X\n+test\n Y%01%02%03\n", self.dmp.patch_toText(patches))

    # Both edges none.
    patches = self.dmp.patch_make("XXXXYYYY", "XXXXtestYYYY")
    self.assertEquals("@@ -1,8 +1,12 @@\n XXXX\n+test\n YYYY\n", self.dmp.patch_toText(patches))
    self.dmp.patch_addPadding(patches)
    self.assertEquals("@@ -5,8 +5,12 @@\n XXXX\n+test\n YYYY\n", self.dmp.patch_toText(patches))

  def testPatchApply(self):
    self.dmp.Match_Distance = 1000
    self.dmp.Match_Threshold = 0.5
    self.dmp.Patch_DeleteThreshold = 0.5
    # Null case.
    patches = self.dmp.patch_make("", "")
    results = self.dmp.patch_apply(patches, "Hello world.")
    self.assertEquals(("Hello world.", []), results)

    # Exact match.
    patches = self.dmp.patch_make("The quick brown fox jumps over the lazy dog.", "That quick brown fox jumped over a lazy dog.")
    results = self.dmp.patch_apply(patches, "The quick brown fox jumps over the lazy dog.")
    self.assertEquals(("That quick brown fox jumped over a lazy dog.", [True, True]), results)

    # Partial match.
    results = self.dmp.patch_apply(patches, "The quick red rabbit jumps over the tired tiger.")
    self.assertEquals(("That quick red rabbit jumped over a tired tiger.", [True, True]), results)

    # Failed match.
    results = self.dmp.patch_apply(patches, "I am the very model of a modern major general.")
    self.assertEquals(("I am the very model of a modern major general.", [False, False]), results)

    # Big delete, small change.
    patches = self.dmp.patch_make("x1234567890123456789012345678901234567890123456789012345678901234567890y", "xabcy")
    results = self.dmp.patch_apply(patches, "x123456789012345678901234567890-----++++++++++-----123456789012345678901234567890y")
    self.assertEquals(("xabcy", [True, True]), results)

    # Big delete, big change 1.
    patches = self.dmp.patch_make("x1234567890123456789012345678901234567890123456789012345678901234567890y", "xabcy")
    results = self.dmp.patch_apply(patches, "x12345678901234567890---------------++++++++++---------------12345678901234567890y")
    self.assertEquals(("xabc12345678901234567890---------------++++++++++---------------12345678901234567890y", [False, True]), results)

    # Big delete, big change 2.
    self.dmp.Patch_DeleteThreshold = 0.6
    patches = self.dmp.patch_make("x1234567890123456789012345678901234567890123456789012345678901234567890y", "xabcy")
    results = self.dmp.patch_apply(patches, "x12345678901234567890---------------++++++++++---------------12345678901234567890y")
    self.assertEquals(("xabcy", [True, True]), results)
    self.dmp.Patch_DeleteThreshold = 0.5

    # Compensate for failed patch.
    self.dmp.Match_Threshold = 0.0
    self.dmp.Match_Distance = 0
    patches = self.dmp.patch_make("abcdefghijklmnopqrstuvwxyz--------------------1234567890", "abcXXXXXXXXXXdefghijklmnopqrstuvwxyz--------------------1234567YYYYYYYYYY890")
    results = self.dmp.patch_apply(patches, "ABCDEFGHIJKLMNOPQRSTUVWXYZ--------------------1234567890")
    self.assertEquals(("ABCDEFGHIJKLMNOPQRSTUVWXYZ--------------------1234567YYYYYYYYYY890", [False, True]), results)
    self.dmp.Match_Threshold = 0.5
    self.dmp.Match_Distance = 1000

    # No side effects.
    patches = self.dmp.patch_make("", "test")
    patchstr = self.dmp.patch_toText(patches)
    results = self.dmp.patch_apply(patches, "")
    self.assertEquals(patchstr, self.dmp.patch_toText(patches))

    # No side effects with major delete.
    patches = self.dmp.patch_make("The quick brown fox jumps over the lazy dog.", "Woof")
    patchstr = self.dmp.patch_toText(patches)
    self.dmp.patch_apply(patches, "The quick brown fox jumps over the lazy dog.")
    self.assertEquals(patchstr, self.dmp.patch_toText(patches))

    # Edge exact match.
    patches = self.dmp.patch_make("", "test")
    self.dmp.patch_apply(patches, "")
    self.assertEquals(("test", [True]), results)

    # Near edge exact match.
    patches = self.dmp.patch_make("XY", "XtestY")
    results = self.dmp.patch_apply(patches, "XY")
    self.assertEquals(("XtestY", [True]), results)

    # Edge partial match.
    patches = self.dmp.patch_make("y", "y123")
    results = self.dmp.patch_apply(patches, "x")
    self.assertEquals(("x123", [True]), results)


if __name__ == "__main__":
  unittest.main()

########NEW FILE########
__FILENAME__ = search_sites
import haystack
haystack.autodiscover()

########NEW FILE########
__FILENAME__ = settings
# -*- coding: utf-8 -*-
# Django settings for algospot project.

import os, sys
from datetime import datetime

PROJECT_DIR = os.path.dirname(__file__)
j = lambda filename: os.path.join(PROJECT_DIR, filename)
sys.path.append(j("libs/common"))
sys.path.append(j("libs/external"))

DEBUG = False
TEMPLATE_DEBUG = DEBUG

ADMINS = (
    ('JongMan Koo', 'jongman@gmail.com'),
    ('Wonha Ryu', 'wonha.ryu@gmail.com'),
)

MANAGERS = ADMINS

DATABASES = {
    'default': {
        # TODO: change this into an absolute path if you're running celeryd from
        # a separate checkout in the same machine
        'ENGINE': 'django.db.backends.sqlite3', # Add 'postgresql_psycopg2', 'postgresql', 'mysql', 'sqlite3' or 'oracle'.
        'NAME': 'db.sqlite3',                      # Or path to database file if using sqlite3.
        'USER': '',                      # Not used with sqlite3.
        'PASSWORD': '',                  # Not used with sqlite3.
        'HOST': '',                      # Set to empty string for localhost. Not used with sqlite3.
        'PORT': '',                      # Set to empty string for default. Not used with sqlite3.
    }
}

# Local time zone for this installation. Choices can be found here:
# http://en.wikipedia.org/wiki/List_of_tz_zones_by_name
# although not all choices may be available on all operating systems.
# On Unix systems, a value of None will cause Django to use the same
# timezone as the operating system.
# If running in a Windows environment this must be set to the same as your
# system time zone.
TIME_ZONE = 'Asia/Seoul'

# Language code for this installation. All choices can be found here:
# http://www.i18nguy.com/unicode/language-identifiers.html
LANGUAGE_CODE = 'en-us'

SITE_ID = 1

# If you set this to False, Django will make some optimizations so as not
# to load the internationalization machinery.
USE_I18N = True

# If you set this to False, Django will not format dates, numbers and
# calendars according to the current locale
USE_L10N = True

# Absolute filesystem path to the directory that will hold user-uploaded files.
# Example: "/home/media/media.lawrence.com/media/"
MEDIA_ROOT = j("../media")

# URL that handles the media served from MEDIA_ROOT. Make sure to use a
# trailing slash.
# Examples: "http://media.lawrence.com/media/", "http://example.com/media/"
#MEDIA_URL = '/media/'
# set for development: reset for prod
MEDIA_URL = "http://0.0.0.0:8000/media/"

# Absolute path to the directory static files should be collected to.
# Don't put anything in this directory yourself; store your static files
# in apps' "static/" subdirectories and in STATICFILES_DIRS.
# Example: "/home/media/media.lawrence.com/static/"
STATIC_ROOT = ''

# URL prefix for static files.
# Example: "http://media.lawrence.com/static/"
STATIC_URL = '/static/'

# URL prefix for admin static files -- CSS, JavaScript and images.
# Make sure to use a trailing slash.
# Examples: "http://foo.com/static/admin/", "/static/admin/".
ADMIN_MEDIA_PREFIX = '/static/admin/'

# Additional locations of static files
STATICFILES_DIRS = (
    j("../static"),
)

# List of finder classes that know how to find static files in
# various locations.
STATICFILES_FINDERS = (
    'django.contrib.staticfiles.finders.FileSystemFinder',
    'django.contrib.staticfiles.finders.AppDirectoriesFinder',
    #    'django.contrib.staticfiles.finders.DefaultStorageFinder',
)

# Make this unique, and don't share it with anybody.
SECRET_KEY = 'ql^5l!arg8ua-nxp-n+!*a-n%9_^osj-*k7ae@zu=n$zbrod-w'

# List of callables that know how to import templates from various sources.
TEMPLATE_LOADERS = (
    'django.template.loaders.filesystem.Loader',
    'django.template.loaders.app_directories.Loader',
    #     'django.template.loaders.eggs.Loader',
)

MIDDLEWARE_CLASSES = (
    'django.middleware.common.CommonMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
)

ROOT_URLCONF = 'algospot.urls'

TEMPLATE_DIRS = (
    j("../templates"),
)

INTERNAL_IPS = ('127.0.0.1',)

INSTALLED_APPS = (
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.sites',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'django.contrib.admin',
    'django.contrib.comments',

    'south',
    'django_extensions',
    'registration',
    'avatar',
    'djcelery',
    'tagging',
    'haystack',
    'guardian',
    #'actstream',

    'base',
    'wiki',
    'forum',
    'newsfeed',
    'judge',
    # Uncomment the next line to enable admin documentation:
    # 'django.contrib.admindocs',
)

AUTH_PROFILE_MODULE = 'base.UserProfile'

ACCOUNT_ACTIVATION_DAYS = 7

# A sample logging configuration. The only tangible logging
# performed by this configuration is to send an email to
# the site admins on every HTTP 500 error.
# See http://docs.djangoproject.com/en/dev/topics/logging for
# more details on how to customize your logging configuration.
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'handlers': {
        'mail_admins': {
            'level': 'ERROR',
            'class': 'django.utils.log.AdminEmailHandler'
        }
    },
    'loggers': {
        'django.request': {
            'handlers': ['mail_admins'],
            'level': 'ERROR',
            'propagate': True,
        },
    }
}

# this is a dev setting
EMAIL_HOST = 'localhost'
EMAIL_PORT = 25

# avatar setting

AUTO_GENERATE_AVATAR_SIZES = (45, 80, 120)
AVATAR_STORAGE_DIR = "avatars"
AVATAR_GRAVATAR_BACKUP = False
AVATAR_DEFAULT_URL = "/static/images/unknown-user.png"

LOGIN_REDIRECT_URL = "/"

DEBUG_TOOLBAR_CONFIG = {"INTERCEPT_REDIRECTS": False }

TEMPLATE_CONTEXT_PROCESSORS = (
    "django.contrib.auth.context_processors.auth",
    "django.core.context_processors.debug",
    "django.core.context_processors.i18n",
    "django.core.context_processors.media",
    "django.core.context_processors.static",
    "django.contrib.messages.context_processors.messages",
    'django.core.context_processors.request',
    "forum.processors.add_categories",
    'base.processors.select_campaign'
)

AUTHENTICATION_BACKENDS = (
    'base.backends.LegacyBackend',
    'base.backends.EmailBackend',
    'django.contrib.auth.backends.ModelBackend',
    'guardian.backends.ObjectPermissionBackend',
)

# GUARDIAN SETTINGS
ANONYMOUS_USER_ID = -1
GUARDIAN_RAISE_403 = True

# JUDGE SETTINGS
JUDGE_SETTINGS = {
    "WORKDIR": j("../judge/work"),
    "USER": "runner",
    "FILESYSTEMSIZE": 64 * 1024,
    "MINMEMORYSIZE": 256 * 1024,
}

# PAGINATION SETTINGS
ITEMS_PER_PAGE = 20
PAGINATOR_RANGE = 5

# PROFILE SETTINGS
PROFILE_LOG_BASE = None

# CELERY SETTINGS
import djcelery
djcelery.setup_loader()

CELERY_IMPORTS = ("judge.tasks",)
CELERYD_CONCURRENCY = 1

# haystack
HAYSTACK_CONNECTIONS = {
    'default': {
        'ENGINE': 'haystack.backends.whoosh_backend.WhooshEngine',
        'PATH': j('../whoosh_index'),
        'STORAGE': 'file',
        'POST_LIMIT': 128 * 1024 * 1024,
        'INCLUDE_SPELLING': True,
        'BATCH_SIZE': 10
    }
}

USE_AYAH = False

SOLVED_CAMPAIGN = [
    {'problem': 'HELLOWORLD',
     'begin': datetime(2012, 1, 1, 0, 0, 0),
     'end': datetime(2012, 12, 31, 23, 59, 59),
     'message': u"""*HELLO WORLD 문제를 푸셨군요!*

축하합니다! ^^
     """.strip()},
]

try:
    import local_settings
except ImportError:
    pass

########NEW FILE########
__FILENAME__ = urls
from django.conf.urls.defaults import patterns, include, url
from django.conf import settings
from django.contrib import admin
from base.feeds import PostFeed
from base.forms import AreYouAHumanFormView
from registration.views import RegistrationView

admin.autodiscover()

urlpatterns = patterns(
    '',
    url(r'^wiki/', include('wiki.urls')),
    url(r'^forum/', include('forum.urls')),
    url(r'^user/', include('base.urls')),
    url(r'^newsfeed/', include('newsfeed.urls')),
    url(r'^judge/', include('judge.urls')),
    url(r'^calendar/', 'base.views.calendar', name='calendar'),
    url(r'^feed/posts/', PostFeed(), name='postfeed'),
    url(r'^discussions/feed.rss', PostFeed()),
    url(r'^zbxe/rss', PostFeed()),

    url(r'^search/', include('haystack.urls')),

    url(r'^admin/', include(admin.site.urls)),
    url(r'^accounts/logout', 'django.contrib.auth.views.logout',
        kwargs={'next_page': '/'}),
    url(r'^avatar/', include('avatar.urls')),

    # we are overriding default comments app's deletion..
    url(r'^comments/delete/(?P<comment_id>.+)/', 'base.views.delete_comment',
        name="comment-delete-algospot"),

    # first page
    url(r'^/?$', 'base.views.index'),

    # comments apps
    url(r'^comments/', include('django.contrib.comments.urls')),
)

if settings.DEBUG:
    # Serve all local files from MEDIA_ROOT below /media/
    urlpatterns += patterns(
        '',
        (r'^media/(?P<path>.*)$', 'django.views.static.serve',
         {'document_root': settings.MEDIA_ROOT, 'show_indexes': True}),)

if settings.USE_AYAH:
    urlpatterns += patterns(
        '',
        url(r'^accounts/register/?$', AreYouAHumanFormView.as_view()),
    )

urlpatterns += patterns(
    '',
    url(r'^accounts/', include('registration.backends.default.urls')),
)

########NEW FILE########
__FILENAME__ = admin
from django import forms
from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.contrib.auth.models import User
from django.contrib.auth.forms import UserCreationForm, UserChangeForm
from django.utils.translation import ugettext_lazy as _

class MyUserCreationForm(UserCreationForm):
    username = forms.RegexField(
        label = _('username'),
        max_length = 30,
        regex = ur'^[\w\uac00-\ud7a3.@+-]+$',
        help_text = _("Required. 30 characters or fewer. Letters, digits, korean characters and @/./+/-/_ characters."),
        error_messages = {
            'invalid': _("This value must contain only letters, digits, korean characters and @/./+/-/_ characters.")})

class MyUserChangeForm(UserChangeForm):
    username = forms.RegexField(
        label = _('username'),
        max_length = 30,
        regex = ur'^[\w\uac00-\ud7a3.@+-]+$',
        help_text = _("Required. 30 characters or fewer. Letters, digits, korean characters and @/./+/-/_ characters."),
        error_messages = {
            'invalid': _("This value must contain only letters, digits, korean characters and @/./+/-/_ characters.")})


class MyUserAdmin(UserAdmin):
    list_filter = UserAdmin.list_filter + ('groups__name',)
    form = MyUserChangeForm
    add_form = MyUserCreationForm

admin.site.unregister(User)
admin.site.register(User, MyUserAdmin)

########NEW FILE########
__FILENAME__ = backends
# -*- coding: utf-8 -*-

from django.contrib.auth.models import User
import hashlib
from django.contrib.auth.backends import ModelBackend

BASE64 = "./0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz"

def md5(s, raw=True):
    m = hashlib.md5()
    m.update(s)
    return m.digest() if raw else m.hexdigest()

def encode64(input, count):
    output = ""
    i = 0
    while True:
        value = ord(input[i]); i += 1
        output += BASE64[value & 0x3f]
        if i < count:
            value |= ord(input[i]) << 8;
        output += BASE64[(value >> 6) & 0x3f];
        if i >= count: break
        i += 1
        if i < count:
            value |= ord(input[i]) << 16
        output += BASE64[(value >> 12) & 0x3f];
        if i >= count: break
        i += 1
        output += BASE64[(value >> 18) & 0x3f];
        if i >= count: break
    return output

def get_hash(password, stored):
    password = password.encode("utf-8")
    salt = stored[4:12]
    count = 2 ** BASE64.index(stored[3])
    hash = md5(salt + password)
    for i in xrange(count):
        hash = md5(hash + password)
    return stored[:12] + encode64(hash, 16)

def first_or_none(model, **kwargs):
    instances = model.objects.filter(**kwargs)
    if not instances: return None
    return instances[0]


MAGIC = r"sha1$deadbeef$"
class LegacyBackend(ModelBackend):
    supports_object_permissions = False
    supports_anonymous_user = False
    supports_inactive_user = False

    def get_user(self, user_id):
        return first_or_none(User, pk=user_id)

    def authenticate(self, username=None, password=None):
        if not username or not password: return None
        user = first_or_none(User, username=username)
        if not user:
            user = first_or_none(User, email=username)
        if not user: return user
        if user.password.startswith(MAGIC):
            stored = user.password[len(MAGIC):]
            if get_hash(password, stored) == stored:
                user.set_password(password)
                return user
        return None

class EmailBackend(ModelBackend):
    def authenticate(self, username=None, password=None):
        user = first_or_none(User, email=username)
        if not user: return user
        if user.check_password(password):
            return user
        return None

########NEW FILE########
__FILENAME__ = decorators
# -*- coding: utf-8 -*-
from django.shortcuts import render
from django.http import HttpResponse
from models import USER_AUTHORIZATION_LIMIT

def authorization_required(func):
    def decorated(request, *args, **kwargs):
        user = request.user
        if not user.is_superuser and not user.get_profile().is_authorized():
            return render(request, "not_authorized.html",
                          {"limit": USER_AUTHORIZATION_LIMIT,
                           "solved": user.get_profile().solved_problems})
        return func(request, *args, **kwargs)
    return decorated

def admin_required(func):
    def decorated(request, *args, **kwargs):
        user = request.user
        if not user.is_superuser:
            return HttpResponse('Unauthorized', status=401)
        return func(request, *args, **kwargs)
    return decorated

########NEW FILE########
__FILENAME__ = feeds
# -*- coding: utf-8 -*-
from django.contrib.syndication.views import Feed
from django.contrib.auth.models import User
from guardian.conf import settings
from forum.models import Post
from forum.utils import get_posts_for_user
from rendertext import render_text

class PostFeed(Feed):
    title = 'algospot.com posts'
    link = '/'
    description = u'알고스팟 새 글 목록'
    anonymous = User.objects.get(pk=settings.ANONYMOUS_USER_ID)

    def items(self):
        return get_posts_for_user(self.anonymous, 'forum.read_post').order_by('-created_on')[:30]
    def item_title(self, obj):
        return u'[%s] %s' % (obj.category.name, obj.title)
    def item_description(self, obj):
        return render_text(obj.text)
    def item_link(self, obj):
        return obj.get_absolute_url()

########NEW FILE########
__FILENAME__ = forms
# -*- coding: utf-8 -*-
from django import forms
from django.conf import settings
from django.utils.safestring import mark_safe
if settings.USE_AYAH:
    import ayah
from registration.forms import RegistrationForm
from registration.backends.default.views import RegistrationView

class SettingsForm(forms.Form):
    password1 = forms.CharField(widget=forms.PasswordInput(render_value=False),
                                required=False, label=u"비밀번호 변경")
    password2 = forms.CharField(widget=forms.PasswordInput(render_value=False),
                                required=False, label=u"비밀번호 (확인)")

    email = forms.EmailField(label=u"이메일", max_length=75)
    intro = forms.CharField(label=u"자기소개",
                            widget=forms.Textarea(attrs={"class": "large",
                                                         "rows": "5"}), required=False)

    def clean(self):
        if 'password1' in self.cleaned_data and 'password2' in self.cleaned_data:
            if self.cleaned_data['password1'] != self.cleaned_data['password2']:
                raise forms.ValidationError(u"비밀 번호가 일치하지 않습니다.")
        return self.cleaned_data

    def save(self, user):
        user.email = self.cleaned_data["email"]
        pw = self.cleaned_data['password1']
        if len(pw) > 0: user.set_password(pw)
        user.save()
        user.get_profile().intro = self.cleaned_data["intro"]
        user.get_profile().save()

class AreYouAHumanWidget(forms.HiddenInput):

    def render(self, name, value, attrs=None):
        # a hack :-(
        assert name == 'session_secret'
        return mark_safe(unicode(ayah.get_publisher_html()))

class AreYouAHumanField(forms.CharField):
    widget = AreYouAHumanWidget
    
    def clean(self, data):
        if not ayah.score_result(data):
            raise forms.ValidationError('Please solve the puzzle')

class AreYouAHumanForm(RegistrationForm):
    session_secret = AreYouAHumanField(label='')

class AreYouAHumanFormView(RegistrationView):
    def get_form_class(self, request):
        if settings.USE_AYAH: 
            ayah.configure(settings.AYAH_PUBLISHER_KEY, settings.AYAH_SCORING_KEY)
            return AreYouAHumanForm
        return RegistrationForm

########NEW FILE########
__FILENAME__ = code_convert
import re
from django.core.management.base import NoArgsCommand
from django.contrib.comments.models import Comment
from django.db.models.signals import post_save
from judge.models import Problem
from wiki.models import PageRevision
from forum.models import Post

class Command(NoArgsCommand):
    pattern = re.compile(r'<code lang=([^>]+)>(.+?)</code>', re.DOTALL)
    def replace(self, match):
        lang = match.group(1).strip('"\'')
        code = match.group(2).replace("\t", "  ")
        print u'#', 
        return u'~~~ %s\n%s\n~~~' % (lang, code)

    def handle(self, **options):
        post_save.disconnect(sender=PageRevision, dispatch_uid="wiki_edit_event")
        post_save.disconnect(sender=Comment, dispatch_uid="comment_event")
        post_save.disconnect(sender=Problem, dispatch_uid="saved_problem")
        post_save.disconnect(sender=Post, dispatch_uid="forum_post_event")

        print u'Posts...', 
        for x in Post.objects.all():
        	x.text = self.pattern.sub(self.replace, x.text)
        	x.save()
        print u'\nPageRevisions...', 
        for x in PageRevision.objects.all():
        	x.text = self.pattern.sub(self.replace, x.text)
        	x.save()
        print u'\nProblems...', 
        for x in Problem.objects.all():
        	x.description = self.pattern.sub(self.replace, x.description)
        	x.input = self.pattern.sub(self.replace, x.input)
        	x.output = self.pattern.sub(self.replace, x.output)
        	x.note = self.pattern.sub(self.replace, x.note)
        	x.save()
        print u'\nComments...', 
        for x in Comment.objects.all():
        	x.comment = self.pattern.sub(self.replace, x.comment)
        	x.save()
        print u'\nDone!'


########NEW FILE########
__FILENAME__ = fromvanilla
# -*- coding: utf-8 -*-
from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from django.conf import settings
from django.contrib.comments.models import Comment
from django.contrib.contenttypes.models import ContentType
from forum.models import Post, Category
from judge.models import Problem, Submission, Attachment
from djangoutils import get_or_none
from newsfeed.models import Activity
from newsfeed import get_activity
import datetime
from django.contrib.sites.models import Site
import MySQLdb
import MySQLdb.cursors
import hashlib
import shutil
import os
import re
import string
import time

def patch(key, val):
    act = get_or_none(Activity, key=key)
    if act:
        act.timestamp = val
        act.save()
    else:
        print "failed to find", key

accepted = string.letters + string.digits + "._-"
def escape(ch):
    if ch in accepted: return ch
    return "_%.3d_" % ord(ch)

def sanitize_filename(filename):
    return "".join(map(escape, filename))

def fetch_all(db, table, **where):
    c = db.cursor()
    where_clause = ""
    if where:
        where_clause = "WHERE " + " AND ".join(["%s=%s" % it for it in
            where.items()])

    c.execute("SELECT * FROM %s %s;" % (table, where_clause))
    return c.fetchall()
def migrate_user(db):
    username_seen = set()
    created = 0
    for u in fetch_all(db, "GDN_User"):
        if u["Name"] in username_seen:
            print "%s is a duplicate" % u["Name"]
            continue
        if u["Deleted"] == "1": continue
        pw = (u["Password"]
                if u["HashMethod"] != "Vanilla"
                else "sha1$deadbeef$" + u["Password"].replace("$", "_"))
        new_user = User(id=u["UserID"],
                username = u["Name"],
                date_joined=u["DateInserted"],
                email=u["Email"],
                is_active=True,
                last_login=u["DateLastActive"] or u["DateInserted"],
                password=pw,
                is_staff=(u["Admin"] == "1"),
                is_superuser=(u["Admin"] == "1"))
        new_user.save()
        # patch("joined-%d" % new_user.id, u["DateInserted"])
        created += 1
        if created % 10 == 0:
            print "created %d users so far" % created
        username_seen.add(u["Name"])
    u = User.objects.get(username="JongMan")
    u.is_superuser = True
    u.save()
    print "created %d users." % created

CATEGORY_MAP = {"freeboard": "free",
        "qna": "qna",
        "openlecture": "old",
        "contest": "old",
        "algospot_contest": "old",
        "editorial": "old",
        "aoj_board": "qna",
        "news": "news"
        }

def migrate_forum(db):
    category_id_map = {}
    for cat in fetch_all(db, "GDN_Category"):
        slug = CATEGORY_MAP.get(cat["UrlCode"], None)
        if not slug: continue
        category_id_map[cat["CategoryID"]] = (Category.objects.get(slug=slug),
                cat["UrlCode"])

    copied_posts, copied_comments = 0, 0
    for thread in fetch_all(db, "GDN_Discussion"):
        if thread["CategoryID"] not in category_id_map: continue
        cat, urlcode = category_id_map.get(thread["CategoryID"])
        new_post = Post(pk=thread["DiscussionID"],
                category=cat,
                title=(thread["Name"] if CATEGORY_MAP[urlcode] != "old"
                    else ("[%s] " % urlcode) + thread["Name"]),
                user=User.objects.get(pk=thread["InsertUserID"]),
                created_on=thread["DateInserted"],
                text=thread["Body"])
        new_post.save()
        new_post.created_on = thread["DateInserted"]
        new_post.save()
        patch("forum-post-%d" % new_post.id, thread["DateInserted"])

        comments = fetch_all(db, "GDN_Comment",
                DiscussionID=thread["DiscussionID"])
        for comment in comments:
            user = User.objects.get(pk=comment["InsertUserID"])
            new_comment = Comment(
                    user=user,
                    content_type=ContentType.objects.get_for_model(Post),
                    object_pk=new_post.pk,
                    comment=comment["Body"],
                    site_id=settings.SITE_ID,
                    submit_date=comment["DateInserted"])
            new_comment.save()
            patch("comment-%d" % new_comment.id, comment["DateInserted"])
            copied_comments += 1
        copied_posts += 1
        if copied_posts % 10 == 0:
            print "%d posts. %d comments." % (copied_posts, copied_comments)

    print "%d posts. %d comments." % (copied_posts, copied_comments)

def migrate_problems(db):
    PROBLEM_MAPPING = {
        "No": "id",
        "ID": "slug",
        "Updated": "updated_on",
        "State": "state",
        "Source": "source",
        "Name": "name",
        "Description": "description",
        "Input": "input",
        "Output": "output",
        "SampleInput": "sample_input",
        "SampleOutput": "sample_output",
        "Note": "note",
        "JudgeModule": "judge_module",
        "TimeLimit": "time_limit",
        "MemoryLimit": "memory_limit",
        "Accepted": "accepted_count",
        "Submissions": "submissions_count",
    }
    imported = 0
    categories = dict([(cat["No"], cat["Name"])
                       for cat in fetch_all(db, "GDN_ProblemCategory")])
    for k, v in categories.items():
        print k, v
    for problem in fetch_all(db, "GDN_Problem", State=3):
        kwargs = {}
        kwargs["user"] = User.objects.get(id=problem["Author"])
        for k, v in PROBLEM_MAPPING.items():
            kwargs[v] = problem[k]
        new_problem = Problem(**kwargs)
        new_problem.save()

        tags = []
        for rel in fetch_all(db, "GDN_ProblemCategoryActualRelation",
                             Problem=problem["No"]):
            if rel["Category"] in categories:
                tags.append(categories[rel["Category"]])
        print new_problem.slug, tags
        new_problem.tags = ",".join(tags)
        new_problem.save()

        # we don't have timestamp information for old problems.
        patch("new-problem-%d" % new_problem.id, datetime.datetime(2009, 7, 11,
                                                                   0, 0, 0, 0))
        imported += 1
    print "imported %d problems." % imported

def migrate_submissions(db):
    SUBMISSION_MAPPING = {
            "No": "id",
            "Submitted": "submitted_on",
            "IsPublic": "is_public",
            "Language": "language",
            "State": "state",
            "Length": "length",
            "Source": "source",
            "Message": "message",
            "Time": "time",
            "Memory": "memory"}
    imported = 0
    submissions = fetch_all(db, "GDN_Submission")
    Submission.objects.all().delete()
    Activity.objects.filter(key__startswith="solved-").delete()
    start = time.time()
    for submission in submissions:
        kwargs = {}
        try:
            kwargs["problem"] = Problem.objects.get(id=submission["Problem"])
        except:
            continue
        kwargs["user"] = User.objects.get(id=submission["Author"])
        for k, v in SUBMISSION_MAPPING.items():
            kwargs[v] = submission[k]
        if not kwargs["message"]:
            kwargs["message"] = ""
        kwargs["state"] = Submission.RECEIVED
        new_submission = Submission(**kwargs)
        new_submission.save()
        new_submission.state = submission["State"]
        new_submission.submitted_on = submission["Submitted"]
        new_submission.save()
        if kwargs["state"] == Submission.ACCEPTED:
            patch("solved-%d-%d" % (submission["Problem"], submission["Author"]),
                  submission["Submitted"])

        imported += 1
        if imported % 100 == 0:
            print "Migrated %d of %d submissions. (%d submissions/sec)" % (imported,
                                                                           len(submissions),
                                                                           imported
                                                                           /
                                                                           (time.time()-start)
                                                                          )
    print "Migrated %d submissions." % imported

def md5file(file_path):
    md5 = hashlib.md5()
    md5.update(open(file_path, "rb").read())
    return md5.hexdigest()

def migrate_attachments(db, upload):
    attachments = fetch_all(db, "GDN_Attachment")
    for attachment in attachments:
        origin = os.path.join(upload, attachment["Path"])
        md5 = md5file(origin)
        name = sanitize_filename(attachment["Name"])
        target_path = os.path.join("judge-attachments",
                                   md5, name)
        copy_to = os.path.join(settings.MEDIA_ROOT, target_path)
        try:
            os.makedirs(os.path.dirname(copy_to))
        except:
            pass
        shutil.copy(origin, copy_to)
        problem = get_or_none(Problem, id=attachment["Problem"])
        if not problem: continue
        new_attachment = Attachment(problem=problem,
                                    id=attachment["No"], file=target_path)
        new_attachment.save()

def fix_insertimage(db):
    def replace(mobj):
        attachment = Attachment.objects.get(id=int(mobj.group(1)))
        print attachment.file.url
        return "![%s](%s)" % (attachment.file.name.replace("]", "\]"),
                              attachment.file.url)
    for problem in Problem.objects.all():
        problem.description = re.sub('\[InsertImage\|([0-9]+)\]',
                                     replace,
                                     problem.description)
        problem.save()

def migrate_judge(db, upload):
    migrate_problems(db)
    migrate_submissions(db)
    migrate_attachments(db, upload)
    fix_insertimage(db)

class Command(BaseCommand):
    args = '<mysql host> <mysql user> <mysql password> <mysql db> <uploaded> [app]'
    help = 'Migrate data over from Vanilla\'s CSV dump'

    def handle(self, *args, **options):
        site = Site.objects.get(id=1)
        site.domain = 'prague.algospot.com'
        site.save()
        host, user, password, db, upload = args[:5]
        db = MySQLdb.connect(host=host, user=user, passwd=password, db=db,
                cursorclass=MySQLdb.cursors.DictCursor,use_unicode=True,charset='utf8')
        app = "all" if len(args) == 5 else args[5]
        if app in ["all", "user"]:
            migrate_user(db)
        if app in ["all", "forum"]:
            migrate_forum(db)
        if app in ["all", "judge"]:
            migrate_judge(db, upload)

########NEW FILE########
__FILENAME__ = include_everyone
from django.core.management.base import NoArgsCommand
from django.contrib.auth.models import User, Group

class Command(NoArgsCommand):
    def handle(self, **options):
        everyone = Group.objects.get(name='everyone')
        for x in User.objects.all():
            everyone.user_set.add(x)

########NEW FILE########
__FILENAME__ = 0001_initial
# encoding: utf-8
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models

class Migration(SchemaMigration):

    def forwards(self, orm):
        
        # Adding model 'UserProfile'
        db.create_table('base_userprofile', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('user', self.gf('django.db.models.fields.related.OneToOneField')(to=orm['auth.User'], unique=True)),
            ('posts', self.gf('django.db.models.fields.IntegerField')(default=0)),
            ('submissions', self.gf('django.db.models.fields.IntegerField')(default=0)),
            ('solved_problems', self.gf('django.db.models.fields.IntegerField')(default=0)),
        ))
        db.send_create_signal('base', ['UserProfile'])


    def backwards(self, orm):
        
        # Deleting model 'UserProfile'
        db.delete_table('base_userprofile')


    models = {
        'auth.group': {
            'Meta': {'object_name': 'Group'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '80'}),
            'permissions': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['auth.Permission']", 'symmetrical': 'False', 'blank': 'True'})
        },
        'auth.permission': {
            'Meta': {'ordering': "('content_type__app_label', 'content_type__model', 'codename')", 'unique_together': "(('content_type', 'codename'),)", 'object_name': 'Permission'},
            'codename': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'content_type': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['contenttypes.ContentType']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '50'})
        },
        'auth.user': {
            'Meta': {'object_name': 'User'},
            'date_joined': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'email': ('django.db.models.fields.EmailField', [], {'max_length': '75', 'blank': 'True'}),
            'first_name': ('django.db.models.fields.CharField', [], {'max_length': '30', 'blank': 'True'}),
            'groups': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['auth.Group']", 'symmetrical': 'False', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'is_active': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'is_staff': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'is_superuser': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'last_login': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'last_name': ('django.db.models.fields.CharField', [], {'max_length': '30', 'blank': 'True'}),
            'password': ('django.db.models.fields.CharField', [], {'max_length': '128'}),
            'user_permissions': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['auth.Permission']", 'symmetrical': 'False', 'blank': 'True'}),
            'username': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '30'})
        },
        'base.userprofile': {
            'Meta': {'object_name': 'UserProfile'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'posts': ('django.db.models.fields.IntegerField', [], {'default': '0'}),
            'solved_problems': ('django.db.models.fields.IntegerField', [], {'default': '0'}),
            'submissions': ('django.db.models.fields.IntegerField', [], {'default': '0'}),
            'user': ('django.db.models.fields.related.OneToOneField', [], {'to': "orm['auth.User']", 'unique': 'True'})
        },
        'contenttypes.contenttype': {
            'Meta': {'ordering': "('name',)", 'unique_together': "(('app_label', 'model'),)", 'object_name': 'ContentType', 'db_table': "'django_content_type'"},
            'app_label': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'model': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '100'})
        }
    }

    complete_apps = ['base']

########NEW FILE########
__FILENAME__ = 0002_auto__add_field_userprofile_intro
# encoding: utf-8
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models

class Migration(SchemaMigration):

    def forwards(self, orm):
        
        # Adding field 'UserProfile.intro'
        db.add_column('base_userprofile', 'intro', self.gf('django.db.models.fields.TextField')(default=''), keep_default=False)


    def backwards(self, orm):
        
        # Deleting field 'UserProfile.intro'
        db.delete_column('base_userprofile', 'intro')


    models = {
        'auth.group': {
            'Meta': {'object_name': 'Group'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '80'}),
            'permissions': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['auth.Permission']", 'symmetrical': 'False', 'blank': 'True'})
        },
        'auth.permission': {
            'Meta': {'ordering': "('content_type__app_label', 'content_type__model', 'codename')", 'unique_together': "(('content_type', 'codename'),)", 'object_name': 'Permission'},
            'codename': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'content_type': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['contenttypes.ContentType']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '50'})
        },
        'auth.user': {
            'Meta': {'object_name': 'User'},
            'date_joined': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'email': ('django.db.models.fields.EmailField', [], {'max_length': '75', 'blank': 'True'}),
            'first_name': ('django.db.models.fields.CharField', [], {'max_length': '30', 'blank': 'True'}),
            'groups': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['auth.Group']", 'symmetrical': 'False', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'is_active': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'is_staff': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'is_superuser': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'last_login': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'last_name': ('django.db.models.fields.CharField', [], {'max_length': '30', 'blank': 'True'}),
            'password': ('django.db.models.fields.CharField', [], {'max_length': '128'}),
            'user_permissions': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['auth.Permission']", 'symmetrical': 'False', 'blank': 'True'}),
            'username': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '30'})
        },
        'base.userprofile': {
            'Meta': {'object_name': 'UserProfile'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'intro': ('django.db.models.fields.TextField', [], {'default': "''"}),
            'posts': ('django.db.models.fields.IntegerField', [], {'default': '0'}),
            'solved_problems': ('django.db.models.fields.IntegerField', [], {'default': '0'}),
            'submissions': ('django.db.models.fields.IntegerField', [], {'default': '0'}),
            'user': ('django.db.models.fields.related.OneToOneField', [], {'to': "orm['auth.User']", 'unique': 'True'})
        },
        'contenttypes.contenttype': {
            'Meta': {'ordering': "('name',)", 'unique_together': "(('app_label', 'model'),)", 'object_name': 'ContentType', 'db_table': "'django_content_type'"},
            'app_label': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'model': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '100'})
        }
    }

    complete_apps = ['base']

########NEW FILE########
__FILENAME__ = 0003_auto__add_field_userprofile_accepted
# encoding: utf-8
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models

class Migration(SchemaMigration):

    def forwards(self, orm):
        
        # Adding field 'UserProfile.accepted'
        db.add_column('base_userprofile', 'accepted', self.gf('django.db.models.fields.IntegerField')(default=0), keep_default=False)


    def backwards(self, orm):
        
        # Deleting field 'UserProfile.accepted'
        db.delete_column('base_userprofile', 'accepted')


    models = {
        'auth.group': {
            'Meta': {'object_name': 'Group'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '80'}),
            'permissions': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['auth.Permission']", 'symmetrical': 'False', 'blank': 'True'})
        },
        'auth.permission': {
            'Meta': {'ordering': "('content_type__app_label', 'content_type__model', 'codename')", 'unique_together': "(('content_type', 'codename'),)", 'object_name': 'Permission'},
            'codename': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'content_type': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['contenttypes.ContentType']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '50'})
        },
        'auth.user': {
            'Meta': {'object_name': 'User'},
            'date_joined': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'email': ('django.db.models.fields.EmailField', [], {'max_length': '75', 'blank': 'True'}),
            'first_name': ('django.db.models.fields.CharField', [], {'max_length': '30', 'blank': 'True'}),
            'groups': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['auth.Group']", 'symmetrical': 'False', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'is_active': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'is_staff': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'is_superuser': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'last_login': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'last_name': ('django.db.models.fields.CharField', [], {'max_length': '30', 'blank': 'True'}),
            'password': ('django.db.models.fields.CharField', [], {'max_length': '128'}),
            'user_permissions': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['auth.Permission']", 'symmetrical': 'False', 'blank': 'True'}),
            'username': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '30'})
        },
        'base.userprofile': {
            'Meta': {'object_name': 'UserProfile'},
            'accepted': ('django.db.models.fields.IntegerField', [], {'default': '0'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'intro': ('django.db.models.fields.TextField', [], {'default': "''"}),
            'posts': ('django.db.models.fields.IntegerField', [], {'default': '0'}),
            'solved_problems': ('django.db.models.fields.IntegerField', [], {'default': '0'}),
            'submissions': ('django.db.models.fields.IntegerField', [], {'default': '0'}),
            'user': ('django.db.models.fields.related.OneToOneField', [], {'to': "orm['auth.User']", 'unique': 'True'})
        },
        'contenttypes.contenttype': {
            'Meta': {'ordering': "('name',)", 'unique_together': "(('app_label', 'model'),)", 'object_name': 'ContentType', 'db_table': "'django_content_type'"},
            'app_label': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'model': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '100'})
        }
    }

    complete_apps = ['base']

########NEW FILE########
__FILENAME__ = models
# -*- coding: utf-8 -*-

from django.db import models
from django.db.models.signals import pre_delete, post_save
from django.dispatch import receiver
from django.contrib.auth.models import User, Group
from django.contrib.contenttypes.models import ContentType
from django.contrib.comments.models import Comment
from guardian.shortcuts import get_perms, get_users_with_perms, get_groups_with_perms
from judge.models import Problem
from newsfeed import publish, depublish

# 이만큼은 문제를 풀어야 위키 변경 등의 일을 할 수 있다.
USER_AUTHORIZATION_LIMIT = 5

class UserProfile(models.Model):
    """Stores additional information about users."""
    user = models.OneToOneField(User)
    posts = models.IntegerField(null=False, default=0)

    submissions = models.IntegerField(null=False, default=0)
    accepted = models.IntegerField(null=False, default=0)
    solved_problems = models.IntegerField(null=False, default=0)

    intro = models.TextField(default="")

    def is_authorized(self):
        return self.solved_problems >= USER_AUTHORIZATION_LIMIT or self.user.is_superuser

@receiver(post_save, sender=User)
def user_added(sender, **kwargs):
    if kwargs["created"]:
        user = kwargs["instance"]
        """ add the user to group 'everyone'. """
        Group.objects.get(name='everyone').user_set.add(user)

        """ automatically create profile classes when a user is created."""
        profile = UserProfile(user=user)
        profile.save()
        # publish("joined-%d" % user.id ,
        #         "other",
        #         "joined",
        #         actor=user,
        #         verb=u"가입했습니다.")

@receiver(pre_delete, sender=User)
def deleting_user(sender, **kwargs):
    user = kwargs["instance"]
    user.get_profile().delete()
    # depublish("joined-%d" % user.id)

def comment_handler(sender, **kwargs):
    instance, created = kwargs["instance"], kwargs["created"]
    profile = instance.user.get_profile()
    target = instance.content_object

    ctype = ContentType.objects.get_for_model(target)
    visible_users = None
    visible_groups = None
    if ctype.name == 'post':
        print 'post'
        print target.category
        visible_users = get_users_with_perms(target.category, with_group_users=False)
        visible_groups = get_groups_with_perms(target.category)
    if ctype.name == 'problem' and target.state != Problem.PUBLISHED:
        visible_users = get_users_with_perms(target, with_group_users=False)
        visible_groups = get_groups_with_perms(target)

    print visible_users
    print visible_groups

    if created:
        publish("comment-%d" % instance.id,
                "posts",
                "commented",
                actor=instance.user,
                action_object=instance,
                target=target,
                timestamp=instance.submit_date,
                visible_users=visible_users,
                visible_groups=visible_groups,
                verb=u"{target}에 새 댓글을 달았습니다: "
                u"{action_object}")
        profile.posts += 1
    elif instance.is_removed:
        depublish("comment-%d" % instance.id)
        profile.posts -= 1
    profile.save()

post_save.connect(comment_handler, sender=Comment,
                  dispatch_uid="comment_event")

########NEW FILE########
__FILENAME__ = processors
from datetime import datetime

CAMPAIGNS = [
    {
        'name': 'techplanet', 
        'start': datetime(2012, 10, 8, 9, 0, 0),
        'end': datetime(2012, 10, 25, 23, 59, 59),
        'image': '/static/images/banners/techplanet.jpg',
        'link': 'http://www.techplanet.kr/'
    },
    {
        'name': 'codesprint', 
        'start': datetime(2012, 10, 8, 9, 0, 0),
        'end': datetime(2012, 11, 4, 23, 59, 59),
        'image': '/static/images/banners/codesprint.gif',
        'link': 'http://www.codesprint.kr/'
    },
    {
        'name': 'codesprint2013',
        'start': datetime(2013, 6, 18, 0, 0, 0),
        'end': datetime(2013, 7, 14, 0, 0, 0),
        'image': '/static/images/banners/codesprint2013.png',
        'link': 'http://codesprint.skplanet.com/'
    }
]

def select_campaign(request):
    campaign = None
    now = datetime.now()
    for c in CAMPAIGNS:
        if c['start'] <= now <= c['end']:
            campaign = c
            break
    return {'campaign': campaign}
    


########NEW FILE########
__FILENAME__ = search_indexes
import datetime
from haystack import indexes
from django.contrib.comments.models import Comment

class CommentIndex(indexes.SearchIndex, indexes.Indexable):
    text = indexes.EdgeNgramField(document=True, model_attr='comment')
    date = indexes.DateTimeField(model_attr='submit_date')

    def get_model(self):
        return Comment

    def index_queryset(self, using=None):
        return self.get_model().objects.filter(submit_date__lte=datetime.datetime.now())

    def get_updated_field(self):
        return 'submit_date'

########NEW FILE########
__FILENAME__ = avatar_custom_tags
from django import template

register = template.Library()

@register.filter
def avatar_url(value):
    return value.avatar_url(80)

########NEW FILE########
__FILENAME__ = common_tags
# -*- coding: utf-8 -*-
from __future__ import division
from diff_match_patch import diff_match_patch
from django.core.urlresolvers import reverse
from django.utils.safestring import mark_safe
from django import template
from django.contrib.comments.templatetags.comments import BaseCommentNode
from rendertext import render_text as actual_render_text
from rendertext import render_latex as actual_render_latex
from pygments import highlight
from pygments.lexers import get_lexer_by_name
from pygments.formatters import HtmlFormatter
import datetime
import itertools
import re

register = template.Library()

class GetLastCommentNode(BaseCommentNode):
    """ Get last comment into the context. """
    def get_context_value_from_queryset(self, context, qs):
        return qs.order_by("-id")[0] if qs.exists() else qs.none()

@register.tag
def get_last_comment(parser, token):
    return GetLastCommentNode.handle_token(parser, token)

class SourceCodeNode(template.Node):
    def __init__(self, code, lang):
        self.code = template.Variable(code)
        self.lang = template.Variable(lang)
    def render(self, context):
        code = self.code.resolve(context)
        lang = self.lang.resolve(context)
        lexer = get_lexer_by_name(lang)
        formatter = HtmlFormatter(style="colorful")
        return highlight(code, lexer, formatter).replace("\n", "<br/>")

@register.tag
def syntax_highlight(parser, token):
    toks = token.split_contents()
    code, lang = toks[1:3]
    return SourceCodeNode(code, lang)

class TableHeaderNode(template.Node):
    def __init__(self, column_name, order_by, options):
        self.column_name = template.Variable(column_name)
        self.order_by = template.Variable(order_by)
        self.options = set(options)

    def render(self, context):
        current_order = context['request'].GET.get('order_by', '')
        column_name = self.column_name.resolve(context)
        order_by = self.order_by.resolve(context)
        arrow = ""
        is_default = 'default' in self.options
        if is_default and current_order == '': current_order = order_by

        can_toggle = 'notoggle' not in self.options
        if order_by == current_order:
            arrow = u"↓"
            if not can_toggle:
                return column_name + arrow
            else:
                new_order = '-' + order_by
        else:
            new_order = order_by
            if current_order.endswith(order_by):
                arrow = u"↑"

        get_params = dict(context['request'].GET)
        get_params['order_by'] = [new_order]
        get_params = '&'.join('%s=%s' % (k, v[0]) for k, v in get_params.items())
        full_path = context['request'].get_full_path().split('?')[0]
        return mark_safe(u"""<a href="%s?%s">%s%s</a>""" % (full_path, get_params, column_name, arrow))

@register.tag
def sortable_table_header(parser, token):
    toks = token.split_contents()
    column_name, order_by = toks[1:3]
    return TableHeaderNode(column_name, order_by, toks[3:])

@register.filter
def get_comment_hotness(count):
    threshold = [1, 5, 10, 50, 100]
    name = ["has_comment", "some_discussions", "heated_discussions",
            "very_heated_discussions", "wow"]
    ret = "none"
    for cnt, nam in zip(threshold, name):
        if cnt <= count:
            ret = nam
    return ret

@register.filter
def print_username(user):
    profile_link = reverse('user_profile', kwargs={"user_id": user.id})
    return mark_safe('<a href="%s" class="username">%s</a>' %
            (profile_link, user.username))

units = [(int(365.2425*24*60*60), u"년"),
         (30*24*60*60, u"달"),
         (7*24*60*60, u"주"),
         (24*60*60, u"일"),
         (60*60, u"시간"),
         (60, u"분")]

def format_readable(diff):
    for size, name in units:
        if diff >= size:
            return u"%d%s 전" % (int(diff / size), name)
    return u"방금 전"

@register.filter
def print_datetime(dt):
    fallback = dt.strftime("%Y/%m/%d %H:%M")
    diff = datetime.datetime.now() - dt
    # python 2.6 compatibility. no total_seconds() :(
    diff = diff.seconds + diff.days * 24 * 3600
    class_name = "hot" if diff < 24*3600 else ""
    return mark_safe(u'<span class="%s" title="%s">%s</span>' % (class_name,
        fallback, format_readable(diff) or fallback))

@register.filter
def render_text(text):
    return mark_safe(actual_render_text(text))

@register.filter
def render_latex(text):
    return mark_safe(actual_render_latex(text))

@register.filter
def safe_latex(text):
    return mark_safe(text.replace('$', "\\$") \
               .replace('#', "\\#") \
               .replace('%', "\\%") \
               .replace('&', "\\&") \
               .replace('_', "\\_") \
               .replace('{', "\\{") \
               .replace('}', "\\}") \
               .replace('^', "\\^{}") \
               .replace('~', "\\~{}"))

class PercentNode(template.Node):
    def __init__(self, a, b):
        self.a = template.Variable(a)
        self.b = template.Variable(b)
    def render(self, context):
        a = self.a.resolve(context)
        b = self.b.resolve(context)
        return str(int(a * 100 / b)) if b else "0"

@register.tag
def percentage(parser, token):
    toks = token.split_contents()
    a, b = toks[1:3]
    return PercentNode(a, b)

# shamelessly copied from
# http://code.activestate.com/recipes/577784-line-based-side-by-side-diff/

def side_by_side_diff(diff):
    """
    Calculates a side-by-side line-based difference view.
    
    Wraps insertions in <ins></ins> and deletions in <del></del>.
    """
    def yield_open_entry(open_entry):
        """ Yield all open changes. """
        ls, rs = open_entry
        # Get unchanged parts onto the right line
        if ls[0] == rs[0]:
            yield (False, ls[0], rs[0])
            for l, r in itertools.izip_longest(ls[1:], rs[1:]):
                yield (True, l, r)
        elif ls[-1] == rs[-1]:
            for l, r in itertools.izip_longest(ls[:-1], rs[:-1]):
                yield (l != r, l, r)
            yield (False, ls[-1], rs[-1])
        else:
            for l, r in itertools.izip_longest(ls, rs):
                yield (True, l, r)
 
    line_split = re.compile(r'(?:\r?\n)')
    open_entry = ([None], [None])
    for change_type, entry in diff:
        assert change_type in [-1, 0, 1]

        entry = (entry.replace('&', '&amp;')
                      .replace('<', '&lt;')
                      .replace('>', '&gt;'))

        lines = line_split.split(entry)

        # Merge with previous entry if still open
        ls, rs = open_entry

        line = lines[0]
        if line:
            if change_type == 0:
                ls[-1] = ls[-1] or ''
                rs[-1] = rs[-1] or ''
                ls[-1] = ls[-1] + line
                rs[-1] = rs[-1] + line
            elif change_type == 1:
                rs[-1] = rs[-1] or ''
                rs[-1] += '<ins>%s</ins>' % line if line else ''
            elif change_type == -1:
                ls[-1] = ls[-1] or ''
                ls[-1] += '<del>%s</del>' % line if line else ''
                
        lines = lines[1:]

        if lines:
            if change_type == 0:
                # Push out open entry
                for entry in yield_open_entry(open_entry):
                    yield entry
                
                # Directly push out lines until last
                for line in lines[:-1]:
                    yield (False, line, line)
                
                # Keep last line open
                open_entry = ([lines[-1]], [lines[-1]])
            elif change_type == 1:
                ls, rs = open_entry
                
                for line in lines:
                    rs.append('<ins>%s</ins>' % line if line else '')
                
                open_entry = (ls, rs)
            elif change_type == -1:
                ls, rs = open_entry
                
                for line in lines:
                    ls.append('<del>%s</del>' % line if line else '')
                
                open_entry = (ls, rs)

    # Push out open entry
    for entry in yield_open_entry(open_entry):
        yield entry

line_split = re.compile(r'(?:\r?\n)')
@register.filter
def html_diff(diff):
    left_line = 0
    right_line = 0
    changing = False
    last_unchanged_line = None
    consecutive_unchanged_lines = 0
    html = []
    html.append('<table>')
    for changed, left, right in side_by_side_diff(diff):
        if left != None:
            left_line += 1
        if right != None:
            right_line += 1
        if not changed:
            last_unchanged_line = (left_line, right_line, left)
            consecutive_unchanged_lines += 1
            if consecutive_unchanged_lines >= 2:
                changing = False
            if changing:
                html.append('<tr><td class="unchanged" colspan="2"><pre>%s</pre></td></tr>' % (left + '&para;' if left != None else ' '))
        else:
            consecutive_unchanged_lines = 0
            if not changing:
                if last_unchanged_line:
                    last_left_line, last_right_line, last_text = last_unchanged_line
                    html.append('<tr><td class="line-no diff-left">Line %d</td><td class="line-no diff-right">Line %d</td></tr>' % (last_left_line, last_right_line))
                    html.append('<tr><td class="unchanged" colspan="2"><pre>%s</pre></td></tr>' % (last_text + '&para;' if last_text != None else ' '))
                else:
                    html.append('<tr><td class="line-no diff-left">Line %d</td><td class="line-no diff-right">Line %d</td></tr>' % (left_line, right_line))
            changing = True
            html.append('<tr>')
            html.append('<td class="diff-left %s"><pre>%s</pre></td>' % ('empty' if left == None else '', left + '&para;' if left != None else ' '))
            html.append('<td class="diff-right %s"><pre>%s</pre></td>' % ('empty' if right == None else '', right + '&para;' if right != None else ' '))
            html.append('</tr>')
    html.append('</table>')
    return mark_safe("".join(html))

########NEW FILE########
__FILENAME__ = tests
"""
This file demonstrates writing tests using the unittest module. These will pass
when you run "manage.py test".

Replace this with more appropriate tests for your application.
"""

from django.test import TestCase


class SimpleTest(TestCase):
    def test_basic_addition(self):
        """
        Tests that 1 + 1 always equals 2.
        """
        self.assertEqual(1 + 1, 2)

########NEW FILE########
__FILENAME__ = urls
# -*- coding: utf-8 -*-
from django.conf.urls.defaults import patterns, url
import views
urlpatterns = patterns(
    'base.views',
    url(r'^profile/(?P<user_id>.+)$', views.profile, name='user_profile'),
    url(r'^settings/(?P<user_id>.+)$', views.settings, name='user_settings'),
)


########NEW FILE########
__FILENAME__ = views
# -*- coding: utf-8 -*-
from django.shortcuts import render, redirect, get_object_or_404
from django.core.urlresolvers import reverse
from django.contrib.auth.models import User
from django.http import HttpResponseForbidden, Http404
from django.contrib.comments.views.moderation import perform_delete
from django.contrib.comments.models import Comment
from forms import SettingsForm
from django.conf import settings as django_settings
from django.contrib.contenttypes.models import ContentType
from tagging.models import TaggedItem
from newsfeed.models import Activity
from newsfeed.utils import get_activities_for_user
from judge.models import Problem, Solver, Submission
from forum.models import Category, Post
from base.models import UserProfile
import pygooglechart as pgc
from collections import defaultdict

def index(request):
    news_category = Category.objects.get(slug='news')
    recent_news = Post.objects.filter(category=news_category).order_by('-modified_on')[0]
    recent_activity = get_activities_for_user(request.user).exclude(category='solved').order_by("-timestamp")
    recent_activity = recent_activity[:10].all()
    return render(request, "index.html",
                  {'title': u'알고스팟에 오신 것을 환영합니다!',
                   'news': recent_news,
                   'actions': recent_activity,
                  })

def get_submission_chart_url(user):
    by_user = Submission.objects.filter(user=user)
    return Submission.get_verdict_distribution_graph(by_user)

# TODO: cache this function somehow
def get_category_chart(user):
    solved_problems = set()
    for s in Solver.objects.filter(user=user, solved=True):
        solved_problems.add(s.problem)
    problem_count = defaultdict(int)
    solved_count = defaultdict(int)
    # 문제/태그 쌍을 모두 순회하자.
    problem_id = ContentType.objects.get_for_model(Problem).id
    for item in TaggedItem.objects.filter(content_type=problem_id).all():
        problem, tag = item.object, item.tag
        if problem.state != Problem.PUBLISHED: continue
        problem_count[tag] += 1
        if problem in solved_problems:
            solved_count[tag] += 1
    # 문제 수가 많은 순서대로 태그들을 정렬한다
    tags_ordered = sorted([(-value, key) for key, value in problem_count.items()])
    # 문제 수가 가장 많은 n개의 태그를 고른다
    tags_display = [t for _, t in tags_ordered[:8]]
    # 나머지를 "나머지" 카테고리로 묶는다
    others_problems = others_solved = 0
    for tag in problem_count.keys():
        if tag not in tags_display:
            others_problems += problem_count[tag]
            others_solved += solved_count[tag]

    progress = [solved_count[tag] * 100 / problem_count[tag]
                for tag in tags_display]
    labels = [tag.name.encode('utf-8') for tag in tags_display]
    if others_problems > 0:
        progress.append(others_solved * 100 / others_problems)
        labels.append(u'기타'.encode('utf-8'))

    # 구글 차트
    chart = pgc.StackedVerticalBarChart(400, 120, y_range=(0, 100))
    chart.add_data(progress)
    chart.set_grid(0, 25, 5, 5)
    chart.set_colours(['C02942'])
    chart.set_axis_labels(pgc.Axis.LEFT, ["", "25", "50", "75", "100"])
    chart.set_axis_labels(pgc.Axis.BOTTOM, labels)
    chart.fill_solid("bg", "65432100")
    return chart.get_url() + "&chbh=r,3"


def profile(request, user_id):
    if not user_id.isdigit(): raise Http404
    user = get_object_or_404(User, id=user_id)
    comment_count = Comment.objects.filter(user=user).count()
    problem_count = Problem.objects.filter(user=user, state=Problem.PUBLISHED).count()
    attempted_problem_count = Solver.objects.filter(user=user).count()
    all_problem_count = Problem.objects.filter(state=Problem.PUBLISHED).count()
    submission_chart = get_submission_chart_url(user)
    failed_problem_count = Solver.objects.filter(user=user, solved=False).count()
    category_chart = get_category_chart(user)
    actions = get_activities_for_user(request.user).filter(actor=user).order_by("-timestamp")
    rank = UserProfile.objects.filter(solved_problems__gt=
                                      user.get_profile().solved_problems).count()
    return render(request, "user_profile.html",
                  {"profile_user": user,
                   "post_count": user.get_profile().posts - comment_count,
                   "problem_count": problem_count,
                   "comment_count": comment_count,
                   "attempted_problem_count": attempted_problem_count,
                   "all_problem_count": all_problem_count,
                   "failed_problem_count": failed_problem_count,
                   "not_attempted_problem_count": all_problem_count - attempted_problem_count,
                   "submission_chart_url": submission_chart,
                   "category_chart_url": category_chart,
                   "actions": actions,
                   "oj_rank": rank+1,
                   "oj_rank_page": (rank / django_settings.ITEMS_PER_PAGE)+1,
                  })

def settings(request, user_id):
    user = get_object_or_404(User, id=user_id)
    if request.user != user and not request.user.is_superuser:
        return HttpResponseForbidden("Forbidden operation.")
    form = SettingsForm(data=request.POST or None,
                        initial={"email": user.email, "intro": user.get_profile().intro})
    if request.method == "POST" and form.is_valid():
        form.save(user)
        return redirect(reverse("user_profile", kwargs={"user_id": user_id}))
    return render(request, "settings.html",
                  {"form": form, "settings_user": user})

def delete_comment(request, comment_id):
    """
    overriding default comments app's delete, so comment owners can always
    delete their comments.
    """
    comment = get_object_or_404(Comment, pk=comment_id)
    user = request.user
    if not user.is_superuser and user != comment.user:
        return HttpResponseForbidden("Forbidden operation.")

    # Delete on POST
    if request.method == 'POST':
        # Flag the comment as deleted instead of actually deleting it.
        perform_delete(request, comment)
        return redirect(request.POST["next"])

    # Render a form on GET
    else:
        return render(request, "comments/delete.html",
                      {"comment": comment,
                       "next": request.GET.get("next", "/")})

def calendar(request):
    return render(request, "calendar.html", {'title': u'알고스팟 캘린더'})

########NEW FILE########
__FILENAME__ = admin
from django.contrib import admin
from forum.models import Category
from guardian.admin import GuardedModelAdmin

admin.site.register(Category, GuardedModelAdmin)

########NEW FILE########
__FILENAME__ = forms
# -*- coding: utf-8 -*-
from django import forms
from models import Post, Category

class WriteForm(forms.ModelForm):
    class Meta:
        model = Post
        exclude = ('user',)
        fields = ('category', 'title', 'text')
    def __init__(self, categories, **kwargs):
        super(WriteForm, self).__init__(**kwargs)
        self.fields['category'].queryset = categories

########NEW FILE########
__FILENAME__ = 0001_initial
# encoding: utf-8
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models

class Migration(SchemaMigration):

    def forwards(self, orm):
        
        # Adding model 'Category'
        db.create_table('forum_category', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('name', self.gf('django.db.models.fields.TextField')()),
            ('slug', self.gf('django.db.models.fields.TextField')()),
        ))
        db.send_create_signal('forum', ['Category'])

        # Adding model 'Post'
        db.create_table('forum_post', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('title', self.gf('django.db.models.fields.TextField')(max_length=100)),
            ('created_on', self.gf('django.db.models.fields.DateTimeField')(auto_now_add=True, blank=True)),
            ('user', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['auth.User'])),
            ('text', self.gf('django.db.models.fields.TextField')()),
        ))
        db.send_create_signal('forum', ['Post'])


    def backwards(self, orm):
        
        # Deleting model 'Category'
        db.delete_table('forum_category')

        # Deleting model 'Post'
        db.delete_table('forum_post')


    models = {
        'auth.group': {
            'Meta': {'object_name': 'Group'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '80'}),
            'permissions': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['auth.Permission']", 'symmetrical': 'False', 'blank': 'True'})
        },
        'auth.permission': {
            'Meta': {'ordering': "('content_type__app_label', 'content_type__model', 'codename')", 'unique_together': "(('content_type', 'codename'),)", 'object_name': 'Permission'},
            'codename': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'content_type': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['contenttypes.ContentType']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '50'})
        },
        'auth.user': {
            'Meta': {'object_name': 'User'},
            'date_joined': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'email': ('django.db.models.fields.EmailField', [], {'max_length': '75', 'blank': 'True'}),
            'first_name': ('django.db.models.fields.CharField', [], {'max_length': '30', 'blank': 'True'}),
            'groups': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['auth.Group']", 'symmetrical': 'False', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'is_active': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'is_staff': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'is_superuser': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'last_login': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'last_name': ('django.db.models.fields.CharField', [], {'max_length': '30', 'blank': 'True'}),
            'password': ('django.db.models.fields.CharField', [], {'max_length': '128'}),
            'user_permissions': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['auth.Permission']", 'symmetrical': 'False', 'blank': 'True'}),
            'username': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '30'})
        },
        'contenttypes.contenttype': {
            'Meta': {'ordering': "('name',)", 'unique_together': "(('app_label', 'model'),)", 'object_name': 'ContentType', 'db_table': "'django_content_type'"},
            'app_label': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'model': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '100'})
        },
        'forum.category': {
            'Meta': {'object_name': 'Category'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.TextField', [], {}),
            'slug': ('django.db.models.fields.TextField', [], {})
        },
        'forum.post': {
            'Meta': {'object_name': 'Post'},
            'created_on': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'text': ('django.db.models.fields.TextField', [], {}),
            'title': ('django.db.models.fields.TextField', [], {'max_length': '100'}),
            'user': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['auth.User']"})
        }
    }

    complete_apps = ['forum']

########NEW FILE########
__FILENAME__ = 0002_auto__add_field_post_category
# encoding: utf-8
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models

class Migration(SchemaMigration):

    def forwards(self, orm):
        
        # Adding field 'Post.category'
        db.add_column('forum_post', 'category', self.gf('django.db.models.fields.related.ForeignKey')(default=1, to=orm['forum.Category']), keep_default=False)


    def backwards(self, orm):
        
        # Deleting field 'Post.category'
        db.delete_column('forum_post', 'category_id')


    models = {
        'auth.group': {
            'Meta': {'object_name': 'Group'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '80'}),
            'permissions': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['auth.Permission']", 'symmetrical': 'False', 'blank': 'True'})
        },
        'auth.permission': {
            'Meta': {'ordering': "('content_type__app_label', 'content_type__model', 'codename')", 'unique_together': "(('content_type', 'codename'),)", 'object_name': 'Permission'},
            'codename': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'content_type': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['contenttypes.ContentType']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '50'})
        },
        'auth.user': {
            'Meta': {'object_name': 'User'},
            'date_joined': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'email': ('django.db.models.fields.EmailField', [], {'max_length': '75', 'blank': 'True'}),
            'first_name': ('django.db.models.fields.CharField', [], {'max_length': '30', 'blank': 'True'}),
            'groups': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['auth.Group']", 'symmetrical': 'False', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'is_active': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'is_staff': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'is_superuser': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'last_login': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'last_name': ('django.db.models.fields.CharField', [], {'max_length': '30', 'blank': 'True'}),
            'password': ('django.db.models.fields.CharField', [], {'max_length': '128'}),
            'user_permissions': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['auth.Permission']", 'symmetrical': 'False', 'blank': 'True'}),
            'username': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '30'})
        },
        'contenttypes.contenttype': {
            'Meta': {'ordering': "('name',)", 'unique_together': "(('app_label', 'model'),)", 'object_name': 'ContentType', 'db_table': "'django_content_type'"},
            'app_label': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'model': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '100'})
        },
        'forum.category': {
            'Meta': {'object_name': 'Category'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.TextField', [], {}),
            'slug': ('django.db.models.fields.TextField', [], {})
        },
        'forum.post': {
            'Meta': {'object_name': 'Post'},
            'category': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['forum.Category']"}),
            'created_on': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'text': ('django.db.models.fields.TextField', [], {}),
            'title': ('django.db.models.fields.TextField', [], {'max_length': '100'}),
            'user': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['auth.User']"})
        }
    }

    complete_apps = ['forum']

########NEW FILE########
__FILENAME__ = 0003_auto__chg_field_post_title
# encoding: utf-8
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models

class Migration(SchemaMigration):

    def forwards(self, orm):
        
        # Changing field 'Post.title'
        db.alter_column('forum_post', 'title', self.gf('django.db.models.fields.CharField')(max_length=100))


    def backwards(self, orm):
        
        # Changing field 'Post.title'
        db.alter_column('forum_post', 'title', self.gf('django.db.models.fields.TextField')(max_length=100))


    models = {
        'auth.group': {
            'Meta': {'object_name': 'Group'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '80'}),
            'permissions': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['auth.Permission']", 'symmetrical': 'False', 'blank': 'True'})
        },
        'auth.permission': {
            'Meta': {'ordering': "('content_type__app_label', 'content_type__model', 'codename')", 'unique_together': "(('content_type', 'codename'),)", 'object_name': 'Permission'},
            'codename': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'content_type': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['contenttypes.ContentType']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '50'})
        },
        'auth.user': {
            'Meta': {'object_name': 'User'},
            'date_joined': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'email': ('django.db.models.fields.EmailField', [], {'max_length': '75', 'blank': 'True'}),
            'first_name': ('django.db.models.fields.CharField', [], {'max_length': '30', 'blank': 'True'}),
            'groups': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['auth.Group']", 'symmetrical': 'False', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'is_active': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'is_staff': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'is_superuser': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'last_login': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'last_name': ('django.db.models.fields.CharField', [], {'max_length': '30', 'blank': 'True'}),
            'password': ('django.db.models.fields.CharField', [], {'max_length': '128'}),
            'user_permissions': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['auth.Permission']", 'symmetrical': 'False', 'blank': 'True'}),
            'username': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '30'})
        },
        'contenttypes.contenttype': {
            'Meta': {'ordering': "('name',)", 'unique_together': "(('app_label', 'model'),)", 'object_name': 'ContentType', 'db_table': "'django_content_type'"},
            'app_label': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'model': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '100'})
        },
        'forum.category': {
            'Meta': {'object_name': 'Category'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.TextField', [], {}),
            'slug': ('django.db.models.fields.TextField', [], {})
        },
        'forum.post': {
            'Meta': {'object_name': 'Post'},
            'category': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['forum.Category']"}),
            'created_on': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'text': ('django.db.models.fields.TextField', [], {}),
            'title': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'user': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['auth.User']"})
        }
    }

    complete_apps = ['forum']

########NEW FILE########
__FILENAME__ = 0004_auto__add_field_post_modified_on
# encoding: utf-8
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models

class Migration(SchemaMigration):

    def forwards(self, orm):
        
        # Adding field 'Post.modified_on'
        db.add_column('forum_post', 'modified_on', self.gf('django.db.models.fields.DateTimeField')(auto_now=True, default=datetime.datetime(2012, 2, 21, 8, 42, 15, 370857), blank=True), keep_default=False)


    def backwards(self, orm):
        
        # Deleting field 'Post.modified_on'
        db.delete_column('forum_post', 'modified_on')


    models = {
        'auth.group': {
            'Meta': {'object_name': 'Group'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '80'}),
            'permissions': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['auth.Permission']", 'symmetrical': 'False', 'blank': 'True'})
        },
        'auth.permission': {
            'Meta': {'ordering': "('content_type__app_label', 'content_type__model', 'codename')", 'unique_together': "(('content_type', 'codename'),)", 'object_name': 'Permission'},
            'codename': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'content_type': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['contenttypes.ContentType']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '50'})
        },
        'auth.user': {
            'Meta': {'object_name': 'User'},
            'date_joined': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'email': ('django.db.models.fields.EmailField', [], {'max_length': '75', 'blank': 'True'}),
            'first_name': ('django.db.models.fields.CharField', [], {'max_length': '30', 'blank': 'True'}),
            'groups': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['auth.Group']", 'symmetrical': 'False', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'is_active': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'is_staff': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'is_superuser': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'last_login': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'last_name': ('django.db.models.fields.CharField', [], {'max_length': '30', 'blank': 'True'}),
            'password': ('django.db.models.fields.CharField', [], {'max_length': '128'}),
            'user_permissions': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['auth.Permission']", 'symmetrical': 'False', 'blank': 'True'}),
            'username': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '30'})
        },
        'contenttypes.contenttype': {
            'Meta': {'ordering': "('name',)", 'unique_together': "(('app_label', 'model'),)", 'object_name': 'ContentType', 'db_table': "'django_content_type'"},
            'app_label': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'model': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '100'})
        },
        'forum.category': {
            'Meta': {'object_name': 'Category'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.TextField', [], {}),
            'slug': ('django.db.models.fields.TextField', [], {})
        },
        'forum.post': {
            'Meta': {'object_name': 'Post'},
            'category': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['forum.Category']"}),
            'created_on': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'modified_on': ('django.db.models.fields.DateTimeField', [], {'auto_now': 'True', 'blank': 'True'}),
            'text': ('django.db.models.fields.TextField', [], {}),
            'title': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'user': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['auth.User']"})
        }
    }

    complete_apps = ['forum']

########NEW FILE########
__FILENAME__ = models
# -*- coding: utf-8 -*-
from django.db import models
from django.core.urlresolvers import reverse
from django.db.models.signals import post_save, pre_delete
from django.contrib.auth.models import User, Group
from guardian.shortcuts import get_perms, get_users_with_perms, get_groups_with_perms
from newsfeed import publish, depublish, depublish_where

class Category(models.Model):
    """Stores a post category."""
    name = models.TextField()
    slug = models.TextField()

    def __unicode__(self):
        return self.name

    def get_absolute_url(self):
        return reverse('forum-list', args=[self.slug, 1])

    class Meta:
        permissions = (
            ('read_post', 'Can read post'),
            ('write_post', 'Can write post'),
        )

class Post(models.Model):
    """Stores a forum post."""
    title = models.CharField(u"제목", max_length=100)
    created_on = models.DateTimeField(auto_now_add=True)
    modified_on = models.DateTimeField(auto_now=True)
    user = models.ForeignKey(User, null=False)
    text = models.TextField(u"내용")
    category = models.ForeignKey(Category, null=False, verbose_name=u"게시판")

    def __unicode__(self):
        return self.title

    def get_absolute_url(self):
        return reverse('forum-read', args=[self.id])

def post_handler(sender, **kwargs):
    instance, created = kwargs["instance"], kwargs["created"]
    if not created: return
    profile = instance.user.get_profile()
    profile.posts += 1
    profile.save()

    # 해당 오브젝트에 대해 아무 퍼미션이나 있으면 처리됨
    visible_users = get_users_with_perms(instance.category, with_group_users=False)
    visible_groups = get_groups_with_perms(instance.category)

    publish("forum-post-%d" % instance.id,
            "posts",
            "posted",
            actor=instance.user,
            target=instance.category,
            action_object=instance,
            timestamp=instance.created_on,
            visible_users=visible_users,
            visible_groups=visible_groups,
            verb=u"{target}에 글 {action_object}를 "
            u"썼습니다.")

def pre_delete_handler(sender, **kwargs):
    instance = kwargs["instance"]
    profile = instance.user.get_profile()
    profile.posts -= 1
    profile.save()
    depublish("forum-post-%d" % instance.id)
    depublish_where(type="commented", target=instance)

pre_delete.connect(pre_delete_handler, sender=Post,
                   dispatch_uid="forum_pre_delete_event")
post_save.connect(post_handler, sender=Post,
                  dispatch_uid="forum_post_event")

########NEW FILE########
__FILENAME__ = processors
# -*- coding: utf-8 -*-

from models import Category
from utils import get_categories_for_user

def add_categories(request):
    return {"forum_categories": get_categories_for_user(request.user, 'read_post')}


########NEW FILE########
__FILENAME__ = search_indexes
import datetime
from haystack import indexes
from models import Post
from utils import get_posts_for_user
from guardian.conf import settings
from django.contrib.auth.models import User

class PostIndex(indexes.SearchIndex, indexes.Indexable):
    text = indexes.EdgeNgramField(document=True, use_template=True)
    user = indexes.CharField(model_attr='user')
    date = indexes.DateTimeField(model_attr='created_on')
    anonymous = User.objects.get(pk=settings.ANONYMOUS_USER_ID)

    def get_model(self):
        return Post

    def index_queryset(self, using=None):
        return get_posts_for_user(self.anonymous, 'forum.read_post').filter(created_on__lte=datetime.datetime.now())

    def get_updated_field(self):
        return 'modified_on'

########NEW FILE########
__FILENAME__ = tests
"""
This file demonstrates writing tests using the unittest module. These will pass
when you run "manage.py test".

Replace this with more appropriate tests for your application.
"""

from django.test import TestCase


class SimpleTest(TestCase):
    def test_basic_addition(self):
        """
        Tests that 1 + 1 always equals 2.
        """
        self.assertEqual(1 + 1, 2)

########NEW FILE########
__FILENAME__ = urls
# -*- coding: utf-8 -*-
from django.conf.urls.defaults import patterns, url
import views

urlpatterns = patterns(
    'forum.views',
    url(r'^list/(?P<slug>[^/]+)/(?P<page>[^/]+)/$', views.list,
        name='forum-list'),
    url(r'^all/(?P<page>[^/]+)/$', views.all, name='forum-all'),
    url(r'^read/(?P<id>[0-9]+)/$', views.read, name="forum-read"),
    url(r'^edit/(?P<id>[0-9]+)/$', views.write, name="forum-edit",
        kwargs={"slug": None}),
    url(r'^write/$', views.write, name="forum-write", kwargs={"id": None}),
    url(r'^write/(?P<slug>.*)/$', views.write, name="forum-write", kwargs={"id": None}),
    url(r'^delete/(?P<id>[0-9]+)/$', views.delete, name="forum-delete"),
    url(r'^by_user/(?P<id>[0-9]+)/$', views.by_user, name="forum-byuser"),
    url(r'^by_user/(?P<id>[0-9]+)/(?P<page>[0-9]+)/$', views.by_user, name="forum-byuser"),
)


########NEW FILE########
__FILENAME__ = utils
# -*- coding: utf-8 -*-
from models import Category, Post
from django.contrib.auth.models import User
from guardian.conf import settings
from guardian.shortcuts import get_objects_for_user

def get_categories_for_user(request_user, perm):
    user = (request_user.is_anonymous() and User.objects.get(pk=settings.ANONYMOUS_USER_ID) or request_user)
    categories = get_objects_for_user(user, perm, Category)
    return categories


def get_posts_for_user(request_user, perm):
    posts = Post.objects.filter(category__in=get_categories_for_user(request_user, perm))
    return posts

########NEW FILE########
__FILENAME__ = views
# -*- coding: utf-8 -*-
from django.shortcuts import get_object_or_404, render, redirect
from django.core.urlresolvers import reverse
from django.contrib.auth.decorators import login_required
from django.contrib.contenttypes.models import ContentType
from django.http import HttpResponseForbidden
from djangoutils import setup_paginator
from models import Category, Post
from forms import WriteForm
from utils import get_posts_for_user, get_categories_for_user
from django.contrib.comments.models import Comment
from django.contrib.auth.models import User
from guardian.core import ObjectPermissionChecker

def list(request, slug, page=1):
    checker = ObjectPermissionChecker(request.user)
    category = get_object_or_404(Category, slug=slug)
    if not checker.has_perm('read_post', category):
        return HttpResponseForbidden("Restricted category")
    posts = Post.objects.filter(category=category).order_by("-id")
    return render(request, "list.html",
                  {"write_at": category.slug if checker.has_perm('write_post', category) else None,
                   "title": category.name,
                   "category": category,
                   "pagination": setup_paginator(posts, page, "forum-list",
                                                 {"slug": category.slug})})

def all(request, page=1):
    posts = get_posts_for_user(request.user, 'forum.read_post').order_by("-id")
    write_category = get_object_or_404(Category, slug='free')
    return render(request, "list.html",
                  {"show_category": True,
                   'write_at': write_category.slug,
                   "title": u"모든 글 보기",
                   "pagination": setup_paginator(posts, page, "forum-all", {})})

def by_user(request, id, page=1):
    user = get_object_or_404(User, id=id)
    posts = get_posts_for_user(request.user, 'forum.read_post').filter(user=user).order_by("-id")
    return render(request, "by_user.html",
                  {"filter_user": user,
                   "pagination": setup_paginator(posts, page, "forum-byuser", {"id": user.id})})

def read(request, id):
    post = get_object_or_404(Post, id=id)
    category = post.category
    checker = ObjectPermissionChecker(request.user)
    if not checker.has_perm('read_post', category):
        return HttpResponseForbidden("Restricted post")
    return render(request, "read.html", {"post": post, "category": category})

@login_required
def write(request, slug, id):
    initial_data = {}
    categories = get_categories_for_user(request.user, 'forum.write_post')
    action = u"글 쓰기"
    if slug != None:
        category = get_object_or_404(Category, slug=slug)
        initial_data["category"] = category.id
    if id != None:
        action = u"글 편집하기"
        post = get_object_or_404(Post, id=id)
        if not request.user.is_superuser and request.user != post.user:
            return HttpResponseForbidden("Operation is forbidden.")
        category = post.category
        categories = categories | Category.objects.filter(id=category.id) # nah
        form = WriteForm(categories, data=request.POST or None, instance=post)
    else:
        if not categories.filter(id=category.id).exists():
            return HttpResponseForbidden("Operation is forbidden.")
        form = WriteForm(categories, data=request.POST or None, initial=initial_data)

    if request.method == "POST" and form.is_valid():
        post = form.save(commit=False)
        if id == None: post.user = request.user
        post.save()
        return redirect(reverse("forum-read", kwargs={"id": post.id}))
    return render(request, "write.html", {"form": form, "action": action,
                                          "category": category, "categories": categories})

def delete(request, id):
    post = get_object_or_404(Post, id=id)
    if not request.user.is_superuser and request.user != post.user:
        return HttpResponseForbidden("operation is forbidden.")
    category = post.category
    # Delete on POST
    if request.method == 'POST':
        # delete all comments
        Comment.objects.filter(object_pk=post.id,
                content_type=ContentType.objects.get_for_model(Post)).delete()
        post.delete()
        return redirect(reverse("forum-list",
                                kwargs={"slug": category.slug, "page": 1}))
    return render(request, "delete.html", {"post": post, "category": category})


########NEW FILE########
__FILENAME__ = admin
from django.contrib import admin
from models import Problem
from guardian.admin import GuardedModelAdmin

admin.site.register(Problem, GuardedModelAdmin)

########NEW FILE########
__FILENAME__ = ignore_trailing_space
# -*- coding: utf-8 -*-
DESC = u"줄 끝에 오는 공백 무시"

def judge(data_dir, input_path, output_path, expected_path):
    return ([line.rstrip() for line in open(output_path)] ==
            [line.rstrip() for line in open(expected_path)])


########NEW FILE########
__FILENAME__ = ignore_whitespace
# -*- coding: utf-8 -*-
DESC = u"공백 무시"
def tokenize(text):
    if isinstance(text, list):
        text = " ".join(text)
    return [x.strip() for x in text.split()]

def judge(data_dir, input_path, output_path, expected_path):
    return (tokenize(open(output_path).read()) ==
            tokenize(open(expected_path).read()))

########NEW FILE########
__FILENAME__ = relative_float
# -*- coding: utf-8 -*-
import math
DESC = u"공백 무시: 실수일 경우 1e-8 이하의 오차 허용"

def tokenize(text):
    if isinstance(text, list):
        text = " ".join(text)
    return [x.strip() for x in text.split()]

def cmp_float(output, expected):
    THRESHOLD = 1e-8
    if output == expected: return True
    try:
        out, exp = float(output), float(expected)
    except ValueError:
        return False
    return math.fabs(exp-out) <= THRESHOLD*max(math.fabs(out), 1)

def judge(data_dir, input_path, output_path, expected_path):
    o, e = tokenize(open(output_path).read()), tokenize(open(expected_path).read())
    if len(o) != len(e): return False
    for i in xrange(len(o)):
        if not cmp_float(o[i], e[i]):
            return False
    return True

########NEW FILE########
__FILENAME__ = special_judge
# -*- coding: utf-8 -*-
DESC = u"스페셜 저지: 문제에 첨부된 저지 모듈을 이용한 채점 (도움말 참조)"

import imp

def judge(data_dir, input_path, output_path, expected_path):
    try:
        judge_module_info = imp.find_module('judge', [data_dir])
    except ImportError:
        raise Exception("Can't find judge module from attachment.")
    judge_module = imp.load_module('judge', *judge_module_info)
    assert hasattr(judge_module, 'judge'), 'judge.judge() not present'
    return judge_module.judge(input_path, output_path, expected_path)

########NEW FILE########
__FILENAME__ = strict
# -*- coding: utf-8 -*-
DESC = u"엄격하게 (라인 피드 차이 허용)"
def tokenize(text):
    if isinstance(text, list):
        text = " ".join(text)
    return [x.strip() for x in text.split()]

def judge(data_dir, input_path, output_path, expected_path):
    o = [line.rstrip("\r\n") for line in open(output_path).readlines()]
    e = [line.rstrip("\r\n") for line in open(expected_path).readlines()]
    return o == e

########NEW FILE########
__FILENAME__ = forms
# -*- coding: utf-8 -*-

from django import forms
from models import Problem, Submission, ProblemRevision
from django.contrib.auth.models import User
import languages
import differs
import tagging

class ProblemRevisionEditForm(forms.ModelForm):
    summary = forms.CharField(max_length=100,
                              widget=forms.TextInput(attrs={"class": "large"}),
                              required=False,
                              label="편집 요약")
    class Meta:
        model = ProblemRevision
        exclude = ('revision_for', 'user', 'edit_summary')
    def save(self, problem, user, summary=None, commit=True):
        instance = super(ProblemRevisionEditForm, self).save(commit=False)
        instance.edit_summary = summary or self.cleaned_data["summary"]
        instance.revision_for = problem
        instance.user = user
        if commit:
            instance.save()
            problem.last_revision = instance
            problem.save()
        return instance

class ProblemEditForm(forms.ModelForm):
    tags = tagging.forms.TagField(label=u"문제 분류", required=False)
    user = forms.ModelChoiceField(label=u"작성자", queryset=User.objects.order_by("username"))
    class Meta:
        model = Problem
        exclude = ('submissions_count', 'accepted_count', 'last_revision')
        widgets = {
            "judge_module": forms.Select(choices=[(key, key + ": " + val.DESC)
                                                  for key, val in differs.modules.iteritems()])
        }
    def __init__(self, *args, **kwargs):
        super(ProblemEditForm, self).__init__(*args, **kwargs)

        if "instance" in kwargs:
            instance = kwargs["instance"]
            self.initial["tags"] = ",".join([tag.name for tag in instance.tags])

    def save(self, commit=True):
        instance = super(ProblemEditForm, self).save(commit=False)
        instance.tags = self.cleaned_data["tags"]
        if commit:
            instance.save()
        return instance

class RestrictedProblemEditForm(forms.ModelForm):
    tags = tagging.forms.TagField(label=u"문제 분류", required=False)
    review = forms.BooleanField(label=u'운영진 리뷰 요청', required=False)
    class Meta:
        model = Problem
        exclude = ('submissions_count', 'accepted_count', 'user', 'state', 'last_revision')
        widgets = {
            "judge_module": forms.Select(choices=[(key, key + ": " + val.DESC)
                                                  for key, val in
                                                  differs.modules.iteritems()]),
        }
    def __init__(self, *args, **kwargs):
        super(RestrictedProblemEditForm, self).__init__(*args, **kwargs)
        if "instance" in kwargs:
            instance = kwargs["instance"]
            self.initial["tags"] = ",".join([tag.name for tag in instance.tags])
            self.initial["review"] = instance.state != Problem.DRAFT

    def save(self, commit=True):
        instance = super(RestrictedProblemEditForm, self).save(commit=False)
        instance.tags = self.cleaned_data["tags"]
        instance.state = (Problem.PENDING_REVIEW if self.cleaned_data["review"]
                          else Problem.DRAFT)

        if commit:
            instance.save()
        return instance

class SubmitForm(forms.Form):
    language = forms.ChoiceField([(key, "%s: %s" % (val.LANGUAGE, val.VERSION))
                                  for key, val in languages.modules.items()],
                                 label=u"사용언어")
    source = forms.CharField(widget=forms.Textarea(attrs={"class": "large monospace",
                                                          "rows": "12"}),
                             label=u"소스코드")

    def __init__(self, *args, **kwargs):
        self.public = kwargs.get('public', True)
        if 'public' in kwargs:
            del kwargs['public']

        super(SubmitForm, self).__init__(*args, **kwargs)

    def save(self, user, problem):
        new_submission = Submission(problem=problem,
                                    user=user,
                                    is_public=self.public,
                                    language=self.cleaned_data["language"],
                                    length=len(self.cleaned_data["source"]),
                                    source=self.cleaned_data["source"])
        new_submission.save()

class AdminSubmitForm(SubmitForm):
    is_public = forms.ChoiceField([("True", u"공개"), ("False", u"비공개")],
                                  label=u"공개여부")

    def save(self, user, problem):
        new_submission = Submission(problem=problem,
                                    user=user,
                                    language=self.cleaned_data["language"],
                                    length=len(self.cleaned_data["source"]),
                                    is_public=("True" == self.cleaned_data["is_public"]),
                                    source=self.cleaned_data["source"])
        new_submission.save()

########NEW FILE########
__FILENAME__ = cpp
import subprocess

def system(cmd):
    return subprocess.Popen(cmd, stdout=subprocess.PIPE,
                            stderr=subprocess.PIPE).communicate()

LANGUAGE = "C++"
EXT = "cpp"
VERSION = system(["g++", "--version"])[0].split("\n")[0]
ADDITIONAL_FILES = []

def setup(sandbox, source_code):
    sandbox.write_file(source_code, "submission.cpp")
    compiled = sandbox.run("g++ -O3 submission.cpp -pedantic-errors --std=c++0x", stdout=".stdout",
                           stderr=".stderr", time_limit=10)
    if compiled.split()[0] != "OK":
        return {"status": "error",
                "message": sandbox.read_file(".stderr")}
    #sandbox.run("rm submission.cpp .stdin .stderr")
    return {"status": "ok"}

def run(sandbox, input_file, time_limit, memory_limit):
    result = sandbox.run("./a.out", stdin=input_file, time_limit=time_limit,
                         override_memory_limit=memory_limit,
                         stdout=".stdout", stderr=".stderr")
    toks = result.split()
    if toks[0] != "OK":
        return {"status": "fail", "message": result, "verdict": toks[0] }
    return {"status": "ok", "time": toks[1], "memory": toks[2], "output": ".stdout"}

########NEW FILE########
__FILENAME__ = go
import subprocess

def system(cmd):
    return subprocess.Popen(cmd, stdout=subprocess.PIPE,
                            stderr=subprocess.PIPE).communicate()

LANGUAGE = "Go"
EXT = "go"
VERSION = " ".join(system(["go", "version"])[0].strip().split(" ")[2:])
ADDITIONAL_FILES = []

def setup(sandbox, source_code):
    sandbox.write_file(source_code, "submission.go")
    compiled = sandbox.run("go build -o a.out submission.go", stdout=".stdout",
                           stderr=".stderr", time_limit=10)
    if compiled.split()[0] != "OK":
        return {"status": "error",
                "message": sandbox.read_file(".stderr")}
    return {"status": "ok"}

def run(sandbox, input_file, time_limit, memory_limit):
    result = sandbox.run("./a.out", stdin=input_file, time_limit=time_limit,
                         override_memory_limit=memory_limit,
                         stdout=".stdout", stderr=".stderr")
    toks = result.split()
    if toks[0] != "OK":
        return {"status": "fail", "message": result, "verdict": toks[0] }
    return {"status": "ok", "time": toks[1], "memory": toks[2], "output": ".stdout"}

########NEW FILE########
__FILENAME__ = hs
import subprocess

def system(cmd):
    return subprocess.Popen(cmd, stdout=subprocess.PIPE,
                            stderr=subprocess.PIPE).communicate()

LANGUAGE = "Haskell"
EXT = "hs"
VERSION = system(["ghc", "--version"])[0].split("\n")[0]
ADDITIONAL_FILES = []

def setup(sandbox, source_code):
    sandbox.write_file(source_code, "Main.hs")
    compiled = sandbox.run("ghc --make -O2 Main", stdout=".stdout",
                           stderr=".stderr", time_limit=10)
    if compiled.split()[0] != "OK":
        return {"status": "error",
                "message": sandbox.read_file(".stderr")}
    #sandbox.run("rm submission.cpp .stdin .stderr")
    print('haskell setup')
    return {"status": "ok"}

def run(sandbox, input_file, time_limit, memory_limit):
    result = sandbox.run("./Main", stdin=input_file, time_limit=time_limit,
                         override_memory_limit=memory_limit,
                         stdout=".stdout", stderr=".stderr")
    toks = result.split()
    if toks[0] != "OK":
        return {"status": "fail", "message": result, "verdict": toks[0] }
    print('haskell run')
    return {"status": "ok", "time": toks[1], "memory": toks[2], "output": ".stdout"}

########NEW FILE########
__FILENAME__ = java
import subprocess

def system(cmd):
    return subprocess.Popen(cmd, stdout=subprocess.PIPE,
                            stderr=subprocess.PIPE).communicate()

LANGUAGE = "Java"
EXT = "java"
VERSION = system(["java", "-version"])[1].split()[2].strip('"')
ADDITIONAL_FILES = []

def setup(sandbox, source_code):
    sandbox.write_file(source_code, "Main.java")
    compiled = sandbox.run("javac Main.java", stdout=".stdout",
                           stderr=".stderr", time_limit=10)
    if compiled.split()[0] != "OK":
        return {"status": "error",
                "message": ("MONITOR:\n" + compiled + "\n" +
                            "STDERR:\n" + sandbox.read_file(".stderr") + "\n" +
                            "STDOUT:\n" + sandbox.read_file(".stdout"))}
    return {"status": "ok"}

def run(sandbox, input_file, time_limit, memory_limit):
    result = sandbox.run("java Main", stdin=input_file, time_limit=time_limit,
                         override_memory_limit=memory_limit,
                         stdout=".stdout", stderr=".stderr")
    toks = result.split()
    if toks[0] != "OK":
        return {"status": "fail", "message": result, "verdict": toks[0] }
    return {"status": "ok", "time": toks[1], "memory": toks[2], "output": ".stdout"}

########NEW FILE########
__FILENAME__ = node
import subprocess

def system(cmd):
    return subprocess.Popen(cmd, stdout=subprocess.PIPE,
                            stderr=subprocess.PIPE).communicate()

LANGUAGE = "Javascript (Node)"
EXT = "js"
VERSION = system(["node", "--version"])[0]
ADDITIONAL_FILES = []

def setup(sandbox, source_code):
    sandbox.write_file(source_code, "submission.js")
    return {"status": "ok"}

def run(sandbox, input_file, time_limit, memory_limit):
    result = sandbox.run("node submission.js", stdin=input_file, time_limit=time_limit,
                         override_memory_limit=memory_limit,
                         stdout=".stdout", stderr=".stderr")
    toks = result.split()
    if toks[0] != "OK":
        return {"status": "fail", "message": result, "verdict": toks[0] }
    return {"status": "ok", "time": toks[1], "memory": toks[2], "output": ".stdout"}

########NEW FILE########
__FILENAME__ = py
import subprocess

def system(cmd):
    return subprocess.Popen(cmd, stdout=subprocess.PIPE,
                            stderr=subprocess.PIPE).communicate()

LANGUAGE = "Python 2"
EXT = "py"
VERSION = system(["python", "--version"])[1].split("\n")[0]
ADDITIONAL_FILES = []

def setup(sandbox, source_code):
    sandbox.write_file(source_code, "submission.py")
    return {"status": "ok"}

def run(sandbox, input_file, time_limit, memory_limit):
    result = sandbox.run("python submission.py", stdin=input_file, time_limit=time_limit,
                         override_memory_limit=memory_limit,
                         stdout=".stdout", stderr=".stderr")
    toks = result.split()
    if toks[0] != "OK":
        return {"status": "fail", "message": result, "verdict": toks[0] }
    return {"status": "ok", "time": toks[1], "memory": toks[2], "output": ".stdout"}

########NEW FILE########
__FILENAME__ = rb
import subprocess

def system(cmd):
    return subprocess.Popen(cmd, stdout=subprocess.PIPE,
                            stderr=subprocess.PIPE).communicate()

LANGUAGE = "Ruby"
EXT = "rb"
INTERP = "/usr/local/rvm/bin/ruby-1.9.3-p125@aoj"
VERSION = system([INTERP, "--version"])[0]
ADDITIONAL_FILES = []

def setup(sandbox, source_code):
    sandbox.write_file(source_code, "submission.rb")
    return {"status": "ok"}

def run(sandbox, input_file, time_limit, memory_limit):
    result = sandbox.run(INTERP + " submission.rb", stdin=input_file, time_limit=time_limit,
                         override_memory_limit=memory_limit,
                         stdout=".stdout", stderr=".stderr")
    toks = result.split()
    if toks[0] != "OK":
        return {"status": "fail", "message": result, "verdict": toks[0] }
    return {"status": "ok", "time": toks[1], "memory": toks[2], "output": ".stdout"}

########NEW FILE########
__FILENAME__ = scala
import subprocess

def system(cmd):
    return subprocess.Popen(cmd, stdout=subprocess.PIPE,
                            stderr=subprocess.PIPE).communicate()

LANGUAGE = "Scala"
EXT = "scala"
VERSION = system(["scala", "-version"])[0].split("\n")[0]
ADDITIONAL_FILES = []

def setup(sandbox, source_code):
    sandbox.write_file(source_code, "Main.scala")
    compiled = sandbox.run("scalac -optimise Main.scala", stdout=".stdout",
                           stderr=".stderr", time_limit=10)
    if compiled.split()[0] != "OK":
        return {"status": "error",
                "message": ("MONITOR:\n" + compiled + "\n" +
                            "STDERR:\n" + sandbox.read_file(".stderr") + "\n" +
                            "STDOUT:\n" + sandbox.read_file(".stdout"))}
    return {"status": "ok"}

def run(sandbox, input_file, time_limit, memory_limit):
    result = sandbox.run("scala Main", stdin=input_file, time_limit=time_limit,
                         override_memory_limit=memory_limit,
                         stdout=".stdout", stderr=".stderr")
    toks = result.split()
    if toks[0] != "OK":
        return {"status": "fail", "message": result, "verdict": toks[0] }
    return {"status": "ok", "time": toks[1], "memory": toks[2], "output": ".stdout"}

########NEW FILE########
__FILENAME__ = problems_set_permission
from django.core.management.base import NoArgsCommand
from django.contrib.auth.models import User, Group
from judge.models import Problem
from guardian.conf import settings
from guardian.shortcuts import assign_perm

class Command(NoArgsCommand):
    def handle(self, **options):
        for x in Problem.objects.all():
            assign_perm('judge.edit_problem', x.user, x)

########NEW FILE########
__FILENAME__ = 0001_initial
# encoding: utf-8
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models

class Migration(SchemaMigration):

    def forwards(self, orm):
        
        # Adding model 'Problem'
        db.create_table('judge_problem', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('slug', self.gf('django.db.models.fields.SlugField')(db_index=True, max_length=100, blank=True)),
            ('updated_on', self.gf('django.db.models.fields.DateTimeField')(auto_now=True, blank=True)),
            ('state', self.gf('django.db.models.fields.SmallIntegerField')(default=0)),
            ('user', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['auth.User'])),
            ('source', self.gf('django.db.models.fields.TextField')(max_length=100, blank=True)),
            ('name', self.gf('django.db.models.fields.TextField')(max_length=100, blank=True)),
            ('description', self.gf('django.db.models.fields.TextField')(blank=True)),
            ('input', self.gf('django.db.models.fields.TextField')(blank=True)),
            ('output', self.gf('django.db.models.fields.TextField')(blank=True)),
            ('sample_input', self.gf('django.db.models.fields.TextField')(blank=True)),
            ('sample_output', self.gf('django.db.models.fields.TextField')(blank=True)),
            ('note', self.gf('django.db.models.fields.TextField')(blank=True)),
            ('judge_module', self.gf('django.db.models.fields.TextField')(max_length=100, blank=True)),
            ('time_limit', self.gf('django.db.models.fields.PositiveIntegerField')(default=10000)),
            ('memory_limit', self.gf('django.db.models.fields.PositiveIntegerField')(default=65536)),
            ('submissions_count', self.gf('django.db.models.fields.IntegerField')(default=0)),
            ('accepted_count', self.gf('django.db.models.fields.IntegerField')(default=0)),
        ))
        db.send_create_signal('judge', ['Problem'])

        # Adding model 'Submission'
        db.create_table('judge_submission', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('submitted_on', self.gf('django.db.models.fields.DateTimeField')(auto_now_add=True, blank=True)),
            ('problem', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['judge.Problem'])),
            ('is_public', self.gf('django.db.models.fields.BooleanField')(default=True)),
            ('user', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['auth.User'])),
            ('language', self.gf('django.db.models.fields.TextField')(max_length=100)),
            ('state', self.gf('django.db.models.fields.SmallIntegerField')(default=0)),
            ('length', self.gf('django.db.models.fields.IntegerField')()),
            ('source', self.gf('django.db.models.fields.TextField')()),
            ('message', self.gf('django.db.models.fields.TextField')(default='', blank=True)),
            ('time', self.gf('django.db.models.fields.IntegerField')(null=True)),
            ('memory', self.gf('django.db.models.fields.IntegerField')(null=True)),
        ))
        db.send_create_signal('judge', ['Submission'])


    def backwards(self, orm):
        
        # Deleting model 'Problem'
        db.delete_table('judge_problem')

        # Deleting model 'Submission'
        db.delete_table('judge_submission')


    models = {
        'auth.group': {
            'Meta': {'object_name': 'Group'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '80'}),
            'permissions': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['auth.Permission']", 'symmetrical': 'False', 'blank': 'True'})
        },
        'auth.permission': {
            'Meta': {'ordering': "('content_type__app_label', 'content_type__model', 'codename')", 'unique_together': "(('content_type', 'codename'),)", 'object_name': 'Permission'},
            'codename': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'content_type': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['contenttypes.ContentType']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '50'})
        },
        'auth.user': {
            'Meta': {'object_name': 'User'},
            'date_joined': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'email': ('django.db.models.fields.EmailField', [], {'max_length': '75', 'blank': 'True'}),
            'first_name': ('django.db.models.fields.CharField', [], {'max_length': '30', 'blank': 'True'}),
            'groups': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['auth.Group']", 'symmetrical': 'False', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'is_active': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'is_staff': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'is_superuser': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'last_login': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'last_name': ('django.db.models.fields.CharField', [], {'max_length': '30', 'blank': 'True'}),
            'password': ('django.db.models.fields.CharField', [], {'max_length': '128'}),
            'user_permissions': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['auth.Permission']", 'symmetrical': 'False', 'blank': 'True'}),
            'username': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '30'})
        },
        'contenttypes.contenttype': {
            'Meta': {'ordering': "('name',)", 'unique_together': "(('app_label', 'model'),)", 'object_name': 'ContentType', 'db_table': "'django_content_type'"},
            'app_label': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'model': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '100'})
        },
        'judge.problem': {
            'Meta': {'object_name': 'Problem'},
            'accepted_count': ('django.db.models.fields.IntegerField', [], {'default': '0'}),
            'description': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'input': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'judge_module': ('django.db.models.fields.TextField', [], {'max_length': '100', 'blank': 'True'}),
            'memory_limit': ('django.db.models.fields.PositiveIntegerField', [], {'default': '65536'}),
            'name': ('django.db.models.fields.TextField', [], {'max_length': '100', 'blank': 'True'}),
            'note': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'output': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'sample_input': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'sample_output': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'slug': ('django.db.models.fields.SlugField', [], {'db_index': 'True', 'max_length': '100', 'blank': 'True'}),
            'source': ('django.db.models.fields.TextField', [], {'max_length': '100', 'blank': 'True'}),
            'state': ('django.db.models.fields.SmallIntegerField', [], {'default': '0'}),
            'submissions_count': ('django.db.models.fields.IntegerField', [], {'default': '0'}),
            'time_limit': ('django.db.models.fields.PositiveIntegerField', [], {'default': '10000'}),
            'updated_on': ('django.db.models.fields.DateTimeField', [], {'auto_now': 'True', 'blank': 'True'}),
            'user': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['auth.User']"})
        },
        'judge.submission': {
            'Meta': {'object_name': 'Submission'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'is_public': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'language': ('django.db.models.fields.TextField', [], {'max_length': '100'}),
            'length': ('django.db.models.fields.IntegerField', [], {}),
            'memory': ('django.db.models.fields.IntegerField', [], {'null': 'True'}),
            'message': ('django.db.models.fields.TextField', [], {'default': "''", 'blank': 'True'}),
            'problem': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['judge.Problem']"}),
            'source': ('django.db.models.fields.TextField', [], {}),
            'state': ('django.db.models.fields.SmallIntegerField', [], {'default': '0'}),
            'submitted_on': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'time': ('django.db.models.fields.IntegerField', [], {'null': 'True'}),
            'user': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['auth.User']"})
        }
    }

    complete_apps = ['judge']

########NEW FILE########
__FILENAME__ = 0002_auto__add_attachment
# encoding: utf-8
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models

class Migration(SchemaMigration):

    def forwards(self, orm):

        # Adding model 'Attachment'
        db.create_table('judge_attachment', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('problem', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['judge.Problem'])),
            ('name', self.gf('django.db.models.fields.CharField')(max_length=128)),
            ('path', self.gf('django.db.models.fields.CharField')(max_length=256)),
            ('size', self.gf('django.db.models.fields.IntegerField')()),
            ('md5', self.gf('django.db.models.fields.CharField')(max_length=32)),
        ))
        db.send_create_signal('judge', ['Attachment'])


    def backwards(self, orm):

        # Deleting model 'Attachment'
        db.delete_table('judge_attachment')


    models = {
        'auth.group': {
            'Meta': {'object_name': 'Group'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '80'}),
            'permissions': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['auth.Permission']", 'symmetrical': 'False', 'blank': 'True'})
        },
        'auth.permission': {
            'Meta': {'ordering': "('content_type__app_label', 'content_type__model', 'codename')", 'unique_together': "(('content_type', 'codename'),)", 'object_name': 'Permission'},
            'codename': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'content_type': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['contenttypes.ContentType']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '50'})
        },
        'auth.user': {
            'Meta': {'object_name': 'User'},
            'date_joined': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'email': ('django.db.models.fields.EmailField', [], {'max_length': '75', 'blank': 'True'}),
            'first_name': ('django.db.models.fields.CharField', [], {'max_length': '30', 'blank': 'True'}),
            'groups': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['auth.Group']", 'symmetrical': 'False', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'is_active': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'is_staff': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'is_superuser': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'last_login': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'last_name': ('django.db.models.fields.CharField', [], {'max_length': '30', 'blank': 'True'}),
            'password': ('django.db.models.fields.CharField', [], {'max_length': '128'}),
            'user_permissions': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['auth.Permission']", 'symmetrical': 'False', 'blank': 'True'}),
            'username': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '30'})
        },
        'contenttypes.contenttype': {
            'Meta': {'ordering': "('name',)", 'unique_together': "(('app_label', 'model'),)", 'object_name': 'ContentType', 'db_table': "'django_content_type'"},
            'app_label': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'model': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '100'})
        },
        'judge.attachment': {
            'Meta': {'object_name': 'Attachment'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'md5': ('django.db.models.fields.CharField', [], {'max_length': '32'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '128'}),
            'path': ('django.db.models.fields.CharField', [], {'max_length': '256'}),
            'problem': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['judge.Problem']"}),
            'size': ('django.db.models.fields.IntegerField', [], {})
        },
        'judge.problem': {
            'Meta': {'object_name': 'Problem'},
            'accepted_count': ('django.db.models.fields.IntegerField', [], {'default': '0'}),
            'description': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'input': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'judge_module': ('django.db.models.fields.TextField', [], {'max_length': '100', 'blank': 'True'}),
            'memory_limit': ('django.db.models.fields.PositiveIntegerField', [], {'default': '65536'}),
            'name': ('django.db.models.fields.TextField', [], {'max_length': '100', 'blank': 'True'}),
            'note': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'output': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'sample_input': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'sample_output': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'slug': ('django.db.models.fields.SlugField', [], {'db_index': 'True', 'max_length': '100', 'blank': 'True'}),
            'source': ('django.db.models.fields.TextField', [], {'max_length': '100', 'blank': 'True'}),
            'state': ('django.db.models.fields.SmallIntegerField', [], {'default': '0'}),
            'submissions_count': ('django.db.models.fields.IntegerField', [], {'default': '0'}),
            'time_limit': ('django.db.models.fields.PositiveIntegerField', [], {'default': '10000'}),
            'updated_on': ('django.db.models.fields.DateTimeField', [], {'auto_now': 'True', 'blank': 'True'}),
            'user': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['auth.User']"})
        },
        'judge.submission': {
            'Meta': {'object_name': 'Submission'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'is_public': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'language': ('django.db.models.fields.TextField', [], {'max_length': '100'}),
            'length': ('django.db.models.fields.IntegerField', [], {}),
            'memory': ('django.db.models.fields.IntegerField', [], {'null': 'True'}),
            'message': ('django.db.models.fields.TextField', [], {'default': "''", 'blank': 'True'}),
            'problem': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['judge.Problem']"}),
            'source': ('django.db.models.fields.TextField', [], {}),
            'state': ('django.db.models.fields.SmallIntegerField', [], {'default': '0'}),
            'submitted_on': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'time': ('django.db.models.fields.IntegerField', [], {'null': 'True'}),
            'user': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['auth.User']"})
        }
    }

    complete_apps = ['judge']

########NEW FILE########
__FILENAME__ = 0003_auto__del_field_attachment_name__del_field_attachment_path__del_field_
# encoding: utf-8
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models

class Migration(SchemaMigration):

    def forwards(self, orm):
        
        # Deleting field 'Attachment.name'
        db.delete_column('judge_attachment', 'name')

        # Deleting field 'Attachment.path'
        db.delete_column('judge_attachment', 'path')

        # Deleting field 'Attachment.size'
        db.delete_column('judge_attachment', 'size')

        # Deleting field 'Attachment.md5'
        db.delete_column('judge_attachment', 'md5')

        # Adding field 'Attachment.file'
        db.add_column('judge_attachment', 'file', self.gf('django.db.models.fields.files.FileField')(default='argh', max_length=1024), keep_default=False)


    def backwards(self, orm):
        
        # Adding field 'Attachment.name'
        db.add_column('judge_attachment', 'name', self.gf('django.db.models.fields.CharField')(default='meh', max_length=128), keep_default=False)

        # Adding field 'Attachment.path'
        db.add_column('judge_attachment', 'path', self.gf('django.db.models.fields.CharField')(default='bah', max_length=256), keep_default=False)

        # Adding field 'Attachment.size'
        db.add_column('judge_attachment', 'size', self.gf('django.db.models.fields.IntegerField')(default='dah'), keep_default=False)

        # Adding field 'Attachment.md5'
        db.add_column('judge_attachment', 'md5', self.gf('django.db.models.fields.CharField')(default='gah', max_length=32), keep_default=False)

        # Deleting field 'Attachment.file'
        db.delete_column('judge_attachment', 'file')


    models = {
        'auth.group': {
            'Meta': {'object_name': 'Group'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '80'}),
            'permissions': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['auth.Permission']", 'symmetrical': 'False', 'blank': 'True'})
        },
        'auth.permission': {
            'Meta': {'ordering': "('content_type__app_label', 'content_type__model', 'codename')", 'unique_together': "(('content_type', 'codename'),)", 'object_name': 'Permission'},
            'codename': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'content_type': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['contenttypes.ContentType']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '50'})
        },
        'auth.user': {
            'Meta': {'object_name': 'User'},
            'date_joined': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'email': ('django.db.models.fields.EmailField', [], {'max_length': '75', 'blank': 'True'}),
            'first_name': ('django.db.models.fields.CharField', [], {'max_length': '30', 'blank': 'True'}),
            'groups': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['auth.Group']", 'symmetrical': 'False', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'is_active': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'is_staff': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'is_superuser': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'last_login': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'last_name': ('django.db.models.fields.CharField', [], {'max_length': '30', 'blank': 'True'}),
            'password': ('django.db.models.fields.CharField', [], {'max_length': '128'}),
            'user_permissions': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['auth.Permission']", 'symmetrical': 'False', 'blank': 'True'}),
            'username': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '30'})
        },
        'contenttypes.contenttype': {
            'Meta': {'ordering': "('name',)", 'unique_together': "(('app_label', 'model'),)", 'object_name': 'ContentType', 'db_table': "'django_content_type'"},
            'app_label': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'model': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '100'})
        },
        'judge.attachment': {
            'Meta': {'object_name': 'Attachment'},
            'file': ('django.db.models.fields.files.FileField', [], {'max_length': '1024'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'problem': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['judge.Problem']"})
        },
        'judge.problem': {
            'Meta': {'object_name': 'Problem'},
            'accepted_count': ('django.db.models.fields.IntegerField', [], {'default': '0'}),
            'description': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'input': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'judge_module': ('django.db.models.fields.TextField', [], {'max_length': '100', 'blank': 'True'}),
            'memory_limit': ('django.db.models.fields.PositiveIntegerField', [], {'default': '65536'}),
            'name': ('django.db.models.fields.TextField', [], {'max_length': '100', 'blank': 'True'}),
            'note': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'output': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'sample_input': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'sample_output': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'slug': ('django.db.models.fields.SlugField', [], {'db_index': 'True', 'max_length': '100', 'blank': 'True'}),
            'source': ('django.db.models.fields.TextField', [], {'max_length': '100', 'blank': 'True'}),
            'state': ('django.db.models.fields.SmallIntegerField', [], {'default': '0'}),
            'submissions_count': ('django.db.models.fields.IntegerField', [], {'default': '0'}),
            'time_limit': ('django.db.models.fields.PositiveIntegerField', [], {'default': '10000'}),
            'updated_on': ('django.db.models.fields.DateTimeField', [], {'auto_now': 'True', 'blank': 'True'}),
            'user': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['auth.User']"})
        },
        'judge.submission': {
            'Meta': {'object_name': 'Submission'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'is_public': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'language': ('django.db.models.fields.TextField', [], {'max_length': '100'}),
            'length': ('django.db.models.fields.IntegerField', [], {}),
            'memory': ('django.db.models.fields.IntegerField', [], {'null': 'True'}),
            'message': ('django.db.models.fields.TextField', [], {'default': "''", 'blank': 'True'}),
            'problem': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['judge.Problem']"}),
            'source': ('django.db.models.fields.TextField', [], {}),
            'state': ('django.db.models.fields.SmallIntegerField', [], {'default': '0'}),
            'submitted_on': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'time': ('django.db.models.fields.IntegerField', [], {'null': 'True'}),
            'user': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['auth.User']"})
        }
    }

    complete_apps = ['judge']

########NEW FILE########
__FILENAME__ = 0004_auto__chg_field_problem_name__chg_field_problem_judge_module__chg_fiel
# encoding: utf-8
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models

class Migration(SchemaMigration):

    def forwards(self, orm):
        
        # Changing field 'Problem.name'
        db.alter_column('judge_problem', 'name', self.gf('django.db.models.fields.CharField')(max_length=100))

        # Changing field 'Problem.judge_module'
        db.alter_column('judge_problem', 'judge_module', self.gf('django.db.models.fields.CharField')(max_length=100))

        # Changing field 'Problem.source'
        db.alter_column('judge_problem', 'source', self.gf('django.db.models.fields.CharField')(max_length=100))


    def backwards(self, orm):
        
        # Changing field 'Problem.name'
        db.alter_column('judge_problem', 'name', self.gf('django.db.models.fields.TextField')(max_length=100))

        # Changing field 'Problem.judge_module'
        db.alter_column('judge_problem', 'judge_module', self.gf('django.db.models.fields.TextField')(max_length=100))

        # Changing field 'Problem.source'
        db.alter_column('judge_problem', 'source', self.gf('django.db.models.fields.TextField')(max_length=100))


    models = {
        'auth.group': {
            'Meta': {'object_name': 'Group'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '80'}),
            'permissions': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['auth.Permission']", 'symmetrical': 'False', 'blank': 'True'})
        },
        'auth.permission': {
            'Meta': {'ordering': "('content_type__app_label', 'content_type__model', 'codename')", 'unique_together': "(('content_type', 'codename'),)", 'object_name': 'Permission'},
            'codename': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'content_type': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['contenttypes.ContentType']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '50'})
        },
        'auth.user': {
            'Meta': {'object_name': 'User'},
            'date_joined': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'email': ('django.db.models.fields.EmailField', [], {'max_length': '75', 'blank': 'True'}),
            'first_name': ('django.db.models.fields.CharField', [], {'max_length': '30', 'blank': 'True'}),
            'groups': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['auth.Group']", 'symmetrical': 'False', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'is_active': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'is_staff': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'is_superuser': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'last_login': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'last_name': ('django.db.models.fields.CharField', [], {'max_length': '30', 'blank': 'True'}),
            'password': ('django.db.models.fields.CharField', [], {'max_length': '128'}),
            'user_permissions': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['auth.Permission']", 'symmetrical': 'False', 'blank': 'True'}),
            'username': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '30'})
        },
        'contenttypes.contenttype': {
            'Meta': {'ordering': "('name',)", 'unique_together': "(('app_label', 'model'),)", 'object_name': 'ContentType', 'db_table': "'django_content_type'"},
            'app_label': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'model': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '100'})
        },
        'judge.attachment': {
            'Meta': {'object_name': 'Attachment'},
            'file': ('django.db.models.fields.files.FileField', [], {'max_length': '1024'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'problem': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['judge.Problem']"})
        },
        'judge.problem': {
            'Meta': {'object_name': 'Problem'},
            'accepted_count': ('django.db.models.fields.IntegerField', [], {'default': '0'}),
            'description': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'input': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'judge_module': ('django.db.models.fields.CharField', [], {'max_length': '100', 'blank': 'True'}),
            'memory_limit': ('django.db.models.fields.PositiveIntegerField', [], {'default': '65536'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '100', 'blank': 'True'}),
            'note': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'output': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'sample_input': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'sample_output': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'slug': ('django.db.models.fields.SlugField', [], {'db_index': 'True', 'max_length': '100', 'blank': 'True'}),
            'source': ('django.db.models.fields.CharField', [], {'max_length': '100', 'blank': 'True'}),
            'state': ('django.db.models.fields.SmallIntegerField', [], {'default': '0'}),
            'submissions_count': ('django.db.models.fields.IntegerField', [], {'default': '0'}),
            'time_limit': ('django.db.models.fields.PositiveIntegerField', [], {'default': '10000'}),
            'updated_on': ('django.db.models.fields.DateTimeField', [], {'auto_now': 'True', 'blank': 'True'}),
            'user': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['auth.User']"})
        },
        'judge.submission': {
            'Meta': {'object_name': 'Submission'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'is_public': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'language': ('django.db.models.fields.TextField', [], {'max_length': '100'}),
            'length': ('django.db.models.fields.IntegerField', [], {}),
            'memory': ('django.db.models.fields.IntegerField', [], {'null': 'True'}),
            'message': ('django.db.models.fields.TextField', [], {'default': "''", 'blank': 'True'}),
            'problem': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['judge.Problem']"}),
            'source': ('django.db.models.fields.TextField', [], {}),
            'state': ('django.db.models.fields.SmallIntegerField', [], {'default': '0'}),
            'submitted_on': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'time': ('django.db.models.fields.IntegerField', [], {'null': 'True'}),
            'user': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['auth.User']"})
        }
    }

    complete_apps = ['judge']

########NEW FILE########
__FILENAME__ = 0005_auto__add_field_problem_tags
# encoding: utf-8
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models

class Migration(SchemaMigration):

    def forwards(self, orm):
        
        # Adding field 'Problem.tags'
        db.add_column('judge_problem', 'tags', self.gf('tagging.fields.TagField')(default=''), keep_default=False)


    def backwards(self, orm):
        
        # Deleting field 'Problem.tags'
        db.delete_column('judge_problem', 'tags')


    models = {
        'auth.group': {
            'Meta': {'object_name': 'Group'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '80'}),
            'permissions': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['auth.Permission']", 'symmetrical': 'False', 'blank': 'True'})
        },
        'auth.permission': {
            'Meta': {'ordering': "('content_type__app_label', 'content_type__model', 'codename')", 'unique_together': "(('content_type', 'codename'),)", 'object_name': 'Permission'},
            'codename': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'content_type': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['contenttypes.ContentType']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '50'})
        },
        'auth.user': {
            'Meta': {'object_name': 'User'},
            'date_joined': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'email': ('django.db.models.fields.EmailField', [], {'max_length': '75', 'blank': 'True'}),
            'first_name': ('django.db.models.fields.CharField', [], {'max_length': '30', 'blank': 'True'}),
            'groups': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['auth.Group']", 'symmetrical': 'False', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'is_active': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'is_staff': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'is_superuser': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'last_login': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'last_name': ('django.db.models.fields.CharField', [], {'max_length': '30', 'blank': 'True'}),
            'password': ('django.db.models.fields.CharField', [], {'max_length': '128'}),
            'user_permissions': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['auth.Permission']", 'symmetrical': 'False', 'blank': 'True'}),
            'username': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '30'})
        },
        'contenttypes.contenttype': {
            'Meta': {'ordering': "('name',)", 'unique_together': "(('app_label', 'model'),)", 'object_name': 'ContentType', 'db_table': "'django_content_type'"},
            'app_label': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'model': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '100'})
        },
        'judge.attachment': {
            'Meta': {'object_name': 'Attachment'},
            'file': ('django.db.models.fields.files.FileField', [], {'max_length': '1024'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'problem': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['judge.Problem']"})
        },
        'judge.problem': {
            'Meta': {'object_name': 'Problem'},
            'accepted_count': ('django.db.models.fields.IntegerField', [], {'default': '0'}),
            'description': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'input': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'judge_module': ('django.db.models.fields.CharField', [], {'max_length': '100', 'blank': 'True'}),
            'memory_limit': ('django.db.models.fields.PositiveIntegerField', [], {'default': '65536'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '100', 'blank': 'True'}),
            'note': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'output': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'sample_input': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'sample_output': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'slug': ('django.db.models.fields.SlugField', [], {'db_index': 'True', 'max_length': '100', 'blank': 'True'}),
            'source': ('django.db.models.fields.CharField', [], {'max_length': '100', 'blank': 'True'}),
            'state': ('django.db.models.fields.SmallIntegerField', [], {'default': '0'}),
            'submissions_count': ('django.db.models.fields.IntegerField', [], {'default': '0'}),
            'tags': ('tagging.fields.TagField', [], {}),
            'time_limit': ('django.db.models.fields.PositiveIntegerField', [], {'default': '10000'}),
            'updated_on': ('django.db.models.fields.DateTimeField', [], {'auto_now': 'True', 'blank': 'True'}),
            'user': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['auth.User']"})
        },
        'judge.submission': {
            'Meta': {'object_name': 'Submission'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'is_public': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'language': ('django.db.models.fields.TextField', [], {'max_length': '100'}),
            'length': ('django.db.models.fields.IntegerField', [], {}),
            'memory': ('django.db.models.fields.IntegerField', [], {'null': 'True'}),
            'message': ('django.db.models.fields.TextField', [], {'default': "''", 'blank': 'True'}),
            'problem': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['judge.Problem']"}),
            'source': ('django.db.models.fields.TextField', [], {}),
            'state': ('django.db.models.fields.SmallIntegerField', [], {'default': '0'}),
            'submitted_on': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'time': ('django.db.models.fields.IntegerField', [], {'null': 'True'}),
            'user': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['auth.User']"})
        }
    }

    complete_apps = ['judge']

########NEW FILE########
__FILENAME__ = 0006_auto__add_solver__del_field_problem_tags
# encoding: utf-8
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models

class Migration(SchemaMigration):

    def forwards(self, orm):
        
        # Adding model 'Solver'
        db.create_table('judge_solver', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('problem', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['judge.Problem'])),
            ('user', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['auth.User'])),
            ('incorrect_tries', self.gf('django.db.models.fields.IntegerField')(default=0)),
            ('fastest_submission', self.gf('django.db.models.fields.related.ForeignKey')(related_name='+', null=True, to=orm['judge.Submission'])),
            ('shortest_submission', self.gf('django.db.models.fields.related.ForeignKey')(related_name='+', null=True, to=orm['judge.Submission'])),
        ))
        db.send_create_signal('judge', ['Solver'])

        # Deleting field 'Problem.tags'
        db.delete_column('judge_problem', 'tags')


    def backwards(self, orm):
        
        # Deleting model 'Solver'
        db.delete_table('judge_solver')

        # Adding field 'Problem.tags'
        db.add_column('judge_problem', 'tags', self.gf('tagging.fields.TagField')(default=''), keep_default=False)


    models = {
        'auth.group': {
            'Meta': {'object_name': 'Group'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '80'}),
            'permissions': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['auth.Permission']", 'symmetrical': 'False', 'blank': 'True'})
        },
        'auth.permission': {
            'Meta': {'ordering': "('content_type__app_label', 'content_type__model', 'codename')", 'unique_together': "(('content_type', 'codename'),)", 'object_name': 'Permission'},
            'codename': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'content_type': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['contenttypes.ContentType']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '50'})
        },
        'auth.user': {
            'Meta': {'object_name': 'User'},
            'date_joined': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'email': ('django.db.models.fields.EmailField', [], {'max_length': '75', 'blank': 'True'}),
            'first_name': ('django.db.models.fields.CharField', [], {'max_length': '30', 'blank': 'True'}),
            'groups': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['auth.Group']", 'symmetrical': 'False', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'is_active': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'is_staff': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'is_superuser': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'last_login': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'last_name': ('django.db.models.fields.CharField', [], {'max_length': '30', 'blank': 'True'}),
            'password': ('django.db.models.fields.CharField', [], {'max_length': '128'}),
            'user_permissions': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['auth.Permission']", 'symmetrical': 'False', 'blank': 'True'}),
            'username': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '30'})
        },
        'contenttypes.contenttype': {
            'Meta': {'ordering': "('name',)", 'unique_together': "(('app_label', 'model'),)", 'object_name': 'ContentType', 'db_table': "'django_content_type'"},
            'app_label': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'model': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '100'})
        },
        'judge.attachment': {
            'Meta': {'object_name': 'Attachment'},
            'file': ('django.db.models.fields.files.FileField', [], {'max_length': '1024'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'problem': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['judge.Problem']"})
        },
        'judge.problem': {
            'Meta': {'object_name': 'Problem'},
            'accepted_count': ('django.db.models.fields.IntegerField', [], {'default': '0'}),
            'description': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'input': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'judge_module': ('django.db.models.fields.CharField', [], {'max_length': '100', 'blank': 'True'}),
            'memory_limit': ('django.db.models.fields.PositiveIntegerField', [], {'default': '65536'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '100', 'blank': 'True'}),
            'note': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'output': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'sample_input': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'sample_output': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'slug': ('django.db.models.fields.SlugField', [], {'db_index': 'True', 'max_length': '100', 'blank': 'True'}),
            'source': ('django.db.models.fields.CharField', [], {'max_length': '100', 'blank': 'True'}),
            'state': ('django.db.models.fields.SmallIntegerField', [], {'default': '0'}),
            'submissions_count': ('django.db.models.fields.IntegerField', [], {'default': '0'}),
            'time_limit': ('django.db.models.fields.PositiveIntegerField', [], {'default': '10000'}),
            'updated_on': ('django.db.models.fields.DateTimeField', [], {'auto_now': 'True', 'blank': 'True'}),
            'user': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['auth.User']"})
        },
        'judge.solver': {
            'Meta': {'object_name': 'Solver'},
            'fastest_submission': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'+'", 'null': 'True', 'to': "orm['judge.Submission']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'incorrect_tries': ('django.db.models.fields.IntegerField', [], {'default': '0'}),
            'problem': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['judge.Problem']"}),
            'shortest_submission': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'+'", 'null': 'True', 'to': "orm['judge.Submission']"}),
            'user': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['auth.User']"})
        },
        'judge.submission': {
            'Meta': {'object_name': 'Submission'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'is_public': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'language': ('django.db.models.fields.TextField', [], {'max_length': '100'}),
            'length': ('django.db.models.fields.IntegerField', [], {}),
            'memory': ('django.db.models.fields.IntegerField', [], {'null': 'True'}),
            'message': ('django.db.models.fields.TextField', [], {'default': "''", 'blank': 'True'}),
            'problem': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['judge.Problem']"}),
            'source': ('django.db.models.fields.TextField', [], {}),
            'state': ('django.db.models.fields.SmallIntegerField', [], {'default': '0'}),
            'submitted_on': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'time': ('django.db.models.fields.IntegerField', [], {'null': 'True'}),
            'user': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['auth.User']"})
        }
    }

    complete_apps = ['judge']

########NEW FILE########
__FILENAME__ = 0007_auto__add_field_solver_solved
# encoding: utf-8
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models

class Migration(SchemaMigration):

    def forwards(self, orm):
        
        # Adding field 'Solver.solved'
        db.add_column('judge_solver', 'solved', self.gf('django.db.models.fields.BooleanField')(default=False), keep_default=False)


    def backwards(self, orm):
        
        # Deleting field 'Solver.solved'
        db.delete_column('judge_solver', 'solved')


    models = {
        'auth.group': {
            'Meta': {'object_name': 'Group'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '80'}),
            'permissions': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['auth.Permission']", 'symmetrical': 'False', 'blank': 'True'})
        },
        'auth.permission': {
            'Meta': {'ordering': "('content_type__app_label', 'content_type__model', 'codename')", 'unique_together': "(('content_type', 'codename'),)", 'object_name': 'Permission'},
            'codename': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'content_type': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['contenttypes.ContentType']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '50'})
        },
        'auth.user': {
            'Meta': {'object_name': 'User'},
            'date_joined': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'email': ('django.db.models.fields.EmailField', [], {'max_length': '75', 'blank': 'True'}),
            'first_name': ('django.db.models.fields.CharField', [], {'max_length': '30', 'blank': 'True'}),
            'groups': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['auth.Group']", 'symmetrical': 'False', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'is_active': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'is_staff': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'is_superuser': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'last_login': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'last_name': ('django.db.models.fields.CharField', [], {'max_length': '30', 'blank': 'True'}),
            'password': ('django.db.models.fields.CharField', [], {'max_length': '128'}),
            'user_permissions': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['auth.Permission']", 'symmetrical': 'False', 'blank': 'True'}),
            'username': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '30'})
        },
        'contenttypes.contenttype': {
            'Meta': {'ordering': "('name',)", 'unique_together': "(('app_label', 'model'),)", 'object_name': 'ContentType', 'db_table': "'django_content_type'"},
            'app_label': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'model': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '100'})
        },
        'judge.attachment': {
            'Meta': {'object_name': 'Attachment'},
            'file': ('django.db.models.fields.files.FileField', [], {'max_length': '1024'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'problem': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['judge.Problem']"})
        },
        'judge.problem': {
            'Meta': {'object_name': 'Problem'},
            'accepted_count': ('django.db.models.fields.IntegerField', [], {'default': '0'}),
            'description': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'input': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'judge_module': ('django.db.models.fields.CharField', [], {'max_length': '100', 'blank': 'True'}),
            'memory_limit': ('django.db.models.fields.PositiveIntegerField', [], {'default': '65536'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '100', 'blank': 'True'}),
            'note': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'output': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'sample_input': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'sample_output': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'slug': ('django.db.models.fields.SlugField', [], {'db_index': 'True', 'max_length': '100', 'blank': 'True'}),
            'source': ('django.db.models.fields.CharField', [], {'max_length': '100', 'blank': 'True'}),
            'state': ('django.db.models.fields.SmallIntegerField', [], {'default': '0'}),
            'submissions_count': ('django.db.models.fields.IntegerField', [], {'default': '0'}),
            'time_limit': ('django.db.models.fields.PositiveIntegerField', [], {'default': '10000'}),
            'updated_on': ('django.db.models.fields.DateTimeField', [], {'auto_now': 'True', 'blank': 'True'}),
            'user': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['auth.User']"})
        },
        'judge.solver': {
            'Meta': {'object_name': 'Solver'},
            'fastest_submission': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'+'", 'null': 'True', 'to': "orm['judge.Submission']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'incorrect_tries': ('django.db.models.fields.IntegerField', [], {'default': '0'}),
            'problem': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['judge.Problem']"}),
            'shortest_submission': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'+'", 'null': 'True', 'to': "orm['judge.Submission']"}),
            'solved': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'user': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['auth.User']"})
        },
        'judge.submission': {
            'Meta': {'object_name': 'Submission'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'is_public': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'language': ('django.db.models.fields.TextField', [], {'max_length': '100'}),
            'length': ('django.db.models.fields.IntegerField', [], {}),
            'memory': ('django.db.models.fields.IntegerField', [], {'null': 'True'}),
            'message': ('django.db.models.fields.TextField', [], {'default': "''", 'blank': 'True'}),
            'problem': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['judge.Problem']"}),
            'source': ('django.db.models.fields.TextField', [], {}),
            'state': ('django.db.models.fields.SmallIntegerField', [], {'default': '0'}),
            'submitted_on': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'time': ('django.db.models.fields.IntegerField', [], {'null': 'True'}),
            'user': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['auth.User']"})
        }
    }

    complete_apps = ['judge']

########NEW FILE########
__FILENAME__ = 0008_auto
# encoding: utf-8
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models

class Migration(SchemaMigration):

    def forwards(self, orm):
        
        # Adding index on 'Solver', fields ['solved']
        db.create_index('judge_solver', ['solved'])

        # Adding index on 'Problem', fields ['source']
        db.create_index('judge_problem', ['source'])

        # Adding index on 'Problem', fields ['state']
        db.create_index('judge_problem', ['state'])

        # Adding index on 'Submission', fields ['time']
        db.create_index('judge_submission', ['time'])

        # Adding index on 'Submission', fields ['state']
        db.create_index('judge_submission', ['state'])

        # Adding index on 'Submission', fields ['length']
        db.create_index('judge_submission', ['length'])


    def backwards(self, orm):
        
        # Removing index on 'Submission', fields ['length']
        db.delete_index('judge_submission', ['length'])

        # Removing index on 'Submission', fields ['state']
        db.delete_index('judge_submission', ['state'])

        # Removing index on 'Submission', fields ['time']
        db.delete_index('judge_submission', ['time'])

        # Removing index on 'Problem', fields ['state']
        db.delete_index('judge_problem', ['state'])

        # Removing index on 'Problem', fields ['source']
        db.delete_index('judge_problem', ['source'])

        # Removing index on 'Solver', fields ['solved']
        db.delete_index('judge_solver', ['solved'])


    models = {
        'auth.group': {
            'Meta': {'object_name': 'Group'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '80'}),
            'permissions': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['auth.Permission']", 'symmetrical': 'False', 'blank': 'True'})
        },
        'auth.permission': {
            'Meta': {'ordering': "('content_type__app_label', 'content_type__model', 'codename')", 'unique_together': "(('content_type', 'codename'),)", 'object_name': 'Permission'},
            'codename': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'content_type': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['contenttypes.ContentType']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '50'})
        },
        'auth.user': {
            'Meta': {'object_name': 'User'},
            'date_joined': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'email': ('django.db.models.fields.EmailField', [], {'max_length': '75', 'blank': 'True'}),
            'first_name': ('django.db.models.fields.CharField', [], {'max_length': '30', 'blank': 'True'}),
            'groups': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['auth.Group']", 'symmetrical': 'False', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'is_active': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'is_staff': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'is_superuser': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'last_login': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'last_name': ('django.db.models.fields.CharField', [], {'max_length': '30', 'blank': 'True'}),
            'password': ('django.db.models.fields.CharField', [], {'max_length': '128'}),
            'user_permissions': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['auth.Permission']", 'symmetrical': 'False', 'blank': 'True'}),
            'username': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '30'})
        },
        'contenttypes.contenttype': {
            'Meta': {'ordering': "('name',)", 'unique_together': "(('app_label', 'model'),)", 'object_name': 'ContentType', 'db_table': "'django_content_type'"},
            'app_label': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'model': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '100'})
        },
        'judge.attachment': {
            'Meta': {'object_name': 'Attachment'},
            'file': ('django.db.models.fields.files.FileField', [], {'max_length': '1024'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'problem': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['judge.Problem']"})
        },
        'judge.problem': {
            'Meta': {'object_name': 'Problem'},
            'accepted_count': ('django.db.models.fields.IntegerField', [], {'default': '0'}),
            'description': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'input': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'judge_module': ('django.db.models.fields.CharField', [], {'max_length': '100', 'blank': 'True'}),
            'memory_limit': ('django.db.models.fields.PositiveIntegerField', [], {'default': '65536'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '100', 'blank': 'True'}),
            'note': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'output': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'sample_input': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'sample_output': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'slug': ('django.db.models.fields.SlugField', [], {'db_index': 'True', 'max_length': '100', 'blank': 'True'}),
            'source': ('django.db.models.fields.CharField', [], {'db_index': 'True', 'max_length': '100', 'blank': 'True'}),
            'state': ('django.db.models.fields.SmallIntegerField', [], {'default': '0', 'db_index': 'True'}),
            'submissions_count': ('django.db.models.fields.IntegerField', [], {'default': '0'}),
            'time_limit': ('django.db.models.fields.PositiveIntegerField', [], {'default': '10000'}),
            'updated_on': ('django.db.models.fields.DateTimeField', [], {'auto_now': 'True', 'blank': 'True'}),
            'user': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['auth.User']"})
        },
        'judge.solver': {
            'Meta': {'object_name': 'Solver'},
            'fastest_submission': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'+'", 'null': 'True', 'to': "orm['judge.Submission']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'incorrect_tries': ('django.db.models.fields.IntegerField', [], {'default': '0'}),
            'problem': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['judge.Problem']"}),
            'shortest_submission': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'+'", 'null': 'True', 'to': "orm['judge.Submission']"}),
            'solved': ('django.db.models.fields.BooleanField', [], {'default': 'False', 'db_index': 'True'}),
            'user': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['auth.User']"})
        },
        'judge.submission': {
            'Meta': {'object_name': 'Submission'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'is_public': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'language': ('django.db.models.fields.TextField', [], {'max_length': '100'}),
            'length': ('django.db.models.fields.IntegerField', [], {'db_index': 'True'}),
            'memory': ('django.db.models.fields.IntegerField', [], {'null': 'True'}),
            'message': ('django.db.models.fields.TextField', [], {'default': "''", 'blank': 'True'}),
            'problem': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['judge.Problem']"}),
            'source': ('django.db.models.fields.TextField', [], {}),
            'state': ('django.db.models.fields.SmallIntegerField', [], {'default': '0', 'db_index': 'True'}),
            'submitted_on': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'time': ('django.db.models.fields.IntegerField', [], {'null': 'True', 'db_index': 'True'}),
            'user': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['auth.User']"})
        }
    }

    complete_apps = ['judge']

########NEW FILE########
__FILENAME__ = 0009_auto__add_field_solver_when
# encoding: utf-8
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models

class Migration(SchemaMigration):

    def forwards(self, orm):
        
        # Adding field 'Solver.when'
        db.add_column('judge_solver', 'when', self.gf('django.db.models.fields.DateTimeField')(null=True), keep_default=False)


    def backwards(self, orm):
        
        # Deleting field 'Solver.when'
        db.delete_column('judge_solver', 'when')


    models = {
        'auth.group': {
            'Meta': {'object_name': 'Group'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '80'}),
            'permissions': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['auth.Permission']", 'symmetrical': 'False', 'blank': 'True'})
        },
        'auth.permission': {
            'Meta': {'ordering': "('content_type__app_label', 'content_type__model', 'codename')", 'unique_together': "(('content_type', 'codename'),)", 'object_name': 'Permission'},
            'codename': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'content_type': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['contenttypes.ContentType']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '50'})
        },
        'auth.user': {
            'Meta': {'object_name': 'User'},
            'date_joined': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'email': ('django.db.models.fields.EmailField', [], {'max_length': '75', 'blank': 'True'}),
            'first_name': ('django.db.models.fields.CharField', [], {'max_length': '30', 'blank': 'True'}),
            'groups': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['auth.Group']", 'symmetrical': 'False', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'is_active': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'is_staff': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'is_superuser': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'last_login': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'last_name': ('django.db.models.fields.CharField', [], {'max_length': '30', 'blank': 'True'}),
            'password': ('django.db.models.fields.CharField', [], {'max_length': '128'}),
            'user_permissions': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['auth.Permission']", 'symmetrical': 'False', 'blank': 'True'}),
            'username': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '30'})
        },
        'contenttypes.contenttype': {
            'Meta': {'ordering': "('name',)", 'unique_together': "(('app_label', 'model'),)", 'object_name': 'ContentType', 'db_table': "'django_content_type'"},
            'app_label': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'model': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '100'})
        },
        'judge.attachment': {
            'Meta': {'object_name': 'Attachment'},
            'file': ('django.db.models.fields.files.FileField', [], {'max_length': '1024'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'problem': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['judge.Problem']"})
        },
        'judge.problem': {
            'Meta': {'object_name': 'Problem'},
            'accepted_count': ('django.db.models.fields.IntegerField', [], {'default': '0'}),
            'description': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'input': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'judge_module': ('django.db.models.fields.CharField', [], {'max_length': '100', 'blank': 'True'}),
            'memory_limit': ('django.db.models.fields.PositiveIntegerField', [], {'default': '65536'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '100', 'blank': 'True'}),
            'note': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'output': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'sample_input': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'sample_output': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'slug': ('django.db.models.fields.SlugField', [], {'db_index': 'True', 'max_length': '100', 'blank': 'True'}),
            'source': ('django.db.models.fields.CharField', [], {'db_index': 'True', 'max_length': '100', 'blank': 'True'}),
            'state': ('django.db.models.fields.SmallIntegerField', [], {'default': '0', 'db_index': 'True'}),
            'submissions_count': ('django.db.models.fields.IntegerField', [], {'default': '0'}),
            'time_limit': ('django.db.models.fields.PositiveIntegerField', [], {'default': '10000'}),
            'updated_on': ('django.db.models.fields.DateTimeField', [], {'auto_now': 'True', 'blank': 'True'}),
            'user': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['auth.User']"})
        },
        'judge.solver': {
            'Meta': {'object_name': 'Solver'},
            'fastest_submission': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'+'", 'null': 'True', 'to': "orm['judge.Submission']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'incorrect_tries': ('django.db.models.fields.IntegerField', [], {'default': '0'}),
            'problem': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['judge.Problem']"}),
            'shortest_submission': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'+'", 'null': 'True', 'to': "orm['judge.Submission']"}),
            'solved': ('django.db.models.fields.BooleanField', [], {'default': 'False', 'db_index': 'True'}),
            'user': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['auth.User']"}),
            'when': ('django.db.models.fields.DateTimeField', [], {'null': 'True'})
        },
        'judge.submission': {
            'Meta': {'object_name': 'Submission'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'is_public': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'language': ('django.db.models.fields.TextField', [], {'max_length': '100'}),
            'length': ('django.db.models.fields.IntegerField', [], {'db_index': 'True'}),
            'memory': ('django.db.models.fields.IntegerField', [], {'null': 'True'}),
            'message': ('django.db.models.fields.TextField', [], {'default': "''", 'blank': 'True'}),
            'problem': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['judge.Problem']"}),
            'source': ('django.db.models.fields.TextField', [], {}),
            'state': ('django.db.models.fields.SmallIntegerField', [], {'default': '0', 'db_index': 'True'}),
            'submitted_on': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'time': ('django.db.models.fields.IntegerField', [], {'null': 'True', 'db_index': 'True'}),
            'user': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['auth.User']"})
        }
    }

    complete_apps = ['judge']

########NEW FILE########
__FILENAME__ = 0010_auto__add_problemrevision__add_field_problem_last_revision__add_unique
# encoding: utf-8
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models

class Migration(SchemaMigration):

    def forwards(self, orm):
        
        # Adding model 'ProblemRevision'
        db.create_table('judge_problemrevision', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('revision_for', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['judge.Problem'])),
            ('created_on', self.gf('django.db.models.fields.DateTimeField')(auto_now_add=True, blank=True)),
            ('user', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['auth.User'])),
            ('edit_summary', self.gf('django.db.models.fields.TextField')(max_length=100)),
            ('description', self.gf('django.db.models.fields.TextField')(blank=True)),
            ('input', self.gf('django.db.models.fields.TextField')(blank=True)),
            ('output', self.gf('django.db.models.fields.TextField')(blank=True)),
            ('sample_input', self.gf('django.db.models.fields.TextField')(blank=True)),
            ('sample_output', self.gf('django.db.models.fields.TextField')(blank=True)),
            ('note', self.gf('django.db.models.fields.TextField')(blank=True)),
            ('time_limit', self.gf('django.db.models.fields.PositiveIntegerField')(default=10000)),
            ('memory_limit', self.gf('django.db.models.fields.PositiveIntegerField')(default=65536)),
        ))
        db.send_create_signal('judge', ['ProblemRevision'])

        # Adding field 'Problem.last_revision'
        db.add_column('judge_problem', 'last_revision', self.gf('django.db.models.fields.related.ForeignKey')(blank=True, related_name='main', null=True, to=orm['judge.ProblemRevision']), keep_default=False)

        # Adding unique constraint on 'Problem', fields ['slug']
        db.create_unique('judge_problem', ['slug'])


    def backwards(self, orm):
        
        # Removing unique constraint on 'Problem', fields ['slug']
        db.delete_unique('judge_problem', ['slug'])

        # Deleting model 'ProblemRevision'
        db.delete_table('judge_problemrevision')

        # Deleting field 'Problem.last_revision'
        db.delete_column('judge_problem', 'last_revision_id')


    models = {
        'auth.group': {
            'Meta': {'object_name': 'Group'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '80'}),
            'permissions': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['auth.Permission']", 'symmetrical': 'False', 'blank': 'True'})
        },
        'auth.permission': {
            'Meta': {'ordering': "('content_type__app_label', 'content_type__model', 'codename')", 'unique_together': "(('content_type', 'codename'),)", 'object_name': 'Permission'},
            'codename': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'content_type': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['contenttypes.ContentType']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '50'})
        },
        'auth.user': {
            'Meta': {'object_name': 'User'},
            'date_joined': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'email': ('django.db.models.fields.EmailField', [], {'max_length': '75', 'blank': 'True'}),
            'first_name': ('django.db.models.fields.CharField', [], {'max_length': '30', 'blank': 'True'}),
            'groups': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['auth.Group']", 'symmetrical': 'False', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'is_active': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'is_staff': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'is_superuser': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'last_login': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'last_name': ('django.db.models.fields.CharField', [], {'max_length': '30', 'blank': 'True'}),
            'password': ('django.db.models.fields.CharField', [], {'max_length': '128'}),
            'user_permissions': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['auth.Permission']", 'symmetrical': 'False', 'blank': 'True'}),
            'username': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '30'})
        },
        'contenttypes.contenttype': {
            'Meta': {'ordering': "('name',)", 'unique_together': "(('app_label', 'model'),)", 'object_name': 'ContentType', 'db_table': "'django_content_type'"},
            'app_label': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'model': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '100'})
        },
        'judge.attachment': {
            'Meta': {'object_name': 'Attachment'},
            'file': ('django.db.models.fields.files.FileField', [], {'max_length': '1024'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'problem': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['judge.Problem']"})
        },
        'judge.problem': {
            'Meta': {'object_name': 'Problem'},
            'accepted_count': ('django.db.models.fields.IntegerField', [], {'default': '0'}),
            'description': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'input': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'judge_module': ('django.db.models.fields.CharField', [], {'max_length': '100', 'blank': 'True'}),
            'last_revision': ('django.db.models.fields.related.ForeignKey', [], {'blank': 'True', 'related_name': "'main'", 'null': 'True', 'to': "orm['judge.ProblemRevision']"}),
            'memory_limit': ('django.db.models.fields.PositiveIntegerField', [], {'default': '65536'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '100', 'blank': 'True'}),
            'note': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'output': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'sample_input': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'sample_output': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'slug': ('django.db.models.fields.SlugField', [], {'unique': 'True', 'max_length': '100', 'db_index': 'True'}),
            'source': ('django.db.models.fields.CharField', [], {'db_index': 'True', 'max_length': '100', 'blank': 'True'}),
            'state': ('django.db.models.fields.SmallIntegerField', [], {'default': '0', 'db_index': 'True'}),
            'submissions_count': ('django.db.models.fields.IntegerField', [], {'default': '0'}),
            'time_limit': ('django.db.models.fields.PositiveIntegerField', [], {'default': '10000'}),
            'updated_on': ('django.db.models.fields.DateTimeField', [], {'auto_now': 'True', 'blank': 'True'}),
            'user': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['auth.User']"})
        },
        'judge.problemrevision': {
            'Meta': {'object_name': 'ProblemRevision'},
            'created_on': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'description': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'edit_summary': ('django.db.models.fields.TextField', [], {'max_length': '100'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'input': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'memory_limit': ('django.db.models.fields.PositiveIntegerField', [], {'default': '65536'}),
            'note': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'output': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'revision_for': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['judge.Problem']"}),
            'sample_input': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'sample_output': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'time_limit': ('django.db.models.fields.PositiveIntegerField', [], {'default': '10000'}),
            'user': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['auth.User']"})
        },
        'judge.solver': {
            'Meta': {'object_name': 'Solver'},
            'fastest_submission': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'+'", 'null': 'True', 'to': "orm['judge.Submission']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'incorrect_tries': ('django.db.models.fields.IntegerField', [], {'default': '0'}),
            'problem': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['judge.Problem']"}),
            'shortest_submission': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'+'", 'null': 'True', 'to': "orm['judge.Submission']"}),
            'solved': ('django.db.models.fields.BooleanField', [], {'default': 'False', 'db_index': 'True'}),
            'user': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['auth.User']"}),
            'when': ('django.db.models.fields.DateTimeField', [], {'null': 'True'})
        },
        'judge.submission': {
            'Meta': {'object_name': 'Submission'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'is_public': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'language': ('django.db.models.fields.TextField', [], {'max_length': '100'}),
            'length': ('django.db.models.fields.IntegerField', [], {'db_index': 'True'}),
            'memory': ('django.db.models.fields.IntegerField', [], {'null': 'True'}),
            'message': ('django.db.models.fields.TextField', [], {'default': "''", 'blank': 'True'}),
            'problem': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['judge.Problem']"}),
            'source': ('django.db.models.fields.TextField', [], {}),
            'state': ('django.db.models.fields.SmallIntegerField', [], {'default': '0', 'db_index': 'True'}),
            'submitted_on': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'time': ('django.db.models.fields.IntegerField', [], {'null': 'True', 'db_index': 'True'}),
            'user': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['auth.User']"})
        }
    }

    complete_apps = ['judge']

########NEW FILE########
__FILENAME__ = 0011_save_problem_as_revision
# encoding: utf-8
import datetime
from south.db import db
from south.v2 import DataMigration
from django.db import models

class Migration(DataMigration):

    def forwards(self, orm):
        for problem in orm.Problem.objects.all():
        	new_revision = orm.ProblemRevision()
        	new_revision.revision_for = problem
        	new_revision.created_on = problem.updated_on
        	new_revision.user = problem.user
        	new_revision.edit_summary = u"Initial edit."

        	new_revision.description = problem.description
        	new_revision.input = problem.input
        	new_revision.output = problem.output
        	new_revision.sample_input = problem.sample_input
        	new_revision.sample_output = problem.sample_output
        	new_revision.note = problem.note
        	new_revision.time_limit = problem.time_limit
        	new_revision.memory_limit = problem.memory_limit
        	new_revision.save()

        	problem.last_revision = new_revision
        	problem.save()

    def backwards(self, orm):
        for problem in orm.Problem.objects.all():
        	last_revision = problem.last_revision
        	problem.description = last_revision.description
        	problem.input = last_revision.input
        	problem.output = last_revision.output
        	problem.sample_input = last_revision.sample_input
        	problem.sample_output = last_revision.sample_output
        	problem.note = last_revision.note
        	problem.time_limit = last_revision.time_limit
        	problem.memory_limit = last_revision.memory_limit
        	problem.updated_on = last_revision.created_on
        	problem.last_revision = None
        	problem.save()
        for revision in orm.ProblemRevision.objects.all():
        	revision.delete()

    models = {
        'auth.group': {
            'Meta': {'object_name': 'Group'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '80'}),
            'permissions': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['auth.Permission']", 'symmetrical': 'False', 'blank': 'True'})
        },
        'auth.permission': {
            'Meta': {'ordering': "('content_type__app_label', 'content_type__model', 'codename')", 'unique_together': "(('content_type', 'codename'),)", 'object_name': 'Permission'},
            'codename': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'content_type': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['contenttypes.ContentType']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '50'})
        },
        'auth.user': {
            'Meta': {'object_name': 'User'},
            'date_joined': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'email': ('django.db.models.fields.EmailField', [], {'max_length': '75', 'blank': 'True'}),
            'first_name': ('django.db.models.fields.CharField', [], {'max_length': '30', 'blank': 'True'}),
            'groups': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['auth.Group']", 'symmetrical': 'False', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'is_active': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'is_staff': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'is_superuser': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'last_login': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'last_name': ('django.db.models.fields.CharField', [], {'max_length': '30', 'blank': 'True'}),
            'password': ('django.db.models.fields.CharField', [], {'max_length': '128'}),
            'user_permissions': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['auth.Permission']", 'symmetrical': 'False', 'blank': 'True'}),
            'username': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '30'})
        },
        'contenttypes.contenttype': {
            'Meta': {'ordering': "('name',)", 'unique_together': "(('app_label', 'model'),)", 'object_name': 'ContentType', 'db_table': "'django_content_type'"},
            'app_label': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'model': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '100'})
        },
        'judge.attachment': {
            'Meta': {'object_name': 'Attachment'},
            'file': ('django.db.models.fields.files.FileField', [], {'max_length': '1024'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'problem': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['judge.Problem']"})
        },
        'judge.problem': {
            'Meta': {'object_name': 'Problem'},
            'accepted_count': ('django.db.models.fields.IntegerField', [], {'default': '0'}),
            'description': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'input': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'judge_module': ('django.db.models.fields.CharField', [], {'max_length': '100', 'blank': 'True'}),
            'last_revision': ('django.db.models.fields.related.ForeignKey', [], {'blank': 'True', 'related_name': "'main'", 'null': 'True', 'to': "orm['judge.ProblemRevision']"}),
            'memory_limit': ('django.db.models.fields.PositiveIntegerField', [], {'default': '65536'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '100', 'blank': 'True'}),
            'note': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'output': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'sample_input': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'sample_output': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'slug': ('django.db.models.fields.SlugField', [], {'unique': 'True', 'max_length': '100', 'db_index': 'True'}),
            'source': ('django.db.models.fields.CharField', [], {'db_index': 'True', 'max_length': '100', 'blank': 'True'}),
            'state': ('django.db.models.fields.SmallIntegerField', [], {'default': '0', 'db_index': 'True'}),
            'submissions_count': ('django.db.models.fields.IntegerField', [], {'default': '0'}),
            'time_limit': ('django.db.models.fields.PositiveIntegerField', [], {'default': '10000'}),
            'updated_on': ('django.db.models.fields.DateTimeField', [], {'auto_now': 'True', 'blank': 'True'}),
            'user': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['auth.User']"})
        },
        'judge.problemrevision': {
            'Meta': {'object_name': 'ProblemRevision'},
            'created_on': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'description': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'edit_summary': ('django.db.models.fields.TextField', [], {'max_length': '100'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'input': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'memory_limit': ('django.db.models.fields.PositiveIntegerField', [], {'default': '65536'}),
            'note': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'output': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'revision_for': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['judge.Problem']"}),
            'sample_input': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'sample_output': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'time_limit': ('django.db.models.fields.PositiveIntegerField', [], {'default': '10000'}),
            'user': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['auth.User']"})
        },
        'judge.solver': {
            'Meta': {'object_name': 'Solver'},
            'fastest_submission': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'+'", 'null': 'True', 'to': "orm['judge.Submission']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'incorrect_tries': ('django.db.models.fields.IntegerField', [], {'default': '0'}),
            'problem': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['judge.Problem']"}),
            'shortest_submission': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'+'", 'null': 'True', 'to': "orm['judge.Submission']"}),
            'solved': ('django.db.models.fields.BooleanField', [], {'default': 'False', 'db_index': 'True'}),
            'user': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['auth.User']"}),
            'when': ('django.db.models.fields.DateTimeField', [], {'null': 'True'})
        },
        'judge.submission': {
            'Meta': {'object_name': 'Submission'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'is_public': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'language': ('django.db.models.fields.TextField', [], {'max_length': '100'}),
            'length': ('django.db.models.fields.IntegerField', [], {'db_index': 'True'}),
            'memory': ('django.db.models.fields.IntegerField', [], {'null': 'True'}),
            'message': ('django.db.models.fields.TextField', [], {'default': "''", 'blank': 'True'}),
            'problem': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['judge.Problem']"}),
            'source': ('django.db.models.fields.TextField', [], {}),
            'state': ('django.db.models.fields.SmallIntegerField', [], {'default': '0', 'db_index': 'True'}),
            'submitted_on': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'time': ('django.db.models.fields.IntegerField', [], {'null': 'True', 'db_index': 'True'}),
            'user': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['auth.User']"})
        }
    }

    complete_apps = ['judge']

########NEW FILE########
__FILENAME__ = 0012_auto__del_field_problem_memory_limit__del_field_problem_sample_output_
# encoding: utf-8
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models

class Migration(SchemaMigration):

    def forwards(self, orm):
        
        # Deleting field 'Problem.memory_limit'
        db.delete_column('judge_problem', 'memory_limit')

        # Deleting field 'Problem.sample_output'
        db.delete_column('judge_problem', 'sample_output')

        # Deleting field 'Problem.description'
        db.delete_column('judge_problem', 'description')

        # Deleting field 'Problem.time_limit'
        db.delete_column('judge_problem', 'time_limit')

        # Deleting field 'Problem.sample_input'
        db.delete_column('judge_problem', 'sample_input')

        # Deleting field 'Problem.note'
        db.delete_column('judge_problem', 'note')

        # Deleting field 'Problem.updated_on'
        db.delete_column('judge_problem', 'updated_on')

        # Deleting field 'Problem.output'
        db.delete_column('judge_problem', 'output')

        # Deleting field 'Problem.input'
        db.delete_column('judge_problem', 'input')


    def backwards(self, orm):
        
        # Adding field 'Problem.memory_limit'
        db.add_column('judge_problem', 'memory_limit', self.gf('django.db.models.fields.PositiveIntegerField')(default=65536), keep_default=False)

        # Adding field 'Problem.sample_output'
        db.add_column('judge_problem', 'sample_output', self.gf('django.db.models.fields.TextField')(default='', blank=True), keep_default=False)

        # Adding field 'Problem.description'
        db.add_column('judge_problem', 'description', self.gf('django.db.models.fields.TextField')(default='', blank=True), keep_default=False)

        # Adding field 'Problem.time_limit'
        db.add_column('judge_problem', 'time_limit', self.gf('django.db.models.fields.PositiveIntegerField')(default=10000), keep_default=False)

        # Adding field 'Problem.sample_input'
        db.add_column('judge_problem', 'sample_input', self.gf('django.db.models.fields.TextField')(default='', blank=True), keep_default=False)

        # Adding field 'Problem.note'
        db.add_column('judge_problem', 'note', self.gf('django.db.models.fields.TextField')(default='', blank=True), keep_default=False)

        # Adding field 'Problem.updated_on'
        db.add_column('judge_problem', 'updated_on', self.gf('django.db.models.fields.DateTimeField')(auto_now=True, default=datetime.datetime(2012, 7, 8, 16, 49, 30, 479650), blank=True), keep_default=False)

        # Adding field 'Problem.output'
        db.add_column('judge_problem', 'output', self.gf('django.db.models.fields.TextField')(default='', blank=True), keep_default=False)

        # Adding field 'Problem.input'
        db.add_column('judge_problem', 'input', self.gf('django.db.models.fields.TextField')(default='', blank=True), keep_default=False)


    models = {
        'auth.group': {
            'Meta': {'object_name': 'Group'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '80'}),
            'permissions': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['auth.Permission']", 'symmetrical': 'False', 'blank': 'True'})
        },
        'auth.permission': {
            'Meta': {'ordering': "('content_type__app_label', 'content_type__model', 'codename')", 'unique_together': "(('content_type', 'codename'),)", 'object_name': 'Permission'},
            'codename': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'content_type': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['contenttypes.ContentType']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '50'})
        },
        'auth.user': {
            'Meta': {'object_name': 'User'},
            'date_joined': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'email': ('django.db.models.fields.EmailField', [], {'max_length': '75', 'blank': 'True'}),
            'first_name': ('django.db.models.fields.CharField', [], {'max_length': '30', 'blank': 'True'}),
            'groups': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['auth.Group']", 'symmetrical': 'False', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'is_active': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'is_staff': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'is_superuser': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'last_login': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'last_name': ('django.db.models.fields.CharField', [], {'max_length': '30', 'blank': 'True'}),
            'password': ('django.db.models.fields.CharField', [], {'max_length': '128'}),
            'user_permissions': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['auth.Permission']", 'symmetrical': 'False', 'blank': 'True'}),
            'username': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '30'})
        },
        'contenttypes.contenttype': {
            'Meta': {'ordering': "('name',)", 'unique_together': "(('app_label', 'model'),)", 'object_name': 'ContentType', 'db_table': "'django_content_type'"},
            'app_label': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'model': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '100'})
        },
        'judge.attachment': {
            'Meta': {'object_name': 'Attachment'},
            'file': ('django.db.models.fields.files.FileField', [], {'max_length': '1024'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'problem': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['judge.Problem']"})
        },
        'judge.problem': {
            'Meta': {'object_name': 'Problem'},
            'accepted_count': ('django.db.models.fields.IntegerField', [], {'default': '0'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'judge_module': ('django.db.models.fields.CharField', [], {'max_length': '100', 'blank': 'True'}),
            'last_revision': ('django.db.models.fields.related.ForeignKey', [], {'blank': 'True', 'related_name': "'main'", 'null': 'True', 'to': "orm['judge.ProblemRevision']"}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '100', 'blank': 'True'}),
            'slug': ('django.db.models.fields.SlugField', [], {'unique': 'True', 'max_length': '100', 'db_index': 'True'}),
            'source': ('django.db.models.fields.CharField', [], {'db_index': 'True', 'max_length': '100', 'blank': 'True'}),
            'state': ('django.db.models.fields.SmallIntegerField', [], {'default': '0', 'db_index': 'True'}),
            'submissions_count': ('django.db.models.fields.IntegerField', [], {'default': '0'}),
            'user': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['auth.User']"})
        },
        'judge.problemrevision': {
            'Meta': {'object_name': 'ProblemRevision'},
            'created_on': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'description': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'edit_summary': ('django.db.models.fields.TextField', [], {'max_length': '100'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'input': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'memory_limit': ('django.db.models.fields.PositiveIntegerField', [], {'default': '65536'}),
            'note': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'output': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'revision_for': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['judge.Problem']"}),
            'sample_input': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'sample_output': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'time_limit': ('django.db.models.fields.PositiveIntegerField', [], {'default': '10000'}),
            'user': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['auth.User']"})
        },
        'judge.solver': {
            'Meta': {'object_name': 'Solver'},
            'fastest_submission': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'+'", 'null': 'True', 'to': "orm['judge.Submission']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'incorrect_tries': ('django.db.models.fields.IntegerField', [], {'default': '0'}),
            'problem': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['judge.Problem']"}),
            'shortest_submission': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'+'", 'null': 'True', 'to': "orm['judge.Submission']"}),
            'solved': ('django.db.models.fields.BooleanField', [], {'default': 'False', 'db_index': 'True'}),
            'user': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['auth.User']"}),
            'when': ('django.db.models.fields.DateTimeField', [], {'null': 'True'})
        },
        'judge.submission': {
            'Meta': {'object_name': 'Submission'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'is_public': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'language': ('django.db.models.fields.TextField', [], {'max_length': '100'}),
            'length': ('django.db.models.fields.IntegerField', [], {'db_index': 'True'}),
            'memory': ('django.db.models.fields.IntegerField', [], {'null': 'True'}),
            'message': ('django.db.models.fields.TextField', [], {'default': "''", 'blank': 'True'}),
            'problem': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['judge.Problem']"}),
            'source': ('django.db.models.fields.TextField', [], {}),
            'state': ('django.db.models.fields.SmallIntegerField', [], {'default': '0', 'db_index': 'True'}),
            'submitted_on': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'time': ('django.db.models.fields.IntegerField', [], {'null': 'True', 'db_index': 'True'}),
            'user': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['auth.User']"})
        }
    }

    complete_apps = ['judge']

########NEW FILE########
__FILENAME__ = models
# -*- coding: utf-8 -*-
from django.db import models
from django.contrib.auth.models import User
from django.core.urlresolvers import reverse
from django.db.models.signals import post_save
from django.db.models import Count
from guardian.shortcuts import get_users_with_perms, get_groups_with_perms, assign_perm
from newsfeed import publish, depublish, has_activity, get_activity
from djangoutils import get_or_none
import pygooglechart as pgc
import tagging

class ProblemRevision(models.Model):
    revision_for = models.ForeignKey('Problem')
    created_on = models.DateTimeField(auto_now_add=True)
    user = models.ForeignKey(User, verbose_name=u"편집자")
    edit_summary = models.TextField(max_length=100, blank=True)

    description = models.TextField(u"설명", blank=True)
    input = models.TextField(u"입력 설명", blank=True)
    output = models.TextField(u"출력 설명", blank=True)
    sample_input = models.TextField(u"예제 입력", blank=True)
    sample_output = models.TextField(u"예제 출력", blank=True)
    note = models.TextField(u"노트", blank=True)
    time_limit = models.PositiveIntegerField(u"시간 제한 (ms)", default=10000)
    memory_limit = models.PositiveIntegerField(u"메모리 제한 (kb)", default=65536)

    def different_from(self, other):
        return (self.description != other.description or 
               self.input != other.input or 
               self.output != other.output or 
               self.sample_input != other.sample_input or 
               self.sample_output != other.sample_output or 
               self.note != other.note or 
               self.time_limit != other.time_limit or 
               self.memory_limit != other.memory_limit)

def problem_revision_edit_handler(sender, **kwargs):
    instance = kwargs["instance"]

    # 해당 오브젝트에 대해 아무 퍼미션이나 있으면 처리됨. 문제의 경우 PUBLISHED 일 때는 이 권한을 사용하지 않아서 안전하다
    visible_users = get_users_with_perms(instance.revision_for, with_group_users=False)
    visible_groups = get_groups_with_perms(instance.revision_for)
    print visible_users
    print visible_groups

    publish("problem-edit-%d" % instance.id,
            "problem",
            "problem-edit",
            actor=instance.user,
            target=instance.revision_for,
            timestamp=instance.created_on,
            visible_users=visible_users,
            visible_groups=visible_groups,
            verb=u"문제 {target}을 편집했습니다.")

post_save.connect(problem_revision_edit_handler, sender=ProblemRevision, dispatch_uid="problem_edit_event")

class Problem(models.Model):
    DRAFT, PENDING_REVIEW, HIDDEN, PUBLISHED = range(4)
    STATE_CHOICES = ((DRAFT, "DRAFT"),
                     (PENDING_REVIEW, "PENDING REVIEW"),
                     (HIDDEN, "HIDDEN"),
                     (PUBLISHED, "PUBLISHED"))

    slug = models.SlugField(u"문제 ID", max_length=100, unique=True)
    state = models.SmallIntegerField(u"문제 상태", default=DRAFT,
                                     choices=STATE_CHOICES,
                                     db_index=True)
    user = models.ForeignKey(User, verbose_name=u"작성자", db_index=True)
    source = models.CharField(u"출처", max_length=100, blank=True, db_index=True)
    name = models.CharField(u"이름", max_length=100, blank=True)
    judge_module = models.CharField(u"채점 모듈", blank=True, max_length=100)
    submissions_count = models.IntegerField(default=0)
    accepted_count = models.IntegerField(default=0)

    last_revision = models.ForeignKey(ProblemRevision, related_name='main', blank=True, null=True)

    def __unicode__(self):
        return self.slug

    def get_state_name(self):
        return Problem.STATE_CHOICES[self.state][1]

    def was_solved_by(self, user):
        return Solver.objects.filter(problem=self, user=user,
                                     solved=True).exists()

    def get_absolute_url(self):
        return reverse("judge-problem-read", kwargs={"slug": self.slug})

    class Meta:
        permissions = (
            ('read_problem', 'Can read problem always'),
            ('edit_problem', 'Can edit problem always'),
        )

tagging.register(Problem)

class Attachment(models.Model):
    problem = models.ForeignKey(Problem, db_index=True)
    file = models.FileField(max_length=1024, upload_to='/will_not_be_used/')

class Submission(models.Model):
    (RECEIVED, COMPILING, RUNNING, JUDGING, COMPILE_ERROR,
    OK, ACCEPTED, WRONG_ANSWER, RUNTIME_ERROR, TIME_LIMIT_EXCEEDED,
    CANT_BE_JUDGED, REJUDGE_REQUESTED) = range(12)
    STATES_KOR = dict([(RECEIVED, u"수신"),
                       (COMPILING, u"컴파일중"),
                       (RUNNING, u"실행중"),
                       (JUDGING, u"채점중"),
                       (COMPILE_ERROR, u"컴파일 실패"),
                       (OK, u"수행완료"),
                       (ACCEPTED, u"정답"),
                       (WRONG_ANSWER, u"오답"),
                       (RUNTIME_ERROR, u"런타임 오류"),
                       (TIME_LIMIT_EXCEEDED, u"시간초과"),
                       (CANT_BE_JUDGED, u"채점실패"),
                       (REJUDGE_REQUESTED, u"재채점")])
    STATES_ENG = dict([(RECEIVED, "RECEIVED"),
                       (COMPILING, "COMPILING"),
                       (RUNNING, "RUNNING"),
                       (JUDGING, "JUDGING"),
                       (COMPILE_ERROR, "COMPILE_ERROR"),
                       (OK, "OK"),
                       (ACCEPTED, "ACCEPTED"),
                       (WRONG_ANSWER, "WRONG_ANSWER"),
                       (RUNTIME_ERROR, "RUNTIME_ERROR"),
                       (TIME_LIMIT_EXCEEDED, "TIME_LIMIT_EXCEEDED"),
                       (CANT_BE_JUDGED, "CANT_BE_JUDGED"),
                       (REJUDGE_REQUESTED, "REJUDGE_REQUESTED")])


    JUDGED = (ACCEPTED, WRONG_ANSWER, RUNTIME_ERROR, TIME_LIMIT_EXCEEDED,
              CANT_BE_JUDGED, COMPILE_ERROR)
    PROGRAM_HAS_RUN = (OK, ACCEPTED, WRONG_ANSWER)
    HAS_MESSAGES = (COMPILE_ERROR, RUNTIME_ERROR)

    submitted_on = models.DateTimeField(auto_now_add=True)
    problem = models.ForeignKey(Problem, db_index=True)
    is_public = models.BooleanField(default=True)
    user = models.ForeignKey(User, db_index=True)
    language = models.TextField(max_length=100)
    state = models.SmallIntegerField(default=RECEIVED,
                                     choices=STATES_ENG.items(),
                                     db_index=True)
    length = models.IntegerField(db_index=True)
    source = models.TextField()
    message = models.TextField(blank=True, default="")
    time = models.IntegerField(null=True, db_index=True)
    memory = models.IntegerField(null=True)

    def __unicode__(self):
        return "%s: %s" % (self.problem.slug,
                           self.user.username)

    def has_run(self):
        return self.state in self.PROGRAM_HAS_RUN

    # TODO: has_messages => has_message
    def has_messages(self):
        return bool(self.message)

    def is_judged(self):
        return self.state in Submission.JUDGED

    def is_accepted(self):
        return self.state == Submission.ACCEPTED

    def name_kor(self):
        return self.STATES_KOR[self.state]

    def name_eng(self):
        return self.STATES_ENG[self.state]

    def get_absolute_url(self):
        return reverse("judge-submission-details", kwargs={"id": self.id})

    def rejudge(self):
        self.message = ""
        self.time = None
        self.state = self.REJUDGE_REQUESTED
        self.save()

    @staticmethod
    def get_verdict_distribution(queryset):
        ret = {}
        for entry in queryset.values('state').annotate(Count('state')):
            ret[entry['state']] = entry['state__count']
        return ret

    @staticmethod
    def get_verdict_distribution_graph(queryset):
        queryset = queryset.filter(is_public=True)
        take = (Submission.ACCEPTED, Submission.WRONG_ANSWER,
                Submission.TIME_LIMIT_EXCEEDED)
        # AC, WA, TLE 이외의 것들을 하나의 카테고리로 모음
        cleaned = {-1: 0}
        for t in take: cleaned[t] = 0
        for verdict, count in Submission.get_verdict_distribution(queryset).items():
            if verdict in take:
                cleaned[verdict] = count
            else:
                cleaned[-1] += count

        # 구글 차트
        pie = pgc.PieChart2D(200, 120)
        if sum(cleaned.values()) == 0:
            pie.add_data([100])
            pie.set_legend(['NONE'])
            pie.set_colours(['999999'])
        else:
            pie.add_data([cleaned[Submission.ACCEPTED],
                          cleaned[Submission.WRONG_ANSWER],
                          cleaned[Submission.TIME_LIMIT_EXCEEDED],
                          cleaned[-1]])
        pie.set_legend(['AC', 'WA', 'TLE', 'OTHER'])
        pie.set_colours(["C02942", "53777A", "542437", "ECD078"])
        pie.fill_solid("bg", "65432100")
        return pie.get_url() + "&chp=4.712"


    @staticmethod
    def get_stat_for_user(user):
        ret = {}
        for entry in Submission.objects.filter(user=user).values('state').annotate(Count('state')):
            ret[entry['state']] = entry['state__count']
        return ret

class Solver(models.Model):
    problem = models.ForeignKey(Problem, db_index=True)
    user = models.ForeignKey(User, db_index=True)
    incorrect_tries = models.IntegerField(default=0)
    solved = models.BooleanField(default=False, db_index=True)
    fastest_submission = models.ForeignKey(Submission, null=True,
                                           related_name="+")
    shortest_submission = models.ForeignKey(Submission, null=True,
                                           related_name="+")
    when = models.DateTimeField(null=True)

    def __unicode__(self):
        return "%s: %s" % (self.problem.slug,
                           self.user.username)

    @staticmethod
    def get_incorrect_tries_chart(problem):

        solvers = Solver.objects.filter(problem=problem, solved=True)
        FAIL_DISPLAY_LIMIT = 50

        dist = {}
        for entry in solvers.values('incorrect_tries').annotate(Count('incorrect_tries')):
            incorrect_tries = min(FAIL_DISPLAY_LIMIT, entry['incorrect_tries'])
            dist[incorrect_tries] = entry['incorrect_tries__count']

        max_fails = max(dist.keys()) if dist else 0
        steps = max(1, max_fails / 10)
        chart = pgc.StackedVerticalBarChart(400, 120)
        chart.add_data([dist.get(i, 0) for i in xrange(max_fails + 1) ])
        chart.set_colours(['C02942'])
        def get_label(fails):
            if fails == FAIL_DISPLAY_LIMIT:
                return str(FAIL_DISPLAY_LIMIT) + '+'
            if fails % steps == 0:
                return str(fails)
            return ''
        chart.set_axis_labels(pgc.Axis.BOTTOM, map(get_label, range(max_fails + 1)))
        chart.fill_solid("bg", "65432100")
        return chart.get_url() + '&chbh=r,3'

    @staticmethod
    def refresh(problem, user):
        # TODO: 언젠가.. 최적화한다. -_-

        # PUBLISHED 가 아니면 Solver 인스턴스는 존재하지 않는다.
        if problem.state != Problem.PUBLISHED:
            return

        # Solver 인스턴스를 찾음. 없으면 만듬.
        instance = get_or_none(Solver, problem=problem, user=user)
        if not instance:
            instance = Solver(problem=problem, user=user)
            instance.save()
        # 이 사람의 서브미션 목록을 찾는다
        submissions = Submission.objects.filter(problem=problem,
                                                is_public=True,
                                                user=user).order_by("id")
        accepted = submissions.filter(state=Submission.ACCEPTED)

        # 풀었나? 못 풀었나?
        prev_solved = instance.solved
        if accepted.count() == 0:
            instance.solved = False
            instance.incorrect_tries = submissions.count()
            instance.fastest_submission = instance.shortest_submission = None
        else:
            instance.solved = True
            first = accepted[0]
            instance.when = first.submitted_on
            incorrect = submissions.filter(id__lt=first.id)
            instance.incorrect_tries = incorrect.count()
            instance.fastest_submission = accepted.order_by("time")[0]
            instance.shortest_submission = accepted.order_by("length")[0]
        instance.save()
        if instance.solved != prev_solved:
            # 유저 프로필에 푼 문제 수 업데이트
            profile = user.get_profile()
            profile.solved_problems = Solver.objects.filter(user=user,
                                                            solved=True).count()
            profile.save()

            # 처음으로 풀었을 경우 알림을 보낸다
            id = "solved-%d-%d" % (problem.id, user.id)
            if instance.solved:
                # 풀었다!
                publish(id, "solved", "judge",
                        target=problem,
                        actor=user,
                        timestamp=instance.fastest_submission.submitted_on,
                        verb=u"%d번의 시도만에 문제 {target}를 해결했습니다." %
                        (instance.incorrect_tries + 1))
            else:
                # 리저지 등 관계로 풀었던 문제를 못푼게 됨.
                depublish(id)

            # TODO: 가장 빠른 솔루션, 가장 짧은 솔루션이 등장했을 경우
            # newsfeed entry를 보낸다
        return instance

# SIGNAL HANDLERS
def saved_problem(sender, **kwargs):
    instance = kwargs["instance"]
    if instance.state == Problem.PUBLISHED:
        id = "new-problem-%d" % instance.id
        if not has_activity(key=id):
            publish(id, "newproblem", "judge",
                    actor=instance.user,
                    action_object=instance,
                    verb=u"온라인 저지에 새 문제 {action_object}를 "
                         u"공개했습니다.")
        else:
            activity = get_activity(key=id)
            activity.actor = instance.user
            activity.save()
    assign_perm('judge.edit_problem', instance.user, instance) # make life easier..

def saved_submission(sender, **kwargs):
    submission = kwargs["instance"]
    created = kwargs["created"]
    if created:
        problem = submission.problem
        problem.submissions_count = Submission.objects.filter(problem=problem,
                                                              is_public=True).count()
        problem.save()
    if submission.state in [Submission.RECEIVED,
                            Submission.REJUDGE_REQUESTED]:
        import tasks
        tasks.judge_submission.delay(submission)

    if submission.state in Submission.JUDGED:
        if not submission.is_public: return
        profile = submission.user.get_profile()
        submissions = Submission.objects.filter(user=submission.user,
                                                is_public=True)

        problem = submission.problem
        problem.accepted_count = Submission.objects.filter(problem=problem,
                                                           is_public=True,
                                                           state=Submission.ACCEPTED).count()
        problem.save()

        profile.submissions = submissions.count()
        profile.accepted = submissions.filter(state=Submission.ACCEPTED).count()
        profile.save()

        Solver.refresh(submission.problem, submission.user)

post_save.connect(saved_problem, sender=Problem,
                 dispatch_uid="saved_problem")
post_save.connect(saved_submission, sender=Submission,
                  dispatch_uid="saved_submission")

########NEW FILE########
__FILENAME__ = monitor
#!/usr/bin/python
import subprocess
import argparse
import resource
import signal

def get_parser():
    parser = argparse.ArgumentParser()
    parser.add_argument("-i", "--input", default=None)
    parser.add_argument("-e", "--error", default=None)
    parser.add_argument("-o", "--output", default=None)
    parser.add_argument("-t", "--time", default=None, type=int)
    parser.add_argument("-m", "--memory", default=None)
    parser.add_argument("-p", "--processes", default=None, type=int)
    parser.add_argument("command")
    return parser

def parse_memory(mem):
    suffixes = {"K": 2**10, "M": 2**20, "G": 2**30,
                "KB": 2**10, "MB": 2**20, "GB": 2**30}
    for suf in suffixes:
        if mem.endswith(suf):
            return int(mem[:-len(suf)]) * suffixes[suf]
    return int(mem)

def get_resources_used():
    usage = resource.getrusage(resource.RUSAGE_CHILDREN)
    return (usage.ru_utime + usage.ru_stime, usage.ru_maxrss)

def handle_sigkill(args):
    time_used, _ = get_resources_used()
    if time_used >= args.time:
        print 'TLE (At monitor: time used %.4lf limit %d' % (time_used, args.time)
    else:
        print ("RTE (SIGKILL: program was forcefully killed, probably "
               "memory limit exceeded)")

def handle_signal(sgn, args):
    if sgn == signal.SIGABRT:
        print "RTE (SIGABRT: program aborted, probably assertion fail)"
    elif sgn == signal.SIGFPE:
        print "RTE (SIGFPE: floating point error, probably divide by zero)"
    elif sgn == signal.SIGSEGV:
        print ("RTE (SIGSEGV: segmentation fault, probably incorrect memory "
               "access)")
    elif sgn == signal.SIGKILL:
        handle_sigkill(args)
    else:
        name = str(sgn)
        for entry in dir(signal):
            if entry.startswith("SIG"):
                if getattr(signal, entry) == sgn:
                    name = entry
                    break
        print "RTE (Unknown signal %s)" % name

def main():
    args = get_parser().parse_args()
    kwargs = {}
    if args.input: kwargs["stdin"] = open(args.input, "r")
    if args.error: kwargs["stderr"] = open(args.error, "w")
    if args.output: kwargs["stdout"] = open(args.output, "w")

    if args.time:
        resource.setrlimit(resource.RLIMIT_CPU, (args.time + 1, args.time + 1))

    if args.memory:
        parsed = parse_memory(args.memory)
        resource.setrlimit(resource.RLIMIT_RSS, (parsed, parsed))

    if args.processes:
        resource.setrlimit(resource.RLIMIT_NPROC,
                           (args.processes, args.processes))

    try:
        process = subprocess.Popen(args.command.split(), **kwargs)
        returncode = process.wait()
    except Exception as e:
        print "RTE (popen failed, contact admin. exception: %s)" % str(e)
        return
    if returncode > 0:
        print "RTE (nonzero return code)"
        return
    if returncode < 0:
        handle_signal(-returncode, args)
        return
    print "OK %.4lf %d" % get_resources_used()

if __name__ == "__main__":
    main()

########NEW FILE########
__FILENAME__ = sandbox
#!/usr/bin/python
# -*- coding: utf-8 -*-

""" This is a stripped-down version of Arkose:
    https://launchpad.net/arkose
    """

import os
import pwd
import tempfile
import shutil
import signal
import subprocess
import time
import logging
import getpass
import codecs
from os.path import expanduser, exists, split, join, abspath, dirname

def makedir(path):
    path = expanduser(path)
    if not exists(path):
        print 'RUN:', 'mkdir %s' % path
        os.makedirs(path)
    return path

class TimeOutException(Exception):
    pass

def execute(command, redirect=True, time_limit=None, kill_command=[]):
    """ time_limit must be in seconds """
    assert isinstance(command, list)
    kwargs = {"close_fds": True}
    if redirect:
        kwargs["stdout"] = kwargs["stderr"] = subprocess.PIPE
    print "RUN:", ' '.join(command)
    popen = subprocess.Popen(command, **kwargs)
    if not time_limit:
        wait = popen.wait()
    else:
        start = time.time()
        # 실제 수행하는 데는 4초를 더 준다.
        while time.time() < start + time_limit + 4 and popen.poll() is None:
            time.sleep(0.1)
        wait = popen.poll()
        if wait is None:
            if kill_command:
                subprocess.call(kill_command)
                popen.wait()
            else:
                popen.kill()
            raise TimeOutException
    ret = {"returncode": wait}
    if redirect:
        ret["stdout"] = popen.stdout.read()
        ret["stderr"] = popen.stderr.read()
    return ret

def get_sandbox(memory_limit):
    assert 1024 <= memory_limit <= 1024*1024*2, "memory_limit should be in kilobytes"
    from django.conf import settings
    SETTINGS = settings.JUDGE_SETTINGS
    return Sandbox(SETTINGS["USER"], SETTINGS["FILESYSTEMSIZE"], memory_limit)

# TODO: 모든 용량 기준 킬로바이트로 통일
class Sandbox(object):
    def __init__(self, user, fs_size=65536, memory_limit=65536, home_type="bind"):
        self.am_i_root = os.geteuid() == 0
        if not self.am_i_root:
            logging.warning("Sandbox not running as root: all sandboxing "
                            "functionalities are unavailable.")
            print ("Sandbox not running as root: all sandboxing "
                            "functionalities are unavailable.")
            user = getpass.getuser()
        self.user = pwd.getpwnam(user)
        self.mounts = []
        self.isolate_filesystem(fs_size, home_type)
        self.generate_config(memory_limit)

    def generate_config(self, memory_limit):
        self.memory_limit = memory_limit
        self.config = join(self.root, "config")
        # 실제 디바이스에는 10MB 를 더 준다
        f = open(self.config, "w")
        f.write("""
lxc.utsname = %s
lxc.tty = 4
lxc.pts = 1024
lxc.rootfs = %s

## /dev filtering
lxc.cgroup.devices.deny = a
# /dev/null and zero
lxc.cgroup.devices.allow = c 1:3 rwm
lxc.cgroup.devices.allow = c 1:5 rwm
# consoles
lxc.cgroup.devices.allow = c 5:1 rwm
lxc.cgroup.devices.allow = c 5:0 rwm
lxc.cgroup.devices.allow = c 4:0 rwm
lxc.cgroup.devices.allow = c 4:1 rwm
# /dev/{,u}random
lxc.cgroup.devices.allow = c 1:9 rwm
lxc.cgroup.devices.allow = c 1:8 rwm
lxc.cgroup.devices.allow = c 136:* rwm
lxc.cgroup.devices.allow = c 5:2 rwm
# rtc
lxc.cgroup.devices.allow = c 254:0 rwm
## Networking
lxc.network.type = empty
## Limit max memory
lxc.cgroup.memory.limit_in_bytes = %dK
lxc.cgroup.memory.memsw.limit_in_bytes = %dK
                """ % (self.name, self.root_mount, memory_limit + 10240,
                       memory_limit + 10240))
        f.close()


    def mount(self, source, destination, fstype, options=None):
        if not self.am_i_root: return
        cmd = ["mount", "-t", fstype, source, destination]
        if options:
            cmd += ["-o", options]
        execute(cmd)
        self.mounts.append(destination)

    def isolate_filesystem(self, fs_size, home_type):
        self.root = tempfile.mkdtemp(dir=makedir("~/.sandbox"))
        print "sandbox root", self.root
        os.chmod(self.root, 0o755)

        self.name = "sandbox-%s" % split(self.root)[1]

        # 워킹 디렉토리: 모든 디렉토리 마운트를 포함. COW 와 restrict
        # 데이터는 워킹 디렉토리의 쿼터에 포함된다.
        self.workdir = makedir(join(self.root, "workdir"))
        self.mount("none", self.workdir, "tmpfs", "size=%d" % (fs_size << 20))

        # LXC 용 cgroup 생성
        self.cgroup = makedir(join(self.workdir, "cgroup"))
        #self.cgroup = '/sys/fs/cgroup'
        self.mount("cgroup", self.cgroup, "cgroup")

        # 루트 디렉토리를 copy-on-write 로 마운트한다.
        # root_mount 위치에 마운트하되, 여기에서 고친 내역은 root_cow
        # 위치에 저장된다.
        self.root_mount = makedir(join(self.workdir, "root-mount"))
        self.root_cow = makedir(join(self.workdir, "root-cow"))
        self.mount("none", self.root_mount, "aufs", "br=%s:/" % self.root_cow)

        # 일부 프로그램들은 /proc 이 없으면 제대로 동작하지 않는다 (Sun JVM 등)
        self.mount("/proc", join(self.root_mount, "proc"), "none", "bind")

        # 빈 디렉토리 user-home 을 만들고, 마운트된 cow 루트 내의 홈디렉토리를
        # 이걸로 덮어씌운다.
        home_path = self.user.pw_dir.lstrip("/")
        self.new_home = makedir(join(self.workdir, "user-home"))
        self.home_in_mounted = makedir(join(self.root_mount, home_path))
        self.new_home_cow = expanduser(join(self.workdir, "user-home-cow"))
        self.mount_home(home_type)

    def _umount(self, mounted):
        if not self.am_i_root: return
        if mounted not in self.mounts: return
        execute(["umount", mounted])
        self.mounts.remove(mounted)

    def mount_home(self, home_type):
        self._umount(self.home_in_mounted)

        if home_type == "bind":
            self.mount(self.new_home, self.home_in_mounted, "none", "bind")
        else:
            if exists(self.new_home_cow):
                shutil.rmtree(self.new_home_cow)
            makedir(self.new_home_cow)
            self.mount("none", self.home_in_mounted, "aufs", "br=%s:%s" %
                       (self.new_home_cow, self.new_home))

        os.chown(self.home_in_mounted, self.user.pw_uid, self.user.pw_gid)
        os.chmod(self.home_in_mounted, 0o700)

    def teardown(self):
        for destination in list(reversed(self.mounts)):
            self._umount(destination)

        #if os.path.exists(self.root): shutil.rmtree(self.root)

    def get_file_path(self, in_home):
        return join(self.home_in_mounted, in_home)

    def put_file(self, source, destination, permission=None):
        "Put a file into user's home directory"
        target = join(self.home_in_mounted, destination)
        shutil.copy(source, target)
        os.chown(target, self.user.pw_uid, self.user.pw_gid)
        if permission:
            os.chmod(target, permission)

    def write_file(self, text, destination, permission=None):
        "Create a file in user's home directory with given contents"
        target = join(self.home_in_mounted, destination)
        open(target, "w").write(text.encode("utf-8"))
        os.chown(target, self.user.pw_uid, self.user.pw_gid)
        if permission:
            os.chmod(target, permission)

    def read_file(self, file):
        "Reads a file from user's home directory"
        return codecs.open(join(self.home_in_mounted, file), encoding="utf-8").read()

    def create_entrypoint(self, command, before=[], after=[]):
        entrypoint = join(self.home_in_mounted, "entrypoint.sh")
        #print "ENTRYPOINT", command
        content = "\n".join([
            "#!/bin/sh",
            "cd `dirname $0`",
            "rm $0",
            "reset -I 2> /dev/null" if self.am_i_root else ""] +
            before +
            [command] +
            after + [
            "RET=$?",
            "pkill -P 1 2> /dev/null" if self.am_i_root else "",
            "exit $RET"])
        fp = open(entrypoint, "w")
        fp.write(content)
        fp.close()
        os.chown(entrypoint, self.user.pw_uid, self.user.pw_gid)

    def run_interactive(self, command):
        "Runs an interactive command in the sandbox"
        # 에.. 이건 왜켜냐
        self.create_entrypoint(command)
        return self._run(False)

    def run(self, command, stdin=None, stdout=None, stderr=None,
            time_limit=None, override_memory_limit=None, before=[], after=[]):
        # 모니터를 샌드박스 안에 집어넣는다
        self.put_file(os.path.join(os.path.dirname(__file__), "monitor.py"),
                       "monitor.py")
        cmd = ["python", "monitor.py"]
        if stdin: cmd += ["-i", stdin]
        if stdout: cmd += ["-o", stdout]
        if stderr: cmd += ["-e", stderr]
        cmd += ["-m", str(self.memory_limit * 1024)]
        if time_limit != None:
            cmd += ["-t", str(int(time_limit + 1.1))]
        cmd.append('"%s"' % command)

        self.create_entrypoint(" ".join(cmd), before, after)
        try:
            result = self._run(True, time_limit)
            if (result["returncode"] != 0 or
                    result["stderr"].strip() or
                    not result["stdout"].strip() or
                    result["stdout"].split()[0] not in ["RTE", "MLE", "OK", "TLE"]):
                raise Exception("Unexpected monitor result:\n" + str(result) + "\n" +
				result["stdout"].split()[0])
        except TimeOutException:
            return "TLE"
        #print "RESULT", result
        toks = result["stdout"].split()
        if toks[0] == "OK":
            time_used, memory_used = map(float, toks[1:3])
            if time_limit is not None and time_used >= time_limit:
                return (u"TLE (Outside sandbox; time used %d limit %d)" %
                        (time_used, time_limit))
            effective_memory_limit = override_memory_limit or self.memory_limit
            if memory_used >= effective_memory_limit:
                return (u"MLE (Outside sandbox: memory used %d limit %d)" %
                        (memory_used, effective_memory_limit))

        return result["stdout"]

    def _run(self, redirect, time_limit=None):
        signal.signal(signal.SIGTTOU, signal.SIG_IGN)
        signal.signal(signal.SIGINT, signal.SIG_IGN)
        current_path = abspath(dirname(__file__))
        if self.am_i_root:
            return execute(["lxc-start",
                            "-n", self.name,
                            "-f", self.config,
                            "-o", join(current_path, "lxc.log"),
                            "-l", "INFO",
                            "su", self.user.pw_name, "-c", "sh", join(self.user.pw_dir, "entrypoint.sh")],
                           redirect=redirect,
                           time_limit=time_limit,
                           kill_command=["lxc-stop",
                                         "-n", self.name])
        return execute(["sh", join(self.home_in_mounted, "entrypoint.sh")],
                       redirect=redirect,
                       time_limit=time_limit)


def main():
    def print_result(x):
        print "RETURN CODE: %d" % x["returncode"]
        for key in x.keys():
            if x[key]:
                print key, "============"
                print x[key]

    try:
        sandbox = Sandbox("runner", home_type="bind")
        sandbox.run_interactive("bash")
        """
        sandbox.mount_home("cow")
        sandbox.run_interactive("bash")
        sandbox.mount_home("cow")
        sandbox.run_interactive("bash")
        sandbox = Sandbox("runner", memory_limit=65536, home_type="bind")
        import sys
        for file in sys.argv[1:]:
            sandbox.put_file(file, os.path.basename(file))
        sandbox.put_file("dp.cpp", "dp.cpp", 0o700)
        sandbox.put_file("inp", "inp")
        print sandbox.run("g++ -O3 dp.cpp -o dp", stdout=".compile.stdout",
                                 stderr=".compile.stderr")
        print sandbox.run("./dp", "inp", ".stdout", ".stderr")
        """
    finally:
        sandbox.teardown()
        pass

if __name__ == "__main__":
    main()

########NEW FILE########
__FILENAME__ = search_indexes
from haystack import indexes
from models import Problem

class ProblemIndex(indexes.SearchIndex, indexes.Indexable):
    text = indexes.EdgeNgramField(document=True, use_template=True)
    date = indexes.DateTimeField(model_attr='updated_on')

    def get_model(self):
        return Problem

    def index_queryset(self, using=None):
        return self.get_model().objects.filter(state=Problem.PUBLISHED)

    def get_updated_field(self):
        return None

########NEW FILE########
__FILENAME__ = tasks
# -*- coding: utf-8 -*-
from django.conf import settings
from celery.decorators import task
from celery.utils.log import get_task_logger
from models import Submission, Attachment
import hashlib
import urllib
import shutil
import os
import zipfile
import glob
import sandbox
import languages
import StringIO
import traceback
import differs

# TODO: get rid of this T_T
SPECIAL_JUDGE_WHITELISTED = ['TRAPCARD', 'WORDCHAIN', 'MEETINGROOM', 'RESTORE',
                             'PACKING']

def print_stack_trace():
    io = StringIO.StringIO()
    traceback.print_exc(file=io)
    io.seek(0)
    return io.read()

@task()
def add(x, y):
    return x + y
    
logger = get_task_logger(__name__)

@task()
def judge_submission(submission):

    def copy(source, dest):
        while True:
            chunk = source.read(1024*1024)
            if not chunk: break
            dest.write(chunk)

    def download(attachment, destination):
        # TODO: add MD5 verification to downloaded files
        logger.info("downloading %s ..", attachment.file.url)
        copy(urllib.urlopen(attachment.file.url), open(destination, "wb"))

    def unzip_and_sanitize(archive, data_dir):
        logger.info("unzipping %s ..", archive)
        file = zipfile.ZipFile(archive, "r")
        for name in file.namelist():
            dest = os.path.join(data_dir, os.path.basename(name))
            logger.info("generating %s ..", dest)
            copy(file.open(name), open(dest, "wb"))
            sanitize_data(dest)

    def download_data(problem):
        attachments = Attachment.objects.filter(problem=problem)
        """
            There are three cases: created, modified, removed.
            I am too lazy to handle all these cases optimally,
            so I'm going to evaluate the hash of all those paths,
            and compare them to re-download all or do nothing.
        """
        entries_to_download = []
        for entry in attachments:
            basename = os.path.basename(entry.file.name)
            ext = basename.split(".")[-1].lower()
            if basename != 'judge.py' and ext not in ["in", "out", "zip"]: continue
            entries_to_download.append((entry, basename))

        joined_entries = "@".join(map(lambda x: x[0].file.name, entries_to_download))
        md5 = hashlib.md5(joined_entries).hexdigest()
        pathhash_name = md5 + '.pathhash'
        pathhash_path = os.path.join(data_dir, pathhash_name)
        if os.path.exists(data_dir) and os.path.exists(pathhash_name):
            return

        if os.path.exists(data_dir):
            shutil.rmtree(data_dir)
        os.makedirs(data_dir)

        for pair in entries_to_download:
            entry, basename = pair
            ext = basename.split(".")[-1].lower()
            destination = os.path.join(data_dir, basename)
            download(entry, destination)
            if ext == "zip":
                unzip_and_sanitize(destination, data_dir)
            else:
                sanitize_data(destination)
        
        open(pathhash_path, 'w').close()

    def sanitize_data(filename):
        # line endings: DOS -> UNIX
        file = open(filename, 'r+b')
        body = file.read().replace('\r\n', '\n')
        file.seek(0)
        file.write(body)
        file.truncate()
        file.close()

    def get_ioset():
        io = {}
        for file in glob.glob(os.path.join(data_dir, "*")):
            if file.endswith(".in") or file.endswith(".out"):
                tokens = file.split(".")
                basename = ".".join(tokens[:-1])
                if basename not in io:
                    io[basename] = {}
                io[basename][tokens[-1]] = file
        if not io:
            raise Exception("Judge I/O data not found.")
        for key, value in io.iteritems():
            if len(value) != 2:
                raise Exception("Non-matching pairs in judge I/O data. See: %s"
                                % str(io))
        return io

    sandbox_env = None
    try:
        logger.info("Checking language module..")
        # 언어별 채점 모듈 존재 여부부터 확인하기
        if submission.language not in languages.modules:
            raise Exception("Can't find judge module for language %s" %
                            submission.language)
        language_module = languages.modules[submission.language]

        problem = submission.problem

        # 결과 differ 모듈 확인
        if problem.judge_module not in differs.modules:
            raise Exception("Can't find diff module %s" % problem.judge_module)
        differ_module = differs.modules[problem.judge_module]
        assert (problem.judge_module != 'special_judge' or 
                problem.slug in SPECIAL_JUDGE_WHITELISTED)
        


        # 문제 채점 데이터를 다운받고 채점 준비
        logger.info("Downloading judge i/o set..")
        data_dir = os.path.join(settings.JUDGE_SETTINGS["WORKDIR"],
                                "data/%d-%s" % (problem.id, problem.slug))
        download_data(submission.problem)
        ioset = get_ioset()

        logger.info("Initiating sandbox..")
        # 샌드박스 생성
        # 컴파일할 때 메모리가 더 필요할 수도 있으니, 샌드박스에 메모리는
        # 문제 제한보다 더 많이 준다. MINMEMORYSIZE 만큼은 항상 주도록 한다.
        sandbox_memory = max(settings.JUDGE_SETTINGS['MINMEMORYSIZE'],
                             problem.last_revision.memory_limit)
        sandbox_env = sandbox.get_sandbox(sandbox_memory)

        logger.info("Compiling..")
        # 컴파일
        submission.state = Submission.COMPILING
        submission.save()
        result = language_module.setup(sandbox_env, submission.source)
        if result["status"] != "ok":
            submission.state = Submission.COMPILE_ERROR
            submission.message = result["message"]
            return

        logger.info("Freezing sandbox..")
        # set sandbox in copy-on-write mode: will run
        sandbox_env.mount_home("cow")

        # let's run now
        logger.info("Running..")
        submission.state = Submission.RUNNING
        submission.save()
        total_time, max_memory = 0, 64
        for io in ioset.itervalues():
            inp = os.path.basename(io["in"])
            sandbox_env.put_file(io["in"], inp)
            result = language_module.run(sandbox_env, inp,
                                         problem.last_revision.time_limit / 1000.,
                                         problem.last_revision.memory_limit)

            # RTE 혹은 MLE?
            if result["status"] != "ok":
                if result["verdict"] == "TLE":
                    submission.state = Submission.TIME_LIMIT_EXCEEDED
                elif result["verdict"] == "MLE":
                    submission.state = Submission.RUNTIME_ERROR
                    submission.message = u"메모리 제한 초과"
                elif result["verdict"] == "RTE":
                    submission.state = Submission.RUNTIME_ERROR
                    submission.message = result["message"]
                return

            # 전체 시간이 시간 초과면 곧장 TLE
            # TODO: 채점 데이터별 시간 제한 지원
            total_time += float(result["time"])
            max_memory = max(max_memory, int(result["memory"]))
            if total_time > problem.last_revision.time_limit / 1000.:
                submission.state = Submission.TIME_LIMIT_EXCEEDED
                return

            # differ 에 보내자
            output = sandbox_env.get_file_path(result["output"])
            if not differ_module.judge(data_dir, io["in"], output, io["out"]):
                submission.time = int(total_time * 1000)
                submission.memory = max_memory
                submission.state = Submission.WRONG_ANSWER
                return

        submission.time = int(total_time * 1000)
        submission.memory = max_memory
        submission.state = Submission.ACCEPTED

    except:
        submission.state = Submission.CANT_BE_JUDGED
        try:
            submission.message = u"\n".join([
                u"채점 중 예외가 발생했습니다.",
                u"스택 트레이스:",
                print_stack_trace()])
        except Exception as e:
            submission.message = u"오류 인코딩 중 에러: %s" % e.message
    finally:
        submission.save()
        if sandbox_env:
            sandbox_env.teardown()



########NEW FILE########
__FILENAME__ = judge_tags
# -*- coding: utf-8 -*-
from django import template
from ..models import Submission
from base.models import UserProfile

register = template.Library()

class HasSolvedNode(template.Node):
    def __init__(self, problem, user, result):
        self.problem = template.Variable(problem)
        self.user = template.Variable(user)
        self.result = result
    def render(self, context):
        problem = self.problem.resolve(context)
        user = self.user.resolve(context)
        ret = (user.is_authenticated() and
               Submission.objects.filter(problem=problem, user=user,
                                         state=Submission.ACCEPTED).count() > 0)
        context[self.result] = ret
        return ""

@register.tag
def get_has_solved(parser, token):
    toks = token.split_contents()
    problem, by, user, as_, solved = toks[1:]
    return HasSolvedNode(problem, user, solved)

@register.filter
def print_length(length):
    if length < 1024: return "%dB" % length
    return "%.1lfKB" % (length / 1024.)

@register.filter
def user_rank(profile):
    qs = UserProfile.objects.filter(solved_problems__gt=profile.solved_problems)
    return str(qs.count() + 1)


########NEW FILE########
__FILENAME__ = tests
"""
This file demonstrates writing tests using the unittest module. These will pass
when you run "manage.py test".

Replace this with more appropriate tests for your application.
"""

from django.test import TestCase


class SimpleTest(TestCase):
    def test_basic_addition(self):
        """
        Tests that 1 + 1 always equals 2.
        """
        self.assertEqual(1 + 1, 2)

########NEW FILE########
__FILENAME__ = urls
# -*- coding: utf-8 -*-
from django.conf.urls.defaults import patterns, url
import views

urlpatterns = patterns(
    'judge.views',
    url(r'^$', views.index,
        name='judge-index'),
    url(r'^ranking/$', views.ranking, name='judge-ranking'),
    url(r'^ranking/(?P<page>.+)/$', views.ranking, name='judge-ranking'),

    url(r'^problem/read/(?P<slug>.+)$', views.problem.read,
        name='judge-problem-read'),
    url(r'^problem/latexify/(?P<slug>.+)$', views.problem.latexify,
        name='judge-problem-latexify'),

    url(r'^problem/mine/$', views.problem.my_problems, name='judge-problem-mine'),
    url(r'^problem/mine/(?P<page>.+)/$', views.problem.my_problems, name='judge-problem-mine'),

    url(r'^problem/new/$', views.problem.new, name='judge-problem-new'),
    url(r'^problem/delete/(?P<id>.+)/$', views.problem.delete, name='judge-problem-delete'),

    url(r'^problem/list/$', views.problem.list, name='judge-problem-list'),
    url(r'^problem/list/(?P<page>.+)$', views.problem.list, name='judge-problem-list'),

    url(r'^problem/stat/(?P<slug>[^/]+)/$', views.problem.stat,
        name='judge-problem-stat'),
    url(r'^problem/stat/(?P<slug>[^/]+)/(?P<page>.+)/$', views.problem.stat, name='judge-problem-stat'),

    url(r'^problem/attachment/list/(?P<id>.+)$', views.problem.list_attachments,
        name='judge-problem-list-attachments'),
    url(r'^problem/attachment/delete/(?P<id>.*)$', views.problem.delete_attachment,
        name='judge-problem-delete-attachment'),

    url(r'^problem/attachment/add/(?P<id>.*)$', views.problem.add_attachment,
        name='judge-problem-add-attachment'),

    url(r'^problem/submit/(?P<slug>.+)$', views.problem.submit,
        name='judge-problem-submit'),

    url(r'^problem/edit/(?P<id>.+)$', views.problem.edit,
        name='judge-problem-edit'),
    url(r'^problem/rejudge/(?P<id>.+)$', views.problem.rejudge,
        name='judge-problem-rejudge'),
    url(r'^problem/history/(?P<slug>.+)$', views.problem.history,
        name='judge-problem-history'),
    url(r'^problem/diff$', views.problem.diff,
        name='judge-problem-diff-home'),
    url(r'^problem/diff/(?P<id1>[0-9]+)/(?P<id2>[0-9]+)$', views.problem.diff,
        name='judge-problem-diff'),
    url(r'^problem/old/(?P<id>[0-9]+)/(?P<slug>.+)$', views.problem.old,
        name='judge-problem-old'),
    url(r'^problem/revert/(?P<id>[0-9]+)/(?P<slug>.+)$', views.problem.revert,
        name='judge-problem-revert'),

    url(r'^submission/detail/(?P<id>.+)$', views.submission.details,
        name='judge-submission-details'),
    url(r'^submission/recent/$', views.submission.recent,
        name='judge-submission-recent'),
    url(r'^submission/recent/(?P<page>.+)$', views.submission.recent,
        name='judge-submission-recent'),
    url(r'^submission/rejudge/(?P<id>.+)$', views.submission.rejudge,
        name='judge-submission-rejudge'),

)


########NEW FILE########
__FILENAME__ = utils
# -*- coding: utf-8 -*-
from django.core.urlresolvers import reverse
from django.utils.html import escape
from models import Problem

def link_to_problem(slug, display):
    problem = Problem.objects.get(slug=slug)
    link = reverse("judge-problem-read", kwargs={"slug": slug})
    return u'<a class="problem" href="%s" title="%s">%s</a>' % (link, problem.name, escape(display or slug))

########NEW FILE########
__FILENAME__ = problem
# -*- coding: utf-8 -*-
from diff_match_patch import diff_match_patch
from django.shortcuts import render, get_object_or_404, redirect
from django.core.urlresolvers import reverse
from django.contrib.auth.decorators import login_required
from django.http import Http404, HttpResponse
from django.core.files.storage import DefaultStorage
from djangoutils import setup_paginator, get_or_none
from datetime import datetime
from django.contrib.auth.models import User
from django.db.models import Count
from guardian.core import ObjectPermissionChecker
from guardian.shortcuts import get_objects_for_user, get_users_with_perms, get_groups_with_perms
from base.decorators import authorization_required, admin_required
from newsfeed import publish
from ..models import Problem, Submission, Attachment, Solver, ProblemRevision
from ..forms import SubmitForm, AdminSubmitForm, ProblemEditForm, RestrictedProblemEditForm, ProblemRevisionEditForm
from rendertext import render_latex
import json
import os
import hashlib
import uuid
import urllib

@login_required
def new(request):
    new_problem = Problem(user=request.user, name=u"(새 문제)",
                          slug=str(uuid.uuid4()))
    new_problem.save()
    new_revision = ProblemRevision()
    new_revision.edit_summary = '문제 생성함.'
    new_revision.revision_for = new_problem
    new_revision.user = request.user
    new_revision.save()
    new_problem.slug = 'NEWPROB' + str(new_problem.id)
    new_problem.last_revision = new_revision
    new_problem.save()
    return redirect(reverse('judge-problem-edit',
                            kwargs={'id': new_problem.id}))

@login_required
def delete(request, id):
    problem = get_object_or_404(Problem, id=id)
    if not request.user.is_superuser and problem.user != request.user:
        raise Http404
    Solver.objects.filter(problem=problem).delete()
    Submission.objects.filter(problem=problem).delete()
    for attach in Attachment.objects.filter(problem=problem):
        attach.file.delete(False)
        attach.delete()
    del problem.tags
    problem.save()
    problem.delete()
    return redirect(reverse('judge-problem-mine'))

@login_required
def edit(request, id):
    problem = get_object_or_404(Problem, id=id)
    checker = ObjectPermissionChecker(request.user)
    if not checker.has_perm('edit_problem', problem) and problem.user != request.user:
        raise Http404
    problem_revision = problem.last_revision

    form_class = (ProblemEditForm if request.user.is_superuser else
                  RestrictedProblemEditForm)
    form = form_class(data=request.POST or None, instance=problem)
    if request.method == "POST":
        revision_form = ProblemRevisionEditForm(data=request.POST or None, instance=ProblemRevision())
        if form.is_valid() and revision_form.is_valid():
            form.save()
            new_revision = revision_form.save(problem, request.user, commit=False)
            if new_revision.different_from(problem_revision):
                revision_form.save(problem, request.user)
            return redirect(reverse("judge-problem-read",
                kwargs={"slug": form.cleaned_data["slug"]}));
    revision_form = ProblemRevisionEditForm(data=request.POST or None, instance=problem_revision)
    return render(request, "problem/edit.html", {"problem": problem,
        "form": form, "revision_form": revision_form, "editable": checker.has_perm("edit_problem", problem)})

@login_required
def rejudge(request, id):
    problem = get_object_or_404(Problem, id=id)
    checker = ObjectPermissionChecker(request.user)
    if not checker.has_perm('edit_problem', problem) and problem.user != request.user:
        raise Http404
    submissions = Submission.objects.filter(problem=problem)
    for submission in submissions:
        submission.rejudge()
    return redirect(reverse('judge-submission-recent') +
                    '?problem=' + problem.slug)

@login_required
def delete_attachment(request, id):
    attachment = get_object_or_404(Attachment, id=id)
    problem = attachment.problem
    checker = ObjectPermissionChecker(request.user)
    if not checker.has_perm('edit_problem', problem) and problem.user != request.user:
        raise Http404
    old_id = attachment.id
    old_filename = attachment.file.name
    attachment.file.delete(False)
    attachment.delete()

    # 해당 오브젝트에 대해 아무 퍼미션이나 있으면 처리됨. 문제의 경우 PUBLISHED 일 때는 이 권한을 사용하지 않아서 안전하다
    visible_users = get_users_with_perms(problem, with_group_users=False)
    visible_groups = get_groups_with_perms(problem)

    publish("problem-attachment-delete-%s" % datetime.now().strftime('%s.%f'),
            "problem",
            "problem-attachment",
            actor=request.user,
            target=problem,
            timestamp=datetime.now(),
            visible_users=visible_users,
            visible_groups=visible_groups,
            verb=u"문제 {target}에서 첨부파일 %s 을 삭제했습니다." % os.path.basename(old_filename))
    return HttpResponse("[]")

def md5file(file):
    md5 = hashlib.md5()
    for chunk in file.chunks():
        md5.update(chunk)
    return md5.hexdigest()

@login_required
def add_attachment(request, id):
    def go():
        problem = get_or_none(Problem, id=id)
        if not problem:
            return {"success": False,
                    "error": u"존재하지 않는 문제입니다."}
        checker = ObjectPermissionChecker(request.user)
        if not checker.has_perm('edit_problem', problem) and problem.user != request.user:
            return {"success": False,
                    "error": u"권한이 없습니다."}
        if request.method != "POST":
            return {"success": False,
                    "error": u"POST 접근하셔야 합니다."}
        file = request.FILES["file"]
        md5 = md5file(file)
        target_path = os.path.join("judge-attachments", md5, file.name)
        storage = DefaultStorage()
        storage.save(target_path, file)
        new_attachment = Attachment(problem=problem,
                                    file=target_path)
        new_attachment.save()

        # 해당 오브젝트에 대해 아무 퍼미션이나 있으면 처리됨. 문제의 경우 PUBLISHED 일 때는 이 권한을 사용하지 않아서 안전하다
        visible_users = get_users_with_perms(problem, with_group_users=False)
        visible_groups = get_groups_with_perms(problem)

        publish("problem-attachment-%s" % datetime.now().strftime('%s.%f'),
                "problem",
                "problem-attachment",
                actor=request.user,
                target=problem,
                timestamp=datetime.now(),
                visible_users=visible_users,
                visible_groups=visible_groups,
                verb=u"문제 {target}에 첨부파일 %s 을 추가했습니다." % file.name)
        return {"success": True}

    return HttpResponse(json.dumps(go()))


@login_required
def list_attachments(request, id):
    problem = get_object_or_404(Problem, id=id)
    checker = ObjectPermissionChecker(request.user)
    if not checker.has_perm('edit_problem', problem) and problem.user != request.user:
        raise Http404
    data = [[attachment.id,
             os.path.basename(attachment.file.name),
             attachment.file.size,
             attachment.file.url]
            for attachment in Attachment.objects.filter(problem=problem)]
    ret = {"iTotalRecords": len(data),
           "sEcho": request.GET.get("sEcho", ""),
           "iTotalDisplayRecords": len(data),
           "aaData": data}
    return HttpResponse(json.dumps(ret))

@login_required
@authorization_required
def my_problems(request, page=1):
    readable_problems = get_objects_for_user(request.user, 'read_problem', Problem)
    my_problems = Problem.objects.filter(user=request.user)
    problems = (readable_problems | my_problems).exclude(state=Problem.PUBLISHED)
    title = u'준비 중인 문제들'

    order_by = request.GET.get("order_by", 'slug')
    problems = problems.annotate(Count('solver'))
    if order_by.lstrip('-') in ('slug', 'name', 'state'):
        problems = problems.order_by(order_by)
    else:
        assert order_by.endswith('user')
        problems = problems.order_by(order_by + '__username')

    return render(request, 'problem/mine.html',
                  {'title': title,
                   'pagination': setup_paginator(problems, page,
                                                 'judge-problem-mine', {})})

def list(request, page=1):
    use_filter = True
    filters = {}
    title_options = []
    problems = Problem.objects.filter(state=Problem.PUBLISHED)
    if request.GET.get("tag"):
        tag = filters["tag"] = request.GET["tag"]
        problems = Problem.tagged.with_all([tag])
        title_options.append(tag)
    if request.GET.get("source"):
        source = filters["source"] = request.GET["source"]
        problems = problems.filter(source=source)
        title_options.append(source)
    if request.GET.get("author"):
        filters["author"] = request.GET["author"]
        author = get_object_or_404(User, username=filters["author"])
        problems = problems.filter(user=author)
        title_options.append(author.username)
    if title_options:
        title = u"문제 목록: " + u", ".join(title_options)
    else:
        title = u"문제 목록 보기"

    if request.GET.get('user_tried'):
        use_filter = False
        id = request.GET.get('user_tried')
        user = get_object_or_404(User, id=id)
        verdict = request.GET.get('verdict')
        if verdict == 'solved':
            title = user.username + u': 해결한 문제들'
            problems = problems.filter(solver__user=user, solver__solved=True)
        elif verdict == 'failed':
            title = user.username + u': 실패한 문제들'
            problems = problems.filter(solver__user=user, solver__solved=False)
        elif verdict == 'notyet':
            title = user.username + u': 시도하지 않은 문제들'
            problems = problems.exclude(solver__user=user)
        else:
            title = user.username + u': 시도한 문제들'
            problems = problems.filter(solver__user=user)

    order_by = request.GET.get('order_by', 'slug')
    if order_by.endswith('ratio'):
        ratio_def = ('cast("judge_problem"."accepted_count" as float) / '
                     'greatest(1, "judge_problem"."submissions_count")')
        problems = problems.extra(select={'ratio': ratio_def})
    if order_by.endswith('user'):
        problems = problems.order_by(order_by + '__username')
    else:
        problems = problems.order_by(order_by)

    # options = {}
    # TODO: 카테고리별 문제 보기
    # TODO: 난이도 순으로 정렬하기
    sources = sorted([entry["source"] for entry in
                      Problem.objects.values("source").distinct()])
    authors = sorted([User.objects.get(id=entry["user"]).username
                      for entry in Problem.objects.values("user").distinct()])
    tags = sorted([tag.name for tag in Problem.tags.all()])

    get_params = '&'.join(k + '=' + v for k, v in request.GET.items())
    return render(request, "problem/list.html",
                  {"title": title,
                   "sources": sources,
                   "authors": authors,
                   "tags": tags,
                   "use_filter": use_filter,
                   "filters": filters,
                   "get_params": get_params,
                   "pagination": setup_paginator(problems, page,
                                                 "judge-problem-list",
                                                 {},
                                                 request.GET)})

def stat(request, slug, page=1):
    problem = get_object_or_404(Problem, slug=slug)
    checker = ObjectPermissionChecker(request.user)
    if (problem.state != Problem.PUBLISHED and
        not checker.has_perm('read_problem', problem) and
        problem.user != request.user):
        raise Http404
    submissions = Submission.objects.filter(problem=problem)
    verdict_chart = Submission.get_verdict_distribution_graph(submissions)
    incorrect_tries_chart = Solver.get_incorrect_tries_chart(problem)

    solvers = Solver.objects.filter(problem=problem, solved=True)
    order_by = request.GET.get('order_by', 'shortest')
    if order_by.endswith('fastest'):
        solvers = solvers.order_by(order_by + '_submission__time')
    elif order_by.endswith('shortest'):
        solvers = solvers.order_by(order_by + '_submission__length')
    else:
        solvers = solvers.order_by(order_by)
    pagination = setup_paginator(solvers, page, 'judge-problem-stat',
                                 {'slug': slug}, request.GET)
    title = problem.slug + u': 해결한 사람들'
    return render(request, "problem/stat.html",
                  {'title': title,
                   'problem': problem,
                   'editable': checker.has_perm('edit_problem', problem),
                   'verdict_chart': verdict_chart,
                   'incorrects_chart': incorrect_tries_chart,
                   'pagination': pagination,
                  })

def read(request, slug):
    problem = get_object_or_404(Problem, slug=slug)
    checker = ObjectPermissionChecker(request.user)
    if (problem.state != Problem.PUBLISHED and
        not checker.has_perm('read_problem', problem) and
        problem.user != request.user):
        raise Http404
    return render(request, "problem/read.html", {"problem": problem, "revision": problem.last_revision, "editable": checker.has_perm('edit_problem', problem)})

@login_required
def latexify(request, slug):
    problem = get_object_or_404(Problem, slug=slug)
    checker = ObjectPermissionChecker(request.user)
    if (not checker.has_perm('read_problem', problem) and
        problem.user != request.user):
        raise Http404
    response = render(request, "problem/latexify.tex", {"problem": problem, "revision": problem.last_revision})
    response['Content-Type'] = 'text/plain; charset=UTF-8'
    return response

@login_required
def history(request, slug):
    problem = get_object_or_404(Problem, slug=slug)
    checker = ObjectPermissionChecker(request.user)
    if (not checker.has_perm('read_problem', problem) and
        problem.user != request.user):
        raise Http404
    revision_set = ProblemRevision.objects.filter(revision_for=problem).order_by("-id")
    ids = [rev.id for rev in revision_set[:2]]
    revisions = revision_set.all()
    last, second_last = -1, -1
    if len(ids) >= 2:
        last, second_last = ids[0], ids[1]
    return render(request, "problem/history.html",
                  {"problem": problem,
                   "editable": checker.has_perm('edit_problem', problem),
                   "revisions": revisions,
                   "last_rev": last,
                   "second_last_rev": second_last})

@login_required
def old(request, id, slug):
    problem = get_object_or_404(Problem, slug=slug)
    checker = ObjectPermissionChecker(request.user)
    if (not checker.has_perm('read_problem', problem) and
        problem.user != request.user):
        raise Http404
    revision = get_object_or_404(ProblemRevision, id=id)
    return render(request, "problem/old.html",
                  {"problem": problem,
                   "editable": checker.has_perm('edit_problem', problem),
                   "revision": revision})

@login_required
def revert(request, id, slug):
    problem = get_object_or_404(Problem, slug=slug)
    checker = ObjectPermissionChecker(request.user)
    if (not checker.has_perm('edit_problem', problem) and
        problem.user != request.user):
        raise Http404
    revision = ProblemRevision.objects.get(id=id)
    old_id = revision.id
    revision.id = None
    revision_form = ProblemRevisionEditForm(data=None, instance=revision)
    revision_form.save(problem, request.user, 
                       summary=u"리비전 %s로 복구." % old_id)
    return redirect(reverse("judge-problem-read", kwargs={"slug": problem.slug}))

@login_required
def diff(request, id1, id2):
    rev1 = get_object_or_404(ProblemRevision, id=id1)
    rev2 = get_object_or_404(ProblemRevision, id=id2)
    problem = rev1.revision_for
    checker = ObjectPermissionChecker(request.user)
    if (not checker.has_perm('read_problem', problem) and
        problem.user != request.user):
        raise Http404

    dmp = diff_match_patch()
    def differ(text1, text2):
        return text1 != text2 and dmp.diff_main(text1, text2) or None

    return render(request, "problem/diff.html",
                  {"problem": problem,
                   "editable": checker.has_perm('edit_problem', problem),
                   "rev1": rev1,
                   "rev2": rev2,
                   "rev1link": reverse("judge-problem-old", kwargs={"id": rev1.id, "slug": problem.slug}),
                   "rev2link": reverse("judge-problem-old", kwargs={"id": rev2.id, "slug": problem.slug}),
                   "description": differ(rev1.description, rev2.description),
                   "input": differ(rev1.input, rev2.input),
                   "output": differ(rev1.output, rev2.output),
                   "sample_input": differ(rev1.sample_input, rev2.sample_input),
                   "sample_output": differ(rev1.sample_output, rev2.sample_output),
                   "note": differ(rev1.note, rev2.note),
                   "differ": differ})

@login_required
def submit(request, slug):
    problem = get_object_or_404(Problem, slug=slug)
    checker = ObjectPermissionChecker(request.user)
    # read_problem permission owners and problem authors can opt in for nonpublic submissions.
    # nobody can submit public submissions to problems that are not published.
    if ((request.user == problem.user or checker.has_perm('read_problem', problem)) and
        problem.state == Problem.PUBLISHED):
        form = AdminSubmitForm(data=request.POST or None)
    else:
        form = SubmitForm(data=request.POST or None,
                          public=(problem.state == Problem.PUBLISHED))
    if request.method == "POST" and form.is_valid():
        form.save(request.user, problem)
        return redirect(reverse("judge-submission-recent"))

    return render(request, "problem/submit.html", {"form": form, "editable": checker.has_perm("edit_problem", problem),
        "problem": problem})

########NEW FILE########
__FILENAME__ = submission
# -*- coding: utf-8 -*-
from datetime import datetime
from django.shortcuts import render, redirect, get_object_or_404
from django.core.urlresolvers import reverse
from djangoutils import setup_paginator, get_or_none
from django.contrib.auth.models import User
from django.http import Http404, HttpResponseForbidden
from django.contrib.auth.decorators import login_required
from guardian.core import ObjectPermissionChecker
from ..models import Problem, Submission

def rejudge(request, id):
    submission = get_object_or_404(Submission, id=id)
    if submission.user != request.user and not request.user.is_superuser:
        return HttpResponseForbidden()
    submission.rejudge()
    return redirect(reverse("judge-submission-details", kwargs={"id": id}))

def recent(request, page=1):
    checker = ObjectPermissionChecker(request.user)
    submissions = Submission.objects.all().order_by("-id")

    filters = {}

    empty_message = u"제출된 답안이 없습니다."
    title_add = []

    # only superuser can see all nonpublic submissions.
    # as an exception, if we are filtering by a problem, the author can see
    # nonpublic submissions. also, everybody can see their nonpublic
    # submissions.
    only_public = not request.user.is_superuser

    if request.GET.get("problem"):
        slug = request.GET["problem"]
        problem = get_object_or_404(Problem, slug=slug)

        if request.user == problem.user or checker.has_perm('read_problem', problem):
            only_public = False

        if (problem.state != Problem.PUBLISHED and
             request.user != problem.user and
             not checker.has_perm('read_problem', problem)):
            raise Http404
        submissions = submissions.filter(problem=problem)

        title_add.append(slug)
        filters["problem"] = slug

    if "state" in request.GET:
        state = request.GET["state"]
        submissions = submissions.filter(state=state)
        filters["state"] = state
        title_add.append(Submission.STATES_KOR[int(state)])

    if request.GET.get("user"):
        username = request.GET["user"]
        user = get_or_none(User, username=username)
        if not user:
            empty_message = u"해당 사용자가 없습니다."
            submissions = submissions.none()
        else:
            submissions = submissions.filter(user=user)
        filters["user"] = username
        title_add.append(username)
        if user == request.user:
            only_public = False

    if only_public:
        submissions = submissions.filter(is_public=True)

    problems = Problem.objects.filter(state=Problem.PUBLISHED).order_by("slug")
    users = User.objects.order_by("username")

    return render(request, "submission/recent.html",
                  {"title": u"답안 목록" + (": " if title_add else "") +
                   ",".join(title_add),
                   "problems": problems,
                   "users": users,
                   "filters": filters,
                   "empty_message": empty_message,
                   "pagination": setup_paginator(submissions, page,
                                                 "judge-submission-recent", {}, filters)})

@login_required
def details(request, id):
    from django.conf import settings 

    checker = ObjectPermissionChecker(request.user)
    submission = get_object_or_404(Submission, id=id)
    problem = submission.problem
    if (not problem.was_solved_by(request.user) and
            submission.user != request.user and
            problem.user != request.user and
            not checker.has_perm('read_problem', problem)):
        return HttpResponseForbidden()
    message = ''
    if submission.state == Submission.ACCEPTED:
        now = datetime.now()
        for item in settings.SOLVED_CAMPAIGN:
            if (item['problem'] == problem.slug and 
                item['begin'] <= now <= item['end']):
                message = item['message']
                break
    return render(request, "submission/details.html",
                  {"title": u"답안 보기",
                   "submission": submission,
                   "message": message,
                   "problem": problem})

########NEW FILE########
__FILENAME__ = manage
#!/usr/bin/env python
import os, sys

if __name__ == "__main__":
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "algospot.settings")

    from django.core.management import execute_from_command_line

    execute_from_command_line(sys.argv)

########NEW FILE########
__FILENAME__ = config
# -*- coding: utf-8 -*-


########NEW FILE########
__FILENAME__ = interface
from models import Activity
from django.contrib.auth.models import User, Group
from guardian.conf import settings
from guardian.shortcuts import assign_perm, get_users_with_perms

def publish(key, category, type, visible_users=None, visible_groups=None, **kwargs):
    new_activity = Activity.new(key=key, category=category, type=type, **kwargs)
    new_activity.save()

    if visible_users is None and visible_groups is None:
        anonymous = User.objects.get(pk=settings.ANONYMOUS_USER_ID)
        everyone = Group.objects.get(name='everyone')
        assign_perm('newsfeed.read_activity', anonymous, new_activity)
        assign_perm('newsfeed.read_activity', everyone, new_activity)
    else:
        for user in visible_users:
            assign_perm('newsfeed.read_activity', user, new_activity)
        for group in visible_groups:
            assign_perm('newsfeed.read_activity', group, new_activity)
    return new_activity

def depublish(key):
    Activity.objects.filter(key=key).delete()

def depublish_where(**kwargs):
    Activity.delete_all(**kwargs)

def has_activity(**kwargs):
    return Activity.objects.filter(**Activity.translate(kwargs)).count() > 0

def get_activity(**kwargs):
    return Activity.objects.get(**Activity.translate(kwargs))

########NEW FILE########
__FILENAME__ = activities_set_permissions
from django.core.management.base import NoArgsCommand
from django.contrib.auth.models import User, Group
from newsfeed.models import Activity
from guardian.conf import settings
from guardian.shortcuts import assign_perm

class Command(NoArgsCommand):
    def handle(self, **options):
        everyone = Group.objects.get(name='everyone')
        anonymous = User.objects.get(pk=settings.ANONYMOUS_USER_ID)

        for x in Activity.objects.all():
            if not x.admin_only:
                assign_perm('newsfeed.read_activity', anonymous, x)
                assign_perm('newsfeed.read_activity', everyone, x)
                

########NEW FILE########
__FILENAME__ = 0001_initial
# encoding: utf-8
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models

class Migration(SchemaMigration):

    def forwards(self, orm):
        pass


    def backwards(self, orm):
        pass


    models = {
        
    }

    complete_apps = ['newsfeed']

########NEW FILE########
__FILENAME__ = 0002_auto__add_activity
# encoding: utf-8
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models

class Migration(SchemaMigration):

    def forwards(self, orm):
        
        # Adding model 'Activity'
        db.create_table('newsfeed_activity', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('key', self.gf('django.db.models.fields.CharField')(unique=True, max_length=255, db_index=True)),
            ('category', self.gf('django.db.models.fields.CharField')(max_length=64, db_index=True)),
            ('actor', self.gf('django.db.models.fields.related.ForeignKey')(related_name='actor', null=True, to=orm['auth.User'])),
            ('verb', self.gf('django.db.models.fields.CharField')(max_length=255)),
            ('timestamp', self.gf('django.db.models.fields.DateTimeField')(auto_now_add=True, blank=True)),
        ))
        db.send_create_signal('newsfeed', ['Activity'])


    def backwards(self, orm):
        
        # Deleting model 'Activity'
        db.delete_table('newsfeed_activity')


    models = {
        'auth.group': {
            'Meta': {'object_name': 'Group'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '80'}),
            'permissions': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['auth.Permission']", 'symmetrical': 'False', 'blank': 'True'})
        },
        'auth.permission': {
            'Meta': {'ordering': "('content_type__app_label', 'content_type__model', 'codename')", 'unique_together': "(('content_type', 'codename'),)", 'object_name': 'Permission'},
            'codename': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'content_type': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['contenttypes.ContentType']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '50'})
        },
        'auth.user': {
            'Meta': {'object_name': 'User'},
            'date_joined': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'email': ('django.db.models.fields.EmailField', [], {'max_length': '75', 'blank': 'True'}),
            'first_name': ('django.db.models.fields.CharField', [], {'max_length': '30', 'blank': 'True'}),
            'groups': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['auth.Group']", 'symmetrical': 'False', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'is_active': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'is_staff': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'is_superuser': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'last_login': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'last_name': ('django.db.models.fields.CharField', [], {'max_length': '30', 'blank': 'True'}),
            'password': ('django.db.models.fields.CharField', [], {'max_length': '128'}),
            'user_permissions': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['auth.Permission']", 'symmetrical': 'False', 'blank': 'True'}),
            'username': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '30'})
        },
        'contenttypes.contenttype': {
            'Meta': {'ordering': "('name',)", 'unique_together': "(('app_label', 'model'),)", 'object_name': 'ContentType', 'db_table': "'django_content_type'"},
            'app_label': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'model': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '100'})
        },
        'newsfeed.activity': {
            'Meta': {'object_name': 'Activity'},
            'actor': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'actor'", 'null': 'True', 'to': "orm['auth.User']"}),
            'category': ('django.db.models.fields.CharField', [], {'max_length': '64', 'db_index': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'key': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '255', 'db_index': 'True'}),
            'timestamp': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'verb': ('django.db.models.fields.CharField', [], {'max_length': '255'})
        }
    }

    complete_apps = ['newsfeed']

########NEW FILE########
__FILENAME__ = 0003_auto__add_field_activity_target_content_type__add_field_activity_targe
# encoding: utf-8
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models

class Migration(SchemaMigration):

    def forwards(self, orm):
        
        # Adding field 'Activity.target_content_type'
        db.add_column('newsfeed_activity', 'target_content_type', self.gf('django.db.models.fields.related.ForeignKey')(blank=True, related_name='target_content_type', null=True, to=orm['contenttypes.ContentType']), keep_default=False)

        # Adding field 'Activity.target_object_id'
        db.add_column('newsfeed_activity', 'target_object_id', self.gf('django.db.models.fields.PositiveIntegerField')(null=True, blank=True), keep_default=False)


    def backwards(self, orm):
        
        # Deleting field 'Activity.target_content_type'
        db.delete_column('newsfeed_activity', 'target_content_type_id')

        # Deleting field 'Activity.target_object_id'
        db.delete_column('newsfeed_activity', 'target_object_id')


    models = {
        'auth.group': {
            'Meta': {'object_name': 'Group'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '80'}),
            'permissions': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['auth.Permission']", 'symmetrical': 'False', 'blank': 'True'})
        },
        'auth.permission': {
            'Meta': {'ordering': "('content_type__app_label', 'content_type__model', 'codename')", 'unique_together': "(('content_type', 'codename'),)", 'object_name': 'Permission'},
            'codename': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'content_type': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['contenttypes.ContentType']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '50'})
        },
        'auth.user': {
            'Meta': {'object_name': 'User'},
            'date_joined': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'email': ('django.db.models.fields.EmailField', [], {'max_length': '75', 'blank': 'True'}),
            'first_name': ('django.db.models.fields.CharField', [], {'max_length': '30', 'blank': 'True'}),
            'groups': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['auth.Group']", 'symmetrical': 'False', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'is_active': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'is_staff': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'is_superuser': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'last_login': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'last_name': ('django.db.models.fields.CharField', [], {'max_length': '30', 'blank': 'True'}),
            'password': ('django.db.models.fields.CharField', [], {'max_length': '128'}),
            'user_permissions': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['auth.Permission']", 'symmetrical': 'False', 'blank': 'True'}),
            'username': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '30'})
        },
        'contenttypes.contenttype': {
            'Meta': {'ordering': "('name',)", 'unique_together': "(('app_label', 'model'),)", 'object_name': 'ContentType', 'db_table': "'django_content_type'"},
            'app_label': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'model': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '100'})
        },
        'newsfeed.activity': {
            'Meta': {'object_name': 'Activity'},
            'actor': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'actor'", 'null': 'True', 'to': "orm['auth.User']"}),
            'category': ('django.db.models.fields.CharField', [], {'max_length': '64', 'db_index': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'key': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '255', 'db_index': 'True'}),
            'target_content_type': ('django.db.models.fields.related.ForeignKey', [], {'blank': 'True', 'related_name': "'target_content_type'", 'null': 'True', 'to': "orm['contenttypes.ContentType']"}),
            'target_object_id': ('django.db.models.fields.PositiveIntegerField', [], {'null': 'True', 'blank': 'True'}),
            'timestamp': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'verb': ('django.db.models.fields.CharField', [], {'max_length': '255'})
        }
    }

    complete_apps = ['newsfeed']

########NEW FILE########
__FILENAME__ = 0004_auto__add_field_activity_action_object_content_type__add_field_activit
# encoding: utf-8
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models

class Migration(SchemaMigration):

    def forwards(self, orm):
        
        # Adding field 'Activity.action_object_content_type'
        db.add_column('newsfeed_activity', 'action_object_content_type', self.gf('django.db.models.fields.related.ForeignKey')(blank=True, related_name='action_object_content_type', null=True, to=orm['contenttypes.ContentType']), keep_default=False)

        # Adding field 'Activity.action_object_object_id'
        db.add_column('newsfeed_activity', 'action_object_object_id', self.gf('django.db.models.fields.PositiveIntegerField')(null=True, blank=True), keep_default=False)


    def backwards(self, orm):
        
        # Deleting field 'Activity.action_object_content_type'
        db.delete_column('newsfeed_activity', 'action_object_content_type_id')

        # Deleting field 'Activity.action_object_object_id'
        db.delete_column('newsfeed_activity', 'action_object_object_id')


    models = {
        'auth.group': {
            'Meta': {'object_name': 'Group'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '80'}),
            'permissions': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['auth.Permission']", 'symmetrical': 'False', 'blank': 'True'})
        },
        'auth.permission': {
            'Meta': {'ordering': "('content_type__app_label', 'content_type__model', 'codename')", 'unique_together': "(('content_type', 'codename'),)", 'object_name': 'Permission'},
            'codename': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'content_type': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['contenttypes.ContentType']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '50'})
        },
        'auth.user': {
            'Meta': {'object_name': 'User'},
            'date_joined': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'email': ('django.db.models.fields.EmailField', [], {'max_length': '75', 'blank': 'True'}),
            'first_name': ('django.db.models.fields.CharField', [], {'max_length': '30', 'blank': 'True'}),
            'groups': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['auth.Group']", 'symmetrical': 'False', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'is_active': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'is_staff': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'is_superuser': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'last_login': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'last_name': ('django.db.models.fields.CharField', [], {'max_length': '30', 'blank': 'True'}),
            'password': ('django.db.models.fields.CharField', [], {'max_length': '128'}),
            'user_permissions': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['auth.Permission']", 'symmetrical': 'False', 'blank': 'True'}),
            'username': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '30'})
        },
        'contenttypes.contenttype': {
            'Meta': {'ordering': "('name',)", 'unique_together': "(('app_label', 'model'),)", 'object_name': 'ContentType', 'db_table': "'django_content_type'"},
            'app_label': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'model': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '100'})
        },
        'newsfeed.activity': {
            'Meta': {'object_name': 'Activity'},
            'action_object_content_type': ('django.db.models.fields.related.ForeignKey', [], {'blank': 'True', 'related_name': "'action_object_content_type'", 'null': 'True', 'to': "orm['contenttypes.ContentType']"}),
            'action_object_object_id': ('django.db.models.fields.PositiveIntegerField', [], {'null': 'True', 'blank': 'True'}),
            'actor': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'actor'", 'null': 'True', 'to': "orm['auth.User']"}),
            'category': ('django.db.models.fields.CharField', [], {'max_length': '64', 'db_index': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'key': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '255', 'db_index': 'True'}),
            'target_content_type': ('django.db.models.fields.related.ForeignKey', [], {'blank': 'True', 'related_name': "'target_content_type'", 'null': 'True', 'to': "orm['contenttypes.ContentType']"}),
            'target_object_id': ('django.db.models.fields.PositiveIntegerField', [], {'null': 'True', 'blank': 'True'}),
            'timestamp': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'verb': ('django.db.models.fields.CharField', [], {'max_length': '255'})
        }
    }

    complete_apps = ['newsfeed']

########NEW FILE########
__FILENAME__ = 0005_auto__add_field_activity_type
# encoding: utf-8
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models

class Migration(SchemaMigration):

    def forwards(self, orm):
        
        # Adding field 'Activity.type'
        db.add_column('newsfeed_activity', 'type', self.gf('django.db.models.fields.CharField')(default='donno', max_length=64), keep_default=False)


    def backwards(self, orm):
        
        # Deleting field 'Activity.type'
        db.delete_column('newsfeed_activity', 'type')


    models = {
        'auth.group': {
            'Meta': {'object_name': 'Group'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '80'}),
            'permissions': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['auth.Permission']", 'symmetrical': 'False', 'blank': 'True'})
        },
        'auth.permission': {
            'Meta': {'ordering': "('content_type__app_label', 'content_type__model', 'codename')", 'unique_together': "(('content_type', 'codename'),)", 'object_name': 'Permission'},
            'codename': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'content_type': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['contenttypes.ContentType']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '50'})
        },
        'auth.user': {
            'Meta': {'object_name': 'User'},
            'date_joined': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'email': ('django.db.models.fields.EmailField', [], {'max_length': '75', 'blank': 'True'}),
            'first_name': ('django.db.models.fields.CharField', [], {'max_length': '30', 'blank': 'True'}),
            'groups': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['auth.Group']", 'symmetrical': 'False', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'is_active': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'is_staff': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'is_superuser': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'last_login': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'last_name': ('django.db.models.fields.CharField', [], {'max_length': '30', 'blank': 'True'}),
            'password': ('django.db.models.fields.CharField', [], {'max_length': '128'}),
            'user_permissions': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['auth.Permission']", 'symmetrical': 'False', 'blank': 'True'}),
            'username': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '30'})
        },
        'contenttypes.contenttype': {
            'Meta': {'ordering': "('name',)", 'unique_together': "(('app_label', 'model'),)", 'object_name': 'ContentType', 'db_table': "'django_content_type'"},
            'app_label': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'model': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '100'})
        },
        'newsfeed.activity': {
            'Meta': {'object_name': 'Activity'},
            'action_object_content_type': ('django.db.models.fields.related.ForeignKey', [], {'blank': 'True', 'related_name': "'action_object_content_type'", 'null': 'True', 'to': "orm['contenttypes.ContentType']"}),
            'action_object_object_id': ('django.db.models.fields.PositiveIntegerField', [], {'null': 'True', 'blank': 'True'}),
            'actor': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'actor'", 'null': 'True', 'to': "orm['auth.User']"}),
            'category': ('django.db.models.fields.CharField', [], {'max_length': '64', 'db_index': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'key': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '255', 'db_index': 'True'}),
            'target_content_type': ('django.db.models.fields.related.ForeignKey', [], {'blank': 'True', 'related_name': "'target_content_type'", 'null': 'True', 'to': "orm['contenttypes.ContentType']"}),
            'target_object_id': ('django.db.models.fields.PositiveIntegerField', [], {'null': 'True', 'blank': 'True'}),
            'timestamp': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'type': ('django.db.models.fields.CharField', [], {'max_length': '64'}),
            'verb': ('django.db.models.fields.CharField', [], {'max_length': '255'})
        }
    }

    complete_apps = ['newsfeed']

########NEW FILE########
__FILENAME__ = 0006_auto__chg_field_activity_timestamp
# encoding: utf-8
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models

class Migration(SchemaMigration):

    def forwards(self, orm):
        
        # Changing field 'Activity.timestamp'
        db.alter_column('newsfeed_activity', 'timestamp', self.gf('django.db.models.fields.DateTimeField')())

        # Adding index on 'Activity', fields ['timestamp']
        db.create_index('newsfeed_activity', ['timestamp'])


    def backwards(self, orm):
        
        # Removing index on 'Activity', fields ['timestamp']
        db.delete_index('newsfeed_activity', ['timestamp'])

        # Changing field 'Activity.timestamp'
        db.alter_column('newsfeed_activity', 'timestamp', self.gf('django.db.models.fields.DateTimeField')(auto_now_add=True))


    models = {
        'auth.group': {
            'Meta': {'object_name': 'Group'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '80'}),
            'permissions': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['auth.Permission']", 'symmetrical': 'False', 'blank': 'True'})
        },
        'auth.permission': {
            'Meta': {'ordering': "('content_type__app_label', 'content_type__model', 'codename')", 'unique_together': "(('content_type', 'codename'),)", 'object_name': 'Permission'},
            'codename': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'content_type': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['contenttypes.ContentType']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '50'})
        },
        'auth.user': {
            'Meta': {'object_name': 'User'},
            'date_joined': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'email': ('django.db.models.fields.EmailField', [], {'max_length': '75', 'blank': 'True'}),
            'first_name': ('django.db.models.fields.CharField', [], {'max_length': '30', 'blank': 'True'}),
            'groups': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['auth.Group']", 'symmetrical': 'False', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'is_active': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'is_staff': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'is_superuser': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'last_login': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'last_name': ('django.db.models.fields.CharField', [], {'max_length': '30', 'blank': 'True'}),
            'password': ('django.db.models.fields.CharField', [], {'max_length': '128'}),
            'user_permissions': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['auth.Permission']", 'symmetrical': 'False', 'blank': 'True'}),
            'username': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '30'})
        },
        'contenttypes.contenttype': {
            'Meta': {'ordering': "('name',)", 'unique_together': "(('app_label', 'model'),)", 'object_name': 'ContentType', 'db_table': "'django_content_type'"},
            'app_label': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'model': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '100'})
        },
        'newsfeed.activity': {
            'Meta': {'object_name': 'Activity'},
            'action_object_content_type': ('django.db.models.fields.related.ForeignKey', [], {'blank': 'True', 'related_name': "'action_object_content_type'", 'null': 'True', 'to': "orm['contenttypes.ContentType']"}),
            'action_object_object_id': ('django.db.models.fields.PositiveIntegerField', [], {'null': 'True', 'blank': 'True'}),
            'actor': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'actor'", 'null': 'True', 'to': "orm['auth.User']"}),
            'category': ('django.db.models.fields.CharField', [], {'max_length': '64', 'db_index': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'key': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '255', 'db_index': 'True'}),
            'target_content_type': ('django.db.models.fields.related.ForeignKey', [], {'blank': 'True', 'related_name': "'target_content_type'", 'null': 'True', 'to': "orm['contenttypes.ContentType']"}),
            'target_object_id': ('django.db.models.fields.PositiveIntegerField', [], {'null': 'True', 'blank': 'True'}),
            'timestamp': ('django.db.models.fields.DateTimeField', [], {'db_index': 'True'}),
            'type': ('django.db.models.fields.CharField', [], {'max_length': '64'}),
            'verb': ('django.db.models.fields.CharField', [], {'max_length': '255'})
        }
    }

    complete_apps = ['newsfeed']

########NEW FILE########
__FILENAME__ = 0007_auto__add_field_activity_admin_only
# encoding: utf-8
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models

class Migration(SchemaMigration):

    def forwards(self, orm):
        
        # Adding field 'Activity.admin_only'
        db.add_column('newsfeed_activity', 'admin_only', self.gf('django.db.models.fields.BooleanField')(default=False), keep_default=False)


    def backwards(self, orm):
        
        # Deleting field 'Activity.admin_only'
        db.delete_column('newsfeed_activity', 'admin_only')


    models = {
        'auth.group': {
            'Meta': {'object_name': 'Group'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '80'}),
            'permissions': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['auth.Permission']", 'symmetrical': 'False', 'blank': 'True'})
        },
        'auth.permission': {
            'Meta': {'ordering': "('content_type__app_label', 'content_type__model', 'codename')", 'unique_together': "(('content_type', 'codename'),)", 'object_name': 'Permission'},
            'codename': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'content_type': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['contenttypes.ContentType']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '50'})
        },
        'auth.user': {
            'Meta': {'object_name': 'User'},
            'date_joined': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'email': ('django.db.models.fields.EmailField', [], {'max_length': '75', 'blank': 'True'}),
            'first_name': ('django.db.models.fields.CharField', [], {'max_length': '30', 'blank': 'True'}),
            'groups': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['auth.Group']", 'symmetrical': 'False', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'is_active': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'is_staff': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'is_superuser': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'last_login': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'last_name': ('django.db.models.fields.CharField', [], {'max_length': '30', 'blank': 'True'}),
            'password': ('django.db.models.fields.CharField', [], {'max_length': '128'}),
            'user_permissions': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['auth.Permission']", 'symmetrical': 'False', 'blank': 'True'}),
            'username': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '30'})
        },
        'contenttypes.contenttype': {
            'Meta': {'ordering': "('name',)", 'unique_together': "(('app_label', 'model'),)", 'object_name': 'ContentType', 'db_table': "'django_content_type'"},
            'app_label': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'model': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '100'})
        },
        'newsfeed.activity': {
            'Meta': {'object_name': 'Activity'},
            'action_object_content_type': ('django.db.models.fields.related.ForeignKey', [], {'blank': 'True', 'related_name': "'action_object_content_type'", 'null': 'True', 'to': "orm['contenttypes.ContentType']"}),
            'action_object_object_id': ('django.db.models.fields.PositiveIntegerField', [], {'null': 'True', 'blank': 'True'}),
            'actor': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'actor'", 'null': 'True', 'to': "orm['auth.User']"}),
            'admin_only': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'category': ('django.db.models.fields.CharField', [], {'max_length': '64', 'db_index': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'key': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '255', 'db_index': 'True'}),
            'target_content_type': ('django.db.models.fields.related.ForeignKey', [], {'blank': 'True', 'related_name': "'target_content_type'", 'null': 'True', 'to': "orm['contenttypes.ContentType']"}),
            'target_object_id': ('django.db.models.fields.PositiveIntegerField', [], {'null': 'True', 'blank': 'True'}),
            'timestamp': ('django.db.models.fields.DateTimeField', [], {'db_index': 'True'}),
            'type': ('django.db.models.fields.CharField', [], {'max_length': '64'}),
            'verb': ('django.db.models.fields.CharField', [], {'max_length': '255'})
        }
    }

    complete_apps = ['newsfeed']

########NEW FILE########
__FILENAME__ = models
# -*- coding: utf-8 -*-
from django.db import models
from django.contrib.contenttypes import generic
from django.contrib.contenttypes.models import ContentType
from django.contrib.auth.models import User
from django.utils.safestring import mark_safe
from django.contrib.comments.models import Comment
import datetime

class Activity(models.Model):
    # 액션 고유 ID. 지울 때 쓴다. 예: judge-problem-opened-417
    key = models.CharField(max_length=255, db_index=True, unique=True)
    # 액션 카테고리. 카테고리별 뉴스피드를 볼 때 쓴다. 예: wiki, judge,
    # membership
    category = models.CharField(max_length=64, db_index=True)
    # 액션 타입. css 클래스를 정하는 데 쓴다.. -_-; 예: wiki-edit,
    # problem-solved, posted, commented
    type = models.CharField(max_length=64)
    # 액터
    actor = models.ForeignKey(User, null=True, related_name='actor')
    # {actor} {target} {action_object} 를 갖는 문자열
    verb = models.CharField(max_length=255)

    admin_only = models.BooleanField(default=False) # 더 이상 사용되지 않고 권한 기반으로 변경됨

    target_content_type = models.ForeignKey(ContentType,
                                            related_name='target_content_type',
                                            blank=True,
                                            null=True)
    target_object_id = models.PositiveIntegerField(blank=True,
                                                   null=True)
    target = generic.GenericForeignKey('target_content_type','target_object_id')

    action_object_content_type = models.ForeignKey(ContentType,
                                                   related_name='action_object_content_type',
                                                   blank=True,
                                                   null=True)
    action_object_object_id = models.PositiveIntegerField(blank=True,null=True)
    action_object = generic.GenericForeignKey('action_object_content_type',
                                              'action_object_object_id')
    timestamp = models.DateTimeField(db_index=True)

    class Meta:
        permissions = (
            ('read_activity', 'Can read this activity'),
        )

    @staticmethod
    def translate(kwargs):
        args = {}
        for k, v in kwargs.iteritems():
            if k in ["target", "action_object"]:
                ct = ContentType.objects.get_for_model(v.__class__)
                pk = v.id
                args[k + "_content_type"] = ct
                args[k + "_object_id"] = pk
            else:
                args[k] = v
        return args

    @staticmethod
    def new(**kwargs):
        if "timestamp" not in kwargs:
            kwargs["timestamp"] = datetime.datetime.now()
        return Activity(**Activity.translate(kwargs))

    @staticmethod
    def delete_all(**kwargs):
        return Activity.objects.filter(**Activity.translate(kwargs)).delete()

    def render(self, spoiler_replacement=None):
        from judge.models import Problem
        def wrap_in_link(object, spoiler_replacement):
            if not object: return ""
            if spoiler_replacement:
                unicode_rep = spoiler_replacement
            elif isinstance(object, Comment):
                unicode_rep = object.comment
                if len(unicode_rep) > 50:
                    unicode_rep = unicode_rep[:47] + ".."
            else:
                unicode_rep = unicode(object)
            if object.get_absolute_url:
                return "".join(['<a href="%s">' % object.get_absolute_url(),
                    unicode_rep,
                    '</a>'])
            return unicode_rep
        return mark_safe(self.verb.format(actor=wrap_in_link(self.actor, None),
                                          action_object=wrap_in_link(self.action_object, spoiler_replacement),
                                          target=wrap_in_link(self.target, None)))

########NEW FILE########
__FILENAME__ = newsfeed_tags
# -*- coding: utf-8 -*-
from django import template
from django.contrib.comments.models import Comment
from guardian.shortcuts import get_perms
from judge.models import Problem, Solver

register = template.Library()

@register.filter
def aggregate_by_user(page):
    # aggregate by actor
    aggregated = []
    for action in page:
        if not aggregated or aggregated[-1][0] != action.actor:
            aggregated.append((action.actor, []))
        aggregated[-1][1].append(action)
    return aggregated

@register.simple_tag
def render_activity(*args, **kwargs):
    activity = kwargs['activity']
    user = kwargs['user']

    hide_spoiler = False
    if isinstance(activity.action_object, Comment):
        if "<spoiler>" in activity.action_object.comment:
            hide_spoiler = True
        if isinstance(activity.target, Problem):
            hide_spoiler = True
            if not user.is_anonymous() and Solver.objects.filter(problem=activity.target, solved=True, user=user).exists():
                hide_spoiler = False
            elif get_perms(user, activity.target): # read and/or edit
                hide_spoiler = False
    return activity.render(spoiler_replacement=u"[스포일러 방지를 위해 보이지 않습니다]" if hide_spoiler else None)

########NEW FILE########
__FILENAME__ = tests
"""
This file demonstrates writing tests using the unittest module. These will pass
when you run "manage.py test".

Replace this with more appropriate tests for your application.
"""

from django.test import TestCase


class SimpleTest(TestCase):
    def test_basic_addition(self):
        """
        Tests that 1 + 1 always equals 2.
        """
        self.assertEqual(1 + 1, 2)

########NEW FILE########
__FILENAME__ = urls
# -*- coding: utf-8 -*-
from django.conf.urls.defaults import patterns, url
import views
urlpatterns = patterns(
    'newsfeed.views',
    url(r'^$', views.stream, name='newsfeed'),
    url(r'^(?P<page>[0-9]+)/$', views.stream, name='newsfeed'),
    url(r'^user/(?P<id>[0-9]+)$', views.by_user, name='newsfeed-byuser'),
    url(r'^user/(?P<id>[0-9]+)/(?P<page>[0-9]+)/$', views.by_user, name='newsfeed-byuser'),
    url(r'^filter/(?P<id>[0-9]+)/(?P<type>[a-z]+)/$', views.filter,
        name='newsfeed-filter'),
    url(r'^filter/(?P<id>[0-9]+)/(?P<type>[a-z]+)/(?P<page>[0-9]+)/$',
        views.filter, name='newsfeed-filter'),
)


########NEW FILE########
__FILENAME__ = utils
# -*- coding: utf-8 -*-

from __future__ import unicode_literals

from django.contrib.contenttypes.models import ContentType
from django.db.models import Count
from django.shortcuts import _get_queryset
from django.contrib.auth.models import User
from itertools import groupby

from guardian.conf import settings
from guardian.compat import get_user_model
from guardian.compat import basestring
from guardian.exceptions import MixedContentTypeError
from guardian.exceptions import WrongAppError
from guardian.utils import get_user_obj_perms_model
from guardian.utils import get_group_obj_perms_model
import warnings
from models import Activity

# 성능 문제 해결을 위해 아직 반영되지 않은 패치 내용을 옮겨 옴
# 기존에는 pk를 리스트로 만들어 ... AND "app_model"."id" IN (6, 7, 35, 36, 41, 43, 45, ... 4175, 4178, 4179, 4184, 4186) ... 식으로 뽑아내는 바람에 성능도 문제가 되고 쿼리 길이 제한에도 걸렸다
# PR: https://github.com/lukaszb/django-guardian/pull/148
# 코드: https://github.com/ggreer/django-guardian/blob/207a5113529ddb96eaa7a8116d5c5d3600e6173e/guardian/shortcuts.py
def get_objects_for_user(user, perms, klass=None, use_groups=True, any_perm=False):
    """
    Returns queryset of objects for which a given ``user`` has *all*
    permissions present at ``perms``.

    :param user: ``User`` instance for which objects would be returned
    :param perms: single permission string, or sequence of permission strings
      which should be checked.
      If ``klass`` parameter is not given, those should be full permission
      names rather than only codenames (i.e. ``auth.change_user``). If more than
      one permission is present within sequence, their content type **must** be
      the same or ``MixedContentTypeError`` exception would be raised.
    :param klass: may be a Model, Manager or QuerySet object. If not given
      this parameter would be computed based on given ``params``.
    :param use_groups: if ``False``, wouldn't check user's groups object
      permissions. Default is ``True``.
    :param any_perm: if True, any of permission in sequence is accepted

    :raises MixedContentTypeError: when computed content type for ``perms``
      and/or ``klass`` clashes.
    :raises WrongAppError: if cannot compute app label for given ``perms``/
      ``klass``.

    Example::

        >>> from guardian.shortcuts import get_objects_for_user
        >>> joe = User.objects.get(username='joe')
        >>> get_objects_for_user(joe, 'auth.change_group')
        []
        >>> from guardian.shortcuts import assign_perm
        >>> group = Group.objects.create('some group')
        >>> assign_perm('auth.change_group', joe, group)
        >>> get_objects_for_user(joe, 'auth.change_group')
        [<Group some group>]

    The permission string can also be an iterable. Continuing with the previous example:

        >>> get_objects_for_user(joe, ['auth.change_group', 'auth.delete_group'])
        []
        >>> get_objects_for_user(joe, ['auth.change_group', 'auth.delete_group'], any_perm=True)
        [<Group some group>]
        >>> assign_perm('auth.delete_group', joe, group)
        >>> get_objects_for_user(joe, ['auth.change_group', 'auth.delete_group'])
        [<Group some group>]

    """
    if isinstance(perms, basestring):
        perms = [perms]
    ctype = None
    app_label = None
    codenames = set()

    # Compute codenames set and ctype if possible
    for perm in perms:
        if '.' in perm:
            new_app_label, codename = perm.split('.', 1)
            if app_label is not None and app_label != new_app_label:
                raise MixedContentTypeError("Given perms must have same app "
                    "label (%s != %s)" % (app_label, new_app_label))
            else:
                app_label = new_app_label
        else:
            codename = perm
        codenames.add(codename)
        if app_label is not None:
            new_ctype = ContentType.objects.get(app_label=app_label,
                permission__codename=codename)
            if ctype is not None and ctype != new_ctype:
                raise MixedContentTypeError("ContentType was once computed "
                    "to be %s and another one %s" % (ctype, new_ctype))
            else:
                ctype = new_ctype

    # Compute queryset and ctype if still missing
    if ctype is None and klass is None:
        raise WrongAppError("Cannot determine content type")
    elif ctype is None and klass is not None:
        queryset = _get_queryset(klass)
        ctype = ContentType.objects.get_for_model(queryset.model)
    elif ctype is not None and klass is None:
        queryset = _get_queryset(ctype.model_class())
    else:
        queryset = _get_queryset(klass)
        if ctype.model_class() != queryset.model:
            raise MixedContentTypeError("Content type for given perms and "
                "klass differs")

    # At this point, we should have both ctype and queryset and they should
    # match which means: ctype.model_class() == queryset.model
    # we should also have ``codenames`` list

    # First check if user is superuser and if so, return queryset immediately
    if user.is_superuser:
        return queryset

    # Now we should extract list of pk values for which we would filter queryset
    user_model = get_user_obj_perms_model(queryset.model)
    user_obj_perms_queryset = (user_model.objects
        .filter(user=user)
        .filter(permission__content_type=ctype)
        .filter(permission__codename__in=codenames))
    if user_model.objects.is_generic():
        fields = ['object_pk', 'permission__codename']
    else:
        fields = ['content_object__pk', 'permission__codename']

    if use_groups:
        group_model = get_group_obj_perms_model(queryset.model)
        group_filters = {
            'permission__content_type': ctype,
            'permission__codename__in': codenames,
            'group__%s' % get_user_model()._meta.module_name: user,
        }
        groups_obj_perms_queryset = group_model.objects.filter(**group_filters)
        if group_model.objects.is_generic():
            fields = ['object_pk', 'permission__codename']
        else:
            fields = ['content_object__pk', 'permission__codename']
        if not any_perm:
            user_obj_perms = user_obj_perms_queryset.values_list(*fields)
            groups_obj_perms = groups_obj_perms_queryset.values_list(*fields)
            data = list(user_obj_perms) + list(groups_obj_perms)
            keyfunc = lambda t: t[0] # sorting/grouping by pk (first in result tuple)
            data = sorted(data, key=keyfunc)
            pk_list = []
            for pk, group in groupby(data, keyfunc):
                obj_codenames = set((e[1] for e in group))
                if codenames.issubset(obj_codenames):
                    pk_list.append(pk)
            objects = queryset.filter(pk__in=pk_list)
            return objects

    if not any_perm:
        counts = user_obj_perms_queryset.values(fields[0]).annotate(object_pk_count=Count(fields[0]))
        user_obj_perms_queryset = counts.filter(object_pk_count__gte=len(codenames))

    objects = queryset.filter(pk__in=user_obj_perms_queryset.values_list(fields[0], flat=True))
    if use_groups:
        objects |= queryset.filter(pk__in=groups_obj_perms_queryset.values_list(fields[0], flat=True))

    return objects

def get_activities_for_user(request_user):
    user = (request_user.is_anonymous() and User.objects.get(pk=settings.ANONYMOUS_USER_ID) or request_user)
    return get_objects_for_user(user, 'newsfeed.read_activity', Activity, any_perm=True)

########NEW FILE########
__FILENAME__ = views
# -*- coding: utf-8 -*-
from django.shortcuts import render, get_object_or_404
from djangoutils import setup_paginator, profile
from models import Activity
from utils import get_activities_for_user
from django.contrib.auth.models import User

@profile("newsfeed_stream")
def stream(request, page="1"):
    actions = get_activities_for_user(request.user).exclude(category='solved').order_by("-timestamp")
    print actions.query

    return render(request, "newsfeed.html",
                  {"pagination": setup_paginator(actions, page, "newsfeed", {})})

def by_user(request, id, page="1"):
    user = get_object_or_404(User, id=id)
    actions = get_activities_for_user(request.user).filter(actor=user).order_by("-timestamp")

    return render(request, "newsfeed.html",
                  {"pagination": setup_paginator(actions, page,
                                                 "newsfeed-byuser", {'id': id})})

def filter(request, id, type, page="1"):
    user = get_object_or_404(User, id=id)
    actions = get_activities_for_user(request.user).filter(actor=user, type=type).order_by("-timestamp")
    pagination = setup_paginator(actions, page, "newsfeed-filter", {'id': id, 'type': type})
    return render(request, "newsfeed.html", {"pagination": pagination})

########NEW FILE########
__FILENAME__ = admin
# -*- coding: utf-8 -*-

from models import Page, PageRevision
from django.contrib import admin

admin.site.register(Page)
admin.site.register(PageRevision)

########NEW FILE########
__FILENAME__ = forms
# -*- coding: utf-8 -*-
from django import forms
from models import PageRevision

class EditForm(forms.Form):
    text = forms.CharField(widget=forms.Textarea(attrs={"class": "large",
                                                        "rows": "20"}))
    summary = forms.CharField(max_length=100,
                              widget=forms.TextInput(attrs={"class": "large"}),
                              required=False)

    def save(self, page, user):
        revision = PageRevision(text=self.cleaned_data["text"],
                                edit_summary=self.cleaned_data["summary"],
                                user=user,
                                revision_for=page)
        revision.save()
        page.current_revision = revision
        page.save()


########NEW FILE########
__FILENAME__ = 0001_initial
# encoding: utf-8
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models

class Migration(SchemaMigration):

    def forwards(self, orm):
        
        # Adding model 'PageRevision'
        db.create_table('wiki_pagerevision', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('text', self.gf('django.db.models.fields.TextField')()),
            ('edit_summary', self.gf('django.db.models.fields.TextField')(max_length=100)),
            ('user', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['auth.User'])),
            ('created_on', self.gf('django.db.models.fields.DateTimeField')(auto_now_add=True, blank=True)),
            ('revision_for', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['wiki.Page'])),
        ))
        db.send_create_signal('wiki', ['PageRevision'])

        # Adding model 'Page'
        db.create_table('wiki_page', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('title', self.gf('django.db.models.fields.CharField')(unique=True, max_length=100)),
            ('slug', self.gf('django.db.models.fields.SlugField')(unique=True, max_length=100, db_index=True)),
            ('created_on', self.gf('django.db.models.fields.DateTimeField')(auto_now_add=True, blank=True)),
            ('modified_on', self.gf('django.db.models.fields.DateTimeField')(auto_now=True, blank=True)),
            ('current_revision', self.gf('django.db.models.fields.related.ForeignKey')(blank=True, related_name='main', null=True, to=orm['wiki.PageRevision'])),
        ))
        db.send_create_signal('wiki', ['Page'])


    def backwards(self, orm):
        
        # Deleting model 'PageRevision'
        db.delete_table('wiki_pagerevision')

        # Deleting model 'Page'
        db.delete_table('wiki_page')


    models = {
        'auth.group': {
            'Meta': {'object_name': 'Group'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '80'}),
            'permissions': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['auth.Permission']", 'symmetrical': 'False', 'blank': 'True'})
        },
        'auth.permission': {
            'Meta': {'ordering': "('content_type__app_label', 'content_type__model', 'codename')", 'unique_together': "(('content_type', 'codename'),)", 'object_name': 'Permission'},
            'codename': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'content_type': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['contenttypes.ContentType']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '50'})
        },
        'auth.user': {
            'Meta': {'object_name': 'User'},
            'date_joined': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'email': ('django.db.models.fields.EmailField', [], {'max_length': '75', 'blank': 'True'}),
            'first_name': ('django.db.models.fields.CharField', [], {'max_length': '30', 'blank': 'True'}),
            'groups': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['auth.Group']", 'symmetrical': 'False', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'is_active': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'is_staff': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'is_superuser': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'last_login': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'last_name': ('django.db.models.fields.CharField', [], {'max_length': '30', 'blank': 'True'}),
            'password': ('django.db.models.fields.CharField', [], {'max_length': '128'}),
            'user_permissions': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['auth.Permission']", 'symmetrical': 'False', 'blank': 'True'}),
            'username': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '30'})
        },
        'contenttypes.contenttype': {
            'Meta': {'ordering': "('name',)", 'unique_together': "(('app_label', 'model'),)", 'object_name': 'ContentType', 'db_table': "'django_content_type'"},
            'app_label': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'model': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '100'})
        },
        'wiki.page': {
            'Meta': {'object_name': 'Page'},
            'created_on': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'current_revision': ('django.db.models.fields.related.ForeignKey', [], {'blank': 'True', 'related_name': "'main'", 'null': 'True', 'to': "orm['wiki.PageRevision']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'modified_on': ('django.db.models.fields.DateTimeField', [], {'auto_now': 'True', 'blank': 'True'}),
            'slug': ('django.db.models.fields.SlugField', [], {'unique': 'True', 'max_length': '100', 'db_index': 'True'}),
            'title': ('django.db.models.fields.TextField', [], {'unique': 'True', 'max_length': '100'})
        },
        'wiki.pagerevision': {
            'Meta': {'object_name': 'PageRevision'},
            'created_on': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'edit_summary': ('django.db.models.fields.TextField', [], {'max_length': '100'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'revision_for': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['wiki.Page']"}),
            'text': ('django.db.models.fields.TextField', [], {}),
            'user': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['auth.User']"})
        }
    }

    complete_apps = ['wiki']

########NEW FILE########
__FILENAME__ = models
# -*- coding: utf-8 -*-
from django.db import models
from django.core.urlresolvers import reverse
from django.db.models.signals import post_save
from django.contrib.auth.models import User
from newsfeed import publish

class PageRevision(models.Model):
    """Stores a specific revision of the page."""
    text = models.TextField()
    edit_summary = models.TextField(max_length=100, blank=True, null=True)
    user = models.ForeignKey(User, null=False)
    created_on = models.DateTimeField(auto_now_add=True)
    revision_for = models.ForeignKey('Page')

    def __unicode__(self):
        return self.revision_for.title + " " + unicode(self.created_on)

class Page(models.Model):
    """Stores a wiki page."""
    title = models.CharField(unique=True, max_length=100)
    slug = models.SlugField(unique=True, max_length=100)
    created_on = models.DateTimeField(auto_now_add=True)
    modified_on = models.DateTimeField(auto_now=True)
    current_revision = models.ForeignKey(PageRevision, related_name='main',
                                         blank=True, null=True)

    def __unicode__(self):
        return self.title

    def get_absolute_url(self):
        return reverse("wiki-detail", args=[self.slug])

def edit_handler(sender, **kwargs):
    instance = kwargs["instance"]
    publish("wiki-edit-%d" % instance.id,
            "wiki",
            "wiki-edit",
            actor=instance.user,
            target=instance.revision_for,
            timestamp=instance.created_on,
            verb=u"위키 페이지 {target}을 편집했습니다.")

post_save.connect(edit_handler, sender=PageRevision,
        dispatch_uid="wiki_edit_event")

########NEW FILE########
__FILENAME__ = search_indexes
import datetime
from haystack import indexes
from models import Page

class PageIndex(indexes.SearchIndex, indexes.Indexable):
    text = indexes.EdgeNgramField(document=True, use_template=True)
    date = indexes.DateTimeField(model_attr='modified_on')

    def get_model(self):
        return Page

    def index_queryset(self, using=None):
        return self.get_model().objects.filter(modified_on__lte=datetime.datetime.now())

########NEW FILE########
__FILENAME__ = tests
"""
This file demonstrates writing tests using the unittest module. These will pass
when you run "manage.py test".

Replace this with more appropriate tests for your application.
"""

from django.test import TestCase


class SimpleTest(TestCase):
    def test_basic_addition(self):
        """
        Tests that 1 + 1 always equals 2.
        """
        self.assertEqual(1 + 1, 2)

########NEW FILE########
__FILENAME__ = urls
# -*- coding: utf-8 -*-
from django.conf.urls.defaults import url, patterns
import views

urlpatterns = patterns(
    'wiki.views',
    url(r'^read/(?P<slug>.+)$', views.detail, name='wiki-detail'),
    url(r'^edit/(?P<slug>.+)$', views.edit, name='wiki-edit'),
    url(r'^history/(?P<slug>.+)$', views.history, name='wiki-history'),
    url(r'^old/(?P<id>[0-9]+)/(?P<slug>.+)$', views.old,
        name='wiki-old'),
    url(r'^revert/(?P<id>[0-9]+)/(?P<slug>.+)$', views.revert,
        name='wiki-revert'),
    url(r'^diff$', views.diff, name='wiki-diff-home'),
    url(r'^diff/(?P<id1>[0-9]+)/(?P<id2>[0-9]+)$', views.diff,
        name='wiki-diff'),
)


########NEW FILE########
__FILENAME__ = utils
# -*- coding: utf-8 -*-
from django.core.urlresolvers import reverse
from django.utils.html import escape
from models import Page
import logging
import re

logger = logging.getLogger("wiki")

def link_to_page(title, display):
    slug = slugify(title)
    if Page.objects.filter(slug=slug).count() == 0:
        return u'<a class="missing" href="%s">%s</a>' % (reverse("wiki-edit", kwargs={"slug": slug}), escape(display or title))
    return u'<a href="%s">%s</a>' % (reverse("wiki-detail", kwargs={"slug": slug}), escape(display or title))

def slugify(title):
    return re.sub(r'\s+', '_', title)

def unslugify(title):
    return re.sub(ur'[_\s]+', ' ', title)



########NEW FILE########
__FILENAME__ = views
# -*- coding: utf-8 -*-
from diff_match_patch import diff_match_patch
from django.core.urlresolvers import reverse
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from base.decorators import authorization_required

from models import Page, PageRevision
from forms import EditForm
from utils import unslugify, logger
from djangoutils import get_or_none

def old(request, id, slug):
    page = get_object_or_404(Page, slug=slug)
    revision = PageRevision.objects.get(id=id)
    return render(request, "old.html",
                  {"slug": slug,
                   "title": page.title,
                   "time": unicode(revision.created_on),
                   "modified": revision.created_on,
                   "text": revision.text})

@login_required
@authorization_required
def revert(request, id, slug):
    page = get_object_or_404(Page, slug=slug)
    revision = PageRevision.objects.get(id=id)
    form = EditForm({"text": revision.text,
                     "summary": u"리비전 %s(으)로 복구." % id})
    assert form.is_valid()
    form.save(page, request.user)
    return redirect(reverse("wiki-detail", kwargs={"slug": page.slug}))

def history(request, slug):
    page = get_object_or_404(Page, slug=slug)

    revision_set = PageRevision.objects.filter(revision_for=page).order_by("-id")
    ids = [rev.id for rev in revision_set[:2]]
    revisions = revision_set.all()
    last, second_last = -1, -1
    if len(ids) >= 2:
        last, second_last = ids[0], ids[1]
        logger.info("last %s second_last %s", last, second_last)

    return render(request, "history.html",
                  {"slug": slug,
                   "revisions": revisions,
                   "title": page.title,
                   "last_rev": last,
                   "second_last_rev": second_last})

def diff(request, id1=-1, id2=-1):
    rev1 = get_object_or_404(PageRevision, id=id1)
    rev2 = get_object_or_404(PageRevision, id=id2)
    slug = rev1.revision_for.slug
    title = rev1.revision_for.title

    dmp = diff_match_patch()
    diff = dmp.diff_main(rev1.text, rev2.text)
    return render(request, "diff.html",
                  {"slug": slug,
                   "title": title,
                   "diff": diff,
                   "rev1": id1,
                   "rev2": id2,
                   "rev1link": reverse("wiki-old", kwargs={"id": id1, "slug": slug}),
                   "rev2link": reverse("wiki-old", kwargs={"id": id2, "slug": slug})})


def detail(request, slug):
    page = get_object_or_404(Page, slug=slug)
    return render(request, "detail.html",
                  {"slug": slug,
                   "title": page.title,
                   "page": page,
                   "modified": page.modified_on,
                   "text": page.current_revision.text})

@login_required
@authorization_required
def edit(request, slug):
    params = {"slug": slug}
    page = get_or_none(Page, slug=slug)

    text = page.current_revision.text if page and page.current_revision else ""
    form = EditForm(data=request.POST or None, initial={"text": text})

    if request.method == "POST" and form.is_valid():
        if not page:
            page = Page(title=unslugify(slug), slug=slug)
            page.save()
        form.save(page, request.user)
        return redirect(reverse("wiki-detail", kwargs={"slug": page.slug}))

    params["form"] = form
    if page:
        params["action"] = "Edit"
        params["title"] = page.title
        params["modified"] = page.modified_on
        params["action"] = "Edit"
    else:
        params["title"] = unslugify(slug)
        params["modified"] = "NULL"
        params["action"] = "Create"

    return render(request, "edit.html", params)

########NEW FILE########
