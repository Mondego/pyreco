__FILENAME__ = FindInFiles
import gedit
import gtk
import os
import gconf
import subprocess

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
          
        search_text = self.search_form.get_text()
        check_ack = os.popen("which ack-grep")
        if (not self.case_sensitive):
          #not a case sensitive serach
          if len(check_ack.readlines()) == 0: 
            cmd=['grep', '-R', '-n', '-H', '-i', search_text, location]
            print "using grep. consider installing ack-grep"
          else:
            cmd=['ack-grep',search_text,location]
            print "you are using ack-grep with speed!"
        else:
          # a case sensitive search
          if len(check_ack.readlines()) == 0:
            cmd=['grep', '-R', '-n', '-H', search_text, location]
            print "using grep. consider installing ack-grep"
          else:
            cmd=['ack-grep', '-i', search_text,location]
            print "you are using ack-grep with speed!"

        output = subprocess.Popen(cmd, stdout=subprocess.PIPE)
        data = output.stdout.read()
        results = data.split('\n')
               
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

                # If we want to ignore comments, then we'll make sure it doesn't start with # or // or other common comment patterns. In the future it would be great to do this in context to the file type
                if (self.ignore_comments):
                    if (not string.startswith("#") and not string.startswith("<!--") and not string.startswith("/*") and not string.startswith("//")):
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
        self.ui_id = panel.add_item(self.results_view, "Find under File Browser", image)
        
    def remove_menu_item(self):
        panel = self.window.get_side_panel()
        
        panel.remove_item(self.results_view)

class FindInFilesPlugin(gedit.Plugin):
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

__version__ = '1.0.5'
__author__ = 'Kevin McGuinness'

import gedit
import gtk
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

class PairCompletionPlugin(gedit.Plugin):
  """Automatic pair character completion for gedit"""
  
  ViewHandlerName = 'pair_char_completion_handler'
 
  def __init__(self):
    gedit.Plugin.__init__(self)
    self.ctrl_enter_enabled = True
    self.language_id = 'plain'
    self.opening_parens = language_parens['default'][0]
    self.closing_parens = language_parens['default'][1]
 
  def activate(self, window):
    self.update_ui(window)
    
  def deactivate(self, window):
    for view in window.get_views():
      handler_id = getattr(view, self.ViewHandlerName, None)
      if handler_id is not None:
        view.disconnect(handler_id)
      setattr(view, self.ViewHandlerName, None)
    
  def update_ui(self, window):
    view = window.get_active_view()
    doc = window.get_active_document()
    if isinstance(view, gedit.View) and doc:
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
    
  def delete_both_parens(self, doc):
    doc.begin_user_action()
    start_iter = doc.get_iter_at_mark(doc.get_insert())
    end_iter = start_iter.copy()
    start_iter.backward_char()
    end_iter.forward_char()
    doc.delete(start_iter, end_iter)
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
      event.keyval == gtk.keysyms.Return and
      event.state & gtk.gdk.CONTROL_MASK)
  
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
  
  def should_delete_both_parens(self, doc, event):
    if event.keyval == gtk.keysyms.BackSpace:
      it = doc.get_iter_at_mark(doc.get_insert())
      current_char = it.get_char()
      if self.is_closing_paren(current_char):
        it.backward_char()
        previous_char = it.get_char()
        matching_paren = self.get_matching_opening_paren(current_char) 
        return previous_char == matching_paren
    return False
  
  def on_key_press(self, view, event, doc):
    handled = False
    self.update_language(doc)
    ch = to_char(event.keyval)
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
      if event.state & gtk.gdk.SHIFT_MASK:
        text_to_insert = self.get_stmt_terminator(doc) + text_to_insert
      self.move_to_end_of_line_and_insert(doc, text_to_insert)
      view.scroll_mark_onscreen(doc.get_insert())
      handled = True
    if not handled and event.keyval in (gtk.keysyms.Return, gtk.keysyms.KP_Enter):
      # Enter was just pressed
      char_under_cursor = self.get_char_under_cursor(doc)
      if (self.is_closing_paren(char_under_cursor) and
        self.would_balance_parens(doc, char_under_cursor)):
        # If the character under the cursor would balance parenthesis
        text_to_insert = NEWLINE_CHAR + self.get_current_line_indent(doc)
        handled = self.insert_two_lines(doc, text_to_insert)
    if not handled and self.should_delete_both_parens(doc, event):
      # Delete parenthesis in front of cursor when one behind is deleted
      handled = self.delete_both_parens(doc)
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
__FILENAME__ = config_dlg
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
import gettext
import ConfigParser
import os

class conf_dlg(gtk.Dialog):
    def __init__(self, parent):
        # Create config diaog window
        title = _("Reopen Tabs Plugin Configuration")
        buttons = (gtk.STOCK_CANCEL, gtk.RESPONSE_CANCEL, gtk.STOCK_OK, gtk.RESPONSE_OK)

        super(conf_dlg, self).__init__(title, parent, 0, buttons)
        
        # Create configuration items
        self._chk_save = gtk.CheckButton(_("Ask for saving on exit"))
        self._chk_save.connect("toggled", self._on_chk_save_toggled)
        self.vbox.pack_start(self._chk_save, True, True, 10)
        
        # Setup configuration file path
        self._conf_path = os.path.join(os.path.expanduser("~/.gnome2/gedit/plugins/"), "reopen-tabs/plugin.conf")
        
        # Check if configuration file does not exists
        if not os.path.exists(self._conf_path):
            # Create configuration file
            conf_file = file(self._conf_path, "wt")
            conf_file.close()
            
        # Create configuration dictionary
        self.read_config()
        
    def read_config(self): # Reads configuration from a file
        self._conf_file = file(self._conf_path, "r+")
        self._conf_dict = ConfigParser.ConfigParser()
        self._conf_dict.readfp(self._conf_file)
        
        self._conf_file.close()

        # Setup default configuration if needed
        if not self._conf_dict.has_section("common"):
            self._conf_dict.add_section("common")
            
        if not self._conf_dict.has_option("common", "save_prompt"):
            self._conf_dict.set("common", "save_prompt", "on")
                
        if not self._conf_dict.has_option("common", "active_document"):
            self._conf_dict.set("common", "active_document", "")
                
        if not self._conf_dict.has_section("documents"):
            self._conf_dict.add_section("documents")
                
    def write_config(self): # Saves configuration to a file
        self._conf_file = file(self._conf_path, "r+")
        self._conf_file.truncate(0)

        self._conf_dict.write(self._conf_file)
        
        self._conf_file.close()
    
    def get_config(self):
        return self._conf_dict
    
    def load_conf(self): # Loads configuration
        val = self._conf_dict.getboolean("common", "save_prompt")
        
        self._chk_save.set_active(val)
    
    def _on_chk_save_toggled(self, chk): # React on checkbox toggle        
        if chk.get_active() == True:
            val = "on"
        else:
            val = "off"
        
        self._conf_dict.set("common", "save_prompt", val)
        
# ex:ts=4:et:

########NEW FILE########
__FILENAME__ = exit_dlg
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
import ConfigParser
import os

class save_dlg(gtk.Dialog):
    def __init__(self, parent, config):
        # Create config diaog window
        title = _("Reopen Tabs Plugin")
        buttons = (gtk.STOCK_NO, gtk.RESPONSE_NO, gtk.STOCK_YES, gtk.RESPONSE_YES)

        super(save_dlg, self).__init__(title, parent, 0, buttons)
        
        # Create diaog items
        self._msg = gtk.Label(_("Restore opened tabs on next run?"))
        self.vbox.pack_start(self._msg, True, True, 10)
        
        self._chk_save = gtk.CheckButton(_("Don't ask again (always save)"))
        self._chk_save.connect("toggled", self._on_chk_save_toggled)
        self.vbox.pack_start(self._chk_save, True, True, 10)

        self.show_all()
        
        # Setup configuration dictionary
        self._config = config
    
    def _on_chk_save_toggled(self, chk): # Reacts on checkbox toggle        
        if chk.get_active() == True:
            val = "off"
        else:
            val = "on"
        
        self._config.set("common", "save_prompt", val)
        
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
import getopt
import config_dlg
import exit_dlg
import gettext

APP_NAME = "plugin"
LOC_PATH = os.path.join(os.path.expanduser("~/.gnome2/gedit/plugins/reopen-tabs/lang"))

