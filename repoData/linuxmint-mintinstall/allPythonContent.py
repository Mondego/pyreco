__FILENAME__ = AptClient
# AptControl.py
# -*- Mode: Python; indent-tabs-mode: nil; tab-width: 4; coding: utf-8 -*-

import apt, apt.progress.base, logging, threading, gobject, time, sys, os
from EventsObject import EventsObject
from ThreadedVar import ThreadedVar

class AptInstallProgressMonitor(apt.progress.base.InstallProgress):
    def __init__(self, thread):
        apt.progress.base.InstallProgress.__init__(self)
        self._thread = thread
        
    def status_change(self, pkg, percent, status):
        if self._thread.task_type == "install":
            self._thread.status.set_value((50 + percent / 2., status))
        else:
            self._thread.status.set_value((percent, status))
        self._thread.status_changed.set()
        
class AptAcquireProgressMonitor(apt.progress.base.AcquireProgress):
    def __init__(self, thread):
        apt.progress.base.AcquireProgress.__init__(self)
        self._thread = thread
        
    def pulse(self, owner):
        percent = 100. * self.current_bytes / self.total_bytes
        self._thread.status.set_value((percent / 2., "downloading"))
        self._thread.status_changed.set()
        return True
    
    def start(self):
        self._thread.status.set_value((0, ""))
        self._thread.status_changed.set()

class AptThread(threading.Thread, EventsObject):
    def __init__(self, task_id, task_type, **params):
        EventsObject.__init__(self)
        threading.Thread.__init__(self, None, self._run, None, (task_type,), params)
        
        self.task_id = task_id
        
        self.ended = threading.Event()
        self.success = threading.Event()
        self.status_changed = threading.Event()
        
        self.error = ThreadedVar(None)
        self.status = ThreadedVar(None)
        self.task_type = task_type
        self.params = params
    
    def _run(self, task_type, **params):
        logging.debug("Starting %s thread with params %s" % (task_type, params))
        
        try:
            if task_type == "install":
                acquire_progress_monitor = AptAcquireProgressMonitor(self)
                install_progress_monitor = AptInstallProgressMonitor(self)
                cache = apt.Cache()
                cache[params["package_name"]].mark_install()
                cache.commit(acquire_progress_monitor, install_progress_monitor)
            elif task_type == "remove":
                acquire_progress_monitor = AptAcquireProgressMonitor(self)
                install_progress_monitor = AptInstallProgressMonitor(self)
                cache = apt.Cache()
                cache[params["package_name"]].mark_delete()
                cache.commit(acquire_progress_monitor, install_progress_monitor)
            elif task_type == "update_cache":
                cache = apt.Cache()
                cache.update()
            elif task_type == "wait":
                # Debugging task
                time.sleep(params["delay"])
            else:
                print "Don't know what to do for task type : " + task_type
            self.success.set()
        except:
            error = sys.exc_info()[1]
            logging.error("Error during %s task with params %s : %s" % (task_type, params, str(error)))
            self.error.set_value(error)
        
        logging.debug("End of %s thread with params %s" % (task_type, params))
        
        self.ended.set()

class AptClient(EventsObject):
    def __init__(self):
        EventsObject.__init__(self)
        
        self._init_debconf()
        
        logging.debug("Initializing cache")
        self._cache = apt.Cache()
        
        self._tasks = {}
        self._queue = []
        self._task_id = 0
        self._queue_lock = threading.Lock()
        self._completed_operations_count = 0
        
        self._running = False
        self._running_lock = threading.Lock()
        
        self._apt_thread = None
    
    def _init_debconf(self):
        # Need to find a way to detect available frontends and use the appropriate fallback
        # Should we implement a custom debconf frontend for better integration ?
        os.putenv("DEBIAN_FRONTEND", "gnome")
    
    def update_cache(self):
        return self._queue_task("update_cache")
    
    def _queue_task(self, task_type, **params):
        logging.debug("Queueing %s task with params %s" % (task_type, str(params)))
        
        self._queue_lock.acquire()
        
        self._task_id += 1
        self._tasks[self._task_id] = (task_type, params)
        self._queue.append(self._task_id)
        res = self._task_id
        
        self._queue_lock.release()
        
        self._process_queue()
        
        return res
    
    def cancel_task(self, task_id):
        self._queue_lock.acquire()
        if task_id in self._tasks:
            i = self._queue.index(task_id)
            del self._queue[i]
            del self._tasks[task_id]
        self._queue_lock.release()
    
    def _process_task(self, task_id, task_type, **params):
        logging.debug("Processing %s task with params %s" % (task_type, str(params)))
        
        self._apt_thread = AptThread(task_id, task_type, **params)
        gobject.timeout_add(100, self._watch_thread)
        self._apt_thread.start()
    
    def _watch_thread(self):
        if self._apt_thread.ended.is_set():
            self._running_lock.acquire()
            self._running = False
            self._running_lock.release()
            
            self._completed_operations_count += 1
            
            self._trigger("task_ended", self._apt_thread.task_id, self._apt_thread.task_type, self._apt_thread.params, self._apt_thread.success.is_set(), self._apt_thread.error.get_value())
            self._process_queue()
            
            return False
        else:
            if self._apt_thread.status_changed.is_set():
                progress, status = self._apt_thread.status.get_value()
                self._trigger("progress", self._apt_thread.task_id, self._apt_thread.task_type, self._apt_thread.params, progress, status)
                self._apt_thread.status_changed.clear()
            return True
    
    def _process_queue(self):
        self._running_lock.acquire()
        
        if not self._running:
            self._queue_lock.acquire()
            
            queue_empty = False
            
            if len(self._queue) > 0:
                task_id = self._queue[0]
                task_type, params = self._tasks[task_id]
                del self._queue[0]
                del self._tasks[task_id]
            else:
                task_id = None
                self._trigger("idle")
                
            self._queue_lock.release()
            
            if task_id != None:
                self._running = True
                self._process_task(task_id, task_type, **params)
            else:
                self._completed_operations_count = 0
            
        self._running_lock.release()
    
    def install_package(self, package_name):
        return self._queue_task("install", package_name = package_name)
    
    def remove_package(self, package_name):
        return self._queue_task("remove", package_name = package_name)
    
    def wait(self, delay):
        # Debugging task
        return self._queue_task("wait", delay = delay)
    
    def get_progress_info(self):
        res = {"tasks": []}
        self._running_lock.acquire()
        self._queue_lock.acquire()
        nb_tasks = len(self._queue)
        total_nb_tasks = len(self._queue) + self._completed_operations_count
        if self._running:
            nb_tasks += 1
            total_nb_tasks += 1
            task_perc = 100. / total_nb_tasks
            task_progress, status = self._apt_thread.status.get_value()
            task_progress = min(task_progress, 99) # Do not show 100% when the task isn't completed
            progress = (100. * self._completed_operations_count + task_progress) / total_nb_tasks
            res["tasks"].append({"role": self._apt_thread.task_type, "status": status, "progress": task_progress, "task_id": self._apt_thread.task_id, "task_params": self._apt_thread.params, "cancellable": False})
        else:
            if total_nb_tasks > 0:
                task_perc = 100. / total_nb_tasks
                progress = (100. * self._completed_operations_count) / total_nb_tasks
            else:
                progress = 0
        for task_id in self._queue:
            task_type, params = self._tasks[task_id]
            res["tasks"].append({"role": task_type, "progress": 0, "task_id": task_id, "task_params": params, "status": "waiting", "cancellable": True})
        self._queue_lock.release()
        self._running_lock.release()
        res["nb_tasks"] = nb_tasks
        res["progress"] = progress
        return res
    
    def call_on_completion(self, callback, *args):
        self._running_lock.acquire()
        self._queue_lock.acquire()
        if self._running or len(self._queue) > 0:
            self.connect("idle", lambda client, *a: callback(*a), *args)
        else:
            callback(*args)
        self._queue_lock.release()
        self._running_lock.release()

########NEW FILE########
__FILENAME__ = EventsObject
# EventsObject.py
# -*- Mode: Python; indent-tabs-mode: nil; tab-width: 4; coding: utf-8 -*-

class EventsObject(object):
    def __init__(self):
        self._events = {}
        self._event_id = 0
        self._events_map = {}
    def connect(self, event, callback, *params):
        if not event in self._events:
            self._events[event] = {}
        self._event_id += 1
        self._events[event][self._event_id] = (callback, params, self._event_id)
        self._events_map[self._event_id] = event
        return self._event_id
    def disconnect(self, event_id):
        if event_id in self._events_map.keys():
            event = self._events_map[event_id]
            if event in self._events.keys() and event_id in self._events[event].keys():
                del self._events[event][event_id]
    def _trigger(self, event, *params):
        if event in self._events.keys():
            for callback, def_params, event_id in self._events[event].values():
                callback(*((self,) + params + def_params))

########NEW FILE########
__FILENAME__ = test
#! /usr/bin/python
# test.py
# -*- Mode: Python; indent-tabs-mode: nil; tab-width: 4; coding: utf-8 -*-

from AptClient import AptClient
import gtk, logging, gobject

class TestApp(object):
    def __init__(self):
        self._apt_client = AptClient()
        self._apt_client.connect("idle", lambda c: gtk.main_quit())
        self._apt_client.connect("task_ended", self._on_task_ended)
        self._apt_client.connect("progress", self._on_progress)
    
    def _on_progress(self, apt_client, progress, status):
        print "_on_progress:", progress, status
    
    def _on_task_ended(self, apt_client, task_id, task_type, task_params, success, error):
        print "\t\t_on_task_ended : ", apt_client, task_id, task_type, task_params, success, error
    
    def _start_tasks(self):
        #self._apt_client.update_cache()
        self._apt_client.install_package("phpmyadmin")
        #self._apt_client.install_package("gedit")
        #self._apt_client.install_package("gnome-xcf-thumbnailer")
        return False
    
    def run(self):
        gobject.threads_init()
        gobject.timeout_add(100, self._start_tasks)
        gtk.main()

if __name__ == "__main__":
    logging.getLogger().setLevel(logging.FATAL)
    
    TestApp().run()

########NEW FILE########
__FILENAME__ = ThreadedVar
#! /usr/bin/python
# -*- coding=utf-8 -*-

import threading

class ThreadedVar(object):
    def __init__(self, value = None):
        self._value = value
        self._lock = threading.Lock()
    
    def get_value(self):
        self._lock.acquire()
        res = self._value
        self._lock.release()
        return res
    
    def set_value(self, value):
        self._lock.acquire()
        self._value = value
        self._lock.release()

########NEW FILE########
__FILENAME__ = Classes
class Model:
	portals = []
	selected_category = None
	selected_application = None
	keyword = ""	
	packages_to_install = []
	packages_to_remove = []
	filter_applications = "all"

	def __init__(self):
		portals = []
		selected_category = None
		selected_application = None
		keyword = ""		
		packages_to_install = []
		packages_to_remove = []
		filter_applications = "all"

class Portal:
	key = ""
	name = ""
	link = ""
	release = ""
	release_name = ""
	update_url = ""
	categories = []
	items = []
	reviews = []

	def __init__(self, key, name="", link="", release="", release_name="", update_url=""):
		self.key = key
		self.name = name
		self.link = link
		self.release = release
		self.release_name = release_name
		self.update_url = update_url
		self.categories = []
		self.items = []
		self.reviews = []

	def find_category(self, key):
		for category in self.categories:
			if category.key == key:
				return category
		return None

	def find_item(self, key):
		for item in self.items:
			if item.key == key:
				return item
		return None

class Category:
	key = ""
	portal = None	
	name = ""
	description = ""
	vieworder = 0
	parent = None	
	subcategories = []
	items = []
	logo = None

	def __init__(self, portal, key, name="", description="", vieworder=0, parent=None, logo=None):
		self.key = key
		self.name = name
		self.description = description
		self.vieworder = vieworder
		self.parent = parent
		self.portal = portal
		self.subcategories = []
		self.items = []
		self.logo = logo

	def add_subcategory(self, category):
		self.subcategories.append(category)
		category.parent = self
	
	def add_item(self, item):
		self.items.append(item)
		item.category = self

class Item:
	key=""
	portal=None
	link=""
	mint_file=""
	category=""
	name=""
	description=""
	long_description=""
	added=""
	views=""
	license=""
	size=""
	website=""
	repository=""
	average_rating=""
	score = 0
	screenshot=None
	screenshot_url=None
	reviews = []	
	packages = []
	repositories = []
	is_special = True
	status = "installed"
	version = ""

	def __init__(self, portal, key, link="", mint_file="", category="", name="", description="", long_description="", added="", views="", license="", size="", website="", repository="", average_rating=""):
		self.portal=portal
		self.key=key
		self.link=link
		self.mint_file=mint_file
		self.category=category
		self.name=name
		self.description=description
		self.long_description=long_description
		self.added=added
		self.views=views
		self.license=license
		self.size=size
		self.website=website
		self.repository=repository
		self.average_rating=average_rating
		self.screenshot=None
		self.screenshot_url=None
		self.score = 0
		self.reviews = []
		self.packages = []
		self.repositories = []
		self.is_special = True
		self.status = "installed"
		self.version = ""

	def add_review(self, review):
		self.reviews.append(review)
		review.item = self

class Review:
	portal=None
	user_id = ""
	username = ""
	item = None
	comment = ""
	rating = 3

	def __init__(self, portal, item, rating, comment, user_id, username):
		self.portal=portal
		self.item=item
		self.rating=rating
		self.comment=comment
		self.user_id=user_id
		self.username=username


########NEW FILE########
__FILENAME__ = frontend
#!/usr/bin/python

import urllib
import Classes
from xml.etree import ElementTree as ET
from user import home
import os
import commands
import gtk
import gtk.glade
import pygtk
import sys
import threading
import gettext
import tempfile
pygtk.require("2.0")

from subprocess import Popen, PIPE

gtk.gdk.threads_init()

# i18n
gettext.install("mintinstall", "/usr/share/linuxmint/locale")

# i18n for menu item
menuName = _("Software Manager")
menuComment = _("Install new applications")

architecture = commands.getoutput("uname -a")
if (architecture.find("x86_64") >= 0):
	import ctypes
	libc = ctypes.CDLL('libc.so.6')
	libc.prctl(15, 'mintInstall', 0, 0, 0)	
else:
	import dl
	libc = dl.open('/lib/libc.so.6')
	libc.call('prctl', 15, 'mintInstall', 0, 0, 0)

global cache
import apt
cache = apt.Cache()
global num_apps
num_apps = 0

def close_application(window, event=None):	
	gtk.main_quit()
	sys.exit(0)

def close_window(widget, window):	
	window.hide_all()

def show_item(selection, model, wTree, username):
	(model_applications, iter) = selection.get_selected()
	if (iter != None):
		wTree.get_widget("button_install").hide()
		wTree.get_widget("button_remove").hide()
		wTree.get_widget("button_cancel_change").hide()
		wTree.get_widget("label_install").set_text(_("Install"))
		wTree.get_widget("label_install").set_tooltip_text("")
		wTree.get_widget("label_remove").set_text(_("Remove"))
		wTree.get_widget("label_remove").set_tooltip_text("")
		wTree.get_widget("label_cancel_change").set_text(_("Cancel change"))
		wTree.get_widget("label_cancel_change").set_tooltip_text("")
		selected_item = model_applications.get_value(iter, 5)
		model.selected_application = selected_item		
		if selected_item.version == "":
			wTree.get_widget("label_name").set_text("<b>" + selected_item.name + "</b>")
			wTree.get_widget("label_name").set_tooltip_text(selected_item.name)
		else:
			version = selected_item.version.split("+")[0]
			version = version.split("-")[0]
			wTree.get_widget("label_name").set_text("<b>" + selected_item.name + "</b> [" + version + "]")
			wTree.get_widget("label_name").set_tooltip_text(selected_item.name + " [" + selected_item.version + "]")		
		wTree.get_widget("label_name").set_use_markup(True)
		wTree.get_widget("label_description").set_text("<i>" + selected_item.description + "</i>")
		wTree.get_widget("label_description").set_use_markup(True)		
		str_size = str(selected_item.size) + _("MB")		
		if selected_item.size == "0" or selected_item.size == 0:						
			str_size = "--"
		wTree.get_widget("image_screenshot").clear()
		if (selected_item.screenshot != None):
			if (os.path.exists(selected_item.screenshot)):
				try:
					wTree.get_widget("image_screenshot").set_from_pixbuf(gtk.gdk.pixbuf_new_from_file_at_size(selected_item.screenshot, 200, 200))
				except Exception, detail:
					print detail
			else:							
				downloadScreenshot = DownloadScreenshot(selected_item, wTree, model)
				downloadScreenshot.start()				
			
		tree_reviews = wTree.get_widget("tree_reviews")
		model_reviews = gtk.TreeStore(str, int, str, object)
		for review in selected_item.reviews:
			iter = model_reviews.insert_before(None, None)						
			model_reviews.set_value(iter, 0, review.username)						
			model_reviews.set_value(iter, 1, review.rating)
			model_reviews.set_value(iter, 2, review.comment)
			model_reviews.set_value(iter, 3, review)
		model_reviews.set_sort_column_id( 1, gtk.SORT_DESCENDING )
		tree_reviews.set_model(model_reviews)	

		first = model_reviews.get_iter_first()
		if (first != None):
			tree_reviews.get_selection().select_iter(first)
			tree_reviews.scroll_to_cell(model_reviews.get_path(first))
					
		del model_reviews			
		if selected_item.is_special:
			wTree.get_widget("button_install").show()
		else:
			if selected_item.status == "available":
				wTree.get_widget("button_install").show()
			elif selected_item.status == "installed": 					
				wTree.get_widget("button_remove").show()
			elif selected_item.status == "add":
				wTree.get_widget("button_cancel_change").show()
				wTree.get_widget("label_cancel_change").set_text(_("Cancel installation"))
 			elif selected_item.status == "remove":
				wTree.get_widget("button_cancel_change").show()
				wTree.get_widget("label_cancel_change").set_text(_("Cancel removal"))

	update_statusbar(wTree, model)

def show_category(selection, model, wTree):	
	(model_categories, iter) = selection.get_selected()
	if (iter != None):
		selected_category = model_categories.get_value(iter, 1)
		model.selected_category = selected_category
		show_applications(wTree, model, True)					

def filter_search(widget, wTree, model):
	keyword = widget.get_text()
	model.keyword = keyword
	show_applications(wTree, model, True)	

def open_search(widget, username):
	os.system("/usr/lib/linuxmint/mintInstall/mintInstall.py " + username + " &")

def open_featured(widget):
	gladefile = "/usr/lib/linuxmint/mintInstall/frontend.glade"
	wTree = gtk.glade.XML(gladefile, "featured_window")
	treeview_featured = wTree.get_widget("treeview_featured")
	wTree.get_widget("featured_window").set_title(_("Featured applications"))
	wTree.get_widget("featured_window").set_icon_from_file("/usr/lib/linuxmint/mintInstall/icon.svg")	
	wTree.get_widget("button_close").connect("clicked", close_window, wTree.get_widget("featured_window"))
	wTree.get_widget("button_apply").connect("clicked", install_featured, wTree, treeview_featured, wTree.get_widget("featured_window"))		
	wTree.get_widget("featured_window").show_all()	

	wTree.get_widget("lbl_intro").set_label(_("These popular applications can be installed on your system:"))

	# the treeview 
	cr = gtk.CellRendererToggle()
	cr.connect("toggled", toggled, treeview_featured)
	column1 = gtk.TreeViewColumn(_("Install"), cr)
	column1.set_cell_data_func(cr, celldatafunction_checkbox)
	column1.set_sort_column_id(1)
	column1.set_resizable(True)  
	column2 = gtk.TreeViewColumn(_("Application"), gtk.CellRendererText(), text=2)
	column2.set_sort_column_id(2)
	column2.set_resizable(True)  
	column3 = gtk.TreeViewColumn(_("Icon"), gtk.CellRendererPixbuf(), pixbuf=3)
	column3.set_sort_column_id(3)
	column3.set_resizable(True)  	
	column4 = gtk.TreeViewColumn(_("Description"), gtk.CellRendererText(), text=4)
	column4.set_sort_column_id(4)
	column4.set_resizable(True)  
	column5 = gtk.TreeViewColumn(_("Size"), gtk.CellRendererText(), text=5)
	column5.set_sort_column_id(5)
	column5.set_resizable(True)  

	treeview_featured.append_column(column1)
	treeview_featured.append_column(column3)
	treeview_featured.append_column(column2)
	treeview_featured.append_column(column4)
	treeview_featured.append_column(column5)
	treeview_featured.set_headers_clickable(False)
	treeview_featured.set_reorderable(False)
	treeview_featured.show()

	model = gtk.TreeStore(str, str, str, gtk.gdk.Pixbuf, str, str)
	import string
	applications = open("/usr/share/linuxmint/mintinstall/featured_applications/list.txt", "r")
	for application in applications:
		application = application.strip()
		application_details = string.split(application, "=")
		if len(application_details) == 3:
			application_pkg = application_details[0]
			application_name = application_details[1]
			application_icon = application_details[2]			
			try:
				global cache
				pkg = cache[application_pkg]
				
				if ((not pkg.is_installed) and (pkg.candidate.summary != "")):
					strSize = str(pkg.candidate.size) + _("B")
					if (pkg.candidate.size >= 1000):
						strSize = str(pkg.candidate.size / 1000) + _("KB")
					if (pkg.candidate.size >= 1000000):
						strSize = str(pkg.candidate.size / 1000000) + _("MB")
					if (pkg.candidate.size >= 1000000000):
						strSize = str(pkg.candidate.size / 1000000000) + _("GB")
					iter = model.insert_before(None, None)						
					model.set_value(iter, 0, application_pkg)
					model.set_value(iter, 1, "false")
					model.set_value(iter, 2, application_name)
					model.set_value(iter, 3, gtk.gdk.pixbuf_new_from_file("/usr/share/linuxmint/mintinstall/featured_applications/" + application_icon))						
					model.set_value(iter, 4, pkg.candidate.summary)
					model.set_value(iter, 5, strSize)

			except Exception, detail:
				#Package isn't in repositories
				print detail				

	treeview_featured.set_model(model)
	del model

def install_featured(widget, wTree, treeview_featured, window):
	vbox = wTree.get_widget("vbox1")
	socket = gtk.Socket()
	vbox.pack_start(socket)
	socket.show()
	window_id = repr(socket.get_id())	
	command = "gksu mint-synaptic-install " + window_id
	model = treeview_featured.get_model()
	iter = model.get_iter_first()
	while iter != None:
		if (model.get_value(iter, 1) == "true"):
			pkg = model.get_value(iter, 0)
			command = command + " " + pkg
		iter = model.iter_next(iter)	
	os.system(command)
	close_window(widget, window)

def toggled(renderer, path, treeview):
    model = treeview.get_model()
    iter = model.get_iter(path)
    if (iter != None):
	    checked = model.get_value(iter, 1)
	    if (checked == "true"):
		model.set_value(iter, 1, "false")
	    else:
		model.set_value(iter, 1, "true")

def celldatafunction_checkbox(column, cell, model, iter):
        cell.set_property("activatable", True)
	checked = model.get_value(iter, 1)
	if (checked == "true"):
		cell.set_property("active", True)
	else:
		cell.set_property("active", False)

def show_screenshot(widget, model):
	#Set the Glade file
	if model.selected_application != None:		
		gladefile = "/usr/lib/linuxmint/mintInstall/frontend.glade"
		wTree = gtk.glade.XML(gladefile, "screenshot_window")
		wTree.get_widget("screenshot_window").set_title(model.selected_application.name)
		wTree.get_widget("screenshot_window").set_icon_from_file("/usr/lib/linuxmint/mintInstall/icon.svg")
		wTree.get_widget("screenshot_window").connect("delete_event", close_window, wTree.get_widget("screenshot_window"))
		wTree.get_widget("button_screen_close").connect("clicked", close_window, wTree.get_widget("screenshot_window"))
		wTree.get_widget("image_screen").set_from_pixbuf(gtk.gdk.pixbuf_new_from_file(model.selected_application.screenshot))	
		wTree.get_widget("button_screen").connect("clicked", close_window, wTree.get_widget("screenshot_window"))	
		wTree.get_widget("screenshot_window").show_all()

def fetch_apt_details(model):
	global cache	
	if os.path.exists("/usr/share/linuxmint/mintinstall/data/details/packages.list"):
		packagesFile = open("/usr/share/linuxmint/mintinstall/data/details/packages.list", "r")
		lines = packagesFile.readlines()
		for line in lines:
			items = line.strip().split()
			key = items[0]
			packages = items[1:]
			item = None
			for portal in model.portals:
				if item is None:
					item = portal.find_item(key)
			if item is not None:	
				item.status = "installed"			
				for package in packages:
					try:
						pkg = cache[package]
						if not pkg.is_installed:
							item.status = "available"
							item.version = pkg.candidate.version
						else:
							item.version = pkg.installed.version
						item.packages.append(pkg)
						item.is_special = False
						item.long_description = pkg.candidate.raw_description
					except Exception, details: 
						print details
			packagesFile.close()											

def show_more_info_wrapper(widget, path, column, model):
	show_more_info(widget, model)

def show_more_info(widget, model):
	if model.selected_application != None:
		if not os.path.exists((model.selected_application.mint_file)):			
			os.system("zenity --error --text=\"" + _("The mint file for this application was not successfully downloaded. Click on refresh to fix the problem.") + "\"")
		else:
			directory = home + "/.linuxmint/mintInstall/tmp/mintFile"
			os.system("mkdir -p " + directory)
			os.system("rm -rf " + directory + "/*") 
			os.system("cp " + model.selected_application.mint_file + " " + directory + "/file.mint")
			os.system("tar zxf " + directory + "/file.mint -C " + directory)
			steps = int(commands.getoutput("ls -l " + directory + "/steps/ | wc -l"))
			steps = steps -1
			repositories = []
			packages = []
			for i in range(steps + 1):
				if (i > 0):			
					openfile = open(directory + "/steps/"+str(i), 'r' )
				        datalist = openfile.readlines()
					for j in range( len( datalist ) ):
					    if (str.find(datalist[j], "INSTALL") > -1):
						install = datalist[j][8:]
						install = str.strip(install)
						packages.append(install)
					    if (str.find(datalist[j], "SOURCE") > -1):
						source = datalist[j][7:]
						source = source.rstrip()
						self.repositories.append(source)	
					openfile.close()
			gladefile = "/usr/lib/linuxmint/mintInstall/frontend.glade"
			wTree = gtk.glade.XML(gladefile, "more_info_window")
			wTree.get_widget("more_info_window").set_title(model.selected_application.name)
			wTree.get_widget("more_info_window").set_icon_from_file("/usr/lib/linuxmint/mintInstall/icon.svg")
			wTree.get_widget("button_versions_close").connect("clicked", close_window, wTree.get_widget("more_info_window"))

			tree_repositories = wTree.get_widget("treeview_repositories")
			column1 = gtk.TreeViewColumn(_("Repository"), gtk.CellRendererText(), text=0)
			column1.set_sort_column_id(0)
			column1.set_resizable(True)
			tree_repositories.append_column(column1)
			tree_repositories.set_headers_clickable(True)
			tree_repositories.set_reorderable(False)
			tree_repositories.show()
			model_repositories = gtk.TreeStore(str)
			if len(repositories) == 0:
				iter = model_repositories.insert_before(None, None)						
				model_repositories.set_value(iter, 0, _("Default repositories"))	
			for repository in repositories:				
				iter = model_repositories.insert_before(None, None)						
				model_repositories.set_value(iter, 0, repository)						
			model_repositories.set_sort_column_id( 0, gtk.SORT_ASCENDING )	
			tree_repositories.set_model(model_repositories)
			del model_repositories	

			tree_packages = wTree.get_widget("treeview_packages")
			column1 = gtk.TreeViewColumn(_("Package"), gtk.CellRendererText(), text=0)
			column1.set_sort_column_id(0)
			column1.set_resizable(True)
			column2 = gtk.TreeViewColumn(_("Installed version"), gtk.CellRendererText(), text=1)
			column2.set_sort_column_id(1)
			column2.set_resizable(True)
			column3 = gtk.TreeViewColumn(_("Available version"), gtk.CellRendererText(), text=2)
			column3.set_sort_column_id(2)
			column3.set_resizable(True)
			column4 = gtk.TreeViewColumn(_("Size"), gtk.CellRendererText(), text=3)
			column4.set_sort_column_id(3)
			column4.set_resizable(True)
			tree_packages.append_column(column1)
			tree_packages.append_column(column2)
			tree_packages.append_column(column3)
			tree_packages.append_column(column4)
			tree_packages.set_headers_clickable(True)
			tree_packages.set_reorderable(False)
			tree_packages.show()
			model_packages = gtk.TreeStore(str, str, str, str)

			description = ""
			strSize = ""	
			for package in packages:
				installedVersion = ""
				candidateVersion = ""
				try:
					global cacke
					pkg = cache[package]
					description = pkg.candidate.raw_description
					if pkg.installed is not None:
						installedVersion = pkg.installed.version	
					if pkg.candidate is not None:
						candidateVersion = pkg.candidate.version				
					size = int(pkg.candidate.size)
					strSize = str(size) + _("B")
					if (size >= 1000):
						strSize = str(size / 1000) + _("KB")
					if (size >= 1000000):
						strSize = str(size / 1000000) + _("MB")
					if (size >= 1000000000):
						strSize = str(size / 1000000000) + _("GB")
				except Exception, detail:
					print detail			
				iter = model_packages.insert_before(None, None)						
				model_packages.set_value(iter, 0, package)
				model_packages.set_value(iter, 1, installedVersion)						
				model_packages.set_value(iter, 2, candidateVersion)
				model_packages.set_value(iter, 3, strSize)															
			model_packages.set_sort_column_id( 0, gtk.SORT_ASCENDING )		
			tree_packages.set_model(model_packages)
			del model_packages	

			wTree.get_widget("lbl_license").set_text(_("License:"))
			wTree.get_widget("lbl_homepage").set_text(_("Website") + ":")
			wTree.get_widget("lbl_portal").set_text(_("Portal URL") + ":")
			wTree.get_widget("lbl_description").set_text(_("Description:"))

			wTree.get_widget("txt_license").set_text(model.selected_application.license)
			wTree.get_widget("txt_description").set_text(description)
			wTree.get_widget("button_website").connect("clicked", visit_website, model, username)
			wTree.get_widget("button_website").set_label(model.selected_application.website)	
			wTree.get_widget("button_portal").connect("clicked", visit_web, model, username)
			wTree.get_widget("button_portal").set_label(model.selected_application.link)					
			wTree.get_widget("more_info_window").show_all()

