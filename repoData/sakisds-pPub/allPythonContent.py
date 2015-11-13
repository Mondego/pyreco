__FILENAME__ = contentprovider
#!/usr/bin/env python2

# pPub by Thanasis Georgiou <sakisds@gmx.com>

# pPub is free software; you can redistribute it and/or modify it under the terms
# of the GNU General Public Licence as published by the Free Software Foundation.

# pPub is distributed in the hope that it will be useful, but WITHOUT ANY
# WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS FOR A
# PARTICULAR PURPOSE.  See the GNU General Public Licence for more details.

# You should have received a copy of the GNU General Public Licence along with
# pPub; if not, write to the Free Software Foundation, Inc., 51 Franklin Street,
# Fifth Floor, Boston, MA 02110-1301, USA.

import hashlib
import zipfile
import os
import shutil
from xml2obj import *

class ContentProvider(): #Manages book files and provides metadata
    def __init__(self, config, window):
        self.window = window
        #Check if cache folder exists
        self.config = config
        self.cache_path = self.config.get("Main", "cacheDir")
        if not os.path.exists(self.cache_path):
            os.mkdir(self.cache_path) #If not create it
        self.ready = False

    def prepare_book(self, filepath):
        #Clear any old files from the cache
        if os.path.exists(self.cache_path):
            shutil.rmtree(self.cache_path)
        #Extract new book
        zipfile.ZipFile(filepath).extractall(path=self.cache_path)
        #Set permissions
        os.system("chmod 700 "+self.cache_path)

        #Find opf file
        if os.path.exists(self.cache_path+"META-INF/container.xml"):
            container_data = xml2obj(open(self.cache_path+"META-INF/container.xml", "r"))
            opf_file_path = container_data.rootfiles.rootfile.full_path
            #Load opf
            metadata = xml2obj(open(self.cache_path+opf_file_path, "r"))
            self.oebps = os.path.split(opf_file_path)[0]
            #Find ncx file
            for x in metadata.manifest.item:
                if x.media_type == "application/x-dtbncx+xml":
                    ncx_file_path = self.cache_path+"/"+self.oebps+"/"+x.href

            #Load titles and filepaths
            self.titles = []
            self.files = []
            if os.access(ncx_file_path, os.R_OK): #Check if ncx is accessible
                #Parse ncx file
                pat=re.compile('-(.*)-')
                for line in open(ncx_file_path):
                    line=line.strip()
                    if "<text>" in line:
                        out = line.replace("<text>", "")
                        out = out.replace("</text>", "")
                        out = out.replace("<content", "")
                        self.titles.append(out)
                    if "<content" in line:
                        out = line.replace("<content src=\"", "")
                        out = out.replace("\"", "")
                        out = out.replace("/>", "")
                        self.files.append(out)
                while not len(self.titles) == len(self.files):
                    self.titles.remove(self.titles[0])

            #Validate files
            if not os.path.exists(self.cache_path+"/"+self.oebps+"/"+self.files[0]):
                #Reload files
                self.files = []
                for x in metadata.manifest.item:
                    if x.media_type == "application/xhtml+xml":
                        self.files.append(x.href)
                self.titles = []
                i = 1
                while not len(self.titles) == len(self.files):
                    self.titles.append("Chapter "+str(i))
                    i += 1

            #Calculate MD5 of book (for bookmarks)
            md5 = hashlib.md5()
            with open(filepath,'rb') as f: 
                for chunk in iter(lambda: f.read(128*md5.block_size), ''):
                    md5.update(chunk)
            #Metadata
            self.book_name = unicode(metadata.metadata.dc_title).encode("utf-8")
            self.book_author = unicode(metadata.metadata.dc_creator).encode("utf-8")
            self.book_md5 = md5.hexdigest()
            #Add book to config (used for bookmarks)
            if not self.config.has_section(self.book_md5):
                self.config.add_section(self.book_md5)
                self.config.set(self.book_md5, "count", 0)
                self.config.set(self.book_md5, "chapter", 0)
                self.config.set(self.book_md5, "pos", 0.0)
                self.config.set(self.book_md5, "stylesheet","")

            #End of preparations
            self.ready = True
            return True
        else: #Else show an error dialog
            error_dialog = Gtk.MessageDialog(self.window, 0, Gtk.MessageType.ERROR,
            Gtk.ButtonsType.OK, "Could not open book.")
            error_dialog.format_secondary_text("Make sure the book you are trying to open is in supported format and try again.")
            error_dialog.run()
            error_dialog.destroy()
            self.ready = False
            return False

    def get_chapter_file(self, number): #Returns a chapter file (for viewer)
        return self.cache_path+"/"+self.oebps+"/"+self.files[number]

    def get_chapter_count(self): #Returns number of chapters
        return len(self.files)-1

    def get_status(self):
        return self.ready

