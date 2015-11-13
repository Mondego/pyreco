__FILENAME__ = ebook
#!/usr/bin/env python
#author:Richard Peng
#project:Kindelabra
#website:http://www.richardpeng.com/projects/kindelabra/
#repository:https://github.com/richardpeng/Kindelabra
#license:Creative Commons GNU GPL v2
# (http://creativecommons.org/licenses/GPL/2.0/)

import struct

import zipfile
import re

class Sectionizer:
    def __init__(self, filename, perm):
        self.f = file(filename, perm)
        header = self.f.read(78)
        self.ident = header[0x3C:0x3C+8]
        if self.ident != 'BOOKMOBI':
            raise ValueError('invalid file format')
        num_sections, = struct.unpack_from('>H', header, 76)
        sections = self.f.read(num_sections*8)
        self.sections = struct.unpack_from('>%dL' % (num_sections*2), sections, 0)[::2] + (0xfffffff, )

    def loadSection(self, section):
        before, after = self.sections[section:section+2]
        self.f.seek(before)
        return self.f.read(after - before)

class Mobi:
    def __init__(self, filename):
        try:
            sections = Sectionizer(filename, 'rb')
            header = sections.loadSection(0)
            len_mobi = struct.unpack_from('>L', header, 20)[0] + 16
            mobi_raw = header[:len_mobi]
            titleoffset, titlelen = struct.unpack_from('>LL', mobi_raw, 84)
            self.title = header[titleoffset:titleoffset+titlelen]
            len_exth, = struct.unpack_from('>L', header, len_mobi+4)
            exth_records = header[len_mobi:len_mobi+len_exth][12:]
            self.exth = dict()
            while len(exth_records) > 8:
                rectype, reclen = struct.unpack_from('>LL', exth_records)
                recdata = exth_records[8:reclen]
                self.exth[rectype] = recdata
                exth_records = exth_records[reclen:]
        except ValueError:
            self.title = None

'''Kindlet metadata parsing
'''
class Kindlet:
    def __init__(self, filename):
        # For official apps, ASIN is stored in the Amazon-ASIN field of META-INF/MANIFEST.MF, and title in the Implementation-Title field
        kindlet = zipfile.ZipFile( filename, 'r')
        kdkmanifest = kindlet.read( 'META-INF/MANIFEST.MF' )
        # Catch Title
        kdktitlem = re.search( '(^Implementation-Title: )(.*?$)', kdkmanifest, re.MULTILINE )
        if kdktitlem and kdktitlem.group(2):
            self.title = kdktitlem.group(2).strip()
        else:
            self.title = None
        # Catch ASIN
        kdkasinm = re.search( '(^Amazon-ASIN: )(.*?$)', kdkmanifest, re.MULTILINE )
        if kdkasinm and kdkasinm.group(2):
            self.asin = kdkasinm.group(2).strip()
        else:
            self.asin = None
        kindlet.close()

'''Topaz metadata parsing. Almost verbatim code by Greg Riker from Calibre
'''
class StreamSlicer(object):
    def __init__(self, stream, start=0, stop=None):
        self._stream = stream
        self.start = start
        if stop is None:
            stream.seek(0, 2)
            stop = stream.tell()
        self.stop = stop
        self._len = stop - start

    def __getitem__(self, key):
        stream = self._stream
        base = self.start
        if isinstance(key, (int, long)):
            stream.seek(base + key)
            return stream.read(1)
        if isinstance(key, slice):
            start, stop, stride = key.indices(self._len)
            if stride < 0:
                start, stop = stop, start
            size = stop - start
            if size <= 0:
                return ""
            stream.seek(base + start)
            data = stream.read(size)
            if stride != 1:
                data = data[::stride]
            return data
        raise TypeError("stream indices must be integers")

