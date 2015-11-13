__FILENAME__ = common
# -*- coding: utf-8 -*-
import sublime, sublime_plugin

sp_wp = None
sp_settings = None
sp_started = False

########NEW FILE########
__FILENAME__ = plugin
# -*- coding: utf-8 -*-
import sublime, sublime_plugin
import os, sys, threading, shutil
if sys.version_info[0] == 3:
	from .wordpress_xmlrpc import *
	from .wordpress_xmlrpc.methods.posts import *
	from .wordpress_xmlrpc.methods.taxonomies import *
	from .wordpress_xmlrpc.methods.users import *
	from . import common
else:
	from wordpress_xmlrpc import *
	from wordpress_xmlrpc.methods.posts import *
	from wordpress_xmlrpc.methods.taxonomies import *
	from wordpress_xmlrpc.methods.users import *
	import common

class CreateDefaultWordpressSettingsCommand(sublime_plugin.TextCommand):
	def run(self, edit):
		if os.path.exists(sublime.packages_path() + "/User/Wordpress.sublime-settings"):
			return

		n = sublime.active_window().open_file(sublime.packages_path() + "/User/Wordpress.sublime-settings")
		n.insert(edit, 0, """
{
	"upload_on_save": true, // Unused
	"scratch_directory": "~/.sublime/wordpress",  // Unused
	"sites":
	{
		/*
		"Site Label":
		{
			"host": "website.com",
			"salt": "unused",
			"username": "username",
			"password": "password",
		}
		*/
	}
}
""")

""" Called by Sublime after Sublime has loaded and is ready to load Sublpress """
def plugin_loaded():
	# log commands for debugging
	#sublime.log_commands(True)

	# show console for debugging
	#sublime.active_window().run_command("show_panel", { "panel": "console", "toggle": True })

	if not os.path.exists(sublime.packages_path() + "/User/Wordpress.sublime-settings"):
		sublime.active_window().run_command('create_default_wordpress_settings')

	# initialize some default values
	common.sp_wp = None
	common.sp_settings = sublime.load_settings('Wordpress.sublime-settings')
	common.sp_started = True

	print("Sublpress loaded.")

if not common.sp_started:
	sublime.set_timeout(plugin_loaded, 300)

class WordpressManageSites(sublime_plugin.WindowCommand):
	def is_enabled(self):
		return True

	def run(self, *args, **kwargs):
		if not os.path.exists(sublime.packages_path() + "/User/Wordpress.sublime-settings"):
			sublime.active_window().run_command('create_default_wordpress_settings')

class WordpressConnectCall(threading.Thread):
	""" Used to connect Sublime's Wordpress Connect command to wordpress_xmlrpc via theads """
	def __init__(self, url, username, password):
		# initialize some stuff
		self.url = url
		self.username = username
		self.password = password
		self.result = None    

		# make sure to initialize the thread
		threading.Thread.__init__(self)

	""" Called by the threading module after being started """
	def run(self):
		# make sure we have a valid wordpress client object
		if common.sp_wp == None:
			common.sp_wp = Client(self.url, self.username, self.password)
			self.result = common.sp_wp
			return

		# display an error message
		sublime.error_message('Already connected.')

		# and make sure the result gets set again
		self.result = common.sp_wp

class WordpressApiCall(threading.Thread):
	""" Used to connect Sublime's Wordpress API commands to wordpress_xmlrpc via theads """
	def __init__(self, method):
		# initialize some stuff
		self.method = method
		self.result = None

		# make sure to initialize the thread
		threading.Thread.__init__(self)

	""" Called by the threading module after being started """
	def run(self):
		# make sure we have a valid wordpress client object
		if common.sp_wp != None:
			self.result = common.sp_wp.call(self.method)
			return

		# display an error message
		sublime.error_message('Not connected')

		# make sure we don't execute the callback
		self.result = False
