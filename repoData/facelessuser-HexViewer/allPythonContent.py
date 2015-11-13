__FILENAME__ = hex_checksum
'''
Hex Viewer
Licensed under MIT
Copyright (c) 2011 Isaac Muse <isaacmuse@gmail.com>
'''

import sublime
import sublime_plugin
import re
from hex_common import *
import threading
import hashlib
import zlib
import sys
import whirlpool
import tiger
import sum_hashes

DEFAULT_CHECKSUM = "md5"
VALID_HASH = []

active_thread = None


def verify_hashes(hashes):
    global VALID_HASH
    for item in hashes:
        module = item.split(":")
        if len(module) == 2:
            try:
                getattr(sys.modules[module[0]], module[1])
                VALID_HASH.append(module[1])
            except:
                print "Hex Viewer: " + module[1] + " hash is not available!"
        else:
            try:
                hashlib.new(item)
                VALID_HASH.append(item)
            except:
                print "Hex Viewer: " + item + " hash is not available!"


# Extra hash SSL and ZLIB classes
class ssl_algorithm(object):
    __algorithm = None
    __name = None

    @property
    def name(self):
        return self.__name

    @property
    def digest_size(self):
        return self.__digest_size

    def algorithm(self, name, digest_size, arg):
        self.__algorithm = hashlib.new(name)
        self.__name = name
        self.__digest_size = digest_size
        self.update(arg)

    def copy(self):
        return None if self.__algorithm is None else self.__algorithm.copy()

    def digest(self):
        return None if self.__algorithm is None else self.__algorithm.digest()

    def hexdigest(self):
        return None if self.__algorithm is None else self.__algorithm.hexdigest()

    def update(self, arg):
        if self.__algorithm is not None:
            self.__algorithm.update(arg)


class zlib_algorithm(object):
    __algorithm = None
    __name = None
    __digest_size = 0
    __hash = 0

    @property
    def name(self):
        return self.__name

    @property
    def digest_size(self):
        return self.__digest_size

    def algorithm(self, name, digest_size, start, arg):
        self.__algorithm = getattr(zlib, name)
        self.__name = name
        self.__digest_size
        self.__hash = start
        self.update(arg)

    def copy(self):
        return self

    def digest(self):
        return None if self.__algorithm is None else self.__hash & 0xffffffff

    def hexdigest(self):
        return None if self.__algorithm is None else '%08x' % (self.digest())

    def update(self, arg):
        if self.__algorithm is not None:
            self.__hash = self.__algorithm(arg, self.__hash)


# Additional Hashes
class md2(ssl_algorithm):
    def __init__(self, arg=''):
        self.algorithm('md2', 16, arg)


class mdc2(ssl_algorithm):
    def __init__(self, arg=''):
        self.algorithm('mdc2', 16, arg)


class md4(ssl_algorithm):
    def __init__(self, arg=''):
        self.algorithm('md4', 16, arg)


class sha(ssl_algorithm):
    def __init__(self, arg=''):
        self.algorithm('sha', 20, arg)


class ripemd160(ssl_algorithm):
    def __init__(self, arg=''):
        self.algorithm('ripemd160', 20, arg)


class crc32(zlib_algorithm):
    def __init__(self, arg=''):
        self.algorithm('crc32', 4, 0, arg)


class adler32(zlib_algorithm):
    def __init__(self, arg=''):
        self.algorithm('adler32', 4, 1, arg)


# Sublime Text Commands
class checksum(object):
    thread = None

    def __init__(self, hash_algorithm=None, data=""):
        if hash_algorithm is None or not hash_algorithm in VALID_HASH:
            hash_algorithm = hv_settings.get("hash_algorithm", DEFAULT_CHECKSUM)
        if not hash_algorithm in VALID_HASH:
            hash_algorithm = DEFAULT_CHECKSUM
        self.hash = getattr(hashlib, hash_algorithm)(data)
        self.name = hash_algorithm

    def update(self, data=""):
        if isinstance(data, basestring):
            self.hash.update(data)

    def threaded_update(self, data=[]):
        if not isinstance(data, basestring):
            global active_thread
            self.thread = hash_thread(data, self.hash)
            self.thread.start()
            self.chunk_thread()
            active_thread = self

    def chunk_thread(self):
        ratio = float(self.thread.chunk) / float(self.thread.chunks)
        percent = int(ratio * 10)
        leftover = 10 - percent
        message = "[" + "-" * percent + ">" + "-" * leftover + ("] %3d%%" % int(ratio * 100)) + " chunks hashed"
        sublime.status_message(message)
        if not self.thread.is_alive():
            if self.thread.abort is True:
                sublime.status_message("Hash calculation aborted!")
                sublime.set_timeout(lambda: self.reset_thread(), 500)
            else:
                sublime.set_timeout(lambda: self.display(), 500)
        else:
            sublime.set_timeout(lambda: self.chunk_thread(), 500)

    def reset_thread(self):
        self.thread = None

    def display(self, window=None):
        if window is None:
            window = sublime.active_window()
        window.show_input_panel(self.name + ":", str(self.hash.hexdigest()), None, None, None)


class hash_thread(threading.Thread):
    def __init__(self, data, obj):
        self.hash = False
        self.data = data
        self.obj = obj
        self.chunk = 0
        self.chunks = len(data)
        self.abort = False
        threading.Thread.__init__(self)

    def run(self):
        for chunk in self.data:
            self.chunk += 1
            if self.abort:
                return
            else:
                self.obj.update(chunk)


class HashSelectionCommand(sublime_plugin.WindowCommand):
    algorithm = "md5"

    def has_selections(self):
        single = False
        view = self.window.active_view()
        if view is not None:
            if len(view.sel()) > 0:
                single = True
        return single

    def hash_eval(self, value):
        if value != -1:
            self.algorithm = VALID_HASH[value]
            if self.has_selections():
                # Initialize hasher and related values
                data = []
                view = self.window.active_view()
                hasher = checksum(self.algorithm)
                # Walk through all selections breaking up data by lines
                for sel in view.sel():
                    lines = view.substr(sel).splitlines(True)
                    for line in lines:
                        data.append(''.join(unichr(ord(c)).encode('utf-8') for c in line))
                hasher.threaded_update(data)

    def run(self):
        if self.has_selections():
            self.window.show_quick_panel(VALID_HASH, self.hash_eval)


class HashEvalCommand(sublime_plugin.WindowCommand):
    algorithm = "md5"

    def hash_eval(self, value):
        data = []
        hasher = checksum(self.algorithm)
        lines = value.splitlines(True)
        for line in lines:
            data.append(''.join(unichr(ord(c)).encode('utf-8') for c in line))
        hasher.threaded_update(data)

    def select_hash(self, value):
        if value != -1:
            self.algorithm = VALID_HASH[value]
            self.window.show_input_panel(
                "hash input:",
                "",
                self.hash_eval,
                None,
                None
            )

    def run(self, hash_algorithm=None):
        self.window.show_quick_panel(VALID_HASH, self.select_hash)


class HexChecksumCommand(sublime_plugin.WindowCommand):
    def is_enabled(self):
        return is_enabled()

    def run(self, hash_algorithm=None, panel=False):
        global active_thread
        if active_thread is not None and active_thread.thread is not None and active_thread.thread.is_alive():
            active_thread.thread.abort = True
        else:
            if not panel:
                self.get_checksum(hash_algorithm)
            else:
                self.window.show_quick_panel(VALID_HASH, self.select_checksum)

    def select_checksum(self, value):
        if value != -1:
            self.get_checksum(VALID_HASH[value])

    def get_checksum(self, hash_algorithm=None):
        view = self.window.active_view()
        if view is not None:
            sublime.set_timeout(lambda: sublime.status_message("Checksumming..."), 0)
            hex_hash = checksum(hash_algorithm)
            r_buffer = view.split_by_newlines(sublime.Region(0, view.size()))
            hex_data = []
            for line in r_buffer:
                hex_data.append(re.sub(r'[\da-z]{8}:[\s]{2}((?:[\da-z]+[\s]{1})*)\s*\:[\w\W]*', r'\1', view.substr(line)).replace(" ", "").decode("hex"))
            hex_hash.threaded_update(hex_data)


# Compose list of hashes
verify_hashes(
    [
        'md2', 'mdc2', 'md4', 'md5',
        'sha', 'sha1', 'sha224', 'sha256', 'sha384', 'sha512',
        'ripemd160',
        'zlib:crc32', 'zlib:adler32',
        'whirlpool:whirlpool',
        'tiger:tiger',
        'sum_hashes:sum8', 'sum_hashes:sum16', 'sum_hashes:sum24', 'sum_hashes:sum32',
        'sum_hashes:xor8'
    ]
)

#Define extra hash classes as members of hashlib
hashlib.md2 = md2
hashlib.mdc2 = mdc2
hashlib.md4 = md4
hashlib.sha = sha
hashlib.ripemd160 = ripemd160
hashlib.crc32 = crc32
hashlib.adler32 = adler32
hashlib.whirlpool = whirlpool.whirlpool
hashlib.tiger = tiger.tiger
hashlib.sum8 = sum_hashes.sum8
hashlib.sum16 = sum_hashes.sum16
hashlib.sum24 = sum_hashes.sum24
hashlib.sum32 = sum_hashes.sum32
hashlib.xor8 = sum_hashes.xor8

########NEW FILE########
__FILENAME__ = hex_common
'''
Hex Viewer
Licensed under MIT
Copyright (c) 2011 Isaac Muse <isaacmuse@gmail.com>
'''

import sublime
from os.path import basename

ADDRESS_OFFSET = 11
ASCII_OFFSET = 3
BITS_PER_BYTE = 8

hv_settings = sublime.load_settings('hex_viewer.sublime-settings')
hv_inspector_enable = hv_settings.get("inspector", False)


def is_enabled(current_view=None):
    window = sublime.active_window()
    if window == None:
        return False
    view = window.active_view()
    if view == None:
        return False
    # Check not only if active main view is hex,
    # check if current view is the main active view
    if current_view != None and current_view.id() != view.id():
        return False
    syntax = view.settings().get('syntax')
    language = basename(syntax).replace('.tmLanguage', '').lower() if syntax != None else "plain text"
    return (language == "hex")


def clear_edits(view):
    view.add_regions(
        "hex_edit",
        [],
        ""
    )


def is_hex_dirty(view):
    return True if len(view.get_regions("hex_edit")) != 0 else False


def get_hex_char_range(group_size, bytes_wide):
    return int((group_size * 2) * bytes_wide / (group_size) + bytes_wide / (group_size)) - 1


def get_byte_count(start, end, group_size):
    return int((end - start - 1) / (group_size * 2 + 1)) * int(group_size) + int(((end - start - 1) % (group_size * 2 + 1)) / 2 + 1)


def ascii_to_hex_col(index, group_size):
    #   Calculate byte number              Account for address
    #
    # current_char   wanted_byte
    # ------------ = -----------  => wanted_byte + offset = start_column
    #  total_chars   total_bytes
    #
    start_column = int(ADDRESS_OFFSET + (group_size * 2) * index / (group_size) + index / (group_size))
    # Convert byte column position to test point
    return start_column


def adjust_hex_sel(view, start, end, group_size):
    bytes = 0
    size = end - start
    if view.score_selector(start, 'raw.nibble.upper') == 0:
        if view.score_selector(start, 'raw.nibble.lower'):
            start -= 1
        elif view.score_selector(start + 1, 'raw.nibble.upper') and size > 0:
            start += 1
        else:
            start = None
    # Adjust ending of selection to end of last selected byte
    if size == 0 and start != None:
        end = start + 1
        bytes = 1
    elif view.score_selector(end, 'raw.nibble.lower') == 0:
        if view.score_selector(end - 1, 'raw.nibble.lower'):
            end -= 1
        else:
            end -= 2
    if start != None and end != None:
        bytes = get_byte_count(start, end, group_size)
    return start, end, bytes


def underline(selected_bytes):
    # Convert to empty regions
    new_regions = []
    for region in selected_bytes:
        start = region.begin()
        end = region.end()
        while start < end:
            new_regions.append(sublime.Region(start))
            start += 1
    return new_regions

########NEW FILE########
__FILENAME__ = hex_editor
'''
Hex Viewer
Licensed under MIT
Copyright (c) 2011 Isaac Muse <isaacmuse@gmail.com>
'''

import sublime
import sublime_plugin
import re
from os.path import basename
from struct import unpack
from hex_common import *

HIGHLIGHT_EDIT_SCOPE = "keyword"
HIGHLIGHT_EDIT_ICON = "none"
HIGHLIGHT_EDIT_STYLE = "underline"


class HexEditorListenerCommand(sublime_plugin.EventListener):
    fail_safe_view = None
    handshake = -1

    def restore(self, value):
        window = sublime.active_window()
        view = None
        if value.strip().lower() == "yes" and self.fail_safe_view != None:
            # Quit if cannot find window
            if window == None:
                self.reset()
                return

            # Get new view if one was created
            if self.handshake != -1:
                for v in window.views():
                    if self.handshake == v.id():
                        view = v
                        # Reset handshake so view won't be closed
                        self.handshake = -1
            if view == None:
                view = window.new_file()

            # Restore view
            if view != None:
                # Get highlight settings
                highlight_scope = hv_settings.get("highlight_edit_scope", HIGHLIGHT_EDIT_SCOPE)
                highlight_icon = hv_settings.get("highlight_edit_icon", HIGHLIGHT_EDIT_ICON)
                style = hv_settings.get("highlight_edit_style", HIGHLIGHT_EDIT_STYLE)

                # No icon?
                if highlight_icon == "none":
                    highlight_icon = ""

                # Process highlight style
                if style == "outline":
                    style = sublime.DRAW_OUTLINED
                elif style == "none":
                    style = sublime.HIDDEN
                elif style == "underline":
                    style = sublime.DRAW_EMPTY_AS_OVERWRITE
                else:
                    style = 0

                # Setup view with saved settings
                view.set_name(basename(self.fail_safe_view["name"]) + ".hex")
                view.settings().set("hex_viewer_bits", self.fail_safe_view["bits"])
                view.settings().set("hex_viewer_bytes", self.fail_safe_view["bytes"])
                view.settings().set("hex_viewer_actual_bytes", self.fail_safe_view["actual"])
                view.settings().set("hex_viewer_file_name", self.fail_safe_view["name"])
                view.settings().set("font_face", self.fail_safe_view["font_face"])
                view.settings().set("font_size", self.fail_safe_view["font_size"])
                view.set_syntax_file("Packages/HexViewer/Hex.tmLanguage")
                view.sel().clear()
                edit = view.begin_edit()
                view.replace(edit, sublime.Region(0, view.size()), self.fail_safe_view["buffer"])
                view.end_edit(edit)
                view.set_scratch(True)
                view.set_read_only(True)
                view.sel().add(sublime.Region(ADDRESS_OFFSET, ADDRESS_OFFSET))
                view.add_regions(
                    "hex_edit",
                    self.fail_safe_view["edits"],
                    highlight_scope,
                    highlight_icon,
                    style
                )
        self.reset()

    def reset(self):
        window = sublime.active_window()
        if window != None and self.handshake != -1:
            for v in window.views():
                if self.handshake == v.id():
                    window.focus_view(v)
                    window.run_command("close_file")
        self.fail_safe_view = None
        self.handshake = -1

    def on_close(self, view):
        if view.settings().has("hex_viewer_file_name") and is_hex_dirty(view):
            window = sublime.active_window()
            file_name = file_name = view.settings().get("hex_viewer_file_name")

            if window != None and file_name != None:
                # Save hex view settings
                self.fail_safe_view = {
                    "buffer": view.substr(sublime.Region(0, view.size())),
                    "bits":  view.settings().get("hex_viewer_bits"),
                    "bytes": view.settings().get("hex_viewer_bytes"),
                    "actual": view.settings().get("hex_viewer_actual_bytes"),
                    "name": file_name,
                    "font_face": view.settings().get("font_face"),
                    "font_size": view.settings().get("font_size"),
                    "edits": view.get_regions("hex_edit")
                }

                # Keep window from closing by creating a view
                # If the last is getting closed
                # Use this buffer as the restore view if restore occurs
                count = 0
                for v in window.views():
                    if not v.settings().get("is_widget"):
                        count += 1
                if count == 1:
                    view = sublime.active_window().new_file()
                    if view != None:
                        self.handshake = view.id()

                # Alert user that they can restore
                window.show_input_panel(
                    ("Restore %s? (yes | no):" % basename(file_name)),
                    "yes",
                    self.restore,
                    None,
                    lambda: self.restore(value="yes")
                )


class HexDiscardEditsCommand(sublime_plugin.WindowCommand):
    def is_enabled(self):
        return is_enabled() and len(self.window.active_view().get_regions("hex_edit"))

    def run(self):
        view = self.window.active_view()
        group_size = int(view.settings().get("hex_viewer_bits", None))
        bytes_wide = int(view.settings().get("hex_viewer_actual_bytes", None))
        clear_edits(view)
        self.window.run_command('hex_viewer', {"bits": group_size, "bytes": bytes_wide})


class HexEditorCommand(sublime_plugin.WindowCommand):
    handshake = -1

    def init(self):
        init_status = False

        # Get highlight settings
        self.highlight_scope = hv_settings.get("highlight_edit_scope", HIGHLIGHT_EDIT_SCOPE)
        self.highlight_icon = hv_settings.get("highlight_edit_icon", HIGHLIGHT_EDIT_ICON)
        style = hv_settings.get("highlight_edit_style", HIGHLIGHT_EDIT_STYLE)

        # No icon?
        if self.highlight_icon == "none":
            self.highlight_icon = ""

        # Process highlight style
        self.highlight_style = 0
        if style == "outline":
            self.highlight_style = sublime.DRAW_OUTLINED
        elif style == "none":
            self.highlight_style = sublime.HIDDEN
        elif style == "underline":
            self.highlight_style = sublime.DRAW_EMPTY_AS_OVERWRITE

        # Get Seetings from settings file
        group_size = self.view.settings().get("hex_viewer_bits", None)
        self.bytes_wide = self.view.settings().get("hex_viewer_actual_bytes", None)
        #Process hex grouping
        if group_size != None and self.bytes_wide != None:
            self.group_size = group_size / BITS_PER_BYTE
            init_status = True
        return init_status

    def is_enabled(self):
        return is_enabled()

    def apply_edit(self, value):
        edits = ""
        self.view = self.window.active_view()
        # Is this the same view as earlier?
        if self.handshake != -1 and self.handshake == self.view.id():
            total_chars = self.total_bytes * 2
            selection = self.line["selection"].replace(" ", "")

            # Transform string if provided
            if re.match("^s\:", value) != None:
                edits = value[2:len(value)].encode("hex")
            else:
                edits = value.replace(" ", "").lower()

            # See if change occured and if changes are valid
            if len(edits) != total_chars:
                self.edit_panel(value, "Unexpected # of bytes!")
                return
            elif re.match("[\da-f]{" + str(total_chars) + "}", edits) == None:
                self.edit_panel(value, "Invalid data!")
                return
            elif selection != edits:
                # Get previous dirty markers before modifying buffer
                regions = self.view.get_regions("hex_edit")

                # Construct old and new data for diffs
                edits = self.line["data1"] + edits + self.line["data2"]
                original = self.line["data1"] + selection + self.line["data2"]

                # Initialize
                ascii = " :"
                start = 0
                ascii_start_pos = self.ascii_pos
                hex_start_pos = self.line["range"].begin() + ADDRESS_OFFSET
                end = len(edits)
                count = 1
                change_start = None

                # Reconstruct line
                l_buffer = self.line["address"]
                while start < end:
                    byte_end = start + 2
                    value = edits[start:byte_end]

                    # Diff data and mark changed bytes
                    if value != original[start:byte_end]:
                        if change_start == None:
                            change_start = [hex_start_pos, ascii_start_pos]
                            # Check if group end
                            if count == self.group_size:
                                regions.append(sublime.Region(change_start[0], hex_start_pos + 2))
                                change_start[0] = None
                        else:
                            # Check if after group end
                            if change_start[0] == None:
                                change_start[0] = hex_start_pos
                            # Check if group end
                            if count == self.group_size:
                                regions.append(sublime.Region(change_start[0], hex_start_pos + 2))
                                change_start[0] = None
                    elif change_start != None:
                        if self.view.score_selector(hex_start_pos - 1, 'raw.nibble.lower'):
                            if change_start[0] != None:
                                regions.append(sublime.Region(change_start[0], hex_start_pos))
                        else:
                            if change_start[0] != None:
                                regions.append(sublime.Region(change_start[0], hex_start_pos - 1))
                        regions.append(sublime.Region(change_start[1], ascii_start_pos))
                        change_start = None

                    # Write bytes and add space and at group region end
                    l_buffer += value
                    if count == self.group_size:
                        l_buffer += " "
                        hex_start_pos += 1
                        count = 0

                    # Copy valid printible ascii chars over or substitute with "."
                    dec = unpack("=B", value.decode("hex"))[0]
                    ascii += chr(dec) if dec in xrange(32, 127) else "."
                    start += 2
                    count += 1
                    hex_start_pos += 2
                    ascii_start_pos += 1

                # Check for end of line case for highlight
                if change_start != None:
                    if change_start[0] != None:
                        regions.append(sublime.Region(change_start[0], hex_start_pos))
                    regions.append(sublime.Region(change_start[1], ascii_start_pos))
                    change_start = None

                # Append ascii chars to line accounting for missing bytes in line
                delta = int(self.bytes_wide) - len(edits) / 2
                group_space = int(delta / self.group_size) + (1 if delta % self.group_size else 0)
                l_buffer += " " * (group_space + delta * 2) + ascii

                # Apply buffer edit
                self.view.sel().clear()
                self.view.set_read_only(False)
                edit = self.view.begin_edit()
                self.view.replace(edit, self.line["range"], l_buffer)
                self.view.end_edit(edit)
                self.view.set_read_only(True)
                self.view.sel().add(sublime.Region(self.start_pos, self.end_pos))

                # Underline if required
                if self.highlight_style == sublime.DRAW_EMPTY_AS_OVERWRITE:
                    regions = underline(regions)

                # Highlight changed bytes
                self.view.add_regions(
                    "hex_edit",
                    regions,
                    self.highlight_scope,
                    self.highlight_icon,
                    self.highlight_style
                )

                # Update selection
                self.window.run_command('hex_highlighter')
        else:
            sublime.error_message("Hex view is no longer in focus! Edit Failed.")
        # Clean up
        self.reset()

    def reset(self):
        self.handshake = -1
        self.total_bytes = 0
        self.start_pos = -1
        self.end_pos = -1
        self.line = {}

    def ascii_to_hex(self, start, end):
        bytes = 0
        size = end - start
        ascii_range = self.view.extract_scope(start)

        # Determine if selection is within ascii range
        if start >= ascii_range.begin() and end <= ascii_range.end() + 1:
            # Single char selection or multi
            bytes = 1 if size == 0 else end - start

        if bytes != 0:
            row, column = self.view.rowcol(start)
            column = ascii_to_hex_col(start - ascii_range.begin(), self.group_size)
            hex_pos = self.view.text_point(row, column)
            start = hex_pos

             # Traverse row finding the specified bytes
            byte_count = bytes
            while byte_count:
                # Byte rising edge
                if self.view.score_selector(hex_pos, 'raw.nibble.upper'):
                    hex_pos += 2
                    byte_count -= 1
                    # End of selection
                    if byte_count == 0:
                        end = hex_pos - 1
                else:
                    hex_pos += 1
        return start, end, bytes

    def edit_panel(self, value, error=None):
        msg = "Edit:" if error == None else "Edit (" + error + "):"
        self.window.show_input_panel(
            msg,
            value,
            self.apply_edit,
            None,
            self.reset
        )

    def run(self):
        self.view = self.window.active_view()

        # Identify view
        if self.handshake != -1 and self.handshake == self.view.id():
            self.reset()
        self.handshake = self.view.id()

        # Single selection?
        if len(self.view.sel()) == 1:
            # Init
            if not self.init():
                self.reset()
                return
            sel = self.view.sel()[0]
            start = sel.begin()
            end = sel.end()
            bytes = 0

            # Get range of hex data
            line = self.view.line(start)
            range_start = line.begin() + ADDRESS_OFFSET
            range_end = range_start + get_hex_char_range(self.group_size, self.bytes_wide)
            hex_range = sublime.Region(range_start, range_end)

            if self.view.score_selector(start, "comment"):
                start, end, bytes = self.ascii_to_hex(start, end)

            # Determine if selection is within hex range
            if start >= hex_range.begin() and end <= hex_range.end():
                # Adjust beginning of selection to begining of first selected byte
                if bytes == 0:
                    start, end, bytes = adjust_hex_sel(self.view, start, end, self.group_size)

                # Get general line info for diffing and editing
                if bytes != 0:
                    self.ascii_pos = hex_range.end() + ASCII_OFFSET
                    self.total_bytes = bytes
                    self.start_pos = start
                    self.end_pos = end + 1
                    selection = self.view.substr(sublime.Region(start, end + 1))
                    self.line = {
                        "range": line,
                        "address": self.view.substr(sublime.Region(line.begin(), line.begin() + ADDRESS_OFFSET)),
                        "selection": selection.replace(" ", ""),
                        "data1": self.view.substr(sublime.Region(hex_range.begin(), start)).replace(" ", ""),
                        "data2": self.view.substr(sublime.Region(end + 1, hex_range.end() + 1)).replace(" ", "")
                    }

                    # Send selected bytes to be edited
                    self.edit_panel(selection.strip())