class Topaz(object):
    def __init__(self, filename):
        self.stream = open(filename, 'rb')
        self.data = StreamSlicer(self.stream)

        sig = self.data[:4]
        if not sig.startswith('TPZ'):
            raise ValueError("'%s': Not a Topaz file" % getattr(stream, 'name', 'Unnamed stream'))
        offset = 4

        self.header_records, consumed = self.decode_vwi(self.data[offset:offset+4])
        offset += consumed
        self.topaz_headers = self.get_headers(offset)

        # First integrity test - metadata header
        if not 'metadata' in self.topaz_headers:
            raise ValueError("'%s': Invalid Topaz format - no metadata record" % getattr(stream, 'name', 'Unnamed stream'))

        # Second integrity test - metadata body
        md_offset = self.topaz_headers['metadata']['blocks'][0]['offset']
        md_offset += self.base
        if self.data[md_offset+1:md_offset+9] != 'metadata':
            raise ValueError("'%s': Damaged metadata record" % getattr(stream, 'name', 'Unnamed stream'))

        # Get metadata, and store what we need
        self.title, self.asin, self.type = self.get_metadata()
        self.stream.close()

    def decode_vwi(self,bytes):
        pos, val = 0, 0
        done = False
        while pos < len(bytes) and not done:
            b = ord(bytes[pos])
            pos += 1
            if (b & 0x80) == 0:
                done = True
            b &= 0x7F
            val <<= 7
            val |= b
            if done: break
        return val, pos

    def get_headers(self, offset):
        # Build a dict of topaz_header records, list of order
        topaz_headers = {}
        for x in range(self.header_records):
            offset += 1
            taglen, consumed = self.decode_vwi(self.data[offset:offset+4])
            offset += consumed
            tag = self.data[offset:offset+taglen]
            offset += taglen
            num_vals, consumed = self.decode_vwi(self.data[offset:offset+4])
            offset += consumed
            blocks = {}
            for val in range(num_vals):
                hdr_offset, consumed = self.decode_vwi(self.data[offset:offset+4])
                offset += consumed
                len_uncomp, consumed = self.decode_vwi(self.data[offset:offset+4])
                offset += consumed
                len_comp, consumed = self.decode_vwi(self.data[offset:offset+4])
                offset += consumed
                blocks[val] = dict(offset=hdr_offset,len_uncomp=len_uncomp,len_comp=len_comp)
            topaz_headers[tag] = dict(blocks=blocks)
        self.eoth = self.data[offset]
        offset += 1
        self.base = offset
        return topaz_headers

    def get_metadata(self):
        ''' Return MetaInformation with title, author'''
        self.get_original_metadata()
        return self.metadata['Title'], self.metadata['ASIN'], self.metadata['CDEType']

    def get_original_metadata(self):
        offset = self.base + self.topaz_headers['metadata']['blocks'][0]['offset']
        self.md_header = {}
        taglen, consumed = self.decode_vwi(self.data[offset:offset+4])
        offset += consumed
        self.md_header['tag'] = self.data[offset:offset+taglen]
        offset += taglen
        self.md_header['flags'] = ord(self.data[offset])
        offset += 1
        self.md_header['num_recs'] = ord(self.data[offset])
        offset += 1

        self.metadata = {}
        for x in range(self.md_header['num_recs']):
            taglen, consumed = self.decode_vwi(self.data[offset:offset+4])
            offset += consumed
            tag = self.data[offset:offset+taglen]
            offset += taglen
            md_len, consumed = self.decode_vwi(self.data[offset:offset+4])
            offset += consumed
            metadata = self.data[offset:offset + md_len]
            offset += md_len
            self.metadata[tag] = metadata

########NEW FILE########
__FILENAME__ = Kindelabra
#!/usr/bin/env python
#author:Richard Peng
#project:Kindelabra
#website:http://www.richardpeng.com/projects/kindelabra/
#repository:https://github.com/richardpeng/Kindelabra
#license:Creative Commons GNU GPL v2
# (http://creativecommons.org/licenses/GPL/2.0/)

import os
import datetime
import json
import re

import gtk
import kindle

VERSION = '0.2'