########NEW FILE########
__FILENAME__ = terms
# -*- coding: utf-8 -*-
import sublime, sublime_plugin
import os, sys, threading, zipfile, re, pprint, subprocess
if sys.version_info[0] == 3:
	from .wordpress_xmlrpc import *
	from .wordpress_xmlrpc.methods.posts import *
	from .wordpress_xmlrpc.methods.taxonomies import *
	from .wordpress_xmlrpc.methods.users import *
	from . import *
else:
	from wordpress_xmlrpc import *
	from wordpress_xmlrpc.methods.posts import *
	from wordpress_xmlrpc.methods.taxonomies import *
	from wordpress_xmlrpc.methods.users import *
	import common, plugin, command


class WordpressManageTaxesCommand(sublime_plugin.WindowCommand):
	""" Sublime Command that shows the user a list of WordPress taxonomies, or for a specific post type"""
	def __init__(self, *args, **kwargs):
		super(WordpressManageTaxesCommand, self).__init__(*args, **kwargs)
		self.wc = command.WordpressCommand()

	""" Called to determine if the command should be enabled """
	def is_enabled(self):
		return self.wc.is_enabled()

	""" Called when the command is ran """
	def run(self, *args, **kwargs):  
		# initialize anything we need for this command
		self.setup_command(*args, **kwargs)

		# initiate any threads we have
		self.wc.init_threads(self.thread_callback)

	""" Called right before the rest of the command runs """
	def setup_command(self, *args, **kwargs):
		# create threaded API call because the http connections could take awhile
		thread = plugin.WordpressApiCall(GetTaxonomies())

		# add the thread to the list
		self.wc.add_thread(thread)

	""" Called when a thread is finished executing """
	def thread_callback(self, result, *args, **kwargs):
		self.taxes = result
		#self.options = ['New Taxonomy']
		self.options = []

		for tax in self.taxes:
			self.options.append(tax.name)

		self.wc.show_quick_panel(self.options, self.panel_callback)

	""" Called when the quick panel is closed """
	def panel_callback(self, index):
		# the user cancelled the panel
		if index == -1:
			return 

		#if index == 0:
			#self.window.run_command('wordpress_new_term')
			#return

		# loop through all of the retreived taxonomies
		for tax in self.taxes:

			# check for a matching title for the selected quick panel option
			if tax.name == self.options[index]:
				# show the user actions for this taxonomy
				self.window.run_command('wordpress_manage_terms', { 'taxonomy': tax.name })

class WordpressManageTermsCommand(sublime_plugin.WindowCommand):
	""" Sublime Command that shows the user a list of WordPress terms for a specific taxonomy"""
	def __init__(self, *args, **kwargs):
		super(WordpressManageTermsCommand, self).__init__(*args, **kwargs)
		self.wc = command.WordpressCommand()

	""" Called to determine if the command should be enabled """
	def is_enabled(self):
		return self.wc.is_enabled()

	""" Called when the command is ran """
	def run(self, *args, **kwargs):  
		# initialize anything we need for this command
		self.setup_command(*args, **kwargs)

		# initiate any threads we have
		self.wc.init_threads(self.thread_callback)

	""" Called right before the rest of the command runs """
	def setup_command(self, *args, **kwargs):
		self.taxonomy = kwargs.get('taxonomy', None)

		# create threaded API call because the http connections could take awhile
		thread = plugin.WordpressApiCall(GetTerms(self.taxonomy))

		# add the thread to the list
		self.wc.add_thread(thread)

	""" Called when a thread is finished executing """
	def thread_callback(self, result, *args, **kwargs):
		self.terms = result
		self.options = ['New Term']

		for term in self.terms:
			self.options.append(term.name)

		self.wc.show_quick_panel(self.options, self.panel_callback)

	""" Called when the quick panel is closed """
	def panel_callback(self, index):
		# the user cancelled the panel
		if index == -1:
			return 

		# create new term
		if index == 0:
			self.window.run_command('wordpress_new_term')
			return

		# loop through all terms
		for term in self.terms:
			if term.name == self.options[index]:
				self.window.run_command('wordpress_term_action', {'id': term.id, 'name': term.name, 'taxonomy': self.taxonomy})

