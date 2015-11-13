__FILENAME__ = google2ubuntu-manager
#!/usr/bin/env python
# -*- coding: utf-8 -*-  
from gi.repository import Gtk
from gi.repository import Notify
from gi.repository import Gdk
from gi.repository import Gio
from os.path import expanduser
import os
import sys
import subprocess
import gettext
import xml.etree.ElementTree as ET

sys.path.append(os.path.dirname(os.path.abspath(__file__))+'/librairy')
from MainWindow import *
from localehelper import LocaleHelper

localeHelper = LocaleHelper()
lang = localeHelper.getLocale()

t=gettext.translation('google2ubuntu',os.path.dirname(os.path.abspath(__file__))+'/i18n/',languages=[lang])
t.install()

#keep the old way for the moment
#gettext.install('google2ubuntu',os.path.dirname(os.path.abspath(__file__))+'/i18n/')

# application principale
class MyApplication(Gtk.Application):
    def __init__(self):
        Gtk.Application.__init__(self)

    def do_activate(self):
        win = MainWindow(self)
        win.show_all()
        localeHelper = LocaleHelper()
        lang = localeHelper.getLocale()

        t=gettext.translation('google2ubuntu',os.path.dirname(os.path.abspath(__file__))+'/i18n/',languages=[lang])
        t.install()

    def do_startup(self):
        Gtk.Application.do_startup(self)
            

app = MyApplication()
exit_status = app.run(sys.argv)
sys.exit(exit_status)

########NEW FILE########
__FILENAME__ = google2ubuntu
#!/usr/bin/env python
# -*- coding: utf-8 -*-
from subprocess import *
from os.path import expanduser
import sys, subprocess, os, json, urllib2, unicodedata, time, gettext, locale

sys.path.append(os.path.dirname(os.path.abspath(__file__))+'/librairy')
from interface import interface
from localehelper import LocaleHelper

localeHelper = LocaleHelper()
lang = localeHelper.getLocale()

t=gettext.translation('google2ubuntu',os.path.dirname(os.path.abspath(__file__))+'/i18n/',languages=[lang])
t.install()


# pause media player if necessary
config = expanduser('~')+'/.config/google2ubuntu/google2ubuntu.conf'
paused = False
try:
    with open(config,"r") as f:
        for line in f.readlines():
            line = line.strip('\n')
            field = line.split('=')
            if field[0] == 'pause' and field[1].replace('"','') != '':
                os.system(field[1].replace('"','')+' &')
                paused = True
            elif field[0] == 'play':
                play_command = field[1].replace('"','')
except Exception:
    print 'Error reading google2ubuntu.conf file'

# launch the recognition                    
g2u = interface()

# restore media player state
print paused
if paused:
    os.system(play_command+' &')

########NEW FILE########
__FILENAME__ = add_window
#!/usr/bin/env python
# -*- coding: utf-8 -*-  
from gi.repository import Gtk
from gi.repository import Notify
from gi.repository import Gdk
from gi.repository import Gio
from os.path import expanduser
from ArgsWindow import ArgsWindow
from moduleSelection import moduleSelection
from HelpWindow import HelpWindow
from localehelper import LocaleHelper
from SetupWindow import *
from externalWindow import *
from internalWindow import *
import os
import sys
import subprocess
import gettext
import locale
import xml.etree.ElementTree as ET

TARGET_TYPE_URI_LIST = 80
dnd_list = [Gtk.TargetEntry.new('text/uri-list', 0, TARGET_TYPE_URI_LIST )]

