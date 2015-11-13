__FILENAME__ = bookmarks
# -*- coding: utf-8 -*-

#  Copyright (C) 2008 - Eugene Khorev
#
#  This program is free software; you can redistribute it and/or modify
#  it under the terms of the GNU General Public License as published by
#  the Free Software Foundation; either version 2 of the License, or
#  (at your option) any later version.
#
#  This program is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU General Public License for more details.
#
#  You should have received a copy of the GNU General Public License
#  along with this program; if not, write to the Free Software
#  Foundation, Inc., 59 Temple Place, Suite 330,
#  Boston, MA 02111-1307, USA.

import pygtk
pygtk.require("2.0")
import gtk

class bookmark_list(object):
    
    def __init__(self, config):
        self._list = {}
        
        self._config = config

        # Load bookmarks from configuration
        sections = config.sections()

        if config.has_section("common"):
            index = sections.index("common")
            del sections[index]
        
        # Create an empty store for the documents that have no bookmarks yet
        self._empty_store = gtk.ListStore(int, str)
        
        for sec in sections:
            store = gtk.ListStore(int, str)
            
            self._list[sec] = {"store": store, "iters": {}}
            
            for line in config.options(sec):
                comment = config.get(sec, line)
                self._list[sec]["iters"][int(line)] = store.append([int(line), comment])
            
            # Setup sorting
            store.set_sort_func(0, self._line_sort)
            store.set_sort_column_id(0, gtk.SORT_ASCENDING)
            
    def get_store(self, uri): # Gets tree store for an uri
        try:
            return self._list[uri]["store"]
        except:
            return self._empty_store
        
    def get_iters(self, uri):
        try:
            return self._list[uri]["iters"]
        except:
            return {}
        
    def add(self, uri, line, source, comment = ""): # Adds a line for an uri (returns True on success)
        exists = self.exists(uri, line)
        
        if comment == "":
            content = source
        else:
            content = comment
        
        if not exists:
            if self._list.has_key(uri):
                self._list[uri]["iters"][line] = self._list[uri]["store"].append([line, content])
            else:
                store = gtk.ListStore(int, str)
                self._list[uri] = {"store": store, "iters": {line: store.append([line, content])}}    
                
                # Setup sorting
                store.set_sort_func(0, self._line_sort)
                store.set_sort_column_id(0, gtk.SORT_ASCENDING)

                # Create uri section in configuration
                self._config.add_section(uri)
            
            # Upadate configuration
            self._config.set(uri, str(line), comment)
        
        return not exists
        
    def delete(self, uri, line = None): # Deletes a line or an entire uri (returns True on success)
        if line:
            exists = self.exists(uri, line)
            
            if exists:
                self._list[uri]["store"].remove(self._list[uri]["iters"][line])
                del self._list[uri]["iters"][line]
                
                # Upadate configuration
                self._config.remove_option(uri, str(line))
                
            return exists
        else:
            try:
                del self._list[uri]
                
                # Upadate configuration
                self._config.remove_section(uri)
                
                return True
            except:
                return False
        
    def exists(self, uri, line): # Returns True if there is a line exists in an uri
        try:
            return self._list[uri]["iters"][line]
        except:
            return False
        
    def toggle(self, uri, line, source, comment = ""): # Adds or removes a line for an uri
        if self.exists(uri, line):
            self.delete(uri, line)
            return False
        else:
            self.add(uri, line, source, comment)
            return True

    def update(self, uri, offset, cur_line, end_line):
        if self._list.has_key(uri):
            iters = {}
            
            keys = self._list[uri]["iters"].keys()
            
            for line in keys:
                row = self._list[uri]["iters"][line]
                
                comment = self._config.get(uri, str(line))
                self._config.remove_option(uri, str(line))

                if line < cur_line:
                    self._list[uri]["store"].set_value(row, 0, line)
                    iters[line] = row
                    
                    # Upadate configuration
                    self._config.set(uri, str(line), comment)
                    
                elif (end_line < 0 and line >= cur_line) or (end_line >= 0 and line > end_line):
                    line = line-offset
                    self._list[uri]["store"].set_value(row, 0, line)
                    iters[line] = row
                    
                    # Upadate configuration
                    self._config.set(uri, str(line), comment)
                    
                else:
                    self._list[uri]["store"].remove(row)
                    
            self._list[uri]["iters"] = iters
            
            return True 
        else:
            return False

    def _line_sort(self, model, line1, line2):
        val1 = model.get_value(line1, 0)
        val2 = model.get_value(line2, 0)

        if val1 < val2:
	        return -1
        if val1 == val2:
	        return 0
        return 1
        
# ex:ts=4:et:

########NEW FILE########
__FILENAME__ = plugin
# -*- coding: utf-8 -*-

#  Copyright (C) 2008 - Eugene Khorev
#
#  This program is free software; you can redistribute it and/or modify
#  it under the terms of the GNU General Public License as published by
#  the Free Software Foundation; either version 2 of the License, or
#  (at your option) any later version.
#
#  This program is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU General Public License for more details.
#
#  You should have received a copy of the GNU General Public License
#  along with this program; if not, write to the Free Software
#  Foundation, Inc., 59 Temple Place, Suite 330,
#  Boston, MA 02111-1307, USA.

import pygtk
pygtk.require("2.0")
import gtk
import gedit
import time
import os
import sys
import gettext
import ConfigParser
import bookmarks
import window_helper

APP_NAME = "plugin"
LOC_PATH = os.path.join(os.path.expanduser("~/.gnome2/gedit/plugins/advanced-bookmarks/lang"))

gettext.find(APP_NAME, LOC_PATH)
gettext.install(APP_NAME, LOC_PATH, True)

class AdvancedBookmarksPlugin(gedit.Plugin):

    def __init__(self):
        gedit.Plugin.__init__(self)
        
        self._instances = {}

        # Setup configuration file path
        conf_path = os.path.join(os.path.expanduser("~/.gnome2/gedit/plugins/"), "advanced-bookmarks/plugin.conf")
        
        # Check if configuration file does not exists
        if not os.path.exists(conf_path):
            # Create configuration file
            conf_file = file(conf_path, "wt")
            conf_file.close()
            
        # Create configuration dictionary
        self.read_config(conf_path)

        # Create bookmark list
        self._bookmarks = bookmarks.bookmark_list(self._config)
        
    def activate(self, window):
        # Create window helper for an instance
        self._instances[window] = window_helper.window_helper(self, window, self._bookmarks, self._config)
        
    def deactivate(self, window):
        self._instances[window].deactivate()
        del self._instances[window]
        
    def update_ui(self, window):
        self._instances[window].update_ui()
                        
    def create_configure_dialog(self):
        # Create configuration dialog
        self._dlg_config_glade = gtk.glade.XML(os.path.dirname( __file__ ) + "/config_dlg.glade")

        # Get dialog window
        self._dlg_config = self._dlg_config_glade.get_widget("config_dialog") 
        
        # Setup signals
        self._dlg_config_glade.signal_autoconnect(self)
        
        # Setup values of dialog widgets
        highlighting = self._config.getboolean("common", "highlighting")
        chk = self._dlg_config_glade.get_widget("chk_highlight")
        chk.set_active(highlighting)
        
        color = self._config.get("common", "highlight_color")
        btn = self._dlg_config_glade.get_widget("btn_color")
        try:
            btn.set_color(gtk.gdk.color_parse(color))
        except:
            btn.set_color(gtk.gdk.color_parse("#FFF0DC"))
        
        return self._dlg_config
        
    def on_btn_cancel_clicked(self, btn):
        self._dlg_config.response(gtk.RESPONSE_CANCEL)
        
    def on_btn_ok_clicked(self, btn):
        self._dlg_config.response(gtk.RESPONSE_OK)
        
    def on_config_dialog_response(self, dlg, res):
        if res == gtk.RESPONSE_OK:
            # Save configuration
            highlight = self._dlg_config_glade.get_widget("chk_highlight").get_active()
            self._config.set("common", "highlighting", highlight and "on" or "off")
            
            color = self._dlg_config_glade.get_widget("btn_color").get_color().to_string()
            self._config.set("common", "highlight_color", color)
            
            self.write_config()
            
            # Remove bookmark markup in all documents if necessary
            for window in self._instances:
                self._instances[window].setup_highlighting(highlight)
            
        dlg.hide()
            
    def read_config(self, conf_path): # Reads configuration from a file
        self._conf_file = file(conf_path, "r+")
        self._config = ConfigParser.ConfigParser()
        self._config.readfp(self._conf_file)
        
        # Check if there is no necessary options in config
        if not self._config.has_section("common"):
            self._config.add_section("common")
        
        if not self._config.has_option("common", "highlighting"):
            self._config.set("common", "highlighting", "on")
        
        if not self._config.has_option("common", "highlight_color"):
            self._config.set("common", "highlight_color", "#FFF0DC")
        
    def write_config(self): # Saves configuration to a file
        self._conf_file.truncate(0)
        self._conf_file.seek(0)

        self._config.write(self._conf_file)
        
#ex:ts=4:et:

########NEW FILE########
__FILENAME__ = toggle_dlg
# -*- coding: utf-8 -*-

#  Copyright (C) 2008 - Eugene Khorev
#
#  This program is free software; you can redistribute it and/or modify
#  it under the terms of the GNU General Public License as published by
#  the Free Software Foundation; either version 2 of the License, or
#  (at your option) any later version.
#
#  This program is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU General Public License for more details.
#
#  You should have received a copy of the GNU General Public License
#  along with this program; if not, write to the Free Software
#  Foundation, Inc., 59 Temple Place, Suite 330,
#  Boston, MA 02111-1307, USA.

import pygtk
pygtk.require("2.0")
import gtk
import gedit
import os

class toggle_dlg(gtk.Dialog):

    def __init__(self, parent, config):
        # Create config diaog window
        title = _("Bookmark properties")
        buttons = (gtk.STOCK_CANCEL, gtk.RESPONSE_CANCEL, gtk.STOCK_OK, gtk.RESPONSE_OK)

        super(toggle_dlg, self).__init__(title, parent, 0, buttons)
        
        self.vbox.set_homogeneous(False)
        
        # Create diaog items
        self._msg = gtk.Label(_("Comment"))
        self._msg.set_property("xalign", 0.0)
        self.vbox.pack_start(self._msg, True, True, 5)
        
        self._input = gtk.Entry()
        self._input.connect("key-press-event", self._on_input_key)
        self.vbox.pack_start(self._input, True, True, 0)
        
        self._note = gtk.Label(_("(leave blank to use source line)"))
        self.vbox.pack_start(self._note, True, True, 5)
        
        self.vbox.show_all()
        
        # Setup configuration dictionary
        self._config = config
    
    def reset(self, comment = ""):#, prompt = True):
        self._input.set_text(comment)
        self._input.grab_focus()
    
    def get_comment(self):
        return self._input.get_text().strip()
    
    def _on_input_key(self, widget, event):
        if event.keyval == gtk.keysyms.Return:
            self.response(gtk.RESPONSE_OK)
    
# ex:ts=4:et:

########NEW FILE########
__FILENAME__ = window_helper
# -*- coding: utf-8 -*-

#  Copyright (C) 2008 - Eugene Khorev
#
#  This program is free software; you can redistribute it and/or modify
#  it under the terms of the GNU General Public License as published by
#  the Free Software Foundation; either version 2 of the License, or
#  (at your option) any later version.
#
#  This program is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU General Public License for more details.
#
#  You should have received a copy of the GNU General Public License
#  along with this program; if not, write to the Free Software
#  Foundation, Inc., 59 Temple Place, Suite 330,
#  Boston, MA 02111-1307, USA.

import pygtk
pygtk.require("2.0")
import gtk
import gedit
import time
import os
import sys
import pango
import bookmarks
import toggle_dlg

class window_helper:
    def __init__(self, plugin, window, bookmarks, config):
        self._window = window
        self._plugin = plugin
        
        self._bookmarks = bookmarks
        self._config = config
        
        self._doc_lines = {}

        # Create icon
        self._icon = gtk.Image()
        self._icon.set_from_icon_name('stock_help-add-bookmark', gtk.ICON_SIZE_MENU)
        
        # Insert main menu items
        self._insert_menu()
        
        # Create bookmark toggle dialog
        self._dlg_toggle = toggle_dlg.toggle_dlg(None, self._config)
        self._dlg_toggle.connect("response", self._on_dlg_toggle_response)
        
        # Create bottom pane tree
        self._tree = gtk.TreeView()
        
        # Create line number column
        self._line_column = gtk.TreeViewColumn(_('Line'))
        self._tree.append_column(self._line_column)
        
        self._line_cell = gtk.CellRendererText()
        self._line_column.pack_start(self._line_cell, True)

        self._line_column.add_attribute(self._line_cell, 'text', 0)
        
        # Create comment column
        self._comment_column = gtk.TreeViewColumn(_('Source / Comment'))
        self._tree.append_column(self._comment_column)
        
        self._comment_cell = gtk.CellRendererText()
        self._comment_column.pack_start(self._comment_cell, True)

        self._comment_column.add_attribute(self._comment_cell, 'text', 1)
        self._comment_column.set_cell_data_func(self._comment_cell, self._render_comment_callback)
        
        # Addtitional settings
        self._tree.set_enable_tree_lines(True)
        self._tree.set_search_column(1)
        self._tree.set_rules_hint(True)
        self._tree.set_grid_lines(gtk.TREE_VIEW_GRID_LINES_BOTH)
        
        # Create bottom pane
        self._pane = gtk.ScrolledWindow()

        # Add tree to bottom pane
        self._pane.add(self._tree);
        self._tree.show()

        # Setup row selection event
        self._tree.connect("row-activated", self._on_row_activated)
        self._tree.connect("cursor-changed", self._on_row_selected)
        self._tree.connect("focus-in-event", self._on_tree_focused)

        # Create popup menu for tree
        self._popup_menu = gtk.Menu()
        
        self._pop_toggle = gtk.MenuItem(_("Toggle bookmark"))
        self._pop_toggle.connect("activate", self._on_toggle_bookmark)
        self._pop_toggle.show()
        self._popup_menu.append(self._pop_toggle)
        
        self._pop_edit = gtk.MenuItem(_("Edit bookmark"))
        self._pop_edit.set_sensitive(False)
        self._pop_edit.connect("activate", self._on_edit_clicked)
        self._pop_edit.show()
        self._popup_menu.append(self._pop_edit)
        
        self._popup_menu.attach_to_widget(self._tree, None)
        self._tree.connect("button-release-event", self._on_tree_clicked)
        
        # Create button boxes
        self._btn_hbox = gtk.HBox(False, 5)
        self._btn_vbox = gtk.VBox(False, 0)

        # Create buttons
        self._btn_toggle = gtk.Button(_("Toggle"))
        self._btn_toggle.set_focus_on_click(False)
        self._btn_toggle.connect("clicked", self._on_toggle_bookmark)
        self._btn_vbox.pack_start(self._btn_toggle, False, False, 5)
        
        self._btn_edit = gtk.Button(_("Edit"))
        self._btn_edit.set_sensitive(False)
        self._btn_edit.set_focus_on_click(False)
        self._btn_edit.connect("clicked", self._on_edit_clicked)
        self._btn_vbox.pack_start(self._btn_edit, False, False, 0)
        
        # Pack vbox into hbox
        self._btn_hbox.pack_start(self._btn_vbox, False, False, 5)
        self._btn_vbox.show_all()
        
        # Create layout table
        table = gtk.Table(2, 1)

        table.attach(self._pane,    0, 1, 0, 1)
        table.attach(self._btn_hbox, 1, 2, 0, 1, 0)

        table.show_all()

        # Install layout table into bottom pane
        pane = window.get_bottom_panel()
        pane.add_item(table, _('Bookmarks'), self._icon)

        # Setup handlers for all documents
        for doc in window.get_documents():
            doc.connect("loaded", self._on_doc_loaded)
            
        # Setup tab handlers
        window.connect("tab-added", self._on_tab_added)
        window.connect("tab-removed", self._on_tab_removed)
        window.connect("active-tab-changed", self._on_tab_changed)
    
    def deactivate(self):
        # Remove any installed menu items
        self._remove_menu()

        self._window = None
        self._plugin = None
        self._action_group = None

    def update_ui(self):
        self._action_group.set_sensitive(self._window.get_active_document() != None)
        
        # Swicth bookmark store for current document
        doc = self._window.get_active_document()
        if doc:
            uri = doc.get_uri()
            self._tree.set_model(self._bookmarks.get_store(uri))
            
    def _insert_menu(self):
        # Get UI manager
        manager = self._window.get_ui_manager()

        # Create menu actions
        self._action_group = gtk.ActionGroup("AdvancedBookmarksActions")
        
        self._act_ab = gtk.Action("AdvancedBookmarks", _("Bookmarks"), _("Bookmarks"), None)

        self._act_toggle = gtk.Action("ToggleBookmark", _("Toggle"), _("Toggle"), None)
        self._act_toggle.connect("activate", self._on_toggle_bookmark)
        
        self._act_toggle_adv = gtk.Action("ToggleBookmarkAdvanced", _("Toggle & edit"), _("Toggle & edit"), None)
        self._act_toggle_adv.connect("activate", self._on_toggle_bookmark, True)
        
        self._act_edit = gtk.Action("EditBookmark", _("Edit bookmark"), _("Edit bookmark"), None)
        self._act_edit.connect("activate", self._on_edit_clicked)
        self._act_edit.set_sensitive(False)
        
        self._act_nb = gtk.Action("NumberedBookmarks", _("Numbered bookmarks"), _("Numbered bookmarks"), None)
        hot_key = 0
        self._act_hot_key = {}
        while hot_key < 10:
            self._act_hot_key[hot_key] = gtk.Action("ToggleBookmark%d" % hot_key, _("Toggle bookmark #%s") % hot_key, _("Toggle bookmark #%s") % hot_key, None)
            self._action_group.add_action_with_accel(self._act_hot_key[hot_key], "<Ctrl><Alt>%d" % hot_key)
            hot_key += 1

        self._action_group.add_action(self._act_ab)
        self._action_group.add_action(self._act_nb)
        self._action_group.add_action_with_accel(self._act_toggle, "<Ctrl>b")
        self._action_group.add_action_with_accel(self._act_toggle_adv, "<Ctrl><Shift>b")
        self._action_group.add_action_with_accel(self._act_edit, "<Ctrl><Alt>b")

        # Insert action group
        manager.insert_action_group(self._action_group, -1)

        # Merge UI
        ui_path = os.path.join(os.path.dirname(__file__), "menu.ui.xml")
        self._ui_id = manager.add_ui_from_file(ui_path)

    def _remove_menu(self):
        # Get the GtkUIManager
        manager = self._window.get_ui_manager()

        # Remove the ui
        manager.remove_ui(self._ui_id)

        # Remove the action group
        manager.remove_action_group(self._action_group)

        # Make sure the manager updates
        manager.ensure_update()
        
    def _on_toggle_bookmark(self, action, add_comment=False, hot_key=None):
        # Get document uri
        doc = self._window.get_active_document()
        
        if doc:
        	uri = uri = doc.get_uri()
        else:
        	uri = None
        	
        if uri:
            # Get current position
            text_iter = doc.get_iter_at_mark(doc.get_insert())

            # Get current line number (strarting from 0)
            line = text_iter.get_line()

            exists = self._bookmarks.exists(uri, line+1)
            
            # Clean up comment dialog field (DO NOT MOVE THINS LINE INTO "IF" STATEMENT)
            self._dlg_toggle.reset("")
            
            if not exists and add_comment:
                res = self._dlg_toggle.run()
            else:
                res = gtk.RESPONSE_OK
            
            if res == gtk.RESPONSE_OK:
                comment = self._dlg_toggle.get_comment()
                
                # Get position of the current and the next lines
                start = doc.get_iter_at_line(line)
                end   = doc.get_iter_at_line(line+1)
                
                # Check if we are at the last line
                if start.get_offset() == end.get_offset():
                    end = doc.get_end_iter()
                
                # Get line text
                source = doc.get_text(start, end, False).strip()
                
                # Toggle bookmark
                added = self._bookmarks.toggle(uri, line+1, source, comment)
                
                # Save bookmarks
                self._plugin.write_config()

                # Update sensitivity of edit button and menu item
                self._btn_edit.set_sensitive(added)
                self._act_edit.set_sensitive(added)
                self._pop_edit.set_sensitive(added)

                # Highlight the bookmark and the line
                if added:
                    store = self._bookmarks.get_store(uri)
                    iters = self._bookmarks.get_iters(uri)
                    
                    path = store.get_path(iters[line+1])
                    
                    self._tree.set_model(store)
                    self._tree.set_cursor(path[0])

                highlight = self._config.getboolean("common", "highlighting")
                self.set_line_highlighting(doc, start, end, added and highlight)
                        
	        buf = self._window.get_active_view()
            buf.grab_focus()
        else:
            m = gtk.MessageDialog(self._window, gtk.DIALOG_MODAL | gtk.DIALOG_DESTROY_WITH_PARENT, gtk.MESSAGE_INFO, gtk.BUTTONS_OK, _("You can toggle the bookmarks in the saved documents only"))
            m.connect("response", lambda dlg, res: dlg.hide())
            m.run()
                
    def _on_dlg_toggle_response(self, dlg_toggle, res): # Handles toggle dialog response
        # Hide configuration dialog
        dlg_toggle.hide()
    	
    def _on_insert_text(self, textbuffer, iter, text, length):
        # Get document uri
        doc = self._window.get_active_document()
        uri = doc.get_uri()
        
        if uri is not None:
            # Get current line number (strarting from 0)
            line = iter.get_line()            

            # Check if the cursor is placed inside a bookmark
            iters = self._bookmarks.get_iters(uri)
            if iters.has_key(line+1) and iter.get_visible_line_offset() > 0:
                line += 1

            # Get new document line count
            count = doc.get_line_count() + text.count("\n")
			
            # Update bookmarks and number of document lines
            self._update_doc_lines(doc, count, line+1)

    def _on_delete_text(self, textbuffer, start, end):
        # Get document uri
        doc = self._window.get_active_document()
        uri = doc.get_uri()
        
        if uri is not None:
            # Get start and end line numbers (strarting from 0)
            start_line = start.get_line()
            end_line = end.get_line()

            # Check if the cursor is placed at the start of the line next a bookmark
            iters = self._bookmarks.get_iters(uri)
            if iters.has_key(end_line) and end.get_visible_line_offset() == 0:
                start_line += 1
            
            # Get new document line count
            count = doc.get_line_count() - int(abs(end_line - start_line))

            # Update document line count and bookmarks
            self._update_doc_lines(doc, count, start_line+1, end_line)

    def _update_doc_lines(self, doc, line_count, line, end = -1):
        uri = doc.get_uri()
        if uri:
            # Check if there is no number of lines stored yet
            if not self._doc_lines.has_key(uri):
                self._doc_lines[uri] = doc.get_line_count()
                
            # Check if number of lines have to be changed
            if self._doc_lines[uri] != line_count:
                # Update bookmarks
                self._bookmarks.update(uri, self._doc_lines[uri] - line_count, line, end)
                
                # Setup new line count
                self._doc_lines[uri] = line_count
	
            # Save bookmarks
            self._plugin.write_config()
            
    def _on_tab_added(self, window, tab):
        # Get tab document
        doc = tab.get_document()
        
        # Setup document load handler
        doc.connect("loaded", self._on_doc_loaded)

    def _on_tab_removed(self, window, tab):
        docs = window.get_documents()

        if len(docs) <= 0:
            self._tree.set_model()
            self._btn_edit.set_sensitive(False)
            self._act_edit.set_sensitive(False)
            self._pop_edit.set_sensitive(False)
    
    def _on_tab_changed(self, window, tab):
        # Swicth bookmark store for current document
        doc = tab.get_document()
        if doc:
            uri = doc.get_uri()
            self._tree.set_model(self._bookmarks.get_store(uri))

    def _on_doc_changed(self, doc):
        uri = doc.get_uri()
        
        if uri:
            # Update number of lines of the document
            self._doc_lines[uri] = doc.get_line_count()
            
            # Refresh highlighting if needed
            highlight = self._config.getboolean("common", "highlighting")
            if highlight:
                # Cleanup highlighting
                self.setup_highlighting(False, doc)
                
                # Put highlighting back
                self.setup_highlighting(True, doc)
            
            iters = self._bookmarks.get_iters(uri)
            
            # Get current position
            text_iter = doc.get_iter_at_mark(doc.get_insert())

            # Get current line number (strarting from 0)
            line = text_iter.get_line() + 1

            if iters.has_key(line):
                it = iters[line]

                store = self._bookmarks.get_store(uri)
                
                if self._config.get(uri, str(line)) == "":
                    # Get position of the current and the next lines
                    start = doc.get_iter_at_line(line-1)
                    end   = doc.get_iter_at_line(line)
                    
                    # Check if we are at the last line
                    if start.get_offset() == end.get_offset():
                        end = doc.get_end_iter()
                    
                    # Get line text
                    source = doc.get_text(start, end, False).strip()
                    
                    store.set_value(it, 1, source.strip())

    def _on_doc_loaded(self, doc, arg, put=True, connect_signals=True):
        # Update comments
        uri = doc.get_uri()
        
        if uri:
            highlight = self._config.getboolean("common", "highlighting")
            
            store = self._bookmarks.get_store(uri)
            iters = self._bookmarks.get_iters(uri)
            
            for i in iters:
                it = iters[i]

                line = int(store.get_value(it, 0)) - 1
                
                start = doc.get_iter_at_line(line)
                end   = doc.get_iter_at_line(line+1)
                
                # Check if we are at the last line
                if start.get_offset() == end.get_offset():
                    end = doc.get_end_iter()
                
                self.set_line_highlighting(doc, start, end, put and highlight)
                    
                if store.get_value(it, 1) == "":
                    source = doc.get_text(start, end, False)
                    store.set_value(it, 1, source.strip())
            
        if connect_signals:
            # Setup update handlers
            doc.connect("insert-text",  self._on_insert_text)
            doc.connect("delete-range", self._on_delete_text)
            doc.connect("changed",      self._on_doc_changed)
            doc.connect("cursor-moved", self._on_cursor_moved)
        
    def _on_edit_clicked(self, btn):
        model = self._tree.get_model()

        cursor = self._tree.get_cursor()
        
        if cursor and cursor[0]:
            row = cursor[0][0]

            self._on_row_activated(self._tree, row, 0)

    def _on_tree_clicked(self, tree, event):
    	if event.button == 3:
	    	self._popup_menu.popup(None, None, None, event.button, event.time)
    	
    	return False

    def _on_row_selected(self, tree):
        model = tree.get_model()
        cursor = tree.get_cursor()
        
        if cursor:
            row = cursor[0][0]
            
            # Set comment button sensitivity
            self._btn_edit.set_sensitive(True)
            self._act_edit.set_sensitive(True)
            self._pop_edit.set_sensitive(True)
            
            # Get bookmark line
            bookmark = model.get_iter(row)
            line = model.get_value(bookmark, 0)
            
            # Get active document
            doc = self._window.get_active_document()
            buf = self._window.get_active_view()
            
            # Get current position
            text_iter = doc.get_iter_at_mark(doc.get_insert())

            if line != text_iter.get_line()+1:
                # Jump to bookmark
                doc.goto_line(int(line)-1)
                buf.scroll_to_cursor()
                buf.grab_focus()

    def _on_row_activated(self, tree, row, column):
        # Get document uri
        doc = self._window.get_active_document()
        uri = doc.get_uri()

        # Get bookmark line
        model = tree.get_model()
        bookmark = model.get_iter(row)
        line = model.get_value(bookmark, 0)
        
        comment = self._config.get(uri, str(line))
        
        self._dlg_toggle.reset(comment)
        res = self._dlg_toggle.run()

        if res == gtk.RESPONSE_OK:
            comment = self._dlg_toggle.get_comment()
            
            # Delete existing bookmark 
            self._bookmarks.delete(uri, line)

            # Get position of the current and the next lines
            start = doc.get_iter_at_line(line-1)
            end   = doc.get_iter_at_line(line)
            
            # Check if we are at the last line
            if start.get_offset() == end.get_offset():
                end = doc.get_end_iter()
            
            # Get line text
            source = doc.get_text(start, end, False).strip()
            
            # Add bookmark
            self._bookmarks.add(uri, line, source, comment)
            self._tree.set_model(self._bookmarks.get_store(uri))
            
            # Save bookmarks
            self._plugin.write_config()
        
    def _on_tree_focused(self, tree, direction):
        view = self._window.get_active_view()
        view.grab_focus()
        
    def _render_comment_callback(self, column, cell_renderer, tree_model, iter):
        doc = self._window.get_active_document()
        uri = doc.get_uri()
        
        if uri:
            line = tree_model.get_value(iter, 0)
            text = tree_model.get_value(iter, 1)
            
            if self._bookmarks.exists(uri, line):
                comment = self._config.get(uri, str(line))
                
                if comment != "":
                    cell_renderer.set_property("style", pango.STYLE_ITALIC)
                    cell_renderer.set_property("text", "'"+text+"'")
                else:
                    cell_renderer.set_property("style", pango.STYLE_NORMAL)
    
    def _on_cursor_moved(self, doc):
        uri = doc.get_uri()

        store = self._bookmarks.get_store(uri)
        
        # Get current position
        text_iter = doc.get_iter_at_mark(doc.get_insert())

        # Get current line number (strarting from 0)
        line = text_iter.get_line() + 1

        exists = self._bookmarks.exists(uri, line)
        
        if exists:
            iters = self._bookmarks.get_iters(uri)
            
            path = store.get_path(iters[line])
            
            self._tree.set_cursor(path[0])
        else:
            sel = self._tree.get_selection()
            sel.unselect_all()
            
            self._btn_edit.set_sensitive(False)
            self._act_edit.set_sensitive(False)
            self._pop_edit.set_sensitive(False)
    
    def set_line_highlighting(self, doc, start, end, highlight):
        tag_table = doc.get_tag_table()
        tag = tag_table.lookup("bookmark")
        
        if tag is None:
            color = self._config.get("common", "highlight_color")
            tag = doc.create_tag("bookmark", paragraph_background_gdk = gtk.gdk.color_parse(color))
        
        if highlight:
            doc.apply_tag(tag, start, end)
        else:
            doc.remove_tag(tag, start, end)
    
    def _remove_highlighting(self, doc):
        tag_table = doc.get_tag_table()
        tag = tag_table.lookup("bookmark")
        
        if tag is not None:
            start = doc.get_start_iter()
            end = doc.get_end_iter()
            doc.remove_tag(tag, start, end)
    
    def setup_highlighting(self, highlight, doc=None):
        func = highlight and (lambda doc: self._on_doc_loaded(doc, None, True, False)) or (lambda doc: self._remove_highlighting(doc))
        
        if doc is None:
            docs = self._window.get_documents()
        else:
            docs = [doc]
            
        for d in docs:
            tag_table = d.get_tag_table()
            tag = tag_table.lookup("bookmark")
            
            if tag is not None:
                tag_table.remove(tag)
                color = self._config.get("common", "highlight_color")
                tag = d.create_tag("bookmark", paragraph_background_gdk = gtk.gdk.color_parse(color))

            func(d)
    
# ex:ts=4:et:

########NEW FILE########
__FILENAME__ = align
# Copyright (C) 2006 Osmo Salomaa
#
# This program is free software; you can redistribute it and/or modify it under
# the terms of the GNU General Public License as published by the Free Software
# Foundation; either version 2 of the License, or (at your option) any later
# version.
#
# This program is distributed in the hope that it will be useful, but WITHOUT
# ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS
# FOR A PARTICULAR PURPOSE.  See the GNU General Public License for more
# details.
#
# You should have received a copy of the GNU General Public License along with
# this program; if not, write to the Free Software Foundation, Inc., 51
# Franklin Street, Fifth Floor, Boston, MA 02110-1301, USA.


"""Align blocks of text into columns."""


from gettext import gettext as _
import gedit
import gtk
import gtk.glade
import os
import gconf


UI = """
<ui>
  <menubar name="MenuBar">
    <menu name="EditMenu" action="Edit">
      <placeholder name="EditOps_6">
        <menuitem name="Align" action="AlignColumns"/>
      </placeholder>
    </menu>
  </menubar>
</ui>"""


gconf_base_uri = u'/apps/gedit-2/plugins/align_columns'

class AlignDialog(object):

    """Dialog for specifying an alignment separator."""

    def __init__(self, parent):

        path = os.path.join(os.path.dirname(__file__), 'align.glade')
        glade_xml = gtk.glade.XML(path)
        self.dialog = glade_xml.get_widget('dialog')
        self.entry = glade_xml.get_widget('entry')

        self.dialog.set_transient_for(parent)
        self.dialog.set_default_response(gtk.RESPONSE_OK)

        self._config = gconf.client_get_default()
        self._config.add_dir(gconf_base_uri, gconf.CLIENT_PRELOAD_NONE)


    def destroy(self):
        """Destroy the dialog."""
        return self.dialog.destroy()

    def get_separator(self):
        """Get separator."""
        separator = self.entry.get_text()
        # Save separator for next use
        self._config.set_string(
            os.path.join(gconf_base_uri,'last_separator'), separator)
        return separator


    def run(self):
        """Show and run the dialog."""
        last_used = self._config.get_string(
            os.path.join(gconf_base_uri,'last_separator'))
        if last_used:
            self.entry.set_text(last_used)
        self.dialog.show()
        return self.dialog.run()


class AlignPlugin(gedit.Plugin):

    """Align blocks of text into columns."""

    def __init__(self):

        gedit.Plugin.__init__(self)

        self.action_group = None
        self.ui_id = None
        self.window = None

    def activate(self, window):
        """Activate plugin."""

        self.window = window
        self.action_group = gtk.ActionGroup('AlignPluginActions')
        self.action_group.add_actions([(
            'AlignColumns',
            None,
            _('Ali_gn...'),
            "<Shift><Alt>A",
            _('Align the selected text to columns'),
            self.on_align_activate
        )])
        uim = window.get_ui_manager()
        uim.insert_action_group(self.action_group, -1)
        self.ui_id = uim.add_ui_from_string(UI)

    def align(self, doc, bounds, separator):
        """Align the selected text into columns."""

        splitter = separator.strip() or ' '
        lines = range(bounds[0].get_line(), bounds[1].get_line() + 1)

        # Split text to rows and columns.
        # Ignore lines that don't match splitter.
        # TODO: Teste here to ignore separator inside a quoted string
        matrix = []
        for i in reversed(range(len(lines))):
            line_start = doc.get_iter_at_line(lines[i])
            line_end = line_start.copy()
            line_end.forward_to_line_end()
            text = doc.get_text(line_start, line_end)
            if text.find(splitter) == -1:
                lines.pop(i)
                continue
            matrix.insert(0, text.split(splitter))
        for i in range(len(matrix)):
            matrix[i][0] = matrix[i][0].rstrip()
            for j in range(1, len(matrix[i])):
                matrix[i][j] = matrix[i][j].strip()

        # Find out column count and widths.
        col_count = max(list(len(x) for x in matrix))
        widths = [0] * col_count
        for row in matrix:
            for i, element in enumerate(row):
                widths[i] = max(widths[i], len(element))

        doc.begin_user_action()

        # Remove text and insert column elements.
        for i, line in enumerate(lines):
            line_start = doc.get_iter_at_line(line)
            line_end = line_start.copy()
            line_end.forward_to_line_end()
            doc.delete(line_start, line_end)
            for j, element in enumerate(matrix[i]):
                offset = sum(widths[:j])
                itr = doc.get_iter_at_line(line)
                itr.set_line_offset(offset)
                doc.insert(itr, element)
                if j < col_count - 1:
                    itr.set_line_offset(offset + len(element))
                    space = ' ' * (widths[j] - len(element))
                    doc.insert(itr, space)

        # Insert separators.
        for i, line in enumerate(lines):
            for j in reversed(range(len(matrix[i]) - 1)):
                offset = sum(widths[:j + 1])
                itr = doc.get_iter_at_line(line)
                itr.set_line_offset(offset)
                doc.insert(itr, separator)

        doc.end_user_action()

    def deactivate(self, window):
        """Deactivate plugin."""

        uim = window.get_ui_manager()
        uim.remove_ui(self.ui_id)
        uim.remove_action_group(self.action_group)
        uim.ensure_update()

        self.action_group = None
        self.ui_id = None
        self.window = None

    def on_align_activate(self, *args):
        """Align the selected text into columns."""

        doc = self.window.get_active_document()
        bounds = doc.get_selection_bounds()
        if not bounds:
            return
        dialog = AlignDialog(self.window)
        response = dialog.run()
        separator = dialog.get_separator()
        dialog.destroy()
        if response == gtk.RESPONSE_OK and separator:
            self.align(doc, bounds, separator)

    def update_ui(self, window):
        """Update sensitivity of plugin's actions."""

        doc = self.window.get_active_document()
        self.action_group.set_sensitive(doc is not None)


########NEW FILE########
__FILENAME__ = browserwidget
# Copyright (C) 2006 Frederic Back (fredericback@gmail.com)
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place, Suite 330, 
# Boston, MA 02111-1307, USA.

import gtk
import gobject
import gedit
import options
import imagelibrary

class ClassBrowser( gtk.VBox ):
    """ A widget that resides in gedits side panel. """

    def __init__(self, geditwindow):
        """ geditwindow -- an instance of gedit.Window """
        
        imagelibrary.initialise()

        gtk.VBox.__init__(self)
        self.geditwindow = geditwindow

        try: self.encoding = gedit.encoding_get_current()
        except: self.encoding = gedit.gedit_encoding_get_current()

        self.active_timeout = False

        self.parser = None
        self.document_history = [] # contains tuple (doc,line,col)
        self.history_pos = 0
        self.previousline = 0

        self.back = gtk.ToolButton(gtk.STOCK_GO_BACK)
        self.back.connect("clicked",self.history_back)
        self.back.set_sensitive(False)
        self.forward = gtk.ToolButton(gtk.STOCK_GO_FORWARD)
        self.forward.connect("clicked",self.history_forward)
        self.forward.set_sensitive(False)

        tb = gtk.Toolbar()
        tb.add(self.back)
        tb.add(self.forward)
        #self.pack_start(tb,False,False)

        # add a treeview
        sw = gtk.ScrolledWindow()
        sw.set_policy(gtk.POLICY_AUTOMATIC, gtk.POLICY_AUTOMATIC)
        sw.set_shadow_type(gtk.SHADOW_IN)
        self.browser = gtk.TreeView()
        self.browser.set_headers_visible(False)
        sw.add(self.browser)
        self.browser.connect("button_press_event",self.__onClick)
        
        self.pack_start(sw)

        # add a text column to the treeview
        self.column = gtk.TreeViewColumn()
        self.browser.append_column(self.column)

        self.cellrendererpixbuf = gtk.CellRendererPixbuf()
        self.column.pack_start(self.cellrendererpixbuf,False)

        self.crt = gtk.CellRendererText()
        self.column.pack_start(self.crt,False)

        # connect stuff
        self.browser.connect("row-activated",self.on_row_activated)
        self.show_all()
        

    def history_back(self, widget):
        if self.history_pos == 0: return
        self.history_pos -= 1
        entry = self.document_history[self.history_pos]
        self.__openDocumentAtLine( entry[0],entry[1],entry[2],False )
        if len(self.document_history) > 1: self.forward.set_sensitive(True)
        if self.history_pos <= 0: self.back.set_sensitive(False)
            
            
    def history_forward(self, widget):
        if self.history_pos+1 > len(self.document_history): return
        self.history_pos += 1
        entry = self.document_history[self.history_pos]
        self.__openDocumentAtLine( entry[0],entry[1],entry[2],False )
        self.back.set_sensitive(True)
        if self.history_pos+1 >= len(self.document_history):
            self.forward.set_sensitive(False)


    def set_model(self, treemodel, parser=None):
        """ set the gtk.TreeModel that contains the current class tree.
        parser must be an instance of a subclass of ClassParserInterface. """
        self.browser.set_model(treemodel)
        if parser:
            self.column.set_cell_data_func(self.crt, parser.cellrenderer)
            self.column.set_cell_data_func(self.cellrendererpixbuf, parser.pixbufrenderer)
        self.parser = parser
        self.browser.queue_draw()
              
              
    def __jump_to_tag(self, path):
        try:
            path, line = self.parser.get_tag_position(self.browser.get_model(),path)
            self.__openDocumentAtLine(path, line)
        except:
            pass
                
                
    def on_row_activated(self, treeview, path, view_column):
        if self.parser: self.__jump_to_tag(path)


    def __onClick(self, treeview, event):

        if event.button == 2:
            if options.singleton().jumpToTagOnMiddleClick:
                x, y = int(event.x), int(event.y)
                pthinfo = treeview.get_path_at_pos(x, y)
                if pthinfo is None: return
                path, col, cellx, celly = pthinfo
                self.__jump_to_tag(path)
                return True
            
        if event.button == 3:
            x, y = int(event.x), int(event.y)
            pthinfo = treeview.get_path_at_pos(x, y)
            if pthinfo is None: return
            path, col, cellx, celly = pthinfo
            #treeview.grab_focus()
            #treeview.set_cursor(path)

            menu = gtk.Menu()

            tagpos = self.parser.get_tag_position(self.browser.get_model(),path)
            if tagpos is not None:
                filename, line = tagpos
                m = gtk.ImageMenuItem(gtk.STOCK_JUMP_TO)
                menu.append(m)
                m.show()
                m.connect("activate", lambda w,p,l: self.__openDocumentAtLine(p,l), filename, line )

            # add the menu items from the parser
            menuitems = self.parser.get_menu(self.browser.get_model(),path)
            for item in menuitems:
                menu.append(item)
                item.show()
                
            m = gtk.SeparatorMenuItem()
            m.show()
            menu.append( m )
            
            
            m = gtk.CheckMenuItem("autocollapse")
            menu.append(m)
            m.show()
            m.set_active( options.singleton().autocollapse )
            def setcollapse(w):
                options.singleton().autocollapse = w.get_active()
            m.connect("toggled", setcollapse )
            
            menu.popup( None, None, None, event.button, event.time)
            

    def get_current_iter(self):
       doc = self.geditwindow.get_active_document() 
       iter = None
       path = None
       if doc and self.parser:
            it = doc.get_iter_at_mark(doc.get_insert())
            line = it.get_line()            
            model = self.browser.get_model()
            path = self.parser.get_tag_at_line(model, doc, line)
            #if there is no current tag, get the root
            if path is None: 
                iter = model.get_iter_root()
                path = model.get_path(iter)
            else:
                #Get current tag
                iter = model.get_iter(path)
       return iter, path


    """ Jump to next/previous tag depending on direction (0, 1)"""
    def jump_to_tag(self, direction = 1): 
    
        #use self dince python doesn't have true closures, yuck!
        self.iter_target = None
        self.iter_next = None
        self.iter_found = False

        def get_previous(model, path, iter, path_searched):
             if path_searched is None:
                self.iter_found = True
                self.iter_target = model.get_iter_root()
             if path == path_searched:
                self.iter_found = True
                #if we are at the beginning of the tree
                if self.iter_target is None:
                    self.iter_target = model.get_iter_root()
                return True
             self.iter_target = iter
             return False


        def get_next(model,path, iter, path_searched):
            if path_searched is None:
                self.iter_found = True
                self.iter_target = model.get_iter_root()
            if self.iter_found: 
                self.iter_target = iter
                return True
            if path == path_searched:  self.iter_found = True   
            return False
        search_funcs = get_previous, get_next

        if ( 0 > direction) or (len(search_funcs) <= direction):
            print "Direction ", direction, " must be between 0 and ", len(search_funcs)
            raise ValueError, "Invalid direction"

        model = self.browser.get_model()
        iter, path = self.get_current_iter()
        model.foreach(search_funcs[direction], path)

        if not self.iter_found or not self.iter_target: 
            if options.singleton().verbose: print "No target path"
            return 
        target_path = model.get_path(self.iter_target)
        tagpos = self.parser.get_tag_position(model, target_path)
        if tagpos is not None:
            path, line = tagpos
            if options.singleton().verbose: print "jump to", path
            self.__openDocumentAtLine(path,line)

        
    def __openDocumentAtLine(self, filename, line, column=1, register_history=True):
        """ open a the file specified by filename at the given line and column
        number. Line and column numbering starts at 1. """
        
        if line == 0 or column == 0:
            raise ValueError, "line and column numbers start at 1"
        
        documents = self.geditwindow.get_documents()
        found = None
        for d in documents:
            if d.get_uri() == filename:
                found = d
                break

        # open an existing tab or create a new one
        if found is not None:
            tab = gedit.tab_get_from_document(found)
            self.geditwindow.set_active_tab(tab)
            doc = tab.get_document()
            doc.begin_user_action()
            it = doc.get_iter_at_line_offset(line-1,column-1)
            doc.place_cursor(it)
            (start, end) = doc.get_bounds()
            self.geditwindow.get_active_view().scroll_to_iter(end,0.0)
            self.geditwindow.get_active_view().scroll_to_iter(it,0.0)
            self.geditwindow.get_active_view().grab_focus()
            doc.end_user_action()
        else:
            tab = self.geditwindow.create_tab_from_uri(filename,self.encoding,line,False,False)
            self.geditwindow.set_active_tab(tab)
            found = self.geditwindow.get_active_document()

        # place mark
        #it = found.get_iter_at_line(line-1)
        #mark = found.create_marker(None,"jumped_to",it)

        if register_history:
            self.document_history.append( (filename,line,column) )
            self.back.set_sensitive(True)
            self.forward.set_sensitive(False)
            self.history_pos += 1
            

    def on_cursor_changed(self, *args):
        """
        I need to catch changes in the cursor position to highlight the current tag
        in the class browser. Unfortunately, there is no signal that gets emitted
        *after* the cursor has been changed, so I have to use a timeout.
        """
        if not self.active_timeout:
            gobject.timeout_add(100,self.update_cursor)
            self.active_timeout = True
            

    def update_cursor(self, *args):
        doc = self.geditwindow.get_active_document()
        if doc and self.parser:
            it = doc.get_iter_at_mark(doc.get_insert())
            line = it.get_line()
            if line != self.previousline:
                self.previousline = line
                if options.singleton().verbose: print "current line:",line

                # pipe the current line to the parser
                self.parser.current_line_changed(self.browser.get_model(), doc, line)

                # set cursor on the tag the cursor is pointing to
                try:
                    path = self.parser.get_tag_at_line(self.browser.get_model(),doc,line)
                    if path:
                        self.browser.realize()
                        if options.singleton().autocollapse: self.browser.collapse_all()
                        self.browser.expand_to_path(path)
                        self.browser.set_cursor(path)
                        if options.singleton().verbose: print "jump to", path

                except Exception, e:
                    if options.singleton().verbose: print "no tag at line",line

        self.active_timeout = False
        return False

########NEW FILE########
__FILENAME__ = imagelibrary
# Copyright (C) 2006 Frederic Back (fredericback@gmail.com)
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place, Suite 330, 
# Boston, MA 02111-1307, USA.

# The class browser pixmaps are stolen from Jesse Van Den Kieboom's
# ctags plugin (http://live.gnome.org/Gedit/PluginCodeListing)

import gtk
import sys, os

pixbufs = {
    "class" : None,
    "default" : None,
    "enum" : None,
    "enum_priv" : None,
    "enum_prot" : None,
    "field" : None,
    "field_priv" : None,
    "field_prot" : None,
    "method" : None,
    "method_priv" : None,
    "method_prot" : None,
    "namespace" : None,
    "patch" : None,
    "struct" : None,
    "struct_priv" : None,
    "struct_prot" : None,
    "variable" : None,
}

def initialise():
    for key in pixbufs:
        try:
            name = "%s.png" % key
            filename = os.path.join(sys.path[0],"classbrowser","pixmaps",name)
            if not os.path.exists(filename):
                filename = os.path.join(os.path.dirname(__file__),"pixmaps",name)
            pixbufs[key] = gtk.gdk.pixbuf_new_from_file(filename)
        except:
            print "Class browser plugin couldn't locate",filename





########NEW FILE########
__FILENAME__ = options
# Copyright (C) 2006 Frederic Back (fredericback@gmail.com)
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place, Suite 330, 
# Boston, MA 02111-1307, USA.

import gobject
import gtk
import gconf

def singleton():
    if Options.singleton is None:
        Options.singleton = Options()
    return Options.singleton

class Options(gobject.GObject):

    __gsignals__ = {
        'options-changed' : (gobject.SIGNAL_RUN_LAST, gobject.TYPE_NONE, ()),
    }

    singleton = None

    def __init__(self):

        gobject.GObject.__init__(self)
        self.__gconfDir = "/apps/gedit-2/plugins/classbrowser"

        # default values
        self.verbose = False
        self.autocollapse = True
        self.jumpToTagOnMiddleClick = False
        self.colours = {
            "class" : gtk.gdk.Color(50000,20000,20000),
            "define": gtk.gdk.Color(60000,0,0),
            "enumerator": gtk.gdk.Color(0,0,0),
            "member" : gtk.gdk.Color(0,0,60000),
            "function" : gtk.gdk.Color(50000,0,60000),
            "namespace" : gtk.gdk.Color(0,20000,0),
        }
    
        # create gconf directory if not set yet
        client = gconf.client_get_default()        
        if not client.dir_exists(self.__gconfDir):
            client.add_dir(self.__gconfDir,gconf.CLIENT_PRELOAD_NONE)

        # get the gconf keys, or stay with default if key not set
        try:
            self.verbose = client.get_bool(self.__gconfDir+"/verbose") \
                or self.verbose 

            self.autocollapse = client.get_bool(self.__gconfDir+"/autocollapse") \
                or self.autocollapse 

            self.jumpToTagOnMiddleClick = client.get_bool(self.__gconfDir+"/jumpToTagOnMiddleClick") \
                or self.jumpToTagOnMiddleClick 

            for i in self.colours:
                col = client.get_string(self.__gconfDir+"/colour_"+i)
                if col: self.colours[i] = gtk.gdk.color_parse(col)

        except Exception, e: # catch, just in case
            print e
            
    def __del__(self):
        # write changes to gconf
        client = gconf.client_get_default()
        client.set_bool(self.__gconfDir+"/verbose", self.verbose)
        client.set_bool(self.__gconfDir+"/autocollapse", self.autocollapse)
        client.set_bool(self.__gconfDir+"/jumpToTagOnMiddleClick", self.jumpToTagOnMiddleClick)
        for i in self.colours:
            client.set_string(self.__gconfDir+"/colour_"+i, self.color_to_hex(self.colours[i]))

    def create_configure_dialog(self):
        win = gtk.Window()
        win.connect("delete-event",lambda w,e: w.destroy())
        win.set_title("Preferences")
        vbox = gtk.VBox() 

        #--------------------------------  

        notebook = gtk.Notebook()
        notebook.set_border_width(6)
        vbox.pack_start(notebook)

        vbox2 = gtk.VBox()
        vbox2.set_border_width(6) 

        box = gtk.HBox()
        verbose = gtk.CheckButton("show debug information")
        verbose.set_active(self.verbose)
        box.pack_start(verbose,False,False,6)
        vbox2.pack_start(box,False)

        box = gtk.HBox()
        autocollapse = gtk.CheckButton("autocollapse symbol tree")
        autocollapse.set_active(self.autocollapse)
        box.pack_start(autocollapse,False,False,6)
        vbox2.pack_start(box,False)

        box = gtk.HBox()
        jumpToTagOnMiddleClick = gtk.CheckButton("jump to tag on middle click")
        jumpToTagOnMiddleClick.set_active(self.jumpToTagOnMiddleClick)
        box.pack_start(jumpToTagOnMiddleClick,False,False,6)
        vbox2.pack_start(box,False)

        notebook.append_page(vbox2,gtk.Label("General"))

        #--------------------------------       
        vbox2 = gtk.VBox()
        vbox2.set_border_width(6)

        button = {}
        for i in self.colours:
            box = gtk.HBox()
            button[i] = gtk.ColorButton()
            button[i].set_color(self.colours[i])
            box.pack_start(button[i],False)
            box.pack_start(gtk.Label(i),False,False,6)
            vbox2.pack_start(box)

        notebook.append_page(vbox2,gtk.Label("Colours"))

        def setValues(w):

            # set class attributes
            self.verbose = verbose.get_active()
            self.autocollapse = autocollapse.get_active()
            self.jumpToTagOnMiddleClick = jumpToTagOnMiddleClick.get_active()
            for i in self.colours:
                self.colours[i] = button[i].get_color()
                
            # write changes to gconf
            client = gconf.client_get_default()

            client.set_bool(self.__gconfDir+"/verbose", self.verbose)
            client.set_bool(self.__gconfDir+"/autocollapse", self.autocollapse)
            client.set_bool(self.__gconfDir+"/jumpToTagOnMiddleClick", self.jumpToTagOnMiddleClick)
            for i in self.colours:
                client.set_string(self.__gconfDir+"/colour_"+i, self.color_to_hex(self.colours[i]))

            # commit changes and quit dialog
            self.emit("options-changed")
            win.destroy()

        box = gtk.HBox()
        b = gtk.Button(None,gtk.STOCK_OK)
        b.connect("clicked",setValues)
        box.pack_end(b,False)
        b = gtk.Button(None,gtk.STOCK_CANCEL)
        b.connect("clicked",lambda w,win: win.destroy(),win)
        box.pack_end(b,False)
        vbox.pack_start(box,False)

        win.add(vbox)
        win.show_all()        
        return win

    def color_to_hex(self, color ):
        r = str(hex( color.red / 256 ))[2:]
        g = str(hex( color.green / 256 ))[2:]
        b = str(hex( color.blue / 256 ))[2:]
        return "#%s%s%s"%(r.zfill(2),g.zfill(2),b.zfill(2))

gobject.type_register(Options)

########NEW FILE########
__FILENAME__ = parserinterface
# Copyright (C) 2006 Frederic Back (fredericback@gmail.com)
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place, Suite 330, 
# Boston, MA 02111-1307, USA.


class ClassParserInterface:
    """ An abstract interface for class parsers.
    
    A class parser monitors gedit documents and provides a gtk.TreeModel
    that contains the browser tree. Elements in the browser tree are reffered
    to as 'tags'.
    
    There is always only *one* active instance of each parser. They are created
    at startup (in __init__.py).
    
    The best way to implement a new parser is probably to store custom python
    objects in a gtk.treestore or gtk.liststore, and to provide a cellrenderer
    to render them.
    """
    
    #------------------------------------- methods that *have* to be implemented
    
    def parse(self, geditdoc): 
        """ Parse a gedit.Document and return a gtk.TreeModel. 
        
        geditdoc -- a gedit.Document
        """
        pass        
        
        
    def cellrenderer(self, treeviewcolumn, cellrenderertext, treemodel, it):
        """ A cell renderer callback function that controls what the text label
        in the browser tree looks like.
        See gtk.TreeViewColumn.set_cell_data_func for more information. """
        pass
        
    #------------------------------------------- methods that can be implemented
   
    def pixbufrenderer(self, treeviewcolumn, cellrendererpixbuf, treemodel, it):
        """ A cell renderer callback function that controls what the pixmap next
        to the label in the browser tree looks like.
        See gtk.TreeViewColumn.set_cell_data_func for more information. """
        cellrendererpixbuf.set_property("pixbuf",None)
        
        
    def get_tag_position(self, model, doc, path):
        """ Return the position of a tag in a file. This is used by the browser
        to jump to a symbol's position.
        
        Returns a tuple with the full file uri of the source file and the line
        number of the tag or None if the tag has no correspondance in a file.
        
        model -- a gtk.TreeModel (previously provided by parse())
        path -- a tuple containing the treepath
        """
        pass
    
        
    def get_menu(self, model, path):
        """ Return a list of gtk.Menu items for the specified tag. 
        Defaults to an empty list
        
        model -- a gtk.TreeModel (previously provided by parse())
        path -- a tuple containing the treepath
        """
        return []

    
    def current_line_changed(self, model, doc, line):
        """ Called when the cursor points to a different line in the document.
        Can be used to monitor changes in the document.
        
        model -- a gtk.TreeModel (previously provided by parse())
        doc -- a gedit document
        line -- int
        """
        pass
  
        
    def get_tag_at_line(self, model, doc, linenumber):
        """ Return a treepath to the tag at the given line number, or None if a
        tag can't be found.
        
        model -- a gtk.TreeModel (previously provided by parse())
        doc -- a gedit document
        linenumber -- int
        """
        pass
        

########NEW FILE########
__FILENAME__ = parser_cstyle
# Copyright (C) 2007 Frederic Back (fredericback@gmail.com)
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place, Suite 330, 
# Boston, MA 02111-1307, USA.

"""

TODO

[1]-----------------------------------------------------------------------------

    The getTokenBackwards method is crap: It will stop as soon as it finds
    certain caracters (";"), but those may be enclosed in "", in ''
    or in comments, and therefore be legitimate.

    It would be better to keep a string in __get_brackets...

[2]-----------------------------------------------------------------------------

    __get_brackets() should skip everything enclosed in "" or ''.

[3]-----------------------------------------------------------------------------

    __get_brackets() should skip comments: c and c++ style
    
[4]-----------------------------------------------------------------------------

    what about php beginnings and endings? Should skip non-php parts
    

"""

import gtk
import pango
import options
import gobject
from parserinterface import ClassParserInterface
import imagelibrary

#---------------------------------------------------------------------------
class Token:

    def __init__(self,t):
        self.type = t
        self.name = None
        self.params = None
        self.visibility = None

        self.uri = None
        self.start = None
        self.end = None

        self.parent = None
        self.children = [] # a list of nested tokens

    def append(self, child):
        child.parent = self
        self.children.append(child)
        
    def __str__(self):
        return str(self.type) +" " +str(self.name)


#---------------------------------------------------------------------------
class _DummyToken:

    def __init__(self):
        self.parent = None
        self.children = [] # a list of nested tokens
        
    def append(self, child):
        child.parent = self
        self.children.append(child)
        
        
#---------------------------------------------------------------------------    
class CStyleCodeParser( ClassParserInterface ):
    """ This clases provides the basic functionality for the new PHP parser """

    def __init__(self):
        pass
   
   
    def getTokenFromChunk(self, chunk):
        """ Subclasses should implement this """
        pass
        
        
    def getTokenBackwards(self, string, position ):
        """ Iterate a string backwards from a given position to get token
            Example: calling ("one two three",8,2) would return ["two",one"] """ 
        
        # first step: get chunk where definition must be located
        # get substring up to a key character
        i = position
        while i > 0:
            i-=1
            if string[i] in ";}{/": # "/" is for comment endings
                break;
        
        # remove dirt
        chunk = string[i:position+1].strip()
        chunk = chunk.replace("\n"," ");
        chunk = chunk.replace("\r"," ");
        chunk = chunk.replace("\t"," ");
        
        return self.getTokenFromChunk(chunk)
        
        
    def parse(self, doc):
        text = doc.get_text(*doc.get_bounds())
        root = self.__get_brackets(text,doc.get_uri())
        self.__browsermodel = gtk.TreeStore(gobject.TYPE_PYOBJECT)
        for child in root.children: self.__appendTokenToBrowser(child,None)
        return self.__browsermodel
        
        
    def get_tag_position(self, model, path):
        tok = model.get_value( model.get_iter(path), 0 )
        try: return tok.uri, tok.start+1
        except: pass


    def cellrenderer(self, column, ctr, model, it):
        """ Render the browser cell according to the token it represents. """
        tok = model.get_value(it,0)
        name = tok.name
        colour = options.singleton().colours[ "function" ]
        if tok.type == "class":
            name = "class "+tok.name
            colour = options.singleton().colours[ "class" ]
        ctr.set_property("text", name)
        ctr.set_property("foreground-gdk", colour)


    def pixbufrenderer(self, column, crp, model, it):
        tok = model.get_value(it,0)
        if tok.type == "class":
            icon = "class"
        else:
            if tok.visibility == "private": icon = "method_priv"
            elif tok.visibility == "protected": icon = "method_prot"
            else: icon = "method"
        crp.set_property("pixbuf",imagelibrary.pixbufs[icon])


    def __appendTokenToBrowser(self, token, parentit ):
        if token.__class__ == _DummyToken: return
        it = self.__browsermodel.append(parentit,(token,))
        token.path = self.__browsermodel.get_path(it)
        for child in token.children:
            self.__appendTokenToBrowser(child, it)

    def __get_brackets(self,string,uri):
        verbose = False
        root = Token("root")
        parent = root
        ident = 0
        
        if verbose: print "-"*80
        
        line = 0 # count lines
        for i in range(len(string)-1):
        
            c = string[i]
            
            if c == "{": #------------------------------------------------------
            
                # get a token from the chunk of code preceding the bracket
                token = self.getTokenBackwards( string, i )
                
                if token:
                    # assign line number and uri to the token
                    token.uri = uri
                    token.start = line
                else:
                    # dummy token for empty brackets. Will not get added to tree.
                    token = _DummyToken()
                    
                # append the token to the tree
                parent.append(token)
                parent = token

                if verbose: print ident*"  "+"{",token
                ident += 1
                
                
            elif c == "}": #----------------------------------------------------
                ident -= 1
                if parent != root:
                    parent.end = line
                    parent = parent.parent
                    
                if verbose: print ident*"  "+"}",parent
                
            elif c == "\n":
                line += 1
                
        return root



########NEW FILE########
__FILENAME__ = parser_ctags
# Copyright (C) 2006 Frederic Back (fredericback@gmail.com)
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place, Suite 330,
# Boston, MA 02111-1307, USA.

import gtk
import tempfile
import os
import gnomevfs

from parserinterface import *
import imagelibrary
import options

class CTagsParser( ClassParserInterface ):
    """ A class parser that uses ctags.

    Note that this is a very rough and hackish implementation.
    Feel free to improve it.

    See http://ctags.sourceforge.net for more information about exuberant ctags,
    and http://ctags.sourceforge.net/FORMAT for a description of the file format.
    """

    def __init__(self):
        self.model = None
        self.document = None


    def parse(self, doc):
        """ Create a gtk.TreeModel with the tags of the document.

        The TreeModel contains:
           token name, source file path, line in the source file, type code

        If the second str contains an empty string, it means that
        the element has no 'physical' position in a file (see get_tag_position)
        """

        self.model = gtk.TreeStore(str,str,int,str) # see __parse_to_model
        self.document = doc
        self.__parse_doc_to_model()
        return self.model


    def __parse_doc_to_model(self):
        """ Parse the given document and write the tags to a gtk.TreeModel.

        The parser uses the ctags command from the shell to create a ctags file,
        then parses the file, and finally populates a treemodel.
        """

        # refactoring noise
        doc = self.document
        ls = self.model
        ls.clear()

        # make sure this is a local file (ie. not via ftp or something)
        try:
            if doc.get_uri()[:4] != "file": return ls
        except:
            return

        docpath = doc.get_uri_for_display()
        path, filename = os.path.split(docpath)
        if filename.find(".") != -1:
            arg = path + os.sep + filename[:filename.rfind(".")] + ".*"
        else:
            arg = docpath

        # simply replacing blanks is the best variant because both gnomevfs
        # and the fs understand it.
        arg = arg.replace(" ","\ ")

        # create tempfile
        h, tmpfile = tempfile.mkstemp()

        # launch ctags
        command = "ctags -n -f %s %s"%(tmpfile,arg)
        os.system(command)

        # print "command:",command

        # create list of tokens from the ctags file-------------------------

        # A list of lists. Matches the order found in tag files.
        # identifier, path to file, line number, type, and then more magical things
        tokenlist = []

        h = open(tmpfile)
        enumcounter = 0
        for r in h.readlines():
            tokens = r.strip().split("\t")
            if tokens[0][:2] == "!_": continue

            # convert line numbers to an int
            tokens[2] =  int(filter( lambda x: x in '1234567890', tokens[2] ))

            # prepend container elements, append member elements. Do this to
            # make sure that container elements are created first.
            if self.__is_container(tokens): tokenlist = [tokens] + tokenlist
            else: tokenlist.append(tokens)

            # hack: remember the number of enums without parents for later grouping
            if self.__get_type(tokens) == 'e' and self.__get_parent(tokens) == None:
                enumcounter += 1

        # add tokens to the treestore---------------------------------------
        containers = { None: None } # keep dict: token's name -> treeiter

        #if enumcounter > 0:
        #    node = ls.append( None, ["Enumerators","",0,""] )
        #    containers["Enumerators"] = node

        # used to sort the list of tokens by file, then by line number
        def cmpfunc(a,b):
            # by filename
            #if a[1] < b[1]: return -1
            #if a[1] > a[1]: return 1

            # by line number
            if a[2] < b[2]: return -1
            if a[2] > b[2]: return 1
            return 0


        # iterate through the list of tags, sorted by their line number
        # a token is a list. Order matches tag file order (name,path,line,type,...)
        for tokens in sorted(tokenlist,cmpfunc):

            # skip enums
            if self.__get_type(tokens) in 'de': continue

            #print self.__get_type(tokens),tokens[0],self.__get_parent(tokens)

            # append current token to parent iter, or to trunk when there is none
            parent = self.__get_parent(tokens)

            # hack: group enums without parents:
            if parent is None and self.__get_type(tokens) == 'e': parent = "Enumerators"

            if parent in containers: node = containers[parent]
            else:
                # create a dummy element in case the parent doesn't exist
                node = ls.append( None, [parent,"",0,""] )
                containers[parent] = node

            # escape blanks in file path
            tokens[1] = str( gnomevfs.get_uri_from_local_path(tokens[1]) )


            # make sure tokens[4] contains type code
            if len(tokens) == 3: tokens.append("")
            else: tokens[3] = self.__get_type(tokens)

            # append to treestore
            it = ls.append( node, tokens[:4] )

            # if this element was a container, remember it's treeiter
            if self.__is_container(tokens): containers[tokens[0]] = it

        # remove temp file
        os.remove(tmpfile)

        #print "------------------"



    def get_tag_position(self, model, path):
        filepath = model.get_value( model.get_iter(path), 1 )
        linenumber = model.get_value( model.get_iter(path), 2 )
        if filepath == "": return None
        return filepath, linenumber


    def get_tag_at_line(self, model, doc, linenumber):
        """ Return a treepath to the tag at the given line number, or None if a
        tag can't be found.
        """

        if doc is None: return

        self.minline = -1
        self.tagpath = None

        def loopfunc(model, path, it):
            if model.get_value(it,1) != doc.get_uri_for_display(): return
            l = model.get_value(it,2)
            if l >= self.minline and l <= linenumber+1:
                self.tagpath = path
                self.minline = l

    # recursively loop through the treestore
        model.foreach(loopfunc)

        if self.tagpath is None:
            it = model.get_iter_root()
            return model.get_path(it)

        return self.tagpath


    def get_menu(self, model, path):
        m = gtk.ImageMenuItem(gtk.STOCK_REFRESH)
        m.connect("activate", lambda w: self.__parse_doc_to_model() )
        return [m]


    def __get_type(self, tokrow):
        """ Returns a char representing the token type or False if none were found.

        According to the ctags docs, possible types are:
		c	class name
		d	define (from #define XXX)
		e	enumerator
		f	function or method name
		F	file name
		g	enumeration name
		m	member (of structure or class data)
		p	function prototype
		s	structure name
		t	typedef
		u	union name
		v	variable
        """
        if len(tokrow) == 3: return
        for i in tokrow[3:]:
            if len(i) == 1: return i # most common case: just one char
            elif i[:4] == "kind": return i[5:]
        return ' '

    def __is_container(self, tokrow):
        """ class, enumerations, structs and unions are considerer containers """
        if self.__get_type(tokrow) in 'cgsu': return True
        return False

    def __get_parent(self, tokrow):
        if len(tokrow) == 3: return
        for i in tokrow[3:]:
            if i[:5] == "class": return i[6:]
            if i[:6] == "struct": return i[7:]
            if i[:5] == "union": return i[6:]
        return None

    def cellrenderer(self, column, ctr, model, it):
        i = model.get_value(it,0)
        ctr.set_property("text", i)

        elements = {
            "c":"class",
            "f":"function",
            "m":"member",
            "e":"enumerator",
            "d":"define",
        }

        i = model.get_value(it,3)
        try: colour = options.singleton().colours[ elements[i] ]
        except: colour = gtk.gdk.Color(0,0,0)
        ctr.set_property("foreground-gdk", colour)

    def pixbufrenderer(self, column, crp, model, it):

        elements = {
            "c":"class", #class name
            "d":"define", #define (from #define XXX)
            "e":"enum", #enumerator
            "f":"method", #function or method name
            "F":"default", #file name
            "g":"enum", #enumeration name
            "m":"default", #(of structure or class data)
        	"p":"default", #function prototype
		    "s":"struct", #structure name
		    "t":"default", #typedef
		    "u":"struct", #union name
		    "v":"variable", #variable
        }

        try:
            i = model.get_value(it,3)
            icon = elements[i]
        except:
            icon = "default"

        crp.set_property("pixbuf",imagelibrary.pixbufs[icon])

########NEW FILE########
__FILENAME__ = parser_diff
# -*- coding: utf-8 -*-
# Copyright (C) 2007 Kristoffer Lundén (kristoffer.lunden@gmail.com)
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place, Suite 330,
# Boston, MA 02111-1307, USA.

import gtk
import gobject
import pango
import os
import options
import imagelibrary
from parserinterface import ClassParserInterface

class Token:
  def __init__(self):
    self.start = 0
    self.end = 0
    self.name = None
    self.parent = None
    self.children = []
    self.type = 'changeset'

class DiffParser(ClassParserInterface):

  def parse(self, geditdoc):
    text = geditdoc.get_text(*geditdoc.get_bounds())
    linecount = -1
    current_file = None
    changeset = None
    files = []
    uri = geditdoc.get_uri()

    for line in text.splitlines():
      linecount += 1
      lstrip = line.lstrip()
      ln = lstrip.split()
      if len(ln) == 0: continue

      if ln[0] == '---':
        if current_file is not None:
          current_file.end = linecount - 1
        current_file = Token()
        current_file.name = ln[1]
        current_file.start = linecount
        current_file.type = 'file'
        current_file.uri = uri
        files.append(current_file)

      elif current_file == None: continue

      elif ln[0] == '@@' and ln[-1] == '@@':
        if changeset is not None:
          changeset.end = linecount
        changeset = Token()
        changeset.name = ' '.join(ln[1:-1])
        changeset.start = linecount
        changeset.uri = uri
        current_file.children.append(changeset)
        changeset.parent = current_file

      # Ending line of last tokens
      if len(files) > 0:
        f =  files[-1]
        f.end = linecount + 2
        if len(f.children) > 0:
          f.children[-1].end = linecount + 2

    model = gtk.TreeStore(gobject.TYPE_PYOBJECT)

    pp = None

    # "Fake" common top folder, if any
    # TODO: Create hierarchy if patch applies in multiple directories
    if len(files) > 0:
      paths = map(lambda f:f.name, files)
      prefix = os.path.dirname(os.path.commonprefix(paths)) + '/'
      if len(prefix) > 1:
        parent_path = Token()
        parent_path.type = 'path'
        parent_path.name = prefix
        for f in files: f.name = f.name.replace(prefix,'',1)
        pp = model.append(None,(parent_path,))

    # Build tree
    for f in files:
      tree_iter = model.append(pp,(f,))
      for c in f.children:
         model.append(tree_iter,(c,))

    return model

  def cellrenderer(self, treeviewcolumn, cellrenderertext, treemodel, it):
    token = treemodel.get_value(it,0)

    colour = options.singleton().colours["member"]

    if token.type == 'path':
      colour = options.singleton().colours["namespace"]
    elif token.type == 'file':
      colour = options.singleton().colours["class"]

    cellrenderertext.set_property("text", token.name)
    cellrenderertext.set_property("style", pango.STYLE_NORMAL)
    cellrenderertext.set_property("foreground-gdk", colour)

  def get_tag_position(self, model, path):
    tok = model.get_value(model.get_iter(path),0)
    try: return tok.uri, tok.start + 1
    except: return None

  def get_tag_at_line(self, model, doc, linenumber):

    def find_path(model, path, iter, data):
      line = data[0]
      token = model.get_value(iter, 0)
      if token.start <= line and token.end > line:
        # print path
        data[1].append(path)
        #return True
      return False

    path_found = []
    model.foreach(find_path, (linenumber, path_found))

    if len(path_found) > 0:
      return path_found[-1]
    return None

  def pixbufrenderer(self, treeviewcolumn, cellrendererpixbuf, treemodel, it):
    token = treemodel.get_value(it,0)
    if token.type == 'path':
      cellrendererpixbuf.set_property("stock-id", gtk.STOCK_DIRECTORY)
    elif token.type == 'file':
      cellrendererpixbuf.set_property("stock-id", gtk.STOCK_FILE)
    else:
      cellrendererpixbuf.set_property("pixbuf",imagelibrary.pixbufs['patch'])

# -*- coding: utf-8 -*-
# Copyright (C) 2007 Kristoffer Lundén (kristoffer.lunden@gmail.com)
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place, Suite 330,
# Boston, MA 02111-1307, USA.

import gtk
import gobject
import pango
import os
import options
import imagelibrary
from parserinterface import ClassParserInterface

class Token:
  def __init__(self):
    self.start = 0
    self.end = 0
    self.name = None
    self.parent = None
    self.children = []
    self.type = 'changeset'

class DiffParser(ClassParserInterface):

  def parse(self, geditdoc):
    text = geditdoc.get_text(*geditdoc.get_bounds())
    linecount = -1
    current_file = None
    changeset = None
    files = []
    uri = geditdoc.get_uri()

    for line in text.splitlines():
      linecount += 1
      lstrip = line.lstrip()
      ln = lstrip.split()
      if len(ln) == 0: continue

      if ln[0] == '---':
        if current_file is not None:
          current_file.end = linecount - 1
        current_file = Token()
        current_file.name = ln[1]
        current_file.start = linecount
        current_file.type = 'file'
        current_file.uri = uri
        files.append(current_file)

      elif current_file == None: continue

      elif ln[0] == '@@' and ln[-1] == '@@':
        if changeset is not None:
          changeset.end = linecount
        changeset = Token()
        changeset.name = ' '.join(ln[1:-1])
        changeset.start = linecount
        changeset.uri = uri
        current_file.children.append(changeset)
        changeset.parent = current_file

      # Ending line of last tokens
      if len(files) > 0:
        f =  files[-1]
        f.end = linecount + 2
        if len(f.children) > 0:
          f.children[-1].end = linecount + 2

    model = gtk.TreeStore(gobject.TYPE_PYOBJECT)

    pp = None

    # "Fake" common top folder, if any
    # TODO: Create hierarchy if patch applies in multiple directories
    if len(files) > 0:
      paths = map(lambda f:f.name, files)
      prefix = os.path.dirname(os.path.commonprefix(paths)) + '/'
      if len(prefix) > 1:
        parent_path = Token()
        parent_path.type = 'path'
        parent_path.name = prefix
        for f in files: f.name = f.name.replace(prefix,'',1)
        pp = model.append(None,(parent_path,))

    # Build tree
    for f in files:
      tree_iter = model.append(pp,(f,))
      for c in f.children:
         model.append(tree_iter,(c,))

    return model

  def cellrenderer(self, treeviewcolumn, cellrenderertext, treemodel, it):
    token = treemodel.get_value(it,0)

    colour = options.singleton().colours["member"]

    if token.type == 'path':
      colour = options.singleton().colours["namespace"]
    elif token.type == 'file':
      colour = options.singleton().colours["class"]

    cellrenderertext.set_property("text", token.name)
    cellrenderertext.set_property("style", pango.STYLE_NORMAL)
    cellrenderertext.set_property("foreground-gdk", colour)

  def get_tag_position(self, model, path):
    tok = model.get_value(model.get_iter(path),0)
    try: return tok.uri, tok.start + 1
    except: return None

  def get_tag_at_line(self, model, doc, linenumber):

    def find_path(model, path, iter, data):
      line = data[0]
      token = model.get_value(iter, 0)
      if token.start <= line and token.end > line:
        # print path
        data[1].append(path)
        #return True
      return False

    path_found = []
    model.foreach(find_path, (linenumber, path_found))

    if len(path_found) > 0:
      return path_found[-1]
    return None

  def pixbufrenderer(self, treeviewcolumn, cellrendererpixbuf, treemodel, it):
    token = treemodel.get_value(it,0)
    if token.type == 'path':
      cellrendererpixbuf.set_property("stock-id", gtk.STOCK_DIRECTORY)
    elif token.type == 'file':
      cellrendererpixbuf.set_property("stock-id", gtk.STOCK_FILE)
    else:
      cellrendererpixbuf.set_property("pixbuf",imagelibrary.pixbufs['patch'])

########NEW FILE########
__FILENAME__ = parser_html
from parserinterface import ClassParserInterface
from HTMLParser import HTMLParser, HTMLParseError
import gtk

#=================================================================================================

class customParser(HTMLParser):

    def __init__(self):
        HTMLParser.__init__(self)
        # id, description, line, offset, [pixbuf]
        self.ls = gtk.TreeStore( str, str, int, int )
        self.currenttag = None

    def handle_starttag(self, tag, attrs):

        # construct tagstring
        tagstring = "<"+tag
        for name, value in attrs:
            if name in ["id","name"]: # append only certain attributes
                tagstring += " %s=%s"%(name,value)
        tagstring += ">"
        #print tagstring

        lineno, offset = self.getpos()
        it = self.ls.append( self.currenttag,(tag,tagstring,lineno,0) )
        #print (tag,tagstring,lineno,0)
        self.currenttag = it


    def handle_endtag(self, tag):

        if self.currenttag:
            t = self.ls.get_value(self.currenttag,0)
            if tag == t:
                #print "</%s>"%tag
                self.currenttag = self.ls.iter_parent(self.currenttag)

#=================================================================================================

class geditHTMLParser( ClassParserInterface ):


    def parse(self, d):
        parser = customParser()
        try: parser.feed(d.get_text(*d.get_bounds()))
        except HTMLParseError, e:
            print e.lineno, e.offset

        return parser.ls

    def cellrenderer(self, treeviewcolumn, ctr, treemodel, it):
        name = treemodel.get_value(it,1)
        ctr.set_property("text", name)

    #------------------------------------------- methods that can be implemented

    def pixbufrenderer(self, treeviewcolumn, cellrendererpixbuf, treemodel, it):
        """ A cell renderer callback function that controls what the pixmap next
        to the label in the browser tree looks like.
        See gtk.TreeViewColumn.set_cell_data_func for more information. """
        cellrendererpixbuf.set_property("pixbuf",None)


    def get_tag_position(self, model, path):
        """ Return the position of a tag in a file. This is used by the browser
        to jump to a symbol's position.

        Returns a tuple with the full file uri of the source file and the line
        number of the tag or None if the tag has no correspondance in a file.

        model -- a gtk.TreeModel (previously provided by parse())
        path -- a tuple containing the treepath
        """

        return


    def get_menu(self, model, path):
        """ Return a list of gtk.Menu items for the specified tag.
        Defaults to an empty list

        model -- a gtk.TreeModel (previously provided by parse())
        path -- a tuple containing the treepath
        """
        return []


    def current_line_changed(self, model, doc, line):
        """ Called when the cursor points to a different line in the document.
        Can be used to monitor changes in the document.

        model -- a gtk.TreeModel (previously provided by parse())
        doc -- a gedit document
        line -- int
        """
        pass


    def get_tag_at_line(self, model, doc, linenumber):
        """ Return a treepath to the tag at the given line number, or None if a
        tag can't be found.

        model -- a gtk.TreeModel (previously provided by parse())
        doc -- a gedit document
        linenumber -- int
        """

        #print "="*80

        self.lastit = None
        def iterate(model, path, it):
            #print model.get_value(it,2)
            line = model.get_value(it,2)
            if line > linenumber: return True # exit, lastpath contains tag
            self.lastit = it

        model.foreach(iterate)
        #print self.lastit, "-----"*20
        return model.get_path(self.lastit)

########NEW FILE########
__FILENAME__ = parser_php
# Copyright (C) 2007 Frederic Back (fredericback@gmail.com)
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place, Suite 330, 
# Boston, MA 02111-1307, USA.

import gtk
import gobject
from parser_cstyle import Token, CStyleCodeParser
import re


e = r".*?" # anything, but *not greedy*
e+= "(?:(private|protected) +)?" # visibility
e+= "function +(\w+)(\(.*\))" # function declaration
e+= " *\{$" # the tail
RE_FUNCTION = re.compile(e)
RE_CLASS = re.compile(r".*class +(\w+)(?: +extends +(\w+))? *\{$")
        
        
class PHPParser( CStyleCodeParser ):

    def __init__(self):
        pass


    def getTokenFromChunk(self, chunk):
        if chunk.find("function")>-1 or chunk.find("class")>-1:
            
            # third step: perform regular expression to get a token
            match = re.match(RE_FUNCTION,chunk)
            if match:
                t = Token("function")
                t.visibility, t.name, t.params = match.groups()
                #print match.groups()
                return t
                
            else:
                match = re.match(RE_CLASS,chunk)
                if match:
                    t = Token("class")
                    t.name, t.params = match.groups()
                    return t

                else:
                
                    # last step: alert user if a chunk could not be parsed
                    #print "Could not resolve PHP function or class in the following string:"
                    #print chunk
                    
                    pass

        return None
        



########NEW FILE########
__FILENAME__ = parser_python
# Copyright (C) 2006 Frederic Back (fredericback@gmail.com)
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place, Suite 330,
# Boston, MA 02111-1307, USA.

import gtk
import gobject
import pango
import os
import re
import options
from parserinterface import ClassParserInterface
import imagelibrary

#===============================================================================

def functionTokenFromString(string):
    """ Parse a string containing a function or class definition and return
        a tuple containing information about the function, or None if the
        parsing failed.

        Example:
            "#def foo(bar):" would return :
            {'comment':True,'type':"def",'name':"foo",'params':"bar" } """

    try:
        e = r"([# ]*?)([a-zA-Z0-9_]+)( +)([a-zA-Z0-9_]+)(.*)"
        r = re.match(e,string).groups()
        token = Token()
        token.comment = '#' in r[0]
        token.type = r[1]
        token.name = r[3]
        token.params = r[4]
        token.original = string
        return token
    except: return None # return None to skip if unable to parse


#===============================================================================

class Token:
    """ Rules:
            type "attribute" may only be nested to "class"
    """

    def __init__(self):
        self.type = None # "attribute", "class" or "function"
        self.original = None # the line in the file, unparsed

        self.indent = 0
        self.name = None
        self.comment = False # if true, the token is commented, ie. inactive
        self.params = None   # string containing additional info
        self.expanded = False

        # start and end points (line number)
        self.start = 0
        self.end = 0

        self.pythonfile = None
        self.path = None # save the position in the browser

        self.parent = None
        self.children = [] # a list of nested tokens
        self.attributes = [] # a list of class attributes


    def get_endline(self):
        """ Get the line number where this token's declaration, including all
            its children, finishes. Use it for copy operations."""
        if len(self.children) > 0:
            return self.children[-1].get_endline()
        return self.end

        def test_nested():
            pass

    def get_toplevel_class(self):
        """ Try to get the class a token is in. """

        if self.type == "class":
            return self

        if self.parent is not None:
            tc = self.parent.get_toplevel_class()
            if tc is None or tc.type == "file": return self #hack
            else: return tc

        return None

    def printout(self):
        for r in range(self.indent): print "",
        print self.name,
        if self.parent: print " (parent: ",self.parent.name
        else: print
        for tok in self.children: tok.printout()

#===============================================================================

class PythonFile(Token):
    """ A class that represents a python file.
        Manages "tokens", ie. classes and functions."""

    def __init__(self, doc):
        Token.__init__(self)
        self.doc = doc
        self.uri = doc.get_uri()
        self.linestotal = 0 # total line count
        self.type = "file"
        self.name = os.path.basename(self.uri)
        self.tokens = []

    def getTokenAtLine(self, line):
        """ get the token at the specified line number """
        for token in self.tokens:
            if token.start <= line and token.end > line:
                return token
        return None

    def parse(self, verbose=True):

        #if verbose: print "parse ----------------------------------------------"
        newtokenlist = []

        indent = 0
        lastElement = None

        self.children = []

        lastToken = None
        indentDictionary = { 0: self, } # indentation level: token

        self.linestotal = self.doc.get_line_count()

        text = self.doc.get_text(*self.doc.get_bounds())
        linecount = -1
        for line in text.splitlines():
            linecount += 1
            lstrip = line.lstrip()
            ln = lstrip.split()
            if len(ln) == 0: continue

            if ln[0] in ("class","def","#class","#def"):

                token = functionTokenFromString(lstrip)
                if token is None: continue
                token.indent = len(line)-len(lstrip)
                token.pythonfile = self

                token.original = line

                # set start and end line of a token. The end line will get set
                # when the next token is parsed.
                token.start = linecount
                if lastToken: lastToken.end = linecount
                newtokenlist.append(token)

                #if verbose: print "appending",token.name,
                if token.indent == indent:
                    # as deep as the last row: append the last e's parent
                    #if verbose: print "(%i == %i)"%(token.indent,indent),
                    if lastToken: p = lastToken.parent
                    else: p = self
                    p.children.append(token)
                    token.parent = p
                    indentDictionary[ token.indent ] = token

                elif token.indent > indent:
                    # this row is deeper than the last, use last e as parent
                    #if verbose: print "(%i > %i)"%(token.indent,indent),
                    if lastToken: p = lastToken
                    else: p = self
                    p.children.append(token)
                    token.parent = p
                    indentDictionary[ token.indent ] = token

                elif token.indent < indent:
                    # this row is shallower than the last
                    #if verbose: print "(%i < %i)"%(token.indent,indent),
                    if token.indent in indentDictionary.keys():
                        p = indentDictionary[ token.indent ].parent
                    else: p = self
                    if p == None: p = self # might happen with try blocks
                    p.children.append(token)
                    token.parent = p

                #if verbose: print "to",token.parent.name
                idx = len(newtokenlist) - 1
                if idx < len(self.tokens):
                    if newtokenlist[idx].original == self.tokens[idx].original:
                        newtokenlist[idx].expanded = self.tokens[idx].expanded
                lastToken = token
                indent = token.indent

            # not a class or function definition
            else:

                # check for class attributes, append to last class in last token
                try:
                    # must match "self.* ="
                    if ln[0][:5] == "self." and ln[1] == "=":

                        # make sure there is only one dot in the declaration
                        # -> attribute is direct descendant of the class
                        if lastToken and ln[0].count(".") == 1:
                            attr = ln[0].split(".")[1]
                            self.__appendClassAttribute(lastToken,attr,linecount)

                except IndexError: pass

        # set the ending line of the last token
        if len(newtokenlist) > 0:
            newtokenlist[ len(newtokenlist)-1 ].end = linecount + 2 # don't ask

        # set new token list
        self.tokens = newtokenlist
        return True

    def __appendClassAttribute(self, token, attrName, linenumber):
        """ Append a class attribute to the class a given token belongs to. """

        # get next parent class
        while token.type != "class":
            token = token.parent
            if not token: return

        # make sure attribute is not set yet
        for i in token.attributes:
            if i.name == attrName: return

        # append a new attribute
        attr = Token()
        attr.type = "attribute"
        attr.name = attrName
        attr.start = linenumber
        attr.end = linenumber
        attr.pythonfile = self
        token.attributes.append(attr)

#===============================================================================

class PythonParser( ClassParserInterface ):
    """ A class parser that uses ctags.

    Note that this is a very rough and hackish implementation.
    Feel free to improve it.

    See http://ctags.sourceforge.net for more information about exuberant ctags,
    and http://ctags.sourceforge.net/FORMAT for a description of the file format.
    """

    def __init__(self, geditwindow):
        self.geditwindow = geditwindow
        self.pythonfile = None


    def appendTokenToBrowser(self, token, parentit ):
        it = self.__browsermodel.append(parentit,(token,))
        token.path = self.__browsermodel.get_path(it)

        # add special subtree for attributes
        if len(token.attributes) > 0:

            holder = Token()
            holder.name = "Attributes"
            holder.type = "attribute"
            it2 = self.__browsermodel.append(it,(holder,))

            for child in token.attributes   :
                self.__browsermodel.append(it2,(child,))

        #if token.parent:
        #    if token.parent.expanded:
        #        self.browser.expand_row(token.parent.path,False)
        #        pass

        for child in token.children:
            self.appendTokenToBrowser(child, it)


    def get_menu(self, model, path):
        """ The context menu is expanded if the python tools plugin and
            bicyclerepairman are available. """

        menuitems = []

        try: tok = model.get_value( model.get_iter(path), 0 )
        except: tok = None
        pt = self.geditwindow.get_data("PythonToolsPlugin")
        tagposition = self.get_tag_position(model,path)

        if pt and tok and tagposition:

            filename, line = tagposition # unpack the location of the token
            if tok.type in ["def","class"] and filename[:7] == "file://":

                # print tok.original

                # trunkate to local filename
                filename = filename[7:]
                column = tok.original.find(tok.name) # find beginning of function definition
                # print filename, line, column

                item = gtk.MenuItem("Find References")
                menuitems.append(item)
                item.connect("activate",lambda w: pt.brm.findReferencesDialog(filename,line,column))

        return menuitems


    def parse(self, doc):
        """
        Create a gtk.TreeModel with the class elements of the document

        The parser uses the ctags command from the shell to create a ctags file,
        then parses the file, and finally populates a treemodel.
        """

        self.pythonfile = PythonFile(doc)
        self.pythonfile.parse(options.singleton().verbose)
        self.__browsermodel = gtk.TreeStore(gobject.TYPE_PYOBJECT)
        for child in self.pythonfile.children:
            self.appendTokenToBrowser(child,None)
        return self.__browsermodel


    def get_tag_position(self, model, path):
        tok = model.get_value( model.get_iter(path), 0 )
        try: return tok.pythonfile.uri, tok.start+1
        except: return None


    def current_line_changed(self, model, doc, line):

        # parse again if line count changed
        if abs(self.pythonfile.linestotal - doc.get_line_count()) > 0:
            if abs(self.pythonfile.linestotal - doc.get_line_count()) > 5:
                if options.singleton().verbose:
                    print "PythonParser: refresh because line dif > 5"
                self.pythonfile.parse()
            else:
                it = doc.get_iter_at_line(line)
                a = it.copy(); b = it.copy()
                a.backward_line(); a.backward_line()
                b.forward_line(); b.forward_line()

                t = doc.get_text(a,b)
                if t.find("class") >= 0 or t.find("def") >= 0:
                    if options.singleton().verbose:
                        print "PythonParser: refresh because line cound changed near keyword"
                    self.pythonfile.parse()


    def get_tag_at_line(self, model, doc, linenumber):
        t = self.pythonfile.getTokenAtLine(linenumber)
        #print linenumber,t
        if t: return t.path


    def cellrenderer(self, column, ctr, model, it):

        """ Render the browser cell according to the token it represents. """
        tok = model.get_value(it,0)

        weight = 400
        style = pango.STYLE_NORMAL
        name = tok.name#+tok.params
        colour = options.singleton().colours[ "function" ]

        # set label and colour
        if tok.type == "class":
            name = "class "+name+tok.params
            colour = options.singleton().colours[ "class" ]
            weight = 600
        if tok.comment: name = "#"+name
        if tok.parent:
            if tok.parent.type == "class":
                colour = options.singleton().colours[ "member" ]

        # assing properties
        ctr.set_property("text", name)
        ctr.set_property("style", style)
        ctr.set_property("foreground-gdk", colour)


    def pixbufrenderer(self, column, crp, model, it):
        tok = model.get_value(it,0)

        icon = "method" # for normal defs

        if tok.type == "class":
            icon = "class"
        elif tok.type == "attribute":
            if tok.name[:2] == "__": icon = "field_priv"
            else: icon = "field"
        elif tok.parent:

            if tok.parent.type == "class":
                icon = "method"
                if tok.name[:2] == "__":
                    icon = "method_priv"


        crp.set_property("pixbuf",imagelibrary.pixbufs[icon])

########NEW FILE########
__FILENAME__ = parser_ruby
# -*- coding: utf-8 -*-
# Copyright (C) 2006 Frederic Back (fredericback@gmail.com)
# Copyright (C) 2007 Kristoffer Lundén (kristoffer.lunden@gmail.com)
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place, Suite 330, 
# Boston, MA 02111-1307, USA.

import gtk
import gobject
import pango
import os
import re
import options
from parserinterface import ClassParserInterface
import imagelibrary

#===============================================================================

def tokenFromString(string):
    """ Parse a string containing a function or class definition and return
        a tuple containing information about the function, or None if the
        parsing failed.

        Example: 
            "#def foo(bar):" would return :
            {'comment':True,'type':"def",'name':"foo",'params':"bar" } """

    try:
        e = r"([# ]*?)([a-zA-Z0-9_]+)( +)([a-zA-Z0-9_\?\!<>\+=\.]+)(.*)"
        r = re.match(e,string).groups()
        token = Token()
        token.comment = '#' in r[0]
        token.type = r[1]
        token.name = r[3]
        token.params = r[4]
        token.original = string
        return token
    except: return None # return None to skip if unable to parse
    
    def test():
        pass

#===============================================================================

class Token:
    def __init__(self):
        self.type = None
        self.original = None # the line in the file, unparsed

        self.indent = 0
        self.name = None
        self.comment = False # if true, the token is commented, ie. inactive
        self.params = None   # string containing additional info
        self.expanded = False

        self.access = "public"

        # start and end points
        self.start = 0
        self.end = 0

        self.rubyfile = None
        self.path = None # save the position in the browser

        self.parent = None
        self.children = []

    def get_endline(self):
        """ Get the line number where this token's declaration, including all
            its children, finishes. Use it for copy operations."""
        if len(self.children) > 0:
            return self.children[-1].get_endline()
        return self.end

        def test_nested():
            pass
            
    def get_toplevel_class(self):
        """ Try to get the class a token is in. """
            
        if self.type == "class":
            return self    

        if self.parent is not None:
            tc = self.parent.get_toplevel_class()
            if tc is None or tc.type == "file": return self #hack
            else: return tc
                
        return None

    def printout(self):
        for r in range(self.indent): print "",
        print self.name,
        if self.parent: print " (parent: ",self.parent.name       
        else: print
        for tok in self.children: tok.printout()

#===============================================================================

class RubyFile(Token):
    """ A class that represents a ruby file.
        Manages "tokens", ie. classes and functions."""

    def __init__(self, doc):
        Token.__init__(self)
        self.doc = doc
        self.uri = doc.get_uri()
        self.linestotal = 0 # total line count
        self.type = "file"
        self.name = os.path.basename(self.uri)
        self.tokens = []


    def getTokenAtLine(self, line):
        """ get the token at the specified line number """
        for token in self.tokens:
            if token.start <= line and token.end > line:
                return self.__findInnermostTokenAtLine(token, line)
        return None

    def __findInnermostTokenAtLine(self, token, line):
        """" ruby is parsed as nested, unlike python """
        for child in token.children:
            if child.start <= line and child.end > line:
                return self.__findInnermostTokenAtLine(child, line)
        return token


    def parse(self, verbose=True):

        #if verbose: print "parse ----------------------------------------------"
        newtokenlist = []

        self.children = []

        currentParent = self

        self.linestotal = self.doc.get_line_count()

        text = self.doc.get_text(*self.doc.get_bounds())
        linecount = -1
        ends_to_skip = 0
        
        access = "public"
        
        for line in text.splitlines():
            linecount += 1
            lstrip = line.lstrip()
            ln = lstrip.split()
            if len(ln) == 0: continue
            if ln[0] == '#': continue
            
            if ln[0] in ("class","module","def"):
                token = tokenFromString(lstrip)
                if token is None: continue
                token.rubyfile = self
                token.start = linecount
                if token.type == "def":
                    token.access = access
                    
                #print "line",linecount
                #print "name", token.name
                #print "type",token.type
                #print "access",token.access
                #print "to",currentParent.name
                
                currentParent.children.append(token)
                token.parent = currentParent
                currentParent = token
                newtokenlist.append(token)
                
                
                idx = len(newtokenlist) - 1
                if idx < len(self.tokens):
                    if newtokenlist[idx].original == self.tokens[idx].original:
                        newtokenlist[idx].expanded = self.tokens[idx].expanded
                
            elif ln[0] in("begin","while","until","case","if","unless","for"):
                    ends_to_skip += 1
                    
            elif ln[0] in ("attr_reader","attr_writer","attr_accessor"):
                for attr in ln:
                    m = re.match(r":(\w+)",attr)
                    if m:
                        token = Token()
                        token.rubyfile = self
                        token.type = 'def'
                        token.name = m.group(1)
                        token.start = linecount
                        token.end = linecount
                        token.original = lstrip
                        currentParent.children.append(token)
                        token.parent = currentParent
                        newtokenlist.append(token)
            
            elif re.search(r"\sdo(\s+\|.*?\|)?\s*(#|$)", line):
                #print "do",line

                # Support for new style RSpec
                if re.match(r"^(describe|it|before|after)\b", ln[0]):
                    token = Token()
                    token.rubyfile = self
                    token.start = linecount
                    
                    if currentParent.type == "describe":                    
                        if ln[0] == "it":
                            token.name = " ".join(ln[1:-1])
                        else:
                            token.name = ln[0]
                        token.type = "def"
                    elif ln[0] == "describe":
                        token.type = "describe"
                        token.name = " ".join(ln[1:-1])
                    else:
                        continue
                    currentParent.children.append(token)
                    token.parent = currentParent
                    currentParent = token
                    newtokenlist.append(token)

                # Deprectated support for old style RSpec, will be removed later
                elif ln[0] in ("context","specify","setup","teardown","context_setup","context_teardown"):
                    token = Token()
                    token.rubyfile = self
                    token.start = linecount
                    
                    if currentParent.type == "context":                    
                        if ln[0] == "specify":
                            token.name = " ".join(ln[1:-1])
                        else:
                            token.name = ln[0]
                        token.type = "def"
                    elif ln[0] == "context":
                        token.type = "context"
                        token.name = " ".join(ln[1:-1])
                    else:
                        continue
                    currentParent.children.append(token)
                    token.parent = currentParent
                    currentParent = token
                    newtokenlist.append(token)
                else:
                    ends_to_skip += 1
                
            elif ln[0] in ("public","private","protected"):
                if len(ln) == 1:
                    access = ln[0]
                    
            if re.search(r";?\s*end(?:\s*$|\s+(?:while|until))", line):
                if ends_to_skip > 0:
                    ends_to_skip -= 1
                else:
                  token = currentParent
                  #print "end",currentParent.name
                  token.end = linecount
                  currentParent = token.parent
                

        # set new token list
        self.tokens = newtokenlist
        return True


#===============================================================================

class RubyParser( ClassParserInterface ):
    
    def __init__(self):
        self.rubyfile = None


    def appendTokenToBrowser(self, token, parentit ):
        it = self.__browsermodel.append(parentit,(token,))
        token.path = self.__browsermodel.get_path(it)
        #print token.path
        #if token.parent:
        #    if token.parent.expanded:
        #        self.browser.expand_row(token.parent.path,False)
        #        pass
        for child in token.children:
            self.appendTokenToBrowser(child, it)


    def parse(self, doc):
        """ 
        Create a gtk.TreeModel with the class elements of the document
        
        The parser uses the ctags command from the shell to create a ctags file,
        then parses the file, and finally populates a treemodel.
        """
    
        self.rubyfile = RubyFile(doc)
        self.rubyfile.parse(options.singleton().verbose)
        self.__browsermodel = gtk.TreeStore(gobject.TYPE_PYOBJECT)
        for child in self.rubyfile.children:
            self.appendTokenToBrowser(child,None)
        return self.__browsermodel

        
    def __private_test_method(self):
        pass


    def get_tag_position(self, model, path):
        tok = model.get_value( model.get_iter(path), 0 )
        try: return tok.rubyfile.uri, tok.start+1
        except: return None


    def current_line_changed(self, model, doc, line):

        # parse again if line count changed
        if abs(self.rubyfile.linestotal - doc.get_line_count()) > 0:
            if abs(self.rubyfile.linestotal - doc.get_line_count()) > 5:
                if options.singleton().verbose:
                    print "RubyParser: refresh because line dif > 5"
                self.rubyfile.parse()
            else:
                it = doc.get_iter_at_line(line)
                a = it.copy(); b = it.copy()
                a.backward_line(); a.backward_line()
                b.forward_line(); b.forward_line()

                t = doc.get_text(a,b)
                if t.find("class") >= 0 or t.find("def") >= 0:
                    if options.singleton().verbose:
                        print "RubyParser: refresh because line cound changed near keyword"
                    self.rubyfile.parse()
 

    def get_tag_at_line(self, model, doc, linenumber):
        t = self.rubyfile.getTokenAtLine(linenumber)
        #print linenumber,t
        if t: return t.path


    def cellrenderer(self, column, ctr, model, it):

        """ Render the browser cell according to the token it represents. """
        tok = model.get_value(it,0)

        weight = 400
        style = pango.STYLE_NORMAL
        name = tok.name#+tok.params
        colour = options.singleton().colours[ "function" ]

        # set label and colour
        if tok.type == "class":
            name = "class "+name
            colour = options.singleton().colours[ "class" ]
            weight = 600
            
        elif tok.type == "module":
            name = "module "+name
            colour = options.singleton().colours[ "namespace" ]
            weight = 600
            
        # new style RSpec
        elif tok.type == "describe":
            name = "describe "+name
            colour = options.singleton().colours[ "namespace" ]
            weight = 600
        
        # Old style RSpec, deprecated    
        elif tok.type == "context":
            name = "context "+name
            colour = options.singleton().colours[ "namespace" ]
            weight = 600
            
        elif tok.type == "def":
            colour = options.singleton().colours[ "member" ]
            
        if tok.comment: name = "#"+name

        # assing properties
        ctr.set_property("text", name)
        ctr.set_property("style", style)
        ctr.set_property("foreground-gdk", colour)


    def pixbufrenderer(self, column, crp, model, it):
        tok = model.get_value(it,0)

        icon = "default"

        if tok.type == "class":
            icon = "class"
        elif tok.type == "module":
            icon = "namespace"
        elif tok.type == "describe":
            icon = "namespace"
        elif tok.type == "context":
            icon = "namespace"
        elif tok.type == "def":
            if tok.access == "public":
                icon = "method"
            elif tok.access == "protected":
                icon = "method_prot"
            elif tok.access == "private":
                icon = "method_priv"
                
        crp.set_property("pixbuf",imagelibrary.pixbufs[icon])

        

########NEW FILE########
__FILENAME__ = tabwatch
# Copyright (C) 2006 Frederic Back (fredericback@gmail.com)
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place, Suite 330, 
# Boston, MA 02111-1307, USA.

import gtk
import options

#-------------------------------------------------------------------------------        
class TabWatch:
    """ Monitor the tabs in gedit to find out when documents get opened or
        changed. """

    def __init__(self, window, classbrowser):
        self.browser = classbrowser   
        self.geditwindow = window
        self.geditwindow.connect("tab_added",self.__tab_added_or_activated)
        self.geditwindow.connect("tab_removed",self.__tab_removed)
        self.geditwindow.connect("active_tab_changed",self.__tab_added_or_activated)
        
        self.openfiles = []
        self.currentDoc = None
        self.languageParsers = {}
        self.defaultparser = None
    
    def register_parser(self, mimetype, parser):
        """ register a new class parser to use with a certain mime type.
            language -- a string (see gtksourceview languages for reference)
            parser -- an instance of ClassParserInterface """
        self.languageParsers[mimetype] = parser  
    
    def __tab_added_or_activated(self, window, tab):
        self.__register(tab.get_document(),tab)
        doc = self.geditwindow.get_active_document()
        if doc != self.currentDoc: self.__update()

    def __tab_removed(self, window, tab):
        self.__unregister(tab.get_document())

        doc = self.geditwindow.get_active_document()
        if doc != self.currentDoc: self.__update()

    def __register(self, doc, tab):
        if doc is None: return
        uri = doc.get_uri()
        if uri in self.openfiles: return
        self.openfiles.append(uri)
        tab.get_view().connect_after("notify",self.browser.on_cursor_changed)
        tab.get_view().connect_after("move-cursor",self.browser.update_cursor)

        #doc.set_modified(True)
        doc.connect("modified-changed",self.__update)
        if options.singleton().verbose: print "added:",uri

    def __unregister(self, doc):
        if doc is None: return
        uri = doc.get_uri()
        if uri not in self.openfiles: return
        self.openfiles.remove(uri)  
        #if options.singleton().verbose: print "removed:",uri

    def __update(self, *args):
        doc = self.geditwindow.get_active_document()
        if doc:
                
            lang = doc.get_language()
            parser = self.defaultparser
            if lang:
                m = lang.get_name()
                if m in self.languageParsers: parser = self.languageParsers[m]

            if options.singleton().verbose:
                print "parse %s (%s)"%(doc.get_uri(),parser.__class__.__name__)
            model = parser.parse(doc)
            self.browser.set_model(model, parser)
            self.currentDoc = doc

        else:
            self.browser.set_model(None)

########NEW FILE########
__FILENAME__ = completion
# Copyright (C) 2006-2008 Osmo Salomaa
#
# This program is free software; you can redistribute it and/or modify it under
# the terms of the GNU General Public License as published by the Free Software
# Foundation; either version 2 of the License, or (at your option) any later
# version.
#
# This program is distributed in the hope that it will be useful, but WITHOUT
# ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS
# FOR A PARTICULAR PURPOSE. See the GNU General Public License for more
# details.
#
# You should have received a copy of the GNU General Public License along with
# this program; if not, write to the Free Software Foundation, Inc., 51
# Franklin Street, Fifth Floor, Boston, MA 02110-1301, USA.

"""Complete words with the tab key.

This plugin provides a 'stupid' word completion plugin, one that is aware of
all words in all open documents, but knows nothing of any context or syntax.
This plugin can be used to speed up writing and to avoid spelling errors in
either regular text documents or in programming documents if no programming
language -aware completion is available.

Words are automatically scanned at regular intervals. Once you have typed a
word and the interval has passed, the word is available in the completion
system. A completion window listing possible completions is shown and updated
as you type. You can complete to the topmost word in the window with the Tab
key, or choose another completion with the arrow keys and complete with the Tab
key. The keybindinds are configurable only by editing the source code.
"""

import gedit
import gobject
import gtk
import pango
import re


class CompletionWindow(gtk.Window):

    """Window for displaying a list of words to complete to.

    This is a popup window merely to display words. This window is not meant
    to receive or handle input from the user, rather the various methods should
    be called to chang the list of words and which one of them is selected.
    """

    def __init__(self, parent):

        gtk.Window.__init__(self, gtk.WINDOW_POPUP)
        self._store = None
        self._view = None
        self.set_transient_for(parent)
        self._init_view()
        self._init_containers()

    def _init_containers(self):
        """Initialize the frame and the scrolled window."""

        scroller = gtk.ScrolledWindow()
        scroller.set_policy(*((gtk.POLICY_NEVER,) * 2))
        scroller.add(self._view)
        frame = gtk.Frame()
        frame.set_shadow_type(gtk.SHADOW_OUT)
        frame.add(scroller)
        self.add(frame)

    def _init_view(self):
        """Initialize the tree view listing the complete words."""

        self._store = gtk.ListStore(gobject.TYPE_STRING)
        self._view = gtk.TreeView(self._store)
        renderer = gtk.CellRendererText()
        renderer.xpad = renderer.ypad = 6
        column = gtk.TreeViewColumn("", renderer, text=0)
        self._view.append_column(column)
        self._view.set_enable_search(False)
        self._view.set_headers_visible(False)
        self._view.set_rules_hint(True)
        selection = self._view.get_selection()
        selection.set_mode(gtk.SELECTION_SINGLE)

    def get_selected(self):
        """Return the index of the selected row."""

        selection = self._view.get_selection()
        return selection.get_selected_rows()[1][0][0]

    def select_next(self):
        """Select the next complete word."""

        row = min(self.get_selected() + 1, len(self._store) - 1)
        selection = self._view.get_selection()
        selection.unselect_all()
        selection.select_path(row)
        self._view.scroll_to_cell(row)

    def select_previous(self):
        """Select the previous complete word."""

        row = max(self.get_selected() - 1, 0)
        selection = self._view.get_selection()
        selection.unselect_all()
        selection.select_path(row)
        self._view.scroll_to_cell(row)

    def set_completions(self, completions):
        """Set the completions to display."""

        # 'gtk.Window.resize' followed later by 'gtk.TreeView.columns_autosize'
        # will allow the window to either grow or shrink to fit the new data.
        self.resize(1, 1)
        self._store.clear()
        for word in completions:
            self._store.append((word,))
        self._view.columns_autosize()
        self._view.get_selection().select_path(0)

    def set_font_description(self, font_desc):
        """Set the font description used in the view."""

        self._view.modify_font(font_desc)


class CompletionPlugin(gedit.Plugin):

    """Complete words with the tab key.

    Instance variables are as follows. '_completion_windows' is a dictionary
    mapping 'gedit.Windows' to 'CompletionWindows'.

    '_all_words' is a dictionary mapping documents to a frozen set containing
    all words in the document. '_favorite_words' is a dictionary mapping
    documents to a set of words that the user has completed to. Favorites are
    thus always document-specific and there are no degrees to favoritism. These
    favorites will be displayed at the top of the completion window. As
    '_all_words' and '_favorite_words' are both sets, the exact order in which
    the words are listed in the completion window is unpredictable.

    '_completions' is a list of the currently active complete words, shown in
    the completion window, that the user can complete to. Similarly '_remains'
    is a list of the untyped parts the _completions, i.e. the part that will be
    inserted when the user presses the Tab key. '_completions' and '_remains'
    always contain words for the gedit window, document and text view that has
    input focus.

    '_font_ascent' is the ascent of the font used in gedit's text view as
    reported by pango. It is needed to be able to properly place the completion
    window right below the caret regardless of the font and font size used.
    """

    # Unlike gedit itself, consider underscores alphanumeric characters
    # allowing completion of identifier names in many programming languages.
    _re_alpha = re.compile(r"\w+", re.UNICODE | re.MULTILINE)
    _re_non_alpha = re.compile(r"\W+", re.UNICODE | re.MULTILINE)

    # TODO: Are these sane defaults? Do we need a configuration dialog?
    _scan_frequency = 10000 # ms
    _max_completions_to_show = 6

    def __init__(self):

        gedit.Plugin.__init__(self)
        self._all_words = {}
        self._completion_windows = {}
        self._completions = []
        self._favorite_words = {}
        self._font_ascent = 0
        self._remains = []

    def _complete_current(self):
        """Complete the current word."""

        window = gedit.app_get_default().get_active_window()
        doc = window.get_active_document()
        index = self._completion_windows[window].get_selected()
        doc.insert_at_cursor(self._remains[index])
        words = self._favorite_words.setdefault(doc, set(()))
        words.add(self._completions[index])
        self._terminate_completion()

    def _connect_document(self, doc):
        """Connect to document's 'loaded' signal."""

        callback = lambda doc, x, self: self._scan_document(doc)
        handler_id = doc.connect("loaded", callback, self)
        doc.set_data(self.__class__.__name__, (handler_id,))

    def _connect_view(self, view, window):
        """Connect to view's editing signals."""

        callback = lambda x, y, self: self._terminate_completion()
        id_1 = view.connect("focus-out-event", callback, self)
        callback = self._on_view_key_press_event
        id_2 = view.connect("key-press-event", callback, window)
        view.set_data(self.__class__.__name__, (id_1, id_2))

    def _display_completions(self, view, event):
        """Find completions and display them in the completion window."""

        doc = view.get_buffer()
        insert = doc.get_iter_at_mark(doc.get_insert())
        start = insert.copy()
        while start.backward_char():
            char = unicode(start.get_char())
            if not self._re_alpha.match(char):
                start.forward_char()
                break
        incomplete = unicode(doc.get_text(start, insert))
        incomplete += unicode(event.string)
        if incomplete.isdigit():
            # Usually completing numbers is not a good idea.
            return self._terminate_completion()
        self._find_completions(doc, incomplete)
        if not self._completions:
            return self._terminate_completion()
        self._show_completion_window(view, insert)

    def _find_completions(self, doc, incomplete):
        """Find completions for incomplete word and save them."""

        self._completions = []
        self._remains = []
        favorites = self._favorite_words.get(doc, ())
        _all_words = set(())
        for words in self._all_words.itervalues():
            _all_words.update(words)
        limit = self._max_completions_to_show
        for sequence in (favorites, _all_words):
            for word in sequence:
                if not word.startswith(incomplete): continue
                if word == incomplete: continue
                if word in self._completions: continue
                self._completions.append(word)
                self._remains.append(word[len(incomplete):])
                if len(self._remains) >= limit: break

    def _on_view_key_press_event(self, view, event, window):
        """Manage actions for completions and the completion window."""

        if event.state & gtk.gdk.CONTROL_MASK:
            return self._terminate_completion()
        if event.state & gtk.gdk.MOD1_MASK:
            return self._terminate_completion()
        if (event.keyval == gtk.keysyms.Return) and self._remains:
            return not self._complete_current()
        completion_window = self._completion_windows[window]
        if (event.keyval == gtk.keysyms.Up) and self._remains:
            return not completion_window.select_previous()
        if (event.keyval == gtk.keysyms.Down) and self._remains:
            return not completion_window.select_next()
        string = unicode(event.string)
        if len(string) != 1:
            # Do not suggest completions after pasting text.
            return self._terminate_completion()
        if self._re_alpha.match(string) is None:
            return self._terminate_completion()
        doc = view.get_buffer()
        insert = doc.get_iter_at_mark(doc.get_insert())
        if self._re_alpha.match(unicode(insert.get_char())):
            # Do not suggest completions in the middle of a word.
            return self._terminate_completion()
        return self._display_completions(view, event)

    def _on_window_tab_added(self, window, tab):
        """Connect to signals of the document and view in tab."""

        self._update_fonts(tab.get_view())
        name = self.__class__.__name__
        doc = tab.get_document()
        handler_id = doc.get_data(name)
        if handler_id is None:
            self._connect_document(doc)
        view = tab.get_view()
        handler_id = view.get_data(name)
        if handler_id is None:
            self._connect_view(view, window)

    def _on_window_tab_removed(self, window, tab):
        """Remove closed document's word and favorite sets."""

        doc = tab.get_document()
        self._all_words.pop(doc, None)
        self._favorite_words.pop(doc, None)

    def _scan_active_document(self, window):
        """Scan all the words in the active document in window."""

        # Return False to not scan again.
        if window is None: return False
        doc = window.get_active_document()
        if doc is not None:
            self._scan_document(doc)
        return True

    def _scan_document(self, doc):
        """Scan and save all words in document."""

        text = unicode(doc.get_text(*doc.get_bounds()))
        self._all_words[doc] = frozenset(self._re_non_alpha.split(text))

    def _show_completion_window(self, view, itr):
        """Show the completion window below the caret."""

        text_window = gtk.TEXT_WINDOW_WIDGET
        rect = view.get_iter_location(itr)
        x, y = view.buffer_to_window_coords(text_window, rect.x, rect.y)
        window = gedit.app_get_default().get_active_window()
        x, y = view.translate_coordinates(window, x, y)
        x += window.get_position()[0] + self._font_ascent
        # Use 24 pixels as an estimate height for window title bar.
        # TODO: There must be a better way than a hardcoded pixel value.
        y += window.get_position()[1] + 24 + (2 * self._font_ascent)
        completion_window = self._completion_windows[window]
        completion_window.set_completions(self._completions)
        completion_window.move(int(x), int(y))
        completion_window.show_all()

    def _terminate_completion(self):
        """Hide the completion window and cancel completions."""

        window = gedit.app_get_default().get_active_window()
        self._completion_windows[window].hide()
        self._completions = []
        self._remains = []

    def _update_fonts(self, view):
        """Update font descriptions and ascent metrics."""

        context = view.get_pango_context()
        font_desc = context.get_font_description()
        if self._font_ascent == 0:
            # Acquiring pango metrics is a bit slow,
            # so do this only when absolutely needed.
            metrics = context.get_metrics(font_desc, None)
            self._font_ascent = metrics.get_ascent() / pango.SCALE
        for completion_window in self._completion_windows.itervalues():
            completion_window.set_font_description(font_desc)

    def activate(self, window):
        """Activate plugin."""

        callback = self._on_window_tab_added
        id_1 = window.connect("tab-added", callback)
        callback = self._on_window_tab_removed
        id_2 = window.connect("tab-removed", callback)
        window.set_data(self.__class__.__name__, (id_1, id_2))
        for doc in window.get_documents():
            self._connect_document(doc)
            self._scan_document(doc)
        views = window.get_views()
        for view in views:
            self._connect_view(view, window)
        if views: self._update_fonts(views[0])
        self._completion_windows[window] = CompletionWindow(window)
        # Scan the active document in window if it has input focus
        # for new words at constant intervals.
        def scan(self, window):
            if not window.is_active(): return True
            return self._scan_active_document(window)
        freq = self._scan_frequency
        priority = gobject.PRIORITY_LOW
        gobject.timeout_add(freq, scan, self, window, priority=priority)

    def deactivate(self, window):
        """Deactivate plugin."""

        widgets = [window]
        widgets.extend(window.get_views())
        widgets.extend(window.get_documents())
        name = self.__class__.__name__
        for widget in widgets:
            for handler_id in widget.get_data(name):
                widget.disconnect(handler_id)
            widget.set_data(name, None)
        self._terminate_completion()
        self._completion_windows.pop(window)
        for doc in window.get_documents():
            self._all_words.pop(doc, None)
            self._favorite_words.pop(doc, None)


########NEW FILE########
__FILENAME__ = FindInFiles
import gedit
import gtk
import os
import gconf

class ResultsView(gtk.VBox):
    def __init__(self, geditwindow):
        gtk.VBox.__init__(self)
        
        # We have to use .geditwindow specifically here (self.window won't work)
        self.geditwindow = geditwindow
        
        # Save the document's encoding in a variable for later use (when opening new tabs)
        try: self.encoding = gedit.encoding_get_current()
        except: self.encoding = gedit.gedit_encoding_get_current()
        
        # Preferences (we'll control them with toggled checkboxes)
        self.ignore_comments = False
        self.case_sensitive = False
        
        # We save the grep search result data in a ListStore
        # Format:  ID (COUNT)  |  FILE (without path)  |  LINE  |  FILE (with path)
        #    Note: We use the full-path version when opening new tabs (when necessary)
        self.search_data = gtk.ListStore(str, str, str, str)

        # Create a list (a "tree view" without children) to display the results
        self.results_list = gtk.TreeView(self.search_data)

        # Get the selection attribute of the results_list and assign a couple of properties
        tree_selection = self.results_list.get_selection()
        
        # Properties...
        tree_selection.set_mode(gtk.SELECTION_SINGLE)
        tree_selection.connect("changed", self.view_result)
        
        # Create the cells for our results list treeview
        #   Note:  We don't need to create a cell or text renderer
        #          for the full-path filename variable because we
        #          won't actually be displaying that information.
        cell_id = gtk.TreeViewColumn("#")        
        cell_line_number = gtk.TreeViewColumn("Line")
        cell_filename = gtk.TreeViewColumn("File")
        
        # Now add the cell objects to the results_list treeview object
        self.results_list.append_column(cell_id)
        self.results_list.append_column(cell_line_number)
        self.results_list.append_column(cell_filename)
        
        # Create text-rendering objects so that we can actually
        # see the data that we'll put into the objects
        text_renderer_id = gtk.CellRendererText()
        text_renderer_filename = gtk.CellRendererText()
        text_renderer_line_number = gtk.CellRendererText()
        
        # Pack the text renderer objects into the cell objects we created
        cell_id.pack_start(text_renderer_id, True)
        cell_filename.pack_start(text_renderer_filename, True)
        cell_line_number.pack_start(text_renderer_line_number, True)
        
        # Now set the IDs to each of the text renderer objects and set them to "text" mode
        cell_id.add_attribute(text_renderer_id, "text", 0)
        cell_filename.add_attribute(text_renderer_filename, "text", 1)
        cell_line_number.add_attribute(text_renderer_line_number, "text", 2)

        # Create a scrolling window object and add our results_list treeview object to it
        scrolled_window = gtk.ScrolledWindow()        
        scrolled_window.add(self.results_list)
        
        # Pack in the scrolled window object
        self.pack_start(scrolled_window)
        
        # Create a "Find" button; we'll pack it into an HBox in a moment...
        button_find = gtk.Button("Find")
        button_find.connect("clicked", self.button_press)
        # Create a "search bar" to type the search string into; we'll pack it
        # into the HBox as well...
        self.search_form = gtk.Entry()
        self.search_form.connect("activate", self.button_press)

        # Here's the HBox I mentioned...
        search_box = gtk.HBox(False, 0)
        search_box.pack_start(self.search_form, False, False)
        search_box.pack_start(button_find, False, False)
        
        # Pack the search box (search bar + Find button) into the side panel
        self.pack_start(search_box, False, False)
        
        # Create a check box to decide whether or not to ignore comments
        self.check_ignore = gtk.CheckButton("Ignore comments")
        self.check_ignore.connect("toggled", self.toggle_ignore)
        # Pack it in...
        self.pack_start(self.check_ignore, False, False)
        
        # Create a check box to determine whether to pay attention to case
        self.check_case = gtk.CheckButton("Case Sensitive")
        self.check_case.connect("toggled", self.toggle_case)
        # Pack it in...
        self.pack_start(self.check_case, False, False)
        
        # Show all UI elements
        self.show_all()

    # A click of the "Ignore comments" check box calls to this function        
    def toggle_ignore(self, widget):
        self.ignore_comments = not self.ignore_comments
        
    # A click of the "Case sensitive" check box calls to this function
    def toggle_case(self, widget):
        self.case_sensitive = not self.case_sensitive
        
    # A call goes to view_result whenever the user clicks on
    # one of the results after a search.  In response to the
    # click, we'll go to that file's tab (or open it in a 
    # new tab if they since closed that tab) and scroll to
    # the line that the result appears in.
    def view_result(self, widget):
        # Get the selection object
        tree_selection = self.results_list.get_selection()
        
        # Get the model and iterator for the row selected
        (model, iterator) = tree_selection.get_selected()
        
        if (iterator):
            # Get the absolute path of the file
            absolute_path = model.get_value(iterator, 3)
            
            # Get the line number
            line_number = int(model.get_value(iterator, 2)) - 1
            
            # Get all open tabs
            documents = self.geditwindow.get_documents()
            
            # Loop through the tabs until we find which one matches the file
            # If we don't find it, we'll create it in a new tab afterwards.
            for each in documents:
            
                if (each.get_uri().replace("file://", "") == absolute_path):
                    # This sets the active tab to "each"
                    self.geditwindow.set_active_tab(gedit.tab_get_from_document(each))
                    each.goto_line(line_number)

                    # Get the bounds of the document                        
                    (start, end) = each.get_bounds()
                    
                    self.geditwindow.get_active_view().scroll_to_iter(end, 0.0)
                    
                    x = each.get_iter_at_line_offset(line_number, 0)
                    self.geditwindow.get_active_view().scroll_to_iter(x, 0.0)
                    
                    return
                    
            # If we got this far, then we didn't find the file open in a tab.
            # Thus, we'll want to go ahead and open it...
            self.geditwindow.create_tab_from_uri("file://" + absolute_path, self.encoding, int(model.get_value(iterator, 2)), False, True)
        
    # Clicking the "Find" button or hitting return in the search area calls button_press.
    # This function, of course, searches each open document for the search query and
    # displays the results in the side panel.
    def button_press(self, widget):
        # Get all open tabs
        documents = self.geditwindow.get_documents()
        
        # Make sure there are documents to search...
        if (len(documents) == 0):
            return # Can't search nothing.  :P
            
        # Let's also make sure the user entered a search string
        if (len(self.search_form.get_text()) <= 0):
            return
        
        # Create a string that will hold all of the filenames;
        # we'll append it to the grep command string.
        string = ""
        
        fbroot = self.get_filebrowser_root()
        if fbroot != "" and fbroot is not None:
          location = fbroot.replace("file://", "")
        else:
          return

        hooray = os.popen ("find " + location + " -type f -not -regex '.*/.svn.*'").readlines()
        for hip in hooray:
          string += " '%s'" % hip[:-1]
        
        # str_case_operator will hold the "case insensitive" command if necessary
        str_case_operator = ""
        if (not self.case_sensitive):
            str_case_operator = " -i"

        # Create a pipe and call the grep command, then read it            
        pipe = os.popen("grep -n -H" + str_case_operator + " %s %s" % (self.search_form.get_text(), string))
        data = pipe.read()
        results = data.split("\n")
        
        # Clear any current results from the side panel
        self.search_data.clear()

        # Process each result...        
        for each in results:
            # Each result will look like this:
            #   FILE (absolute path):Line number:string
            #
            #   ... where string is the line that the search data was found in.
            pieces = each.split(":", 2)
            
            if (len(pieces) == 3):
                line_number = pieces[1]
                filename = os.path.basename(pieces[0]) # We just want the filename, not the path
                string = pieces[2].lstrip(" ") # Remove leading whitespace

                # If we want to ignore comments, then we'll make sure it doesn't start with # or //                        
                if (self.ignore_comments):
                    if (not string.startswith("#") and not string.startswith("//")):
                        self.search_data.append( ("%d" % (len(self.search_data) + 1), filename, line_number, pieces[0]) )
                else:            
                    self.search_data.append( ("%d" % (len(self.search_data) + 1), filename, line_number, pieces[0]) )
                    
    def get_filebrowser_root(self):
        base = u'/apps/gedit-2/plugins/filebrowser/on_load'
        client = gconf.client_get_default()
        client.add_dir(base, gconf.CLIENT_PRELOAD_NONE)
        path = os.path.join(base, u'virtual_root')
        val = client.get(path)
        if val is not None:
          #also read hidden files setting
          base = u'/apps/gedit-2/plugins/filebrowser'
          client = gconf.client_get_default()
          client.add_dir(base, gconf.CLIENT_PRELOAD_NONE)
          path = os.path.join(base, u'filter_mode')
          try:
            fbfilter = client.get(path).get_string()
          except AttributeError:
            fbfilter = "hidden"
          if fbfilter.find("hidden") == -1:
            self._show_hidden = True
          else:
            self._show_hidden = False
          return val.get_string()

class PluginHelper:
    def __init__(self, plugin, window):
        self.window = window
        self.plugin = plugin
        
        self.ui_id = None
        
        self.add_panel(window)
        
    def deactivate(self):        
        self.remove_menu_item()
        
        self.window = None
        self.plugin = None
        
    def update_ui(self):
        pass
        
    def add_panel(self, window):
        panel = self.window.get_side_panel()
        
        self.results_view = ResultsView(window)
        
        image = gtk.Image()
        image.set_from_stock(gtk.STOCK_DND_MULTIPLE, gtk.ICON_SIZE_BUTTON)
        self.ui_id = panel.add_item(self.results_view, "Find in Open Documents", image)
        
    def remove_menu_item(self):
        panel = self.window.get_side_panel()
        
        panel.remove_item(self.results_view)

class FindInDocumentsPlugin(gedit.Plugin):
    def __init__(self):
        gedit.Plugin.__init__(self)
        self.instances = {}
        
    def activate(self, window):
        self.instances[window] = PluginHelper(self, window)
        
    def deactivate(self, window):
        self.instances[window].deactivate()
        
    def update_ui(self, window):
        self.instances[window].update_ui()

########NEW FILE########
__FILENAME__ = gemini
#        Gedit gemini plugin
#        Copyright (C) 2005-2006    Gary Haran <gary.haran@gmail.com>
#
#        This program is free software; you can redistribute it and/or modify
#        it under the terms of the GNU General Public License as published by
#        the Free Software Foundation; either version 2 of the License, or
#        (at your option) any later version.
#
#        This program is distributed in the hope that it will be useful,
#        but WITHOUT ANY WARRANTY; without even the implied warranty of
#        MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.    See the
#        GNU General Public License for more details.
#
#        You should have received a copy of the GNU General Public License
#        along with this program; if not, write to the Free Software
#        Foundation, Inc., 51 Franklin St, Fifth Floor, Boston, MA
#        02110-1301  USA

import gedit
import gtk
import gobject
import re

class GeminiPlugin( gedit.Plugin):
    handler_ids = []

    def __init__(self):
        gedit.Plugin.__init__(self)

    def activate(self, window):
        view = window.get_active_view()
        self.setup_gemini (view)

    def deactivate(self, window):
        for (handler_id, view) in self.handler_ids:
            if view.handler_is_connected(handler_id):
                view.disconnect(handler_id)

    def update_ui(self, window):
        view = window.get_active_view()
        self.setup_gemini(view)


    # Starts auto completion for a given view
    def setup_gemini(self, view):
        if type(view) == gedit.View:
            if getattr(view, 'gemini_instance', False) == False:
                setattr(view, 'gemini_instance',Gemini())
                handler_id = view.connect ('key-press-event', view.gemini_instance.key_press_handler)
                self.handler_ids.append((handler_id, view))

class Gemini:
    start_keyvals = [34, 39, 96, 40, 91, 123,60]
    end_keyvals   = [34, 39, 96, 41, 93, 125,62]
    twin_start    = ['"',"'",'`','(','[','{','<']
    twin_end      = ['"',"'",'`',')',']','}','>']

    def __init__(self):
        return

    def key_press_handler(self, view, event):
        #print event.keyval
        buf = view.get_buffer()
        cursor_mark = buf.get_insert()
        cursor_iter = buf.get_iter_at_mark(cursor_mark)

        if event.keyval in self.start_keyvals or event.keyval in self.end_keyvals or event.keyval in (65288, 65293):

            back_iter = cursor_iter.copy()
            back_char = back_iter.backward_char()
            back_char = buf.get_text(back_iter, cursor_iter)

            forward_iter = cursor_iter.copy()
            forward_char = forward_iter.forward_char()
            forward_char = buf.get_text(cursor_iter, forward_iter)

            if event.keyval in self.start_keyvals:
                index = self.start_keyvals.index(event.keyval)
                start_str = self.twin_start[index]
                end_str = self.twin_end[index]
            else:
                start_str, end_str = None, None

            # Here is the meat of the logic
            if buf.get_has_selection() and event.keyval not in (65288, 65535):
                # pad the selected text with twins
                start_iter, end_iter = buf.get_selection_bounds()
                selected_text = start_iter.get_text(end_iter)
                buf.delete(start_iter, end_iter)
                buf.insert_at_cursor(start_str + selected_text + end_str)
                return True
            elif end_str != forward_char and end_str != None:
                # insert the twin that matches your typed twin
                buf.insert(cursor_iter, end_str)
                if cursor_iter.backward_char():
                    buf.place_cursor (cursor_iter)
            elif event.keyval == 65288 and back_char in self.twin_start and forward_char in self.twin_end:
                # delete twins when backspacing starting char next to ending char
                if self.twin_start.index(back_char) == self.twin_end.index(forward_char):
                        cursor_iter = buf.get_iter_at_mark(buf.get_insert())
                        forward_iter = cursor_iter.copy()
                        if forward_iter.forward_char():
                            buf.delete(back_iter, forward_iter)
                            return True
            elif event.keyval in self.end_keyvals:
                # stop people from closing an already closed pair
                index = self.end_keyvals.index(event.keyval)
                if self.twin_end[index] == forward_char :
                    cursor_iter = buf.get_iter_at_mark(buf.get_insert())
                    forward_iter = cursor_iter.copy()
                    if forward_iter.forward_char():
                        buf.place_cursor(forward_iter)
                        return True
            elif event.keyval == 65293 and forward_char == '}':
                # add proper indentation when hitting before a closing bracket
                cursor_iter = buf.get_iter_at_mark(buf.get_insert ())
                line_start_iter = cursor_iter.copy()
                view.backward_display_line_start(line_start_iter)

                line = buf.get_text(line_start_iter, cursor_iter)
                preceding_white_space_pattern = re.compile(r'^(\s*)')
                groups = preceding_white_space_pattern.search(line).groups()
                preceding_white_space = groups[0]
                plen = len(preceding_white_space)

                buf.insert_at_cursor('\n')
                buf.insert_at_cursor(preceding_white_space)
                buf.insert_at_cursor('\n')

                cursor_mark = buf.get_insert()
                cursor_iter = buf.get_iter_at_mark(cursor_mark)

                buf.insert_at_cursor(preceding_white_space)

                cursor_mark = buf.get_insert()
                cursor_iter = buf.get_iter_at_mark(cursor_mark)

                for i in range(plen + 1):
                    if cursor_iter.backward_char():
                        buf.place_cursor(cursor_iter)
                if view.get_insert_spaces_instead_of_tabs():
                    buf.insert_at_cursor(' ' * view.get_tab_width())
                else:
                    buf.insert_at_cursor('\t')
                return True
########NEW FILE########
__FILENAME__ = gotofile_window
# Gedit Go to File plugin - Easily open and switch between files
# Copyright (C) 2008  Eric Butler <eric@extremeboredom.net>
#
# Based on "Snap Open" (C) 2006 Mads Buus Jensen <online@buus.net>
# Inspired by TextMate
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

import pygtk
import gtk, gobject, pango
import sexy
import relevance
import os

class GotoFileWindow(gtk.Window):
	def __init__(self, plugin):
		gtk.Window.__init__(self)

		self._plugin = plugin

		self.set_title('Go to File')
		self.set_default_size(300, 250)
		self.set_type_hint(gtk.gdk.WINDOW_TYPE_HINT_UTILITY)
		self.set_position(gtk.WIN_POS_CENTER) # _ON_PARENT
		self.connect('show', self._windowShow)
		self.connect('delete-event', self._windowDeleteEvent)

		theme = gtk.icon_theme_get_default()
		searchPixbuf = theme.load_icon('search', 16, gtk.ICON_LOOKUP_USE_BUILTIN)

		self._entry = sexy.IconEntry()
		self._entry.add_clear_button()
		self._entry.set_icon(sexy.ICON_ENTRY_PRIMARY, gtk.image_new_from_pixbuf(searchPixbuf))
		self._entry.connect('changed', self._entryChanged)
		self._entry.connect('key-press-event', self._entryKeyPress)
		self._entry.connect('activate', self._entryActivated)

		cell = gtk.CellRendererText()
		cell.set_property('ellipsize', pango.ELLIPSIZE_START)

		self._tree = gtk.TreeView()
		self._tree.set_headers_visible(False)
		self._tree.append_column(gtk.TreeViewColumn("Name", cell, markup=0))
		self._tree.connect('button-press-event', self._treeButtonPress)
		self._tree.get_selection().connect('changed', self._treeSelectionChanged)

		# Model columns: formattedName, formattedPath, path, score
		self._store = gtk.ListStore(gobject.TYPE_STRING, gobject.TYPE_STRING, gobject.TYPE_STRING, gobject.TYPE_FLOAT)

		self._sortModel = gtk.TreeModelSort(self._store)
		self._sortModel.set_sort_column_id(3, gtk.SORT_DESCENDING)
		self._tree.set_model(self._sortModel)

		vbox = gtk.VBox()

		alignment = gtk.Alignment(0, 0, 1, 1)
		alignment.set_padding(6, 6, 6, 6)
		alignment.add(self._entry)
		vbox.pack_start(alignment, False, False, 0)

		vbox.pack_start(gtk.HSeparator(), False, False, 0)

		swindow = gtk.ScrolledWindow()
		swindow.set_policy(gtk.POLICY_NEVER, gtk.POLICY_AUTOMATIC)
		swindow.add(self._tree)
		vbox.pack_start(swindow, True, True, 0)

		vbox.pack_start(gtk.HSeparator(), False, False, 0)

		label = gtk.Label()
		#label.set_ellipsize(pango.ELLIPSIZE_START)
		self._expander = gtk.Expander(None)
		self._expander.set_label_widget(label)
		
		table = gtk.Table(2,3, False)
		table.set_property('row-spacing', 6)
		table.set_property('column-spacing', 6)
		table.set_border_width(6)
		table.attach(gtk.Label("Include:"), 0, 1, 0, 1, gtk.SHRINK, gtk.SHRINK, 0, 0)
		self._includeFilterEntry = gtk.Entry()
		self._includeFilterEntry.set_text(self._plugin.getIncludeFilter())
		self._includeFilterEntry.connect('changed', self._filtersChanged)
		table.attach(self._includeFilterEntry, 1, 2, 0, 1, gtk.FILL|gtk.EXPAND, gtk.SHRINK, 0, 0)

		table.attach(gtk.Label("Exclude:"), 0, 1, 1, 2, gtk.SHRINK, gtk.SHRINK, 0, 0)
		self._excludeFilterEntry = gtk.Entry()
		self._excludeFilterEntry.set_text(self._plugin.getExcludeFilter())
		self._excludeFilterEntry.connect('changed', self._filtersChanged)
		table.attach(self._excludeFilterEntry, 1, 2, 1, 2, gtk.FILL|gtk.EXPAND, gtk.SHRINK, 0, 0)

		self._showHiddenCheck = gtk.CheckButton("Show hidden files/folders")
		self._showHiddenCheck.connect('toggled', self._filtersChanged)
		table.attach(self._showHiddenCheck, 0, 2, 2, 3, gtk.FILL|gtk.EXPAND, gtk.SHRINK, 0, 0)

		self._expander.add(table)

		vbox.pack_start(self._expander, False, False, 0)

		self.add(vbox)
		
		try:
			import texas
			self._walker = texas.WalkerTexasRanger(self._onWalkResult, self._onWalkClear, self._onWalkFinish)
		except:
			print "async walker not available"
			import moonwalk
			self._walker = moonwalk.MoonWalker(self._onWalkResult, self._onWalkClear, self._onWalkFinish)

	def _windowShow(self, win):
		self._rootDirectory = self._plugin.getRootDirectory()
		self._entry.set_text('')
		self._entry.grab_focus()
		self._expander.set_expanded(False)
		self._search('')

	def _windowDeleteEvent(self, win, event):
		self._walker.cancel()
		self.hide()
		return True
	
	def _entryActivated(self, entry):
		self._openSelectedFile()

	def _entryChanged(self, entry):
		 self._search(entry.get_text())

	def _entryKeyPress(self, entry, event):
                if event.keyval == gtk.keysyms.Escape:
			self.hide()
                else:
			model, iter = self._tree.get_selection().get_selected()
			if iter:
				path = model.get_path(iter)
				if event.keyval == gtk.keysyms.Up:
					path = (path[0] - 1,)
					if path[0] >= 0:
						iter = model.get_iter(path)
						self._tree.get_selection().select_iter(iter)
					return True
				elif event.keyval == gtk.keysyms.Down:
					path = (path[0] + 1,)
					if path[0] < model.iter_n_children(None):
						iter = model.get_iter(path)
						self._tree.get_selection().select_iter(iter)
					return True
		return False
	
	def _filtersChanged(self, sender):
		self._plugin.setShowHidden(self._showHiddenCheck.get_active())
		self._plugin.setIncludeFilter(self._includeFilterEntry.get_text())
		self._plugin.setExcludeFilter(self._excludeFilterEntry.get_text())
		self._search(self._entry.get_text())
			
	def _treeButtonPress(self, tree, event):
		self._openSelectedFile()

	def _treeSelectionChanged(self, selection):
		model, iter = selection.get_selected()
		if iter:
			self._expander.get_label_widget().set_markup(model.get_value(iter, 1))
	
	def _onWalkResult(self, walker, dirname, dirs, files, text):
		if text == None: text = ''
		for file, score in self._plugin.filterFiles(text, files):
			name = relevance.formatCommonSubstrings(file, text)
			self._store.append((name, os.path.join(dirname, name), os.path.join(dirname, file), score))
			total = self._store.iter_n_children(None)
			if total == self._plugin.getMaxResults():
				print "Max results reached",self._plugin.getMaxResults()
				walker.cancel()
				break
	
	def _onWalkClear(self, walker, text):
		self._store.clear()
	
	def _onWalkFinish(self, walker, text):
		iter = self._sortModel.get_iter_first()
		if iter:
			self._tree.get_selection().select_iter(iter)
			path = self._sortModel.get_path(iter)
			self._tree.scroll_to_cell(path, None, True, 0, 0)
	
	def _search(self, text):
		text = text.replace(' ', '')
		ignoreDot = not self._plugin.getShowHidden()
		maxDepth  = self._plugin.getMaxDepth()
		self._walker.walk(self._rootDirectory, ignoredot = ignoreDot, maxdepth = maxDepth, user_data=text)
	
	def _openSelectedFile(self):
		model, iter = self._tree.get_selection().get_selected()
		if iter:
			path = model.get_value(iter, 2)
			self._plugin.openFile(path)
			self.hide()

########NEW FILE########
__FILENAME__ = moonwalk
# Copyright (C) 2008  Christian Hergert <chris@dronelabs.com>
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

import os

class MoonWalker(object):
	def __init__(self, onResult, onClear=None, onFinish=None):
		self._onResult  = onResult
		self._onClear   = onClear
		self._onFinish  = onFinish
		self._userData  = None

	def walk(self, query, ignoredot = False, maxdepth = -1, user_data = None):
		self._cancel = False
		self._onClear(self, user_data)
		for root, dirs, files in self._innerWalk(query, ignoredot=ignoredot, maxdepth=maxdepth, user_data=user_data):
			self._onResult(self, root, dirs, files, user_data)
			if self._cancel: break
		self._onFinish(self, user_data)

	def cancel(self):
		self._cancel = True
			
	def _innerWalk(self, path, **kwargs):
		"""
	Generator for recursively walking a directory tree with additional
	options compared to os.walk.
	 
	@path: a str containing the root directoyr or file
	@kwargs: The following args are supported:
	ignoredot=False -- ignores dot folders during recursion
	maxdepth=-1 -- sets the maximum recursions to be performed
	 
	Returns: yields tuple of (str,[str],[str]) containing the root dir
	as the first item, list of files as the second, and list of
	dirs as the third.
	"""
		if not os.path.isdir(path):
		    raise StopIteration
	 
		ignoredot = kwargs.get('ignoredot', False)
		maxdepth = kwargs.get('maxdepth', -1)
		curdepth = kwargs.get('curdepth', -1)
		kwargs['curdepth'] = curdepth + 1
	 
		if maxdepth > -1 and curdepth > maxdepth:
		    raise StopIteration
	 
		matches = lambda p: not ignoredot or not p.startswith('.')
		dirs = []
		files = []
	 
		for child in os.listdir(path):
			if matches(child):
				fullpath = os.path.join(path, child)
				if os.path.isdir(fullpath):
					dirs.append(child)
				else:
					files.append(child)
	 
		yield (path, dirs, files)
	 
		for child in dirs:
			fullpath = os.path.join(path, child)
			for item in self._innerWalk(fullpath, **kwargs):
				yield item

########NEW FILE########
__FILENAME__ = relevance
# Copyright (C) 2008  Christian Hergert <chris@dronelabs.com>
# This code was ported from gnome-do. Original Copyright:
#               2007  Chris Halse Rogers, DR Colkitt
#                     David Siegel, James Walker
#                     Jason Smith, Miguel de Icaza
#                     Rick Harding, Thomsen Anders
#                     Volker Braun, Jonathon Anderson 
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

"""
This module provides relevance matching and formatting of related strings
based on the relevance.  It is borrowed from Gnome-Do with modifications
to fit nicely into python.

>>> import relevance
>>> relevance.score('hi there dude', 'hi dude')
0.53480769230769232
>>> relevance.formatCommonSubstrings('hi there dude', 'hi dude')
'<b>hi </b>there <b>dude</b>'
"""

def formatCommonSubstrings(main, other, format = '<b>%s</b>'):
    """
    Creates a new string using @format to highlight matching substrings
    of @other in @main.
    
    Returns: a formatted str
    
    >>> formatCommonSubstrings('hi there dude', 'hi dude')
    '<b>hi </b>there <b>dude</b>'
    """
    length = 0
    result = ''
    match_pos = last_main_cut = 0
    lower_main = main.lower()
    other = other.lower()
    
    for pos in range(len(other)):
        matchedTermination = False
        for length in range(1, 1 + len(other) - pos + 1):
            tmp_match_pos  = _index(lower_main, other[pos:pos + length])
            if tmp_match_pos < 0:
                length -= 1
                matchedTermination = False
                break
            else:
                matchedTermination = True
                match_pos = tmp_match_pos
        if matchedTermination:
            length -= 1
        if 0 < length:
            # There is a match starting at match_pos with positive length
            skipped = main[last_main_cut:match_pos - last_main_cut]
            matched = main[match_pos:match_pos + length]
            if len(skipped) + len(matched) < len(main):
                remainder = formatCommonSubstrings(
                    main[match_pos + length:],
                    other[pos + length:],
                    format)
            else:
                remainder = ''
            result = '%s%s%s' % (skipped, format % matched, remainder)
            break
    
    if result == '':
        # No matches
        result = main
    
    return result

def score(s, query):
    """
    A relevancy score for the string ranging from 0 to 1
    
    @s: a str to be scored
    @query: a str query to score against
    
    Returns: a float between 0 and 1
    
    >>> score('terminal', 'trml')
    0.52875000000000005
    >>> score('terminal', 'term')
    0.96750000000000003
    """
    if len(query) == 0:
        return 1

    ls = s.lower()
    lquery = query.lower()

    lastPos = 0
    for c in lquery:
        lastPos = ls.find(c, lastPos)
        if lastPos == -1:
            return 0    
    
    score = float(0)
    
    # Find the shortest possible substring that matches the query
    # and get the ration of their lengths for a base score
    match = _findBestMatch(ls, lquery)
    if match[1] - match[0] == 0:
        return .0
    
    score = len(lquery) / float(match[1] - match[0])
    if score == 0:
        return .0
        
    # Now we weight by string length so shorter strings are better
    score *= .7 + len(lquery) / len(s) * .3
    
    # Bonus points if the characters start words
    good = 0
    bad = 1
    firstCount = 0
    for i in range(match[0], match[1] - 1):
        if s[i] == ' ':
            if ls[i + 1] in lquery:
                firstCount += 1
            else:
                bad += 1
    
    # A first character match counts extra
    if lquery[0] == ls[0]:
        firstCount += 2
        
    # The longer the acronym, the better it scores
    good += firstCount * firstCount * 4
    
    # Better yet if the match itself started there
    if match[0] == 0:
        good += 2
        
    # Super bonus if the whole match is at the beginning
    if match[1] == len(lquery) - 1:
        good += match[1] + 4
        
    # Super duper bonus if it is a perfect match
    if lquery == ls:
        good += match[1] * 2 + 4
        
    if good + bad > 0:
        score = (score + 3 * good / (good + bad)) / 4
        
    # This fix makes sure tha tperfect matches always rank higher
    # than split matches.  Perfect matches get the .9 - 1.0 range
    # everything else lower
    
    if match[1] - match[0] == len(lquery):
        score = .9 + .1 * score
    else:
        score = .9 * score
    
    return score
    
def _findBestMatch(s, query):
    """
    Finds the shortest substring of @s that contains all characters of query
    in order.
    
    @s: a str to search
    @query: a str query to search for
    
    Returns: a two-item tuple containing the start and end indicies of
             the match.  No match returns (-1,-1).
    """
    if len(query) == 0:
        return 0, 0
    
    index = -1
    bestMatch = -1, -1
    
    # Find the last instance of the last character of the query
    # since we never need to search beyond that
    lastChar = len(s) - 1
    while lastChar >= 0 and s[lastChar] != query[-1]:
        lastChar -= 1
    
    # No instance of the character?
    if lastChar == -1:
        return bestMatch
    
    # Loop through each instance of the first character in query
    index = _index(s, query[0], index + 1, lastChar - index)
    while index >= 0:
        # Is there room for a match?
        if index > (lastChar + 1 - len(query)):
            break
        
        # Look for the best match in the tail
        # We know the first char matches, so we dont check it.
        cur = index + 1
        qcur = 1
        while (qcur < len(query)) and (cur < len(s)):
            if query[qcur] == s[cur]:
                qcur += 1
            cur += 1
        
        if ((qcur == len(query)) \
        and (((cur - index) < (bestMatch[1] - bestMatch[0])) \
        or (bestMatch[0] == -1))):
            bestMatch = (index, cur)
        
        if index == (len(s) - 1):
            break
        
        index = _index(s, query[0], index + 1, lastChar - index)
        
    return bestMatch
    
def _index(s, char, index = 0, count = -1):
    """
    Looks for the index of @char in @s starting at @index for count bytes.
    
    Returns: int containing the offset of @char.  -1 if @char is not found.
    
    >>> _index('hi', 'i', 0, 2)
    1
    """
    if count >= 0:
        s = s[index:index + count]
    else:
        s = s[index:]
    
    try:
        return index + s.index(char)
    except ValueError:
        return -1

########NEW FILE########
__FILENAME__ = texas
#/usr/bin/env python
#
# Copyright (C) 2008  Christian Hergert <chris@dronelabs.com>
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License or the
# GNU Lesser General Public License as published by the 
# Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

import gio
import gobject
import glib
import os
import time

_NAME_ATTRIBUTE="standard::display-name"
_TYPE_ATTRIBUTE="standard::type"

class WalkerTexasRanger(object):
    def __init__(self, onResult, onClear=None, onFinish=None):
        self._onResult  = onResult
        self._onClear   = onClear
        self._onFinish  = onFinish
        self._enumerate = gio.Cancellable()
        self._userData  = None
    
    def _result(self, *args, **kwargs):
        if callable(self._onResult):
            userData = self._userData and [self._userData] or [None]
            apply(self._onResult, [self] + list(args) + userData, kwargs)
    
    def _clear(self, *args, **kwargs):
        if callable(self._onClear):
            userData = self._userData and [self._userData] or [None]
            apply(self._onClear, [self] + list(args) + userData, kwargs)
    
    def _finish(self, *args, **kwargs):
        if callable(self._onFinish):
            userData = self._userData and [self._userData] or [None]
            apply(self._onFinish, [self] + list(args) + userData, kwargs)
    
    def cancel(self):
        """
        Cancels a running query.
        """
        self._stamp = None
        self._enumerate.cancel()
        
    def walk(self, query, ignoredot = False, maxdepth = -1, user_data = None):
        # cancel any existing request
        self._enumerate.cancel()
        self._enumerate.reset()
        self._userData = user_data
        
        # call the clear callback
        self._clear()
        
        # consider doing query_info_async to determine if this is
        # a directory without potential blocking for slow disks.
        if not query or not os.path.isdir(query):
            False
        
        # build a unique stamp for this query
        stamp = self._stamp = str(time.time()) + query
        
        # build our state and file objects
        # state => (
        #   unique query stamp,
        #   dirs to traverse,
        #   ignore dot files/dirs
        #   max depth to traverse
        #   current traversal depth
        # )
        state = [stamp, [], ignoredot, maxdepth, 0]
        vfs = gio.vfs_get_default()
        gfile = vfs.get_file_for_path(query)
        
        # asynchronously get the list of children
        attrs = ','.join([_NAME_ATTRIBUTE, _TYPE_ATTRIBUTE])
        gfile.enumerate_children_async(attrs, self._walk, 0, 0,
                                       self._enumerate, state)
        
        return True
        
    def _walk(self, gfile, result, state):
        stamp, todo, ignoredot, maxdepth, curdepth = state
        
        # return immediately if we have been End-Of-Lifed
        if stamp != self._stamp:
            return
        
        try:
            children = gfile.enumerate_children_finish(result)
            dirname = gfile.get_path()
            dirs = []
            files = []
            
            # iterate the children found
            for child in children:
                childname = child.get_attribute_string(_NAME_ATTRIBUTE)
                childtype = child.get_attribute_uint32(_TYPE_ATTRIBUTE)
                
                # keep track of dirs and files for callback.
                # add directories to traverse if needed.
                if childtype == gio.FILE_TYPE_DIRECTORY:
                    if childname.startswith('.') and ignoredot:
                        continue
                    
                    # only add this to the todo list if its within
                    # our depth limit.
                    if maxdepth < 0 or curdepth + 1 <= maxdepth:
                        fullpath = os.path.join(gfile.get_path(), childname)
                        todo.insert(0, (fullpath, curdepth + 1))
                    
                    dirs.insert(0, childname)
                elif childtype == gio.FILE_TYPE_REGULAR:
                    if childname.startswith('.') and ignoredot:
                        continue
                    files.insert(0, childname)
            
            self._result(dirname, dirs, files)
            children.close()

            del children
        except gio.Error, ex:
            pass
        
        del gfile
        
        # we are done if no more dirs are left to traverse.
        # call finish and return.
        if not len(todo):
            self._finish()
            return
        
        # perform our next enumerate which calls this same method
        nextpath, nextdepth = todo.pop()
        state[-1] = nextdepth
        next = gio.file_parse_name(nextpath)
        attrs = ','.join([_NAME_ATTRIBUTE, _TYPE_ATTRIBUTE])
        next.enumerate_children_async(attrs, self._walk, 0, 0,
                                      self._enumerate, state)
        
if __name__ == '__main__':
    import gtk
    import pprint
    
    def p(walker, dirname, dirs, files, user):
        assert(user != None)
        print '=' * 76
        print dirname
        if dirs:
            print '  dirs:'
            print '    ' + '\n    '.join(dirs)
            print
        if files:
            print '  files:'
            print '    ' + '\n    '.join(files)
            print
    
    walker = WalkerTexasRanger(p, None, lambda *a: gtk.main_quit())
    #walker.walk('/home/chergert')
    
    def newwalk():
        walker.walk('/home/chergert', True, 2, "user data")
        return False
    
    # start a new search 50 mili later
    glib.timeout_add(50, newwalk)
    
    gtk.main()

########NEW FILE########
__FILENAME__ = config_dict
# Copyright (C) 2007 Ami Tavory (atavory@gmail.com)
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place, Suite 330, 
# Boston, MA 02111-1307, USA.



"""
Configuration dictionary. This is a dictionary that describes the different user preferences.
"""



import unittest
import gen_utils
import log_utils
import consts
import os
import opt_stream_utils
import tidy_opt_utils



def _default_config_dict():
	"""
	Returns a configuration dictionary with the default choices. Used when can't open
		a file describing these choices.
	"""
	d = {}
	
	d[consts.tidy_opts_config_category] = consts.default_tidy_opts_config
	
	d[consts.type_config_category] = consts.mime_type_config
	
	d[consts.type_ext_category] = consts.html_xhtml_and_xml_exts

	d[consts.opt_file_name_category] = consts.opt_file_name
	
	d[consts.custom_opts_names_dicts_category] = tidy_opt_utils.default_names_dicts()
	
	return d
	


def read_config_dict():
	"""
	Reads the configuration dictionary from a predefined file (defined in consts.py).
	"""
	log_utils.debug('reading config dict')

	data_dir = gen_utils.data_dir()	

	d = _default_config_dict()

	f_name = os.path.join(data_dir, consts.config_f_name)

	try:
		f = open(f_name, 'r')
		d = opt_stream_utils.opt_stream_to_dict(f)					
		f.close()
	except Exception, inst:		
		log_utils.warn(str(inst))
		log_utils.warn('couldn\'t read config dict from %s' % f_name)
		
	custom_dict = tidy_opt_utils.read_dict(consts.custom_opt_file_name, True)
	d[consts.custom_opts_names_dicts_category] = tidy_opt_utils.dict_to_names_dicts(custom_dict)
	
	log_utils.debug('read config dict')
	
	return d
	


def write_config_dict(d):
	"""
	Writes the configuration dictionary to a predefined file (defined in consts.py).
	"""
	log_utils.debug('writing config dict')
					
	custom_dict = tidy_opt_utils.names_dicts_to_dict(d[consts.custom_opts_names_dicts_category])
	tidy_opt_utils.write_dict(custom_dict, consts.custom_opt_file_name)
	
	tmp_d = {}
	
	for k in [k for k in d.keys() if k != consts.custom_opts_names_dicts_category]:
		tmp_d[k] = d[k]

	f_name = os.path.join(gen_utils.data_dir(), consts.config_f_name)

	f = open(f_name, 'w')
	opt_stream_utils.dict_to_opt_stream(tmp_d, f)
	f.close()
		
	log_utils.debug('wrote config dict')			



def effective_opts_dict(d):
	"""
	Given a configuration dictionary, returns the effective HTML-Tidy options dictionary (default, from file, or custom).
	"""
	k = d[consts.tidy_opts_config_category]
	
	if k == consts.default_tidy_opts_config:
		return tidy_opt_utils.names_dicts_to_dict( tidy_opt_utils.default_names_dicts() )
	elif  k == consts.from_file_tidy_opts_config:
		return tidy_opt_utils.read_dict( d[consts.opt_file_name_category] )
	elif  k == consts.custom_tidy_opts_config:
		return tidy_opt_utils.names_dicts_to_dict( d[consts.custom_opts_names_dicts_category] )
	else:
		assert False
		


class test(unittest.TestCase):		
	def test_default_config_dict(self):		
		d = _default_config_dict()

		self.assertEqual(d[consts.tidy_opts_config_category], consts.default_tidy_opts_config)
	
		self.assertEqual(d[consts.type_config_category], consts.mime_type_config)
		
		
	def test_read_config_dict(self):
		read_config_dict()


	def test_write_config_dict(self):
		d = read_config_dict()
		
		write_config_dict(d)



def suite():
	return unittest.TestLoader().loadTestsFromTestCase(test)
		
		

if __name__ == '__main__':
	unittest.main()

########NEW FILE########
__FILENAME__ = config_dlg
# Copyright (C) 2007 Ami Tavory (atavory@gmail.com)
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place, Suite 330, 
# Boston, MA 02111-1307, USA.



"""
Dialog used for user's preferences. See config_dict.py for the DS that stores these
	preferences.
"""



import unittest
import pygtk
pygtk.require('2.0')
import gtk
import consts
import config_dict
import log_utils
import tidy_opt_utils
import opts_dlg



class dlg(gtk.Dialog):
	def __init__(self, parent):
		title = 'HTML-Tidy Plugin Configuration'
		buttons = (gtk.STOCK_OK, gtk.RESPONSE_OK, gtk.STOCK_CANCEL, gtk.RESPONSE_CANCEL)

		super(dlg, self).__init__(title, parent, 0, buttons)
		        
		self._make_tidy_opts_vbox()

		self._make_mime_types_vbox()


	def reset(self, config_dict):
		self._config_dict = config_dict.copy()
		        
		self._init_from_config_dict()
		
		self._on_opts_changed(None)
		
		self._on_types_changed(None)
		
		
	def get_config_dict(self):
		return self._config_dict

				
	def _init_from_config_dict(self):
		v = self._config_dict[consts.tidy_opts_config_category]
		
		self._use_default_opts.set_active(v == consts.default_tidy_opts_config)
		self._from_file_opts.set_active(v == consts.from_file_tidy_opts_config)
		self._use_custom_opts.set_active(v == consts.custom_tidy_opts_config)
		
		v = self._config_dict[consts.opt_file_name_category]
		
		self._file_entry.set_text(v)

		v = self._config_dict[consts.type_config_category]

		self._mime_types.set_active(v == consts.mime_type_config)
		self._ext_types.set_active(v == consts.ext_type_config)
		self._all_types.set_active(v == consts.all_type_config)
		
		v = self._config_dict[consts.type_ext_category]
		
		self._ext_entry.set_text(v)

		        
	def _make_tidy_opts_vbox(self):
		frame = gtk.Frame('HTML Tidy Options')
		
		table = gtk.Table(3, 3, False)
		
		self._use_default_opts = gtk.RadioButton(label =  '_Default')
		self._from_file_opts = gtk.RadioButton(group = self._use_default_opts, label = 'From _File')
		self._use_custom_opts = gtk.RadioButton(group = self._use_default_opts, label = '_Custom')
		
		self._use_default_opts.connect('toggled', self._on_opts_changed)
		self._from_file_opts.connect('toggled', self._on_opts_changed)
		self._use_custom_opts.connect('toggled', self._on_opts_changed)
		
		table.attach(self._use_default_opts, 0, 1, 0, 1, xoptions = gtk.SHRINK | gtk.FILL)
		table.attach(self._from_file_opts, 0, 1, 1, 2, xoptions = gtk.SHRINK | gtk.FILL)
		table.attach(self._use_custom_opts, 0, 1, 2, 3, xoptions = gtk.SHRINK | gtk.FILL)
		
		self._view_default_opts = gtk.Button('View...')
		self._view_file_opts = gtk.Button('View...')
		self._edit_custom_opts = gtk.Button('Edit...')

		self._view_default_opts.connect('clicked', self._on_view_default_opts)
		self._view_file_opts.connect('clicked', self._on_view_file_opts)
		self._edit_custom_opts.connect('clicked', self._on_edit_custom_opts)

		table.attach(self._view_default_opts, 1, 2, 0, 1, xoptions = gtk.SHRINK | gtk.FILL)
		table.attach(self._view_file_opts, 1, 2, 1, 2, xoptions = gtk.SHRINK | gtk.FILL)
		table.attach(self._edit_custom_opts, 1, 2, 2, 3, xoptions = gtk.SHRINK | gtk.FILL)
		
		self._file_label = gtk.Label('File')
		
		self._file_entry = gtk.Entry()
		self._file_entry.connect('changed', self._on_file_entry_changed)
		self._choose_file = gtk.Button('Choose')
				
		hbox = gtk.HBox(False, 2)
		hbox.pack_start(self._file_label, False, False, 2)
		hbox.pack_start(self._file_entry, True, True, 2)
		hbox.pack_start(self._choose_file, False, False, 2)
		
		table.attach(hbox, 2, 3, 1, 2)

		self._choose_file.connect('clicked', self._on_choose_file)

		frame.add(table)
		        
		self.vbox.pack_start(frame, True, False, 2)


	def _make_mime_types_vbox(self):
		frame = gtk.Frame('File Types')
		
		table = gtk.Table(3, 3, False)		
		
		self._mime_types = gtk.RadioButton(label = 'Mime Types (HTML, _XHTML, and XML)')
		self._ext_types = gtk.RadioButton(group = self._mime_types, label =  'By _Extension')
		self._all_types = gtk.RadioButton(group = self._mime_types, label =  '_All')

		self._mime_types.connect('toggled', self._on_types_changed)
		self._ext_types.connect('toggled', self._on_types_changed)
		self._all_types.connect('toggled', self._on_types_changed)

		table.attach(self._mime_types, 0, 1, 0, 1, xoptions = gtk.SHRINK | gtk.FILL)
		table.attach(self._ext_types, 0, 1, 1, 2, xoptions = gtk.SHRINK | gtk.FILL)
		table.attach(self._all_types, 0, 1, 2, 3, xoptions = gtk.SHRINK | gtk.FILL)

		self._ext_label = gtk.Label('Extensions')

		self._ext_entry = gtk.Entry()
		self._ext_entry.connect('changed', self._on_ext_entry_changed)

		hbox = gtk.HBox(False, 2)
		hbox.pack_start(self._ext_label, False, False, 2)
		hbox.pack_start(self._ext_entry, True, True, 2)
		
		table.attach(hbox, 2, 3, 1, 2)

		frame.add(table)
		        
		self.vbox.pack_start(frame, True, False, 2)
		
		
	def _on_opts_changed(self, widget):
		use_default = self._use_default_opts.get_active()
		from_file = self._from_file_opts.get_active()
		custom_opts = self._use_custom_opts.get_active()		
		
		k = consts.tidy_opts_config_category
		
		if use_default:
			self._config_dict[k] = consts.default_tidy_opts_config
		elif from_file:
			self._config_dict[k] = consts.from_file_tidy_opts_config
		elif custom_opts:
			self._config_dict[k] = consts.custom_tidy_opts_config
		else:
			assert False
		
		self._view_default_opts.set_sensitive(use_default)
		
		self._view_file_opts.set_sensitive(from_file and self._file_entry.get_text() != '')
		self._file_label.set_sensitive(from_file)
		self._file_entry.set_sensitive(from_file)
		self._choose_file.set_sensitive(from_file)
		
		self._edit_custom_opts.set_sensitive(custom_opts)


	def _on_types_changed(self, widget):
		mime = self._mime_types.get_active()
		ext = self._ext_types.get_active()
		all = self._all_types.get_active()		
		
		k = consts.type_config_category
		
		if mime:
			self._config_dict[k] = consts.mime_type_config 
		elif ext:
			self._config_dict[k] = consts.ext_type_config
		elif all:
			self._config_dict[k] = consts.all_type_config
		else:
			assert False

		self._ext_label.set_sensitive(ext)
		self._ext_entry.set_sensitive(ext)
		
	
	def _on_file_entry_changed(self, w):
		t = self._file_entry.get_text()
		
		self._config_dict[consts.opt_file_name_category] = t

		self._view_file_opts.set_sensitive(self._file_entry.get_text() != '')


	def _on_ext_entry_changed(self, w):
		t = self._ext_entry.get_text()
		
		self._config_dict[consts.type_ext_category] = t
		

	def _on_view_default_opts(self, w):
		tabs = tidy_opt_utils.default_opts_names_dicts()
	
		d = opts_dlg.dlg(self, tabs, False)
		
		d.show_all()
		
		d.run()
		
		d.destroy()
		
		
	def _on_view_file_opts(self, w):
		f_name = self._file_entry.get_text()
		
		try:
			f_dict = tidy_opt_utils.read_dict(f_name)
		except Exception, inst:
			parent = self
			flags = gtk.DIALOG_MODAL | gtk.DIALOG_DESTROY_WITH_PARENT
			type_ = gtk.MESSAGE_WARNING
			buttons = gtk.BUTTONS_OK
			log_utils.warn('can\'t view opts file')
			log_utils.warn(inst)
			msg = 'Couldn\'t read or parse file'
			
			d = gtk.MessageDialog(parent, flags, type_, buttons, msg)
			
			d.run()
			
			d.destroy()
			
			return
		
		tabs = tidy_opt_utils.dict_to_names_dicts(f_dict)
	
		d = opts_dlg.dlg(self, tabs, False)
		
		d.show_all()
		
		d.run()
		
		d.destroy()

		
	def _on_edit_custom_opts(self, w):	
		tabs = self._config_dict[consts.custom_opts_names_dicts_category] 
		
		d = opts_dlg.dlg(self, tabs, True)
		
		d.show_all()
		
		rep = d.run()
		
		if rep == gtk.RESPONSE_OK:
			log_utils.debug('updating custom opts')
			
			self._config_dict[consts.custom_opts_names_dicts_category] = d.names_dicts()
			
			log_utils.debug('updated custom opts')
			
		d.destroy()
		

	def _on_choose_file(self, w):
		title = 'Choose...'
		flags = gtk.FILE_CHOOSER_ACTION_OPEN	
		buttons = (gtk.STOCK_CANCEL, gtk.RESPONSE_CANCEL, gtk.STOCK_OPEN, gtk.RESPONSE_OK)
		
		s = gtk.FileChooserDialog(title, None, flags, buttons)
		   			
		f_name = None
   		if s.run() == gtk.RESPONSE_OK:
   			t = s.get_filename()
   			
   			self._file_entry.set_text(t)
   		
   		s.destroy()



class test(unittest.TestCase):		
	def test_dlg_0(self):		
		o = dlg(None)
		
		o.reset(config_dict.read_config_dict())
		
		o.show_all()

		rep = o.run()
		
		if rep == gtk.RESPONSE_OK:
			config_dict.write_config_dict(o.get_config_dict())
		


def suite():
	return unittest.TestLoader().loadTestsFromTestCase(test)
		
		

if __name__ == '__main__':
	unittest.main()



########NEW FILE########
__FILENAME__ = consts
# Copyright (C) 2007 Ami Tavory (atavory@gmail.com)
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place, Suite 330, 
# Boston, MA 02111-1307, USA.



"""
Just some constants used throughout.
"""



plugin_name = 'html-tidy'
data_dir = 'data'



"""
HTML-Tidy's options categories. 
"""
opts = [
	'html_xhtml_xml_opts',
	'diagnostics_opts',	
	'char_encoding_opts',
	'pretty_print_opts',
	'misc_opts'
]



"""
Maps each option category to the name HTML Tidy gives it.
"""
opt_names_to_logical_names = {
	'html_xhtml_xml_opts' : 'HTML, XHTML, and XML',
	'diagnostics_opts' : 'Diagnostics',	
	'char_encoding_opts' : 'Character Encoding',
	'pretty_print_opts' : 'Pretty Printing',
	'misc_opts' : 'Misc.'
}



"""
Maps each option category to the file where its default options are stored.
"""
opt_names_to_f_names = {
	'html_xhtml_xml_opts' : 'html_xhtml_xml_opts.txt',
	'diagnostics_opts' : 'diagnostics_opts.txt',	
	'char_encoding_opts' : 'char_encoding_opts.txt',
	'pretty_print_opts' : 'pretty_print_opts.txt',
	'misc_opts' : 'misc_opts.txt'
}



"""
The gedit MIME types that pertain to this plugins.
"""
gedit_mime_types = [
	'text/html', 
	'application/xml', 
	'application/xhtml+xml'
]



tidy_opts_config_category = 'tidy_opts_config'
default_tidy_opts_config = 'default'
from_file_tidy_opts_config = 'from_file'
custom_tidy_opts_config = 'custom'



opt_file_name_category = 'opt_file'
opt_file_name = ''

custom_opt_file_name = 'custom_opts.txt'
custom_opts_names_dicts_category = 'custom_opts_names_dicts'


type_config_category = 'type_config'
mime_type_config = 'html_xhtml_and_xml_only'
ext_type_config = 'ext'
all_type_config = 'all'
	
	

type_ext_category = 'extensions'
html_xhtml_and_xml_exts = 'html, xhtml, xml'


	
config_f_name = 'config.txt'



sample_tidy_config_f_name = 'sample_tidy_config.txt'



tmp_input_f_name = 'tmp_input'
tmp_output_f_name = 'tmp_output'

########NEW FILE########
__FILENAME__ = ex
# Copyright (C) 2007 Ami Tavory (atavory@gmail.com)
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place, Suite 330, 
# Boston, MA 02111-1307, USA.



"""
Exception classes.
"""


import log_utils



class error(Exception):
	"""
	Exception class.
	"""
	def __init__(self, what):
		log_utils.warn('raising exception %s' % what)
		self.value = what
		
	
	def __str__(self):
		return repr(self.value)


########NEW FILE########
__FILENAME__ = file_types_filter
# Copyright (C) 2007 Ami Tavory (atavory@gmail.com)
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place, Suite 330, 
# Boston, MA 02111-1307, USA.



"""
Filters to decide whether some file type pertains to this plugin.
"""



import unittest
import log_utils
import consts
import os
import os.path



def can_tidy(config_dict, f_name, mime_type):
	"""
	Checks whether some file type pertains to this plugin (i.e., can possibly be tidied).
	
	Keyword arguments:
	
	config_dict -- The configuration dictionary describing the user preferences (see config_dict.py)
	f_name -- File's name
	mime_type -- gedit's MIME type for the content	
	"""
	log_utils.debug('checking if can tidy %s with mime type %s' % (f_name, mime_type))
	
	v = config_dict[consts.type_config_category]
	
	if v == consts.mime_type_config:
		return _can_tidy_mime_type(mime_type)		
	if v == consts.ext_type_config:
		return _can_tidy_ext(config_dict, f_name)
	if v == consts.all_type_config:
		return _can_tidy_all_type()		

	log_utils.warn('can\'t figure out type_config_category %s in config dict' % v)

	assert False

	return True			

	
	
def _can_tidy_mime_type(mime_type):
	log_utils.debug('checking if can tidy mime type %s based on mime type' % mime_type)
	
	can_tidy = mime_type in consts.gedit_mime_types
				
	log_utils.debug('can tidy = %s' % can_tidy)
	
	return can_tidy



def _can_tidy_ext(config_dict, f_name):
	log_utils.debug('checking if can tidy %s based on extension' % f_name)
	
	if f_name == None:
		log_utils.debug('there is no f_name')
		
		return False
	
	exts = [e.strip() for e in config_dict[consts.type_ext_category].split(',')]
	
	log_utils.debug('extensions are %s' % str(exts))
	
	ext = os.path.splitext(f_name)[1][1: ]
	
	log_utils.debug('the extension of %s is %s' % (f_name, ext))
	
	can_tidy = ext in exts
				
	log_utils.debug('can tidy = %s' % can_tidy)
	
	return can_tidy
	


def _can_tidy_all_type():
	log_utils.debug('checking if can tidy based on all type')
	
	can_tidy = True

	log_utils.debug('can tidy = %s' % can_tidy)	
	
	return can_tidy
		
		
		
class test(unittest.TestCase):		
	def test_mime_type(self):		
		config_dict = {
			consts.type_config_category : consts.mime_type_config, 
			consts.type_ext_category : consts.html_xhtml_and_xml_exts
			}
		f_name = 'index.html'

		mime_type = consts.gedit_mime_types[0]
		self.assertEquals(can_tidy(config_dict, f_name, mime_type), True)

		mime_type = 'shrimpy/foo'
		assert not mime_type in consts.html_xhtml_and_xml_exts
		self.assertEquals(can_tidy(config_dict, f_name, mime_type), False)


	def test_ext(self):		
		config_dict = {
			consts.type_config_category : consts.ext_type_config, 
			consts.type_ext_category : consts.html_xhtml_and_xml_exts
			}
		mime_type = consts.gedit_mime_types[0]
		
		f_name = 'index.html'
		self.assertEquals(can_tidy(config_dict, f_name, mime_type), True)

		f_name = 'index.htmls'
		self.assertEquals(can_tidy(config_dict, f_name, mime_type), False)

		f_name = 'index.html.htmls'
		self.assertEquals(can_tidy(config_dict, f_name, mime_type), False)

		f_name = None
		self.assertEquals(can_tidy(config_dict, f_name, mime_type), False)


	def test_all(self):		
		config_dict = {
			consts.type_config_category : consts.all_type_config, 
			consts.type_ext_category : consts.html_xhtml_and_xml_exts
			}
		f_name = 'index.html'
		
		mime_type = consts.gedit_mime_types[0]
		self.assertEquals(can_tidy(config_dict, f_name, mime_type), True)

		mime_type = 'shrimpy/foo'
		assert not mime_type in consts.html_xhtml_and_xml_exts
		self.assertEquals(can_tidy(config_dict, f_name, mime_type), True)


def suite():
	return unittest.TestLoader().loadTestsFromTestCase(test)
		
		

if __name__ == '__main__':
	unittest.main()
		

########NEW FILE########
__FILENAME__ = gen_utils
# Copyright (C) 2007 Ami Tavory (atavory@gmail.com)
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place, Suite 330, 
# Boston, MA 02111-1307, USA.



"""
General-purpose utilities.
"""



import consts
import unittest
import os
import log_utils
import ex



_found_data_dir = None



def is_string_type(s):
	"""
	True iff s is a string.
	"""
	return type(s) == type('')
	
	
	
def is_bool_type(s):
	"""
	True iff s is a boolean.
	"""
	return type(s) == type(True)



def disjoint_dicts_union(dicts):
	"""
	Takes a list of dictionaries that have disjoint keys.
	Returns a dictionary that is their union.
	"""
	ret = {}
	
	for d in dicts:
		for k in d.keys():
			assert not ret.has_key(k), k
			
			ret[k] = d[k]
			
	return ret



def replace_dict(d0, d1):
	"""
	Returns a dictionary whose keys are the intersection of d0 and d1, and
	whose values are from d1.
	"""
	ret = {}
	
	for (name, val) in d1.items():
		if name in d0.keys():
				ret[name] = val
		
	return ret



# Idea from snippets plugin, Copyright (C) 2005-2006  Jesse van den Kieboom.
def data_dir():
	"""
	Returns the data directory, i.e., the directory where the plugin's data files reside.
	"""
	global _found_data_dir

	if _found_data_dir != None:
		return _found_data_dir

	base_dirs = [
		os.path.join(os.environ['HOME'], '.gnome2', 'gedit', 'plugins'),
		'/usr/local/share/gedit-2',
		'/usr/share/gedit-2']
		
	for dir in base_dirs:
		_found_data_dir = os.path.join(dir, consts.plugin_name, consts.data_dir)
                        
		if os.path.isdir(_found_data_dir):
			log_utils.debug('found directory %s' % _found_data_dir)
			return _found_data_dir
               
	raise ex.error('can\'t find data directory')	



class test(unittest.TestCase):		
	def test_is_string_type(self):		
		self.assert_(is_string_type(''))
		self.assert_(is_string_type('dd'))
		self.assert_(not is_string_type(2))

		
	def test_is_bool_type(self):		
		self.assert_(is_bool_type(True))
		self.assert_(is_bool_type(False))	
		self.assert_(not is_bool_type(2))


	def test_disjoint_dicts_union(self):
		d = disjoint_dicts_union([{1 : 'a', 2 : 'b'}, {3 : 'c'}])

		self.assert_(len(d), 3)
		
		self.assertEquals(d[1], 'a')
		self.assertEquals(d[2], 'b')
		self.assertEquals(d[3], 'c')
		
		
	def test_replace_dict(self):
		d0 = {'a': 1, 'b': 2}
		
		d1 = {'b': 3, 'f': 8}
		
		d = replace_dict(d0, d1)
		
		self.assertEquals(len(d), 1)

		self.assertEquals(d['b'], 3)

	
	def test_data_dir(self):
		# Tmp Ami
		data_dir()



def suite():
	return unittest.TestLoader().loadTestsFromTestCase(test)
		


if __name__ == '__main__':
	unittest.main()

########NEW FILE########
__FILENAME__ = gtk_utils
# Copyright (C) 2007 Ami Tavory (atavory@gmail.com)
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place, Suite 330, 
# Boston, MA 02111-1307, USA.



"""
GTK utilities.
"""


import string
import unittest
import pygtk
pygtk.require('2.0')
import gtk
import log_utils
import unittest



def get_view_text(view):
	"""
	Retrieves all the text in a gtk.TextView
	
	Keyword arguments:
    view -- The gtk.TextView object.
	"""
	log_utils.debug('retrieving text')
		
	bf = view.get_buffer()

	start = bf.get_start_iter()
	end = bf.get_end_iter()

	text = bf.get_text(start, end)		
	
	log_utils.debug('retrieved text')

	return text
	
	
	
def get_num_cols_at_line(bf, line):
	"""
	Retrieves the number of columns in a given line of a gtk.TextBuffer.
	
	Keyword arguments:
    bf -- The gtk.TextBuffer object.
    line -- The line number.
	"""
	line_start_it = bf.get_iter_at_line(line)

	it = line_start_it
	count = 0

	while not it.is_end() and it.get_char() != '\n':
		count = count + 1

		it.forward_char()
		
	return count
	
	
	
def _scroll_to_it(view, bf, it):
	(start, end) = bf.get_bounds()
	
	bf.place_cursor(it)
	
	view.scroll_to_iter(end, within_margin = 0.25, use_align = False)
	view.scroll_to_iter(it, within_margin = 0.25, use_align = False)
	
	view.grab_focus()
	
	
	
# Taken from the classbrowser plugin code, Copyright (C) 2006 Frederic Back (fredericback@gmail.com)
def scroll_view_to_line_col(view, line, col):
	"""
	Places cursor at some gtk.TextView in some line and column
	
	Keyword arguments:
    view -- The gtk.TextView object.
    line -- The line number.
    col -- The column.
	"""
	log_utils.debug('scrolling to line  = %d col  = %d ' % (line, col))
	
	assert line > 0 and col > 0
	
	line = line - 1
	col = col - 1

	bf = view.get_buffer()
	
	if col < get_num_cols_at_line(bf, line):
		it = bf.get_iter_at_line_offset(line, col)
	else:
		it = bf.get_iter_at_line(line)	

	_scroll_to_it(view, bf, it)
	    
	log_utils.debug('scrolled to line  = %d col  = %d ' % (line, col))
	
	
	
def num_non_whites_till_cur(bf):	
	"""
	Retrieves the number of non whitespace characters in a gtk.TextBuffer
	up to the current insert cursor.
	
	Keyword arguments:
    bf -- gtk.TextBuffer object.
	"""
	log_utils.debug('retrieving text')
	
	it = bf.get_start_iter()
	
	insert_iter = bf.get_iter_at_mark(bf.get_insert())
	
	count = 0
	while not it.equal(insert_iter):
		if not  it.get_char() in string.whitespace:
			count = count + 1
			
		it.forward_char()
		
	log_utils.debug('retrieved text; non_whites = %d' % count)
			
	return count
		
	

def cursor_to_non_whites(view, non_white):
	"""
	Given a gtk.TextView and a number of non-whitespace characters, places the cursor
	and scrolls the view to this number of spaces from the beginning.
	
	Keyword arguments:
    view -- The gtk.TextView object.
    non_white -- The number of non whitespace chars.
	"""
	bf = view.get_buffer()
	
	(start, end) = bf.get_bounds()
	it = start
	
	log_utils.debug('scrolling non_white = %d' % non_white)
	
	count = 0
	while not it.is_end() and count < non_white:
		if not  it.get_char() in string.whitespace:
			count = count + 1
			
		it.forward_char()

	_scroll_to_it(view, bf, it)
	
	log_utils.debug('scrolled')



class test(unittest.TestCase):		
	def _non_whites_on_change(self, bf):
		num_non_whites_till_cur(bf)
		

	def test_non_whites(self):		
		main_box = gtk.VBox(False, 2)
	
		v = gtk.TextView()
		
		bf = v.get_buffer()
		
		v.connect('destroy', gtk.main_quit)	
		
		v.set_size_request(200, 200)
		
		main_box.pack_start(v, True, True, 2)
		
		main_box.pack_start(gtk.HSeparator(), False, False, 2)

		nonwhites_button = gtk.Button('_Check')		
		nonwhites_box = gtk.HBox(False, 2)
		nonwhites_label = gtk.Label('Non-Whites:')
		nonwhites_entry = gtk.Entry()
		nonwhites_box.pack_start(nonwhites_button, False, False, 2)
		nonwhites_box.pack_start(nonwhites_label, False, False, 2)
		nonwhites_box.pack_start(nonwhites_entry, True, True, 2)
		
		main_box.pack_start(nonwhites_box, False, False, 2)

		main_wnd = gtk.Window(gtk.WINDOW_TOPLEVEL)
		main_wnd.set_title('Non-Whites Test');
		main_wnd.add(main_box)
		
		def on_check_non_whites(b):	
			non_white = num_non_whites_till_cur(bf)
				
			nonwhites_entry.set_text(str(non_white))
			
			cursor_to_non_whites(v, non_white)
	
		nonwhites_button.connect('clicked', on_check_non_whites)
		
		main_wnd.show_all()
		gtk.main()



def suite():
	return unittest.TestLoader().loadTestsFromTestCase(test)
		
		

if __name__ == '__main__':
	unittest.main()

	
	
	



########NEW FILE########
__FILENAME__ = log_utils
# Copyright (C) 2007 Ami Tavory (atavory@gmail.com)
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place, Suite 330, 
# Boston, MA 02111-1307, USA.



"""
Some logging utilities.
"""



import logging



_l = logging.getLogger("gedit-html-tidy.log")
_l.setLevel(logging.WARN)

_ch = logging.StreamHandler()
######
# Set here the logging level.
######
_ch.setLevel(logging.WARN)

_fmt = logging.Formatter("%(levelname)s -  %(message)s")
_ch.setFormatter(_fmt)

_l.addHandler(_ch)



def debug(msg):
	"""
	Logs a debug level message.
	
	Keyword arguments:
    msg -- The message (text).
	"""
	_l.debug(msg)



def info(msg):
	"""
	Logs an info level message.
	
	Keyword arguments:
    msg -- The message (text).
	"""
	_l.info(msg)



def warn(msg):
	"""
	Logs a warn level message.
	
	Keyword arguments:
    msg -- The message (text).
	"""
	_l.warn(msg)



def error(msg):
	"""
	Logs an error level message.
	
	Keyword arguments:
    msg -- The message (text).
	"""
	_l.error(msg)



def critical(msg):
	"""
	Logs a critical level message.
	
	Keyword arguments:
    msg -- The message (text).
	"""
	_l.critical(msg)

########NEW FILE########
__FILENAME__ = opts_dlg
# Copyright (C) 2007 Ami Tavory (atavory@gmail.com)
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place, Suite 330, 
# Boston, MA 02111-1307, USA.



"""
A dialog for setting HTML-Tidy options.
"""


import unittest
import pygtk
pygtk.require('2.0')
import gtk
import config_dict
import opts_notebook
import os
import tidy_opt_utils
import consts
import sys, string
import gen_utils
import log_utils
				


class dlg(gtk.Dialog):
	"""
	A dialog for setting HTML-Tidy options.
	"""
	def __init__(self, parent, tabs, sensitive):
		"""
		Keyword arguments:
	    parent -- gtk.Window parent.
	    tabs -- A list of pairs of (logical category name, options dictionary within the category).
	    sensitive -- Wether the options are sensitive (i.e., can be modified).
		"""
		title = 'HTML-Tidy Options'
		flags = gtk.DIALOG_MODAL | gtk.DIALOG_DESTROY_WITH_PARENT	
		if sensitive:
			buttons = (gtk.STOCK_OK, gtk.RESPONSE_OK, gtk.STOCK_CANCEL, gtk.RESPONSE_CANCEL)
		else:
			buttons = (gtk.STOCK_OK, gtk.RESPONSE_OK)		      

		super(dlg, self).__init__(title, parent, flags, buttons)
				      
		log_utils.debug('setting up opts dialog')
		
		self._n = opts_notebook.notebook(tabs, sensitive)
		
		self.vbox.pack_start(self._n, True, True)
		
		log_utils.debug('set up opts dialog')
		
		self.show_all()
		
	
	def names_dicts(self):
		"""
		Returns a list of pairs of (logical category name, options dictionary within the category).
		"""
		return self._n.names_dicts()
		


class test(unittest.TestCase):		
	def test_defaults_dlg(self):		
		tabs = tidy_opt_utils.default_names_dicts()
	
		o = dlg(None, tabs, False)

		rep = o.run()
		

	def test_custom_dlg(self):		
		custom_dict = tidy_opt_utils.read_dict(consts.custom_opt_file_name, True)
		tabs = tidy_opt_utils.dict_to_names_dicts(custom_dict)
	
		o = dlg(None, tabs, True)

		rep = o.run()
		
		if rep == gtk.RESPONSE_OK:
			log_utils.debug('updating custom opts')
			
			names_dicts = o.names_dicts()
			custom_dict = tidy_opt_utils.names_dicts_to_dict(names_dicts)
			
			tidy_opt_utils.write_dict(custom_dict, consts.custom_opt_file_name)
			
			log_utils.debug('updated custom opts')



def suite():
	return unittest.TestLoader().loadTestsFromTestCase(test)
		
		

if __name__ == '__main__':
	unittest.main()



########NEW FILE########
__FILENAME__ = opts_notebook
# Copyright (C) 2007 Ami Tavory (atavory@gmail.com)
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place, Suite 330, 
# Boston, MA 02111-1307, USA.



"""
A notebook for setting HTML-Tidy options.
"""


import unittest
import pygtk
pygtk.require('2.0')
import gtk
import opts_tab
import os
import tidy_opt_utils
import consts
import sys, string
import gen_utils
import log_utils
		
		

class notebook(gtk.Notebook):
	"""
	A notebook for setting HTML-Tidy options.
	"""
	def __init__(self, tabs, sensitive):
		"""
		Keyword arguments:
	    tabs -- A list of pairs of (logical category name, options dictionary within the category).
	    sensitive -- Wether the options are sensitive (i.e., can be modified).
		"""
		log_utils.debug('setting up opts notebook')
		
		super(notebook, self).__init__()
		
		for (tab_name, opts_dict) in tabs:
			o = opts_tab.tab(opts_dict, sensitive)			
			self.append_page(o, gtk.Label(tab_name))
				
		log_utils.debug('set up opts notebook')
		
		
	def names_dicts(self):
		"""
		Returns a list of pairs of (logical category name, options dictionary within the category).
		"""
		children = [super(notebook, self).get_nth_page(i) for i in range(super(notebook, self).get_n_pages())]
		
		return [(super(notebook, self).get_tab_label_text(child), child.opts_dict()) for child in children]
		
		

class test(unittest.TestCase):
	def _test_notebook(self, names_dicts, sensitive):
		o = notebook(names_dicts, sensitive)
	
		o.connect("destroy", gtk.main_quit)			

		main_wnd = gtk.Window(gtk.WINDOW_TOPLEVEL)
		main_wnd.set_title('Output');
		main_wnd.add(o)

		main_wnd.show_all()
		gtk.main()


	def test_notebook_0(self):	
		self._test_notebook(tidy_opt_utils.default_names_dicts(), True)


	def test_notebook_1(self):
	 	sample_f_name = os.path.join(gen_utils.data_dir(), consts.sample_tidy_config_f_name)
	 	
	 	sample_dict = tidy_opt_utils.read_dict(sample_f_name)
	 	
		self._test_notebook(tidy_opt_utils.dict_to_names_dicts(sample_dict), False)



def suite():
	return unittest.TestLoader().loadTestsFromTestCase(test)
		
		

if __name__ == '__main__':
	unittest.main()



########NEW FILE########
__FILENAME__ = opts_tab
# Copyright (C) 2007 Ami Tavory (atavory@gmail.com)
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place, Suite 330, 
# Boston, MA 02111-1307, USA.



"""
A notebook tab for setting HTML-Tidy options.
"""


import unittest
import pygtk
pygtk.require('2.0')
import gtk
import os
import tidy_opt_utils
import consts
import sys, string
import gen_utils



class tab(gtk.Alignment):
	def __init__(self, opt_dict, sensitive):
		"""
		Keyword arguments:
		dict -- An options dictionary within some HTML-Tidy options category.
	    sensitive -- Wether the options are sensitive (i.e., can be modified).
		"""
		super(tab, self).__init__(0, 0)
		
		self._dict = opt_dict.copy()

		self.set_border_width(10)

		names = self._dict.keys()
		names.sort()
		
		i = 0
		num_vert = 16
		
		hbox = gtk.HBox(True,  4)
			
		while i <= len(names):
			vbox = gtk.VBox(True,  2)

			for name in names[i : min(len(names), i + num_vert)]:
				widget = self._make_widget(name, self._dict[name], sensitive)
				vbox.pack_start(widget, True, False)
			
			vbox.show()
			
			hbox.pack_start(vbox, False, True)

			i = i + num_vert
			
		self.add(hbox)

		self.show()
		

	def opts_dict(self):
		"""
		Returns the options dictionary belonging to (and possibly modified by) this dialog.
		"""
		return self._dict


	def _make_widget(self, name, val, sensitive):
		make_check = gen_utils.is_string_type(val)
		
		name = tidy_opt_utils.lib_to_orig_opt_rep(name)
		
		if make_check:
			val = tidy_opt_utils.lib_to_orig_opt_rep(val)
		
			return self._make_string_widget(name, val, sensitive)

		assert gen_utils.is_bool_type(val), val 

		return self._make_check_widget(name, val, sensitive)


	def _make_string_widget(self, name, val, sensitive):
		h = gtk.HBox(False, 2)
		h.set_sensitive(sensitive)

		l = gtk.Label(name)
		l.set_sensitive(sensitive)
		
		e = gtk.Entry()
		e.connect('changed', self._on_edit_changed, name)
		e.set_text(val)
		
		h.pack_start(l, False, False)
		h.pack_start(e, True, True)

		l.show()
		e.show()
		h.show()
		
		return h


	def _make_check_widget(self, name, val, sensitive):
		b = gtk.CheckButton(name)
		b.set_sensitive(sensitive)
		
		b.connect('toggled', self._on_check, name)
		assert gen_utils.is_bool_type(val), val
		b.set_active(val)		
		
		b.show()
			
		return b
		
		
	def _on_check(self, b, name):
		name = tidy_opt_utils.orig_to_lib_opt_rep(name)
		
		assert self._dict.has_key(name)
		
		self._dict[name] = b.get_active()
		

	def _on_edit_changed(self, e, name):
		name = tidy_opt_utils.orig_to_lib_opt_rep(name)
		
		assert self._dict.has_key(name)
		
		self._dict[name] = e.get_text()
		


class test(unittest.TestCase):		
	def _test_tab(self, sensitive):		
		f_name = os.path.join(gen_utils.data_dir(), consts.opt_names_to_f_names['html_xhtml_xml_opts'])
		opts_dict = tidy_opt_utils.read_dict(f_name)
		
		o = tab(opts_dict, sensitive)

		o.connect('destroy', gtk.main_quit)	

		main_wnd = gtk.Window(gtk.WINDOW_TOPLEVEL)
		main_wnd.set_title('Output');
		main_wnd.add(o)

		main_wnd.show_all()
		gtk.main()


	def test_tab_0(self):		
		self._test_tab(True)


	def test_tab_1(self):		
		self._test_tab(False)



def suite():
	return unittest.TestLoader().loadTestsFromTestCase(test)
		
		

if __name__ == '__main__':
	unittest.main()



########NEW FILE########
__FILENAME__ = opt_stream_utils
# Copyright (C) 2007 Ami Tavory (atavory@gmail.com)
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place, Suite 330, 
# Boston, MA 02111-1307, USA.



"""
Utilities for converting between a stream and an options dictionary.
"""


import unittest
import gen_utils
import log_utils
import consts
import string
import os
import StringIO
import ex



def _is_empty_line(line):
	return line.strip() == ''
	
	
	
def _is_comment_line(line):
	stripped_line = line.strip()
	
	if len(stripped_line) < 2:
		return False
		
	return stripped_line[0: 2] == '//'
	

def _is_def_line(line):
	return len(line.split(':')) == 2
	


def _content_lines(lines):
	content_lines = []
	
	for line in lines:
		if not _is_empty_line(line) and not _is_comment_line(line):
			content_lines.append(line)
			
	return content_lines



def _unsplit_lines(lines):
	if len(lines) == 0:
		return []

	unsplit_lines = [lines[0]]

	for line in lines[1: ]:
		if _is_def_line(line):
			unsplit_lines.append(line)
		else:
			unsplit_lines[-1] = unsplit_lines[-1] + ' %s' % line
			
	return unsplit_lines
		
		
		
def _parse_line(line):
	log_utils.debug('parsing %s' % line)
	
	if not _is_def_line(line):
		raise ex.error('cannot parse %s' % line)
	
	split = line.split(':')
	
	assert len(split) == 2, split
		
	(key, val) = (split[0].strip(), split[1].strip())
	
	log_utils.debug('parsed %s->%s' % (key, val))
	
	return (key, val)
	


def opt_stream_to_dict(s):
	"""
	Transforms a stream of lines of the form x: y into a dictionary where x->y.

	Keyword arguments:
    s -- The stream
	"""
	lines = s.readlines()		
		
	content_lines = _content_lines(lines)
	
	unsplit_lines = _unsplit_lines(content_lines)
	
	d = {}
					
	try:		
		for line in unsplit_lines:
			(key, val) = _parse_line(line)
			
			d[key] = val
	except:
		raise ex.error('cannot parse!')
	
	return d
	


def dict_to_opt_stream(d, s):
	"""
	Transforms a dictionary where x->y to a stream of lines of the form x: y.
	
	Keyword arguments:
	d -- The dictionary.
	s -- The stream.
	"""
	for (name, val) in d.items():
		s.write('%s: %s\n' % (name, val))



class test(unittest.TestCase):		
	def test_dict_to_opt_stream(self):
		d = {'a' : 1}
		s = StringIO.StringIO()
		
		dict_to_opt_stream(d, s)
	
		self.assertEquals(s.getvalue(), 'a: 1\n')
		
		
	def test_is_empty_line(self):
		self.assertEquals(_is_empty_line(''), True)
		self.assertEquals(_is_empty_line('\n'), True)
		self.assertEquals(_is_empty_line('\t\n'), True)
		self.assertEquals(_is_empty_line('dd\n'), False)
		
				
	def test_is_comment_line(self):
		self.assertEquals(_is_comment_line('// ddd'), True)
		self.assertEquals(_is_comment_line('// ddd\n'), True)
		self.assertEquals(_is_comment_line('\t\t// ddd'), True)
		self.assertEquals(_is_comment_line('bib// ddd'), False)
		
		
	def test_content_lines(self):
		self.assertEquals(_content_lines(['dd']), ['dd'])
		self.assertEquals(_content_lines(['dd', 'yy']), ['dd', 'yy'])
		self.assertEquals(_content_lines(['', 'dd', 'yy']), ['dd', 'yy'])
		self.assertEquals(_content_lines(['// Testing, testing', 'dd', 'yy']), ['dd', 'yy'])
		
		
	def test_unsplit_lines(self):
		self.assertEquals(_unsplit_lines(['dd: ']), ['dd: '])
		self.assertEquals(_unsplit_lines(['dd: ', 'ff']), ['dd:  ff'])
		
	
	def test_parse_line(self):
		self.assertEquals(_parse_line('dd: ff'), ('dd', 'ff'))
		self.assertEquals(_parse_line('dd: '), ('dd', ''))


	def _test_opt_stream_to_dict(self, f_name, required_num, required_dict):
		f = open(f_name, 'r')
		d = opt_stream_to_dict(f)
		f.close()
		
		self.assertEqual(len(d), required_num)
		
		for (key, val) in required_dict.items():
			self.assert_(d.has_key(key))
			self.assertEqual(d[key], required_dict[key])
	

	def test_opt_stream_to_dict_0(self):
		f_name = os.path.join(gen_utils.data_dir(), consts.opt_names_to_f_names['misc_opts'])
		
		required_dict = {
			'write-back': 'no',
			'gnu-emacs-file': ''}
		
		self._test_opt_stream_to_dict(f_name, 10, required_dict)


	def test_opt_stream_to_dict_1(self):
		f_name = os.path.join(gen_utils.data_dir(), 'sample_tidy_config.txt')
		
		required_dict = {
			'indent': 'auto',
			'indent-spaces': '2',
			'wrap': '72',
			'markup': 'yes',
			'output-xml': 'no',
			'input-xml': 'no',
			'show-warnings': 'yes',
			'numeric-entities': 'yes',
			'quote-marks': 'yes',
			'quote-nbsp': 'yes',
			'quote-ampersand': 'no',
			'break-before-br': 'no',
			'uppercase-tags': 'no',
			'uppercase-attributes': 'no',
			'char-encoding': 'latin1',
			'new-inline-tags': 'cfif, cfelse, math, mroot, \n   mrow, mi, mn, mo, msqrt, mfrac, msubsup, munderover,\n   munder, mover, mmultiscripts, msup, msub, mtext,\n   mprescripts, mtable, mtr, mtd, mth',
			'new-blocklevel-tags': 'cfoutput, cfquery',
			'new-empty-tags': 'cfelse'}
		
		self._test_opt_stream_to_dict(f_name, 18, required_dict)
	
		
	def test_dict_to_opt_stream(self):
		d = {'a' : 1}
		s = StringIO.StringIO()
		
		dict_to_opt_stream(d, s)
	
		self.assertEquals(s.getvalue(), 'a: 1\n')
		
		
		
def suite():
	return unittest.TestLoader().loadTestsFromTestCase(test)
		
		

if __name__ == '__main__':
	unittest.main()

########NEW FILE########
__FILENAME__ = output_pane
# Copyright (C) 2007 Ami Tavory (atavory@gmail.com)
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place, Suite 330, 
# Boston, MA 02111-1307, USA.



"""
Output pane for displaying Tidy's output.
"""



import unittest
import pygtk
pygtk.require('2.0')
import gtk
import pango
import sys, string
import log_utils
import tidy_utils



def _make_column(title, num, markup, allow_sort):
	renderer = gtk.CellRendererText()
		
	column = gtk.TreeViewColumn(title, renderer)
	
	if markup:
		column.add_attribute(renderer, 'markup', num)
	else:
		column.add_attribute(renderer, 'text', num)
	
	if allow_sort:
		column.set_sort_column_id(num)

	return column



def _type_to_color(type_):
	assert tidy_utils.is_valid_type(type_)

	if type_ == 'Error':
		return 'red'
	elif type_ == 'Warning':
		return 'orange'
	elif type_ == 'Config':
		return 'purple'
	else:
		return 'black'			
	


def _color_span(color, s):
	return '<span foreground = "%s">%s</span>' %(color, s)

	

def _cond_visible(n):
	if n != None:
		return n
		
	return ''



def _str_to_int(s):
	if s == '':
		return None
		
	return int(s)
	


def _make_str_int_cmp(num):
	def str_int_cmp(model, it0, it1):
		lhs = _str_to_int( model.get_value(it0, num) )
		rhs = _str_to_int( model.get_value(it1, num) )
		
		if lhs == None and rhs == None:
			return 0

		if lhs == None:
			return -1
			
		if rhs == None:
			return 1
			
		if lhs < rhs:
			return -1
		if lhs == rhs:
			return 0
		return 1

	return str_int_cmp
	
	

class _output_box(gtk.TreeView):
	def __init__(self, on_activated):
		self._list_store = gtk.ListStore(str, str, str, str)
		super(_output_box, self).__init__(self._list_store)
		
		self.append_column(_make_column('Line', 0, False, True))			
		self._list_store.set_sort_func(0, _make_str_int_cmp(0))
		
		self.append_column(_make_column('Column', 1, False, False))	
		self._list_store.set_sort_func(1, _make_str_int_cmp(1))
		
		self.append_column(_make_column('Type', 2, True, True))	
		
		self.append_column(_make_column('Message', 3, False, True))	
						
		self.set_headers_clickable(True)
		
		self._on_activated = on_activated
		
		self.connect("row-activated", self._on_row_activated)		
						
		
	def append(self, line, col, type_, what):		
		log_utils.debug('adding  %s %s %s %s to output box' %(line, col, type_, what))
				
		color = _type_to_color(type_)
		
		log_utils.debug('adding  %s %s to output box' %(_color_span(color, type_), what))
			
		self._list_store.append([_cond_visible(line), _cond_visible(col), _color_span(color, type_), what])
		
		log_utils.debug('added to output box')
		
		
	def clear(self):
		log_utils.debug('clearing output box')
	
		self._list_store.clear()
		
		log_utils.debug('cleared output box')
		
		
	def _on_row_activated(self, view, row, column):
		assert self == view
		
		model = view.get_model()
		iter = model.get_iter(row)

		line = _str_to_int( model.get_value(iter, 0) )
		col = _str_to_int( model.get_value(iter, 1) )
		type_ = model.get_value(iter, 2)
		what = model.get_value(iter, 3)
		
		self._on_activated(line, col, type_, what)



class output_pane(gtk.ScrolledWindow):
	"""
	Output pane for displaying Tidy's output.
	"""
	def __init__(self, on_activated):
		"""
		Keyword arguments:
	    on_activated -- Callback for when a row is activated.
		"""
		super(output_pane, self).__init__()
				
		self.set_policy(gtk.POLICY_NEVER, gtk.POLICY_AUTOMATIC);
		self.set_shadow_type(gtk.SHADOW_IN)
		
		self._box = _output_box(on_activated)
				
		self.add_with_viewport(self._box)
		self._box.show()
		
		self.target_uri = None
		
		
	def append(self, line, col, type_, what):
		"""
		Append another row.
		"""
		self._box.append(line, col, type_, what)
		
	
	def clear(self):
		"""
		Clear all rows.
		"""
		self._box.clear()
		
		self.target_uri = None		



class test(unittest.TestCase):		
	def _print_activated(self, line, col, type_, what):
		print line, col, type_, what
		

	def test_output_pane_0(self):		
		o = output_pane(self._print_activated)

		o.connect("destroy", gtk.main_quit)	

		main_wnd = gtk.Window(gtk.WINDOW_TOPLEVEL)
		main_wnd.set_title('Output');
		main_wnd.add(o)
		
		o.target_uri = 'foo'

		o.append(None, None, 'Info', 'Some info')		
		o.append(1, 2, 'Warning', 'Bad stuff!')
		o.append(10, 2, 'Error', 'unknown tag <boo>')
		o.append(1, 222, 'Warning', 'Also bad stuff!')
		o.append(6, 2, 'Config', 'Just config stuff')
		o.append(None, None, 'Config', 'Just config stuff with no line')		
			
		main_wnd.show_all()
		gtk.main()



def suite():
	return unittest.TestLoader().loadTestsFromTestCase(test)
		
		

if __name__ == '__main__':
	unittest.main()

########NEW FILE########
__FILENAME__ = plugin
# Copyright (C) 2007 Ami Tavory (atavory@gmail.com)
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place, Suite 330, 
# Boston, MA 02111-1307, USA.



"""
Tidy plugin class.
"""



import unittest
import pygtk
pygtk.require('2.0')
import gtk
import sys
import gedit
from gettext import gettext as _
import output_pane
import tidy_opt_utils
import log_utils
import window_helper
import gen_utils
import os
import config_dlg
import config_dict



class html_tidy_plugin(gedit.Plugin):
	"""
	Tidy plugin class.
	"""
	def __init__(self):
		super(html_tidy_plugin, self).__init__()
		self._instances = {}
		self._data_dir = gen_utils.data_dir()
		
		self.config_dict = config_dict.read_config_dict()
		
		
	def activate(self, window):
		"""
		Called to activate a specific gedit window.
		"""
		log_utils.debug('activating plugin')
	
		helper = window_helper.window_helper(self, window)
		self._instances[window] = helper

		self._activate_output_pane(window, helper)
		
		self._config_dlg = config_dlg.dlg(None)
		self._config_dlg.connect('response', self._on_config_dlg_response)

		log_utils.debug('activated plugin')


	def _activate_output_pane(self, window, helper):
		self.output_pane = output_pane.output_pane(helper.on_output_pane_row_activated)
		bottom = window.get_bottom_panel()

		image = gtk.Image()
		image.set_from_icon_name('stock_mark', gtk.ICON_SIZE_MENU)

		bottom.add_item(self.output_pane, _('HTML Tidy'), image)
		

	def deactivate(self, window):
		"""
		Called to deactivate a specific gedit window.
		"""
		log_utils.debug('deactivating plugin')	
	
		self._deactivate_output_pane(window)
	 
		self._instances[window].deactivate()
		del self._instances[window]

		log_utils.debug('deactivated plugin')


	def _deactivate_output_pane(self, window):
		window.get_bottom_panel().remove_item(self.output_pane)
		
			
	def update_ui(self, window):
		"""
		Called to update the user interface of a specific gedit window.
		"""
		self._instances[window].update_ui()
		
		
	def on_configure(self, action):
		dlg = self.create_configure_dialog()
		
		rep = dlg.run()
		
		self._on_config_dlg_response(dlg, rep)
		
		
	def create_configure_dialog(self):
		"""
		Called when configuration is needed. Just returns a configuration dialog (see config_dlg.py), but doesn't run it
			(gedit's framework does that).
		"""
		self._config_dlg.reset(self.config_dict)
	
		self._config_dlg.show_all()
		
		return self._config_dlg 
		
		
	def _on_config_dlg_response(self, dlg, rep):
		"""
		This is given to the configuration dialog as the callback when it gets a response.
		"""
		log_utils.debug('handling config dlg response')
	
		dlg.hide()
	
		if rep == gtk.RESPONSE_OK:
			log_utils.debug('handling OK config dlg response')
		
			self.config_dict = self._config_dlg.get_config_dict().copy()
			
			config_dict.write_config_dict(self.config_dict)
			
		log_utils.debug('handled config dlg response')

		self._config_dlg.reset(self.config_dict)
			

########NEW FILE########
__FILENAME__ = sub_proc
# Copyright (C) 2007 Ami Tavory (atavory@gmail.com)
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place, Suite 330, 
# Boston, MA 02111-1307, USA.



"""
Wrapper around Python's subprocess.
"""


import unittest
import subprocess
import select
import threading
import os
import log_utils
import copy



_buf_size = 1024



def _to_none_if_empty(text):
	if text == '':
		return None
		
	return text



def _make_select_list(read_txt, err_txt, out_fd, err_fd):
	select_list = []
	
	if read_txt != '':
		select_list.append(out_fd)
	if err_txt != '':
		select_list.append(err_fd)

	return select_list



class proc_dispatch:
	def __init__ (self, args, read_fn, err_fn, done_fn, except_fn):
		self._args = args
		self._read_fn = read_fn
		self._err_fn = err_fn
		self._except_fn = except_fn		
		self._done_fn = done_fn
			
		
	def run(self):
		log_utils.debug('proc_dispatch::run running popen')
	
		self._pr = subprocess.Popen(self._args, stdout = subprocess.PIPE, stderr = subprocess.PIPE, shell = True)
		
		log_utils.debug('proc_dispatch::run ran running popen; running select loop')

		self._select_loop()		
		
		log_utils.debug('proc_dispatch::run left select loop; calling done fn')
		
		self._done_fn()
		
		log_utils.debug('proc_dispatch::run left select loop; called done fn')


	def _select_loop(self):
		out_fd = self._pr.stdout.fileno()
		err_fd = self._pr.stderr.fileno()
		
		read_txt = 'dummy'
		err_txt = 'dummy'

		while True:
			select_list = _make_select_list(read_txt, err_txt, out_fd, err_fd)
			
			if select_list == []:
				return

			read_list, write_list, except_list = select.select(select_list, [], select_list)
			
			assert write_list == [], str(write_list)
			
			assert except_list == []
			
			for fd in except_list:
				log_utils.warn('proc_dispatch::select_loop calling except function')
				self._except_fn()
				
				return
	
			if out_fd in read_list:
				log_utils.debug('proc_dispatch::select_loop calling read function')
				read_txt = os.read(out_fd,  _buf_size)
				self._read_fn(_to_none_if_empty(read_txt))
				
			if	err_fd in read_list:
				log_utils.debug('proc_dispatch::select_loop calling err function')
				err_txt = os.read(err_fd, _buf_size)
				self._err_fn(_to_none_if_empty(err_txt))					
				
				
				
class _on_readline:
	def __init__(self, cb):
		self._cb = cb
		self._text = ''
		self._none_reached = False
		
		
	def on_read(self, text):
		assert self._none_reached == False
		
		if text == None:
			self._none_reached = True
		
			self._cb(_to_none_if_empty(self._text))
			
			return
	
		self._text = self._text + text		
		
		while self._text.find('\n') != -1:
			newline_pos = self._text.find('\n')
		
			self._cb(self._text[0: newline_pos])
			
			self._text = self._text[newline_pos + 1: ]
				
				

def make_on_line_cb(fn):
	return _on_readline(fn).on_read



class _on_done:
	def __init__(self, cb):
		self._cb = cb
		self._text = ''
		self._none_reached = False
		
		
	def on_read(self, text):
		assert self._none_reached == False
		
		if text == None:
			self._none_reached = True
		
			self._cb(_to_none_if_empty(self._text))
			
			return
	
		self._text = self._text + text		
		

				
def make_on_done_cb(fn):
	return _on_done(fn).on_read



class test(unittest.TestCase):		
	class _on_readline_helper:
		def __init__(self):
			self.lines = []
			
			
		def on_readline(self, line):
			if line != None:
				self.lines.append(line)
			
			
	def _test_readline(self, notifications, lines):
		
		assert len(notifications) == len(lines)
		
		h = self._on_readline_helper()		
		f = make_on_line_cb(h.on_readline)
		
		for i in range(1, len(lines)):
			tmp = copy.copy(lines[i - 1])
			tmp.extend(lines[i])
			lines[i] = tmp
			
		for i in range(len(notifications)):					
			f(notifications[i])
		
			self.assertEqual(lines[i], h.lines)
		
		
	def test_readline(self):
		self._test_readline([], [])
		self._test_readline([None], [[]])		
		self._test_readline([''], [[]])
		self._test_readline(['hello'], [[]])
		self._test_readline(['hello\n'], [['hello']])
		self._test_readline(['hello', '\n'], [[], ['hello']])
		self._test_readline(['hello', '\n', 'world\n'], [[], ['hello'], ['world']])
		self._test_readline(['hello', '\n', 'world', None], [[], ['hello'], [], ['world']])
		self._test_readline(['hello', '\n', 'world\nyeah', '\n'], [[], ['hello'], ['world'], ['yeah']])
		self._test_readline(['hello', '\n', 'world\nyeah', '\n', None], [[], ['hello'], ['world'], ['yeah'], []])
		self._test_readline(['hello', '\n', 'world\nyeah\n'], [[], ['hello'], ['world', 'yeah']])
				
		

def suite():
	return unittest.TestLoader().loadTestsFromTestCase(test)
		
		

if __name__ == '__main__':
	unittest.main()

########NEW FILE########
__FILENAME__ = tidy_opt_utils
# Copyright (C) 2007 Ami Tavory (atavory@gmail.com)
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place, Suite 330, 
# Boston, MA 02111-1307, USA.



"""
Utility facade for HTML Tidy - just the dictionary part.
"""



import os
import consts
import unittest
import gen_utils
import log_utils
import opt_stream_utils
import itertools
import string



def orig_to_lib_opt_rep(s):
	""" 
	Translates an option from the form used by Tidy utility to the form used by the Tidy python.
	"""
	if not gen_utils.is_string_type(s):
		return s
		
	if s == 'yes':
		return True
	elif s == 'no':
		return False

	return s
	


def lib_to_orig_opt_rep(s):
	""" 
	Translates an option from the form used by Tidy python to the form used by the Tidy utility.
	"""
	if gen_utils.is_bool_type(s):
		if s:
			return 'yes'

		return 'no'
	
	return s
	


def _opt_stream_to_dict(s):
	d = {}
	
	for (name, val) in opt_stream_utils.opt_stream_to_dict(s).items():
		d[orig_to_lib_opt_rep(name)] = orig_to_lib_opt_rep(val)	
		
	return d
	


def _dict_to_opt_stream(d, s):
	tmp_d = {}
	
	for (name, val) in d.items():
		tmp_d[lib_to_orig_opt_rep(name)] = lib_to_orig_opt_rep(val)
		
	opt_stream_utils.dict_to_opt_stream(tmp_d, s)



def default_names_dicts():
	"""
	Returns a pair-list of Tidy's default options.
	The first item in each pair is the name of the dictionary (e.g., "Diagnostics"); the second
	item in each pair is the dictionary itself.
	"""
	names = [consts.opt_names_to_logical_names[k] for k in consts.opts] 

	data_dir = gen_utils.data_dir()
	
	f_names = [os.path.join(data_dir, consts.opt_names_to_f_names[k]) for k in consts.opts]

	dicts = [_opt_stream_to_dict(open(f_name, 'r')) for f_name in f_names]	
	
	return [p for p in itertools.izip(names, dicts)]
	
	
	
def dict_to_names_dicts(d):
	"""
	Converts an options dictionary to a list of pairs of (logical category name, options dictionary within the category).
	"""
	return [(n_, gen_utils.replace_dict(d_, d)) for (n_, d_) in default_names_dicts()]



def names_dicts_to_dict(names_dicts):
	"""
	Converts a list of pairs of (logical category name, options dictionary within the category) to an options dictionary.
	"""
	return gen_utils.disjoint_dicts_union([d_ for (n_, d_) in names_dicts])



def read_dict(f_name, use_default_on_err = False):
	"""
	Returns an dictionary contained in a file.
	
	Keyword arguments:
	f_name -- File name containing the stuff.
	use_default_on_err (= True) -- Whether to return the default dict in case f_name could not be read/parsed.
	"""
	try:
		f = open(f_name, 'r')
		ret = _opt_stream_to_dict(f)
		f.close()
		
		return ret
	except Exception, inst:
		log_utils.warn(inst)
		
		if use_default_on_err:
			return names_dicts_to_dict(default_names_dicts())
			
		raise inst



def write_dict(d, f_name):
	"""
	Writes an options dictionary to a file
	"""
	f = open(f_name, 'w')
	_dict_to_opt_stream(d, f)	
	f.close()
		
		
		
def dict_to_str(d):
	"""
	Converts a dictionary to the format expected by HTML Tidy's command line utility. 
	"""
	return string.join(['--%s \'%s\'' % (lib_to_orig_opt_rep(k), lib_to_orig_opt_rep(v)) for (k, v) in d.items() if v != ''], ' ')



class test(unittest.TestCase):		
	def test_orig_to_lib_opt_rep(self):		
		self.assertEqual(orig_to_lib_opt_rep('dd'), 'dd')
		self.assertEqual(orig_to_lib_opt_rep(2), 2)
		self.assertEqual(orig_to_lib_opt_rep('yes'), True)
		self.assertEqual(orig_to_lib_opt_rep('no'), False)


	def test_lib_to_orig_opt_rep(self):		
		self.assertEqual(lib_to_orig_opt_rep('dd'), 'dd')
		self.assertEqual(lib_to_orig_opt_rep(2), 2)
		self.assertEqual(lib_to_orig_opt_rep(True), 'yes')
		self.assertEqual(lib_to_orig_opt_rep(False), 'no')


	def test_opt_stream_to_dict(self):
		f_name = os.path.join(gen_utils.data_dir(), consts.opt_names_to_f_names['misc_opts'])
		d = _opt_stream_to_dict(open(f_name, 'r'))
		
		self.assertEqual(len(d), 10)
		self.assertEqual(d['write-back'], False)
		self.assertEqual(gen_utils.is_bool_type(d['write-back']), True)
		self.assertEqual(d['gnu-emacs-file'], '')
		
		
	def test_default_names_dicts(self):
		names_dicts = default_names_dicts()
		
		self.assertEqual(len(names_dicts), len(consts.opts))

	
	def test_dict_to_names_dicts(self):
		names_dicts = default_names_dicts()
		d = names_dicts_to_dict(names_dicts)
		
		self.assertEquals(dict_to_names_dicts(d), names_dicts)
	 	
	 	
	def test_dict_to_str(self):	 	
		self.assertEquals(dict_to_str({'char-encoding': 'utf8'}), '--char-encoding \'utf8\'')
		self.assertEquals(dict_to_str({'char-encoding': 'utf8', 'foo': ''}), '--char-encoding \'utf8\'')
		self.assertEquals(dict_to_str({'wrap-php': True}), '--wrap-php \'yes\'')
		self.assertEquals(dict_to_str({}), '')
		 
		 	
	
def suite():
	return unittest.TestLoader().loadTestsFromTestCase(test)
		
		

if __name__ == '__main__':
	unittest.main()

########NEW FILE########
__FILENAME__ = tidy_utils
# Copyright (C) 2007 Ami Tavory (atavory@gmail.com)
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place, Suite 330, 
# Boston, MA 02111-1307, USA.



"""
Utility facade for HTML Tidy - just the tidying part.
"""



import os
import unittest
import log_utils
import gen_utils
import tidy_opt_utils
import consts
import commands
import re



class tidy_report:
	__slots__ = ['line', 'col', 'type_', 'what']


	def __init__(self, line, col, type_, what):
		self.line = line
		self.col = col
		self.type_ = type_
		self.what = what 



_line_col_report_re = re.compile('line (\d+) column (\d+) - (\w+): (.*)')
_no_line_col_report_re = re.compile('(\w+): (.*)')



def is_valid_type(type_):
	return type_ in ['Info', 'Error', 'Warning', 'Config']

		

def tidy_report_from_line(line):
	m = _line_col_report_re.match(line)
	
	if m:
		line = int(m.group(1))
		col = int(m.group(2))
		type_ = m.group(3)
		what = m.group(4)			
		
		if is_valid_type(type_):
			return tidy_report(line, col, type_, what)
			
	m = _no_line_col_report_re.match(line)
	
	if m:
		type_ = m.group(1)
		what = m.group(2)			
		
		if is_valid_type(type_):
			return tidy_report(None, None, type_, what)
	
	return None
	
	

def tidy_the_stuff(text, tidy_dict):
	tmp_input_f_name = os.path.join(gen_utils.data_dir(), consts.tmp_input_f_name)
	tmp_output_f_name = os.path.join(gen_utils.data_dir(), consts.tmp_output_f_name)

	log_utils.debug('tidying')	
	
	f = open(tmp_input_f_name, 'w')
	f.write(text)
	f.close()
	
	cmd_str = 'tidy %s %s 2> %s' % (tidy_opt_utils.dict_to_str(tidy_dict),
		tmp_input_f_name,
		tmp_output_f_name)
		
	log_utils.debug(cmd_str)
	
	(stat, out) = commands.getstatusoutput(cmd_str)
		
	log_utils.debug('tidied')
	
	log_utils.debug('generating report items')
	
	f = open(tmp_output_f_name, 'r')
	lines = f.readlines()
	f.close()

	errs = [tidy_report_from_line(line) for line in lines]
	errs = [e for e in errs if e != None]
		
	log_utils.debug('generated report items')
	
	return (out, errs)



class test(unittest.TestCase):		
	def _test_tidy_report_from_line(self, line, expected):
		e  = tidy_report_from_line(line)
		
		self.assertEqual(e.line, expected.line)
		self.assertEqual(e.col, expected.col)
		self.assertEqual(e.type_, expected.type_)
		self.assertEqual(e.what, expected.what)


	def test_tidy_report_from_line(self):
		self._test_tidy_report_from_line('line 1 column 1 - Warning: inserting missing \'title\' element', tidy_report(1, 1, 'Warning', 'inserting missing \'title\' element'))
		

	def test_tidy_the_stuff_0(self):
		opts_dict = 	tidy_opt_utils.names_dicts_to_dict(tidy_opt_utils.default_names_dicts())
		
		(d, tidy_reports) = tidy_the_stuff('', opts_dict)
		
		self.assert_(len(tidy_reports) != 0)

		
	def test_tidy_the_stuff_1(self):		
		f_name = os.path.join(gen_utils.data_dir(), 'bad_tidy_config.txt')		
		opts_dict = 	tidy_opt_utils.read_dict(f_name)
		
		(d, tidy_reports) = tidy_the_stuff('', opts_dict)
		
		self.assert_(len(tidy_reports) != 0)
		


def suite():
	return unittest.TestLoader().loadTestsFromTestCase(test)
		
		

if __name__ == '__main__':
	unittest.main()

########NEW FILE########
__FILENAME__ = window_helper
# Copyright (C) 2007 Ami Tavory (atavory@gmail.com)
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place, Suite 330, 
# Boston, MA 02111-1307, USA.



"""
The window-specific HTML plugin part.
"""



import gtk
import gedit
from gettext import gettext as _
import gtk_utils
import output_pane
import config_dict
import tidy_utils
import file_types_filter
import log_utils



class window_helper:
	"""
	The window-specific HTML plugin part.
	"""
	def __init__(self, plugin, window):
		log_utils.debug('Creating window helper')
	
		self._window = window
		self._plugin = plugin
	
		self._insert_menu()
		self._insert_configure_menu()
		
		log_utils.debug('Created window helper')
		
		
	def _flash_message(self, msg):
			self._window.get_statusbar().flash_message(112, msg)
			
		
	def deactivate(self):
		self._remove_configure_menu()
		self._remove_menu()
		
		self._window = None
		self._plugin = None
		self._action_group = None
		self._configure_action_group = None
						
	
	def _insert_menu(self):
		ui_str = """
<ui>
	<menubar name="MenuBar">
		<menu name="ToolsMenu" action="Tools">
			<placeholder name="ToolsOps_2">
				<separator/>
				<menuitem name="tidy" action="tidy"/>
				<menuitem name="tidy_check" action="tidy_check"/>
				<separator/>
			</placeholder>
			<placeholder name="ToolsOps_5">
				<menuitem name="configure_tidy" action="configure_tidy"/>
			</placeholder>
		</menu>
	</menubar>
</ui>
"""
	
		self._action_group = gtk.ActionGroup("html_tidy_plugin_actions")
		actions = [
			("tidy", None, _("_Tidy"), None, _("Tidies HTML, XHTML, and XML"),	self.on_tidy),
			("tidy_check", None, _("Tidy _Check"), None, _("Checks HTML, XHTML, and XML"),	self.on_tidy_check)]
		self._action_group.add_actions(actions)
		
		manager = self._window.get_ui_manager()
		
		manager.insert_action_group(self._action_group, -1)
		
		self._ui_id = manager.add_ui_from_string(ui_str)
	
	
	def _insert_configure_menu(self):
		ui_str = """
<ui>
	<menubar name="MenuBar">
		<menu name="ToolsMenu" action="Tools">
			<placeholder name="ToolsOps_5">
				<menuitem name="configure_tidy" action="configure_tidy"/>
			</placeholder>
		</menu>
	</menubar>
</ui>
"""
	
		self._configure_action_group = gtk.ActionGroup("html_tidy_plugin_configure_actions")
		actions = [
			("configure_tidy", None, _("Configure Tidy..."), None, _("Configures HTML, XHTML, and XML Checker"), self._plugin.on_configure)]
		self._configure_action_group.add_actions(actions)
		
		manager = self._window.get_ui_manager()
		
		manager.insert_action_group(self._configure_action_group, -1)
		
		self._configure_ui_id = manager.add_ui_from_string(ui_str)


	def _remove_menu(self):
		manager = self._window.get_ui_manager()
		
		manager.remove_ui(self._ui_id)
		
		smanager.remove_action_group(self._action_group)
		
		manager.ensure_update()
		
		
	def _remove_configure_menu(self):
		manager = self._window.get_ui_manager()
		
		manager.remove_ui(self._configure_ui_id)
		
		smanager.remove_action_group(self._configure_action_group)
		
		manager.ensure_update()


	def _can_tidy(self):
		log_utils.debug('checking if can tidy')
		
		active_doc = self._window.get_active_document()
		
		if active_doc == None:
			log_utils.debug('No doc active - returning False')
			return False
			
		f_name = active_doc.get_uri()
		mime_type = active_doc.get_mime_type()		
		
		log_utils.debug('active doc\'s name is %s' % f_name)
		log_utils.debug('active doc\'s mime type is %s' % mime_type)
		
		return file_types_filter.can_tidy(self._plugin.config_dict, f_name, mime_type)
	
	
	def update_ui(self):
		sensitive = self._can_tidy()
		
		self._action_group.set_sensitive(sensitive)
		
		self._configure_action_group.set_sensitive(True)
		
		
	def on_tidy(self, action):
		self._plugin.output_pane.clear()
		
		log_utils.debug('tidying')
		
		view = self._window.get_active_view()	
		bf = view.get_buffer()
		
		non_white = gtk_utils.num_non_whites_till_cur(bf)
		text = gtk_utils.get_view_text(view)
			
		try:	
			effective_opts_dict = config_dict.effective_opts_dict(self._plugin.config_dict)
			(s, report_items) = tidy_utils.tidy_the_stuff(text, effective_opts_dict)
		except Exception, inst:
			self._flash_message(str(inst))

			return
		
		log_utils.debug('tidy checked; found %s' % len(report_items))
		
		if s == '':
			log_utils.warn('got empty tidied text')
			
			self._flash_message('failed to tidy')
			
			return
		
		doc = self._window.get_active_document()

		doc.set_text(s)
		
		log_utils.debug('set text')
		
		gtk_utils.cursor_to_non_whites(view, non_white)

		log_utils.debug('tidied')
		
		
	def on_tidy_check(self, action):
		self._plugin.output_pane.clear()
		
		log_utils.debug('setting target uri')
		
		uri = self._window.get_active_document().get_uri()
		if uri == None:
			self._flash_message('Please first save your work to some name')
		
			return
			
		self._plugin.output_pane.target_uri = uri
			
		log_utils.debug('set target uri')

		log_utils.debug('tidy checking')
		
		view = self._window.get_active_view()	
		text = gtk_utils.get_view_text(view)
		
		try:	
			effective_opts_dict = config_dict.effective_opts_dict(self._plugin.config_dict)
			(s, report_items) = tidy_utils.tidy_the_stuff(text, effective_opts_dict)
		except Exception, inst:
			self._flash_message(str(inst))

			return

		log_utils.debug('tidy checked; found %s' % len(report_items))
		
		for item in report_items:
			self._plugin.output_pane.append(item.line, item.col, item.type_, item.what)
			
		if len(report_items) > 0:
			log_utils.debug('showing output pane')
			
			self._plugin.output_pane.show()

		log_utils.debug('tidy checked')
		

	def on_output_pane_row_activated(self, line, col, type_, what):
		target_uri = self._plugin.output_pane.target_uri
	
		log_utils.debug('row activated for  %s %s %s %s %s to output box' % (target_uri, line, col, type_, what))
		
		uri = self._window.get_active_document().get_uri()
		
		if uri != target_uri:
			self._flash_message('Please switch to %s' % target_uri)
	
			return
			
		if line == None:
			assert col == None, col
			
			return
			
		assert col != None, col
		
		view = self._window.get_active_view()

		try:
			gtk_utils.scroll_view_to_line_col(view, line, col)
		except Exception, inst:
			log_utils.warn('failed to scroll')
			
			log_utils.warn(inst)
			
			self._flash_message('Huh? Can\'t scroll to this position...')
		

########NEW FILE########
__FILENAME__ = config
import os
import pastie
import gtk
import gtk.glade

CONFIG_FILE = os.path.dirname( __file__ ) + '/config.pur'

LINKS = ['Clipboard', 'Window']
PRIVATES = ['True', 'False']
SYNTAXES = list(pastie.LANGS) 

class NoConfig(Exception): pass

class ConfigDialog():
    def __init__(self):
        self._glade = gtk.glade.XML( os.path.dirname( __file__ ) + "/Config.glade" )
        self.window = self._glade.get_widget("dialog")
        self._syntax = self._glade.get_widget("syntax")
        self._link = self._glade.get_widget("link")
        self._ok_button = self._glade.get_widget("ok_button")
        self._cancel_button = self._glade.get_widget("cancel_button")
        self._private = self._glade.get_widget("private")
        self.set_syntaxes()
        self.set_links()
        
        self._cancel_button.connect("clicked", self.hide)
    
    def set_syntaxes(self):
        for syntax in SYNTAXES:
            self._syntax.append_text(syntax)
    
    def set_links(self):
        for link in LINKS:
            self._link.append_text(link)
     
    def set_private(self, private):
        if private == "True":
            to_set = True
        else:
            to_set = False
        
        self._private.set_active(to_set)
        
    def set_syntax(self, syntax):
        self._syntax.set_active(SYNTAXES.index(syntax))
    
    def set_link(self, link):
        self._link.set_active(LINKS.index(link))
            
    def get_link(self):
        return self._link.get_model()[self._link.get_active()][0]
    
    def get_syntax(self):
        return self._syntax.get_model()[self._syntax.get_active()][0]

    def get_private(self):
        return self._private.get_active()
    
    def hide(self, widget=None, event=None):
        self.window.hide()
        self.reset()
        return True

    def connect_ok(self, func):
        self._ok_button.connect("clicked", lambda a: func())
    
        
class Configuration():

    def __init__(self):
        self._config_exists = os.access(CONFIG_FILE, os.R_OK)
        self.window = ConfigDialog()
        self.window.connect_ok(self.ok)
        try:
            self.read()
        except NoConfig:
            self.new()
        self.window_set()
        self.window.reset = self.window_set
        self.call_when_configuration_changes = None
        
    def error_dialog(self):
        dialog = gtk.MessageDialog(message_format="Error reading/writing configuration file!", 
                                   buttons = gtk.BUTTONS_OK,
                                   type = gtk.MESSAGE_ERROR )
        dialog.set_title("Error!")
        dialog.connect("response", lambda x, y: dialog.destroy())
        dialog.run()
    
    def read(self):
        if self._config_exists:
            try:
                f = open(CONFIG_FILE, 'rb')
            except:
                self.error_dialog()
            else:
                self.data = f.read()
                self.parse()
            finally:
                f.close()
        else:
            raise NoConfig
           
    def new(self):
        self.syntax = "Plain Text"
        self.link = "Window"
        self.private = "True"
        self.save()
        
    def parse(self):
        array = self.data.split("\n")
        if len(array) < 3:
            self.new()
        else:
          self.syntax = array[0]
          self.link = array[1]
          self.private = array[2]
        try:
            LINKS.index(self.link)
            PRIVATES.index(self.private)
            SYNTAXES.index(self.syntax) 
        except ValueError:
            self.new()
            
    def window_set(self):
        self.window.set_link(self.link)
        self.window.set_syntax(self.syntax)
        self.window.set_private(self.private)
        
    def ok(self):
        self.syntax = self.window.get_syntax()
        self.link = self.window.get_link()
        if self.window.get_private():
            self.private = "True"
        else:
            self.private = "False"
        self.save()
        self.window.hide()
        if self.call_when_configuration_changes:
            self.call_when_configuration_changes()
        
    def save(self):
        try:
            f = open(CONFIG_FILE, 'w')
        except:
            self.error_dialog()
        else:
            f.write("\n".join([self.syntax, self.link, self.private])+"\n")
        finally:
            f.close()
        

########NEW FILE########
__FILENAME__ = pastie
import urllib2
import urllib

PASTES = {
    'Ruby (on Rails)':'ruby_on_rails',
    'Ruby':'ruby',
    'Python':'python',
    'Plain Text':'plain_text',
    'ActionScript':'actionscript',
    'C/C++':'c++',
    'CSS':'css',
    'Diff':'diff',
    'HTML (Rails)':'html_rails',
    'HTML / XML':'html',
    'Java':'java',
    'JavaScript':'javascript',
    'Objective C/C++':'objective-c++',
    'PHP':'php',
    'SQL':'sql',
    'Shell Script':'shell-unix-generic'
}
#because dictionaries don't store order
LANGS = ('Ruby (on Rails)', 'Ruby', 'Python', 'Plain Text', 'ActionScript', 'C/C++', 'CSS', 'Diff', 'HTML (Rails)', 'HTML / XML', 'Java', 'JavaScript', 'Objective C/C++', 'PHP', 'SQL', 'Shell Script')
         
URL = 'http://pastie.org/pastes'

class Pastie:

    def __init__(self, text='', syntax='Plain Text', private=False):
        self.text = text
        self.syntax = syntax
        self.private = private

    def paste(self):
        if not PASTES.has_key(self.syntax):
            return 'Wrong syntax.'
        
        opener = urllib2.build_opener()
        params = {
                  'paste[body]':self.text,
                  'paste[parser]':PASTES[self.syntax],
                  'paste[authorization]':'burger' #pastie protecion against general spam bots
                  }
        if self.private:
            params['paste[restricted]'] = '1'
        else:
            params['paste[restricted]'] = '0'
            
        data = urllib.urlencode(params)
        request = urllib2.Request(URL, data)
        request.add_header('User-Agent', 'PastiePythonClass/1.0 +http://hiler.pl/')
        try:
            firstdatastream = opener.open(request)
        except:
            return 'We are sorry but something went wrong. Maybe pastie is down?'
        else:
            return firstdatastream.url
            

########NEW FILE########
__FILENAME__ = windows
import os
import pastie
import config
import gtk
import gtk.glade

class Window():

    def __init__(self, gladefile):
        self._glade = gtk.glade.XML( os.path.dirname( __file__ ) + "/" + gladefile )
        self._window = self._glade.get_widget("window")
        self._window.connect("delete_event", self._hide)
        
    def _hide(self, widget, event):
        widget.hide()
        return True
    
    def show(self, dummy=None):
        self._window.show()
        

class PastieWindow(Window):

    def __init__(self,):
        Window.__init__(self, "PasteWindow.glade")
       
        for lang in pastie.LANGS:
            self._glade.get_widget("syntax").append_text(lang)
        
        self._glade.get_widget("syntax").set_active(0) #sets active posision in syntax list
        self._glade.get_widget("ok_button").connect("clicked", self._ok_button)
        self._glade.get_widget("cancel_button").connect("clicked", lambda a: self._window.hide())
        
        self.inform = Inform()
        self.config = config.Configuration()
        
        self.set_from_defaults()
        self.config.call_when_configuration_changes = self.set_from_defaults
     
    def set_from_defaults(self):
        self._glade.get_widget("syntax").set_active(config.SYNTAXES.index(self.config.syntax))
        
        if self.config.private == "True":
            to_set = True
        else:
            to_set = False
        
        self._glade.get_widget("private").set_active(to_set)
        
        
    def _ok_button(self, event=None):
        text = self.get_text()
        combox = self._glade.get_widget("syntax")
        model = combox.get_model()
        active = combox.get_active()
        syntax = model[active][0]
        priv = self._glade.get_widget("private").get_active()
        self._window.hide()
        self._paste(syntax, priv, text, self.config.link)
        
    def paste_defaults(self, bla):
        if self.config.private == "True":
            private = True
        else:
            private = False
            
        self._paste(self.config.syntax, private, self.get_text(), self.config.link)
        
        
    def _paste(self, syntax, priv, text, link):
        "pastes selected text and displays window with link"
        p = pastie.Pastie(text, syntax, priv)
        paste = p.paste()
        if link == "Window":
            self.inform.entry.set_text("please wait")
            self.inform.show() #shows window
            self.inform.entry.set_text(paste)
        else:
            clipboard = gtk.clipboard_get('CLIPBOARD')
            clipboard.set_text(paste)
            clipboard.store()

class Inform(Window):

    def __init__(self):
        Window.__init__(self, "Inform.glade")
        self.entry = self._glade.get_widget("link")
        self._glade.get_widget("ok_button").connect("clicked", lambda a: self._window.hide())


########NEW FILE########
__FILENAME__ = rails_extract_partial
# -*- coding: utf8 -*-
# vim: ts=4 nowrap expandtab textwidth=80
# Rails Extract Partial Plugin
# Copyright © 2008 Alexandre da Silva / Carlos Antonio da Silva
#
# This file is part of Gmate.
#
# See LICENTE.TXT for licence information

import gedit
import gtk
import gnomevfs
import os.path

class ExtractPartialPlugin(gedit.Plugin):

    ui_str = """
    <ui>
      <menubar name="MenuBar">
        <menu name="EditMenu" action="Edit">
          <placeholder name="EditOps_6">
              <menuitem action="ExtractPartial"/>
          </placeholder>
        </menu>
      </menubar>
    </ui>
    """
    #

    bookmarks = {}

    def __init__(self):
        gedit.Plugin.__init__(self)

    def activate(self, window):
        self.__window = window
        actions = [('ExtractPartial', None, 'Extract Partial',
                    '<Alt><Control>p', 'Extract select text to a partial',
                    self.extract_partial)]
        windowdata = dict()
        window.set_data("ExtractPartialPluginWindowDataKey", windowdata)
        windowdata["action_group"] = gtk.ActionGroup("GeditExtractPartialPluginActions")
        windowdata["action_group"].add_actions(actions, window)
        manager = window.get_ui_manager()
        manager.insert_action_group(windowdata["action_group"], -1)
        windowdata["ui_id"] = manager.add_ui_from_string(self.ui_str)
        window.set_data("ExtractPartialPluginInfo", windowdata)

    def deactivate(self, window):
        windowdata = window.get_data("ExtractPartialPluginWindowDataKey")
        manager = window.get_ui_manager()
        manager.remove_ui(windowdata["ui_id"])
        manager.remove_action_group(windowdata["action_group"])

    def update_ui(self, window):
        view = window.get_active_view()

        windowdata = window.get_data("ExtractPartialPluginWindowDataKey")
        windowdata["action_group"].set_sensitive(bool(view and view.get_editable()))

    def create_file(self, window, file_uri, text):
        window.create_tab_from_uri(str(file_uri),
                                        gedit.encoding_get_current(),
                                        0, True, True)
        view = window.get_active_view()
        buf = view.get_buffer()
        doc = window.get_active_document()
        doc.begin_user_action()
        buf.insert_interactive_at_cursor(text, True)
        doc.end_user_action()

    def extract_partial(self, action, window):
        doc = window.get_active_document()
        view = window.get_active_view()
        buf = view.get_buffer()
        language = buf.get_language()
        # Only RHTML
        if language.get_id() != 'rhtml': return
        str_uri = doc.get_uri()
        if buf.get_has_selection():
            if str_uri:
                uri = gnomevfs.URI(str_uri)
                if uri:
                    path = uri.scheme + '://' + uri.dirname
                    dialog = gtk.Dialog("Enter partial Name",
                             window, gtk.DIALOG_MODAL | gtk.DIALOG_DESTROY_WITH_PARENT,
                             (gtk.STOCK_CANCEL, gtk.RESPONSE_REJECT,
                             gtk.STOCK_OK, gtk.RESPONSE_ACCEPT))
                    dialog.set_alternative_button_order([gtk.RESPONSE_ACCEPT, gtk.RESPONSE_CANCEL])
                    dialog.vbox.pack_start(gtk.Label("Don't use _ nor extension(html.erb/erb/rhtml)"))
                    entry = gtk.Entry()
                    entry.connect('key-press-event', self.__dialog_key_press, dialog)
                    dialog.vbox.pack_start(entry)
                    dialog.show_all()
                    response = dialog.run()
                    if response == gtk.RESPONSE_ACCEPT:
                        partial_name = entry.get_text()
                        doc_name = doc.get_short_name_for_display()
                        extension = self.__get_file_extension(doc_name)
                        itstart, itend = doc.get_selection_bounds()
                        partial_text = doc.get_slice(itstart, itend, True)
                        partial_render = '<%%= render :partial => "%s" %%>' % partial_name
                        doc.begin_user_action()
                        doc.delete(itstart, itend)
                        doc.insert_interactive(itstart, partial_render, True)
                        doc.end_user_action()
                        file_name = "%s/_%s%s" % (path, partial_name, extension)
                        self.create_file(window, file_name, partial_text)
                    dialog.destroy()
        else: return

    def __get_file_extension(self, doc_name):
        name, ext = os.path.splitext(doc_name)
        if ext == '.rhtml':
            return ext
        if ext == '.erb':
            name, ext = os.path.splitext(name)
            return "%s.erb" % ext
        return '.html.erb'

    def __dialog_key_press(self, widget, event, dialog):
        if event.keyval == 65293:
            dialog.response(gtk.RESPONSE_ACCEPT)

########NEW FILE########
__FILENAME__ = regexsearchinstance
import gedit
from gettext import gettext as _
import gtk
import gtk.glade
import os
import re

ui_str = """
<ui>
    <menubar name="MenuBar">
        <menu name="ToolsMenu" action="Tools">
            <placeholder name="ToolsOps_3">
                <menuitem name="Regex Search and Replace" action="RegexSearch"/>
            </placeholder>
        </menu>
    </menubar>
</ui>
"""

GLADE_FILE = os.path.join(os.path.dirname(__file__), "regexsearch.glade")

class RegexSearchInstance:

    ###
    # Object initialization
    def __init__(self, window):
        self._window = window
        self.create_menu_item()
        self.load_dialog()


    ###
    # Create menu item
    # Create our menu item in "Tools" menu.
    def create_menu_item(self):
        manager = self._window.get_ui_manager()
        self._action_group = gtk.ActionGroup("RegexSearchActions")
        regexreplace_action = gtk.Action("RegexSearch", _("Regex Search & Replace"), _("Search using regular expressions"), gtk.STOCK_FIND_AND_REPLACE)
        regexreplace_action.connect("activate", self.on_open_regex_dialog)
        self._action_group.add_action_with_accel( regexreplace_action, "<Ctrl><Alt>h" )
        manager.insert_action_group( self._action_group, -1)
        manager.add_ui_from_string(ui_str)
        manager.ensure_update()

    ###
    # Load dialog.
    #   - Load dialog from its Glade file
    #   - Connect widget signals
    #   - Put needed widgets in object variables.
    def load_dialog(self):
        glade_xml = gtk.glade.XML(GLADE_FILE)

        self._search_dialog = glade_xml.get_widget("search_dialog")
        self._search_dialog.hide()
        self._search_dialog.set_transient_for(self._window)
        self._search_dialog.set_destroy_with_parent(True)
        self._search_dialog.connect("delete_event", self._search_dialog.hide_on_delete)

        self._find_button = glade_xml.get_widget("find_button")
        self._find_button.connect("clicked", self.on_find_button_clicked)

        self._replace_button = glade_xml.get_widget("replace_button")
        self._replace_button.connect("clicked", self.on_replace_button_clicked)
        self._replace_all_button = glade_xml.get_widget("replace_all_button")
        self._replace_all_button.connect("clicked", self.on_replace_all_button_clicked)

#        close_button = glade_xml.get_widget("close_button")
#        close_button.connect("clicked", self.on_close_button_clicked)

        self._search_text_box = glade_xml.get_widget("search_text")
        self._search_text_box.connect("changed", self.on_search_text_changed)

        self._replace_text_box = glade_xml.get_widget("replace_text")
        self._replace_text_box.connect("changed", self.on_replace_text_changed)

        self._wrap_around_check = glade_xml.get_widget("wrap_around_check")
        self._use_backreferences_check = glade_xml.get_widget("use_backreferences_check")
        self._case_sensitive_check = glade_xml.get_widget("case_sensitive_check")


    ###
    # Called when the "Find" button is clicked.
    def on_find_button_clicked(self, find_button):
        self.search_document()

    ###
    # Called when the "Replace" button is clicked.
    def on_replace_button_clicked(self, replace_button):
        self.search_document(button = 'replace')

    # Called when the "Replace All" button is clicked.
    def on_replace_all_button_clicked(self, replace_button):
        document = self._window.get_active_document()
        start_iter = document.get_start_iter()
        end_iter = document.get_end_iter()
        alltext = unicode(document.get_text(start_iter, end_iter, False), "utf-8")

        regex = self.create_regex()
        if regex==None: return

        replace_string = self._replace_text_box.get_text()
        if not self._use_backreferences_check.get_active():
            replace_string = replace_string.replace('\\','\\\\') # turn \ into \\ so that backreferences are not done.

        new_string, n_replacements = regex.subn(replace_string, alltext)

        selection_bound_mark = document.get_mark("selection_bound")
        document.place_cursor(start_iter)
        document.move_mark(selection_bound_mark, end_iter)
        document.delete_selection(False, False)
        document.insert_at_cursor(new_string)

        self.show_alert_dialog(u"%d replacement(s)." % (n_replacements))

    ###
#    # Called when the "Close" button is clicked.
#    def on_close_button_clicked(self, close_button):
#        self._search_dialog.hide()

    def create_regex(self):
        try:
            # note multi-line flag, and dot does not match newline.
            if self._case_sensitive_check.get_active():
                regex = re.compile( unicode(self._search_text_box.get_text(), "utf-8"), re.MULTILINE)
            else:
                regex = re.compile( unicode(self._search_text_box.get_text(), "utf-8"), re.MULTILINE | re.IGNORECASE)
        except:
            self.show_alert_dialog(u"Invalid regular expression.")
            return None
        return regex

    ###
    # Called when the text to be searched is changed. We enable the fields once. (still want to be able to replace '')
    def on_search_text_changed(self, search_text_entry):
        search_text  = search_text_entry.get_text()
        replace_text_entry = self._replace_text_box

        if len(search_text) > 0:
            self._find_button.set_sensitive(True)
        else:
            self._find_button.set_sensitive(False)

        self.on_replace_text_changed(replace_text_entry)

    ###
    # Called when the text to be replaced is changed.
    def on_replace_text_changed(self, replace_text_entry):
        if not self.enable_replace:
            replace_text = replace_text_entry.get_text()
            search_text  =  self._search_text_box.get_text()

            if len(search_text) > 0 and len(replace_text) > 0:
                self._replace_button.set_sensitive(True)
                self._replace_all_button.set_sensitive(True)
                self.enable_replace = True

    ###
    # To update plugin's user interface
    def update_ui(self):
        pass


    ###
    # Called to open the Regex Search dialog.
    def on_open_regex_dialog (self, action = None):
        self.enable_replace = False
        self._search_dialog.show()


    ###
    # Search the document.
    #
    # The search begins from the current cursor position.
    def search_document(self, start_iter = None, wrapped_around = False, button = 'search'):
        document = self._window.get_active_document()

        if start_iter == None:
            start_iter = document.get_iter_at_mark(document.get_insert())

        end_iter = document.get_end_iter()

        regex = self.create_regex()
        if regex==None: return

        text = unicode(document.get_text(start_iter, end_iter, False), "utf-8")
        result = regex.search(text)

        if result != None:
            # There is a match

            self.handle_search_result(result, document, start_iter, wrapped_around, button)
        else:
            # No match found

            if self._wrap_around_check.get_active() and not wrapped_around and start_iter.get_offset() > 0:
                # Let's wrap around, searching the whole document
                self.search_document(document.get_start_iter(), True,button)
            else:
                # We've already wrapped around. There's no match in the whole document.
                self.show_alert_dialog(u"No match found for regular expression \"%s\"." % self._search_text_box.get_text())



    def show_alert_dialog(self, s):
        dlg = gtk.MessageDialog(self._window,
                                gtk.DIALOG_MODAL | gtk.DIALOG_DESTROY_WITH_PARENT,
                                gtk.MESSAGE_INFO,
                                gtk.BUTTONS_CLOSE,
                                _(s))
        dlg.run()
        dlg.hide()

    ###
    # Handle search's result.
    # If the result is already selected, we search for the next match.
    # Otherwise we show it.
    #
    # The parameter "result" should contain the match result of a regex search.
    def handle_search_result(self, result, document, start_iter, wrapped_around = False,button='search'):
        curr_iter = document.get_iter_at_mark(document.get_insert())

        selection_bound_mark = document.get_mark("selection_bound")
        selection_bound_iter = document.get_iter_at_mark(selection_bound_mark)

        if button=='search':
            # If our result is already selected, we will search again starting from the end of
            # of the current result.
            if start_iter.get_offset() + result.start() == curr_iter.get_offset() and \
               start_iter.get_offset() + result.end() == selection_bound_iter.get_offset():

                start_iter.forward_chars(result.end()+1) # To the first char after the current selection/match.

                # fixed bug- no wrapping when match at end of document, used to be get_offset() < document
                if start_iter.get_offset() <= document.get_end_iter().get_offset() and not wrapped_around:
                    self.search_document(start_iter,False,button)
            else:
                self.show_search_result(result, document, start_iter, button)
        else:
            # If we are replacing, and there is a selection that matches, we want to replace the selection.
            # don't advance the cursor
            self.show_search_result(result, document, start_iter, button)

    ###
    # Show search's result.
    # i.e.: Select the search result text, scroll to that position, etc.
    #
    # The parameter "result" should contain the match result of a regex search.
    def show_search_result(self, result, document, start_iter,button):

        selection_bound_mark = document.get_mark("selection_bound")

        result_start_iter = document.get_iter_at_offset(start_iter.get_offset() + result.start())
        result_end_iter = document.get_iter_at_offset(start_iter.get_offset() + result.end())

        document.place_cursor(result_start_iter)
        document.move_mark(selection_bound_mark, result_end_iter)

        if (button == 'replace'):
            replace_text = self._replace_text_box.get_text()
            self.replace_text(document,replace_text, result)

        view = self._window.get_active_view()
        view.scroll_to_cursor()

    def replace_text(self,document,replace_string, result):
        if not self._use_backreferences_check.get_active():
            replace_text = replace_string
        else:
            replace_text = result.expand(replace_string) # perform backslash expansion, like \1
        document.delete_selection(False, False)
        document.insert_at_cursor(replace_text)

        #now select the text that was replaced


########NEW FILE########
__FILENAME__ = plugin
# -*- coding: utf-8 -*-

#  Copyright (C) 2008 - Eugene Khorev
#
#  This program is free software; you can redistribute it and/or modify
#  it under the terms of the GNU General Public License as published by
#  the Free Software Foundation; either version 2 of the License, or
#  (at your option) any later version.
#
#  This program is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU General Public License for more details.
#
#  You should have received a copy of the GNU General Public License
#  along with this program; if not, write to the Free Software
#  Foundation, Inc., 59 Temple Place, Suite 330,
#  Boston, MA 02111-1307, USA.

import pygtk
pygtk.require("2.0")
import gtk
import gedit
import time
import os
import sys
import getopt
import ConfigParser
import gettext

APP_NAME = "plugin"
LOC_PATH = os.path.join(os.path.expanduser("~/.gnome2/gedit/plugins/reopen-tabs/lang"))

gettext.find(APP_NAME, LOC_PATH)
gettext.install(APP_NAME, LOC_PATH, True)

RELOADER_STATE_READY        = "ready"
RELOADER_STATE_INIT         = "init"
RELOADER_STATE_RELOADING    = "reloading"
RELOADER_STATE_DONE         = "done"
RELOADER_STATE_CLOSING      = "closing"

def log(msg):
	print '\033[32m' + msg + '\033[0m'


class ReopenTabsPlugin(gedit.Plugin):


	def __init__(self):
		gedit.Plugin.__init__(self)
		
		self._config = None
		
		self._state = RELOADER_STATE_INIT


	def activate(self, window):
		log('Event: app activated')
		self.read_config()

		window.connect("active-tab-changed", self._on_active_tab_changed)
		window.connect("active-tab-state-changed", self._on_active_tab_state_changed)
		window.connect("tabs-reordered", self._on_tabs_reordered)
		window.connect("tab-removed", self._on_tab_removed)

		# Register signal handler to ask a user to save tabs on exit
		window.connect("delete_event", self._on_destroy)
		

	def deactivate(self, window):
		log('Event: app deactivate')
		pass


	def read_config(self): # Reads configuration from a file
		# Get configuration dictionary
		self._conf_path = os.path.join(os.path.expanduser("~/.gnome2/gedit/plugins/"), "reopen-tabs/plugin.conf")

		# Check if configuration file does not exists
		if not os.path.exists(self._conf_path):
			# Create configuration file
			conf_file = file(self._conf_path, "wt")
			conf_file.close()

		self._conf_file = file(self._conf_path, "r+")
		self._config = ConfigParser.ConfigParser()
		self._config.readfp(self._conf_file)
		self._conf_file.close()

		# Setup default configuration if needed
		if not self._config.has_section("common"):
			self._config.add_section("common")

		if not self._config.has_option("common", "active_document"):
			self._config.set("common", "active_document", "")

		if not self._config.has_section("documents"):
			self._config.add_section("documents")

	def write_config(self): # Saves configuration to a file
		self._conf_file = file(self._conf_path, "r+")
		self._conf_file.truncate(0)
		self._config.write(self._conf_file)
		self._conf_file.close()
	
	def _on_tabs_reordered(self, window):
		log('Event: tabs reordered')
		if self._state == RELOADER_STATE_DONE:
			self._save_tabs()


	def _on_tab_removed(self, window, data):
		log('Event: tab removed (%s, %s)' % (self._state, window.get_state()))
		if self._state == RELOADER_STATE_DONE:
			self._save_tabs()


	def _on_active_tab_changed(self, window, tab):
		log('Event: active tab changed')
		if self._state == RELOADER_STATE_INIT:
			self._state = RELOADER_STATE_READY
			self._on_active_tab_state_changed(window)


	def _on_active_tab_state_changed(self, window):
		log('Event: active state tab changed: ' + str(window.get_active_tab().get_state()))
		log('Event: active state tab changed: ' + str(window.get_state()))
		# Check if we are not reloading and did not finished yet
		if self._state in (RELOADER_STATE_READY, RELOADER_STATE_DONE):
			# Get active tab
			tab = window.get_active_tab()
			# Check if we are ready to reload
			if tab and tab.get_state() == gedit.TAB_STATE_NORMAL:
				if self._state == RELOADER_STATE_READY:
					self._state = RELOADER_STATE_RELOADING
					self._reopen_tabs(window)
					self._state = RELOADER_STATE_DONE
				else:
					self._save_tabs()


	def update_ui(self, window):
		pass


	def _on_destroy(self, widget, event): # Handles window destory (saves tabs if required)
		log('Event: app destroy')
		self._state = RELOADER_STATE_CLOSING
	
	import time

	def _save_tabs(self): # Save opened tabs in configuration file
		log('ACTION save tabs')
		start = time.time()
		# Clear old document list
		self._config.remove_section("documents")

		# Get document URI list
		app = gedit.app_get_default()
		win = app.get_active_window()
		
		# Return list of documents which having URI's
		docs = [d.get_uri() for d in win.get_documents() if d.get_uri()]
		
		# Check if there is anything to save
		if len(docs) > 0:
			self._config.add_section("documents")
			self._config.remove_option("common", "active_document")
	
			cur_doc = win.get_active_document()
			if cur_doc: cur_uri = cur_doc.get_uri()
			else: cur_uri = None
			cur_doc = None
		
			# Create new document list
			n = 1
			for uri in docs:
				# Setup option name
				name = "document" + str(n).rjust(3).replace(" ", "0")
		
				# Check if current document is active
				if uri == cur_uri:
					cur_doc = name

				self._config.set("documents", name, uri)
				n = n + 1

			# Remeber active document
			if cur_doc:
				self._config.set("common", "active_document", cur_doc)

		self.write_config()
		end = time.time()
		
		if self._config.has_section("documents"):
			log(str(self._config.options("documents")))
		else:
			log('[]')
		log('>>> %0.3fms' % (1000 * (end - start)))
		
	def _reopen_tabs(self, window):
		log('ACTION load tabs')
		# Get list of open documents
		open_docs = [d.get_uri() for d in window.get_documents() if d.get_uri()]
		
		# Get saved active document
		active = self._config.get("common", "active_document")
	
		# Get document list
		docs = self._config.options("documents")
		log(str(docs))

		empty_tab = None
		active_tab = None

		# Check if active document is untitled (there is empty tab)
		if window.get_active_document().is_untitled():
			# Remember empty tab to close it later
			empty_tab = window.get_active_tab()

		# Check if document list is not empty
		if len(docs) > 0:
			
			# Process the rest documents
			for d in docs:
				# Get document uri
				uri = self._config.get("documents", d)
				
				# Check if document is not already opened
				if open_docs.count(uri) > 0: continue

				# Check if document exists
				if not os.path.exists(uri.replace('file://', '', 1)): continue

				# Create new tab
				log('ACTION: restore tab "%s"' % uri)
				tab = window.create_tab_from_uri(uri, None, 0, True, False)
		
				# Check if document was active (and there is NOT file in command line)
				if d == active and empty_tab != None:
					active_tab = tab

		# Connect handler that switches saved active document tab
		log('empty tab: ' + str(empty_tab))
		log('activ tab: ' + str(active_tab))
		if active_tab:
			def on_doc_loaded(doc, arg):
				window.set_active_tab(active_tab)
				if empty_tab and empty_tab.get_state() == gedit.TAB_STATE_NORMAL:
					log('ACTION: closing empty tab')
					_state = self._state
					self._state = RELOADER_STATE_CLOSING
					window.close_tab(empty_tab)
					self._state = _state

			active_tab.get_document().connect("loaded", on_doc_loaded)
		if empty_tab == None:
			self._save_tabs()


########NEW FILE########
__FILENAME__ = rubyonrailsloader
# Copyright (C) 2009 Alexandre da Silva
#
# This program is free software; you can redistribute it and/or modify it under
# the terms of the GNU General Public License as published by the Free Software
# Foundation; either version 2 of the License, or (at your option) any later
# version.
#
# This program is distributed in the hope that it will be useful, but WITHOUT
# ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS
# FOR A PARTICULAR PURPOSE. See the GNU General Public License for more
# details.
#
# You should have received a copy of the GNU General Public License along with
# this program; if not, write to the Free Software Foundation, Inc., 51
# Franklin Street, Fifth Floor, Boston, MA 02110-1301, USA.

"""Automatically detects if file resides in a ruby on rails application and set the properly language."""

import gedit, os

class RubyOnRailsLoader(gedit.Plugin):

    """Automatically strip all trailing whitespace before saving."""

    def activate(self, window):
        """Activate plugin."""
        self.window = window
        handler_id = window.connect("tab-added", self.on_window_tab_added)
        window.set_data(self.__class__.__name__, handler_id)
        for doc in window.get_documents():
            self.connect_document(doc)

    def connect_document(self, doc):
        """Connect to document's 'load' signal."""

        handler_id = doc.connect("loaded", self.on_document_load)
        doc.set_data(self.__class__.__name__, handler_id)


    def deactivate(self, window):
        """Deactivate plugin."""

        name = self.__class__.__name__
        handler_id = window.get_data(name)
        window.disconnect(handler_id)
        window.set_data(name, None)


    def on_window_tab_added(self, window, tab):
        """Connect the document in tab."""
        doc = tab.get_document()
        self.connect_document(doc)


    def on_document_load(self, doc, *args):
        language = doc.get_language()
        if language:
            lang = language.get_id()
            if lang == 'ruby':
                uri = doc.get_uri_for_display()
                if self.get_in_rails(uri):
                    lang = gedit.get_language_manager().get_language('rubyonrails')
                    doc.set_language(lang)


    def get_in_rails(self, uri):
        rails_root = self.get_data('RailsLoaderRoot')
        if rails_root:
            return rails_root
        base_dir = os.path.dirname(uri)
        depth = 10
        while depth > 0:
            depth -= 1
            app_dir = os.path.join(base_dir, 'app')
            config_dir = os.path.join(base_dir, 'config')
            environment_file = os.path.join(base_dir, 'config', 'environment.rb')
            if os.path.isdir(app_dir) and os.path.isdir(config_dir) and os.path.isfile(environment_file):
                rails_root = base_dir
                break
            else:
                base_dir = os.path.abspath(os.path.join(base_dir, '..'))
        if rails_root:
            self.set_data('RailsLoaderRoot', rails_root)
            return True
        return False


    def set_data(self, name, value):
        self.window.get_active_tab().get_view().set_data(name, value)


    def get_data(self, name):
        return self.window.get_active_tab().get_view().get_data(name)


########NEW FILE########
__FILENAME__ = smart_indent
# -*- coding: utf-8 -*-
# vim: ts=4 nowrap textwidth=80
# Smart Indent Plugin
# Copyright © 2008 Alexandre da Silva / Carlos Antonio da Silva
#
# This file is part of Gmate.
#
# See LICENTE.TXT for licence information

import gedit
import gtk
import gobject
import re

class SmartIndentPlugin(gedit.Plugin):
    handler_ids = []

    def __init__(self):
        gedit.Plugin.__init__(self)

    def activate(self, window):
        view = window.get_active_view()
        self.setup_smart_indent(view, 'none')

    def deactivate(self, window):
        for (handler_id, view) in self.handler_ids:
            view.disconnect(handler_id)

    def update_ui(self, window):
        view = window.get_active_view()
        lang = 'none'
        if view:
            buf = view.get_buffer()
            language = buf.get_language()
            if language:
                lang = language.get_id()
        self.setup_smart_indent(view, lang)

    def setup_smart_indent(self, view, lang):
        if type(view) == gedit.View:
            if getattr(view, 'smart_indent_instance', False) == False:
                setattr(view, 'smart_indent_instance', SmartIndent())
                handler_id = view.connect('key-press-event', view.smart_indent_instance.key_press_handler)
                self.handler_ids.append((handler_id, view))
            view.smart_indent_instance.set_language(lang)

class SmartIndent:

    def __init__(self):
        self.__not_available = True
        self.__line_unindented = -1
        self.__line_no = -1
        return

    def set_language(self, lang):
        self.__not_available = False
        if lang == 'none':
            self.__not_available = True
        elif lang == 'ruby':
            self.re_indent_next = re.compile(r'[^#]*\s+\bdo\b(\s*|(\s+\|.+\|\s*))|\s*(\bif\b\s+.*|\belsif\b.*|\belse\b.*|\bdo\b(\s*|\s+.*)|\bcase\b\s+.*|\bwhen\b\s+.*|\bwhile\b\s+.*|\bfor\b\s+.*|\buntil\b\s+.*|\bloop\b\s+.*|\bdef\b\s+.*|\bclass\b\s+.*|\bmodule\b\s+.*|\bbegin\b.*|\bunless\b\s+.*|\brescue\b.*|\bensure\b.*)+')
            self.re_unindent_curr = re.compile(r'^\s*(else.*|end\s*|elsif.*|rescue.*|when.*|ensure.*)$')
            self.unindent_keystrokes = 'edfn'
        elif lang == 'python':
            self.re_indent_next = re.compile(r'\s*[^#]{3,}:\s*(#.*)?')
            self.re_unindent_curr = re.compile(r'^\s*(else|elif\s.*|except(\s.*)?|finally)\s*:')
            self.unindent_keystrokes = ':'
        elif lang == 'javascript':
            self.re_indent_next = re.compile(r'\s*(((if|while)\s*\(|else\s*|else\s+if\s*\(|for\s*\(.*\))[^{;]*)')
            self.re_unindent_curr = re.compile(r'^.*(default:\s*|case.*:.*)$')
            self.unindent_keystrokes = ':'
        elif lang == 'php':
            self.re_indent_next = re.compile(r'\s*(((if|while|else\s*(if)?|for(each)?|switch|declare)\s*\(.*\)[^{:;]*)|(do\s*[^\({:;]*))')
            self.re_unindent_curr = re.compile(r'^.*(default:\s*|case.*:.*)$')
            self.unindent_keystrokes = ':'
        else:
            self.__not_available = True

    def __update_line_no(self, buf):
        cursor_iter = buf.get_iter_at_mark(buf.get_insert())
        self.__line_no = cursor_iter.get_line()
        if self.__line_no != self.__line_unindented:
            self.__line_unindented = -1

    def __get_current_line(self, view, buf):
        cursor_iter = buf.get_iter_at_mark(buf.get_insert())
        line_start_iter = cursor_iter.copy()
        view.backward_display_line_start(line_start_iter)
        return buf.get_text(line_start_iter, cursor_iter)

    def key_press_handler(self, view, event):
        buf = view.get_buffer()
        if self.__not_available or buf.get_has_selection(): return
        # Get tabs/indent configuration
        if view.get_insert_spaces_instead_of_tabs():
          indent_width = ' ' * view.get_tab_width()
        else:
          indent_width = '\t'
        keyval = event.keyval
        self.__update_line_no(buf)
        if keyval == 65293:
            # Check next line indentation for current line
            line = self.__get_current_line(view, buf)
            if self.re_indent_next and self.re_indent_next.match(line):
                old_indent = line[:len(line) - len(line.lstrip())]
                indent = '\n'+ old_indent + indent_width
                buf.insert_interactive_at_cursor(indent, True)
                return True
        elif keyval == 65288:
            line = self.__get_current_line(view, buf)
            if line.strip() == '' and line != '':
                length = len(indent_width)
                nb_to_delete = len(line) % length or length
                cursor_position = buf.get_property('cursor-position')
                iter_cursor = buf.get_iter_at_offset(cursor_position)
                iter_before = buf.get_iter_at_offset(cursor_position - nb_to_delete)
                buf.delete_interactive(iter_before, iter_cursor, True)
                return True
        elif keyval in [ord(k) for k in self.unindent_keystrokes]:
            line = self.__get_current_line(view, buf)
            if self.__line_unindented != self.__line_no:
                line_eval = line+chr(event.keyval)
                if self.re_unindent_curr and self.re_unindent_curr.match(line_eval):
                    cursor_iter = buf.get_iter_at_mark(buf.get_insert())
                    line_start_iter = cursor_iter.copy()
                    view.backward_display_line_start(line_start_iter)
                    iter_end_del = buf.get_iter_at_offset(line_start_iter.get_offset() + len(indent_width))
                    text = buf.get_text(line_start_iter, iter_end_del)
                    if text.strip() == '':
                        buf.delete_interactive(line_start_iter, iter_end_del, True)
                        self.__line_unindented = self.__line_no
                        return False
        return False

########NEW FILE########
__FILENAME__ = text_tools
# -*- coding: utf8 -*-
#  Text Tools Plugin
#
#  Copyright (C) 2008 Shaddy Zeineddine <simpsomboy at gmail dot com>
#
#  This program is free software: you can redistribute it and/or modify
#  it under the terms of the GNU General Public License as published by
#  the Free Software Foundation, either version 3 of the License, or
#  (at your option) any later version.
#
#  This program is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU General Public License for more details.
#
#  You should have received a copy of the GNU General Public License
#  along with this program.  If not, see <http://www.gnu.org/licenses/>.
#  Some code was got from LineTools Plugin

import gedit
import gtk

class TextToolsPlugin(gedit.Plugin):

  line_tools_str = """
    <ui>
      <menubar name="MenuBar">
        <menu name="EditMenu" action="Edit">
          <placeholder name="EditOps_6">
            <menu action="TextTools">
              <menuitem action="ClearLine"/>
              <menuitem action="DuplicateLine"/>
              <menuitem action="RaiseLine"/>
              <menuitem action="LowerLine"/>
              <menuitem action="SelectEnclosed"/>
            </menu>
          </placeholder>
        </menu>
      </menubar>
    </ui>
    """
    #


  bookmarks = {}

  def __init__(self):
    gedit.Plugin.__init__(self)

  def activate(self, window):
    actions = [
      ('TextTools',           None, 'Text Tools'),
      ('ClearLine',           None, 'Clear Line',         '<Shift><Control>c',        'Remove all the characters on the current line',                             self.clear_line),
      ('DuplicateLine',       None, 'Duplicate Line',     '<Shift><Control>d', 'Create a duplicate of the current line below the current line',             self.duplicate_line),
      ('RaiseLine',           None, 'Move Line Up',       '<Alt>Up',           'Transpose the current line with the line above it',                         self.raise_line),
      ('LowerLine',           None, 'Move Line Down',     '<Alt>Down',         'Transpose the current line with the line below it',                         self.lower_line),
      ('SelectEnclosed',      None, 'Select Enclosed Text','<Alt><Control>9','Select the content between enclose chars, quotes or tags',            self.select_enclosed)
    ]
    windowdata = dict()
    window.set_data("TextToolsPluginWindowDataKey", windowdata)
    windowdata["action_group"] = gtk.ActionGroup("GeditTextToolsPluginActions")
    windowdata["action_group"].add_actions(actions, window)
    manager = window.get_ui_manager()
    manager.insert_action_group(windowdata["action_group"], -1)
    windowdata["ui_id"] = manager.add_ui_from_string(self.line_tools_str)
    window.set_data("TextToolsPluginInfo", windowdata)

  def deactivate(self, window):
    windowdata = window.get_data("TextToolsPluginWindowDataKey")
    manager = window.get_ui_manager()
    manager.remove_ui(windowdata["ui_id"])
    manager.remove_action_group(windowdata["action_group"])

  def update_ui(self, window):
    view = window.get_active_view()
    windowdata = window.get_data("TextToolsPluginWindowDataKey")
    windowdata["action_group"].set_sensitive(bool(view and view.get_editable()))

  def clear_line(self, action, window):
    # Got from LineTools plugin
    doc = window.get_active_document()
    doc.begin_user_action()
    itstart = doc.get_iter_at_mark(doc.get_insert())
    itstart.set_line_offset(0);
    is_end = itstart.ends_line()
    if is_end == False:
      itend = doc.get_iter_at_mark(doc.get_insert())
      is_end = itend.ends_line()
      if is_end == False:
        itend.forward_to_line_end()
      doc.delete(itstart, itend)
    doc.end_user_action()

  def duplicate_line(self, action, window):
    # Got from LineTools plugin
    doc = window.get_active_document()
    doc.begin_user_action()
    itstart = doc.get_iter_at_mark(doc.get_insert())
    itstart.set_line_offset(0);
    itend = doc.get_iter_at_mark(doc.get_insert())
    itend.forward_line()
    line = doc.get_slice(itstart, itend, True)
    doc.insert(itend, line)
    doc.end_user_action()

  def raise_line(self, action, window):
    # Got from LineTools plugin
    doc = window.get_active_document()
    doc.begin_user_action()
    itstart = doc.get_iter_at_mark(doc.get_insert())
    itstart.set_line_offset(0);
    itstart.backward_line()
    itend = doc.get_iter_at_mark(doc.get_insert())
    itend.set_line_offset(0);
    line = doc.get_slice(itstart, itend, True)
    doc.delete(itstart, itend)
    itend.forward_line()
    doc.insert(itend, line)
    doc.end_user_action()

  def lower_line(self, action, window):
    # Got from LineTools plugin
    doc = window.get_active_document()
    doc.begin_user_action()
    itstart = doc.get_iter_at_mark(doc.get_insert())
    itstart.forward_line()
    itend = doc.get_iter_at_mark(doc.get_insert())
    itend.forward_line()
    itend.forward_line()
    line = doc.get_slice(itstart, itend, True)
    doc.delete(itstart, itend)
    itstart.backward_line()
    doc.insert(itstart, line)
    doc.end_user_action()

  def select_enclosed(self, action, window):
    """Select Characters enclosed by quotes or braces"""
    starting_chars = ['"', "'", "[", "(", "{", "<", ">"]
    ending_chars   = ['"', "'", "]", ")", "}", ">", "<"]
    beg_iter = None
    end_iter = None
    char_match = None
    doc = window.get_active_document()
    itr = doc.get_iter_at_mark(doc.get_insert())
    while itr.backward_char():
        if itr.get_char() in starting_chars:
            char_match = ending_chars[starting_chars.index(itr.get_char())]
            itr.forward_char()
            beg_iter = itr.copy()
            break
    while itr.forward_char():
        if itr.get_char() == char_match:
            end_iter = itr.copy()
            break
    doc.select_range(beg_iter, end_iter)

########NEW FILE########
__FILENAME__ = todo
# -*- coding: utf-8 -*-
#
# Copyright (C) 2007 - Alexandre da Silva
#
# Inspired in Nando Vieira's todo.rb source code
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2, or (at your option)
# any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place - Suite 330, Boston, MA 02111-1307, USA.
#

import os, sys, operator
from stat import *
from string import Template
import re

# Get the command line argument to define the root folder on search for
root = sys.argv[1]

home_folder = os.path.expanduser('~')

temp_file_name = '/tmp/_todo_%s_todo.html' %  os.environ['USER']

# TODO: Look first for a config file present in /etc to facility configuration
# Config FileName
config_file = os.path.join(os.path.dirname(__file__), "todo.conf")

# Configs read regular expression
cfg_rx = re.compile(r"(ALLOWED_EXTENSIONS|SKIPED_DIRS|KNOWN_MARKS|SKIPED_FILES|SHOW_EMPTY_MARKS|REQUIRE_COLON|MARK_COLORS)=+(.*?)$")

# Get Configuration Info
cfg_file = open(config_file,'r')
cfg_data = cfg_file.read().split('\n')

configs = {'ALLOWED_EXTENSIONS':'','SKIPED_DIRS':'','KNOWN_MARKS':'',\
        'SKIPED_FILES':'','SHOW_EMPTY_MARKS':'0','REQUIRE_COLON':'1','MARK_COLORS': ''}

for cfg_line in cfg_data:
    cfg_match = cfg_rx.search(cfg_line)
    if cfg_match:
        configs[cfg_match.group(1)] = cfg_match.group(2)

def make_regex(config_str):
    return "|".join([re.escape(k) for k in configs[config_str].split(';')])

allowed_extensions_regex = make_regex('ALLOWED_EXTENSIONS')
skiped_dirs_regex = make_regex('SKIPED_DIRS')
known_marks_regex = make_regex('KNOWN_MARKS')
skiped_files_regex = make_regex('SKIPED_FILES')

known_marks_list = known_marks_regex.split('|')

# Initial Setup
allowed_types = re.compile(r'.*\.\b(%s)\b$' % allowed_extensions_regex)
skiped_dirs = re.compile(r'.*(%s)$' % skiped_dirs_regex)
# Enable os disable colons
if configs["REQUIRE_COLON"] == "1":
    known_marks = re.compile(r'\b(%s)\b\s?: +(.*?)$' % known_marks_regex)
else:
    known_marks = re.compile(r'\b(%s)\b\s?:? +(.*?)$' % known_marks_regex)
skiped_files = re.compile(r"("+skiped_files_regex+")$")

total_marks = 0

# Helper Functions
def file_link(file, line=0):
    return "gedit:///%s?line=%d" % (file,line-1)

# Escape possible tags from comments as HTML
def escape(str_):
    lt = re.compile(r'<')
    gt = re.compile(r'>')
    return lt.sub("&lt;",gt.sub("&gt;",str_))

# Todo Header image pattern
def todo_header():
    return "file:///%s/.gnome2/gedit/plugins/todo/todo_header.png" % home_folder

# Todo Gear Image
def todo_gears():
    return  "file:///%s/.gnome2/gedit/plugins/todo/todo_gears.png"  % home_folder

# Initialize the values list
values = []

# Markup Label Counter
labels = {}

for label in known_marks_list:
    labels[label]=0


# walk over directory tree
def walktree(top, callback):
    '''recursively descend the directory tree rooted at top,
       calling the callback function for each regular file'''

    for f in os.listdir(top):
        pathname = os.path.join(top, f)
        try:
            mode = os.stat(pathname)[ST_MODE]
            if S_ISDIR(mode):
                # It's a directory, recurse into it
                if not skiped_dirs.match(pathname):
                    walktree(pathname, callback)
            elif S_ISREG(mode):
                # It's a file, call the callback function
                if not skiped_files.match(pathname):
                    callback(pathname)
            else:
                # Unknown file type, pass
                pass
        except OSError:
            continue

# Test File Callback function
def test_file(file):
    """ Parse the file passed as argument searching for TODO Tags"""
    if allowed_types.match(file):
        try:
            file_search = open(file, 'r')
        except IOError:
            sys.exit(2)

        data = file_search.read()
        data = data.split('\n')

        # Line Number
        ln = 0
        for line in data:
            ln = ln + 1
            a_match = known_marks.search(line)
            if (a_match):
                pt, fl = os.path.split(file)
                labels[a_match.group(1)] += 1
                result = [file,fl,ln,a_match.group(1),a_match.group(2)]
                values.append(result)

# Search Directories for files matching
walktree(root, test_file)

html = '<div id="todo_list">\n'

# Make the Menu
menu = '<ul id="navigation">\n'
for label in labels:
    total_marks += labels[label]
    if configs['SHOW_EMPTY_MARKS'] == '1' or labels[label]:
        menu += '   <li class="%s"><a href="#%s-title">%s</a>: %d</li>\n' % (label.lower(), label.lower(), label, labels[label])

menu += '<li class="total">Total: %d</li></ul>\n' % total_marks

table_pattern = Template(\
"""\
    <h2 id=\"${label}-title\">${labelU}</h2>
    <table id="${label}">
    <thead>
        <tr>
            <th class="file">File</th>
            <th class="comment">Comment</th>
        </tr>
    </thead>
    <tbody>
"""
)

tables = {}

for label_ in known_marks_list:
    tables[label_]= table_pattern.substitute(dict(label=label_.lower(),labelU=label_.upper()))

table_row_pattern = '        <tr class="%s"><td><a href="%s"  title="%s">%s</a> <span>(%s)</span></td><td>%s</td>\n'

def format_row(value_):
    return table_row_pattern % (css, file_link(value_[0], value_[2]), value_[0], value_[1], value_[2], value_[4])

for ix, value in enumerate(sorted(values,key=operator.itemgetter(3))):
    css = 'odd'
    if ix % 2 == 0:
        css = 'even'
    for table_value in tables:
        if value[3] == table_value:
            tables[table_value] += format_row(value)

for table_value in tables:
    tables[table_value] += '    </tbody></table>\n'

html += menu

for label in labels:
    if labels[label]:
        html += tables[label]

html += '   <a href="#todo_list" id="toplink">↑ top</a>\n  </div>'

todo_links_css_pattern = \
"""
    #${label}-title {
        color: ${color};
    }
    li.${label} {
        background: ${color};
    }
"""

todo_links_css = ''

color_rx = re.compile(r'^(.*)(#[0-9a-fA-F]{6})$')

todo_links_template = Template(todo_links_css_pattern)

for markcolor in configs['MARK_COLORS'].split(';'):
    c_match = color_rx.search(markcolor)
    if c_match:
        mark,mcolor = c_match.group(1), c_match.group(2)
        todo_links_css += todo_links_template.substitute(label=mark.lower(),color=mcolor)
# TODO: load this template pattern from a file.
html_pattern = \
"""
<!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.1//EN"
    "http://www.w3.org/TR/xhtml11/DTD/xhtml11.dtd">
<html>
<head>
    <meta http-equiv="Content-type" content="text/html; charset=utf-8" />
    <title>TODO-List</title>
    <style type="text/css">
    * {
        color: #333;
    }

    body {
        font-size: 12px;
        font-family: "bitstream vera sans mono", "sans-serif";
        padding: 0;
        margin: 0;
        width: 700px;
        height: 500px;
    }

    th {
        text-align: left;
    }

    td {
        vertical-align: top;
    }

    ${labelcss}

    th, a {
        color: #0D2681;
    }

    .odd td {
        background: #f0f0f0;
    }

    table {
        border-collapse: collapse;
        width: 650px;
    }

    td,th {
        padding: 3px;
    }

    th {
        border-bottom: 1px solid #999;
    }

    th.file {
        width: 30%;
    }

    #toplink {
        position: fixed;
        bottom: 10px;
        right: 40px;
    }

    h1 {
        color: #fff;
        padding: 20px 5px 18px 5px;
        margin: 0;
    }

    h2 {
        font-size: 16px;
        margin: 0 0 10px;
        padding-top: 30px;
    }

    #page {
        overflow: auto;
        height: 406px;
        padding: 0 15px 20px 15px;
        position: relative;
    }

    #root {
        position: absolute;
        top: 28px;
        right: 23px;
        color: #fff;
    }

    #navigation {
        margin: 0;
        padding: 0;
        border-left: 1px solid #000;
    }

    #navigation * {
        color: #fff;
    }

    li.total {
        background: #000000;
        font-weight: bold
    }

    #navigation li {
        float: left;
        list-style: none;
        text-align: center;
        padding: 7px 10px;
        margin: 0;
        border: 1px solid #000;
        border-left: none;
        font-weight: bold
    }

    #navigation:after {
        content: ".";
        display: block;
        height: 0;
        clear: both;
        visibility: hidden;
    }

    #todo_list {
        padding-top: 30px;
    }

    #container {
        position: relative;
        background: url(${todo_header}) repeat-x;
    }

    #gears {
        float : right;
        margin : 0 0 0 0;
    }

    </style>
</head>
<body>
<div id="container">
<img src="${todo_gears}" id="gears" />
<h1>TODO List</h1>
<p id="root">${root}</p>
<div id="page">
    ${html}
</div>
</div>
</body>
</html>
"""

markup = Template(html_pattern)

markup_out = markup.substitute(todo_header=todo_header(), \
    todo_gears=todo_gears(),root=escape(root), html=html, \
    labelcss=todo_links_css)

# Remove the file if exists
try:
    os.unlink(temp_file_name)
except OSError:
    pass

# Create the temp new file
tmp_file = open(temp_file_name,'w')
tmp_file.write(markup_out)
tmp_file.close()

########NEW FILE########
__FILENAME__ = trailsave
# Copyright (C) 2006-2008 Osmo Salomaa
#
# This program is free software; you can redistribute it and/or modify it under
# the terms of the GNU General Public License as published by the Free Software
# Foundation; either version 2 of the License, or (at your option) any later
# version.
#
# This program is distributed in the hope that it will be useful, but WITHOUT
# ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS
# FOR A PARTICULAR PURPOSE. See the GNU General Public License for more
# details.
#
# You should have received a copy of the GNU General Public License along with
# this program; if not, write to the Free Software Foundation, Inc., 51
# Franklin Street, Fifth Floor, Boston, MA 02110-1301, USA.

"""Automatically strip all trailing whitespace before saving."""

import gedit
import os
import gconf

from smart_indent import get_crop_spaces_eol, get_insert_newline_eof, get_remove_blanklines_eof


class SaveWithoutTrailingSpacePlugin(gedit.Plugin):

    """Automatically strip all trailing whitespace before saving."""

    def activate(self, window):
        """Activate plugin."""

        handler_id = window.connect("tab-added", self.on_window_tab_added)
        window.set_data(self.__class__.__name__, handler_id)
        for doc in window.get_documents():
            self.connect_document(doc)


    def connect_document(self, doc):
        """Connect to document's 'saving' signal."""

        handler_id = doc.connect("saving", self.on_document_saving)
        doc.set_data(self.__class__.__name__, handler_id)


    def deactivate(self, window):
        """Deactivate plugin."""

        name = self.__class__.__name__
        handler_id = window.get_data(name)
        window.disconnect(handler_id)
        window.set_data(name, None)
        for doc in window.get_documents():
            handler_id = doc.get_data(name)
            doc.disconnect(handler_id)
            doc.set_data(name, None)


    def on_document_saving(self, doc, *args):
        """Strip trailing spaces in document."""

        cursor = doc.get_iter_at_mark(doc.get_insert())
        line = cursor.get_line()
        offset = cursor.get_line_offset()
        doc.begin_user_action()
        self.strip_trailing_spaces_on_lines(doc)
        self.strip_trailing_blank_lines(doc)
        doc.end_user_action()
        try:
            doc.go_to_line(line)
        except:
            pass
        return


    def on_window_tab_added(self, window, tab):
        """Connect the document in tab."""

        name = self.__class__.__name__
        doc = tab.get_document()
        handler_id = doc.get_data(name)
        if handler_id is None:
            self.connect_document(doc)


    def get_language_id(self, doc):
        language = doc.get_language()
        if language == None:
            return 'plain_text'
        return language.get_id()


    def strip_trailing_blank_lines(self, doc):
        """Delete trailing space at the end of the document but let the line"""
        lng = self.get_language_id(doc)

        if get_remove_blanklines_eof(lng):
            buffer_end = doc.get_end_iter()
            if buffer_end.starts_line():
                itr = buffer_end.copy()
                while itr.backward_line():
                    if not itr.ends_line():
                        itr.forward_to_line_end()
                        #itr.forward_char()
                        break
                doc.delete(itr, buffer_end)

        if get_insert_newline_eof(lng):
            buffer_end = doc.get_end_iter()
            itr = buffer_end.copy()
            if itr.backward_char():
                if not itr.get_text(buffer_end) == "\n":
                    doc.insert(buffer_end, "\n")


    def strip_trailing_spaces_on_lines(self, doc):
        """Delete trailing space at the end of each line."""
        lng = self.get_language_id(doc)
        if get_crop_spaces_eol(lng):
            buffer_end = doc.get_end_iter()
            for line in range(buffer_end.get_line() + 1):
                line_end = doc.get_iter_at_line(line)
                line_end.forward_to_line_end()
                itr = line_end.copy()
                while itr.backward_char():
                    if not itr.get_char() in (" ", "\t"):
                        itr.forward_char()
                        break
                doc.delete(itr, line_end)


########NEW FILE########
__FILENAME__ = plugin
import os
import logging
from xml.etree import ElementTree as ET
from gi.repository import GObject, Gdk, Gtk, Gedit, GdkPixbuf, Gio

logging.basicConfig()
LOG_LEVEL = logging.DEBUG
DATA_DIR = os.path.join(os.path.dirname(__file__), 'data')
ICON_DIR = os.path.join(DATA_DIR, 'icons', '16x16')  
   
class FavoritesPlugin(GObject.Object, Gedit.WindowActivatable):
    __gtype_name__ = "FavoritesPlugin"
    window = GObject.property(type=Gedit.Window)
    FAVORITE_ICON = Gtk.STOCK_FILE
    FOLDER_ICON = "favorites-folder" #Gtk.STOCK_DIRECTORY
    
    def __init__(self):
        GObject.Object.__init__(self)
        self._log = logging.getLogger(self.__class__.__name__)
        self._log.setLevel(LOG_LEVEL)
        self._install_stock_icons()
  
    def _add_favorites_uri(self, parent_iter, uri):
        """ 
        Add a new favorite URI to the treeview under parent_iter. If the URI
        already exists, it will simply be selected.
        """
        exists = self._select_uri_in_treeview(self._store.get_iter_first(), uri)
        if not exists:
            name = os.path.basename(uri)
            self._store.append(parent_iter, (self.FAVORITE_ICON, name, uri, 0))
    
    def _add_favorites_folder(self, parent_iter, name):
        """ Add a new favorites folder to the treeview under parent_iter. """
        new_iter = self._store.append(parent_iter, (self.FOLDER_ICON, 
                                                    name, None, 1))
        return new_iter
        
    def _add_panel(self):
        # create the modal
        self._store = Gtk.TreeStore(GObject.TYPE_STRING,    # icon
                                    GObject.TYPE_STRING,    # name
                                    GObject.TYPE_STRING,    # uri
                                    GObject.TYPE_INT)       # editable 

        # create the treeview
        self._treeview = Gtk.TreeView.new_with_model(self._store)   
        column = Gtk.TreeViewColumn("Favorite")
        cell = Gtk.CellRendererPixbuf()
        column.pack_start(cell, False)
        column.add_attribute(cell, "stock-id", 0)
        cell = Gtk.CellRendererText()
        self._edit_cell = cell
        cell.connect("edited", self.on_cell_edited)
        column.pack_start(cell, True)
        column.add_attribute(cell, "text", 1)
        column.add_attribute(cell, "editable", 3)
        self._treeview.append_column(column)
        self._treeview.set_tooltip_column(2)
        self._treeview.set_headers_visible(False)
        
        scrolled = Gtk.ScrolledWindow()
        scrolled.set_policy(Gtk.PolicyType.AUTOMATIC, Gtk.PolicyType.AUTOMATIC)
        scrolled.add(self._treeview)
        
        self._panel_widget = Gtk.VBox(homogeneous=False, spacing=2)
        self._panel_widget.pack_start(scrolled, True, True, 0)
        self._panel_widget.show_all()
        self._create_popup_menu()
        
        # add the panel
        filename = os.path.join(ICON_DIR, 'gedit-favorites.png')
        icon = Gtk.Image.new_from_file(filename)
        panel = self.window.get_side_panel()
        panel.add_item(self._panel_widget, "FavoritesPlugin", "Favorites", icon)
        
        # create popup
        
        
        # drag and drop not working in GTK+ 3.0. A patch has been committed.
        self._treeview.set_reorderable(True) 
        """
        targets = [('MY_TREE_MODEL_ROW', Gtk.TargetFlags.SAME_WIDGET, 0),]
        self._treeview.enable_model_drag_source(Gdk.ModifierType.BUTTON1_MASK, 
                                                targets,
                                                Gdk.DragAction.DEFAULT |
                                                Gdk.DragAction.MOVE)
        """
        # connect signals
        self._treeview.connect("row-activated", self.on_row_activated)
        self._treeview.connect("button-press-event", self.on_button_press_event)

    def _add_ui(self):
        """ Merge the 'Project' menu into the Gedit menubar. """
        ui_file = os.path.join(DATA_DIR, 'menu.ui')
        manager = self.window.get_ui_manager()

        self._file_actions = Gtk.ActionGroup("FavoritesFile")
        self._file_actions.add_actions([
            ('AddToFavorites', self.FOLDER_ICON, "A_dd to Favorites", 
                None, "Add document to favorites.", 
                self.on_add_to_favorites_activate),
        ])
        self._file_actions.set_sensitive(False)
        manager.insert_action_group(self._file_actions)       

        self._ui_merge_id = manager.add_ui_from_file(ui_file)
        manager.ensure_update()
    
    def _begin_edit_at_iter(self, tree_iter):
        path = self._store.get_path(tree_iter)
        parent_iter = self._store.iter_parent(tree_iter)
        if parent_iter:
            self._treeview.expand_to_path(path)
        column = self._treeview.get_column(0)
        self._treeview.grab_focus()
        self._treeview.set_cursor_on_cell(path, column, self._edit_cell, True)
        
    def _create_popup_menu(self):
        """ Create the popup menu used by the treeview. """
        manager = Gtk.UIManager()
        self._popup_actions = Gtk.ActionGroup("TreeGlobalActions")
        self._popup_actions.add_actions([
            ('NewFolder', Gtk.STOCK_DIRECTORY, "New _Folder", 
                None, "Add a folder.", 
                self.on_new_folder_activate),
            ('Open', Gtk.STOCK_OPEN, "_Open", 
                None, "Open document.", 
                self.on_open_activate),
            ('Rename', None, "_Rename", 
                None, "Rename the item.", 
                self.on_rename_activate),
            ('Remove', Gtk.STOCK_REMOVE, "Re_move", 
                None, "Remove the item.", 
                self.on_remove_activate),
        ])
        manager.insert_action_group(self._popup_actions)
        ui_file = os.path.join(DATA_DIR, 'popmenu.ui')
        manager.add_ui_from_file(ui_file)
        self._popup = manager.get_widget("/FavoritesPopup")  
        
    def do_activate(self):
        """ Activate plugin. """
        self._add_panel()
        self._add_ui() 
        self.do_update_state()
        self.load_from_xml()

    def do_deactivate(self):
        """ Deactivate plugin. """
        self._remove_panel()
        self._remove_ui()
        self._save_to_xml()

    def do_update_state(self):
        """ Update UI to reflect current state. """
        if self.window.get_active_document():
            self._file_actions.set_sensitive(True)
        else:
            self._file_actions.set_sensitive(False)
    
    def error_dialog(self, message, parent=None):
        """ Display a very basic error dialog """
        self._log.warn(message)
        if not parent:
            parent = self.window
        dialog = Gtk.MessageDialog(parent,
                                   Gtk.DialogFlags.MODAL | 
                                   Gtk.DialogFlags.DESTROY_WITH_PARENT,
                                   Gtk.MessageType.ERROR, Gtk.ButtonsType.OK, 
                                   message)
        dialog.set_title("Error")
        dialog.run()
        dialog.destroy()
    
    def _install_stock_icons(self):
        """ 
        Install the favorites folder icon used in the treeview to avoid confusion
        with the filebrowser plugin.
        """
        factory = Gtk.IconFactory()
        pixbuf = GdkPixbuf.Pixbuf.new_from_file(os.path.join(ICON_DIR, "favorites-folder.png"))
        iconset = Gtk.IconSet.new_from_pixbuf(pixbuf)
        factory.add('favorites-folder', iconset)
        factory.add_default()

    def _load_element(self, parent_iter, element):
        """ Recursive function to add elements from the XML to the treeview. """
        if element.tag == "folder":
            new_iter = self._add_favorites_folder(parent_iter, element.attrib['name'])
            for subelement in element:
                self._load_element(new_iter, subelement)
        elif element.tag == "uri":
            self._add_favorites_uri(parent_iter, element.text)
        
    def load_from_xml(self):
        """ Load the favorites into the treeview from an XML file. """
        self._store.clear()
        filename = os.path.join(DATA_DIR, "favorites.xml")
        xml = ET.parse(filename)
        root = xml.getroot()
        for element in root:
            self._load_element(None, element)

    def on_add_to_favorites_activate(self, action, data=None):
        """ Add the current document to the treeview. """
        document = self.window.get_active_document()
        if document:
            location = document.get_location()
            if location:
                uri = location.get_uri()
                self._add_favorites_uri(None, uri)
    
    def on_button_press_event(self, treeview, event):
        """ Show popup menu. """
        if event.button == 3:
            x = int(event.x)
            y = int(event.y)
            time = event.time
            pthinfo = treeview.get_path_at_pos(x, y)
            if pthinfo is not None:
                path, col, cellx, celly = pthinfo
                treeview.grab_focus()
                treeview.set_cursor(path, col, 0)
                tree_iter = self._store.get_iter(path)
                uri = self._store.get_value(tree_iter, 2)
                if uri: 
                    self._popup_actions.get_action("Open").set_sensitive(True)
                    self._popup_actions.get_action("NewFolder").set_sensitive(False)
                    self._popup_actions.get_action("Rename").set_sensitive(False)
                    self._popup_actions.get_action("Remove").set_sensitive(True)
                else:
                    self._popup_actions.get_action("Open").set_sensitive(True)
                    self._popup_actions.get_action("NewFolder").set_sensitive(True)
                    self._popup_actions.get_action("Rename").set_sensitive(True)
                    self._popup_actions.get_action("Remove").set_sensitive(True)
            else:
                treeview.get_selection().unselect_all()
                self._popup_actions.get_action("Open").set_sensitive(False)
                self._popup_actions.get_action("NewFolder").set_sensitive(True)
                self._popup_actions.get_action("Rename").set_sensitive(False)
                self._popup_actions.get_action("Remove").set_sensitive(False)
            self._popup.popup(None, None, None, None, event.button, time)
            return True
    
    def on_cell_edited(self, cell, path, new_text, data=None):
        self._store[path][1] = new_text
        
    def on_remove_activate(self, action, data=None):
        selection = self._treeview.get_selection()
        model, tree_iter = selection.get_selected()
        self._store.remove(tree_iter)
    
    def on_row_inserted(self, model, path, tree_iter, data=None):
        print "on_row_inserted"
        self._store.set_value(tree_iter, 1, "test")
        
    def on_rows_reordered(self, model, path, tree_iter, new_order, data=None):
        print "on_rows_reordered"
        self._store.set_value(tree_iter, 1, "test")
        
    def on_new_folder_activate(self, action, data=None):
        """ Create a new untitled folder. """
        selection = self._treeview.get_selection()
        model, tree_iter = selection.get_selected()
        if tree_iter:
            uri = model.get_value(tree_iter, 2)
            if uri is not None:
                parent_iter = model.iter_parent(tree_iter)
            else:
                parent_iter = tree_iter
        else:
            parent_iter = None
        new_iter = self._add_favorites_folder(parent_iter, "Untitled")
        self._begin_edit_at_iter(new_iter)
        
    def on_open_activate(self, action, data=None):
        selection = self._treeview.get_selection()
        model, tree_iter = selection.get_selected()
        uri = model.get_value(tree_iter, 2)
        if uri:
            self._open_uri(uri)
        else:
            self._open_uris_at_iter(tree_iter)
    
    def on_rename_activate(self, action, data=None):
        selection = self._treeview.get_selection()
        model, tree_iter = selection.get_selected()
        if tree_iter:
            self._begin_edit_at_iter(tree_iter)
        
    def on_row_activated(self, treeview, path, column, data=None):
        model = treeview.get_model()
        tree_iter = model.get_iter(path)
        uri = model.get_value(tree_iter, 2)
        if uri:
            self._open_uri(uri)
   
    def _open_uri(self, uri):
        location = Gio.file_new_for_uri(uri)
        tab = self.window.get_tab_from_location(location)
        if tab:
            self.window.set_active_tab(tab)
        else:
            self.window.create_tab_from_location(location, None, 0, 0, False, True) 
    
    def _open_uris_at_iter(self, tree_iter):
        """ Recursively open all URIs under tree_iter. """
        model = self._store
        while tree_iter:
            uri = model.get_value(tree_iter, 2)
            if uri:
                self._open_uri(uri)
            if model.iter_has_child(tree_iter):
                child_iter = model.iter_children(tree_iter)
                self._open_uris_at_iter(child_iter)
            tree_iter = model.iter_next(tree_iter)
    
    def _remove_panel(self):
        """ Removes the side panel """
        if self._panel_widget:
            panel = self.window.get_side_panel()
            panel.remove_item(self._panel_widget)
        
    def _remove_ui(self):
        """ Remove the 'Project' menu from the Gedit menubar. """
        manager = self.window.get_ui_manager()
        manager.remove_ui(self._ui_merge_id)
        manager.remove_action_group(self._file_actions)
        manager.ensure_update()

    def _get_xml_at_iter(self, tree_iter, spaces=2):
        xml = ""
        tabs = " " * spaces
        while tree_iter:
            if self._store.get_value(tree_iter, 2) == None:
                name = self._store.get_value(tree_iter, 1)
                xml += "%s<folder name=\"%s\">\n" % (tabs, name)
                if self._store.iter_has_child(tree_iter):
                    child_iter = self._store.iter_children(tree_iter)
                    xml += self._get_xml_at_iter(child_iter, spaces+2)
                xml += "%s</folder>\n" % tabs
            else:
                uri = self._store.get_value(tree_iter, 2)
                xml += "%s<uri>%s</uri>\n" % (tabs, uri)
                """
                Temporary hack to fix folders dropped on files since we cannot
                implement a custom drag and drop in GTK+ 3.0 (patch committed)
                """
                if self._store.iter_has_child(tree_iter):
                    name = self._store.get_value(tree_iter, 1)
                    xml += "%s<folder name=\"%s\">\n" % (tabs, name)
                    child_iter = self._store.iter_children(tree_iter)
                    xml += self._get_xml_at_iter(child_iter, spaces+2)
                    xml += "%s</folder>\n" % tabs
                    
            tree_iter = self._store.iter_next(tree_iter)
        
        return xml
        
    def _save_to_xml(self):
        """ Save the favorites tree to the XML file. """
        filename = os.path.join(DATA_DIR, "favorites.xml")
        xml =  "<?xml version=\"1.0\" encoding=\"UTF-8\"?>\n"
        xml += "<gedit-favorites version=\"1.0\">\n"
        xml += self._get_xml_at_iter(self._store.get_iter_first())
        xml += "</gedit-favorites>\n"
        
        f = open(filename, "w")
        f.write(xml)
        f.close()
    
    def _select_uri_in_treeview(self, tree_iter, uri):
        """ Recursively find URI in treeview and select it or return False. """
        model = self._store
        while tree_iter:
            row_uri = model.get_value(tree_iter, 2)
            if row_uri:
                if row_uri == uri:
                    path = model.get_path(tree_iter)
                    self._treeview.expand_to_path(path)
                    self._treeview.set_cursor(path, None, False)
                    return True
            if model.iter_has_child(tree_iter):
                child_iter = model.iter_children(tree_iter)
                exists = self._select_uri_in_treeview(child_iter, uri)
                if exists:
                    return exists
            tree_iter = model.iter_next(tree_iter)
        return False

    
    

########NEW FILE########
__FILENAME__ = pair_char_completion
# -*- coding: utf-8 -*-
#
# Gedit plugin that does automatic pair character completion.
#
# Copyright © 2010, Kevin McGuinness <kevin.mcguinness@gmail.com>
#
# This program is free software; you can redistribute it and/or modify it under
# the terms of the GNU General Public License as published by the Free Software
# Foundation; either version 2 of the License, or (at your option) any later
# version.
#
# This program is distributed in the hope that it will be useful, but WITHOUT
# ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS
# FOR A PARTICULAR PURPOSE. See the GNU General Public License for more
# details.
#
# You should have received a copy of the GNU General Public License along with
# this program; if not, write to the Free Software Foundation, Inc., 51
# Franklin Street, Fifth Floor, Boston, MA 02110-1301, USA.
#

__version__ = '1.0.4'
__author__ = 'Kevin McGuinness'

from gi.repository import Gtk, Gedit, GObject, Gdk
import sys
import os

# Defaults
DEFAULT_STMT_TERMINATOR = ';'
LANG_META_STMT_TERMINATOR_KEY = 'statement-terminator'
NEWLINE_CHAR = '\n'

# Map from language identifiers to (opening parens, closing parens) pairs
language_parens = {}

def add_language_parenthesis(name, spec):
  """Add parenthesis for the given language. The spec should be a string in
     which each pair of characters represents a pair of parenthesis for the
     language, eg. "(){}[]".
  """
  parens = [], []
  for i in range(0, len(spec), 2):
    parens[0].append(spec[i+0])
    parens[1].append(spec[i+1])
  language_parens[name] = parens

def to_char(keyval_or_char):
  """Convert a event keyval or character to a character"""
  if isinstance(keyval_or_char, str):
    return keyval_or_char
  return chr(keyval_or_char) if 0 < keyval_or_char < 128 else None

class PairCompletionPlugin(GObject.Object, Gedit.WindowActivatable):
  """Automatic pair character completion for gedit"""

  ViewHandlerName = 'pair_char_completion_handler'

  window = GObject.property(type=Gedit.Window)

  def __init__(self):
    GObject.Object.__init__(self)
    self.ctrl_enter_enabled = True
    self.language_id = 'plain'
    self.opening_parens = language_parens['default'][0]
    self.closing_parens = language_parens['default'][1]

  def do_activate(self):
    self.do_update_state()

  def do_deactivate(self):
    for view in self.window.get_views():
      handler_id = getattr(view, self.ViewHandlerName, None)
      if handler_id is not None:
        view.disconnect(handler_id)
      setattr(view, self.ViewHandlerName, None)

  def do_update_state(self):
    self.update_ui()


  def update_ui(self):
    view = self.window.get_active_view()
    doc = self.window.get_active_document()
    if isinstance(view, Gedit.View) and doc:
      if getattr(view, self.ViewHandlerName, None) is None:
        handler_id = view.connect('key-press-event', self.on_key_press, doc)
        setattr(view, self.ViewHandlerName, handler_id)

  def is_opening_paren(self,char):
    return char in self.opening_parens

  def is_closing_paren(self,char):
    return char in self.closing_parens

  def get_matching_opening_paren(self,closer):
    try:
      return self.opening_parens[self.closing_parens.index(closer)]
    except ValueError:
      return None

  def get_matching_closing_paren(self,opener):
    try:
      return self.closing_parens[self.opening_parens.index(opener)]
    except ValueError:
      return None

  def would_balance_parens(self, doc, closing_paren):
    iter1 = doc.get_iter_at_mark(doc.get_insert())
    opening_paren = self.get_matching_opening_paren(closing_paren)
    balance = 1
    while balance != 0 and not iter1.is_start():
      iter1.backward_char()
      if iter1.get_char() == opening_paren:
        balance -= 1
      elif iter1.get_char() == closing_paren:
        balance += 1
    return balance == 0

  def compare_marks(self, doc, mark1, mark2):
    return doc.get_iter_at_mark(mark1).compare(doc.get_iter_at_mark(mark2))

  def enclose_selection(self, doc, opening_paren):
    closing_paren = self.get_matching_closing_paren(opening_paren)
    doc.begin_user_action()
    mark1 = doc.get_insert()
    mark2 = doc.get_selection_bound()
    if self.compare_marks(doc, mark1, mark2) > 0:
      mark1, mark2 = mark2, mark1
    doc.insert(doc.get_iter_at_mark(mark1), opening_paren)
    doc.insert(doc.get_iter_at_mark(mark2), closing_paren)
    iter1 = doc.get_iter_at_mark(mark2)
    doc.place_cursor(iter1)
    doc.end_user_action()
    return True

  def auto_close_paren(self, doc, opening_paren):
    closing_paren = self.get_matching_closing_paren(opening_paren)
    doc.begin_user_action()
    doc.insert_at_cursor(opening_paren+closing_paren)
    iter1 = doc.get_iter_at_mark(doc.get_insert())
    iter1.backward_char()
    doc.place_cursor(iter1)
    doc.end_user_action()
    return True

  def move_cursor_forward(self, doc):
    doc.begin_user_action()
    iter1 = doc.get_iter_at_mark(doc.get_insert())
    iter1.forward_char()
    doc.place_cursor(iter1)
    doc.end_user_action()
    return True

  def move_to_end_of_line_and_insert(self, doc, text):
    doc.begin_user_action()
    mark = doc.get_insert()
    iter1 = doc.get_iter_at_mark(mark)
    iter1.set_line_offset(0)
    iter1.forward_to_line_end()
    doc.place_cursor(iter1)
    doc.insert_at_cursor(text)
    doc.end_user_action()
    return True

  def insert_two_lines(self, doc, text):
    doc.begin_user_action()
    mark = doc.get_insert()
    iter1 = doc.get_iter_at_mark(mark)
    doc.place_cursor(iter1)
    doc.insert_at_cursor(text)
    doc.insert_at_cursor(text)
    mark = doc.get_insert()
    iter2 = doc.get_iter_at_mark(mark)
    iter2.backward_chars(len(text))
    doc.place_cursor(iter2)
    doc.end_user_action()
    return True

  def get_char_under_cursor(self, doc):
    return doc.get_iter_at_mark(doc.get_insert()).get_char()

  def get_stmt_terminator(self, doc):
    terminator = DEFAULT_STMT_TERMINATOR
    lang = doc.get_language()
    if lang is not None:
      # Allow this to be changed by the language definition
      lang_terminator = lang.get_metadata(LANG_META_STMT_TERMINATOR_KEY)
      if lang_terminator is not None:
        terminator = lang_terminator
    return terminator

  def get_current_line_indent(self, doc):
    it_start = doc.get_iter_at_mark(doc.get_insert())
    it_start.set_line_offset(0)
    it_end = it_start.copy()
    it_end.forward_to_line_end()
    indentation = []
    while it_start.compare(it_end) < 0:
      char = it_start.get_char()
      if char == ' ' or char == '\t':
        indentation.append(char)
      else:
        break
      it_start.forward_char()
    return ''.join(indentation)

  def is_ctrl_enter(self, event):
    return (self.ctrl_enter_enabled and
      event.keyval == Gdk.KEY_Return and
      event.get_state() & Gdk.ModifierType.CONTROL_MASK)

  def should_auto_close_paren(self, doc):
    iter1 = doc.get_iter_at_mark(doc.get_insert())
    if iter1.is_end() or iter1.ends_line():
      return True
    char = iter1.get_char()
    return not (char.isalnum() or char == '_')

  def update_language(self, doc):
    lang = doc.get_language()
    lang_id = lang.get_id() if lang is not None else 'plain'
    if lang_id != self.language_id:
      parens = language_parens.get(lang_id, language_parens['default'])
      self.opening_parens = parens[0]
      self.closing_parens = parens[1]
      self.language_id = lang_id

  def on_key_press(self, view, event, doc):
    handled = False
    self.update_language(doc)
    ch = to_char(event.keyval)
    key = Gdk.keyval_name(event.keyval)
    if self.is_closing_paren(ch):
      # Skip over closing parenthesis if doing so would mean that the
      # preceeding parenthesis are correctly balanced
      if (self.get_char_under_cursor(doc) == ch and
          self.would_balance_parens(doc, ch)):
        handled = self.move_cursor_forward(doc)
    if not handled and self.is_opening_paren(ch):
      if doc.get_has_selection():
        # Enclose selection in parenthesis or quotes
        handled = self.enclose_selection(doc, ch)
      elif self.should_auto_close_paren(doc):
        # Insert matching closing parenthesis and move cursor back one
        handled = self.auto_close_paren(doc, ch)
    if not handled and self.is_ctrl_enter(event):
      # Handle Ctrl+Return and Ctrl+Shift+Return
      text_to_insert = NEWLINE_CHAR + self.get_current_line_indent(doc)
      if event.get_state() & Gdk.EventMask.SHIFT_MASK:
        text_to_insert = self.get_stmt_terminator(doc) + text_to_insert
      self.move_to_end_of_line_and_insert(doc, text_to_insert)
      view.scroll_mark_onscreen(doc.get_insert())
      handled = True
    if not handled and key in ('Enter', 'Return', 'ISO_Return'):
      # Enter was just pressed
      char_under_cusor = self.get_char_under_cursor(doc)
      if (self.is_closing_paren(char_under_cusor) and
        self.would_balance_parens(doc, char_under_cusor)):
        # If the character under the cursor would balance parenthesis
        text_to_insert = NEWLINE_CHAR + self.get_current_line_indent(doc)
        self.insert_two_lines(doc, text_to_insert)
        handled = True
    return handled

# Load language parenthesis
for path in sys.path:
  fn = os.path.join(path, 'pair_char_lang.py')
  if os.path.isfile(fn):
    execfile(fn, {'lang': add_language_parenthesis})
    break

########NEW FILE########
__FILENAME__ = pair_char_lang
# -*- coding: utf-8 -*-
#
# Programming language pair char support
#
# The default set is used if the language is not specified below. The plain
# set is used for plain text, or when the document has no specified language.
#
lang('default',    '(){}[]""\'\'``')
lang('changelog',  '(){}[]""<>')
lang('html',       '(){}[]""<>')
lang('ruby',       '(){}[]""\'\'``||')
lang('xml',        '(){}[]""<>')
lang('php',        '(){}[]""<>')
lang('plain',      '(){}[]""')
lang('latex',      '(){}[]""$$`\'')

########NEW FILE########
__FILENAME__ = config
import os
import pastie
from gi.repository import Gtk

CONFIG_FILE = os.path.dirname( __file__ ) + '/config.pur'

LINKS = ['Clipboard', 'Window']
PRIVATES = ['True', 'False']
SYNTAXES = list(pastie.LANGS) 

class NoConfig(Exception): pass

class ConfigDialog():
    def __init__(self):

        self._glade = Gtk.Builder()
        self._glade.add_from_file(os.path.join(os.path.dirname(__file__), 'Config.ui'))
        self.window = self._glade.get_object("dialog")
        self._syntax = self._glade.get_object("syntax")
        self._link = self._glade.get_object("link")
        self._ok_button = self._glade.get_object("ok_button")
        self._cancel_button = self._glade.get_object("cancel_button")
        self._private = self._glade.get_object("private")
        self.set_syntaxes()
        self.set_links()
        
        self._cancel_button.connect("clicked", self.hide)
    
    def set_syntaxes(self):
        for syntax in SYNTAXES:
            self._syntax.append_text(syntax)
    
    def set_links(self):
        for link in LINKS:
            self._link.append_text(link)
     
    def set_private(self, private):
        if private == "True":
            to_set = True
        else:
            to_set = False
        
        self._private.set_active(to_set)
        
    def set_syntax(self, syntax):
        self._syntax.set_active(SYNTAXES.index(syntax))
    
    def set_link(self, link):
        self._link.set_active(LINKS.index(link))
            
    def get_link(self):
        return self._link.get_model()[self._link.get_active()][0]
    
    def get_syntax(self):
        return self._syntax.get_model()[self._syntax.get_active()][0]

    def get_private(self):
        return self._private.get_active()
    
    def hide(self, widget=None, event=None):
        self.window.hide()
        self.reset()
        return True

    def connect_ok(self, func):
        self._ok_button.connect("clicked", lambda a: func())
    
        
class Configuration():

    def __init__(self):
        self._config_exists = os.access(CONFIG_FILE, os.R_OK)
        self.window = ConfigDialog()
        self.window.connect_ok(self.ok)
        try:
            self.read()
        except NoConfig:
            self.new()
        self.window_set()
        self.window.reset = self.window_set
        self.call_when_configuration_changes = None
        
    def error_dialog(self):
        dialog = Gtk.MessageDialog(message_format="Error reading/writing configuration file!", 
                                   buttons = Gtk.ButtonsType.OK,
                                   type = Gtk.MessageType.ERROR )
        dialog.set_title("Error!")
        dialog.connect("response", lambda x, y: dialog.destroy())
        dialog.run()
    
    def read(self):
        if self._config_exists:
            try:
                f = open(CONFIG_FILE, 'rb')
            except:
                self.error_dialog()
            else:
                self.data = f.read()
                self.parse()
            finally:
                f.close()
        else:
            raise NoConfig
           
    def new(self):
        self.syntax = "Plain Text"
        self.link = "Window"
        self.private = "True"
        self.save()
        
    def parse(self):
        array = self.data.split("\n")
        if len(array) < 3:
            self.new()
        else:
          self.syntax = array[0]
          self.link = array[1]
          self.private = array[2]
        try:
            LINKS.index(self.link)
            PRIVATES.index(self.private)
            SYNTAXES.index(self.syntax) 
        except ValueError:
            self.new()
            
    def window_set(self):
        self.window.set_link(self.link)
        self.window.set_syntax(self.syntax)
        self.window.set_private(self.private)
        
    def ok(self):
        self.syntax = self.window.get_syntax()
        self.link = self.window.get_link()
        if self.window.get_private():
            self.private = "True"
        else:
            self.private = "False"
        self.save()
        self.window.hide()
        if self.call_when_configuration_changes:
            self.call_when_configuration_changes()
        
    def save(self):
        try:
            f = open(CONFIG_FILE, 'w')
        except:
            self.error_dialog()
        else:
            f.write("\n".join([self.syntax, self.link, self.private])+"\n")
        finally:
            f.close()
        

########NEW FILE########
__FILENAME__ = pastie
import urllib2
import urllib

PASTES = {
    'Ruby (on Rails)':'ruby_on_rails',
    'Ruby':'ruby',
    'Python':'python',
    'Plain Text':'plain_text',
    'ActionScript':'actionscript',
    'C/C++':'c++',
    'CSS':'css',
    'Diff':'diff',
    'HTML (Rails)':'html_rails',
    'HTML / XML':'html',
    'Java':'java',
    'JavaScript':'javascript',
    'Objective C/C++':'objective-c++',
    'PHP':'php',
    'SQL':'sql',
    'Shell Script':'shell-unix-generic'
}
#because dictionaries don't store order
LANGS = ('Ruby (on Rails)', 'Ruby', 'Python', 'Plain Text', 'ActionScript', 'C/C++', 'CSS', 'Diff', 'HTML (Rails)', 'HTML / XML', 'Java', 'JavaScript', 'Objective C/C++', 'PHP', 'SQL', 'Shell Script')
         
URL = 'http://pastie.org/pastes'

class Pastie:

    def __init__(self, text='', syntax='Plain Text', private=False):
        self.text = text
        self.syntax = syntax
        self.private = private

    def paste(self):
        if not PASTES.has_key(self.syntax):
            return 'Wrong syntax.'
        
        opener = urllib2.build_opener()
        params = {
                  'paste[body]':self.text,
                  'paste[parser]':PASTES[self.syntax],
                  'paste[authorization]':'burger' #pastie protecion against general spam bots
                  }
        if self.private:
            params['paste[restricted]'] = '1'
        else:
            params['paste[restricted]'] = '0'
            
        data = urllib.urlencode(params)
        request = urllib2.Request(URL, data)
        request.add_header('User-Agent', 'PastiePythonClass/1.0 +http://hiler.pl/')
        try:
            firstdatastream = opener.open(request)
        except:
            return 'We are sorry but something went wrong. Maybe pastie is down?'
        else:
            return firstdatastream.url
            

########NEW FILE########
__FILENAME__ = windows
import os
import pastie
import config
from gi.repository import Gtk

class Window():

    def __init__(self, gladefile):

        self._glade = Gtk.Builder()
        self._glade.add_from_file(os.path.join(os.path.dirname(__file__), gladefile))
        self._window = self._glade.get_object("window")
        self._window.connect("delete_event", self._hide)
        
    def _hide(self, widget, event):
        widget.hide()
        return True
    
    def show(self, dummy=None):
        self._window.show()
        

class PastieWindow(Window):

    def __init__(self,):
        Window.__init__(self, "PasteWindow.ui")
       
        syntaxCombo = self._glade.get_object("syntax")

        for lang in pastie.LANGS:
            syntaxCombo.append_text(lang)
        
        self._glade.get_object("syntax").set_active(0) #sets active posision in syntax list
        self._glade.get_object("ok_button").connect("clicked", self._ok_button)
        self._glade.get_object("cancel_button").connect("clicked", lambda a: self._window.hide())
        
        self.inform = Inform()
        self.config = config.Configuration()
        
        self.set_from_defaults()
        self.config.call_when_configuration_changes = self.set_from_defaults
     
    def set_from_defaults(self):
        self._glade.get_object("syntax").set_active(config.SYNTAXES.index(self.config.syntax))
        
        if self.config.private == "True":
            to_set = True
        else:
            to_set = False
        
        self._glade.get_object("private").set_active(to_set)
        
        
    def _ok_button(self, event=None):
        text = self.get_text()
        combox = self._glade.get_object("syntax")
        model = combox.get_model()
        active = combox.get_active()
        syntax = model[active][0]
        priv = self._glade.get_object("private").get_active()
        self._window.hide()
        self._paste(syntax, priv, text, self.config.link)
        
    def paste_defaults(self, bla):
        if self.config.private == "True":
            private = True
        else:
            private = False
            
        self._paste(self.config.syntax, private, self.get_text(), self.config.link)
        
        
    def _paste(self, syntax, priv, text, link):
        "pastes selected text and displays window with link"
        p = pastie.Pastie(text, syntax, priv)
        paste = p.paste()
        if link == "Window":
            self.inform.entry.set_text("please wait")
            self.inform.show() #shows window
            self.inform.entry.set_text(paste)
        else:
            clipboard = Gtk.clipboard_get('CLIPBOARD')
            clipboard.set_text(paste)
            clipboard.store()

class Inform(Window):

    def __init__(self):
        Window.__init__(self, "Inform.ui")
        self.entry = self._glade.get_object("link")
        self._glade.get_object("ok_button").connect("clicked", lambda a: self._window.hide())


########NEW FILE########
__FILENAME__ = restoretabs
import os
from gi.repository import GObject, GLib, Gtk, Gio, Gedit

SETTINGS_SCHEMA = "org.gnome.gedit.plugins.restoretabs"

class RestoreTabsWindowActivatable(GObject.Object, Gedit.WindowActivatable):
    __gtype_name__ = "RestoreTabsWindowActivatable"
    window = GObject.property(type=Gedit.Window)

    def __init__(self):
        GObject.Object.__init__(self)
        self._handlers = []
    
    def do_activate(self):
        handlers = []
        handler_id = self.window.connect("delete-event", 
                                         self.on_window_delete_event)                             
        self._handlers.append(handler_id)
        self._temp_handler = self.window.connect("show", self.on_window_show)  

    def do_deactivate(self):
        [self.window.disconnect(handler_id) for handler_id in self._handlers]
    
    def do_update_state(self):
        pass
        
    def is_first_window(self):
        app = Gedit.App.get_default()
        if len(app.get_windows()) <= 1:
            return True
        else:
            return False

    def on_window_delete_event(self, window, event, data=None):
        uris = []
        for document in window.get_documents():
            gfile = document.get_location()
            if gfile:
                uris.append(gfile.get_uri())
        settings = Gio.Settings.new(SETTINGS_SCHEMA)
        settings.set_value('uris', GLib.Variant("as", uris))
        return False
    
    def on_window_show(self, window, data=None):
        if self.is_first_window():
            tab = self.window.get_active_tab()
            if tab.get_state() == 0 and not tab.get_document().get_location():
                self.window.close_tab(tab)
            settings = Gio.Settings.new(SETTINGS_SCHEMA)
            uris = settings.get_value('uris')
            if uris:
                for uri in uris:
                    location = Gio.file_new_for_uri(uri)
                    tab = self.window.get_tab_from_location(location)
                    if not tab:
                        self.window.create_tab_from_location(location, None, 0, 
                                                             0, False, True)
            self.window.disconnect(self._temp_handler)


########NEW FILE########
__FILENAME__ = config_manager
# -*- encoding:utf-8 -*-


# config_manager.py
#
# Copyright 2010 swatch
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU General Public License for more details.
# 
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA 02111-1307 USA
#



import os
from xml.dom.minidom import parse

class ConfigManager:
	def __init__(self, filename):
		if os.path.exists(filename) == True:
			self.config_file = filename
			self.dom = parse(filename) # parse an XML file by name
			#self.root = self.dom.documentElement
	
	def get_configure(self, branch, attr):
		root = self.dom.documentElement
		nodes = root.getElementsByTagName(branch)
		for i in range(0, len(nodes)):
			if nodes[i].getAttribute('name') == attr:
				return nodes[i].firstChild.nodeValue
	
	def load_configure(self, branch):
		root = self.dom.documentElement
		nodes = root.getElementsByTagName(branch)
		dic = {}
		for i in range(0, len(nodes)):
			dic[nodes[i].getAttribute('name')] = nodes[i].firstChild.nodeValue
		return dic
	
	def update_config_file(self, filename, branch, dic):
		root = self.dom.documentElement
		nodes = root.getElementsByTagName(branch)
		for i in range(0, len(nodes)):
			nodes[i].firstChild.nodeValue = dic[nodes[i].getAttribute('name')]

		f = open(filename, 'w+')
		f.write(self.dom.toprettyxml('', '', 'utf-8'))
		f.close
		
	def boolean(self, string):
		return string.lower() in ['true', 'yes', 't', 'y', 'ok', '1']
		
	def to_bool(self, dic):
		for key in dic.keys():
			dic[key] = self.boolean(dic[key])

	
if __name__ == '__main__':
	pass

########NEW FILE########
__FILENAME__ = config_ui
# -*- encoding:utf-8 -*-


# config_ui.py
#
#
# Copyright 2010 swatch
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU General Public License for more details.
# 
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA 02111-1307 USA
#



#import sys
from gi.repository import Gtk, Gedit, Gdk
import os.path

#Gtk.glade.bindtextdomain('smart-highlight', os.path.join(os.path.dirname(__file__), 'locale'))
#Gtk.glade.textdomain('smart-highlight')


class ConfigUI(object):
	def __init__(self, plugin):
		#self._plugin = plugin
		self._instance, self._window = plugin.get_instance()
	
		#Set the Glade file
		gladefile = os.path.join(os.path.dirname(__file__),"config.glade")
		UI = Gtk.Builder()
		UI.set_translation_domain('smart-highlight')
		UI.add_from_file(gladefile)
		self.configWindow = UI.get_object("configWindow")
		self.matchWholeWordCheckbutton = UI.get_object("matchWholeWordCheckbutton")
		self.matchCaseCheckbutton = UI.get_object("matchCaseCheckbutton")
		self.regexSearchCheckbutton = UI.get_object("regexSearchCheckbutton")
		self.fgColorbutton = UI.get_object("fgColorbutton")
		self.bgColorbutton = UI.get_object("bgColorbutton")
		
		self.matchWholeWordCheckbutton.set_active(self._instance.options['MATCH_WHOLE_WORD'])
		self.matchCaseCheckbutton.set_active(self._instance.options['MATCH_CASE'])
		self.regexSearchCheckbutton.set_active(self._instance.options['REGEX_SEARCH'])
		self.fgColorbutton.set_color(Gdk.color_parse(self._instance.smart_highlight['FOREGROUND_COLOR']))
		self.bgColorbutton.set_color(Gdk.color_parse(self._instance.smart_highlight['BACKGROUND_COLOR']))
			
		self.configWindow.show_all()

		signals = { "on_configWindow_destroy" : self.on_configWindow_destroy,
					"on_matchWholeWordCheckbutton_toggled" : self.on_matchWholeWordCheckbutton_toggled,
					"on_matchCaseCheckbutton_toggled" : self.on_matchCaseCheckbutton_toggled,
					"on_regexSearchCheckbutton_toggled": self.on_regexSearchCheckbutton_toggled,
					"on_fgColorbutton_color_set" : self.on_fgColorbutton_color_set,
					"on_bgColorbutton_color_set" : self.on_bgColorbutton_color_set }
		
		UI.connect_signals(signals)
		
		
	def on_configWindow_destroy(self, widget):
		pass
		
	def on_matchWholeWordCheckbutton_toggled(self, widget):
		self._instance.options['MATCH_WHOLE_WORD'] = widget.get_active()
		
	def on_matchCaseCheckbutton_toggled(self, widget):
		self._instance.options['MATCH_CASE'] = widget.get_active()
	
	def on_regexSearchCheckbutton_toggled(self, widget):
		self._instance.options['REGEX_SEARCH'] = widget.get_active()
		
	def on_fgColorbutton_color_set(self, widget):
		self._instance.smart_highlight['FOREGROUND_COLOR'] = widget.get_color().to_string()
		
	def on_bgColorbutton_color_set(self, widget):
		self._instance.smart_highlight['BACKGROUND_COLOR'] = widget.get_color().to_string()	


if __name__ == '__main__':
	dlg = ConfigUI(None)
	Gtk.main()


########NEW FILE########
__FILENAME__ = smart_highlight
# -*- encoding:utf-8 -*-


# smart_highlight.py
#
#
# Copyright 2010 swatch
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU General Public License for more details.
# 
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA 02111-1307 USA
#




from gi.repository import Gtk, Gedit
import re
import os.path
#import pango

import config_manager
from config_ui import ConfigUI

import gettext
APP_NAME = 'smart-highlight'
#LOCALE_DIR = '/usr/share/locale'
LOCALE_DIR = os.path.join(os.path.dirname(__file__), 'locale')
if not os.path.exists(LOCALE_DIR):
	LOCALE_DIR = '/usr/share/locale'
try:
	t = gettext.translation(APP_NAME, LOCALE_DIR)
	_ = t.gettext
except:
	pass
#gettext.install(APP_NAME, LOCALE_DIR, unicode=True)


ui_str = """<ui>
	<menubar name="MenuBar">
		<menu name="ToolsMenu" action="Tools">
			<placeholder name="ToolsOps_0">
				<separator/>
				<menu name="SmartHighlightMenu" action="SmartHighlightMenu">
					<placeholder name="SmartHighlightMenuHolder">
						<menuitem name="smart_highlight_configure" action="smart_highlight_configure"/>
					</placeholder>
				</menu>
				<separator/>
			</placeholder>
		</menu>
	</menubar>
</ui>
"""



class SmartHighlightWindowHelper:
	def __init__(self, plugin, window):
		self._window = window
		self._plugin = plugin
		views = self._window.get_views()
		for view in views:
			view.get_buffer().connect('mark-set', self.on_textbuffer_markset_event)
		self.active_tab_added_id = self._window.connect("tab-added", self.tab_added_action)
		
		configfile = os.path.join(os.path.dirname(__file__), "config.xml")
		self.config_manager = config_manager.ConfigManager(configfile)
		self.options = self.config_manager.load_configure('search_option')
		self.config_manager.to_bool(self.options)
		self.smart_highlight = self.config_manager.load_configure('smart_highlight')
		
		self._insert_menu()

	def deactivate(self):
		# Remove any installed menu items
		self._window.disconnect(self.active_tab_added_id)
		self.config_manager.update_config_file(self.config_manager.config_file, 'search_option', self.options)
		self.config_manager.update_config_file(self.config_manager.config_file, 'smart_highlight', self.smart_highlight)
		
	def _insert_menu(self):
		# Get the GtkUIManager
		manager = self._window.get_ui_manager()

		# Create a new action group
		self._action_group = Gtk.ActionGroup("SmartHighlightActions")
		self._action_group.add_actions( [("SmartHighlightMenu", None, _('Smart Highlighting'))] + \
										[("smart_highlight_configure", None, _("Configuration"), None, _("Smart Highlighting Configure"), self.smart_highlight_configure)]) 

		# Insert the action group
		manager.insert_action_group(self._action_group, -1)

		# Merge the UI
		self._ui_id = manager.add_ui_from_string(ui_str)
	
	def _remove_menu(self):
		# Get the GtkUIManager
		manager = self._window.get_ui_manager()

		# Remove the ui
		manager.remove_ui(self._ui_id)

		# Remove the action group
		manager.remove_action_group(self._action_group)

		# Make sure the manager updates
		manager.ensure_update()

	def update_ui(self):
		self._action_group.set_sensitive(self._window.get_active_document() != None)

	'''		
	def show_message_dialog(self, text):
		dlg = Gtk.MessageDialog(self._window, 
								Gtk.DialogFlags.MODAL | Gtk.DialogFlags.DESTROY_WITH_PARENT,
								Gtk.MessageType.INFO,
								Gtk.ButtonsType.CLOSE,
								_(text))
		dlg.run()
		dlg.hide()
	#'''
		
		
	def create_regex(self, pattern, options):
		if options['REGEX_SEARCH'] == False:
			pattern = re.escape(unicode(r'%s' % pattern, "utf-8"))
		else:
			pattern = unicode(r'%s' % pattern, "utf-8")
		
		if options['MATCH_WHOLE_WORD'] == True:
			pattern = r'\b%s\b' % pattern
			
		if options['MATCH_CASE'] == True:
			regex = re.compile(pattern, re.MULTILINE)
		else:
			regex = re.compile(pattern, re.IGNORECASE | re.MULTILINE)
		
		return regex

	def smart_highlighting_action(self, doc, search_pattern):
		regex = self.create_regex(search_pattern, self.options)
		self.smart_highlight_off(doc)
		start, end = doc.get_bounds()
		text = unicode(doc.get_text(start, end, True), 'utf-8')
		
		match = regex.search(text)
		while(match):
			self.smart_highlight_on(doc, match.start(), match.end() - match.start())
			match = regex.search(text, match.end()+1)
			
	def tab_added_action(self, action, tab):
		view = tab.get_view()
		view.get_buffer().connect('mark-set', self.on_textbuffer_markset_event)
	
	def on_textbuffer_markset_event(self, textbuffer, iter, textmark):
		if textmark.get_name() == None:
			return
		if textbuffer.get_selection_bounds():
			start, end = textbuffer.get_selection_bounds()
 			self.smart_highlighting_action(textbuffer, textbuffer.get_text(start, end, True))
 		else:
 			self.smart_highlight_off(textbuffer)
	
	def smart_highlight_on(self, doc, highlight_start, highlight_len):
		if doc.get_tag_table().lookup('smart_highlight') == None:
			tag = doc.create_tag("smart_highlight", foreground=self.smart_highlight['FOREGROUND_COLOR'], background=self.smart_highlight['BACKGROUND_COLOR'])
		doc.apply_tag_by_name('smart_highlight', doc.get_iter_at_offset(highlight_start), doc.get_iter_at_offset(highlight_start + highlight_len))
		
	def smart_highlight_off(self, doc):
		start, end = doc.get_bounds()
		if doc.get_tag_table().lookup('smart_highlight') == None:
			tag = doc.create_tag("smart_highlight", foreground=self.smart_highlight['FOREGROUND_COLOR'], background=self.smart_highlight['BACKGROUND_COLOR'])
		doc.remove_tag_by_name('smart_highlight', start, end)
		
	def smart_highlight_configure(self, action, data = None):
		config_ui = ConfigUI(self._plugin)
	


########NEW FILE########
__FILENAME__ = tabswitch
# -*- coding: utf-8 -*-

VERSION = "0.1"

from gi.repository import GObject, Gtk, Gedit, Gdk, Gio
from gettext import gettext as _
import cPickle, os

class TabSwitchPlugin(GObject.Object, Gedit.WindowActivatable):
    __gtype_name__ = "ExamplePyWindowActivatable"
    window = GObject.property(type=Gedit.Window)

    def __init__(self):
        GObject.Object.__init__(self)
        self.id_name = 'TabSwitchPluginID'
    
    def do_activate(self):
        l_ids = []
        for signal in ('key-press-event',):
            method = getattr(self, 'on_window_' + signal.replace('-', '_'))
            l_ids.append(self.window.connect(signal, method))
        self.window.set_data(self.id_name, l_ids)
    
    def do_deactivate(self):
        l_ids = self.window.get_data(self.id_name)
        
        for l_id in l_ids:
            self.window.disconnect(l_id)
    
    def on_window_key_press_event(self, window, event):
        key = Gdk.keyval_name(event.keyval)

        if event.state & Gdk.ModifierType.CONTROL_MASK and key in ('Tab', 'ISO_Left_Tab'):
            atab = self.window.get_active_tab()
            docs = self.window.get_documents()
            tabs = []
            for doc in docs:
              tabs.append(Gedit.Tab.get_from_document(doc))
            
            tlen = len(tabs)
            i = 0
            tab = atab
            
            for tab in tabs:
                i += 1
                if tab == atab:
                    break
            
            if key == 'ISO_Left_Tab':
                i -= 2
            
            if i < 0:
                tab = tabs[tlen-1]
            elif i >= tlen:
                tab = tabs[0]
            else:
                tab = tabs[i]
            
            self.window.set_active_tab(tab)
            
            return True


########NEW FILE########
__FILENAME__ = whitespaceterminator
# coding: utf8
# Copyright © 2011 Kozea
# Licensed under a 3-clause BSD license.

"""
Strip trailing whitespace before saving.

"""

from gi.repository import GObject, Gedit


class WhiteSpaceTerminator(GObject.Object, Gedit.WindowActivatable):
    """Strip trailing whitespace before saving."""
    window = GObject.property(type=Gedit.Window)

    def do_activate(self):
        self.handlers = []
        handler = self.window.connect("tab-added", self.on_tab_added)
        self.handlers.append((self.window, handler))
        for document in self.window.get_documents():
            document.connect("save", self.on_document_save)
            self.handlers.append((document, handler))

    def on_tab_added(self, window, tab, data=None):
        handler = tab.get_document().connect("save", self.on_document_save)
        self.handlers.append((tab, handler))

    def on_document_save(self, document, location, encoding, compression,
                         flags, data=None):
        for i, text in enumerate(document.props.text.rstrip().splitlines()):
            strip_stop = document.get_iter_at_line(i)
            strip_stop.forward_to_line_end()
            strip_start = strip_stop.copy()
            strip_start.backward_chars(len(text) - len(text.rstrip()))
            document.delete(strip_start, strip_stop)
        document.delete(strip_start, document.get_end_iter())

    def do_deactivate(self):
        for obj, handler in self.handlers:
            obj.disconnect(handler)

########NEW FILE########