gettext.find(APP_NAME, LOC_PATH)
gettext.install(APP_NAME, LOC_PATH, True)

RELOADER_STATE_READY        = "ready"
RELOADER_STATE_WAIT         = "wait"
RELOADER_STATE_RELOADING    = "reloading"
RELOADER_STATE_DONE         = "done"

class ReopenTabsPlugin(gedit.Plugin):
    def __init__(self):
        gedit.Plugin.__init__(self)
        
        self._config = None
        
        self._state = RELOADER_STATE_WAIT

    def activate(self, window):
        # Create configuration dialog
        self._dlg_conf = config_dlg.conf_dlg(None)
        self._dlg_conf.connect("response", self._on_dlg_conf_response)
        
        # Get configuration dictionary
        self._config = self._dlg_conf.get_config()
        
        window.connect("active-tab-changed", self._on_active_tab_changed)
        window.connect("active-tab-state-changed", self._on_active_tab_state_changed)

        # Register signal handler to ask a user to save tabs on exit
        window.connect("delete_event", self._on_destroy)
        
    def deactivate(self, window):
        pass
        
    def _on_active_tab_changed(self, window, tab):
        if self._state == RELOADER_STATE_WAIT:
            self._state = RELOADER_STATE_READY
            self._on_active_tab_state_changed(window)
        
    def _on_active_tab_state_changed(self, window):
        # Check if we are not reloading and did not finished yet
        if self._state == RELOADER_STATE_READY:
            # Get active tab
            tab = window.get_active_tab()
            
            # Check if we are ready to reload
            if tab and tab.get_state() == gedit.TAB_STATE_NORMAL:
                self._state = RELOADER_STATE_RELOADING

                self._reopen_tabs(window)

                self._state = RELOADER_STATE_DONE
        
    def update_ui(self, window):
        pass

    def create_configure_dialog(self): # Upadtes configuration dialog (executes by framework)
        # Update configuration dialog widgets
        self._dlg_conf.load_conf()
        self._dlg_conf.show_all()

        # Return configuration dialog to framework
        return self._dlg_conf

    def _on_dlg_conf_response(self, dlg_conf, res): # Handles configuration dialog response
        # Hide configuration dialog
        dlg_conf.hide()

        # Check if user pressed OK button
        if res == gtk.RESPONSE_OK:
            # Save configuration
            self._dlg_conf.write_config()
            
    def _on_destroy(self, widget, event): # Handles window destory (saves tabs if required)
        # Clear old document list
        self._config.remove_section("documents")

        self._docs = self._get_doc_list()
        
        # Check if there is anything to save
        if len(self._docs) > 0:
            # Check if we need ask a user to save tabs
            if self._config.getboolean("common", "save_prompt"):
                # Create and run prompt dialog
                dlg_save = exit_dlg.save_dlg(None, self._config)
                dlg_save.connect("response", self._on_dlg_save_response)
                dlg_save.run()
            else:
                self._save_tabs()
                
        self._dlg_conf.write_config()
        
    def _on_dlg_save_response(self, dlg, res): # Handles saving prompt response
        # Check if user pressed YES button
        if res == gtk.RESPONSE_YES:
            # Save opened tabs in configuration file
            self._save_tabs()
        
    def _get_doc_list(self):
        # Get document URI list
        app  = gedit.app_get_default()
        win  = app.get_active_window()
        docs = win.get_documents()
        
        # Return list of documents which having URI's
        return [d.get_uri() for d in docs if d.get_uri()]
        
    def _save_tabs(self): # Save opened tabs in configuration file
        self._config.add_section("documents")
        
        # Get active document
        app = gedit.app_get_default()
        win = app.get_active_window()
    
        doc = win.get_active_document()
        if doc:
            cur_uri = doc.get_uri()
        else:
            cur_uri = None
        
        doc = None
        
        # Create new document list
        n = 1
        for uri in self._docs:
            # Setup option name
            name = "document" + str(n).rjust(3).replace(" ", "0")
        
            # Check if current document is active
            if uri == cur_uri:
                doc = name

            self._config.set("documents", name, uri)
            n = n + 1

        # Remeber active document
        if doc:
            self._config.set("common", "active_document", doc)
        
    def _reopen_tabs(self, window):
        # Get list of open documents
        docs = window.get_documents()
        open_docs = [d.get_uri() for d in docs if d.get_uri()]
        
        # Get saved active document
        active = self._config.get("common", "active_document")
        self._active_tab = None
    
        # Get document list
        docs = self._config.options("documents")
        docs.sort()

        # Check if document list is not empty
        if len(docs) > 0:
            # Get active document
            doc = window.get_active_document()
            
            # Check if document is untitled (there is empty tab)
            tab = window.get_active_tab()
            
            if doc.is_untitled():
            	# Remember empty tab to close it later
            	self._empty_tab = tab
            else:
                # Remember active tab (in case if there is file in a command line)
            	self._empty_tab = None
                self._active_tab = tab
            
            # Process the rest documents
            for d in docs:
                # Get document uri
                uri = self._config.get("documents", d)
                
                # Check if document is not already opened
                if open_docs.count(uri) == 0:
                    # Create new tab
                    tab = window.create_tab_from_uri(uri, gedit.encoding_get_current(), 0, True, False)
            
                    # Check if document was active (and there is NOT file in command line)
                    if d == active and not self._active_tab:
                        self._active_tab = tab

        # Connect handler that switches saved active document tab
        if self._active_tab:
            self._active_tab.get_document().connect("loaded", self._on_doc_loaded)

    def _on_doc_loaded(self, doc, arg): # Switches to saved active document tab
        # Activate tab
        app = gedit.app_get_default()
        win = app.get_active_window()
        win.set_active_tab(self._active_tab)
        
        # Close empty tab if any
        if self._empty_tab:
            win.close_tab(self._empty_tab)
        
# ex:ts=4:et:

########NEW FILE########
__FILENAME__ = tabs_extend
# -*- coding: utf-8 -*-
#
# Copyright © 2008, Éverton Ribeiro <nuxlli@gmail.com>
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

import gtk
import gedit

# Find widget by name
def lookup_widget(base, widget_name):
  widgets = []

  for widget in base.get_children():
    if widget.get_name() == widget_name:
      widgets.append(widget)
    if isinstance(widget, gtk.Container):
      widgets += lookup_widget(widget, widget_name)

  return widgets

# UI Manager XML
ACTIONS_UI = """
<ui>
  <menubar name="MenuBar">
    <menu name="FileMenu" action="File">
      <placeholder name="FileOps_2">
        <menuitem name="UndoClose" action="UndoClose"/>
      </placeholder>
    </menu>
  </menubar>

  <popup name="NotebookPopup" action="NotebookPopupAction">
    <placeholder name="NotebookPupupOps_1">
      <menuitem name="UndoClose" action="UndoClose"/>
      <menuitem name="CloseAll" action="CloseAll"/>
      <menuitem name="CloseOthers" action="CloseOthers"/>
    </placeholder>
  </popup>
</ui>
"""