class WordpressRenameTermCommand(sublime_plugin.WindowCommand):
	""" Sublime Command that shows allows the user to rename a taxonomy term """
	def __init__(self, *args, **kwargs):
		super(WordpressRenameTermCommand, self).__init__(*args, **kwargs)
		self.wc = command.WordpressCommand()

	""" Called when the input panel has received input """
	def doDone(self, name):
		# save the old name
		self.old_name = self.term.name

		# assign the new name to this term
		self.term.name = name

		# create threaded API call because the http connections could take awhile
		thread = plugin.WordpressApiCall(EditTerm(self.term.id, self.term))

		# add the thread to the list
		self.wc.add_thread(thread)

		# initiate any threads we have
		self.wc.init_threads(self.thread_callback)

	""" Called to determine if the command should be enabled """
	def is_enabled(self):
		return self.wc.is_enabled()

	""" Called when the command is ran """
	def run(self, *args, **kwargs):  
		# initialize anything we need for this command
		self.setup_command(*args, **kwargs)

	""" Called right before the rest of the command runs """
	def setup_command(self, *args, **kwargs):
		# initialize an empty WordPress term
		self.term = WordPressTerm()

		# grab the id, name, and taxonomy from the commands arguments
		self.term.id = kwargs.get('id', None)
		self.term.name = kwargs.get('name', None)
		self.term.taxonomy = kwargs.get('taxonomy', None)

		# make sure we have a valid term
		if self.term.id == None or self.term.name == None:
			sublime.status_message('No term id or name specified.')
		else:
			self.window.show_input_panel('Rename Term', self.term.name, self.doDone, None, None)

	""" Called when the thread is finished executing """
	def thread_callback(self, result, *args, **kwargs):
		# Display a successful status message
		sublime.status_message('Successfully renamed ' + self.old_name + ' to ' + self.term.name + '.')

class WordpressNewTermCommand(sublime_plugin.WindowCommand):
	""" Sublime Command that shows allows the user to create a new taxonomy term """
	def __init__(self, *args, **kwargs):
		super(WordpressNewTermCommand, self).__init__(*args, **kwargs)
		self.wc = command.WordpressCommand()

	""" Called when the input panel has received input """
	def doDone(self, name):
		# initialize an empty WordPress term
		self.term = WordPressTerm()
		self.term.taxonomy = 'category'
		#new_term.parent = parent_cat.id
		self.term.name = name

		# create threaded API call because the http connections could take awhile
		thread = plugin.WordpressApiCall(NewTerm(self.term))

		# add the thread to the list
		self.wc.add_thread(thread)

		# initiate any threads we have
		self.wc.init_threads(self.thread_callback)

	""" Called to determine if the command should be enabled """
	def is_enabled(self):
		return self.wc.is_enabled()

	""" Called when the command is ran """
	def run(self, *args, **kwargs):  
		# initialize anything we need for this command
		self.setup_command(*args, **kwargs)

	""" Called right before the rest of the command runs """
	def setup_command(self, *args, **kwargs):
		self.window.show_input_panel('New Term Name', '', self.doDone, None, None)

	""" Called when the thread is finished executing """
	def thread_callback(self, result, *args, **kwargs):
		self.term.id = result

		# Display a successful status message
		sublime.status_message('Successfully created ' + self.term.name + ' with id of ' + self.term.id + '.')

class WordpressDeleteTermCommand(sublime_plugin.WindowCommand):
	""" Sublime Command that shows allows the user to delete a new taxonomy term """
	def __init__(self, *args, **kwargs):
		super(WordpressDeleteTermCommand, self).__init__(*args, **kwargs)
		self.wc = command.WordpressCommand()

	""" Called to determine if the command should be enabled """
	def is_enabled(self):
		return self.wc.is_enabled()

	""" Called when the command is ran """
	def run(self, *args, **kwargs):  
		# initialize anything we need for this command
		self.setup_command(*args, **kwargs)

		# initiate any threads we have
		self.wc.init_threads(self.thread_callback)

	""" Called right before the rest of the command runs """
	def setup_command(self, *args, **kwargs):
		# create threaded API call because the http connections could take awhile
		thread = plugin.WordpressApiCall(DeleteTerm(kwargs.get('taxonomy', None), kwargs.get('id')))

		# add the thread to the list
		self.wc.add_thread(thread)
		

	""" Called when the thread is finished executing """
	def thread_callback(self, result, *args, **kwargs):
		sublime.status_message(' Successfully deleted term.')