########NEW FILE########
__FILENAME__ = hex_finder
'''
Hex Viewer
Licensed under MIT
Copyright (c) 2011 Isaac Muse <isaacmuse@gmail.com>
'''

import sublime
import sublime_plugin
from hex_common import *


class HexFinderCommand(sublime_plugin.WindowCommand):
    handshake = -1

    def go_to_address(self, address):
        #init
        view = self.window.active_view()

        if self.handshake != -1 and self.handshake == view.id():
            # Adress offset for line
            group_size = view.settings().get("hex_viewer_bits", None)
            bytes_wide = view.settings().get("hex_viewer_actual_bytes", None)
            if group_size == None and bytes_wide == None:
                return
            group_size = group_size / BITS_PER_BYTE

            # Go to address
            try:
                # Address wanted
                wanted = int(address, 16)
                # Calculate row
                row = int(wanted / (bytes_wide))
                # Byte offset into final row
                byte = wanted % (bytes_wide)
                #   Calculate byte number              Offset Char
                #
                #  wanted_char      byte
                # ------------ = -----------  => wanted_char + 11 = column
                #  total_chars   total_bytes
                #
                column = int((float(byte) / group_size) * ((group_size) * 2 + 1)) + ADDRESS_OFFSET

                # Go to address and focus
                pt = view.text_point(row, column)
                view.sel().clear()
                view.sel().add(pt)
                view.show_at_center(pt)
                # Highlight
                self.window.run_command('hex_highlighter')
            except:
                pass
        else:
            sublime.error_message("Hex view is no longer in focus! Find address canceled.")
        self.reset()

    def reset(self):
        self.handshake = -1

    def is_enabled(self):
        return is_enabled()

    def run(self):
         # Identify view
        view = self.window.active_view()
        if self.handshake != -1 and self.handshake == view.id():
            self.reset()
        self.handshake = view.id()

        self.window.show_input_panel(
            "Find: 0x",
            "",
            self.go_to_address,
            None,
            None
        )

########NEW FILE########
__FILENAME__ = hex_highlighter
'''
Hex Viewer
Licensed under MIT
Copyright (c) 2011 Isaac Muse <isaacmuse@gmail.com>
'''

import sublime
import sublime_plugin
from hex_common import *
from time import time, sleep
import thread

HIGHLIGHT_SCOPE = "string"
HIGHLIGHT_ICON = "dot"
HIGHLIGHT_STYLE = "solid"
MS_HIGHLIGHT_DELAY = 500
MAX_HIGHIGHT = 1000
THROTTLING = False


class Pref(object):
    @classmethod
    def load(cls):
        cls.wait_time = 0.12
        cls.time = time()
        cls.modified = False
        cls.ignore_all = False

Pref.load()


class HhThreadMgr(object):
    restart = False


class HexHighlighter(object):
    def init(self):
        init_status = False
        self.address_done = False
        self.total_bytes = 0
        self.address = []
        self.selected_bytes = []

        # Get Seetings from settings file
        group_size = self.view.settings().get("hex_viewer_bits", None)
        self.inspector_enabled = hv_inspector_enable
        self.throttle = hv_settings.get("highlight_throttle", THROTTLING)
        self.max_highlight = hv_settings.get("highlight_max_bytes", MAX_HIGHIGHT)
        self.bytes_wide = self.view.settings().get("hex_viewer_actual_bytes", None)
        self.highlight_scope = hv_settings.get("highlight_scope", HIGHLIGHT_SCOPE)
        self.highlight_icon = hv_settings.get("highlight_icon", HIGHLIGHT_ICON)
        style = hv_settings.get("highlight_style", HIGHLIGHT_STYLE)

        # No icon?
        if self.highlight_icon == "none":
            self.highlight_icon = ""

        # Process highlight style
        self.highlight_style = 0
        if style == "outline":
            self.highlight_style = sublime.DRAW_OUTLINED
        elif style == "none":
            self.highlight_style = sublime.HIDDEN
        elif style == "underline":
            self.highlight_style = sublime.DRAW_EMPTY_AS_OVERWRITE

        #Process hex grouping
        if group_size != None and self.bytes_wide != None:
            self.group_size = group_size / BITS_PER_BYTE
            self.hex_char_range = get_hex_char_range(self.group_size, self.bytes_wide)
            init_status = True
        return init_status

    def get_address(self, start, bytes, line):
        lines = line
        align_to_address_offset = 2
        add_start = lines * self.bytes_wide + start - align_to_address_offset
        add_end = add_start + bytes - 1
        length = len(self.address)
        if length == 0:
            # Add first address group
            multi_byte = -1 if add_start == add_end else add_end
            self.address.append(add_start)
            self.address.append(multi_byte)
        elif (
            (self.address[1] == -1 and self.address[0] + 1 == add_start) or
            (self.address[1] != -1 and self.address[1] + 1 == add_start)
        ):
            # Update end address
            self.address[1] = add_end
        else:
            # Stop getting adresses if bytes are not consecutive
            self.address_done = True

    def display_address(self):
        count = ''
        if self.total_bytes == 0 or len(self.address) != 2:
            self.view.set_status('hex_address', "Address: None")
            return
        # Display number of bytes whose address is not displayed
        if self.address_done:
            delta = 1 if self.address[1] == -1 else self.address[1] - self.address[0] + 1
            if self.total_bytes == "?":
                count = " [+?]"
            else:
                counted_bytes = self.total_bytes - delta
                if counted_bytes > 0:
                    count = " [+" + str(counted_bytes) + " bytes]"
        # Display adresses
        status = "Address: "
        if self.address[1] == -1:
            status += ("0x%08x" % self.address[0]) + count
        else:
            status += ("0x%08x" % self.address[0]) + "-" + ("0x%08x" % self.address[1]) + count
        self.view.set_status('hex_address', status)

    def display_total_bytes(self):
        # Display total hex bytes
        total = self.total_bytes if self.total_bytes == "?" else str(self.total_bytes)
        self.view.set_status('hex_total_bytes', "Total Bytes: " + total)

    def hex_selection(self, start, bytes, first_pos):
        row, column = self.view.rowcol(first_pos)
        column = ascii_to_hex_col(start, self.group_size)
        hex_pos = self.view.text_point(row, column)

        # Log first byte
        if self.first_all == -1:
            self.first_all = hex_pos

         # Traverse row finding the specified bytes
        highlight_start = -1
        byte_count = bytes
        while byte_count:
            # Byte rising edge
            if self.view.score_selector(hex_pos, 'raw.nibble.upper'):
                if highlight_start == -1:
                    highlight_start = hex_pos
                hex_pos += 2
                byte_count -= 1
                # End of selection
                if byte_count == 0:
                    self.selected_bytes.append(sublime.Region(highlight_start, hex_pos))
            else:
                # Byte group falling edge
                self.selected_bytes.append(sublime.Region(highlight_start, hex_pos))
                hex_pos += 1
                highlight_start = -1
        # Log address
        if bytes and not self.address_done:
            self.get_address(start + 2, bytes, row)

    def ascii_to_hex(self, sel):
        view = self.view
        start = sel.begin()
        end = sel.end()
        bytes = 0
        ascii_range = view.extract_scope(sel.begin())

        # Determine if selection is within ascii range
        if (
                start >= ascii_range.begin() and
                (
                    # Single selection should ignore the end of line selection
                    (end == start and end < ascii_range.end() - 1) or
                    (end != start and end < ascii_range.end())
                )
            ):
            # Single char selection
            if sel.size() == 0:
                bytes = 1
                self.selected_bytes.append(sublime.Region(start, end + 1))
            else:
                # Multi char selection
                bytes = end - start
                self.selected_bytes.append(sublime.Region(start, end))
            self.total_bytes += bytes
            # Highlight hex values
            self.hex_selection(start - ascii_range.begin(), bytes, start)

    def hex_to_ascii(self, sel):
        view = self.view
        start = sel.begin()
        end = sel.end()

        # Get range of hex data
        line = view.line(start)
        range_start = line.begin() + ADDRESS_OFFSET
        range_end = range_start + self.hex_char_range
        hex_range = sublime.Region(range_start, range_end)

        # Determine if selection is within hex range
        if start >= hex_range.begin() and end <= hex_range.end():
            # Adjust beginning of selection to begining of first selected byte
            start, end, bytes = adjust_hex_sel(view, start, end, self.group_size)

            # Highlight hex values and their ascii chars
            if bytes != 0:
                self.total_bytes += bytes
                # Zero based byte number
                start_byte = get_byte_count(hex_range.begin(), start + 2, self.group_size) - 1
                self.hex_selection(start_byte, bytes, start)

                # Highlight Ascii
                ascii_start = hex_range.end() + ASCII_OFFSET + start_byte
                ascii_end = ascii_start + bytes
                self.selected_bytes.append(sublime.Region(ascii_start, ascii_end))

    def get_highlights(self):
        self.first_all = -1
        for sel in self.view.sel():
            # Kick out if total bytes exceeds limit
            if self.throttle and self.total_bytes >= self.max_highlight:
                if len(self.address) == 2:
                    self.address[1] = -1
                self.total_bytes = "?"
                return

            if self.view.score_selector(sel.begin(), 'comment'):
                self.ascii_to_hex(sel)
            else:
                self.hex_to_ascii(sel)

    def run(self, window):
        if window == None:
            return
        self.window = window
        view = self.window.active_view()
        self.view = view

        if not self.init():
            return

        self.get_highlights()

        # Show inspector panel
        if self.inspector_enabled:
            reset = False if self.total_bytes == 1 else True
            self.window.run_command(
                'hex_inspector',
                {'first_byte': self.first_all, 'reset': reset, 'bytes_wide': self.bytes_wide}
            )

        # Highlight selected regions
        if self.highlight_style == sublime.DRAW_EMPTY_AS_OVERWRITE:
            self.selected_bytes = underline(self.selected_bytes)
        view.add_regions(
            "hex_view",
            self.selected_bytes,
            self.highlight_scope,
            self.highlight_icon,
            self.highlight_style
        )
        # Display selected byte addresses and total bytes selected
        self.display_address()
        self.display_total_bytes()

hh_highlight = HexHighlighter().run


class HexHighlighterCommand(sublime_plugin.WindowCommand):
    def run(self):
        if Pref.ignore_all:
            return
        Pref.modified = True

    def is_enabled(self):
        return is_enabled()


class HexHighlighterListenerCommand(sublime_plugin.EventListener):
    def on_selection_modified(self, view):
        if not is_enabled(view) or Pref.ignore_all:
            return
        now = time()
        if now - Pref.time > Pref.wait_time:
            sublime.set_timeout(lambda: hh_run(), 0)
        else:
            Pref.modified = True
            Pref.time = now


# Kick off hex highlighting
def hh_run():
    Pref.modified = False
    # Ignore selection and edit events inside the routine
    Pref.ignore_all = True
    hh_highlight(sublime.active_window())
    Pref.ignore_all = False
    Pref.time = time()


# Start thread that will ensure highlighting happens after a barage of events
# Initial highlight is instant, but subsequent events in close succession will
# be ignored and then accounted for with one match by this thread
def hh_loop():
    while not HhThreadMgr.restart:
        if Pref.modified == True and time() - Pref.time > Pref.wait_time:
            sublime.set_timeout(lambda: hh_run(), 0)
        sleep(0.5)

    if HhThreadMgr.restart:
        HhThreadMgr.restart = False
        sublime.set_timeout(lambda: thread.start_new_thread(hh_loop, ()), 0)

if not 'running_hh_loop' in globals():
    running_hh_loop = True
    thread.start_new_thread(hh_loop, ())
else:
    HhThreadMgr.restart = True

########NEW FILE########
__FILENAME__ = hex_inspector
'''
Hex Viewer
Licensed under MIT
Copyright (c) 2011 Isaac Muse <isaacmuse@gmail.com>
'''

import sublime
import sublime_plugin
import math
from struct import unpack
from hex_common import *

hv_endianness = hv_settings.get("inspector_endian", "little")


class HexShowInspectorCommand(sublime_plugin.WindowCommand):
    def is_enabled(self):
        return is_enabled() and hv_inspector_enable

    def run(self):
        # Setup inspector window
        view = self.window.get_output_panel('hex_viewer_inspector')
        view.set_syntax_file("Packages/HexViewer/HexInspect.hidden-tmLanguage")
        view.settings().set("draw_white_space", "none")
        view.settings().set("draw_indent_guides", False)
        view.settings().set("gutter", False)
        view.settings().set("line_numbers", False)
        # Show
        self.window.run_command("show_panel", {"panel": "output.hex_viewer_inspector"})
        self.window.run_command("hex_inspector", {"reset": True})


class HexHideInspectorCommand(sublime_plugin.WindowCommand):
    def is_enabled(self):
        return is_enabled() and hv_inspector_enable

    def run(self):
        self.window.run_command("hide_panel", {"panel": "output.hex_viewer_inspector"})


class HexToggleInspectorEndiannessCommand(sublime_plugin.WindowCommand):
    def is_enabled(self):
        return is_enabled() and hv_inspector_enable

    def run(self):
        global hv_endianness
        hv_endianness = "big" if hv_endianness == "little" else "little"
        self.window.run_command('hex_highlighter')


class HexInspectorCommand(sublime_plugin.WindowCommand):
    def get_bytes(self, start, bytes_wide):
        bytes = self.view.substr(sublime.Region(start, start + 2))
        byte64 = None
        byte32 = None
        byte16 = None
        byte8 = None
        start += 2
        size = self.view.size()
        count = 1
        group_divide = 1
        address = 12
        ascii_divide = group_divide + bytes_wide + address + 1
        target_bytes = 8

        # Look for 64 bit worth of bytes
        while start < size and count < target_bytes:
            # Check if sitting on first nibble
            if self.view.score_selector(start, 'raw.nibble.upper'):
                bytes += self.view.substr(sublime.Region(start, start + 2))
                count += 1
                start += 2
            else:
                # Must be at byte group falling edge; try and step over divider
                start += group_divide
                if start < size and self.view.score_selector(start, 'raw.nibble.upper'):
                    bytes += self.view.substr(sublime.Region(start, start + 2))
                    count += 1
                    start += 2
                # Must be at line end; try and step to next line
                else:
                    start += ascii_divide
                    if start < size and self.view.score_selector(start, 'raw.nibble.upper'):
                        bytes += self.view.substr(sublime.Region(start, start + 2))
                        count += 1
                        start += 2
                    else:
                        # No more bytes to check
                        break

        byte8 = bytes[0:2]
        if count > 1:
            byte16 = bytes[0:4]
        if count > 3:
            byte32 = bytes[0:8]
        if count > 7:
            byte64 = bytes[0:16]
        return byte8, byte16, byte32, byte64

    def display(self, view, byte8, bytes16, bytes32, bytes64):
        item_dec = hv_settings.get("inspector_integer_format", "%-12s:  %-14d")
        item_str = hv_settings.get("inspector_missing/bad_format", "%-12s:  %-14s")
        item_float = hv_settings.get("insepctor_float_format", "%-12s:  %-14e")
        item_double = hv_settings.get("inspector_double_format", "%-12s:  %-14e")
        item_bin = hv_settings.get("inspector_binary_format", "%-12s:  %-14s")
        nl = "\n"
        endian = ">" if self.endian == "big" else "<"
        i_buffer = "%28s:%-28s" % ("Hex Inspector ", (" Big Endian" if self.endian == "big" else " Little Endian")) + nl
        if byte8 != None:
            i_buffer += item_dec * 2 % (
                "byte", unpack(endian + "B", byte8.decode("hex"))[0],
                "short", unpack(endian + "b", byte8.decode("hex"))[0]
            ) + nl
        else:
            i_buffer += item_str * 2 % (
                "byte", "--",
                "short", "--"
            ) + nl
        if bytes16 != None:
            i_buffer += item_dec * 2 % (
                "word", unpack(endian + "H", bytes16.decode("hex"))[0],
                "int", unpack(endian + "h", bytes16.decode("hex"))[0]
            ) + nl
        else:
            i_buffer += item_str * 2 % (
                "word", "--",
                "int", "--"
            ) + nl
        if bytes32 != None:
            i_buffer += item_dec * 2 % (
                "dword", unpack(endian + "I", bytes32.decode("hex"))[0],
                "longint", unpack(endian + "i", bytes32.decode("hex"))[0]
            ) + nl
        else:
            i_buffer += item_str * 2 % (
                "dword", "--",
                "longint", "--"
            ) + nl
        if bytes32 != None:
            s_float = unpack(endian + "f", bytes32.decode('hex'))[0]
            if math.isnan(s_float):
                i_buffer += item_str % ("float", "NaN")
            else:
                i_buffer += item_float % (
                    "float", s_float
                )
        else:
            i_buffer += item_str % ("float", "--")
        if bytes64 != None:
            d_float = unpack(endian + "d", bytes64.decode('hex'))[0]
            if math.isnan(d_float):
                i_buffer += item_str % ("double", "NaN") + nl
            else:
                i_buffer += item_double % (
                    "double", d_float
                ) + nl
        else:
            i_buffer += item_str % ("double", "--") + nl
        if byte8 != None:
            i_buffer += item_bin % ("binary", '{0:08b}'.format(unpack(endian + "B", byte8.decode("hex"))[0])) + nl
        else:
            i_buffer += item_str % ("binary", "--") + nl

        # Update content
        view.set_read_only(False)
        edit = view.begin_edit()
        view.replace(edit, sublime.Region(0, view.size()), i_buffer)
        view.end_edit(edit)
        view.set_read_only(True)
        view.sel().clear()

    def is_enabled(self):
        return is_enabled()

    def run(self, first_byte=None, bytes_wide=None, reset=False):
        self.view = self.window.active_view()
        self.endian = hv_endianness
        byte8, bytes16, bytes32, bytes64 = None, None, None, None
        if not reset and first_byte != None and bytes_wide != None:
            byte8, bytes16, bytes32, bytes64 = self.get_bytes(int(first_byte), int(bytes_wide))
        self.display(self.window.get_output_panel('hex_viewer_inspector'), byte8, bytes16, bytes32, bytes64)

########NEW FILE########
__FILENAME__ = hex_viewer
'''
Hex Viewer
Licensed under MIT
Copyright (c) 2011 Isaac Muse <isaacmuse@gmail.com>
'''

import sublime
import sublime_plugin
import struct
import threading
from os.path import basename
from os.path import getsize as get_file_size
from hex_common import *
from fnmatch import fnmatch

DEFAULT_BIT_GROUP = 16
DEFAULT_BYTES_WIDE = 24
VALID_BITS = [8, 16, 32, 64, 128]
VALID_BYTES = [8, 10, 16, 24, 32, 48, 64, 128, 256, 512]
AUTO_OPEN = False


class ReadBin(threading.Thread):
    def __init__(self, file_name, bytes_wide, group_size):
        self.bytes_wide = bytes_wide
        self.group_size = group_size
        self.file_name = file_name
        self.file_size = get_file_size(file_name)
        self.read_count = 0
        self.abort = False
        self.buffer = False
        threading.Thread.__init__(self)

    def iterfile(self, maxblocksize=4096):
        with open(self.file_name, "rb") as bin:
            # Ensure read block is a multiple of groupsize
            bytes_wide = self.bytes_wide
            blocksize = maxblocksize - (maxblocksize % bytes_wide)

            start = 0
            bytes = bin.read(blocksize)
            while bytes:
                outbytes = bytes[start:start + bytes_wide]
                while outbytes:
                    yield outbytes
                    start += bytes_wide
                    outbytes = bytes[start:start + bytes_wide]
                start = 0
                bytes = bin.read(blocksize)

    def run(self):
        translate_table = ("." * 32) + "".join(chr(c) for c in xrange(32, 127)) + ("." * 129)
        def_struct = struct.Struct("=" + ("B" * self.bytes_wide))
        def_template = (("%02x" * self.group_size) + " ") * (self.bytes_wide / self.group_size)

        line = 0
        b_buffer = []
        read_count = 0
        for bytes in self.iterfile():
            if self.abort:
                return
            l_buffer = []

            read_count += self.bytes_wide
            self.read_count = read_count if read_count < self.file_size else self.file_size

            # Add line number
            l_buffer.append("%08x:  " % (line * self.bytes_wide))

            try:
                # Complete line
                # Convert to decimal value
                values = def_struct.unpack(bytes)

                # Add hex value
                l_buffer.append(def_template % values)
            except struct.error:
                # Incomplete line
                # Convert to decimal value
                values = struct.unpack("=" + ("B" * len(bytes)), bytes)

                # Add hex value
                remain_group = len(bytes) / self.group_size
                remain_extra = len(bytes) % self.group_size
                l_buffer.append(((("%02x" * self.group_size) + " ") * (remain_group) + ("%02x" * remain_extra)) % values)

                # Append printable chars to incomplete line
                delta = self.bytes_wide - len(bytes)
                group_space = delta / self.group_size
                extra_space = (1 if delta % self.group_size else 0)

                l_buffer.append(" " * (group_space + extra_space + delta * 2))

            # Append printable chars
            l_buffer.append(" :" + bytes.translate(translate_table))

            # Add line to buffer
            b_buffer.append("".join(l_buffer))

            line += 1

        # Join buffer lines
        self.buffer = "\n".join(b_buffer)


class HexViewerListenerCommand(sublime_plugin.EventListener):
    open_me = None

    def is_bin_file(self, file_path):
        match = False
        patterns = hv_settings.get("auto_open_patterns", [])
        for pattern in patterns:
            match |= fnmatch(file_path, pattern)
            if match:
                break
        return match

    def open_bin_file(self, view=None, window=None):
        open_now = False
        if view != None and window != None:
            # Direct open file
            open_now = True
        else:
            # Preview view of file
            window = sublime.active_window()
            if window != None:
                view = window.active_view()
        # Open bin file in hex viewer
        if window and view and (open_now or view.file_name() == self.open_me):
            is_preview = window and view.file_name() not in [file.file_name() for file in window.views()]
            if is_preview:
                return
            view.settings().set("hex_no_auto_open", True)
            window.run_command('hex_viewer')

    def auto_load(self, view, window, is_preview):
        file_name = view.file_name()
        # Make sure we have a file name and that we haven't already processed the view
        if file_name != None and not view.settings().get("hex_no_auto_open", False):
            # Make sure the file is specified in our binary file list
            if self.is_bin_file(file_name):
                # Handle previw or direct open
                if is_preview:
                    self.open_me = file_name
                    sublime.set_timeout(lambda: self.open_bin_file(), 100)
                else:
                    self.open_me = file_name
                    self.open_bin_file(view, window)

    def on_activated(self, view):
        # Logic for preview windows
        if hv_settings.get("auto_open", AUTO_OPEN) and not view.settings().get('is_widget'):
            window = view.window()
            is_preview = window and view.file_name() not in [file.file_name() for file in window.views()]
            if view.settings().get("hex_view_postpone_hexview", True) and not view.is_loading():
                self.auto_load(view, window, is_preview)

    def on_load(self, view):
        # Logic for direct open files
        if hv_settings.get("auto_open", AUTO_OPEN) and not view.settings().get('is_widget'):
            window = view.window()
            is_preview = window and view.file_name() not in [file.file_name() for file in window.views()]
            if window and not is_preview and view.settings().get("hex_view_postpone_hexview", True):
                self.auto_load(view, window, is_preview)

    def on_pre_save(self, view):
        # We are saving the file so it will now reference itself
        # Instead of the original binary file, so reset settings.
        # Hex output will no longer be able to toggle back
        # To original file, so open original file along side
        # Newly saved hex output
        if view.settings().has("hex_viewer_file_name"):
            view.window().open_file(view.settings().get("hex_viewer_file_name"))
            view.set_scratch(False)
            view.set_read_only(False)
            view.settings().erase("hex_viewer_bits")
            view.settings().erase("hex_viewer_bytes")
            view.settings().erase("hex_viewer_actual_bytes")
            view.settings().erase("hex_viewer_file_name")