class TabsExtendWindowHelper:
  handler_ids = []
  tabs_closed = []

  def __init__(self, plugin, window):
    """Activate plugin."""
    self.window   = window
    self.notebook = self.get_notebook()

    self.add_all()
    self.handler_ids.append((self.notebook, self.notebook.connect("tab_added", self.tab_added_handler)))
    self.handler_ids.append((self.notebook, self.notebook.connect("tab_removed", self.tab_removed_handler)))
    self.add_actions()

  def add_actions(self):
    undoclose = (
      'UndoClose', # name
      'gtk-undo', # icon stock id
      'Undo close', # label
      '<Ctrl><Shift>T',# accelerator
      'Open the folder containing the current document', # tooltip
      self.on_undo_close # callback
    )

    closeall = (
      'CloseAll', # name
      'gtk-close', # icon stock id
      'Close all', # label
      '<Ctrl><Shift>W',# accelerator
      'Open the folder containing the current document', # tooltip
      self.on_close_all # callback
    )

    closeothers = (
      'CloseOthers', # name
      'gtk-close', # icon stock id
      'Close others', # label
      '<Ctrl><Shift>O',# accelerator
      'Open the folder containing the current document', # tooltip
      self.on_close_outher # callback
    )

    action_group = gtk.ActionGroup(self.__class__.__name__)
    action_group.add_actions([undoclose, closeall, closeothers])

    ui_manager = self.window.get_ui_manager()
    ui_manager.insert_action_group(action_group, 0)
    ui_id = ui_manager.add_ui_from_string(ACTIONS_UI)

    data = { 'action_group': action_group, 'ui_id': ui_id }
    self.window.set_data(self.__class__.__name__, data)
    self.update_ui()

  def deactivate(self):
    """Deactivate plugin."""
    # disconnect
    for (handler_id, widget) in self.handler_ids:
      widget.disconnect(handler_id)

    data = self.window.get_data(self.__class__.__name__)
    ui_manager = self.window.get_ui_manager()
    ui_manager.remove_ui(data['ui_id'])
    ui_manager.remove_action_group(data['action_group'])
    ui_manager.ensure_update()
    self.window.set_data(self.__class__.__name__, None)

    self.window   = None
    self.notebook = None
    self.handles  = None

  def update_ui(self):
    """Update the sensitivities of actions."""
    pass
    windowdata = self.window.get_data(self.__class__.__name__)
    windowdata['action_group'].get_action('UndoClose').set_sensitive(len(self.tabs_closed) > 0)
    windowdata['action_group'].get_action('CloseAll').set_sensitive(self.notebook.get_n_pages() > 0)
    windowdata['action_group'].get_action('CloseOthers').set_sensitive(self.notebook.get_n_pages() > 1)

  def get_notebook(self):
    return lookup_widget(self.window, 'GeditNotebook')[0]

  def add_all(self):
    for x in range(self.notebook.get_n_pages()):
      tab = self.notebook.get_nth_page(x)
      self.add_middle_click_in_tab(tab)

  def add_middle_click_in_tab(self, tab):
    eventbox   = self.notebook.get_tab_label(tab).get_children()[0]
    handler_id = eventbox.connect("button-press-event", self.middle_click_handler, tab)
    self.handler_ids.append([eventbox, handler_id])

  def middle_click_handler(self, widget, event, tab):
    if event.type == gtk.gdk.BUTTON_PRESS and event.button == 2:
      if self.notebook.get_n_pages():
        self.notebook.prev_page()
      self.window.close_tab(tab)

  def tab_added_handler(self, widget, tab):
    self.add_middle_click_in_tab(tab)

  def tab_removed_handler(self, widget, tab):
    self.save_tab_to_undo(tab)
    self.update_ui()
    for (handler_id, widget) in self.handler_ids:
      if widget == tab:
        widget.disconnect(handler_id)
        self.handler_ids.remove(handler_id)
        break

  def get_current_line(self, document):
    """ Get current line for documento """
    return document.get_iter_at_mark(document.get_insert()).get_line() + 1

  # TODO: Save position tab
  def save_tab_to_undo(self, tab):
    """ Save close tabs """

    document = tab.get_document()
    if document.get_uri() != None:
      self.tabs_closed.append((
        document.get_uri(),
        self.get_current_line(document)
      ))

  def on_undo_close(self, action):
    if len(self.tabs_closed) > 0:
      uri, line = tab = self.tabs_closed[-1:][0]

      if uri == None:
        self.window.create_tab(True)
      else:
        self.window.create_tab_from_uri(uri, None, line, True, True)

      self.tabs_closed.remove(tab)
    self.update_ui()

  def on_close_all(self, action):
    if self.notebook.get_n_pages() > 0:
      self.window.close_all_tabs()
      self.update_ui()

  def on_close_outher(self, action):
    if self.notebook.get_n_pages() > 1:
      dont_close = self.window.get_active_tab()

      tabs = []
      for x in range(self.notebook.get_n_pages()):
        tab = self.notebook.get_nth_page(x)
        if tab != dont_close:
          tabs.append(tab)

      tabs.reverse()
      for tab in tabs:
        self.window.close_tab(tab)

      self.update_ui()

class TabsExtendPlugin(gedit.Plugin):
    def __init__(self):
        gedit.Plugin.__init__(self)
        self._instances = {}

    def activate(self, window):
        self._instances[window] = TabsExtendWindowHelper(self, window)

    def deactivate(self, window):
        self._instances[window].deactivate()
        del self._instances[window]

    def update_ui(self, window):
        self._instances[window].update_ui()

########NEW FILE########
__FILENAME__ = textmap
# Copyright 2011, Dan Gindikin <dgindikin@gmail.com>
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

import gtk
import time
import gobject
import gedit
import sys
import math
import cairo
import re
import copy
import platform

version = "0.2 beta"

# ------------------------------------------------------------------------------
# These regular expressions are applied in sequence ot each line, to determine
# whether it is a section start or not

SectionREs = (
  re.compile('def\s*(\w+)\s*\('),                          # python method
  re.compile('class\s*(\w+)\s*'),                          # python/java class
  
  re.compile('cdef\s*class\s*(\w+)\s*[(:]'),               # cython class
  re.compile('cdef\s*(?:[\w\.]*?\**\s*)?(\w+)\s*\('),      # cython method
  
  re.compile('^(\w*)\s*\('),                               # C method
  re.compile('^\w+[\w\s\*]*?(\w*)\s*\('),                  # C method
  
  re.compile('^function\s*(\w+)\s*\('),                    # javascript method
  
  re.compile('\w+[\w\s]*?class (\w*)'),                    # java class
)

SubsectionREs = (
  re.compile('\s+def\s*(\w+)\s*\('),                       # python class method
  
  re.compile('\s+cdef\s*(?:[\w\.]*?\**\s*)?(\w+)\s*\('),   # cython class method
  
  re.compile('\s+(?:public|static|private|final)[\w\s]*?(\w+)\s*\('), # java method
)

# ------------------------------------------------------------------------------

class struct:pass

class TimeRec:
  def __init__(M):
    M.tot = M.N = M.childtot = M.heretot = 0
    M.start_ = None
    
class Timer:
  'L == label'
  def __init__(M):
    M.dat = {}
    M.stack = []
  def push(M,L):
    assert L not in M.stack,(L,M.stack)
    M.stack.append(L)
    tmrec = M.dat.setdefault(L,TimeRec())
    tmrec.start_=time.time()
  def pop(M,L):
    assert M.stack[-1]==L,(L,M.stack)
    M.stack.pop()
    tmrec = M.dat[L]
    dur = time.time()-tmrec.start_
    tmrec.start_ = None
    tmrec.tot += dur
    tmrec.N += 1
    #for parent in M.stack:
    #  M.dat[parent].childtot += dur
    if M.stack <> []:
      M.dat[M.stack[-1]].childtot += dur
  def print_(M):
    for tmrec in M.dat.values():
      tmrec.heretot = tmrec.tot-tmrec.childtot
    R = sorted(M.dat.items(),lambda x,y:-cmp(x[1].heretot,y[1].heretot))
    print '%7s %7s %5s' % ('Tm Here', 'Tm Avg', 'Count')
    for L,tmrec in R:
      print '%7s %7s %5d %s' % ('%.3f'%tmrec.heretot, '%.3f'%(tmrec.heretot/float(tmrec.N)), tmrec.N, L)
    print
      
#TIMER = Timer()
TIMER = None
   
def indent(s):
  x = 0
  for c in s:
    if c == ' ':
      x += 1
    elif c == '\t':
      x += 8
    else:
      break
  return x
  
def probj(ob,*substrs):
  meths = dir(ob)
  meths.sort()
  print ob,type(ob)
  for m in meths:
    doprint=True
    if substrs:
      doprint=False
      for s in substrs:
        if s in m:
          doprint=True
          break
    if doprint:
      print '%40s'%m
      
def match_RE_list(str, REs):
  for r in REs:
    m = r.match(str)
    if m:
      return m.groups()[0]
  return None

def document_lines(document):
  if not document:
    return None
  #print 'document_lines',document
  STR = document.get_property('text')
  lines = STR.split('\n')
  ans = []
  for i,each in enumerate(lines):
    x = struct()
    x.i = i
    x.len = len(each)
    x.indent = indent(each)
    x.raw = each
    x.section = match_RE_list(x.raw,SectionREs)
    x.subsection = None
    x.search_match = False
    if not x.section:
      x.subsection = match_RE_list(x.raw,SubsectionREs)
    if x.section or x.subsection:
      match = Split_Off_Indent_Pattern.match(x.raw)
      x.indentSTR = None
      x.justextSTR = None
      if match:
        groups = match.groups()
        if len(groups) == 2:
          x.indentSTR, x.justextSTR = groups
    ans.append(x)
  return ans
  
