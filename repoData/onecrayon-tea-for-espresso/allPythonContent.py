__FILENAME__ = espresso
'''Automatic retrieval of the standard Espresso classes'''

import objc

MRRangeSet = objc.lookUpClass('MRRangeSet')
CETextRecipe = objc.lookUpClass('CETextRecipe')
CETextSnippet = objc.lookUpClass('CETextSnippet')
SXSelectorGroup = objc.lookUpClass('SXSelectorGroup')
########NEW FILE########
__FILENAME__ = html_replace
'''
Registers a special handler for named HTML entities

Usage:
import html_replace
text = u'Some string with Unicode characters'
text = text.encode('ascii', 'html_replace')
'''

import codecs
from htmlentitydefs import codepoint2name

def html_replace(text):
    if isinstance(text, (UnicodeEncodeError, UnicodeTranslateError)):
        s = []
        for c in text.object[text.start:text.end]:
            if ord(c) in codepoint2name:
                s.append(u'&%s;' % codepoint2name[ord(c)])
            else:
                s.append(u'&#%s;' % ord(c))
        return ''.join(s), text.end
    else:
        raise TypeError("Can't handle %s" % text.__name__)
codecs.register_error('html_replace', html_replace)

########NEW FILE########
__FILENAME__ = persistent_re
'''
Class that enables persistent regex evaluations

Usage:
gre = persistent_re()

if gre.match(r'foo', text):
    # do something with gre.last, which is an re MatchObject
'''

import re

class persistent_re(object):
    def __init__(self):
        self.last = None
    def match(self, pattern, text):
        self.last = re.match(pattern, text)
        return self.last
    def search(self, pattern, text):
        self.last = re.search(pattern, text)
        return self.last

########NEW FILE########
__FILENAME__ = TEAPythonLoader
'''
The class responsible for loading the action and interacting with the
TEAforEspresso class
'''

from Foundation import *
import objc

from tea_utils import load_action

class TEAPythonLoader(NSObject):
    @objc.signature('B@:@@')
    def actInContext_forAction_(self, context, actionObject):
        '''This actually performs the Python action'''
        # Grab variables from the actionObject
        action = actionObject.action()
        paths = actionObject.supportPaths()
        
        if actionObject.options() is not None:
            # In order to pass dictionary as keyword arguments it has to:
            # 1) be a Python dictionary
            # 2) have the key encoded as a string
            # This dictionary comprehension takes care of both issues
            options = dict(
                [str(arg), value] \
                for arg, value in actionObject.options().iteritems()
            )
        else:
            options = None
        
        # Find and run the action
        target_module = load_action(action, *paths)
        if target_module is None:
            # Couldn't find the module, log the error
            NSLog('TEA: Could not find the module ' + action)
            return False
        
        # We may need to pass the action object as the second argument
        if "req_action_object" in target_module.__dict__ and \
           target_module.req_action_object:
            if options is not None:
                return target_module.act(context, actionObject, **options)
            else:
                return target_module.act(context, actionObject)
        elif options is not None:
            # We've got options, pass them as keyword arguments
            return target_module.act(context, **options)
        else:
            return target_module.act(context)

########NEW FILE########
__FILENAME__ = tea_actions
'''Utility functions for working with TEA for Espresso'''

import re
from types import StringTypes

from Foundation import *

from espresso import *
import html_replace

# ===============================================================
# Interact with the user and output information
# ===============================================================

def say(context, title, message,
        main_button=None, alt_button=None, other_button=None):
    '''Displays a dialog with a message for the user'''
    alert = NSAlert.alertWithMessageText_defaultButton_alternateButton_otherButton_informativeTextWithFormat_(
        title,
        main_button,
        alt_button,
        other_button,
        message
    )
    if context.windowForSheet() is not None:
        return alert.beginSheetModalForWindow_modalDelegate_didEndSelector_contextInfo_(
            context.windowForSheet(), None, None, None
        )
    else:
        return alert.runModal()

def log(message):
    '''
    Convenience function for logging messages to console
    
    Please make sure they are strings before you try to log them; wrap
    anything you aren't sure of in str()
    '''
    NSLog(str(message))

# ===============================================================
# Preference lookup shortcuts
# ===============================================================

def get_prefs(context):
    '''
    Convenience function; returns the CETextPreferences object with
    current preferences
    '''
    return context.textPreferences()

def get_line_ending(context):
    '''Shortcut function to get the line-endings for the context'''
    prefs = get_prefs(context)
    return prefs.lineEndingString()

def get_indentation_string(context):
    '''Shortcut to retrieve the indentation string'''
    prefs = get_prefs(context)
    return prefs.tabString()

def get_xhtml_closestring():
    '''Retrieves the XHTML closing string (based on user preferences)'''
    defaults = NSUserDefaults.standardUserDefaults()
    return defaults.stringForKey_('TEASelfClosingString')

# ===============================================================
# Text manipulations and helper functions
# ===============================================================

def parse_word(selection):
    '''
    Extract the first word from a string
    
    Returns the word:
    parse_word('p class="stuff"') => word = 'p'
    '''
    matches = re.match(r'(([a-zA-Z0-9_-]+)\s*.*)$', selection)
    if matches == None:
        return None
    return matches.group(2)

def string_to_tag(string):
    '''
    Parses a string into a tag with id and class attributes
    
    For example, div#stuff.good.things translates into
    `div id="stuff" class="good things"`
    '''
    if string.find('#') > 0 or string.find('.') > 0:
        match = re.search('#([a-zA-Z0-9_-]+)', string)
        if match:
            id = match.group(1)
        else:
            id = False
        matches = re.findall('\.([a-zA-Z0-9_-]+)', string)
        classes = ''
        for match in matches:
            if classes:
                classes += ' '
            classes += match
        tag = parse_word(string)
        if id:
            tag += ' id="' + id + '"'
        if classes:
            tag += ' class="' + classes + '"'
        return tag
    else:
        return string

def is_selfclosing(tag):
    '''Checks a tag and returns True if it's a self-closing XHTML tag'''
    # For now, we're just checking off a list
    selfclosing = ['img', 'input', 'br', 'hr', 'link', 'base', 'meta']
    # Make sure we've just got the tag
    if not tag.isalnum():
        tag = parse_word(tag)
        if tag is None:
            return False
    return tag in selfclosing

def get_tag_closestring(context):
    '''
    Tries to determine if the current context is XHTML or not, and
    returns the proper string for self-closing tags
    '''
    # Currently doesn't run any logic; just defaults to user prefs
    defaults = NSUserDefaults.standardUserDefaults()
    use_xhtml = defaults.boolForKey_('TEADefaultToXHTML')
    if not use_xhtml:
        return ''
    return get_xhtml_closestring()

def encode_ampersands(text, enc='&amp;'):
    '''Encodes ampersands'''
    return re.sub('&(?!([a-zA-Z0-9]+|#[0-9]+|#x[0-9a-fA-F]+);)', enc, text)

def named_entities(text):
    '''Converts Unicode characters into named HTML entities'''
    text = text.encode('ascii', 'html_replace')
    return encode_ampersands(text)

def numeric_entities(text, ampersands=None):
    '''Converts Unicode characters into numeric HTML entities'''
    text = text.encode('ascii', 'xmlcharrefreplace')
    if ampersands == 'numeric':
        return encode_ampersands(text, '&#38;')
    elif ampersands == 'named':
        return encode_ampersands(text)
    else:
        return text

def entities_to_hex(text, wrap):
    '''
    Converts HTML entities into hexadecimal; replaces $HEX in wrap
    with the hex code
    '''
    # This is a bit of a hack to make the variable available to the function
    wrap = [wrap]
    def wrap_hex(match):
        hex = '%X' % int(match.group(2))
        while len(hex) < 4:
            hex = '0' + hex
        return wrap[0].replace('$HEX', hex)
    return re.sub(r'&(#x?)?([0-9]+|[0-9a-fA-F]+);', wrap_hex, text)

def trim(context, text, lines=True, sides='both', respect_indent=False,
         preserve_linebreaks=True):
    '''
    Trims whitespace from the text
    
    If lines=True, will trim each line in the text.
    
    sides can be both, start, or end and dictates where trimming occurs.
    
    If respect_indent=True, indent characters at the start of lines will be
    left alone (specific character determined by preferences)
    '''
    def trimit(text, sides, indent, preserve_linebreaks):
        '''Utility function for trimming the text'''
        # Preserve the indent if an indent string is passed in
        if (sides == 'both' or sides == 'start') and indent != '':
            match = re.match('(' + indent + ')+', text)
            if match:
                indent_chars = match.group(0)
            else:
                indent_chars = ''
        else:
            indent_chars = ''
        # Preserve the linebreaks at the end if needed
        match = re.search(r'[\n\r]+$', text)
        if match and preserve_linebreaks:
            linebreak = match.group(0)
        else:
            linebreak = ''
        # Strip that whitespace!
        if sides == 'start':
            text = text.lstrip()
        elif sides == 'end':
            text = text.rstrip()
        else:
            text = text.strip()
        return indent_chars + text + linebreak
    
    # Set up which characters to treat as indent
    if respect_indent:
        indent = get_indentation_string(context)
    else:
        indent = ''
    finaltext = ''
    if lines:
        for line in text.splitlines(True):
            finaltext += trimit(line, sides, indent, preserve_linebreaks)
    else:
        finaltext = trimit(text, sides, indent, preserve_linebreaks)
    return finaltext

def unix_line_endings(text):
    '''Converts all line endings to Unix'''
    if text.find('\r\n') != -1:
        text = text.replace('\r\n','\n')
    if text.find('\r') != -1:
        text = text.replace('\r','\n')
    return text

def clean_line_endings(context, text, line_ending=None):
    '''
    Converts all line endings to the default line ending of the file,
    or if line_ending is specified uses that
    '''
    text = unix_line_endings(text)
    if line_ending is None:
        target = get_line_ending(context)
    else:
        target = line_ending
    return text.replace('\n', target)

# ===============================================================
# Espresso object convenience methods
# ===============================================================

def new_range_set(context):
    '''
    Convenience function; returns the MRRangeSet for the selection in
    the current context
    
    For range set methods, see Espresso.app/Contents/Headers/MRRangeSet.h
    '''
    return MRRangeSet.alloc().initWithRangeValues_(context.selectedRanges())

def new_recipe():
    '''
    Convenience function to create a new text recipe
    
    For recipe methods, see Espresso.app/Contents/Headers/EspressoTextCore.h
    '''
    return CETextRecipe.textRecipe()

def new_snippet(snippet):
    '''
    Initializes a string as a CETextSnippet object
    '''
    return CETextSnippet.snippetWithString_(snippet)

# ===============================================================
# Working with ranges and selected text
# ===============================================================

def new_range(location, length):
    '''Convenience function for creating an NSRange'''
    return NSMakeRange(location, length)

def get_ranges(context):
    '''
    Convenience function to get a list of all ranges in the document
    
    Automatically cleans them up into NSRanges from NSConcreateValues
    '''
    ranges = context.selectedRanges()
    return [range.rangeValue() for range in ranges]

def get_first_range(context):
    '''
    Shortcut function to snag the first selection in the document;
    guaranteed to be at least one because the cursor is a range
    '''
    ranges = get_ranges(context)
    return ranges[0]

def get_selection(context, range):
    '''Convenience function; returns selected text within a given range'''
    return context.string().substringWithRange_(range)

def get_line(context, range):
    '''Returns the line bounding range.location'''
    linerange = context.lineStorage().lineRangeForIndex_(range.location)
    return get_selection(context, linerange), linerange

def set_selected_range(context, range):
    '''Sets the selection to the single range passed as an argument'''
    context.setSelectedRanges_([NSValue.valueWithRange_(range)])

def get_single_range(context, with_errors=False):
    '''
    Returns the range of a single selection, or throws an optional
    error if there are multiple selections
    '''
    ranges = context.selectedRanges()
    # Since there aren't good ways to deal with discontiguous selections
    # verify that we're only working with a single selection
    if len(ranges) != 1:
        if with_errors:
            say(
                context, "Error: multiple selections detected",
                "You must have a single selection in order to use this action."
            )
        return None
    # Range is not an NSConcreteValue b/c it's stored in an array
    # This converts it to an NSRange which we can work with
    return ranges[0].rangeValue()

def get_single_selection(context, with_errors=False):
    '''
    If there's a single selection, returns the selected text,
    otherwise throws optional descriptive errors
    
    Returns a tuple with the selected text first and its range second
    '''
    range = get_single_range(context, with_errors)
    if range == None:
        # More than one range, apparently
        return None, None
    if range.length is 0:
        if with_errors:
            say(
                context, "Error: selection required",
                "You must select some text in order to use this action."
            )
        return None, range
    return get_selection(context, range), range

def get_character(context, range):
    '''Returns the character immediately preceding the cursor'''
    if range.location > 0:
        range = new_range(range.location - 1, 1)
        return get_selection(context, range), range
    else:
        return None, range

def get_word(context, range, alpha_numeric=True, extra_characters='_-',
             bidirectional=True):
    '''
    Selects and returns the current word and its range from the passed range
    
    By default it defines a word as a contiguous string of alphanumeric
    characters plus extra_characters. Setting alpha_numeric to False will
    define a word as a contiguous string of alphabetic characters plus
    extra_characters
    
    If bidirectional is False, then it will only look behind the cursor
    '''
    # Helper regex for determining if line ends with a tag
    # Includes checks for ASP/PHP/JSP/ColdFusion closing delimiters
    re_tag = re.compile(r'(<\/?[\w:-]+[^>]*|\s*(/|\?|%|-{2,3}))>$')
    
    def test_word():
        # Mini-function to cut down on code bloat
        if alpha_numeric:
            return all(c.isalnum() or c in extra_characters for c in char)
        else:
            return all(char.isalpha() or c in extra_characters for c in char)
    
    def ends_with_tag(cur_index):
        # Mini-function to check if line to index ends with a tag
        linestart = context.lineStorage().lineStartIndexLessThanIndex_(cur_index)
        text = get_selection(
            context, new_range(linestart, cur_index - linestart + 1)
        )
        return re_tag.search(text) != None
    
    # Set up basic variables
    index = range.location
    word = ''
    maxlength = context.string().length()
    if bidirectional:
        # Make sure the cursor isn't at the end of the document
        if index != maxlength:
            # Check if cursor is mid-word
            char = get_selection(context, new_range(index, 1))
            if test_word():
                inword = True
                # Parse forward until we hit the end of word or document
                while inword:
                    char = get_selection(context, new_range(index, 1))
                    if test_word():
                        word += char
                    else:
                        inword = False
                    index += 1
                    if index == maxlength:
                        inword = False
            else:
                # lastindex logic assumes we've been incrementing as we go,
                # so bump it up one to compensate
                index += 1
        lastindex = index - 1 if index < maxlength else index
    else:
        # Only parsing backward, so final index is cursor
        lastindex = range.location
    # Reset index to one less than the cursor
    index = range.location - 1
    # Only walk backwards if we aren't at the beginning
    if index >= 0:
        # Parse backward to get the word ahead of the cursor
        inword = True
        while inword:
            char = get_selection(context, new_range(index, 1))
            if test_word() and not (char == '>' and ends_with_tag(index)):
                word = char + word
                index -= 1
            else:
                inword = False
            if index < 0:
                inword = False
    # Since index is left-aligned and we've overcompensated,
    # need to increment +1
    firstindex = index + 1
    # Switch last index to length for use in range
    lastindex = lastindex - firstindex
    range = new_range(firstindex, lastindex)
    return word, range

def get_word_or_selection(context, range, alpha_numeric=True,
                          extra_characters='_-', bidirectional=True):
    '''
    Selects and returns the current word and its range from the passed range,
    or if there's already a selection returns the contents and its range
    
    See get_word() for an explanation of the extra arguments
    '''
    if range.length == 0:
        return get_word(context, range, alpha_numeric, extra_characters, bidirectional)
    else:
        return get_selection(context, range), range

# ===============================================================
# Syntax zone methods
# ===============================================================

def get_root_zone(context):
    '''
    DEPRECATED: use select_from_zones instead
    
    Returns the string identifier of the current root zone'''
    # This is terrible, but I can't find a good way to detect
    # if the object is null
    if context.syntaxTree().rootZone().typeIdentifier() is not None:
        return context.syntaxTree().rootZone().typeIdentifier().stringValue()
    else:
        return False

def get_active_zone(context, range):
    '''Returns the textual zone ID immediately under the cursor'''
    if context.syntaxTree().zoneAtCharacterIndex_(range.location) is not None:
        if context.syntaxTree().zoneAtCharacterIndex_(range.location).\
           typeIdentifier() is not None:
            return context.syntaxTree().zoneAtCharacterIndex_(range.location).\
                   typeIdentifier().stringValue()
    # Made it here, something's wrong
    return False

def select_from_zones(context, range=None, default=None, **syntaxes):
    '''
    Checks the keys in **syntaxes to see what matches the active zone,
    and returns that item's contents, or default if no match
    '''
    if range is None:
        range = get_single_range(context)
    for key, value in syntaxes.iteritems():
        selectors = SXSelectorGroup.selectorGroupWithString_(key)
        if context.string().length() == range.location:
            zone = context.syntaxTree().rootZone()
        else:
            zone = context.syntaxTree().rootZone().zoneAtCharacterIndex_(
                range.location
            )
        if selectors.matches_(zone):
            return value
    
    # If we reach this point, there's no match
    return default

def range_in_zone(context, range, selector):
    '''
    Tests the location of the range to see if it matches the provided
    zone selector string
    '''
    target = SXSelectorGroup.selectorGroupWithString_(selector)
    if context.string().length() == range.location:
        zone = context.syntaxTree().rootZone()
    else:
        zone = context.syntaxTree().rootZone().zoneAtCharacterIndex_(
            range.location
        )
    return target.matches_(zone)

def cursor_in_zone(context, selector):
    '''
    Tests the location of the range to see if it matches the provided
    zone selector string
    '''
    ranges = get_ranges(context)
    return range_in_zone(context, ranges[0], selector)

# ===============================================================
# Itemizer methods
# ===============================================================

def get_item_for_range(context, range):
    '''Returns the smallest item containing the given range'''
    return context.itemizer().smallestItemContainingCharacterRange_(range)

def get_item_parent_for_range(context, range):
    '''Returns the parent of the item containing the given range'''
    item = get_item_for_range(context, range)
    if item is None:
        return None
    new_range = item.range()
    # Select the parent if the range is the same
    while(item.parent() and (new_range.location == range.location and \
          new_range.length == range.length)):
        item = item.parent()
        new_range = item.range()
    return item

# ===============================================================
# Snippet methods
# ===============================================================

def sanitize_for_snippet(text):
    '''
    Escapes special characters used by snippet syntax
    '''
    text = text.replace('$', '\$')
    text = text.replace('{', '\{')
    text = text.replace('}', '\}')
    return text.replace('`', '\`')

def construct_snippet(text, snippet, parse_new_vars=False):
    '''
    Constructs a simple snippet by replacing $EDITOR_SELECTION with
    sanitized text
    '''
    if text is None:
        text = ''
    text = sanitize_for_snippet(text)
    if parse_new_vars:
        snippet = snippet.replace('$EDITOR_SELECTION', text)
    return snippet.replace('$SELECTED_TEXT', text)

def indent_snippet(context, snippet, range):
    '''
    DEPRECATED: PLEASE USE ESPRESSO'S BUILT-IN SNIPPET INDENTATION INSTEAD
    
    Sets a snippet's indentation level to match that of the line starting
    at the location of range
    '''
    # Are there newlines?
    if re.search(r'[\n\r]', snippet) is not None:
        # Check if line is indented
        line = context.lineStorage().lineRangeForIndex_(range.location)
        # Check if line is actually indented
        if line.location != range.location:
            line = get_selection(context, line)
            match = re.match(r'([ \t]+)', line)
            # Only indent if the line starts with whitespace
            if match is not None:
                current_indent = match.group(1)
                indent_string = get_indentation_string(context)
                # Convert tabs to indent_string and indent each line
                if indent_string != '\t':
                    snippet = snippet.replace('\t', indent_string)
                lines = snippet.splitlines(True)
                # Convert to iterator so we can avoid processing item 0
                lines = iter(lines)
                snippet = lines.next()
                for line in lines:
                    snippet += current_indent + line
                if re.search(r'[\n\r]$', snippet) is not None:
                    # Ends with a newline, add the indent
                    snippet += current_indent
    return snippet

# ===============================================================
# Insertion methods
# ===============================================================

def insert_text_over_range(context, text, range, undo_name=None):
    '''Immediately replaces the text at range with passed in text'''
    insertions = new_recipe()
    insertions.addReplacementString_forRange_(text, range)
    if undo_name != None:
        insertions.setUndoActionName_(undo_name)
    return context.applyTextRecipe_(insertions)

def insert_snippet(context, snippet, indent=True):
    '''
    Convenience function to insert a text snippet
    
    Make sure to set the selection intelligently before calling this
    '''
    # Need context to get the tag closestring, so we do it here
    snippet = snippet.replace('$E_XHTML', get_tag_closestring(context))
    if type(snippet) in StringTypes:
        snippet = new_snippet(snippet)
    if indent:
        return context.insertTextSnippet_(snippet)
    else:
        return context.insertTextSnippet_options_(snippet, 0)

def insert_snippet_over_range(context, snippet, range, undo_name=None, indent=True):
    '''Replaces text at range with a text snippet'''
    if range.length is not 0:
        # Need to first delete the text under the range
        deletions = new_recipe()
        deletions.addDeletedRange_(range)
        if undo_name != None:
            deletions.setUndoActionName_(undo_name)
        # Apply the deletions
        context.applyTextRecipe_(deletions)
    # Insert the snippet
    return insert_snippet(context, snippet, indent)

########NEW FILE########
__FILENAME__ = tea_utils
'''
This module includes common utility functions for working with
TEA actions

Most common usage is to find and load TEA actions
'''

import imp
import sys
import os

from Foundation import *

