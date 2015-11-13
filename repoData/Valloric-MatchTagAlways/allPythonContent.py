__FILENAME__ = mta_core
#!/usr/bin/env python
#
# Copyright (C) 2012  Strahinja Val Markovic  <val@markovic.io>
#
# This file is part of MatchTagAlways.
#
# MatchTagAlways is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# MatchTagAlways is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with MatchTagAlways.  If not, see <http://www.gnu.org/licenses/>.

import re


TAG_REGEX = re.compile(
  r"""<\s*                    # the opening bracket + whitespace
      (?P<start_slash>/)?     # captures the slash if closing bracket
      \s*                     # more whitespace
      (?P<tag_name>[\w:-]+)   # the tag name, captured
      .*?                     # anything else in the tag
      (?P<end_slash>/)?       # ending slash, for self-closed tags
      >""",
  re.VERBOSE | re.DOTALL )

COMMENT_REGEX = re.compile( '<!--.*?-->', re.DOTALL )


class TagType( object ):
  OPENING = 1
  CLOSING = 2
  SELF_CLOSED = 3


class Tag( object ):
  def __init__( self, match_object ):
    if not match_object:
      self.valid = False
      return
    self.valid = True
    self.name = match_object.group( 'tag_name' )

    if match_object.group( 'start_slash' ):
      self.kind = TagType.CLOSING
    elif match_object.group( 'end_slash' ):
      self.kind = TagType.SELF_CLOSED
    else:
      self.kind = TagType.OPENING

    self.start_offset = match_object.start()
    self.end_offset = match_object.end()


  def __nonzero__( self ):
    return self.valid


  def __eq__( self, other ):
    if type( other ) is type( self ):
        return
    return False


def PacifyHtmlComments( text ):
  """Replaces the contents (including delimiters) of all HTML comments in the
  passed-in text with 'x'. For instance, 'foo <!-- bar -->' becomes
  'foo xxxx xxx xxx'. We can't just remove the comments because that would screw
  with the mapping of string offset to Vim line/column."""

  def replacement( match ):
    return re.sub( '\S', 'x', match.group() )
  return COMMENT_REGEX.sub( replacement, text )


def ReverseFindTag( text, from_position ):
  try:
    bracket_index = text.rindex( '<', 0, from_position )
  except ValueError:
    return None
  match = TAG_REGEX.match( text, bracket_index )
  if not match:
    return None
  if match.end() <= from_position:
    return Tag( match )
  return None


def ForwardFindTag( text, from_position ):
  return Tag( TAG_REGEX.search( text, from_position ) )


def OffsetForLineColumnInString( text, line, column ):
  offset = -1
  current_line = 1
  current_column = 0
  previous_char = ''
  for char in text:
    offset += 1
    current_column += 1
    if char == '\n':
      current_line += 1
      current_column = 0

    if current_line == line and current_column == column:
      return offset
    if current_line > line:
      # Vim allows the user to stop on an empty line and declares that column 1
      # exists even when there are no characters on that line
      if current_column == 0 and previous_char == '\n':
        return offset -1
      break
    previous_char = char
  return None


def LineColumnForOffsetInString( text, offset ):
  current_offset = -1
  current_line = 1
  current_column = 0
  for char in text:
    current_offset += 1
    current_column += 1
    if char == '\n':
      current_line += 1
      current_column = 0
      continue

    if current_offset == offset:
      return current_line, current_column
    if current_offset > offset:
      break
  return None, None


def TagWithSameNameExistsInSequence( tag, sequence ):
  for current_tag in sequence:
    if current_tag.name == tag.name:
      return True
  return False


def GetPreviousUnmatchedOpeningTag( html, cursor_offset ):
  search_index = cursor_offset
  tags_to_close = []
  while True:
    prev_tag = ReverseFindTag( html, search_index )
    if not prev_tag:
      break
    search_index = prev_tag.start_offset

    if prev_tag.kind == TagType.CLOSING:
      tags_to_close.append( prev_tag )
    elif prev_tag.kind == TagType.OPENING:
      if tags_to_close:
        if tags_to_close[ -1 ].name == prev_tag.name:
          tags_to_close.pop()
        else:
          continue
      else:
        return prev_tag
    # self-closed tags ignored
  return None