########NEW FILE########
__FILENAME__ = dialogs
#!/usr/bin/env python2

# pPub by Thanasis Georgiou <sakisds@gmx.com>

# pPub is free software; you can redistribute it and/or modify it under the terms
# of the GNU General Public Licence as published by the Free Software Foundation.

# pPub is distributed in the hope that it will be useful, but WITHOUT ANY
# WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS FOR A
# PARTICULAR PURPOSE.  See the GNU General Public Licence for more details.

# You should have received a copy of the GNU General Public Licence along with
# pPub; if not, write to the Free Software Foundation, Inc., 51 Franklin Street,
# Fifth Floor, Boston, MA 02110-1301, USA.

from gi.repository import Gdk, Gtk

class OpenDialog(Gtk.FileChooserDialog): #File>Open dialog
    def __init__(self, title, none, action, buttons, activate, files):
        super(OpenDialog, self).__init__(title, none, action, buttons)
        #Prepare filters
        if files == 0: #For open dialog only
            filter_pub = Gtk.FileFilter()
            filter_pub.set_name("EPub files")
            filter_pub.add_pattern("*.epub")
            self.add_filter(filter_pub)
        #For all dialogs
        filter_all = Gtk.FileFilter()
        filter_all.set_name("All files")
        filter_all.add_pattern("*")
        self.add_filter(filter_all)
        #Activation response
        self.activate = activate
        #Prepare dialog
        self.set_default_response(Gtk.ResponseType.OK)
        self.connect("file-activated", self.activate)
        self.connect("response", self.respond)

    def respond(self, widget, data=None): #Check response
        if data == (-5):
            self.activate(widget, data)
        else:
            self.destroy()

class JumpChapterDialog(Gtk.Dialog): #Chapters>Jump dialog
    def __init__(self):
        super(JumpChapterDialog, self).__init__()
        #Set window properties
        self.set_resizable(False)
        #Create widgets
        label = Gtk.Label("Enter chapter number:") #Label
        self.entry = Gtk.Entry() #Textbox
        #Actions
        self.entry.connect("activate", self.on_dialog_enter) #Close on enter
        #Add to container
        self.vbox.pack_start(self.entry, True, True, 0)
        self.vbox.pack_start(label, True, True, 0)
        self.vbox.show_all()
        #Add buttons
        self.add_button(Gtk.STOCK_OK, 0)
        self.add_button(Gtk.STOCK_CANCEL, 1)
        self.set_default_response(0)

    def get_text(self): #Returns text in entry box
        return self.entry.get_text()

    def run(self): #Shows dialog
        answer = super(JumpChapterDialog, self).run()
        if answer == 0:
            if self.entry.get_text() != "":
                return 0
            else:
                return 1
        else:
            return 1

    def on_dialog_enter(self, widget, data=None): #Closes "jump to" dialog when enter is pressed
        if self.entry.get_text() != "":
            self.response(0)
        else:
            self.response(1)

class SpinnerDialog(Gtk.Dialog): #Convert book spinner
    def __init__(self):
        super(SpinnerDialog, self).__init__()
        #Window options
        self.set_resizable(False)
        #Create container and objects
        hbox = Gtk.HBox()
        spinner = Gtk.Spinner()
        label = Gtk.Label("Importing...")
        #Start spinner and set size
        spinner.start()
        spinner.set_size_request(50,50)
        #Add objects to containers
        hbox.pack_start(spinner, True, True, 10)
        hbox.pack_start(label, True, True, 10)
        self.vbox.pack_start(hbox, True, True, 0)
        self.vbox.show_all()