def load_action(target, *roots):
    '''
    Imports target TEA action file and returns it as a module
    (TEA modules are likely not, by default, in the system path)
    
    Searches user override directory first, and then the default
    Support directory in the Sugar bundle (also searches TEA directory
    for backwards compatibility)
    
    Usage: wrap_selection_in_tag = load_action('wrap_selection_in_tag')
    '''
    paths = []
    for idx, root in enumerate(roots):
        paths.append(os.path.join(root, 'Scripts'))
    
    try:
        # Is the action already loaded?
        module = sys.modules[target]
    except (KeyError, ImportError):
        # Find the action (searches user overrides first)
        file, pathname, description = imp.find_module(target, paths)
        if file is None:
            # Action doesn't exist
            return None
        # File exists, load the action
        module = imp.load_module(
            target, file, pathname, description
        )
    return module

def refresh_symlinks(bundle_path, rebuild=False):
    '''
    Walks the file system and adds or updates symlinks to the TEA user
    actions folder
    '''
    def test_link(link, path):
        '''Utility function; tests if the symlink is pointing to the path'''
        if os.path.islink(link):
            if os.readlink(link) == path:
                return True
        return False
    
    defaults = NSUserDefaults.standardUserDefaults()
    enabled = defaults.boolForKey_('TEAEnableUserActions')
    sym_loc = bundle_path + '/TextActions/'
    if enabled:
        # user actions are enabled, so walk the user directory and refresh them
        user_dirs = [
            os.path.expanduser(
                '~/Library/Application Support/Espresso/Support/TextActions/'
            ),
            os.path.expanduser(
                '~/Library/Application Support/Espresso/TEA/TextActions/'
            )
        ]
        for user_dir in user_dirs:
            for root, dirs, filenames in os.walk(user_dir):
                # Rewrite dirs to only include folders that don't start with '.'
                dirs[:] = [dir for dir in dirs if not dir[0] == '.']
                basename = root[len(user_dir):].replace('/', '-')
                for file in filenames:
                    if file[-3:] == 'xml':
                        ref = basename + file
                        # Make sure it's a unique filename
                        count = 1
                        refbase = ref[:-4]
                        prior_link = False
                        while os.path.exists(sym_loc + ref):
                            if test_link(sym_loc + ref, os.path.join(root, file)):
                                prior_link = True
                                break
                            else:
                                ref = str(count) + refbase + '.xml'
                                count += 1
                        if prior_link is False:
                            os.symlink(os.path.join(root, file), sym_loc + ref)
    elif rebuild:
        # user actions just disabled; remove any symlinks in the bundle
        for root, dirs, filenames in os.walk(sym_loc):
            for file in filenames:
                loc = os.path.join(root, file)
                if os.path.islink(loc):
                    os.remove(loc)
            break

def nsdict_to_pydict(nsdict):
    '''Recursively converts an NSDictionary into a Python dict'''
    pydict = dict()
    for arg, value in nsdict.iteritems():
        classname = value.className()
        if classname == 'NSCFDictionary' or classname == 'NSDictionary':
            pydict[str(arg)] = nsdict_to_pydict(value)
        elif classname == 'NSCFString' or classname == 'NSString':
            pydict[str(arg)] = str(value)
        else:
            pydict[str(arg)] = value
    return pydict

########NEW FILE########
__FILENAME__ = comment
#!/usr/bin/env python
# -*- coding: utf-8 -*-

'''
Comment important tags (with 'id' and 'class' attributes)
@author Sergey Chikuyonok (serge.che@gmail.com)
@link http://chikuyonok.ru
'''
from zencoding import zen_core as zen_coding

alias = 'c'
"Filter name alias (if not defined, ZC will use module name)"

def add_comments(node, i):
	
	"""
	Add comments to tag
	@type node: ZenNode
	@type i: int
	"""
	id_attr = node.get_attribute('id')
	class_attr = node.get_attribute('class')
	nl = zen_coding.get_newline()
		
	if id_attr or class_attr:
		comment_str = ''
		padding = node.parent and node.parent.padding or ''
		if id_attr: comment_str += '#' + id_attr
		if class_attr: comment_str += '.' + class_attr
		
		node.start = node.start.replace('<', '<!-- ' + comment_str + ' -->' + nl + padding + '<', 1)
		node.end = node.end.replace('>', '>' + nl + padding + '<!-- /' + comment_str + ' -->', 1)
		
		# replace counters
		node.start = zen_coding.replace_counter(node.start, i + 1)
		node.end = zen_coding.replace_counter(node.end, i + 1)

def process(tree, profile):
	if profile['tag_nl'] is False:
		return tree
		
	for i, item in enumerate(tree.children):
		if item.is_block():
			add_comments(item, i)
		process(item, profile)
	
	return tree
########NEW FILE########
__FILENAME__ = escape
#!/usr/bin/env python
# -*- coding: utf-8 -*-

'''
Filter for escaping unsafe XML characters: <, >, &
@author Sergey Chikuyonok (serge.che@gmail.com)
@link http://chikuyonok.ru
'''
import re

alias = 'e'
"Filter name alias (if not defined, ZC will use module name)"

char_map = {
	'<': '&lt;',
	'>': '&gt;',
	'&': '&amp;'
}

re_chars = re.compile(r'[<>&]')

def escape_chars(text):
	return re_chars.sub(lambda m: char_map[m.group(0)], text)

def process(tree, profile=None):
	for item in tree.children:
		item.start = escape_chars(item.start)
		item.end = escape_chars(item.end)
		
		process(item)
	
	return tree
########NEW FILE########
__FILENAME__ = format-css
#!/usr/bin/env python
# -*- coding: utf-8 -*-

'''
Format CSS properties: add space after property name:
padding:0; -> padding: 0;
@author Sergey Chikuyonok (serge.che@gmail.com)
@link http://chikuyonok.ru
'''
import re

alias = 'fc'
"Filter name alias (if not defined, ZC will use module name)"

re_css_prop = re.compile(r'([\w\-]+\s*:)\s*')

def process(tree, profile):
	for item in tree.children:
		# CSS properties are always snippets 
		if item.type == 'snippet':
			item.start = re_css_prop.sub(r'\1 ', item.start)
		
		process(item, profile)
		
	return tree
########NEW FILE########
__FILENAME__ = format
#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Generic formatting filter: creates proper indentation for each tree node,
placing "%s" placeholder where the actual output should be. You can use
this filter to preformat tree and then replace %s placeholder to whatever you
need. This filter should't be called directly from editor as a part 
of abbreviation.
@author Sergey Chikuyonok (serge.che@gmail.com)
@link http://chikuyonok.ru
"""
import re
from zencoding import zen_core as zen_coding

alias = '_format'
"Filter name alias (if not defined, ZC will use module name)"

child_token = '${child}'
placeholder = '%s'

def get_newline():
	return zen_coding.get_newline()


def get_indentation():
	return zen_coding.get_indentation()

def has_block_sibling(item):
	"""
	Test if passed node has block-level sibling element
	@type item: ZenNode
	@return: bool
	"""
	return item.parent and item.parent.has_block_children()

def is_very_first_child(item):
	"""
	Test if passed itrem is very first child of the whole tree
	@type tree: ZenNode
	"""
	return item.parent and not item.parent.parent and not item.previous_sibling

def should_break_line(node, profile):
	"""
	Need to add line break before element
	@type node: ZenNode
	@type profile: dict
	@return: bool
	"""
	if not profile['inline_break']:
		return False
		
	# find toppest non-inline sibling
	while node.previous_sibling and node.previous_sibling.is_inline():
		node = node.previous_sibling
	
	if not node.is_inline():
		return False
		
	# calculate how many inline siblings we have
	node_count = 1
	node = node.next_sibling
	while node:
		if node.is_inline():
			node_count += 1
		else:
			break
		node = node.next_sibling
	
	return node_count >= profile['inline_break']

def should_break_child(node, profile):
	"""
	 Need to add newline because <code>item</code> has too many inline children
	 @type node: ZenNode
	 @type profile: dict
	 @return: bool
	"""
	# we need to test only one child element, because 
	# has_block_children() method will do the rest
	return node.children and should_break_line(node.children[0], profile)

def process_snippet(item, profile, level=0):
	"""
	Processes element with <code>snippet</code> type
	@type item: ZenNode
	@type profile: dict
	@param level: Depth level
	@type level: int
	"""
	data = item.source.value;
		
	if not data:
		# snippet wasn't found, process it as tag
		return process_tag(item, profile, level)
		
	item.start = placeholder
	item.end = placeholder
	
	padding = item.parent.padding if item.parent else get_indentation() * level 
	
	if not is_very_first_child(item):
		item.start = get_newline() + padding + item.start
	
	# adjust item formatting according to last line of <code>start</code> property
	parts = data.split(child_token)
	lines = zen_coding.split_by_lines(parts[0] or '')
	padding_delta = get_indentation()
		
	if len(lines) > 1:
		m = re.match(r'^(\s+)', lines[-1])
		if m:
			padding_delta = m.group(1)
	
	item.padding = padding + padding_delta
	
	return item

def process_tag(item, profile, level=0):
	"""
	Processes element with <code>tag</code> type
	@type item: ZenNode
	@type profile: dict
	@param level: Depth level
	@type level: int
	"""
	if not item.name:
		# looks like it's a root element
		return item
	
	item.start = placeholder
	item.end = placeholder
	
	is_unary = item.is_unary() and not item.children
		
	# formatting output
	if profile['tag_nl'] is not False:
		padding = item.parent.padding if item.parent else get_indentation() * level
		force_nl = profile['tag_nl'] is True
		should_break = should_break_line(item, profile)
		
		# formatting block-level elements
		if ((item.is_block() or should_break) and item.parent) or force_nl:
			# snippet children should take different formatting
			if not item.parent or (item.parent.type != 'snippet' and not is_very_first_child(item)):
				item.start = get_newline() + padding + item.start
				
			if item.has_block_children() or should_break_child(item, profile) or (force_nl and not is_unary):
				item.end = get_newline() + padding + item.end
				
			if item.has_tags_in_content() or (force_nl and not item.has_children() and not is_unary):
				item.start += get_newline() + padding + get_indentation()
			
		elif item.is_inline() and has_block_sibling(item) and not is_very_first_child(item):
			item.start = get_newline() + padding + item.start
		
		item.padding = padding + get_indentation()
	
	return item

def process(tree, profile, level=0):
	"""
	Processes simplified tree, making it suitable for output as HTML structure
	@type item: ZenNode
	@type profile: dict
	@param level: Depth level
	@type level: int
	"""
	
	for item in tree.children:
		if item.type == 'tag':
			item = process_tag(item, profile, level)
		else:
			item = process_snippet(item, profile, level)
		
		if item.content:
			item.content = zen_coding.pad_string(item.content, item.padding)
			
		process(item, profile, level + 1)
	
	return tree
########NEW FILE########
__FILENAME__ = haml
#!/usr/bin/env python
# -*- coding: utf-8 -*-

'''
Filter that produces HAML tree
@author Sergey Chikuyonok (serge.che@gmail.com)
@link http://chikuyonok.ru
'''
from zencoding import zen_core as zen_coding

child_token = '${child}'
	
def make_attributes_string(tag, profile):
	"""
	 Creates HTML attributes string from tag according to profile settings
	 @type tag: ZenNode
	 @type profile: dict
	"""
	# make attribute string
	attrs = ''
	attr_quote = profile['attr_quotes'] == 'single' and "'" or '"'
	cursor = profile['place_cursor'] and zen_coding.get_caret_placeholder() or ''
		
	# use short notation for ID and CLASS attributes
	for a in tag.attributes:
		name_lower = a['name'].lower()
		if name_lower == 'id':
			attrs += '#' + (a['value'] or cursor)
		elif name_lower == 'class':
			attrs += '.' + (a['value'] or cursor)
			
	other_attrs = []
	
	# process other attributes
	for a in tag.attributes:
		name_lower = a['name'].lower()
		if name_lower != 'id' and name_lower != 'class':
			attr_name = profile['attr_case'] == 'upper' and a['name'].upper() or name_lower
			other_attrs.append(':' + attr_name + ' => ' + attr_quote + (a['value'] or cursor) + attr_quote)
		
	if other_attrs:
		attrs += '{' + ', '.join(other_attrs) + '}'
	
	return attrs

def _replace(placeholder, value):
	if placeholder:
		return placeholder % value
	else:
		return value		

def process_snippet(item, profile, level=0):
	"""
	Processes element with <code>snippet</code> type
	@type item: ZenNode
	@type profile: dict
	@type level: int
	"""
	data = item.source.value
		
	if not data:
		# snippet wasn't found, process it as tag
		return process_tag(item, profile, level)
		
	tokens = data.split(child_token)
	if len(tokens) < 2:
		start = tokens[0]
		end = ''
	else:
		start, end = tokens
	
	padding = item.parent and item.parent.padding or ''
		
	item.start = _replace(item.start, zen_coding.pad_string(start, padding))
	item.end = _replace(item.end, zen_coding.pad_string(end, padding))
	
	return item

def has_block_sibling(item):
	"""
	Test if passed node has block-level sibling element
	@type item: ZenNode
	@return: bool
	"""
	return item.parent and item.parent.has_block_children()

def process_tag(item, profile, level=0):
	"""
	Processes element with <code>tag</code> type
	@type item: ZenNode
	@type profile: dict
	@type level: int
	"""
	if not item.name:
		# looks like it's root element
		return item
	
	attrs = make_attributes_string(item, profile) 
	cursor = profile['place_cursor'] and zen_coding.get_caret_placeholder() or ''
	self_closing = ''
	is_unary = item.is_unary() and not item.children
	
	if profile['self_closing_tag'] and is_unary:
		self_closing = '/'
		
	# define tag name
	tag_name = '%' + (profile['tag_case'] == 'upper' and item.name.upper() or item.name.lower())
					
	if tag_name.lower() == '%div' and '{' not in attrs:
		# omit div tag
		tag_name = ''
		
	item.end = ''
	item.start = _replace(item.start, tag_name + attrs + self_closing)
	
	if not item.children and not is_unary:
		item.start += cursor
	
	return item

def process(tree, profile, level=0):
	"""
	Processes simplified tree, making it suitable for output as HTML structure
	@type tree: ZenNode
	@type profile: dict
	@type level: int
	"""
	if level == 0:
		# preformat tree
		tree = zen_coding.run_filters(tree, profile, '_format')
		
	for i, item in enumerate(tree.children):
		if item.type == 'tag':
			process_tag(item, profile, level)
		else:
			process_snippet(item, profile, level)
	
		# replace counters
		item.start = zen_coding.replace_counter(item.start, i + 1)
		item.end = zen_coding.replace_counter(item.end, i + 1)
		process(item, profile, level + 1)
		
	return tree
########NEW FILE########
__FILENAME__ = html
#!/usr/bin/env python
# -*- coding: utf-8 -*-

'''
Filter that produces HTML tree
@author Sergey Chikuyonok (serge.che@gmail.com)
@link http://chikuyonok.ru
'''
from zencoding import zen_core as zen_coding

child_token = '${child}'

def make_attributes_string(tag, profile):
	"""
	Creates HTML attributes string from tag according to profile settings
	@type tag: ZenNode
	@type profile: dict
	"""
	# make attribute string
	attrs = ''
	attr_quote = profile['attr_quotes'] == 'single' and "'" or '"'
	cursor = profile['place_cursor'] and zen_coding.get_caret_placeholder() or ''
	
	# process other attributes
	for a in tag.attributes:
		attr_name = profile['attr_case'] == 'upper' and a['name'].upper() or a['name'].lower()
		attrs += ' ' + attr_name + '=' + attr_quote + (a['value'] or cursor) + attr_quote
		
	return attrs

def _replace(placeholder, value):
	if placeholder:
		return placeholder % value
	else:
		return value

def process_snippet(item, profile, level):
	"""
	Processes element with <code>snippet</code> type
	@type item: ZenNode
	@type profile: dict
	@type level: int
	"""
	data = item.source.value;
		
	if not data:
		# snippet wasn't found, process it as tag
		return process_tag(item, profile, level)
		
	tokens = data.split(child_token)
	if len(tokens) < 2:
		start = tokens[0]
		end = ''
	else:
		start, end = tokens
		
	padding = item.parent and item.parent.padding or ''
		
	item.start = _replace(item.start, zen_coding.pad_string(start, padding))
	item.end = _replace(item.end, zen_coding.pad_string(end, padding))
	
	return item


def has_block_sibling(item):
	"""
	Test if passed node has block-level sibling element
	@type item: ZenNode
	@return: bool
	"""
	return item.parent and item.parent.has_block_children()

def process_tag(item, profile, level):
	"""
	Processes element with <code>tag</code> type
	@type item: ZenNode
	@type profile: dict
	@type level: int
	"""
	if not item.name:
		# looks like it's root element
		return item
	
	attrs = make_attributes_string(item, profile) 
	cursor = profile['place_cursor'] and zen_coding.get_caret_placeholder() or ''
	self_closing = ''
	is_unary = item.is_unary() and not item.children
	start= ''
	end = ''
	
	if profile['self_closing_tag'] == 'xhtml':
		self_closing = ' /'
	elif profile['self_closing_tag'] is True:
		self_closing = '/'
		
	# define opening and closing tags
	tag_name = profile['tag_case'] == 'upper' and item.name.upper() or item.name.lower()
	if is_unary:
		start = '<' + tag_name + attrs + self_closing + '>'
		item.end = ''
	else:
		start = '<' + tag_name + attrs + '>'
		end = '</' + tag_name + '>'
	
	item.start = _replace(item.start, start)
	item.end = _replace(item.end, end)
	
	if not item.children and not is_unary:
		item.start += cursor
	
	return item

def process(tree, profile, level=0):
	"""
	Processes simplified tree, making it suitable for output as HTML structure
	@type tree: ZenNode
	@type profile: dict
	@type level: int
	"""
	if level == 0:
		# preformat tree
		tree = zen_coding.run_filters(tree, profile, '_format')
		zen_coding.max_tabstop = 0
		
	for item in tree.children:
		if item.type == 'tag':
			process_tag(item, profile, level)
		else:
			process_snippet(item, profile, level)
	
		# replace counters
		item.start = zen_coding.unescape_text(zen_coding.replace_counter(item.start, item.counter))
		item.end = zen_coding.unescape_text(zen_coding.replace_counter(item.end, item.counter))
		zen_coding.upgrade_tabstops(item)
		
		process(item, profile, level + 1)
		
	return tree

########NEW FILE########
__FILENAME__ = xsl
#!/usr/bin/env python
# -*- coding: utf-8 -*-

'''
Filter for trimming "select" attributes from some tags that contains
child elements
@author Sergey Chikuyonok (serge.che@gmail.com)
@link http://chikuyonok.ru
'''
import re

tags = {
	'xsl:variable': 1,
	'xsl:with-param': 1
}

re_attr = re.compile(r'\s+select\s*=\s*([\'"]).*?\1')

def trim_attribute(node):
	"""
	Removes "select" attribute from node
	@type node: ZenNode
	"""
	node.start = re_attr.sub('', node.start)

def process(tree, profile):
	for item in tree.children:
		if item.type == 'tag' and item.name.lower() in tags and item.children:
			trim_attribute(item)
		
		process(item, profile)
########NEW FILE########
__FILENAME__ = html_matcher
#!/usr/bin/env python
# -*- coding: utf-8 -*-

'''
Context-independent xHTML pair matcher
Use method <code>match(html, start_ix)</code> to find matching pair.
If pair was found, this function returns a list of indexes where tag pair 
starts and ends. If pair wasn't found, <code>None</code> will be returned.

The last matched (or unmatched) result is saved in <code>last_match</code> 
dictionary for later use.

@author: Sergey Chikuyonok (serge.che@gmail.com)
'''
import re

start_tag = r'<([\w\:\-]+)((?:\s+[\w\-:]+(?:\s*=\s*(?:(?:"[^"]*")|(?:\'[^\']*\')|[^>\s]+))?)*)\s*(\/?)>'
end_tag = r'<\/([\w\:\-]+)[^>]*>'
attr = r'([\w\-:]+)(?:\s*=\s*(?:(?:"((?:\\.|[^"])*)")|(?:\'((?:\\.|[^\'])*)\')|([^>\s]+)))?'

"Last matched HTML pair"
last_match = {
	'opening_tag': None, # Tag() or Comment() object
	'closing_tag': None, # Tag() or Comment() object
	'start_ix': -1,
	'end_ix': -1
}

cur_mode = 'xhtml'
"Current matching mode"

def set_mode(new_mode):
	global cur_mode
	if new_mode != 'html': new_mode = 'xhtml'
	cur_mode = new_mode

def make_map(elems):
	"""
	Create dictionary of elements for faster searching
	@param elems: Elements, separated by comma
	@type elems: str
	"""
	obj = {}
	for elem in elems.split(','):
			obj[elem] = True

	return obj

# Empty Elements - HTML 4.01
empty = make_map("area,base,basefont,br,col,frame,hr,img,input,isindex,link,meta,param,embed");

# Block Elements - HTML 4.01
block = make_map("address,applet,blockquote,button,center,dd,dir,div,dl,dt,fieldset,form,frameset,hr,iframe,isindex,li,map,menu,noframes,noscript,object,ol,p,pre,script,table,tbody,td,tfoot,th,thead,tr,ul");

# Inline Elements - HTML 4.01
inline = make_map("a,abbr,acronym,applet,b,basefont,bdo,big,br,button,cite,code,del,dfn,em,font,i,iframe,img,input,ins,kbd,label,map,object,q,s,samp,select,small,span,strike,strong,sub,sup,textarea,tt,u,var");

# Elements that you can, intentionally, leave open
# (and which close themselves)
close_self = make_map("colgroup,dd,dt,li,options,p,td,tfoot,th,thead,tr");

# Attributes that have their values filled in disabled="disabled"
fill_attrs = make_map("checked,compact,declare,defer,disabled,ismap,multiple,nohref,noresize,noshade,nowrap,readonly,selected");

#Special Elements (can contain anything)
# serge.che: parsing data inside <scipt> elements is a "feature"
special = make_map("style");

class Tag():
	"""Matched tag"""
	def __init__(self, match, ix):
		"""
		@type match: MatchObject
		@param match: Matched HTML tag
		@type ix: int
		@param ix: Tag's position
		"""
		global cur_mode
		
		name = match.group(1).lower()
		self.name = name
		self.full_tag = match.group(0)
		self.start = ix
		self.end = ix + len(self.full_tag)
		self.unary = ( len(match.groups()) > 2 and bool(match.group(3)) ) or (name in empty and cur_mode == 'html')
		self.type = 'tag'
		self.close_self = (name in close_self and cur_mode == 'html')

class Comment():
	"Matched comment"
	def __init__(self, start, end):
		self.start = start
		self.end = end
		self.type = 'comment'

def make_range(opening_tag=None, closing_tag=None, ix=0):
	"""
	Makes selection ranges for matched tag pair
	@type opening_tag: Tag
    @type closing_tag: Tag
    @type ix: int
    @return list
	"""
	start_ix, end_ix = -1, -1
	
	if opening_tag and not closing_tag: # unary element
		start_ix = opening_tag.start
		end_ix = opening_tag.end
	elif opening_tag and closing_tag: # complete element
		if (opening_tag.start < ix and opening_tag.end > ix) or (closing_tag.start <= ix and closing_tag.end > ix):
			start_ix = opening_tag.start
			end_ix = closing_tag.end;
		else:
			start_ix = opening_tag.end
			end_ix = closing_tag.start
	
	return start_ix, end_ix

def save_match(opening_tag=None, closing_tag=None, ix=0):
	"""
	Save matched tag for later use and return found indexes
    @type opening_tag: Tag
    @type closing_tag: Tag
    @type ix: int
    @return list
	"""
	last_match['opening_tag'] = opening_tag; 
	last_match['closing_tag'] = closing_tag;
	
	last_match['start_ix'], last_match['end_ix'] = make_range(opening_tag, closing_tag, ix)
	
	return last_match['start_ix'] != -1 and (last_match['start_ix'], last_match['end_ix']) or (None, None)

def match(html, start_ix, mode='xhtml'):
	"""
	Search for matching tags in <code>html</code>, starting from
	<code>start_ix</code> position. The result is automatically saved
	in <code>last_match</code> property
	"""
	return _find_pair(html, start_ix, mode, save_match)

def find(html, start_ix, mode='xhtml'):
	"""
	Search for matching tags in <code>html</code>, starting from
	<code>start_ix</code> position.
	"""
	return _find_pair(html, start_ix, mode)

def get_tags(html, start_ix, mode='xhtml'):
	"""
	Search for matching tags in <code>html</code>, starting from 
	<code>start_ix</code> position. The difference between 
	<code>match</code> function itself is that <code>get_tags</code> 
	method doesn't save matched result in <code>last_match</code> property 
	and returns array of opening and closing tags
	This method is generally used for lookups
	"""
	return _find_pair(html, start_ix, mode, lambda op, cl=None, ix=0: (op, cl) if op and op.type == 'tag' else None)


def _find_pair(html, start_ix, mode='xhtml', action=make_range):
	"""
	Search for matching tags in <code>html</code>, starting from
	<code>start_ix</code> position
	
	@param html: Code to search
	@type html: str
	
	@param start_ix: Character index where to start searching pair
	(commonly, current caret position)
	@type start_ix: int
	
	@param action: Function that creates selection range
	@type action: function
	
	@return: list
	"""

	forward_stack = []
	backward_stack = []
	opening_tag = None
	closing_tag = None
	html_len = len(html)
	
	set_mode(mode)

	def has_match(substr, start=None):
		if start is None:
			start = ix

		return html.find(substr, start) == start


	def find_comment_start(start_pos):
		while start_pos:
			if html[start_pos] == '<' and has_match('<!--', start_pos):
				break

			start_pos -= 1

		return start_pos

#    find opening tag
	ix = start_ix - 1
	while ix >= 0:
		ch = html[ix]
		if ch == '<':
			check_str = html[ix:]
			m = re.match(end_tag, check_str)
			if m:  # found closing tag
				tmp_tag = Tag(m, ix)
				if tmp_tag.start < start_ix and tmp_tag.end > start_ix: # direct hit on searched closing tag
					closing_tag = tmp_tag
				else:
					backward_stack.append(tmp_tag)
			else:
				m = re.match(start_tag, check_str)
				if m: # found opening tag
					tmp_tag = Tag(m, ix);
					if tmp_tag.unary:
						if tmp_tag.start < start_ix and tmp_tag.end > start_ix: # exact match
							return action(tmp_tag, None, start_ix)
					elif backward_stack and backward_stack[-1].name == tmp_tag.name:
						backward_stack.pop()
					else: # found nearest unclosed tag
						opening_tag = tmp_tag
						break
				elif check_str.startswith('<!--'): # found comment start
					end_ix = check_str.find('-->') + ix + 3;
					if ix < start_ix and end_ix >= start_ix:
						return action(Comment(ix, end_ix))
		elif ch == '-' and has_match('-->'): # found comment end
			# search left until comment start is reached
			ix = find_comment_start(ix)

		ix -= 1
		
	if not opening_tag:
		return action(None)
	
	# find closing tag
	if not closing_tag:
		ix = start_ix
		while ix < html_len:
			ch = html[ix]
			if ch == '<':
				check_str = html[ix:]
				m = re.match(start_tag, check_str)
				if m: # found opening tag
					tmp_tag = Tag(m, ix);
					if not tmp_tag.unary:
						forward_stack.append(tmp_tag)
				else:
					m = re.match(end_tag, check_str)
					if m:   #found closing tag
						tmp_tag = Tag(m, ix);
						if forward_stack and forward_stack[-1].name == tmp_tag.name:
							forward_stack.pop()
						else:  # found matched closing tag
							closing_tag = tmp_tag;
							break
					elif has_match('<!--'): # found comment
						ix += check_str.find('-->') + 3
						continue
			elif ch == '-' and has_match('-->'):
				# looks like cursor was inside comment with invalid HTML
				if not forward_stack or forward_stack[-1].type != 'comment':
					end_ix = ix + 3
					return action(Comment( find_comment_start(ix), end_ix ))
				
			ix += 1
	
	return action(opening_tag, closing_tag, start_ix)
########NEW FILE########
__FILENAME__ = stparser
'''
Zen Coding's settings parser
Created on Jun 14, 2009

@author: sergey
'''
from copy import deepcopy

import re
import types
from zen_settings import zen_settings

_original_settings = deepcopy(zen_settings)

TYPE_ABBREVIATION = 'zen-tag',
TYPE_EXPANDO = 'zen-expando',
TYPE_REFERENCE = 'zen-reference';
""" Reference to another abbreviation or tag """

re_tag = r'^<([\w\-]+(?:\:[\w\-]+)?)((?:\s+[\w\-]+(?:\s*=\s*(?:(?:"[^"]*")|(?:\'[^\']*\')|[^>\s]+))?)*)\s*(\/?)>'
"Regular expression for XML tag matching"
	
re_attrs = r'([\w\-]+)\s*=\s*([\'"])(.*?)\2'
"Regular expression for matching XML attributes"

class Entry:
	"""
	Unified object for parsed data
	"""
	def __init__(self, entry_type, key, value):
		"""
		@type entry_type: str
		@type key: str
		@type value: dict
		"""
		self.type = entry_type
		self.key = key
		self.value = value

def _make_expando(key, value):
	"""
	Make expando from string
	@type key: str
	@type value: str
	@return: Entry
	"""
	return Entry(TYPE_EXPANDO, key, value)

def _make_abbreviation(key, tag_name, attrs, is_empty=False):
	"""
	Make abbreviation from string
	@param key: Abbreviation key
	@type key: str
	@param tag_name: Expanded element's tag name
	@type tag_name: str
	@param attrs: Expanded element's attributes
	@type attrs: str
	@param is_empty: Is expanded element empty or not
	@type is_empty: bool
	@return: dict
	"""
	result = {
		'name': tag_name,
		'is_empty': is_empty
	};
	
	if attrs:
		result['attributes'] = [];
		for m in re.findall(re_attrs, attrs):
			result['attributes'].append({
				'name': m[0],
				'value': m[2]
			})
			
	return Entry(TYPE_ABBREVIATION, key, result)

def _parse_abbreviations(obj):
	"""
	Parses all abbreviations inside dictionary
 	@param obj: dict
	"""
	for key, value in obj.items():
		key = key.strip()
		if key[-1] == '+':
#			this is expando, leave 'value' as is
			obj[key] = _make_expando(key, value)
		else:
			m = re.search(re_tag, value)
			if m:
				obj[key] = _make_abbreviation(key, m.group(1), m.group(2), (m.group(3) == '/'))
			else:
#				assume it's reference to another abbreviation
				obj[key] = Entry(TYPE_REFERENCE, key, value)

def parse(settings):
	"""
	Parse user's settings. This function must be called *before* any activity
	in zen coding (for example, expanding abbreviation)
 	@type settings: dict
	"""
	for p, value in settings.items():
		if p == 'abbreviations':
			_parse_abbreviations(value)
		elif p == 'extends':
			settings[p] = [v.strip() for v in value.split(',')]
		elif type(value) == types.DictType:
			parse(value)


def extend(parent, child):
	"""
	Recursevly extends parent dictionary with children's keys. Used for merging
	default settings with user's
	@type parent: dict
	@type child: dict
	"""
	for p, value in child.items():
		if type(value) == types.DictType:
			if p not in parent:
				parent[p] = {}
			extend(parent[p], value)
		else:
			parent[p] = value
				


def create_maps(obj):
	"""
	Create hash maps on certain string properties of zen settings
	@type obj: dict
	"""
	for p, value in obj.items():
		if p == 'element_types':
			for k, v in value.items():
				if isinstance(v, str):
					value[k] = [el.strip() for el in v.split(',')]
		elif type(value) == types.DictType:
			create_maps(value)


if __name__ == '__main__':
	pass

def get_settings(user_settings=None):
	"""
	Main function that gather all settings and returns parsed dictionary
	@param user_settings: A dictionary of user-defined settings
	"""
	settings = deepcopy(_original_settings)
	create_maps(settings)
	
	if user_settings:
		user_settings = deepcopy(user_settings)
		create_maps(user_settings)
		extend(settings, user_settings)
	
	# now we need to parse final set of settings
	parse(settings)
	
	return settings
	
########NEW FILE########
__FILENAME__ = zen_actions
#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Middleware layer that communicates between editor and Zen Coding.
This layer describes all available Zen Coding actions, like 
"Expand Abbreviation".
@author Sergey Chikuyonok (serge.che@gmail.com)
@link http://chikuyonok.ru
"""
from zencoding import zen_core as zen_coding
from zencoding import html_matcher
import re