def GetNextUnmatchedClosingTag( html, cursor_offset ):
  def RemoveClosedOpenTags( tags_to_close, new_tag ):
    i = 1
    for tag in reversed( tags_to_close ):
      if tag.name == new_tag.name:
        break
      else:
        i += 1
    assert i <= len( tags_to_close )
    del tags_to_close[ -i: ]
    return tags_to_close

  search_index = cursor_offset
  tags_to_close = []
  while True:
    next_tag = ForwardFindTag( html, search_index )
    if not next_tag:
      break
    search_index = next_tag.end_offset

    if next_tag.kind == TagType.OPENING:
      tags_to_close.append( next_tag )
    elif next_tag.kind == TagType.CLOSING:
      if not tags_to_close or not TagWithSameNameExistsInSequence(
        next_tag, tags_to_close ):
        return next_tag
      tags_to_close = RemoveClosedOpenTags( tags_to_close, next_tag )
    # self-closed tags ignored
  return None


def GetOpeningAndClosingTags( html, cursor_offset ):
  current_offset = cursor_offset

  closing_tag = GetNextUnmatchedClosingTag( html, current_offset )
  while True:
    opening_tag = GetPreviousUnmatchedOpeningTag( html, current_offset )

    if not opening_tag or not closing_tag:
      return None, None

    if opening_tag.name == closing_tag.name:
      return opening_tag, closing_tag
    current_offset = opening_tag.start_offset


def AdaptCursorOffsetIfNeeded( sanitized_html, cursor_offset ):
  """The cursor offset needs to be adapted if it is inside a tag.
  If the cursor is inside an opening tag, it will be moved to the index of the
  character just past the '>'. If it's inside the closing tag, it will be moved
  to the index of the '<'. This will ensure that both the opening and the
  closing tags are correctly found.
  If the cursor is inside a self-closed tag, then it doesn't really matter what
  we do with it, the surrounding tags will be correctly found (the self-closed
  tag is ignored, as it should be)."""

  preceding_angle_bracket_index = cursor_offset
  while True:
    if preceding_angle_bracket_index < 0:
      return cursor_offset
    char = sanitized_html[ preceding_angle_bracket_index ]
    if preceding_angle_bracket_index != cursor_offset and char == '>':
      # Not inside a tag, no need for adaptation
      return cursor_offset

    if char == '<':
      break
    preceding_angle_bracket_index -= 1

  tag = Tag( TAG_REGEX.match( sanitized_html,
                              preceding_angle_bracket_index ) )
  if not tag:
    return cursor_offset

  if tag.kind == TagType.OPENING:
    return tag.end_offset
  return tag.start_offset


def LocationsOfEnclosingTags( input_html, cursor_line, cursor_column ):
  bad_result = ( 0, 0, 0, 0 )
  try:
    sanitized_html = PacifyHtmlComments( input_html )
    cursor_offset = OffsetForLineColumnInString( sanitized_html,
                                                 cursor_line,
                                                 cursor_column )
    if cursor_offset == None:
      return bad_result

    adapted_cursor_offset = AdaptCursorOffsetIfNeeded( sanitized_html,
                                                       cursor_offset )
    opening_tag, closing_tag = GetOpeningAndClosingTags( sanitized_html,
                                                         adapted_cursor_offset )

    if not opening_tag or not closing_tag:
      return bad_result

    opening_tag_line, opening_tag_column = LineColumnForOffsetInString(
      sanitized_html,
      opening_tag.start_offset )

    closing_tag_line, closing_tag_column = LineColumnForOffsetInString(
      sanitized_html,
      closing_tag.start_offset )

    return ( opening_tag_line,
             opening_tag_column,
             closing_tag_line,
             closing_tag_column )
  except Exception:
    return bad_result


########NEW FILE########
__FILENAME__ = mta_vim
#!/usr/bin/env python
#
# Copyright (C) 2012  Strahinja Val Markovic  <val@markovic.io>
#
# This file is part of MatchTagAlways.
#
# MatchTagAlways is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# MatchTagAlways is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with MatchTagAlways.  If not, see <http://www.gnu.org/licenses/>.