class HexViewerCommand(sublime_plugin.WindowCommand):
    handshake = -1
    file_name = ""
    thread = None

    def set_format(self):
        self.group_size = DEFAULT_BIT_GROUP / BITS_PER_BYTE
        self.bytes_wide = DEFAULT_BYTES_WIDE

        # Set grouping
        if self.bits in VALID_BITS:
            self.group_size = self.bits / BITS_PER_BYTE

        # Set bytes per line
        if self.bytes in hv_settings.get("valid_bytes_per_line", VALID_BYTES):
            self.bytes_wide = self.bytes

        # Check if grouping and bytes per line do not align
        # Round to nearest bytes
        offset = self.bytes_wide % self.group_size
        if offset == self.bytes_wide:
            self.bytes_wide = self.bits / BITS_PER_BYTE
        elif offset != 0:
            self.bytes_wide -= offset

    def buffer_init(self, bits, bytes):
        self.view = self.window.active_view()
        file_name = None
        if self.view != None:
            # Get font settings
            self.font = hv_settings.get('custom_font', 'None')
            self.font_size = hv_settings.get('custom_font_size', 0)

            #Get file name
            file_name = self.view.settings().get("hex_viewer_file_name", self.view.file_name())

            # Get current bit and byte settings from view
            # Or try and get them from settings file
            # If none are found, use default
            current_bits = self.view.settings().get(
                'hex_viewer_bits',
                hv_settings.get('group_bytes_by_bits', DEFAULT_BIT_GROUP)
            )
            current_bytes = self.view.settings().get(
                'hex_viewer_bytes',
                hv_settings.get('bytes_per_line', DEFAULT_BYTES_WIDE)
            )
            # Use passed in bit and byte settings if available
            self.bits = bits if bits != None else int(current_bits)
            self.bytes = int(bytes) if bytes != None else int(current_bytes)
            self.set_format()
        return file_name

    def read_bin(self, file_name):
        self.abort = False
        self.current_view = self.view
        self.thread = ReadBin(file_name, self.bytes_wide, self.group_size)
        self.thread.start()
        self.handle_thread()

    def load_hex_view(self):
        file_name = self.thread.file_name
        b_buffer = self.thread.buffer
        self.thread = None

        # Show binary data
        view = self.window.new_file()
        view.set_name(basename(file_name) + ".hex")
        self.window.focus_view(self.view)
        if self.window.active_view().id() == self.view.id():
            self.window.run_command("close_file")
        self.window.focus_view(view)

        # Set syntax
        view.set_syntax_file("Packages/HexViewer/Hex.tmLanguage")

        # Set font
        if self.font != 'none':
            view.settings().set('font_face', self.font)
        if self.font_size != 0:
            view.settings().set("font_size", self.font_size)

        # Save hex view settings
        view.settings().set("hex_viewer_bits", self.bits)
        view.settings().set("hex_viewer_bytes", self.bytes)
        view.settings().set("hex_viewer_actual_bytes", self.bytes_wide)
        view.settings().set("hex_viewer_file_name", file_name)
        view.settings().set("hex_no_auto_open", True)

        # Show hex content in view; make read only
        view.set_scratch(True)
        edit = view.begin_edit()
        view.sel().clear()
        view.replace(edit, sublime.Region(0, view.size()), b_buffer)
        view.end_edit(edit)
        view.set_read_only(True)

        # Offset past address to first byte
        view.sel().add(sublime.Region(ADDRESS_OFFSET, ADDRESS_OFFSET))
        if hv_settings.get("inspector", False) and hv_settings.get("inspector_auto_show", False):
            view.window().run_command("hex_show_inspector")

    def read_file(self, file_name):
        if hv_settings.get("inspector", False):
            self.window.run_command("hex_hide_inspector")
        view = self.window.open_file(file_name)
        view.settings().set("hex_no_auto_open", True)
        self.window.focus_view(self.view)
        self.window.run_command("close_file")
        self.window.focus_view(view)

    def reset_thread(self):
        self.thread = None

    def handle_thread(self):
        if self.abort == True:
            self.thread.abort = True
            sublime.status_message("Hex View aborted!")
            sublime.set_timeout(lambda: self.reset_thread(), 500)
            return
        ratio = float(self.thread.read_count) / float(self.thread.file_size)
        percent = int(ratio * 10)
        leftover = 10 - percent
        message = "[" + "-" * percent + ">" + "-" * leftover + ("] %3d%%" % int(ratio * 100)) + " converted to hex"
        sublime.status_message(message)
        if not self.thread.is_alive():
            sublime.set_timeout(lambda: self.load_hex_view(), 100)
        else:
            sublime.set_timeout(lambda: self.handle_thread(), 100)

    def abort_hex_load(self):
        self.abort = True

    def discard_changes(self, value):
        if value.strip().lower() == "yes":
            if self.switch_type == "hex":
                view = sublime.active_window().active_view()
                if self.handshake == view.id():
                    view.set_scratch(True)
                    self.read_bin(self.file_name)
                else:
                    sublime.error_message("Target view is no longer in focus!  Hex view aborted.")
            else:
                self.read_file(self.file_name)
        self.reset()

    def discard_panel(self):
        self.window.show_input_panel(
            "Discard Changes? (yes | no):",
            "no",
            self.discard_changes,
            None,
            self.reset
        )

    def reset(self):
        self.handshake = -1
        self.file_name = ""
        self.type = None

    def run(self, bits=None, bytes=None):
        # If thread is active cancel thread
        if self.thread != None and self.thread.is_alive():
            self.abort_hex_load()
            return

        # Init Buffer
        file_name = self.buffer_init(bits, bytes)

        # Identify view
        if self.handshake != -1 and self.handshake == self.view.id():
            self.reset()
        self.handshake = self.view.id()

        if file_name != None:
            # Decide whether to read in as a binary file or a traditional file
            if self.view.settings().has("hex_viewer_file_name"):
                self.view_type = "hex"
                if is_hex_dirty(self.view):
                    self.file_name = file_name
                    if bits == None and bytes == None:
                        self.switch_type = "file"
                    else:
                        self.switch_type = "hex"
                    self.discard_panel()
                else:
                    if bits == None and bytes == None:
                        # Switch back to traditional output
                        self.read_file(file_name)
                    else:
                        # Reload hex with new settings
                        self.read_bin(file_name)
            else:
                # We are going to swap out the current file for hex output
                # So as not to clutter the screen.  Changes need to be saved
                # Or they will be lost
                if self.view.is_dirty():
                    self.file_name = file_name
                    self.switch_type = "hex"
                    self.discard_panel()
                else:
                    # Switch to hex output
                    self.read_bin(file_name)


class HexViewerOptionsCommand(sublime_plugin.WindowCommand):
    def set_bits(self, value):
        if value != -1:
            self.window.run_command('hex_viewer', {"bits": VALID_BITS[value]})

    def set_bytes(self, value):
        if value != -1:
            self.window.run_command('hex_viewer', {"bytes": self.valid_bytes[value]})

    def is_enabled(self):
        return is_enabled()

    def run(self, option):
        self.view = self.window.active_view()
        file_name = self.view.settings().get("hex_viewer_file_name", self.view.file_name())
        self.valid_bytes = hv_settings.get("valid_bytes_per_line", VALID_BYTES)
        if file_name != None:
            if self.view.settings().has("hex_viewer_file_name"):
                option_list = []
                if option == "bits":
                    for bits in VALID_BITS:
                        option_list.append(str(bits) + " bits")
                    self.window.show_quick_panel(option_list, self.set_bits)
                elif option == "bytes":
                    for bytes in self.valid_bytes:
                        option_list.append(str(bytes) + " bytes")
                    self.window.show_quick_panel(option_list, self.set_bytes)

########NEW FILE########
__FILENAME__ = hex_writer
'''
Hex Viewer
Licensed under MIT
Copyright (c) 2011 Isaac Muse <isaacmuse@gmail.com>
'''

import sublime
import sublime_plugin
from os.path import dirname, exists
import re
from hex_common import *
from hex_checksum import checksum

USE_CHECKSUM_ON_SAVE = True


class HexWriterCommand(sublime_plugin.WindowCommand):
    export_path = ""
    handshake = -1

    def is_enabled(self):
        return is_enabled()

    def export_panel(self):
        self.window.show_input_panel(
            "Export To:",
            self.export_path,
            self.prepare_export,
            None,
            self.reset
        )

    def overwrite(self, value):
        if value.strip().lower() == "yes":
            self.export()
        else:
            self.export_path = self.view.settings().get("hex_viewer_file_name")
            self.export_panel()

    def prepare_export(self, file_path):
        self.export_path = file_path
        if exists(dirname(file_path)):
            if exists(file_path):
                self.window.show_input_panel(
                    "Overwrite File? (yes | no):",
                    "no",
                    self.overwrite,
                    None,
                    self.reset
                )
            else:
                self.export()
        else:
            sublime.error_message("Directory does not exist!")
            self.export_path = self.view.settings().get("hex_viewer_file_name")
            self.export_panel()

    def export(self):
        self.view = self.window.active_view()
        if self.handshake != -1 and self.handshake == self.view.id():
            hex_hash = None
            # Get checksum if required
            if hv_settings.get("checksum_on_save", USE_CHECKSUM_ON_SAVE):
                hex_hash = checksum()
            try:
                with open(self.export_path, "wb") as bin:
                    r_buffer = self.view.split_by_newlines(sublime.Region(0, self.view.size()))
                    h_buffer = []
                    for line in r_buffer:
                        hex_data = re.sub(r'[\da-z]{8}:[\s]{2}((?:[\da-z]+[\s]{1})*)\s*\:[\w\W]*', r'\1', self.view.substr(line)).replace(" ", "").decode("hex")
                        bin.write(hex_data)
                        if hex_hash != None:
                            h_buffer.append(hex_data)
                if hex_hash != None:
                    # Checksum will be threaded and will show the result when done
                    sublime.set_timeout(lambda: sublime.status_message("Checksumming..."), 0)
                    hex_hash.threaded_update(h_buffer)
            except:
                sublime.error_message("Failed to export to " + self.export_path)
                self.reset()
                return
            # Update the tab name
            self.view.set_name(basename(self.export_path) + ".hex")
            # Update the internal path
            self.view.settings().set("hex_viewer_file_name", self.export_path)
            # Clear the marked edits
            clear_edits(self.view)
            # Reset class
            self.reset()

        else:
            sublime.error_message("Hex view is no longer in focus! File not saved.")
            self.reset()

    def reset(self):
        self.export_path = ""
        self.handshake = -1

    def run(self):
        self.view = self.window.active_view()

        # Identify view
        if self.handshake != -1 and self.handshake == self.view.id():
            self.reset()
        self.handshake = self.view.id()

        self.export_path = self.view.settings().get("hex_viewer_file_name")

        self.export_panel()

########NEW FILE########
__FILENAME__ = sum_hashes
"""
Hex Viewer
Licensed under MIT
Copyright (c) 2013 Isaac Muse <isaacmuse@gmail.com>
"""

BIT8_MOD = 256
BIT16_MOD = 65536
BIT24_MOD = 16777216
BIT32_MOD = 4294967296


class sum8(object):
    __name = "sum8"
    __digest_size = 1

    def __init__(self, arg=""):
        self.sum = 0
        self.update(arg)

    @property
    def name(self):
        return self.__name

    @property
    def digest_size(self):
        return self.__digest_size

    def update(self, arg):
        for b in arg:
            self.sum += ord(b)

    def digest(self):
        return self.sum % BIT8_MOD

    def hexdigest(self):
        return "%02x" % self.digest()

    def copy(self):
        import copy
        return copy.deepcopy(self)


class sum16(sum8):
    __name = "sum16"
    __digest_size = 2

    def digest(self):
        return self.sum % BIT16_MOD

    def hexdigest(self):
        return "%04x" % self.digest()


class sum24(sum8):
    __name = "sum24"
    __digest_size = 3

    def digest(self):
        return self.sum % BIT24_MOD

    def hexdigest(self):
        return "%06x" % self.digest()


class sum32(sum8):
    __name = "sum32"
    __digest_size = 4

    def digest(self):
        return self.sum % BIT32_MOD

    def hexdigest(self):
        return "%08x" % self.digest()


class xor8(sum8):
    __name = "xor8"
    __digest_size = 1

    def update(self, arg):
        for b in arg:
            self.sum ^= ord(b) & 0xFF

    def digest(self):
        return int(self.sum)

    def hexdigest(self):
        return "%02x" % self.digest()

########NEW FILE########
__FILENAME__ = tiger
'''
Copyright (c) 2011 Brian Browning, David Bern

Permission is hereby granted, free of charge, to any person obtaining a copy of this software and associated
documentation files (the "Software"), to deal in the Software without restriction, including without limitation the
rights to use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies of the Software, and to permit
persons to whom the Software is furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all copies or substantial portions of the
Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE
WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR
COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR
OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.
'''

import array
import struct

BIG_ENDIAN = True


class tiger(object):
    __name = 'tiger'
    __digest_size = 24

    def __init__(self, arg=""):
        self.tig = TigerStruct()
        self.update(arg)

    @property
    def name(self):
        return self.__name

    @property
    def digest_size(self):
        return self.__digest_size

    def update(self, arg):
        tiger_add(arg, self.tig)

    def digest(self):
        if BIG_ENDIAN:
            tiger_finalize(self.tig)
            big_endian = struct.unpack("<QQQ", struct.pack(">QQQ", self.tig.res[0], self.tig.res[1], self.tig.res[2]))
            return (
                ((big_endian[0] & 0xFFFFFFFFFFFFFFFF) << 32 * 4) |
                ((big_endian[1] & 0xFFFFFFFFFFFFFFFF) << 16 * 4) |
                ((big_endian[2] & 0xFFFFFFFFFFFFFFFF))
            )
        else:
            tiger_finalize(self.tig)
            return (
                ((self.tig.res[0] & 0xFFFFFFFFFFFFFFFF) << 32 * 4) |
                ((self.tig.res[1] & 0xFFFFFFFFFFFFFFFF) << 16 * 4) |
                ((self.tig.res[2] & 0xFFFFFFFFFFFFFFFF))
            )

    def hexdigest(self):
        return "%048x" % self.digest()

    def copy(self):
        import copy
        return copy.deepcopy(self)


t1 = [
    0x02AAB17CF7E90C5E, 0xAC424B03E243A8EC,
    0x72CD5BE30DD5FCD3, 0x6D019B93F6F97F3A,
    0xCD9978FFD21F9193, 0x7573A1C9708029E2,
    0xB164326B922A83C3, 0x46883EEE04915870,
    0xEAACE3057103ECE6, 0xC54169B808A3535C,
    0x4CE754918DDEC47C, 0x0AA2F4DFDC0DF40C,
    0x10B76F18A74DBEFA, 0xC6CCB6235AD1AB6A,
    0x13726121572FE2FF, 0x1A488C6F199D921E,
    0x4BC9F9F4DA0007CA, 0x26F5E6F6E85241C7,
    0x859079DBEA5947B6, 0x4F1885C5C99E8C92,
    0xD78E761EA96F864B, 0x8E36428C52B5C17D,
    0x69CF6827373063C1, 0xB607C93D9BB4C56E,
    0x7D820E760E76B5EA, 0x645C9CC6F07FDC42,
    0xBF38A078243342E0, 0x5F6B343C9D2E7D04,
    0xF2C28AEB600B0EC6, 0x6C0ED85F7254BCAC,
    0x71592281A4DB4FE5, 0x1967FA69CE0FED9F,
    0xFD5293F8B96545DB, 0xC879E9D7F2A7600B,
    0x860248920193194E, 0xA4F9533B2D9CC0B3,
    0x9053836C15957613, 0xDB6DCF8AFC357BF1,
    0x18BEEA7A7A370F57, 0x037117CA50B99066,
    0x6AB30A9774424A35, 0xF4E92F02E325249B,
    0x7739DB07061CCAE1, 0xD8F3B49CECA42A05,
    0xBD56BE3F51382F73, 0x45FAED5843B0BB28,
    0x1C813D5C11BF1F83, 0x8AF0E4B6D75FA169,
    0x33EE18A487AD9999, 0x3C26E8EAB1C94410,
    0xB510102BC0A822F9, 0x141EEF310CE6123B,
    0xFC65B90059DDB154, 0xE0158640C5E0E607,
    0x884E079826C3A3CF, 0x930D0D9523C535FD,
    0x35638D754E9A2B00, 0x4085FCCF40469DD5,
    0xC4B17AD28BE23A4C, 0xCAB2F0FC6A3E6A2E,
    0x2860971A6B943FCD, 0x3DDE6EE212E30446,
    0x6222F32AE01765AE, 0x5D550BB5478308FE,
    0xA9EFA98DA0EDA22A, 0xC351A71686C40DA7,
    0x1105586D9C867C84, 0xDCFFEE85FDA22853,
    0xCCFBD0262C5EEF76, 0xBAF294CB8990D201,
    0xE69464F52AFAD975, 0x94B013AFDF133E14,
    0x06A7D1A32823C958, 0x6F95FE5130F61119,
    0xD92AB34E462C06C0, 0xED7BDE33887C71D2,
    0x79746D6E6518393E, 0x5BA419385D713329,
    0x7C1BA6B948A97564, 0x31987C197BFDAC67,
    0xDE6C23C44B053D02, 0x581C49FED002D64D,
    0xDD474D6338261571, 0xAA4546C3E473D062,
    0x928FCE349455F860, 0x48161BBACAAB94D9,
    0x63912430770E6F68, 0x6EC8A5E602C6641C,
    0x87282515337DDD2B, 0x2CDA6B42034B701B,
    0xB03D37C181CB096D, 0xE108438266C71C6F,
    0x2B3180C7EB51B255, 0xDF92B82F96C08BBC,
    0x5C68C8C0A632F3BA, 0x5504CC861C3D0556,
    0xABBFA4E55FB26B8F, 0x41848B0AB3BACEB4,
    0xB334A273AA445D32, 0xBCA696F0A85AD881,
    0x24F6EC65B528D56C, 0x0CE1512E90F4524A,
    0x4E9DD79D5506D35A, 0x258905FAC6CE9779,
    0x2019295B3E109B33, 0xF8A9478B73A054CC,
    0x2924F2F934417EB0, 0x3993357D536D1BC4,
    0x38A81AC21DB6FF8B, 0x47C4FBF17D6016BF,
    0x1E0FAADD7667E3F5, 0x7ABCFF62938BEB96,
    0xA78DAD948FC179C9, 0x8F1F98B72911E50D,
    0x61E48EAE27121A91, 0x4D62F7AD31859808,
    0xECEBA345EF5CEAEB, 0xF5CEB25EBC9684CE,
    0xF633E20CB7F76221, 0xA32CDF06AB8293E4,
    0x985A202CA5EE2CA4, 0xCF0B8447CC8A8FB1,
    0x9F765244979859A3, 0xA8D516B1A1240017,
    0x0BD7BA3EBB5DC726, 0xE54BCA55B86ADB39,
    0x1D7A3AFD6C478063, 0x519EC608E7669EDD,
    0x0E5715A2D149AA23, 0x177D4571848FF194,
    0xEEB55F3241014C22, 0x0F5E5CA13A6E2EC2,
    0x8029927B75F5C361, 0xAD139FABC3D6E436,
    0x0D5DF1A94CCF402F, 0x3E8BD948BEA5DFC8,
    0xA5A0D357BD3FF77E, 0xA2D12E251F74F645,
    0x66FD9E525E81A082, 0x2E0C90CE7F687A49,
    0xC2E8BCBEBA973BC5, 0x000001BCE509745F,
    0x423777BBE6DAB3D6, 0xD1661C7EAEF06EB5,
    0xA1781F354DAACFD8, 0x2D11284A2B16AFFC,
    0xF1FC4F67FA891D1F, 0x73ECC25DCB920ADA,
    0xAE610C22C2A12651, 0x96E0A810D356B78A,
    0x5A9A381F2FE7870F, 0xD5AD62EDE94E5530,
    0xD225E5E8368D1427, 0x65977B70C7AF4631,
    0x99F889B2DE39D74F, 0x233F30BF54E1D143,
    0x9A9675D3D9A63C97, 0x5470554FF334F9A8,
    0x166ACB744A4F5688, 0x70C74CAAB2E4AEAD,
    0xF0D091646F294D12, 0x57B82A89684031D1,
    0xEFD95A5A61BE0B6B, 0x2FBD12E969F2F29A,
    0x9BD37013FEFF9FE8, 0x3F9B0404D6085A06,
    0x4940C1F3166CFE15, 0x09542C4DCDF3DEFB,
    0xB4C5218385CD5CE3, 0xC935B7DC4462A641,
    0x3417F8A68ED3B63F, 0xB80959295B215B40,
    0xF99CDAEF3B8C8572, 0x018C0614F8FCB95D,
    0x1B14ACCD1A3ACDF3, 0x84D471F200BB732D,
    0xC1A3110E95E8DA16, 0x430A7220BF1A82B8,
    0xB77E090D39DF210E, 0x5EF4BD9F3CD05E9D,
    0x9D4FF6DA7E57A444, 0xDA1D60E183D4A5F8,
    0xB287C38417998E47, 0xFE3EDC121BB31886,
    0xC7FE3CCC980CCBEF, 0xE46FB590189BFD03,
    0x3732FD469A4C57DC, 0x7EF700A07CF1AD65,
    0x59C64468A31D8859, 0x762FB0B4D45B61F6,
    0x155BAED099047718, 0x68755E4C3D50BAA6,
    0xE9214E7F22D8B4DF, 0x2ADDBF532EAC95F4,
    0x32AE3909B4BD0109, 0x834DF537B08E3450,
    0xFA209DA84220728D, 0x9E691D9B9EFE23F7,
    0x0446D288C4AE8D7F, 0x7B4CC524E169785B,
    0x21D87F0135CA1385, 0xCEBB400F137B8AA5,
    0x272E2B66580796BE, 0x3612264125C2B0DE,
    0x057702BDAD1EFBB2, 0xD4BABB8EACF84BE9,
    0x91583139641BC67B, 0x8BDC2DE08036E024,
    0x603C8156F49F68ED, 0xF7D236F7DBEF5111,
    0x9727C4598AD21E80, 0xA08A0896670A5FD7,
    0xCB4A8F4309EBA9CB, 0x81AF564B0F7036A1,
    0xC0B99AA778199ABD, 0x959F1EC83FC8E952,
    0x8C505077794A81B9, 0x3ACAAF8F056338F0,
    0x07B43F50627A6778, 0x4A44AB49F5ECCC77,
    0x3BC3D6E4B679EE98, 0x9CC0D4D1CF14108C,
    0x4406C00B206BC8A0, 0x82A18854C8D72D89,
    0x67E366B35C3C432C, 0xB923DD61102B37F2,
    0x56AB2779D884271D, 0xBE83E1B0FF1525AF,
    0xFB7C65D4217E49A9, 0x6BDBE0E76D48E7D4,
    0x08DF828745D9179E, 0x22EA6A9ADD53BD34,
    0xE36E141C5622200A, 0x7F805D1B8CB750EE,
    0xAFE5C7A59F58E837, 0xE27F996A4FB1C23C,
    0xD3867DFB0775F0D0, 0xD0E673DE6E88891A,
    0x123AEB9EAFB86C25, 0x30F1D5D5C145B895,
    0xBB434A2DEE7269E7, 0x78CB67ECF931FA38,
    0xF33B0372323BBF9C, 0x52D66336FB279C74,
    0x505F33AC0AFB4EAA, 0xE8A5CD99A2CCE187,
    0x534974801E2D30BB, 0x8D2D5711D5876D90,
    0x1F1A412891BC038E, 0xD6E2E71D82E56648,
    0x74036C3A497732B7, 0x89B67ED96361F5AB,
    0xFFED95D8F1EA02A2, 0xE72B3BD61464D43D,
    0xA6300F170BDC4820, 0xEBC18760ED78A77A
]