def find_abbreviation(editor):
	"""
	Search for abbreviation in editor from current caret position
	@param editor: Editor instance
	@type editor: ZenEditor
	@return: str
	"""
	start, end = editor.get_selection_range()
	if start != end:
		# abbreviation is selected by user
		return editor.get_content()[start, end];
	
	# search for new abbreviation from current caret position
	cur_line_start, cur_line_end = editor.get_current_line_range()
	return zen_coding.extract_abbreviation(editor.get_content()[cur_line_start:start])

def expand_abbreviation(editor, syntax=None, profile_name=None):
	"""
	Find from current caret position and expand abbreviation in editor
	@param editor: Editor instance
	@type editor: ZenEditor
	@param syntax: Syntax type (html, css, etc.)
	@type syntax: str
	@param profile_name: Output profile name (html, xml, xhtml)
	@type profile_name: str
	@return: True if abbreviation was expanded successfully
	"""
	if syntax is None: syntax = editor.get_syntax()
	if profile_name is None: profile_name = editor.get_profile_name()
	
	range_start, caret_pos = editor.get_selection_range()
	abbr = find_abbreviation(editor)
	content = ''
		
	if abbr:
		content = zen_coding.expand_abbreviation(abbr, syntax, profile_name)
		if content:
			editor.replace_content(content, caret_pos - len(abbr), caret_pos)
			return True
	
	return False

def expand_abbreviation_with_tab(editor, syntax, profile_name='xhtml'):
	"""
	A special version of <code>expandAbbreviation</code> function: if it can't
	find abbreviation, it will place Tab character at caret position
	@param editor: Editor instance
	@type editor: ZenEditor
	@param syntax: Syntax type (html, css, etc.)
	@type syntax: str
	@param profile_name: Output profile name (html, xml, xhtml)
	@type profile_name: str
	"""
	if not expand_abbreviation(editor, syntax, profile_name):
		editor.replace_content(zen_coding.get_variable('indentation'), editor.get_caret_pos())
	
	return True 

def match_pair(editor, direction='out', syntax=None):
	"""
	Find and select HTML tag pair
	@param editor: Editor instance
	@type editor: ZenEditor
	@param direction: Direction of pair matching: 'in' or 'out'. 
	@type direction: str 
	"""
	direction = direction.lower()
	if syntax is None: syntax = editor.get_profile_name()
	
	range_start, range_end = editor.get_selection_range()
	cursor = range_end
	content = editor.get_content()
	rng = None
	
	old_open_tag = html_matcher.last_match['opening_tag']
	old_close_tag = html_matcher.last_match['closing_tag']
	
	if direction == 'in' and old_open_tag and range_start != range_end:
#		user has previously selected tag and wants to move inward
		if not old_close_tag:
#			unary tag was selected, can't move inward
			return False
		elif old_open_tag.start == range_start:
			if content[old_open_tag.end] == '<':
#				test if the first inward tag matches the entire parent tag's content
				_r = html_matcher.find(content, old_open_tag.end + 1, syntax)
				if _r[0] == old_open_tag.end and _r[1] == old_close_tag.start:
					rng = html_matcher.match(content, old_open_tag.end + 1, syntax)
				else:
					rng = (old_open_tag.end, old_close_tag.start)
			else:
				rng = (old_open_tag.end, old_close_tag.start)
		else:
			new_cursor = content[0:old_close_tag.start].find('<', old_open_tag.end)
			search_pos = new_cursor + 1 if new_cursor != -1 else old_open_tag.end
			rng = html_matcher.match(content, search_pos, syntax)
	else:
		rng = html_matcher.match(content, cursor, syntax)
	
	if rng and rng[0] is not None:
		editor.create_selection(rng[0], rng[1])
		return True
	else:
		return False

def match_pair_inward(editor):
	return match_pair(editor, 'in')
	
def match_pair_outward(editor):
	return match_pair(editor, 'out')

def narrow_to_non_space(text, start, end):
	"""
	Narrow down text indexes, adjusting selection to non-space characters
	@type text: str
	@type start: int
	@type end: int
	@return: list
	"""
	# narrow down selection until first non-space character
	while start < end:
		if not text[start].isspace():
			break
			
		start += 1
	
	while end > start:
		end -= 1
		if not text[end].isspace():
			end += 1
			break
		
	return start, end

def wrap_with_abbreviation(editor, abbr, syntax=None, profile_name=None):
	"""
	Wraps content with abbreviation
	@param editor: Editor instance
	@type editor: ZenEditor
	@param syntax: Syntax type (html, css, etc.)
	@type syntax: str
	@param profile_name: Output profile name (html, xml, xhtml)
	@type profile_name: str
	"""
	if not abbr: return None 
	
	if syntax is None: syntax = editor.get_syntax()
	if profile_name is None: profile_name = editor.get_profile_name()
	
	start_offset, end_offset = editor.get_selection_range()
	content = editor.get_content()
	
	if start_offset == end_offset:
		# no selection, find tag pair
		rng = html_matcher.match(content, start_offset, profile_name)
		
		if rng[0] is None: # nothing to wrap
			return None
		else:
			start_offset, end_offset = rng
			
	start_offset, end_offset = narrow_to_non_space(content, start_offset, end_offset)
	line_bounds = get_line_bounds(content, start_offset)
	padding = get_line_padding(content[line_bounds[0]:line_bounds[1]])
	
	new_content = content[start_offset:end_offset]
	result = zen_coding.wrap_with_abbreviation(abbr, unindent_text(new_content, padding), syntax, profile_name)
	
	if result:
		editor.replace_content(result, start_offset, end_offset)
		return True
	
	return False

def unindent(editor, text):
	"""
	Unindent content, thus preparing text for tag wrapping
	@param editor: Editor instance
	@type editor: ZenEditor
	@param text: str
	@return str
	"""
	return unindent_text(text, get_current_line_padding(editor))

def unindent_text(text, pad):
	"""
	Removes padding at the beginning of each text's line
	@type text: str
	@type pad: str
	"""
	lines = zen_coding.split_by_lines(text)
	
	for i,line in enumerate(lines):
		if line.startswith(pad):
			lines[i] = line[len(pad):]
	
	return zen_coding.get_newline().join(lines)

def get_current_line_padding(editor):
	"""
	Returns padding of current editor's line
	@return str
	"""
	return get_line_padding(editor.get_current_line())

def get_line_padding(line):
	"""
	Returns padding of current editor's line
	@return str
	"""
	m = re.match(r'^(\s+)', line)
	return m and m.group(0) or ''

def find_new_edit_point(editor, inc=1, offset=0):
	"""
	Search for new caret insertion point
	@param editor: Editor instance
	@type editor: ZenEditor
	@param inc: Search increment: -1 — search left, 1 — search right
	@param offset: Initial offset relative to current caret position
	@return: -1 if insertion point wasn't found
	"""
	cur_point = editor.get_caret_pos() + offset
	content = editor.get_content()
	max_len = len(content)
	next_point = -1
	re_empty_line = r'^\s+$'
	
	def get_line(ix):
		start = ix
		while start >= 0:
			c = content[start]
			if c == '\n' or c == '\r': break
			start -= 1
		
		return content[start:ix]
		
	while cur_point < max_len and cur_point > 0:
		cur_point += inc
		cur_char = content[cur_point]
		next_char = content[cur_point + 1]
		prev_char = content[cur_point - 1]
		
		if cur_char in '"\'':
			if next_char == cur_char and prev_char == '=':
				# empty attribute
				next_point = cur_point + 1
		elif cur_char == '>' and next_char == '<':
			# between tags
			next_point = cur_point + 1
		elif cur_char in '\r\n':
			# empty line
			if re.search(re_empty_line, get_line(cur_point - 1)):
				next_point = cur_point
		
		if next_point != -1: break
	
	return next_point

def prev_edit_point(editor):
	"""
	Move caret to previous edit point
	@param editor: Editor instance
	@type editor: ZenEditor
	"""
	cur_pos = editor.get_caret_pos()
	new_point = find_new_edit_point(editor, -1)
		
	if new_point == cur_pos:
		# we're still in the same point, try searching from the other place
		new_point = find_new_edit_point(editor, -1, -2)
	
	if new_point != -1:
		editor.set_caret_pos(new_point)
		return True
	
	return False

def next_edit_point(editor):
	"""
	Move caret to next edit point
	@param editor: Editor instance
	@type editor: ZenEditor
	""" 
	new_point = find_new_edit_point(editor, 1)
	if new_point != -1:
		editor.set_caret_pos(new_point)
		return True
	
	return False

def insert_formatted_newline(editor, mode='html'):
	"""
	Inserts newline character with proper indentation
	@param editor: Editor instance
	@type editor: ZenEditor
	@param mode: Syntax mode (only 'html' is implemented)
	@type mode: str
	"""
	caret_pos = editor.get_caret_pos()
	nl = zen_coding.get_newline()
	pad = zen_coding.get_variable('indentation')
		
	if mode == 'html':
		# let's see if we're breaking newly created tag
		pair = html_matcher.get_tags(editor.get_content(), editor.get_caret_pos(), editor.get_profile_name())
		
		if pair[0] and pair[1] and pair[0]['type'] == 'tag' and pair[0]['end'] == caret_pos and pair[1]['start'] == caret_pos:
			editor.replace_content(nl + pad + zen_coding.get_caret_placeholder() + nl, caret_pos)
		else:
			editor.replace_content(nl, caret_pos)
	else:
		editor.replace_content(nl, caret_pos)
		
	return True

def select_line(editor):
	"""
	Select line under cursor
	@param editor: Editor instance
	@type editor: ZenEditor
	"""
	start, end = editor.get_current_line_range();
	editor.create_selection(start, end)
	return True

def go_to_matching_pair(editor):
	"""
	Moves caret to matching opening or closing tag
	@param editor: Editor instance
	@type editor: ZenEditor
	"""
	content = editor.get_content()
	caret_pos = editor.get_caret_pos()
	
	if content[caret_pos] == '<': 
		# looks like caret is outside of tag pair  
		caret_pos += 1
		
	tags = html_matcher.get_tags(content, caret_pos, editor.get_profile_name())
		
	if tags and tags[0]:
		# match found
		open_tag, close_tag = tags
			
		if close_tag: # exclude unary tags
			if open_tag['start'] <= caret_pos and open_tag['end'] >= caret_pos:
				editor.set_caret_pos(close_tag['start'])
			elif close_tag['start'] <= caret_pos and close_tag['end'] >= caret_pos:
				editor.set_caret_pos(open_tag['start'])
				
		return True
	
	return False
				

def merge_lines(editor):
	"""
	Merge lines spanned by user selection. If there's no selection, tries to find
	matching tags and use them as selection
	@param editor: Editor instance
	@type editor: ZenEditor
	"""
	start, end = editor.get_selection_range()
	if start == end:
		# find matching tag
		pair = html_matcher.match(editor.get_content(), editor.get_caret_pos(), editor.get_profile_name())
		if pair and pair[0] is not None:
			start, end = pair
	
	if start != end:
		# got range, merge lines
		text = editor.get_content()[start:end]
		lines = map(lambda s: re.sub(r'^\s+', '', s), zen_coding.split_by_lines(text))
		text = re.sub(r'\s{2,}', ' ', ''.join(lines))
		editor.replace_content(text, start, end)
		editor.create_selection(start, start + len(text))
		return True
	
	return False

def toggle_comment(editor):
	"""
	Toggle comment on current editor's selection or HTML tag/CSS rule
	@type editor: ZenEditor
	"""
	syntax = editor.get_syntax()
	if syntax == 'css':
		return toggle_css_comment(editor)
	else:
		return toggle_html_comment(editor)

def toggle_html_comment(editor):
	"""
	Toggle HTML comment on current selection or tag
	@type editor: ZenEditor
	@return: True if comment was toggled
	"""
	start, end = editor.get_selection_range()
	content = editor.get_content()
		
	if start == end:
		# no selection, find matching tag
		pair = html_matcher.get_tags(content, editor.get_caret_pos(), editor.get_profile_name())
		if pair and pair[0]: # found pair
			start = pair[0].start
			end = pair[1] and pair[1].end or pair[0].end
	
	return generic_comment_toggle(editor, '<!--', '-->', start, end)

