__FILENAME__ = bootstrap
import sublime


def plugin_loaded():
    # Native package causes some conflicts.
    disable_native_markdown_package()

def disable_native_markdown_package():
    settings = sublime.load_settings('Preferences.sublime-settings')
    ignored_packages = settings.get('ignored_packages', [])

    if 'Markdown' not in ignored_packages:
        ignored_packages.append('Markdown')
        settings.set('ignored_packages', ignored_packages)
        sublime.save_settings('Preferences.sublime-settings')

########NEW FILE########
__FILENAME__ = custom_find_under_expand
"""
	Re-implements `find_under_expand` command because ST refuses to use it inside macro
	definitions.

	Source: http://www.sublimetext.com/forum/viewtopic.php?f=3&t=5148
"""

import sublime, sublime_plugin


class CustomFindUnderExpandCommand(sublime_plugin.TextCommand):
    def run(self, edit):
        regions = []

        for s in self.view.sel():
            word = self.view.word(sublime.Region(s.begin(), s.end()))
            regions.append(word)

        for r in regions:
            self.view.sel().add(r)

########NEW FILE########
__FILENAME__ = distraction_free_mode
"""
    This file contains some "distraction free" mode improvements. However they can be
    used in normal mode, too. These features can be enabled/disabled via settings files.
    In order to target "distraction free" mode, FullScreenStatus plugin must be installed:
    https://github.com/maliayas/SublimeText_FullScreenStatus
"""

import sublime, sublime_plugin


def on_distraction_free():
    return sublime.active_window().settings().get('fss_on_distraction_free')

def view_is_markdown(view):
    return bool(view.score_selector(view.sel()[0].a, "text.html.markdown"))

class KeepCurrentLineCentered(sublime_plugin.EventListener):
    def on_modified(self, view):
        # One of the MarkdownEditing syntax files must be in use.
        if not view_is_markdown(view):
            return False

        if on_distraction_free():
            if view.settings().get("mde.distraction_free_mode").get("mde.keep_centered") is False:
                return False

        else:
            if view.settings().get("mde.keep_centered") is False:
                return False

        view.show_at_center(view.sel()[0].begin())

########NEW FILE########
__FILENAME__ = footnotes
import sublime
import sublime_plugin
import re

DEFINITION_KEY = 'MarkdownEditing-footnote-definitions'
REFERENCE_KEY = 'MarkdownEditing-footnote-references'
REFERENCE_REGEX = "\[\^([^\]]*)\]"
DEFINITION_REGEX = "^ *\[\^([^\]]*)\]:"


def get_footnote_references(view):
    ids = {}
    for ref in view.get_regions(REFERENCE_KEY):
        if not re.match(DEFINITION_REGEX, view.substr(view.line(ref))):
            id = view.substr(ref)[2:-1]
            if id in ids:
                ids[id].append(ref)
            else:
                ids[id] = [ref]
    return ids


def get_footnote_definition_markers(view):
    ids = {}
    for defn in view.get_regions(DEFINITION_KEY):
        id = view.substr(defn).strip()[2:-2]
        ids[id] = defn
    return ids


def get_footnote_identifiers(view):
    ids = get_footnote_references(view).keys()
    ids.sort()
    return ids


def get_last_footnote_marker(view):
    ids = sorted([int(a) for a in get_footnote_identifiers(view) if a.isdigit()])
    if len(ids):
        return int(ids[-1])
    else:
        return 0


def get_next_footnote_marker(view):
    return get_last_footnote_marker(view) + 1


def is_footnote_definition(view):
    line = view.substr(view.line(view.sel()[-1]))
    return re.match(DEFINITION_REGEX, line)


def is_footnote_reference(view):
    refs = view.get_regions(REFERENCE_KEY)
    for ref in refs:
        if ref.contains(view.sel()[0]):
            return True
    return False


def strip_trailing_whitespace(view, edit):
    tws = view.find('\s+\Z', 0)
    if tws:
        view.erase(edit, tws)