def visit_web(widget, model, username):
	if model.selected_application != None:
		os.system("sudo -u " + username + " /usr/lib/linuxmint/common/launch_browser_as.py \"" + model.selected_application.link + "\"")	

def visit_website(widget, model, username):
	if model.selected_application != None:
		os.system("sudo -u " + username + " /usr/lib/linuxmint/common/launch_browser_as.py \"" + model.selected_application.website + "\"")		

def install(widget, model, wTree, username):	
	if model.selected_application != None:
		if model.selected_application.is_special:
			if not os.path.exists((model.selected_application.mint_file)):
				os.system("zenity --error --text=\"" + _("The mint file for this application was not successfully downloaded. Click on refresh to fix the problem.") + "\"")
			else:
				os.system("mintInstall " + model.selected_application.mint_file)
				show_item(wTree.get_widget("tree_applications").get_selection(), model, wTree, username)
				global cache
				cache = apt.Cache()
				show_applications(wTree, model, False)
		else:
			for package in model.selected_application.packages:
				if package not in model.packages_to_install:
					model.packages_to_install.append(package)
			model.selected_application.status = "add"
			wTree.get_widget("toolbutton_apply").set_sensitive(True)			
			model_applications, iter = wTree.get_widget("tree_applications").get_selection().get_selected()			
			model_applications.set_value(iter, 7, gtk.gdk.pixbuf_new_from_file("/usr/lib/linuxmint/mintInstall/status-icons/add.png"))		
			model_applications.set_value(iter, 8, 1)
			show_item(wTree.get_widget("tree_applications").get_selection(), model, wTree, username)
		

def remove(widget, model, wTree, username):
	if model.selected_application != None:
		if model.selected_application.is_special:
			if not os.path.exists((model.selected_application.mint_file)):
				os.system("zenity --error --text=\"" + _("The mint file for this application was not successfully downloaded. Click on refresh to fix the problem.") + "\"")
			else:
				os.system("/usr/lib/linuxmint/mintInstall/remove.py " + model.selected_application.mint_file)
				show_item(wTree.get_widget("tree_applications").get_selection(), model, wTree, username)
				global cache
				cache = apt.Cache()
				show_applications(wTree, model, False)
		else:
			for package in model.selected_application.packages:
				if package not in model.packages_to_remove:
					model.packages_to_remove.append(package)
			model.selected_application.status = "remove"
			wTree.get_widget("toolbutton_apply").set_sensitive(True)
			model_applications, iter = wTree.get_widget("tree_applications").get_selection().get_selected()			
			model_applications.set_value(iter, 7, gtk.gdk.pixbuf_new_from_file("/usr/lib/linuxmint/mintInstall/status-icons/remove.png"))		
			model_applications.set_value(iter, 8, 2)
			show_item(wTree.get_widget("tree_applications").get_selection(), model, wTree, username)

def cancel_change(widget, model, wTree, username):
	if model.selected_application != None:
		model_applications, iter = wTree.get_widget("tree_applications").get_selection().get_selected()
		if model.selected_application.status == "add":
			for package in model.selected_application.packages:
				if package in model.packages_to_install:
					model.packages_to_install.remove(package)
			model.selected_application.status = "available"
			model_applications.set_value(iter, 7, gtk.gdk.pixbuf_new_from_file("/usr/lib/linuxmint/mintInstall/status-icons/available.png"))		
			model_applications.set_value(iter, 8, 4)
		elif model.selected_application.status == "remove":
			for package in model.selected_application.packages:
				if package in model.packages_to_remove:
					model.packages_to_remove.remove(package)
			model.selected_application.status = "installed"
			model_applications.set_value(iter, 7, gtk.gdk.pixbuf_new_from_file("/usr/lib/linuxmint/mintInstall/status-icons/installed.png"))		
			model_applications.set_value(iter, 8, 3)

		if len(model.packages_to_install) == 0 and len(model.packages_to_remove) == 0:
			wTree.get_widget("toolbutton_apply").set_sensitive(False)

		show_item(wTree.get_widget("tree_applications").get_selection(), model, wTree, username)

def apply(widget, model, wTree, username):
	wTree.get_widget("main_window").window.set_cursor(gtk.gdk.Cursor(gtk.gdk.WATCH))
	wTree.get_widget("main_window").set_sensitive(False)
	cmd = ["sudo", "/usr/sbin/synaptic", "--hide-main-window", "--non-interactive"]
	cmd.append("--progress-str")
	cmd.append("\"" + _("Please wait, this can take some time") + "\"")
	cmd.append("--finish-str")
	cmd.append("\"" + _("The changes are complete") + "\"")
		
	f = tempfile.NamedTemporaryFile()

	for pkg in model.packages_to_install:				    
	    f.write("%s\tinstall\n" % pkg.name)		
	for pkg in model.packages_to_remove:				    
	    f.write("%s\tdeinstall\n" % pkg.name)				    

	cmd.append("--set-selections-file")
	cmd.append("%s" % f.name)
	f.flush()
	comnd = Popen(' '.join(cmd), shell=True)
	returnCode = comnd.wait()				
        #sts = os.waitpid(comnd.pid, 0)
	f.close()	

	model.packages_to_install = []
	model.packages_to_remove = []

	wTree.get_widget("main_window").window.set_cursor(None)
	wTree.get_widget("main_window").set_sensitive(True)
	wTree.get_widget("toolbutton_apply").set_sensitive(False)

	global cache
	cache = apt.Cache()

	fetch_apt_details(model)
	show_applications(wTree, model, True)
	

def show_applications(wTree, model, scrollback):	

	matching_statuses = []
	if model.filter_applications == "available":
		matching_statuses.append("available")
		matching_statuses.append("add")
		matching_statuses.append("special")
	elif model.filter_applications == "installed":
		matching_statuses.append("installed")	
		matching_statuses.append("remove")	
	elif model.filter_applications == "changes":
		matching_statuses.append("add")	
		matching_statuses.append("remove")	
	elif model.filter_applications == "all":
		matching_statuses.append("available")	
		matching_statuses.append("installed")	
		matching_statuses.append("special")	
		matching_statuses.append("add")	
		matching_statuses.append("remove")	
	global num_apps
	num_apps = 0
	category_keys = []
	if (model.selected_category == None): 
		#The All category is selected
		for portal in model.portals:			
			for category in portal.categories:
				category_keys.append(category.key)
	else:
		category_keys.append(model.selected_category.key)
		for subcategory in model.selected_category.subcategories:
			category_keys.append(subcategory.key)		

	tree_applications = wTree.get_widget("tree_applications")
	new_selection = None
	model_applications = gtk.TreeStore(str, str, int, int, str, object, int, gtk.gdk.Pixbuf, int)
	for portal in model.portals:
		for item in portal.items:	
			if (item.category.key in category_keys):
				if item.status in matching_statuses and (model.keyword == None 
					or item.name.upper().count(model.keyword.upper()) > 0
					or item.description.upper().count(model.keyword.upper()) > 0
					or item.long_description.upper().count(model.keyword.upper()) > 0):
					iter = model_applications.insert_before(None, None)						
					model_applications.set_value(iter, 0, item.name)						
					model_applications.set_value(iter, 1, item.average_rating)
					model_applications.set_value(iter, 2, len(item.reviews))
					model_applications.set_value(iter, 3, item.views)
					model_applications.set_value(iter, 4, item.added)
					model_applications.set_value(iter, 5, item)
					model_applications.set_value(iter, 6, float(item.average_rating) * len(item.reviews) + (item.views / 1000))
					if item.is_special:
						model_applications.set_value(iter, 7, gtk.gdk.pixbuf_new_from_file("/usr/lib/linuxmint/mintInstall/status-icons/special.png"))	
						model_applications.set_value(iter, 8, 9)

					else:	
						if item.status == "available":
							model_applications.set_value(iter, 7, gtk.gdk.pixbuf_new_from_file("/usr/lib/linuxmint/mintInstall/status-icons/available.png"))		
							model_applications.set_value(iter, 8, 4)				
						elif item.status == "installed":
							model_applications.set_value(iter, 7, gtk.gdk.pixbuf_new_from_file("/usr/lib/linuxmint/mintInstall/status-icons/installed.png"))
							model_applications.set_value(iter, 8, 3)
						elif item.status == "add":
							model_applications.set_value(iter, 7, gtk.gdk.pixbuf_new_from_file("/usr/lib/linuxmint/mintInstall/status-icons/add.png"))		
							model_applications.set_value(iter, 8, 1)
						elif item.status == "remove":
							model_applications.set_value(iter, 7, gtk.gdk.pixbuf_new_from_file("/usr/lib/linuxmint/mintInstall/status-icons/remove.png"))		
							model_applications.set_value(iter, 8, 2)

					if model.selected_application == item:						
						new_selection = iter
						
					num_apps = num_apps + 1
	model_applications.set_sort_column_id( 6, gtk.SORT_DESCENDING )
	tree_applications.set_model(model_applications)
	if scrollback: 
		first = model_applications.get_iter_first()
		if (first != None):
			tree_applications.get_selection().select_iter(first)
			tree_applications.scroll_to_cell(model_applications.get_path(first))
	else:
		if new_selection is not None:
			tree_applications.get_selection().select_iter(new_selection)
			tree_applications.scroll_to_cell(model_applications.get_path(new_selection))
	del model_applications
	update_statusbar(wTree, model)

def update_statusbar(wTree, model):
	global num_apps
	statusbar = wTree.get_widget("statusbar")
	context_id = statusbar.get_context_id("mintInstall")	
	statusbar.push(context_id,  _("%(applications)d applications listed, %(install)d to install, %(remove)d to remove") % {'applications':num_apps, 'install':len(model.packages_to_install), 'remove':len(model.packages_to_remove)})

def filter_applications(combo, wTree, model):
	combomodel = combo.get_model()
	comboindex = combo.get_active()
        model.filter_applications = combomodel[comboindex][1]
	show_applications(wTree, model, True)

def build_GUI(model, username):

	#Set the Glade file
	gladefile = "/usr/lib/linuxmint/mintInstall/frontend.glade"
	wTree = gtk.glade.XML(gladefile, "main_window")
	wTree.get_widget("main_window").set_title(_("Software Manager"))
	wTree.get_widget("main_window").set_icon_from_file("/usr/lib/linuxmint/mintInstall/icon.svg")
	wTree.get_widget("main_window").connect("delete_event", close_application)

	wTree.get_widget("image_screenshot").clear()

	#i18n
	wTree.get_widget("label5").set_text(_("Quick search:"))
	wTree.get_widget("label2").set_text(_("More info"))
	wTree.get_widget("label1").set_text(_("Show:"))
	wTree.get_widget("button_search_online").set_label(_("Search"))

	wTree.get_widget("lbl_featured").set_label(_("Featured applications"))	

	# Filter
	model.filter_applications = "all"
	combo = wTree.get_widget("filter_combo")
	store = gtk.ListStore(str, str)
	store.append([_("All software"), "all"])
	store.append([_("Available software"), "available"])
	store.append([_("Installed software"), "installed"])
	store.append([_("Your changes"), "changes"])
	combo.set_model(store)
	combo.set_active(0)
	combo.connect('changed', filter_applications, wTree, model)		

	# Build categories tree
	tree_categories = wTree.get_widget("tree_categories")	
	pix = gtk.CellRendererPixbuf()
	pix.set_property('xalign', 0.0)
	column1 = gtk.TreeViewColumn(_("Category"), pix, pixbuf=2)
	column1.set_alignment(0.0)
	cell = gtk.CellRendererText()
	column1.pack_start(cell, True)
	column1.add_attribute(cell, 'text', 0)
	cell.set_property('xalign', 0.1)
	
	tree_categories.append_column(column1)
	tree_categories.set_headers_clickable(True)
	tree_categories.set_reorderable(False)
	tree_categories.show()
	model_categories = gtk.TreeStore(str, object)	
	tree_categories.set_model(model_categories)
	del model_categories

	#Build applications table
	tree_applications = wTree.get_widget("tree_applications")
	column1 = gtk.TreeViewColumn(_("Application"), gtk.CellRendererText(), text=0)
	column1.set_sort_column_id(0)
	column1.set_resizable(True)

	column2 = gtk.TreeViewColumn(_("Average rating"), gtk.CellRendererText(), text=1)
	column2.set_sort_column_id(1)
	column2.set_resizable(True)

	column3 = gtk.TreeViewColumn(_("Reviews"), gtk.CellRendererText(), text=2)
	column3.set_sort_column_id(2)
	column3.set_resizable(True)

	column4 = gtk.TreeViewColumn(_("Views"), gtk.CellRendererText(), text=3)
	column4.set_sort_column_id(3)
	column4.set_resizable(True)

	column5 = gtk.TreeViewColumn(_("Added"), gtk.CellRendererText(), text=4)
	column5.set_sort_column_id(4)
	column5.set_resizable(True)

	column6 = gtk.TreeViewColumn(_("Score"), gtk.CellRendererText(), text=6)
	column6.set_sort_column_id(6)
	column6.set_resizable(True)

	column7 = gtk.TreeViewColumn(_("Status"), gtk.CellRendererPixbuf(), pixbuf=7)
	column7.set_sort_column_id(8)
	column7.set_resizable(True)

	tree_applications.append_column(column7)
	tree_applications.append_column(column6)
	tree_applications.append_column(column1)
	tree_applications.append_column(column2)
	tree_applications.append_column(column3)
	tree_applications.append_column(column4)
	tree_applications.append_column(column5)
	tree_applications.set_headers_clickable(True)
	tree_applications.set_reorderable(False)
	tree_applications.show()
	model_applications = gtk.TreeStore(str, int, int, int, str, object, int, gtk.gdk.Pixbuf, int)
	tree_applications.set_model(model_applications)
	del model_applications	

	tree_applications.connect("row_activated", show_more_info_wrapper, model)

	#Build reviews table
	tree_reviews = wTree.get_widget("tree_reviews")
	column1 = gtk.TreeViewColumn(_("Reviewer"), gtk.CellRendererText(), text=0)
	column1.set_sort_column_id(0)
	column1.set_resizable(True)

	column2 = gtk.TreeViewColumn(_("Rating"), gtk.CellRendererText(), text=1)
	column2.set_sort_column_id(1)
	column2.set_resizable(True)

	column3 = gtk.TreeViewColumn(_("Review"), gtk.CellRendererText(), text=2)
	column3.set_sort_column_id(2)
	column3.set_resizable(True)

	tree_reviews.append_column(column1)
	tree_reviews.append_column(column2)
	tree_reviews.append_column(column3)

	tree_reviews.set_headers_clickable(True)
	tree_reviews.set_reorderable(False)
	tree_reviews.show()
	model_reviews = gtk.TreeStore(str, int, str, object)
	tree_reviews.set_model(model_reviews)
	del model_reviews
	
	selection = tree_applications.get_selection()
	selection.connect("changed", show_item, model, wTree, username)

	entry_search = wTree.get_widget("entry_search")
	entry_search.connect("changed", filter_search, wTree, model)		
	
	wTree.get_widget("button_search_online").connect("clicked", open_search, username)
	wTree.get_widget("button_feature").connect("clicked", open_featured)				
	wTree.get_widget("button_screenshot").connect("clicked", show_screenshot, model)
	wTree.get_widget("button_install").connect("clicked", install, model, wTree, username)	
	wTree.get_widget("button_remove").connect("clicked", remove, model, wTree, username)
	wTree.get_widget("button_cancel_change").connect("clicked", cancel_change, model, wTree, username)		
	wTree.get_widget("button_show").connect("clicked", show_more_info, model)

	wTree.get_widget("toolbutton_apply").connect("clicked", apply, model, wTree, username)	

	fileMenu = gtk.MenuItem(_("_File"))
	fileSubmenu = gtk.Menu()
	fileMenu.set_submenu(fileSubmenu)
	closeMenuItem = gtk.ImageMenuItem(gtk.STOCK_CLOSE)
	closeMenuItem.get_child().set_text(_("Quit"))
	closeMenuItem.connect("activate", close_application)
	fileSubmenu.append(closeMenuItem)		
	closeMenuItem.show()

	editMenu = gtk.MenuItem(_("_Edit"))
	editSubmenu = gtk.Menu()
	editMenu.set_submenu(editSubmenu)
	cancelMenuItem = gtk.MenuItem(_("Cancel all changes"))
	cancelMenuItem.connect("activate", cancel_changes, wTree, model)
	editSubmenu.append(cancelMenuItem)		
	cancelMenuItem.show()

	helpMenu = gtk.MenuItem(_("_Help"))
	helpSubmenu = gtk.Menu()
	helpMenu.set_submenu(helpSubmenu)
	aboutMenuItem = gtk.ImageMenuItem(gtk.STOCK_ABOUT)
	aboutMenuItem.get_child().set_text(_("About"))
	aboutMenuItem.show()
	aboutMenuItem.connect("activate", open_about)
	helpSubmenu.append(aboutMenuItem)
        fileMenu.show()
	editMenu.show()
	helpMenu.show()
	wTree.get_widget("menubar1").append(fileMenu)
	wTree.get_widget("menubar1").append(editMenu)
	wTree.get_widget("menubar1").append(helpMenu)
	
	return wTree

def cancel_changes(widget, wTree, model):
	for portal in model.portals:
		for item in portal.items:
			if item.status == "add":
				item.status = "available"
			elif item.status == "remove":
				item.status = "installed"
	model.packages_to_install = []
	model.packages_to_remove = []
	wTree.get_widget("toolbutton_apply").set_sensitive(False)
	show_applications(wTree, model, True)

def open_about(widget):
	dlg = gtk.AboutDialog()		
	dlg.set_version(commands.getoutput("/usr/lib/linuxmint/common/version.py mintinstall"))
	dlg.set_name("mintInstall")
	dlg.set_comments(_("Software manager"))
        try:
            h = open('/usr/share/common-licenses/GPL','r')
            s = h.readlines()
	    gpl = ""
            for line in s:
                gpl += line
            h.close()
            dlg.set_license(gpl)
        except Exception, detail:
            print detail            
        dlg.set_authors(["Clement Lefebvre <root@linuxmint.com>"]) 
	dlg.set_icon_from_file("/usr/lib/linuxmint/mintInstall/icon.svg")
	dlg.set_logo(gtk.gdk.pixbuf_new_from_file("/usr/lib/linuxmint/mintInstall/icon.svg"))
        def close(w, res):
            if res == gtk.RESPONSE_CANCEL:
                w.hide()
        dlg.connect("response", close)
        dlg.show()

class DownloadScreenshot(threading.Thread):

	def __init__(self, selected_item, wTree, model):
		threading.Thread.__init__(self)
		self.selected_item = selected_item
		self.wTree = wTree
		self.model = model

	def run(self):
		try:
			import urllib
			urllib.urlretrieve (self.selected_item.screenshot_url, "/usr/share/linuxmint/mintinstall/data/screenshots/" + self.selected_item.key)
			gtk.gdk.threads_enter()
			if (self.model.selected_application == self.selected_item):
				self.wTree.get_widget("image_screenshot").set_from_pixbuf(gtk.gdk.pixbuf_new_from_file_at_size(self.selected_item.screenshot, 200, 200))
			gtk.gdk.threads_leave()
		except Exception, detail:
			pass					

class RefreshThread(threading.Thread):

	def __init__(self, wTree, refresh, model, username):
		threading.Thread.__init__(self)
		self.wTree = wTree
		self.refresh = refresh
		self.directory = "/usr/share/linuxmint/mintinstall/data"
		self.model = model
		self.username = username

	def run(self):
		try:
		
			self.initialize()
			del self.model.portals[:]
			self.model = self.register_portals(self.model)
			gtk.gdk.threads_enter()
			self.wTree.get_widget("main_window").set_sensitive(False)
			self.wTree.get_widget("main_window").window.set_cursor(gtk.gdk.Cursor(gtk.gdk.WATCH))
			gtk.gdk.threads_leave()
			if (self.refresh):	
				for portal in self.model.portals:
					self.download_portal(portal)
			try:
				global num_apps
				num_apps = 0
				for portal in self.model.portals:
					self.build_portal(self.model, portal)
					num_apps = num_apps + len(portal.items)

				# Reconciliation of categories hierarchy
				for portal in self.model.portals:
					for category in portal.categories:
						if (category.parent == "0"):
							category.parent = None
						else:
							parentKey = category.parent			
							parent = portal.find_category(parentKey)
							parent.add_subcategory(category)

				gtk.gdk.threads_enter()	
				update_statusbar(wTree, model)
				gtk.gdk.threads_leave()				
			except Exception, details:
				print details
				allPortalsHere = True
				for portal in model.portals:
					if not os.path.exists(self.directory + "/xml/" + portal.key + ".xml"):
						allPortalsHere = False
				if allPortalsHere:
					print details
					os.system("zenity --error --text=\"" + _("The data used by mintInstall is corrupted or out of date. Click on refresh to fix the problem :") + " " + str(details) + "\"")
				else:
					gtk.gdk.threads_enter()
					dialog = gtk.MessageDialog(self.wTree.get_widget("main_window"), gtk.DIALOG_MODAL, gtk.MESSAGE_INFO, gtk.BUTTONS_NONE, _("Please refresh mintInstall by clicking on the Refresh button"))
					dialog.set_title("mintInstall")
					dialog.set_icon_from_file("/usr/lib/linuxmint/mintInstall/icon.svg")
					dialog.add_button(gtk.STOCK_CLOSE, gtk.RESPONSE_CLOSE)
					dialog.connect('response', lambda dialog, response: dialog.destroy())
					dialog.show()
					gtk.gdk.threads_leave()					

				del self.model.portals[:]
				self.model = self.register_portals(self.model)

			gtk.gdk.threads_enter()
			self.load_model_in_GUI(self.wTree, self.model)			
			self.wTree.get_widget("main_window").window.set_cursor(None)
			self.wTree.get_widget("main_window").set_sensitive(True)
			gtk.gdk.threads_leave()
		except Exception, detail:
			print detail

	def initialize(self):		
		#if self.refresh:
		#	os.system("rm -rf " + self.directory + "/tmp/*")	
		os.system("mkdir -p " + self.directory + "/icons/categories")
		os.system("mkdir -p " + self.directory + "/mintfiles")
		os.system("mkdir -p " + self.directory + "/screenshots")
		os.system("mkdir -p " + self.directory + "/xml")
		#os.system("mkdir -p " + self.directory + "/etc")		
		#if not os.path.exists(self.directory + "/etc/portals.list"):
		#	os.system("cp /etc/linuxmint/version/mintinstall/portals.list " + self.directory + "/etc/portals.list")

	def register_portals(self, model):		
		portalsFile = open("/usr/share/linuxmint/mintinstall/portals.list")	
		for line in portalsFile:
			array = line.split(";")
			if len(array) == 6:
				portal = Classes.Portal(array[0], array[1], array[2], array[3], array[4], array[5])
				model.portals.append(portal)
		portalsFile.close()
		return model

	def download_portal(self, portal):
		gtk.gdk.threads_enter()	
		statusbar = wTree.get_widget("statusbar")
		context_id = statusbar.get_context_id("mintInstall")
		portal.update_url = portal.update_url.strip()
		statusbar.push(context_id, _("Downloading data for %s") % (portal.name))
		gtk.gdk.threads_leave()		
		webFile = urllib.urlopen(portal.update_url)
		localFile = open(self.directory + "/xml/" + portal.key + ".xml", 'w')
		localFile.write(webFile.read())
		webFile.close()
		localFile.close()		

	def build_portal(self, model, portal):	
		fileName = self.directory + "/xml/" + portal.key + ".xml"
		numItems = commands.getoutput("grep -c \"<item\" " + fileName)
		numReviews = commands.getoutput("grep -c \"<review\" " + fileName)
		numScreenshots = commands.getoutput("grep -c \"<screenshot\" " + fileName)
		numCategories = commands.getoutput("grep -c \"<category\" " + fileName)
		numTotal = int(numItems) + int(numReviews) + int(numScreenshots) + int(numCategories)
		progressbar = wTree.get_widget("progressbar")
		progressbar.set_fraction(0)
		progressbar.set_text("0%")
		processed_categories = 0
		processed_items = 0
		processed_screenshots = 0
		processed_reviews = 0			
		processed_total = 0
		xml = ET.parse(fileName)
		root = xml.getroot()				
		gtk.gdk.threads_enter()
		statusbar = wTree.get_widget("statusbar")
		context_id = statusbar.get_context_id("mintInstall")
		gtk.gdk.threads_leave()	
		for element in root: 
			if element.tag == "category":
				category = Classes.Category(portal, element.attrib["id"], element.attrib["name"], element.attrib["description"], element.attrib["vieworder"], element.attrib["parent"], element.attrib["logo"])				
				category.name = category.name.replace("ANDAND", "&")
				if self.refresh:
					os.chdir(self.directory + "/icons/categories")	
					os.system("wget -nc -O" + category.key + " " + category.logo)
					os.chdir("/usr/lib/linuxmint/mintInstall")					
				category.logo = gtk.gdk.pixbuf_new_from_file_at_size(self.directory + "/icons/categories/" + category.key, 16, 16)
				category.name = _(category.name)
				portal.categories.append(category)	
				gtk.gdk.threads_enter()	
				processed_categories = int(processed_categories) + 1	
				statusbar.push(context_id, _("%d categories loaded") % processed_categories)
				processed_total = processed_total + 1
				ratio = float(processed_total) / float(numTotal)
				progressbar.set_fraction(ratio)
				pct = int(ratio * 100)
				progressbar.set_text(str(pct) + "%")
				gtk.gdk.threads_leave()		
					
			elif element.tag == "item":
				item = Classes.Item(portal, element.attrib["id"], element.attrib["link"], element.attrib["mint_file"], element.attrib["category"], element.attrib["name"], element.attrib["description"], "", element.attrib["added"], element.attrib["views"], element.attrib["license"], element.attrib["size"], element.attrib["website"], element.attrib["repository"], element.attrib["average_rating"])
				item.average_rating = item.average_rating[:3]								
				if item.average_rating.endswith("0"):
					item.average_rating = item.average_rating[0]
				item.views = int(item.views)
				item.link = item.link.replace("ANDAND", "&")
				if self.refresh:					
					os.chdir(self.directory + "/mintfiles")	
					os.system("wget -nc -O" + item.key + ".mint -T10 \"" + item.mint_file + "\"")
					os.chdir("/usr/lib/linuxmint/mintInstall")
				item.mint_file = self.directory + "/mintfiles/" + item.key + ".mint"				

				if item.repository == "":
					item.repository = _("Default repositories")
				portal.items.append(item)		
				portal.find_category(item.category).add_item(item)
				gtk.gdk.threads_enter()
				processed_items = int(processed_items) + 1	
				statusbar.push(context_id, _("%d applications loaded") % processed_items)
				processed_total = processed_total + 1
				ratio = float(processed_total) / float(numTotal)
				progressbar.set_fraction(ratio)
				pct = int(ratio * 100)
				progressbar.set_text(str(pct) + "%")
				gtk.gdk.threads_leave()						

			elif element.tag == "screenshot":
				screen_item = element.attrib["item"]
				screen_img = element.attrib["img"]
				item = portal.find_item(screen_item)
				if item != None:			
					try:
						if self.refresh:					
							os.chdir(self.directory + "/screenshots")	
							os.system("wget -nc -O" + screen_item + " -T10 \"" + screen_img + "\"")
							os.chdir("/usr/lib/linuxmint/mintInstall")
						item.screenshot = self.directory + "/screenshots/" + screen_item
						item.screenshot_url = screen_img				
						gtk.gdk.threads_enter()						
						processed_screenshots = int(processed_screenshots) + 1	
						statusbar.push(context_id, _("%d screenshots loaded") % processed_screenshots)
						gtk.gdk.threads_leave()		
					except:
						pass
				gtk.gdk.threads_enter()
				processed_total = processed_total + 1
				ratio = float(processed_total) / float(numTotal)
				progressbar.set_fraction(ratio)
				pct = int(ratio * 100)
				progressbar.set_text(str(pct) + "%")
				gtk.gdk.threads_leave()

			elif element.tag == "review":
				item = portal.find_item(element.attrib["item"])
				if (item != None):
					review = Classes.Review(portal, item, element.attrib["rating"], element.attrib["comment"], element.attrib["user_id"], element.attrib["user_name"])
					if "@" in review.username:
						elements = review.username.split("@")
						firstname = elements[0]
						secondname = elements[1]
						firstname = firstname[0:1] + "..." + firstname [-2:-1]
						review.username = firstname + "@" + secondname
					review.rating = int(review.rating)
					item.add_review(review)
					portal.reviews.append(review)
					gtk.gdk.threads_enter()					
					processed_reviews = int(processed_reviews) + 1	
					statusbar.push(context_id, _("%d reviews loaded") % processed_reviews)
					gtk.gdk.threads_leave()								
	
				gtk.gdk.threads_enter()
				processed_total = processed_total + 1
				ratio = float(processed_total) / float(numTotal)
				progressbar.set_fraction(ratio)
				pct = int(ratio * 100)
				progressbar.set_text(str(pct) + "%")
				gtk.gdk.threads_leave()

		fetch_apt_details(model)	

		gtk.gdk.threads_enter()
		progressbar.set_fraction(0)
		progressbar.set_text("")
		gtk.gdk.threads_leave()

	def load_model_in_GUI(self, wTree, model):
		# Build categories tree
		tree_categories = wTree.get_widget("tree_categories")
		model_categories = gtk.TreeStore(str, object, gtk.gdk.Pixbuf)
		#Add the "All" category
		iter = model_categories.insert_before(None, None)						
		model_categories.set_value(iter, 0, _("All applications"))						
		model_categories.set_value(iter, 1, None)
		model_categories.set_value(iter, 2, gtk.gdk.pixbuf_new_from_file_at_size("/usr/lib/linuxmint/mintInstall/icon.svg", 16, 16))
		for portal in model.portals:
			for category in portal.categories:		
				if (category.parent == None or category.parent == "None"):
					iter = model_categories.insert_before(None, None)						
					model_categories.set_value(iter, 0, category.name)						
					model_categories.set_value(iter, 1, category)
					model_categories.set_value(iter, 2, category.logo)
					for subcategory in category.subcategories:				
						subiter = model_categories.insert_before(iter, None)						
						model_categories.set_value(subiter, 0, subcategory.name)				
						model_categories.set_value(subiter, 1, subcategory)
						model_categories.set_value(subiter, 2, subcategory.logo)
		tree_categories.set_model(model_categories)
		del model_categories
		selection = tree_categories.get_selection()
		selection.connect("changed", show_category, model, wTree)

		#Build applications table
		tree_applications = wTree.get_widget("tree_applications")
		model_applications = gtk.TreeStore(str, str, int, int, str, object, int, gtk.gdk.Pixbuf, int)		
		for portal in model.portals:
			for item in portal.items:		
				iter = model_applications.insert_before(None, None)						
				model_applications.set_value(iter, 0, item.name)						
				model_applications.set_value(iter, 1, item.average_rating)
				model_applications.set_value(iter, 2, len(item.reviews))
				model_applications.set_value(iter, 3, item.views)
				model_applications.set_value(iter, 4, item.added)
				model_applications.set_value(iter, 5, item)
				model_applications.set_value(iter, 6, float(item.average_rating) * len(item.reviews) + (item.views / 1000))
				if item.is_special:
					model_applications.set_value(iter, 7, gtk.gdk.pixbuf_new_from_file("/usr/lib/linuxmint/mintInstall/status-icons/special.png"))	
					model_applications.set_value(iter, 8, 9)	
				else:					
					if item.status == "available":
						model_applications.set_value(iter, 7, gtk.gdk.pixbuf_new_from_file("/usr/lib/linuxmint/mintInstall/status-icons/available.png"))		
						model_applications.set_value(iter, 8, 4)				
					elif item.status == "installed":
						model_applications.set_value(iter, 7, gtk.gdk.pixbuf_new_from_file("/usr/lib/linuxmint/mintInstall/status-icons/installed.png"))
						model_applications.set_value(iter, 8, 3)
					elif item.status == "add":
						model_applications.set_value(iter, 7, gtk.gdk.pixbuf_new_from_file("/usr/lib/linuxmint/mintInstall/status-icons/add.png"))		
						model_applications.set_value(iter, 8, 1)
					elif item.status == "remove":
						model_applications.set_value(iter, 7, gtk.gdk.pixbuf_new_from_file("/usr/lib/linuxmint/mintInstall/status-icons/remove.png"))		
						model_applications.set_value(iter, 8, 2)
		model_applications.set_sort_column_id( 6, gtk.SORT_DESCENDING )
		tree_applications.set_model(model_applications)		
		first = model_applications.get_iter_first()
		if (first != None):
			tree_applications.get_selection().select_iter(first)
		del model_applications				