t2 = [
    0xE6A6BE5A05A12138, 0xB5A122A5B4F87C98,
    0x563C6089140B6990, 0x4C46CB2E391F5DD5,
    0xD932ADDBC9B79434, 0x08EA70E42015AFF5,
    0xD765A6673E478CF1, 0xC4FB757EAB278D99,
    0xDF11C6862D6E0692, 0xDDEB84F10D7F3B16,
    0x6F2EF604A665EA04, 0x4A8E0F0FF0E0DFB3,
    0xA5EDEEF83DBCBA51, 0xFC4F0A2A0EA4371E,
    0xE83E1DA85CB38429, 0xDC8FF882BA1B1CE2,
    0xCD45505E8353E80D, 0x18D19A00D4DB0717,
    0x34A0CFEDA5F38101, 0x0BE77E518887CAF2,
    0x1E341438B3C45136, 0xE05797F49089CCF9,
    0xFFD23F9DF2591D14, 0x543DDA228595C5CD,
    0x661F81FD99052A33, 0x8736E641DB0F7B76,
    0x15227725418E5307, 0xE25F7F46162EB2FA,
    0x48A8B2126C13D9FE, 0xAFDC541792E76EEA,
    0x03D912BFC6D1898F, 0x31B1AAFA1B83F51B,
    0xF1AC2796E42AB7D9, 0x40A3A7D7FCD2EBAC,
    0x1056136D0AFBBCC5, 0x7889E1DD9A6D0C85,
    0xD33525782A7974AA, 0xA7E25D09078AC09B,
    0xBD4138B3EAC6EDD0, 0x920ABFBE71EB9E70,
    0xA2A5D0F54FC2625C, 0xC054E36B0B1290A3,
    0xF6DD59FF62FE932B, 0x3537354511A8AC7D,
    0xCA845E9172FADCD4, 0x84F82B60329D20DC,
    0x79C62CE1CD672F18, 0x8B09A2ADD124642C,
    0xD0C1E96A19D9E726, 0x5A786A9B4BA9500C,
    0x0E020336634C43F3, 0xC17B474AEB66D822,
    0x6A731AE3EC9BAAC2, 0x8226667AE0840258,
    0x67D4567691CAECA5, 0x1D94155C4875ADB5,
    0x6D00FD985B813FDF, 0x51286EFCB774CD06,
    0x5E8834471FA744AF, 0xF72CA0AEE761AE2E,
    0xBE40E4CDAEE8E09A, 0xE9970BBB5118F665,
    0x726E4BEB33DF1964, 0x703B000729199762,
    0x4631D816F5EF30A7, 0xB880B5B51504A6BE,
    0x641793C37ED84B6C, 0x7B21ED77F6E97D96,
    0x776306312EF96B73, 0xAE528948E86FF3F4,
    0x53DBD7F286A3F8F8, 0x16CADCE74CFC1063,
    0x005C19BDFA52C6DD, 0x68868F5D64D46AD3,
    0x3A9D512CCF1E186A, 0x367E62C2385660AE,
    0xE359E7EA77DCB1D7, 0x526C0773749ABE6E,
    0x735AE5F9D09F734B, 0x493FC7CC8A558BA8,
    0xB0B9C1533041AB45, 0x321958BA470A59BD,
    0x852DB00B5F46C393, 0x91209B2BD336B0E5,
    0x6E604F7D659EF19F, 0xB99A8AE2782CCB24,
    0xCCF52AB6C814C4C7, 0x4727D9AFBE11727B,
    0x7E950D0C0121B34D, 0x756F435670AD471F,
    0xF5ADD442615A6849, 0x4E87E09980B9957A,
    0x2ACFA1DF50AEE355, 0xD898263AFD2FD556,
    0xC8F4924DD80C8FD6, 0xCF99CA3D754A173A,
    0xFE477BACAF91BF3C, 0xED5371F6D690C12D,
    0x831A5C285E687094, 0xC5D3C90A3708A0A4,
    0x0F7F903717D06580, 0x19F9BB13B8FDF27F,
    0xB1BD6F1B4D502843, 0x1C761BA38FFF4012,
    0x0D1530C4E2E21F3B, 0x8943CE69A7372C8A,
    0xE5184E11FEB5CE66, 0x618BDB80BD736621,
    0x7D29BAD68B574D0B, 0x81BB613E25E6FE5B,
    0x071C9C10BC07913F, 0xC7BEEB7909AC2D97,
    0xC3E58D353BC5D757, 0xEB017892F38F61E8,
    0xD4EFFB9C9B1CC21A, 0x99727D26F494F7AB,
    0xA3E063A2956B3E03, 0x9D4A8B9A4AA09C30,
    0x3F6AB7D500090FB4, 0x9CC0F2A057268AC0,
    0x3DEE9D2DEDBF42D1, 0x330F49C87960A972,
    0xC6B2720287421B41, 0x0AC59EC07C00369C,
    0xEF4EAC49CB353425, 0xF450244EEF0129D8,
    0x8ACC46E5CAF4DEB6, 0x2FFEAB63989263F7,
    0x8F7CB9FE5D7A4578, 0x5BD8F7644E634635,
    0x427A7315BF2DC900, 0x17D0C4AA2125261C,
    0x3992486C93518E50, 0xB4CBFEE0A2D7D4C3,
    0x7C75D6202C5DDD8D, 0xDBC295D8E35B6C61,
    0x60B369D302032B19, 0xCE42685FDCE44132,
    0x06F3DDB9DDF65610, 0x8EA4D21DB5E148F0,
    0x20B0FCE62FCD496F, 0x2C1B912358B0EE31,
    0xB28317B818F5A308, 0xA89C1E189CA6D2CF,
    0x0C6B18576AAADBC8, 0xB65DEAA91299FAE3,
    0xFB2B794B7F1027E7, 0x04E4317F443B5BEB,
    0x4B852D325939D0A6, 0xD5AE6BEEFB207FFC,
    0x309682B281C7D374, 0xBAE309A194C3B475,
    0x8CC3F97B13B49F05, 0x98A9422FF8293967,
    0x244B16B01076FF7C, 0xF8BF571C663D67EE,
    0x1F0D6758EEE30DA1, 0xC9B611D97ADEB9B7,
    0xB7AFD5887B6C57A2, 0x6290AE846B984FE1,
    0x94DF4CDEACC1A5FD, 0x058A5BD1C5483AFF,
    0x63166CC142BA3C37, 0x8DB8526EB2F76F40,
    0xE10880036F0D6D4E, 0x9E0523C9971D311D,
    0x45EC2824CC7CD691, 0x575B8359E62382C9,
    0xFA9E400DC4889995, 0xD1823ECB45721568,
    0xDAFD983B8206082F, 0xAA7D29082386A8CB,
    0x269FCD4403B87588, 0x1B91F5F728BDD1E0,
    0xE4669F39040201F6, 0x7A1D7C218CF04ADE,
    0x65623C29D79CE5CE, 0x2368449096C00BB1,
    0xAB9BF1879DA503BA, 0xBC23ECB1A458058E,
    0x9A58DF01BB401ECC, 0xA070E868A85F143D,
    0x4FF188307DF2239E, 0x14D565B41A641183,
    0xEE13337452701602, 0x950E3DCF3F285E09,
    0x59930254B9C80953, 0x3BF299408930DA6D,
    0xA955943F53691387, 0xA15EDECAA9CB8784,
    0x29142127352BE9A0, 0x76F0371FFF4E7AFB,
    0x0239F450274F2228, 0xBB073AF01D5E868B,
    0xBFC80571C10E96C1, 0xD267088568222E23,
    0x9671A3D48E80B5B0, 0x55B5D38AE193BB81,
    0x693AE2D0A18B04B8, 0x5C48B4ECADD5335F,
    0xFD743B194916A1CA, 0x2577018134BE98C4,
    0xE77987E83C54A4AD, 0x28E11014DA33E1B9,
    0x270CC59E226AA213, 0x71495F756D1A5F60,
    0x9BE853FB60AFEF77, 0xADC786A7F7443DBF,
    0x0904456173B29A82, 0x58BC7A66C232BD5E,
    0xF306558C673AC8B2, 0x41F639C6B6C9772A,
    0x216DEFE99FDA35DA, 0x11640CC71C7BE615,
    0x93C43694565C5527, 0xEA038E6246777839,
    0xF9ABF3CE5A3E2469, 0x741E768D0FD312D2,
    0x0144B883CED652C6, 0xC20B5A5BA33F8552,
    0x1AE69633C3435A9D, 0x97A28CA4088CFDEC,
    0x8824A43C1E96F420, 0x37612FA66EEEA746,
    0x6B4CB165F9CF0E5A, 0x43AA1C06A0ABFB4A,
    0x7F4DC26FF162796B, 0x6CBACC8E54ED9B0F,
    0xA6B7FFEFD2BB253E, 0x2E25BC95B0A29D4F,
    0x86D6A58BDEF1388C, 0xDED74AC576B6F054,
    0x8030BDBC2B45805D, 0x3C81AF70E94D9289,
    0x3EFF6DDA9E3100DB, 0xB38DC39FDFCC8847,
    0x123885528D17B87E, 0xF2DA0ED240B1B642,
    0x44CEFADCD54BF9A9, 0x1312200E433C7EE6,
    0x9FFCC84F3A78C748, 0xF0CD1F72248576BB,
    0xEC6974053638CFE4, 0x2BA7B67C0CEC4E4C,
    0xAC2F4DF3E5CE32ED, 0xCB33D14326EA4C11,
    0xA4E9044CC77E58BC, 0x5F513293D934FCEF,
    0x5DC9645506E55444, 0x50DE418F317DE40A,
    0x388CB31A69DDE259, 0x2DB4A83455820A86,
    0x9010A91E84711AE9, 0x4DF7F0B7B1498371,
    0xD62A2EABC0977179, 0x22FAC097AA8D5C0E
]

t3 = [
    0xF49FCC2FF1DAF39B, 0x487FD5C66FF29281,
    0xE8A30667FCDCA83F, 0x2C9B4BE3D2FCCE63,
    0xDA3FF74B93FBBBC2, 0x2FA165D2FE70BA66,
    0xA103E279970E93D4, 0xBECDEC77B0E45E71,
    0xCFB41E723985E497, 0xB70AAA025EF75017,
    0xD42309F03840B8E0, 0x8EFC1AD035898579,
    0x96C6920BE2B2ABC5, 0x66AF4163375A9172,
    0x2174ABDCCA7127FB, 0xB33CCEA64A72FF41,
    0xF04A4933083066A5, 0x8D970ACDD7289AF5,
    0x8F96E8E031C8C25E, 0xF3FEC02276875D47,
    0xEC7BF310056190DD, 0xF5ADB0AEBB0F1491,
    0x9B50F8850FD58892, 0x4975488358B74DE8,
    0xA3354FF691531C61, 0x0702BBE481D2C6EE,
    0x89FB24057DEDED98, 0xAC3075138596E902,
    0x1D2D3580172772ED, 0xEB738FC28E6BC30D,
    0x5854EF8F63044326, 0x9E5C52325ADD3BBE,
    0x90AA53CF325C4623, 0xC1D24D51349DD067,
    0x2051CFEEA69EA624, 0x13220F0A862E7E4F,
    0xCE39399404E04864, 0xD9C42CA47086FCB7,
    0x685AD2238A03E7CC, 0x066484B2AB2FF1DB,
    0xFE9D5D70EFBF79EC, 0x5B13B9DD9C481854,
    0x15F0D475ED1509AD, 0x0BEBCD060EC79851,
    0xD58C6791183AB7F8, 0xD1187C5052F3EEE4,
    0xC95D1192E54E82FF, 0x86EEA14CB9AC6CA2,
    0x3485BEB153677D5D, 0xDD191D781F8C492A,
    0xF60866BAA784EBF9, 0x518F643BA2D08C74,
    0x8852E956E1087C22, 0xA768CB8DC410AE8D,
    0x38047726BFEC8E1A, 0xA67738B4CD3B45AA,
    0xAD16691CEC0DDE19, 0xC6D4319380462E07,
    0xC5A5876D0BA61938, 0x16B9FA1FA58FD840,
    0x188AB1173CA74F18, 0xABDA2F98C99C021F,
    0x3E0580AB134AE816, 0x5F3B05B773645ABB,
    0x2501A2BE5575F2F6, 0x1B2F74004E7E8BA9,
    0x1CD7580371E8D953, 0x7F6ED89562764E30,
    0xB15926FF596F003D, 0x9F65293DA8C5D6B9,
    0x6ECEF04DD690F84C, 0x4782275FFF33AF88,
    0xE41433083F820801, 0xFD0DFE409A1AF9B5,
    0x4325A3342CDB396B, 0x8AE77E62B301B252,
    0xC36F9E9F6655615A, 0x85455A2D92D32C09,
    0xF2C7DEA949477485, 0x63CFB4C133A39EBA,
    0x83B040CC6EBC5462, 0x3B9454C8FDB326B0,
    0x56F56A9E87FFD78C, 0x2DC2940D99F42BC6,
    0x98F7DF096B096E2D, 0x19A6E01E3AD852BF,
    0x42A99CCBDBD4B40B, 0xA59998AF45E9C559,
    0x366295E807D93186, 0x6B48181BFAA1F773,
    0x1FEC57E2157A0A1D, 0x4667446AF6201AD5,
    0xE615EBCACFB0F075, 0xB8F31F4F68290778,
    0x22713ED6CE22D11E, 0x3057C1A72EC3C93B,
    0xCB46ACC37C3F1F2F, 0xDBB893FD02AAF50E,
    0x331FD92E600B9FCF, 0xA498F96148EA3AD6,
    0xA8D8426E8B6A83EA, 0xA089B274B7735CDC,
    0x87F6B3731E524A11, 0x118808E5CBC96749,
    0x9906E4C7B19BD394, 0xAFED7F7E9B24A20C,
    0x6509EADEEB3644A7, 0x6C1EF1D3E8EF0EDE,
    0xB9C97D43E9798FB4, 0xA2F2D784740C28A3,
    0x7B8496476197566F, 0x7A5BE3E6B65F069D,
    0xF96330ED78BE6F10, 0xEEE60DE77A076A15,
    0x2B4BEE4AA08B9BD0, 0x6A56A63EC7B8894E,
    0x02121359BA34FEF4, 0x4CBF99F8283703FC,
    0x398071350CAF30C8, 0xD0A77A89F017687A,
    0xF1C1A9EB9E423569, 0x8C7976282DEE8199,
    0x5D1737A5DD1F7ABD, 0x4F53433C09A9FA80,
    0xFA8B0C53DF7CA1D9, 0x3FD9DCBC886CCB77,
    0xC040917CA91B4720, 0x7DD00142F9D1DCDF,
    0x8476FC1D4F387B58, 0x23F8E7C5F3316503,
    0x032A2244E7E37339, 0x5C87A5D750F5A74B,
    0x082B4CC43698992E, 0xDF917BECB858F63C,
    0x3270B8FC5BF86DDA, 0x10AE72BB29B5DD76,
    0x576AC94E7700362B, 0x1AD112DAC61EFB8F,
    0x691BC30EC5FAA427, 0xFF246311CC327143,
    0x3142368E30E53206, 0x71380E31E02CA396,
    0x958D5C960AAD76F1, 0xF8D6F430C16DA536,
    0xC8FFD13F1BE7E1D2, 0x7578AE66004DDBE1,
    0x05833F01067BE646, 0xBB34B5AD3BFE586D,
    0x095F34C9A12B97F0, 0x247AB64525D60CA8,
    0xDCDBC6F3017477D1, 0x4A2E14D4DECAD24D,
    0xBDB5E6D9BE0A1EEB, 0x2A7E70F7794301AB,
    0xDEF42D8A270540FD, 0x01078EC0A34C22C1,
    0xE5DE511AF4C16387, 0x7EBB3A52BD9A330A,
    0x77697857AA7D6435, 0x004E831603AE4C32,
    0xE7A21020AD78E312, 0x9D41A70C6AB420F2,
    0x28E06C18EA1141E6, 0xD2B28CBD984F6B28,
    0x26B75F6C446E9D83, 0xBA47568C4D418D7F,
    0xD80BADBFE6183D8E, 0x0E206D7F5F166044,
    0xE258A43911CBCA3E, 0x723A1746B21DC0BC,
    0xC7CAA854F5D7CDD3, 0x7CAC32883D261D9C,
    0x7690C26423BA942C, 0x17E55524478042B8,
    0xE0BE477656A2389F, 0x4D289B5E67AB2DA0,
    0x44862B9C8FBBFD31, 0xB47CC8049D141365,
    0x822C1B362B91C793, 0x4EB14655FB13DFD8,
    0x1ECBBA0714E2A97B, 0x6143459D5CDE5F14,
    0x53A8FBF1D5F0AC89, 0x97EA04D81C5E5B00,
    0x622181A8D4FDB3F3, 0xE9BCD341572A1208,
    0x1411258643CCE58A, 0x9144C5FEA4C6E0A4,
    0x0D33D06565CF620F, 0x54A48D489F219CA1,
    0xC43E5EAC6D63C821, 0xA9728B3A72770DAF,
    0xD7934E7B20DF87EF, 0xE35503B61A3E86E5,
    0xCAE321FBC819D504, 0x129A50B3AC60BFA6,
    0xCD5E68EA7E9FB6C3, 0xB01C90199483B1C7,
    0x3DE93CD5C295376C, 0xAED52EDF2AB9AD13,
    0x2E60F512C0A07884, 0xBC3D86A3E36210C9,
    0x35269D9B163951CE, 0x0C7D6E2AD0CDB5FA,
    0x59E86297D87F5733, 0x298EF221898DB0E7,
    0x55000029D1A5AA7E, 0x8BC08AE1B5061B45,
    0xC2C31C2B6C92703A, 0x94CC596BAF25EF42,
    0x0A1D73DB22540456, 0x04B6A0F9D9C4179A,
    0xEFFDAFA2AE3D3C60, 0xF7C8075BB49496C4,
    0x9CC5C7141D1CD4E3, 0x78BD1638218E5534,
    0xB2F11568F850246A, 0xEDFABCFA9502BC29,
    0x796CE5F2DA23051B, 0xAAE128B0DC93537C,
    0x3A493DA0EE4B29AE, 0xB5DF6B2C416895D7,
    0xFCABBD25122D7F37, 0x70810B58105DC4B1,
    0xE10FDD37F7882A90, 0x524DCAB5518A3F5C,
    0x3C9E85878451255B, 0x4029828119BD34E2,
    0x74A05B6F5D3CECCB, 0xB610021542E13ECA,
    0x0FF979D12F59E2AC, 0x6037DA27E4F9CC50,
    0x5E92975A0DF1847D, 0xD66DE190D3E623FE,
    0x5032D6B87B568048, 0x9A36B7CE8235216E,
    0x80272A7A24F64B4A, 0x93EFED8B8C6916F7,
    0x37DDBFF44CCE1555, 0x4B95DB5D4B99BD25,
    0x92D3FDA169812FC0, 0xFB1A4A9A90660BB6,
    0x730C196946A4B9B2, 0x81E289AA7F49DA68,
    0x64669A0F83B1A05F, 0x27B3FF7D9644F48B,
    0xCC6B615C8DB675B3, 0x674F20B9BCEBBE95,
    0x6F31238275655982, 0x5AE488713E45CF05,
    0xBF619F9954C21157, 0xEABAC46040A8EAE9,
    0x454C6FE9F2C0C1CD, 0x419CF6496412691C,
    0xD3DC3BEF265B0F70, 0x6D0E60F5C3578A9E
]

t4 = [
    0x5B0E608526323C55, 0x1A46C1A9FA1B59F5,
    0xA9E245A17C4C8FFA, 0x65CA5159DB2955D7,
    0x05DB0A76CE35AFC2, 0x81EAC77EA9113D45,
    0x528EF88AB6AC0A0D, 0xA09EA253597BE3FF,
    0x430DDFB3AC48CD56, 0xC4B3A67AF45CE46F,
    0x4ECECFD8FBE2D05E, 0x3EF56F10B39935F0,
    0x0B22D6829CD619C6, 0x17FD460A74DF2069,
    0x6CF8CC8E8510ED40, 0xD6C824BF3A6ECAA7,
    0x61243D581A817049, 0x048BACB6BBC163A2,
    0xD9A38AC27D44CC32, 0x7FDDFF5BAAF410AB,
    0xAD6D495AA804824B, 0xE1A6A74F2D8C9F94,
    0xD4F7851235DEE8E3, 0xFD4B7F886540D893,
    0x247C20042AA4BFDA, 0x096EA1C517D1327C,
    0xD56966B4361A6685, 0x277DA5C31221057D,
    0x94D59893A43ACFF7, 0x64F0C51CCDC02281,
    0x3D33BCC4FF6189DB, 0xE005CB184CE66AF1,
    0xFF5CCD1D1DB99BEA, 0xB0B854A7FE42980F,
    0x7BD46A6A718D4B9F, 0xD10FA8CC22A5FD8C,
    0xD31484952BE4BD31, 0xC7FA975FCB243847,
    0x4886ED1E5846C407, 0x28CDDB791EB70B04,
    0xC2B00BE2F573417F, 0x5C9590452180F877,
    0x7A6BDDFFF370EB00, 0xCE509E38D6D9D6A4,
    0xEBEB0F00647FA702, 0x1DCC06CF76606F06,
    0xE4D9F28BA286FF0A, 0xD85A305DC918C262,
    0x475B1D8732225F54, 0x2D4FB51668CCB5FE,
    0xA679B9D9D72BBA20, 0x53841C0D912D43A5,
    0x3B7EAA48BF12A4E8, 0x781E0E47F22F1DDF,
    0xEFF20CE60AB50973, 0x20D261D19DFFB742,
    0x16A12B03062A2E39, 0x1960EB2239650495,
    0x251C16FED50EB8B8, 0x9AC0C330F826016E,
    0xED152665953E7671, 0x02D63194A6369570,
    0x5074F08394B1C987, 0x70BA598C90B25CE1,
    0x794A15810B9742F6, 0x0D5925E9FCAF8C6C,
    0x3067716CD868744E, 0x910AB077E8D7731B,
    0x6A61BBDB5AC42F61, 0x93513EFBF0851567,
    0xF494724B9E83E9D5, 0xE887E1985C09648D,
    0x34B1D3C675370CFD, 0xDC35E433BC0D255D,
    0xD0AAB84234131BE0, 0x08042A50B48B7EAF,
    0x9997C4EE44A3AB35, 0x829A7B49201799D0,
    0x263B8307B7C54441, 0x752F95F4FD6A6CA6,
    0x927217402C08C6E5, 0x2A8AB754A795D9EE,
    0xA442F7552F72943D, 0x2C31334E19781208,
    0x4FA98D7CEAEE6291, 0x55C3862F665DB309,
    0xBD0610175D53B1F3, 0x46FE6CB840413F27,
    0x3FE03792DF0CFA59, 0xCFE700372EB85E8F,
    0xA7BE29E7ADBCE118, 0xE544EE5CDE8431DD,
    0x8A781B1B41F1873E, 0xA5C94C78A0D2F0E7,
    0x39412E2877B60728, 0xA1265EF3AFC9A62C,
    0xBCC2770C6A2506C5, 0x3AB66DD5DCE1CE12,
    0xE65499D04A675B37, 0x7D8F523481BFD216,
    0x0F6F64FCEC15F389, 0x74EFBE618B5B13C8,
    0xACDC82B714273E1D, 0xDD40BFE003199D17,
    0x37E99257E7E061F8, 0xFA52626904775AAA,
    0x8BBBF63A463D56F9, 0xF0013F1543A26E64,
    0xA8307E9F879EC898, 0xCC4C27A4150177CC,
    0x1B432F2CCA1D3348, 0xDE1D1F8F9F6FA013,
    0x606602A047A7DDD6, 0xD237AB64CC1CB2C7,
    0x9B938E7225FCD1D3, 0xEC4E03708E0FF476,
    0xFEB2FBDA3D03C12D, 0xAE0BCED2EE43889A,
    0x22CB8923EBFB4F43, 0x69360D013CF7396D,
    0x855E3602D2D4E022, 0x073805BAD01F784C,
    0x33E17A133852F546, 0xDF4874058AC7B638,
    0xBA92B29C678AA14A, 0x0CE89FC76CFAADCD,
    0x5F9D4E0908339E34, 0xF1AFE9291F5923B9,
    0x6E3480F60F4A265F, 0xEEBF3A2AB29B841C,
    0xE21938A88F91B4AD, 0x57DFEFF845C6D3C3,
    0x2F006B0BF62CAAF2, 0x62F479EF6F75EE78,
    0x11A55AD41C8916A9, 0xF229D29084FED453,
    0x42F1C27B16B000E6, 0x2B1F76749823C074,
    0x4B76ECA3C2745360, 0x8C98F463B91691BD,
    0x14BCC93CF1ADE66A, 0x8885213E6D458397,
    0x8E177DF0274D4711, 0xB49B73B5503F2951,
    0x10168168C3F96B6B, 0x0E3D963B63CAB0AE,
    0x8DFC4B5655A1DB14, 0xF789F1356E14DE5C,
    0x683E68AF4E51DAC1, 0xC9A84F9D8D4B0FD9,
    0x3691E03F52A0F9D1, 0x5ED86E46E1878E80,
    0x3C711A0E99D07150, 0x5A0865B20C4E9310,
    0x56FBFC1FE4F0682E, 0xEA8D5DE3105EDF9B,
    0x71ABFDB12379187A, 0x2EB99DE1BEE77B9C,
    0x21ECC0EA33CF4523, 0x59A4D7521805C7A1,
    0x3896F5EB56AE7C72, 0xAA638F3DB18F75DC,
    0x9F39358DABE9808E, 0xB7DEFA91C00B72AC,
    0x6B5541FD62492D92, 0x6DC6DEE8F92E4D5B,
    0x353F57ABC4BEEA7E, 0x735769D6DA5690CE,
    0x0A234AA642391484, 0xF6F9508028F80D9D,
    0xB8E319A27AB3F215, 0x31AD9C1151341A4D,
    0x773C22A57BEF5805, 0x45C7561A07968633,
    0xF913DA9E249DBE36, 0xDA652D9B78A64C68,
    0x4C27A97F3BC334EF, 0x76621220E66B17F4,
    0x967743899ACD7D0B, 0xF3EE5BCAE0ED6782,
    0x409F753600C879FC, 0x06D09A39B5926DB6,
    0x6F83AEB0317AC588, 0x01E6CA4A86381F21,
    0x66FF3462D19F3025, 0x72207C24DDFD3BFB,
    0x4AF6B6D3E2ECE2EB, 0x9C994DBEC7EA08DE,
    0x49ACE597B09A8BC4, 0xB38C4766CF0797BA,
    0x131B9373C57C2A75, 0xB1822CCE61931E58,
    0x9D7555B909BA1C0C, 0x127FAFDD937D11D2,
    0x29DA3BADC66D92E4, 0xA2C1D57154C2ECBC,
    0x58C5134D82F6FE24, 0x1C3AE3515B62274F,
    0xE907C82E01CB8126, 0xF8ED091913E37FCB,
    0x3249D8F9C80046C9, 0x80CF9BEDE388FB63,
    0x1881539A116CF19E, 0x5103F3F76BD52457,
    0x15B7E6F5AE47F7A8, 0xDBD7C6DED47E9CCF,
    0x44E55C410228BB1A, 0xB647D4255EDB4E99,
    0x5D11882BB8AAFC30, 0xF5098BBB29D3212A,
    0x8FB5EA14E90296B3, 0x677B942157DD025A,
    0xFB58E7C0A390ACB5, 0x89D3674C83BD4A01,
    0x9E2DA4DF4BF3B93B, 0xFCC41E328CAB4829,
    0x03F38C96BA582C52, 0xCAD1BDBD7FD85DB2,
    0xBBB442C16082AE83, 0xB95FE86BA5DA9AB0,
    0xB22E04673771A93F, 0x845358C9493152D8,
    0xBE2A488697B4541E, 0x95A2DC2DD38E6966,
    0xC02C11AC923C852B, 0x2388B1990DF2A87B,
    0x7C8008FA1B4F37BE, 0x1F70D0C84D54E503,
    0x5490ADEC7ECE57D4, 0x002B3C27D9063A3A,
    0x7EAEA3848030A2BF, 0xC602326DED2003C0,
    0x83A7287D69A94086, 0xC57A5FCB30F57A8A,
    0xB56844E479EBE779, 0xA373B40F05DCBCE9,
    0xD71A786E88570EE2, 0x879CBACDBDE8F6A0,
    0x976AD1BCC164A32F, 0xAB21E25E9666D78B,
    0x901063AAE5E5C33C, 0x9818B34448698D90,
    0xE36487AE3E1E8ABB, 0xAFBDF931893BDCB4,
    0x6345A0DC5FBBD519, 0x8628FE269B9465CA,
    0x1E5D01603F9C51EC, 0x4DE44006A15049B7,
    0xBF6C70E5F776CBB1, 0x411218F2EF552BED,
    0xCB0C0708705A36A3, 0xE74D14754F986044,
    0xCD56D9430EA8280E, 0xC12591D7535F5065,
    0xC83223F1720AEF96, 0xC3A0396F7363A51F
]