class MarkFootnotes(sublime_plugin.EventListener):
    def update_footnote_data(self, view):
        view.add_regions(REFERENCE_KEY, view.find_all(REFERENCE_REGEX), '', 'cross', sublime.HIDDEN)
        view.add_regions(DEFINITION_KEY, view.find_all(DEFINITION_REGEX), '', 'cross', sublime.HIDDEN)

    def on_modified(self, view):
        self.update_footnote_data(view)

    def on_load(self, view):
        self.update_footnote_data(view)


class GatherMissingFootnotesCommand(sublime_plugin.TextCommand):
    def run(self, edit):
        edit = self.view.begin_edit()
        refs = get_footnote_identifiers(self.view)
        defs = get_footnote_definition_markers(self.view)
        missingnotes = [note_token for note_token in refs if not note_token in defs]
        if len(missingnotes):
            self.view.insert(edit, self.view.size(), "\n")
            for note in missingnotes:
                self.view.insert(edit, self.view.size(), '\n [^%s]: ' % note)
        self.view.end_edit(edit)

    def is_enabled(self):
        return bool(self.view.score_selector(self.view.sel()[0].a, "text.html.markdown"))


class InsertFootnoteCommand(sublime_plugin.TextCommand):
    def run(self, edit):
        edit = self.view.begin_edit()
        startloc = self.view.sel()[-1].end()
        markernum = get_next_footnote_marker(self.view)
        if bool(self.view.size()):
            targetloc = self.view.find('(\s|$)', startloc).begin()
        else:
            targetloc = 0
        self.view.insert(edit, targetloc, '[^%s]' % markernum)
        self.view.insert(edit, self.view.size(), '\n [^%s]: ' % markernum)
        self.view.run_command('set_motion', {"inclusive": True, "motion": "move_to", "motion_args": {"extend": True, "to": "eof"}})
        if self.view.settings().get('command_mode'):
            self.view.run_command('enter_insert_mode', {"insert_command": "move", "insert_args": {"by": "characters", "forward": True}})
        self.view.end_edit(edit)

    def is_enabled(self):
        return bool(self.view.score_selector(self.view.sel()[0].a, "text.html.markdown"))


class GoToFootnoteDefinitionCommand(sublime_plugin.TextCommand):
    def run(self, edit):
        defs = get_footnote_definition_markers(self.view)
        regions = self.view.get_regions(REFERENCE_KEY)

        sel = self.view.sel()
        if len(sel) == 1:
            target = None
            selreg = sel[0]

            for region in regions:
                if selreg.intersects(region):
                    target = self.view.substr(region)[2:-1]
            if not target:
                try:
                    target = self.view.substr(self.view.find(REFERENCE_REGEX, sel[-1].end()))[2:-1]
                except:
                    pass
            if target:
                self.view.sel().clear()
                self.view.sel().add(defs[target])
                self.view.show(defs[target])

    def is_enabled(self):
        return bool(self.view.score_selector(self.view.sel()[0].a, "text.html.markdown"))


class GoToFootnoteReferenceCommand(sublime_plugin.TextCommand):
    def run(self, edit):
        refs = get_footnote_references(self.view)
        match = is_footnote_definition(self.view)
        if match:
            target = match.groups()[0]
            self.view.sel().clear()
            [self.view.sel().add(a) for a in refs[target]]
            self.view.show(refs[target][0])

    def is_enabled(self):
        return bool(self.view.score_selector(self.view.sel()[0].a, "text.html.markdown"))


class MagicFootnotesCommand(sublime_plugin.TextCommand):
    def run(self, edit):
        if (is_footnote_definition(self.view)):
            self.view.run_command('go_to_footnote_reference')
        elif (is_footnote_reference(self.view)):
            self.view.run_command('go_to_footnote_definition')
        else:
            self.view.run_command('insert_footnote')

    def is_enabled(self):
        return bool(self.view.score_selector(self.view.sel()[0].a, "text.html.markdown"))


class SwitchToFromFootnoteCommand(sublime_plugin.TextCommand):
    def run(self, edit):
        if (is_footnote_definition(self.view)):
            self.view.run_command('go_to_footnote_reference')
        else:
            self.view.run_command('go_to_footnote_definition')

    def is_enabled(self):
        return bool(self.view.score_selector(self.view.sel()[0].a, "text.html.markdown"))