def toggle_css_comment(editor):
	"""
	Simple CSS commenting
	@type editor: ZenEditor
	@return: True if comment was toggled
	"""
	start, end = editor.get_selection_range()
	
	if start == end:
		# no selection, get current line
		start, end = editor.get_current_line_range()

		# adjust start index till first non-space character
		start, end = narrow_to_non_space(editor.get_content(), start, end)
	
	return generic_comment_toggle(editor, '/*', '*/', start, end)

def search_comment(text, pos, start_token, end_token):
	"""
	Search for nearest comment in <code>str</code>, starting from index <code>from</code>
	@param text: Where to search
	@type text: str
	@param pos: Search start index
	@type pos: int
	@param start_token: Comment start string
	@type start_token: str
	@param end_token: Comment end string
	@type end_token: str
	@return: None if comment wasn't found, list otherwise
	"""
	start_ch = start_token[0]
	end_ch = end_token[0]
	comment_start = -1
	comment_end = -1
	
	def has_match(tx, start):
		return text[start:start + len(tx)] == tx
	
		
	# search for comment start
	while pos:
		pos -= 1
		if text[pos] == start_ch and has_match(start_token, pos):
			comment_start = pos
			break
	
	if comment_start != -1:
		# search for comment end
		pos = comment_start
		content_len = len(text)
		while content_len >= pos:
			pos += 1
			if text[pos] == end_ch and has_match(end_token, pos):
				comment_end = pos + len(end_token)
				break
	
	if comment_start != -1 and comment_end != -1:
		return comment_start, comment_end
	else:
		return None

def generic_comment_toggle(editor, comment_start, comment_end, range_start, range_end):
	"""
	Generic comment toggling routine
	@type editor: ZenEditor
	@param comment_start: Comment start token
	@type comment_start: str
	@param comment_end: Comment end token
	@type comment_end: str
	@param range_start: Start selection range
	@type range_start: int
	@param range_end: End selection range
	@type range_end: int
	@return: bool
	"""
	content = editor.get_content()
	caret_pos = [editor.get_caret_pos()]
	new_content = None
		
	def adjust_caret_pos(m):
		caret_pos[0] -= len(m.group(0))
		return ''
		
	def remove_comment(text):
		"""
		Remove comment markers from string
		@param {Sting} str
		@return {String}
		"""
		text = re.sub(r'^' + re.escape(comment_start) + r'\s*', adjust_caret_pos, text)
		return re.sub(r'\s*' + re.escape(comment_end) + '$', '', text)
	
	def has_match(tx, start):
		return content[start:start + len(tx)] == tx
	
	# first, we need to make sure that this substring is not inside comment
	comment_range = search_comment(content, caret_pos[0], comment_start, comment_end)
	
	if comment_range and comment_range[0] <= range_start and comment_range[1] >= range_end:
		# we're inside comment, remove it
		range_start, range_end = comment_range
		new_content = remove_comment(content[range_start:range_end])
	else:
		# should add comment
		# make sure that there's no comment inside selection
		new_content = '%s %s %s' % (comment_start, re.sub(re.escape(comment_start) + r'\s*|\s*' + re.escape(comment_end), '', content[range_start:range_end]), comment_end)
			
		# adjust caret position
		caret_pos[0] += len(comment_start) + 1

	# replace editor content
	if new_content is not None:
		d = caret_pos[0] - range_start
		new_content = new_content[0:d] + zen_coding.get_caret_placeholder() + new_content[d:]
		editor.replace_content(unindent(editor, new_content), range_start, range_end)
		return True
	
	return False

def split_join_tag(editor, profile_name=None):
	"""
	Splits or joins tag, e.g. transforms it into a short notation and vice versa:
	<div></div> → <div /> : join
	<div /> → <div></div> : split
	@param editor: Editor instance
	@type editor: ZenEditor
	@param profile_name: Profile name
	@type profile_name: str
	"""
	caret_pos = editor.get_caret_pos()
	profile = zen_coding.get_profile(profile_name or editor.get_profile_name())
	caret = zen_coding.get_caret_placeholder()

	# find tag at current position
	pair = html_matcher.get_tags(editor.get_content(), caret_pos, profile_name or editor.get_profile_name())
	if pair and pair[0]:
		new_content = pair[0].full_tag
		
		if pair[1]: # join tag
			closing_slash = ''
			if profile['self_closing_tag'] is True:
				closing_slash = '/'
			elif profile['self_closing_tag'] == 'xhtml':
				closing_slash = ' /'
				
			new_content = re.sub(r'\s*>$', closing_slash + '>', new_content)
			
			# add caret placeholder
			if len(new_content) + pair[0].start < caret_pos:
				new_content += caret
			else:
				d = caret_pos - pair[0].start
				new_content = new_content[0:d] + caret + new_content[d:]
			
			editor.replace_content(new_content, pair[0].start, pair[1].end)
		else: # split tag
			nl = zen_coding.get_newline()
			pad = zen_coding.get_variable('indentation')
			
			# define tag content depending on profile
			tag_content = profile['tag_nl'] is True and nl + pad + caret + nl or caret
			
			new_content = '%s%s</%s>' % (re.sub(r'\s*\/>$', '>', new_content), tag_content, pair[0].name)
			editor.replace_content(new_content, pair[0].start, pair[0].end)
		
		return True
	else:
		return False
	

def get_line_bounds(text, pos):
	"""
	Returns line bounds for specific character position
	@type text: str
	@param pos: Where to start searching
	@type pos: int
	@return: list
	"""
	start = 0
	end = len(text) - 1
	
	# search left
	for i in range(pos - 1, 0, -1):
		if text[i] in '\n\r':
			start = i + 1
			break
		
	# search right
	for i in range(pos, len(text)):
		if text[i] in '\n\r':
			end = i
			break
		
	return start, end

def remove_tag(editor):
	"""
	Gracefully removes tag under cursor
	@type editor: ZenEditor
	"""
	caret_pos = editor.get_caret_pos()
	content = editor.get_content()
		
	# search for tag
	pair = html_matcher.get_tags(content, caret_pos, editor.get_profile_name())
	if pair and pair[0]:
		if not pair[1]:
			# simply remove unary tag
			editor.replace_content(zen_coding.get_caret_placeholder(), pair[0].start, pair[0].end)
		else:
			tag_content_range = narrow_to_non_space(content, pair[0].end, pair[1].start)
			start_line_bounds = get_line_bounds(content, tag_content_range[0])
			start_line_pad = get_line_padding(content[start_line_bounds[0]:start_line_bounds[1]])
			tag_content = content[tag_content_range[0]:tag_content_range[1]]
				
			tag_content = unindent_text(tag_content, start_line_pad)
			editor.replace_content(zen_coding.get_caret_placeholder() + tag_content, pair[0].start, pair[1].end)
		
		return True
	else:
		return False
########NEW FILE########
__FILENAME__ = zen_core
#!/usr/bin/env python
# -*- coding: utf-8 -*-
'''
Core Zen Coding library. Contains various text manipulation functions:

== Expand abbreviation
Expands abbreviation like ul#nav>li*5>a into a XHTML string.
=== How to use
First, you have to extract current string (where cursor is) from your test 
editor and use <code>find_abbr_in_line()</code> method to extract abbreviation. 
If abbreviation was found, this method will return it as well as position index
of abbreviation inside current line. If abbreviation wasn't 
found, method returns empty string. With abbreviation found, you should call
<code>parse_into_tree()</code> method to transform abbreviation into a tag tree. 
This method returns <code>Tag</code> object on success, None on failure. Then
simply call <code>to_string()</code> method of returned <code>Tag</code> object
to transoform tree into a XHTML string

You can setup output profile using <code>setup_profile()</code> method 
(see <code>default_profile</code> definition for available options) 

 
Created on Apr 17, 2009

@author: Sergey Chikuyonok (http://chikuyonok.ru)
'''
from zen_settings import zen_settings
import re
import stparser

newline = '\n'
"Newline symbol"

caret_placeholder = '{%::zen-caret::%}'

default_tag = 'div'

re_tag = re.compile(r'<\/?[\w:\-]+(?:\s+[\w\-:]+(?:\s*=\s*(?:(?:"[^"]*")|(?:\'[^\']*\')|[^>\s]+))?)*\s*(\/?)>$')

profiles = {}
"Available output profiles"

default_profile = {
	'tag_case': 'lower',         # values are 'lower', 'upper'
	'attr_case': 'lower',        # values are 'lower', 'upper'
	'attr_quotes': 'double',     # values are 'single', 'double'
	
	'tag_nl': 'decide',          # each tag on new line, values are True, False, 'decide'
	
	'place_cursor': True,        # place cursor char — | (pipe) — in output
	
	'indent': True,              # indent tags
	
	'inline_break': 3,           # how many inline elements should be to force line break (set to 0 to disable)
	
	'self_closing_tag': 'xhtml'  # use self-closing style for writing empty elements, e.g. <br /> or <br>. 
                                 # values are True, False, 'xhtml'
}

basic_filters = 'html';
"Filters that will be applied for unknown syntax"

max_tabstop = 0
"Maximum tabstop index for current session"

def char_at(text, pos):
	"""
	Returns character at specified index of text.
	If index if out of range, returns empty string
	"""
	return text[pos] if pos < len(text) else ''

def has_deep_key(obj, key):
	"""
	Check if <code>obj</code> dictionary contains deep key. For example,
	example, it will allow you to test existance of my_dict[key1][key2][key3],
	testing existance of my_dict[key1] first, then my_dict[key1][key2], 
	and finally my_dict[key1][key2][key3]
	@param obj: Dictionary to test
	@param obj: dict
	@param key: Deep key to test. Can be list (like ['key1', 'key2', 'key3']) or
	string (like 'key1.key2.key3')
	@type key: list, tuple, str
	@return: bool
	"""
	if isinstance(key, str):
		key = key.split('.')
		
	last_obj = obj
	for v in key:
		if hasattr(last_obj, v):
			last_obj = getattr(last_obj, v)
		elif last_obj.has_key(v):
			last_obj = last_obj[v]
		else:
			return False
	
	return True
		

def is_allowed_char(ch):
	"""
	Test if passed symbol is allowed in abbreviation
	@param ch: Symbol to test
	@type ch: str
	@return: bool
	"""
	return ch.isalnum() or ch in "#.>+*:$-_!@[]()|"

def split_by_lines(text, remove_empty=False):
	"""
	Split text into lines. Set <code>remove_empty</code> to true to filter out
	empty lines
	@param text: str
	@param remove_empty: bool
	@return list
	"""
	lines = text.splitlines()
	
	return remove_empty and [line for line in lines if line.strip()] or lines

def make_map(prop):
	"""
	Helper function that transforms string into dictionary for faster search
	@param prop: Key name in <code>zen_settings['html']</code> dictionary
	@type prop: str
	"""
	obj = {}
	for a in zen_settings['html'][prop].split(','):
		obj[a] = True
		
	zen_settings['html'][prop] = obj

def create_profile(options):
	"""
	Create profile by adding default values for passed optoin set
	@param options: Profile options
	@type options: dict
	"""
	for k, v in default_profile.items():
		options.setdefault(k, v)
	
	return options

def setup_profile(name, options = {}):
	"""
	@param name: Profile name
	@type name: str
	@param options: Profile options
	@type options: dict
	"""
	profiles[name.lower()] = create_profile(options);

def get_newline():
	"""
	Returns newline symbol which is used in editor. This function must be 
	redefined to return current editor's settings 
	@return: str
	"""
	return newline

def set_newline(char):
	"""
	Sets newline character used in Zen Coding
	"""
	global newline
	newline = char

def string_to_hash(text):
	"""
	Helper function that transforms string into hash
	@return: dict
	"""
	obj = {}
	items = text.split(",")
	for i in items:
		obj[i] = True
		
	return obj

def pad_string(text, pad):
	"""
	Indents string with space characters (whitespace or tab)
	@param text: Text to indent
	@type text: str
	@param pad: Indentation level (number) or indentation itself (string)
	@type pad: int, str
	@return: str
	"""
	pad_str = ''
	result = ''
	if isinstance(pad, basestring):
		pad_str = pad
	else:
		pad_str = get_indentation() * pad
		
	nl = get_newline()
	
	lines = split_by_lines(text)
	
	if lines:
		result += lines[0]
		for line in lines[1:]:
			result += nl + pad_str + line
			
	return result

def is_snippet(abbr, doc_type = 'html'):
	"""
	Check is passed abbreviation is a snippet
	@return bool
	"""
	return get_snippet(doc_type, abbr) and True or False

def is_ends_with_tag(text):
	"""
	Test is string ends with XHTML tag. This function used for testing if '<'
	symbol belogs to tag or abbreviation 
	@type text: str
	@return: bool
	"""
	return re_tag.search(text) != None

def get_elements_collection(resource, type):
	"""
	Returns specified elements collection (like 'empty', 'block_level') from
	<code>resource</code>. If collections wasn't found, returns empty object
	@type resource: dict
	@type type: str
	@return: dict
	"""
	if 'element_types' in resource and type in resource['element_types']:
		return resource['element_types'][type]
	else:
		return {}
	
def replace_variables(text, vars=None):
	"""
	Replace variables like ${var} in string
	@param text: str
	@return: str
	"""
	if vars is None:
	    vars = zen_settings['variables']
	return re.sub(r'\$\{([\w\-]+)\}', lambda m: m.group(1) in vars and vars[m.group(1)] or m.group(0), text)

def get_abbreviation(res_type, abbr):
	"""
	Returns abbreviation value from data set
	@param res_type: Resource type (html, css, ...)
	@type res_type: str
	@param abbr: Abbreviation name
	@type abbr: str
	@return dict, None
	"""
	return get_settings_resource(res_type, abbr, 'abbreviations')

def get_snippet(res_type, snippet_name):
	"""
	Returns snippet value from data set
	@param res_type: Resource type (html, css, ...)
	@type res_type: str
	@param snippet_name: Snippet name
	@type snippet_name: str
	@return dict, None
	"""
	return get_settings_resource(res_type, snippet_name, 'snippets');

def get_variable(name):
	"""
	Returns variable value
	 @return: str
	"""
	return zen_settings['variables'][name]

def set_variable(name, value):
	"""
	Set variable value
	"""
	zen_settings['variables'][name] = value

def get_indentation():
	"""
	Returns indentation string
	@return {String}
	"""
	return get_variable('indentation');

def create_resource_chain(syntax, name):
	"""
	Creates resource inheritance chain for lookups
	@param syntax: Syntax name
	@type syntax: str
	@param name: Resource name
	@type name: str
	@return: list
	"""
	result = []
	
	if syntax in zen_settings:
		resource = zen_settings[syntax]
		if name in resource:
			result.append(resource[name])
		if 'extends' in resource:
			# find resource in ancestors
			for type in resource['extends']:
				if  has_deep_key(zen_settings, [type, name]):
					result.append(zen_settings[type][name])
				
	return result

def get_resource(syntax, name):
	"""
	Get resource collection from settings file for specified syntax. 
	It follows inheritance chain if resource wasn't directly found in
	syntax settings
	@param syntax: Syntax name
	@type syntax: str
	@param name: Resource name
	@type name: str
	"""
	chain = create_resource_chain(syntax, name)
	return chain[0] if chain else None

def get_settings_resource(syntax, abbr, name):
	"""
	Returns resurce value from data set with respect of inheritance
	@param syntax: Resource syntax (html, css, ...)
	@type syntax: str
	@param abbr: Abbreviation name
	@type abbr: str
	@param name: Resource name ('snippets' or 'abbreviation')
	@type name: str
	@return dict, None
	"""
	for item in create_resource_chain(syntax, name):
		if abbr in item:
			return item[abbr]
		
	return None

def get_word(ix, text):
	"""
	Get word, starting at <code>ix</code> character of <code>text</code>
	@param ix: int
	@param text: str
	"""
	m = re.match(r'^[\w\-:\$]+', text[ix:])
	return m.group(0) if m else ''
	
def extract_attributes(attr_set):
	"""
	Extract attributes and their values from attribute set 
 	@param attr_set: str
	"""
	attr_set = attr_set.strip()
	loop_count = 100 # endless loop protection
	re_string = r'^(["\'])((?:(?!\1)[^\\]|\\.)*)\1'
	result = []
		
	while attr_set and loop_count:
		loop_count -= 1
		attr_name = get_word(0, attr_set)
		attr = None
		if attr_name:
			attr = {'name': attr_name, 'value': ''}
			
			# let's see if attribute has value
			ch = attr_set[len(attr_name)] if len(attr_set) > len(attr_name) else ''
			if ch == '=':
				ch2 = attr_set[len(attr_name) + 1]
				if ch2 in '"\'':
					# we have a quoted string
					m = re.match(re_string, attr_set[len(attr_name) + 1:])
					if m:
						attr['value'] = m.group(2)
						attr_set = attr_set[len(attr_name) + len(m.group(0)) + 1:].strip()
					else:
						# something wrong, break loop
						attr_set = ''
				else:
					# unquoted string
					m = re.match(r'^(.+?)(\s|$)', attr_set[len(attr_name) + 1:])
					if m:
						attr['value'] = m.group(1)
						attr_set = attr_set[len(attr_name) + len(m.group(1)) + 1:].strip()
					else:
						# something wrong, break loop
						attr_set = ''
				
			else:
				attr_set = attr_set[len(attr_name):].strip()
		else:
			# something wrong, can't extract attribute name
			break
		
		if attr: result.append(attr)
		
	return result

def parse_attributes(text):
	"""
	Parses tag attributes extracted from abbreviation
	"""
	
#	Example of incoming data:
#	#header
#	.some.data
#	.some.data#header
#	[attr]
#	#item[attr=Hello other="World"].class

	result = []
	class_name = None
	char_map = {'#': 'id', '.': 'class'}
	
	# walk char-by-char
	i = 0
	il = len(text)
		
	while i < il:
		ch = text[i]
		
		if ch == '#': # id
			val = get_word(i, text[1:])
			result.append({'name': char_map[ch], 'value': val})
			i += len(val) + 1
			
		elif ch == '.': #class
			val = get_word(i, text[1:])
			if not class_name:
				# remember object pointer for value modification
				class_name = {'name': char_map[ch], 'value': ''}
				result.append(class_name)
			
			if class_name['value']:
				class_name['value'] += ' ' + val
			else:
				class_name['value'] = val
			
			i += len(val) + 1
				
		elif ch == '[': # begin attribute set
			# search for end of set
			end_ix = text.find(']', i)
			if end_ix == -1:
				# invalid attribute set, stop searching
				i = len(text)
			else:
				result.extend(extract_attributes(text[i + 1:end_ix]))
				i = end_ix
		else:
			i += 1
		
		
	return result

class AbbrGroup(object):
	"""
	Abreviation's group element
	"""
	def __init__(self, parent=None):
		"""
		@param parent: Parent group item element
		@type parent: AbbrGroup
		"""
		self.expr = ''
		self.parent = parent
		self.children = []
		
	def add_child(self):
		child = AbbrGroup(self)
		self.children.append(child)
		return child
	
	def clean_up(self):
		for item in self.children:
			expr = item.expr
			if not expr:
				self.children.remove(item)
			else:
				# remove operators at the and of expression
				item.clean_up()

def split_by_groups(abbr):
	"""
	Split abbreviation by groups
	@type abbr: str
	@return: AbbrGroup
	"""
	root = AbbrGroup()
	last_parent = root
	cur_item = root.add_child()
	stack = []
	i = 0
	il = len(abbr)
	
	while i < il:
		ch = abbr[i]
		if ch == '(':
			# found new group
			operator = i and abbr[i - 1] or ''
			if operator == '>':
				stack.append(cur_item)
				last_parent = cur_item
			else:
				stack.append(last_parent)
			cur_item = None
		elif ch == ')':
			last_parent = stack.pop()
			cur_item = None
			next_char = char_at(abbr, i + 1)
			if next_char == '+' or next_char == '>': 
				# next char is group operator, skip it
				i += 1
		else:
			if ch == '+' or ch == '>':
				# skip operator if it's followed by parenthesis
				next_char = char_at(abbr, i + 1)
				if next_char == '(':
					i += 1 
					continue
			
			if not cur_item:
				cur_item = last_parent.add_child()
			cur_item.expr += ch
			
		i += 1
	
	root.clean_up()
	return root

def rollout_tree(tree, parent=None):
	"""
	Roll outs basic Zen Coding tree into simplified, DOM-like tree.
	The simplified tree, for example, represents each multiplied element 
	as a separate element sets with its own content, if exists.
	 
	The simplified tree element contains some meta info (tag name, attributes, 
	etc.) as well as output strings, which are exactly what will be outputted
	after expanding abbreviation. This tree is used for <i>filtering</i>:
	you can apply filters that will alter output strings to get desired look
	of expanded abbreviation.
	 
	@type tree: Tag
	@param parent: ZenNode
	"""
	if not parent:
		parent = ZenNode(tree)
		
	how_many = 1
	tag_content = ''
	
	for child in tree.children:
		how_many = child.count
		
		if child.repeat_by_lines:
			# it's a repeating element
			tag_content = split_by_lines(child.get_content(), True)
			how_many = max(len(tag_content), 1)
		else:
			tag_content = child.get_content()
		
		for j in range(how_many):
			tag = ZenNode(child)
			parent.add_child(tag)
			tag.counter = j + 1
			
			if child.children:
				rollout_tree(child, tag)
				
			add_point = tag.find_deepest_child() or tag
			
			if tag_content:
				if isinstance(tag_content, basestring):
					add_point.content = tag_content
				else:
					add_point.content = tag_content[j] or ''
					
	return parent

def run_filters(tree, profile, filter_list):
	"""
	Runs filters on tree
	@type tree: ZenNode
	@param profile: str, object
	@param filter_list: str, list
	@return: ZenNode
	"""
	import filters
	
	if isinstance(profile, basestring) and profile in profiles:
		profile = profiles[profile];
	
	if not profile:
		profile = profiles['plain']
		
	if isinstance(filter_list, basestring):
		filter_list = re.split(r'[\|,]', filter_list)
		
	for name in filter_list:
		name = name.strip()
		if name and name in filters.filter_map:
			tree = filters.filter_map[name](tree, profile)
			
	return tree

