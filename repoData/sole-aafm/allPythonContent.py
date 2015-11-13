__FILENAME__ = aafm-gui
#!/usr/bin/env python2

import pygtk
pygtk.require('2.0')
import gtk
import gobject
import os
import shutil
import socket
import datetime
import stat
import pwd
import grp
import urllib

if os.name == 'nt':
	import win32api
	import win32con
	import win32security

from TreeViewFile import TreeViewFile
from Aafm import Aafm


class Aafm_GUI:

	QUEUE_ACTION_COPY_TO_DEVICE = 'copy_to_device'
	QUEUE_ACTION_COPY_FROM_DEVICE = 'copy_from_device'
	QUEUE_ACTION_MOVE_IN_DEVICE = 'move_in_device'
	QUEUE_ACTION_MOVE_IN_HOST = 'move_in_host'

	# These constants are for dragging files to Nautilus
	XDS_ATOM = gtk.gdk.atom_intern("XdndDirectSave0")
	TEXT_ATOM = gtk.gdk.atom_intern("text/plain")
	XDS_FILENAME = 'whatever.txt'

	def __init__(self):
		
		# The super core
		self.aafm = Aafm('adb', os.getcwd(), '/mnt/sdcard/')
		self.queue = []

		self.basedir = os.path.dirname(os.path.abspath(__file__))
		
		if os.name == 'nt':
			self.get_owner = self._get_owner_windows
			self.get_group = self._get_group_windows
		else:
			self.get_owner = self._get_owner
			self.get_group = self._get_group

		# Build main window from XML
		builder = gtk.Builder()
		builder.add_from_file(os.path.join(self.basedir, "data/glade/interface.xml"))
		builder.connect_signals({ "on_window_destroy" : gtk.main_quit })
		self.window = builder.get_object("window")

		imageDir = gtk.Image()
		imageDir.set_from_file(os.path.join(self.basedir, './data/icons/folder.png'))
		imageFile = gtk.Image()
		imageFile.set_from_file(os.path.join(self.basedir, './data/icons/file.png'))
		
		# Host and device TreeViews
		
		# HOST
		self.host_treeViewFile = TreeViewFile(imageDir.get_pixbuf(), imageFile.get_pixbuf())
		
		hostFrame = builder.get_object('frameHost')
		hostFrame.get_child().add(self.host_treeViewFile.get_view())
		
		hostTree = self.host_treeViewFile.get_tree()
		hostTree.connect('row-activated', self.host_navigate_callback)
		hostTree.connect('button_press_event', self.on_host_tree_view_contextual_menu)
	
		host_targets = [
			('DRAG_SELF', gtk.TARGET_SAME_WIDGET, 0),
			('ADB_text', 0, 1),
			('text/plain', 0, 2)
		]

		hostTree.enable_model_drag_dest(
			host_targets,
			gtk.gdk.ACTION_DEFAULT | gtk.gdk.ACTION_COPY | gtk.gdk.ACTION_MOVE
		)
		hostTree.connect('drag-data-received', self.on_host_drag_data_received)

		hostTree.enable_model_drag_source(
			gtk.gdk.BUTTON1_MASK,
			host_targets,
			gtk.gdk.ACTION_DEFAULT | gtk.gdk.ACTION_COPY | gtk.gdk.ACTION_MOVE
		)
		hostTree.connect('drag_data_get', self.on_host_drag_data_get)
		
		self.hostFrame = hostFrame
		self.hostName = socket.gethostname()


		# DEVICE
		self.device_treeViewFile = TreeViewFile(imageDir.get_pixbuf(), imageFile.get_pixbuf())
		
		deviceFrame = builder.get_object('frameDevice')
		deviceFrame.get_child().add(self.device_treeViewFile.get_view())

		deviceTree = self.device_treeViewFile.get_tree()
		deviceTree.connect('row-activated', self.device_navigate_callback)
		deviceTree.connect('button_press_event', self.on_device_tree_view_contextual_menu)

		device_targets = [
			('DRAG_SELF', gtk.TARGET_SAME_WIDGET, 0),
			('ADB_text', 0, 1),
			('XdndDirectSave0', 0, 2),
			('text/plain', 0, 3)
		]

		deviceTree.enable_model_drag_dest(
			device_targets,
			gtk.gdk.ACTION_DEFAULT | gtk.gdk.ACTION_COPY | gtk.gdk.ACTION_MOVE
		)
		deviceTree.connect('drag-data-received', self.on_device_drag_data_received)
		
		deviceTree.enable_model_drag_source(
			gtk.gdk.BUTTON1_MASK,
			device_targets,
			gtk.gdk.ACTION_DEFAULT | gtk.gdk.ACTION_COPY | gtk.gdk.ACTION_MOVE
		)
		deviceTree.connect('drag-data-get', self.on_device_drag_data_get)
		deviceTree.connect('drag-begin', self.on_device_drag_begin)
		
		self.deviceFrame = deviceFrame


		# Progress bar
		self.progress_bar = builder.get_object('progressBar')

		# Some more subtle details...
		self.window.set_title("Android ADB file manager")
		#self.adb = 'adb'
		self.host_cwd = os.getcwd()
		self.device_cwd = '/mnt/sdcard/'

		self.refresh_host_files()
		self.refresh_device_files()

		# Make both panels equal in size (at least initially)
		panelsPaned = builder.get_object('panelsPaned')
		panelW, panelH = panelsPaned.size_request()
		halfW = panelW / 2
		panelsPaned.set_position(halfW)

		# And we're done!
		self.window.show_all()


	def host_navigate_callback(self, widget, path, view_column):
		
		row = path[0]
		model = widget.get_model()
		iter = model.get_iter(row)
		is_dir = model.get_value(iter, 0)
		name = model.get_value(iter, 1)

		if is_dir:
			self.host_cwd = os.path.normpath(os.path.join(self.host_cwd, name))
			self.aafm.set_host_cwd(self.host_cwd)
			self.refresh_host_files()


	def device_navigate_callback(self, widget, path, view_column):

		row = path[0]
		model = widget.get_model()
		iter = model.get_iter(row)
		is_dir = model.get_value(iter, 0)
		name = model.get_value(iter, 1)

		if is_dir:
			self.device_cwd = self.aafm.device_path_normpath(self.aafm.device_path_join(self.device_cwd, name))
			self.aafm.set_device_cwd(self.device_cwd)
			self.refresh_device_files()

	
	def refresh_host_files(self):
		self.host_treeViewFile.load_data(self.dir_scan_host(self.host_cwd))
		self.hostFrame.set_label('%s:%s' % (self.hostName, self.host_cwd))


	def refresh_device_files(self):
		self.device_treeViewFile.load_data(self.dir_scan_device(self.device_cwd))
		self.deviceFrame.set_label('%s:%s' % ('device', self.device_cwd))


	def get_treeviewfile_selected(self, treeviewfile):
		values = []
		model, rows = treeviewfile.get_tree().get_selection().get_selected_rows()

		for row in rows:
			iter = model.get_iter(row)
			filename = model.get_value(iter, 1)
			is_directory = model.get_value(iter, 0)
			values.append({'filename': filename, 'is_directory': is_directory})

		return values


	def get_host_selected_files(self):
		return self.get_treeviewfile_selected(self.host_treeViewFile)

	def get_device_selected_files(self):
		return self.get_treeviewfile_selected(self.device_treeViewFile)


	""" Walks through a directory and return the data in a tree-style list 
		that can be used by the TreeViewFile """
	def dir_scan_host(self, directory):
		output = []

		root, dirs, files = next(os.walk(directory))

		dirs.sort()
		files.sort()

		output.append({'directory': True, 'name': '..', 'size': 0, 'timestamp': '',
				'permissions': '',
				'owner': '',
				'group': ''})

		for d in dirs:
			path = os.path.join(directory, d)
			output.append({
				'directory': True,
				'name': d,
				'size': 0,
				'timestamp': self.format_timestamp(os.path.getmtime(path)),
				'permissions': self.get_permissions(path),
				'owner': self.get_owner(path),
				'group': self.get_group(path)
			})

		for f in files:
			path = os.path.join(directory, f)
			size = os.path.getsize(path)
			output.append({
				'directory': False,
				'name': f,
				'size': size,
				'timestamp': self.format_timestamp(os.path.getmtime(path)),
				'permissions': self.get_permissions(path),
				'owner': self.get_owner(path),
				'group': self.get_group(path)
			})

		return output

	""" The following three methods are probably NOT the best way of doing things.
	At least according to all the warnings that say os.stat is very costly
	and should be cached."""
	def get_permissions(self, filename):
		st = os.stat(filename)
		mode = st.st_mode
		permissions = ''

		bits = [ 
			stat.S_IRUSR, stat.S_IWUSR, stat.S_IXUSR,
			stat.S_IRGRP, stat.S_IWGRP, stat.S_IXGRP,
			stat.S_IROTH, stat.S_IWOTH, stat.S_IXOTH
		]

		attrs = ['r', 'w', 'x']

		for i in range(0, len(bits)):
			bit = bits[i]
			attr = attrs[i % len(attrs)]

			if bit & mode:
				permissions += attr
			else:
				permissions += '-'

		return permissions

	def _get_owner(self, filename):
		st = os.stat(filename)
		uid = st.st_uid
		try:
			user = pwd.getpwuid(uid)[0]
		except KeyError:
			print ('unknown uid %d for file %s' % (uid, filename))
			user = 'unknown'
		return user
		
	def _get_owner_windows(self, filename):
		sd = win32security.GetFileSecurity(filename, win32security.OWNER_SECURITY_INFORMATION)
		owner_sid = sd.GetSecurityDescriptorOwner()
		name, domain, type = win32security.LookupAccountSid(None, owner_sid)
		return name

	def _get_group(self, filename):
		st = os.stat(filename)
		gid = st.st_gid
		try:
			groupname = grp.getgrgid(gid)[0]
		except KeyError:
			print ('unknown gid %d for file %s' % (gid, filename))
			groupname = 'unknown'
		return groupname
	
	def _get_group_windows(self, filename):
		return ""


	def format_timestamp(self, timestamp):
		d = datetime.datetime.fromtimestamp(timestamp)
		return d.strftime(r'%Y-%m-%d %H:%M')

	""" Like dir_scan_host, but in the connected Android device """
	def dir_scan_device(self, directory):
		output = []
		
		entries = self.aafm.get_device_file_list()

		dirs = []
		files = []

		for filename, entry in entries.iteritems():
			if entry['is_directory']:
				dirs.append(filename)
			else:
				files.append(filename)

		dirs.sort()
		files.sort()

		output.append({'directory': True, 'name': '..', 'size': 0, 'timestamp': '', 'permissions': '', 'owner': '', 'group': ''})

		for d in dirs:
			output.append({
				'directory': True,
				'name': d,
				'size': 0,
				'timestamp': self.format_timestamp(entries[d]['timestamp']), 
				'permissions': entries[d]['permissions'],
				'owner': entries[d]['owner'],
				'group': entries[d]['group']
			})

		for f in files:
			size = int(entries[f]['size'])
			output.append({
				'directory': False,
				'name': f,
				'size': size,
				'timestamp': self.format_timestamp(entries[f]['timestamp']),
				'permissions': entries[f]['permissions'],
				'owner': entries[f]['owner'],
				'group': entries[f]['group']
			})

		return output

	def on_host_tree_view_contextual_menu(self, widget, event):
		if event.button == 3: # Right click
			builder = gtk.Builder()
			builder.add_from_file(os.path.join(self.basedir, 'data/glade/menu_contextual_host.xml'))
			menu = builder.get_object('menu')
			builder.connect_signals({
				'on_menuHostCopyToDevice_activate': self.on_host_copy_to_device_callback,
				'on_menuHostCreateDirectory_activate': self.on_host_create_directory_callback,
				'on_menuHostRefresh_activate': self.on_host_refresh_callback,
				'on_menuHostDeleteItem_activate': self.on_host_delete_item_callback,
				'on_menuHostRenameItem_activate': self.on_host_rename_item_callback
			})

			# Ensure only right options are available
			num_selected = len(self.get_host_selected_files())
			has_selection = num_selected > 0

			menuCopy = builder.get_object('menuHostCopyToDevice')
			menuCopy.set_sensitive(has_selection)

			menuDelete = builder.get_object('menuHostDeleteItem')
			menuDelete.set_sensitive(has_selection)

			menuRename = builder.get_object('menuHostRenameItem')
			menuRename.set_sensitive(num_selected == 1)	

			menu.popup(None, None, None, event.button, event.time)
			return True
		
		# Not consuming the event
		return False

	# Copy to device
	def on_host_copy_to_device_callback(self, widget):
		for row in self.get_host_selected_files():
			src = os.path.join(self.host_cwd, row['filename'])
			self.add_to_queue(self.QUEUE_ACTION_COPY_TO_DEVICE, src, self.device_cwd)
		self.process_queue()

	
	# Create host directory
	def on_host_create_directory_callback(self, widget):
		directory_name = self.dialog_get_directory_name()

		if directory_name is None:
			return

		full_path = os.path.join(self.host_cwd, directory_name)
		if not os.path.exists(full_path):
			os.mkdir(full_path)
			self.refresh_host_files()


	def on_host_refresh_callback(self, widget):
		self.refresh_host_files()


	def on_host_delete_item_callback(self, widget):
		selected = self.get_host_selected_files()
		items = []
		for item in selected:
			items.append(item['filename'])
			
		result = self.dialog_delete_confirmation(items)

		if result == gtk.RESPONSE_OK:
			for item in items:
				full_item_path = os.path.join(self.host_cwd, item)
				self.delete_item(full_item_path)
				self.refresh_host_files()

	def delete_item(self, path):
		if os.path.isfile(path):
			os.remove(path)
		else:
			shutil.rmtree(path)

	def on_host_rename_item_callback(self, widget):
		old_name = self.get_host_selected_files()[0]['filename']
		new_name = self.dialog_get_item_name(old_name)

		if new_name is None:
			return

		full_src_path = os.path.join(self.host_cwd, old_name)
		full_dst_path = os.path.join(self.host_cwd, new_name)

		shutil.move(full_src_path, full_dst_path)
		self.refresh_host_files()

	def on_device_tree_view_contextual_menu(self, widget, event):
		if event.button == 3: # Right click
			builder = gtk.Builder()
			builder.add_from_file(os.path.join(self.basedir, "data/glade/menu_contextual_device.xml"))
			menu = builder.get_object("menu")
			builder.connect_signals({
				'on_menuDeviceDeleteItem_activate': self.on_device_delete_item_callback,
				'on_menuDeviceCreateDirectory_activate': self.on_device_create_directory_callback,
				'on_menuDeviceRefresh_activate': self.on_device_refresh_callback,
				'on_menuDeviceCopyToComputer_activate': self.on_device_copy_to_computer_callback,
				'on_menuDeviceRenameItem_activate': self.on_device_rename_item_callback
			})

			# Ensure only right options are available
			num_selected = len(self.get_device_selected_files())
			has_selection = num_selected > 0
			menuDelete = builder.get_object('menuDeviceDeleteItem')
			menuDelete.set_sensitive(has_selection)
			
			menuCopy = builder.get_object('menuDeviceCopyToComputer')
			menuCopy.set_sensitive(has_selection)

			menuRename = builder.get_object('menuDeviceRenameItem')
			menuRename.set_sensitive(num_selected == 1)

			menu.popup(None, None, None, event.button, event.time)
			return True
		
		# don't consume the event, so we can still double click to navigate
		return False

	def on_device_delete_item_callback(self, widget):
		selected = self.get_device_selected_files()

		items = []

		for item in selected:
			items.append(item['filename'])

		result = self.dialog_delete_confirmation(items)

		if result == gtk.RESPONSE_OK:
			for item in items:
				full_item_path = self.aafm.device_path_join(self.device_cwd, item)
				self.aafm.device_delete_item(full_item_path)
				self.refresh_device_files()
		else:
			print('no no')


	def dialog_delete_confirmation(self, items):
		items.sort()
		joined = ', '.join(items)
		dialog = gtk.MessageDialog(
			parent = None,
			flags = gtk.DIALOG_MODAL | gtk.DIALOG_DESTROY_WITH_PARENT,
			type = gtk.MESSAGE_QUESTION,
			buttons = gtk.BUTTONS_OK_CANCEL,
			message_format = "Are you sure you want to delete %d items?" % len(items)
		)
		dialog.format_secondary_markup('%s will be deleted. This action cannot be undone.' % joined)
		dialog.show_all()
		result = dialog.run()
		
		dialog.destroy()
		return result

	def on_device_create_directory_callback(self, widget):
		directory_name = self.dialog_get_directory_name()

		# dialog was cancelled
		if directory_name is None:
			return

		full_path = self.aafm.device_path_join(self.device_cwd, directory_name)
		self.aafm.device_make_directory(full_path)
		self.refresh_device_files()


	def dialog_get_directory_name(self):
		dialog = gtk.MessageDialog(
			None,
			gtk.DIALOG_MODAL | gtk.DIALOG_DESTROY_WITH_PARENT,
			gtk.MESSAGE_QUESTION,
			gtk.BUTTONS_OK_CANCEL,
			None)

		dialog.set_markup('Please enter new directory name:')

		entry = gtk.Entry()
		entry.connect('activate', self.dialog_response, dialog, gtk.RESPONSE_OK)

		hbox = gtk.HBox()
		hbox.pack_start(gtk.Label('Name:'), False, 5, 5)
		hbox.pack_end(entry)

		dialog.vbox.pack_end(hbox, True, True, 0)
		dialog.show_all()

		result = dialog.run()

		text = entry.get_text()
		dialog.destroy()

		if result == gtk.RESPONSE_OK:
			return text
		else:
			return None


	def dialog_response(self, entry, dialog, response):
		dialog.response(response)


	def on_device_refresh_callback(self, widget):
		self.refresh_device_files()


	def on_device_copy_to_computer_callback(self, widget):
		selected = self.get_device_selected_files()
		task = self.copy_from_device_task(selected)
		gobject.idle_add(task.next)


	def copy_from_device_task(self, rows):
		completed = 0
		total = len(rows)

		self.update_progress()

		for row in rows:
			filename = row['filename']
			is_directory = row['is_directory']

			full_device_path = self.aafm.device_path_join(self.device_cwd, filename)
			full_host_path = self.host_cwd
			
			self.aafm.copy_to_host(full_device_path, full_host_path)
			completed = completed + 1
			self.refresh_host_files()
			self.update_progress(completed * 1.0 / total)

			yield True

		yield False

	def on_device_rename_item_callback(self, widget):
		old_name = self.get_device_selected_files()[0]['filename']
		new_name = self.dialog_get_item_name(old_name)

		if new_name is None:
			return

		full_src_path = self.aafm.device_path_join(self.device_cwd, old_name)
		full_dst_path = self.aafm.device_path_join(self.device_cwd, new_name)

		self.aafm.device_rename_item(full_src_path, full_dst_path)
		self.refresh_device_files()
	
	def dialog_get_item_name(self, old_name):
		dialog = gtk.MessageDialog(
			None,
			gtk.DIALOG_MODAL | gtk.DIALOG_DESTROY_WITH_PARENT,
			gtk.MESSAGE_QUESTION,
			gtk.BUTTONS_OK_CANCEL,
			None)

		dialog.set_markup('Please enter new name:')

		entry = gtk.Entry()
		entry.connect('activate', self.dialog_response, dialog, gtk.RESPONSE_OK)
		entry.set_text(old_name)

		hbox = gtk.HBox()
		hbox.pack_start(gtk.Label('Name:'), False, 5, 5)
		hbox.pack_end(entry)

		dialog.vbox.pack_end(hbox, True, True, 0)
		dialog.show_all()

		result = dialog.run()
		text = entry.get_text()
		dialog.destroy()
		
		if result == gtk.RESPONSE_OK:
			return text
		else:
			return None


	def update_progress(self, value = None):
		if value is None:
			self.progress_bar.set_fraction(0)
			self.progress_bar.set_text("")
			self.progress_bar.pulse()
		else:
			self.progress_bar.set_fraction(value)

			self.progress_bar.set_text("%d%%" % (value * 100))

		if value >= 1:
			self.progress_bar.set_text("Done")
			self.progress_bar.set_fraction(0)


	def on_host_drag_data_get(self, widget, context, selection, target_type, time):
		data = '\n'.join(['file://' + urllib.quote(os.path.join(self.host_cwd, item['filename'])) for item in self.get_host_selected_files()])
		
		selection.set(selection.target, 8, data)

	
	def on_host_drag_data_received(self, tree_view, context, x, y, selection, info, timestamp):
		data = selection.data
		type = selection.type
		drop_info = tree_view.get_dest_row_at_pos(x, y)
		destination = self.host_cwd
		
		if drop_info:
			model = tree_view.get_model()
			path, position = drop_info
			
			if position in [ gtk.TREE_VIEW_DROP_INTO_OR_BEFORE, gtk.TREE_VIEW_DROP_INTO_OR_AFTER ]:
				iter = model.get_iter(path)
				is_directory = model.get_value(iter, 0)
				name = model.get_value(iter, 1)

				# If dropping over a folder, copy things to that folder
				if is_directory:
					destination = os.path.join(self.host_cwd, name)

		for line in [line.strip() for line in data.split('\n')]:
			if line.startswith('file://'):
				source = urllib.unquote(line.replace('file://', '', 1))

				if type == 'DRAG_SELF':
					self.add_to_queue(self.QUEUE_ACTION_MOVE_IN_HOST, source, destination)
				elif type == 'ADB_text':
					self.add_to_queue(self.QUEUE_ACTION_COPY_FROM_DEVICE, source, destination)

		self.process_queue()



	def on_device_drag_begin(self, widget, context):
		
		context.source_window.property_change(self.XDS_ATOM, self.TEXT_ATOM, 8, gtk.gdk.PROP_MODE_REPLACE, self.XDS_FILENAME)
	

	def on_device_drag_data_get(self, widget, context, selection, target_type, time):
		
		if selection.target == 'XdndDirectSave0':
			type, format, destination_file = context.source_window.property_get(self.XDS_ATOM, self.TEXT_ATOM)

			if destination_file.startswith('file://'):
				destination = os.path.dirname(urllib.unquote(destination_file).replace('file://', '', 1))
				for item in self.get_device_selected_files():
					self.add_to_queue(self.QUEUE_ACTION_COPY_FROM_DEVICE, self.aafm.device_path_join(self.device_cwd, item['filename']), destination)

				self.process_queue()
			else:
				print("ERROR: Destination doesn't start with file://?!!?")


		else:
			selection.set(selection.target, 8, '\n'.join(['file://' + urllib.quote(self.aafm.device_path_join(self.device_cwd, item['filename'])) for item in self.get_device_selected_files()]))
	

	def on_device_drag_data_received(self, tree_view, context, x, y, selection, info, timestamp):

		data = selection.data
		type = selection.type
		drop_info = tree_view.get_dest_row_at_pos(x, y)
		destination = self.device_cwd
		
		# When dropped over a row
		if drop_info:
			model = tree_view.get_model()
			path, position = drop_info
			
			if position in [ gtk.TREE_VIEW_DROP_INTO_OR_BEFORE, gtk.TREE_VIEW_DROP_INTO_OR_AFTER ]:
				iter = model.get_iter(path)
				is_directory = model.get_value(iter, 0)
				name = model.get_value(iter, 1)

				# If dropping over a folder, copy things to that folder
				if is_directory:
					destination = self.aafm.device_path_join(self.device_cwd, name)

		if type == 'DRAG_SELF':
			if self.device_cwd != destination:
				for line in [line.strip() for line in data.split('\n')]:
					if line.startswith('file://'):
						source = urllib.unquote(line.replace('file://', '', 1))
						if source != destination:
							name = self.aafm.device_path_basename(source)
							self.add_to_queue(self.QUEUE_ACTION_MOVE_IN_DEVICE, source, os.path.join(destination, name))
		else:
			# COPY stuff
			for line in [line.strip() for line in data.split('\n')]:
				if line.startswith('file://'):
					source = urllib.unquote(line.replace('file://', '', 1))
					self.add_to_queue(self.QUEUE_ACTION_COPY_TO_DEVICE, source, destination)
		
		self.process_queue()


	def add_to_queue(self, action, src_file, dst_path):
		self.queue.append([action, src_file, dst_path])
	

	def process_queue(self):
		task = self.process_queue_task()
		gobject.idle_add(task.next)
	
	def process_queue_task(self):
		completed = 0
		self.update_progress()

		while len(self.queue) > 0:
			item = self.queue.pop()
			action, src, dst = item

			if action == self.QUEUE_ACTION_COPY_TO_DEVICE:
				self.aafm.copy_to_device(src, dst)
				self.refresh_device_files()
			if action == self.QUEUE_ACTION_COPY_FROM_DEVICE:
				self.aafm.copy_to_host(src, dst)
				self.refresh_host_files()
			elif action == self.QUEUE_ACTION_MOVE_IN_DEVICE:
				self.aafm.device_rename_item(src, dst)
				self.refresh_device_files()
			elif action == self.QUEUE_ACTION_MOVE_IN_HOST:
				shutil.move(src, dst)
				self.refresh_host_files()

			completed = completed + 1
			total = len(self.queue) + 1
			self.update_progress(completed * 1.0 / total)

			yield True

		yield False



	def die_callback(self, widget, data=None):
		self.destroy(widget, data)


	def destroy(self, widget, data=None):
		gtk.main_quit()


	def main(self):
		gtk.main()