if __name__ == "__main__":
	#i18n (force categories to make it to the pot file)
	i18n = _("Games")
	i18n = _("First person shooters")
	i18n = _("Turn-based strategy")
	i18n = _("Real time strategy")
	i18n = _("Internet")
	i18n = _("Emulators")
	i18n = _("Simulation & racing")
	i18n = _("Email")
	i18n = _("Accessories")
	i18n = _("Text editors")
	i18n = _("Sound & Video")
	i18n = _("Audio players")
	i18n = _("Video players")
	i18n = _("Burning tools")
	i18n = _("Office")
	i18n = _("Office suites")
	i18n = _("Collection managers")
	i18n = _("Document viewers")
	i18n = _("Finance")
	i18n = _("Graphics")
	i18n = _("2D")
	i18n = _("Image viewers")
	i18n = _("Photo")
	i18n = _("Scanning tools")
	i18n = _("Tools")
	i18n = _("Web browsers")
	i18n = _("Word processors")
	i18n = _("Spreadsheets")
	i18n = _("Publishing")
	i18n = _("Graph and flowcharts")
	i18n = _("Databases")
	i18n = _("Mind mapping")
	i18n = _("Instant messengers")
	i18n = _("Internet Relay Chat")
	i18n = _("Programming")
	i18n = _("Education")
	i18n = _("System Tools")
	i18n = _("FTP")
	i18n = _("Desktop components")
	i18n = _("Package management")
	i18n = _("P2P and torrent")
	i18n = _("Firewall")
	i18n = _("Drivers")
	i18n = _("Upstream")

	username = sys.argv[1]
	os.system("sudo -u " + username + " xhost +root")
	model = Classes.Model()
	wTree = build_GUI(model, username)
	refresh = RefreshThread(wTree, False, model, username)
	refresh.start()
	gtk.main()



		

########NEW FILE########
__FILENAME__ = mintinstall
#!/usr/bin/python
# -*- coding: UTF-8 -*-

import Classes
import sys, os, commands
import gtk
import gtk.glade
import pygtk
import gobject
import thread
import gettext
import tempfile
import threading
import webkit
import string
import Image
import StringIO
import ImageFont, ImageDraw, ImageOps
import time
import apt
import urllib, urllib2
import thread
import glib
import dbus
import httplib
from urlparse import urlparse

from AptClient.AptClient import AptClient

from datetime import datetime
from subprocess import Popen, PIPE
from widgets.pathbar2 import NavigationBar
from widgets.searchentry import SearchEntry
from user import home
import base64

# Don't let mintinstall run as root
#~ if os.getuid() == 0:
    #~ print "The software manager should not be run as root. Please run it in user mode."
    #~ sys.exit(1)
if os.getuid() != 0:
    print "The software manager should be run as root."
    sys.exit(1)

pygtk.require("2.0")

sys.path.append('/usr/lib/linuxmint/common')
from configobj import ConfigObj

def print_timing(func):
    def wrapper(*arg):
        t1 = time.time()
        res = func(*arg)
        t2 = time.time()
        print '%s took %0.3f ms' % (func.func_name, (t2-t1)*1000.0)
        return res
    return wrapper

# i18n
gettext.install("mintinstall", "/usr/share/linuxmint/locale")

architecture = commands.getoutput("uname -a")
if (architecture.find("x86_64") >= 0):
    import ctypes
    libc = ctypes.CDLL('libc.so.6')
    libc.prctl(15, 'mintinstall', 0, 0, 0)
else:
    import dl   
    if os.path.exists('/lib/libc.so.6'):
        libc = dl.open('/lib/libc.so.6')
        libc.call('prctl', 15, 'mintinstall', 0, 0, 0)
    elif os.path.exists('/lib/i386-linux-gnu/libc.so.6'):
        libc = dl.open('/lib/i386-linux-gnu/libc.so.6')
        libc.call('prctl', 15, 'mintinstall', 0, 0, 0)

gtk.gdk.threads_init()

COMMERCIAL_APPS = ["chromium-browser", "chromium-browser-l10n", "chromium-codecs-ffmpeg", 
                  "chromium-codecs-ffmpeg-extra", "chromium-codecs-ffmpeg-extra", 
                  "chromium-browser-dbg", "chromium-chromedriver", "chromium-chromedriver-dbg"]

# List of packages which are either broken or do not install properly in mintinstall
BROKEN_PACKAGES = ['pepperflashplugin-nonfree']

def get_dbus_bus():
   bus = dbus.SystemBus()
   return bus


def convertImageToGtkPixbuf(image):
    buf = StringIO.StringIO()
    image.save (buf, format="PNG")
    bufString=buf.getvalue()
    loader = gtk.gdk.PixbufLoader('png')
    loader.write(bufString, len(bufString))
    pixbuf = loader.get_pixbuf()
    loader.close()
    buf.close()
    return pixbuf;

class DownloadReviews(threading.Thread):
    def __init__(self, application):
        threading.Thread.__init__(self)
        self.application = application

    def run(self):
        try:
            reviews_dir = home + "/.linuxmint/mintinstall"
            os.system("mkdir -p " + reviews_dir)
            reviews_path = reviews_dir + "/reviews.list"
            reviews_path_tmp = reviews_path + ".tmp"
            url=urllib.urlretrieve("http://community.linuxmint.com/data/reviews.list", reviews_path_tmp)
            numlines = 0
            numlines_new = 0
            if os.path.exists(reviews_path):
                numlines = int(commands.getoutput("cat " + reviews_path + " | wc -l"))
            if os.path.exists(reviews_path_tmp):
                numlines_new = int(commands.getoutput("cat " + reviews_path_tmp + " | wc -l"))
            if numlines_new > numlines:
                os.system("mv " + reviews_path_tmp + " " + reviews_path)
                print "Overwriting reviews file in " + reviews_path
                self.application.update_reviews()
        except Exception, detail:
            print detail

class ScreenshotDownloader(threading.Thread):
    def __init__(self, application, pkg_name):        
        threading.Thread.__init__(self)
        self.application = application
        self.pkg_name = pkg_name

    def run(self):        
        num_screenshots = 0;
        self.application.screenshots = []
        # Add main screenshot
        try:
            thumb = "http://community.linuxmint.com/thumbnail.php?w=250&pic=/var/www/community.linuxmint.com/img/screenshots/%s.png" % self.pkg_name
            link = "http://community.linuxmint.com/img/screenshots/%s.png" % self.pkg_name            
            p = urlparse(link)
            conn = httplib.HTTPConnection(p.netloc)
            conn.request('HEAD', p.path)
            resp = conn.getresponse()
            if resp.status < 400:
                num_screenshots+=1;
                self.application.screenshots.append('addScreenshot("%s", "%s")' % (link, thumb))
        except Exception, detail:
            print detail

        try:
            # Add additional screenshots
            from BeautifulSoup import BeautifulSoup
            page = BeautifulSoup(urllib2.urlopen("http://screenshots.debian.net/package/%s" % self.pkg_name))
            images = page.findAll('img')
            for image in images:
                if num_screenshots >= 4:
                    break
                if image['src'].startswith('/screenshots'):
                    thumb = "http://screenshots.debian.net%s" % image['src']
                    link = thumb.replace("_small", "_large")
                    num_screenshots+=1;
                    self.application.screenshots.append('addScreenshot("%s", "%s")' % (link, thumb))
        except Exception, detail:
            print detail 

        try:
            gobject.idle_add(self.application.show_screenshots, self.pkg_name)
        except Exception, detail:
            print detail 
   

class APTProgressHandler(threading.Thread):
    def __init__(self, application, packages, wTree, apt_client):
        threading.Thread.__init__(self)
        self.application = application
        self.apt_client = apt_client
        self.wTree = wTree
        self.status_label = wTree.get_widget("label_ongoing")
        self.progressbar = wTree.get_widget("progressbar1")
        self.tree_transactions = wTree.get_widget("tree_transactions")
        self.packages = packages
        self.model = gtk.TreeStore(str, str, str, float, object)
        self.tree_transactions.set_model(self.model)
        self.tree_transactions.connect( "button-release-event", self.menuPopup )
        
        self.apt_client.connect("progress", self._on_apt_client_progress)
        self.apt_client.connect("task_ended", self._on_apt_client_task_ended)
    
    def _on_apt_client_progress(self, *args):
        self._update_display()

    def _on_apt_client_task_ended(self,aptClient, task_id, task_type, params, success, error):
        self._update_display()
        
        if error:
            if task_type == "install":
                title = _("The package '%s' could not be installed") % str(params["package_name"])
            elif task_type == "remove":
                title = _("The package '%s' could not be removed") % str(params["package_name"])
            else:
                # Fail silently for other task types (update, wait)
                return

            # By default assume there's a problem with the Internet connection
            text=_("Please check your connection to the Internet")

            # Check to see if no other APT process is running
            p1 = Popen(['ps', '-U', 'root', '-o', 'comm'], stdout=PIPE)
            p = p1.communicate()[0]
            running = None
            pslist = p.split('\n')
            for process in pslist:
                process_name = process.strip()
                if process_name in ["dpkg", "apt-get", "aptitude", "synaptic","update-manager", "adept", "adept-notifier", "checkAPT.py"]:
                    running = process_name                    
                    text="%s\n\n    <b>%s</b>" % (_("Another application is using APT:"), process_name)
                    break
                                                    
            self.application.show_dialog_modal(title=title,
                                            text=text,
                                            type=gtk.MESSAGE_ERROR,
                                            buttons=gtk.BUTTONS_OK)
          
          
          
    def _update_display(self):
        progress_info = self.apt_client.get_progress_info()
        task_ids = []
        for task in progress_info["tasks"]:
            task_is_new = True
            task_ids.append(task["task_id"])
            iter = self.model.get_iter_first()
            while iter is not None:
                if self.model.get_value(iter, 4)["task_id"] == task["task_id"]:
                    self.model.set_value(iter, 1, self.get_status_description(task))
                    self.model.set_value(iter, 2, "%d %%" % task["progress"])
                    self.model.set_value(iter, 3, task["progress"])
                    task_is_new = False
                iter = self.model.iter_next(iter)
            if task_is_new:
                iter = self.model.insert_before(None, None)
                self.model.set_value(iter, 0, self.get_role_description(task))
                self.model.set_value(iter, 1, self.get_status_description(task))
                self.model.set_value(iter, 2, "%d %%" % task["progress"])
                self.model.set_value(iter, 3, task["progress"])
                self.model.set_value(iter, 4, task)
        iter = self.model.get_iter_first()
        while iter is not None:
            if self.model.get_value(iter, 4)["task_id"] not in task_ids:
                task = self.model.get_value(iter, 4)
                iter_to_be_removed = iter
                iter = self.model.iter_next(iter)
                self.model.remove(iter_to_be_removed)
                if task["role"] in ["install", "remove"]:
                    pkg_name = task["task_params"]["package_name"]
                    cache = apt.Cache()
                    new_pkg = cache[pkg_name]
                    # Update packages
                    for package in self.packages:
                        if package.pkg.name == pkg_name:
                            package.pkg = new_pkg
                            # If the user is currently viewing this package in the browser,
                            # refresh the view to show that the package has been installed or uninstalled.
                            if self.application.navigation_bar.get_active().get_label() == pkg_name:
                                self.application.show_package(package, None)

                    # Update apps tree  
                    tree_applications = self.wTree.get_widget("tree_applications")
                    if tree_applications:
                        model_apps = tree_applications.get_model()
                        if isinstance(model_apps, gtk.TreeModelFilter):
                            model_apps = model_apps.get_model()

                        if model_apps is not None:
                            iter_apps = model_apps.get_iter_first()
                            while iter_apps is not None:
                                package = model_apps.get_value(iter_apps, 3)
                                if package.pkg.name == pkg_name:
                                    model_apps.set_value(iter_apps, 0, self.application.get_package_pixbuf_icon(package))
                                iter_apps = model_apps.iter_next(iter_apps)                    

                        # Update mixed apps tree                   
                        model_apps = self.wTree.get_widget("tree_mixed_applications").get_model()
                        if isinstance(model_apps, gtk.TreeModelFilter):
                            model_apps = model_apps.get_model()
                        if model_apps is not None:
                            iter_apps = model_apps.get_iter_first()
                            while iter_apps is not None:
                                package = model_apps.get_value(iter_apps, 3)
                                if package.pkg.name == pkg_name:
                                    
                                    model_apps.set_value(iter_apps, 0, self.application.get_package_pixbuf_icon(package))
                                iter_apps = model_apps.iter_next(iter_apps)
            else:
                iter = self.model.iter_next(iter)
        if progress_info["nb_tasks"] > 0:
            fraction = progress_info["progress"]
            progress = str(int(fraction)) + '%'
        else:
            fraction = 0
            progress = ""
        self.status_label.set_text(_("%d ongoing actions") % progress_info["nb_tasks"])
        self.progressbar.set_text(progress)
        self.progressbar.set_fraction(fraction / 100.)

    def menuPopup( self, widget, event ):
        if event.button == 3:
            model, iter = self.tree_transactions.get_selection().get_selected()
            if iter is not None:
                task = model.get_value(iter, 4)
                menu = gtk.Menu()
                cancelMenuItem = gtk.MenuItem(_("Cancel the task: %s") % model.get_value(iter, 0))
                cancelMenuItem.set_sensitive(task["cancellable"])
                menu.append(cancelMenuItem)
                menu.show_all()
                cancelMenuItem.connect( "activate", self.cancelTask, task)
                menu.popup( None, None, None, event.button, event.time )

    def cancelTask(self, menu, task):
        self.apt_client.cancel_task(task["task_id"])
        self._update_display()
            
    def get_status_description(self, transaction):
        descriptions = {"waiting":_("Waiting"), "downloading":_("Downloading"), "running":_("Running"), "finished":_("Finished")}
        if "status" in transaction:
            if transaction["status"] in descriptions.keys():
                return descriptions[transaction["status"]]
            else:
                return transaction["status"]
        else:
            return ""
    
    def get_role_description(self, transaction):
        if "role" in transaction:
            if transaction["role"] == "install":
                return _("Installing %s") % transaction["task_params"]["package_name"]
            elif transaction["role"] == "remove":
                return _("Removing %s") % transaction["task_params"]["package_name"]
            elif transaction["role"] == "update_cache":
                return _("Updating cache")
            else:
                return _("No role set")
        else:
            return _("No role set")

class Category:

    def __init__(self, name, icon, sections, parent, categories):
        self.name = name
        self.icon = icon
        self.parent = parent
        self.subcategories = []
        self.packages = []
        self.sections = sections
        self.matchingPackages = []
        if parent is not None:
            parent.subcategories.append(self)
        categories.append(self)
        cat = self
        while cat.parent is not None:
            cat = cat.parent

class Package(object):
    __slots__='name', 'pkg', 'reviews', 'categories','score','avg_rating','num_reviews','candidate','summary' #To remove __dict__ memory overhead
    
    def __init__(self, name, pkg):
        self.name = name
        self.pkg = pkg
        self.reviews = []
        self.categories = []
        self.score = 0
        self.avg_rating = 0
        self.num_reviews = 0
        self.candidate = pkg.candidate #cache, as the pkg.candidate call has a performance overhead
        
        #search cache:
        self.summary = None
        if self.candidate is not None:
          self.summary = self.candidate.summary
            
    def update_stats(self):
        points = 0
        sum_rating = 0
        self.num_reviews = len(self.reviews)
        self.avg_rating = 0
        for review in self.reviews:
            points = points + (review.rating - 3)
            sum_rating = sum_rating + review.rating
        if self.num_reviews > 0:
            self.avg_rating = int(round(sum_rating / self.num_reviews))
        self.score = points

class Review(object):
    __slots__='date','packagename','username','rating','comment','package' #To remove __dict__ memory overhead
    
    def __init__(self, packagename, date, username, rating, comment):
        self.date = date
        self.packagename = packagename
        self.username = username
        self.rating = int(rating)
        self.comment = comment
        self.package = None