class TigerStruct(object):
    def __init__(self):
        self.res = [0x0123456789ABCDEF, 0xFEDCBA9876543210, 0xF096A5B4C3B2E187]
        self.length = 0
        self.leftover = ""


def tiger_round(a, b, c, x, mul):
    c ^= x
    c &= 0xffffffffffffffff
    a -= t1[((c) >> (0 * 8)) & 0xFF] ^ t2[((c) >> (2 * 8)) & 0xFF] ^ t3[((c) >> (4 * 8)) & 0xFF] ^ t4[((c) >> (6 * 8)) & 0xFF]
    b += t4[((c) >> (1 * 8)) & 0xFF] ^ t3[((c) >> (3 * 8)) & 0xFF] ^ t2[((c) >> (5 * 8)) & 0xFF] ^ t1[((c) >> (7 * 8)) & 0xFF]
    b *= mul
    a &= 0xffffffffffffffff
    b &= 0xffffffffffffffff
    c &= 0xffffffffffffffff
    return {"a": a, "b": b, "c": c}


def tiger_pass(a, b, c, mul, mystr):
    values = tiger_round(a, b, c, mystr[0], mul)
    values = tiger_round(values["b"], values["c"], values["a"], mystr[1], mul)
    values = {"b": values["a"], "c": values["b"], "a": values["c"]}
    values = tiger_round(values["c"], values["a"], values["b"], mystr[2], mul)
    values = {"c": values["a"], "a": values["b"], "b": values["c"]}
    values = tiger_round(values["a"], values["b"], values["c"], mystr[3], mul)
    values = tiger_round(values["b"], values["c"], values["a"], mystr[4], mul)
    values = {"b": values["a"], "c": values["b"], "a": values["c"]}
    values = tiger_round(values["c"], values["a"], values["b"], mystr[5], mul)
    values = {"c": values["a"], "a": values["b"], "b": values["c"]}
    values = tiger_round(values["a"], values["b"], values["c"], mystr[6], mul)
    values = tiger_round(values["b"], values["c"], values["a"], mystr[7], mul)
    values = {"b": values["a"], "c": values["b"], "a": values["c"]}
    return values


def tiger_compress(str, res):
    #setup
    a = res[0]
    b = res[1]
    c = res[2]

    x = []

    for j in range(0, 8):
        x.append(struct.unpack('Q', str[j * 8:j * 8 + 8])[0])

    # compress
    aa = a
    bb = b
    cc = c
    allf = 0xFFFFFFFFFFFFFFFF
    for i in range(0, 3):
        if i != 0:
            x[0] = (x[0] - (x[7] ^ 0xA5A5A5A5A5A5A5A5) & allf) & allf
            x[1] ^= x[0]
            x[2] = (x[2] + x[1]) & allf
            x[3] = (x[3] - (x[2] ^ (~x[1] & allf) << 19) & allf) & allf
            x[4] ^= x[3]
            x[5] = (x[5] + x[4]) & allf
            x[6] = (x[6] - (x[5] ^ (~x[4] & allf) >> 23) & allf) & allf
            x[7] ^= x[6]
            x[0] = (x[0] + x[7]) & allf
            x[1] = (x[1] - (x[0] ^ (~x[7] & allf) << 19) & allf) & allf
            x[2] ^= x[1]
            x[3] = (x[3] + x[2]) & allf
            x[4] = (x[4] - (x[3] ^ (~x[2] & allf) >> 23) & allf) & allf
            x[5] ^= x[4]
            x[6] = (x[6] + x[5]) & allf
            x[7] = (x[7] - (x[6] ^ 0x0123456789ABCDEF) & allf) & allf

        if i == 0:
            vals = tiger_pass(a, b, c, 5, x)
            a = vals['a']
            b = vals['b']
            c = vals['c']
        elif i == 1:
            vals = tiger_pass(a, b, c, 7, x)
            a = vals['a']
            b = vals['b']
            c = vals['c']
        else:
            vals = tiger_pass(a, b, c, 9, x)
            a = vals['a']
            b = vals['b']
            c = vals['c']
        tmpa = a
        a = c
        c = b
        b = tmpa
    a ^= aa
    b = (b - bb) & allf
    c = (c + cc) & allf

    # map values out
    res[0] = a
    res[1] = b
    res[2] = c


def tiger_add(input_str, tig):
    i = 0
    temp = tig.leftover + input_str
    length = len(temp)
    while i < length - 63:
        tiger_compress(temp[i:i + 64], tig.res)
        i += 64
    tig.leftover = temp[i:]
    tig.length += len(input_str)


def tiger_finalize(tig):
    length = tig.length
    temp = array.array('c', tig.leftover)
    j = len(temp)
    temp.append(chr(0x01))
    j += 1

    while j & 7 != 0:
        temp.append(chr(0))
        j += 1

    if j > 56:
        while j < 64:
            temp.append(chr(0))
            j += 1
        tiger_compress(temp, tig.res)
        j = 0

    # make the first 56 bytes 0
    temp.extend([chr(0) for i in range(0, 56 - j)])
    while j < 56:
        temp[j] = chr(0)
        j += 1
    while len(temp) > 56:
        temp.pop(56)

    temp.fromstring(struct.pack('<Q', length << 3))
    tiger_compress(temp, tig.res)


def test_tiger_hash():
    # TODO: Re-generate hashes with default endian
    #Tests
    assert tiger('').hexdigest() == \
        '24f0130c63ac933216166e76b1bb925ff373de2d49584e7a'
    assert tiger('abc').hexdigest() == \
        'f258c1e88414ab2a527ab541ffc5b8bf935f7b951c132951'
    assert tiger('Tiger').hexdigest() == \
        '9f00f599072300dd276abb38c8eb6dec37790c116f9d2bdf'
    assert tiger("ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+-").hexdigest() == \
        '87fb2a9083851cf7470d2cf810e6df9eb586445034a5a386'
    assert tiger("ABCDEFGHIJKLMNOPQRSTUVWXYZ=abcdefghijklmnopqrstuvwxyz+0123456789").hexdigest() == \
        '467db80863ebce488df1cd1261655de957896565975f9197'
    assert tiger("Tiger - A Fast New Hash Function, by Ross Anderson and Eli Biham").hexdigest() == \
        '0c410a042968868a1671da5a3fd29a725ec1e457d3cdb303'
    assert tiger(
        "Tiger - A Fast New Hash Function, by Ross Anderson and Eli Biham, " \
        "proceedings of Fast Software Encryption 3, Cambridge."
    ).hexdigest() == \
        'ebf591d5afa655ce7f22894ff87f54ac89c811b6b0da3193'
    assert tiger(
        "Tiger - A Fast New Hash Function, by Ross Anderson and" \
        " Eli Biham, proceedings of Fast Software Encryption 3, Cambridge, 1996."
    ).hexdigest() == \
        '3d9aeb03d1bd1a6357b2774dfd6d5b24dd68151d503974fc'
    assert tiger(
        "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz01" \
        "23456789+-ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz012345" \
        "6789+-"
    ).hexdigest() == \
        '00b83eb4e53440c576ac6aaee0a7485825fd15e70a59ffe4'
    #Chunked
    test = tiger('The quick brown fox jumps over the lazy dog')
    test.update('The quick brown fox jumps over the lazy dog')
    test.update('The quick brown fox jumps over the lazy dog')
    test.update('The quick brown fox jumps over the lazy dog')
    test.update('The quick brown fox jumps over the lazy dog')
    assert test.hexdigest() == \
        "33b3d0fbc7b8a2559b7b4689357d928c7202768b4c655f49"

########NEW FILE########
__FILENAME__ = whirlpool
## whirlpool.py - pure Python implementation of the Whirlpool algorithm.
## Bjorn Edstrom <be@bjrn.se> 16 december 2007.
##
## Copyrights
## ==========
##
## This code is based on the reference implementation by
## Paulo S.L.M. Barreto and Vincent Rijmen. The reference implementation
## is placed in the public domain but has the following headers:
##
## * THIS SOFTWARE IS PROVIDED BY THE AUTHORS ''AS IS'' AND ANY EXPRESS
## * OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED
## * WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE
## * ARE DISCLAIMED.  IN NO EVENT SHALL THE AUTHORS OR CONTRIBUTORS BE
## * LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR
## * CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF
## * SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR
## * BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY,
## * WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE
## * OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE,
## * EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
## *
## */
## /* The code contained in this file (Whirlpool.c) is in the public domain. */
##
## This Python implementation is therefore also placed in the public domain.

DIGESTBYTES = 64
DIGESTBITS = 512


class whirlpool(object):
    __name = 'whirlpool'
    __digest_size = DIGESTBYTES

    def __init__(self, arg=""):
        self.ctx = WhirlpoolStruct()
        if arg != "" and arg != None:
            self.update(arg)
        self.digest_status = 0

    @property
    def name(self):
        return self.__name

    @property
    def digest_size(self):
        return self.__digest_size

    def update(self, arg):
        if arg != "" and arg != None:
            WhirlpoolAdd(arg, len(arg) * 8, self.ctx)
        self.digest_status = 0

    def digest(self):
        digest = None
        if self.digest_status == 0:
            digest = WhirlpoolFinalize(self.ctx)
        self.digest_status = 1
        return digest

    def hexdigest(self):
        digest = self.digest()
        if digest == None:
            return None
        hex_digest = ''
        for byte in digest:
            hex_byte = '%02x' % (ord(byte))
            hex_digest += hex_byte
        return hex_digest

    def copy(self):
        import copy
        return copy.deepcopy(self)

#
# Private.
#

R = 10