class add_window():
    """
    @description: This class allow the user to manage all his commands thanks
    to a treeview. The grid generated will be added to the window
    """
    def __init__(self,button_config):
        self.Button = button_config
        # Gtk.ListStore will hold data for the TreeView
        # Only the first two columns will be displayed
        # The third one is for sorting file sizes as numbers
        store = Gtk.ListStore(str, str, str, str, str)
        # Get the data - see below
        self.populate_store(store)

        # use a filter in order to filtering the data
        self.tree_filter = store.filter_new()

        # create the treeview
        treeview = Gtk.TreeView.new_with_model(self.tree_filter)
        treeview.set_tooltip_text(_('list of commands'))
        treeview.set_headers_visible(False)
        treeview.set_enable_search(True)
        treeview.set_search_column(1)
        treeview.set_hexpand(True)
        treeview.set_vexpand(True)

        # The first TreeView column displays the data from
        # the first ListStore column (text=0), which contains
        # file names
        renderer_1 = Gtk.CellRendererText()        
        renderer_1.set_property("editable", True)
        renderer_1.connect("edited", self.key_edited,store)
        column_1 = Gtk.TreeViewColumn(_('Keys'), renderer_1, text=0)
        column_1.set_min_width(200)
        # Calling set_sort_column_id makes the treeViewColumn sortable
        # by clicking on its header. The column is sorted by
        # the ListStore column index passed to it 
        # (in this case 0 - the first ListStore column) 
        column_1.set_sort_column_id(0)        
        treeview.append_column(column_1)
        
        # xalign=1 right-aligns the file sizes in the second column
        renderer_2 = Gtk.CellRendererText(xalign=1)
        renderer_2.set_property("editable", True)
        renderer_2.connect("edited", self.command_edited,store)
        # text=1 pulls the data from the second ListStore column
        # which contains filesizes in bytes formatted as strings
        # with thousand separators
        column_2 = Gtk.TreeViewColumn(_('Commands'), renderer_2, text=1)
        # Mak the Treeview column sortable by the third ListStore column
        # which contains the actual file sizes
        column_2.set_sort_column_id(1)
        treeview.append_column(column_2)
        
        # the label we use to show the selection
        self.labelState = Gtk.Label()
        self.labelState.set_text(_("Ready"))
        self.labelState.set_justify(Gtk.Justification.LEFT) 
        self.labelState.set_halign(Gtk.Align.START) 
        
        # Use ScrolledWindow to make the TreeView scrollable
        # Otherwise the TreeView would expand to show all items
        # Only allow vertical scrollbar
        self.scrolled_window = Gtk.ScrolledWindow()
        self.scrolled_window.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        self.scrolled_window.add(treeview)
        self.scrolled_window.set_min_content_width(200)
        self.scrolled_window.set_min_content_height(200)        
        self.scrolled_window.connect('drag_data_received', self.on_drag_data_received,store)
        self.scrolled_window.drag_dest_set( Gtk.DestDefaults.MOTION | Gtk.DestDefaults.HIGHLIGHT | Gtk.DestDefaults.DROP, dnd_list, Gdk.DragAction.COPY)
                
        # a toolbar created in the method create_toolbar (see below)
        self.toolbar = self.create_toolbar(store)
        self.toolbar.set_hexpand(True)
        self.toolbar.show()

        # when a row of the treeview is selected, it emits a signal
        self.selection = treeview.get_selection()
        self.selection.connect("changed", self.on_changed,store)

        # define the visible func toolbar should be create
        self.tree_filter.set_visible_func(self.match_func)

        # Use a grid to add all item
        self.grid = Gtk.Grid()
        self.grid.set_border_width(0)
        self.grid.set_vexpand(True)
        self.grid.set_hexpand(True)
        self.grid.set_column_spacing(2)
        self.grid.set_column_homogeneous(False)
        self.grid.set_row_homogeneous(False)
        self.grid.set_row_spacing(2);
        self.grid.attach(self.toolbar,0,0,1,1)
        self.grid.attach(self.scrolled_window, 0, 1, 1, 1)    
        self.grid.attach(self.labelState,0,2,1,1) 
        
        # a grid for setup
        self.setup_grid = Gtk.Grid()


    def get_grid(self):
        """
        @description: get the grid
        
        @return a Gtk.Grid
        """
        return self.grid

    def on_drag_data_received(self,widget, context, x, y, Selection, target_type, timestamp,store):
        """
        @description: The treeview allows dnd so, if the user select a file then the process to 
        add a module start and finally a new line is added to the treeview. If the user select a 
        folder then a new line is added to the treeview with a command to open this folder
        
        @param: widget
            the widget that support dnd
        
        @param: Selection
            the item selected
        
        @param: store
            the listStore to append the new entry
        """
        if target_type == TARGET_TYPE_URI_LIST:
            uri= Selection.get_uris()[0]
            uri = uri.strip('\r\n\x00')
            uris= uri.split('://')
            if len(uris) >= 1 :
                path = uris[1]
                print 'path', path
                if os.path.isfile(path):
                    self.addModule(store,path)
                elif os.path.isdir(path):
                    store.append([_('key sentence'),'xdg-open '+path,_('external'), ' ', ' '])
                    self.scroll_to_bottom(store)

    def show_label(self,action):
        """
        @description: Show or hide the bottom label
        
        @param: action
            a string 'show' or 'hide'
        """
        etat = self.labelState.get_parent()
        if action == 'show' and etat == None:
            self.grid.attach(self.labelState,0,2,2,1)
        elif action == 'hide' and etat != None:
            self.grid.remove(self.labelState)

    def command_edited(self, widget, path, text,store):
        """
        @description: callback function called when the user edited the command
        field of the treeview, we need to modify the liststore
        
        @param: widget
            a Gtk.Widget
        
        @param: path
            the way to find the modifiyed item
        
        @param: text
            the new text
        
        @param: store
            the listStore to modify
        """
        iters = self.tree_filter.get_iter(path)
        path = self.tree_filter.convert_iter_to_child_iter(iters)
        store[path][1] = text
        self.saveTree(store)

    def key_edited(self, widget, path, text,store):
        """
        @description: same thing that the previous function
        """
        iters = self.tree_filter.get_iter(path)
        path = self.tree_filter.convert_iter_to_child_iter(iters)        
        store[path][0] = text
        self.saveTree(store)

    def on_changed(self, selection,store):
        """
        @description: hide the bottom label when the selection change
        
        @param: selection
            the selection from the treeview
            
        @return: a boolean 
        """
        # get the model and the iterator that points at the data in the model
        (model, iter) = selection.get_selected()
        if iter is not None:
            if self.setup_grid.get_parent is not None:
                self.setup_grid.destroy()
                
            self.show_label('hide')
            path = self.tree_filter.convert_iter_to_child_iter(iter)
            if store[path][2] == _('external'):
                if self.try_button.get_parent() is None:
                    self.toolbar.insert(self.try_button,2)
            else:
                if self.try_button.get_parent() is not None:
                    self.toolbar.remove(self.try_button)
         
        return True

    # a method to create the toolbar
    def create_toolbar(self,store):
        """
        @description: create the toolbar of the main window
        
        @param: store
            the listStore to connect to some buttons
            
        @return: a Gtk.toolbar
        """
        # a toolbar
        toolbar = Gtk.Toolbar()
        # which is the primary toolbar of the application
        toolbar.set_icon_size(Gtk.IconSize.LARGE_TOOLBAR)    
        toolbar.set_style(Gtk.ToolbarStyle.BOTH_HORIZ)
        toolbar.set_show_arrow(True) 

        # create a menu
        menu = Gtk.Menu()
        externe = Gtk.MenuItem(label=_("External commands"))
        externe.connect("activate",self.add_clicked,store,'externe')
        externe.show()
        menu.append(externe)
        interne = Gtk.MenuItem(label=_("Internal commands"))
        interne.connect("activate",self.add_clicked,store,'interne')
        interne.show()
        menu.append(interne)        
        module = Gtk.MenuItem(label=_("Module"))
        module.connect("activate",self.add_clicked,store,'module')
        module.show()
        menu.append(module)

        # create a button for the "add" action, with a stock image
        add_button = Gtk.MenuToolButton.new_from_stock(Gtk.STOCK_ADD)
        add_button.set_label(_("Add"))
        add_button.set_menu(menu)
        image = Gtk.Image()
        image.set_from_stock(Gtk.STOCK_ADD, Gtk.IconSize.BUTTON)
        # label is shown
        add_button.set_is_important(True)
        # insert the button at position in the toolbar
        toolbar.insert(add_button, 0)
        # show the button
        add_button.connect("clicked", self.add_clicked,store,'externe')
        add_button.set_tooltip_text(_('Add a new command'))
        add_button.show()
        
        # create a menu to store remove action
        delete_menu = Gtk.Menu()
        one_item = Gtk.MenuItem(label=_("Remove"))
        one_item.connect("activate",self.remove_clicked,store)
        one_item.set_tooltip_text(_('Remove this command'))
        one_item.show()
        delete_menu.append(one_item)
        all_item = Gtk.MenuItem(label=_("Clean up"))
        all_item.connect("activate",self.removeall_clicked,store)
        all_item.set_tooltip_text(_('Remove all commands'))
        all_item.show()
        delete_menu.append(all_item)   

        remove_button = Gtk.MenuToolButton.new_from_stock(Gtk.STOCK_REMOVE)
        remove_button.set_label(_("Remove"))
        remove_button.set_menu(delete_menu)
        image = Gtk.Image()
        image.set_from_stock(Gtk.STOCK_REMOVE, Gtk.IconSize.BUTTON)
        # label is shown
        remove_button.set_is_important(True)
        # insert the button at position in the toolbar
        toolbar.insert(remove_button, 1)
        # show the button
        remove_button.connect("clicked", self.remove_clicked,store)
        remove_button.set_tooltip_text(_('Remove this command'))
        remove_button.show()

         # create a button for the "try" action
        self.try_button = Gtk.ToolButton.new_from_stock(Gtk.STOCK_MEDIA_PLAY)
        self.try_button.set_label(_("Try"))
        self.try_button.set_is_important(True)
        self.try_button.connect("clicked",self.try_command,store)
        self.try_button.set_tooltip_text(_('Try this command'))
        self.try_button.show()
        #toolbar.insert(self.try_button,2)

        
        # create a button to edit a module
        self.module_button = Gtk.ToolButton.new_from_stock(Gtk.STOCK_EDIT)
        self.module_button.set_label(_('Edit'))
        self.module_button.set_is_important(True)
        self.module_button.connect("clicked",self.edit_clicked,store)
        self.module_button.set_tooltip_text(_('Edit this command'))
        self.module_button.show()
        toolbar.insert(self.module_button,2)

        # create a button to setup the application
        toolbar.insert(self.Button,3)

        
        # create a combobox to store user choice
        self.combo = self.get_combobox()
        toolcombo = Gtk.ToolItem()
        toolcombo.add(self.combo)
        toolcombo.show()
        toolbar.insert(toolcombo,4)        
        
        # add a separator
        separator = Gtk.ToolItem()
        separator.set_expand(True)
        toolbar.insert(separator,5)
        
        # create a button for the "Help" action
        help_button = Gtk.ToolButton.new_from_stock(Gtk.STOCK_HELP)
        help_button.set_label(_("Help"))
        help_button.set_is_important(True)
        toolbar.insert(help_button,6)
        help_button.connect("clicked",self.help_clicked )
        help_button.set_tooltip_text(_("Display help message"))
        help_button.show() 
        
        # return the complete toolbar
        return toolbar

    # open a setup window
    def setup_clicked(self,button):
        s = SetupWindow()

    # return a combobox to add to the toolbar
    def get_combobox(self):
        """
        @description: get the combobox of the toolbar
        
        @return: a Gtk.Combobox
        """
        # the data in the model, of type string
        listmodel = Gtk.ListStore(str)
        # append the data in the model
        listmodel.append([_('All')])
        listmodel.append([_('External')])
        listmodel.append([_('Internal')])
        listmodel.append([_('Modules')])
                        
        # a combobox to see the data stored in the model
        combobox = Gtk.ComboBox(model=listmodel)
        combobox.set_tooltip_text(_("What type of command to add")+'?')

        # a cellrenderer to render the text
        cell = Gtk.CellRendererText()

        # pack the cell into the beginning of the combobox, allocating
        # no more space than needed
        combobox.pack_start(cell, False)
        # associate a property ("text") of the cellrenderer (cell) to a column (column 0)
        # in the model used by the combobox
        combobox.add_attribute(cell, "text", 0)

        # the first row is the active one by default at the beginning
        combobox.set_active(0)

        # connect the signal emitted when a row is selected to the callback function
        combobox.connect("changed", self.on_combochanged)
        return combobox
    
    # callback function attach to the combobox   
    def on_combochanged(self,combo):
        """
        @description: the combobox is used to filter the treeview and switch
        between different commands types
        """
        self.tree_filter.refilter()

    # filter function
    def match_func(self, model, iterr, data=None):
        """
        @description: we get the combobox selection and filter the treeview
        data thanks to this selection.
        
        @return: a boolean
        """
        query = self.combo.get_active()
        value = model.get_value(iterr, 1)
        field = model.get_value(iterr, 2)
        
        if query == 0:
            return True
        elif query == 1 and _('modules') not in field and _('internal') not in field:
            return True
        elif query == 2 and _('internal') in field:
            return True
        elif query == 3 and _('modules') in field:
            return True
        else:
            return False
    
    def edit_clicked(self,button,store):
        # get the selected line, if it is module then we can open the window
        (model, iters) = self.selection.get_selected()

        if len(store) != 0:
            if iters is not None:
                iter = self.tree_filter.convert_iter_to_child_iter(iters)
                w = None
                if store[iter][2] == _('modules'):
                    w = ArgsWindow(store[iter][3], store[iter][1],store,iter)                   
                elif store[iter][2] == _('external'):
                    w = externalWindow(store,iter)
                elif store[iter][2] == _('internal'):
                    w = internalWindow(store,iter)
                    
                if self.setup_grid.get_parent() is None and w is not None:
                    self.setup_grid = w.get_grid()
                    self.grid.attach_next_to(self.setup_grid,self.scrolled_window,Gtk.PositionType.BOTTOM,1,1)                     

                
    def add_clicked(self,button,store,add_type):
        """
        @description: callback function called when the user want to add
        command
        
        @param: button
            the button that has to be clicked
        
        @param: store
            the listStore that will contain a new entry
        
        @param: add_type
            the type of the new command to add
        """
        if self.setup_grid.get_parent() is None:
            if add_type == 'externe':
                win = externalWindow(store,None)
                self.setup_grid = win.get_grid()
                self.grid.attach_next_to(self.setup_grid,self.scrolled_window,Gtk.PositionType.BOTTOM,1,1) 
                self.grid.show_all()

            elif add_type == 'interne':
                win = internalWindow(store,None)
                self.setup_grid = win.get_grid()
                self.grid.attach_next_to(self.setup_grid,self.scrolled_window,Gtk.PositionType.BOTTOM,1,1)   

            elif add_type == 'module':
                mo = moduleSelection()
                module = mo.getModule()
                if module != '-1':
                    self.addModule(store,module)
                else:
                    self.show_label('show')
                self.labelState.set_text(_("Error, you must choose a file"))
    
    def scroll_to_bottom(self,store):    
        # autoscroll to the bottom
        adj = self.scrolled_window.get_vadjustment()
        adj.set_value( adj.get_upper()  - adj.get_page_size() )
        
        # select the bottom one
        iter = store.get_iter(len(store)-1)
        st,iters = self.tree_filter.convert_child_iter_to_iter(iter)
        
        self.selection.select_iter(iters)


    def addModule(self,store,module):
        """
        @description: function that adds a module
        
        @param: store
            the listStore that will receive a new entry
        
        @param: module
            the path of the executable file of the module
        """
        # ex: recup de weather.sh
        name = module.split('/')[-1]
        iter = None
                
        if self.setup_grid.get_parent() is None:
            win = ArgsWindow(module,name,store,iter) 
            self.setup_grid = win.get_grid()
            self.grid.attach_next_to(self.setup_grid,self.scrolled_window,Gtk.PositionType.BOTTOM,1,1)          
    
    def remove_clicked(self,button,store):
        """
        @description: callback function called wnen the user want to remove 
        a line of the treeview
        
        @param: button
            the button that will be clicked
        
        @param: store
            the listStore that is going to be modify
        """
        if len(store) != 0:
            (model, iters) = self.selection.get_selected()
            if iters is not None:
                iter = self.tree_filter.convert_iter_to_child_iter(iters)
                if iter is not None:
                    self.show_label('show')
                    self.labelState.set_text(_('Remove')+': '+store[iter][0]+' '+store[iter][1]) 
                    store.remove(iter)
                    self.saveTree(store)
                else:
                    print "Select a title to remove"
        else:
            print "Empty list"

    def removeall_clicked(self,button,store):
        """
        @description: Same as the past function but remove all lines of the 
        treeview
        """
        # if there is still an entry in the model
        old = expanduser('~') +'/.config/google2ubuntu/google2ubuntu.xml'
        new = expanduser('~') +'/.config/google2ubuntu/.google2ubuntu.bak'
        if os.path.exists(old):
            os.rename(old,new)

        if len(store) != 0:
            # remove all the entries in the model
            self.labelState.set_text(_('Remove all commands'))               
            for i in range(len(store)):   
                iter = store.get_iter(0)
                store.remove(iter)
            
            self.saveTree(store)   
        print "Empty list"        

    def try_command(self,button,store):
        """
        @description: try a command (bash)
        
        @param: button
            the button that has to be clicked
        
        @param: store
            the listStore
        """
        (model, iter) = self.selection.get_selected()
        if iter is not None:
            command = model[iter][1]
            Type = model[iter][2]
            if _('internal') != Type and _('modules') != Type:
                process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
                output,error = process.communicate() 
                self.show_label('show')       
                self.labelState.set_text(output+'\n'+error)
    
    def help_clicked(self,button):
        """
        @description: show the help window
        
        @param: button
            the button that has to be clicked
        """
        win = HelpWindow()

    def populate_store(self, store):    
        """
        @description: load the treeview from the google2ubuntu.xml file or
        from the default.xml file
        
        @param: store
            the listStore that will be modify
        """    
        # user ocnfig file
        config = expanduser('~') +'/.config/google2ubuntu/google2ubuntu.xml'
        
        # default config file for the selected language
        path = os.path.dirname(os.path.abspath(__file__)).strip('librairy')    
        localeHelper = LocaleHelper('en_EN')
        self.lang = localeHelper.getLocale()
        default = path +'config/'+self.lang+'/default.xml'        

        try:
            if os.path.isfile(config):
                # here the program refuses to load the xml file
                tree = ET.parse(config)
            else:
                if os.path.exists(expanduser('~') +'/.config/google2ubuntu') == False:
                    os.makedirs(expanduser('~') +'/.config/google2ubuntu')
                tree = ET.parse(default)
            if os.path.exists(expanduser('~') +'/.config/google2ubuntu/modules') == False:
                os.system('cp -r '+path+'/modules '+expanduser('~') +'/.config/google2ubuntu')

            root = tree.getroot()
            for entry in root.findall('entry'):
                Type=entry.get('name')
                Key = entry.find('key').text
                Command = entry.find('command').text
                linker = entry.find('linker').text
                spacebyplus = entry.find('spacebyplus').text
                store.append([Key, Command, Type, linker, spacebyplus])  
        except Exception as e:
            print 'Error while reading config file'
            print type(e)
            print e.args
            print e

    def saveTree(self,store):
        """
        @description: save the treeview in the google2ubuntu.xml file
        
        @param: store
            the listStore attach to the treeview
        """
        # if there is still an entry in the model
        model = self.tree_filter.get_model()
        config = expanduser('~') +'/.config/google2ubuntu/google2ubuntu.xml'     
        try:
            if not os.path.exists(os.path.dirname(config)):
                os.makedirs(os.path.dirname(config))            
            
            root = ET.Element("data")
            if len(store) != 0:
                for i in range(len(store)):
                    iter = store.get_iter(i)
                    if model[iter][0] != '' and model[iter][1] != '':
                        for s in model[iter][0].split('|'):
                            s = s.lower()
                            s = s.replace('*',' ')
                            Type = ET.SubElement(root, "entry")
                            Type.set("name",unicode(model[iter][2],"utf-8"))
                            Key = ET.SubElement(Type, "key")
                            Key.text = unicode(s,"utf-8")
                            Command = ET.SubElement(Type, "command")
                            Command.text = unicode(model[iter][1],"utf-8")
                            Linker = ET.SubElement(Type, "linker") 
                            Spacebyplus = ET.SubElement(Type, "spacebyplus")
                            if store[iter][3] is not None or store[iter][4] is not None:
                                Linker.text = unicode(store[iter][3],"utf-8")
                                Spacebyplus.text = unicode(store[iter][4],"utf-8")
                            
            tree = ET.ElementTree(root).write(config,encoding="utf-8",xml_declaration=True)

            self.show_label('show')
            self.labelState.set_text(_('Save commands'))   
        except IOError:
            print "Unable to write the file"    

