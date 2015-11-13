__FILENAME__ = appselector
import imp
from gi.repository import GObject, Gtk

class AppSelector(Gtk.VBox):
    __gtype_name__ = "DjangoProjectAppSelector"
    def __init__(self, settings_module=None):
        Gtk.VBox.__init__(self, homogeneous=False, spacing=0) 
        self._model = Gtk.ListStore(GObject.TYPE_INT, GObject.TYPE_STRING)
        treeview = Gtk.TreeView.new_with_model(self._model)
        treeview.set_headers_visible(False)
        column = Gtk.TreeViewColumn("Apps")
        cell = Gtk.CellRendererToggle()
        cell.set_activatable(True)
        cell.connect("toggled", self.on_toggled, (self._model, 0))
        column.pack_start(cell, False)
        column.add_attribute(cell, "active", 0)
        cell = Gtk.CellRendererText()
        column.pack_start(cell, True)
        column.add_attribute(cell, "text", 1)
        treeview.append_column(column)
        scrolled = Gtk.ScrolledWindow()
        scrolled.set_policy(Gtk.PolicyType.AUTOMATIC, Gtk.PolicyType.AUTOMATIC)
        scrolled.add(treeview)
        scrolled.set_shadow_type(Gtk.ShadowType.IN)
        scrolled.show_all()
        self.pack_start(scrolled, True, True, 0)
        if settings_module:
            self.load_from_settings(settings_module)
    
    def load_from_settings(self, settings_module):
        [self._model.append((False, app,)) for app in settings_module.INSTALLED_APPS]
    
    def get_selected(self, short_names=True):
        selected = []
        if short_names:
            [selected.append(row[1][row[1].rfind(".")+1:]) for row in self._model if row[0]]
        else:
            [selected.append(row[1]) for row in self._model if row[0]]
        return selected
            
    def on_toggled(self, renderer, path, data=None):
        model, column = data
        model[path][column] = not model[path][column]
        

########NEW FILE########
__FILENAME__ = output
import os
import subprocess
import shlex
import logging
from gi.repository import GObject, Gtk, GLib, Pango

logging.basicConfig()
LOG_LEVEL = logging.ERROR
logger = logging.getLogger(__name__)
logger.setLevel(LOG_LEVEL)

class OutputBox(Gtk.HBox):
    """
    A widget to display the output of running django commands.    
    """
    __gtype_name__ = "DjangoProjectOutputBox"
    
    def __init__(self):
        Gtk.HBox.__init__(self, homogeneous=False, spacing=4) 
        # configurable options
        self.cwd = None
        self._last_output = None
        scrolled = Gtk.ScrolledWindow()
        self._view = self._create_view()
        scrolled.add(self._view)
        self.pack_start(scrolled, True, True, 0)
        self.set_font("monospace 10")
        self.show_all()
    
    def _create_view(self):
        """ Create the gtk.TextView used for shell output """
        view = Gtk.TextView()
        view.set_editable(False)
        buff = view.get_buffer()
        buff.create_tag('bold', foreground='#7F7F7F', weight=Pango.Weight.BOLD)
        buff.create_tag('info', foreground='#7F7F7F', style=Pango.Style.OBLIQUE)
        buff.create_tag('error', foreground='red')
        return view
    
    def get_last_output(self):
        return self._last_output
        
    def set_font(self, font_name):
        font_desc = Pango.FontDescription(font_name)
        self._view.modify_font(font_desc)
        
    def run(self, command, cwd=None):
        """ Run a command inserting output into the gtk.TextView """
        self.insert("Running: ", 'info')
        self.insert("%s\n" % command, 'bold')
        args = shlex.split(command)
        output = None
        if cwd is None:
            cwd = self.cwd
        logger.debug(cwd)
        process = subprocess.Popen(args, 0, 
                                   shell=False, 
                                   stdout=subprocess.PIPE, 
                                   stderr=subprocess.PIPE, 
                                   cwd=cwd)
        output = process.communicate()
        if output[0]:
            self.insert(output[0])
            self._last_output = output[0]
        if output[1]:
            self.insert(output[1], 'error')
        
        self.insert("\nExit: ", 'info')
        self.insert("%s\n\n" % process.returncode, 'bold')
        
        if output[1] and process.returncode <> 0:
            raise Exception(output[1])
    
    def insert(self, text, tag_name=None):
        """ Insert text, apply tag, and scroll to end iter """
        buff = self._view.get_buffer()
        end_iter = buff.get_end_iter()
        buff.insert(end_iter, "%s" % text)
        if tag_name:
            offset = buff.get_char_count() - len(text)
            start_iter = buff.get_iter_at_offset(offset)
            end_iter = buff.get_end_iter()
            buff.apply_tag_by_name(tag_name, start_iter, end_iter)
        while Gtk.events_pending():
            Gtk.main_iteration()
        self._view.scroll_to_iter(buff.get_end_iter(), 0.0, True, 0.0, 0.0)
        

