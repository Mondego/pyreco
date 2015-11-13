__FILENAME__ = add_file
import os
import shutil

from kivy.garden.filebrowser import FileBrowser
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.button import Button
from kivy.uix.label import Label
from kivy.properties import ObjectProperty
from kivy.uix.popup import Popup


class AddFileDialog(BoxLayout):
    '''AddFileDialog is a dialog for adding files to current project. It emits
       'on_added' event if file has been added successfully, 'on_error' if
       there has been some error in adding file and 'on_cancel' when user
       wishes to cancel the operation.
    '''

    text_file = ObjectProperty()
    '''An instance to TextInput showing file path to be added.
       :data:`text_file` is a :class:`~kivy.properties.ObjectProperty`
    '''

    text_folder = ObjectProperty()
    '''An instance to TextInput showing folder where file has to be added.
       :data:`text_folder` is a :class:`~kivy.properties.ObjectProperty`
    '''

    always_check = ObjectProperty()
    '''An instance to :class:`~kivy.uix.checkbox.CheckBox`, which will
       determine whether same folder will be used for all files of
       same type or not.
       :data:`always_check` is a :class:`~kivy.properties.ObjectProperty`
    '''

    __events__ = ('on_cancel', 'on_added', 'on_error')

    def __init__(self, proj_loader, **kwargs):
        super(AddFileDialog, self).__init__(**kwargs)
        self.proj_loader = proj_loader

    def on_cancel(self):
        pass

    def on_added(self):
        pass

    def on_error(self):
        pass

    def _perform_add_file(self):
        '''To copy file from its original path to new path
        '''

        if self.text_file.text == '' or self.text_folder.text == '':
            return

        self.proj_loader.proj_watcher.stop()

        folder = os.path.join(self.proj_loader.proj_dir, self.text_folder.text)
        if not os.path.exists(folder):
            os.mkdir(folder)

        try:
            shutil.copy(self.text_file.text,
                        os.path.join(folder,
                                     os.path.basename(self.text_file.text)))

            if self.always_check.active:
                self.proj_loader.add_dir_for_file_type(
                    self.text_file.text[self.text_file.text.rfind('.')+1:],
                    self.text_folder.text)

            self.proj_loader.proj_watcher.start_watching(
                self.proj_loader.proj_dir)
            self.dispatch('on_added')

        except OSError, IOError:
            self.dispatch('on_error')

    def update_from_file(self, *args):
        '''To determine the folder associated with current file type.
        '''

        curr_type = self.text_file.text
        curr_type = curr_type[curr_type.find('.') + 1:]
        if curr_type == '':
            return

        try:
            folder = self.proj_loader.dict_file_type_and_path[curr_type]
            self.text_folder.text = folder
            self.always_check.active = True

        except KeyError:
            pass

    def _cancel_popup(self, *args):
        '''To dismiss popup when cancel is pressed.
        '''

        self._popup.dismiss()

    def _file_load(self, instance):
        '''To set the text of text_file, to the file selected.
        '''

        self._popup.dismiss()
        if instance.selection != []:
            self.text_file.text = instance.selection[0]

    def open_file_btn_pressed(self, *args):
        '''To load File Browser for selected file when 'Open File' is clicked
        '''

        self._fbrowser = FileBrowser(select_string='Open')
        self._fbrowser.bind(on_success=self._file_load,
                            on_canceled=self._cancel_popup)

        self._popup = Popup(title='Open File', content=self._fbrowser,
                            size_hint=(0.9, 0.9), auto_dismiss=False)

        self._popup.open()

    def _folder_load(self, instance):
        '''To set the text of text_folder, to the folder selected.
        '''

        if hasattr(self, '_popup'):
            self._popup.dismiss()

        proj_dir = ''
        if instance.ids.tabbed_browser.current_tab.text == 'List View':
            proj_dir = instance.ids.list_view.path
        else:
            proj_dir = instance.ids.icon_view.path

        proj_dir = os.path.join(proj_dir, instance.filename)
        if proj_dir.find(self.proj_loader.proj_dir) != -1:
            proj_dir = proj_dir.replace(self.proj_loader.proj_dir, '')
            if proj_dir[0] == '/':
                proj_dir = proj_dir[1:]

            self.text_folder.text = proj_dir

    def open_folder_btn_pressed(self, *args):
        '''To load File Browser for selected folder when 'Open Folder'
           is clicked
        '''

        self._fbrowser = FileBrowser(select_string='Open')
        self._fbrowser.ids.list_view.path = self.proj_loader.proj_dir
        self._fbrowser.bind(on_success=self._folder_load,
                            on_canceled=self._cancel_popup)

        self._popup = Popup(title='Open File', content=self._fbrowser,
                            size_hint=(0.9, 0.9), auto_dismiss=False)

        self._popup.open()

########NEW FILE########
__FILENAME__ = app
__all__ = ('DesignerApp', )

import kivy
import time
import os
import shutil
import traceback

kivy.require('1.4.1')
from kivy.app import App
from kivy.uix.floatlayout import FloatLayout
from kivy.uix.layout import Layout
from kivy.factory import Factory
from kivy.properties import ObjectProperty, BooleanProperty
from kivy.clock import Clock
from kivy.uix import actionbar
from kivy.garden.filebrowser import FileBrowser
from kivy.uix.popup import Popup
from kivy.uix.tabbedpanel import TabbedPanel, TabbedPanelItem
from kivy.lang import Builder
from kivy.uix.carousel import Carousel
from kivy.uix.screenmanager import ScreenManager

import designer
from designer.uix.actioncheckbutton import ActionCheckButton
from designer.playground import PlaygroundDragElement
from designer.common import widgets
from designer.uix.editcontview import EditContView
from designer.uix.kv_lang_area import KVLangArea
from designer.undo_manager import WidgetOperation, UndoManager
from designer.project_loader import ProjectLoader, ProjectLoaderException
from designer.select_class import SelectClass
from designer.confirmation_dialog import ConfirmationDialog
from designer.proj_watcher import ProjectWatcher
from designer.recent_manager import RecentManager, RecentDialog
from designer.add_file import AddFileDialog
from designer.ui_creator import UICreator
from designer.designer_content import DesignerContent
from designer.uix.designer_sandbox import DesignerSandbox
from designer.project_settings import ProjectSettings
from designer.designer_settings import DesignerSettings
from designer.helper_functions import get_kivy_designer_dir
from designer.new_dialog import NewProjectDialog, NEW_PROJECTS
from designer.eventviewer import EventViewer
from designer.uix.designer_action_items import DesignerActionButton
from designer.help_dialog import HelpDialog, AboutDialog

NEW_PROJECT_DIR_NAME = 'new_proj'
NEW_TEMPLATES_DIR = 'new_templates'


class Designer(FloatLayout):
    '''Designer is the Main Window class of Kivy Designer
       :data:`message` is a :class:`~kivy.properties.StringProperty`
    '''

    designer_console = ObjectProperty(None)
    '''Instance of :class:`designer.designer_console.ConsoleDialog`
    '''

    statusbar = ObjectProperty(None)
    '''Reference to the :class:`~designer.statusbar.StatusBar` instance.
       :data:`statusbar` is a :class:`~kivy.properties.ObjectProperty`
    '''

    editcontview = ObjectProperty(None)
    '''Reference to the :class:`~designer.uix.EditContView` instance.
       :data:`v` is a :class:`~kivy.properties.ObjectProperty`
    '''

    actionbar = ObjectProperty(None)
    '''Reference to the :class:`~kivy.actionbar.ActionBar` instance.
       ActionBar is used as a MenuBar to display bunch of menu items.
       :data:`actionbar` is a :class:`~kivy.properties.ObjectProperty`
    '''

    undo_manager = ObjectProperty(UndoManager())
    '''Reference to the :class:`~designer.UndoManager` instance.
       :data:`undo_manager` is a :class:`~kivy.properties.ObjectProperty`
    '''

    project_watcher = ObjectProperty(None)
    '''Reference to the :class:`~designer.project_watcher.ProjectWatcher`.
       :data:`project_watcher` is a :class:`~kivy.properties.ObjectProperty`
    '''

    project_loader = ObjectProperty(None)
    '''Reference to the :class:`~designer.project_loader.ProjectLoader`.
       :data:`project_loader` is a :class:`~kivy.properties.ObjectProperty`
    '''

    proj_settings = ObjectProperty(None)
    '''Reference of :class:`~designer.project_settings.ProjectSettings`.
       :data:`proj_settings` is a :class:`~kivy.properties.ObjectProperty`
    '''

    _curr_proj_changed = BooleanProperty(False)
    '''Specifies whether current project has been changed inside Kivy Designer
       :data:`_curr_proj_changed` is
       a :class:`~kivy.properties.BooleanProperty`
    '''

    _proj_modified_outside = BooleanProperty(False)
    '''Specifies whether current project has been changed outside Kivy Designer
       :data:`_proj_modified_outside` is a
       :class:`~kivy.properties.BooleanProperty`
    '''

    ui_creator = ObjectProperty(None)
    '''Reference to :class:`~designer.ui_creator.UICreator` instance.
       :data:`ui_creator` is a :class:`~kivy.properties.ObjectProperty`
    '''

    designer_content = ObjectProperty(None)
    '''Reference to
       :class:`~designer.designer_content.DesignerContent` instance.
       :data:`designer_content` is a :class:`~kivy.properties.ObjectProperty`
    '''

    proj_tree_view = ObjectProperty(None)
    '''Reference to Project Tree instance
       :data:`proj_tree_view` is a :class:`~kivy.properties.ObjectProperty`
    '''

    designer_settings = ObjectProperty(None)
    '''Reference of :class:`~designer.designer_settings.DesignerSettings`.
       :data:`designer_settings` is a :class:`~kivy.properties.ObjectProperty`
    '''

    start_page = ObjectProperty(None)
    '''Reference of :class:`~designer.start_page.DesignerStartPage`.
       :data:`start_page` is a :class:`~kivy.properties.ObjectProperty`
    '''

    recent_files_cont_menu = ObjectProperty(None)
    '''The context sub menu, containing the recently opened/saved projects.
       Reference of :class:`~designer.uix.contextual.ContextSubMenu`.
       :data:`recent_files_cont_menu` is a
       :class:`~kivy.properties.ObjectProperty`
    '''

    def __init__(self, **kwargs):
        super(Designer, self).__init__(**kwargs)
        self.project_watcher = ProjectWatcher(self.project_modified)
        self.project_loader = ProjectLoader(self.project_watcher)
        self.recent_manager = RecentManager()
        self.widget_to_paste = None
        self.designer_content = DesignerContent(size_hint=(1, None))

        self.designer_settings = DesignerSettings()
        self.designer_settings.bind(on_config_change=self._config_change)
        self.designer_settings.load_settings()
        self.designer_settings.bind(on_close=self._cancel_popup)

        Clock.schedule_interval(
            self.project_loader.perform_auto_save,
            int(self.designer_settings.config_parser.getdefault(
                'global', 'auto_save_time', 5))*60)

    def show_help(self, *args):
        '''Event handler for 'on_help' event of self.start_page
        '''

        self.help_dlg = HelpDialog()
        self._popup = Popup(title='Kivy Designer Help', content=self.help_dlg,
                            size_hint=(0.95, 0.95),
                            auto_dismiss=False)
        self._popup.open()
        self.help_dlg.bind(on_cancel=self._cancel_popup)

        self.help_dlg.rst.source = 'help.rst'

    def _config_change(self, *args):
        '''Event Handler for 'on_config_change'
           event of self.designer_settings.
        '''

        Clock.unschedule(self.project_loader.perform_auto_save)
        Clock.schedule_interval(
            self.project_loader.perform_auto_save,
            int(self.designer_settings.config_parser.getdefault(
                'global', 'auto_save_time', 5))*60)

        self.ui_creator.kv_code_input.reload_kv = \
            bool(self.designer_settings.config_parser.getdefault(
                 'global', 'reload_kv', True))

        self.recent_manager.max_recent_files = \
            int(self.designer_settings.config_parser.getdefault(
                'global', 'num_recent_files', 5))

    def _add_designer_content(self):
        '''Add designer_content to Designer, when a project is loaded
        '''

        for _child in self.children[:]:
            if _child == self.designer_content:
                return

        self.remove_widget(self.start_page)
        self.add_widget(self.designer_content, 1)

        self.ids['actn_btn_save'].disabled = False
        self.ids['actn_btn_save_as'].disabled = False
        self.ids['actn_chk_proj_tree'].disabled = False
        self.ids['actn_chk_prop_event'].disabled = False
        self.ids['actn_chk_widget_tree'].disabled = False
        self.ids['actn_chk_status_bar'].disabled = False
        self.ids['actn_chk_kv_lang_area'].disabled = False
        self.ids['actn_btn_add_file'].disabled = False
        self.ids['actn_btn_custom_widget'].disabled = False
        self.ids['actn_btn_proj_pref'].disabled = False
        self.ids['actn_btn_run_proj'].disabled = False

    def on_statusbar_height(self, *args):
        '''Callback for statusbar.height
        '''

        self.designer_content.y = self.statusbar.height
        self.on_height(*args)

    def on_actionbar_height(self, *args):
        '''Callback for actionbar.height
        '''

        self.on_height(*args)

    def on_height(self, *args):
        '''Callback for self.height
        '''

        if self.actionbar and self.statusbar:
            self.designer_content.height = self.height - \
                self.actionbar.height - self.statusbar.height

            self.designer_content.y = self.statusbar.height

    def project_modified(self, *args):
        '''Event Handler called when Project is modified outside Kivy Designer
        '''

        #To dispatch modified event only once for all files/folders of proj_dir
        if self._proj_modified_outside:
            return

        self._confirm_dlg = ConfirmationDialog(
            message="Current Project has been modified\n"
            "outside the Kivy Designer.\nDo you want to reload project?")
        self._confirm_dlg.bind(on_ok=self._perform_reload,
                               on_cancel=self._cancel_popup)
        self._popup = Popup(title='Kivy Designer', content=self._confirm_dlg,
                            size_hint=(None, None), size=('200pt', '150pt'),
                            auto_dismiss=False)
        self._popup.open()

        self._proj_modified_outside = True

    def _perform_reload(self, *args):
        '''Perform reload of project after it is modified
        '''

        #Perform reload of project after it is modified
        self._popup.dismiss()
        self.project_watcher.allow_event_dispatch = False
        self._perform_open(self.project_loader.proj_dir)
        self.project_watcher.allow_event_dispatch = True
        self._proj_modified_outside = False

    def on_show_edit(self, *args):
        '''Event Handler of 'on_show_edit' event. This will show EditContView
           in ActionBar
        '''

        if isinstance(self.actionbar.children[0], EditContView):
            return

        if self.editcontview is None:
            self.editcontview = EditContView(
                on_undo=self.action_btn_undo_pressed,
                on_redo=self.action_btn_redo_pressed,
                on_cut=self.action_btn_cut_pressed,
                on_copy=self.action_btn_copy_pressed,
                on_paste=self.action_btn_paste_pressed,
                on_delete=self.action_btn_delete_pressed,
                on_selectall=self.action_btn_select_all_pressed,
                on_next_screen=self._next_screen,
                on_prev_screen=self._prev_screen)

        self.actionbar.add_widget(self.editcontview)

        widget = self.ui_creator.propertyviewer.widget

        if isinstance(widget, Carousel) or\
                isinstance(widget, ScreenManager) or\
                isinstance(widget, TabbedPanel):
            self.editcontview.show_action_btn_screen(True)
        else:
            self.editcontview.show_action_btn_screen(False)

        if self.ui_creator.kv_code_input.clicked:
            self._edit_selected = 'KV'
        elif self.ui_creator.playground.clicked:
            self._edit_selected = 'Play'
        else:
            self._edit_selected = 'Py'

        self.ui_creator.playground.clicked = False
        self.ui_creator.kv_code_input.clicked = False

    def _prev_screen(self, *args):
        '''Event handler for 'on_prev_screen' for self.editcontview
        '''

        widget = self.ui_creator.propertyviewer.widget
        if isinstance(widget, Carousel):
            widget.load_previous()

        elif isinstance(widget, ScreenManager):
            widget.current = widget.previous()

        elif isinstance(widget, TabbedPanel):
            index = widget.tab_list.index(widget.current_tab)
            if len(widget.tab_list) <= index + 1:
                return

            widget.switch_to(widget.tab_list[index + 1])

    def _next_screen(self, *args):
        '''Event handler for 'on_next_screen' for self.editcontview
        '''

        widget = self.ui_creator.propertyviewer.widget
        if isinstance(widget, Carousel):
            widget.load_next()

        elif isinstance(widget, ScreenManager):
            widget.current = widget.next()

        elif isinstance(widget, TabbedPanel):
            index = widget.tab_list.index(widget.current_tab)
            if index == 0:
                return

            widget.switch_to(widget.tab_list[index - 1])

    def on_touch_down(self, touch):
        '''Override of FloatLayout.on_touch_down. Used to determine where
           touch is down and to call self.actionbar.on_previous
        '''

        if not isinstance(self.actionbar.children[0], EditContView) or\
           self.actionbar.collide_point(*touch.pos):
            return super(FloatLayout, self).on_touch_down(touch)

        self.actionbar.on_previous(self)

        return super(FloatLayout, self).on_touch_down(touch)

    def action_btn_new_pressed(self, *args):
        '''Event Handler when ActionButton "New" is pressed.
        '''

        if not self._curr_proj_changed:
            self._show_new_dialog()
            return

        self._confirm_dlg = ConfirmationDialog('All unsaved changes will be'
                                               ' lost.\n'
                                               'Do you want to continue?')
        self._confirm_dlg.bind(on_ok=self._show_new_dialog,
                               on_cancel=self._cancel_popup)

        self._popup = Popup(title='New', content=self._confirm_dlg,
                            size_hint=(None, None), size=('200pt', '150pt'),
                            auto_dismiss=False)
        self._popup.open()

    def _show_new_dialog(self, *args):
        if hasattr(self, '_popup'):
            self._popup.dismiss()

        self._new_dialog = NewProjectDialog()
        self._new_dialog.bind(on_select=self._perform_new,
                              on_cancel=self._cancel_popup)
        self._popup = Popup(title='New Project', content=self._new_dialog,
                            size_hint=(None, None), size=('650pt', '450pt'),
                            auto_dismiss=False)
        self._popup.open()

    def _perform_new(self, *args):
        '''To load new project
        '''

        if hasattr(self, '_popup'):
            self._popup.dismiss()

        self.cleanup()
        new_proj_dir = os.path.join(get_kivy_designer_dir(),
                                    NEW_PROJECT_DIR_NAME)
        if os.path.exists(new_proj_dir):
            shutil.rmtree(new_proj_dir)

        os.mkdir(new_proj_dir)

        template = self._new_dialog.adapter.selection[0].text
        kv_file = NEW_PROJECTS[template][0]
        py_file = NEW_PROJECTS[template][1]

        _dir = os.path.dirname(designer.__file__)
        _dir = os.path.split(_dir)[0]
        templates_dir = os.path.join(_dir, NEW_TEMPLATES_DIR)
        shutil.copy(os.path.join(templates_dir, py_file),
                    os.path.join(new_proj_dir, "main.py"))

        shutil.copy(os.path.join(templates_dir, kv_file),
                    os.path.join(new_proj_dir, "main.kv"))

        self.ui_creator.playground.sandbox.error_active = True
        with self.ui_creator.playground.sandbox:
            self.project_loader.load_new_project(os.path.join(new_proj_dir,
                                                              "main.kv"))
            root_wigdet = self.project_loader.get_root_widget()
            self.ui_creator.playground.add_widget_to_parent(root_wigdet, None,
                                                            from_undo=True)
            self.ui_creator.kv_code_input.text = \
                self.project_loader.get_full_str()
            self.designer_content.update_tree_view(self.project_loader)
            self._add_designer_content()
            if self.project_loader.class_rules:
                for i, _rule in enumerate(self.project_loader.class_rules):
                    widgets.append((_rule.name, 'custom'))

                self.designer_content.toolbox.add_custom()

        self.ui_creator.playground.sandbox.error_active = False

    def cleanup(self):
        '''To cleanup everything loaded by the current project before loading
           another project.
        '''

        self.project_loader.cleanup()
        self.ui_creator.cleanup()
        self.undo_manager.cleanup()
        self.designer_content.toolbox.cleanup()

        for node in self.proj_tree_view.root.nodes[:]:
            self.proj_tree_view.remove_node(node)

        for widget in widgets[:]:
            if widget[1] == 'custom':
                widgets.remove(widget)

        self._curr_proj_changed = False
        self.ui_creator.kv_code_input.text = ""

        self.designer_content.tab_pannel.list_py_code_inputs = []
        for th in self.designer_content.tab_pannel.tab_list[:-1]:
            self.designer_content.tab_pannel.remove_widget(th)

    def action_btn_open_pressed(self, *args):
        '''Event Handler when ActionButton "Open" is pressed.
        '''

        if not self._curr_proj_changed:
            self._show_open_dialog()
            return

        self._confirm_dlg = ConfirmationDialog('All unsaved changes will be '
                                               'lost.\n'
                                               'Do you want to continue?')

        self._confirm_dlg.bind(on_ok=self._show_open_dialog,
                               on_cancel=self._cancel_popup)

        self._popup = Popup(title='Kivy Designer', content=self._confirm_dlg,
                            size_hint=(None, None), size=('200pt', '150pt'),
                            auto_dismiss=False)
        self._popup.open()

    def _show_open_dialog(self, *args):
        '''To show FileBrowser to "Open" a project
        '''

        if hasattr(self, '_popup'):
            self._popup.dismiss()

        self._fbrowser = FileBrowser(select_string='Open')

        def_path = os.getcwd()
        if not self.project_loader.new_project and \
                self.project_loader.proj_dir:
            def_path = self.project_loader.proj_dir

        if self._fbrowser.ids.tabbed_browser.current_tab.text == 'List View':
            self._fbrowser.ids.list_view.path = def_path
        else:
            self._fbrowser.ids.icon_view.path = def_path

        self._fbrowser.bind(on_success=self._fbrowser_load,
                            on_canceled=self._cancel_popup)

        self._popup = Popup(title="Open", content=self._fbrowser,
                            size_hint=(0.9, 0.9), auto_dismiss=False)
        self._popup.open()

    def _select_class_selected(self, *args):
        '''Event Handler for 'on_select' event of self._select_class
        '''

        selection = self._select_class.listview.adapter.selection[0].text

        with self.ui_creator.playground.sandbox:
            root_widget = self.project_loader.set_root_widget(selection)
            self.ui_creator.playground.add_widget_to_parent(root_widget,
                                                            None,
                                                            from_undo=True)
            self.ui_creator.kv_code_input.text = \
                self.project_loader.get_root_str()

        self._select_class_popup.dismiss()

    def _select_class_cancel(self, *args):
        '''Event Handler for 'on_cancel' event of self._select_class
        '''

        self._select_class_popup.dismiss()

    def _fbrowser_load(self, instance):
        '''Event Handler for 'on_load' event of self._fbrowser
        '''
        if instance.selection == []:
            return

        file_path = instance.selection[0]
        self._popup.dismiss()
        self._perform_open(file_path)

    def _perform_open(self, file_path):
        '''To open a project given by file_path
        '''

        for widget in widgets[:]:
            if widget[1] == 'custom':
                widgets.remove(widget)

        self.cleanup()

        self.ui_creator.playground.sandbox.error_active = True

        root_widget = None

        with self.ui_creator.playground.sandbox:
            try:
                self.project_loader.load_project(file_path)

                if self.project_loader.class_rules:
                    for i, _rule in enumerate(self.project_loader.class_rules):
                        widgets.append((_rule.name, 'custom'))

                    self.designer_content.toolbox.add_custom()

                #to test listview
                #root_wigdet = None
                root_wigdet = self.project_loader.get_root_widget()

                if not root_wigdet:
                    #Show list box showing widgets
                    self._select_class = SelectClass(
                        self.project_loader.class_rules)

                    self._select_class.bind(
                        on_select=self._select_class_selected,
                        on_cancel=self._select_class_cancel)

                    self._select_class_popup = Popup(
                        title="Select Root Widget",
                        content=self._select_class,
                        size_hint=(0.5, 0.5),
                        auto_dismiss=False)
                    self._select_class_popup.open()

                else:
                    self.ui_creator.playground.add_widget_to_parent(
                        root_wigdet, None, from_undo=True)
                    self.ui_creator.kv_code_input.text = \
                        self.project_loader.get_full_str()

                self.recent_manager.add_file(file_path)
                #Record everything for later use
                self.project_loader.record()
                self.designer_content.update_tree_view(self.project_loader)
                self._add_designer_content()

            except Exception as e:
                self.statusbar.show_message('Cannot load Project: %s' %
                                            (str(e)))

        self.ui_creator.playground.sandbox.error_active = False

    def _cancel_popup(self, *args):
        '''EventHandler for all self._popup when self._popup.content
           emits 'on_cancel' or equivalent.
        '''

        self._proj_modified_outside = False
        self._popup.dismiss()

    def action_btn_save_pressed(self, *args):
        '''Event Handler when ActionButton "Save" is pressed.
        '''

        if self.project_loader.root_rule:
            try:
                if self.project_loader.new_project:
                    self.action_btn_save_as_pressed()
                    return

                else:
                    self.project_loader.save_project()
                    projdir = self.project_loader.proj_dir
                    self.project_loader.cleanup(stop_watcher=False)
                    self.ui_creator.playground.cleanup()
                    self.project_loader.load_project(projdir)
                    root_wigdet = self.project_loader.get_root_widget()
                    self.ui_creator.playground.add_widget_to_parent(
                        root_wigdet, None, from_undo=True, from_kv=True)
                self._curr_proj_changed = False
                self.statusbar.show_message('Project saved successfully')

            except:
                self.statusbar.show_message('Cannot save project')

    def action_btn_save_as_pressed(self, *args):
        '''Event Handler when ActionButton "Save As" is pressed.
        '''

        if self.project_loader.root_rule:
            self._curr_proj_changed = False

            self._save_as_browser = FileBrowser(select_string='Save')

            def_path = os.getcwd()
            if not self.project_loader.new_project and \
                    self.project_loader.proj_dir:
                def_path = self.project_loader.proj_dir

            if self._save_as_browser.ids.tabbed_browser.current_tab.text == \
                    'List View':
                self._save_as_browser.ids.list_view.path = def_path
            else:
                self._save_as_browser.ids.icon_view.path = def_path

            self._save_as_browser.bind(on_success=self._perform_save_as,
                                       on_canceled=self._cancel_popup)

            self._popup = Popup(title="Enter Folder Name",
                                content=self._save_as_browser,
                                size_hint=(0.9, 0.9), auto_dismiss=False)
            self._popup.open()

    def _perform_save_as(self, instance):
        '''Event handler for 'on_success' event of self._save_as_browser
        '''

        if hasattr(self, '_popup'):
            self._popup.dismiss()

        proj_dir = ''
        if instance.ids.tabbed_browser.current_tab.text == 'List View':
            proj_dir = instance.ids.list_view.path
        else:
            proj_dir = instance.ids.icon_view.path

        proj_dir = os.path.join(proj_dir, instance.filename)
        try:
            self.project_loader.save_project(proj_dir)
            self.recent_manager.add_file(proj_dir)
            projdir = self.project_loader.proj_dir
            self.project_loader.cleanup()
            self.ui_creator.playground.cleanup()
            self.project_loader.load_project(projdir)
            root_wigdet = self.project_loader.get_root_widget()
            self.ui_creator.playground.add_widget_to_parent(root_wigdet,
                                                            None,
                                                            from_undo=True)
            self.statusbar.show_message('Project saved successfully')

        except:
            self.statusbar.show_message('Cannot save project')

    def action_btn_settings_pressed(self, *args):
        '''Event handler for 'on_release' event of
           DesignerActionButton "Settings"
        '''

        self.designer_settings.parent = None
        self._popup = Popup(title="Kivy Designer Settings",
                            content=self.designer_settings,
                            size_hint=(None, None),
                            size=(600, 400), auto_dismiss=False)

        self._popup.open()

    def action_btn_recent_files_pressed(self, *args):
        '''Event Handler when ActionButton "Recent Files" is pressed.
        '''
        pass

    def fill_recent_menu(self, *args):
        '''Fill self.recent_files_cont_menu with DesignerActionButton
           of all Recent Files
        '''
        recent_menu = self.recent_files_cont_menu
        for _file in self.recent_manager.list_files:
            act_btn = DesignerActionButton(text=_file, shorten=True)
            recent_menu.add_widget(act_btn)
            act_btn.bind(on_release=self._recent_file_release)

    def _recent_file_release(self, instance, *args):
        '''Event Handler for 'on_select' event of self._recent_dlg.
        '''
        self._perform_open(instance.text)

    def action_btn_quit_pressed(self, *args):
        '''Event Handler when ActionButton "Quit" is pressed.
        '''

        App.get_running_app().stop()

    def action_btn_undo_pressed(self, *args):
        '''Event Handler when ActionButton "Undo" is pressed.
        '''

        if self._edit_selected == 'Play':
            self.undo_manager.do_undo()
        elif self._edit_selected == 'KV':
            self.ui_creator.kv_code_input.do_undo()
        elif self._edit_selected == 'Py':
            list_py = self.designer_content.tab_pannel.list_py_code_inputs
            for code_input in list_py:
                if code_input.clicked is True:
                    code_input.clicked = False
                    code_input.do_undo()

    def action_btn_redo_pressed(self, *args):
        '''Event Handler when ActionButton "Redo" is pressed.
        '''

        if self._edit_selected == 'Play':
            self.undo_manager.do_redo()
        elif self._edit_selected == 'KV':
            self.ui_creator.kv_code_input.do_redo()
        elif self._edit_selected == 'Py':
            list_py = self.designer_content.tab_pannel.list_py_code_inputs
            for code_input in list_py:
                if code_input.clicked is True:
                    code_input.clicked = False
                    code_input.do_redo()

    def action_btn_cut_pressed(self, *args):
        '''Event Handler when ActionButton "Cut" is pressed.
        '''

        if self._edit_selected == 'Play':
            self.ui_creator.playground.do_cut()

        elif self._edit_selected == 'KV':
            self.ui_creator.kv_code_input.do_cut()

        elif self._edit_selected == 'Py':
            list_py = self.designer_content.tab_pannel.list_py_code_inputs
            for code_input in list_py:
                if code_input.clicked is True:
                    code_input.clicked = False
                    code_input.do_cut()

    def action_btn_copy_pressed(self, *args):
        '''Event Handler when ActionButton "Copy" is pressed.
        '''

        if self._edit_selected == 'Play':
            self.ui_creator.playground.do_copy()

        elif self._edit_selected == 'KV':
            self.ui_creator.kv_code_input.do_copy()

        elif self._edit_selected == 'Py':
            list_py = self.designer_content.tab_pannel.list_py_code_inputs
            for code_input in list_py:
                if code_input.clicked is True:
                    code_input.clicked = False
                    code_input.do_copy()

    def action_btn_paste_pressed(self, *args):
        '''Event Handler when ActionButton "Paste" is pressed.
        '''

        if self._edit_selected == 'Play':
            self.ui_creator.playground.do_paste()

        elif self._edit_selected == 'KV':
            self.ui_creator.kv_code_input.do_paste()

        elif self._edit_selected == 'Py':
            list_py = self.designer_content.tab_pannel.list_py_code_inputs
            for code_input in list_py:
                if code_input.clicked is True:
                    code_input.clicked = False
                    code_input.do_paste()

    def action_btn_delete_pressed(self, *args):
        '''Event Handler when ActionButton "Delete" is pressed.
        '''

        if self._edit_selected == 'Play':
            self.ui_creator.playground.do_delete()

        elif self._edit_selected == 'KV':
            self.ui_creator.kv_code_input.do_delete()

        elif self._edit_selected == 'Py':
            list_py = self.designer_content.tab_pannel.list_py_code_inputs
            for code_input in list_py:
                if code_input.clicked is True:
                    code_input.clicked = False
                    code_input.do_delete()

    def action_btn_select_all_pressed(self, *args):
        '''Event Handler when ActionButton "Select All" is pressed.
        '''

        if self._edit_selected == 'Play':
            self.ui_creator.playground.do_select_all()

        elif self._edit_selected == 'KV':
            self.ui_creator.kv_code_input.do_select_all()

        elif self._edit_selected == 'Py':
            list_py = self.designer_content.tab_pannel.list_py_code_inputs
            for code_input in list_py:
                if code_input.clicked is True:
                    code_input.clicked = False
                    code_input.do_select_all()

    def action_btn_add_custom_widget_press(self, *args):
        '''Event Handler when ActionButton "Add Custom Widget" is pressed.
        '''

        self._custom_browser = FileBrowser(select_string='Add')
        self._custom_browser.bind(on_success=self._custom_browser_load,
                                  on_canceled=self._cancel_popup)

        self._popup = Popup(title="Add Custom Widget",
                            content=self._custom_browser,
                            size_hint=(0.9, 0.9), auto_dismiss=False)
        self._popup.open()

    def _custom_browser_load(self, instance):
        '''Event Handler for 'on_success' event of self._custom_browser
        '''

        file_path = instance.selection[0]
        self._popup.dismiss()

        self.ui_creator.playground.sandbox.error_active = True

        with self.ui_creator.playground.sandbox:
            try:
                self.project_loader.add_custom_widget(file_path)

                self.designer_content.toolbox.cleanup()
                for _rule in (self.project_loader.custom_widgets):
                    widgets.append((_rule.name, 'custom'))

                self.designer_content.toolbox.add_custom()

            except ProjectLoaderException as e:
                self.statusbar.show_message('Cannot load widget. %s' % str(e))

        self.ui_creator.playground.sandbox.error_active = False

    def action_chk_btn_toolbox_active(self, chk_btn):
        '''Event Handler when ActionCheckButton "Toolbox" is activated.
        '''

        if chk_btn.checkbox.active:
            self._toolbox_parent.add_widget(
                self.designer_content.splitter_tree)
            self.designer_content.splitter_tree.width = self._toolbox_width

        else:
            self._toolbox_parent = self.designer_content.splitter_tree.parent
            self._toolbox_parent.remove_widget(
                self.designer_content.splitter_tree)
            self._toolbox_width = self.designer_content.splitter_tree.width
            self.designer_content.splitter_tree.width = 0

    def action_chk_btn_property_viewer_active(self, chk_btn):
        '''Event Handler when ActionCheckButton "Property Viewer" is activated.
        '''

        if chk_btn.checkbox.active:
            self._toggle_splitter_widget_tree()
            if self.ui_creator.splitter_widget_tree.parent is None:
                self._splitter_widget_tree_parent.add_widget(
                    self.ui_creator.splitter_widget_tree)
                self.ui_creator.splitter_widget_tree.width = \
                    self._splitter_widget_tree_width

            add_tree = False
            if self.ui_creator.grid_widget_tree.parent is not None:
                add_tree = True
                self.ui_creator.splitter_property.size_hint_y = None
                self.ui_creator.splitter_property.height = 300

            self._splitter_property_parent.clear_widgets()
            if add_tree:
                self._splitter_property_parent.add_widget(
                    self.ui_creator.grid_widget_tree)

            self._splitter_property_parent.add_widget(
                self.ui_creator.splitter_property)
        else:
            self._splitter_property_parent = \
                self.ui_creator.splitter_property.parent
            self._splitter_property_parent.remove_widget(
                self.ui_creator.splitter_property)
            self._toggle_splitter_widget_tree()

    def action_chk_btn_widget_tree_active(self, chk_btn):
        '''Event Handler when ActionCheckButton "Widget Tree" is activated.
        '''

        if chk_btn.checkbox.active:
            self._toggle_splitter_widget_tree()
            add_prop = False
            if self.ui_creator.splitter_property.parent is not None:
                add_prop = True

            self._grid_widget_tree_parent.clear_widgets()
            self._grid_widget_tree_parent.add_widget(
                self.ui_creator.grid_widget_tree)
            if add_prop:
                self._grid_widget_tree_parent.add_widget(
                    self.ui_creator.splitter_property)
                self.ui_creator.splitter_property.size_hint_y = None
                self.ui_creator.splitter_property.height = 300
        else:
            self._grid_widget_tree_parent = \
                self.ui_creator.grid_widget_tree.parent
            self._grid_widget_tree_parent.remove_widget(
                self.ui_creator.grid_widget_tree)
            self.ui_creator.splitter_property.size_hint_y = 1
            self._toggle_splitter_widget_tree()

    def _toggle_splitter_widget_tree(self):
        '''To show/hide splitter_widget_tree
        '''

        if self.ui_creator.splitter_widget_tree.parent is not None and\
                self.ui_creator.splitter_property.parent is None and\
                self.ui_creator.grid_widget_tree.parent is None:

            self._splitter_widget_tree_parent = \
                self.ui_creator.splitter_widget_tree.parent
            self._splitter_widget_tree_parent.remove_widget(
                self.ui_creator.splitter_widget_tree)
            self._splitter_widget_tree_width = \
                self.ui_creator.splitter_widget_tree.width
            self.ui_creator.splitter_widget_tree.width = 0

        elif self.ui_creator.splitter_widget_tree.parent is None:
            self._splitter_widget_tree_parent.add_widget(
                self.ui_creator.splitter_widget_tree)
            self.ui_creator.splitter_widget_tree.width = \
                self._splitter_widget_tree_width

    def action_chk_btn_status_bar_active(self, chk_btn):
        '''Event Handler when ActionCheckButton "StatusBar" is activated.
        '''

        if chk_btn.checkbox.active:
            self._statusbar_parent.add_widget(self.statusbar)
            self.statusbar.height = self._statusbar_height
        else:
            self._statusbar_parent = self.statusbar.parent
            self._statusbar_height = self.statusbar.height
            self._statusbar_parent.remove_widget(self.statusbar)
            self.statusbar.height = 0

    def action_chk_btn_kv_area_active(self, chk_btn):
        '''Event Handler when ActionCheckButton "KVLangArea" is activated.
        '''

        if chk_btn.checkbox.active:
            self.ui_creator.splitter_kv_code_input.height = \
                self._kv_area_height
            self._kv_area_parent.add_widget(
                self.ui_creator.splitter_kv_code_input)
        else:
            self._kv_area_parent = \
                self.ui_creator.splitter_kv_code_input.parent
            self._kv_area_height = \
                self.ui_creator.splitter_kv_code_input.height
            self.ui_creator.splitter_kv_code_input.height = 0
            self._kv_area_parent.remove_widget(
                self.ui_creator.splitter_kv_code_input)

    def _error_adding_file(self, *args):
        '''Event Handler for 'on_error' event of self._add_file_dlg
        '''

        self.statusbar.show_message('Error while adding file to project')
        self._popup.dismiss()

    def _added_file(self, *args):
        '''Event Handler for 'on_added' event of self._add_file_dlg
        '''

        self.statusbar.show_message('File successfully added to project')
        self._popup.dismiss()
        if self._add_file_dlg.target_file[3:] == '.py':
            self.designer_content.add_file_to_tree_view(
                self._add_file_dlg.target_file)

    def action_btn_add_file_pressed(self, *args):
        '''Event Handler when ActionButton "Add File" is pressed.
        '''

        self._add_file_dlg = AddFileDialog(self.project_loader)
        self._add_file_dlg.bind(on_added=self._added_file,
                                on_error=self._error_adding_file,
                                on_cancel=self._cancel_popup)

        self._popup = Popup(title="Add File",
                            content=self._add_file_dlg,
                            size_hint=(None, None),
                            size=(400, 300), auto_dismiss=False)

        self._popup.open()

    def action_btn_project_pref_pressed(self, *args):
        '''Event Handler when ActionButton "Project Prefences" is pressed.
        '''
        self.proj_settings = ProjectSettings(proj_loader=self.project_loader)
        self.proj_settings.load_proj_settings()
        self.proj_settings.bind(on_close=self._cancel_popup)
        self._popup = Popup(title="Project Preferences",
                            content=self.proj_settings,
                            size_hint=(None, None),
                            size=(600, 400), auto_dismiss=False)

        self._popup.open()

    def action_btn_run_project_pressed(self, *args):
        '''Event Handler when ActionButton "Run" is pressed.
        '''
        if self.project_loader.file_list == []:
            return
        args = ''
        envs = ''

        python_path = self.designer_settings.config_parser.getdefault(
            'global', 'python_shell_path', '')

        if python_path == '':
            self.statusbar.show_message("Python Shell Path not specified,"
                                        " please specify it before running"
                                        " project")
            return

        if self.proj_settings and self.proj_settings.config_parser:
            args = self.proj_settings.config_parser.getdefault('arguments',
                                                               'arg', '')
            envs = self.proj_settings.config_parser.getdefault(
                'env variables', 'env', '')
            for env in envs.split(' '):
                self.ui_creator.kivy_console.environment[
                    env[:env.find('=')]] = env[env.find('=')+1:]

        for _file in self.project_loader.file_list:
            if 'main.py' in os.path.basename(_file):
                self.ui_creator.kivy_console.stdin.write(
                    '"%s" "%s" %s' % (python_path, _file, args))
                self.ui_creator.tab_pannel.switch_to(
                    self.ui_creator.tab_pannel.tab_list[2])
                return

        self.ui_creator.kivy_console.stdin.write(
            '"%s" "%s" %s' % (python_path, self.project_loader._app_file, args))

        self.ui_creator.tab_pannel.switch_to(
            self.ui_creator.tab_pannel.tab_list[2])

    def on_sandbox_getting_exception(self, *args):
        '''Event Handler for
           :class:`~designer.uix.designer_sandbox.DesignerSandbox`
           on_getting_exception event. This function will add exception
           string in error_console.
        '''

        s = traceback.format_list(traceback.extract_tb(
            self.ui_creator.playground.sandbox.tb))
        s = '\n'.join(s)
        to_insert = "Exception:\n" + s + '\n' + \
            "{!r}".format(self.ui_creator.playground.sandbox.exception)
        text = self.ui_creator.error_console.text + to_insert + '\n\n'
        self.ui_creator.error_console.text = text
        if self.ui_creator.playground.sandbox.error_active:
            self.ui_creator.tab_pannel.switch_to(
                self.ui_creator.tab_pannel.tab_list[0])

        self.ui_creator.playground.sandbox.error_active = False

    def action_btn_about_pressed(self, *args):
        '''Event handler for 'on_release' event of DesignerActionButton
           "About Kivy Designer"
        '''
        self.about_dlg = AboutDialog()
        self._popup = Popup(title='About Kivy Designer',
                            content=self.about_dlg,
                            size_hint=(None, None), size=(600, 400),
                            auto_dismiss=False)
        self._popup.open()
        self.about_dlg.bind(on_cancel=self._cancel_popup)


class DesignerApp(App):

    widget_focused = ObjectProperty(allownone=True)
    '''Currently focused widget
    '''

    title = 'Kivy Designer'

    def on_stop(self, *args):
        self.root.ui_creator.py_console.exit()

    def build(self):
        Factory.register('Playground', module='designer.playground')
        Factory.register('Toolbox', module='designer.toolbox')
        Factory.register('StatusBar', module='designer.statusbar')
        Factory.register('PropertyViewer', module='designer.propertyviewer')
        Factory.register('EventViewer', module='designer.eventviewer')
        Factory.register('WidgetsTree', module='designer.nodetree')
        Factory.register('UICreator', module='designer.ui_creator')
        Factory.register('DesignerContent',
                         module='designer.designer_content')
        Factory.register('KivyConsole', module='designer.uix.kivy_console')
        Factory.register('PythonConsole', module='designer.uix.py_console')
        Factory.register('DesignerContent',
                         module='designer.uix.designer_sandbox')
        Factory.register('EventDropDown', module='designer.eventviewer')
        Factory.register('DesignerActionPrevious',
                         module='designer.uix.designer_action_items')
        Factory.register('DesignerActionGroup',
                         module='designer.uix.designer_action_items')
        Factory.register('DesignerActionButton',
                         module='designer.uix.designer_action_items')
        Factory.register('DesignerActionSubMenu',
                         module='designer.uix.designer_action_items')
        Factory.register('DesignerStartPage', module='designer.start_page')
        Factory.register('DesignerLinkLabel', module='designer.start_page')
        Factory.register('RecentFilesBox', module='designer.start_page')
        Factory.register('ContextMenu', module='designer.uix.contextual')

        self._widget_focused = None
        self.root = Designer()
        Clock.schedule_once(self._setup)

    def _setup(self, *args):
        '''To setup the properties of different classes
        '''

        self.root.proj_tree_view = self.root.designer_content.tree_view
        self.root.ui_creator = self.root.designer_content.ui_creator
        self.root.statusbar.playground = self.root.ui_creator.playground
        self.root.project_loader.kv_code_input = \
            self.root.ui_creator.kv_code_input
        self.root.project_loader.tab_pannel = \
            self.root.designer_content.tab_pannel
        self.root.ui_creator.playground.undo_manager = self.root.undo_manager
        self.root.ui_creator.kv_code_input.project_loader = \
            self.root.project_loader
        self.root.ui_creator.kv_code_input.statusbar = self.root.statusbar
        self.root.ui_creator.widgettree.project_loader = \
            self.root.project_loader
        self.root.ui_creator.eventviewer.project_loader = \
            self.root.project_loader
        self.root.ui_creator.eventviewer.designer_tabbed_panel = \
            self.root.designer_content.tab_pannel
        self.root.ui_creator.eventviewer.statusbar = self.root.statusbar
        self.root.statusbar.bind(height=self.root.on_statusbar_height)
        self.root.actionbar.bind(height=self.root.on_actionbar_height)
        self.root.ui_creator.playground.sandbox = DesignerSandbox()
        self.root.ui_creator.playground.add_widget(
            self.root.ui_creator.playground.sandbox)
        self.root.ui_creator.playground.sandbox.pos = \
            self.root.ui_creator.playground.pos
        self.root.ui_creator.playground.sandbox.size = \
            self.root.ui_creator.playground.size
        self.root.start_page.recent_files_box.root = self.root

        self.root.ui_creator.playground.sandbox.bind(
            on_getting_exception=self.root.on_sandbox_getting_exception)

        self.bind(widget_focused=
                  self.root.ui_creator.propertyviewer.setter('widget'))
        self.bind(widget_focused=
                  self.root.ui_creator.eventviewer.setter('widget'))

        self.focus_widget(self.root.ui_creator.playground.root)

        self.create_kivy_designer_dir()
        self.root.start_page.recent_files_box.add_recent(
            self.root.recent_manager.list_files)

        self.root.fill_recent_menu()

    def create_kivy_designer_dir(self):
        '''To create the ~/.kivy-designer dir
        '''

        if not os.path.exists(get_kivy_designer_dir()):
            os.mkdir(get_kivy_designer_dir())

    def create_draggable_element(self, widgetname, touch, widget=None):
        '''Create PlagroundDragElement and make it draggable
           until the touch is released also search default args if exist
        '''
        container = None
        if not widget:
            default_args = {}
            for options in widgets:
                if len(options) > 2:
                    default_args = options[2]

            container = self.root.ui_creator.playground.\
                get_playground_drag_element(widgetname, touch, **default_args)

        else:
            container = PlaygroundDragElement(
                playground=self.root.ui_creator.playground, child=widget)
            touch.grab(container)
            touch.grab_current = container
            container.on_touch_move(touch)
            container.center_x = touch.x
            container.y = touch.y + 20

        if container:
            self.root.add_widget(container)
        else:
            self.root.statusbar.show_message("Cannot create %s" % widgetname)

        container.widgettree = self.root.ui_creator.widgettree
        return container

    def focus_widget(self, widget, *largs):
        '''Called when a widget is select in Playground. It will also draw
           lines around focussed widget.
        '''

        if self._widget_focused and (widget is None or
                                     self._widget_focused[0] != widget):
            fwidget = self._widget_focused[0]
            for instr in self._widget_focused[1:]:
                fwidget.canvas.after.remove(instr)
            self._widget_focused = []

        self.widget_focused = widget
        self.root.ui_creator.widgettree.refresh()

        if not widget:
            return

        x, y = widget.pos
        right, top = widget.right, widget.top
        points = [x, y, right, y, right, top, x, top]
        if self._widget_focused:
            line = self._widget_focused[2]
            line.points = points
        else:
            from kivy.graphics import Color, Line
            with widget.canvas.after:
                color = Color(.42, .62, .65)
                line = Line(points=points, close=True, width=2.)
            self._widget_focused = [widget, color, line]

        self.root.ui_creator.playground.clicked = True
        self.root.on_show_edit()

########NEW FILE########
__FILENAME__ = common

#: Describe the widgets to show in the toolbox,
#: and anything else needed for the
#: designer. The base is a list, because python dict don't preserve the order.
#: The first field is the name used for Factory.<name>
#: The second field represent a category name

widgets = [
    ('Label', 'base', {'text': 'A label'}),
    ('Button', 'base', {'text': 'A button'}),
    ('CheckBox', 'base'),
    ('Image', 'base'),
    ('Slider', 'base'),
    ('ProgressBar', 'base'),
    ('TextInput', 'base'),
    ('ToggleButton', 'base'),
    ('Switch', 'base'),
    ('Video', 'base'),
    ('ScreenManager', 'base'),
    ('Screen', 'base'),
    ('Carousel', 'base'),
    ('TabbedPanel', 'base'),
    ('GridLayout', 'layout', {'cols': 2}),
    ('BoxLayout', 'layout'),
    ('AnchorLayout', 'layout'),
    ('StackLayout', 'layout'),
    ('FileChooserListView', 'complex'),
    ('FileChooserIconView', 'complex'),
    ('Popup', 'complex'),
    ('Spinner', 'complex'),
    ('VideoPlayer', 'complex'),
    ('ActionButton', 'complex'),
    ('ActionPrevious', 'complex'),
    ('ScrollView', 'behavior'),
    #('VKeybord', 'complex'),
    #('Scatter', 'behavior'),
    #('StencilView', 'behavior'),
]

########NEW FILE########
__FILENAME__ = confirmation_dialog
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.label import Label
from kivy.uix.button import Button
from kivy.properties import StringProperty


class ConfirmationDialog(BoxLayout):
    '''ConfirmationDialog shows a confirmation message with two buttons
       "Yes" and "No". It may be used for confirming user about an operation.
       It emits 'on_ok' when "Yes" is pressed and 'on_cancel' when "No" is
       pressed.
    '''

    message = StringProperty('')
    '''It is the message to be shown
       :data:`message` is a :class:`~kivy.properties.StringProperty`
    '''

    __events__ = ('on_ok', 'on_cancel')

    def __init__(self, message):
        super(ConfirmationDialog, self).__init__()
        self.message = message

    def on_ok(self, *args):
        pass

    def on_cancel(self, *args):
        pass

########NEW FILE########
__FILENAME__ = designer_content
import os

from kivy.app import App
from kivy.uix.floatlayout import FloatLayout
from kivy.factory import Factory
from kivy.properties import ObjectProperty, ListProperty
from kivy.uix.tabbedpanel import TabbedPanel, TabbedPanelItem
from kivy.uix.treeview import TreeViewLabel
from designer.uix.py_code_input import PyCodeInput, PyScrollView


class DesignerContent(FloatLayout):
    '''This class contains the body of the Kivy Designer. It contains,
       Project Tree and TabbedPanel.
    '''

    ui_creator = ObjectProperty(None)
    '''This property refers to the :class:`~designer.ui_creator.UICreator`
       instance. As there can only be one
       :data:`ui_creator` is a :class:`~kivy.properties.ObjectProperty`
    '''

    tree_toolbox_tab_panel = ObjectProperty(None)
    '''TabbedPanel containing Toolbox and Project Tree. Instance of
       :class:`~designer.designer_content.DesignerTabbedPanel`
    '''

    splitter_tree = ObjectProperty(None)
    '''Reference to the splitter parent of tree_toolbox_tab_panel.
       :data:`splitter_toolbox` is an
       :class:`~kivy.properties.ObjectProperty`
    '''

    toolbox = ObjectProperty(None)
    '''Reference to the :class:`~designer.toolbox.Toolbox` instance.
       :data:`toolbox` is an :class:`~kivy.properties.ObjectProperty`
    '''

    tree_view = ObjectProperty(None)
    '''This property refers to Project Tree. Project Tree displays project's
       py files under its parent directories. Clicking on any of the file will
       open it up for editing.
       :data:`tree_view` is a :class:`~kivy.properties.ObjectProperty`
    '''

    tab_pannel = ObjectProperty(None)
    '''This property refers to the instance of
       :class:`~designer.designer_content.DesignerTabbedPanel`.
       :data:`tab_pannel` is a :class:`~kivy.properties.ObjectProperty`
    '''

    def update_tree_view(self, proj_loader):
        '''This function is used to insert all the py files detected.
           as a node in the Project Tree.
        '''

        self.proj_loader = proj_loader

        #Fill nodes with file and directories
        self._root_node = self.tree_view.root
        for _file in proj_loader.file_list:
            self.add_file_to_tree_view(_file)

    def add_file_to_tree_view(self, _file):
        '''This function is used to insert py file given by it's path argument
           _file. It will also insert any directory node if not present.
        '''

        self.tree_view.root_options = dict(text='')
        dirname = os.path.dirname(_file)
        dirname = dirname.replace(self.proj_loader.proj_dir, '')
        #The way os.path.dirname works, there will never be '/' at the end
        #of a directory. So, there will always be '/' at the starting
        #of 'dirname' variable after removing proj_dir

        #This algorithm first breaks path into its components
        #and creates a list of these components.
        _dirname = dirname
        _basename = 'a'
        list_path_components = []
        while _basename != '':
            _split = os.path.split(_dirname)
            _dirname = _split[0]
            _basename = _split[1]
            list_path_components.insert(0, _split[1])

        if list_path_components[0] == '':
            del list_path_components[0]

        #Then it traverses from root_node to its children searching from
        #each component in the path. If it doesn't find any component
        #related with node then it creates it.
        node = self._root_node
        while list_path_components != []:
            found = False
            for _node in node.nodes:
                if _node.text == list_path_components[0]:
                    node = _node
                    found = True
                    break

            if not found:
                for component in list_path_components:
                    _node = TreeViewLabel(text=component)
                    self.tree_view.add_node(_node, node)
                    node = _node
                list_path_components = []
            else:
                del list_path_components[0]

        #Finally add file_node with node as parent.
        file_node = TreeViewLabel(text=os.path.basename(_file))
        file_node.bind(on_touch_down=self._file_node_clicked)
        self.tree_view.add_node(file_node, node)

        self.tree_view.root_options = dict(
            text=os.path.basename(self.proj_loader.proj_dir))

    def _file_node_clicked(self, instance, touch):
        '''This is emmited whenever any file node of Project Tree is
           clicked. This will open up a tab in DesignerTabbedPanel, for
           editing that py file.
        '''

        #Travel upwards and find the path of instance clicked
        path = instance.text
        parent = instance.parent_node
        while parent != self._root_node:
            _path = parent.text
            path = os.path.join(_path, path)
            parent = parent.parent_node

        full_path = os.path.join(self.proj_loader.proj_dir, path)
        self.tab_pannel.open_file(full_path, path)


class DesignerTabbedPanel(TabbedPanel):
    '''DesignerTabbedPanel is used to display files opened up in tabs with
       :class:`~designer.ui_creator.UICreator`
       Tab as a special one containing all features to edit the UI.
    '''

    list_py_code_inputs = ListProperty([])
    '''This list contains reference to all the PyCodeInput's opened till now
       :data:`list_py_code_inputs` is a :class:`~kivy.properties.ListProperty`
    '''

    def open_file(self, path, rel_path, switch_to=True):
        '''This will open py file for editing in the DesignerTabbedPanel.
        '''

        for i, code_input in enumerate(self.list_py_code_inputs):
            if code_input.rel_file_path == rel_path:
                self.switch_to(self.tab_list[len(self.tab_list) - i - 2])
                return

        panel_item = DesignerTabbedPanelItem(text=os.path.basename(path))
        f = open(path, 'r')
        scroll = PyScrollView()
        _py_code_input = scroll.code_input
        _py_code_input.rel_file_path = rel_path
        _py_code_input.text = f.read()
        _py_code_input.bind(
            on_show_edit=App.get_running_app().root.on_show_edit)
        f.close()
        self.list_py_code_inputs.append(_py_code_input)
        panel_item.content = scroll
        self.add_widget(panel_item)
        if switch_to:
            self.switch_to(self.tab_list[0])


class DesignerTabbedPanelItem(TabbedPanelItem):
    pass

########NEW FILE########
__FILENAME__ = designer_settings
import os
import os.path
import shutil
import sys

from kivy.properties import ObjectProperty
from kivy.config import ConfigParser
from kivy.uix.settings import Settings, SettingTitle
from kivy.uix.label import Label
from kivy.uix.button import Button

from designer.helper_functions import get_kivy_designer_dir
import designer

DESIGNER_CONFIG_FILE_NAME = 'config.ini'


class DesignerSettings(Settings):
    '''Subclass of :class:`kivy.uix.settings.Settings` responsible for
       showing settings of Kivy Designer.
    '''

    config_parser = ObjectProperty(None)
    '''Config Parser for this class. Instance
       of :class:`kivy.config.ConfigParser`
    '''

    def load_settings(self):
        '''This function loads project settings
        '''
        self.config_parser = ConfigParser()
        DESIGNER_CONFIG = os.path.join(get_kivy_designer_dir(),
                                       DESIGNER_CONFIG_FILE_NAME)

        _dir = os.path.dirname(designer.__file__)
        _dir = os.path.split(_dir)[0]

        if not os.path.exists(DESIGNER_CONFIG):
            shutil.copyfile(os.path.join(_dir,
                                         DESIGNER_CONFIG_FILE_NAME),
                            DESIGNER_CONFIG)

        self.config_parser.read(DESIGNER_CONFIG)
        self.add_json_panel('Kivy Designer Settings', self.config_parser,
                            os.path.join(_dir, 'designer', 'settings', 'designer_settings.json'))

        path = self.config_parser.getdefault(
            'global', 'python_shell_path', '')

        if path == "":
            self.config_parser.set('global', 'python_shell_path',
                                   sys.executable)
            self.config_parser.write()

    def on_config_change(self, *args):
        '''This function is default handler of on_config_change event.
        '''
        self.config_parser.write()
        super(DesignerSettings, self).on_config_change(*args)

########NEW FILE########
__FILENAME__ = eventviewer
from kivy.uix.textinput import TextInput
from kivy.properties import ObjectProperty, StringProperty, BooleanProperty
from kivy.clock import Clock
from kivy.uix.dropdown import DropDown
from kivy.uix.button import Button
from kivy.app import App
from kivy.uix.scrollview import ScrollView

from designer.uix.info_bubble import InfoBubble
from designer.propertyviewer import PropertyViewer,\
    PropertyTextInput, PropertyLabel

import re


class EventHandlerTextInput(TextInput):
    '''EventHandlerTextInput is used to display/change/remove EventHandler
       for an event
    '''

    eventwidget = ObjectProperty(None)
    '''Current selected widget
       :data:`eventwidget` is a :class:`~kivy.properties.ObjectProperty`
    '''

    eventname = StringProperty(None)
    '''Name of current event
       :data:`eventname` is a :class:`~kivy.properties.ObjectProperty`
    '''

    kv_code_input = ObjectProperty()
    '''Reference to KVLangArea
       :data:`kv_code_input` is a :class:`~kivy.properties.ObjectProperty`
    '''

    text_inserted = BooleanProperty(None)
    '''Specifies whether text has been inserted or not
       :data:`text_inserted` is a :class:`~kivy.properties.ObjectProperty`
    '''

    project_loader = ObjectProperty(None)
    '''Reference to ProjectLoader
       :data:`project_loader` is a :class:`~kivy.properties.ObjectProperty`
    '''

    info_message = StringProperty(None)
    '''Message to be displayed by InfoBubble
       :data:`info_message` is a :class:`~kivy.properties.StringProperty`
    '''

    dropdown = ObjectProperty(None)
    '''DropDown which will be displayed to show possible
       functions for that event
       :data:`dropdown` is a :class:`~kivy.properties.ObjectProperty`
    '''

    def on_touch_down(self, touch):
        '''Default handler for 'on_touch_down' event
        '''
        if self.collide_point(*touch.pos):
            self.info_bubble = InfoBubble(message=self.info_message)
            self.info_bubble.show(self.pos, 1)

        return super(EventHandlerTextInput, self).on_touch_down(touch)

    def show_drop_down_for_widget(self, widget):
        '''Show all functions for a widget in a Dropdown.
        '''
        self.dropdown = DropDown()
        list_funcs = dir(widget)
        for func in list_funcs:
            if '__' not in func and hasattr(getattr(widget, func), '__call__'):
                btn = Button(text=func, size_hint=(None, None),
                             size=(100, 30), shorten=True)
                self.dropdown.add_widget(btn)
                btn.bind(on_release=lambda btn: self.dropdown.select(btn.text))
                btn.text_size = [btn.size[0] - 4, btn.size[1]]
                btn.valign = 'middle'

        self.dropdown.open(self)
        self.dropdown.pos = (self.x, self.y)
        self.dropdown.bind(on_select=self._dropdown_select)

    def _dropdown_select(self, instance, value):
        '''Event handler for 'on_select' event of self.dropdown
        '''
        self.text += value

    def on_text(self, instance, value):
        '''Default event handler for 'on_text'
        '''
        if not self.kv_code_input:
            return

        self.kv_code_input.set_event_handler(self.eventwidget,
                                             self.eventname,
                                             self.text)
        if self.text and self.text[-1] == '.':
            if self.text == 'self.':
                self.show_drop_down_for_widget(self.eventwidget)

            elif self.text == 'root.':
                self.show_drop_down_for_widget(
                    self.project_loader.root_rule.widget)

            else:
                _id = self.text.replace('.', '')
                root = self.project_loader.root_rule.widget
                widget = None

                if _id in root.ids:
                    widget = root.ids[_id]

                if widget:
                    self.show_drop_down_for_widget(widget)

        elif self.dropdown:
            self.dropdown.dismiss()


class NewEventTextInput(TextInput):
    '''NewEventTextInput is TextInput which is used to create a new event
       for a widget. When event is created then on_create_event is emitted
    '''

    __events__ = ('on_create_event',)

    info_message = StringProperty(None)
    '''Message which will be displayed in the InfoBubble
       :data:`info_message` is a :class:`~kivy.properties.StringProperty`
    '''

    def on_create_event(self, *args):
        '''Default event handler for 'on_create_event'
        '''
        pass

    def insert_text(self, substring, from_undo=False):
        '''Override of 'insert_text' of :class:`kivy.uix.textinput.TextInput`
        '''
        if '\n' in substring:
            #Enter pressed create a new event
            substring = substring.replace('\n', '')
            if self.text[:3] == 'on_':
                self.dispatch('on_create_event')

        super(NewEventTextInput, self).insert_text(substring, from_undo)

    def on_touch_down(self, touch):
        '''Default handler for 'on_touch_down' event.
        '''
        if self.collide_point(*touch.pos):
            self.info_bubble = InfoBubble(message=self.info_message)
            self.info_bubble.show(self.pos, 1)

        return super(NewEventTextInput, self).on_touch_down(touch)


class EventLabel(PropertyLabel):
    pass


class EventViewer(PropertyViewer):
    '''EventViewer, to display all the events associated with the widget and
       event handler.
    '''

    project_loader = ObjectProperty(None)
    '''Reference to ProjectLoader
       :data:`project_loader` is a :class:`~kivy.properties.ObjectProperty`
    '''

    designer_tabbed_panel = ObjectProperty(None)
    '''Reference to DesignerTabbedPanel
       :data:`designer_tabbed_panel` is a
       :class:`~kivy.properties.ObjectProperty`
    '''

    statusbar = ObjectProperty(None)
    '''Reference to Statusbar
       :data:`statusbar` is a :class:`~kivy.properties.ObjectProperty`
    '''

    def on_widget(self, instance, value):
        '''Default handler for change of 'widget' property
        '''
        self.clear()
        if value is not None:
            self.discover(value)

    def clear(self):
        '''To clear :data:`prop_list`.
        '''
        self.prop_list.clear_widgets()

    def discover(self, value):
        '''To discover all properties and add their
           :class:`~designer.propertyviewer.PropertyLabel` and
           :class:`~designer.propertyviewer.PropertyBoolean`/
           :class:`~designer.propertyviewer.PropertyTextInput`
           to :data:`prop_list`.
        '''

        add = self.prop_list.add_widget
        events = value.events()
        for event in events:
            ip = self.build_for(event)
            if not ip:
                continue
            add(EventLabel(text=event))
            add(ip)

        if self.project_loader.is_widget_custom(self.widget):
            #Allow adding a new event only if current widget is a custom rule
            add(EventLabel(text='Type and press enter to \n'
                           'create a new event'))
            txt = NewEventTextInput(
                multiline=True,
                info_message='Type and press enter to create a new event')
            txt.bind(on_create_event=self.create_event)
            add(txt)

    def create_event(self, txt):
        '''This function will create a new event given by 'txt' to the widget.
        '''
        #Find the python file of widget
        py_file = None
        for rule in self.project_loader.class_rules:
            if rule.name == type(self.widget).__name__:
                py_file = rule.file
                break

        #Open it in DesignerTabbedPannel
        rel_path = py_file.replace(self.project_loader.proj_dir, '')
        if rel_path[0] == '/' or rel_path[0] == '\\':
            rel_path = rel_path[1:]

        self.designer_tabbed_panel.open_file(py_file, rel_path,
                                             switch_to=False)
        self.rel_path = rel_path
        self.txt = txt
        Clock.schedule_once(self._add_event)

    def _add_event(self, *args):
        '''This function will create a new event given by 'txt' to the widget.
        '''
        #Find the class definition
        py_code_input = None
        txt = self.txt
        rel_path = self.rel_path
        for code_input in self.designer_tabbed_panel.list_py_code_inputs:
            if code_input.rel_file_path == rel_path:
                py_code_input = code_input
                break

        pos = -1
        for searchiter in re.finditer(r'class\s+%s\(.+\):' %
                                      type(self.widget).__name__,
                                      py_code_input.text):
            pos = searchiter.end()

        if pos != -1:
            col, row = py_code_input.get_cursor_from_index(pos)
            lines = py_code_input.text.splitlines()
            found_events = False
            events_row = row
            for i in range(row, len(lines)):
                if re.match(r'__events__\s*=\s*\(.+\)', lines[i]):
                    found_events = True
                    events_row = i
                    break

                elif re.match('class\s+[\w\d\_]+\(.+\):', lines[i]):
                    break

                elif re.match('def\s+[\w\d\_]+\(.+\):', lines[i]):
                    break

            if found_events:
                events_col = lines[events_row].rfind(')') - 1
                py_code_input.cursor = events_row, events_col
                py_code_input.insert_text(txt.text)

            else:
                py_code_input.text = py_code_input.text[:pos] + \
                    '\n    __events__=("%s",)\n'\
                    '    def %s(self, *args):\n        pass' % \
                    (txt.text, txt.text) +\
                    py_code_input.text[pos:]
            self.statusbar.show_message('New Event Created you must save '
                                        'project for changes to take effect')

    def build_for(self, name):
        '''To create :class:`~designer.propertyviewer.PropertyBoolean`/
           :class:`~designer.propertyviewer.PropertyTextInput`
           for Property 'name'
        '''
        text = self.kv_code_input.get_property_value(self.widget, name)
        return EventHandlerTextInput(
            kv_code_input=self.kv_code_input, eventname=name,
            eventwidget=self.widget, multiline=False, text=text,
            project_loader=self.project_loader,
            info_message="Set event handler for event %s" % (name))

########NEW FILE########
__FILENAME__ = helper_functions
'''This file contains a few functions which are required by more than one
   module of Kivy Designer.
'''

import os

from kivy.app import App


def get_indent_str(indentation):
    '''Return a string consisting only indentation number of spaces
    '''
    i = 0
    s = ''
    while i < indentation:
        s += ' '
        i += 1

    return s


def get_line_end_pos(string, line):
    '''Returns the end position of line in a string
    '''
    _line = 0
    _line_pos = -1
    _line_pos = string.find('\n', _line_pos + 1)
    while _line < line:
        _line_pos = string.find('\n', _line_pos + 1)
        _line += 1

    return _line_pos


def get_line_start_pos(string, line):
    '''Returns starting position of line in a string
    '''
    _line = 0
    _line_pos = -1
    _line_pos = string.find('\n', _line_pos + 1)
    while _line < line - 1:
        _line_pos = string.find('\n', _line_pos + 1)
        _line += 1

    return _line_pos


def get_indent_level(string):
    '''Returns the indentation of first line of string
    '''
    lines = string.splitlines()
    lineno = 0
    line = lines[lineno]
    indent = 0
    total_lines = len(lines)
    while line < total_lines and indent == 0:
        indent = len(line)-len(line.lstrip())
        line = lines[lineno]
        line += 1

    return indent


def get_indentation(string):
    '''Returns the number of indent spaces in a string
    '''
    count = 0
    for s in string:
        if s == ' ':
            count += 1
        else:
            return count

    return count


def get_kivy_designer_dir():
    '''This function returns kivy-designer's config dir
    '''
    user_dir = os.path.join(App.get_running_app().user_data_dir,
                            '.kivy-designer')
    if not os.path.exists(user_dir):
        os.makedirs(user_dir)
    return user_dir

########NEW FILE########
__FILENAME__ = help_dialog
from kivy.uix.boxlayout import BoxLayout
from kivy.properties import ObjectProperty


class HelpDialog(BoxLayout):
    '''HelpDialog, in which help will be displayed from help.rst.
       It emits 'on_cancel' event when 'Cancel' button is released.
    '''

    rst = ObjectProperty(None)
    '''rst is reference to `kivy.uix.rst.RstDocument` to display help from
       help.rst
    '''

    __events__ = ('on_cancel',)

    def on_cancel(self, *args):
        '''Default handler for 'on_cancel' event
        '''
        pass


class AboutDialog(BoxLayout):
    '''AboutDialog, to display about information.
       It emits 'on_cancel' event when 'Cancel' button is released.
    '''

    __events__ = ('on_cancel',)

    def on_cancel(self, *args):
        '''Default handler for 'on_cancel' event
        '''
        pass

########NEW FILE########
__FILENAME__ = new_dialog
import designer

from kivy.uix.boxlayout import BoxLayout
from kivy.uix.listview import ListView
from kivy.properties import ObjectProperty
from kivy.adapters.listadapter import ListAdapter
from kivy.uix.image import Image
from os.path import join, dirname, split
from functools import partial
from kivy.factory import Factory

NEW_PROJECTS = {
    'FloatLayout': ('template_floatlayout_kv',
                    'template_floatlayout_py'),
    'BoxLayout': ('template_boxlayout_kv',
                  'template_boxlayout_py'),
    'ScreenManager': ('template_screen_manager_kv',
                      'template_screen_manager_py'),
    'ActionBar': ('template_actionbar_kv',
                  'template_actionbar_py'),
    'Carousel and ActionBar': ('template_actionbar_carousel_kv',
                               'template_actionbar_carousel_py'),
    'ScreenManager and ActionBar': ('template_screen_manager_actionbar_kv',
                                    'template_screen_manager_actionbar_py'),
    'TabbedPanel': ('template_tabbed_panel_kv',
                    'template_tabbed_panel_py'),
    'TextInput and ScrollView': ('template_textinput_scrollview_kv',
                                 'template_textinput_scrollview_py')}

NEW_TEMPLATES_DIR = 'new_templates'
NEW_TEMPLATE_IMAGE_PATH = join(NEW_TEMPLATES_DIR, 'images')


class NewProjectDialog(BoxLayout):

    listview = ObjectProperty(None)
    ''':class:`~kivy.uix.listview.ListView` used for showing file paths.
       :data:`listview` is a :class:`~kivy.properties.ObjectProperty`
    '''

    select_button = ObjectProperty(None)
    ''':class:`~kivy.uix.button.Button` used to select the list item.
       :data:`select_button` is a :class:`~kivy.properties.ObjectProperty`
    '''

    cancel_button = ObjectProperty(None)
    ''':class:`~kivy.uix.button.Button` to cancel the dialog.
       :data:`cancel_button` is a :class:`~kivy.properties.ObjectProperty`
    '''

    adapter = ObjectProperty(None)
    ''':class:`~kivy.uix.listview.ListAdapter` used for selecting files.
       :data:`adapter` is a :class:`~kivy.properties.ObjectProperty`
    '''

    image = ObjectProperty(None)
    '''Type of :class:`~kivy.uix.image.Image` to display image of selected
       new template.
       :data:`image` is a :class:`~kivy.properties.ObjectProperty`
    '''

    list_parent = ObjectProperty(None)
    '''Parent of listview.
       :data:`list_parent` is a :class:`~kivy.properties.ObjectProperty`
    '''

    __events__ = ('on_select', 'on_cancel')

    def __init__(self, **kwargs):
        super(NewProjectDialog, self).__init__(**kwargs)
        item_strings = NEW_PROJECTS.keys()
        self.adapter = ListAdapter(cls=Factory.DesignerListItemButton, data=item_strings,
                                   selection_mode='single',
                                   allow_empty_selection=False)
        self.adapter.bind(on_selection_change=self.on_adapter_selection_change)
        self.listview = ListView(adapter=self.adapter)
        self.listview.size_hint = (0.5, 1)
        self.listview.pos_hint = {'top': 1}
        self.list_parent.add_widget(self.listview, 1)
        self.on_adapter_selection_change(self.adapter)

    def on_adapter_selection_change(self, adapter):
        '''Event handler for 'on_selection_change' event of adapter.
        '''
        name = adapter.selection[0].text.lower() + '.png'
        name = name.replace(' and ', '_')
        image_source = join(NEW_TEMPLATE_IMAGE_PATH, name)
        _dir = dirname(designer.__file__)
        _dir = split(_dir)[0]
        image_source = join(_dir, image_source)
        parent = self.image.parent
        parent.remove_widget(self.image)
        self.image = Image(source=image_source)
        parent.add_widget(self.image)

    def on_select(self, *args):
        '''Default Event Handler for 'on_select' event
        '''
        pass

    def on_cancel(self, *args):
        '''Default Event Handler for 'on_cancel' event
        '''
        pass

    def on_select_button(self, *args):
        '''Event Handler for 'on_release' of select button.
        '''
        self.select_button.bind(on_press=partial(self.dispatch, 'on_select'))

    def on_cancel_button(self, *args):
        '''Event Handler for 'on_release' of cancel button.
        '''
        self.cancel_button.bind(on_press=partial(self.dispatch, 'on_cancel'))

########NEW FILE########
__FILENAME__ = nodetree
from kivy.uix.treeview import TreeViewLabel
from kivy.uix.scrollview import ScrollView
from kivy.properties import ObjectProperty, BooleanProperty
from kivy.app import App
from kivy.clock import Clock
from kivy.uix.tabbedpanel import TabbedPanel

from designer.common import widgets


class WidgetTreeElement(TreeViewLabel):
    '''WidgetTreeElement represents each node in WidgetsTree
    '''
    node = ObjectProperty(None)


class WidgetsTree(ScrollView):
    '''WidgetsTree class is used to display the Root Widget's Tree in a
       Tree hierarchy.
    '''
    playground = ObjectProperty(None)
    '''This property is an instance of :class:`~designer.playground.Playground`
       :data:`playground` is a :class:`~kivy.properties.ObjectProperty`
    '''

    tree = ObjectProperty(None)
    '''This property is an instance of :class:`~kivy.uix.treeview.TreeView`.
       This TreeView is responsible for showing Root Widget's Tree.
       :data:`tree` is a :class:`~kivy.properties.ObjectProperty`
    '''

    project_loader = ObjectProperty()
    '''Reference to :class:`~designer.project_loader.ProjectLoader` instance.
       :data:`project_loader` is a :class:`~kivy.properties.ObjectProperty`
    '''

    dragging = BooleanProperty(False)
    '''Specifies whether a node is dragged or not.
       :data:`dragging` is a :class:`~kivy.properties.BooleanProperty`
    '''

    selected_widget = ObjectProperty(allownone=True)
    '''Current selected widget.
       :data:`dragging` is a :class:`~kivy.properties.ObjectProperty`
    '''

    def recursive_insert(self, node, treenode):
        '''This function will add a node to TreeView, by recursively travelling
           through the Root Widget's Tree.
        '''

        if node is None:
            return

        b = WidgetTreeElement(node=node)
        self.tree.add_node(b, treenode)
        class_rules = self.project_loader.class_rules
        root_widget = self.project_loader.root_rule.widget

        is_child_custom = False
        for rule in class_rules:
            if rule.name == type(node).__name__:
                is_child_custom = True
                break

        is_child_complex = False
        for widget in widgets:
            if widget[0] == type(node).__name__ and widget[1] == 'complex':
                is_child_complex = True
                break

        if root_widget == node or (not is_child_custom and
                                   not is_child_complex):
            if isinstance(node, TabbedPanel):
                self.insert_for_tabbed_panel(node, b)
            else:
                for child in node.children:
                    self.recursive_insert(child, b)

    def insert_for_tabbed_panel(self, node, treenode):
        '''This function will insert nodes in tree specially for TabbedPanel.
        '''
        for tab in node.tab_list:
            b = WidgetTreeElement(node=tab)
            self.tree.add_node(b, treenode)
            self.recursive_insert(tab.content, b)

    def refresh(self, *l):
        '''This function will refresh the tree. It will first remove all nodes
           and then insert them using recursive_insert
        '''
        for node in self.tree.root.nodes:
            self.tree.remove_node(node)

        self.recursive_insert(self.playground.root, self.tree.root)

    def on_touch_up(self, touch):
        '''Default event handler for 'on_touch_up' event.
        '''
        self.dragging = False
        Clock.unschedule(self._start_dragging)
        return super(WidgetsTree, self).on_touch_up(touch)

    def on_touch_down(self, touch):
        '''Default event handler for 'on_touch_down' event.
        '''
        if self.collide_point(*touch.pos) and not self.dragging:
            self.dragging = True
            self.touch = touch
            Clock.schedule_once(self._start_dragging, 2)
            node = self.tree.get_node_at_pos((self.touch.x, self.touch.y))
            if node:
                self.selected_widget = node.node
                self.playground.selected_widget = self.selected_widget
            else:
                self.selected_widget = None
                self.playground.selected_widget = None

        return super(WidgetsTree, self).on_touch_down(touch)

    def _start_dragging(self, *args):
        '''This function will start dragging the widget.
        '''
        if self.dragging and self.selected_widget:
            self.playground.selected_widget = self.selected_widget
            self.playground.dragging = False
            self.playground.touch = self.touch
            self.playground.start_widget_dragging()

########NEW FILE########
__FILENAME__ = playground
import re
import functools

from kivy.uix.scatter import ScatterPlane
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.layout import Layout
from kivy.properties import ObjectProperty, BooleanProperty,\
    OptionProperty, ListProperty
from kivy.app import App
from kivy.uix.filechooser import FileChooserListView, FileChooserIconView
from kivy.uix.floatlayout import FloatLayout
from kivy.uix.sandbox import Sandbox
from kivy.factory import Factory
from kivy.base import EventLoop
from kivy.clock import Clock
from kivy.uix.scatterlayout import ScatterLayout
from kivy.uix.relativelayout import RelativeLayout
from kivy.uix.anchorlayout import AnchorLayout
from kivy.uix.gridlayout import GridLayout
from kivy.uix.carousel import Carousel
from kivy.uix.button import Button
from kivy.uix.screenmanager import ScreenManager, Screen
from kivy.uix.actionbar import ActionBar
from kivy.graphics import Color, Line
from kivy.uix.tabbedpanel import TabbedPanel

from designer.common import widgets
from designer.tree import Tree
from designer.undo_manager import WidgetOperation, WidgetDragOperation
from designer.uix.designer_sandbox import DesignerSandbox


class PlaygroundDragElement(BoxLayout):
    '''An instance of this class is the drag element shown when user tries to
       add a widget to :class:`~designer.playground.Playground` by dragging
       from :class:`~designer.toolbox.Toolbox` to
       :class:`~designer.playground.Playground`.
    '''

    playground = ObjectProperty()
    '''Reference to the :class:`~designer.playground.Playground`
       :data:`playground` is a :class:`~kivy.properties.ObjectProperty`
    '''

    target = ObjectProperty(allownone=True)
    '''Widget where widget is to be added.
       :data:`target` a :class:`~kivy.properties.ObjectProperty`
    '''
    can_place = BooleanProperty(False)
    '''Whether widget can be added or not.
       :data:`can_place` is a :class:`~kivy.properties.BooleanProperty`
    '''

    drag_type = OptionProperty('new widget', options=('new widget',
                                                      'dragndrop'))
    '''Specifies the type of dragging currently done by PlaygroundDragElement.
       If it is 'new widget', then it means a new widget will be added
       If it is 'dragndrop', then it means already created widget is
       drag-n-drop, from one position to another.
       :data:`drag_type` is a :class:`~kivy.properties.OptionProperty`
    '''

    drag_parent = ObjectProperty(None)
    '''Parent of currently dragged widget.
       Will be none if 'drag_type' is 'new widget'
       :data:`drag_parent` is a :class:`~kivy.properties.ObjectProperty`
    '''

    placeholder = ObjectProperty(None)
    '''Instance of :class:`~designer.uix.placeholder`
       :data:`placeholder` is a :class:`~kivy.properties.ObjectProperty`
    '''

    widgettree = ObjectProperty(None)
    '''Reference to class:`~designer.nodetree.WidgetsTree`, the widgettree of
       Designer.
       :data:`widgettree` is a :class:`~kivy.properties.ObjectProperty`
    '''

    child = ObjectProperty(None)
    '''The widget which is currently being dragged.
       :data:`child` is a :class:`~kivy.properties.ObjectProperty`
    '''

    def __init__(self, **kwargs):
        super(PlaygroundDragElement, self).__init__(**kwargs)
        self._prev_target = None
        self.i = 0
        if self.child:
            self.first_pos = (self.child.pos[0], self.child.pos[1])
            self.first_size = (self.child.size[0], self.child.size[1])
            self.first_size_hint = (self.child.size_hint[0],
                                    self.child.size_hint[1])
            self.add_widget(self.child)

    def show_lines_on_child(self, *args):
        '''To schedule Clock's callback for _show_lines_on_child.
        '''
        Clock.schedule_once(self._show_lines_on_child, 0.01)

    def _show_lines_on_child(self, *args):
        '''To show boundaries around the child.
        '''
        x, y = self.child.pos
        right, top = self.child.right, self.child.top
        points = [x, y, right, y, right, top, x, top]
        if hasattr(self, '_canvas_instr'):
            points_equal = True
            for i in range(len(points)):
                if points[i] != self._canvas_instr[1].points[i]:
                    points_equal = False
                    break

            if points_equal:
                return

        self.remove_lines_on_child()
        with self.child.canvas.after:
            color = Color(1, 0.5, 0.8)
            line = Line(points=points, close=True, width=2.)

        self._canvas_instr = [color, line]

    def remove_lines_on_child(self, *args):
        '''Remove lines from canvas of child.
        '''
        if hasattr(self, '_canvas_instr') and \
                self._canvas_instr[1].points[0] != -1:
            try:
                self.child.canvas.after.remove(self._canvas_instr[0])
                self.child.canvas.after.remove(self._canvas_instr[1])
            except ValueError:
                pass

            self._canvas_instr[1].points[0] = -1
            Clock.unschedule(self._show_lines_on_child)

    def is_intersecting_playground(self, x, y):
        '''To determine whether x,y is inside playground
        '''
        if not self.playground:
            return False

        if self.playground.x <= x <= self.playground.right and\
                self.playground.y <= y <= self.playground.top:
            return True

        return False

    def is_intersecting_widgettree(self, x, y):
        '''To determine whether x,y is inside playground
        '''
        if not self.widgettree:
            return False

        if self.widgettree.x <= x <= self.widgettree.right and\
                self.widgettree.y <= y <= self.widgettree.top:
            return True

        return False

    def on_touch_move(self, touch):
        '''This is responsible for moving the drag element and showing where
           the widget it contains will be added.
        '''

        if touch.grab_current is self:
            self.playground.sandbox.error_active = True
            with self.playground.sandbox:
                target = None
                self.center_x = touch.x
                self.y = touch.y + 20
                local = self.playground.to_widget(self.center_x, self.y)
                if self.is_intersecting_playground(self.center_x, self.y):
                    target = self.playground.try_place_widget(
                        self.child, self.center_x, self.y - 20)

                else:
                    #self.widgettree.collide_point(self.center_x, self.y)
                    #not working :(
                    #had to use this method
                    if self.is_intersecting_widgettree(self.center_x, self.y):
                        node = self.widgettree.tree.get_node_at_pos(
                            (self.center_x, touch.y))
                        if node:
                            if node.node == self.child:
                                return True

                            else:
                                while node and \
                                        node.node != self.playground.sandbox:
                                    widget = node.node
                                    if self.playground.allowed_target_for(
                                            widget, self.child):
                                        target = widget
                                        break

                                    node = node.parent_node

                if target == self.child:
                    return True

                if self.child.parent:
                    if self.target:
                        if isinstance(self.target, ScreenManager):
                            if isinstance(self.child, Screen):
                                self.target.remove_widget(self.child)

                            self.target.real_remove_widget(self.child)

                        elif not isinstance(self.target, TabbedPanel):
                            self.target.remove_widget(self.child)

                    if self.child.parent:
                        self.child.parent.remove_widget(self.child)

                if self.drag_type == 'dragndrop':
                    self.can_place = target == self.drag_parent

                else:
                    self.can_place = target is not None

                self.child.pos = self.first_pos
                self.child.size_hint = self.first_size_hint
                self.child.size = self.first_size

                if target:
                    if self.can_place and self.drag_type == 'dragndrop':
                        if self.is_intersecting_playground(self.center_x,
                                                           self.y):
                            x, y = self.playground.to_local(*touch.pos)
                            target2 = self.playground.find_target(
                                x, y, self.playground.root)
                            if target2.parent:
                                _parent = target2.parent
                                target.add_widget(
                                    self.child,
                                    _parent.children.index(target2))

                        else:
                            if self.is_intersecting_widgettree(self.center_x,
                                                               self.y):
                                node = self.widgettree.tree.get_node_at_pos(
                                    (self.center_x, touch.y))
                                if node:
                                    target2 = node.node
                                    if target2.parent:
                                        _parent = target2.parent
                                        target.add_widget(
                                            self.child,
                                            _parent.children.index(target2))
                        self.show_lines_on_child()

                    elif not self.can_place and self.child.parent != self:
                        self.remove_lines_on_child()
                        self.child.pos = (0, 0)
                        self.child.size_hint = (1, 1)
                        self.add_widget(self.child)

                    elif self.can_place and self.drag_type != 'dragndrop':
                        if isinstance(target, ScreenManager):
                            target.real_add_widget(self.child)

                        else:
                            target.add_widget(self.child)

                        self.show_lines_on_child()

                    App.get_running_app().focus_widget(target)

                elif not self.can_place and self.child.parent != self:
                    self.remove_lines_on_child()
                    self.child.pos = (0, 0)
                    self.child.size_hint = (1, 1)
                    self.add_widget(self.child)

                self.target = target

        return True

    def on_touch_up(self, touch):
        '''This is responsible for adding the widget to the parent
        '''
        if touch.grab_current is self:
            self.playground.sandbox.error_active = True
            with self.playground.sandbox:
                touch.ungrab(self)
                widget_from = None
                target = None
                self.center_x = touch.x
                self.y = touch.y + 20
                local = self.playground.to_widget(self.center_x, self.y)
                if self.is_intersecting_playground(self.center_x, self.y):
                    target = self.playground.try_place_widget(
                        self.child, self.center_x, self.y - 20)
                    widget_from = 'playground'

                else:
                    #self.widgettree.collide_point(self.center_x, self.y)
                    #not working :(
                    #had to use this method
                    if self.is_intersecting_widgettree(self.center_x, self.y):
                        node = self.widgettree.tree.get_node_at_pos(
                            (self.center_x, touch.y))
                        if node:
                            widget = node.node
                            while widget and widget != self.playground.sandbox:
                                if self.playground.allowed_target_for(
                                        widget, self.child):
                                    target = widget
                                    widget_from = 'treeview'
                                    break

                                widget = widget.parent
                parent = None
                if self.child.parent != self:
                    parent = self.child.parent
                elif not self.playground.root:
                    parent = self.child.parent

                index = -1

                if self.drag_type == 'dragndrop':
                    self.can_place = target == self.drag_parent and \
                        parent is not None
                else:
                    self.can_place = target is not None and \
                        parent is not None

                if self.target:
                    try:
                        index = self.target.children.index(self.child)
                    except ValueError:
                        pass

                    self.target.remove_widget(self.child)
                    if isinstance(self.target, ScreenManager):
                        self.target.real_remove_widget(self.child)

                elif parent:
                    index = parent.children.index(self.child)
                    parent.remove_widget(self.child)

                if self.can_place or self.playground.root is None:
                    child = self.child
                    if self.drag_type == 'dragndrop':
                        if self.can_place and parent:
                            if widget_from == 'playground':
                                self.playground.place_widget(
                                    child, self.center_x, self.y - 20,
                                    index=index)
                            else:
                                self.playground.place_widget(
                                    child, self.center_x, self.y - 20,
                                    index=index, target=target)

                        elif not self.can_place:
                            self.playground.undo_dragging()

                        self.playground.drag_operation = []

                    else:
                        if widget_from == 'playground':
                            self.playground.place_widget(
                                child, self.center_x, self.y - 20)

                        else:
                            #playground.add_widget_to_parent(child,target)
                            #doesn't work, don't know why :/.
                            #so, has to use this
                            self.playground.add_widget_to_parent(type(child)(),
                                                                 target)

                elif self.drag_type == 'dragndrop':
                    self.playground.undo_dragging()

                self.remove_lines_on_child()
                self.target = None

        if self.parent:
            self.parent.remove_widget(self)

        return True


class Playground(ScatterPlane):
    '''Playground represents the actual area where user will add and delete
       the widgets. It has event on_show_edit, which is emitted whenever
       Playground is clicked.
    '''

    root = ObjectProperty(allownone=True)
    '''This property represents the root widget.
       :data:`root` is a :class:`~kivy.properties.ObjectProperty`
    '''

    selection_mode = BooleanProperty(True)
    '''
       :data:`can_place` is a :class:`~kivy.properties.BooleanProperty`
    '''

    tree = ObjectProperty()

    clicked = BooleanProperty(False)
    '''This property represents whether
       :class:`~designer.playground.Playground` has been clicked or not
       :data:`clicked` is a :class:`~kivy.properties.BooleanProperty`
    '''

    sandbox = ObjectProperty(None)
    '''This property represents the sandbox widget which is added to
       :class:`~designer.playground.Playground`.
       :data:`sandbox` is a :class:`~kivy.properties.ObjectProperty`
    '''

    kv_code_input = ObjectProperty()
    '''This property refers to the
       :class:`~designer.ui_creator.UICreator`'s KVLangArea.
       :data:`kv_code_input` is a :class:`~kivy.properties.ObjectProperty`
    '''

    widgettree = ObjectProperty()
    '''This property refers to the
       :class:`~designer.ui_creator.UICreator`'s WidgetTree.
       :data:`widgettree` is a :class:`~kivy.properties.ObjectProperty`
    '''

    from_drag = BooleanProperty(False)
    '''Specifies whether a widget is dragged or a new widget is added.
       :data:`from_drag` is a :class:`~kivy.properties.BooleanProperty`
    '''

    drag_operation = ListProperty((), allownone=True)
    '''Stores data of drag_operation in form of a tuple.
       drag_operation[0] is the widget which has been dragged.
       drag_operation[1] is the parent of above widget.
       drag_operation[2] is the index of widget in parent's children property.
       :data:`drag_operation` is a :class:`~kivy.properties.ListProperty`
    '''

    _touch_still_down = BooleanProperty(False)
    '''Specifies whether touch is still down or not.
       :data:`_touch_still_down` is a :class:`~kivy.properties.BooleanProperty`
    '''

    dragging = BooleanProperty(False)
    '''Specifies whether currently dragging is performed or not.
       :data:`dragging` is a :class:`~kivy.properties.BooleanProperty`
    '''

    __events__ = ('on_show_edit',)

    def __init__(self, **kwargs):
        super(Playground, self).__init__(**kwargs)
        self.tree = Tree()
        self.keyboard = None
        self.selected_widget = None
        self.undo_manager = None
        self._widget_x = -1
        self._widget_y = -1
        self.widget_to_paste = None

    def on_pos(self, *args):
        '''Default handler for 'on_pos'
        '''
        if self.sandbox:
            self.sandbox.pos = self.pos

    def on_size(self, *args):
        '''Default handler for 'on_size'
        '''
        if self.sandbox:
            self.sandbox.size = self.size

    def on_show_edit(self, *args):
        '''Default handler for 'on_show_edit'
        '''
        pass

    def try_place_widget(self, widget, x, y):
        '''This function is used to determine where to add the widget
        '''

        x, y = self.to_local(x, y)
        return self.find_target(x, y, self.root, widget)

    def place_widget(self, widget, x, y, index=0, target=None):
        '''This function is used to first determine the target where to add
           the widget. Then it add that widget.
        '''
        local_x, local_y = self.to_local(x, y)
        if not target:
            target = self.find_target(local_x, local_y, self.root, widget)

        if not self.from_drag:
            #wx, wy = target.to_widget(x, y)
            #widget.pos = wx, wy
            widget.pos = 0, 0
            self.add_widget_to_parent(widget, target)

        else:
            extra_args = {'x': x, 'y': y, 'index': index}
            self.add_widget_to_parent(widget, target, from_kv=True,
                                      from_undo=True, extra_args=extra_args)

    def drag_wigdet(self, widget, target, extra_args, from_undo=False):
        '''This function will drag widget from one place to another inside
           target
        '''
        extra_args['prev_x'], extra_args['prev_y'] = \
            self.to_parent(self._widget_x, self._widget_y)

        if isinstance(target, FloatLayout) or \
                isinstance(target, ScatterLayout) or \
                isinstance(target, RelativeLayout):
            target.add_widget(widget, self.drag_operation[2])
            widget.pos_hint = {}
            widget.x, widget.y = self.to_local(extra_args['x'],
                                               extra_args['y'])
            self.from_drag = False
            added = True
            local_x, local_y = widget.x - target.x, widget.y - target.y
            self.kv_code_input.set_property_value(
                widget, 'pos_hint', "{'x': %f, 'y': %f}" % (
                    local_x/target.width, local_y/target.height),
                'ListPropery')

            if not from_undo:
                self.undo_manager.push_operation(
                    WidgetDragOperation(widget, target,
                                        self.drag_operation[1],
                                        self.drag_operation[2],
                                        self, extra_args=extra_args))

        elif isinstance(target, BoxLayout) or \
                isinstance(target, AnchorLayout) or \
                isinstance(target, GridLayout):
            target.add_widget(widget, extra_args['index'])
            self.from_drag = False
            added = True
            if 'prev_index' in extra_args:
                self.kv_code_input.shift_widget(widget,
                                                extra_args['prev_index'])

            else:
                self.kv_code_input.shift_widget(widget, self.drag_operation[2])

            if not from_undo:
                self.undo_manager.push_operation(
                    WidgetDragOperation(widget, target,
                                        self.drag_operation[1],
                                        self.drag_operation[2],
                                        self, extra_args=extra_args))

    def add_widget_to_parent(self, widget, target, from_undo=False,
                             from_kv=False, kv_str='', extra_args={}):
        '''This function is used to add the widget to the target.
        '''
        added = False
        if target is None:
            with self.sandbox:
                self.root = widget
                self.sandbox.add_widget(widget)
                widget.size = self.sandbox.size
                added = True

        else:
            with self.sandbox:
                if extra_args and self.from_drag:
                    self.drag_wigdet(widget, target, extra_args=extra_args)

                else:
                    target.add_widget(widget)
                    added = True

        if not added:
            return False

        self.widgettree.refresh()

        if not from_kv:
            self.kv_code_input.add_widget_to_parent(widget, target,
                                                    kv_str=kv_str)
        if not from_undo:
            root = App.get_running_app().root
            root.undo_manager.push_operation(WidgetOperation('add',
                                                             widget, target,
                                                             self, ''))

    def get_widget(self, widgetname, **default_args):
        '''This function is used to get the instance of class of name,
           widgetname.
        '''

        widget = None
        with self.sandbox:
            custom = False
            for _widget in widgets:
                if _widget[0] == widgetname and _widget[1] == 'custom':
                    widget = App.get_running_app().root\
                        .project_loader.get_widget_of_class(widgetname)
                    custom = True
            if not custom:
                try:
                    widget = getattr(Factory, widgetname)(**default_args)
                except:
                    pass

        return widget

    def get_playground_drag_element(self, widgetname, touch, **default_args):
        '''This function will return the desired playground element
           for widgetname.
        '''

        widget = self.get_widget(widgetname, **default_args)
        container = PlaygroundDragElement(playground=self, child=widget)
        touch.grab(container)
        container.center_x = touch.x
        container.y = touch.y + 20
        return container

    def cleanup(self):
        '''This function is used to clean the state of Playground, cleaning
           the changes done by currently opened project.
        '''

        #Cleanup is called when project is created or loaded
        #so this operation shouldn't be recorded in Undo
        if self.root:
            self.remove_widget_from_parent(self.root, from_undo=True,
                                           from_kv=True)

        self.tree = Tree()

    def remove_widget_from_parent(self, widget, from_undo=False,
                                  from_kv=False):
        '''This function is used to remove widget its parent.
        '''

        parent = None
        root = App.get_running_app().root
        if not widget:
            return

        removed_str = ''
        if not from_kv:
            removed_str = self.kv_code_input.remove_widget_from_parent(widget,
                                                                       parent)
        if widget != self.root:
            parent = widget.parent
            if isinstance(parent.parent, Carousel):
                parent.parent.remove_widget(widget)

            elif isinstance(parent, ScreenManager):
                if isinstance(widget, Screen):
                    parent.remove_widget(widget)
                else:
                    parent.real_remove_widget(widget)

            else:
                parent.remove_widget(widget)
        else:
            self.root.parent.remove_widget(self.root)
            self.root = None

        #self.tree.delete(widget)
        root.ui_creator.widgettree.refresh()
        if not from_undo:
            root.undo_manager.push_operation(
                WidgetOperation('remove', widget, parent, self, removed_str))

    def find_target(self, x, y, target, widget=None):
        '''This widget is used to find the widget which collides with x,y
        '''
        if target is None or not target.collide_point(x, y):
            return None

        x, y = target.to_local(x, y)
        class_rules = App.get_running_app().root.project_loader.class_rules

        for child in target.children:
            is_child_custom = False
            for rule in class_rules:
                if rule.name == type(child).__name__:
                    is_child_custom = True
                    break

            is_child_complex = False
            for _widget in widgets:
                if _widget[0] == type(child).__name__ and\
                        _widget[1] == 'complex':
                    is_child_complex = True
                    break

            #if point lies in custom wigdet's child then return custom widget
            if is_child_custom or is_child_complex:
                if not widget and self._custom_widget_collides(child, x, y):
                    return child

                elif widget:
                    if isinstance(child, TabbedPanel):
                        if child.current_tab:
                            _item = self.find_target(
                                x, y, child.current_tab.content)
                            return _item

                    else:
                        return target

            elif isinstance(child.parent, Carousel):
                t = self.find_target(x, y, child, widget)
                return t

            else:
                if not child.collide_point(x, y):
                    continue

                if not self.allowed_target_for(child, widget) and not\
                        child.children:
                    continue

                return self.find_target(x, y, child, widget)

        return target

    def _custom_widget_collides(self, widget, x, y):
        '''This widget is used to find which custom widget collides with x,y
        '''
        if not widget:
            return False

        if widget.collide_point(x, y):
            return True

        x, y = widget.to_local(x, y)
        for child in widget.children:
            if self._custom_widget_collides(child, x, y):
                return True

        return False

    def allowed_target_for(self, target, widget):
        '''This function is used to determine if widget could be added to
           target.
        '''
        # stop on complex widget
        t = target if widget else target.parent
        if isinstance(t, FileChooserListView):
            return False
        if isinstance(t, FileChooserIconView):
            return False

        # stop on custom widget but not root widget
        class_rules = App.get_running_app().root.\
            project_loader.class_rules
        root_widget = App.get_running_app().root.\
            project_loader.root_rule.widget

        # if we don't have widget, always return true
        if widget is None:
            return True

        is_widget_layout = isinstance(widget, Layout)
        is_target_layout = isinstance(target, Layout)
        if is_widget_layout and is_target_layout:
            return True

        if is_target_layout or isinstance(target, Carousel):
            return True

        return False

    def _keyboard_released(self, *args):
        '''Called when self.keyboard is released
        '''
        self.keyboard.unbind(on_key_down=self._on_keyboard_down)
        self.keyboard = None

    def _on_keyboard_down(self, keyboard, keycode, text, modifiers):
        '''Called when a key on keyboard is pressed
        '''
        if modifiers != [] and modifiers[-1] == 'ctrl':
            if keycode[1] == 'c':
                self.do_copy()

            elif keycode[1] == 'v':
                self.do_paste()

            elif keycode[1] == 'x':
                self.do_cut()

            elif keycode[1] == 'a':
                self.do_select_all()

            elif keycode[1] == 'z':
                self.do_undo()

            elif modifiers[0] == 'shift' and keycode[1] == 'z':
                self.do_redo()

        elif keycode[1] == 'delete':
            self.do_delete()

    def do_undo(self):
        '''Undoes the last operation
        '''
        self.undo_manager.do_undo()

    def do_redo(self):
        '''Undoes the last operation
        '''
        self.undo_manager.do_redo()

    def do_copy(self, for_drag=False):
        '''Copy the selected widget
        '''
        base_widget = self.selected_widget
        if base_widget:
            self.widget_to_paste = self.get_widget(type(base_widget).__name__)
            props = base_widget.properties()
            for prop in props:
                if prop == 'id' or prop == 'children':
                    continue

                setattr(self.widget_to_paste, prop,
                        getattr(base_widget, prop))

            self.widget_to_paste.parent = None
            widget_str = self.kv_code_input.\
                get_widget_text_from_kv(base_widget, None)

            if not for_drag:
                widget_str = re.sub(r'\s+id:\s*[\w\d_]+', '', widget_str)
            self._widget_str_to_paste = widget_str

    def do_paste(self):
        '''Paste the selected widget to the current widget
        '''
        parent = self.selected_widget
        if parent and self.widget_to_paste:
            class_rules = App.get_running_app().root.\
                project_loader.class_rules
            root_widget = App.get_running_app().root.\
                project_loader.root_rule.widget
            is_child_custom = False
            for rule in class_rules:
                if rule.name == type(parent).__name__:
                    is_child_custom = True
                    break

            #find appropriate parent to add widget_to_paste
            while parent:
                if isinstance(parent, Layout) and (not is_child_custom
                                                   or root_widget == parent):
                    break

                parent = parent.parent
                is_child_custom = False
                for rule in class_rules:
                    if rule.name == type(parent).__name__:
                        is_child_custom = True
                        break

            if parent is not None:
                self.add_widget_to_parent(self.widget_to_paste,
                                          parent,
                                          kv_str=self._widget_str_to_paste)
                self.widget_to_paste = None

    def do_cut(self):
        '''Cuts the selected widget
        '''
        base_widget = self.selected_widget

        if base_widget and base_widget.parent:
            self.widget_to_paste = base_widget
            self._widget_str_to_paste = self.kv_code_input.\
                get_widget_text_from_kv(base_widget, None)

            self.remove_widget_from_parent(base_widget)

    def do_select_all(self):
        '''Select All widgets which basically means selecting root widget
        '''
        self.selected_widget = self.root
        App.get_running_app().focus_widget(self.root)

    def do_delete(self):
        '''Delete the selected widget
        '''
        if self.selected_widget:
            self.remove_widget_from_parent(self.selected_widget)
            self.selected_widget = None

    def on_touch_move(self, touch):
        '''Default handler for 'on_touch_move'
        '''
        if self.widgettree.dragging is True:
            return True

        super(Playground, self).on_touch_move(touch)
        return False

    def on_touch_up(self, touch):
        '''Default handler for 'on_touch_move'
        '''
        if super(ScatterPlane, self).collide_point(*touch.pos):
            self.dragging = False
            Clock.unschedule(self.start_widget_dragging)

        return super(Playground, self).on_touch_up(touch)

    def undo_dragging(self):
        '''To undo the last dragging operation if it has not been completed.
        '''
        if not self.drag_operation:
            return

        if self.drag_operation[0].parent:
            self.drag_operation[0].parent.remove_widget(self.drag_operation[0])

        self.drag_operation[1].add_widget(self.drag_operation[0],
                                          self.drag_operation[2])
        Clock.schedule_once(functools.partial(
                            App.get_running_app().focus_widget,
                            self.drag_operation[0]), 0.01)
        self.drag_operation = []

    def start_widget_dragging(self, *args):
        '''This function will create PlaygroundDragElement
           which will start dragging currently selected widget.
        '''
        if not self.dragging and not self.drag_operation and\
                self.selected_widget:
            #x, y = self.to_local(*touch.pos)
            #target = self.find_target(x, y, self.root)
            drag_widget = self.selected_widget
            self._widget_x, self._widget_y = drag_widget.x, drag_widget.y
            index = self.selected_widget.parent.children.index(drag_widget)
            self.drag_operation = (drag_widget, drag_widget.parent, index)

            self.selected_widget.parent.remove_widget(self.selected_widget)
            drag_elem = App.get_running_app().create_draggable_element(
                '', self.touch, self.selected_widget)

            drag_elem.drag_type = 'dragndrop'
            drag_elem.drag_parent = self.drag_operation[1]
            self.dragging = True
            self.from_drag = True
            App.get_running_app().focus_widget(None)

    def on_touch_down(self, touch):
        '''An override of ScatterPlane's on_touch_down.
           Used to determine the current selected widget and also emits,
           on_show_edit event.
        '''

        if super(ScatterPlane, self).collide_point(*touch.pos) and \
                not self.keyboard:
            win = EventLoop.window
            self.keyboard = win.request_keyboard(self._keyboard_released, self)
            self.keyboard.bind(on_key_down=self._on_keyboard_down)

        if self.selection_mode:
            if super(ScatterPlane, self).collide_point(*touch.pos):
                if not self.dragging:
                    self.touch = touch
                    Clock.schedule_once(self.start_widget_dragging, 1)

                x, y = self.to_local(*touch.pos)
                target = self.find_target(x, y, self.root)
                self.selected_widget = target
                App.get_running_app().focus_widget(target)
                self.clicked = True
                self.dispatch('on_show_edit', Playground)
                return True

        if self.parent.collide_point(*touch.pos):
            super(Playground, self).on_touch_down(touch)

        return False

########NEW FILE########
__FILENAME__ = project_loader
import re
import os
import sys
import inspect
import time
import functools
import shutil
import imp

from kivy.app import App
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.floatlayout import FloatLayout
from kivy.uix.button import Button
from kivy.base import runTouchApp
from kivy.factory import Factory, FactoryException
from kivy.properties import ObjectProperty
from kivy.lang import Builder
from kivy.uix.sandbox import Sandbox
from kivy.clock import Clock

from designer.helper_functions import get_indentation, get_indent_str,\
    get_line_start_pos, get_kivy_designer_dir
from designer.proj_watcher import ProjectWatcher

PROJ_DESIGNER = '.designer'
KV_PROJ_FILE_NAME = os.path.join(PROJ_DESIGNER, 'kvproj')
PROJ_FILE_CONFIG = os.path.join(PROJ_DESIGNER, 'file_config.ini')


class Comment(object):

    def __init__(self, string, path, _file):
        super(Comment, self).__init__()
        self.string = string
        self.path = path
        self.kv_file = _file


class WidgetRule(object):
    '''WidgetRule is an Abstract class for representing a rule of Widget.
    '''
    def __init__(self, widget, parent):
        super(WidgetRule, self).__init__()
        self.name = widget
        self.parent = parent
        self.file = None
        self.kv_file = None
        self.module = None


class ClassRule(WidgetRule):
    '''ClassRule is a class for representing a class rule in kv
    '''
    def __init__(self, class_name):
        super(ClassRule, self).__init__(class_name, None)


class CustomWidgetRule(ClassRule):
    '''CustomWidgetRule is a class for representing a custom widgets rule in kv
    '''
    def __init__(self, class_name, kv_file, py_file):
        super(ClassRule, self).__init__(class_name, None)
        self.class_name = class_name
        self.kv_file = kv_file
        self.py_file = py_file


class RootRule(ClassRule):
    '''RootRule is a class for representing root rule in kv.
    '''
    def __init__(self, class_name, widget):
        super(RootRule, self).__init__(class_name)
        self.widget = widget


class ProjectLoaderException(Exception):
    pass


class ProjectLoader(object):
    '''ProjectLoader class, used to load Project
    '''

    def __init__(self, proj_watcher):
        super(ProjectLoader, self).__init__()
        self._dir_list = []
        self.proj_watcher = proj_watcher
        self.class_rules = []
        self.root_rule = None
        self.new_project = None
        self.dict_file_type_and_path = {}
        self.kv_file_list = []
        self.kv_code_input = None
        self.tab_pannel = None
        self._root_rule = None
        self.file_list = []
        self.proj_dir = ""
        self._is_root_already_in_factory = False

    def _get_file_list(self, path):
        '''This function is recursively called for loading all py file files
           in the current directory.
        '''

        file_list = []
        if '.designer' in path:
            return []

        sys.path.insert(0, path)
        self._dir_list.append(path)
        for _file in os.listdir(path):
            file_path = os.path.join(path, _file)
            if os.path.isdir(file_path):
                file_list += self._get_file_list(file_path)
            else:
                #Consider only kv and py files
                if file_path[file_path.rfind('.'):] == '.py':
                    if os.path.dirname(file_path) == self.proj_dir:
                        file_list.insert(0, file_path)
                    else:
                        file_list.append(file_path)

        return file_list

    def add_custom_widget(self, py_path):
        '''This function is used to add a custom widget given path to its
           py file.
        '''

        f = open(py_path, 'r')
        py_string = f.read()
        f.close()

        #Find path to kv. py file will have Builder.load_file('path/to/kv')
        _r = re.findall(r'Builder\.load_file\s*\(\s*.+\s*\)', py_string)
        if _r == []:
            raise ProjectLoaderException('Cannot find widget\'s kv file.')

        py_string = py_string.replace(_r[0], '')
        kv_path = _r[0][_r[0].find('(') + 1: _r[0].find(')')]
        py_string = py_string.replace(kv_path, '')
        kv_path = kv_path.replace("'", '').replace('"', '')

        f = open(kv_path, 'r')
        kv_string = f.read()
        f.close()

        #Remove all the 'app' lines
        for app_str in re.findall(r'.+app+.+', kv_string):
            kv_string = kv_string.replace(
                app_str,
                app_str[:get_indentation(app_str)] + '#' + app_str.lstrip())

        Builder.load_string(kv_string)

        sys.path.insert(0, os.path.dirname(kv_path))

        _to_check = []

        #Get all the class_rules
        for class_str in re.findall(r'<+([\w_]+)>', kv_string):
            if re.search(r'\bclass\s+%s+.+:' % class_str, py_string):
                module = imp.new_module('CustomWidget')
                exec py_string in module.__dict__
                sys.modules['AppModule'] = module
                class_rule = CustomWidgetRule(class_str, kv_path, py_path)
                class_rule.file = py_path
                class_rule.module = module
                self.custom_widgets.append(class_rule)

    def get_root_str(self, kv_str=''):
        '''This function will get the root widgets rule from either kv_str
           or if it is empty string then from the kv file of root widget
        '''

        if kv_str == '':
            f = open(self.root_rule.kv_file, 'r')
            kv_str = f.read()
            f.close()

        #Find the start position of root_rule
        start_pos = kv_str.find(self.root_rule.name)
        if start_pos == -1:
            raise ProjectLoaderException(
                'Cannot find root rule in its file')

        #Get line for start_pos
        _line = 0
        _line_pos = 0
        _line_pos = kv_str.find('\n', _line_pos + 1)
        while _line_pos != -1 and _line_pos < start_pos:
            _line_pos = kv_str.find('\n', _line_pos + 1)
            _line += 1

        #Find the end position of root_rule, where indentation becomes 0
        #or file ends
        _line += 1
        lines = kv_str.splitlines()
        _total_lines = len(lines)
        while _line < _total_lines and (lines[_line].strip() == '' or
                                        get_indentation(lines[_line]) != 0):
            _line_pos = kv_str.find('\n', _line_pos + 1)
            _line += 1

        end_pos = _line_pos

        root_old_str = kv_str[start_pos: end_pos]

        for _rule in self.class_rules:
            if _rule.name == self.root_rule.name:
                root_old_str = "<" + root_old_str

        return root_old_str

    def get_full_str(self):
        '''This function will give the full string of all detected kv files.
        '''

        text = ''
        for _file in self.kv_file_list:
            f = open(_file, 'r')
            text += f.read() + '\n'
            f.close()

        return text

    def load_new_project(self, kv_path):
        '''To load a new project given by kv_path
        '''

        self.new_project = True
        self._load_project(kv_path)

    def load_project(self, kv_path):
        '''To load a project given by kv_path
        '''

        ret = self._load_project(kv_path)
        self.new_project = False
        #Add project_dir to watch
        self.proj_watcher.start_watching(self.proj_dir)
        return ret

    def _load_project(self, kv_path):
        '''Pivate function to load any project given by kv_path
        '''

        if os.path.isdir(kv_path):
            self.proj_dir = kv_path
        else:
            self.proj_dir = os.path.dirname(kv_path)

        parent_proj_dir = os.path.dirname(self.proj_dir)
        sys.path.insert(0, parent_proj_dir)

        self.class_rules = []
        all_files_loaded = True
        _file = None

        for _file in os.listdir(self.proj_dir):
            #Load each kv file in the directory
            _file = os.path.join(self.proj_dir, _file)
            if _file[_file.rfind('.'):] != '.kv':
                continue

            self.kv_file_list.append(_file)

            f = open(_file, 'r')
            kv_string = f.read()
            f.close()

            #Remove all the 'app' lines
            for app_str in re.findall(r'.+app+.+', kv_string):
                kv_string = kv_string.replace(
                    app_str,
                    app_str[:get_indentation(app_str)] +
                    '#' + app_str.lstrip())

            #Get all the class_rules
            for class_str in re.findall(r'<+([\w_]+)>', kv_string):
                class_rule = ClassRule(class_str)
                class_rule.kv_file = _file
                self.class_rules.append(class_rule)

            try:
                root_name = re.findall(r'^([\w\d_]+)\:', kv_string,
                                       re.MULTILINE)

                if root_name != []:
                    #It will occur when there is a root rule and it can't
                    #be loaded by Builder because the its file
                    #has been imported
                    root_name = root_name[0]
                    if not hasattr(Factory, root_name):
                        match = re.search(r'^([\w\d_]+)\:', kv_string,
                                          re.MULTILINE)
                        kv_string = kv_string[:match.start()] + \
                            '<'+root_name+'>:' + kv_string[match.end():]
                        self.root_rule = RootRule(root_name, None)
                        self.root_rule.kv_file = _file
                        self._root_rule = self.root_rule
                        self._is_root_already_in_factory = False

                    else:
                        self._is_root_already_in_factory = True
                else:
                    self._is_root_already_in_factory = False

                root_rule = Builder.load_string(re.sub(r'\s+on_\w+:\w+',
                                                       '', kv_string))
                if root_rule:
                    self.root_rule = RootRule(root_rule.__class__.__name__,
                                              root_rule)
                    self.root_rule.kv_file = _file
                    self._root_rule = self.root_rule

            except Exception as e:
                all_files_loaded = False

        if not all_files_loaded:
            raise ProjectLoaderException('Cannot load file "%s"' % (_file))

        if os.path.exists(os.path.join(self.proj_dir, KV_PROJ_FILE_NAME)):
            projdir_mtime = os.path.getmtime(self.proj_dir)

            f = open(os.path.join(self.proj_dir, KV_PROJ_FILE_NAME), 'r')
            proj_str = f.read()
            f.close()

            _file_is_valid = True
            #Checking if the file is valid
            if proj_str == '' or\
                    proj_str.count('<files>') != proj_str.count('</files>') or\
                    proj_str.count('<file>') != proj_str.count('</file>') or\
                    proj_str.count('<class>') != proj_str.count('</class>'):
                _file_is_valid = False

            if _file_is_valid:
                projdir_time = proj_str[
                    proj_str.find('<time>') + len('<time>'):
                    proj_str.find('</time>')]

                projdir_time = float(projdir_time.strip())

            if _file_is_valid and projdir_mtime <= projdir_time:
                #Project Directory folder hasn't been modified,
                #file list will remain same
                self.file_list = []
                un_modified_files = []
                start_pos = proj_str.find('<files>')
                end_pos = proj_str.find('</files>')
                if start_pos != -1 and end_pos != -1:
                    start_pos = proj_str.find('<file>', start_pos)
                    end_pos1 = proj_str.find('</file>', start_pos)
                    while start_pos < end_pos and start_pos != -1:
                        _file = proj_str[
                            start_pos + len('<file>'):end_pos1].strip()
                        self.file_list.append(_file)
                        if os.path.getmtime(_file) <= projdir_time:
                            un_modified_files.append(_file)

                        start_pos = proj_str.find('<file>', end_pos1)
                        end_pos1 = proj_str.find('</file>', start_pos)

                    for _file in self.file_list:
                        _dir = os.path.dirname(_file)
                        if _dir not in sys.path:
                            sys.path.insert(0, _dir)

                #Reload information for app
                start_pos = proj_str.find('<app>')
                end_pos = proj_str.find('</app>')
                if start_pos != -1 and end_pos != -1:
                    self._app_class = proj_str[
                        proj_str.find('<class>', start_pos) + len('<class>'):
                        proj_str.find('</class>', start_pos)].strip()
                    self._app_file = proj_str[
                        proj_str.find('<file>', start_pos) + len('<file>'):
                        proj_str.find('</file>', start_pos)].strip()
                    f = open(self._app_file, 'r')
                    self._app_module = self._import_module(f.read(),
                                                           self._app_file)
                    f.close()

                #Reload information for the files which haven't been modified
                start_pos = proj_str.find('<classes>')
                end_pos = proj_str.find('</classes>')

                if start_pos != -1 and end_pos != -1:
                    while start_pos < end_pos and start_pos != -1:
                        start_pos = proj_str.find('<class>', start_pos) +\
                            len('<class>')
                        end_pos1 = proj_str.find('</class>', start_pos)
                        _file = proj_str[
                            proj_str.find('<file>', start_pos) + len('<file>'):
                            proj_str.find('</file>', start_pos)].strip()

                        if _file in un_modified_files:
                            #If _file is un modified then assign it to
                            #class rule with _name
                            _name = proj_str[
                                proj_str.find('<name>', start_pos) +
                                len('<name>'):
                                proj_str.find('</name>', start_pos)].strip()

                            for _rule in self.class_rules:
                                if _name == _rule.name:
                                    _rule.file = _file
                                    f = open(_file, 'r')
                                    _rule.module = self._import_module(
                                        f.read(), _file, _fromlist=[_name])
                                    f.close()

                        start_pos = proj_str.find('<class>', start_pos)
                        end_pos1 = proj_str.find('</class>', start_pos)

        if self.file_list == []:
            self.file_list = self._get_file_list(self.proj_dir)

        #Get all files corresponding to each class
        self._get_class_files()

        #If root widget is not created but root class is known
        #then create widget
        if self.root_rule and not self.root_rule.widget and \
                self.root_rule.name:
            self.root_rule.widget = self.get_widget_of_class(
                self.root_rule.name)

        self.load_proj_config()

    def load_proj_config(self):
        '''To load project's config file. Project's config file is stored in
           .designer directory in project's directory.
        '''

        try:
            f = open(os.path.join(self.proj_dir, PROJ_FILE_CONFIG), 'r')
            s = f.read()
            f.close()

            start_pos = -1
            end_pos = -1

            start_pos = s.find('<file_type_and_dirs>\n')
            end_pos = s.find('</file_type_and_dirs>\n')

            if start_pos != -1 and end_pos != -1:
                for searchiter in re.finditer(r'<file_type=.+', s):
                    if searchiter.start() < start_pos:
                        continue

                    if searchiter.start() > end_pos:
                        break

                    found_str = searchiter.group(0)
                    file_type = found_str[found_str.find('"') + 1:
                                          found_str.find(
                                              '"', found_str.find('"') + 1)]
                    folder = found_str[
                        found_str.find('"', found_str.find('dir=') + 1) + 1:
                        found_str.rfind('"')]

                    self.dict_file_type_and_path[file_type] = folder

        except IOError:
            pass

    def save_proj_config(self):
        '''To save project's config file.
        '''

        string = '<file_type_and_dirs>\n'
        for file_type in self.dict_file_type_and_path.keys():
            string += '    <file_type="' + file_type + '"' + ' dir="' + \
                self.dict_file_type_and_path[file_type] + '">\n'
        string += '</file_type_and_dirs>\n'

        f = open(os.path.join(self.proj_dir, PROJ_CONFIG), 'w')
        f.write(string)
        f.close()

    def add_dir_for_file_type(self, file_type, folder):
        '''To add directory for specified file_type. More information in
           add_file.py
        '''

        self.dict_file_type_and_path[file_type] = folder
        self.save_proj_config()

    def perform_auto_save(self, *args):
        '''To perform auto save. Auto Save is done after every 5 min.
        '''

        if not self.root_rule:
            return

        auto_save_dir = os.path.join(self.proj_dir, '.designer')
        auto_save_dir = os.path.join(auto_save_dir, 'auto_save')

        if not os.path.exists(auto_save_dir):
            os.makedirs(auto_save_dir)

        else:
            shutil.rmtree(auto_save_dir)
            os.mkdir(auto_save_dir)

        for _file in os.listdir(self.proj_dir):
            if '.designer' in _file:
                continue

            old_file = os.path.join(self.proj_dir, _file)
            new_file = os.path.join(auto_save_dir, _file)
            if os.path.isdir(old_file):
                shutil.copytree(old_file, new_file)
            else:
                shutil.copy(old_file, new_file)

        root_rule_file = os.path.join(auto_save_dir,
                                      os.path.basename(self.root_rule.kv_file))
        f = open(root_rule_file, 'r')
        _file_str = f.read()
        f.close()

        text = self.kv_code_input.text

        root_str = self.get_root_str()
        f = open(root_rule_file, 'w')
        _file_str = _file_str.replace(root_str, text)
        f.write(_file_str)
        f.close()

        #For custom widgets copy py and kv file
        for widget in self.custom_widgets:
            custom_kv = os.path.join(auto_save_dir,
                                     os.path.basename(widget.kv_file))
            if not os.path.exists(custom_kv):
                shutil.copy(widget.kv_file, custom_kv)

            custom_py = os.path.join(auto_save_dir,
                                     os.path.basename(widget.py_file))
            if not os.path.exists(custom_py):
                shutil.copy(widget.py_file, custom_py)

    def save_project(self, proj_dir=''):
        '''To save project to proj_dir. If proj_dir is not empty string then
           project is saved to a new directory other than its
           current directory and otherwise it is saved to the
           current directory.
        '''

        #To stop ProjectWatcher from emitting event when project is saved
        self.proj_watcher.allow_event_dispatch = False
        proj_dir_changed = False

        if self.new_project:
            #Create dir and copy new_proj.kv and new_proj.py to new directory
            if not os.path.exists(proj_dir):
                os.mkdir(proj_dir)

            kivy_designer_dir = get_kivy_designer_dir()
            kivy_designer_new_proj_dir = os.path.join(kivy_designer_dir,
                                                      "new_proj")
            for _file in os.listdir(kivy_designer_new_proj_dir):
                old_file = os.path.join(kivy_designer_new_proj_dir, _file)
                new_file = os.path.join(proj_dir, _file)
                if os.path.isdir(old_file):
                    shutil.copytree(old_file, new_file)
                else:
                    shutil.copy(old_file, new_file)

            self.file_list = self._get_file_list(proj_dir)

            new_kv_file = os.path.join(proj_dir, "main.kv")
            new_py_file = os.path.join(proj_dir, "main.py")

            self.proj_dir = proj_dir
            if self.root_rule:
                self.root_rule.kv_file = new_kv_file
                self.root_rule.py_file = new_py_file

            if self.class_rules:
                self.class_rules[0].py_file = new_py_file
                self.class_rules[0].kv_file = new_kv_file

            self.new_project = False

        else:
            if proj_dir != '' and proj_dir != self.proj_dir:
                proj_dir_changed = True

                #Remove previous project directories from sys.path
                for _dir in self._dir_list:
                    try:
                        sys.path.remove(_dir)
                    except:
                        pass

                #if proj_dir and self.proj_dir differs then user wants to save
                #an already opened project to somewhere else
                #Copy all the files
                if not os.path.exists(proj_dir):
                    os.mkdir(proj_dir)

                for _file in os.listdir(self.proj_dir):
                    old_file = os.path.join(self.proj_dir, _file)
                    new_file = os.path.join(proj_dir, _file)
                    if os.path.isdir(old_file):
                        shutil.copytree(old_file, new_file)
                    else:
                        shutil.copy(old_file, new_file)

                self.file_list = self._get_file_list(proj_dir)

                #Change the path of all files in the class rules,
                #root rule and app
                relative_path = self._app_file[
                    self._app_file.find(self.proj_dir):]
                self._app_file = os.path.join(proj_dir, relative_path)

                f = open(self._app_file, 'r')
                s = f.read()
                f.close()

                self._import_module(s, self._app_file,
                                    _fromlist=[self._app_class])

                for _rule in self.class_rules:
                    relative_path = _rule.kv_file[
                        _rule.kv_file.find(self.proj_dir):]
                    _rule.kv_file = os.path.join(proj_dir, relative_path)

                    relative_path = _rule.file[_rule.file.find(self.proj_dir):]
                    _rule.file = os.path.join(proj_dir, relative_path)

                    f = open(_rule.file, 'r')
                    s = f.read()
                    f.close()

                    self._import_module(s, _rule.file, _fromlist=[_rule.name])

                relative_path = self.root_rule.kv_file[
                    self.root_rule.kv_file.find(self.proj_dir):]
                self.root_rule.kv_file = os.path.join(proj_dir, relative_path)

                relative_path = self.root_rule.file[
                    self.root_rule.file.find(self.proj_dir):]
                self.root_rule.file = os.path.join(proj_dir, relative_path)

                self.proj_dir = proj_dir

        #For custom widgets copy py and kv file to project directory
        for widget in self.custom_widgets:
            custom_kv = os.path.join(self.proj_dir,
                                     os.path.basename(widget.kv_file))
            if not os.path.exists(custom_kv):
                shutil.copy(widget.kv_file, custom_kv)

            custom_py = os.path.join(self.proj_dir,
                                     os.path.basename(widget.py_file))
            if not os.path.exists(custom_py):
                shutil.copy(widget.py_file, custom_py)

        #Saving all opened py files and also reimport them
        for _code_input in self.tab_pannel.list_py_code_inputs:
            path = os.path.join(self.proj_dir, _code_input.rel_file_path)
            f = open(path, 'w')
            f.write(_code_input.text)
            f.close()
            _from_list = []
            for rule in self.class_rules:
                if rule.file == path:
                    _from_list.append(rule.file)

            if not self.is_root_a_class_rule():
                if self.root_rule.file == path:
                    _from_list.append(self.root_rule.name)

            self._import_module(_code_input.text, path, _fromlist=_from_list)

        #Save all class rules
        text = self.kv_code_input.text
        for _rule in self.class_rules:
            #Get the kv text from KVLangArea and write it to class rule's file
            f = open(_rule.kv_file, 'r')
            _file_str = f.read()
            f.close()

            old_str = self.get_class_str_from_text(_rule.name, _file_str)
            new_str = self.get_class_str_from_text(_rule.name, text)

            f = open(_rule.kv_file, 'w')
            _file_str = _file_str.replace(old_str, new_str)
            f.write(_file_str)
            f.close()

        #If root widget is not changed
        if self._root_rule.name == self.root_rule.name:
            #Save root widget's rule
            is_root_class = False
            for _rule in self.class_rules:
                if _rule.name == self.root_rule.name:
                    is_root_class = True
                    break

            if not is_root_class:
                f = open(self.root_rule.kv_file, 'r')
                _file_str = f.read()
                f.close()

                old_str = self.get_class_str_from_text(self.root_rule.name,
                                                       _file_str,
                                                       is_class=False)
                new_str = self.get_class_str_from_text(self.root_rule.name,
                                                       text, is_class=False)

                f = open(self.root_rule.kv_file, 'w')
                _file_str = _file_str.replace(old_str, new_str)
                f.write(_file_str)
                f.close()

        else:
            #If root widget is changed
            #Root Widget changes, there can be these cases:
            root_name = self.root_rule.name
            f = open(self._app_file, 'r')
            file_str = f.read()
            f.close()
            self._root_rule = self.root_rule

            if self.is_root_a_class_rule() and self._app_file:
                #Root Widget's class rule is a custom class
                #and its rule is class rule. So, it already have been saved
                #the string of App's build() function will be changed to
                #return new root widget's class

                if self._app_class != 'runTouchApp':
                    s = re.search(r'class\s+%s.+:' % self._app_class, file_str)
                    if s:
                        build_searchiter = None
                        for searchiter in re.finditer(
                                r'[ \ \t]+def\s+build\s*\(\s*self.+\s*:',
                                file_str):
                            if searchiter.start() > s.start():
                                build_searchiter = searchiter
                                break

                        if build_searchiter:
                            indent = get_indentation(build_searchiter.group(0))
                            file_str = file_str[:build_searchiter.end()] +\
                                '\n' + get_indent_str(2*indent) + "return " +\
                                root_name + "()\n" + \
                                file_str[build_searchiter.end():]

                        else:
                            file_str = file_str[:s.end()] + \
                                "\n    def build(self):\n        return " + \
                                root_name + '()\n' + file_str[s.end():]

                else:
                    file_str = re.sub(r'runTouchApp\s*\(.+\)',
                                      'runTouchApp('+root_name+'())', file_str)

                f = open(self._app_file, 'w')
                f.write(file_str)
                f.close()

            else:
                #Root Widget's rule is not a custom class
                #and its rule is root rule
                #Its kv_file should be of App's class name
                #and App's build() function should be cleared
                if not self.root_rule.kv_file:
                    s = self._app_class.replace('App', '').lower()
                    root_file = None
                    for _file in self.kv_file_list:
                        if os.path.basename(_file).find(s) == 0:
                            self.root_rule.kv_file = _file
                            break

                f = open(self.root_rule.kv_file, 'r')
                _file_str = f.read()
                f.close()

                new_str = self.get_class_str_from_text(self.root_rule.name,
                                                       text, False)

                f = open(self.root_rule.kv_file, 'a')
                f.write(new_str)
                f.close()

                if self._app_class != 'runTouchApp':
                    s = re.search(r'class\s+%s.+:' % self._app_class, file_str)
                    if s:
                        build_searchiter = None
                        for searchiter in re.finditer(
                                r'[ \ \t]+def\s+build\s*\(\s*self.+\s*:',
                                file_str):
                            if searchiter.start() > s.start():
                                build_searchiter = searchiter
                                break

                        if build_searchiter:
                            lines = file_str.splitlines()
                            total_lines = len(lines)
                            indent = get_indentation(build_searchiter.group(0))

                            _line = 0
                            _line_pos = -1
                            _line_pos = file_str.find('\n', _line_pos + 1)
                            while _line_pos <= build_searchiter.start():
                                _line_pos = file_str.find('\n', _line_pos + 1)
                                _line += 1

                            _line += 1

                            while _line < total_lines:
                                if lines[_line].strip() != '' and\
                                        get_indentation(lines[_line]) <= \
                                        indent:
                                    break

                                _line += 1

                            _line -= 1
                            end = get_line_start_pos(file_str, _line)
                            start = build_searchiter.start()
                            file_str = file_str.replace(file_str[start:end],
                                                        '    pass')

                            f = open(self._app_file, 'w')
                            f.write(file_str)
                            f.close()

        #Allow Project Watcher to emit events
        Clock.schedule_once(self._allow_proj_watcher_dispatch, 1)

    def get_class_str_from_text(self, class_name, _file_str, is_class=True):
        '''To return the full class rule of class_name from _file_str
        '''
        _file_str += '\n'
        start_pos = -1
        #Find the start position of class_name
        if is_class:
            start_pos = _file_str.find('<'+class_name+'>:')
        else:
            while True:
                start_pos = _file_str.find(class_name, start_pos+1)
                if start_pos == 0 or not (_file_str[start_pos-1].isalnum() and
                                          _file_str[start_pos-1] != ''):
                    break

        _line = 0
        _line_pos = 0
        _line_pos = _file_str.find('\n', _line_pos + 1)
        while _line_pos != -1 and _line_pos < start_pos:
            _line_pos = _file_str.find('\n', _line_pos + 1)
            _line += 1

        #Find the end position of class_name, where indentation becomes 0
        #or file ends
        _line += 1
        lines = _file_str.splitlines()
        _total_lines = len(lines)

        hash_pos = 0
        while hash_pos == 0 and _line < _total_lines:
            hash_pos = lines[_line].find('#')
            if hash_pos == 0:
                _line_pos += 1 + len(lines[_line])
                _line += 1

        while _line < _total_lines and (lines[_line].strip() == '' or
                                        get_indentation(lines[_line]) != 0):
            _line_pos = _file_str.find('\n', _line_pos + 1)
            _line += 1
            hash_pos = 0
            while hash_pos == 0 and _line < _total_lines:
                hash_pos = lines[_line].find('#')
                if hash_pos == 0:
                    _line += 1

        end_pos = _line_pos

        old_str = _file_str[start_pos: end_pos]
        return old_str

    def _allow_proj_watcher_dispatch(self, *args):
        '''To start project_watcher to start watching self.proj_dir
        '''

        self.proj_watcher.allow_event_dispatch = True
        #self.proj_watcher.start_watching(self.proj_dir)

    def _app_in_string(self, s):
        '''To determine if there is an App class or runTouchApp
           defined/used in string s.
        '''

        if 'runTouchApp' in s:
            self._app_class = 'runTouchApp'
            return True

        elif 'kivy.app' in s:
            for _class in re.findall(r'\bclass\b.+:', s):
                b_index1 = _class.find('(')
                b_index2 = _class.find(')')
                if _class[b_index1+1:b_index2].strip() == 'App':
                    self._app_class = _class[_class.find(' '):b_index1].strip()
                    return True

        return False

    def _get_class_files(self):
        '''To search through all detected class rules and find
           their python files and to search for app.
        '''
        if self._app_file is None:
            #Search for main.py
            for _file in self.file_list:
                if _file[_file.rfind('/')+1:] == 'main.py':
                    f = open(_file, 'r')
                    s = f.read()
                    f.close()
                    if self._app_in_string(s):
                        self._app_module = self._import_module(s, _file)
                        self._app_file = _file

            #Search for a file with app in its name
            if not self._app_class:
                for _file in self.file_list:
                    if 'app' in _file[_file.rfind('/'):]:
                        f = open(_file, 'r')
                        s = f.read()
                        f.close()
                        if self._app_in_string(s):
                            self._app_module = self._import_module(s, _file)
                            self._app_file = _file

        to_find = []
        for _rule in self.class_rules:
            if _rule.file is None:
                to_find.append(_rule)

        if self.root_rule:
            to_find.append(self.root_rule)

        #If cannot find due to above methods, search every file
        for _file in self.file_list:
            f = open(_file, 'r')
            s = f.read()
            f.close()
            if not self._app_file and self._app_in_string(s):
                self._app_module = self._import_module(s, _file)
                self._app_file = _file

            for _rule in to_find[:]:
                if _rule.file:
                    continue

                if re.search(r'\bclass\s*%s+.+:' % (_rule.name), s):
                    mod = self._import_module(s, _file, _fromlist=[_rule.name])
                    if hasattr(mod, _rule.name):
                        _rule.file = _file
                        to_find.remove(_rule)
                        _rule.module = mod

        #Cannot Find App, So, use default runTouchApp
        if not self._app_file:
            self._app_class = 'runTouchApp'

        #Root Widget may be in Factory not in file
        if self.root_rule:
            if not self.root_rule.file and\
                    hasattr(Factory, self.root_rule.name):
                to_find.remove(self.root_rule)

        #to_find should be empty, if not some class's files are not detected
        if to_find != []:
            raise ProjectLoaderException(
                'Cannot find class files for all classes')

    def _import_module(self, s, _file, _fromlist=[]):
        module = None
        import_from_s = False
        _r = re.findall(r'Builder\.load_file\s*\(\s*.+\s*\)', s)
        if _r:
            s = s.replace(_r[0], '')
            import_from_s = True

        run_pos = s.rfind('().run()')

        if run_pos != -1:
            run_pos -= 1
            while not s[run_pos].isspace():
                run_pos -= 1

            i = run_pos - 1
            while s[i] == ' ':
                i -= 1

        if i == run_pos - 1 or _r != []:
            if i == run_pos - 1:
                s = s.replace('%s().run()' % self._app_class, '')

            if 'AppModule' in sys.modules:
                del sys.modules['AppModule']

            module = imp.new_module('AppModule')
            exec s in module.__dict__
            sys.modules['AppModule'] = module
            return module

        module_name = _file[_file.rfind(os.sep)+1:].replace('.py', '')
        if module_name in sys.modules:
            del sys.modules[module_name]

        module = __import__(module_name, fromlist=_fromlist)
        return module

    def cleanup(self, stop_watcher=True):
        '''To cleanup everything loaded by previous project.
        '''

        if stop_watcher:
            self.proj_watcher.stop()

        #Remove all class rules and root rules of previous project
        rules = []

        try:
            rules = Builder.match(self.root_rule.widget)
            for _rule in rules:
                for _tuple in Builder.rules[:]:
                    if _tuple[1] == _rule:
                        Builder.rules.remove(_tuple)
        except:
            pass

        for _tuple in Builder.rules[:]:
            for _rule in self.class_rules:
                if "<" + _rule.name + ">" == _tuple[1].name:
                    Builder.rules.remove(_tuple)

        if self.root_rule and not self._is_root_already_in_factory and\
                hasattr(Factory, self.root_rule.name):
            Factory.unregister(self.root_rule.name)

        self._app_file = None
        self._app_class = None
        self._app_module = None
        self._app = None
        #Remove previous project directories
        for _dir in self._dir_list:
            try:
                sys.path.remove(_dir)
            except:
                pass

        self.kv_file_list = []
        self.file_list = []
        self._dir_list = []
        self.class_rules = []
        self.list_comments = []
        self.custom_widgets = []
        self.dict_file_type_and_path = {}
        self.root_rule = None
        self._root_rule = None

    def get_app(self, reload_app=False):
        '''To get the applications app class instance
        '''

        if not self._app_file or not self._app_class or not self._app_module:
            return None

        if not reload_app and self._app:
            return self._app

        for name, obj in inspect.getmembers(self._app_module):
            if inspect.isclass(obj) and self._app_class == name:
                self._app = obj()
                return self._app

        #if still couldn't get app, although that shouldn't happen
        return None

    def reload_from_str(self, root_str):
        '''To reload from root_str
        '''

        rules = []
        #Cleaning root rules
        try:
            rules = Builder.match(self.root_rule.widget)
            for _rule in rules:
                for _tuple in Builder.rules[:]:
                    if _tuple[1] == _rule:
                        Builder.rules.remove(_tuple)
        except:
            pass

        #Cleaning class rules
        for _rule in self.class_rules:
            for rule in Builder.rules[:]:
                if rule[1].name == '<'+_rule.name+'>':
                    Builder.rules.remove(rule)
                    break

        root_widget = None
        #Remove all the 'app' lines
        root_str = re.sub(r'.+app+.+', '', root_str)

        root_widget = Builder.load_string(root_str)

        if not root_widget:
            root_widget = self.get_widget_of_class(self.root_rule.name)
            self.root_rule.widget = root_widget

        if not root_widget:
            root_name = root_str[:root_str.find('\n')]
            root_name = root_widget.replace(':', '').replace('<', '')
            root_name = root_widget.replace('>', '')
            root_widget = self.set_root_widget(root_name)

        return root_widget

    def is_root_a_class_rule(self):
        '''Returns True if root rule is a class rule
        '''

        for _rule in self.class_rules:
            if _rule.name == self.root_rule.name:
                return True

        return False

    def set_root_widget(self, root_name, widget=None):
        '''To set root_name as the root rule.
        '''

        root_widget = None
        if not widget:
            root_widget = self.get_widget_of_class(root_name)
        else:
            root_widget = widget

        self.root_rule = RootRule(root_name, root_widget)
        for _rule in self.class_rules:
            if _rule.name == root_name:
                self.root_rule.kv_file = _rule.kv_file
                self.root_rule.py_file = _rule.file
                break

        if not self._root_rule:
            self._root_rule = self.root_rule

        return root_widget

    def get_root_widget(self, new_root=False):
        '''To get the root widget of the current project.
        '''

        if not new_root and self.root_rule and self.root_rule.name != '':
            return self.root_rule.widget

        if self._app_file is None:
            return None

        f = open(self._app_file, 'r')
        s = f.read()
        f.close()

        current_app = App.get_running_app()
        app = self.get_app(reload_app=True)
        root_widget = None
        if app is not None:
            root_widget = app.build()
            if not root_widget:
                root_widget = app.root

        App._running_app = current_app

        if root_widget:
            self.root_rule = RootRule(root_widget.__class__.__name__,
                                      root_widget)
            for _rule in self.class_rules:
                if _rule.name == self.root_rule.name:
                    self.root_rule.kv_file = _rule.kv_file
                    self.root_rule.file = _rule.file
                    break

            if not self._root_rule:
                self._root_rule = self.root_rule

        if not self.root_rule.kv_file:
            raise ProjectLoaderException("Cannot find root widget's kv file")

        return root_widget

    def get_widget_of_class(self, class_name):
        '''To get instance of the class_name
        '''

        self.root = getattr(Factory, class_name)()
        return self.root

    def is_widget_custom(self, widget):
        for rule in self.class_rules:
            if rule.name == type(widget).__name__:
                return True

        return False

    def record(self):
        '''To record all the findings in ./designer/kvproj. These will
           be loaded again if project hasn't been modified
           outside Kivy Designer
        '''

        if not os.path.exists(os.path.join(
                self.proj_dir, os.path.dirname(KV_PROJ_FILE_NAME))):
            os.mkdir(os.path.join(self.proj_dir, ".designer"))

        f = open(os.path.join(self.proj_dir, KV_PROJ_FILE_NAME), 'w')
        f.close()

        f = open(os.path.join(self.proj_dir, KV_PROJ_FILE_NAME), 'w')
        proj_file_str = '<time>\n' + '    ' + str(time.time()) + '\n</time>\n'
        proj_file_str += '<files>\n'
        for _file in self.file_list:
            proj_file_str += '    <file>\n'
            proj_file_str += '        '+_file
            proj_file_str += '\n    </file>\n'

        proj_file_str += '</files>\n'

        proj_file_str += '<classes>\n'
        for _rule in self.class_rules:
            proj_file_str += '    <class>\n'
            proj_file_str += '         <name>\n'
            proj_file_str += '             '+_rule.name
            proj_file_str += '\n         </name>\n'
            proj_file_str += '         <file>\n'
            proj_file_str += '             '+_rule.file
            proj_file_str += '\n         </file>\n'
            proj_file_str += '\n    </class>\n'

        proj_file_str += '</classes>\n'

        if self._app_class and self._app_file:
            proj_file_str += '<app>\n'
            proj_file_str += '    <class>\n'
            proj_file_str += '         '+self._app_class
            proj_file_str += '\n    </class>\n'
            proj_file_str += '    <file>\n'
            proj_file_str += '         '+self._app_file
            proj_file_str += '\n    </file>\n'
            proj_file_str += '</app>\n'

        f.write(proj_file_str)

        f.close()

########NEW FILE########
__FILENAME__ = project_settings
import os

from kivy.properties import ObjectProperty
from kivy.config import ConfigParser
from kivy.uix.settings import Settings, SettingTitle
from kivy.uix.label import Label
from kivy.uix.button import Button

PROJ_DESIGNER = '.designer'
PROJ_CONFIG = os.path.join(PROJ_DESIGNER, 'config.ini')


class ProjectSettings(Settings):
    '''Subclass of :class:`kivy.uix.settings.Settings` responsible for
       showing settings of project.
    '''

    proj_loader = ObjectProperty(None)
    '''Reference to :class:`desginer.project_loader.ProjectLoader`
    '''

    config_parser = ObjectProperty(None)
    '''Config Parser for this class. Instance
       of :class:`kivy.config.ConfigParser`
    '''

    def load_proj_settings(self):
        '''This function loads project settings
        '''
        self.config_parser = ConfigParser()
        file_path = os.path.join(self.proj_loader.proj_dir, PROJ_CONFIG)
        if not os.path.exists(file_path):
            if not os.path.exists(os.path.dirname(file_path)):
                os.makedirs(os.path.dirname(file_path))

            CONFIG_TEMPLATE = '''[proj_name]
name = Project

[arguments]
arg =

[env variables]
env =
'''
            f = open(file_path, 'w')
            f.write(CONFIG_TEMPLATE)
            f.close()

        self.config_parser.read(file_path)
        proj_prop_panel = self.create_json_panel(
            'Project Properties', self.config_parser,
            './designer/settings/proj_settings_proj_prop.json')
        self.add_widget(proj_prop_panel)
        self.add_json_panel(
            'Shell Environment', self.config_parser,
            './designer/settings/proj_settings_shell_env.json')

    def on_config_change(self, *args):
        '''This function is default handler of on_config_change event.
        '''
        self.config_parser.write()
        super(ProjectSettings, self).on_config_change(*args)

########NEW FILE########
__FILENAME__ = proj_watcher
import sys
import os
import time

from watchdog.events import FileSystemEventHandler
from watchdog.observers import Observer
import traceback


class ProjectEventHandler(FileSystemEventHandler):
    '''ProjectEventHandler is the event handler for any event occurring on
       its current directory. See FileSystemEventHandler in python-watchdog
       documentation for more information.
    '''
    def __init__(self, observer, proj_watcher):
        self._observer = observer
        self._proj_watcher = proj_watcher
        super(ProjectEventHandler, self).__init__()

    def on_any_event(self, event):
        '''An event handler for any event.
        '''
        self._proj_watcher.dispatch_proj_event(event)


class ProjectWatcher(object):
    '''ProjectWatcher is responsible for watching any changes in
       project directory. It will call self._callback whenever there
       are any changes. It can currently handle only one directory at
       a time.
    '''
    def __init__(self, callback):
        super(ProjectWatcher, self).__init__()
        self.proj_event = None
        self._observer = None
        self._event_handler = None
        self._callback = callback
        self.allow_event_dispatch = True

    def start_watching(self, project_dir):
        '''To start watching project_dir.
        '''
        self._project_dir = project_dir
        self._observer = Observer()
        self._event_handler = ProjectEventHandler(self._observer, self)
        self._watch = self._observer.schedule(self._event_handler,
                                              self._project_dir,
                                              recursive=True)
        self._observer.start()

    def on_project_modified(self, *args):
        pass

    def dispatch_proj_event(self, event):
        '''To dispatch event to self._callback.
        '''
        self.proj_event = event
        #Do not dispatch event if '.designer' is modified
        if '.designer' not in event.src_path and self.allow_event_dispatch:
            self._callback(event)

    def stop(self):
        '''To stop watching currently watched directory. This will also call
           join() on the thread created by Observer.
        '''

        if self._observer:
            self._observer.unschedule_all()
            self._observer.stop()
            self.join()

        self._observer = None

    def join(self):
        '''join observer after unschedulling it
        '''
        self._observer.join()

########NEW FILE########
__FILENAME__ = propertyviewer
from kivy.uix.scrollview import ScrollView
from kivy.properties import ObjectProperty, NumericProperty, StringProperty,\
    BoundedNumericProperty, BooleanProperty, OptionProperty
from kivy.uix.label import Label
from kivy.uix.textinput import TextInput
from kivy.uix.checkbox import CheckBox
from kivy.uix.spinner import Spinner
from kivy.app import App

from designer.undo_manager import PropOperation


class PropertyLabel(Label):
    '''This class represents the :class:`~kivy.label.Label` for showing
       Property Names in :class:`~designer.propertyviewer.PropertyViewer`.
    '''
    pass


class PropertyBase(object):
    '''This class represents Abstract Class for Property showing classes i.e.
       PropertyTextInput and PropertyBoolean
    '''

    propwidget = ObjectProperty()
    '''It is an instance to the Widget whose property value is displayed.
       :data:`propwidget` is a :class:`~kivy.properties.ObjectProperty`
    '''

    propname = StringProperty()
    '''It is the name of the property.
       :data:`propname` is a :class:`~kivy.properties.StringProperty`
    '''

    propvalue = ObjectProperty(allownone=True)
    '''It is the value of the property.
       :data:`propvalue` is a :class:`~kivy.properties.ObjectProperty`
    '''

    oldvalue = ObjectProperty(allownone=True)
    '''It is the old value of the property
       :data:`oldvalue` is a :class:`~kivy.properties.ObjectProperty`
    '''

    have_error = BooleanProperty(False)
    '''It specifies whether there have been an error in setting new value
       to property
       :data:`have_error` is a :class:`~kivy.properties.BooleanProperty`
    '''

    proptype = StringProperty()
    '''It is the type of property.
       :data:`proptype` is a :class:`~kivy.properties.StringProperty`
    '''

    record_to_undo = BooleanProperty(False)
    '''It specifies whether the property change has to be recorded to undo.
       It is used when :class:`~designer.undo_manager.UndoManager` undoes
       or redoes the property change.
       :data:`record_to_undo` is a :class:`~kivy.properties.BooleanProperty`
    '''

    kv_code_input = ObjectProperty()
    '''It is a reference to the
       :class:`~designer.uix.kv_code_input.KVLangArea`.
       :data:`kv_code_input` is a :class:`~kivy.properties.ObjectProperty`
    '''

    def set_value(self, value):
        '''This function first converts the value of the propwidget, then sets
           the new value. If there is some error in setting new value, then it
           sets the property value back to oldvalue
        '''

        self.have_error = False
        conversion_err = False
        oldvalue = getattr(self.propwidget, self.propname)
        try:
            if isinstance(self.propwidget.property(self.propname),
                          NumericProperty):

                if value == 'None' or value == '':
                    value = None
                else:
                    value = float(value)

        except Exception:
            conversion_err = True

        root = App.get_running_app().root
        if not conversion_err:
            try:
                setattr(self.propwidget, self.propname, value)
                self.kv_code_input.set_property_value(self.propwidget,
                                                      self.propname, value,
                                                      self.proptype)
                if self.record_to_undo:
                    root.undo_manager.push_operation(
                        PropOperation(self, oldvalue, value))
                self.record_to_undo = True
            except Exception:
                self.have_error = True
                setattr(self.propwidget, self.propname, oldvalue)


class PropertyOptions(PropertyBase, Spinner):
    '''PropertyOptions to show/set/get options for an OptionProperty
    '''

    def __init__(self, prop, **kwargs):
        PropertyBase.__init__(self, **kwargs)
        Spinner.__init__(self, values=prop.options, **kwargs)

    def on_propvalue(self, *args):
        '''Default handler for 'on_propvalue'.
        '''
        self.text = self.propvalue


class PropertyTextInput(PropertyBase, TextInput):
    '''PropertyTextInput is used as widget to display
       :class:`~kivy.properties.StringProperty` and
       :class:`~kivy.properties.NumericProperty`.
    '''

    def insert_text(self, substring, from_undo=False):
        '''Override of :class:`~kivy.uix.textinput.TextInput`.insert_text,
           it first checks whether the value being entered is valid or not.
           If yes, then it enters that value otherwise it doesn't.
           For Example, if Property is NumericProperty then it will
           first checks if value being entered should be a number
           or decimal only.
        '''
        if self.proptype == 'NumericProperty' and \
           substring.isdigit() is False and\
           (substring != '.' or '.' in self.text)\
           and substring not in 'None':
                return

        super(PropertyTextInput, self).insert_text(substring)


class PropertyBoolean(PropertyBase, CheckBox):
    '''PropertyBoolean is used as widget to display
       :class:`~kivy.properties.BooleanProperty`.
    '''
    pass


class PropertyViewer(ScrollView):
    '''PropertyViewer is used to display property names and their corresponding
       value.
    '''

    widget = ObjectProperty(allownone=True)
    '''Widget for which properties are displayed.
       :data:`widget` is a :class:`~kivy.properties.ObjectProperty`
    '''

    prop_list = ObjectProperty()
    '''Widget in which all the properties and their value is added. It is a
       :class:`~kivy.gridlayout.GridLayout.
       :data:`prop_list` is a :class:`~kivy.properties.ObjectProperty`
    '''

    kv_code_input = ObjectProperty()
    '''It is a reference to the KVLangArea.
       :data:`kv_code_input` is a :class:`~kivy.properties.ObjectProperty`
    '''

    def on_widget(self, instance, value):
        '''Default handler for 'on_widget'.
        '''
        self.clear()
        if value is not None:
            self.discover(value)

    def clear(self):
        '''To clear :data:`prop_list`.
        '''
        self.prop_list.clear_widgets()

    def discover(self, value):
        '''To discover all properties and add their
           :class:`~designer.propertyviewer.PropertyLabel` and
           :class:`~designer.propertyviewer.PropertyBoolean`/
           :class:`~designer.propertyviewer.PropertyTextInput`
           to :data:`prop_list`.
        '''

        add = self.prop_list.add_widget
        props = value.properties().keys()
        props.sort()
        for prop in props:
            ip = self.build_for(prop)
            if not ip:
                continue
            add(PropertyLabel(text=prop))
            add(ip)

    def build_for(self, name):
        '''To create :class:`~designer.propertyviewer.PropertyBoolean`
           :class:`~designer.propertyviewer.PropertyTextInput`
           for Property 'name'
        '''

        prop = self.widget.property(name)
        if isinstance(prop, NumericProperty):
            return PropertyTextInput(propwidget=self.widget, propname=name,
                                     proptype='NumericProperty',
                                     kv_code_input=self.kv_code_input)

        elif isinstance(prop, StringProperty):
            return PropertyTextInput(propwidget=self.widget, propname=name,
                                     proptype='StringProperty',
                                     kv_code_input=self.kv_code_input)

        elif isinstance(prop, BooleanProperty):
            ip = PropertyBoolean(propwidget=self.widget, propname=name,
                                 proptype='BooleanProperty',
                                 kv_code_input=self.kv_code_input)
            ip.record_to_undo = True
            return ip

        elif isinstance(prop, OptionProperty):
            ip = PropertyOptions(prop, propwidget=self.widget, propname=name,
                                 proptype='StringProperty',
                                 kv_code_input=self.kv_code_input)
            return ip

        return None

########NEW FILE########
__FILENAME__ = recent_manager
import os
from functools import partial

from kivy.uix.boxlayout import BoxLayout
from kivy.uix.button import Button
from kivy.uix.popup import Popup
from kivy.uix.listview import ListView, ListItemButton
from kivy.properties import ObjectProperty, NumericProperty
from kivy.adapters.listadapter import ListAdapter

from designer.helper_functions import get_kivy_designer_dir

RECENT_FILES_NAME = 'recent_files'


class RecentManager(object):
    '''RecentManager is responsible for retrieving/storing the list of recently
       opened/saved projects.
    '''

    def __init__(self):
        super(RecentManager, self).__init__()
        self.list_files = []
        self.max_recent_files = 5
        self.load_files()

    def add_file(self, _file):
        '''To add file to RecentManager.
        '''

        _file_index = 0
        try:
            _file_index = self.list_files.index(_file)
        except:
            _file_index = -1

        if _file_index != -1:
            #If _file is already present in list_files, then move it to 0 index
            self.list_files.remove(_file)

        self.list_files.insert(0, _file)

        #Recent files should not be greater than max_recent_files
        while len(self.list_files) > self.max_recent_files:
            self.list_files.pop()

        self.store_files()

    def store_files(self):
        '''To store the list of files on disk.
        '''

        _string = ''
        for _file in self.list_files:
            _string += _file + '\n'

        recent_file_path = os.path.join(get_kivy_designer_dir(),
                                        RECENT_FILES_NAME)
        f = open(recent_file_path, 'w')
        f.write(_string)
        f.close()

    def load_files(self):
        '''To load the list of files from disk
        '''

        recent_file_path = os.path.join(get_kivy_designer_dir(),
                                        RECENT_FILES_NAME)

        if not os.path.exists(recent_file_path):
            return

        f = open(recent_file_path, 'r')
        _file = f.readline()

        while _file != '':
            file_path = _file.strip()
            if os.path.exists(file_path):
                self.list_files.append(file_path)

            _file = f.readline()

        f.close()


class RecentDialog(BoxLayout):
    '''RecentDialog shows the list of recent files retrieved from RecentManager
       It emits, 'on_select' event when a file is selected and select_button is
       clicked and 'on_cancel' when cancel_button is pressed.
    '''

    listview = ObjectProperty(None)
    ''':class:`~kivy.uix.listview.ListView` used for showing file paths.
       :data:`listview` is a :class:`~kivy.properties.ObjectProperty`
    '''

    select_button = ObjectProperty(None)
    ''':class:`~kivy.uix.button.Button` used to select the list item.
       :data:`select_button` is a :class:`~kivy.properties.ObjectProperty`
    '''

    cancel_button = ObjectProperty(None)
    ''':class:`~kivy.uix.button.Button` to cancel the dialog.
       :data:`cancel_button` is a :class:`~kivy.properties.ObjectProperty`
    '''

    adapter = ObjectProperty(None)
    ''':class:`~kivy.uix.listview.ListAdapter` used for selecting files.
       :data:`adapter` is a :class:`~kivy.properties.ObjectProperty`
    '''

    __events__ = ('on_select', 'on_cancel')

    def __init__(self, file_list, **kwargs):
        super(RecentDialog, self).__init__(**kwargs)
        item_strings = file_list
        adapter = ListAdapter(cls=ListItemButton, data=item_strings,
                              selection_mode='single',
                              allow_empty_selection=False)

        self.listview = ListView(adapter=adapter)
        self.add_widget(self.listview, 1)

    def on_select_button(self, *args):
        '''Event handler for 'on_release' event of select_button.
        '''
        self.select_button.bind(on_press=partial(self.dispatch, 'on_select'))

    def on_cancel_button(self, *args):
        '''Event handler for 'on_release' event of cancel_button.
        '''
        self.cancel_button.bind(on_press=partial(self.dispatch, 'on_cancel'))

    def on_select(self, *args):
        '''Default event handler for 'on_select' event.
        '''
        pass

    def on_cancel(self, *args):
        '''Default event handler for 'on_cancel' event.
        '''
        pass

########NEW FILE########
__FILENAME__ = select_class
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.button import Button
from kivy.uix.popup import Popup
from kivy.uix.listview import ListView, ListItemButton
from kivy.properties import ObjectProperty
from kivy.adapters.listadapter import ListAdapter

from functools import partial


class SelectClass(BoxLayout):
    '''SelectClass dialog is shows a list of classes. User would have to
       select a class from these classes. It will emit 'on_select' when
       select_button is pressed and 'on_cancel' when cancel_button is pressed.
    '''

    listview = ObjectProperty(None)
    ''':class:`~kivy.uix.listview.ListView` used for showing file paths.
       :data:`listview` is a :class:`~kivy.properties.ObjectProperty`
    '''

    select_button = ObjectProperty(None)
    ''':class:`~kivy.uix.button.Button` used to select the list item.
       :data:`select_button` is a :class:`~kivy.properties.ObjectProperty`
    '''

    cancel_button = ObjectProperty(None)
    ''':class:`~kivy.uix.button.Button` to cancel the dialog.
       :data:`cancel_button` is a :class:`~kivy.properties.ObjectProperty`
    '''

    adapter = ObjectProperty(None)
    ''':class:`~kivy.uix.listview.ListAdapter` used for selecting files.
       :data:`adapter` is a :class:`~kivy.properties.ObjectProperty`
    '''

    __events__ = ('on_select', 'on_cancel')

    def __init__(self, class_rule_list, **kwargs):
        super(SelectClass, self).__init__(**kwargs)
        item_strings = [_rule.name for _rule in class_rule_list]
        adapter = ListAdapter(cls=ListItemButton, data=item_strings,
                              selection_mode='single',
                              allow_empty_selection=False)
        self.listview = ListView(adapter=adapter)
        self.add_widget(self.listview, 1)

    def on_select_button(self, *args):
        '''Event handler for 'on_release' event of select_button.
        '''
        self.select_button.bind(on_press=partial(self.dispatch, 'on_select'))

    def on_cancel_button(self, *args):
        '''Event handler for 'on_release' event of cancel_button.
        '''
        self.cancel_button.bind(on_press=partial(self.dispatch, 'on_cancel'))

    def on_select(self, *args):
        '''Default event handler for 'on_select' event.
        '''
        pass

    def on_cancel(self, *args):
        '''Default event handler for 'on_cancel' event.
        '''
        pass

########NEW FILE########
__FILENAME__ = start_page
import webbrowser

from kivy.app import App
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.gridlayout import GridLayout
from kivy.uix.button import Button
from kivy.uix.label import Label
from kivy.uix.scrollview import ScrollView
from kivy.properties import StringProperty, ObjectProperty
from kivy.metrics import pt
from kivy.clock import Clock


class DesignerLinkLabel(Button):
    '''DesignerLinkLabel displays a http link and opens it in a browser window
       when clicked.
    '''

    link = StringProperty(None)
    '''Contains the http link to be opened.
       :data:`link` is a :class:`~kivy.properties.StringProperty`
    '''

    def on_release(self, *args):
        '''Default event handler for 'on_release' event.
        '''
        if self.link:
            webbrowser.open(self.link)


class RecentFilesBox(ScrollView):
    '''Container consistings of buttons, with their names specifying
       the recent files.
    '''

    grid = ObjectProperty(None)
    '''The grid layout consisting of all buttons.
       This property is an instance of :class:`~kivy.uix.gridlayout`
       :data:`grid` is a :class:`~kivy.properties.ObjectProperty`
    '''

    root = ObjectProperty(None)
    '''Reference to :class:`~designer.app.Designer`
       :data:`root` is a :class:`~kivy.properties.ObjectProperty`
    '''

    def __init__(self, **kwargs):
        super(RecentFilesBox, self).__init__(**kwargs)

    def _setup_width(self, *args):
        '''To set appropriate width of RecentFilesBox.
        '''
        max_width = -1
        for child in self.grid.children:
            max_width = max(child.texture_size[0], max_width)

        self.width = max_width + pt(20)

    def add_recent(self, list_files):
        '''To add buttons representing Recent Files.
        '''
        for i in list_files:
            btn = Button(text=i, size_hint_y=None, height=pt(22))
            self.grid.add_widget(btn)
            btn.bind(size=self._btn_size_changed)
            btn.bind(on_release=self.btn_release)
            btn.valign = 'middle'
            self.grid.height += btn.height

        self.grid.height = max(self.grid.height, self.height)
        Clock.schedule_once(self._setup_width, 0.01)

    def _btn_size_changed(self, instance, value):
        '''Event Handler for 'on_size' of buttons added.
        '''
        instance.text_size = value

    def btn_release(self, instance):
        '''Event Handler for 'on_release' of an event.
        '''
        self.root._perform_open(instance.text)


class DesignerStartPage(GridLayout):
    '''This is the start page of the Designer. It will contain two buttons
       'Open Project' and 'New Project', two DesignerLinkLabel
       'Kivy' and 'Kivy Designer Help' and a RecentFilesBox. It emits two
       events 'on_open_down' when 'Open Project' is clicked and
       'on_new_down' when 'New Project' is clicked.
    '''

    btn_open = ObjectProperty(None)
    '''The 'Open Project' Button.
       This property is an instance of :class:`~kivy.uix.button`
       :data:`btn_open` is a :class:`~kivy.properties.ObjectProperty`
    '''

    btn_new = ObjectProperty(None)
    '''The 'New Project' Button.
       This property is an instance of :class:`~kivy.uix.button`
       :data:`btn_new` is a :class:`~kivy.properties.ObjectProperty`
    '''

    recent_files_box = ObjectProperty(None)
    '''This property is an instance
        of :class:`~designer.start_page.RecentFilesBox`
       :data:`recent_files_box` is a :class:`~kivy.properties.ObjectProperty`
    '''

    kivy_link = ObjectProperty(None)
    '''The 'Kivy' DesignerLinkLabel.
       :data:`kivy_link` is a :class:`~kivy.properties.ObjectProperty`
    '''

    designer_link = ObjectProperty(None)
    '''The 'Kivy Designer Help' DesignerLinkLabel.
       :data:`designer_link` is a :class:`~kivy.properties.ObjectProperty`
    '''

    __events__ = ('on_open_down', 'on_new_down', 'on_help')

    def on_open_down(self, *args):
        '''Default Event Handler for 'on_open_down'
        '''
        pass

    def on_new_down(self, *args):
        '''Default Event Handler for 'on_new_down'
        '''
        pass

    def on_help(self, *args):
        '''Default Event Handler for 'on_help'
        '''
        pass

########NEW FILE########
__FILENAME__ = statusbar
from kivy.properties import ObjectProperty
from kivy.uix.button import Button
from kivy.uix.label import Label
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.gridlayout import GridLayout
from kivy.uix.tabbedpanel import TabbedPanelContent, TabbedPanelHeader,\
    TabbedPanel

from kivy.uix.sandbox import SandboxContent


class StatusNavBarButton(Button):
    '''StatusNavBarButton is a :class:`~kivy.uix.button` representing
       the Widgets in the Widget heirarchy of currently selected widget.
    '''

    node = ObjectProperty()


class StatusNavBarSeparator(Label):
    '''StatusNavBarSeparator :class:`~kivy.uix.label.Label`
       Used to separate two Widgets by '>'
    '''

    pass


class StatusBar(BoxLayout):
    '''StatusBar used to display Widget heirarchy of currently selected
       widget and to display messages.
    '''

    app = ObjectProperty()
    '''Reference to current app instance.
       :data:`app` is an
       :class:`~kivy.properties.ObjectProperty`
    '''

    navbar = ObjectProperty()
    '''To be used as parent of :class:`~designer.statusbar.StatusNavBarButton`
       and :class:`~designer.statusbar.StatusNavBarSeparator`.
       :data:`navbar` is an
       :class:`~kivy.properties.ObjectProperty`
    '''

    gridlayout = ObjectProperty()
    '''Parent of :data:`navbar`.
       :data:`gridlayout` is an
       :class:`~kivy.properties.ObjectProperty`
    '''

    playground = ObjectProperty()
    '''Instance of
       :data:`playground` is an
       :class:`~kivy.properties.ObjectProperty`
    '''

    def show_message(self, message):
        '''To show a message in StatusBar
        '''

        self.app.widget_focused = None
        if (self.gridlayout.children or not
                isinstance(self.gridlayout.children[0], Label)):
            #Create navbar again, as doing clear_widgets
            #will make its reference
            #count to 0 and it will be destroyed
            self.navbar = GridLayout(rows=1)

        self.gridlayout.clear_widgets()
        self.gridlayout.add_widget(Label(text=message))
        self.gridlayout.children[0].text = message

    def on_app(self, instance, app):
        app.bind(widget_focused=self.update_navbar)

    def update_navbar(self, *largs):
        '''To update navbar with the parents of currently selected Widget.
        '''

        if self.gridlayout.children and\
                isinstance(self.gridlayout.children[0], Label):
            self.gridlayout.clear_widgets()
            self.gridlayout.add_widget(self.navbar)

        self.navbar.clear_widgets()
        wid = self.app.widget_focused
        if not wid:
            return

        # get parent list, until app.root.playground.root
        children = []
        while wid:
            if wid == self.playground.sandbox or\
                    wid == self.playground.sandbox.children[0]:
                break

            if isinstance(wid, TabbedPanelContent):
                _wid = wid
                wid = wid.parent.current_tab
                children.append(StatusNavBarButton(node=wid))
                wid = _wid.parent

            elif isinstance(wid, TabbedPanelHeader):
                children.append(StatusNavBarButton(node=wid))
                _wid = wid
                while _wid and not isinstance(_wid, TabbedPanel):
                    _wid = _wid.parent
                wid = _wid

            children.append(StatusNavBarButton(node=wid))
            wid = wid.parent

        count = len(children)
        for index, child in enumerate(reversed(children)):
            self.navbar.add_widget(child)
            if index < count - 1:
                self.navbar.add_widget(StatusNavBarSeparator())
            else:
                child.state = 'down'

########NEW FILE########
__FILENAME__ = toolbox
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.label import Label
from kivy.uix.button import Button
from kivy.properties import ObjectProperty
from kivy.clock import Clock
from designer.common import widgets
from kivy.uix.accordion import Accordion, AccordionItem
from kivy.metrics import pt
from kivy.factory import Factory


class ToolboxCategory(AccordionItem):
    '''ToolboxCategory is responsible for grouping and showing
       :class:`~designer.toolbox.ToolboxButton`
       of same class into one category.
    '''

    gridlayout = ObjectProperty(None)
    '''An instance of :class:`~kivy.uix.gridlayout.GridLayout`.
       :data:`gridlayout` is an
       :class:`~kivy.properties.ObjectProperty`
    '''


class ToolboxButton(Button):
    '''ToolboxButton is a subclass of :class:`~kivy.uix.button.Button`,
       to display class of Widgets in
       :class:`~designer.toolbox.ToolboxCategory`.
    '''

    def __init__(self, **kwargs):
        self.register_event_type('on_press_and_touch')
        super(ToolboxButton, self).__init__(**kwargs)

    def on_touch_down(self, touch):
        '''Default handler for 'on_touch_down'
        '''
        if self.collide_point(*touch.pos):
            self.dispatch('on_press_and_touch', touch)
        return super(ToolboxButton, self).on_touch_down(touch)

    def on_press_and_touch(self, touch):
        '''Default handler for 'on_press_and_touch' event
        '''
        pass


class Toolbox(BoxLayout):
    '''Toolbox is used to display all the widgets in designer.common.widgets
       in their respective classes.
    '''

    accordion = ObjectProperty()
    '''An instance to :class:`~kivy.uix.accordion.Accordion`,
       used to show Widgets in their groups.
       :data:`accordion` is an
       :class:`~kivy.properties.ObjectProperty`
    '''

    app = ObjectProperty()
    '''An instance to the current running app.
       :data:`app` is an
       :class:`~kivy.properties.ObjectProperty`
    '''

    def __init__(self, **kwargs):
        super(Toolbox, self).__init__(**kwargs)
        Clock.schedule_once(self.discover_widgets, 0)
        self.custom_category = None
        self._list = []

    def discover_widgets(self, *largs):
        '''To create and add ToolboxCategory and ToolboxButton for widgets in
           designer.common.widgets
        '''
        # for now, don't do auto detection of widgets.
        # just do manual discovery, and tagging.

        categories = list(set([x[1] for x in widgets]))
        for category in categories:
            toolbox_category = ToolboxCategory(title=category)
            self.accordion.add_widget(toolbox_category)
            
            cat_widgets = []
            for widget in widgets:
                if widget[1] == category:
                    cat_widgets.append(widget)
            
            cat_widgets.sort()
            for widget in cat_widgets:
                toolbox_category.gridlayout.add_widget(
                    ToolboxButton(text=widget[0]))

        self.accordion.children[-1].collapse = False

    def cleanup(self):
        '''To clean all the children in self.custom_category.
        '''
        if self.custom_category:
            self.accordion.remove_widget(self.custom_category)
            Factory.register('BoxLayout', module='kivy.uix.boxlayout')
            self.custom_category = ToolboxCategory(title='custom')
            self._list.append(self.custom_category)

            #FIXME: ToolboxCategory keeps on adding more scrollview,
            #if they are initialized again, unable to find the cause of problem
            #I just decided to delete those scrollview whose childs are not
            #self.gridlayout.
            _scrollview_parent = self.custom_category.gridlayout.parent.parent
            for child in _scrollview_parent.children[:]:
                if child.children[0] != self.custom_category.gridlayout:
                    _scrollview_parent.remove_widget(child)

    def add_custom(self):
        '''To add/update self.custom_category with new custom classes loaded
           by project.
        '''
        self.custom_category = ToolboxCategory(title='custom')
        self._list.append(self.custom_category)

        self.accordion.add_widget(self.custom_category)
        
        custom_widgets = []
        for widget in widgets:
            if widget[1] == 'custom':
                custom_widgets.append(widget)
        
        custom_widgets.sort()
        for widget in custom_widgets:
            self.custom_category.gridlayout.add_widget(
                ToolboxButton(text=widget[0]))

        #Setting appropriate height to gridlayout to enable scrolling
        self.custom_category.gridlayout.size_hint_y = None
        self.custom_category.gridlayout.height = \
            (len(self.custom_category.gridlayout.children)+5)*pt(22)

########NEW FILE########
__FILENAME__ = tree
from kivy.uix.widget import Widget


class TreeException(Exception):
    pass


class TreeNode(object):
    '''TreeNode class for representing information of Widgets
    '''

    def __init__(self):
        super(TreeNode, self).__init__()

        self.parent_node = None
        self.list_children = []
        self.class_name = ''
        self.base_class_name = ''
        self.is_subclassed = False
        self.widget = None


class Tree(object):
    '''Tree class for saving all the information regarding widgets
    '''

    def __init__(self):
        super(Tree, self).__init__()

        self.list_root_nodes = []

    def insert(self, widget, parent=None):
        '''inserts a new node of widget with parent.
           Returns new node on success
        '''

        if not isinstance(widget, Widget):
            TreeException('Tree accepts only Widget to be inserted')

        if parent is None:
            node = TreeNode()
            node.widget = widget
            self.list_root_nodes.append(node)
            return node

        if not isinstance(parent, Widget):
            TreeException('Tree only accepts parent to be a Widget')

        parent_node = self.get_node_for_widget(parent)
        node = TreeNode()
        node.widget = widget
        node.parent_node = parent_node
        if parent_node is None:
            self.list_root_nodes.append(node)
        else:
            parent_node.list_children.append(node)
        return node

    def _get_node_for_widget(self, widget, node):
        if node.widget == widget:
            return node

        for _node in node.list_children:
            node_found = self._get_node_for_widget(widget, _node)
            if node_found is not None:
                return node_found

        return None

    def get_node_for_widget(self, widget):
        '''Returns node for widget, None if not found
        '''
        for _root in self.list_root_nodes:
            node = self._get_node_for_widget(widget, _root)
            if node is not None:
                return node

        return None

    def traverse_tree(self, node=None):
        '''Traverse the tree, and run traverse code for every node
        '''
        if node is None:
            for _node in self.list_root_nodes:
                self.traverse_tree(_node)
        else:
            #Add traverse code here
            for child in node.list_children:
                self.traverse_tree(child)

    def delete(self, widget):
        '''deletes a node of widget from the Tree.
           Returns that node on deletion
        '''
        if not isinstance(widget, Widget):
            TreeException('Tree accepts only Widget to be deleted')

        node = self.get_node_for_widget(widget)
        if node in self.list_root_nodes:
            self.list_root_nodes.remove(node)
        else:
            node.parent_node.list_children.remove(node)
        return node

########NEW FILE########
__FILENAME__ = actioncheckbutton
from kivy.uix.actionbar import ActionItem
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.label import Label
from kivy.uix.checkbox import CheckBox
from kivy.properties import ObjectProperty, StringProperty
from kivy.clock import Clock

from functools import partial


class ActionCheckButton(ActionItem, BoxLayout):
    '''ActionCheckButton is a check button displaying text with a checkbox
    '''

    checkbox = ObjectProperty(None)
    '''Instance of :class:`~kivy.uix.checkbox.CheckBox`.
       :data:`checkbox` is a :class:`~kivy.properties.StringProperty`
    '''

    text = StringProperty('Check Button')
    '''text which is displayed by ActionCheckButton.
       :data:`text` is a :class:`~kivy.properties.StringProperty`
    '''

    cont_menu = ObjectProperty(None)

    __events__ = ('on_active',)

    def __init__(self, **kwargs):
        super(ActionCheckButton, self).__init__(**kwargs)
        self._label = Label()
        self.checkbox = CheckBox(active=True)
        self.checkbox.size_hint_x = None
        self.checkbox.x = self.x + 2
        self.checkbox.width = '20sp'
        BoxLayout.add_widget(self, self.checkbox)
        BoxLayout.add_widget(self, self._label)
        self._label.valign = 'middle'
        self._label.text = self.text
        self.checkbox.bind(active=partial(self.dispatch, 'on_active'))
        Clock.schedule_once(self._label_setup, 0)

    def _label_setup(self, dt):
        '''To setup text_size of _label
        '''
        self._label.text_size = (self.minimum_width - self.checkbox.width - 4,
                                 self._label.size[1])

    def on_touch_down(self, touch):
        '''Override of its parent's on_touch_down, used to reverse the state
           of CheckBox.
        '''
        if not self.disabled and self.collide_point(*touch.pos):
            self.checkbox.active = not self.checkbox.active
            self.cont_menu.dismiss()

    def on_active(self, *args):
        '''Default handler for 'on_active' event.
        '''
        pass

    def on_text(self, instance, value):
        '''Used to set the text of label
        '''
        self._label.text = value

########NEW FILE########
__FILENAME__ = contextual
from kivy.uix.tabbedpanel import TabbedPanel, TabbedPanelItem,\
    TabbedPanelHeader, TabbedPanelContent
from kivy.properties import ObjectProperty, StringProperty,\
    BooleanProperty, NumericProperty
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.gridlayout import GridLayout
from kivy.uix.widget import Widget
from kivy.uix.button import Button
from kivy.uix.floatlayout import FloatLayout
from kivy.uix.image import Image
from kivy.uix.bubble import Bubble, BubbleButton
from kivy.lang import Builder
from kivy.metrics import dp
from kivy.uix.scrollview import ScrollView
from kivy.clock import Clock


class MenuBubble(Bubble):
    '''
    '''
    pass


class MenuHeader(TabbedPanelHeader):
    '''MenuHeader class. To be used as default TabbedHeader.
    '''
    show_arrow = BooleanProperty(False)
    '''Specifies whether to show arrow or not.
       :data:`show_arrow` is a :class:`~kivy.properties.BooleanProperty`,
       default to True
    '''


class ContextMenuException(Exception):
    '''ContextMenuException class
    '''
    pass


class MenuButton(Button):
    '''MenuButton class. Used as a default menu button. It auto provides
       look and feel for a menu button.
    '''
    cont_menu = ObjectProperty(None)
    '''Reference to :class:`~designer.uix.contextual.ContextMenu`.
    '''

    def on_release(self, *args):
        '''Default Event Handler for 'on_release'
        '''
        self.cont_menu.dismiss()
        super(MenuButton, self).on_release(*args)


class ContextMenu(TabbedPanel):
    '''ContextMenu class. See module documentation for more information.
      :Events:
        `on_select`: data
            Fired when a selection is done, with the data of the selection as
            first argument. Data is what you pass in the :meth:`select` method
            as first argument.
        `on_dismiss`:
            .. versionadded:: 1.8.0

            Fired when the ContextMenu is dismissed either on selection or on
            touching outside the widget.
    '''
    container = ObjectProperty(None)
    '''(internal) The container which will be used to contain Widgets of
       main menu.
       :data:`container` is a :class:`~kivy.properties.ObjectProperty`, default
       to :class:`~kivy.uix.boxlayout.BoxLayout`.
    '''

    main_tab = ObjectProperty(None)
    '''Main Menu Tab of ContextMenu.
       :data:`main_tab` is a :class:`~kivy.properties.ObjectProperty`, default
       to None.
    '''

    bubble_cls = ObjectProperty(MenuBubble)
    '''Bubble Class, whose instance will be used to create
       container of ContextMenu.
       :data:`bubble_cls` is a :class:`~kivy.properties.ObjectProperty`,
       default to :class:`MenuBubble`.
    '''

    header_cls = ObjectProperty(MenuHeader)
    '''Header Class used to create Tab Header.
       :data:`header_cls` is a :class:`~kivy.properties.ObjectProperty`,
       default to :class:`MenuHeader`.
    '''

    attach_to = ObjectProperty(allownone=True)
    '''(internal) Property that will be set to the widget on which the
       drop down list is attached to.

       The method :meth:`open` will automatically set that property, while
       :meth:`dismiss` will set back to None.
    '''

    auto_width = BooleanProperty(True)
    '''By default, the width of the ContextMenu will be the same
       as the width of the attached widget. Set to False if you want
       to provide your own width.
    '''

    dismiss_on_select = BooleanProperty(True)
    '''By default, the ContextMenu will be automatically dismissed
    when a selection have been done. Set to False to prevent the dismiss.

    :data:`dismiss_on_select` is a :class:`~kivy.properties.BooleanProperty`,
    default to True.
    '''

    max_height = NumericProperty(None, allownone=True)
    '''Indicate the maximum height that the dropdown can take. If None, it will
    take the maximum height available, until the top or bottom of the screen
    will be reached.

    :data:`max_height` is a :class:`~kivy.properties.NumericProperty`, default
    to None.
    '''

    __events__ = ('on_select', 'on_dismiss')

    def __init__(self, **kwargs):
        self._win = None
        self.add_tab = super(ContextMenu, self).add_widget
        self.bubble = self.bubble_cls(size_hint=(None, None))
        self.container = None
        self.main_tab = self.header_cls(text='Main')
        self.main_tab.content = ScrollView(size_hint=(1, 1))
        self.main_tab.content.bind(height=self.on_scroll_height)

        super(ContextMenu, self).__init__(**kwargs)
        self.bubble.add_widget(self)
        self.bind(size=self._reposition)
        self.bubble.bind(on_height=self._bubble_height)

    def _bubble_height(self, *args):
        '''Handler for bubble's 'on_height' event.
        '''
        self.height = self.bubble.height

    def open(self, widget):
        '''Open the dropdown list, and attach to a specific widget.
           Depending the position of the widget on the window and
           the height of the dropdown, the placement might be
           lower or higher off that widget.
        '''
        #ensure we are not already attached
        if self.attach_to is not None:
            self.dismiss()

        #we will attach ourself to the main window, so ensure the widget we are
        #looking for have a window
        self._win = widget.get_parent_window()
        if self._win is None:
            raise ContextMenuException(
                'Cannot open a dropdown list on a hidden widget')

        self.attach_to = widget
        widget.bind(pos=self._reposition, size=self._reposition)

        self.add_tab(self.main_tab)
        self.switch_to(self.main_tab)
        self.main_tab.show_arrow = False

        self._reposition()

        # attach ourself to the main window
        self._win.add_widget(self.bubble)
        self.main_tab.color = (0, 0, 0, 0)

    def on_select(self, data):
        '''Default handler for 'on_select' event.
        '''
        pass

    def dismiss(self, *largs):
        '''Remove the dropdown widget from the iwndow, and detach itself from
        the attached widget.
        '''
        if self.bubble.parent:
            self.bubble.parent.remove_widget(self.bubble)
        if self.attach_to:
            self.attach_to.unbind(pos=self._reposition, size=self._reposition)
            self.attach_to = None

        self.switch_to(self.main_tab)

        for child in self.tab_list[:]:
            self.remove_widget(child)

        self.dispatch('on_dismiss')

    def select(self, data):
        '''Call this method to trigger the `on_select` event, with the `data`
        selection. The `data` can be anything you want.
        '''
        self.dispatch('on_select', data)
        if self.dismiss_on_select:
            self.dismiss()

    def on_dismiss(self):
        '''Default event handler for 'on_dismiss' event.
        '''
        pass

    def _set_width_to_bubble(self, *args):
        '''To set self.width and bubble's width equal.
        '''
        self.width = self.bubble.width

    def _reposition(self, *largs):
        # calculate the coordinate of the attached widget in the window
        # coordinate sysem
        win = self._win
        widget = self.attach_to
        if not widget or not win:
            return

        wx, wy = widget.to_window(*widget.pos)
        wright, wtop = widget.to_window(widget.right, widget.top)

        # set width and x
        if self.auto_width:
            #Calculate minimum required width
            if len(self.container.children) == 1:
                self.bubble.width = max(self.main_tab.parent.parent.width,
                                        self.container.children[0].width)
            else:
                self.bubble.width = max(self.main_tab.parent.parent.width,
                                        self.bubble.width,
                                        *([i.width
                                           for i in self.container.children]))

        Clock.schedule_once(self._set_width_to_bubble, 0.01)
        # ensure the dropdown list doesn't get out on the X axis, with a
        # preference to 0 in case the list is too wide.
        x = wx
        if x + self.bubble.width > win.width:
            x = win.width - self.bubble.width
        if x < 0:
            x = 0
        self.bubble.x = x

        #determine if we display the dropdown upper or lower to the widget
        h_bottom = wy - self.bubble.height
        h_top = win.height - (wtop + self.bubble.height)
        if h_bottom > 0:
            self.bubble.top = wy
            self.bubble.arrow_pos = 'top_mid'
        elif h_top > 0:
            self.bubble.y = wtop
            self.bubble.arrow_pos = 'bottom_mid'
        else:
            #none of both top/bottom have enough place to display the widget at
            #the current size. Take the best side, and fit to it.
            height = max(h_bottom, h_top)
            if height == h_bottom:
                self.bubble.top = wy
                self.bubble.height = wy
                self.bubble.arrow_pos = 'top_mid'
            else:
                self.bubble.y = wtop
                self.bubble.height = win.height - wtop
                self.bubble.arrow_pos = 'bottom_mid'

    def on_touch_down(self, touch):
        '''Default Handler for 'on_touch_down'
        '''
        if super(ContextMenu, self).on_touch_down(touch):
            return True
        if self.collide_point(*touch.pos):
            return True
        self.dismiss()

    def on_touch_up(self, touch):
        '''Default Handler for 'on_touch_up'
        '''

        if super(ContextMenu, self).on_touch_up(touch):
            return True
        self.dismiss()

    def add_widget(self, widget, index=0):
        '''Add a widget.
        '''
        if self.tab_list and widget == self.tab_list[0].content or\
                widget == self._current_tab.content or \
                self.content == widget or\
                self._tab_layout == widget or\
                isinstance(widget, TabbedPanelContent) or\
                isinstance(widget, TabbedPanelHeader):
            super(ContextMenu, self).add_widget(widget, index)
            return

        if not self.container:
            self.container = GridLayout(orientation='vertical',
                                        size_hint_y=None,
                                        cols=1)
            self.main_tab.content.add_widget(self.container)
            self.container.bind(height=self.on_main_box_height)

        self.container.add_widget(widget, index)

        if hasattr(widget, 'cont_menu'):
            widget.cont_menu = self

        widget.bind(height=self.on_child_height)
        widget.size_hint_y = None

    def remove_widget(self, widget):
        '''Remove a widget
        '''
        if self.container and widget in self.container.children:
            self.container.remove_widget(widget)
        else:
            super(ContextMenu, self).remove_widget(widget)

    def on_scroll_height(self, *args):
        '''Event Handler for scollview's height.
        '''
        if not self.container:
            return

        self.container.height = max(self.container.height,
                                    self.main_tab.content.height)

    def on_main_box_height(self, *args):
        '''Event Handler for main_box's height.
        '''

        if not self.container:
            return

        self.container.height = max(self.container.height,
                                    self.main_tab.content.height)

        if self.max_height:
            self.bubble.height = min(self.container.height +
                                     self.tab_height + dp(16),
                                     self.max_height)
        else:
            self.bubble.height = self.container.height + \
                self.tab_height + dp(16)

    def on_child_height(self, *args):
        '''Event Handler for children's height.
        '''
        height = 0
        for i in self.container.children:
            height += i.height

        self.main_tab.content.height = height
        self.container.height = height

    def add_tab(self, widget, index=0):
        '''To add a Widget as a new Tab.
        '''
        super(ContextMenu, self).add_widget(widget, index)


class ContextSubMenu(MenuButton):
    '''ContextSubMenu class. To be used to add a sub menu.
    '''

    attached_menu = ObjectProperty(None)
    '''(internal) Menu attached to this sub menu.
    :data:`attached_menu` is a :class:`~kivy.properties.ObjectProperty`,
    default to None.
    '''

    cont_menu = ObjectProperty(None)
    '''(internal) Reference to the main ContextMenu.
    :data:`cont_menu` is a :class:`~kivy.properties.ObjectProperty`,
    default to None.
    '''

    container = ObjectProperty(None)
    '''(internal) The container which will be used to contain Widgets of
       main menu.
       :data:`container` is a :class:`~kivy.properties.ObjectProperty`, default
       to :class:`~kivy.uix.boxlayout.BoxLayout`.
    '''

    show_arrow = BooleanProperty(False)
    '''(internal) To specify whether ">" arrow image should be shown in the
       header or not. If there exists a child menu then arrow image will be
       shown otherwise not.
       :data:`show_arrow` is a
       :class:`~kivy.properties.BooleanProperty`, default to False
    '''

    def __init__(self, **kwargs):
        super(ContextSubMenu, self).__init__(**kwargs)
        self._list_children = []

    def on_text(self, *args):
        '''Default handler for text.
        '''
        if self.attached_menu:
            self.attached_menu.text = self.text

    def on_attached_menu(self, *args):
        '''Default handler for attached_menu.
        '''
        self.attached_menu.text = self.text

    def add_widget(self, widget, index=0):
        '''Add a widget.
        '''
        if isinstance(widget, Image):
            Button.add_widget(self, widget, index)
            return

        self._list_children.append((widget, index))
        if hasattr(widget, 'cont_menu'):
            widget.cont_menu = self.cont_menu

    def on_cont_menu(self, *args):
        '''Default handler for cont_menu.
        '''
        self._add_widget()

    def _add_widget(self, *args):
        if not self.cont_menu:
            return

        if not self.attached_menu:
            self.attached_menu = self.cont_menu.header_cls(text=self.text)
            self.attached_menu.content = ScrollView(size_hint=(1, 1))
            self.attached_menu.content.bind(height=self.on_scroll_height)
            self.container = GridLayout(orientation='vertical',
                                        size_hint_y=None, cols=1)

            self.attached_menu.content.add_widget(self.container)
            self.container.bind(height=self.on_container_height)

        for widget, index in self._list_children:
            self.container.add_widget(widget, index)
            widget.cont_menu = self.cont_menu
            widget.bind(height=self.on_child_height)

    def on_scroll_height(self, *args):
        '''Handler for scrollview's height.
        '''
        self.container.height = max(self.container.height,
                                    self.attached_menu.content.height)

    def on_container_height(self, *args):
        '''Handler for container's height.
        '''
        self.container.height = max(self.container.height,
                                    self.attached_menu.content.height)

    def on_child_height(self, *args):
        '''Handler for children's height.
        '''
        height = 0
        for i in self.container.children:
            height += i.height

        self.container.height = height

    def on_release(self, *args):
        '''Default handler for 'on_release' event.
        '''
        if not self.attached_menu or not self._list_children:
            return

        try:
            index = self.cont_menu.tab_list.index(self.attached_menu)
            self.cont_menu.switch_to(self.cont_menu.tab_list[index])
            tab = self.cont_menu.tab_list[index]
            if hasattr(tab, 'show_arrow') and index != 0:
                tab.show_arrow = True
            else:
                tab.show_arrow = False

        except:
            curr_index = self.cont_menu.tab_list.index(
                self.cont_menu.current_tab)
            for i in range(curr_index - 1, -1, -1):
                self.cont_menu.remove_widget(self.cont_menu.tab_list[i])

            self.cont_menu.add_tab(self.attached_menu)
            self.cont_menu.switch_to(self.cont_menu.tab_list[0])
            if hasattr(self.cont_menu.tab_list[1], 'show_arrow'):
                self.cont_menu.tab_list[1].show_arrow = True
            else:
                self.cont_menu.tab_list[1].show_arrow = False

        from kivy.clock import Clock
        Clock.schedule_once(self._scroll, 0.1)

    def _scroll(self, dt):
        '''To scroll ContextMenu's strip to appropriate place.
        '''
        from kivy.animation import Animation
        self.cont_menu._reposition()
        total_tabs = len(self.cont_menu.tab_list)
        tab_list = self.cont_menu.tab_list
        curr_index = total_tabs - tab_list.index(self.cont_menu.current_tab)
        to_scroll = len(tab_list) / curr_index
        anim = Animation(scroll_x=to_scroll, d=0.75)
        anim.cancel_all(self.cont_menu.current_tab.parent.parent)
        anim.start(self.cont_menu.current_tab.parent.parent)

if __name__ == '__main__':
    from kivy.app import App

    from kivy.uix.actionbar import ActionItem

    class ActionContext(ContextSubMenu, ActionItem):
        pass

    Builder.load_string('''
#:import ContextMenu contextual.ContextMenu

<ContextMenu>:
<Test>:
    ActionBar:
        pos_hint: {'top':1}
        ActionView:
            use_separator: True
            ActionPrevious:
                title: 'Action Bar'
                with_previous: False
            ActionOverflow:
            ActionButton:
                text: 'Btn0'
                icon: 'atlas://data/images/defaulttheme/audio-volume-high'
            ActionButton:
                text: 'Btn1'
            ActionButton:
                text: 'Btn2'
            ActionButton:
                text: 'Btn3'
            ActionButton:
                text: 'Btn4'
            ActionGroup:
                mode: 'spinner'
                text: 'Group1'
                dropdown_cls: ContextMenu
                ActionButton:
                    text: 'Btn5'
                    height: 30
                    size_hint_y: None
                ActionButton:
                    text: 'Btnddddddd6'
                    height: 30
                    size_hint_y: None
                ActionButton:
                    text: 'Btn7'
                    height: 30
                    size_hint_y: None

                ActionContext:
                    text: 'Item2'
                    size_hint_y: None
                    height: 30
                    ActionButton:
                        text: '2->1'
                        size_hint_y: None
                        height: 30
                    ActionButton:
                        text: '2->2'
                        size_hint_y: None
                        height: 30
                    ActionButton:
                        text: '2->2'
                        size_hint_y: None
                        height: 30
''')

    class CMenu(ContextMenu):
        pass

    class Test(FloatLayout):
        def __init__(self, **kwargs):
            super(Test, self).__init__(**kwargs)
            self.context_menu = CMenu()

        def add_menu(self, obj, *l):
            self.context_menu = CMenu()
            self.context_menu.open(self.children[0])

    class MyApp(App):
        def build(self):
            return Test()

    MyApp().run()

########NEW FILE########
__FILENAME__ = designer_action_items
from kivy.uix.actionbar import ActionGroup, ActionButton, \
    ActionPrevious, ActionItem
from designer.uix.contextual import MenuButton, ContextMenu, ContextSubMenu


class DesignerActionPrevious(ActionPrevious):
    pass


class DesignerActionSubMenu(ContextSubMenu, ActionItem):
    pass


class DesignerActionGroup(ActionGroup):
    pass


class DesignerActionButton(ActionItem, MenuButton):
    pass

########NEW FILE########
__FILENAME__ = designer_code_input
from kivy.uix.codeinput import CodeInput
from kivy.core.clipboard import Clipboard
from kivy.properties import BooleanProperty


class DesignerCodeInput(CodeInput):
    '''A subclass of CodeInput to be used for KivyDesigner.
       It has copy, cut and paste functions, which otherwise are accessible
       only using Keyboard.
       It emits on_show_edit event whenever clicked, this is catched
       to show EditContView;
    '''

    __events__ = ('on_show_edit',)

    clicked = BooleanProperty(False)
    '''If clicked is True, then it confirms that this widget has been clicked.
       The one checking this property, should set it to False.
       :data:`clicked` is a :class:`~kivy.properties.BooleanProperty`
    '''

    def on_show_edit(self, *args):
        pass

    def on_touch_down(self, touch):
        '''Override of CodeInput's on_touch_down event.
           Used to emit on_show_edit
        '''

        if self.collide_point(*touch.pos):
            self.clicked = True
            self.dispatch('on_show_edit')

        return super(DesignerCodeInput, self).on_touch_down(touch)

    def do_copy(self):
        '''Function to do copy operation
        '''

        if self.selection_text == '':
            return

        self._copy(self.selection_text)

    def do_cut(self):
        '''Function to do cut operation
        '''

        if self.selection_text == '':
            return

        self._cut(self.selection_text)

    def do_paste(self):
        '''Function to do paste operation
        '''

        self._paste()

    def do_select_all(self):
        '''Function to select all text
        '''

        self.select_text(0, len(self.text))

    def do_delete(self):
        '''Function to delete selected text
        '''

        if self.selection_text != '':
            self.do_backspace()

########NEW FILE########
__FILENAME__ = designer_sandbox
from kivy.uix.sandbox import Sandbox, SandboxExceptionManager, sandbox
from kivy.properties import BooleanProperty
from kivy.lang import Builder
from kivy.clock import Clock
from kivy.context import Context
from kivy.uix.floatlayout import FloatLayout


class DesignerSandbox(Sandbox):
    '''DesignerSandbox is subclass of :class:`~kivy.uix.sandbox.Sandbox`
       for use with Kivy Designer. It emits on_getting_exeption event
       when code running in it will raise some exception.
    '''

    __events__ = ('on_getting_exception',)
    error_active = BooleanProperty(False)

    def __init__(self, **kwargs):
        super(DesignerSandbox, self).__init__(**kwargs)
        self._context['Builder'] = object.__getattribute__(Builder, '_obj')
        self._context['Clock'] = object.__getattribute__(Clock, '_obj')
        Clock.unschedule(self._clock_sandbox)
        Clock.unschedule(self._clock_sandbox_draw)

    def __exit__(self, _type, value, tb):
        '''Override of __exit__
        '''
        self._context.pop()
        #print 'EXITING THE SANDBOX', (self, _type, value, tb)
        if _type is not None:
            return self.on_exception(value, tb=tb)

    def on_exception(self, exception, tb=None):
        '''Override of on_exception
        '''
        self.exception = exception
        self.tb = tb
        self.dispatch('on_getting_exception')
        return super(DesignerSandbox, self).on_exception(exception, tb)

    def on_getting_exception(self, *args):
        '''Default handler for 'on_getting_exception'
        '''
        pass

    @sandbox
    def _clock_sandbox(self, dt):
        pass

    @sandbox
    def _clock_sandbox_draw(self, dt):
        pass

########NEW FILE########
__FILENAME__ = editcontview
from kivy.uix.actionbar import ContextualActionView, ActionButton
from kivy.properties import ObjectProperty

from functools import partial


class EditContView(ContextualActionView):
    '''EditContView is a ContextualActionView, used to display Edit items:
       Copy, Cut, Paste, Undo, Redo, Select All, Add Custom Widget. It has
       events:
       on_undo, emitted when Undo ActionButton is clicked.
       on_redo, emitted when Redo ActionButton is clicked.
       on_cut, emitted when Cut ActionButton is clicked.
       on_copy, emitted when Copy ActionButton is clicked.
       on_paste, emitted when Paste ActionButton is clicked.
       on_delete, emitted when Delete ActionButton is clicked.
       on_selectall, emitted when Select All ActionButton is clicked.
       on_add_custom, emitted when Add Custom ActionButton is clicked.
    '''

    __events__ = ('on_undo', 'on_redo', 'on_cut', 'on_copy',
                  'on_paste', 'on_delete', 'on_selectall',
                  'on_next_screen', 'on_prev_screen')

    action_btn_next_screen = ObjectProperty(None, allownone=True)
    action_btn_prev_screen = ObjectProperty(None, allownone=True)

    def show_action_btn_screen(self, show):
        '''To add action_btn_next_screen and action_btn_prev_screen
           if show is True. Otherwise not.
        '''
        if self.action_btn_next_screen:
            self.remove_widget(self.action_btn_next_screen)
        if self.action_btn_prev_screen:
            self.remove_widget(self.action_btn_prev_screen)

        self.action_btn_next_screen = None
        self.action_btn_prev_screen = None

        if show:
            self.action_btn_next_screen = ActionButton(text="Next Screen")
            self.action_btn_next_screen.bind(
                on_press=partial(self.dispatch, 'on_next_screen'))
            self.action_btn_prev_screen = ActionButton(text="Previous Screen")
            self.action_btn_prev_screen.bind(
                on_press=partial(self.dispatch, 'on_prev_screen'))

            self.add_widget(self.action_btn_next_screen)
            self.add_widget(self.action_btn_prev_screen)

    def on_undo(self, *args):
        pass

    def on_redo(self, *args):
        pass

    def on_cut(self, *args):
        pass

    def on_copy(self, *args):
        pass

    def on_paste(self, *args):
        pass

    def on_delete(self, *args):
        pass

    def on_selectall(self, *args):
        pass

    def on_next_screen(self, *args):
        pass

    def on_prev_screen(self, *args):
        pass

########NEW FILE########
__FILENAME__ = info_bubble
from kivy.uix.bubble import Bubble
from kivy.properties import StringProperty
from kivy.clock import Clock
from kivy.animation import Animation
from kivy.core.window import Window


class InfoBubble(Bubble):
    '''Bubble to be used to display short Help Information'''

    message = StringProperty('')
    '''Message to be displayed
       :data:`message` is a :class:`~kivy.properties.StringProperty`
    '''

    def show(self, pos, duration, width=None):
        '''Animate the bubble into position'''
        if width:
            self.width = width
        #wait for the bubble to adjust it's size according to text then animate
        Clock.schedule_once(lambda dt: self._show(pos, duration))

    def _show(self, pos, duration):
        '''To show Infobubble at pos with Animation of duration.
        '''
        def on_stop(*l):
            if duration:
                Clock.schedule_once(self.hide, duration + .5)

        self.opacity = 0
        arrow_pos = self.arrow_pos
        if arrow_pos[0] in ('l', 'r'):
            pos = pos[0], pos[1] - (self.height/2)
        else:
            pos = pos[0] - (self.width/2), pos[1]

        self.limit_to = Window
        self.pos = pos
        Window.add_widget(self)

        anim = Animation(opacity=1, d=0.75)
        anim.bind(on_complete=on_stop)
        anim.cancel_all(self)
        anim.start(self)

    def hide(self, *dt):
        ''' Auto fade out the Bubble
        '''
        def on_stop(*l):
            Window.remove_widget(self)
        anim = Animation(opacity=0, d=0.75)
        anim.bind(on_complete=on_stop)
        anim.cancel_all(self)
        anim.start(self)

########NEW FILE########
__FILENAME__ = kivy_console
# -*- coding: utf-8 -*-
'''
KivyConsole
===========

.. image:: images/KivyConsole.jpg
    :align: right

:class:`KivyConsole` is a :class:`~kivy.uix.widget.Widget`
Purpose: Providing a system console for debugging kivy by running another
instance of kivy in this console and displaying it's output.
To configure, you can use

cached_history  :
cached_commands :
font            :
font_size       :
shell           :

''Versionadded:: 1.0.?TODO

''Usage:
    from kivy.uix.kivyconsole import KivyConsole

    parent.add_widget(KivyConsole())

or

    console = KivyConsole()

To run a command:

    console.stdin.write('ls -l')

or
    subprocess.Popen(('echo','ls'), stdout = console.stdin)

To display something on stdout write to stdout

    console.stdout.write('this will be written to the stdout\n')

or
    subprocess.Popen('ps', stdout = console.stdout, shell = True)

Warning: To read from stdout remember that the process is run in a thread, give
it time to complete otherwise you might get a empty or partial string;
returning whatever has been written to the stdout pipe till the time
read() was called.

    text = console.stdout.read() or read(no_of_bytes) or readline()

TODO: create a stdin and stdout pipe for
      this console like in logger.[==== ]%done
TODO: move everything that is non-specific to
      a generic console in a different Project.[     ]%done
TODO: Fix Prompt, make it smaller plus give it more info

''Shortcuts:
Inside the console you can use the following shortcuts:
Shortcut                     Function
_________________________________________________________
PGup           Search for previous command inside command history
               starting with the text before current cursor position

PGdn           Search for Next command inside command history
               starting with the text before current cursor position

UpArrow        Replace command_line with previous command

DnArrow        Replace command_line with next command
               (only works if one is not at last command)

Tab            If there is nothing before the cursur when tab is pressed
                   contents of current directory will be displayed.
               '.' before cursur will be converted to './'
               '..' to '../'
               If there is a path before cursur position
                   contents of the path will be displayed.
               else contents of the path before cursor containing
                    the commands matching the text before cursur will
                    be displayed
'''

__all__ = ('KivyConsole', )

import shlex
import subprocess
import thread
import os
import sys
from functools import partial
from pygments.lexers import BashSessionLexer

from kivy.uix.gridlayout import GridLayout
from kivy.properties import (NumericProperty, StringProperty,
                             BooleanProperty, ObjectProperty, DictProperty,
                             AliasProperty, ListProperty)
from kivy.uix.button import Button
from kivy.uix.scrollview import ScrollView
from kivy.uix.textinput import TextInput
from kivy.clock import Clock
from kivy.lang import Builder
from kivy.app import App
from kivy.logger import Logger
from kivy.core.window import Window
from kivy.utils import platform


Builder.load_string('''
<KivyConsole>:
    cols:1
    txtinput_history_box: history_box.__self__
    txtinput_command_line: command_line.__self__
    ScrollView:
        CodeInput:
            id: history_box
            size_hint: (1, None)
            height: 801
            font_name: root.font_name
            font_size: root.font_size
            readonly: True
            foreground_color: root.foreground_color
            background_color: root.background_color
            on_text: root.on_text(*args)
    TextInput:
        id: command_line
        multiline: False
        size_hint: (1, None)
        font_name: root.font_name
        font_size: root.font_size
        readonly: root.readonly
        foreground_color: root.foreground_color
        background_color: root.background_color
        height: 36
        on_text_validate: root.on_enter(*args)
        on_touch_up:
            self.collide_point(*args[1].pos)\\
            and root._move_cursor_to_end(self)
''')


class KivyConsole(GridLayout):
    '''This is a Console widget used for debugging and running external
    commands

    '''

    readonly = BooleanProperty(False)
    '''This defines weather a person can enter commands in the console

    :data:`readonly` is an :class:`~kivy.properties.BooleanProperty`,
    Default to 'False'
    '''

    foreground_color = ListProperty((.5, .5, .5, .93))
    '''This defines the color of the text in the console

    :data:`foreground_color` is an :class:`~kivy.properties.ListProperty`,
    Default to '(.5, .5, .5, .93)'
    '''

    background_color = ListProperty((0, 0, 0, 1))
    '''This defines the color of the text in the console

    :data:`foreground_color` is an :class:`~kivy.properties.ListProperty`,
    Default to '(0, 0, 0, 1)'
    '''

    cached_history = NumericProperty(200)
    '''Indicates the No. of lines to cache. Defaults to 200

    :data:`cached_history` is an :class:`~kivy.properties.NumericProperty`,
    Default to '200'
    '''

    cached_commands = NumericProperty(90)
    '''Indicates the no of commands to cache. Defaults to 90

    :data:`cached_commands` is a :class:`~kivy.properties.NumericProperty`,
    Default to '90'
    '''
    font_name = StringProperty('data/fonts/DroidSansMono.ttf')
    '''Indicates the font Style used in the console

    :data:`font` is a :class:`~kivy.properties.StringProperty`,
    Default to 'DroidSansMono'
    '''

    environment = DictProperty(os.environ.copy())
    '''Indicates the environment the commands are run in. Set your PATH or
    other environment variables here. like so::

        kivy_console.environment['PATH']='path'

    environment is :class:`~kivy.properties.DictProperty`, defaults to
    the environment for the pricess running Kivy console
    '''

    font_size = NumericProperty(14)
    '''Indicates the size of the font used for the console

    :data:`font_size` is a :class:`~kivy.properties.NumericProperty`,
    Default to '9'
    '''

    textcache = ListProperty(['', ])
    '''Indicates the cache of the commands and their output

    :data:`textcache` is a :class:`~kivy.properties.ListProperty`,
    Default to ''
    '''

    shell = BooleanProperty(False)
    '''Indicates the weather system shell is used to run the commands

    :data:`shell` is a :class:`~kivy.properties.BooleanProperty`,
    Default to 'False'

    WARNING: Shell = True is a security risk and therefore = False by default,
    As a result with shell = False some shell specific commands and
    redirections
    like 'ls |grep lte' or dir >output.txt will not work.
    If for some reason you need to run such commands, try running the platform
    shell first
    eg:  /bin/sh ...etc on nix platforms and cmd.exe on windows.
    As the ability to interact with the running command is built in,
    you should be able to interact with the native shell.

    Shell = True, should be set only if absolutely necessary.
    '''

    txtinput_command_line = ObjectProperty(None)

    def __init__(self, **kwargs):
        self.register_event_type('on_subprocess_done')
        super(KivyConsole, self).__init__(**kwargs)
        #initialisations
        self.txtinput_command_line_refocus = False
        self.txtinput_run_command_refocus = False
        self.win = None
        self.scheduled = False
        self.command_history = []
        self.command_history_pos = 0
        self.command_status = 'closed'
        self.cur_dir = os.getcwdu()
        self.stdout = std_in_out(self, 'stdout')
        self.stdin = std_in_out(self, 'stdin')
        #self.stderror = stderror(self)
        # delayed initialisation
        Clock.schedule_once(self._initialize)
        self_change_txtcache = self._change_txtcache
        _trig = Clock.create_trigger(self_change_txtcache)
        self.bind(textcache=_trig)

    def clear(self, *args):
        self.txtinput_history_box.text = ''
        self.textcache = ['', ]

    def _initialize(self, dt):
        cl = self.txtinput_command_line
        self.txtinput_history_box.lexer = BashSessionLexer()
        self.txtinput_history_box.text = u''.join(self.textcache)
        self.txtinput_command_line.text = self.prompt()
        self.txtinput_command_line.bind(focus=self.on_focus)
        Clock.schedule_once(self._change_txtcache)
        self._focus(self.txtinput_command_line)
        self._list = [self.txtinput_command_line]

    def _move_cursor_to_end(self, instance):
        def mte(*l):
            instance.cursor = instance.get_cursor_from_index(len_prompt)
        len_prompt = len(self.prompt())
        if instance.cursor[0] < len_prompt:
            Clock.schedule_once(mte, -1)

    def _focus(self, widg, t_f=True):
        Clock.schedule_once(partial(self._deffered_focus, widg, t_f))

    def _deffered_focus(self, widg, t_f, dt):
        if widg.get_root_window():
            widg.focus = t_f

    def prompt(self, *args):
        _platform = ''
        if hasattr(os, 'uname'):
            _platform = os.uname()
        else:
            _platform = os.environ.get('COMPUTERNAME')
        return "[%s@%s %s]>> " % (
            os.environ.get('USERNAME', 'UNKNOWN'), _platform[1],
            os.path.basename(str(self.cur_dir)))

    def _change_txtcache(self, *args):
        tihb = self.txtinput_history_box
        tihb.text = ''.join(self.textcache)
        if not self.get_root_window():
            return
        tihb.height = max(tihb.minimum_height, tihb.parent.height)
        tihb.parent.scroll_y = 0

    def on_text(self, instance, txt):
        # check if history_box has more text than indicated buy
        # self.cached_history and remove excess lines from top
        if txt == '':
            return
        try:
            #self._skip_textcache = True
            self.textcache = self.textcache[-self.cached_history:]
        except IndexError:
            pass
            #self._skip_textcache = False

    def on_keyboard(self, *l):
        ticl = self.txtinput_command_line

        def move_cursor_to(col):
            ticl.cursor =\
                col, ticl.cursor[1]

        def search_history(up_dn):
            if up_dn == 'up':
                plus_minus = -1
            else:
                plus_minus = 1
            l_curdir = len(self.prompt())
            col = ticl.cursor_col
            command = ticl.text[l_curdir: col]
            max_len = len(self.command_history) - 1
            chp = self.command_history_pos

            while max_len >= 0:
                if plus_minus == 1:
                    if self.command_history_pos > max_len - 1:
                        self.command_history_pos = max_len
                        return
                else:
                    if self.command_history_pos <= 0:
                        self.command_history_pos = max_len
                        return
                self.command_history_pos = self.command_history_pos\
                    + plus_minus
                cmd = self.command_history[self.command_history_pos]
                if cmd[:len(command)] == command:
                    ticl.text = u''.join((
                        self.prompt(), cmd))
                    move_cursor_to(col)
                    return
            self.command_history_pos = max_len + 1

        if ticl.focus:
            if l[1] == 273:
                # up arrow: display previous command
                if self.command_history_pos > 0:
                    self.command_history_pos = self.command_history_pos - 1
                    ticl.text = u''.join(
                        (self.prompt(),
                         self.command_history[self.command_history_pos]))
                return
            if l[1] == 274:
                # dn arrow: display next command
                if self.command_history_pos < len(self.command_history) - 1:
                    self.command_history_pos = self.command_history_pos + 1
                    ticl.text = u''.join(
                        (self.prompt(),
                         self.command_history[self.command_history_pos]))
                else:
                    self.command_history_pos = len(self.command_history)
                    ticl.text = self.prompt()
                col = len(ticl.text)
                move_cursor_to(col)
                return
            if l[1] == 9:
                # tab: autocomplete
                def display_dir(cur_dir, starts_with=None):
                    # display contents of dir from cur_dir variable
                    starts_with_is_not_None = starts_with is not None
                    try:
                        dir_list = os.listdir(cur_dir)
                    except OSError, err:
                        self.add_to_cache(u''.join((err.strerror, '\n')))
                        return
                    if starts_with_is_not_None:
                        len_starts_with = len(starts_with)
                    self.add_to_cache(u''.join(('contents of directory: ',
                                                cur_dir, '\n')))
                    txt = u''
                    no_of_matches = 0

                    for _file in dir_list:
                        if starts_with_is_not_None:
                            if _file[:len_starts_with] == starts_with:
                                # if file matches starts with
                                txt = u''.join((txt, _file, ' '))
                                no_of_matches += 1
                        else:
                            self.add_to_cache(u''.join((_file, '\t')))
                    if no_of_matches == 1:
                        len_txt = len(txt) - 1
                        cmdl_text = ticl.text
                        len_cmdl = len(cmdl_text)
                        os_sep = os.sep \
                            if col == len_cmdl or (col < len_cmdl and
                                                   cmdl_text[col] !=
                                                   os.sep) else ''
                        ticl.text = u''.join(
                            (self.prompt(), text_before_cursor,
                             txt[len_starts_with:len_txt], os_sep,
                             cmdl_text[col:]))
                        move_cursor_to(col + (len_txt - len_starts_with) + 1)
                    elif no_of_matches > 1:
                        self.add_to_cache(txt)
                    self.add_to_cache('\n')

                # send back space to command line -remove the tab
                ticl.do_backspace()
                ntext = os.path.expandvars(ticl.text)
                # store text before cursor for comparison
                l_curdir = len(self.prompt())
                col = ticl.cursor_col
                if ntext != ticl.text:
                    ticl.text = ntext
                    col = len(ntext)
                text_before_cursor = ticl.text[l_curdir: col]

                # if empty or space before: list cur dir
                if text_before_cursor == ''\
                   or ticl.text[col - 1] == ' ':
                    display_dir(self.cur_dir)
                # if in mid command:
                else:
                    # list commands in PATH starting with text before cursor
                    # split command into path till the seperator
                    cmd_start = text_before_cursor.rfind(' ')
                    cmd_start += 1
                    cur_dir = self.cur_dir\
                        if text_before_cursor[cmd_start] != os.sep\
                        else os.sep
                    os_sep = os.sep if cur_dir != os.sep else ''
                    cmd_end = text_before_cursor.rfind(os.sep)
                    len_txt_bef_cur = len(text_before_cursor) - 1
                    if cmd_end == len_txt_bef_cur:
                        # display files in path
                        if text_before_cursor[cmd_start] == os.sep:
                            cmd_start += 1
                        display_dir(u''.join((cur_dir, os_sep,
                                    text_before_cursor[cmd_start:cmd_end])))
                    elif text_before_cursor[len_txt_bef_cur] == '.':
                        # if / already there return
                        if len(ticl.text) > col\
                           and ticl.text[col] == os.sep:
                            return
                        if text_before_cursor[len_txt_bef_cur - 1] == '.':
                            len_txt_bef_cur -= 1
                        if text_before_cursor[len_txt_bef_cur - 1]\
                           not in (' ', os.sep):
                            return
                        # insert at cursor os.sep: / or \
                        ticl.text = u''.join((self.prompt(),
                                              text_before_cursor, os_sep,
                                              ticl.text[col:]))
                    else:
                        if cmd_end < 0:
                            cmd_end = cmd_start
                        else:
                            cmd_end += 1
                        display_dir(u''.join((
                                    cur_dir,
                                    os_sep,
                                    text_before_cursor[cmd_start:cmd_end])),
                                    text_before_cursor[cmd_end:])
                return
            if l[1] == 280:
                # pgup: search last command starting with...
                search_history('up')
                return
            if l[1] == 281:
                # pgdn: search next command starting with...
                search_history('dn')
                return
            if l[1] == 278:
                # Home: cursor should not go to the left of cur_dir
                col = len(self.prompt())
                move_cursor_to(col)
                if len(l[4]) > 0 and l[4][0] == 'shift':
                    ticl.selection_to = col
                return
            if l[1] == 276 or l[1] == 8:
                # left arrow/bkspc: cursor should not go left of cur_dir
                col = len(self.prompt())
                if ticl.cursor_col < col:
                    if l[1] == 8:
                        ticl.text = self.prompt()
                    move_cursor_to(col)
                return

    def on_focus(self, instance, value):
        if value:
            # focused
            if instance is self.txtinput_command_line:
                Window.unbind(on_keyboard=self.on_keyboard)
                Window.bind(on_keyboard=self.on_keyboard)
        else:
            # defocused
            if self.txtinput_command_line_refocus:
                self.txtinput_command_line_refocus = False
                if self.txtinput_command_line.get_root_window():
                    self.txtinput_command_line.focus = True
                self.txtinput_command_line.scroll_x = 0
            if self.txtinput_run_command_refocus:
                self.txtinput_run_command_refocus = False
                instance.focus = True
                instance.scroll_x = 0
                instance.text = u''

    def add_to_cache(self, _string):
        #os.write(self.stdout.stdout_pipe, _string.encode('utf-8'))
        #self.stdout.flush()
        self.textcache.append(_string)
        _string = None

    def on_enter(self, *l):
        txtinput_command_line = self.txtinput_command_line
        add_to_cache = self.add_to_cache
        command_history = self.command_history

        def remove_command_interaction_widgets(*l):
            #command finished:remove widget responsible for interaction with it
            parent.remove_widget(self.interact_layout)
            self.interact_layout = None
            # enable running a new command
            try:
                parent.add_widget(self.txtinput_command_line)
            except:
                self._initialize(0)

            self._focus(txtinput_command_line, True)
            Clock.schedule_once(self._change_txtcache, .1)
            self.dispatch('on_subprocess_done')

        def run_cmd(*l):
            # this is run inside a thread so take care, avoid gui ops
            try:
                comand = command.encode('utf-8')
                _posix = True
                if sys.platform[0] == 'w':
                    _posix = False
                cmd = shlex.split(str(command), posix=_posix)\
                    if not self.shell else command
            except Exception as err:
                cmd = ''
                self.add_to_cache(u''.join((str(err), ' <', command, ' >\n')))
            if len(cmd) > 0:
                prev_stdout = sys.stdout
                sys.stdout = self.stdout
                Clock_schedule_once = Clock.schedule_once
                try:
                    #execute command
                    self.popen_obj = popen = subprocess.Popen(
                        cmd,
                        bufsize=0,
                        stdout=subprocess.PIPE,
                        stdin=subprocess.PIPE,
                        stderr=subprocess.STDOUT,
                        preexec_fn=None,
                        close_fds=False,
                        shell=self.shell,
                        cwd=self.cur_dir,
                        env=self.environment,
                        universal_newlines=False,
                        startupinfo=None,
                        creationflags=0)
                    popen_stdout_r = popen.stdout.readline
                    popen_stdout_flush = popen.stdout.flush
                    txt = popen_stdout_r()
                    plat = platform()
                    while txt != '':
                        # skip flush on android
                        if plat[0] != 'a':
                            popen_stdout_flush()
                        add_to_cache(txt.decode('utf8'))
                        txt = popen_stdout_r()
                except OSError or ValueError, err:
                    add_to_cache(u''.join((str(err.strerror),
                                           ' < ', command, ' >\n')))
                sys.stdout = prev_stdout
            self.popen_obj = None
            Clock.schedule_once(remove_command_interaction_widgets)
            self.command_status = 'closed'

        # append text to textcache
        add_to_cache(u''.join((self.txtinput_command_line.text, '\n')))
        command = txtinput_command_line.text[len(self.prompt()):]

        if command == '':
            self.txtinput_command_line_refocus = True
            return

        # store command in command_history
        if self.command_history_pos > 0:
            self.command_history_pos = len(command_history)
            if command_history[self.command_history_pos - 1] != command:
                command_history.append(command)
        else:
            command_history.append(command)

        len_command_history = len(command_history)
        self.command_history_pos = len(command_history)

        # on reaching limit(cached_lines) pop first command
        if len_command_history >= self.cached_commands:
            self.command_history = command_history[1:]

        # replce $PATH with
        command = os.path.expandvars(command)

        # if command = cd change directory
        if command.startswith('cd ') or command.startswith('export '):
            if command[0] == 'e':
                e_q = command[7:].find('=')
                _exprt = command[7:]
                if e_q:
                    os.environ[_exprt[:e_q]] = _exprt[e_q + 1:]
                    self.environment = os.environ.copy()
            else:
                try:
                    if command[3] == os.sep:
                        os.chdir(command[3:])
                    else:
                        os.chdir(self.cur_dir + os.sep + command[3:])
                    self.cur_dir = os.getcwdu()
                except OSError, err:
                    Logger.debug('Shell Console: err:' + err.strerror +
                                 ' directory:' + command[3:])
                    add_to_cache(u''.join((err.strerror, '\n')))
            add_to_cache(u''.join((txtinput_command_line.text, '\n')))
            txtinput_command_line.text = self.prompt()
            self.txtinput_command_line_refocus = True
            return

        txtinput_command_line.text = self.prompt()
        # store output in textcache
        parent = txtinput_command_line.parent
        # disable running a new command while and old one is running
        parent.remove_widget(txtinput_command_line)
        # add widget for interaction with the running command
        txtinput_run_command = TextInput(multiline=False,
                                         font_size=self.font_size,
                                         font_name=self.font_name)

        def interact_with_command(*l):
            popen_obj = self.popen_obj
            if not popen_obj:
                return
            txt = l[0].text + u'\n'
            popen_obj_stdin = popen_obj.stdin
            popen_obj_stdin.write(txt.encode('utf-8'))
            popen_obj_stdin.flush()
            self.txtinput_run_command_refocus = True

        self.txtinput_run_command_refocus = False
        txtinput_run_command.bind(on_text_validate=interact_with_command)
        txtinput_run_command.bind(focus=self.on_focus)
        btn_kill = Button(text="kill",
                          width=27,
                          size_hint=(None, 1))

        def kill_process(*l):
            self.popen_obj.kill()

        self.interact_layout = il = GridLayout(rows=1, cols=2, height=27,
                                               size_hint=(1, None))
        btn_kill.bind(on_press=kill_process)
        il.add_widget(txtinput_run_command)
        il.add_widget(btn_kill)
        parent.add_widget(il)

        txtinput_run_command.focus = True
        self.command_status = 'started'
        thread.start_new_thread(run_cmd, ())

    def on_subprocess_done(self, *args):
        pass


class std_in_out(object):
    ''' class for writing to/reading from this console'''

    def __init__(self, obj, mode='stdout'):
        self.obj = obj
        self.mode = mode
        self.stdin_pipe, self.stdout_pipe = os.pipe()
        thread.start_new_thread(self.read_from_in_pipe, ())
        self.textcache = None

    def update_cache(self, text_line, obj, *l):
        obj.textcache.append(text_line.decode('utf-8'))

    def read_from_in_pipe(self, *l):
        txt = '\n'
        txt_line = ''
        os_read = os.read
        self_stdin_pipe = self.stdin_pipe
        self_mode = self.mode
        self_write = self.write
        Clock_schedule_once = Clock.schedule_once
        self_update_cache = self.update_cache
        self_flush = self.flush
        obj = self.obj
        try:
            while txt != '':
                txt = os_read(self_stdin_pipe, 1)
                txt_line = u''.join((txt_line, txt))
                if txt == '\n':
                    if self_mode == 'stdin':
                        # run command
                        self_write(txt_line)
                    else:
                        Clock_schedule_once(
                            partial(self_update_cache, txt_line, obj), 0)
                        self_flush()
                    txt_line = ''
        except OSError, e:
            Logger.exception(e)

    def close(self):
        os.close(self.stdin_pipe)
        os.close(self.stdout_pipe)

    def __del__(self):
        self.close()

    def fileno(self):
        return self.stdout_pipe

    def write(self, s):
        Logger.debug('write called with command:' + str(s))
        if self.mode == 'stdout':
            self.obj.add_to_cache(s)
            self.flush()
        else:
            # process.stdout.write ...run command
            if self.mode == 'stdin':
                self.obj.txtinput_command_line.text = ''.join((
                    self.obj.prompt(), s))
                self.obj.on_enter()

    def read(self, no_of_bytes=0):
        if self.mode == 'stdin':
            # stdin.read
            Logger.exception('KivyConsole: can not read from a stdin pipe')
            return
        # process.stdout/in.read
        txtc = self.textcache
        if no_of_bytes == 0:
            # return all data
            if txtc is None:
                self.flush()
            while self.obj.command_status != 'closed':
                pass
            txtc = self.textcache
            return txtc
        try:
            self.textcache = txtc[no_of_bytes:]
        except IndexError:
            self.textcache = txtc
        return txtc[:no_of_bytes]

    def readline(self):
        if self.mode == 'stdin':
            # stdin.readline
            Logger.exception('KivyConsole: can not read from a stdin pipe')
            return
        else:
            # process.stdout.readline
            if self.textcache is None:
                self.flush()
            txt = self.textcache
            x = txt.find('\n')
            if x < 0:
                Logger.Debug('console_shell: no more data')
                return
            self.textcache = txt[x:]
            ###self. write to ...
            return txt[:x]

    def flush(self):
        self.textcache = u''.join(self.obj.textcache)
        return

########NEW FILE########
__FILENAME__ = kv_lang_area
import re

from kivy.uix.codeinput import CodeInput
from kivy.properties import BooleanProperty, StringProperty,\
    NumericProperty, OptionProperty, ObjectProperty
from kivy.app import App
from kivy.lang import Builder
from kivy.factory import Factory
from kivy.clock import Clock
from kivy.uix.carousel import Carousel
from kivy.uix.screenmanager import ScreenManager
from kivy.uix.tabbedpanel import TabbedPanelContent, \
    TabbedPanel, TabbedPanelHeader

from designer.helper_functions import get_indent_str, get_line_end_pos,\
    get_line_start_pos, get_indent_level, get_indentation
from designer.uix.designer_code_input import DesignerCodeInput


class KVLangArea(DesignerCodeInput):
    '''KVLangArea is the CodeInput for editing kv lang. It emits on_show_edit
       event, when clicked.
    '''

    have_error = BooleanProperty(False)
    '''This property specifies whether KVLangArea has encountered an error
       in reload in the edited text by user or not.
       :data:`can_place` is a :class:`~kivy.properties.BooleanProperty`
    '''

    _reload = BooleanProperty(False)
    '''Specifies whether to reload kv or not.
       :data:`_reload` is a :class:`~kivy.properties.BooleanProperty`
    '''

    reload_kv = BooleanProperty(True)

    playground = ObjectProperty()
    '''Reference to :class:`~designer.playground.Playground`
       :data:`playground` is a :class:`~kivy.properties.ObjectProperty`
    '''

    project_loader = ObjectProperty()
    '''Reference to :class:`~designer.project_loader.ProjectLoader`
       :data:`project_loader` is a :class:`~kivy.properties.ObjectProperty`
    '''
    statusbar = ObjectProperty()

    def __init__(self, **kwargs):
        super(KVLangArea, self).__init__(**kwargs)
        self._reload_trigger = Clock.create_trigger(self.func_reload_kv, 1)
        self.bind(text=self._reload_trigger)

    def _get_widget_path(self, widget):
        '''To get path of a widget, path of a widget is a list containing
           the index of it in its parent's children list. For example,
           Widget1:
               Widget2:
               Widget3:
                   Widget4:

           path of Widget4 is [0, 1, 0]
        '''

        path_to_widget = []
        _widget = widget
        while _widget and _widget != self.playground.sandbox.children[0]:
            if not _widget.parent:
                break

            if isinstance(_widget.parent.parent, Carousel):
                parent = _widget.parent
                try:
                    place = parent.parent.slides.index(_widget)

                except ValueError:
                    place = 0

                path_to_widget.append(place)
                _widget = _widget.parent.parent

            elif isinstance(_widget.parent, ScreenManager):
                parent = _widget.parent
                try:
                    place = parent.screens.index(_widget)

                except ValueError:
                    place = 0

                path_to_widget.append(place)
                _widget = _widget.parent

            elif isinstance(_widget.parent, TabbedPanelContent):
                tab_panel = _widget.parent.parent
                path_to_widget.append(0)
                place = len(tab_panel.tab_list) - \
                    tab_panel.tab_list.index(tab_panel.current_tab) - 1

                path_to_widget.append(place)
                _widget = tab_panel

            elif isinstance(_widget, TabbedPanelHeader):
                tab_panel = _widget.parent
                while tab_panel and not isinstance(tab_panel, TabbedPanel):
                    tab_panel = tab_panel.parent

                place = len(tab_panel.tab_list) - \
                    tab_panel.tab_list.index(_widget) - 1

                path_to_widget.append(place)
                _widget = tab_panel

            else:
                place = len(_widget.parent.children) - \
                    _widget.parent.children.index(_widget) - 1

                path_to_widget.append(place)
                _widget = _widget.parent

        return path_to_widget

    def shift_widget(self, widget, from_index):
        '''This function will shift widget's kv str from one position
           to another.
        '''
        self._reload = False

        path = self._get_widget_path(widget)
        path.reverse()
        prev_path = [x for x in path]
        prev_path[-1] = len(widget.parent.children) - from_index - 1
        start_pos, end_pos = self.get_widget_text_pos_from_kv(widget,
                                                              widget.parent,
                                                              path_to_widget=
                                                              prev_path)
        widget_text = self.text[start_pos:end_pos]

        if widget.parent.children.index(widget) == 0:
            self.text = self.text[:start_pos] + self.text[end_pos:]
            self.add_widget_to_parent(widget, widget.parent,
                                      kv_str=widget_text)

        else:
            self.text = self.text[:start_pos] + self.text[end_pos:]
            text = re.sub(r'#.+', '', self.text)
            lines = text.splitlines()
            total_lines = len(lines)
            root_lineno = 0
            root_name = self.project_loader.root_rule.name
            for lineno, line in enumerate(lines):
                pos = line.find(root_name)
                if pos != -1 and get_indentation(line) == 0:
                    root_lineno = lineno
                    break

            next_widget_path = path
            lineno = self._find_widget_place(next_widget_path, lines,
                                             total_lines,
                                             root_lineno + 1)

            self.cursor = (0, lineno)
            self.insert_text(widget_text+'\n')

    def add_widget_to_parent(self, widget, target, kv_str=''):
        '''This function is called when widget is added to target.
           It will search for line where parent is defined in text and will add
           widget there.
        '''
        text = re.sub(r'#.+', '', self.text)
        lines = text.splitlines()
        total_lines = len(lines)
        if total_lines == 0:
            return

        self._reload = False

        #If target is not none then widget is not root widget
        if target:
            path_to_widget = self._get_widget_path(target)

            path_to_widget.reverse()

            root_lineno = 0
            root_name = self.project_loader.root_rule.name
            for lineno, line in enumerate(lines):
                pos = line.find(root_name)
                if pos != -1 and get_indentation(line) == 0:
                    root_lineno = lineno
                    break

            parent_lineno = self._find_widget_place(path_to_widget, lines,
                                                    total_lines,
                                                    root_lineno + 1)

            if parent_lineno >= total_lines:
                return

            #Get text of parents line
            parent_line = lines[parent_lineno]
            if not parent_line.strip():
                return

            insert_after_line = -1

            if parent_line.find(':') == -1:
                #If parent_line doesn't contain ':' then insert it
                #Also insert widget's rule after its properties
                insert_after_line = parent_lineno
                _line = 0
                _line_pos = -1
                _line_pos = self.text.find('\n', _line_pos + 1)

                while _line <= insert_after_line:
                    _line_pos = self.text.find('\n', _line_pos + 1)
                    _line += 1

                self.text = self.text[:_line_pos] + ':' + self.text[_line_pos:]
                indent = len(parent_line) - len(parent_line.lstrip())

            else:
                #If ':' in parent_line then,
                #find a place to insert widget's rule
                indent = len(parent_line) - len(parent_line.lstrip())
                lineno = parent_lineno
                _indent = indent + 1
                line = parent_line
                while (line.strip() == '' or _indent > indent):
                    lineno += 1
                    if lineno >= total_lines:
                        break
                    line = lines[lineno]
                    _indent = len(line) - len(line.lstrip())

                insert_after_line = lineno - 1
                line = lines[insert_after_line]
                while line.strip() == '':
                    insert_after_line -= 1
                    line = lines[insert_after_line]

            to_insert = ''
            if kv_str == '':
                to_insert = type(widget).__name__ + ':'
            else:
                to_insert = kv_str.strip()

            if insert_after_line == total_lines - 1:
                #if inserting at the last line
                _line_pos = len(self.text) - 1

                self.text = self.text[:_line_pos + 1] + '\n' + \
                    get_indent_str(indent + 4) + to_insert
            else:
                #inserting somewhere else
                insert_after_line -= 1
                _line = 0
                _line_pos = -1
                _line_pos = self.text.find('\n', _line_pos + 1)
                while _line <= insert_after_line:
                    _line_pos = self.text.find('\n', _line_pos + 1)
                    _line += 1

                self.text = self.text[:_line_pos] + '\n' + \
                    get_indent_str(indent + 4) + to_insert + \
                    self.text[_line_pos:]

        else:
            #widget is a root widget
            parent_lineno = 0
            self.cursor = (0, 0)
            type_name = type(widget).__name__
            is_class = False
            for rule in self.project_loader.class_rules:
                if rule.name == type_name:
                    is_class = True
                    break

            if not is_class:
                self.insert_text(type_name+':\n')

            self.project_loader.set_root_widget(type_name, widget)

    def get_widget_text_pos_from_kv(self, widget, parent, path_to_widget=[]):
        '''To get start and end pos of widget's rule in kv text
        '''

        if not path_to_widget:
            path_to_widget = self._get_widget_path(widget)
            path_to_widget.reverse()

        #Go to widget's rule's line and determines all its rule's
        #and it's child if any. Then delete them
        text = re.sub(r'#.+', '', self.text)
        lines = text.splitlines()
        total_lines = len(lines)
        root_lineno = 0
        root_name = self.project_loader.root_rule.name
        for lineno, line in enumerate(lines):
            pos = line.find(root_name)
            if pos != -1 and get_indentation(line) == 0:
                root_lineno = lineno
                break

        widget_lineno = self._find_widget_place(path_to_widget, lines,
                                                total_lines, root_lineno + 1)
        widget_line = lines[widget_lineno]
        indent = len(widget_line) - len(widget_line.lstrip())
        lineno = widget_lineno
        _indent = indent + 1
        line = widget_line
        while (line.strip() == '' or _indent > indent):
            lineno += 1
            if lineno >= total_lines:
                break
            line = lines[lineno]
            _indent = len(line) - len(line.lstrip())

        delete_until_line = lineno - 1
        line = lines[delete_until_line]
        while line.strip() == '':
            delete_until_line -= 1
            line = lines[delete_until_line]

        widget_line_pos = get_line_start_pos(self.text, widget_lineno)
        delete_until_line_pos = -1
        if delete_until_line == total_lines - 1:
            delete_until_line_pos = len(self.text)
        else:
            delete_until_line_pos = get_line_end_pos(self.text,
                                                     delete_until_line)

        self._reload = False

        return widget_line_pos, delete_until_line_pos

    def get_widget_text_from_kv(self, widget, parent, path=[]):
        '''This function will get a widget's text from KVLangArea's text given
           its parent.
        '''

        start_pos, end_pos = self.get_widget_text_pos_from_kv(
            widget, parent, path_to_widget=path)
        text = self.text[start_pos:end_pos]

        return text

    def remove_widget_from_parent(self, widget, parent):
        '''This function is called when widget is removed from parent.
           It will delete widget's rule from parent's rule
        '''
        if self.text == '':
            return

        self._reload = False

        delete_from_kv = False
        if type(widget).__name__ == self.project_loader.root_rule.name:
            #If root widget is being deleted then delete its rule only if
            #it is not in class rules.

            if not self.project_loader.is_root_a_class_rule():
                delete_from_kv = True

        else:
            delete_from_kv = True

        if delete_from_kv:
            start_pos, end_pos = self.get_widget_text_pos_from_kv(widget,
                                                                  parent)
            text = self.text[start_pos:end_pos]
            self.text = self.text[:start_pos] + self.text[end_pos:]
            return text

    def _get_widget_from_path(self, path):
        '''This function is used to get widget given its path
        '''

        if not self.playground.root:
            return None

        if len(path) == 0:
            return None

        root = self.playground.root
        path_index = 0
        widget = root
        path_length = len(path)

        while widget.children != [] and path_index < path_length:
            try:
                widget = widget.children[len(widget.children) -
                                         1 - path[path_index]]
            except IndexError:
                widget = widget.children[0]

            path_index += 1

        return widget

    def func_reload_kv(self, *args):
        if not self.reload_kv:
            return

        if self.text == '':
            return

        if not self._reload:
            self._reload = True
            return

        statusbar = self.statusbar

        playground = self.playground
        project_loader = self.project_loader

        try:
            widget = project_loader.reload_from_str(self.text)

            if widget:
                playground.remove_widget_from_parent(playground.root,
                                                     None, from_kv=True)
                playground.add_widget_to_parent(widget, None, from_kv=True)

            statusbar.show_message("")
            self.have_error = False

        except:
            self.have_error = True
            statusbar.show_message("Cannot reload from text")

    def _get_widget_path_at_line(self, lineno, root_lineno=0):
        '''To get widget path of widget at line
        '''

        if self.text == '':
            return []

        text = self.text
        #Remove all comments
        text = re.sub(r'#.+', '', text)

        lines = text.splitlines()
        line = lines[lineno]

        #Search for the line containing widget's name
        _lineno = lineno

        while line.find(':') != -1 and \
                line.strip().find(':') != len(line.strip()) - 1:
            lineno -= 1
            line = lines[lineno]

        path = []
        child_count = 0
        #From current line go above and
        #fill number of children above widget's rule
        while _lineno >= root_lineno and lines[_lineno].strip() != "" and \
                get_indentation(lines[lineno]) != 0:
            _lineno = lineno - 1
            diff_indent = get_indentation(lines[lineno]) - \
                get_indentation(lines[_lineno])

            while _lineno >= root_lineno and (lines[_lineno].strip() == ''
                                              or diff_indent <= 0):
                if lines[_lineno].strip() != '' and diff_indent == 0 and \
                    'canvas' not in lines[_lineno] and \
                        (lines[_lineno].find(':') == -1 or
                         lines[_lineno].find(':') ==
                         len(lines[_lineno].rstrip()) - 1):
                    child_count += 1

                _lineno -= 1
                diff_indent = get_indentation(lines[lineno]) - \
                    get_indentation(lines[_lineno])

            lineno = _lineno

            if _lineno > root_lineno:
                _lineno += 1

            if 'canvas' not in lines[_lineno] and \
                    lines[_lineno].strip().find(':') == \
                    len(lines[_lineno].strip()) - 1:

                path.insert(0, child_count)
                child_count = 0

        return path

    def get_property_value(self, widget, prop):
        self._reload = False
        if prop[:3] != 'on_' and \
                not isinstance(widget.properties()[prop], StringProperty) and\
                value == '':
            return

        path_to_widget = self._get_widget_path(widget)
        path_to_widget.reverse()

        #Go to the line where widget is declared
        lines = re.sub(r'#.+', '', self.text).splitlines()
        total_lines = len(lines)

        root_name = self.project_loader.root_rule.name
        total_lines = len(lines)
        root_lineno = 0
        for lineno, line in enumerate(lines):
            pos = line.find(root_name)
            if pos != -1 and get_indentation(line) == 0:
                root_lineno = lineno
                break

        widget_lineno = self._find_widget_place(path_to_widget, lines,
                                                total_lines, root_lineno+1)
        widget_line = lines[widget_lineno]
        indent = get_indentation(widget_line)
        prop_found = False

        #Else find if property has already been declared with a value
        lineno = widget_lineno + 1
        #But if widget line is the last line in the text
        if lineno < total_lines:
            line = lines[lineno]
            _indent = get_indentation(line)
            colon_pos = -1
            while lineno < total_lines and (line.strip() == '' or
                                            _indent > indent):
                line = lines[lineno]
                _indent = get_indentation(line)
                if line.strip() != '':
                    colon_pos = line.find(':')
                    if colon_pos == -1:
                        break

                    if colon_pos == len(line.rstrip()) - 1:
                        break

                    if prop == line[:colon_pos].strip():
                        prop_found = True
                        break

                lineno += 1

        if prop_found:
            #if property found then change its value
            _pos_prop_value = get_line_start_pos(self.text, lineno) + \
                colon_pos + 2
            if lineno == total_lines - 1:
                _line_end_pos = len(self.text)
            else:
                _line_end_pos = get_line_end_pos(self.text, lineno)

            return self.text[_pos_prop_value:_line_end_pos]

        return ""

    def set_event_handler(self, widget, prop, value):
        self._reload = False

        path_to_widget = self._get_widget_path(widget)
        path_to_widget.reverse()

        #Go to the line where widget is declared
        lines = re.sub(r'#.+', '', self.text).splitlines()
        total_lines = len(lines)

        root_name = self.project_loader.root_rule.name
        total_lines = len(lines)
        root_lineno = 0
        for lineno, line in enumerate(lines):
            pos = line.find(root_name)
            if pos != -1 and get_indentation(line) == 0:
                root_lineno = lineno
                break

        widget_lineno = self._find_widget_place(path_to_widget, lines,
                                                total_lines, root_lineno+1)

        widget_line = lines[widget_lineno]
        indent = get_indentation(widget_line)
        prop_found = False

        if not widget_line.strip():
            return

        if ':' not in widget_line:
            #If cannot find ':' then insert it
            self.cursor = (len(lines[widget_lineno]), widget_lineno)
            lines[widget_lineno] += ':'
            self.insert_text(':')

        else:
            #Else find if property has already been declared with a value
            lineno = widget_lineno + 1
            #But if widget line is the last line in the text
            if lineno < total_lines:
                line = lines[lineno]
                _indent = get_indentation(line)
                colon_pos = -1
                while lineno < total_lines and (line.strip() == '' or
                                                _indent > indent):
                    line = lines[lineno]
                    _indent = get_indentation(line)
                    if line.strip() != '':
                        colon_pos = line.find(':')
                        if colon_pos == -1:
                            break

                        if colon_pos == len(line.rstrip()) - 1:
                            break

                        if prop == line[:colon_pos].strip():
                            prop_found = True
                            break

                    lineno += 1

        if prop_found:
            if lineno == total_lines - 1:
                _line_end_pos = len(self.text)
            else:
                _line_end_pos = get_line_end_pos(self.text, lineno)

            if value != '':
                #if property found then change its value
                _pos_prop_value = get_line_start_pos(self.text, lineno) + \
                    colon_pos + 2
                self.text = self.text[:_pos_prop_value] + ' ' + value + \
                    self.text[_line_end_pos:]

                self.cursor = (0, lineno)

            else:
                _line_start_pos = get_line_start_pos(self.text, widget_lineno)
                self.text = \
                    self.text[:get_line_start_pos(self.text, lineno)] + \
                    self.text[_line_end_pos:]

        elif value != '':
            #if not found then add property after the widgets line
            _line_end_pos = get_line_end_pos(self.text, widget_lineno)

            indent_str = '\n'
            for i in range(indent + 4):
                indent_str += ' '

            self.cursor = (len(lines[widget_lineno]), widget_lineno)
            self.insert_text(indent_str + prop + ': ' + str(value))

    def set_property_value(self, widget, prop, value, proptype):
        '''To find and change the value of property of widget rule in text
        '''

        #Do not add property if value is empty and
        #property is not a string property

        self._reload = False
        if not isinstance(widget.properties()[prop], StringProperty) and\
                value == '':
            return

        path_to_widget = self._get_widget_path(widget)
        path_to_widget.reverse()

        #Go to the line where widget is declared
        lines = re.sub(r'#.+', '', self.text.rstrip()).splitlines()
        total_lines = len(lines)

        root_name = self.project_loader.root_rule.name
        total_lines = len(lines)
        root_lineno = 0
        for lineno, line in enumerate(lines):
            pos = line.find(root_name)
            if pos != -1 and get_indentation(line) == 0:
                root_lineno = lineno
                break

        widget_lineno = self._find_widget_place(path_to_widget, lines,
                                                total_lines, root_lineno+1)
        widget_line = lines[widget_lineno]
        if not widget_line.strip():
            return

        indent = get_indentation(widget_line)
        prop_found = False

        if ':' not in widget_line:
            #If cannot find ':' then insert it
            self.cursor = (len(lines[widget_lineno]), widget_lineno)
            lines[widget_lineno] += ':'
            self.insert_text(':')

        else:
            #Else find if property has already been declared with a value
            lineno = widget_lineno + 1
            #But if widget line is the last line in the text
            if lineno < total_lines:
                line = lines[lineno]
                _indent = get_indentation(line)
                colon_pos = -1
                while lineno < total_lines and (line.strip() == '' or
                                                _indent > indent):
                    line = lines[lineno]
                    _indent = get_indentation(line)
                    if line.strip() != '':
                        colon_pos = line.find(':')
                        if colon_pos == -1:
                            break

                        if colon_pos == len(line.rstrip()) - 1:
                            break

                        if prop == line[:colon_pos].strip():
                            prop_found = True
                            break

                    lineno += 1

        if prop_found:
            #if property found then change its value
            _pos_prop_value = get_line_start_pos(self.text, lineno) + \
                colon_pos + 2
            if lineno == total_lines - 1:
                _line_end_pos = len(self.text)
            else:
                _line_end_pos = get_line_end_pos(self.text, lineno)

            if proptype == 'StringProperty':
                value = "'"+value+"'"

            self.text = self.text[:_pos_prop_value] + ' ' + str(value) + \
                self.text[_line_end_pos:]

            self.cursor = (0, lineno)

        else:
            #if not found then add property after the widgets line
            _line_start_pos = get_line_start_pos(self.text, widget_lineno)
            _line_end_pos = get_line_end_pos(self.text, widget_lineno)
            if proptype == 'StringProperty':
                value = "'"+value+"'"

            indent_str = '\n'
            for i in range(indent + 4):
                indent_str += ' '

            self.cursor = (len(lines[widget_lineno]), widget_lineno)
            self.insert_text(indent_str + prop + ': ' + str(value))

    def _find_widget_place(self, path, lines, total_lines, lineno, indent=4):
        '''To find the line where widget is declared according to path
        '''

        child_count = 0
        path_index = 1
        path_length = len(path)
        #From starting line go down to find the widget's rule according to path
        while lineno < total_lines and path_index < path_length:
            line = lines[lineno]
            _indent = get_indentation(line)
            colon_pos = line.find(':')
            if _indent == indent and line.strip() != '':
                if colon_pos != -1:
                    line = line.rstrip()
                    if colon_pos == len(line) - 1 and 'canvas' not in line:
                        line = line[:colon_pos].lstrip()
                        if child_count == path[path_index]:
                            path_index += 1
                            indent = _indent + 4
                            child_count = 0
                        else:
                            child_count += 1
                else:
                    child_count += 1

            lineno += 1

        return lineno - 1

########NEW FILE########
__FILENAME__ = py_code_input
from kivy.uix.codeinput import CodeInput
from kivy.properties import ObjectProperty, StringProperty, BooleanProperty
from kivy.uix.scrollview import ScrollView

from designer.uix.designer_code_input import DesignerCodeInput


class PyCodeInput(DesignerCodeInput):
    '''PyCodeInput used as the CodeInput for editing Python Files.
       It's rel_file_path property, gives the file path of the file it is
       currently displaying relative to Project Directory
    '''

    rel_file_path = StringProperty('')
    '''Path of file relative to the Project Directory.
       To get full path of file, use os.path.join
       :data:`rel_file_path` is a :class:`~kivy.properties.StringProperty`
    '''


class PyScrollView(ScrollView):
    '''PyScrollView used as a :class:`~kivy.scrollview.ScrollView`
       for adding :class:`~designer.uix.py_code_input.PyCodeInput`.
    '''

    code_input = ObjectProperty()
    '''Reference to the :class:`~designer.uix.py_code_input.PyCodeInput`.
       :data:`code_input` is a :class:`~kivy.properties.ObjectProperty`
    '''

########NEW FILE########
__FILENAME__ = py_console
import code
import sys
import threading

from kivy.uix.textinput import TextInput
from kivy.uix.scrollview import ScrollView
from kivy.uix.boxlayout import BoxLayout
from kivy.base import runTouchApp
from kivy.clock import Clock
from kivy.base import EventLoop
from kivy.properties import ObjectProperty, ListProperty,\
    StringProperty, NumericProperty
from kivy.lang import Builder

Builder.load_string('''
<PythonConsole>:
    text_input: text_input2
    scroll_view: scroll_view
    ScrollView:
        id: scroll_view
        InteractiveShellInput:
            id: text_input2
            size_hint: (1, None)
            font_name: root.font_name
            font_size: root.font_size
            foreground_color: root.foreground_color
            background_color: root.background_color
            height: max(self.parent.height, self.minimum_height)
            on_ready_to_input: root.ready_to_input()
''')


class PseudoFile(object):
    '''A psuedo file object, to redirect I/O operations from Python Shell to
       InteractiveShellInput.
    '''

    def __init__(self, sh):
        self.sh = sh

    def write(self, s):
        '''To write to a PsuedoFile object.
        '''
        self.sh.write(s)

    def writelines(self, lines):
        '''To write lines to a PsuedoFile object.
        '''

        for line in lines:
            self.write(line)

    def flush(self):
        '''To flush a PsuedoFile object.
        '''
        pass

    def isatty(self):
        '''To determine if PsuedoFile object is a tty or not.
        '''
        return True


class Shell(code.InteractiveConsole):
    "Wrapper around Python that can filter input/output to the shell"

    def __init__(self, root):
        code.InteractiveConsole.__init__(self)
        self.thread = None
        self.root = root
        self._exit = False

    def write(self, data):
        '''write data to show as output on the screen.
        '''
        import functools
        Clock.schedule_once(functools.partial(self.root.show_output, data), 0)

    def raw_input(self, prompt=""):
        '''To show prompt and get required data from user.
        '''
        return self.root.get_input(prompt)

    def runcode(self, _code):
        """Execute a code object.

        When an exception occurs, self.showtraceback() is called to
        display a traceback.  All exceptions are caught except
        SystemExit, which is reraised.

        A note about KeyboardInterrupt: this exception may occur
        elsewhere in this code, and may not always be caught.  The
        caller should be prepared to deal with it.

        """
        org_stdout = sys.stdout
        sys.stdout = PseudoFile(self)
        try:
            exec _code in self.locals
        except SystemExit:
            raise
        except:
            self.showtraceback()
        else:
            if code.softspace(sys.stdout, 0):
                print

        sys.stdout = org_stdout

    def exit(self):
        '''To exit PythonConsole.
        '''
        self._exit = True

    def interact(self, banner=None):
        """Closely emulate the interactive Python console.

        The optional banner argument specify the banner to print
        before the first interaction; by default it prints a banner
        similar to the one printed by the real Python interpreter,
        followed by the current class name in parentheses (so as not
        to confuse this with the real interpreter -- since it's so
        close!).

        """
        try:
            sys.ps1
        except AttributeError:
            sys.ps1 = ">>> "
        try:
            sys.ps2
        except AttributeError:
            sys.ps2 = "... "
        cprt = 'Type "help", "copyright", "credits" or "license"'\
            ' for more information.'
        if banner is None:
            self.write("Python %s on %s\n%s\n(%s)\n" %
                       (sys.version, sys.platform, cprt,
                        self.__class__.__name__))
        else:
            self.write("%s\n" % str(banner))
        more = 0
        while not self._exit:
            try:
                if more:
                    prompt = sys.ps2
                else:
                    prompt = sys.ps1
                try:
                    line = self.raw_input(prompt)
                    if line is None:
                        continue
                    # Can be None if sys.stdin was redefined
                    encoding = getattr(sys.stdin, "encoding", None)
                    if encoding and not isinstance(line, unicode):
                        line = line.decode(encoding)
                except EOFError:
                    self.write("\n")
                    break
                else:
                    more = self.push(line)

            except KeyboardInterrupt:
                self.write("\nKeyboardInterrupt\n")
                self.resetbuffer()
                more = 0


class InteractiveThread(threading.Thread):
    '''Another thread in which main loop of Shell will run.
    '''
    def __init__(self, sh):
        super(InteractiveThread, self).__init__()
        self._sh = sh
        self._sh.thread = self

    def run(self):
        '''To start main loop of _sh in this thread.
        '''
        self._sh.interact()


class InteractiveShellInput(TextInput):
    '''Displays Output and sends input to Shell. Emits 'on_ready_to_input'
       when it is ready to get input from user.
    '''

    __events__ = ('on_ready_to_input',)

    def __init__(self, **kwargs):
        super(InteractiveShellInput, self).__init__(**kwargs)
        self.last_line = None

    def _keyboard_on_key_down(self, window, keycode, text, modifiers):
        '''Override of _keyboard_on_key_down.
        '''
        if keycode[0] == 13:
            #For enter
            self.last_line = self.text[self._cursor_pos:]
            self.dispatch('on_ready_to_input')

        return super(InteractiveShellInput, self)._keyboard_on_key_down(
            window, keycode, text, modifiers)

    def insert_text(self, substring, from_undo=False):
        '''Override of insert_text
        '''
        if self.cursor_index() < self._cursor_pos:
            return

        return super(InteractiveShellInput, self).insert_text(substring,
                                                              from_undo)

    def on_ready_to_input(self, *args):
        '''Default handler of 'on_ready_to_input'
        '''
        pass

    def show_output(self, output):
        '''Show output to the user.
        '''
        self.text += output
        Clock.schedule_once(self._set_cursor_val, 0.1)

    def _set_cursor_val(self, *args):
        '''Get last position of cursor where output was added.
        '''
        self._cursor_pos = self.cursor_index()
        from kivy.animation import Animation
        anim = Animation(scroll_y=0, d=0.5)
        anim.cancel_all(self.parent)
        anim.start(self.parent)


class PythonConsole(BoxLayout):

    text_input = ObjectProperty(None)
    '''Instance of :class:`~designer.uix.py_console.InteractiveShellInput`
       :data:`text_input` is an :class:`~kivy.properties.ObjectProperty`
    '''

    sh = ObjectProperty(None)
    '''Instance of :class:`~designer.uix.py_console.Shell`
       :data:`sh` is an :class:`~kivy.properties.ObjectProperty`
    '''

    scroll_view = ObjectProperty(None)
    '''Instance of :class:`~kivy.uix.scrollview.ScrollView`
       :data:`scroll_view` is an :class:`~kivy.properties.ObjectProperty`
    '''

    foreground_color = ListProperty((.5, .5, .5, .93))
    '''This defines the color of the text in the console

    :data:`foreground_color` is an :class:`~kivy.properties.ListProperty`,
    Default to '(.5, .5, .5, .93)'
    '''

    background_color = ListProperty((0, 0, 0, 1))
    '''This defines the color of the text in the console

    :data:`foreground_color` is an :class:`~kivy.properties.ListProperty`,
    Default to '(0, 0, 0, 1)'''

    font_name = StringProperty('data/fonts/DroidSansMono.ttf')
    '''Indicates the font Style used in the console

    :data:`font` is a :class:`~kivy.properties.StringProperty`,
    Default to 'DroidSansMono'
    '''

    font_size = NumericProperty(14)
    '''Indicates the size of the font used for the console

    :data:`font_size` is a :class:`~kivy.properties.NumericProperty`,
    Default to '9'
    '''

    def __init__(self, **kwargs):
        super(PythonConsole, self).__init__()
        self.sh = Shell(self)
        self._thread = InteractiveThread(self.sh)

        Clock.schedule_once(self.run_sh, 0)
        self._ready_to_input = False
        self._exit = False

    def ready_to_input(self, *args):
        '''Specifies that PythonConsole is ready to take input from user.
        '''
        self._ready_to_input = True

    def run_sh(self, *args):
        '''Start Python Shell.
        '''
        self._thread.start()

    def show_output(self, data, dt):
        '''Show output to user.
        '''
        self.text_input.show_output(data)

    def _show_prompt(self, *args):
        '''Show prompt to user and asks for input.
        '''
        self.text_input.show_output(self.prompt)

    def get_input(self, prompt):
        '''Get input from user.
        '''
        import time
        self.prompt = prompt
        Clock.schedule_once(self._show_prompt, 0.1)
        while not self._ready_to_input and not self._exit:
            time.sleep(0.05)

        self._ready_to_input = False
        return self.text_input.last_line

    def exit(self):
        '''Exit PythonConsole
        '''
        self._exit = True
        self.sh.exit()

if __name__ == '__main__':
    runTouchApp(PythonConsole())

########NEW FILE########
__FILENAME__ = ui_creator
from kivy.uix.floatlayout import FloatLayout
from kivy.properties import ObjectProperty, NumericProperty
from kivy.app import App
from kivy.clock import Clock


class UICreator(FloatLayout):
    '''UICreator is the Wigdet responsible for editing/creating UI of project
    '''

    toolbox = ObjectProperty(None)
    '''Reference to the :class:`~designer.toolbox.Toolbox` instance.
       :data:`toolbox` is an :class:`~kivy.properties.ObjectProperty`
    '''

    propertyviewer = ObjectProperty(None)
    '''Reference to the :class:`~designer.propertyviewer.PropertyViewer`
       instance. :data:`propertyviewer` is an
       :class:`~kivy.properties.ObjectProperty`
    '''

    playground = ObjectProperty(None)
    '''Reference to the :class:`~designer.playground.Playground` instance.
       :data:`playground` is an :class:`~kivy.properties.ObjectProperty`
    '''

    widgettree = ObjectProperty(None)
    '''Reference to the :class:`~designer.nodetree.WidgetsTree` instance.
       :data:`widgettree` is an :class:`~kivy.properties.ObjectProperty`
    '''

    kv_code_input = ObjectProperty(None)
    '''Reference to the :class:`~designer.uix.KVLangArea` instance.
       :data:`kv_code_input` is an
       :class:`~kivy.properties.ObjectProperty`
    '''

    splitter_kv_code_input = ObjectProperty(None)
    '''Reference to the splitter parent of kv_code_input.
       :data:`splitter_kv_code_input` is an
       :class:`~kivy.properties.ObjectProperty`
    '''

    grid_widget_tree = ObjectProperty(None)
    '''Reference to the grid parent of widgettree.
       :data:`grid_widget_tree` is an
       :class:`~kivy.properties.ObjectProperty`
    '''

    splitter_property = ObjectProperty(None)
    '''Reference to the splitter parent of propertyviewer.
       :data:`splitter_property` is an
       :class:`~kivy.properties.ObjectProperty`
    '''

    splitter_widget_tree = ObjectProperty(None)
    '''Reference to the splitter parent of widgettree.
       :data:`splitter_widget_tree` is an
       :class:`~kivy.properties.ObjectProperty`
    '''

    error_console = ObjectProperty(None)
    '''Instance of :class:`~kivy.uix.codeinput.CodeInput` used for displaying
       exceptions.
    '''

    kivy_console = ObjectProperty(None)
    '''Instance of :class:`~designer.uix.kivy_console.KivyConsole`.
    '''

    python_console = ObjectProperty(None)
    '''Instance of :class:`~designer.uix.py_console.PythonConsole`
    '''

    tab_pannel = ObjectProperty(None)
    '''Instance of :class:`~designer.designer_content.DesignerTabbedPanel`
       containing error_console, kivy_console and kv_lang_area
    '''

    eventviewer = ObjectProperty(None)

    def __init__(self, **kwargs):
        super(UICreator, self).__init__(**kwargs)
        Clock.schedule_once(self._setup_everything)

    def reload_btn_pressed(self, *args):
        '''Default handler for 'on_release' event of "Reload" button.
        '''
        self.kv_code_input.func_reload_kv()

    def on_touch_down(self, *args):
        '''Default handler for 'on_touch_down' event.
        '''
        if self.playground and self.playground.keyboard:
            self.playground.keyboard.release()

        return super(UICreator, self).on_touch_down(*args)

    def on_show_edit(self, *args):
        '''Event handler for 'on_show_edit' event.
        '''
        App.get_running_app().root.on_show_edit(*args)

    def cleanup(self):
        '''To clean up everything before loading new project.
        '''
        self.playground.cleanup()
        self.kv_code_input.text = ''

    def _setup_everything(self, *args):
        '''To setup all the references in between widget
        '''

        self.kv_code_input.playground = self.playground
        self.playground.kv_code_input = self.kv_code_input
        self.playground.widgettree = self.widgettree
        self.propertyviewer.kv_code_input = self.kv_code_input
        self.eventviewer.kv_code_input = self.kv_code_input
        self.py_console.remove_widget(self.py_console.children[1])

########NEW FILE########
__FILENAME__ = undo_manager
from kivy.properties import ObjectProperty, OptionProperty
from kivy.uix.textinput import TextInput
from kivy.uix.checkbox import CheckBox
from kivy.app import App


class OperationBase(object):
    '''UndoOperationBase class, Abstract class for all Undo Operations
    '''

    def __init__(self, operation_type):
        super(OperationBase, self).__init__()
        self.operation_type = operation_type

    def do_undo(self):
        pass

    def do_redo(self):
        pass


class WidgetOperation(OperationBase):
    '''WidgetOperation class for widget operations of add and remove
    '''

    def __init__(self, widget_op_type, widget, parent, playground, kv_str):
        super(WidgetOperation, self).__init__('widget')
        self.widget_op_type = widget_op_type
        self.parent = parent
        self.widget = widget
        self.playground = playground
        self.kv_str = kv_str

    def do_undo(self):
        '''Override of :class:`OperationBase`.do_undo.
           This will undo a WidgetOperation.
        '''
        if self.widget_op_type == 'add':
            self.playground.remove_widget_from_parent(self.widget, True)

        else:
            self.widget.parent = None
            self.playground.add_widget_to_parent(self.widget, self.parent,
                                                 from_undo=True,
                                                 kv_str=self.kv_str)

    def do_redo(self):
        '''Override of :class:`OperationBase`.do_redo.
           This will redo a WidgetOperation.
        '''

        if self.widget_op_type == 'remove':
            self.playground.remove_widget_from_parent(self.widget, True)

        else:
            self.widget.parent = None
            self.playground.add_widget_to_parent(self.widget, self.parent,
                                                 from_undo=True,
                                                 kv_str=self.kv_str)


class WidgetDragOperation(OperationBase):

    def __init__(self, widget, cur_parent, prev_parent, prev_index,
                 playground, extra_args):
        self.widget = widget
        self.cur_parent = cur_parent
        self.prev_parent = prev_parent
        self.prev_index = prev_index
        self.playground = playground
        self.cur_index = extra_args['index']
        self.extra_args = extra_args

    def do_undo(self):
        self.cur_parent.remove_widget(self.widget)
        self.playground.drag_wigdet(self.widget, self.prev_parent,
                                    extra_args={'index': self.prev_index,
                                                'prev_index': self.cur_index,
                                                'x': self.extra_args['prev_x'],
                                                'y': self.extra_args['prev_y']},
                                    from_undo=True)

    def do_redo(self):
        self.prev_parent.remove_widget(self.widget)
        self.playground.drag_wigdet(self.widget, self.cur_parent,
                                    extra_args={'index': self.cur_index,
                                                'prev_index': self.prev_index,
                                                'x': self.extra_args['x'],
                                                'y': self.extra_args['y']},
                                    from_undo=True)


class PropOperation(OperationBase):
    '''PropOperation class for Property Operations of changing property value
    '''

    def __init__(self, prop, oldvalue, newvalue):
        super(PropOperation, self).__init__('property')
        self.prop = prop
        self.oldvalue = oldvalue
        self.newvalue = newvalue

    def do_undo(self):
        '''Override of :class:`OperationBase`.do_undo.
           This will undo a PropOperation.
        '''

        setattr(self.prop.propwidget, self.prop.propname, self.oldvalue)
        self._update_widget(self.oldvalue)

    def _update_widget(self, value):
        '''After do_undo or do_redo, this function will update the PropWidget's
           value associated with that property.
        '''
        self.prop.record_to_undo = False
        if isinstance(self.prop, TextInput):
            self.prop.text = value
        elif isinstance(self.prop, CheckBox):
            self.prop.active = value

    def do_redo(self):
        '''Override of :class:`OperationBase`.do_redo.
           This will redo a PropOperation.
        '''

        setattr(self.prop.propwidget, self.prop.propname, self.newvalue)
        self._update_widget(self.newvalue)


class UndoManager(object):
    '''UndoManager is reponsible for managing all the operations related
       to Widgets. It is also responsible for redoing and undoing the last
       available operation.
    '''

    def __init__(self, **kwargs):
        super(UndoManager, self).__init__(**kwargs)
        self._undo_stack_operation = []
        self._redo_stack_operation = []

    def push_operation(self, op):
        '''To push an operation into _undo_stack.
        '''
        App.get_running_app().root._curr_proj_changed = True
        self._undo_stack_operation.append(op)

    def do_undo(self):
        '''To undo last operation
        '''
        if self._undo_stack_operation == []:
            return

        operation = self._undo_stack_operation.pop()
        operation.do_undo()
        self._redo_stack_operation.append(operation)

    def do_redo(self):
        '''To redo last operation
        '''

        if self._redo_stack_operation == []:
            return

        operation = self._redo_stack_operation.pop()
        operation.do_redo()
        self._undo_stack_operation.append(operation)

    def cleanup(self):
        '''To cleanup operation stacks when another project is loaded
        '''
        self._undo_stack_operation = []
        self._redo_stack_operation = []

########NEW FILE########
__FILENAME__ = main
if __name__ == '__main__':
    from designer.app import DesignerApp
    DesignerApp().run()

########NEW FILE########
__FILENAME__ = pep8
#!/usr/bin/env python
# pep8.py - Check Python source code formatting, according to PEP 8
# Copyright (C) 2006 Johann C. Rocholl <johann@rocholl.net>
#
# Permission is hereby granted, free of charge, to any person
# obtaining a copy of this software and associated documentation files
# (the "Software"), to deal in the Software without restriction,
# including without limitation the rights to use, copy, modify, merge,
# publish, distribute, sublicense, and/or sell copies of the Software,
# and to permit persons to whom the Software is furnished to do so,
# subject to the following conditions:
#
# The above copyright notice and this permission notice shall be
# included in all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND,
# EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF
# MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND
# NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS
# BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN
# ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN
# CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.

r"""
Check Python source code formatting, according to PEP 8:
http://www.python.org/dev/peps/pep-0008/

For usage and a list of options, try this:
$ python pep8.py -h

This program and its regression test suite live here:
http://github.com/jcrocholl/pep8

Groups of errors and warnings:
E errors
W warnings
100 indentation
200 whitespace
300 blank lines
400 imports
500 line length
600 deprecation
700 statements
900 syntax error

You can add checks to this program by writing plugins. Each plugin is
a simple function that is called for each line of source code, either
physical or logical.

Physical line:
- Raw line of text from the input file.

Logical line:
- Multi-line statements converted to a single line.
- Stripped left and right.
- Contents of strings replaced with 'xxx' of same length.
- Comments removed.

The check function requests physical or logical lines by the name of
the first argument:

def maximum_line_length(physical_line)
def extraneous_whitespace(logical_line)
def blank_lines(logical_line, blank_lines, indent_level, line_number)

The last example above demonstrates how check plugins can request
additional information with extra arguments. All attributes of the
Checker object are available. Some examples:

lines: a list of the raw lines from the input file
tokens: the tokens that contribute to this logical line
line_number: line number in the input file
blank_lines: blank lines before this one
indent_char: first indentation character in this file (' ' or '\t')
indent_level: indentation (with tabs expanded to multiples of 8)
previous_indent_level: indentation on previous line
previous_logical: previous logical line

The docstring of each check function shall be the relevant part of
text from PEP 8. It is printed if the user enables --show-pep8.
Several docstrings contain examples directly from the PEP 8 document.

Okay: spam(ham[1], {eggs: 2})
E201: spam( ham[1], {eggs: 2})

These examples are verified automatically when pep8.py is run with the
--doctest option. You can add examples for your own check functions.
The format is simple: "Okay" or error/warning code followed by colon
and space, the rest of the line is example source code. If you put 'r'
before the docstring, you can use \n for newline, \t for tab and \s
for space.

"""

__version__ = '1.3.3'

import os
import sys
import re
import time
import inspect
import keyword
import tokenize
from optparse import OptionParser
from fnmatch import fnmatch
try:
    from ConfigParser import RawConfigParser
    from io import TextIOWrapper
except ImportError:
    from configparser import RawConfigParser

DEFAULT_EXCLUDE = '.svn,CVS,.bzr,.hg,.git'
DEFAULT_IGNORE = 'E24'
if sys.platform == 'win32':
    DEFAULT_CONFIG = os.path.expanduser(r'~\.pep8')
else:
    DEFAULT_CONFIG = os.path.join(os.getenv('XDG_CONFIG_HOME') or
                                  os.path.expanduser('~/.config'), 'pep8')
MAX_LINE_LENGTH = 80
REPORT_FORMAT = {
    'default': '%(path)s:%(row)d:%(col)d: %(code)s %(text)s',
    'pylint': '%(path)s:%(row)d: [%(code)s] %(text)s',
}


SINGLETONS = frozenset(['False', 'None', 'True'])
KEYWORDS = frozenset(keyword.kwlist + ['print']) - SINGLETONS
BINARY_OPERATORS = frozenset([
    '**=', '*=', '+=', '-=', '!=', '<>',
    '%=', '^=', '&=', '|=', '==', '/=', '//=', '<=', '>=', '<<=', '>>=',
    '%',  '^',  '&',  '|',  '=',  '/',  '//',  '<',  '>',  '<<'])
UNARY_OPERATORS = frozenset(['>>', '**', '*', '+', '-'])
OPERATORS = BINARY_OPERATORS | UNARY_OPERATORS
WHITESPACE = frozenset(' \t')
SKIP_TOKENS = frozenset([tokenize.COMMENT, tokenize.NL, tokenize.NEWLINE,
                         tokenize.INDENT, tokenize.DEDENT])
BENCHMARK_KEYS = ['directories', 'files', 'logical lines', 'physical lines']

INDENT_REGEX = re.compile(r'([ \t]*)')
RAISE_COMMA_REGEX = re.compile(r'raise\s+\w+\s*(,)')
RERAISE_COMMA_REGEX = re.compile(r'raise\s+\w+\s*,\s*\w+\s*,\s*\w+')
SELFTEST_REGEX = re.compile(r'(Okay|[EW]\d{3}):\s(.*)')
ERRORCODE_REGEX = re.compile(r'[EW]\d{3}')
DOCSTRING_REGEX = re.compile(r'u?r?["\']')
EXTRANEOUS_WHITESPACE_REGEX = re.compile(r'[[({] | []}),;:]')
WHITESPACE_AFTER_COMMA_REGEX = re.compile(r'[,;:]\s*(?:  |\t)')
COMPARE_SINGLETON_REGEX = re.compile(r'([=!]=)\s*(None|False|True)')
COMPARE_TYPE_REGEX = re.compile(r'([=!]=|is|is\s+not)\s*type(?:s\.(\w+)Type'
                                r'|\(\s*(\(\s*\)|[^)]*[^ )])\s*\))')
KEYWORD_REGEX = re.compile(r'(?:[^\s])(\s*)\b(?:%s)\b(\s*)' %
                           r'|'.join(KEYWORDS))
OPERATOR_REGEX = re.compile(r'(?:[^\s])(\s*)(?:[-+*/|!<=>%&^]+)(\s*)')
LAMBDA_REGEX = re.compile(r'\blambda\b')
HUNK_REGEX = re.compile(r'^@@ -\d+,\d+ \+(\d+),(\d+) @@.*$')

# Work around Python < 2.6 behaviour, which does not generate NL after
# a comment which is on a line by itself.
COMMENT_WITH_NL = tokenize.generate_tokens(['#\n'].pop).send(None)[1] == '#\n'


##############################################################################
# Plugins (check functions) for physical lines
##############################################################################


def tabs_or_spaces(physical_line, indent_char):
    r"""
    Never mix tabs and spaces.

    The most popular way of indenting Python is with spaces only.  The
    second-most popular way is with tabs only.  Code indented with a mixture
    of tabs and spaces should be converted to using spaces exclusively.  When
    invoking the Python command line interpreter with the -t option, it issues
    warnings about code that illegally mixes tabs and spaces.  When using -tt
    these warnings become errors.  These options are highly recommended!

    Okay: if a == 0:\n        a = 1\n        b = 1
    E101: if a == 0:\n        a = 1\n\tb = 1
    """
    indent = INDENT_REGEX.match(physical_line).group(1)
    for offset, char in enumerate(indent):
        if char != indent_char:
            return offset, "E101 indentation contains mixed spaces and tabs"


def tabs_obsolete(physical_line):
    r"""
    For new projects, spaces-only are strongly recommended over tabs.  Most
    editors have features that make this easy to do.

    Okay: if True:\n    return
    W191: if True:\n\treturn
    """
    indent = INDENT_REGEX.match(physical_line).group(1)
    if '\t' in indent:
        return indent.index('\t'), "W191 indentation contains tabs"


def trailing_whitespace(physical_line):
    r"""
    JCR: Trailing whitespace is superfluous.
    FBM: Except when it occurs as part of a blank line (i.e. the line is
         nothing but whitespace). According to Python docs[1] a line with only
         whitespace is considered a blank line, and is to be ignored. However,
         matching a blank line to its indentation level avoids mistakenly
         terminating a multi-line statement (e.g. class declaration) when
         pasting code into the standard Python interpreter.

         [1] http://docs.python.org/reference/lexical_analysis.html#blank-lines

    The warning returned varies on whether the line itself is blank, for easier
    filtering for those who want to indent their blank lines.

    Okay: spam(1)
    W291: spam(1)\s
    W293: class Foo(object):\n    \n    bang = 12
    """
    physical_line = physical_line.rstrip('\n')    # chr(10), newline
    physical_line = physical_line.rstrip('\r')    # chr(13), carriage return
    physical_line = physical_line.rstrip('\x0c')  # chr(12), form feed, ^L
    stripped = physical_line.rstrip(' \t\v')
    if physical_line != stripped:
        if stripped:
            return len(stripped), "W291 trailing whitespace"
        else:
            return 0, "W293 blank line contains whitespace"


#def trailing_blank_lines(physical_line, lines, line_number):
#    r"""
#    JCR: Trailing blank lines are superfluous.
#
#    Okay: spam(1)
#    W391: spam(1)\n
#    """
#    if not physical_line.rstrip() and line_number == len(lines):
#        return 0, "W391 blank line at end of file"


def missing_newline(physical_line):
    """
    JCR: The last line should have a newline.

    Reports warning W292.
    """
    if physical_line.rstrip() == physical_line:
        return len(physical_line), "W292 no newline at end of file"


def maximum_line_length(physical_line, max_line_length):
    """
    Limit all lines to a maximum of 79 characters.

    There are still many devices around that are limited to 80 character
    lines; plus, limiting windows to 80 characters makes it possible to have
    several windows side-by-side.  The default wrapping on such devices looks
    ugly.  Therefore, please limit all lines to a maximum of 79 characters.
    For flowing long blocks of text (docstrings or comments), limiting the
    length to 72 characters is recommended.

    Reports error E501.
    """
    line = physical_line.rstrip()
    length = len(line)
    if length > max_line_length:
        if hasattr(line, 'decode'):   # Python 2
            # The line could contain multi-byte characters
            try:
                length = len(line.decode('utf-8'))
            except UnicodeError:
                pass
        if length > max_line_length:
            return (max_line_length, "E501 line too long "
                    "(%d > %d characters)" % (length, max_line_length))


##############################################################################
# Plugins (check functions) for logical lines
##############################################################################


def blank_lines(logical_line, blank_lines, indent_level, line_number,
                previous_logical, previous_indent_level):
    r"""
    Separate top-level function and class definitions with two blank lines.

    Method definitions inside a class are separated by a single blank line.

    Extra blank lines may be used (sparingly) to separate groups of related
    functions.  Blank lines may be omitted between a bunch of related
    one-liners (e.g. a set of dummy implementations).

    Use blank lines in functions, sparingly, to indicate logical sections.

    Okay: def a():\n    pass\n\n\ndef b():\n    pass
    Okay: def a():\n    pass\n\n\n# Foo\n# Bar\n\ndef b():\n    pass

    E301: class Foo:\n    b = 0\n    def bar():\n        pass
    E302: def a():\n    pass\n\ndef b(n):\n    pass
    E303: def a():\n    pass\n\n\n\ndef b(n):\n    pass
    E303: def a():\n\n\n\n    pass
    E304: @decorator\n\ndef a():\n    pass
    """
    if line_number == 1:
        return  # Don't expect blank lines before the first line
    if previous_logical.startswith('@'):
        if blank_lines:
            yield 0, "E304 blank lines found after function decorator"
    elif blank_lines > 2 or (indent_level and blank_lines == 2):
        yield 0, "E303 too many blank lines (%d)" % blank_lines
    elif logical_line.startswith(('def ', 'class ', '@')):
        if indent_level:
            if not (blank_lines or previous_indent_level < indent_level or
                    DOCSTRING_REGEX.match(previous_logical)):
                yield 0, "E301 expected 1 blank line, found 0"
        elif blank_lines != 2:
            yield 0, "E302 expected 2 blank lines, found %d" % blank_lines


def extraneous_whitespace(logical_line):
    """
    Avoid extraneous whitespace in the following situations:

    - Immediately inside parentheses, brackets or braces.

    - Immediately before a comma, semicolon, or colon.

    Okay: spam(ham[1], {eggs: 2})
    E201: spam( ham[1], {eggs: 2})
    E201: spam(ham[ 1], {eggs: 2})
    E201: spam(ham[1], { eggs: 2})
    E202: spam(ham[1], {eggs: 2} )
    E202: spam(ham[1 ], {eggs: 2})
    E202: spam(ham[1], {eggs: 2 })

    E203: if x == 4: print x, y; x, y = y , x
    E203: if x == 4: print x, y ; x, y = y, x
    E203: if x == 4 : print x, y; x, y = y, x
    """
    line = logical_line
    for match in EXTRANEOUS_WHITESPACE_REGEX.finditer(line):
        text = match.group()
        char = text.strip()
        found = match.start()
        if text == char + ' ':
            # assert char in '([{'
            yield found + 1, "E201 whitespace after '%s'" % char
        elif line[found - 1] != ',':
            code = ('E202' if char in '}])' else 'E203')  # if char in ',;:'
            yield found, "%s whitespace before '%s'" % (code, char)


def whitespace_around_keywords(logical_line):
    r"""
    Avoid extraneous whitespace around keywords.

    Okay: True and False
    E271: True and  False
    E272: True  and False
    E273: True and\tFalse
    E274: True\tand False
    """
    for match in KEYWORD_REGEX.finditer(logical_line):
        before, after = match.groups()

        if '\t' in before:
            yield match.start(1), "E274 tab before keyword"
        elif len(before) > 1:
            yield match.start(1), "E272 multiple spaces before keyword"

        if '\t' in after:
            yield match.start(2), "E273 tab after keyword"
        elif len(after) > 1:
            yield match.start(2), "E271 multiple spaces after keyword"


def missing_whitespace(logical_line):
    """
    JCR: Each comma, semicolon or colon should be followed by whitespace.

    Okay: [a, b]
    Okay: (3,)
    Okay: a[1:4]
    Okay: a[:4]
    Okay: a[1:]
    Okay: a[1:4:2]
    E231: ['a','b']
    E231: foo(bar,baz)
    """
    line = logical_line
    for index in range(len(line) - 1):
        char = line[index]
        if char in ',;:' and line[index + 1] not in WHITESPACE:
            before = line[:index]
            if char == ':' and before.count('[') > before.count(']'):
                continue  # Slice syntax, no space required
            if char == ',' and line[index + 1] == ')':
                continue  # Allow tuple with only one element: (3,)
            yield index, "E231 missing whitespace after '%s'" % char


def indentation(logical_line, previous_logical, indent_char,
                indent_level, previous_indent_level):
    r"""
    Use 4 spaces per indentation level.

    For really old code that you don't want to mess up, you can continue to
    use 8-space tabs.

    Okay: a = 1
    Okay: if a == 0:\n    a = 1
    E111:   a = 1

    Okay: for item in items:\n    pass
    E112: for item in items:\npass

    Okay: a = 1\nb = 2
    E113: a = 1\n    b = 2
    """
    if indent_char == ' ' and indent_level % 4:
        yield 0, "E111 indentation is not a multiple of four"
    indent_expect = previous_logical.endswith(':')
    if indent_expect and indent_level <= previous_indent_level:
        yield 0, "E112 expected an indented block"
    if indent_level > previous_indent_level and not indent_expect:
        yield 0, "E113 unexpected indentation"


def continuation_line_indentation(logical_line, tokens, indent_level, verbose):
    r"""
    Continuation lines should align wrapped elements either vertically using
    Python's implicit line joining inside parentheses, brackets and braces, or
    using a hanging indent.

    When using a hanging indent the following considerations should be applied:

    - there should be no arguments on the first line, and

    - further indentation should be used to clearly distinguish itself as a
      continuation line.

    Okay: a = (\n)
    E123: a = (\n    )

    Okay: a = (\n    42)
    E121: a = (\n   42)
    E122: a = (\n42)
    E123: a = (\n    42\n    )
    E124: a = (24,\n     42\n)
    E125: if (a or\n    b):\n    pass
    E126: a = (\n        42)
    E127: a = (24,\n      42)
    E128: a = (24,\n    42)
    """
    first_row = tokens[0][2][0]
    nrows = 1 + tokens[-1][2][0] - first_row
    if nrows == 1:
        return

    # indent_next tells us whether the next block is indented; assuming
    # that it is indented by 4 spaces, then we should not allow 4-space
    # indents on the final continuation line; in turn, some other
    # indents are allowed to have an extra 4 spaces.
    indent_next = logical_line.endswith(':')

    row = depth = 0
    # remember how many brackets were opened on each line
    parens = [0] * nrows
    # relative indents of physical lines
    rel_indent = [0] * nrows
    # visual indents
    indent = [indent_level]
    indent_chances = {}
    last_indent = (0, 0)
    if verbose >= 3:
        print((">>> " + tokens[0][4].rstrip()))

    for token_type, text, start, end, line in tokens:
        newline = row < start[0] - first_row
        if newline:
            row = start[0] - first_row
            newline = (not last_token_multiline and
                       token_type not in (tokenize.NL, tokenize.NEWLINE))

        if newline:
            # this is the beginning of a continuation line.
            last_indent = start
            if verbose >= 3:
                print(("... " + line.rstrip()))

            # record the initial indent.
            rel_indent[row] = start[1] - indent_level

            if depth:
                # a bracket expression in a continuation line.
                # find the line that it was opened on
                for open_row in range(row - 1, -1, -1):
                    if parens[open_row]:
                        break
            else:
                # an unbracketed continuation line (ie, backslash)
                open_row = 0
            hang = rel_indent[row] - rel_indent[open_row]
            visual_indent = indent_chances.get(start[1])

            if token_type == tokenize.OP and text in ']})':
                # this line starts with a closing bracket
                if indent[depth]:
                    if start[1] != indent[depth]:
                        yield (start, 'E124 closing bracket does not match '
                               'visual indentation')
                elif hang:
                    yield (start, 'E123 closing bracket does not match '
                           'indentation of opening bracket\'s line')
            elif visual_indent is True:
                # visual indent is verified
                if not indent[depth]:
                    indent[depth] = start[1]
            elif visual_indent in (text, str):
                # ignore token lined up with matching one from a previous line
                pass
            elif indent[depth] and start[1] < indent[depth]:
                # visual indent is broken
                yield (start, 'E128 continuation line '
                       'under-indented for visual indent')
            elif hang == 4 or (indent_next and rel_indent[row] == 8):
                # hanging indent is verified
                pass
            else:
                # indent is broken
                if hang <= 0:
                    error = 'E122', 'missing indentation or outdented'
                elif indent[depth]:
                    error = 'E127', 'over-indented for visual indent'
                elif hang % 4:
                    error = 'E121', 'indentation is not a multiple of four'
                else:
                    error = 'E126', 'over-indented for hanging indent'
                yield start, "%s continuation line %s" % error

        # look for visual indenting
        if parens[row] and token_type != tokenize.NL and not indent[depth]:
            indent[depth] = start[1]
            indent_chances[start[1]] = True
            if verbose >= 4:
                print(("bracket depth %s indent to %s" % (depth, start[1])))
        # deal with implicit string concatenation
        elif token_type == tokenize.STRING or text in ('u', 'ur', 'b', 'br'):
            indent_chances[start[1]] = str

        # keep track of bracket depth
        if token_type == tokenize.OP:
            if text in '([{':
                depth += 1
                indent.append(0)
                parens[row] += 1
                if verbose >= 4:
                    print(("bracket depth %s seen, col %s, visual min = %s" %
                          (depth, start[1], indent[depth])))
            elif text in ')]}' and depth > 0:
                # parent indents should not be more than this one
                prev_indent = indent.pop() or last_indent[1]
                for d in range(depth):
                    if indent[d] > prev_indent:
                        indent[d] = 0
                for ind in list(indent_chances):
                    if ind >= prev_indent:
                        del indent_chances[ind]
                depth -= 1
                if depth:
                    indent_chances[indent[depth]] = True
                for idx in range(row, -1, -1):
                    if parens[idx]:
                        parens[idx] -= 1
                        break
            assert len(indent) == depth + 1
            if start[1] not in indent_chances:
                # allow to line up tokens
                indent_chances[start[1]] = text

        last_token_multiline = (start[0] != end[0])

    if indent_next and rel_indent[-1] == 4:
        yield (last_indent, "E125 continuation line does not distinguish "
               "itself from next logical line")


def whitespace_before_parameters(logical_line, tokens):
    """
    Avoid extraneous whitespace in the following situations:

    - Immediately before the open parenthesis that starts the argument
      list of a function call.

    - Immediately before the open parenthesis that starts an indexing or
      slicing.

    Okay: spam(1)
    E211: spam (1)

    Okay: dict['key'] = list[index]
    E211: dict ['key'] = list[index]
    E211: dict['key'] = list [index]
    """
    prev_type = tokens[0][0]
    prev_text = tokens[0][1]
    prev_end = tokens[0][3]
    for index in range(1, len(tokens)):
        token_type, text, start, end, line = tokens[index]
        if (token_type == tokenize.OP and
            text in '([' and
            start != prev_end and
            (prev_type == tokenize.NAME or prev_text in '}])') and
            # Syntax "class A (B):" is allowed, but avoid it
            (index < 2 or tokens[index - 2][1] != 'class') and
                # Allow "return (a.foo for a in range(5))"
                not keyword.iskeyword(prev_text)):
            yield prev_end, "E211 whitespace before '%s'" % text
        prev_type = token_type
        prev_text = text
        prev_end = end


def whitespace_around_operator(logical_line):
    r"""
    Avoid extraneous whitespace in the following situations:

    - More than one space around an assignment (or other) operator to
      align it with another.

    Okay: a = 12 + 3
    E221: a = 4  + 5
    E222: a = 4 +  5
    E223: a = 4\t+ 5
    E224: a = 4 +\t5
    """
    for match in OPERATOR_REGEX.finditer(logical_line):
        before, after = match.groups()

        if '\t' in before:
            yield match.start(1), "E223 tab before operator"
        elif len(before) > 1:
            yield match.start(1), "E221 multiple spaces before operator"

        if '\t' in after:
            yield match.start(2), "E224 tab after operator"
        elif len(after) > 1:
            yield match.start(2), "E222 multiple spaces after operator"


def missing_whitespace_around_operator(logical_line, tokens):
    r"""
    - Always surround these binary operators with a single space on
      either side: assignment (=), augmented assignment (+=, -= etc.),
      comparisons (==, <, >, !=, <>, <=, >=, in, not in, is, is not),
      Booleans (and, or, not).

    - Use spaces around arithmetic operators.

    Okay: i = i + 1
    Okay: submitted += 1
    Okay: x = x * 2 - 1
    Okay: hypot2 = x * x + y * y
    Okay: c = (a + b) * (a - b)
    Okay: foo(bar, key='word', *args, **kwargs)
    Okay: baz(**kwargs)
    Okay: negative = -1
    Okay: spam(-1)
    Okay: alpha[:-i]
    Okay: if not -5 < x < +5:\n    pass
    Okay: lambda *args, **kw: (args, kw)

    E225: i=i+1
    E225: submitted +=1
    E225: x = x*2 - 1
    E225: hypot2 = x*x + y*y
    E225: c = (a+b) * (a-b)
    E225: c = alpha -4
    E225: z = x **y
    """
    parens = 0
    need_space = False
    prev_type = tokenize.OP
    prev_text = prev_end = None
    for token_type, text, start, end, line in tokens:
        if token_type in (tokenize.NL, tokenize.NEWLINE, tokenize.ERRORTOKEN):
            # ERRORTOKEN is triggered by backticks in Python 3000
            continue
        if text in ('(', 'lambda'):
            parens += 1
        elif text == ')':
            parens -= 1
        if need_space:
            if start != prev_end:
                need_space = False
            elif text == '>' and prev_text in ('<', '-'):
                # Tolerate the "<>" operator, even if running Python 3
                # Deal with Python 3's annotated return value "->"
                pass
            else:
                yield prev_end, "E225 missing whitespace around operator"
                need_space = False
        elif token_type == tokenize.OP and prev_end is not None:
            if text == '=' and parens:
                # Allow keyword args or defaults: foo(bar=None).
                pass
            elif text in BINARY_OPERATORS:
                need_space = True
            elif text in UNARY_OPERATORS:
                # Allow unary operators: -123, -x, +1.
                # Allow argument unpacking: foo(*args, **kwargs).
                if prev_type == tokenize.OP:
                    if prev_text in '}])':
                        need_space = True
                elif prev_type == tokenize.NAME:
                    if prev_text not in KEYWORDS:
                        need_space = True
                elif prev_type not in SKIP_TOKENS:
                    need_space = True
            if need_space and start == prev_end:
                yield prev_end, "E225 missing whitespace around operator"
                need_space = False
        prev_type = token_type
        prev_text = text
        prev_end = end


def whitespace_around_comma(logical_line):
    r"""
    Avoid extraneous whitespace in the following situations:

    - More than one space around an assignment (or other) operator to
      align it with another.

    Note: these checks are disabled by default

    Okay: a = (1, 2)
    E241: a = (1,  2)
    E242: a = (1,\t2)
    """
    line = logical_line
    for m in WHITESPACE_AFTER_COMMA_REGEX.finditer(line):
        found = m.start() + 1
        if '\t' in m.group():
            yield found, "E242 tab after '%s'" % m.group()[0]
        else:
            yield found, "E241 multiple spaces after '%s'" % m.group()[0]


def whitespace_around_named_parameter_equals(logical_line, tokens):
    """
    Don't use spaces around the '=' sign when used to indicate a
    keyword argument or a default parameter value.

    Okay: def complex(real, imag=0.0):
    Okay: return magic(r=real, i=imag)
    Okay: boolean(a == b)
    Okay: boolean(a != b)
    Okay: boolean(a <= b)
    Okay: boolean(a >= b)

    E251: def complex(real, imag = 0.0):
    E251: return magic(r = real, i = imag)
    """
    parens = 0
    no_space = False
    prev_end = None
    for token_type, text, start, end, line in tokens:
        if no_space:
            no_space = False
            if start != prev_end:
                yield (prev_end,
                       "E251 no spaces around keyword / parameter equals")
        elif token_type == tokenize.OP:
            if text == '(':
                parens += 1
            elif text == ')':
                parens -= 1
            elif parens and text == '=':
                no_space = True
                if start != prev_end:
                    yield (prev_end,
                           "E251 no spaces around keyword / parameter equals")
        prev_end = end


def whitespace_before_inline_comment(logical_line, tokens):
    """
    Separate inline comments by at least two spaces.

    An inline comment is a comment on the same line as a statement.  Inline
    comments should be separated by at least two spaces from the statement.
    They should start with a # and a single space.

    Okay: x = x + 1  # Increment x
    Okay: x = x + 1    # Increment x
    E261: x = x + 1 # Increment x
    E262: x = x + 1  #Increment x
    E262: x = x + 1  #  Increment x
    """
    prev_end = (0, 0)
    for token_type, text, start, end, line in tokens:
        if token_type == tokenize.COMMENT:
            if not line[:start[1]].strip():
                continue
            if prev_end[0] == start[0] and start[1] < prev_end[1] + 2:
                yield (prev_end,
                       "E261 at least two spaces before inline comment")
            if text.startswith('#  ') or not text.startswith('# '):
                yield start, "E262 inline comment should start with '# '"
        elif token_type != tokenize.NL:
            prev_end = end


def imports_on_separate_lines(logical_line):
    r"""
    Imports should usually be on separate lines.

    Okay: import os\nimport sys
    E401: import sys, os

    Okay: from subprocess import Popen, PIPE
    Okay: from myclas import MyClass
    Okay: from foo.bar.yourclass import YourClass
    Okay: import myclass
    Okay: import foo.bar.yourclass
    """
    line = logical_line
    if line.startswith('import '):
        found = line.find(',')
        if -1 < found:
            yield found, "E401 multiple imports on one line"


def compound_statements(logical_line):
    r"""
    Compound statements (multiple statements on the same line) are
    generally discouraged.

    While sometimes it's okay to put an if/for/while with a small body
    on the same line, never do this for multi-clause statements. Also
    avoid folding such long lines!

    Okay: if foo == 'blah':\n    do_blah_thing()
    Okay: do_one()
    Okay: do_two()
    Okay: do_three()

    E701: if foo == 'blah': do_blah_thing()
    E701: for x in lst: total += x
    E701: while t < 10: t = delay()
    E701: if foo == 'blah': do_blah_thing()
    E701: else: do_non_blah_thing()
    E701: try: something()
    E701: finally: cleanup()
    E701: if foo == 'blah': one(); two(); three()

    E702: do_one(); do_two(); do_three()
    """
    line = logical_line
    found = line.find(':')
    if -1 < found < len(line) - 1:
        before = line[:found]
        if (before.count('{') <= before.count('}') and  # {'a': 1} (dict)
            before.count('[') <= before.count(']') and  # [1:2] (slice)
            before.count('(') <= before.count(')') and  # (Python 3 annotation)
                not LAMBDA_REGEX.search(before)):       # lambda x: x
            yield found, "E701 multiple statements on one line (colon)"
    found = line.find(';')
    if -1 < found:
        yield found, "E702 multiple statements on one line (semicolon)"


def explicit_line_join(logical_line, tokens):
    r"""
    Avoid explicit line join between brackets.

    The preferred way of wrapping long lines is by using Python's implied line
    continuation inside parentheses, brackets and braces.  Long lines can be
    broken over multiple lines by wrapping expressions in parentheses.  These
    should be used in preference to using a backslash for line continuation.

    E502: aaa = [123, \\n       123]
    E502: aaa = ("bbb " \\n       "ccc")

    Okay: aaa = [123,\n       123]
    Okay: aaa = ("bbb "\n       "ccc")
    Okay: aaa = "bbb " \\n    "ccc"
    """
    prev_start = prev_end = parens = 0
    for token_type, text, start, end, line in tokens:
        if start[0] != prev_start and parens and backslash:
            yield backslash, "E502 the backslash is redundant between brackets"
        if end[0] != prev_end:
            if line.rstrip('\r\n').endswith('\\'):
                backslash = (end[0], len(line.splitlines()[-1]) - 1)
            else:
                backslash = None
            prev_start = prev_end = end[0]
        else:
            prev_start = start[0]
        if token_type == tokenize.OP:
            if text in '([{':
                parens += 1
            elif text in ')]}':
                parens -= 1


def comparison_to_singleton(logical_line):
    """
    Comparisons to singletons like None should always be done
    with "is" or "is not", never the equality operators.

    Okay: if arg is not None:
    E711: if arg != None:
    E712: if arg == True:

    Also, beware of writing if x when you really mean if x is not None --
    e.g. when testing whether a variable or argument that defaults to None was
    set to some other value.  The other value might have a type (such as a
    container) that could be false in a boolean context!
    """
    match = COMPARE_SINGLETON_REGEX.search(logical_line)
    if match:
        same = (match.group(1) == '==')
        singleton = match.group(2)
        msg = "'if cond is %s:'" % (('' if same else 'not ') + singleton)
        if singleton in ('None',):
            code = 'E711'
        else:
            code = 'E712'
            nonzero = ((singleton == 'True' and same) or
                       (singleton == 'False' and not same))
            msg += " or 'if %scond:'" % ('' if nonzero else 'not ')
        yield match.start(1), ("%s comparison to %s should be %s" %
                               (code, singleton, msg))


def comparison_type(logical_line):
    """
    Object type comparisons should always use isinstance() instead of
    comparing types directly.

    Okay: if isinstance(obj, int):
    E721: if type(obj) is type(1):

    When checking if an object is a string, keep in mind that it might be a
    unicode string too! In Python 2.3, str and unicode have a common base
    class, basestring, so you can do:

    Okay: if isinstance(obj, basestring):
    Okay: if type(a1) is type(b1):
    """
    match = COMPARE_TYPE_REGEX.search(logical_line)
    if match:
        inst = match.group(3)
        if inst and isidentifier(inst) and inst not in SINGLETONS:
            return  # Allow comparison for types which are not obvious
        yield match.start(1), "E721 do not compare types, use 'isinstance()'"


def python_3000_has_key(logical_line):
    r"""
    The {}.has_key() method will be removed in the future version of
    Python. Use the 'in' operation instead.

    Okay: if "alph" in d:\n    print d["alph"]
    W601: assert d.has_key('alph')
    """
    pos = logical_line.find('.has_key(')
    if pos > -1:
        yield pos, "W601 .has_key() is deprecated, use 'in'"


def python_3000_raise_comma(logical_line):
    """
    When raising an exception, use "raise ValueError('message')"
    instead of the older form "raise ValueError, 'message'".

    The paren-using form is preferred because when the exception arguments
    are long or include string formatting, you don't need to use line
    continuation characters thanks to the containing parentheses.  The older
    form will be removed in Python 3000.

    Okay: raise DummyError("Message")
    W602: raise DummyError, "Message"
    """
    match = RAISE_COMMA_REGEX.match(logical_line)
    if match and not RERAISE_COMMA_REGEX.match(logical_line):
        yield match.start(1), "W602 deprecated form of raising exception"


def python_3000_not_equal(logical_line):
    """
    != can also be written <>, but this is an obsolete usage kept for
    backwards compatibility only. New code should always use !=.
    The older syntax is removed in Python 3000.

    Okay: if a != 'no':
    W603: if a <> 'no':
    """
    pos = logical_line.find('<>')
    if pos > -1:
        yield pos, "W603 '<>' is deprecated, use '!='"


def python_3000_backticks(logical_line):
    """
    Backticks are removed in Python 3000.
    Use repr() instead.

    Okay: val = repr(1 + 2)
    W604: val = `1 + 2`
    """
    pos = logical_line.find('`')
    if pos > -1:
        yield pos, "W604 backticks are deprecated, use 'repr()'"


##############################################################################
# Helper functions
##############################################################################


if '' == ''.encode():
    # Python 2: implicit encoding.
    def readlines(filename):
        f = open(filename)
        try:
            return f.readlines()
        finally:
            f.close()

    isidentifier = re.compile(r'[a-zA-Z_]\w*').match
    stdin_get_value = sys.stdin.read
else:
    # Python 3
    def readlines(filename):
        f = open(filename, 'rb')
        try:
            coding, lines = tokenize.detect_encoding(f.readline)
            f = TextIOWrapper(f, coding, line_buffering=True)
            return [l.decode(coding) for l in lines] + f.readlines()
        except (LookupError, SyntaxError, UnicodeError):
            f.close()
            # Fall back if files are improperly declared
            f = open(filename, encoding='latin-1')
            return f.readlines()
        finally:
            f.close()

    isidentifier = str.isidentifier
    stdin_get_value = TextIOWrapper(sys.stdin.buffer, errors='ignore').read
readlines.__doc__ = "    Read the source code."


def expand_indent(line):
    r"""
    Return the amount of indentation.
    Tabs are expanded to the next multiple of 8.

    >>> expand_indent('    ')
    4
    >>> expand_indent('\t')
    8
    >>> expand_indent('    \t')
    8
    >>> expand_indent('       \t')
    8
    >>> expand_indent('        \t')
    16
    """
    if '\t' not in line:
        return len(line) - len(line.lstrip())
    result = 0
    for char in line:
        if char == '\t':
            result = result // 8 * 8 + 8
        elif char == ' ':
            result += 1
        else:
            break
    return result


def mute_string(text):
    """
    Replace contents with 'xxx' to prevent syntax matching.

    >>> mute_string('"abc"')
    '"xxx"'
    >>> mute_string("'''abc'''")
    "'''xxx'''"
    >>> mute_string("r'abc'")
    "r'xxx'"
    """
    # String modifiers (e.g. u or r)
    start = text.index(text[-1]) + 1
    end = len(text) - 1
    # Triple quotes
    if text[-3:] in ('"""', "'''"):
        start += 2
        end -= 2
    return text[:start] + 'x' * (end - start) + text[end:]


def parse_udiff(diff, patterns=None, parent='.'):
    rv = {}
    path = nrows = None
    for line in diff.splitlines():
        if nrows:
            if line[:1] != '-':
                nrows -= 1
            continue
        if line[:3] == '@@ ':
            row, nrows = [int(g) for g in HUNK_REGEX.match(line).groups()]
            rv[path].update(list(range(row, row + nrows)))
        elif line[:3] == '+++':
            path = line[4:].split('\t', 1)[0]
            if path[:2] == 'b/':
                path = path[2:]
            rv[path] = set()
    return dict([(os.path.join(parent, path), rows)
                 for (path, rows) in list(rv.items())
                 if rows and filename_match(path, patterns)])


def filename_match(filename, patterns, default=True):
    """
    Check if patterns contains a pattern that matches filename.
    If patterns is unspecified, this always returns True.
    """
    if not patterns:
        return default
    return any(fnmatch(filename, pattern) for pattern in patterns)


##############################################################################
# Framework to run all checks
##############################################################################


def find_checks(argument_name):
    """
    Find all globally visible functions where the first argument name
    starts with argument_name.
    """
    for name, function in list(globals().items()):
        if not inspect.isfunction(function):
            continue
        args = inspect.getargspec(function)[0]
        if args and args[0].startswith(argument_name):
            codes = ERRORCODE_REGEX.findall(function.__doc__ or '')
            yield name, codes, function, args


class Checker(object):
    """
    Load a Python source file, tokenize it, check coding style.
    """

    def __init__(self, filename, lines=None,
                 options=None, report=None, **kwargs):
        if options is None:
            options = StyleGuide(kwargs).options
        else:
            assert not kwargs
        self._io_error = None
        self._physical_checks = options.physical_checks
        self._logical_checks = options.logical_checks
        self.max_line_length = options.max_line_length
        self.verbose = options.verbose
        self.filename = filename
        if filename is None:
            self.filename = 'stdin'
            self.lines = lines or []
        elif lines is None:
            try:
                self.lines = readlines(filename)
            except IOError:
                exc_type, exc = sys.exc_info()[:2]
                self._io_error = '%s: %s' % (exc_type.__name__, exc)
                self.lines = []
        else:
            self.lines = lines
        self.report = report or options.report
        self.report_error = self.report.error

    def readline(self):
        """
        Get the next line from the input buffer.
        """
        self.line_number += 1
        if self.line_number > len(self.lines):
            return ''
        return self.lines[self.line_number - 1]

    def readline_check_physical(self):
        """
        Check and return the next physical line. This method can be
        used to feed tokenize.generate_tokens.
        """
        line = self.readline()
        if line:
            self.check_physical(line)
        return line

    def run_check(self, check, argument_names):
        """
        Run a check plugin.
        """
        arguments = []
        for name in argument_names:
            arguments.append(getattr(self, name))
        return check(*arguments)

    def check_physical(self, line):
        """
        Run all physical checks on a raw input line.
        """
        self.physical_line = line
        if self.indent_char is None and line[:1] in WHITESPACE:
            self.indent_char = line[0]
        for name, check, argument_names in self._physical_checks:
            result = self.run_check(check, argument_names)
            if result is not None:
                offset, text = result
                self.report_error(self.line_number, offset, text, check)

    def build_tokens_line(self):
        """
        Build a logical line from tokens.
        """
        self.mapping = []
        logical = []
        length = 0
        previous = None
        for token in self.tokens:
            token_type, text = token[0:2]
            if token_type in SKIP_TOKENS:
                continue
            if token_type == tokenize.STRING:
                text = mute_string(text)
            if previous:
                end_row, end = previous[3]
                start_row, start = token[2]
                if end_row != start_row:    # different row
                    prev_text = self.lines[end_row - 1][end - 1]
                    if prev_text == ',' or (prev_text not in '{[('
                                            and text not in '}])'):
                        logical.append(' ')
                        length += 1
                elif end != start:  # different column
                    fill = self.lines[end_row - 1][end:start]
                    logical.append(fill)
                    length += len(fill)
            self.mapping.append((length, token))
            logical.append(text)
            length += len(text)
            previous = token
        self.logical_line = ''.join(logical)
        assert self.logical_line.strip() == self.logical_line

    def check_logical(self):
        """
        Build a line from tokens and run all logical checks on it.
        """
        self.build_tokens_line()
        self.report.increment_logical_line()
        first_line = self.lines[self.mapping[0][1][2][0] - 1]
        indent = first_line[:self.mapping[0][1][2][1]]
        self.previous_indent_level = self.indent_level
        self.indent_level = expand_indent(indent)
        if self.verbose >= 2:
            print((self.logical_line[:80].rstrip()))
        for name, check, argument_names in self._logical_checks:
            if self.verbose >= 4:
                print(('   ' + name))
            for result in self.run_check(check, argument_names):
                offset, text = result
                if isinstance(offset, tuple):
                    orig_number, orig_offset = offset
                else:
                    for token_offset, token in self.mapping:
                        if offset >= token_offset:
                            orig_number = token[2][0]
                            orig_offset = (token[2][1] + offset - token_offset)
                self.report_error(orig_number, orig_offset, text, check)
        self.previous_logical = self.logical_line

    def generate_tokens(self):
        if self._io_error:
            self.report_error(1, 0, 'E902 %s' % self._io_error, readlines)
        tokengen = tokenize.generate_tokens(self.readline_check_physical)
        try:
            for token in tokengen:
                yield token
        except (SyntaxError, tokenize.TokenError):
            exc_type, exc = sys.exc_info()[:2]
            offset = exc.args[1]
            if len(offset) > 2:
                offset = offset[1:3]
            self.report_error(offset[0], offset[1],
                              'E901 %s: %s' % (exc_type.__name__, exc.args[0]),
                              self.generate_tokens)
    generate_tokens.__doc__ = "    Check if the syntax is valid."

    def check_all(self, expected=None, line_offset=0):
        """
        Run all checks on the input file.
        """
        self.report.init_file(self.filename, self.lines, expected, line_offset)
        self.line_number = 0
        self.indent_char = None
        self.indent_level = 0
        self.previous_logical = ''
        self.tokens = []
        self.blank_lines = blank_lines_before_comment = 0
        parens = 0
        for token in self.generate_tokens():
            self.tokens.append(token)
            token_type, text = token[0:2]
            if self.verbose >= 3:
                if token[2][0] == token[3][0]:
                    pos = '[%s:%s]' % (token[2][1] or '', token[3][1])
                else:
                    pos = 'l.%s' % token[3][0]
                print(('l.%s\t%s\t%s\t%r' %
                      (token[2][0], pos, tokenize.tok_name[token[0]], text)))
            if token_type == tokenize.OP:
                if text in '([{':
                    parens += 1
                elif text in '}])':
                    parens -= 1
            elif not parens:
                if token_type == tokenize.NEWLINE:
                    if self.blank_lines < blank_lines_before_comment:
                        self.blank_lines = blank_lines_before_comment
                    self.check_logical()
                    self.tokens = []
                    self.blank_lines = blank_lines_before_comment = 0
                elif token_type == tokenize.NL:
                    if len(self.tokens) == 1:
                        # The physical line contains only this token.
                        self.blank_lines += 1
                    self.tokens = []
                elif token_type == tokenize.COMMENT and len(self.tokens) == 1:
                    if blank_lines_before_comment < self.blank_lines:
                        blank_lines_before_comment = self.blank_lines
                    self.blank_lines = 0
                    if COMMENT_WITH_NL:
                        # The comment also ends a physical line
                        self.tokens = []
        return self.report.get_file_results()


class BaseReport(object):
    """Collect the results of the checks."""
    print_filename = False

    def __init__(self, options):
        self._benchmark_keys = options.benchmark_keys
        self._ignore_code = options.ignore_code
        # Results
        self.elapsed = 0
        self.total_errors = 0
        self.counters = dict.fromkeys(self._benchmark_keys, 0)
        self.messages = {}

    def start(self):
        """Start the timer."""
        self._start_time = time.time()

    def stop(self):
        """Stop the timer."""
        self.elapsed = time.time() - self._start_time

    def init_file(self, filename, lines, expected, line_offset):
        """Signal a new file."""
        self.filename = filename
        self.lines = lines
        self.expected = expected or ()
        self.line_offset = line_offset
        self.file_errors = 0
        self.counters['files'] += 1
        self.counters['physical lines'] += len(lines)

    def increment_logical_line(self):
        """Signal a new logical line."""
        self.counters['logical lines'] += 1

    def error(self, line_number, offset, text, check):
        """Report an error, according to options."""
        code = text[:4]
        if self._ignore_code(code):
            return
        if code in self.counters:
            self.counters[code] += 1
        else:
            self.counters[code] = 1
            self.messages[code] = text[5:]
        # Don't care about expected errors or warnings
        if code in self.expected:
            return
        if self.print_filename and not self.file_errors:
            print((self.filename))
        self.file_errors += 1
        self.total_errors += 1
        return code

    def get_file_results(self):
        """Return the count of errors and warnings for this file."""
        return self.file_errors

    def get_count(self, prefix=''):
        """Return the total count of errors and warnings."""
        return sum([self.counters[key]
                    for key in self.messages if key.startswith(prefix)])

    def get_statistics(self, prefix=''):
        """
        Get statistics for message codes that start with the prefix.

        prefix='' matches all errors and warnings
        prefix='E' matches all errors
        prefix='W' matches all warnings
        prefix='E4' matches all errors that have to do with imports
        """
        return ['%-7s %s %s' % (self.counters[key], key, self.messages[key])
                for key in sorted(self.messages) if key.startswith(prefix)]

    def print_statistics(self, prefix=''):
        """Print overall statistics (number of errors and warnings)."""
        for line in self.get_statistics(prefix):
            print(line)

    def print_benchmark(self):
        """Print benchmark numbers."""
        print(('%-7.2f %s' % (self.elapsed, 'seconds elapsed')))
        if self.elapsed:
            for key in self._benchmark_keys:
                print(('%-7d %s per second (%d total)' %
                      (self.counters[key] / self.elapsed, key,
                       self.counters[key])))


class FileReport(BaseReport):
    print_filename = True


class StandardReport(BaseReport):
    """Collect and print the results of the checks."""

    def __init__(self, options):
        super(StandardReport, self).__init__(options)
        self._fmt = REPORT_FORMAT.get(options.format.lower(),
                                      options.format)
        self._repeat = options.repeat
        self._show_source = options.show_source
        self._show_pep8 = options.show_pep8

    def error(self, line_number, offset, text, check):
        """
        Report an error, according to options.
        """
        code = super(StandardReport, self).error(line_number, offset,
                                                 text, check)
        if code and (self.counters[code] == 1 or self._repeat):
            print((self._fmt % {
                'path': self.filename,
                'row': self.line_offset + line_number, 'col': offset + 1,
                'code': code, 'text': text[5:],
            }))
            if self._show_source:
                if line_number > len(self.lines):
                    line = ''
                else:
                    line = self.lines[line_number - 1]
                print((line.rstrip()))
                print((' ' * offset + '^'))
            if self._show_pep8:
                print((check.__doc__.lstrip('\n').rstrip()))
        return code


class DiffReport(StandardReport):
    """Collect and print the results for the changed lines only."""

    def __init__(self, options):
        super(DiffReport, self).__init__(options)
        self._selected = options.selected_lines

    def error(self, line_number, offset, text, check):
        if line_number not in self._selected[self.filename]:
            return
        return super(DiffReport, self).error(line_number, offset, text, check)


class TestReport(StandardReport):
    """Collect the results for the tests."""

    def __init__(self, options):
        options.benchmark_keys += ['test cases', 'failed tests']
        super(TestReport, self).__init__(options)
        self._verbose = options.verbose

    def get_file_results(self):
        # Check if the expected errors were found
        label = '%s:%s:1' % (self.filename, self.line_offset)
        codes = sorted(self.expected)
        for code in codes:
            if not self.counters.get(code):
                self.file_errors += 1
                self.total_errors += 1
                print(('%s: error %s not found' % (label, code)))
        if self._verbose and not self.file_errors:
            print(('%s: passed (%s)' %
                  (label, ' '.join(codes) or 'Okay')))
        self.counters['test cases'] += 1
        if self.file_errors:
            self.counters['failed tests'] += 1
        # Reset counters
        for key in set(self.counters) - set(self._benchmark_keys):
            del self.counters[key]
        self.messages = {}
        return self.file_errors

    def print_results(self):
        results = ("%(physical lines)d lines tested: %(files)d files, "
                   "%(test cases)d test cases%%s." % self.counters)
        if self.total_errors:
            print((results % ", %s failures" % self.total_errors))
        else:
            print((results % ""))
        print(("Test failed." if self.total_errors else "Test passed."))


class StyleGuide(object):
    """Initialize a PEP-8 instance with few options."""

    def __init__(self, *args, **kwargs):
        # build options from the command line
        parse_argv = kwargs.pop('parse_argv', False)
        config_file = kwargs.pop('config_file', None)
        options, self.paths = process_options(parse_argv=parse_argv,
                                              config_file=config_file)
        if args or kwargs:
            # build options from dict
            options_dict = dict(*args, **kwargs)
            options.__dict__.update(options_dict)
            if 'paths' in options_dict:
                self.paths = options_dict['paths']

        self.runner = self.input_file
        self.options = options

        if not options.reporter:
            options.reporter = BaseReport if options.quiet else StandardReport

        for index, value in enumerate(options.exclude):
            options.exclude[index] = value.rstrip('/')
        # Ignore all checks which are not explicitly selected
        options.select = tuple(options.select or ())
        options.ignore = tuple(options.ignore or options.select and ('',))
        options.benchmark_keys = BENCHMARK_KEYS[:]
        options.ignore_code = self.ignore_code
        options.physical_checks = self.get_checks('physical_line')
        options.logical_checks = self.get_checks('logical_line')
        self.init_report()

    def init_report(self, reporter=None):
        """Initialize the report instance."""
        self.options.report = (reporter or self.options.reporter)(self.options)
        return self.options.report

    def check_files(self, paths=None):
        """Run all checks on the paths."""
        if paths is None:
            paths = self.paths
        report = self.options.report
        runner = self.runner
        report.start()
        for path in paths:
            if os.path.isdir(path):
                self.input_dir(path)
            elif not self.excluded(path):
                runner(path)
        report.stop()
        return report

    def input_file(self, filename, lines=None, expected=None, line_offset=0):
        """Run all checks on a Python source file."""
        if self.options.verbose:
            print(('checking %s' % filename))
        fchecker = Checker(filename, lines=lines, options=self.options)
        return fchecker.check_all(expected=expected, line_offset=line_offset)

    def input_dir(self, dirname):
        """Check all files in this directory and all subdirectories."""
        dirname = dirname.rstrip('/')
        if self.excluded(dirname):
            return 0
        counters = self.options.report.counters
        verbose = self.options.verbose
        filepatterns = self.options.filename
        runner = self.runner
        for root, dirs, files in os.walk(dirname):
            if verbose:
                print(('directory ' + root))
            counters['directories'] += 1
            for subdir in sorted(dirs):
                if self.excluded(subdir):
                    dirs.remove(subdir)
            for filename in sorted(files):
                # contain a pattern that matches?
                if ((filename_match(filename, filepatterns) and
                     not self.excluded(filename))):
                    runner(os.path.join(root, filename))

    def excluded(self, filename):
        """
        Check if options.exclude contains a pattern that matches filename.
        """
        basename = os.path.basename(filename)
        return filename_match(basename, self.options.exclude, default=False)

    def ignore_code(self, code):
        """
        Check if the error code should be ignored.

        If 'options.select' contains a prefix of the error code,
        return False.  Else, if 'options.ignore' contains a prefix of
        the error code, return True.
        """
        return (code.startswith(self.options.ignore) and
                not code.startswith(self.options.select))

    def get_checks(self, argument_name):
        """
        Find all globally visible functions where the first argument name
        starts with argument_name and which contain selected tests.
        """
        checks = []
        for name, codes, function, args in find_checks(argument_name):
            if any(not (code and self.ignore_code(code)) for code in codes):
                checks.append((name, function, args))
        return sorted(checks)


def init_tests(pep8style):
    """
    Initialize testing framework.

    A test file can provide many tests.  Each test starts with a
    declaration.  This declaration is a single line starting with '#:'.
    It declares codes of expected failures, separated by spaces or 'Okay'
    if no failure is expected.
    If the file does not contain such declaration, it should pass all
    tests.  If the declaration is empty, following lines are not checked,
    until next declaration.

    Examples:

     * Only E224 and W701 are expected:         #: E224 W701
     * Following example is conform:            #: Okay
     * Don't check these lines:                 #:
    """
    report = pep8style.init_report(TestReport)
    runner = pep8style.input_file

    def run_tests(filename):
        """Run all the tests from a file."""
        lines = readlines(filename) + ['#:\n']
        line_offset = 0
        codes = ['Okay']
        testcase = []
        count_files = report.counters['files']
        for index, line in enumerate(lines):
            if not line.startswith('#:'):
                if codes:
                    # Collect the lines of the test case
                    testcase.append(line)
                continue
            if codes and index:
                codes = [c for c in codes if c != 'Okay']
                # Run the checker
                runner(filename, testcase, expected=codes,
                       line_offset=line_offset)
            # output the real line numbers
            line_offset = index + 1
            # configure the expected errors
            codes = line.split()[1:]
            # empty the test case buffer
            del testcase[:]
        report.counters['files'] = count_files + 1
        return report.counters['failed tests']

    pep8style.runner = run_tests


def selftest(options):
    """
    Test all check functions with test cases in docstrings.
    """
    count_failed = count_all = 0
    report = BaseReport(options)
    counters = report.counters
    checks = options.physical_checks + options.logical_checks
    for name, check, argument_names in checks:
        for line in check.__doc__.splitlines():
            line = line.lstrip()
            match = SELFTEST_REGEX.match(line)
            if match is None:
                continue
            code, source = match.groups()
            checker = Checker(None, options=options, report=report)
            for part in source.split(r'\n'):
                part = part.replace(r'\t', '\t')
                part = part.replace(r'\s', ' ')
                checker.lines.append(part + '\n')
            checker.check_all()
            error = None
            if code == 'Okay':
                if len(counters) > len(options.benchmark_keys):
                    codes = [key for key in counters
                             if key not in options.benchmark_keys]
                    error = "incorrectly found %s" % ', '.join(codes)
            elif not counters.get(code):
                error = "failed to find %s" % code
            # Keep showing errors for multiple tests
            for key in set(counters) - set(options.benchmark_keys):
                del counters[key]
            report.messages = {}
            count_all += 1
            if not error:
                if options.verbose:
                    print(("%s: %s" % (code, source)))
            else:
                count_failed += 1
                print(("%s: %s:" % (__file__, error)))
                for line in checker.lines:
                    print((line.rstrip()))
    return count_failed, count_all


def read_config(options, args, arglist, parser):
    """Read both user configuration and local configuration."""
    config = RawConfigParser()

    user_conf = options.config
    if user_conf and os.path.isfile(user_conf):
        if options.verbose:
            print(('user configuration: %s' % user_conf))
        config.read(user_conf)

    parent = tail = args and os.path.abspath(os.path.commonprefix(args))
    while tail:
        local_conf = os.path.join(parent, '.pep8')
        if os.path.isfile(local_conf):
            if options.verbose:
                print(('local configuration: %s' % local_conf))
            config.read(local_conf)
            break
        parent, tail = os.path.split(parent)

    if config.has_section('pep8'):
        option_list = dict([(o.dest, o.type or o.action)
                            for o in parser.option_list])

        # First, read the default values
        new_options, _ = parser.parse_args([])

        # Second, parse the configuration
        for opt in config.options('pep8'):
            if options.verbose > 1:
                print(('  %s = %s' % (opt, config.get('pep8', opt))))
            if opt.replace('_', '-') not in parser.config_options:
                print(('Unknown option: \'%s\'\n  not in [%s]' %
                      (opt, ' '.join(parser.config_options))))
                sys.exit(1)
            normalized_opt = opt.replace('-', '_')
            opt_type = option_list[normalized_opt]
            if opt_type in ('int', 'count'):
                value = config.getint('pep8', opt)
            elif opt_type == 'string':
                value = config.get('pep8', opt)
            else:
                assert opt_type in ('store_true', 'store_false')
                value = config.getboolean('pep8', opt)
            setattr(new_options, normalized_opt, value)

        # Third, overwrite with the command-line options
        options, _ = parser.parse_args(arglist, values=new_options)

    return options


def process_options(arglist=None, parse_argv=False, config_file=None):
    """Process options passed either via arglist or via command line args."""
    if not arglist and not parse_argv:
        # Don't read the command line if the module is used as a library.
        arglist = []
    if config_file is True:
        config_file = DEFAULT_CONFIG
    parser = OptionParser(version=__version__,
                          usage="%prog [options] input ...")
    parser.config_options = [
        'exclude', 'filename', 'select', 'ignore', 'max-line-length', 'count',
        'format', 'quiet', 'show-pep8', 'show-source', 'statistics', 'verbose']
    parser.add_option('-v', '--verbose', default=0, action='count',
                      help="print status messages, or debug with -vv")
    parser.add_option('-q', '--quiet', default=0, action='count',
                      help="report only file names, or nothing with -qq")
    parser.add_option('-r', '--repeat', default=True, action='store_true',
                      help="(obsolete) show all occurrences of the same error")
    parser.add_option('--first', action='store_false', dest='repeat',
                      help="show first occurrence of each error")
    parser.add_option('--exclude', metavar='patterns', default=DEFAULT_EXCLUDE,
                      help="exclude files or directories which match these "
                           "comma separated patterns (default: %default)")
    parser.add_option('--filename', metavar='patterns', default='*.py',
                      help="when parsing directories, only check filenames "
                           "matching these comma separated patterns "
                           "(default: %default)")
    parser.add_option('--select', metavar='errors', default='',
                      help="select errors and warnings (e.g. E,W6)")
    parser.add_option('--ignore', metavar='errors', default='',
                      help="skip errors and warnings (e.g. E4,W)")
    parser.add_option('--show-source', action='store_true',
                      help="show source code for each error")
    parser.add_option('--show-pep8', action='store_true',
                      help="show text of PEP 8 for each error "
                           "(implies --first)")
    parser.add_option('--statistics', action='store_true',
                      help="count errors and warnings")
    parser.add_option('--count', action='store_true',
                      help="print total number of errors and warnings "
                           "to standard error and set exit code to 1 if "
                           "total is not null")
    parser.add_option('--max-line-length', type='int', metavar='n',
                      default=MAX_LINE_LENGTH,
                      help="set maximum allowed line length "
                           "(default: %default)")
    parser.add_option('--format', metavar='format', default='default',
                      help="set the error format [default|pylint|<custom>]")
    parser.add_option('--diff', action='store_true',
                      help="report only lines changed according to the "
                           "unified diff received on STDIN")
    group = parser.add_option_group("Testing Options")
    group.add_option('--testsuite', metavar='dir',
                     help="run regression tests from dir")
    group.add_option('--doctest', action='store_true',
                     help="run doctest on myself")
    group.add_option('--benchmark', action='store_true',
                     help="measure processing speed")
    group = parser.add_option_group("Configuration", description=(
        "The project options are read from the [pep8] section of the .pep8 "
        "file located in any parent folder of the path(s) being processed. "
        "Allowed options are: %s." % ', '.join(parser.config_options)))
    group.add_option('--config', metavar='path', default=config_file,
                     help="config file location (default: %default)")

    options, args = parser.parse_args(arglist)
    options.reporter = None

    if options.testsuite:
        args.append(options.testsuite)
    elif not options.doctest:
        if parse_argv and not args:
            if os.path.exists('.pep8') or options.diff:
                args = ['.']
            else:
                parser.error('input not specified')
        options = read_config(options, args, arglist, parser)
        options.reporter = parse_argv and options.quiet == 1 and FileReport

    if options.filename:
        options.filename = options.filename.split(',')
    options.exclude = options.exclude.split(',')
    if options.select:
        options.select = options.select.split(',')
    if options.ignore:
        options.ignore = options.ignore.split(',')
    elif not (options.select or
              options.testsuite or options.doctest) and DEFAULT_IGNORE:
        # The default choice: ignore controversial checks
        # (for doctest and testsuite, all checks are required)
        options.ignore = DEFAULT_IGNORE.split(',')

    if options.diff:
        options.reporter = DiffReport
        stdin = stdin_get_value()
        options.selected_lines = parse_udiff(stdin, options.filename, args[0])
        args = sorted(options.selected_lines)

    return options, args


def _main():
    """Parse options and run checks on Python source."""
    pep8style = StyleGuide(parse_argv=True, config_file=True)
    options = pep8style.options
    if options.doctest:
        import doctest
        fail_d, done_d = doctest.testmod(report=False, verbose=options.verbose)
        fail_s, done_s = selftest(options)
        count_failed = fail_s + fail_d
        if not options.quiet:
            count_passed = done_d + done_s - count_failed
            print(("%d passed and %d failed." % (count_passed, count_failed)))
            print(("Test failed." if count_failed else "Test passed."))
        if count_failed:
            sys.exit(1)
    if options.testsuite:
        init_tests(pep8style)
    report = pep8style.check_files()
    if options.statistics:
        report.print_statistics()
    if options.benchmark:
        report.print_benchmark()
    if options.testsuite and not options.quiet:
        report.print_results()
    if report.total_errors:
        if options.count:
            sys.stderr.write(str(report.total_errors) + '\n')
        sys.exit(1)


if __name__ == '__main__':
    _main()

########NEW FILE########
__FILENAME__ = pep8kivy
import sys
from os import walk
from os.path import isdir, join, abspath, dirname
import pep8
import time

htmlmode = False

pep8_ignores = (
    'E125',  # continuation line does not
             # distinguish itself from next logical line
    'E126',  # continuation line over-indented for hanging indent
    'E127',  # continuation line over-indented for visual indent
    'E128')  # continuation line under-indented for visual indent

class KivyStyleChecker(pep8.Checker):

    def __init__(self, filename):
        pep8.Checker.__init__(self, filename, ignore=pep8_ignores)

    def report_error(self, line_number, offset, text, check):
        if htmlmode is False:
            return pep8.Checker.report_error(self,
                line_number, offset, text, check)

        # html generation
        print('<tr><td>{0}</td><td>{1}</td></tr>'.format(line_number, text))


if __name__ == '__main__':

    def usage():
        print('Usage: python pep8kivy.py [-html] <file_or_folder_to_check>*')
        print('Folders will be checked recursively.')
        sys.exit(1)

    if len(sys.argv) < 2:
        usage()
    if sys.argv[1] == '-html':
        if len(sys.argv) < 3:
            usage()
        else:
            htmlmode = True
            targets = sys.argv[-1].split()
    elif sys.argv == 2:
        targets = sys.argv[-1]
    else:
        targets = sys.argv[-1].split()

    def check(fn):
        try:
            checker = KivyStyleChecker(fn)
        except IOError:
            # File couldn't be opened, so was deleted apparently.
            # Don't check deleted files.
            return 0
        return checker.check_all()

    errors = 0
    exclude_dirs = ['/lib', '/coverage', '/pep8', '/doc']
    exclude_files = ['kivy/gesture.py', 'osx/build.py', 'win32/build.py',
                     'kivy/tools/stub-gl-debug.py',
                     'kivy/modules/webdebugger.py']
    for target in targets:
        if isdir(target):
            if htmlmode:
                path = join(dirname(abspath(__file__)), 'pep8base.html')
                print(open(path, 'r').read())
                print('''<p>Generated: %s</p><table>''' % (time.strftime('%c')))

            for dirpath, dirnames, filenames in walk(target):
                cont = False
                for pat in exclude_dirs:
                    if pat in dirpath:
                        cont = True
                        break
                if cont:
                    continue
                for filename in filenames:
                    if not filename.endswith('.py'):
                        continue
                    cont = False
                    complete_filename = join(dirpath, filename)
                    for pat in exclude_files:
                        if complete_filename.endswith(pat):
                            cont = True
                    if cont:
                        continue

                    if htmlmode:
                        print('<tr><th colspan="2">%s</td></tr>' \
                             % complete_filename)
                    errors += check(complete_filename)

            if htmlmode:
                print('</div></div></table></body></html>')

        else:
            # Got a single file to check
            for pat in exclude_dirs + exclude_files:
                if pat in target:
                    break
            else:
                if target.endswith('.py'):
                    errors += check(target)

    # If errors is 0 we return with 0. That's just fine.
    sys.exit(errors)

########NEW FILE########