class WordpressTermActionCommand(sublime_plugin.WindowCommand):
	""" Sublime Command that displays a list of actions for a WordPress term """
	def __init__(self, *args, **kwargs):
		super(WordpressTermActionCommand, self).__init__(*args, **kwargs)
		self.wc = command.WordpressCommand()
		
	""" Called to determine if the command should be enabled """
	def is_enabled(self):
		return self.wc.is_enabled()

	""" Called when the command is ran """
	def run(self, *args, **kwargs):  
		# initialize anything we need for this command
		self.setup_command(*args, **kwargs)

	""" Called right before the rest of the command runs """
	def setup_command(self, *args, **kwargs):
		self.taxonomy = kwargs.get('taxonomy', None)
		self.id = kwargs.get('id', None)
		self.name = kwargs.get('name', None)

		self.options = ['Rename Term', 'Delete Term']

		self.wc.show_quick_panel(self.options, self.panel_callback)

	""" Called when the quick panel is closed """
	def panel_callback(self, index):
		# the user cancelled the panel
		if index == -1:
			return 

		# rename term
		if index == 0:
			self.window.run_command('wordpress_rename_term', { 'id': self.id, 'name': self.name, 'taxonomy': self.taxonomy })

		# delete term
		if index == 1:
			self.window.run_command('wordpress_delete_term', { 'id': self.id, 'name': self.name, 'taxonomy': self.taxonomy })

	""" Called when the thread is finished executing """  
	def thread_callback(self, result, *args, **kwargs):
		pass