class Application():
        
    PAGE_CATEGORIES = 0
    PAGE_MIXED = 1
    PAGE_PACKAGES = 2
    PAGE_DETAILS = 3
    PAGE_SCREENSHOT = 4
    PAGE_WEBSITE = 5
    PAGE_SEARCH = 6
    PAGE_TRANSACTIONS = 7
    PAGE_REVIEWS = 8

    NAVIGATION_HOME = 1
    NAVIGATION_SEARCH = 2
    NAVIGATION_CATEGORY = 3
    NAVIGATION_SEARCH_CATEGORY = 4
    NAVIGATION_SUB_CATEGORY = 5
    NAVIGATION_SEARCH_SUB_CATEGORY = 6
    NAVIGATION_ITEM = 7
    NAVIGATION_SCREENSHOT = 8
    NAVIGATION_WEBSITE = 8
    NAVIGATION_REVIEWS = 8

    if os.path.exists("/usr/share/fonts/truetype/wqy/wqy-microhei.ttc"):
        FONT = "/usr/share/fonts/truetype/wqy/wqy-microhei.ttc"
    else:
        FONT = "/usr/share/fonts/truetype/freefont/FreeSans.ttf"
        
    
    @print_timing    
    def __init__(self):
        self.browser = webkit.WebView()
        self.browser2 = webkit.WebView()
        self.packageBrowser = webkit.WebView()
        self.screenshotBrowser = webkit.WebView()
        self.websiteBrowser = webkit.WebView()
        self.reviewsBrowser = webkit.WebView()

        self.add_categories()
        self.build_matched_packages()
        self.add_packages()
                    

        self.screenshots = []        

        # Build the GUI
        gladefile = "/usr/lib/linuxmint/mintInstall/mintinstall.glade"
        wTree = gtk.glade.XML(gladefile, "main_window")
        wTree.get_widget("main_window").set_title(_("Software Manager"))
        wTree.get_widget("main_window").set_icon_from_file("/usr/lib/linuxmint/mintInstall/icon.svg")
        wTree.get_widget("main_window").connect("delete_event", self.close_application)
        
        self.main_window = wTree.get_widget("main_window")

        self.apt_client = AptClient()
        self.apt_progress_handler = APTProgressHandler(self, self.packages, wTree, self.apt_client)
        
        self.add_reviews()
        downloadReviews = DownloadReviews(self)
        downloadReviews.start()

        if len(sys.argv) > 1 and sys.argv[1] == "list":
            # Print packages and their categories and exit
            self.export_listing()
            sys.exit(0)

        self.prefs = self.read_configuration()

        # Build the menu
        fileMenu = gtk.MenuItem(_("_File"))
        fileSubmenu = gtk.Menu()
        fileMenu.set_submenu(fileSubmenu)
        closeMenuItem = gtk.ImageMenuItem(gtk.STOCK_CLOSE)
        closeMenuItem.get_child().set_text(_("Close"))
        closeMenuItem.connect("activate", self.close_application)
        fileSubmenu.append(closeMenuItem)

        editMenu = gtk.MenuItem(_("_Edit"))
        editSubmenu = gtk.Menu()
        editMenu.set_submenu(editSubmenu)
        prefsMenuItem = gtk.ImageMenuItem(gtk.STOCK_PREFERENCES)
        prefsMenuItem.get_child().set_text(_("Preferences"))
        prefsMenu = gtk.Menu()
        prefsMenuItem.set_submenu(prefsMenu)

        searchInSummaryMenuItem = gtk.CheckMenuItem(_("Search in packages summary (slower search)"))
        searchInSummaryMenuItem.set_active(self.prefs["search_in_summary"])
        searchInSummaryMenuItem.connect("toggled", self.set_search_filter, "search_in_summary")

        searchInDescriptionMenuItem = gtk.CheckMenuItem(_("Search in packages description (even slower search)"))
        searchInDescriptionMenuItem.set_active(self.prefs["search_in_description"])
        searchInDescriptionMenuItem.connect("toggled", self.set_search_filter, "search_in_description")

        openLinkExternalMenuItem = gtk.CheckMenuItem(_("Open links using the web browser"))
        openLinkExternalMenuItem.set_active(self.prefs["external_browser"])
        openLinkExternalMenuItem.connect("toggled", self.set_external_browser)

        searchWhileTypingMenuItem = gtk.CheckMenuItem(_("Search while typing"))
        searchWhileTypingMenuItem.set_active(self.prefs["search_while_typing"])
        searchWhileTypingMenuItem.connect("toggled", self.set_search_filter, "search_while_typing")

        prefsMenu.append(searchInSummaryMenuItem)
        prefsMenu.append(searchInDescriptionMenuItem)
        prefsMenu.append(openLinkExternalMenuItem)
        prefsMenu.append(searchWhileTypingMenuItem)

        #prefsMenuItem.connect("activate", open_preferences, treeview_update, statusIcon, wTree)
        editSubmenu.append(prefsMenuItem)

        accountMenuItem = gtk.ImageMenuItem(gtk.STOCK_PREFERENCES)
        accountMenuItem.get_child().set_text(_("Account information"))
        accountMenuItem.connect("activate", self.open_account_info)
        editSubmenu.append(accountMenuItem)

        if os.path.exists("/usr/bin/software-sources") or os.path.exists("/usr/bin/software-properties-gtk") or os.path.exists("/usr/bin/software-properties-kde"):
            sourcesMenuItem = gtk.ImageMenuItem(gtk.STOCK_PREFERENCES)
            sourcesMenuItem.set_image(gtk.image_new_from_file("/usr/lib/linuxmint/mintUpdate/icons/software-properties.png"))
            sourcesMenuItem.get_child().set_text(_("Software sources"))
            sourcesMenuItem.connect("activate", self.open_repositories)
            editSubmenu.append(sourcesMenuItem)

        viewMenu = gtk.MenuItem(_("_View"))
        viewSubmenu = gtk.Menu()
        viewMenu.set_submenu(viewSubmenu)

        availablePackagesMenuItem = gtk.CheckMenuItem(_("Available packages"))
        availablePackagesMenuItem.set_active(self.prefs["available_packages_visible"])
        availablePackagesMenuItem.connect("toggled", self.set_filter, "available_packages_visible")

        installedPackagesMenuItem = gtk.CheckMenuItem(_("Installed packages"))
        installedPackagesMenuItem.set_active(self.prefs["installed_packages_visible"])
        installedPackagesMenuItem.connect("toggled", self.set_filter, "installed_packages_visible")

        viewSubmenu.append(availablePackagesMenuItem)
        viewSubmenu.append(installedPackagesMenuItem)

        helpMenu = gtk.MenuItem(_("_Help"))
        helpSubmenu = gtk.Menu()
        helpMenu.set_submenu(helpSubmenu)
        aboutMenuItem = gtk.ImageMenuItem(gtk.STOCK_ABOUT)
        aboutMenuItem.get_child().set_text(_("About"))
        aboutMenuItem.connect("activate", self.open_about)
        helpSubmenu.append(aboutMenuItem)

        #browser.connect("activate", browser_callback)
        #browser.show()
        wTree.get_widget("menubar1").append(fileMenu)
        wTree.get_widget("menubar1").append(editMenu)
        wTree.get_widget("menubar1").append(viewMenu)
        wTree.get_widget("menubar1").append(helpMenu)

        # Build the applications tables
        self.tree_applications = wTree.get_widget("tree_applications")
        self.tree_mixed_applications = wTree.get_widget("tree_mixed_applications")
        self.tree_search = wTree.get_widget("tree_search")
        self.tree_transactions = wTree.get_widget("tree_transactions")

        self.build_application_tree(self.tree_applications)
        self.build_application_tree(self.tree_mixed_applications)
        self.build_application_tree(self.tree_search)
        self.build_transactions_tree(self.tree_transactions)

        self.navigation_bar = NavigationBar()
        self.searchentry = SearchEntry()
        self.searchentry.connect("terms-changed", self.on_search_terms_changed)
        self.searchentry.connect("activate", self.on_search_entry_activated)
        top_hbox = gtk.HBox()
        top_hbox.pack_start(self.navigation_bar, padding=6)
        top_hbox.pack_start(self.searchentry, expand=False, padding=6)
        wTree.get_widget("toolbar").pack_start(top_hbox, expand=False, padding=6)
        
        self.search_in_category_hbox = wTree.get_widget("search_in_category_hbox")
        self.message_search_in_category_label = wTree.get_widget("message_search_in_category_label")
        wTree.get_widget("show_all_results_button").connect("clicked", lambda w: self._show_all_search_results())
        wTree.get_widget("search_in_category_hbox_wrapper").modify_bg(gtk.STATE_NORMAL, gtk.gdk.color_parse("#F5F5B5"))
        
        self._search_in_category = self.root_category
        self._current_search_terms = ""

        self.notebook = wTree.get_widget("notebook1")

        sans26  =  ImageFont.truetype ( self.FONT, 26 )
        sans10  =  ImageFont.truetype ( self.FONT, 12 )

        # Build the category browsers
        template = open("/usr/lib/linuxmint/mintInstall/data/templates/CategoriesView.html").read()
        subs = {'header': _("Categories")}      
        subs['subtitle'] = _("Please choose a category")
        subs['package_num'] = _("%d packages are currently available") % len(self.packages)
        html = string.Template(template).safe_substitute(subs)
        self.browser.load_html_string(html, "file:/")
        self.browser.connect("load-finished", self._on_load_finished)
        self.browser.connect('title-changed', self._on_title_changed)
        wTree.get_widget("scrolled_categories").add(self.browser)

        template = open("/usr/lib/linuxmint/mintInstall/data/templates/SubCategoriesView.html").read()
        subs = {'header': _("Categories")}
        subs['subtitle'] = _("Please choose a sub-category")
        html = string.Template(template).safe_substitute(subs)
        self.browser2.load_html_string(html, "file:/")
        self.browser2.connect('title-changed', self._on_title_changed)
        wTree.get_widget("scrolled_mixed_categories").add(self.browser2)

        wTree.get_widget("scrolled_details").add(self.packageBrowser)

        self.packageBrowser.connect('title-changed', self._on_title_changed)

        wTree.get_widget("scrolled_screenshot").add(self.screenshotBrowser)
        wTree.get_widget("scrolled_website").add(self.websiteBrowser)
        wTree.get_widget("scrolled_reviews").add(self.reviewsBrowser)

        # kill right click menus in webkit views
        self.browser.connect("button-press-event", lambda w, e: e.button == 3)
        self.browser2.connect("button-press-event", lambda w, e: e.button == 3)
        self.packageBrowser.connect("button-press-event", lambda w, e: e.button == 3)
        self.screenshotBrowser.connect("button-press-event", lambda w, e: e.button == 3)
        self.reviewsBrowser.connect("button-press-event", lambda w, e: e.button == 3)

        wTree.get_widget("label_ongoing").set_text(_("No ongoing actions"))
        wTree.get_widget("label_transactions_header").set_text(_("Active tasks:"))
        wTree.get_widget("progressbar1").hide_all()

        wTree.get_widget("button_transactions").connect("clicked", self.show_transactions)
        
        wTree.get_widget("tree_applications_scrolledview").get_vadjustment().connect("value-changed", self._on_tree_applications_scrolled, self.tree_applications)
        wTree.get_widget("tree_mixed_applications_scrolledview").get_vadjustment().connect("value-changed", self._on_tree_applications_scrolled, self.tree_mixed_applications)
        
        self._load_more_timer = None

        self.searchentry.grab_focus()
       
        wTree.get_widget("scrolled_search").get_vadjustment().connect("value-changed", self._on_search_applications_scrolled)
        self._load_more_search_timer = None
        self.initial_search_display=200 #number of packages shown on first search
        self.scroll_search_display=300 #number of packages added after scrolling
        
        wTree.get_widget("main_window").show_all()        
        
        self.generic_installed_icon_path = "/usr/lib/linuxmint/mintInstall/data/installed.png"
        self.generic_available_icon_path = "/usr/lib/linuxmint/mintInstall/data/available.png"        
        
        self.generic_installed_icon_pixbuf=gtk.gdk.pixbuf_new_from_file_at_size(self.generic_installed_icon_path, 32, 32)
        self.generic_available_icon_pixbuf=gtk.gdk.pixbuf_new_from_file_at_size(self.generic_available_icon_path, 32, 32)        
        
    
    def show_screenshots(self, pkg_name):
        if self.navigation_bar.get_active().get_label() == pkg_name:
            for screenshot_cmd in self.screenshots:
                self.packageBrowser.execute_script(screenshot_cmd)
    
    def on_search_entry_activated(self, searchentry):
        terms = searchentry.get_text()
        if terms != "":
            self.show_search_results(terms)
    
    def on_search_terms_changed(self, searchentry, terms):
        if terms != "" and self.prefs["search_while_typing"] and len(terms) >= 3:
            if terms!=self._current_search_terms:
              self.show_search_results(terms)

    def set_filter(self, checkmenuitem, configName):
        config = ConfigObj(home + "/.linuxmint/mintinstall.conf")
        if (config.has_key('filter')):
            config['filter'][configName] = checkmenuitem.get_active()
        else:
            config['filter'] = {}
            config['filter'][configName] = checkmenuitem.get_active()
        config.write()
        self.prefs = self.read_configuration()
        if self.model_filter is not None:
            self.model_filter.refilter()

    def set_search_filter(self, checkmenuitem, configName):
        config = ConfigObj(home + "/.linuxmint/mintinstall.conf")
        if (config.has_key('search')):
            config['search'][configName] = checkmenuitem.get_active()
        else:
            config['search'] = {}
            config['search'][configName] = checkmenuitem.get_active()
        config.write()
        self.prefs = self.read_configuration()
        if (self.searchentry.get_text() != ""):
            self.show_search_results(self.searchentry.get_text())

    def set_external_browser(self, checkmenuitem):
        config = ConfigObj(home + "/.linuxmint/mintinstall.conf")
        config['external_browser'] = checkmenuitem.get_active()
        config.write()
        self.prefs = self.read_configuration()

    def read_configuration(self):

        config = ConfigObj(home + "/.linuxmint/mintinstall.conf")
        prefs = {}

        #Read account info
        try:
            prefs["username"] = config['account']['username']
            prefs["password"] = config['account']['password']
        except:
            prefs["username"] = ""
            prefs["password"] = ""


        #Read filter info
        try:
            prefs["available_packages_visible"] = (config['filter']['available_packages_visible'] == "True")
        except:
            prefs["available_packages_visible"] = True
        try:
            prefs["installed_packages_visible"] = (config['filter']['installed_packages_visible'] == "True")
        except:
            prefs["installed_packages_visible"] = True

        #Read search info
        try:
            prefs["search_in_summary"] = (config['search']['search_in_summary'] == "True")
        except:
            prefs["search_in_summary"] = True
        try:
            prefs["search_in_description"] = (config['search']['search_in_description'] == "True")
        except:
            prefs["search_in_description"] = False
        try:
            prefs["search_while_typing"] = (config['search']['search_while_typing'] == "True")
        except:
            prefs["search_while_typing"] = True

        #External browser
        try:
            prefs["external_browser"] = (config['external_browser'] == "True")
        except:
            prefs["external_browser"] = False

        return prefs

    def open_repositories(self, widget):        
        if os.path.exists("/usr/bin/software-sources"):
            os.system("/usr/bin/software-sources")
        elif os.path.exists("/usr/bin/software-properties-gtk"):
            os.system("/usr/bin/software-properties-gtk")
        elif os.path.exists("/usr/bin/software-properties-kde"):
            os.system("/usr/bin/software-properties-kde")
        self.close_application(None, None, 9) # Status code 9 means we want to restart ourselves

    def open_account_info(self, widget):
        gladefile = "/usr/lib/linuxmint/mintInstall/mintinstall.glade"
        wTree = gtk.glade.XML(gladefile, "window_account")
        wTree.get_widget("window_account").set_title(_("Account information"))
        wTree.get_widget("window_account").set_icon_from_file("/usr/lib/linuxmint/mintInstall/icon.svg")
        wTree.get_widget("label1").set_label("<b>%s</b>" % _("Your community account"))
        wTree.get_widget("label1").set_use_markup(True)
        wTree.get_widget("label2").set_label("<i><small>%s</small></i>" % _("Fill in your account info to review applications"))
        wTree.get_widget("label2").set_use_markup(True)
        wTree.get_widget("label3").set_label(_("Username:"))
        wTree.get_widget("label4").set_label(_("Password:"))
        wTree.get_widget("entry_username").set_text(self.prefs["username"])
        wTree.get_widget("entry_password").set_text(base64.b64decode(self.prefs["password"]))
        wTree.get_widget("close_button").connect("clicked", self.close_window, wTree.get_widget("window_account"))
        wTree.get_widget("entry_username").connect("notify::text", self.update_account_info, "username")
        wTree.get_widget("entry_password").connect("notify::text", self.update_account_info, "password")
        wTree.get_widget("window_account").show_all()

    def close_window(self, widget, window):
        window.hide()

    def update_account_info(self, entry, prop, configName):
        config = ConfigObj(home + "/.linuxmint/mintinstall.conf")
        if (not config.has_key('account')):
            config['account'] = {}

        if (configName == "password"):
            text = base64.b64encode(entry.props.text)
        else:
            text = entry.props.text

        config['account'][configName] = text
        config.write()
        self.prefs = self.read_configuration()

    def open_about(self, widget):
        dlg = gtk.AboutDialog()
        dlg.set_title(_("About"))
        dlg.set_program_name("mintInstall")
        dlg.set_comments(_("Software Manager"))
        try:
            h = open('/usr/share/common-licenses/GPL','r')
            s = h.readlines()
            gpl = ""
            for line in s:
                gpl += line
            h.close()
            dlg.set_license(gpl)
        except Exception, detail:
            print detail
        try:
            version = commands.getoutput("/usr/lib/linuxmint/common/version.py mintinstall")
            dlg.set_version(version)
        except Exception, detail:
            print detail

        dlg.set_authors(["Clement Lefebvre <root@linuxmint.com>"])
        dlg.set_icon_from_file("/usr/lib/linuxmint/mintInstall/icon.svg")
        dlg.set_logo(gtk.gdk.pixbuf_new_from_file("/usr/lib/linuxmint/mintInstall/icon.svg"))
        def close(w, res):
            if res == gtk.RESPONSE_CANCEL:
                w.hide()
        dlg.connect("response", close)
        dlg.show()

    def export_listing(self):
        # packages
        for package in self.packages:
            if package.pkg.name.endswith(":i386") or package.pkg.name.endswith(":amd64"):
                continue
            summary = ""
            if package.pkg.candidate is not None:
                summary = package.pkg.candidate.summary
            summary = summary.capitalize()
            description = ""
            version = ""
            homepage = ""
            strSize = ""
            if package.pkg.candidate is not None:
                description = package.pkg.candidate.description
                version = package.pkg.candidate.version
                homepage = package.pkg.candidate.homepage
                strSize = str(package.pkg.candidate.size) + _("B")
                if (package.pkg.candidate.size >= 1000):
                    strSize = str(package.pkg.candidate.size / 1000) + _("KB")
                if (package.pkg.candidate.size >= 1000000):
                    strSize = str(package.pkg.candidate.size / 1000000) + _("MB")
                if (package.pkg.candidate.size >= 1000000000):
                    strSize = str(package.pkg.candidate.size / 1000000000) + _("GB")

            description = description.capitalize()
            description = description.replace("\r\n", "<br>")
            description = description.replace("\n", "<br>")
            output = package.pkg.name + "#~#" + version + "#~#" + homepage + "#~#" + strSize + "#~#" + summary + "#~#" + description + "#~#"
            for category in package.categories:
                output = output + category.name + ":::"
            if output[-3:] == (":::"):
                output = output[:-3]
            print output

    def show_transactions(self, widget):
        self.notebook.set_current_page(self.PAGE_TRANSACTIONS)

    def close_window(self, widget, window, extra=None):
        try:
            window.hide_all()
        except:
            pass

    def build_application_tree(self, treeview):
        column0 = gtk.TreeViewColumn(_("Icon"), gtk.CellRendererPixbuf(), pixbuf=0)
        column0.set_sort_column_id(0)
        column0.set_resizable(True)

        column1 = gtk.TreeViewColumn(_("Application"), gtk.CellRendererText(), markup=1)
        column1.set_sort_column_id(1)
        column1.set_resizable(True)
        column1.set_sizing(gtk.TREE_VIEW_COLUMN_FIXED)
        column1.set_min_width(350)
        column1.set_max_width(350)

        column2 = gtk.TreeViewColumn(_("Score"), gtk.CellRendererPixbuf(), pixbuf=2)
        column2.set_sort_column_id(2)
        column2.set_resizable(True)
        
        #prevents multiple load finished handlers being hooked up to packageBrowser in show_package
        self.loadHandlerID = -1
        self.acthread = threading.Thread(target=self.cache_apt)
        
        treeview.append_column(column0)
        treeview.append_column(column1)
        treeview.append_column(column2)
        treeview.set_headers_visible(False)
        treeview.connect("row-activated", self.show_selected)
        treeview.show()
        #treeview.connect("row_activated", self.show_more_info)

        selection = treeview.get_selection()
        selection.set_mode(gtk.SELECTION_BROWSE)

        #selection.connect("changed", self.show_selected)

    def build_transactions_tree(self, treeview):
        column0 = gtk.TreeViewColumn(_("Task"), gtk.CellRendererText(), text=0)
        column0.set_resizable(True)

        column1 = gtk.TreeViewColumn(_("Status"), gtk.CellRendererText(), text=1)
        column1.set_resizable(True)

        column2 = gtk.TreeViewColumn(_("Progress"), gtk.CellRendererProgress(), text=2, value=3)
        column2.set_resizable(True)

        treeview.append_column(column0)
        treeview.append_column(column1)
        treeview.append_column(column2)
        treeview.set_headers_visible(True)
        treeview.show()

    def show_selected(self, tree, path, column):
        #self.main_window.window.set_cursor(gtk.gdk.Cursor(gtk.gdk.WATCH))   
        #self.main_window.set_sensitive(False)
        model = tree.get_model()
        iter = model.get_iter(path)

        #poll for end of apt caching when idle
        glib.idle_add(self.show_package_if_apt_cached, model.get_value(iter, 3), tree)
        #cache apt in a separate thread as blocks gui update
        self.acthread.start()

    def show_package_if_apt_cached(self, pkg, tree):
        if (self.acthread.isAlive()):
            self.acthread.join()
        
        self.show_package(pkg, tree)
        self.acthread = threading.Thread(target=self.cache_apt) #rebuild here for speed
        return False #false will remove this from gtk's list of idle functions
        #return True

    def cache_apt(self):
        self.cache = apt.Cache()

    def show_more_info(self, tree, path, column):
        model = tree.get_model()
        iter = model.get_iter(path)
        self.selected_package = model.get_value(iter, 3)

    def navigate(self, button, destination):

        if (destination == "search"):
            self.notebook.set_current_page(self.PAGE_SEARCH)
        else:
            self.searchentry.set_text("")
            self._search_in_category = self.root_category
            if isinstance(destination, Category):
                self._search_in_category = destination
                if len(destination.subcategories) > 0:
                    if len(destination.packages) > 0:
                        self.notebook.set_current_page(self.PAGE_MIXED)
                    else:
                        self.notebook.set_current_page(self.PAGE_CATEGORIES)
                else:
                    self.notebook.set_current_page(self.PAGE_PACKAGES)
            elif isinstance(destination, Package):
                self.notebook.set_current_page(self.PAGE_DETAILS)
            elif (destination == "screenshot"):
                self.notebook.set_current_page(self.PAGE_SCREENSHOT)
            elif (destination == "reviews"):
                self.notebook.set_current_page(self.PAGE_REVIEWS)
            else:
                self.notebook.set_current_page(self.PAGE_WEBSITE)


    def close_application(self, window, event=None, exit_code=0):
        self.apt_client.call_on_completion(lambda c: self.do_close_application(c), exit_code)
        window.hide()
    
    def do_close_application(self, exit_code):
        if exit_code == 0:
            # Not happy with Python when it comes to closing threads, so here's a radical method to get what we want.
            pid = os.getpid()
            os.system("kill -9 %s &" % pid)
        else:            
            gtk.main_quit()
            sys.exit(exit_code)

    def _on_load_finished(self, view, frame):
        # Get the categories
        self.show_category(self.root_category)

    @print_timing
    def _on_package_load_finished(self, view, frame, package):        
        #Add the reviews
        reviews = package.reviews
        self.packageBrowser.execute_script('clearReviews()')
        reviews.sort(key=lambda x: x.date, reverse=True)
        if len(reviews) > 10:
            for review in reviews[0:10]:
                rating = "/usr/lib/linuxmint/mintInstall/data/small_" + str(review.rating) + ".png"
                comment = review.comment.strip()
                comment = comment.replace("'", "\'")
                comment = comment.replace('"', '\"')
                comment = comment.capitalize()
                comment = unicode(comment, 'UTF-8', 'replace')
                review_date = datetime.fromtimestamp(review.date).strftime("%Y.%m.%d")

                self.packageBrowser.execute_script('addReview("%s", "%s", "%s", "%s")' % (review_date, review.username, rating, comment))
            self.packageBrowser.execute_script('addLink("%s")' % _("See more reviews"))

        else:
            for review in reviews:
                rating = "/usr/lib/linuxmint/mintInstall/data/small_" + str(review.rating) + ".png"
                comment = review.comment.strip()
                comment = comment.replace("'", "\'")
                comment = comment.replace('"', '\"')
                comment = comment.capitalize()
                comment = unicode(comment, 'UTF-8', 'replace')
                review_date = datetime.fromtimestamp(review.date).strftime("%Y.%m.%d")

                self.packageBrowser.execute_script('addReview("%s", "%s", "%s", "%s")' % (review_date, review.username, rating, comment))
        #self.main_window.set_sensitive(True)
        #self.main_window.window.set_cursor(None)

        downloadScreenshots = ScreenshotDownloader(self, package.name)
        downloadScreenshots.start()

    def on_category_clicked(self, name):
        for category in self.categories:
            if category.name == name:
                self.show_category(category)

    def on_button_clicked(self):        
        package = self.current_package
        if package is not None:             
            if package.pkg.is_installed:
                self.apt_client.remove_package(package.pkg.name)
            else:
                if package.pkg.name not in BROKEN_PACKAGES:
                    self.apt_client.install_package(package.pkg.name)
    
    def on_screenshot_clicked(self, url):
        package = self.current_package
        if package is not None:
            template = open("/usr/lib/linuxmint/mintInstall/data/templates/ScreenshotView.html").read()
            subs = {}
            subs['url'] = url
            print "loading: '%s'" % url
            html = string.Template(template).safe_substitute(subs)
            self.screenshotBrowser.load_html_string(html, "file:/")
            self.navigation_bar.add_with_id(_("Screenshot"), self.navigate, self.NAVIGATION_SCREENSHOT, "screenshot")

    def on_website_clicked(self):
        package = self.current_package
        if package is not None:
            if self.prefs['external_browser']:
                os.system("xdg-open " + self.current_package.pkg.candidate.homepage + " &")
            else:
                self.websiteBrowser.open(self.current_package.pkg.candidate.homepage)
                self.navigation_bar.add_with_id(_("Website"), self.navigate, self.NAVIGATION_WEBSITE, "website")

    def on_reviews_clicked(self):
        package = self.current_package
        if package is not None:
            template = open("/usr/lib/linuxmint/mintInstall/data/templates/ReviewsView.html").read()
            subs = {}
            subs['appname'] = self.current_package.pkg.name
            subs['reviewsLabel'] = _("Reviews")
            font_description = gtk.Label("pango").get_pango_context().get_font_description()
            subs['font_family'] = font_description.get_family()
            try:
                subs['font_weight'] = font_description.get_weight().real
            except:
                subs['font_weight'] = font_description.get_weight()   
            subs['font_style'] = font_description.get_style().value_nick        
            subs['font_size'] = font_description.get_size() / 1024    
            html = string.Template(template).safe_substitute(subs)
            self.reviewsBrowser.load_html_string(html, "file:/")
            self.reviewsBrowser.connect("load-finished", self._on_reviews_load_finished, package.reviews)
            self.navigation_bar.add_with_id(_("Reviews"), self.navigate, self.NAVIGATION_REVIEWS, "reviews")

    def _on_reviews_load_finished(self, view, frame, reviews):
        #Add the reviews
        self.reviewsBrowser.execute_script('clearReviews()')
        reviews.sort(key=lambda x: x.date, reverse=True)
        for review in reviews:
            rating = "/usr/lib/linuxmint/mintInstall/data/small_" + str(review.rating) + ".png"
            comment = review.comment.strip()
            comment = comment.replace("'", "\'")
            comment = comment.replace('"', '\"')
            comment = comment.capitalize()
            comment = unicode(comment, 'UTF-8', 'replace')
            review_date = datetime.fromtimestamp(review.date).strftime("%Y.%m.%d")
            self.reviewsBrowser.execute_script('addReview("%s", "%s", "%s", "%s")' % (review_date, review.username, rating, comment))

    def _on_title_changed(self, view, frame, title):
        # no op - needed to reset the title after a action so that
        #        the action can be triggered again
        if title.startswith("nop"):
            return
        # call directive looks like:
        #  "call:func:arg1,arg2"
        #  "call:func"
        if title.startswith("call:"):
            args_str = ""
            args_list = []
            # try long form (with arguments) first            
            try:                
                elements = title.split(":")
                t = elements[0]
                funcname = elements[1]
                if len(elements) > 2:
                    args_str = ':'.join(elements[2:])
                    if args_str:
                        args_list = args_str.split(",")
            
                # see if we have it and if it can be called
                f = getattr(self, funcname)
                if f and callable(f):
                    f(*args_list)
                # now we need to reset the title
                self.browser.execute_script('window.setTimeout(function(){document.title = "nop"},0);') #setTimeout workaround: otherwise title parameter doesn't upgrade in callback causing show_category to be called twice
            except Exception, detail:
                print detail
                pass
            return            
            
    @print_timing
    def add_categories(self):
        self.categories = []
        self.root_category = Category(_("Categories"), "applications-other", None, None, self.categories)
        
        featured = Category(_("Featured"), "/usr/lib/linuxmint/mintInstall/data/templates/featured.svg", None, self.root_category, self.categories)
        featured.matchingPackages = self.file_to_array("/usr/lib/linuxmint/mintInstall/categories/featured.list")
        
        self.category_all = Category(_("All Packages"), "applications-other", None, self.root_category, self.categories)
        
        internet = Category(_("Internet"), "applications-internet", None, self.root_category, self.categories)
        subcat = Category(_("Web"), "web-browser", ("web", "net"), internet, self.categories)
        subcat.matchingPackages = self.file_to_array("/usr/lib/linuxmint/mintInstall/categories/internet-web.list")
        subcat = Category(_("Email"), "applications-mail", ("mail"), internet, self.categories)
        subcat.matchingPackages = self.file_to_array("/usr/lib/linuxmint/mintInstall/categories/internet-email.list")
        subcat = Category(_("Chat"), "xchat", None, internet, self.categories)
        subcat.matchingPackages = self.file_to_array("/usr/lib/linuxmint/mintInstall/categories/internet-chat.list")
        subcat = Category(_("File sharing"), "transmission", None, internet, self.categories)
        subcat.matchingPackages = self.file_to_array("/usr/lib/linuxmint/mintInstall/categories/internet-filesharing.list")
        
        cat = Category(_("Sound and video"), "applications-multimedia", ("multimedia", "video"), self.root_category, self.categories)
        cat.matchingPackages = self.file_to_array("/usr/lib/linuxmint/mintInstall/categories/sound-video.list")
        
        graphics = Category(_("Graphics"), "applications-graphics", ("graphics"), self.root_category, self.categories)
        graphics.matchingPackages = self.file_to_array("/usr/lib/linuxmint/mintInstall/categories/graphics.list")
        subcat = Category(_("3D"), "blender", None, graphics, self.categories)
        subcat.matchingPackages = self.file_to_array("/usr/lib/linuxmint/mintInstall/categories/graphics-3d.list")
        subcat = Category(_("Drawing"), "gimp", None, graphics, self.categories)
        subcat.matchingPackages = self.file_to_array("/usr/lib/linuxmint/mintInstall/categories/graphics-drawing.list")
        subcat = Category(_("Photography"), "shotwell", None, graphics, self.categories)
        subcat.matchingPackages = self.file_to_array("/usr/lib/linuxmint/mintInstall/categories/graphics-photography.list")
        subcat = Category(_("Publishing"), "scribus", None, graphics, self.categories)
        subcat.matchingPackages = self.file_to_array("/usr/lib/linuxmint/mintInstall/categories/graphics-publishing.list")
        subcat = Category(_("Scanning"), "flegita", None, graphics, self.categories)
        subcat.matchingPackages = self.file_to_array("/usr/lib/linuxmint/mintInstall/categories/graphics-scanning.list")
        subcat = Category(_("Viewers"), "gthumb", None, graphics, self.categories)
        subcat.matchingPackages = self.file_to_array("/usr/lib/linuxmint/mintInstall/categories/graphics-viewers.list")
        
        Category(_("Office"), "applications-office", ("office", "editors"), self.root_category, self.categories)
        
        games = Category(_("Games"), "applications-games", ("games"), self.root_category, self.categories)
        games.matchingPackages = self.file_to_array("/usr/lib/linuxmint/mintInstall/categories/games.list")
        subcat = Category(_("Board games"), "gnome-glchess", None, games, self.categories)
        subcat.matchingPackages = self.file_to_array("/usr/lib/linuxmint/mintInstall/categories/games-board.list")
        subcat = Category(_("First-person shooters"), "UrbanTerror", None, games, self.categories)
        subcat.matchingPackages = self.file_to_array("/usr/lib/linuxmint/mintInstall/categories/games-fps.list")
        subcat = Category(_("Real-time strategy"), "applications-games", None, games, self.categories)
        subcat.matchingPackages = self.file_to_array("/usr/lib/linuxmint/mintInstall/categories/games-rts.list")
        subcat = Category(_("Turn-based strategy"), "wormux", None, games, self.categories)
        subcat.matchingPackages = self.file_to_array("/usr/lib/linuxmint/mintInstall/categories/games-tbs.list")
        subcat = Category(_("Emulators"), "wine", None, games, self.categories)
        subcat.matchingPackages = self.file_to_array("/usr/lib/linuxmint/mintInstall/categories/games-emulators.list")
        subcat = Category(_("Simulation and racing"), "torcs", None, games, self.categories)
        subcat.matchingPackages = self.file_to_array("/usr/lib/linuxmint/mintInstall/categories/games-simulations.list")
        
        Category(_("Accessories"), "applications-utilities", ("accessories", "utils"), self.root_category, self.categories)

        cat = Category(_("System tools"), "applications-system", ("system", "admin"), self.root_category, self.categories)
        cat.matchingPackages = self.file_to_array("/usr/lib/linuxmint/mintInstall/categories/system-tools.list")

        subcat = Category(_("Fonts"), "applications-fonts", ("fonts"), self.root_category, self.categories)
        subcat.matchingPackages = self.file_to_array("/usr/lib/linuxmint/mintInstall/categories/fonts.list")
               
        subcat = Category(_("Science and Education"), "applications-science", ("science", "math", "education"), self.root_category, self.categories)
        subcat.matchingPackages = self.file_to_array("/usr/lib/linuxmint/mintInstall/categories/education.list")

        Category(_("Programming"), "applications-development", ("devel", "java"), self.root_category, self.categories)
        #self.category_other = Category(_("Other"), "applications-other", None, self.root_category, self.categories)        

    def file_to_array(self, filename):
        array = []
        f = open(filename)
        for line in f:
            line = line.replace("\n","").replace("\r","").strip();
            if line != "":
                array.append(line)
        return array


    @print_timing
    def build_matched_packages(self):
        # Build a list of matched packages
        self.matchedPackages = []
        for category in self.categories:
            self.matchedPackages.extend(category.matchingPackages)
        self.matchedPackages.sort()

    @print_timing
    def add_packages(self):
        self.packages = []
        self.packages_dict = {}
        cache = apt.Cache()         
                                                
        for pkg in cache:
            package = Package(pkg.name, pkg)
            self.packages.append(package)
            self.packages_dict[pkg.name] = package
            self.category_all.packages.append(package)

            # If the package is not a "matching package", find categories with matching sections
            if (pkg.name not in self.matchedPackages):
                section = pkg.section
                if "/" in section:
                    section = section.split("/")[1]
                for category in self.categories:
                    if category.sections is not None:
                        if section in category.sections:
                            self.add_package_to_category(package, category)
     
        # Process matching packages
        for category in self.categories:
            for package_name in category.matchingPackages:              
                try:
                    package = self.packages_dict[package_name]                  
                    self.add_package_to_category(package, category)
                except Exception, detail:
                    pass
                    #print detail
        
        

    def add_package_to_category(self, package, category):
        if category.parent is not None:
            if category not in package.categories:
                package.categories.append(category)
                category.packages.append(package)
            self.add_package_to_category(package, category.parent)

    @print_timing
    def add_reviews(self):
        reviews_path = home + "/.linuxmint/mintinstall/reviews.list"
        if not os.path.exists(reviews_path):
            # No reviews found, use the ones from the packages itself
            os.system("cp /usr/lib/linuxmint/mintInstall/reviews.list %s" % reviews_path)
            print "First run detected, initial set of reviews used"
            
        with open(reviews_path) as reviews:
          last_package = None
          for line in reviews:
              elements = line.split("~~~")
              if len(elements) == 5:
                  review = Review(elements[0], float(elements[1]), elements[2], elements[3], elements[4])
                  if last_package != None and last_package.name == elements[0]:
                      #Comment is on the same package as previous comment.. no need to search for the package
                      last_package.reviews.append(review)
                      review.package = last_package
                      last_package.update_stats()
                  else:
                      if elements[0] in self.packages_dict:
                          package = self.packages_dict[elements[0]]
                          last_package = package
                          package.reviews.append(review)
                          review.package = package
                          package.update_stats()
        
            

    @print_timing
    def update_reviews(self):
        reviews_path = home + "/.linuxmint/mintinstall/reviews.list"
        if os.path.exists(reviews_path):
            reviews = open(reviews_path)
            last_package = None
            for line in reviews:
                elements = line.split("~~~")
                if len(elements) == 5:
                    review = Review(elements[0], float(elements[1]), elements[2], elements[3], elements[4])
                    if last_package != None and last_package.name == elements[0]:
                        #Comment is on the same package as previous comment.. no need to search for the package
                        alreadyThere = False
                        for rev in last_package.reviews:
                            if rev.username == elements[2]:
                                alreadyThere = True
                                break
                        if not alreadyThere:
                            last_package.reviews.append(review)
                            review.package = last_package
                            last_package.update_stats()
                    else:
                        if elements[0] in self.packages_dict:
                            package = self.packages_dict[elements[0]]
                            last_package = package
                            alreadyThere = False
                            for rev in package.reviews:
                                if rev.username == elements[2]:
                                    alreadyThere = True
                                    break
                            if not alreadyThere:
                                package.reviews.append(review)
                                review.package = package
                                package.update_stats()
    
    def _on_tree_applications_scrolled(self, adjustment, tree_applications):
        if self._load_more_timer:
            gobject.source_remove(self._load_more_timer)
        self._load_more_timer = gobject.timeout_add(500, self._load_more_packages, tree_applications)
    
    
    def show_dialog_modal(self, title, text, type, buttons):
        gobject.idle_add(self._show_dialog_modal_callback, title, text, type, buttons) #as this might not be called from the main thread
         
    def _show_dialog_modal_callback(self, title, text, type, buttons):
        dialog=gtk.MessageDialog(self.main_window ,flags=gtk.DIALOG_MODAL | gtk.DIALOG_DESTROY_WITH_PARENT, type=type, buttons=buttons, message_format=title)
        dialog.format_secondary_markup(text)
        dialog.connect('response', self._show_dialog_modal_clicked, dialog)
        dialog.show()
    
    def _show_dialog_modal_clicked(self, dialog, *args):
      dialog.destroy()
      
    
    def _load_more_packages(self, tree_applications):
        self._load_more_timer = None
        
        adjustment = tree_applications.get_vadjustment()
        if adjustment.get_value() + adjustment.get_page_size() > 0.90 * adjustment.get_upper():
            if len(self._listed_packages) > self._nb_displayed_packages:
                packages_to_show = self._listed_packages[self._nb_displayed_packages:self._nb_displayed_packages+500]
                self.display_packages_list(packages_to_show, False)
                self._nb_displayed_packages = min(len(self._listed_packages), self._nb_displayed_packages + 500)
        return False
    
    def display_packages_list(self, packages_list, searchTree):
        sans26  =  ImageFont.truetype ( self.FONT, 26 )
        sans10  =  ImageFont.truetype ( self.FONT, 12 )
        
        model_applications=None
        
        if searchTree:
            model_applications=self._model_applications_search
        else:
            model_applications=self._model_applications
        
        
        for package in packages_list:
            
            if (not searchTree and package.name in COMMERCIAL_APPS):
                continue
            
            iter = model_applications.insert_before(None, None)
            
            model_applications.set_value(iter, 0, self.get_package_pixbuf_icon(package))
                    
            summary = ""
            if package.candidate is not None:
                summary = package.candidate.summary
                summary = unicode(summary, 'UTF-8', 'replace')
                summary = summary.replace("<", "&lt;")
                summary = summary.replace("&", "&amp;")

            model_applications.set_value(iter, 1, "%s\n<small><span foreground='#555555'>%s</span></small>" % (package.name, summary.capitalize()))

            if package.num_reviews > 0:
                image = "/usr/lib/linuxmint/mintInstall/data/" + str(package.avg_rating) + ".png"
                im=Image.open(image)
                draw = ImageDraw.Draw(im)

                color = "#000000"
                if package.score < 0:
                    color = "#AA5555"
                elif package.score > 0:
                    color = "#55AA55"
                draw.text((87, 9), str(package.score), font=sans26, fill="#AAAAAA")
                draw.text((86, 8), str(package.score), font=sans26, fill="#555555")
                draw.text((85, 7), str(package.score), font=sans26, fill=color)
                draw.text((13, 33), u"%s" % (_("%d reviews") % package.num_reviews), font=sans10, fill="#555555")
                
                model_applications.set_value(iter, 2, convertImageToGtkPixbuf(im))

            model_applications.set_value(iter, 3, package)
    
    @print_timing
    def show_category(self, category):
        self._search_in_category = category
        # Load subcategories
        if len(category.subcategories) > 0:
            if len(category.packages) == 0:
                # Show categories page
                browser = self.browser
                size = 96
            else:
                # Show mixed page
                browser = self.browser2
                size = 64

            browser.execute_script('clearCategories()')
            theme = gtk.icon_theme_get_default()
            for cat in category.subcategories:
                icon = None               
                if theme.has_icon(cat.icon):                   
                    iconInfo = theme.lookup_icon(cat.icon, size, 0)
                    if iconInfo and os.path.exists(iconInfo.get_filename()):
                        icon = iconInfo.get_filename()              
                if icon == None:
                    if os.path.exists(cat.icon):
                        icon = cat.icon
                    else:
                        iconInfo = theme.lookup_icon("applications-other", size, 0)
                        if iconInfo and os.path.exists(iconInfo.get_filename()):
                            icon = iconInfo.get_filename()
                browser.execute_script('addCategory("%s", "%s", "%s")' % (cat.name, _("%d packages") % len(cat.packages), icon))

        # Load packages into self.tree_applications
        if (len(category.subcategories) == 0):
            # Show packages
            tree_applications = self.tree_applications
        else:
            tree_applications = self.tree_mixed_applications

        self._model_applications = gtk.TreeStore(gtk.gdk.Pixbuf, str, gtk.gdk.Pixbuf, object)

        self.model_filter = self._model_applications.filter_new()
        self.model_filter.set_visible_func(self.visible_func)

        
        self._listed_packages = category.packages
        self._listed_packages.sort(self.package_compare)
        self._nb_displayed_packages = min(len(self._listed_packages), 200)
        self.display_packages_list(self._listed_packages[0:200], False)

        tree_applications.set_model(self.model_filter)
        first = self._model_applications.get_iter_first()

        # Update the navigation bar
        if category == self.root_category:
            self.navigation_bar.add_with_id(category.name, self.navigate, self.NAVIGATION_HOME, category)
        elif category.parent == self.root_category:
            self.navigation_bar.add_with_id(category.name, self.navigate, self.NAVIGATION_CATEGORY, category)
        else:
            self.navigation_bar.add_with_id(category.name, self.navigate, self.NAVIGATION_SUB_CATEGORY, category)
    
    
    
    
    
    
    def get_package_pixbuf_icon(self, package):
        icon_path=None
        
        try:
            icon_path = self.find_app_icon(package)
        except:
            try:
                icon_path = self.find_app_icon_alternative(package)
            except:
                icon_path = self.find_fallback_icon(package)
        
        #get cached generic icons, so they aren't converted repetitively
        if icon_path==self.generic_installed_icon_path:
            return self.generic_installed_icon_pixbuf
        if icon_path==self.generic_available_icon_path:
            return self.generic_available_icon_pixbuf
        
        return gtk.gdk.pixbuf_new_from_file_at_size(icon_path, 32, 32)
    
    
    
    def find_fallback_icon(self, package):
        if package.pkg.is_installed:
            icon_path = self.generic_installed_icon_path
        else:
            icon_path = self.generic_available_icon_path
        return icon_path
            
    def find_app_icon_alternative(self, package):        
        icon_path = None
        if package.pkg.is_installed:
            icon_path = "/usr/share/linuxmint/mintinstall/installed/%s" % package.name
            if os.path.exists(icon_path + ".png"):
                icon_path = icon_path + ".png"
            elif os.path.exists(icon_path + ".xpm"):
                icon_path = icon_path + ".xpm"
            else:
                # Else, default to generic icons
                icon_path = self.generic_installed_icon_path
        else:          
            # Try the Icon theme first
            theme = gtk.icon_theme_get_default()
            if theme.has_icon(package.name):
                iconInfo = theme.lookup_icon(package.name, 32, 0)
                if iconInfo and os.path.exists(iconInfo.get_filename()):
                    icon_path = iconInfo.get_filename()
            else:
                # Try mintinstall-icons then
                icon_path = "/usr/share/linuxmint/mintinstall/icons/%s" % package.name
                if os.path.exists(icon_path + ".png"):
                    icon_path = icon_path + ".png"
                elif os.path.exists(icon_path + ".xpm"):
                    icon_path = icon_path + ".xpm"
                else:
                    # Else, default to generic icons
                    icon_path = self.generic_available_icon_path
        return icon_path
    
    def find_app_icon(self, package):
        icon_path = None
        # Try the Icon theme first
        theme = gtk.icon_theme_get_default()
        if theme.has_icon(package.name):
            iconInfo = theme.lookup_icon(package.name, 32, 0)
            if iconInfo and os.path.exists(iconInfo.get_filename()):
                icon_path = iconInfo.get_filename()

        # If - is in the name, try the first part of the name (for instance "steam" instead of "steam-launcher")
        if icon_path is None and "-" in package.name:
            name = package.name.split("-")[0]
            if theme.has_icon(name):
                iconInfo = theme.lookup_icon(name, 32, 0)
                if iconInfo and os.path.exists(iconInfo.get_filename()):
                    icon_path = iconInfo.get_filename()

        if icon_path is not None:
            if package.pkg.is_installed:
                im=Image.open(icon_path)
                bg_w,bg_h=im.size
                im2=Image.open("/usr/lib/linuxmint/mintInstall/data/emblem-installed.png")
                img_w,img_h=im2.size 
                offset=(17,17)         
                im.paste(im2, offset,im2)
                tmpFile = tempfile.NamedTemporaryFile(delete=False)
                im.save (tmpFile.name + ".png")             
                icon_path = tmpFile.name + ".png"               
        else:
            # Try mintinstall-icons then
            if package.pkg.is_installed:
                icon_path = "/usr/share/linuxmint/mintinstall/installed/%s" % package.name
            else:
                icon_path = "/usr/share/linuxmint/mintinstall/icons/%s" % package.name
            
            if os.path.exists(icon_path + ".png"):
                icon_path = icon_path + ".png"
            elif os.path.exists(icon_path + ".xpm"):
                icon_path = icon_path + ".xpm"
            else:
                # Else, default to generic icons                
                if package.pkg.is_installed:
                    icon_path = self.generic_installed_icon_path
                else:
                    icon_path = self.generic_available_icon_path
                                            
        return icon_path
    
                
    def find_large_app_icon(self, package):
        theme = gtk.icon_theme_get_default()
        if theme.has_icon(package.name):
            iconInfo = theme.lookup_icon(package.name, 64, 0)
            if iconInfo and os.path.exists(iconInfo.get_filename()):
                return iconInfo.get_filename()
                
        # If - is in the name, try the first part of the name (for instance "steam" instead of "steam-launcher")
        if "-" in package.name:
            name = package.name.split("-")[0]
            if theme.has_icon(name):
                iconInfo = theme.lookup_icon(name, 64, 0)
                if iconInfo and os.path.exists(iconInfo.get_filename()):
                    return iconInfo.get_filename()

        iconInfo = theme.lookup_icon("applications-other", 64, 0)       
        return iconInfo.get_filename()
    
    def _show_all_search_results(self):
        self._search_in_category = self.root_category
        self.show_search_results(self._current_search_terms)
	
	
	
    
    def _on_search_applications_scrolled(self, adjustment):
        if self._load_more_search_timer:
            gobject.source_remove(self._load_more_search_timer)
        self._load_more_search_timer = gobject.timeout_add(500, self._load_more_search_packages)
    
    
    def _load_more_search_packages(self):
        self._load_more_search_timer = None
        adjustment = self.tree_search.get_vadjustment()
        if adjustment.get_value() + adjustment.get_page_size() > 0.90 * adjustment.get_upper():
            if len(self._searched_packages) > self._nb_displayed_search_packages:
                packages_to_show = self._searched_packages[self._nb_displayed_search_packages:self._nb_displayed_search_packages+self.scroll_search_display]
                self.display_packages_list(packages_to_show, True)
                self._nb_displayed_search_packages = min(len(self._searched_packages), self._nb_displayed_search_packages + self.scroll_search_display)
        return False
	
	
	
    @print_timing
    def show_search_results(self, terms):
        self._current_search_terms = terms
        # Load packages into self.tree_search
        model_applications = gtk.TreeStore(gtk.gdk.Pixbuf, str, gtk.gdk.Pixbuf, object)
        
        self._model_applications_search=model_applications
        
        self.model_filter = model_applications.filter_new()
        self.model_filter.set_visible_func(self.visible_func)

        sans26  =  ImageFont.truetype ( self.FONT, 26 )
        sans10  =  ImageFont.truetype ( self.FONT, 12 )
        
        
        termsUpper=terms.upper()
        
        if self._search_in_category == self.root_category:
            packages = self.packages
        else:
            packages = self._search_in_category.packages
        
        
        self._searched_packages=[]
        
        for package in packages:
            visible = False
            if termsUpper in package.name.upper():
                visible = True
            else:
                if (package.candidate is not None):
                    if (self.prefs["search_in_summary"] and termsUpper in package.summary.upper()):
                        visible = True
                    elif(self.prefs["search_in_description"] and termsUpper in package.candidate.description.upper()):
                        visible = True
            
            if visible:
                self._searched_packages.append(package)
        
        
        self._searched_packages.sort(self.package_compare)
        
        
        self._nb_displayed_search_packages = min(len(self._searched_packages), self.initial_search_display)
        self.display_packages_list(self._searched_packages[0:self.initial_search_display], True)
        
        
        self.tree_search.set_model(self.model_filter)
        del model_applications
        if self._search_in_category != self.root_category:
            self.search_in_category_hbox.show()
            self.message_search_in_category_label.set_markup("<b>%s</b>" % (_("Only results in category \"%s\" are shown." % self._search_in_category.name)))
        if self._search_in_category == self.root_category:
            self.search_in_category_hbox.hide()
            self.navigation_bar.add_with_id(self._search_in_category.name, self.navigate, self.NAVIGATION_HOME, self._search_in_category)
            navigation_id = self.NAVIGATION_SEARCH
        elif self._search_in_category.parent == self.root_category:
            self.navigation_bar.add_with_id(self._search_in_category.name, self.navigate, self.NAVIGATION_CATEGORY, self._search_in_category)
            navigation_id = self.NAVIGATION_SEARCH_CATEGORY
        else:
            self.navigation_bar.add_with_id(self._search_in_category.name, self.navigate, self.NAVIGATION_SUB_CATEGORY, self._search_in_category)
            navigation_id = self.NAVIGATION_SEARCH_SUB_CATEGORY
        self.navigation_bar.add_with_id(_("Search results"), self.navigate, navigation_id, "search")

    def visible_func(self, model, iter):
        package = model.get_value(iter, 3)
        if package is not None:
            if package.pkg is not None:
                if (package.pkg.is_installed and self.prefs["installed_packages_visible"] == True):
                    return True
                elif (package.pkg.is_installed == False and self.prefs["available_packages_visible"] == True):
                    return True
        return False

    @print_timing
    def show_package(self, package, tree):

        self.current_package = package
                
        # Load package info
        subs = {}
        subs['username'] = self.prefs["username"]
        subs['password'] = self.prefs["password"]
        subs['comment'] = ""
        subs['score'] = 0
        
        font_description = gtk.Label("pango").get_pango_context().get_font_description()
        subs['font_family'] = font_description.get_family()
        try:
            subs['font_weight'] = font_description.get_weight().real
        except:
            subs['font_weight'] = font_description.get_weight()   
        subs['font_style'] = font_description.get_style().value_nick        
        subs['font_size'] = font_description.get_size() / 1024      

        if self.prefs["username"] != "":
            for review in package.reviews:
                if review.username == self.prefs["username"]:
                    subs['comment'] = review.comment
                    subs['score'] = review.rating

        score_options = ["", _("Hate it"), _("Not a fan"), _("So so"), _("Like it"), _("Awesome!")]
        subs['score_options'] = ""
        for score in range(6):
            if (score == subs['score']):
                option = "<option value=%d %s>%s</option>" % (score, "SELECTED", score_options[score])
            else:
                option = "<option value=%d %s>%s</option>" % (score, "", score_options[score])

            subs['score_options'] = subs['score_options'] + option

        subs['iconbig'] = self.find_large_app_icon(package)

        subs['appname'] = package.name
        subs['pkgname'] = package.pkg.name
        subs['description'] = package.pkg.candidate.description
        subs['description'] = subs['description'].replace('\n','<br />\n')
        subs['summary'] = package.pkg.candidate.summary.capitalize()
        subs['label_score'] = _("Score:")
        subs['label_submit'] = _("Submit")
        subs['label_your_review'] = _("Your review")

        impacted_packages = []    
        pkg = self.cache[package.name]
        if package.pkg.is_installed:
            pkg.mark_delete(True, True)
        else:
            pkg.mark_install()
    
        changes = self.cache.get_changes()
        for pkg in changes:
            if (pkg.is_installed):
                impacted_packages.append(_("%s (removed)") % pkg.name)
            else:
                impacted_packages.append(_("%s (installed)") % pkg.name)
        
        downloadSize = str(self.cache.required_download) + _("B")
        if (self.cache.required_download >= 1000):
            downloadSize = str(self.cache.required_download / 1000) + _("KB")
        if (self.cache.required_download >= 1000000):
            downloadSize = str(self.cache.required_download / 1000000) + _("MB")
        if (self.cache.required_download >= 1000000000):
            downloadSize = str(self.cache.required_download / 1000000000) + _("GB")
                   
        required_space = self.cache.required_space
        if (required_space < 0):
            required_space = (-1) * required_space          
        localSize = str(required_space) + _("B")
        if (required_space >= 1000):
            localSize = str(required_space / 1000) + _("KB")
        if (required_space >= 1000000):
            localSize = str(required_space / 1000000) + _("MB")
        if (required_space >= 1000000000):
            localSize = str(required_space / 1000000000) + _("GB")

        subs['sizeLabel'] = _("Size:")
        subs['versionLabel'] = _("Version:")
        subs['impactLabel'] = _("Impact on packages:")
        subs['reviewsLabel'] = _("Reviews")
        subs['yourReviewLabel'] = _("Your review:")
        subs['detailsLabel'] = _("Details")
        
        if package.pkg.is_installed:
            if self.cache.required_space < 0:
                subs['sizeinfo'] = _("%(localSize)s of disk space freed") % {'localSize': localSize}
            else:
                subs['sizeinfo'] = _("%(localSize)s of disk space required") % {'localSize': localSize}
        else:
            if self.cache.required_space < 0:
                subs['sizeinfo'] = _("%(downloadSize)s to download, %(localSize)s of disk space freed") % {'downloadSize': downloadSize, 'localSize': localSize}
            else:
                subs['sizeinfo'] = _("%(downloadSize)s to download, %(localSize)s of disk space required") % {'downloadSize': downloadSize, 'localSize': localSize}
            
        subs['packagesinfo'] = (', '.join(name for name in impacted_packages))

        if len(package.pkg.candidate.homepage) > 0:
            subs['homepage'] = package.pkg.candidate.homepage
            subs['homepage_button_visibility'] = "visible"
        else:
            subs['homepage'] = ""
            subs['homepage_button_visibility'] = "hidden"
        
        direction = gtk.widget_get_default_direction()
        if direction ==  gtk.TEXT_DIR_RTL:
            subs['text_direction'] = 'DIR="RTL"'
        elif direction ==  gtk.TEXT_DIR_LTR:
            subs['text_direction'] = 'DIR="LTR"'

        if package.pkg.is_installed:
            subs['action_button_label'] = _("Remove")
            subs['action_button_value'] = "remove"
            subs['version'] = package.pkg.installed.version
            subs['action_button_description'] = _("Installed")
            subs['iconstatus'] = "/usr/lib/linuxmint/mintInstall/data/installed.png"
        else:
            if package.pkg.name in BROKEN_PACKAGES:           
                subs['action_button_label'] = _("Not available")
                subs['action_button_value'] = "remove"
                subs['version'] = package.pkg.candidate.version
                subs['action_button_description'] = _("Please use apt-get to install this package.")
                subs['iconstatus'] = "/usr/lib/linuxmint/mintInstall/data/available.png"
            else:
                subs['action_button_label'] = _("Install")
                subs['action_button_value'] = "install"
                subs['version'] = package.pkg.candidate.version
                subs['action_button_description'] = _("Not installed")
                subs['iconstatus'] = "/usr/lib/linuxmint/mintInstall/data/available.png"

        if package.num_reviews > 0:
            sans26 = ImageFont.truetype(self.FONT, 26)
            sans10 = ImageFont.truetype(self.FONT, 12)
            image = "/usr/lib/linuxmint/mintInstall/data/" + str(package.avg_rating) + ".png"
            im=Image.open(image)
            draw = ImageDraw.Draw(im)
            color = "#000000"
            if package.score < 0:
                color = "#AA5555"
            elif package.score > 0:
                color = "#55AA55"
            draw.text((87, 9), str(package.score), font=sans26, fill="#AAAAAA")
            draw.text((86, 8), str(package.score), font=sans26, fill="#555555")
            draw.text((85, 7), str(package.score), font=sans26, fill=color)
            draw.text((13, 33), u"%s" % (_("%d reviews") % package.num_reviews), font=sans10, fill="#555555")
            tmpFile = tempfile.NamedTemporaryFile(delete=True)
            im.save (tmpFile.name + ".png")
            subs['rating'] = tmpFile.name + ".png"
            subs['reviews'] = "<b>" + _("Reviews:") + "</b>"
        else:
            subs['rating'] = "/usr/lib/linuxmint/mintInstall/data/no-reviews.png"
            subs['reviews'] = ""

        template = open("/usr/lib/linuxmint/mintInstall/data/templates/PackageView.html")        
        html = string.Template(template.read()).safe_substitute(subs)
        self.packageBrowser.load_html_string(html, "file:/")
        template.close()
        
        if self.loadHandlerID != -1:
            self.packageBrowser.disconnect(self.loadHandlerID)
        
        self.loadHandlerID = self.packageBrowser.connect("load-finished", self._on_package_load_finished, package)       

        # Update the navigation bar
        self.navigation_bar.add_with_id(package.name, self.navigate, self.NAVIGATION_ITEM, package)


    def package_compare(self, x, y):
        if x.score == y.score:
            if x.name < y.name:
                return -1
            elif x.name > y.name:
                return 1
            else:
                return 0

        if x.score > y.score:
            return -1
        else:  #x < y
            return 1

