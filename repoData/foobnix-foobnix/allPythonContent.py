__FILENAME__ = dm
'''
Created on Oct 26, 2010

@author: ivan
'''

from gi.repository import Gtk
from gi.repository import Notify
import time
import thread
import logging
import threading

from foobnix.fc.fc import FC
from foobnix.dm.dm_dowloader import Dowloader
from foobnix.helpers.toolbar import MyToolbar
from foobnix.gui.model import FDModel, FModel
from foobnix.helpers.window import ChildTopWindow
from foobnix.preferences.configs import CONFIG_OTHER
from foobnix.helpers.dialog_entry import directory_chooser_dialog
from foobnix.gui.treeview.dm_tree import DownloadManagerTreeControl
from foobnix.gui.treeview.dm_nav_tree import DMNavigationTreeControl
from foobnix.util.const import DOWNLOAD_STATUS_INACTIVE, DOWNLOAD_STATUS_ACTIVE, \
    DOWNLOAD_STATUS_COMPLETED, DOWNLOAD_STATUS_DOWNLOADING, DOWNLOAD_STATUS_ALL, \
    DOWNLOAD_STATUS_STOP, DOWNLOAD_STATUS_ERROR
from foobnix.util import analytics


class DMControls(MyToolbar):
    def __init__(self, controls, dm_tree): 
        MyToolbar.__init__(self)   
        
        self.add_button(_("Preferences"), Gtk.STOCK_PREFERENCES, controls.preferences.show, CONFIG_OTHER)
        self.add_separator()   
        self.add_button(_("Start Downloading"), Gtk.STOCK_MEDIA_PLAY, dm_tree.update_status_for_selected, DOWNLOAD_STATUS_ACTIVE)
        self.add_button(_("Stop Downloading"), Gtk.STOCK_MEDIA_PAUSE, dm_tree.update_status_for_selected, DOWNLOAD_STATUS_STOP)
        self.add_separator()   
        #self.add_button("Start All", Gtk.STOCK_MEDIA_FORWARD, dm_tree.update_status_for_all, DOWNLOAD_STATUS_ACTIVE)
        #self.add_button("Stop All", Gtk.STOCK_STOP, dm_tree.update_status_for_all, DOWNLOAD_STATUS_STOP)
        #self.add_separator()   
        self.add_button("Delete", Gtk.STOCK_DELETE, dm_tree.delete_all_selected, None)
        #self.add_button("Delete All", Gtk.STOCK_CLEAR, dm_tree.delete_all, None)
        #self.add_separator()
        
    def on_load(self): pass
    def on_save(self): pass


class DM(ChildTopWindow):
    def __init__(self, controls):
        self.controls = controls        
        ChildTopWindow.__init__(self, _("Download Manager"))
        self.set_resizable(True)
        self.set_default_size(900, 700)
        
        vbox = Gtk.VBox(False, 0)
        #paned = Gtk.HPaned()
        #paned.set_position(200)
        
        self.navigation = DMNavigationTreeControl()
            
        self.navigation.append(FDModel("All").add_artist("All").add_status(DOWNLOAD_STATUS_ALL))
        self.navigation.append(FDModel("Downloading").add_artist("Downloading").add_status(DOWNLOAD_STATUS_DOWNLOADING))
        self.navigation.append(FDModel("Completed").add_artist("Completed").add_status(DOWNLOAD_STATUS_COMPLETED))
        self.navigation.append(FDModel("Active").add_artist("Active").add_status(DOWNLOAD_STATUS_ACTIVE))
        self.navigation.append(FDModel("Inactive").add_artist("Inactive").add_status(DOWNLOAD_STATUS_INACTIVE))
        
        self.dm_list = DownloadManagerTreeControl(self.navigation)
        self.navigation.dm_list = self.dm_list
        #paned.pack1(self.navigation.scroll)
        #paned.pack2(self.dm_list.scroll)
        playback = DMControls(self.controls, self.dm_list)
        
        vbox.pack_start(playback, False, True, 0)
        #vbox.pack_start(paned, True, True)
        vbox.pack_start(self.dm_list.scroll, True, True, 0)
                       
        self.add(vbox)
        thread.start_new_thread(self.dowloader, (self.dm_list,))

    def demo_tasks(self):
        self.append_task(FModel("Madonna - Sorry"))
        self.append_task(FModel("Madonna - Frozen"))
        self.append_task(FModel("Madonna - Sorry"))
        self.append_task(FModel("Madonna - Frozen"))
        self.append_task(FModel("Madonna - Sorry"))
        self.append_task(FModel("Madonna - Frozen"))
        
        self.append_task(FModel("Madonna - Sorry"))
        self.append_task(FModel("Madonna - Frozen"))
        self.append_task(FModel("Madonna - Sorry"))
        self.append_task(FModel("Madonna - Frozen"))
        self.append_task(FModel("Madonna - Sorry"))
        self.append_task(FModel("Madonna - Frozen"))
        self.append_task(FModel("Madonna - Sorry"))
        self.append_task(FModel("Madonna - Frozen"))

    def show(self):
        self.show_all()
        analytics.action("DM")
    
    def append_task(self, bean, save_to=None):
        """download only remote files"""
        #if bean.path and not bean.path.startswith("http"):
        #    return 
          
        bean.status = DOWNLOAD_STATUS_ACTIVE
        if save_to:
            bean.save_to = save_to
            
        self.dm_list.append(bean)

        if FC().notifier:
            self.to_notify(bean.get_display_name())

        logging.debug("Begin download %s" % bean)

    def to_notify(self, notify_text):
        notification = Notify.Notification.new("Downloading:", notify_text, "")
        notification.set_urgency(Notify.Urgency.LOW)
        notification.set_timeout(FC().notify_time)
        
        notification.show()

    def append_tasks_with_dialog(self, beans):
        paths = directory_chooser_dialog(_("Choose Folder"), FC().last_dir)
        if paths:
            self.append_tasks(beans, paths[0])
    
    def append_tasks(self, beans, save_to=None):
        self.show()
        for bean in beans:
            self.append_task(bean, save_to)
    
    def dowloader(self, dm_list):
        semaphore = threading.Semaphore(FC().amount_dm_threads)
        while True:
            #self.navigation.use_filter()
            semaphore.acquire()
            bean = dm_list.get_next_bean_to_dowload()            
            if bean:
                if not bean.path or not self.controls.check_path(bean.path):                
                    vk = self.controls.vk_service.find_one_track(bean.get_display_name())
                    if not vk:
                        bean.status = DOWNLOAD_STATUS_ERROR
                        dm_list.update_bean_info(bean)
                        logging.debug("Source for song not found" + bean.text)
                        semaphore.release()
                        continue
                        
                    bean.path = vk.path
                         
                def notify_finish():
                    self.navigation.update_statistics()                    
                    semaphore.release()
                    
                thread = Dowloader(dm_list.update_bean_info, bean, notify_finish)                
                thread.start()
            else:
                time.sleep(1)
                semaphore.release()
                
if __name__ == '__main__':
    class FakePref():
            def show(self):
                pass
    class Fake():        
        def __init__(self):
            self.preferences = FakePref()
        def show(self):
            pass
        
    controls = Fake()
    dm = DM(controls)
    dm.show()            
    Gtk.main()

########NEW FILE########
__FILENAME__ = dm_dowloader
'''
Created on Oct 27, 2010

@author: ivan
'''

from __future__ import with_statement

import os
import time
import logging
import threading
from foobnix.fc.fc import FC
from urllib import FancyURLopener
from foobnix.util.time_utils import size2text
from foobnix.util.file_utils import get_file_extension
from foobnix.util.bean_utils import get_bean_download_path
from foobnix.util.const import DOWNLOAD_STATUS_COMPLETED, \
    DOWNLOAD_STATUS_DOWNLOADING, DOWNLOAD_STATUS_INACTIVE


class Dowloader(threading.Thread):
    def __init__(self, update, bean, notify_finish):
        threading.Thread.__init__(self)
        self.update = update
        self.bean = bean
        self.notify_finish = notify_finish
    
    def run(self):
        try:
            self.download()
        except Exception, e:
            self.bean.status = DOWNLOAD_STATUS_INACTIVE
            self.update(self.bean)
            logging.error(e)
        finally:
            self.notify_finish() 
    
    def download(self):
        bean = self.bean 
        update = self.update 
        if not bean or not bean.path:            
            return None
         
        opener = FancyURLopener()
        remote = opener.open(bean.path)
        remote_size = 0
        
        if "Content-Length" in remote.headers:
            remote_size = int(remote.headers["Content-Length"])
            bean.size = size2text(remote_size) 
        
        block_size = 4096
        block_count = 0
        
        ext = get_file_extension(bean.path)
        
        path = FC().online_save_to_folder
        if not os.path.isdir(path):
            os.makedirs(path)
            
        if bean.save_to:
            to_file = os.path.join(bean.save_to, bean.text + ".mp3") 
        else:            
            to_file = get_bean_download_path(bean, FC().online_save_to_folder)
        
        if not os.path.exists(os.path.dirname(to_file)):
                os.makedirs(os.path.dirname(to_file))        
        
        to_file_tmp = to_file + ".tmp"
        
        if os.path.exists(to_file_tmp):
            bean.status = DOWNLOAD_STATUS_INACTIVE
            bean.to_file = to_file
            update(bean)
            return None
        
        if os.path.exists(to_file):
            bean.status = DOWNLOAD_STATUS_COMPLETED
            bean.to_file = to_file
            update(bean)
            return None
        
        bean.save_to = to_file        
        with file(to_file_tmp, "wb") as tmp_file:
            data = True
            
            """begin download"""
            self.bean.status = DOWNLOAD_STATUS_DOWNLOADING
            self.bean.path = to_file
            self.update(self.bean)

            while data:
                data = remote.read(block_size)
                if data:
                    block_count += 1
                    tmp_file.write(data)
                    #time.sleep(0.1)
                    persent = block_count * block_size * 100.0 / remote_size
                    if block_count % 50 == 0:
                        bean.persent = persent
                        update(bean)
        time.sleep(0.5)           
        """update file info on finish"""                    
        logging.debug("rename %s - %s" % (to_file_tmp, to_file))
        os.rename(to_file_tmp, to_file)
        bean.status = DOWNLOAD_STATUS_COMPLETED
        bean.to_file = to_file
        bean.persent = 100
        update(bean)

########NEW FILE########
__FILENAME__ = eq_controller
#-*- coding: utf-8 -*-
'''
Created on 24 окт. 2010

@author: ivan
'''

import logging

from foobnix.fc.fc import FC
from foobnix.util import analytics
from foobnix.eq.eq_gui import EqWindow
from foobnix.gui.state import LoadSave
from foobnix.gui.model.signal import FControl
from foobnix.gui.model.eq_model import EqModel


class EqController(FControl, LoadSave):
    def __init__(self, controls):
        FControl.__init__(self, controls)
        LoadSave.__init__(self)

        self.eq_view = EqWindow(controls, self.on_eq_chaged)
        self.eq_view.hide()

    def show(self):
        self.eq_view.show_all()
        analytics.action("EqController")

    def hide(self):
        self.eq_view.hide()

    def get_preamp(self):
        return self.eq_view.get_active_values()[0]

    def get_bands(self):
        return self.eq_view.get_active_values()[1:]

    def on_eq_chaged(self):
        pre = self.eq_view.get_active_values()[0]
        self.controls.media_engine.set_all_bands(pre, self.eq_view.get_active_values()[1:])

    def on_load(self):
        logging.debug("FC().eq_presets %s" % FC().eq_presets)
        if FC().eq_presets:
            self.eq_view.append_all_models(FC().eq_presets)
        else:
            self.eq_view.append_all_models(self.default_models())

        self.eq_view.default_models = self.default_models()
        self.eq_view.set_active(FC().eq_presets_default)

        logging.debug("default_models %s" % self.default_models())
        logging.debug("FC().eq_presets_default %s" % FC().eq_presets_default)

        self.eq_view.on_load()

    def on_save(self):
        pass

    def default_models(self):
        models = []
        models.append(EqModel("CUSTOM", "Custom", 0, [0, 0, 0, 0, 0, 0, 0, 0, 0, 0]))
        models.append(EqModel("DEFAULT", "Default", 0, [0, 0, 0, 0, 0, 0, 0, 0, 0, 0]))
        models.append(EqModel("CLASSICAL", "Classical", 0, [0, 0, 0, 0, 0, 0, -7.2, -7.2, -7.2, -9.6]))
        models.append(EqModel("CLUB", "Club", 0, [ 0, 0, 8, 5.6, 5.6, 5.6, 3.2, 0, 0, 0]))
        models.append(EqModel("DANCE", "Dance", 0, [ 9.6, 7.2, 2.4, 0, 0, -5.6, -7.2, -7.2, 0, 0]))
        models.append(EqModel("FULL BASS", "Full Bass", 0, [ -8, 9.6, 9.6, 5.6, 1.6, -4, -8, -10.4, -11.2, -11.2]))
        models.append(EqModel("FULL BASS AND TREBLE", "Full Bass and Treble", 0, [ 7.2, 5.6, 0, -7.2, -4.8, 1.6, 8, 11.2, 12, 12]))
        models.append(EqModel("FULL TREBLE", "Full Treble", 0, [ -9.6, -9.6, -9.6, -4, 2.4, 11.2, 16, 16, 16, 16.8]))
        models.append(EqModel("LAPTOP SPEAKERS", "Laptop Speakers and Headphones", 0, [ 4.8, 11.2, 5.6, -3.2, -2.4, 1.6, 4.8, 9.6, 11.9, 11.9]))
        models.append(EqModel("LARGE HALL", "Large Hall", 0, [ 10.4, 10.4, 5.6, 5.6, 0, -4.8, -4.8, -4.8, 0, 0]))
        models.append(EqModel("LIVE", "Live", 0, [ -4.8, 0, 4, 5.6, 5.6, 5.6, 4, 2.4, 2.4, 2.4]))
        models.append(EqModel("PARTY", "Party", 0, [ 7.2, 7.2, 0, 0, 0, 0, 0, 0, 7.2, 7.2]))
        models.append(EqModel("POP", "Pop", 0, [ -1.6, 4.8, 7.2, 8, 5.6, 0, -2.4, -2.4, -1.6, -1.6]))
        models.append(EqModel("REGGAE", "Reggae", 0, [ 0, 0, 0, -5.6, 0, 6.4, 6.4, 0, 0, 0]))
        models.append(EqModel("ROCK", "Rock", 0, [ 8, 4.8, -5.6, -8, -3.2, 4, 8.8, 11.2, 11.2, 11.2]))
        models.append(EqModel("SKA", "Ska", 0, [ -2.4, -4.8, -4, 0, 4, 5.6, 8.8, 9.6, 11.2, 9.6]))
        models.append(EqModel("SOFT", "Soft", 0, [ 4.8, 1.6, 0, -2.4, 0, 4, 8, 9.6, 11.2, 12]))
        models.append(EqModel("SOFT ROCK", "Soft Rock", 0, [ 4, 4, 2.4, 0, -4, -5.6, -3.2, 0, 2.4, 8.8]))
        models.append(EqModel("TECHNO", "Techno", 0, [ 8, 5.6, 0, -5.6, -4.8, 0, 8, 9.6, 9.6, 8.8]))
        return models


########NEW FILE########
__FILENAME__ = eq_gui
#-*- coding: utf-8 -*-
'''
Created on Sep 8, 2010

@author: ivan
'''

from gi.repository import Gtk
import copy
import logging

from foobnix.fc.fc import FC
from foobnix.helpers.menu import Popup
from foobnix.gui.model.signal import FControl
from foobnix.gui.model.eq_model import EqModel
from foobnix.helpers.window import ChildTopWindow
from foobnix.helpers.my_widgets import ImageButton
from foobnix.util.mouse_utils import is_rigth_click
from foobnix.util.const import EQUALIZER_LABLES, STATE_PLAY


def label(): 
    label = Gtk.Label("–")
    label.show()
    return label

def empty(): 
    label = Gtk.Label(" ")
    label.show()
    return label

def text(text): 
    label = Gtk.Label(text)
    label.show()
    return label

class EqWindow(ChildTopWindow, FControl):
    
    def __init__(self, controls, callback):
        self.callback = callback
        FControl.__init__(self, controls)        
        ChildTopWindow.__init__(self, _("Equalizer"))

        self.combo = Gtk.ComboBoxText.new_with_entry()
        self.combo.connect("changed", self.on_combo_change)

        self.eq_lines = []
        for label in EQUALIZER_LABLES:
            self.eq_lines.append(EqLine(label, self.on_callback))
        
        lbox = Gtk.VBox(False, 0)
        lbox.show()
        
        lbox.pack_start(self.top_row(), False, False, 0)
        lbox.pack_start(self.middle_lines_box(), False, False, 0)
            
        self.add(lbox)
        
        self.models = []
        self.default_models = []
                
    def on_restore_defaults(self, *a):
        self.models = []
        num = self.combo.get_active() 
        self.combo.get_model().clear()  
        self.append_all_models(copy.deepcopy(self.default_models))
        self.combo.set_active(num)
        self.on_combo_change()
        
    def on_button_press(self, w, e):
        if is_rigth_click(e):
            menu = Popup()
            menu.add_item('Restore Defaults', Gtk.STOCK_REFRESH, None)
            menu.show(e)
    
    def on_callback(self):
        pre = self.eq_lines[0].get_value()
        if float(pre) >= 0:
            pre = "+" + pre
            
        self.db_text.set_text(pre + "db")
        self.callback()
    
    def set_custom_title_and_button_label(self):
        status = _("Disabled")
        self.on.set_label(_("Enable EQ")) 
        if FC().is_eq_enable:
            status = _("Enabled")
            self.on.set_label(_("Disable EQ"))       
        self.set_title(_("Equalizer %s") % status)

    def on_enable_eq(self, w):
        FC().is_eq_enable = w.get_active()
        self.set_custom_title_and_button_label()
        self.controls.media_engine.realign_eq()
        #if self.controls.media_engine.get_state() == STATE_PLAY:
        #    self.controls.state_stop(remember_position=True)
        #    self.controls.state_play(under_pointer_icon=True)
            
    def on_save(self, *args):
        text = self.combo.get_active_text()
        
        logging.debug("text %s "%text)
        
        find = False
        text_id = None 
        for model in self.models:
            if model.name == text:               
                values = self.get_active_values()[1:]
                logging.debug("values %s " % values)
                model.set_values(values)
                model.set_preamp(self.get_active_values()[0])
                find = True
                text_id = model.id
                logging.debug("find %s "%model.id)
                break
        
        if not find:
            self.models.append(EqModel(text, text, self.get_active_values()[0], self.get_active_values()[1:]))
            self.combo.append_text(text)
            text_id = text
            logging.debug("not find %s "%text)
            
        FC().eq_presets_default =  text_id
        FC().eq_presets =  self.models
        logging.debug("SAVE %s "%text_id)   
        FC().save()
        
    def get_active_values(self):
        result = []
        for line in self.eq_lines:
            result.append(float(line.get_value()))
        
        return result

    def notify_chage_eq_line(self):
        self.get_active_values()    
    
    def append_all_models(self, models):
        self.models = models
        self.populate(models)
    
    def set_active(self, model_id):
        for i, c_model in enumerate(self.models):
            if c_model.id == model_id:
                self.combo.set_active(i)
                return
        
    def on_combo_change(self, *a):        
        num = self.combo.get_active()
        if num >= 0:
            model = self.models[num]
            self.set_all_eq_span_values([model.preamp] + model.values)
            self.callback()
        
    def populate(self, models):
        for model in models:
            self.combo.append_text(model.name)
    
    def set_active_preset(self, name):        
        self.presets_cache[name]
    
    def top_row(self):
        
        box = Gtk.HBox(False, 0)
        box.show()
        
        self.on = Gtk.ToggleButton(_("Enable EQ"))
        self.on.set_tooltip_text(_("To enable EQ set ON"))
        self.on.connect("toggled", self.on_enable_eq)
        #on.set_size_request(30,-1)        
        self.on.show()
        
        auto = Gtk.ToggleButton(_("Auto"))
        #auto.set_size_request(50,-1)
        auto.show()
        
        empt = empty()
        empt.set_size_request(65, -1)
        #auto.set_size_request(50,-1)
        auto.show()
        #combo = Gtk.ComboBoxEntry()
        #self.combo.set_size_request(240, -1)
        self.combo.show()
        
        save = Gtk.Button(_("Save"))
        save.connect("clicked", self.on_save)
        
        save.show()
                
        resButton = ImageButton(Gtk.STOCK_REFRESH)
        resButton.connect("clicked", self.on_restore_defaults)
        resButton.set_tooltip_text(_("Restore defaults presets"))
        
        box.pack_start(self.on, False, False, 0)
        #box.pack_start(auto, False, True, 0)
        box.pack_start(empt, False, True, 0)        
        box.pack_start(self.combo, False, True, 0)        
        box.pack_start(save, False, True, 0)
        box.pack_start(Gtk.Label(), True, True, 0)
        box.pack_start(resButton, False, True, 0)
        
        return box
    
    def dash_line(self):
        lables = Gtk.VBox(False, 0)
        lables.show()
        lables.pack_start(label(), False, False, 0)
        lables.pack_start(label(), True, False, 0)
        lables.pack_start(label(), False, False, 0)
        lables.pack_start(empty(), False, False, 0)
        return lables
    
    def db_line(self):
        lables = Gtk.VBox(False, 0)
        lables.show()
        lables.pack_start(text("+12db"), False, False, 0)
        
        self.db_text = text("0db")
        
        lables.pack_start(self.db_text, True, False, 0)
        lables.pack_start(text("-12db"), False, False, 0)
        lables.pack_start(empty(), False, False, 0)
        return lables
    
    def empty_line(self):
        lables = Gtk.VBox(False, 0)
        lables.show()
        lables.pack_start(empty(), False, False, 0)
        lables.pack_start(empty(), True, False, 0)
        lables.pack_start(empty(), False, False, 0)
        lables.pack_start(empty(), False, False, 0)
        return lables
                
    def middle_lines_box(self):         
        lines_box = Gtk.HBox(False, 0)
        lines_box.show()
        
        eq_iter = iter(self.eq_lines)
        
        lines_box.pack_start(self.dash_line(), False, False, 0)
        lines_box.pack_start(eq_iter.next(), False, False, 0)
        lines_box.pack_start(self.dash_line(), False, False, 0)
        
        lines_box.pack_start(self.empty_line(), False, False, 0)
        lines_box.pack_start(self.db_line(), False, False, 0)
        lines_box.pack_start(self.empty_line(), False, False, 0)
        lines_box.pack_start(self.dash_line(), False, False, 0)
        
        lines_box.pack_start(eq_iter.next(), False, False, 0)
        lines_box.pack_start(self.dash_line(), False, False, 0)
        lines_box.pack_start(eq_iter.next(), False, False, 0)
        lines_box.pack_start(self.dash_line(), False, False, 0)
        lines_box.pack_start(eq_iter.next(), False, False, 0)
        lines_box.pack_start(self.dash_line(), False, False, 0)
        lines_box.pack_start(eq_iter.next(), False, False, 0)
        lines_box.pack_start(self.dash_line(), False, False, 0)
        lines_box.pack_start(eq_iter.next(), False, False, 0)
        lines_box.pack_start(self.dash_line(), False, False, 0)
        lines_box.pack_start(eq_iter.next(), False, False, 0)
        lines_box.pack_start(self.dash_line(), False, False, 0)
        lines_box.pack_start(eq_iter.next(), False, False, 0)
        lines_box.pack_start(self.dash_line(), False, False, 0)
        lines_box.pack_start(eq_iter.next(), False, False, 0)
        lines_box.pack_start(self.dash_line(), False, False, 0)
        lines_box.pack_start(eq_iter.next(), False, False, 0)
        lines_box.pack_start(self.dash_line(), False, False, 0)
        lines_box.pack_start(eq_iter.next(), False, False, 0)
        lines_box.pack_start(self.dash_line(), False, False, 0)
        lines_box.pack_start(self.empty_line(), False, False, 0)
        
        return lines_box
    
    def set_all_eq_span_values(self, values):
        for i, eq_scale in enumerate(self.eq_lines):
            eq_scale.set_value(values[i])
        
    def on_load(self):
        self.on.set_active(FC().is_eq_enable)
        if FC().is_eq_enable:
            self.on.set_label(_("Disable EQ"))
            
class EqLine(Gtk.VBox):
        def __init__(self, text, callback, def_value=0):
            self.callback = callback
            self.text = text
            Gtk.VBox.__init__(self, False, 0)
            self.show()
            
            adjustment = Gtk.Adjustment(value=def_value, lower= -12, upper=12, step_incr=1, page_incr=2, page_size=0)
            self.scale = Gtk.VScale(adjustment=adjustment)
            self.scale.connect("change-value", self.on_change_value)
            self.scale.set_size_request(-1, 140)  
            self.scale.set_draw_value(False)      
            self.scale.set_inverted(True)       
            self.scale.show()
            
            """text under"""
            text = Gtk.Label(text)
            text.show()
            
            self.pack_start(self.scale, False, False, 0)
            self.pack_start(text, False, False, 0)
        
        def on_change_value(self, *args):
            self.callback()
        
        def set_value(self, value):
            self.scale.set_value(value)
        
        def get_value(self):
            return "%.1f" % self.scale.get_value()   

########NEW FILE########
__FILENAME__ = fc
#-*- coding: utf-8 -*-
'''
Created on 23 сент. 2010

@author: ivan
'''

import os

from foobnix.util import const
from foobnix.fc.fc_base import FCBase
from foobnix.fc.fc_cache import FCache
from foobnix.util.singleton import Singleton
from foobnix.util.agent import get_ranmom_agent
from foobnix.fc.fc_helper import FCStates, CONFIG_DIR
from foobnix.util.const import ICON_FOOBNIX, ICON_FOOBNIX_PLAY, \
    ICON_FOOBNIX_PAUSE, ICON_FOOBNIX_STOP, ICON_FOOBNIX_RADIO


CONFIG_FILE = os.path.join(CONFIG_DIR , "foobnix.pkl")
#CONFIG_FILE = os.path.join(CONFIG_DIR , "foobnix_winter.pkl")

"""Foobnix player configuration"""
class FC():
    __metaclass__ = Singleton

    def __init__(self):

        """init default values"""
        self.is_view_info_panel = True
        self.is_view_search_panel = True
        self.is_view_music_tree_panel = True
        self.is_view_coverlyrics_panel = False
        self.is_view_lyric_panel = True
        self.is_view_video_panel = False
        self.is_order_random = False
        self.repeat_state = const.REPEAT_ALL
        self.playlist_type = const.PLAYLIST_TREE

        """player controls"""
        self.volume = 90
        self.temp_volume = self.volume
        self.is_eq_enable = False
        self.eq_presets = None
        self.eq_presets_default = "CUSTOM"

        """VK"""
        self.access_token =  None
        self.user_id =  None
        self.enable_vk_autocomlete = False

        """LastFM"""
        self.search_limit = 50

        """tabs"""
        self.len_of_tab = 30
        self.tab_close_element = "label"
        self.count_of_tabs = 5
        self.tab_position = "top"

        self.update_tree_on_start = False

        """expand tree paths"""
        self.nav_expand_paths = []
        self.radio_expand_paths = []
        self.virtual_expand_paths = []

        """selected tree paths"""
        self.nav_selected_paths = []
        self.radio_selected_paths = []
        self.virtual_selected_paths = []

        """selected tabs"""
        self.nav_selected_tab = 0
        self.pl_selected_tab = 0

        #"""selected perpective"""
        #self.selected_perspective = None

        self.agent_line = get_ranmom_agent()

        """main window controls"""
        self.main_window_size = [119, 154, 1024, 479]
        self.window_maximized = False
        self.hpaned_left = 365
        self.hpaned_right = 850
        self.hpaned_right_right_side_width = 174 #self.main_window_size[3] - self.hpaned_right
        self.vpaned_small = 100
        self.background_image_themes = ["theme/cat.jpg", "theme/flower.jpg", "theme/winter.jpg"]
        self.background_image = None # "theme/winter.jpg"
        self.window_opacity = 1

        """Check network available"""
        self.net_ping = False

        self.menu_style = "new"

        """main window action"""
        self.on_close_window = const.ON_CLOSE_CLOSE

        """support file formats"""
        audio_containers = [".cue", ".iso.wv", ".m3u", ".m3u8"]
        self.audio_formats = [".mp3", ".ogg", ".ape", ".flac", ".wma", ".mpc", ".aiff", ".raw", ".au", ".aac", ".ac3", ".m4a", ".ra", ".m4p", ".wv", ".shn", ".wav"]
        self.all_support_formats = self.audio_formats + audio_containers
        self.all_support_formats.sort()

        self.enable_music_scrobbler = True
        self.enable_radio_scrobbler = True

        """tray icon"""
        self.show_tray_icon = True
        self.hide_on_start = False
        self.static_tray_icon = True
        self.system_icons_dinamic = False
        self.change_tray_icon = False

        self.all_icons = [ICON_FOOBNIX, ICON_FOOBNIX_PLAY, ICON_FOOBNIX_PAUSE, ICON_FOOBNIX_STOP, ICON_FOOBNIX_RADIO, "images/foobnix-tux.gif"]

        self.static_icon_entry = ICON_FOOBNIX

        self.play_icon_entry = ICON_FOOBNIX_PLAY
        self.pause_icon_entry = ICON_FOOBNIX_PAUSE
        self.stop_icon_entry = ICON_FOOBNIX_STOP
        self.radio_icon_entry = ICON_FOOBNIX_RADIO

        """Notification"""
        self.notifier = True
        self.notify_time = 3000

        """download manager controls"""
        self.auto_start_donwload = True
        self.amount_dm_threads = 3
        self.online_save_to_folder = "/tmp"
        self.automatic_online_save = False
        self.nosubfolder = False
        self.is_save_online = True

        """info panel"""
        self.info_panel_image_size = 150
        self.tooltip_image_size = 150
        self.is_info_panel_show_tags = False

        self.check_new_version = True

        self.last_dir = None

        """proxy"""
        self.proxy_enable = False
        self.proxy_url = None
        self.proxy_user = None
        self.proxy_password = None

        '''Multimedia and hot keys'''
        self.action_hotkey = {'play_pause': '<SUPER>z', 'state_stop': '<SUPER>x', 'volume_up': '<SUPER>Up', 'volume_down': '<SUPER>Down', 'show_hide': '<SUPER>a', 'prev': '<SUPER>Left', 'next': '<SUPER>Right', 'download' : '<Control><SUPER>z'}
        self.multimedia_keys = {'prev': 'XF86AudioPrev', 'next': 'XF86AudioNext', 'play_pause': 'XF86AudioPlay', 'state_stop': 'XF86AudioStop', 'volume_up': 'XF86AudioRaiseVolume', 'volume_down': 'XF86AudioLowerVolume', 'mute': 'XF86AudioMute'}
        self.media_volume_keys = {'volume_up': 'XF86AudioRaiseVolume', 'volume_down': 'XF86AudioLowerVolume', 'mute': 'XF86AudioMute'}
        self.media_keys_enabled = True
        self.media_volume_keys_enabled = False

        self.left_perspective = "info"

        self.gap_secs = 0
        self.network_buffer_size = 128  # kbytes

        self.tabs_mode = "Multi" # Multi, Single

        self.order_repeat_style = "ToggleButtons"

        self.file_managers = ['nautilus', 'dolphin', 'konqueror', 'thunar', 'pcmanfm', 'krusader', 'explorer']
        self.active_manager = [0, ""]

        #self.numbering_by_order = True

        '''columns configuration'''
        '''for playlists'''
        """translations of key words must match exactly with the translations of column.key names in PlaylistTreeControl"""
        self.columns = {'*': [True, 0, 40], 'N': [True, 1, 30], 'Composer': [False, 2, 80], 'Artist': [False, 3, 90], 'Title': [False, 4, 70], 'Track': [True, 5, 450], 'Time': [True, 6, 50], "Album": [False, 7, 90]}

        '''for navigation tree'''
        self.show_full_filename = False

        self.antiscreensaver = False

        self.is_my_radio_active = False

        self.load()

    def delete(self):
        FCStates().delete(CONFIG_FILE)

    def save(self):
        FCStates().save(self, CONFIG_FILE)
        FCBase().save()
        FCache().save()

    def load(self):
        FCStates().load(self, CONFIG_FILE)

########NEW FILE########
__FILENAME__ = fc_base
#-*- coding: utf-8 -*-
'''
Created on 23 сент. 2010

@author: ivan
'''

from __future__ import with_statement

import os
import uuid

from foobnix.fc.fc_helper import FCStates, CONFIG_DIR
from foobnix.util.singleton import Singleton


CONFIG_BASE_FILE = os.path.join(CONFIG_DIR, "foobnix_base.pkl") 

"""Foobnix base configuration, not change after installation, stable"""
class FCBase():
    __metaclass__ = Singleton

    API_KEY = "bca6866edc9bdcec8d5e8c32f709bea1"
    API_SECRET = "800adaf46e237805a4ec2a81404b3ff2"
    LASTFM_USER = "l_user_"
    LASTFM_PASSWORD = "l_pass_"
    
    def __init__(self):
        """last fm"""
        self.lfm_login = self.LASTFM_USER
        self.lfm_password = self.LASTFM_PASSWORD
        
        self.uuid = uuid.uuid4().hex
         
        self.load()
    
    def save(self):
        FCStates().save(self, CONFIG_BASE_FILE)
    
    def load(self):
        FCStates().load(self, CONFIG_BASE_FILE)

########NEW FILE########
__FILENAME__ = fc_cache
#-*- coding: utf-8 -*-
'''
Created on 20 February 2010

@author: Dmitry Kogura (zavlab1)
'''

from __future__ import with_statement

import os
import shutil
import threading
from foobnix.util.singleton import Singleton
from foobnix.fc.fc_helper import CONFIG_DIR, CACHE_DIR, FCStates


CACHE_FILE = os.path.join(CONFIG_DIR, "foobnix_cache.pkl")
COVERS_DIR = os.path.join(CACHE_DIR, 'covers', '')
LYRICS_DIR = os.path.join(CACHE_DIR, 'lyrics', '')

CACHE_COVERS_FILE = os.path.join(CACHE_DIR, 'covers_cache')
CACHE_ALBUM_FILE = os.path.join(CACHE_DIR, 'albums_cache')
CACHE_RADIO_FILE = os.path.join(CACHE_DIR, 'radio_cache')

fcache_save_lock = threading.Lock()

"""Foobnix cache"""
class FCache:
    __metaclass__ = Singleton
    def __init__(self):
        self.covers = {}
        self.album_titles = {}

        """music library"""
        self.tab_names = [_("Empty tab"), ]
        self.last_music_path = None
        self.music_paths = [[], ]
        self.cache_music_tree_beans = [{}, ]

        self.cache_virtual_tree_beans = {}
        self.cache_radio_tree_beans = {}
        self.cache_pl_tab_contents = []
        self.tab_pl_names = [_("Empty tab"), ]

        self.load()

    def save(self):
        fcache_save_lock.acquire()
        FCStates().save(self, CACHE_FILE)
        shutil.copy2(CACHE_FILE, CACHE_FILE + "_backup")
        if fcache_save_lock.locked():
            fcache_save_lock.release()

    def load(self):
        FCStates().load(self, CACHE_FILE)

    def on_load(self):
        if os.path.isfile(CACHE_COVERS_FILE):
            '''reading cover cache file in dictionary'''
            with file(CACHE_COVERS_FILE, 'r') as cov_conf:
                for line in cov_conf:
                    if line.startswith('#') and not FCache().covers.has_key(line[1:-1]):
                        FCache().covers[line[1:-1]] = cov_conf.next()[:-1].split(", ")

        if os.path.isfile(CACHE_ALBUM_FILE):
            '''reading cover cache file in dictionary'''
            with file(CACHE_ALBUM_FILE, 'r') as albums_cache:
                for line in albums_cache:
                    if line.startswith('#') and not FCache().album_titles.has_key(line[1:-1]):
                        FCache().album_titles[line[1:-1]] = albums_cache.next()[:-1]

    def on_quit(self):
        if not os.path.isdir(COVERS_DIR):
            os.mkdir(COVERS_DIR)

        with file(CACHE_COVERS_FILE, 'w') as f:
            for key, value in zip(FCache().covers.keys(), FCache().covers.values()):
                f.write('#' + key + '\n' + ','.join(value) + '\n')

        with file(CACHE_ALBUM_FILE, 'w') as f:
            for key, value in zip(FCache().album_titles.keys(), FCache().album_titles.values()):
                f.write('#' + key + '\n' + value + '\n')
########NEW FILE########
__FILENAME__ = fc_helper
#-*- coding: utf-8 -*-
'''
Created on 21 февр. 2011

@author: ivan
'''

from __future__ import with_statement
import os
import logging
import cPickle
import threading

CONFIG_DIR = os.path.join(os.path.expanduser("~"), ".config", "foobnix-3", "")
CACHE_DIR = os.path.join(os.path.expanduser("~"), ".cache", "foobnix-3", "")
if not os.path.exists(CONFIG_DIR):
    os.makedirs(CONFIG_DIR)
if not os.path.exists(CACHE_DIR):
    os.makedirs(CACHE_DIR)


class FCStates:
    def save(self, fc, file):
        #if in_thread:
        #    thread.start_new_thread(FCHelper().save, (fc,))
        #else:
        FCHelper().save(fc, file)

    def load(self, fc, file):
        """restore from file"""
        object = FCHelper().load(file)
        if object:
            dict = object.__dict__
            keys = fc.__dict__.keys()
            for i in dict:
                try:
                    if i in keys:
                        setattr(fc, i, dict[i])
                except Exception as e:
                    logging.warn("Value not found" + str(e))
                    return False
        return True

    def info(self):
        FCHelper().print_info(self)

    def delete(self, file_path):
        FCHelper().delete(file_path)


class FCHelper():
    def __init__(self):
        self.save_lock = threading.Lock()
        pass

    def save(self, object, file_path):
        self.save_lock.acquire()
        try:
            save_file = open(file_path, 'w')
            try:
                cPickle.dump(object, save_file)
            except Exception as e:
                logging.error("Error dumping pickle conf " + str(e))
            save_file.close()
            logging.debug("Config save")
            self.print_info(object)
        finally:
            if self.save_lock.locked():
                self.save_lock.release()

    def load(self, file_path):
        if not os.path.exists(file_path):
            logging.debug("Config file not found" + file_path)
            if not file_path.endswith("_backup"):
                logging.info("Try to load config backup")
                return self.load(file_path + "_backup")
            return None

        with open(file_path, 'r') as load_file:
            try:
                load_file = open(file_path, 'r')
                pickled = load_file.read()

                object = cPickle.loads(pickled)
                logging.debug("Config loaded")
                self.print_info(object)
                return object
            except Exception as e:
                logging.error("Error load config" + str(e))
                if not file_path.endswith("_backup"):
                    logging.info("Try to load config backup")
                    return self.load(file_path + "_backup")
        return None

    def delete(self, file_path):
        if os.path.exists(file_path):
            os.remove(file_path)

    def print_info(self, object):
        dict = object.__dict__
        for i in object.__dict__:
            if i not in ["user_id", "access_token", "vk_user", "vk_pass", "lfm_login", "lfm_password", "uuid"]:
                logging.debug(i + " " + str(dict[i])[:500])

########NEW FILE########
__FILENAME__ = about
# -*- coding: utf-8 -*-
'''
Created on Oct 2, 2010

@author: dimitry (zavlab1)
'''

from gi.repository import Gtk
from gi.repository import Gdk
from foobnix.gui.service.path_service import get_foobnix_resourse_path_by_name
from foobnix.util.const import ICON_FOOBNIX
from foobnix.version import FOOBNIX_VERSION

class AboutWindow(Gtk.AboutDialog):
    def __init__(self):
        Gtk.AboutDialog.__init__(self)
        
        self.set_program_name("Foobnix")
        self.set_version(FOOBNIX_VERSION)
        self.set_copyright("(c) Ivan Ivanenko <ivan.ivanenko@gmail.com>")
        self.set_comments(_("Simple and Powerful player"))
        self.set_website("http://www.foobnix.com")
        self.set_authors(["Dmitry Kozhura (zavlab1) <zavlab1@gmail.com>", "Pietro Campagnano <fain182@gmailcom>", "Viktor Suprun <popsul1993@gmail.com>"])
        
        self.set_translator_credits("""Bernardo Miguel Savone
Sérgio Marques
XsLiDian
KamilSPL
north
Alex Serada
Ivan Ivanenko
Dmitry-Kogura
Fitoschido
zeugma
Schaffino
Oleg «Eleidan» Kulik
Sergey Zigachev
Martino Barbon
Florian Heissenberger
Aldo Mann""")
        
        
        self.set_logo(Gdk.pixbuf_new_from_file(get_foobnix_resourse_path_by_name(ICON_FOOBNIX))) #@UndefinedVariable
    
    def show(self):
        self.run()
        self.destroy()

########NEW FILE########
__FILENAME__ = base_controls
#-*- coding: utf-8 -*-
'''
Created on 25 сент. 2010

@author: ivan
'''

import os
import time
import copy
import thread
import logging

from gi.repository import Gtk
from gi.repository import GLib
from gi.repository import GdkPixbuf

from threading import Lock
from urllib2 import urlopen
from foobnix.fc.fc import FC
from foobnix.fc.fc_base import FCBase
from foobnix.fc.fc_cache import FCache
from foobnix.helpers.dialog_entry import file_chooser_dialog, \
    directory_chooser_dialog, info_dialog_with_link_and_donate
from foobnix.gui.model import FModel
from foobnix.gui.service.music_service import get_all_music_by_paths
from foobnix.gui.service.vk_service import VKService
from foobnix.gui.state import LoadSave, Quitable
from foobnix.util.bean_utils import get_bean_posible_paths
from foobnix.util.const import STATE_PLAY, STATE_PAUSE, STATE_STOP, FTYPE_RADIO
from foobnix.util.file_utils import get_file_extension
from foobnix.util.iso_util import mount_tmp_iso
from foobnix.util.version import compare_versions
from foobnix.version import FOOBNIX_VERSION
from foobnix.util import analytics, idle_task, idle_task_priority
from foobnix.util.text_utils import normalize_text


class BaseFoobnixControls():
    def __init__(self):
        self.vk_service = VKService(FC().access_token, FC().user_id)

        self.count_errors = 0
        self.is_scrobbled = False
        self.start_time = None

        self.cache_text = None
        self.play_lock = Lock()

    def check_for_media(self, args):
        dirs = []
        files = []
        for arg in args:
            if os.path.isdir(arg):
                dirs.append(arg)
            elif os.path.isfile(arg) and get_file_extension(arg) in FC().all_support_formats:
                files.append(arg)
        if dirs:
            self.on_add_folders(dirs)
        elif files:
            self.on_add_files(files)
            try:
                self.play_first_added(files)
            except:
                logging.error("Can't to play first added file")

    def play_first_added(self, added_files):
        tree = self.notetabs.get_current_tree()
        model = tree.get_model()
        number = len(model) - len(added_files)
        if (number) > -1:
            iter = model.get_iter_from_string(str(number))
            bean = tree.get_bean_from_model_iter(model, iter)
            tree.set_play_icon_to_bean(bean)
            self.play(bean)

    def love_this_tracks(self, beans=None):
        if not beans:
            return
        map(self.lastfm_service.love, beans)

    def add_to_my_playlist(self, beans=None):
         if not beans:
             return
         map(self.vk_service.add, beans)

    def show_google_results(self, query):
        return [FModel('"%s" not found' % query)]

    def get_active_bean(self):
        tree = self.notetabs.get_current_tree()
        if tree:
            return tree.get_selected_or_current_bean()

    def play_selected_song(self):
        current = self.get_active_bean()
        tree = self.notetabs.get_current_tree()
        if not current:
            try:
                current = tree.get_bean_under_pointer_icon()
            except AttributeError:
                return
        if not current:
            return None
        logging.debug("play current bean is %s" % str(current.text))
        if current and current.is_file:
            tree.set_play_icon_to_bean(current)
            self.play(current)

    def check_path(self, path):
        if path:
            if not path.startswith("http://"):
                if os.path.exists(path):
                    return True
            else:
                try:
                    u = urlopen(path, timeout=5)    # @UnusedVariable
                    if "u" not in vars():
                        return False
                    return True
                except:
                    return False
        return False

    def save_beans_to(self, beans):
        return None

    def on_chage_player_state(self, state, bean):
        logging.debug("bean state %s" % state)

        self.set_dbus_state(state, bean)

        if not FC().system_icons_dinamic:
            return None

        if state == STATE_STOP:
            self.trayicon.set_image_from_path(FC().stop_icon_entry)
        elif state == STATE_PAUSE:
            self.trayicon.set_image_from_path(FC().pause_icon_entry)
        elif state == STATE_PLAY:
            self.trayicon.set_image_from_path(FC().play_icon_entry)

        if bean and bean.type:
            logging.debug("bean state and type %s %s" % (state, bean.type))
            if bean.type == FTYPE_RADIO:
                return self.trayicon.set_image_from_path(FC().radio_icon_entry)

    @idle_task
    def set_dbus_state(self, state, bean):
        if self.dbus:
            self.dbus._update_info(bean)
            if state is STATE_PLAY:
                self.dbus._set_state_play()
            elif state is STATE_PAUSE:
                self.dbus._set_state_pause()
            else:
                self.dbus._set_state_stop()

    def on_add_folders(self, paths=None):
        if not paths:
            paths = directory_chooser_dialog(_("Choose folders to open"), FC().last_dir)
            if not paths:
                return
        tree = self.notetabs.get_current_tree()
        FC().last_dir = os.path.dirname(paths[0])
        if tree.is_empty():
            if len(paths) > 1:
                tabname = os.path.basename(FC().last_dir)
            else:
                tabname = os.path.basename(paths[0])
            self.notetabs.rename_tab(tree.scroll, tabname)
        tree.append(paths)

    def on_add_files(self, paths=None, tab_name=None):
        if not paths:
            paths = file_chooser_dialog(_("Choose file to open"), FC().last_dir)
            if not paths:
                return
        tree = self.notetabs.get_current_tree()
        FC().last_dir = os.path.dirname(paths[0])
        if tree.is_empty():
            tabname = os.path.split(os.path.dirname(paths[0]))[1]
            self.notetabs.rename_tab(tree.scroll, tabname)
        tree.append(paths)

    def set_playlist_tree(self):
        self.notetabs.set_playlist_tree()

    def set_playlist_plain(self):
        self.notetabs.set_playlist_plain()

    def load_music_tree(self):
        tabs = len(FCache().cache_music_tree_beans)
        tabhelper = self.perspectives.get_perspective('fs').get_tabhelper()
        for tab in xrange(tabs - 1, -1, -1):
            tabhelper._append_tab(FCache().tab_names[tab], rows=FCache().cache_music_tree_beans[tab])

            if not FCache().cache_music_tree_beans[tab]:
                self.perspectives.get_perspective('fs').show_add_button()
            else:
                self.perspectives.get_perspective('fs').hide_add_button()

            logging.info("Tree loaded from cache")

        if FC().update_tree_on_start:
            def cycle():
                for n in xrange(len(FCache().music_paths)):
                    tab_child = tabhelper.get_nth_page(n)
                    tree = tab_child.get_child()
                    self.update_music_tree(tree, n)
            GLib.idle_add(cycle)

    def update_music_tree(self, tree, number_of_page=0):
        logging.info("Update music tree" + str(FCache().music_paths[number_of_page]))
        tree.clear_tree()   # safe method
        FCache().cache_music_tree_beans[number_of_page] = {}

        all = get_all_music_by_paths(FCache().music_paths[number_of_page], self)

        try:
            self.perspectives.get_perspective('fs').hide_add_button()
        except AttributeError:
            logging.warn("Object perspective not exists yet")

        if not all:
            try:
                self.perspectives.get_perspective('fs').show_add_button()
            except AttributeError:
                logging.warn("Object perspective not exists yet")
        tree.append_all(all)     # safe method
        tree.ext_width = tree.ext_column.get_width()

        GLib.idle_add(tree.save_rows_from_tree,
                         FCache().cache_music_tree_beans[number_of_page])
        #GLib.idle_add(self.tabhelper.on_save_tabs)   # for true order

    @idle_task
    def set_visible_video_panel(self, flag):
        return
        #FC().is_view_video_panel = flag
        #if flag:
        #    self.movie_window.show()
        #else:
        #    self.movie_window.hide()

    @idle_task
    def volume_up(self):
        self.volume.volume_up()

    @idle_task
    def volume_down(self):
        self.volume.volume_down()

    @idle_task
    def mute(self):
        self.volume.mute()

    @idle_task
    def hide(self):
        self.main_window.hide()

    @idle_task
    def show_hide(self):
        self.main_window.show_hide()

    @idle_task
    def show(self):
        self.main_window.show()

    @idle_task
    def play_pause(self):
        if self.media_engine.get_state() == STATE_PLAY:
            self.media_engine.state_pause()
        elif self.media_engine.get_state() == STATE_STOP:
            self.state_play(True)
        else:
            self.media_engine.state_play()

    @idle_task
    def seek_up(self):
        self.media_engine.seek_up()

    @idle_task
    def seek_down(self):
        self.media_engine.seek_down()

    @idle_task
    def windows_visibility(self):
        visible = self.main_window.get_property('visible')
        if visible:
            GLib.idle_add(self.main_window.hide)
        else:
            GLib.idle_add(self.main_window.show)

    @idle_task
    def state_play(self, under_pointer_icon=False):
        if self.media_engine.get_state() == STATE_PAUSE:
            self.media_engine.state_play()
            self.statusbar.set_text(self.media_engine.bean.info)
        elif under_pointer_icon:
            tree = self.notetabs.get_current_tree()
            bean = tree.get_bean_under_pointer_icon()
            self.play(bean)
        else:
            self.play_selected_song()

    @idle_task
    def show_preferences(self):
        self.preferences.show()

    @idle_task
    def state_pause(self):
        self.media_engine.state_pause()

    @idle_task_priority(priority=GLib.PRIORITY_HIGH_IDLE)
    def state_stop(self, remember_position=False):
        self.record.hide()
        self.media_engine.state_stop(remember_position)
        if not remember_position:
            self.statusbar.set_text(_("Stopped"))
            self.seek_bar.clear()

    @idle_task
    def state_play_pause(self):
        self.media_engine.state_play_pause()
        bean = self.media_engine.bean
        if self.media_engine.get_state() == STATE_PLAY:
            self.statusbar.set_text(bean.info)
        else:
            self.statusbar.set_text(_("Paused | ") + str(bean.info))

    def state_is_playing(self):
        return self.media_engine.get_state() == STATE_PLAY

    def fill_bean_from_vk(self, bean):
        if bean.type and bean.type == FTYPE_RADIO:
            return False
        vk = self.vk_service.find_one_track(bean.get_display_name())
        if vk:
            bean.path = vk.path
            bean.time = vk.time
            return True
        else:
            return False

    def fill_bean_by_vk_aid(self, bean):
        if not bean.vk_audio_id:
            return False
        if bean.type and bean.type == FTYPE_RADIO:
            return False
        track = self.vk_service.find_track_by_id(bean.vk_audio_id)
        if track:
            bean.path = track.path
            bean.time = track.time
            return True
        return False

    @idle_task
    def play(self, bean):
        if not bean or not bean.is_file:
            return

        self.play_lock.acquire()
        self.seek_bar.clear()
        ## TODO: Check for GTK+3.4 (Status icon doesn't have a set_tooltip method)
        self.statusbar.set_text(bean.info)
        self.trayicon.set_text(bean.text)
        #self.movie_window.set_text(bean.text)

        if bean.type == FTYPE_RADIO:
            self.record.show()
            self.seek_bar.progressbar.set_fraction(0)
            self.seek_bar.set_text(_("Radio ") + bean.text.capitalize())
        else:
            self.record.hide()

        self.main_window.set_title(bean.text)

        thread.start_new_thread(self._one_thread_play, (bean,))

    def _one_thread_play(self, bean):
        try:
            self._play(bean)
        finally:
            if self.play_lock.locked():
                self.play_lock.release()

    def _play(self, bean):
        if not bean.path:
            bean.path = get_bean_posible_paths(bean)

        if not self.check_path(bean.path):
            if bean.iso_path and os.path.exists(bean.iso_path):
                logging.info("Try to remount " + bean.iso_path)
                mount_tmp_iso(bean.iso_path)
            elif bean.vk_audio_id:
                self.fill_bean_by_vk_aid(bean)
            elif not bean.path or ("userapi" in bean.path) or ("vk.me" in bean.path):
                self.fill_bean_from_vk(bean)
            else:
                resource = bean.path if bean.path else bean.text
                logging.error("Resourse " + resource + " not found")
                self.media_engine.state_stop(show_in_tray=False)
                self.statusbar.set_text(_("Resource not found"))
                self.seek_bar.set_text(_("Resource not found"))
                self.count_errors += 1
                time.sleep(2)
                if self.count_errors < 4:
                    if self.play_lock.locked():
                        self.play_lock.release()
                    self.next()
                else:
                    self.seek_bar.set_text(_("Stopped. No resources found"))
                return

        elif os.path.isdir(bean.path):
            return

        self.count_errors = 0
        self.media_engine.play(bean)
        self.is_scrobbled = False
        self.start_time = False

        if bean.type != FTYPE_RADIO:
            self.update_info_panel(bean)
        self.set_visible_video_panel(False)

    @idle_task
    def notify_playing(self, pos_sec, dur_sec, bean):
        if not bean.type or bean.type != FTYPE_RADIO:
            self.seek_bar.update_seek_status(pos_sec, dur_sec)
        else:
            self.seek_bar.fill_seekbar()

        if pos_sec == 2 or (pos_sec > 2 and (pos_sec % 20) == 0):
            self.net_wrapper.execute(self.lastfm_service.report_now_playing, bean)

        if not self.start_time:
            self.start_time = str(int(time.time()))

        if not self.is_scrobbled and bean.type != FTYPE_RADIO:
            ## song should be scrobbled if 90% has been played or played greater than 5 minutes
            if pos_sec > (dur_sec * 0.9) or pos_sec > (60 * 5):
                self.is_scrobbled = True
                self.net_wrapper.execute(self.lastfm_service.report_scrobbled, bean, self.start_time, dur_sec)
                """download music"""
                if FC().automatic_online_save and bean.path and bean.path.startswith("http://"):
                    self.dm.append_task(bean)

    @idle_task
    def notify_title(self, bean, raw_text):
        logging.debug("Notify title" + raw_text)
        text = raw_text.partition("||")[0]
        if not self.cache_text:
            self.cache_text = text

        self.statusbar.set_text(raw_text.replace("||", "|"))

        text = normalize_text(text)

        self.seek_bar.set_text(text)
        t_bean = bean.create_from_text(text)
        self.update_info_panel(t_bean)
        self.set_dbus_state(STATE_PLAY, t_bean)
        if FC().enable_radio_scrobbler:
            start_time = str(int(time.time()))
            self.net_wrapper.execute(self.lastfm_service.report_now_playing, t_bean)

            if " - " in text and self.cache_text != text:
                c_bean = copy.copy(bean)
                prev_bean = c_bean.create_from_text(self.cache_text)
                self.net_wrapper.execute(self.lastfm_service.report_scrobbled, prev_bean, start_time, 200)
                self.cache_text = text

    @idle_task
    def notify_error(self, msg):
        logging.error("notify error " + msg)
        self.seek_bar.set_text(msg)
        self.perspectives.get_perspective('info').clear()

    @idle_task
    def notify_eos(self):
        self.next()

    @idle_task
    def player_seek(self, percent):
        self.media_engine.seek(percent)

    @idle_task
    def player_volume(self, percent):
        self.media_engine.volume(percent)

    def search_vk_page_tracks(self, vk_ulr):
        logging.debug("Search vk_service page tracks")
        results = self.vk_service.find_tracks_by_url(vk_ulr)
        all = []
        p_bean = FModel(vk_ulr).add_font("bold")
        all.append(p_bean)
        for i, bean in enumerate(results):
            bean.tracknumber = i + 1
            bean.parent(p_bean).add_is_file(True)
            all.append(bean)

        self.notetabs.append_tab(vk_ulr, all)

    def search_all_tracks(self, query):
        def search_all_tracks_task():
            analytics.action("SEARCH_search_all_tracks")
            results = self.vk_service.find_tracks_by_query(query)
            if not results:
                results = []
            all = []
            p_bean = FModel(query).add_font("bold")
            all.append(p_bean)
            for i, bean in enumerate(results):
                bean.tracknumber = i + 1
                bean.parent(p_bean).add_is_file(True)
                all.append(bean)

            if not results:
                all = self.show_google_results(query)

            self.notetabs.append_tab(query, all)
        self.in_thread.run_with_progressbar(search_all_tracks_task, no_thread=True)

    def search_top_tracks(self, query):
        def search_top_tracks_task(query):
            analytics.action("SEARCH_search_top_tracks")
            results = self.lastfm_service.search_top_tracks(query)
            if not results:
                results = []
            all = []
            parent_bean = FModel(query)
            all.append(parent_bean)
            for i, bean in enumerate(results):
                bean.tracknumber = i + 1
                bean.parent(parent_bean).add_is_file(True)
                all.append(bean)

            if not results:
                all = self.show_google_results(query)

            self.notetabs.append_tab(query, all)

        self.in_thread.run_with_progressbar(search_top_tracks_task, query)

    def search_top_albums(self, query):
        def search_top_albums_task(query):
            analytics.action("SEARCH_search_top_albums")
            results = self.lastfm_service.search_top_albums(query)
            if not results:
                results = []
            self.notetabs.append_tab(query, None)
            albums_already_inserted = []
            for album in results[:15]:
                all = []
                if album.album.lower() in albums_already_inserted:
                    continue
                album.is_file = False
                tracks = self.lastfm_service.search_album_tracks(album.artist, album.album)
                for i, track in enumerate(tracks):
                    track.tracknumber = i + 1
                    track.album = album.album
                    track.parent(album).add_is_file(True)
                    all.append(track)
                if len(all) > 0:
                    all = [album] + all
                    albums_already_inserted.append(album.album.lower())
                    self.notetabs.append_all(all)

            if not results:
                all = self.show_google_results(query)
                self.notetabs.append_all(all)

        self.in_thread.run_with_progressbar(search_top_albums_task, query)

    def search_top_similar(self, query):

        def search_top_similar_task(query):
            analytics.action("SEARCH_search_top_similar")
            results = self.lastfm_service.search_top_similar_artist(query)
            if not results:
                results = []
            self.notetabs.append_tab(query, None)
            for artist in results[:15]:
                all = []
                artist.is_file = False
                all.append(artist)
                tracks = self.lastfm_service.search_top_tracks(artist.artist)
                for i, track in enumerate(tracks):
                    track.tracknumber = i + 1
                    track.parent(artist).add_is_file(True)
                    all.append(track)

                self.notetabs.append_all(all)

            if not results:
                all = self.show_google_results(query)

        #inline(query)
        self.in_thread.run_with_progressbar(search_top_similar_task, query)

    def search_top_tags(self, query):

        def search_top_tags_task(query):
            analytics.action("SEARCH_search_top_tags")
            results = self.lastfm_service.search_top_tags(query)
            if not results:
                logging.debug("tag result not found")
                results = []
            self.notetabs.append_tab(query, None)
            for tag in results[:15]:
                all = []
                tag.is_file = False
                all.append(tag)
                tracks = self.lastfm_service.search_top_tag_tracks(tag.text)
                for i, track in enumerate(tracks):
                    track.tracknumber = i + 1
                    track.parent(tag).add_is_file(True)
                    all.append(track)

                self.notetabs.append_all(all)

            if not results:
                all = self.show_google_results(query)
                self.notetabs.append_all(all)

        #inline(query)
        self.in_thread.run_with_progressbar(search_top_tags_task, query)

    @idle_task
    def update_info_panel(self, bean):
        self.perspectives.get_perspective('info').update(bean)

    @idle_task
    def append_to_new_notebook(self, text, beans, optimization=False):
        self.notetabs._append_tab(text, beans, optimization)

    @idle_task
    def append_to_current_notebook(self, beans):
        self.notetabs.append_all(beans)

    @idle_task
    def next(self):
        bean = self.notetabs.next()
        if not bean:
            return
        gap = FC().gap_secs
        time.sleep(gap)
        logging.debug("play current bean is %s" % str(bean.text))

        self.play(bean)

    @idle_task
    def prev(self):
        bean = self.notetabs.prev()
        if not bean:
            return

        self.play(bean)

    def quit(self, *a):
        self.state_stop()

        self.main_window.hide()
        self.trayicon.hide()

        logging.info("Controls - Quit")

        for element in self.__dict__:
            if isinstance(self.__dict__[element], Quitable):
                self.__dict__[element].on_quit()

        FC().save()

        GLib.idle_add(Gtk.main_quit) # wait for complete stop task

    def check_version(self):
        uuid = FCBase().uuid
        current_version = FOOBNIX_VERSION
        system = "not_set"
        try:
            import platform
            system = platform.system()
        except:
            pass

        try:
            from socket import gethostname
            f = urlopen("http://www.foobnix.com/version?uuid=" + uuid + "&host=" + gethostname()
                        + "&version=" + current_version + "&platform=" + system, timeout=7)
            #f = urllib2.urlopen("http://localhost:8080/version?uuid=" + uuid + "&host=" + gethostname() + "&v=" + current_version)
        except Exception as e:
            logging.error("Check version error: " + str(e))
            return None

        new_version_line = f.read()

        logging.info("version " + current_version + "|" + new_version_line + "|" + str(uuid))

        f.close()
        if FC().check_new_version and compare_versions(current_version, new_version_line) == 1:
            info_dialog_with_link_and_donate(new_version_line)

    def on_load(self):
        """load controls"""
        for element in self.__dict__:
            if isinstance(self.__dict__[element], LoadSave):
                init = time.time()
                self.__dict__[element].on_load()
                logging.debug("%f LOAD ON START %s" % (time.time() - init, str(self.__dict__[element])))

        """load others"""
        #self.movie_window.hide_all()

        self.main_window.show()
        self.search_progress.stop()

        """base layout"""
        self.layout.on_load()

        """check for new version"""

        if os.name == 'nt':
            self.check_version()
        else:
            pass
            #GLib.idle_add(self.check_version)

    @idle_task_priority(GLib.PRIORITY_LOW)
    def play_first_file_in_playlist(self):
        active_playlist_tree = self.notetabs.get_current_tree()
        filter_model = active_playlist_tree.get_model()
        current_model = filter_model.get_model()

        def play_item(iter, active_playlist_tree, filter_model, current_model):
            bean = active_playlist_tree.get_bean_from_model_iter(current_model, iter)
            if not bean:
                return

            if bean.font != 'bold':
                self.play(bean)
                tree_selection = active_playlist_tree.get_selection()
                filter_iter = filter_model.convert_child_iter_to_iter(iter)
                if filter_iter[0]:
                    GLib.idle_add(tree_selection.select_iter, filter_iter[1])
                active_playlist_tree.set_play_icon_to_bean_to_selected()
            else:
                iter = current_model.iter_next(iter)
                play_item(iter, active_playlist_tree, filter_model, current_model)

        iter = current_model.get_iter_first()
        play_item(iter, active_playlist_tree, filter_model, current_model)

    def on_save(self):
        for element in self.__dict__:
            if isinstance(self.__dict__[element], LoadSave):
                logging.debug("SAVE " + str(self.__dict__[element]))
                self.__dict__[element].on_save()

    def download(self):
        self.dm.append_task(bean=self.notetabs.get_current_tree().get_current_bean_by_UUID())

########NEW FILE########
__FILENAME__ = base_layout
#-*- coding: utf-8 -*-
'''
Created on 25 сент. 2010

@author: ivan
'''

import logging

from gi.repository import Gtk
from gi.repository import Gdk
from gi.repository import GLib

from foobnix.fc.fc import FC
from foobnix.gui.model.signal import FControl
from foobnix.gui.state import LoadSave

## TODO: move into resources
foobnix_style = """
GtkComboBox .button {
    /* fix for very large size of combobox */
    padding: 2px 5px;
}
/*
foobnix\+gui\+window\+MainWindow {
    background-image: url("/usr/share/pixmaps/foobnix-big.png");
    background-size:100% 100%;
    background-repeat:no-repeat;
}
GtkHPaned {
    background-color: rgba(255, 255, 255, 0.5);
}
*/
"""


class BaseFoobnixLayout(FControl, LoadSave):
    def __init__(self, controls):
        FControl.__init__(self, controls)

        """ set application stylesheet"""
        self.style_provider = Gtk.CssProvider()
        ## TODO: after moving style to resource - replace to load_from_file
        self.style_provider.load_from_data(foobnix_style)
        Gtk.StyleContext.add_provider_for_screen(
            Gdk.Screen.get_default(),
            self.style_provider,
            Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION
        )

        self.controls = controls
        bbox = Gtk.VBox(False, 0)
        notebox = Gtk.Overlay.new()
        notebox.add(controls.notetabs)
        notebox.add_overlay(controls.search_progress)

        bbox.pack_start(notebox, True, True, 0)
        #bbox.pack_start(controls.movie_window, False, False, 0)

        center_box = Gtk.VBox(False, 0)
        center_box.pack_start(controls.searchPanel, False, False, 0)
        center_box.pack_start(bbox, True, True, 0)

        self.hpaned_left = Gtk.HPaned()
        self.hpaned_left.connect("motion-notify-event", self.on_motion)

        self.hpaned_left.pack1(child=controls.perspectives, resize=True, shrink=True)
        self.hpaned_left.pack2(child=center_box, resize=True, shrink=True)

        self.hpaned_right = Gtk.HPaned()
        self.hpaned_right.connect("motion-notify-event", self.on_motion)
        self.hpaned_right.pack1(child=self.hpaned_left, resize=True, shrink=True)
        self.hpaned_right.pack2(child=controls.coverlyrics, resize=True, shrink=False)

        vbox = Gtk.VBox(False, 0)
        vbox.pack_start(controls.top_panel, False, False, 0)
        vbox.pack_start(self.hpaned_right, True, True, 0)
        vbox.pack_start(controls.statusbar, False, True, 0)
        vbox.show_all()

        self.hpaned_left.connect("button-press-event", self.on_border_press)
        self.hpaned_right.connect("button-press-event", self.on_border_press)
        self.hpaned_left.connect("button-release-event", self.on_border_release)
        self.hpaned_right.connect("button-release-event", self.on_border_release)
        self.id_handler_left = self.hpaned_left.connect("size-allocate", self.on_configure_hl_event)
        self.id_handler_right = self.hpaned_right.connect("size-allocate", self.on_configure_hr_event)

        self.hpaned_press_release_handler_blocked = False

        controls.main_window.connect("configure-event", self.on_configure_event)
        controls.main_window.add(vbox)

    def set_visible_search_panel(self, flag=True):
        logging.info("set_visible_search_panel " + str(flag))
        if flag:
            self.controls.searchPanel.show_all()
        else:
            self.controls.searchPanel.hide()

        FC().is_view_search_panel = flag

    def set_visible_musictree_panel(self, flag):
        logging.info("set_visible_musictree_panel " + str(flag))
        if flag:
            self.hpaned_left.set_position(FC().hpaned_left)
        else:
            self.hpaned_left.set_position(0)

        FC().is_view_music_tree_panel = flag

    def set_visible_coverlyrics_panel(self, flag):
        logging.info("set_visible_coverlyrics_panel " + str(flag))
        if flag:
            self.hpaned_right.set_position(self.hpaned_right.get_allocated_width() - FC().hpaned_right_right_side_width)
            self.controls.coverlyrics.show()
            #GLib.idle_add(self.controls.coverlyrics.adapt_image)
        else:
            self.controls.coverlyrics.hide()

        FC().is_view_coverlyrics_panel = flag

    def on_motion(self, *a):
        return

    def on_border_press(self, *a):
        if not self.hpaned_press_release_handler_blocked:
            self.hpaned_left.handler_block(self.id_handler_left)
            self.hpaned_right.handler_block(self.id_handler_right)
            self.hpaned_press_release_handler_blocked = True

    def on_border_release(self, w, *a):
        if self.hpaned_press_release_handler_blocked:
            self.hpaned_left.handler_unblock(self.id_handler_left)
            self.hpaned_right.handler_unblock(self.id_handler_right)
            self.hpaned_press_release_handler_blocked = False
        self.save_right_panel()
        if w is self.hpaned_left:
            self.save_left_panel()
        elif w is self.hpaned_right:
            self.on_configure_hl_event()
            GLib.idle_add(self.save_left_panel)

    def save_right_panel(self):
        if self.controls.coverlyrics.get_property("visible"):
            right_position = self.hpaned_right.get_position()
            if right_position != FC().hpaned_right and right_position > 0:
                FC().hpaned_right = right_position
            FC().hpaned_right_right_side_width = self.hpaned_right.get_allocated_width() - right_position
            #self.controls.coverlyrics.adapt_image()

    def save_left_panel(self):
        left_position = self.hpaned_left.get_position()
        if left_position != FC().hpaned_left and left_position > 0:
            FC().hpaned_left = left_position
            self.normalize_columns()

    def normalize_columns(self):
        tabhelper = self.controls.perspectives.get_perspective('fs').get_tabhelper()
        for page in xrange(tabhelper.get_n_pages()):
            tab_content = tabhelper.get_nth_page(page)
            tree = tab_content.get_child()
            tree.normalize_columns_width()

    def on_configure_event(self, w, e):
        FC().main_window_size = [e.x, e.y, e.width, e.height]

    def on_configure_hl_event(self, *a):
        def task():
            if FC().is_view_music_tree_panel and self.hpaned_left.get_position() != FC().hpaned_left:
                self.hpaned_left.set_position(FC().hpaned_left)
        GLib.idle_add(task)

    def on_configure_hr_event(self, *a):
        def task():
            if self.controls.coverlyrics.get_property("visible"):
                hrw = self.hpaned_right.get_allocated_width()
                if (hrw - self.hpaned_right.get_position()) != FC().hpaned_right_right_side_width:
                    self.hpaned_right.set_position(hrw - FC().hpaned_right_right_side_width)
        GLib.idle_add(task)

    def on_load(self):
        self.set_visible_search_panel(FC().is_view_search_panel)
        GLib.idle_add(self.set_visible_musictree_panel, FC().is_view_music_tree_panel,
                         priority = GLib.PRIORITY_DEFAULT_IDLE - 10)
        self.set_visible_coverlyrics_panel(FC().is_view_coverlyrics_panel)

########NEW FILE########
__FILENAME__ = dbus_manager
#-*- coding: utf-8 -*-
'''
Created on 28 сент. 2010

@author: anton.komolov
'''

import logging
import dbus.service

from foobnix.fc.fc import FC
from foobnix.util import idle_task
from foobnix.version import FOOBNIX_VERSION
from dbus.mainloop.glib import DBusGMainLoop
from foobnix.gui.service.path_service import get_foobnix_resourse_path_by_name
from foobnix.thirdparty.sound_menu import SoundMenuControls
from foobnix.util.const import STATE_PLAY, ICON_FOOBNIX

DBusGMainLoop(set_as_default=True)

DBUS_NAME = "org.mpris.MediaPlayer2.foobnix"
MPRIS_ROOT_PATH = "/"
MPRIS_PLAYER_PATH = "/Player"
MPRIS_TRACKLIST_PATH = "/TrackList"
DBUS_MEDIAPLAYER_INTERFACE = 'org.freedesktop.MediaPlayer'


class DBusManager():
    def __init__(self, controls):
        try:
            self.sound_menu = MprisSoundMenu(controls)
            self.player = MprisPlayer(controls)
        except Exception, e:
            self.sound_menu = None
            logging.error("DBUS Initialization Error " + str(e))

        '''
        try:
            dbus_interface = 'org.gnome.SettingsDaemon.MediaKeys'
            mm_object = bus.get_object('org.gnome.SettingsDaemon', '/org/gnome/SettingsDaemon/MediaKeys')

            mm_object.GrabMediaPlayerKeys("MyMultimediaThingy", 0, dbus_interface=dbus_interface)
            mm_object.connect_to_signal('MediaPlayerKeyPressed', self.on_mediakey)
            #mm_object.ReleaseMediaPlayerKeys("MyMultimediaThingy", dbus_interface=dbus_interface)
        except Exception, e:
            self.sound_menu = None
            logging.error("DBUS Initialization Error " + str(e))
        '''

    def _set_state_play(self):
        if self.sound_menu:
            self.sound_menu.signal_playing()

    def _set_state_pause(self):
        if self.sound_menu:
            self.sound_menu.signal_paused()

    def _set_state_stop(self):
        if self.sound_menu:
            self.sound_menu.signal_stopped()

    def _update_info(self, bean):
        if not bean:
            return
        if not self.sound_menu:     # if dbus initialization can't be finished
            return
        image = "file:///" + get_foobnix_resourse_path_by_name(ICON_FOOBNIX)
        if bean.image:
            if bean.image.startswith("/"):
                image = "file:///" + bean.image
            else:
                image = bean.image
        artists = None
        if bean.artist:
            artists = [bean.artist]
        self.sound_menu.song_changed(artists=artists,
                                     title=bean.title or bean.text,
                                     album=bean.album,
                                     cover=image)

    def on_mediakey(self, comes_from, what):
        if not FC().media_keys_enabled:
            return
        logging.debug("Multi media key pressed" + what)
        """
        gets called when multimedia keys are pressed down.
        """
        if what in ['Stop', 'Play', 'Next', 'Previous']:
            if what == 'Stop':
                self.controls.state_stop()
            elif what == 'Play':
                self.controls.state_play_pause()
            elif what == 'Next':
                self.controls.next()
            elif what == 'Previous':
                self.controls.prev()
        else:
            logging.debug('Got a multimedia key:' + str(what))


class MprisPlayer(dbus.service.Object):
    """implementation org.mpris.MediaPlayer2.foobnix /Player"""


    def __init__(self, controls):
        self.controls = controls

        bus = dbus.SessionBus()
        bus_name = dbus.service.BusName(DBUS_NAME, bus=bus)
        dbus.service.Object.__init__(self, bus_name, MPRIS_PLAYER_PATH)

    #Next ( )
    @dbus.service.method(DBUS_MEDIAPLAYER_INTERFACE, in_signature='', out_signature='')
    def Next(self):
        self.controls.next()

    #Prev ( )
    @dbus.service.method(DBUS_MEDIAPLAYER_INTERFACE, in_signature='', out_signature='')
    def Previous(self):
        self.controls.prev()

    #Pause ( )
    @dbus.service.method(DBUS_MEDIAPLAYER_INTERFACE, in_signature='', out_signature='')
    def Pause(self):
        self.controls.state_pause()

    #Stop ( )
    @dbus.service.method(DBUS_MEDIAPLAYER_INTERFACE, in_signature='', out_signature='')
    def Stop(self):
        self.controls.state_stop()

    #Play ( )
    @dbus.service.method(DBUS_MEDIAPLAYER_INTERFACE, in_signature='', out_signature='')
    def Play(self):
        self.controls.state_play()

    #PlayPause for test
    @dbus.service.method(DBUS_MEDIAPLAYER_INTERFACE, in_signature='', out_signature='')
    def PlayPause(self):
        self.controls.state_play_pause()

    @dbus.service.method(DBUS_MEDIAPLAYER_INTERFACE, in_signature='', out_signature='s')
    def Identity(self):
        return "foobnix %s" % FOOBNIX_VERSION

    @dbus.service.method(DBUS_MEDIAPLAYER_INTERFACE, in_signature='', out_signature='(qq)')
    def MprisVersion(self):
        return 1, 0

    @dbus.service.method(DBUS_MEDIAPLAYER_INTERFACE, in_signature='', out_signature='')
    def Quit(self):
        self.controls.quit()

    @dbus.service.method(DBUS_MEDIAPLAYER_INTERFACE, in_signature='', out_signature='s')
    def parse_arguments(self, args):
        if args and len(args) > 0:
            self.controls.check_for_media(args)
            result = self.check_for_commands(args)
            if not result:
                self.controls.show()
            if type(result).__name__ == 'str':
                return result
        return "Other copy of player is run"

    def check_for_commands(self, args):
        if len(args) == 1:
            command = args[0]

        elif len(args) == 2:
            command = args[1]
        else:
            return False

        if "--next" == command:
            self.controls.next()
        elif "--prev" == command:
            self.controls.prev()
        elif "--stop" == command:
            self.controls.state_stop()
        elif "--pause" == command:
            self.controls.state_pause()
        elif "--play" == command:
            self.controls.state_play()
        elif "--volume-up" == command:
            self.controls.volume_up()
        elif "--volume-down" == command:
            self.controls.volume_down()
        elif "--mute" == command:
            self.controls.mute()
        elif "--show-hide" == command:
            self.controls.show_hide()
        elif "--show" == command:
            self.controls.show()
        elif "--hide" == command:
            self.controls.hide()
        elif "--play-pause" == command:
            self.controls.play_pause()
        elif "--download" == command:
            self.controls.download()
        elif "--version" == command:
            return FOOBNIX_VERSION
        elif "--state" == command:
            return self.controls.media_engine.current_state
        elif "--now-playing" == command:
            bean = self.controls.notetabs.get_current_tree().get_current_bean_by_UUID()
            if bean:
                return bean.get_display_name()
        else:
            return False
        return True


class MprisSoundMenu(SoundMenuControls):
    def __init__(self, controls):
        self.controls = controls
        SoundMenuControls.__init__(self, "foobnix")


    def _sound_menu_next(self):
        self.controls.next()

    def _sound_menu_previous(self):
        self.controls.prev()

    def _sound_menu_is_playing(self):
        return self.controls.media_engine.current_state is STATE_PLAY

    def _sound_menu_play(self):
        self.controls.state_play()

    def _sound_menu_pause(self):
        self.controls.state_pause()

    @idle_task
    def _sound_menu_raise(self):
        self.controls.main_window.show()

    @dbus.service.method('org.mpris.MediaPlayer2.Player')
    def Stop(self):
        self.controls.state_stop()

    @dbus.service.method('org.mpris.MediaPlayer2.Player')
    def Play(self):
        self.controls.state_play()


def foobnix_dbus_interface():
    try:
        bus = dbus.SessionBus()
        dbus_objects = dbus.Interface(bus.get_object('org.freedesktop.DBus', '/org/freedesktop/DBus'),
                                      'org.freedesktop.DBus').ListNames()

        if not DBUS_NAME in dbus_objects:
            return None
        else:
            return dbus.Interface(bus.get_object(DBUS_NAME, MPRIS_PLAYER_PATH), DBUS_MEDIAPLAYER_INTERFACE)
    except Exception, e:
        logging.error("Dbus error", e)
        return None

########NEW FILE########
__FILENAME__ = filter
#-*- coding: utf-8 -*-
'''
Created on 25 сент. 2010

@author: ivan
'''

from gi.repository import Gtk
from foobnix.gui.state import LoadSave, Filterable
from foobnix.helpers.my_widgets import tab_close_button, ToggleImageButton
from foobnix.helpers.toggled import OneActiveToggledButton
from foobnix.util.key_utils import is_key


class FilterControl(Gtk.HBox, LoadSave):

    def __init__(self, filterabe):
        Gtk.HBox.__init__(self, False, 0)
        LoadSave.__init__(self)

        assert isinstance(filterabe, Filterable)

        self.entry = Gtk.Entry()
        self.entry.connect("key-release-event", self.on_key_press)

        self.search_func = filterabe.filter_by_file

        file_search = ToggleImageButton(Gtk.STOCK_FILE, func=self.set_search_by, param=filterabe.filter_by_file)
        file_search.set_tooltip_text(_("File search"))
        file_search.set_active(True)

        folder_search = ToggleImageButton(Gtk.STOCK_DIRECTORY, func=self.set_search_by, param=filterabe.filter_by_folder)
        folder_search.set_tooltip_text(_("Folder search"))

        self.list = [file_search, folder_search]
        OneActiveToggledButton(self.list)

        """search button"""
        search = tab_close_button(func=self.on_filter, stock=Gtk.STOCK_FIND)

        self.pack_start(file_search, False, False, 0)
        self.pack_start(folder_search, False, False, 0)
        self.pack_start(self.entry, True, True, 0)
        self.pack_start(search, False, False, 0)


    def set_search_by(self, search_func):
        self.search_func = search_func

    def on_key_press(self, w, e):
        if is_key(e, 'Return'):
            self.on_filter()

        if not self.entry.get_text():
            self.on_filter()


    def on_filter(self, *a):
        value = self.entry.get_text()
        self.search_func(value)

    def on_load(self):
        pass

    def on_save(self):
        pass

########NEW FILE########
__FILENAME__ = movie_area
#-*- coding: utf-8 -*-

import logging
import threading

from gi.repository import Gtk
from gi.repository import Gdk
from gi.repository import GLib

from foobnix.gui.controls.playback import PlaybackControls
from foobnix.gui.model.signal import FControl
from foobnix.helpers.my_widgets import notetab_label, ImageButton
from foobnix.helpers.window import ChildTopWindow
from foobnix.util import analytics, idle_task
from foobnix.util.key_utils import is_key, is_key_alt, get_key
from foobnix.util.mouse_utils import is_double_left_click


class AdvancedDrawingArea(Gtk.DrawingArea):
    def __init__(self, controls):
        Gtk.DrawingArea.__init__(self)
        self.controls = controls
        self.set_events(Gdk.EventMask.ALL_EVENTS_MASK) #@UndefinedVariable

        # TODO: check it
        ## self.set_flags(Gtk.CAN_FOCUS)

        self.connect("key-release-event", self.on_key_press)
        self.connect("button-press-event", self.on_button_press)
        self.connect("scroll-event", self.controls.volume.on_scroll_event)

    def action_function(self):
        logging.debug("Template function not defined")

    def on_key_press(self, w, e):
        if is_key(e, 'Escape') or get_key(e) in ('F', 'f', 'а', 'А'):
            self.action_function()
        elif is_key_alt(e) and is_key(e, "Return"):
            self.action_function()
        elif get_key(e) in ('P', 'p', 'з', 'З','space'):
            self.controls.play_pause()
        elif is_key(e, 'Left'):
            self.controls.seek_down()
        elif is_key(e, 'Right'):
            self.controls.seek_up()
        elif is_key(e, 'Up'):
            self.controls.volume_up()
        elif is_key(e, 'Down'):
            self.controls.volume_down()

        self.grab_focus()

    def on_button_press(self, w, e):
        if is_double_left_click(e):
            self.action_function()

        self.grab_focus()

class FullScreanArea(ChildTopWindow):
        def __init__(self, controls, on_hide_callback):
            self.controls = controls
            ChildTopWindow.__init__(self, "movie")
            self.set_hide_on_escape(False)
            self.on_hide_callback = on_hide_callback
            ## TODO: check it
            ##self.set_flags(Gtk.CAN_FOCUS)
            self.layout = Gtk.VBox(False)
            self.set_property("skip-taskbar-hint", True)
            self.set_keep_above(True)
            self.draw = AdvancedDrawingArea(controls)
            self.draw.action_function = on_hide_callback
            self.set_resizable(True)
            self.set_border_width(0)

            self.layout.pack_start(self.draw, True, False, 0)

            self.text_label = Gtk.Label("foobnix")
            self.volume_button = Gtk.VolumeButton()
            self.volume_button.connect("value-changed", self.volume_changed)

            line = Gtk.HBox(False)
            line.pack_start(ImageButton(Gtk.STOCK_FULLSCREEN, on_hide_callback, _("Exit Fullscrean")), False, False, 0)
            line.pack_start(PlaybackControls(controls), False, False, 0)
            line.pack_start(controls.seek_bar_movie, True, False, 0)
            line.pack_start(Gtk.SeparatorToolItem.new(), False, False, 0)
            line.pack_start(self.text_label, False, False, 0)
            line.pack_start(Gtk.SeparatorToolItem.new(), False, False, 0)
            line.pack_start(self.volume_button, False, False, 0)
            line.show_all()

            control_panel = Gtk.Window(Gtk.WindowType.POPUP)
            control_panel.set_size_request(800, -1)
            control_panel.add(line)

            self.add(self.layout)

            self.draw.connect("enter-notify-event", lambda *a: GLib.idle_add(control_panel.hide))

            def my_event(w, e):
                if e.y > Gdk.screen_height() - 5: #@UndefinedVariable
                    def safe_task():
                        control_panel.show()
                        control_panel.set_size_request(Gdk.screen_width(), -1)#@UndefinedVariable
                        control_panel.move(0, Gdk.screen_height() - control_panel.get_allocation().height)#@UndefinedVariable
                    GLib.idle_add(safe_task)

            self.connect("motion-notify-event", my_event)

        def volume_changed(self, volumebutton, value):
            self.controls.volume.set_value(float(value * 100))

        @idle_task
        def set_text(self, text):
            self.text_label.set_text(text)

        def get_draw(self):
            return self.draw

        @idle_task
        def hide_window(self, *a):
            self.hide()

        @idle_task
        def show_window(self):
            self.fullscreen()
            self.volume_button.set_value(float(self.controls.volume.volume_scale.get_value()/ 100))
            self.show_all()


class MovieDrawingArea(FControl, Gtk.Frame):
    def __init__(self, controls):
        FControl.__init__(self, controls)
        Gtk.Frame.__init__(self)

        self.set_label_widget(notetab_label(self.hide))
        self.set_label_align(1.0, 0.0)
        self.set_border_width(0)

        self.smallscree_area = AdvancedDrawingArea(controls)
        self.smallscree_area.action_function = self.on_full_screen

        self.add(self.smallscree_area)

        self.fullscrean_area = FullScreanArea(controls, self.on_small_screen)

        def modyfy_background():
            for state in (Gtk.StateType.NORMAL, Gtk.STATE_PRELIGHT, Gtk.STATE_ACTIVE, Gtk.STATE_SELECTED, Gtk.STATE_INSENSITIVE):
                self.smallscree_area.modify_bg(state, self.smallscree_area.get_colormap().alloc_color("black"))
                self.fullscrean_area.draw.modify_bg(state, self.fullscrean_area.get_colormap().alloc_color("black"))
        # TODO Fix it
        #GLib.idle_add(modyfy_background)

        self.output = None
        self.set_output(self.smallscree_area)

    def set_output(self, area):
        self.output = area


    def get_output(self):
        return self.output

    def get_draw(self):
        return self.smallscree_area

    def on_full_screen(self):
        self.controls.state_stop(True)
        self.fullscrean_area.show_window()
        self.set_output(self.fullscrean_area.get_draw())
        self.controls.state_play(under_pointer_icon=True)
        analytics.action("FullScreanArea")

    @idle_task
    def set_text(self, text):
        self.fullscrean_area.set_text(text)

    def on_small_screen(self):
        self.controls.state_stop(True)
        self.set_output(self.smallscree_area)
        self.fullscrean_area.hide_window()
        self.controls.state_play(under_pointer_icon=True)

    @idle_task
    def draw_video(self, message):
        message_name = message.get_structure().get_name()

        if message_name == "prepare-xwindow-id":
            imagesink = message.src

            imagesink.set_property("force-aspect-ratio", True)
            self.show_all()
            imagesink.set_xwindow_id(self.get_output().window.xid)

            '''trick to amoid possible black screen in movie_area'''
            threading.Timer(0.5, lambda: self.get_output().set_size_request(-1, 400)).start()

########NEW FILE########
__FILENAME__ = playback
'''
Created on Sep 27, 2010

@author: ivan
'''

from gi.repository import Gtk

from foobnix.util import const
from foobnix.fc.fc import FC
from foobnix.gui.state import LoadSave
from foobnix.helpers.toolbar import MyToolbar
from foobnix.gui.model.signal import FControl
from foobnix.helpers.my_widgets import ImageButton, EventLabel


class OrderShuffleControls(FControl, Gtk.HBox, LoadSave):
    def __init__(self, controls):
        Gtk.HBox.__init__(self, False)

        self.toggle_buttons = OrderShuffleControls_ZAVLAB(controls)

        self.rlabel = EventLabel(text="S", func=lambda * a: self.on_random())
        self.olabel = EventLabel(text="R", func=lambda * a: self.on_order())

        self.pack_start(self.rlabel, False, False, 0)
        self.pack_start(Gtk.Label(" "), False, False, 0)
        self.pack_start(self.olabel, False, False, 0)
        self.pack_start(self.toggle_buttons, False, False, 0)

        self.pack_start(Gtk.SeparatorToolItem.new(), False, False, 0)

    def update(self):
        if FC().is_order_random:
            self.rlabel.set_markup("<b>S</b>")
            self.rlabel.set_tooltip_text(_("Shuffle on"))

        else:
            self.rlabel.set_markup("S")
            self.rlabel.set_tooltip_text(_("Shuffle off"))

        if FC().repeat_state == const.REPEAT_ALL:
            self.olabel.set_markup("<b>R</b>")
            self.olabel.set_tooltip_text(_("Repeat all"))
        elif FC().repeat_state == const.REPEAT_SINGLE:
            self.olabel.set_markup("<b>R1</b>")
            self.olabel.set_tooltip_text(_("Repeat single"))
        else:
            self.olabel.set_markup("R")
            self.olabel.set_tooltip_text(_("Repeat off"))

    def on_random(self, *a):
        FC().is_order_random = not FC().is_order_random
        self.update()

    def on_order(self):
        if FC().repeat_state == const.REPEAT_ALL:
            FC().repeat_state = const.REPEAT_SINGLE
        elif FC().repeat_state == const.REPEAT_SINGLE:
            FC().repeat_state = const.REPEAT_NO
        elif FC().repeat_state == const.REPEAT_NO:
            FC().repeat_state = const.REPEAT_ALL
        self.update()

    def on_load(self):
        if FC().order_repeat_style == "ToggleButtons":
            self.toggle_buttons.on_load()
            self.olabel.hide()
            self.rlabel.hide()
            self.toggle_buttons.show()
        else:
            self.update()
            self.toggle_buttons.hide()
            self.olabel.show()
            self.rlabel.show()

    def on_save(self): pass


class OrderShuffleControls_ZAVLAB(FControl, Gtk.HBox, LoadSave):
    def __init__(self, controls):
        Gtk.HBox.__init__(self, False)

        self.order = Gtk.ToggleButton()
        order_image = Gtk.Image.new_from_stock(Gtk.STOCK_REDO, Gtk.IconSize.BUTTON)
        self.order.add(order_image)
        self.order.set_relief(Gtk.ReliefStyle.NONE)
        self.order.set_focus_on_click(False)

        self.order.connect("button-press-event", self.on_order)

        self.pack_start(self.order, False, False, 0)

        self.repeat = Gtk.ToggleButton()
        repeat_image = Gtk.Image.new_from_stock(Gtk.STOCK_REFRESH, Gtk.IconSize.BUTTON)
        self.repeat.add(repeat_image)
        self.repeat.set_relief(Gtk.ReliefStyle.NONE)
        self.repeat.set_focus_on_click(False)

        try:
            self.order.set_has_tooltip(True)
            self.repeat.set_has_tooltip(True)
        except:
            pass

        self.repeat.connect("button-press-event", self.choise)
        self.pack_start(self.repeat, False, False, 0)

        #self.pack_start(Gtk.SeparatorToolItem.new())

        self.menu = Gtk.Menu()
        self.item_all = Gtk.CheckMenuItem(_("Repeat all"))
        self.item_all.connect("button-press-event", self.on_repeat)
        self.menu.append(self.item_all)
        self.item_single = Gtk.CheckMenuItem(_("Repeat single"))
        self.item_single.connect("button-press-event", lambda item, *a: self.on_repeat(item, False))
        self.menu.append(self.item_single)

    def choise(self, widget, event):
            self.menu.popup(None, None, None, None, event.button, event.time)
            self.menu.show_all()

    def on_load(self):
        if FC().is_order_random:
            self.order.set_active(True)
            self.order.set_tooltip_text(_("Shuffle on"))
        else:
            self.order.set_active(False)
            self.order.set_tooltip_text(_("Shuffle off"))

        if FC().repeat_state == const.REPEAT_ALL:
            self.repeat.set_active(True)
            self.repeat.set_tooltip_text(_("Repeat all"))
            self.item_all.set_active(True)
        elif FC().repeat_state == const.REPEAT_SINGLE:
            self.repeat.set_active(True)
            self.repeat.set_tooltip_text(_("Repeat single"))
            self.item_single.set_active(True)
        else:
            self.repeat.set_active(False)
            self.repeat.set_tooltip_text(_("Repeat off"))

    def on_order(self, *a):
        FC().is_order_random = not FC().is_order_random
        if FC().is_order_random:
            self.order.set_tooltip_text(_("Shuffle on"))
        else:
            self.order.set_tooltip_text(_("Shuffle off"))

    def on_repeat(self, item, all=True):
        is_active = item.get_active()
        for menu_item in self.menu:
            menu_item.set_active(False)
        if all:
            if not is_active:
                FC().repeat_state = const.REPEAT_ALL
                self.repeat.set_tooltip_text(_("Repeat all"))
                self.repeat.set_active(True)
            else:
                FC().repeat_state = const.REPEAT_NO
                item.set_active(True) #because signal "toggled" will change the value to the opposite
                self.repeat.set_active(False)
        elif not all:
            if not is_active:
                FC().repeat_state = const.REPEAT_SINGLE
                self.repeat.set_tooltip_text(_("Repeat single"))
                self.repeat.set_active(True)
            else:
                FC().repeat_state = const.REPEAT_NO
                item.set_active(True) #because signal "toggled" will change the value to the opposite
                self.repeat.set_active(False)

    def on_save(self): pass


class PlaybackControls(FControl, Gtk.HBox, LoadSave):
    def __init__(self, controls):
        Gtk.HBox.__init__(self, False)
        self.pack_start(Gtk.SeparatorToolItem.new(), False, False, 0)
        self.pack_start(ImageButton(Gtk.STOCK_MEDIA_STOP, controls.state_stop, _("Stop")), False, False, 0)
        self.pack_start(ImageButton(Gtk.STOCK_MEDIA_PLAY, controls.state_play, _("Play")), False, False, 0)
        self.pack_start(ImageButton(Gtk.STOCK_MEDIA_PAUSE, controls.state_play_pause, _("Pause")), False, False, 0)
        self.pack_start(ImageButton(Gtk.STOCK_MEDIA_PREVIOUS, controls.prev, _("Previous")), False, False, 0)
        self.pack_start(ImageButton(Gtk.STOCK_MEDIA_NEXT, controls.next, _("Next")), False, False, 0)
        self.pack_start(Gtk.SeparatorToolItem.new(), False, False, 0)


    def on_load(self): pass
    def on_save(self): pass

########NEW FILE########
__FILENAME__ = record
'''
Created on Mar 23, 2011

@author: zavlab1
'''
import os
import shutil
import logging
from gi.repository import Gtk
from gi.repository import Gst
from foobnix.helpers.dialog_entry import FileSavingDialog


class RadioRecord(Gtk.ToggleButton):
    def __init__(self, controls):
        Gtk.ToggleButton.__init__(self)
        self.controls = controls
        
        rec_image = Gtk.Image.new_from_stock(Gtk.STOCK_MEDIA_RECORD, Gtk.IconSize.BUTTON)
        rec_image.show()
        self.add(rec_image)
        self.set_relief(Gtk.ReliefStyle.NONE)
        self.set_focus_on_click(False)
        self.connect("toggled", self.on_toggle)
        self.set_tooltip_text(_("Record radio"))
        self.set_no_show_all(True)
        self.hide()
        
    def on_toggle(self, a):
        engine = self.controls.media_engine
            
        if engine.radio_recording:
            engine.stop_radio_record()
            if os.path.isfile(engine.radio_path):
                name = os.path.splitext(os.path.basename(engine.radio_path))[0] + ".ogg"
            else:
                name = "radio_record.ogg"

            temp_file = os.path.join("/tmp", name)
            if not os.path.exists(temp_file):
                logging.warning(_("So file doesn't exist. Pehaps it wasn't create yet."))
                return

            def func(filename, folder):
                try:
                    shutil.move(temp_file, os.path.join(folder, filename))
                except IOError, e:
                    logging.error(e)

            FileSavingDialog(_("Save file as ..."), func, args=None,
                             current_folder=os.path.expanduser("~"), current_name=name)
        else:
            bean = self.controls.notetabs.get_current_tree().get_current_bean_by_UUID()
            engine.record_radio(bean)
########NEW FILE########
__FILENAME__ = search_progress
#-*- coding: utf-8 -*-
'''
Created on 27 сент. 2010

@author: ivan
'''

from gi.repository import Gtk
from gi.repository import Gdk

from foobnix.util import idle_task


class SearchProgress(Gtk.Spinner):
    def __init__(self, controls):
        Gtk.Spinner.__init__(self)
        self.controls = controls
        self.set_no_show_all(True)
        self.main_window = self.controls.main_window
        self.set_size_request(30, 30)
        self.set_halign(Gtk.Align.END)
        self.set_valign(Gtk.Align.END)

        self.override_background_color(Gtk.StateType.NORMAL, Gdk.RGBA(255, 255, 255))

    @idle_task
    def start(self, text=None):
        self.show()
        super(SearchProgress, self).start()

    @idle_task
    def stop(self):
        super(SearchProgress, self).stop()
        self.hide()

    def background_spinner_wrapper(self, task, *args):
        self.start()
        while Gtk.events_pending():
            Gtk.main_iteration()
        try:
            task(*args)
        finally:
            self.stop()

    '''def background_spinner_wrapper(self, task, in_graphic_thread, *args):
        self.start()

        def thread_task(*args):
            def safe_task(*args):
                try:
                    task(*args)
                finally:
                    self.stop()
            if in_graphic_thread:
                GLib.idle_add(safe_task, *args)
            else:
                safe_task(*args)

        t = threading.Thread(target=thread_task, args=(args))
        t.start()'''

    def move_to_coord(self, *a):
        pl_tree = self.controls.notetabs.get_current_tree()
        pl_tree_alloc = pl_tree.get_allocation()
        scrolled_pl_tree_alloc = pl_tree.scroll.get_allocation()
        try:
            pl_tree_width = pl_tree_alloc.width
            scrolled_pl_tree_width = scrolled_pl_tree_alloc.width
        except:
            pl_tree_width = 0
            scrolled_pl_tree_width = 0
        try:
            pl_tree_height = pl_tree_alloc.height
            scrolled_pl_tree_height = scrolled_pl_tree_alloc.height
        except:
            pl_tree_height = 0
            scrolled_pl_tree_height = 0

        self.set_margin_bottom(scrolled_pl_tree_height - pl_tree_height + 5)
        self.set_margin_right(scrolled_pl_tree_width - pl_tree_width + 5)

    def show(self):
        super(SearchProgress, self).show()
        self.move_to_coord()
########NEW FILE########
__FILENAME__ = seekbar
#-*- coding: utf-8 -*-
'''
Created on 28 сент. 2010

@author: ivan
'''

from gi.repository import Gtk
from gi.repository import Gdk
from gi.repository import Pango

from foobnix.util import idle_task
from foobnix.util.const import FTYPE_RADIO
from foobnix.gui.model.signal import FControl
from foobnix.util.time_utils import convert_seconds_to_text


class SeekProgressBarControls(FControl, Gtk.Alignment):
    def __init__(self, controls, seek_bar_movie=None):
        FControl.__init__(self, controls)
        self.seek_bar_movie = seek_bar_movie
        Gtk.Alignment.__init__(self, xalign=0.5, yalign=0.5, xscale=1.0, yscale=1.0)

        self.set_padding(padding_top=7, padding_bottom=7, padding_left=0, padding_right=7)

        self.tooltip = Gtk.Window(Gtk.WindowType.POPUP)
        self.tooltip.set_position(Gtk.WindowPosition.CENTER)
        self.tooltip_label = Gtk.Label()
        self.tooltip.add(self.tooltip_label)

        self.progressbar = Gtk.ProgressBar()
        self.progressbar.set_ellipsize(Pango.EllipsizeMode.END)
        self.progressbar.set_property("show-text", True)
        self.progressbar.set_text("00:00 / 00:00")
        try:
            self.progressbar.set_has_tooltip(True)
        except:
            #fix debian compability
            pass

        event = Gtk.EventBox()
        event.add(self.progressbar)
        event.connect("button-press-event", self.on_seek)
        event.connect("leave-notify-event", lambda *a: self.safe_hide_tooltip())
        event.connect("motion-notify-event", self.on_pointer_motion)
        self.add(event)
        self.show_all()
        self.tooltip.hide()

    @idle_task
    def safe_hide_tooltip(self):
        self.tooltip.hide()

    @idle_task
    def on_pointer_motion(self, widget, event):
        width = self.progressbar.get_allocation().width
        x = event.x
        duration = self.controls.media_engine.duration_sec
        seek_percent = (x + 0.0) / width
        sec = int(duration * seek_percent)
        sec = convert_seconds_to_text(sec)

        self.tooltip_label.set_text(sec)
        self.tooltip.show_all()
        unknown_var, x, y, mask = Gdk.get_default_root_window().get_pointer()
        self.tooltip.move(x+5, y-15)

    def on_seek(self, widget, event):
        bean = self.controls.media_engine.bean
        if bean and bean.type == FTYPE_RADIO:
            return None

        width = widget.get_allocation().width
        x = event.x
        seek_percent = (x + 0.0) / width * 100
        self.controls.player_seek(seek_percent)

        if self.seek_bar_movie:
            self.seek_bar_movie.on_seek(widget, event)

    @idle_task
    def set_text(self, text):
        if text:
            self.progressbar.set_text(text[:200])

        if self.seek_bar_movie:
            self.seek_bar_movie.set_text(text)

    @idle_task
    def clear(self):
        self.progressbar.set_text("00:00 / 00:00")
        self.progressbar.set_fraction(0)

        if self.seek_bar_movie:
            self.seek_bar_movie.clear()

    @idle_task
    def fill_seekbar(self):
        self.progressbar.set_fraction(1)

    @idle_task
    def update_seek_status(self, position_sec, duration_sec):
        if duration_sec == 0:
            seek_text = "00:00 / 00:00"
            seek_persent = 0.999
        else:
            duration_str = convert_seconds_to_text(duration_sec)
            position_str = convert_seconds_to_text(position_sec)
            seek_persent = (position_sec + 0.0) / duration_sec
            seek_text = position_str + " / " + duration_str

        if 0 <= seek_persent <= 1:
            self.progressbar.set_text(seek_text)
            self.progressbar.set_fraction(seek_persent)

        if self.seek_bar_movie:
            self.seek_bar_movie.update_seek_status(position_sec, duration_sec)

########NEW FILE########
__FILENAME__ = status_bar
#-*- coding: utf-8 -*-
'''
Created on 28 сент. 2010

@author: ivan
'''
from gi.repository import Gtk
from foobnix.util import idle_task
from foobnix.gui.model.signal import FControl


class StatusbarControls(Gtk.Statusbar, FControl):
    def __init__(self, controls):
        Gtk.Statusbar.__init__(self)
        FControl.__init__(self, controls)
        self.show()
        self.get_children()[0].set_shadow_type(Gtk.ShadowType.NONE)

    @idle_task
    def set_text(self, text):
        if text:
            self.push(0, text)
        else:
            self.push(0, "")


########NEW FILE########
__FILENAME__ = tray_icon
#-*- coding: utf-8 -*-
'''
Created on 29 сент. 2010

@author: ivan
'''

import logging

from gi.repository import Gdk
from gi.repository import Gtk
from gi.repository import Notify

from foobnix.fc.fc import FC
from foobnix.gui.controls.playback import PlaybackControls
from foobnix.gui.model import FModel
from foobnix.gui.model.signal import FControl
from foobnix.gui.service.path_service import get_foobnix_resourse_path_by_name
from foobnix.gui.state import LoadSave
from foobnix.helpers.image import ImageBase
from foobnix.helpers.my_widgets import ImageButton, AlternateVolumeControl
from foobnix.helpers.pref_widgets import VBoxDecorator
from foobnix.util import idle_task
from foobnix.util.const import ICON_FOOBNIX
from foobnix.util.mouse_utils import is_middle_click
from foobnix.util.text_utils import split_string


class PopupTrayWindow (Gtk.Window, FControl):
    def __init__(self, controls):
        FControl.__init__(self, controls)
        Gtk.Window.__init__(self, Gtk.WindowType.POPUP)

        self.set_position(Gtk.WindowPosition.MOUSE)
        self.connect("leave-notify-event", self.on_leave_window)
        Notify.init('Foobnix')

    def on_leave_window(self, w, event):
        max_x, max_y = w.size_request()
        x, y = event.x, event.y
        if 0 < x < max_x and 0 < y < max_y:
            return True
        self.hide()


class PopupMenuWindow(PopupTrayWindow):
    def __init__ (self, controls):
        PopupTrayWindow.__init__(self, controls)
        #self.modify_bg(Gtk.StateType.NORMAL, self.get_colormap().alloc_color("gray23"))
        vbox = Gtk.VBox(False, 0)

        playcontrols = PlaybackControls(controls)
        playcontrols.pack_start(ImageButton(Gtk.STOCK_QUIT, controls.quit, _("Exit")), False, False, 0)
        playcontrols.pack_start(ImageButton(Gtk.STOCK_OK, self.hide, _("Close Popup")), False, False, 0)

        self.poopup_text = Gtk.Label()
        self.set_text("Foobnix")
        self.poopup_text.set_line_wrap(True)

        vbox.pack_start(playcontrols, False, False, 0)
        vbox.pack_start(self.poopup_text, False, False, 0)
        self.add(vbox)
        self.show_all()
        self.hide()

    @idle_task
    def set_text(self, text):
        text = unicode(text)
        self.poopup_text.set_text(text[:40])

        '''set colour of text'''
        self.poopup_text.modify_fg(Gtk.StateType.NORMAL,
                                   Gdk.color_parse('#FFFFFF'))


class PopupVolumeWindow(PopupTrayWindow):
    def __init__(self, controls, popup_menu_window):
        PopupTrayWindow.__init__(self, controls)

        height = popup_menu_window.get_size()[1]
        width = height * 3
        self.set_size_request(width, height)
        self.avc = AlternateVolumeControl(levels=35, s_width=2, interval=1, v_step=1)
        #self.avc.modify_bg(Gtk.StateType.NORMAL, self.get_colormap().alloc_color("gray23"))
        ebox = Gtk.EventBox()
        ebox.add(self.avc)
        ebox.connect("scroll-event", self.controls.volume.on_scroll_event)
        self.add (ebox)
        self.show_all()
        self.hide()

class TrayIconControls(Gtk.StatusIcon, ImageBase, FControl, LoadSave):
    def __init__(self, controls):
        FControl.__init__(self, controls)
        Gtk.StatusIcon.__init__(self)
        self.hide()
        ImageBase.__init__(self, ICON_FOOBNIX, 150)

        self.popup_menu = PopupMenuWindow(self.controls)
        self.popup_volume_contol = PopupVolumeWindow(self.controls, self.popup_menu)

        self.connect("activate", self.on_activate)
        self.connect("popup-menu", self.on_popup_menu)

        try:
            self.set_has_tooltip(True)
            self.tooltip = Gtk.Tooltip()
            self.set_tooltip("Foobnix music player")
            self.connect("query-tooltip", self.on_query_tooltip)
            self.connect("button-press-event", self.on_button_press)
            self.connect("scroll-event", self.on_scroll)
        except Exception, e:
            logging.warn("On debian it doesn't work" + str(e))

        self.current_bean = FModel().add_artist("Artist").add_title("Title")
        self.tooltip_image = ImageBase(ICON_FOOBNIX, 75)

        self._previous_notify = None

    def on_save(self):
        pass

    def on_scroll (self, button, event):
        self.controls.volume.on_scroll_event(button, event)
        self.popup_volume_contol.show()

    def on_load(self):
        if FC().show_tray_icon:
            self.set_from_file(get_foobnix_resourse_path_by_name(ICON_FOOBNIX))
            self.show()

    def update_info_from(self, bean):
        self.current_bean = bean
        if bean.artist:
            artist = bean.artist
            self.tooltip_image.size = 150
        else:
            artist = 'Unknown artist'
            self.tooltip_image.size = 75
            self.tooltip_image.resource = ICON_FOOBNIX
        self.tooltip_image.update_info_from(bean)

        if bean.title:
            title = bean.title
        else:
            title = bean.text
        if FC().change_tray_icon:
            super(TrayIconControls, self).update_info_from(bean)

        if FC().notifier:
            self.to_notify(artist, title)

    @idle_task
    def to_notify(self, artist, title):
            message = "%s%s" % (artist, title)
            if self._previous_notify == message:
                return
            self._previous_notify = message
            notification = Notify.Notification.new(artist, title, "")
            notification.set_urgency(Notify.Urgency.LOW)
            notification.set_timeout(FC().notify_time)
            if self.tooltip_image.get_pixbuf() != None:
                notification.set_icon_from_pixbuf(self.tooltip_image.get_pixbuf())
            notification.show()

    def on_query_tooltip(self, widget, x, y, keyboard_tip, tooltip):
        artist = "Artist"
        title = "Title"
        if self.current_bean:
            if self.current_bean.artist and self.current_bean.title:
                artist = self.current_bean.artist
                #artist = string.join(["&amp;" if x == '&' else x for x in artist], '')
                artist = artist.replace('&', '&amp;')
                title = self.current_bean.title
            else:
                artist = "Unknown artist"
                title = self.current_bean.text

        max_str_len = 40
        if len(title) > max_str_len:
            title = split_string(title, max_str_len)

        alabel = Gtk.Label()
        alabel.set_markup("<b>%s</b>" % artist)
        hbox1 = Gtk.HBox()
        hbox1.pack_start(alabel, False, False)
        hbox2 = Gtk.HBox()
        hbox2.pack_start(Gtk.Label(title), False, False)
        vbox = VBoxDecorator(Gtk.Label(), hbox1, Gtk.Label(), hbox2)
        if self.tooltip_image.size == 150:
            alignment = Gtk.Alignment(0, 0.4)
        else:
            alignment = Gtk.Alignment()
        alignment.set_padding(padding_top=0, padding_bottom=0, padding_left=10, padding_right=10)
        alignment.add(vbox)
        tooltip.set_icon(self.tooltip_image.get_pixbuf())
        tooltip.set_custom(alignment)
        return True

    def on_activate(self, *a):
        self.controls.windows_visibility()

    def on_button_press(self, w, e):
        if is_middle_click(e):
            self.controls.play_pause()

    def hide(self):
        self.set_visible(False)

    def show(self):
        self.set_visible(True)

    def show_window(self, *a):
        self.popup_menu.reshow_with_initial_size()
        self.popup_menu.show()

    def hide_window(self, *a):
        self.popup_menu.hide()

    def on_popup_menu(self, *a):
        self.show_window()

    @idle_task
    def set_text(self, text):
        self.popup_menu.set_text(text)
        self.set_tooltip_text(text)

########NEW FILE########
__FILENAME__ = volume
#-*- coding: utf-8 -*-
'''
Created on 28 сент. 2010

@author: ivan
'''

from gi.repository import Gtk
from gi.repository import Gdk
from foobnix.fc.fc import FC
from foobnix.gui.state import LoadSave
from foobnix.gui.model.signal import FControl


class VolumeControls(LoadSave, Gtk.HBox, FControl):
    MAX_VALUE = 100

    def __init__(self, controls):
        Gtk.HBox.__init__(self, False, 0)
        FControl.__init__(self, controls)

        adjustment = Gtk.Adjustment(value=1, lower=0, upper=self.MAX_VALUE, step_incr=0, page_incr=0, page_size=0)
        self.volume_scale = Gtk.HScale(adjustment=adjustment)
        self.volume_scale.connect("value-changed", self.on_value_changed)
        self.volume_scale.connect("scroll-event", self.on_scroll_event)
        self.volume_scale.connect("button-press-event", self.on_volume_change)
        self.volume_scale.set_size_request(200, -1)
        self.volume_scale.set_digits(1)
        self.volume_scale.set_draw_value(False)

        self.pack_start(self.volume_scale, False, False, 0)

        self.show_all()

    def on_volume_change(self, w, event):
        max_x, max_y = w.size_request()
        x, y = event.x, event.y
        value = x / max_x * self.MAX_VALUE
        if value > self.MAX_VALUE * 0.75:
            value += self.MAX_VALUE / 20
        elif value < self.MAX_VALUE * 0.25:
            value -= self.MAX_VALUE / 20

        self.set_value(value)
        self.on_save()

    def get_value(self):
        self.volume_scale.get_value()

    def set_value(self, value):
        self.volume_scale.set_value(value)

    def volume_up(self):
        value = self.volume_scale.get_value()
        self.volume_scale.set_value(value + 3)

    def volume_down(self):
        value = self.volume_scale.get_value()
        self.volume_scale.set_value(value - 3)

    def mute(self):
        value = self.volume_scale.get_value()
        if value == 0:
            self.volume_scale.set_value(FC().temp_volume)
        else:
            FC().temp_volume = value
            self.volume_scale.set_value(0)

    def on_scroll_event(self, button, event):
        value = self.volume_scale.get_value()
        if event.direction == Gdk.ScrollDirection.UP or \
                (event.direction == Gdk.ScrollDirection.SMOOTH and event.delta_y <= 0.):     #@UndefinedVariable
            self.volume_scale.set_value(value + 15)
        else:
            self.volume_scale.set_value(value - 15)
        self.controls.player_volume(value)
        return True

    def on_value_changed(self, widget):
        percent = widget.get_value()
        self.controls.player_volume(percent)
        FC().volume = percent
        self.controls.trayicon.popup_volume_contol.avc.set_volume(percent)

    def on_save(self):
        pass

    def on_load(self):
        self.volume_scale.set_value(FC().volume)

########NEW FILE########
__FILENAME__ = coverlyrics
'''
Created on Apr 17, 2011

@author: zavlab1
'''

from gi.repository import Gtk

from foobnix.fc.fc import FC
from foobnix.helpers.image import ImageBase
from foobnix.helpers.textarea import TextArea
from foobnix.util.const import ICON_BLANK_DISK


class CoverLyricsPanel(Gtk.Frame):
    def __init__(self, controls):
        Gtk.Frame.__init__(self)
        vbox = Gtk.VBox(False, 5)
        self.controls = controls
        self.set_size_request(100, 200)
        self.album_title = Gtk.Label(_("Album title"))
        image_size = FC().main_window_size[2] - (FC().hpaned_right + 16)
        self.image = ImageBase(ICON_BLANK_DISK, size=image_size)
        image_frame = Gtk.Frame()
        image_frame.add(self.image)
        image_frame.set_label_widget(Gtk.Label(_("Cover:")))
        vbox.pack_start(image_frame, False, False, 0)

        self.lyrics = TextArea()
        self.lyrics.connect("size-allocate", self.adapt_image)
        lyrics_frame = Gtk.Frame()
        lyrics_frame.add(self.lyrics)
        lyrics_frame.set_label_widget(Gtk.Label(_("Lyric:")))
        vbox.pack_start(lyrics_frame, True, True, 0)

        self.add(vbox)
        self.set_label_widget(self.album_title)
        self.show_all()


    def get_pixbuf(self):
        return self.controls.perspectives.get_perspective('info').get_widget().image.pixbuf

    def set_cover(self):
        pixbuf = self.get_pixbuf()
        self.image.size = FC().info_panel_image_size
        self.image.set_from_pixbuf(pixbuf)

    def adapt_image(self, *a):
        dif = self.lyrics.get_allocation().width - self.image.get_allocation().width
        if self.lyrics.get_property("visible") and dif < 2:
            self.image.size = self.lyrics.get_allocation().width - 20
            self.image.set_from_pixbuf(self.controls.coverlyrics.get_pixbuf())


########NEW FILE########
__FILENAME__ = gstreamer
#-*- coding: utf-8 -*-
'''
Created on 28 сент. 2010

@author: ivan
'''

import os
import time
import thread
import logging

import gi
gi.require_version('Gst', '1.0')
from gi.repository import Gst
from gi.repository import GLib
from gi.repository import GObject

from foobnix.fc.fc import FC
from foobnix.util.id3_util import correct_encoding
from foobnix.gui.engine import MediaPlayerEngine
from foobnix.util.plsparser import get_radio_source
from foobnix.util.const import STATE_STOP, STATE_PLAY, STATE_PAUSE, FTYPE_RADIO

Gst.init("")


class RecorderBin(Gst.Bin):

    def __init__(self, name=None):
        super(RecorderBin, self).__init__(name=name)

        self.vorbisenc = Gst.ElementFactory.make("vorbisenc", "vorbisenc")
        self.oggmux = Gst.ElementFactory.make("oggmux", "oggmux")
        self.filesink = Gst.ElementFactory.make("filesink", "filesink")

        self.add(self.vorbisenc)
        self.add(self.oggmux)
        self.add(self.filesink)

        self.vorbisenc.link(self.oggmux)
        self.oggmux.link(self.filesink)

        self.sink_pad = Gst.GhostPad.new("sink", self.vorbisenc.get_static_pad("sink"))
        self.add_pad(self.sink_pad)

    def set_location(self, location):
        self.filesink.set_property("location", location)


class GStreamerEngine(MediaPlayerEngine, GObject.GObject):
    NANO_SECONDS = 1000000000
    SPECT_BANDS = 10
    AUDIOFREQ = 44100

    def __init__(self, controls):
        MediaPlayerEngine.__init__(self, controls)
        GObject.GObject.__init__(self)
        self.bean = None
        self.position_sec = 0
        self.duration_sec = 0

        self.prev_path = None

        self.equalizer = None

        self.current_state = STATE_STOP
        self.remembered_seek_position = 0
        self.error_counter = 0
        self.radio_recording = False
        self.buffering = False
        self.player = self.gstreamer_player()

    def get_state(self):
        return self.current_state

    def set_state(self, state):
        self.current_state = state

    def gstreamer_player(self):
        '''
        Filesrc -----+                                                      + -> volume -> equalizer -> audiosink
                     |-> (queue2) -> (decodebin -> audioconvert) -> tee ->  |
        souphttpsrc -+                                                      + -> vorbisenc -> oggmux -> filesink
                                                                            |___________________________________|
                                                                                        Dynamic part
        '''
        playbin = Gst.Pipeline()
        self.fsource = Gst.ElementFactory.make("filesrc", "fsource")
        self.init_hsource()
        volume = Gst.ElementFactory.make("volume", "volume")
        audioconvert = Gst.ElementFactory.make("audioconvert", "audioconvert")
        audiosink = Gst.ElementFactory.make("autoaudiosink", "autoaudiosink")
        self.decodebin = Gst.ElementFactory.make("decodebin", "decode")
        self.equalizer = Gst.ElementFactory.make('equalizer-10bands', 'equalizer')

        self.tee = Gst.ElementFactory.make("tee", "tee")

        #self.spectrum = Gst.ElementFactory.make('spectrum', 'spectrum')
        #self.spectrum.set_property("bands", self.SPECT_BANDS)
        #self.spectrum.set_property("threshold", -80)
        #self.spectrum.set_property("message-phase", True)

        def on_new_decoded_pad(dbin, pad):
            pad.link(audioconvert.get_static_pad("sink"))

        self.decodebin.connect("pad-added", on_new_decoded_pad)

        playbin.add(self.decodebin)
        playbin.add(volume)
        playbin.add(audioconvert)
        playbin.add(audiosink)
        playbin.add(self.tee)
        playbin.add(self.equalizer)

        #self.queue.link_pads("src", self.decodebin, "sink")
        audioconvert.link_pads("src", self.tee, "sink")
        self.tee.link_pads("src_0", volume, "sink")
        volume.link(self.equalizer)
        self.equalizer.link(audiosink)

        bus = playbin.get_bus()
        bus.add_signal_watch()
        bus.enable_sync_message_emission()
        bus.connect("message", self.on_message)
        bus.connect("sync-message::element", self.on_sync_message)

        return playbin

    def realign_eq(self):
        if FC().is_eq_enable:
            pre = self.controls.eq.get_preamp()
            bands = self.controls.eq.get_bands()
            self.set_all_bands(pre, bands, force=True)
        else:
            self.set_all_bands(0, [0] * 10, force=True)

    def init_hsource(self):
        self.hsource = Gst.ElementFactory.make("souphttpsrc", "hsource")
        self.hsource.set_property("user-agent", "Fooobnix music player")
        self.hsource.set_property("automatic-redirect", "false")

        self.queue = Gst.ElementFactory.make("queue2", "queue")
        self.queue.set_property("use-buffering", True)
        self.queue.set_property("low-percent", 10)
        self.queue.set_property("max-size-buffers", 0)
        self.queue.set_property("max-size-time", 0)
        buff = int(FC().network_buffer_size)
        if not buff:
            buff = 128
        self.queue.set_property("max-size-bytes", buff * 1024)   # 128Kb

    def notify_init(self, duration_int):
        logging.debug("Pre init thread: " + str(duration_int))

    def notify_playing(self, position_int, duration_int):
        #LOG.debug("Notify playing", position_int)
        self.position_sec = position_int / self.NANO_SECONDS
        self.duration_sec = duration_int / self.NANO_SECONDS
        self.controls.notify_playing(self.position_sec, self.duration_sec, self.bean)

    def notify_eos(self):
        logging.debug("Notify eos, STOP State")

        self.emit('eos-signal')
        self.controls.notify_eos()
        self.set_state(STATE_STOP)

    def notify_title(self, text):
        if not text:
            return
        if self._is_remote():
            "notify radio playing"

            self.emit("title-changed", self.bean, text)
            self.controls.notify_title(self.bean, text)

    def notify_error(self, msg):
        logging.debug("Notify error, STOP state")
        self.set_state(STATE_STOP)
        self.controls.notify_error(msg)

    def record_radio(self, bean):
        if os.path.isfile(self.radio_path):
            file_name = os.path.join("/tmp", os.path.splitext(os.path.basename(self.radio_path))[0] + ".ogg")
        else:
            file_name = os.path.join("/tmp", "radio_record.ogg")
        self.recorder = RecorderBin(name="recorder")
        self.player.add(self.recorder)
        self.tee.link_pads("src_1", self.recorder, "sink")
        self.recorder.set_location(file_name)
        self.recorder.sync_state_with_parent()
        self.radio_recording = True

    def stop_radio_record(self):
        if not self.radio_recording:
            return
        self.recorder.set_state(Gst.State.NULL)
        self.tee.unlink_pads("src_1", self.recorder, 'sink')
        self.player.remove(self.recorder)
        self.radio_recording = False

    def play(self, bean):
        if not bean or not bean.path:
            logging.error("Bean or path is None")
            return None

        self.bean = bean

        self.state_stop(show_in_tray=False)
        self.player.set_state(Gst.State.NULL)

        if self.radio_recording:
            self.stop_radio_record()

        if bean.path.startswith("http://"):
            self.radio_path = get_radio_source(bean.path)
            logging.debug("Try To play path " + self.radio_path)
            uri = self.radio_path

            if not self.bean.type == FTYPE_RADIO:
                self.notify_title(uri)
        else:
            uri = bean.path

        logging.info("Gstreamer try to play " + uri)

        self.fsource.set_state(Gst.State.NULL)
        self.hsource.set_state(Gst.State.NULL)
        self.fsource.unlink(self.decodebin)
        self.hsource.unlink(self.queue)
        self.queue.unlink(self.decodebin)
        if self.player.get_by_name("fsource"):
            self.player.remove(self.fsource)
        if self.player.get_by_name("hsource"):
            self.player.remove(self.hsource)
            self.player.remove(self.queue)
        if uri.startswith("http://"):
            logging.debug("Set up hsource")
            self.init_hsource()
            if FC().proxy_enable and FC().proxy_url:
                logging.debug("gst proxy set up")
                self.hsource.set_property("proxy", FC().proxy_url)
                self.hsource.set_property("proxy-id", FC().proxy_user)
                self.hsource.set_property("proxy-pw", FC().proxy_password)

            self.player.add(self.hsource)
            self.player.add(self.queue)
            self.hsource.link(self.queue)
            self.queue.link(self.decodebin)
            self.player.get_by_name("hsource").set_property("location", uri)
            self.hsource.set_state(Gst.State.READY)
        else:
            logging.debug("Set up fsource")
            self.player.add(self.fsource)
            self.fsource.link(self.decodebin)
            self.player.get_by_name("fsource").set_property("location", uri)
            self.fsource.set_state(Gst.State.READY)

        self.realign_eq()
        self.state_play()

        if self.remembered_seek_position:
            self.wait_for_seek()
            self.player.seek_simple(Gst.Format.TIME, Gst.SeekFlags.FLUSH, self.remembered_seek_position)
        else:
            if bean.start_sec and bean.start_sec != '0':
                self.wait_for_seek()
                self.seek_seconds(bean.start_sec)

        self.remembered_seek_position = 0

        logging.debug(
            "current state before thread " + str(self.get_state()) + " thread_id: " + str(self.play_thread_id))
        self.play_thread_id = thread.start_new_thread(self.playing_thread, ())
        self.pause_thread_id = False

    def wait_for_seek(self):
        while True:
            try:
                init_time = time.time()
                if self.player.query_position(Gst.Format.TIME)[0]:
                    logging.debug("Wait for seek: " + str(time.time() - init_time))
                    return
            except Exception as e:
                continue

    def set_all_bands(self, pre, values, force=False):
        if FC().is_eq_enable or force:
            for i, value in enumerate(values):
                real = float(value) + pre
                if real >= 12:
                    real = 12
                if real <= -12:
                    real = -12
                self.equalizer.set_property("band%s" % i, real)

    def get_position_seek_ns(self):
        try:
            position = self.player.query_position(Gst.Format(Gst.Format.TIME))
            return position[1]
        except Exception, e:
            logging.warn("GET query_position: " + str(e))
            return - 1

    def get_duration_seek_ns(self):
        try:
            position = self.player.query_duration(Gst.Format(Gst.Format.TIME))
            return position[1]
        except Exception, e:
            logging.warn("GET query_duration: " + str(e))
            return - 1

    def playing_thread(self):
        if not self.play_thread_id:
            self.play_thread_id = 1
        thread_id = self.play_thread_id
        previous_position = -1

        logging.debug("current state in thread: " + str(self.get_state()))

        attemps = 5
        for i in xrange(attemps):
            if thread_id == self.play_thread_id and i < attemps:
                time.sleep(0.2)
                duration_int = self.get_duration_seek_ns()
                if duration_int <= 0:
                    time.sleep(0.3)
                    continue
                self.notify_init(duration_int)
                break
            else:
                break

        if self.bean.duration_sec and self.bean.duration_sec > 0:
            duration_int = float(self.bean.duration_sec) * self.NANO_SECONDS

        logging.debug("current state before while " + str(self.get_state()))

        self.set_state(STATE_PLAY)

        while thread_id == self.play_thread_id:
            if self.pause_thread_id:
                time.sleep(0.05)
                continue
            try:
                position_int = self.get_position_seek_ns()
                if position_int > 0 and self.bean.start_sec and self.bean.start_sec > 0:
                    position_int -= float(self.bean.start_sec) * self.NANO_SECONDS
                    if (position_int + self.NANO_SECONDS) > duration_int:
                        self.notify_eos()

                if int(position_int / self.NANO_SECONDS) != previous_position:
                    previous_position = int(position_int / self.NANO_SECONDS)
                    self.notify_playing(position_int, duration_int)

                time.sleep(0.1)
            except Exception, e:
                logging.info("Playing thread error... " + str(e))

            time.sleep(0.05)

    def seek(self, percent, offset=0):
        if not self.bean:
            return None
        seek_ns = self.duration_sec * (percent + offset) / 100 * self.NANO_SECONDS

        if self.bean.start_sec and self.bean.start_sec > 0:
            seek_ns += float(self.bean.start_sec) * self.NANO_SECONDS

        self.player.seek_simple(Gst.Format(Gst.Format.TIME), Gst.SeekFlags.FLUSH, seek_ns)

    def seek_seconds(self, seconds):
        if not seconds:
            return
        logging.info("Start with seconds " + str(seconds))
        seek_ns = (float(seconds) + 0.0) * self.NANO_SECONDS
        logging.info("SEC SEEK SEC " + str(seek_ns))
        self.player.seek_simple(Gst.Format(Gst.Format.TIME), Gst.SeekFlags.FLUSH, seek_ns)

    def seek_ns(self, ns):
        if not ns:
            return
        logging.info("SEC ns " + str(ns))
        self.player.seek_simple(Gst.Format(Gst.Format.TIME), Gst.SeekFlags.FLUSH, ns)

    def volume(self, percent):
        value = percent / 100.0
        try:
            self.player.set_property('volume', value)
        except:
            self.player.get_by_name("volume").set_property('volume', value)

    def state_play(self):
        self.pause_thread_id = False
        self.player.set_state(Gst.State.PLAYING)
        self.current_state = STATE_PLAY
        self.on_chage_state()

    def get_current_percent(self):
        duration = self.get_duration_seek_ns()
        postion = self.get_position_seek_ns()
        return postion * 100.0 / duration

    def seek_up(self, offset=3):
        self.seek(self.get_current_percent(), offset)
        logging.debug("SEEK UP")

    def seek_down(self, offset=-3):
        self.seek(self.get_current_percent(), offset)
        logging.debug("SEEK DOWN")

    def state_stop(self, remember_position=False, show_in_tray=True):
        if remember_position:
            self.player.set_state(Gst.State.PAUSED)
            self.remembered_seek_position = self.get_position_seek_ns()
            self.pause_thread_id = True
        else:
            self.play_thread_id = None

        self.player.set_state(Gst.State.PAUSED)
        self.set_state(STATE_STOP)

        if show_in_tray:
            self.on_chage_state()
        logging.debug("state STOP")
        if self.radio_recording:
            self.controls.record.set_active(False)  # it will call "on toggle" method from self.record
            self.stop_radio_record()

    def state_pause(self, show_in_tray=True):
        self.player.set_state(Gst.State.PAUSED)
        self.set_state(STATE_PAUSE)
        if show_in_tray:
            self.on_chage_state()
        if self.radio_recording:
            self.controls.record.set_active(False)  # it will call "on toggle" method from self.record
            self.stop_radio_record()

    def state_play_pause(self):
        if self.get_state() == STATE_PLAY:
            self.state_pause()
        else:
            self.state_play()

    def _is_remote(self):
        return self.bean.type == FTYPE_RADIO or (self.bean.path and self.bean.path.startswith("http"))

    def on_chage_state(self):
        self.controls.on_chage_player_state(self.get_state(), self.bean)

    def on_sync_message(self, bus, message):
        return
        # struct = message.get_structure()
        # if struct is None:
        #     return
        # if struct.get_name() == "spectrum":
        #     print ("spectrum data")
        #     magnitude = struct.get_value("magnitude")
        #     phase = struct.get_value("phase")
        #     print (magnitude, phase)
        # else:
        #     self.controls.movie_window.draw_video(message)

    def on_message(self, bus, message):
        type = message.type
        struct = message.get_structure()

        if type == Gst.MessageType.BUFFERING:
            percent = message.parse_buffering()
            if percent < 100:
                if not self.buffering:
                    logging.debug("Pausing...")
                    self.buffering = True
                    self.player.set_state(Gst.State.PAUSED)
                logging.debug("Buffering... %d" % percent)
            else:
                if self.buffering:
                    logging.debug("Playing...")
                    self.buffering = False
                    self.player.set_state(Gst.State.PLAYING)

            return

        if type == Gst.MessageType.ERROR:
            err, debug = message.parse_error()
            logging.warn("Error: " + str(err) + str(debug) + str(err.domain) + str(err.code))

            if self.error_counter > 1 and err.code != 1:
                self.notify_error(str(err))
                self.error_counter = 0
                self.state_stop()
            else:
                logging.warning("Error ocured, retry")
                self.error_counter += 1
                self.play(self.bean)

        elif type in [Gst.MessageType.STATE_CHANGED, Gst.MessageType.STREAM_STATUS]:
            if (self.bean and self.bean.type == FTYPE_RADIO and
                    struct.has_field("new-state") and
                        struct.get_enum('old-state', Gst.State) == Gst.State.READY and
                        struct.get_enum('new-state', Gst.State) == Gst.State.NULL):
                logging.info("Reconnect")
                self.play(self.bean)
                return

        if type == Gst.MessageType.TAG and message.parse_tag():
            self.error_counter = 0

            if struct.has_field("taglist"):
                taglist = struct.get_value("taglist")
                title = taglist.get_string("title")[1]
                if not title:
                    title = ""
                title = correct_encoding(title)
                text = title

                if taglist.get_string('artist')[0]:
                    artist = taglist.get_string('artist')[1]
                    artist = correct_encoding(artist)
                    text = artist + " - " + text
                if not text:
                    text = self.bean.path
                if self._is_remote() and taglist.get_string("audio-codec")[0]:
                    text = text + " || " + taglist.get_string("audio-codec")[1]
                if self._is_remote() and taglist.get_uint('bitrate')[0]:
                    text = text + " || " + str(taglist.get_uint('bitrate')[1] / 1000) + _("kbps")
                    self.emit('bitrate-changed', taglist.get_uint('bitrate')[1])

                self.notify_title(text)

        elif type == Gst.MessageType.EOS:
            self.error_counter = 0
            logging.info("MESSAGE_EOS")
            self.notify_eos()

GObject.signal_new("title-changed", GStreamerEngine, GObject.SIGNAL_RUN_LAST, None, (object, str,))
GObject.signal_new("bitrate-changed", GStreamerEngine, GObject.SIGNAL_RUN_LAST, None, (int,))
GObject.signal_new("eos-signal", GStreamerEngine, GObject.SIGNAL_RUN_LAST, None, ())
########NEW FILE########
__FILENAME__ = foobnix_core
#-*- coding: utf-8 -*-
from foobnix.fc.fc import FC
from foobnix.gui.notetab import NoteTabControl
from foobnix.gui.base_layout import BaseFoobnixLayout
from foobnix.gui.base_controls import BaseFoobnixControls
from foobnix.gui.perspectives.fsperspective import FSPerspective
from foobnix.gui.perspectives.info import InfoPerspective
from foobnix.gui.perspectives.lastfm import LastFMPerspective
from foobnix.gui.perspectives.radio import RadioPerspective
from foobnix.gui.perspectives.storage import StoragePerspective
from foobnix.gui.perspectives.vk import VKPerspective
from foobnix.gui.window import MainWindow
from foobnix.gui.controls.playback import PlaybackControls, \
    OrderShuffleControls
from foobnix.gui.search import SearchControls
from foobnix.gui.controls.search_progress import SearchProgress
from foobnix.gui.engine.gstreamer import GStreamerEngine
from foobnix.gui.controls.seekbar import SeekProgressBarControls
from foobnix.gui.controls.volume import VolumeControls
from foobnix.gui.controls.status_bar import StatusbarControls
from foobnix.gui.controls.tray_icon import TrayIconControls
from foobnix.preferences.preferences_window import PreferencesWindow
from foobnix.gui.top import TopWidgets
from foobnix.eq.eq_controller import EqController
from foobnix.dm.dm import DM
from foobnix.util.single_thread import SingleThread
from foobnix.gui.perspectives.controller import Controller
from foobnix.util.localization import foobnix_localization
from foobnix.gui.service.lastfm_service import LastFmService
from foobnix.gui.controls.record import RadioRecord
from foobnix.gui.coverlyrics import CoverLyricsPanel
from foobnix.util.net_wrapper import NetWrapper


foobnix_localization()

class FoobnixCore(BaseFoobnixControls):
    def __init__(self, with_dbus=True):
        BaseFoobnixControls.__init__(self)
        self.layout = None

        self.net_wrapper = NetWrapper(self, FC().net_ping)

        self.statusbar = StatusbarControls(self)

        self.lastfm_service = LastFmService(self)

        self.media_engine = GStreamerEngine(self)

        """elements"""

        self.volume = VolumeControls(self)

        self.record = RadioRecord(self)
        self.seek_bar_movie = SeekProgressBarControls(self)
        self.seek_bar = SeekProgressBarControls(self, self.seek_bar_movie)

        self.trayicon = TrayIconControls(self)
        self.main_window = MainWindow(self)

        self.notetabs = NoteTabControl(self)
        self.search_progress = SearchProgress(self)
        self.in_thread = SingleThread(self.search_progress)

        #self.movie_window = MovieDrawingArea(self)

        self.searchPanel = SearchControls(self)
        self.os = OrderShuffleControls(self)
        self.playback = PlaybackControls(self)

        self.coverlyrics = CoverLyricsPanel(self)

        self.perspectives = Controller(self)

        self.perspectives.attach_perspective(FSPerspective(self))
        self.perspectives.attach_perspective(VKPerspective(self))
        self.perspectives.attach_perspective(LastFMPerspective(self))
        self.perspectives.attach_perspective(RadioPerspective(self))
        self.perspectives.attach_perspective(StoragePerspective(self))
        self.perspectives.attach_perspective(InfoPerspective(self))

        """preferences"""
        self.preferences = PreferencesWindow(self)

        self.eq = EqController(self)
        self.dm = DM(self)

        """layout panels"""
        self.top_panel = TopWidgets(self)

        """layout"""
        self.layout = BaseFoobnixLayout(self)

        self.dbus = None
        if with_dbus:
            from foobnix.gui.controls.dbus_manager import DBusManager
            self.dbus = DBusManager(self)
            try:
                import keybinder #@UnresolvedImport @UnusedImport
                from foobnix.preferences.configs.hotkey_conf import load_foobnix_hotkeys
                load_foobnix_hotkeys()
            except:
                pass

    def run(self):
        self.on_load()
        if FC().hide_on_start:
            self.main_window.hide()


########NEW FILE########
__FILENAME__ = infopanel
'''
Created on Sep 23, 2010

@author: ivan
'''
import os
import copy
import logging
import threading

from gi.repository import Gtk
from gi.repository import GObject

from foobnix.fc.fc import FC
from foobnix.gui.model import FModel
from foobnix.gui.state import LoadSave
from foobnix.helpers.image import ImageBase
from foobnix.helpers.textarea import TextArea
from foobnix.gui.model.signal import FControl
from foobnix.helpers.my_widgets import EventLabel
from foobnix.helpers.pref_widgets import HBoxDecoratorTrue
from foobnix.fc.fc_cache import FCache, COVERS_DIR, LYRICS_DIR
from foobnix.gui.treeview.simple_tree import SimpleTreeControl
from foobnix.util import idle_task
from foobnix.util.const import FTYPE_NOT_UPDATE_INFO_PANEL, \
    ICON_BLANK_DISK, SITE_LOCALE
from foobnix.util.bean_utils import update_parent_for_beans, \
    update_bean_from_normalized_text
from foobnix.thirdparty.lyr import get_lyrics
from foobnix.gui.service.lyrics_parsing_service import get_lyrics_by_parsing
from foobnix.util.id3_util import get_image_for_bean


class InfoCache():
    def __init__(self):
        self.best_songs_bean = None
        self.similar_tracks_bean = None
        self.similar_artists_bean = None
        self.similar_tags_bean = None
        self.lyric_bean = None
        self.wiki_artist = None

        self.active_method = None


class InfoPanelWidget(Gtk.Frame, LoadSave, FControl):
    def __init__(self, controls):
        Gtk.Frame.__init__(self)
        FControl.__init__(self, controls)

        self.album_label = Gtk.Label()
        self.album_label.set_line_wrap(True)
        self.album_label.set_markup("<b></b>")
        self.set_label_widget(self.album_label)

        self.empty = TextArea()

        self.best_songs = SimpleTreeControl(_("Best Songs"), controls)
        self.best_songs.line_title = EventLabel(self.best_songs.get_title(), func=self.show_current,
                                                arg=self.best_songs, func1=self.show_best_songs)

        self.artists = SimpleTreeControl(_("Similar Artists"), controls)
        self.artists.line_title = EventLabel(self.artists.get_title(), func=self.show_current,
                                             arg=self.artists, func1=self.show_similar_artists)

        self.tracks = SimpleTreeControl(_("Similar Songs"), controls)
        self.tracks.line_title = EventLabel(self.tracks.get_title(), func=self.show_current,
                                            arg=self.tracks, func1=self.show_similar_tracks)

        self.tags = SimpleTreeControl(_("Similar Tags"), controls)
        self.tags.line_title = EventLabel(self.tags.get_title(), func=self.show_current,
                                          arg=self.tags, func1=self.show_similar_tags)

        self.lyrics = TextArea()
        lyric_title = _("Lyrics")
        self.lyrics.set_text("", lyric_title)
        self.lyrics.line_title = EventLabel(lyric_title, func=self.show_current,
                                            arg=self.lyrics, func1=self.show_similar_lyrics)

        """wiki"""
        wBox = Gtk.VBox()
        wiki_title = _("About Artist")
        self.wiki = TextArea()

        wBox.line_title = EventLabel(wiki_title, func=self.show_current, arg=wBox, func1=self.show_wiki_info)

        """info"""
        info_frame = Gtk.Frame(label=_("Info"))

        self.last_fm_label = Gtk.LinkButton("http://www.last.fm", "Last.Fm")
        self.wiki_label = Gtk.LinkButton("http://www.wikipedia.org", "Wikipedia")

        info_line = HBoxDecoratorTrue(self.last_fm_label, self.wiki_label)
        info_frame.add(info_line)

        """downloads"""
        dm_frame = Gtk.Frame(label=_("Downloads"))

        self.exua_label = Gtk.LinkButton("http://www.ex.ua", "EX.ua")
        self.rutracker_label = Gtk.LinkButton("http://rutracker.org", "Rutracker")

        dm_line = HBoxDecoratorTrue(self.exua_label, self.rutracker_label)
        dm_frame.add(dm_line)

        self.wiki = TextArea()
        self.wiki.set_text("", wiki_title)

        wBox.pack_start(HBoxDecoratorTrue(info_frame, dm_frame), False, False, 0)
        wBox.pack_start(self.wiki, True, True, 0)

        wBox.scroll = wBox

        self.vpaned_small = Gtk.VBox(False, 0)

        """image and similar artists"""
        ibox = Gtk.HBox(False, 0)
        self.image = ImageBase(ICON_BLANK_DISK, FC().info_panel_image_size)

        lbox = Gtk.VBox(False, 0)

        self.left_widget = [wBox, self.artists, self.tracks, self.tags, self.lyrics, self.best_songs]

        for l_widget in self.left_widget:
            lbox.pack_start(l_widget.line_title, True, True, 0)

        ibox.pack_start(self.image, False, False, 0)
        ibox.pack_start(lbox, True, True, 0)

        """image and similar artists"""
        sbox = Gtk.VBox(False, 0)

        for l_widget in self.left_widget:
            sbox.pack_start(l_widget.scroll, True, True, 0)

        sbox.pack_end(self.empty.scroll, True, True, 0)

        self.vpaned_small.pack_start(ibox, False, False, 0)
        self.vpaned_small.pack_start(sbox, True, True, 0)

        self.add(self.vpaned_small)

        self.bean = None
        self.info_cache = InfoCache()
        self.update_lock = threading.Lock()
        self.clear()

    @idle_task
    def show_current(self, widget):
        if not self.controls.net_wrapper.is_internet():
            return

        self.empty.hide()
        if widget.line_title.selected:
            widget.scroll.hide()
            self.empty.show()
            widget.line_title.set_not_active()
            return

        for w in self.left_widget:
            w.scroll.hide()
            w.line_title.set_not_active()

        widget.scroll.show_all()
        widget.line_title.set_active()

        self.info_cache.active_method = widget.line_title.func1
        self.controls.in_thread.run_with_progressbar(widget.line_title.func1)

    def clear(self):
        self.image.set_no_image()
        self.tracks.clear_tree()
        self.tags.clear_tree()
        self.artists.clear_tree()
        self.lyrics.set_text("", _("Lyrics"))

    def update_info_panel(self):
        if not self.controls.net_wrapper.is_internet() or not self.bean:
            return

        bean = copy.copy(self.bean)

        def update_info_panel_task():
            self.update_lock.acquire()
            try:
                self.show_album_title(bean)
                self.show_disc_cover(bean)
                if self.controls.coverlyrics.get_property("visible"):
                    try:
                        self.show_similar_lyrics(bean)
                    except Exception, e:
                        logging.error("Can't get lyrics. " + type(e).__name__ + ": " + e.message)
                if self.info_cache.active_method:
                    self.info_cache.active_method()
            except: pass
            self.update_lock.release()

        self.controls.in_thread.run_with_progressbar(update_info_panel_task, with_lock=False)

    def update(self, bean):
        if bean.type == FTYPE_NOT_UPDATE_INFO_PANEL:
            return False

        self.clear()

        if not self.controls.net_wrapper.is_internet():
            return

        if not FC().is_view_info_panel:
            logging.debug("Info panel disabled")
            return

        """check connection"""
        if not self.controls.lastfm_service.connect():
            return

        """update bean info form text if possible"""
        bean = update_bean_from_normalized_text(bean)

        if not bean.artist or not bean.title:
            logging.debug("Artist and title not defined")

        self.bean = bean

        self.update_info_panel()

    def show_album_title(self, bean=None):
        if not bean:
            bean = self.bean
        if bean.UUID != self.bean.UUID:
            return

        """update info album and year"""
        info_line = bean.artist
        if bean.text in FCache().album_titles:
            info_line = FCache().album_titles[bean.text]
        else:
            album_name = self.controls.lastfm_service.get_album_name(bean.artist, bean.title)
            album_year = self.controls.lastfm_service.get_album_year(bean.artist, bean.title)
            if album_name:
                info_line = album_name
            if album_name and album_year:
                info_line = album_name + " (" + album_year + ")"

            if isinstance(info_line, unicode) or isinstance(info_line, str):
                FCache().album_titles[bean.text] = info_line
        if info_line and bean.UUID == self.bean.UUID:
            info_line = info_line.replace('&', '&amp;')
            self.album_label.set_markup("<b>%s</b>" % info_line)
            self.controls.coverlyrics.album_title.set_markup("<b>%s</b>" % info_line)

    def show_disc_cover(self, bean=None):
        if not bean:
            bean = self.bean
        if bean.UUID != self.bean.UUID:
            return

        """update image"""
        if not bean.image:
            if not os.path.isdir(COVERS_DIR):
                os.mkdir(COVERS_DIR)
            bean.image = get_image_for_bean(bean, self.controls)

        if not bean.image:
            logging.warning("""""Can't get cover image. Check the correctness of the artist's name and track title""""")

        if bean.UUID == self.bean.UUID:
            self.image.update_info_from(bean)
            self.controls.trayicon.update_info_from(bean)
            self.controls.coverlyrics.set_cover()

    def show_similar_lyrics(self, bean=None):
        if not bean:
            bean = self.bean
        if not bean:
            return
        if bean.UUID != self.bean.UUID:
            return

        """lyrics"""
        if not os.path.isdir(LYRICS_DIR):
            os.mkdir(LYRICS_DIR)

        cache_name = lyrics_title = "%s - %s" % (bean.artist, bean.title)

        illegal_chars = ["/", "#", ";", ":", "%", "*", "&", "\\"]
        for char in illegal_chars:
            cache_name = cache_name.replace(char, "_")
        cache_name = cache_name.lower().strip()

        text = None

        if os.path.exists(os.path.join(LYRICS_DIR, cache_name)):
            text = "".join(open(os.path.join(LYRICS_DIR, cache_name), 'r').readlines())
        else:
            self.lyrics.set_text(_("Loading..."), lyrics_title)
            try:
                logging.debug("Try to get lyrics from lyrics.wikia.com")
                text = get_lyrics(bean.artist, bean.title)
            except:
                logging.info("Error occurred when getting lyrics from lyrics.wikia.com")
            if not text:
                text = get_lyrics_by_parsing(bean.artist, bean.title)
            if text:
                open(os.path.join(LYRICS_DIR, cache_name), 'w').write(text)
            else:
                logging.info("The text not found")
                text = _("The text not found")
        if bean.UUID == self.bean.UUID:
            self.lyrics.set_text(text, lyrics_title)

    def show_wiki_info(self):
        if not self.bean:
            return
        if self.info_cache.wiki_artist == self.bean.artist:
            return None
        self.info_cache.wiki_artist = self.bean.artist

        self.wiki_label.set_uri("http://%s.wikipedia.org/w/index.php?&search=%s" % (SITE_LOCALE, self.bean.artist))
        self.last_fm_label.set_uri("http://www.last.fm/search?q=%s" % self.bean.artist)

        self.exua_label.set_uri("http://www.ex.ua/search?s=%s" % self.bean.artist)
        self.rutracker_label.set_uri("http://rutracker.org/forum/tracker.php?nm=%s" % self.bean.artist)

        artist = self.controls.lastfm_service.get_network().get_artist(self.bean.artist)
        self.wiki.set_text(artist.get_bio_summary(), self.bean.artist)

#         Deprecated
#         images = artist.get_images(limit=6)
#
#         for image in images:
#             try:
#                 url = image.sizes.large
#             except AttributeError:
#                 url = image.sizes["large"]
#             self.wiki.append_image(url)

    def show_similar_tags(self):
        if self.info_cache.similar_tags_bean == self.bean:
            return None
        self.info_cache.similar_tags_bean = self.bean

        """similar  tags"""
        similar_tags = self.controls.lastfm_service.search_top_similar_tags(self.bean.artist, self.bean.title)
        parent = FModel(_("Similar Tags:") + " " + self.bean.title)
        update_parent_for_beans(similar_tags, parent)
        self.tags.populate_all([parent] + similar_tags)

    def show_similar_tracks(self):
        if self.info_cache.similar_tracks_bean == self.bean:
            return None
        self.info_cache.similar_tracks_bean = self.bean

        """similar  songs"""
        similar_tracks = self.controls.lastfm_service.search_top_similar_tracks(self.bean.artist, self.bean.title)
        parent = FModel(_("Similar Tracks:") + " " + self.bean.title)
        update_parent_for_beans(similar_tracks, parent)
        self.tracks.populate_all([parent] + similar_tracks)

    def show_similar_artists(self):
        if self.info_cache.similar_artists_bean == self.bean:
            return None
        self.info_cache.similar_artists_bean = self.bean

        """similar  artists"""
        if self.bean.artist:
            similar_artists = self.controls.lastfm_service.search_top_similar_artist(self.bean.artist)
            parent = FModel(_("Similar Artists:") + " " + self.bean.artist)
            update_parent_for_beans(similar_artists, parent)
            self.artists.populate_all([parent] + similar_artists)

    def show_best_songs(self):
        if self.info_cache.best_songs_bean == self.bean:
            return None

        self.info_cache.best_songs_bean = self.bean

        best_songs = self.controls.lastfm_service.search_top_tracks(self.bean.artist)
        parent = FModel(_("Best Songs:") + " " + self.bean.artist)
        update_parent_for_beans(best_songs, parent)
        self.best_songs.populate_all([parent] + best_songs)

    def on_load(self):
        for w in self.left_widget:
            w.scroll.hide()
            w.line_title.set_not_active()
        self.empty.show()
        FCache().on_load()

    def on_save(self):
        pass

    def on_quit(self):
        FCache().on_quit()

########NEW FILE########
__FILENAME__ = menu
'''
Created on Sep 22, 2010

@author: ivan
'''

from gi.repository import Gtk

import logging

from foobnix.fc.fc import FC
from foobnix.util import const
from foobnix.gui.model.signal import FControl
from foobnix.gui.about.about import AboutWindow
from foobnix.util.widget_utils import MenuStyleDecorator
from foobnix.helpers.my_widgets import open_link_in_browser


class MenuBarWidget(FControl):
    def __init__(self, controls, parent=None):
        FControl.__init__(self, controls)
        """TOP menu constructor"""

        decorator = MenuStyleDecorator()
        if not parent:
            parent = TopMenuBar()

        top = parent

        """File"""
        file = top.add_submenu(_("File"))
        file.add_image_item(_("Add File(s)"), Gtk.STOCK_OPEN, self.controls.on_add_files)
        file.add_image_item(_("Add Folder(s)"), Gtk.STOCK_OPEN, self.controls.on_add_folders)
        file.add_image_item(_("Save Playlist As"), Gtk.STOCK_SAVE_AS,
                            lambda: self.controls.notetabs.on_save_playlist(self.controls.notetabs.get_current_tree().scroll))
        file.separator()
        file.add_image_item(_("Quit"), Gtk.STOCK_QUIT, self.controls.quit)

        """View"""
        view = top.add_submenu(_("View"))
        view.set_no_show_all(True)
        self.view_music_tree = view.add_check_item(_("Left Panel"), FC().is_view_music_tree_panel)
        self.view_music_tree.connect("activate", lambda w: controls.layout.set_visible_musictree_panel(w.get_active()))

        self.view_search_panel = view.add_check_item(_("Search Panel"), FC().is_view_search_panel)
        self.view_search_panel.connect("activate", lambda w: controls.layout.set_visible_search_panel(w.get_active()))

        self.view_cover_lyrics = view.add_check_item(_("Cover & Lyrics Panel"), FC().is_view_coverlyrics_panel)
        self.view_cover_lyrics.connect("activate", lambda w: controls.layout.set_visible_coverlyrics_panel(w.get_active()))

        separator1 = view.separator() #@UnusedVariable
        view.add_image_item(_("Equalizer"), None, self.controls.eq.show)
        view.add_image_item(_("Download Manager"), None, self.controls.dm.show)
        separator2 = view.separator()
        preferences_item = view.add_image_item(_("Preferences"), Gtk.STOCK_PREFERENCES, self.controls.show_preferences)

        """if new style menu - remove preferences from View"""
        if not isinstance(parent, TopMenuBar):
            separator2.hide()
            preferences_item.hide()

        """Playback"""
        playback = top.add_submenu(_("Playback"))

        def set_random(flag=True):
            FC().is_order_random = flag
            logging.debug("set random" + str(flag))
            controls.os.on_load()

        """Playback - Order"""
        order = playback.add_text_item(_("Order"))
        playback_radio_group = []
        self.playback_order_linear = order.add_radio_item(_("Linear"), playback_radio_group, not FC().is_order_random)
        self.playback_order_linear.connect("activate", lambda w: set_random(False))

        self.playback_order_random = order.add_radio_item(_("Random"), playback_radio_group, FC().is_order_random)
        self.playback_order_random.connect("activate", lambda w: set_random(True))

        """Playback - Repeat"""
        repeat = playback.add_text_item(_("Repeat"))
        repeat_radio_group = []
        self.lopping_all = repeat.add_radio_item(_("All"), repeat_radio_group, FC().repeat_state == const.REPEAT_ALL)
        self.lopping_single = repeat.add_radio_item(_("Single"), repeat_radio_group, FC().repeat_state == const.REPEAT_SINGLE)
        self.lopping_disable = repeat.add_radio_item(_("Disable"), repeat_radio_group, FC().repeat_state == const.REPEAT_NO)

        def repeat_all():
            FC().repeat_state = const.REPEAT_ALL
            logging.debug("set repeat_all")
            controls.os.on_load()


        def repeat_sigle():
            FC().repeat_state = const.REPEAT_SINGLE
            logging.debug("set repeat_sigle")
            controls.os.on_load()

        def repeat_no():
            FC().repeat_state = const.REPEAT_NO
            logging.debug("set repeat_no")
            controls.os.on_load()

        self.lopping_all.connect("activate", lambda * a:repeat_all())
        self.lopping_single.connect("activate", lambda * a:repeat_sigle())
        self.lopping_disable.connect("activate", lambda * a:repeat_no())

        """Playlist View"""
        #playlist = playback.add_text_item("Playlist")
        #self.playlist_plain = playlist.add_radio_item("Plain (normal style)", None, FC().playlist_type == const.PLAYLIST_PLAIN)
        #self.playlist_tree = playlist.add_radio_item("Tree (apollo style)", self.playlist_plain , FC().playlist_type == const.PLAYLIST_TREE)

        #self.playlist_plain.connect("activate", lambda w: w.get_active() and controls.set_playlist_plain())
        #self.playlist_tree.connect("activate", lambda w: w.get_active() and controls.set_playlist_tree())

        """Help"""
        help = top.add_submenu(_("Help"))
        help.add_image_item(_("About"), Gtk.STOCK_ABOUT, self.show_about)
        help.separator()
        help.add_text_item(_("Project page"), lambda * a:open_link_in_browser(_("http://www.foobnix.com/news/eng")), None, False)
        help.add_image_item(_("Issue report"), Gtk.STOCK_DIALOG_WARNING, lambda * a:open_link_in_browser("http://code.google.com/p/foobnix/issues/list"))
        help.separator()
        help.add_image_item(_("Donate Participate"), Gtk.STOCK_DIALOG_QUESTION, lambda * a:open_link_in_browser(_("http://www.foobnix.com/donate/eng")))

        #help.add_image_item("Help", Gtk.STOCK_HELP)

        #top.decorate()

        decorator.apply(top)
        decorator.apply(file)
        decorator.apply(view)
        decorator.apply(playback)
        decorator.apply(repeat)
        decorator.apply(order)
        decorator.apply(help)

        self.widget = top

        self.on_load()

    def show_about(self):
        about = AboutWindow()
        about.show()

    def on_load(self):
        self.view_music_tree.set_active(FC().is_view_music_tree_panel)
        self.view_search_panel.set_active(FC().is_view_search_panel)
        self.view_cover_lyrics.set_active(FC().is_view_coverlyrics_panel)

    def on_save(self):
        FC().is_view_music_tree_panel = self.view_music_tree.get_active()
        FC().is_view_search_panel = self.view_search_panel.get_active()
        FC().is_view_coverlyrics_panel = self.view_cover_lyrics.get_active()


class MyMenu(Gtk.Menu):
    """My custom menu class for helping buildings"""
    def __init__(self):
        Gtk.Menu.__init__(self)

    def add_image_item(self, title, gtk_stock, func=None, param=None):
        item = Gtk.ImageMenuItem(title)

        item.show()
        if gtk_stock:
            img = Gtk.Image.new_from_stock(gtk_stock, Gtk.IconSize.MENU)
            item.set_image(img)

        logging.debug("Menu-Image-Activate" + title + str(gtk_stock) + str(func) + str(param))
        if func and param:
            item.connect("activate", lambda * a: func(param))
        elif func:
            item.connect("activate", lambda * a: func())
        self.append(item)
        return item

    def separator(self):
        separator = Gtk.SeparatorMenuItem.new()
        separator.show()
        self.append(separator)
        return separator

    def add_check_item(self, title, active=False, func=None, param=None):
        check = Gtk.CheckMenuItem(title)

        if param and func:
            check.connect("activate", lambda * a: func(param))
        elif func:
            check.connect("activate", lambda * a: func())

        check.show()
        check.set_active(active)
        self.append(check)
        return check

    def add_radio_item(self, title, group, active):
        check = Gtk.RadioMenuItem.new_with_label(group, title)
        group.append(check)
        check.show()
        check.set_active(active)
        self.append(check)
        return check

    def add_text_item(self, title, func=None, param=None, sub_menu=True):
        sub = Gtk.MenuItem(title)
        sub.show()
        self.append(sub)

        if param and func:
            sub.connect("activate", lambda * a: func(param))
        elif func:
            sub.connect("activate", lambda * a: func())

        if sub_menu:
            menu = MyMenu()
            menu.show()
            sub.set_submenu(menu)
            return menu


"""My top menu bar helper"""
class TopMenuBar(Gtk.MenuBar):
    def __init__(self):
        rc_st = '''
            style "menubar-style" {
                GtkMenuBar::shadow_type = none
                GtkMenuBar::internal-padding = 0
                }
            class "GtkMenuBar" style "menubar-style"
        '''
        Gtk.rc_parse_string(rc_st)
        Gtk.MenuBar.__init__(self)

    def add_submenu(self, title):
        menu = MyMenu()
        menu.show()

        file_item = Gtk.MenuItem(title)
        file_item.show()

        file_item.set_submenu(menu)
        self.append(file_item)
        return menu



########NEW FILE########
__FILENAME__ = eq_model
'''
Created on Oct 25, 2010

@author: ivan
'''
class EqModel():
    def __init__(self, id, name, preamp, values):
        self.id = id
        self.name = name
        self.preamp = preamp
        self.values = values
    
    def set_preamp(self, preamp):
        self.preamp = preamp
    
    def set_values(self, values):
        self.values = values
########NEW FILE########
__FILENAME__ = signal
#-*- coding: utf-8 -*-
'''
Created on 25 сент. 2010

@author: ivan
'''
"""base class to comunicate beatween all controls"""


class FControl():
    def __init__(self, controls):
        self.controls = controls

########NEW FILE########
__FILENAME__ = tab_library
#-*- coding: utf-8 -*-
'''
Created on Dec 7, 2010

@author: zavlab1
'''

from gi.repository import Gtk

from foobnix.fc.fc import FC
from foobnix.fc.fc_cache import FCache
from foobnix.util.list_utils import reorderer_list
from foobnix.helpers.menu import Popup
from foobnix.gui.notetab import TabGeneral


class TabHelperControl(TabGeneral):
    def __init__(self, controls):
        TabGeneral.__init__(self, controls)

        self.set_tab_pos(Gtk.PositionType.LEFT)

        """the only signal lets get the previous number of moved page"""
        self.connect("button-release-event", self.get_page_number)
        self.connect('switch-page', self.save_selected_tab)
        self.loaded = False

    def save_selected_tab(self, notebook, page, page_num, *args):
        if not self.loaded: #bbecause the "switch-page" event is fired after every tab's addtion
            return
        FC().nav_selected_tab = page_num

    def on_add_button_click(self):
        self._append_tab()
        self.controls.perspectives.get_perspective('fs').show_add_button()
        FCache().music_paths.insert(0, [])
        FCache().tab_names.insert(0, self.get_full_tab_name(self.get_current_tree().scroll))
        FCache().cache_music_tree_beans.insert(0, {})

    def on_button_press(self, w, e, *a):
        if e.button == 3:
            w.menu.show_all()
            w.menu.popup(None, None, None, None, e.button, e.time)

    def tab_menu_creator(self, widget, tab_child):
        widget.menu = Popup()
        widget.menu.add_item(_("Rename tab"), "", lambda: self.on_rename_tab(tab_child, 90, FCache().tab_names), None)
        widget.menu.add_item(_("Update Music Tree"), Gtk.STOCK_REFRESH, lambda: self.on_update_music_tree(tab_child), None)
        widget.menu.add_item(_("Add folder"), Gtk.STOCK_OPEN, lambda: self.on_add_folder(tab_child), None)
        widget.menu.add_item(_("Add folder in new tab"), Gtk.STOCK_OPEN, lambda : self.on_add_folder(tab_child, True), None)
        widget.menu.add_item(_("Clear Music Tree"), Gtk.STOCK_CLEAR, lambda : self.clear_tree(tab_child), None)
        widget.menu.add_item(_("Close tab"), Gtk.STOCK_CLOSE, lambda: self.on_delete_tab(tab_child), None)
        return widget

    def reorder_callback(self, notebook, child, new_page_num):
        for list in [FCache().music_paths, FCache().tab_names, FCache().cache_music_tree_beans]:
            reorderer_list(list, new_page_num, self.page_number,)
        self.on_save_tabs()

    def get_page_number(self, *a):
            self.page_number = self.get_current_page()

    def on_add_folder(self, tab_child, in_new_tab=False):
        tree = tab_child.get_child()
        tree.add_folder(in_new_tab)

    def clear_tree(self, tab_child):
        n = self.page_num(tab_child)
        tree = tab_child.get_child()
        tree.clear_tree()
        FCache().cache_music_tree_beans[n] = {}

    def on_update_music_tree(self, tab_child):
        n = self.page_num(tab_child)
        tree = tab_child.get_child()
        self.controls.update_music_tree(tree, n)

    def on_load(self):
        if FC().tabs_mode == "Single":
            self.set_show_tabs(False)

        self.controls.load_music_tree()
        self.set_current_page(FC().nav_selected_tab)
        self.loaded = True

    def save_tabs(self):
        '''need for one_thread_save method'''
        pass

########NEW FILE########
__FILENAME__ = controller
from foobnix.gui.controls.filter import FilterControl

__author__ = 'popsul'

from gi.repository import Gtk
from foobnix.util import analytics
from foobnix.gui.state import LoadSave, Quitable, Filterable
from foobnix.gui.perspectives import StackableWidget, BasePerspective, OneButtonToggled
from foobnix.helpers.my_widgets import PerspectiveButton


class Controller(Gtk.VBox, LoadSave, Quitable, Filterable):

    def __init__(self, controls):
        super(Controller, self).__init__(False, 0)

        self.perspectives_container = StackableWidget()
        self.button_container = Gtk.HBox(False, 0)
        self.button_controller = OneButtonToggled()
        self.perspectives = {}
        ## internal property
        self._perspectives = []

        self.filter = FilterControl(self)

        self.pack_start(self.perspectives_container, True, True, 0)
        self.pack_start(self.filter, False, False, 0)
        self.pack_start(self.button_container, False, False, 0)

        ## insert dummy page
        self.perspectives_container.add(Gtk.Label(""))
        self.show_all()

    def attach_perspective(self, perspective):
        assert isinstance(perspective, BasePerspective)
        perspective_id = perspective.get_id()
        self.perspectives[perspective_id] = perspective
        self._perspectives.append(perspective)
        widget = perspective.get_widget()
        perspective.widget_id = self.perspectives_container.add(widget)
        button = PerspectiveButton(perspective.get_name(), perspective.get_icon(), perspective.get_tooltip())

        def toggle_handler(btn, handler, *args):
            if btn.get_active():
                handler()
        button.connect("toggled", toggle_handler, lambda *a: self.activate_perspective(perspective_id))
        perspective.button = button
        self.button_container.pack_start(button, False, False, 0)
        self.button_controller.add_button(button)

    def activate_perspective(self, perspective_id):
        if self.is_activated(perspective_id):
            return
        perspective = self.get_perspective(perspective_id)
        assert perspective
        for _id in self.perspectives.keys():
            if self.is_activated(_id):
                self.get_perspective(_id).emit("deactivated")
        self.perspectives_container.set_active_by_index(perspective.widget_id)
        perspective.button.set_active(True)
        if isinstance(perspective, Filterable):
            self.filter.show()
        else:
            self.filter.hide()
        perspective.emit("activated")
        analytics.action("PERSPECTIVE_" + perspective.get_id())
        self.check_availability()

    def check_availability(self):
        for perspective in self._perspectives:
            if not perspective.is_available():
                perspective.button.set_sensitive(False)
                perspective.button.set_tooltip_text("Not available")
                if self.is_activated(perspective.get_id()):
                    self.activate_perspective(self._perspectives[0].get_id())
            else:
                perspective.button.set_sensitive(True)
                perspective.button.set_tooltip_text(perspective.get_tooltip())

    def is_activated(self, perspective_id):
        perspective = self.get_perspective(perspective_id)
        assert perspective
        return perspective.widget_id == self.perspectives_container.get_active_index()

    def get_perspective(self, perspective_id):
        if perspective_id in self.perspectives:
            return self.perspectives[perspective_id]
        return None

    def filter_by_file(self, value):
        for perspective in self._perspectives:
            if isinstance(perspective, Filterable):
                perspective.filter_by_file(value)

    def filter_by_folder(self, value):
        for perspective in self._perspectives:
            if isinstance(perspective, Filterable):
                perspective.filter_by_folder(value)

    def on_load(self):
        for perspective in self._perspectives:
            if isinstance(perspective, LoadSave):
                perspective.on_load()
        self.activate_perspective(self._perspectives[0].get_id())

    def on_save(self):
        for perspective in self._perspectives:
            if isinstance(perspective, LoadSave):
                perspective.on_save()

    def on_quit(self):
        for perspective in self._perspectives:
            if isinstance(perspective, Quitable):
                perspective.on_quit()

########NEW FILE########
__FILENAME__ = fsperspective

__author__ = 'popsul'

from gi.repository import Gtk
from foobnix.util import idle_task
from foobnix.gui.state import Filterable
from foobnix.gui.perspectives import BasePerspective
from foobnix.helpers.my_widgets import ButtonStockText
from foobnix.gui.notetab.tab_library import TabHelperControl


class FSPerspective(BasePerspective, Filterable):

    def __init__(self, controls):
        super(FSPerspective, self).__init__()
        self.tabhelper = TabHelperControl(controls)
        self.vbox = Gtk.VBox(False, 0)

        self.add_button = ButtonStockText(_(" Add Folder(s) in tree"), Gtk.STOCK_ADD)
        self.add_button.connect("clicked", lambda * a: self.tabhelper.get_current_tree().add_folder())

        self.vbox.pack_start(self.add_button, False, False, 0)
        self.vbox.pack_start(self.tabhelper, True, True)
        self.vbox.show_all()

    def get_tabhelper(self):
        ## temporary duplicate for get_widget()
        return self.tabhelper

    @idle_task
    def hide_add_button(self):
        self.add_button.hide()

    @idle_task
    def show_add_button(self):
        self.add_button.show()

    def get_id(self):
        return "fs"

    def get_icon(self):
        return Gtk.STOCK_HARDDISK

    def get_name(self):
        return _("Music")

    def get_tooltip(self):
        return _("Music Navigation (Alt+1)")

    def get_widget(self):
        return self.vbox

    ## LoadSave implementation
    def on_load(self):
        self.tabhelper.on_load()

    def on_save(self):
        self.tabhelper.on_save()

    ## Filterable implementation
    def filter_by_file(self, value):
        self.tabhelper.get_current_tree().filter_by_file(value)

    def filter_by_folder(self, value):
        self.tabhelper.get_current_tree().filter_by_folder(value)

########NEW FILE########
__FILENAME__ = info

__author__ = 'popsul'

from gi.repository import Gtk
from foobnix.gui.state import Quitable
from foobnix.gui.perspectives import BasePerspective
from foobnix.gui.infopanel import InfoPanelWidget


class InfoPerspective(BasePerspective, Quitable):

    def __init__(self, controls):
        super(InfoPerspective, self).__init__()
        self.widget = InfoPanelWidget(controls)

    def update(self, bean):
        self.widget.update(bean)

    def clear(self):
        self.widget.clear()

    def get_id(self):
        return "info"

    def get_icon(self):
        return Gtk.STOCK_INFO

    def get_name(self):
        return _("Info")

    def get_tooltip(self):
        return _("Info Panel (Alt+4)")

    def get_widget(self):
        return self.widget

    def on_load(self):
        self.widget.on_load()

    def on_save(self):
        self.widget.on_save()

    def on_quit(self):
        self.widget.on_quit()

########NEW FILE########
__FILENAME__ = lastfm

__author__ = 'popsul'

from gi.repository import Gtk
from foobnix.fc.fc import FCBase
from foobnix.gui.perspectives import BasePerspective
from foobnix.gui.treeview.lastfm_integration_tree import LastFmIntegrationControls


class LastFMPerspective(BasePerspective):

    def __init__(self, controls):
        super(LastFMPerspective, self).__init__()
        self.widget = LastFmIntegrationControls(controls)

    def get_id(self):
        return "lastfm"

    def get_icon(self):
        return Gtk.STOCK_CONNECT

    def get_name(self):
        return _("Last.FM")

    def get_tooltip(self):
        return _("Last.FM Panel (Alt+5)")

    def get_widget(self):
        return self.widget.scroll

    def is_available(self):
        return (FCBase().lfm_login != "l_user_") and FCBase().lfm_password

    ## LoadSave implementation
    def on_load(self):
        pass

    def on_save(self):
        pass


########NEW FILE########
__FILENAME__ = radio

__author__ = 'popsul'

from gi.repository import Gtk
from foobnix.gui.state import Filterable, Quitable
from foobnix.gui.perspectives import BasePerspective, StackableWidget
from foobnix.gui.treeview.radio_tree import RadioTreeControl, MyRadioTreeControl


class RadioPerspective(BasePerspective, Filterable, Quitable):

    def __init__(self, controls):
        super(RadioPerspective, self).__init__()

        self.auto_radio = RadioTreeControl(controls)
        self.my_radio = MyRadioTreeControl(controls)

        self.switch_button = Gtk.Button()
        self.switch_button.connect("clicked", self.switch_radio)

        self.vbox = Gtk.VBox(False, 0)
        self.radios = StackableWidget()
        self.radios.add(self.auto_radio.scroll)
        self.radios.add(self.my_radio.scroll)

        self.vbox.pack_start(self.radios, True, True, 0)
        self.vbox.pack_start(self.switch_button, False, False, 0)
        self.vbox.show_all()

        self.update_button_label()

    def switch_radio(self, *args):
        index = self.radios.get_active_index()
        new_index = abs(index - 1)
        self.radios.set_active_by_index(new_index)
        self.update_button_label()

    def update_button_label(self):
        index = self.radios.get_active_index()
        radio = self.radios.get_nth_page(index)
        self.switch_button.set_label(radio.get_child().switcher_label)

    def get_id(self):
        return "radio"

    def get_icon(self):
        return Gtk.STOCK_NETWORK

    def get_name(self):
        return _("Radio")

    def get_tooltip(self):
        return _("Radio Stantions (Alt+2)")

    def get_widget(self):
        return self.vbox

    ## LoadSave implementation
    def on_load(self):
        self.auto_radio.on_load()
        self.my_radio.on_load()

    def on_save(self):
        self.auto_radio.on_save()
        self.my_radio.on_save()

    ## Quitable implementation
    def on_quit(self):
        self.auto_radio.on_quit()
        self.my_radio.on_quit()

    ## Filterable implementation
    def filter_by_folder(self, value):
        self.auto_radio.filter_by_folder(value)
        self.my_radio.filter_by_folder(value)

    def filter_by_file(self, value):
        self.auto_radio.filter_by_file(value)
        self.my_radio.filter_by_file(value)

########NEW FILE########
__FILENAME__ = storage

__author__ = 'popsul'

from gi.repository import Gtk
from foobnix.gui.state import Quitable, Filterable
from foobnix.gui.perspectives import BasePerspective
from foobnix.gui.treeview.virtual_tree import VirtualTreeControl


class StoragePerspective(BasePerspective, Quitable, Filterable):

    def __init__(self, controls):
        super(StoragePerspective, self).__init__()
        self.widget = VirtualTreeControl(controls)

    def get_id(self):
        return "storage"

    def get_icon(self):
        return Gtk.STOCK_INDEX

    def get_name(self):
        return _("Storage")

    def get_tooltip(self):
        return _("Storage (Alt+3)")

    def get_widget(self):
        return self.widget.scroll

    ## LoadSave implementation
    def on_load(self):
        self.widget.on_load()

    def on_save(self):
        self.widget.on_save()

    ## Quitable implementation
    def on_quit(self):
        self.widget.on_quit()

    ## Filterable implementation
    def filter_by_file(self, value):
        self.widget.filter_by_file(value)

    def filter_by_folder(self, value):
        self.widget.filter_by_folder(value)

########NEW FILE########
__FILENAME__ = vk

__author__ = 'popsul'

import thread
from gi.repository import Gtk
from foobnix.gui.state import Filterable
from foobnix.gui.perspectives import BasePerspective
from foobnix.gui.treeview.vk_integration_tree import VKIntegrationControls


class VKPerspective(BasePerspective, Filterable):

    def __init__(self, controls):
        super(VKPerspective, self).__init__()
        self.widget = VKIntegrationControls(controls)

        self.connect("activated", self.on_activated)

    def on_activated(self, perspective):
        thread.start_new_thread(self.widget.lazy_load, ())

    def get_id(self):
        return "vk"

    def get_icon(self):
        return Gtk.STOCK_UNINDENT

    def get_name(self):
        return _("VK")

    def get_tooltip(self):
        return _("VK Panel (Alt+6)")

    def get_widget(self):
        return self.widget.scroll

    ## LoadSave implementation
    def on_load(self):
        pass

    def on_save(self):
        pass

    ## Filterable implementation
    def filter_by_folder(self, value):
        self.widget.filter_by_folder(value)

    def filter_by_file(self, value):
        pass

########NEW FILE########
__FILENAME__ = search
from gi.repository import Gtk
import thread
import logging

from foobnix.util.key_utils import is_key_enter
from foobnix.gui.model.signal import FControl
from foobnix.util.text_utils import capitalize_query
from foobnix.helpers.toggled import OneActiveToggledButton


class SearchControls(FControl, Gtk.VBox):
    def __init__(self, controls):        
        Gtk.VBox.__init__(self, False, 0)
        FControl.__init__(self, controls)
        self.controls = controls
        
        label = Gtk.Label()
        label.set_markup("<b>%s:</b>" % _("Search music online"))
        
        """default search function"""
        self.search_function = self.controls.search_top_tracks
        self.buttons = []      
        
        self.pack_start(self.search_line(), False, False, 0)

        #self.pack_start(controls.search_progress, False, False, 0)
        
        self.show_all()
        """search on enter"""
        for button in self.buttons:
            button.connect("key-press-event", self.on_search_key_press)
        
        """only one button active"""    
        OneActiveToggledButton(self.buttons)

    def set_search_function(self, search_function):
        logging.info("Set search function" + str(search_function))
        self.search_function = search_function
        
    def on_search(self, *w):
        thread.start_new_thread(self._on_search, ())
        #Otherwise you can't call authorization window,
        #it can be called only from not main loop

    def _on_search(self):
        def task():
            if self.get_query():
                if self.get_query().startswith("http://vk"):
                    self.controls.search_vk_page_tracks(self.get_query())                
                else:
                    self.search_function(self.get_query())
        self.controls.net_wrapper.execute(task)
    
    def get_query(self):
        query = self.entry.get_text()
        return capitalize_query(query)
        
    def search_line(self):
        self.entry = Gtk.Entry()
        online_text = _("Online Music Search, Play, Download")        

        self.entry.connect("key-press-event", self.on_search_key_press)
        
        self.entry.set_placeholder_text(online_text)
               
        combobox = self.combobox_creator()
        
        search_button = Gtk.Button(_("Search"))
        search_button.connect("clicked", self.on_search)
        
        hbox = Gtk.HBox(False, 0)
        searchLable = Gtk.Label()
        searchLable.set_markup("<b>%s</b>" % _("Online Search"))
        
        ##if Gtk.pygtk_version < (2, 22, 0):
        ##    hbox.pack_start(self.controls.search_progress, False, False)
        
        hbox.pack_start(combobox, False, False, 0)
        hbox.pack_start(self.entry, True, True, 0)
        hbox.pack_start(search_button, False, False, 0)
        hbox.show_all()
        
        return hbox 
    
    def set_search_text(self, text):
        self.entry.set_text(text)
    
    def on_search_key_press(self, w, e):
        if is_key_enter(e):
            self.on_search()
            self.entry.grab_focus()

    def combobox_creator(self):
        list_func = []
        liststore = Gtk.ListStore(str)

        liststore.append([_("Tracks")])
        list_func.append(self.controls.search_top_tracks)

        liststore.append([_("Albums")])
        list_func.append(self.controls.search_top_albums)
        
        liststore.append([_("Similar")])
        list_func.append(self.controls.search_top_similar)
        
        liststore.append([_("Genre")])
        list_func.append(self.controls.search_top_tags)

        liststore.append([_("VKontakte")])
        list_func.append(self.controls.search_all_tracks)
        
        #liststore.append([_("Video")])
        #list_func.append(self.controls.search_all_videos)
               
        combobox = Gtk.ComboBox(model=liststore)
        cell = Gtk.CellRendererText()
        combobox.pack_start(cell, True)
        combobox.add_attribute(cell, 'text', 0)
        combobox.set_active(0)
        self.set_search_function(list_func[0])
        
        def on_changed(combobox):
            n = combobox.get_active()
            self.set_search_function(list_func[n])
            self.entry.grab_focus()
        
        combobox.connect("changed", on_changed)     
        return combobox
        
    def show_menu(self, w, event, menu):
        menu.show_all()
        menu.popup(None, None, None, None, event.button, event.time)  

########NEW FILE########
__FILENAME__ = lastfm_service
#-*- coding: utf-8 -*-
'''
Created on 27 сент. 2010

@author: ivan
'''

import time
import thread
import logging
import datetime

from foobnix.fc.fc import FC
from foobnix.fc.fc_base import FCBase
from foobnix.gui.model import FModel
from foobnix.thirdparty.pylast import WSError, Tag
from foobnix.thirdparty import pylast

API_KEY = FCBase().API_KEY
API_SECRET = FCBase().API_SECRET


class Cache():
    def __init__(self, network):
        self.network = network
        self.cache_tracks = {}
        self.cache_albums = {}
        self.cache_images = {}

    def get_key(self, artist, title):
        return artist + "-" + title

    def get_track(self, artist, title):
        if not artist or not title:
            return None
        if self.get_key(artist, title) in self.cache_tracks:
            track = self.cache_tracks[self.get_key(artist, title)]
            logging.debug("Get track from cache " + str(track))
            return track
        else:
            track = self.network.get_track(artist, title)
            self.cache_tracks[self.get_key(artist, title)] = track
            return track

    def get_album(self, artist, title):
        if not artist or not title:
            return None
        track = self.get_track(artist, title)
        if track:
            if self.get_key(artist, title) in self.cache_albums:
                logging.debug("Get album from cache" + str(track))
                return self.cache_albums[self.get_key(artist, title)]
            else:
                album = track.get_album()
                if album:
                    self.cache_albums[self.get_key(artist, title)] = album
                    return album
        return None

    def get_album_image_url(self, artist, title, size=pylast.COVER_LARGE):
        if not artist or not title:
            return None
        if self.get_key(artist, title) in self.cache_images:
            logging.info("Get image from cache")
            return self.cache_images[self.get_key(artist, title)]
        else:
            album = self.get_album(artist, title)
            if album:
                image = album.get_cover_image(size)
                self.cache_images[self.get_key(artist, title)] = image
                return image


class LastFmService():
    def __init__(self, controls):
        self.connection = None
        self.network = None
        self.scrobbler = None
        self.preferences_window = None
        self.controls = controls
        thread.start_new_thread(self.init_thread, ())

    def connect(self):
        if self.network and self.scrobbler:
            return True
        return self.init_thread()

    def init_thread(self):
        time.sleep(5)
        if not self.controls.net_wrapper.is_internet():
            return None

        logging.debug("RUN INIT LAST.FM")
        username = FCBase().lfm_login
        password_hash = pylast.md5(FCBase().lfm_password)
        self.cache = None
        try:
            self.network = pylast.get_lastfm_network(api_key=API_KEY,
                                                     api_secret=API_SECRET,
                                                     username=username,
                                                     password_hash=password_hash)
            self.cache = Cache(self.network)

            """scrobbler"""
            scrobbler_network = pylast.get_lastfm_network(username=username, password_hash=password_hash)
            self.scrobbler = scrobbler_network.get_scrobbler("fbx", "1.0")
        except:
            self.network = None
            self.scrobbler = None
            self.controls.statusbar.set_text("Error last.fm connection with %s/%s" % (username, FCBase().lfm_password))
            logging.error("Either invalid last.fm login or password or network problems")
            """
            val = show_login_password_error_dialog(_("Last.fm connection error"), _("Verify user and password"), username, FC().lfm_password)
            if val:
                FC().lfm_login = val[0]
                FC().lfm_password = val[1]
            return False
            """
        return True

    def get_network(self):
        return self.network

    def get_user(self, username):
        return self.network.get_user(username)

    def get_authenticated_user(self):
        return self.network.get_authenticated_user()

    def get_loved_tracks(self, username, limit=50):
        lfm_tracks = self.get_user(username).get_loved_tracks(limit=limit)
        return self.sub_tracks_to_models(lfm_tracks, 'track')

    def get_recent_tracks(self, username, unused_limit=10):
        lfm_tracks = self.get_user(username).get_recent_tracks(limit=20)
        return self.sub_tracks_to_models(lfm_tracks, 'track')

    def get_top_tracks(self, username, unused):
        lfm_tracks = self.get_user(username).get_top_tracks()
        return self.sub_tracks_to_models(lfm_tracks, 'item')

    def get_top_artists(self, username, unused):
        lfm_tracks = self.get_user(username).get_top_artists()
        return self.sub_artist_to_models(lfm_tracks, 'item')

    def get_recommended_artists(self, username, limit=50):
        lfm_artists = self.get_authenticated_user().get_recommended_artists(limit=limit)
        return self.artists_to_models(lfm_artists)

    def get_friends(self, username):
        lfm_tracks = self.get_user(username).get_friends()
        list = self.get_sub_childs(lfm_tracks, 'name')
        result = []
        for item in list:
            result.append(FModel(item))
        return result

    def get_neighbours(self, username):
        lfm_tracks = self.get_user(username).get_neighbours()
        list = self.get_sub_childs(lfm_tracks, 'name')
        result = []
        for item in list:
            parent = FModel(item)
            result.append(parent)
        return result

    def get_scrobbler(self):
        return self.scrobbler

    def report_now_playing(self, bean):
        if not FC().enable_music_scrobbler:
            logging.debug("Last.fm scrobbler not enabled")
            return None
        if not self.get_scrobbler():
            logging.warn("no last.fm scrobbler")
            return None

        def task(bean):
            if bean.artist and bean.title:
                try:
                    bean.artist, bean.title = bean.artist.encode("utf-8"), bean.title.encode("utf-8")
                    self.get_scrobbler().report_now_playing(bean.artist, bean.title)
                    logging.debug("notify %s %s" % (bean.artist, bean.title))
                except Exception, e:
                    logging.error(str(e) + "Error reporting now playing last.fm" + str(bean.artist) + str(bean.title))
            else:
                logging.debug("Bean title or artist not defined")

        thread.start_new_thread(task, (bean,))

    def report_scrobbled(self, bean, start_time, duration_sec):
        if not FC().enable_music_scrobbler:
            logging.debug("Last.fm scrobbler not enabled")
            return None

        if not self.get_scrobbler():
            return None

        def task(bean):
            if bean.artist and bean.title:
                try:
                    bean.artist, bean.title = bean.artist.encode("utf-8"), bean.title.encode("utf-8")
                    self.get_scrobbler().scrobble(bean.artist, bean.title, start_time, "P", "", int(duration_sec))
                    logging.debug("Song Scrobbled " + str(bean.artist) + " " + str(bean.title) + " " + str(start_time) + " P: " + str(int(duration_sec)))
                except Exception, e:
                    logging.error(str(e) + "Error reporting now playing last.fm " + str(bean.artist) + " " + str(bean.title) + " A: " + str(bean.album))
            else:
                logging.debug("Bean title or artist not defined")

        thread.start_new_thread(task, (bean,))

    def connected(self):
        return self.network is not None

    def search_top_albums(self, aritst_name):
        if not self.connect():
            return None
        artist = self.network.get_artist(aritst_name)
        if not artist:
            return None
        try:
            albums = artist.get_top_albums()
        except WSError:
            logging.info("No artist with that name")
            return None

        beans = []
        for album in albums:
            try:
                album_txt = album.item
            except AttributeError:
                album_txt = album['item']

            name = album_txt.get_name()
            #year = album_txt.get_release_year()
            year = None
            if year:
                bean = FModel(name + "(" + year + ")").add_album(name).add_artist(aritst_name).add_year(year)
            else:
                bean = FModel(name).add_album(name).add_artist(aritst_name).add_year(year)

            beans.append(bean)
        return beans

    """some parent linke LoveTrack"""
    def sub_tracks_to_models(self, love_tracks, key='track'):
        tracks = []
        for love_track in love_tracks:
            try:
                track = getattr(love_track, key)
            except AttributeError:
                track = love_track[key]
            tracks.append(track)

        return self.tracks_to_models(tracks)

    def get_sub_childs(self, list, key='name'):
        result = []
        for item in list:
            try:
                artist = getattr(item, key)
            except AttributeError:
                artist = item[key]
            result.append(artist)
        return result

    def sub_artist_to_models(self, topartists, key='item'):
        artists = []
        for love_track in topartists:
            try:
                artist = getattr(love_track, key)
            except AttributeError:
                artist = love_track[key]
            artists.append(artist)

        return self.artists_to_models(artists)

    def tracks_to_models(self, tracks):
        results = []
        for track in tracks:
            artist = track.get_artist().get_name()
            title = track.get_title()
            bean = FModel(artist + " - " + title).add_artist(artist).add_title(title)
            results.append(bean)
        return results

    def artists_to_models(self, artists):
        results = []
        for track in artists:
            artist = track.get_name()
            bean = FModel(artist).add_artist(artist)
            results.append(bean)
        return results

    def search_album_tracks(self, artist_name, album_name):
        if not artist_name or not album_name:
            logging.warn("search_album_tracks artist and album is empty")
            return []
        if not self.connect():
            return None
        album = self.network.get_album(artist_name, album_name)
        tracks = album.get_tracks()
        return self.tracks_to_models(tracks)

    def search_top_tags(self, tag):

        logging.debug("Search tag " + tag)
        if not self.connect():
            return None
        if not tag:
            logging.warn("search_top_tags TAG is empty")
            return []
        beans = []
        tags = self.network.search_for_tag(tag)
        for tag in tags.get_next_page():
                tag_name = tag.get_name()
                bean = FModel(tag_name).add_genre(tag_name)
                beans.append(bean)
        return beans

    def search_top_tag_tracks(self, tag_name):
        logging.warn("search_top_tag tracks"+tag_name)
        if not self.connect():
            return None
        if not tag_name:
            logging.warn("search_top_tags TAG is empty")
            return []

        tag = Tag(tag_name, self.network)
        tracks = tag.get_top_tracks()

        beans = []

        for track in tracks:

            try:
                track_item = track.item
            except AttributeError:
                track_item = track['item']

            #LOG.info(track_item.get_duration())

            #bean = CommonBean(name=str(track_item), path="", type=CommonBean.TYPE_MUSIC_URL, parent=query);
            artist = track_item.get_artist().get_name()
            title = track_item.get_title()
            text = artist + " - " + title
            bean = FModel(text).add_artist(artist).add_title(title)
            beans.append(bean)

        return beans

    def search_top_tracks(self, artist_name):
        if not self.connect():
            return None
        artist = self.network.get_artist(artist_name)
        if not artist:
            return []
        try:
            tracks = artist.get_top_tracks()
        except WSError:
            logging.info("No artist with that name")
            return []

        beans = []

        for track in tracks:

            try:
                track_item = track.item
            except AttributeError:
                track_item = track['item']

            #LOG.info(track_item.get_duration())

            #bean = CommonBean(name=str(track_item), path="", type=CommonBean.TYPE_MUSIC_URL, parent=query);
            artist = track_item.get_artist().get_name()
            title = track_item.get_title()
            text = artist + " - " + title
            bean = FModel(text).add_artist(artist).add_title(title)
            beans.append(bean)

        return beans

    def search_top_similar_artist(self, artist_name, count=45):
        if not self.connect():
            return None
        if not artist_name:
            logging.warn("search_top_similar_artist, Artist name is empty")
            return []

        artist = self.network.get_artist(artist_name)
        if not artist:
            return []

        artists = artist.get_similar(count)
        beans = []
        for artist in artists:
            try:
                artist_txt = artist.item
            except AttributeError:
                artist_txt = artist['item']

            artist_name = artist_txt.get_name()
            bean = FModel(artist_name).add_artist(artist_name).add_is_file(True)

            beans.append(bean)
        return beans

    def search_top_similar_tracks(self, artist, title):
        if not self.connect():
            return None

        if not artist or not title:
            logging.warn("search_top_similar_tags artist or title is empty")
            return []

        track = self.cache.get_track(artist, title)
        if not track:
            logging.warn("search_top_similar_tracks track not found")
            return []

        similars = track.get_similar()
        beans = []
        for tsong in similars:
            try:
                tsong_item = tsong.item
            except AttributeError:
                tsong_item = tsong['item']

            artist = tsong_item.get_artist().get_name()
            title = tsong_item.get_title()
            model = FModel(artist + " - " + title).add_artist(artist).add_title(title).add_is_file(True)
            beans.append(model)

        return beans

    def search_top_similar_tags(self, artist, title):
        if not self.connect():
            return None

        if not artist or not title:
            logging.warn("search_top_similar_tags artist or title is empty")
            return []

        track = self.cache.get_track(artist, title)

        if not track:
            logging.warn("search_top_similar_tags track not found")
            return []

        tags = track.get_top_tags()
        beans = []
        for tag in tags:
            try:
                tag_item = tag.item
            except AttributeError:
                tag_item = tag['item']

            tag_name = tag_item.get_name()
            model = FModel(tag_name).add_genre(tag_name).add_is_file(True)
            beans.append(model)
        return beans

    def get_album_name(self, artist, title):
        if not self.connect():
            return None
        album = self.cache.get_album(artist, title)
        if album:
            return album.get_name()

    def get_album_year(self, artist, title):
        if not self.connect():
            return None
        album = self.cache.get_album(artist, title)
        if album:
            st_date = str(album.get_release_date())
            try:
                dt = datetime.datetime.strptime(st_date, "%d %b %Y, %H:%M")
            except:
                if st_date:
                    i = st_date.find(",")
                    return st_date[i - 4:i]
                else:
                    return st_date
            return str(dt.year)

    def get_album_image_url(self, artist, title, size=pylast.COVER_LARGE):
        if not self.connect():
            return None
        return self.cache.get_album_image_url(artist, title)

    def love(self, bean):
        track = self.cache.get_track(bean.artist, bean.title)
        track.love()
        logging.debug("I love this track %s-%s" % (bean.artist, bean.title))

########NEW FILE########
__FILENAME__ = lyrics_parsing_service
'''
Created on Sep 1, 2012

@author: zavlab1
'''

import urllib
import logging
from HTMLParser import HTMLParser


class LyricsFinder(HTMLParser):
    def __init__(self, tagname=None, attr=None, attr_value=None):
        HTMLParser.__init__(self)
        self.data = []
        self.needed_tag = 0
        self.tagname = tagname
        self.attr = attr
        self.attr_value = attr_value

    def get_lyrics_from_lyricsmania(self, artist, title):
        base = "http://www.lyricsmania.com/"
        self.tagname = 'div'
        self.attr = 'id'
        self.attr_value = 'songlyrics_h'
        title = title.encode('utf-8').strip().replace(" ", "_").replace("/", "-")
        title = urllib.quote(title)
        artist = artist.encode('utf-8').strip().replace(" ", "_").replace("/", "-")
        artist = urllib.quote(artist)
        result = urllib.urlopen(base + title + "_lyrics_" + artist + ".html").read()
        result = result.replace('&#039;', '!apostrophe!')
        self.feed(result)
        return "\n".join(self.data).replace('!apostrophe!', '&#039;')

    def get_lyrics_from_megalyrics(self, artist, title):
        base = "http://megalyrics.ru/lyric/"
        self.tagname = 'pre'
        self.attr = 'class'
        self.attr_value = 'lyric'
        title = title.replace(" ", "-").replace("/", "-")
        title = urllib.quote(title)
        artist = artist.replace(" ", "-").replace("/", "-")
        artist = urllib.quote(artist)
        result = urllib.urlopen(base + artist + "/" + title + ".html").read()
        result = result.replace('&#039;', '!apostrophe!').replace('<br/><br/>', '<br/>\n<br/>')
        self.feed(result)
        del self.data[0]
        return "\n".join(self.data).replace('!apostrophe!', "\'")

    def handle_starttag(self, tag, attrs):
        if tag == self.tagname:
            for name, value in attrs:
                if name == self.attr and value == self.attr_value:
                    self.needed_tag = 1

    def handle_endtag(self, tag):
        if tag == self.tagname and self.needed_tag:
            self.needed_tag = 0

    def handle_data(self, data):
        if self.needed_tag:
            self.data.append(data.strip())


def get_lyrics_by_parsing(artist, title):
    if not artist or not title:
        return ""

    if "lyrics_finder" not in globals():
        global lyrics_finder
        lyrics_finder = LyricsFinder()
    artist = artist.encode('utf-8').strip()
    title = title.encode('utf-8').strip()
    lyrics_finder.data = []
    text = None
    try:
        logging.debug("Try to get lyrics from lyricsmania.com")
        text = lyrics_finder.get_lyrics_from_lyricsmania(artist, title)
    except:
        logging.info("Error occurred when getting lyrics from lyricsmania.com")

    if not text:
        try:
            logging.debug("Try to get lyrics from megalyrics.ru")
            text = lyrics_finder.get_lyrics_from_megalyrics(artist, title)
        except:
            logging.info("Error occurred when getting lyrics from megalyrics.ru")

    lyrics_finder.reset()
    return text


if __name__ == '__main__':
    print get_lyrics_by_parsing("aBBA", " honey, Honey ")
########NEW FILE########
__FILENAME__ = music_service
#-*- coding: utf-8 -*-
'''
Created on 25 сент. 2010

@author: ivan
'''
import os
from gi.repository import Gtk
import logging

from foobnix.fc.fc import FC
from foobnix.gui.model import FModel
from foobnix.helpers.window import ChildTopWindow
from foobnix.util.file_utils import file_extension, get_file_extension
from foobnix.util.list_utils import sort_by_song_name
from foobnix.util.id3_file import update_id3_wind_filtering


def get_all_music_by_paths(paths, controls):
    '''end_scanning = False
    pr_window = ProgWindow(controls)
    #pr_window.analyzed_folders += 1

    def task():
        while not end_scanning:
            time.sleep(0.5)
            GObject.idle_add(pr_window.update_window)

    thread.start_new_thread(task, ())'''
    result = []
    for path in paths:
        if path == "/":
            logging.info("Skip root folder")
            continue
        current_result = _scanner(path, None)
        result = result + current_result
    #end_scanning = True
    #GObject.idle_add(pr_window.hide)
    return result

def get_all_music_with_id3_by_path(path, with_cue_filter=None):
    beans = simple_scanner(path, None)
    all = []
    if with_cue_filter:
        for bean in beans:
            if get_file_extension(bean.path) == ".cue":
                all.append(bean)
    beans = all if all else beans
    return update_id3_wind_filtering(beans)

def _scanner(path, level):
    try:
        path = path.encode("utf-8")
    except:
        pass

    results = []
    if not os.path.exists(path):
        return
    dir = os.path.abspath(path)

    list = sort_by_name(path, os.listdir(dir))

    for file in list:
        full_path = os.path.join(path, file)

        if os.path.isfile(full_path):
            #pr_window.analyzed_files += 1
            if file_extension(file) not in FC().all_support_formats:
                continue

        if os.path.isdir(full_path):
            #pr_window.analyzed_folders += 1
            if is_dir_with_music(full_path):
                #pr_window.media_folders += 1
                b_bean = FModel(file, full_path).add_parent(level).add_is_file(False)
                results.append(b_bean)
                results.extend(_scanner(full_path, b_bean.get_level()))
        elif os.path.isfile(full_path):
            results.append(FModel(file, full_path).add_parent(level).add_is_file(True))
            #pr_window.media_files +=1

    return results

def simple_scanner(path, level):
    try:
        path = path.encode("utf-8")
    except:
        pass

    results = []
    if not os.path.exists(path):
        return
    dir = os.path.abspath(path)

    list = sort_by_name(path, os.listdir(dir))

    for file in list:
        full_path = os.path.join(path, file)

        if os.path.isfile(full_path):
            if file_extension(file) not in FC().all_support_formats:
                continue;

        if os.path.isdir(full_path):
            if is_dir_with_music(full_path):
                b_bean = FModel(file, full_path).add_parent(level).add_is_file(False)
                results.append(b_bean)
                results.extend(simple_scanner(full_path, b_bean.get_level()))
        elif os.path.isfile(full_path):
            results.append(FModel(file, full_path).add_parent(level).add_is_file(True))

    return results

def scanner(path, level):
    try:
        path = path.encode("utf-8")
    except:
        pass

    results = []
    if not os.path.exists(path):
        return
    dir = os.path.abspath(path)

    list = sort_by_name(path, os.listdir(dir))

    for file in list:
        full_path = os.path.join(path, file)

        if os.path.isfile(full_path):
            if file_extension(file) not in FC().all_support_formats:
                continue

        if os.path.isdir(full_path):
            if is_dir_with_music(full_path):
                b_bean = FModel(file, full_path).add_parent(level).add_is_file(False)
                results.append(b_bean)
                results.extend(simple_scanner(full_path, b_bean.get_level()))
        elif os.path.isfile(full_path):
            results.append(FModel(file, full_path).add_parent(level).add_is_file(True))

    return results


def sort_by_name(path, list):
    files = []
    directories = []
    for file in list:
        full_path = os.path.join(path, file)
        if os.path.isdir(full_path):
            directories.append(file)
        else:
            files.append(file)

    return sorted(directories) + sort_by_song_name(files)

def is_dir_with_music(path):
    list = None
    try:
        list = os.listdir(path)
    except OSError, e:
        logging.info("Can't get list of dir"+ str(e))

    if not list:
        return False

    for file in list:
        full_path = os.path.join(path, file)
        if os.path.isdir(full_path):
            if is_dir_with_music(full_path):
                return True
        else:
            if file_extension(file) in FC().all_support_formats:
                return True
    return False

class ProgWindow(ChildTopWindow):
    def __init__(self, controls):
        ChildTopWindow.__init__(self, "Progress", 500, 100)

        self.set_transient_for(controls.main_window)

        self.label = Gtk.Label("Total analyzed folders: ")
        self.label1 = Gtk.Label("Total analyzed files: ")
        self.label2 = Gtk.Label("Folders with media files found: ")
        self.label3 = Gtk.Label("Media files found: ")

        self.analyzed_files_label = Gtk.Label("0")
        self.analyzed_folders_label = Gtk.Label("0")
        self.media_files_label = Gtk.Label("0")
        self.media_folders_label = Gtk.Label("0")

        self.analyzed_files = 0
        self.analyzed_folders = 0
        self.media_files = 0
        self.media_folders = 0

        left_box = Gtk.VBox()
        left_box.pack_start(self.label)
        left_box.pack_start(self.label1)
        left_box.pack_start(self.label2)
        left_box.pack_start(self.label3)

        right_box = Gtk.VBox()
        right_box.pack_start(self.analyzed_folders_label)
        right_box.pack_start(self.analyzed_files_label)
        right_box.pack_start(self.media_folders_label)
        right_box.pack_start(self.media_files_label)

        box = Gtk.HBox()
        box.pack_start(left_box)
        box.pack_start(right_box)

        self.add(box)

        self.show_all()

    def update_window(self):
        self.analyzed_folders_label.set_text(str(self.analyzed_folders))
        self.analyzed_files_label.set_text(str(self.analyzed_files))
        self.media_files_label.set_text(str(self.media_files))
        self.media_folders_label.set_text(str(self.media_folders))


########NEW FILE########
__FILENAME__ = path_service
#-*- coding: utf-8 -*-
'''
Created on 3 окт. 2010

@author: ivan
'''
import os.path, sys
import logging


def get_foobnix_resourse_path_by_name(filename):
    if not filename:
        return None

    paths = ["/usr/local/share/pixmaps",
             "/usr/local/share/foobnix",
             "/usr/share/pixmaps",
             "/usr/share/foobnix",
             "share/pixmaps",
             "share/foobnix",
             "share/pixmaps",
             "./",
             filename]

    if len(sys.path) > 1:
        paths.append(sys.path[0])
        paths.append(os.path.join(sys.path[0], "share/pixmaps"))
        paths.append(os.path.join(sys.path[0], "share/foobnix"))

    for path in paths:
        full_path = os.path.join(path, filename)
        if os.path.isfile(full_path):
            return full_path

    logging.error("File " + filename + " not found")
    raise TypeError("******* WARNING: File " + filename + " not found *******")

########NEW FILE########
__FILENAME__ = radio_service
'''
Created on 15  2010

@author: ivan
'''
from __future__ import with_statement
import os
import sys
import logging


FOOBNIX_RADIO_PATHS = [
    os.path.join(sys.path[0], "share/foobnix/radio"),
    "share/foobnix/radio",
    "/usr/local/share/foobnix/radio",
    "/usr/share/foobnix/radio"
    ]
EXTENSION = ".fpl"


class FPL():
    def __init__(self, name, urls_dict):
        self.name = name
        self.urls_dict = urls_dict

    def __str__(self):
        return self.name + "radios" + str(self.urls_dict)


class RadioFolder():
    def __init__(self):
        pass

    """get list of foobnix playlist files in the directory"""
    def get_radio_list(self):
        result = []
        for cur_path in FOOBNIX_RADIO_PATHS:
            if os.path.isdir(cur_path):
                """read directory files by extestion and size > 0 """
                for item in os.listdir(cur_path):
                    path = os.path.join(cur_path, item)
                    if item.endswith(EXTENSION) and os.path.isfile(path) and os.path.getsize(path) > 0:
                        logging.info("Find radio station playlist " + str(item))
                        if item not in result:
                            result.append(item)
        return result

    """parser playlist by name"""
    def parse_play_list(self, list_name):
        for path in FOOBNIX_RADIO_PATHS:
            full_path = os.path.join(path, list_name)

            if not os.path.isfile(full_path):
                logging.debug("Not a file " + full_path)
                continue

            dict = {}

            """get name and stations"""
            with open(full_path) as file:
                for line in file:
                    if line and not line.startswith("#") and "=" in line:
                        name_end = line.find("=")
                        name = line[:name_end].strip()
                        stations = line[name_end + 1:].split(",")
                        if stations:
                            good_stations = []
                            for url in stations:
                                good_url = url.strip()
                                if good_url and (good_url.startswith("http://") or good_url.startswith("file://")):
                                    if not good_url.endswith("wma"):
                                        if not good_url.endswith("asx"):
                                            if not good_url.endswith("ram"):
                                                good_stations.append(good_url)
                                                dict[name] = good_stations
            return dict

    def get_radio_FPLs(self):
        names = self.get_radio_list()
        if not names:
            return []

        results = []
        for play_name in names:
            content = self.parse_play_list(play_name)
            logging.info("Create FPL" + play_name)
            play_name = play_name[:-len(EXTENSION)]
            results.append(FPL(play_name, content))
        return results

########NEW FILE########
__FILENAME__ = vk_service

# -*- coding: utf-8 -*-
'''
Created on Sep 29, 2010

@author: ivan
'''

import os
import gi
gi.require_version("WebKit", "3.0")

import threading
import time
import urllib
import logging
import urllib2
import simplejson

from gi.repository import Gtk
from gi.repository import GLib
from gi.repository import WebKit
from gi.repository import Soup

from HTMLParser import HTMLParser
from urlparse import urlparse
from foobnix.fc.fc import FC, FCBase
from foobnix.gui.model import FModel
from foobnix.fc.fc_helper import CONFIG_DIR
from foobnix.util.time_utils import convert_seconds_to_text

cookiefile = os.path.join(CONFIG_DIR, "vk_cooky")


class VKWebkitAuth(Gtk.Dialog):

    SCOPE = ["audio", "friends", "wall"]
    CLIENT_ID = "2234333"

    def __init__(self):
        super(VKWebkitAuth, self).__init__(_("vk.com authorization"), None, Gtk.DialogFlags.MODAL, ())

        self.set_size_request(550, -1)
        self.auth_url = "http://oauth.vk.com/oauth/authorize?" + \
                        "redirect_uri=http://oauth.vk.com/blank.html&response_type=token&" + \
                        "client_id=%s&scope=%s" % (self.CLIENT_ID, ",".join(self.SCOPE))
        self.web_view = WebKit.WebView()
        self.web_view.show()
        self.vbox.pack_start(self.web_view, False, False, 0)

        self.web_view.connect('onload-event', self.on_load)
        session = WebKit.get_default_session()
        if FC().proxy_enable and FC().proxy_url:
            if FC().proxy_user and FC().proxy_password:
                proxy_url = "http://%s:%s@%s" % (FC().proxy_user, FC().proxy_password, FC().proxy_url)
            else:
                proxy_url = "http://%s" % FC().proxy_url
            soup_url = Soup.URI.new(proxy_url)
            session.set_property("proxy-uri", soup_url)
        else:
            session.set_property("proxy-uri", None)

        cookiejar = Soup.CookieJarText.new(cookiefile, False)
        session.add_feature(cookiejar)

        self.access_token = None
        self.user_id = None
        self.first_page_loaded = False

    def auth_user(self, check_only=False):
        if check_only:
            return self.access_token, self.user_id if self.access_token and self.user_id else None
        self.web_view.open(self.auth_url)
        logging.debug("waiting for answer...")
        while not self.first_page_loaded:
            Gtk.main_iteration()
        logging.debug("answer found!")
        logging.debug(self.access_token)
        logging.debug(self.user_id)
        if self.access_token and self.user_id:
            return self.access_token, self.user_id
        result = self.run()
        if (result == Gtk.ResponseType.ACCEPT) and self.access_token and self.user_id:
            return self.access_token, self.user_id
        return None

    def extract_answer(self, url):
        def split_key_value(kv_pair):
            kv = kv_pair.split("=")
            if len(kv) == 2:
                return kv[0], kv[1]  # ["key", "val"], e.g. key=val
            else:
                return kv[0], None  # ["key"], e.g. key= or key
        return dict(split_key_value(kv_pair) for kv_pair in url.fragment.split("&"))

    def on_load(self, webview, frm):
        url = urlparse(webview.get_property("uri"))
        if url.path == "/blank.html":
            answer = self.extract_answer(url)
            if "access_token" in answer and "user_id" in answer:
                self.access_token, self.user_id = answer["access_token"], answer["user_id"]
            self.response(Gtk.ResponseType.ACCEPT)
        self.first_page_loaded = True


class VKService:
    def __init__(self, token, user_id):
        self.set_token_user(token, user_id)
        self.authorized_lock = threading.Lock()

    def auth(self, check_only=False):
        logging.debug("do auth")
        self.auth_res = None
        self.task_finished = False

        def safetask():
            self.auth_res = False
            logging.debug("trying to auth")
            auth_provider = VKWebkitAuth()
            res = auth_provider.auth_user(check_only)
            auth_provider.destroy()
            if res:
                FC().access_token = res[0]
                FC().user_id = res[1]
                self.set_token_user(res[0], res[1])
                self.auth_res = True
            self.task_finished = True
            logging.debug("task finished, result is %s" % str(res))
        GLib.idle_add(safetask)
        logging.debug("idle task added, waiting...")
        while not self.task_finished:
            time.sleep(0.1)
        logging.debug("auth result is %s" % self.auth_res)
        return self.auth_res

    def set_token_user(self, token, user_id):
        self.token = token
        self.user_id = user_id

    def get_result(self, method, data, attempt_count=0):
        logging.debug("get_result(%s, %s, %s)" % (method, data, attempt_count))
        result = self.get(method, data)
        if not result:
            return
        logging.debug("result " + result)
        try:
            object = self.to_json(result)
        except simplejson.JSONDecodeError, e:
            logging.error(e)
            return
        if "response" in object:
            return object["response"]
        elif "error" in object:
            logging.debug("error found!")
            if attempt_count > 0:
                return
            if not self.auth():
                return
            time.sleep(1)
            attempt_count += 1
            return self.get_result(method, data, attempt_count)

    def reset_vk(self):
        if os.path.isfile(cookiefile):
            os.remove(cookiefile)

        FC().access_token = None
        FC().user_id = None
        FCBase().vk_login = None
        FCBase().vk_password = None
        self.token = None
        self.user_id = None
        self.connected = False

    def get(self, method, data):
        url = "https://api.vk.com/method/%(METHOD_NAME)s?%(PARAMETERS)s&access_token=%(ACCESS_TOKEN)s" % {'METHOD_NAME':method, 'PARAMETERS':data, 'ACCESS_TOKEN':self.token }
        if (method == 'audio.search'):
             count = FC().search_limit
             url = url + "&count=%(COUNT)s" % {'COUNT': count }

        if (FC().enable_vk_autocomlete == True):
             url = url + "&auto_complete=1"
        else:
             url = url + "&auto_complete=0"

        logging.debug("Try to get response from vkontakte")
        try:
            response = urllib2.urlopen(url, timeout=7)
            if "response" not in vars():
                logging.error("Can't get response from vkontakte")
                return
        except IOError:
            logging.error("Can't get response from vkontakte")
            return
        result = response.read()
        return result

    def to_json(self, json):
        p = HTMLParser()
        json = p.unescape(json)
        return simplejson.loads(json)

    def get_profile(self, without_auth=False):
        return self.get_result("getProfiles", "uid=" + str(self.user_id), 1 if without_auth else 0)

    def find_tracks_by_query(self, query):
        logging.info("start search songs " + query)
        query = urllib.quote(query.encode("utf-8"))

        list = self.get_result("audio.search", "q=" + query)
        childs = []

        if not list:
            return childs

        for line in list[1:]:
            bean = FModel(line['artist'] + ' - ' + line['title'])
            bean.aritst = line['artist']
            bean.title = line['title']
            bean.time = convert_seconds_to_text(line['duration'])
            bean.path = line['url']
            bean.vk_audio_id = "%s_%s" % (line['owner_id'], line['aid'])
            childs.append(bean)

        return childs

    def find_tracks_by_url(self, url):
        logging.debug("Search By URL")

        index = url.rfind("#")
        if index > 0:
            url = url[:index]
        index = url.find("id=")
        if index < 0:
            return None

        id = url[index + 3:]
        id = int(id)
        if id > 0:
            results = self.get_result('audio.get', "uid=" + str(id))
        else:
            results = self.get_result('audio.get', "gid=" + str(abs(id)))

        childs = []
        for line in results:
            bean = FModel(line['artist'] + ' - ' + line['title'])
            bean.aritst = line['artist']
            bean.title = line['title']
            bean.time = convert_seconds_to_text(line['duration'])
            bean.path = line['url']
            bean.vk_audio_id = "%s_%s" % (line['owner_id'], line['aid'])
            childs.append(bean)

        return childs

    def find_one_track(self, query):
        vkSongs = self.find_tracks_by_query(query)
        if not vkSongs:
            return None
        #We want the most common song, so we search it using the track duration
        times_count = {}
        for song in vkSongs:
            time = song.time
            if time in times_count:
                times_count[time] += 1
            else:
                times_count[time] = 1
        #get most relatives times time
        r_count = max(times_count.values())
        r_time = self.find_time_value(times_count, r_count)
        logging.info("Song time " + str(r_time))
        logging.info("Count of songs with this time " + str(r_count))

        for song in vkSongs:
            if song.time == r_time:
                return song

        return vkSongs[0]

    def find_track_by_id(self, id):
        result = self.get_result("audio.get", "audios=" + str(id))
        if not result:
            return None
        line = result[0]
        bean = FModel(line['artist'] + ' - ' + line['title'])
        bean.aritst = line['artist']
        bean.title = line['title']
        bean.time = convert_seconds_to_text(line['duration'])
        bean.path = line['url']
        bean.vk_audio_id = "%s_%s" % (line['owner_id'], line['aid'])
        return bean


    def find_time_value(self, times_count, r_count):
        for i in times_count:
            if times_count[i] == r_count:
                return i
        return None

    def add(self, bean):
         if (bean.vk_audio_id != None):
             ids=bean.vk_audio_id.split('_')
             url = "https://api.vk.com/method/audio.add?access_token=%(ACCESS_TOKEN)s&aid=%(AID)s&oid=%(OID)s" % {'ACCESS_TOKEN':self.token, 'AID':ids[1], 'OID':ids[0] }
             #logging.debug("GET " + url)
             logging.debug("Try add audio to vkontakte")
             try:
                 response = urllib2.urlopen(url, timeout=7)
                 if "response" not in vars():
                     logging.error("Can't get response from vkontakte")
                     return
             except IOError:
                 logging.error("Can't get response from vkontakte")
                 return
             result = response.read()
         return result

########NEW FILE########
__FILENAME__ = state
#-*- coding: utf-8 -*-
'''
Created on 23 сент. 2010

@author: ivan
'''
class LoadSave(object):
    def __init__(self):
        pass

    def on_load(self):
        raise Exception("Method not defined on_load", self.__class__.__name__)

    def on_save(self):
        raise Exception("Method not defined on_save", self.__class__.__name__)


class Quitable(object):

    def on_quit(self):
        pass


class Filterable(object):

    def filter_by_file(self, value):
        pass

    def filter_by_folder(self, value):
        pass
########NEW FILE########
__FILENAME__ = top
#-*- coding: utf-8 -*-
'''
Created on 22 сент. 2010

@author: ivan
'''

from gi.repository import Gtk

from foobnix.gui.model.signal import FControl
from foobnix.gui.state import LoadSave
from foobnix.gui.menu import MenuBarWidget
from foobnix.helpers.my_widgets import ImageButton
from foobnix.helpers.menu import Popup
from foobnix.fc.fc import FC
from foobnix.util.widget_utils import MenuStyleDecorator

class TopWidgets(FControl, LoadSave, Gtk.HBox):
    def __init__(self, controls):
        FControl.__init__(self, controls)
        Gtk.HBox.__init__(self, False, 0)

        self.old_menu = MenuBarWidget(controls)


        self.pack_start(self.old_menu.widget, False, False, 0)

        self.new_menu_button = ImageButton(Gtk.STOCK_PREFERENCES)
        self.new_menu_button.connect("button-press-event", self.on_button_press)

        self.pack_start(self.new_menu_button, False, False, 0)
        self.pack_start(controls.playback, False, False, 0)
        self.pack_start(controls.os, False, False, 0)
        self.pack_start(controls.volume, False, False, 0)
        self.pack_start(Gtk.SeparatorToolItem.new(), False, False, 0)
        self.pack_start(controls.record, False, False, 0)
        self.pack_start(controls.seek_bar, True, True, 0)

        """menu init"""
        menu = Popup()
        decorator = MenuStyleDecorator()
        MenuBarWidget(self.controls, menu)
        menu.add_separator()
        menu.add_item(_("Preferences"), Gtk.STOCK_PREFERENCES, self.controls.show_preferences)
        menu.add_separator()
        menu.add_item(_("Quit"), Gtk.STOCK_QUIT, self.controls.quit)

        decorator.apply(menu)
        self.menu = menu

    def update_menu_style(self):
        if FC().menu_style == "new":
            self.old_menu.widget.hide()
            self.new_menu_button.show()
        else:
            self.old_menu.widget.show()
            self.new_menu_button.hide()

    def on_save(self):
        self.controls.volume.on_save()
        self.old_menu.on_save()

    def on_load(self):
        self.controls.volume.on_load()
        self.old_menu.on_load()
        self.controls.os.on_load()
        self.update_menu_style()

    def on_button_press(self, w, e):
        self.menu.show(e)

########NEW FILE########
__FILENAME__ = common_tree
#-*- coding: utf-8 -*-
'''
Created on 20 окт. 2010

@author: ivan
'''

import sys
import logging

from gi.repository import Gtk
from gi.repository import Gdk
from gi.repository import GLib
from gi.repository import GObject
from random import randint

from foobnix.fc.fc_cache import fcache_save_lock
from foobnix.gui.model.signal import FControl
from foobnix.gui.model import FTreeModel, FModel
from foobnix.gui.treeview.filter_tree import FilterTreeControls
from foobnix.util import idle_task


class CommonTreeControl(FTreeModel, FControl, FilterTreeControls):

    def __init__(self, controls):
        FilterTreeControls.__init__(self, controls)

        FTreeModel.__init__(self)
        FControl.__init__(self, controls)

        self.get_selection().set_mode(Gtk.SelectionMode.MULTIPLE)
        self.set_enable_tree_lines(True)

        """model config"""
        self.model = MyTreeStore(*FTreeModel().types())

        """filter config"""
        self.filter_model = self.model.filter_new()
        self.filter_model.set_visible_column(self.visible[0])
        self.set_model(self.filter_model)

        """connectors"""
        self.connect("button-press-event", self.on_button_press)
        self.connect("key-release-event", self.on_key_release)
        self.connect("row-expanded", self.on_row_expanded)
        self.connect('button_press_event', self.on_multi_button_press)
        self.connect('button_release_event', self.on_multi_button_release)

        self.count_index = 0

        self.set_reorderable(False)
        self.set_headers_visible(False)

        self.set_type_plain()

        self.active_UUID = -1

        self.defer_select = False

        self.scroll = Gtk.ScrolledWindow()
        self.scroll.set_policy(Gtk.PolicyType.AUTOMATIC, Gtk.PolicyType.AUTOMATIC)
        self.scroll.add(self)

    def on_row_expanded(self, widget, iter, path):
        bean = self.get_bean_from_path(path)
        self.on_bean_expanded(bean)

    def get_bean_from_path(self, path_string):
        iter = self.model.get_iter(path_string)
        return self.get_bean_from_iter(iter)

    def on_bean_expanded(self, bean):
        pass

    def on_multi_button_press(self, widget, event):
        target = self.get_path_at_pos(int(event.x), int(event.y))
        if (target and event.type == Gdk.BUTTON_PRESS and not (event.state & (Gdk.ModifierType.CONTROL_MASK | Gdk.ModifierType.SHIFT_MASK )) #@UndefinedVariable
            and self.get_selection().path_is_selected(target[0])):
            # disable selection
            self.get_selection().set_select_function(lambda * ignore: False, False)
            self.defer_select = target[0]

    def on_multi_button_release(self, widget, event):
        self.get_selection().set_select_function(lambda * ignore: True, False)

        target = self.get_path_at_pos(int(event.x), int(event.y))
        if (self.defer_select and target and self.defer_select == target[0] and not (event.x == 0 and event.y == 0)): # certain drag and drop
            self.set_cursor(target[0], target[1], False)

        self.defer_select = False

    def rename_selected(self, text):
        selection = self.get_selection()
        fm, paths = selection.get_selected_rows()#@UnusedVariable
        path = paths[0]
        path = self.filter_model.convert_path_to_child_path(path)
        iter = self.model.get_iter(path)
        self.model.set_value(iter, self.text[0], text)

    def populate(self, bean):
        self.clear()
        self.append(bean)

    def populate_all(self, beans):
        self.clear_tree()
        self.append_all(beans)

    def get_bean_from_iter(self, iter):
        return self.get_bean_from_model_iter(self.model, iter)

    def get_bean_from_row(self, row):
        bean = FModel()
        id_dict = FTreeModel().cut().__dict__
        for key in id_dict.keys():
            num = id_dict[key]
            setattr(bean, key, row[num])
        return bean

    def get_row_from_bean(self, bean):
        #logging.debug("get_row_from_bean %s" % bean)
        attributes = []
        m_dict = FTreeModel().cut().__dict__
        new_dict = dict (zip(m_dict.values(), m_dict.keys()))

        for key in new_dict.values():
            if not hasattr(bean, key):
                setattr(bean, key, None)

            value = getattr(bean, key)
            if type(value) in [int, float, long]:
                value = str(value)
            attributes.append(value)

        #logging.debug("get_row_from_bean attributes %s" % attributes)
        return attributes

    def get_row_from_model_iter(self, model, iter):
        attributes = []
        size = len(FTreeModel().__dict__)
        for i in xrange(size):
            value = model.get_value(iter, i)
            attributes.append(value)
        return attributes

    def get_previous_iter(self, model, iter):
        path = model.get_path(iter)
        if path[-1] != 0:
            previous_path = path[:-1] + (path[-1] - 1,)
            return model.get_iter(previous_path)

    def get_iter_from_row_reference(self, row_reference):
        model = row_reference.get_model()
        path = row_reference.get_path()
        return model.get_iter(path)

    def get_row_reference_from_iter(self, model, iter):
        path = model.get_path(iter)
        return Gtk.TreeRowReference.new(model, path)

    def save_rows_from_tree(self, dict):
        try:
            fcache_save_lock.acquire()
            dict.clear()
            iter = self.model.get_iter_first()
            def task(iter):
                str_path = self.model.get_string_from_iter(iter)
                row = self.get_row_from_iter(self.model, iter)
                dict[tuple([int(i) for i in str_path.split(':')])] = row
                for n in xrange(self.model.iter_n_children(iter)):
                    child_iter = self.model.iter_nth_child(iter, n)
                    if child_iter:
                        task(child_iter)
            while iter:
                task(iter)
                iter = self.model.iter_next(iter)
        finally:
            if fcache_save_lock.locked():
                fcache_save_lock.release()

    @idle_task
    def restore_rows(self, rows):
        for key in sorted(rows.keys()):
            if len(key) == 1:
                self.model.append(None, rows[key])
            else:
                str_path = str(key).replace(', ',':')
                parent_path = str_path[1:str_path.rfind(':')]
                parent_iter = self.model.get_iter_from_string(parent_path)
                self.model.append(parent_iter, rows[key])


    def find_rows_by_element(self, element, value):
        '''element - member of FTreeModel class
        for example self.UUID)'''

        result = []

        def task(row):
            if row[element[0]] == value:
                result.append(row)
            if row.iterchildren():
                for child_row in row.iterchildren():
                    task(child_row)

        for row in self.model:
            task(row)

        return result

    def clear_tree(self):
        self.model.clear()

    def on_button_press(self, w, e):
        pass

    def on_key_release(self, w, e):
        pass

    def delete_selected(self):
        selection = self.get_selection()
        fm, paths = selection.get_selected_rows()#@UnusedVariable
        paths.reverse()
        for path in paths:
            path = self.filter_model.convert_path_to_child_path(path)
            iter = self.model.get_iter(path)
            self.model.remove(iter)

        if len(paths) == 1:
            path = paths[0]
            logging.debug("path " + repr(path))
            position = path[0]
            if path[0]:
                selection.select_path(position - 1)
            else:
                selection.select_path(position)

    def get_selected_bean_paths(self):
        selection = self.get_selection()
        if not selection:
            return None
        model, paths = selection.get_selected_rows()#@UnusedVariable
        if not paths:
            return None
        return paths


    def get_selected_bean(self):
        paths = self.get_selected_bean_paths()
        if not paths:
            return None
        selected_bean = self._get_bean_by_path(paths[0])

        return selected_bean

    def get_selected_beans(self):
        paths = self.get_selected_bean_paths()
        if not paths:
            return None

        beans = [self._get_bean_by_path(path) for path in paths]

        return beans

    def get_selected_or_current_bean(self):
        bean = self.get_selected_bean()
        if bean:
            return bean
        else:
            return self.get_current_bean_by_UUID()

    @idle_task
    def set_play_icon_to_bean_to_selected(self):
        for row in self.model:
            row[self.play_icon[0]] = ''

        paths = self.get_selected_bean_paths()
        if not paths:
            return None
        logging.debug("Set play icon to selected bean")
        path = paths[0]
        iter = self.model.get_iter(path)
        self.model.set_value(iter, FTreeModel().play_icon[0], "go-next")
        self.active_UUID = self.model.get_value(iter, FTreeModel().UUID[0])

    @idle_task
    def set_bean_column_value(self, bean, colum_num, value):
        for row in self.model:
            if row[self.UUID[0]] == bean.UUID:
                row[colum_num] = value
                break

    def update_bean(self, bean):
        for row in self.model:
            if row[self.UUID[0]] == bean.UUID:
                dict = FTreeModel().__dict__
                for key in dict:
                    value = getattr(bean, key)
                    if value is None:
                        value = ''
                    row_num = dict[key][0]
                    row[row_num] = value
                break

    def _get_bean_by_path(self, path):
        model = self.model
        path = self.filter_model.convert_path_to_child_path(path)
        iter = model.get_iter(path)

        if iter:
            bean = FModel()
            dt = FTreeModel().__dict__
            for key in dt.keys():
                setattr(bean, key, model.get_value(iter, dt[key][0]))
            return bean
        return None

    def get_bean_by_UUID(self, UUID):
        for row in self.model:
            if row[self.UUID[0]] == UUID:
                return self.get_bean_from_row(row)

    def get_current_bean_by_UUID(self):
        UUID = self.active_UUID
        for row in self.model:
            if row[self.UUID[0]] == UUID:
                return self.get_bean_from_row(row)

        return None

    @idle_task
    def set_play_icon_to_bean(self, bean):
        logging.debug("Set play icon to bean")
        for row in self.model:
            if row[self.UUID[0]] == bean.UUID:
                row[self.play_icon[0]] = "go-next"
                self.active_UUID = bean.UUID
            else:
                row[self.play_icon[0]] = ""

    def get_next_bean_by_UUID(self, repeat_all=False):
        '''not correct method after rebuild beans'''
        UUID = self.active_UUID
        rows = self.get_all_file_rows()
        for i, row in enumerate(rows):
            if row[self.UUID[0]] == UUID and i + 1 < len(rows):
                next_row = rows[i + 1]
                if next_row:
                    return self.get_bean_from_row(next_row)

        if repeat_all:
            return self.get_bean_from_row(rows[0])

    def get_prev_bean_by_UUID(self, repeat_all=False):
        '''not correct method after rebuild beans'''
        UUID = self.active_UUID
        rows = self.get_all_file_rows()

        for i, row in enumerate(rows):
            if row[self.UUID[0]] == UUID and i > 0:
                prev_row = rows[i - 1]
                if prev_row:
                    return self.get_bean_from_row(prev_row)

        if repeat_all:
            return self.get_bean_from_row(rows[len(rows) - 1])

    def get_next_bean(self, repeat_all=False):
        rows = self.get_all_file_rows()
        if not rows:
            return
        for i, row in enumerate(rows):
            if row[self.play_icon[0]] and i + 1 < len(rows):
                next_row = rows[i + 1]
                if next_row:
                    return self.get_bean_from_row(next_row)

        if repeat_all:
            return self.get_bean_from_row(rows[0])

    def get_prev_bean(self, repeat_all=False):
        rows = self.get_all_file_rows()
        if not rows:
            return
        for i, row in enumerate(rows):
            if row[self.play_icon[0]] and i > 0:
                prev_row = rows[i - 1]
                if prev_row:
                    return self.get_bean_from_row(prev_row)

        if repeat_all:
            return self.get_bean_from_row(rows[len(rows) - 1])

    def get_all_file_rows(self):
        rows = [row for row in self.model if row[self.is_file[0]]]
        return rows

    def get_random_bean(self):
        rows = self.get_all_file_rows()
        return self.get_bean_from_row(rows[randint(0, len(rows) - 1)])

    def get_child_level1_beans_by_selected(self):
        selection = self.get_selection()
        model, paths = selection.get_selected_rows()
        selected = model.get_iter(paths[0])
        n = model.iter_n_children(selected)
        iterch = model.iter_children(selected)

        results = []

        for i in xrange(n):#@UnusedVariable
            path = model.get_path(iterch)
            bean = self._get_bean_by_path(path)
            results.append(bean)
            iterch = model.iter_next(iterch)

        return results

    def get_all_child_beans_by_selected(self):
            model, paths = self.get_selection().get_selected_rows()
            #to_path = model.convert_path_to_child_path(paths[0])
            if model and paths:
                iter = model.get_iter(paths[0])
                return self.get_child_beans_by_parent(model, iter)
            return None

    def get_all_beans(self):
        results = []
        next = self.model.get_iter_first()
        if next:
            parent = self.get_bean_from_iter(next)
            results += [parent] + self.get_child_beans_by_parent(self.model, next)
        else:
            return None

        flag = True

        while flag:
            next = self.model.iter_next(next)
            if not next:
                flag = False
            else:
                parent = self.get_bean_from_iter(next)
                results += [parent] + self.get_child_beans_by_parent(self.model, next)

        return results

    def get_all_beans_text(self):
        result = []
        beans = self.get_all_beans()

        if not beans:
            return result

        for bean in beans:
            result.append(bean.text)

        return result

    def get_all_selected_beans(self):
        selection = self.get_selection()
        model, paths = selection.get_selected_rows()#@UnusedVariable
        if not paths:
            return None
        beans = []
        for path in paths:
            selection.select_path(path)
            bean = self._get_bean_by_path(path)
            beans.append(bean)
        return beans

    @idle_task
    def restore_selection(self, str_paths):
        selection = self.get_selection()
        for str_path in str_paths:
            iter = self.model.get_iter_from_string(str_path)
            path = self.model.get_path(iter)
            selection.select_path(path)

    @idle_task
    def restore_expand(self, str_paths):
        for str_path in str_paths:
            iter = self.model.get_iter_from_string(str_path)
            path = self.model.get_path(iter)
            self.expand_to_path(path)

    def copy_info_to_clipboard(self, mode=False):
        beans = self.get_selected_beans()
        if not beans:
            return
        clb = Gtk.Clipboard.get(Gdk.SELECTION_CLIPBOARD)
        if not mode:
            tracks = [b.tracknumber + ". " + b.title + " (" + b.time + ")"
                      if (b.tracknumber and b.title and b.time) else b.text for b in beans]
        else:
            tracks = []
            for bean in beans:
                artist = bean.artist if bean.artist else "Unknown artist"
                title = bean.title if bean.title else "Unknown title"
                album = bean.album if bean.album else "Unknown album"
                tracks.append(artist + " - " + title + " (" + album + ")")

        clb.set_text("\n".join(tracks), -1)


    def selection_changed(self, callback):
        def on_selection_changed(w):
            paths = self.get_selected_bean_paths()
            if paths:
                callback([str(path) for path in paths])
        selection = self.get_selection()
        if selection:
            selection.connect("changed", on_selection_changed)

    def expand_updated(self, callback):
        def on_expand_collapse(w, iter, path):
            values = []
            self.map_expanded_rows(lambda w, path, data: values.append(str(path)), None)
            callback(values)
        self.connect("row-expanded", on_expand_collapse)
        self.connect("row-collapsed", on_expand_collapse)

    def is_empty(self):
        if not self.get_model().get_model().get_iter_first():
            return True
        else:
            return False

class MyTreeStore(Gtk.TreeStore):
    def __init__(self, *types):
        Gtk.TreeStore.__init__(self, *types)

    def _convert_value(self, column, value):
        if value is None:
            return None

        # we may need to convert to a basic type
        type_ = self.get_column_type(column)
        if type_ == GObject.TYPE_STRING:
            if isinstance(value, str):
                value = str(value)
            elif sys.version_info < (3, 0):
                if isinstance(value, unicode):
                    value = value.encode('UTF-8')
                else:
                    raise ValueError('Expected string or unicode for column %i but got %s%s' % (column, value, type(value)))
            else:
                raise ValueError('Expected a string for column %i but got %s' % (column, type(value)))
        elif type_ == GObject.TYPE_FLOAT or type_ == GObject.TYPE_DOUBLE:
            if isinstance(value, float):
                value = float(value)
            else:
                raise ValueError('Expected a float for column %i but got %s' % (column, type(value)))
        elif type_ == GObject.TYPE_LONG or type_ == GObject.TYPE_INT:
            if isinstance(value, int):
                value = int(value)
            elif sys.version_info < (3, 0):
                if isinstance(value, long):
                    value = long(value)
                else:
                    try:
                        value = long(value)
                    except ValueError:
                        raise ValueError('Expected an long for column %i but got %s' % (column, type(value)))
            else:
                try:
                    value = long(value)
                except ValueError:
                    raise ValueError('Expected an integer for column %i but got %s' % (column, type(value)))
        elif type_ == GObject.TYPE_BOOLEAN:
            cmp_classes = [int]
            if sys.version_info < (3, 0):
                cmp_classes.append(long)

            if isinstance(value, tuple(cmp_classes)):
                value = bool(value)
            else:
                raise ValueError('Expected a bool for column %i but got %s' % (column, type(value)))
        else:
            # use GValues directly to marshal to the correct type
            # standard object checks should take care of validation
            # so we don't have to do it here
            value_container = GObject.Value()
            value_container.init(type_)
            if type_ == GObject.TYPE_CHAR:
                value_container.set_char(value)
                value = value_container
            elif type_ == GObject.TYPE_UCHAR:
                value_container.set_uchar(value)
                value = value_container
            elif type_ == GObject.TYPE_UNICHAR:
                cmp_classes = [str]
                if sys.version_info < (3, 0):
                    cmp_classes.append(unicode)

                if isinstance(value, tuple(cmp_classes)):
                    value = ord(value[0])

                value_container.set_uint(value)
                value = value_container
            elif type_ == GObject.TYPE_UINT:
                value_container.set_uint(value)
                value = value_container
            elif type_ == GObject.TYPE_ULONG:
                value_container.set_ulong(value)
                value = value_container
            elif type_ == GObject.TYPE_INT64:
                value_container.set_int64(value)
                value = value_container
            elif type_ == GObject.TYPE_UINT64:
                value_container.set_uint64(value)
                value = value_container
            elif type_ == GObject.TYPE_PYOBJECT:
                value_container.set_boxed(value)
                value = value_container

        return value
########NEW FILE########
__FILENAME__ = dm_nav_tree
'''
Created on Oct 27, 2010

@author: ivan
'''
from foobnix.gui.treeview.simple_tree import SimpleTreeControl
from foobnix.util.const import DOWNLOAD_STATUS_ALL
from foobnix.gui.model import FTreeModel
from foobnix.util.mouse_utils import is_double_left_click, is_empty_click
class DMNavigationTreeControl(SimpleTreeControl):
    def __init__(self):
        SimpleTreeControl.__init__(self, None, None)
        self.dm_list = None
    
    def on_button_press(self, w, e):
        if is_empty_click(w,e):
            w.get_selection().unselect_all()
        if is_double_left_click(e):
            active = self.get_selected_bean()
            if active:
                if active.get_status() == DOWNLOAD_STATUS_ALL:
                    self.dm_list.filter_by_file(None, FTreeModel().status[0])
                else:
                    self.dm_list.filter_by_file(active.get_status(), FTreeModel().status[0])
    def use_filter(self):
        active = self.get_selected_bean()
        if active:
            if active.get_status() == DOWNLOAD_STATUS_ALL:
                self.dm_list.filter_by_file(None, FTreeModel().status[0])
            else:
                self.dm_list.filter_by_file(active.get_status(), FTreeModel().status[0])
    
    """statistics in {DOWNLOAD_TYPE:count}"""
    def update_statistics(self):
        statisctics = self.dm_list.get_status_statisctics()  
        all = self.get_all_beans()
        for bean in all:
            status = bean.get_status()
            num = 0
            if status in statisctics:
                num = statisctics[status]
            value = bean.artist + " (%s)" % num
            self.set_bean_column_value(bean, FTreeModel().text[0], value)
        
    def on_load(self):
        pass
    
    def on_save(self):
        pass

########NEW FILE########
__FILENAME__ = dm_tree
'''
Created on Oct 27, 2010

@author: ivan
'''

import logging

from gi.repository import Gtk
from gi.repository import GObject

from foobnix.util import idle_task
from foobnix.fc.fc import FC
from foobnix.helpers.menu import Popup
from foobnix.gui.model import FTreeModel
from foobnix.util.file_utils import open_in_filemanager
from foobnix.gui.treeview.common_tree import CommonTreeControl
from foobnix.util.const import DOWNLOAD_STATUS_ALL, DOWNLOAD_STATUS_ACTIVE, \
    DOWNLOAD_STATUS_LOCK
from foobnix.util.mouse_utils import is_rigth_click,\
    right_click_optimization_for_trees, is_empty_click


class DownloadManagerTreeControl(CommonTreeControl):
    def __init__(self, navigation):
        self.navigation = navigation
        CommonTreeControl.__init__(self, None)
        self.set_reorderable(False)
        self.set_headers_visible(True)

        self.tree_menu = Popup()

        """column config"""
        column = Gtk.TreeViewColumn("Name", Gtk.CellRendererText(), text=self.text[0])
        column.set_resizable(True)
        self.append_column(column)
        
        """column config"""
        column = Gtk.TreeViewColumn("Progress", Gtk.CellRendererProgress(), text=self.persent[0], value=self.persent[0])
        column.set_resizable(True)
        self.append_column(column)
        
        """column config"""
        column = Gtk.TreeViewColumn("Size", Gtk.CellRendererText(), text=self.size[0])
        column.set_resizable(True)
        self.append_column(column)
        
        """status"""
        column = Gtk.TreeViewColumn("Status", Gtk.CellRendererText(), text=self.status[0])
        column.set_resizable(True)
        self.append_column(column)
        
        """column config"""
        column = Gtk.TreeViewColumn("Path", Gtk.CellRendererText(), text=self.save_to[0])
        column.set_resizable(True)
        column.set_expand(True)
        self.append_column(column)

        self.set_type_plain()

    @idle_task
    def delete_all(self):
        self.clear()

    @idle_task
    def delete_all_selected(self):
        self.delete_selected()

    @idle_task
    def update_status_for_selected(self, status):
        beans = self.get_all_selected_beans()
        for bean in beans:
            self.set_bean_column_value(bean, FTreeModel().status[0], status)

    @idle_task
    def update_status_for_all(self, status):
        beans = self.get_all_beans()
        for bean in beans:
            self.set_bean_column_value(bean, FTreeModel().status[0], status)

    @idle_task
    def update_status_for_beans(self, beans, status):
        for bean in beans:
            self.set_bean_column_value(bean, FTreeModel().status[0], status)

    def get_next_bean_to_dowload(self):
        all = self.get_all_beans()
        if not all:
            return None
        for bean in all:
            if bean.get_status() == DOWNLOAD_STATUS_ACTIVE:
                self.set_bean_column_value(bean, FTreeModel().status[0], DOWNLOAD_STATUS_LOCK)
                return bean

    @idle_task
    def update_bean_info(self, bean):
        self.update_bean(bean)
        self.navigation.update_statistics()
        #self.navigation.use_filter()
    
    def on_button_press(self, w, e):
        logging.debug("on dm button press")
        if is_empty_click(w, e):
            w.get_selection().unselect_all()
        if is_rigth_click(e):
            right_click_optimization_for_trees(w, e)
            try:
                self.tree_menu.clear()
                if self.get_selected_bean():
                    self.tree_menu.add_item(_("Open in file manager"), None, open_in_filemanager, self.get_selected_bean().path)
                else:
                    self.tree_menu.add_item(_("Open in file manager"), None, open_in_filemanager, FC().online_save_to_folder)
                self.tree_menu.show(e)
            except Exception, e:
                logging.error(e)

    def get_status_statisctics(self):
        all_beans = self.get_all_beans()
        if not all_beans:
            return {}
        results = {DOWNLOAD_STATUS_ALL: len(all_beans)}
        for bean in all_beans:
            status = bean.get_status()
            if status in results:
                results[status] += 1
            else:
                results[status] = 1
        return results

########NEW FILE########
__FILENAME__ = dragdrop_tree
'''
Created on Oct 14, 2010

@author: ivan
'''

from gi.repository import Gdk
from gi.repository import GLib
from gi.repository import Gtk

import copy
import thread
import logging
import os.path
import threading
import collections

from foobnix.gui.model import FModel, FTreeModel, FDModel
from foobnix.util.file_utils import get_file_extension, is_m3u
from foobnix.util.id3_file import update_id3_wind_filtering
from foobnix.util.iso_util import get_beans_from_iso_wv
from foobnix.util import idle_task_priority, idle_task

try:
    from gi.repository.GLib import GError
except ImportError as e:
    try:
        from gi._glib import GError
    except ImportError as e:
        from gi._glib._glib import GError

VIEW_PLAIN = 0
VIEW_TREE = 1

class DragDropTree(Gtk.TreeView):
    def __init__(self, controls):
        self.controls = controls
        Gtk.TreeView.__init__(self)

        self.connect("drag-begin", self.on_drag_begin)
        self.connect("drag-data-get", self.on_drag_data_get)
        self.connect("drag-data-received", self.on_drag_data_received)
        self.connect("drag-drop", self.on_drag_drop)
        self.connect("drag-motion", self.on_drag_motion)
        self.connect('drag-leave', self.on_drag_leave)
        self.connect('drag-end', self.on_drag_end)

        """init values"""
        self.hash = {None: None}
        self.current_view = None
        self.filling_lock = threading.Lock()

    def on_drag_data_get(self, source_tree, drag_context, selection, info, time):
        pass

    def on_drag_end(self, *a):
        pass

    def on_drag_data_received(self, treeview, context, x, y, selection, info, timestamp):
        self.stop_emission('drag-data-received')

    def on_drag_begin(self, source_widget, drag_context):
        ff_model, ff_paths = source_widget.get_selection().get_selected_rows()  # @UnusedVariable
        if len(ff_paths) > 1:
            self.drag_source_set_icon_stock('gtk-dnd-multiple')
        else:
            self.drag_source_set_icon_stock('gtk-dnd')

    def on_drag_motion(self, widget, drag_context, x, y, time):
        Gdk.drag_status(drag_context, Gdk.DragAction.COPY, time)
        widget.drag_highlight()
        drop_info = widget.get_dest_row_at_pos(x, y)
        if drop_info:
            self.set_drag_dest_row(*drop_info)

    def on_drag_leave(self, widget, context, time):
        widget.drag_unhighlight()

    def configure_recive_drag(self):
        self.enable_model_drag_dest([("text/uri-list", 0, 0)], Gdk.DragAction.COPY | Gdk.DragAction.MOVE) # @UndefinedVariable
        self.drag_dest_add_text_targets()

    def configure_send_drag(self):
        self.drag_source_set(Gdk.ModifierType.BUTTON1_MASK, [Gtk.TargetEntry.new("text/uri-list", 0, 0)], Gdk.DragAction.COPY | Gdk.DragAction.MOVE) #@UndefinedVariable
        self.drag_source_add_text_targets()

    def append_all(self, beans):
        logging.debug("begin append all")
        if self.current_view == VIEW_PLAIN:
            self.plain_append_all(beans)
        else:
            self.tree_append_all(beans)

    def simple_append_all(self, beans):
        logging.debug("simple_append_all")

        if self.current_view == VIEW_PLAIN:
            for bean in beans:
                row = self.get_row_from_bean(bean)
                self.model.append(None, row)
            if "PlaylistTreeControl" in str(self):
                thread.start_new_thread(self.controls.notetabs.on_save_tabs, ())
        else:
            self.tree_append_all(beans)

    def append(self, bean):
        if self.current_view == VIEW_PLAIN:
            self.plain_append_all([bean])
        else:
            self.tree_append(bean)

    def set_type_plain(self):
        self.current_view = VIEW_PLAIN

    def set_type_tree(self):
        self.current_view = VIEW_TREE

    def get_bean_from_model_iter(self, model, iter):
        if not model or not iter:
            return None
        bean = FModel()
        id_dict = FTreeModel().cut().__dict__
        for key in id_dict.keys():
            num = id_dict[key]
            try:
                val = model.get_value(iter, num)
            except GError:
                val = None
            setattr(bean, key, val)
        return bean

    def on_drag_drop(self, to_tree, context, x, y, time):
        to_tree.drag_get_data(context, context.list_targets()[-1], time)
        return True

    def remove_replaced(self, model, rowrefs):
        for ref in rowrefs:
            iter = self.get_iter_from_row_reference(ref)
            iter = model.convert_iter_to_child_iter(iter)
            model.get_model().remove(iter)

    def child_by_recursion(self, row, plain):
        for child in row.iterchildren():
            plain.append(child)
            self.child_by_recursion(child, plain)

    def rebuild_as_tree(self, *a):
        self.current_view = VIEW_TREE
        plain = []
        for row in self.model:
            plain.append(row)
            self.child_by_recursion(row, plain)

        copy_beans = []
        for row in plain:
            bean = self.get_bean_from_row(row)
            copy_beans.append(bean)

        self.clear_tree()

        self.tree_append_all(copy_beans)

        self.expand_all()

    def rebuild_as_plain(self, with_beans=True):
        self.current_view = VIEW_PLAIN
        if len(self.model) == 0:
            return
        plain = []
        for row in self.model:
            plain.append(row)
            self.child_by_recursion(row, plain)
        if not with_beans:
            for row in plain:
                self.model.append(None, row)
            return
        copy_beans = []
        for row in plain:
            bean = self.get_bean_from_row(row)
            copy_beans.append(bean)

        self.clear_tree()
        self.plain_append_all(copy_beans)

    @idle_task
    def tree_append_all(self, beans):
        self._tree_append_all(beans)

    def _tree_append_all(self, beans):
        if not beans:
            return None
        self.current_view = VIEW_TREE
        logging.debug("append all as tree")

        for bean in beans:
            self.tree_append(bean)

    def get_iter_from_bean(self, bean):
        for row in self.model:
            if row[self.UUID[0]] == bean.UUID:
                return row.iter
        return None

    def remove_iters(self, allIters):
        for iter in allIters:
            self.model.remove(iter)

    def get_child_iters_by_parent(self, model, iter):
        list = []
        if model.iter_has_child(iter):
            for i in xrange(model.iter_n_children(iter)):
                next_iter = model.iter_nth_child(iter, i)

                list.append(next_iter)

                iters = self.get_child_beans_by_parent(model, next_iter)

                for iter in iters:
                    list.append(iter)

        return list

    def get_child_beans_by_parent(self, model, iter):
        list = []

        def add_to_list(beans):
            for i, bean in enumerate(beans):
                if i: bean.parent(parent)
                if bean.path and bean.path.lower().endswith(".iso.wv"):
                    add_to_list(get_beans_from_iso_wv(bean.path))
                else:
                    list.append(bean)

        if model.iter_has_child(iter):
            for i in xrange(model.iter_n_children(iter)):
                next_iter = model.iter_nth_child(iter, i)

                parent = self.get_bean_from_model_iter(model, next_iter)
                add_to_list([parent])

                beans = self.get_child_beans_by_parent(model, next_iter)
                add_to_list(beans)

        return list

    @idle_task
    def plain_append_all(self, beans, parent=None):
        try:
            self._plain_append_all(beans, parent)
        finally:
            if "PlaylistTreeControl" in str(self):
                thread.start_new_thread(self.controls.notetabs.on_save_tabs, ())

    def _plain_append_all(self, beans, parent=None):
        logging.debug("begin plain append all")
        if not beans:
            return

        parent_iter = None
        if parent:
            parent_iter = self.get_iter_from_bean(parent)

        self.current_view = VIEW_PLAIN

        normalized = []
        for model in beans:
            if model.path and model.path.lower().endswith(".iso.wv"):
                logging.debug("begin normalize iso.wv" + str(model.path))
                all = get_beans_from_iso_wv(model.path)

                if not all:
                    break
                for inner in all:
                    normalized.append(inner)
            else:
                normalized.append(model)

        beans = normalized

        #counter = 0
        for bean in beans:
            """if not bean.path or not get_file_extension(bean.path) == ".cue":
                if bean.is_file and FC().numbering_by_order:
                    counter += 1
                    bean.tracknumber = counter
                else:
                    counter = 0
            """
            self._plain_append(bean, parent_iter)

    def _plain_append(self, bean, parent_iter):
        logging.debug("Plain append task: " + str(bean.text) + " " + str(bean.path))
        if not bean:
            return

        if bean.is_file:
            bean.font = "normal"
        else:
            bean.font = "bold"

        bean.visible = True
        beans = update_id3_wind_filtering([bean])
        for one in beans:
            one.update_uuid()
            row = self.get_row_from_bean(one)

            self.model.append(parent_iter, row)

    def tree_append(self, bean):
        if not bean:
            return
        if bean.is_file:
            bean.font = "normal"
        else:
            bean.font = "bold"

        """copy beans"""
        bean = copy.copy(bean)
        bean.visible = True

        last_folder_iter = None

        row = self.get_row_from_bean(bean)

        if self.hash.has_key(bean.get_parent()):
            parent_iter_exists = self.hash[bean.get_parent()]
            if not bean.is_file:
                for i in xrange(self.model.iter_n_children(parent_iter_exists)):
                    iter = self.model.iter_nth_child(parent_iter_exists, i)
                    if not self.model.get_value(iter, self.is_file[0]):
                        last_folder_iter = iter
                if last_folder_iter:
                    new_iter = self.model.insert_after(None, last_folder_iter, row)
                    self.hash[bean.level] = new_iter
                    return
                else:
                    new_iter = self.model.prepend(parent_iter_exists, row)
                    self.hash[bean.level] = new_iter
                    return
        else:
            parent_iter_exists = None

        parent_iter = self.model.append(parent_iter_exists, row)
        self.hash[bean.level] = parent_iter

    def tree_insert_row(self, row):
        last_folder_iter = None

        if self.hash.has_key(row[self.parent_level[0]]):
            parent_iter_exists = self.hash[row[self.parent_level[0]]]
            if not row[self.is_file[0]]:
                for i in xrange(self.model.iter_n_children(parent_iter_exists)):
                    iter = self.model.iter_nth_child(parent_iter_exists, i)
                    if not self.model.get_value(iter, self.is_file[0]):
                        last_folder_iter = iter

                if last_folder_iter:
                    new_iter = self.model.insert_after(None, last_folder_iter, row)
                    self.hash[row[self.level[0]]] = new_iter
                    return
                else:
                    new_iter = self.model.prepend(parent_iter_exists, row)
                    self.hash[row[self.level[0]]] = new_iter
                    return
        else:
            parent_iter_exists = None

        parent_iter = self.model.append(parent_iter_exists, row)
        self.hash[row[self.level[0]]] = parent_iter



    def get_row_from_iter(self, model, iter):
        row = []
        for num in xrange(model.get_n_columns()):
            try:
                val = model.get_value(iter, num)
            except GError:
                val = None
            row.append(val)
        return row

    def get_list_of_iters_with_children(self, model, iter):
        all_iters = []
        def task(iter):
            all_iters.append(iter)
            for n in xrange(model.iter_n_children(iter)):
                child_iter = model.iter_nth_child(iter, n)
                if child_iter:
                    task(child_iter)
        task(iter)
        return all_iters

    def get_list_of_paths_with_children(self, model, iter):
        all_paths = []
        def task(iter):
            path = model.get_path(iter)
            all_paths.append(path)
            for n in xrange(model.iter_n_children(iter)):
                child_iter = model.iter_nth_child(iter, n)
                if child_iter:
                    task(child_iter)
        task(iter)
        return all_paths

    def fill_treerows(self):
        all_extra_rows = {}

        for k, treerow in enumerate(self.model):
            if not treerow[self.time[0]] and treerow[self.is_file[0]]:
                bean = self.get_bean_from_row(treerow)
                full_beans = update_id3_wind_filtering([bean])
                rows_for_add = []
                if len(full_beans) == 1:
                    full_bean = full_beans[0]
                    m_dict = FTreeModel().cut().__dict__
                    new_dict = dict(zip(m_dict.values(), m_dict.keys()))
                    for i, key in enumerate(new_dict.values()):
                        value = getattr(full_bean, key)
                        if value is None:
                            value = ''
                        elif type(value) in [int, float, long]:
                            value = str(value)
                        treerow[i] = value
                else:
                    for n, full_bean in enumerate(full_beans):
                        full_bean.visible = True
                        full_bean.update_uuid()
                        row = self.get_row_from_bean(full_bean)
                        rows_for_add.insert(0, row)
                        if n == 0:
                            treerow[self.font[0]] = 'bold'
                            treerow[self.is_file[0]] = False

                    if rows_for_add:
                        all_extra_rows[k] = rows_for_add

        if all_extra_rows:
            for i in sorted(all_extra_rows.keys(), reverse = True):
                for row in all_extra_rows[i]:
                    self.model.insert_after(None, self.model.get_iter(i), row)

    def safe_fill_treerows(self):
        try:
            self.filling_lock.acquire()

            rows = collections.OrderedDict()
            for treerow in self.model:
                rows[Gtk.TreeRowReference.new(self.model, treerow.path)] = [col for col in treerow]
            for row_ref in rows.keys():
                row = rows[row_ref]
                if not row[self.time[0]] and row[self.is_file[0]] and row_ref.valid():
                    bean = self.get_bean_from_row(row)
                    beans = update_id3_wind_filtering([bean])
                    if len(beans) == 1:
                        self.fill_row(row_ref, beans[:][0])
                    else:
                        bean = FDModel(text=_('Playlist: ') + os.path.basename(bean.path)).add_font("bold").add_is_file(False)
                        self.fill_row(row_ref, bean)
                        beans.reverse()
                        for b in beans[:]:
                            self.insert_bean(row_ref, b)
        finally:
            #self.update_tracknumber()
            self.controls.notetabs.on_save_tabs()
            if self.filling_lock.locked():
                self.filling_lock.release()

    @idle_task_priority(GLib.PRIORITY_LOW)
    def fill_row(self, row_ref, bean):
            if row_ref.valid():
                treerow = self.model[row_ref.get_path()]
                m_dict = FTreeModel().cut().__dict__
                new_dict = dict(zip(m_dict.values(), m_dict.keys()))
                for i, key in enumerate(new_dict.values()):
                    value = getattr(bean, key)
                    if value is None:
                        value = ''
                    elif type(value) in [int, float, long]:
                        value = str(value)
                    if i != self.play_icon[0]:
                        treerow[i] = value

    @idle_task_priority(GLib.PRIORITY_LOW)
    def insert_bean(self, row_ref, bean):
        if row_ref.valid():
            row = self.get_row_from_bean(bean)
            iter = self.model.insert_after(None, self.get_iter_from_row_reference(row_ref), row)
            self.fill_row(self.get_row_reference_from_iter(self.model, iter), bean)
    '''
    @idle_task_priority(GLib.PRIORITY_LOW + 1)
    def update_tracknumber(self):
        try:
            self.current_view = VIEW_PLAIN
            tn = self.tracknumber[0]
            isfile = self.is_file[0]
            counter = 0
            for row in self.model:
                if row[isfile] and FC().numbering_by_order:
                    counter += 1
                else:
                    counter = 0
                row[tn] = str(counter) if counter else ''
        finally:
            self.controls.notetabs.on_save_tabs()
            if self.filling_lock.locked():
                self.filling_lock.release()
    '''

    def playlist_filter(self, rows):
        checked_cue_rows = []
        checked_m3u_rows = []
        m3u_rows_for_delete = []

        def task(rows):
            for row in rows:
                index = self.path[0]
                path = row[index]
                if path and (is_m3u(path)
                             and row not in checked_m3u_rows):
                    checked_m3u_rows.append(row)
                    for r in rows:
                        if (os.path.dirname(r[index]) == os.path.dirname(path) and os.path.isfile(r[index])
                            and not is_m3u(r[index])):
                                m3u_rows_for_delete.append(r)
                                break
                    return task(rows)

                if path and (get_file_extension(path) == ".cue"
                             and row not in checked_cue_rows):

                    checked_cue_rows.append(row)
                    filtered_rows = [r for r in rows if (os.path.dirname(r[index]) != os.path.dirname(path)
                                                           or os.path.isdir(r[index])
                                                           or get_file_extension(r[index]) == ".cue")]
                    return task(filtered_rows)
            return rows

        all_filtered_rows = task(rows)

        return [row for row in all_filtered_rows
                if row not in m3u_rows_for_delete] if m3u_rows_for_delete else all_filtered_rows
########NEW FILE########
__FILENAME__ = filter_tree
#-*- coding: utf-8 -*-
'''
Created on 7 нояб. 2010

@author: ivan
'''

from foobnix.gui.model import FTreeModel
from foobnix.gui.treeview.dragdrop_tree import DragDropTree

class FilterTreeControls(DragDropTree):
    def __init__(self, controls):
        DragDropTree.__init__(self, controls)

    def show_all_lines(self):
        def req(line):
                for child in line.iterchildren():
                    child[self.visible[0]] = True
                    req(child)

        for line in self.model:
            line[self.visible[0]] = True
            req(line)

    def is_query_in_file_line(self, query, parent, column_num):
        find = False

        for child in parent.iterchildren():

            column_text = child[column_num].decode().lower().strip()

            if not child[self.is_file[0]]:
                """folder"""
                if self.is_query_in_file_line(query, child, column_num):
                    find = True
            else:
                """file"""
                if query in column_text:
                    child[self.visible[0]] = True
                    find = True
                else:
                    child[self.visible[0]] = False

        if not parent[self.is_file[0]]:
            parent[self.visible[0]] = find

        return find

    def is_query_in_folder_line(self, query, parent, column_num):
        find = False

        for child in parent.iterchildren():

            column_text = child[column_num].decode().lower().strip()

            if not child[self.is_file[0]]:
                if query in column_text:
                    find = True
                elif self.is_query_in_folder_line(query, child, column_num):
                    find = True
            else:
                """file"""
                if query in column_text:
                    find = True

        parent[self.visible[0]] = find

        return find

    def file_filter(self, query, column_num):
        for parent in self.model:
            if parent[self.is_file[0]]:
                column_text = parent[column_num].decode().lower().strip()
                if query not in column_text:
                    parent[self.visible[0]] = False
            else:
                self.is_query_in_file_line(query, parent, column_num)

    def folder_filter(self, query, column_num):
        for parent in self.model:
            if not parent[self.is_file[0]]:
                column_text = parent[column_num].decode().lower().strip()
                if query not in column_text:
                    self.is_query_in_folder_line(query, parent, column_num)

    def filter_by_file(self, query, column_num=FTreeModel().text[0]):
        self.show_all_lines()

        if query and len(query.strip()) > 0:
            query = query.decode().strip().lower()
            self.file_filter(query, column_num)
            self.expand_all()
        else:
            self.collapse_all()

    def filter_by_folder(self, query, column_num=FTreeModel().text[0], expand=True):
        self.show_all_lines()

        if query and len(query.strip()) > 0:
            query = query.decode().strip().lower()
            self.folder_filter(query, column_num)
            if expand:
                self.expand_all()
        else:
            self.collapse_all()

########NEW FILE########
__FILENAME__ = lastfm_integration_tree
'''
Created on Jan 27, 2011

@author: ivan
'''

import logging

from gi.repository import Gtk
from gi.repository import GLib

from foobnix.fc.fc import FC
from foobnix.fc.fc_base import FCBase
from foobnix.helpers.menu import Popup
from foobnix.gui.model import FModel, FDModel
from foobnix.util.mouse_utils import is_rigth_click,\
    right_click_optimization_for_trees, is_empty_click
from foobnix.util.bean_utils import update_parent_for_beans
from foobnix.gui.treeview.common_tree import CommonTreeControl


class LastFmIntegrationControls(CommonTreeControl):
    def __init__(self, controls):
        CommonTreeControl.__init__(self, controls)

        """column config"""
        column = Gtk.TreeViewColumn(_("Lasm.fm Integration ") + FCBase().lfm_login,
                                    Gtk.CellRendererText(), text=self.text[0], font=self.font[0])
        column.set_resizable(True)
        self.set_headers_visible(True)
        self.append_column(column)

        self.tree_menu = Popup()

        self.configure_send_drag()
        self.configure_recive_drag()

        self.set_type_tree()

        self.services = {_("My recommendations"):   self.controls.lastfm_service.get_recommended_artists,
                         _("My loved tracks"):      self.controls.lastfm_service.get_loved_tracks,
                         _("My top tracks"):        self.controls.lastfm_service.get_top_tracks,
                         _("My recent tracks"):     self.controls.lastfm_service.get_recent_tracks,
                         _("My top artists"):       self.controls.lastfm_service.get_top_artists,
                         #_("My friends"):self.controls.lastfm_service.get_friends,
                         # #_("My neighbours"):self.controls.lastfm_service.get_neighbours
                         }

        for name in self.services:
            parent = FModel(name)
            bean = FDModel(_("loading...")).parent(parent).add_is_file(True)
            self.append(parent)
            self.append(bean)

    def on_button_press(self, w, e):
        if is_empty_click(w, e):
            w.get_selection().unselect_all()
        if is_rigth_click(e):
            right_click_optimization_for_trees(w, e)
            active = self.get_selected_bean()
            self.tree_menu.clear()
            self.tree_menu.add_item(_('Play'), Gtk.STOCK_MEDIA_PLAY, self.controls.play, active)
            self.tree_menu.add_item(_('Copy to Search Line'), Gtk.STOCK_COPY,
                                    self.controls.searchPanel.set_search_text, active.text)
            self.tree_menu.show(e)

    def on_bean_expanded(self, parent):
        logging.debug("expanded %s" % parent)

        def task():
            old_iters = self.get_child_iters_by_parent(self.model, self.get_iter_from_bean(parent))
            childs = self.services[u""+parent.text](FCBase().lfm_login, str(int(FC().search_limit)))
            update_parent_for_beans(childs, parent)
            self.append_all(childs)
            GLib.idle_add(self.remove_iters, old_iters)
        self.controls.in_thread.run_with_progressbar(task)

########NEW FILE########
__FILENAME__ = navigation_tree
#-*- coding: utf-8 -*-
'''
Created on 25 сент. 2010

@author: ivan
'''

import os
import logging
import threading

from gi.repository import Gtk
from gi.repository import GLib

from foobnix.fc.fc import FC
from foobnix.fc.fc_cache import FCache
from foobnix.gui.model import FModel
from foobnix.helpers.menu import Popup
from foobnix.gui.state import LoadSave
from foobnix.gui.treeview.common_tree import CommonTreeControl
from foobnix.util.file_utils import open_in_filemanager, rename_file_on_disk,\
    delete_files_from_disk, create_folder_dialog, is_m3u
from foobnix.util.mouse_utils import is_double_left_click, is_rigth_click, is_left_click, \
    is_middle_click_release, is_middle_click, right_click_optimization_for_trees,\
    is_empty_click


class NavigationTreeControl(CommonTreeControl, LoadSave):
    def __init__(self, controls):
        CommonTreeControl.__init__(self, controls)

        self.controls = controls
        self.full_name = ""
        self.label = Gtk.Label()

        self.tree_menu = Popup()

        self.set_headers_visible(True)
        self.set_headers_clickable(True)

        """column config"""
        self.column = Gtk.TreeViewColumn("File", Gtk.CellRendererText(), text=self.text[0], font=self.font[0])
        self._append_column(self.column, _("File"))

        def func(column, cell, model, iter, ext=False):
            try:
                data = model.get_value(iter, self.text[0])
            except TypeError:
                data = None
                pass
            if not model.get_value(iter, self.path[0]):
                cell.set_property('text', '')
                return
            if os.path.isfile(model.get_value(iter, self.path[0])):
                if data:
                    if ext:
                        cell.set_property('text', os.path.splitext(data)[1][1:])
                    else:
                        cell.set_property('text', os.path.splitext(data)[0])
            else:
                if ext:
                    cell.set_property('text', '')

        self.name_column = Gtk.TreeViewColumn("Name", Gtk.CellRendererText(), text=self.text[0], font=self.font[0])
        self.name_column.set_sizing(Gtk.TREE_VIEW_COLUMN_FIXED)
        for rend in self.name_column.get_cells():
            self.name_column.set_cell_data_func(rend, func, False)
        self._append_column(self.name_column, _("Name"))

        self.ext_column = Gtk.TreeViewColumn("Ext", Gtk.CellRendererText(), text=self.text[0], font=self.font[0])
        for rend in self.ext_column.get_cells():
            self.ext_column.set_cell_data_func(rend, func, True)
        self._append_column(self.ext_column, _("Ext"))

        self.configure_send_drag()
        self.configure_recive_drag()

        self.set_type_tree()
        #self.is_empty = False
        self.connect("button-release-event", self.on_button_release)
        self.connect("drag-data-get", self.on_drag_data_get)
        '''to force the ext_column to take the minimum size'''
        self.name_column.set_fixed_width(2000)

        def task(*a):
            self.on_click_header(None, None, on_start=True)
        GLib.idle_add(task)

        self.scroll.get_vscrollbar().connect('show', task)
        self.scroll.get_vscrollbar().connect('hide', task)

    def on_button_release(self, w, e):
        if is_middle_click_release(e):
            # on left click add selected items to current tab
            """to select item under cursor"""
            try:
                path, col, cellx, celly = self.get_path_at_pos(int(e.x), int(e.y))  # @UnusedVariable
                self.get_selection().select_path(path)
            except TypeError:
                pass
            self.add_to_tab(True)
            return


    def on_button_press(self, w, e):
        if is_empty_click(w, e):
            w.get_selection().unselect_all()
        if is_middle_click(e):
            """to avoid unselect all selected items"""
            self.stop_emission('button-press-event')
        if is_left_click(e):
            # on left click expand selected folders
            return

        if is_double_left_click(e):
            # on middle click play selected beans
            self.add_to_tab()
            return

        if is_rigth_click(e):
            right_click_optimization_for_trees(w, e)
            tabhelper = self.controls.perspectives.get_perspective('fs').get_tabhelper()
            # on right click, show pop-up menu
            self.tree_menu.clear()
            self.tree_menu.add_item(_("Append to playlist"), Gtk.STOCK_ADD, lambda: self.add_to_tab(True), None)
            self.tree_menu.add_item(_("Open in new playlist"), Gtk.STOCK_MEDIA_PLAY, self.add_to_tab, None)
            self.tree_menu.add_separator()
            self.tree_menu.add_item(_("Add folder here"), Gtk.STOCK_OPEN, self.add_folder, None)
            self.tree_menu.add_separator()

            if FC().tabs_mode == "Multi":
                self.tree_menu.add_item(_("Add folder in new tab"), Gtk.STOCK_OPEN, lambda: self.add_folder(True), None)
                self.tree_menu.add_item(_("Clear"), Gtk.STOCK_CLEAR, lambda: tabhelper.clear_tree(self.scroll), None)
            self.tree_menu.add_item(_("Update"), Gtk.STOCK_REFRESH, lambda: tabhelper.on_update_music_tree(self.scroll), None)

            f_model, f_t_paths = self.get_selection().get_selected_rows()
            if f_t_paths:
                model = f_model.get_model()
                t_paths = [f_model.convert_child_path_to_path(f_t_path) for f_t_path in f_t_paths]
                row = model[t_paths[0]]
                paths = [model[t_path][self.path[0]] for t_path in t_paths]
                row_refs = [Gtk.TreeRowReference.new(model, t_path) for t_path in t_paths]
                self.tree_menu.add_separator()
                self.tree_menu.add_item(_("Open in file manager"), None, open_in_filemanager, self.get_selected_bean().path)
                self.tree_menu.add_item(_("Create folder"), None, self.create_folder, (model, f_t_paths[0], row))
                self.tree_menu.add_item(_("Rename file (folder)"), None, self.rename_files, (row, self.path[0], self.text[0]))
                self.tree_menu.add_item(_("Delete file(s) / folder(s)"), None, self.delete_files, (row_refs, paths, self.get_iter_from_row_reference))

            self.tree_menu.show(e)

    def _append_column(self, column, title):
        column.label = Gtk.Label(title)
        column.label.show()
        column.set_widget(column.label)
        column.set_clickable(True)
        self.append_column(column)
        column.button = column.label.get_parent().get_parent().get_parent()
        column.button.connect("button-press-event", self.on_click_header)

    def rename_files(self, a):
        row, index_path, index_text = a
        if rename_file_on_disk(row, index_path, index_text):
            self.save_tree()

    def delete_files(self, a):
        row_refs, paths, get_iter_from_row_reference = a
        if delete_files_from_disk(row_refs, paths, get_iter_from_row_reference):
            self.delete_selected()
            self.save_tree()

    def create_folder(self, a):
        model, tree_path, row = a # @UnusedVariable
        file_path = row[self.path[0]]
        new_folder_path = create_folder_dialog(file_path)
        bean = FModel(os.path.basename(new_folder_path), new_folder_path).add_is_file(False)
        if os.path.isfile(file_path):
            bean.add_parent(row[self.parent_level[0]])
        elif os.path.isdir(file_path):
            bean.add_parent(row[self.level[0]])
        else:
            logging.error("So path doesn't exist")
        self.tree_append(bean)
        self.save_tree()

    def add_to_tab(self, current=False):
        paths = self.get_selected_bean_paths()
        to_tree = self.controls.notetabs.get_current_tree()
        try:
            to_model = to_tree.get_model().get_model()
        except AttributeError:
            current = False
            to_model = None
        from_model = self.get_model()

        def task(to_tree, to_model):
            treerows = [from_model[path] for path in paths]
            for  i, treerow in enumerate(treerows):
                for k, ch_row in enumerate(treerow.iterchildren()):
                    treerows.insert(i+k+1, ch_row)

            #treerows = self.playlist_filter(treerows)
            if not current:
                name = treerows[0][0]
                self.controls.notetabs._append_tab(name)
                to_tree = self.controls.notetabs.get_current_tree()     # because to_tree has changed
                to_model = to_tree.get_model().get_model()
            for i, treerow in enumerate(treerows):
                if is_m3u(treerow[self.path[0]]):
                    rows = to_tree.file_paths_to_rows([treerow[self.path[0]]])
                    if rows:
                        rows.reverse()
                        map(lambda row: treerows.insert(i + 1, row), rows)
                        continue
                to_model.append(None, [col for col in treerow])
            t = threading.Thread(target=to_tree.safe_fill_treerows)
            t.start()
            t.join()
            if not current:
                '''gobject because rebuild_as_plain use it too'''
                self.controls.play_first_file_in_playlist()
            self.controls.notetabs.on_save_tabs()
        task(to_tree, to_model)
        #self.controls.search_progress.background_spinner_wrapper(task, to_tree, to_model)

    def add_folder(self, in_new_tab=False):
        chooser = Gtk.FileChooserDialog(title=_("Choose directory with music"),
                                        action=Gtk.FileChooserAction.SELECT_FOLDER,
                                        buttons=(Gtk.STOCK_OPEN, Gtk.ResponseType.OK))
        chooser.set_default_response(Gtk.ResponseType.OK)
        chooser.set_select_multiple(True)
        if FCache().last_music_path:
            chooser.set_current_folder(FCache().last_music_path)
        response = chooser.run()

        if response == Gtk.ResponseType.OK:
            paths = chooser.get_filenames()
            chooser.destroy()
            self.controls.main_window.present()

            def task():
                tabhelper = self.controls.perspectives.get_perspective('fs').get_tabhelper()
                path = paths[0]
                FCache().last_music_path = path[:path.rfind("/")]
                tree = self
                number_of_tab = tabhelper.page_num(tree.scroll)

                if in_new_tab:
                    tab_name = unicode(path[path.rfind("/") + 1:])
                    tabhelper._append_tab(tab_name)
                    tree = tabhelper.get_current_tree()
                    number_of_tab = tabhelper.get_current_page()
                    FCache().music_paths.insert(0, [])
                    FCache().tab_names.insert(0, tab_name)
                    FCache().cache_music_tree_beans.insert(0, {})

                elif tree.is_empty():
                    tab_name = unicode(path[path.rfind("/") + 1:])
                    vbox = Gtk.VBox()
                    label = Gtk.Label(tab_name + " ")
                    label.set_angle(90)
                    if FC().tab_close_element:
                        vbox.pack_start(tabhelper.button(tree.scroll), False, False)
                    vbox.pack_end(label, False, False)
                    event = self.controls.notetabs.to_eventbox(vbox, tree)
                    event = tabhelper.tab_menu_creator(event, tree.scroll)
                    event.connect("button-press-event", tabhelper.on_button_press)
                    tabhelper.set_tab_label(tree.scroll, event)
                    FCache().tab_names[number_of_tab] = tab_name
                    FCache().music_paths[number_of_tab] = []

                for path in paths:
                    if path in FCache().music_paths[number_of_tab]:
                        pass
                    else:
                        FCache().music_paths[number_of_tab].append(path)
                        #self.controls.preferences.on_load()
                        logging.info("New music paths" + str(FCache().music_paths[number_of_tab]))
                self.controls.update_music_tree(tree, number_of_tab)

            #self.controls.in_thread.run_with_progressbar(task, with_lock=False)
            self.controls.search_progress.background_spinner_wrapper(task)
        elif response == Gtk.ResponseType.CANCEL:
            logging.info('Closed, no files selected')
            chooser.destroy()

    def normalize_columns_width(self):
        if not hasattr(self, 'ext_width') or not self.ext_width:
            self.ext_width = self.ext_column.get_width()

        increase = 0
        vscrollbar = self.scroll.get_vscrollbar()
        if not vscrollbar.get_property('visible'):
            increase += 3

        self.name_column.set_fixed_width(self.get_allocation().width - self.ext_width - increase)

    def on_click_header(self, w, e, on_start=False):
        def task(tree):
            if FC().show_full_filename:
                tree.column.set_visible(True)
                tree.name_column.set_visible(False)
                tree.ext_column.set_visible(False)
            else:
                tree.column.set_visible(False)
                tree.name_column.set_visible(True)
                tree.ext_column.set_visible(True)

        if not on_start:
            FC().show_full_filename = not FC().show_full_filename
            tabhelper = self.controls.perspectives.get_perspective('fs').get_tabhelper()
            for page in xrange(tabhelper.get_n_pages()):
                tab_content = tabhelper.get_nth_page(page)
                tree = tab_content.get_child()
                task(tree)
        else:
            task(self)
            self.normalize_columns_width()

    def on_load(self):
        #self.controls.load_music_tree()
        self.restore_expand(FC().nav_expand_paths)
        self.restore_selection(FC().nav_selected_paths)

        def set_expand_path(new_value):
            FC().nav_expand_paths = new_value

        def set_selected_path(new_value):
            FC().nav_selected_paths = new_value

        self.expand_updated(set_expand_path)
        self.selection_changed(set_selected_path)

    def on_save(self):
        pass

    def on_drag_data_get(self, source_tree, drag_context, selection, info, time):
        treeselection = source_tree.get_selection()
        ff_model, ff_paths = treeselection.get_selected_rows()
        iters = [ff_model.get_iter(ff_path) for ff_path in ff_paths]
        all_file_paths = ''
        for iter in iters:
            all_iters = self.get_list_of_iters_with_children(ff_model, iter)
            file_paths = ','.join([ff_model.get_value(iter, self.path[0]) for iter in all_iters])
            all_file_paths += file_paths

        selection.set(selection.get_target(), 0, all_file_paths)
        self.stop_emission('drag-data-get')

    def save_tree(self):
        page_num = self.controls.perspectives.get_perspective('fs').get_tabhelper().page_num(self.scroll)
        self.save_rows_from_tree(FCache().cache_music_tree_beans[page_num])
########NEW FILE########
__FILENAME__ = playlist_tree
#-*- coding: utf-8 -*-
'''
Created on 25 сент. 2010

@author: ivan
'''


import logging
import os
import re
import thread

from gi.repository import Gtk
from gi.repository import GLib

from foobnix.fc.fc import FC
from foobnix.playlists.pls_reader import update_id3_for_pls
from foobnix.util import const, idle_task
from foobnix.helpers.menu import Popup
from foobnix.util.bean_utils import get_bean_from_file
from foobnix.util.id3_util import update_id3
from foobnix.util.tag_util import edit_tags
from foobnix.util.converter import convert_files
from foobnix.util.audio import get_mutagen_audio
from foobnix.util.file_utils import open_in_filemanager, copy_to, get_files_from_gtk_selection_data,\
    get_file_extension, is_playlist
from foobnix.util.localization import foobnix_localization
from foobnix.gui.treeview.common_tree import CommonTreeControl
from foobnix.util.key_utils import KEY_RETURN, is_key, KEY_DELETE, \
    is_modificator
from foobnix.util.mouse_utils import is_double_left_click, \
    is_rigth_click, right_click_optimization_for_trees, is_empty_click

from foobnix.playlists.m3u_reader import update_id3_for_m3u


foobnix_localization()

FLAG = False


class PlaylistTreeControl(CommonTreeControl):
    def __init__(self, controls):
        CommonTreeControl.__init__(self, controls)

        self.menu = Popup()
        self.tree_menu = Popup()
        self.full_name = ""
        self.label = Gtk.Label()

        self.set_headers_visible(True)
        self.set_headers_clickable(True)
        self.set_reorderable(True)

        """Column icon"""
        self.icon_col = Gtk.TreeViewColumn(None, Gtk.CellRendererPixbuf(), icon_name=self.play_icon[0])
        self.icon_col.key = "*"
        self.icon_col.set_sizing(Gtk.TreeViewColumnSizing.FIXED)
        self.icon_col.set_fixed_width(32)
        self.icon_col.set_min_width(32)
        self.icon_col.label = Gtk.Label("*")
        self._append_column(self.icon_col)

        """track number"""
        self.trkn_col = Gtk.TreeViewColumn(None, Gtk.CellRendererText(), text=self.tracknumber[0])
        self.trkn_col.key = "N"
        self.trkn_col.set_clickable(True)
        self.trkn_col.label = Gtk.Label("№")
        self.trkn_col.label.show()
        self.trkn_col.item = Gtk.CheckMenuItem(_("Number"))
        self.trkn_col.set_widget(self.trkn_col.label)
        self._append_column(self.trkn_col)

        """column composer"""
        self.comp_col = Gtk.TreeViewColumn(None, Gtk.CellRendererText(), text=self.composer[0])
        self.comp_col.key = "Composer"
        self.comp_col.set_resizable(True)
        self.comp_col.label = Gtk.Label(_("Composer"))
        self.comp_col.item = Gtk.CheckMenuItem(_("Composer"))
        self._append_column(self.comp_col)

        """column artist title"""
        self.description_col = Gtk.TreeViewColumn(None, Gtk.CellRendererText(), text=self.text[0], font=self.font[0])
        self.description_col.key = "Track"
        self.description_col.set_resizable(True)
        self.description_col.label = Gtk.Label(_("Track"))
        self.description_col.item = Gtk.CheckMenuItem(_("Track"))
        self._append_column(self.description_col)

        """column artist"""
        self.artist_col = Gtk.TreeViewColumn(None, Gtk.CellRendererText(), text=self.artist[0])
        self.artist_col.key = "Artist"
        self.artist_col.set_sizing(Gtk.TREE_VIEW_COLUMN_AUTOSIZE)
        self.artist_col.set_resizable(True)
        self.artist_col.label = Gtk.Label(_("Artist"))
        self.artist_col.item = Gtk.CheckMenuItem(_("Artist"))
        self._append_column(self.artist_col)

        """column title"""
        self.title_col = Gtk.TreeViewColumn(None, Gtk.CellRendererText(), text=self.title[0])
        self.title_col.key = "Title"
        self.title_col.set_sizing(Gtk.TREE_VIEW_COLUMN_AUTOSIZE)
        self.title_col.set_resizable(True)
        self.title_col.label = Gtk.Label(_("Title"))
        self.title_col.item = Gtk.CheckMenuItem(_("Title"))
        self._append_column(self.title_col)

        """column album"""
        self.album_col = Gtk.TreeViewColumn(None, Gtk.CellRendererText(), text=self.album[0])
        self.album_col.key = "Album"

        if self.album_col.key not in FC().columns:
            FC().columns[self.album_col.key] = [False, 7, 90]
        self.album_col.set_sizing(Gtk.TREE_VIEW_COLUMN_AUTOSIZE)
        self.album_col.set_resizable(True)
        self.album_col.label = Gtk.Label(_("Album"))
        self.album_col.item = Gtk.CheckMenuItem(_("Album"))
        self._append_column(self.album_col)

        """column time"""
        self.time_col = Gtk.TreeViewColumn(None, Gtk.CellRendererText(), text=self.time[0])
        self.time_col.key = "Time"
        self.time_col.label = Gtk.Label(_("Time"))
        self.time_col.item = Gtk.CheckMenuItem(_("Time"))
        self._append_column(self.time_col)

        self.configure_send_drag()
        self.configure_recive_drag()

        self.set_playlist_plain()

        self.connect("button-release-event", self.on_button_press)

        self.on_load()

        self.connect("columns-changed", self.on_columns_changed)

    def set_playlist_tree(self):
        self.rebuild_as_tree()

    def set_playlist_plain(self):
        self.rebuild_as_plain()

    def on_key_release(self, w, e):
        if is_modificator(e):
            return
        elif is_key(e, KEY_RETURN):
            self.controls.play_selected_song()
        elif is_key(e, KEY_DELETE):
            self.delete_selected()
        elif is_key(e, 'Left'):
            self.controls.seek_down()
        elif is_key(e, 'Right'):
            self.controls.seek_up()

    def get_bean_under_pointer_icon(self):
        for row in self.model:
            if row[self.play_icon[0]]:
                bean = self.get_bean_from_row(row)
                return bean

    def common_single_random(self):
        logging.debug("Repeat state " + str(FC().repeat_state))
        if FC().repeat_state == const.REPEAT_SINGLE:
            return self.get_current_bean_by_UUID()

        if FC().is_order_random:
            bean = self.get_random_bean()
            self.set_play_icon_to_bean(bean)
            return bean

    def next(self):
        bean = self.common_single_random()
        if bean:
            self.scroll_follow_play_icon()
            return bean

        bean = self.get_next_bean(FC().repeat_state == const.REPEAT_ALL)

        if not bean:
            self.controls.state_stop()
            return

        self.set_play_icon_to_bean(bean)
        self.scroll_follow_play_icon()

        logging.debug("Next bean " + str(bean) + bean.text)

        return bean

    def prev(self):
        if FC().repeat_state == const.REPEAT_SINGLE:
            return self.get_current_bean_by_UUID()

        bean = self.get_prev_bean(FC().repeat_state == const.REPEAT_ALL)

        if not bean:
            self.controls.state_stop()
            return

        self.set_play_icon_to_bean(bean)
        self.scroll_follow_play_icon()

        return bean


    @idle_task
    def scroll_follow_play_icon(self):
        paths = [(i,) for i, row in enumerate(self.model)]
        for row, path in zip(self.model, paths):
            if row[self.play_icon[0]]:
                start_path, end_path = self.get_visible_range()
                path = row.path
                if path >= end_path or path <= start_path:
                    self.scroll_to_cell(path)

    def append(self, paths):
        for i, path in enumerate(paths):
            if os.path.isdir(path):
                listdir = filter(lambda x: get_file_extension(x) in FC().all_support_formats or os.path.isdir(x),
                                 [os.path.join(path, f) for f in os.listdir(path)])
                for k, p in enumerate(listdir):
                    paths.insert(i + k + 1, p)
        rows = self.file_paths_to_rows(paths)
        if not rows:
            return
        #rows = self.playlist_filter(rows)
        for row in rows:
            self.model.append(None, row)
        thread.start_new_thread(self.safe_fill_treerows, ())

    def is_empty(self):
        return True if not self.model.get_iter_first() else False

    def on_button_press(self, w, e):
        if is_empty_click(w, e):
            w.get_selection().unselect_all()
        if is_double_left_click(e):
            self.controls.play_selected_song()

        if is_rigth_click(e):
            right_click_optimization_for_trees(w, e)
            beans = self.get_selected_beans()
            if beans:
                self.tree_menu.clear()
                self.tree_menu.add_item(_('Play'), Gtk.STOCK_MEDIA_PLAY, self.controls.play_selected_song, None)
                self.tree_menu.add_item(_('Delete from playlist'), Gtk.STOCK_DELETE, self.delete_selected, None)

                paths = []
                inet_paths = []
                local_paths = []
                for bean in beans:
                    if bean.path in paths:
                        continue
                    paths.append(bean.path)
                    if not bean.path or bean.path.startswith("http://"):
                        inet_paths.append(bean.path)
                    else:
                        local_paths.append(bean.path)

                if local_paths:
                    self.tree_menu.add_item(_('Copy To...'), Gtk.STOCK_ADD, copy_to, local_paths)
                    self.tree_menu.add_item(_("Open in file manager"), None, open_in_filemanager, local_paths[0])
                if inet_paths:
                    self.tree_menu.add_item(_('Download'), Gtk.STOCK_ADD,
                                            self.controls.dm.append_tasks, self.get_all_selected_beans())
                    self.tree_menu.add_item(_('Download To...'), Gtk.STOCK_ADD,
                                            self.controls.dm.append_tasks_with_dialog, self.get_all_selected_beans())

                self.tree_menu.add_separator()

                if local_paths:
                    self.tree_menu.add_item(_('Edit Tags'), Gtk.STOCK_EDIT, edit_tags, (self.controls, local_paths))
                    self.tree_menu.add_item(_('Format Converter'), Gtk.STOCK_CONVERT, convert_files, local_paths)
                text = self.get_selected_bean().text
                self.tree_menu.add_item(_('Copy To Search Line'), Gtk.STOCK_COPY,
                                        self.controls.searchPanel.set_search_text, text)
                self.tree_menu.add_separator()
                self.tree_menu.add_item(_('Copy №-Title-Time'), Gtk.STOCK_COPY, self.copy_info_to_clipboard)
                self.tree_menu.add_item(_('Copy Artist-Title-Album'), Gtk.STOCK_COPY,
                                        self.copy_info_to_clipboard, True)
                self.tree_menu.add_separator()
                self.tree_menu.add_item(_('Love This Track(s) by Last.fm'), None,
                                        self.controls.love_this_tracks, self.get_all_selected_beans())
                self.tree_menu.add_item(_('Add to My Audio (VK)'), None,
                                        self.controls.add_to_my_playlist, self.get_all_selected_beans())

                self.tree_menu.show(e)

    def on_click_header(self, w, e):
        if is_rigth_click(e):
            if "menu" in w.__dict__:
                w.menu.show(e)
            else:
                self.menu.show(e)

    def on_toggled_num(self, *a):
        FC().numbering_by_order = not FC().numbering_by_order
        number_music_tabs = self.controls.notetabs.get_n_pages() - 1
        for page in xrange(number_music_tabs, -1, -1):
            tab_content = self.controls.notetabs.get_nth_page(page)
            pl_tree = tab_content.get_child()
            if FC().numbering_by_order:
                pl_tree.update_tracknumber()
                pl_tree.num_order.set_active(True)
                continue
            pl_tree.num_tags.set_active(True)
            for row in pl_tree.model:
                if row[pl_tree.is_file[0]]:
                    audio = get_mutagen_audio(row[pl_tree.path[0]])
                    if audio and audio.has_key('tracknumber'):
                        row[pl_tree.tracknumber[0]] = re.search('\d*', audio['tracknumber'][0]).group()
                    if audio and audio.has_key('trkn'):
                        row[pl_tree.tracknumber[0]] = re.search('\d*', audio["trkn"][0]).group()

    def on_toggle(self, w, e, column):
        FC().columns[column.key][0] = not FC().columns[column.key][0]

        number_music_tabs = self.controls.notetabs.get_n_pages() - 1
        for key in self.__dict__.keys():
            if self.__dict__[key] is column:
                atr_name = key
                break

        for page in xrange(number_music_tabs, -1, -1):
            tab_content = self.controls.notetabs.get_nth_page(page)
            pl_tree = tab_content.get_child()
            ## TODO: check "local variable 'atr_name' might be referenced before assignment"
            pl_tree_column = pl_tree.__dict__[atr_name]
            if FC().columns[column.key][0]:
                pl_tree.move_column_after(pl_tree_column, pl_tree.icon_col)
                pl_tree_column.set_visible(True)
                if self is not pl_tree:
                    pl_tree_column.item.set_active(True)
            else:
                pl_tree_column.set_visible(False)
                if self is not pl_tree:
                    pl_tree_column.item.set_active(False)

    def _append_column(self, column):
        column.set_widget(column.label)
        column.set_sizing(Gtk.TREE_VIEW_COLUMN_FIXED)
        if column.key in ['*', 'N', 'Time']:
            column.set_sizing(Gtk.TREE_VIEW_COLUMN_AUTOSIZE)
        else:
            column.set_sizing(Gtk.TREE_VIEW_COLUMN_FIXED)
        if FC().columns[column.key][2] > 0:
            column.set_fixed_width(FC().columns[column.key][2])

        self.append_column(column)
        column.button = column.label.get_parent().get_parent().get_parent()
        column.button.connect("button-press-event", self.on_click_header)
        '''
        if column.key == 'N':
            self.trkn_col.button.menu = Popup()
            group = []
            self.num_order = Gtk.RadioMenuItem.new_with_label(group, _("Numbering by order"))
            self.num_order.connect("button-press-event", self.on_toggled_num)
            group.append(self.num_order)
            self.num_tags = Gtk.RadioMenuItem.new_with_label(group, _("Numbering by tags"))
            self.num_tags.connect("button-press-event", self.on_toggled_num)
            group.append(self.num_tags)
            self.trkn_col.button.menu.append(self.num_order)
            self.trkn_col.button.menu.append(self.num_tags)
            if FC().numbering_by_order:
                self.num_order.set_active(True)
            else:
                self.num_tags.set_active(True)
        '''

    def on_columns_changed(self, *a):
        global FLAG
        if FLAG:
            return
        FLAG = True

        number_music_tabs = self.controls.notetabs.get_n_pages() - 1
        for i, column in enumerate(self.get_columns()):
            FC().columns[column.key][1] = i
            if column.get_width() > 1:  # to avoid recording of zero width in config
                FC().columns[column.key][2] = column.get_width()

        for page in xrange(number_music_tabs, 0, -1):
            tab_content = self.controls.notetabs.get_nth_page(page)
            pl_tree = tab_content.get_child()
            col_list = pl_tree.get_columns()
            col_list.sort(self.to_order_columns, reverse=True)
            for column in col_list:
                pl_tree.move_column_after(column, None)
        FLAG = False

    def to_order_columns(self, x, y):
        return cmp(FC().columns[x.key][1], FC().columns[y.key][1])

    def on_load(self):
        col_list = self.get_columns()
        col_list.sort(self.to_order_columns, reverse=True)
        visible_columns = []
        for column in col_list:
            column.label.show()
            column.set_widget(column.label)
            column.set_clickable(True)
            if column.key != "*":
                column.set_reorderable(True)
            if FC().columns[column.key][0]:
                self.move_column_after(column, None)
                if "item" in column.__dict__:
                    column.item.connect("button-press-event", self.on_toggle, column)
                    self.menu.append(column.item)
                    column.item.set_active(True)
                visible_columns.append(column)
            else:
                if "item" in column.__dict__:
                    column.item.connect("button-press-event", self.on_toggle, column)
                    self.menu.append(column.item)
                    column.item.set_active(False)
                column.set_visible(False)
        '''if FC().columns["Track"][2] < 0:
             self.description_col.set_fixed_width(self.get_allocation().width - (FC().columns["Time"][2]+70))'''

    def change_rows_by_path(self, file_paths):
        for treerow in self.model:
            if treerow[self.is_file[0]] and treerow[self.path[0]] in file_paths:
                bean = self.get_bean_from_row(treerow)
                bean = update_id3(bean)
                row_ref = Gtk.TreeRowReference.new(self.model, treerow.path)
                self.fill_row(row_ref, bean)
        GLib.idle_add(self.controls.notetabs.save_current_tab, priority=GLib.PRIORITY_LOW)

    def file_paths_to_rows(self, paths):
        result = []
        for path in paths:
            bean = get_bean_from_file(path)
            beans = update_id3_for_m3u([bean])
            beans = update_id3_for_pls(beans)
            if beans and (len(beans) > 1 or is_playlist(bean.path)):
                    bean = bean.add_text(_('Playlist: ') + bean.text).add_font("bold").add_is_file(False)
                    bean.path = ''
                    beans.insert(0, bean)
            for bean in beans:
                result.append(self.get_row_from_bean(bean))
        return result

    def on_drag_data_received(self, treeview, context, x, y, selection, info, timestamp):
        logging.debug('Playlist on_drag_data_received')
        model = self.get_model().get_model()
        drop_info = self.get_dest_row_at_pos(x, y)

        if drop_info:
            path, position = drop_info
            iter = model.get_iter(path)

        files = sorted([file for file in get_files_from_gtk_selection_data(selection)
                if os.path.isdir(file) or get_file_extension(file) in FC().all_support_formats],
                key=lambda x: x[self.text[0]])
        if files:
            '''dnd from the outside of the player'''
            if self.is_empty():
                if len(files) == 1 and os.path.isdir(files[0]):
                    tabname = os.path.basename(files[0])
                else:
                    tabname = os.path.split(os.path.dirname(files[0]))[1]
                self.controls.notetabs.rename_tab(self.scroll, tabname)
            for i, file in enumerate(files):
                if os.path.isdir(file):
                    sorted_dirs = []
                    sorted_files = []
                    for f in sorted(os.listdir(file), key=lambda x: x):
                        f = os.path.join(file, f)
                        if os.path.isdir(f):
                            sorted_dirs.append(f)
                        elif get_file_extension(f) in FC().all_support_formats:
                            sorted_files.append(f)

                    listdir = sorted_dirs + sorted_files
                    '''
                    listdir = sorted(filter(lambda x: get_file_extension(x) in FC().all_support_formats or os.path.isdir(x),
                                     [os.path.join(file, f) for f in os.listdir(file)]), key=lambda x: x)
                    '''
                    for k, path in enumerate(listdir):
                        files.insert(i + k + 1, path)

            rows = self.file_paths_to_rows(files)
            if not rows:
                return
            rows = self.playlist_filter(rows)
            for row in rows:
                if drop_info:
                    if (position == Gtk.TREE_VIEW_DROP_BEFORE
                        or position == Gtk.TREE_VIEW_DROP_INTO_OR_BEFORE):
                        model.insert_before(None, iter, row)
                    else:
                        model.insert_after(None, iter, row)
                        iter = model.iter_next(iter)
                else:
                    model.append(None, row)

        else:
            '''dnd inside the player'''
            # ff - from_filter
            ff_tree = Gtk.drag_get_source_widget(context)
            ff_model, ff_paths = ff_tree.get_selection().get_selected_rows()
            treerows = [ff_model[ff_path] for ff_path in ff_paths]

            if self is ff_tree:
                '''internal dnd'''
                ff_row_refs = [Gtk.TreeRowReference.new(ff_model, ff_path) for ff_path in ff_paths]
                for ff_row_ref in ff_row_refs:
                    ff_iter = self.get_iter_from_row_reference(ff_row_ref)
                    f_iter = ff_model.convert_iter_to_child_iter(ff_iter)
                    if drop_info:
                        if (position == Gtk.TREE_VIEW_DROP_BEFORE
                            or position == Gtk.TREE_VIEW_DROP_INTO_OR_BEFORE):
                            model.move_before(f_iter, iter)
                        else:
                            model.move_after(f_iter, iter)
                            iter = model.iter_next(iter)
                    else:
                        model.move_before(f_iter, None)
                return

            else:
                '''dnd from other tree'''
                if self.is_empty():
                    path = treerows[0][self.path[0]]
                    if path:
                        if len(treerows) == 1 and os.path.isdir(path):
                            tabname = os.path.basename(path)
                        else:
                            tabname = os.path.split(os.path.dirname(path))[1]
                        self.controls.notetabs.rename_tab(self.scroll, tabname)
                    else:
                        pass
                for i, treerow in enumerate(treerows):

                    for k, ch_row in enumerate(treerow.iterchildren()):
                        treerows.insert(i + k + 1, ch_row)

                #treerows = self.playlist_filter(treerows)

                for i, treerow in enumerate(treerows):
                    if is_playlist(treerow[self.path[0]]):
                        rows = self.file_paths_to_rows([treerow[self.path[0]]])
                        if rows:
                            rows.reverse()
                            map(lambda row: treerows.insert(i + 1, row), rows)
                            continue
                    row = [col for col in treerow]
                    if drop_info:
                        if (position == Gtk.TREE_VIEW_DROP_BEFORE
                            or position == Gtk.TREE_VIEW_DROP_INTO_OR_BEFORE):
                            model.insert_before(None, iter, row)
                        else:
                            model.insert_after(None, iter, row)
                            iter = model.iter_next(iter)
                    else:
                        model.append(None, row)


        thread.start_new_thread(self.safe_fill_treerows, ())

        context.finish(True, False, timestamp)
        self.stop_emission('drag-data-received')
        return True


########NEW FILE########
__FILENAME__ = radio_tree
'''
Created on Sep 29, 2010

@author: ivan
'''

from __future__ import with_statement

import logging
import os.path
import thread

from gi.repository import Gtk

from foobnix.fc.fc import FC
from foobnix.fc.fc_cache import FCache, CACHE_RADIO_FILE
from foobnix.helpers.dialog_entry import two_line_dialog, one_line_dialog
from foobnix.helpers.menu import Popup
from foobnix.gui.model import FModel, FTreeModel
from foobnix.gui.service.radio_service import RadioFolder
from foobnix.gui.treeview.common_tree import CommonTreeControl
from foobnix.util import idle_task
from foobnix.util.const import FTYPE_RADIO
from foobnix.util.mouse_utils import is_double_left_click, is_rigth_click,\
    right_click_optimization_for_trees, is_empty_click
from foobnix.util.key_utils import is_key, KEY_DELETE


class RadioTreeControl(CommonTreeControl):
    def __init__(self, controls):
        CommonTreeControl.__init__(self, controls)
        self.set_reorderable(False)
        self.switcher_label = _("My channels")
        self.tree_menu = Popup()
        """column config"""
        column = Gtk.TreeViewColumn(_("Radio Stations"), Gtk.CellRendererText(), text=self.text[0], font=self.font[0])
        column.set_resizable(True)
        self.set_headers_visible(True)
        self.append_column(column)

        self.configure_send_drag()
        self.configure_recive_drag()
        self.set_type_tree()

    @idle_task
    def on_load(self):
        if FCache().cache_radio_tree_beans:
            self.restore_rows(FCache().cache_radio_tree_beans)
        else:
            self.update_radio_tree()

    def on_button_press(self, w, e):
        if is_double_left_click(e):
            selected = self.get_selected_bean()
            beans = self.get_all_child_beans_by_selected()
            self.controls.notetabs._append_tab(selected.text, [selected] + beans, optimization=True)
            "run radio channel"
            self.controls.play_first_file_in_playlist()

        if is_rigth_click(e):
            right_click_optimization_for_trees(w, e)

            self.tree_menu.clear()
            bean = self.get_selected_bean()
            if bean:
                if self.get_selected_bean().is_file:
                    self.tree_menu.add_item(_("Edit Station"), Gtk.STOCK_EDIT, self.on_edit_radio, None)
                    self.tree_menu.add_item(_("Delete Station"), Gtk.STOCK_DELETE, self.delete_selected, None)
                else:
                    self.tree_menu.add_item(_("Rename Group"), Gtk.STOCK_EDIT, self.on_rename_group, None)
                    self.tree_menu.add_item(_("Delete Group"), Gtk.STOCK_DELETE, self.delete_selected, None)
                self.tree_menu.add_separator()
            self.tree_menu.add_item(_("Reload radio folder"), Gtk.STOCK_REFRESH, self.update_radio_tree, None)
            self.tree_menu.show(e)

    def on_edit_radio(self):
        bean = self.get_selected_bean()
        name, url = two_line_dialog(_("Edit Radio"),
                                    parent = self.controls.main_window,
                                    message_text1 = _("Enter new name and URL"),
                                    message_text2 = None,
                                    entry_text1=bean.text,
                                    entry_text2 = bean.path)
        if not name or not url:
            return
        bean.add_text(name)
        bean.add_path(url)

        rows = self.find_rows_by_element(self.UUID, bean.UUID)
        if rows:
            rows[0][self.text[0]] = name
            rows[0][self.path[0]] = url

    def on_rename_group(self):
        bean = self.get_selected_bean()
        name = one_line_dialog(_("Rename Group"), self.controls.main_window,
                               entry_text=bean.text, message_text1=_("Enter new group name"))
        if not name:
            return
        rows = self.find_rows_by_element(self.UUID, bean.UUID)
        if rows:
            rows[0][self.text[0]] = name

    def on_add_station(self):
        name, url = two_line_dialog(_("Add New Radio Station"),
                                    parent = self.controls.main_window,
                                    message_text1 = _("Enter station name and URL"),
                                    message_text2 = None,
                                    entry_text1 = None,
                                    entry_text2 = "http://")
        if not name or not url:
            return
        bean = self.get_selected_bean()
        new_bean = FModel(name, url).add_type(FTYPE_RADIO).add_is_file(True)
        if bean:
            if bean.is_file:
                new_bean.add_parent(bean.parent_level)
            else:
                new_bean.add_parent(bean.level)
        self.append(new_bean)

    def on_save(self):
        pass

    #def update_radio_tree(self):
    #    self.controls.in_thread.run_with_progressbar(self._update_radio_tree)

    @idle_task
    def update_radio_tree(self):
        logging.info("in update radio")
        self.clear_tree()
        self.radio_folder = RadioFolder()
        files = self.radio_folder.get_radio_FPLs()
        for fpl in files:
            parent = FModel(fpl.name).add_is_file(False)
            self.append(parent)
            keys = fpl.urls_dict.keys()
            keys.sort()
            for radio in keys:
                child = FModel(radio, fpl.urls_dict[radio][0]).parent(parent).add_type(FTYPE_RADIO).add_is_file(True)
                self.append(child)

    def auto_add_user_station(self):
        if os.path.isfile(CACHE_RADIO_FILE) and os.path.getsize(CACHE_RADIO_FILE) > 0:
            with open(CACHE_RADIO_FILE, 'r') as f:
                list = f.readlines()
                parent_level_for_depth = {}
                previous = {"bean": None, "depth": 0, "name": '', "url": ''}
                for line in list:
                    depth = self.simbol_counter(line, '-')
                    try:
                        name = line[depth : line.index('#')]
                    except ValueError, e:
                        logging.warning('\'#\' ' + str(e) + ' in line \"' + line + '\"')
                        continue
                    url = line[line.index('#') + 1 : -1]
                    bean = FModel(name)
                    if url:
                        bean.add_is_file(True).add_path(url).add_type(FTYPE_RADIO)
                    if previous["depth"] < depth:
                        bean.add_parent(previous["bean"].level)
                    elif previous["depth"] > depth:
                        bean.add_parent(parent_level_for_depth[depth])
                    else:
                        if previous["bean"]:
                            bean.add_parent(previous["bean"].parent_level)

                    self.append(bean)
                    parent_level_for_depth[depth] = bean.parent_level
                    previous = {"bean": bean, "depth": depth, "name": name, "url": url}

    def simbol_counter(self, line, simbol):
        counter = 0
        for letter in line:
            if letter == simbol:
                counter += 1
            else:
                break
        return counter

    def lazy_load(self):
        def task():
            logging.debug("radio Lazy loading")
            if FCache().cache_radio_tree_beans:
                self.populate_all(FCache().cache_radio_tree_beans)
            else:
                self.update_radio_tree()
            self.is_radio_populated = True
        thread.start_new_thread(task, ())

    def on_quit(self):
        self.save_rows_from_tree(FCache().cache_radio_tree_beans)


class MyRadioTreeControl(RadioTreeControl):
    def __init__(self, controls):
        RadioTreeControl.__init__(self, controls)
        self.switcher_label = _("Autogenerated channels")

    def on_load(self):
        self.auto_add_user_station()

    def on_button_press(self, w, e):
        if is_empty_click(w, e):
            w.get_selection().unselect_all()

        if is_double_left_click(e):
            selected = self.get_selected_bean()
            beans = self.get_all_child_beans_by_selected()
            self.controls.notetabs._append_tab(selected.text, [selected] + beans, optimization=True)
            "run radio channel"
            self.controls.play_first_file_in_playlist()

        if is_rigth_click(e):
            right_click_optimization_for_trees(w, e)

            self.tree_menu.clear()
            self.tree_menu.add_item(_("Add Station"), Gtk.STOCK_ADD, self.on_add_station, None)
            self.tree_menu.add_item(_("Create Group"), Gtk.STOCK_ADD, self.create_new_group, None)
            bean = self.get_selected_bean()
            if bean:
                if self.get_selected_bean().is_file:
                    self.tree_menu.add_item(_("Edit Station"), Gtk.STOCK_EDIT, self.on_edit_radio, None)
                    self.tree_menu.add_item(_("Delete Station"), Gtk.STOCK_DELETE, self.delete_selected, None)
                else:
                    self.tree_menu.add_item(_("Rename Group"), Gtk.STOCK_EDIT, self.on_rename_group, None)
                    self.tree_menu.add_item(_("Delete Group"), Gtk.STOCK_DELETE, self.delete_selected, None)
            self.tree_menu.show(e)

    def on_key_release(self, w, e):
        if is_key(e, KEY_DELETE):
            self.delete_selected()

    def create_new_group(self):
        name = one_line_dialog(_("Create Group"), self.controls.main_window, message_text1=_("Enter group name"))
        if not name:
            return
        bean = self.get_selected_bean()
        folder_bean = FModel(name)
        if bean:
            if bean.is_file:
                folder_bean.add_parent(bean.parent_level)
            else:
                folder_bean.add_parent(bean.level)
        self.append(folder_bean)
        '''
        #another method without sorting
        selected = self.get_dest_row_at_pos(x, y)
        if selected:
            m, paths = selected
            iter = self.get_iter(paths[0])
            treerow = self[paths[0]]
            row = [col for col in treerow]
            if self.get_value(iter, self.is_file[0]):
                self.insert_after(None, iter, row)
            else:
                self.append(iter, row)
        else:
            self.append(None, row)
        '''

    def on_quit(self):

        with open(CACHE_RADIO_FILE, 'w') as f:
            def task(row):
                iter = row.iter
                level = self.model.iter_depth(iter)
                text = self.model.get_value(iter, FTreeModel().text[0])
                path = self.model.get_value(iter, FTreeModel().path[0])
                if not path:
                    path = ""
                f.write(level * '-' + text + '#' + path + '\n')
                if row.iterchildren():
                    for child_row in row.iterchildren():
                        task(child_row)

            for row in self.model:
                task(row)

    def on_drag_data_received(self, treeview, context, x, y, selection, info, timestamp):
        logging.debug('Storage on_drag_data_received')
        model = self.get_model().get_model()
        drop_info = self.get_dest_row_at_pos(x, y)

        # ff - from_filter
        ff_tree = Gtk.drag_get_source_widget(context)
        ff_model, ff_paths = ff_tree.get_selection().get_selected_rows()
        treerows = [ff_model[ff_path] for ff_path in ff_paths]
        if drop_info:
            path, position = drop_info
            iter = model.get_iter(path)

        if self == ff_tree:
            ff_row_refs = [Gtk.TreeRowReference.new(ff_model, ff_path) for ff_path in ff_paths]

            def add_childs(treerow, new_iter):
                    for ch_row in treerow.iterchildren():
                        niter = model.append(new_iter, [col for col in ch_row])
                        add_childs(ch_row, niter)
            for treerow, ref in zip(treerows, ff_row_refs):
                row = [col for col in treerow]
                if drop_info:
                    if position == Gtk.TREE_VIEW_DROP_BEFORE:
                        new_iter = model.insert_before(None, iter, row)
                    elif (position == Gtk.TREE_VIEW_DROP_INTO_OR_BEFORE or
                          position == Gtk.TREE_VIEW_DROP_INTO_OR_AFTER):
                        if model.get_value(iter, self.is_file[0]):
                            new_iter = model.insert_after(None, iter, row)
                            iter = model.iter_next(iter)
                        else:
                            new_iter = model.append(iter, row)
                    else:
                        new_iter = model.insert_after(None, iter, row)
                        iter = model.iter_next(iter)
                else:
                    new_iter = model.append(None, row)
                treerow = model[ref.get_path()]     # reinitialize
                add_childs(treerow, new_iter)
            self.remove_replaced(ff_model, ff_row_refs)

        self.stop_emission('drag-data-received')
########NEW FILE########
__FILENAME__ = simple_tree
'''
Created on Sep 28, 2010

@author: ivan
'''

from gi.repository import Gtk

from foobnix.helpers.menu import Popup
from foobnix.gui.state import LoadSave
from foobnix.gui.model import FTreeModel
from foobnix.gui.treeview.common_tree import CommonTreeControl
from foobnix.util.mouse_utils import is_rigth_click, is_double_left_click, \
    is_left_click, right_click_optimization_for_trees, is_empty_click
from foobnix.util.const import FTYPE_NOT_UPDATE_INFO_PANEL, \
     DOWNLOAD_STATUS_ALL


class SimpleTreeControl(CommonTreeControl, LoadSave):
    def __init__(self, title_name, controls, head_visible=True):        
        CommonTreeControl.__init__(self, controls)
        self.title_name = title_name 
        
        self.set_reorderable(False)
        
        """column config"""
        column = Gtk.TreeViewColumn(title_name, Gtk.CellRendererText(), text=self.text[0], font=self.font[0])
        column.set_resizable(True)
        self.append_column(column)
        self.set_headers_visible(head_visible)
        
        self.configure_send_drag()
        
        self.set_type_plain()
        #self.populate_all([FModel("Madonna").add_is_file(True)])
        
        self.line_title = None
    
    def get_title(self):
        return self.title_name
    
    def on_button_press(self, w, e):
        if is_empty_click(w, e):
            w.get_selection().unselect_all()
        active = self.get_selected_bean()
        if active:
            active.type = FTYPE_NOT_UPDATE_INFO_PANEL
        else:
            return None
        
        if is_left_click(e):
            if active.get_status():
                if active.get_status() == DOWNLOAD_STATUS_ALL:
                    self.controls.dm.filter(None, FTreeModel().status[0])
                else:
                    self.controls.dm.filter(active.get_status(), FTreeModel().status[0])
                
        if is_double_left_click(e):
            self.controls.play(active)
        
        if is_rigth_click(e):
            right_click_optimization_for_trees(w, e)
            menu = Popup()
            menu.add_item('Play', Gtk.STOCK_MEDIA_PLAY, self.controls.play, active)
            menu.add_item('Copy to Search Line', Gtk.STOCK_COPY, self.controls.searchPanel.set_search_text, active.text)
            menu.show(e)
        
    def on_load(self):
        pass
    
    def on_save(self):
        pass

class SimpleListTreeControl(SimpleTreeControl):
    def __init__(self, title_name, controls, head_visible=True):
        SimpleTreeControl.__init__(self, title_name, controls, head_visible)
        
        self.left_click_func = None
        self.left_click_arg = None
        
        self.connect("cursor-changed", lambda * a:self.on_func())
    
    def set_left_click_func(self, func=None, arg=None):
        self.left_click_func = func
        self.left_click_arg = arg
    
    def on_func(self):
        if self.left_click_func and self.left_click_arg:
            self.left_click_func(self.left_click_arg)
        elif self.left_click_func:
            self.left_click_func()  
    
    def on_button_press(self, w, e):
        if is_left_click(e):            
            self.on_func()                         
        if is_double_left_click(e):
            pass
        
        if is_rigth_click(e):
            pass
        

########NEW FILE########
__FILENAME__ = virtual_tree
'''
Created on Sep 29, 2010

@author: ivan
'''
import logging

from gi.repository import Gtk

from foobnix.gui.state import LoadSave
from foobnix.util.mouse_utils import is_double_left_click, is_rigth_click,\
    right_click_optimization_for_trees, is_empty_click
from foobnix.helpers.menu import Popup
from foobnix.helpers.dialog_entry import one_line_dialog
from foobnix.gui.model import FModel
from foobnix.gui.treeview.common_tree import CommonTreeControl
from foobnix.fc.fc import FC
from foobnix.fc.fc_cache import FCache
from foobnix.util.key_utils import KEY_DELETE, is_key


class VirtualTreeControl(CommonTreeControl, LoadSave):
    def __init__(self, controls):
        CommonTreeControl.__init__(self, controls)

        """column config"""
        column = Gtk.TreeViewColumn(_("Storage"), Gtk.CellRendererText(), text=self.text[0], font=self.font[0])
        column.set_resizable(True)
        self.set_headers_visible(True)
        self.append_column(column)

        self.tree_menu = Popup()

        self.configure_send_drag()
        self.configure_recive_drag()

        self.set_type_tree()

    def on_key_release(self, w, e):
        if is_key(e, KEY_DELETE):
            self.delete_selected()

    def on_drag_drop_finish(self):
        FCache().cache_virtual_tree_beans = self.get_all_beans()
        FC().save()

    def on_button_press(self, w, e):
        if is_empty_click(w, e):
            w.get_selection().unselect_all()
        if is_double_left_click(e):

            selected = self.get_selected_bean()
            beans = self.get_all_child_beans_by_selected()
            self.controls.notetabs._append_tab(selected.text, [selected] + beans, optimization=True)
            self.controls.play_first_file_in_playlist()

        if is_rigth_click(e):
                right_click_optimization_for_trees(w, e)
                self.tree_menu.clear()
                self.tree_menu.add_item(_("Add playlist"), Gtk.STOCK_ADD, self.create_playlist, None)
                bean = self.get_selected_bean()
                if bean:
                    if bean.is_file:
                        self.tree_menu.add_item(_("Rename"), Gtk.STOCK_EDIT, self.rename_selected, None)
                        self.tree_menu.add_item(_("Delete"), Gtk.STOCK_DELETE, self.delete_selected, None)
                    else:
                        self.tree_menu.add_item(_("Rename playlist"), Gtk.STOCK_EDIT, self.rename_selected, None)
                        self.tree_menu.add_item(_("Delete playlist"), Gtk.STOCK_DELETE, self.delete_selected, None)
                #menu.add_item(_("Save as"), Gtk.STOCK_SAVE_AS, None, None)
                #menu.add_item(_("Open as"), Gtk.STOCK_OPEN, None, None)
                self.tree_menu.show(e)

    def create_playlist(self):
        name = one_line_dialog(_("Create new playlist"), self.controls.main_window, message_text1=_("Enter playlist name"))
        if not name:
            return
        bean = self.get_selected_bean()
        folder_bean = FModel(name)
        if bean:
            if bean.is_file:
                folder_bean.add_parent(bean.parent_level)
            else:
                folder_bean.add_parent(bean.level)
        self.append(folder_bean)

    def rename_selected(self):
        bean = self.get_selected_bean()
        name = one_line_dialog(_("Rename Dialog"), self.controls.main_window,
                               entry_text=bean.text, message_text1=_("Enter new name"))
        if not name:
            return
        rows = self.find_rows_by_element(self.UUID, bean.UUID)
        if rows:
            rows[0][self.text[0]] = name

    def on_load(self):
        self.scroll.hide()
        self.restore_rows(FCache().cache_virtual_tree_beans)
        self.restore_expand(FC().virtual_expand_paths)
        self.restore_selection(FC().virtual_selected_paths)

        def set_expand_path(new_value):
            FC().virtual_expand_paths = new_value

        def set_selected_path(new_value):
            FC().virtual_selected_paths = new_value

        self.expand_updated(set_expand_path)
        self.selection_changed(set_selected_path)

    def on_quit(self):
        self.save_rows_from_tree(FCache().cache_virtual_tree_beans)

    def on_drag_data_received(self, treeview, context, x, y, selection, info, timestamp):
        logging.debug('Storage on_drag_data_received')
        model = self.get_model().get_model()
        drop_info = self.get_dest_row_at_pos(x, y)

        # ff - from_filter
        ff_tree = Gtk.drag_get_source_widget(context)
        ff_model, ff_paths = ff_tree.get_selection().get_selected_rows()
        treerows = [ff_model[ff_path] for ff_path in ff_paths]
        if drop_info:
            path, position = drop_info
            iter = model.get_iter(path)
            if position == Gtk.TREE_VIEW_DROP_INTO_OR_BEFORE or position == Gtk.TREE_VIEW_DROP_INTO_OR_AFTER:
                self.model[path][self.font[0]] = 'bold'

        if self == ff_tree:
            ff_row_refs = [Gtk.TreeRowReference.new(ff_model, ff_path) for ff_path in ff_paths]

            def add_childs(treerow, new_iter):
                    for ch_row in treerow.iterchildren():
                        niter = model.append(new_iter, [col for col in ch_row])
                        add_childs(ch_row, niter)
            for treerow, ref in zip(treerows, ff_row_refs):
                row = [col for col in treerow]
                if drop_info:
                    if position == Gtk.TREE_VIEW_DROP_BEFORE:
                        new_iter = model.insert_before(None, iter, row)
                    elif (position == Gtk.TREE_VIEW_DROP_INTO_OR_BEFORE or
                          position == Gtk.TREE_VIEW_DROP_INTO_OR_AFTER):
                        new_iter = model.append(iter, row)
                    else:
                        new_iter = model.insert_after(None, iter, row)
                        iter = model.iter_next(iter)
                else:
                    new_iter = model.append(None, row)
                treerow = model[ref.get_path()]     # reinitialize
                add_childs(treerow, new_iter)
            self.remove_replaced(ff_model, ff_row_refs)
        else:
            for treerow in treerows:
                row = [col for col in treerow]
                if drop_info:
                    if position == Gtk.TREE_VIEW_DROP_BEFORE:
                        new_iter = model.insert_before(None, iter, row)
                    elif (position == Gtk.TREE_VIEW_DROP_INTO_OR_BEFORE or
                          position == Gtk.TREE_VIEW_DROP_INTO_OR_AFTER):
                        new_iter = model.append(iter, row)
                    else:
                        new_iter = model.insert_after(None, iter, row)
                        iter = model.iter_next(iter)
                else:
                    new_iter = model.append(None, row)
                if len(treerows) == 1 and treerow[self.font[0]] == 'bold':
                    while treerow.next and treerow.next[self.font[0]] != 'bold':
                        treerow = treerow.next
                        treerows.append(treerow)
                        drop_info = True
                        iter = new_iter
                        position = Gtk.TREE_VIEW_DROP_INTO_OR_AFTER

        self.stop_emission('drag-data-received')

########NEW FILE########
__FILENAME__ = vk_integration_tree
'''
Created on Jan 27, 2011

@author: ivan
'''

from gi.repository import Gtk
from gi.repository import GLib

import logging

from foobnix.fc.fc import FC
from foobnix.helpers.menu import Popup
from foobnix.gui.model import FModel, FDModel
from foobnix.util.time_utils import convert_seconds_to_text
from foobnix.gui.treeview.common_tree import CommonTreeControl
from foobnix.util.mouse_utils import is_rigth_click, is_double_left_click,\
    right_click_optimization_for_trees, is_empty_click


class VKIntegrationControls(CommonTreeControl):
    def __init__(self, controls):
        CommonTreeControl.__init__(self, controls)

        """column config"""
        column = Gtk.TreeViewColumn(_("VK Integration "), Gtk.CellRendererText(), text=self.text[0], font=self.font[0])
        column.set_resizable(True)
        self.set_headers_visible(True)
        self.append_column(column)

        self.tree_menu = Popup()

        self.configure_send_drag()
        self.configure_recive_drag()

        self.set_type_tree()

        self.lazy = False
        self.cache = []

    def lazy_load(self):
        if not self.lazy:
            self.controls.in_thread.run_with_progressbar(self._lazy_load)

    def _lazy_load(self):
        def get_users_by_uuid(uuidd):
            for user in self.controls.vk_service.get_result('getProfiles', 'uids=' + uuidd):
                def task(user):
                    logging.debug(user)
                    name = user['first_name'] + " " + user['last_name']

                    parent = FModel(name)
                    parent.user_id = user['uid']
                    bean = FDModel(_("loading...")).parent(parent).add_is_file(True)
                    self.append(parent)
                    self.append(bean)
                GLib.idle_add(task, user)

        if not FC().user_id and not self.controls.vk_service.auth():
            return
        get_users_by_uuid(FC().user_id)

        uids = self.controls.vk_service.get_result('friends.get', 'uid=' + FC().user_id)
        if uids:
            get_users_by_uuid(",".join(["%s" % i for i in uids]))

        self.lazy = True

    def on_button_press(self, w, e):
        if is_empty_click(w, e):
            w.get_selection().unselect_all()
        if is_rigth_click(e):
            right_click_optimization_for_trees(w, e)
            active = self.get_selected_bean()
            if active:
                self.tree_menu.clear()
                if isinstance(active, FModel) and active.path:
                    self.tree_menu.add_item(_('Play'), Gtk.STOCK_MEDIA_PLAY, self.controls.play, active)
                self.tree_menu.add_item(_('Copy to Search Line'), Gtk.STOCK_COPY, self.controls.searchPanel.set_search_text, active.text)
                self.tree_menu.show(e)

        if is_double_left_click(e):
            selected = self.get_selected_bean()
            if not selected:
                return

            def task():
                if (selected.user_id not in self.cache) and (not selected.is_file):
                    beans = self.get_user_tracks_as_beans(selected.user_id)
                else:
                    beans = self.get_all_child_beans_by_selected()
                self.controls.notetabs.append_tab(selected.text, [selected] + beans, optimization=True)
                self.controls.play_first_file_in_playlist()

            self.controls.in_thread.run_with_progressbar(task)

    def on_row_expanded(self, widget, iter, path):
        self.on_bean_expanded(iter)

    def get_user_tracks_as_beans(self, user_id):
        beans = []
        result = self.controls.vk_service.get_result('audio.get', "uid=" + user_id)
        if not result:
            beans = [FDModel(_("No results found")).add_is_file(True)]
        else:
            for line in result:
                bean = FModel(line['artist'] + ' - ' + line['title'])
                bean.aritst = line['artist']
                bean.title = line['title']
                bean.time = convert_seconds_to_text(line['duration'])
                bean.path = line['url']
                bean.aid = line['aid']
                bean.oid = line['owner_id']
                bean.is_file = True
                bean.vk_audio_id = "%s_%s" % (line['owner_id'], line['aid'])
                beans.append(bean)
        return beans

    def on_bean_expanded(self, parent_iter):
        logging.debug("expanded %s" % parent_iter)

        p_iter = self.get_model().convert_iter_to_child_iter(parent_iter)
        parent = self.get_bean_from_iter(p_iter)

        if parent.user_id in self.cache:
            return None

        self.cache.append(parent.user_id)

        old_iters = self.get_child_iters_by_parent(self.model, p_iter)

        def task():
            beans = self.get_user_tracks_as_beans(parent.user_id)

            def safe():
                for bean in beans:
                    bean.parent(parent)
                    row = self.get_row_from_bean(bean)
                    self.model.append(p_iter, row)

                for rem in old_iters:
                    self.model.remove(rem)
            GLib.idle_add(safe)

        self.controls.in_thread.run_with_progressbar(task)

########NEW FILE########
__FILENAME__ = window
#-*- coding: utf-8 -*-
'''
Created on 25 сент. 2010

@author: ivan
'''

import logging

from gi.repository import Gtk
from gi.repository import Gdk

from foobnix.fc.fc import FC
from foobnix.gui.service.path_service import get_foobnix_resourse_path_by_name
from foobnix.util import const
from foobnix.gui.state import LoadSave
from foobnix.version import FOOBNIX_VERSION
from foobnix.gui.model.signal import FControl
from foobnix.util.key_utils import is_key, is_key_alt, is_key_control


class MainWindow(Gtk.Window, FControl, LoadSave):
    def __init__(self, controls):
        FControl.__init__(self, controls)
        Gtk.Window.__init__(self, Gtk.WindowType.TOPLEVEL)

        self.set_title("Foobnix " + FOOBNIX_VERSION)
        self.set_position(Gtk.WindowPosition.CENTER)
        self.set_resizable(True)
        self.connect("window-state-event", self.on_change_state)
        self.connect("delete-event", self.hide_window)
        self.connect("key-press-event", self.on_key_press)
        try:
            self.set_icon_from_file(get_foobnix_resourse_path_by_name(const.ICON_FOOBNIX))
        except TypeError as e:
            logging.error(str(e))

        self.set_opacity(FC().window_opacity)
        self.iconified = False

    def on_key_press(self, w, e):
        if is_key(e, 'Escape'):
            self.hide_window()
        elif is_key(e, 'space') and not isinstance(self.get_focus(), Gtk.Entry):
            self.controls.play_pause()
        elif is_key_alt(e) and is_key(e, "1"):
            self.controls.perspectives.activate_perspective("fs")
        elif is_key_alt(e) and is_key(e, "2"):
            self.controls.perspectives.activate_perspective("radio")
        elif is_key_alt(e) and is_key(e, "3"):
            self.controls.perspectives.activate_perspective("storage")
        elif is_key_alt(e) and is_key(e, "4"):
            self.controls.perspectives.activate_perspective("info")
        elif is_key_control(e) and (is_key(e, "q") or is_key(e, "Cyrillic_shorti")):
            self.controls.quit()
        elif is_key_control(e) and (is_key(e, "s") or is_key(e, "Cyrillic_yeru")):
            self.controls.notetabs.on_save_playlist(self.controls.notetabs.get_current_tree().scroll)

    def on_save(self, *a):
        pass

    def on_load(self):
        cfg = FC().main_window_size
        if cfg:
            self.resize(cfg[2], cfg[3])
            self.move(cfg[0], cfg[1])
        if FC().window_maximized:
            self.maximize()

    def show_hide(self):
        visible = self.get_property('visible')
        if visible:
            self.hide()
        else:
            self.show()

    def hide_window(self, *args):
        if FC().on_close_window == const.ON_CLOSE_CLOSE:
            self.controls.quit()

        elif FC().on_close_window == const.ON_CLOSE_HIDE:
            self.hide()

        elif FC().on_close_window == const.ON_CLOSE_MINIMIZE:
            self.iconify()

        logging.debug("On close window action %s" % FC().on_close_window)

        return True

    def on_change_state(self, w, e):
        if int(e.new_window_state) == 0:
            """window restored"""
            self.iconified = False
            FC().window_maximized = False

        elif e.new_window_state & Gdk.WindowState.ICONIFIED:#@UndefinedVariable
            """minimized"""
            self.iconified = True
            FC().window_maximized = False

        elif e.new_window_state & Gdk.WindowState.MAXIMIZED:#@UndefinedVariable
            """maximized"""
            self.iconified = False
            FC().window_maximized = True

########NEW FILE########
__FILENAME__ = dialog_entry
#-*- coding: utf-8 -*-
'''
Created on 24 авг. 2010

@author: ivan
'''
from gi.repository import Gtk
import logging

from foobnix.fc.fc import FC
from foobnix.helpers.image import ImageBase
from foobnix.util.const import SITE_LOCALE, ICON_FOOBNIX
from foobnix.util.localization import foobnix_localization
from foobnix.gui.service.path_service import get_foobnix_resourse_path_by_name

foobnix_localization()

def responseToDialog(entry, dialog, response):
        dialog.response(response)

def file_selection_dialog(title, current_folder=None):
    chooser = Gtk.FileSelection(title)
    chooser.set_icon_from_file(get_foobnix_resourse_path_by_name(ICON_FOOBNIX))
    chooser.set_default_response(Gtk.ResponseType.OK)
    chooser.set_select_multiple(True)
    paths = None
    if current_folder:
        chooser.set_current_folder(current_folder)
    response = chooser.run()
    if response == Gtk.ResponseType.OK:
        paths = chooser.get_selections()
    elif response == Gtk.ResponseType.CANCEL:
        logging.info('Closed, no files selected')
    chooser.destroy()
    return paths

def file_chooser_dialog(title, current_folder=None):
    chooser = Gtk.FileChooserDialog(title, action=Gtk.FILE_CHOOSER_ACTION_OPEN, buttons=(Gtk.STOCK_OPEN, Gtk.ResponseType.OK))
    chooser.set_icon_from_file(get_foobnix_resourse_path_by_name(ICON_FOOBNIX))
    chooser.set_default_response(Gtk.ResponseType.OK)
    chooser.set_select_multiple(True)
    paths = None
    if current_folder:
        chooser.set_current_folder(current_folder)
    response = chooser.run()
    if response == Gtk.ResponseType.OK:
        paths = chooser.get_filenames()
    elif response == Gtk.ResponseType.CANCEL:
        logging.info('Closed, no files selected')
    chooser.destroy()
    return paths

def directory_chooser_dialog(title, current_folder=None):
    chooser = Gtk.FileChooserDialog(title, action=Gtk.FileChooserAction.SELECT_FOLDER, buttons=(Gtk.STOCK_OPEN, Gtk.ResponseType.OK))
    chooser.set_default_response(Gtk.ResponseType.OK)
    chooser.set_select_multiple(True)
    paths = None
    if current_folder:
        chooser.set_current_folder(current_folder)
    response = chooser.run()
    if response == Gtk.ResponseType.OK:
        paths = chooser.get_filenames()
    elif response == Gtk.ResponseType.CANCEL:
        logging.info('Closed, no directory selected')
    chooser.destroy()
    return paths

def one_line_dialog(dialog_title, parent=None, entry_text=None, message_text1=None, message_text2=None):
        dialog = Gtk.MessageDialog(
            parent,
            Gtk.DialogFlags.MODAL | Gtk.DialogFlags.DESTROY_WITH_PARENT,
            Gtk.MessageType.INFO,
            Gtk.ButtonsType.OK,
            None)
        dialog.set_icon_from_file(get_foobnix_resourse_path_by_name(ICON_FOOBNIX))
        dialog.set_title(dialog_title)
        if message_text1:
            dialog.set_markup(message_text1)
        if message_text2:
            dialog.format_secondary_markup(message_text2)


        entry = Gtk.Entry()

        '''set last widget in action area as default widget (button OK)'''
        dialog.set_default_response(Gtk.ResponseType.OK)

        '''activate default widget after Enter pressed in entry'''
        entry.set_activates_default(True)

        if entry_text:
            entry.set_text(entry_text)
        dialog.vbox.pack_start(entry, True, True, 0)
        dialog.show_all()

        dialog.run()
        text = entry.get_text()

        dialog.destroy()
        return text if text else None

def two_line_dialog(dialog_title, parent=None, message_text1=None,
                    message_text2=None, entry_text1="", entry_text2=""):
        dialog = Gtk.MessageDialog(
            parent,
            Gtk.DialogFlags.MODAL | Gtk.DialogFlags.DESTROY_WITH_PARENT,
            Gtk.MessageType.QUESTION,
            Gtk.ButtonsType.OK,
            None)
        dialog.set_icon_from_file(get_foobnix_resourse_path_by_name(ICON_FOOBNIX))
        dialog.set_title(dialog_title)
        if message_text1:
            dialog.set_markup(message_text1)
        if message_text2:
            dialog.format_secondary_markup(message_text2)

        login_entry = Gtk.Entry()
        if entry_text1:
            login_entry.set_text(entry_text1)
        login_entry.show()

        password_entry = Gtk.Entry()
        if entry_text2:
            password_entry.set_text(entry_text2)
        password_entry.show()

        hbox = Gtk.VBox()
        hbox.pack_start(login_entry, False, False, 0)
        hbox.pack_start(password_entry, False, False, 0)
        dialog.vbox.pack_start(hbox, True, True, 0)
        dialog.show_all()

        '''set last widget in action area as default widget (button OK)'''
        dialog.set_default_response(Gtk.ResponseType.OK)

        '''activate default widget after Enter pressed in entry'''
        login_entry.set_activates_default(True)
        password_entry.set_activates_default(True)

        dialog.run()
        login_text = login_entry.get_text()
        password_text = password_entry.get_text()
        dialog.destroy()
        return [login_text, password_text] if (login_text and password_text) else [None,None]

def info_dialog(title, message, parent=None):
        dialog = Gtk.MessageDialog(
            parent,
            Gtk.DialogFlags.MODAL | Gtk.DialogFlags.DESTROY_WITH_PARENT,
            Gtk.MessageType.INFO,
            Gtk.ButtonsType.OK,
            None)
        dialog.set_icon_from_file(get_foobnix_resourse_path_by_name(ICON_FOOBNIX))
        dialog.set_title(title)
        dialog.set_markup(title)
        dialog.format_secondary_markup(message)
        dialog.show_all()
        dialog.run()
        dialog.destroy()

def info_dialog_with_link(title, version, link):
        dialog = Gtk.MessageDialog(
            None,
            Gtk.DialogFlags.MODAL | Gtk.DialogFlags.DESTROY_WITH_PARENT,
            Gtk.MessageType.INFO,
            Gtk.ButtonsType.OK,
            None)
        dialog.set_icon_from_file(get_foobnix_resourse_path_by_name(ICON_FOOBNIX))
        dialog.set_title(title)
        dialog.set_markup(title)
        dialog.format_secondary_markup("<b>" + version + "</b>")
        link = Gtk.LinkButton(link, link)
        link.show()
        dialog.vbox.pack_end(link, True, True, 0)
        dialog.show_all()
        dialog.run()
        dialog.destroy()

def info_dialog_with_link_and_donate(version):
        dialog = Gtk.MessageDialog(
            None,
            Gtk.DialogFlags.MODAL | Gtk.DialogFlags.DESTROY_WITH_PARENT,
            Gtk.MessageType.INFO,
            Gtk.ButtonsType.OK,
            None)
        dialog.set_icon_from_file(get_foobnix_resourse_path_by_name(ICON_FOOBNIX))
        dialog.set_title(_("New foobnix release avaliable"))
        dialog.set_markup(_("New foobnix release avaliable"))
        dialog.format_secondary_markup("<b>" + version + "</b>")



        card = Gtk.LinkButton("http://www.foobnix.com/support?lang=%s"%SITE_LOCALE, _("Download and Donate"))
        #terminal = Gtk.LinkButton("http://www.foobnix.com/donate/eng#terminal", _("Download and Donate by Webmoney or Payment Terminal"))
        link = Gtk.LinkButton("http://www.foobnix.com/support?lang=%s"%SITE_LOCALE, _("Download"))

        frame = Gtk.Frame(label="Please donate and download")
        vbox = Gtk.VBox(True, 0)
        vbox.pack_start(card, True, True)
        #vbox.pack_start(terminal, True, True)
        vbox.pack_start(link, True, True)
        frame.add(vbox)

        image = ImageBase("images/foobnix-slogan.jpg")

        dialog.vbox.pack_start(image, True, True)
        dialog.vbox.pack_start(frame, True, True)
        dialog.vbox.pack_start(Gtk.Label(_("We hope you like the player. We will make it even better.")), True, True)
        version_check = Gtk.CheckButton(_("Check for new foobnix release on start"))
        version_check.set_active(FC().check_new_version)
        dialog.vbox.pack_start(version_check, True, True)

        dialog.show_all()
        dialog.run()

        FC().check_new_version = version_check.get_active()
        FC().save()
        dialog.destroy()


def show_entry_dialog(title, description):
        dialog = Gtk.MessageDialog(
            None,
            Gtk.DialogFlags.MODAL | Gtk.DialogFlags.DESTROY_WITH_PARENT,
            Gtk.MessageType.QUESTION,
            Gtk.ButtonsType.OK,
            None)
        dialog.set_icon_from_file(get_foobnix_resourse_path_by_name(ICON_FOOBNIX))
        dialog.set_markup(title)
        entry = Gtk.Entry()
        entry.connect("activate", responseToDialog, dialog, Gtk.ResponseType.OK)
        hbox = Gtk.HBox()
        hbox.pack_start(Gtk.Label("Value:"), False, 5, 5)
        hbox.pack_end(entry)
        dialog.format_secondary_markup(description)
        dialog.vbox.pack_end(hbox, True, True, 0)
        dialog.show_all()
        dialog.run()
        text = entry.get_text()
        dialog.destroy()
        return text

def show_login_password_error_dialog(title, description, login, password):
        dialog = Gtk.MessageDialog(
            None,
            Gtk.DialogFlags.MODAL | Gtk.DialogFlags.DESTROY_WITH_PARENT,
            Gtk.MessageType.ERROR,
            Gtk.ButtonsType.OK,
            title)
        dialog.set_icon_from_file(get_foobnix_resourse_path_by_name(ICON_FOOBNIX))
        dialog.set_markup(str(title))
        dialog.format_secondary_markup(description)

        login_entry = Gtk.Entry()
        login_entry.set_text(login)
        login_entry.show()

        password_entry = Gtk.Entry()
        password_entry.set_text(password)
        password_entry.set_visibility(False)
        password_entry.set_invisible_char("*")
        password_entry.show()

        hbox = Gtk.VBox()
        hbox.pack_start(login_entry, False, False, 0)
        hbox.pack_start(password_entry, False, False, 0)
        dialog.vbox.pack_start(hbox, True, True, 0)
        dialog.show_all()
        dialog.run()
        login_text = login_entry.get_text()
        password_text = password_entry.get_text()
        dialog.destroy()
        return [login_text, password_text]

def file_saving_dialog(title, current_folder=None):
    chooser = Gtk.FileChooserDialog(title, action=Gtk.FileChooserAction.SAVE, buttons=(Gtk.STOCK_SAVE, Gtk.ResponseType.OK))
    chooser.set_icon_from_file(get_foobnix_resourse_path_by_name(ICON_FOOBNIX))
    chooser.set_default_response(Gtk.ResponseType.OK)
    chooser.set_select_multiple(False)
    if current_folder:
        chooser.set_current_folder(current_folder)
    response = chooser.run()
    if response == Gtk.ResponseType.OK:
        paths = chooser.get_filenames()
    elif response == Gtk.ResponseType.CANCEL:
        logging.info('Closed, no files selected')
    chooser.destroy()

class FileSavingDialog(Gtk.FileChooserDialog):
    def __init__(self, title, func, args = None, current_folder=None, current_name=None):
        Gtk.FileChooserDialog.__init__(self, title, action=Gtk.FileChooserAction.SAVE, buttons=(Gtk.STOCK_SAVE, Gtk.ResponseType.OK))
        self.set_default_response(Gtk.ResponseType.OK)
        self.set_select_multiple(False)
        self.set_do_overwrite_confirmation(True)
        self.set_icon_from_file(get_foobnix_resourse_path_by_name(ICON_FOOBNIX))
        if current_folder:
            self.set_current_folder(current_folder)
        if current_name:
            self.set_current_name(current_name)

        response = self.run()
        if response == Gtk.ResponseType.OK:
            filename = self.get_filename()
            folder = self.get_current_folder()
            if func:
                try:
                    if args: func(filename, folder, args)
                    else: func(filename, folder)
                except IOError, e:
                        logging.error(e)
        elif response == Gtk.ResponseType.CANCEL:
            logging.info('Closed, no files selected')
        self.destroy()

if __name__ == '__main__':
        info_dialog_with_link_and_donate("foobnix 0.2.1-8")
        Gtk.main()


########NEW FILE########
__FILENAME__ = image
'''
Created on Sep 28, 2010

@author: ivan
'''

import logging
import os

from gi.repository import Gtk

from foobnix.util import idle_task
from foobnix.util.pix_buffer import create_pixbuf_from_resource, \
    create_pixbuf_from_url, create_pixbuf_from_path, resize_pixbuf


class ImageBase(Gtk.Image):
    def __init__(self, resource, size=None):
        Gtk.Image.__init__(self)
        self.resource = resource
        self.size = size
        self.pixbuf = create_pixbuf_from_resource(self.resource, self.size)

    @idle_task
    def set_no_image(self):
        self.pixbuf = create_pixbuf_from_resource(self.resource, self.size)
        self.set_from_pixbuf(self.pixbuf)

    @idle_task
    def set_from_resource(self, resource_name):
        self.pixbuf = create_pixbuf_from_resource(resource_name, self.size)
        self.set_from_pixbuf(self.pixbuf)

    @idle_task
    def set_from_pixbuf(self, pix):
        self.pixbuf = resize_pixbuf(pix, self.size)
        super(ImageBase, self).set_from_pixbuf(self.pixbuf)

    @idle_task
    def set_image_from_url(self, url):
        self.pixbuf = create_pixbuf_from_url(url, self.size)
        self.set_from_pixbuf(self.pixbuf)

    @idle_task
    def set_image_from_path(self, path):
        if not os.path.isfile(path):
            return self.set_from_resource(path)

        logging.debug("Change icon path %s" % path)
        self.pixbuf = create_pixbuf_from_path(path, self.size)
        self.set_from_pixbuf(self.pixbuf)

    def get_pixbuf(self):
        return self.pixbuf

    def update_info_from(self, bean):
        if not bean or not bean.image:
            self.set_no_image()
            return
        if bean.image.startswith("http://"):
            self.set_image_from_url(bean.image)
        else:
            self.set_image_from_path(bean.image)

########NEW FILE########
__FILENAME__ = menu
'''
Created on Aug 26, 2010

@author: ivan
'''
from gi.repository import Gtk
import time
from foobnix.gui.menu import MyMenu
class Popup(Gtk.Menu):

    def __init__(self, *args, **kwargs):
        Gtk.Menu.__init__(self, *args, **kwargs)

    def add_separator(self):
        separator = Gtk.SeparatorMenuItem.new()
        separator.show()
        self.append(separator)

    def add_item(self, text, gtk_stock="", func=None, arg=None):
        item = Gtk.ImageMenuItem(text)
        if gtk_stock:
            img = Gtk.Image.new_from_stock(gtk_stock, Gtk.IconSize.MENU)
            item.set_image(img)
        if func and arg:
            item.connect("activate", lambda * a: func(arg))
        elif func:
            item.connect("activate", lambda * a: func())
        self.add(item)
        item.show()
        return item

    def add_image_item(self, title, gtk_stock, func=None, param=None):
        item = Gtk.ImageMenuItem(title)

        item.show()
        if gtk_stock:
            img = Gtk.Image.new_from_stock(gtk_stock, Gtk.IconSize.MENU)
            item.set_image(img)

        if func and param:
            item.connect("activate", lambda * a: func(param))
        elif func:
            item.connect("activate", lambda * a: func())

        self.append(item)
        return item

    def show(self, event):
        self.show_all()
        self.popup(None, None, lambda menu, data: (event.get_root_coords()[0], event.get_root_coords()[1], True), None, event.button, event.time)

    def show_widget(self, w):
        self.show_all()
        self.popup(None, None, None, 3, long(time.time()))

    def add_submenu(self, title):
        menu = MyMenu()
        menu.show()

        file_item = Gtk.MenuItem(title)
        file_item.show()

        file_item.set_submenu(menu)
        self.append(file_item)
        return menu

    def clear(self):
        for w in self.get_children():
            self.remove(w)
            w.destroy()

########NEW FILE########
__FILENAME__ = my_widgets
#-*- coding: utf-8 -*-
'''
Created on 30 авг. 2010

@author: ivan
'''

from gi.repository import Gtk
from gi.repository import Gdk

from foobnix.fc.fc import FC
from foobnix.helpers.pref_widgets import HBoxDecorator


def open_link_in_browser(uri):
    link = Gtk.LinkButton(uri)
    link.clicked()

class PerspectiveButton(Gtk.ToggleButton):
    def __init__(self, title, gtk_stock, tooltip=None):
        Gtk.ToggleButton.__init__(self, title)
        if not tooltip:
            tooltip = title

        self.set_tooltip_text(tooltip)

        self.set_relief(Gtk.ReliefStyle.NONE)
        label = self.get_child()
        if label:
            self.remove(label)

        vbox = Gtk.VBox(False, 0)
        img = Gtk.Image.new_from_stock(gtk_stock, Gtk.IconSize.MENU)
        vbox.add(img)
        vbox.add(Gtk.Label(title))
        vbox.show_all()

        self.add(vbox)

class ButtonStockText(Gtk.Button):
    def __init__(self, title, gtk_stock, tooltip=None):
        Gtk.Button.__init__(self, "")
        if not tooltip:
            tooltip = title

        self.set_tooltip_text(tooltip)

        label = self.get_child()
        self.remove(label)

        box = Gtk.HBox(False, 0)
        img = Gtk.Image.new_from_stock(gtk_stock, Gtk.IconSize.MENU)
        box.add(img)
        box.add(Gtk.Label(title))
        box.show_all()

        alignment = Gtk.Alignment(xalign=0.5)
        #alignment.set_padding(padding_top=0, padding_bottom=0, padding_left=10, padding_right=10)
        alignment.add(box)

        self.add(alignment)

class InsensetiveImageButton(Gtk.EventBox):
    def __init__(self, stock_image, size=Gtk.IconSize.LARGE_TOOLBAR):
        Gtk.EventBox.__init__(self)
        self.button = Gtk.Button()
        #self.button.set_sensitive(False)
        self.button.set_focus_on_click(False)
        self.button.set_relief(Gtk.ReliefStyle.NONE)
        img = Gtk.Image.new_from_stock(stock_image, size)
        self.button.set_image(img)
        self.add(HBoxDecorator(self.button, Gtk.Label("R")))

        #self.button.modify_bg(Gtk.StateType.NORMAL, Gdk.color_parse("red"))

        self.connect("button-press-event", self.on_click)
        self.button.connect("button-press-event", self.on_click1)

        self.insensetive = False

    def on_click1(self, *a):
        pass

    def on_click(self, *a):
        self.insensetive = not self.insensetive
        #self.button.set_sensitive(self.insensetive)

class ImageButton(Gtk.Button):
    def __init__(self, stock_image, func=None, tooltip_text=None, size=Gtk.IconSize.LARGE_TOOLBAR):
        Gtk.Button.__init__(self)
        self.set_relief(Gtk.ReliefStyle.NONE)
        self.set_focus_on_click(False)
        if tooltip_text:
            self.set_tooltip_text(tooltip_text)
        img = Gtk.Image.new_from_stock(stock_image, size)
        self.set_image(img)
        if func:
            self.connect("clicked", lambda * a: func())


class ToggleImageButton(Gtk.ToggleButton):
    def __init__(self, gtk_stock, func=None, param=None):
        Gtk.ToggleButton.__init__(self)
        self.set_relief(Gtk.ReliefStyle.NONE)
        self.set_focus_on_click(False)
        if param and func:
            self.connect("toggled", lambda * a: func(param))
        elif func:
            self.connect("toggled", lambda * a: func())

        img = Gtk.Image.new_from_stock(gtk_stock, Gtk.IconSize.MENU)
        self.add(img)

class ToggleWidgetButton(Gtk.ToggleButton):
    def __init__(self, widget, func=None, param=None):
        Gtk.ToggleButton.__init__(self)

        if param and func:
            self.connect("toggled", lambda * a: func(param))
        elif func:
            self.connect("toggled", lambda * a: func())

        self.set_relief(Gtk.ReliefStyle.NONE)
        self.add(widget)


def tab_close_button(func=None, arg=None, stock=Gtk.STOCK_CLOSE):
    """button"""
    button = Gtk.Button()
    button.set_relief(Gtk.ReliefStyle.NONE)
    img = Gtk.Image.new_from_stock(stock, Gtk.IconSize.MENU)
    button.set_image(img)
    if func and arg:
        button.connect("button-press-event", lambda * a: func(arg))
    elif func:
        button.connect("button-press-event", lambda * a: func())
    button.show()
    return button



class EventLabel(Gtk.EventBox):
    def __init__(self, text="×", angle=0, func=None, arg=None, func1=None):
        Gtk.EventBox.__init__(self)
        self.text = text
        self.set_visible_window(False)
        self.selected = False

        self.label = Gtk.Label()
        self.set_not_underline()

        self.label.set_angle(angle)

        self.connect("enter-notify-event", lambda * a : self.set_underline())
        self.connect("leave-notify-event", lambda * a: self.set_not_underline())
        if func and arg:
            self.connect("button-press-event", lambda * a: func(arg))
        elif func:
            self.connect("button-press-event", lambda * a: func())

        self.func1 = func1

        self.add(self.label)
        self.show_all()

    def set_markup(self, text):
        self.text = text
        self.label.set_markup(text)

    def set_underline(self):
        if self.selected:
            self.label.set_markup("<b><u>" + self.text + "</u></b>")
        else:
            self.label.set_markup("<u>" + self.text + "</u>")

    def set_not_underline(self):
        if self.selected:
            self.label.set_markup("<b>" + self.text + "</b>")
        else:
            self.label.set_markup(self.text)

    def set_active(self):
        self.selected = True
        self.set_underline()

    def set_not_active(self):
        self.selected = False
        self.set_not_underline()

def notetab_label(func=None, arg=None, angle=0, symbol="×"):
    """label"""
    label = Gtk.Label(symbol)
    label.show()
    label.set_angle(angle)

    event = Gtk.EventBox()
    event.show()
    event.add(label)
    event.set_visible_window(False)

    event.connect("enter-notify-event", lambda w, e:w.get_child().set_markup("<u>" + symbol + "</u>"))
    event.connect("leave-notify-event", lambda w, e:w.get_child().set_markup(symbol))
    if func and arg:
        event.connect("button-press-event", lambda * a: func(arg))
    elif func:
        event.connect("button-press-event", lambda * a: func())
    event.show()
    return event

class AlternateVolumeControl (Gtk.DrawingArea):
    def __init__(self, levels, s_width, interval, v_step):
        Gtk.DrawingArea.__init__(self)
        self.show()
        self.volume = FC().volume
        self.connect("draw", self.draw_callback, levels, s_width, interval, v_step)

    def set_volume (self, vol):
        self.volume = vol
        self.queue_draw()

    def draw_callback(self, w, cr, levels, s_width, interval, v_step):
        #levels = a number of volume levels (a number of sticks equals level-1)
        #s_width - width of stick
        #interval - interval between sticks
        #v_step - increase the height of the stick
        #all parameters must be integer type

        area_width = w.get_allocation().width
        area_height = w.get_allocation().height

        h_step = s_width + interval
        width = levels * (s_width + interval) - interval
        height = v_step * (levels - 1)

        if width < area_width:
            start_x = (area_width-width)/2
        else:
            start_x = 1

        if height < area_height:
            start_y = area_height - (area_height - height)/2
        else:
            start_y = 0

        x = start_x
        y = start_y - 1

        label = FC().volume * width/100.0 + start_x

        i = 0
        while i < levels:
            color = Gdk.color_parse("orange red") if x  < label else Gdk.color_parse("white")
            Gdk.cairo_set_source_color(cr, color)

            cr.move_to(x, start_y)
            cr.line_to(x+s_width, start_y)
            cr.line_to(x+s_width, y)
            cr.line_to(x, y)
            #cr.close_path()
            cr.fill()

            i += 1
            x += h_step
            y -= v_step




########NEW FILE########
__FILENAME__ = pref_widgets
'''
Created on Nov 5, 2010

@author: ivan
'''

import logging

from gi.repository import Gtk
from gi.repository import GObject

from foobnix.fc.fc import FC
from foobnix.helpers.dialog_entry import file_chooser_dialog
from foobnix.util.pix_buffer import create_pixbuf_from_resource
from foobnix.helpers.window import ChildTopWindow


class IconBlock(Gtk.HBox):

    temp_list = FC().all_icons[:]

    def __init__(self, text, controls, filename, all_icons=temp_list):
        Gtk.HBox.__init__(self, False, 0)

        self.controls = controls

        self.combobox = Gtk.ComboBox()
        self.entry = Gtk.Entry()
        self.entry.set_size_request(300, -1)
        self.entry.set_property("margin", 0)
        if filename:
            self.entry.set_text(filename)
        else:
            filename = ""

        self.all_icons = all_icons

        self.modconst = ModelConstructor(all_icons)

        self.combobox.set_model(self.modconst.model)

        if filename in self.all_icons:
            self.combobox.set_active(self.all_icons.index(filename))
        else:
            self.combobox.set_active(0)
            self.on_change_icon()
            logging.warning("Icon " + filename + " is absent in list of icons")

        pix_render = Gtk.CellRendererPixbuf()
        self.combobox.pack_start(pix_render, 0)
        self.combobox.add_attribute(pix_render, 'pixbuf', 0)

        button = Gtk.Button("Choose", Gtk.STOCK_OPEN)
        button.connect("clicked", self.on_file_choose)

        button_2 = Gtk.Button("Delete", Gtk.STOCK_DELETE)
        button_2.connect("clicked", self.on_delete)

        label = Gtk.Label(text)
        if text: # if iconblock without label
            label.set_size_request(80, -1)

        self.pack_start(label, False, False, 0)
        self.pack_start(self.combobox, False, False, 0)
        self.pack_start(self.entry, True, True, 0)
        self.pack_start(button, False, False, 0)
        self.pack_start(button_2, False, False, 0)

        self.combobox.connect("changed", self.on_change_icon)

    def on_file_choose(self, *a):
        file = file_chooser_dialog("Choose icon")
        if not file:
            return None
        self.entry.set_text(file[0])
        self.modconst.apeend_icon(self, file[0], True)
        self.all_icons.append(file[0])

    def on_change_icon(self, *a):
        active_id = self.combobox.get_active()
        if active_id >= 0:
            icon_name = self.combobox.get_model()[active_id][1]
            self.entry.set_text(icon_name)
        #FC().static_tray_icon = True
        #self.controls.trayicon.on_dynamic_icons(None)

    def get_active_path(self):
        active_id = self.combobox.get_active()
        return self.combobox.get_model()[active_id][1]

    def on_delete(self, *a):
        active_id = self.combobox.get_active()
        rem_icon = self.entry.get_text()
        iter = self.modconst.model.get_iter(active_id)
        try:
            if self.all_icons.index(rem_icon) > 4:
                self.all_icons.remove(rem_icon)
                self.modconst.delete_icon(iter)
                self.combobox.set_active(0)
            else:
                error_window = ChildTopWindow("Error")
                label = Gtk.Label("You can not remove a standard icon")
                error_window.add(label)
                error_window.show()
        except ValueError, e:
            logging.error("There is not such icon in the list" + str(e))

class FrameDecorator(Gtk.Frame):
    def __init__(self, text, widget):
        Gtk.Frame.__init__(self, label=text)
        self.add(widget)

class ChooseDecorator(Gtk.HBox):
    def __init__(self, parent, widget):
        Gtk.HBox.__init__(self, False, 0)
        self._widget = widget
        self.button = Gtk.RadioButton.new_from_widget(parent)

        self.on_toggle()
        self.button.connect("toggled", self.on_toggle)
        box = HBoxDecorator(self.button, self._widget)
        self.pack_start(box, False, True, 0)

    def on_toggle(self, *a):
        if self.button.get_active():
            self._widget.set_sensitive(True)
        else:
            self._widget.set_sensitive(False)

    def get_radio_button(self):
        return self.button

class VBoxDecorator(Gtk.VBox):
    def __init__(self, *args):
        Gtk.VBox.__init__(self, False, 0)
        for widget in args:
            self.pack_start(widget, False, False, 0)
        self.show_all()

class HBoxDecorator(Gtk.HBox):
    def __init__(self, *args):
        Gtk.HBox.__init__(self, False, 0)
        for widget in args:
            self.pack_start(widget, False, False, 0)
        self.show_all()

class HBoxDecoratorTrue(Gtk.HBox):
    def __init__(self, *args):
        Gtk.HBox.__init__(self, False, 0)
        for widget in args:
            self.pack_start(widget, True, True, 0)
        self.show_all()


class HBoxLableEntry(Gtk.HBox):
    def __init__(self, text, entry):
        Gtk.HBox.__init__(self, False, 0)
        self.pack_start(text, False, False, 0)
        self.pack_start(entry, True, True, 0)
        self.show_all()

class ModelConstructor():

    ICON_SIZE = 24

    def __init__(self, all_icons):

        self.model = Gtk.ListStore(GObject.TYPE_OBJECT, str)

        for icon_name in all_icons:
            self.apeend_icon(None, icon_name)

    def apeend_icon(self, calling_object, icon_name, active=False):
        pixbuf = create_pixbuf_from_resource(icon_name, self.ICON_SIZE)
        if pixbuf:
            self.model.append([pixbuf, icon_name])
            if active:
                calling_object.combobox.set_active(len(self.model) - 1)

    def delete_icon(self, iter):
        self.model.remove(iter)

########NEW FILE########
__FILENAME__ = textarea
'''
Created on Oct 29, 2010

@author: ivan
'''

import pango

from gi.repository import Gtk

from foobnix.helpers.image import ImageBase
from foobnix.util import idle_task


class TextArea(Gtk.ScrolledWindow):
    def __init__(self):
        Gtk.ScrolledWindow.__init__(self)

        texttagtable = Gtk.TextTagTable()
        self.buffer = Gtk.TextBuffer.new(texttagtable)

        self.tag_bold = Gtk.TextTag(name="bold")
        self.tag_bold.set_property("weight", pango.WEIGHT_BOLD)

        texttagtable.add(self.tag_bold)

        text = Gtk.TextView(buffer=self.buffer)
        text.set_wrap_mode(Gtk.WrapMode.WORD)
        text.set_editable(False)

        self.set_policy(Gtk.PolicyType.AUTOMATIC, Gtk.PolicyType.AUTOMATIC)
        self.add(text)

        self.scroll = self
        self.line_title = None

    @idle_task
    def append_image(self, url):
        if not url:
            return None
        enditer = self.buffer.get_end_iter()
        image = ImageBase(None)
        image.set_image_from_url(url)
        self.buffer.insert_pixbuf(enditer, image.get_pixbuf())

    @idle_task
    def set_text(self, text="", bold_text=""):
        if not text:
            text = ""
        if not bold_text:
            bold_text = ""

        full_text = bold_text + "\n\n" + text + "\n"
        self.buffer.set_text(full_text)
        if text:
            self.clear_tags(full_text)
        start = self.buffer.get_iter_at_offset(0)
        end = self.buffer.get_iter_at_offset(len(unicode(bold_text)))
        self.buffer.apply_tag(self.tag_bold, start, end)

    def clear_tags(self, text):
        start_index = 0
        text_length = len(unicode(text))
        while start_index != -1:
            buf_text = self.buffer.get_text(self.buffer.get_iter_at_offset(0),
                                            self.buffer.get_iter_at_offset(text_length),
                                            False)
            start_index = buf_text.find("<")
            if start_index != -1:
                end_index = buf_text.find(">", start_index)
                if end_index != -1:
                    start = self.buffer.get_iter_at_offset(start_index)
                    end = self.buffer.get_iter_at_offset(end_index + 1)
                    self.buffer.delete(start, end)
                else:
                    return


class ScrolledText():
    def __init__(self):
        self.buffer = Gtk.TextBuffer()
        self.text = Gtk.TextView(buffer=self.buffer)
        self.text.set_editable(False)
        self.text.set_cursor_visible(False)
        self.scroll = Gtk.ScrolledWindow()
        self.scroll.set_policy(Gtk.PolicyType.AUTOMATIC, Gtk.PolicyType.AUTOMATIC)
        self.scroll.add(self.text)

########NEW FILE########
__FILENAME__ = toggled
'''
Created on Sep 23, 2010

@author: ivan
'''
class OneActiveToggledButton():
    def __init__(self, buttons):
        for button in buttons:
            button.connect("toggled", self.one_button_selected, buttons) 
    
    def one_button_selected(self, clicked_button, buttons):
        # so, the button becomes checked. Uncheck all other buttons
        for button in buttons:
            if button != clicked_button:
                button.set_active(False)    

        if all([not button.get_active() for button in buttons]):
            clicked_button.set_active(True)
            
        # if the button should become unchecked, then do nothing
        if not clicked_button.get_active():
            return
    


########NEW FILE########
__FILENAME__ = toolbar
'''
Created on Sep 27, 2010

@author: ivan
'''
from gi.repository import Gtk
import logging



class MyToolbar(Gtk.Toolbar):
    def __init__(self):
        rc_st = '''
        style "toolbar-style" {
            GtkToolbar::shadow_type = none
            }
        class "GtkToolbar" style "toolbar-style"
        '''
        Gtk.rc_parse_string(rc_st)

        Gtk.Toolbar.__init__(self)

        self.show()
        self.set_style(Gtk.ToolbarStyle.ICONS)
        self.set_show_arrow(False)
        self.set_icon_size(Gtk.IconSize.SMALL_TOOLBAR)

        self.i = 0

    def add_button(self, tooltip, gtk_stock, func, param):
        button = Gtk.ToolButton(gtk_stock)
        button.show()
        button.set_tooltip_text(tooltip)

        logging.debug("Button-Controls-Clicked" + str(tooltip)+ str(gtk_stock) + str(func) + str(param))
        if func and param:
            button.connect("clicked", lambda * a: func(param))
        elif func:
            button.connect("clicked", lambda * a: func())

        self.insert(button, self.i)
        self.i += 1

    def add_separator(self):
        sep = Gtk.SeparatorToolItem.new()
        sep.show()
        self.insert(sep, self.i)
        self.i += 1

class ToolbarSeparator(MyToolbar):
    def __init__(self):
        MyToolbar.__init__(self)
        self.add_separator()

########NEW FILE########
__FILENAME__ = tree
'''
Created on Sep 23, 2010

@author: ivan
'''
from gi.repository import Gtk
class ScrolledTreeView(Gtk.TreeView):
    def __init__(self, policy_horizontal, policy_vertical):
        Gtk.TreeView.__init__(self)
        scrool = Gtk.ScrolledWindow()
        scrool.set_policy(policy_horizontal, policy_vertical)
        scrool.add_with_viewport(self)
        scrool.show_all()
        
        
        
        
        
########NEW FILE########
__FILENAME__ = window
#-*- coding: utf-8 -*-
'''
Created on 27 окт. 2010

@author: ivan
'''

import os
from gi.repository import Gtk
import time
import logging
import threading

from foobnix.fc.fc import FC
from foobnix.util.key_utils import is_key
from foobnix.util.const import ICON_FOOBNIX
from foobnix.util.text_utils import split_string
from foobnix.util.file_utils import get_full_size
from foobnix.gui.service.path_service import get_foobnix_resourse_path_by_name


class ChildTopWindow(Gtk.Window):
    def __init__(self, title=None, width=None, height=None):
        Gtk.Window.__init__(self, Gtk.WindowType.TOPLEVEL)
        if title:
            self.set_title(title)

        self.set_position(Gtk.WindowPosition.CENTER)
        self.set_resizable(False)
        self.set_border_width(5)
        try:
            self.set_icon_from_file (self.get_fobnix_logo())
        except TypeError: pass
        if width and height:
            self.set_size_request(width, height)
        self.connect("delete-event", self.hide_window)
        self.connect("key-press-event", self.on_key_press)

        self.hide_on_escape = True
        self.set_opacity(FC().window_opacity)
        self.is_rendered = True

    def set_hide_on_escape(self, hide_on_escape=True):
        self.hide_on_escape = hide_on_escape

    def get_fobnix_logo(self):
        return get_foobnix_resourse_path_by_name(ICON_FOOBNIX)

    def on_key_press(self, w, e):
        if self.hide_on_escape and is_key(e, 'Escape'):
            self.hide()

    def hide_window(self, *a):
        self.hide()
        return True

    def show(self):
        self.show_all()

class CopyProgressWindow(Gtk.Dialog):
    def __init__(self, title, file_list, width=None, hight=None):
        Gtk.Dialog.__init__(self, title)
        if width and hight:
            self.set_default_size(width, hight)

        self.set_icon_from_file(get_foobnix_resourse_path_by_name(ICON_FOOBNIX))
        self.set_resizable(True)
        self.set_border_width(5)
        self.total_size = get_full_size(file_list)

        self.label_from = Gtk.Label()
        self.label_to = Gtk.Label()
        self.pr_label = Gtk.Label(_("Total progress"))

        self.pr_bar = Gtk.ProgressBar()
        self.total_pr_bar = Gtk.ProgressBar()

        self.add_button(_("Stop"), Gtk.ResponseType.REJECT)

        self.vbox.pack_start(self.label_from, False)
        self.vbox.pack_start(self.label_to, False)
        self.vbox.pack_start(self.pr_bar, False)
        self.vbox.pack_start(self.pr_label, False)
        self.vbox.pack_start(self.total_pr_bar, False)
        self.exit = False
        self.show_all()

    def progress(self, file, dest_folder):
        size = os.path.getsize(file)
        new_file = os.path.join(dest_folder, os.path.basename(file))
        counter = 0
        got_store = 0
        while True:
            if not os.path.exists(new_file):
                counter += 1
                time.sleep(0.1)
                if counter > 100:
                    logging.error("Can't create file %s" % new_file)
                    return
                continue

            got = os.path.getsize(new_file)
            definite = got - got_store
            got_store = got

            fraction = (got+0.0)/size
            self.pr_bar.set_fraction(fraction)
            self.pr_bar.set_text("%.0f%%" % (100 * fraction))

            fraction = (definite+0.0)/self.total_size + self.total_pr_bar.get_fraction()
            self.total_pr_bar.set_fraction(fraction)
            self.total_pr_bar.set_text("%.0f%%" % (100 * fraction))
            time.sleep(0.1)
            if self.exit:
                raise threading.ThreadError("the thread is stopped")
            if got == size:
                break

class MessageWindow(Gtk.MessageDialog):
    def __init__(self, title, type=Gtk.MessageType.INFO, text=None, parent=None,
                 buttons=None, flags=0, func=None, args=(), func1=None, args1=()):
        text = split_string(text, 40)
        Gtk.MessageDialog.__init__(self, parent, flags, type, buttons, text)

        self.set_title(title)
        self.show_all()
        id = self.run()
        if id != Gtk.ResponseType.NONE:
            if func and id in [Gtk.ResponseType.OK, Gtk.ResponseType.APPLY, Gtk.ResponseType.ACCEPT, Gtk.ResponseType.YES]:
                func(args) if args else func()
            if func1 and id in [Gtk.ResponseType.NO, Gtk.ResponseType.CLOSE, Gtk.ResponseType.CANCEL, Gtk.ResponseType.REJECT]:
                func1(args1) if args else func1()
        time.sleep(0.2) #otherwise can be freezes
        self.destroy()
        #GObject.timeout_add(100, self.destroy)


    def delete_event(self, widget, event, data=None):
        self.response(Gtk.ResponseType.NONE)
        return True
########NEW FILE########
__FILENAME__ = cue_reader
'''
Created on 7  2010

@author: ivan
'''

from __future__ import with_statement

import os
import re
import logging
import chardet
import foobnix.util.id3_util

from foobnix.fc.fc import FC
from foobnix.gui.model import FModel
from foobnix.util import file_utils
from foobnix.util.audio import get_mutagen_audio
from foobnix.util.image_util import get_image_by_path
from foobnix.util.time_utils import convert_seconds_to_text
from foobnix.util.file_utils import get_any_supported_audio_file
from foobnix.util.id3_util import update_id3, correct_encoding

TITLE = "TITLE"
PERFORMER = "PERFORMER"
FILE = "FILE"
INDEX = "INDEX"

class CueTrack():

    def __init__(self, title, performer, index, path):
        self.title = title
        self.performer = performer
        self.index = index
        self.duration = 0
        self.path = path

    def __str__(self):
        return "Track: " + self.title + " " + self.performer + " " + self.index

    def get_start_time_str(self):
        return self.index[len("INDEX 01") + 1:]

    def get_start_time_sec(self):
        time = self.get_start_time_str()

        times = re.findall("([0-9]{1,3}):", time)

        if not times or len(times) < 2:
            return 0

        min = times[0]
        sec = times[1]
        starts = int(min) * 60 + int(sec)
        return starts

class CueFile():
    def __init__(self):
        self.title = None
        self.performer = None
        self.file = ""
        self.image = None
        self.tracks = []

    def append_track(self, track):
        self.tracks.append(track)

    def __str__(self):
        if self.title:
            logging.info("Title" + self.title)
        if self.performer:
            logging.info("Performer" + self.performer)
        if self.file:
            logging.info("File" + self.file)

        return "CUEFILE: " + self.title + " " + self.performer + " " + self.file

class CueReader():

    def __init__(self, cue_path, embedded_cue=None):
        self.cue_path = cue_path
        self.embedded_cue = embedded_cue
        self.is_valid = True
        self.cue_file = CueFile()


    def get_line_value(self, str):
        first = str.find('"') or str.find("'")
        end = str.find('"', first + 1) or str.find("'", first + 1)
        return str[first + 1:end]

    def get_full_duration (self, file):
        try:
            audio = get_mutagen_audio(file)
        except Exception, e:
            logging.warn(str(e) + " " + file)
            return

        return audio.info.length

    def normalize(self):
        duration_tracks = []
        tracks = self.cue_file.tracks
        for i in xrange(len(tracks)):
            track = tracks[i]
            full_duration = self.get_full_duration(track.path)
            if full_duration:
                if i == len(tracks) - 1: #for last track in cue
                    duration = self.get_full_duration(track.path) - track.get_start_time_sec()
                else:
                    next_track = tracks[i + 1]
                    if next_track.get_start_time_sec() > track.get_start_time_sec():
                        #for cue "one file - several tracks"
                        duration = next_track.get_start_time_sec() - track.get_start_time_sec()
                    else: #for cue  "several files - each file involve several tracks"
                        duration = self.get_full_duration(track.path) - track.get_start_time_sec()

                track.duration = duration
            else:
                track.duration = None
            if not track.path:
                track.path = self.cue_file.file

            track.path = get_any_supported_audio_file(track.path)

            duration_tracks.append(track)

        self.cue_file.tracks = duration_tracks
        return self.cue_file

    def get_common_beans(self):
        beans = []
        cue = self.parse()
        if not self.is_cue_valid():
            return []
        for i, track  in enumerate(cue.tracks):
            bean = FModel(text=track.performer + " - " + track.title, path=track.path)
            bean.artist = track.performer
            bean.tracknumber = i + 1
            bean.title = track.title
            bean.album = self.cue_file.title
            bean.name = bean.text
            bean.start_sec = track.get_start_time_sec()
            bean.duration_sec = track.duration
            bean.time = convert_seconds_to_text(track.duration)
            bean.is_file = True
            try:
                bean.info = foobnix.util.id3_util.normalized_info(get_mutagen_audio(track.path).info, bean)
            except Exception, e:
                logging.warn(str(e) + " " + bean.path)
                bean.info = ""

            if not bean.title or not bean.artist:
                bean = udpate_id3(bean)

            beans.append(bean)

        return beans

    def is_cue_valid(self):
        logging.info("CUE VALID" + str(self.cue_path) + str(self.is_valid))
        return self.is_valid

    """detect file encoding"""
    def code_detecter(self, data):
        try:
            return chardet.detect(data)['encoding']
        except:
            return "windows-1251"

    def parse(self):
        if self.embedded_cue:
            data = self.embedded_cue
        else:
            file = open(self.cue_path, "r")
            data = file.read()
        code = self.code_detecter(correct_encoding(data))
        data = data.replace('\r\n', '\n').split('\n')

        title = ""
        performer = ""
        index = "00:00:00"
        full_file = None

        self.cue_file.image = get_image_by_path(self.cue_path)

        self.files_count = 0

        for line in data:
            if not self.is_valid and not line.startswith(FILE):
                continue
            else: self.is_valid = True

            try:
                line = unicode(line, code)
            except:
                logging.error("There is some problems while converting in unicode")

            line = str(line).strip()
            if not line:
                continue

            if line.startswith(TITLE):
                title = self.get_line_value(line)
                if self.files_count == 0:
                    self.cue_file.title = title


            if line.startswith(PERFORMER):
                performer = self.get_line_value(line)
                if self.files_count == 0:
                    self.cue_file.performer = performer

            if line.startswith(FILE):
                self.files_count += 1
                file = self.get_line_value(line)
                file = os.path.basename(file)

                if "/" in file:
                    file = file[file.rfind("/")+1:]
                if "\\" in file:
                    file = file[file.rfind("\\")+1:]

                dir = os.path.dirname(self.cue_path)
                full_file = os.path.join(dir, file)
                logging.debug("CUE source" + full_file)
                exists = os.path.exists(full_file)
                """if there no source cue file"""

                if not exists:
                    """try to find other source"""
                    ext = file_utils.get_file_extension(full_file)
                    nor = full_file[:-len(ext)]
                    logging.info("Normalized path" + nor)

                    find_source = False
                    for support_ext in FC().audio_formats:
                        try_name = nor + support_ext
                        if os.path.exists(try_name):
                            full_file = try_name
                            logging.debug("Found source for cue file name" + try_name)
                            find_source = True
                            break

                    if not find_source:
                        self.is_valid = False
                        self.files_count -= 1
                        logging.warn("Can't find source for " + line + "  Check source file name")
                        continue

                if self.files_count == 0:
                    self.cue_file.file = full_file

            if line.startswith(INDEX):
                index = self.get_line_value(line)

            if line.startswith("INDEX 01"):
                cue_track = CueTrack(title, performer, index, full_file)
                self.cue_file.append_track(cue_track)

        logging.debug("CUE file parsed " + str(self.cue_file.file))
        return self.normalize()

def update_id3_for_cue(beans):
    result = []
    for bean in beans:
        if (bean.path and bean.path.lower().endswith(".cue")) or bean.cue:
            reader = CueReader(bean.path, bean.cue)
            cue_beans = reader.get_common_beans()
            for cue in cue_beans:
                result.append(cue)
        else:
            result.append(bean)
    return result


########NEW FILE########
__FILENAME__ = m3u_reader
'''
Created on Apr 26, 2013

@author: dimitry
'''

import logging
import os.path

from foobnix.gui.model import FModel
from foobnix.util.file_utils import get_file_extension


class M3UReader:
    def __init__(self, path):
        self.path = path
        try:
            self.m3u = open(unicode(path))
        except Exception as e:
            logging.error(str(e))
            self.m3u = None

    def get_common_beans(self):
        paths_and_texts = self.parse()
        if not paths_and_texts:
            return []
        beans = [FModel(path=path_and_text[0],
                        text=path_and_text[1])
                        .add_is_file(True)
                        for path_and_text in paths_and_texts]
        return beans

    def parse(self):
        try:
            if not self.m3u:
                return
            lines = self.m3u.readlines()
            paths = [os.path.normpath(line).strip('\r\n') for line in lines
                     if line.startswith("##") or not line.startswith("#")]
            dirname = os.path.dirname(self.path)

            full_paths = []
            paths = iter(paths)
            for path in paths:
                text = None
                if path.startswith("##"):
                    def task(path):
                        text = path[2 : ]
                        try:
                            next_path = paths.next()
                            path = next_path if not next_path.startswith("##") else None
                        except StopIteration:
                            path = None
                            next_path = None
                        if not path:
                            full_paths.append( [path, text.strip('\r\n')] )
                            if next_path:
                                path, text = task(next_path)

                        return path, text

                    path, text = task(path)
                    if not path:
                        break

                if text:
                    text = text.strip('\r\n')
                else:
                    new_text = path.rsplit('/', 1)[-1]
                    if path == new_text:
                        text = path.rsplit('\\', 1)[-1]
                    else:
                        text = new_text

                if (path in "\\/"):
                    full_paths.append( [path.replace("\\", "/"), text] )
                elif path.startswith('http'):
                    if not text:
                        text = path.rsplit('/', 1)[-1]
                    full_paths.append( [path.replace('/', '//', 1), text] )
                else:
                    full_paths.append([os.path.join(dirname, path).replace("\\", "/"), text] )
            return full_paths
        except IndexError:
            logging.warn("You try to load empty playlist")



def update_id3_for_m3u(beans):
    result = []
    for bean in beans:
        if bean.path and get_file_extension(bean.path) in [".m3u", ".m3u8"]:
            reader = M3UReader(bean.path)
            m3u_beans = reader.get_common_beans()
            for bean in m3u_beans:
                result.append(bean)
        else:
            result.append(bean)
    return result
########NEW FILE########
__FILENAME__ = pls_reader
'''
Created on Nov 15, 2013

@author: Viktor Suprun
'''

import logging

from foobnix.gui.model import FModel
from foobnix.util.file_utils import get_file_extension


class PLSReader:

    def __init__(self, path):
        self.path = path
        try:
            self.pls = open(unicode(path))
        except Exception as e:
            logging.error(str(e))
            self.pls = None

    def get_common_beans(self):
        if not self.pls:
            return []
        try:
            beans = []
            lines = self.pls.readlines()
            lines = [map(lambda x: x.strip(), l.split("=")) for l in lines if not l.strip().startswith("[")]
            playlist = {}
            for l in lines:
                playlist[l[0]] = l[1]
            for i in range(1, int(playlist["NumberOfEntries"])+1):
                si = str(i)
                if "File" + si in playlist:
                    bean = FModel(path=playlist["File" + si],
                                  text=playlist["Title" + si] if "Title" + si in playlist else playlist["File" + si]).add_is_file(True)
                    beans.append(bean)
            return beans

        except Exception as e:
            logging.error("Couldn't parse pls")
            logging.error(str(e))
        return []


def update_id3_for_pls(beans):
    result = []
    for bean in beans:
        if bean.path and get_file_extension(bean.path) in [".pls"]:
            reader = PLSReader(bean.path)
            plsbeans = reader.get_common_beans()
            for bean in plsbeans:
                result.append(bean)
        else:
            result.append(bean)
    return result
########NEW FILE########
__FILENAME__ = category_info
#-*- coding: utf-8 -*-
'''
Created on 24 авг. 2010

@author: ivan
'''
from gi.repository import Gtk
from foobnix.preferences.config_plugin import ConfigPlugin
class CategoryInfoConfig(ConfigPlugin):
    name = _("Category Info")
    def __init__(self):
        box = Gtk.VBox(False, 0)
        box.hide()
        
        similar_arists = Gtk.CheckButton(label="Show Similar Artists", use_underline=True)
        similar_arists.show()
        
        similar_song = Gtk.CheckButton(label="Show Similar Songs", use_underline=True)
        similar_song.show()
        
        similar_tags = Gtk.CheckButton(label="Show Similar Tags", use_underline=True)
        similar_tags.show()
        
        box.pack_start(similar_arists, False, True, 0)
        box.pack_start(similar_song, False, True, 0)
        box.pack_start(similar_tags, False, True, 0)
        
        self.widget = box

########NEW FILE########
__FILENAME__ = dm_config
#-*- coding: utf-8 -*-
'''
Created on 24 авг. 2010

@author: ivan
'''
from gi.repository import Gtk
from foobnix.preferences.config_plugin import ConfigPlugin
import logging
from foobnix.fc.fc import FC
from foobnix.preferences.configs import CONFIG_DOWNLOAD_MANAGER

class DMConfig(ConfigPlugin):
    
    name = CONFIG_DOWNLOAD_MANAGER
    
    def __init__(self, controls):
        box = Gtk.VBox(False, 0)
        box.hide()        

        hbox = Gtk.HBox(False, 0)
        
        self.is_save = Gtk.CheckButton(label=_("Save online music"), use_underline=True)
        self.is_save.connect("clicked", self.on_save_online)
        self.is_save.show()
        
        self.online_dir = Gtk.FileChooserButton("set place")
        self.online_dir.set_action(Gtk.FileChooserAction.SELECT_FOLDER)
        self.online_dir.connect("current-folder-changed", self.on_change_folder)        
        self.online_dir.show()
        
        hbox.pack_start(self.is_save, False, True, 0)
        hbox.pack_start(self.online_dir, True, True, 0)
        
                
        box.pack_start(hbox, False, True, 0)
        
        self.widget = box
        
        
    def on_save_online(self, *a):
        value = self.is_save.get_active()
        if  value:
            self.online_dir.set_sensitive(True)
        else:
            self.online_dir.set_sensitive(False)
                
        FC().is_save_online = value              
        
    def on_change_folder(self, *a):
        path = self.online_dir.get_filename()       
        FC().online_save_to_folder = path
        
        logging.info("Change music online folder"+ path)  
                
    
    def on_load(self):
        self.is_save.set_active(FC().is_save_online)
        self.online_dir.set_current_folder(FC().online_save_to_folder)
        self.online_dir.set_sensitive(FC().is_save_online)

########NEW FILE########
__FILENAME__ = hotkey_conf
'''
Created on Sep 7, 2010

@author: ivan
'''

import collections
import gi
import logging

gi.require_version("Keybinder", "3.0")

from gi.repository import Gtk
from gi.repository import Gdk
from gi.repository import Keybinder

from copy import copy
from foobnix.fc.fc import FC
from foobnix.helpers.menu import Popup
from foobnix.helpers.pref_widgets import FrameDecorator
from foobnix.util.mouse_utils import is_double_left_click
from foobnix.preferences.config_plugin import ConfigPlugin
from foobnix.util.key_utils import is_key_control, is_key_shift, is_key_super, \
    is_key_alt

Keybinder.init()


def activate_hot_key(hotkey, command):
    logging.debug("Run command: " + command + " Hotkey: " + hotkey)
    if HotKeysConfig.controls:
        eval('HotKeysConfig.controls.' + command + '()')


def add_key_binder(command, hotkey):
    try:
        logging.debug("binding a key %s with command %s" % (hotkey, command))
        Keybinder.bind(hotkey, activate_hot_key, command)
    except Exception, e:
        logging.warn("add_key_binder exception: %s %s" % (str(hotkey), str(e)))


def bind_all():
    binder(FC().action_hotkey)
    if FC().media_keys_enabled:
        items = to_form_dict_of_mmkeys()
        logging.debug(items)
        if items:
            binder(items)
    else:
        logging.debug("media keys has been disabled")

    HotKeysConfig.binded = True


def binder(items):
    for key in items:
        command = key
        hotkey = items[key]
        add_key_binder(command, hotkey)


def load_foobnix_hotkeys():
    logging.debug("LOAD HOT KEYS")
    bind_all()


def to_form_dict_of_mmkeys():
    if FC().media_keys_enabled:
        items = copy(FC().multimedia_keys)
        if not FC().media_volume_keys_enabled:
            for key in FC().media_volume_keys:
                if key in items:
                    del items[key]
        return items


class HotKeysConfig(ConfigPlugin):

    name = _("Global Hotkeys")
    binded = True
    controls = None

    def __init__(self, controls):
        HotKeysConfig.controls = controls
        box = Gtk.VBox(False, 0)
        box.hide()

        self.tree_widget = Gtk.TreeView()
        self.tree_widget.connect("button-press-event", self.on_populate_click)

        self.tree_widget.show()
        self.model = Gtk.ListStore(str, str)

        self.title = None
        self.column1 = Gtk.TreeViewColumn(_("Action"), Gtk.CellRendererText(), text=0)
        self.column2 = Gtk.TreeViewColumn(_("Hotkey"), Gtk.CellRendererText(), text=1)
        self.tree_widget.append_column(self.column1)
        self.tree_widget.append_column(self.column2)
        self.tree_widget.set_model(self.model)

        hbox = Gtk.HBox(False, 0)
        hbox.show()

        add_button = Gtk.Button(_("Add"))
        add_button.set_size_request(80, -1)
        add_button.connect("clicked", self.on_add_row)
        add_button.show()

        remove_button = Gtk.Button(_("Remove"))
        remove_button.connect("clicked", self.on_remove_row)
        remove_button.set_size_request(80, -1)
        remove_button.show()

        hbox.pack_start(add_button, False, True, 0)
        hbox.pack_start(remove_button, False, True, 0)

        hotbox = Gtk.HBox(False, 0)
        hotbox.show()

        self.action_text = Gtk.Entry()
        self.action_text.set_size_request(150, -1)
        self.action_text.connect("button-press-event", self.on_mouse_click)

        self.hotkey_text = Gtk.Entry()
        self.hotkey_text.set_editable(False)
        self.hotkey_text.connect("key-press-event", self.on_key_press)
        self.hotkey_text.set_size_request(150, -1)

        self.hotkey_auto = Gtk.CheckButton(_("Auto key"))
        self.hotkey_auto.set_active(True)

        hotbox.pack_start(self.action_text, False, True, 0)
        hotbox.pack_start(self.hotkey_text, False, True, 0)
        hotbox.pack_start(self.hotkey_auto, False, True, 0)

        self.disable_mediakeys = Gtk.CheckButton(label=_("Disable Multimedia Keys"), use_underline=True)
        self.disable_volume_keys = Gtk.CheckButton(label=_("Don't try to bind volume control keys"), use_underline=True)
        def on_toggle(*a):
            if self.disable_mediakeys.get_active():
                self.disable_volume_keys.set_sensitive(False)
            else:
                self.disable_volume_keys.set_sensitive(True)

        self.disable_mediakeys.connect("toggled", on_toggle)

        mmbox = Gtk.VBox(False, 0)
        mmbox.pack_start(self.disable_mediakeys, False, False, 0)
        mmbox.pack_start(self.disable_volume_keys, False, False, 0)
        self.mm_frame_decorator = FrameDecorator(_("Multimedia keys"), mmbox)

        box.pack_start(self.tree_widget, False, True, 0)
        box.pack_start(hotbox, False, True, 0)
        box.pack_start(hbox, False, True, 0)
        box.pack_start(self.mm_frame_decorator, False, False, 0)
        self.widget = box
        self.menu = self.create_menu()

    def create_menu(self):
        menu = Popup()
        menu.add_item(_("Play-Pause"), Gtk.STOCK_MEDIA_PAUSE, self.set_action_text, "play_pause")
        menu.add_item(_("Stop"), Gtk.STOCK_MEDIA_STOP, self.set_action_text, "state_stop")
        menu.add_item(_("Next song"), Gtk.STOCK_MEDIA_NEXT, self.set_action_text, "next")
        menu.add_item(_("Previous song"), Gtk.STOCK_MEDIA_PREVIOUS, self.set_action_text, "prev")
        menu.add_item(_("Volume up"), Gtk.STOCK_GO_UP, self.set_action_text, "volume_up")
        menu.add_item(_("Volume down"), Gtk.STOCK_GO_DOWN, self.set_action_text, "volume_down")
        menu.add_item(_("Show-Hide"), Gtk.STOCK_FULLSCREEN, self.set_action_text, "show_hide")
        menu.add_item(_('Download'), Gtk.STOCK_ADD, self.set_action_text, "download")
        return menu

    def set_action_text(self, text):
        self.action_text.set_text(text)

    def set_hotkey_text(self, text):
        text = text.replace("Super_L", "<SUPER>").replace("Super_R", "<SUPER>").replace("Control_L", "<Control>").replace("Control_R", "<Control>").replace("Shift_L", "<Shift>").replace("Shift_R", "<Shift>").replace("Alt_L", "<Alt>").replace("Alt_R", "<Alt>")
        text = text.replace("<Shift>", "") #because of bug in python-keybinder https://bugs.launchpad.net/kupfer/+bug/826075
        if text.count("<") > 2 or text.endswith("ISO_Next_Group"): return
        self.hotkey_text.set_text(text)

    def get_hotkey_text(self):
        text = self.hotkey_text.get_text()
        if not text:
            text = ""
        return text

    def on_add_row(self, *args):
        command = self.action_text.get_text()
        hotkey = self.hotkey_text.get_text()
        if command and hotkey:
            if hotkey not in self.get_all_items():
                if command in self.get_all_items():
                    for item in self.model:
                        if item[0] == command:
                            item[1] = hotkey
                else:
                    self.model.append([command, hotkey])

        self.action_text.set_text("")
        self.hotkey_text.set_text("")

    def on_remove_row(self, *args):
        selection = self.tree_widget.get_selection()
        model, selected = selection.get_selected()
        if selected:
            model.remove(selected)

    def unbind_all(self):
        self.unbinder(FC().action_hotkey)
        self.unbinder(FC().multimedia_keys)

        HotKeysConfig.binded = False

    def unbinder(self, items):
        for keystring in items:
            try:
                Keybinder.unbind(items[keystring])
            except:
                pass
        HotKeysConfig.binded = False

    def on_populate_click(self, w, event):
        if is_double_left_click(event):
            selection = self.tree_widget.get_selection()
            model, selected = selection.get_selected()

            command = self.model.get_value(selected, 0)
            keystring = self.model.get_value(selected, 1)
            self.action_text.set_text(command)
            self.hotkey_text.set_text(keystring)

    def on_mouse_click(self, w, event):
        self.menu.show(event)

    def on_load(self):
        if not FC().media_keys_enabled:
            self.disable_mediakeys.set_active(True)
        if not FC().media_volume_keys_enabled:
            self.disable_volume_keys.set_active(True)
        self.fill_hotkey_list()

    def fill_hotkey_list(self):
        items = FC().action_hotkey
        self.model.clear()
        for key in items:
            command = key
            hotkey = items[key]
            self.model.append([command, hotkey])

    def on_save(self):
        if self.disable_mediakeys.get_active():
            FC().media_keys_enabled = False
        else:
            FC().media_keys_enabled = True
        if self.disable_volume_keys.get_active():
            FC().media_volume_keys_enabled = False
        else:
            FC().media_volume_keys_enabled = True
        self.unbind_all()
        FC().action_hotkey = self.get_all_items()
        bind_all()

    def get_all_items(self):
        items = collections.OrderedDict()
        for item in self.model:
            action = item[0]
            hotkey = item[1]
            items[action] = hotkey
        return items

    def on_key_press(self, w, event):
        if not self.hotkey_auto.get_active():
            self.hotkey_text.set_editable(True)
            return None
        self.hotkey_text.set_editable(False)

        self.unbind_all()

        keyname = Gdk.keyval_name(event.keyval) #@UndefinedVariable

        logging.debug("Key %s (%d) was pressed. %s" % (keyname, event.keyval, str(event.state)))
        if is_key_control(event):
            self.set_hotkey_text(self.get_hotkey_text() + keyname)
        elif is_key_shift(event):
            self.set_hotkey_text(self.get_hotkey_text() + keyname)
        elif is_key_super(event):
            self.set_hotkey_text(self.get_hotkey_text() + keyname)
        elif is_key_alt(event):
            self.set_hotkey_text(self.get_hotkey_text() + keyname)
        else:
            self.set_hotkey_text(keyname)

    def on_key_release(self, w, event):
        keyname = Gdk.keyval_name(event.keyval) #@UndefinedVariable
        logging.debug("Key release %s (%d) was pressed" % (keyname, event.keyval))

    def on_close(self):
        if not HotKeysConfig.binded:
            self.fill_hotkey_list()
            bind_all()


########NEW FILE########
__FILENAME__ = info_panel_conf
#-*- coding: utf-8 -*-
'''
Created on 29 авг. 2010

@author: ivan
'''
from foobnix.preferences.config_plugin import ConfigPlugin
from gi.repository import Gtk
from foobnix.fc.fc import FC
class InfoPagenConfig(ConfigPlugin):
    
    name = _("Info panel")
    
    def __init__(self, controls):
        box = Gtk.VBox(False, 0)
        box.hide()
        
        """count"""
        cbox = Gtk.HBox(False, 0)
        cbox.show()
        
        tab_label = Gtk.Label(_("Disc cover size"))
        tab_label.show()
        
        adjustment = Gtk.Adjustment(value=1, lower=100, upper=350, step_incr=20, page_incr=50, page_size=0)
        self.image_size_spin = Gtk.SpinButton(adjustment)
        self.image_size_spin.show()
        
        cbox.pack_start(tab_label, False, False, 0)
        cbox.pack_start(self.image_size_spin, False, True, 0)
        
        """lyric panel size"""
        lbox = Gtk.HBox(False, 0)
        lbox.show()
        
        lyric_label = Gtk.Label(_("Lyric panel size"))
        lyric_label.show()
        
        adjustment = Gtk.Adjustment(value=1, lower=100, upper=500, step_incr=20, page_incr=50, page_size=0)
        self.lyric_size_spin = Gtk.SpinButton(adjustment)
        self.lyric_size_spin.show()

        lbox.pack_start(lyric_label, False, False, 0)
        lbox.pack_start(self.lyric_size_spin, False, True, 0)
        
        
        self.show_tags = Gtk.CheckButton(label=_("Show Tags list"), use_underline=True)
        self.show_tags.show()
        
        
        box.pack_start(cbox, False, True, 0)
        #box.pack_start(lbox, False, True, 0)
        #box.pack_start( self.show_tags, False, True, 0)
        self.widget = box
    
    def on_load(self):
        self.image_size_spin.set_value(FC().info_panel_image_size)
        self.show_tags.set_active(FC().is_info_panel_show_tags)
        
    
    def on_save(self):        
        FC().info_panel_image_size = self.image_size_spin.get_value_as_int()
        FC().is_info_panel_show_tags = self.show_tags.get_active()
         
        

########NEW FILE########
__FILENAME__ = last_fm
#-*- coding: utf-8 -*-
'''
Created on 24 авг. 2010

@author: ivan
'''

import thread

from gi.repository import Gtk
from gi.repository import GLib

from foobnix.preferences.config_plugin import ConfigPlugin
from foobnix.fc.fc import FC
from foobnix.fc.fc_base import FCBase
from foobnix.util import idle_task


class LastFmConfig(ConfigPlugin):

    name = _("Last FM + VK")

    def __init__(self, controls):
        self.controls = controls

        box = VBox(self, False, 0)
        box.hide()

        """LAST.FM"""
        l_frame = Gtk.Frame(label=_("Last.FM"))
        l_frame.set_border_width(0)
        l_layout = Gtk.VBox(False, 0)

        """LOGIN"""
        lbox = Gtk.HBox(False, 0)
        lbox.show()

        login = Gtk.Label(_("Login"))
        login.set_size_request(150, -1)
        login.show()

        self.login_text = Gtk.Entry()
        self.login_text.show()

        lbox.pack_start(login, False, False, 0)
        lbox.pack_start(self.login_text, False, True, 0)

        """PASSWORD"""
        pbox = Gtk.HBox(False, 0)
        pbox.show()

        password = Gtk.Label(_("Password"))
        password.set_size_request(150, -1)
        password.show()

        self.password_text = Gtk.Entry()
        self.password_text.set_visibility(False)
        self.password_text.set_invisible_char("*")
        self.password_text.show()

        limit_text = Gtk.Label(_("Limit search results:  "))
        limit_text.show()

        self.adjustment = Gtk.Adjustment(value=50, lower=10, upper=200, step_incr=10)
        limit = Gtk.SpinButton(adjustment=self.adjustment, climb_rate=0.0, digits=0)
        limit.show()

        limitbox = Gtk.HBox(False, 0)
        limitbox.pack_start(limit_text, False, False, 0)
        limitbox.pack_start(limit, False, False, 0)

        self.music_scrobbler = Gtk.CheckButton(label=_("Enable Music Scrobbler"), use_underline=True)
        self.music_scrobbler.show()

        self.radio_scrobbler = Gtk.CheckButton(label=_("Enable Radio Scrobbler"), use_underline=True)
        self.radio_scrobbler.show()

        pbox.pack_start(password, False, False, 0)
        pbox.pack_start(self.password_text, False, True, 0)

        l_layout.pack_start(lbox, False, True, 0)
        l_layout.pack_start(pbox, False, True, 0)
        l_layout.pack_start(limitbox, False, True, 10)
        l_layout.pack_start(self.music_scrobbler, False, True, 0)
        l_layout.pack_start(self.radio_scrobbler, False, True, 0)

        l_frame.add(l_layout)

        """VK"""

        vk_frame = Gtk.Frame(label=_("VKontakte"))
        vk_frame.set_border_width(0)

        vk_layout = Gtk.VBox(False, 0)

        self.default_label_value = _("Not connected")

        self.frase_begin = _("You vk account is:")
        self.vk_account_label = Gtk.Label(self.frase_begin + " %s" % self.default_label_value)
        self.reset_vk_auth_button = Gtk.Button(_("Reset vk authorization"))
        self.reset_vk_auth_button.connect("button-release-event", self.on_reset_vk_click)
        self.vk_autocomplete = Gtk.CheckButton(label=_("Enable VK autocomplete"), use_underline=True)
        self.vk_autocomplete.show()
        vk_layout.pack_start(self.vk_account_label, False, False, 0)
        vk_layout.pack_start(self.reset_vk_auth_button, False, False, 0)
        vk_layout.pack_start(self.vk_autocomplete, False, False)
        vk_frame.add(vk_layout)

        """all"""
        box.pack_start(l_frame, False, True, 0)
        box.pack_start(vk_frame, False, True, 0)

        self.widget = box

    @idle_task
    def on_reset_vk_click(self, *a):
        self.controls.vk_service.reset_vk()
        self.vk_account_label.set_text(self.frase_begin + " %s" % self.default_label_value)

    def get_and_set_profile(self):
        def task_get_and_set_profile():
            profile = self.controls.net_wrapper.execute(self.controls.vk_service.get_profile, True)
            if profile:
                fname = profile[0]["first_name"]
                sname = profile[0]["last_name"]
                GLib.idle_add(self.vk_account_label.set_text, self.frase_begin + " %s %s" % (fname, sname))
        thread.start_new_thread(task_get_and_set_profile, () )

    def on_load(self):
        self.login_text.set_text(FCBase().lfm_login)
        self.password_text.set_text(FCBase().lfm_password)
        self.adjustment.set_value(FC().search_limit)
        self.music_scrobbler.set_active(FC().enable_music_scrobbler)
        self.radio_scrobbler.set_active(FC().enable_radio_scrobbler)
        self.vk_autocomplete.set_active(FC().enable_vk_autocomlete)

    def on_save(self):
        if FCBase().lfm_login != self.login_text.get_text() or FCBase().lfm_password != self.password_text.get_text():
            FCBase().cookie = None

        FCBase().lfm_login = self.login_text.get_text()
        FCBase().lfm_password = self.password_text.get_text()
        FC().search_limit = self.adjustment.get_value()
        FC().enable_music_scrobbler = self.music_scrobbler.get_active()
        FC().enable_radio_scrobbler = self.radio_scrobbler.get_active()
        FC().enable_vk_autocomlete  = self.vk_autocomplete.get_active()

class VBox(Gtk.VBox):
    def __init__(self, config, *args):
            Gtk.VBox.__init__(self, args)
            self.config = config

    def show(self):
            self.config.get_and_set_profile()
            super(VBox, self).show()

########NEW FILE########
__FILENAME__ = music_library
#-*- coding: utf-8 -*-
'''
Created on 24 авг. 2010

@author: ivan
'''

from gi.repository import Gtk
import os.path
import logging

from foobnix.fc.fc import FC
from foobnix.fc.fc_cache import FCache
from foobnix.gui.model import FDModel
from foobnix.gui.model.signal import FControl
from foobnix.preferences.config_plugin import ConfigPlugin
from foobnix.preferences.configs import CONFIG_MUSIC_LIBRARY
from foobnix.gui.treeview.simple_tree import  SimpleListTreeControl
from foobnix.helpers.dialog_entry import show_entry_dialog,\
    directory_chooser_dialog


class MusicLibraryConfig(ConfigPlugin, FControl):
    name = CONFIG_MUSIC_LIBRARY
    enable = True

    def __init__(self, controls):
        FControl.__init__(self, controls)

        box = Gtk.VBox(False, 0)
        box.hide()
        box.pack_start(self.tabs_mode(), False, True, 0)
        box.pack_start(self.dirs(), False, True, 0)
        box.pack_start(self.formats(), False, True, 0)

        self.widget = box
        uhbox = Gtk.HBox()
        ulabel = Gtk.Label(_("Update library on start (more slow) "))
        self.update_on_start = Gtk.CheckButton()

        uhbox.pack_start(ulabel, False, True, 0)
        uhbox.pack_start(self.update_on_start, False, False, 0)
        box.pack_start(uhbox, False, True, 0)
        box.pack_start(self.gap(), False, True, 0)
        box.pack_start(self.buffer_size(), False, True, 0)


    def dirs(self):
        self.frame = Gtk.Frame(label=_("Music dirs"))
        self.frame.set_border_width(0)
        self.frame.show()
        self.frame.set_no_show_all(True)
        frame_box = Gtk.HBox(False, 0)
        frame_box.set_border_width(5)
        frame_box.show()

        self.tree_controller = SimpleListTreeControl(_("Paths"), None)

        """buttons"""
        button_box = Gtk.VBox(False, 0)
        button_box.show()

        bt_add = Gtk.Button(_("Add"))
        bt_add.connect("clicked", self.add_dir)
        bt_add.set_size_request(80, -1)
        bt_add.show()

        bt_remove = Gtk.Button(_("Remove"))
        bt_remove.connect("clicked", self.remove_dir)
        bt_remove.set_size_request(80, -1)
        bt_remove.show()

        empty = Gtk.Label("")
        empty.show()

        button_box.pack_start(bt_add, False, False, 0)
        button_box.pack_start(bt_remove, False, False, 0)
        button_box.pack_start(empty, True, True, 0)

        self.tree_controller.scroll.show_all()
        frame_box.pack_start(self.tree_controller.scroll, True, True, 0)
        frame_box.pack_start(button_box, False, False, 0)

        self.frame.add(frame_box)

        if FC().tabs_mode == "Multi":
            self.frame.hide()
        return self.frame

    def reload_dir(self, *a):
        FCache().music_paths[0] = self.temp_music_paths[:] #create copy of list
        self.controls.update_music_tree()

    def on_load(self):
        self.tree_controller.clear_tree()
        for path in FCache().music_paths[0]:
            self.tree_controller.append(FDModel(os.path.basename(path), path).add_is_file(False))

        self.files_controller.clear_tree()
        for ext in FC().all_support_formats:
            self.files_controller.append(FDModel(ext))

        self.adjustment.set_value(FC().gap_secs)
        self.buffer_adjustment.set_value(FC().network_buffer_size)

        if FC().tabs_mode == "Single":
            self.singletab_button.set_active(True)
            self.controls.perspectives.get_perspective('fs').get_tabhelper().set_show_tabs(False)

        if FC().update_tree_on_start:
            self.update_on_start.set_active(True)

        self.temp_music_paths = FCache().music_paths[0][:] #create copy of list

    def on_save(self):
        FC().all_support_formats = self.files_controller.get_all_beans_text()
        FC().gap_secs = self.adjustment.get_value()
        FC().network_buffer_size = self.buffer_adjustment.get_value()
        if self.singletab_button.get_active():
            '''for i in xrange(len(FCache().music_paths) - 1, 0, -1):
                del FCache().music_paths[i]
                del FCache().cache_music_tree_beans[i]
                del FCache().tab_names[i]
                self.controls.tabhelper.remove_page(i)'''
            FC().tabs_mode = "Single"
            self.controls.perspectives.get_perspective('fs').get_tabhelper().set_show_tabs(False)
            if self.temp_music_paths != FCache().music_paths[0]:
                self.reload_dir()

        else:
            FC().tabs_mode = "Multi"
            self.controls.perspectives.get_perspective('fs').get_tabhelper().set_show_tabs(True)
        if self.update_on_start.get_active():
            FC().update_tree_on_start = True
        else:
            FC().update_tree_on_start = False

    def add_dir(self, *a):
        current_folder = FCache().last_music_path if FCache().last_music_path else None
        paths = directory_chooser_dialog(_("Choose directory with music"), current_folder)
        if not paths:
            return
        path = paths[0]
        FCache().last_music_path = path[:path.rfind("/")]
        for path in paths:
            if path not in self.temp_music_paths:
                self.tree_controller.append(FDModel(os.path.basename(path), path).add_is_file(False))
                self.temp_music_paths.append(path)

    def remove_dir(self, *a):
        selection = self.tree_controller.get_selection()
        fm, paths = selection.get_selected_rows()#@UnusedVariable
        paths.reverse()
        for path in paths:
            del FCache().music_paths[0][path[0]]
            del FCache().cache_music_tree_beans[0][path[0]]

        self.tree_controller.delete_selected()
        remaining_beans = self.tree_controller.get_all_beans()
        if remaining_beans:
            self.temp_music_paths = [bean.path for bean in self.tree_controller.get_all_beans()]
        else:
            self.temp_music_paths = []

    def formats(self):
        frame = Gtk.Frame(label=_("File Types"))
        frame.set_border_width(0)
        frame.show()

        frame_box = Gtk.HBox(False, 0)
        frame_box.set_border_width(5)
        frame_box.show()

        self.files_controller = SimpleListTreeControl(_("Extensions"), None)

        """buttons"""
        button_box = Gtk.VBox(False, 0)
        button_box.show()

        bt_add = Gtk.Button(_("Add"))
        bt_add.connect("clicked", self.on_add_file)
        bt_add.set_size_request(80, -1)
        bt_add.show()

        bt_remove = Gtk.Button(_("Remove"))
        bt_remove.connect("clicked", lambda *a: self.files_controller.delete_selected())
        bt_remove.set_size_request(80, -1)
        bt_remove.show()
        button_box.pack_start(bt_add, False, False, 0)
        button_box.pack_start(bt_remove, False, False, 0)

        scrool_tree = Gtk.ScrolledWindow()
        scrool_tree.set_size_request(-1, 160)
        scrool_tree.set_policy(Gtk.PolicyType.AUTOMATIC, Gtk.PolicyType.AUTOMATIC)
        scrool_tree.add_with_viewport(self.files_controller.scroll)
        scrool_tree.show()

        frame_box.pack_start(scrool_tree, True, True, 0)
        frame_box.pack_start(button_box, False, False, 0)

        frame.add(frame_box)

        return frame

    def on_add_file(self, *a):
        val = show_entry_dialog(_("Please add audio extension"), _("Extension should be like '.mp3'"))
        if val and val.find(".") >= 0 and len(val) <= 5 and val not in self.files_controller.get_all_beans_text():
            self.files_controller.append(FDModel(val))
        else:
            logging.info("Can't add your value" + val)

    def gap(self):
        label = Gtk.Label(_("Gap between tracks"))

        self.adjustment = Gtk.Adjustment(value=0, lower=0, upper=5, step_incr=0.5)

        gap_len = Gtk.SpinButton(adjustment=self.adjustment, climb_rate=0.0, digits=1)
        gap_len.show()

        hbox = Gtk.HBox(False, 10)
        hbox.pack_start(gap_len, False, False, 0)
        hbox.pack_start(label, False, False, 0)
        hbox.show_all()

        return hbox

    def buffer_size(self):
        label = Gtk.Label(_("Buffer size for network streams (KBytes)"))

        self.buffer_adjustment = Gtk.Adjustment(value=128, lower=16, upper=2048, step_incr=16)

        buff_size = Gtk.SpinButton(adjustment=self.buffer_adjustment, climb_rate=0, digits=0)
        buff_size.show()

        hbox = Gtk.HBox(False, 10)
        hbox.pack_start(buff_size, False, False, 0)
        hbox.pack_start(label, False, False, 0)
        hbox.show_all()

        return hbox

    def tabs_mode(self):
        hbox = Gtk.HBox()
        self.multitabs_button = Gtk.RadioButton(None, _("Multi tab mode"))
        def on_toggle_multitab(widget, data=None):
            self.frame.hide()
        self.multitabs_button.connect("toggled", on_toggle_multitab)
        hbox.pack_start(self.multitabs_button, True, False, 0)

        self.singletab_button = Gtk.RadioButton.new_with_label_from_widget(self.multitabs_button, _("Single tab mode"))
        def on_toggle_singletab(widget, data=None):
            self.tree_controller.clear_tree()
            for path in FCache().music_paths[0]:
                self.tree_controller.append(FDModel(os.path.basename(path), path).add_is_file(False))
            self.temp_music_paths = FCache().music_paths[0][:]
            self.frame.show()
        self.singletab_button.connect("toggled", on_toggle_singletab)
        hbox.pack_end(self.singletab_button, True, False, 0)
        return hbox
########NEW FILE########
__FILENAME__ = network_conf
#-*- coding: utf-8 -*-
'''
Created on 1 сент. 2010

@author: ivan
'''


import time
import logging
import urllib2

from gi.repository import Gtk

from foobnix.fc.fc import FC
from foobnix.preferences.config_plugin import ConfigPlugin
from foobnix.util.proxy_connect import set_proxy_settings
from foobnix.gui.service.lastfm_service import LastFmService


class NetworkConfig(ConfigPlugin):

    name = _("Network Settings")

    def __init__(self, controls):

        self.controls = controls

        box = Gtk.VBox(False, 0)
        box.hide()

        self.enable_proxy = Gtk.CheckButton(label=_("Enable HTTP proxy"), use_underline=True)
        self.enable_proxy.connect("clicked", self.on_enable_http_proxy)
        self.enable_proxy.show()

        self.frame = Gtk.Frame(label=_("Settings"))
        self.frame.set_border_width(0)
        self.frame.show()

        all = Gtk.VBox(False, 0)
        all.show()


        """URL"""
        proxy_box = Gtk.HBox(False, 0)
        proxy_box.show()

        proxy_lable = Gtk.Label(_("Server"))
        proxy_lable.set_size_request(150, -1)
        proxy_lable.show()

        self.proxy_server = Gtk.Entry()
        self.proxy_server.show()

        require = Gtk.Label(_("example: 66.42.182.178:3128"))
        require.show()

        proxy_box.pack_start(proxy_lable, False, False, 0)
        proxy_box.pack_start(self.proxy_server, False, True, 0)
        proxy_box.pack_start(require, False, True, 0)


        """LOGIN"""
        lbox = Gtk.HBox(False, 0)
        lbox.show()

        login = Gtk.Label(_("Login"))
        login.set_size_request(150, -1)
        login.show()

        self.login_text = Gtk.Entry()
        self.login_text.show()

        lbox.pack_start(login, False, False, 0)
        lbox.pack_start(self.login_text, False, True, 0)

        """PASSWORD"""
        pbox = Gtk.HBox(False, 0)
        pbox.show()

        password = Gtk.Label(_("Password"))
        password.set_size_request(150, -1)
        password.show()

        self.password_text = Gtk.Entry()
        self.password_text.set_visibility(False)
        self.password_text.set_invisible_char("*")
        self.password_text.show()

        pbox.pack_start(password, False, False, 0)
        pbox.pack_start(self.password_text, False, True, 0)

        """check"""

        check = Gtk.HBox(False, 0)
        check.show()

        self.vk_test = Gtk.Entry()
        self.vk_test.set_text("http://vkontakte.ru")
        self.vk_test.show()

        self.test_button = Gtk.Button(_("Check Connection"))
        self.test_button.set_size_request(150, -1)
        self.test_button.connect("clicked", self.text_connection)
        self.test_button.show()

        self.result = Gtk.Label(_("Result:"))
        self.result.show()

        check.pack_start(self.test_button, False, True, 0)
        check.pack_start(self.vk_test, False, False, 0)
        check.pack_start(self.result, False, True, 0)

        """global"""
        all.pack_start(proxy_box, False, False, 0)
        all.pack_start(lbox, False, False, 0)
        all.pack_start(pbox, False, False, 0)
        all.pack_start(check, False, False, 0)

        self.frame.add(all)

        frame_box = Gtk.HBox(False, 0)
        frame_box.set_border_width(5)
        frame_box.show()

        self.net_ping = Gtk.CheckButton(label=_("Show message on network disconnection"), use_underline=True)

        box.pack_start(self.net_ping, False, True, 0)
        box.pack_start(self.enable_proxy, False, True, 0)
        box.pack_start(self.frame, False, True, 0)

        self.widget = box

        if  FC().proxy_enable and FC().proxy_url:
            set_proxy_settings()


    def text_connection(self, *a):
        self.on_save()
        set_proxy_settings()
        init = time.time()
        try:
            f = urllib2.urlopen(self.vk_test.get_text())
            f.read()
            f.close()
        except Exception, e:
            logging.error(e)
            self.result.set_text(str(e))
            return None

        seconds = time.time() - init
        self.result.set_text(_("Result:") + _(" OK in seconds: ") + str(seconds))

    def on_enable_http_proxy(self, *a):
        if  self.enable_proxy.get_active():
            self.frame.set_sensitive(True)
        else:
            self.frame.set_sensitive(False)

    def is_proxy_changed(self):
        if [FC().proxy_enable, FC().proxy_url, FC().proxy_user, FC().proxy_password] != [self.enable_proxy.get_active(), self.proxy_server.get_text(), self.login_text.get_text(), self.password_text.get_text()]:
            return True
        else:
            return False

    def on_load(self):
        self.enable_proxy.set_active(FC().proxy_enable)
        self.frame.set_sensitive(FC().proxy_enable)

        if FC().proxy_url:
            self.proxy_server.set_text(FC().proxy_url)
        if FC().proxy_user:
            self.login_text.set_text(FC().proxy_user)
        if FC().proxy_password:
            self.password_text.set_text(FC().proxy_password)

        if FC().net_ping:
            self.net_ping.set_active(True)


    def on_save(self):
        if not self.is_proxy_changed():
            return
        proxy_url = self.proxy_server.get_text()
        if proxy_url:
            if not ":" in proxy_url:
                logging.error("No port specified")
                proxy_url = proxy_url + ":3128"
            FC().proxy_url = proxy_url.strip()
        else:
            FC().proxy_url = None

        if self.enable_proxy.get_active() and FC().proxy_url:
            FC().proxy_enable = True
            if not self.controls.lastfm_service.network:
                self.controls.lastfm_service = LastFmService(self.controls)
            else:
                self.controls.lastfm_service.network.enable_proxy(FC().proxy_url)
        else:
            FC().proxy_enable = False
            if not self.controls.lastfm_service.network:
                self.controls.lastfm_service = LastFmService(self.controls)
            else:
                self.controls.lastfm_service.network.disable_proxy()


        if self.login_text.get_text():
            FC().proxy_user = self.login_text.get_text()
        else:
            FC().proxy_user = None

        if self.password_text.get_text():
            FC().proxy_password = self.password_text.get_text()
        else:
            FC().proxy_password = None

        if self.net_ping.get_active():
            self.controls.net_wrapper.set_ping(True)
        else:
            self.controls.net_wrapper.set_ping(False)

        set_proxy_settings()

        def set_new_vk_window():
            pass


########NEW FILE########
__FILENAME__ = notification_conf
#-*- coding: utf-8 -*-
'''
Created on 3 сент. 2010

@author: ivan
'''
from foobnix.preferences.config_plugin import ConfigPlugin
from gi.repository import Gtk
from foobnix.fc.fc import FC
from foobnix.helpers.dialog_entry import info_dialog_with_link_and_donate
class NotificationConfig(ConfigPlugin):
    
    name = _("Notifications")
    
    def __init__(self, controls):
        box = Gtk.VBox(False, 0)
        box.hide()
        
        self.check_new_version = Gtk.CheckButton(label=_("Check for new foobnix release on start"), use_underline=True)
        self.check_new_version.show()
        
        demo = Gtk.Button(_("Show new foobnix release avaliable demo dialog"))
        demo.connect("clicked", lambda * a:info_dialog_with_link_and_donate("foobnix [version]"))
        demo.show()
        
        
        box.pack_start(self.check_new_version, False, True, 0)
        box.pack_start(demo, False, False, 0)
        
        self.widget = box
    
    def on_load(self):
        self.check_new_version.set_active(FC().check_new_version)
    
    def on_save(self):        
        FC().check_new_version = self.check_new_version.get_active()
        
        
    
    

########NEW FILE########
__FILENAME__ = other_conf
#-*- coding: utf-8 -*-
'''
Created on 23 дек. 2010

@author: ivan
'''

import logging
from gi.repository import Gtk

from foobnix.fc.fc import FC
from foobnix.preferences.configs import CONFIG_OTHER
from foobnix.util.antiscreensaver import antiscreensaver
from foobnix.preferences.config_plugin import ConfigPlugin
from foobnix.helpers.dialog_entry import info_dialog_with_link_and_donate


class OtherConfig(ConfigPlugin):
    
    name = CONFIG_OTHER
    
    def __init__(self, controls):
        self.controls = controls
                
        box = Gtk.VBox(False, 0)
        box.hide()

        download_frame = Gtk.Frame(label=_("File downloads"))
        df_vbox = Gtk.VBox(False, 5)
        df_vbox.set_border_width(4)

        """save to"""

        hbox = Gtk.HBox(False, 5)
        self.online_dir = Gtk.FileChooserButton("set place")
        self.online_dir.set_action(Gtk.FileChooserAction.SELECT_FOLDER)
        self.online_dir.connect("current-folder-changed", self.on_change_folder)
        
        hbox.pack_start(Gtk.Label(_("Save online music to folder:")), False, True, 0)
        hbox.pack_start(self.online_dir, True, True, 0)
        
        """automatic save"""                
        self.automatic_save_checkbutton = Gtk.CheckButton(label=_("Automatic online music save"), use_underline=True)
        self.nosubfolder_checkbutton = Gtk.CheckButton(label=_("Save to one folder (no subfolders)"), use_underline=True)

        """download threads"""
        thbox = Gtk.HBox(False, 5)
        tab_label = Gtk.Label(_("Download in threads"))
        
        adjustment = Gtk.Adjustment(value=1, lower=1, upper=10, step_incr=1, page_incr=1, page_size=0)
        self.threads_count = Gtk.SpinButton(adjustment=adjustment)
        
        thbox.pack_start(tab_label, False, False, 0)
        thbox.pack_start(self.threads_count, False, True, 0)

        df_vbox.pack_start(hbox, False, False, 2)
        df_vbox.pack_start(self.automatic_save_checkbutton, False, False, 2)
        df_vbox.pack_start(self.nosubfolder_checkbutton, False, False, 2)
        df_vbox.pack_start(thbox, False, False, 2)
        download_frame.add(df_vbox)
        download_frame.show_all()
              
        """disc cover size"""
        dc_frame = Gtk.Frame(label=_("Disc cover settings"))

        cbox = Gtk.HBox(False, 5)
        cbox.set_border_width(4)
        
        tab_label = Gtk.Label(_("Disc cover size:"))
        
        adjustment = Gtk.Adjustment(value=1, lower=100, upper=350, step_incr=20, page_incr=50, page_size=0)
        self.image_size_spin = Gtk.SpinButton(adjustment=adjustment)
        
        cbox.pack_start(tab_label, False, False, 0)
        cbox.pack_start(self.image_size_spin, False, True, 0)

        dc_frame.add(cbox)
        dc_frame.show_all()

        """notification"""
        updates_frame = Gtk.Frame(label=_("Updates"))
        uhbox = Gtk.HBox(False, 5)
        uhbox.set_border_width(4)
        self.check_new_version = Gtk.CheckButton(label=_("Check for new foobnix release on start"), use_underline=True)

        demo = Gtk.Button(label=_("Check for update"))
        demo.connect("clicked", lambda * a: info_dialog_with_link_and_donate("foobnix [version]"))
        uhbox.pack_start(self.check_new_version, True, True, 0)
        uhbox.pack_start(demo, False, False, 0)
        updates_frame.add(uhbox)
        updates_frame.show_all()
        
        """background image"""
        theme_frame = Gtk.Frame(label=_("Theming"))
        thvbox = Gtk.VBox(False, 1)
        thvbox.set_border_width(4)
        
        """menu position"""
        pbox = Gtk.HBox(False, 5)
        pbox.show()
        
        label = Gtk.Label(_("Menu type: "))
        
        self.old_style = Gtk.RadioButton(None, _("Old Style (Menu Bar)"))
                
        self.new_style = Gtk.RadioButton.new_with_label_from_widget(self.old_style, _("New Style (Button)"))
        
        pbox.pack_start(label, False, False, 0)
        pbox.pack_start(self.new_style, False, True, 0)
        pbox.pack_start(self.old_style, False, False, 0)
        
        o_r_box = Gtk.HBox(False, 5)
        o_r_box.show()
        
        o_r_label = Gtk.Label(_("Order-Repeat Switcher Style:"))
        
        self.buttons = Gtk.RadioButton(None, _("Toggle Buttons"))
        
        self.labels = Gtk.RadioButton.new_with_label_from_widget(self.buttons, _("Text Labels"))
        
        o_r_box.pack_start(o_r_label, False, False, 0)
        o_r_box.pack_start(self.buttons, False, True, 0)
        o_r_box.pack_start(self.labels, False, False, 0)
        
        """opacity"""
        obox = Gtk.HBox(False, 5)
        obox.show()
        
        tab_label = Gtk.Label(_("Opacity:"))
        tab_label.show()
          
        adjustment = Gtk.Adjustment(value=1, lower=20, upper=100, step_incr=1, page_incr=1, page_size=0)
        self.opacity_size = Gtk.SpinButton(adjustment=adjustment)
        self.opacity_size.connect("value-changed", self.on_chage_opacity)
        self.opacity_size.show()
        
        obox.pack_start(tab_label, False, False, 0)
        obox.pack_start(self.opacity_size, False, True, 0)
        
        self.fmgrs_combo = self.fmgr_combobox()
        hcombobox = Gtk.HBox(False, 5)
        hcombobox.pack_start(Gtk.Label(_('Choose your preferred file manager:')), False, False, 0)
        hcombobox.pack_start(self.fmgrs_combo, False, False, 0)
        
        self.disable_screensaver = Gtk.CheckButton(label=_("Disable Xscreensaver"), use_underline=True)

        thvbox.pack_start(pbox, False, False, 1)
        thvbox.pack_start(o_r_box, False, False, 1)
        thvbox.pack_start(obox, False, False, 1)
        thvbox.pack_start(hcombobox, False, False, 1)
        thvbox.pack_start(self.disable_screensaver, False, False, 0)
        theme_frame.add(thvbox)
        theme_frame.show_all()
                
        """packaging"""        
        box.pack_start(download_frame, False, True, 2)
        box.pack_start(dc_frame, False, True, 2)
        box.pack_start(theme_frame, False, False, 2)
        box.pack_start(updates_frame, False, True, 2)
        
        self.widget = box
    
    def on_chage_opacity(self, *a):
        opacity = self.opacity_size.get_value() / 100
        self.controls.main_window.set_opacity(opacity)
        self.controls.preferences.set_opacity(opacity)
    
    def on_change_menu_type(self, *a):
        if self.old_style.get_active():
            FC().menu_style = "old"
        elif self.new_style.get_active():
            FC().menu_style = "new"
                
        self.controls.top_panel.update_menu_style()
    
    def on_change_folder(self, *a):
        path = self.online_dir.get_filename()       
        FC().online_save_to_folder = path        
        logging.info("Change music online folder: " + path)  
                
    def on_load(self):
        self.online_dir.set_current_folder(FC().online_save_to_folder)
        self.online_dir.set_sensitive(FC().is_save_online)
        
        """disc"""
        self.image_size_spin.set_value(FC().info_panel_image_size)
        self.threads_count.set_value(FC().amount_dm_threads)

        self.opacity_size.set_value(int(FC().window_opacity * 100))
        
        self.check_new_version.set_active(FC().check_new_version)
        
        if FC().automatic_online_save:
            self.automatic_save_checkbutton.set_active(True)

        if FC().nosubfolder:
            self.nosubfolder_checkbutton.set_active(True)

        """menu style"""
        if FC().menu_style == "new":
            self.new_style.set_active(True)        
        else: 
            self.old_style.set_active(True)
        
        if FC().order_repeat_style == "TextLabels":
            self.labels.set_active(True)
        
        self.fmgrs_combo.set_active(FC().active_manager[0])
        
        if FC().antiscreensaver:
            self.disable_screensaver.set_active(True)
            antiscreensaver()
            
    def on_save(self):
        if self.buttons.get_active():
            FC().order_repeat_style = "ToggleButtons"
        else:
            FC().order_repeat_style = "TextLabels"
        self.controls.os.on_load()
        
        FC().info_panel_image_size = self.image_size_spin.get_value_as_int()
        FC().amount_dm_threads = self.threads_count.get_value_as_int()
        
        FC().window_opacity = self.opacity_size.get_value() / 100
        FC().check_new_version = self.check_new_version.get_active()
        
        FC().automatic_online_save = self.automatic_save_checkbutton.get_active()
        FC().nosubfolder = self.nosubfolder_checkbutton.get_active()

        FC().active_manager = [self.fmgrs_combo.get_active(), self.fmgrs_combo.get_active_text().lower()]
        
        if self.disable_screensaver.get_active():
            FC().antiscreensaver = True
            antiscreensaver()
        else:
            FC().antiscreensaver = False
            
        self.on_change_menu_type()
        
    def fmgr_combobox(self):
        combobox = Gtk.ComboBoxText()
        combobox.append_text('--- Auto ---')
        combobox.append_text('Nautilus')
        combobox.append_text('Dolphin')
        combobox.append_text('Konqueror')
        combobox.append_text('Thunar')
        combobox.append_text('PCManFM')
        combobox.append_text('Krusader')
        combobox.append_text('Explorer')
        
        combobox.set_active(0)
        
        return combobox
########NEW FILE########
__FILENAME__ = tabs
#-*- coding: utf-8 -*-
'''
Created on 24 авг. 2010

@author: ivan
'''

from foobnix.preferences.config_plugin import ConfigPlugin
from gi.repository import Gtk
from foobnix.helpers.my_widgets import tab_close_button
from foobnix.fc.fc import FC


class TabsConfig(ConfigPlugin):
    
    name = _("Tabs")
    
    def __init__(self, controls):
        self.controls = controls
        box = Gtk.VBox(False, 0)
        box.hide()
        
        """count"""
        cbox = Gtk.HBox(False, 0)
        cbox.show()
        
        tab_label = Gtk.Label(_("Count of tabs:"))
        tab_label.set_size_request(150, -1)
        tab_label.set_alignment(0, .5)
        
        adjustment = Gtk.Adjustment(value=1, lower=1, upper=20, step_incr=1, page_incr=10, page_size=0)
        self.tabs_count = Gtk.SpinButton(adjustment=adjustment)
        
        cbox.pack_start(tab_label, False, False, 0)
        cbox.pack_start(self.tabs_count, False, True, 0)
                
        """len"""
        lbox = Gtk.HBox(False, 0)
        lbox.show()
        
        tab_label = Gtk.Label(_("Max length of tab:"))
        tab_label.set_size_request(150, -1)
        tab_label.set_alignment(0, .5)
        
        adjustment = Gtk.Adjustment(value=0, lower=-1, upper=300, step_incr=1, page_incr=10, page_size=0)
        self.tab_len = Gtk.SpinButton(adjustment=adjustment)
        
        lbox.pack_start(tab_label, False, False, 0)
        lbox.pack_start(self.tab_len, False, True, 0)
        
        """position"""
        pbox = Gtk.HBox(False, 10)
        
        label = Gtk.Label(_("Tab position:"))
        label.set_size_request(150, -1)
        label.set_alignment(0, .5)
        
        self.radio_tab_left = Gtk.RadioButton(None, _("Left"))
        self.radio_tab_left.set_size_request(55, -1)
        
        self.radio_tab_top = Gtk.RadioButton.new_with_label_from_widget(self.radio_tab_left, _("Top"))
        self.radio_tab_top.set_size_request(55, -1)
        
        self.radio_tab_no = Gtk.RadioButton.new_with_label_from_widget(self.radio_tab_left, _("No Tabs"))
        self.radio_tab_no.set_size_request(55, -1)
        
        pbox.pack_start(label, False, False, 0)
        pbox.pack_start(self.radio_tab_left, False, False, 0)
        pbox.pack_start(self.radio_tab_top, False, False, 0)
        pbox.pack_start(self.radio_tab_no, False, False, 0)
        
        """closed type """
        close_label_box = Gtk.HBox(False, 10)
        
        close_label = Gtk.Label(_("Close tab sign:"))
        close_label.set_size_request(150, -1)
        close_label.set_alignment(0, .5)
        
        self.radio_tab_label = Gtk.RadioButton(None, "x")
        self.radio_tab_label.set_size_request(55, -1)
        
        self.radio_tab_button = Gtk.RadioButton.new_from_widget(self.radio_tab_label)
        
        self.tab_close_box = Gtk.HBox()
        self.tab_close_box.pack_start(self.radio_tab_button, False, True, 0)
        self.tab_close_box.pack_start(tab_close_button(), False, False, 0)
        self.tab_close_box.set_size_request(55, -1)
        
        self.radio_tab_none = Gtk.RadioButton.new_with_label_from_widget(self.radio_tab_label, _("None"))
        self.radio_tab_none.set_size_request(55, -1)
        
        close_label_box.pack_start(close_label, False, False, 0)
        close_label_box.pack_start(self.radio_tab_label, False, False, 0)
        close_label_box.pack_start(self.tab_close_box, False, False, 0)
        close_label_box.pack_start(self.radio_tab_none, False, False, 0)
                
        """global pack"""
        box.pack_start(cbox, False, True, 2)
        box.pack_start(lbox, False, True, 2)
        box.pack_start(pbox, False, True, 2)
        box.pack_start(close_label_box, False, True, 2)
        box.show_all()
        
        self.widget = box
        
    
    def removing_of_extra_tabs(self, number_of_tabs):
        overage = self.controls.notetabs.get_n_pages() - number_of_tabs
        while overage > 0:
            self.controls.notetabs.remove_page(self.controls.notetabs.get_n_pages() - 1)
            overage -= 1
   
    def on_load(self):
        self.tabs_count.set_value(FC().count_of_tabs)
        self.tab_len.set_value(FC().len_of_tab)
        
        if  FC().tab_position == "left":
            self.radio_tab_left.set_active(True)
        
        elif  FC().tab_position == "top":
            self.radio_tab_top.set_active(True)
        
        elif FC().tab_position == "no":
            self.radio_tab_no.set_active(True)
            
        if  FC().tab_close_element == "label":
            self.radio_tab_label.set_active(True)
            
        elif FC().tab_close_element == "button":
            self.radio_tab_button.set_active(True)
            
        else: self.radio_tab_none.set_active(True)
            
    def on_save(self):
        FC().count_of_tabs = self.tabs_count.get_value_as_int()
        
        if self.controls.notetabs.get_n_pages() > FC().count_of_tabs:
            self.removing_of_extra_tabs(FC().count_of_tabs) 
        FC().len_of_tab = self.tab_len.get_value_as_int()
        
        if self.radio_tab_label.get_active():
            FC().tab_close_element = "label"
        elif self.radio_tab_button.get_active():
            FC().tab_close_element = "button"
        else: 
            FC().tab_close_element = None
        
        if self.radio_tab_left.get_active():
            FC().tab_position = "left"
            self.controls.notetabs.set_tab_left()
        elif self.radio_tab_top.get_active(): 
            FC().tab_position = "top"
            self.controls.notetabs.set_tab_top()
        else: 
            FC().tab_position = "no"
            self.controls.notetabs.set_tab_no()
            
        self.controls.notetabs.crop_all_tab_names()

########NEW FILE########
__FILENAME__ = tray_icon_conf
#-*- coding: utf-8 -*-
'''
Created on 24 авг. 2010

@author: ivan
'''

from gi.repository import Gtk

from foobnix.fc.fc import FC
from foobnix.util import const
from foobnix.preferences.config_plugin import ConfigPlugin
from foobnix.helpers.image import ImageBase
from foobnix.util.const import ICON_BLANK_DISK
from foobnix.gui.service.path_service import get_foobnix_resourse_path_by_name
from foobnix.helpers.pref_widgets import FrameDecorator, VBoxDecorator, ChooseDecorator, \
    IconBlock


class TrayIconConfig(ConfigPlugin):

    name = ("Tray Icon")

    def __init__(self, controls):
        self.controls = controls
        box = Gtk.VBox(False, 0)
        box.hide()

        '''static_icon'''
        self.static_icon = IconBlock("Icon", controls, FC().static_icon_entry)

        """dynamic icons"""
        self.play_icon = IconBlock("Play", controls, FC().play_icon_entry)
        self.pause_icon = IconBlock("Pause", controls, FC().pause_icon_entry)
        self.stop_icon = IconBlock("Stop", controls, FC().stop_icon_entry)
        self.radio_icon = IconBlock("Radio", controls, FC().radio_icon_entry)

        self.tray_icon_button = Gtk.CheckButton(label=_("Show tray icon"), use_underline=True)
        self.hide_in_tray_on_start = Gtk.CheckButton(label=_("Hide player in tray on start"), use_underline=True)
        #self.tray_icon_button.connect("clicked", self.on_show_tray_icon)

        self.close_button = Gtk.RadioButton(group=None, label=_("On close window - close player"))

        self.hide_button = Gtk.RadioButton(group=self.close_button, label=_("On close window - hide player"))
        self.hide_button.connect("toggled", self.on_show_tray_icon)

        self.minimize_button = Gtk.RadioButton(group=self.close_button, label=_("On close window - minimize player"))

        """system icon"""
        self.static_tray_icon = ChooseDecorator(None, FrameDecorator(_("System Icon Static"), self.static_icon))

        """dynamic icons"""
        line = VBoxDecorator(self.play_icon,
                             self.pause_icon,
                             self.stop_icon,
                             self.radio_icon)

        self.icon_controls = ChooseDecorator(self.static_tray_icon.get_radio_button(), FrameDecorator(_("System Icons Dynamic"), line))

        """disc image icon"""
        image = ImageBase(ICON_BLANK_DISK, 30)
        self.change_tray_icon = ChooseDecorator(self.static_tray_icon.get_radio_button(), FrameDecorator(_("Disc cover image"), image))

        self.notifier = Gtk.CheckButton(_("Notification pop-up"))
        self.notifier.connect("toggled", self.on_toggle)

        self.n_time = self.notify_time()

        box.pack_start(self.hide_in_tray_on_start, False, True, 0)
        box.pack_start(self.tray_icon_button, False, True, 0)
        box.pack_start(self.close_button, False, True, 0)
        box.pack_start(self.hide_button, False, True, 0)
        box.pack_start(self.minimize_button, False, True, 0)

        box.pack_start(self.static_tray_icon, True, True, 0)
        box.pack_start(self.icon_controls, True, True, 0)
        box.pack_start(self.change_tray_icon, False, False, 0)

        notifier_box = Gtk.VBox()
        notifier_box.pack_start(self.notifier, False, False, 0)
        notifier_box.pack_start(self.n_time, False, False, 0)
        box.pack_start(FrameDecorator(_("Notification"), notifier_box), False, False, 0)
        self.widget = box

    def on_show_tray_icon(self, *args):
        if not self.tray_icon_button.get_active():
            self.hide_button.set_sensitive(False)
            if self.hide_button.get_active():
                self.minimize_button.set_active(True)
            self.controls.trayicon.hide()
        else:
            self.controls.trayicon.show()
            self.hide_button.set_sensitive(True)

    def on_static_icon(self):
        if FC().static_tray_icon:
            FC().static_icon_entry = self.static_icon.get_active_path()
            self.controls.trayicon.set_from_resource(FC().static_icon_entry)

    def check_active_dynamic_icon(self, icon_object):
        icon_name = icon_object.entry.get_text()
        try:
            path = get_foobnix_resourse_path_by_name(icon_name)
            self.controls.trayicon.set_image_from_path(path)
        except TypeError:
            pass

    def notify_time(self):
        label = Gtk.Label(_("Time Notification (sec): "))

        self.adjustment = Gtk.Adjustment(value=0, lower=1, upper=10, step_incr=0.5)

        not_len = Gtk.SpinButton(adjustment=self.adjustment, climb_rate=0.0, digits=1)
        not_len.show()

        hbox = Gtk.HBox(False, 5)
        hbox.pack_start(label, False, False, 0)
        hbox.pack_start(not_len, False, False, 0)
        hbox.show_all()
        hbox.set_sensitive(False)

        return hbox

    def on_toggle(self, *a):
            if self.notifier.get_active():
                self.n_time.set_sensitive(True)
            else:
                self.n_time.set_sensitive(False)

    def on_load(self):
        self.tray_icon_button.set_active(FC().show_tray_icon)
        self.static_tray_icon.button.set_active(FC().static_tray_icon)
        self.icon_controls.button.set_active(FC().system_icons_dinamic)
        self.change_tray_icon.button.set_active(FC().change_tray_icon)
        self.hide_in_tray_on_start.set_active(FC().hide_on_start)

        if FC().on_close_window == const.ON_CLOSE_CLOSE:
            self.close_button.set_active(True)

        elif FC().on_close_window == const.ON_CLOSE_HIDE:
            self.hide_button.set_active(True)

        elif FC().on_close_window == const.ON_CLOSE_MINIMIZE:
            self.minimize_button.set_active(True)

        if FC().notifier:
            self.notifier.set_active(True)
            self.n_time.set_sensitive(True)
        self.adjustment.set_value(FC().notify_time / 1000)

        self.static_icon.entry.set_text(FC().static_icon_entry)
        self.play_icon.entry.set_text(FC().play_icon_entry)
        self.pause_icon.entry.set_text(FC().pause_icon_entry)
        self.stop_icon.entry.set_text(FC().stop_icon_entry)
        self.radio_icon.entry.set_text(FC().radio_icon_entry)

    def on_save(self):
        FC().show_tray_icon = self.tray_icon_button.get_active()
        FC().hide_on_start =  self.hide_in_tray_on_start.get_active()
        FC().static_tray_icon = self.static_tray_icon.button.get_active()

        if FC().static_tray_icon:
            self.on_static_icon()

        if FC().system_icons_dinamic:
            FC().play_icon_entry = self.play_icon.get_active_path()
            FC().pause_icon_entry = self.pause_icon.get_active_path()
            FC().stop_icon_entry = self.stop_icon.get_active_path()
            FC().radio_icon_entry = self.radio_icon.get_active_path()

        FC().system_icons_dinamic = self.icon_controls.button.get_active()

        FC().change_tray_icon = self.change_tray_icon.button.get_active()

        if  self.close_button.get_active():
            FC().on_close_window = const.ON_CLOSE_CLOSE

        elif self.hide_button.get_active():
            FC().on_close_window = const.ON_CLOSE_HIDE

        elif self.minimize_button.get_active():
            FC().on_close_window = const.ON_CLOSE_MINIMIZE

        if self.notifier.get_active():
            FC().notifier = True
        else:
            FC().notifier = False

        FC().static_icon_entry = self.static_icon.entry.get_text()
        FC().play_icon_entry = self.play_icon.entry.get_text()
        FC().pause_icon_entry = self.pause_icon.entry.get_text()
        FC().stop_icon_entry = self.stop_icon.entry.get_text()
        FC().radio_icon_entry = self.radio_icon.entry.get_text()
        FC().notify_time = int(self.adjustment.get_value() * 1000)

        if IconBlock.temp_list != FC().all_icons:
            FC().all_icons = IconBlock.temp_list

        self.on_show_tray_icon()
########NEW FILE########
__FILENAME__ = config_plugin
#-*- coding: utf-8 -*-
'''
Created on 24 авг. 2010

@author: ivan
'''
class ConfigPlugin():
    name = 'undefined'
    widget = "error"
    
    def show(self):
        self.widget.show()
    
    def hide(self):
        self.widget.hide()
    
    def on_load(self):
        pass
    
    def on_save(self):
        pass
    
    

########NEW FILE########
__FILENAME__ = preferences_window
#!/usr/bin/env python

# example packbox.py

import os
import thread
import logging
from gi.repository import Gtk
from gi.repository import GLib

from foobnix.fc.fc import FC
from foobnix.gui.model import FDModel
from foobnix.gui.state import LoadSave
from foobnix.gui.model.signal import FControl
from foobnix.gui.treeview.simple_tree import SimpleListTreeControl
from foobnix.helpers.window import ChildTopWindow
from foobnix.preferences.configs.tabs import TabsConfig
from foobnix.preferences.configs.last_fm import LastFmConfig
from foobnix.preferences.configs import CONFIG_MUSIC_LIBRARY
from foobnix.preferences.configs.other_conf import OtherConfig
from foobnix.preferences.configs.network_conf import NetworkConfig
from foobnix.preferences.configs.tray_icon_conf import TrayIconConfig
from foobnix.preferences.configs.music_library import MusicLibraryConfig
from foobnix.util import analytics


class PreferencesWindow(ChildTopWindow, FControl, LoadSave):

    configs = []
    POS_NAME = 0

    def __init__(self, controls):
        FControl.__init__(self, controls)
        thread.start_new_thread(self.lazy_init, (True,) )

    def lazy_init(self, sleep=False):
        controls = self.controls
        self.configs.append(MusicLibraryConfig(controls))
        self.configs.append(TabsConfig(controls))
        self.configs.append(LastFmConfig(controls))
        self.configs.append(TrayIconConfig(controls))
        self.configs.append(NetworkConfig(controls))

        try:
            """check keybinder installed, debian"""
            from gi.repository import Keybinder #@UnresolvedImport @UnusedImport
            from foobnix.preferences.configs.hotkey_conf import HotKeysConfig
            self.configs.append(HotKeysConfig(controls))
        except Exception, e:
            logging.warn("Keybinder not installed" + str(e))

        self.configs.append(OtherConfig(controls))

        self.label = None

        mainVBox = Gtk.VBox(False, 0)

        ChildTopWindow.__init__(self, _("Preferences"), 900, 550)

        paned = Gtk.HPaned()
        paned.set_position(250)

        def func():
            bean = self.navigation.get_selected_bean()
            if bean:
                self.populate_config_category(bean.text)

        self.navigation = SimpleListTreeControl(_("Categories"), controls, True)

        for plugin in self.configs:
            self.navigation.append(FDModel(plugin.name))

        self.navigation.set_left_click_func(func)

        paned.add1(self.navigation.scroll)

        cbox = Gtk.VBox(False, 0)
        for plugin in self.configs:
            cbox.pack_start(plugin.widget, False, True, 0)

        self._container = self.create_container(cbox)
        paned.add2(self._container)

        mainVBox.pack_start(paned, True, True, 0)
        mainVBox.pack_start(self.create_save_cancel_buttons(), False, False, 0)

        #self.add(mainVBox)
        GLib.idle_add(self.add, mainVBox)

    def show(self, current=CONFIG_MUSIC_LIBRARY):
        self.show_all()
        self.populate_config_category(current)
        self.on_load()
        analytics.action("PreferencesWindow")

    def on_load(self):
        logging.debug("LOAD PreferencesWindow")
        for plugin in self.configs:
            plugin.on_load()

    def on_save(self):
        for plugin in self.configs:
            plugin.on_save()
        FC().save()
        bean = self.navigation.get_selected_bean()
        if bean:
            self.populate_config_category(bean.text)

    def hide_window(self, *a):
        self.hide()
        for plugin in self.configs:
            if hasattr(plugin, "on_close"):
                plugin.on_close()
        self.navigation.set_cursor_on_cell(Gtk.TreePath(0), None, None, False)
        return True

    def populate_config_category(self, name):
        for plugin in self.configs:
            if plugin.name == name:
                plugin.widget.show()
                try:
                    self.update_label(name)
                except:
                    pass
            else:
                plugin.widget.hide()

    def create_save_cancel_buttons(self):
        box = Gtk.HBox(False, 0)
        box.show()

        button_restore = Gtk.Button(_("Restore Defaults Settings"))
        button_restore.connect("clicked", lambda * a: self.restore_defaults())
        button_restore.show()

        button_apply = Gtk.Button(_("Apply"))
        button_apply.set_size_request(100, -1)
        button_apply.connect("clicked", lambda * a: self.on_save())
        button_apply.show()

        button_close = Gtk.Button(_("Close"))
        button_close.set_size_request(100, -1)
        button_close.connect("clicked", self.hide_window)
        button_close.show()

        empty = Gtk.Label("")
        empty.show()

        box.pack_start(button_restore, False, True, 0)
        box.pack_start(empty, True, True, 0)
        box.pack_start(button_apply, False, True, 0)
        box.pack_start(button_close, False, True, 0)

        return box

    def restore_defaults(self):
        logging.debug("restore defaults settings")
        Gtk.main_quit()
        FC().delete()
        thread.start_new_thread(os.system, ("foobnix",))


    def update_label(self, title):
        self.label.set_markup('<b><i><span  size="x-large" >' + title + '</span></i></b>');

    def create_container(self, widget):
        box = Gtk.VBox(False, 0)
        box.show()

        self.label = Gtk.Label()
        self.label.show()

        separator = Gtk.HSeparator.new()
        separator.show()

        box.pack_start(self.label, False, True, 0)
        box.pack_start(separator, False, True, 0)
        box.pack_start(widget, False, True, 0)

        return box

if __name__ == "__main__":
    w = PreferencesWindow(None)
    w.show()
    Gtk.main()

########NEW FILE########
__FILENAME__ = lyr
# -*- coding: utf-8 -*-
#       lyricwiki.py
#       
#       Copyright 2009 Amr Hassan <amr.hassan@gmail.com>
#       
#       This program is free software; you can redistribute it and/or modify
#       it under the terms of the GNU General Public License as published by
#       the Free Software Foundation; either version 2 of the License, or
#       (at your option) any later version.
#       
#       This program is distributed in the hope that it will be useful,
#       but WITHOUT ANY WARRANTY; without even the implied warranty of
#       MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#       GNU General Public License for more details.
#       
#       You should have received a copy of the GNU General Public License
#       along with this program; if not, write to the Free Software
#       Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston,
#       MA 02110-1301, USA.

import simplejson, urllib, os, hashlib, time
import urllib2

def _download(args):
    """
        Downloads the json response and returns it
    """
    
    base = "http://lyrics.wikia.com/api.php?"
    
    str_args = {}
    for key in args:
        str_args[key] = args[key].encode("utf-8")
    
    args = urllib.urlencode(str_args)
    
    return urllib2.urlopen(base + args, timeout=7).read()

def _get_page_titles(artist, title):
    """
        Returns a list of available page titles
    """
    
    args = {"action": "query",
        "list": "search",
        "srsearch": artist + " " + title,
        "format": "json",
        }
    
    titles = ["%s:%s" % (artist, title), "%s:%s" % (artist.title(), title.title())]
    content = simplejson.loads(_download(args))
    for t in content["query"]["search"]:
        titles.append(t["title"])
    
    return titles

def _get_lyrics(artist, title):
    
    for page_title in _get_page_titles(artist, title):
        args = {"action": "query",
            "prop": "revisions",
            "rvprop": "content",
            "titles": page_title,
            "format": "json",
            }
        
        revisions = simplejson.loads(_download(args))["query"]["pages"].popitem()[1]
        
        if not "revisions" in revisions:
            continue
            
        content = revisions["revisions"][0]["*"]
        
        if content.startswith("#Redirect"):
            n_title = content[content.find("[[") + 2:content.rfind("]]")]
            return _get_lyrics(*n_title.split(":"))
        
        if "<lyrics>" in content:
            return content[content.find("<lyrics>") + len("<lyrics>") : content.find("</lyrics>")].strip()
        elif "<lyric>" in content:
            return content[content.find("<lyric>") + len("<lyric>") : content.find("</lyric>")].strip()

def get_lyrics(artist, title, cache_dir=None):
    #return "Lyrics Disabled"

    """
        Get lyrics by artist and title
        set cache_dir to a valid (existing) directory
        to enable caching.
    """
    
    path = None
    
    if cache_dir and os.path.exists(cache_dir):
        digest = hashlib.sha1(artist.lower().encode("utf-8") + title.lower().encode("utf-8")).hexdigest()
        path = os.path.join(cache_dir, digest)
        
        if os.path.exists(path):
            fp = open(path)
            return simplejson.load(fp)["lyrics"].strip()
    
    lyrics = _get_lyrics(artist, title)
    
    if path and lyrics:
        fp = open(path, "w")
        simplejson.dump({"time": time.time(), "artist": artist, "title": title,
                    "source": "lyricwiki", "lyrics": lyrics }, fp, indent=4)
        fp.close()
    
    return lyrics

########NEW FILE########
__FILENAME__ = pylast
#
# pylast - A Python interface to Last.fm (and other API compatible social networks)
# Copyright (C) 2008-2009  Amr Hassan
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
# Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA 02111-1307
# USA
#
# http://code.google.com/p/pylast/

import datetime
import base64
import urllib2
import logging
import hashlib
import httplib
import urllib
import threading
import xml.dom
import time
import shelve
import tempfile
import sys
import htmlentitydefs

try:
    import collections
except ImportError:
    pass

from xml.dom import minidom
from foobnix.fc.fc import FC

__version__ = '0.4'
__author__ = 'Amr Hassan'
__copyright__ = "Copyright (C) 2008-2009  Amr Hassan"
__license__ = "gpl"
__email__ = 'amr.hassan@gmail.com'

STATUS_INVALID_SERVICE = 2
STATUS_INVALID_METHOD = 3
STATUS_AUTH_FAILED = 4
STATUS_INVALID_FORMAT = 5
STATUS_INVALID_PARAMS = 6
STATUS_INVALID_RESOURCE = 7
STATUS_TOKEN_ERROR = 8
STATUS_INVALID_SK = 9
STATUS_INVALID_API_KEY = 10
STATUS_OFFLINE = 11
STATUS_SUBSCRIBERS_ONLY = 12
STATUS_INVALID_SIGNATURE = 13
STATUS_TOKEN_UNAUTHORIZED = 14
STATUS_TOKEN_EXPIRED = 15

EVENT_ATTENDING = '0'
EVENT_MAYBE_ATTENDING = '1'
EVENT_NOT_ATTENDING = '2'

PERIOD_OVERALL = 'overall'
PERIOD_3MONTHS = '3month'
PERIOD_6MONTHS = '6month'
PERIOD_12MONTHS = '12month'

DOMAIN_ENGLISH = 0
DOMAIN_GERMAN = 1
DOMAIN_SPANISH = 2
DOMAIN_FRENCH = 3
DOMAIN_ITALIAN = 4
DOMAIN_POLISH = 5
DOMAIN_PORTUGUESE = 6
DOMAIN_SWEDISH = 7
DOMAIN_TURKISH = 8
DOMAIN_RUSSIAN = 9
DOMAIN_JAPANESE = 10
DOMAIN_CHINESE = 11

COVER_SMALL = 0
COVER_MEDIUM = 1
COVER_LARGE = 2
COVER_EXTRA_LARGE = 3
COVER_MEGA = 4

IMAGES_ORDER_POPULARITY = "popularity"
IMAGES_ORDER_DATE = "dateadded"


USER_MALE = 'Male'
USER_FEMALE = 'Female'

SCROBBLE_SOURCE_USER = "P"
SCROBBLE_SOURCE_NON_PERSONALIZED_BROADCAST = "R"
SCROBBLE_SOURCE_PERSONALIZED_BROADCAST = "E"
SCROBBLE_SOURCE_LASTFM = "L"
SCROBBLE_SOURCE_UNKNOWN = "U"

SCROBBLE_MODE_PLAYED = ""
SCROBBLE_MODE_LOVED = "L"
SCROBBLE_MODE_BANNED = "B"
SCROBBLE_MODE_SKIPPED = "S"

"""
A list of the implemented webservices (from http://www.last.fm/api/intro)
=====================================
# Album

    * album.addTags            DONE
    * album.getInfo            DONE
    * album.getTags            DONE
    * album.removeTag        DONE
    * album.search             DONE

# Artist

    * artist.addTags         DONE
    * artist.getEvents         DONE
    * artist.getImages         DONE
    * artist.getInfo         DONE
    * artist.getPodcast     TODO
    * artist.getShouts         DONE
    * artist.getSimilar     DONE
    * artist.getTags         DONE
    * artist.getTopAlbums     DONE
    * artist.getTopFans     DONE
    * artist.getTopTags     DONE
    * artist.getTopTracks     DONE
    * artist.removeTag         DONE
    * artist.search         DONE
    * artist.share             DONE
    * artist.shout             DONE

# Auth

    * auth.getMobileSession DONE
    * auth.getSession         DONE
    * auth.getToken         DONE

# Event

    * event.attend             DONE
    * event.getAttendees     DONE
    * event.getInfo            DONE
    * event.getShouts         DONE
    * event.share             DONE
    * event.shout             DONE

# Geo

    * geo.getEvents
    * geo.getTopArtists
    * geo.getTopTracks

# Group

    * group.getMembers                DONE
    * group.getWeeklyAlbumChart        DONE
    * group.getWeeklyArtistChart    DONE
    * group.getWeeklyChartList        DONE
    * group.getWeeklyTrackChart        DONE

# Library

    * library.addAlbum        DONE
    * library.addArtist        DONE
    * library.addTrack        DONE
    * library.getAlbums        DONE
    * library.getArtists    DONE
    * library.getTracks        DONE

# Playlist

    * playlist.addTrack    DONE
    * playlist.create    DONE
    * playlist.fetch    DONE

# Radio

    * radio.getPlaylist
    * radio.tune

# Tag

    * tag.getSimilar    DONE
    * tag.getTopAlbums    DONE
    * tag.getTopArtists    DONE
    * tag.getTopTags    DONE
    * tag.getTopTracks    DONE
    * tag.getWeeklyArtistChart    DONE
    * tag.getWeeklyChartList    DONE
    * tag.search    DONE

# Tasteometer

    * tasteometer.compare    DONE

# Track

    * track.addTags    DONE
    * track.ban    DONE
    * track.getInfo    DONE
    * track.getSimilar    DONE
    * track.getTags    DONE
    * track.getTopFans    DONE
    * track.getTopTags    DONE
    * track.love    DONE
    * track.removeTag    DONE
    * track.search    DONE
    * track.share    DONE

# User

    * user.getEvents    DONE
    * user.getFriends    DONE
    * user.getInfo    DONE
    * user.getLovedTracks    DONE
    * user.getNeighbours    DONE
    * user.getPastEvents    DONE
    * user.getPlaylists    DONE
    * user.getRecentStations    TODO
    * user.getRecentTracks    DONE
    * user.getRecommendedArtists    DONE
    * user.getRecommendedEvents    DONE
    * user.getShouts    DONE
    * user.getTopAlbums    DONE
    * user.getTopArtists    DONE
    * user.getTopTags    DONE
    * user.getTopTracks    DONE
    * user.getWeeklyAlbumChart    DONE
    * user.getWeeklyArtistChart    DONE
    * user.getWeeklyChartList    DONE
    * user.getWeeklyTrackChart    DONE
    * user.shout    DONE

# Venue

    * venue.getEvents    DONE
    * venue.getPastEvents    DONE
    * venue.search    DONE
"""

class Network(object):
    """
        A music social network website that is Last.fm or one exposing a Last.fm compatible API
    """

    def __init__(self, name, homepage, ws_server, api_key, api_secret, session_key, submission_server, username, password_hash,
                    domain_names, urls):
        """
            name: the name of the network
            homepage: the homepage url
            ws_server: the url of the webservices server
            api_key: a provided API_KEY
            api_secret: a provided API_SECRET
            session_key: a generated session_key or None
            submission_server: the url of the server to which tracks are submitted (scrobbled)
            username: a username of a valid user
            password_hash: the output of pylast.md5(password) where password is the user's password thingy
            domain_names: a dict mapping each DOMAIN_* value to a string domain name
            urls: a dict mapping types to urls

            if username and password_hash were provided and not session_key, session_key will be
            generated automatically when needed.

            Either a valid session_key or a combination of username and password_hash must be present for scrobbling.

            You should use a preconfigured network object through a get_*_network(...) method instead of creating an object
            of this class, unless you know what you're doing.
        """

        self.ws_server = ws_server
        self.submission_server = submission_server
        self.name = name
        self.homepage = homepage
        self.api_key = api_key
        self.api_secret = api_secret
        self.session_key = session_key
        self.username = username
        self.password_hash = password_hash
        self.domain_names = domain_names
        self.urls = urls

        self.cache_backend = None
        self.proxy_enabled = False
        self.proxy = None

        """Changed by zablab1"""
        if FC().proxy_enable and FC().proxy_url:
            self.enable_proxy(FC().proxy_url)

        self.last_call_time = 0

        #generate a session_key if necessary
        if (self.api_key and self.api_secret) and not self.session_key and (self.username and self.password_hash):
            sk_gen = SessionKeyGenerator(self)
            self.session_key = sk_gen.get_session_key(self.username, self.password_hash)

    def get_artist(self, artist_name):
        """
            Return an Artist object
        """

        return Artist(artist_name, self)

    def get_track(self, artist, title):
        """
            Return a Track object
        """

        return Track(artist, title, self)

    def get_album(self, artist, title):
        """
            Return an Album object
        """

        return Album(artist, title, self)

    def get_authenticated_user(self):
        """
            Returns the authenticated user
        """

        return AuthenticatedUser(self)

    def get_country(self, country_name):
        """
            Returns a country object
        """

        return Country(country_name, self)

    def get_group(self, name):
        """
            Returns a Group object
        """

        return Group(name, self)

    def get_user(self, username):
        """
            Returns a user object
        """

        return User(username, self)

    def get_tag(self, name):
        """
            Returns a tag object
        """

        return Tag(name, self)

    def get_scrobbler(self, client_id, client_version):
        """
            Returns a Scrobbler object used for submitting tracks to the server

            Quote from http://www.last.fm/api/submissions:
            ========
            Client identifiers are used to provide a centrally managed database of
            the client versions, allowing clients to be banned if they are found to
            be behaving undesirably. The client ID is associated with a version
            number on the server, however these are only incremented if a client is
            banned and do not have to reflect the version of the actual client application.

            During development, clients which have not been allocated an identifier should
            use the identifier tst, with a version number of 1.0. Do not distribute code or
            client implementations which use this test identifier. Do not use the identifiers
            used by other clients.
            =========

            To obtain a new client identifier please contact:
                * Last.fm: submissions@last.fm
                * # TODO: list others

            ...and provide us with the name of your client and its homepage address.
        """

        return Scrobbler(self, client_id, client_version)

    def _get_language_domain(self, domain_language):
        """
            Returns the mapped domain name of the network to a DOMAIN_* value
        """

        if domain_language in self.domain_names:
            return self.domain_names[domain_language]

    def _get_url(self, domain, type):
        return "http://%s/%s" % (self._get_language_domain(domain), self.urls[type])

    def _get_ws_auth(self):
        """
            Returns a (API_KEY, API_SECRET, SESSION_KEY) tuple.
        """
        return (self.api_key, self.api_secret, self.session_key)

    def _delay_call(self):
        """
            Makes sure that web service calls are at least a second apart
        """

        # delay time in seconds
        DELAY_TIME = 1.0
        now = time.time()

        if (now - self.last_call_time) < DELAY_TIME:
            time.sleep(1)

        self.last_call_time = now

    def create_new_playlist(self, title, description):
        """
            Creates a playlist for the authenticated user and returns it
                title: The title of the new playlist.
                description: The description of the new playlist.
        """

        params = {}
        params['title'] = _unicode(title)
        params['description'] = _unicode(description)

        doc = _Request(self, 'playlist.create', params).execute(False)

        e_id = doc.getElementsByTagName("id")[0].firstChild.data
        user = doc.getElementsByTagName('playlists')[0].getAttribute('user')

        return Playlist(user, e_id, self)

    def get_top_tags(self, limit=None):
        """Returns a sequence of the most used tags as a sequence of TopItem objects."""

        doc = _Request(self, "tag.getTopTags").execute(True)
        seq = []
        for node in doc.getElementsByTagName("tag"):
            tag = Tag(_extract_data(node, "name"), self)
            weight = _number(_extract_data(node, "count"))

            if len(seq) < limit:
                seq.append(TopItem(tag, weight))

        return seq

    def enable_proxy(self, proxy):
        """Enable a web proxy"""
        """Changed by zavlab1"""
        if not proxy:
            logging.warn("No proxy url is specified")
            return
        index = proxy.find(":")
        host = proxy[:index]
        port = proxy[index + 1:]
        self.proxy = [host, _number(port)]
        self.proxy_enabled = True
        logging.info("Enable proxy for last.fm " + proxy)

    def disable_proxy(self):
        """Disable using the web proxy"""

        self.proxy_enabled = False

    def is_proxy_enabled(self):
        """Returns True if a web proxy is enabled."""

        return self.proxy_enabled

    def _get_proxy(self):
        """Returns proxy details."""

        return self.proxy

    def enable_caching(self, file_path=None):
        """Enables caching request-wide for all cachable calls.
        In choosing the backend used for caching, it will try _SqliteCacheBackend first if
        the module sqlite3 is present. If not, it will fallback to _ShelfCacheBackend which uses shelve.Shelf objects.

        * file_path: A file path for the backend storage file. If
        None set, a temp file would probably be created, according the backend.
        """

        if not file_path:
            file_path = tempfile.mktemp(prefix="pylast_tmp_")

        self.cache_backend = _ShelfCacheBackend(file_path)

    def disable_caching(self):
        """Disables all caching features."""

        self.cache_backend = None

    def is_caching_enabled(self):
        """Returns True if caching is enabled."""

        return not (self.cache_backend == None)

    def _get_cache_backend(self):

        return self.cache_backend

    def search_for_album(self, album_name):
        """Searches for an album by its name. Returns a AlbumSearch object.
        Use get_next_page() to retreive sequences of results."""

        return AlbumSearch(album_name, self)

    def search_for_artist(self, artist_name):
        """Searches of an artist by its name. Returns a ArtistSearch object.
        Use get_next_page() to retreive sequences of results."""

        return ArtistSearch(artist_name, self)

    def search_for_tag(self, tag_name):
        """Searches of a tag by its name. Returns a TagSearch object.
        Use get_next_page() to retreive sequences of results."""

        return TagSearch(tag_name, self)

    def search_for_track(self, artist_name, track_name):
        """Searches of a track by its name and its artist. Set artist to an empty string if not available.
        Returns a TrackSearch object.
        Use get_next_page() to retreive sequences of results."""

        return TrackSearch(artist_name, track_name, self)

    def search_for_venue(self, venue_name, country_name):
        """Searches of a venue by its name and its country. Set country_name to an empty string if not available.
        Returns a VenueSearch object.
        Use get_next_page() to retreive sequences of results."""

        return VenueSearch(venue_name, country_name, self)

    def get_track_by_mbid(self, mbid):
        """Looks up a track by its MusicBrainz ID"""

        params = {"mbid": _unicode(mbid)}

        doc = _Request(self, "track.getInfo", params).execute(True)

        return Track(_extract_data(doc, "name", 1), _extract_data(doc, "name"), self)

    def get_artist_by_mbid(self, mbid):
        """Loooks up an artist by its MusicBrainz ID"""

        params = {"mbid": _unicode(mbid)}

        doc = _Request(self, "artist.getInfo", params).execute(True)

        return Artist(_extract_data(doc, "name"), self)

    def get_album_by_mbid(self, mbid):
        """Looks up an album by its MusicBrainz ID"""

        params = {"mbid": _unicode(mbid)}

        doc = _Request(self, "album.getInfo", params).execute(True)

        return Album(_extract_data(doc, "artist"), _extract_data(doc, "name"), self)

def get_lastfm_network(api_key="", api_secret="", session_key="", username="", password_hash=""):
    """
    Returns a preconfigured Network object for Last.fm

    api_key: a provided API_KEY
    api_secret: a provided API_SECRET
    session_key: a generated session_key or None
    username: a username of a valid user
    password_hash: the output of pylast.md5(password) where password is the user's password

    if username and password_hash were provided and not session_key, session_key will be
    generated automatically when needed.

    Either a valid session_key or a combination of username and password_hash must be present for scrobbling.

    Most read-only webservices only require an api_key and an api_secret, see about obtaining them from:
    http://www.last.fm/api/account
    """

    return Network (
                    name="Last.fm",
                    homepage="http://last.fm",
                    ws_server=("ws.audioscrobbler.com", "/2.0/"),
                    api_key=api_key,
                    api_secret=api_secret,
                    session_key=session_key,
                    submission_server="http://post.audioscrobbler.com:80/",
                    username=username,
                    password_hash=password_hash,
                    domain_names={
                        DOMAIN_ENGLISH: 'www.last.fm',
                        DOMAIN_GERMAN: 'www.lastfm.de',
                        DOMAIN_SPANISH: 'www.lastfm.es',
                        DOMAIN_FRENCH: 'www.lastfm.fr',
                        DOMAIN_ITALIAN: 'www.lastfm.it',
                        DOMAIN_POLISH: 'www.lastfm.pl',
                        DOMAIN_PORTUGUESE: 'www.lastfm.com.br',
                        DOMAIN_SWEDISH: 'www.lastfm.se',
                        DOMAIN_TURKISH: 'www.lastfm.com.tr',
                        DOMAIN_RUSSIAN: 'www.lastfm.ru',
                        DOMAIN_JAPANESE: 'www.lastfm.jp',
                        DOMAIN_CHINESE: 'cn.last.fm',
                        },
                    urls={
                        "album": "music/%(artist)s/%(album)s",
                        "artist": "music/%(artist)s",
                        "event": "event/%(id)s",
                        "country": "place/%(country_name)s",
                        "playlist": "user/%(user)s/library/playlists/%(appendix)s",
                        "tag": "tag/%(name)s",
                        "track": "music/%(artist)s/_/%(title)s",
                        "group": "group/%(name)s",
                        "user": "user/%(name)s",
                        }
                    )

def get_librefm_network(api_key="", api_secret="", session_key="", username="", password_hash=""):
    """
    Returns a preconfigured Network object for Libre.fm

    api_key: a provided API_KEY
    api_secret: a provided API_SECRET
    session_key: a generated session_key or None
    username: a username of a valid user
    password_hash: the output of pylast.md5(password) where password is the user's password

    if username and password_hash were provided and not session_key, session_key will be
    generated automatically when needed.
    """

    return Network (
                    name="Libre.fm",
                    homepage="http://alpha.dev.libre.fm",
                    ws_server=("alpha.dev.libre.fm", "/2.0/"),
                    api_key=api_key,
                    api_secret=api_secret,
                    session_key=session_key,
                    submission_server="http://turtle.libre.fm:80/",
                    username=username,
                    password_hash=password_hash,
                    domain_names={
                        DOMAIN_ENGLISH: "alpha.dev.libre.fm",
                        DOMAIN_GERMAN: "alpha.dev.libre.fm",
                        DOMAIN_SPANISH: "alpha.dev.libre.fm",
                        DOMAIN_FRENCH: "alpha.dev.libre.fm",
                        DOMAIN_ITALIAN: "alpha.dev.libre.fm",
                        DOMAIN_POLISH: "alpha.dev.libre.fm",
                        DOMAIN_PORTUGUESE: "alpha.dev.libre.fm",
                        DOMAIN_SWEDISH: "alpha.dev.libre.fm",
                        DOMAIN_TURKISH: "alpha.dev.libre.fm",
                        DOMAIN_RUSSIAN: "alpha.dev.libre.fm",
                        DOMAIN_JAPANESE: "alpha.dev.libre.fm",
                        DOMAIN_CHINESE: "alpha.dev.libre.fm",
                        },
                    urls={
                        "album": "artist/%(artist)s/album/%(album)s",
                        "artist": "artist/%(artist)s",
                        "event": "event/%(id)s",
                        "country": "place/%(country_name)s",
                        "playlist": "user/%(user)s/library/playlists/%(appendix)s",
                        "tag": "tag/%(name)s",
                        "track": "music/%(artist)s/_/%(title)s",
                        "group": "group/%(name)s",
                        "user": "user/%(name)s",
                        }
                    )

class _ShelfCacheBackend(object):
    """Used as a backend for caching cacheable requests."""
    def __init__(self, file_path=None):
        self.shelf = shelve.open(file_path)

    def get_xml(self, key):
        return self.shelf[key]

    def set_xml(self, key, xml_string):
        self.shelf[key] = xml_string

    def has_key(self, key):
        return key in self.shelf.keys()

class _ThreadedCall(threading.Thread):
    """Facilitates calling a function on another thread."""

    def __init__(self, sender, funct, funct_args, callback, callback_args):

        threading.Thread.__init__(self)

        self.funct = funct
        self.funct_args = funct_args
        self.callback = callback
        self.callback_args = callback_args

        self.sender = sender

    def run(self):

        output = []

        if self.funct:
            if self.funct_args:
                output = self.funct(*self.funct_args)
            else:
                output = self.funct()

        if self.callback:
            if self.callback_args:
                self.callback(self.sender, output, *self.callback_args)
            else:
                self.callback(self.sender, output)

class _Request(object):
    """Representing an abstract web service operation."""

    def __init__(self, network, method_name, params={}):
        self.params = params
        self.network = network

        (self.api_key, self.api_secret, self.session_key) = network._get_ws_auth()

        self.params["api_key"] = self.api_key
        self.params["method"] = method_name

        if network.is_caching_enabled():
            self.cache = network._get_cache_backend()

        if self.session_key:
            self.params["sk"] = self.session_key
            self.sign_it()

    def sign_it(self):
        """Sign this request."""

        if not "api_sig" in self.params.keys():
            self.params['api_sig'] = self._get_signature()

    def _get_signature(self):
        """Returns a 32-character hexadecimal md5 hash of the signature string."""

        keys = self.params.keys()[:]

        keys.sort()

        string = ""

        for name in keys:
            string += name
            string += self.params[name]

        string += self.api_secret

        return md5(string)

    def _get_cache_key(self):
        """The cache key is a string of concatenated sorted names and values."""

        keys = self.params.keys()
        keys.sort()

        cache_key = str()

        for key in keys:
            if key != "api_sig" and key != "api_key" and key != "sk":
                cache_key += key + _string(self.params[key])

        return hashlib.sha1(cache_key).hexdigest()

    def _get_cached_response(self):
        """Returns a file object of the cached response."""

        if not self._is_cached():
            response = self._download_response()
            self.cache.set_xml(self._get_cache_key(), response)

        return self.cache.get_xml(self._get_cache_key())

    def _is_cached(self):
        """Returns True if the request is already in cache."""

        return self.cache.has_key(self._get_cache_key())

    def _download_response(self):
        """Returns a response body string from the server."""

        # Delay the call if necessary
        #self.network._delay_call()    # enable it if you want.

        data = []
        for name in self.params.keys():
            data.append('='.join((name, urllib.quote_plus(_string(self.params[name])))))

        data = '&'.join(data)

        headers = {
            "Content-type": "application/x-www-form-urlencoded",
            'Accept-Charset': 'utf-8',
            'User-Agent': "pylast" + '/' + __version__
            }

        (HOST_NAME, HOST_SUBDIR) = self.network.ws_server

        if self.network.is_proxy_enabled():
            proxy_rul = FC().proxy_url
            index = proxy_rul.find(":")
            proxy = proxy_rul[:index]
            port = proxy_rul[index + 1:]
            """Changed by zavlab1"""
            if FC().proxy_user and FC().proxy_password:
                user = urllib2.unquote(FC().proxy_user)
                password = urllib2.unquote(FC().proxy_password)
                auth = base64.b64encode(user + ":" + password).strip()
                headers['Proxy-Authorization'] =  '''Basic %s''' % auth

            conn = httplib.HTTPConnection(host=proxy, port=port)
            conn.request(method='POST', url="http://" + HOST_NAME + HOST_SUBDIR,
                body=data, headers=headers)
        else:
            conn = httplib.HTTPConnection(host=HOST_NAME)
            conn.request(method='POST', url=HOST_SUBDIR, body=data, headers=headers)

        response = conn.getresponse()

        response_text = _unicode(response.read())
        self._check_response_for_errors(response_text)
        return response_text

    def execute(self, cacheable=False):
        """Returns the XML DOM response of the POST Request from the server"""

        if self.network.is_caching_enabled() and cacheable:
            response = self._get_cached_response()
        else:
            response = self._download_response()
        return minidom.parseString(_string(response))

    def _check_response_for_errors(self, response):
        """Checks the response for errors and raises one if any exists."""

        doc = minidom.parseString(_string(response))
        e = doc.getElementsByTagName('lfm')[0]

        if e.getAttribute('status') != "ok":
            e = doc.getElementsByTagName('error')[0]
            status = e.getAttribute('code')
            details = e.firstChild.data.strip()
            raise WSError(self.network, status, details)

class SessionKeyGenerator(object):
    """Methods of generating a session key:
    1) Web Authentication:
        a. network = get_*_network(API_KEY, API_SECRET)
        b. sg = SessionKeyGenerator(network)
        c. url = sg.get_web_auth_url()
        d. Ask the user to open the url and authorize you, and wait for it.
        e. session_key = sg.get_web_auth_session_key(url)
    2) Username and Password Authentication:
        a. network = get_*_network(API_KEY, API_SECRET)
        b. username = raw_input("Please enter your username: ")
        c. password_hash = pylast.md5(raw_input("Please enter your password: ")
        d. session_key = SessionKeyGenerator(network).get_session_key(username, password_hash)

    A session key's lifetime is infinie, unless the user provokes the rights of the given API Key.

    If you create a Network object with just a API_KEY and API_SECRET and a username and a password_hash, a
    SESSION_KEY will be automatically generated for that network and stored in it so you don't have to do this
    manually, unless you want to.
    """

    def __init__(self, network):
        self.network = network
        self.web_auth_tokens = {}

    def _get_web_auth_token(self):
        """Retrieves a token from the network for web authentication.
        The token then has to be authorized from getAuthURL before creating session.
        """

        request = _Request(self.network, 'auth.getToken')

        # default action is that a request is signed only when
        # a session key is provided.
        request.sign_it()

        doc = request.execute()

        e = doc.getElementsByTagName('token')[0]
        return e.firstChild.data

    def get_web_auth_url(self):
        """The user must open this page, and you first, then call get_web_auth_session_key(url) after that."""

        token = self._get_web_auth_token()

        url = '%(homepage)s/api/auth/?api_key=%(api)s&token=%(token)s' % \
            {"homepage": self.network.homepage, "api": self.network.api_key, "token": token}

        self.web_auth_tokens[url] = token

        return url

    def get_web_auth_session_key(self, url):
        """Retrieves the session key of a web authorization process by its url."""

        if url in self.web_auth_tokens.keys():
            token = self.web_auth_tokens[url]
        else:
            token = ""    #that's gonna raise a WSError of an unauthorized token when the request is executed.

        request = _Request(self.network, 'auth.getSession', {'token': token})

        # default action is that a request is signed only when
        # a session key is provided.
        request.sign_it()

        doc = request.execute()

        return doc.getElementsByTagName('key')[0].firstChild.data

    def get_session_key(self, username, password_hash):
        """Retrieve a session key with a username and a md5 hash of the user's password."""

        params = {"username": username, "authToken": md5(username + password_hash)}
        request = _Request(self.network, "auth.getMobileSession", params)

        # default action is that a request is signed only when
        # a session key is provided.
        request.sign_it()

        doc = request.execute()

        return _extract_data(doc, "key")

def _namedtuple(name, children):
    """
        collections.namedtuple is available in (python >= 2.6)
    """

    v = sys.version_info
    if v[1] >= 6 and v[0] < 3:
        return collections.namedtuple(name, children)
    else:
        def fancydict(*args):
            d = {}
            i = 0
            for child in children:
                d[child.strip()] = args[i]
                i += 1
            return d

        return fancydict

TopItem = _namedtuple("TopItem", ["item", "weight"])
SimilarItem = _namedtuple("SimilarItem", ["item", "match"])
LibraryItem = _namedtuple("LibraryItem", ["item", "playcount", "tagcount"])
PlayedTrack = _namedtuple("PlayedTrack", ["track", "playback_date", "timestamp"])
LovedTrack = _namedtuple("LovedTrack", ["track", "date", "timestamp"])
ImageSizes = _namedtuple("ImageSizes", ["original", "large", "largesquare", "medium", "small", "extralarge"])
Image = _namedtuple("Image", ["title", "url", "dateadded", "format", "owner", "sizes", "votes"])
Shout = _namedtuple("Shout", ["body", "author", "date"])

def _string_output(funct):
    def r(*args):
        return _string(funct(*args))

    return r

class _BaseObject(object):
    """An abstract webservices object."""

    network = None

    def __init__(self, network):
        self.network = network

        """Added by zavlab1"""
        self.limit = FC().search_limit

    def _request(self, method_name, cacheable=False, params=None):
        if not params:
            params = self._get_params()

        """Added by zavlab1"""
        if self.limit:
            params["limit"] = str(self.limit)

        return _Request(self.network, method_name, params).execute(cacheable)

    def _get_params(self):
        """Returns the most common set of parameters between all objects."""

        return {}

    def __hash__(self):
        return hash(self.network) + \
            hash(str(type(self)) + "".join(self._get_params().keys() + self._get_params().values()).lower())

class _Taggable(object):
    """Common functions for classes with tags."""

    def __init__(self, ws_prefix):
        self.ws_prefix = ws_prefix

    def add_tags(self, *tags):
        """Adds one or several tags.
        * *tags: Any number of tag names or Tag objects.
        """

        for tag in tags:
            self._add_tag(tag)

    def _add_tag(self, tag):
        """Adds one or several tags.
        * tag: one tag name or a Tag object.
        """

        if isinstance(tag, Tag):
            tag = tag.get_name()

        params = self._get_params()
        params['tags'] = _unicode(tag)

        self._request(self.ws_prefix + '.addTags', False, params)

    def _remove_tag(self, single_tag):
        """Remove a user's tag from this object."""

        if isinstance(single_tag, Tag):
            single_tag = single_tag.get_name()

        params = self._get_params()
        params['tag'] = _unicode(single_tag)

        self._request(self.ws_prefix + '.removeTag', False, params)

    def get_tags(self):
        """Returns a list of the tags set by the user to this object."""

        # Uncacheable because it can be dynamically changed by the user.
        params = self._get_params()

        doc = self._request(self.ws_prefix + '.getTags', False, params)
        tag_names = _extract_all(doc, 'name')
        tags = []
        for tag in tag_names:
            tags.append(Tag(tag, self.network))

        return tags

    def remove_tags(self, *tags):
        """Removes one or several tags from this object.
        * *tags: Any number of tag names or Tag objects.
        """

        for tag in tags:
            self._remove_tag(tag)

    def clear_tags(self):
        """Clears all the user-set tags. """

        self.remove_tags(*(self.get_tags()))

    def set_tags(self, *tags):
        """Sets this object's tags to only those tags.
        * *tags: any number of tag names.
        """

        c_old_tags = []
        old_tags = []
        c_new_tags = []
        new_tags = []

        to_remove = []
        to_add = []

        tags_on_server = self.get_tags()

        for tag in tags_on_server:
            c_old_tags.append(tag.get_name().lower())
            old_tags.append(tag.get_name())

        for tag in tags:
            c_new_tags.append(tag.lower())
            new_tags.append(tag)

        for i in range(0, len(old_tags)):
            if not c_old_tags[i] in c_new_tags:
                to_remove.append(old_tags[i])

        for i in range(0, len(new_tags)):
            if not c_new_tags[i] in c_old_tags:
                to_add.append(new_tags[i])

        self.remove_tags(*to_remove)
        self.add_tags(*to_add)

    def get_top_tags(self, limit=None):
        """Returns a list of the most frequently used Tags on this object."""

        doc = self._request(self.ws_prefix + '.getTopTags', True)

        elements = doc.getElementsByTagName('tag')
        seq = []

        for element in elements:
            if limit and len(seq) >= limit:
                break
            tag_name = _extract_data(element, 'name')
            tagcount = _extract_data(element, 'count')

            seq.append(TopItem(Tag(tag_name, self.network), tagcount))

        return seq

class WSError(Exception):
    """Exception related to the Network web service"""

    def __init__(self, network, status, details):
        self.status = status
        self.details = details
        self.network = network

    @_string_output
    def __str__(self):
        return self.details

    def get_id(self):
        """Returns the exception ID, from one of the following:
            STATUS_INVALID_SERVICE = 2
            STATUS_INVALID_METHOD = 3
            STATUS_AUTH_FAILED = 4
            STATUS_INVALID_FORMAT = 5
            STATUS_INVALID_PARAMS = 6
            STATUS_INVALID_RESOURCE = 7
            STATUS_TOKEN_ERROR = 8
            STATUS_INVALID_SK = 9
            STATUS_INVALID_API_KEY = 10
            STATUS_OFFLINE = 11
            STATUS_SUBSCRIBERS_ONLY = 12
            STATUS_TOKEN_UNAUTHORIZED = 14
            STATUS_TOKEN_EXPIRED = 15
        """

        return self.status

class Album(_BaseObject, _Taggable):
    """An album."""

    title = None
    artist = None

    def __init__(self, artist, title, network):
        """
        Create an album instance.
        # Parameters:
            * artist: An artist name or an Artist object.
            * title: The album title.
        """

        _BaseObject.__init__(self, network)
        _Taggable.__init__(self, 'album')

        if isinstance(artist, Artist):
            self.artist = artist
        else:
            self.artist = Artist(artist, self.network)

        self.title = title

    @_string_output
    def __repr__(self):
        return u"%s - %s" % (self.get_artist().get_name(), self.get_title())

    def __eq__(self, other):
        return (self.get_title().lower() == other.get_title().lower()) and (self.get_artist().get_name().lower() == other.get_artist().get_name().lower())

    def __ne__(self, other):
        return (self.get_title().lower() != other.get_title().lower()) or (self.get_artist().get_name().lower() != other.get_artist().get_name().lower())

    def _get_params(self):
        return {'artist': self.get_artist().get_name(), 'album': self.get_title(), }

    def get_artist(self):
        """Returns the associated Artist object."""

        return self.artist

    def get_title(self):
        """Returns the album title."""

        return self.title

    def get_name(self):
        """Returns the album title (alias to Album.get_title)."""

        return self.get_title()

    def get_release_date(self):
        """Retruns the release date of the album."""

        return _extract_data(self._request("album.getInfo", cacheable=True), "releasedate")

    def get_release_year(self):
        st_date = str(self.get_release_date())
        try:
            dt = datetime.datetime.strptime(st_date, "%d %b %Y, %H:%M")
        except:
            if st_date:
                i = st_date.find(",")
                return st_date[i - 4:i]
            else:
                return st_date
        return str(dt.year)

    def get_cover_image(self, size=COVER_EXTRA_LARGE):
        """
        Returns a uri to the cover image
        size can be one of:
            COVER_MEGA
            COVER_EXTRA_LARGE
            COVER_LARGE
            COVER_MEDIUM
            COVER_SMALL
        """

        return _extract_all(self._request("album.getInfo", cacheable=True), 'image')[size]

    def get_id(self):
        """Returns the ID"""

        return _extract_data(self._request("album.getInfo", cacheable=True), "id")

    def get_playcount(self):
        """Returns the number of plays on the network"""

        return _number(_extract_data(self._request("album.getInfo", cacheable=True), "playcount"))

    def get_listener_count(self):
        """Returns the number of liteners on the network"""

        return _number(_extract_data(self._request("album.getInfo", cacheable=True), "listeners"))

    def get_top_tags(self, limit=None):
        """Returns a list of the most-applied tags to this album."""

        doc = self._request("album.getInfo", True)
        e = doc.getElementsByTagName("toptags")[0]

        seq = []
        for name in _extract_all(e, "name"):
            if len(seq) < limit:
                seq.append(Tag(name, self.network))

        return seq

    def get_tracks(self):
        """Returns the list of Tracks on this album."""

        uri = 'lastfm://playlist/album/%s' % self.get_id()

        return XSPF(uri, self.network).get_tracks()

    def get_mbid(self):
        """Returns the MusicBrainz id of the album."""

        return _extract_data(self._request("album.getInfo", cacheable=True), "mbid")

    def get_url(self, domain_name=DOMAIN_ENGLISH):
        """Returns the url of the album page on the network.
        # Parameters:
        * domain_name str: The network's language domain. Possible values:
            o DOMAIN_ENGLISH
            o DOMAIN_GERMAN
            o DOMAIN_SPANISH
            o DOMAIN_FRENCH
            o DOMAIN_ITALIAN
            o DOMAIN_POLISH
            o DOMAIN_PORTUGUESE
            o DOMAIN_SWEDISH
            o DOMAIN_TURKISH
            o DOMAIN_RUSSIAN
            o DOMAIN_JAPANESE
            o DOMAIN_CHINESE
        """

        artist = _url_safe(self.get_artist().get_name())
        album = _url_safe(self.get_title())

        return self.network._get_url(domain_name, "album") % {'artist': artist, 'album': album}

    def get_wiki_published_date(self):
        """Returns the date of publishing this version of the wiki."""

        doc = self._request("album.getInfo", True)

        if len(doc.getElementsByTagName("wiki")) == 0:
            return

        node = doc.getElementsByTagName("wiki")[0]

        return _extract_data(node, "published")

    def get_wiki_summary(self):
        """Returns the summary of the wiki."""

        doc = self._request("album.getInfo", True)

        if len(doc.getElementsByTagName("wiki")) == 0:
            return

        node = doc.getElementsByTagName("wiki")[0]

        return _extract_data(node, "summary")

    def get_wiki_content(self):
        """Returns the content of the wiki."""

        doc = self._request("album.getInfo", True)

        if len(doc.getElementsByTagName("wiki")) == 0:
            return

        node = doc.getElementsByTagName("wiki")[0]

        return _extract_data(node, "content")

class Artist(_BaseObject, _Taggable):
    """An artist."""

    name = None

    def __init__(self, name, network):
        """Create an artist object.
        # Parameters:
            * name str: The artist's name.
        """

        _BaseObject.__init__(self, network)
        _Taggable.__init__(self, 'artist')

        self.name = name

    @_string_output
    def __repr__(self):
        return self.get_name()

    def __eq__(self, other):
        return self.get_name().lower() == other.get_name().lower()

    def __ne__(self, other):
        return self.get_name().lower() != other.get_name().lower()

    def _get_params(self):
        return {'artist': self.get_name()}

    def get_name(self):
        """Returns the name of the artist."""

        return self.name

    def get_cover_image(self, size=COVER_LARGE):
        """
        Returns a uri to the cover image
        size can be one of:
            COVER_MEGA
            COVER_EXTRA_LARGE
            COVER_LARGE
            COVER_MEDIUM
            COVER_SMALL
        """

        return _extract_all(self._request("artist.getInfo", True), "image")[size]

    def get_playcount(self):
        """Returns the number of plays on the network."""

        return _number(_extract_data(self._request("artist.getInfo", True), "playcount"))

    def get_mbid(self):
        """Returns the MusicBrainz ID of this artist."""

        doc = self._request("artist.getInfo", True)

        return _extract_data(doc, "mbid")

    def get_listener_count(self):
        """Returns the number of liteners on the network."""

        return _number(_extract_data(self._request("artist.getInfo", True), "listeners"))

    def is_streamable(self):
        """Returns True if the artist is streamable."""

        return bool(_number(_extract_data(self._request("artist.getInfo", True), "streamable")))

    def get_bio_published_date(self):
        """Returns the date on which the artist's biography was published."""

        return _extract_data(self._request("artist.getInfo", True), "published")

    def get_bio_summary(self):
        """Returns the summary of the artist's biography."""

        return _extract_whole_text(self._request("artist.getInfo", True), "summary")

    def get_bio_content(self):
        """Returns the content of the artist's biography."""

        return _extract_data(self._request("artist.getInfo", True), "content")

    def get_upcoming_events(self):
        """Returns a list of the upcoming Events for this artist."""

        doc = self._request('artist.getEvents', True)

        ids = _extract_all(doc, 'id')

        events = []
        for e_id in ids:
            events.append(Event(e_id, self.network))

        return events

    def get_similar(self, limit=None):
        """Returns the similar artists on the network."""

        params = self._get_params()
        if limit:
            params['limit'] = _unicode(limit)

        doc = self._request('artist.getSimilar', True, params)

        names = _extract_all(doc, "name")
        matches = _extract_all(doc, "match")

        artists = []
        for i in range(0, len(names)):
            artists.append(SimilarItem(Artist(names[i], self.network), _number(matches[i])))

        return artists

    def get_top_albums(self):
        """Retuns a list of the top albums."""

        doc = self._request('artist.getTopAlbums', True)

        seq = []

        for node in doc.getElementsByTagName("album"):
            name = _extract_data(node, "name")
            artist = _extract_data(node, "name", 1)
            playcount = _extract_data(node, "playcount")

            seq.append(TopItem(Album(artist, name, self.network), playcount))

        return seq

    def get_top_tracks(self):
        """Returns a list of the most played Tracks by this artist."""

        doc = self._request("artist.getTopTracks", True)

        seq = []
        for track in doc.getElementsByTagName('track'):

            title = _extract_data(track, "name")
            artist = _extract_data(track, "name", 1)
            playcount = _number(_extract_data(track, "playcount"))

            seq.append(TopItem(Track(artist, title, self.network), playcount))

        return seq

    def get_top_fans(self, limit=None):
        """Returns a list of the Users who played this artist the most.
        # Parameters:
            * limit int: Max elements.
        """

        doc = self._request('artist.getTopFans', True)

        seq = []

        elements = doc.getElementsByTagName('user')

        for element in elements:
            if limit and len(seq) >= limit:
                break

            name = _extract_data(element, 'name')
            weight = _number(_extract_data(element, 'weight'))

            seq.append(TopItem(User(name, self.network), weight))

        return seq

    def share(self, users, message=None):
        """Shares this artist (sends out recommendations).
        # Parameters:
            * users [User|str,]: A list that can contain usernames, emails, User objects, or all of them.
            * message str: A message to include in the recommendation message.
        """

        #last.fm currently accepts a max of 10 recipient at a time
        while(len(users) > 10):
            section = users[0:9]
            users = users[9:]
            self.share(section, message)

        nusers = []
        for user in users:
            if isinstance(user, User):
                nusers.append(user.get_name())
            else:
                nusers.append(user)

        params = self._get_params()
        recipients = ','.join(nusers)
        params['recipient'] = recipients
        if message: params['message'] = _unicode(message)

        self._request('artist.share', False, params)

    def get_url(self, domain_name=DOMAIN_ENGLISH):
        """Returns the url of the artist page on the network.
        # Parameters:
        * domain_name: The network's language domain. Possible values:
          o DOMAIN_ENGLISH
          o DOMAIN_GERMAN
          o DOMAIN_SPANISH
          o DOMAIN_FRENCH
          o DOMAIN_ITALIAN
          o DOMAIN_POLISH
          o DOMAIN_PORTUGUESE
          o DOMAIN_SWEDISH
          o DOMAIN_TURKISH
          o DOMAIN_RUSSIAN
          o DOMAIN_JAPANESE
          o DOMAIN_CHINESE
        """

        artist = _url_safe(self.get_name())

        return self.network._get_url(domain_name, "artist") % {'artist': artist}

    """Deprecated by Last.FM"""
    def get_images(self, order=IMAGES_ORDER_POPULARITY, limit=None):
        """
            Returns a sequence of Image objects
            if limit is None it will return all
            order can be IMAGES_ORDER_POPULARITY or IMAGES_ORDER_DATE
        """

        images = []

        params = self._get_params()
        params["order"] = order
        nodes = _collect_nodes(limit, self, "artist.getImages", True, params)
        for e in nodes:
            if _extract_data(e, "name"):
                user = User(_extract_data(e, "name"), self.network)
            else:
                user = None

            images.append(Image(
                            _extract_data(e, "title"),
                            _extract_data(e, "url"),
                            _extract_data(e, "dateadded"),
                            _extract_data(e, "format"),
                            user,
                            ImageSizes(*_extract_all(e, "size")),
                            (_extract_data(e, "thumbsup"), _extract_data(e, "thumbsdown"))
                            )
                        )
        return images

    def get_shouts(self, limit=50):
        """
            Returns a sequqence of Shout objects
        """

        shouts = []
        for node in _collect_nodes(limit, self, "artist.getShouts", False):
            shouts.append(Shout(
                                _extract_data(node, "body"),
                                User(_extract_data(node, "author"), self.network),
                                _extract_data(node, "date")
                                )
                            )
        return shouts

    def shout(self, message):
        """
            Post a shout
        """

        params = self._get_params()
        params["message"] = message

        self._request("artist.Shout", False, params)


class Event(_BaseObject):
    """An event."""

    id = None

    def __init__(self, event_id, network):
        _BaseObject.__init__(self, network)

        self.id = _unicode(event_id)

    @_string_output
    def __repr__(self):
        return "Event #" + self.get_id()

    def __eq__(self, other):
        return self.get_id() == other.get_id()

    def __ne__(self, other):
        return self.get_id() != other.get_id()

    def _get_params(self):
        return {'event': self.get_id()}

    def attend(self, attending_status):
        """Sets the attending status.
        * attending_status: The attending status. Possible values:
          o EVENT_ATTENDING
          o EVENT_MAYBE_ATTENDING
          o EVENT_NOT_ATTENDING
        """

        params = self._get_params()
        params['status'] = _unicode(attending_status)

        self._request('event.attend', False, params)

    def get_attendees(self):
        """
            Get a list of attendees for an event
        """

        doc = self._request("event.getAttendees", False)

        users = []
        for name in _extract_all(doc, "name"):
            users.append(User(name, self.network))

        return users

    def get_id(self):
        """Returns the id of the event on the network. """

        return self.id

    def get_title(self):
        """Returns the title of the event. """

        doc = self._request("event.getInfo", True)

        return _extract_data(doc, "title")

    def get_headliner(self):
        """Returns the headliner of the event. """

        doc = self._request("event.getInfo", True)

        return Artist(_extract_data(doc, "headliner"), self.network)

    def get_artists(self):
        """Returns a list of the participating Artists. """

        doc = self._request("event.getInfo", True)
        names = _extract_all(doc, "artist")

        artists = []
        for name in names:
            artists.append(Artist(name, self.network))

        return artists

    def get_venue(self):
        """Returns the venue where the event is held."""

        doc = self._request("event.getInfo", True)

        v = doc.getElementsByTagName("venue")[0]
        venue_id = _number(_extract_data(v, "id"))

        return Venue(venue_id, self.network)

    def get_start_date(self):
        """Returns the date when the event starts."""

        doc = self._request("event.getInfo", True)

        return _extract_data(doc, "startDate")

    def get_description(self):
        """Returns the description of the event. """

        doc = self._request("event.getInfo", True)

        return _extract_data(doc, "description")

    def get_cover_image(self, size=COVER_LARGE):
        """
        Returns a uri to the cover image
        size can be one of:
            COVER_MEGA
            COVER_EXTRA_LARGE
            COVER_LARGE
            COVER_MEDIUM
            COVER_SMALL
        """

        doc = self._request("event.getInfo", True)

        return _extract_all(doc, "image")[size]

    def get_attendance_count(self):
        """Returns the number of attending people. """

        doc = self._request("event.getInfo", True)

        return _number(_extract_data(doc, "attendance"))

    def get_review_count(self):
        """Returns the number of available reviews for this event. """

        doc = self._request("event.getInfo", True)

        return _number(_extract_data(doc, "reviews"))

    def get_url(self, domain_name=DOMAIN_ENGLISH):
        """Returns the url of the event page on the network.
        * domain_name: The network's language domain. Possible values:
          o DOMAIN_ENGLISH
          o DOMAIN_GERMAN
          o DOMAIN_SPANISH
          o DOMAIN_FRENCH
          o DOMAIN_ITALIAN
          o DOMAIN_POLISH
          o DOMAIN_PORTUGUESE
          o DOMAIN_SWEDISH
          o DOMAIN_TURKISH
          o DOMAIN_RUSSIAN
          o DOMAIN_JAPANESE
          o DOMAIN_CHINESE
        """

        return self.network._get_url(domain_name, "event") % {'id': self.get_id()}

    def share(self, users, message=None):
        """Shares this event (sends out recommendations).
          * users: A list that can contain usernames, emails, User objects, or all of them.
          * message: A message to include in the recommendation message.
        """

        #last.fm currently accepts a max of 10 recipient at a time
        while(len(users) > 10):
            section = users[0:9]
            users = users[9:]
            self.share(section, message)

        nusers = []
        for user in users:
            if isinstance(user, User):
                nusers.append(user.get_name())
            else:
                nusers.append(user)

        params = self._get_params()
        recipients = ','.join(nusers)
        params['recipient'] = recipients
        if message: params['message'] = _unicode(message)

        self._request('event.share', False, params)

    def get_shouts(self, limit=50):
        """
            Returns a sequqence of Shout objects
        """

        shouts = []
        for node in _collect_nodes(limit, self, "event.getShouts", False):
            shouts.append(Shout(
                                _extract_data(node, "body"),
                                User(_extract_data(node, "author"), self.network),
                                _extract_data(node, "date")
                                )
                            )
        return shouts

    def shout(self, message):
        """
            Post a shout
        """

        params = self._get_params()
        params["message"] = message

        self._request("event.Shout", False, params)

class Country(_BaseObject):
    """A country at Last.fm."""

    name = None

    def __init__(self, name, network):
        _BaseObject.__init__(self, network)

        self.name = name

    @_string_output
    def __repr__(self):
        return self.get_name()

    def __eq__(self, other):
        return self.get_name().lower() == other.get_name().lower()

    def __ne__(self, other):
        return self.get_name() != other.get_name()

    def _get_params(self):
        return {'country': self.get_name()}

    def _get_name_from_code(self, alpha2code):
        # TODO: Have this function lookup the alpha-2 code and return the country name.

        return alpha2code

    def get_name(self):
        """Returns the country name. """

        return self.name

    def get_top_artists(self):
        """Returns a sequence of the most played artists."""

        doc = self._request('geo.getTopArtists', True)

        seq = []
        for node in doc.getElementsByTagName("artist"):
            name = _extract_data(node, 'name')
            playcount = _extract_data(node, "playcount")

            seq.append(TopItem(Artist(name, self.network), playcount))

        return seq

    def get_top_tracks(self):
        """Returns a sequence of the most played tracks"""

        doc = self._request("geo.getTopTracks", True)

        seq = []

        for n in doc.getElementsByTagName('track'):

            title = _extract_data(n, 'name')
            artist = _extract_data(n, 'name', 1)
            playcount = _number(_extract_data(n, "playcount"))

            seq.append(TopItem(Track(artist, title, self.network), playcount))

        return seq

    def get_url(self, domain_name=DOMAIN_ENGLISH):
        """Returns the url of the event page on the network.
        * domain_name: The network's language domain. Possible values:
          o DOMAIN_ENGLISH
          o DOMAIN_GERMAN
          o DOMAIN_SPANISH
          o DOMAIN_FRENCH
          o DOMAIN_ITALIAN
          o DOMAIN_POLISH
          o DOMAIN_PORTUGUESE
          o DOMAIN_SWEDISH
          o DOMAIN_TURKISH
          o DOMAIN_RUSSIAN
          o DOMAIN_JAPANESE
          o DOMAIN_CHINESE
        """

        country_name = _url_safe(self.get_name())

        return self.network._get_url(domain_name, "country") % {'country_name': country_name}


class Library(_BaseObject):
    """A user's Last.fm library."""

    user = None

    def __init__(self, user, network):
        _BaseObject.__init__(self, network)

        if isinstance(user, User):
            self.user = user
        else:
            self.user = User(user, self.network)

        self._albums_index = 0
        self._artists_index = 0
        self._tracks_index = 0

    @_string_output
    def __repr__(self):
        return repr(self.get_user()) + "'s Library"

    def _get_params(self):
        return {'user': self.user.get_name()}

    def get_user(self):
        """Returns the user who owns this library."""

        return self.user

    def add_album(self, album):
        """Add an album to this library."""

        params = self._get_params()
        params["artist"] = album.get_artist.get_name()
        params["album"] = album.get_name()

        self._request("library.addAlbum", False, params)

    def add_artist(self, artist):
        """Add an artist to this library."""

        params = self._get_params()
        params["artist"] = artist.get_name()

        self._request("library.addArtist", False, params)

    def add_track(self, track):
        """Add a track to this library."""

        params = self._get_params()
        params["track"] = track.get_title()

        self._request("library.addTrack", False, params)

    def get_albums(self, limit=50):
        """
        Returns a sequence of Album objects
        if limit==None it will return all (may take a while)
        """

        seq = []
        for node in _collect_nodes(limit, self, "library.getAlbums", True):
            name = _extract_data(node, "name")
            artist = _extract_data(node, "name", 1)
            playcount = _number(_extract_data(node, "playcount"))
            tagcount = _number(_extract_data(node, "tagcount"))

            seq.append(LibraryItem(Album(artist, name, self.network), playcount, tagcount))

        return seq

    def get_artists(self, limit=50):
        """
        Returns a sequence of Album objects
        if limit==None it will return all (may take a while)
        """

        seq = []
        for node in _collect_nodes(limit, self, "library.getArtists", True):
            name = _extract_data(node, "name")

            playcount = _number(_extract_data(node, "playcount"))
            tagcount = _number(_extract_data(node, "tagcount"))

            seq.append(LibraryItem(Artist(name, self.network), playcount, tagcount))

        return seq

    def get_tracks(self, limit=50):
        """
        Returns a sequence of Album objects
        if limit==None it will return all (may take a while)
        """

        seq = []
        for node in _collect_nodes(limit, self, "library.getTracks", True):
            name = _extract_data(node, "name")
            artist = _extract_data(node, "name", 1)
            playcount = _number(_extract_data(node, "playcount"))
            tagcount = _number(_extract_data(node, "tagcount"))

            seq.append(LibraryItem(Track(artist, name, self.network), playcount, tagcount))

        return seq


class Playlist(_BaseObject):
    """A Last.fm user playlist."""

    id = None
    user = None

    def __init__(self, user, id, network):
        _BaseObject.__init__(self, network)

        if isinstance(user, User):
            self.user = user
        else:
            self.user = User(user, self.network)

        self.id = _unicode(id)

    @_string_output
    def __repr__(self):
        return repr(self.user) + "'s playlist # " + repr(self.id)

    def _get_info_node(self):
        """Returns the node from user.getPlaylists where this playlist's info is."""

        doc = self._request("user.getPlaylists", True)

        for node in doc.getElementsByTagName("playlist"):
            if _extract_data(node, "id") == str(self.get_id()):
                return node

    def _get_params(self):
        return {'user': self.user.get_name(), 'playlistID': self.get_id()}

    def get_id(self):
        """Returns the playlist id."""

        return self.id

    def get_user(self):
        """Returns the owner user of this playlist."""

        return self.user

    def get_tracks(self):
        """Returns a list of the tracks on this user playlist."""

        uri = u'lastfm://playlist/%s' % self.get_id()

        return XSPF(uri, self.network).get_tracks()

    def add_track(self, track):
        """Adds a Track to this Playlist."""

        params = self._get_params()
        params['artist'] = track.get_artist().get_name()
        params['track'] = track.get_title()

        self._request('playlist.addTrack', False, params)

    def get_title(self):
        """Returns the title of this playlist."""

        return _extract_data(self._get_info_node(), "title")

    def get_creation_date(self):
        """Returns the creation date of this playlist."""

        return _extract_data(self._get_info_node(), "date")

    def get_size(self):
        """Returns the number of tracks in this playlist."""

        return _number(_extract_data(self._get_info_node(), "size"))

    def get_description(self):
        """Returns the description of this playlist."""

        return _extract_data(self._get_info_node(), "description")

    def get_duration(self):
        """Returns the duration of this playlist in milliseconds."""

        return _number(_extract_data(self._get_info_node(), "duration"))

    def is_streamable(self):
        """Returns True if the playlist is streamable.
        For a playlist to be streamable, it needs at least 45 tracks by 15 different artists."""

        if _extract_data(self._get_info_node(), "streamable") == '1':
            return True
        else:
            return False

    def has_track(self, track):
        """Checks to see if track is already in the playlist.
        * track: Any Track object.
        """

        return track in self.get_tracks()

    def get_cover_image(self, size=COVER_LARGE):
        """
        Returns a uri to the cover image
        size can be one of:
            COVER_MEGA
            COVER_EXTRA_LARGE
            COVER_LARGE
            COVER_MEDIUM
            COVER_SMALL
        """

        return _extract_data(self._get_info_node(), "image")[size]

    def get_url(self, domain_name=DOMAIN_ENGLISH):
        """Returns the url of the playlist on the network.
        * domain_name: The network's language domain. Possible values:
          o DOMAIN_ENGLISH
          o DOMAIN_GERMAN
          o DOMAIN_SPANISH
          o DOMAIN_FRENCH
          o DOMAIN_ITALIAN
          o DOMAIN_POLISH
          o DOMAIN_PORTUGUESE
          o DOMAIN_SWEDISH
          o DOMAIN_TURKISH
          o DOMAIN_RUSSIAN
          o DOMAIN_JAPANESE
          o DOMAIN_CHINESE
        """

        english_url = _extract_data(self._get_info_node(), "url")
        appendix = english_url[english_url.rfind("/") + 1:]

        return self.network._get_url(domain_name, "playlist") % {'appendix': appendix, "user": self.get_user().get_name()}


class Tag(_BaseObject):
    """A Last.fm object tag."""

    # TODO: getWeeklyArtistChart (too lazy, i'll wait for when someone requests it)

    name = None

    def __init__(self, name, network):
        _BaseObject.__init__(self, network)

        self.name = name

    def _get_params(self):
        return {'tag': self.get_name()}

    @_string_output
    def __repr__(self):
        return self.get_name()

    def __eq__(self, other):
        return self.get_name().lower() == other.get_name().lower()

    def __ne__(self, other):
        return self.get_name().lower() != other.get_name().lower()

    def get_name(self):
        """Returns the name of the tag. """

        return self.name

    def get_similar(self):
        """Returns the tags similar to this one, ordered by similarity. """

        doc = self._request('tag.getSimilar', True)

        seq = []
        names = _extract_all(doc, 'name')
        for name in names:
            seq.append(Tag(name, self.network))

        return seq

    def get_top_albums(self):
        """Retuns a list of the top albums."""

        doc = self._request('tag.getTopAlbums', True)

        seq = []

        for node in doc.getElementsByTagName("album"):
            name = _extract_data(node, "name")
            artist = _extract_data(node, "name", 1)
            playcount = _extract_data(node, "playcount")

            seq.append(TopItem(Album(artist, name, self.network), playcount))

        return seq

    def get_top_tracks(self):
        """Returns a list of the most played Tracks by this artist."""

        doc = self._request("tag.getTopTracks", True)

        seq = []
        for track in doc.getElementsByTagName('track'):

            title = _extract_data(track, "name")
            artist = _extract_data(track, "name", 1)
            playcount = _number(_extract_data(track, "playcount"))

            seq.append(TopItem(Track(artist, title, self.network), playcount))

        return seq

    def get_top_artists(self):
        """Returns a sequence of the most played artists."""

        doc = self._request('tag.getTopArtists', True)

        seq = []
        for node in doc.getElementsByTagName("artist"):
            name = _extract_data(node, 'name')
            playcount = _extract_data(node, "playcount")

            seq.append(TopItem(Artist(name, self.network), playcount))

        return seq

    def get_weekly_chart_dates(self):
        """Returns a list of From and To tuples for the available charts."""

        doc = self._request("tag.getWeeklyChartList", True)

        seq = []
        for node in doc.getElementsByTagName("chart"):
            seq.append((node.getAttribute("from"), node.getAttribute("to")))

        return seq

    def get_weekly_artist_charts(self, from_date=None, to_date=None):
        """Returns the weekly artist charts for the week starting from the from_date value to the to_date value."""

        params = self._get_params()
        if from_date and to_date:
            params["from"] = from_date
            params["to"] = to_date

        doc = self._request("tag.getWeeklyArtistChart", True, params)

        seq = []
        for node in doc.getElementsByTagName("artist"):
            item = Artist(_extract_data(node, "name"), self.network)
            weight = _number(_extract_data(node, "weight"))
            seq.append(TopItem(item, weight))

        return seq

    def get_url(self, domain_name=DOMAIN_ENGLISH):
        """Returns the url of the tag page on the network.
        * domain_name: The network's language domain. Possible values:
          o DOMAIN_ENGLISH
          o DOMAIN_GERMAN
          o DOMAIN_SPANISH
          o DOMAIN_FRENCH
          o DOMAIN_ITALIAN
          o DOMAIN_POLISH
          o DOMAIN_PORTUGUESE
          o DOMAIN_SWEDISH
          o DOMAIN_TURKISH
          o DOMAIN_RUSSIAN
          o DOMAIN_JAPANESE
          o DOMAIN_CHINESE
        """

        name = _url_safe(self.get_name())

        return self.network._get_url(domain_name, "tag") % {'name': name}

class Track(_BaseObject, _Taggable):
    """A Last.fm track."""

    artist = None
    title = None

    def __init__(self, artist, title, network):
        _BaseObject.__init__(self, network)
        _Taggable.__init__(self, 'track')

        if isinstance(artist, Artist):
            self.artist = artist
        else:
            self.artist = Artist(artist, self.network)

        self.title = title

    @_string_output
    def __repr__(self):
        return self.get_artist().get_name() + ' - ' + self.get_title()

    def __eq__(self, other):
        return (self.get_title().lower() == other.get_title().lower()) and (self.get_artist().get_name().lower() == other.get_artist().get_name().lower())

    def __ne__(self, other):
        return (self.get_title().lower() != other.get_title().lower()) or (self.get_artist().get_name().lower() != other.get_artist().get_name().lower())

    def _get_params(self):
        return {'artist': self.get_artist().get_name(), 'track': self.get_title()}

    def get_artist(self):
        """Returns the associated Artist object."""

        return self.artist

    def get_title(self):
        """Returns the track title."""

        return self.title

    def get_name(self):
        """Returns the track title (alias to Track.get_title)."""

        return self.get_title()

    def get_id(self):
        """Returns the track id on the network."""

        doc = self._request("track.getInfo", True)

        return _extract_data(doc, "id")

    def get_duration(self):
        """Returns the track duration."""

        doc = self._request("track.getInfo", True)

        return _number(_extract_data(doc, "duration"))

    def get_mbid(self):
        """Returns the MusicBrainz ID of this track."""

        doc = self._request("track.getInfo", True)

        return _extract_data(doc, "mbid")

    def get_listener_count(self):
        """Returns the listener count."""

        doc = self._request("track.getInfo", True)

        return _number(_extract_data(doc, "listeners"))

    def get_playcount(self):
        """Returns the play count."""

        doc = self._request("track.getInfo", True)
        return _number(_extract_data(doc, "playcount"))

    def is_streamable(self):
        """Returns True if the track is available at Last.fm."""

        doc = self._request("track.getInfo", True)
        return _extract_data(doc, "streamable") == "1"

    def is_fulltrack_available(self):
        """Returns True if the fulltrack is available for streaming."""

        doc = self._request("track.getInfo", True)
        return doc.getElementsByTagName("streamable")[0].getAttribute("fulltrack") == "1"

    def get_album(self):
        """Returns the album object of this track."""

        doc = self._request("track.getInfo", True)

        albums = doc.getElementsByTagName("album")

        if len(albums) == 0:
            return

        node = doc.getElementsByTagName("album")[0]
        return Album(_extract_data(node, "artist"), _extract_data(node, "title"), self.network)

    def get_wiki_published_date(self):
        """Returns the date of publishing this version of the wiki."""

        doc = self._request("track.getInfo", True)

        if len(doc.getElementsByTagName("wiki")) == 0:
            return

        node = doc.getElementsByTagName("wiki")[0]

        return _extract_data(node, "published")

    def get_wiki_summary(self):
        """Returns the summary of the wiki."""

        doc = self._request("track.getInfo", True)

        if len(doc.getElementsByTagName("wiki")) == 0:
            return

        node = doc.getElementsByTagName("wiki")[0]

        return _extract_data(node, "summary")

    def get_wiki_content(self):
        """Returns the content of the wiki."""

        doc = self._request("track.getInfo", True)

        if len(doc.getElementsByTagName("wiki")) == 0:
            return

        node = doc.getElementsByTagName("wiki")[0]

        return _extract_data(node, "content")

    def love(self):
        """Adds the track to the user's loved tracks. """

        self._request('track.love')

    def ban(self):
        """Ban this track from ever playing on the radio. """

        self._request('track.ban')

    def get_similar(self):
        """Returns similar tracks for this track on the network, based on listening data. """

        doc = self._request('track.getSimilar', True)

        seq = []
        for node in doc.getElementsByTagName("track"):
            title = _extract_data(node, 'name')
            artist = _extract_data(node, 'name', 1)
            match = _number(_extract_data(node, "match"))

            seq.append(SimilarItem(Track(artist, title, self.network), match))

        return seq

    def get_top_fans(self, limit=None):
        """Returns a list of the Users who played this track."""

        doc = self._request('track.getTopFans', True)

        seq = []

        elements = doc.getElementsByTagName('user')

        for element in elements:
            if limit and len(seq) >= limit:
                break

            name = _extract_data(element, 'name')
            weight = _number(_extract_data(element, 'weight'))

            seq.append(TopItem(User(name, self.network), weight))

        return seq

    def share(self, users, message=None):
        """Shares this track (sends out recommendations).
          * users: A list that can contain usernames, emails, User objects, or all of them.
          * message: A message to include in the recommendation message.
        """

        #last.fm currently accepts a max of 10 recipient at a time
        while(len(users) > 10):
            section = users[0:9]
            users = users[9:]
            self.share(section, message)

        nusers = []
        for user in users:
            if isinstance(user, User):
                nusers.append(user.get_name())
            else:
                nusers.append(user)

        params = self._get_params()
        recipients = ','.join(nusers)
        params['recipient'] = recipients
        if message: params['message'] = _unicode(message)

        self._request('track.share', False, params)

    def get_url(self, domain_name=DOMAIN_ENGLISH):
        """Returns the url of the track page on the network.
        * domain_name: The network's language domain. Possible values:
          o DOMAIN_ENGLISH
          o DOMAIN_GERMAN
          o DOMAIN_SPANISH
          o DOMAIN_FRENCH
          o DOMAIN_ITALIAN
          o DOMAIN_POLISH
          o DOMAIN_PORTUGUESE
          o DOMAIN_SWEDISH
          o DOMAIN_TURKISH
          o DOMAIN_RUSSIAN
          o DOMAIN_JAPANESE
          o DOMAIN_CHINESE
        """

        artist = _url_safe(self.get_artist().get_name())
        title = _url_safe(self.get_title())

        return self.network._get_url(domain_name, "track") % {'domain': self.network._get_language_domain(domain_name), 'artist': artist, 'title': title}

    def get_shouts(self, limit=50):
        """
            Returns a sequqence of Shout objects
        """

        shouts = []
        for node in _collect_nodes(limit, self, "track.getShouts", False):
            shouts.append(Shout(
                                _extract_data(node, "body"),
                                User(_extract_data(node, "author"), self.network),
                                _extract_data(node, "date")
                                )
                            )
        return shouts

    def shout(self, message):
        """
            Post a shout
        """

        params = self._get_params()
        params["message"] = message

        self._request("track.Shout", False, params)

class Group(_BaseObject):
    """A Last.fm group."""

    name = None

    def __init__(self, group_name, network):
        _BaseObject.__init__(self, network)

        self.name = group_name

    @_string_output
    def __repr__(self):
        return self.get_name()

    def __eq__(self, other):
        return self.get_name().lower() == other.get_name().lower()

    def __ne__(self, other):
        return self.get_name() != other.get_name()

    def _get_params(self):
        return {'group': self.get_name()}

    def get_name(self):
        """Returns the group name. """
        return self.name

    def get_weekly_chart_dates(self):
        """Returns a list of From and To tuples for the available charts."""

        doc = self._request("group.getWeeklyChartList", True)

        seq = []
        for node in doc.getElementsByTagName("chart"):
            seq.append((node.getAttribute("from"), node.getAttribute("to")))

        return seq

    def get_weekly_artist_charts(self, from_date=None, to_date=None):
        """Returns the weekly artist charts for the week starting from the from_date value to the to_date value."""

        params = self._get_params()
        if from_date and to_date:
            params["from"] = from_date
            params["to"] = to_date

        doc = self._request("group.getWeeklyArtistChart", True, params)

        seq = []
        for node in doc.getElementsByTagName("artist"):
            item = Artist(_extract_data(node, "name"), self.network)
            weight = _number(_extract_data(node, "playcount"))
            seq.append(TopItem(item, weight))

        return seq

    def get_weekly_album_charts(self, from_date=None, to_date=None):
        """Returns the weekly album charts for the week starting from the from_date value to the to_date value."""

        params = self._get_params()
        if from_date and to_date:
            params["from"] = from_date
            params["to"] = to_date

        doc = self._request("group.getWeeklyAlbumChart", True, params)

        seq = []
        for node in doc.getElementsByTagName("album"):
            item = Album(_extract_data(node, "artist"), _extract_data(node, "name"), self.network)
            weight = _number(_extract_data(node, "playcount"))
            seq.append(TopItem(item, weight))

        return seq

    def get_weekly_track_charts(self, from_date=None, to_date=None):
        """Returns the weekly track charts for the week starting from the from_date value to the to_date value."""

        params = self._get_params()
        if from_date and to_date:
            params["from"] = from_date
            params["to"] = to_date

        doc = self._request("group.getWeeklyTrackChart", True, params)

        seq = []
        for node in doc.getElementsByTagName("track"):
            item = Track(_extract_data(node, "artist"), _extract_data(node, "name"), self.network)
            weight = _number(_extract_data(node, "playcount"))
            seq.append(TopItem(item, weight))

        return seq

    def get_url(self, domain_name=DOMAIN_ENGLISH):
        """Returns the url of the group page on the network.
        * domain_name: The network's language domain. Possible values:
          o DOMAIN_ENGLISH
          o DOMAIN_GERMAN
          o DOMAIN_SPANISH
          o DOMAIN_FRENCH
          o DOMAIN_ITALIAN
          o DOMAIN_POLISH
          o DOMAIN_PORTUGUESE
          o DOMAIN_SWEDISH
          o DOMAIN_TURKISH
          o DOMAIN_RUSSIAN
          o DOMAIN_JAPANESE
          o DOMAIN_CHINESE
        """

        name = _url_safe(self.get_name())

        return self.network._get_url(domain_name, "group") % {'name': name}

    def get_members(self, limit=50):
        """
            Returns a sequence of User objects
            if limit==None it will return all
        """

        nodes = _collect_nodes(limit, self, "group.getMembers", False)

        users = []

        for node in nodes:
            users.append(User(_extract_data(node, "name"), self.network))

        return users

class XSPF(_BaseObject):
    "A Last.fm XSPF playlist."""

    uri = None

    def __init__(self, uri, network):
        _BaseObject.__init__(self, network)

        self.uri = uri

    def _get_params(self):
        return {'playlistURL': self.get_uri()}

    @_string_output
    def __repr__(self):
        return self.get_uri()

    def __eq__(self, other):
        return self.get_uri() == other.get_uri()

    def __ne__(self, other):
        return self.get_uri() != other.get_uri()

    def get_uri(self):
        """Returns the Last.fm playlist URI. """

        return self.uri

    def get_tracks(self):
        """Returns the tracks on this playlist."""

        doc = self._request('playlist.fetch', True)

        seq = []
        for n in doc.getElementsByTagName('track'):
            title = _extract_data(n, 'title')
            artist = _extract_data(n, 'creator')

            seq.append(Track(artist, title, self.network))

        return seq

class User(_BaseObject):
    """A Last.fm user."""

    name = None

    def __init__(self, user_name, network):
        _BaseObject.__init__(self, network)

        self.name = user_name

        self._past_events_index = 0
        self._recommended_events_index = 0
        self._recommended_artists_index = 0

    @_string_output
    def __repr__(self):
        return self.get_name()

    def __eq__(self, another):
        return self.get_name() == another.get_name()

    def __ne__(self, another):
        return self.get_name() != another.get_name()

    def _get_params(self):
        return {"user": self.get_name()}

    def get_name(self):
        """Returns the nuser name."""

        return self.name

    def get_upcoming_events(self):
        """Returns all the upcoming events for this user. """

        doc = self._request('user.getEvents', True)

        ids = _extract_all(doc, 'id')
        events = []

        for e_id in ids:
            events.append(Event(e_id, self.network))

        return events

    def get_friends(self, limit=50):
        """Returns a list of the user's friends. """

        seq = []
        for node in _collect_nodes(limit, self, "user.getFriends", False):
            seq.append(User(_extract_data(node, "name"), self.network))

        return seq

    def get_loved_tracks(self, limit=50):
        """Returns this user's loved track as a sequence of LovedTrack objects
        in reverse order of their timestamp, all the way back to the first track.

        If limit==None, it will try to pull all the available data.

        This method uses caching. Enable caching only if you're pulling a
        large amount of data.

        Use extract_items() with the return of this function to
        get only a sequence of Track objects with no playback dates. """

        params = self._get_params()
        if limit:
            params['limit'] = _unicode(limit)

        seq = []
        for track in _collect_nodes(limit, self, "user.getLovedTracks", True, params):

            title = _extract_data(track, "name")
            artist = _extract_data(track, "name", 1)
            date = _extract_data(track, "date")
            timestamp = track.getElementsByTagName("date")[0].getAttribute("uts")

            seq.append(LovedTrack(Track(artist, title, self.network), date, timestamp))

        return seq

    def get_neighbours(self, limit=50):
        """Returns a list of the user's friends."""

        params = self._get_params()
        if limit:
            params['limit'] = _unicode(limit)

        doc = self._request('user.getNeighbours', True, params)

        seq = []
        names = _extract_all(doc, 'name')

        for name in names:
            seq.append(User(name, self.network))

        return seq

    def get_past_events(self, limit=50):
        """
        Returns a sequence of Event objects
        if limit==None it will return all
        """

        seq = []
        for n in _collect_nodes(limit, self, "user.getPastEvents", False):
            seq.append(Event(_extract_data(n, "id"), self.network))

        return seq

    def get_playlists(self):
        """Returns a list of Playlists that this user owns."""

        doc = self._request("user.getPlaylists", True)

        playlists = []
        for playlist_id in _extract_all(doc, "id"):
            playlists.append(Playlist(self.get_name(), playlist_id, self.network))

        return playlists

    def get_now_playing(self):
        """Returns the currently playing track, or None if nothing is playing. """

        params = self._get_params()
        params['limit'] = '1'

        doc = self._request('user.getRecentTracks', False, params)

        e = doc.getElementsByTagName('track')[0]

        if not e.hasAttribute('nowplaying'):
            return None

        artist = _extract_data(e, 'artist')
        title = _extract_data(e, 'name')

        return Track(artist, title, self.network)


    def get_recent_tracks(self, limit=10):
        """Returns this user's played track as a sequence of PlayedTrack objects
        in reverse order of their playtime, all the way back to the first track.

        If limit==None, it will try to pull all the available data.

        This method uses caching. Enable caching only if you're pulling a
        large amount of data.

        Use extract_items() with the return of this function to
        get only a sequence of Track objects with no playback dates. """

        params = self._get_params()
        if limit:
            params['limit'] = _unicode(limit)

        seq = []
        for track in _collect_nodes(limit, self, "user.getRecentTracks", True, params):

            if track.hasAttribute('nowplaying'):
                continue    #to prevent the now playing track from sneaking in here

            title = _extract_data(track, "name")
            artist = _extract_data(track, "artist")
            date = _extract_data(track, "date")
            timestamp = track.getElementsByTagName("date")[0].getAttribute("uts")

            seq.append(PlayedTrack(Track(artist, title, self.network), date, timestamp))

        return seq

    def get_top_albums(self, period=PERIOD_OVERALL):
        """Returns the top albums played by a user.
        * period: The period of time. Possible values:
          o PERIOD_OVERALL
          o PERIOD_3MONTHS
          o PERIOD_6MONTHS
          o PERIOD_12MONTHS
        """

        params = self._get_params()
        params['period'] = period

        doc = self._request('user.getTopAlbums', True, params)

        seq = []
        for album in doc.getElementsByTagName('album'):
            name = _extract_data(album, 'name')
            artist = _extract_data(album, 'name', 1)
            playcount = _extract_data(album, "playcount")

            seq.append(TopItem(Album(artist, name, self.network), playcount))

        return seq

    def get_top_artists(self, period=PERIOD_OVERALL):
        """Returns the top artists played by a user.
        * period: The period of time. Possible values:
          o PERIOD_OVERALL
          o PERIOD_3MONTHS
          o PERIOD_6MONTHS
          o PERIOD_12MONTHS
        """

        params = self._get_params()
        params['period'] = period

        doc = self._request('user.getTopArtists', True, params)

        seq = []
        for node in doc.getElementsByTagName('artist'):
            name = _extract_data(node, 'name')
            playcount = _extract_data(node, "playcount")

            seq.append(TopItem(Artist(name, self.network), playcount))

        return seq

    def get_top_tags(self, limit=None):
        """Returns a sequence of the top tags used by this user with their counts as (Tag, tagcount).
        * limit: The limit of how many tags to return.
        """

        doc = self._request("user.getTopTags", True)

        seq = []
        for node in doc.getElementsByTagName("tag"):
            if len(seq) < limit:
                seq.append(TopItem(Tag(_extract_data(node, "name"), self.network), _extract_data(node, "count")))

        return seq

    def get_top_tracks(self, period=PERIOD_OVERALL):
        """Returns the top tracks played by a user.
        * period: The period of time. Possible values:
          o PERIOD_OVERALL
          o PERIOD_3MONTHS
          o PERIOD_6MONTHS
          o PERIOD_12MONTHS
        """

        params = self._get_params()
        params['period'] = period

        doc = self._request('user.getTopTracks', True, params)

        seq = []
        for track in doc.getElementsByTagName('track'):
            name = _extract_data(track, 'name')
            artist = _extract_data(track, 'name', 1)
            playcount = _extract_data(track, "playcount")

            seq.append(TopItem(Track(artist, name, self.network), playcount))

        return seq

    def get_weekly_chart_dates(self):
        """Returns a list of From and To tuples for the available charts."""

        doc = self._request("user.getWeeklyChartList", True)

        seq = []
        for node in doc.getElementsByTagName("chart"):
            seq.append((node.getAttribute("from"), node.getAttribute("to")))

        return seq

    def get_weekly_artist_charts(self, from_date=None, to_date=None):
        """Returns the weekly artist charts for the week starting from the from_date value to the to_date value."""

        params = self._get_params()
        if from_date and to_date:
            params["from"] = from_date
            params["to"] = to_date

        doc = self._request("user.getWeeklyArtistChart", True, params)

        seq = []
        for node in doc.getElementsByTagName("artist"):
            item = Artist(_extract_data(node, "name"), self.network)
            weight = _number(_extract_data(node, "playcount"))
            seq.append(TopItem(item, weight))

        return seq

    def get_weekly_album_charts(self, from_date=None, to_date=None):
        """Returns the weekly album charts for the week starting from the from_date value to the to_date value."""

        params = self._get_params()
        if from_date and to_date:
            params["from"] = from_date
            params["to"] = to_date

        doc = self._request("user.getWeeklyAlbumChart", True, params)

        seq = []
        for node in doc.getElementsByTagName("album"):
            item = Album(_extract_data(node, "artist"), _extract_data(node, "name"), self.network)
            weight = _number(_extract_data(node, "playcount"))
            seq.append(TopItem(item, weight))

        return seq

    def get_weekly_track_charts(self, from_date=None, to_date=None):
        """Returns the weekly track charts for the week starting from the from_date value to the to_date value."""

        params = self._get_params()
        if from_date and to_date:
            params["from"] = from_date
            params["to"] = to_date

        doc = self._request("user.getWeeklyTrackChart", True, params)

        seq = []
        for node in doc.getElementsByTagName("track"):
            item = Track(_extract_data(node, "artist"), _extract_data(node, "name"), self.network)
            weight = _number(_extract_data(node, "playcount"))
            seq.append(TopItem(item, weight))

        return seq

    def compare_with_user(self, user, shared_artists_limit=None):
        """Compare this user with another Last.fm user.
        Returns a sequence (tasteometer_score, (shared_artist1, shared_artist2, ...))
        user: A User object or a username string/unicode object.
        """

        if isinstance(user, User):
            user = user.get_name()

        params = self._get_params()
        if shared_artists_limit:
            params['limit'] = _unicode(shared_artists_limit)
        params['type1'] = 'user'
        params['type2'] = 'user'
        params['value1'] = self.get_name()
        params['value2'] = user

        doc = self._request('tasteometer.compare', False, params)

        score = _extract_data(doc, 'score')

        artists = doc.getElementsByTagName('artists')[0]
        shared_artists_names = _extract_all(artists, 'name')

        shared_artists_seq = []

        for name in shared_artists_names:
            shared_artists_seq.append(Artist(name, self.network))

        return (score, shared_artists_seq)

    def get_url(self, domain_name=DOMAIN_ENGLISH):
        """Returns the url of the user page on the network.
        * domain_name: The network's language domain. Possible values:
          o DOMAIN_ENGLISH
          o DOMAIN_GERMAN
          o DOMAIN_SPANISH
          o DOMAIN_FRENCH
          o DOMAIN_ITALIAN
          o DOMAIN_POLISH
          o DOMAIN_PORTUGUESE
          o DOMAIN_SWEDISH
          o DOMAIN_TURKISH
          o DOMAIN_RUSSIAN
          o DOMAIN_JAPANESE
          o DOMAIN_CHINESE
        """

        name = _url_safe(self.get_name())

        return self.network._get_url(domain_name, "user") % {'name': name}

    def get_library(self):
        """Returns the associated Library object. """

        return Library(self, self.network)

    def get_shouts(self, limit=50):
        """
            Returns a sequqence of Shout objects
        """

        shouts = []
        for node in _collect_nodes(limit, self, "user.getShouts", False):
            shouts.append(Shout(
                                _extract_data(node, "body"),
                                User(_extract_data(node, "author"), self.network),
                                _extract_data(node, "date")
                                )
                            )
        return shouts

    def shout(self, message):
        """
            Post a shout
        """

        params = self._get_params()
        params["message"] = message

        self._request("user.Shout", False, params)

class AuthenticatedUser(User):
    def __init__(self, network):
        User.__init__(self, "", network);

    def _get_params(self):
        return {"user": self.get_name()}

    def get_name(self):
        """Returns the name of the authenticated user."""

        doc = self._request("user.getInfo", True, {"user": ""})    # hack

        self.name = _extract_data(doc, "name")
        return self.name

    def get_id(self):
        """Returns the user id."""

        doc = self._request("user.getInfo", True)

        return _extract_data(doc, "id")

    def get_cover_image(self):
        """Returns the user's avatar."""

        doc = self._request("user.getInfo", True)

        return _extract_data(doc, "image")

    def get_language(self):
        """Returns the language code of the language used by the user."""

        doc = self._request("user.getInfo", True)

        return _extract_data(doc, "lang")

    def get_country(self):
        """Returns the name of the country of the user."""

        doc = self._request("user.getInfo", True)

        return Country(_extract_data(doc, "country"), self.network)

    def get_age(self):
        """Returns the user's age."""

        doc = self._request("user.getInfo", True)

        return _number(_extract_data(doc, "age"))

    def get_gender(self):
        """Returns the user's gender. Either USER_MALE or USER_FEMALE."""

        doc = self._request("user.getInfo", True)

        value = _extract_data(doc, "gender")

        if value == 'm':
            return USER_MALE
        elif value == 'f':
            return USER_FEMALE

        return None

    def is_subscriber(self):
        """Returns whether the user is a subscriber or not. True or False."""

        doc = self._request("user.getInfo", True)

        return _extract_data(doc, "subscriber") == "1"

    def get_playcount(self):
        """Returns the user's playcount so far."""

        doc = self._request("user.getInfo", True)

        return _number(_extract_data(doc, "playcount"))

    def get_recommended_events(self, limit=50):
        """
        Returns a sequence of Event objects
        if limit==None it will return all
        """

        seq = []
        for node in _collect_nodes(limit, self, "user.getRecommendedEvents", False):
            seq.append(Event(_extract_data(node, "id"), self.network))

        return seq

    def get_recommended_artists(self, limit=50):
        """
        Returns a sequence of Event objects
        if limit==None it will return all
        """

        seq = []
        for node in _collect_nodes(int(limit), self, "user.getRecommendedArtists", False):
            seq.append(Artist(_extract_data(node, "name"), self.network))

        return seq

class _Search(_BaseObject):
    """An abstract class. Use one of its derivatives."""

    def __init__(self, ws_prefix, search_terms, network):
        _BaseObject.__init__(self, network)

        self._ws_prefix = ws_prefix
        self.search_terms = search_terms

        self._last_page_index = 0

    def _get_params(self):
        params = {}

        for key in self.search_terms.keys():
            params[key] = self.search_terms[key]

        return params

    def get_total_result_count(self):
        """Returns the total count of all the results."""

        doc = self._request(self._ws_prefix + ".search", True)

        return _extract_data(doc, "opensearch:totalResults")

    def _retreive_page(self, page_index):
        """Returns the node of matches to be processed"""

        params = self._get_params()
        params["page"] = str(page_index)
        doc = self._request(self._ws_prefix + ".search", True, params)

        return doc.getElementsByTagName(self._ws_prefix + "matches")[0]

    def _retrieve_next_page(self):
        self._last_page_index += 1
        return self._retreive_page(self._last_page_index)

class AlbumSearch(_Search):
    """Search for an album by name."""

    def __init__(self, album_name, network):

        _Search.__init__(self, "album", {"album": album_name}, network)

    def get_next_page(self):
        """Returns the next page of results as a sequence of Album objects."""

        master_node = self._retrieve_next_page()

        seq = []
        for node in master_node.getElementsByTagName("album"):
            seq.append(Album(_extract_data(node, "artist"), _extract_data(node, "name"), self.network))

        return seq

class ArtistSearch(_Search):
    """Search for an artist by artist name."""

    def __init__(self, artist_name, network):
        _Search.__init__(self, "artist", {"artist": artist_name}, network)

    def get_next_page(self):
        """Returns the next page of results as a sequence of Artist objects."""

        master_node = self._retrieve_next_page()

        seq = []
        for node in master_node.getElementsByTagName("artist"):
            seq.append(Artist(_extract_data(node, "name"), self.network))

        return seq

class TagSearch(_Search):
    """Search for a tag by tag name."""

    def __init__(self, tag_name, network):

        _Search.__init__(self, "tag", {"tag": tag_name}, network)

    def get_next_page(self):
        """Returns the next page of results as a sequence of Tag objects."""

        master_node = self._retrieve_next_page()

        seq = []
        for node in master_node.getElementsByTagName("tag"):
            seq.append(Tag(_extract_data(node, "name"), self.network))

        return seq

class TrackSearch(_Search):
    """Search for a track by track title. If you don't wanna narrow the results down
    by specifying the artist name, set it to empty string."""

    def __init__(self, artist_name, track_title, network):

        _Search.__init__(self, "track", {"track": track_title, "artist": artist_name}, network)

    def get_next_page(self):
        """Returns the next page of results as a sequence of Track objects."""

        master_node = self._retrieve_next_page()

        seq = []
        for node in master_node.getElementsByTagName("track"):
            seq.append(Track(_extract_data(node, "artist"), _extract_data(node, "name"), self.network))

        return seq

class VenueSearch(_Search):
    """Search for a venue by its name. If you don't wanna narrow the results down
    by specifying a country, set it to empty string."""

    def __init__(self, venue_name, country_name, network):

        _Search.__init__(self, "venue", {"venue": venue_name, "country": country_name}, network)

    def get_next_page(self):
        """Returns the next page of results as a sequence of Track objects."""

        master_node = self._retrieve_next_page()

        seq = []
        for node in master_node.getElementsByTagName("venue"):
            seq.append(Venue(_extract_data(node, "id"), self.network))

        return seq

class Venue(_BaseObject):
    """A venue where events are held."""

    # TODO: waiting for a venue.getInfo web service to use.

    id = None

    def __init__(self, id, network):
        _BaseObject.__init__(self, network)

        self.id = _number(id)

    @_string_output
    def __repr__(self):
        return "Venue #" + str(self.id)

    def __eq__(self, other):
        return self.get_id() == other.get_id()

    def _get_params(self):
        return {"venue": self.get_id()}

    def get_id(self):
        """Returns the id of the venue."""

        return self.id

    def get_upcoming_events(self):
        """Returns the upcoming events in this venue."""

        doc = self._request("venue.getEvents", True)

        seq = []
        for node in doc.getElementsByTagName("event"):
            seq.append(Event(_extract_data(node, "id"), self.network))

        return seq

    def get_past_events(self):
        """Returns the past events held in this venue."""

        doc = self._request("venue.getEvents", True)

        seq = []
        for node in doc.getElementsByTagName("event"):
            seq.append(Event(_extract_data(node, "id"), self.network))

        return seq

def md5(text):
    """Returns the md5 hash of a string."""

    h = hashlib.md5()
    h.update(_string(text))

    return h.hexdigest()

def async_call(sender, call, callback=None, call_args=None, callback_args=None):
    """This is the function for setting up an asynchronous operation.
    * call: The function to call asynchronously.
    * callback: The function to call after the operation is complete, Its prototype has to be like:
        callback(sender, output[, param1, param3, ... ])
    * call_args: A sequence of args to be passed to call.
    * callback_args: A sequence of args to be passed to callback.
    """

    thread = _ThreadedCall(sender, call, call_args, callback, callback_args)
    thread.start()

def _unicode(text):
    if type(text) == unicode:
        return text

    if type(text) == int:
        return unicode(text)

    return unicode(text, "utf-8")

def _string(text):
    if type(text) == str:
        return text

    if type(text) == int:
        return str(text)

    return text.encode("utf-8")

def _collect_nodes(limit, sender, method_name, cacheable, params=None):
    """
        Returns a sequqnce of dom.Node objects about as close to
        limit as possible
    """

    if not limit: limit = sys.maxint
    if not params: params = sender._get_params()

    nodes = []
    page = 1
    end_of_pages = False

    while len(nodes) < limit and not end_of_pages:
        params["page"] = str(page)
        doc = sender._request(method_name, cacheable, params)

        main = doc.documentElement.childNodes[1]

        if main.hasAttribute("totalPages"):
            total_pages = _number(main.getAttribute("totalPages"))
        elif main.hasAttribute("totalpages"):
            total_pages = _number(main.getAttribute("totalpages"))
        else:
            raise Exception("No total pages attribute")

        for node in main.childNodes:
            if not node.nodeType == xml.dom.Node.TEXT_NODE and len(nodes) < limit:
                nodes.append(node)

        if page >= total_pages:
            end_of_pages = True

        page += 1

    return nodes

def _extract_data(node, name, index=0):
    """Extracts a value from the xml string"""

    nodes = node.getElementsByTagName(name)

    if len(nodes):
        if nodes[index].firstChild:
            return _unescape_htmlentity(nodes[index].firstChild.data.strip())
    else:
        return None

def _extract_whole_text(node, name, index=0):
    """Extracts a value from the xml string"""

    nodes = node.getElementsByTagName(name)

    if len(nodes):
        if nodes[index].firstChild:
            return _unescape_htmlentity(nodes[index].firstChild.wholeText.strip())
    else:
        return None

def _extract_all(node, name, limit_count=None):
    """Extracts all the values from the xml string. returning a list."""

    seq = []

    for i in range(0, len(node.getElementsByTagName(name))):
        if len(seq) == limit_count:
            break

        seq.append(_extract_data(node, name, i))

    return seq

def _url_safe(text):
    """Does all kinds of tricks on a text to make it safe to use in a url."""

    if type(text) == unicode:
        text = text.encode('utf-8')

    return urllib.quote_plus(urllib.quote_plus(text)).lower()

def _number(string):
    """
        Extracts an int from a string. Returns a 0 if None or an empty string was passed
    """
    if not string:
        return 0
    elif string == "":
        return 0
    else:
        try:
            return int(string)
        except ValueError:
            return float(string)

def _unescape_htmlentity(string):

    string = _unicode(string)

    mapping = htmlentitydefs.name2codepoint
    for key in mapping:
        string = string.replace("&%s;" % key, unichr(mapping[key]))

    return string

def extract_items(topitems_or_libraryitems):
    """Extracts a sequence of items from a sequence of TopItem or LibraryItem objects."""

    seq = []
    for i in topitems_or_libraryitems:
        seq.append(i.item)

    return seq

class ScrobblingError(Exception):
    def __init__(self, message):
        Exception.__init__(self)
        self.message = message

    @_string_output
    def __str__(self):
        return self.message

class BannedClientError(ScrobblingError):
    def __init__(self):
        ScrobblingError.__init__(self, "This version of the client has been banned")

class BadAuthenticationError(ScrobblingError):
    def __init__(self):
        ScrobblingError.__init__(self, "Bad authentication token")

class BadTimeError(ScrobblingError):
    def __init__(self):
        ScrobblingError.__init__(self, "Time provided is not close enough to current time")

class BadSessionError(ScrobblingError):
    def __init__(self):
        ScrobblingError.__init__(self, "Bad session id, consider re-handshaking")

class _ScrobblerRequest(object):

    def __init__(self, url, params, network, type="POST"):
        self.params = params
        self.type = type
        (self.hostname, self.subdir) = urllib.splithost(url[len("http:"):])
        self.network = network

    def execute(self):
        """Returns a string response of this request."""

        connection = httplib.HTTPConnection(self.hostname)

        data = []
        for name in self.params.keys():
            value = urllib.quote_plus(self.params[name])
            data.append('='.join((name, value)))
        data = "&".join(data)

        headers = {
            "Content-type": "application/x-www-form-urlencoded",
            "Accept-Charset": "utf-8",
            "User-Agent": "pylast" + "/" + __version__,
            "HOST": self.hostname
            }
        if self.network.is_proxy_enabled():
            proxy_rul = FC().proxy_url
            index = proxy_rul.find(":")
            proxy = proxy_rul[:index]
            port = proxy_rul[index + 1:]
            """Changed by zavlab1"""
            if FC().proxy_user and FC().proxy_password:
                user = urllib2.unquote(FC().proxy_user)
                password = urllib2.unquote(FC().proxy_password)
                auth = base64.b64encode(user + ":" + password).strip()
                headers['Proxy-Authorization'] =  '''Basic %s''' % auth

            connection = httplib.HTTPConnection(host=proxy, port=port)
            if self.type == "GET":
                connection.request(method="GET", url="http://" + self.hostname + self.subdir + "?" + data,
                                   headers=headers)
            else:
                connection.request(method="POST", url="http://" + self.hostname + self.subdir,
                                   body=data, headers=headers)
        else:
            if self.type == "GET":
                connection.request("GET", self.subdir + "?" + data, headers=headers)
            else:
                connection.request("POST", self.subdir, data, headers)

        response = connection.getresponse().read()

        self._check_response_for_errors(response)

        return response

    def _check_response_for_errors(self, response):
        """When passed a string response it checks for erros, raising
        any exceptions as necessary."""

        lines = response.split("\n")
        status_line = lines[0]

        if status_line == "OK":
            return
        elif status_line == "BANNED":
            raise BannedClientError()
        elif status_line == "BADAUTH":
            raise BadAuthenticationError()
        elif status_line == "BadTimeError":
            raise BadTimeError()
        elif status_line == "BadSessionError":
            raise BadSessionError()
        elif status_line.startswith("FAILED "):
            reason = status_line[status_line.find("FAILED ") + len("FAILED "):]
            raise ScrobblingError(reason)

class Scrobbler(object):
    """A class for scrobbling tracks to Last.fm"""

    session_id = None
    nowplaying_url = None
    submissions_url = None

    def __init__(self, network, client_id, client_version):
        self.client_id = client_id
        self.client_version = client_version
        self.username = network.username
        self.password = network.password_hash
        self.network = network

    def _do_handshake(self):
        """Handshakes with the server"""

        timestamp = str(int(time.time()))

        if self.password and self.username:
            token = md5(self.password + timestamp)
        elif self.network.api_key and self.network.api_secret and self.network.session_key:
            if not self.username:
                self.username = self.network.get_authenticated_user().get_name()
            token = md5(self.network.api_secret + timestamp)

        params = {"hs": "true", "p": "1.2.1", "c": self.client_id,
            "v": self.client_version, "u": self.username, "t": timestamp,
            "a": token}

        if self.network.session_key and self.network.api_key:
            params["sk"] = self.network.session_key
            params["api_key"] = self.network.api_key

        server = self.network.submission_server
        response = _ScrobblerRequest(server, params, self.network, "GET").execute().split("\n")

        self.session_id = response[1]
        self.nowplaying_url = response[2]
        self.submissions_url = response[3]

    def _get_session_id(self, new=False):
        """Returns a handshake. If new is true, then it will be requested from the server
        even if one was cached."""

        if not self.session_id or new:
            self._do_handshake()

        return self.session_id

    def report_now_playing(self, artist, title, album="", duration="", track_number="", mbid=""):

        params = {"s": self._get_session_id(), "a": artist, "t": title,
            "b": album, "l": duration, "n": track_number, "m": mbid}

        try:
            _ScrobblerRequest(self.nowplaying_url, params, self.network).execute()
        except BadSessionError:
            self._do_handshake()
            self.report_now_playing(artist, title, album, duration, track_number, mbid)

    def scrobble(self, artist, title, time_started, source, mode, duration, album="", track_number="", mbid=""):
        """Scrobble a track. parameters:
            artist: Artist name.
            title: Track title.
            time_started: UTC timestamp of when the track started playing.
            source: The source of the track
                SCROBBLE_SOURCE_USER: Chosen by the user (the most common value, unless you have a reason for choosing otherwise, use this).
                SCROBBLE_SOURCE_NON_PERSONALIZED_BROADCAST: Non-personalised broadcast (e.g. Shoutcast, BBC Radio 1).
                SCROBBLE_SOURCE_PERSONALIZED_BROADCAST: Personalised recommendation except Last.fm (e.g. Pandora, Launchcast).
                SCROBBLE_SOURCE_LASTFM: ast.fm (any mode). In this case, the 5-digit recommendation_key value must be set.
                SCROBBLE_SOURCE_UNKNOWN: Source unknown.
            mode: The submission mode
                SCROBBLE_MODE_PLAYED: The track was played.
                SCROBBLE_MODE_LOVED: The user manually loved the track (implies a listen)
                SCROBBLE_MODE_SKIPPED: The track was skipped (Only if source was Last.fm)
                SCROBBLE_MODE_BANNED: The track was banned (Only if source was Last.fm)
            duration: Track duration in seconds.
            album: The album name.
            track_number: The track number on the album.
            mbid: MusicBrainz ID.
        """

        params = {"s": self._get_session_id(), "a[0]": _string(artist), "t[0]": _string(title),
            "i[0]": str(time_started), "o[0]": source, "r[0]": mode, "l[0]": str(duration),
            "b[0]": _string(album), "n[0]": track_number, "m[0]": mbid}

        _ScrobblerRequest(self.submissions_url, params, self.network).execute()

########NEW FILE########
__FILENAME__ = sound_menu
#!/usr/bin/python
# -*- coding: utf-8 -*-
### BEGIN LICENSE
# Copyright (C) 2011 Rick Spencer <rick.spencer@canonical.com>
# This program is free software: you can redistribute it and/or modify it
# under the terms of the GNU General Public License version 3, as published
# by the Free Software Foundation.
#
# This program is distributed in the hope that it will be useful, but
# WITHOUT ANY WARRANTY; without even the implied warranties of
# MERCHANTABILITY, SATISFACTORY QUALITY, or FITNESS FOR A PARTICULAR
# PURPOSE.  See the GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License along
# with this program.  If not, see <http://www.gnu.org/licenses/>.
### END LICENSE

"""Contains SoundMenuControls, A class to make it easy to integrate with the Ubuntu Sound Menu.

In order for a media player to appear in the sonud menu, it must have
a desktop file in /usr/share/applications. For example, for a media player
named "simple" player, there must be desktop file /usr/share/applications/simple-player.desktop

The desktop file must specify that it is indeed a media player. For example, simple-player.desktop
might look like the follwing:
[Desktop Entry]
Name=Simple Player
Comment=SimplePlayer application
Categories=GNOME;Audio;Music;Player;AudioVideo;
Exec=simple-player
Icon=simple-player
Terminal=false
Type=Application
MimeType=application/x-ogg;application/ogg;audio/x-vorbis+ogg;audio/x-scpls;audio/x-mp3;audio/x-mpeg;audio/mpeg;audio/x-mpegurl;audio/x-flac;

In order for the sound menu to run, a dbus loop must be running before
the player is created and before the Gtk. mainloop is run. you can add
DBusGMainLoop(set_as_default=True) to your application's __main__ function.

The Ubuntu Sound Menu integrates with applications via the MPRIS2 dbus api,
which is specified here: http://www.mpris.org/2.1/spec/

This module does strive to provide an MPRIS2 implementation, but rather
focuses on the subset of functionality required by the Sound Menu.

The SoundMenuControls class can be ininstatiated, but does not provide any
default functionality. In order to provide the required functionality,
implementations must be provided for the functions starting with
"_sound_menu", such as "_sound_menu_play", etc...

Functions and properties starting with capitalize letters, such as
"Next" and "Previous" are called by the Ubuntu Sound Menu. These
functions and properties are not designed to be called directly
or overriden by application code, only the Sound Menu.

Other functions are designed to be called as needed by the
implementation to inform the Sound Menu of changes. Thse functions
include signal_playing, signal_paused, and song_changed.

Using
#create the sound menu object and reassign functions
sound_menu = SoundMenuControls(desktop_name)
sound_menu._sound_menu_next = _sound_menu_next
sound_menu._sound_menu_previous = _sound_menu_previous
sound_menu._sound_menu_is_playing = _sound_menu_is_playing
sound_menu._sound_menu_play = _sound_menu_play
sound_menu._sound_menu_pause = _sound_menu_play
sound_menu._sound_menu_raise = _sound_menu_raise

#when the song in the player changes, it should inform
the sond menu
sound_menu.song_changed(artist,album,title)

#when the player changes to/from the playing, it should inform the sound menu
sound_menu.signal_playing()
sound_menu.signal_paused()

#whent the song is changed from the application,
#use song_changed to inform the Ubuntu Sound Menu
sound_menu.song_changed(artist, album, song_title)

Configuring
SoundMenuControls does not come with any stock behaviors, so it
cannot be configured

Extending
SoundMenuControls can be used as a base class with single or multiple inheritance.

_sound_menu_next
_sound_menu_previous
_sound_menu_is_playing
_sound_menu_play
_sound_menu_pause

"""

import dbus
import dbus.service

class SoundMenuControls(dbus.service.Object):
    """
    SoundMenuControls - A class to make it easy to integrate with the Ubuntu Sound Menu.

    """

    def __init__(self, desktop_name):
        """
        Creates a SoundMenuControls object.

        Requires a dbus loop to be created before the gtk mainloop,
        typically by calling DBusGMainLoop(set_as_default=True).

        arguments:
        desktop_name: The name of the desktop file for the application,
        such as, "simple-player" to refer to the file: simple-player.desktop.

        """

        self.desktop_name = desktop_name
        bus_str = """org.mpris.MediaPlayer2.%s""" % desktop_name
        bus_name = dbus.service.BusName(bus_str, bus=dbus.SessionBus())
        dbus.service.Object.__init__(self, bus_name, "/org/mpris/MediaPlayer2")
        self.__playback_status = "Stopped"

        self.song_changed()

    def song_changed(self, artists = None, album = None, title = None, cover = None):
        """song_changed - sets the info for the current song.

        This method is not typically overriden. It should be called
        by implementations of this class when the player has changed
        songs.

        named arguments:
            artists - a list of strings representing the artists"
            album - a string for the name of the album
            title - a string for the title of the song

        """

        if artists is None:
            artists = ["Artist Unknown"]
        if album is None:
            album = "Album Uknown"
        if title is None:
            title = "Title Uknown"
        data = {"xesam:album": album,
                "xesam:title": title,
                "xesam:artist": artists
                }
        if cover:
            data["mpris:artUrl"] = cover
        self.__meta_data = dbus.Dictionary(data, "sv", variant_level=1)


    @dbus.service.method('org.mpris.MediaPlayer2')
    def Raise(self):
        """Raise

        A dbus signal handler for the Raise signal. Do no override this
        function directly. rather, overrise _sound_menu_raise. This
        function is typically only called by the Sound, not directly
        from code.

        """

        self._sound_menu_raise()

    def _sound_menu_raise(self):
        """ _sound_menu_raise -

        Override this function to bring the media player to the front
        when selected by the sound menu. For example, by calling
        app_window.get_window().show()

        """

        raise NotImplementedError("""@dbus.service.method('org.mpris.MediaPlayer2') Raise
                                      is not implemented by this player.""")


    @dbus.service.method(dbus.PROPERTIES_IFACE, in_signature='ss', out_signature='v')
    def Get(self, interface, prop):
        """Get

        A function necessary to implement dbus properties.

        This function is only called by the Sound Menu, and should not
        be overriden or called directly.

        """

        my_prop = self.__getattribute__(prop)
        return my_prop

    @dbus.service.method(dbus.PROPERTIES_IFACE, in_signature='ssv')
    def Set(self, interface, prop, value):
        """Set

        A function necessary to implement dbus properties.

        This function is only called by the Sound Menu, and should not
        be overriden or called directly.

        """
        my_prop = self.__getattribute__(prop)
        my_prop = value

    @dbus.service.method(dbus.PROPERTIES_IFACE, in_signature='s', out_signature='a{sv}')
    def GetAll(self, interface):
        """GetAll

        A function necessary to implement dbus properties.

        This function is only called by the Sound Menu, and should not
        be overriden or called directly.

        """

        return [DesktopEntry, PlaybackStatus, MetaData]

    @property
    def DesktopEntry(self):
        """DesktopEntry

        The name of the desktop file.

        This propert is only used by the Sound Menu, and should not
        be overriden or called directly.

        """

        return self.desktop_name

    @property
    def PlaybackStatus(self):
        """PlaybackStatus

        Current status "Playing", "Paused", or "Stopped"

        This property is only used by the Sound Menu, and should not
        be overriden or called directly.

        """

        return self.__playback_status

    @property
    def MetaData(self):
        """MetaData

        The info for the current song.

        This property is only used by the Sound Menu, and should not
        be overriden or called directly.

        """

        return self.__meta_data

    @dbus.service.method('org.mpris.MediaPlayer2.Player')
    def Next(self):
        """Next

        A dbus signal handler for the Next signal. Do no override this
        function directly. Rather, overide _sound_menu_next. This
        function is typically only called by the Sound, not directly
        from code.

        """

        self._sound_menu_next()

    def _sound_menu_next(self):
        """_sound_menu_next

        This function is called when the user has clicked
        the next button in the Sound Indicator. Implementations
        should overrirde this function in order to a function to
        advance to the next track. Implementations should call
        song_changed() and sound_menu.signal_playing() in order to
        keep the song information in the sound menu in sync.

        The default implementation of this function has no effect.

        """
        pass

    @dbus.service.method('org.mpris.MediaPlayer2.Player')
    def Previous(self):
        """Previous

        A dbus signal handler for the Previous signal. Do no override this
        function directly. Rather, overide _sound_menu_previous. This
        function is typically only called by the Sound Menu, not directly
        from code.

        """


        self._sound_menu_previous()

    def _sound_menu_previous(self):
        """_sound_menu_previous

        This function is called when the user has clicked
        the previous button in the Sound Indicator. Implementations
        should overrirde this function in order to a function to
        advance to the next track. Implementations should call
        song_changed() and  sound_menu.signal_playing() in order to
        keep the song information in sync.

        The default implementation of this function has no effect.


        """
        pass

    @dbus.service.method('org.mpris.MediaPlayer2.Player')
    def PlayPause(self):
        """Next

        A dbus signal handler for the Next signal. Do no override this
        function directly. Rather, overide _sound_menu_next. This
        function is typically only called by the Sound, not directly
        from code.

        """

        if not self._sound_menu_is_playing():
            self._sound_menu_play()
            self.signal_playing()
        else:
            self._sound_menu_pause()
            self.signal_paused()

    def signal_playing(self):
        """signal_playing - Tell the Sound Menu that the player has
        started playing. Implementations many need to call this function in order
        to keep the Sound Menu in synch.

        arguments:
            none

        """
        self.__playback_status = "Playing"
        d = dbus.Dictionary({"PlaybackStatus":self.__playback_status, "Metadata":self.__meta_data},
                            "sv",variant_level=1)
        self.PropertiesChanged("org.mpris.MediaPlayer2.Player",d,[])

    def signal_paused(self):
        """signal_paused - Tell the Sound Menu that the player has
        been paused. Implementations many need to call this function in order
        to keep the Sound Menu in synch.

        arguments:
            none

        """

        self.__playback_status = "Paused"
        d = dbus.Dictionary({"PlaybackStatus":self.__playback_status},
                            "sv",variant_level=1)
        self.PropertiesChanged("org.mpris.MediaPlayer2.Player",d,[])

    def signal_stopped(self):
        self.__playback_status = "Stopped"
        d = dbus.Dictionary({"PlaybackStatus": self.__playback_status},
                            "sv", variant_level=1)
        self.PropertiesChanged("org.mpris.MediaPlayer2.Player", d, [])

    def _sound_menu_is_playing(self):
        """_sound_menu_is_playing

        Check if the the player is playing,.
        Implementations should overrirde this function
        so that the Sound Menu can check whether to display
        Play or Pause functionality.

        The default implementation of this function always
        returns False.

        arguments:
            none

        returns:
            returns True if the player is playing, otherwise
            returns False if the player is stopped or paused.
        """

        return False

    def _sound_menu_pause(self):
        """_sound_menu_pause

        Reponds to the Sound Menu when the user has click the
        Pause button.

        Implementations should overrirde this function
        to pause playback when called.

        The default implementation of this function does nothing

        arguments:
            none

        returns:
            None

       """

        pass

    def _sound_menu_play(self):
        """_sound_menu_play

        Reponds to the Sound Menu when the user has click the
        Play button.

        Implementations should overrirde this function
        to play playback when called.

        The default implementation of this function does nothing

        arguments:
            none

        returns:
            None

       """

        pass

    @dbus.service.signal(dbus.PROPERTIES_IFACE, signature='sa{sv}as')
    def PropertiesChanged(self, interface_name, changed_properties,
                          invalidated_properties):
        """PropertiesChanged

        A function necessary to implement dbus properties.

        Typically, this function is not overriden or called directly.

        """

        pass
########NEW FILE########
__FILENAME__ = agent
#-*- coding: utf-8 -*-
'''
Created on 24 дек. 20%0

@author: ivan
'''
import random

all_agents = """
Mozilla/5.0 (X11; U; Linux x86_64; en-US; rv:1.9.1.3) Gecko/20090913 Firefox/3.5.3
Mozilla/5.0 (Windows; U; Windows NT 6.1; en; rv:1.9.1.3) Gecko/20090824 Firefox/3.5.3 (.NET CLR 3.5.30729)
Mozilla/5.0 (Windows; U; Windows NT 5.2; en-US; rv:1.9.1.3) Gecko/20090824 Firefox/3.5.3 (.NET CLR 3.5.30729)
Mozilla/5.0 (Windows; U; Windows NT 6.1; en-US; rv:1.9.1.1) Gecko/20090718 Firefox/3.5.1
Mozilla/5.0 (Windows; U; Windows NT 5.1; en-US) AppleWebKit/532.1 (KHTML, like Gecko) Chrome/4.0.219.6 Safari/532.1
Mozilla/4.0 (compatible; MSIE 8.0; Windows NT 6.1; WOW64; Trident/4.0; SLCC2; .NET CLR 2.0.50727; InfoPath.2)
Mozilla/4.0 (compatible; MSIE 8.0; Windows NT 6.0; Trident/4.0; SLCC1; .NET CLR 2.0.50727; .NET CLR 1.1.4322; .NET CLR 3.5.30729; .NET CLR 3.0.30729)
Mozilla/4.0 (compatible; MSIE 8.0; Windows NT 5.2; Win64; x64; Trident/4.0)
Mozilla/4.0 (compatible; MSIE 8.0; Windows NT 5.1; Trident/4.0; SV1; .NET CLR 2.0.50727; InfoPath.2)Mozilla/5.0 (Windows; U; MSIE 7.0; Windows NT 6.0; en-US)
Mozilla/4.0 (compatible; MSIE 6.1; Windows XP)
"""

def get_ranmom_agent():
    agents = None
    for i in xrange(10):
        agents = all_agents.replace(str(i), str(random.randint(0, 10)))
    return agents.splitlines()[random.randint(1, 10)]

########NEW FILE########
__FILENAME__ = analytics
'''
Created on Nov 27, 2012

@author: iivanenko
'''

import urllib
import urllib2
import logging
import platform
import thread

from foobnix.version import FOOBNIX_VERSION
from foobnix.fc.fc_base import FCBase
from foobnix.util.const import SITE_LOCALE



"""
https://developers.google.com/analytics/devguides/collection/protocol/v1/devguide
https://developers.google.com/analytics/devguides/collection/protocol/v1/reference
https://developers.google.com/analytics/devguides/collection/protocol/v1/parameters
"""

api_url = "http://www.google-analytics.com/collect" 


def send(d={"t":"appview"}):
    params = { 
               "v":"1",
               "tid":"UA-36625986-1",
               "cid":FCBase().uuid,
                "ul":SITE_LOCALE,
                "an":"Foobnix",
                "av":FOOBNIX_VERSION,
                "cd1":platform.python_version(),
                "cd2":platform.platform()
              }
    params.update(d)

    #logging.debug("analytics params: "+str(params));
    enq = urllib.urlencode(params)
    thread.start_new_thread(urllib2.urlopen, (api_url, enq))
    #threading.Thread(target=urllib2.urlopen, args=(api_url, enq))
    

""" User Open or user Some Feature"""
def action(event_type="unknown"):
    send(d={"t":"appview","cd":event_type})
    logging.debug("analytics: action "+event_type);

""" User  Start Player """    
def begin_session():
    send(d={"t":"appview","sc":"start"})
    logging.debug("analytics: begin_session");
    
""" User  Stop Player """    
def end_session():
    send(d={"t":"appview","sc":"end"})
    logging.debug("analytics: end_session");

""" User  Type in  Player """    
def error(exDescription="Error"):
    send(d={"t":"exception","exd":exDescription})
    logging.debug("analytics: error");
     
if __name__ == '__main__':
    begin_session()
    action("Radio")  
    error("MainCrash")
    end_session()

########NEW FILE########
__FILENAME__ = antiscreensaver
#-*- coding: utf-8 -*-
'''
Created on June 12 2011

@author: zavlab1
'''

import os
import time
import threading
from foobnix.fc.fc import FC

def antiscreensaver():
    def task():
        while FC().antiscreensaver:
            os.system("xscreensaver-command -deactivate &") 
            time.sleep(55)

    t = threading.Thread(target=task)
    t.daemon = True #this thread must be only deamonic, else python process can't finish"
    t.start()
########NEW FILE########
__FILENAME__ = audio
'''
Created on Nov 10, 2010

@author: ivan
'''

import logging

from mutagen.asf import ASF
from mutagen.mp3 import MP3
from mutagen.mp4 import MP4
from mutagen.flac import FLAC
from mutagen.easyid3 import EasyID3
from mutagen.wavpack import WavPack
from mutagen.oggvorbis import OggVorbis
from mutagen.monkeysaudio import MonkeysAudio

from foobnix.util.file_utils import get_file_extension


def get_mutagen_audio (path):
    logging.debug("GET mutagen audio" + path)
    ext = get_file_extension(path)
    audio = None
    if ext == ".flac":
        audio = FLAC(path)
    if ext == ".ape":
        audio = MonkeysAudio(path)
    if ext == ".mp3":
        audio = MP3(path, ID3=EasyID3)
    if ext == ".wv":
        audio = WavPack(path)
    if ext == ".wma":
        audio = ASF(path)
    if ext == ".ogg":
        try:
            audio = OggVorbis(path)
        except:
            from mutagen.oggtheora import OggTheora
            try:
                audio = OggTheora(path)
            except:
                from mutagen.oggflac import OggFLAC
                try:
                    audio = OggFLAC(path)
                except:
                    from mutagen.oggspeex import OggSpeex
                    try:
                        audio = OggSpeex(path)
                    except:
                        logging.error("This file in not ogg format")

    if ext == ".m4a" or ext == ".mp4" or ext == ".mkv":
        audio = MP4(path)

    return audio

########NEW FILE########
__FILENAME__ = bean_utils
#-*- coding: utf-8 -*-
'''
Created on 20 окт. 2010

@author: ivan
'''
import os
import logging
from foobnix.gui.model import FDModel, FModel

from foobnix.util.text_utils import normalize_text
from foobnix.fc.fc import FC
from foobnix.fc.fc_cache import FCache

def update_parent_for_beans(beans, parent):
    for bean in beans:
        bean.parent(parent).add_is_file(True)


"""update bean info form text if possible"""
def update_bean_from_normalized_text(bean):

    if not bean.artist or not bean.title:
        bean.text = normalize_text(bean.text)

        text_artist = bean.get_artist_from_text()
        text_title = bean.get_title_from_text()

        if text_artist and text_title:
            bean.artist, bean.title = text_artist, text_title
    return bean


def get_bean_posible_paths(bean):
    logging.debug("get bean path: %s" % bean)
    path = get_bean_download_path(bean, path=FC().online_save_to_folder)
    if path and os.path.exists(path):
        return path

    for paths in FCache().music_paths:
        for path in paths:
            path = get_bean_download_path(bean, path)
            if path and os.path.exists(path):
                return path

    return None


def get_bean_download_path(bean, path=FC().online_save_to_folder, nosubfolder = FC().nosubfolder):

    ext = ".mp3"
    if nosubfolder:
        name = bean.get_display_name()
        name = name.replace("/", "-")
        name = name.replace("\\", "-")
        path = os.path.join(path, name + ext)
        return path
    elif bean.artist:
        bean.artist = bean.artist.replace("/", "-")
        bean.artist = bean.artist.replace("\\", "-")
        path = os.path.join(path, bean.artist, bean.get_display_name() + ext)
        logging.debug("bean path %s" % path)
        return path
    else:
        logging.debug("get bean path: %s" % bean)
        path = os.path.join(path, bean.get_display_name() + ext)
        logging.debug("bean path %s" % path)
        return path


def get_bean_from_file(f):
    if not os.path.exists(f):
        logging.debug("not exists" + str(f))
        return None
    bean = FDModel(text=os.path.basename(f), path=f)
    is_file = True if os.path.isfile(f) else False
    bean = bean.add_is_file(is_file)
    if not is_file:
        bean.add_font("bold")
    return bean

########NEW FILE########
__FILENAME__ = const
#-*- coding: utf-8 -*-
'''
Created on 30 авг. 2010

@author: ivan
'''
from foobnix.util.localization import foobnix_localization
import locale
from gi.repository import Gtk

foobnix_localization()

SITE_LOCALE = "en"
if locale.getdefaultlocale()[0] and ("ru" in locale.getdefaultlocale()[0]):
    SITE_LOCALE = "ru"

ORDER_LINEAR = "ORDER_LINEAR"
ORDER_SHUFFLE = "ORDER_SHUFFLE"
ORDER_RANDOM = "ORDER_RANDOM"

REPEAT_ALL = "REPEAT_ALL"
REPEAT_SINGLE = "REPEAT_SINGLE"
REPEAT_NO = "REPEAT_NO"


ON_CLOSE_CLOSE = "ON_CLOSE_CLOSE"
ON_CLOSE_HIDE = "ON_CLOSE_HIDE"
ON_CLOSE_MINIMIZE = "ON_CLOSE_MINIMIZE"

PLAYLIST_PLAIN = "PLAYLIST_PLAIN"
PLAYLIST_TREE = "PLAYLIST_TREE"

EQUALIZER_LABLES = ["PREAMP", "29", "59", "119", "237", "474", "1K", "2K", "4K", "8K", "15K"]


STATE_STOP = "STOP"
STATE_PLAY = "PLAY"
STATE_PAUSE = "PAUSE"

FTYPE_NOT_UPDATE_INFO_PANEL = "FTYPE_NOT_UPDATE_INFO_PANEL"

FTYPE_RADIO = "FTYPE_RADIO"

DOWNLOAD_STATUS_ALL = _("All")
DOWNLOAD_STATUS_ACTIVE = _("Active")
DOWNLOAD_STATUS_STOP = _("Stop")
DOWNLOAD_STATUS_DOWNLOADING = _("Downloading")
DOWNLOAD_STATUS_COMPLETED = _("Complete")
DOWNLOAD_STATUS_INACTIVE = _("Inactive")

DOWNLOAD_STATUS_LOCK = _("Lock")
DOWNLOAD_STATUS_ERROR = _("Error")

ICON_FOOBNIX = "images/foobnix.png"

ICON_FOOBNIX_PLAY = "images/foobnix-play.png"
ICON_FOOBNIX_PAUSE = "images/foobnix-pause.png"
ICON_FOOBNIX_STOP = "images/foobnix-stop.png"
ICON_FOOBNIX_RADIO = "images/foobnix-radio.jpg"
ICON_BLANK_DISK = "images/foobnix-blank-disc.jpg"

BEFORE = Gtk.TreeViewDropPosition.BEFORE
AFTER = Gtk.TreeViewDropPosition.AFTER
INTO_OR_BEFORE = Gtk.TreeViewDropPosition.INTO_OR_BEFORE
INTO_OR_AFTER = Gtk.TreeViewDropPosition.INTO_OR_AFTER
########NEW FILE########
__FILENAME__ = converter
#-*- coding: utf-8 -*-
'''
Created on Jan 25, 2011

@author: zavlab1
'''

from __future__ import with_statement

import os
import re
import thread
import logging

from gi.repository import Gtk
from gi.repository import GLib
from subprocess import Popen, PIPE

from foobnix.fc.fc_helper import CONFIG_DIR
from foobnix.util.const import ICON_FOOBNIX
from foobnix.util.file_utils import open_in_filemanager
from foobnix.util.localization import foobnix_localization
from foobnix.helpers.textarea import ScrolledText
from foobnix.helpers.window import ChildTopWindow
from foobnix.gui.service.path_service import get_foobnix_resourse_path_by_name

foobnix_localization()

LOGO = get_foobnix_resourse_path_by_name(ICON_FOOBNIX)
FFMPEG_NAME = "ffmpeg_foobnix"
#fix win
if os.name == 'posix':
    if os.uname()[4] == 'x86_64':
        FFMPEG_NAME += "_x64"

class Converter(ChildTopWindow):
    def __init__(self):
        ChildTopWindow.__init__(self, title="Audio Converter", width=500, height=400)

        self.area = ScrolledText()
        vbox = Gtk.VBox(False, 10)
        vbox.pack_start(self.area.scroll)
        vbox.show()
        format_label = Gtk.Label(_('Format'))
        bitrate_label = Gtk.Label(_('Bitrate'))
        channels_label = Gtk.Label(_('Channels'))
        hertz_label = Gtk.Label(_('Frequency'))

        format_box = Gtk.VBox()
        bitrate_box = Gtk.VBox()
        channels_box = Gtk.VBox()
        hertz_box = Gtk.VBox()

        self.format_list = ["Choose", "  mp3", "  ogg", "  mp2", "  ac3", "  m4a", "  wav"]
        self.bitrate_list = ["  64 kbps", "  96 kbps", "  128 kbps", "  160 kbps", "  192 kbps", "  224 kbps", "  256 kbps", "  320 kbps", "  384 kbps", "  448 kbps", "  640 kbps"]
        self.channels_list = ["  1", "  2", "  6"]
        self.hertz_list = ["  22050 Hz", "  44100 Hz", "  48000 Hz", "  96000 Hz"]

        self.format_combo = combobox_constr(self.format_list)
        self.format_combo.connect("changed", self.on_change_format)

        self.bitrate_combo = combobox_constr()
        self.channels_combo = combobox_constr()
        self.hertz_combo = combobox_constr()

        format_box.pack_start(format_label, False, False, 0)
        format_box.pack_start(self.format_combo, False, False, 0)
        bitrate_box.pack_start(bitrate_label, False, False, 0)
        bitrate_box.pack_start(self.bitrate_combo, False, False, 0)
        channels_box.pack_start(channels_label, False, False, 0)
        channels_box.pack_start(self.channels_combo, False, False, 0)
        hertz_box.pack_start(hertz_label, False, False, 0)
        hertz_box.pack_start(self.hertz_combo, False, False, 0)

        hbox = Gtk.HBox(False, 30)
        hbox.pack_start(format_box, False, False, 0)
        hbox.pack_start(bitrate_box, False, False, 0)
        hbox.pack_start(channels_box, False, False, 0)
        hbox.pack_start(hertz_box, False, False, 0)
        hbox.set_border_width(10)
        hbox.show_all()

        vbox.pack_start(hbox, False)

        self.button_box = Gtk.HBox(False, 10)
        close_button = Gtk.Button(_("Close"))
        close_button.set_size_request(150, 30)
        close_button.connect("clicked", lambda *a: self.hide())
        self.convert_button = Gtk.Button(_("Convert"))
        self.convert_button.set_size_request(150, 30)
        self.convert_button.connect("clicked", self.save)

        self.progressbar = Gtk.ProgressBar()

        self.stop_button = Gtk.Button(_("Stop"))
        self.stop_button.set_size_request(100, 30)
        self.stop_button.connect("clicked", self.on_stop)

        self.open_folder_button = Gtk.Button(_("Show files"))
        self.open_folder_button.connect('released', self.open_in_fm)

        self.progress_box = Gtk.HBox()
        self.progress_box.pack_end(self.open_folder_button, False)
        self.progress_box.pack_end(self.stop_button, False)
        self.progress_box.pack_end(self.progressbar, True)

        self.output = ScrolledText()
        self.output.text.set_size_request(-1, 50)
        self.output.scroll.set_size_request(-1, 50)
        self.output.scroll.set_placement(Gtk.CornerType.BOTTOM_LEFT)
        vbox.pack_start(self.progress_box, False)

        self.button_box.pack_end(self.convert_button, False)
        self.button_box.pack_end(close_button, False)

        self.button_box.show_all()

        vbox.pack_start(self.button_box, False)
        vbox.pack_start(self.output.scroll, False)
        self.add(vbox)

    def save(self, *a):
        chooser = Gtk.FileChooserDialog(title=_("Choose directory to save converted files"),
                                        action=Gtk.FileChooserAction.SELECT_FOLDER,
                                        buttons=(Gtk.STOCK_SAVE, Gtk.ResponseType.OK))
        chooser.set_current_folder(os.path.dirname(self.paths[0]))
        chooser.set_icon_from_file(LOGO)
        response = chooser.run()

        if response == Gtk.ResponseType.OK:
            format = self.format_combo.get_active_text().strip()
            self.current_folder = chooser.get_current_folder()

            for path in self.paths:
                if (os.path.splitext(os.path.basename(path))[0] + '.' + format) in os.listdir(self.current_folder):
                    if not self.warning():
                        chooser.destroy()
                        return
                    else:
                        break
            self.stop = False
            self.button_box.hide_all()
            self.progressbar.set_fraction(0)
            self.progress_box.show_all()
            self.output.scroll.show()

            fraction_length = 1.0 / len(self.paths)
            self.progressbar.set_text("")
            self.output.buffer.delete(self.output.buffer.get_start_iter(), self.output.buffer.get_end_iter())
            def task():
                self.stop_button.show()
                self.open_folder_button.hide()
                for i, path in enumerate(self.paths):
                    self.progressbar.set_text("Convert  %d of %d file(s)" % (i+1, len(self.paths)))
                    self.convert(path, os.path.join(self.current_folder, os.path.splitext(os.path.basename(path))[0] + "." + format), format)
                    self.progressbar.set_fraction(self.progressbar.get_fraction() + fraction_length)
                    if self.stop:
                        self.open_folder_button.show()
                        self.progressbar.set_text("Stopped . Converted %d of %d file(s)" % (i, len(self.paths)))
                        break
                    else:
                        self.progressbar.set_text("Finished (%d of %d)" % (i+1, len(self.paths)))
                self.stop_button.hide()
                self.open_folder_button.show()
                self.button_box.show_all()
            thread.start_new_thread(task, ())
        chooser.destroy()

    def convert(self, path, new_path, format):
        bitrate_text = self.bitrate_combo.get_active_text()
        if bitrate_text:
            bitrate = re.search('^([0-9]{1,5})', bitrate_text.strip()).group() + 'k'
        else:
            bitrate = ""
        channels_text = self.channels_combo.get_active_text()
        channels = re.search('^([0-9]{1,5})', channels_text.strip()).group()
        hertz_text = self.hertz_combo.get_active_text()
        samp_rate = re.search('^([0-9]{1,5})', hertz_text.strip()).group()

        if format == "mp3":
            acodec = "libmp3lame"
        elif format == "ogg":
            acodec = "libvorbis"
        elif format == "mp2":
            acodec = "mp2"
        elif format == "ac3":
            acodec = "ac3"
        elif format == "m4a":
            acodec = "libfaac"
        elif format == "wav":
            acodec = "pcm_s16le"
        else:
            logging.error('Unsupported format')
            return

        list = [os.path.join(CONFIG_DIR, FFMPEG_NAME), "-i", path, "-acodec", acodec, "-ac", channels, "-ab", bitrate, "-ar", samp_rate, '-y', new_path]

        if format == "wav":
            list.remove("-ab")
            list.remove(bitrate)

        logging.debug(" ".join(list))

        self.ffmpeg = Popen(list, universal_newlines=True, stderr=PIPE)

        for line in iter(self.ffmpeg.stderr.readline, ""):
            GLib.idle_add(self.output.buffer.insert_at_cursor, line)
            logging.debug(line)
            adj = self.output.scroll.get_vadjustment()
            GLib.idle_add(adj.set_value, adj.get_upper() - adj.get_page_size() + 1)

        self.ffmpeg.wait()

    def on_stop(self, *a):
        self.ffmpeg.terminate()
        self.stop = True
        #self.open_folder_button.show()

    def fill_form(self, paths):
        self.paths = []
        self.area.buffer.delete(self.area.buffer.get_start_iter(), self.area.buffer.get_end_iter())
        for path in paths:
            if os.path.isfile(path):
                self.paths.append(path)
                self.area.buffer.insert_at_cursor(os.path.basename(path) + "\n")

    def warning(self):
        dialog = Gtk.Dialog(_("Warning!!!"))
        ok_button = dialog.add_button(Gtk.STOCK_OK, Gtk.ResponseType.OK) #@UnusedVariable
        cancel_button = dialog.add_button(Gtk.STOCK_CANCEL, Gtk.ResponseType.CANCEL)
        cancel_button.grab_default()
        label = Gtk.Label(_("So file(s)  already exist(s) and will be overwritten.\nDo you wish to continue?"))
        image = Gtk.Image.new_from_stock(Gtk.STOCK_DIALOG_WARNING, Gtk.IconSize.LARGE_TOOLBAR)
        hbox = Gtk.HBox(False, 10)
        hbox.pack_start(image)
        hbox.pack_start(label)
        dialog.vbox.pack_start(hbox)
        dialog.set_icon_from_file(LOGO)
        dialog.set_default_size(210, 100)
        dialog.show_all()
        if dialog.run() == Gtk.ResponseType.OK:
            dialog.destroy()
            return True
        else:
            dialog.destroy()
            return False

    def remake_combos(self, bitrate_list, channels_list, hertz_list):
        self.clear_combos(self.bitrate_combo, self.channels_combo, self.hertz_combo)
        for b in bitrate_list:
            self.bitrate_combo.append_text(b)
        for c in channels_list:
            self.channels_combo.append_text(c)
        for h in hertz_list:
            self.hertz_combo.append_text(h)

    def clear_combos(self, *combo_list):
        if not combo_list:
            return
        for combo in combo_list:
            combo.remove_all()
            #for i in self.bitrate_list: #the longest list
            #    combo.remove()

    def on_change_format(self, a):
        bitrate_list = self.bitrate_list[:]
        channels_list = self.channels_list[:]
        hertz_list = self.hertz_list[:]

        bitrate_index = 6
        channels_index = 1
        hertz_index = 2

        if self.format_combo.get_active_text() == "  mp3":
            bitrate_list.remove("  640 kbps")
            bitrate_list.remove("  448 kbps")
            bitrate_list.remove("  384 kbps")
            channels_list.remove("  6")
            hertz_list.remove("  96000 Hz")
            hertz_index = 1
        elif self.format_combo.get_active_text() == "  mp2":
            bitrate_list.remove("  640 kbps")
            bitrate_list.remove("  448 kbps")
            hertz_list.remove("  96000 Hz")
            hertz_list.remove("  44100 Hz")
            hertz_list.remove("  22050 Hz")
            hertz_index = 0
        elif self.format_combo.get_active_text() == "  ac3":
            hertz_list.remove("  96000 Hz")
        elif self.format_combo.get_active_text() == "  m4a":
            bitrate_list.remove("  640 kbps")

        self.remake_combos(bitrate_list, channels_list, hertz_list)

        self.bitrate_combo.set_active(bitrate_index)
        self.channels_combo.set_active(channels_index)
        self.hertz_combo.set_active(hertz_index)

        if self.format_combo.get_active() == 0:
            self.clear_combos(self.bitrate_combo, self.channels_combo, self.hertz_combo)
            self.convert_button.set_sensitive(False)
            self.bitrate_combo.set_sensitive(False)
            self.channels_combo.set_sensitive(False)
            self.hertz_combo.set_sensitive(False)
        else:
            self.convert_button.set_sensitive(True)

        if self.format_combo.get_active_text() == "  wav":
            self.clear_combos(self.bitrate_combo)
            self.bitrate_combo.set_sensitive(False)
        else:
            self.bitrate_combo.set_sensitive(True)
            self.channels_combo.set_sensitive(True)
            self.hertz_combo.set_sensitive(True)

    def open_in_fm(self, *a):
        open_in_filemanager(self.current_folder)

def combobox_constr(list=None):
    combobox = Gtk.ComboBoxText()
    if not list:
        return combobox

    for item in list:
        combobox.append_text(item)

    return combobox

def convert_files(paths):
    if FFMPEG_NAME in os.listdir(CONFIG_DIR):
        if not globals().has_key("converter"):
            global converter
            converter = Converter()
        converter.show_all()
        converter.progress_box.hide_all()
        converter.output.scroll.hide()
        converter.fill_form(paths)
        converter.format_combo.set_active(0)
    else:
        url = "http://foobnix.googlecode.com/files/" + FFMPEG_NAME
        dialog = Gtk.Dialog(_("Attention"))
        area = ScrolledText()
        area.buffer.set_text(_("Converter require specially compiled ffmpeg module for work.\n" +
                               "You should download it automatically (click Download)\n"+
                               "Also check if you have packages libmp3lame0 and libfaac0"))
        ok_button = dialog.add_button(_("Download"), Gtk.ResponseType.OK)

        cancel_button = dialog.add_button(Gtk.STOCK_CANCEL, Gtk.ResponseType.CANCEL)
        ok_button.grab_default()
        prog_bar = Gtk.ProgressBar()
        dialog.vbox.pack_start(area.scroll)
        dialog.vbox.pack_start(prog_bar, False)
        dialog.set_icon_from_file(LOGO)
        dialog.set_default_size(400, 150)
        dialog.show_all()
        prog_bar.hide()
        canceled = False
        if dialog.run() == Gtk.ResponseType.OK:
            prog_bar.show()
            import urllib2
            remote_file = urllib2.urlopen(url)
            size = float(remote_file.info()['Content-Length'])
            ffmpeg_path = os.path.join(CONFIG_DIR, FFMPEG_NAME)

            def on_close(*a):
                if os.path.isfile(ffmpeg_path) and os.path.getsize(ffmpeg_path) < size:
                    os.remove(ffmpeg_path)
                dialog.destroy()
                return
            cancel_button.connect("released", on_close)

            def task():
                with open(ffmpeg_path, 'wb') as local_file:
                    got = 0
                    cycle = True
                    while cycle and not canceled:
                        try:
                            local_file.write(remote_file.read(20000))
                            if got + 20000 >= size:
                                cycle = False
                            got = os.path.getsize(ffmpeg_path)

                            def subtask():
                                prog_bar.set_fraction(got/size)
                                prog_bar.set_text("Downloaded  %.2f of %.2fMb" % (float(got)/1024/1024, size/1024/1024))

                            GLib.idle_add(subtask)
                        except OSError as e:
                            if os.path.isfile(ffmpeg_path) and os.path.getsize(ffmpeg_path) < size:
                                os.remove(ffmpeg_path)

                os.chmod(ffmpeg_path, 0777)
                GLib.idle_add(convert_files, paths)
                dialog.destroy()

            thread.start_new_thread(task, ())
        else:
            dialog.destroy()

########NEW FILE########
__FILENAME__ = file_utils
'''
Created on Feb 26, 2010

@author: ivan
'''

import os
from gi.repository import Gtk
import sys
import urllib
import shutil
import thread
import logging
import threading

from subprocess import Popen
from foobnix.fc.fc import FC
from foobnix.util.const import ICON_FOOBNIX
from foobnix.helpers.textarea import ScrolledText
from foobnix.gui.service.path_service import get_foobnix_resourse_path_by_name
from foobnix.helpers.dialog_entry import directory_chooser_dialog
import subprocess


def open_in_filemanager(path, managers=None):
    dirname = path if os.path.isdir(path) else os.path.dirname(path)
    if sys.platform.startswith('darwin'):
        subprocess.call(('open', dirname))
    elif os.name == 'nt':
        os.startfile(dirname)
    elif os.name == 'posix':
        subprocess.call(('xdg-open', dirname))

def get_files_from_folder(folder):
    return [file for file in os.listdir(folder) if not os.path.isdir(file)]

def rename_file_on_disk(row, index_path, index_text):
    path = row[index_path]
    name = os.path.basename(path)
    entry = Gtk.Entry()
    entry.set_width_chars(64)
    hbox = Gtk.HBox()
    if os.path.isdir(path):
        entry.set_text(name)
        hbox.pack_start(entry)
        title = _('Rename folder')
    else:
        name_tuple = os.path.splitext(name)
        entry.set_text(name_tuple[0])
        entry_ext = Gtk.Entry()
        entry_ext.set_width_chars(7)
        entry_ext.set_text(name_tuple[1][1:])
        hbox.pack_start(entry)
        hbox.pack_start(entry_ext)
        title = _('Rename file')
    dialog = Gtk.Dialog(title, buttons=("Rename", Gtk.ResponseType.ACCEPT, "Cancel", Gtk.ResponseType.REJECT))
    dialog.vbox.pack_start(hbox)
    dialog.set_icon_from_file(get_foobnix_resourse_path_by_name(ICON_FOOBNIX))
    dialog.show_all()
    if dialog.run() == Gtk.ResponseType.ACCEPT:
        if os.path.isdir(path) or not entry_ext.get_text():
            new_path = os.path.join(os.path.dirname(path), entry.get_text())
        else:
            new_path = os.path.join(os.path.dirname(path), entry.get_text() + '.' + entry_ext.get_text())
        try:
            os.rename(path, new_path)
            row[index_path] = new_path
            row[index_text] = os.path.basename(new_path)
        except IOError, e:
            logging.error(e)
        dialog.destroy()
        return True
    dialog.destroy()

def delete_files_from_disk(row_refs, paths, get_iter_from_row_reference):
    title = _('Delete file(s) / folder(s)')
    label = Gtk.Label(_('Do you really want to delete item(s) from disk?'))
    dialog = Gtk.Dialog(title, buttons=("Delete", Gtk.ResponseType.ACCEPT, "Cancel", Gtk.ResponseType.REJECT))
    dialog.set_default_size(500, 200)
    dialog.set_border_width(5)
    dialog.vbox.pack_start(label)
    dialog.set_icon_from_file(get_foobnix_resourse_path_by_name(ICON_FOOBNIX))
    buffer = Gtk.TextBuffer()
    text = Gtk.TextView(buffer=buffer)
    text.set_editable(False)
    text.set_cursor_visible(False)
    scrolled_window = Gtk.ScrolledWindow()
    scrolled_window.set_policy(Gtk.PolicyType.AUTOMATIC, Gtk.PolicyType.AUTOMATIC)
    scrolled_window.add(text)
    dialog.vbox.pack_start(scrolled_window)
    for path in paths:
        name = os.path.basename(path)
        buffer.insert_at_cursor('\t' + name + '\n')

    dialog.show_all()
    if dialog.run() == Gtk.ResponseType.ACCEPT:
        model = row_refs[0].get_model()

        for row_ref, path in zip(row_refs, paths):
            try:
                if os.path.isfile(path):
                    os.remove(path)
                else:
                    del_dir(path)
                model.remove(get_iter_from_row_reference(row_ref))
            except Exception, e:
                logging.error(str(e))
                continue
        dialog.destroy()
        return True
    dialog.destroy()

def del_dir(path):
        list = os.listdir(path)
        if not list: return
        for item in list:
            item_abs = os.path.join(path, item)
            if os.path.isfile(item_abs):
                os.remove(item_abs)
            else:
                del_dir(item_abs)
        os.rmdir(path)

def copy_move_files_dialog(files, dest_folder, copy=None):
    if copy == Gdk.DragAction.COPY: action = _("Copy") #@UndefinedVariable
    else: action = _("Replace")

    dialog = Gtk.Dialog(_('%s file(s) / folder(s)') % action)

    ok_button = dialog.add_button(action, Gtk.ResponseType.OK)
    cancel_button = dialog.add_button(Gtk.STOCK_CANCEL, Gtk.ResponseType.CANCEL) #@UnusedVariable

    ok_button.grab_default()
    label = Gtk.Label('\n' + _("Are you really want to %s this item(s) to %s ?") % (action, dest_folder))
    area = ScrolledText()
    area.text.set_editable(False)
    area.text.set_cursor_visible(False)
    area.buffer.set_text("\n".join([os.path.basename(path) for path in files]))
    dialog.vbox.pack_start(area.scroll)
    dialog.set_border_width(5)
    dialog.vbox.pack_start(label)
    dialog.set_icon_from_file(get_foobnix_resourse_path_by_name(ICON_FOOBNIX))
    dialog.set_default_size(400, 150)
    dialog.show_all()
    if dialog.run() == Gtk.ResponseType.OK:
        dialog.destroy()
        return True
    dialog.destroy()
    return False

def create_folder_dialog(path):
    dirname = path if os.path.isdir(path) else os.path.dirname(path)
    dialog = Gtk.Dialog(_("Make folder dialog"))
    ok_button = dialog.add_button(_("Create folder"), Gtk.ResponseType.OK)
    label1 = Gtk.Label(_("You want to create subfolder in folder") + " " + os.path.basename(dirname))
    label2 = Gtk.Label(_("Enter new folder's name:"))
    entry = Gtk.Entry()
    dialog.set_border_width(5)
    dialog.vbox.pack_start(label1)
    dialog.vbox.pack_start(label2)
    dialog.vbox.pack_start(entry)
    dialog.show_all()
    ok_button.grab_default()
    def task():
        if dialog.run() == Gtk.ResponseType.OK:
            folder_name = entry.get_text()
            if folder_name:
                full_path = os.path.join(dirname, folder_name)
                try:
                    os.mkdir(full_path)
                except OSError, e:
                    logging.error(e)
                    if str(e).startswith("[Errno 17]"):
                        er_message = _("So folder already exists")
                    else:
                        er_message = str(e)
                    warning = Gtk.MessageDialog(parent=dialog, flags=Gtk.DialogFlags.DESTROY_WITH_PARENT, type=Gtk.MessageType.ERROR, message_format=er_message)
                    if warning.run() == Gtk.ResponseType.DELETE_EVENT:
                        warning.destroy()
                    full_path = task()
                return full_path
    full_path = task()
    dialog.destroy()
    return full_path

def isDirectory(path):
    return os.path.isdir(path)

"""extentsion like .mp3, .mp4"""
def get_file_extension(fileName):
    if not fileName:
        return None

    if fileName.startswith("http"):
        return None

    return os.path.splitext(fileName)[1].lower().strip()

def file_extension(file_name):
    return get_file_extension(file_name)


def get_any_supported_audio_file(full_file):
    exists = os.path.exists(full_file)
    if exists:
        return  full_file

    """try to find other source"""
    ext = get_file_extension(full_file)
    nor = full_file[:-len(ext)]
    logging.info("Normalized path" + nor)

    for support_ext in FC().audio_formats:
        try_name = nor + support_ext
        if os.path.exists(try_name):
            return try_name

    return None


def get_file_path_from_dnd_dropped_uri(uri):
    path = ""
    if uri.startswith('file:\\\\\\'):   # windows
        path = uri[8:]  # 8 is len('file:///')
    elif uri.startswith('file://'):     # nautilus, rox
        path = uri[7:]  # 7 is len('file://')
    elif uri.startswith('file:'):   # xffm
        path = uri[5:]  # 5 is len('file:')
    path = urllib.url2pathname(path)    # escape special chars
    path = path.strip('\r\n\x00')   # remove \r\n and NULL

    return path


def get_files_from_gtk_selection_data(selection):
    if not selection or selection.get_format() != 8 or selection.get_length() <= 0:
        return []
    files = selection.get_text().split("\n")
    files = [k.strip("\r") for k in files if k.strip() != ""]
    return [get_file_path_from_dnd_dropped_uri(k) for k in files]


def get_dir_size(dirpath):
    folder_size = 0
    for (path, dirs, files) in os.walk(dirpath): #@UnusedVariable
        for file in files:
            filename = os.path.join(path, file)
            folder_size += os.path.getsize(filename)
    return folder_size

def get_full_size(path_list):
    size = 0
    for path in path_list:
        if os.path.exists(path):
            if os.path.isdir(path):
                size += get_dir_size(path)
            else:
                size += os.path.getsize(path)
    return size

def copy_move_with_progressbar(pr_window, src, dst_folder, move=False, symlinks=False, ignore=None):
    '''changed shutil.copytree(src, dst, symlinks, ignore)'''
    if sys.version_info < (2, 6):
        logging.warning("your python version is too old")
        return
    else:
        from multiprocessing import Process
    def copy_move_one_file(src, dst_folder):

        m = Process(target=func, args=(src, dst_folder))
        m.start()
        def task():
            try:
                name_begin = pr_window.label_from.get_text().split()[0]
                pr_window.label_from.set_text(name_begin + " " + os.path.basename(src) + "\n")
                pr_window.progress(src, dst_folder)
            except threading.ThreadError:
                m.terminate()
                os.remove(os.path.join(dst_folder, os.path.basename(src)))
        thread.start_new_thread(task, ())
        if m.is_alive():
            m.join()
        return

    func = shutil.move if move else shutil.copy2
    if os.path.isfile(src):
        copy_move_one_file(src, dst_folder)
        return
    """Recursively copy a directory tree using copy2().

    The destination directory must not already exist.
    If exception(s) occur, an Error is raised with a list of reasons.

    If the optional symlinks flag is true, symbolic links in the
    source tree result in symbolic links in the destination tree; if
    it is false, the contents of the files pointed to by symbolic
    links are copied.

    The optional ignore argument is a callable. If given, it
    is called with the `src` parameter, which is the directory
    being visited by copytree(), and `names` which is the list of
    `src` contents, as returned by os.listdir():

        callable(src, names) -> ignored_names

    Since copytree() is called recursively, the callable will be
    called once for each directory that is copied. It returns a
    list of names relative to the `src` directory that should
    not be copied.

    XXX Consider this example code rather than the ultimate tool.

    """
    try:
        names = os.listdir(src)
    except OSError, why:
        logging.error(why)
    if ignore is not None:
        ignored_names = ignore(src, names)
    else:
        ignored_names = set()

    if not os.path.exists(dst_folder):
        os.makedirs(dst_folder)
    subfolder = os.path.join(dst_folder, os.path.basename(src))
    if not os.path.exists(subfolder):
        os.makedirs(subfolder)
    errors = []
    for name in names:
        if name in ignored_names:
            continue
        srcname = os.path.join(src, name)
        dstname = os.path.join(subfolder, name)
        try:
            if symlinks and os.path.islink(srcname):
                linkto = os.readlink(srcname)
                os.symlink(linkto, dstname)
            elif os.path.isdir(srcname):
                copy_move_with_progressbar(pr_window, srcname, subfolder, move, symlinks, ignore)
            else:
                copy_move_one_file(srcname, subfolder)

                # XXX What about devices, sockets etc.?
        except (IOError, os.error), why:
            errors.append((srcname, dstname, str(why)))
        # catch the Error from the recursive copytree so that we can
        # continue with other files
    if move:
        os.rmdir(src)
    else:
        try:
            shutil.copystat(src, dst_folder)
        except OSError, why:
            errors.extend((src, dst_folder, str(why)))

def copy_to(old_paths):
        destinations = directory_chooser_dialog(_("Choose Folder"), FC().last_dir)
        if not destinations:
            return
        from foobnix.helpers.window import CopyProgressWindow
        pr_window = CopyProgressWindow(_("Progress"), old_paths, 300, 100)
        pr_window.label_to.set_text(_("To: ") + destinations[0] + "\n")
        if destinations:
            for old_path in old_paths:
                if not os.path.exists(old_path):
                    logging.warning("File " + old_path + " not exists")
                    continue
                pr_window.label_from.set_text(_("Copying: ") + os.path.dirname(old_path))
                def task():
                    copy_move_with_progressbar(pr_window, old_path, destinations[0])
                    pr_window.response(Gtk.ResponseType.OK)
                t = threading.Thread(target=task)
                t.start()
                if pr_window.run() == Gtk.ResponseType.REJECT:
                    pr_window.exit = True
                    t.join()
        pr_window.destroy()

def is_playlist(path=''):
    return True if get_file_extension(path) in ['.m3u', '.m3u8', '.pls'] else False

def is_m3u(path=''):
    return True if get_file_extension(path) in ['.m3u', '.m3u8'] else False

def is_cue(path=''):
    return True if get_file_extension(path) == '.cue' else False
########NEW FILE########
__FILENAME__ = id3_file
from foobnix.util.id3_util import get_support_music_beans_from_all,\
    update_id3_for_beans, add_update_image_paths
from foobnix.playlists.cue_reader import update_id3_for_cue
from foobnix.playlists.m3u_reader import update_id3_for_m3u

def update_id3_wind_filtering(beans):
    beans = update_id3_for_m3u(beans)
    beans = get_support_music_beans_from_all(beans)
    beans = update_id3_for_beans(beans)
    beans = update_id3_for_cue(beans)
    beans = add_update_image_paths(beans)
    result = []
    for bean in beans:
        result.append(bean)
    return result
########NEW FILE########
__FILENAME__ = id3_util
#-*- coding: utf-8 -*-
'''
Created on 24 нояб. 2010

@author: ivan
'''
from _bsddb import api
import os
import logging
import urllib

from gi.repository.GdkPixbuf import Pixbuf

from zlib import crc32
from subprocess import Popen, PIPE
from tempfile import NamedTemporaryFile
from foobnix.fc.fc import FC, FCache
from foobnix.fc.fc_cache import COVERS_DIR
from foobnix.util.image_util import get_image_by_path
from foobnix.util.time_utils import convert_seconds_to_text
from foobnix.util.bean_utils import update_bean_from_normalized_text
from foobnix.util.file_utils import file_extension, get_file_extension
from foobnix.util.audio import get_mutagen_audio
from mutagen.id3 import ID3
from mutagen.flac import FLAC
from mutagen.mp4 import MP4

RUS_ALPHABITE = "абвгдеёжзийклмнопрстуфхцчшщъыьэюя"


def correct_encoding(text):
    try:
        text = text.encode('cp1252').decode('cp1251')
    except:
        pass
    return text


def update_id3_for_beans(beans):
    for bean in beans:
        if get_file_extension(bean.text) in FC().audio_formats:
            try:
                update_id3(bean)
            except Exception, e:
                logging.warn("update id3 error - % s" % e)
        if bean.text:
            if (bean.text[0] == "/") or (len(bean.text)>1 and bean.text[1] == ":"):
                bean.text = os.path.basename(bean.text)
    return beans


def update_id3(bean):
    if bean and bean.path and os.path.isfile(bean.path):
        try:
            audio = get_mutagen_audio(bean.path)
        except Exception, e:
            logging.warn("ID3 NOT FOUND IN " + str(e) + " " + bean.path)
            return bean
        if audio:
            if isinstance(audio, MP4):
                if audio.has_key('\xa9ART'): bean.artist = audio["\xa9ART"][0]
                if audio.has_key('\xa9nam'): bean.title = audio["\xa9nam"][0]
                if audio.has_key('\xa9alb'): bean.album = audio["\xa9alb"][0]
                if audio.has_key('\xa9wrt'): bean.composer = audio["\xa9wrt"][0]
                if audio.has_key('trkn'):
                    #if not FC().numbering_by_order:
                    bean.tracknumber = audio['trkn'][0]
            else:
                if audio.has_key('artist'): bean.artist = correct_encoding(audio["artist"][0])
                if audio.has_key('title'): bean.title = correct_encoding(audio["title"][0])
                if audio.has_key('album'): bean.album = correct_encoding(audio["album"][0])
                if audio.has_key('composer'): bean.composer = correct_encoding(audio['composer'][0])
                if audio.has_key('cuesheet'): bean.cue = audio['cuesheet'][0] # correct_encoding is in cue parser
                if audio.has_key('tracknumber'):
                    #if not FC().numbering_by_order:
                    bean.tracknumber = audio["tracknumber"][0]

        duration_sec = bean.duration_sec

        if not bean.duration_sec and audio.info.length:
            duration_sec = int(audio.info.length)

        if audio.info.__dict__:
            bean.info = normalized_info(audio.info, bean)

        if bean.artist or bean.title:
            if bean.artist and bean.title:
                pass
            elif bean.artist:
                bean.title = _("Unknown title")
            elif bean.title:
                bean.artist = _("Unknown artist")
            bean.text = bean.artist + " - " + bean.title
        '''
        if bean.tracknumber:
            try:
                bean.tracknumber = int(bean.tracknumber)
            except:
                bean.tracknumber = ""
        '''
        bean = update_bean_from_normalized_text(bean)
        bean.time = convert_seconds_to_text(duration_sec)

    return bean


def normalized_info(info, bean):
    list = info.pprint().split(", ")
    new_list = []
    bean.size = os.path.getsize(bean.path)
    new_list.append(list[0])
    if info.__dict__.has_key('channels'):
        new_list.append('Ch: ' + str(info.channels))
    if info.__dict__.has_key('bits_per_sample'):
        new_list.append(str(info.bits_per_sample) + ' bit')
    if info.__dict__.has_key('sample_rate'):
        new_list.append(str(info.sample_rate) + 'Hz')
    if info.__dict__.has_key('bitrate'):
        new_list.append(str(info.bitrate / 1000) + ' kbps')
    else:
        kbps = int(round(bean.size * 8 / info.length / 1000))
        new_list.append(str(kbps + 1 if kbps % 2 else kbps) + ' kbps')
    if info.__dict__.has_key('length'):
        new_list.append(convert_seconds_to_text(int(info.length)))
    size = '%.2f MB' % (float(bean.size) / 1024 / 1024)
    new_list.append(size)
    return " | ".join(new_list)


def get_support_music_beans_from_all(beans):
    result = []
    for bean in beans:
        if bean.path and os.path.isdir(bean.path):
            result.append(bean)
        elif bean.path and os.path.isfile(bean.path) and file_extension(bean.path) in FC().audio_formats:
            result.append(bean)
        elif bean.path and bean.path.startswith("http://"):
            result.append(bean)
        else:
            result.append(bean)

    return result


def add_update_image_paths(beans):
    for bean in beans:
        if bean.path and bean.is_file:
            set_cover_from_tags(bean)
            if not bean.image:
                bean.image = get_image_by_path(bean.path)
    return beans


def _get_extension_by_mime(mime):
    if mime == "image/jpeg" or mime == "image/jpg":
        return ".jpg"
    elif mime == "image/png":
        return ".png"
    logging.warning("Unknown cover mime-type: %s" % mime)
    return None


def _get_pic_from_mp3(audio):
    apics = [k for k in audio.keys() if k.startswith("APIC:")]
    if apics:
        return audio[apics[0]]
    return None


def _get_pic_from_flac(audio):
    if audio.pictures:
        return audio.pictures[0]
    return None


def set_cover_from_tags(bean):
    try:
        ext = get_file_extension(bean.path)
        if ext == ".mp3":
            data = _get_pic_from_mp3(ID3(bean.path))
        elif ext == ".flac":
            data = _get_pic_from_flac(FLAC(bean.path))
        else:
            return None
        if data:
            filename = os.path.join(COVERS_DIR, str(crc32(bean.path)) + '.jpg')
            fd = NamedTemporaryFile()
            fd.write(data.data)
            pixbuf = Pixbuf.new_from_file(fd.name)
            pixbuf.savev(filename, "jpeg", ["quality"], ["90"])
            fd.close()
            bean.image = filename
            basename = os.path.splitext(os.path.basename(filename))[0]
            cache_dict = FCache().covers
            if basename in cache_dict:
                cache_dict[basename].append(bean.text)
            else:
                cache_dict[basename] = [bean.text]
            return filename

    except Exception, e:
        pass
    return None


def get_image_for_bean(bean, controls):
    """
    Lookup image for the bean
    :param bean: FModel
    :param controls:
    :return: str
    """
    if bean.image and os.path.exists(bean.image):
        return bean.image
    if bean.path and not bean.path.startswith("http"):
        cover = get_image_by_path(bean.path)
        if cover:
            return cover
        cover = set_cover_from_tags(bean)
        if cover:
            return cover
    image = controls.lastfm_service.get_album_image_url(bean.artist, bean.title)
    if image:
        try:
            ext = image.rpartition(".")[2]
            cache_name = "%s%s.%s" % (COVERS_DIR, crc32(image), ext)
            if os.path.exists(cache_name):
                return cache_name
            urllib.urlretrieve(image, cache_name)
            return cache_name
        except:
            pass
    return None
########NEW FILE########
__FILENAME__ = image_util
#-*- coding: utf-8 -*-
'''
Created on 11 сент. 2010

@author: ivan
'''
import os

from foobnix.util.file_utils import get_file_extension


def get_image_by_path(path):

    dir = path if os.path.isdir(path) else os.path.dirname(path)

    if not os.path.isdir(dir):
        return None

    ext_list = ['.jpg', '.png', '.bmp', '.tiff', '.gif']

    dirs = []
    files = []

    for item in os.listdir(dir):
        if os.path.isdir(os.path.join(dir, item)) and item.lower().startswith("cover"):
            dirs.append(item)
        elif get_file_extension(item) in ext_list:
            files.append(item)

    if not files and not dirs:
        return None

    if files:
        for file in files:
            for name in ("cover", "face", "front", "case"):
                if name in file.lower():
                    return os.path.join(dir, file)
        return os.path.join(dir, files[0])

    if dirs:
        for subdir in dirs:
            image = get_image_by_path(os.path.join(dir, subdir))
            if image:
                return image

########NEW FILE########
__FILENAME__ = iso_util
#-*- coding: utf-8 -*-
'''
Created on 1 дек. 2010

@author: ivan
'''

import os
import logging
import subprocess

from foobnix.gui.service.music_service import get_all_music_with_id3_by_path

def get_beans_from_iso_wv(path):
    if path and path.lower().endswith("iso.wv"):
        mount_path = mount_tmp_iso(path)        
        beans = get_all_music_with_id3_by_path(mount_path, True)
        for bean in beans:
            bean.add_iso_path(path)
        return beans
    
      
def mount_tmp_iso(path):
    name = os.path.basename(path)
    tmp_dir = os.path.join("/tmp", name)
    if os.path.exists(tmp_dir):
        logging.debug("tmp dir to mount already exists" + tmp_dir)
        return tmp_dir
    command = ["fuseiso", "-n", "-p", path, tmp_dir]
    logging.debug("Mount iso.wv %s" % command)
    subprocess.call(command)
    return tmp_dir

########NEW FILE########
__FILENAME__ = key_utils
'''
Created on Oct 21, 2010

@author: ivan
'''

from gi.repository import Gtk
from gi.repository import Gdk

KEY_DELETE = 'Delete'
KEY_RETURN = 'Return'

def is_key(event, key_const):
    const = Gdk.keyval_name(event.keyval) #@UndefinedVariable
    #LOG.debug("KEY", const)
    return const == key_const

def get_key(event):
    const = Gdk.keyval_name(event.keyval) #@UndefinedVariable
    #LOG.debug("KEY", const)    
    return const

def is_key_enter(e):
    return is_key(e, 'Return') or is_key(e, 'KP_Enter')

def is_key_control(event): 
    return event.state & Gdk.ModifierType.CONTROL_MASK   #@UndefinedVariable

def is_key_shift(event): 
    return event.state & Gdk.ModifierType.SHIFT_MASK     #@UndefinedVariable

def is_key_super(event): 
    return event.state & Gdk.ModifierType.SUPER_MASK    #@UndefinedVariable

def is_key_alt(event):
    return event.state & Gdk.ModifierType.MOD1_MASK     # | Gtk.gdk.MOD2_MASK #@UndefinedVariable

def is_modificator(event):
    if is_key_control(event) or is_key_shift(event) or is_key_super(event) or is_key_alt(event):
        return True

########NEW FILE########
__FILENAME__ = list_utils
#-*- coding: utf-8 -*-
'''
Created on Dec 7, 2010

@author: zavlab1
'''
import re

def reorderer_list(List, new_index, old_index):
    if new_index < old_index:
        List.insert(new_index, List[old_index])
        del List[old_index + 1]
    elif old_index < new_index:
        List.insert(new_index + 1, List[old_index])
        del List[old_index]

def any(pred, list):
    for el in list:
        if pred(el):
            return True
    return False

def get_song_number(text):
    res = re.search('^([0-9]{1,4})', text)
    if res:
        return int(res.group())

def comparator(x, y):
    value_x = get_song_number(x)
    value_y = get_song_number(y)
    if value_x and value_y:
        return value_x - value_y
    else:
        return cmp(x, y)

def sort_by_song_name(list):
    list.sort(comparator)
    return list

########NEW FILE########
__FILENAME__ = localization
#-*- coding: utf-8 -*-
'''
Created on 24  2010

@author: ivan
'''
import gettext
import locale
import os

def foobnix_localization():
    APP_NAME = "foobnix"
    gettext.textdomain(APP_NAME)
    gettext.install(APP_NAME)
    
    if os.name == 'nt':
        try:
            lang = gettext.translation(APP_NAME, "share\locale", languages=[locale.getdefaultlocale()[0]])
            lang.install(unicode=True)
        except:
            pass
    
        
    
    
     


########NEW FILE########
__FILENAME__ = LOG
'''
Created on Feb 26, 2010

@author: ivan
'''

import logging
with_print = False

levels = {
    "info": logging.INFO,
    "warning": logging.WARNING,
    "error": logging.ERROR,
    "none": logging.CRITICAL,
    "debug": logging.DEBUG
}

def fprint(msg):
    if with_print:
        print msg
    else:
        logging.info(msg)

def setup(level="error", filename=None):
    log_level = level
    """
    Sets up the basic logger and if `:param:filename` is set, then it will log
    to that file instead of stdout.

    :param level: str, the level to log
    :param filename: str, the file to log to
    """
    if not level or level not in levels:
        level = "error"

    logging.getLogger("foobnix")
    logging.basicConfig(
        level=levels[level],
        format="[%(levelname)-8s] [%(asctime)s] [%(filename)s:%(lineno)d] %(message)s",
        datefmt="%H:%M:%S",
        filename=filename,
        filemode="w"
    )

def print_platform_info():
    import platform
    logging.debug('*************** PLATFORM INFORMATION ************************')
    
    logging.debug('==Interpreter==')
    logging.debug('Version      :' + platform.python_version())
    logging.debug('Version tuple:' + str(platform.python_version_tuple()))
    logging.debug('Compiler     :' + platform.python_compiler())
    logging.debug('Build        :' + str(platform.python_build()))
    
    logging.debug('==Platform==')
    logging.debug('Normal :' + platform.platform())
    logging.debug('Aliased:' + platform.platform(aliased=True))
    logging.debug('Terse  :' + platform.platform(terse=True))
    
    logging.debug('==Operating System and Hardware Info==')
    logging.debug('uname:' + str(platform.uname()))
    logging.debug('system   :' + platform.system())
    logging.debug('node     :' + platform.node())
    logging.debug('release  :' + platform.release())
    logging.debug('version  :' + platform.version())
    logging.debug('machine  :' + platform.machine())
    logging.debug('processor:' + platform.processor())
    
    logging.debug('==Executable Architecture==')
    logging.debug('interpreter:' + str(platform.architecture()))
    logging.debug('/bin/ls    :' + str(platform.architecture('/bin/ls')))
    logging.debug('*******************************************************')

if __name__ == '__main__':
    setup("debug")
    print_platform_info()     

########NEW FILE########
__FILENAME__ = m3u_utils
#-*- coding: utf-8 -*-
from gi.repository import Gtk
import logging
import os.path

from foobnix.gui.service.path_service import get_foobnix_resourse_path_by_name
from foobnix.util.const import ICON_FOOBNIX
from foobnix.util.file_utils import get_file_extension



def m3u_writer(name, current_folder, paths):
    try:
        absolute = False
        for path in paths:
            if not path.startswith(current_folder):
                absolute = True
                break

        if not absolute:
            absolute = message_on_save()
        if not absolute:
            paths = [path.lstrip(current_folder+'/').replace("/", "\\")+'\r\n' for path in paths]
        else:
            paths = [path +'\r\n' for path in paths]

        m3u_file = open(name, "w")
        m3u_file.write("# This file is generated by Foobnix - the best linux player\r\n")
        map(m3u_file.write, paths)
    except UnboundLocalError:
        logging.warn("You try to save empty playlist")

def is_m3u(path):
    extension = get_file_extension(path)
    if extension and extension.lower() in [".m3u", ".m3u8"]:
        return True
    return False

def message_on_save(absolute=True):
    dialog = Gtk.Dialog(buttons=("Yes", Gtk.ResponseType.OK, "No", Gtk.ResponseType.REJECT))
    dialog.set_title(_("Choose window"))
    dialog.set_border_width(5)
    dialog.set_icon_from_file(get_foobnix_resourse_path_by_name(ICON_FOOBNIX))
    label = Gtk.Label()
    label.set_markup(_("""<big><b>\t\t\t\t\t\t\t\tAttention!\n</b></big>\t\
The relative location of the \
playlist and music files allows you to save a relative
paths to the files in your playlist. This will allow to carry along the playlist with the
files (only together) at any place of the computer or even at another computer.
Also, it will make library compatible with OS Windows. However, in this case you can't
change the relative location of the playlist file  and music files.
\tAbsolute file paths make it impossible to transfer a playlist on other computer
or use it in OS Windows, but it will put the library anywhere in the file system sepa-
rate from the music files (the library will be working).\n
\tDo you want to save the playlist with relative paths?\n"""))
    label.show()
    dialog.vbox.pack_start(label, False, False)
    dialog.vbox.show()
    dialog.show_all()
    response = dialog.run()
    if response == Gtk.ResponseType.OK:
        dialog.destroy()
        return False
    else:
        dialog.destroy()
        return True

"""message_on_save(absolute=True)
Gtk.main()"""
########NEW FILE########
__FILENAME__ = mouse_utils

from gi.repository import Gtk
from gi.repository import Gdk

def is_left_click(event):
    if event.button == 1 and event.type == Gdk.EventType.BUTTON_PRESS: #@UndefinedVariable
        return True
    else:
        return False

def is_double_left_click(event):
    if event.button == 1 and event.type == Gdk.EventType._2BUTTON_PRESS: #@UndefinedVariable
        return True
    else:
        return False

def is_middle_click(event):
    if event.button == 2 and event.type == Gdk.EventType.BUTTON_PRESS: #@UndefinedVariable
        return True
    else:
        return False

def is_double_middle_click(event):
    if event.button == 2 and event.type == Gdk.EventType._2BUTTON_PRESS: #@UndefinedVariable
        return True
    else:
        return False

def is_rigth_click(event):
    if event.button == 3 and event.type == Gdk.EventType.BUTTON_PRESS: #@UndefinedVariable
        return True
    else:
        return False

def is_double_rigth_click(event):
    if event.button == 3 and event.type == Gdk.EventType._2BUTTON_PRESS: #@UndefinedVariable
        return True
    else:
        return False

def is_middle_click_release(event):
    if event.button == 2 and event.type == Gdk.EventType.BUTTON_RELEASE: #@UndefinedVariable
        return True
    else:
        return False

def is_rigth_click_release(event):
    if event.button == 3 and event.type == Gdk.EventType.BUTTON_RELEASE: #@UndefinedVariable
        return True
    else:
        return False
    
def is_left_click_release(event):
    if event.button == 1 and event.type == Gdk.EventType.BUTTON_RELEASE: #@UndefinedVariable
        return True
    else:
        return False
    
def right_click_optimization_for_trees(treeview, event):
    try:
        path, col, cellx, celly = treeview.get_path_at_pos(int(event.x), int(event.y))
        # just in case the view doesn't already have focus
        treeview.grab_focus()
        treeview.stop_emission('button-press-event')
        selection = treeview.get_selection()
                 
        # if this row isn't already selected, then select it before popup
        if not selection.path_is_selected(path):
            selection.unselect_all()                                                
            selection.select_path(path)
    except TypeError:
        treeview.get_selection().unselect_all()
    
def is_empty_click(treeview, event):
    try:
        path, col, cellx, celly = treeview.get_path_at_pos(int(event.x), int(event.y))
        return False
    except TypeError:
        return True
########NEW FILE########
__FILENAME__ = net_wrapper
#-*- coding: utf-8 -*-
'''
Created on 31 may 2011

@author: zavlab1
'''

import time
import base64
import socket
import thread
import logging

from gi.repository import Gtk

from foobnix.fc.fc import FC
from foobnix.helpers.window import MessageWindow
from foobnix.gui.service.lastfm_service import LastFmService
from foobnix.util import idle_task


class NetWrapper():
    def __init__(self, contorls, is_ping=True):
        self.controls = contorls
        self.flag = False
        self.counter = 0 #to count how many times in row was disconnect
        self.dd_count = 0
        self.is_ping = None
        self.set_ping(is_ping)
        self.timeout = 7
        self.pause = 10
        self.is_connected = False
        "only for self.execute() method"
        self.previous_connect = True #show the message only if a connection existed and then there was a disconnect
        self.start_ping()

    def set_ping(self, is_ping=True):
        FC().net_ping = is_ping
        if not self.is_ping and is_ping:
            logging.info("ping enabled")
        elif self.is_ping and not is_ping:
            logging.info("ping disabled")
        self.is_ping = is_ping

    def start_ping(self):
        if self.flag: #means there is already one active ping process
            logging.warning("You may not have more one ping process simultaneously")
            return
        self.flag = True
        thread.start_new_thread(self.ping, ())

    def stop_ping(self):
        self.flag = False

    def ping(self):
        while self.flag:
            if FC().proxy_enable and FC().proxy_url:
                try:
                    self.ping_with_proxy()
                except Exception, e:
                    logging.error(str(e))
                return
            s = socket.socket()
            s.settimeout(self.timeout)
            port = 80 #port number is a number, not string
            try:
                s.connect(('google.com', port))
                self.is_connected = True
                if not self.previous_connect:
                    self.restore_connection()
                self.previous_connect = True
                if self.is_ping:
                    logging.info("Success Internet connection")
                self.counter = 0
            except Exception, e:

                self.is_connected = False
                if self.is_ping:
                    logging.warning("Can\'t connect to Internet. Reason - " + str(e))
                self.counter += 1
                if self.counter == 2: #if disconnect was two times in row, show message
                    if self.previous_connect:
                        self.previous_connect = False
                        if self.is_ping:
                            self.disconnect_dialog()
                    self.counter = 0
            finally:
                s.close()

            time.sleep(self.pause)

    def ping_with_proxy(self):
        while self.flag:
            if not FC().proxy_enable:
                self.ping()
                return
            s = socket.socket(socket.AF_INET,socket.SOCK_STREAM)
            s.settimeout(self.timeout)
            url="http://www.google.com:80/"
            index = FC().proxy_url.find(":")
            host = FC().proxy_url[:index]
            port = FC().proxy_url[index + 1:]
            auth = None
            if FC().proxy_user and FC().proxy_password:
                auth = base64.b64encode(FC().proxy_user + ":" + FC().proxy_password).strip()
            try:
                s.connect((host, int(port)))
                if auth:
                    s.send('GET %s HTTP/1.1' % url + '\r\n' + 'Proxy-Authorization: Basic %s' % auth + '\r\n\r\n')
                else:
                    s.send('GET %s HTTP/1.1' % url + '\r\n\r\n')
                data = s.recv(1024)
                s.close()
                if not data:
                    raise Exception("Can't get reply from " + url)
                if "407" in data:
                    raise Exception("Proxy Authentication Required")
                self.is_connected = True
                if not self.previous_connect:
                    self.restore_connection()
                self.previous_connect = True
                if self.is_ping:
                    logging.info("Success Internet connection")
                self.counter = 0
            except Exception, e:
                s.close()
                self.is_connected = False
                if self.is_ping:
                    logging.warning("Can\'t connect to Internet. Reason - " + str(e))
                self.counter += 1
                if self.counter == 2: #if disconnect was two times in row, show message
                    if self.previous_connect:
                        self.previous_connect = False
                        if self.is_ping:
                            self.disconnect_dialog()
                    self.counter = 0
            finally:
                s.close()

            time.sleep(self.pause)

    @idle_task
    def disconnect_dialog(self):
        # only one dialog must be shown
        if self.dd_count:
                logging.debug("one disconnect dialog is showing yet")
                return

        logging.info("Disconnect dialog is shown")
        self.dd_count += 1
        MessageWindow(title=_("Internet Connection"),
                      text=_("Foobnix not connected or Internet not available. Please try again a little bit later."),
                      parent=self.controls.main_window, buttons=Gtk.ButtonsType.OK)
        self.dd_count -= 1


    def is_internet(self):
        return True if self.is_connected else False

    def break_connection(self):
        self.stop_ping()
        self.is_connect = False

    def restore_connection(self):
        self.start_ping()
        logging.info("Try to restore connection")
        def task_restore_connection():
            #logging.info("Try to restore vk_service")
            #self.controls.vk_service = VKService(FC().access_token, FC().user_id)
            logging.info("Try to restore lastfm_service")
            self.controls.lastfm_service = LastFmService(self.controls)
        thread.start_new_thread(task_restore_connection, ())


    "wrapper for Internet function"
    def execute(self,func, *args):
        if not self.is_ping:
            return func(*args) if args else func()
        if self.is_connected:
            #self.previous_connect = True
            logging.info("In execute. Success internet connection")
            return func(*args) if args else func()
        else:
            logging.warning("In execute. No internet connection")
            return None


########NEW FILE########
__FILENAME__ = pix_buffer
'''
Created on Nov 4, 2010

@author: ivan
'''
import urllib
from foobnix.gui.service.path_service import get_foobnix_resourse_path_by_name
from gi.repository import Gtk
from gi.repository import GdkPixbuf
import logging

def create_pixbuf_from_url(url, size):
    pixbuf = create_origin_pixbuf_from_url(url)
    if size:
        return resize_pixbuf(pixbuf, size)
    else:
        return pixbuf

def resize_pixbuf(pixbuf, size):
    if not pixbuf:
        return None
    if size:
        return pixbuf.scale_simple(size, size, GdkPixbuf.InterpType.BILINEAR) #@UndefinedVariable
    else:
        return pixbuf

def create_pixbuf_from_path(path, size):
    if not path:
        return None
    try:
        pixbuf = GdkPixbuf.Pixbuf.new_from_file(path) #@UndefinedVariable
    except Exception, e:
        logging.error(e)
        return None

    if size:
        return resize_pixbuf(pixbuf, size)
    else:
        return pixbuf

def create_pixbuf_from_resource(name, size=None):
    path = get_foobnix_resourse_path_by_name(name)
    return create_pixbuf_from_path(path, size)

def create_origin_pixbuf_from_url(url):
    f = urllib.urlopen(url)
    data = f.read()
    pbl = GdkPixbuf.PixbufLoader() #@UndefinedVariable
    pbl.write(data)
    pbuf = pbl.get_pixbuf()
    pbl.close()
    return pbuf

########NEW FILE########
__FILENAME__ = plsparser
'''
Created on Mar 3, 2010

@author: ivan
'''
import urllib2
import logging
from foobnix.util import LOG


"Get content of the url"
def get_content(url):
    if not url:
        return None

    try:       
        connect = urllib2.urlopen(url, timeout=7)
        data = connect.read()
        return data
    except:
        logging.error("INCORRECT URL ERROR .... " + url)
        return None
    
def is_valid_station(url):
    if not url:
        return None

    try:       
        connect = urllib2.urlopen(url, timeout=10)
        if connect.getcode() == 200:
            return True
        else:
            return False
    except:
        logging.error("INCORRECT URL ERROR .... " + url)
        return False    
    
            
def getStationPath(url):
    
    if not url:
        return None
    
    _file_url = url
    urls = [] 
    try:       
        connect = urllib2.urlopen(url, timeout=7)
        data = connect.read()
        urls = getStations(data, urls)
    except Exception, e:
        logging.error("INCORRECT URL ERROR .... " + url + str(e))
    if urls:
        return urls[0]
        
def getStations(data, urls):
    for line in data.rsplit():
        line = line.lower()         
        if line.startswith("file"):                                
                index = line.find("=")
                url = line[index + 1 : ]
                urls.append(url)
                return urls    

def get_radio_source(url):
    LOG.fprint(url)
    if url:          
        if url.lower().endswith(".pls"):                
            source_url = getStationPath(url)
            if source_url :          
                logging.info("Radio url " + source_url)      
                return  source_url                   
                
        elif url.lower().endswith(".m3u"):
            content = get_content(url)
            if not content:
                return None
            for line in content.rsplit():
                if line.startswith("http://") and is_valid_station(line):
                    logging.info("Radio url " + line)
                    return line
    
    logging.info("Radio url " + url)
    return url
             
                        
                     
                

def getPlsName(_file_url):
    index = _file_url.rfind("/")
    return _file_url[index + 1:]

def getFirst(self, urls):
    if urls:
        return urls[0]
    else:
        return None

########NEW FILE########
__FILENAME__ = proxy_connect
#-*- coding: utf-8 -*-
'''
Created on 1 sep. 2010

@author: ivan
'''

import logging
import urllib2

from foobnix.fc.fc import FC

def set_proxy_settings():
    if not FC().proxy_url or not FC().proxy_enable:
        opener = urllib2.build_opener()
        urllib2.install_opener(opener)
        return
    if FC().proxy_user and FC().proxy_password:
        http_proxy = "http://%s:%s@%s" % (FC().proxy_user, FC().proxy_password, FC().proxy_url)
        https_proxy = "https://%s:%s@%s" % (FC().proxy_user, FC().proxy_password, FC().proxy_url)
    else:
        http_proxy = "http://%s" % FC().proxy_url
        https_proxy = "https://%s" % FC().proxy_url
    proxy = urllib2.ProxyHandler({"http" : http_proxy, "https" : https_proxy})
    opener = urllib2.build_opener(proxy)
    urllib2.install_opener(opener)
    logging.info("The proxy " + FC().proxy_url + " for http and https has been set")
    
if __name__ == '__main__':
    set_proxy_settings()
    res = urllib2.urlopen('https://mail.ru')
    print res.read()
########NEW FILE########
__FILENAME__ = singleton
'''
Created on Jul 27, 2010

@author: ivan
'''
class Singleton(type):
    def __call__(self, *args, **kw):
        if self.instance is None:
            self.instance = super(Singleton, self).__call__(*args, **kw)
        return self.instance
    
    def __init__(self, name, bases, dict):
        super(Singleton, self).__init__(name, bases, dict)
        self.instance = None
########NEW FILE########
__FILENAME__ = single_thread
#-*- coding: utf-8 -*-
'''
Created on 27 сент. 2010

@author: ivan
'''

import sys
import time
import thread
import logging
import traceback

from threading import Lock


class SingleThread():
    def __init__(self, progressbar=None):
        self.lock = Lock()
        self.progressbar = progressbar
        
    def run_with_progressbar(self, method, args=None, text='', no_thread=False, with_lock=True):
        #with_lock - shows, does it necessarily to do a lock or not
        
        if no_thread:
            if method and args:
                method(args)
            if method:
                method()
        else:
            self._run(method, args, text, with_lock)
                
    def _run(self, method, args=None, text='', with_lock=True):
        if not self.lock.locked():            
            self.lock.acquire()
            if self.progressbar:
                self.progressbar.start(text)
            thread.start_new_thread(self._thread_task, (method, args,))
        else:
            logging.warning("Previous thread not finished " + str(method) + " " + str(args))
            if not with_lock:
                logging.info("Try to run method without progress bar")
                thread.start_new_thread(self._thread_task, (method, args))  
    
    def _thread_task(self, method, args, with_lock=True):
        try:
            if method and args:
                method(args)
            elif method:
                method()
        except Exception, e:
            logging.error(str(e))
            exc_type, exc_value, exc_traceback = sys.exc_info()
            traceback.print_exception(exc_type, exc_value, exc_traceback, file=sys.stdout)
        finally:
            if self.lock.locked():
                if self.progressbar:
                    self.progressbar.stop()        
                self.lock.release()

########NEW FILE########
__FILENAME__ = string_utils
#-*- coding: utf-8 -*-
'''
Created on July 18, 2012

@author: zavlab1
'''

def crop_string(string, max_length):
    if (max_length > -1) and (len(string) > max_length):
            return string[:max_length]
    else:
            return string
########NEW FILE########
__FILENAME__ = tag_util
#-*- coding: utf-8 -*-
'''
Created on Jan 25, 2011

@author: zavlab1
'''

from gi.repository import Gtk
import logging
import os.path
import thread

from foobnix.util.id3_util import correct_encoding
from foobnix.util.audio import get_mutagen_audio
from foobnix.helpers.window import ChildTopWindow
from mutagen.easyid3 import EasyID3
from foobnix.util.localization import foobnix_localization
from mutagen.mp4 import MP4, MP4MetadataValueError

foobnix_localization()

class TagEditor(ChildTopWindow):
    def __init__(self, controls):
        ChildTopWindow.__init__(self, _("Tag Editor"))
        self.controls = controls

        self.store = {}

        self.set_resizable(True)
        self.set_default_size(430, 150)

        """make tooltip more quick (useful for checkbuttons)"""
        Gtk.Settings().set_property('gtk-tooltip-timeout', 0)


        artist_label = Gtk.Label(_("Artist")) #@UnusedVariable
        title_label = Gtk.Label(_("Title")) #@UnusedVariable
        album_label = Gtk.Label(_("Album")) #@UnusedVariable
        date_label = Gtk.Label(_("Year")) #@UnusedVariable
        tracknumber_label = Gtk.Label(_("Track number")) #@UnusedVariable
        genre_label = Gtk.Label(_("Genre")) #@UnusedVariable
        author_label = Gtk.Label(_("Author text")) #@UnusedVariable
        composer_label = Gtk.Label(_("Composer")) #@UnusedVariable

        self.paths = []
        self.tag_names = ["artist", "title", "album", "date", "tracknumber", "genre", "author", "composer"]
        self.tag_mp4_names = ['\xa9ART', '\xa9nam', '\xa9alb', '\xa9day', 'trkn', '\xa9gen', '', '\xa9wrt']
        self.tag_entries = []
        self.labels = []
        self.check_buttons = []
        self.hboxes = []

        for tag_name in self.tag_names:

            vars()[tag_name + "_entry"] = Gtk.Entry()
            self.tag_entries.append(vars()[tag_name + "_entry"])

            self.labels.append(vars()[tag_name + "_label"])

            vars()[tag_name + "_chbutton"] = Gtk.CheckButton()
            self.check_buttons.append(vars()[tag_name + "_chbutton"])
#
            check_button = self.check_buttons[-1]

            check_button.set_focus_on_click(False)
            check_button.set_tooltip_text(_("Apply for all selected tracks\n(active on multi selection)"))

            vars()[tag_name + "_hbox"] = Gtk.HBox(False, 5)
            self.hboxes.append(vars()[tag_name + "_hbox"])

            self.hboxes[-1].pack_end(check_button, False, False)
            self.hboxes[-1].pack_end(self.tag_entries[-1], True, True)


        lvbox = Gtk.VBox(True, 7)
        rvbox = Gtk.VBox(True, 7)
        hpan = Gtk.HPaned()

        for label, hbox in zip(self.labels, self.hboxes):
            lvbox.pack_start(label)
            rvbox.pack_start(hbox)

        hpan.pack1(lvbox)
        hpan.pack2(rvbox)

        apply_button = Gtk.Button(_("Apply"))
        close_button = Gtk.Button(_("Close"))

        buttons_hbox = Gtk.HBox(True, 10)
        buttons_hbox.pack_start(apply_button)
        buttons_hbox.pack_start(close_button)

        vbox = Gtk.VBox(False, 15)
        vbox.pack_start(hpan)
        vbox.pack_start(buttons_hbox, True, True, 10)

        apply_button.connect("clicked", self.save_audio_tags, self.paths)
        close_button.connect("clicked", lambda * a: self.hide())

        self.add(vbox)
        self.show_all()
    """
    def apply_changes_for_rows_in_tree(self):
        ''' apply stored changes for rows in playlist_tree '''
        texts = {}
        artists = {}
        titles = {}
        composers = {}
        albums = {}

        playlist_tree = self.controls.notetabs.get_current_tree()

        for path in self.store.keys():
            if self.store[path][0] and self.store[path][1]:
                artists[path] = self.store[path][0]
                titles[path] = self.store[path][1]
            elif self.store[path][0] and not self.store[path][1]:
                artists[path] = self.store[path][0]
                titles[path] = _('Unknown title')
            elif self.store[path][1] and not self.store[path][0]:
                artists[path] = _('Unknown artist')
                titles[path] = self.store[path][1]

            if artists.has_key(path):
                texts[path] = artists[path] + ' - ' + titles[path]
            else:
                texts[path] = os.path.basename(path)
                artists[path] = ""
                titles[path] = ""

            if artists[path] == _('Unknown artist'):
                artists[path] = ""
            if titles[path] == _('Unknown title'):
                titles[path] == ""

            if self.store[path][2]:
                composers[path] = self.store[path][2]
            if self.store[path][3]:
                albums[path] = self.store[path][3]

        for path in self.store.keys():
            for row in playlist_tree.model:
                if row[playlist_tree.path[0]] == path:
                    if path in texts:
                        row[playlist_tree.text[0]] = texts[path]
                        row[playlist_tree.artist[0]] = artists[path]
                        row[playlist_tree.title[0]] = titles[path]
                    if path in composers:
                        row[playlist_tree.composer[0]] = composers[path]
                    if path in albums:
                        row[playlist_tree.album[0]] = albums[path]
        self.store = {}
    """

    def get_audio_tags(self, paths):
        self.paths = paths
        if len(paths) == 1:
            for chbutton in self.check_buttons:
                chbutton.set_sensitive(False)
        else:
            for chbutton in self.check_buttons:
                chbutton.set_sensitive(True)

        self.audious = []
        for path in paths[:]:
            if not path or os.path.isdir(path):
                self.paths.remove(path)
                continue
            audio = get_mutagen_audio(path)

            if not audio:
                try:
                    audio.add_tags(ID3=EasyID3)
                except Exception, e:
                    logging.error(e)

            self.decoding_cp866(audio)
            self.audious.append(audio)


        if isinstance(self.audious[0], MP4):
            tag_names = self.tag_mp4_names
            '''make author entry not sensitive because mp4 hasn't so tag'''
            self.tag_entries[-2].set_sensitive(False)
            self.check_buttons[-2].set_sensitive(False)
            self.labels[-2].set_sensitive(False)
        else:
            tag_names = self.tag_names
        for tag_name, tag_entry in zip(tag_names, self.tag_entries):
            tag_entry.delete_text(0, -1)
            try:
                if self.audious[0].has_key(tag_name):
                    tag_entry.set_text(self.audious[0][tag_name][0])
                else:
                    tag_entry.set_text('')
            except AttributeError:
                logging.warn('Can\'t get tags. This is not audio file')
            except TypeError, e:
                if isinstance(self.audious[0][tag_name][0], tuple):
                    tag_entry.set_text(str(self.audious[0][tag_name][0]).strip('()'))
                else:
                    logging.error(e)
        self.show_all()

    def save_audio_tags(self, button, paths):

        def set_tags(audio, path, tag_name):
            if not self.store.has_key(path):
                self.store[path] = ["", "", "", ""]
            if isinstance(audio, MP4):
                tag_name = tag_mp4_name
            try:
                if audio.has_key(tag_name):
                    if not tag_value:
                        del audio[tag_name]
                        audio.save()
                        return
                    audio[tag_name] = tag_value
                else:
                    if tag_value:
                        audio[tag_name] = [tag_value]
                audio.save()

            except AttributeError:
                logging.warn('Can\'t save tags. Perhaps' + os.path.split(path)[1] + ' is not audio file')
            except MP4MetadataValueError:
                '''for mp4 trkn is tuple'''
                new_tag_value = [tuple(map(int, tag_value.split(', ')))]
                audio[tag_name] = new_tag_value
                audio.save()

            """
            ''' store changes '''
            if (tag_name == "artist" or tag_name == '\xa9ART') and tag_value:
                self.store[path][0] = tag_value
                try:
                    if audio.has_key("title"):
                        self.store[path][1] = audio["title"][0]
                    elif audio.has_key('\xa9nam'):
                        self.store[path][1] = audio['\xa9nam'][0]
                except UnicodeDecodeError:
                    pass
            elif (tag_name == "title" or tag_name == '\xa9nam') and tag_value:
                self.store[path][1] = tag_value
                try:
                    if audio.has_key("artist"):
                        self.store[path][0] = audio["artist"][0]
                    elif audio.has_key('\xa9ART'):
                        self.store[path][0] = audio['\xa9ART']
                except UnicodeDecodeError:
                    pass
            if (tag_name == "composer" or tag_name == '\xa9wrt') and tag_value:
                self.store[path][2] = tag_value
            if (tag_name == "album" or tag_name == '\xa9alb') and tag_value:
                self.store[path][3] = tag_value
            """


        for tag_name, tag_mp4_name, tag_entry, check_button in zip(self.tag_names, self.tag_mp4_names, self.tag_entries, self.check_buttons):
            tag_value = tag_entry.get_text()
            if check_button.get_active():
                for audio, path in zip(self.audious, self.paths):
                    set_tags(audio, path, tag_name)
            else:
                set_tags(self.audious[0], self.paths[0], tag_name)

            check_button.set_active(False)

        #self.apply_changes_for_rows_in_tree()

        self.hide()

        self.controls.notetabs.get_current_tree().change_rows_by_path(self.paths)


    def decoding_cp866(self, audio):
        if not audio:
            return
        if not isinstance(audio, MP4):
            for value, key in zip(audio.values(), audio.keys()):
                audio[key] = correct_encoding(value[0])

def edit_tags(a):
    controls, paths = a
    if not globals().has_key("tag_editor"):
        global tag_editor
        tag_editor = TagEditor(controls)
    tag_editor.get_audio_tags(paths)



########NEW FILE########
__FILENAME__ = text_utils
import re
from foobnix.fc.fc import FC
from foobnix.util.file_utils import get_file_extension
import urllib
import string

def capitalize_query(line):
    if not line:
        return line
    
    if line.startswith("http://"):
        return line
    
    line = u"" + line.strip()
    result = ""
    for word in line.split():
        result += " " + word[0].upper() + word[1:]
    return result.strip()

def capitalize_string(src):
    if not src:
        return src

    line = u"" + src.strip()
    word_capitalized = map(string.capitalize, line.split())
    return ' '.join(word_capitalized)


def smart_splitter(input, max_len):
    if not input:
        return input
    
    if max_len > len(input):
        return input
        
    separators = (" " , "-" , "," , "/" , "_", "\n")    
    result = []    
    buffer = ""
    for i in xrange(len(input)):
        char = input[i]
        buffer += char
                
        if len(buffer) >= max_len:
            if char in separators:   
                result.append(buffer.strip())
                buffer = ""                
    result.append(buffer[:max_len].strip())
    return result


'''divides the string into pieces according to a specified maximum length
fission occurs only at the nearest left separator
If delimiter is not found, the division on the maximum length'''        
def split_string(str, length):
    if not str:
        return str
    #take the max number of characters from a string
    i = length - 1 
    separator = None
    #go around them from right to left
    while i > -1:
        #compare each character with the values of the tuple
        for simbol in (" " , "-" , "," , "/" , "_"):
            #first matching symbol assign separator
            if str[i] == simbol:
                separator = str[i]
                break
        #if the symbol is not found in the tuple, 
        #go to the next symbol to the left
        if not separator:
            i -= 1
        else: break
    #if the symbol is not found in the sequence,
    #the separator becomes the last symbol of the first row
    if not separator:
        i = length - 1
        separator = str[i]
    #divide the string into substrings
    substr1 = str[: i + 1].strip()
    substr2 = str[(i + 1) :].strip()
    #if the second row higher than the maximum length, call recursion
    if len(substr2) > length:
        substr2 = split_string(substr2, length)
    #divide the string into substrings on the separator and return the result
    str = substr1 + "\n" + substr2
    return str

def normalize_text(line):
    if not line:
        return ""
    line = urllib.unquote(line)
    """find in extension"""
    for element in ("[", "(", "*","#"):
        index = line.find(element)
        if index >= 0:            
            line = line[:index]
        index = -1
        
    """find in prefix"""
    prefix_index = re.search('^([ 0-9.-]*)', line).end()   
    line = line[prefix_index:]
    
    line = capitalize_string(line)
    
    """remove extension"""
    ext = get_file_extension(line)  
    if ext in FC().all_support_formats:                
        line = line.replace(ext, "")
    
    return line.strip()

def html_decode(line):
    try:
        from setuptools.package_index import htmldecode
        return htmldecode(line)
    except:
        return line

########NEW FILE########
__FILENAME__ = time_utils
'''
Created on Feb 26, 2010

@author: ivan
'''


def size2text(size):
    if size > 1024 * 1024 * 1024:
        return "%.2f Gb" % (size / (1024 * 1024 * 1024.0))
    if size > 1024 * 1024:
        return "%.2f Mb" % (size / (1024 * 1024.0))
    if size > 1024:
        return "%.2f Kb" % (size / 1024.0)
    return size

def convert_seconds_to_text(time_sec):
        time_sec = int(time_sec)

        hours = time_sec / (60 * 60)
        time_sec = time_sec - (hours * 60 * 60)

        mins = time_sec / 60
        time_sec = time_sec - (mins * 60)

        secs = time_sec
        if hours > 0:
            return '%(hours)d:%(mins)02d:%(secs)02d' % {'hours' : hours, 'mins': mins, 'secs': secs }
        else:
            return '%(mins)02d:%(secs)02d' % {'mins': mins, 'secs': secs}
########NEW FILE########
__FILENAME__ = url_utils
#-*- coding: utf-8 -*-
'''
Created on 1 дек. 2010

@author: ivan
'''
import urllib
import httplib
import urlparse


""""
Server: nginx/0.8.53
Date: Wed, 01 Dec 2010 07:37:42 GMT
Content-Type: text/html
Content-Length: 169
Connection: close
"""

def get_url_length(path):
    open = urllib.urlopen(path)
    return open.info().getheaders("Content-Length")[0]

def get_url_type(path):
    open = urllib.urlopen(path)
    return open.info().getheaders("Content-Type")[0]

"""method is not reliable. too dependent on the server configuration"""
def is_exists(url):
    p = urlparse.urlparse(url)
    h = httplib.HTTP(p[1])
    h.putrequest('HEAD', p[2])
    h.endheaders()
    if h.getreply()[0] == 200:
        return 1
    else:
        return 0

if __name__ == '__main__':
    is_exists("")
########NEW FILE########
__FILENAME__ = version
def compare_versions(v1, v2):
    
    if not v1 or not v2:
        return 0
    v1 = v1.replace("-","").replace(".","")
    v2 = v2.replace("-","").replace(".","")
    
    v1 = int(v1)
    v2 = int(v2)
    
    if v1 == v2:
        return 0
    elif v1 > v2:
        return -1
    else:
        return 1
    
    
if __name__ == '__main__':
    print compare_versions("2.6.0","2.5.3")
    

########NEW FILE########
__FILENAME__ = widget_utils
#-*- coding: utf-8 -*-
'''
Created on 29 нояб. 2010

@author: ivan
'''
from gi.repository import Gtk

class MenuStyleDecorator():
    def __init__(self):
        correct_style_element = Gtk.Window()
        correct_style_element.realize()
        self.style = correct_style_element.get_style()
        
    def apply(self, widget):
        style = self.style
        ## TODO: fix it
        return
        ##widget.modify_bg(Gtk.StateType.NORMAL, style.bg[Gtk.StateType.NORMAL])
        ##widget.modify_fg(Gtk.StateType.NORMAL, style.fg[Gtk.StateType.NORMAL])
        
        for childs in widget.get_children():
            for child in childs:
                widget.modify_bg(Gtk.StateType.NORMAL, style.bg[Gtk.StateType.NORMAL])
                child.modify_fg(Gtk.StateType.NORMAL, style.fg[Gtk.StateType.NORMAL])
        

########NEW FILE########
__FILENAME__ = version
FOOBNIX_VERSION='3.0.00'
########NEW FILE########
__FILENAME__ = foobnix
#!/usr/bin/env python

import os
import sys
import time
import logging
import traceback

from gi import pygtkcompat, require_version
pygtkcompat.enable_gtk(version="3.0")

from gi.repository import Gtk
from gi.repository import GLib


from threading import Timer
from foobnix.fc.fc import FC
from foobnix.util import LOG, analytics
from foobnix.fc.fc_helper import CONFIG_DIR


def except_hook(exc_t, exc_v, traceback):
    logging.error("*** Uncaught exception ***")
    logging.error(exc_t)
    logging.error(exc_v)
    logging.error(traceback)

#sys.excepthook = except_hook


def foobnix():

    if "--debug" in sys.argv:
        LOG.with_print = True
        for param in sys.argv:
            if param.startswith("--log"):
                if "=" in param:
                    filepath = param[param.index("=")+1 : ]
                    if filepath.startswith('~'):
                        filepath = os.path.expanduser("~") + filepath[1 : ]
                else:
                    filepath = os.path.join(CONFIG_DIR, "foobnix.log")
                LOG.setup("debug", filename=filepath)
        else:
            LOG.setup("debug")
        LOG.print_platform_info()
    else:
        LOG.setup("error")

    from foobnix.gui.foobnix_core import FoobnixCore

    if "--test" in sys.argv:
        from test.all import run_all_tests
        print("""TEST MODE""")
        result = run_all_tests(ignore="test_core")
        if not result:
            raise SystemExit("Test failures are listed above.")
        exit()

    init_time = time.time()

    if "--nt" in sys.argv or os.name == 'nt':
        GLib.threads_init() #@UndefinedVariable
        core = FoobnixCore(False)
        core.run()
        analytics.begin_session()
        print("******Foobnix run in", time.time() - init_time, " seconds******")
        Gtk.main()
    else:
        init_time = time.time()
        from foobnix.gui.controls.dbus_manager import foobnix_dbus_interface
        iface = foobnix_dbus_interface()
        if "--debug" in sys.argv or not iface:
            print("start program")
            GLib.threads_init()    #@UndefinedVariable
            core = FoobnixCore(True)
            core.run()
            settings = Gtk.settings_get_default()
            settings.props.gtk_button_images = True
            settings.props.gtk_menu_images = True
            analytics.begin_session()
            analytics.begin_session()
            #core.dbus.parse_arguments(sys.argv)
            analytics.begin_session()
            print("******Foobnix run in", time.time() - init_time, " seconds******")
            if sys.argv:
                Timer(1, GLib.idle_add, [core.check_for_media, sys.argv]).start()

            Gtk.main()
        else:
            print(iface.parse_arguments(sys.argv))

if "--profile" in sys.argv:
    import cProfile
    cProfile.run('foobnix()')
else:
    try:
        foobnix()
        analytics.end_session()
    except Exception, e:
        analytics.end_session()
        analytics.error("Main Exception"+str(e))
        exc_type, exc_value, exc_traceback = sys.exc_info()
        traceback.print_exception(exc_type, exc_value, exc_traceback, file=sys.stdout)
        FC().save()

########NEW FILE########
__FILENAME__ = changelog_gen
#!/usr/bin/env python
import sys
import datetime
print sys.argv
VERSION = sys.argv[1]
UBUNTU = sys.argv[2]

"""begin"""
dt = datetime.datetime.today()
TIME = dt.strftime("%a, %d %b %Y %H:%M:%S +0200")
BUG_NUM = "1000" + VERSION

template = """foobnix (%(VERSION)s) %(UBUNTU)s; urgency=low

  * Initial release (Closes: #%(BUG_NUM)s)  Upload new release %(VERSION)s
  
 -- Ivan Ivanenko <ivan.ivanenko@gmail.com>  %(TIME)s
""" % {'UBUNTU':UBUNTU, 'VERSION':VERSION, "TIME":TIME, "BUG_NUM":BUG_NUM}

file = open("changelog", "w")
file.write(template)
file.close()

print template





########NEW FILE########
__FILENAME__ = all
#-*- coding: utf-8 -*-
'''
Created on 20 нояб. 2010

@author: ivan
'''
import glob
import unittest

def run_all_tests(ignore="@"):
    test_file_strings = glob.glob('test/test_*.py')
    if not test_file_strings:      
        test_file_strings = glob.glob('test_*.py')
    module_strings = [str[0:len(str) - 3].replace("/", ".") for str in test_file_strings if ignore not in str]
    suites = [unittest.defaultTestLoader.loadTestsFromName(str) for str
              in module_strings]
    testSuite = unittest.TestSuite(suites)
    result = unittest.TextTestRunner().run(testSuite)
    return result.wasSuccessful()

########NEW FILE########
__FILENAME__ = di_fm
'''
Created on 16  2010

@author: ivan
'''
import urllib2
import simplejson
from HTMLParser import HTMLParser


def load_urls_name_page():
    connect = urllib2.urlopen("http://listen.di.fm/public3")
    data = connect.read()
    p = HTMLParser()
    data = p.unescape(data)
    for i in simplejson.loads(data):
        print "%s =  %s" % (i["name"], i["playlist"])

if __name__ == "__main__":
    load_urls_name_page()
########NEW FILE########
__FILENAME__ = guzei
# -*- coding: utf-8 -*-
'''
Created on Jul 16, 2010

@author: ivan
'''

import re
import sys
import logging
import urllib2
from multiprocessing import Pool

def load_urls_name_page():
    site = "http://guzei.com/online_radio/"
    file = open("GUZEI.COM.fpl", "w")
    j = 1
    result = []
    while True:
        print "Opening page %d" % j
        site = "http://guzei.com/online_radio/?p=" + str(j)
        connect = urllib2.urlopen(site)
        data = connect.read()
        for line in data.split("\n"):
            reg_all = "([^{</}]*)"

            re_link = '<a target="guzei_online" href="./listen.php\?online_radio_id=([0-9]*)" title="' + reg_all + '"><span class="name">' + reg_all + '</span></a>'
            re_region = '<a href="\./index\.php\?radio_region=([0-9]*)">' + reg_all + '</a>'
            re_bitrate = '\d*Kbps'

            links = re.findall(re_link, line, re.IGNORECASE | re.UNICODE)

            if links:
                region = re.findall(re_region, line, re.IGNORECASE | re.UNICODE)
                re_bitrate = re.findall(re_bitrate, line, re.IGNORECASE | re.UNICODE)
                i = 0
                pool_queue = []
                for line in links:
                    id = line[0]
                    name = line[2]
                    if region:
                        name = name + " (" + region[i][1] + ")" + ' - ' + re_bitrate[i]
                    i += 1
                    pool_queue.append({
                        'name': name,
                        'id': id
                    })
                pool = Pool(processes=12)
                actual = pool.map(get_url_by_id, pool_queue)
                for entry in actual:
                    if "url" in entry:
                        result.append("%s =  %s\n" % (entry["name"], entry["url"]))

        if re.search('<span class="nav_bar">\d*</span><a class="nav_bar"', data):
            j += 1
            continue
        else:
            print "The end"
            #map(sys.stdout.write, result)
            map(file.write, result)
            break


def get_url_by_id(entry):
    id = entry["id"]
    print "\tGetting url for station %s" % id
    url = "http://guzei.com/online_radio/listen.php?online_radio_id=" + id
    connect = urllib2.urlopen(url)
    data = connect.read()
    for line in data.split("\n"):
        line = line.strip()
        cr = '<audio autoplay="autoplay" controls="controls" style="margin: 2px auto"><source src="'
        if line.startswith(cr):
            subline = line[len(cr) : ]
            link = subline[0 : subline.find('"')]
            link = link.strip()
            entry["url"] = link
            return entry
    return entry

if __name__ == '__main__':
    load_urls_name_page()

########NEW FILE########
__FILENAME__ = guzei_best
# -*- coding: utf-8 -*-
'''
Created on Jul 16, 2010

@author: ivan
'''

import re
import logging
import urllib2
from foobnix.util.plsparser import is_valid_station
import os

def load_urls_name_page():
    file_name = "GUZEI.COM.fpl";
    if os.path.isfile(file_name):
        os.remove(file_name)
    file = open(file_name, "w")
    for j in range(1,30):
        result = []
        print "==========", "page", str(j),"============================"
        site = "http://guzei.com/online_radio/index.php?f[mp3]=on&radio_format=0&p=" + str(j)
        print site
        connect = urllib2.urlopen(site)
        data = connect.read()  
        
        for line in data.split("\n"):
            if '<a target="guzei_online" href="./listen.php?online_radio_id=' in line:
                reg_all = "([^{</}]*)"
              
                re_link = '<a target="guzei_online" href="./listen.php\?online_radio_id=([0-9]*)" title="' + reg_all + '"><span class="name">' + reg_all + '</span></a>'
                re_region = '<a href="./\?radio_region=([0-9]*)">' + reg_all + '</a>'
                re_bitrate = '\d*Kbps'
                
                links = re.findall(re_link, line, re.IGNORECASE | re.UNICODE)
                if links:
                    region = re.findall(re_region, line, re.IGNORECASE | re.UNICODE)
                    re_bitrate = re.findall(re_bitrate, line, re.IGNORECASE | re.UNICODE)
                    i = 0
                    for line in links:
                        
                        id = line[0]
                        name = line[2]
                        if region:
                            name = name + " (" + region[i][1] + ")" + ' - ' + re_bitrate[i]
                        i += 1
                        print id,name
                        url = get_ulr_by_id(id)
                        print url
                        if not url:
                            continue
                        if not is_valid_station(url):
                            continue
                                                     
                        res = name + " = " + url
                        logging.info(j)
                        logging.info(res)
                        print "page", j, res
                        result.append(res + '\n')
                        #file.write(res + '\n')
            
        map(file.write, result)

def get_ulr_by_id(id):
    url = "http://guzei.com/online_radio/listen.php?online_radio_id=" + str(id)
    connect = urllib2.urlopen(url)
    data = connect.read()
    reg_all = "([^{<}]*)"
    links = re.findall(u'<source src="'+reg_all+'"', data, re.IGNORECASE | re.UNICODE)
    if links and links[0]:
        path = links[0].replace('" width="300px" height="94','')
        return path
    else:
        return None
        
            
if __name__ == '__main__':
    load_urls_name_page()
    #get_ulr_by_id(2728)  

########NEW FILE########
__FILENAME__ = jazzradio_com
# -*- coding: utf-8 -*-
'''
Created on 17 Nov 2013

@author: Viktor Suprun
'''
import urllib2
import simplejson
from HTMLParser import HTMLParser


def load_urls_name_page():
    connect = urllib2.urlopen("http://listen.jazzradio.com/public3")
    data = connect.read()
    p = HTMLParser()
    data = p.unescape(data)
    for i in simplejson.loads(data):
        print "%s =  %s" % (i["name"].encode('utf-8'), i["playlist"].encode('utf-8'))

if __name__ == "__main__":
    load_urls_name_page()
########NEW FILE########
__FILENAME__ = myradio_ua
# -*- coding: utf-8 -*-
'''
Created on 16  2010

@author: ivan
'''
import urllib2
import logging
import re
site = "http://myradio.ua/player/50"


def load_urls_name_page():
    connect = urllib2.urlopen(site)
    data = connect.read()  
    result = {}  
    file = open("MYRADIO_UA.fpl", "w")
    for line in data.split("\n"):
        line = line.decode("cp1251").decode('utf8')
        reg_all = "([-\w0-9,. ]*)"
        findall = re.findall('name="'+reg_all+'" value="([0-9]*)" external="0" mount="'+reg_all+'"', line, re.IGNORECASE | re.UNICODE)
        if findall:
            name = findall[0][0]
            url = findall[0][2]
            out = name + " = " + "http://relay.myradio.ua/" + url + "128.mp3 \n"
            print out
            file.write(out)
        

def test():
    reg_all = "([-\w/0-9,. ]*)"
    url = """<a onclick="MRPlayer.changeFormat(this);" id="format_62" name="фіasdf-123" value="62" external="0" mount="eurovision2010" server="1" class="radio__dropdown-link" slogan="Музыка ежегодного телевизионного конкурса" url="eurovision" comments="40" fm="0">Евровидение</a>"""
    findall = re.findall('name="'+reg_all+'" value="([0-9]*)" external="0" mount="'+reg_all+'"', url.decode('utf8'),re.UNICODE)
    if findall:
        print findall
             

#test();
load_urls_name_page()
########NEW FILE########
__FILENAME__ = screamer-radio
'''
Created on Jul 16, 2010

@author: ivan
'''
import urllib2
import logging

site = "http://www.screamer-radio.com/"
site_full = site + "directory/browsegenre/51/"

def load_urls_name_page():
    connect = urllib2.urlopen(site_full)
    data = connect.read()  
    file = open("SKY.FM.fpl", "w")
    for line in data.split("\n"):
        if line.find("sky.fm") > 0:            
            url = line[line.find('<td><a href="') + len('<td><a href="') + 1:line.find('/">')]
            name = line[line.find('sky.fm -') + len('sky.fm -') + 1:line.find('</a></td>')]
            logging.info(name+ url)
            urls = get_urls(site + url)
            file.write(name.strip() + " = " + urls + "\n");
    file.close()       

def get_urls(path):
    connect = urllib2.urlopen(path)
    data = connect.read()
    result = ""  
    for line in data.split("\n"):
        if line.find(") http://") > 0:
           result = result + line[line.find(') ') + 2:line.find("<br />")] + ", "

    return result[:-2]
#load_urls_name_page()
#LOG.info(get_urls("http://www.screamer-radio.com/directory/show/3825/")

########NEW FILE########
__FILENAME__ = sky_fm
# -*- coding: utf-8 -*-
'''
Created on 16  2010

@author: ivan
'''
import urllib2
import simplejson
from HTMLParser import HTMLParser


def load_urls_name_page():
    connect = urllib2.urlopen("http://listen.sky.fm/public3")
    data = connect.read()
    p = HTMLParser()
    data = p.unescape(data)
    for i in simplejson.loads(data):
        print "%s =  %s" % (i["name"], i["playlist"])

if __name__ == "__main__":
    load_urls_name_page()
########NEW FILE########
__FILENAME__ = xiph
'''
Created on Sep 10, 2010

@author: ivan
'''
import urllib2
from foobnix.util.plsparser import get_radio_source
def load_urls_name_page():    
    file = open("XIPH_ORG.fpl", "w")
    for i in xrange(6):    
        print "begin page", str(i)
        connect = urllib2.urlopen("http://dir.xiph.org/by_format/MP3?search=mp3&page=" + str(i))
        data = connect.read()
        print "end"  
        
        name = ""
        link = "" 
        description = "" 
        genre = ""
        genres = []
        
        for line in data.split("\n"):
            if line.find("('/stream/website');") >= 0:
                if name:            
                    link = get_radio_source(link);
                    if link:                        
                        all = name + " (" + description + ") " + ", ".join(genres) + "=" + link + "\n"
                        all = all.replace("&#039;", "")
                        all = all.replace("&amp;", "&")
                        print all
                        file.write(all)          
                    genres = []
                                
                name = line[line.find("('/stream/website');") + len("('/stream/website');") + 2:line.find("</a>")]
                #print "RADIO:- "+name.replace("&#039;","'")
            
            
            """href="/listen/1003756/listen.m3u">M3U</a>"""
            if line.find("M3U</a>") >= 0:
                link = line[line.find('href="/listen/') + len('href="'):line.find('title="') - 2]
                link = "http://dir.xiph.org/" + link
                #print link
    
            """<p class="stream-description">Jazz, Soul und Blues rund um die Uhr</p>"""    
            if line.find('stream-description">') >= 0:
                description = line[line.find('stream-description">') + len("stream-description'>"):line.find("</p>")]
                #print "description:- "+description.replace("&#039;","'")
            
            """<a title="Music radios" href="/by_genre/Music">Music</a>"""
            if line.find(' href="/by_genre/') >= 0 and line.find("dir.xiph.org") < 0:
                genre = line[line.find('>') + len('href="/by_genre/') + 4:line.find('</a>')]
                if genre.find('" title') > 0:
                    genre = genre[:genre.find('" title')]
                #print "genre:- "+genre
                genres.append(genre)
            
    file.close();
load_urls_name_page()   

########NEW FILE########
__FILENAME__ = logger
#-*- coding: utf-8 -*-
'''
Created on 25 дек. 2010

@author: ivan
'''
import logging

LEVELS = {'debug': logging.DEBUG,
          'info': logging.INFO,
          'warning': logging.WARNING,
          'error': logging.ERROR,
          'critical': logging.CRITICAL}


#level = LEVELS.get(logging.DEBUG, logging.NOTSET)
logging.basicConfig(level=logging.DEBUG)

logging.debug('This is a debug message')
logging.info('This is an info message')
logging.warning('This is a warning message')
logging.error('This is an error message')
logging.critical('This is a critical error message')

########NEW FILE########
__FILENAME__ = test
import pygtk
pyGtk.require('2.0')
from gi.repository import Gtk

class Winder( Gtk.Window):
    def __init__(self):
        Gtk.Window.__init__(self)

        box = Gtk.HBox()
        self.add(box)

        model = Gtk.TreeStore(str)
        tree = Gtk.TreeView(model)
        box.pack_start(tree)

        cell = Gtk.CellRendererText()
        col = Gtk.TreeViewColumn('woot', cell, text=0)
        tree.append_column(col)

        #tree.enable_model_drag_dest([("text/uri-list", 0, 0)], Gtk.gdk.ACTION_COPY | Gtk.gdk.ACTION_MOVE) #@UndefinedVariable
        
    

        targets = [('text/uri-list', 0, 0)]
        
        tree.drag_source_set(Gtk.gdk.BUTTON1_MASK, targets,Gtk.gdk.ACTION_COPY|Gtk.gdk.ACTION_MOVE)
        #tree.enable_model_drag_source(Gtk.gdk.BUTTON1_MASK, [("text/uri-list", 0, 0)], Gtk.gdk.ACTION_COPY | Gtk.gdk.ACTION_MOVE) #@UndefinedVariable
        #tree.enable_model_drag_source(Gtk.gdk.BUTTON1_MASK, [('text/uri-list', 0, 0)], Gtk.gdk.ACTION_COPY | Gtk.gdk.ACTION_MOVE) #@UndefinedVariable
        tree.enable_model_drag_dest(targets, Gtk.gdk.ACTION_COPY|Gtk.gdk.ACTION_MOVE)
        
        tree.drag_source_set_icon_stock('gtk-dnd-multiple')

        for i in range(0, 100):
            model.append(None,['test_%d' % i])

        self.set_size_request(500, 500)
        self.show_all()

Winder()
Gtk.main()
########NEW FILE########
__FILENAME__ = twitter
import httplib
import json
import logging
import socket
import time
import urllib
 
SEARCH_HOST = "search.twitter.com"
SEARCH_PATH = "/search.json"
 
 
class TagCrawler(object):
    ''' Crawl twitter search API for matches to specified tag.  Use since_id to
    hopefully not submit the same message twice.  However, bug reports indicate
    since_id is not always reliable, and so we probably want to de-dup ourselves
    at some level '''
 
    def __init__(self, max_id, tag, interval):
        self.max_id = max_id
        self.tag = tag
        self.interval = interval
 
    def search(self):
        c = httplib.HTTPConnection(SEARCH_HOST)
        params = {'q' : self.tag}
        if self.max_id is not None:
            params['since_id'] = self.max_id
        path = "%s?%s" % (SEARCH_PATH, urllib.urlencode(params))
        try:
            c.request('GET', path)
            r = c.getresponse()
            data = r.read()
            c.close()
            try:
                result = json.loads(data)
            except ValueError:
                return None
            if 'results' not in result:
                return None
            self.max_id = result['max_id']
            return result['results']
        except (httplib.HTTPException, socket.error, socket.timeout), e:
            logging.error("search() error: %s" % (e))
            return None
 
    def loop(self):
        while True:
            logging.info("Starting search")
            data = self.search()
            if data:
                logging.info("%d new result(s)" % (len(data)))
                self.submit(data)
            else:
                logging.info("No new results")
            logging.info("Search complete sleeping for %d seconds"
                    % (self.interval))
            time.sleep(float(self.interval))
 
    def submit(self, data):
        pass
tag = TagCrawler(10, "foobnix", 10)
for line in tag.search():
    print line['from_user'], " = ", line['text'], "id:", line["id_str"]
    #print line
#print tag.loop()

########NEW FILE########
__FILENAME__ = test_core
#-*- coding: utf-8 -*-
'''
Created on 20 нояб. 2010

@author: ivan
'''
import unittest
from foobnix.gui.foobnix_core import FoobnixCore
class TestFoobnixCore(unittest.TestCase):    
    def __test_main_window(self):
        self.w = FoobnixCore()
        self.assertTrue(True)
        self.w = None
    
    def test_veraion(self):
        self.assertTrue('0.2.2-10ppa0' > '0.2.2-09ppa0')
        self.assertTrue('0.2.2-9ppa0' > '0.2.2-09ppa0')
        
if __name__ == '__main__':
    unittest.main()

########NEW FILE########
__FILENAME__ = test_crash
#-*- coding: utf-8 -*-
'''
Created on 5 дек. 2010

@author: ivan
'''
def chardecode_crash():
    s = u'\x00Q\x00u\x00i\x00c\x00k'
    print s
    print s == 'Quick'
    import re
    re.search('Quick', s)
    import chardet
    print chardet.detect(s)
    print s.decode('utf_16')
    
    print "Success"

class A():
    def __init__(self):
        print "a"
    
    def go(self):
        print self.param
    
class B(A):
    def __init__(self):
        A.__init__(self)
        print "b"
        self.param = "hi"

b = B()
b.go()

########NEW FILE########
__FILENAME__ = test_cue_service
from foobnix.cue.cue_reader import CueReader
import unittest

""" TODO if possible to implament all cases with all different CUE files"""
import os
class TestGoogleService(unittest.TestCase):
    def _test_correct_cue(self):
        class FakeNormalReader(CueReader):
            def __init__(self, cue_file, duration_min):
                CueReader.__init__(self, cue_file)
                self.duration_min = duration_min
                
            def get_full_duration(self, cue_file):
                return 60 * self.duration_min
        
        path = os.path.join("test", "cue", "normal", "Portishead - Dummy.cue")
        if not os.path.exists(path):
            path = os.path.join("cue", "normal", "Portishead - Dummy.cue")
        
        cue = FakeNormalReader(os.path.join(path), 45)
        common_beans = cue.get_common_beans()        
        result = [
                    ('Portishead', 'Mysterons', 0, 303, '05:03'),
                    ('Portishead', 'Sour Times', 303, 251, '04:11'),
                    ('Portishead', 'Strangers', 554, 237, '03:57'),
                    ('Portishead', 'It Could Be Sweet', 791, 256, '04:16'),
                    ('Portishead', 'Wandering Star', 1047, 293, '04:53'),
                    ('Portishead', "It's a Fire", 1340, 225, '03:45'),
                    ('Portishead', 'Numb', 1565, 234, '03:54'),
                    ('Portishead', 'Roads', 1799, 303, '05:03'),
                    ('Portishead', 'Pedestal', 2102, 219, '03:39'),
                    ('Portishead', 'Biscuit', 2321, 301, '05:01'),
                    ('Portishead', 'Glory Box', 2622, 78, '01:18')
                   ]
        
        self.assertTrue(common_beans)
        
        for i, bean in enumerate(common_beans):
            line = bean.artist, bean.title, bean.start_sec, bean.duration_sec, bean.time
            self.assertEquals(result[i], line)
        
    """need not implement"""
    def _test_splited_cue(self):
        class FakeSplitReader(CueReader):
            def __init__(self, cue_file, duration_min):
                CueReader.__init__(self, cue_file)
                self.duration_min = duration_min
                
            def get_full_duration(self, cue_file):
                if "01 - Pray for Rain.flac" in cue_file:
                    return 60 * self.duration_min
                if "02 - Babel.flac" in cue_file:
                    return 60 * self.duration_min
                if "10 - Atlas Air.flac" in cue_file:
                    return 60 * self.duration_min
                
                return 60 * self.duration_min
        
        cue = FakeSplitReader("cue/split/Heligoland.cue", 45)
                
        common_beans = cue.get_common_beans() 
        result = [
                 ('01 - Pray for Rain', 0, 0, '00:00'),
                 ('02 - Babel', 0, 0, '00:00'),
                 ('10 - Atlas Air', 0, 0, '00:00')
                 ]
        
        self.assertTrue(common_beans)
        
        for i in [0, 1, 9]:
            bean = common_beans[i]
            line = bean.text, bean.start_sec, bean.duration_sec, bean.time
            self.assertEquals(result[i], line)  
    
    
if __name__ == '__main__':
    unittest.main()    

########NEW FILE########
__FILENAME__ = test_google_service
#-*- coding: utf-8 -*-
'''
Created on 22 нояб. 2010

@author: ivan
'''
import unittest
from foobnix.gui.service.google_service import google_search_results
from xgoogle import translate
class TestGoogleService(unittest.TestCase):
        
    def test_find_word(self):
        list = google_search_results("Madonna", 10)
        self.assertEquals(10, len(list))
        for line in list:
            self.assertTrue(line is not None)
            
    def test_translate(self):
        result = translate(text="мама", src="ru", to="en")
        self.assertEquals("mom", result)
    
if __name__ == '__main__':
    unittest.main()    

########NEW FILE########
__FILENAME__ = test_lfm_service
#-*- coding: utf-8 -*-
'''
Created on 21 нояб. 2010

@author: ivan
'''
import unittest
from foobnix.gui.service.lastfm_service import LastFmService
class TestLastFmService(unittest.TestCase):
    lfm = LastFmService(None)
        
    def test_find_disk_cover(self):
        url = self.lfm.get_album_image_url("Madonna", "Sorry")
        self.assertTrue(url.startswith("http://")) 
    
        
    def test_find_top_tracks(self):
        list = self.lfm.search_top_tracks("Madonna")
        self.assertEquals(50, len(list))        
        for bean in list:
            self.assertTrue(bean.text)
            
        
    
if __name__ == '__main__':
    unittest.main()    

########NEW FILE########
__FILENAME__ = test_pylast
'''
Created on Nov 9, 2013

@author: ivan
'''
import unittest
from foobnix.thirdparty import pylast
from foobnix.fc.fc_base import FCBase
from foobnix.thirdparty.pylast import Artist

API_KEY = FCBase().API_KEY
API_SECRET = FCBase().API_SECRET
username = FCBase().lfm_login
password_hash = pylast.md5(FCBase().lfm_password)

class Test(unittest.TestCase):

    def test_pylast(self):
        network = pylast.get_lastfm_network(api_key=API_KEY,
                                                     api_secret=API_SECRET,
                                                     username=username,
                                                     password_hash=password_hash)
        artist = network.get_artist("Madonna");
        summary = artist.get_bio_summary()
        print "========="
        print summary


########NEW FILE########
__FILENAME__ = test_sorting
'''
Created on Jan 16, 2011

@author: ivan
'''
import unittest
from foobnix.util.list_utils import sort_by_song_name
class Test(unittest.TestCase):

    def test_good_names(self):
        input = ["1.Enigma", "10.Bee", "11.Some", "2.KOT"]
        result = ["1.Enigma", "2.KOT", "10.Bee", "11.Some"]
        self.assertEquals(result, sort_by_song_name(input))
        
    def test_bad_name(self):
        input = ["a1.Enigma", "a10.Bee", "a11.Some", "a2.KOT"]
        result = ["a1.Enigma", "a10.Bee", "a11.Some", "a2.KOT"]
        self.assertEquals(result, sort_by_song_name(input))
        
    def test_bad_name_alpha(self):
        input = ["aEnigma", "cBee", "bSome", "dKOT"]
        result = ["aEnigma", "bSome", "cBee", "dKOT"]
        self.assertEquals(result, sort_by_song_name(input))
    
    def test_log_compare(self):        
        input = ["1234512345132316149982_b39e7d45e6_o1", "1234512345132316149981_b39e7d45e6_o1"]
        result = ["1234512345132316149982_b39e7d45e6_o1", "1234512345132316149981_b39e7d45e6_o1"]
        self.assertEquals(result, sort_by_song_name(input))

if __name__ == "__main__":
    #import sys;sys.argv = ['', 'Test.testName']
    unittest.main()

########NEW FILE########
__FILENAME__ = test_text_utils
#-*- coding: utf-8 -*-
import unittest
from foobnix.util.text_utils import smart_splitter, capitalize_string, \
    capitalize_query, split_string, normalize_text

class TestCapitalizeFunctions(unittest.TestCase):
    def test_capitalize_None(self):
        self.assertEquals(None, capitalize_string(None))
        self.assertEquals("", capitalize_string(""))
        
    def test_capitalize(self):
        self.assertEquals(u"Madonna Music", capitalize_string("MaDoNna MUSIC"))
        self.assertEquals(u"Madonna", capitalize_string("MaDoNna"))

class TestCapitalizeQueryFunctions(unittest.TestCase):
    def test_capitalize_None(self):
        self.assertEquals(None, capitalize_query(None))
        self.assertEquals("", capitalize_query(""))
        
    def test_capitalize_url(self):
        self.assertEquals(u"http://Madonna", capitalize_query("http://Madonna"))
    
    def test_capitalize_string(self):
        self.assertEquals(u"Ddt", capitalize_query("ddt"))
        self.assertEquals(u"DDT", capitalize_query("DDT"))
        self.assertEquals(u"DDT Music", capitalize_query("DDT music"))


class TestSplitterFunctions(unittest.TestCase):
    def setUp(self):
        self.input = "abcde 1234 w2e3"
    
    def test_empty_string(self):
        result = smart_splitter(None, 3)
        self.assertEquals(None, result)
        
    def test_empty_len(self):
        result = smart_splitter("100", None)
        self.assertEquals(["100"], result)
        
    def test_good_splitter(self):
        result = smart_splitter(self.input, 4)
        self.assertEquals(["abcde", "1234", "w2e3"], result)
    
    def test_good_splitter1(self):
        result = smart_splitter(self.input, 2)
        self.assertEquals(["abcde", "1234", "w2"], result)


class TestSplitStringFunction(unittest.TestCase):
    def setUp(self):
        self.input = "abcde,1234 w2    e3fdfd"
    
    def test_empty_string(self):
        result = split_string("", 3)
        self.assertEquals("", result)
        
    def test_empty_len(self):
        result = split_string("100", 3)
        self.assertEquals("100\n", result)
        
    def test_good_splitter(self):
        result = split_string(self.input, 10)
        self.assertEquals("abcde,\n1234 w2\ne3fdfd", result)
    
    def test_good_splitter1(self):
        result = split_string(self.input, 19)
        self.assertEquals("abcde,1234 w2\ne3fdfd", result)

class TestNormalizeFunctions(unittest.TestCase):
    def test_normalize_function(self):
        self.assertEquals(u"Madonna - Music", normalize_text("01 - Madonna - Music.mp3"))
        self.assertEquals(u"Madonna", normalize_text("Madonna.mp3"))
        self.assertEquals(u"Madonna", normalize_text("01 - Madonna [music].MP3"))
        self.assertEquals(u"Madonna - Music", normalize_text("01-Madonna - MUSIC.ogg"))
        self.assertEquals(u"Enigma - Sadeness Part", normalize_text("1.ENIGMA - SADENESS PART.mp3"))
        self.assertEquals(u"Similar Tracks - Give A Little More", normalize_text("Similar Tracks - Give A Little More *** www.ipmusic.ch ***"))
        self.assertEquals(u"Similar Feat. Tracks - Give A Little More", normalize_text("Similar feat. Tracks  - Give A Little More *** www.ipmusic.ch ***"))
        
        

if __name__ == '__main__':
    unittest.main()


########NEW FILE########
__FILENAME__ = test_time_utils
import unittest

from foobnix.util.time_utils import size2text, convert_seconds_to_text

class TestSize2Text(unittest.TestCase):
    def test_gigabyte(self):
        self.assertEquals('2.00 Gb', size2text(2*1024*1024*1024))
        self.assertEquals('2.20 Gb', size2text(2.2*1024*1024*1024))
    def test_megabyte(self):
        self.assertEquals('3.00 Mb', size2text(3*1024*1024))
        self.assertEquals('3.30 Mb', size2text(3.3*1024*1024))
    def test_kilobyte(self):
        self.assertEquals('4.00 Kb', size2text(4*1024))
        self.assertEquals('4.40 Kb', size2text(4.4*1024))

class TestConvertSecondsToText(unittest.TestCase):
    def check(self, expected, argument):
        self.assertEquals(expected, convert_seconds_to_text(argument))
    def test_zero(self):
        self.check('00:00', 0)
    def test_less_than_10_seconds(self):
        self.check('00:05', 5)
    def test_less_than_a_minute(self):
        self.check('00:55', 55)
    def test_less_than_10_minutes(self):
        self.check('05:45', 5*60+45)
    def test_less_than_an_hour(self):
        self.check('35:42', 35*60+42)
    def test_more_than_an_hour(self):
        self.check('3:35:42', 3*60*60+35*60+42)

########NEW FILE########
__FILENAME__ = test_version

import unittest
from foobnix.util.version import compare_versions
class TestNormalizeFunctions(unittest.TestCase):
    def test_normalize_function(self):
        self.assertEquals(0, compare_versions("","0.2.5-10"))
        self.assertEquals(0, compare_versions("",None))
        self.assertEquals(0, compare_versions("12312",""))
        self.assertEquals(0, compare_versions("0.2.5-10","0.2.5-10"))
        self.assertEquals(-1, compare_versions("0.2.5-10","0.2.5-1"))
        self.assertEquals(-1, compare_versions("0.2.5-10","0.2.5"))
        self.assertEquals(1, compare_versions("0.2.5-10","0.2.5-11"))
        self.assertEquals(-1, compare_versions("0.2.5-11","0.2.5-1"))
        self.assertEquals(-1, compare_versions("0.2.5-10","0.2.5-9"))
        self.assertEquals(1, compare_versions("0.2.5-9","0.2.5-10"))
        #self.assertEquals(0, compare_versions("0.2.5","0.2.5-0"))
        #self.assertEquals(1, compare_versions("0.2.3-9","0.2.5-0"))
        self.assertEquals(0, compare_versions("0.2.5-10","2.5.10"))
        self.assertEquals(1, compare_versions("0.2.5-9","2.5.10"))
        
        
        

if __name__ == '__main__':
    unittest.main()
########NEW FILE########
__FILENAME__ = test_vk_api
from foobnix.gui.service.vk_service import VKService
from foobnix.fc.fc_base import FCBase
FCBase().vk_login, FCBase().vk_password = "ivan.ivanenko@gmail.com",""
vk_service = VKService(True)
i =0
for line in vk_service.api.get("video.get", uid=6851750):
    i+=1
    if line ==25:
        continue
    print line['title'] 
    print line['image']
    print line['link']
    print line
    print i
    if i==3:
        break
    


########NEW FILE########
__FILENAME__ = test_vk_service
#-*- coding: utf-8 -*-
'''
Created on 21 нояб. 2010

@author: ivan
'''
import unittest
from foobnix.gui.service.vk_service import VKService
from foobnix.util.url_utils import get_url_type

class TestVKService(unittest.TestCase):
    vk_service = VKService(True)
    
    def test_login(self):
        self.assertTrue(self.vk_service.is_connected())

    def test_search_page(self):
        self.assertTrue(self.vk_service.search("Madonna").find("Madonna") > -1)

    def test_find_videos(self):
        list = self.vk_service.find_videos_by_query("Мадонна")
        for bean in list[:10]:
            self.assertNotEquals("text/html", get_url_type(bean.path))
            self.assertTrue(bean.path.startswith("http://")) 
        
    def test_find_track(self):
        bean = self.vk_service.find_one_track("Мадонна")        
        self.assertTrue(bean.path.startswith("http://"))
    
    def test_bad_link_track(self):
        beans = self.vk_service.find_videos_by_query("akon-cry out of jou(michael jackson tribute")
        "http://cs12907.vkontakte.ru/u87507380/video/bee60bc871.240.mp4"
        path = beans[0].path
        self.assertNotEquals("text/html", get_url_type(path))
                    
    def test_find_by_url(self):
        list = self.vk_service.find_tracks_by_url("http://vkontakte.ru/audio.php?gid=2849#album_id=0&gid=2849&id=0&offset=200")        
        for bean in list:
            self.assertTrue(bean.path.startswith("http://"))
   
    def test_find_by_url_user(self):
        list = self.vk_service.find_tracks_by_url("http://vkontakte.ru/audio.php?id=14775382")        
        for bean in list:
            self.assertFalse('\">' in bean.text)
            self.assertTrue(bean.path.startswith("http://"))

if __name__ == '__main__':
    unittest.main()
   
    


########NEW FILE########