########NEW FILE########
__FILENAME__ = plugin
import os
import logging
from gi.repository import GObject, Gtk, Gedit, Gio, GdkPixbuf
from project import DjangoProject
from server import DjangoServer
from output import OutputBox
from shell import Shell
from appselector import AppSelector

logging.basicConfig()
LOG_LEVEL = logging.DEBUG
logger = logging.getLogger(__name__)
logger.setLevel(LOG_LEVEL)

DATA_DIR = os.path.join(os.path.dirname(__file__), 'data')
STOCK_DBSHELL = "dbshell"
STOCK_SERVER = "server"
STOCK_PYTHON = "python"

class Plugin(GObject.Object, Gedit.WindowActivatable):
    __gtype_name__ = "GeditDjangoProjectPlugin"
    window = GObject.property(type=Gedit.Window)
    
    def __init__(self):
        GObject.Object.__init__(self)
        self._project = None
        self._server = None
        self._output = None
        self._shell = None
        self._dbshell = None
        self._install_stock_icons()
        self._admin_cmd = "django-admin.py" 
        self._manage_cmd = "python manage.py"
        self._font = "monospace 10"
    
    def _add_dbshell_panel(self):
        """ Adds a database shell to the bottom pane. """
        logger.debug("Adding database shell panel.")
        self._dbshell = Shell()
        self._dbshell.set_font(self._font)
        panel = self.window.get_bottom_panel()
        panel.add_item_with_stock_icon(self._dbshell, "DjangoDbShell", 
                                       "Database Shell", STOCK_DBSHELL)
        self._setup_dbshell_panel()
        panel.activate_item(self._dbshell)
                                       
    def _add_output_panel(self):
        """ Adds a widget to the bottom pane for django command output. """
        self._output = OutputBox()
        self._output.set_font(self._font)
        panel = self.window.get_bottom_panel()
        panel.add_item_with_stock_icon(self._output, "DjangoOutput", 
                                       "Django Output", Gtk.STOCK_EXECUTE)
        
    def _add_server_panel(self, cwd=None):
        """ Adds a VTE widget to the bottom pane for development server. """
        logger.debug("Adding server panel.")
        self._server = DjangoServer()
        self._server.set_font(self._font)
        self._server.command = "%s runserver" % (self._manage_cmd)
        if cwd:
            self._server.cwd = cwd
        self._server.connect("server-started", self.on_server_started)
        self._server.connect("server-stopped", self.on_server_stopped)
        panel = self.window.get_bottom_panel()
        panel.add_item_with_stock_icon(self._server, "DjangoServer", 
                                       "Django Server", STOCK_SERVER)
        self._setup_server_panel()
    
    def _add_shell_panel(self):
        """ Adds a python shell to the bottom pane. """
        logger.debug("Adding shell.")
        self._shell = Shell()
        self._shell.set_font(self._font)
        panel = self.window.get_bottom_panel()
        panel.add_item_with_stock_icon(self._shell, "DjangoShell", 
                                       "Python Shell", STOCK_PYTHON)
        self._setup_shell_panel()
        panel.activate_item(self._shell)
                                       
    def _add_ui(self):
        """ Merge the 'Django' menu into the Gedit menubar. """
        ui_file = os.path.join(DATA_DIR, 'menu.ui')
        manager = self.window.get_ui_manager()
        
        # global actions are always sensitive
        self._global_actions = Gtk.ActionGroup("DjangoGlobal")
        self._global_actions.add_actions([
            ('Django', None, "_Django", None, None, None),
            ('NewProject', Gtk.STOCK_NEW, "_New Project...", 
                "<Shift><Control>N", "Start a new Django project.", 
                self.on_new_project_activate),
            ('OpenProject', Gtk.STOCK_OPEN, "_Open Project", 
                "<Shift><Control>O", "Open an existing Django project.", 
                self.on_open_project_activate),
            ('NewApp', Gtk.STOCK_NEW, "New _App...", 
                "<Shift><Control>A", "Start a new Django application.", 
                self.on_new_app_activate),
        ])
        self._global_actions.add_toggle_actions([
            ('ViewServerPanel', None, "Django _Server", 
                None, "Add the Django development server to the bottom panel.", 
                self.on_view_server_panel_activate, True),
            ('ViewPythonShell', None, "_Python Shell", 
                None, "Add a Python shell to the bottom panel.", 
                self.on_view_python_shell_panel_activate, False),
            ('ViewDbShell', None, "_Database Shell", 
                None, "Add a Database shell to the bottom panel.", 
                self.on_view_db_shell_panel_activate, False),
        ])
        manager.insert_action_group(self._global_actions)       
        
        # project actions are sensitive when a project is open
        self._project_actions = Gtk.ActionGroup("DjangoProject")
        self._project_actions.add_actions([
            ('CloseProject', Gtk.STOCK_CLOSE, "_Close Project...", 
                "", "Close the current Django project.", 
                self.on_close_project_activate),
            ('Manage', None, "_Manage", None, None, None),
            ('SyncDb', Gtk.STOCK_REFRESH, "_Synchronize Database", None, 
                "Creates the database tables for all apps whose tables have not already been created.", 
                self.on_manage_command_activate),
            ('Cleanup', None, "_Cleanup", None, 
                "Clean out old data from the database.", 
                self.on_manage_command_activate),
            ('DiffSettings', None, "Di_ff Settings", None, 
                "Displays differences between the current settings and Django's default settings.", 
                self.on_manage_command_activate),
            ('InspectDb', None, "_Inspect Database", None, 
                "Introspects the database and outputs a Django model module.", 
                self.on_manage_command_activate),
            ('Flush', None, "_Flush", None, 
                "Returns the database to the state it was in immediately after syncdb was executed.", 
                self.on_manage_command_activate),
                # all clear custom flush
            ('Sql', None, "S_QL...", None, 
                "Prints the CREATE TABLE SQL statements for the given app name(s).", 
                self.on_manage_app_select_command_activate),
            ('SqlAll', None, "SQL _All...", None, 
                "Prints the CREATE TABLE and initial-data SQL statements for the given app name(s).", 
                self.on_manage_app_select_command_activate),
            ('SqlClear', None, "SQL C_lear...", None, 
                "Prints the DROP TABLE SQL statements for the given app name(s).", 
                self.on_manage_app_select_command_activate),
            ('SqlCustom', None, "SQL C_ustom...", None, 
                "Prints the custom SQL statements for the given app name(s).", 
                self.on_manage_app_select_command_activate),
            ('SqlFlush', None, "S_QL Flush", None, 
                "Prints the SQL statements that would be executed for the flush command.", 
                self.on_manage_command_activate),
            ('SqlIndexes', None, "SQL _Indexes...", None, 
                "Prints the CREATE INDEX SQL statements for the given app name(s).", 
                self.on_manage_app_select_command_activate),
            ('SqlSequenceReset', None, "SQL Sequence Rese_t...", None, 
                "Prints the SQL statements for resetting sequences for the given app name(s).", 
                self.on_manage_app_select_command_activate),
            ('Validate', None, "_Validate", None, 
                "Validates all installed models.", 
                self.on_manage_command_activate),
            ('LoadData', None, "_Load Data...", None, 
                "Loads the contents of fixtures into the database.", 
                self.on_manage_load_data_activate),
            ('DumpData', None, "_Dump Data...", None, 
                "Outputs all data in the database associated with the named application(s).", 
                self.on_manage_app_select_command_activate),
        ])
        self._project_actions.add_toggle_actions([
            ('RunServer', None, "_Run Development Server", 
                "<Shift>F5", "Start/Stop the Django development server.", 
                self.on_manage_runserver_activate, False),
        ])
        self._project_actions.set_sensitive(False)
        manager.insert_action_group(self._project_actions)   
        
        self._ui_merge_id = manager.add_ui_from_file(ui_file)
        manager.ensure_update()
    
    def close_project(self):
        self._project = None
        self._server.stop()
        self._server.cwd = None
        self._server.refresh_ui()
        if self._shell:
            self._shell.kill()
        if self._dbshell:
            self._dbshell.kill()
        self._project_actions.set_sensitive(False)
        self._update_run_server_action()
    
    def confirmation_dialog(self, message):
        """ Display a very basic informative Yes/No dialog. """
        dialog = Gtk.MessageDialog(self.window,
                                   Gtk.DialogFlags.MODAL | 
                                   Gtk.DialogFlags.DESTROY_WITH_PARENT,
                                   Gtk.MessageType.QUESTION, Gtk.ButtonsType.YES_NO,  
                                   message)
        dialog.set_title("Confirm")
        response = dialog.run()
        dialog.destroy()
        
        if response == Gtk.ResponseType.YES: 
            return True
        else:
            return False
            
    def do_activate(self):
        logger.debug("Activating plugin.")
        self._add_ui()
        self._add_output_panel()
        self._add_server_panel()

    def do_deactivate(self):
        logger.debug("Deactivating plugin.")
        self._remove_ui()
        self._remove_output_panel()
        self._remove_server_panel()
        self._remove_shell_panel()
        self._remove_dbshell_panel()

    def do_update_state(self):
        pass
    
    def error_dialog(self, message):
        """ Display a very basic error dialog. """
        logger.warn(message)
        dialog = Gtk.MessageDialog(self.window,
                                   Gtk.DialogFlags.MODAL | 
                                   Gtk.DialogFlags.DESTROY_WITH_PARENT,
                                   Gtk.MessageType.ERROR, Gtk.ButtonsType.OK, 
                                   message)
        dialog.set_title("Error")
        dialog.run()
        dialog.destroy()
    
    def _install_stock_icons(self):
        """ Register custom stock icons used on the tabs. """
        logger.debug("Installing stock icons.")
        icons = (STOCK_PYTHON, STOCK_DBSHELL, STOCK_SERVER)
        factory = Gtk.IconFactory()
        for name in icons:
            filename = name + ".png"
            pixbuf = GdkPixbuf.Pixbuf.new_from_file(os.path.join(DATA_DIR, "icons", filename))
            iconset = Gtk.IconSet.new_from_pixbuf(pixbuf)
            factory.add(name, iconset)
        factory.add_default()
    
    def new_app(self, path, name):
        """ Runs the 'startapp' Django command. """ 
        try:
            self.run_admin_command("startapp %s" % name, path)
        except Exception as e:
            self.error_dialog(str(e))
            
    def new_dialog(self, title):
        filename = os.path.join(DATA_DIR, 'dialogs.ui')
        path = name = None
        builder = Gtk.Builder()
        try:
            builder.add_from_file(filename)
        except Exception as e:
            logger.error("Failed to load %s: %s." % (filename, str(e)))
            return 
        dialog = builder.get_object('new_dialog')
        if not dialog:
            logger.error("Could not find 'new_dialog' widget in %s." % filename)
            return
        dialog.set_transient_for(self.window)
        dialog.set_default_response(Gtk.ResponseType.OK)
        dialog.set_title(title)
        response = dialog.run()
        if response == Gtk.ResponseType.OK:
            name_widget = builder.get_object('name')
            project_widget = builder.get_object('directory')
            name = name_widget.get_text()
            path = project_widget.get_filename()
        dialog.destroy()
        
        return (name, path)
    
    def new_project(self, path, name):
        """ Runs the 'startproject' Django command and opens the project. """ 
        try:
            self.run_admin_command("startproject %s" % name, path)
        except Exception as e:
            self.error_dialog(str(e))
            return
        
        self.open_project(os.path.join(path, name))
    
    def new_tab_from_output(self):
        message = "Do you want to create a new document with the output?"
        if not self.confirmation_dialog(message):
            return
        tab = self.window.create_tab(False)
        buff = tab.get_view().get_buffer()
        end_iter = buff.get_end_iter()
        buff.insert(end_iter, self._output.get_last_output())
        self.window.set_active_tab(tab)
            
    def on_close_project_activate(self, action, data=None):
        self.close_project()
   
    def on_manage_command_activate(self, action, data=None):
        """ Handles simple manage.py actions. """
        command = action.get_name().lower()
        if command in ('syncdb', 'flush'):
            command += ' --noinput'
        try:
            self.run_management_command(command)
        except:
            pass # errors show up in output
        
        if command in ('inspectdb', 'sqlflush', 'diffsettings'):
            self.new_tab_from_output()
    
    def on_manage_app_select_command_activate(self, action, data=None):
        dialog = Gtk.Dialog("Select apps...",
                            self.window,
                            Gtk.DialogFlags.MODAL | 
                            Gtk.DialogFlags.DESTROY_WITH_PARENT,
                            (Gtk.STOCK_CANCEL, Gtk.ResponseType.CANCEL, 
                            Gtk.STOCK_OK, Gtk.ResponseType.OK))
        dialog.set_default_size(300, 200)
        selector = AppSelector()
        selector.show_all()
        try:
            selector.load_from_settings(self._project.get_settings_module())
        except Exception as e:
            self.error_dialog("Error getting app list: %s" % str(e))
        box = dialog.get_content_area()
        box.set_border_width(10)
        box.pack_start(selector, True, True, 0)
        response = dialog.run()
        if response == Gtk.ResponseType.OK:
            files = selector.get_selected()
            command = action.get_name().lower()
            full_command = "%s %s" % (command, " ".join([f for f in files]) )
            try:
                self.run_management_command(full_command)
            except Exception as e:
                self.error_dialog(str(e))
        dialog.destroy()
        
        # only after the dialog is destroyed do we prompt them for a new tab
        if response == Gtk.ResponseType.OK:
            if command[:3] == "sql" or command in ('dumpdata'):
                self.new_tab_from_output()
        
    def on_manage_load_data_activate(self, action, data=None):
        """ Prompt user for fixtures to load into database. """
        dialog = Gtk.FileChooserDialog("Select fixtures...",
                                       self.window,
                                       Gtk.FileChooserAction.OPEN,
                                       (Gtk.STOCK_CANCEL, Gtk.ResponseType.CANCEL, 
                                       Gtk.STOCK_OPEN, Gtk.ResponseType.OK))
        dialog.set_select_multiple(True)
        if self._project:
            dialog.set_filename(self._project.get_path())
        response = dialog.run()
        if response == Gtk.ResponseType.OK:
            files = dialog.get_files()
            command = "loaddata "+" ".join([f.get_path() for f in files]) 
            try:
                self.run_management_command(command)
            except Exception as e:
                self.error_dialog(str(e))
            
        dialog.destroy()
         
    def on_manage_runserver_activate(self, action, data=None):
        """ Run Django development server. """
        if not self._server:
            return
        try:
            if not action.get_active() and self._server.is_running():
                self._server.stop()
            elif action.get_active() and not self._server.is_running():
                self._server.start()
        except Exception as e:
            self.error_dialog(str(e))
            return
        
    def on_new_app_activate(self, action, data=None):
        """ Prompt user for new app name and directory """
        name, path = self.new_dialog("New Django App")
        if name and path:
            self.new_app(path, name)
            
    def on_new_project_activate(self, action, data=None):
        """ Prompt user for new project name and directory """
        name, path = self.new_dialog("New Django Project")
        if name and path:
            self.new_project(path, name)
    
    def on_open_project_activate(self, action, data=None):
        """ Prompt the user for the Django project directory. """
        path = None
        dialog = Gtk.FileChooserDialog("Select project folder...", self.window,
                                       Gtk.FileChooserAction.SELECT_FOLDER,
                                       (Gtk.STOCK_CANCEL, Gtk.ResponseType.CANCEL, 
                                        Gtk.STOCK_OPEN, Gtk.ResponseType.OK))
        response = dialog.run()
        if response == Gtk.ResponseType.OK: 
            path = dialog.get_filename()
        dialog.destroy()
        if path:
            self.open_project(path)
    
    def on_server_started(self, server, pid, data=None):
        self._project_actions.get_action("RunServer").set_active(True)
        panel = self.window.get_bottom_panel()
        panel.activate_item(self._server)
                
    def on_server_stopped(self, server, pid, data=None):
        self._project_actions.get_action("RunServer").set_active(False)
        panel = self.window.get_bottom_panel()
        panel.activate_item(self._server)
    
    def on_view_db_shell_panel_activate(self, action, data=None):
        """ Show/Hide database shell from main menu. """
        if action.get_active():
            self._add_dbshell_panel()
        else:
            self._remove_dbshell_panel()
        
    def on_view_python_shell_panel_activate(self, action, data=None):
        """ Show/Hide python shell from main menu. """
        if action.get_active():
            self._add_shell_panel()
        else:
            self._remove_shell_panel()
        
    def on_view_server_panel_activate(self, action, data=None):
        """ Show/Hide development server from main menu. """
        if action.get_active():
            self._add_server_panel()
        else:
            self._remove_server_panel()
        self._update_run_server_action()
        
    def open_project(self, path):
        logger.debug("Opening Django project: %s" % path)
        if self._project:
            self.close_project()
        try:
            self._project = DjangoProject(path)
        except IOError as e:
            self.error_dialog("Could not open project: %s" % str(e))
            return

        self._output.cwd = self._project.get_path()
        self._setup_server_panel()
        self._setup_shell_panel()
        self._setup_dbshell_panel()
        self._project_actions.set_sensitive(True)
        self._update_run_server_action()
        
        # print version as it may have changed due to virtualenv
        try:
            #command = "%s --version" % (self._admin_cmd)
            #self._output.run(command)
            self.run_admin_command("--version" , path)
        except:
            pass

    def _setup_dbshell_panel(self):
        if self._dbshell and self._project:
            self._dbshell.cwd = self._project.get_path()
            self._dbshell.command = "%s dbshell" % self._manage_cmd
            self._dbshell.run()
    
    def _setup_server_panel(self):
        if self._server and self._project:
            self._server.cwd = self._project.get_path()
            self._server.refresh_ui()
        
    def _setup_shell_panel(self):
        if self._shell and self._project:
            self._shell.cwd = self._project.get_path()
            self._shell.command = "%s shell" % self._manage_cmd
            self._shell.run()
        
    def _remove_output_panel(self):
        """ Remove the output box from the bottom panel. """
        logger.debug("Removing output panel.")
        if self._output:
            self._remove_panel(self._output)
            self._output = None
    
    def _remove_panel(self, item):
        panel = self.window.get_bottom_panel()
        panel.remove_item(item)
        
    def _remove_server_panel(self):
        """ Stop and remove development server panel from the bottom panel. """
        if self._server:
            logger.debug("Removing server panel.")
            self._server.stop()
            self._remove_panel(self._server)
            self._server = None
            
    
    def _remove_shell_panel(self):
        """ Remove python shell from bottom panel. """
        if self._shell:
            logger.debug("Removing shell panel.")
            self._remove_panel(self._shell)
            self._shell = None
    
    def _remove_dbshell_panel(self):
        """ Remove database shell from bottom panel. """
        if self._dbshell:
            logger.debug("Removing database shell panel.")
            self._remove_panel(self._dbshell)
            self._dbshell = None
            
    def _remove_ui(self):
        """ Remove the 'Django' menu from the the Gedit menubar. """
        manager = self.window.get_ui_manager()
        manager.remove_ui(self._ui_merge_id)
        manager.remove_action_group(self._global_actions)
        manager.remove_action_group(self._project_actions)
        manager.ensure_update()
    
    def run_admin_command(self, command, path=None):
        """ Run a django-admin.py command in the output panel. """
        self.window.get_bottom_panel().activate_item(self._output)
        full_command = "%s %s" % (self._admin_cmd, command)
        deb_command =  "%s %s" % (self._admin_cmd[0:-3], command)
        original_cwd = self._output.cwd
        self._output.cwd = path
        try:
            self._output.run(full_command)
        except OSError:
            try: 
                # try without ".py" for debian/ubuntu system installs
                print(deb_command)
                self._output.run(deb_command)
            except:
                raise Exception("Could not execute django-admin.py command.\nIs Django installed?")
        finally:
            self._output.cwd = original_cwd
            
    def run_management_command(self, command):
        """ Run a manage.py command in the output panel. """
        self.window.get_bottom_panel().activate_item(self._output)
        full_command = "%s %s" % (self._manage_cmd, command)
        self._output.run(full_command)
    
    def _update_run_server_action(self):
        if not self._server or not self._project:
            self._project_actions.get_action("RunServer").set_sensitive(False)
        else:
            self._project_actions.get_action("RunServer").set_sensitive(True)
  
        