C0 = [
    0x18186018c07830d8, 0x23238c2305af4626, 0xc6c63fc67ef991b8, 0xe8e887e8136fcdfb,
    0x878726874ca113cb, 0xb8b8dab8a9626d11, 0x0101040108050209, 0x4f4f214f426e9e0d,
    0x3636d836adee6c9b, 0xa6a6a2a6590451ff, 0xd2d26fd2debdb90c, 0xf5f5f3f5fb06f70e,
    0x7979f979ef80f296, 0x6f6fa16f5fcede30, 0x91917e91fcef3f6d, 0x52525552aa07a4f8,
    0x60609d6027fdc047, 0xbcbccabc89766535, 0x9b9b569baccd2b37, 0x8e8e028e048c018a,
    0xa3a3b6a371155bd2, 0x0c0c300c603c186c, 0x7b7bf17bff8af684, 0x3535d435b5e16a80,
    0x1d1d741de8693af5, 0xe0e0a7e05347ddb3, 0xd7d77bd7f6acb321, 0xc2c22fc25eed999c,
    0x2e2eb82e6d965c43, 0x4b4b314b627a9629, 0xfefedffea321e15d, 0x575741578216aed5,
    0x15155415a8412abd, 0x7777c1779fb6eee8, 0x3737dc37a5eb6e92, 0xe5e5b3e57b56d79e,
    0x9f9f469f8cd92313, 0xf0f0e7f0d317fd23, 0x4a4a354a6a7f9420, 0xdada4fda9e95a944,
    0x58587d58fa25b0a2, 0xc9c903c906ca8fcf, 0x2929a429558d527c, 0x0a0a280a5022145a,
    0xb1b1feb1e14f7f50, 0xa0a0baa0691a5dc9, 0x6b6bb16b7fdad614, 0x85852e855cab17d9,
    0xbdbdcebd8173673c, 0x5d5d695dd234ba8f, 0x1010401080502090, 0xf4f4f7f4f303f507,
    0xcbcb0bcb16c08bdd, 0x3e3ef83eedc67cd3, 0x0505140528110a2d, 0x676781671fe6ce78,
    0xe4e4b7e47353d597, 0x27279c2725bb4e02, 0x4141194132588273, 0x8b8b168b2c9d0ba7,
    0xa7a7a6a7510153f6, 0x7d7de97dcf94fab2, 0x95956e95dcfb3749, 0xd8d847d88e9fad56,
    0xfbfbcbfb8b30eb70, 0xeeee9fee2371c1cd, 0x7c7ced7cc791f8bb, 0x6666856617e3cc71,
    0xdddd53dda68ea77b, 0x17175c17b84b2eaf, 0x4747014702468e45, 0x9e9e429e84dc211a,
    0xcaca0fca1ec589d4, 0x2d2db42d75995a58, 0xbfbfc6bf9179632e, 0x07071c07381b0e3f,
    0xadad8ead012347ac, 0x5a5a755aea2fb4b0, 0x838336836cb51bef, 0x3333cc3385ff66b6,
    0x636391633ff2c65c, 0x02020802100a0412, 0xaaaa92aa39384993, 0x7171d971afa8e2de,
    0xc8c807c80ecf8dc6, 0x19196419c87d32d1, 0x494939497270923b, 0xd9d943d9869aaf5f,
    0xf2f2eff2c31df931, 0xe3e3abe34b48dba8, 0x5b5b715be22ab6b9, 0x88881a8834920dbc,
    0x9a9a529aa4c8293e, 0x262698262dbe4c0b, 0x3232c8328dfa64bf, 0xb0b0fab0e94a7d59,
    0xe9e983e91b6acff2, 0x0f0f3c0f78331e77, 0xd5d573d5e6a6b733, 0x80803a8074ba1df4,
    0xbebec2be997c6127, 0xcdcd13cd26de87eb, 0x3434d034bde46889, 0x48483d487a759032,
    0xffffdbffab24e354, 0x7a7af57af78ff48d, 0x90907a90f4ea3d64, 0x5f5f615fc23ebe9d,
    0x202080201da0403d, 0x6868bd6867d5d00f, 0x1a1a681ad07234ca, 0xaeae82ae192c41b7,
    0xb4b4eab4c95e757d, 0x54544d549a19a8ce, 0x93937693ece53b7f, 0x222288220daa442f,
    0x64648d6407e9c863, 0xf1f1e3f1db12ff2a, 0x7373d173bfa2e6cc, 0x12124812905a2482,
    0x40401d403a5d807a, 0x0808200840281048, 0xc3c32bc356e89b95, 0xecec97ec337bc5df,
    0xdbdb4bdb9690ab4d, 0xa1a1bea1611f5fc0, 0x8d8d0e8d1c830791, 0x3d3df43df5c97ac8,
    0x97976697ccf1335b, 0x0000000000000000, 0xcfcf1bcf36d483f9, 0x2b2bac2b4587566e,
    0x7676c57697b3ece1, 0x8282328264b019e6, 0xd6d67fd6fea9b128, 0x1b1b6c1bd87736c3,
    0xb5b5eeb5c15b7774, 0xafaf86af112943be, 0x6a6ab56a77dfd41d, 0x50505d50ba0da0ea,
    0x45450945124c8a57, 0xf3f3ebf3cb18fb38, 0x3030c0309df060ad, 0xefef9bef2b74c3c4,
    0x3f3ffc3fe5c37eda, 0x55554955921caac7, 0xa2a2b2a2791059db, 0xeaea8fea0365c9e9,
    0x656589650fecca6a, 0xbabad2bab9686903, 0x2f2fbc2f65935e4a, 0xc0c027c04ee79d8e,
    0xdede5fdebe81a160, 0x1c1c701ce06c38fc, 0xfdfdd3fdbb2ee746, 0x4d4d294d52649a1f,
    0x92927292e4e03976, 0x7575c9758fbceafa, 0x06061806301e0c36, 0x8a8a128a249809ae,
    0xb2b2f2b2f940794b, 0xe6e6bfe66359d185, 0x0e0e380e70361c7e, 0x1f1f7c1ff8633ee7,
    0x6262956237f7c455, 0xd4d477d4eea3b53a, 0xa8a89aa829324d81, 0x96966296c4f43152,
    0xf9f9c3f99b3aef62, 0xc5c533c566f697a3, 0x2525942535b14a10, 0x59597959f220b2ab,
    0x84842a8454ae15d0, 0x7272d572b7a7e4c5, 0x3939e439d5dd72ec, 0x4c4c2d4c5a619816,
    0x5e5e655eca3bbc94, 0x7878fd78e785f09f, 0x3838e038ddd870e5, 0x8c8c0a8c14860598,
    0xd1d163d1c6b2bf17, 0xa5a5aea5410b57e4, 0xe2e2afe2434dd9a1, 0x616199612ff8c24e,
    0xb3b3f6b3f1457b42, 0x2121842115a54234, 0x9c9c4a9c94d62508, 0x1e1e781ef0663cee,
    0x4343114322528661, 0xc7c73bc776fc93b1, 0xfcfcd7fcb32be54f, 0x0404100420140824,
    0x51515951b208a2e3, 0x99995e99bcc72f25, 0x6d6da96d4fc4da22, 0x0d0d340d68391a65,
    0xfafacffa8335e979, 0xdfdf5bdfb684a369, 0x7e7ee57ed79bfca9, 0x242490243db44819,
    0x3b3bec3bc5d776fe, 0xabab96ab313d4b9a, 0xcece1fce3ed181f0, 0x1111441188552299,
    0x8f8f068f0c890383, 0x4e4e254e4a6b9c04, 0xb7b7e6b7d1517366, 0xebeb8beb0b60cbe0,
    0x3c3cf03cfdcc78c1, 0x81813e817cbf1ffd, 0x94946a94d4fe3540, 0xf7f7fbf7eb0cf31c,
    0xb9b9deb9a1676f18, 0x13134c13985f268b, 0x2c2cb02c7d9c5851, 0xd3d36bd3d6b8bb05,
    0xe7e7bbe76b5cd38c, 0x6e6ea56e57cbdc39, 0xc4c437c46ef395aa, 0x03030c03180f061b,
    0x565645568a13acdc, 0x44440d441a49885e, 0x7f7fe17fdf9efea0, 0xa9a99ea921374f88,
    0x2a2aa82a4d825467, 0xbbbbd6bbb16d6b0a, 0xc1c123c146e29f87, 0x53535153a202a6f1,
    0xdcdc57dcae8ba572, 0x0b0b2c0b58271653, 0x9d9d4e9d9cd32701, 0x6c6cad6c47c1d82b,
    0x3131c43195f562a4, 0x7474cd7487b9e8f3, 0xf6f6fff6e309f115, 0x464605460a438c4c,
    0xacac8aac092645a5, 0x89891e893c970fb5, 0x14145014a04428b4, 0xe1e1a3e15b42dfba,
    0x16165816b04e2ca6, 0x3a3ae83acdd274f7, 0x6969b9696fd0d206, 0x09092409482d1241,
    0x7070dd70a7ade0d7, 0xb6b6e2b6d954716f, 0xd0d067d0ceb7bd1e, 0xeded93ed3b7ec7d6,
    0xcccc17cc2edb85e2, 0x424215422a578468, 0x98985a98b4c22d2c, 0xa4a4aaa4490e55ed,
    0x2828a0285d885075, 0x5c5c6d5cda31b886, 0xf8f8c7f8933fed6b, 0x8686228644a411c2,
]
C1 = [
    0xd818186018c07830, 0x2623238c2305af46, 0xb8c6c63fc67ef991, 0xfbe8e887e8136fcd,
    0xcb878726874ca113, 0x11b8b8dab8a9626d, 0x0901010401080502, 0x0d4f4f214f426e9e,
    0x9b3636d836adee6c, 0xffa6a6a2a6590451, 0x0cd2d26fd2debdb9, 0x0ef5f5f3f5fb06f7,
    0x967979f979ef80f2, 0x306f6fa16f5fcede, 0x6d91917e91fcef3f, 0xf852525552aa07a4,
    0x4760609d6027fdc0, 0x35bcbccabc897665, 0x379b9b569baccd2b, 0x8a8e8e028e048c01,
    0xd2a3a3b6a371155b, 0x6c0c0c300c603c18, 0x847b7bf17bff8af6, 0x803535d435b5e16a,
    0xf51d1d741de8693a, 0xb3e0e0a7e05347dd, 0x21d7d77bd7f6acb3, 0x9cc2c22fc25eed99,
    0x432e2eb82e6d965c, 0x294b4b314b627a96, 0x5dfefedffea321e1, 0xd5575741578216ae,
    0xbd15155415a8412a, 0xe87777c1779fb6ee, 0x923737dc37a5eb6e, 0x9ee5e5b3e57b56d7,
    0x139f9f469f8cd923, 0x23f0f0e7f0d317fd, 0x204a4a354a6a7f94, 0x44dada4fda9e95a9,
    0xa258587d58fa25b0, 0xcfc9c903c906ca8f, 0x7c2929a429558d52, 0x5a0a0a280a502214,
    0x50b1b1feb1e14f7f, 0xc9a0a0baa0691a5d, 0x146b6bb16b7fdad6, 0xd985852e855cab17,
    0x3cbdbdcebd817367, 0x8f5d5d695dd234ba, 0x9010104010805020, 0x07f4f4f7f4f303f5,
    0xddcbcb0bcb16c08b, 0xd33e3ef83eedc67c, 0x2d0505140528110a, 0x78676781671fe6ce,
    0x97e4e4b7e47353d5, 0x0227279c2725bb4e, 0x7341411941325882, 0xa78b8b168b2c9d0b,
    0xf6a7a7a6a7510153, 0xb27d7de97dcf94fa, 0x4995956e95dcfb37, 0x56d8d847d88e9fad,
    0x70fbfbcbfb8b30eb, 0xcdeeee9fee2371c1, 0xbb7c7ced7cc791f8, 0x716666856617e3cc,
    0x7bdddd53dda68ea7, 0xaf17175c17b84b2e, 0x454747014702468e, 0x1a9e9e429e84dc21,
    0xd4caca0fca1ec589, 0x582d2db42d75995a, 0x2ebfbfc6bf917963, 0x3f07071c07381b0e,
    0xacadad8ead012347, 0xb05a5a755aea2fb4, 0xef838336836cb51b, 0xb63333cc3385ff66,
    0x5c636391633ff2c6, 0x1202020802100a04, 0x93aaaa92aa393849, 0xde7171d971afa8e2,
    0xc6c8c807c80ecf8d, 0xd119196419c87d32, 0x3b49493949727092, 0x5fd9d943d9869aaf,
    0x31f2f2eff2c31df9, 0xa8e3e3abe34b48db, 0xb95b5b715be22ab6, 0xbc88881a8834920d,
    0x3e9a9a529aa4c829, 0x0b262698262dbe4c, 0xbf3232c8328dfa64, 0x59b0b0fab0e94a7d,
    0xf2e9e983e91b6acf, 0x770f0f3c0f78331e, 0x33d5d573d5e6a6b7, 0xf480803a8074ba1d,
    0x27bebec2be997c61, 0xebcdcd13cd26de87, 0x893434d034bde468, 0x3248483d487a7590,
    0x54ffffdbffab24e3, 0x8d7a7af57af78ff4, 0x6490907a90f4ea3d, 0x9d5f5f615fc23ebe,
    0x3d202080201da040, 0x0f6868bd6867d5d0, 0xca1a1a681ad07234, 0xb7aeae82ae192c41,
    0x7db4b4eab4c95e75, 0xce54544d549a19a8, 0x7f93937693ece53b, 0x2f222288220daa44,
    0x6364648d6407e9c8, 0x2af1f1e3f1db12ff, 0xcc7373d173bfa2e6, 0x8212124812905a24,
    0x7a40401d403a5d80, 0x4808082008402810, 0x95c3c32bc356e89b, 0xdfecec97ec337bc5,
    0x4ddbdb4bdb9690ab, 0xc0a1a1bea1611f5f, 0x918d8d0e8d1c8307, 0xc83d3df43df5c97a,
    0x5b97976697ccf133, 0x0000000000000000, 0xf9cfcf1bcf36d483, 0x6e2b2bac2b458756,
    0xe17676c57697b3ec, 0xe68282328264b019, 0x28d6d67fd6fea9b1, 0xc31b1b6c1bd87736,
    0x74b5b5eeb5c15b77, 0xbeafaf86af112943, 0x1d6a6ab56a77dfd4, 0xea50505d50ba0da0,
    0x5745450945124c8a, 0x38f3f3ebf3cb18fb, 0xad3030c0309df060, 0xc4efef9bef2b74c3,
    0xda3f3ffc3fe5c37e, 0xc755554955921caa, 0xdba2a2b2a2791059, 0xe9eaea8fea0365c9,
    0x6a656589650fecca, 0x03babad2bab96869, 0x4a2f2fbc2f65935e, 0x8ec0c027c04ee79d,
    0x60dede5fdebe81a1, 0xfc1c1c701ce06c38, 0x46fdfdd3fdbb2ee7, 0x1f4d4d294d52649a,
    0x7692927292e4e039, 0xfa7575c9758fbcea, 0x3606061806301e0c, 0xae8a8a128a249809,
    0x4bb2b2f2b2f94079, 0x85e6e6bfe66359d1, 0x7e0e0e380e70361c, 0xe71f1f7c1ff8633e,
    0x556262956237f7c4, 0x3ad4d477d4eea3b5, 0x81a8a89aa829324d, 0x5296966296c4f431,
    0x62f9f9c3f99b3aef, 0xa3c5c533c566f697, 0x102525942535b14a, 0xab59597959f220b2,
    0xd084842a8454ae15, 0xc57272d572b7a7e4, 0xec3939e439d5dd72, 0x164c4c2d4c5a6198,
    0x945e5e655eca3bbc, 0x9f7878fd78e785f0, 0xe53838e038ddd870, 0x988c8c0a8c148605,
    0x17d1d163d1c6b2bf, 0xe4a5a5aea5410b57, 0xa1e2e2afe2434dd9, 0x4e616199612ff8c2,
    0x42b3b3f6b3f1457b, 0x342121842115a542, 0x089c9c4a9c94d625, 0xee1e1e781ef0663c,
    0x6143431143225286, 0xb1c7c73bc776fc93, 0x4ffcfcd7fcb32be5, 0x2404041004201408,
    0xe351515951b208a2, 0x2599995e99bcc72f, 0x226d6da96d4fc4da, 0x650d0d340d68391a,
    0x79fafacffa8335e9, 0x69dfdf5bdfb684a3, 0xa97e7ee57ed79bfc, 0x19242490243db448,
    0xfe3b3bec3bc5d776, 0x9aabab96ab313d4b, 0xf0cece1fce3ed181, 0x9911114411885522,
    0x838f8f068f0c8903, 0x044e4e254e4a6b9c, 0x66b7b7e6b7d15173, 0xe0ebeb8beb0b60cb,
    0xc13c3cf03cfdcc78, 0xfd81813e817cbf1f, 0x4094946a94d4fe35, 0x1cf7f7fbf7eb0cf3,
    0x18b9b9deb9a1676f, 0x8b13134c13985f26, 0x512c2cb02c7d9c58, 0x05d3d36bd3d6b8bb,
    0x8ce7e7bbe76b5cd3, 0x396e6ea56e57cbdc, 0xaac4c437c46ef395, 0x1b03030c03180f06,
    0xdc565645568a13ac, 0x5e44440d441a4988, 0xa07f7fe17fdf9efe, 0x88a9a99ea921374f,
    0x672a2aa82a4d8254, 0x0abbbbd6bbb16d6b, 0x87c1c123c146e29f, 0xf153535153a202a6,
    0x72dcdc57dcae8ba5, 0x530b0b2c0b582716, 0x019d9d4e9d9cd327, 0x2b6c6cad6c47c1d8,
    0xa43131c43195f562, 0xf37474cd7487b9e8, 0x15f6f6fff6e309f1, 0x4c464605460a438c,
    0xa5acac8aac092645, 0xb589891e893c970f, 0xb414145014a04428, 0xbae1e1a3e15b42df,
    0xa616165816b04e2c, 0xf73a3ae83acdd274, 0x066969b9696fd0d2, 0x4109092409482d12,
    0xd77070dd70a7ade0, 0x6fb6b6e2b6d95471, 0x1ed0d067d0ceb7bd, 0xd6eded93ed3b7ec7,
    0xe2cccc17cc2edb85, 0x68424215422a5784, 0x2c98985a98b4c22d, 0xeda4a4aaa4490e55,
    0x752828a0285d8850, 0x865c5c6d5cda31b8, 0x6bf8f8c7f8933fed, 0xc28686228644a411,
]
C2 = [
    0x30d818186018c078, 0x462623238c2305af, 0x91b8c6c63fc67ef9, 0xcdfbe8e887e8136f,
    0x13cb878726874ca1, 0x6d11b8b8dab8a962, 0x0209010104010805, 0x9e0d4f4f214f426e,
    0x6c9b3636d836adee, 0x51ffa6a6a2a65904, 0xb90cd2d26fd2debd, 0xf70ef5f5f3f5fb06,
    0xf2967979f979ef80, 0xde306f6fa16f5fce, 0x3f6d91917e91fcef, 0xa4f852525552aa07,
    0xc04760609d6027fd, 0x6535bcbccabc8976, 0x2b379b9b569baccd, 0x018a8e8e028e048c,
    0x5bd2a3a3b6a37115, 0x186c0c0c300c603c, 0xf6847b7bf17bff8a, 0x6a803535d435b5e1,
    0x3af51d1d741de869, 0xddb3e0e0a7e05347, 0xb321d7d77bd7f6ac, 0x999cc2c22fc25eed,
    0x5c432e2eb82e6d96, 0x96294b4b314b627a, 0xe15dfefedffea321, 0xaed5575741578216,
    0x2abd15155415a841, 0xeee87777c1779fb6, 0x6e923737dc37a5eb, 0xd79ee5e5b3e57b56,
    0x23139f9f469f8cd9, 0xfd23f0f0e7f0d317, 0x94204a4a354a6a7f, 0xa944dada4fda9e95,
    0xb0a258587d58fa25, 0x8fcfc9c903c906ca, 0x527c2929a429558d, 0x145a0a0a280a5022,
    0x7f50b1b1feb1e14f, 0x5dc9a0a0baa0691a, 0xd6146b6bb16b7fda, 0x17d985852e855cab,
    0x673cbdbdcebd8173, 0xba8f5d5d695dd234, 0x2090101040108050, 0xf507f4f4f7f4f303,
    0x8bddcbcb0bcb16c0, 0x7cd33e3ef83eedc6, 0x0a2d050514052811, 0xce78676781671fe6,
    0xd597e4e4b7e47353, 0x4e0227279c2725bb, 0x8273414119413258, 0x0ba78b8b168b2c9d,
    0x53f6a7a7a6a75101, 0xfab27d7de97dcf94, 0x374995956e95dcfb, 0xad56d8d847d88e9f,
    0xeb70fbfbcbfb8b30, 0xc1cdeeee9fee2371, 0xf8bb7c7ced7cc791, 0xcc716666856617e3,
    0xa77bdddd53dda68e, 0x2eaf17175c17b84b, 0x8e45474701470246, 0x211a9e9e429e84dc,
    0x89d4caca0fca1ec5, 0x5a582d2db42d7599, 0x632ebfbfc6bf9179, 0x0e3f07071c07381b,
    0x47acadad8ead0123, 0xb4b05a5a755aea2f, 0x1bef838336836cb5, 0x66b63333cc3385ff,
    0xc65c636391633ff2, 0x041202020802100a, 0x4993aaaa92aa3938, 0xe2de7171d971afa8,
    0x8dc6c8c807c80ecf, 0x32d119196419c87d, 0x923b494939497270, 0xaf5fd9d943d9869a,
    0xf931f2f2eff2c31d, 0xdba8e3e3abe34b48, 0xb6b95b5b715be22a, 0x0dbc88881a883492,
    0x293e9a9a529aa4c8, 0x4c0b262698262dbe, 0x64bf3232c8328dfa, 0x7d59b0b0fab0e94a,
    0xcff2e9e983e91b6a, 0x1e770f0f3c0f7833, 0xb733d5d573d5e6a6, 0x1df480803a8074ba,
    0x6127bebec2be997c, 0x87ebcdcd13cd26de, 0x68893434d034bde4, 0x903248483d487a75,
    0xe354ffffdbffab24, 0xf48d7a7af57af78f, 0x3d6490907a90f4ea, 0xbe9d5f5f615fc23e,
    0x403d202080201da0, 0xd00f6868bd6867d5, 0x34ca1a1a681ad072, 0x41b7aeae82ae192c,
    0x757db4b4eab4c95e, 0xa8ce54544d549a19, 0x3b7f93937693ece5, 0x442f222288220daa,
    0xc86364648d6407e9, 0xff2af1f1e3f1db12, 0xe6cc7373d173bfa2, 0x248212124812905a,
    0x807a40401d403a5d, 0x1048080820084028, 0x9b95c3c32bc356e8, 0xc5dfecec97ec337b,
    0xab4ddbdb4bdb9690, 0x5fc0a1a1bea1611f, 0x07918d8d0e8d1c83, 0x7ac83d3df43df5c9,
    0x335b97976697ccf1, 0x0000000000000000, 0x83f9cfcf1bcf36d4, 0x566e2b2bac2b4587,
    0xece17676c57697b3, 0x19e68282328264b0, 0xb128d6d67fd6fea9, 0x36c31b1b6c1bd877,
    0x7774b5b5eeb5c15b, 0x43beafaf86af1129, 0xd41d6a6ab56a77df, 0xa0ea50505d50ba0d,
    0x8a5745450945124c, 0xfb38f3f3ebf3cb18, 0x60ad3030c0309df0, 0xc3c4efef9bef2b74,
    0x7eda3f3ffc3fe5c3, 0xaac755554955921c, 0x59dba2a2b2a27910, 0xc9e9eaea8fea0365,
    0xca6a656589650fec, 0x6903babad2bab968, 0x5e4a2f2fbc2f6593, 0x9d8ec0c027c04ee7,
    0xa160dede5fdebe81, 0x38fc1c1c701ce06c, 0xe746fdfdd3fdbb2e, 0x9a1f4d4d294d5264,
    0x397692927292e4e0, 0xeafa7575c9758fbc, 0x0c3606061806301e, 0x09ae8a8a128a2498,
    0x794bb2b2f2b2f940, 0xd185e6e6bfe66359, 0x1c7e0e0e380e7036, 0x3ee71f1f7c1ff863,
    0xc4556262956237f7, 0xb53ad4d477d4eea3, 0x4d81a8a89aa82932, 0x315296966296c4f4,
    0xef62f9f9c3f99b3a, 0x97a3c5c533c566f6, 0x4a102525942535b1, 0xb2ab59597959f220,
    0x15d084842a8454ae, 0xe4c57272d572b7a7, 0x72ec3939e439d5dd, 0x98164c4c2d4c5a61,
    0xbc945e5e655eca3b, 0xf09f7878fd78e785, 0x70e53838e038ddd8, 0x05988c8c0a8c1486,
    0xbf17d1d163d1c6b2, 0x57e4a5a5aea5410b, 0xd9a1e2e2afe2434d, 0xc24e616199612ff8,
    0x7b42b3b3f6b3f145, 0x42342121842115a5, 0x25089c9c4a9c94d6, 0x3cee1e1e781ef066,
    0x8661434311432252, 0x93b1c7c73bc776fc, 0xe54ffcfcd7fcb32b, 0x0824040410042014,
    0xa2e351515951b208, 0x2f2599995e99bcc7, 0xda226d6da96d4fc4, 0x1a650d0d340d6839,
    0xe979fafacffa8335, 0xa369dfdf5bdfb684, 0xfca97e7ee57ed79b, 0x4819242490243db4,
    0x76fe3b3bec3bc5d7, 0x4b9aabab96ab313d, 0x81f0cece1fce3ed1, 0x2299111144118855,
    0x03838f8f068f0c89, 0x9c044e4e254e4a6b, 0x7366b7b7e6b7d151, 0xcbe0ebeb8beb0b60,
    0x78c13c3cf03cfdcc, 0x1ffd81813e817cbf, 0x354094946a94d4fe, 0xf31cf7f7fbf7eb0c,
    0x6f18b9b9deb9a167, 0x268b13134c13985f, 0x58512c2cb02c7d9c, 0xbb05d3d36bd3d6b8,
    0xd38ce7e7bbe76b5c, 0xdc396e6ea56e57cb, 0x95aac4c437c46ef3, 0x061b03030c03180f,
    0xacdc565645568a13, 0x885e44440d441a49, 0xfea07f7fe17fdf9e, 0x4f88a9a99ea92137,
    0x54672a2aa82a4d82, 0x6b0abbbbd6bbb16d, 0x9f87c1c123c146e2, 0xa6f153535153a202,
    0xa572dcdc57dcae8b, 0x16530b0b2c0b5827, 0x27019d9d4e9d9cd3, 0xd82b6c6cad6c47c1,
    0x62a43131c43195f5, 0xe8f37474cd7487b9, 0xf115f6f6fff6e309, 0x8c4c464605460a43,
    0x45a5acac8aac0926, 0x0fb589891e893c97, 0x28b414145014a044, 0xdfbae1e1a3e15b42,
    0x2ca616165816b04e, 0x74f73a3ae83acdd2, 0xd2066969b9696fd0, 0x124109092409482d,
    0xe0d77070dd70a7ad, 0x716fb6b6e2b6d954, 0xbd1ed0d067d0ceb7, 0xc7d6eded93ed3b7e,
    0x85e2cccc17cc2edb, 0x8468424215422a57, 0x2d2c98985a98b4c2, 0x55eda4a4aaa4490e,
    0x50752828a0285d88, 0xb8865c5c6d5cda31, 0xed6bf8f8c7f8933f, 0x11c28686228644a4,
]
C3 = [
    0x7830d818186018c0, 0xaf462623238c2305, 0xf991b8c6c63fc67e, 0x6fcdfbe8e887e813,
    0xa113cb878726874c, 0x626d11b8b8dab8a9, 0x0502090101040108, 0x6e9e0d4f4f214f42,
    0xee6c9b3636d836ad, 0x0451ffa6a6a2a659, 0xbdb90cd2d26fd2de, 0x06f70ef5f5f3f5fb,
    0x80f2967979f979ef, 0xcede306f6fa16f5f, 0xef3f6d91917e91fc, 0x07a4f852525552aa,
    0xfdc04760609d6027, 0x766535bcbccabc89, 0xcd2b379b9b569bac, 0x8c018a8e8e028e04,
    0x155bd2a3a3b6a371, 0x3c186c0c0c300c60, 0x8af6847b7bf17bff, 0xe16a803535d435b5,
    0x693af51d1d741de8, 0x47ddb3e0e0a7e053, 0xacb321d7d77bd7f6, 0xed999cc2c22fc25e,
    0x965c432e2eb82e6d, 0x7a96294b4b314b62, 0x21e15dfefedffea3, 0x16aed55757415782,
    0x412abd15155415a8, 0xb6eee87777c1779f, 0xeb6e923737dc37a5, 0x56d79ee5e5b3e57b,
    0xd923139f9f469f8c, 0x17fd23f0f0e7f0d3, 0x7f94204a4a354a6a, 0x95a944dada4fda9e,
    0x25b0a258587d58fa, 0xca8fcfc9c903c906, 0x8d527c2929a42955, 0x22145a0a0a280a50,
    0x4f7f50b1b1feb1e1, 0x1a5dc9a0a0baa069, 0xdad6146b6bb16b7f, 0xab17d985852e855c,
    0x73673cbdbdcebd81, 0x34ba8f5d5d695dd2, 0x5020901010401080, 0x03f507f4f4f7f4f3,
    0xc08bddcbcb0bcb16, 0xc67cd33e3ef83eed, 0x110a2d0505140528, 0xe6ce78676781671f,
    0x53d597e4e4b7e473, 0xbb4e0227279c2725, 0x5882734141194132, 0x9d0ba78b8b168b2c,
    0x0153f6a7a7a6a751, 0x94fab27d7de97dcf, 0xfb374995956e95dc, 0x9fad56d8d847d88e,
    0x30eb70fbfbcbfb8b, 0x71c1cdeeee9fee23, 0x91f8bb7c7ced7cc7, 0xe3cc716666856617,
    0x8ea77bdddd53dda6, 0x4b2eaf17175c17b8, 0x468e454747014702, 0xdc211a9e9e429e84,
    0xc589d4caca0fca1e, 0x995a582d2db42d75, 0x79632ebfbfc6bf91, 0x1b0e3f07071c0738,
    0x2347acadad8ead01, 0x2fb4b05a5a755aea, 0xb51bef838336836c, 0xff66b63333cc3385,
    0xf2c65c636391633f, 0x0a04120202080210, 0x384993aaaa92aa39, 0xa8e2de7171d971af,
    0xcf8dc6c8c807c80e, 0x7d32d119196419c8, 0x70923b4949394972, 0x9aaf5fd9d943d986,
    0x1df931f2f2eff2c3, 0x48dba8e3e3abe34b, 0x2ab6b95b5b715be2, 0x920dbc88881a8834,
    0xc8293e9a9a529aa4, 0xbe4c0b262698262d, 0xfa64bf3232c8328d, 0x4a7d59b0b0fab0e9,
    0x6acff2e9e983e91b, 0x331e770f0f3c0f78, 0xa6b733d5d573d5e6, 0xba1df480803a8074,
    0x7c6127bebec2be99, 0xde87ebcdcd13cd26, 0xe468893434d034bd, 0x75903248483d487a,
    0x24e354ffffdbffab, 0x8ff48d7a7af57af7, 0xea3d6490907a90f4, 0x3ebe9d5f5f615fc2,
    0xa0403d202080201d, 0xd5d00f6868bd6867, 0x7234ca1a1a681ad0, 0x2c41b7aeae82ae19,
    0x5e757db4b4eab4c9, 0x19a8ce54544d549a, 0xe53b7f93937693ec, 0xaa442f222288220d,
    0xe9c86364648d6407, 0x12ff2af1f1e3f1db, 0xa2e6cc7373d173bf, 0x5a24821212481290,
    0x5d807a40401d403a, 0x2810480808200840, 0xe89b95c3c32bc356, 0x7bc5dfecec97ec33,
    0x90ab4ddbdb4bdb96, 0x1f5fc0a1a1bea161, 0x8307918d8d0e8d1c, 0xc97ac83d3df43df5,
    0xf1335b97976697cc, 0x0000000000000000, 0xd483f9cfcf1bcf36, 0x87566e2b2bac2b45,
    0xb3ece17676c57697, 0xb019e68282328264, 0xa9b128d6d67fd6fe, 0x7736c31b1b6c1bd8,
    0x5b7774b5b5eeb5c1, 0x2943beafaf86af11, 0xdfd41d6a6ab56a77, 0x0da0ea50505d50ba,
    0x4c8a574545094512, 0x18fb38f3f3ebf3cb, 0xf060ad3030c0309d, 0x74c3c4efef9bef2b,
    0xc37eda3f3ffc3fe5, 0x1caac75555495592, 0x1059dba2a2b2a279, 0x65c9e9eaea8fea03,
    0xecca6a656589650f, 0x686903babad2bab9, 0x935e4a2f2fbc2f65, 0xe79d8ec0c027c04e,
    0x81a160dede5fdebe, 0x6c38fc1c1c701ce0, 0x2ee746fdfdd3fdbb, 0x649a1f4d4d294d52,
    0xe0397692927292e4, 0xbceafa7575c9758f, 0x1e0c360606180630, 0x9809ae8a8a128a24,
    0x40794bb2b2f2b2f9, 0x59d185e6e6bfe663, 0x361c7e0e0e380e70, 0x633ee71f1f7c1ff8,
    0xf7c4556262956237, 0xa3b53ad4d477d4ee, 0x324d81a8a89aa829, 0xf4315296966296c4,
    0x3aef62f9f9c3f99b, 0xf697a3c5c533c566, 0xb14a102525942535, 0x20b2ab59597959f2,
    0xae15d084842a8454, 0xa7e4c57272d572b7, 0xdd72ec3939e439d5, 0x6198164c4c2d4c5a,
    0x3bbc945e5e655eca, 0x85f09f7878fd78e7, 0xd870e53838e038dd, 0x8605988c8c0a8c14,
    0xb2bf17d1d163d1c6, 0x0b57e4a5a5aea541, 0x4dd9a1e2e2afe243, 0xf8c24e616199612f,
    0x457b42b3b3f6b3f1, 0xa542342121842115, 0xd625089c9c4a9c94, 0x663cee1e1e781ef0,
    0x5286614343114322, 0xfc93b1c7c73bc776, 0x2be54ffcfcd7fcb3, 0x1408240404100420,
    0x08a2e351515951b2, 0xc72f2599995e99bc, 0xc4da226d6da96d4f, 0x391a650d0d340d68,
    0x35e979fafacffa83, 0x84a369dfdf5bdfb6, 0x9bfca97e7ee57ed7, 0xb44819242490243d,
    0xd776fe3b3bec3bc5, 0x3d4b9aabab96ab31, 0xd181f0cece1fce3e, 0x5522991111441188,
    0x8903838f8f068f0c, 0x6b9c044e4e254e4a, 0x517366b7b7e6b7d1, 0x60cbe0ebeb8beb0b,
    0xcc78c13c3cf03cfd, 0xbf1ffd81813e817c, 0xfe354094946a94d4, 0x0cf31cf7f7fbf7eb,
    0x676f18b9b9deb9a1, 0x5f268b13134c1398, 0x9c58512c2cb02c7d, 0xb8bb05d3d36bd3d6,
    0x5cd38ce7e7bbe76b, 0xcbdc396e6ea56e57, 0xf395aac4c437c46e, 0x0f061b03030c0318,
    0x13acdc565645568a, 0x49885e44440d441a, 0x9efea07f7fe17fdf, 0x374f88a9a99ea921,
    0x8254672a2aa82a4d, 0x6d6b0abbbbd6bbb1, 0xe29f87c1c123c146, 0x02a6f153535153a2,
    0x8ba572dcdc57dcae, 0x2716530b0b2c0b58, 0xd327019d9d4e9d9c, 0xc1d82b6c6cad6c47,
    0xf562a43131c43195, 0xb9e8f37474cd7487, 0x09f115f6f6fff6e3, 0x438c4c464605460a,
    0x2645a5acac8aac09, 0x970fb589891e893c, 0x4428b414145014a0, 0x42dfbae1e1a3e15b,
    0x4e2ca616165816b0, 0xd274f73a3ae83acd, 0xd0d2066969b9696f, 0x2d12410909240948,
    0xade0d77070dd70a7, 0x54716fb6b6e2b6d9, 0xb7bd1ed0d067d0ce, 0x7ec7d6eded93ed3b,
    0xdb85e2cccc17cc2e, 0x578468424215422a, 0xc22d2c98985a98b4, 0x0e55eda4a4aaa449,
    0x8850752828a0285d, 0x31b8865c5c6d5cda, 0x3fed6bf8f8c7f893, 0xa411c28686228644,
]
C4 = [
    0xc07830d818186018, 0x05af462623238c23, 0x7ef991b8c6c63fc6, 0x136fcdfbe8e887e8,
    0x4ca113cb87872687, 0xa9626d11b8b8dab8, 0x0805020901010401, 0x426e9e0d4f4f214f,
    0xadee6c9b3636d836, 0x590451ffa6a6a2a6, 0xdebdb90cd2d26fd2, 0xfb06f70ef5f5f3f5,
    0xef80f2967979f979, 0x5fcede306f6fa16f, 0xfcef3f6d91917e91, 0xaa07a4f852525552,
    0x27fdc04760609d60, 0x89766535bcbccabc, 0xaccd2b379b9b569b, 0x048c018a8e8e028e,
    0x71155bd2a3a3b6a3, 0x603c186c0c0c300c, 0xff8af6847b7bf17b, 0xb5e16a803535d435,
    0xe8693af51d1d741d, 0x5347ddb3e0e0a7e0, 0xf6acb321d7d77bd7, 0x5eed999cc2c22fc2,
    0x6d965c432e2eb82e, 0x627a96294b4b314b, 0xa321e15dfefedffe, 0x8216aed557574157,
    0xa8412abd15155415, 0x9fb6eee87777c177, 0xa5eb6e923737dc37, 0x7b56d79ee5e5b3e5,
    0x8cd923139f9f469f, 0xd317fd23f0f0e7f0, 0x6a7f94204a4a354a, 0x9e95a944dada4fda,
    0xfa25b0a258587d58, 0x06ca8fcfc9c903c9, 0x558d527c2929a429, 0x5022145a0a0a280a,
    0xe14f7f50b1b1feb1, 0x691a5dc9a0a0baa0, 0x7fdad6146b6bb16b, 0x5cab17d985852e85,
    0x8173673cbdbdcebd, 0xd234ba8f5d5d695d, 0x8050209010104010, 0xf303f507f4f4f7f4,
    0x16c08bddcbcb0bcb, 0xedc67cd33e3ef83e, 0x28110a2d05051405, 0x1fe6ce7867678167,
    0x7353d597e4e4b7e4, 0x25bb4e0227279c27, 0x3258827341411941, 0x2c9d0ba78b8b168b,
    0x510153f6a7a7a6a7, 0xcf94fab27d7de97d, 0xdcfb374995956e95, 0x8e9fad56d8d847d8,
    0x8b30eb70fbfbcbfb, 0x2371c1cdeeee9fee, 0xc791f8bb7c7ced7c, 0x17e3cc7166668566,
    0xa68ea77bdddd53dd, 0xb84b2eaf17175c17, 0x02468e4547470147, 0x84dc211a9e9e429e,
    0x1ec589d4caca0fca, 0x75995a582d2db42d, 0x9179632ebfbfc6bf, 0x381b0e3f07071c07,
    0x012347acadad8ead, 0xea2fb4b05a5a755a, 0x6cb51bef83833683, 0x85ff66b63333cc33,
    0x3ff2c65c63639163, 0x100a041202020802, 0x39384993aaaa92aa, 0xafa8e2de7171d971,
    0x0ecf8dc6c8c807c8, 0xc87d32d119196419, 0x7270923b49493949, 0x869aaf5fd9d943d9,
    0xc31df931f2f2eff2, 0x4b48dba8e3e3abe3, 0xe22ab6b95b5b715b, 0x34920dbc88881a88,
    0xa4c8293e9a9a529a, 0x2dbe4c0b26269826, 0x8dfa64bf3232c832, 0xe94a7d59b0b0fab0,
    0x1b6acff2e9e983e9, 0x78331e770f0f3c0f, 0xe6a6b733d5d573d5, 0x74ba1df480803a80,
    0x997c6127bebec2be, 0x26de87ebcdcd13cd, 0xbde468893434d034, 0x7a75903248483d48,
    0xab24e354ffffdbff, 0xf78ff48d7a7af57a, 0xf4ea3d6490907a90, 0xc23ebe9d5f5f615f,
    0x1da0403d20208020, 0x67d5d00f6868bd68, 0xd07234ca1a1a681a, 0x192c41b7aeae82ae,
    0xc95e757db4b4eab4, 0x9a19a8ce54544d54, 0xece53b7f93937693, 0x0daa442f22228822,
    0x07e9c86364648d64, 0xdb12ff2af1f1e3f1, 0xbfa2e6cc7373d173, 0x905a248212124812,
    0x3a5d807a40401d40, 0x4028104808082008, 0x56e89b95c3c32bc3, 0x337bc5dfecec97ec,
    0x9690ab4ddbdb4bdb, 0x611f5fc0a1a1bea1, 0x1c8307918d8d0e8d, 0xf5c97ac83d3df43d,
    0xccf1335b97976697, 0x0000000000000000, 0x36d483f9cfcf1bcf, 0x4587566e2b2bac2b,
    0x97b3ece17676c576, 0x64b019e682823282, 0xfea9b128d6d67fd6, 0xd87736c31b1b6c1b,
    0xc15b7774b5b5eeb5, 0x112943beafaf86af, 0x77dfd41d6a6ab56a, 0xba0da0ea50505d50,
    0x124c8a5745450945, 0xcb18fb38f3f3ebf3, 0x9df060ad3030c030, 0x2b74c3c4efef9bef,
    0xe5c37eda3f3ffc3f, 0x921caac755554955, 0x791059dba2a2b2a2, 0x0365c9e9eaea8fea,
    0x0fecca6a65658965, 0xb9686903babad2ba, 0x65935e4a2f2fbc2f, 0x4ee79d8ec0c027c0,
    0xbe81a160dede5fde, 0xe06c38fc1c1c701c, 0xbb2ee746fdfdd3fd, 0x52649a1f4d4d294d,
    0xe4e0397692927292, 0x8fbceafa7575c975, 0x301e0c3606061806, 0x249809ae8a8a128a,
    0xf940794bb2b2f2b2, 0x6359d185e6e6bfe6, 0x70361c7e0e0e380e, 0xf8633ee71f1f7c1f,
    0x37f7c45562629562, 0xeea3b53ad4d477d4, 0x29324d81a8a89aa8, 0xc4f4315296966296,
    0x9b3aef62f9f9c3f9, 0x66f697a3c5c533c5, 0x35b14a1025259425, 0xf220b2ab59597959,
    0x54ae15d084842a84, 0xb7a7e4c57272d572, 0xd5dd72ec3939e439, 0x5a6198164c4c2d4c,
    0xca3bbc945e5e655e, 0xe785f09f7878fd78, 0xddd870e53838e038, 0x148605988c8c0a8c,
    0xc6b2bf17d1d163d1, 0x410b57e4a5a5aea5, 0x434dd9a1e2e2afe2, 0x2ff8c24e61619961,
    0xf1457b42b3b3f6b3, 0x15a5423421218421, 0x94d625089c9c4a9c, 0xf0663cee1e1e781e,
    0x2252866143431143, 0x76fc93b1c7c73bc7, 0xb32be54ffcfcd7fc, 0x2014082404041004,
    0xb208a2e351515951, 0xbcc72f2599995e99, 0x4fc4da226d6da96d, 0x68391a650d0d340d,
    0x8335e979fafacffa, 0xb684a369dfdf5bdf, 0xd79bfca97e7ee57e, 0x3db4481924249024,
    0xc5d776fe3b3bec3b, 0x313d4b9aabab96ab, 0x3ed181f0cece1fce, 0x8855229911114411,
    0x0c8903838f8f068f, 0x4a6b9c044e4e254e, 0xd1517366b7b7e6b7, 0x0b60cbe0ebeb8beb,
    0xfdcc78c13c3cf03c, 0x7cbf1ffd81813e81, 0xd4fe354094946a94, 0xeb0cf31cf7f7fbf7,
    0xa1676f18b9b9deb9, 0x985f268b13134c13, 0x7d9c58512c2cb02c, 0xd6b8bb05d3d36bd3,
    0x6b5cd38ce7e7bbe7, 0x57cbdc396e6ea56e, 0x6ef395aac4c437c4, 0x180f061b03030c03,
    0x8a13acdc56564556, 0x1a49885e44440d44, 0xdf9efea07f7fe17f, 0x21374f88a9a99ea9,
    0x4d8254672a2aa82a, 0xb16d6b0abbbbd6bb, 0x46e29f87c1c123c1, 0xa202a6f153535153,
    0xae8ba572dcdc57dc, 0x582716530b0b2c0b, 0x9cd327019d9d4e9d, 0x47c1d82b6c6cad6c,
    0x95f562a43131c431, 0x87b9e8f37474cd74, 0xe309f115f6f6fff6, 0x0a438c4c46460546,
    0x092645a5acac8aac, 0x3c970fb589891e89, 0xa04428b414145014, 0x5b42dfbae1e1a3e1,
    0xb04e2ca616165816, 0xcdd274f73a3ae83a, 0x6fd0d2066969b969, 0x482d124109092409,
    0xa7ade0d77070dd70, 0xd954716fb6b6e2b6, 0xceb7bd1ed0d067d0, 0x3b7ec7d6eded93ed,
    0x2edb85e2cccc17cc, 0x2a57846842421542, 0xb4c22d2c98985a98, 0x490e55eda4a4aaa4,
    0x5d8850752828a028, 0xda31b8865c5c6d5c, 0x933fed6bf8f8c7f8, 0x44a411c286862286,
]
C5 = [
    0x18c07830d8181860, 0x2305af462623238c, 0xc67ef991b8c6c63f, 0xe8136fcdfbe8e887,
    0x874ca113cb878726, 0xb8a9626d11b8b8da, 0x0108050209010104, 0x4f426e9e0d4f4f21,
    0x36adee6c9b3636d8, 0xa6590451ffa6a6a2, 0xd2debdb90cd2d26f, 0xf5fb06f70ef5f5f3,
    0x79ef80f2967979f9, 0x6f5fcede306f6fa1, 0x91fcef3f6d91917e, 0x52aa07a4f8525255,
    0x6027fdc04760609d, 0xbc89766535bcbcca, 0x9baccd2b379b9b56, 0x8e048c018a8e8e02,
    0xa371155bd2a3a3b6, 0x0c603c186c0c0c30, 0x7bff8af6847b7bf1, 0x35b5e16a803535d4,
    0x1de8693af51d1d74, 0xe05347ddb3e0e0a7, 0xd7f6acb321d7d77b, 0xc25eed999cc2c22f,
    0x2e6d965c432e2eb8, 0x4b627a96294b4b31, 0xfea321e15dfefedf, 0x578216aed5575741,
    0x15a8412abd151554, 0x779fb6eee87777c1, 0x37a5eb6e923737dc, 0xe57b56d79ee5e5b3,
    0x9f8cd923139f9f46, 0xf0d317fd23f0f0e7, 0x4a6a7f94204a4a35, 0xda9e95a944dada4f,
    0x58fa25b0a258587d, 0xc906ca8fcfc9c903, 0x29558d527c2929a4, 0x0a5022145a0a0a28,
    0xb1e14f7f50b1b1fe, 0xa0691a5dc9a0a0ba, 0x6b7fdad6146b6bb1, 0x855cab17d985852e,
    0xbd8173673cbdbdce, 0x5dd234ba8f5d5d69, 0x1080502090101040, 0xf4f303f507f4f4f7,
    0xcb16c08bddcbcb0b, 0x3eedc67cd33e3ef8, 0x0528110a2d050514, 0x671fe6ce78676781,
    0xe47353d597e4e4b7, 0x2725bb4e0227279c, 0x4132588273414119, 0x8b2c9d0ba78b8b16,
    0xa7510153f6a7a7a6, 0x7dcf94fab27d7de9, 0x95dcfb374995956e, 0xd88e9fad56d8d847,
    0xfb8b30eb70fbfbcb, 0xee2371c1cdeeee9f, 0x7cc791f8bb7c7ced, 0x6617e3cc71666685,
    0xdda68ea77bdddd53, 0x17b84b2eaf17175c, 0x4702468e45474701, 0x9e84dc211a9e9e42,
    0xca1ec589d4caca0f, 0x2d75995a582d2db4, 0xbf9179632ebfbfc6, 0x07381b0e3f07071c,
    0xad012347acadad8e, 0x5aea2fb4b05a5a75, 0x836cb51bef838336, 0x3385ff66b63333cc,
    0x633ff2c65c636391, 0x02100a0412020208, 0xaa39384993aaaa92, 0x71afa8e2de7171d9,
    0xc80ecf8dc6c8c807, 0x19c87d32d1191964, 0x497270923b494939, 0xd9869aaf5fd9d943,
    0xf2c31df931f2f2ef, 0xe34b48dba8e3e3ab, 0x5be22ab6b95b5b71, 0x8834920dbc88881a,
    0x9aa4c8293e9a9a52, 0x262dbe4c0b262698, 0x328dfa64bf3232c8, 0xb0e94a7d59b0b0fa,
    0xe91b6acff2e9e983, 0x0f78331e770f0f3c, 0xd5e6a6b733d5d573, 0x8074ba1df480803a,
    0xbe997c6127bebec2, 0xcd26de87ebcdcd13, 0x34bde468893434d0, 0x487a75903248483d,
    0xffab24e354ffffdb, 0x7af78ff48d7a7af5, 0x90f4ea3d6490907a, 0x5fc23ebe9d5f5f61,
    0x201da0403d202080, 0x6867d5d00f6868bd, 0x1ad07234ca1a1a68, 0xae192c41b7aeae82,
    0xb4c95e757db4b4ea, 0x549a19a8ce54544d, 0x93ece53b7f939376, 0x220daa442f222288,
    0x6407e9c86364648d, 0xf1db12ff2af1f1e3, 0x73bfa2e6cc7373d1, 0x12905a2482121248,
    0x403a5d807a40401d, 0x0840281048080820, 0xc356e89b95c3c32b, 0xec337bc5dfecec97,
    0xdb9690ab4ddbdb4b, 0xa1611f5fc0a1a1be, 0x8d1c8307918d8d0e, 0x3df5c97ac83d3df4,
    0x97ccf1335b979766, 0x0000000000000000, 0xcf36d483f9cfcf1b, 0x2b4587566e2b2bac,
    0x7697b3ece17676c5, 0x8264b019e6828232, 0xd6fea9b128d6d67f, 0x1bd87736c31b1b6c,
    0xb5c15b7774b5b5ee, 0xaf112943beafaf86, 0x6a77dfd41d6a6ab5, 0x50ba0da0ea50505d,
    0x45124c8a57454509, 0xf3cb18fb38f3f3eb, 0x309df060ad3030c0, 0xef2b74c3c4efef9b,
    0x3fe5c37eda3f3ffc, 0x55921caac7555549, 0xa2791059dba2a2b2, 0xea0365c9e9eaea8f,
    0x650fecca6a656589, 0xbab9686903babad2, 0x2f65935e4a2f2fbc, 0xc04ee79d8ec0c027,
    0xdebe81a160dede5f, 0x1ce06c38fc1c1c70, 0xfdbb2ee746fdfdd3, 0x4d52649a1f4d4d29,
    0x92e4e03976929272, 0x758fbceafa7575c9, 0x06301e0c36060618, 0x8a249809ae8a8a12,
    0xb2f940794bb2b2f2, 0xe66359d185e6e6bf, 0x0e70361c7e0e0e38, 0x1ff8633ee71f1f7c,
    0x6237f7c455626295, 0xd4eea3b53ad4d477, 0xa829324d81a8a89a, 0x96c4f43152969662,
    0xf99b3aef62f9f9c3, 0xc566f697a3c5c533, 0x2535b14a10252594, 0x59f220b2ab595979,
    0x8454ae15d084842a, 0x72b7a7e4c57272d5, 0x39d5dd72ec3939e4, 0x4c5a6198164c4c2d,
    0x5eca3bbc945e5e65, 0x78e785f09f7878fd, 0x38ddd870e53838e0, 0x8c148605988c8c0a,
    0xd1c6b2bf17d1d163, 0xa5410b57e4a5a5ae, 0xe2434dd9a1e2e2af, 0x612ff8c24e616199,
    0xb3f1457b42b3b3f6, 0x2115a54234212184, 0x9c94d625089c9c4a, 0x1ef0663cee1e1e78,
    0x4322528661434311, 0xc776fc93b1c7c73b, 0xfcb32be54ffcfcd7, 0x0420140824040410,
    0x51b208a2e3515159, 0x99bcc72f2599995e, 0x6d4fc4da226d6da9, 0x0d68391a650d0d34,
    0xfa8335e979fafacf, 0xdfb684a369dfdf5b, 0x7ed79bfca97e7ee5, 0x243db44819242490,
    0x3bc5d776fe3b3bec, 0xab313d4b9aabab96, 0xce3ed181f0cece1f, 0x1188552299111144,
    0x8f0c8903838f8f06, 0x4e4a6b9c044e4e25, 0xb7d1517366b7b7e6, 0xeb0b60cbe0ebeb8b,
    0x3cfdcc78c13c3cf0, 0x817cbf1ffd81813e, 0x94d4fe354094946a, 0xf7eb0cf31cf7f7fb,
    0xb9a1676f18b9b9de, 0x13985f268b13134c, 0x2c7d9c58512c2cb0, 0xd3d6b8bb05d3d36b,
    0xe76b5cd38ce7e7bb, 0x6e57cbdc396e6ea5, 0xc46ef395aac4c437, 0x03180f061b03030c,
    0x568a13acdc565645, 0x441a49885e44440d, 0x7fdf9efea07f7fe1, 0xa921374f88a9a99e,
    0x2a4d8254672a2aa8, 0xbbb16d6b0abbbbd6, 0xc146e29f87c1c123, 0x53a202a6f1535351,
    0xdcae8ba572dcdc57, 0x0b582716530b0b2c, 0x9d9cd327019d9d4e, 0x6c47c1d82b6c6cad,
    0x3195f562a43131c4, 0x7487b9e8f37474cd, 0xf6e309f115f6f6ff, 0x460a438c4c464605,
    0xac092645a5acac8a, 0x893c970fb589891e, 0x14a04428b4141450, 0xe15b42dfbae1e1a3,
    0x16b04e2ca6161658, 0x3acdd274f73a3ae8, 0x696fd0d2066969b9, 0x09482d1241090924,
    0x70a7ade0d77070dd, 0xb6d954716fb6b6e2, 0xd0ceb7bd1ed0d067, 0xed3b7ec7d6eded93,
    0xcc2edb85e2cccc17, 0x422a578468424215, 0x98b4c22d2c98985a, 0xa4490e55eda4a4aa,
    0x285d8850752828a0, 0x5cda31b8865c5c6d, 0xf8933fed6bf8f8c7, 0x8644a411c2868622,
]
C6 = [
    0x6018c07830d81818, 0x8c2305af46262323, 0x3fc67ef991b8c6c6, 0x87e8136fcdfbe8e8,
    0x26874ca113cb8787, 0xdab8a9626d11b8b8, 0x0401080502090101, 0x214f426e9e0d4f4f,
    0xd836adee6c9b3636, 0xa2a6590451ffa6a6, 0x6fd2debdb90cd2d2, 0xf3f5fb06f70ef5f5,
    0xf979ef80f2967979, 0xa16f5fcede306f6f, 0x7e91fcef3f6d9191, 0x5552aa07a4f85252,
    0x9d6027fdc0476060, 0xcabc89766535bcbc, 0x569baccd2b379b9b, 0x028e048c018a8e8e,
    0xb6a371155bd2a3a3, 0x300c603c186c0c0c, 0xf17bff8af6847b7b, 0xd435b5e16a803535,
    0x741de8693af51d1d, 0xa7e05347ddb3e0e0, 0x7bd7f6acb321d7d7, 0x2fc25eed999cc2c2,
    0xb82e6d965c432e2e, 0x314b627a96294b4b, 0xdffea321e15dfefe, 0x41578216aed55757,
    0x5415a8412abd1515, 0xc1779fb6eee87777, 0xdc37a5eb6e923737, 0xb3e57b56d79ee5e5,
    0x469f8cd923139f9f, 0xe7f0d317fd23f0f0, 0x354a6a7f94204a4a, 0x4fda9e95a944dada,
    0x7d58fa25b0a25858, 0x03c906ca8fcfc9c9, 0xa429558d527c2929, 0x280a5022145a0a0a,
    0xfeb1e14f7f50b1b1, 0xbaa0691a5dc9a0a0, 0xb16b7fdad6146b6b, 0x2e855cab17d98585,
    0xcebd8173673cbdbd, 0x695dd234ba8f5d5d, 0x4010805020901010, 0xf7f4f303f507f4f4,
    0x0bcb16c08bddcbcb, 0xf83eedc67cd33e3e, 0x140528110a2d0505, 0x81671fe6ce786767,
    0xb7e47353d597e4e4, 0x9c2725bb4e022727, 0x1941325882734141, 0x168b2c9d0ba78b8b,
    0xa6a7510153f6a7a7, 0xe97dcf94fab27d7d, 0x6e95dcfb37499595, 0x47d88e9fad56d8d8,
    0xcbfb8b30eb70fbfb, 0x9fee2371c1cdeeee, 0xed7cc791f8bb7c7c, 0x856617e3cc716666,
    0x53dda68ea77bdddd, 0x5c17b84b2eaf1717, 0x014702468e454747, 0x429e84dc211a9e9e,
    0x0fca1ec589d4caca, 0xb42d75995a582d2d, 0xc6bf9179632ebfbf, 0x1c07381b0e3f0707,
    0x8ead012347acadad, 0x755aea2fb4b05a5a, 0x36836cb51bef8383, 0xcc3385ff66b63333,
    0x91633ff2c65c6363, 0x0802100a04120202, 0x92aa39384993aaaa, 0xd971afa8e2de7171,
    0x07c80ecf8dc6c8c8, 0x6419c87d32d11919, 0x39497270923b4949, 0x43d9869aaf5fd9d9,
    0xeff2c31df931f2f2, 0xabe34b48dba8e3e3, 0x715be22ab6b95b5b, 0x1a8834920dbc8888,
    0x529aa4c8293e9a9a, 0x98262dbe4c0b2626, 0xc8328dfa64bf3232, 0xfab0e94a7d59b0b0,
    0x83e91b6acff2e9e9, 0x3c0f78331e770f0f, 0x73d5e6a6b733d5d5, 0x3a8074ba1df48080,
    0xc2be997c6127bebe, 0x13cd26de87ebcdcd, 0xd034bde468893434, 0x3d487a7590324848,
    0xdbffab24e354ffff, 0xf57af78ff48d7a7a, 0x7a90f4ea3d649090, 0x615fc23ebe9d5f5f,
    0x80201da0403d2020, 0xbd6867d5d00f6868, 0x681ad07234ca1a1a, 0x82ae192c41b7aeae,
    0xeab4c95e757db4b4, 0x4d549a19a8ce5454, 0x7693ece53b7f9393, 0x88220daa442f2222,
    0x8d6407e9c8636464, 0xe3f1db12ff2af1f1, 0xd173bfa2e6cc7373, 0x4812905a24821212,
    0x1d403a5d807a4040, 0x2008402810480808, 0x2bc356e89b95c3c3, 0x97ec337bc5dfecec,
    0x4bdb9690ab4ddbdb, 0xbea1611f5fc0a1a1, 0x0e8d1c8307918d8d, 0xf43df5c97ac83d3d,
    0x6697ccf1335b9797, 0x0000000000000000, 0x1bcf36d483f9cfcf, 0xac2b4587566e2b2b,
    0xc57697b3ece17676, 0x328264b019e68282, 0x7fd6fea9b128d6d6, 0x6c1bd87736c31b1b,
    0xeeb5c15b7774b5b5, 0x86af112943beafaf, 0xb56a77dfd41d6a6a, 0x5d50ba0da0ea5050,
    0x0945124c8a574545, 0xebf3cb18fb38f3f3, 0xc0309df060ad3030, 0x9bef2b74c3c4efef,
    0xfc3fe5c37eda3f3f, 0x4955921caac75555, 0xb2a2791059dba2a2, 0x8fea0365c9e9eaea,
    0x89650fecca6a6565, 0xd2bab9686903baba, 0xbc2f65935e4a2f2f, 0x27c04ee79d8ec0c0,
    0x5fdebe81a160dede, 0x701ce06c38fc1c1c, 0xd3fdbb2ee746fdfd, 0x294d52649a1f4d4d,
    0x7292e4e039769292, 0xc9758fbceafa7575, 0x1806301e0c360606, 0x128a249809ae8a8a,
    0xf2b2f940794bb2b2, 0xbfe66359d185e6e6, 0x380e70361c7e0e0e, 0x7c1ff8633ee71f1f,
    0x956237f7c4556262, 0x77d4eea3b53ad4d4, 0x9aa829324d81a8a8, 0x6296c4f431529696,
    0xc3f99b3aef62f9f9, 0x33c566f697a3c5c5, 0x942535b14a102525, 0x7959f220b2ab5959,
    0x2a8454ae15d08484, 0xd572b7a7e4c57272, 0xe439d5dd72ec3939, 0x2d4c5a6198164c4c,
    0x655eca3bbc945e5e, 0xfd78e785f09f7878, 0xe038ddd870e53838, 0x0a8c148605988c8c,
    0x63d1c6b2bf17d1d1, 0xaea5410b57e4a5a5, 0xafe2434dd9a1e2e2, 0x99612ff8c24e6161,
    0xf6b3f1457b42b3b3, 0x842115a542342121, 0x4a9c94d625089c9c, 0x781ef0663cee1e1e,
    0x1143225286614343, 0x3bc776fc93b1c7c7, 0xd7fcb32be54ffcfc, 0x1004201408240404,
    0x5951b208a2e35151, 0x5e99bcc72f259999, 0xa96d4fc4da226d6d, 0x340d68391a650d0d,
    0xcffa8335e979fafa, 0x5bdfb684a369dfdf, 0xe57ed79bfca97e7e, 0x90243db448192424,
    0xec3bc5d776fe3b3b, 0x96ab313d4b9aabab, 0x1fce3ed181f0cece, 0x4411885522991111,
    0x068f0c8903838f8f, 0x254e4a6b9c044e4e, 0xe6b7d1517366b7b7, 0x8beb0b60cbe0ebeb,
    0xf03cfdcc78c13c3c, 0x3e817cbf1ffd8181, 0x6a94d4fe35409494, 0xfbf7eb0cf31cf7f7,
    0xdeb9a1676f18b9b9, 0x4c13985f268b1313, 0xb02c7d9c58512c2c, 0x6bd3d6b8bb05d3d3,
    0xbbe76b5cd38ce7e7, 0xa56e57cbdc396e6e, 0x37c46ef395aac4c4, 0x0c03180f061b0303,
    0x45568a13acdc5656, 0x0d441a49885e4444, 0xe17fdf9efea07f7f, 0x9ea921374f88a9a9,
    0xa82a4d8254672a2a, 0xd6bbb16d6b0abbbb, 0x23c146e29f87c1c1, 0x5153a202a6f15353,
    0x57dcae8ba572dcdc, 0x2c0b582716530b0b, 0x4e9d9cd327019d9d, 0xad6c47c1d82b6c6c,
    0xc43195f562a43131, 0xcd7487b9e8f37474, 0xfff6e309f115f6f6, 0x05460a438c4c4646,
    0x8aac092645a5acac, 0x1e893c970fb58989, 0x5014a04428b41414, 0xa3e15b42dfbae1e1,
    0x5816b04e2ca61616, 0xe83acdd274f73a3a, 0xb9696fd0d2066969, 0x2409482d12410909,
    0xdd70a7ade0d77070, 0xe2b6d954716fb6b6, 0x67d0ceb7bd1ed0d0, 0x93ed3b7ec7d6eded,
    0x17cc2edb85e2cccc, 0x15422a5784684242, 0x5a98b4c22d2c9898, 0xaaa4490e55eda4a4,
    0xa0285d8850752828, 0x6d5cda31b8865c5c, 0xc7f8933fed6bf8f8, 0x228644a411c28686,
]
C7 = [
    0x186018c07830d818, 0x238c2305af462623, 0xc63fc67ef991b8c6, 0xe887e8136fcdfbe8,
    0x8726874ca113cb87, 0xb8dab8a9626d11b8, 0x0104010805020901, 0x4f214f426e9e0d4f,
    0x36d836adee6c9b36, 0xa6a2a6590451ffa6, 0xd26fd2debdb90cd2, 0xf5f3f5fb06f70ef5,
    0x79f979ef80f29679, 0x6fa16f5fcede306f, 0x917e91fcef3f6d91, 0x525552aa07a4f852,
    0x609d6027fdc04760, 0xbccabc89766535bc, 0x9b569baccd2b379b, 0x8e028e048c018a8e,
    0xa3b6a371155bd2a3, 0x0c300c603c186c0c, 0x7bf17bff8af6847b, 0x35d435b5e16a8035,
    0x1d741de8693af51d, 0xe0a7e05347ddb3e0, 0xd77bd7f6acb321d7, 0xc22fc25eed999cc2,
    0x2eb82e6d965c432e, 0x4b314b627a96294b, 0xfedffea321e15dfe, 0x5741578216aed557,
    0x155415a8412abd15, 0x77c1779fb6eee877, 0x37dc37a5eb6e9237, 0xe5b3e57b56d79ee5,
    0x9f469f8cd923139f, 0xf0e7f0d317fd23f0, 0x4a354a6a7f94204a, 0xda4fda9e95a944da,
    0x587d58fa25b0a258, 0xc903c906ca8fcfc9, 0x29a429558d527c29, 0x0a280a5022145a0a,
    0xb1feb1e14f7f50b1, 0xa0baa0691a5dc9a0, 0x6bb16b7fdad6146b, 0x852e855cab17d985,
    0xbdcebd8173673cbd, 0x5d695dd234ba8f5d, 0x1040108050209010, 0xf4f7f4f303f507f4,
    0xcb0bcb16c08bddcb, 0x3ef83eedc67cd33e, 0x05140528110a2d05, 0x6781671fe6ce7867,
    0xe4b7e47353d597e4, 0x279c2725bb4e0227, 0x4119413258827341, 0x8b168b2c9d0ba78b,
    0xa7a6a7510153f6a7, 0x7de97dcf94fab27d, 0x956e95dcfb374995, 0xd847d88e9fad56d8,
    0xfbcbfb8b30eb70fb, 0xee9fee2371c1cdee, 0x7ced7cc791f8bb7c, 0x66856617e3cc7166,
    0xdd53dda68ea77bdd, 0x175c17b84b2eaf17, 0x47014702468e4547, 0x9e429e84dc211a9e,
    0xca0fca1ec589d4ca, 0x2db42d75995a582d, 0xbfc6bf9179632ebf, 0x071c07381b0e3f07,
    0xad8ead012347acad, 0x5a755aea2fb4b05a, 0x8336836cb51bef83, 0x33cc3385ff66b633,
    0x6391633ff2c65c63, 0x020802100a041202, 0xaa92aa39384993aa, 0x71d971afa8e2de71,
    0xc807c80ecf8dc6c8, 0x196419c87d32d119, 0x4939497270923b49, 0xd943d9869aaf5fd9,
    0xf2eff2c31df931f2, 0xe3abe34b48dba8e3, 0x5b715be22ab6b95b, 0x881a8834920dbc88,
    0x9a529aa4c8293e9a, 0x2698262dbe4c0b26, 0x32c8328dfa64bf32, 0xb0fab0e94a7d59b0,
    0xe983e91b6acff2e9, 0x0f3c0f78331e770f, 0xd573d5e6a6b733d5, 0x803a8074ba1df480,
    0xbec2be997c6127be, 0xcd13cd26de87ebcd, 0x34d034bde4688934, 0x483d487a75903248,
    0xffdbffab24e354ff, 0x7af57af78ff48d7a, 0x907a90f4ea3d6490, 0x5f615fc23ebe9d5f,
    0x2080201da0403d20, 0x68bd6867d5d00f68, 0x1a681ad07234ca1a, 0xae82ae192c41b7ae,
    0xb4eab4c95e757db4, 0x544d549a19a8ce54, 0x937693ece53b7f93, 0x2288220daa442f22,
    0x648d6407e9c86364, 0xf1e3f1db12ff2af1, 0x73d173bfa2e6cc73, 0x124812905a248212,
    0x401d403a5d807a40, 0x0820084028104808, 0xc32bc356e89b95c3, 0xec97ec337bc5dfec,
    0xdb4bdb9690ab4ddb, 0xa1bea1611f5fc0a1, 0x8d0e8d1c8307918d, 0x3df43df5c97ac83d,
    0x976697ccf1335b97, 0x0000000000000000, 0xcf1bcf36d483f9cf, 0x2bac2b4587566e2b,
    0x76c57697b3ece176, 0x82328264b019e682, 0xd67fd6fea9b128d6, 0x1b6c1bd87736c31b,
    0xb5eeb5c15b7774b5, 0xaf86af112943beaf, 0x6ab56a77dfd41d6a, 0x505d50ba0da0ea50,
    0x450945124c8a5745, 0xf3ebf3cb18fb38f3, 0x30c0309df060ad30, 0xef9bef2b74c3c4ef,
    0x3ffc3fe5c37eda3f, 0x554955921caac755, 0xa2b2a2791059dba2, 0xea8fea0365c9e9ea,
    0x6589650fecca6a65, 0xbad2bab9686903ba, 0x2fbc2f65935e4a2f, 0xc027c04ee79d8ec0,
    0xde5fdebe81a160de, 0x1c701ce06c38fc1c, 0xfdd3fdbb2ee746fd, 0x4d294d52649a1f4d,
    0x927292e4e0397692, 0x75c9758fbceafa75, 0x061806301e0c3606, 0x8a128a249809ae8a,
    0xb2f2b2f940794bb2, 0xe6bfe66359d185e6, 0x0e380e70361c7e0e, 0x1f7c1ff8633ee71f,
    0x62956237f7c45562, 0xd477d4eea3b53ad4, 0xa89aa829324d81a8, 0x966296c4f4315296,
    0xf9c3f99b3aef62f9, 0xc533c566f697a3c5, 0x25942535b14a1025, 0x597959f220b2ab59,
    0x842a8454ae15d084, 0x72d572b7a7e4c572, 0x39e439d5dd72ec39, 0x4c2d4c5a6198164c,
    0x5e655eca3bbc945e, 0x78fd78e785f09f78, 0x38e038ddd870e538, 0x8c0a8c148605988c,
    0xd163d1c6b2bf17d1, 0xa5aea5410b57e4a5, 0xe2afe2434dd9a1e2, 0x6199612ff8c24e61,
    0xb3f6b3f1457b42b3, 0x21842115a5423421, 0x9c4a9c94d625089c, 0x1e781ef0663cee1e,
    0x4311432252866143, 0xc73bc776fc93b1c7, 0xfcd7fcb32be54ffc, 0x0410042014082404,
    0x515951b208a2e351, 0x995e99bcc72f2599, 0x6da96d4fc4da226d, 0x0d340d68391a650d,
    0xfacffa8335e979fa, 0xdf5bdfb684a369df, 0x7ee57ed79bfca97e, 0x2490243db4481924,
    0x3bec3bc5d776fe3b, 0xab96ab313d4b9aab, 0xce1fce3ed181f0ce, 0x1144118855229911,
    0x8f068f0c8903838f, 0x4e254e4a6b9c044e, 0xb7e6b7d1517366b7, 0xeb8beb0b60cbe0eb,
    0x3cf03cfdcc78c13c, 0x813e817cbf1ffd81, 0x946a94d4fe354094, 0xf7fbf7eb0cf31cf7,
    0xb9deb9a1676f18b9, 0x134c13985f268b13, 0x2cb02c7d9c58512c, 0xd36bd3d6b8bb05d3,
    0xe7bbe76b5cd38ce7, 0x6ea56e57cbdc396e, 0xc437c46ef395aac4, 0x030c03180f061b03,
    0x5645568a13acdc56, 0x440d441a49885e44, 0x7fe17fdf9efea07f, 0xa99ea921374f88a9,
    0x2aa82a4d8254672a, 0xbbd6bbb16d6b0abb, 0xc123c146e29f87c1, 0x535153a202a6f153,
    0xdc57dcae8ba572dc, 0x0b2c0b582716530b, 0x9d4e9d9cd327019d, 0x6cad6c47c1d82b6c,
    0x31c43195f562a431, 0x74cd7487b9e8f374, 0xf6fff6e309f115f6, 0x4605460a438c4c46,
    0xac8aac092645a5ac, 0x891e893c970fb589, 0x145014a04428b414, 0xe1a3e15b42dfbae1,
    0x165816b04e2ca616, 0x3ae83acdd274f73a, 0x69b9696fd0d20669, 0x092409482d124109,
    0x70dd70a7ade0d770, 0xb6e2b6d954716fb6, 0xd067d0ceb7bd1ed0, 0xed93ed3b7ec7d6ed,
    0xcc17cc2edb85e2cc, 0x4215422a57846842, 0x985a98b4c22d2c98, 0xa4aaa4490e55eda4,
    0x28a0285d88507528, 0x5c6d5cda31b8865c, 0xf8c7f8933fed6bf8, 0x86228644a411c286,
]