def lines_add_section_len(lines):
  line_prevsection = None
  counter = 0
  for i, line in enumerate(lines):
    if line.section:
      if line_prevsection:
        line_prevsection.section_len = counter
      line_prevsection = line
      counter = 0
    counter += 1
  if line_prevsection:
    line_prevsection.section_len = counter
  return lines

def lines_mark_changed_sections(lines):
  sec = None
  subsec = None
  for line in lines:
    if line.section:
      line.sectionchanged = False
      sec = line
      subsec = None
    if line.subsection:
      line.subsectionchanged = False
      subsec = line
    if line.changed:
      if sec is not None:
        sec.sectionchanged = True
      if subsec is not None:
        subsec.subsectionchanged = True
  return lines
  
BUG_MASK = 0

BUG_CAIRO_MAC_FONT_REF  = 1
BUG_CAIRO_TEXT_EXTENTS  = 2
BUG_DOC_GET_SEARCH_TEXT = 4

if platform.system() == 'Darwin':
  BUG_MASK |= BUG_CAIRO_MAC_FONT_REF  # extra decref causes aborts, use less font ops

major,minor,patch = gedit.version
if major<=2 and minor<28:
  BUG_MASK |= BUG_CAIRO_TEXT_EXTENTS  # some reference problem
  BUG_MASK |= BUG_DOC_GET_SEARCH_TEXT # missing INCREF then
  
def text_extents(str,cr):
  "code around bug in older cairo"
  
  if BUG_MASK & BUG_CAIRO_TEXT_EXTENTS:  
    if str:
      x, y = cr.get_current_point()
      cr.move_to(0,-5)
      cr.show_text(str)
      nx,ny = cr.get_current_point()
      cr.move_to(x,y)
    else:
      nx = 0
      ny = 0

    #print repr(str),x,nx,y,ny
    ascent, descent, height, max_x_advance, max_y_advance = cr.font_extents()
    
    return nx, height
  
  else:
  
    x_bearing, y_bearing, width, height, x_advance, y_advance = cr.text_extents(str)
    return width, height
    
def pr_text_extents(s,cr):
  x_bearing, y_bearing, width, height, x_advance, y_advance = cr.text_extents(s)
  print repr(s),':','x_bearing',x_bearing,'y_bearing',y_bearing,'width',width,'height',height,'x_advance',x_advance,'y_advance',y_advance
  
def show_section_label(str, fg, bg, cr):
  tw,th = text_extents(str,cr)
  x,y = cr.get_current_point()
  cr.set_source_rgba(bg[0],bg[1],bg[2],.75)
  cr.rectangle(x,y-th+3,tw,th)
  cr.fill()
  cr.move_to(x,y)
  cr.set_source_rgb(*fg)
  cr.show_text(str)
    
def fit_text(str, w, h, fg, bg, cr):
  moved_down = False
  originalx,_ = cr.get_current_point()
  sofarH = 0
  rn = []
  if dark(*bg):
    bg_rect_C = lighten(.1,*bg)
  else:
    bg_rect_C = darken(.1,*bg)
    
  while 1:
    # find the next chunk of the string that fits
    for i in range(len(str)):
      tw, th = text_extents(str[:i],cr)
      if tw > w:
        break
    disp = str[:i+1]
    str = str[i+1:]
    tw, th = text_extents(disp,cr)
    
    sofarH += th
    if sofarH > h:
      return rn
    if not moved_down:
      moved_down = True
      cr.rel_move_to(0, th)
      
    # bg rectangle
    x,y = cr.get_current_point()
    #cr.set_source_rgba(46/256.,52/256.,54/256.,.75)
    cr.set_source_rgba(bg_rect_C[0],bg_rect_C[1],bg_rect_C[2],.75)
    if str:
      cr.rectangle(x,y-th+2,tw,th+3)
    else: # last line does not need a very big rectangle
      cr.rectangle(x,y-th+2,tw,th)    
    cr.fill()
    cr.move_to(x,y)
    
    # actually display
    cr.set_source_rgb(*fg)
    cr.show_text(disp)
    
    # remember
    rec = struct()
    rec.x = x
    rec.y = y
    rec.th = th
    rec.tw = tw
    rn.append(rec)
    
    cr.rel_move_to(0,th+3)
    x,y = cr.get_current_point()
    cr.move_to(originalx,y)
    
    if not str:
      break
  return rn
      
def downsample_lines(lines, h, min_scale, max_scale):
  n = len(lines)
  
  # pick scale
  for scale in range(max_scale,min_scale-1,-1): 
    maxlines_ = h/(.85*scale)
    if n < 2*maxlines_:
      break
      
  if n <= maxlines_:
    downsampled = False
    return lines, scale, downsampled
    
  # need to downsample
  lines[0].score = sys.maxint # keep the first line
  for i in range(1, len(lines)):
    if lines[i].section:  # keep sections
      lines[i].score = sys.maxint
    elif lines[i].subsection:
      lines[i].score = sys.maxint/2
    elif lines[i].changed or lines[i].search_match:
      lines[i].score = sys.maxint/2
    else:
      if 0: # get rid of lines that are very different
        lines[i].score = abs(lines[i].indent-lines[i-1].indent) \
                         + abs(len(lines[i].raw)-len(lines[i-1].raw))
      if 1: # get rid of lines randomly
        lines[i].score = hash(lines[i].raw)
        if lines[i].score > sys.maxint/2:
          lines[i].score -= sys.maxint/2
                     
  scoresorted = sorted(lines, lambda x,y: cmp(x.score,y.score))
  erasures_ = int(math.ceil(n - maxlines_))
  #print 'erasures_',erasures_
  scoresorted[0:erasures_]=[]
    
  downsampled = True
  
  return sorted(scoresorted, lambda x,y:cmp(x.i,y.i)), scale, downsampled
      
def visible_lines_top_bottom(geditwin):
  view = geditwin.get_active_view()
  rect = view.get_visible_rect()
  topiter = view.get_line_at_y(rect.y)[0]
  botiter = view.get_line_at_y(rect.y+rect.height)[0]
  return topiter.get_line(), botiter.get_line()
      
def dark(r,g,b):
  "return whether the color is light or dark"
  if r+g+b < 1.5:
    return True
  else:
    return False
    
def darken(fraction,r,g,b):
  return r-fraction*r,g-fraction*g,b-fraction*b
  
def lighten(fraction,r,g,b):
  return r+(1-r)*fraction,g+(1-g)*fraction,b+(1-b)*fraction
  