########NEW FILE########
__FILENAME__ = project
import os
import imp
import sys
import logging

logging.basicConfig()
LOG_LEVEL = logging.DEBUG
logger = logging.getLogger(__name__)
logger.setLevel(LOG_LEVEL)

class DjangoProject(object):
    
    def __init__(self, path):
        self.set_path(path)
        
    def close_project(self):
        sys.path.remove(self._path)
        try:
            del os.environ['DJANGO_SETTINGS_MODULE']
        except:
            pass

    def activate_virtualenv(self, path):
        """
        Activates the virtualenv if necessary. Traverses the projects path up
        to the file system root and checks if 'bin/activate_this.py' exists
        in the directories. If this file is found, it gets loaded.
        """
        parent_path = os.path.dirname(path)
        
        if parent_path == path:
            logger.debug("Virtual environment not found.")
            return

        for dirname in os.listdir(path):
            venv = os.path.join(path, dirname)
            activate_this = os.path.join(venv, 'bin', 'activate_this.py')
            if os.path.isfile(activate_this):
                imp.load_source('activate_this', activate_this)
                logger.debug("Activated virtual environment: %s" % venv)
                return
                
        self.activate_virtualenv(parent_path)
        
    def get_path(self):
        """
        Return the path to the django project (where settings.py and manage.py 
        are found).
        """
        return self._path
        
    def set_path(self, path):
        """
        Set Path
        
        Set the full filesystem path to where the Django project files are stored
        or raise IOError if the path does not exist or if settings.py or manage.py
        cannot be found in the path.
        """
        self.activate_virtualenv(path)
        
        if not os.path.exists(path):
            raise IOError("Django project directory does not exist: %s" % path)
        
        # find manage.py
        manage = os.path.join(path, 'manage.py')
        if not os.path.isfile(manage):
            raise IOError("Django manage file does not exist: %s" % manage)
        
        orig_cwd = os.getcwd()
        os.chdir(path)
        sys.path.append(path)
        
        # Load the manage module, so the DJANGO_SETTINGS_MODULE environment
        # variable gets set. Loading may fail, but setting DJANGO_SETTINGS_MODULE
        # hopefully don't.
        try:
            orig_sys_argv = sys.argv
            sys.argv = ['manage.py', '--version']

            imp.load_source('__main__', manage)
            logger.debug("Loaded manage module: %s" % manage)

            sys.argv = orig_sys_argv
        except:
            raise IOError("Django manage module could not get loaded")
        
        # set DJANGO_SETTINGS_MODULE environment variable to 'settings' if it
        # was not already set by the user or manage.py.
        os.environ.setdefault("DJANGO_SETTINGS_MODULE", "settings")

        # Now we try to load the settings module and get the file path.
        try:
            __import__(os.environ['DJANGO_SETTINGS_MODULE'], globals(), locals(), [], -1)
            mod_settings = sys.modules[os.environ['DJANGO_SETTINGS_MODULE']]
            settings = mod_settings.__file__
            logger.debug("Loaded settings module: %s" % settings)
        except:
            raise IOError("Django settings could not get loaded")

        self._path = path
        self._settings = settings
        self._mod_settings = mod_settings
        self._manage = manage

        os.chdir(orig_cwd)
        
        """
        # find settings.py in Django >= 1.4
        settings = os.path.join(path, os.path.basename(path), 'settings.py')
        if not os.path.isfile(settings):
            # find settings.py in Django < 1.4
            settings = os.path.join(path, 'settings.py')
            if not os.path.isfile(settings):
                raise IOError("Django settings file does not exist: %s" % settings)
        
        self._path = path
        self._settings = settings
        self._manage = manage
        """
    
    def get_settings_module(self):
        return self._mod_settings
        
    def get_settings_filename(self):
        return self._settings
    
    def get_manage_filename(self):
        return self._manage
        