########NEW FILE########
__FILENAME__ = ArgsWindow
#!/usr/bin/env python
# -*- coding: utf-8 -*-  
from gi.repository import Gtk
from gi.repository import Notify
from gi.repository import Gdk
from gi.repository import Gio
from os.path import expanduser
import os, sys, subprocess, gettext
import xml.etree.ElementTree as ET

# gère l'apparition de la fenêtre d'assistance de création de module
class ArgsWindow():
    """
    @description: Display a window to help the user create a config for a
    module
    
    @param module
        module's folder
    
    @param name
        module's name
    
    @param store
        a Gtk.Listore in which we will append a new line for this module
    """
    def __init__(self,module,name,store,iter=None):    
        self.grid = Gtk.Grid()
        self.grid.set_border_width(5)
        self.grid.set_row_spacing(5)
        self.grid.set_vexpand(True)
        self.grid.set_hexpand(True)
        self.grid.set_column_spacing(2)
        self.grid.set_column_homogeneous(False)        
        
        label1 = Gtk.Label(_('key sentence'))
        label1.set_justify(Gtk.Justification.LEFT) 
        label1.set_halign(Gtk.Align.START) 
        label1.set_hexpand(True)
        
        label2 = Gtk.Label(_("Linking word"))
        label2.set_justify(Gtk.Justification.LEFT) 
        label2.set_halign(Gtk.Align.START) 

        label3 = Gtk.Label(_("Replace space by plus"))
        label3.set_justify(Gtk.Justification.LEFT) 
        label3.set_halign(Gtk.Align.START) 
        
        ll = Gtk.Label()
        ll.set_vexpand(True)
        
        self.entry1 = Gtk.Entry()
        self.entry1.set_tooltip_text(_('key sentence'))
        
        self.entry2 = Gtk.Entry()
        self.entry2.set_tooltip_text(_("Word to separate call and parameter"))
        self.checkbutton = Gtk.Switch()
        self.checkbutton.set_tooltip_text(_("Replace space by plus"))
        self.checkbutton.set_active(False)
        
        button = Gtk.Button()
        button.set_label(_("Go"))
        button.set_tooltip_text(_("Go"))
        image = Gtk.Image()
        image.set_from_stock(Gtk.STOCK_APPLY, Gtk.IconSize.BUTTON)
        button.set_image(image)
        
        button_cancel = Gtk.Button.new_from_stock(Gtk.STOCK_CANCEL)
        button_cancel.connect("clicked",self.do_destroy)
        
        print module, name
        if iter is None:
            button.connect("clicked",self.do_clicked,module,name,store)
        else:
            self.entry1.set_text(store[iter][0])
            linker = store[iter][3]
            spacebyplus = store[iter][4]
            self.entry2.set_text(linker)
            
            if spacebyplus == '1':
                self.checkbutton.set_active(True)
            button.connect("clicked",self.do_modify,store[iter][3],store,iter)
        
        self.grid.attach(label1,0,0,11,1)
        self.grid.attach(self.entry1,11,0,4,1)        
        self.grid.attach(label2,0,1,11,1)
        self.grid.attach(self.entry2,11,1,4,1)
        self.grid.attach(label3,0,2,14,1)
        self.grid.attach(self.checkbutton,14,2,1,1) 
        self.grid.attach(ll,0,3,15,1)
        self.grid.attach(button_cancel,13,4,1,1)
        self.grid.attach(button,14,4,1,1)    
        self.grid.show_all()            
    
    def do_destroy(self,button):
        self.grid.destroy()    
    
    def get_grid(self):
        return self.grid
        
    def do_clicked(self,button,module,name,store):
        """
        @description: callback function called when the user want to finish
        the configuration of the module. If everything is ok then the config
        file is written at the right place
        """
        key = self.entry1.get_text()
        linker = self.entry2.get_text()
        if self.checkbutton.get_active():
            spacebyplus='1' 
        else:
            spacebyplus='0'
        
        if linker is not '':
            try:
                # folder = name.split('.')[0]
                module_path=expanduser('~')+'/.config/google2ubuntu/modules/'
                                
                os.system('cp '+module+' '+module_path)
                print 'key', key
                print 'name', name
                print 'module', module_path+name
                print 'linker', linker
                print 'spacebyplus', spacebyplus
                store.append([key,name,'modules',linker,spacebyplus])    
                #save the store
                self.saveTree(store)
            except IOError:
                "Unable to open the file"
        
        self.grid.destroy()
    
    def do_modify(self,button,argsfile,store,iter):
        if self.checkbutton.get_active():
           spacebyplus = 1
        else:
           spacebyplus = 0
                
        # modifying the store
        store[iter][0] = self.entry1.get_text()
        store[iter][3] = self.entry2.get_text()
        store[iter][4] = str(spacebyplus)
        
        #save the store
        self.saveTree(store)
        self.grid.destroy()

    def saveTree(self,store):
        """
        @description: save the treeview in the google2ubuntu.xml file
        
        @param: store
            the listStore attach to the treeview
        """
        # if there is still an entry in the model
        config = expanduser('~') +'/.config/google2ubuntu/google2ubuntu.xml'     
        try:
            if not os.path.exists(os.path.dirname(config)):
                os.makedirs(os.path.dirname(config))            
            
            root = ET.Element("data")
            if len(store) != 0:
                for i in range(len(store)):
                    iter = store.get_iter(i)
                    if store[iter][0] != '' and store[iter][1] != '':
                        for s in store[iter][0].split('|'):
                            s = s.lower()
                            s = s.replace('*',' ')
                            Type = ET.SubElement(root, "entry")
                            Type.set("name",unicode(store[iter][2],"utf-8"))
                            Key = ET.SubElement(Type, "key")
                            Key.text = unicode(s,"utf-8")
                            Command = ET.SubElement(Type, "command")
                            Command.text = unicode(store[iter][1],"utf-8")
                            Linker = ET.SubElement(Type, "linker") 
                            Spacebyplus = ET.SubElement(Type, "spacebyplus")
                            if store[iter][3] is not None or store[iter][4] is not None:
                                Linker.text = unicode(store[iter][3],"utf-8")
                                Spacebyplus.text = unicode(store[iter][4],"utf-8")
                
            tree = ET.ElementTree(root).write(config,encoding="utf-8",xml_declaration=True)

        except IOError:
            print "Unable to write the file"   