rc = [
    0x0000000000000000,
    0x1823c6e887b8014f,
    0x36a6d2f5796f9152,
    0x60bc9b8ea30c7b35,
    0x1de0d7c22e4bfe57,
    0x157737e59ff04ada,
    0x58c9290ab1a06b85,
    0xbd5d10f4cb3e0567,
    0xe427418ba77d95d8,
    0xfbee7c66dd17479e,
    0xca2dbf07ad5a8333
]


class WhirlpoolStruct(object):
    def __init__(self):
        self.bitLength = [0] * 32
        self.buffer = [0] * DIGESTBYTES
        self.bufferBits = 0
        self.bufferPos = 0
        self.hash = [0] * 8
        self.prev_sourceBits = 0


def WhirlpoolAdd(source, sourceBits, ctx):
    source = [ord(s) & 0xff for s in source]

    carry = 0
    value = ctx.prev_sourceBits + sourceBits
    ctx.prev_sourceBits += sourceBits
    i = 31
    ctx.bitLength = [0] * 32
    while i >= 0 and value != 0:
        carry += ctx.bitLength[i] + ((value % 0x100000000) & 0xff)
        ctx.bitLength[i] = carry % 0x100
        carry >>= 8
        value >>= 8
        i -= 1
    bufferBits = ctx.bufferBits
    bufferPos = ctx.bufferPos
    sourcePos = 0
    sourceGap = (8 - (sourceBits & 7)) & 7
    bufferRem = ctx.bufferBits & 7
    buffr = ctx.buffer

    while sourceBits > 8:
        b = ((source[sourcePos] << sourceGap) & 0xff) | ((source[sourcePos + 1] & 0xff) >> (8 - sourceGap))
        buffr[bufferPos] |= (b >> bufferRem) % 0x100
        bufferPos += 1
        bufferBits += 8 - bufferRem
        if bufferBits == DIGESTBITS or bufferPos == DIGESTBYTES:
            processBuffer(ctx)
            bufferBits = 0
            bufferPos = 0

        buffr[bufferPos] = b << (8 - bufferRem)
        bufferBits += bufferRem

        sourceBits -= 8
        sourcePos += 1

    b = (source[sourcePos] << sourceGap) & 0xff
    buffr[bufferPos] |= b >> bufferRem
    if bufferRem + sourceBits < 8:
        bufferBits += sourceBits
    else:
        bufferPos += 1
        bufferBits += 8 - bufferRem
        sourceBits -= 8 - bufferRem
        if bufferBits == DIGESTBITS or bufferPos == DIGESTBYTES:
            processBuffer(ctx)
            bufferBits = 0
            bufferPos = 0
        buffr[bufferPos] = b << (8 - bufferRem)
        bufferBits += sourceBits
    ctx.bufferBits += bufferBits
    ctx.bufferPos = bufferPos