if __name__ == "__main__":
    os.system("mkdir -p " + home + "/.linuxmint/mintinstall/screenshots/")
    #splash_process = Popen("/usr/lib/linuxmint/mintInstall/splash.py")
    model = Classes.Model()
    Application()
    #os.system("kill -9 %d" % splash_process.pid)
    gtk.main()

########NEW FILE########
__FILENAME__ = remove
#!/usr/bin/env python

try:
     import pygtk
     pygtk.require("2.0")
except:
      pass
try:
    import sys
    import string
    import gtk
    import gtk.glade
    import os
    import commands
    import threading
    import tempfile
    import gettext
    from user import home
	
except Exception, detail:
    print detail
    sys.exit(1)

from subprocess import Popen, PIPE

gtk.gdk.threads_init()

# i18n
gettext.install("mintinstall", "/usr/share/linuxmint/locale")

class RemoveExecuter(threading.Thread):

    def __init__(self, window_id, packages):
	threading.Thread.__init__(self)
	self.window_id = window_id
	self.packages = packages
    
    def execute(self, command):
	#print "Executing: " + command
	os.system(command)
	ret = commands.getoutput("echo $?")
	return ret

    def run(self):		
	cmd = ["sudo", "/usr/sbin/synaptic", "--hide-main-window",  \
	        "--non-interactive", "--parent-window-id", self.window_id]
	cmd.append("--progress-str")
	cmd.append("\"" + _("Please wait, this can take some time") + "\"")
	cmd.append("--finish-str")
	cmd.append("\"" + _("Application removed successfully") + "\"")
	f = tempfile.NamedTemporaryFile()
	for pkg in self.packages:
            f.write("%s\tdeinstall\n" % pkg)
        cmd.append("--set-selections-file")
        cmd.append("%s" % f.name)
        f.flush()
        comnd = Popen(' '.join(cmd), shell=True)
	returnCode = comnd.wait()
	f.close()
	gtk.main_quit()
	sys.exit(0)
		
class mintRemoveWindow:

    def __init__(self, mintFile):
	self.mintFile = mintFile

	if os.path.exists(self.mintFile):			
		directory = home + "/.linuxmint/mintInstall/tmp/mintFile"
		os.system("mkdir -p " + directory)
		os.system("rm -rf " + directory + "/*") 
		os.system("cp " + self.mintFile + " " + directory + "/file.mint")
		os.system("tar zxf " + directory + "/file.mint -C " + directory)
		appName = commands.getoutput("cat " + directory + "/name")
		steps = int(commands.getoutput("ls -l " + directory + "/steps/ | wc -l"))
		steps = steps -1
		repositories = []
		packages = []
		for i in range(steps + 1):
			if (i > 0):			
				openfile = open(directory + "/steps/"+str(i), 'r' )
				datalist = openfile.readlines()
				for j in range( len( datalist ) ):
				    if (str.find(datalist[j], "INSTALL") > -1):
					install = datalist[j][8:]
					install = str.strip(install)
					packages.append(install)						   					
				openfile.close()		
					
        #Set the Glade file
        self.gladefile = "/usr/lib/linuxmint/mintInstall/remove.glade"
        wTree = gtk.glade.XML(self.gladefile,"main_window")
	wTree.get_widget("main_window").set_icon_from_file("/usr/lib/linuxmint/mintInstall/icon.svg")
	wTree.get_widget("main_window").set_title("")
	wTree.get_widget("main_window").connect("destroy", self.giveUp)

	# Get the window socket (needed for synaptic later on)
	vbox = wTree.get_widget("vbox1")
	socket = gtk.Socket()
	vbox.pack_start(socket)
	socket.show()
	window_id = repr(socket.get_id())
        
	wTree.get_widget("txt_name").set_text("<big><b>" + _("Remove %s?") % (appName) + "</b></big>")
	wTree.get_widget("txt_name").set_use_markup(True)

	wTree.get_widget("txt_guidance").set_text(_("The following packages will be removed:"))
	
	treeview = wTree.get_widget("tree")
	column1 = gtk.TreeViewColumn()
	renderer = gtk.CellRendererText()
	column1.pack_start(renderer, False)
	column1.set_attributes(renderer, text = 0)
	treeview.append_column(column1)
	treeview.set_headers_visible(False)

	model = gtk.ListStore(str)

	for package in packages:		
		dependenciesString = commands.getoutput("apt-get -s -q remove " + package + " | grep Remv")
		dependencies = string.split(dependenciesString, "\n")
		for dependency in dependencies:
			dependency = dependency.replace("Remv ", "")
			model.append([dependency])

	treeview.set_model(model)
	treeview.show()		

        dic = {"on_remove_button_clicked" : (self.MainButtonClicked, window_id, packages, wTree),
               "on_cancel_button_clicked" : (self.giveUp) }
        wTree.signal_autoconnect(dic)

	wTree.get_widget("main_window").show()


    def MainButtonClicked(self, widget, window_id, packages, wTree):
	wTree.get_widget("main_window").window.set_cursor(gtk.gdk.Cursor(gtk.gdk.WATCH))
	wTree.get_widget("main_window").set_sensitive(False)
	executer = RemoveExecuter(window_id, packages)
	executer.start()
	return True

    def giveUp(self, widget):
	gtk.main_quit()
	sys.exit(0)

if __name__ == "__main__":
    mainwin = mintRemoveWindow(sys.argv[1])
    gtk.main()
    

########NEW FILE########
__FILENAME__ = splash
#!/usr/bin/python
# -*- coding: UTF-8 -*-
import gtk
import gtk.glade
import pygtk
import os
import gettext
import webkit
import string
import apt
print os.getpid()

# i18n
gettext.install("mintinstall", "/usr/share/linuxmint/locale")

# Build the GUI
gladefile = "/usr/lib/linuxmint/mintInstall/splash.glade"
wTree = gtk.glade.XML(gladefile, "splash_window")
splash_window = wTree.get_widget("splash_window")
splash_window.set_title(_("Software Manager"))
splash_window.set_icon_from_file("/usr/lib/linuxmint/mintInstall/data/templates/featured.svg")