class KindleUI:
    '''Interface for manipulating a Kindle collection JSON file
    '''
    def __init__(self):
        self.root = os.getcwd()
        self.filemodel = gtk.TreeStore(str, str, bool)
        self.fileview = self.get_view('Files', self.filemodel, 'fileview')
        self.colmodel = gtk.TreeStore(str, str, str)
        self.colview = self.get_view('Collections', self.colmodel, 'colview')

        self.window = gtk.Window(gtk.WINDOW_TOPLEVEL)
        self.window.set_title("Kindelabra v%s" % VERSION)
        self.window.set_default_size(1000, 700)
        self.window.connect("destroy", gtk.main_quit)
        self.accel_group = gtk.AccelGroup()
        self.window.add_accel_group(self.accel_group)
        vbox_main = gtk.VBox()
        filechooserdiag = gtk.FileChooserDialog("Select your Kindle folder", self.window,
                                     gtk.FILE_CHOOSER_ACTION_SELECT_FOLDER,
                                    (gtk.STOCK_CANCEL, gtk.RESPONSE_REJECT,
                                     gtk.STOCK_OK, gtk.RESPONSE_ACCEPT))
        filechooserdiag.set_current_folder(os.path.join(self.root, 'system'))
        self.filechooser = gtk.FileChooserButton(filechooserdiag)
        self.filechooser.connect("current-folder-changed", self.load)

        file_toolbar = gtk.HBox()
        file_toolbar.pack_start(self.filechooser, True, True, 2)
        file_toolbar.pack_start(self.get_button('gtk-refresh', 'Refresh files', self.refresh), False, True, 2)
        file_toolbar.pack_start(self.get_button('gtk-open', 'Open collection file', self.open_collection, "O"), False, True, 2)
        file_toolbar.pack_start(gtk.VSeparator(), False, True, 2)
        file_toolbar.pack_start(self.get_button('gtk-save', 'Save collection file', self.save, "S"), False, True, 2)

        hbox_main = gtk.HBox()
        filescroll = gtk.ScrolledWindow()
        filescroll.add(self.fileview)
        colscroll = gtk.ScrolledWindow()
        colscroll.add(self.colview)
        col_toolbar = gtk.VBox()
        col_toolbar.pack_start(self.get_button('gtk-new', 'Create new collection', self.add_collection, "N"), False, True, 2)
        col_toolbar.pack_start(self.get_button('gtk-edit', 'Rename collection', self.rename_collection, "E"), False, True, 2)
        col_toolbar.pack_start(self.get_button('gtk-remove', 'Delete collection', self.del_collection), False, True, 2)
        col_toolbar.pack_start(gtk.HSeparator(), False, True, 7)
        col_toolbar.pack_start(self.get_button('gtk-go-forward', 'Add book to collection', self.add_file), False, True, 2)
        col_toolbar.pack_start(self.get_button('gtk-go-back', 'Remove book from collection', self.del_file), False, True, 2)
        col_toolbar.pack_start(gtk.HSeparator(), False, True, 7)
        col_toolbar.pack_start(self.get_button('gtk-revert-to-saved', 'Revert collections', self.revert), False, True, 2)

        hbox_main.add(filescroll)
        hbox_main.pack_start(col_toolbar, False, False, 2)
        hbox_main.add(colscroll)

        self.statusbar = gtk.Statusbar()

        vbox_main.pack_start(file_toolbar, False)
        vbox_main.add(hbox_main)
        vbox_main.pack_start(self.statusbar, False)

        self.window.add(vbox_main)
        self.window.show_all()
        self.status("Select your Kindle's home folder")
        gtk.main()

    def get_button(self, image, tooltip, cb, accelkey=None):
        button = gtk.Button()
        label = gtk.Image()
        label.set_from_stock(image, gtk.ICON_SIZE_LARGE_TOOLBAR)
        button.set_image(label)
        button.set_tooltip_text(tooltip)
        button.connect("clicked", cb)
        if accelkey:
            button.add_accelerator("activate", self.accel_group, ord(accelkey),
                                   gtk.gdk.CONTROL_MASK, gtk.ACCEL_VISIBLE)
        return button

    def status(self, message):
        self.statusbar.pop(1)
        self.statusbar.push(1, message)

    def load(self, widget):
        current = self.filechooser.get_current_folder()
        if not self.root == current:
            self.status("Loading... please wait")
            self.root = current
            self.kindle = kindle.Kindle(self.root)
            self.filemodel.clear()
            self.colmodel.clear()
            if self.kindle.is_connected():
                self.colfile = os.path.join(self.root, 'system', 'collections.json')
                self.db = kindle.CollectionDB(self.colfile)
                self.refresh(widget)
                self.revert(widget)
                self.status("Kindle Loaded")
            else:
                self.status("Kindle files not found")

    def get_collections(self):
        for collection in self.db:
            citer = self.colmodel.append(None, [collection, "", ""])
            for namehash in self.db[collection]['items']:
                if re.match('\*[\w]', namehash):
                    namehash = str(namehash.lstrip("*"))
                asin = re.match('\#([\w\-]+)\^\w{4}', namehash)
                if asin:
                    asin = asin.group(1)
                    try:
                        book = self.kindle.searchAsin(asin)
                        namehash = book.hash
                    except:
                        namehash = None
                        print "! ASIN %s belongs to collection %s but wasn't found on the device!" %( asin, collection )
                if namehash in self.kindle.files:
                    if self.kindle.files[namehash].title:
                        filename = self.kindle.files[namehash].title
                    else:
                        filename = os.path.basename(self.kindle.files[namehash].path)
                    if self.kindle.files[namehash].asin:
                        asin = self.kindle.files[namehash].asin
                    else:
                        asin = ""
                    fiter = self.colmodel.append(citer, [filename, namehash, asin])
                    #if asin != "":
                    #else:
                    #for row in self.filemodel

    def add_collection(self, widget):
        (dialog, input_box) = self.collection_prompt("Add Collection", "New Collection name:")
        dialog.show_all()
        colname = ""
        if dialog.run() == gtk.RESPONSE_ACCEPT:
            colname = unicode(input_box.get_text().strip())
        dialog.destroy()
        if colname == "":
            return
        if not colname in self.db:
            coliter = self.colmodel.append(None, [colname, "", ""])
            treesel = self.colview.get_selection()
            treesel.unselect_all()
            treesel.select_iter(coliter)
            treepath = treesel.get_selected_rows()[1][0]
            self.colview.scroll_to_cell(treepath)
            self.db[colname] = kindle.Collection({ 'locale': 'en-US', 'items': [], 'lastAccess': 0})
        else:
            self.status("%s collection already exists" % colname)

    def collection_prompt(self, title, label):
        labeltext = label
        label = gtk.Label(labeltext)
        col_input = gtk.Entry()
        col_input.set_activates_default(True)
        dialog = gtk.Dialog(title,
            self.window,
            gtk.DIALOG_MODAL | gtk.DIALOG_DESTROY_WITH_PARENT,
            (gtk.STOCK_CANCEL, gtk.RESPONSE_REJECT,
            gtk.STOCK_OK, gtk.RESPONSE_ACCEPT))
        dialog.set_default_response(gtk.RESPONSE_ACCEPT)
        dialog.vbox.pack_start(label)
        dialog.vbox.pack_start(col_input)
        return (dialog, col_input)

    def del_collection(self, widget):
        (colstore, rows) = self.colview.get_selection().get_selected_rows()
        collections = list()
        for row in rows:
            if len(row) == 1:
                collections.append(gtk.TreeRowReference(colstore, row))
        for col in collections:
            collection = unicode(self.get_path_value(colstore, col)[0])
            dialog = self.del_collection_prompt(collection)
            if dialog.run() == gtk.RESPONSE_ACCEPT and collection in self.db:
                del self.db[collection]
                colstore.remove(colstore[col.get_path()].iter)
                self.status("Deleted collection %s" % collection)
            dialog.destroy()

    def del_collection_prompt(self, title):
        label = gtk.Label("Delete collection \"%s\"?" % title)
        dialog = gtk.Dialog("Delete collection",
                    self.window,
                    gtk.DIALOG_MODAL | gtk.DIALOG_DESTROY_WITH_PARENT,
                    (gtk.STOCK_CANCEL, gtk.RESPONSE_REJECT,
                    gtk.STOCK_OK, gtk.RESPONSE_ACCEPT))
        dialog.vbox.pack_start(label)
        dialog.show_all()
        return dialog

    def rename_collection(self, widget):
        (colstore, rows) = self.colview.get_selection().get_selected_rows()
        collections = list()
        for row in rows:
            if len(row) == 1:
                collections.append(gtk.TreeRowReference(colstore, row))
        if len(collections) == 1:
            colrow = colstore[collections[0].get_path()]
            colname = colrow[0]
            (dialog, input_box) = self.collection_prompt("Add Collection", "New Collection name:")
            input_box.set_text(colname)
            dialog.show_all()
            newname = ""
            if dialog.run() == gtk.RESPONSE_ACCEPT:
                newname = input_box.get_text().strip()
                if not newname == colname and colname in self.db:
                    colrow[0] = newname
                    self.db[newname] = self.db[colname]
                    del self.db[colname]
            else:
                self.statusbar.pop(1)
            dialog.destroy()
        elif len(collections) > 1:
            self.status("Select a single collection to rename")
        else:
            self.statusbar.pop(1)

    def get_path_value(self, model, row):
        if isinstance(row, gtk.TreeRowReference):
            path = row.get_path()
        elif isinstance(row, tuple):
            path = row
        else:
            return None
        piter = model[path].iter
        return model.get(piter, 0, 1)

    def get_colpath_value(self, model, row):
        if isinstance(row, gtk.TreeRowReference):
            path = row.get_path()
        elif isinstance(row, tuple):
            path = row
        else:
            return None
        piter = model[path].iter
        return model.get(piter, 0, 1, 2)

    def get_hashes(self, filestore, filerows):
        filehashes = list()
        for row in filerows:
            gtkrow = gtk.TreeRowReference(filestore, row)
            filerow = self.get_path_value(filestore, gtkrow)
            if filerow[1] == "":
                piter = filestore.get_iter(gtkrow.get_path())
                citer = filestore.iter_children(piter)
                if citer:
                    subrow = filestore.get_path(citer)
                    subhashes = self.get_hashes(filestore, [subrow])
                    for subhash in subhashes:
                        filehashes.append(subhash)

                    niter = filestore.iter_next(citer)
                    while niter:
                        nextrow = filestore.get_path(niter)
                        subhashes = self.get_hashes(filestore, [nextrow])
                        for subhash in subhashes:
                            filehashes.append(subhash)
                        niter = filestore.iter_next(niter)
            else:
                filehashes.append((filerow[0], filerow[1]))
        return filehashes

    def add_file(self, widget):
        self.statusbar.pop(1)
        (filestore, filerows) = self.fileview.get_selection().get_selected_rows()
        (colstore, colrows) = self.colview.get_selection().get_selected_rows()

        colpaths = list()
        for row in colrows:
            if len(row) == 1:
                colpaths.append(row)
            else:
                parent = (row[0], )
                if not parent in colpaths:
                    colpaths.append(parent)
        targetcols = list()
        for path in colpaths:
            gtkrow = gtk.TreeRowReference(colstore, path)
            targetcols.append((path, self.get_path_value(colstore, gtkrow)[0]))
        if len(targetcols) == 0:
            self.status("Select a target collection to add")

        filehashes = self.get_hashes(filestore, filerows)
        for filename, filehash in filehashes:
            for colpath, colname in targetcols:
                colname = unicode(colname)
                if colname in self.db:
                    try:
                        asin = self.kindle.files[filehash].asin
                        if not self.db.in_collection(colname, asin):
                            colstore.append(colstore[colpath].iter, [filename, filehash, asin])
                            self.db.add_asin(colname, self.kindle.files[filehash].asin, self.kindle.files[filehash].type)
                    except TypeError:
                        if not self.db.in_collection(colname, filehash):
                            colstore.append(colstore[colpath].iter, [filename, filehash, ""])
                            self.db.add_filehash(colname, filehash)
                else:
                    self.status("No such collection:" + colname)
        #self.colview.expand_all()

    def del_file(self, widget):
        self.statusbar.pop(1)
        (colstore, rows) = self.colview.get_selection().get_selected_rows()
        ref = list()
        for row in rows:
            if len(row) == 2:
                ref.append(gtk.TreeRowReference(colstore, row))
        for row in range(len(ref)):
            gtkrow = ref[row]
            path = gtkrow.get_path()
            (filename, filehash, asin) = self.get_colpath_value(colstore, gtkrow)
            collection = unicode(self.get_colpath_value(colstore, (path[0], ))[0])
            if asin and asin != '':
                book = self.kindle.searchAsin(asin)
                asin = "#%s^%s" % (book.asin, book.type)
                if self.db[collection].has_hash(asin):
                    self.db[collection]['items'].remove(asin)
                    colstore.remove(colstore[path].iter)
            elif self.db[collection].has_hash(filehash):
                jsonhash = '*' + filehash
                self.db[collection]['items'].remove(jsonhash)
                colstore.remove(colstore[path].iter)
            else:
                self.status("File not in collection")

    def get_view(self, title, model, name):
        treeview = gtk.TreeView(model)
        treeview.set_name(name)
        tvcolumn = gtk.TreeViewColumn(title)
        treeview.append_column(tvcolumn)
        cell = gtk.CellRendererText()
        tvcolumn.pack_start(cell, True)
        tvcolumn.add_attribute(cell, 'text', 0)
        treeview.set_search_column(0)
        treeview.expand_all()
        treeview.set_rubber_banding(True)
        treeselection = treeview.get_selection()
        treeselection.set_mode(gtk.SELECTION_MULTIPLE)
        tvcolumn.set_sort_column_id(0)
        return treeview

    def revert(self, widget):
        self.db = kindle.CollectionDB(self.colfile)
        self.colmodel.clear()
        self.get_collections()
        self.colview.expand_all()
        self.status("Kindle collections reloaded")

    def save(self, widget):
        now = datetime.datetime.now().strftime('%Y%m%d%H%M%S')
        backup = os.path.join(self.root, 'system', '%s-collections.json.backup' % (now))
        jsonfile = os.path.join(self.root, 'system', 'collections.json')
        if os.path.exists(jsonfile):
            os.rename(jsonfile, backup)
        with open(os.path.join(self.root, 'system', 'collections.json'), 'wb') as colfile:
            json.dump(self.db.toKindleDb(), colfile, separators=(',', ':'), ensure_ascii=True)
        self.status("Collections saved to Kindle, restart to load your new collections")

    def get_filenodes(self, tree, nodes):
        if len(nodes) > 1:
            if not nodes[0] in tree:
                tree[nodes[0]] = dict()
            self.get_filenodes(tree[nodes[0]], nodes[1:])
        elif len(nodes) == 1:
            if not 'files' in tree:
                tree['files'] = list()
            tree['files'].append(nodes[0])

    def get_files(self, filemodel, tree, piter=None, path=""):
        for node in tree:
            if node == 'files':
                for filename in tree['files']:
                    filehash = kindle.get_hash('/mnt/us' + '/'.join([path, filename]))
                    if filehash in self.kindle.files and self.kindle.files[filehash].title:
                        filename = self.kindle.files[filehash].title
                    filemodel.append(piter, [filename, filehash, False])
            else:
                niter = filemodel.append(piter, [node, "", False])
                self.get_files(filemodel, tree[node], niter, '/'.join([path,node]))

    def refresh(self, widget):
        self.kindle.init_data()
        self.filemodel.clear()
        self.get_files(self.filemodel, self.kindle.filetree)
        self.fileview.expand_all()
        self.status("File list refreshed")

    def open_collection(self, widget):
        dialog = gtk.FileChooserDialog("Open a collection", self.window,
                                     gtk.FILE_CHOOSER_ACTION_OPEN,
                                    (gtk.STOCK_CANCEL, gtk.RESPONSE_REJECT,
                                     gtk.STOCK_OK, gtk.RESPONSE_ACCEPT))
        dialog.set_current_folder(os.path.join(self.root, 'system'))
        dialog.show()
        if dialog.run() == gtk.RESPONSE_ACCEPT:
            filename = dialog.get_filename()
            self.colfile = filename
            self.db = kindle.CollectionDB(self.colfile)
            self.revert(widget)
        dialog.destroy()