import mta_core
import vim

def CurrentLineAndColumn():
  """Returns the 1-based current line and 1-based current column."""
  line, column = vim.current.window.cursor
  column += 1
  return line, column


def CanAccessCursorColumn( cursor_column ):
  try:
    # The passed-in cursor_column is 1-based, vim.current.line is 0-based
    vim.current.line[ cursor_column - 1 ]
    return True
  except IndexError:
    return False


def LocationOfEnclosingTagsInWindowView():
  # 1-based line numbers
  first_window_line = int( vim.eval( "line('w0')" ) )
  last_window_line = int( vim.eval( "line('w$')" ) )

  # -1 because vim.current.buffer is 0-based whereas vim lines are 1-based
  visible_text = '\n'.join(
    vim.current.buffer[ first_window_line -1 : last_window_line ] )

  cursor_line, cursor_column = CurrentLineAndColumn()
  adapted_cursor_line = cursor_line - first_window_line + 1

  if not CanAccessCursorColumn( cursor_column ):
    # We need to do this because when the cursor is on the last column in insert
    # mode, that column *doesn't exist yet*. Not until the user actually types
    # something in and moves the cursor forward.
    cursor_column -= 1

  ( opening_tag_line,
    opening_tag_column,
    closing_tag_line,
    closing_tag_column ) = mta_core.LocationsOfEnclosingTags(
      visible_text,
      adapted_cursor_line,
      cursor_column )

  return [ opening_tag_line + first_window_line - 1,
           opening_tag_column,
           closing_tag_line + first_window_line - 1,
           closing_tag_column ]


########NEW FILE########
__FILENAME__ = mta_core_test
#!/usr/bin/env python
#
# Copyright (C) 2012  Strahinja Val Markovic  <val@markovic.io>
#
# This file is part of MatchTagAlways.
#
# MatchTagAlways is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# MatchTagAlways is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with MatchTagAlways.  If not, see <http://www.gnu.org/licenses/>.

from nose.tools import eq_
from .. import mta_core


def LineColumnOffsetConversions_Basic_test():
  text = "foo"
  eq_( 2, mta_core.OffsetForLineColumnInString( text, 1, 3 ) )
  eq_( (1, 3), mta_core.LineColumnForOffsetInString( text, 2 ) )


def LineColumnOffsetConversions_BasicMultiLine_test():
  text = "foo\nbar"
  eq_( 6, mta_core.OffsetForLineColumnInString( text, 2, 3 ) )
  eq_( (2, 3), mta_core.LineColumnForOffsetInString( text, 6 ) )


def LineColumnOffsetConversions_ComplexMultiLine_test():
  text = "foo\nbar\nqux the thoeu \n\n\n aa "
  eq_( 8, mta_core.OffsetForLineColumnInString( text, 3, 1 ) )
  eq_( 21, mta_core.OffsetForLineColumnInString( text, 3, 14 ) )
  eq_( 25, mta_core.OffsetForLineColumnInString( text, 6, 1 ) )

  eq_( (3, 1), mta_core.LineColumnForOffsetInString( text, 8 ) )
  eq_( (3, 14), mta_core.LineColumnForOffsetInString( text, 21 ) )
  eq_( (6, 1), mta_core.LineColumnForOffsetInString( text, 25 ) )


def LineColumnOffsetConversions_EmtpyLine_test():
  # Vim allows the user to stop on an empty line and declares that column 1
  # exists even when there are no characters on that line
  text = "foo\nbar\nqux the thoeu \n\n\n aa "
  eq_( 23, mta_core.OffsetForLineColumnInString( text, 5, 1 ) )


def LineColumnOffsetConversions_FailOnEmptyString_test():
  text = ""
  eq_( None, mta_core.OffsetForLineColumnInString( text, 1, 3 ) )
  eq_( (None, None), mta_core.LineColumnForOffsetInString( text, 2 ) )