browser = webkit.WebView()
wTree.get_widget("vbox1").add(browser)
browser.connect("button-press-event", lambda w, e: e.button == 3)
subs = {}
subs['title'] = _("Software Manager")
subs['subtitle'] = _("Gathering information for %d packages...") % len(apt.Cache())
font_description = gtk.Label("pango").get_pango_context().get_font_description()
subs['font_family'] = font_description.get_family()
try:
    subs['font_weight'] = font_description.get_weight().real
except:
    subs['font_weight'] = font_description.get_weight()   
subs['font_style'] = font_description.get_style().value_nick        
subs['font_size'] = font_description.get_size() / 1024      
template = open("/usr/lib/linuxmint/mintInstall/data/templates/splash.html").read()
html = string.Template(template).safe_substitute(subs)
browser.load_html_string(html, "file:/")

splash_window.show_all()
gtk.main()

########NEW FILE########
__FILENAME__ = animatedimage
# Copyright (C) 2009 Canonical
#
# Authors:
#  Michael Vogt
#  Andrew Higginson (rugby471)
#
# This program is free software; you can redistribute it and/or modify it under
# the terms of the GNU General Public License as published by the Free Software
# Foundation; version 3.
#
# This program is distributed in the hope that it will be useful, but WITHOUT
# ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS
# FOR A PARTICULAR PURPOSE.  See the GNU General Public License for more
# details.
#
# You should have received a copy of the GNU General Public License along with
# this program; if not, write to the Free Software Foundation, Inc.,
# 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301 USA

import gobject
import gtk
import os
import glob
import time

class AnimatedImage(gtk.Image):
    
    FPS = 20.0
    SIZE = 24

    def __init__(self, icon):
        """ Animate a gtk.Image
    
        Keywords:
        icon: pass either:
              - None - creates empty image with self.SIZE
              - string - for a static icon
              - string - for a image with multiple sub icons
              - list of string pathes
              - a gtk.gdk.Pixbuf if you require a static image
        """
        super(AnimatedImage, self).__init__()
        self._progressN = 0
        if icon is None:
            icon = gtk.gdk.Pixbuf(gtk.gdk.COLORSPACE_RGB, True, 8, 1, 1)
            icon.fill(0)
        if isinstance(icon, list):
            self.images = []
            for f in icon:
                self.images.append(gtk.gdk.pixbuf_new_from_file(f))
        elif isinstance(icon, gtk.gdk.Pixbuf):
            self.images = [icon]
            self.set_from_pixbuf(icon)
        elif isinstance(icon, str):
            self._imagefiles = icon
            self.images = []
            if not self._imagefiles:
                raise IOError, "no images for the animation found in '%s'" % icon
            # construct self.images list
            pixbuf_orig = gtk.gdk.pixbuf_new_from_file(icon)
            pixbuf_buffer = pixbuf_orig.copy()
            x = 0
            y = 0
            for f in range((pixbuf_orig.get_width() / self.SIZE) * 
                           (pixbuf_orig.get_height() / self.SIZE)):
                pixbuf_buffer = pixbuf_orig.subpixbuf(x, y, self.SIZE, self.SIZE)
                self.images.append(pixbuf_buffer)
                if x == (pixbuf_orig.get_width() - self.SIZE):
                    x = 0
                    y += self.SIZE
                else:
                    x += self.SIZE

            self.set_from_pixbuf(self.images[self._progressN])
            self.connect("show", self.start)
            self.connect("hide", self.stop)
        else:
            raise IOError, "need a str, list or a pixbuf"

    def start(self, w=None):
        source_id = gobject.timeout_add(int(1000/self.FPS), 
                                              self._progress_timeout)
        self._run = True

    def stop(self, w=None):
        self._run = False

    def get_current_pixbuf(self):
        return self.images[self._progressN]

    def get_animation_len(self):
        return len(self.images)

    def _progress_timeout(self):
        self._progressN += 1
        if self._progressN == len(self.images):
            self._progressN = 0
        self.set_from_pixbuf(self.get_current_pixbuf())
        return self._run

class CellRendererAnimatedImage(gtk.CellRendererPixbuf):

    __gproperties__  = { 
        "image" : (gobject.TYPE_OBJECT, 
                   "Image",
                   "Image", 
                   gobject.PARAM_READWRITE),
    }
    FPS = 20.0

    def __init__(self):
        gtk.CellRendererPixbuf.__init__(self)
    def do_set_property(self, pspec, value):
        setattr(self, pspec.name, value)
    def do_get_property(self, pspec):
        return getattr(self, pspec.name)
    def _animation_helper(self, widget, image):
        #print time.time()
        model = widget.get_model()
        if not model:
            return
        for row in model:
            cell_area = widget.get_cell_area(row.path, widget.get_column(0))
            widget.queue_draw_area(cell_area.x, cell_area.y, 
                                   cell_area.width, cell_area.height)
    def do_render(self, window, widget, background_area, cell_area, expose_area, flags):
        image = self.get_property("image")
        if image.get_animation_len() > 1:
            gobject.timeout_add(int(1000.0/self.FPS), self._animation_helper, widget, image)
        self.set_property("pixbuf", image.get_current_pixbuf())
        return gtk.CellRendererPixbuf.do_render(self, window, widget, background_area, cell_area, expose_area, flags)
    def do_get_size(self, widget, cell_area):
        image = self.get_property("image")
        self.set_property("pixbuf", image.get_current_pixbuf())
        return gtk.CellRendererPixbuf.do_get_size(self, widget, cell_area)

if __name__ == "__main__":
    import sys

    if len(sys.argv) > 1:
        datadir = sys.argv[1]
    elif os.path.exists("./data"):
        datadir = "./data"
    else:
        datadir = "/usr/share/software-center/data"

    image = AnimatedImage(datadir+"/icons/24x24/status/softwarecenter-progress.png")
    image1 = AnimatedImage(datadir+"/icons/24x24/status/softwarecenter-progress.png")
    image1.start()
    image2 = AnimatedImage(datadir+"/icons/24x24/status/softwarecenter-progress.png")
    pixbuf = gtk.gdk.pixbuf_new_from_file(datadir+"/icons/24x24/status/softwarecenter-progress.png")
    image3 = AnimatedImage(pixbuf)
    image3.show()

    image4 = AnimatedImage(glob.glob(datadir+"/icons/32x32/status/*"))
    image4.start()
    image4.show()

    model = gtk.ListStore(AnimatedImage)
    model.append([image1])
    model.append([image2])
    treeview = gtk.TreeView(model)
    tp = CellRendererAnimatedImage()
    column = gtk.TreeViewColumn("Icon", tp, image=0)
    treeview.append_column(column)
    treeview.show()

    box = gtk.VBox()
    box.pack_start(image)
    box.pack_start(image3)
    box.pack_start(image4)
    box.pack_start(treeview)
    box.show()
    win = gtk.Window()
    win.add(box)
    win.set_size_request(400,400)
    win.show()

    print "running the image for 5s"
    gobject.timeout_add_seconds(1, image.show)
    gobject.timeout_add_seconds(5, image.hide)

    gtk.main()



########NEW FILE########
__FILENAME__ = fancyimage
import gtk
import cairo
import gobject


# pi constants
M_PI = 3.1415926535897931
PI_DIV_180 = M_PI/180.0

class FancyProgress(gtk.DrawingArea):

    RADIUS = 36

    def __init__(self):
        gtk.DrawingArea.__init__(self)
        self._fraction = 0.0
        self._animator = None
        self.connect('expose-event', self._on_expose)
        return

    def set_fraction(self, fraction):
        self.fraction = fraction
        self._animate_progress()
        return

    def _animate_progress(self):
        a = self.allocation
        if not a:
            return

        r = self.RADIUS
        xc, yc = a.width/2, a.height/2
        da = (xc-r, yc-r, 2*r, 2*r)

        self._step = (self.fraction-self._fraction)*0.25
        if not self._animator:
            self._animator = gobject.timeout_add(20, self._animate_progress_cb, da)

        if self.fraction >= 1.0:
            self._fraction = 1.0
            gobject.source_remove(self._animator)
            self._animator = None
            self.queue_draw_area(*da)
        return

    def _animate_progress_cb(self, da):
        self._fraction += self._step
        self.queue_draw_area(*da)
        return True

    def _on_expose(self, widget, event):
        a = widget.allocation
        cr = widget.window.cairo_create()

        # pie
        xc, yc = a.width/2, a.height/2
        angle2 = 360*self._fraction*PI_DIV_180
        cr.move_to(xc, yc)
        cr.line_to(xc, yc-self.RADIUS)
        cr.new_sub_path()
        cr.arc(xc, yc, self.RADIUS, 0, angle2)
        cr.line_to(xc, yc)
        cr.set_source_rgb(1,0,1)
        cr.fill()

        cr.arc(xc, yc, self.RADIUS, 0, 360*PI_DIV_180)
        cr.stroke()
        del cr
        return



#class FancyImage(gtk.DrawingArea):

#    BORDER_WIDTH = 25

#    DROPSHADOW_CORNERS = {
#        'nw': gtk.gdk.pixbuf_new_from_file('data/misc/nw.png'),
#        'ne': gtk.gdk.pixbuf_new_from_file('data/misc/ne.png'),
#        'sw': gtk.gdk.pixbuf_new_from_file('data/misc/sw.png'),
#        'se': gtk.gdk.pixbuf_new_from_file('data/misc/se.png')
#        }

#    def __init__(self):
#        gtk.DrawingArea.__init__(self)

#        self.pixbuf = None
#        self._animator = None

#        self.connect('expose-event', self.on_expose_cb)
#        return

#    def set_from_file(self, path):
#        # if there is an animation kill the handler
#        if self._animator:
#            gobject.source_remove(self._animator)
#        if not path:
#            return False

#        im_data = self.load_image(path)
#        self.display_image(im_data)
#        return

#    def load_image(self, path):
#        pic = gtk.gdk.PixbufAnimation(path)
#        pb = pic.get_static_image()

#        w, h = pb.get_width(), pb.get_height()
#        w += 2*self.BORDER_WIDTH
#        h += 2*self.BORDER_WIDTH
#        self.set_size_request(w, h)

#        if pic.is_static_image():
#            pb_iter = None
#        else:
#            pb_iter = pic.get_iter()

#        return pb, pb_iter

#    def display_image(self, im_data):
#        pb, pb_iter, = im_data
#        self.pixbuf = pb
#        self.queue_draw()

#        if pb_iter:
#            # if animation; start animation

#            # calc draw area
#            self._animator = gobject.timeout_add(
#                pb_iter.get_delay_time(),
#                self.advance_cb,
#                pb_iter)
#        return

#    def draw_image(self, cr, pb, x, y, w, h):
#        # draw dropshadow
#        self.draw_dropshadow(cr, x-1, y-1, w+2, h+2)

#        # draw image frame
#        cr.rectangle(x-1, y-1, w+2, h+2)
#        cr.set_source_rgb(1,1,1)
#        cr.fill()

#        # redraw old image
#        cr.set_source_pixbuf(pb, x, y)
#        cr.paint()
#        return

#    def draw_dropshadow(self, cr, x, y, sw, sh):
#        cr.set_line_width(1)

#        # n shadow
#        xO, x1 = x+2, x+sw-2
#        self.line(cr,0.0667,xO,y-0.5,x1,y-0.5)
#        self.line(cr,0.0196,xO,y-1.5,x1,y-1.5)

#        # s shadow
#        xO += 2
#        x1 -= 2
#        yO = y+sh+0.5
#        self.line(cr,0.6824,xO,yO,x1,yO)
#        self.line(cr,0.5216,xO,yO+1,x1,yO+1)
#        self.line(cr,0.3294,xO,yO+2,x1,yO+2)
#        self.line(cr,0.1686,xO,yO+3,x1,yO+3)
#        self.line(cr,0.0667,xO,yO+4,x1,yO+4)
#        self.line(cr,0.0196,xO,yO+5,x1,yO+5)

#        # e shadow
#        xO, yO, y1  = x+sw+0.5, y+5, y+sh-2
#        self.line(cr,0.3294,xO,yO,xO,y1)
#        self.line(cr,0.1686,xO+1,yO,xO+1,y1)
#        self.line(cr,0.0667,xO+2,yO,xO+2,y1)
#        self.line(cr,0.0196,xO+3,yO,xO+3,y1)

#        # w shadow
#        xO = x-0.5
#        self.line(cr,0.3294,xO,yO,xO,y1)
#        self.line(cr,0.1686,xO-1,yO,xO-1,y1)
#        self.line(cr,0.0667,xO-2,yO,xO-2,y1)
#        self.line(cr,0.0196,xO-3,yO,xO-3,y1)

#        # corner shadows from cached pixbufs
#        cnrs = self.DROPSHADOW_CORNERS
#        cr.set_source_pixbuf(cnrs['nw'], x-4, y-2)
#        cr.paint()
#        cr.set_source_pixbuf(cnrs['ne'], x+sw-2, y-2)
#        cr.paint()
#        cr.set_source_pixbuf(cnrs['sw'], x-4, y+sh-2)
#        cr.paint()
#        cr.set_source_pixbuf(cnrs['se'], x+sw-4, y+sh-2)
#        cr.paint()
#        return

#    def line(self, cr, a, x0, y0, x1, y1):
#        # just a plain old line
#        cr.set_source_rgba(0,0,0,a)
#        cr.move_to(x0,y0)
#        cr.line_to(x1,y1)
#        cr.stroke()
#        return

#    def on_expose_cb(self, widget, event):
#        cr = widget.window.cairo_create()
#        cr.rectangle(event.area)
#        cr.clip()

#        alloc = widget.get_allocation()
#        aw, ah = alloc.width, alloc.height

#        # bg
#        lin = cairo.LinearGradient(0, 0, 0, ah)
#        lin.add_color_stop_rgb(1, 0.2235, 0.2392, 0.2941)
#        lin.add_color_stop_rgb(0, 0.2863, 0.3176, 0.3843)
#        cr.set_source(lin)
#        rounded_rect(cr, 0, 0, aw, ah, 3)
#        cr.fill()

#        if aw > 1 and ah > 1 and self.pixbuf:
#            w, h = self.pixbuf.get_width(), self.pixbuf.get_height()
#            x = (aw - w)/2
#            y = (ah - h)/2
#            self.draw_image(cr, self.pixbuf, x, y, w, h)

#        del cr
#        return

#    def on_change_cb(self, imstore):
#        self.set_image(imstore.get_path())
#        return

#    def advance_cb(self, pb_iter):
#        self.pixbuf = pb_iter.get_pixbuf()
#        pb_iter.advance()
#        self.queue_draw()
#        return True




########NEW FILE########
__FILENAME__ = gbwidget
# Copyright (C) 2009 Canonical
#
# Authors:
#  Michael Vogt
#
# This program is free software; you can redistribute it and/or modify it under
# the terms of the GNU General Public License as published by the Free Software
# Foundation; version 3.
#
# This program is distributed in the hope that it will be useful, but WITHOUT
# ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS
# FOR A PARTICULAR PURPOSE.  See the GNU General Public License for more
# details.
#
# You should have received a copy of the GNU General Public License along with
# this program; if not, write to the Free Software Foundation, Inc.,
# 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301 USA


import gobject
import gtk
import logging
import os
import sys
import string

class GtkbuilderWidget(gtk.HBox):
    """A widget that gets loaded from a Gtkbuilder UI file 
    
    If no "toplevel_name" paramter is given, the name of
    the class is used to find a UI file of that name and
    load the object with that name
    """
    def __init__(self, datadir, toplevel_name=None):
        gtk.HBox.__init__(self)
        if toplevel_name is None:
            toplevel_name = self.__class__.__name__
        ui_file = "%s/ui/%s.ui" % (datadir, toplevel_name)
        builder = gtk.Builder()
        builder.add_objects_from_file(ui_file, [toplevel_name])
        builder.connect_signals(self)
        for o in builder.get_objects():
            if issubclass(type(o), gtk.Buildable):
                name = gtk.Buildable.get_name(o)
                setattr(self, name, o)
            else:
                logging.warn("WARNING: can not get name for '%s'" % o)
        # parent
        w = getattr(self, self.__class__.__name__)
        self.add(w)
    def show(self):
        w = getattr(self, self.__class__.__name__)
        w.show_all()

# test widget that just loads the 
class GBTestWidget(GtkbuilderWidget):

    def on_button_clicked(self, button):
        print "on_button_clicked"


if __name__ == "__main__":
    logging.basicConfig(level=logging.DEBUG)

    if len(sys.argv) > 1:
        datadir = sys.argv[1]
    elif os.path.exists("./data"):
        datadir = "./data"
    else:
        datadir = "/usr/share/software-center"

    w = GBTestWidget(datadir)
    w.show()

    win = gtk.Window()
    win.add(w)
    #win.set_size_request(600,400)
    win.show_all()

    gtk.main()

########NEW FILE########
__FILENAME__ = imagedialog
# Copyright (C) 2009 Canonical
#
# Authors:
#  Michael Vogt
#
# This program is free software; you can redistribute it and/or modify it under
# the terms of the GNU General Public License as published by the Free Software
# Foundation; version 3.
#
# This program is distributed in the hope that it will be useful, but WITHOUT
# ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS
# FOR A PARTICULAR PURPOSE.  See the GNU General Public License for more
# details.
#
# You should have received a copy of the GNU General Public License along with
# this program; if not, write to the Free Software Foundation, Inc.,
# 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301 USA

import gconf
import glib
import gio
import gtk
import logging
import tempfile
import time
import threading
import urllib
import gobject

from softwarecenter.enums import *
from softwarecenter.utils import get_http_proxy_string_from_gconf

ICON_EXCEPTIONS = ["gnome"]

class Url404Error(IOError):
    pass

class Url403Error(IOError):
    pass

class GnomeProxyURLopener(urllib.FancyURLopener):
    """A urllib.URLOpener that honors the gnome proxy settings"""
    def __init__(self, user_agent=USER_AGENT):
        proxies = {}
        http_proxy = get_http_proxy_string_from_gconf()
        if http_proxy:
            proxies = { "http" : http_proxy }
        urllib.FancyURLopener.__init__(self, proxies)
        self.version = user_agent
    def http_error_404(self, url, fp, errcode, errmsg, headers):
        logging.debug("http_error_404: %s %s %s" % (url, errcode, errmsg))
        raise Url404Error, "404 %s" % url
    def http_error_403(self, url, fp, errcode, errmsg, headers):
        logging.debug("http_error_403: %s %s %s" % (url, errcode, errmsg))
        raise Url403Error, "403 %s" % url

class ShowImageDialog(gtk.Dialog):
    """A dialog that shows a image """

    def __init__(self, title, url, loading_img, loading_img_size, missing_img, parent=None):
        gtk.Dialog.__init__(self)
        # find parent window for the dialog
        if not parent:
            parent = self.get_parent()
            while parent:
                parent = w.get_parent()
        # missing
        self._missing_img = missing_img
        self.image_filename = self._missing_img
        # image
            # loading
        pixbuf_orig = gtk.gdk.pixbuf_new_from_file(loading_img)
        self.x = self._get_loading_x_start(loading_img_size)
        self.y = 0
        self.pixbuf_count = 0
        pixbuf_buffer = pixbuf_orig.copy()
        
        self.pixbuf_list = []
                
        for f in range((pixbuf_orig.get_width() / loading_img_size) * (pixbuf_orig.get_height() / loading_img_size)):
            pixbuf_buffer = pixbuf_orig.subpixbuf(self.x, self.y, loading_img_size, loading_img_size)
            self.pixbuf_list.append(pixbuf_buffer)
            if self.x == pixbuf_orig.get_width() - loading_img_size:
                self.x = self.x = self._get_loading_x_start(loading_img_size)
                self.y += loading_img_size
                if self.y == pixbuf_orig.get_height():
                    self.x = self.x = self._get_loading_x_start(loading_img_size)
                    self.y = 0
            else:
                self.x += loading_img_size
        
        
        
        self.img = gtk.Image()
        self.img.set_from_file(loading_img)
        self.img.show()
        gobject.timeout_add(50, self._update_loading, pixbuf_orig, loading_img_size)

        # view port
        scroll = gtk.ScrolledWindow()
        scroll.set_policy(gtk.POLICY_AUTOMATIC, gtk.POLICY_AUTOMATIC)
        scroll.add_with_viewport(self.img)
        scroll.show() 

        # box
        vbox = gtk.VBox()
        vbox.pack_start(scroll)
        vbox.show()
        # dialog
        self.set_transient_for(parent)
        self.set_position(gtk.WIN_POS_CENTER_ON_PARENT)
        self.get_content_area().add(vbox)
        self.add_button(gtk.STOCK_CLOSE, gtk.RESPONSE_CLOSE)
        self.set_default_size(850,650)
        self.set_title(title)
        self.connect("response", self._response)
        # install urlopener
        urllib._urlopener = GnomeProxyURLopener()
        # data
        self.url = url

    def _update_loading(self, pixbuf_orig, loading_img_size):
        if not self._finished:
            self.img.set_from_pixbuf(self.pixbuf_list[self.pixbuf_count])
            if self.pixbuf_count == (pixbuf_orig.get_width() / loading_img_size) * (pixbuf_orig.get_height() / loading_img_size) - 1:
                self.pixbuf_count = 0
            else:
                self.pixbuf_count += 1
            return True
            
    def _get_loading_x_start(self, loading_img_size):
        if (gtk.settings_get_default().props.gtk_icon_theme_name in ICON_EXCEPTIONS) or (gtk.settings_get_default().props.gtk_fallback_icon_theme in ICON_EXCEPTIONS):
            return loading_img_size
        else:
            return 0
            

    def _response(self, dialog, reponse_id):
        self._finished = True
        self._abort = True
        
    def run(self):
        self.show()
        # thread
        self._finished = False
        self._abort = False
        self._fetched = 0.0
        self._percent = 0.0
        t = threading.Thread(target=self._fetch)
        t.start()
        # wait for download to finish or for abort
        while not self._finished:
            time.sleep(0.1)
            while gtk.events_pending():
                gtk.main_iteration()
        # aborted
        if self._abort:
            return gtk.RESPONSE_CLOSE
        # load into icon
        try:
            pixbuf = gtk.gdk.pixbuf_new_from_file(self.image_filename)
        except:
            logging.debug("The image format couldn't be determined")
            pixbuf = gtk.gdk.pixbuf_new_from_file(self._missing_img)
        self.img.set_from_pixbuf(pixbuf)
        # and run the real thing
        gtk.Dialog.run(self)

    def _fetch(self):
        "fetcher thread"
        logging.debug("_fetch: %s" % self.url)
        self.location = tempfile.NamedTemporaryFile()
        try:
            (screenshot, info) = urllib.urlretrieve(self.url, 
                                                    self.location.name, 
                                                    self._progress)
            self.image_filename = self.location.name
        except (Url403Error, Url404Error), e:
            self.image_filename = self._missing_img
        except Exception, e:
            logging.exception("urlopen error")
        self._finished = True

    def _progress(self, count, block, total):
        "fetcher progress reporting"
        logging.debug("_progress %s %s %s" % (count, block, total))
        #time.sleep(1)
        self._fetched += block
        # ensure we do not go over 100%
        self._percent = min(self._fetched/total, 1.0)

if __name__ == "__main__":
    pkgname = "synaptic"
    url = "http://screenshots.ubuntu.com/screenshot/synaptic"
    loading = "/usr/share/icons/hicolor/32x32/animations/softwarecenter-loading-installed.gif"
    d = ShowImageDialog("Synaptic Screenshot", url, loading, pkgname)
    d.run()

########NEW FILE########
__FILENAME__ = navigationbar
# Copyright (C) 2009 Canonical
#
# Authors:
#  Michael Vogt
#
# This program is free software; you can redistribute it and/or modify it under
# the terms of the GNU General Public License as published by the Free Software
# Foundation; version 3.
#
# This program is distributed in the hope that it will be useful, but WITHOUT
# ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS
# FOR A PARTICULAR PURPOSE.  See the GNU General Public License for more
# details.
#
# You should have received a copy of the GNU General Public License along with
# this program; if not, write to the Free Software Foundation, Inc.,
# 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301 USA

import gtk

class NavigationBar(gtk.HBox):
    """A navigation bar using button (like nautilus)"""

    def __init__(self, group=None):
        super(NavigationBar, self).__init__()
        self.id_to_widget = {}
        self.id_to_callback = {}
        if not group:
            self.group = gtk.RadioButton()
        else:
            self.group = group

    def add_with_id(self, label, callback, id):
        """
        Add a new button with the given label/callback
        
        If there is the same id already, replace the existing one
        with the new one
        """
        # check if we have the button of that id or need a new one
        if id in self.id_to_widget:
            button = self.id_to_widget[id]
            button.disconnect(self.id_to_callback[id])
        else:
            button = gtk.RadioButton(self.group)
            button.set_mode(False)
            self.pack_start(button, expand=False)
            self.id_to_widget[id] = button
            button.show()
        # common code
        handler_id = button.connect("clicked", callback)
        button.set_label(label)
        button.set_active(True)
        self.id_to_callback[id] = handler_id

    def remove_id(self, id):
        """
        Remove the navigation button with the given id
        """
        if not id in self.id_to_widget:
            return
        self.remove(self.id_to_widget[id])
        del self.id_to_widget[id]
        try:
            del self.id_to_callback[id]
        except KeyError:
            pass

    def remove_all(self):
        """remove all elements"""
        for w in self:
            self.remove(w)
        self.id_to_widget = {}
        self.id_to_callback = {}
        
    def get_button_from_id(self, id):
        """
        return the button for the given id (or None)
        """
        if not id in self.id_to_widget:
            return None
        return self.id_to_widget[id]

    def get_label(self, id):
        """
        Return the label of the navigation button with the given id
        """
        if not id in self.id_to_widget:
            return
        return self.id_to_widget[id].get_label()

    

########NEW FILE########
__FILENAME__ = pathbar2
# Copyright (C) 2009 Matthew McGowan
#
# Authors:
#   Matthew McGowan
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


import rgb
import gtk
import cairo
import pango
import gobject

from rgb import to_float as f

# pi constants
M_PI = 3.1415926535897931
PI_OVER_180 = 0.017453292519943295


class PathBar(gtk.DrawingArea):

    # shapes
    SHAPE_RECTANGLE = 0
    SHAPE_START_ARROW = 1
    SHAPE_MID_ARROW = 2
    SHAPE_END_CAP = 3

    def __init__(self, group=None):
        gtk.DrawingArea.__init__(self)
        self.__init_drawing()
        self.set_redraw_on_allocate(False)

        self.__parts = []
        self.__active_part = None
        self.__focal_part = None
        self.__button_down = False

        self.__scroller = None
        self.__scroll_xO = 0

        self.theme = self.__pick_theme()

        # setup event handling
        self.set_flags(gtk.CAN_FOCUS)
        self.set_events(gtk.gdk.POINTER_MOTION_MASK|
                        gtk.gdk.BUTTON_PRESS_MASK|
                        gtk.gdk.BUTTON_RELEASE_MASK|
                        gtk.gdk.KEY_RELEASE_MASK|
                        gtk.gdk.KEY_PRESS_MASK|
                        gtk.gdk.LEAVE_NOTIFY_MASK)

        self.connect("motion-notify-event", self.__motion_notify_cb)
        self.connect("leave-notify-event", self.__leave_notify_cb)
        self.connect("button-press-event", self.__button_press_cb)
        self.connect("button-release-event", self.__button_release_cb)
#        self.connect("key-release-event", self.__key_release_cb)

        self.connect("realize", self.__realize_cb)
        self.connect("expose-event", self.__expose_cb)
        self.connect("style-set", self.__style_change_cb)
        self.connect("size-allocate", self.__allocation_change_cb)
        self.last_label = None
        return

    def set_active(self, part):
        part.set_state(gtk.STATE_ACTIVE)
        prev, redraw = self.__set_active(part)
        if redraw:
            self.queue_draw_area(*prev.get_allocation_tuple())
            self.queue_draw_area(*part.get_allocation_tuple())
        self.last_label = None
        return

    def get_active(self):
        return self.__active_part

#    def get_left_part(self):
#        active = self.get_active()
#        if not active:
#            return self.__parts[0]

#        i = self.__parts.index(active)+1
#        if i > len(self.__parts)-1:
#            i = 0
#        return self.__parts[i]

#    def get_right_part(self):
#        active = self.get_active()
#        if not active:
#            return self.__parts[0]