########NEW FILE########
__FILENAME__ = basicCommands
#!/usr/bin/env python
# -*- coding: utf-8 -*-
from gi.repository import Gtk
from gi.repository import Gdk
from subprocess import *
from Googletts import tts
import os, gettext, time, subprocess

# Permet de faire appel aux fonctions basiques
class basicCommands():
    """
    @description: Called when the user wants to start an internal command
    for the moment there is 3 internal commands:
    
    * time 
    * clipboard
    * hour
    
    @param text
        name of the function to launch
        
    @param PID
        the program's pid to synchronize osd notification
    """
    def __init__(self,text,PID):
        # suivant le paramètre reçu, on exécute une action
        self.pid = PID
        if text == _('time'):
            self.getTime()
        elif text == _('power'):
            self.getPower()
        elif text == _('clipboard'):
            self.read_clipboard()
        elif text == _('dictation mode'):
            f=open('/tmp/g2u_dictation',"w")
            f.close()
        elif text == _('exit dictation mode'):
            os.remove('/tmp/g2u_dictation')
        else:
            print "no action found"
    
    def read_clipboard(self):
        """
        @description: A function to make google2ubuntu reads the selected
        text
        """
        clipboard = Gtk.Clipboard.get(Gdk.SELECTION_PRIMARY)

        text = clipboard.wait_for_text()
        if text != None:
            text=text.replace("'",' ')
            print "read:", text
            tts(text)
        else:
            tts(_('Nothing in the clipboard'))
    
    def getTime(self):
        """
        @description: a function that let google2ubuntu read and display
        the current timme
        """
        var=time.strftime('%H:%M',time.localtime())
        hour=var.split(':')[0]
        minute=var.split(':')[1]
        
        message = _('it is')+' '+hour+' '+_('hour')+' '+minute+' '+_('minute')
        os.system('echo "'+var+'" > /tmp/g2u_display_'+self.pid)
        print message
        tts(message)
                    
    def getPower(self):
        """
        @description: a function that let google2ubuntu read and display
        the current power state
        """
        command = "acpi -b"
        process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
        output,error  = process.communicate()
        #parsing output
        if output.count('Battery') > 0:
            pcent = output.split(' ')[3]
            rtime = output.split(' ')[4]
            
            if output.count('Charging') > 0:
                message = _('Charging')+': '+pcent+'\n'+rtime+' '+_('before charging')
            else:
                message = _('Discharging')+': '+pcent+'\n'+rtime+' '+_('remaining')
        else:
            message = _('battery is not plugged')
        
        os.system('echo "'+message+'" > /tmp/g2u_display_'+self.pid)
        tts(message)

########NEW FILE########
__FILENAME__ = externalWindow
#!/usr/bin/env python
# -*- coding: utf-8 -*-  
from gi.repository import Gtk
from gi.repository import Notify
from gi.repository import Gdk
from gi.repository import Gio
from os.path import expanduser
import os, sys, subprocess, gettext, locale
import xml.etree.ElementTree as ET