def abbr_to_primary_tree(abbr, doc_type='html'):
	"""
	Transforms abbreviation into a primary internal tree. This tree should'n 
	be used ouside of this scope
	@param abbr: Abbreviation to transform
	@type abbr: str
	@param doc_type: Document type (xsl, html), a key of dictionary where to
	search abbreviation settings
	@type doc_type: str
	@return: Tag
	"""
	root = Tag('', 1, doc_type)
	token = re.compile(r'([\+>])?([a-z@\!\#\.][\w:\-]*)((?:(?:[#\.][\w\-\$]+)|(?:\[[^\]]+\]))+)?(\*(\d*))?(\+$)?', re.IGNORECASE)
	
	if not abbr:
		return None
	
	def expando_replace(m):
		ex = m.group(0)
		a = get_abbreviation(doc_type, ex)
		return a and a.value or ex
		
	def token_expander(operator, tag_name, attrs, has_multiplier, multiplier, has_expando):
		multiply_by_lines = (has_multiplier and not multiplier)
		multiplier = multiplier and int(multiplier) or 1
		
		tag_ch = tag_name[0]
		if tag_ch == '#' or tag_ch == '.':
			if attrs: attrs = tag_name + attrs
			else: attrs = tag_name
			tag_name = default_tag
		
		if has_expando:
			tag_name += '+'
		
		current = is_snippet(tag_name, doc_type) and Snippet(tag_name, multiplier, doc_type) or Tag(tag_name, multiplier, doc_type)
		
		if attrs:
			attrs = parse_attributes(attrs)
			for attr in attrs:
				current.add_attribute(attr['name'], attr['value'])
			
		# dive into tree
		if operator == '>' and token_expander.last:
			token_expander.parent = token_expander.last;
			
		token_expander.parent.add_child(current)
		token_expander.last = current
		
		if multiply_by_lines:
			root.multiply_elem = current
		
		return ''
		
	# replace expandos
	abbr = re.sub(r'([a-z][a-z0-9]*)\+$', expando_replace, abbr)
	
	token_expander.parent = root
	token_expander.last = None
	
	
#	abbr = re.sub(token, lambda m: token_expander(m.group(1), m.group(2), m.group(3), m.group(4), m.group(5), m.group(6), m.group(7)), abbr)
	# Issue from Einar Egilsson
	abbr = token.sub(lambda m: token_expander(m.group(1), m.group(2), m.group(3), m.group(4), m.group(5), m.group(6)), abbr)
	
	root.last = token_expander.last
	
	# empty 'abbr' variable means that abbreviation was expanded successfully, 
	# non-empty variable means there was a syntax error
	return not abbr and root or None;

def expand_group(group, doc_type, parent):
	"""
	Expand single group item 
	@param group: AbbrGroup
	@param doc_type: str
	@param parent: Tag
	"""
	tree = abbr_to_primary_tree(group.expr, doc_type)
	last_item = None
		
	if tree:
		for item in tree.children:
			last_item = item
			parent.add_child(last_item)
	else:
		raise Exception('InvalidGroup')
	
	
	# set repeating element to the topmost node
	root = parent
	while root.parent:
		root = root.parent
	
	root.last = tree.last
	if tree.multiply_elem:
		root.multiply_elem = tree.multiply_elem
		
	# process child groups
	if group.children:
		add_point = last_item.find_deepest_child() or last_item
		for child in group.children:
			expand_group(child, doc_type, add_point)

def replace_unescaped_symbol(text, symbol, replace):
	"""
	Replaces unescaped symbols in <code>text</code>. For example, the '$' symbol
	will be replaced in 'item$count', but not in 'item\$count'.
	@param text: Original string
	@type text: str
	@param symbol: Symbol to replace
	@type symbol: st
	@param replace: Symbol replacement
	@type replace: str, function 
	@return: str
	"""
	i = 0
	il = len(text)
	sl = len(symbol)
	match_count = 0
		
	while i < il:
		if text[i] == '\\':
			# escaped symbol, skip next character
			i += sl + 1
		elif text[i:i + sl] == symbol:
			# have match
			cur_sl = sl
			match_count += 1
			new_value = replace
			if callable(new_value):
				replace_data = replace(text, symbol, i, match_count)
				if replace_data:
					cur_sl = len(replace_data[0])
					new_value = replace_data[1]
				else:
					new_value = False
			
			if new_value is False: # skip replacement
				i += 1
				continue
			
			text = text[0:i] + new_value + text[i + cur_sl:]
			# adjust indexes
			il = len(text)
			i += len(new_value)
		else:
			i += 1
	
	return text
	
def run_action(name, *args, **kwargs):
	"""
	 Runs Zen Coding action. For list of available actions and their
	 arguments see zen_actions.py file.
	 @param name: Action name 
	 @type name: str 
	 @param args: Additional arguments. It may be array of arguments
	 or inline arguments. The first argument should be <code>zen_editor</code> instance
	 @type args: list
	 @example
	 zen_coding.run_actions('expand_abbreviation', zen_editor)
	 zen_coding.run_actions('wrap_with_abbreviation', zen_editor, 'div')  
	"""
	import zen_actions
	
	try:
		if hasattr(zen_actions, name):
			return getattr(zen_actions, name)(*args, **kwargs)
	except:
		return False

def expand_abbreviation(abbr, syntax='html', profile_name='plain'):
	"""
	Expands abbreviation into a XHTML tag string
	@type abbr: str
	@return: str
	"""
	tree_root = parse_into_tree(abbr, syntax);
	if tree_root:
		tree = rollout_tree(tree_root)
		apply_filters(tree, syntax, profile_name, tree_root.filters)
		return replace_variables(tree.to_string())
	
	return ''

def extract_abbreviation(text):
	"""
	Extracts abbreviations from text stream, starting from the end
	@type text: str
	@return: Abbreviation or empty string
	"""
	cur_offset = len(text)
	start_index = -1
	brace_count = 0
	
	while True:
		cur_offset -= 1
		if cur_offset < 0:
			# moved at string start
			start_index = 0
			break
		
		ch = text[cur_offset]
		
		if ch == ']':
			brace_count += 1
		elif ch == '[':
			brace_count -= 1
		else:
			if brace_count: 
				# respect all characters inside attribute sets
				continue
			if not is_allowed_char(ch) or (ch == '>' and is_ends_with_tag(text[0:cur_offset + 1])):
				# found stop symbol
				start_index = cur_offset + 1
				break
		
	return text[start_index:] if start_index != -1 else ''

def parse_into_tree(abbr, doc_type='html'):
	"""
	Parses abbreviation into a node set
	@param abbr: Abbreviation to transform
	@type abbr: str
	@param doc_type: Document type (xsl, html), a key of dictionary where to
	search abbreviation settings
	@type doc_type: str
	@return: Tag
	"""
	# remove filters from abbreviation
	filter_list = []
	
	def filter_replace(m):
		filter_list.append(m.group(1))
		return ''
	
	re_filter = re.compile(r'\|([\w\|\-]+)$')
	abbr = re_filter.sub(filter_replace, abbr)
	
	# split abbreviation by groups
	group_root = split_by_groups(abbr)
	tree_root = Tag('', 1, doc_type)
	
	# then recursively expand each group item
	try:
		for item in group_root.children:
			expand_group(item, doc_type, tree_root)
	except:
		# there's invalid group, stop parsing
		return None
	
	tree_root.filters = ''.join(filter_list)
	return tree_root

def is_inside_tag(html, cursor_pos):
	re_tag = re.compile(r'^<\/?\w[\w\:\-]*.*?>')
	
	# search left to find opening brace
	pos = cursor_pos
	while pos > -1:
		if html[pos] == '<': break
		pos -= 1
	
	
	if pos != -1:
		m = re_tag.match(html[pos:]);
		if m and cursor_pos > pos and cursor_pos < pos + len(m.group(0)):
			return True

	return False

def wrap_with_abbreviation(abbr, text, doc_type='html', profile='plain'):
	"""
	Wraps passed text with abbreviation. Text will be placed inside last
	expanded element
	@param abbr: Abbreviation
	@type abbr: str
	
	@param text: Text to wrap
	@type text: str
	
	@param doc_type: Document type (html, xml, etc.)
	@type doc_type: str
	
	@param profile: Output profile's name.
	@type profile: str
	@return {String}
	"""
	tree_root = parse_into_tree(abbr, doc_type)
	if tree_root:
		repeat_elem = tree_root.multiply_elem or tree_root.last
		repeat_elem.set_content(text)
		repeat_elem.repeat_by_lines = bool(tree_root.multiply_elem)
		
		tree = rollout_tree(tree_root)
		apply_filters(tree, doc_type, profile, tree_root.filters);
		return replace_variables(tree.to_string())
	
	return None

def get_caret_placeholder():
	"""
	Returns caret placeholder
	@return: str
	"""
	if callable(caret_placeholder):
		return caret_placeholder()
	else:
		return caret_placeholder

def set_caret_placeholder(value):
	"""
	Set caret placeholder: a string (like '|') or function.
	You may use a function as a placeholder generator. For example,
	TextMate uses ${0}, ${1}, ..., ${n} natively for quick Tab-switching
	between them.
	@param {String|Function}
	"""
	global caret_placeholder
	caret_placeholder = value

def apply_filters(tree, syntax, profile, additional_filters=None):
	"""
	Applies filters to tree according to syntax
	@param tree: Tag tree to apply filters to
	@type tree: ZenNode
	@param syntax: Syntax name ('html', 'css', etc.)
	@type syntax: str
	@param profile: Profile or profile's name
	@type profile: str, object
	@param additional_filters: List or pipe-separated string of additional filters to apply
	@type additional_filters: str, list 
	 
	@return: ZenNode
	"""
	_filters = get_resource(syntax, 'filters') or basic_filters
		
	if additional_filters:
		_filters += '|'
		if isinstance(additional_filters, basestring):
			_filters += additional_filters
		else:
			_filters += '|'.join(additional_filters)
		
	if not _filters:
		# looks like unknown syntax, apply basic filters
		_filters = basic_filters
		
	return run_filters(tree, profile, _filters)

def replace_counter(text, value):
	"""
	 Replaces '$' character in string assuming it might be escaped with '\'
	 @type text: str
	 @type value: str, int
	 @return: str
	"""
	symbol = '$'
	value = str(value)
	
	def replace_func(tx, symbol, pos, match_num):
		if char_at(tx, pos + 1) == '{' or char_at(tx, pos + 1).isdigit():
			# it's a variable, skip it
			return False
		
		# replace sequense of $ symbols with padded number  
		j = pos + 1
		if j < len(text):
			while tx[j] == '$' and char_at(tx, j + 1) != '{': j += 1
		
		return (tx[pos:j], value.zfill(j - pos))
	
	return replace_unescaped_symbol(text, symbol, replace_func)

def upgrade_tabstops(node):
	"""
	Upgrades tabstops in zen node in order to prevent naming conflicts
	@type node: ZenNode
	@param offset: Tab index offset
	@type offset: int
	@returns Maximum tabstop index in element
	"""
	max_num = [0]
	props = ('start', 'end', 'content')
	
	def _replace(m):
		num = int(m.group(1) or m.group(2))
		if num > max_num[0]: max_num[0] = num
		return re.sub(r'\d+', str(num + max_tabstop), m.group(0), 1)
	
	for prop in props:
		node.__setattr__(prop, re.sub(r'\$(\d+)|\$\{(\d+):[^\}]+\}', _replace, node.__getattribute__(prop)))
		
	globals()['max_tabstop'] += max_num[0] + 1
		
	return max_num[0]

def unescape_text(text):
	"""
	Unescapes special characters used in Zen Coding, like '$', '|', etc.
	@type text: str
	@return: str
	"""
	return re.sub(r'\\(.)', r'\1', text)


def get_profile(name):
	"""
	Get profile by it's name. If profile wasn't found, returns 'plain' profile
	"""
	return profiles[name] if name in profiles else profiles['plain']

def update_settings(settings):
	globals()['zen_settings'] = settings
	
class Tag(object):
	def __init__(self, name, count=1, doc_type='html'):
		"""
		@param name: Tag name
		@type name: str
		@param count:  How many times this tag must be outputted
		@type count: int
		@param doc_type: Document type (xsl, html)
		@type doc_type: str
		"""
		name = name.lower()
		
		abbr = get_abbreviation(doc_type, name)
		
		if abbr and abbr.type == stparser.TYPE_REFERENCE:
			abbr = get_abbreviation(doc_type, abbr.value)
		
		self.name = abbr and abbr.value['name'] or name.replace('+', '')
		self.count = count
		self.children = []
		self.attributes = []
		self.multiply_elem = None
		self.__attr_hash = {}
		self._abbr = abbr
		self.__content = ''
		self.repeat_by_lines = False
		self._res = zen_settings.has_key(doc_type) and zen_settings[doc_type] or {}
		self.parent = None
		
		# add default attributes
		if self._abbr and 'attributes' in self._abbr.value:
			for a in self._abbr.value['attributes']:
				self.add_attribute(a['name'], a['value'])
		
	def add_child(self, tag):
		"""
		Add new child
		@type tag: Tag
		"""
		tag.parent = self
		self.children.append(tag)
		
	def add_attribute(self, name, value):
		"""
		Add attribute to tag. If the attribute with the same name already exists,
		it will be overwritten, but if it's name is 'class', it will be merged
		with the existed one
		@param name: Attribute nama
		@type name: str
		@param value: Attribute value
		@type value: str
		"""
		
		# the only place in Tag where pipe (caret) character may exist
		# is the attribute: escape it with internal placeholder
		value = replace_unescaped_symbol(value, '|', get_caret_placeholder());
		
		if name in self.__attr_hash:
#			attribue already exists
			a = self.__attr_hash[name]
			if name == 'class':
#				'class' is a magic attribute
				if a['value']:
					value = ' ' + value
				a['value'] += value
			else:
				a['value'] = value
		else:
			a = {'name': name, 'value': value}
			self.__attr_hash[name] = a
			self.attributes.append(a)
	
	def has_tags_in_content(self):
		"""
		This function tests if current tags' content contains XHTML tags. 
	 	This function is mostly used for output formatting
		"""
		return self.get_content() and re_tag.search(self.get_content())
	
	def get_content(self):
		return self.__content
	
	def set_content(self, value):
		self.__content = value
		
	def set_content(self, content): #@DuplicatedSignature
		self.__content = content
		
	def get_content(self): #@DuplicatedSignature
		return self.__content
	
	def find_deepest_child(self):
		"""
		Search for deepest and latest child of current element.
		Returns None if there's no children
	 	@return Tag or None 
		"""
		if not self.children:
			return None
			
		deepest_child = self
		while True:
			deepest_child = deepest_child.children[-1]
			if not deepest_child.children:
				break
		
		return deepest_child
	
class Snippet(Tag):
	def __init__(self, name, count=1, doc_type='html'):
		super(Snippet, self).__init__(name, count, doc_type)
		self.value = replace_unescaped_symbol(get_snippet(doc_type, name), '|', get_caret_placeholder())
		self.attributes = {'id': get_caret_placeholder(), 'class': get_caret_placeholder()}
		self._res = zen_settings[doc_type]		
	
	def is_block(self):
		return True
	
class ZenNode(object):
	"""
	Creates simplified tag from Zen Coding tag
	"""
	def __init__(self, tag):
		"""
		@type tag: Tag
		"""
		self.type = 'snippet' if isinstance(tag, Snippet) else 'tag'
		self.name = tag.name
		self.attributes = tag.attributes
		self.children = [];
		self.counter = 1
		
		self.source = tag
		"Source element from which current tag was created"
		
		# relations
		self.parent = None
		self.next_sibling = None
		self.previous_sibling = None
		
		# output params
		self.start = ''
		self.end = ''
		self.content = ''
		self.padding = ''

	def add_child(self, tag):
		"""
		@type tag: ZenNode
		"""
		tag.parent = self
		
		if self.children:
			last_child = self.children[-1]
			tag.previous_sibling = last_child
			last_child.next_sibling = tag
		
		self.children.append(tag)
		
	def get_attribute(self, name):
		"""
		Get attribute's value.
		@type name: str
		@return: None if attribute wasn't found
		"""
		name = name.lower()
		for attr in self.attributes:
			if attr['name'].lower() == name:
				return attr['value']
		
		return None
	
	def is_unary(self):
		"""
		Test if current tag is unary (no closing tag)
		@return: bool
		"""
		if self.type == 'snippet':
			return False
			
		return (self.source._abbr and self.source._abbr.value['is_empty']) or (self.name in get_elements_collection(self.source._res, 'empty'))
	
	def is_inline(self):
		"""
		Test if current tag is inline-level (like <strong>, <img>)
		@return: bool
		"""
		return self.name in get_elements_collection(self.source._res, 'inline_level')
	
	def is_block(self):
		"""
		Test if current element is block-level
		@return: bool
		"""
		return self.type == 'snippet' or not self.is_inline()
	
	def has_tags_in_content(self):
		"""
		This function tests if current tags' content contains xHTML tags. 
		This function is mostly used for output formatting
		"""
		return self.content and re_tag.search(self.content)
	
	def has_children(self):
		"""
		Check if tag has child elements
		@return: bool
		"""
		return bool(self.children)
	
	def has_block_children(self):
		"""
		Test if current tag contains block-level children
		@return: bool
		"""
		if self.has_tags_in_content() and self.is_block():
			return True
		
		for item in self.children:
			if item.is_block():
				return True
			
		return False
	
	def find_deepest_child(self):
		"""
		Search for deepest and latest child of current element
		Returns None if there's no children
		@return: ZenNode|None 
		"""
		if not self.children:
			return None
			
		deepest_child = self
		while True:
			deepest_child = deepest_child.children[-1]
			if not deepest_child.children:
				break
		
		return deepest_child
	
	def to_string(self):
		"@return {String}"
		content = ''.join([item.to_string() for item in self.children])
		return self.start + self.content + content + self.end
		
# create default profiles
setup_profile('xhtml');
setup_profile('html', {'self_closing_tag': False});
setup_profile('xml', {'self_closing_tag': True, 'tag_nl': True});
setup_profile('plain', {'tag_nl': False, 'indent': False, 'place_cursor': False});

# This method call explicity loads default settings from zen_settings.py on start up
# Comment this line if you want to load data from other resources (like editor's 
# native snippet) 
update_settings(stparser.get_settings())

########NEW FILE########
__FILENAME__ = zen_editor
'''
High-level editor interface that communicates with underlying editor (like
Espresso, Coda, etc.) or browser.
Basically, you should call <code>set_context(obj)</code> method to
set up undelying editor context before using any other method.

This interface is used by <i>zen_actions.py</i> for performing different
actions like <b>Expand abbreviation</b>

@example
import zen_editor
zen_editor.set_context(obj);
//now you are ready to use editor object
zen_editor.get_selection_range();

@author Sergey Chikuyonok (serge.che@gmail.com)
@link http://chikuyonok.ru
'''
class ZenEditor():
	def __init__(self):
		pass

	def set_context(self, context):
		"""
		Setup underlying editor context. You should call this method
		<code>before</code> using any Zen Coding action.
		@param context: context object
		"""
		pass

	def get_selection_range(self):
		"""
		Returns character indexes of selected text
		@return: list of start and end indexes
		@example
		start, end = zen_editor.get_selection_range();
		print('%s, %s' % (start, end))
		"""
		return 0, 0


	def create_selection(self, start, end=None):
		"""
		Creates selection from <code>start</code> to <code>end</code> character
		indexes. If <code>end</code> is ommited, this method should place caret
		and <code>start</code> index
		@type start: int
		@type end: int
		@example
		zen_editor.create_selection(10, 40)
		# move caret to 15th character
		zen_editor.create_selection(15)
		"""
		pass

	def get_current_line_range(self):
		"""
		Returns current line's start and end indexes
		@return: list of start and end indexes
		@example
		start, end = zen_editor.get_current_line_range();
		print('%s, %s' % (start, end))
		"""
		return 0, 0

	def get_caret_pos(self):
		""" Returns current caret position """
		return 0

	def set_caret_pos(self, pos):
		"""
		Set new caret position
		@type pos: int
		"""
		pass

	def get_current_line(self):
		"""
		Returns content of current line
		@return: str
		"""
		return ''

	def replace_content(self, value, start=None, end=None):
		"""
		Replace editor's content or it's part (from <code>start</code> to
		<code>end</code> index). If <code>value</code> contains
		<code>caret_placeholder</code>, the editor will put caret into
		this position. If you skip <code>start</code> and <code>end</code>
		arguments, the whole target's content will be replaced with
		<code>value</code>.

		If you pass <code>start</code> argument only,
		the <code>value</code> will be placed at <code>start</code> string
		index of current content.

		If you pass <code>start</code> and <code>end</code> arguments,
		the corresponding substring of current target's content will be
		replaced with <code>value</code>
		@param value: Content you want to paste
		@type value: str
		@param start: Start index of editor's content
		@type start: int
		@param end: End index of editor's content
		@type end: int
		"""
		pass

	def get_content(self):
		"""
		Returns editor's content
		@return: str
		"""
		return ''

	def get_syntax(self):
		"""
		Returns current editor's syntax mode
		@return: str
		"""
		return 'html'

	def get_profile_name(self):
		"""
		Returns current output profile name (@see zen_coding#setup_profile)
		@return {String}
		"""
		return 'xhtml'