class SortFootnotesCommand(sublime_plugin.TextCommand):
    def run(self, edit):
        edit = self.view.begin_edit()
        strip_trailing_whitespace(self.view, edit)
        self.view.end_edit(edit)
        edit = self.view.begin_edit()
        defs = get_footnote_definition_markers(self.view)
        notes = {}
        erase = []
        keyorder = map(lambda x: self.view.substr(x)[2:-1], self.view.get_regions(REFERENCE_KEY))
        keys = []
        [keys.append(r) for r in keyorder if not r in keys]

        for (key, item) in defs.items():
            fnend = self.view.find('(\s*\Z|\n\s*\n(?!\ {4,}))', item.end())
            fnreg = sublime.Region(item.begin(), fnend.end())
            notes[key] = self.view.substr(fnreg).strip()
            erase.append(fnreg)
        erase.sort()
        erase.reverse()
        [self.view.erase(edit, reg) for reg in erase]
        self.view.end_edit(edit)

        edit = self.view.begin_edit()
        for key in keys:
            self.view.insert(edit, self.view.size(), '\n\n ' + notes[key])
        self.view.end_edit(edit)

    def is_enabled(self):
        return bool(self.view.score_selector(self.view.sel()[0].a, "text.html.markdown"))

########NEW FILE########
__FILENAME__ = gather_missing_links
import sublime_plugin


class GatherMissingLinkMarkersCommand(sublime_plugin.TextCommand):
    def run(self, edit):
        markers = []
        self.view.find_all("\]\[([^\]]+)\]", 0, "$1", markers)
        self.view.find_all("\[([^\]]*)\]\[\]", 0, "$1", markers)
        missinglinks = [link for link in set(markers) if not self.view.find_all("\n\s*\[%s\]:" % link)]
        if len(missinglinks):
            # Remove all whitespace at the end of the file
            whitespace_at_end = self.view.find(r'\s*\z', 0)
            self.view.replace(edit, whitespace_at_end, "\n")

            # If there is not already a reference list at the and, insert a new line at the end
            if not self.view.find(r'\n\s*\[[^\]]*\]:.*\s*\z', 0):
                self.view.insert(edit, self.view.size(), "\n")

            for link in missinglinks:
                self.view.insert(edit, self.view.size(), '[%s]: \n' % link)

    def is_enabled(self):
        return bool(self.view.score_selector(self.view.sel()[0].a, "text.html.markdown"))

########NEW FILE########
__FILENAME__ = indent_list_item
import sublime_plugin
import re

class IndentListItemCommand(sublime_plugin.TextCommand):
    def run(self, edit, reverse = False):
        for region in self.view.sel():
            line = self.view.line(region)
            line_content = self.view.substr(line)

            bullet_pattern = "([*+\\-])"

            new_line = line_content

            # Transform the bullet to the next/previous bullet type
            if self.view.settings().get("mde.list_indent_auto_switch_bullet", True):
                bullets = self.view.settings().get("mde.list_indent_bullets", ["*", "-", "+"])

                for key, bullet in enumerate(bullets):
                    if bullet in new_line:
                        new_line = new_line.replace(bullet, bullets[(key + (1 if not reverse else -1)) % len(bullets)])
                        break

            # Determine how to indent (tab or spaces)
            if self.view.settings().get("translate_tabs_to_spaces"):
                tab_str = self.view.settings().get("tab_size", 4) * " "

            else:
                tab_str = "\t"

            if not reverse:
                # Do the indentation
                new_line = re.sub(bullet_pattern, tab_str + "\\1", new_line)

            else:
                # Do the unindentation
                new_line = re.sub(tab_str + bullet_pattern, "\\1", new_line)

            # Insert the new item
            self.view.replace(edit, line, new_line)

    def is_enabled(self):
        return bool(self.view.score_selector(self.view.sel()[0].a, "text.html.markdown"))

########NEW FILE########
__FILENAME__ = insert_references
# -*- coding: UTF-8 -*-

import sublime
import sublime_plugin
import re