if __name__ == '__main__':
	gui = Aafm_GUI()
	gui.main()

########NEW FILE########
__FILENAME__ = Aafm
import os
import re
import subprocess
import time
import pipes

class Aafm:
	def __init__(self, adb='adb', host_cwd=None, device_cwd='/'):
		self.adb = adb
		self.host_cwd = host_cwd
		self.device_cwd = device_cwd
		
		# The Android device should always use POSIX path style separators (/),
		# so we can happily use os.path.join when running on Linux (which is POSIX)
		# But we can't use it when running on Windows machines because they use '\\'
		# So we'll import the robust, tested and proven posixpath module,
		# instead of using an inferior poorman's replica.
		# Not sure how much of a hack is this...
		# Feel free to illuminate me if there's a better way.
		pathmodule = __import__('posixpath')
		
		self._path_join_function = pathmodule.join
		self._path_normpath_function = pathmodule.normpath
		self._path_basename_function = pathmodule.basename
		
		self.busybox = False
		self.probe_for_busybox()
		

	def execute(self, command):
		print "EXECUTE=", command
		process = subprocess.Popen(command, shell=True, stdout=subprocess.PIPE).stdout

		lines = []

		while True:
			line = process.readline()
			
			if not line:
				break

			lines.append(line)
		
		return lines


	def set_host_cwd(self, cwd):
		self.host_cwd = cwd
	

	def set_device_cwd(self, cwd):
		self.device_cwd = cwd


	def get_device_file_list(self):
		return self.parse_device_list( self.device_list_files( self._path_join_function(self.device_cwd, '') ) )

	def probe_for_busybox(self):
		command = '%s shell ls --help' % (self.adb)
		lines = self.execute(command)
		if len(lines) > 0 and lines[0].startswith('BusyBox'):
			print "BusyBox ls detected"
			self.busybox = True

	def device_list_files(self, device_dir):
		if self.busybox:
			command = '%s shell ls -l -A -e --color=never %s' % (self.adb, self.device_escape_path( device_dir))
		else:
			command = '%s shell ls -l -a %s' % (self.adb, self.device_escape_path(device_dir))
		lines = self.execute(command)
		return lines


	def parse_device_list(self, lines):
		entries = {}

		if self.busybox:
			pattern = re.compile(r"^(?P<permissions>[dl\-][rwx\-]+)\s+(?P<hardlinks>\d+)\s+(?P<owner>[\w_]+)\s+(?P<group>[\w_]+)\s+(?P<size>\d+)\s+(?P<datetime>\w{3} \w{3}\s+\d+\s+\d{2}:\d{2}:\d{2} \d{4}) (?P<name>.+)$")
		else:
			pattern = re.compile(r"^(?P<permissions>[dl\-][rwx\-]+) (?P<owner>\w+)\W+(?P<group>[\w_]+)\W*(?P<size>\d+)?\W+(?P<datetime>\d{4}-\d{2}-\d{2} \d{2}:\d{2}) (?P<name>.+)$")
		for line in lines:
			line = line.rstrip()
			match = pattern.match(line)
			
			if match:
				permissions = match.group('permissions')
				owner = match.group('owner')
				group = match.group('group')
				fsize = match.group('size')
				if fsize is None:
					fsize = 0
				filename = match.group('name')
				
				if self.busybox:
					date_format = "%a %b %d %H:%M:%S %Y"
				else:
					date_format = "%Y-%m-%d %H:%M"
				timestamp = time.mktime((time.strptime(match.group('datetime'), date_format)))
				
				is_directory = permissions.startswith('d')

				if permissions.startswith('l'):
					filename, target = filename.split(' -> ')
					is_directory = self.is_device_file_a_directory(target)

				entries[filename] = { 
					'is_directory': is_directory,
					'size': fsize,
					'timestamp': timestamp,
					'permissions': permissions,
					'owner': owner,
					'group': group
				}

			else:
				print line, "wasn't matched, please report to the developer!"

		return entries


	# NOTE: Currently using pipes.quote, in the future we might detect shlex.quote
	# availability and use it instead. Or not. /me is confused about python 3k
	def device_escape_path(self, path):
		return pipes.quote( path )


	def is_device_file_a_directory(self, device_file):
		parent_dir = os.path.dirname(device_file)
		filename = os.path.basename(device_file)
		lines = self.device_list_files(parent_dir)
		entries = self.parse_device_list(lines)

		if not entries.has_key(filename):
			return False

		return entries[filename]['is_directory']

	def device_make_directory(self, directory):
		pattern = re.compile(r'(\w|_|-)+')
		base = os.path.basename(directory)
		if pattern.match(base):
			self.execute( '%s shell mkdir %s' % (self.adb, self.device_escape_path( directory )) )
		else:
			print 'invalid directory name', directory
	
	
	def device_delete_item(self, path):

		if self.is_device_file_a_directory(path):
			entries = self.parse_device_list(self.device_list_files(path))

			for filename, entry in entries.iteritems():
				entry_full_path = os.path.join(path, filename)
				self.device_delete_item(entry_full_path)

			# finally delete the directory itself
			self.execute('%s shell rmdir %s' % (self.adb, self.device_escape_path(path)))

		else:
			self.execute('%s shell rm %s' % (self.adb, self.device_escape_path(path)))


	# See  __init__ for _path_join_function definition
	def device_path_join(self, a, *p):
		return self._path_join_function(a, *p)

	# Again, see __init_ for how _path_normpath_function is defined
	def device_path_normpath(self, path):
		return self._path_normpath_function(path)

	# idem
	def device_path_basename(self, path):
		return self._path_basename_function(path)


	def copy_to_host(self, device_file, host_directory):

		# We can only copy to a destination path, not to a file
		# TODO is this really needed?
		if os.path.isfile(host_directory):
			print "ERROR", host_directory, "is a file, not a directory"
			return

		if self.is_device_file_a_directory(device_file):

			# make sure host_directory exists before copying anything
			if not os.path.exists(host_directory):
				os.makedirs(host_directory)

			# Also make directory in host_directory
			dir_basename = os.path.basename( os.path.normpath( device_file ))
			final_host_directory = os.path.join( host_directory, dir_basename )
			
			if not os.path.exists( final_host_directory ):
				os.mkdir( final_host_directory )

			# copy recursively!
			entries = self.parse_device_list(self.device_list_files(device_file))

			for filename, entry in entries.iteritems():
				self.copy_to_host(os.path.join(device_file, filename), final_host_directory)
		else:
			host_file = os.path.join(host_directory, os.path.basename(device_file))
			self.execute('%s pull %s "%s"' % (self.adb, self.device_escape_path( device_file ), host_file))
	
	
	def copy_to_device(self, host_file, device_directory):

		if os.path.isfile( host_file ):

			self.execute('%s push "%s" %s' % (self.adb, host_file, self.device_escape_path( device_directory ) ) )

		else:

			normalized_directory = os.path.normpath( host_file )
			dir_basename = os.path.basename( normalized_directory )
			device_dst_dir = os.path.join( device_directory, dir_basename )

			# Ensures the directory exists beforehand
			self.device_make_directory( device_dst_dir )

			device_entries = self.parse_device_list( self.device_list_files( device_dst_dir ) )
			host_entries = os.listdir( normalized_directory )

			for entry in host_entries:

				src_file = os.path.join( normalized_directory, entry )
				
				if device_entries.has_key( entry ):
					
					# We only copy if the dst file is older or different in size
					if device_entries[ entry ]['timestamp'] >= os.path.getmtime( src_file ) or device_entries[ entry ]['size'] == os.path.getsize( src_file ):
						print "File is newer or the same, skipping"
						return

					self.copy_to_device( src_file, device_dst_dir )
                                else:
                                        self.copy_to_device( src_file, device_dst_dir )


	def device_rename_item(self, device_src_path, device_dst_path):
		items = self.parse_device_list(self.device_list_files(self.device_escape_path(os.path.dirname(device_dst_path))))
		filename = os.path.basename(device_dst_path)
		print filename

		if items.has_key(filename):
			print 'Filename %s already exists' % filename
			return

		self.execute('%s shell mv %s %s' % (self.adb, self.device_escape_path(device_src_path), self.device_escape_path(device_dst_path)))