def LineColumnOffsetConversions_FailLineOutOfRange_test():
  text = "foo\nbar\nqux the thoeu \n\n\n aa "
  eq_( None, mta_core.OffsetForLineColumnInString( text, 10, 3 ) )
  eq_( (None, None), mta_core.LineColumnForOffsetInString( text, 100 ) )


def LineColumnOffsetConversions_FailColumnOutOfRange_test():
  text = "foo\nbar\nqux the thoeu \n\n\n aa "
  # eq_( None, mta_core.OffsetForLineColumnInString( text, 2, 0 ) )
  eq_( None, mta_core.OffsetForLineColumnInString( text, 2, 5 ) )
  eq_( None, mta_core.OffsetForLineColumnInString( text, 2, 4 ) )

  eq_( (None, None), mta_core.LineColumnForOffsetInString( text, 3 ) )
  eq_( (None, None), mta_core.LineColumnForOffsetInString( text, 7 ) )
  eq_( (None, None), mta_core.LineColumnForOffsetInString( text, 22 ) )


def TAG_REGEX_Works_test():
  eq_(
    {
      'start_slash' : None,
      'tag_name' : 'div',
      'end_slash' : None,
    },
    mta_core.TAG_REGEX.match( "<div>" ).groupdict() )

  eq_(
    {
      'start_slash' : None,
      'tag_name' : 'p',
      'end_slash' : None,
    },
    mta_core.TAG_REGEX.match( "< p \n\n id='xx' \nclass='b'>" ).groupdict() )

  eq_(
    {
      'start_slash' : None,
      'tag_name' : 'foo:bar-goo',
      'end_slash' : None,
    },
    mta_core.TAG_REGEX.match( "<foo:bar-goo>" ).groupdict() )

  eq_(
    {
      'start_slash' : '/',
      'tag_name' : 'p',
      'end_slash' : None,
    },
    mta_core.TAG_REGEX.match( "</p>" ).groupdict() )

  eq_(
    {
      'start_slash' : '/',
      'tag_name' : 'p',
      'end_slash' : None,
    },
    mta_core.TAG_REGEX.match( "<\n/  p>" ).groupdict() )

  eq_(
    {
      'start_slash' : None,
      'tag_name' : 'br',
      'end_slash' : '/',
    },
    mta_core.TAG_REGEX.match( "< br \n\n id='xx' \nclass='b' />" ).groupdict() )


def PacifyHtmlComments_Works_test():
  eq_( 'foo xxxx xxxxx \txxx \n xxxxxx xxxxx xxx',
       mta_core.PacifyHtmlComments(
         'foo <!-- <div> \tfoo \n </div> <br/> -->' ) )


def GetPreviousUnmatchedOpeningTag_Simple_test():
  html = "<div> foo"
  eq_( 0, mta_core.GetPreviousUnmatchedOpeningTag( html, 6 ).start_offset )


def GetPreviousUnmatchedOpeningTag_Nested_test():
  html = "<div><div></div> foo "
  eq_( 0, mta_core.GetPreviousUnmatchedOpeningTag( html, 17 ).start_offset )

  html = "<div><div><p></p> foo "
  eq_( 5, mta_core.GetPreviousUnmatchedOpeningTag( html, 18 ).start_offset )


def GetPreviousUnmatchedOpeningTag_NestedMultiLine_test():
  html = "<div>\n<div\n></div> foo "
  eq_( 0, mta_core.GetPreviousUnmatchedOpeningTag( html, 20 ).start_offset )

  html = "<\ndiv>\n<div><br/><p>\n\n</p> foo "
  eq_( 7, mta_core.GetPreviousUnmatchedOpeningTag( html, 27 ).start_offset )


def GetPreviousUnmatchedOpeningTag_OnAngleBracket_test():
  html = "<div>x"
  eq_( 0, mta_core.GetPreviousUnmatchedOpeningTag( html, 5 ).start_offset )
  eq_( None, mta_core.GetPreviousUnmatchedOpeningTag( html, 4 ) )


def GetPreviousUnmatchedOpeningTag_OrphanOpeningTag_test():
  html = "<div><p><i><br></i></p>x"
  eq_( 0, mta_core.GetPreviousUnmatchedOpeningTag( html, 23 ).start_offset )