class externalWindow():
    def __init__(self,store,iter=None):
        self.grid = Gtk.Grid()
        self.grid.set_border_width(5)
        self.grid.set_row_spacing(5)
        self.grid.set_vexpand(True)
        self.grid.set_hexpand(True)
        self.grid.set_column_spacing(2)
        self.grid.set_column_homogeneous(False)
        label1 = Gtk.Label(_('key sentence'))
        label1.set_hexpand(True)
        label1.set_justify(Gtk.Justification.LEFT) 
        label1.set_halign(Gtk.Align.START) 
        label2 = Gtk.Label(_('your command'))
        label2.set_justify(Gtk.Justification.LEFT) 
        label2.set_halign(Gtk.Align.START) 
        ll = Gtk.Label()
        ll.set_vexpand(True)
        self.entry1 = Gtk.Entry()
        self.entry2 = Gtk.Entry()

        if iter is not None:
            self.entry1.set_text(store[iter][0])
            self.entry2.set_text(store[iter][1])

        button = Gtk.Button.new_from_stock(Gtk.STOCK_OK)        
        button.connect("clicked",self.button_clicked,store,iter)
        button_cancel = Gtk.Button.new_from_stock(Gtk.STOCK_CANCEL)
        button_cancel.connect("clicked",self.do_destroy)
        
        self.grid.attach(label1,0,0,11,1)
        self.grid.attach(self.entry1,11,0,4,1)
        self.grid.attach(label2,0,1,11,1)
        self.grid.attach(self.entry2,11,1,4,1)
        self.grid.attach(ll,0,2,15,1)    
        self.grid.attach(button_cancel,13,3,1,1) 
        self.grid.attach(button,14,3,1,1)         
        self.grid.show_all()  
   
    def do_destroy(self,button):
        self.grid.destroy()
   
    def get_grid(self):
        return self.grid
            
    def button_clicked(self,button,store,iter):
        if iter is None:
            if self.entry1.get_text() is not '' and self.entry2.get_text() is not '':
                store.append([self.entry1.get_text(),self.entry2.get_text(),_('external'), ' ',' '])
                self.saveTree(store)
        elif iter is not None:
            store[iter][0] = str(self.entry1.get_text())
            store[iter][1] = str(self.entry2.get_text())
            self.saveTree(store)
            
        self.grid.destroy()
        
    def saveTree(self,store):
        """
        @description: save the treeview in the google2ubuntu.xml file
        
        @param: store
            the listStore attach to the treeview
        """
        # if there is still an entry in the model
        config = expanduser('~') +'/.config/google2ubuntu/google2ubuntu.xml'     
        try:
            if not os.path.exists(os.path.dirname(config)):
                os.makedirs(os.path.dirname(config))            
            
            root = ET.Element("data")
            if len(store) != 0:
                for i in range(len(store)):
                    iter = store.get_iter(i)
                    if store[iter][0] != '' and store[iter][1] != '':
                        for s in store[iter][0].split('|'):
                            s = s.lower()
                            s = s.replace('*',' ')
                            Type = ET.SubElement(root, "entry")
                            Type.set("name",unicode(store[iter][2],"utf-8"))
                            Key = ET.SubElement(Type, "key")
                            Key.text = unicode(s,"utf-8")
                            Command = ET.SubElement(Type, "command")
                            Command.text = unicode(store[iter][1],"utf-8")                          
                            Linker = ET.SubElement(Type, "linker") 
                            Spacebyplus = ET.SubElement(Type, "spacebyplus")
                            if store[iter][3] is not None and store[iter][4] is not None:
                                Linker.text = unicode(store[iter][3],"utf-8")
                                Spacebyplus.text = unicode(store[iter][4],"utf-8")
                            
                
            tree = ET.ElementTree(root).write(config,encoding="utf-8",xml_declaration=True)

        except IOError:
            print "Unable to write the file"    

########NEW FILE########
__FILENAME__ = Googletts
#!/usr/bin/env python
# -*- coding: utf-8 -*-
from os.path import expanduser
from localehelper import LocaleHelper
import urllib, urllib2, time, re, unicodedata, os, sys, locale

class tts():
    """
    @description: Let google2ubuntu to use the Google tts API
    
    @param: the text to read to the user
    """
    def __init__(self,text):
        # need to put this line 
        locale.setlocale(locale.LC_ALL, '')

        # make the program able to switch language
        p = os.path.dirname(os.path.abspath(__file__)).strip('librairy')   
        localeHelper = LocaleHelper()
        lc = localeHelper.getLocale()
        text = unicodedata.normalize('NFKD', unicode(text,"utf-8"))
        text=text.encode("utf8")
        text = text.replace('\n',' ')
        text_list = re.split('(\,|\.)', text)
        combined_text = []
        output=open('/tmp/tts.mp3',"w")
        
        for idx, val in enumerate(text_list):
            if idx % 2 == 0:
                combined_text.append(val)
            else:
                joined_text = ''.join((combined_text.pop(),val))
                if len(joined_text) < 100:
                    combined_text.append(joined_text)
                else:
                    subparts = re.split('( )', joined_text)
                    temp_string = ""
                    temp_array = []
                    for part in subparts:
                        temp_string = temp_string + part
                        if len(temp_string) > 80:
                            temp_array.append(temp_string)
                            temp_string = ""
                    #append final part
                    temp_array.append(temp_string)
                    combined_text.extend(temp_array)
        #download chunks and write them to the output file
        for idx, val in enumerate(combined_text):
            mp3url = "http://translate.google.com/translate_tts?ie=UTF-8&tl=%s&q=%s&total=%s&idx=%s" % (lc, urllib.quote(val), len(combined_text), idx)
            headers = {"Host":"translate.google.com",
            "Referer":"http://www.gstatic.com/translate/sound_player2.swf",
            "User-Agent":"Mozilla/5.0 (Macintosh; Intel Mac OS X 10_7_3) AppleWebKit/535.19 (KHTML, like Gecko) Chrome/18.0.1025.163 Safari/535.19"}
            req = urllib2.Request(mp3url, '', headers)
            sys.stdout.write('.')
            sys.stdout.flush()
            if len(val) > 0:
                try:
                    response = urllib2.urlopen(req)
                    output.write(response.read())
                    time.sleep(.5)
                except urllib2.HTTPError as e:
                    print ('%s' % e)
        output.close()


        os.system("play /tmp/tts.mp3 &")

########NEW FILE########
__FILENAME__ = HelpWindow
#!/usr/bin/env python
# -*- coding: utf-8 -*-  
from gi.repository import Gtk
from gi.repository import Notify
from gi.repository import Gdk
from gi.repository import Gio
from os.path import expanduser
import os, sys, subprocess, gettext

# gère l'apparition de le fenêtre d'aide
class HelpWindow():
    """
    @description: Diaplay an help window
    """
    def __init__(self):
        #a  Gtk.AboutDialog
        self.aboutdialog = Gtk.AboutDialog()

        # lists of authors and documenters (will be used later)
        authors = ["Franquet Benoit"]
        documenters = ["Franquet Benoit"]
        translators = "Franquet Benoit <benoitfranquet@gmail.com>\n"
        translators += "Tectas\n"
        translators += "Daniele Scasciafratte <mte90net@gmail.com>\n"
        translators += "Leor <leor.bi.otti.flor@gmail.com﻿>\n"
        translators += "Ladios\n"
        translators += "Franck Claessen"

        # we fill in the aboutdialog
        self.aboutdialog.set_program_name(_("Help Google2Ubuntu"))
        self.aboutdialog.set_copyright("Copyright \xc2\xa9 2014 Franquet Benoit")
        self.aboutdialog.set_authors(authors)
        self.aboutdialog.set_translator_credits(translators) 
        self.aboutdialog.set_documenters(documenters)
        self.aboutdialog.set_version("1.1.1")
        self.aboutdialog.set_license_type (Gtk.License.GPL_3_0,)
        self.aboutdialog.set_website("https://github.com/benoitfragit/google2ubuntu")
        self.aboutdialog.set_website_label("https://github.com/benoitfragit/google2ubuntu")

        # we do not want to show the title, which by default would be "About AboutDialog Example"
        # we have to reset the title of the messagedialog window after setting the program name
        self.aboutdialog.set_title("")

        # to close the aboutdialog when "close" is clicked we connect the
        # "response" signal to on_close
        self.aboutdialog.connect("response", self.on_close)
        # show the aboutdialog
        self.aboutdialog.show()
        
    # destroy the aboutdialog
    def on_close(self, action, parameter):
        """
        @description: function called when the user wants to close the window
        
        @param: action
            the window to close
        """
        action.destroy()

########NEW FILE########
__FILENAME__ = interface
#!/usr/bin/env python
# -*- coding: utf-8 -*-
from subprocess import *
from os.path import expanduser
import sys, subprocess, os, json, urllib2, unicodedata, time, gettext, locale

from Googletts import tts
from stringParser import stringParser
from localehelper import LocaleHelper