def scrollbar(lines,topI,botI,w,h,bg,cr,scrollbarW=10):
  "top and bot a passed as line indices"
  # figure out location
  topY = None
  botY = None
  for line in lines:
    if not topY:
      if line.i >= topI:
        topY = line.y
    if not botY:
      if line.i >= botI:
        botY = line.y
  
  if topY is None:
    topY = 0
  if botY is None:
    botY = lines[-1].y

  if 0: # bg rectangle     
    cr.set_source_rgba(.1,.1,.1,.35)
    cr.rectangle(w-scrollbarW,0,scrollbarW,topY)
    cr.fill()
    cr.rectangle(w-scrollbarW,botY,scrollbarW,h-botY)
    cr.fill()
    
  if 0: # scheme 1
    cr.set_line_width(1)
    #cr.set_source_rgb(0,0,0)
    #cr.set_source_rgb(1,1,1)
    cr.set_source_rgb(0xd3/256.,0xd7/256.,0xcf/256.)
    if 0: # big down line
      cr.set_source_rgb(0xd3/256.,0xd7/256.,0xcf/256.)
      cr.move_to(w-scrollbarW/2.,0)
      cr.line_to(w-scrollbarW/2.,topY)
      cr.stroke()
      cr.move_to(w-scrollbarW/2.,botY)
      cr.line_to(w-scrollbarW/2.,h)
      cr.stroke()
    if 0:
      cr.rectangle(w-scrollbarW,topY,scrollbarW-1,botY-topY)
      cr.stroke()
    if 1: # bottom lines
      #cr.set_line_width(2)
      #cr.move_to(w-scrollbarW,topY)
      cr.move_to(0,topY)
      cr.line_to(w,topY)
      cr.stroke()
      cr.move_to(0,botY)
      cr.line_to(w,botY)
      cr.stroke()
    if 0: # rect
      cr.set_source_rgba(.5,.5,.5,.1)
      #cr.set_source_rgba(.1,.1,.1,.35)
      #cr.rectangle(w-scrollbarW,topY,scrollbarW,botY-topY)
      cr.rectangle(0,topY,w,botY-topY)
      cr.fill()

  if 0: # scheme 2
    cr.set_line_width(3)
    cr.set_source_rgb(0xd3/256.,0xd7/256.,0xcf/256.)
    if 1: # bottom lines
      cr.move_to(0,topY)
      cr.line_to(w,topY)
      cr.stroke()
      cr.move_to(0,botY)
      cr.line_to(w,botY)
      cr.stroke()
    if 1: # side lines
      cr.set_line_width(2)
      len = (botY-topY)/8
      margin = 1
      if 0: # left
        cr.move_to(margin,topY)
        cr.line_to(margin,topY+len)
        cr.stroke()
        cr.move_to(margin,botY-len)
        cr.line_to(margin,botY)
        cr.stroke()
      if 1: # right
        cr.move_to(w-margin,topY)
        cr.line_to(w-margin,topY+len)
        cr.stroke()
        cr.move_to(w-margin,botY-len)
        cr.line_to(w-margin,botY)
        cr.stroke()
    if 0: # center
      len = (botY-topY)/5
      cx = w/2
      cy = topY+(botY-topY)/2
      if 1: # vert
        for x in (cx,):#(cx-len/2,cx,cx+len/2):
          cr.move_to(x,cy-len/2)
          cr.line_to(x,cy+len/2)
          cr.stroke()
      if 0: # horiz
        cr.move_to(cx-len/2,cy)
        cr.line_to(cx+len/2,cy)
        cr.stroke()
    
  if 0: # view indicator  
    cr.set_source_rgba(.5,.5,.5,.5)
    #cr.set_source_rgba(.1,.1,.1,.35)
    cr.rectangle(w-scrollbarW,topY,scrollbarW,botY-topY)
    cr.fill()
    cr.rectangle(w-scrollbarW,topY,scrollbarW-1,botY-topY)
    cr.set_line_width(.5)
    cr.set_source_rgb(1,1,1)
    #cr.set_source_rgb(0,0,0)
    cr.stroke()
  
  if 0: # lines
    cr.set_source_rgb(1,1,1)
    cr.move_to(w,0)
    cr.line_to(w-scrollbarW,topY)
    cr.line_to(w-scrollbarW,botY)
    cr.line_to(w,h)
    cr.stroke()
    
  if 0: # scheme 3
  
    if 1: # black lines
      cr.set_line_width(2)
      cr.set_source_rgb(0,0,0)
      cr.move_to(0,topY)
      cr.line_to(w,topY)
      cr.stroke()
      cr.move_to(0,botY)
      cr.line_to(w,botY)
      cr.stroke() 
      
    if 1: # white lines
      cr.set_line_width(2)
      cr.set_dash([1,2])
      cr.set_source_rgb(1,1,1)
      cr.move_to(0,topY)
      cr.line_to(w,topY)
      cr.stroke()
      cr.move_to(0,botY)
      cr.line_to(w,botY)
      cr.stroke()   
  
  if 0: # scheme 4
    pat = cairo.LinearGradient(0,topY-10,0,topY)
    pat.add_color_stop_rgba(0, 1, 1, 1,1)
    pat.add_color_stop_rgba(1, .2,.2,.2,1)
    pat.add_color_stop_rgba(2, 0, 0, 0,1)
    cr.rectangle(0,topY-10,w,10)
    cr.set_source(pat)
    cr.fill()
    
  if 0: # triangle right
    # triangle
    size=12
    midY = topY+(botY-topY)/2
    cr.set_line_width(2)
    cr.set_source_rgb(1,1,1)
    cr.move_to(w-size-1,midY)
    cr.line_to(w-1,midY-size/2)
    #cr.stroke_preserve()
    cr.line_to(w-1,midY+size/2)
    #cr.stroke_preserve()
    cr.line_to(w-size-1,midY)
    cr.fill()
    # line
    cr.move_to(w-2,topY+2)
    cr.line_to(w-2,botY-2)
    cr.stroke()
    
  if dark(*bg):
    color = (1,1,1)
  else:
    color = (0,0,0)
    
  if 0: # triangle left
    # triangle
    size=12
    midY = topY+(botY-topY)/2
    cr.set_line_width(2)
    cr.set_source_rgb(*color)
    cr.move_to(size+1,midY)
    cr.line_to(1,midY-size/2)
    #cr.stroke_preserve()
    cr.line_to(1,midY+size/2)
    #cr.stroke_preserve()
    cr.line_to(size+1,midY)
    cr.fill()
    # line
    #cr.move_to(2,topY+2)
    #cr.line_to(2,botY-2)
    #cr.stroke()
    
  if 1: # dashed lines
    cr.set_line_width(2)
    cr.set_source_rgb(*color)
    cr.set_dash([8,8])
    #cr.rectangle(2,topY,w-4,botY-topY)
    cr.move_to(4,topY); cr.line_to(w,topY)
    cr.stroke()
    cr.move_to(4,botY); cr.line_to(w,botY)
    cr.stroke()
        
def queue_refresh(textmapview):
  try:
    win = textmapview.darea.get_window()
  except AttributeError:
    win = textmapview.darea.window
  if win:
    w,h = win.get_size()
    textmapview.darea.queue_draw_area(0,0,w,h)
    
def str2rgb(s):
  assert s.startswith('#') and len(s)==7,('not a color string',s)
  r = int(s[1:3],16)/256.
  g = int(s[3:5],16)/256.
  b = int(s[5:7],16)/256.
  return r,g,b
  
def init_original_lines_info(doc,lines):
  rn = []
  # now we insert marks at the end of every line
  iter = doc.get_start_iter()
  n = 0
  while 1:
    if n>=len(lines):
      break
    more_left = iter.forward_line()
    rec = struct()
    lines[n].mark = doc.create_mark(None,iter,False) 
    n+=1
    if not more_left:
      break
  assert n>=len(lines)-1,(n,len(lines),'something off with our iterator logic')
  if n==len(lines)-1:
    lines[-1].mark=doc.create_mark(None,doc.get_end_iter(),False)
  return lines
  
def mark_changed_lines(doc,original,current):
  'unfortunate choice of name, has nothing to do with GtkTextBuffer marks'

  # presume all current lines are changed
  for line in current:
    line.changed = True
  
  # mark any original lines we find as unchanged
  start = doc.get_start_iter()
  c=0
  for oline in original:
    end = doc.get_iter_at_mark(oline.mark)
    slice = doc.get_slice(start,end)
    # see if the first line between the marks is the original line
    if slice.split('\n',1)[0] == oline.raw:
      current[c].changed = False
    # forward through all the slice lines
    c += slice.count('\n')

    start = end

  return current
      
def lines_mark_search_matches(lines,docrec):
  for line in lines:
    if docrec.search_text and docrec.search_text in line.raw:
      line.search_match = True
    else:
      line.search_match = False
  return lines
  
Split_Off_Indent_Pattern = re.compile('(\s*)(.*)$')
      