########NEW FILE########
__FILENAME__ = zen_settings
"""
Zen Coding settings
@author Sergey Chikuyonok (serge.che@gmail.com)
@link http://chikuyonok.ru
"""
zen_settings = {
			
#	Variables that can be placed inside snippets or abbreviations as ${variable}
#	${child} variable is reserved, don't use it
	'variables': {
		'lang': 'en',
		'locale': 'en-US',
		'charset': 'UTF-8',
		'profile': 'xhtml',
		
#		Inner element indentation
		'indentation': '\t'
	},
	
	# common settings are used for quick injection of user-defined snippets
	'common': {
		
	},
	
	'css': {
		'extends': 'common',
		'snippets': {
			"@i": "@import url(|);",
			"@m": "@media print {\n\t|\n}",
			"@f": "@font-face {\n\tfont-family:|;\n\tsrc:url(|);\n}",
			"!": "!important",
			"pos": "position:|;",
			"pos:s": "position:static;",
			"pos:a": "position:absolute;",
			"pos:r": "position:relative;",
			"pos:f": "position:fixed;",
			"t": "top:|;",
			"t:a": "top:auto;",
			"r": "right:|;",
			"r:a": "right:auto;",
			"b": "bottom:|;",
			"b:a": "bottom:auto;",
			"brad": "-webkit-border-radius: ${1:radius};\n-moz-border-radius: $1;\n-ms-border-radius: $1;\nborder-radius: $1;",
			"bsha": "-webkit-box-shadow: ${1:hoff} ${2:voff} ${3:blur} ${4:rgba(0,0,0,0.5)};\n-moz-box-shadow: $1 $2 $3 $4;\n-ms-box-shadow: $1 $2 $3 $4;\nbox-shadow: $1 $2 $3 $4;",
			"l": "left:|;",
			"l:a": "left:auto;",
			"z": "z-index:|;",
			"z:a": "z-index:auto;",
			"fl": "float:|;",
			"fl:n": "float:none;",
			"fl:l": "float:left;",
			"fl:r": "float:right;",
			"cl": "clear:|;",
			"cl:n": "clear:none;",
			"cl:l": "clear:left;",
			"cl:r": "clear:right;",
			"cl:b": "clear:both;",
			"d": "display:|;",
			"d:n": "display:none;",
			"d:b": "display:block;",
			"d:i": "display:inline;",
			"d:ib": "display:inline-block;",
			"d:li": "display:list-item;",
			"d:ri": "display:run-in;",
			"d:cp": "display:compact;",
			"d:tb": "display:table;",
			"d:itb": "display:inline-table;",
			"d:tbcp": "display:table-caption;",
			"d:tbcl": "display:table-column;",
			"d:tbclg": "display:table-column-group;",
			"d:tbhg": "display:table-header-group;",
			"d:tbfg": "display:table-footer-group;",
			"d:tbr": "display:table-row;",
			"d:tbrg": "display:table-row-group;",
			"d:tbc": "display:table-cell;",
			"d:rb": "display:ruby;",
			"d:rbb": "display:ruby-base;",
			"d:rbbg": "display:ruby-base-group;",
			"d:rbt": "display:ruby-text;",
			"d:rbtg": "display:ruby-text-group;",
			"v": "visibility:|;",
			"v:v": "visibility:visible;",
			"v:h": "visibility:hidden;",
			"v:c": "visibility:collapse;",
			"ov": "overflow:|;",
			"ov:v": "overflow:visible;",
			"ov:h": "overflow:hidden;",
			"ov:s": "overflow:scroll;",
			"ov:a": "overflow:auto;",
			"ovx": "overflow-x:|;",
			"ovx:v": "overflow-x:visible;",
			"ovx:h": "overflow-x:hidden;",
			"ovx:s": "overflow-x:scroll;",
			"ovx:a": "overflow-x:auto;",
			"ovy": "overflow-y:|;",
			"ovy:v": "overflow-y:visible;",
			"ovy:h": "overflow-y:hidden;",
			"ovy:s": "overflow-y:scroll;",
			"ovy:a": "overflow-y:auto;",
			"ovs": "overflow-style:|;",
			"ovs:a": "overflow-style:auto;",
			"ovs:s": "overflow-style:scrollbar;",
			"ovs:p": "overflow-style:panner;",
			"ovs:m": "overflow-style:move;",
			"ovs:mq": "overflow-style:marquee;",
			"zoo": "zoom:1;",
			"cp": "clip:|;",
			"cp:a": "clip:auto;",
			"cp:r": "clip:rect(|);",
			"bxz": "box-sizing:|;",
			"bxz:cb": "box-sizing:content-box;",
			"bxz:bb": "box-sizing:border-box;",
			"bxsh": "box-shadow:|;",
			"bxsh:n": "box-shadow:none;",
			"bxsh:w": "-webkit-box-shadow:0 0 0 #000;",
			"bxsh:m": "-moz-box-shadow:0 0 0 0 #000;",
			"m": "margin:|;",
			"m:a": "margin:auto;",
			"m:0": "margin:0;",
			"m:2": "margin:0 0;",
			"m:3": "margin:0 0 0;",
			"m:4": "margin:0 0 0 0;",
			"mt": "margin-top:|;",
			"mt:a": "margin-top:auto;",
			"mr": "margin-right:|;",
			"mr:a": "margin-right:auto;",
			"mb": "margin-bottom:|;",
			"mb:a": "margin-bottom:auto;",
			"ml": "margin-left:|;",
			"ml:a": "margin-left:auto;",
			"p": "padding:|;",
			"p:0": "padding:0;",
			"p:2": "padding:0 0;",
			"p:3": "padding:0 0 0;",
			"p:4": "padding:0 0 0 0;",
			"pt": "padding-top:|;",
			"pr": "padding-right:|;",
			"pb": "padding-bottom:|;",
			"pl": "padding-left:|;",
			"w": "width:|;",
			"w:a": "width:auto;",
			"h": "height:|;",
			"h:a": "height:auto;",
			"maw": "max-width:|;",
			"maw:n": "max-width:none;",
			"mah": "max-height:|;",
			"mah:n": "max-height:none;",
			"miw": "min-width:|;",
			"mih": "min-height:|;",
			"o": "outline:|;",
			"o:n": "outline:none;",
			"oo": "outline-offset:|;",
			"ow": "outline-width:|;",
			"os": "outline-style:|;",
			"oc": "outline-color:#000;",
			"oc:i": "outline-color:invert;",
			"bd": "border:|;",
			"bd+": "border:1px solid #000;",
			"bd:n": "border:none;",
			"bdbk": "border-break:|;",
			"bdbk:c": "border-break:close;",
			"bdcl": "border-collapse:|;",
			"bdcl:c": "border-collapse:collapse;",
			"bdcl:s": "border-collapse:separate;",
			"bdc": "border-color:#000;",
			"bdi": "border-image:url(|);",
			"bdi:n": "border-image:none;",
			"bdi:w": "-webkit-border-image:url(|) 0 0 0 0 stretch stretch;",
			"bdi:m": "-moz-border-image:url(|) 0 0 0 0 stretch stretch;",
			"bdti": "border-top-image:url(|);",
			"bdti:n": "border-top-image:none;",
			"bdri": "border-right-image:url(|);",
			"bdri:n": "border-right-image:none;",
			"bdbi": "border-bottom-image:url(|);",
			"bdbi:n": "border-bottom-image:none;",
			"bdli": "border-left-image:url(|);",
			"bdli:n": "border-left-image:none;",
			"bdci": "border-corner-image:url(|);",
			"bdci:n": "border-corner-image:none;",
			"bdci:c": "border-corner-image:continue;",
			"bdtli": "border-top-left-image:url(|);",
			"bdtli:n": "border-top-left-image:none;",
			"bdtli:c": "border-top-left-image:continue;",
			"bdtri": "border-top-right-image:url(|);",
			"bdtri:n": "border-top-right-image:none;",
			"bdtri:c": "border-top-right-image:continue;",
			"bdbri": "border-bottom-right-image:url(|);",
			"bdbri:n": "border-bottom-right-image:none;",
			"bdbri:c": "border-bottom-right-image:continue;",
			"bdbli": "border-bottom-left-image:url(|);",
			"bdbli:n": "border-bottom-left-image:none;",
			"bdbli:c": "border-bottom-left-image:continue;",
			"bdf": "border-fit:|;",
			"bdf:c": "border-fit:clip;",
			"bdf:r": "border-fit:repeat;",
			"bdf:sc": "border-fit:scale;",
			"bdf:st": "border-fit:stretch;",
			"bdf:ow": "border-fit:overwrite;",
			"bdf:of": "border-fit:overflow;",
			"bdf:sp": "border-fit:space;",
			"bdl": "border-length:|;",
			"bdl:a": "border-length:auto;",
			"bdsp": "border-spacing:|;",
			"bds": "border-style:|;",
			"bds:n": "border-style:none;",
			"bds:h": "border-style:hidden;",
			"bds:dt": "border-style:dotted;",
			"bds:ds": "border-style:dashed;",
			"bds:s": "border-style:solid;",
			"bds:db": "border-style:double;",
			"bds:dtds": "border-style:dot-dash;",
			"bds:dtdtds": "border-style:dot-dot-dash;",
			"bds:w": "border-style:wave;",
			"bds:g": "border-style:groove;",
			"bds:r": "border-style:ridge;",
			"bds:i": "border-style:inset;",
			"bds:o": "border-style:outset;",
			"bdw": "border-width:|;",
			"bdt": "border-top:|;",
			"bdt+": "border-top:1px solid #000;",
			"bdt:n": "border-top:none;",
			"bdtw": "border-top-width:|;",
			"bdts": "border-top-style:|;",
			"bdts:n": "border-top-style:none;",
			"bdtc": "border-top-color:#000;",
			"bdr": "border-right:|;",
			"bdr+": "border-right:1px solid #000;",
			"bdr:n": "border-right:none;",
			"bdrw": "border-right-width:|;",
			"bdrs": "border-right-style:|;",
			"bdrs:n": "border-right-style:none;",
			"bdrc": "border-right-color:#000;",
			"bdb": "border-bottom:|;",
			"bdb+": "border-bottom:1px solid #000;",
			"bdb:n": "border-bottom:none;",
			"bdbw": "border-bottom-width:|;",
			"bdbs": "border-bottom-style:|;",
			"bdbs:n": "border-bottom-style:none;",
			"bdbc": "border-bottom-color:#000;",
			"bdl": "border-left:|;",
			"bdl+": "border-left:1px solid #000;",
			"bdl:n": "border-left:none;",
			"bdlw": "border-left-width:|;",
			"bdls": "border-left-style:|;",
			"bdls:n": "border-left-style:none;",
			"bdlc": "border-left-color:#000;",
			"bdrs": "border-radius:|;",
			"bdtrrs": "border-top-right-radius:|;",
			"bdtlrs": "border-top-left-radius:|;",
			"bdbrrs": "border-bottom-right-radius:|;",
			"bdblrs": "border-bottom-left-radius:|;",
			"bg": "background:|;",
			"bg+": "background:#FFF url(|) 0 0 no-repeat;",
			"bg:n": "background:none;",
			"bg:ie": "filter:progid:DXImageTransform.Microsoft.AlphaImageLoader(src='|x.png');",
			"bgc": "background-color:#FFF;",
			"bgi": "background-image:url(|);",
			"bgi:n": "background-image:none;",
			"bgr": "background-repeat:|;",
			"bgr:n": "background-repeat:no-repeat;",
			"bgr:x": "background-repeat:repeat-x;",
			"bgr:y": "background-repeat:repeat-y;",
			"bga": "background-attachment:|;",
			"bga:f": "background-attachment:fixed;",
			"bga:s": "background-attachment:scroll;",
			"bgp": "background-position:0 0;",
			"bgpx": "background-position-x:|;",
			"bgpy": "background-position-y:|;",
			"bgbk": "background-break:|;",
			"bgbk:bb": "background-break:bounding-box;",
			"bgbk:eb": "background-break:each-box;",
			"bgbk:c": "background-break:continuous;",
			"bgcp": "background-clip:|;",
			"bgcp:bb": "background-clip:border-box;",
			"bgcp:pb": "background-clip:padding-box;",
			"bgcp:cb": "background-clip:content-box;",
			"bgcp:nc": "background-clip:no-clip;",
			"bgo": "background-origin:|;",
			"bgo:pb": "background-origin:padding-box;",
			"bgo:bb": "background-origin:border-box;",
			"bgo:cb": "background-origin:content-box;",
			"bgz": "background-size:|;",
			"bgz:a": "background-size:auto;",
			"bgz:ct": "background-size:contain;",
			"bgz:cv": "background-size:cover;",
			"c": "color:#000;",
			"tbl": "table-layout:|;",
			"tbl:a": "table-layout:auto;",
			"tbl:f": "table-layout:fixed;",
			"cps": "caption-side:|;",
			"cps:t": "caption-side:top;",
			"cps:b": "caption-side:bottom;",
			"ec": "empty-cells:|;",
			"ec:s": "empty-cells:show;",
			"ec:h": "empty-cells:hide;",
			"lis": "list-style:|;",
			"lis:n": "list-style:none;",
			"lisp": "list-style-position:|;",
			"lisp:i": "list-style-position:inside;",
			"lisp:o": "list-style-position:outside;",
			"list": "list-style-type:|;",
			"list:n": "list-style-type:none;",
			"list:d": "list-style-type:disc;",
			"list:c": "list-style-type:circle;",
			"list:s": "list-style-type:square;",
			"list:dc": "list-style-type:decimal;",
			"list:dclz": "list-style-type:decimal-leading-zero;",
			"list:lr": "list-style-type:lower-roman;",
			"list:ur": "list-style-type:upper-roman;",
			"lisi": "list-style-image:|;",
			"lisi:n": "list-style-image:none;",
			"q": "quotes:|;",
			"q:n": "quotes:none;",
			"q:ru": "quotes:'\00AB' '\00BB' '\201E' '\201C';",
			"q:en": "quotes:'\201C' '\201D' '\2018' '\2019';",
			"ct": "content:|;",
			"ct:n": "content:normal;",
			"ct:oq": "content:open-quote;",
			"ct:noq": "content:no-open-quote;",
			"ct:cq": "content:close-quote;",
			"ct:ncq": "content:no-close-quote;",
			"ct:a": "content:attr(|);",
			"ct:c": "content:counter(|);",
			"ct:cs": "content:counters(|);",
			"coi": "counter-increment:|;",
			"cor": "counter-reset:|;",
			"va": "vertical-align:|;",
			"va:sup": "vertical-align:super;",
			"va:t": "vertical-align:top;",
			"va:tt": "vertical-align:text-top;",
			"va:m": "vertical-align:middle;",
			"va:bl": "vertical-align:baseline;",
			"va:b": "vertical-align:bottom;",
			"va:tb": "vertical-align:text-bottom;",
			"va:sub": "vertical-align:sub;",
			"ta": "text-align:|;",
			"ta:l": "text-align:left;",
			"ta:c": "text-align:center;",
			"ta:r": "text-align:right;",
			"tal": "text-align-last:|;",
			"tal:a": "text-align-last:auto;",
			"tal:l": "text-align-last:left;",
			"tal:c": "text-align-last:center;",
			"tal:r": "text-align-last:right;",
			"td": "text-decoration:|;",
			"td:n": "text-decoration:none;",
			"td:u": "text-decoration:underline;",
			"td:o": "text-decoration:overline;",
			"td:l": "text-decoration:line-through;",
			"te": "text-emphasis:|;",
			"te:n": "text-emphasis:none;",
			"te:ac": "text-emphasis:accent;",
			"te:dt": "text-emphasis:dot;",
			"te:c": "text-emphasis:circle;",
			"te:ds": "text-emphasis:disc;",
			"te:b": "text-emphasis:before;",
			"te:a": "text-emphasis:after;",
			"th": "text-height:|;",
			"th:a": "text-height:auto;",
			"th:f": "text-height:font-size;",
			"th:t": "text-height:text-size;",
			"th:m": "text-height:max-size;",
			"ti": "text-indent:|;",
			"ti:-": "text-indent:-9999px;",
			"tj": "text-justify:|;",
			"tj:a": "text-justify:auto;",
			"tj:iw": "text-justify:inter-word;",
			"tj:ii": "text-justify:inter-ideograph;",
			"tj:ic": "text-justify:inter-cluster;",
			"tj:d": "text-justify:distribute;",
			"tj:k": "text-justify:kashida;",
			"tj:t": "text-justify:tibetan;",
			"to": "text-outline:|;",
			"to+": "text-outline:0 0 #000;",
			"to:n": "text-outline:none;",
			"tr": "text-replace:|;",
			"tr:n": "text-replace:none;",
			"tt": "text-transform:|;",
			"tt:n": "text-transform:none;",
			"tt:c": "text-transform:capitalize;",
			"tt:u": "text-transform:uppercase;",
			"tt:l": "text-transform:lowercase;",
			"tw": "text-wrap:|;",
			"tw:n": "text-wrap:normal;",
			"tw:no": "text-wrap:none;",
			"tw:u": "text-wrap:unrestricted;",
			"tw:s": "text-wrap:suppress;",
			"tsh": "text-shadow:|;",
			"tsh+": "text-shadow:0 0 0 #000;",
			"tsh:n": "text-shadow:none;",
			"lh": "line-height:|;",
			"whs": "white-space:|;",
			"whs:n": "white-space:normal;",
			"whs:p": "white-space:pre;",
			"whs:nw": "white-space:nowrap;",
			"whs:pw": "white-space:pre-wrap;",
			"whs:pl": "white-space:pre-line;",
			"whsc": "white-space-collapse:|;",
			"whsc:n": "white-space-collapse:normal;",
			"whsc:k": "white-space-collapse:keep-all;",
			"whsc:l": "white-space-collapse:loose;",
			"whsc:bs": "white-space-collapse:break-strict;",
			"whsc:ba": "white-space-collapse:break-all;",
			"wob": "word-break:|;",
			"wob:n": "word-break:normal;",
			"wob:k": "word-break:keep-all;",
			"wob:l": "word-break:loose;",
			"wob:bs": "word-break:break-strict;",
			"wob:ba": "word-break:break-all;",
			"wos": "word-spacing:|;",
			"wow": "word-wrap:|;",
			"wow:nm": "word-wrap:normal;",
			"wow:n": "word-wrap:none;",
			"wow:u": "word-wrap:unrestricted;",
			"wow:s": "word-wrap:suppress;",
			"lts": "letter-spacing:|;",
			"f": "font:|;",
			"f+": "font:1em Arial,sans-serif;",
			"fw": "font-weight:|;",
			"fw:n": "font-weight:normal;",
			"fw:b": "font-weight:bold;",
			"fw:br": "font-weight:bolder;",
			"fw:lr": "font-weight:lighter;",
			"fs": "font-style:|;",
			"fs:n": "font-style:normal;",
			"fs:i": "font-style:italic;",
			"fs:o": "font-style:oblique;",
			"fv": "font-variant:|;",
			"fv:n": "font-variant:normal;",
			"fv:sc": "font-variant:small-caps;",
			"fz": "font-size:|;",
			"fza": "font-size-adjust:|;",
			"fza:n": "font-size-adjust:none;",
			"ff": "font-family:|;",
			"ff:s": "font-family:serif;",
			"ff:ss": "font-family:sans-serif;",
			"ff:c": "font-family:cursive;",
			"ff:f": "font-family:fantasy;",
			"ff:m": "font-family:monospace;",
			"fef": "font-effect:|;",
			"fef:n": "font-effect:none;",
			"fef:eg": "font-effect:engrave;",
			"fef:eb": "font-effect:emboss;",
			"fef:o": "font-effect:outline;",
			"fem": "font-emphasize:|;",
			"femp": "font-emphasize-position:|;",
			"femp:b": "font-emphasize-position:before;",
			"femp:a": "font-emphasize-position:after;",
			"fems": "font-emphasize-style:|;",
			"fems:n": "font-emphasize-style:none;",
			"fems:ac": "font-emphasize-style:accent;",
			"fems:dt": "font-emphasize-style:dot;",
			"fems:c": "font-emphasize-style:circle;",
			"fems:ds": "font-emphasize-style:disc;",
			"fsm": "font-smooth:|;",
			"fsm:a": "font-smooth:auto;",
			"fsm:n": "font-smooth:never;",
			"fsm:aw": "font-smooth:always;",
			"fst": "font-stretch:|;",
			"fst:n": "font-stretch:normal;",
			"fst:uc": "font-stretch:ultra-condensed;",
			"fst:ec": "font-stretch:extra-condensed;",
			"fst:c": "font-stretch:condensed;",
			"fst:sc": "font-stretch:semi-condensed;",
			"fst:se": "font-stretch:semi-expanded;",
			"fst:e": "font-stretch:expanded;",
			"fst:ee": "font-stretch:extra-expanded;",
			"fst:ue": "font-stretch:ultra-expanded;",
			"op": "opacity:|;",
			"op:ie": "filter:progid:DXImageTransform.Microsoft.Alpha(Opacity=100);",
			"op:ms": "-ms-filter:'progid:DXImageTransform.Microsoft.Alpha(Opacity=100)';",
			"rz": "resize:|;",
			"rz:n": "resize:none;",
			"rz:b": "resize:both;",
			"rz:h": "resize:horizontal;",
			"rz:v": "resize:vertical;",
			"cur": "cursor:|;",
			"cur:a": "cursor:auto;",
			"cur:d": "cursor:default;",
			"cur:c": "cursor:crosshair;",
			"cur:ha": "cursor:hand;",
			"cur:he": "cursor:help;",
			"cur:m": "cursor:move;",
			"cur:p": "cursor:pointer;",
			"cur:t": "cursor:text;",
			"pgbb": "page-break-before:|;",
			"pgbb:au": "page-break-before:auto;",
			"pgbb:al": "page-break-before:always;",
			"pgbb:l": "page-break-before:left;",
			"pgbb:r": "page-break-before:right;",
			"pgbi": "page-break-inside:|;",
			"pgbi:au": "page-break-inside:auto;",
			"pgbi:av": "page-break-inside:avoid;",
			"pgba": "page-break-after:|;",
			"pgba:au": "page-break-after:auto;",
			"pgba:al": "page-break-after:always;",
			"pgba:l": "page-break-after:left;",
			"pgba:r": "page-break-after:right;",
			"orp": "orphans:|;",
			"wid": "widows:|;"
		}
	},
	
	'html': {
		'extends': 'common',
		'filters': 'html',
		'snippets': {
			'cc:ie6': '<!--[if lte IE 6]>\n\t${child}|\n<![endif]-->',
			'cc:ie': '<!--[if IE]>\n\t${child}|\n<![endif]-->',
			'cc:noie': '<!--[if !IE]><!-->\n\t${child}|\n<!--<![endif]-->',
			'html:4t': '<!DOCTYPE HTML PUBLIC "-//W3C//DTD HTML 4.01 Transitional//EN" "http://www.w3.org/TR/html4/loose.dtd">\n' +
					'<html lang="${lang}">\n' +
					'<head>\n' +
					'	<meta http-equiv="Content-Type" content="text/html;charset=${charset}">\n' +
					'	<title></title>\n' +
					'</head>\n' +
					'<body>\n\t${child}|\n</body>\n' +
					'</html>',
			
			'html:4s': '<!DOCTYPE HTML PUBLIC "-//W3C//DTD HTML 4.01//EN" "http://www.w3.org/TR/html4/strict.dtd">\n' +
					'<html lang="${lang}">\n' +
					'<head>\n' +
					'	<meta http-equiv="Content-Type" content="text/html;charset=${charset}">\n' +
					'	<title></title>\n' +
					'</head>\n' +
					'<body>\n\t${child}|\n</body>\n' +
					'</html>',
			
			'html:xt': '<!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.0 Transitional//EN" "http://www.w3.org/TR/xhtml1/DTD/xhtml1-transitional.dtd">\n' +
					'<html xmlns="http://www.w3.org/1999/xhtml" xml:lang="${lang}">\n' +
					'<head>\n' +
					'	<meta http-equiv="Content-Type" content="text/html;charset=${charset}" />\n' +
					'	<title></title>\n' +
					'</head>\n' +
					'<body>\n\t${child}|\n</body>\n' +
					'</html>',
			
			'html:xs': '<!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.0 Strict//EN" "http://www.w3.org/TR/xhtml1/DTD/xhtml1-strict.dtd">\n' +
					'<html xmlns="http://www.w3.org/1999/xhtml" xml:lang="${lang}">\n' +
					'<head>\n' +
					'	<meta http-equiv="Content-Type" content="text/html;charset=${charset}" />\n' +
					'	<title></title>\n' +
					'</head>\n' +
					'<body>\n\t${child}|\n</body>\n' +
					'</html>',
			
			'html:xxs': '<!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.1//EN" "http://www.w3.org/TR/xhtml11/DTD/xhtml11.dtd">\n' +
					'<html xmlns="http://www.w3.org/1999/xhtml" xml:lang="${lang}">\n' +
					'<head>\n' +
					'	<meta http-equiv="Content-Type" content="text/html;charset=${charset}" />\n' +
					'	<title></title>\n' +
					'</head>\n' +
					'<body>\n\t${child}|\n</body>\n' +
					'</html>',
			
			'html:5': '<!DOCTYPE HTML>\n' +
					'<html lang="${locale}">\n' +
					'<head>\n' +
					'	<meta charset="${charset}">\n' +
					'	<title></title>\n' +
					'</head>\n' +
					'<body>\n\t${child}|\n</body>\n' +
					'</html>'
		},
		
		'abbreviations': {
			'a': '<a href=""></a>',
			'a:link': '<a href="http://|"></a>',
			'a:mail': '<a href="mailto:|"></a>',
			'abbr': '<abbr title=""></abbr>',
			'acronym': '<acronym title=""></acronym>',
			'base': '<base href="" />',
			'bdo': '<bdo dir=""></bdo>',
			'bdo:r': '<bdo dir="rtl"></bdo>',
			'bdo:l': '<bdo dir="ltr"></bdo>',
			'link:css': '<link rel="stylesheet" type="text/css" href="${1:style}.css" media="all" />',
			'link:print': '<link rel="stylesheet" type="text/css" href="|print.css" media="print" />',
			'link:favicon': '<link rel="shortcut icon" type="image/x-icon" href="|favicon.ico" />',
			'link:touch': '<link rel="apple-touch-icon" href="|favicon.png" />',
			'link:rss': '<link rel="alternate" type="application/rss+xml" title="RSS" href="|rss.xml" />',
			'link:atom': '<link rel="alternate" type="application/atom+xml" title="Atom" href="atom.xml" />',
			'meta:utf': '<meta http-equiv="Content-Type" content="text/html;charset=UTF-8" />',
			'meta:win': '<meta http-equiv="Content-Type" content="text/html;charset=Win-1251" />',
			'meta:compat': '<meta http-equiv="X-UA-Compatible" content="IE=7" />',
			'style': '<style type="text/css"></style>',
			'script': '<script type="text/javascript"></script>',
			'script:src': '<script type="text/javascript" src=""></script>',
			'img': '<img src="" alt="" />',
			'iframe': '<iframe src="" frameborder="0"></iframe>',
			'embed': '<embed src="" type="" />',
			'object': '<object data="" type=""></object>',
			'param': '<param name="" value="" />',
			'map': '<map name=""></map>',
			'area': '<area shape="" coords="" href="" alt="" />',
			'area:d': '<area shape="default" href="" alt="" />',
			'area:c': '<area shape="circle" coords="" href="" alt="" />',
			'area:r': '<area shape="rect" coords="" href="" alt="" />',
			'area:p': '<area shape="poly" coords="" href="" alt="" />',
			'link': '<link rel="stylesheet" href="" />',
			'form': '<form action=""></form>',
			'form:get': '<form action="" method="get"></form>',
			'form:post': '<form action="" method="post"></form>',
			'label': '<label for=""></label>',
			'input': '<input type="" />',
			'input:hidden': '<input type="hidden" name="" />',
			'input:h': '<input type="hidden" name="" />',
			'input:text': '<input type="text" name="" id="" />',
			'input:t': '<input type="text" name="" id="" />',
			'input:search': '<input type="search" name="" id="" />',
			'input:email': '<input type="email" name="" id="" />',
			'input:url': '<input type="url" name="" id="" />',
			'input:password': '<input type="password" name="" id="" />',
			'input:p': '<input type="password" name="" id="" />',
			'input:datetime': '<input type="datetime" name="" id="" />',
			'input:date': '<input type="date" name="" id="" />',
			'input:datetime-local': '<input type="datetime-local" name="" id="" />',
			'input:month': '<input type="month" name="" id="" />',
			'input:week': '<input type="week" name="" id="" />',
			'input:time': '<input type="time" name="" id="" />',
			'input:number': '<input type="number" name="" id="" />',
			'input:color': '<input type="color" name="" id="" />',
			'input:checkbox': '<input type="checkbox" name="" id="" />',
			'input:c': '<input type="checkbox" name="" id="" />',
			'input:radio': '<input type="radio" name="" id="" />',
			'input:r': '<input type="radio" name="" id="" />',
			'input:range': '<input type="range" name="" id="" />',
			'input:file': '<input type="file" name="" id="" />',
			'input:f': '<input type="file" name="" id="" />',
			'input:submit': '<input type="submit" value="" />',
			'input:s': '<input type="submit" value="" />',
			'input:image': '<input type="image" src="" alt="" />',
			'input:i': '<input type="image" src="" alt="" />',
			'input:reset': '<input type="reset" value="" />',
			'input:button': '<input type="button" value="" />',
			'input:b': '<input type="button" value="" />',
			'select': '<select name="" id=""></select>',
			'option': '<option value=""></option>',
			'textarea': '<textarea name="" id="" cols="30" rows="10"></textarea>',
			'menu:context': '<menu type="context"></menu>',
			'menu:c': '<menu type="context"></menu>',
			'menu:toolbar': '<menu type="toolbar"></menu>',
			'menu:t': '<menu type="toolbar"></menu>',
			'video': '<video src=""></video>',
			'audio': '<audio src=""></audio>',
			'html:xml': '<html xmlns="http://www.w3.org/1999/xhtml"></html>',
			'bq': '<blockquote></blockquote>',
			'acr': '<acronym></acronym>',
			'fig': '<figure></figure>',
			'ifr': '<iframe></iframe>',
			'emb': '<embed></embed>',
			'obj': '<object></object>',
			'src': '<source></source>',
			'cap': '<caption></caption>',
			'colg': '<colgroup></colgroup>',
			'fst': '<fieldset></fieldset>',
			'btn': '<button></button>',
			'optg': '<optgroup></optgroup>',
			'opt': '<option></option>',
			'tarea': '<textarea></textarea>',
			'leg': '<legend></legend>',
			'sect': '<section></section>',
			'art': '<article></article>',
			'hdr': '<header></header>',
			'ftr': '<footer></footer>',
			'adr': '<address></address>',
			'dlg': '<dialog></dialog>',
			'str': '<strong></strong>',
			'prog': '<progress></progress>',
			'fset': '<fieldset></fieldset>',
			'datag': '<datagrid></datagrid>',
			'datal': '<datalist></datalist>',
			'kg': '<keygen></keygen>',
			'out': '<output></output>',
			'det': '<details></details>',
			'cmd': '<command></command>',
			
#			expandos
			'ol+': 'ol>li',
			'ul+': 'ul>li',
			'dl+': 'dl>dt+dd',
			'map+': 'map>area',
			'table+': 'table>tr>td',
			'colgroup+': 'colgroup>col',
			'colg+': 'colgroup>col',
			'tr+': 'tr>td',
			'select+': 'select>option',
			'optgroup+': 'optgroup>option',
			'optg+': 'optgroup>option'

		},
		
		'element_types': {
			'empty': 'area,base,basefont,br,col,frame,hr,img,input,isindex,link,meta,param,embed,keygen,command',
			'block_level': 'address,applet,blockquote,button,center,dd,del,dir,div,dl,dt,fieldset,form,frameset,hr,iframe,ins,isindex,li,link,map,menu,noframes,noscript,object,ol,p,pre,script,table,tbody,td,tfoot,th,thead,tr,ul,h1,h2,h3,h4,h5,h6',
			'inline_level': 'a,abbr,acronym,applet,b,basefont,bdo,big,br,button,cite,code,del,dfn,em,font,i,iframe,img,input,ins,kbd,label,map,object,q,s,samp,script,select,small,span,strike,strong,sub,sup,textarea,tt,u,var'
		}
	},
	
	'xsl': {
		'extends': 'common,html',
		'filters': 'html, xsl',
		'abbreviations': {
			'tm': '<xsl:template match="" mode=""></xsl:template>',
			'tmatch': 'tm',
			'tn': '<xsl:template name=""></xsl:template>',
			'tname': 'tn',
			'xsl:when': '<xsl:when test=""></xsl:when>',
			'wh': 'xsl:when',
			'var': '<xsl:variable name="">|</xsl:variable>',
			'vare': '<xsl:variable name="" select=""/>',
			'if': '<xsl:if test=""></xsl:if>',
			'call': '<xsl:call-template name=""/>',
			'attr': '<xsl:attribute name=""></xsl:attribute>',
			'wp': '<xsl:with-param name="" select=""/>',
			'par': '<xsl:param name="" select=""/>',
			'val': '<xsl:value-of select=""/>',
			'co': '<xsl:copy-of select=""/>',
			'each': '<xsl:for-each select=""></xsl:for-each>',
			'ap': '<xsl:apply-templates select="" mode=""/>',
			
#			expandos
			'choose+': 'xsl:choose>xsl:when+xsl:otherwise'
		}
	},
	
	'xml': {
		'extends': 'common'
	},
	
	'haml': {
		'filters': 'haml',
		'extends': 'html'
	}
}
########NEW FILE########
__FILENAME__ = zen_editor
'''
High-level editor interface that communicates with underlying editor (like
Espresso, Coda, etc.) or browser.
Basically, you should call <code>set_context(obj)</code> method to
set up undelying editor context before using any other method.

This interface is used by <i>zen_actions.py</i> for performing different
actions like <b>Expand abbreviation</b>

@example
import zen_editor
zen_editor.set_context(obj);
//now you are ready to use editor object
zen_editor.get_selection_range();

@author Sergey Chikuyonok (serge.che@gmail.com)
@link http://chikuyonok.ru
'''
import tea_actions as tea
import zen_settings_loader as settings_loader
from zencoding import zen_core as zen
import re