def get_clipboard_if_url():
    # If the clipboard contains an URL, return it
    # Otherwise, return an empty string
    re_match_urls = re.compile(r"""((?:[a-z][\w-]+:(?:/{1,3}|[a-z0-9%])|www\d{0,3}[.]|[a-z0-9.\-]+[.‌​][a-z]{2,4}/)(?:[^\s()<>]+|(([^\s()<>]+|(([^\s()<>]+)))*))+(?:(([^\s()<>]+|(‌​([^\s()<>]+)))*)|[^\s`!()[]{};:'".,<>?«»“”‘’]))""", re.DOTALL)
    m = re_match_urls.search(sublime.get_clipboard())
    return m.group() if m else ''


def mangle_url(url):
    url = url.strip()
    if re.match(r'^([a-z0-9-]+\.)+\w{2,4}', url, re.IGNORECASE):
        url = 'http://' + url
    return url


def check_for_link(view, url):
    titles = []
    # Check if URL is already present as reference link
    view.find_all(r'^\s{0,3}\[([^^\]]+)\]:[ \t]+' + re.escape(url) + '$', 0, '$1', titles)
    return titles[0] if titles else None


def append_reference_link(edit, view, title, url):
    # Detect if file ends with \n
    if view.substr(view.size() - 1) == '\n':
        nl = ''
    else:
        nl = '\n'
    # Append the new reference link to the end of the file
    view.insert(edit, view.size(), '{0}[{1}]: {2}\n'.format(nl, title, url))


def insert_references(edit, view, title):
    # Add a reference with given title at the current cursor or around the current selection(s)
    sels = view.sel()
    caret = []

    for sel in sels:
        text = view.substr(sel)
        # If something is selected...
        if len(text) > 0:
            # ... turn the selected text into the link text
            view.replace(edit, sel, "[{0}][{1}]".format(text, title))
        else:
            # Add the link, with empty link text, and the caret positioned
            # ready to type the link text
            view.replace(edit, sel, "[][{0}]".format(title))
            caret += [sublime.Region(sel.begin() + 1, sel.begin() + 1)]

    if len(caret) > 0:
        sels.clear()
        for c in caret:
            sels.add(c)


# Inspired by http://www.leancrew.com/all-this/2012/08/markdown-reference-links-in-bbedit/
# Appends a new reference link to end of document, using a user-input name and URL.
# Then inserts a reference to the link at the current selection(s).

class InsertNamedReferenceCommand(sublime_plugin.TextCommand):

    def description(self):
        return 'Insert Numbered Reference Link'

    def run(self, edit):
        self.view.window().show_input_panel(
            'URL to link to:',
            get_clipboard_if_url(),
            self.receive_link,
            None, None)

    def receive_link(self, linkurl):
        linkurl = mangle_url(linkurl)

        newref = check_for_link(self.view, linkurl)
        if newref:
            # Link already exists, reuse existing reference
            self.insert_link(linkurl, newref, False)

        else:
            self.view.window().show_input_panel(
                'Name for reference:', '',
                lambda newref: self.insert_link(linkurl, newref),
                None, None)

    def insert_link(self, linkurl, newref, actually_insert=True):
        # Check if title is already present as reference
        if actually_insert and self.view.find(r'^\s{0,3}\[' + re.escape(newref) + '\]:[ \t]+', 0):
            sublime.error_message('A reference named "' + newref + '" already exists.')
            self.view.window().show_input_panel(
                'Name for reference:', '',
                lambda newref: self.insert_link(linkurl, newref),
                None, None)
            return

        edit = self.view.begin_edit()

        try:
            if actually_insert:
                append_reference_link(edit, self.view, newref, linkurl)

            insert_references(edit, self.view, newref)

        finally:
            self.view.end_edit(edit)

    def is_enabled(self):
        return bool(self.view.score_selector(self.view.sel()[0].a, "text.html.markdown"))


# Inspired by http://www.leancrew.com/all-this/2012/08/markdown-reference-links-in-bbedit/
# Appends a new reference link to end of document, using an autoincrementing number as the reference title.
# Then inserts a reference to the link at the current selection(s).