class WordpressModifyPostTermsCommand(sublime_plugin.WindowCommand):
	""" Sublime Command called when the user selects the option to modify the terms and taxes of a post from the quick panel """
	def __init__(self, *args, **kwargs):
		super(WordpressModifyPostTermsCommand, self).__init__(*args, **kwargs)
		self.wc = command.WordpressCommand()

	""" Called to determine if the command should be enabled """
	def is_enabled(self):
		return self.wc.is_enabled()

	""" Called when the command is ran """
	def run(self, *args, **kwargs):  
		# initialize anything we need for this command
		self.setup_command(*args, **kwargs)

		# initiate any threads we have
		self.wc.init_threads(self.thread_callback)

	""" Called right before the rest of the command runs """
	def setup_command(self, *args, **kwargs):
		# grab the passed in post id
		self.post_id = kwargs.get('id', None)
		self.selected_terms = []

		# create threaded API calls because the http connections could take awhile
		thread = plugin.WordpressApiCall(GetPost(self.post_id))
		thread2 = plugin.WordpressApiCall(GetTaxonomies())
		
		# save a copy of the current view when ran
		self.view = self.window.active_view()
		
		# add the thread to the list
		self.wc.add_thread(thread)
		self.wc.add_thread(thread2)

	""" Called when the thread has returned a list of taxonomies and we need the user to choose one """
	def choose_taxonomy(self, taxes):
		self.taxes = taxes
		self.taxonomy_options = ["Choose a Taxonomy", ]

		for tax in self.taxes:
			self.taxonomy_options.append(tax.name)

		self.wc.show_quick_panel(self.taxonomy_options, self.choose_taxonomy_callback)

	""" Called when the user has chosen a taxonomy """
	def choose_taxonomy_callback(self, index):
		# the user cancelled the panel
		if index == -1:
			return 

		# Do Nothing
		if index == 0:
			self.choose_taxonomy(self.taxes)
			return

		# loop through all of the retreived taxonomies
		for tax in self.taxes:
			# check for a matching title for the selected quick panel option
			if tax.name == self.taxonomy_options[index]:
				self.cur_tax = tax
				thread = plugin.WordpressApiCall(GetTerms(tax.name))
				self.wc.add_thread(thread)
				self.wc.init_threads(self.thread_callback)

	""" Called when the thread has returned a list of terms and we need the user to choose one """
	def choose_term(self, terms):
		self.terms = terms
		self.term_options = [["Save Post", "with the terms marked below"], ]

		for term in self.terms:
			term_description = term.description
			if not term.description:
				term_description = "No Description"

			if term.id in self.selected_terms:
				self.term_options.append([self.wc.prefix.decode('utf8')  + term.name, "ID " + term.id + ": " + term_description])
			else:
				self.term_options.append([term.name, "ID " + term.id + ": " + term_description])

		self.wc.show_quick_panel(self.term_options, self.choose_term_callback)

	""" Called when the user has chosen a term """
	def choose_term_callback(self, index):
		# the user cancelled 0he panel
		if index == -1:
			return 

		# save the new terms
		if index == 0:
			self.update_post()
			return

		# loop through all of the retreived terms
		for term in self.terms:

			# split up the second line by the colon
			parts = self.term_options[index][1].partition(':')

			# check for a matching id for the selected quick panel option
			if term.id == parts[0][3:]:
				if term.id not in self.selected_terms:
					self.selected_terms.append(term.id)
				else:
					self.selected_terms.remove(term.id)
				self.choose_term(self.terms)

	""" Called when the thread is finished executing """
	def thread_callback(self, result, *args, **kwargs):
		if type(result) is WordPressPost:
			self.post = result
			
			for term in self.post.terms:
				self.selected_terms.append(term.id)
		elif type(result) is list:
			if type(result[0]) is WordPressTerm:
				self.choose_term(result)
			if type(result[0]) is WordPressTaxonomy:
				self.choose_taxonomy(result)
		elif type(result) is bool and result == True:
			sublime.status_message('Post updated with new terms and taxes')
				
	""" Called when the user wants to save the post with the new taxes and terms """
	def update_post(self):

		self.post.terms = [term for term in self.terms if term.id in self.selected_terms]
		#pprint.pprint(self.post.terms)

		thread = plugin.WordpressApiCall(EditPost(self.post.id, self.post))
		self.wc.add_thread(thread)
		self.wc.init_threads(self.thread_callback)

########NEW FILE########
__FILENAME__ = wordpress
# -*- coding: utf-8 -*-
import sublime, sublime_plugin
import os, sys, threading, zipfile, re, pprint, subprocess
if sys.version_info[0] == 3:
	from .wordpress_xmlrpc import *
	from .wordpress_xmlrpc.methods.posts import *
	from .wordpress_xmlrpc.methods.taxonomies import *
	from .wordpress_xmlrpc.methods.users import *
	from . import *
else:
	from wordpress_xmlrpc import *
	from wordpress_xmlrpc.methods.posts import *
	from wordpress_xmlrpc.methods.taxonomies import *
	from wordpress_xmlrpc.methods.users import *
	import common, plugin, command

class WordpressInsertCommand(sublime_plugin.TextCommand):
	""" Sublime Text Command to insert content into the active view """
	def __init__(self, *args, **kwargs):
		super(WordpressInsertCommand, self).__init__(*args, **kwargs)
		self.wc = command.WordpressTextCommand()

	""" Called to determine if the command should be enabled """
	def is_enabled(self):
		return self.wc.is_enabled()

	""" Called when the command is ran """
	def run(self, edit, *args, **kwargs):
		# grab the status keys and view data from the passed args
		title = kwargs.get('title', 'Unknown')
		content = kwargs.get('content', 'No Content')
		status = kwargs.get('status', {})
		syntax = kwargs.get('syntax', 'Packages/HTML/HTML.tmLanguage')

		# create a new file
		self.file = sublime.active_window().new_file()

		# set some initial data
		self.file.set_name(title)
		self.file.set_syntax_file(syntax) # HTML syntax
		self.file.set_scratch(True)

		# loop through the and set the status keys
		for k, v in status.items():
			self.file.set_status(k, v)

		# insert the content into the new view
		self.file.insert(edit, 0, content)