class TextmapView(gtk.VBox):
  def __init__(me, geditwin):
    gtk.VBox.__init__(me)
    
    me.geditwin = geditwin
    
    darea = gtk.DrawingArea()
    darea.connect("expose-event", me.expose)
    
    darea.add_events(gtk.gdk.BUTTON_PRESS_MASK)
    darea.connect("button-press-event", me.button_press)
    darea.connect("scroll-event", me.on_darea_scroll_event)
    darea.add_events(gtk.gdk.ENTER_NOTIFY_MASK)
    darea.connect("enter-notify-event", me.on_darea_enter_notify_event)
    darea.add_events(gtk.gdk.LEAVE_NOTIFY_MASK)
    darea.connect("leave-notify-event", me.on_darea_leave_notify_event)
    darea.add_events(gtk.gdk.POINTER_MOTION_MASK)
    darea.connect("motion-notify-event", me.on_darea_motion_notify_event)
    
    
    me.pack_start(darea, True, True)
    
    me.darea = darea
    #probj(me.darea)

    me.connected = {}
    me.draw_scrollbar_only = False
    me.draw_sections = False
    me.topL = None
    me.surface_textmap = None
    
    me.line_count = 0
    
    me.doc_attached_data = {}
    
    me.show_all()
    
    # need this bc of a cairo bug, keep references to all our font faces
    me.font_face_keepalive = None
    
     #'''
     #   gtk.gdk.SCROLL_UP, 
     #  gtk.gdk.SCROLL_DOWN, 
     #  gtk.gdk.SCROLL_LEFT, 
     #  gtk.gdk.SCROLL_RIGHT
   #
     #Example:
   #
     #  def on_button_scroll_event(button, event):
     #    if event.direction == gtk.gdk.SCROLL_UP:
     #       print "You scrolled up"
     #       
     #event = gtk.gdk.Event(gtk.gdk.EXPOSE)
     #
     #      def motion_notify(ruler, event):
     #          return ruler.emit("motion_notify_event", event)
     #      self.area.connect_object("motion_notify_event", motion_notify,
     #                               self.hruler)
     #      self.area.connect_object("motion_notify_event", motion_notify,
     #                               self.vruler)
     #'''
  
  def on_darea_motion_notify_event(me, widget, event):
    #probj(event)
    #print event.type
    if event.state & gtk.gdk.BUTTON1_MASK:
      me.scroll_from_y_mouse_pos(event.y)
      
  def on_darea_enter_notify_event(me, widget, event):
    if event.mode.value_name == 'GDK_CROSSING_GTK_UNGRAB':
      return
    #print 'in here enter'
    me.draw_sections = True
    queue_refresh(me)
    
  def on_darea_leave_notify_event(me, widget, event):
    #print 'in here leaving'
    me.draw_sections = False
    queue_refresh(me)
    
  def on_darea_scroll_event(me, widget, event):
    pass
    #print 'XXX on_darea_scroll_event'
    
    # this scheme does not work
    # somehow pass this on, scroll the document/view
    #print type(widget),widget,type(event),event
    #probj(event)
    #view = me.geditwin.get_active_view()
    #if not view:
    #  return
    #return view.emit('scroll-event',event)

    # the following crashes
    #pagesize = 12
    #topI,botI = visible_lines_top_bottom(me.geditwin)
    #if event.direction == gtk.gdk.SCROLL_UP:
    #  newI = topI - pagesize
    #elif event.direction == gtk.gdk.SCROLL_DOWN:
    #  newI = botI + pagesize
    #else:
    #  return
    #  
    #view = me.geditwin.get_active_view()
    #doc  = me.geditwin.get_active_tab().get_document()
    #view.scroll_to_iter(doc.get_iter_at_line_index(newI,0),0,False,0,0)
    #
    #queue_refresh(me)
    
  def on_doc_cursor_moved(me, doc):
    #new_line_count = doc.get_line_count()
    #print 'new_line_count',new_line_count
    topL = visible_lines_top_bottom(me.geditwin)[0]
    if topL <> me.topL:
      queue_refresh(me)
      me.draw_scrollbar_only = True
    
  def on_insert_text(me, doc, piter, text, len):
    pass
    #if len < 20 and '\n' in text:
    #  print 'piter',piter,'text',repr(text),'len',len
    
  def scroll_from_y_mouse_pos(me,y):
    for line in me.lines:
      if line.y > y:
        break
    #print line.i, repr(line.raw)
    view = me.geditwin.get_active_view()
    doc = me.geditwin.get_active_tab().get_document()
    
    #doc.place_cursor(doc.get_iter_at_line_index(line.i,0))
    #view.scroll_to_cursor()
    #print view
    
    view.scroll_to_iter(doc.get_iter_at_line_index(line.i,0),0,True,0,.5)
    
    queue_refresh(me)
        
  def button_press(me, widget, event):
    me.scroll_from_y_mouse_pos(event.y)
    
  def on_scroll_finished(me):
    #print 'in here',me.last_scroll_time,time.time()-me.last_scroll_time
    if time.time()-me.last_scroll_time > .47:
      if me.draw_sections:
        me.draw_sections = False
        me.draw_scrollbar_only = False
        queue_refresh(me)
    return False
    
  def on_scroll_event(me,view,event):
    me.last_scroll_time = time.time()
    if me.draw_sections: # we are in the middle of scrolling
      me.draw_scrollbar_only = True
    else:
      me.draw_sections = True # for the first scroll, turn on section names
    gobject.timeout_add(500,me.on_scroll_finished) # this will fade out sections
    queue_refresh(me)
    
  def on_search_highlight_updated(me,doc,t,u):
    #print 'on_search_highlight_updated:',repr(doc.get_search_text())
    docrec = me.doc_attached_data[id(doc)]
    s = doc.get_search_text()[0]
    if s <> docrec.search_text:
      docrec.search_text = s
      queue_refresh(me)    
    
  def test_event(me, ob, event):
    print 'here',ob
    
  def save_refs_to_all_font_faces(me, cr, *scales):
    me.font_face_keepalive = []
    for each in scales:
      cr.set_font_size(each)
      me.font_face_keepalive.append(cr.get_font_face())
    
  def expose(me, widget, event):
    doc = me.geditwin.get_active_tab().get_document()
    if not doc:   # nothing open yet
      return
    
    if id(doc) not in me.connected:
      me.connected[id(doc)] = True
      doc.connect("cursor-moved", me.on_doc_cursor_moved)
      doc.connect("insert-text", me.on_insert_text)
      doc.connect("search-highlight-updated", me.on_search_highlight_updated)
      
    view = me.geditwin.get_active_view()
    if not view:
      return
    
    if TIMER: TIMER.push('expose')
    
    if id(view) not in me.connected:
      me.connected[id(view)] = True
      view.connect("scroll-event", me.on_scroll_event)
      #view.connect("start-interactive-goto-line", me.test_event)
      #view.connect("start-interactive-search", me.test_event)
      #view.connect("reset-searched-text", me.test_event)
      
    bg = (0,0,0)
    fg = (1,1,1)
    try:
      style = doc.get_style_scheme().get_style('text')
      if style is None: # there is a style scheme, but it does not specify default
        bg = (1,1,1)
        fg = (0,0,0)
      else:
        fg,bg = map(str2rgb, style.get_properties('foreground','background'))  
    except Exception,e:
      pass  # probably an older version of gedit, no style schemes yet
    
    changeCLR = (1,0,1)
    
    #search_match_style = None
    #try:
    #  search_match_style = doc.get_style_scheme().get_style('search-match')
    #except:
    #  pass
    #if search_match_style is None:
    #  searchFG = fg
    #  searchBG = (0,1,0)
    #else:
    #  searchFG,searchBG = map(str2rgb, style.get_properties('foreground','background'))
    searchFG = fg
    searchBG = (0,1,0)
      
    
    #print doc
       
    try:
      win = widget.get_window()
    except AttributeError:
      win = widget.window
    w,h = map(float,win.get_size())
    cr = widget.window.cairo_create()
    
    #probj(cr,'rgb')
    
    # Are we drawing everything, or just the scrollbar?
    fontfamily = 'sans-serif'
    cr.select_font_face('monospace', cairo.FONT_SLANT_NORMAL, cairo.FONT_WEIGHT_NORMAL)
            
    if me.surface_textmap is None or not me.draw_scrollbar_only:
    
      if TIMER: TIMER.push('document_lines')

      lines = document_lines(doc)
      
      if TIMER: TIMER.pop('document_lines')
      
      if TIMER: TIMER.push('draw textmap')
      
      if id(doc) not in me.doc_attached_data:
        docrec = struct()
        me.doc_attached_data[id(doc)] = docrec
        docrec.original_lines_info = None # we skip the first one, its empty
        docrec.search_text = None
        for l in lines:
          l.changed = False
      else:
        docrec = me.doc_attached_data[id(doc)]
        if docrec.original_lines_info == None:
          docrec.original_lines_info = init_original_lines_info(doc,lines)
        lines = mark_changed_lines(doc, docrec.original_lines_info, lines)
        
      if BUG_MASK & BUG_DOC_GET_SEARCH_TEXT:
        pass
      else:
        docrec.search_text = doc.get_search_text()[0]
        lines = lines_mark_search_matches(lines,docrec)
     
      cr.push_group()
      
      # bg
      if 1:
        #cr.set_source_rgb(46/256.,52/256.,54/256.)
        cr.set_source_rgb(*bg)
        cr.move_to(0,0)
        cr.rectangle(0,0,w,h)
        cr.fill()
        cr.move_to(0,0)
      
      if not lines:
        return
        
      # translate everthing in
      margin = 3
      cr.translate(margin,0)
      w -= margin # an d here
            
      if TIMER: TIMER.push('downsample')
      max_scale = 3
      lines, scale, downsampled = downsample_lines(lines, h, 2, max_scale)
      if TIMER: TIMER.pop('downsample')
      
      smooshed = False
      if downsampled or scale < max_scale:
        smooshed = True
      
      if TIMER: TIMER.push('lines_add_section_len')
      lines = lines_add_section_len(lines)
      if TIMER: TIMER.pop('lines_add_section_len')
      
      if TIMER: TIMER.push('lines_mark_changed_sections')
      lines = lines_mark_changed_sections(lines)
      if TIMER: TIMER.pop('lines_mark_changed_sections')

      n = len(lines)
      lineH = h/n
      
      #print 'doc',doc.get_uri(), lines[0].raw
      
      if BUG_MASK & BUG_CAIRO_MAC_FONT_REF and me.font_face_keepalive is None:
        me.save_refs_to_all_font_faces(cr,scale,scale+3,10,12)
      
      cr.set_font_size(scale)
      whitespaceW = text_extents('.',cr)[0]
      #print pr_text_extents(' ',cr)
      #print pr_text_extents('.',cr)
      #print pr_text_extents(' .',cr)
      
      # ------------------------ display text silhouette -----------------------
      if TIMER: TIMER.push('draw silhouette')
      
      if dark(*fg):
        faded_fg = lighten(.5,*fg)
      else:
        faded_fg = darken(.5,*fg)
          
      rectH = h/float(len(lines))
      sofarH= 0
      sections = []
      for i, line in enumerate(lines):
      
        line.y = sofarH
        lastH = sofarH
        cr.set_font_size(scale)
        
        if line.raw.strip(): # there is some text here
            
          tw,th = text_extents(line.raw,cr)
        
          if line.search_match:
            cr.set_source_rgb(*searchBG)
          elif line.changed:
            cr.set_source_rgb(*changeCLR)
          elif me.draw_sections:
            cr.set_source_rgb(*faded_fg)
          else:
            cr.set_source_rgb(*fg)
            
          if line.section or line.subsection:
            #cr.select_font_face(fontfamily, cairo.FONT_SLANT_NORMAL, cairo.FONT_WEIGHT_BOLD)
            cr.set_font_size(scale+3)
            if line.justextSTR:
              x,y = cr.get_current_point()
              cr.move_to(whitespaceW*line.indent,y)
              cr.show_text(line.justextSTR)
            else:
              cr.show_text(line.raw)
          else:
            #cr.select_font_face(fontfamily, cairo.FONT_SLANT_NORMAL, cairo.FONT_WEIGHT_NORMAL)
            cr.set_font_size(scale)
            cr.show_text(line.raw)
          
          if smooshed:
            sofarH += lineH
          else:
            sofarH += th
        else: # empty line
          if smooshed:
            sofarH += lineH
          else:
            sofarH += scale-1
          
        if line.section:
          sections.append((line, lastH))
          
        cr.move_to(0, sofarH)
        
      if TIMER: TIMER.pop('draw silhouette')
          
      # ------------------- display sections and subsections labels  ------------------

      if me.draw_sections:
        # Subsections
        
        if TIMER: TIMER.push('draw subsections')
        
        if dark(*bg):
          bg_rect_C = lighten(.1,*bg)
        else:
          bg_rect_C = darken(.1,*bg)
          
        if 0: # - blot out the background -
          cr.set_source_rgba(bg_rect_C[0],bg_rect_C[1],bg_rect_C[2],.5)
          cr.rectangle(0,0,w,h)
          cr.fill()
        
        cr.new_path()
        cr.set_line_width(1.5)
        subsW = 10
        subsmargin = 10
        cr.set_font_size(10)
        for line in lines:
          if line.subsection:
            if 0:
              cr.move_to(subsmargin,line.y)
              cr.line_to(subsmargin+subsW,line.y)
            #if line.subsectionchanged:
            #  cr.set_source_rgb(*changeCLR)
            #else:
            #  cr.set_source_rgb(*fg)
            if 0:
              cr.set_source_rgb(*fg)
              cr.arc(subsmargin,line.y+3,2,0,6.28)
              cr.stroke()
            if 1:
              #cr.move_to(20,line.y)
              cr.set_source_rgb(*fg)
              #cr.show_text(line.subsection)
              cr.move_to(whitespaceW*line.indent,line.y)
              #cr.move_to(10,line.y)
              #fit_text(line.subsection, 10000, 10000, fg, bg, cr)
              show_section_label(line.subsection, fg, bg_rect_C, cr)
              
        if TIMER: TIMER.pop('draw subsections')
        
        # Sections
        
        if TIMER: TIMER.push('draw sections')
        cr.set_font_size(12)
        for line, lastH in sections:
        
          if 0: # section lines
            cr.move_to(0, lastH)
            cr.set_line_width(1)
            cr.set_source_rgb(*fg)
            cr.line_to(w,lastH)
            cr.stroke()
          
          if 1: # section heading
            cr.move_to(0,lastH)
            #if line.sectionchanged:
            #  cr.set_source_rgb(*changeCLR)
            #else:
            #  cr.set_source_rgb(*fg)
            cr.set_source_rgb(*fg)         
            #dispnfo = fit_text(line.section,4*w/5,line.section_len*rectH,fg,bg,cr)
            show_section_label(line.section, fg, bg_rect_C, cr)
            
          if 0 and dispnfo: # section hatches
            cr.set_line_width(1)
            r=dispnfo[0] # first line
            cr.move_to(r.x+r.tw+2,r.y-r.th/2+2)
            cr.line_to(w,r.y-r.th/2+2)
            cr.stroke()
            
        if TIMER: TIMER.pop('draw sections')
          
      # ------------------ translate back for the scroll bar -------------------
      
      cr.translate(-margin,0)
      w += margin

      # -------------------------- mark lines markers --------------------------
            
      if TIMER: TIMER.push('draw line markers')
      for line in lines:
        if line.search_match:
          clr = searchBG
        elif line.changed:
          clr = changeCLR
        else:
          continue # nothing interesting has happened with this line
        cr.set_source_rgb(*clr)      
        cr.rectangle(w-3,line.y-2,2,5)
        cr.fill()
      if TIMER: TIMER.pop('draw line markers')
        
      if TIMER: TIMER.pop('draw textmap')
      
      # save
      me.surface_textmap = cr.pop_group() # everything but the scrollbar
      me.lines = lines

    if TIMER: TIMER.push('surface_textmap')
    cr.set_source(me.surface_textmap)
    cr.rectangle(0,0,w,h)
    cr.fill()
    if TIMER: TIMER.pop('surface_textmap')
        
    # ------------------------------- scrollbar -------------------------------

    if TIMER: TIMER.push('scrollbar')
    
    topL,botL = visible_lines_top_bottom(me.geditwin)
    
    if topL==0 and botL==doc.get_end_iter().get_line():
      pass # everything is visible, don't draw scrollbar
    else:
      scrollbar(me.lines,topL,botL,w,h,bg,cr)
    
    if TIMER: TIMER.pop('scrollbar')
    
    me.topL = topL
    me.draw_scrollbar_only = False
    
    if TIMER: TIMER.pop('expose')
    if TIMER: TIMER.print_()
      
        