class InsertNumberedReferenceCommand(sublime_plugin.TextCommand):

    def description(self):
        return 'Insert Numbered Reference Link'

    def run(self, edit):
        self.view.window().show_input_panel(
            'URL to link to:',
            get_clipboard_if_url(),
            self.insert_link,
            None, None)

    def insert_link(self, linkurl):
        edit = self.view.begin_edit()

        try:
            linkurl = mangle_url(linkurl)
            newref = check_for_link(self.view, linkurl)
            if not newref:
                # Find the next reference number
                reflinks = self.view.find_all(r'(?<=^\[)(\d+)(?=\]: )')
                if len(reflinks) == 0:
                    newref = 1
                else:
                    newref = max(int(self.view.substr(reg)) for reg in reflinks) + 1

                append_reference_link(edit, self.view, newref, linkurl)

            insert_references(edit, self.view, newref)

        finally:
            self.view.end_edit(edit)

    def is_enabled(self):
        return bool(self.view.score_selector(self.view.sel()[0].a, "text.html.markdown"))

########NEW FILE########
__FILENAME__ = jumpToMarker
# Author: Gabriel Weatherhead
# Contact: gabe@macdrifter.com

import sublime, sublime_plugin, re

class GotoReferenceCommand(sublime_plugin.TextCommand):
    def run(self, edit):
        self.linkRef = []
        self.view.find_all("(^\s{0,3}\\[.*?\\]:) (.*)", 0, "$1 $2", self.linkRef)
        self.view.window().show_quick_panel(self.linkRef, self.jump_to_link, sublime.MONOSPACE_FONT)

    def jump_to_link(self, choice):
        if choice == -1:
            return
        # Set a bookmark so we can easily jump back
        self.view.run_command('toggle_bookmark')
        findmarker = self.linkRef[choice].split(':', 1)[1].strip()
        if len(findmarker) == 0:
            findmarker = self.linkRef[choice].split(':', 1)[0].strip()
        self.view.sel().clear()
        # Get the selection
        pt = self.view.find(re.escape(findmarker+':'), 0)
        self.view.sel().add(pt)

    def is_enabled(self):
        return bool(self.view.score_selector(self.view.sel()[0].a, "text.html.markdown"))

########NEW FILE########
__FILENAME__ = list_markdown_references
import sublime, sublime_plugin
import re


# Based on http://www.macdrifter.com/2012/08/making-a-sublime-text-plugin-markdown-reference-viewer.html
# and http://www.leancrew.com/all-this/2012/08/more-markdown-reference-links-in-bbedit/
# Displays a list of reference links in the document, and
# inserts a reference to the chosen item at the current selection.

class ListMarkdownReferencesCommand(sublime_plugin.TextCommand):
    def run(self, edit):
        self.markers = []
        self.view.find_all(r'^\s{0,3}(\[[^^\]]+\]):[ \t]+(.+)$', 0, '$1: $2', self.markers)
        self.view.window().show_quick_panel(self.markers, self.insert_link, sublime.MONOSPACE_FONT)

    def insert_link(self, choice):
        if choice == -1:
            return
        edit = self.view.begin_edit()

        try:
            # Extract the reference name that was selected
            ref = re.match(r'^\[([^^\]]+)\]', self.markers[choice]).group(1)

            # Now, add a reference to that link at the current cursor or around the current selection(s)
            sels = self.view.sel()
            caret = []

            for sel in sels:
                text = self.view.substr(sel)
                # If something is selected...
                if len(text) > 0:
                    # ... turn the selected text into the link text
                    self.view.replace(edit, sel, "[{0}][{1}]".format(text, ref))
                else:
                    # Add the link, with empty link text, and the caret positioned
                    # ready to type the link text
                    self.view.replace(edit, sel, "[][{0}]".format(ref))
                    caret += [sublime.Region(sel.begin() + 1, sel.begin() + 1)]

            if len(caret) > 0:
                sels.clear()
                for c in caret:
                    sels.add(c)

        finally:
            self.view.end_edit(edit)

    def is_enabled(self):
        return bool(self.view.score_selector(self.view.sel()[0].a, "text.html.markdown"))

########NEW FILE########
__FILENAME__ = numbered_list
import sublime_plugin
import re