########NEW FILE########
__FILENAME__ = server
import os
import signal
import subprocess
import shlex
import logging
from gi.repository import GObject, Gtk, Vte, GLib

logging.basicConfig()
LOG_LEVEL = logging.DEBUG
logger = logging.getLogger(__name__)
logger.setLevel(LOG_LEVEL)

class DjangoServer(Gtk.HBox):
    """
    A terminal widget setup to run the Django development server management
    command providing Start/Stop button.
    
    Start and stop the server by calling start() and stop() methods.
    
    Connect to the "server-started" and "server-stopped" signals to update UI as
    the server may stop for any number of reasons, including errors in Django
    code, pressing <CTRL+C>, or the stop button on the widget.
    """
    __gtype_name__ = "DjangoProjectServer"
    __gsignals__ = {
        "server-started": 
            (GObject.SIGNAL_RUN_FIRST, GObject.TYPE_NONE, 
            (GObject.TYPE_PYOBJECT,)),
        "server-stopped": 
            (GObject.SIGNAL_RUN_FIRST, GObject.TYPE_NONE, 
            (GObject.TYPE_PYOBJECT,)),
    }
    
    def __init__(self):
        Gtk.HBox.__init__(self, homogeneous=False, spacing=0)  
        self.command = "python manage.py runserver"
        self.cwd = None
        self._pid = None
        self._vte = Vte.Terminal()
        self._vte.set_size(self._vte.get_column_count(), 5)
        self._vte.set_size_request(200, 50)
        self._vte.set_font_from_string("monospace 10")
        self._vte.connect("child-exited", self.on_child_exited)
        self.pack_start(self._vte, True, True, 0)
        scrollbar = Gtk.Scrollbar.new(Gtk.Orientation.VERTICAL, self._vte.get_vadjustment())
        self.pack_start(scrollbar, False, False, 0)
        self._button = Gtk.Button()
        self._button.connect("clicked", self.on_button_clicked)
        box = Gtk.VButtonBox()
        box.set_border_width(5)
        box.set_layout(Gtk.ButtonBoxStyle.START)
        box.add(self._button)
        self.pack_start(box, False, False, 0)
        self._start_icon = Gtk.Image.new_from_stock(Gtk.STOCK_EXECUTE, Gtk.IconSize.BUTTON)
        self._stop_icon = Gtk.Image.new_from_stock(Gtk.STOCK_STOP, Gtk.IconSize.BUTTON)
        self.refresh_ui()
        self.show_all()
 
    def is_running(self):
        if self._pid is not None:
            return True
        else:
            return False
    
    def on_button_clicked(self, widget=None, data=None):
        if self.is_running():
            self.stop()
        else:
            self.start()
            
    def on_child_exited(self, vte, data=None):
        pid = self._pid
        self._pid = None
        self.refresh_ui()
        self.emit("server-stopped", pid)
        logger.debug("Development server stopped (pid %s)" % pid)
    
    def set_font(self, font_name):
        self._vte.set_font_from_string(font_name)
        
    def start(self):
        if self.is_running():
            return
        args = shlex.split(self.command)
        self._pid = self._vte.fork_command_full(Vte.PtyFlags.DEFAULT, 
                                                self.cwd,
                                                args,
                                                None,
                                                GLib.SpawnFlags.SEARCH_PATH,
                                                None, 
                                                None)[1]  
        self.refresh_ui()                        
        self.emit("server-started", self._pid)
        logger.debug("Development server started (pid %s)" % self._pid)
        
    def stop(self):
        if self.is_running():
            os.kill(self._pid, signal.SIGKILL)
    
    def refresh_ui(self):
        if self.is_running():
            self._button.set_image(self._stop_icon)
            self._button.set_label("Stop")
        else:
            self._button.set_image(self._start_icon)
            self._button.set_label("Start")
        
        self._button.set_sensitive(bool(self.cwd))
            