if __name__ == "__main__":
    KindleUI()

########NEW FILE########
__FILENAME__ = kindle
#!/usr/bin/env python
#author:Richard Peng
#project:Kindelabra
#website:http://www.richardpeng.com/projects/kindelabra/
#repository:https://github.com/richardpeng/Kindelabra
#license:Creative Commons GNU GPL v2
# (http://creativecommons.org/licenses/GPL/2.0/)

import hashlib
import os
import re
import json
import sys

import ebook

KINDLEROOT = '/mnt/us'
FILTER = ['pdf', 'mobi', 'prc', 'txt', 'tpz', 'azw1', 'azw', 'manga', 'azw2', 'zip']
FOLDERS = ['documents', 'pictures']

class Collection(dict):
    '''Holds a single collection
    '''
    def has_hash(self, filehash):
        for item in self['items']:
            if not item.find(filehash) == -1:
                return True
        return False

class CollectionDB(dict):
    '''Holds a collection database
    '''
    def __init__(self, colfile):
        #Fixes IOError if no collections.json is on the kindle
        try:
            with open(colfile) as colfile:
                tmpjson = json.load(colfile)
        except IOError:
	        tmpjson = json.loads('{}')
        tmpdict = dict()
        for key in iter(tmpjson.keys()):
            split = key.rpartition('@')
            colname = unicode(split[0])
            tmpdict[colname] = Collection(tmpjson[key])
            tmpdict[colname]['locale'] = split[2]
        dict.__init__(self, tmpdict)

    # Converts the collection back to Kindle JSON format
    def toKindleDb(self):
        tmpjson = dict()
        for key in self:
            tmpkey = '@'.join([key, self[key]['locale']])
            tmpvalue = self[key].copy()
            del tmpvalue['locale']
            tmpjson[tmpkey] = tmpvalue
        return tmpjson

    def in_collection(self, collection, filehash):
        if self[collection].has_hash(filehash):
            return True
        else:
            return False

    def add_filehash(self, collection, filehash):
        filehash = '*'+filehash
        self[collection]['items'].append(filehash)

    def add_asin(self, collection, asin, booktype):
        asin = "#%s^%s" % (asin, booktype)
        self[collection]['items'].append(asin)