class DeleteBookmarksDialog(Gtk.Dialog):
    def __init__(self, config, book_md5, action):
        #Window properties
        super(DeleteBookmarksDialog, self).__init__()
        self.set_title("Bookmarks")
        self.set_size_request(350, 250)
        self.activation_action = action
        #Variables
        self.config = config
        self.book_md5 = book_md5
        #Create objects
        label = Gtk.Label("Double click a bookmark to delete.") #Label
        self.scr_window = Gtk.ScrolledWindow() #Scrollable Area
        #Set properties of Scrollable Area
        self.scr_window.set_policy(Gtk.PolicyType.AUTOMATIC, Gtk.PolicyType.AUTOMATIC)
        self.scr_window.set_shadow_type(Gtk.ShadowType.ETCHED_IN)
        #Add objects to container
        self.vbox.pack_end(self.scr_window, True, True, 0)
        self.vbox.pack_start(label, False, False, 0)
        #Tree view
        self.refresh_tree()
        #Buttons
        self.add_button(Gtk.STOCK_CLOSE, 0)
        self.set_default_response(0)
        #Show all these stuff
        self.vbox.show_all()

    def refresh_tree(self, widget=None, data=None, row=None): #Refresh bookmarks view
        if widget != None:
            self.scr_window.remove(self.tree)
        store = self.create_model()
        self.tree = Gtk.TreeView(model=store)
        self.create_columns(self.tree)
        self.tree.connect("row-activated", self.activation_action)
        self.tree.connect("row-activated", self.refresh_tree)
        self.tree.set_rules_hint(True)
        #Re-add widget
        self.scr_window.add(self.tree)
        self.tree.show()

    def create_model(self): #Load data
        store = Gtk.ListStore(int, str)
        #Parse bookmarks from config
        count = int(self.config.get(self.book_md5, "count"))
        i = 0
        while i != count:
            i += 1
            store.append((i, "Chapter "+str(self.config.get(self.book_md5, str(i)+"-ch"))))
        return store

    def create_columns(self, tree_view): #Create columns for tree view
        #Number column
        renderer_text = Gtk.CellRendererText()
        column = Gtk.TreeViewColumn("Number", renderer_text, text=0)
        column.set_sort_column_id(0)
        tree_view.append_column(column)
        #Chapter column
        renderer_text = Gtk.CellRendererText()
        column = Gtk.TreeViewColumn("Chapter", renderer_text, text=1)
        column.set_sort_column_id(1)
        tree_view.append_column(column)

    def run(self): #Show dialog
        answer = super(DeleteBookmarksDialog, self).run()
        if answer == 0 or answer == -4:
            self.destroy()
        else:
            self.activation_action(self)

########NEW FILE########
__FILENAME__ = xml2obj
#!/usr/bin/env python2

# pPub by Thanasis Georgiou <sakisds@gmx.com>

# pPub is free software; you can redistribute it and/or modify it under the terms
# of the GNU General Public Licence as published by the Free Software Foundation.

# pPub is distributed in the hope that it will be useful, but WITHOUT ANY
# WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS FOR A
# PARTICULAR PURPOSE.  See the GNU General Public Licence for more details.

# You should have received a copy of the GNU General Public Licence along with
# pPub; if not, write to the Free Software Foundation, Inc., 51 Franklin Street,
# Fifth Floor, Boston, MA 02110-1301, USA.

import re
import xml.sax.handler

def xml2obj(src): #Converts xml to an object
    non_id_char = re.compile('[^_0-9a-zA-Z]')
    def _name_mangle(name):
        return non_id_char.sub('_', name)

    class DataNode(object):
        def __init__(self):
            self._attrs = {}    # XML attributes and child elements
            self.data = None    # child text data
        def __len__(self):
            # treat single element as a list of 1
            return 1
        def __getitem__(self, key):
            if isinstance(key, basestring):
                return self._attrs.get(key,None)
            else:
                return [self][key]
        def __contains__(self, name):
            return self._attrs.has_key(name)
        def __nonzero__(self):
            return bool(self._attrs or self.data)
        def __getattr__(self, name):
            if name.startswith('__'):
                # need to do this for Python special methods???
                raise AttributeError(name)
            return self._attrs.get(name,None)
        def _add_xml_attr(self, name, value):
            if name in self._attrs:
                # multiple attribute of the same name are represented by a list
                children = self._attrs[name]
                if not isinstance(children, list):
                    children = [children]
                    self._attrs[name] = children
                children.append(value)
            else:
                self._attrs[name] = value
        def __str__(self):
            return self.data or ''
        def __repr__(self):
            items = sorted(self._attrs.items())
            if self.data:
                items.append(('data', self.data))
            return u'{%s}' % ', '.join([u'%s:%s' % (k,repr(v)) for k,v in items])

    class TreeBuilder(xml.sax.handler.ContentHandler):
        def __init__(self):
            self.stack = []
            self.root = DataNode()
            self.current = self.root
            self.text_parts = []
        def startElement(self, name, attrs):
            self.stack.append((self.current, self.text_parts))
            self.current = DataNode()
            self.text_parts = []
            # xml attributes --> python attributes
            for k, v in attrs.items():
                self.current._add_xml_attr(_name_mangle(k), v)
        def endElement(self, name):
            text = ''.join(self.text_parts).strip()
            if text:
                self.current.data = text
            if self.current._attrs:
                obj = self.current
            else:
                # a text only node is simply represented by the string
                obj = text or ''
            self.current, self.text_parts = self.stack.pop()
            self.current._add_xml_attr(_name_mangle(name), obj)
        def characters(self, content):
            self.text_parts.append(content)

    builder = TreeBuilder()
    if isinstance(src,basestring):
        xml.sax.parseString(src, builder)
    else:
        xml.sax.parse(src, builder)
    return builder.root._attrs.values()[0]

########NEW FILE########