class TextmapWindowHelper:
  def __init__(me, plugin, window):
    me.window = window
    me.plugin = plugin

    panel = me.window.get_side_panel()
    image = gtk.Image()
    image.set_from_stock(gtk.STOCK_DND_MULTIPLE, gtk.ICON_SIZE_BUTTON)
    me.textmapview = TextmapView(me.window)
    me.ui_id = panel.add_item(me.textmapview, "TextMap", image)
    
    me.panel = panel

  def deactivate(me):
    me.window = None
    me.plugin = None
    me.textmapview = None

  def update_ui(me):
    queue_refresh(me.textmapview)
    
class TextmapPlugin(gedit.Plugin):
  def __init__(me):
    gedit.Plugin.__init__(me)
    me._instances = {}

  def activate(me, window):
    me._instances[window] = TextmapWindowHelper(me, window)

  def deactivate(me, window):
    if window in me._instances:
      me._instances[window].deactivate()

  def update_ui(me, window):
    # Called whenever the window has been updated (active tab
    # changed, etc.)
    #print 'plugin.update_ui'
    if window in me._instances:
      me._instances[window].update_ui()
      #window.do_expose_event()

########NEW FILE########
__FILENAME__ = TextWrap
#!/usr/bin/env python
# -*- coding: utf8 -*-
# Text Wrap Gedit Plugin
#
# This file is part of the Text Wrap Plugin for Gedit
# Copyright (C) 2008-2009 Christian Hartmann <christian.hartmann@berlin.de>
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