########NEW FILE########
__FILENAME__ = MultiDragTreeView
import gtk
import gobject
import pango

""" This class is taken (with some edits) from the excellent QuodLibet project:
	code.google.com/p/quodlibet/

	QuodLibet is licensed under the GPL v2 License:
	http://www.gnu.org/licenses/old-licenses/gpl-2.0.html
"""

class MultiDragTreeView(gtk.TreeView):
    """TreeView with multirow drag support:
    * Selections don't change until button-release-event...
    * Unless they're a Shift/Ctrl modification, then they happen immediately
    * Drag icons include 3 rows/2 plus a "and more" count"""

    def __init__(self, *args):
        super(MultiDragTreeView, self).__init__(*args)
        self.connect_object(
            'button-press-event', MultiDragTreeView.__button_press, self)
        self.connect_object(
            'button-release-event', MultiDragTreeView.__button_release, self)
        self.connect_object('drag-begin', MultiDragTreeView.__begin, self)
        self.__pending_event = None

    def __button_press(self, event):
        if event.button == 1: return self.__block_selection(event)

    def __block_selection(self, event):
        x, y = map(int, [event.x, event.y])
        try: path, col, cellx, celly = self.get_path_at_pos(x, y)
        except TypeError: return True
        self.grab_focus()
        selection = self.get_selection()
        if ((selection.path_is_selected(path)
            and not (event.state & (gtk.gdk.CONTROL_MASK|gtk.gdk.SHIFT_MASK)))):
            self.__pending_event = [x, y]
            selection.set_select_function(lambda *args: False)
        elif event.type == gtk.gdk.BUTTON_PRESS:
            self.__pending_event = None
            selection.set_select_function(lambda *args: True)

    def __button_release(self, event):
        if self.__pending_event:
            selection = self.get_selection()
            selection.set_select_function(lambda *args: True)
            oldevent = self.__pending_event
            self.__pending_event = None
            if oldevent != [event.x, event.y]: return True
            x, y = map(int, [event.x, event.y])
            try: path, col, cellx, celly = self.get_path_at_pos(x, y)
            except TypeError: return True
            self.set_cursor(path, col, 0)

    def __begin(self, ctx):
        model, paths = self.get_selection().get_selected_rows()
        MAX = 3
        if paths:
            icons = map(self.create_row_drag_icon, paths[:MAX])
            height = (
                sum(map(lambda s: s.get_size()[1], icons))-2*len(icons))+2
            width = max(map(lambda s: s.get_size()[0], icons))
            final = gtk.gdk.Pixmap(icons[0], width, height)
            gc = gtk.gdk.GC(final)
            gc.copy(self.style.fg_gc[gtk.STATE_NORMAL])
            gc.set_colormap(self.window.get_colormap())
            count_y = 1
            for icon in icons:
                w, h = icon.get_size()
                final.draw_drawable(gc, icon, 1, 1, 1, count_y, w-2, h-2)
                count_y += h - 2
            if len(paths) > MAX:
                count_y -= h - 2
                bgc = gtk.gdk.GC(final)
                bgc.copy(self.style.base_gc[gtk.STATE_NORMAL])
                final.draw_rectangle(bgc, True, 1, count_y, w-2, h-2)
				# WARNING -- modified from original!
				# Not using i18n so taking out the initial underscore for translations ;)
                more = ("and %d more...") % (len(paths) - MAX + 1) # _("and %d more...") % (len(paths) - MAX + 1)
                layout = self.create_pango_layout(more)
                attrs = pango.AttrList()
                attrs.insert(pango.AttrStyle(pango.STYLE_ITALIC, 0, len(more)))
                layout.set_attributes(attrs)
                layout.set_width(pango.SCALE * (w - 2))
                lw, lh = layout.get_pixel_size()
                final.draw_layout(gc, (w-lw)//2, count_y + (h-lh)//2, layout)

            final.draw_rectangle(gc, False, 0, 0, width-1, height-1)
            self.drag_source_set_icon(final.get_colormap(), final)
        else:
            gobject.idle_add(ctx.drag_abort, gtk.get_current_event_time())
            self.drag_source_set_icon_stock(gtk.STOCK_MISSING_IMAGE)


########NEW FILE########
__FILENAME__ = TreeViewFile
import gtk
import gobject
import MultiDragTreeView

""" A sort of TreeView container that serves for showing file listings """
class TreeViewFile:

	def __init__(self, pixbufDir, pixbufFile):
		
		self.pixbufDirectory = pixbufDir
		self.pixbufFile = pixbufFile
		# GOTCHA: Number of columns in the store *MUST* match the number of values
		# added in loadData
		self.tree_store = gtk.TreeStore(gobject.TYPE_BOOLEAN, str, str, str, str, str, str)
		self.tree_view = MultiDragTreeView.MultiDragTreeView(self.tree_store)
		self.tree_view.get_selection().set_mode(gtk.SELECTION_MULTIPLE)
		self.scrolled_window = gtk.ScrolledWindow()
		self.scrolled_window.add_with_viewport(self.tree_view)
		self.scrolled_window.set_policy(gtk.POLICY_AUTOMATIC, gtk.POLICY_AUTOMATIC)
		
		# TYPE
		type_col = gtk.TreeViewColumn('')
		self.tree_view.append_column(type_col)
		
		type_col_renderer_pixbuf = gtk.CellRendererPixbuf()
		type_col.pack_start(type_col_renderer_pixbuf, expand=True)
		# GOTCHA Func must be set AFTER the renderer is packed into the column
		type_col.set_cell_data_func(type_col_renderer_pixbuf, self.render_dir_or_file)

		# NAME
		name_col = gtk.TreeViewColumn('File name')
		self.tree_view.append_column(name_col)
		
		name_col_renderer_text = gtk.CellRendererText()
		name_col.pack_start(name_col_renderer_text, expand=True)
		name_col.add_attribute(name_col_renderer_text, 'text', 1)
		name_col.set_sort_column_id(1)
		self.tree_view.set_search_column(1)
		
		# SIZE
		size_col = gtk.TreeViewColumn('Size')
		self.tree_view.append_column(size_col)
		
		size_col_renderer = gtk.CellRendererText()
		size_col.pack_start(size_col_renderer, expand=True)
		size_col.add_attribute(size_col_renderer, 'text', 2)
		size_col.set_sort_column_id(2)

		# TIMESTAMP
		time_col = gtk.TreeViewColumn('Date modified')
		self.tree_view.append_column(time_col)

		time_col_renderer = gtk.CellRendererText()
		time_col.pack_start(time_col_renderer, expand=True)
		time_col.add_attribute(time_col_renderer, 'text', 3)
		time_col.set_sort_column_id(3)

		# PERMISSIONS
		perm_col = gtk.TreeViewColumn('Permissions')
		self.tree_view.append_column(perm_col)

		perm_col_renderer = gtk.CellRendererText()
		perm_col.pack_start(perm_col_renderer, expand=True)
		perm_col.add_attribute(perm_col_renderer, 'text', 4)
		perm_col.set_sort_column_id(4)

		# OWNER
		own_col = gtk.TreeViewColumn('Owner')
		self.tree_view.append_column(own_col)

		own_col_renderer = gtk.CellRendererText()
		own_col.pack_start(own_col_renderer, expand=True)
		own_col.add_attribute(own_col_renderer, 'text', 5)
		own_col.set_sort_column_id(5)

		# GROUP
		group_col = gtk.TreeViewColumn('Group')
		self.tree_view.append_column(group_col)

		group_col_renderer = gtk.CellRendererText()
		group_col.pack_start(group_col_renderer, expand=True)
		group_col.add_attribute(group_col_renderer, 'text', 6)
		group_col.set_sort_column_id(6)


	def render_dir_or_file(self, tree_view_column, cell, model, iter):
		isDir = model.get_value(iter, 0)
		if isDir:
			pixbuf = self.pixbufDirectory
		else:
			pixbuf = self.pixbufFile

		cell.set_property('pixbuf', pixbuf)


	def get_view(self):
		return self.scrolled_window

	def get_tree(self):
		return self.tree_view


	def load_data(self, data):
		self.tree_store.clear()

		for row in data:
			if row['size'] == 0:
				size = ''
			else:
				size = str(row['size'])

			rowIter = self.tree_store.append(None, [ row['directory'], row['name'], size, row['timestamp'], row['permissions'], row['owner'], row['group'] ])



########NEW FILE########