class Ebook():
    def __init__(self, path):
        self.path = get_kindle_path(path)
        self.hash = get_hash(self.path)
        self.title = None
        self.meta = None
        self.asin = None
        self.type = None
        ext = os.path.splitext(path)[1][1:].lower()
        if ext in ['mobi', 'azw']:
            self.meta = ebook.Mobi(path)
            if self.meta.title:
                self.title = self.meta.title
                if 113 in self.meta.exth:
                    self.asin = self.meta.exth[113]
                if 501 in self.meta.exth:
                    self.type = self.meta.exth[501]
                if 503 in self.meta.exth:
                    self.title = self.meta.exth[503]
            else:
                print "\nMetadata read error:", path
        elif ext in ['tpz', 'azw1']:
            self.meta = ebook.Topaz(path)
            if self.meta.title:
                self.title = self.meta.title
                if self.meta.asin:
                    self.asin = self.meta.asin
                if self.meta.type:
                    self.type = self.meta.type
            else:
                print "\nTopaz metadata read error:", path
        elif ext in ['azw2']:
            self.meta = ebook.Kindlet(path)
            if self.meta.title:
                self.title = self.meta.title
            if self.meta.asin:
                self.asin = self.meta.asin
                self.type = 'AZW2'
            else:
                # Couldn't get an ASIN, developper app? We'll use the hash instead, which is what the Kindle itself does, so no harm done.
                print "\nKindlet Metadata read error, assuming developper app:", path