class WordpressActionsCommand(sublime_plugin.WindowCommand):
	""" Sublime command to display the initial WordPress control panel """
	def __init__(self, *args, **kwargs):
		super(WordpressActionsCommand, self).__init__(*args, **kwargs)
		self.wc = command.WordpressCommand()

	""" Called to determine if the command should be enabled """
	def is_enabled(self):
		return self.wc.is_enabled()

	""" Called when the command is ran """
	def run(self, *args, **kwargs):
		# initialize anything we need for this command
		self.setup_command(*args, **kwargs)

	""" Called right before the rest of the command runs """
	def setup_command(self, *args, **kwargs):
		self.options = ['Edit Settings', 'Manage all Pages', 'Manage all Posts', 'Manage all Taxonomies', 'Manage a Custom Post Type']
		self.wc.show_quick_panel(self.options, self.panel_callback)

	""" Called when the quick panel has finished """
	def panel_callback(self, index):

		# the user cancelled the panel
		if index == -1:
			return

		# settings
		if index == 0:
			self.window.run_command('wordpress_edit_settings')

		# manage Pages
		if index == 1:
			self.window.run_command('wordpress_manage_posts', {'post_type': 'page'})
			return

		# manage Posts
		if index == 2:
			self.window.run_command('wordpress_manage_posts', {'post_type': 'post'})

		# manage Taxonomies
		if index == 3:
			self.window.run_command('wordpress_manage_taxes')

		# manage a Custom Post Type
		if index == 4:
			self.window.run_command('wordpress_manage_custom_posts')

class WordpressConnectCommand(sublime_plugin.WindowCommand):
	""" Sublime command to display the list of sites we can connect to """
	def __init__(self, *args, **kwargs):
		super(WordpressConnectCommand, self).__init__(*args, **kwargs)
		self.wc = command.WordpressCommand()

	""" Called to determine if the command should be enabled """
	def is_enabled(self):
		if common.sp_wp == None:
			return True

		return False

	""" Called when the command is ran """
	def run(self, *args, **kwargs):
		# initialize anything we need for this command
		self.setup_command(*args, **kwargs)

	""" Called right before the rest of the command runs """
	def setup_command(self, *args, **kwargs):
		self.sites = []
		self.options = []

		# check if we have valid sublpress settings, reload if not
		if common.sp_settings == None:
			common.sp_settings = sublime.load_settings('Wordpress.sublime-settings')

		if not common.sp_settings.has('sites') or len(common.sp_settings.get('sites')) <= 0:
			sublime.error_message('No sites configured.')
			return

		# loop through all the sites
		for name, site in common.sp_settings.get('sites').items():

			# and add them to the quick panel options and our sites container
			self.options.append([name, site['username'] + '@' + site['host']], )
			self.sites.append(site)

		# show the quick panel
		self.wc.show_quick_panel(self.options, self.panel_callback)


	""" Called when the quick panel has finished """
	def panel_callback(self, index):

		# the user cancelled the panel
		if index == -1:
			return
		site = self.sites[index]

		url = 'http://' + site['host'] + '/xmlrpc.php'

		# create threaded API call because the http connections could take awhile
		thread = plugin.WordpressConnectCall(url, site['username'], site['password'])

		# add the thread to the list
		self.wc.add_thread(thread)

		# initiate any threads we have
		self.wc.init_threads(self.thread_callback)

	""" Called when the thread has finished executing """
	def thread_callback(self, result):
		#pprint.pprint(vars(result))
		# display a status message
		sublime.status_message('Connected to ' + common.sp_wp.url + ' successfully.')

		# show the wordpress actions panel
		self.window.run_command('wordpress_actions')

class WordpressDisconnectCommand(sublime_plugin.WindowCommand):
	def is_enabled(self):
		if common.sp_wp == None:
			return False

		return True

	def run(self, *args, **kwargs):
		common.sp_wp = None
		common.sp_settings = sublime.load_settings('Wordpress.sublime-settings')

########NEW FILE########