class ZenEditor():
	def __init__(self, context):
		self._context = None
		self.zen_settings = settings_loader.load_settings()
		zen.update_settings(self.zen_settings)

		if context:
			self.set_context(context)

	def set_context(self, context):
		"""
		Setup underlying editor context. You should call this method
		<code>before</code> using any Zen Coding action.
		@param context: context object
		"""
		self._context = context
		zen.newline = self.safe_str(tea.get_line_ending(context))
		self.zen_settings['variables']['indentation'] = self.safe_str(tea.get_indentation_string(context))

	def get_selection_range(self):
		"""
		Returns character indexes of selected text
		@return: list of start and end indexes
		@example
		start, end = zen_editor.get_selection_range();
		print('%s, %s' % (start, end))
		"""
		rng = tea.get_first_range(self._context)
		return rng.location, rng.location + rng.length


	def create_selection(self, start, end=None):
		"""
		Creates selection from <code>start</code> to <code>end</code> character
		indexes. If <code>end</code> is ommited, this method should place caret
		and <code>start</code> index
		@type start: int
		@type end: int
		@example
		zen_editor.create_selection(10, 40)
		# move caret to 15th character
		zen_editor.create_selection(15)
		"""
		if end is None: end = start
		new_range = tea.new_range(start, end - start)
		tea.set_selected_range(self._context, new_range)

	def get_current_line_range(self):
		"""
		Returns current line's start and end indexes
		@return: list of start and end indexes
		@example
		start, end = zen_editor.get_current_line_range();
		print('%s, %s' % (start, end))
		"""
		rng = tea.get_ranges(self._context)[0]
		text, rng = tea.get_line(self._context, rng)
		return rng.location, rng.location + rng.length

	def get_caret_pos(self):
		""" Returns current caret position """
		range = tea.get_ranges(self._context)[0]
		return range.location

	def set_caret_pos(self, pos):
		"""
		Set new caret position
		@type pos: int
		"""
		self.create_selection(pos)

	def get_current_line(self):
		"""
		Returns content of current line
		@return: str
		"""
		rng = tea.get_ranges(self._context)[0]
		text, rng = tea.get_line(self._context, rng)
		return text

	def replace_content(self, value, start=None, end=None, undo_name = 'Replace content'):
		"""
		Replace editor's content or it's part (from <code>start</code> to
		<code>end</code> index). If <code>value</code> contains
		<code>caret_placeholder</code>, the editor will put caret into
		this position. If you skip <code>start</code> and <code>end</code>
		arguments, the whole target's content will be replaced with
		<code>value</code>.

		If you pass <code>start</code> argument only,
		the <code>value</code> will be placed at <code>start</code> string
		index of current content.

		If you pass <code>start</code> and <code>end</code> arguments,
		the corresponding substring of current target's content will be
		replaced with <code>value</code>
		@param value: Content you want to paste
		@type value: str
		@param start: Start index of editor's content
		@type start: int
		@param end: End index of editor's content
		@type end: int
		"""
		if start is None: start = 0
		if end is None: end = len(self.get_content())
		rng = tea.new_range(start, end - start)
		value = self.add_placeholders(value)
		tea.insert_snippet_over_range(self._context, value, rng, undo_name)


	def get_content(self):
		"""
		Returns editor's content
		@return: str
		"""
		return self._context.string()

	def get_syntax(self):
		"""
		Returns current editor's syntax mode
		@return: str
		"""
		zones = {
			'css, css *': 'css',
			'xsl, xsl *': 'xsl',
			'xml, xml *': 'xml',
			'haml, haml *': 'haml'
		}
		rng = tea.get_first_range(self._context)
		return tea.select_from_zones(self._context, rng, 'html', **zones)

	def get_profile_name(self):
		"""
		Returns current output profile name (@see zen_coding#setup_profile)
		@return {String}
		"""
		forced_profile = zen.get_variable('profile')
		if forced_profile:
			return forced_profile
		
		close_string = tea.get_tag_closestring(self._context)
		if close_string == '/':
			return 'xml'
		elif close_string != ' /':
			return 'html'
		else:
			return 'xhtml'

	def safe_str(self, text):
		"""
		Creates safe string representation to deal with Python's encoding issues
		"""
		return text.encode('utf-8')
	
	def add_placeholders(self, text):
		_ix = [zen.max_tabstop]
		
		def get_ix(m):
			_ix[0] += 1
			return '$%s' % _ix[0]
		
		text = re.sub(r'\$(?![\d\{])', '\\$', text)
		return re.sub(zen.get_caret_placeholder(), get_ix, text)

########NEW FILE########
__FILENAME__ = zen_settings_loader
'''
Zen settings loader that can read user-defined snippets from Espresso
@author: Sergey Chikuyonok (serge.che@gmail.com)
'''
import os
import re
import pickle

from Foundation import NSUserDefaults, NSLog

import tea_utils

from zencoding import stparser

plist_path = os.path.expanduser('~/Library/Preferences/com.macrabbit.Espresso.plist')
cache_folder = os.path.expanduser(
        '~/Library/Application Support/Espresso/Support/Caches'
)
cache_file = os.path.join(cache_folder, 'zen_user_snippets.cache')

re_full_tag = re.compile(r'^<([\w\-]+(?:\:\w+)?)((?:\s+[\w\-]+(?:\s*=\s*(?:(?:"[^"]*")|(?:\'[^\']*\')|[^>\s]+))?)*)\s*(\/?)>(?:</\1>)?')

def _convert_user_snippets_to_zen_settings():
    defaults = NSUserDefaults.standardUserDefaults()
    snippets = defaults.objectForKey_('UserSnippets1.0')
    
    if snippets is not None:
        snips = {}
        abbrs = {}
        for item in snippets:
            if 'snippetString' in item and 'title' in item:
                abbr_name = 'triggerString' in item and item['triggerString'] or item['title']
                if re_full_tag.match(item['snippetString']):
                    abbrs[abbr_name] = item['snippetString']
                else:
                    snips[abbr_name] = item['snippetString']
        
        return {'common': {
            'snippets': snips,
            'abbreviations': abbrs
        }}
    
    return None

def load_settings():
    """
    Load zen coding's settings, combined with user-defined snippets
    """
    defaults = NSUserDefaults.standardUserDefaults()
    
    # Construct our initial settings dictionary
    objc_dict = defaults.objectForKey_('TEAZenSettings')
    if objc_dict is not None:
        user_settings = tea_utils.nsdict_to_pydict(objc_dict)
    else:
        user_settings = dict()
    
    # Add the CSS filter if we're adding a space after properties
    if defaults.boolForKey_('TEAZenAddSpaceCSSProperties'):
        user_settings['css'] = {'filters': 'html, fc'}
    
    # Check to see if we're converting user snippets to zen abbreviations
    convert_to_zen = defaults.boolForKey_('TEAConvertUserSnippetsToZen')
    if convert_to_zen:
        orig_date = os.path.getmtime(plist_path)
        
        need_reload = True
        
        # Does our cache path exist and is writable?
        cache_dir_exists = os.path.isdir(cache_folder)
        if not cache_dir_exists:
            # Attempt to create the cache folder
            try:
                os.makedirs(cache_folder, 0755)
                cache_dir_exists = True
            except os.error:
                NSLog('TEA Error: Cannot create zen coding cache path for user snippets')
        
        # In worst case scenario, we can't read or write to the cache file
        # so we'll need to read from preferences every time
        # This variable tracks the user snippets in case of that eventuality
        _data = None
        
        # check if cached file exists and up-to-date
        if cache_dir_exists and (not os.path.exists(cache_file) or \
           os.path.getmtime(cache_file) < orig_date):
            # need to reparse and cache data
            _data = _convert_user_snippets_to_zen_settings()
            try:
                fp = open(cache_file, 'wb')
                pickle.dump(_data, fp)
                fp.close()
            except IOError:
                NSLog('TEA Error: Zen user snippets cache file is not writable')
            need_reload = False
        
        if need_reload:
            try:
                fp = open(cache_file, 'rb')
                _data = pickle.load(fp)
                fp.close()
            except IOError:
                NSLog('TEA Error: Zen user snippets cache file is not readable')
        
        if _data is not None:
            # Add the settings to the user_settings dict
            user_settings.update(_data)
    
    # The settings dictionary is setup, return the full zen settings
    return stparser.get_settings(user_settings)
########NEW FILE########
__FILENAME__ = balance
'''
Attempts to locate the balanced delimiters around the cursor and select
their contents.

If direction == 'in', balance will attempt to move inward (select first
balanced delimiters contained within the current delimiter) rather than
outward.

mode controls what type of balancing is used:
- auto (default): tries to detect if we're in HTML before using zen
- zen: always uses zen coding, even if we aren't in HTML or XML
- itemizer: always uses itemizer balancing, even in HTML
'''

from Foundation import NSValue

import tea_actions as tea

from zencoding import zen_core as zen_coding
from zen_editor import ZenEditor

def act(context, direction='out', mode='auto'):
    zen_target = 'html, html *, xml, xml *'
    if (mode.lower() == 'auto' and tea.cursor_in_zone(context, zen_target)) or \
       mode.lower() == 'zen':
        # HTML or XML, so use Zen-coding's excellent balancing commands
        
        editor = ZenEditor(context)
        action_name = 'match_pair_inward' if direction == 'in' else 'match_pair_outward'
        return zen_coding.run_action(action_name, editor)
    else:
        # No HTML or XML, so we'll rely on itemizers
        ranges = tea.get_ranges(context)
        targets = []
        for range in ranges:
            if direction.lower() == 'in':
                item = tea.get_item_for_range(context, range)
                if item is None:
                    # No item, so jump to next iteration
                    continue
                new_range = item.range()
                if new_range.location == range.location and \
                   new_range.length == range.length:
                    items = item.childItems()
                    if len(items) > 0:
                        new_range = items[0].range()
                targets.append(new_range)
            else:
                item = tea.get_item_parent_for_range(context, range)
                if item is None:
                    continue
                targets.append(item.range())
        
        # Set the selections, and return
        if len(targets) > 0:
            context.setSelectedRanges_([NSValue.valueWithRange_(range) for range in targets])
            return True
        else:
            return False

########NEW FILE########
__FILENAME__ = encode_unicode
'''
Converts unicode characters in selection (or character preceding the cursor)
into various types of ASCII strings
'''

import tea_actions as tea

def act(context, type='named', wrap='$HEX', undo_name=None):
    '''
    Required action method
    
    Type can be:
    named: named HTML entities, with high value numeric entities if no name
    numeric: numeric HTML entities
    hex: hexadecimal encoding; use the 'wrap' option for specific output
    
    Wrap will be used if type is 'hex' and will replace $HEX with the actual
    hex value.  For example '\u$HEX' will be result in something like '\u0022'
    '''
    ranges = tea.get_ranges(context)
    if len(ranges) == 1 and ranges[0].length == 0:
        # We've got one empty range; make sure it's not at the
        # beginning of the document
        if ranges[0].location > 0:
            # Set the new target range to the character before the cursor
            ranges[0] = tea.new_range(ranges[0].location - 1, 1)
        else:
            return False
    # Since we're here we've got something to work with
    insertions = tea.new_recipe()
    for range in ranges:
        text = tea.get_selection(context, range)
        if type == 'named':
            # Convert any characters we can into named HTML entities
            text = tea.named_entities(text)
        elif type == 'numeric':
            # Convert any characters we can into numeric HTML entities
            text = tea.numeric_entities(text, type)
        elif type == 'hex':
            # Convert characters to hex via numeric entities
            text = tea.numeric_entities(text)
            text = tea.entities_to_hex(text, wrap)
        insertions.addReplacementString_forRange_(text, range)
    if undo_name is not None:
        insertions.setUndoActionName_(undo_name)
    return context.applyTextRecipe_(insertions)