# La classe interface permet de lancer l'enregistrement et de communiquer
# avec Google
class interface():
    """
    @description: This class start the osd server, then start recording your voice before
    asking Google for the translation. Then, the result is parsing in order to
    execute the associated action
    """
    def __init__(self):
        # make the program able to switch language
        self.p = os.path.dirname(os.path.abspath(__file__)).strip('librairy')        

        localeHelper = LocaleHelper('en_EN')

        self.lang = localeHelper.getLocale()
        # this line can be remove if we modify the config/en_EN to config/en
        #self.lang = self.lang+'_'+self.lang.upper()
   
        # Initialisation des notifications
        self.PID = str(os.getpid())
        os.system('rm /tmp/g2u_*_'+self.PID+' 2>/dev/null')
        os.system('python '+self.p+'librairy/osd.py '+self.PID+' &')

        # on joue un son pour signaler le démarrage
        os.system('play '+self.p+'resources/sound.wav &')
        os.system('> /tmp/g2u_start_'+self.PID)

        # On lance le script d'enregistrement pour acquérir la voix pdt 5s
        command =self.p+'record.sh ' + self.PID
        p = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
        output,error  = p.communicate()

        # return to 16kHz
        os.system(self.p+'convert.sh '+self.PID)
        
        self.sendto()    

    def sendto(self):
        """
        @function: Send the flac file to Google and start the parser
        """
        # lecture du fichier audio
        filename='/tmp/voix_'+self.PID+'.flac'
        f = open(filename)
        data = f.read()
        f.close()
        
        # suppression du fichier audio
        if os.path.exists('/tmp/voix_'+self.PID+'.flac'):
            os.system('rm /tmp/voix_'+self.PID+'.flac')
        
        # fichier de configuration
        config = expanduser('~') + '/.config/google2ubuntu/google2ubuntu.xml'
        default = self.p +'config/'+self.lang+'/default.xml'
        
        if os.path.exists(config):
            config_file = config
        else:
            if os.path.exists(expanduser('~') +'/.config/google2ubuntu') == False:
                os.makedirs(expanduser('~') +'/.config/google2ubuntu')
            if os.path.exists(expanduser('~') +'/.config/google2ubuntu/modules') == False:
                os.system('cp -r '+self.p+'/modules '+expanduser('~') +'/.config/google2ubuntu')
            if os.path.exists(default) == False:
                default = self.p+'config/en_EN/default.xml'
                
            config_file = default
        
        print 'config file:', config_file
        try:
            # envoie une requête à Google
            req = urllib2.Request('https://www.google.com/speech-api/v1/recognize?xjerr=1&client=chromium&lang='+self.lang, data=data, headers={'Content-type': 'audio/x-flac; rate=16000'})  
            # retour de la requête
            ret = urllib2.urlopen(req)
            
            # before parsing we need to eliminate eventually empty result when sox bug
            # ret= ((ret.read()).split('}'))[0]+'}]}'

            # parsing du retour
            text=json.loads(ret.read())['hypotheses'][0]['utterance']
            os.system('echo "'+text.encode("utf-8")+'" > /tmp/g2u_result_'+self.PID)

            # parsing du résultat pour trouver l'action
            sp = stringParser(text,config_file,self.PID)                 
        except Exception:
            message = _('unable to translate')
            os.system('echo "'+message+'" > /tmp/g2u_error_'+self.PID)
            sys.exit(1)

########NEW FILE########
__FILENAME__ = internalWindow
#!/usr/bin/env python
# -*- coding: utf-8 -*-  
from gi.repository import Gtk
from gi.repository import Notify
from gi.repository import Gdk
from gi.repository import Gio
from os.path import expanduser
import os, sys, subprocess, gettext, locale
import xml.etree.ElementTree as ET

class internalWindow():
    def __init__(self,store,iter=None):        
        self.grid = Gtk.Grid()
        self.grid.set_border_width(5)
        self.grid.set_row_spacing(5)
        self.grid.set_vexpand(True)
        self.grid.set_hexpand(True)
        self.grid.set_column_spacing(2)
        self.grid.set_column_homogeneous(False)
        self.grid.set_row_homogeneous(False)
        
        label1 = Gtk.Label(_('key sentence'))
        label1.set_justify(Gtk.Justification.LEFT) 
        label1.set_halign(Gtk.Align.START) 
        label1.set_hexpand(True)
        label2 = Gtk.Label(_('your command'))
        label2.set_justify(Gtk.Justification.LEFT) 
        label2.set_halign(Gtk.Align.START)
        ll = Gtk.Label()
        ll.set_vexpand(True)
        self.entry1 = Gtk.Entry()
        if iter is not None:
            self.entry1.set_text(store[iter][0])
            
        self.combo = self.__get_combobox(store,iter)
        button = Gtk.Button.new_from_stock(Gtk.STOCK_OK)
        button.connect("clicked",self.button_clicked,store,iter)
        button_cancel = Gtk.Button.new_from_stock(Gtk.STOCK_CANCEL)
        button_cancel.connect("clicked",self.do_destroy)
        
        
        self.grid.attach(label1,0,0,11,1)
        self.grid.attach(self.entry1,11,0,4,1)
        self.grid.attach(label2,0,1,11,1)
        self.grid.attach(self.combo,11,1,4,1)
        self.grid.attach(ll,0,2,15,1)
        self.grid.attach(button_cancel,13,3,1,1)
        self.grid.attach(button,14,3,1,1)
        self.grid.show_all()
    
    def do_destroy(self,button):
        self.grid.destroy()    
    
    def get_grid(self):
        return self.grid
    
    def button_clicked(self,button,store,iter):
        if iter is None:
            if self.entry1.get_text() is not '':
                store.append([self.entry1.get_text(),str(self.dic[self.combo.get_active()]),_('internal'),' ',' '])
                self.saveTree(store)
        else:
            store[iter][0] = str(self.entry1.get_text())
            store[iter][1] = str(self.dic[self.combo.get_active()])
            self.saveTree(store)
        
        self.grid.destroy()
        
    # return a combobox to add to the toolbar
    def __get_combobox(self,store,iter):
        """
        @description: get the combobox of the toolbar
        
        @return: a Gtk.Combobox
        """
        # the data in the model, of type string
        listmodel = Gtk.ListStore(str)
        # append the data in the model
        self.dic = {}
        self.dic[0] = _('time')
        listmodel.append([_('time')])
        self.dic[1] = _('power')
        listmodel.append([_('power')])
        self.dic[2] = _('clipboard')
        listmodel.append([_('clipboard')])
        self.dic[3] = _('dictation mode')
        listmodel.append([_('dictation mode')])
        self.dic[4] = _('exit dictation mode')
        listmodel.append([_('exit dictation mode')])
        
        selected = 0
        if iter is not None:
            for i in range(len(self.dic)):
                if self.dic[i] == store[iter][1]:
                    selected = i
                    
        # a combobox to see the data stored in the model
        combobox = Gtk.ComboBox(model=listmodel)
        combobox.set_tooltip_text(_("Which internal command to choose")+'?')

        # a cellrenderer to render the text
        cell = Gtk.CellRendererText()

        # pack the cell into the beginning of the combobox, allocating
        # no more space than needed
        combobox.pack_start(cell, False)
        # associate a property ("text") of the cellrenderer (cell) to a column (column 0)
        # in the model used by the combobox
        combobox.add_attribute(cell, "text", 0)

        # the first row is the active one by default at the beginning
        combobox.set_active(selected)

        return combobox

    def saveTree(self,store):
        """
        @description: save the treeview in the google2ubuntu.xml file
        
        @param: store
            the listStore attach to the treeview
        """
        # if there is still an entry in the model
        config = expanduser('~') +'/.config/google2ubuntu/google2ubuntu.xml'     
        try:
            if not os.path.exists(os.path.dirname(config)):
                os.makedirs(os.path.dirname(config))            
            
            root = ET.Element("data")
            if len(store) != 0:
                for i in range(len(store)):
                    iter = store.get_iter(i)
                    if store[iter][0] != '' and store[iter][1] != '':
                        for s in store[iter][0].split('|'):
                            s = s.lower()
                            s = s.replace('*',' ')
                            Type = ET.SubElement(root, "entry")
                            Type.set("name",unicode(store[iter][2],"utf-8"))
                            Key = ET.SubElement(Type, "key")
                            Key.text = unicode(s,"utf-8")
                            Command = ET.SubElement(Type, "command")
                            Command.text = unicode(store[iter][1],"utf-8")
                            Linker = ET.SubElement(Type, "linker") 
                            Spacebyplus = ET.SubElement(Type, "spacebyplus")
                            if store[iter][3] is not None and store[iter][4] is not None:
                                Linker.text = unicode(store[iter][3],"utf-8")
                                Spacebyplus.text = unicode(store[iter][4],"utf-8")
                
            tree = ET.ElementTree(root).write(config,encoding="utf-8",xml_declaration=True)

        except IOError:
            print "Unable to write the file"    

########NEW FILE########
__FILENAME__ = localehelper
#!/usr/bin/env python
# -*- coding: utf-8 -*-  
from os.path import expanduser
import locale
import os

RELATIVE_LOCALE_CONFIG_PATH = '/.config/google2ubuntu/google2ubuntu.conf'