class NumberListCommand(sublime_plugin.TextCommand):
	def run(self, edit):
		view = self.view
		sel = view.sel()[0]
		text = view.substr(view.full_line(sel))
		num = re.search('\d', text).start()
		dot = text.find(".")
		if num == 0:
			view.insert(edit, sel.end(), "\n%d. " % (int(text[:dot]) + 1,))
		else:
			view.insert(edit, sel.end(), "\n%s%d. " % (text[:num], int(text[num:dot]) + 1))

	def is_enabled(self):
		return bool(self.view.score_selector(self.view.sel()[0].a, "text.html.markdown"))

########NEW FILE########
__FILENAME__ = paste_as_link
import sublime
import sublime_plugin


class PasteAsLinkCommand(sublime_plugin.TextCommand):
    def run(self, edit):
        view = self.view
        sel = view.sel()[0]
        text = view.substr(sel)
        contents = sublime.get_clipboard()
        view.replace(edit, sel, "["+text+"]("+contents+")")

    def is_enabled(self):
        return bool(self.view.score_selector(self.view.sel()[0].a, "text.html.markdown"))

########NEW FILE########
__FILENAME__ = paste_as_reference
import sublime
import sublime_plugin


class PasteAsReferenceCommand(sublime_plugin.TextCommand):
    def run(self, edit):
        view = self.view
        sel = view.sel()[0]
        text = view.substr(sel)
        contents = sublime.get_clipboard()
        self.view.replace(edit, sel, "["+text+"]: "+contents)

    def is_enabled(self):
        return bool(self.view.score_selector(self.view.sel()[0].a, "text.html.markdown"))

########NEW FILE########
__FILENAME__ = quote_indenting
import re
import sublime
import sublime_plugin


class IndentQuote(sublime_plugin.TextCommand):
    def description(self):
        return 'Indent a quote'

    def run(self, edit):
        view = self.view
        selections = view.sel()
        new_selections = []

        for selection in selections:
            lines_in_selection = self.view.lines(selection)
            all_lines = []

            expanded_selection_start = lines_in_selection[0].begin()
            for line in lines_in_selection:
                complete_line = view.line(line)
                expanded_selection_end = complete_line.end()
                text = view.substr(complete_line)
                all_lines.append("> " + text)

            expanded_selection = sublime.Region(expanded_selection_start, expanded_selection_end)

            replacement_text = "\n".join(all_lines)
            view.replace(edit, expanded_selection, replacement_text)

            new_selections.append(sublime.Region(expanded_selection_start, expanded_selection_start + len(replacement_text)))

        selections.clear()
        for selection in new_selections:
            selections.add(selection)

    def is_enabled(self):
        return bool(self.view.score_selector(self.view.sel()[0].a, "text.html.markdown"))


class DeindentQuote(sublime_plugin.TextCommand):
    def description(self):
        return 'Deindent a quote'

    def run(self, edit):
        view = self.view
        selections = view.sel()
        new_selections = []

        for selection in selections:
            lines_in_selection = self.view.lines(selection)
            all_lines = []

            expanded_selection_start = lines_in_selection[0].begin()
            for line in lines_in_selection:
                complete_line = view.line(line)
                expanded_selection_end = complete_line.end()
                text = view.substr(complete_line)
                all_lines.append(re.sub(r'^(> )', '', text))

            expanded_selection = sublime.Region(expanded_selection_start, expanded_selection_end)

            replacement_text = "\n".join(all_lines)
            view.replace(edit, expanded_selection, replacement_text)

            new_selections.append(sublime.Region(expanded_selection_start, expanded_selection_start + len(replacement_text)))

        selections.clear()
        for selection in new_selections:
            selections.add(selection)

    def is_enabled(self):
        return bool(self.view.score_selector(self.view.sel()[0].a, "text.html.markdown"))

########NEW FILE########
__FILENAME__ = underlined_headers
"""Commands for working with with setext-style (underlined) Markdown headers.

Header dashes can be completed with <tab>. For example:

	This is an H2
	-<tab>

Becomes:

	This is an H2
	-------------

Inspired by the similar TextMate command.

Also adds "Fix Underlined Markdown Headers" to Tools > Command Palette. After modifying
header text, this command will re-align the underline dashes with the new text length.

"""
import sublime, sublime_plugin
import re, itertools

SETEXT_DASHES_RE = re.compile( r'''
	(?: =+ | -+ ) # A run of ---- or ==== underline characters.
	\s*           # Optional trailing whitespace.
	$             # Must fill the while line. Don't match "- list items"
	''', re.X )