def GetNextUnmatchedClosingTag_NoOpeningTagFail_test():
  html = "foobar"
  eq_( None, mta_core.GetPreviousUnmatchedOpeningTag( html, 3 ) )

  html = "<!DOCTYPE>"
  eq_( None, mta_core.GetPreviousUnmatchedOpeningTag( html, 3 ) )

  html = "</div>"
  eq_( None, mta_core.GetPreviousUnmatchedOpeningTag( html, 3 ) )

  html = "</div> foo"
  eq_( None, mta_core.GetPreviousUnmatchedOpeningTag( html, 7 ) )

  html = "</div><br/></div> foo "
  eq_( None, mta_core.GetPreviousUnmatchedOpeningTag( html, 18 ) )

  html = "<\n/div>\n<div/><br/><p/>\n\n</p> foo "
  eq_( None, mta_core.GetPreviousUnmatchedOpeningTag( html, 30 ) )


def GetNextUnmatchedClosingTag_Simple_test():
  html = "foo </div>"
  eq_( 4, mta_core.GetNextUnmatchedClosingTag( html, 0 ).start_offset )


def GetNextUnmatchedClosingTag_Nested_test():
  html = "foo <div></div></div>"
  eq_( 15, mta_core.GetNextUnmatchedClosingTag( html, 0 ).start_offset )

  html = "foo <div><br/></div></div>"
  eq_( 20, mta_core.GetNextUnmatchedClosingTag( html, 0 ).start_offset )

  html = "foo <\ndiv><\n\nbr/></div></div>"
  eq_( 23, mta_core.GetNextUnmatchedClosingTag( html, 0 ).start_offset )


def GetNextUnmatchedClosingTag_NoClosingTagFail_test():
  html = "foobar"
  eq_( None, mta_core.GetNextUnmatchedClosingTag( html, 0 ) )

  html = "<!DOCTYPE>"
  eq_( None, mta_core.GetNextUnmatchedClosingTag( html, 0 ) )

  html = "<div>"
  eq_( None, mta_core.GetNextUnmatchedClosingTag( html, 0 ) )

  html = "foo <div>"
  eq_( None, mta_core.GetNextUnmatchedClosingTag( html, 0 ) )

  html = "foo <div><br/><div>"
  eq_( None, mta_core.GetNextUnmatchedClosingTag( html, 0 ) )

  html = "foo <\ndiv>\n<div/><br/><p/>\n\n<p>"
  eq_( None, mta_core.GetNextUnmatchedClosingTag( html, 0 ) )


def GetNextUnmatchedClosingTag_OnAngleBracket_test():
  html = "x</div>"
  eq_( 1, mta_core.GetNextUnmatchedClosingTag( html, 0 ).start_offset )
  eq_( 1, mta_core.GetNextUnmatchedClosingTag( html, 1 ).start_offset )
  eq_( None, mta_core.GetNextUnmatchedClosingTag( html, 2 ) )


def GetNextUnmatchedClosingTag_OrphanOpeningTag_test():
  html = "x<p><i><br></i></p></div>"
  eq_( 19, mta_core.GetNextUnmatchedClosingTag( html, 0 ).start_offset )

  html = "x<p><i><br></i></p><br></div>"
  eq_( 23, mta_core.GetNextUnmatchedClosingTag( html, 0 ).start_offset )


def LocationsOfEnclosingTags_Basic_test():
  html = "<div> foo </div>"
  eq_( ( 1, 1, 1, 11 ), mta_core.LocationsOfEnclosingTags( html, 1, 7 ) )


def LocationsOfEnclosingTags_Nested_test():
  html = "<div><p><br/></p> foo </div>"
  eq_( ( 1, 1, 1, 23 ), mta_core.LocationsOfEnclosingTags( html, 1, 19 ) )


def LocationsOfEnclosingTags_MultiLine_test():
  html = "<\ndiv><\n\np>\n<br/></p>\n foo </div>"
  eq_( ( 1, 1, 6, 6 ), mta_core.LocationsOfEnclosingTags( html, 6, 2 ) )

  html = "<\ndiv><\n\np>\n<br/></p>\n foo <\ta>\tbar\n<br/><\n/a> </div>"
  eq_( ( 1, 1, 8, 5 ), mta_core.LocationsOfEnclosingTags( html, 6, 2 ) )