class LocaleHelper:
    def __init__(self, defaultLocale='en_EN', languageFolder=os.path.dirname(os.path.abspath(__file__)) + '/../i18n/'):
        systemLocale = locale.getlocale()
        
        self.__systemLocale = None
        
        if systemLocale is not None and len(systemLocale) > 0:
            if systemLocale[0] is not None and len(systemLocale[0]) > 0:
                self.__systemLocale = systemLocale[0]
        
        self.__languageFolder = languageFolder
        self.__defaultLocale = defaultLocale
        self.__localeConfPath = expanduser('~') + RELATIVE_LOCALE_CONFIG_PATH
    
    def __getSystemLocale(self):
        if self.__checkIfLocalePresent(self.__systemLocale):
            return self.__systemLocale
        else:
            fallback = self.__getLocaleFallbackValue(self.__systemLocale)
            if self.__checkIfLocalePresent(fallback):
                return fallback
            else:
                return self.__defaultLocale

    def __readSingleLine(self, filePath):
        fileHandle = None
        line = None
        try:
            fileHandle = open(filePath, 'r')
            line = fileHandle.readline().strip('\n')
        except:
            pass
        finally:
            if fileHandle:
                fileHandle.close()
        return line

    def __getLocaleConfigValue(self):
        fileHandle = None
        lc = None
        try:
            fileHandle = open(self.__localeConfPath, 'r')
            for ligne in fileHandle.readlines():
                ligne = ligne.strip('\n')
                field=ligne.split('=')
                if field[0] == 'locale':
                    lc = field[1]

        except:
            pass
        finally:
            if fileHandle:
                fileHandle.close()
        if self.__checkIfLocalePresent(lc):
            return lc
        else:
            return self.__getSystemLocale()

    def __getLocaleFallbackValue(self, lang):
        if lang is not None and lang != '':
            return self.__readSingleLine(self.__languageFolder + lang + '/fallback')
        return None

    def __checkIfLocalePresent(self, lang):
        if lang is not None:
            if lang.strip() != '' and os.path.isdir(self.__languageFolder + lang + '/LC_MESSAGES') == True:
                return True
        
        return False
    
    def getFormatedLocaleString(self, localeString, longFormat=True):
        if localeString is None:
            return None
        elif localeString.strip() == '':
            return None

        localeString = localeString.replace(' ', '')

        if '_' not in localeString and longFormat == True:
            localeString = localeString + '_' + localeString.upper()
        elif '_' in localeString and longFormat == False:
            localeString = localeString.split('_')[0]
        
        return localeString
    
    def getLocale(self, longFormat=True):
        return self.getFormatedLocaleString(self.__getLocaleConfigValue(), longFormat)

########NEW FILE########
__FILENAME__ = MainWindow
#!/usr/bin/env python
# -*- coding: utf-8 -*-  
from gi.repository import Gtk
from gi.repository import Notify
from gi.repository import Gdk
from gi.repository import Gio
from os.path import expanduser
from add_window import add_window
from SetupWindow import *
import os
import sys
import subprocess
import gettext

# Classe MyWindow gere l'apparition de la fenetre principale
class MainWindow(Gtk.ApplicationWindow):
    """
    @description: This class display the main window that the user will 
    see when he wants to manage his commands
    """
    def __init__(self,app):
        Gtk.Window.__init__(self, title="google2ubuntu-manager",application=app)
        self.set_default_size(800, 400)  
        self.set_resizable(True)     
        self.set_border_width(0)
        self.get_focus()
        self.set_position(Gtk.WindowPosition.CENTER)
        path = os.path.dirname(os.path.abspath(__file__)).strip('librairy')
        self.set_default_icon_from_file(path+'/resources/icons.png')

        # get two button to switch between view
        button_config = Gtk.ToolButton.new_from_stock(Gtk.STOCK_PREFERENCES)
        button_config.set_label(_("Setup"))
        button_config.set_is_important(True)
        button_config.set_tooltip_text(_('Open setup window'))
        button_config.show() 
        button_config.connect("clicked",self.change_page,1)
        
        button_back = Gtk.Button.new_from_stock(Gtk.STOCK_OK)
        button_back.connect("clicked",self.change_page,0)
        button_cancel = Gtk.Button.new_from_stock(Gtk.STOCK_CANCEL)
        button_cancel.connect("clicked",self.change_page,0)
        
        # get the main view 
        content = add_window(button_config)
        label_main = Gtk.Label("main")
        config = SetupWindow(button_back,button_cancel)
        label_config = Gtk.Label("config")
        
        # create a Gtk.Notebook to store both page
        self.notebook = Gtk.Notebook.new()
        self.notebook.set_show_tabs(False)   
        self.notebook.append_page(content.get_grid(),label_main)
        self.notebook.append_page(config.getGrid(),label_config)
        
        # show
        self.add(self.notebook)
        self.show_all()

    def change_page(self,button,page):
        self.notebook.set_current_page(page)

########NEW FILE########
__FILENAME__ = moduleSelection
#!/usr/bin/env python
# -*- coding: utf-8 -*-  
from gi.repository import Gtk
from gi.repository import Notify
from gi.repository import Gdk
from gi.repository import Gio
from os.path import expanduser
import os, sys, subprocess, gettext

# gère l'apparition de la fenêtre de choix du module
class moduleSelection():
    """
    @description: This class display an fileChooserDialog when the user 
    wants to add a new module from the menu of the main window
    """
    def __init__(self):
        w=Gtk.Window()
        dialog = Gtk.FileChooserDialog(_("Choose a file"), w,Gtk.FileChooserAction.OPEN,(Gtk.STOCK_CANCEL, Gtk.ResponseType.CANCEL,Gtk.STOCK_OPEN, Gtk.ResponseType.OK))        
        dialog.set_default_size(800, 400)

        response = dialog.run()
        self.module = '-1'
        if response == Gtk.ResponseType.OK:
            self.module=dialog.get_filename()
        elif response == Gtk.ResponseType.CANCEL:
            print("Cancel clicked")

        dialog.destroy()
    
    def getModule(self):
        """
        @description: return the module selected
        
        @return: return the path to the executable of the module
        """
        return self.module

########NEW FILE########
__FILENAME__ = osd
#!/usr/bin/env python
# -*- coding: utf-8 -*-
from gi.repository import Gtk
from gi.repository import Gdk
from gi.repository import Notify
from os.path import expanduser
from localehelper import LocaleHelper
import time, os, gettext, sys, locale

path = os.path.dirname(os.path.abspath(__file__)).strip('librairy')
localeHelper = LocaleHelper()
lang = localeHelper.getLocale()
t=gettext.translation('google2ubuntu',path+'i18n/',languages=[lang])
t.install()

#keep the old way for the moment
#gettext.install('google2ubuntu',path+'/i18n/')
RESULT = False
path += 'resources'


if len(sys.argv) >= 2:
    PID = sys.argv[1]
    # nom des fichiers
    start='/tmp/g2u_start_'+PID
    stop='/tmp/g2u_stop_'+PID
    result='/tmp/g2u_result_'+PID
    cmd='/tmp/g2u_cmd_'+PID
    error='/tmp/g2u_error_'+PID
    display='/tmp/g2u_display_'+PID


    # initialisation
    Notify.init("google2ubuntu")
    n = Notify.Notification.new('google2ubuntu',_('Ready'),path+"/icons.png")
    n.set_urgency(Notify.Urgency.CRITICAL)    
    n.show()

    while os.path.exists(start) == False:
        n.update('google2ubuntu',_('Ready'), path+"/icons.png")
        n.show()
        time.sleep(0.5)

    i = 0    
    delay=0.1
    while os.path.exists(stop) == False:
        if os.path.exists(error):
            f = open(error,"r")
            title = _('Error')
            body = f.readline().rstrip('\n')
            f.close
            n.update(title, body,icon = path+"/error.png")
            n.show()
            time.sleep(2)
            n.close()
            os.system('rm /tmp/g2u_*_'+PID+' 2>/dev/null')
            sys.exit(1)
            
        if os.path.exists(result) and RESULT == False:
            f = open(result,"r")
            title=_('Recognition result')
            body = f.readline().rstrip('\n')
            icon = path+"/icons.png"
            f.close()
            delay = 2
            RESULT = True
        elif os.path.exists(cmd) and RESULT == True:
            if os.path.exists(result):
                os.system('rm '+result)
            f = open(cmd,"r")
            title = _('Calling command')
            body = f.readline().rstrip('\n')
            icon = path+"/icons.png"
            delay = 2
            f.close()
        elif os.path.exists(display):
            f = open(display,"r")
            title = _('Information')
            body = f.readline().rstrip('\n')
            f.close
            icon = path+"/icons.png"
            delay=3
        else:
            title = _('Performing recording')
            body = _('Please speak')
            icon = path+"/Waiting/wait-"+str(i)+".png"
    
        n.update(title, body, icon)
        n.show()
        time.sleep(delay)
        i += 1;
        if i > 17:
            i = 0    

    n.update("google2ubuntu",_('Done'),path+"/icons.png")
    n.show()
    time.sleep(1)
    n.close()
    os.system('rm /tmp/g2u_*_'+PID+' 2>/dev/null')

########NEW FILE########
__FILENAME__ = stringParser
#!/usr/bin/env python
# -*- coding: utf-8 -*-
from os.path import expanduser
from workWithModule import workWithModule
from basicCommands import basicCommands
from Googletts import tts
import xml.etree.ElementTree as ET
import os, gettext, time, sys, subprocess