#        i = self.__parts.index(active)-1
#        if i < 0:
#            i = len(self.__parts)-1
#        return self.__parts[i]

    def append(self, part):
        prev, did_shrink = self.__append(part)
        if not self.get_property("visible"):
            return False

        if self.theme.animate and len(self.__parts) > 1:
            aw = self.theme.arrow_width

            # calc draw_area
            x,y,w,h = part.get_allocation_tuple()
            w += aw

            # begin scroll animation
            self.__hscroll_out_init(
                part.get_width(),
                gtk.gdk.Rectangle(x,y,w,h),
                self.theme.scroll_duration_ms,
                self.theme.scroll_fps
                )
        else:
            self.queue_draw_area(*part.get_allocation_tuple())
        return False

    def remove(self, part):
        if len(self.__parts)-1 < 1:
            #print 'The first part is sacred ;)'
            return

        old_w = self.__draw_width()

        # remove part from interal part list
        try:
            del self.__parts[self.__parts.index(part)]
        except:
            pass

        self.__compose_parts(self.__parts[-1], False)

        if old_w >= self.allocation.width:
            self.__grow_check(old_w, self.allocation)
            self.queue_draw()

        else:
            self.queue_draw_area(*part.get_allocation_tuple())
            self.queue_draw_area(*self.__parts[-1].get_allocation_tuple())
        return

    def __set_active(self, part):
        for i in self.id_to_part:
            apart = self.id_to_part[i]
            if apart.id > part.id:
                self.remove(apart)
                
        prev_active = self.__active_part
        redraw = False
        if part.callback:
            part.callback(self, part.obj)
        if prev_active and prev_active != part:
            prev_active.set_state(gtk.STATE_NORMAL)
            redraw = True

        self.__active_part = part
        return prev_active, redraw

    def __append(self, part):
        # clean up any exisitng scroll callbacks
        if self.__scroller:
            gobject.source_remove(self.__scroller)
        self.__scroll_xO = 0

        # the basics
        x = self.__draw_width()
        self.__parts.append(part)
        part.set_pathbar(self)

        prev_active = self.set_active(part)

        # determin part shapes, and calc modified parts widths
        prev = self.__compose_parts(part, True)
        # set the position of new part
        part.set_x(x)

        # check parts fit to widgets allocated width
        if x + part.get_width() > self.allocation.width  and \
            self.allocation.width != 1:
            self.__shrink_check(self.allocation)
            return prev, True

        return prev, False

#    def __shorten(self, n):
#        n = int(n)
#        old_w = self.__draw_width()
#        end_active = self.get_active() == self.__parts[-1]

#        if len(self.__parts)-n < 1:
#            print WARNING + 'The first part is sacred ;)' + ENDC
#            return old_w, False

#        del self.__parts[-n:]
#        self.__compose_parts(self.__parts[-1], False)

#        if end_active:
#            self.set_active(self.__parts[-1])

#        if old_w >= self.allocation.width:
#            self.__grow_check(old_w, self.allocation)
#            return old_w, True

#        return old_w, False

    def __shrink_check(self, allocation):
        path_w = self.__draw_width()
        shrinkage = path_w - allocation.width
        mpw = self.theme.min_part_width
        xO = 0

        for part in self.__parts[:-1]:
            w = part.get_width()
            dw = 0

            if w - shrinkage <= mpw:
                dw = w - mpw
                shrinkage -= dw
                part.set_size(mpw, -1)
                part.set_x(part.get_x() - xO)

            else:
                part.set_size(w - shrinkage, -1)
                part.set_x(part.get_x() - xO)
                dw = shrinkage
                shrinkage = 0

            xO += dw

        last = self.__parts[-1]
        last.set_x(last.get_x() - xO)
        return

    def __grow_check(self, old_width, allocation):
        parts = self.__parts
        if len(parts) == 0:
            return

        growth = old_width - self.__draw_width()
        parts.reverse()

        for part in parts:
            bw = part.get_size_requisition()[0]
            w = part.get_width()

            if w < bw:
                dw = bw - w

                if dw <= growth:
                    growth -= dw
                    part.set_size(bw, -1)
                    part.set_x(part.get_x() + growth)

                else:
                    part.set_size(w + growth, -1)
                    growth = 0

            else:
                part.set_x(part.get_x() + growth)

        parts.reverse()
        shift =  parts[0].get_x()

        # left align parts
        if shift > 0:
            for part in parts: part.set_x(part.get_x() - shift)
        return

    def __compose_parts(self, last, prev_set_size):
        parts = self.__parts

        if len(parts) == 1:
            last.set_shape(self.SHAPE_RECTANGLE)
            last.set_size(*last.calc_size_requisition())
            prev = None

        elif len(parts) == 2:
            prev = parts[0]
            prev.set_shape(self.SHAPE_START_ARROW)
            prev.calc_size_requisition()

            last.set_shape(self.SHAPE_END_CAP)
            last.set_size(*last.calc_size_requisition())

        else:
            prev = parts[-2]
            prev.set_shape(self.SHAPE_MID_ARROW)
            prev.calc_size_requisition()

            last.set_shape(self.SHAPE_END_CAP)
            last.set_size(*last.calc_size_requisition())

        if prev and prev_set_size:
            prev.set_size(*prev.get_size_requisition())
        return prev

    def __draw_width(self):
        l = len(self.__parts)
        if l == 0:
            return 0
        a = self.__parts[-1].allocation
        return a[0] + a[2]

    def __hscroll_out_init(self, distance, draw_area, duration, fps):
        self.__scroller = gobject.timeout_add(
            int(1000.0 / fps),  # interval
            self.__hscroll_out_cb,
            distance,
            duration*0.001,   # 1 over duration (converted to seconds)
            gobject.get_current_time(),
            draw_area.x,
            draw_area.y,
            draw_area.width,
            draw_area.height)
        return

    def __hscroll_out_cb(self, distance, duration, start_t, x, y, w, h):
        cur_t = gobject.get_current_time()
        xO = distance - distance*((cur_t - start_t) / duration)

        if xO > 0:
            self.__scroll_xO = xO
            self.queue_draw_area(x, y, w, h)
        else:   # final frame
            self.__scroll_xO = 0
            # redraw the entire widget
            # incase some timeouts are skipped due to high system load
            self.queue_draw()
            self.__scroller = None
            return False
        return True

    def __part_at_xy(self, x, y):
        for part in self.__parts:
            a = part.get_allocation()
            region = gtk.gdk.region_rectangle(a)

            if region.point_in(int(x), int(y)):
                return part
        return None

    def __draw_hscroll(self, cr):
        if len(self.__parts) < 2:
            return

        # draw the last two parts
        prev, last = self.__parts[-2:]

        # style theme stuff
        style, r, aw, shapes = self.style, self.theme.curvature, \
            self.theme.arrow_width, self.__shapes

        # draw part that need scrolling
        self.__draw_part(cr,
                         last,
                         style,
                         r,
                         aw,
                         shapes,
                         self.__scroll_xO)

        # draw the last part that does not scroll
        self.__draw_part(cr,
                         prev,
                         style,
                         r,
                         aw,
                         shapes)
        return

    def __draw_all(self, cr, event_area):
        style = self.style
        r = self.theme.curvature
        aw = self.theme.arrow_width
        shapes = self.__shapes
        region = gtk.gdk.region_rectangle(event_area)

        # if a scroll is pending we want to not draw the final part,
        # as we don't want to prematurely reveal the part befor the
        # scroll animation has had a chance to start
        if self.__scroller:
            parts = self.__parts[:-1]
        else:
            parts = self.__parts

        parts.reverse()
        for part in parts:
            if region.rect_in(part.get_allocation()) != gtk.gdk.OVERLAP_RECTANGLE_OUT:
                self.__draw_part(cr, part, style, r, aw, shapes)
        parts.reverse()
        return

    def __draw_part_ltr(self, cr, part, style, r, aw, shapes, sxO=0):
        x, y, w, h = part.get_allocation()
        shape = part.shape
        state = part.state
        icon_pb = part.icon.pixbuf

        cr.save()
        cr.translate(x-sxO, y)

        # draw bg
        self.__draw_part_bg(cr, part, w, h, state, shape, style,r, aw, shapes)

        # determine left margin.  left margin depends on part shape
        # and whether there exists an icon or not
        if shape == self.SHAPE_MID_ARROW or shape == self.SHAPE_END_CAP:
            margin = int(0.75*self.theme.arrow_width + self.theme.xpadding)
        else:
            margin = self.theme.xpadding

        # draw icon
        if icon_pb:
            cr.set_source_pixbuf(
                icon_pb,
                self.theme.xpadding-sxO,
                (alloc.height - icon_pb.get_height())/2)
            cr.paint()
            margin += icon_pb.get_width() + self.theme.spacing

        # if space is limited and an icon is set, dont draw label
        # otherwise, draw label
        if w == self.theme.min_part_width and icon_pb:
            pass

        else:
            layout = part.get_layout()
            lw, lh = layout.get_pixel_size()
            dst_x = x + margin - int(sxO)
            dst_y = (self.allocation.height - lh)/2+1
            style.paint_layout(
                self.window,
                self.theme.text_state[state],
                False,
                (dst_x, dst_y, lw+4, lh),   # clip area
                self,
                None,
                dst_x,
                dst_y,
                layout)

        cr.restore()
        return

    def __draw_part_rtl(self, cr, part, style, r, aw, shapes, sxO=0):
        x, y, w, h = part.get_allocation()
        shape = part.shape
        state = part.state
        icon_pb = part.icon.pixbuf

        cr.save()
        cr.translate(x+sxO, y)

        # draw bg
        self.__draw_part_bg(cr, part, w, h, state, shape, style,r, aw, shapes)

        # determine left margin.  left margin depends on part shape
        # and whether there exists an icon or not
        if shape == self.SHAPE_MID_ARROW or shape == self.SHAPE_END_CAP:
            margin = self.theme.arrow_width + self.theme.xpadding
        else:
            margin = self.theme.xpadding

        # draw icon
        if icon_pb:
            margin += icon_pb.get_width()
            cr.set_source_pixbuf(
                icon_pb,
                w - margin + sxO,
                (h - icon_pb.get_height())/2)
            cr.paint()
            margin += self.spacing

        # if space is limited and an icon is set, dont draw label
        # otherwise, draw label
        if w == self.theme.min_part_width and icon_pb:
            pass

        else:
            layout = part.get_layout()
            lw, lh = layout.get_pixel_size()
            dst_x = x + part.get_width() - margin - lw + int(sxO)
            dst_y = (self.allocation.height - lh)/2+1
            style.paint_layout(
                self.window,
                self.theme.text_state[state],
                False,
                None,
                self,
                None,
                dst_x,
                dst_y,
                layout)

        cr.restore()
        return

    def __draw_part_bg(self, cr, part, w, h, state, shape, style, r, aw, shapes):
        # outer slight bevel or focal highlight
        shapes[shape](cr, 0, 0, w, h, r, aw)
        cr.set_source_rgba(0, 0, 0, 0.055)
        cr.fill()

        # colour scheme dicts
        bg = self.theme.bg_colors
        outer = self.theme.dark_line_colors
        inner = self.theme.light_line_colors

        # bg linear vertical gradient
        if state != gtk.STATE_PRELIGHT:
            color1, color2 = bg[state]
        else:
            if part != self.get_active():
                color1, color2 = bg[self.theme.PRELIT_NORMAL]
            else:
                color1, color2 = bg[self.theme.PRELIT_ACTIVE]

        shapes[shape](cr, 1, 1, w-1, h-1, r, aw)
        lin = cairo.LinearGradient(0, 0, 0, h-1)
        lin.add_color_stop_rgb(0.0, *color1)
        lin.add_color_stop_rgb(1.0, *color2)
        cr.set_source(lin)
        cr.fill()

        cr.set_line_width(1.0)
        # strong outline
        shapes[shape](cr, 1.5, 1.5, w-1.5, h-1.5, r, aw)
        cr.set_source_rgb(*outer[state])
        cr.stroke()

        # inner bevel/highlight
        if self.theme.light_line_colors[state]:
            shapes[shape](cr, 2.5, 2.5, w-2.5, h-2.5, r, aw)
            r, g, b = inner[state]
            cr.set_source_rgba(r, g, b, 0.6)
            cr.stroke()
        return

    def __shape_rect(self, cr, x, y, w, h, r, aw):
        global M_PI, PI_OVER_180
        cr.new_sub_path()
        cr.arc(r+x, r+y, r, M_PI, 270*PI_OVER_180)
        cr.arc(w-r, r+y, r, 270*PI_OVER_180, 0)
        cr.arc(w-r, h-r, r, 0, 90*PI_OVER_180)
        cr.arc(r+x, h-r, r, 90*PI_OVER_180, M_PI)
        cr.close_path()
        return

    def __shape_start_arrow_ltr(self, cr, x, y, w, h, r, aw):
        global M_PI, PI_OVER_180
        cr.new_sub_path()
        cr.arc(r+x, r+y, r, M_PI, 270*PI_OVER_180)
        # arrow head
        cr.line_to(w-aw+1, y)
        cr.line_to(w, (h+y)*0.5)
        cr.line_to(w-aw+1, h)
        cr.arc(r+x, h-r, r, 90*PI_OVER_180, M_PI)
        cr.close_path()
        return

    def __shape_mid_arrow_ltr(self, cr, x, y, w, h, r, aw):
        cr.move_to(-1, y)
        # arrow head
        cr.line_to(w-aw+1, y)
        cr.line_to(w, (h+y)*0.5)
        cr.line_to(w-aw+1, h)
        cr.line_to(-1, h)
        cr.close_path()
        return

    def __shape_end_cap_ltr(self, cr, x, y, w, h, r, aw):
        global M_PI, PI_OVER_180
        cr.move_to(-1, y)
        cr.arc(w-r, r+y, r, 270*PI_OVER_180, 0)
        cr.arc(w-r, h-r, r, 0, 90*PI_OVER_180)
        cr.line_to(-1, h)
        cr.close_path()
        return

    def __shape_start_arrow_rtl(self, cr, x, y, w, h, r, aw):
        global M_PI, PI_OVER_180
        cr.new_sub_path()
        cr.move_to(x, (h+y)*0.5)
        cr.line_to(aw-1, y)
        cr.arc(w-r, r+y, r, 270*PI_OVER_180, 0)
        cr.arc(w-r, h-r, r, 0, 90*PI_OVER_180)
        cr.line_to(aw-1, h)
        cr.close_path()
        return

    def __shape_mid_arrow_rtl(self, cr, x, y, w, h, r, aw):
        cr.move_to(x, (h+y)*0.5)
        cr.line_to(aw-1, y)
        cr.line_to(w+1, y)
        cr.line_to(w+1, h)
        cr.line_to(aw-1, h)
        cr.close_path()
        return

    def __shape_end_cap_rtl(self, cr, x, y, w, h, r, aw):
        global M_PI, PI_OVER_180
        cr.arc(r+x, r+y, r, M_PI, 270*PI_OVER_180)
        cr.line_to(w+1, y)
        cr.line_to(w+1, h)
        cr.arc(r+x, h-r, r, 90*PI_OVER_180, M_PI)
        cr.close_path()
        return

    def __state(self, part):
        # returns the idle state of the part depending on
        # whether part is active or not.
        if part == self.__active_part:
            return gtk.STATE_ACTIVE
        return gtk.STATE_NORMAL

    def __tooltip_check(self, part):
        # only show a tooltip if part is truncated, i.e. not all label text is
        # visible.
        if part.is_truncated():
            self.set_has_tooltip(False)
            gobject.timeout_add(50, self.__set_tooltip_cb, part.label)
        else:
            self.set_has_tooltip(False)
        return

    def __set_tooltip_cb(self, text):
        # callback allows the tooltip position to be updated as pointer moves
        # accross different parts
        self.set_has_tooltip(True)
        self.set_tooltip_markup(text)
        return False

    def __pick_theme(self, name=None):
        name = name or gtk.settings_get_default().get_property("gtk-theme-name")
        themes = PathBarThemes.DICT
        if themes.has_key(name):
            return themes[name]()
        #print "No styling hints for %s are available" % name
        return PathBarThemeHuman()

    def __init_drawing(self):
        if self.get_direction() != gtk.TEXT_DIR_RTL:
            self.__draw_part = self.__draw_part_ltr
            self.__shapes = {
                self.SHAPE_RECTANGLE : self.__shape_rect,
                self.SHAPE_START_ARROW : self.__shape_start_arrow_ltr,
                self.SHAPE_MID_ARROW : self.__shape_mid_arrow_ltr,
                self.SHAPE_END_CAP : self.__shape_end_cap_ltr}
        else:
            self.__draw_part = self.__draw_part_rtl
            self.__shapes = {
                self.SHAPE_RECTANGLE : self.__shape_rect,
                self.SHAPE_START_ARROW : self.__shape_start_arrow_rtl,
                self.SHAPE_MID_ARROW : self.__shape_mid_arrow_rtl,
                self.SHAPE_END_CAP : self.__shape_end_cap_rtl}
        return

    def __motion_notify_cb(self, widget, event):
        if self.__scroll_xO > 0:
            return

        part = self.__part_at_xy(event.x, event.y)
        prev_focal = self.__focal_part

        if self.__button_down:
            if prev_focal and part != prev_focal:
                prev_focal.set_state(self.__state(prev_focal))
                self.queue_draw_area(*prev_focal.get_allocation_tuple())
            return

        self.__button_down = False
        if part and part.state != gtk.STATE_PRELIGHT:
            self.__tooltip_check(part)
            part.set_state(gtk.STATE_PRELIGHT)

            if prev_focal:
                prev_focal.set_state(self.__state(prev_focal))
                self.queue_draw_area(*prev_focal.get_allocation_tuple())

            self.__focal_part = part
            self.queue_draw_area(*part.get_allocation_tuple())

        elif not part and prev_focal != None:
            prev_focal.set_state(self.__state(prev_focal))
            self.queue_draw_area(*prev_focal.get_allocation_tuple())
            self.__focal_part = None
        return

    def __leave_notify_cb(self, widget, event):
        self.__button_down = False
        prev_focal = self.__focal_part
        if prev_focal:
            prev_focal.set_state(self.__state(prev_focal))
            self.queue_draw_area(*prev_focal.get_allocation_tuple())
        self.__focal_part = None
        return

    def __button_press_cb(self, widget, event):
        self.__button_down = True
        part = self.__part_at_xy(event.x, event.y)
        if part:
            part.set_state(gtk.STATE_SELECTED)
            self.queue_draw_area(*part.get_allocation_tuple())
        return

    def __button_release_cb(self, widget, event):
        part = self.__part_at_xy(event.x, event.y)

        if self.__focal_part and self.__focal_part != part:
            pass
        elif part and self.__button_down:
            self.grab_focus()
            prev_active, redraw = self.__set_active(part)
            part.set_state(gtk.STATE_PRELIGHT)
            self.queue_draw_area(*part.get_allocation_tuple())

            if redraw:
                self.queue_draw_area(*prev_active.get_allocation_tuple())
        self.__button_down = False
        return

#    def __key_release_cb(self, widget, event):
#        part = None

#        # left key pressed
#        if event.keyval == 65363:
#            part = self.get_left_part()

#        # right key pressed
#        elif event.keyval == 65361:
#            part = self.get_right_part()

#        if not part: return

#        prev_active = self.set_active(part)
#        self.queue_draw_area(*part.allocation)
#        if prev_active:
#            self.queue_draw_area(*prev_active.allocation)

#        part.emit("clicked", event.copy())
#        return

    def __realize_cb(self, widget):
        self.theme.load(widget.style)
        return

    def __expose_cb(self, widget, event):
        cr = widget.window.cairo_create()

        if self.theme.base_hack:
            cr.set_source_rgb(*self.theme.base_hack)
            cr.paint()

        if self.__scroll_xO:
            self.__draw_hscroll(cr)
        else:
            self.__draw_all(cr, event.area)

        del cr
        return

    def __style_change_cb(self, widget, old_style):
        # when alloc.width == 1, this is typical of an unallocated widget,
        # lets not break a sweat for nothing...
        if self.allocation.width == 1:
            return

        self.theme = self.__pick_theme()
        self.theme.load(widget.style)
        # set height to 0 so that if part height has been reduced the widget will
        # shrink to an appropriate new height based on new font size
        self.set_size_request(-1, 28)

        parts = self.__parts
        self.__parts = []

        # recalc best fits, re-append then draw all
        for part in parts:

            if part.icon.pixbuf:
                part.icon.load_pixbuf()

            part.calc_size_requisition()
            self.__append(part)

        self.queue_draw()
        return

    def __allocation_change_cb(self, widget, allocation):
        if allocation.width == 1:
            return

        path_w = self.__draw_width()
        if path_w == allocation.width:
            return
        elif path_w > allocation.width:
            self.__shrink_check(allocation)
        else:
            self.__grow_check(allocation.width, allocation)

        self.queue_draw()
        return


class PathPart:

    def __init__(self, id, label=None, callback=None, obj=None):
        self.__requisition = (0,0)
        self.__layout = None
        self.__pbar = None

        self.id = id

        self.allocation = [0, 0, 0, 0]
        self.state = gtk.STATE_NORMAL
        self.shape = PathBar.SHAPE_RECTANGLE

        self.callback = callback
        self.obj = obj
        self.set_label(label or "")
        self.icon = PathBarIcon()
        return

    def set_callback(self, cb):
        self.callback = cb
        return

    def set_label(self, label):
        # escape special characters
        label = gobject.markup_escape_text(label.strip())
        # some hackery to preserve italics markup
        label = label.replace('&lt;i&gt;', '<i>').replace('&lt;/i&gt;', '</i>')
        self.label = label
        return

    def set_icon(self, stock_icon, size=gtk.ICON_SIZE_BUTTON):
        self.icon.specify(stock_icon, size)
        self.icon.load_pixbuf()
        return

    def set_state(self, gtk_state):
        self.state = gtk_state
        return

    def set_shape(self, shape):
        self.shape = shape
        return

    def set_x(self, x):
        self.allocation[0] = int(x)
        return

    def set_size(self, w, h):
        if w != -1: self.allocation[2] = int(w)
        if h != -1: self.allocation[3] = int(h)
        self.__calc_layout_width(self.__layout, self.shape, self.__pbar)
        return

    def set_pathbar(self, path_bar):
        self.__pbar = path_bar
        return

    def get_x(self):
        return self.allocation[0]

    def get_width(self):
        return self.allocation[2]

    def get_height(self):
        return self.allocation[3]

    def get_label(self):
        return self.label

    def get_allocation(self):
        return gtk.gdk.Rectangle(*self.get_allocation_tuple())

    def get_allocation_tuple(self):
        if self.__pbar.get_direction() != gtk.TEXT_DIR_RTL:
            return self.allocation
        x, y, w, h = self.allocation
        x = self.__pbar.allocation[2]-x-w
        return x, y, w, h

    def get_size_requisition(self):
        return self.__requisition

    def get_layout(self):
        return self.__layout

    def activate(self):
        self.__pbar.set_active(self)
        return

    def calc_size_requisition(self):
        pbar = self.__pbar

        # determine widget size base on label width
        self.__layout = self.__layout_text(self.label, pbar.get_pango_context())
        extents = self.__layout.get_pixel_extents()

        # calc text width + 2 * padding, text height + 2 * ypadding
        w = extents[1][2] + 2*pbar.theme.xpadding
        h = max(extents[1][3] + 2*pbar.theme.ypadding, pbar.get_size_request()[1])

        # if has icon add some more pixels on
        if self.icon.pixbuf:
            w += self.icon.pixbuf.get_width() + pbar.theme.spacing
            h = max(self.icon.pixbuf.get_height() + 2*pbar.theme.ypadding, h)

        # extend width depending on part shape  ...
        if self.shape == PathBar.SHAPE_START_ARROW or \
            self.shape == PathBar.SHAPE_END_CAP:
            w += pbar.theme.arrow_width

        elif self.shape == PathBar.SHAPE_MID_ARROW:
            w += 2*pbar.theme.arrow_width

        # if height greater than current height request,
        # reset height request to higher value
        # i get the feeling this should be in set_size_request(), but meh
        if h > pbar.get_size_request()[1]:
            pbar.set_size_request(-1, h)

        self.__requisition = (w,h)
        return w, h

    def is_truncated(self):
        return self.__requisition[0] != self.allocation[2]

    def __layout_text(self, text, pango_context):
        layout = pango.Layout(pango_context)
        layout.set_markup('%s' % text)
        layout.set_ellipsize(pango.ELLIPSIZE_END)
        return layout

    def __calc_layout_width(self, layout, shape, pbar):
        # set layout width
        if self.icon.pixbuf:
            icon_w = self.icon.pixbuf.get_width() + pbar.theme.spacing
        else:
            icon_w = 0

        w = self.allocation[2]
        if shape == PathBar.SHAPE_MID_ARROW:
            layout.set_width((w - 2*pbar.theme.arrow_width -
                2*pbar.theme.xpadding - icon_w)*pango.SCALE)

        elif shape == PathBar.SHAPE_START_ARROW or \
            shape == PathBar.SHAPE_END_CAP:
            layout.set_width((w - pbar.theme.arrow_width - 2*pbar.theme.xpadding -
                icon_w)*pango.SCALE)
        else:
            layout.set_width((w - 2*pbar.theme.xpadding - icon_w)*pango.SCALE)
        return


class PathBarIcon:

    def __init__(self, name=None, size=None):
        self.name = name
        self.size = size
        self.pixbuf = None
        return

    def specify(self, name, size):
        self.name = name
        self.size = size
        return

    def load_pixbuf(self):
        if not self.name:
            print 'Error: No icon specified.'
            return
        if not self.size:
            print 'Note: No icon size specified.'

        def render_icon(icon_set, name, size):
            self.pixbuf = icon_set.render_icon(
                style,
                gtk.TEXT_DIR_NONE,
                gtk.STATE_NORMAL,
                self.size or gtk.ICON_SIZE_BUTTON,
                gtk.Image(),
                None)
            return

        style = gtk.Style()
        icon_set = style.lookup_icon_set(self.name)

        if not icon_set:
            t = gtk.icon_theme_get_default()
            self.pixbuf = t.lookup_icon(self.name, self.size, 0).load_icon()
        else:
            icon_set = style.lookup_icon_set(self.name)
            render_icon(icon_set, self.name, self.size)

        if not self.pixbuf:
            print 'Error: No name failed to match any installed icon set.'
            self.name = gtk.STOCK_MISSING_IMAGE
            icon_set = style.lookup_icon_set(self.name)
            render_icon(icon_set, self.name, self.size)
        return


class PathBarThemeHuman:

    PRELIT_NORMAL = 10
    PRELIT_ACTIVE = 11

    curvature = 2.5
    min_part_width = 56
    xpadding = 8
    ypadding = 2
    spacing = 4
    arrow_width = 13
    scroll_duration_ms = 150
    scroll_fps = 50
    animate = gtk.settings_get_default().get_property("gtk-enable-animations")

    def __init__(self):
        return

    def load(self, style):
        mid = style.mid
        dark = style.dark
        light = style.light
        text = style.text
        active = rgb.mix_color(mid[gtk.STATE_NORMAL],
                               mid[gtk.STATE_SELECTED], 0.25)

        self.bg_colors = {
            gtk.STATE_NORMAL: (f(rgb.shade(mid[gtk.STATE_NORMAL], 1.2)),
                                f(mid[gtk.STATE_NORMAL])),

            gtk.STATE_ACTIVE: (f(rgb.shade(active, 1.2)),
                               f(active)),

            gtk.STATE_SELECTED: (f(mid[gtk.STATE_ACTIVE]),
                                 f(mid[gtk.STATE_ACTIVE])),

            self.PRELIT_NORMAL: (f(rgb.shade(mid[gtk.STATE_NORMAL], 1.25)),
                                 f(rgb.shade(mid[gtk.STATE_NORMAL], 1.05))),

            self.PRELIT_ACTIVE: (f(rgb.shade(active, 1.25)),
                                 f(rgb.shade(active, 1.05)))
            }

        self.dark_line_colors = {
            gtk.STATE_NORMAL: f(dark[gtk.STATE_NORMAL]),
            gtk.STATE_ACTIVE: f(dark[gtk.STATE_ACTIVE]),
            gtk.STATE_SELECTED: f(rgb.shade(dark[gtk.STATE_ACTIVE], 0.9)),
            gtk.STATE_PRELIGHT: f(dark[gtk.STATE_PRELIGHT])
            }

        self.light_line_colors = {
            gtk.STATE_NORMAL: f(light[gtk.STATE_NORMAL]),
            gtk.STATE_ACTIVE: f(light[gtk.STATE_ACTIVE]),
            gtk.STATE_SELECTED: None,
            gtk.STATE_PRELIGHT: f(light[gtk.STATE_PRELIGHT])
            }

        self.text_state = {
            gtk.STATE_NORMAL: gtk.STATE_NORMAL,
            gtk.STATE_ACTIVE: gtk.STATE_ACTIVE,
            gtk.STATE_SELECTED: gtk.STATE_ACTIVE,
            gtk.STATE_PRELIGHT: gtk.STATE_PRELIGHT
            }

        self.base_hack = None
        return