########NEW FILE########
__FILENAME__ = shell
import os
import signal
import subprocess
import shlex
import logging
from gi.repository import GObject, Gtk, Vte, GLib

logging.basicConfig()
LOG_LEVEL = logging.DEBUG
logger = logging.getLogger(__name__)
logger.setLevel(LOG_LEVEL)

class Shell(Gtk.HBox):
    """
    A terminal widget setup to run as shell. The command will automatically
    re-start when it is killed.
    """
    __gtype_name__ = "DjangoProjectShell"
    
    def __init__(self):
        Gtk.HBox.__init__(self, homogeneous=False, spacing=0)  
        self.command = None
        self.cwd = None
        self._pid = None
        self._vte = Vte.Terminal()
        self._vte.set_size(self._vte.get_column_count(), 5)
        self._vte.set_size_request(200, 50)
        self._vte.set_font_from_string("monospace 10")
        self._vte.connect("child-exited", self.on_child_exited)
        self.pack_start(self._vte, True, True, 0)
        scrollbar = Gtk.Scrollbar.new(Gtk.Orientation.VERTICAL, self._vte.get_vadjustment())
        self.pack_start(scrollbar, False, False, 0)
        self.show_all()
            
    def on_child_exited(self, vte, data=None):
        logger.debug("Child exited: %s" % self._pid);
        if self._running:
            self.run()

    def run(self):
        self._running = True
        args = shlex.split(self.command)
        self._pid = self._vte.fork_command_full(Vte.PtyFlags.DEFAULT, 
                                                self.cwd,
                                                args,
                                                None,
                                                GLib.SpawnFlags.SEARCH_PATH,
                                                None, 
                                                None)[1]                         
        logger.debug("Running %s (pid %s)" % (self.command, self._pid))
    
    def kill(self):
        self._running = False
        if self._pid:
            os.kill(self._pid, signal.SIGKILL)
        self._vte.reset(False, True)
        
    def set_font(self, font_name):
        self._vte.set_font_from_string(font_name)
        

########NEW FILE########