def LocationsOfEnclosingTags_Comments_test():
  html = "<div><p><!-- <div> --><br/></p> foo </div>"
  eq_( ( 1, 1, 1, 37 ), mta_core.LocationsOfEnclosingTags( html, 1, 34 ) )


def LocationsOfEnclosingTags_CursorInTag_test():
  html = "<\ndiv\t \nid='foo' \n>baz <p>qux<br/></p></div>"
  eq_( ( 1, 1, 4, 21 ), mta_core.LocationsOfEnclosingTags( html, 3, 2 ) )


def LocationsOfEnclosingTags_CursorInTagFull_test():
  html = "<div></div>"
  def gen( column ):
    eq_( ( 1, 1, 1, 6 ), mta_core.LocationsOfEnclosingTags( html, 1, column ) )

  for i in xrange( 1, len( html ) + 1 ):
    yield gen, i


def LocationsOfEnclosingTags_UnbalancedOpeningTag_test():
  # this is the reason why we need to continue looking for a different opening
  # tag if the closing tag we found does not match
  html = "<ul><li>foo</ul>"
  eq_( ( 1, 1, 1, 12 ), mta_core.LocationsOfEnclosingTags( html, 1, 9 ) )

  html = "<ul><li></ul></ul>"
  eq_( ( 1, 1, 1, 9 ), mta_core.LocationsOfEnclosingTags( html, 1, 1 ) )

  # this is the reason why we need to be able to skip over orphan open tags
  html = "<ul><ul><li></ul>x<ul><li></ul>\n</ul>"
  eq_( ( 1, 1, 2, 1 ), mta_core.LocationsOfEnclosingTags( html, 1, 2 ) )
  eq_( ( 1, 1, 2, 1 ), mta_core.LocationsOfEnclosingTags( html, 1, 18 ) )


def LocationsOfEnclosingTags_UnbalancedOpeningTagFull_test():
  html = "<ul><li>foo</ul>"
  def gen( column ):
    eq_( ( 1, 1, 1, 12 ), mta_core.LocationsOfEnclosingTags( html, 1, column ) )

  for i in xrange( 1, len( html ) + 1 ):
    yield gen, i


def LocationsOfEnclosingTags_Fail_test():
  html = ""
  eq_( ( 0, 0, 0, 0 ), mta_core.LocationsOfEnclosingTags( html, 1, 2 ) )

  html = "foo bar baz qux"
  eq_( ( 0, 0, 0, 0 ), mta_core.LocationsOfEnclosingTags( html, 1, 8 ) )

  html = "<div>"
  eq_( ( 0, 0, 0, 0 ), mta_core.LocationsOfEnclosingTags( html, 1, 2 ) )

  html = "</div>"
  eq_( ( 0, 0, 0, 0 ), mta_core.LocationsOfEnclosingTags( html, 1, 2 ) )

  html = "<div></div>"
  eq_( ( 0, 0, 0, 0 ), mta_core.LocationsOfEnclosingTags( html, 10, 10 ) )
  eq_( ( 0, 0, 0, 0 ), mta_core.LocationsOfEnclosingTags( html, 1, 20 ) )

  html = "<div><div>"
  eq_( ( 0, 0, 0, 0 ), mta_core.LocationsOfEnclosingTags( html, 1, 5 ) )

  html = "<div><br/><div>"
  eq_( ( 0, 0, 0, 0 ), mta_core.LocationsOfEnclosingTags( html, 1, 8 ) )

  html = "</div><div/>"
  eq_( ( 0, 0, 0, 0 ), mta_core.LocationsOfEnclosingTags( html, 1, 5 ) )

  html = "</div></div>"
  eq_( ( 0, 0, 0, 0 ), mta_core.LocationsOfEnclosingTags( html, 1, 5 ) )

  html = "<div></foo>"
  eq_( ( 0, 0, 0, 0 ), mta_core.LocationsOfEnclosingTags( html, 1, 5 ) )

########NEW FILE########