def WhirlpoolFinalize(ctx):
    bufferPos = ctx.bufferPos
    ctx.buffer[bufferPos] |= 0x80 >> (ctx.bufferBits & 7)
    bufferPos += 1
    if bufferPos > 32:
        if bufferPos < DIGESTBYTES:
            for i in xrange(DIGESTBYTES - bufferPos):
                ctx.buffer[bufferPos + i] = 0
        processBuffer(ctx)
        bufferPos = 0
    if bufferPos < 32:
        for i in xrange(32 - bufferPos):
            ctx.buffer[bufferPos + i] = 0
    bufferPos = 32
    for i in xrange(32):
        ctx.buffer[32 + i] = ctx.bitLength[i]
    processBuffer(ctx)
    digest = ''
    for i in xrange(8):
        digest += chr((ctx.hash[i] >> 56) % 0x100)
        digest += chr((ctx.hash[i] >> 48) % 0x100)
        digest += chr((ctx.hash[i] >> 40) % 0x100)
        digest += chr((ctx.hash[i] >> 32) % 0x100)
        digest += chr((ctx.hash[i] >> 24) % 0x100)
        digest += chr((ctx.hash[i] >> 16) % 0x100)
        digest += chr((ctx.hash[i] >> 8) % 0x100)
        digest += chr((ctx.hash[i]) % 0x100)
    ctx.bufferPos = bufferPos
    return digest


def CDo(buf, a0, a1, a2, a3, a4, a5, a6, a7):
    return C0[((buf[a0] >> 56) % 0x100000000) & 0xff] ^ \
           C1[((buf[a1] >> 48) % 0x100000000) & 0xff] ^ \
           C2[((buf[a2] >> 40) % 0x100000000) & 0xff] ^ \
           C3[((buf[a3] >> 32) % 0x100000000) & 0xff] ^ \
           C4[((buf[a4] >> 24) % 0x100000000) & 0xff] ^ \
           C5[((buf[a5] >> 16) % 0x100000000) & 0xff] ^ \
           C6[((buf[a6] >> 8) % 0x100000000) & 0xff] ^ \
           C7[((buf[a7] >> 0) % 0x100000000) & 0xff]


def processBuffer(ctx):
    i, r = 0, 0
    K = [0] * 8
    block = [0] * 8
    state = [0] * 8
    L = [0] * 8
    buffr = ctx.buffer

    buf_cnt = 0
    for i in xrange(8):
        block[i] = ((buffr[buf_cnt + 0] & 0xff) << 56) ^ \
                   ((buffr[buf_cnt + 1] & 0xff) << 48) ^ \
                   ((buffr[buf_cnt + 2] & 0xff) << 40) ^ \
                   ((buffr[buf_cnt + 3] & 0xff) << 32) ^ \
                   ((buffr[buf_cnt + 4] & 0xff) << 24) ^ \
                   ((buffr[buf_cnt + 5] & 0xff) << 16) ^ \
                   ((buffr[buf_cnt + 6] & 0xff) << 8) ^ \
                   ((buffr[buf_cnt + 7] & 0xff) << 0)
        buf_cnt += 8
    for i in xrange(8):
        K[i] = ctx.hash[i]
        state[i] = block[i] ^ K[i]

    for r in xrange(1, R + 1):
        L[0] = CDo(K, 0, 7, 6, 5, 4, 3, 2, 1) ^ rc[r]
        L[1] = CDo(K, 1, 0, 7, 6, 5, 4, 3, 2)
        L[2] = CDo(K, 2, 1, 0, 7, 6, 5, 4, 3)
        L[3] = CDo(K, 3, 2, 1, 0, 7, 6, 5, 4)
        L[4] = CDo(K, 4, 3, 2, 1, 0, 7, 6, 5)
        L[5] = CDo(K, 5, 4, 3, 2, 1, 0, 7, 6)
        L[6] = CDo(K, 6, 5, 4, 3, 2, 1, 0, 7)
        L[7] = CDo(K, 7, 6, 5, 4, 3, 2, 1, 0)
        for i in xrange(8):
            K[i] = L[i]
        L[0] = CDo(state, 0, 7, 6, 5, 4, 3, 2, 1) ^ K[0]
        L[1] = CDo(state, 1, 0, 7, 6, 5, 4, 3, 2) ^ K[1]
        L[2] = CDo(state, 2, 1, 0, 7, 6, 5, 4, 3) ^ K[2]
        L[3] = CDo(state, 3, 2, 1, 0, 7, 6, 5, 4) ^ K[3]
        L[4] = CDo(state, 4, 3, 2, 1, 0, 7, 6, 5) ^ K[4]
        L[5] = CDo(state, 5, 4, 3, 2, 1, 0, 7, 6) ^ K[5]
        L[6] = CDo(state, 6, 5, 4, 3, 2, 1, 0, 7) ^ K[6]
        L[7] = CDo(state, 7, 6, 5, 4, 3, 2, 1, 0) ^ K[7]
        for i in xrange(8):
            state[i] = L[i]
    # apply the Miyaguchi-Preneel compression function
    for i in xrange(8):
        ctx.hash[i] ^= state[i] ^ block[i]
    return


def test_whirlpool_hash():
    # Tests
    assert whirlpool('The quick brown fox jumps over the lazy dog').hexdigest() == \
        'b97de512e91e3828b40d2b0fdce9ceb3c4a71f9bea8d88e75c4fa854df36725fd2b52eb6544edcacd6f8beddfea403cb55ae31f03ad62a5ef54e42ee82c3fb35'
    assert whirlpool('The quick brown fox jumps over the lazy eog').hexdigest() == \
        'c27ba124205f72e6847f3e19834f925cc666d0974167af915bb462420ed40cc50900d85a1f923219d832357750492d5c143011a76988344c2635e69d06f2d38c'
    assert whirlpool('').hexdigest() == \
        '19fa61d75522a4669b44e39c1d2e1726c530232130d407f89afee0964997f7a73e83be698b288febcf88e3e03c4f0757ea8964e59b63d93708b138cc42a66eb3'
    # Chunked
    test = whirlpool('The quick brown fox jumps over the lazy dog')
    test.update('The quick brown fox jumps over the lazy dog')
    test.update('The quick brown fox jumps over the lazy dog')
    test.update('The quick brown fox jumps over the lazy dog')
    test.update('The quick brown fox jumps over the lazy dog')
    assert test.hexdigest() == \
        'f4d0e0d7a9a47b9d24c94cf608348147fb5725e4ba40104b91b2bd43e99c9b978c12a2e051cb05d15eeb8f7447b238c4138c1a10db86f4b811506744b19cefaf'

########NEW FILE########