# This plugin is intended to ease the setting of Text Wrap (aka Line Wrap,
# Word Wrap) by either a Keyboard Shortcurt (currently sticked to Shift-Ctrl-B),
# a new entry in the View Menu or by an Icon in the Toolbar. The use of either 
# option works as a toggle (de- or activate text wrap). The initial setting for 
# new or new opened files is taken from the setting in the Preferences dialog 
# and remembered per file as long thew file is open. 

# Parts of this plugin are based on the work of Mike Doty <mike@psyguygames.com>
# who wrotes the infamous SplitView plugin. The rest is inspired from the Python
# Plugin Howto document and the Python-GTK documentation.

# CHANGELOG
# =========
# * 2008-10-10:
#   0.1 initial release for private use only
# * 2009-04-26:
#   0.2 changed filenames from textwrap to TextWrap as it conflicts with 
#   /usr/lib/python2.6/textwrap.py when loading the plugin. Unfortunately
#   i have no real clue what actualy is causing this conflict. This might
#   be reasoned by a change in the Gedit Python Plugin Loader, as this has
#   not been happening before upgrading gedit or a prerequisite of it through
#   an upgrade of my Ubuntu to 8.10 or 9.04. Added a couple documentst mainly
#   to ease the burdon of installation for gedit plugin beginners and made it
#   public available on my company website: http://hartmann-it-design.de/gedit




# import basic requisites
import gedit
import gtk

# for the texts in the UI elements we use gettext (do we realy?)
from gettext import gettext as _

# just a constant used in several places herein
plugin_name = "TextWrap"

# a common ui definition for menu and toolbar additions
ui_str = """<ui>
  <menubar name="MenuBar">
    <menu name="ViewMenu" action="View">
      <placeholder name="ViewOps_2">
        <menuitem name="ToggleTextWrap" action="ToggleTextWrap" />
      </placeholder>
    </menu>
  </menubar>
  <toolbar name="ToolBar">
    <separator />
    <toolitem name="ToggleTextWrap" action="ToggleTextWrap" />
  </toolbar>
</ui>
"""




# define the plugin helper class
class ToggleTextWrapHelper:

    def __init__(self, plugin, window):
    
        self._DEBUG = False
        
        if self._DEBUG:
            print "Plugin", plugin_name, "created for", window
        self._window = window
        self._plugin = plugin
        
        # Define default initial state for the plugin
        _initial_toggle_state_default = True
        
        # Get initial state from word wrapping in this view (not available
        # on gedit startup but if plugin is enabled during the gedit session
        # and for what ever reason we do not have an update ui signal on init)
        _active_view = self._window.get_active_view()
        try:
            _current_wrap_mode = _active_view.get_wrap_mode()
            if _current_wrap_mode == gtk.WRAP_NONE:
                self._initial_toggle_state = False
            else:
                self._initial_toggle_state = True
            if self._DEBUG:
                print "Plugin", plugin_name, "from current wrap mode using initial toggle state", self._initial_toggle_state
    	except:
            self._initial_toggle_state = _initial_toggle_state_default
            if self._DEBUG:
            	print "Plugin", plugin_name, "using _default_ initial toggle state", _initial_toggle_state_default
        
        # Add "Toggle Text Wrap" to the View menu and to the Toolbar
        self._insert_ui_items()


    def deactivate(self):
        if self._DEBUG:
            print "Plugin", plugin_name, "stopped for", self._window
        self._remove_ui_items()
        self._window = None
        self._plugin = None


    def _insert_ui_items(self):
        # Get the GtkUIManager
        self._manager = self._window.get_ui_manager()
        # Create a new action group
        self._action_group = gtk.ActionGroup("PluginActions")
        
        ## LEFT IN AS AN EXAMPLE:
        ## Create a toggle action (the classic way) ...
        #self._toggle_linebreak_action = gtk.ToggleAction(name="ToggleTextWrap", label="Text Wrap", tooltip="Toggle Current Text Wrap Setting", stock_id=gtk.STOCK_EXECUTE)
        #self._toggle_linebreak_action = gtk.ToggleAction(name="ToggleTextWrap", label="Text Wrap", tooltip="Toggle Current Text Wrap Setting", file="gtk-execute.png")
        ## connect my callback function to the action ...
        #self._toggle_linebreak_action.connect("activate", self.on_toggle_linebreak)
        ## and add the action with Ctrl+Shift+L as its keyboard shortcut
        #self._action_group.add_action_with_accel(self._toggle_linebreak_action, "<Ctrl><Shift>B")
        ## END OF EXAMPLE CODE
        
        # Create a toggle action (convenience way: see 16.1.2.2. in PyGTK Manual)
        #gtk.STOCK_INSERT_CROSS_REFERENCE
        #gtk.STOCK_INSERT-CROSS-REFERENCE
        #gtk.STOCK_INSERT_FOOTNOTE
        #None
        self._action_group.add_toggle_actions([(
                "ToggleTextWrap", 
                gtk.STOCK_OK, 
                _("Text Wrap"), 
                "<Ctrl><Shift>B", 
                _("Toggle Current Text Wrap Setting"), 
                self.on_toggle_linebreak, self._initial_toggle_state)])
        # Insert the action group
        self._manager.insert_action_group(self._action_group, -1)
        # Add my item to the "Views" menu and to the Toolbar
        self._ui_id = self._manager.add_ui_from_string(ui_str)
        # Debug merged ui
        if self._DEBUG:
        	print self._manager.get_ui()


    def _remove_ui_items(self):
        # Remove the ui
        self._manager.remove_ui(self._ui_id)
        self._ui_id = None
        # Remove action group
        self._manager.remove_action_group(self._action_group)
        self._action_group = None
        # ensure that manager updates
        self._manager.ensure_update()


    def update_ui(self):
        self._action_group.set_sensitive(self._window.get_active_document() != None)
        if self._DEBUG:
            print "Plugin", plugin_name, "called for UI update", self._window
        try:
            # Get initial state from word wrapping in this view (if any)
            _active_view = self._window.get_active_view()
            _current_wrap_mode = _active_view.get_wrap_mode()
            if self._DEBUG:
                print "Plugin", plugin_name, "current wrap mode", _current_wrap_mode
            # Get our action and set state according to current wrap mode
            _current_action = self._action_group.get_action("ToggleTextWrap")
            if _current_wrap_mode == gtk.WRAP_NONE:
                _current_action.set_active(False)
            else:
                _current_action.set_active(True)
    	except:
            return


    def on_toggle_linebreak(self, action):
        if self._DEBUG:
            print "Plugin", plugin_name, "action in", self._window
        _active_view = self._window.get_active_view()
        _current_wrap_mode = _active_view.get_wrap_mode()
        if self._DEBUG:
            print "Plugin", plugin_name, "current wrap mode", _current_wrap_mode
        _current_action = self._action_group.get_action("ToggleTextWrap")
        _is_active = _current_action.get_active()
        if self._DEBUG:
            print "Plugin", plugin_name, "current action state", _is_active
        if _is_active:
            _active_view.set_wrap_mode(gtk.WRAP_WORD)
        else:
            _active_view.set_wrap_mode(gtk.WRAP_NONE)


    def _console(self, vartext):
        if self._DEBUG:
            print "Plugin", plugin_name, vartext




# define the plugin derivate class
class ToggleTextWrapPlugin(gedit.Plugin):

    def __init__(self):
        gedit.Plugin.__init__(self)
        self._instances = {}


    def activate(self, window):
        self._instances[window] = ToggleTextWrapHelper(self, window)


    def deactivate(self, window):
        self._instances[window].deactivate()
        del self._instances[window]


    def update_ui(self, window):
        self._instances[window].update_ui()


########NEW FILE########