SETEXT_HEADER_RE = re.compile( r'''
	^(.+)\n
	( =+ | -+ ) # A run of ---- or ==== underline characters.
	[ \t]*        # Optional trailing whitespace.
	$             # Must fill the while line. Don't match "- list items"
	''', re.X | re.M )

def fix_dashes(view, edit, text_region, dash_region):
	"""Replaces the underlined "dash" region of a setext header with a run of
	dashes or equal-signs that match the length of the header text."""

	if len(view.substr(text_region).strip()) == 0:
		# Ignore dashes not under text. They are HRs.
		return

	old_dashes = view.substr(dash_region)
	first_dash = old_dashes[0]
	new_dashes = first_dash * text_region.size()
	view.replace(edit, dash_region, new_dashes)


class CompleteUnderlinedHeaderCommand(sublime_plugin.TextCommand):
	"""If the current selection is looks like a setext underline of - or = ,
	then inserts enough dash characters to match the length of the previous
	(header text) line."""

	def run(self, edit):
		for region in self.view.sel():
			dashes_line = self.view.line(region)
			# Ignore first list
			if dashes_line.begin() == 0: continue

			text_line = self.view.line(dashes_line.begin() - 1)
			if text_line.begin() < 0: continue

			text = self.view.substr(text_line)
			dashes = self.view.substr(dashes_line)

			# ignore, text_line is a list item
			if text.lstrip().startswith("-") and len(dashes.strip()) < 2:
				settings = self.view.settings()
				use_spaces = bool(settings.get('translate_tabs_to_spaces'))
				tab_size = int(settings.get('tab_size', 8))
				indent_characters = '\t'
				if use_spaces:
					    indent_characters = ' ' * tab_size
				self.view.insert(edit, dashes_line.begin(), indent_characters)
				break

			m = SETEXT_DASHES_RE.match(dashes)
			if m:
				fix_dashes(self.view, edit, text_line, dashes_line)

	def is_enabled(self):
		return bool(self.view.score_selector(self.view.sel()[0].a, "text.html.markdown"))


class FixAllUnderlinedHeadersCommand(sublime_plugin.TextCommand):
	"""Searches for all setext headings resize them to match the preceding
	header text."""

	def description(self):
		# Used as the name for Undo.
		return 'Fix Underlined Markdown Headers'

	def run(self, edit):
		lines = self.view.split_by_newlines(sublime.Region(0, self.view.size()))
		if len(lines) < 2: return

		# Since we're modifying the text, we are shifting all the following
		# regions. To avoid this, just go backwards.
		lines = reversed(lines)

		# Duplicate the iterator and next() it once to get farther ahead.
		# Since lines are reversed, this will always point to the line *above*
		# the current one: the text of the header.
		prev_lines, lines = itertools.tee(lines)
		next(prev_lines)

		for text_line, dashes_line in zip(prev_lines, lines):
			dashes_text = self.view.substr(dashes_line)
			m = SETEXT_DASHES_RE.match(dashes_text)
			if m:
				fix_dashes(self.view, edit, text_line, dashes_line)

	def is_enabled(self):
		return bool(self.view.score_selector(self.view.sel()[0].a, "text.html.markdown"))

class ConvertToAtxCommand(sublime_plugin.TextCommand):

	def run(self, edit, closed=False):
		regions =  list(self.view.sel())
		if len(regions) == 1 and regions[0].size() == 0:
			regions = [sublime.Region(0, self.view.size())]
		regions.reverse()
		for region in regions:
			txt = self.view.substr(region)
			matches = list(SETEXT_HEADER_RE.finditer(txt))
			matches.reverse()
			for m in matches:
				mreg = sublime.Region(region.begin()+m.start(), region.begin()+m.end())
				atx = "# "
				if '-' in m.group(2):
					atx = "#" + atx
				closing = atx[::-1] if closed else ""
				self.view.replace(edit, mreg, atx + m.group(1) + closing)

	def is_enabled(self):
		return bool(self.view.score_selector(self.view.sel()[0].a, "text.html.markdown"))

########NEW FILE########