class PathBarThemeHumanClearlooks(PathBarThemeHuman):

    def __init__(self):
        PathBarThemeHuman.__init__(self)
        return

    def __init__(self):
        return

    def load(self, style):
        mid = style.mid
        dark = style.dark
        light = style.light
        text = style.text
        active = rgb.mix_color(mid[gtk.STATE_NORMAL],
                               mid[gtk.STATE_SELECTED], 0.25)

        self.bg_colors = {
            gtk.STATE_NORMAL: (f(rgb.shade(mid[gtk.STATE_NORMAL], 1.20)),
                                f(rgb.shade(mid[gtk.STATE_NORMAL], 1.05))),

            gtk.STATE_ACTIVE: (f(rgb.shade(active, 1.20)),
                               f(rgb.shade(active, 1.05))),

            gtk.STATE_SELECTED: (f(rgb.shade(mid[gtk.STATE_ACTIVE], 1.15)),
                                f(mid[gtk.STATE_ACTIVE])),

            self.PRELIT_NORMAL: (f(rgb.shade(mid[gtk.STATE_NORMAL], 1.35)),
                                 f(rgb.shade(mid[gtk.STATE_NORMAL], 1.15))),

            self.PRELIT_ACTIVE: (f(rgb.shade(active, 1.35)),
                                 f(rgb.shade(active, 1.15)))
            }

        self.dark_line_colors = {
            gtk.STATE_NORMAL: f(rgb.shade(dark[gtk.STATE_ACTIVE], 0.975)),
            gtk.STATE_ACTIVE: f(rgb.shade(dark[gtk.STATE_ACTIVE], 0.975)),
            gtk.STATE_SELECTED: f(rgb.shade(dark[gtk.STATE_ACTIVE], 0.95)),
            gtk.STATE_PRELIGHT: f(dark[gtk.STATE_PRELIGHT])
            }

        self.light_line_colors = {
            gtk.STATE_NORMAL: None,
            gtk.STATE_ACTIVE: None,
            gtk.STATE_SELECTED: f(mid[gtk.STATE_ACTIVE]),
            gtk.STATE_PRELIGHT: f(light[gtk.STATE_PRELIGHT])
            }

        self.text_state = {
            gtk.STATE_NORMAL: gtk.STATE_NORMAL,
            gtk.STATE_ACTIVE: gtk.STATE_ACTIVE,
            gtk.STATE_SELECTED: gtk.STATE_NORMAL,
            gtk.STATE_PRELIGHT: gtk.STATE_PRELIGHT
            }

        self.base_hack = None
        return


class PathBarThemeDust(PathBarThemeHuman):

    def __init__(self):
        PathBarThemeHuman.__init__(self)
        return

    def load(self, style):
        mid = style.mid
        dark = style.dark
        light = style.light
        text = style.text
        active = rgb.mix_color(mid[gtk.STATE_NORMAL],
                               light[gtk.STATE_SELECTED], 0.3)

        self.bg_colors = {
            gtk.STATE_NORMAL: (f(rgb.shade(mid[gtk.STATE_NORMAL], 1.3)),
                                f(mid[gtk.STATE_NORMAL])),

            gtk.STATE_ACTIVE: (f(rgb.shade(active, 1.3)),
                               f(active)),

            gtk.STATE_SELECTED: (f(rgb.shade(mid[gtk.STATE_NORMAL], 0.95)),
                                 f(rgb.shade(mid[gtk.STATE_NORMAL], 0.95))),

            self.PRELIT_NORMAL: (f(rgb.shade(mid[gtk.STATE_NORMAL], 1.35)),
                                 f(rgb.shade(mid[gtk.STATE_NORMAL], 1.15))),

            self.PRELIT_ACTIVE: (f(rgb.shade(active, 1.35)),
                                 f(rgb.shade(active, 1.15)))
            }

        self.dark_line_colors = {
            gtk.STATE_NORMAL: f(dark[gtk.STATE_ACTIVE]),
            gtk.STATE_ACTIVE: f(dark[gtk.STATE_ACTIVE]),
            gtk.STATE_SELECTED: f(rgb.shade(dark[gtk.STATE_ACTIVE], 0.95)),
            gtk.STATE_PRELIGHT: f(dark[gtk.STATE_PRELIGHT])
            }

        self.light_line_colors = {
            gtk.STATE_NORMAL: f(light[gtk.STATE_NORMAL]),
            gtk.STATE_ACTIVE: f(light[gtk.STATE_NORMAL]),
            gtk.STATE_SELECTED: None,
            gtk.STATE_PRELIGHT: f(light[gtk.STATE_PRELIGHT])
            }

        self.text_state = {
            gtk.STATE_NORMAL: gtk.STATE_NORMAL,
            gtk.STATE_ACTIVE: gtk.STATE_ACTIVE,
            gtk.STATE_SELECTED: gtk.STATE_NORMAL,
            gtk.STATE_PRELIGHT: gtk.STATE_PRELIGHT
            }

        self.base_hack = None
        return


class PathBarThemeNewWave(PathBarThemeHuman):

    curvature = 1.5

    def __init__(self):
        PathBarThemeHuman.__init__(self)
        return

    def load(self, style):
        mid = style.mid
        dark = style.dark
        light = style.light
        text = style.text
        active = rgb.mix_color(mid[gtk.STATE_NORMAL],
                               light[gtk.STATE_SELECTED], 0.5)

        self.bg_colors = {
            gtk.STATE_NORMAL: (f(rgb.shade(mid[gtk.STATE_NORMAL], 1.01)),
                                f(mid[gtk.STATE_NORMAL])),

            gtk.STATE_ACTIVE: (f(rgb.shade(active, 1.01)),
                               f(active)),

            gtk.STATE_SELECTED: (f(rgb.shade(mid[gtk.STATE_NORMAL], 0.95)),
                                 f(rgb.shade(mid[gtk.STATE_NORMAL], 0.95))),

            self.PRELIT_NORMAL: (f(rgb.shade(mid[gtk.STATE_NORMAL], 1.2)),
                                 f(rgb.shade(mid[gtk.STATE_NORMAL], 1.15))),

            self.PRELIT_ACTIVE: (f(rgb.shade(active, 1.2)),
                                 f(rgb.shade(active, 1.15)))
            }

        self.dark_line_colors = {
            gtk.STATE_NORMAL: f(rgb.shade(dark[gtk.STATE_ACTIVE], 0.95)),
            gtk.STATE_ACTIVE: f(rgb.shade(dark[gtk.STATE_ACTIVE], 0.95)),
            gtk.STATE_SELECTED: f(rgb.shade(dark[gtk.STATE_ACTIVE], 0.95)),
            gtk.STATE_PRELIGHT: f(dark[gtk.STATE_PRELIGHT])
            }

        self.light_line_colors = {
            gtk.STATE_NORMAL: f(rgb.shade(light[gtk.STATE_NORMAL], 1.2)),
            gtk.STATE_ACTIVE: f(rgb.shade(light[gtk.STATE_NORMAL], 1.2)),
            gtk.STATE_SELECTED: None,
            gtk.STATE_PRELIGHT: f(rgb.shade(light[gtk.STATE_PRELIGHT], 1.2))
            }

        self.text_state = {
            gtk.STATE_NORMAL: gtk.STATE_NORMAL,
            gtk.STATE_ACTIVE: gtk.STATE_ACTIVE,
            gtk.STATE_SELECTED: gtk.STATE_NORMAL,
            gtk.STATE_PRELIGHT: gtk.STATE_PRELIGHT
            }

        self.base_hack = f(gtk.gdk.color_parse("#F2F2F2"))
        return


class PathBarThemeHicolor:

    PRELIT_NORMAL = 10
    PRELIT_ACTIVE = 11

    curvature = 0.5
    min_part_width = 56
    xpadding = 15
    ypadding = 10
    spacing = 10
    arrow_width = 15
    scroll_duration_ms = 150
    scroll_fps = 50
    animate = gtk.settings_get_default().get_property("gtk-enable-animations")

    def __init__(self):
        return

    def load(self, style):
        mid = style.mid
        dark = style.dark
        light = style.light
        text = style.text

        self.bg_colors = {
            gtk.STATE_NORMAL: (f(mid[gtk.STATE_NORMAL]),
                               f(mid[gtk.STATE_NORMAL])),

            gtk.STATE_ACTIVE: (f(mid[gtk.STATE_ACTIVE]),
                               f(mid[gtk.STATE_ACTIVE])),

            gtk.STATE_SELECTED: (f(mid[gtk.STATE_SELECTED]),
                                 f(mid[gtk.STATE_SELECTED])),

            self.PRELIT_NORMAL: (f(mid[gtk.STATE_PRELIGHT]),
                                 f(mid[gtk.STATE_PRELIGHT])),

            self.PRELIT_ACTIVE: (f(mid[gtk.STATE_PRELIGHT]),
                                 f(mid[gtk.STATE_PRELIGHT]))
            }

        self.dark_line_colors = {
            gtk.STATE_NORMAL: f(dark[gtk.STATE_NORMAL]),
            gtk.STATE_ACTIVE: f(dark[gtk.STATE_ACTIVE]),
            gtk.STATE_SELECTED: f(dark[gtk.STATE_SELECTED]),
            gtk.STATE_PRELIGHT: f(dark[gtk.STATE_PRELIGHT])
            }

        self.light_line_colors = {
            gtk.STATE_NORMAL: f(light[gtk.STATE_NORMAL]),
            gtk.STATE_ACTIVE: f(light[gtk.STATE_ACTIVE]),
            gtk.STATE_SELECTED: None,
            gtk.STATE_PRELIGHT: f(light[gtk.STATE_PRELIGHT])
            }

        self.text_state = {
            gtk.STATE_NORMAL: gtk.STATE_NORMAL,
            gtk.STATE_ACTIVE: gtk.STATE_ACTIVE,
            gtk.STATE_SELECTED: gtk.STATE_SELECTED,
            gtk.STATE_PRELIGHT: gtk.STATE_PRELIGHT
            }

        self.base_hack = None
        return


class PathBarThemes:

    DICT = {
        "Human": PathBarThemeHuman,
        "Human-Clearlooks": PathBarThemeHumanClearlooks,
        "HighContrastInverse": PathBarThemeHicolor,
        "HighContrastLargePrintInverse": PathBarThemeHicolor,
        "Dust": PathBarThemeDust,
        "Dust Sand": PathBarThemeDust,
        "New Wave": PathBarThemeNewWave
        }


class NavigationBar(PathBar):
    def __init__(self, group=None):
        PathBar.__init__(self)
        self.set_size_request(-1, 28)
        self.id_to_part = {}
        return

    def add_with_id(self, label, callback, id, obj, icon=None):
        """
        Add a new button with the given label/callback

        If there is the same id already, replace the existing one
        with the new one
        """
        if label == self.last_label:
                #ignoring duplicate
            return

        #print "Adding %s(%d)" % (label, id)


        # check if we have the button of that id or need a new one
        if id == 1 and len(self.id_to_part) > 0:
            # We already have the first item, just don't do anything
            return
        else:
            for i in self.id_to_part:
                part = self.id_to_part[i]
                if part.id >= id:
                    self.remove(part)

        part = PathPart(id, label, callback, obj)
        part.set_pathbar(self)
        self.id_to_part[id] = part
        gobject.timeout_add(150, self.append, part)

        if icon: part.set_icon(icon)
        self.last_label = label
        return

    def remove_id(self, id):
        if not id in self.id_to_part:
            return

        part = self.id_to_part[id]
        del self.id_to_part[id]
        self.remove(part)
        self.last_label = None
        return

    def remove_all(self):
        """remove all elements"""
        self.__parts = []
        self.id_to_part = {}
        self.queue_draw()
        self.last_label = None
        return

    def get_button_from_id(self, id):
        """
        return the button for the given id (or None)
        """
        if not id in self.id_to_part:
            return None
        return self.id_to_part[id]

    def get_label(self, id):
        """
        Return the label of the navigation button with the given id
        """
        if not id in self.id_to_part:
            return

########NEW FILE########
__FILENAME__ = rgb
# Copyright (C) 2009 Matthew McGowan
#
# Authors:
#   Matthew McGowan
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


import colorsys
from gtk.gdk import Color


def parse_colour_scheme(colour_scheme_str):
    scheme_dict = {}
    for ln in colour_scheme_str.splitlines():
        k, v = ln.split(':')
        scheme_dict[k.strip()] = gtk.gdk.color_parse(v.strip())
    return scheme_dict


def shade(color, k):
    # as seen in Murrine's cairo-support.c
    r = color.red_float
    g = color.green_float
    b = color.blue_float

    if (k == 1.0):
        return color

    h,l,s = colorsys.rgb_to_hls(r,g,b)

    l *= k
    if (l > 1.0):
        l = 1.0
    elif (l < 0.0):
        l = 0.0

    s *= k
    if (s > 1.0):
        s = 1.0
    elif (s < 0.0):
        s = 0.0

    r, g, b = colorsys.hls_to_rgb(h,l,s)

    return Color(int(r*65535), int(g*65535), int(b*65535))

def mix_color(color1, color2, mix_factor):
    # as seen in Murrine's cairo-support.c
    r = color1.red_float*(1-mix_factor)+color2.red_float*mix_factor
    g = color1.green_float*(1-mix_factor)+color2.green_float*mix_factor
    b = color1.blue_float*(1-mix_factor)+color2.blue_float*mix_factor
    return Color(int(r*65535), int(g*65535), int(b*65535))

def to_float(color):
    return color.red_float, color.green_float, color.blue_float

########NEW FILE########
__FILENAME__ = searchentry
# coding: utf-8
#
# SearchEntry - An enhanced search entry with alternating background colouring 
#               and timeout support
#
# Copyright (C) 2007 Sebastian Heinlein
#               2007-2009 Canonical Ltd.
#
# Authors:
#  Sebastian Heinlein <glatzor@ubuntu.com>
#
# This program is free software; you can redistribute it and/or modify it under
# the terms of the GNU General Public License as published by the Free Software
# Foundation; version 3.
#
# This program is distributed in the hope that it will be useful, but WITHOUT
# ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS
# FOR A PARTICULAR PURPOSE.  See the GNU General Public License for more
# details.
#
# You should have received a copy of the GNU General Public License along with
# this program; if not, write to the Free Software Foundation, Inc., 59 Temple
# Place, Suite 330, Boston, MA 02111-1307 USA

import sexy
import gtk
import gobject

class SearchEntry(sexy.IconEntry):

    # FIMXE: we need "can-undo", "can-redo" signals
    __gsignals__ = {'terms-changed':(gobject.SIGNAL_RUN_FIRST,
                                     gobject.TYPE_NONE,
                                     (gobject.TYPE_STRING,))}

    SEARCH_TIMEOUT = 400

    def __init__(self, icon_theme=None):
        """
        Creates an enhanced IconEntry that supports a time out when typing
        and uses a different background colour when the search is active
        """
        sexy.IconEntry.__init__(self)
        if not icon_theme:
            icon_theme = gtk.icon_theme_get_default()
        self._handler_changed = self.connect_after("changed",
                                                   self._on_changed)
        self.connect("icon-pressed", self._on_icon_pressed)
        image_find = gtk.image_new_from_stock(gtk.STOCK_FIND, 
                                              gtk.ICON_SIZE_MENU)
        self.set_icon(sexy.ICON_ENTRY_PRIMARY, image_find)

        self.empty_image = gtk.Image()
        self.clear_image = gtk.image_new_from_stock(gtk.STOCK_CLEAR, 
                                                    gtk.ICON_SIZE_MENU)
        self.set_icon(sexy.ICON_ENTRY_SECONDARY, self.clear_image)
        self.set_icon_highlight(sexy.ICON_ENTRY_PRIMARY, True)

        # Do not draw a yellow bg if an a11y theme is used
        settings = gtk.settings_get_default()
        theme = settings.get_property("gtk-theme-name")
        self._a11y = (theme.startswith("HighContrast") or
                      theme.startswith("LowContrast"))
        # data
        self._timeout_id = 0
        self._undo_stack = [""]
        self._redo_stack = []

    def _on_icon_pressed(self, widget, icon, mouse_button):
        """
        Emit the terms-changed signal without any time out when the clear
        button was clicked
        """
        if icon == sexy.ICON_ENTRY_SECONDARY:
            # clear with no signal and emit manually to avoid the
            # search-timeout
            self.clear_with_no_signal()
            self.grab_focus()
            self.emit("terms-changed", "")
        elif icon == sexy.ICON_ENTRY_PRIMARY:
            self.select_region(0, -1)
            self.grab_focus()

    def undo(self):
        if len(self._undo_stack) <= 1:
            return
        # pop top element and push on redo stack
        text = self._undo_stack.pop()
        self._redo_stack.append(text)
        # the next element is the one we want to display
        text = self._undo_stack.pop()
        self.set_text(text)
        self.set_position(-1)
    
    def redo(self):
        if not self._redo_stack:
            return
        # just reply the redo stack
        text = self._redo_stack.pop()
        self.set_text(text)
        self.set_position(-1)

    def clear(self):
        self.set_text("")
        self._check_style()

    def clear_with_no_signal(self):
        """Clear and do not send a term-changed signal"""
        self.handler_block(self._handler_changed)
        self.clear()
        self.handler_unblock(self._handler_changed)

    def _emit_terms_changed(self):
        text = self.get_text()
        # add to the undo stack once a term changes
        self._undo_stack.append(text)
        self.emit("terms-changed", text)

    def _on_changed(self, widget):
        """
        Call the actual search method after a small timeout to allow the user
        to enter a longer search term
        """
        self._check_style()
        if self._timeout_id > 0:
            gobject.source_remove(self._timeout_id)
        self._timeout_id = gobject.timeout_add(self.SEARCH_TIMEOUT,
                                               self._emit_terms_changed)

    def _check_style(self):
        """
        Use a different background colour if a search is active
        """
        # show/hide icon
        if self.get_text() != "":
            self.set_icon(sexy.ICON_ENTRY_SECONDARY, self.clear_image)
        else:
            self.set_icon(sexy.ICON_ENTRY_SECONDARY, self.empty_image)
        # Based on the Rhythmbox code
        yellowish = gtk.gdk.Color(63479, 63479, 48830)
        if self._a11y == True:
            return
        if self.get_text() == "":
            self.modify_base(gtk.STATE_NORMAL, None)
        else:
            self.modify_base(gtk.STATE_NORMAL, yellowish)

def on_entry_changed(self, terms):
    print terms

if __name__ == "__main__":

    icons = gtk.icon_theme_get_default()
    entry = SearchEntry(icons)
    entry.connect("terms-changed", on_entry_changed)

    win = gtk.Window()
    win.add(entry)
    win.set_size_request(400,400)
    win.show_all()

    gtk.main()
    

########NEW FILE########
__FILENAME__ = urltextview
# urlview.py
#  
#  Copyright (c) 2006 Sebastian Heinlein
#  
#  Author: Sebastian Heinlein <sebastian.heinlein@web.de>
#
#  This modul provides an inheritance of the gtk.TextView that is 
#  aware of http URLs and allows to open them in a browser.
#  It is based on the pygtk-demo "hypertext".
# 
#  This program is free software; you can redistribute it and/or 
#  modify it under the terms of the GNU General Public License as 
#  published by the Free Software Foundation; version 3.
# 
#  This program is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU General Public License for more details.
# 
#  You should have received a copy of the GNU General Public License
#  along with this program; if not, write to the Free Software
#  Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA 02111-1307
#  USA


import pygtk
import gtk
import pango
import subprocess
import os

class UrlTextView(gtk.TextView):
    def __init__(self, text=None):
        """TextView subclass that supports tagging/adding of links"""
        # init the parent
        gtk.TextView.__init__(self)
        # global hovering over link state
        self.hovering = False
        self.first = True
        # setup the buffer and signals
        self.set_property("editable", False)
        self.set_cursor_visible(False)
        self.buffer = gtk.TextBuffer()
        self.set_buffer(self.buffer)
        self.connect("event-after", self.event_after)
        self.connect("motion-notify-event", self.motion_notify_event)
        self.connect("visibility-notify-event", self.visibility_notify_event)
        #self.buffer.connect("changed", self.search_links)
        self.buffer.connect_after("insert-text", self.on_insert_text)
        # search text
        if text != None:
            self.buffer.set_text(text)

    def tag_link(self, start, end, url):
        """Apply the tag that marks links to the specified buffer selection"""
        tag = self.buffer.create_tag(None, 
                                     foreground="blue",
                                     underline=pango.UNDERLINE_SINGLE)
        tag.set_data("url", url)
        self.buffer.apply_tag(tag , start, end)

    def on_insert_text(self, buffer, iter_end, text, *args):
        """Search for http URLs in newly inserted text  
           and tag them accordingly"""
        iter = buffer.get_iter_at_offset(iter_end.get_offset() - len(text))
        iter_real_end = buffer.get_end_iter()
        for protocol in ["http://", "https://"]:
            while True:
                # search for the next URL in the buffer
                ret = iter.forward_search(protocol, 
                                      gtk.TEXT_SEARCH_VISIBLE_ONLY,
                                      iter_end)
                # if we reach the end break the loop
                if not ret:
                    break
                # get the position of the protocol prefix
                (match_start, match_end) = ret
                match_tmp = match_end.copy()
                while True:
                    # extend the selection to the complete URL
                    if match_tmp.forward_char():
                        text =  match_end.get_text(match_tmp)
                        if text in (" ", ")", "]", "\n", "\t",">","!"):
                            break
                    else:
                        break
                    match_end = match_tmp.copy()
                # call the tagging method for the complete URL
                url = match_start.get_text(match_end)
                tags = match_start.get_tags()
                tagged = False
                for tag in tags:
                    url = tag.get_data("url")
                    if url != "":
                        tagged = True
                        break
                if tagged == False:
                    self.tag_link(match_start, match_end, url)
                # set the starting point for the next search
                iter = match_end

    def event_after(self, text_view, event):
        """callback for mouse click events"""
        # we only react on left mouse clicks
        if event.type != gtk.gdk.BUTTON_RELEASE:
            return False
        if event.button != 1:
            return False

        # try to get a selection
        try:
            (start, end) = self.buffer.get_selection_bounds()
        except ValueError:
            pass
        else:
            if start.get_offset() != end.get_offset():
                return False

        # get the iter at the mouse position
        (x, y) = self.window_to_buffer_coords(gtk.TEXT_WINDOW_WIDGET,
                                              int(event.x), int(event.y))
        iter = self.get_iter_at_location(x, y)
        
        # call open_url if an URL is assigned to the iter
        tags = iter.get_tags()
        for tag in tags:
            url = tag.get_data("url")
            if url != None:
                self.open_url(url)
                break

    def open_url(self, url):
        """Open the specified URL in a browser"""
        # Find an appropiate browser
        if os.path.exists('/usr/bin/gnome-open'):
            command = ['gnome-open', url]
        else:
            command = ['x-www-browser', url]

        # Avoid to run the browser as user root
        if os.getuid() == 0 and os.environ.has_key('SUDO_USER'):
            command = ['sudo', '-u', os.environ['SUDO_USER']] + command

        subprocess.Popen(command)

    def motion_notify_event(self, text_view, event):
        """callback for the mouse movement event, that calls the
           check_hovering method with the mouse postition coordiantes"""
        x, y = text_view.window_to_buffer_coords(gtk.TEXT_WINDOW_WIDGET,
                                                 int(event.x), int(event.y))
        self.check_hovering(x, y)
        self.window.get_pointer()
        return False
    
    def visibility_notify_event(self, text_view, event):
        """callback if the widgets gets visible (e.g. moves to the foreground)
           that calls the check_hovering method with the mouse position
           coordinates"""
        (wx, wy, mod) = text_view.window.get_pointer()
        (bx, by) = text_view.window_to_buffer_coords(gtk.TEXT_WINDOW_WIDGET, wx,
                                                     wy)
        self.check_hovering(bx, by)
        return False

    def check_hovering(self, x, y):
        """Check if the mouse is above a tagged link and if yes show
           a hand cursor"""
        _hovering = False
        # get the iter at the mouse position
        iter = self.get_iter_at_location(x, y)
        
        # set _hovering if the iter has the tag "url"
        tags = iter.get_tags()
        for tag in tags:
            url = tag.get_data("url")
            if url != None:
                _hovering = True
                break

        # change the global hovering state
        if _hovering != self.hovering or self.first == True:
            self.first = False
            self.hovering = _hovering
            # Set the appropriate cursur icon
            if self.hovering:
                self.get_window(gtk.TEXT_WINDOW_TEXT).\
                        set_cursor(gtk.gdk.Cursor(gtk.gdk.HAND2))
            else:
                self.get_window(gtk.TEXT_WINDOW_TEXT).\
                        set_cursor(gtk.gdk.Cursor(gtk.gdk.LEFT_PTR))

########NEW FILE########
__FILENAME__ = wkwidget
# Copyright (C) 2009 Canonical
#
# Authors:
#  Michael Vogt
#
# This program is free software; you can redistribute it and/or modify it under
# the terms of the GNU General Public License as published by the Free Software
# Foundation; version 3.
#
# This program is distributed in the hope that it will be useful, but WITHOUT
# ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS
# FOR A PARTICULAR PURPOSE.  See the GNU General Public License for more
# details.
#
# You should have received a copy of the GNU General Public License along with
# this program; if not, write to the Free Software Foundation, Inc.,
# 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301 USA


import gobject
import gtk
import logging
import os
import tempfile
import string

gobject.threads_init()
import webkit

class WebkitWidget(webkit.WebView):
    """Widget that uses a webkit html form for its drawing

    All i18n should be done *outside* the html, currently
    no i18n supported. So all user visible strings should
    be set via templates.

    When a function is prefixed with "wksub_" it will be
    called on load of the page and the template in the
    html page will be replaced by the value that is returned
    by the function. E.g. the html has "... <p>$description</p>"
    then that will get replaced by the call to 
    "def wksub_description(self)".

    It support calls to functions via javascript title change
    methods. The title should look like any of those:
    - "call:func_name"
    - "call:func_name:argument"
    - "call:func_name:arg1,args2"
    """
    SUBSTITUTE_FUNCTION_PREFIX = "wksub_"

    def __init__(self, datadir, substitute=None):
        # init webkit
        webkit.WebView.__init__(self)
        # kill right click menu (the hard way) by stopping event
        # propergation on right-click
        self.connect("button-press-event", lambda w, e: e.button == 3)
        # setup vard
        self.datadir = datadir
        self._template = ""
        self._html = ""
        # callbacks
        self.connect('title-changed', self._on_title_changed)
        self.connect("show", self._show)
        # global settings
        settings = self.get_settings()
        settings.set_property("enable-plugins", False)
        if logging.root.level == logging.DEBUG:
            self.debug_html_path = os.path.join(
                tempfile.mkdtemp(), "software-center-render.html")
            logging.info("writing html output to '%s'" % self.debug_html_path)

    def refresh_html(self):
        self._show(None)

    # internal helpers
    def _show(self, widget):
        """Load and render when show is called"""
        logging.debug("%s.show() called" % self.__class__.__name__)
        self._load()
        self._substitute()
        self._render()
        #print self._html

    def _load(self):
        class_name = self.__class__.__name__        
        self._html_path = self.datadir+"/templates/%s.html" % class_name
        logging.debug("looking for '%s'" % self._html_path)
        if os.path.exists(self._html_path):
            self._template = open(self._html_path).read()

    def _render(self):
        # FIXME: use self._html_path here as base_uri ?
        self.load_html_string(self._html, "file:/")
        # If we are debugging, save us a copy of the substitued HTML
        if logging.root.level == logging.DEBUG:
            f = open(self.debug_html_path, "w")
            logging.info("writing html output to '%s'" % self.debug_html_path)
            f.write(self._html)
            f.close()

    def _substitute(self, subs=None):
        """
        substituate template strings in the html text. If a dict is passed
        to the argument "subs" that will be used for the substitution.
        Otherwise it will call all functions that are prefixed with 
        "wksub_" and use those values for the substitution
        """
        if subs is None:
            subs = {}
            for (k, v) in self.__class__.__dict__.iteritems():
                if callable(v) and k.startswith(self.SUBSTITUTE_FUNCTION_PREFIX):
                    subs[k[len(self.SUBSTITUTE_FUNCTION_PREFIX):]] = v(self)
        self._html = string.Template(self._template).safe_substitute(subs)

    # internal callbacks
    def _on_title_changed(self, view, frame, title):
        logging.debug("%s: title_changed %s %s %s" % (self.__class__.__name__,
                                                      view, frame, title))
        # no op - needed to reset the title after a action so that
        #         the action can be triggered again
        if title.startswith("nop"):
            return
        # call directive looks like:
        #  "call:func:arg1,arg2"
        #  "call:func"
        if title.startswith("call:"):
            args_str = ""
            args_list = []
            # try long form (with arguments) first
            try:
                (t,funcname,args_str) = title.split(":")
            except ValueError:
                # now try short (without arguments)
                (t,funcname) = title.split(":")
            if args_str:
                args_list = args_str.split(",")
            # see if we have it and if it can be called
            f = getattr(self, funcname)
            if f and callable(f):
                f(*args_list)
            # now we need to reset the title
            self.execute_script('document.title = "nop"')


class WKTestWidget(WebkitWidget):

    def func1(self, arg1, arg2):
        print "func1: ", arg1, arg2

    def func2(self):
        print "func2"

if __name__ == "__main__":
    logging.basicConfig(level=logging.DEBUG)

    import sys

    if len(sys.argv) > 1:
        datadir = sys.argv[1]
    elif os.path.exists("./data"):
        datadir = "./data"
    else:
        datadir = "/usr/share/software-center"


    subs = {
        'key' : 'subs value' 
    }
    w = WKTestWidget(datadir, subs)

    win = gtk.Window()
    scroll = gtk.ScrolledWindow()
    scroll.add(w)
    win.add(scroll)
    win.set_size_request(600,400)
    win.show_all()

    gtk.main()

########NEW FILE########