class Kindle:
    '''Access a Kindle filesystem
    '''
    def __init__(self, root):
        self.root = unicode(root)

    def init_data(self):
        self.files = dict()
        self.filetree = dict()
        if self.is_connected():
            for folder in FOLDERS:
                self.load_folder(folder)

            for path in self.files:
                regex = re.compile(r'.*?/(%s)' % '|'.join(FOLDERS))
                self.get_filenodes(self.filetree, re.sub(regex, r'\1', self.files[path].path).split('/'))

    def load_folder(self, path):
        sys.stdout.write("Loading " + path)
        for root, dirs, files in os.walk(os.path.join(self.root, path)):
            for filename in files:
                if os.path.splitext(filename)[1][1:].lower() in FILTER:
                    fullpath = os.path.abspath(os.path.join(root, filename))
                    book = Ebook(fullpath)
                    self.files[book.hash] = book
                    sys.stdout.write(".")
        sys.stdout.write("\n")

    def searchAsin(self, asin):
        '''Returns the Ebook with asin
        '''
        for filehash in self.files:
            if self.files[filehash].asin == asin:
                asin_hash = self.files[filehash]
                break
            else:
                asin_hash = None
        return asin_hash

    # Adds files to the dictionary: tree
    def get_filenodes(self, tree, nodes):
        if len(nodes) > 1:
            if not nodes[0] in tree:
                tree[nodes[0]] = dict()
            self.get_filenodes(tree[nodes[0]], nodes[1:])
        elif len(nodes) == 1:
            if not 'files' in tree:
                tree['files'] = list()
            tree['files'].append(nodes[0])

    # Checks if the specified folder is a Kindle filestructure
    def is_connected(self):
        docs = os.path.exists(os.path.join(self.root, 'documents'))
        sys = os.path.exists(os.path.join(self.root, 'system'))
        return docs and sys

# Returns a full path on the kindle filesystem
def get_kindle_path(path):
    path = os.path.normpath(path)
    folder = os.path.dirname(path)
    filename = os.path.basename(path)
    return '/'.join([KINDLEROOT, re.sub(r'.*(documents|pictures)', r'\1', folder), filename]).replace('\\', '/')

# Returns a SHA-1 hash
def get_hash(path):
    path = unicode(path).encode('utf-8')
    return hashlib.sha1(path).hexdigest()

if __name__ == "__main__":
    k = Kindle("Kindle")
    k.init_data()

########NEW FILE########