# Permet d'exécuter la commande associée à un mot prononcé
class stringParser():
    """
    @description: This class parses the text retrieve by Google in order 
    to distinguish external commands, internal commands and modules
    """
    def __init__(self,text,File,PID):
        # read configuration files
        self.pid=PID
        try:
            max = 0
            text=text.lower()
            tree = ET.parse(File)
            root = tree.getroot()
            tp = ''
            # si le mode dictée est activé
            if os.path.exists('/tmp/g2u_dictation'):
                for entry in root.findall('entry'):
                    if entry.get('name') == _('internal') and entry.find('command').text == unicode(_('exit dictation mode'),"utf8"):
                        score = 0
                        Type=entry.get('name')
                        Key=entry.find('key').text
                        Command=entry.find('command').text
                        key=Key.split(' ')
                        for j in range(len(key)):
                            score += text.count(key[j])
                        
                        if score == len(key):
                            do = Command
                            tp = Type
                        else:
                            do = text
            else:
                for entry in root.findall('entry'):
                    score = 0
                    Type=entry.get('name')
                    Key=entry.find('key').text
                    Command=entry.find('command').text
                    Linker = entry.find('linker').text
                    Spacebyplus = entry.find('spacebyplus').text
                    
                    key=Key.split(' ')
                    for j in range(len(key)):
                        score += text.count(key[j])
                        
                    if max < score:
                        max = score
                        do = Command
                        tp = Type
                        linker = Linker
                        spacebyplus = Spacebyplus
            
            do = do.encode('utf8') 
            tp = tp.encode('utf8')
            
            print 'key', tp
            print 'command', do
            
            os.system('echo "'+do+'" > /tmp/g2u_cmd_'+self.pid)
            if _('modules') in tp:
                # si on trouve le mot "modules", on instancie une classe workWithModule et on lui passe
                # le dossier ie weather, search,...; le nom du module ie weather.sh, search.sh et le texte prononcé 
                linker = linker.encode('utf8')
                spacebyplus = spacebyplus.encode('utf8')
                wm = workWithModule(do,text,linker,spacebyplus,self.pid)
            elif _('internal') in tp:
                # on execute une commande intene, la commande est configurée
                # ainsi interne/batterie, on envoie batterie à la fonction
                b = basicCommands(do,self.pid)
            elif _('external') in tp:
                os.system(do+' &')
            else:
                os.system('xdotool type "'+do+'"')
                
            os.system('> /tmp/g2u_stop_'+self.pid)
            
            
        except Exception as e:
            message = _('Setup file missing')
            os.system('echo "'+message+'" > /tmp/g2u_error_'+self.pid)
            sys.exit(1)   

########NEW FILE########
__FILENAME__ = workWithModule
#!/usr/bin/env python
# -*- coding: utf-8 -*-
from os.path import expanduser
from subprocess import *
from Googletts import tts
import os, gettext, time, subprocess, unicodedata

gettext.install('google2ubuntu',os.path.dirname(os.path.abspath(__file__))+'/i18n/')

# Permet de faire appel aux modules    
class workWithModule():
    """
    @description: This class allows you to call external modules. If a call
    for an external module is detected by the parser then this class check
    the module's config file before extracting modules's parameter from the
    text you have pronounced
    """
    def __init__(self,module_name,text,linker,plus,PID):
        self.pid = PID
        
        try:
            # on utilise un mot de liaison pour séparer l'appel du module
            # des arguments à lui envoyer
            # ex: Quelle est la météo à Paris
            #     Quelle est la météo à Issy les moulineaux
            #
            # Le mot de liaison peut être " à "
            sentence=text.lower()
            # oblige to put this .encode('ASCII', 'ignore') for french
            print sentence
            sentence = unicodedata.normalize('NFKD', sentence)
            print sentence
            sentence=sentence.encode('ASCII', 'ignore')
            print sentence
            sentence=sentence.lower()  
            
            if sentence.count(linker) > 0:
                param =(sentence.split(linker,1)[1]).encode("utf-8")

                # on regarde si l'utilisateur veut transformer les ' ' en +
                if plus == '1':
                    param=param.replace(' ','+')
                print param
                # commande qui sera exécutée    
                execute = expanduser('~')+'/.config/google2ubuntu/modules/'+module_name+' '+'"'+param+'" &'
                os.system(execute)
            else:
                message=_("you didn't say the linking word")   
                os.system('echo "'+message+'" > /tmp/g2u_error_'+self.pid)      
            
        except IOError:
            message = _('args file missing')
            os.system('echo "'+message+'" > /tmp/g2u_error_'+self.pid)
            sys.exit(1) 

########NEW FILE########
__FILENAME__ = listener
# Okay Google hotword activation script
# Josh Chen, 14 Feb 2014
# Feel free to modify as you need

#!/usr/bin/env python
# -*- coding: utf-8 -*-
from subprocess import *
from os.path import expanduser
import sys, subprocess, os, json, urllib2, unicodedata, time, gettext, locale, gettext

p = os.path.dirname(os.path.abspath(__file__))

sys.path.append( p +'/librairy')
from localehelper import LocaleHelper

localeHelper = LocaleHelper()
lang = localeHelper.getLocale()

t=gettext.translation('google2ubuntu',p +'/i18n/',languages=[lang])
t.install()

hotword = _('ok start')
config_file = expanduser('~') + '/.config/google2ubuntu/google2ubuntu.conf'
try:
    if os.path.exists(config_file):
        f=open(config_file,'r')
        for line in f.readlines():
            line = line.strip('\n')
            field = line.split('=')
            if field[0] == 'hotword':  
                hotword = field[1].replace('"','')
        f.close()
except Exception:
    print "Error loading", config_file
    sys.exit(1)


# lecture du fichier audio
filename='/tmp/pingvox.flac'
f = open(filename)
data = f.read()
f.close()

try:
    # Send request to Google
    fail = 'req'
    req = urllib2.Request('https://www.google.com/speech-api/v1/recognize?xjerr=1&client=chromium&lang='+lang, data=data, headers={'Content-type': 'audio/x-flac; rate=16000'})
    
    fail = 'ret'
    # Return request
    ret = urllib2.urlopen(req)
    
    # Google translate API sometimes returns lists of phrases. We'll join them all up into a single phrase again
    phrase = ''
    t = ret.read().split('\n')
    t.remove('')
    for i in t:
        s = json.loads(i)
        if len(s['hypotheses']) > 0:
            phrase = phrase + s['hypotheses'][0]['utterance'] + ' '
    print "Recognition: "+phrase
        
    fail = 'parse'
    # Parse
    #text=json.loads(d)['hypotheses'][0]['utterance']
    
    print "hotword:", hotword
    print "detected:", phrase   
    if phrase.lower().count(hotword.lower()) > 0: 
        os.system('python ' + p + '/google2ubuntu.py')

except Exception:
    os.system('echo Fail:'+fail) # for debugging
    #message = _('unable to translate')
    if fail == 'req':
        message = _('Cannot connect to Google Translate')
    elif fail == 'parse':
        message = _('Phrase parsing failed')
    elif fail == 'ret':
        message = _('Error processing value returned by Google Translate')
    
    print message
    sys.exit(1)

########NEW FILE########
__FILENAME__ = goto
#!/usr/bin/env python
# -*- coding: utf-8 -*-

import sys,os, re

if len(sys.argv) >= 2:
    web = sys.argv[1]
    web = web.replace(' ','+')
    web = web.lower()
    
    url = 'www.'+web
    os.system('xdg-open '+url+' &')

########NEW FILE########
__FILENAME__ = meaning
#!/usr/bin/env python
# -*- coding: utf-8 -*-
from subprocess import *
from os.path import expanduser
import sys, subprocess, os, json, unicodedata, time, locale
from urllib2 import urlopen

locale.setlocale(locale.LC_ALL, '')
lang = locale.getdefaultlocale()[0]
lang=lang.split('_')[0]

sys.path.append('/usr/share/google2ubuntu/librairy')
from Googletts import tts

if len(sys.argv) >= 2:
    null = None
    keyword = sys.argv[1]
    #keyword = keyword.replace(' ','+')
    print keyword
    data = urlopen("http://www.google.com/dictionary/json?callback=dict_api.callbacks.id100&q="+keyword+"&sl="+lang+"&tl="+lang+"&restrict=pr%2Cde&client=te").read()[25:-1]
 
    d = eval('('+data+')')
    if d[1] == 200:
        result = d[0]
          
        if 'webDefinitions' in result:
            webd = result.get('webDefinitions')[0]
            entries = webd.get('entries')
            entry=entries[0]
            for term in entry.get('terms'):
                if term.get('type') == 'text':
                    tts(term.get('text'))

########NEW FILE########