########NEW FILE########
__FILENAME__ = goto
'''
Attempts to go to (select) a location in the document
'''

import re

import tea_actions as tea

def act(context, target=None, source=None, trim=False, discard_indent=False,
        search_string=None, regex=False):
    '''
    Required action method
    
    target dictates what we're looking for:
    - text
    - if unspecified, simply selects the source
    
    source dictates how to gather the string to search for:
    - word (word under the caret)
    - line (line under the caret)
    - if unspecified, defaults to selection
    
    Setting trim=True will cause the source to be trimmed
    
    Setting discard_indent=True will cause leading whitespace
    to be trimmed (unnecessary unless trim=True)
    
    search_string will set the string to search for if target is text or zone
    - $EDITOR_SELECTION will be replaced with the source text
    
    Setting regex=True will cause search_string to be evaluated as regex
    '''
    range = tea.get_ranges(context)[0]
    if source == 'word':
        text, range = tea.get_word(context, range)
    elif source == 'line':
        text, range = tea.get_line(context, range)
    elif range.length > 0:
        text = tea.get_selection(context, range)
    
    # Make sure that we've got some text, even if it's an empty string
    if text is None:
        text = ''
    
    # Trim the source
    if trim:
        if discard_indent:
            trimmed = tea.trim(context, text, False, preserve_linebreaks=False)
        else:
            trimmed = tea.trim(context, text, False, 'end',
                               preserve_linebreaks=False)
        
        start = text.find(trimmed)
        if start != -1:
            start = range.location + start
        length = len(trimmed)
        if source == 'line' and trimmed[-1:] in ['\r\n', '\r', '\n']:
            # We don't want the linebreak if we're trimming
            length = length - 1
        range = tea.new_range(start, length)
        text = trimmed
    
    if target is not None and text:
        if search_string is not None:
            # DEPRECATED: Please use $EDITOR_SELECTION instead
            search = search_string.replace('$SELECTED_TEXT', text)
            search = search_string.replace('$EDITOR_SELECTION', text)
        else:
            search = text
        # Find the start and end points of the substring
        start = end = None
        if regex:
            match = re.search(r'(' + search + r')', context.string())
            if match:
                # Get the start and end points
                start, end = match.span(1)
        else:
            start = context.string().find(search)
            if start != -1:
                end = start + len(search)
            else:
                start = None
        # Construct the new target range
        if start is not None and end is not None:
            range = tea.new_range(start, end - start)
    
    # Set the new range
    tea.set_selected_range(context, range)
    return True

########NEW FILE########
__FILENAME__ = insert_snippet
'''Inserts a snippet at the user's cursor; useful for tab completions'''

import tea_actions as tea

def act(context, default=None, undo_name=None, **syntaxes):
    '''
    Required action method
    
    Inserts an arbitrary text snippet after the cursor with provisions for
    syntax-specific alternatives
    
    Accepts $EDITOR_SELECTION placeholder
    
    This method requires at least the snippet default to be defined in the XML
    '''
    if default is None:
        return False
    # Get the cursor position
    text, range = tea.get_single_selection(context)
    # Check for root-zone specific override
    snippet = tea.select_from_zones(context, range, default, **syntaxes)
    # Construct the snippet
    snippet = tea.construct_snippet(text, snippet)
    # Insert that snippet!
    return tea.insert_snippet(context, snippet)

########NEW FILE########
__FILENAME__ = insert_text
'''Inserts arbitrary text over all selections'''

import tea_actions as tea

def act(context, default=None, prefix_selection=False,
        suffix_selection=False, undo_name=None, **syntaxes):
    '''
    Required action method
    
    Inserts arbitrary text over all selections; specific text can be
    syntax-specific (same procedure as Wrap Selection In Link)
    
    If you set prefix_selection to true, the inserted text will precede
    any selected text; if suffix_selection is true it will follow any
    selected text; if both are true it will wrap the text
    '''
    # Grab the ranges
    ranges = tea.get_ranges(context)
    # Set up our text recipe
    insertions = tea.new_recipe()
    for range in ranges:
        if prefix_selection or suffix_selection:
            # Get the selected text
            text = tea.get_selection(context, range)
            if prefix_selection:
                text = '$INSERT' + text
            if suffix_selection:
                text += '$INSERT'
            # If empty selection, only insert one
            if text == '$INSERT$INSERT':
                text = '$INSERT'
        else:
            text = '$INSERT'
        # Check for zone-specific insertion
        insert = tea.select_from_zones(context, range, default, **syntaxes)
        text = text.replace('$INSERT', insert)
        text = text.replace('$TOUCH', '')
        # Insert the text, or replace the selected text
        if range.length is 0:
            insertions.addInsertedString_forIndex_(text, range.location)
        else:
            insertions.addReplacementString_forRange_(text, range)
    # Set undo name and run the recipe
    if undo_name != None:
        insertions.setUndoActionName_(undo_name)
    reset_cursor = False
    if len(ranges) is 1 and ranges[0].length is 0:
        # Thanks to addInsertedString's wonkiness, we have to reset the cursor
        reset_cursor = True
    # Espresso beeps if I return True or False; hence this weirdness
    return_val = context.applyTextRecipe_(insertions)
    if reset_cursor:
        new_range = tea.new_range(ranges[0].location + len(text), 0)
        tea.set_selected_range(context, new_range)
    return return_val

########NEW FILE########
__FILENAME__ = insert_url_snippet
'''Wraps selected text in a link (what kind of link based on context)'''

import subprocess

import tea_actions as tea
from persistent_re import *

def format_hyperlink(text, fallback=''):
    gre = persistent_re()
    if gre.match(r'(mailto:)?(.+?@.+\..+)$', text):
        # Email; ensure it has a mailto prefix
        return 'mailto:' + gre.last.group(2)
    elif gre.search(r'http://(?:www\.)?(amazon\.(?:com|co\.uk|co\.jp|ca|fr|de))'\
                    r'/.+?/([A-Z0-9]{10})/[-a-zA-Z0-9_./%?=&]+', text):
        # Amazon URL; rewrite it with short version
        return 'http://' + gre.last.group(1) + '/dp/' + gre.last.group(2)
    elif gre.match(r'[a-zA-Z][a-zA-Z0-9.+-]+?://.*$', text):
        # Unknown prefix
        return tea.encode_ampersands(text)
    elif gre.match(r'.*\.(com|uk|net|org|info)(/.*)?$', text):
        # Recognizable URL without http:// prefix
        return 'http://' + tea.encode_ampersands(text)
    elif gre.match(r'\S+$', text):
        # No space characters, so could be a URL; toss 'er in there
        return tea.encode_ampersands(text)
    else:
        # Nothing that remotely looks URL-ish; give them the fallback
        return fallback

def act(context, default=None, fallback_url='', undo_name=None, **syntaxes):
    '''
    Required action method
    
    A flexible link generator which uses the clipboard text (if there's
    a recognizable link there) and formats the snippet based on the
    active syntax of the context
    '''
    if default is None:
        return False
    # Get the text and range
    text, range = tea.get_single_selection(context, True)
    if text == None:
        return False
    
    # Get the clipboard contents, parse for a URL
    process = subprocess.Popen(['pbpaste'], stdout=subprocess.PIPE)
    clipboard, error = process.communicate(None)
    # Construct the default link
    url = format_hyperlink(clipboard, fallback_url)
    # Get the snippet based on the root zone
    snippet = tea.select_from_zones(context, range, default, **syntaxes)
    snippet = tea.construct_snippet(text, snippet)
    snippet = snippet.replace('$URL', tea.sanitize_for_snippet(url))
    return tea.insert_snippet(context, snippet)

########NEW FILE########
__FILENAME__ = selected_lines_to_snippets
'''Wraps currently selected lines in a text snippet'''

import re

import tea_actions as tea

def act(context, first_snippet='', following_snippet='',
        final_append='', undo_name=None):
    '''
    Required action method
    
    This only allows a single selection (enforced through the utility
    functions) then parses over the lines and inserts a snippet
    
    Theoretically we could allow discontiguous selections; have to consider
    it if recipes get snippet capabilities
    '''
    text, range = tea.get_single_selection(context, True)
    if text == None:
        return False
    # Split the text into lines, maintaining the linebreaks
    lines = text.splitlines(True)
    # Compile the regex for quicker action on lots of lines
    parser = re.compile(r'(\s*)(.*?)(\s*(\r|\r\n|\n)|$)')
    first = first_snippet
    following = following_snippet
    # Loop over lines and construct the snippet
    snippet = ''
    # This is the number of snippets processed, not lines
    count = 1
    for line in lines:
        content = parser.search(line)
        # Only wrap the line if there's some content
        if content.group(2) != '':
            if count == 1:
                segment = tea.construct_snippet(content.group(2), first, True)
            else:
                segment = tea.construct_snippet(content.group(2), following, True)
            snippet += content.group(1) + segment + content.group(3)
            count += 1
        else:
            snippet += line
    snippet += final_append
    return tea.insert_snippet_over_range(context, snippet, range, undo_name, False)

########NEW FILE########
__FILENAME__ = selections_to_snippets
'''Wraps the currently selected text in a snippet'''

import tea_actions as tea

def act(context, first_snippet='', following_snippet='',
        final_append='', undo_name=None):
    '''
    Required action method
    
    Wraps the selected text in a snippet
    
    Support for discontiguous selections will be implemented when recipes
    can support snippets; until then only first_snippet will be used
    '''
    # TODO: change to a loop once snippets in recipes are supported
    # This function will handle the logic of when to use open vs. multi
    text, range = tea.get_single_selection(context)
    if text == None:
        text = ''
    # Only indent the snippet if there aren't multiple lines in the selected text
    if len(text.splitlines()) > 1:
        indent = False
    else:
        indent = True
    snippet = tea.construct_snippet(text, first_snippet + final_append)
    return tea.insert_snippet(context, snippet, indent)

########NEW FILE########
__FILENAME__ = selections_to_text
'''
Formats the selected text by wrapping it in the passed segment

Will use an automatically formatted snippet for a single selection,
or a simple text replacement for multiple selections
'''

import tea_actions as tea

def act(context, default=None, undo_name=None, **syntaxes):
    '''
    Required action method
    
    default parameter is not a snippet, but should contain the
    $EDITOR_SELECTION placeholder
    '''
    # Get the selected ranges
    ranges = tea.get_ranges(context)
    if len(ranges) is 1:
        # Since we've only got one selection we can use a snippet
        range = ranges[0]
        insertion = tea.select_from_zones(context, range, default, **syntaxes)
        # Make sure the range is actually a selection
        if range.length > 0:
            text = tea.get_selection(context, range)
            snippet = '${1:' + insertion.replace('$EDITOR_SELECTION',
                                                 '${2:$EDITOR_SELECTION}') + '}$0'
        else:
            # Not a selection, just wrap the cursor
            text = ''
            snippet = insertion.replace('$EDITOR_SELECTION', '$1') + '$0'
        snippet = tea.construct_snippet(text, snippet)
        return tea.insert_snippet(context, snippet)
    # Since we're here, it must not have been a single selection
    insertions = tea.new_recipe()
    for range in ranges:
        insertion = tea.select_from_zones(context, range, default, **syntaxes)
        text = tea.get_selection(context, range)
        # DEPRECATED: $SELECTED_TEXT will go away in future; don't use it
        insertion = insertion.replace('$SELECTED_TEXT', text)
        insertion = insertion.replace('$EDITOR_SELECTION', text)
        insertions.addReplacementString_forRange_(insertion, range)
    if undo_name is not None:
        insertions.setUndoActionName_(undo_name)
    return context.applyTextRecipe_(insertions)

########NEW FILE########
__FILENAME__ = sort_lines
'''Sorts selected lines ascending or descending'''

import random

import tea_actions as tea

def act(context, direction=None, remove_duplicates=False, undo_name=None):
    '''
    Required action method
    
    This sorts the selected lines (or document, if no selection)
    either ascending, descending, or randomly.
    '''
    # Check if there is a selection, otherwise take all lines
    ranges = tea.get_ranges(context)
    if len(ranges) == 1 and ranges[0].length == 0:
        ranges = [tea.new_range(0, context.string().length())]
    
    # Setup the text recipe
    recipe = tea.new_recipe()
    
    for range in ranges:
        text = tea.get_selection(context, range)
        
        # A blank range means we have only one range and it's empty
        # so we can't do any sorting
        if text == '':
            return False

        # Split the text into lines, not maintaining the linebreaks
        lines = text.splitlines(False)
        
        # Remove duplicates if set
        if remove_duplicates:
            if direction is None:
                seen = {}
                result = []
                for x in lines:
                    if x in seen: continue
                    seen[x] = 1
                    result.append(x)
                lines = result
            else:
                lines = list(set(lines))
        
        # Sort lines ascending or descending
        if direction == 'asc' or direction == 'desc':
            lines.sort()
            if direction == 'desc':
                lines.reverse()
        
        # If direction is random, shuffle lines
        if direction == 'random':
            random.shuffle(lines)
    
        # Join lines to one string
        linebreak = tea.get_line_ending(context)
        sortedText = unicode.join(linebreak, lines)
        
        # Add final linebreak if selected text has one
        if text.endswith(linebreak):
            sortedText += linebreak
        
        # Insert the text
        recipe.addReplacementString_forRange_(sortedText, range)
    
    if undo_name is not None:
        recipe.setUndoActionName_(undo_name)
    # Apply the recipe
    return context.applyTextRecipe_(recipe)

########NEW FILE########
__FILENAME__ = spaces_to_tabs
'''Converts spaces in the document to tabs and vice-versa'''

import re

import tea_actions as tea

# This is a special variable; if it exists in a module, the module will be
# passed the actionObject as the second parameter
req_action_object = True

def act(context, actionObject, operation='entab'):
    def replacements(match):
        '''Utility function for replacing items'''
        return match.group(0).replace(search, replace)
    
    spaces = int(actionObject.userInput().stringValue())
    if operation == 'entab':
        target = re.compile(r'^(\t* +\t*)+', re.MULTILINE)
        search = ' ' * spaces
        replace = '\t'
    else:
        target = re.compile(r'^( *\t+ *)+', re.MULTILINE)
        search = '\t'
        replace = ' ' * spaces
    insertions = tea.new_recipe()
    ranges = tea.get_ranges(context)
    if len(ranges) == 1 and ranges[0].length == 0:
        # No selection, use the document
        ranges[0] = tea.new_range(0, context.string().length())
    for range in ranges:
        text = tea.get_selection(context, range)
        # Non-Unix line endings will bork things; convert them
        text = tea.unix_line_endings(text)
        text = re.sub(target, replacements, text)
        if tea.get_line_ending(context) != '\n':
            text = tea.clean_line_endings(context, text)
        insertions.addReplacementString_forRange_(text, range)
    insertions.setUndoActionName_(operation.title())
    context.applyTextRecipe_(insertions)
    
    return True

########NEW FILE########
__FILENAME__ = trim
'''
Trims the text; what is trimmed depends on what's passed in via XML
'''

import tea_actions as tea

def act(context, input=None, alternate=None, trim='both', respect_indent=False,
        undo_name=None):
    '''
    Required action method
    
    input dictates what should be trimmed:
    - None (default): falls back to alternate
    - selection: ignores lines if they exist, just trims selection
    - selected_lines: each line in the selection
    
    alternate dictates what to fall back on
    - None (default): will do nothing if input is blank
    - line: will trim the line the caret is on
    - all_lines: all lines in the document
    
    trim dictates what part of the text should be trimmed:
    - both (default)
    - start
    - end
    
    If respect_indent is True, indent characters (as defined in preferences)
    at the beginning of the line will be left untouched.
    '''
    # Since input is always a selection of some kind, check if we have one
    ranges = tea.get_ranges(context)
    insertions = tea.new_recipe()
    if (len(ranges) == 1 and ranges[0].length == 0) or input is None:
        if alternate == 'line':
            text, range = tea.get_line(context, ranges[0])
            text = tea.trim(context, text, False, trim, respect_indent)
        elif alternate == 'all_lines':
            range = tea.new_range(0, context.string().length())
            text = tea.get_selection(context, range)
            text = tea.trim(context, text, True, trim, respect_indent)
        insertions.addReplacementString_forRange_(text, range)
    else:
        if input == 'selected_lines':
            parse_lines = True
        else:
            parse_lines = False
        for range in ranges:
            text = tea.get_selection(context, range)
            text = tea.trim(context, text, parse_lines, trim, respect_indent)
            insertions.addReplacementString_forRange_(text, range)
    if undo_name != None:
        insertions.setUndoActionName_(undo_name)
    return context.applyTextRecipe_(insertions)

########NEW FILE########
__FILENAME__ = visit_url
'''
Visits a URL, filling a placeholder with selected text (or similar)
'''

import urllib

from Foundation import NSWorkspace, NSURL

import tea_actions as tea

def act(context, input=None, default=None, **syntaxes):
    '''
    Required action method
    
    input dictates what fills the placeholder if there is no selection:
    - word
    - line
    
    default and syntaxes will replace $EDITOR_SELECTION with a URL escaped version
    of the selected text (or input, if no selected text)
    '''
    text, range = tea.get_single_selection(context)
    if text is None:
        range = tea.get_single_range(context)
        if input == 'word':
            text, range = tea.get_word(context, range)
        elif input == 'line':
            text, range = tea.get_line(context, range)
    # If we still don't have text, there's nothing to work with
    if text is None:
        return False
    # URL escape the selected text
    text = urllib.quote_plus(text)
    url = tea.select_from_zones(context, range, default, **syntaxes)
    # Got the URL, let's run the URL
    # DEPRECATED: please use $EDITOR_SELECTION instead
    url = url.replace('$SELECTED_TEXT', text)
    url = url.replace('$EDITOR_SELECTION', text)
    NSWorkspace.sharedWorkspace().openURL_(NSURL.URLWithString_(url))
    # Because this gets passed through to Obj-C, using int prevents beeping
    return True

########NEW FILE########
__FILENAME__ = word_to_snippet
'''Converts word or selection under the cursor into a snippet'''

import tea_actions as tea

from zencoding import zen_core
import zen_settings_loader

def act(context, default=None, alpha_numeric=True, extra_characters='',
        bidirectional=True, mode=None, close_string='', undo_name=None,
        **syntaxes):
    '''
    Required action method
    
    Transforms the word under the cursor (or the word immediately previous
    to the cursor) into a snippet (or processes it using zen-coding)
    
    The snippet offers two placeholders:
    $EDITOR_SELECTION: replaced with the word, or any selected text
    $WORD: if text is selected, replaced just with the first word
    '''
    
    if default is None:
        return False
    range = tea.get_single_range(context, True)
    if range == None:
        return False
    # Check for specific zone override
    snippet = tea.select_from_zones(context, range, default, **syntaxes)
    # Fetch the word
    word, new_range = tea.get_word_or_selection(context, range, alpha_numeric,
                                                extra_characters, bidirectional)
    if word == '':
        # No word, so nothing further to do
        return False
    # If we're using $WORD, make sure the word is just a word
    if snippet.find('$WORD') >= 0:
        fullword = word
        word = tea.parse_word(word)
        if word is None:
            word = ''
    else:
        fullword = word
    
    # We've got some extra work if the mode is HTML or zen
    # This is a really hacky solution, but I can't think of a concise way to
    # represent this functionality via XML
    # TODO remove it
    if mode == 'zen' and fullword.find(' ') < 0:
        # Explicitly load zen settings
        zen_settings = zen_settings_loader.load_settings()
        zen_core.update_settings(zen_settings)
        
        # Set up the config variables
        zen_core.newline = tea.get_line_ending(context)
        zen_settings['variables']['indentation'] = tea.get_indentation_string(context)
        
        # This allows us to use smart incrementing tab stops in zen snippets
        point_ix = [0]
        def place_ins_point(text):
            point_ix[0] += 1
            return '$%s' % point_ix[0]
        zen_core.insertion_point = place_ins_point
    
        # Detect the type of document we're working with
        zones = {
            'css, css *': 'css',
            'xsl, xsl *': 'xsl',
            'xml, xml *': 'xml'
        }
        doc_type = tea.select_from_zones(context, range, 'html', **zones)
        
        # Setup the zen profile based on doc_type and XHTML status
        profile = {}
        if doc_type == 'html':
            close_string = tea.get_tag_closestring(context)
            if close_string == '/':
                profile['self_closing_tag'] = True
            elif close_string != ' /':
                profile['self_closing_tag'] = False
        elif doc_type == 'xml':
            profile = {'self_closing_tag': True, 'tag_nl': True}
        
        zen_core.setup_profile('tea_profile', profile)
        
        # Prepare the snippet
        snippet = zen_core.expand_abbreviation(fullword, doc_type, 'tea_profile')
    elif (mode == 'zen' or mode == 'html') and tea.is_selfclosing(word):
        # Self-closing, so construct the snippet from scratch
        snippet = '<' + fullword
        if fullword == word and not fullword in ['br', 'hr']:
            snippet += ' $1'
        snippet += '$E_XHTML>$0'
    # Special replacement in case we're using $WORD
    snippet = snippet.replace('$WORD', word)
    # Construct the snippet
    snippet = tea.construct_snippet(fullword, snippet)
    return tea.insert_snippet_over_range(context, snippet, new_range, undo_name)

########NEW FILE########
__FILENAME__ = zen_actions
#!/usr/bin/env python
# -*- coding: utf-8 -*-

from zen_editor import ZenEditor
from zencoding import zen_core as zen_coding

# This is a special variable; if it exists in a module, the module will be
# passed the actionObject as the second parameter
req_action_object = True

def act(context, actionObject, action_name, undo_name=None):
    zen_editor = ZenEditor(context)
    
    if action_name == 'wrap_with_abbreviation':
        abbr = actionObject.userInput().stringValue()
        if abbr:
            return zen_coding.run_action(action_name, zen_editor, abbr)
    else:
        return zen_coding.run_action(action_name, zen_editor)
            
    return False
########NEW FILE########
