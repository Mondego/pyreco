__FILENAME__ = badips
# emacs: -*- mode: python; py-indent-offset: 4; indent-tabs-mode: t -*-
# vi: set ft=python sts=4 ts=4 sw=4 noet :

# This file is part of Fail2Ban.
#
# Fail2Ban is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# Fail2Ban is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with Fail2Ban; if not, write to the Free Software
# Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA  02110-1301, USA.

import sys
if sys.version_info < (2, 7):
	raise ImportError("badips.py action requires Python >= 2.7")
import json
from functools import partial
import threading
import logging
if sys.version_info >= (3, ):
	from urllib.request import Request, urlopen
	from urllib.parse import urlencode
	from urllib.error import HTTPError
else:
	from urllib2 import Request, urlopen, HTTPError
	from urllib import urlencode

from fail2ban.server.actions import ActionBase
from fail2ban.version import version as f2bVersion

class BadIPsAction(ActionBase):
	"""Fail2Ban action which reports bans to badips.com, and also
	blacklist bad IPs listed on badips.com by using another action's
	ban method.

	Parameters
	----------
	jail : Jail
		The jail which the action belongs to.
	name : str
		Name assigned to the action.
	category : str
		Valid badips.com category for reporting failures.
	score : int, optional
		Minimum score for bad IPs. Default 3.
	age : str, optional
		Age of last report for bad IPs, per badips.com syntax.
		Default "24h" (24 hours)
	key : str, optional
		Key issued by badips.com to report bans, for later retrieval
		of personalised content.
	banaction : str, optional
		Name of banaction to use for blacklisting bad IPs. If `None`,
		no blacklist of IPs will take place.
		Default `None`.
	bancategory : str, optional
		Name of category to use for blacklisting, which can differ
		from category used for reporting. e.g. may want to report
		"postfix", but want to use whole "mail" category for blacklist.
		Default `category`.
	bankey : str, optional
		Key issued by badips.com to blacklist IPs reported with the
		associated key.
	updateperiod : int, optional
		Time in seconds between updating bad IPs blacklist.
		Default 900 (15 minutes)

	Raises
	------
	ValueError
		If invalid `category`, `score`, `banaction` or `updateperiod`.
	"""

	_badips = "http://www.badips.com"
	_Request = partial(
		Request, headers={'User-Agent': "Fail2Ban %s" % f2bVersion})

	def __init__(self, jail, name, category, score=3, age="24h", key=None,
		banaction=None, bancategory=None, bankey=None, updateperiod=900):
		super(BadIPsAction, self).__init__(jail, name)

		self.category = category
		self.score = score
		self.age = age
		self.key = key
		self.banaction = banaction
		self.bancategory = bancategory or category
		self.bankey = bankey
		self.updateperiod = updateperiod

		self._bannedips = set()
		# Used later for threading.Timer for updating badips
		self._timer = None

	def getCategories(self, incParents=False):
		"""Get badips.com categories.

		Returns
		-------
		set
			Set of categories.

		Raises
		------
		HTTPError
			Any issues with badips.com request.
		"""
		try:
			response = urlopen(
				self._Request("/".join([self._badips, "get", "categories"])))
		except HTTPError as response:
			messages = json.loads(response.read().decode('utf-8'))
			self._logSys.error(
				"Failed to fetch categories. badips.com response: '%s'",
				messages['err'])
			raise
		else:
			categories = json.loads(response.read().decode('utf-8'))['categories']
			categories_names = set(
				value['Name'] for value in categories)
			if incParents:
				categories_names.update(set(
					value['Parent'] for value in categories
					if "Parent" in value))
			return categories_names

	def getList(self, category, score, age, key=None):
		"""Get badips.com list of bad IPs.

		Parameters
		----------
		category : str
			Valid badips.com category.
		score : int
			Minimum score for bad IPs.
		age : str
			Age of last report for bad IPs, per badips.com syntax.
		key : str, optional
			Key issued by badips.com to fetch IPs reported with the
			associated key.

		Returns
		-------
		set
			Set of bad IPs.

		Raises
		------
		HTTPError
			Any issues with badips.com request.
		"""
		try:
			url = "?".join([
				"/".join([self._badips, "get", "list", category, str(score)]),
				urlencode({'age': age})])
			if key:
				url = "&".join([url, urlencode({"key", key})])
			response = urlopen(self._Request(url))
		except HTTPError as response:
			messages = json.loads(response.read().decode('utf-8'))
			self._logSys.error(
				"Failed to fetch bad IP list. badips.com response: '%s'",
				messages['err'])
			raise
		else:
			return set(response.read().decode('utf-8').split())

	@property
	def category(self):
		"""badips.com category for reporting IPs.
		"""
		return self._category

	@category.setter
	def category(self, category):
		if category not in self.getCategories():
			self._logSys.error("Category name '%s' not valid. "
				"see badips.com for list of valid categories",
				category)
			raise ValueError("Invalid category: %s" % category)
		self._category = category

	@property
	def bancategory(self):
		"""badips.com bancategory for fetching IPs.
		"""
		return self._bancategory

	@bancategory.setter
	def bancategory(self, bancategory):
		if bancategory not in self.getCategories(incParents=True):
			self._logSys.error("Category name '%s' not valid. "
				"see badips.com for list of valid categories",
				bancategory)
			raise ValueError("Invalid bancategory: %s" % bancategory)
		self._bancategory = bancategory

	@property
	def score(self):
		"""badips.com minimum score for fetching IPs.
		"""
		return self._score

	@score.setter
	def score(self, score):
		score = int(score)
		if 0 <= score <= 5:
			self._score = score
		else:
			raise ValueError("Score must be 0-5")

	@property
	def banaction(self):
		"""Jail action to use for banning/unbanning.
		"""
		return self._banaction

	@banaction.setter
	def banaction(self, banaction):
		if banaction is not None and banaction not in self._jail.actions:
			self._logSys.error("Action name '%s' not in jail '%s'",
				banaction, self._jail.name)
			raise ValueError("Invalid banaction")
		self._banaction = banaction

	@property
	def updateperiod(self):
		"""Period in seconds between banned bad IPs will be updated.
		"""
		return self._updateperiod

	@updateperiod.setter
	def updateperiod(self, updateperiod):
		updateperiod = int(updateperiod)
		if updateperiod > 0:
			self._updateperiod = updateperiod
		else:
			raise ValueError("Update period must be integer greater than 0")

	def _banIPs(self, ips):
		for ip in ips:
			try:
				self._jail.actions[self.banaction].ban({
					'ip': ip,
					'failures': 0,
					'matches': "",
					'ipmatches': "",
					'ipjailmatches': "",
				})
			except Exception as e:
				self._logSys.error(
					"Error banning IP %s for jail '%s' with action '%s': %s",
					ip, self._jail.name, self.banaction, e,
					exc_info=self._logSys.getEffectiveLevel()<=logging.DEBUG)
			else:
				self._bannedips.add(ip)
				self._logSys.info(
					"Banned IP %s for jail '%s' with action '%s'",
					ip, self._jail.name, self.banaction)

	def _unbanIPs(self, ips):
		for ip in ips:
			try:
				self._jail.actions[self.banaction].unban({
					'ip': ip,
					'failures': 0,
					'matches': "",
					'ipmatches': "",
					'ipjailmatches': "",
				})
			except Exception as e:
				self._logSys.info(
					"Error unbanning IP %s for jail '%s' with action '%s': %s",
					ip, self._jail.name, self.banaction, e,
					exc_info=self._logSys.getEffectiveLevel()<=logging.DEBUG)
			else:
				self._logSys.info(
					"Unbanned IP %s for jail '%s' with action '%s'",
					ip, self._jail.name, self.banaction)
			finally:
				self._bannedips.remove(ip)

	def start(self):
		"""If `banaction` set, blacklists bad IPs.
		"""
		if self.banaction is not None:
			self.update()

	def update(self):
		"""If `banaction` set, updates blacklisted IPs.

		Queries badips.com for list of bad IPs, removing IPs from the
		blacklist if no longer present, and adds new bad IPs to the
		blacklist.
		"""
		if self.banaction is not None:
			if self._timer:
				self._timer.cancel()
				self._timer = None

			try:
				ips = self.getList(
					self.bancategory, self.score, self.age, self.bankey)
				# Remove old IPs no longer listed
				self._unbanIPs(self._bannedips - ips)
				# Add new IPs which are now listed
				self._banIPs(ips - self._bannedips)

				self._logSys.info(
					"Updated IPs for jail '%s'. Update again in %i seconds",
					self._jail.name, self.updateperiod)
			finally:
				self._timer = threading.Timer(self.updateperiod, self.update)
				self._timer.start()

	def stop(self):
		"""If `banaction` set, clears blacklisted IPs.
		"""
		if self.banaction is not None:
			if self._timer:
				self._timer.cancel()
				self._timer = None
			self._unbanIPs(self._bannedips.copy())

	def ban(self, aInfo):
		"""Reports banned IP to badips.com.

		Parameters
		----------
		aInfo : dict
			Dictionary which includes information in relation to
			the ban.

		Raises
		------
		HTTPError
			Any issues with badips.com request.
		"""
		try:
			url = "/".join([self._badips, "add", self.category, aInfo['ip']])
			if self.key:
				url = "?".join([url, urlencode({"key", self.key})])
			response = urlopen(self._Request(url))
		except HTTPError as response:
			messages = json.loads(response.read().decode('utf-8'))
			self._logSys.error(
				"Response from badips.com report: '%s'",
				messages['err'])
			raise
		else:
			messages = json.loads(response.read().decode('utf-8'))
			self._logSys.info(
				"Response from badips.com report: '%s'",
				messages['suc'])

Action = BadIPsAction

########NEW FILE########
__FILENAME__ = smtp
# emacs: -*- mode: python; py-indent-offset: 4; indent-tabs-mode: t -*-
# vi: set ft=python sts=4 ts=4 sw=4 noet :

# This file is part of Fail2Ban.
#
# Fail2Ban is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# Fail2Ban is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with Fail2Ban; if not, write to the Free Software
# Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA  02110-1301, USA.

import socket
import smtplib
from email.mime.text import MIMEText
from email.utils import formatdate, formataddr

from fail2ban.server.actions import ActionBase, CallingMap

messages = {}
messages['start'] = \
"""Hi,

The jail %(jailname)s has been started successfully.

Regards,
Fail2Ban"""

messages['stop'] = \
"""Hi,

The jail %(jailname)s has been stopped.

Regards,
Fail2Ban"""

messages['ban'] = {}
messages['ban']['head'] = \
"""Hi,

The IP %(ip)s has just been banned for %(bantime)s seconds
by Fail2Ban after %(failures)i attempts against %(jailname)s.
"""
messages['ban']['tail'] = \
"""
Regards,
Fail2Ban"""
messages['ban']['matches'] = \
"""
Matches for this ban:
%(matches)s
"""
messages['ban']['ipmatches'] = \
"""
Matches for %(ip)s:
%(ipmatches)s
"""
messages['ban']['ipjailmatches'] = \
"""
Matches for %(ip)s for jail %(jailname)s:
%(ipjailmatches)s
"""

class SMTPAction(ActionBase):
	"""Fail2Ban action which sends emails to inform on jail starting,
	stopping and bans.
	"""

	def __init__(
		self, jail, name, host="localhost", user=None, password=None,
		sendername="Fail2Ban", sender="fail2ban", dest="root", matches=None):
		"""Initialise action.

		Parameters
		----------
		jail : Jail
			The jail which the action belongs to.
		name : str
			Named assigned to the action.
		host : str, optional
			SMTP host, of host:port format. Default host "localhost" and
			port "25"
		user : str, optional
			Username used for authentication with SMTP server.
		password : str, optional
			Password used for authentication with SMTP server.
		sendername : str, optional
			Name to use for from address in email. Default "Fail2Ban".
		sender : str, optional
			Email address to use for from address in email.
			Default "fail2ban".
		dest : str, optional
			Email addresses of intended recipient(s) in comma space ", "
			delimited format. Default "root".
		matches : str, optional
			Type of matches to be included from ban in email. Can be one
			of "matches", "ipmatches" or "ipjailmatches". Default None
			(see man jail.conf.5).
		"""

		super(SMTPAction, self).__init__(jail, name)

		self.host = host
		#TODO: self.ssl = ssl

		self.user = user
		self.password =password

		self.fromname = sendername
		self.fromaddr = sender
		self.toaddr = dest

		self.matches = matches

		self.message_values = CallingMap(
			jailname = self._jail.name,
			hostname = socket.gethostname,
			bantime = self._jail.actions.getBanTime,
			)

	def _sendMessage(self, subject, text):
		"""Sends message based on arguments and instance's properties.

		Parameters
		----------
		subject : str
			Subject of the email.
		text : str
			Body of the email.

		Raises
		------
		SMTPConnectionError
			Error on connecting to host.
		SMTPAuthenticationError
			Error authenticating with SMTP server.
		SMTPException
			See Python `smtplib` for full list of other possible
			exceptions.
		"""
		msg = MIMEText(text)
		msg['Subject'] = subject
		msg['From'] = formataddr((self.fromname, self.fromaddr))
		msg['To'] = self.toaddr
		msg['Date'] = formatdate()

		smtp = smtplib.SMTP()
		try:
			self._logSys.debug("Connected to SMTP '%s', response: %i: %s",
				self.host, *smtp.connect(self.host))
			if self.user and self.password:
				smtp.login(self.user, self.password)
			failed_recipients = smtp.sendmail(
				self.fromaddr, self.toaddr.split(", "), msg.as_string())
		except smtplib.SMTPConnectError:
			self._logSys.error("Error connecting to host '%s'", self.host)
			raise
		except smtplib.SMTPAuthenticationError:
			self._logSys.error(
				"Failed to authenticate with host '%s' user '%s'",
				self.host, self.user)
			raise
		except smtplib.SMTPException:
			self._logSys.error(
				"Error sending mail to host '%s' from '%s' to '%s'",
				self.host, self.fromaddr, self.toaddr)
			raise
		else:
			if failed_recipients:
				self._logSys.warning(
					"Email to '%s' failed to following recipients: %r",
					self.toaddr, failed_recipients)
			self._logSys.debug("Email '%s' successfully sent", subject)
		finally:
			try:
				self._logSys.debug("Disconnected from '%s', response %i: %s",
					self.host, *smtp.quit())
			except smtplib.SMTPServerDisconnected:
				pass # Not connected

	def start(self):
		"""Sends email to recipients informing that the jail has started.
		"""
		self._sendMessage(
			"[Fail2Ban] %(jailname)s: started on %(hostname)s" %
				self.message_values,
			messages['start'] % self.message_values)

	def stop(self):
		"""Sends email to recipients informing that the jail has stopped.
		"""
		self._sendMessage(
			"[Fail2Ban] %(jailname)s: stopped on %(hostname)s" %
				self.message_values,
			messages['stop'] % self.message_values)

	def ban(self, aInfo):
		"""Sends email to recipients informing that ban has occurred.

		Parameters
		----------
		aInfo : dict
			Dictionary which includes information in relation to
			the ban.
		"""
		aInfo.update(self.message_values)
		message = "".join([
			messages['ban']['head'],
			messages['ban'].get(self.matches, ""),
			messages['ban']['tail']
			])
		self._sendMessage(
			"[Fail2Ban] %(jailname)s: banned %(ip)s from %(hostname)s" %
				aInfo,
			message % aInfo)

Action = SMTPAction

########NEW FILE########
__FILENAME__ = conf
# -*- coding: utf-8 -*-

import sys
import os

sys.path.insert(0, ".")
sys.path.insert(0, "..")

# If extensions (or modules to document with autodoc) are in another directory,
# add these directories to sys.path here. If the directory is relative to the
# documentation root, use os.path.abspath to make it absolute, like shown here.
#sys.path.insert(0, os.path.abspath('.'))

# -- General configuration ------------------------------------------------

# If your documentation needs a minimal Sphinx version, state it here.
#needs_sphinx = '1.0'

# Add any Sphinx extension module names here, as strings. They can be
# extensions coming with Sphinx (named 'sphinx.ext.*') or your custom
# ones.
extensions = [
    'sphinx.ext.autodoc',
    'sphinx.ext.autosummary',
    'numpydoc',
]

# Add any paths that contain templates here, relative to this directory.
templates_path = ['templates']

# The suffix of source filenames.
source_suffix = '.rst'

# The encoding of source files.
#source_encoding = 'utf-8-sig'

# The master toctree document.
master_doc = 'index'

# General information about the project.
project = u'Fail2Ban'
copyright = u'2014'

# The version info for the project you're documenting, acts as replacement for
# |version| and |release|, also used in various other places throughout the
# built documents.
#

from fail2ban.version import version as fail2ban_version
from distutils.version import LooseVersion

fail2ban_loose_version = LooseVersion(fail2ban_version)

# The short X.Y version.
version = ".".join(str(_) for _ in fail2ban_loose_version.version[:2])
# The full version, including alpha/beta/rc tags.
release = fail2ban_version

# The language for content autogenerated by Sphinx. Refer to documentation
# for a list of supported languages.
#language = None

# There are two options for replacing |today|: either, you set today to some
# non-false value, then it is used:
#today = ''
# Else, today_fmt is used as the format for a strftime call.
#today_fmt = '%B %d, %Y'

# List of patterns, relative to source directory, that match files and
# directories to ignore when looking for source files.
exclude_patterns = ['build']

# The reST default role (used for this markup: `text`) to use for all
# documents.
#default_role = None

# If true, '()' will be appended to :func: etc. cross-reference text.
#add_function_parentheses = True

# If true, the current module name will be prepended to all description
# unit titles (such as .. function::).
#add_module_names = True

# If true, sectionauthor and moduleauthor directives will be shown in the
# output. They are ignored by default.
#show_authors = False

# The name of the Pygments (syntax highlighting) style to use.
pygments_style = 'sphinx'

# A list of ignored prefixes for module index sorting.
#modindex_common_prefix = []

# If true, keep warnings as "system message" paragraphs in the built documents.
#keep_warnings = False


# -- Options for HTML output ----------------------------------------------

# The theme to use for HTML and HTML Help pages.  See the documentation for
# a list of builtin themes.
html_theme = 'default'

# Theme options are theme-specific and customize the look and feel of a theme
# further.  For a list of options available for each theme, see the
# documentation.
#html_theme_options = {}

# Add any paths that contain custom themes here, relative to this directory.
#html_theme_path = []

# The name for this set of Sphinx documents.  If None, it defaults to
# "<project> v<release> documentation".
#html_title = None

# A shorter title for the navigation bar.  Default is the same as html_title.
#html_short_title = None

# The name of an image file (relative to this directory) to place at the top
# of the sidebar.
#html_logo = None

# The name of an image file (within the static path) to use as favicon of the
# docs.  This file should be a Windows icon file (.ico) being 16x16 or 32x32
# pixels large.
#html_favicon = None

# Add any paths that contain custom static files (such as style sheets) here,
# relative to this directory. They are copied after the builtin static files,
# so a file named "default.css" will overwrite the builtin "default.css".
html_static_path = ['static']

# Add any extra paths that contain custom files (such as robots.txt or
# .htaccess) here, relative to this directory. These files are copied
# directly to the root of the documentation.
#html_extra_path = []

# If not '', a 'Last updated on:' timestamp is inserted at every page bottom,
# using the given strftime format.
#html_last_updated_fmt = '%b %d, %Y'

# If true, SmartyPants will be used to convert quotes and dashes to
# typographically correct entities.
#html_use_smartypants = True

# Custom sidebar templates, maps document names to template names.
#html_sidebars = {}

# Additional templates that should be rendered to pages, maps page names to
# template names.
#html_additional_pages = {}

# If false, no module index is generated.
#html_domain_indices = True

# If false, no index is generated.
#html_use_index = True

# If true, the index is split into individual pages for each letter.
#html_split_index = False

# If true, links to the reST sources are added to the pages.
#html_show_sourcelink = True

# If true, "Created using Sphinx" is shown in the HTML footer. Default is True.
#html_show_sphinx = True

# If true, "(C) Copyright ..." is shown in the HTML footer. Default is True.
#html_show_copyright = True

# If true, an OpenSearch description file will be output, and all pages will
# contain a <link> tag referring to it.  The value of this option must be the
# base URL from which the finished HTML is served.
#html_use_opensearch = ''

# This is the file name suffix for HTML files (e.g. ".xhtml").
#html_file_suffix = None

# Output file base name for HTML help builder.
htmlhelp_basename = 'Fail2Bandoc'


# -- Options for LaTeX output ---------------------------------------------

latex_elements = {
# The paper size ('letterpaper' or 'a4paper').
#'papersize': 'letterpaper',

# The font size ('10pt', '11pt' or '12pt').
#'pointsize': '10pt',

# Additional stuff for the LaTeX preamble.
#'preamble': '',
}

# Grouping the document tree into LaTeX files. List of tuples
# (source start file, target name, title,
#  author, documentclass [howto, manual, or own class]).
latex_documents = [
  ('index', 'Fail2Ban.tex', u'Fail2Ban Developers\' Documentation',
   u'', 'manual'),
]

# The name of an image file (relative to this directory) to place at the top of
# the title page.
#latex_logo = None

# For "manual" documents, if this is true, then toplevel headings are parts,
# not chapters.
#latex_use_parts = False

# If true, show page references after internal links.
#latex_show_pagerefs = False

# If true, show URL addresses after external links.
#latex_show_urls = False

# Documents to append as an appendix to all manuals.
#latex_appendices = []

# If false, no module index is generated.
#latex_domain_indices = True


# -- Options for manual page output ---------------------------------------

# One entry per manual page. List of tuples
# (source start file, name, description, authors, manual section).
man_pages = [
    ('index', 'fail2ban', u'Fail2Ban Developers\' Documentation',
     [u''], 1)
]

# If true, show URL addresses after external links.
#man_show_urls = False


# -- Options for Texinfo output -------------------------------------------

# Grouping the document tree into Texinfo files. List of tuples
# (source start file, target name, title, author,
#  dir menu entry, description, category)
texinfo_documents = [
  ('index', 'Fail2Ban', u'Fail2Ban Developers\' Documentation',
   u'', 'Fail2Ban', 'One line description of project.',
   'Miscellaneous'),
]

# Documents to append as an appendix to all manuals.
#texinfo_appendices = []

# If false, no module index is generated.
#texinfo_domain_indices = True

# How to display URL addresses: 'footnote', 'no', or 'inline'.
#texinfo_show_urls = 'footnote'

# If true, do not generate a @detailmenu in the "Top" node's menu.
#texinfo_no_detailmenu = False
autodoc_default_flags = ['members', 'inherited-members', 'undoc-members', 'show-inheritance']

########NEW FILE########
__FILENAME__ = actionreader
# emacs: -*- mode: python; py-indent-offset: 4; indent-tabs-mode: t -*-
# vi: set ft=python sts=4 ts=4 sw=4 noet :

# This file is part of Fail2Ban.
#
# Fail2Ban is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# Fail2Ban is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with Fail2Ban; if not, write to the Free Software
# Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA  02110-1301, USA.

# Author: Cyril Jaquier
# 

__author__ = "Cyril Jaquier"
__copyright__ = "Copyright (c) 2004 Cyril Jaquier"
__license__ = "GPL"

import logging, os

from .configreader import ConfigReader, DefinitionInitConfigReader

# Gets the instance of the logger.
logSys = logging.getLogger(__name__)

class ActionReader(DefinitionInitConfigReader):

	_configOpts = [
		["string", "actionstart", None],
		["string", "actionstop", None],
		["string", "actioncheck", None],
		["string", "actionban", None],
		["string", "actionunban", None],
	]

	def __init__(self, file_, jailName, initOpts, **kwargs):
		self._name = initOpts.get("actname", file_)
		DefinitionInitConfigReader.__init__(
			self, file_, jailName, initOpts, **kwargs)

	def setName(self, name):
		self._name = name

	def getName(self):
		return self._name

	def read(self):
		return ConfigReader.read(self, os.path.join("action.d", self._file))

	def convert(self):
		head = ["set", self._jailName]
		stream = list()
		stream.append(head + ["addaction", self._name])
		head.extend(["action", self._name])
		for opt in self._opts:
			if opt == "actionstart":
				stream.append(head + ["actionstart", self._opts[opt]])
			elif opt == "actionstop":
				stream.append(head + ["actionstop", self._opts[opt]])
			elif opt == "actioncheck":
				stream.append(head + ["actioncheck", self._opts[opt]])
			elif opt == "actionban":
				stream.append(head + ["actionban", self._opts[opt]])
			elif opt == "actionunban":
				stream.append(head + ["actionunban", self._opts[opt]])
		if self._initOpts:
			for p in self._initOpts:
				stream.append(head + [p, self._initOpts[p]])

		return stream

########NEW FILE########
__FILENAME__ = beautifier
# emacs: -*- mode: python; py-indent-offset: 4; indent-tabs-mode: t -*-
# vi: set ft=python sts=4 ts=4 sw=4 noet :

# This file is part of Fail2Ban.
#
# Fail2Ban is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# Fail2Ban is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with Fail2Ban; if not, write to the Free Software
# Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA  02110-1301, USA.

__author__ = "Cyril Jaquier, Yaroslav Halchenko"
__copyright__ = "Copyright (c) 2004 Cyril Jaquier, 2013- Yaroslav Halchenko"
__license__ = "GPL"

import logging

from ..exceptions import UnknownJailException, DuplicateJailException

# Gets the instance of the logger.
logSys = logging.getLogger(__name__)

##
# Beautify the output of the client.
#
# Fail2ban server only return unformatted return codes which need to be
# converted into user readable messages.

class Beautifier:
	
	def __init__(self, cmd = None):
		self.__inputCmd = cmd

	def setInputCmd(self, cmd):
		self.__inputCmd = cmd
		
	def getInputCmd(self):
		return self.__inputCmd
		
	def beautify(self, response):
		logSys.debug("Beautify " + `response` + " with " + `self.__inputCmd`)
		inC = self.__inputCmd
		msg = response
		try:
			if inC[0] == "ping":
				msg = "Server replied: " + response
			elif inC[0] == "start":
				msg = "Jail started"
			elif inC[0] == "stop":
				if len(inC) == 1:
					if response is None:
						msg = "Shutdown successful"
				else:
					if response is None:
						msg = "Jail stopped"
			elif inC[0] == "add":
				msg = "Added jail " + response
			elif inC[0] == "flushlogs":
				msg = "logs: " + response
			elif inC[0:1] == ['status']:
				if len(inC) > 1:
					# Display information
					msg = ["Status for the jail: %s" % inC[1]]
					for n, res1 in enumerate(response):
						prefix1 = "`-" if n == len(response) - 1 else "|-"
						msg.append("%s %s" % (prefix1, res1[0]))
						prefix1 = "   " if n == len(response) - 1 else "|  "
						for m, res2 in enumerate(res1[1]):
							prefix2 = prefix1 + ("`-" if m == len(res1[1]) - 1 else "|-")
							val = " ".join(res2[1]) if isinstance(res2[1], list) else res2[1]
							msg.append("%s %s:\t%s" % (prefix2, res2[0], val))
				else:
					msg = ["Status"]
					for n, res1 in enumerate(response):
						prefix1 = "`-" if n == len(response) - 1 else "|-"
						val = " ".join(res1[1]) if isinstance(res1[1], list) else res1[1]
						msg.append("%s %s:\t%s" % (prefix1, res1[0], val))
				msg = "\n".join(msg)
			elif inC[1] == "logtarget":
				msg = "Current logging target is:\n"
				msg = msg + "`- " + response
			elif inC[1:2] == ['loglevel']:
				msg = "Current logging level is "
				if response == 1:
					msg = msg + "ERROR"
				elif response == 2:
					msg = msg + "WARN"
				elif response == 3:
					msg = msg + "INFO"
				elif response == 4:
					msg = msg + "DEBUG"
				else:
					msg = msg + `response`
			elif inC[1] == "dbfile":
				if response is None:
					msg = "Database currently disabled"
				else:
					msg = "Current database file is:\n"
					msg = msg + "`- " + response
			elif inC[1] == "dbpurgeage":
				if response is None:
					msg = "Database currently disabled"
				else:
					msg = "Current database purge age is:\n"
					msg = msg + "`- %iseconds" % response
			elif inC[2] in ("logpath", "addlogpath", "dellogpath"):
				if len(response) == 0:
					msg = "No file is currently monitored"
				else:
					msg = "Current monitored log file(s):\n"
					for path in response[:-1]:
						msg = msg + "|- " + path + "\n"
					msg = msg + "`- " + response[len(response)-1]
			elif inC[2] == "logencoding":
				msg = "Current log encoding is set to:\n"
				msg = msg + response
			elif inC[2] in ("journalmatch", "addjournalmatch", "deljournalmatch"):
				if len(response) == 0:
					msg = "No journal match filter set"
				else:
					msg = "Current match filter:\n"
					msg += ' + '.join(" ".join(res) for res in response)
			elif inC[2] == "datepattern":
				msg = "Current date pattern set to: "
				if response is None:
					msg = msg + "Not set/required"
				elif response[0] is None:
					msg = msg + "%s" % response[1]
				else:
					msg = msg + "%s (%s)" % response
			elif inC[2] in ("ignoreip", "addignoreip", "delignoreip"):
				if len(response) == 0:
					msg = "No IP address/network is ignored"
				else:
					msg = "These IP addresses/networks are ignored:\n"
					for ip in response[:-1]:
						msg = msg + "|- " + ip + "\n"
					msg = msg + "`- " + response[len(response)-1]
			elif inC[2] in ("failregex", "addfailregex", "delfailregex",
							"ignoreregex", "addignoreregex", "delignoreregex"):
				if len(response) == 0:
					msg = "No regular expression is defined"
				else:
					msg = "The following regular expression are defined:\n"
					c = 0
					for ip in response[:-1]:
						msg = msg + "|- [" + str(c) + "]: " + ip + "\n"
						c += 1
					msg = msg + "`- [" + str(c) + "]: " + response[len(response)-1]
			elif inC[2] == "actions":
				if len(response) == 0:
					msg = "No actions for jail %s" % inC[1]
				else:
					msg = "The jail %s has the following actions:\n" % inC[1]
					msg += ", ".join(response)
			elif inC[2] == "actionproperties":
				if len(response) == 0:
					msg = "No properties for jail %s action %s" % (
						inC[1], inC[3])
				else:
					msg = "The jail %s action %s has the following " \
						"properties:\n" % (inC[1], inC[3])
					msg += ", ".join(response)
			elif inC[2] == "actionmethods":
				if len(response) == 0:
					msg = "No methods for jail %s action %s" % (
						inC[1], inC[3])
				else:
					msg = "The jail %s action %s has the following " \
						"methods:\n" % (inC[1], inC[3])
					msg += ", ".join(response)
		except Exception:
			logSys.warning("Beautifier error. Please report the error")
			logSys.error("Beautify " + `response` + " with " + `self.__inputCmd` +
						 " failed")
			msg = msg + `response`
		return msg

	def beautifyError(self, response):
		logSys.debug("Beautify (error) " + `response` + " with " + `self.__inputCmd`)
		msg = response
		if isinstance(response, UnknownJailException):
			msg = "Sorry but the jail '" + response.args[0] + "' does not exist"
		elif isinstance(response, IndexError):
			msg = "Sorry but the command is invalid"
		elif isinstance(response, DuplicateJailException):
			msg = "The jail '" + response.args[0] + "' already exists"
		return msg

########NEW FILE########
__FILENAME__ = configparserinc
# emacs: -*- mode: python; py-indent-offset: 4; indent-tabs-mode: t -*-
# vi: set ft=python sts=4 ts=4 sw=4 noet :

# This file is part of Fail2Ban.
#
# Fail2Ban is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# Fail2Ban is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with Fail2Ban; if not, write to the Free Software
# Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA  02110-1301, USA.

# Author: Yaroslav Halchenko
# Modified: Cyril Jaquier

__author__ = 'Yaroslav Halhenko'
__copyright__ = 'Copyright (c) 2007 Yaroslav Halchenko'
__license__ = 'GPL'

import logging, os, sys

if sys.version_info >= (3,2): # pragma: no cover

	# SafeConfigParser deprecated from Python 3.2 (renamed to ConfigParser)
	from configparser import ConfigParser as SafeConfigParser, \
		BasicInterpolation

	# And interpolation of __name__ was simply removed, thus we need to
	# decorate default interpolator to handle it
	class BasicInterpolationWithName(BasicInterpolation):
		"""Decorator to bring __name__ interpolation back.

		Original handling of __name__ was removed because of
		functional deficiencies: http://bugs.python.org/issue10489

		commit v3.2a4-105-g61f2761
		Author: Lukasz Langa <lukasz@langa.pl>
		Date:	Sun Nov 21 13:41:35 2010 +0000

		Issue #10489: removed broken `__name__` support from configparser

		But should be fine to reincarnate for our use case
		"""
		def _interpolate_some(self, parser, option, accum, rest, section, map,
							  depth):
			if section and not (__name__ in map):
				map = map.copy()		  # just to be safe
				map['__name__'] = section
			return super(BasicInterpolationWithName, self)._interpolate_some(
				parser, option, accum, rest, section, map, depth)

else: # pragma: no cover
	from ConfigParser import SafeConfigParser

# Gets the instance of the logger.
logSys = logging.getLogger(__name__)

__all__ = ['SafeConfigParserWithIncludes']

class SafeConfigParserWithIncludes(SafeConfigParser):
	"""
	Class adds functionality to SafeConfigParser to handle included
	other configuration files (or may be urls, whatever in the future)

	File should have section [includes] and only 2 options implemented
	are 'files_before' and 'files_after' where files are listed 1 per
	line.

	Example:

[INCLUDES]
before = 1.conf
         3.conf

after = 1.conf

	It is a simple implementation, so just basic care is taken about
	recursion. Includes preserve right order, ie new files are
	inserted to the list of read configs before original, and their
	includes correspondingly so the list should follow the leaves of
	the tree.

	I wasn't sure what would be the right way to implement generic (aka c++
	template) so we could base at any *configparser class... so I will
	leave it for the future

	"""

	SECTION_NAME = "INCLUDES"

	if sys.version_info >= (3,2):
		# overload constructor only for fancy new Python3's
		def __init__(self, *args, **kwargs):
			kwargs = kwargs.copy()
			kwargs['interpolation'] = BasicInterpolationWithName()
			kwargs['inline_comment_prefixes'] = ";"
			super(SafeConfigParserWithIncludes, self).__init__(
				*args, **kwargs)

	#@staticmethod
	def getIncludes(resource, seen = []):
		"""
		Given 1 config resource returns list of included files
		(recursively) with the original one as well
		Simple loops are taken care about
		"""
		
		# Use a short class name ;)
		SCPWI = SafeConfigParserWithIncludes
		
		parser = SafeConfigParser()
		try:
			if sys.version_info >= (3,2): # pragma: no cover
				parser.read(resource, encoding='utf-8')
			else:
				parser.read(resource)
		except UnicodeDecodeError, e:
			logSys.error("Error decoding config file '%s': %s" % (resource, e))
			return []
		
		resourceDir = os.path.dirname(resource)

		newFiles = [ ('before', []), ('after', []) ]
		if SCPWI.SECTION_NAME in parser.sections():
			for option_name, option_list in newFiles:
				if option_name in parser.options(SCPWI.SECTION_NAME):
					newResources = parser.get(SCPWI.SECTION_NAME, option_name)
					for newResource in newResources.split('\n'):
						if os.path.isabs(newResource):
							r = newResource
						else:
							r = os.path.join(resourceDir, newResource)
						if r in seen:
							continue
						s = seen + [resource]
						option_list += SCPWI.getIncludes(r, s)
		# combine lists
		return newFiles[0][1] + [resource] + newFiles[1][1]
		#print "Includes list for " + resource + " is " + `resources`
	getIncludes = staticmethod(getIncludes)


	def read(self, filenames):
		fileNamesFull = []
		if not isinstance(filenames, list):
			filenames = [ filenames ]
		for filename in filenames:
			fileNamesFull += SafeConfigParserWithIncludes.getIncludes(filename)
		logSys.debug("Reading files: %s" % fileNamesFull)
		if sys.version_info >= (3,2): # pragma: no cover
			return SafeConfigParser.read(self, fileNamesFull, encoding='utf-8')
		else:
			return SafeConfigParser.read(self, fileNamesFull)


########NEW FILE########
__FILENAME__ = configreader
# emacs: -*- mode: python; py-indent-offset: 4; indent-tabs-mode: t -*-
# vi: set ft=python sts=4 ts=4 sw=4 noet :

# This file is part of Fail2Ban.
#
# Fail2Ban is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# Fail2Ban is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with Fail2Ban; if not, write to the Free Software
# Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA  02110-1301, USA.

# Author: Cyril Jaquier
# Modified by: Yaroslav Halchenko (SafeConfigParserWithIncludes)

__author__ = "Cyril Jaquier"
__copyright__ = "Copyright (c) 2004 Cyril Jaquier"
__license__ = "GPL"

import glob, logging, os
from ConfigParser import NoOptionError, NoSectionError

from .configparserinc import SafeConfigParserWithIncludes

# Gets the instance of the logger.
logSys = logging.getLogger(__name__)

class ConfigReader(SafeConfigParserWithIncludes):

	DEFAULT_BASEDIR = '/etc/fail2ban'
	
	def __init__(self, basedir=None):
		SafeConfigParserWithIncludes.__init__(self)
		self.setBaseDir(basedir)
		self.__opts = None
	
	def setBaseDir(self, basedir):
		if basedir is None:
			basedir = ConfigReader.DEFAULT_BASEDIR	# stock system location
		self._basedir = basedir.rstrip('/')
	
	def getBaseDir(self):
		return self._basedir
	
	def read(self, filename):
		if not os.path.exists(self._basedir):
			raise ValueError("Base configuration directory %s does not exist "
							  % self._basedir)
		basename = os.path.join(self._basedir, filename)
		logSys.info("Reading configs for %s under %s "  % (basename, self._basedir))
		config_files = [ basename + ".conf" ]

		# possible further customizations under a .conf.d directory
		config_dir = basename + '.d'
		config_files += sorted(glob.glob('%s/*.conf' % config_dir))

		config_files.append(basename + ".local")
	
		config_files += sorted(glob.glob('%s/*.local' % config_dir))

		# choose only existing ones
		config_files = filter(os.path.exists, config_files)

		if len(config_files):
			# at least one config exists and accessible
			logSys.debug("Reading config files: " + ', '.join(config_files))
			config_files_read = SafeConfigParserWithIncludes.read(self, config_files)
			missed = [ cf for cf in config_files if cf not in config_files_read ]
			if missed:
				logSys.error("Could not read config files: " + ', '.join(missed))
			if config_files_read:
				return True
			logSys.error("Found no accessible config files for %r under %s" %
						 ( filename, self.getBaseDir() ))
			return False
		else:
			logSys.error("Found no accessible config files for %r " % filename
						 + (["under %s" % self.getBaseDir(),
							 "among existing ones: " + ', '.join(config_files)][bool(len(config_files))]))

			return False

	##
	# Read the options.
	#
	# Read the given option in the configuration file. Default values
	# are used...
	# Each optionValues entry is composed of an array with:
	# 0 -> the type of the option
	# 1 -> the name of the option
	# 2 -> the default value for the option
	
	def getOptions(self, sec, options, pOptions = None):
		values = dict()
		for option in options:
			try:
				if option[0] == "bool":
					v = self.getboolean(sec, option[1])
				elif option[0] == "int":
					v = self.getint(sec, option[1])
				else:
					v = self.get(sec, option[1])
				if not pOptions is None and option[1] in pOptions:
					continue
				values[option[1]] = v
			except NoSectionError, e:
				# No "Definition" section or wrong basedir
				logSys.error(e)
				values[option[1]] = option[2]
				# TODO: validate error handling here.
			except NoOptionError:
				if not option[2] is None:
					logSys.warning("'%s' not defined in '%s'. Using default one: %r"
								% (option[1], sec, option[2]))
					values[option[1]] = option[2]
				else:
					logSys.debug(
						"Non essential option '%s' not defined in '%s'.",
						option[1], sec)
			except ValueError:
				logSys.warning("Wrong value for '" + option[1] + "' in '" + sec +
							"'. Using default one: '" + `option[2]` + "'")
				values[option[1]] = option[2]
		return values

class DefinitionInitConfigReader(ConfigReader):
	"""Config reader for files with options grouped in [Definition] and
       [Init] sections.

       Is a base class for readers of filters and actions, where definitions
       in jails might provide custom values for options defined in [Init]
       section.
       """

	_configOpts = []
	
	def __init__(self, file_, jailName, initOpts, **kwargs):
		ConfigReader.__init__(self, **kwargs)
		self.setFile(file_)
		self.setJailName(jailName)
		self._initOpts = initOpts
	
	def setFile(self, fileName):
		self._file = fileName
		self._initOpts = {}
	
	def getFile(self):
		return self._file
	
	def setJailName(self, jailName):
		self._jailName = jailName
	
	def getJailName(self):
		return self._jailName
	
	def read(self):
		return ConfigReader.read(self, self._file)

	# needed for fail2ban-regex that doesn't need fancy directories
	def readexplicit(self):
		return SafeConfigParserWithIncludes.read(self, self._file)
	
	def getOptions(self, pOpts):
		self._opts = ConfigReader.getOptions(
			self, "Definition", self._configOpts, pOpts)
		
		if self.has_section("Init"):
			for opt in self.options("Init"):
				if not self._initOpts.has_key(opt):
					self._initOpts[opt] = self.get("Init", opt)
	
	def convert(self):
		raise NotImplementedError

########NEW FILE########
__FILENAME__ = configurator
# emacs: -*- mode: python; py-indent-offset: 4; indent-tabs-mode: t -*-
# vi: set ft=python sts=4 ts=4 sw=4 noet :

# This file is part of Fail2Ban.
#
# Fail2Ban is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# Fail2Ban is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with Fail2Ban; if not, write to the Free Software
# Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA  02110-1301, USA.

# Author: Cyril Jaquier
# 

__author__ = "Cyril Jaquier"
__copyright__ = "Copyright (c) 2004 Cyril Jaquier"
__license__ = "GPL"

import logging

from .fail2banreader import Fail2banReader
from .jailsreader import JailsReader

# Gets the instance of the logger.
logSys = logging.getLogger(__name__)

class Configurator:
	
	def __init__(self):
		self.__settings = dict()
		self.__streams = dict()
		self.__fail2ban = Fail2banReader()
		self.__jails = JailsReader()
	
	def setBaseDir(self, folderName):
		self.__fail2ban.setBaseDir(folderName)
		self.__jails.setBaseDir(folderName)
	
	def getBaseDir(self):
		fail2ban_basedir = self.__fail2ban.getBaseDir()
		jails_basedir = self.__jails.getBaseDir()
		if fail2ban_basedir != jails_basedir:
			logSys.error("fail2ban.conf and jails.conf readers have differing "
						 "basedirs: %r and %r. "
						 "Returning the one for fail2ban.conf"
						 % (fail2ban_basedir, jails_basedir))
		return fail2ban_basedir
	
	def readEarly(self):
		self.__fail2ban.read()
	
	def readAll(self):
		self.readEarly()
		self.__jails.read()
	
	def getEarlyOptions(self):
		return self.__fail2ban.getEarlyOptions()

	def getOptions(self, jail = None):
		self.__fail2ban.getOptions()
		return self.__jails.getOptions(jail)
		
	def convertToProtocol(self):
		self.__streams["general"] = self.__fail2ban.convert()
		self.__streams["jails"] = self.__jails.convert()
	
	def getConfigStream(self):
		cmds = list()
		for opt in self.__streams["general"]:
			cmds.append(opt)
		for opt in self.__streams["jails"]:
			cmds.append(opt)
		return cmds
	

########NEW FILE########
__FILENAME__ = csocket
# emacs: -*- mode: python; py-indent-offset: 4; indent-tabs-mode: t -*-
# vi: set ft=python sts=4 ts=4 sw=4 noet :

# This file is part of Fail2Ban.
#
# Fail2Ban is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# Fail2Ban is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with Fail2Ban; if not, write to the Free Software
# Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA  02110-1301, USA.

# Author: Cyril Jaquier
# 

__author__ = "Cyril Jaquier"
__copyright__ = "Copyright (c) 2004 Cyril Jaquier"
__license__ = "GPL"

#from cPickle import dumps, loads, HIGHEST_PROTOCOL
from pickle import dumps, loads, HIGHEST_PROTOCOL
import socket, sys

if sys.version_info >= (3,):
	# b"" causes SyntaxError in python <= 2.5, so below implements equivalent
	EMPTY_BYTES = bytes("", encoding="ascii")
else:
	# python 2.x, string type is equivalent to bytes.
	EMPTY_BYTES = ""

class CSocket:
	
	if sys.version_info >= (3,):
		END_STRING = bytes("<F2B_END_COMMAND>", encoding='ascii')
	else:
		END_STRING = "<F2B_END_COMMAND>"
	
	def __init__(self, sock = "/var/run/fail2ban/fail2ban.sock"):
		# Create an INET, STREAMing socket
		#self.csock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
		self.__csock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
		#self.csock.connect(("localhost", 2222))
		self.__csock.connect(sock)
	
	def send(self, msg):
		# Convert every list member to string
		obj = dumps([str(m) for m in msg], HIGHEST_PROTOCOL)
		self.__csock.send(obj + CSocket.END_STRING)
		ret = self.receive(self.__csock)
		self.__csock.close()
		return ret
	
	#@staticmethod
	def receive(sock):
		msg = EMPTY_BYTES
		while msg.rfind(CSocket.END_STRING) == -1:
			chunk = sock.recv(6)
			if chunk == '':
				raise RuntimeError, "socket connection broken"
			msg = msg + chunk
		return loads(msg)
	receive = staticmethod(receive)

########NEW FILE########
__FILENAME__ = fail2banreader
# emacs: -*- mode: python; py-indent-offset: 4; indent-tabs-mode: t -*-
# vi: set ft=python sts=4 ts=4 sw=4 noet :

# This file is part of Fail2Ban.
#
# Fail2Ban is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# Fail2Ban is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with Fail2Ban; if not, write to the Free Software
# Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA  02110-1301, USA.

# Author: Cyril Jaquier
# 

__author__ = "Cyril Jaquier"
__copyright__ = "Copyright (c) 2004 Cyril Jaquier"
__license__ = "GPL"

import logging

from .configreader import ConfigReader

# Gets the instance of the logger.
logSys = logging.getLogger(__name__)

class Fail2banReader(ConfigReader):
	
	def __init__(self, **kwargs):
		ConfigReader.__init__(self, **kwargs)
	
	def read(self):
		ConfigReader.read(self, "fail2ban")
	
	def getEarlyOptions(self):
		opts = [["string", "socket", "/var/run/fail2ban/fail2ban.sock"],
				["string", "pidfile", "/var/run/fail2ban/fail2ban.pid"]]
		return ConfigReader.getOptions(self, "Definition", opts)
	
	def getOptions(self):
		opts = [["string", "loglevel", "INFO" ],
				["string", "logtarget", "STDERR"],
				["string", "dbfile", "/var/lib/fail2ban/fail2ban.sqlite3"],
				["int", "dbpurgeage", 86400]]
		self.__opts = ConfigReader.getOptions(self, "Definition", opts)
	
	def convert(self):
		stream = list()
		for opt in self.__opts:
			if opt == "loglevel":
				stream.append(["set", "loglevel", self.__opts[opt]])
			elif opt == "logtarget":
				stream.append(["set", "logtarget", self.__opts[opt]])
			elif opt == "dbfile":
				stream.append(["set", "dbfile", self.__opts[opt]])
			elif opt == "dbpurgeage":
				stream.append(["set", "dbpurgeage", self.__opts[opt]])
		# Ensure logtarget/level set first so any db errors are captured
		return sorted(stream, reverse=True)
	

########NEW FILE########
__FILENAME__ = filterreader
# emacs: -*- mode: python; py-indent-offset: 4; indent-tabs-mode: t -*-
# vi: set ft=python sts=4 ts=4 sw=4 noet :

# This file is part of Fail2Ban.
#
# Fail2Ban is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# Fail2Ban is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with Fail2Ban; if not, write to the Free Software
# Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA  02110-1301, USA.

# Author: Cyril Jaquier
# 

__author__ = "Cyril Jaquier"
__copyright__ = "Copyright (c) 2004 Cyril Jaquier"
__license__ = "GPL"

import logging, os, shlex

from .configreader import ConfigReader, DefinitionInitConfigReader
from ..server.action import CommandAction

# Gets the instance of the logger.
logSys = logging.getLogger(__name__)

class FilterReader(DefinitionInitConfigReader):

	_configOpts = [
		["string", "ignoreregex", None],
		["string", "failregex", ""],
	]

	def read(self):
		return ConfigReader.read(self, os.path.join("filter.d", self._file))
	
	def convert(self):
		stream = list()
		combinedopts = dict(list(self._opts.items()) + list(self._initOpts.items()))
		opts = CommandAction.substituteRecursiveTags(combinedopts)
		if not opts:
			raise ValueError('recursive tag definitions unable to be resolved')
		for opt, value in opts.iteritems():
			if opt == "failregex":
				for regex in value.split('\n'):
					# Do not send a command if the rule is empty.
					if regex != '':
						stream.append(["set", self._jailName, "addfailregex", regex])
			elif opt == "ignoreregex":
				for regex in value.split('\n'):
					# Do not send a command if the rule is empty.
					if regex != '':
						stream.append(["set", self._jailName, "addignoreregex", regex])		
		if self._initOpts:
			if 'maxlines' in self._initOpts:
				# We warn when multiline regex is used without maxlines > 1
				# therefore keep sure we set this option first.
				stream.insert(0, ["set", self._jailName, "maxlines", self._initOpts["maxlines"]])
			if 'datepattern' in self._initOpts:
				stream.append(["set", self._jailName, "datepattern", self._initOpts["datepattern"]])
			# Do not send a command if the match is empty.
			if self._initOpts.get("journalmatch", '') != '':
				for match in self._initOpts["journalmatch"].split("\n"):
					stream.append(
						["set", self._jailName, "addjournalmatch"] +
                        shlex.split(match))
		return stream
		

########NEW FILE########
__FILENAME__ = jailreader
# emacs: -*- mode: python; py-indent-offset: 4; indent-tabs-mode: t -*-
# vi: set ft=python sts=4 ts=4 sw=4 noet :

# This file is part of Fail2Ban.
#
# Fail2Ban is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# Fail2Ban is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with Fail2Ban; if not, write to the Free Software
# Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA  02110-1301, USA.

# Author: Cyril Jaquier
# 

__author__ = "Cyril Jaquier"
__copyright__ = "Copyright (c) 2004 Cyril Jaquier"
__license__ = "GPL"

import logging, re, glob, os.path
import json

from .configreader import ConfigReader
from .filterreader import FilterReader
from .actionreader import ActionReader

# Gets the instance of the logger.
logSys = logging.getLogger(__name__)

class JailReader(ConfigReader):
	
	optionCRE = re.compile("^((?:\w|-|_|\.)+)(?:\[(.*)\])?$")
	optionExtractRE = re.compile(
		r'([\w\-_\.]+)=(?:"([^"]*)"|\'([^\']*)\'|([^,]*))(?:,|$)')
	
	def __init__(self, name, force_enable=False, **kwargs):
		ConfigReader.__init__(self, **kwargs)
		self.__name = name
		self.__filter = None
		self.__force_enable = force_enable
		self.__actions = list()
		self.__opts = None
	
	@property
	def options(self):
		return self.__opts

	def setName(self, value):
		self.__name = value
	
	def getName(self):
		return self.__name
	
	def read(self):
		out = ConfigReader.read(self, "jail")
		# Before returning -- verify that requested section
		# exists at all
		if not (self.__name in self.sections()):
			raise ValueError("Jail %r was not found among available"
							 % self.__name)
		return out
	
	def isEnabled(self):
		return self.__force_enable or (
			self.__opts and self.__opts.get("enabled", False))

	@staticmethod
	def _glob(path):
		"""Given a path for glob return list of files to be passed to server.

		Dangling symlinks are warned about and not returned
		"""
		pathList = []
		for p in glob.glob(path):
			if os.path.exists(p):
				pathList.append(p)
			else:
				logSys.warning("File %s is a dangling link, thus cannot be monitored" % p)
		return pathList

	def getOptions(self):
		opts = [["bool", "enabled", False],
				["string", "logpath", None],
				["string", "logencoding", None],
				["string", "backend", "auto"],
				["int", "maxretry", None],
				["int", "findtime", None],
				["int", "bantime", None],
				["string", "usedns", None],
				["string", "failregex", None],
				["string", "ignoreregex", None],
				["string", "ignorecommand", None],
				["string", "ignoreip", None],
				["string", "filter", ""],
				["string", "action", ""]]
		self.__opts = ConfigReader.getOptions(self, self.__name, opts)
		if not self.__opts:
			return False
		
		if self.isEnabled():
			# Read filter
			if self.__opts["filter"]:
				filterName, filterOpt = JailReader.extractOptions(
					self.__opts["filter"])
				self.__filter = FilterReader(
					filterName, self.__name, filterOpt, basedir=self.getBaseDir())
				ret = self.__filter.read()
				if ret:
					self.__filter.getOptions(self.__opts)
				else:
					logSys.error("Unable to read the filter")
					return False
			else:
				self.__filter = None
				logSys.warning("No filter set for jail %s" % self.__name)
		
			# Read action
			for act in self.__opts["action"].split('\n'):
				try:
					if not act:			  # skip empty actions
						continue
					actName, actOpt = JailReader.extractOptions(act)
					if actName.endswith(".py"):
						self.__actions.append([
							"set",
							self.__name,
							"addaction",
							actOpt.pop("actname", os.path.splitext(actName)[0]),
							os.path.join(
								self.getBaseDir(), "action.d", actName),
							json.dumps(actOpt),
							])
					else:
						action = ActionReader(
							actName, self.__name, actOpt,
							basedir=self.getBaseDir())
						ret = action.read()
						if ret:
							action.getOptions(self.__opts)
							self.__actions.append(action)
						else:
							raise AttributeError("Unable to read action")
				except Exception, e:
					logSys.error("Error in action definition " + act)
					logSys.debug("Caught exception: %s" % (e,))
					return False
			if not len(self.__actions):
				logSys.warning("No actions were defined for %s" % self.__name)
		return True
	
	def convert(self, allow_no_files=False):
		"""Convert read before __opts to the commands stream

		Parameters
		----------
		allow_missing : bool
		  Either to allow log files to be missing entirely.  Primarily is
		  used for testing
		 """

		stream = []
		for opt in self.__opts:
			if opt == "logpath" and	\
					self.__opts.get('backend', None) != "systemd":
				found_files = 0
				for path in self.__opts[opt].split("\n"):
					path = path.rsplit(" ", 1)
					path, tail = path if len(path) > 1 else (path[0], "head")
					pathList = JailReader._glob(path)
					if len(pathList) == 0:
						logSys.error("No file(s) found for glob %s" % path)
					for p in pathList:
						found_files += 1
						stream.append(
							["set", self.__name, "addlogpath", p, tail])
				if not (found_files or allow_no_files):
					raise ValueError(
						"Have not found any log file for %s jail" % self.__name)
			elif opt == "logencoding":
				stream.append(["set", self.__name, "logencoding", self.__opts[opt]])
			elif opt == "backend":
				backend = self.__opts[opt]
			elif opt == "maxretry":
				stream.append(["set", self.__name, "maxretry", self.__opts[opt]])
			elif opt == "ignoreip":
				for ip in self.__opts[opt].split():
					# Do not send a command if the rule is empty.
					if ip != '':
						stream.append(["set", self.__name, "addignoreip", ip])
			elif opt == "findtime":
				stream.append(["set", self.__name, "findtime", self.__opts[opt]])
			elif opt == "bantime":
				stream.append(["set", self.__name, "bantime", self.__opts[opt]])
			elif opt == "usedns":
				stream.append(["set", self.__name, "usedns", self.__opts[opt]])
			elif opt == "failregex":
				stream.append(["set", self.__name, "addfailregex", self.__opts[opt]])
			elif opt == "ignorecommand":
				stream.append(["set", self.__name, "ignorecommand", self.__opts[opt]])
			elif opt == "ignoreregex":
				for regex in self.__opts[opt].split('\n'):
					# Do not send a command if the rule is empty.
					if regex != '':
						stream.append(["set", self.__name, "addignoreregex", regex])
		if self.__filter:
			stream.extend(self.__filter.convert())
		for action in self.__actions:
			if isinstance(action, ConfigReader):
				stream.extend(action.convert())
			else:
				stream.append(action)
		stream.insert(0, ["add", self.__name, backend])
		return stream
	
	#@staticmethod
	def extractOptions(option):
		match = JailReader.optionCRE.match(option)
		if not match:
			# TODO proper error handling
			return None, None
		option_name, optstr = match.groups()
		option_opts = dict()
		if optstr:
			for optmatch in JailReader.optionExtractRE.finditer(optstr):
				opt = optmatch.group(1)
				value = [
					val for val in optmatch.group(2,3,4) if val is not None][0]
				option_opts[opt.strip()] = value.strip()
		return option_name, option_opts
	extractOptions = staticmethod(extractOptions)

########NEW FILE########
__FILENAME__ = jailsreader
# emacs: -*- mode: python; py-indent-offset: 4; indent-tabs-mode: t -*-
# vi: set ft=python sts=4 ts=4 sw=4 noet :

# This file is part of Fail2Ban.
#
# Fail2Ban is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# Fail2Ban is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with Fail2Ban; if not, write to the Free Software
# Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA  02110-1301, USA.

# Author: Cyril Jaquier
#

__author__ = "Cyril Jaquier"
__copyright__ = "Copyright (c) 2004 Cyril Jaquier"
__license__ = "GPL"

import logging

from .configreader import ConfigReader
from .jailreader import JailReader

# Gets the instance of the logger.
logSys = logging.getLogger(__name__)

class JailsReader(ConfigReader):

	def __init__(self, force_enable=False, **kwargs):
		"""
		Parameters
		----------
		force_enable : bool, optional
		  Passed to JailReader to force enable the jails.
		  It is for internal use
		"""
		ConfigReader.__init__(self, **kwargs)
		self.__jails = list()
		self.__force_enable = force_enable

	@property
	def jails(self):
		return self.__jails

	def read(self):
		return ConfigReader.read(self, "jail")

	def getOptions(self, section=None):
		"""Reads configuration for jail(s) and adds enabled jails to __jails
		"""
		opts = []
		self.__opts = ConfigReader.getOptions(self, "Definition", opts)

		if section is None:
			sections = self.sections()
		else:
			sections = [ section ]

		# Get the options of all jails.
		parse_status = True
		for sec in sections:
			if sec == 'INCLUDES':
				continue
			jail = JailReader(sec, basedir=self.getBaseDir(),
							  force_enable=self.__force_enable)
			jail.read()
			ret = jail.getOptions()
			if ret:
				if jail.isEnabled():
					# We only add enabled jails
					self.__jails.append(jail)
			else:
				logSys.error("Errors in jail %r. Skipping..." % sec)
				parse_status = False
		return parse_status

	def convert(self, allow_no_files=False):
		"""Convert read before __opts and jails to the commands stream

		Parameters
		----------
		allow_missing : bool
		  Either to allow log files to be missing entirely.  Primarily is
		  used for testing
		"""

		stream = list()
		for opt in self.__opts:
			if opt == "":
				stream.append([])
		# Convert jails
		for jail in self.__jails:
			stream.extend(jail.convert(allow_no_files=allow_no_files))
		# Start jails
		for jail in self.__jails:
			stream.append(["start", jail.getName()])

		return stream


########NEW FILE########
__FILENAME__ = exceptions
# emacs: -*- mode: python; py-indent-offset: 4; indent-tabs-mode: t -*-
# vi: set ft=python sts=4 ts=4 sw=4 noet :
"""Fail2Ban exceptions used by both client and server

"""
# This file is part of Fail2Ban.
#
# Fail2Ban is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# Fail2Ban is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with Fail2Ban; if not, write to the Free Software
# Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA  02110-1301, USA.

__author__ = "Cyril Jaquier, Yaroslav Halchenko"
__copyright__ = "Copyright (c) 2004 Cyril Jaquier, 2011-2012 Yaroslav Halchenko"
__license__ = "GPL"

#
# Jails
#
class DuplicateJailException(Exception):
	pass

class UnknownJailException(KeyError):
	pass




########NEW FILE########
__FILENAME__ = helpers
# emacs: -*- mode: python; py-indent-offset: 4; indent-tabs-mode: t -*-
# vi: set ft=python sts=4 ts=4 sw=4 noet :

# This file is part of Fail2Ban.
#
# Fail2Ban is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# Fail2Ban is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with Fail2Ban; if not, write to the Free Software
# Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA  02110-1301, USA.

__author__ = "Cyril Jaquier, Arturo 'Buanzo' Busleiman, Yaroslav Halchenko"
__license__ = "GPL"

import sys
import os
import traceback
import re
import logging

def formatExceptionInfo():
	""" Consistently format exception information """
	cla, exc = sys.exc_info()[:2]
	return (cla.__name__, str(exc))

#
# Following "traceback" functions are adopted from PyMVPA distributed
# under MIT/Expat and copyright by PyMVPA developers (i.e. me and
# Michael).  Hereby I re-license derivative work on these pieces under GPL
# to stay in line with the main Fail2Ban license
#
def mbasename(s):
	"""Custom function to include directory name if filename is too common

	Also strip .py at the end
	"""
	base = os.path.basename(s)
	if base.endswith('.py'):
		base = base[:-3]
	if base in set(['base', '__init__']):
		base = os.path.basename(os.path.dirname(s)) + '.' + base
	return base

class TraceBack(object):
	"""Customized traceback to be included in debug messages
	"""

	def __init__(self, compress=False):
		"""Initialize TrackBack metric

		Parameters
		----------
		compress : bool
		  if True then prefix common with previous invocation gets
		  replaced with ...
		"""
		self.__prev = ""
		self.__compress = compress

	def __call__(self):
		ftb = traceback.extract_stack(limit=100)[:-2]
		entries = [
			[mbasename(x[0]), os.path.dirname(x[0]), str(x[1])] for x in ftb]
		entries = [ [e[0], e[2]] for e in entries
					if not (e[0] in ['unittest', 'logging.__init__']
							or e[1].endswith('/unittest'))]

		# lets make it more concise
		entries_out = [entries[0]]
		for entry in entries[1:]:
			if entry[0] == entries_out[-1][0]:
				entries_out[-1][1] += ',%s' % entry[1]
			else:
				entries_out.append(entry)
		sftb = '>'.join(['%s:%s' % (mbasename(x[0]),
									x[1]) for x in entries_out])
		if self.__compress:
			# lets remove part which is common with previous invocation
			prev_next = sftb
			common_prefix = os.path.commonprefix((self.__prev, sftb))
			common_prefix2 = re.sub('>[^>]*$', '', common_prefix)

			if common_prefix2 != "":
				sftb = '...' + sftb[len(common_prefix2):]
			self.__prev = prev_next

		return sftb

class FormatterWithTraceBack(logging.Formatter):
	"""Custom formatter which expands %(tb) and %(tbc) with tracebacks

	TODO: might need locking in case of compressed tracebacks
	"""
	def __init__(self, fmt, *args, **kwargs):
		logging.Formatter.__init__(self, fmt=fmt, *args, **kwargs)
		compress = '%(tbc)s' in fmt
		self._tb = TraceBack(compress=compress)

	def format(self, record):
		record.tbc = record.tb = self._tb()
		return logging.Formatter.format(self, record)

########NEW FILE########
__FILENAME__ = protocol
# emacs: -*- mode: python; py-indent-offset: 4; indent-tabs-mode: t -*-
# vi: set ft=python sts=4 ts=4 sw=4 noet :

# This file is part of Fail2Ban.
#
# Fail2Ban is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# Fail2Ban is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with Fail2Ban; if not, write to the Free Software
# Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA  02110-1301, USA.

# Author: Cyril Jaquier
# 

__author__ = "Cyril Jaquier"
__copyright__ = "Copyright (c) 2004 Cyril Jaquier"
__license__ = "GPL"

import textwrap

##
# Describes the protocol used to communicate with the server.

protocol = [
['', "BASIC", ""],
["start", "starts the server and the jails"], 
["reload", "reloads the configuration"], 
["reload <JAIL>", "reloads the jail <JAIL>"], 
["stop", "stops all jails and terminate the server"], 
["status", "gets the current status of the server"], 
["ping", "tests if the server is alive"], 
["help", "return this output"], 
['', "LOGGING", ""],
["set loglevel <LEVEL>", "sets logging level to <LEVEL>. Levels: CRITICAL, ERROR, WARNING, NOTICE, INFO, DEBUG"], 
["get loglevel", "gets the logging level"], 
["set logtarget <TARGET>", "sets logging target to <TARGET>. Can be STDOUT, STDERR, SYSLOG or a file"], 
["get logtarget", "gets logging target"], 
["flushlogs", "flushes the logtarget if a file and reopens it. For log rotation."], 
['', "DATABASE", ""],
["set dbfile <FILE>", "set the location of fail2ban persistent datastore. Set to \"None\" to disable"], 
["get dbfile", "get the location of fail2ban persistent datastore"], 
["set dbpurgeage <SECONDS>", "sets the max age in <SECONDS> that history of bans will be kept"], 
["get dbpurgeage", "gets the max age in seconds that history of bans will be kept"], 
['', "JAIL CONTROL", ""],
["add <JAIL> <BACKEND>", "creates <JAIL> using <BACKEND>"], 
["start <JAIL>", "starts the jail <JAIL>"], 
["stop <JAIL>", "stops the jail <JAIL>. The jail is removed"], 
["status <JAIL>", "gets the current status of <JAIL>"],
['', "JAIL CONFIGURATION", ""],
["set <JAIL> idle on|off", "sets the idle state of <JAIL>"], 
["set <JAIL> addignoreip <IP>", "adds <IP> to the ignore list of <JAIL>"], 
["set <JAIL> delignoreip <IP>", "removes <IP> from the ignore list of <JAIL>"], 
["set <JAIL> addlogpath <FILE> ['tail']", "adds <FILE> to the monitoring list of <JAIL>, optionally starting at the 'tail' of the file (default 'head')."], 
["set <JAIL> dellogpath <FILE>", "removes <FILE> from the monitoring list of <JAIL>"],
["set <JAIL> logencoding <ENCODING>", "sets the <ENCODING> of the log files for <JAIL>"],
["set <JAIL> addjournalmatch <MATCH>", "adds <MATCH> to the journal filter of <JAIL>"],
["set <JAIL> deljournalmatch <MATCH>", "removes <MATCH> from the journal filter of <JAIL>"],
["set <JAIL> addfailregex <REGEX>", "adds the regular expression <REGEX> which must match failures for <JAIL>"], 
["set <JAIL> delfailregex <INDEX>", "removes the regular expression at <INDEX> for failregex"], 
["set <JAIL> ignorecommand <VALUE>", "sets ignorecommand of <JAIL>"],
["set <JAIL> addignoreregex <REGEX>", "adds the regular expression <REGEX> which should match pattern to exclude for <JAIL>"],
["set <JAIL> delignoreregex <INDEX>", "removes the regular expression at <INDEX> for ignoreregex"], 
["set <JAIL> findtime <TIME>", "sets the number of seconds <TIME> for which the filter will look back for <JAIL>"], 
["set <JAIL> bantime <TIME>", "sets the number of seconds <TIME> a host will be banned for <JAIL>"], 
["set <JAIL> datepattern <PATTERN>", "sets the <PATTERN> used to match date/times for <JAIL>"],
["set <JAIL> usedns <VALUE>", "sets the usedns mode for <JAIL>"],
["set <JAIL> banip <IP>", "manually Ban <IP> for <JAIL>"], 
["set <JAIL> unbanip <IP>", "manually Unban <IP> in <JAIL>"], 
["set <JAIL> maxretry <RETRY>", "sets the number of failures <RETRY> before banning the host for <JAIL>"], 
["set <JAIL> maxlines <LINES>", "sets the number of <LINES> to buffer for regex search for <JAIL>"], 
["set <JAIL> addaction <ACT>[ <PYTHONFILE> <JSONKWARGS>]", "adds a new action named <NAME> for <JAIL>. Optionally for a Python based action, a <PYTHONFILE> and <JSONKWARGS> can be specified, else will be a Command Action"], 
["set <JAIL> delaction <ACT>", "removes the action <ACT> from <JAIL>"], 
["", "COMMAND ACTION CONFIGURATION", ""],
["set <JAIL> action <ACT> actionstart <CMD>", "sets the start command <CMD> of the action <ACT> for <JAIL>"], 
["set <JAIL> action <ACT> actionstop <CMD>", "sets the stop command <CMD> of the action <ACT> for <JAIL>"], 
["set <JAIL> action <ACT> actioncheck <CMD>", "sets the check command <CMD> of the action <ACT> for <JAIL>"], 
["set <JAIL> action <ACT> actionban <CMD>", "sets the ban command <CMD> of the action <ACT> for <JAIL>"],
["set <JAIL> action <ACT> actionunban <CMD>", "sets the unban command <CMD> of the action <ACT> for <JAIL>"], 
["set <JAIL> action <ACT> timeout <TIMEOUT>", "sets <TIMEOUT> as the command timeout in seconds for the action <ACT> for <JAIL>"],
["", "GENERAL ACTION CONFIGURATION", ""],
["set <JAIL> action <ACT> <PROPERTY> <VALUE>", "sets the <VALUE> of <PROPERTY> for the action <ACT> for <JAIL>"],
["set <JAIL> action <ACT> <METHOD>[ <JSONKWARGS>]", "calls the <METHOD> with <JSONKWARGS> for the action <ACT> for <JAIL>"],
['', "JAIL INFORMATION", ""],
["get <JAIL> logpath", "gets the list of the monitored files for <JAIL>"],
["get <JAIL> logencoding", "gets the encoding of the log files for <JAIL>"],
["get <JAIL> journalmatch", "gets the journal filter match for <JAIL>"],
["get <JAIL> ignoreip", "gets the list of ignored IP addresses for <JAIL>"],
["get <JAIL> ignorecommand", "gets ignorecommand of <JAIL>"],
["get <JAIL> failregex", "gets the list of regular expressions which matches the failures for <JAIL>"],
["get <JAIL> ignoreregex", "gets the list of regular expressions which matches patterns to ignore for <JAIL>"],
["get <JAIL> findtime", "gets the time for which the filter will look back for failures for <JAIL>"],
["get <JAIL> bantime", "gets the time a host is banned for <JAIL>"],
["get <JAIL> datepattern", "gets the patern used to match date/times for <JAIL>"],
["get <JAIL> usedns", "gets the usedns setting for <JAIL>"],
["get <JAIL> maxretry", "gets the number of failures allowed for <JAIL>"],
["get <JAIL> maxlines", "gets the number of lines to buffer for <JAIL>"],
["get <JAIL> actions", "gets a list of actions for <JAIL>"],
["", "COMMAND ACTION INFORMATION",""],
["get <JAIL> action <ACT> actionstart", "gets the start command for the action <ACT> for <JAIL>"],
["get <JAIL> action <ACT> actionstop", "gets the stop command for the action <ACT> for <JAIL>"],
["get <JAIL> action <ACT> actioncheck", "gets the check command for the action <ACT> for <JAIL>"],
["get <JAIL> action <ACT> actionban", "gets the ban command for the action <ACT> for <JAIL>"],
["get <JAIL> action <ACT> actionunban", "gets the unban command for the action <ACT> for <JAIL>"],
["get <JAIL> action <ACT> timeout", "gets the command timeout in seconds for the action <ACT> for <JAIL>"],
["", "GENERAL ACTION INFORMATION", ""],
["get <JAIL> actionproperties <ACT>", "gets a list of properties for the action <ACT> for <JAIL>"],
["get <JAIL> actionmethods <ACT>", "gets a list of methods for the action <ACT> for <JAIL>"],
["get <JAIL> action <ACT> <PROPERTY>", "gets the value of <PROPERTY> for the action <ACT> for <JAIL>"],
]

##
# Prints the protocol in a "man" format. This is used for the
# "-h" output of fail2ban-client.

def printFormatted():
	INDENT=4
	MARGIN=41
	WIDTH=34
	firstHeading = False
	for m in protocol:
		if m[0] == '' and firstHeading:
			print
		firstHeading = True
		first = True
		if len(m[0]) >= MARGIN:
			m[1] = ' ' * WIDTH + m[1]
		for n in textwrap.wrap(m[1], WIDTH, drop_whitespace=False):
			if first:
				line = ' ' * INDENT + m[0] + ' ' * (MARGIN - len(m[0])) + n.strip()
				first = False
			else:
				line = ' ' * (INDENT + MARGIN) + n.strip()
			print line

##
# Prints the protocol in a "mediawiki" format.

def printWiki():
	firstHeading = False
	for m in protocol:
		if m[0] == '':
			if firstHeading:
				print "|}"
			__printWikiHeader(m[1], m[2])
			firstHeading = True
		else:
			print "|-"
			print "| <span style=\"white-space:nowrap;\"><tt>" + m[0] + "</tt></span> || || " + m[1]
	print "|}"

def __printWikiHeader(section, desc):
	print
	print "=== " + section + " ==="
	print
	print desc
	print
	print "{|"
	print "| '''Command''' || || '''Description'''"

########NEW FILE########
__FILENAME__ = action
# emacs: -*- mode: python; py-indent-offset: 4; indent-tabs-mode: t -*-
# vi: set ft=python sts=4 ts=4 sw=4 noet :

# This file is part of Fail2Ban.
#
# Fail2Ban is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# Fail2Ban is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with Fail2Ban; if not, write to the Free Software
# Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA  02110-1301, USA.

__author__ = "Cyril Jaquier and Fail2Ban Contributors"
__copyright__ = "Copyright (c) 2004 Cyril Jaquier, 2011-2012 Yaroslav Halchenko"
__license__ = "GPL"

import logging, os, subprocess, time, signal, tempfile
import threading, re
from abc import ABCMeta
from collections import MutableMapping
#from subprocess import call

# Gets the instance of the logger.
logSys = logging.getLogger(__name__)

# Create a lock for running system commands
_cmd_lock = threading.Lock()

# Some hints on common abnormal exit codes
_RETCODE_HINTS = {
	127: '"Command not found".  Make sure that all commands in %(realCmd)r '
			'are in the PATH of fail2ban-server process '
			'(grep -a PATH= /proc/`pidof -x fail2ban-server`/environ). '
			'You may want to start '
			'"fail2ban-server -f" separately, initiate it with '
			'"fail2ban-client reload" in another shell session and observe if '
			'additional informative error messages appear in the terminals.'
	}

# Dictionary to lookup signal name from number
signame = dict((num, name)
	for name, num in signal.__dict__.iteritems() if name.startswith("SIG"))

class CallingMap(MutableMapping):
	"""A Mapping type which returns the result of callable values.

	`CallingMap` behaves similar to a standard python dictionary,
	with the exception that any values which are callable, are called
	and the result is returned as the value.
	No error handling is in place, such that any errors raised in the
	callable will raised as usual.
	Actual dictionary is stored in property `data`, and can be accessed
	to obtain original callable values.

	Attributes
	----------
	data : dict
		The dictionary data which can be accessed to obtain items uncalled
	"""

	def __init__(self, *args, **kwargs):
		self.data = dict(*args, **kwargs)

	def __getitem__(self, key):
		value = self.data[key]
		if callable(value):
			return value()
		else:
			return value

	def __setitem__(self, key, value):
		self.data[key] = value

	def __delitem__(self, key):
		del self.data[key]

	def __iter__(self):
		return iter(self.data)

	def __len__(self):
		return len(self.data)

class ActionBase(object):
	"""An abstract base class for actions in Fail2Ban.

	Action Base is a base definition of what methods need to be in
	place to create a Python based action for Fail2Ban. This class can
	be inherited from to ease implementation.
	Required methods:

	- __init__(jail, name)
	- start()
	- stop()
	- ban(aInfo)
	- unban(aInfo)

	Called when action is created, but before the jail/actions is
	started. This should carry out necessary methods to initialise
	the action but not "start" the action.

	Parameters
	----------
	jail : Jail
		The jail in which the action belongs to.
	name : str
		Name assigned to the action.

	Notes
	-----
	Any additional arguments specified in `jail.conf` or passed
	via `fail2ban-client` will be passed as keyword arguments.
	"""
	__metaclass__ = ABCMeta

	@classmethod
	def __subclasshook__(cls, C):
		required = (
			"start",
			"stop",
			"ban",
			"unban",
			)
		for method in required:
			if not callable(getattr(C, method, None)):
				return False
		return True

	def __init__(self, jail, name):
		self._jail = jail
		self._name = name
		self._logSys = logging.getLogger(
			'%s.%s' % (__name__, self.__class__.__name__))

	def start(self):
		"""Executed when the jail/action is started.
		"""
		pass

	def stop(self):
		"""Executed when the jail/action is stopped.
		"""
		pass

	def ban(self, aInfo):
		"""Executed when a ban occurs.

		Parameters
		----------
		aInfo : dict
			Dictionary which includes information in relation to
			the ban.
		"""
		pass

	def unban(self, aInfo):
		"""Executed when a ban expires.

		Parameters
		----------
		aInfo : dict
			Dictionary which includes information in relation to
			the ban.
		"""
		pass

class CommandAction(ActionBase):
	"""A action which executes OS shell commands.

	This is the default type of action which Fail2Ban uses.

	Default sets all commands for actions as empty string, such
	no command is executed.

	Parameters
	----------
	jail : Jail
		The jail in which the action belongs to.
	name : str
		Name assigned to the action.

	Attributes
	----------
	actionban
	actionstart
	actionstop
	actionunban
	timeout
	"""

	_escapedTags = set(('matches', 'ipmatches', 'ipjailmatches'))

	def __init__(self, jail, name):
		super(CommandAction, self).__init__(jail, name)
		self.timeout = 60
		## Command executed in order to initialize the system.
		self.actionstart = ''
		## Command executed when an IP address gets banned.
		self.actionban = ''
		## Command executed when an IP address gets removed.
		self.actionunban = ''
		## Command executed in order to check requirements.
		self.actioncheck = ''
		## Command executed in order to stop the system.
		self.actionstop = ''
		self._logSys.debug("Created %s" % self.__class__)

	@classmethod
	def __subclasshook__(cls, C):
		return NotImplemented # Standard checks

	@property
	def timeout(self):
		"""Time out period in seconds for execution of commands.
		"""
		return self._timeout

	@timeout.setter
	def timeout(self, timeout):
		self._timeout = int(timeout)
		self._logSys.debug("Set action %s timeout = %i" %
			(self._name, self.timeout))

	@property
	def _properties(self):
		"""A dictionary of the actions properties.

		This is used to subsitute "tags" in the commands.
		"""
		return dict(
			(key, getattr(self, key))
			for key in dir(self)
			if not key.startswith("_") and not callable(getattr(self, key)))

	@property
	def actionstart(self):
		"""The command executed on start of the jail/action.
		"""
		return self._actionstart

	@actionstart.setter
	def actionstart(self, value):
		self._actionstart = value
		self._logSys.debug("Set actionstart = %s" % value)

	def start(self):
		"""Executes the "actionstart" command.

		Replace the tags in the action command with actions properties
		and executes the resulting command.
		"""
		if (self._properties and
			not self.substituteRecursiveTags(self._properties)):
			self._logSys.error(
				"properties contain self referencing definitions "
				"and cannot be resolved")
			raise RuntimeError("Error starting action")
		startCmd = self.replaceTag(self.actionstart, self._properties)
		if not self.executeCmd(startCmd, self.timeout):
			raise RuntimeError("Error starting action")

	@property
	def actionban(self):
		"""The command used when a ban occurs.
		"""
		return self._actionban

	@actionban.setter
	def actionban(self, value):
		self._actionban = value
		self._logSys.debug("Set actionban = %s" % value)

	def ban(self, aInfo):
		"""Executes the "actionban" command.

		Replaces the tags in the action command with actions properties
		and ban information, and executes the resulting command.

		Parameters
		----------
		aInfo : dict
			Dictionary which includes information in relation to
			the ban.
		"""
		if not self._processCmd(self.actionban, aInfo):
			raise RuntimeError("Error banning %(ip)s" % aInfo)

	@property
	def actionunban(self):
		"""The command used when an unban occurs.
		"""
		return self._actionunban

	@actionunban.setter
	def actionunban(self, value):
		self._actionunban = value
		self._logSys.debug("Set actionunban = %s" % value)

	def unban(self, aInfo):
		"""Executes the "actionunban" command.

		Replaces the tags in the action command with actions properties
		and ban information, and executes the resulting command.

		Parameters
		----------
		aInfo : dict
			Dictionary which includes information in relation to
			the ban.
		"""
		if not self._processCmd(self.actionunban, aInfo):
			raise RuntimeError("Error unbanning %(ip)s" % aInfo)

	@property
	def actioncheck(self):
		"""The command used to check the environment.

		This is used prior to a ban taking place to ensure the
		environment is appropriate. If this check fails, `stop` and
		`start` is executed prior to the check being called again.
		"""
		return self._actioncheck

	@actioncheck.setter
	def actioncheck(self, value):
		self._actioncheck = value
		self._logSys.debug("Set actioncheck = %s" % value)

	@property
	def actionstop(self):
		"""The command executed when the jail/actions stops.
		"""
		return self._actionstop

	@actionstop.setter
	def actionstop(self, value):
		self._actionstop = value
		self._logSys.debug("Set actionstop = %s" % value)

	def stop(self):
		"""Executes the "actionstop" command.

		Replaces the tags in the action command with actions properties
		and executes the resulting command.
		"""
		stopCmd = self.replaceTag(self.actionstop, self._properties)
		if not self.executeCmd(stopCmd, self.timeout):
			raise RuntimeError("Error stopping action")

	@classmethod
	def substituteRecursiveTags(cls, tags):
		"""Sort out tag definitions within other tags.

		so:		becomes:
		a = 3		a = 3
		b = <a>_3	b = 3_3

		Parameters
		----------
		tags : dict
			Dictionary of tags(keys) and their values.

		Returns
		-------
		dict
			Dictionary of tags(keys) and their values, with tags
			within the values recursively replaced.
		"""
		t = re.compile(r'<([^ >]+)>')
		for tag in tags.iterkeys():
			if tag in cls._escapedTags:
				# Escaped so won't match
				continue
			value = str(tags[tag])
			m = t.search(value)
			done = []
			#logSys.log(5, 'TAG: %s, value: %s' % (tag, value))
			while m:
				found_tag = m.group(1)
				#logSys.log(5, 'found: %s' % found_tag)
				if found_tag == tag or found_tag in done:
					# recursive definitions are bad
					#logSys.log(5, 'recursion fail tag: %s value: %s' % (tag, value) )
					return False
				elif found_tag in cls._escapedTags:
					# Escaped so won't match
					continue
				else:
					if tags.has_key(found_tag):
						value = value.replace('<%s>' % found_tag , tags[found_tag])
						#logSys.log(5, 'value now: %s' % value)
						done.append(found_tag)
						m = t.search(value, m.start())
					else:
						# Missing tags are ok so we just continue on searching.
						# cInfo can contain aInfo elements like <HOST> and valid shell
						# constructs like <STDIN>.
						m = t.search(value, m.start() + 1)
			#logSys.log(5, 'TAG: %s, newvalue: %s' % (tag, value))
			tags[tag] = value
		return tags

	@staticmethod
	def escapeTag(value):
		"""Escape characters which may be used for command injection.

		Parameters
		----------
		value : str
			A string of which characters will be escaped.

		Returns
		-------
		str
			`value` with certain characters escaped.

		Notes
		-----
		The following characters are escaped::

			\\#&;`|*?~<>^()[]{}$'"

		"""
		for c in '\\#&;`|*?~<>^()[]{}$\'"':
			if c in value:
				value = value.replace(c, '\\' + c)
		return value

	@classmethod
	def replaceTag(cls, query, aInfo):
		"""Replaces tags in `query` with property values.

		Parameters
		----------
		query : str
			String with tags.
		aInfo : dict
			Tags(keys) and associated values for substitution in query.

		Returns
		-------
		str
			`query` string with tags replaced.
		"""
		string = query
		aInfo = cls.substituteRecursiveTags(aInfo)
		for tag in aInfo:
			if "<%s>" % tag in query:
				value = str(aInfo[tag])			  # assure string
				if tag in cls._escapedTags:
					# That one needs to be escaped since its content is
					# out of our control
					value = cls.escapeTag(value)
				string = string.replace('<' + tag + '>', value)
		# New line
		string = string.replace("<br>", '\n')
		return string

	def _processCmd(self, cmd, aInfo = None):
		"""Executes a command with preliminary checks and substitutions.

		Before executing any commands, executes the "check" command first
		in order to check if pre-requirements are met. If this check fails,
		it tries to restore a sane environment before executing the real
		command.

		Parameters
		----------
		cmd : str
			The command to execute.
		aInfo : dictionary
			Dynamic properties.

		Returns
		-------
		bool
			True if the command succeeded.
		"""
		if cmd == "":
			self._logSys.debug("Nothing to do")
			return True

		checkCmd = self.replaceTag(self.actioncheck, self._properties)
		if not self.executeCmd(checkCmd, self.timeout):
			self._logSys.error(
				"Invariant check failed. Trying to restore a sane environment")
			self.stop()
			self.start()
			if not self.executeCmd(checkCmd, self.timeout):
				self._logSys.critical("Unable to restore environment")
				return False

		# Replace tags
		if not aInfo is None:
			realCmd = self.replaceTag(cmd, aInfo)
		else:
			realCmd = cmd
		
		# Replace static fields
		realCmd = self.replaceTag(realCmd, self._properties)
		
		return self.executeCmd(realCmd, self.timeout)

	@staticmethod
	def executeCmd(realCmd, timeout=60):
		"""Executes a command.

		Parameters
		----------
		realCmd : str
			The command to execute.
		timeout : int
			The time out in seconds for the command.

		Returns
		-------
		bool
			True if the command succeeded.

		Raises
		------
		OSError
			If command fails to be executed.
		RuntimeError
			If command execution times out.
		"""
		logSys.debug(realCmd)
		if not realCmd:
			logSys.debug("Nothing to do")
			return True
		
		_cmd_lock.acquire()
		try: # Try wrapped within another try needed for python version < 2.5
			stdout = tempfile.TemporaryFile(suffix=".stdout", prefix="fai2ban_")
			stderr = tempfile.TemporaryFile(suffix=".stderr", prefix="fai2ban_")
			try:
				popen = subprocess.Popen(
					realCmd, stdout=stdout, stderr=stderr, shell=True)
				stime = time.time()
				retcode = popen.poll()
				while time.time() - stime <= timeout and retcode is None:
					time.sleep(0.1)
					retcode = popen.poll()
				if retcode is None:
					logSys.error("%s -- timed out after %i seconds." %
						(realCmd, timeout))
					os.kill(popen.pid, signal.SIGTERM) # Terminate the process
					time.sleep(0.1)
					retcode = popen.poll()
					if retcode is None: # Still going...
						os.kill(popen.pid, signal.SIGKILL) # Kill the process
						time.sleep(0.1)
						retcode = popen.poll()
			except OSError, e:
				logSys.error("%s -- failed with %s" % (realCmd, e))
		finally:
			_cmd_lock.release()

		std_level = retcode == 0 and logging.DEBUG or logging.ERROR
		if std_level >= logSys.getEffectiveLevel():
			stdout.seek(0)
			logSys.log(std_level, "%s -- stdout: %r" % (realCmd, stdout.read()))
			stderr.seek(0)
			logSys.log(std_level, "%s -- stderr: %r" % (realCmd, stderr.read()))
		stdout.close()
		stderr.close()

		if retcode == 0:
			logSys.debug("%s -- returned successfully" % realCmd)
			return True
		elif retcode is None:
			logSys.error("%s -- unable to kill PID %i" % (realCmd, popen.pid))
		elif retcode < 0:
			logSys.error("%s -- killed with %s" %
				(realCmd, signame.get(-retcode, "signal %i" % -retcode)))
		else:
			msg = _RETCODE_HINTS.get(retcode, None)
			logSys.error("%s -- returned %i" % (realCmd, retcode))
			if msg:
				logSys.info("HINT on %i: %s"
							% (retcode, msg % locals()))
			return False
		raise RuntimeError("Command execution failed: %s" % realCmd)
	

########NEW FILE########
__FILENAME__ = actions
# emacs: -*- mode: python; py-indent-offset: 4; indent-tabs-mode: t -*-
# vi: set ft=python sts=4 ts=4 sw=4 noet :

# This file is part of Fail2Ban.
#
# Fail2Ban is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# Fail2Ban is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with Fail2Ban; if not, write to the Free Software
# Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA  02110-1301, USA.

# Author: Cyril Jaquier
# 

__author__ = "Cyril Jaquier"
__copyright__ = "Copyright (c) 2004 Cyril Jaquier"
__license__ = "GPL"

import time, logging
import os
import sys
if sys.version_info >= (3, 3):
	import importlib.machinery
else:
	import imp
from collections import Mapping
try:
	from collections import OrderedDict
except ImportError:
	OrderedDict = None

from .banmanager import BanManager
from .jailthread import JailThread
from .action import ActionBase, CommandAction, CallingMap
from .mytime import MyTime

# Gets the instance of the logger.
logSys = logging.getLogger(__name__)

class Actions(JailThread, Mapping):
	"""Handles jail actions.

	This class handles the actions of the jail. Creation, deletion or to
	actions must be done through this class. This class is based on the
	Mapping type, and the `add` method must be used to add new actions.
	This class also starts and stops the actions, and fetches bans from
	the jail executing these bans via the actions.

	Parameters
	----------
	jail: Jail
		The jail of which the actions belongs to.

	Attributes
	----------
	daemon
	ident
	name
	status
	active : bool
		Control the state of the thread.
	idle : bool
		Control the idle state of the thread.
	sleeptime : int
		The time the thread sleeps for in the loop.
	"""

	def __init__(self, jail):
		JailThread.__init__(self)
		## The jail which contains this action.
		self._jail = jail
		if OrderedDict is not None:
			self._actions = OrderedDict()
		else:
			self._actions = dict()
		## The ban manager.
		self.__banManager = BanManager()

	def add(self, name, pythonModule=None, initOpts=None):
		"""Adds a new action.

		Add a new action if not already present, defaulting to standard
		`CommandAction`, or specified Python module.

		Parameters
		----------
		name : str
			The name of the action.
		pythonModule : str, optional
			Path to Python file which must contain `Action` class.
			Default None, which means `CommandAction` is used.
		initOpts : dict, optional
			Options for Python Action, used as keyword arguments for
			initialisation. Default None.

		Raises
		------
		ValueError
			If action name already exists.
		RuntimeError
			If external Python module does not have `Action` class
			or does not implement necessary methods as per `ActionBase`
			abstract class.
		"""
		# Check is action name already exists
		if name in self._actions:
			raise ValueError("Action %s already exists" % name)
		if pythonModule is None:
			action = CommandAction(self._jail, name)
		else:
			pythonModuleName = os.path.splitext(
				os.path.basename(pythonModule))[0]
			if sys.version_info >= (3, 3):
				customActionModule = importlib.machinery.SourceFileLoader(
					pythonModuleName, pythonModule).load_module()
			else:
				customActionModule = imp.load_source(
					pythonModuleName, pythonModule)
			if not hasattr(customActionModule, "Action"):
				raise RuntimeError(
					"%s module does not have 'Action' class" % pythonModule)
			elif not issubclass(customActionModule.Action, ActionBase):
				raise RuntimeError(
					"%s module %s does not implement required methods" % (
						pythonModule, customActionModule.Action.__name__))
			action = customActionModule.Action(self._jail, name, **initOpts)
		self._actions[name] = action

	def __getitem__(self, name):
		try:
			return self._actions[name]
		except KeyError:
			raise KeyError("Invalid Action name: %s" % name)

	def __delitem__(self, name):
		try:
			del self._actions[name]
		except KeyError:
			raise KeyError("Invalid Action name: %s" % name)

	def __iter__(self):
		return iter(self._actions)

	def __len__(self):
		return len(self._actions)

	def __eq__(self, other): # Required for Threading
		return False

	def __hash__(self): # Required for Threading
		return id(self)

	##
	# Set the ban time.
	#
	# @param value the time
	
	def setBanTime(self, value):
		self.__banManager.setBanTime(value)
		logSys.info("Set banTime = %s" % value)
	
	##
	# Get the ban time.
	#
	# @return the time
	
	def getBanTime(self):
		return self.__banManager.getBanTime()

	def removeBannedIP(self, ip):
		"""Removes banned IP calling actions' unban method

		Remove a banned IP now, rather than waiting for it to expire,
		even if set to never expire.

		Parameters
		----------
		ip : str
			The IP address to unban

		Raises
		------
		ValueError
			If `ip` is not banned
		"""
		# Find the ticket with the IP.
		ticket = self.__banManager.getTicketByIP(ip)
		if ticket is not None:
			# Unban the IP.
			self.__unBan(ticket)
		else:
			raise ValueError("IP %s is not banned" % ip)

	def run(self):
		"""Main loop for Threading.

		This function is the main loop of the thread. It checks the jail
		queue and executes commands when an IP address is banned.

		Returns
		-------
		bool
			True when the thread exits nicely.
		"""
		for name, action in self._actions.iteritems():
			try:
				action.start()
			except Exception as e:
				logSys.error("Failed to start jail '%s' action '%s': %s",
					self._jail.name, name, e,
					exc_info=logSys.getEffectiveLevel()<=logging.DEBUG)
		while self.active:
			if not self.idle:
				#logSys.debug(self._jail.name + ": action")
				ret = self.__checkBan()
				if not ret:
					self.__checkUnBan()
					time.sleep(self.sleeptime)
			else:
				time.sleep(self.sleeptime)
		self.__flushBan()

		actions = self._actions.items()
		actions.reverse()
		for name, action in actions:
			try:
				action.stop()
			except Exception as e:
				logSys.error("Failed to stop jail '%s' action '%s': %s",
					self._jail.name, name, e,
					exc_info=logSys.getEffectiveLevel()<=logging.DEBUG)
		logSys.debug(self._jail.name + ": action terminated")
		return True

	def __checkBan(self):
		"""Check for IP address to ban.

		Look in the jail queue for FailTicket. If a ticket is available,
		it executes the "ban" command and adds a ticket to the BanManager.

		Returns
		-------
		bool
			True if an IP address get banned.
		"""
		ticket = self._jail.getFailTicket()
		if ticket != False:
			aInfo = CallingMap()
			bTicket = BanManager.createBanTicket(ticket)
			ip = bTicket.getIP()
			aInfo["ip"] = ip
			aInfo["failures"] = bTicket.getAttempt()
			aInfo["time"] = bTicket.getTime()
			aInfo["matches"] = "\n".join(bTicket.getMatches())
			if self._jail.database is not None:
				aInfo["ipmatches"] = lambda jail=self._jail: "\n".join(
					jail.database.getBansMerged(ip=ip).getMatches())
				aInfo["ipjailmatches"] = lambda jail=self._jail: "\n".join(
					jail.database.getBansMerged(ip=ip, jail=jail).getMatches())
				aInfo["ipfailures"] = lambda jail=self._jail: \
					jail.database.getBansMerged(ip=ip).getAttempt()
				aInfo["ipjailfailures"] = lambda jail=self._jail: \
					jail.database.getBansMerged(ip=ip, jail=jail).getAttempt()
			if self.__banManager.addBanTicket(bTicket):
				logSys.notice("[%s] Ban %s" % (self._jail.name, aInfo["ip"]))
				for name, action in self._actions.iteritems():
					try:
						action.ban(aInfo)
					except Exception as e:
						logSys.error(
							"Failed to execute ban jail '%s' action '%s': %s",
							self._jail.name, name, e,
							exc_info=logSys.getEffectiveLevel()<=logging.DEBUG)
				return True
			else:
				logSys.notice("[%s] %s already banned" % (self._jail.name,
														aInfo["ip"]))
		return False

	def __checkUnBan(self):
		"""Check for IP address to unban.

		Unban IP addresses which are outdated.
		"""
		for ticket in self.__banManager.unBanList(MyTime.time()):
			self.__unBan(ticket)

	def __flushBan(self):
		"""Flush the ban list.

		Unban all IP address which are still in the banning list.
		"""
		logSys.debug("Flush ban list")
		for ticket in self.__banManager.flushBanList():
			self.__unBan(ticket)

	def __unBan(self, ticket):
		"""Unbans host corresponding to the ticket.

		Executes the actions in order to unban the host given in the
		ticket.

		Parameters
		----------
		ticket : FailTicket
			Ticket of failures of which to unban
		"""
		aInfo = dict()
		aInfo["ip"] = ticket.getIP()
		aInfo["failures"] = ticket.getAttempt()
		aInfo["time"] = ticket.getTime()
		aInfo["matches"] = "".join(ticket.getMatches())
		logSys.notice("[%s] Unban %s" % (self._jail.name, aInfo["ip"]))
		for name, action in self._actions.iteritems():
			try:
				action.unban(aInfo)
			except Exception as e:
				logSys.error(
					"Failed to execute unban jail '%s' action '%s': %s",
					self._jail.name, name, e,
					exc_info=logSys.getEffectiveLevel()<=logging.DEBUG)

	@property
	def status(self):
		"""Status of active bans, and total ban counts.
		"""
		ret = [("Currently banned", self.__banManager.size()), 
			   ("Total banned", self.__banManager.getBanTotal()),
			   ("Banned IP list", self.__banManager.getBanList())]
		return ret

########NEW FILE########
__FILENAME__ = asyncserver
# emacs: -*- mode: python; py-indent-offset: 4; indent-tabs-mode: t -*-
# vi: set ft=python sts=4 ts=4 sw=4 noet :

# This file is part of Fail2Ban.
#
# Fail2Ban is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# Fail2Ban is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with Fail2Ban; if not, write to the Free Software
# Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA  02110-1301, USA.

# Author: Cyril Jaquier
# 

__author__ = "Cyril Jaquier"
__copyright__ = "Copyright (c) 2004 Cyril Jaquier"
__license__ = "GPL"

from pickle import dumps, loads, HIGHEST_PROTOCOL
import asyncore, asynchat, socket, os, logging, sys, traceback, fcntl

from .. import helpers

# Gets the instance of the logger.
logSys = logging.getLogger(__name__)

if sys.version_info >= (3,):
	# b"" causes SyntaxError in python <= 2.5, so below implements equivalent
	EMPTY_BYTES = bytes("", encoding="ascii")
else:
	# python 2.x, string type is equivalent to bytes.
	EMPTY_BYTES = ""

##
# Request handler class.
#
# This class extends asynchat in order to provide a request handler for
# incoming query.

class RequestHandler(asynchat.async_chat):
	
	if sys.version_info >= (3,):
		END_STRING = bytes("<F2B_END_COMMAND>", encoding="ascii")
	else:
		END_STRING = "<F2B_END_COMMAND>"

	def __init__(self, conn, transmitter):
		asynchat.async_chat.__init__(self, conn)
		self.__transmitter = transmitter
		self.__buffer = []
		# Sets the terminator.
		self.set_terminator(RequestHandler.END_STRING)

	def collect_incoming_data(self, data):
		#logSys.debug("Received raw data: " + str(data))
		self.__buffer.append(data)

	##
	# Handles a new request.
	#
	# This method is called once we have a complete request.

	def found_terminator(self):
		# Joins the buffer items.
		message = loads(EMPTY_BYTES.join(self.__buffer))
		# Gives the message to the transmitter.
		message = self.__transmitter.proceed(message)
		# Serializes the response.
		message = dumps(message, HIGHEST_PROTOCOL)
		# Sends the response to the client.
		self.push(message + RequestHandler.END_STRING)
		# Closes the channel.
		self.close_when_done()
		
	def handle_error(self):
		e1, e2 = helpers.formatExceptionInfo()
		logSys.error("Unexpected communication error: %s" % str(e2))
		logSys.error(traceback.format_exc().splitlines())
		self.close()
		
##
# Asynchronous server class.
#
# This class extends asyncore and dispatches connection requests to
# RequestHandler.

class AsyncServer(asyncore.dispatcher):

	def __init__(self, transmitter):
		asyncore.dispatcher.__init__(self)
		self.__transmitter = transmitter
		self.__sock = "/var/run/fail2ban/fail2ban.sock"
		self.__init = False

	##
	# Returns False as we only read the socket first.

	def writable(self):
		return False

	def handle_accept(self):
		try:
			conn, addr = self.accept()
		except socket.error:
			logSys.warning("Socket error")
			return
		except TypeError:
			logSys.warning("Type error")
			return
		AsyncServer.__markCloseOnExec(conn)
		# Creates an instance of the handler class to handle the
		# request/response on the incoming connection.
		RequestHandler(conn, self.__transmitter)
	
	##
	# Starts the communication server.
	#
	# @param sock: socket file.
	# @param force: remove the socket file if exists.
	
	def start(self, sock, force):
		self.__sock = sock
		# Remove socket
		if os.path.exists(sock):
			logSys.error("Fail2ban seems to be already running")
			if force:
				logSys.warning("Forcing execution of the server")
				os.remove(sock)
			else:
				raise AsyncServerException("Server already running")
		# Creates the socket.
		self.create_socket(socket.AF_UNIX, socket.SOCK_STREAM)
		self.set_reuse_addr()
		try:
			self.bind(sock)
		except Exception:
			raise AsyncServerException("Unable to bind socket %s" % self.__sock)
		AsyncServer.__markCloseOnExec(self.socket)
		self.listen(1)
		# Sets the init flag.
		self.__init = True
		# TODO Add try..catch
		# There's a bug report for Python 2.6/3.0 that use_poll=True yields some 2.5 incompatibilities:
		if sys.version_info >= (2, 6): # if python 2.6 or greater...
			logSys.debug("Detected Python 2.6 or greater. asyncore.loop() not using poll")
			asyncore.loop(use_poll = False) # fixes the "Unexpected communication problem" issue on Python 2.6 and 3.0
		else: # pragma: no cover
			logSys.debug("NOT Python 2.6/3.* - asyncore.loop() using poll")
			asyncore.loop(use_poll = True)
	
	##
	# Stops the communication server.
	
	def stop(self):
		if self.__init:
			# Only closes the socket if it was initialized first.
			self.close()
		# Remove socket
		if os.path.exists(self.__sock):
			logSys.debug("Removed socket file " + self.__sock)
			os.remove(self.__sock)
		logSys.debug("Socket shutdown")

	##
	# Marks socket as close-on-exec to avoid leaking file descriptors when
	# running actions involving command execution.

	# @param sock: socket file.
	
	#@staticmethod
	def __markCloseOnExec(sock):
		fd = sock.fileno()
		flags = fcntl.fcntl(fd, fcntl.F_GETFD)
		fcntl.fcntl(fd, fcntl.F_SETFD, flags|fcntl.FD_CLOEXEC)
	__markCloseOnExec = staticmethod(__markCloseOnExec)

##
# AsyncServerException is used to wrap communication exceptions.

class AsyncServerException(Exception):
	pass

########NEW FILE########
__FILENAME__ = banmanager
# emacs: -*- mode: python; py-indent-offset: 4; indent-tabs-mode: t -*-
# vi: set ft=python sts=4 ts=4 sw=4 noet :

# This file is part of Fail2Ban.
#
# Fail2Ban is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# Fail2Ban is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with Fail2Ban; if not, write to the Free Software
# Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA  02110-1301, USA.

# Author: Cyril Jaquier
# 

__author__ = "Cyril Jaquier"
__copyright__ = "Copyright (c) 2004 Cyril Jaquier"
__license__ = "GPL"

import logging
from threading import Lock

from .ticket import BanTicket
from .mytime import MyTime

# Gets the instance of the logger.
logSys = logging.getLogger(__name__)

##
# Banning Manager.
#
# Manage the banned IP addresses. Convert FailTicket to BanTicket.
# This class is mainly used by the Action class.

class BanManager:
	
	##
	# Constructor.
	#
	# Initialize members with default values.
	
	def __init__(self):
		## Mutex used to protect the ban list.
		self.__lock = Lock()
		## The ban list.
		self.__banList = list()
		## The amount of time an IP address gets banned.
		self.__banTime = 600
		## Total number of banned IP address
		self.__banTotal = 0
	
	##
	# Set the ban time.
	#
	# Set the amount of time an IP address get banned.
	# @param value the time
	
	def setBanTime(self, value):
		try:
			self.__lock.acquire()
			self.__banTime = int(value)
		finally:
			self.__lock.release()
	
	##
	# Get the ban time.
	#
	# Get the amount of time an IP address get banned.
	# @return the time
	
	def getBanTime(self):
		try:
			self.__lock.acquire()
			return self.__banTime
		finally:
			self.__lock.release()
	
	##
	# Set the total number of banned address.
	#
	# @param value total number
	
	def setBanTotal(self, value):
		try:
			self.__lock.acquire()
			self.__banTotal = value
		finally:
			self.__lock.release()
	
	##
	# Get the total number of banned address.
	#
	# @return the total number
	
	def getBanTotal(self):
		try:
			self.__lock.acquire()
			return self.__banTotal
		finally:
			self.__lock.release()

	##
	# Returns a copy of the IP list.
	#
	# @return IP list
	
	def getBanList(self):
		try:
			self.__lock.acquire()
			return [m.getIP() for m in self.__banList]
		finally:
			self.__lock.release()

	##
	# Create a ban ticket.
	#
	# Create a BanTicket from a FailTicket. The timestamp of the BanTicket
	# is the current time. This is a static method.
	# @param ticket the FailTicket
	# @return a BanTicket
	
	#@staticmethod
	def createBanTicket(ticket):
		ip = ticket.getIP()
		#lastTime = ticket.getTime()
		lastTime = MyTime.time()
		banTicket = BanTicket(ip, lastTime, ticket.getMatches())
		banTicket.setAttempt(ticket.getAttempt())
		return banTicket
	createBanTicket = staticmethod(createBanTicket)
	
	##
	# Add a ban ticket.
	#
	# Add a BanTicket instance into the ban list.
	# @param ticket the ticket
	# @return True if the IP address is not in the ban list
	
	def addBanTicket(self, ticket):
		try:
			self.__lock.acquire()
			if not self._inBanList(ticket):
				self.__banList.append(ticket)
				self.__banTotal += 1
				return True
			return False
		finally:
			self.__lock.release()
	
	
	##
	# Get the size of the ban list.
	#
	# @return the size
	
	def size(self):
		try:
			self.__lock.acquire()
			return len(self.__banList)
		finally:
			self.__lock.release()
	
	##
	# Check if a ticket is in the list.
	#
	# Check if a BanTicket with a given IP address is already in the
	# ban list.
	# @param ticket the ticket
	# @return True if a ticket already exists
	
	def _inBanList(self, ticket):
		for i in self.__banList:
			if ticket.getIP() == i.getIP():
				return True
		return False
	
	##
	# Get the list of IP address to unban.
	#
	# Return a list of BanTicket which need to be unbanned.
	# @param time the time
	# @return the list of ticket to unban
	
	def unBanList(self, time):
		try:
			self.__lock.acquire()
			# Permanent banning
			if self.__banTime < 0:
				return list()

			# Gets the list of ticket to remove.
			unBanList = [ticket for ticket in self.__banList
						 if ticket.getTime() < time - self.__banTime]
			
			# Removes tickets.
			self.__banList = [ticket for ticket in self.__banList
							  if ticket not in unBanList]
						
			return unBanList
		finally:
			self.__lock.release()

	##
	# Flush the ban list.
	#
	# Get the ban list and initialize it with an empty one.
	# @return the complete ban list
	
	def flushBanList(self):
		try:
			self.__lock.acquire()
			uBList = self.__banList
			self.__banList = list()
			return uBList
		finally:
			self.__lock.release()

	##
	# Gets the ticket for the specified IP.
	#
	# @return the ticket for the IP or False.
	def getTicketByIP(self, ip):
		try:
			self.__lock.acquire()

			# Find the ticket the IP goes with and return it
			for i, ticket in enumerate(self.__banList):
				if ticket.getIP() == ip:
					# Return the ticket after removing (popping)
					# if from the ban list.
					return self.__banList.pop(i)
		finally:
			self.__lock.release()
		return None						  # if none found

########NEW FILE########
__FILENAME__ = database
# emacs: -*- mode: python; py-indent-offset: 4; indent-tabs-mode: t -*-
# vi: set ft=python sts=4 ts=4 sw=4 noet :

# This file is part of Fail2Ban.
#
# Fail2Ban is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# Fail2Ban is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with Fail2Ban; if not, write to the Free Software
# Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA  02110-1301, USA.

__author__ = "Steven Hiscocks"
__copyright__ = "Copyright (c) 2013 Steven Hiscocks"
__license__ = "GPL"

import logging
import sys
import shutil, time
import sqlite3
import json
import locale
from functools import wraps
from threading import Lock

from .mytime import MyTime
from .ticket import FailTicket

# Gets the instance of the logger.
logSys = logging.getLogger(__name__)

if sys.version_info >= (3,):
	sqlite3.register_adapter(
		dict,
		lambda x: json.dumps(x, ensure_ascii=False).encode(
			locale.getpreferredencoding(), 'replace'))
	sqlite3.register_converter(
		"JSON",
		lambda x: json.loads(x.decode(
			locale.getpreferredencoding(), 'replace')))
else:
	sqlite3.register_adapter(dict, json.dumps)
	sqlite3.register_converter("JSON", json.loads)

def commitandrollback(f):
	@wraps(f)
	def wrapper(self, *args, **kwargs):
		with self._lock: # Threading lock
			with self._db: # Auto commit and rollback on exception
				return f(self, self._db.cursor(), *args, **kwargs)
	return wrapper

class Fail2BanDb(object):
	"""Fail2Ban database for storing persistent data.

	This allows after Fail2Ban is restarted to reinstated bans and
	to continue monitoring logs from the same point.

	This will either create a new Fail2Ban database, connect to an
	existing, and if applicable upgrade the schema in the process.

	Parameters
	----------
	filename : str
		File name for SQLite3 database, which will be created if
		doesn't already exist.
	purgeAge : int
		Purge age in seconds, used to remove old bans from
		database during purge.

	Raises
	------
	sqlite3.OperationalError
		Error connecting/creating a SQLite3 database.
	RuntimeError
		If exisiting database fails to update to new schema.

	Attributes
	----------
	filename
	purgeage
	"""
	__version__ = 2
	# Note all _TABLE_* strings must end in ';' for py26 compatibility
	_TABLE_fail2banDb = "CREATE TABLE fail2banDb(version INTEGER);"
	_TABLE_jails = "CREATE TABLE jails(" \
			"name TEXT NOT NULL UNIQUE, " \
			"enabled INTEGER NOT NULL DEFAULT 1" \
			");" \
			"CREATE INDEX jails_name ON jails(name);"
	_TABLE_logs = "CREATE TABLE logs(" \
			"jail TEXT NOT NULL, " \
			"path TEXT, " \
			"firstlinemd5 TEXT, " \
			"lastfilepos INTEGER DEFAULT 0, " \
			"FOREIGN KEY(jail) REFERENCES jails(name) ON DELETE CASCADE, " \
			"UNIQUE(jail, path)," \
			"UNIQUE(jail, path, firstlinemd5)" \
			");" \
			"CREATE INDEX logs_path ON logs(path);" \
			"CREATE INDEX logs_jail_path ON logs(jail, path);"
			#TODO: systemd journal features \
			#"journalmatch TEXT, " \
			#"journlcursor TEXT, " \
			#"lastfiletime INTEGER DEFAULT 0, " # is this easily available \
	_TABLE_bans = "CREATE TABLE bans(" \
			"jail TEXT NOT NULL, " \
			"ip TEXT, " \
			"timeofban INTEGER NOT NULL, " \
			"data JSON, " \
			"FOREIGN KEY(jail) REFERENCES jails(name) " \
			");" \
			"CREATE INDEX bans_jail_timeofban_ip ON bans(jail, timeofban);" \
			"CREATE INDEX bans_jail_ip ON bans(jail, ip);" \
			"CREATE INDEX bans_ip ON bans(ip);" \

	def __init__(self, filename, purgeAge=24*60*60):
		try:
			self._lock = Lock()
			self._db = sqlite3.connect(
				filename, check_same_thread=False,
				detect_types=sqlite3.PARSE_DECLTYPES)
			self._dbFilename = filename
			self._purgeAge = purgeAge

			self._bansMergedCache = {}

			logSys.info(
				"Connected to fail2ban persistent database '%s'", filename)
		except sqlite3.OperationalError, e:
			logSys.error(
				"Error connecting to fail2ban persistent database '%s': %s",
				filename, e.args[0])
			raise

		cur = self._db.cursor()
		cur.execute("PRAGMA foreign_keys = ON;")

		try:
			cur.execute("SELECT version FROM fail2banDb LIMIT 1")
		except sqlite3.OperationalError:
			logSys.warning("New database created. Version '%i'",
				self.createDb())
		else:
			version = cur.fetchone()[0]
			if version < Fail2BanDb.__version__:
				newversion = self.updateDb(version)
				if newversion == Fail2BanDb.__version__:
					logSys.warning( "Database updated from '%i' to '%i'",
						version, newversion)
				else:
					logSys.error( "Database update failed to achieve version '%i'"
						": updated from '%i' to '%i'",
						Fail2BanDb.__version__, version, newversion)
					raise RuntimeError('Failed to fully update')
		finally:
			cur.close()

	@property
	def filename(self):
		"""File name of SQLite3 database file.
		"""
		return self._dbFilename

	@property
	def purgeage(self):
		"""Purge age in seconds.
		"""
		return self._purgeAge

	@purgeage.setter
	def purgeage(self, value):
		self._purgeAge = int(value)

	@commitandrollback
	def createDb(self, cur):
		"""Creates a new database, called during initialisation.
		"""
		# Version info
		cur.executescript(Fail2BanDb._TABLE_fail2banDb)
		cur.execute("INSERT INTO fail2banDb(version) VALUES(?)",
			(Fail2BanDb.__version__, ))
		# Jails
		cur.executescript(Fail2BanDb._TABLE_jails)
		# Logs
		cur.executescript(Fail2BanDb._TABLE_logs)
		# Bans
		cur.executescript(Fail2BanDb._TABLE_bans)

		cur.execute("SELECT version FROM fail2banDb LIMIT 1")
		return cur.fetchone()[0]

	@commitandrollback
	def updateDb(self, cur, version):
		"""Update an existing database, called during initialisation.

		A timestamped backup is also created prior to attempting the update.
		"""
		self._dbBackupFilename = self.filename + '.' + time.strftime('%Y%m%d-%H%M%S', MyTime.gmtime())
		shutil.copyfile(self.filename, self._dbBackupFilename)
		logSys.info("Database backup created: %s", self._dbBackupFilename)
		if version > Fail2BanDb.__version__:
			raise NotImplementedError(
						"Attempt to travel to future version of database ...how did you get here??")

		if version < 2:
			cur.executescript("BEGIN TRANSACTION;"
						"CREATE TEMPORARY TABLE logs_temp AS SELECT * FROM logs;"
						"DROP TABLE logs;"
						"%s;"
						"INSERT INTO logs SELECT * from logs_temp;"
						"DROP TABLE logs_temp;"
						"UPDATE fail2banDb SET version = 2;"
						"COMMIT;" % Fail2BanDb._TABLE_logs)

		cur.execute("SELECT version FROM fail2banDb LIMIT 1")
		return cur.fetchone()[0]

	@commitandrollback
	def addJail(self, cur, jail):
		"""Adds a jail to the database.

		Parameters
		----------
		jail : Jail
			Jail to be added to the database.
		"""
		cur.execute(
			"INSERT OR REPLACE INTO jails(name, enabled) VALUES(?, 1)",
			(jail.name,))

	@commitandrollback
	def delJail(self, cur, jail):
		"""Deletes a jail from the database.

		Parameters
		----------
		jail : Jail
			Jail to be removed from the database.
		"""
		# Will be deleted by purge as appropriate
		cur.execute(
			"UPDATE jails SET enabled=0 WHERE name=?", (jail.name, ))

	@commitandrollback
	def delAllJails(self, cur):
		"""Deletes all jails from the database.
		"""
		# Will be deleted by purge as appropriate
		cur.execute("UPDATE jails SET enabled=0")

	@commitandrollback
	def getJailNames(self, cur):
		"""Get name of jails in database.

		Currently only used for testing purposes.

		Returns
		-------
		set
			Set of jail names.
		"""
		cur.execute("SELECT name FROM jails")
		return set(row[0] for row in cur.fetchmany())

	@commitandrollback
	def addLog(self, cur, jail, container):
		"""Adds a log to the database.

		Parameters
		----------
		jail : Jail
			Jail that log is being monitored by.
		container : FileContainer
			File container of the log file being added.

		Returns
		-------
		int
			If log was already present in database, value of last position
			in the log file; else `None`
		"""
		lastLinePos = None
		cur.execute(
			"SELECT firstlinemd5, lastfilepos FROM logs "
				"WHERE jail=? AND path=?",
			(jail.name, container.getFileName()))
		try:
			firstLineMD5, lastLinePos = cur.fetchone()
		except TypeError:
			firstLineMD5 = False

		cur.execute(
				"INSERT OR REPLACE INTO logs(jail, path, firstlinemd5, lastfilepos) "
					"VALUES(?, ?, ?, ?)",
				(jail.name, container.getFileName(),
					container.getHash(), container.getPos()))
		if container.getHash() != firstLineMD5:
			lastLinePos = None
		return lastLinePos

	@commitandrollback
	def getLogPaths(self, cur, jail=None):
		"""Gets all the log paths from the database.

		Currently only for testing purposes.

		Parameters
		----------
		jail : Jail
			If specified, will only reutrn logs belonging to the jail.

		Returns
		-------
		set
			Set of log paths.
		"""
		query = "SELECT path FROM logs"
		queryArgs = []
		if jail is not None:
			query += " WHERE jail=?"
			queryArgs.append(jail.name)
		cur.execute(query, queryArgs)
		return set(row[0] for row in cur.fetchmany())

	@commitandrollback
	def updateLog(self, cur, *args, **kwargs):
		"""Updates hash and last position in log file.

		Parameters
		----------
		jail : Jail
			Jail of which the log file belongs to.
		container : FileContainer
			File container of the log file being updated.
		"""
		self._updateLog(cur, *args, **kwargs)

	def _updateLog(self, cur, jail, container):
		cur.execute(
			"UPDATE logs SET firstlinemd5=?, lastfilepos=? "
				"WHERE jail=? AND path=?",
			(container.getHash(), container.getPos(),
				jail.name, container.getFileName()))

	@commitandrollback
	def addBan(self, cur, jail, ticket):
		"""Add a ban to the database.

		Parameters
		----------
		jail : Jail
			Jail in which the ban has occurred.
		ticket : BanTicket
			Ticket of the ban to be added.
		"""
		try:
			del self._bansMergedCache[(ticket.getIP(), jail)]
		except KeyError:
			pass
		#TODO: Implement data parts once arbitrary match keys completed
		cur.execute(
			"INSERT INTO bans(jail, ip, timeofban, data) VALUES(?, ?, ?, ?)",
			(jail.name, ticket.getIP(), ticket.getTime(),
				{"matches": ticket.getMatches(),
					"failures": ticket.getAttempt()}))

	@commitandrollback
	def _getBans(self, cur, jail=None, bantime=None, ip=None):
		query = "SELECT ip, timeofban, data FROM bans WHERE 1"
		queryArgs = []

		if jail is not None:
			query += " AND jail=?"
			queryArgs.append(jail.name)
		if bantime is not None and bantime >= 0:
			query += " AND timeofban > ?"
			queryArgs.append(MyTime.time() - bantime)
		if ip is not None:
			query += " AND ip=?"
			queryArgs.append(ip)
		query += " ORDER BY ip, timeofban"

		return cur.execute(query, queryArgs)

	def getBans(self, **kwargs):
		"""Get bans from the database.

		Parameters
		----------
		jail : Jail
			Jail that the ban belongs to. Default `None`; all jails.
		bantime : int
			Ban time in seconds, such that bans returned would still be
			valid now.  Negative values are equivalent to `None`.
			Default `None`; no limit.
		ip : str
			IP Address to filter bans by. Default `None`; all IPs.

		Returns
		-------
		list
			List of `Ticket`s for bans stored in database.
		"""
		tickets = []
		for ip, timeofban, data in self._getBans(**kwargs):
			#TODO: Implement data parts once arbitrary match keys completed
			tickets.append(FailTicket(ip, timeofban, data['matches']))
			tickets[-1].setAttempt(data['failures'])
		return tickets

	def getBansMerged(self, ip=None, jail=None, bantime=None):
		"""Get bans from the database, merged into single ticket.

		This is the same as `getBans`, but bans merged into single
		ticket.

		Parameters
		----------
		jail : Jail
			Jail that the ban belongs to. Default `None`; all jails.
		bantime : int
			Ban time in seconds, such that bans returned would still be
			valid now. Negative values are equivalent to `None`.
			Default `None`; no limit.
		ip : str
			IP Address to filter bans by. Default `None`; all IPs.

		Returns
		-------
		list or Ticket
			Single ticket representing bans stored in database per IP
			in a list. When `ip` argument passed, a single `Ticket` is
			returned.
		"""
		cacheKey = None
		if bantime is None or bantime < 0:
			cacheKey = (ip, jail)
			if cacheKey in self._bansMergedCache:
				return self._bansMergedCache[cacheKey]

		tickets = []
		ticket = None

		results = list(self._getBans(ip=ip, jail=jail, bantime=bantime))
		if results:
			prev_banip = results[0][0]
			matches = []
			failures = 0
			for banip, timeofban, data in results:
				#TODO: Implement data parts once arbitrary match keys completed
				if banip != prev_banip:
					ticket = FailTicket(prev_banip, prev_timeofban, matches)
					ticket.setAttempt(failures)
					tickets.append(ticket)
					# Reset variables
					prev_banip = banip
					matches = []
					failures = 0
				matches.extend(data['matches'])
				failures += data['failures']
				prev_timeofban = timeofban
			ticket = FailTicket(banip, prev_timeofban, matches)
			ticket.setAttempt(failures)
			tickets.append(ticket)

		if cacheKey:
			self._bansMergedCache[cacheKey] = tickets if ip is None else ticket
		return tickets if ip is None else ticket

	@commitandrollback
	def purge(self, cur):
		"""Purge old bans, jails and log files from database.
		"""
		self._bansMergedCache = {}
		cur.execute(
			"DELETE FROM bans WHERE timeofban < ?",
			(MyTime.time() - self._purgeAge, ))
		cur.execute(
			"DELETE FROM jails WHERE enabled = 0 "
				"AND NOT EXISTS(SELECT * FROM bans WHERE jail = jails.name)")


########NEW FILE########
__FILENAME__ = datedetector
# emacs: -*- mode: python; py-indent-offset: 4; indent-tabs-mode: t -*-
# vi: set ft=python sts=4 ts=4 sw=4 noet :

# This file is part of Fail2Ban.
#
# Fail2Ban is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# Fail2Ban is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with Fail2Ban; if not, write to the Free Software
# Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA  02110-1301, USA.

__author__ = "Cyril Jaquier and Fail2Ban Contributors"
__copyright__ = "Copyright (c) 2004 Cyril Jaquier"
__license__ = "GPL"

import logging
from threading import Lock

from .datetemplate import DatePatternRegex, DateTai64n, DateEpoch

# Gets the instance of the logger.
logSys = logging.getLogger(__name__)

class DateDetector(object):
	"""Manages one or more date templates to find a date within a log line.

	Attributes
	----------
	templates
	"""

	def __init__(self):
		self.__lock = Lock()
		self.__templates = list()
		self.__known_names = set()

	def _appendTemplate(self, template):
		name = template.name
		if name in self.__known_names:
			raise ValueError(
				"There is already a template with name %s" % name)
		self.__known_names.add(name)
		self.__templates.append(template)

	def appendTemplate(self, template):
		"""Add a date template to manage and use in search of dates.

		Parameters
		----------
		template : DateTemplate or str
			Can be either a `DateTemplate` instance, or a string which will
			be used as the pattern for the `DatePatternRegex` template. The
			template will then be added to the detector.

		Raises
		------
		ValueError
			If a template already exists with the same name.
		"""
		if isinstance(template, str):
			template = DatePatternRegex(template)
		self._appendTemplate(template)

	def addDefaultTemplate(self):
		"""Add Fail2Ban's default set of date templates.
		"""
		self.__lock.acquire()
		try:
			# asctime with optional day, subsecond and/or year:
			# Sun Jan 23 21:59:59.011 2005 
			self.appendTemplate("(?:%a )?%b %d %H:%M:%S(?:\.%f)?(?: %Y)?")
			# simple date, optional subsecond (proftpd):
			# 2005-01-23 21:59:59 
			# simple date: 2005/01/23 21:59:59 
			# custom for syslog-ng 2006.12.21 06:43:20
			self.appendTemplate("%Y(?P<_sep>[-/.])%m(?P=_sep)%d %H:%M:%S(?:,%f)?")
			# simple date too (from x11vnc): 23/01/2005 21:59:59 
			# and with optional year given by 2 digits: 23/01/05 21:59:59 
			# (See http://bugs.debian.org/537610)
			# 17-07-2008 17:23:25
			self.appendTemplate("%d(?P<_sep>[-/])%m(?P=_sep)(?:%Y|%y) %H:%M:%S")
			# Apache format optional time zone:
			# [31/Oct/2006:09:22:55 -0000]
			# 26-Jul-2007 15:20:52
			self.appendTemplate("%d(?P<_sep>[-/])%b(?P=_sep)%Y[ :]?%H:%M:%S(?:\.%f)?(?: %z)?")
			# CPanel 05/20/2008:01:57:39
			self.appendTemplate("%m/%d/%Y:%H:%M:%S")
			# named 26-Jul-2007 15:20:52.252 
			# roundcube 26-Jul-2007 15:20:52 +0200
			# 01-27-2012 16:22:44.252
			# subseconds explicit to avoid possible %m<->%d confusion
			# with previous
			self.appendTemplate("%m-%d-%Y %H:%M:%S\.%f")
			# TAI64N
			template = DateTai64n()
			template.name = "TAI64N"
			self.appendTemplate(template)
			# Epoch
			template = DateEpoch()
			template.name = "Epoch"
			self.appendTemplate(template)
			# ISO 8601
			self.appendTemplate("%Y-%m-%d[T ]%H:%M:%S(?:\.%f)?(?:%z)?")
			# Only time information in the log
			self.appendTemplate("^%H:%M:%S")
			# <09/16/08@05:03:30>
			self.appendTemplate("^<%m/%d/%y@%H:%M:%S>")
			# MySQL: 130322 11:46:11
			self.appendTemplate("^%y%m%d  ?%H:%M:%S")
			# Apache Tomcat
			self.appendTemplate("%b %d, %Y %I:%M:%S %p")
			# ASSP: Apr-27-13 02:33:06
			self.appendTemplate("^%b-%d-%y %H:%M:%S")
		finally:
			self.__lock.release()

	@property
	def templates(self):
		"""List of template instances managed by the detector.
		"""
		return self.__templates

	def matchTime(self, line):
		"""Attempts to find date on a log line using templates.

		This uses the templates' `matchDate` method in an attempt to find
		a date. It also increments the match hit count for the winning
		template.

		Parameters
		----------
		line : str
			Line which is searched by the date templates.

		Returns
		-------
		re.MatchObject
			The regex match returned from the first successfully matched
			template.
		"""
		self.__lock.acquire()
		try:
			for template in self.__templates:
				match = template.matchDate(line)
				if not match is None:
					logSys.debug("Matched time template %s" % template.name)
					template.hits += 1
					return match
			return None
		finally:
			self.__lock.release()

	def getTime(self, line):
		"""Attempts to return the date on a log line using templates.

		This uses the templates' `getDate` method in an attempt to find
		a date.

		Parameters
		----------
		line : str
			Line which is searched by the date templates.

		Returns
		-------
		float
			The Unix timestamp returned from the first successfully matched
			template.
		"""
		self.__lock.acquire()
		try:
			for template in self.__templates:
				try:
					date = template.getDate(line)
					if date is None:
						continue
					logSys.debug("Got time %f for \"%r\" using template %s" %
						(date[0], date[1].group(), template.name))
					return date
				except ValueError:
					pass
			return None
		finally:
			self.__lock.release()

	def sortTemplate(self):
		"""Sort the date templates by number of hits

		Sort the template lists using the hits score. This method is not
		called in this object and thus should be called from time to time.
		This ensures the most commonly matched templates are checked first,
		improving performance of matchTime and getTime.
		"""
		self.__lock.acquire()
		try:
			logSys.debug("Sorting the template list")
			self.__templates.sort(key=lambda x: x.hits, reverse=True)
			t = self.__templates[0]
			logSys.debug("Winning template: %s with %d hits" % (t.name, t.hits))
		finally:
			self.__lock.release()

########NEW FILE########
__FILENAME__ = datetemplate
# emacs: -*- mode: python; coding: utf-8; py-indent-offset: 4; indent-tabs-mode: t -*-
# vi: set ft=python sts=4 ts=4 sw=4 noet :

# This file is part of Fail2Ban.
#
# Fail2Ban is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# Fail2Ban is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with Fail2Ban; if not, write to the Free Software
# Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA  02110-1301, USA.

# Author: Cyril Jaquier
# 

__author__ = "Cyril Jaquier"
__copyright__ = "Copyright (c) 2004 Cyril Jaquier"
__license__ = "GPL"

import re
import logging
from abc import abstractmethod

from .strptime import reGroupDictStrptime, timeRE

logSys = logging.getLogger(__name__)


class DateTemplate(object):
	"""A template which searches for and returns a date from a log line.

	This is an not functional abstract class which other templates should
	inherit from.

	Attributes
	----------
	name
	regex
	"""

	def __init__(self):
		self._name = ""
		self._regex = ""
		self._cRegex = None
		self.hits = 0

	@property
	def name(self):
		"""Name assigned to template.
		"""
		return self._name

	@name.setter
	def name(self, name):
		self._name = name

	def getRegex(self):
		return self._regex

	def setRegex(self, regex, wordBegin=True):
		"""Sets regex to use for searching for date in log line.

		Parameters
		----------
		regex : str
			The regex the template will use for searching for a date.
		wordBegin : bool
			Defines whether the regex should be modified to search at
			beginning of a word, by adding "\\b" to start of regex.
			Default True.

		Raises
		------
		re.error
			If regular expression fails to compile
		"""
		regex = regex.strip()
		if (wordBegin and not re.search(r'^\^', regex)):
			regex = r'\b' + regex
		self._regex = regex
		self._cRegex = re.compile(regex, re.UNICODE | re.IGNORECASE)

	regex = property(getRegex, setRegex, doc=
		"""Regex used to search for date.
		""")

	def matchDate(self, line):
		"""Check if regex for date matches on a log line.
		"""
		dateMatch = self._cRegex.search(line)
		return dateMatch

	@abstractmethod
	def getDate(self, line):
		"""Abstract method, which should return the date for a log line

		This should return the date for a log line, typically taking the
		date from the part of the line which matched the templates regex.
		This requires abstraction, therefore just raises exception.

		Parameters
		----------
		line : str
			Log line, of which the date should be extracted from.

		Raises
		------
		NotImplementedError
			Abstract method, therefore always returns this.
		"""
		raise NotImplementedError("getDate() is abstract")


class DateEpoch(DateTemplate):
	"""A date template which searches for Unix timestamps.

	This includes Unix timestamps which appear at start of a line, optionally
	within square braces (nsd), or on SELinux audit log lines.

	Attributes
	----------
	name
	regex
	"""

	def __init__(self):
		DateTemplate.__init__(self)
		self.regex = "(?:^|(?P<square>(?<=^\[))|(?P<selinux>(?<=audit\()))\d{10}(?:\.\d{3,6})?(?(selinux)(?=:\d+\))(?(square)(?=\])))"

	def getDate(self, line):
		"""Method to return the date for a log line.

		Parameters
		----------
		line : str
			Log line, of which the date should be extracted from.

		Returns
		-------
		(float, str)
			Tuple containing a Unix timestamp, and the string of the date
			which was matched and in turned used to calculated the timestamp.
		"""
		dateMatch = self.matchDate(line)
		if dateMatch:
			# extract part of format which represents seconds since epoch
			return (float(dateMatch.group()), dateMatch)
		return None

class DatePatternRegex(DateTemplate):
	"""Date template, with regex/pattern

	Parameters
	----------
	pattern : str
		Sets the date templates pattern.

	Attributes
	----------
	name
	regex
	pattern
	"""
	_patternRE = r"%%(%%|[%s])" % "".join(timeRE.keys())
	_patternName = {
		'a': "DAY", 'A': "DAYNAME", 'b': "MON", 'B': "MONTH", 'd': "Day",
		'H': "24hour", 'I': "12hour", 'j': "Yearday", 'm': "Month",
		'M': "Minute", 'p': "AMPM", 'S': "Second", 'U': "Yearweek",
		'w': "Weekday", 'W': "Yearweek", 'y': 'Year2', 'Y': "Year", '%': "%",
		'z': "Zone offset", 'f': "Microseconds", 'Z': "Zone name"}
	for _key in set(timeRE) - set(_patternName): # may not have them all...
		_patternName[_key] = "%%%s" % _key

	def __init__(self, pattern=None):
		super(DatePatternRegex, self).__init__()
		self._pattern = None
		if pattern is not None:
			self.pattern = pattern

	@property
	def pattern(self):
		"""The pattern used for regex with strptime "%" time fields.

		This should be a valid regular expression, of which matching string
		will be extracted from the log line. strptime style "%" fields will
		be replaced by appropriate regular expressions, or custom regex
		groups with names as per the strptime fields can also be used
		instead.
		"""
		return self._pattern

	@pattern.setter
	def pattern(self, pattern):
		self._pattern = pattern
		self._name = re.sub(
			self._patternRE, r'%(\1)s', pattern) % self._patternName
		super(DatePatternRegex, self).setRegex(
			re.sub(self._patternRE, r'%(\1)s', pattern) % timeRE)

	def setRegex(self, value):
		raise NotImplementedError("Regex derived from pattern")

	@DateTemplate.name.setter
	def name(self, value):
		raise NotImplementedError("Name derived from pattern")

	def getDate(self, line):
		"""Method to return the date for a log line.

		This uses a custom version of strptime, using the named groups
		from the instances `pattern` property.

		Parameters
		----------
		line : str
			Log line, of which the date should be extracted from.

		Returns
		-------
		(float, str)
			Tuple containing a Unix timestamp, and the string of the date
			which was matched and in turned used to calculated the timestamp.
		"""
		dateMatch = self.matchDate(line)
		if dateMatch:
			groupdict = dict(
				(key, value)
				for key, value in dateMatch.groupdict().iteritems()
				if value is not None)
			return reGroupDictStrptime(groupdict), dateMatch

class DateTai64n(DateTemplate):
	"""A date template which matches TAI64N formate timestamps.

	Attributes
	----------
	name
	regex
	"""

	def __init__(self):
		DateTemplate.__init__(self)
		# We already know the format for TAI64N
		# yoh: we should not add an additional front anchor
		self.setRegex("@[0-9a-f]{24}", wordBegin=False)

	def getDate(self, line):
		"""Method to return the date for a log line.

		Parameters
		----------
		line : str
			Log line, of which the date should be extracted from.

		Returns
		-------
		(float, str)
			Tuple containing a Unix timestamp, and the string of the date
			which was matched and in turned used to calculated the timestamp.
		"""
		dateMatch = self.matchDate(line)
		if dateMatch:
			# extract part of format which represents seconds since epoch
			value = dateMatch.group()
			seconds_since_epoch = value[2:17]
			# convert seconds from HEX into local time stamp
			return (int(seconds_since_epoch, 16), dateMatch)
		return None

########NEW FILE########
__FILENAME__ = faildata
# emacs: -*- mode: python; py-indent-offset: 4; indent-tabs-mode: t -*-
# vi: set ft=python sts=4 ts=4 sw=4 noet :

# This file is part of Fail2Ban.
#
# Fail2Ban is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# Fail2Ban is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with Fail2Ban; if not, write to the Free Software
# Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA  02110-1301, USA.

# Author: Cyril Jaquier
# 

__author__ = "Cyril Jaquier"
__copyright__ = "Copyright (c) 2004 Cyril Jaquier"
__license__ = "GPL"

import logging

# Gets the instance of the logger.
logSys = logging.getLogger(__name__)

class FailData:
	
	def __init__(self):
		self.__retry = 0
		self.__lastTime = 0
		self.__lastReset = 0
		self.__matches = []

	def setRetry(self, value):
		self.__retry = value
		# keep only the last matches or reset entirely
		# Explicit if/else for compatibility with Python 2.4
		if value:
			self.__matches = self.__matches[-min(len(self.__matches, value)):]
		else:
			self.__matches = []

	def getRetry(self):
		return self.__retry

	def getMatches(self):
		return self.__matches

	def inc(self, matches=None):
		self.__retry += 1
		self.__matches += matches or []

	def setLastTime(self, value):
		if value > self.__lastTime:
			self.__lastTime = value
	
	def getLastTime(self):
		return self.__lastTime

	def getLastReset(self):
		return self.__lastReset

	def setLastReset(self, value):
		self.__lastReset = value

########NEW FILE########
__FILENAME__ = failmanager
# emacs: -*- mode: python; py-indent-offset: 4; indent-tabs-mode: t -*-
# vi: set ft=python sts=4 ts=4 sw=4 noet :

# This file is part of Fail2Ban.
#
# Fail2Ban is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# Fail2Ban is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with Fail2Ban; if not, write to the Free Software
# Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA  02110-1301, USA.

# Author: Cyril Jaquier
# 

__author__ = "Cyril Jaquier"
__copyright__ = "Copyright (c) 2004 Cyril Jaquier"
__license__ = "GPL"

from threading import Lock
import logging

from .faildata import FailData
from .ticket import FailTicket

# Gets the instance of the logger.
logSys = logging.getLogger(__name__)

class FailManager:
	
	def __init__(self):
		self.__lock = Lock()
		self.__failList = dict()
		self.__maxRetry = 3
		self.__maxTime = 600
		self.__failTotal = 0
	
	def setFailTotal(self, value):
		try:
			self.__lock.acquire()
			self.__failTotal = value
		finally:
			self.__lock.release()
		
	def getFailTotal(self):
		try:
			self.__lock.acquire()
			return self.__failTotal
		finally:
			self.__lock.release()
	
	def setMaxRetry(self, value):
		try:
			self.__lock.acquire()
			self.__maxRetry = value
		finally:
			self.__lock.release()
	
	def getMaxRetry(self):
		try:
			self.__lock.acquire()
			return self.__maxRetry
		finally:
			self.__lock.release()
	
	def setMaxTime(self, value):
		try:
			self.__lock.acquire()
			self.__maxTime = value
		finally:
			self.__lock.release()
	
	def getMaxTime(self):
		try:
			self.__lock.acquire()
			return self.__maxTime
		finally:
			self.__lock.release()

	def addFailure(self, ticket):
		try:
			self.__lock.acquire()
			ip = ticket.getIP()
			unixTime = ticket.getTime()
			matches = ticket.getMatches()
			if self.__failList.has_key(ip):
				fData = self.__failList[ip]
				if fData.getLastReset() < unixTime - self.__maxTime:
					fData.setLastReset(unixTime)
					fData.setRetry(0)
				fData.inc(matches)
				fData.setLastTime(unixTime)
			else:
				fData = FailData()
				fData.inc(matches)
				fData.setLastReset(unixTime)
				fData.setLastTime(unixTime)
				self.__failList[ip] = fData

			self.__failTotal += 1

			if logSys.getEffectiveLevel() <= logging.DEBUG:
				# yoh: Since composing this list might be somewhat time consuming
				# in case of having many active failures, it should be ran only
				# if debug level is "low" enough
				failures_summary = ', '.join(['%s:%d' % (k, v.getRetry())
											  for k,v in  self.__failList.iteritems()])
				logSys.debug("Total # of detected failures: %d. Current failures from %d IPs (IP:count): %s"
							 % (self.__failTotal, len(self.__failList), failures_summary))
		finally:
			self.__lock.release()
	
	def size(self):
		try:
			self.__lock.acquire()
			return len(self.__failList)
		finally:
			self.__lock.release()
	
	def cleanup(self, time):
		try:
			self.__lock.acquire()
			tmp = self.__failList.copy()
			for item in tmp:
				if tmp[item].getLastTime() < time - self.__maxTime:
					self.__delFailure(item)
		finally:
			self.__lock.release()
	
	def __delFailure(self, ip):
		if self.__failList.has_key(ip):
			del self.__failList[ip]
	
	def toBan(self):
		try:
			self.__lock.acquire()
			for ip in self.__failList:
				data = self.__failList[ip]
				if data.getRetry() >= self.__maxRetry:
					self.__delFailure(ip)
					# Create a FailTicket from BanData
					failTicket = FailTicket(ip, data.getLastTime(), data.getMatches())
					failTicket.setAttempt(data.getRetry())
					return failTicket
			raise FailManagerEmpty
		finally:
			self.__lock.release()

class FailManagerEmpty(Exception):
	pass

########NEW FILE########
__FILENAME__ = failregex
# emacs: -*- mode: python; py-indent-offset: 4; indent-tabs-mode: t -*-
# vi: set ft=python sts=4 ts=4 sw=4 noet :

# This file is part of Fail2Ban.
#
# Fail2Ban is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# Fail2Ban is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with Fail2Ban; if not, write to the Free Software
# Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA  02110-1301, USA.

__author__ = "Cyril Jaquier"
__copyright__ = "Copyright (c) 2004 Cyril Jaquier"
__license__ = "GPL"

import re, sre_constants, sys

##
# Regular expression class.
#
# This class represents a regular expression with its compiled version.

class Regex:

	##
	# Constructor.
	#
	# Creates a new object. This method can throw RegexException in order to
	# avoid construction of invalid object.
	# @param value the regular expression
	
	def __init__(self, regex):
		self._matchCache = None
		# Perform shortcuts expansions.
		# Replace "<HOST>" with default regular expression for host.
		regex = regex.replace("<HOST>", "(?:::f{4,6}:)?(?P<host>[\w\-.^_]*\w)")
		# Replace "<SKIPLINES>" with regular expression for multiple lines.
		regexSplit = regex.split("<SKIPLINES>")
		regex = regexSplit[0]
		for n, regexLine in enumerate(regexSplit[1:]):
			regex += "\n(?P<skiplines%i>(?:(.*\n)*?))" % n + regexLine
		if regex.lstrip() == '':
			raise RegexException("Cannot add empty regex")
		try:
			self._regexObj = re.compile(regex, re.MULTILINE)
			self._regex = regex
		except sre_constants.error:
			raise RegexException("Unable to compile regular expression '%s'" %
								 regex)
	def __str__(self):
		return "%s(%r)" % (self.__class__.__name__, self._regex)
	##
	# Gets the regular expression.
	#
	# The effective regular expression used is returned.
	# @return the regular expression
	
	def getRegex(self):
		return self._regex
	
	##
	# Searches the regular expression.
	#
	# Sets an internal cache (match object) in order to avoid searching for
	# the pattern again. This method must be called before calling any other
	# method of this object.
	# @param a list of tupples. The tupples are ( prematch, datematch, postdatematch )
	
	def search(self, tupleLines):
		self._matchCache = self._regexObj.search(
			"\n".join("".join(value[::2]) for value in tupleLines) + "\n")
		if self.hasMatched():
			# Find start of the first line where the match was found
			try:
				self._matchLineStart = self._matchCache.string.rindex(
					"\n", 0, self._matchCache.start() +1 ) + 1
			except ValueError:
				self._matchLineStart = 0
			# Find end of the last line where the match was found
			try:
				self._matchLineEnd = self._matchCache.string.index(
					"\n", self._matchCache.end() - 1) + 1
			except ValueError:
				self._matchLineEnd = len(self._matchCache.string)


			lineCount1 = self._matchCache.string.count(
				"\n", 0, self._matchLineStart)
			lineCount2 = self._matchCache.string.count(
				"\n", 0, self._matchLineEnd)
			self._matchedTupleLines = tupleLines[lineCount1:lineCount2]
			self._unmatchedTupleLines = tupleLines[:lineCount1]

			n = 0
			for skippedLine in self.getSkippedLines():
				for m, matchedTupleLine in enumerate(
					self._matchedTupleLines[n:]):
					if "".join(matchedTupleLine[::2]) == skippedLine:
						self._unmatchedTupleLines.append(
							self._matchedTupleLines.pop(n+m))
						n += m
						break
			self._unmatchedTupleLines.extend(tupleLines[lineCount2:])

	# Checks if the previous call to search() matched.
	#
	# @return True if a match was found, False otherwise
	
	def hasMatched(self):
		if self._matchCache:
			return True
		else:
			return False

	##
	# Returns skipped lines.
	#
	# This returns skipped lines captured by the <SKIPLINES> tag.
	# @return list of skipped lines
	
	def getSkippedLines(self):
		if not self._matchCache:
			return []
		skippedLines = ""
		n = 0
		while True:
			try:
				if self._matchCache.group("skiplines%i" % n) is not None:
					skippedLines += self._matchCache.group("skiplines%i" % n)
				n += 1
			except IndexError:
				break
			# KeyError is because of PyPy issue1665 affecting pypy <= 2.2.1 
			except KeyError:
				if 'PyPy' not in sys.version: # pragma: no cover - not sure this is even reachable
					raise
				break
		return skippedLines.splitlines(False)

	##
	# Returns unmatched lines.
	#
	# This returns unmatched lines including captured by the <SKIPLINES> tag.
	# @return list of unmatched lines

	def getUnmatchedTupleLines(self):
		if not self.hasMatched():
			return []
		else:
			return self._unmatchedTupleLines

	def getUnmatchedLines(self):
		if not self.hasMatched():
			return []
		else:
			return ["".join(line) for line in self._unmatchedTupleLines]

	##
	# Returns matched lines.
	#
	# This returns matched lines by excluding those captured
	# by the <SKIPLINES> tag.
	# @return list of matched lines

	def getMatchedTupleLines(self):
		if not self.hasMatched():
			return []
		else:
			return self._matchedTupleLines

	def getMatchedLines(self):
		if not self.hasMatched():
			return []
		else:
			return ["".join(line) for line in self._matchedTupleLines]

##
# Exception dedicated to the class Regex.

class RegexException(Exception):
	pass


##
# Regular expression class.
#
# This class represents a regular expression with its compiled version.

class FailRegex(Regex):

	##
	# Constructor.
	#
	# Creates a new object. This method can throw RegexException in order to
	# avoid construction of invalid object.
	# @param value the regular expression
	
	def __init__(self, regex):
		# Initializes the parent.
		Regex.__init__(self, regex)
		# Check for group "host"
		if "host" not in self._regexObj.groupindex:
			raise RegexException("No 'host' group in '%s'" % self._regex)
	
	##
	# Returns the matched host.
	#
	# This corresponds to the pattern matched by the named group "host".
	# @return the matched host
	
	def getHost(self):
		host = self._matchCache.group("host")
		if host is None:
			# Gets a few information.
			s = self._matchCache.string
			r = self._matchCache.re
			raise RegexException("No 'host' found in '%s' using '%s'" % (s, r))
		return str(host)

########NEW FILE########
__FILENAME__ = filter
# emacs: -*- mode: python; py-indent-offset: 4; indent-tabs-mode: t -*-
# vi: set ft=python sts=4 ts=4 sw=4 noet :

# This file is part of Fail2Ban.
#
# Fail2Ban is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# Fail2Ban is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with Fail2Ban; if not, write to the Free Software
# Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA  02110-1301, USA.

__author__ = "Cyril Jaquier and Fail2Ban Contributors"
__copyright__ = "Copyright (c) 2004 Cyril Jaquier, 2011-2013 Yaroslav Halchenko"
__license__ = "GPL"

import logging, re, os, fcntl, sys, locale, codecs

from .failmanager import FailManagerEmpty, FailManager
from .ticket import FailTicket
from .jailthread import JailThread
from .datedetector import DateDetector
from .datetemplate import DatePatternRegex, DateEpoch, DateTai64n
from .mytime import MyTime
from .failregex import FailRegex, Regex, RegexException
from .action import CommandAction

# Gets the instance of the logger.
logSys = logging.getLogger(__name__)

##
# Log reader class.
#
# This class reads a log file and detects login failures or anything else
# that matches a given regular expression. This class is instantiated by
# a Jail object.

class Filter(JailThread):

	##
	# Constructor.
	#
	# Initialize the filter object with default values.
	# @param jail the jail object

	def __init__(self, jail, useDns='warn'):
		JailThread.__init__(self)
		## The jail which contains this filter.
		self.jail = jail
		## The failures manager.
		self.failManager = FailManager()
		## The regular expression list matching the failures.
		self.__failRegex = list()
		## The regular expression list with expressions to ignore.
		self.__ignoreRegex = list()
		## Use DNS setting
		self.setUseDns(useDns)
		## The amount of time to look back.
		self.__findTime = 600
		## The ignore IP list.
		self.__ignoreIpList = []
		## Size of line buffer
		self.__lineBufferSize = 1
		## Line buffer
		self.__lineBuffer = []
		## Store last time stamp, applicable for multi-line
		self.__lastTimeText = ""
		self.__lastDate = None
		## External command
		self.__ignoreCommand = False

		self.dateDetector = DateDetector()
		self.dateDetector.addDefaultTemplate()
		logSys.debug("Created %s" % self)


	def __repr__(self):
		return "%s(%r)" % (self.__class__.__name__, self.jail)

	##
	# Add a regular expression which matches the failure.
	#
	# The regular expression can also match any other pattern than failures
	# and thus can be used for many purporse.
	# @param value the regular expression

	def addFailRegex(self, value):
		try:
			regex = FailRegex(value)
			self.__failRegex.append(regex)
			if "\n" in regex.getRegex() and not self.getMaxLines() > 1:
				logSys.warning(
					"Mutliline regex set for jail '%s' "
					"but maxlines not greater than 1")
		except RegexException, e:
			logSys.error(e)
			raise e


	def delFailRegex(self, index):
		try:
			del self.__failRegex[index]
		except IndexError:
			logSys.error("Cannot remove regular expression. Index %d is not "
						 "valid" % index)

	##
	# Get the regular expression which matches the failure.
	#
	# @return the regular expression

	def getFailRegex(self):
		failRegex = list()
		for regex in self.__failRegex:
			failRegex.append(regex.getRegex())
		return failRegex

	##
	# Add the regular expression which matches the failure.
	#
	# The regular expression can also match any other pattern than failures
	# and thus can be used for many purpose.
	# @param value the regular expression

	def addIgnoreRegex(self, value):
		try:
			regex = Regex(value)
			self.__ignoreRegex.append(regex)
		except RegexException, e:
			logSys.error(e)
			raise e 

	def delIgnoreRegex(self, index):
		try:
			del self.__ignoreRegex[index]
		except IndexError:
			logSys.error("Cannot remove regular expression. Index %d is not "
						 "valid" % index)

	##
	# Get the regular expression which matches the failure.
	#
	# @return the regular expression

	def getIgnoreRegex(self):
		ignoreRegex = list()
		for regex in self.__ignoreRegex:
			ignoreRegex.append(regex.getRegex())
		return ignoreRegex

	##
	# Set the Use DNS mode
	# @param value the usedns mode

	def setUseDns(self, value):
		if isinstance(value, bool):
			value = {True: 'yes', False: 'no'}[value]
		value = value.lower()			  # must be a string by now
		if not (value in ('yes', 'no', 'warn')):
			logSys.error("Incorrect value %r specified for usedns. "
						 "Using safe 'no'" % (value,))
			value = 'no'
		logSys.debug("Setting usedns = %s for %s" % (value, self))
		self.__useDns = value

	##
	# Get the usedns mode
	# @return the usedns mode

	def getUseDns(self):
		return self.__useDns

	##
	# Set the time needed to find a failure.
	#
	# This value tells the filter how long it has to take failures into
	# account.
	# @param value the time

	def setFindTime(self, value):
		self.__findTime = value
		self.failManager.setMaxTime(value)
		logSys.info("Set findtime = %s" % value)

	##
	# Get the time needed to find a failure.
	#
	# @return the time

	def getFindTime(self):
		return self.__findTime

	##
	# Set the date detector pattern, removing Defaults
	#
	# @param pattern the date template pattern

	def setDatePattern(self, pattern):
		if pattern is None:
			self.dateDetector = None
			return
		elif pattern.upper() == "EPOCH":
			template = DateEpoch()
			template.name = "Epoch"
		elif pattern.upper() == "TAI64N":
			template = DateTai64n()
			template.name = "TAI64N"
		else:
			template = DatePatternRegex(pattern)
		self.dateDetector = DateDetector()
		self.dateDetector.appendTemplate(template)
		logSys.info("Date pattern set to `%r`: `%s`" %
			(pattern, template.name))
		logSys.debug("Date pattern regex for %r: %s" %
			(pattern, template.regex))

	##
	# Get the date detector pattern, or Default Detectors if not changed
	#
	# @return pattern of the date template pattern

	def getDatePattern(self):
		if self.dateDetector is not None:
			templates = self.dateDetector.templates
			if len(templates) > 1:
				return None, "Default Detectors"
			elif len(templates) == 1:
				if hasattr(templates[0], "pattern"):
					pattern =  templates[0].pattern
				else:
					pattern = None
				return pattern, templates[0].name

	##
	# Set the maximum retry value.
	#
	# @param value the retry value

	def setMaxRetry(self, value):
		self.failManager.setMaxRetry(value)
		logSys.info("Set maxRetry = %s" % value)

	##
	# Get the maximum retry value.
	#
	# @return the retry value

	def getMaxRetry(self):
		return self.failManager.getMaxRetry()

	##
	# Set the maximum line buffer size.
	#
	# @param value the line buffer size

	def setMaxLines(self, value):
		if int(value) <= 0:
			raise ValueError("maxlines must be integer greater than zero")
		self.__lineBufferSize = int(value)
		logSys.info("Set maxlines = %i" % self.__lineBufferSize)

	##
	# Get the maximum line buffer size.
	#
	# @return the line buffer size

	def getMaxLines(self):
		return self.__lineBufferSize

	##
	# Main loop.
	#
	# This function is the main loop of the thread. It checks if the
	# file has been modified and looks for failures.
	# @return True when the thread exits nicely

	def run(self): # pragma: no cover
		raise Exception("run() is abstract")

	##
	# Set external command, for ignoredips
	#

	def setIgnoreCommand(self, command):
		self.__ignoreCommand = command

	##
	# Get external command, for ignoredips
	#

	def getIgnoreCommand(self):
		return self.__ignoreCommand

	##
	# Ban an IP - http://blogs.buanzo.com.ar/2009/04/fail2ban-patch-ban-ip-address-manually.html
	# Arturo 'Buanzo' Busleiman <buanzo@buanzo.com.ar>
	#
	# to enable banip fail2ban-client BAN command

	def addBannedIP(self, ip):
		if self.inIgnoreIPList(ip):
			logSys.warning('Requested to manually ban an ignored IP %s. User knows best. Proceeding to ban it.' % ip)

		unixTime = MyTime.time()
		for i in xrange(self.failManager.getMaxRetry()):
			self.failManager.addFailure(FailTicket(ip, unixTime))

		# Perform the banning of the IP now.
		try: # pragma: no branch - exception is the only way out
			while True:
				ticket = self.failManager.toBan()
				self.jail.putFailTicket(ticket)
		except FailManagerEmpty:
			self.failManager.cleanup(MyTime.time())

		return ip

	##
	# Add an IP/DNS to the ignore list.
	#
	# IP addresses in the ignore list are not taken into account
	# when finding failures. CIDR mask and DNS are also accepted.
	# @param ip IP address to ignore

	def addIgnoreIP(self, ip):
		logSys.debug("Add " + ip + " to ignore list")
		self.__ignoreIpList.append(ip)

	def delIgnoreIP(self, ip):
		logSys.debug("Remove " + ip + " from ignore list")
		self.__ignoreIpList.remove(ip)

	def getIgnoreIP(self):
		return self.__ignoreIpList

	##
	# Check if IP address/DNS is in the ignore list.
	#
	# Check if the given IP address matches an IP address/DNS or a CIDR
	# mask in the ignore list.
	# @param ip IP address
	# @return True if IP address is in ignore list

	def inIgnoreIPList(self, ip):
		for i in self.__ignoreIpList:
			# An empty string is always false
			if i == "":
				continue
			s = i.split('/', 1)
			# IP address without CIDR mask
			if len(s) == 1:
				s.insert(1, '32')
			elif "." in s[1]: # 255.255.255.0 style mask
				s[1] = len(re.search(
					"(?<=b)1+", bin(DNSUtils.addr2bin(s[1]))).group())
			s[1] = long(s[1])
			try:
				a = DNSUtils.cidr(s[0], s[1])
				b = DNSUtils.cidr(ip, s[1])
			except Exception:
				# Check if IP in DNS
				ips = DNSUtils.dnsToIp(i)
				if ip in ips:
					return True
				else:
					continue
			if a == b:
				return True

		if self.__ignoreCommand:
			command = CommandAction.replaceTag(self.__ignoreCommand, { 'ip': ip } )
			logSys.debug('ignore command: ' + command)
			return CommandAction.executeCmd(command)

		return False


	def processLine(self, line, date=None, returnRawHost=False,
		checkAllRegex=False):
		"""Split the time portion from log msg and return findFailures on them
		"""
		if date:
			tupleLine = line
		else:
			l = line.rstrip('\r\n')
			logSys.log(7, "Working on line %r", line)

			timeMatch = self.dateDetector.matchTime(l)
			if timeMatch:
				tupleLine  = (
					l[:timeMatch.start()],
					l[timeMatch.start():timeMatch.end()],
					l[timeMatch.end():])
			else:
				tupleLine = (l, "", "")

		return "".join(tupleLine[::2]), self.findFailure(
			tupleLine, date, returnRawHost, checkAllRegex)

	def processLineAndAdd(self, line, date=None):
		"""Processes the line for failures and populates failManager
		"""
		for element in self.processLine(line, date)[1]:
			ip = element[1]
			unixTime = element[2]
			lines = element[3]
			logSys.debug("Processing line with time:%s and ip:%s"
						 % (unixTime, ip))
			if unixTime < MyTime.time() - self.getFindTime():
				logSys.debug("Ignore line since time %s < %s - %s"
							 % (unixTime, MyTime.time(), self.getFindTime()))
				break
			if self.inIgnoreIPList(ip):
				logSys.info("[%s] Ignore %s" % (self.jail.name, ip))
				continue
			logSys.info("[%s] Found %s" % (self.jail.name, ip))
			## print "D: Adding a ticket for %s" % ((ip, unixTime, [line]),)
			self.failManager.addFailure(FailTicket(ip, unixTime, lines))

	##
	# Returns true if the line should be ignored.
	#
	# Uses ignoreregex.
	# @param line: the line
	# @return: a boolean

	def ignoreLine(self, tupleLines):
		for ignoreRegexIndex, ignoreRegex in enumerate(self.__ignoreRegex):
			ignoreRegex.search(tupleLines)
			if ignoreRegex.hasMatched():
				return ignoreRegexIndex
		return None

	##
	# Finds the failure in a line given split into time and log parts.
	#
	# Uses the failregex pattern to find it and timeregex in order
	# to find the logging time.
	# @return a dict with IP and timestamp.

	def findFailure(self, tupleLine, date=None, returnRawHost=False,
		checkAllRegex=False):
		failList = list()

		# Checks if we must ignore this line.
		if self.ignoreLine([tupleLine[::2]]) is not None:
			# The ignoreregex matched. Return.
			logSys.log(7, "Matched ignoreregex and was \"%s\" ignored",
				"".join(tupleLine[::2]))
			return failList

		timeText = tupleLine[1]
		if date:
			self.__lastTimeText = timeText
			self.__lastDate = date
		elif timeText:

			dateTimeMatch = self.dateDetector.getTime(timeText)

			if dateTimeMatch is None:
				logSys.error("findFailure failed to parse timeText: " + timeText)
				date = self.__lastDate

			else:
				# Lets get the time part
				date = dateTimeMatch[0]

				self.__lastTimeText = timeText
				self.__lastDate = date
		else:
			timeText = self.__lastTimeText or "".join(tupleLine[::2])
			date = self.__lastDate

		self.__lineBuffer = (
			self.__lineBuffer + [tupleLine])[-self.__lineBufferSize:]

		# Iterates over all the regular expressions.
		for failRegexIndex, failRegex in enumerate(self.__failRegex):
			failRegex.search(self.__lineBuffer)
			if failRegex.hasMatched():
				# The failregex matched.
				logSys.log(7, "Matched %s", failRegex)
				# Checks if we must ignore this match.
				if self.ignoreLine(failRegex.getMatchedTupleLines()) \
						is not None:
					# The ignoreregex matched. Remove ignored match.
					self.__lineBuffer = failRegex.getUnmatchedTupleLines()
					logSys.log(7, "Matched ignoreregex and was ignored")
					if not checkAllRegex:
						break
					else:
						continue
				if date is None:
					logSys.warning(
						"Found a match for %r but no valid date/time "
						"found for %r. Please try setting a custom "
						"date pattern (see man page jail.conf(5)). "
						"If format is complex, please "
						"file a detailed issue on"
						" https://github.com/fail2ban/fail2ban/issues "
						"in order to get support for this format."
						 % ("\n".join(failRegex.getMatchedLines()), timeText))
				else:
					self.__lineBuffer = failRegex.getUnmatchedTupleLines()
					try:
						host = failRegex.getHost()
						if returnRawHost:
							failList.append([failRegexIndex, host, date,
								 failRegex.getMatchedLines()])
							if not checkAllRegex:
								break
						else:
							ipMatch = DNSUtils.textToIp(host, self.__useDns)
							if ipMatch:
								for ip in ipMatch:
									failList.append([failRegexIndex, ip, date,
										 failRegex.getMatchedLines()])
								if not checkAllRegex:
									break
					except RegexException, e: # pragma: no cover - unsure if reachable
						logSys.error(e)
		return failList

	@property
	def status(self):
		"""Status of failures detected by filter.
		"""
		ret = [("Currently failed", self.failManager.size()),
		       ("Total failed", self.failManager.getFailTotal())]
		return ret


class FileFilter(Filter):

	def __init__(self, jail, **kwargs):
		Filter.__init__(self, jail, **kwargs)
		## The log file path.
		self.__logPath = []
		self.setLogEncoding("auto")

	##
	# Add a log file path
	#
	# @param path log file path

	def addLogPath(self, path, tail = False):
		if self.containsLogPath(path):
			logSys.error(path + " already exists")
		else:
			container = FileContainer(path, self.getLogEncoding(), tail)
			db = self.jail.database
			if db is not None:
				lastpos = db.addLog(self.jail, container)
				if lastpos and not tail:
					container.setPos(lastpos)
			self.__logPath.append(container)
			logSys.info("Added logfile = %s" % path)
			self._addLogPath(path)			# backend specific

	def _addLogPath(self, path):
		# nothing to do by default
		# to be overridden by backends
		pass


	##
	# Delete a log path
	#
	# @param path the log file to delete

	def delLogPath(self, path):
		for log in self.__logPath:
			if log.getFileName() == path:
				self.__logPath.remove(log)
				db = self.jail.database
				if db is not None:
					db.updateLog(self.jail, log)
				logSys.info("Removed logfile = %s" % path)
				self._delLogPath(path)
				return

	def _delLogPath(self, path): # pragma: no cover - overwritten function
		# nothing to do by default
		# to be overridden by backends
		pass

	##
	# Get the log file path
	#
	# @return log file path

	def getLogPath(self):
		return self.__logPath

	##
	# Check whether path is already monitored.
	#
	# @param path The path
	# @return True if the path is already monitored else False

	def containsLogPath(self, path):
		for log in self.__logPath:
			if log.getFileName() == path:
				return True
		return False

	##
	# Set the log file encoding
	#
	# @param encoding the encoding used with log files

	def setLogEncoding(self, encoding):
		if encoding.lower() == "auto":
			encoding = locale.getpreferredencoding()
		codecs.lookup(encoding) # Raise LookupError if invalid codec
		for log in self.getLogPath():
			log.setEncoding(encoding)
		self.__encoding = encoding
		logSys.info("Set jail log file encoding to %s" % encoding)

	##
	# Get the log file encoding
	#
	# @return log encoding value

	def getLogEncoding(self):
		return self.__encoding

	def getFileContainer(self, path):
		for log in self.__logPath:
			if log.getFileName() == path:
				return log
		return None

	##
	# Gets all the failure in the log file.
	#
	# Gets all the failure in the log file which are newer than
	# MyTime.time()-self.findTime. When a failure is detected, a FailTicket
	# is created and is added to the FailManager.

	def getFailures(self, filename):
		container = self.getFileContainer(filename)
		if container is None:
			logSys.error("Unable to get failures in " + filename)
			return False
		# Try to open log file.
		try:
			has_content = container.open()
		# see http://python.org/dev/peps/pep-3151/
		except IOError, e:
			logSys.error("Unable to open %s" % filename)
			logSys.exception(e)
			return False
		except OSError, e: # pragma: no cover - requires race condition to tigger this
			logSys.error("Error opening %s" % filename)
			logSys.exception(e)
			return False
		except OSError, e: # pragma: no cover - Requires implemention error in FileContainer to generate
			logSys.error("Internal errror in FileContainer open method - please report as a bug to https://github.com/fail2ban/fail2ban/issues")
			logSys.exception(e)
			return False

		# yoh: has_content is just a bool, so do not expect it to
		# change -- loop is exited upon break, and is not entered at
		# all if upon container opening that one was empty.  If we
		# start reading tested to be empty container -- race condition
		# might occur leading at least to tests failures.
		while has_content:
			line = container.readline()
			if not line or not self.active:
				# The jail reached the bottom or has been stopped
				break
			self.processLineAndAdd(line)
		container.close()
		db = self.jail.database
		if db is not None:
			db.updateLog(self.jail, container)
		return True

	@property
	def status(self):
		"""Status of Filter plus files being monitored.
		"""
		ret = super(FileFilter, self).status
		path = [m.getFileName() for m in self.getLogPath()]
		ret.append(("File list", path))
		return ret

##
# FileContainer class.
#
# This class manages a file handler and takes care of log rotation detection.
# In order to detect log rotation, the hash (MD5) of the first line of the file
# is computed and compared to the previous hash of this line.

try:
	import hashlib
	md5sum = hashlib.md5
except ImportError: # pragma: no cover
	# hashlib was introduced in Python 2.5.  For compatibility with those
	# elderly Pythons, import from md5
	import md5
	md5sum = md5.new

class FileContainer:

	def __init__(self, filename, encoding, tail = False):
		self.__filename = filename
		self.setEncoding(encoding)
		self.__tail = tail
		self.__handler = None
		# Try to open the file. Raises an exception if an error occurred.
		handler = open(filename, 'rb')
		stats = os.fstat(handler.fileno())
		self.__ino = stats.st_ino
		try:
			firstLine = handler.readline()
			# Computes the MD5 of the first line.
			self.__hash = md5sum(firstLine).hexdigest()
			# Start at the beginning of file if tail mode is off.
			if tail:
				handler.seek(0, 2)
				self.__pos = handler.tell()
			else:
				self.__pos = 0
		finally:
			handler.close()

	def getFileName(self):
		return self.__filename

	def setEncoding(self, encoding):
		codecs.lookup(encoding) # Raises LookupError if invalid
		self.__encoding = encoding

	def getEncoding(self):
		return self.__encoding

	def getHash(self):
		return self.__hash

	def getPos(self):
		return self.__pos

	def setPos(self, value):
		self.__pos = value

	def open(self):
		self.__handler = open(self.__filename, 'rb')
		# Set the file descriptor to be FD_CLOEXEC
		fd = self.__handler.fileno()
		flags = fcntl.fcntl(fd, fcntl.F_GETFD)
		fcntl.fcntl(fd, fcntl.F_SETFD, flags | fcntl.FD_CLOEXEC)
		# Stat the file before even attempting to read it
		stats = os.fstat(self.__handler.fileno())
		if not stats.st_size:
			# yoh: so it is still an empty file -- nothing should be
			#      read from it yet
			# print "D: no content -- return"
			return False
		firstLine = self.__handler.readline()
		# Computes the MD5 of the first line.
		myHash = md5sum(firstLine).hexdigest()
		## print "D: fn=%s hashes=%s/%s inos=%s/%s pos=%s rotate=%s" % (
		## 	self.__filename, self.__hash, myHash, stats.st_ino, self.__ino, self.__pos,
		## 	self.__hash != myHash or self.__ino != stats.st_ino)
		## sys.stdout.flush()
		# Compare hash and inode
		if self.__hash != myHash or self.__ino != stats.st_ino:
			logSys.info("Log rotation detected for %s" % self.__filename)
			self.__hash = myHash
			self.__ino = stats.st_ino
			self.__pos = 0
		# Sets the file pointer to the last position.
		self.__handler.seek(self.__pos)
		return True

	def readline(self):
		if self.__handler is None:
			return ""
		line = self.__handler.readline()
		try:
			line = line.decode(self.getEncoding(), 'strict')
		except UnicodeDecodeError:
			logSys.warning("Error decoding line from '%s' with '%s': %s" %
				(self.getFileName(), self.getEncoding(), `line`))
			if sys.version_info >= (3,): # In python3, must be decoded
				line = line.decode(self.getEncoding(), 'ignore')
		return line

	def close(self):
		if not self.__handler is None:
			# Saves the last position.
			self.__pos = self.__handler.tell()
			# Closes the file.
			self.__handler.close()
			self.__handler = None
		## print "D: Closed %s with pos %d" % (handler, self.__pos)
		## sys.stdout.flush()


##
# JournalFilter class.
#
# Base interface class for systemd journal filters

class JournalFilter(Filter): # pragma: systemd no cover

	def addJournalMatch(self, match): # pragma: no cover - Base class, not used
		pass

	def delJournalMatch(self, match): # pragma: no cover - Base class, not used
		pass

	def getJournalMatch(self, match): # pragma: no cover - Base class, not used
		return []

##
# Utils class for DNS and IP handling.
#
# This class contains only static methods used to handle DNS and IP
# addresses.

import socket, struct

class DNSUtils:

	IP_CRE = re.compile("^(?:\d{1,3}\.){3}\d{1,3}$")

	#@staticmethod
	def dnsToIp(dns):
		""" Convert a DNS into an IP address using the Python socket module.
			Thanks to Kevin Drapel.
		"""
		try:
			return set(socket.gethostbyname_ex(dns)[2])
		except socket.error, e:
			logSys.warning("Unable to find a corresponding IP address for %s: %s"
						% (dns, e))
			return list()
		except socket.error, e:
			logSys.warning("Socket error raised trying to resolve hostname %s: %s"
						% (dns, e))
			return list()
	dnsToIp = staticmethod(dnsToIp)

	#@staticmethod
	def searchIP(text):
		""" Search if an IP address if directly available and return
			it.
		"""
		match = DNSUtils.IP_CRE.match(text)
		if match:
			return match
		else:
			return None
	searchIP = staticmethod(searchIP)

	#@staticmethod
	def isValidIP(string):
		""" Return true if str is a valid IP
		"""
		s = string.split('/', 1)
		try:
			socket.inet_aton(s[0])
			return True
		except socket.error:
			return False
	isValidIP = staticmethod(isValidIP)

	#@staticmethod
	def textToIp(text, useDns):
		""" Return the IP of DNS found in a given text.
		"""
		ipList = list()
		# Search for plain IP
		plainIP = DNSUtils.searchIP(text)
		if not plainIP is None:
			plainIPStr = plainIP.group(0)
			if DNSUtils.isValidIP(plainIPStr):
				ipList.append(plainIPStr)

		# If we are allowed to resolve -- give it a try if nothing was found
		if useDns in ("yes", "warn") and not ipList:
			# Try to get IP from possible DNS
			ip = DNSUtils.dnsToIp(text)
			ipList.extend(ip)
			if ip and useDns == "warn":
				logSys.warning("Determined IP using DNS Lookup: %s = %s",
					text, ipList)

		return ipList
	textToIp = staticmethod(textToIp)

	#@staticmethod
	def cidr(i, n):
		""" Convert an IP address string with a CIDR mask into a 32-bit
			integer.
		"""
		# 32-bit IPv4 address mask
		MASK = 0xFFFFFFFFL
		return ~(MASK >> n) & MASK & DNSUtils.addr2bin(i)
	cidr = staticmethod(cidr)

	#@staticmethod
	def addr2bin(string):
		""" Convert a string IPv4 address into an unsigned integer.
		"""
		return struct.unpack("!L", socket.inet_aton(string))[0]
	addr2bin = staticmethod(addr2bin)

	#@staticmethod
	def bin2addr(addr):
		""" Convert a numeric IPv4 address into string n.n.n.n form.
		"""
		return socket.inet_ntoa(struct.pack("!L", addr))
	bin2addr = staticmethod(bin2addr)

########NEW FILE########
__FILENAME__ = filtergamin
# emacs: -*- mode: python; py-indent-offset: 4; indent-tabs-mode: t -*-
# vi: set ft=python sts=4 ts=4 sw=4 noet :

# This file is part of Fail2Ban.
#
# Fail2Ban is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# Fail2Ban is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with Fail2Ban; if not, write to the Free Software
# Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA  02110-1301, USA.

# Author: Cyril Jaquier, Yaroslav Halchenko

__author__ = "Cyril Jaquier, Yaroslav Halchenko"
__copyright__ = "Copyright (c) 2004 Cyril Jaquier, 2012 Yaroslav Halchenko"
__license__ = "GPL"

import time, logging, fcntl

import gamin

from .failmanager import FailManagerEmpty
from .filter import FileFilter
from .mytime import MyTime

# Gets the instance of the logger.
logSys = logging.getLogger(__name__)

##
# Log reader class.
#
# This class reads a log file and detects login failures or anything else
# that matches a given regular expression. This class is instanciated by
# a Jail object.

class FilterGamin(FileFilter):

	##
	# Constructor.
	#
	# Initialize the filter object with default values.
	# @param jail the jail object

	def __init__(self, jail):
		FileFilter.__init__(self, jail)
		self.__modified = False
		# Gamin monitor
		self.monitor = gamin.WatchMonitor()
		fd = self.monitor.get_fd()
		flags = fcntl.fcntl(fd, fcntl.F_GETFD)
		fcntl.fcntl(fd, fcntl.F_SETFD, flags|fcntl.FD_CLOEXEC)
		logSys.debug("Created FilterGamin")


	def callback(self, path, event):
		logSys.debug("Got event: " + `event` + " for " + path)
		if event in (gamin.GAMCreated, gamin.GAMChanged, gamin.GAMExists):
			logSys.debug("File changed: " + path)
			self.__modified = True

		self._process_file(path)


	def _process_file(self, path):
		"""Process a given file

		TODO -- RF:
		this is a common logic and must be shared/provided by FileFilter
		"""
		self.getFailures(path)
		try:
			while True:
				ticket = self.failManager.toBan()
				self.jail.putFailTicket(ticket)
		except FailManagerEmpty:
			self.failManager.cleanup(MyTime.time())
		self.dateDetector.sortTemplate()
		self.__modified = False

	##
	# Add a log file path
	#
	# @param path log file path

	def _addLogPath(self, path):
		self.monitor.watch_file(path, self.callback)

	##
	# Delete a log path
	#
	# @param path the log file to delete

	def _delLogPath(self, path):
		self.monitor.stop_watch(path)

	##
	# Main loop.
	#
	# This function is the main loop of the thread. It checks if the
	# file has been modified and looks for failures.
	# @return True when the thread exits nicely

	def run(self):
		# Gamin needs a loop to collect and dispatch events
		while self.active:
			if not self.idle:
				# We cannot block here because we want to be able to
				# exit.
				if self.monitor.event_pending():
					self.monitor.handle_events()
			time.sleep(self.sleeptime)
		logSys.debug(self.jail.name + ": filter terminated")
		return True


	def stop(self):
		super(FilterGamin, self).stop()
		self.__cleanup()

	##
	# Desallocates the resources used by Gamin.

	def __cleanup(self):
		for path in self.getLogPath():
			self.monitor.stop_watch(path.getFileName())
		del self.monitor

########NEW FILE########
__FILENAME__ = filterpoll
# emacs: -*- mode: python; py-indent-offset: 4; indent-tabs-mode: t -*-
# vi: set ft=python sts=4 ts=4 sw=4 noet :

# This file is part of Fail2Ban.
#
# Fail2Ban is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# Fail2Ban is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with Fail2Ban; if not, write to the Free Software
# Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA  02110-1301, USA.

# Author: Cyril Jaquier, Yaroslav Halchenko
#

__author__ = "Cyril Jaquier, Yaroslav Halchenko"
__copyright__ = "Copyright (c) 2004 Cyril Jaquier; 2012 Yaroslav Halchenko"
__license__ = "GPL"

import time, logging, os

from .failmanager import FailManagerEmpty
from .filter import FileFilter
from .mytime import MyTime

# Gets the instance of the logger.
logSys = logging.getLogger(__name__)

##
# Log reader class.
#
# This class reads a log file and detects login failures or anything else
# that matches a given regular expression. This class is instantiated by
# a Jail object.

class FilterPoll(FileFilter):

	##
	# Constructor.
	#
	# Initialize the filter object with default values.
	# @param jail the jail object

	def __init__(self, jail):
		FileFilter.__init__(self, jail)
		self.__modified = False
		## The time of the last modification of the file.
		self.__prevStats = dict()
		self.__file404Cnt = dict()
		logSys.debug("Created FilterPoll")

	##
	# Add a log file path
	#
	# @param path log file path

	def _addLogPath(self, path):
		self.__prevStats[path] = (0, None, None)	 # mtime, ino, size
		self.__file404Cnt[path] = 0

	##
	# Delete a log path
	#
	# @param path the log file to delete

	def _delLogPath(self, path):
		del self.__prevStats[path]
		del self.__file404Cnt[path]

	##
	# Main loop.
	#
	# This function is the main loop of the thread. It checks if the
	# file has been modified and looks for failures.
	# @return True when the thread exits nicely

	def run(self):
		while self.active:
			if logSys.getEffectiveLevel() <= 6:
				logSys.log(6, "Woke up idle=%s with %d files monitored",
						   self.idle, len(self.getLogPath()))
			if not self.idle:
				# Get file modification
				for container in self.getLogPath():
					filename = container.getFileName()
					if self.isModified(filename):
						self.getFailures(filename)
						self.__modified = True

				if self.__modified:
					try:
						while True:
							ticket = self.failManager.toBan()
							self.jail.putFailTicket(ticket)
					except FailManagerEmpty:
						self.failManager.cleanup(MyTime.time())
					self.dateDetector.sortTemplate()
					self.__modified = False
				time.sleep(self.sleeptime)
			else:
				time.sleep(self.sleeptime)
		logSys.debug(
			(self.jail is not None and self.jail.name or "jailless") +
					 " filter terminated")
		return True

	##
	# Checks if the log file has been modified.
	#
	# Checks if the log file has been modified using os.stat().
	# @return True if log file has been modified

	def isModified(self, filename):
		try:
			logStats = os.stat(filename)
			stats = logStats.st_mtime, logStats.st_ino, logStats.st_size
			pstats = self.__prevStats[filename]
			self.__file404Cnt[filename] = 0
			if logSys.getEffectiveLevel() <= 7:
				# we do not want to waste time on strftime etc if not necessary
				dt = logStats.st_mtime - pstats[0]
				logSys.log(7, "Checking %s for being modified. Previous/current stats: %s / %s. dt: %s",
				           filename, pstats, stats, dt)
				# os.system("stat %s | grep Modify" % filename)
			if pstats == stats:
				return False
			else:
				logSys.debug("%s has been modified", filename)
				self.__prevStats[filename] = stats
				return True
		except OSError, e:
			logSys.error("Unable to get stat on %s because of: %s"
						 % (filename, e))
			self.__file404Cnt[filename] += 1
			if self.__file404Cnt[filename] > 2:
				logSys.warning("Too many errors. Setting the jail idle")
				if self.jail is not None:
					self.jail.idle = True
				else:
					logSys.warning("No jail is assigned to %s" % self)
				self.__file404Cnt[filename] = 0
			return False

########NEW FILE########
__FILENAME__ = filterpyinotify
# emacs: -*- mode: python; py-indent-offset: 4; indent-tabs-mode: t -*-
# vi: set ft=python sts=4 ts=4 sw=4 noet :

# This file is part of Fail2Ban.
#
# Fail2Ban is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# Fail2Ban is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with Fail2Ban; if not, write to the Free Software
# Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA  02110-1301, USA.

# Original author: Cyril Jaquier

__author__ = "Cyril Jaquier, Lee Clemens, Yaroslav Halchenko"
__copyright__ = "Copyright (c) 2004 Cyril Jaquier, 2011-2012 Lee Clemens, 2012 Yaroslav Halchenko"
__license__ = "GPL"

import logging
from distutils.version import LooseVersion
from os.path import dirname, sep as pathsep

import pyinotify

from .failmanager import FailManagerEmpty
from .filter import FileFilter
from .mytime import MyTime


if not hasattr(pyinotify, '__version__') \
  or LooseVersion(pyinotify.__version__) < '0.8.3':
  raise ImportError("Fail2Ban requires pyinotify >= 0.8.3")

# Verify that pyinotify is functional on this system
# Even though imports -- might be dysfunctional, e.g. as on kfreebsd
try:
	manager = pyinotify.WatchManager()
	del manager
except Exception, e:
	raise ImportError("Pyinotify is probably not functional on this system: %s"
					  % str(e))

# Gets the instance of the logger.
logSys = logging.getLogger(__name__)

##
# Log reader class.
#
# This class reads a log file and detects login failures or anything else
# that matches a given regular expression. This class is instantiated by
# a Jail object.

class FilterPyinotify(FileFilter):
	##
	# Constructor.
	#
	# Initialize the filter object with default values.
	# @param jail the jail object

	def __init__(self, jail):
		FileFilter.__init__(self, jail)
		self.__modified = False
		# Pyinotify watch manager
		self.__monitor = pyinotify.WatchManager()
		self.__watches = dict()
		logSys.debug("Created FilterPyinotify")


	def callback(self, event, origin=''):
		logSys.debug("%sCallback for Event: %s", origin, event)
		path = event.pathname
		if event.mask & ( pyinotify.IN_CREATE | pyinotify.IN_MOVED_TO ):
			# skip directories altogether
			if event.mask & pyinotify.IN_ISDIR:
				logSys.debug("Ignoring creation of directory %s", path)
				return
			# check if that is a file we care about
			if not path in self.__watches:
				logSys.debug("Ignoring creation of %s we do not monitor", path)
				return
			else:
				# we need to substitute the watcher with a new one, so first
				# remove old one
				self._delFileWatcher(path)
				# place a new one
				self._addFileWatcher(path)

		self._process_file(path)


	def _process_file(self, path):
		"""Process a given file

		TODO -- RF:
		this is a common logic and must be shared/provided by FileFilter
		"""
		self.getFailures(path)
		try:
			while True:
				ticket = self.failManager.toBan()
				self.jail.putFailTicket(ticket)
		except FailManagerEmpty:
			self.failManager.cleanup(MyTime.time())
		self.dateDetector.sortTemplate()
		self.__modified = False


	def _addFileWatcher(self, path):
		wd = self.__monitor.add_watch(path, pyinotify.IN_MODIFY)
		self.__watches.update(wd)
		logSys.debug("Added file watcher for %s", path)

	def _delFileWatcher(self, path):
		wdInt = self.__watches[path]
		wd = self.__monitor.rm_watch(wdInt)
		if wd[wdInt]:
			del self.__watches[path]
			logSys.debug("Removed file watcher for %s", path)
			return True
		else:
			return False

	##
	# Add a log file path
	#
	# @param path log file path

	def _addLogPath(self, path):
		path_dir = dirname(path)
		if not (path_dir in self.__watches):
			# we need to watch also  the directory for IN_CREATE
			self.__watches.update(
				self.__monitor.add_watch(path_dir, pyinotify.IN_CREATE | pyinotify.IN_MOVED_TO))
			logSys.debug("Added monitor for the parent directory %s", path_dir)

		self._addFileWatcher(path)
		self._process_file(path)


    ##
	# Delete a log path
	#
	# @param path the log file to delete

	def _delLogPath(self, path):
		if not self._delFileWatcher(path):
			logSys.error("Failed to remove watch on path: %s", path)

		path_dir = dirname(path)
		if not len([k for k in self.__watches
					if k.startswith(path_dir + pathsep)]):
			# Remove watches for the directory
			# since there is no other monitored file under this directory
			wdInt = self.__watches.pop(path_dir)
			self.__monitor.rm_watch(wdInt)
			logSys.debug("Removed monitor for the parent directory %s", path_dir)


	##
	# Main loop.
	#
	# Since all detection is offloaded to pyinotifier -- no manual
	# loop is necessary

	def run(self):
		self.__notifier = pyinotify.ThreadedNotifier(self.__monitor,
			ProcessPyinotify(self))
		self.__notifier.start()
		logSys.debug("pyinotifier started for %s.", self.jail.name)
		# TODO: verify that there is nothing really to be done for
		#       idle jails
		return True

	##
	# Call super.stop() and then stop the 'Notifier'

	def stop(self):
		super(FilterPyinotify, self).stop()

		# Stop the notifier thread
		self.__notifier.stop()
		self.__notifier.join()			# to not exit before notifier does
		self.__cleanup()				# for pedantic ones

	##
	# Deallocates the resources used by pyinotify.

	def __cleanup(self):
		self.__notifier = None
		self.__monitor = None


class ProcessPyinotify(pyinotify.ProcessEvent):
	def __init__(self, FileFilter, **kargs):
		#super(ProcessPyinotify, self).__init__(**kargs)
		# for some reason root class _ProcessEvent is old-style (is
		# not derived from object), so to play safe let's avoid super
		# for now, and call superclass directly
		pyinotify.ProcessEvent.__init__(self, **kargs)
		self.__FileFilter = FileFilter
		pass

	# just need default, since using mask on watch to limit events
	def process_default(self, event):
		try:
			self.__FileFilter.callback(event, origin='Default ')
		except Exception as e:
			logSys.error("Error in FilterPyinotify callback: %s",
				e, exc_info=logSys.getEffectiveLevel() <= logging.DEBUG)

########NEW FILE########
__FILENAME__ = filtersystemd
# emacs: -*- mode: python; py-indent-offset: 4; indent-tabs-mode: t -*-
# vi: set ft=python sts=4 ts=4 sw=4 noet :

# This file is part of Fail2Ban.
#
# Fail2Ban is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# Fail2Ban is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with Fail2Ban; if not, write to the Free Software
# Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA  02110-1301, USA.


__author__ = "Steven Hiscocks"
__copyright__ = "Copyright (c) 2013 Steven Hiscocks"
__license__ = "GPL"

import logging, datetime, time
from distutils.version import LooseVersion

from systemd import journal
if LooseVersion(getattr(journal, '__version__', "0")) < '204':
	raise ImportError("Fail2Ban requires systemd >= 204")

from .failmanager import FailManagerEmpty
from .filter import JournalFilter
from .mytime import MyTime


# Gets the instance of the logger.
logSys = logging.getLogger("fail2ban.filter")

##
# Journal reader class.
#
# This class reads from systemd journal and detects login failures or anything
# else that matches a given regular expression. This class is instantiated by
# a Jail object.

class FilterSystemd(JournalFilter): # pragma: systemd no cover
	##
	# Constructor.
	#
	# Initialize the filter object with default values.
	# @param jail the jail object

	def __init__(self, jail, **kwargs):
		JournalFilter.__init__(self, jail, **kwargs)
		self.__modified = False
		# Initialise systemd-journal connection
		self.__journal = journal.Reader(converters={'__CURSOR': lambda x: x})
		self.__matches = []
		self.setDatePattern(None)
		logSys.debug("Created FilterSystemd")


	##
	# Add a journal match filters from list structure
	#
	# @param matches list structure with journal matches

	def _addJournalMatches(self, matches):
		if self.__matches:
			self.__journal.add_disjunction() # Add OR
		newMatches = []
		for match in matches:
			newMatches.append([])
			for match_element in match:
				self.__journal.add_match(match_element)
				newMatches[-1].append(match_element)
			self.__journal.add_disjunction()
		self.__matches.extend(newMatches)

	##
	# Add a journal match filter
	#
	# @param match journalctl syntax matches in list structure

	def addJournalMatch(self, match):
		newMatches = [[]]
		for match_element in match:
			if match_element == "+":
				newMatches.append([])
			else:
				newMatches[-1].append(match_element)
		try:
			self._addJournalMatches(newMatches)
		except ValueError:
			logSys.error(
				"Error adding journal match for: %r", " ".join(match))
			self.resetJournalMatches()
			raise
		else:
			logSys.info("Added journal match for: %r", " ".join(match))
	##
	# Reset a journal match filter called on removal or failure
	#
	# @return None 

	def resetJournalMatches(self):
		self.__journal.flush_matches()
		logSys.debug("Flushed all journal matches")
		match_copy = self.__matches[:]
		self.__matches = []
		try:
			self._addJournalMatches(match_copy)
		except ValueError:
			logSys.error("Error restoring journal matches")
			raise
		else:
			logSys.debug("Journal matches restored")

	##
	# Delete a journal match filter
	#
	# @param match journalctl syntax matches

	def delJournalMatch(self, match):
		if match in self.__matches:
			del self.__matches[self.__matches.index(match)]
			self.resetJournalMatches()
		else:
			raise ValueError("Match not found")
		logSys.info("Removed journal match for: %r" % " ".join(match))

	##
	# Get current journal match filter
	#
	# @return journalctl syntax matches

	def getJournalMatch(self):
		return self.__matches

    ##
    # Join group of log elements which may be a mix of bytes and strings
    #
    # @param elements list of strings and bytes
    # @return elements joined as string

	@staticmethod
	def _joinStrAndBytes(elements):
		strElements = []
		for element in elements:
			if isinstance(element, str):
				strElements.append(element)
			else:
				strElements.append(str(element, errors='ignore'))
		return " ".join(strElements)

	##
	# Format journal log entry into syslog style
	#
	# @param entry systemd journal entry dict
	# @return format log line

	@classmethod
	def formatJournalEntry(cls, logentry):
		logelements = [""]
		if logentry.get('_HOSTNAME'):
			logelements.append(logentry['_HOSTNAME'])
		if logentry.get('SYSLOG_IDENTIFIER'):
			logelements.append(logentry['SYSLOG_IDENTIFIER'])
			if logentry.get('SYSLOG_PID') or logentry.get('_PID'):
				logelements[-1] += ("[%i]" % logentry.get(
					'SYSLOG_PID', logentry['_PID']))
			logelements[-1] += ":"
		elif logentry.get('_COMM'):
			logelements.append(logentry['_COMM'])
			if logentry.get('_PID'):
				logelements[-1] += ("[%i]" % logentry['_PID'])
			logelements[-1] += ":"
		if logelements[-1] == "kernel:":
			if '_SOURCE_MONOTONIC_TIMESTAMP' in logentry:
				monotonic = logentry.get('_SOURCE_MONOTONIC_TIMESTAMP')
			else:
				monotonic = logentry.get('__MONOTONIC_TIMESTAMP')[0]
			logelements.append("[%12.6f]" % monotonic.total_seconds())
		if isinstance(logentry.get('MESSAGE',''), list):
			logelements.append(" ".join(logentry['MESSAGE']))
		else:
			logelements.append(logentry.get('MESSAGE', ''))

		try:
			logline = u" ".join(logelements)
		except UnicodeDecodeError:
			# Python 2, so treat as string
			logline = " ".join([str(logline) for logline in logelements])
		except TypeError:
			# Python 3, one or more elements bytes
			logSys.warning("Error decoding log elements from journal: %s" %
				repr(logelements))
			logline =  cls._joinStrAndBytes(logelements)

		date = logentry.get('_SOURCE_REALTIME_TIMESTAMP',
				logentry.get('__REALTIME_TIMESTAMP'))
		logSys.debug("Read systemd journal entry: %r" %
			"".join([date.isoformat(), logline]))
		return (('', date.isoformat(), logline),
			time.mktime(date.timetuple()) + date.microsecond/1.0E6)

	##
	# Main loop.
	#
	# Peridocily check for new journal entries matching the filter and
	# handover to FailManager

	def run(self):

		if not self.getJournalMatch():
			logSys.notice(
				"Jail started without 'journalmatch' set. "
				"Jail regexs will be checked against all journal entries, "
				"which is not advised for performance reasons.")

		# Seek to now - findtime in journal
		start_time = datetime.datetime.now() - \
				datetime.timedelta(seconds=int(self.getFindTime()))
		self.__journal.seek_realtime(start_time)
		# Move back one entry to ensure do not end up in dead space
		# if start time beyond end of journal
		try:
			self.__journal.get_previous()
		except OSError:
			pass # Reading failure, so safe to ignore

		while self.active:
			if not self.idle:
				while self.active:
					try:
						logentry = self.__journal.get_next()
					except OSError:
						logSys.warning(
							"Error reading line from systemd journal")
						continue
					if logentry:
						self.processLineAndAdd(
							*self.formatJournalEntry(logentry))
						self.__modified = True
					else:
						break
				if self.__modified:
					try:
						while True:
							ticket = self.failManager.toBan()
							self.jail.putFailTicket(ticket)
					except FailManagerEmpty:
						self.failManager.cleanup(MyTime.time())
					self.__modified = False
			self.__journal.wait(self.sleeptime)
		logSys.debug((self.jail is not None and self.jail.name
                      or "jailless") +" filter terminated")
		return True

	@property
	def status(self):
		ret = super(FilterSystemd, self).status
		ret.append(("Journal matches",
			[" + ".join(" ".join(match) for match in self.__matches)]))
		return ret

########NEW FILE########
__FILENAME__ = jail
# emacs: -*- mode: python; py-indent-offset: 4; indent-tabs-mode: t -*-
# vi: set ft=python sts=4 ts=4 sw=4 noet :

# This file is part of Fail2Ban.
#
# Fail2Ban is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# Fail2Ban is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with Fail2Ban; if not, write to the Free Software
# Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA  02110-1301, USA.

# Author: Cyril Jaquier

__author__ = "Cyril Jaquier, Lee Clemens, Yaroslav Halchenko"
__copyright__ = "Copyright (c) 2004 Cyril Jaquier, 2011-2012 Lee Clemens, 2012 Yaroslav Halchenko"
__license__ = "GPL"

import Queue, logging

from .actions import Actions

# Gets the instance of the logger.
logSys = logging.getLogger(__name__)

class Jail:
	"""Fail2Ban jail, which manages a filter and associated actions.

	The class handles the initialisation of a filter, and actions. It's
	role is then to act as an interface between the filter and actions,
	passing bans detected by the filter, for the actions to then act upon.

	Parameters
	----------
	name : str
		Name assigned to the jail.
	backend : str
		Backend to be used for filter. "auto" will attempt to pick
		the most preferred backend method. Default: "auto"
	db : Fail2BanDb
		Fail2Ban persistent database instance. Default: `None`

	Attributes
	----------
	name
	database
	filter
	actions
	idle
	status
	"""

	#Known backends. Each backend should have corresponding __initBackend method
	# yoh: stored in a list instead of a tuple since only
	#      list had .index until 2.6
	_BACKENDS = ['pyinotify', 'gamin', 'polling', 'systemd']

	def __init__(self, name, backend = "auto", db=None):
		self.__db = db
		# 26 based on iptable chain name limit of 30 less len('f2b-')
		if len(name) >= 26:
			logSys.warning("Jail name %r might be too long and some commands "
							"might not function correctly. Please shorten"
							% name)
		self.__name = name
		self.__queue = Queue.Queue()
		self.__filter = None
		logSys.info("Creating new jail '%s'" % self.name)
		self._setBackend(backend)

	def __repr__(self):
		return "%s(%r)" % (self.__class__.__name__, self.name)

	def _setBackend(self, backend):
		backend = backend.lower()		# to assure consistent matching

		backends = self._BACKENDS
		if backend != 'auto':
			# we have got strict specification of the backend to use
			if not (backend in self._BACKENDS):
				logSys.error("Unknown backend %s. Must be among %s or 'auto'"
					% (backend, backends))
				raise ValueError("Unknown backend %s. Must be among %s or 'auto'"
					% (backend, backends))
			# so explore starting from it till the 'end'
			backends = backends[backends.index(backend):]

		for b in backends:
			initmethod = getattr(self, '_init%s' % b.capitalize())
			try:
				initmethod()
				if backend != 'auto' and b != backend:
					logSys.warning("Could only initiated %r backend whenever "
								   "%r was requested" % (b, backend))
				else:
					logSys.info("Initiated %r backend" % b)
				self.__actions = Actions(self)
				return					# we are done
			except ImportError, e:
				# Log debug if auto, but error if specific
				logSys.log(
					logging.DEBUG if backend == "auto" else logging.ERROR,
					"Backend %r failed to initialize due to %s" % (b, e))
		# log error since runtime error message isn't printed, INVALID COMMAND
		logSys.error(
			"Failed to initialize any backend for Jail %r" % self.name)
		raise RuntimeError(
			"Failed to initialize any backend for Jail %r" % self.name)


	def _initPolling(self):
		from filterpoll import FilterPoll
		logSys.info("Jail '%s' uses poller" % self.name)
		self.__filter = FilterPoll(self)

	def _initGamin(self):
		# Try to import gamin
		from filtergamin import FilterGamin
		logSys.info("Jail '%s' uses Gamin" % self.name)
		self.__filter = FilterGamin(self)

	def _initPyinotify(self):
		# Try to import pyinotify
		from filterpyinotify import FilterPyinotify
		logSys.info("Jail '%s' uses pyinotify" % self.name)
		self.__filter = FilterPyinotify(self)

	def _initSystemd(self): # pragma: systemd no cover
		# Try to import systemd
		from filtersystemd import FilterSystemd
		logSys.info("Jail '%s' uses systemd" % self.name)
		self.__filter = FilterSystemd(self)

	@property
	def name(self):
		"""Name of jail.
		"""
		return self.__name

	@property
	def database(self):
		"""The database used to store persistent data for the jail.
		"""
		return self.__db

	@property
	def filter(self):
		"""The filter which the jail is using to monitor log files.
		"""
		return self.__filter

	@property
	def actions(self):
		"""Actions object used to manage actions for jail.
		"""
		return self.__actions

	@property
	def idle(self):
		"""A boolean indicating whether jail is idle.
		"""
		return self.filter.idle or self.actions.idle

	@idle.setter
	def idle(self, value):
		self.filter.idle = value
		self.actions.idle = value

	@property
	def status(self):
		"""The status of the jail.
		"""
		return [
			("Filter", self.filter.status),
			("Actions", self.actions.status),
			]

	def putFailTicket(self, ticket):
		"""Add a fail ticket to the jail.

		Used by filter to add a failure for banning.
		"""
		self.__queue.put(ticket)
		if self.database is not None:
			self.database.addBan(self, ticket)

	def getFailTicket(self):
		"""Get a fail ticket from the jail.

		Used by actions to get a failure for banning.
		"""
		try:
			return self.__queue.get(False)
		except Queue.Empty:
			return False

	def start(self):
		"""Start the jail, by starting filter and actions threads.

		Once stated, also queries the persistent database to reinstate
		any valid bans.
		"""
		self.filter.start()
		self.actions.start()
		# Restore any previous valid bans from the database
		if self.database is not None:
			for ticket in self.database.getBansMerged(
				jail=self, bantime=self.actions.getBanTime()):
				if not self.filter.inIgnoreIPList(ticket.getIP()):
					self.__queue.put(ticket)
		logSys.info("Jail '%s' started" % self.name)

	def stop(self):
		"""Stop the jail, by stopping filter and actions threads.
		"""
		self.filter.stop()
		self.actions.stop()
		self.filter.join()
		self.actions.join()
		logSys.info("Jail '%s' stopped" % self.name)

	def is_alive(self):
		"""Check jail "is_alive" by checking filter and actions threads.
		"""
		return self.filter.is_alive() or self.actions.is_alive()

########NEW FILE########
__FILENAME__ = jails
# emacs: -*- mode: python; py-indent-offset: 4; indent-tabs-mode: t -*-
# vi: set ft=python sts=4 ts=4 sw=4 noet :

# This file is part of Fail2Ban.
#
# Fail2Ban is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# Fail2Ban is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with Fail2Ban; if not, write to the Free Software
# Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA  02110-1301, USA.

__author__ = "Cyril Jaquier, Yaroslav Halchenko"
__copyright__ = "Copyright (c) 2004 Cyril Jaquier, 2013- Yaroslav Halchenko"
__license__ = "GPL"

from threading import Lock
from collections import Mapping

from ..exceptions import DuplicateJailException, UnknownJailException
from .jail import Jail


class Jails(Mapping):
	"""Handles the jails.

	This class handles the jails. Creation, deletion or access to a jail
	must be done through this class. This class is thread-safe which is
	not the case of the jail itself, including filter and actions. This
	class is based on Mapping type, and the `add` method must be used to
	add additional jails.
	"""

	def __init__(self):
		self.__lock = Lock()
		self._jails = dict()

	def add(self, name, backend, db=None):
		"""Adds a jail.

		Adds a new jail if not already present which should use the
		given backend.

		Parameters
		----------
		name : str
			The name of the jail.
		backend : str
			The backend to use.
		db : Fail2BanDb
			Fail2Ban's persistent database instance.

		Raises
		------
		DuplicateJailException
			If jail name is already present.
		"""
		try:
			self.__lock.acquire()
			if name in self._jails:
				raise DuplicateJailException(name)
			else:
				self._jails[name] = Jail(name, backend, db)
		finally:
			self.__lock.release()

	def __getitem__(self, name):
		try:
			self.__lock.acquire()
			return self._jails[name]
		except KeyError:
			raise UnknownJailException(name)
		finally:
			self.__lock.release()

	def __delitem__(self, name):
		try:
			self.__lock.acquire()
			del self._jails[name]
		except KeyError:
			raise UnknownJailException(name)
		finally:
			self.__lock.release()

	def __len__(self):
		try:
			self.__lock.acquire()
			return len(self._jails)
		finally:
			self.__lock.release()

	def __iter__(self):
		try:
			self.__lock.acquire()
			return iter(self._jails)
		finally:
			self.__lock.release()

########NEW FILE########
__FILENAME__ = jailthread
# emacs: -*- mode: python; py-indent-offset: 4; indent-tabs-mode: t -*-
# vi: set ft=python sts=4 ts=4 sw=4 noet :

# This file is part of Fail2Ban.
#
# Fail2Ban is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# Fail2Ban is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with Fail2Ban; if not, write to the Free Software
# Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA  02110-1301, USA.

# Author: Cyril Jaquier
# 

__author__ = "Cyril Jaquier"
__copyright__ = "Copyright (c) 2004 Cyril Jaquier"
__license__ = "GPL"

from threading import Thread
from abc import abstractproperty, abstractmethod

class JailThread(Thread):
	"""Abstract class for threading elements in Fail2Ban.

	Attributes
	----------
	daemon
	ident
	name
	status
	active : bool
		Control the state of the thread.
	idle : bool
		Control the idle state of the thread.
	sleeptime : int
		The time the thread sleeps for in the loop.
	"""

	def __init__(self):
		super(JailThread, self).__init__()
		## Control the state of the thread.
		self.active = False
		## Control the idle state of the thread.
		self.idle = False
		## The time the thread sleeps in the loop.
		self.sleeptime = 1

	@abstractproperty
	def status(self): # pragma: no cover - abstract
		"""Abstract - Should provide status information.
		"""
		pass

	def start(self):
		"""Sets active flag and starts thread.
		"""
		self.active = True
		super(JailThread, self).start()

	def stop(self):
		"""Sets `active` property to False, to flag run method to return.
		"""
		self.active = False

	@abstractmethod
	def run(self): # pragma: no cover - absract
		"""Abstract - Called when thread starts, thread stops when returns.
		"""
		pass

########NEW FILE########
__FILENAME__ = mytime
# emacs: -*- mode: python; py-indent-offset: 4; indent-tabs-mode: t -*-
# vi: set ft=python sts=4 ts=4 sw=4 noet :

# This file is part of Fail2Ban.
#
# Fail2Ban is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# Fail2Ban is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with Fail2Ban; if not, write to the Free Software
# Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA  02110-1301, USA.

__author__ = "Cyril Jaquier"
__copyright__ = "Copyright (c) 2004 Cyril Jaquier"
__license__ = "GPL"

import time, datetime

##
# MyTime class.
#
# This class is a wrapper around time.time()  and time.gmtime(). When
# performing unit test, it is very useful to get a fixed value from these
# functions.
# Thus, time.time() and time.gmtime() should never be called directly.
# This wrapper should be called instead. The API are equivalent.

class MyTime:
	
	myTime = None
	
	##
	# Sets the current time.
	#
	# Use None in order to always get the real current time.
	#
	# @param t the time to set or None
	
	#@staticmethod
	def setTime(t):
		MyTime.myTime = t
	setTime = staticmethod(setTime)
	
	##
	# Equivalent to time.time()
	#
	# @return time.time() if setTime was called with None
	
	#@staticmethod
	def time():
		if MyTime.myTime is None:
			return time.time()
		else:
			return MyTime.myTime
	time = staticmethod(time)
	
	##
	# Equivalent to time.gmtime()
	#
	# @return time.gmtime() if setTime was called with None
	
	#@staticmethod
	def gmtime():
		if MyTime.myTime is None:
			return time.gmtime()
		else:
			return time.gmtime(MyTime.myTime)
	gmtime = staticmethod(gmtime)

	#@staticmethod
	def now():
		if MyTime.myTime is None:
			return datetime.datetime.now()
		else:
			return datetime.datetime.fromtimestamp(MyTime.myTime)
	now = staticmethod(now)

	def localtime(x=None):
		if MyTime.myTime is None or x is not None:
			return time.localtime(x)
		else:
			return time.localtime(MyTime.myTime)
	localtime = staticmethod(localtime)

########NEW FILE########
__FILENAME__ = server
# emacs: -*- mode: python; py-indent-offset: 4; indent-tabs-mode: t -*-
# vi: set ft=python sts=4 ts=4 sw=4 noet :

# This file is part of Fail2Ban.
#
# Fail2Ban is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# Fail2Ban is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with Fail2Ban; if not, write to the Free Software
# Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA  02110-1301, USA.

# Author: Cyril Jaquier
# 

__author__ = "Cyril Jaquier"
__copyright__ = "Copyright (c) 2004 Cyril Jaquier"
__license__ = "GPL"

from threading import Lock, RLock
import logging, logging.handlers, sys, os, signal

from .jails import Jails
from .filter import FileFilter, JournalFilter
from .transmitter import Transmitter
from .asyncserver import AsyncServer, AsyncServerException
from .. import version

# Gets the instance of the logger.
logSys = logging.getLogger(__name__)

try:
	from .database import Fail2BanDb
except ImportError:
	# Dont print error here, as database may not even be used
	Fail2BanDb = None

class Server:
	
	def __init__(self, daemon = False):
		self.__loggingLock = Lock()
		self.__lock = RLock()
		self.__jails = Jails()
		self.__db = None
		self.__daemon = daemon
		self.__transm = Transmitter(self)
		self.__asyncServer = AsyncServer(self.__transm)
		self.__logLevel = None
		self.__logTarget = None
		# Set logging level
		self.setLogLevel("INFO")
		self.setLogTarget("STDOUT")
	
	def __sigTERMhandler(self, signum, frame):
		logSys.debug("Caught signal %d. Exiting" % signum)
		self.quit()
	
	def start(self, sock, pidfile, force = False):
		logSys.info("Starting Fail2ban v" + version.version)
		
		# Install signal handlers
		signal.signal(signal.SIGTERM, self.__sigTERMhandler)
		signal.signal(signal.SIGINT, self.__sigTERMhandler)
		
		# First set the mask to only allow access to owner
		os.umask(0077)
		if self.__daemon: # pragma: no cover
			logSys.info("Starting in daemon mode")
			ret = self.__createDaemon()
			if ret:
				logSys.info("Daemon started")
			else:
				logSys.error("Could not create daemon")
				raise ServerInitializationError("Could not create daemon")
		
		# Creates a PID file.
		try:
			logSys.debug("Creating PID file %s" % pidfile)
			pidFile = open(pidfile, 'w')
			pidFile.write("%s\n" % os.getpid())
			pidFile.close()
		except IOError, e:
			logSys.error("Unable to create PID file: %s" % e)
		
		# Start the communication
		logSys.debug("Starting communication")
		try:
			self.__asyncServer.start(sock, force)
		except AsyncServerException, e:
			logSys.error("Could not start server: %s", e)
		# Removes the PID file.
		try:
			logSys.debug("Remove PID file %s" % pidfile)
			os.remove(pidfile)
		except OSError, e:
			logSys.error("Unable to remove PID file: %s" % e)
		logSys.info("Exiting Fail2ban")
	
	def quit(self):
		# Stop communication first because if jail's unban action
		# tries to communicate via fail2ban-client we get a lockup
		# among threads.  So the simplest resolution is to stop all
		# communications first (which should be ok anyways since we
		# are exiting)
		# See https://github.com/fail2ban/fail2ban/issues/7
		self.__asyncServer.stop()

		# Now stop all the jails
		self.stopAllJail()

		# Only now shutdown the logging.
		try:
			self.__loggingLock.acquire()
			logging.shutdown()
		finally:
			self.__loggingLock.release()

	
	def addJail(self, name, backend):
		self.__jails.add(name, backend, self.__db)
		if self.__db is not None:
			self.__db.addJail(self.__jails[name])
		
	def delJail(self, name):
		if self.__db is not None:
			self.__db.delJail(self.__jails[name])
		del self.__jails[name]

	def startJail(self, name):
		try:
			self.__lock.acquire()
			if not self.__jails[name].is_alive():
				self.__jails[name].start()
		finally:
			self.__lock.release()
	
	def stopJail(self, name):
		logSys.debug("Stopping jail %s" % name)
		try:
			self.__lock.acquire()
			if self.__jails[name].is_alive():
				self.__jails[name].stop()
				self.delJail(name)
		finally:
			self.__lock.release()
	
	def stopAllJail(self):
		logSys.info("Stopping all jails")
		try:
			self.__lock.acquire()
			for jail in self.__jails.keys():
				self.stopJail(jail)
		finally:
			self.__lock.release()

	def setIdleJail(self, name, value):
		self.__jails[name].idle = value
		return True

	def getIdleJail(self, name):
		return self.__jails[name].idle
	
	# Filter
	def addIgnoreIP(self, name, ip):
		self.__jails[name].filter.addIgnoreIP(ip)
	
	def delIgnoreIP(self, name, ip):
		self.__jails[name].filter.delIgnoreIP(ip)
	
	def getIgnoreIP(self, name):
		return self.__jails[name].filter.getIgnoreIP()
	
	def addLogPath(self, name, fileName, tail=False):
		filter_ = self.__jails[name].filter
		if isinstance(filter_, FileFilter):
			filter_.addLogPath(fileName, tail)
	
	def delLogPath(self, name, fileName):
		filter_ = self.__jails[name].filter
		if isinstance(filter_, FileFilter):
			filter_.delLogPath(fileName)
	
	def getLogPath(self, name):
		filter_ = self.__jails[name].filter
		if isinstance(filter_, FileFilter):
			return [m.getFileName()
					for m in filter_.getLogPath()]
		else: # pragma: systemd no cover
			logSys.info("Jail %s is not a FileFilter instance" % name)
			return []
	
	def addJournalMatch(self, name, match): # pragma: systemd no cover
		filter_ = self.__jails[name].filter
		if isinstance(filter_, JournalFilter):
			filter_.addJournalMatch(match)
	
	def delJournalMatch(self, name, match): # pragma: systemd no cover
		filter_ = self.__jails[name].filter
		if isinstance(filter_, JournalFilter):
			filter_.delJournalMatch(match)
	
	def getJournalMatch(self, name): # pragma: systemd no cover
		filter_ = self.__jails[name].filter
		if isinstance(filter_, JournalFilter):
			return filter_.getJournalMatch()
		else:
			logSys.info("Jail %s is not a JournalFilter instance" % name)
			return []
	
	def setLogEncoding(self, name, encoding):
		filter_ = self.__jails[name].filter
		if isinstance(filter_, FileFilter):
			filter_.setLogEncoding(encoding)
	
	def getLogEncoding(self, name):
		filter_ = self.__jails[name].filter
		if isinstance(filter_, FileFilter):
			return filter_.getLogEncoding()
	
	def setFindTime(self, name, value):
		self.__jails[name].filter.setFindTime(value)
	
	def getFindTime(self, name):
		return self.__jails[name].filter.getFindTime()

	def setDatePattern(self, name, pattern):
		self.__jails[name].filter.setDatePattern(pattern)

	def getDatePattern(self, name):
		return self.__jails[name].filter.getDatePattern()

	def setIgnoreCommand(self, name, value):
		self.__jails[name].filter.setIgnoreCommand(value)

	def getIgnoreCommand(self, name):
		return self.__jails[name].filter.getIgnoreCommand()

	def addFailRegex(self, name, value):
		self.__jails[name].filter.addFailRegex(value)
	
	def delFailRegex(self, name, index):
		self.__jails[name].filter.delFailRegex(index)
	
	def getFailRegex(self, name):
		return self.__jails[name].filter.getFailRegex()
	
	def addIgnoreRegex(self, name, value):
		self.__jails[name].filter.addIgnoreRegex(value)
	
	def delIgnoreRegex(self, name, index):
		self.__jails[name].filter.delIgnoreRegex(index)
	
	def getIgnoreRegex(self, name):
		return self.__jails[name].filter.getIgnoreRegex()
	
	def setUseDns(self, name, value):
		self.__jails[name].filter.setUseDns(value)
	
	def getUseDns(self, name):
		return self.__jails[name].filter.getUseDns()
	
	def setMaxRetry(self, name, value):
		self.__jails[name].filter.setMaxRetry(value)
	
	def getMaxRetry(self, name):
		return self.__jails[name].filter.getMaxRetry()
	
	def setMaxLines(self, name, value):
		self.__jails[name].filter.setMaxLines(value)
	
	def getMaxLines(self, name):
		return self.__jails[name].filter.getMaxLines()
	
	# Action
	def addAction(self, name, value, *args):
		self.__jails[name].actions.add(value, *args)
	
	def getActions(self, name):
		return self.__jails[name].actions
	
	def delAction(self, name, value):
		del self.__jails[name].actions[value]
	
	def getAction(self, name, value):
		return self.__jails[name].actions[value]
	
	def setBanTime(self, name, value):
		self.__jails[name].actions.setBanTime(value)
	
	def setBanIP(self, name, value):
		return self.__jails[name].filter.addBannedIP(value)
		
	def setUnbanIP(self, name, value):
		self.__jails[name].actions.removeBannedIP(value)
		
	def getBanTime(self, name):
		return self.__jails[name].actions.getBanTime()
	
	# Status
	def status(self):
		try:
			self.__lock.acquire()
			jails = list(self.__jails)
			jails.sort()
			jailList = ", ".join(jails)
			ret = [("Number of jail", len(self.__jails)),
				   ("Jail list", jailList)]
			return ret
		finally:
			self.__lock.release()
	
	def statusJail(self, name):
		return self.__jails[name].status
	
	# Logging
	
	##
	# Set the logging level.
	#
	# CRITICAL
	# ERROR
	# WARNING
	# NOTICE
	# INFO
	# DEBUG
	# @param value the level
	
	def setLogLevel(self, value):
		try:
			self.__loggingLock.acquire()
			logging.getLogger(__name__).parent.parent.setLevel(
				getattr(logging, value.upper()))
		except AttributeError:
			raise ValueError("Invalid log level")
		else:
			self.__logLevel = value.upper()
		finally:
			self.__loggingLock.release()
	
	##
	# Get the logging level.
	#
	# @see setLogLevel
	# @return the log level
	
	def getLogLevel(self):
		try:
			self.__loggingLock.acquire()
			return self.__logLevel
		finally:
			self.__loggingLock.release()
	
	##
	# Sets the logging target.
	#
	# target can be a file, SYSLOG, STDOUT or STDERR.
	# @param target the logging target
	
	def setLogTarget(self, target):
		try:
			self.__loggingLock.acquire()
			# set a format which is simpler for console use
			formatter = logging.Formatter("%(asctime)s %(name)-16s[%(process)d]: %(levelname)-7s %(message)s")
			if target == "SYSLOG":
				# Syslog daemons already add date to the message.
				formatter = logging.Formatter("%(name)s[%(process)d]: %(levelname)s %(message)s")
				facility = logging.handlers.SysLogHandler.LOG_DAEMON
				hdlr = logging.handlers.SysLogHandler("/dev/log", facility=facility)
			elif target == "STDOUT":
				hdlr = logging.StreamHandler(sys.stdout)
			elif target == "STDERR":
				hdlr = logging.StreamHandler(sys.stderr)
			else:
				# Target should be a file
				try:
					open(target, "a").close()
					hdlr = logging.handlers.RotatingFileHandler(target)
				except IOError:
					logSys.error("Unable to log to " + target)
					logSys.info("Logging to previous target " + self.__logTarget)
					return False
			# Removes previous handlers -- in reverse order since removeHandler
			# alter the list in-place and that can confuses the iterable
			logger = logging.getLogger(__name__).parent.parent
			for handler in logger.handlers[::-1]:
				# Remove the handler.
				logger.removeHandler(handler)
				# And try to close -- it might be closed already
				try:
					handler.flush()
					handler.close()
				except (ValueError, KeyError): # pragma: no cover
					# Is known to be thrown after logging was shutdown once
					# with older Pythons -- seems to be safe to ignore there
					# At least it was still failing on 2.6.2-0ubuntu1 (jaunty)
					if (2,6,3) <= sys.version_info < (3,) or \
							(3,2) <= sys.version_info:
						raise
			# tell the handler to use this format
			hdlr.setFormatter(formatter)
			logger.addHandler(hdlr)
			# Does not display this message at startup.
			if not self.__logTarget is None:
				logSys.info("Changed logging target to %s for Fail2ban v%s" %
						(target, version.version))
			# Sets the logging target.
			self.__logTarget = target
			return True
		finally:
			self.__loggingLock.release()
	
	def getLogTarget(self):
		try:
			self.__loggingLock.acquire()
			return self.__logTarget
		finally:
			self.__loggingLock.release()
	
	def flushLogs(self):
		if self.__logTarget not in ['STDERR', 'STDOUT', 'SYSLOG']:
			for handler in logging.getLogger(__name__).parent.parent.handlers:
				try:
					handler.doRollover()
					logSys.info("rollover performed on %s" % self.__logTarget)
				except AttributeError:
					handler.flush()
					logSys.info("flush performed on %s" % self.__logTarget)
			return "rolled over"
		else:
			for handler in logging.getLogger(__name__).parent.parent.handlers:
				handler.flush()
				logSys.info("flush performed on %s" % self.__logTarget)
			return "flushed"
			
	def setDatabase(self, filename):
		if len(self.__jails) == 0:
			if filename.lower() == "none":
				self.__db = None
			else:
				if Fail2BanDb is not None:
					self.__db = Fail2BanDb(filename)
					self.__db.delAllJails()
				else:
					logSys.error(
						"Unable to import fail2ban database module as sqlite "
						"is not available.")
		else:
			raise RuntimeError(
				"Cannot change database when there are jails present")
	
	def getDatabase(self):
		return self.__db
	

	def __createDaemon(self): # pragma: no cover
		""" Detach a process from the controlling terminal and run it in the
			background as a daemon.
		
			http://aspn.activestate.com/ASPN/Cookbook/Python/Recipe/278731
		"""
	
		# When the first child terminates, all processes in the second child
		# are sent a SIGHUP, so it's ignored.

		# We need to set this in the parent process, so it gets inherited by the
		# child process, and this makes sure that it is effect even if the parent
		# terminates quickly.
		signal.signal(signal.SIGHUP, signal.SIG_IGN)
		
		try:
			# Fork a child process so the parent can exit.  This will return control
			# to the command line or shell.  This is required so that the new process
			# is guaranteed not to be a process group leader.  We have this guarantee
			# because the process GID of the parent is inherited by the child, but
			# the child gets a new PID, making it impossible for its PID to equal its
			# PGID.
			pid = os.fork()
		except OSError, e:
			return((e.errno, e.strerror))	 # ERROR (return a tuple)
		
		if pid == 0:	   # The first child.
	
			# Next we call os.setsid() to become the session leader of this new
			# session.  The process also becomes the process group leader of the
			# new process group.  Since a controlling terminal is associated with a
			# session, and this new session has not yet acquired a controlling
			# terminal our process now has no controlling terminal.  This shouldn't
			# fail, since we're guaranteed that the child is not a process group
			# leader.
			os.setsid()
		
			try:
				# Fork a second child to prevent zombies.  Since the first child is
				# a session leader without a controlling terminal, it's possible for
				# it to acquire one by opening a terminal in the future.  This second
				# fork guarantees that the child is no longer a session leader, thus
				# preventing the daemon from ever acquiring a controlling terminal.
				pid = os.fork()		# Fork a second child.
			except OSError, e:
				return((e.errno, e.strerror))  # ERROR (return a tuple)
		
			if (pid == 0):	  # The second child.
				# Ensure that the daemon doesn't keep any directory in use.  Failure
				# to do this could make a filesystem unmountable.
				os.chdir("/")
			else:
				os._exit(0)	  # Exit parent (the first child) of the second child.
		else:
			os._exit(0)		 # Exit parent of the first child.
		
		# Close all open files.  Try the system configuration variable, SC_OPEN_MAX,
		# for the maximum number of open files to close.  If it doesn't exist, use
		# the default value (configurable).
		try:
			maxfd = os.sysconf("SC_OPEN_MAX")
		except (AttributeError, ValueError):
			maxfd = 256	   # default maximum
	
		# urandom should not be closed in Python 3.4.0. Fixed in 3.4.1
		# http://bugs.python.org/issue21207
		if sys.version_info[0:3] == (3, 4, 0): # pragma: no cover
			urandom_fd = os.open("/dev/urandom", os.O_RDONLY)
			for fd in range(0, maxfd):
				try:
					if not os.path.sameopenfile(urandom_fd, fd):
						os.close(fd)
				except OSError:   # ERROR (ignore)
					pass
			os.close(urandom_fd)
		else:
			os.closerange(0, maxfd)
	
		# Redirect the standard file descriptors to /dev/null.
		os.open("/dev/null", os.O_RDONLY)	# standard input (0)
		os.open("/dev/null", os.O_RDWR)		# standard output (1)
		os.open("/dev/null", os.O_RDWR)		# standard error (2)
		return True


class ServerInitializationError(Exception):
	pass

########NEW FILE########
__FILENAME__ = strptime
# emacs: -*- mode: python; coding: utf-8; py-indent-offset: 4; indent-tabs-mode: t -*-
# vi: set ft=python sts=4 ts=4 sw=4 noet :

# This file is part of Fail2Ban.
#
# Fail2Ban is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# Fail2Ban is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with Fail2Ban; if not, write to the Free Software
# Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA  02110-1301, USA.

import time
import calendar
import datetime
from _strptime import LocaleTime, TimeRE, _calc_julian_from_U_or_W

from .mytime import MyTime

locale_time = LocaleTime()
timeRE = TimeRE()
timeRE['z'] = r"(?P<z>Z|[+-]\d{2}(?::?[0-5]\d)?)"

def reGroupDictStrptime(found_dict):
	"""Return time from dictionary of strptime fields

	This is tweaked from python built-in _strptime.

	Parameters
	----------
	found_dict : dict
		Dictionary where keys represent the strptime fields, and values the
		respective value.

	Returns
	-------
	float
		Unix time stamp.
	"""

	now = MyTime.now()
	year = month = day = hour = minute = None
	hour = minute = None
	second = fraction = 0
	tzoffset = None
	# Default to -1 to signify that values not known; not critical to have,
	# though
	week_of_year = -1
	week_of_year_start = -1
	# weekday and julian defaulted to -1 so as to signal need to calculate
	# values
	weekday = julian = -1
	for group_key in found_dict.keys():
		# Directives not explicitly handled below:
		#   c, x, X
		#	  handled by making out of other directives
		#   U, W
		#	  worthless without day of the week
		if group_key == 'y':
			year = int(found_dict['y'])
			# Open Group specification for strptime() states that a %y
			#value in the range of [00, 68] is in the century 2000, while
			#[69,99] is in the century 1900
			if year <= 68:
				year += 2000
			else:
				year += 1900
		elif group_key == 'Y':
			year = int(found_dict['Y'])
		elif group_key == 'm':
			month = int(found_dict['m'])
		elif group_key == 'B':
			month = locale_time.f_month.index(found_dict['B'].lower())
		elif group_key == 'b':
			month = locale_time.a_month.index(found_dict['b'].lower())
		elif group_key == 'd':
			day = int(found_dict['d'])
		elif group_key == 'H':
			hour = int(found_dict['H'])
		elif group_key == 'I':
			hour = int(found_dict['I'])
			ampm = found_dict.get('p', '').lower()
			# If there was no AM/PM indicator, we'll treat this like AM
			if ampm in ('', locale_time.am_pm[0]):
				# We're in AM so the hour is correct unless we're
				# looking at 12 midnight.
				# 12 midnight == 12 AM == hour 0
				if hour == 12:
					hour = 0
			elif ampm == locale_time.am_pm[1]:
				# We're in PM so we need to add 12 to the hour unless
				# we're looking at 12 noon.
				# 12 noon == 12 PM == hour 12
				if hour != 12:
					hour += 12
		elif group_key == 'M':
			minute = int(found_dict['M'])
		elif group_key == 'S':
			second = int(found_dict['S'])
		elif group_key == 'f':
			s = found_dict['f']
			# Pad to always return microseconds.
			s += "0" * (6 - len(s))
			fraction = int(s)
		elif group_key == 'A':
			weekday = locale_time.f_weekday.index(found_dict['A'].lower())
		elif group_key == 'a':
			weekday = locale_time.a_weekday.index(found_dict['a'].lower())
		elif group_key == 'w':
			weekday = int(found_dict['w'])
			if weekday == 0:
				weekday = 6
			else:
				weekday -= 1
		elif group_key == 'j':
			julian = int(found_dict['j'])
		elif group_key in ('U', 'W'):
			week_of_year = int(found_dict[group_key])
			if group_key == 'U':
				# U starts week on Sunday.
				week_of_year_start = 6
			else:
				# W starts week on Monday.
				week_of_year_start = 0
		elif group_key == 'z':
			z = found_dict['z']
			if z == "Z":
				tzoffset = 0
			else:
				tzoffset = int(z[1:3]) * 60 # Hours...
				if len(z)>3:
					tzoffset += int(z[-2:]) # ...and minutes
				if z.startswith("-"):
					tzoffset = -tzoffset

	# Fail2Ban will assume it's this year
	assume_year = False
	if year is None:
		year = now.year
		assume_year = True
	# If we know the week of the year and what day of that week, we can figure
	# out the Julian day of the year.
	if julian == -1 and week_of_year != -1 and weekday != -1:
		week_starts_Mon = True if week_of_year_start == 0 else False
		julian = _calc_julian_from_U_or_W(year, week_of_year, weekday,
											week_starts_Mon)
	# Cannot pre-calculate datetime.datetime() since can change in Julian
	# calculation and thus could have different value for the day of the week
	# calculation.
	if julian != -1 and (month is None or day is None):
		datetime_result = datetime.datetime.fromordinal((julian - 1) + datetime.datetime(year, 1, 1).toordinal())
		year = datetime_result.year
		month = datetime_result.month
		day = datetime_result.day
	# Add timezone info
	if tzoffset is not None:
		gmtoff = tzoffset * 60
	else:
		gmtoff = None

	# Fail2Ban assume today
	assume_today = False
	if month is None and day is None:
		month = now.month
		day = now.day
		assume_today = True

	# Actully create date
	date_result =  datetime.datetime(
		year, month, day, hour, minute, second, fraction)
	if gmtoff:
		date_result = date_result - datetime.timedelta(seconds=gmtoff)

	if date_result > now and assume_today:
		# Rollover at midnight, could mean it's yesterday...
		date_result = date_result - datetime.timedelta(days=1)
	if date_result > now and assume_year:
		# Could be last year?
		# also reset month and day as it's not yesterday...
		date_result = date_result.replace(
			year=year-1, month=month, day=day)

	if gmtoff is not None:
		return calendar.timegm(date_result.utctimetuple())
	else:
		return time.mktime(date_result.utctimetuple())


########NEW FILE########
__FILENAME__ = ticket
# emacs: -*- mode: python; py-indent-offset: 4; indent-tabs-mode: t -*-
# vi: set ft=python sts=4 ts=4 sw=4 noet :

# This file is part of Fail2Ban.
#
# Fail2Ban is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# Fail2Ban is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with Fail2Ban; if not, write to the Free Software
# Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA  02110-1301, USA.

# Author: Cyril Jaquier
# 

__author__ = "Cyril Jaquier"
__copyright__ = "Copyright (c) 2004 Cyril Jaquier"
__license__ = "GPL"

import logging

# Gets the instance of the logger.
logSys = logging.getLogger(__name__)

class Ticket:
	
	def __init__(self, ip, time, matches=None):
		"""Ticket constructor

		@param ip the IP address
		@param time the ban time
		@param matches (log) lines caused the ticket
		"""

		self.setIP(ip)
		self.__time = time
		self.__attempt = 0
		self.__file = None
		self.__matches = matches or []

	def __str__(self):
		return "%s: ip=%s time=%s #attempts=%d matches=%r" % \
			   (self.__class__.__name__.split('.')[-1], self.__ip, self.__time, self.__attempt, self.__matches)

	def __repr__(self):
		return str(self)

	def __eq__(self, other):
		try:
			return self.__ip == other.__ip and \
				round(self.__time,2) == round(other.__time,2) and \
				self.__attempt == other.__attempt and \
				self.__matches == other.__matches
		except AttributeError:
			return False

	def setIP(self, value):
		if isinstance(value, basestring):
			# guarantee using regular str instead of unicode for the IP
			value = str(value)
		self.__ip = value
	
	def getIP(self):
		return self.__ip
	
	def setTime(self, value):
		self.__time = value
	
	def getTime(self):
		return self.__time
	
	def setAttempt(self, value):
		self.__attempt = value
	
	def getAttempt(self):
		return self.__attempt

	def getMatches(self):
		return self.__matches


class FailTicket(Ticket):
	pass


##
# Ban Ticket.
#
# This class extends the Ticket class. It is mainly used by the BanManager.

class BanTicket(Ticket):
	pass

########NEW FILE########
__FILENAME__ = transmitter
# emacs: -*- mode: python; py-indent-offset: 4; indent-tabs-mode: t -*-
# vi: set ft=python sts=4 ts=4 sw=4 noet :

# This file is part of Fail2Ban.
#
# Fail2Ban is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# Fail2Ban is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with Fail2Ban; if not, write to the Free Software
# Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA  02110-1301, USA.

# Author: Cyril Jaquier
# 

__author__ = "Cyril Jaquier"
__copyright__ = "Copyright (c) 2004 Cyril Jaquier"
__license__ = "GPL"

import logging, time
import json

# Gets the instance of the logger.
logSys = logging.getLogger(__name__)

class Transmitter:
	
	##
	# Constructor.
	#
	# @param The server reference
	
	def __init__(self, server):
		self.__server = server
		
	##
	# Proceeds a command.
	#
	# Proceeds an incoming command.
	# @param command The incoming command
	
	def proceed(self, command):
		# Deserialize object
		logSys.debug("Command: " + `command`)
		try:
			ret = self.__commandHandler(command)
			ack = 0, ret
		except Exception, e:
			logSys.warning("Command %r has failed. Received %r"
						% (command, e))
			ack = 1, e
		return ack
	
	##
	# Handle an command.
	#
	# 
	
	def __commandHandler(self, command):
		if command[0] == "ping":
			return "pong"
		elif command[0] == "add":
			name = command[1]
			if name == "all":
				raise Exception("Reserved name")
			try:
				backend = command[2]
			except IndexError:
				backend = "auto"
			self.__server.addJail(name, backend)
			return name
		elif command[0] == "start":
			name = command[1]
			self.__server.startJail(name)
			return None
		elif command[0] == "stop":
			if len(command) == 1:
				self.__server.quit()
			elif command[1] == "all":
				self.__server.stopAllJail()
			else:
				name = command[1]
				self.__server.stopJail(name)
			return None
		elif command[0] == "sleep":
			value = command[1]
			time.sleep(int(value))
			return None
		elif command[0] == "flushlogs":
			return self.__server.flushLogs()
		elif command[0] == "set":
			return self.__commandSet(command[1:])
		elif command[0] == "get":
			return self.__commandGet(command[1:])
		elif command[0] == "status":
			return self.status(command[1:])			
		raise Exception("Invalid command")
	
	def __commandSet(self, command):
		name = command[0]
		# Logging
		if name == "loglevel":
			value = command[1]
			self.__server.setLogLevel(value)
			return self.__server.getLogLevel()
		elif name == "logtarget":
			value = command[1]
			if self.__server.setLogTarget(value):
				return self.__server.getLogTarget()
			else:
				raise Exception("Failed to change log target")
		#Database
		elif name == "dbfile":
			self.__server.setDatabase(command[1])
			db = self.__server.getDatabase()
			if db is None:
				return None
			else:
				return db.filename
		elif name == "dbpurgeage":
			db = self.__server.getDatabase()
			if db is None:
				return None
			else:
				db.purgeage = command[1]
				return db.purgeage
		# Jail
		elif command[1] == "idle":
			if command[2] == "on":
				self.__server.setIdleJail(name, True)
			elif command[2] == "off":
				self.__server.setIdleJail(name, False)
			else:
				raise Exception("Invalid idle option, must be 'on' or 'off'")
			return self.__server.getIdleJail(name)
		# Filter
		elif command[1] == "addignoreip":
			value = command[2]
			self.__server.addIgnoreIP(name, value)
			return self.__server.getIgnoreIP(name)
		elif command[1] == "delignoreip":
			value = command[2]
			self.__server.delIgnoreIP(name, value)
			return self.__server.getIgnoreIP(name)
		elif command[1] == "ignorecommand":
			value = command[2]
			self.__server.setIgnoreCommand(name, value)
			return self.__server.getIgnoreCommand(name)
		elif command[1] == "addlogpath":
			value = command[2]
			tail = False
			if len(command) == 4:
				if command[3].lower()  == "tail":
					tail = True
				elif command[3].lower() != "head":
					raise ValueError("File option must be 'head' or 'tail'")
			elif len(command) > 4:
				raise ValueError("Only one file can be added at a time")
			self.__server.addLogPath(name, value, tail)
			return self.__server.getLogPath(name)
		elif command[1] == "dellogpath":
			value = command[2]
			self.__server.delLogPath(name, value)
			return self.__server.getLogPath(name)
		elif command[1] == "logencoding":
			value = command[2]
			self.__server.setLogEncoding(name, value)
			return self.__server.getLogEncoding(name)
		elif command[1] == "addjournalmatch": # pragma: systemd no cover
			value = command[2:]
			self.__server.addJournalMatch(name, value)
			return self.__server.getJournalMatch(name)
		elif command[1] == "deljournalmatch": # pragma: systemd no cover
			value = command[2:]
			self.__server.delJournalMatch(name, value)
			return self.__server.getJournalMatch(name)
		elif command[1] == "addfailregex":
			value = command[2]
			self.__server.addFailRegex(name, value)
			return self.__server.getFailRegex(name)
		elif command[1] == "delfailregex":
			value = int(command[2])
			self.__server.delFailRegex(name, value)
			return self.__server.getFailRegex(name)
		elif command[1] == "addignoreregex":
			value = command[2]
			self.__server.addIgnoreRegex(name, value)
			return self.__server.getIgnoreRegex(name)
		elif command[1] == "delignoreregex":
			value = int(command[2])
			self.__server.delIgnoreRegex(name, value)
			return self.__server.getIgnoreRegex(name)
		elif command[1] == "usedns":
			value = command[2]
			self.__server.setUseDns(name, value)
			return self.__server.getUseDns(name)
		elif command[1] == "findtime":
			value = command[2]
			self.__server.setFindTime(name, int(value))
			return self.__server.getFindTime(name)
		elif command[1] == "datepattern":
			value = command[2]
			self.__server.setDatePattern(name, value)
			return self.__server.getDatePattern(name)
		elif command[1] == "maxretry":
			value = command[2]
			self.__server.setMaxRetry(name, int(value))
			return self.__server.getMaxRetry(name)
		elif command[1] == "maxlines":
			value = command[2]
			self.__server.setMaxLines(name, int(value))
			return self.__server.getMaxLines(name)
		# command
		elif command[1] == "bantime":
			value = command[2]
			self.__server.setBanTime(name, int(value))
			return self.__server.getBanTime(name)
		elif command[1] == "banip":
			value = command[2]
			return self.__server.setBanIP(name,value)
		elif command[1] == "unbanip":
			value = command[2]
			self.__server.setUnbanIP(name, value)
			return value
		elif command[1] == "addaction":
			args = [command[2]]
			if len(command) > 3:
				args.extend([command[3], json.loads(command[4])])
			self.__server.addAction(name, *args)
			return args[0]
		elif command[1] == "delaction":
			value = command[2]
			self.__server.delAction(name, value)
			return None
		elif command[1] == "action":
			actionname = command[2]
			actionkey = command[3]
			action = self.__server.getAction(name, actionname)
			if callable(getattr(action, actionkey, None)):
				actionvalue = json.loads(command[4]) if len(command)>4 else {}
				return getattr(action, actionkey)(**actionvalue)
			else:
				actionvalue = command[4]
				setattr(action, actionkey, actionvalue)
				return getattr(action, actionkey)
		raise Exception("Invalid command (no set action or not yet implemented)")
	
	def __commandGet(self, command):
		name = command[0]
		# Logging
		if name == "loglevel":
			return self.__server.getLogLevel()
		elif name == "logtarget":
			return self.__server.getLogTarget()
		#Database
		elif name == "dbfile":
			db = self.__server.getDatabase()
			if db is None:
				return None
			else:
				return db.filename
		elif name == "dbpurgeage":
			db = self.__server.getDatabase()
			if db is None:
				return None
			else:
				return db.purgeage
		# Filter
		elif command[1] == "logpath":
			return self.__server.getLogPath(name)
		elif command[1] == "logencoding":
			return self.__server.getLogEncoding(name)
		elif command[1] == "journalmatch": # pragma: systemd no cover
			return self.__server.getJournalMatch(name)
		elif command[1] == "ignoreip":
			return self.__server.getIgnoreIP(name)
		elif command[1] == "ignorecommand":
			return self.__server.getIgnoreCommand(name)
		elif command[1] == "failregex":
			return self.__server.getFailRegex(name)
		elif command[1] == "ignoreregex":
			return self.__server.getIgnoreRegex(name)
		elif command[1] == "usedns":
			return self.__server.getUseDns(name)
		elif command[1] == "findtime":
			return self.__server.getFindTime(name)
		elif command[1] == "datepattern":
			return self.__server.getDatePattern(name)
		elif command[1] == "maxretry":
			return self.__server.getMaxRetry(name)
		elif command[1] == "maxlines":
			return self.__server.getMaxLines(name)
		# Action
		elif command[1] == "bantime":
			return self.__server.getBanTime(name)
		elif command[1] == "actions":
			return self.__server.getActions(name).keys()
		elif command[1] == "action":
			actionname = command[2]
			actionvalue = command[3]
			action = self.__server.getAction(name, actionname)
			return getattr(action, actionvalue)
		elif command[1] == "actionproperties":
			actionname = command[2]
			action = self.__server.getAction(name, actionname)
			return [
				key for key in dir(action)
				if not key.startswith("_") and
					not callable(getattr(action, key))]
		elif command[1] == "actionmethods":
			actionname = command[2]
			action = self.__server.getAction(name, actionname)
			return [
				key for key in dir(action)
				if not key.startswith("_") and callable(getattr(action, key))]
		raise Exception("Invalid command (no get action or not yet implemented)")
	
	def status(self, command):
		if len(command) == 0:
			return self.__server.status()
		elif len(command) == 1:
			name = command[0]
			return self.__server.statusJail(name)
		raise Exception("Invalid command (no status)")
	

########NEW FILE########
__FILENAME__ = actionstestcase
# emacs: -*- mode: python; py-indent-offset: 4; indent-tabs-mode: t -*-
# vi: set ft=python sts=4 ts=4 sw=4 noet :

# This file is part of Fail2Ban.
#
# Fail2Ban is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# Fail2Ban is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with Fail2Ban; if not, write to the Free Software
# Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA  02110-1301, USA.

# Author: Daniel Black
# 

__author__ = "Daniel Black"
__copyright__ = "Copyright (c) 2013 Daniel Black"
__license__ = "GPL"

import time
import os
import tempfile

from ..server.actions import Actions
from .dummyjail import DummyJail
from .utils import LogCaptureTestCase

TEST_FILES_DIR = os.path.join(os.path.dirname(__file__), "files")

class ExecuteActions(LogCaptureTestCase):

	def setUp(self):
		"""Call before every test case."""
		super(ExecuteActions, self).setUp()
		self.__jail = DummyJail()
		self.__actions = Actions(self.__jail)
		self.__tmpfile, self.__tmpfilename  = tempfile.mkstemp()

	def tearDown(self):
		super(ExecuteActions, self).tearDown()
		os.remove(self.__tmpfilename)

	def defaultActions(self):
		self.__actions.add('ip')
		self.__ip = self.__actions['ip']
		self.__ip.actionstart = 'echo ip start 64 >> "%s"' % self.__tmpfilename
		self.__ip.actionban = 'echo ip ban <ip> >> "%s"' % self.__tmpfilename
		self.__ip.actionunban = 'echo ip unban <ip> >> "%s"' % self.__tmpfilename
		self.__ip.actioncheck = 'echo ip check <ip> >> "%s"' % self.__tmpfilename
		self.__ip.actionstop = 'echo ip stop >> "%s"' % self.__tmpfilename

	def testActionsAddDuplicateName(self):
		self.__actions.add('test')
		self.assertRaises(ValueError, self.__actions.add, 'test')

	def testActionsManipulation(self):
		self.__actions.add('test')
		self.assertTrue(self.__actions['test'])
		self.assertTrue('test' in self.__actions)
		self.assertFalse('nonexistant action' in self.__actions)
		self.__actions.add('test1')
		del self.__actions['test']
		del self.__actions['test1']
		self.assertFalse('test' in self.__actions)
		self.assertEqual(len(self.__actions), 0)

		self.__actions.setBanTime(127)
		self.assertEqual(self.__actions.getBanTime(),127)
		self.assertRaises(ValueError, self.__actions.removeBannedIP, '127.0.0.1')


	def testActionsOutput(self):
		self.defaultActions()
		self.__actions.start()
		with open(self.__tmpfilename) as f:
			time.sleep(3)
			self.assertEqual(f.read(),"ip start 64\n")

		self.__actions.stop()
		self.__actions.join()
		self.assertEqual(self.__actions.status,[("Currently banned", 0 ),
               ("Total banned", 0 ), ("Banned IP list", [] )])


	def testAddActionPython(self):
		self.__actions.add(
			"Action", os.path.join(TEST_FILES_DIR, "action.d/action.py"),
			{'opt1': 'value'})

		self.assertTrue(self._is_logged("TestAction initialised"))

		self.__actions.start()
		time.sleep(3)
		self.assertTrue(self._is_logged("TestAction action start"))

		self.__actions.stop()
		self.__actions.join()
		self.assertTrue(self._is_logged("TestAction action stop"))

		self.assertRaises(IOError,
			self.__actions.add, "Action3", "/does/not/exist.py", {})

		# With optional argument
		self.__actions.add(
			"Action4", os.path.join(TEST_FILES_DIR, "action.d/action.py"),
			{'opt1': 'value', 'opt2': 'value2'})
		# With too many arguments
		self.assertRaises(
			TypeError, self.__actions.add, "Action5",
			os.path.join(TEST_FILES_DIR, "action.d/action.py"),
			{'opt1': 'value', 'opt2': 'value2', 'opt3': 'value3'})
		# Missing required argument
		self.assertRaises(
			TypeError, self.__actions.add, "Action5",
			os.path.join(TEST_FILES_DIR, "action.d/action.py"), {})

	def testAddPythonActionNOK(self):
		self.assertRaises(RuntimeError, self.__actions.add,
			"Action", os.path.join(TEST_FILES_DIR,
				"action.d/action_noAction.py"),
			{})
		self.assertRaises(RuntimeError, self.__actions.add,
			"Action", os.path.join(TEST_FILES_DIR,
				"action.d/action_nomethod.py"),
			{})
		self.__actions.add(
			"Action", os.path.join(TEST_FILES_DIR,
				"action.d/action_errors.py"),
			{})
		self.__actions.start()
		time.sleep(3)
		self.assertTrue(self._is_logged("Failed to start"))
		self.__actions.stop()
		self.__actions.join()
		self.assertTrue(self._is_logged("Failed to stop"))

########NEW FILE########
__FILENAME__ = actiontestcase
# emacs: -*- mode: python; py-indent-offset: 4; indent-tabs-mode: t -*-
# vi: set ft=python sts=4 ts=4 sw=4 noet :

# This file is part of Fail2Ban.
#
# Fail2Ban is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# Fail2Ban is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with Fail2Ban; if not, write to the Free Software
# Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA  02110-1301, USA.

# Author: Cyril Jaquier
# 

__author__ = "Cyril Jaquier"
__copyright__ = "Copyright (c) 2004 Cyril Jaquier"
__license__ = "GPL"

import time

from ..server.action import CommandAction, CallingMap

from .utils import LogCaptureTestCase

class CommandActionTest(LogCaptureTestCase):

	def setUp(self):
		"""Call before every test case."""
		self.__action = CommandAction(None, "Test")
		LogCaptureTestCase.setUp(self)

	def tearDown(self):
		"""Call after every test case."""
		LogCaptureTestCase.tearDown(self)
		self.__action.stop()

	def testSubstituteRecursiveTags(self):
		aInfo = {
			'HOST': "192.0.2.0",
			'ABC': "123 <HOST>",
			'xyz': "890 <ABC>",
		}
		# Recursion is bad
		self.assertFalse(CommandAction.substituteRecursiveTags({'A': '<A>'}))
		self.assertFalse(CommandAction.substituteRecursiveTags({'A': '<B>', 'B': '<A>'}))
		self.assertFalse(CommandAction.substituteRecursiveTags({'A': '<B>', 'B': '<C>', 'C': '<A>'}))
		# Unresolveable substition
		self.assertFalse(CommandAction.substituteRecursiveTags({'A': 'to=<B> fromip=<IP>', 'C': '<B>', 'B': '<C>', 'D': ''}))
		self.assertFalse(CommandAction.substituteRecursiveTags({'failregex': 'to=<honeypot> fromip=<IP>', 'sweet': '<honeypot>', 'honeypot': '<sweet>', 'ignoreregex': ''}))
		# missing tags are ok
		self.assertEqual(CommandAction.substituteRecursiveTags({'A': '<C>'}), {'A': '<C>'})
		self.assertEqual(CommandAction.substituteRecursiveTags({'A': '<C> <D> <X>','X':'fun'}), {'A': '<C> <D> fun', 'X':'fun'})
		self.assertEqual(CommandAction.substituteRecursiveTags({'A': '<C> <B>', 'B': 'cool'}), {'A': '<C> cool', 'B': 'cool'})
		# Multiple stuff on same line is ok
		self.assertEqual(CommandAction.substituteRecursiveTags({'failregex': 'to=<honeypot> fromip=<IP> evilperson=<honeypot>', 'honeypot': 'pokie', 'ignoreregex': ''}),
								{ 'failregex': "to=pokie fromip=<IP> evilperson=pokie",
									'honeypot': 'pokie',
									'ignoreregex': '',
								})
		# rest is just cool
		self.assertEqual(CommandAction.substituteRecursiveTags(aInfo),
								{ 'HOST': "192.0.2.0",
									'ABC': '123 192.0.2.0',
									'xyz': '890 123 192.0.2.0',
								})

	def testReplaceTag(self):
		aInfo = {
			'HOST': "192.0.2.0",
			'ABC': "123",
			'xyz': "890",
		}
		self.assertEqual(
			self.__action.replaceTag("Text<br>text", aInfo),
			"Text\ntext")
		self.assertEqual(
			self.__action.replaceTag("Text <HOST> text", aInfo),
			"Text 192.0.2.0 text")
		self.assertEqual(
			self.__action.replaceTag("Text <xyz> text <ABC> ABC", aInfo),
			"Text 890 text 123 ABC")
		self.assertEqual(
			self.__action.replaceTag("<matches>",
				{'matches': "some >char< should \< be[ escap}ed&\n"}),
			"some \\>char\\< should \\\\\\< be\\[ escap\\}ed\\&\n")
		self.assertEqual(
			self.__action.replaceTag("<ipmatches>",
				{'ipmatches': "some >char< should \< be[ escap}ed&\n"}),
			"some \\>char\\< should \\\\\\< be\\[ escap\\}ed\\&\n")
		self.assertEqual(
			self.__action.replaceTag("<ipjailmatches>",
				{'ipjailmatches': "some >char< should \< be[ escap}ed&\n"}),
			"some \\>char\\< should \\\\\\< be\\[ escap\\}ed\\&\n")


		# Recursive
		aInfo["ABC"] = "<xyz>"
		self.assertEqual(
			self.__action.replaceTag("Text <xyz> text <ABC> ABC", aInfo),
			"Text 890 text 890 ABC")

		# Callable
		self.assertEqual(
			self.__action.replaceTag("09 <matches> 11",
				CallingMap(matches=lambda: str(10))),
			"09 10 11")

		# As tag not present, therefore callable should not be called
		# Will raise ValueError if it is
		self.assertEqual(
			self.__action.replaceTag("abc",
				CallingMap(matches=lambda: int("a"))), "abc")

	def testExecuteActionBan(self):
		self.__action.actionstart = "touch /tmp/fail2ban.test"
		self.assertEqual(self.__action.actionstart, "touch /tmp/fail2ban.test")
		self.__action.actionstop = "rm -f /tmp/fail2ban.test"
		self.assertEqual(self.__action.actionstop, 'rm -f /tmp/fail2ban.test')
		self.__action.actionban = "echo -n"
		self.assertEqual(self.__action.actionban, 'echo -n')
		self.__action.actioncheck = "[ -e /tmp/fail2ban.test ]"
		self.assertEqual(self.__action.actioncheck, '[ -e /tmp/fail2ban.test ]')
		self.__action.actionunban = "true"
		self.assertEqual(self.__action.actionunban, 'true')

		self.assertFalse(self._is_logged('returned'))
		# no action was actually executed yet

		self.__action.ban({'ip': None})
		self.assertTrue(self._is_logged('Invariant check failed'))
		self.assertTrue(self._is_logged('returned successfully'))

	def testExecuteActionEmptyUnban(self):
		self.__action.actionunban = ""
		self.__action.unban({})
		self.assertTrue(self._is_logged('Nothing to do'))

	def testExecuteActionStartCtags(self):
		self.__action.HOST = "192.0.2.0"
		self.__action.actionstart = "touch /tmp/fail2ban.test.<HOST>"
		self.__action.actionstop = "rm -f /tmp/fail2ban.test.<HOST>"
		self.__action.actioncheck = "[ -e /tmp/fail2ban.test.192.0.2.0 ]"
		self.__action.start()

	def testExecuteActionCheckRestoreEnvironment(self):
		self.__action.actionstart = ""
		self.__action.actionstop = "rm -f /tmp/fail2ban.test"
		self.__action.actionban = "rm /tmp/fail2ban.test"
		self.__action.actioncheck = "[ -e /tmp/fail2ban.test ]"
		self.assertRaises(RuntimeError, self.__action.ban, {'ip': None})
		self.assertTrue(self._is_logged('Unable to restore environment'))

	def testExecuteActionChangeCtags(self):
		self.assertRaises(AttributeError, getattr, self.__action, "ROST")
		self.__action.ROST = "192.0.2.0"
		self.assertEqual(self.__action.ROST,"192.0.2.0")

	def testExecuteActionUnbanAinfo(self):
		aInfo = {
			'ABC': "123",
		}
		self.__action.actionban = "touch /tmp/fail2ban.test.123"
		self.__action.actionunban = "rm /tmp/fail2ban.test.<ABC>"
		self.__action.ban(aInfo)
		self.__action.unban(aInfo)

	def testExecuteActionStartEmpty(self):
		self.__action.actionstart = ""
		self.__action.start()
		self.assertTrue(self._is_logged('Nothing to do'))

	def testExecuteIncorrectCmd(self):
		CommandAction.executeCmd('/bin/ls >/dev/null\nbogusXXX now 2>/dev/null')
		self.assertTrue(self._is_logged('HINT on 127: "Command not found"'))

	def testExecuteTimeout(self):
		stime = time.time()
		# Should take a minute
		self.assertRaises(
			RuntimeError, CommandAction.executeCmd, 'sleep 60', timeout=2)
		self.assertAlmostEqual(time.time() - stime, 2, places=0)
		self.assertTrue(self._is_logged('sleep 60 -- timed out after 2 seconds'))
		self.assertTrue(self._is_logged('sleep 60 -- killed with SIGTERM'))

	def testCaptureStdOutErr(self):
		CommandAction.executeCmd('echo "How now brown cow"')
		self.assertTrue(self._is_logged("'How now brown cow\\n'"))
		CommandAction.executeCmd(
			'echo "The rain in Spain stays mainly in the plain" 1>&2')
		self.assertTrue(self._is_logged(
			"'The rain in Spain stays mainly in the plain\\n'"))

	def testCallingMap(self):
		mymap = CallingMap(callme=lambda: str(10), error=lambda: int('a'),
			dontcallme= "string", number=17)

		# Should work fine
		self.assertEqual(
			"%(callme)s okay %(dontcallme)s %(number)i" % mymap,
			"10 okay string 17")
		# Error will now trip, demonstrating delayed call
		self.assertRaises(ValueError, lambda x: "%(error)i" % x, mymap)

########NEW FILE########
__FILENAME__ = test_badips
# emacs: -*- mode: python; py-indent-offset: 4; indent-tabs-mode: t -*-
# vi: set ft=python sts=4 ts=4 sw=4 noet :

# This file is part of Fail2Ban.
#
# Fail2Ban is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# Fail2Ban is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with Fail2Ban; if not, write to the Free Software
# Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA  02110-1301, USA.

import os
import unittest
import sys

from ..dummyjail import DummyJail

if os.path.exists('config/fail2ban.conf'):
	CONFIG_DIR = "config"
else:
	CONFIG_DIR='/etc/fail2ban'

if sys.version_info >= (2,7):
	class BadIPsActionTest(unittest.TestCase):

		def setUp(self):
			"""Call before every test case."""
			self.jail = DummyJail()

			self.jail.actions.add("test")

			pythonModule = os.path.join(CONFIG_DIR, "action.d", "badips.py")
			self.jail.actions.add("badips", pythonModule, initOpts={
				'category': "ssh",
				'banaction': "test",
				})
			self.action = self.jail.actions["badips"]

		def tearDown(self):
			"""Call after every test case."""
			# Must cancel timer!
			if self.action._timer:
				self.action._timer.cancel()

		def testCategory(self):
			categories = self.action.getCategories()
			self.assertTrue("ssh" in categories)
			self.assertTrue(len(categories) >= 10)

			self.assertRaises(
				ValueError, setattr, self.action, "category",
				"invalid-category")

			# Not valid for reporting category...
			self.assertRaises(
				ValueError, setattr, self.action, "category", "mail")
			# but valid for blacklisting.
			self.action.bancategory = "mail"

		def testScore(self):
			self.assertRaises(ValueError, setattr, self.action, "score", -5)
			self.action.score = 5
			self.action.score = "5"

		def testBanaction(self):
			self.assertRaises(
				ValueError, setattr, self.action, "banaction",
				"invalid-action")
			self.action.banaction = "test"

		def testUpdateperiod(self):
			self.assertRaises(
				ValueError, setattr, self.action, "updateperiod", -50)
			self.assertRaises(
				ValueError, setattr, self.action, "updateperiod", 0)
			self.action.updateperiod = 900
			self.action.updateperiod = "900"

		def testStart(self):
			self.action.start()
			self.assertTrue(len(self.action._bannedips) > 10)

		def testStop(self):
			self.testStart()
			self.action.stop()
			self.assertTrue(len(self.action._bannedips) == 0)

########NEW FILE########
__FILENAME__ = test_smtp
# emacs: -*- mode: python; py-indent-offset: 4; indent-tabs-mode: t -*-
# vi: set ft=python sts=4 ts=4 sw=4 noet :

# This file is part of Fail2Ban.
#
# Fail2Ban is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# Fail2Ban is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with Fail2Ban; if not, write to the Free Software
# Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA  02110-1301, USA.

import os
import smtpd
import asyncore
import threading
import unittest
import sys
if sys.version_info >= (3, 3):
	import importlib
else:
	import imp

from ..dummyjail import DummyJail

if os.path.exists('config/fail2ban.conf'):
	CONFIG_DIR = "config"
else:
	CONFIG_DIR='/etc/fail2ban'

class TestSMTPServer(smtpd.SMTPServer):

	def process_message(self, peer, mailfrom, rcpttos, data):
		self.peer = peer
		self.mailfrom = mailfrom
		self.rcpttos = rcpttos
		self.data = data

class SMTPActionTest(unittest.TestCase):

	def setUp(self):
		"""Call before every test case."""
		self.jail = DummyJail()
		pythonModule = os.path.join(CONFIG_DIR, "action.d", "smtp.py")
		pythonModuleName = os.path.basename(pythonModule.rstrip(".py"))
		if sys.version_info >= (3, 3):
			customActionModule = importlib.machinery.SourceFileLoader(
				pythonModuleName, pythonModule).load_module()
		else:
			customActionModule = imp.load_source(
				pythonModuleName, pythonModule)

		self.smtpd = TestSMTPServer(("localhost", 0), None)
		port = self.smtpd.socket.getsockname()[1]

		self.action = customActionModule.Action(
			self.jail, "test", host="127.0.0.1:%i" % port)

		self._loop_thread = threading.Thread(
			target=asyncore.loop, kwargs={'timeout': 1})
		self._loop_thread.start()

	def tearDown(self):
		"""Call after every test case."""
		self.smtpd.close()
		self._loop_thread.join()

	def testStart(self):
		self.action.start()
		self.assertEqual(self.smtpd.mailfrom, "fail2ban")
		self.assertEqual(self.smtpd.rcpttos, ["root"])
		self.assertTrue(
			"Subject: [Fail2Ban] %s: started" % self.jail.name
			in self.smtpd.data)

	def testStop(self):
		self.action.stop()
		self.assertEqual(self.smtpd.mailfrom, "fail2ban")
		self.assertEqual(self.smtpd.rcpttos, ["root"])
		self.assertTrue(
			"Subject: [Fail2Ban] %s: stopped" %
				self.jail.name in self.smtpd.data)

	def testBan(self):
		aInfo = {
			'ip': "127.0.0.2",
			'failures': 3,
			'matches': "Test fail 1\n",
			'ipjailmatches': "Test fail 1\nTest Fail2\n",
			'ipmatches': "Test fail 1\nTest Fail2\nTest Fail3\n",
			}

		self.action.ban(aInfo)
		self.assertEqual(self.smtpd.mailfrom, "fail2ban")
		self.assertEqual(self.smtpd.rcpttos, ["root"])
		subject = "Subject: [Fail2Ban] %s: banned %s" % (
			self.jail.name, aInfo['ip'])
		self.assertTrue(subject in self.smtpd.data.replace("\n", ""))
		self.assertTrue(
			"%i attempts" % aInfo['failures'] in self.smtpd.data)

		self.action.matches = "matches"
		self.action.ban(aInfo)
		self.assertTrue(aInfo['matches'] in self.smtpd.data)

		self.action.matches = "ipjailmatches"
		self.action.ban(aInfo)
		self.assertTrue(aInfo['ipjailmatches'] in self.smtpd.data)

		self.action.matches = "ipmatches"
		self.action.ban(aInfo)
		self.assertTrue(aInfo['ipmatches'] in self.smtpd.data)

	def testOptions(self):
		self.action.start()
		self.assertEqual(self.smtpd.mailfrom, "fail2ban")
		self.assertEqual(self.smtpd.rcpttos, ["root"])

		self.action.fromname = "Test"
		self.action.fromaddr = "test@example.com"
		self.action.toaddr = "test@example.com, test2@example.com"
		self.action.start()
		self.assertEqual(self.smtpd.mailfrom, "test@example.com")
		self.assertTrue("From: %s <%s>" %
			(self.action.fromname, self.action.fromaddr) in self.smtpd.data)
		self.assertEqual(set(self.smtpd.rcpttos), set(["test@example.com", "test2@example.com"]))

########NEW FILE########
__FILENAME__ = banmanagertestcase
# emacs: -*- mode: python; py-indent-offset: 4; indent-tabs-mode: t -*-
# vi: set ft=python sts=4 ts=4 sw=4 noet :

# This file is part of Fail2Ban.
#
# Fail2Ban is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# Fail2Ban is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with Fail2Ban; if not, write to the Free Software
# Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA  02110-1301, USA.

# Author: Cyril Jaquier
# 

__author__ = "Cyril Jaquier"
__copyright__ = "Copyright (c) 2004 Cyril Jaquier"
__license__ = "GPL"

import unittest

from ..server.banmanager import BanManager
from ..server.ticket import BanTicket

class AddFailure(unittest.TestCase):

	def setUp(self):
		"""Call before every test case."""
		self.__ticket = BanTicket('193.168.0.128', 1167605999.0)
		self.__banManager = BanManager()
		self.assertTrue(self.__banManager.addBanTicket(self.__ticket))

	def tearDown(self):
		"""Call after every test case."""
	
	def testAdd(self):
		self.assertEqual(self.__banManager.size(), 1)
	
	def testAddDuplicate(self):
		self.assertFalse(self.__banManager.addBanTicket(self.__ticket))
		self.assertEqual(self.__banManager.size(), 1)
		
	def testInListOK(self):
		ticket = BanTicket('193.168.0.128', 1167605999.0)
		self.assertTrue(self.__banManager._inBanList(ticket))
	
	def testInListNOK(self):
		ticket = BanTicket('111.111.1.111', 1167605999.0)
		self.assertFalse(self.__banManager._inBanList(ticket))
		

########NEW FILE########
__FILENAME__ = clientreadertestcase
# emacs: -*- mode: python; py-indent-offset: 4; indent-tabs-mode: t -*-
# vi: set ft=python sts=4 ts=4 sw=4 noet :

# This file is part of Fail2Ban.
#
# Fail2Ban is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# Fail2Ban is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with Fail2Ban; if not, write to the Free Software
# Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA  02110-1301, USA.

__author__ = "Cyril Jaquier, Yaroslav Halchenko"
__copyright__ = "Copyright (c) 2004 Cyril Jaquier, 2011-2013 Yaroslav Halchenko"
__license__ = "GPL"

import os, glob, shutil, tempfile, unittest

from ..client.configreader import ConfigReader
from ..client.jailreader import JailReader
from ..client.filterreader import FilterReader
from ..client.jailsreader import JailsReader
from ..client.actionreader import ActionReader
from ..client.configurator import Configurator
from .utils import LogCaptureTestCase

TEST_FILES_DIR = os.path.join(os.path.dirname(__file__), "files")
STOCK = os.path.exists(os.path.join('config','fail2ban.conf'))
CONFIG_DIR='config' if STOCK else '/etc/fail2ban'

IMPERFECT_CONFIG = os.path.join(os.path.dirname(__file__), 'config')

class ConfigReaderTest(unittest.TestCase):

	def setUp(self):
		"""Call before every test case."""
		self.d = tempfile.mkdtemp(prefix="f2b-temp")
		self.c = ConfigReader(basedir=self.d)

	def tearDown(self):
		"""Call after every test case."""
		shutil.rmtree(self.d)

	def _write(self, fname, value=None, content=None):
		# verify if we don't need to create .d directory
		if os.path.sep in fname:
			d = os.path.dirname(fname)
			d_ = os.path.join(self.d, d)
			if not os.path.exists(d_):
				os.makedirs(d_)
		f = open("%s/%s" % (self.d, fname), "w")
		if value is not None:
			f.write("""
[section]
option = %s
	""" % value)
		if content is not None:
			f.write(content)
		f.close()

	def _remove(self, fname):
		os.unlink("%s/%s" % (self.d, fname))
		self.assertTrue(self.c.read('c'))	# we still should have some


	def _getoption(self, f='c'):
		self.assertTrue(self.c.read(f))	# we got some now
		return self.c.getOptions('section', [("int", 'option')])['option']


	def testInaccessibleFile(self):
		f = os.path.join(self.d, "d.conf")  # inaccessible file
		self._write('d.conf', 0)
		self.assertEqual(self._getoption('d'), 0)
		os.chmod(f, 0)
		# fragile test and known to fail e.g. under Cygwin where permissions
		# seems to be not enforced, thus condition
		if not os.access(f, os.R_OK):
			self.assertFalse(self.c.read('d'))	# should not be readable BUT present
		else:
			# SkipTest introduced only in 2.7 thus can't yet use generally
			# raise unittest.SkipTest("Skipping on %s -- access rights are not enforced" % platform)
			pass


	def testOptionalDotDDir(self):
		self.assertFalse(self.c.read('c'))	# nothing is there yet
		self._write("c.conf", "1")
		self.assertEqual(self._getoption(), 1)
		self._write("c.conf", "2")		# overwrite
		self.assertEqual(self._getoption(), 2)
		self._write("c.d/98.conf", "998") # add 1st override in .d/
		self.assertEqual(self._getoption(), 998)
		self._write("c.d/90.conf", "990") # add previously sorted override in .d/
		self.assertEqual(self._getoption(), 998) #  should stay the same
		self._write("c.d/99.conf", "999") # now override in a way without sorting we possibly get a failure
		self.assertEqual(self._getoption(), 999)
		self._write("c.local", "3")		# add override in .local
		self.assertEqual(self._getoption(), 3)
		self._write("c.d/1.local", "4")		# add override in .local
		self.assertEqual(self._getoption(), 4)
		self._remove("c.d/1.local")
		self._remove("c.local")
		self.assertEqual(self._getoption(), 999)
		self._remove("c.d/99.conf")
		self.assertEqual(self._getoption(), 998)
		self._remove("c.d/98.conf")
		self.assertEqual(self._getoption(), 990)
		self._remove("c.d/90.conf")
		self.assertEqual(self._getoption(), 2)

	def testInterpolations(self):
		self.assertFalse(self.c.read('i'))	# nothing is there yet
		self._write("i.conf", value=None, content="""
[DEFAULT]
b = a
zz = the%(__name__)s

[section]
y = 4%(b)s
e = 5${b}
z = %(__name__)s

[section2]
z = 3%(__name__)s
""")
		self.assertTrue(self.c.read('i'))
		self.assertEqual(self.c.sections(), ['section', 'section2'])
		self.assertEqual(self.c.get('section', 'y'), '4a')	 # basic interpolation works
		self.assertEqual(self.c.get('section', 'e'), '5${b}') # no extended interpolation
		self.assertEqual(self.c.get('section', 'z'), 'section') # __name__ works
		self.assertEqual(self.c.get('section', 'zz'), 'thesection') # __name__ works even 'delayed'
		self.assertEqual(self.c.get('section2', 'z'), '3section2') # and differs per section ;)

	def testComments(self):
		self.assertFalse(self.c.read('g'))	# nothing is there yet
		self._write("g.conf", value=None, content="""
[DEFAULT]
# A comment
b = a
c = d ;in line comment
""")
		self.assertTrue(self.c.read('g'))
		self.assertEqual(self.c.get('DEFAULT', 'b'), 'a')
		self.assertEqual(self.c.get('DEFAULT', 'c'), 'd')

class JailReaderTest(LogCaptureTestCase):

	def testIncorrectJail(self):
		jail = JailReader('XXXABSENTXXX', basedir=CONFIG_DIR)
		self.assertRaises(ValueError, jail.read)
		
	def testJailActionEmpty(self):
		jail = JailReader('emptyaction', basedir=IMPERFECT_CONFIG)
		self.assertTrue(jail.read())
		self.assertTrue(jail.getOptions())
		self.assertTrue(jail.isEnabled())
		self.assertTrue(self._is_logged('No filter set for jail emptyaction'))
		self.assertTrue(self._is_logged('No actions were defined for emptyaction'))

	def testJailActionFilterMissing(self):
		jail = JailReader('missingbitsjail', basedir=IMPERFECT_CONFIG)
		self.assertTrue(jail.read())
		self.assertFalse(jail.getOptions())
		self.assertTrue(jail.isEnabled())
		self.assertTrue(self._is_logged("Found no accessible config files for 'filter.d/catchallthebadies' under %s" % IMPERFECT_CONFIG))
		self.assertTrue(self._is_logged('Unable to read the filter'))

	def TODOtestJailActionBrokenDef(self):
		jail = JailReader('brokenactiondef', basedir=IMPERFECT_CONFIG)
		self.assertTrue(jail.read())
		self.assertFalse(jail.getOptions())
		self.assertTrue(jail.isEnabled())
		self.printLog()
		self.assertTrue(self._is_logged('Error in action definition joho[foo'))
		self.assertTrue(self._is_logged('Caught exception: While reading action joho[foo we should have got 1 or 2 groups. Got: 0'))


	if STOCK:
		def testStockSSHJail(self):
			jail = JailReader('sshd', basedir=CONFIG_DIR) # we are running tests from root project dir atm
			self.assertTrue(jail.read())
			self.assertTrue(jail.getOptions())
			self.assertFalse(jail.isEnabled())
			self.assertEqual(jail.getName(), 'sshd')
			jail.setName('ssh-funky-blocker')
			self.assertEqual(jail.getName(), 'ssh-funky-blocker')
		
	def testSplitOption(self):
		# Simple example
		option = "mail-whois[name=SSH]"
		expected = ('mail-whois', {'name': 'SSH'})
		result = JailReader.extractOptions(option)
		self.assertEqual(expected, result)

		self.assertEqual(('mail.who_is', {}), JailReader.extractOptions("mail.who_is"))
		self.assertEqual(('mail.who_is', {'a':'cat', 'b':'dog'}), JailReader.extractOptions("mail.who_is[a=cat,b=dog]"))
		self.assertEqual(('mail--ho_is', {}), JailReader.extractOptions("mail--ho_is"))

		self.assertEqual(('mail--ho_is', {}), JailReader.extractOptions("mail--ho_is['s']"))
		#self.printLog()
		#self.assertTrue(self._is_logged("Invalid argument ['s'] in ''s''"))

		self.assertEqual(('mail', {'a': ','}), JailReader.extractOptions("mail[a=',']"))

		#self.assertRaises(ValueError, JailReader.extractOptions ,'mail-how[')


		# Empty option
		option = "abc[]"
		expected = ('abc', {})
		result = JailReader.extractOptions(option)
		self.assertEqual(expected, result)

		# More complex examples
		option = 'option[opt01=abc,opt02="123",opt03="with=okay?",opt04="andwith,okay...",opt05="how about spaces",opt06="single\'in\'double",opt07=\'double"in"single\',  opt08= leave some space, opt09=one for luck, opt10=, opt11=]'
		expected = ('option', {
			'opt01': "abc",
			'opt02': "123",
			'opt03': "with=okay?",
			'opt04': "andwith,okay...",
			'opt05': "how about spaces",
			'opt06': "single'in'double",
			'opt07': "double\"in\"single",
			'opt08': "leave some space",
			'opt09': "one for luck",
			'opt10': "",
			'opt11': "",
		})
		result = JailReader.extractOptions(option)
		self.assertEqual(expected, result)

	def testGlob(self):
		d = tempfile.mkdtemp(prefix="f2b-temp")
		# Generate few files
		# regular file
		f1 = os.path.join(d, 'f1')
		open(f1, 'w').close()
		# dangling link
		f2 = os.path.join(d, 'f2')
		os.symlink('nonexisting',f2)

		# must be only f1
		self.assertEqual(JailReader._glob(os.path.join(d, '*')), [f1])
		# since f2 is dangling -- empty list
		self.assertEqual(JailReader._glob(f2), [])
		self.assertTrue(self._is_logged('File %s is a dangling link, thus cannot be monitored' % f2))
		self.assertEqual(JailReader._glob(os.path.join(d, 'nonexisting')), [])
		os.remove(f1)
		os.remove(f2)
		os.rmdir(d)

		
class FilterReaderTest(unittest.TestCase):

	def testConvert(self):
		output = [['set', 'testcase01', 'addfailregex',
			"^\\s*(?:\\S+ )?(?:kernel: \\[\\d+\\.\\d+\\] )?(?:@vserver_\\S+ )"
			"?(?:(?:\\[\\d+\\])?:\\s+[\\[\\(]?sshd(?:\\(\\S+\\))?[\\]\\)]?:?|"
			"[\\[\\(]?sshd(?:\\(\\S+\\))?[\\]\\)]?:?(?:\\[\\d+\\])?:)?\\s*(?:"
			"error: PAM: )?Authentication failure for .* from <HOST>\\s*$"],
			['set', 'testcase01', 'addfailregex',
			"^\\s*(?:\\S+ )?(?:kernel: \\[\\d+\\.\\d+\\] )?(?:@vserver_\\S+ )"
			"?(?:(?:\\[\\d+\\])?:\\s+[\\[\\(]?sshd(?:\\(\\S+\\))?[\\]\\)]?:?|"
			"[\\[\\(]?sshd(?:\\(\\S+\\))?[\\]\\)]?:?(?:\\[\\d+\\])?:)?\\s*(?:"
			"error: PAM: )?User not known to the underlying authentication mo"
			"dule for .* from <HOST>\\s*$"],
			['set', 'testcase01', 'addfailregex',
			"^\\s*(?:\\S+ )?(?:kernel: \\[\\d+\\.\\d+\\] )?(?:@vserver_\\S+ )"
			"?(?:(?:\\[\\d+\\])?:\\s+[\\[\\(]?sshd(?:\\(\\S+\\))?[\\]\\)]?:?|"
			"[\\[\\(]?sshd(?:\\(\\S+\\))?[\\]\\)]?:?(?:\\[\\d+\\])?:)?\\s*(?:"
			"error: PAM: )?User not known to the\\nunderlying authentication."
			"+$<SKIPLINES>^.+ module for .* from <HOST>\\s*$"],
			['set', 'testcase01', 'addignoreregex', 
			"^.+ john from host 192.168.1.1\\s*$"],
			['set', 'testcase01', 'addjournalmatch',
				"_COMM=sshd", "+", "_SYSTEMD_UNIT=sshd.service", "_UID=0"],
			['set', 'testcase01', 'addjournalmatch',
				"FIELD= with spaces ", "+", "AFIELD= with + char and spaces"],
			['set', 'testcase01', 'datepattern', "%Y %m %d %H:%M:%S"],
			['set', 'testcase01', 'maxlines', "1"], # Last for overide test
		]
		filterReader = FilterReader("testcase01", "testcase01", {})
		filterReader.setBaseDir(TEST_FILES_DIR)
		filterReader.read()
		#filterReader.getOptions(["failregex", "ignoreregex"])
		filterReader.getOptions(None)

		# Add sort as configreader uses dictionary and therefore order
		# is unreliable
		self.assertEqual(sorted(filterReader.convert()), sorted(output))

		filterReader = FilterReader(
			"testcase01", "testcase01", {'maxlines': "5"})
		filterReader.setBaseDir(TEST_FILES_DIR)
		filterReader.read()
		#filterReader.getOptions(["failregex", "ignoreregex"])
		filterReader.getOptions(None)
		output[-1][-1] = "5"
		self.assertEqual(sorted(filterReader.convert()), sorted(output))


	def testFilterReaderSubstitionDefault(self):
		output = [['set', 'jailname', 'addfailregex', 'to=sweet@example.com fromip=<IP>']]
		filterReader = FilterReader('substition', "jailname", {})
		filterReader.setBaseDir(TEST_FILES_DIR)
		filterReader.read()
		filterReader.getOptions(None)
		c = filterReader.convert()
		self.assertEqual(sorted(c), sorted(output))

	def testFilterReaderSubstitionSet(self):
		output = [['set', 'jailname', 'addfailregex', 'to=sour@example.com fromip=<IP>']]
		filterReader = FilterReader('substition', "jailname", {'honeypot': 'sour@example.com'})
		filterReader.setBaseDir(TEST_FILES_DIR)
		filterReader.read()
		filterReader.getOptions(None)
		c = filterReader.convert()
		self.assertEqual(sorted(c), sorted(output))

	def testFilterReaderSubstitionFail(self):
		filterReader = FilterReader('substition', "jailname", {'honeypot': '<sweet>', 'sweet': '<honeypot>'})
		filterReader.setBaseDir(TEST_FILES_DIR)
		filterReader.read()
		filterReader.getOptions(None)
		self.assertRaises(ValueError, FilterReader.convert, filterReader)


class JailsReaderTest(LogCaptureTestCase):

	def testProvidingBadBasedir(self):
		if not os.path.exists('/XXX'):
			reader = JailsReader(basedir='/XXX')
			self.assertRaises(ValueError, reader.read)

	def testReadTestJailConf(self):
		jails = JailsReader(basedir=IMPERFECT_CONFIG)
		self.assertTrue(jails.read())
		self.assertFalse(jails.getOptions())
		self.assertRaises(ValueError, jails.convert)
		comm_commands = jails.convert(allow_no_files=True)
		self.maxDiff = None
		self.assertEqual(sorted(comm_commands),
			sorted([['add', 'emptyaction', 'auto'],
			 ['add', 'missinglogfiles', 'auto'],
			 ['set', 'missinglogfiles', 'addfailregex', '<IP>'],
			 ['add', 'brokenaction', 'auto'],
			 ['set', 'brokenaction', 'addfailregex', '<IP>'],
			 ['set', 'brokenaction', 'addaction', 'brokenaction'],
			 ['set',
			  'brokenaction',
			  'action',
			  'brokenaction',
			  'actionban',
			  'hit with big stick <ip>'],
			 ['add', 'parse_to_end_of_jail.conf', 'auto'],
			 ['set', 'parse_to_end_of_jail.conf', 'addfailregex', '<IP>'],
			 ['start', 'emptyaction'],
			 ['start', 'missinglogfiles'],
			 ['start', 'brokenaction'],
			 ['start', 'parse_to_end_of_jail.conf'],]))
		self.assertTrue(self._is_logged("Errors in jail 'missingbitsjail'. Skipping..."))
		self.assertTrue(self._is_logged("No file(s) found for glob /weapons/of/mass/destruction"))

	if STOCK:
		def testReadStockJailConf(self):
			jails = JailsReader(basedir=CONFIG_DIR) # we are running tests from root project dir atm
			self.assertTrue(jails.read())		  # opens fine
			self.assertTrue(jails.getOptions())	  # reads fine
			comm_commands = jails.convert()
			# by default None of the jails is enabled and we get no
			# commands to communicate to the server
			self.assertEqual(comm_commands, [])

			# TODO: make sure this is handled well
			## We should not "read" some bogus jail
			#old_comm_commands = comm_commands[:]   # make a copy
			#self.assertRaises(ValueError, jails.getOptions, "BOGUS")
			#self.printLog()
			#self.assertTrue(self._is_logged("No section: 'BOGUS'"))
			## and there should be no side-effects
			#self.assertEqual(jails.convert(), old_comm_commands)

			allFilters = set()

			# All jails must have filter and action set
			# TODO: evolve into a parametric test
			for jail in jails.sections():
				if jail == 'INCLUDES':
					continue
				filterName = jails.get(jail, 'filter')
				allFilters.add(filterName)
				self.assertTrue(len(filterName))
				# moreover we must have a file for it
				# and it must be readable as a Filter
				filterReader = FilterReader(filterName, jail, {})
				filterReader.setBaseDir(CONFIG_DIR)
				self.assertTrue(filterReader.read(),"Failed to read filter:" + filterName)		  # opens fine
				filterReader.getOptions({})	  # reads fine

				#  test if filter has failregex set
				self.assertTrue(filterReader._opts.get('failregex', '').strip())

				actions = jails.get(jail, 'action')
				self.assertTrue(len(actions.strip()))

				# somewhat duplicating here what is done in JailsReader if
				# the jail is enabled
				for act in actions.split('\n'):
					actName, actOpt = JailReader.extractOptions(act)
					self.assertTrue(len(actName))
					self.assertTrue(isinstance(actOpt, dict))
					if actName == 'iptables-multiport':
						self.assertTrue('port' in actOpt)

					actionReader = ActionReader(
						actName, jail, {}, basedir=CONFIG_DIR)
					self.assertTrue(actionReader.read())
					actionReader.getOptions({})	  # populate _opts
					cmds = actionReader.convert()
					self.assertTrue(len(cmds))

					# all must have some actionban
					self.assertTrue(actionReader._opts.get('actionban', '').strip())

		# Verify that all filters found under config/ have a jail
		def testReadStockJailFilterComplete(self):
			jails = JailsReader(basedir=CONFIG_DIR, force_enable=True)
			self.assertTrue(jails.read())             # opens fine
			self.assertTrue(jails.getOptions())       # reads fine
			# grab all filter names
			filters = set(os.path.splitext(os.path.split(a)[1])[0]
				for a in glob.glob(os.path.join('config', 'filter.d', '*.conf'))
					if not a.endswith('common.conf'))
			filters_jail = set(jail.options['filter'] for jail in jails.jails)
			self.maxDiff = None
			self.assertTrue(filters.issubset(filters_jail),
					"More filters exists than are referenced in stock jail.conf %r" % filters.difference(filters_jail))
			self.assertTrue(filters_jail.issubset(filters),
					"Stock jail.conf references non-existent filters %r" % filters_jail.difference(filters))

		def testReadStockJailConfForceEnabled(self):
			# more of a smoke test to make sure that no obvious surprises
			# on users' systems when enabling shipped jails
			jails = JailsReader(basedir=CONFIG_DIR, force_enable=True) # we are running tests from root project dir atm
			self.assertTrue(jails.read())		  # opens fine
			self.assertTrue(jails.getOptions())	  # reads fine
			comm_commands = jails.convert(allow_no_files=True)

			# by default we have lots of jails ;)
			self.assertTrue(len(comm_commands))

			# and we know even some of them by heart
			for j in ['sshd', 'recidive']:
				# by default we have 'auto' backend ATM
				self.assertTrue(['add', j, 'auto'] in comm_commands)
				# and warn on useDNS
				self.assertTrue(['set', j, 'usedns', 'warn'] in comm_commands)
				self.assertTrue(['start', j] in comm_commands)

			# last commands should be the 'start' commands
			self.assertEqual(comm_commands[-1][0], 'start')

			for j in  jails._JailsReader__jails:
				actions = j._JailReader__actions
				jail_name = j.getName()
				# make sure that all of the jails have actions assigned,
				# otherwise it makes little to no sense
				self.assertTrue(len(actions),
								msg="No actions found for jail %s" % jail_name)

				# Test for presence of blocktype (in relation to gh-232)
				for action in actions:
					commands = action.convert()
					action_name = action.getName()
					if '<blocktype>' in str(commands):
						# Verify that it is among cInfo
						self.assertTrue('blocktype' in action._initOpts)
						# Verify that we have a call to set it up
						blocktype_present = False
						target_command = ['set', jail_name, 'action', action_name, 'blocktype']
						for command in commands:
							if (len(command) > 5 and
								command[:5] == target_command):
								blocktype_present = True
								continue
						self.assertTrue(
							blocktype_present,
							msg="Found no %s command among %s"
								% (target_command, str(commands)) )


		def testStockConfigurator(self):
			configurator = Configurator()
			configurator.setBaseDir(CONFIG_DIR)
			self.assertEqual(configurator.getBaseDir(), CONFIG_DIR)

			configurator.readEarly()
			opts = configurator.getEarlyOptions()
			# our current default settings
			self.assertEqual(opts['socket'], '/var/run/fail2ban/fail2ban.sock')
			self.assertEqual(opts['pidfile'], '/var/run/fail2ban/fail2ban.pid')

			configurator.getOptions()
			configurator.convertToProtocol()
			commands = configurator.getConfigStream()
			# and there is logging information left to be passed into the
			# server
			self.assertEqual(sorted(commands),
							 [['set', 'dbfile',
								'/var/lib/fail2ban/fail2ban.sqlite3'],
							  ['set', 'dbpurgeage', 86400],
							  ['set', 'loglevel', "INFO"],
							  ['set', 'logtarget', '/var/log/fail2ban.log']])

			# and if we force change configurator's fail2ban's baseDir
			# there should be an error message (test visually ;) --
			# otherwise just a code smoke test)
			configurator._Configurator__jails.setBaseDir('/tmp')
			self.assertEqual(configurator._Configurator__jails.getBaseDir(), '/tmp')
			self.assertEqual(configurator.getBaseDir(), CONFIG_DIR)

	def testMultipleSameAction(self):
		basedir = tempfile.mkdtemp("fail2ban_conf")
		os.mkdir(os.path.join(basedir, "filter.d"))
		os.mkdir(os.path.join(basedir, "action.d"))
		open(os.path.join(basedir, "action.d", "testaction1.conf"), 'w').close()
		open(os.path.join(basedir, "filter.d", "testfilter1.conf"), 'w').close()
		jailfd = open(os.path.join(basedir, "jail.conf"), 'w')
		jailfd.write("""
[testjail1]
enabled = true
action = testaction1[actname=test1]
         testaction1[actname=test2]
         testaction.py
         testaction.py[actname=test3]
filter = testfilter1
""")
		jailfd.close()
		jails = JailsReader(basedir=basedir)
		self.assertTrue(jails.read())
		self.assertTrue(jails.getOptions())
		comm_commands = jails.convert(allow_no_files=True)

		add_actions = [comm[3:] for comm in comm_commands
			if comm[:3] == ['set', 'testjail1', 'addaction']]

		self.assertEqual(len(set(action[0] for action in add_actions)), 4)

		# Python actions should not be passed `actname`
		self.assertEqual(add_actions[-1][-1], "{}")

		shutil.rmtree(basedir)

########NEW FILE########
__FILENAME__ = databasetestcase
# emacs: -*- mode: python; py-indent-offset: 4; indent-tabs-mode: t -*-
# vi: set ft=python sts=4 ts=4 sw=4 noet :

# This file is part of Fail2Ban.
#
# Fail2Ban is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# Fail2Ban is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with Fail2Ban; if not, write to the Free Software
# Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA  02110-1301, USA.

# Fail2Ban developers

__copyright__ = "Copyright (c) 2013 Steven Hiscocks"
__license__ = "GPL"

import os
import sys
import unittest
import tempfile
import sqlite3
import shutil

from ..server.filter import FileContainer
from ..server.mytime import MyTime
from ..server.ticket import FailTicket
from .dummyjail import DummyJail
try:
	from ..server.database import Fail2BanDb
except ImportError:
	Fail2BanDb = None

TEST_FILES_DIR = os.path.join(os.path.dirname(__file__), "files")

class DatabaseTest(unittest.TestCase):

	def setUp(self):
		"""Call before every test case."""
		if Fail2BanDb is None and sys.version_info >= (2,7): # pragma: no cover
			raise unittest.SkipTest(
				"Unable to import fail2ban database module as sqlite is not "
				"available.")
		elif Fail2BanDb is None:
			return
		_, self.dbFilename = tempfile.mkstemp(".db", "fail2ban_")
		self.db = Fail2BanDb(self.dbFilename)

	def tearDown(self):
		"""Call after every test case."""
		if Fail2BanDb is None: # pragma: no cover
			return
		# Cleanup
		os.remove(self.dbFilename)

	def testGetFilename(self):
		if Fail2BanDb is None: # pragma: no cover
			return
		self.assertEqual(self.dbFilename, self.db.filename)

	def testCreateInvalidPath(self):
		if Fail2BanDb is None: # pragma: no cover
			return
		self.assertRaises(
			sqlite3.OperationalError,
			Fail2BanDb,
			"/this/path/should/not/exist")

	def testCreateAndReconnect(self):
		if Fail2BanDb is None: # pragma: no cover
			return
		self.testAddJail()
		# Reconnect...
		self.db = Fail2BanDb(self.dbFilename)
		# and check jail of same name still present
		self.assertTrue(
			self.jail.name in self.db.getJailNames(),
			"Jail not retained in Db after disconnect reconnect.")

	def testUpdateDb(self):
		if Fail2BanDb is None: # pragma: no cover
			return
		shutil.copyfile(
			os.path.join(TEST_FILES_DIR, 'database_v1.db'), self.dbFilename)
		self.db = Fail2BanDb(self.dbFilename)
		self.assertEqual(self.db.getJailNames(), set(['DummyJail #29162448 with 0 tickets']))
		self.assertEqual(self.db.getLogPaths(), set(['/tmp/Fail2BanDb_pUlZJh.log']))
		ticket = FailTicket("127.0.0.1", 1388009242.26, [u"abc\n"])
		self.assertEqual(self.db.getBans()[0], ticket)

		self.assertEqual(self.db.updateDb(Fail2BanDb.__version__), Fail2BanDb.__version__)
		self.assertRaises(NotImplementedError, self.db.updateDb, Fail2BanDb.__version__ + 1)
		os.remove(self.db._dbBackupFilename)

	def testAddJail(self):
		if Fail2BanDb is None: # pragma: no cover
			return
		self.jail = DummyJail()
		self.db.addJail(self.jail)
		self.assertTrue(
			self.jail.name in self.db.getJailNames(),
			"Jail not added to database")

	def testAddLog(self):
		if Fail2BanDb is None: # pragma: no cover
			return
		self.testAddJail() # Jail required

		_, filename = tempfile.mkstemp(".log", "Fail2BanDb_")
		self.fileContainer = FileContainer(filename, "utf-8")

		self.db.addLog(self.jail, self.fileContainer)

		self.assertTrue(filename in self.db.getLogPaths(self.jail))
		os.remove(filename)

	def testUpdateLog(self):
		if Fail2BanDb is None: # pragma: no cover
			return
		self.testAddLog() # Add log file

		# Write some text
		filename = self.fileContainer.getFileName()
		file_ = open(filename, "w")
		file_.write("Some text to write which will change md5sum\n")
		file_.close()
		self.fileContainer.open()
		self.fileContainer.readline()
		self.fileContainer.close()

		# Capture position which should be after line just written
		lastPos = self.fileContainer.getPos()
		self.assertTrue(lastPos > 0)
		self.db.updateLog(self.jail, self.fileContainer)

		# New FileContainer for file
		self.fileContainer = FileContainer(filename, "utf-8")
		self.assertEqual(self.fileContainer.getPos(), 0)

		# Database should return previous position in file
		self.assertEqual(
			self.db.addLog(self.jail, self.fileContainer), lastPos)

		# Change md5sum
		file_ = open(filename, "w") # Truncate
		file_.write("Some different text to change md5sum\n")
		file_.close()

		self.fileContainer = FileContainer(filename, "utf-8")
		self.assertEqual(self.fileContainer.getPos(), 0)

		# Database should be aware of md5sum change, such doesn't return
		# last position in file
		self.assertEqual(
			self.db.addLog(self.jail, self.fileContainer), None)
		os.remove(filename)

	def testAddBan(self):
		if Fail2BanDb is None: # pragma: no cover
			return
		self.testAddJail()
		ticket = FailTicket("127.0.0.1", 0, ["abc\n"])
		self.db.addBan(self.jail, ticket)

		self.assertEqual(len(self.db.getBans(jail=self.jail)), 1)
		self.assertTrue(
			isinstance(self.db.getBans(jail=self.jail)[0], FailTicket))

	def testGetBansWithTime(self):
		if Fail2BanDb is None: # pragma: no cover
			return
		self.testAddJail()
		self.db.addBan(
			self.jail, FailTicket("127.0.0.1", MyTime.time() - 60, ["abc\n"]))
		self.db.addBan(
			self.jail, FailTicket("127.0.0.1", MyTime.time() - 40, ["abc\n"]))
		self.assertEqual(len(self.db.getBans(jail=self.jail,bantime=50)), 1)
		self.assertEqual(len(self.db.getBans(jail=self.jail,bantime=20)), 0)
		# Negative values are for persistent bans, and such all bans should
		# be returned
		self.assertEqual(len(self.db.getBans(jail=self.jail,bantime=-1)), 2)

	def testGetBansMerged(self):
		if Fail2BanDb is None: # pragma: no cover
			return
		self.testAddJail()

		jail2 = DummyJail()
		self.db.addJail(jail2)

		ticket = FailTicket("127.0.0.1", MyTime.time() - 40, ["abc\n"])
		ticket.setAttempt(10)
		self.db.addBan(self.jail, ticket)
		ticket = FailTicket("127.0.0.1", MyTime.time() - 30, ["123\n"])
		ticket.setAttempt(20)
		self.db.addBan(self.jail, ticket)
		ticket = FailTicket("127.0.0.2", MyTime.time() - 20, ["ABC\n"])
		ticket.setAttempt(30)
		self.db.addBan(self.jail, ticket)
		ticket = FailTicket("127.0.0.1", MyTime.time() - 10, ["ABC\n"])
		ticket.setAttempt(40)
		self.db.addBan(jail2, ticket)

		# All for IP 127.0.0.1
		ticket = self.db.getBansMerged("127.0.0.1")
		self.assertEqual(ticket.getIP(), "127.0.0.1")
		self.assertEqual(ticket.getAttempt(), 70)
		self.assertEqual(ticket.getMatches(), ["abc\n", "123\n", "ABC\n"])

		# All for IP 127.0.0.1 for single jail
		ticket = self.db.getBansMerged("127.0.0.1", jail=self.jail)
		self.assertEqual(ticket.getIP(), "127.0.0.1")
		self.assertEqual(ticket.getAttempt(), 30)
		self.assertEqual(ticket.getMatches(), ["abc\n", "123\n"])

		# Should cache result if no extra bans added
		self.assertEqual(
			id(ticket),
			id(self.db.getBansMerged("127.0.0.1", jail=self.jail)))

		newTicket = FailTicket("127.0.0.2", MyTime.time() - 20, ["ABC\n"])
		ticket.setAttempt(40)
		# Add ticket, but not for same IP, so cache still valid
		self.db.addBan(self.jail, newTicket)
		self.assertEqual(
			id(ticket),
			id(self.db.getBansMerged("127.0.0.1", jail=self.jail)))

		newTicket = FailTicket("127.0.0.1", MyTime.time() - 10, ["ABC\n"])
		ticket.setAttempt(40)
		self.db.addBan(self.jail, newTicket)
		# Added ticket, so cache should have been cleared
		self.assertNotEqual(
			id(ticket),
			id(self.db.getBansMerged("127.0.0.1", jail=self.jail)))

		tickets = self.db.getBansMerged()
		self.assertEqual(len(tickets), 2)
		self.assertEqual(
			sorted(list(set(ticket.getIP() for ticket in tickets))),
			sorted([ticket.getIP() for ticket in tickets]))

		tickets = self.db.getBansMerged(jail=jail2)
		self.assertEqual(len(tickets), 1)

		tickets = self.db.getBansMerged(bantime=25)
		self.assertEqual(len(tickets), 2)
		tickets = self.db.getBansMerged(bantime=15)
		self.assertEqual(len(tickets), 1)
		tickets = self.db.getBansMerged(bantime=5)
		self.assertEqual(len(tickets), 0)
		# Negative values are for persistent bans, and such all bans should
		# be returned
		tickets = self.db.getBansMerged(bantime=-1)
		self.assertEqual(len(tickets), 2)

	def testPurge(self):
		if Fail2BanDb is None: # pragma: no cover
			return
		self.testAddJail() # Add jail

		self.db.purge() # Jail enabled by default so shouldn't be purged
		self.assertEqual(len(self.db.getJailNames()), 1)

		self.db.delJail(self.jail)
		self.db.purge() # Should remove jail
		self.assertEqual(len(self.db.getJailNames()), 0)

		self.testAddBan()
		self.db.delJail(self.jail)
		self.db.purge() # Purge should remove all bans
		self.assertEqual(len(self.db.getJailNames()), 0)
		self.assertEqual(len(self.db.getBans(jail=self.jail)), 0)

		# Should leave jail
		self.testAddJail()
		self.db.addBan(
			self.jail, FailTicket("127.0.0.1", MyTime.time(), ["abc\n"]))
		self.db.delJail(self.jail)
		self.db.purge() # Should leave jail as ban present
		self.assertEqual(len(self.db.getJailNames()), 1)
		self.assertEqual(len(self.db.getBans(jail=self.jail)), 1)

########NEW FILE########
__FILENAME__ = datedetectortestcase
# emacs: -*- mode: python; py-indent-offset: 4; indent-tabs-mode: t -*-
# vi: set ft=python sts=4 ts=4 sw=4 noet :

# This file is part of Fail2Ban.
#
# Fail2Ban is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# Fail2Ban is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with Fail2Ban; if not, write to the Free Software
# Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA  02110-1301, USA.

# Author: Cyril Jaquier
# 

__author__ = "Cyril Jaquier"
__copyright__ = "Copyright (c) 2004 Cyril Jaquier"
__license__ = "GPL"

import unittest
import time
import datetime

from ..server.datedetector import DateDetector
from ..server.datetemplate import DateTemplate
from .utils import setUpMyTime, tearDownMyTime

class DateDetectorTest(unittest.TestCase):

	def setUp(self):
		"""Call before every test case."""
		setUpMyTime()
		self.__datedetector = DateDetector()
		self.__datedetector.addDefaultTemplate()

	def tearDown(self):
		"""Call after every test case."""
		tearDownMyTime()
	
	def testGetEpochTime(self):
		log = "1138049999 [sshd] error: PAM: Authentication failure"
		#date = [2006, 1, 23, 21, 59, 59, 0, 23, 0]
		dateUnix = 1138049999.0

		( datelog, matchlog ) = self.__datedetector.getTime(log)
		self.assertEqual(datelog, dateUnix)
		self.assertEqual(matchlog.group(), '1138049999')
	
	def testGetTime(self):
		log = "Jan 23 21:59:59 [sshd] error: PAM: Authentication failure"
		dateUnix = 1106513999.0
		# yoh: testing only up to 6 elements, since the day of the week
		#      is not correctly determined atm, since year is not present
		#      in the log entry.  Since this doesn't effect the operation
		#      of fail2ban -- we just ignore incorrect day of the week
		( datelog, matchlog ) = self.__datedetector.getTime(log)
		self.assertEqual(datelog, dateUnix)
		self.assertEqual(matchlog.group(), 'Jan 23 21:59:59')

	def testVariousTimes(self):
		"""Test detection of various common date/time formats f2b should understand
		"""
		dateUnix = 1106513999.0

		for anchored, sdate in (
			(False, "Jan 23 21:59:59"),
			(False, "Sun Jan 23 21:59:59 2005"),
			(False, "Sun Jan 23 21:59:59"),
			(False, "2005/01/23 21:59:59"),
			(False, "2005.01.23 21:59:59"),
			(False, "23/01/2005 21:59:59"),
			(False, "23/01/05 21:59:59"),
			(False, "23/Jan/2005:21:59:59"),
			(False, "23/Jan/2005:21:59:59 +0100"),
			(False, "01/23/2005:21:59:59"),
			(False, "2005-01-23 21:59:59"),
		    (False, "2005-01-23 21:59:59,000"),	  # proftpd
			(False, "23-Jan-2005 21:59:59"),
			(False, "23-Jan-2005 21:59:59.02"),
			(False, "23-Jan-2005 21:59:59 +0100"),
			(False, "23-01-2005 21:59:59"),
			(False, "01-23-2005 21:59:59.252"), # reported on f2b, causes Feb29 fix to break
			(False, "@4000000041f4104f00000000"), # TAI64N
			(False, "2005-01-23T20:59:59.252Z"), #ISO 8601 (UTC)
			(False, "2005-01-23T15:59:59-05:00"), #ISO 8601 with TZ
			(False, "2005-01-23T21:59:59"), #ISO 8601 no TZ, assume local
			(True,  "<01/23/05@21:59:59>"),
			(True,  "050123 21:59:59"), # MySQL
			(True,  "Jan-23-05 21:59:59"), # ASSP like
			(False, "Jan 23, 2005 9:59:59 PM"), # Apache Tomcat
			(True,  "1106513999"), # Regular epoch
			(True,  "1106513999.000"), # Regular epoch with millisec
			(False, "audit(1106513999.000:987)"), # SELinux
			):
			for should_match, prefix in ((True,     ""),
										 (not anchored, "bogus-prefix ")):
				log = prefix + sdate + "[sshd] error: PAM: Authentication failure"

				logtime = self.__datedetector.getTime(log)
				if should_match:
					self.assertNotEqual(logtime, None, "getTime retrieved nothing: failure for %s, anchored: %r, log: %s" % ( sdate, anchored, log))
					( logUnix, logMatch ) = logtime
					self.assertEqual(logUnix, dateUnix, "getTime comparison failure for %s: \"%s\" is not \"%s\"" % (sdate, logUnix, dateUnix))
					if sdate.startswith('audit('):
						# yes, special case, the group only matches the number
						self.assertEqual(logMatch.group(), '1106513999.000')
					else:
						self.assertEqual(logMatch.group(), sdate)
				else:
					self.assertEqual(logtime, None, "getTime should have not matched for %r Got: %s" % (sdate, logtime))

	def testStableSortTemplate(self):
		old_names = [x.name for x in self.__datedetector.templates]
		self.__datedetector.sortTemplate()
		# If there were no hits -- sorting should not change the order
		for old_name, n in zip(old_names, self.__datedetector.templates):
			self.assertEqual(old_name, n.name) # "Sort must be stable"

	def testAllUniqueTemplateNames(self):
		self.assertRaises(ValueError, self.__datedetector.appendTemplate,
						  self.__datedetector.templates[0])

	def testFullYearMatch_gh130(self):
		# see https://github.com/fail2ban/fail2ban/pull/130
		# yoh: unfortunately this test is not really effective to reproduce the
		#      situation but left in place to assure consistent behavior
		mu = time.mktime(datetime.datetime(2012, 10, 11, 2, 37, 17).utctimetuple())
		logdate = self.__datedetector.getTime('2012/10/11 02:37:17 [error] 18434#0')
		self.assertNotEqual(logdate, None)
		( logTime, logMatch ) = logdate
		self.assertEqual(logTime, mu)
		self.assertEqual(logMatch.group(), '2012/10/11 02:37:17')
		self.__datedetector.sortTemplate()
		# confuse it with year being at the end
		for i in xrange(10):
			( logTime, logMatch ) =	self.__datedetector.getTime('11/10/2012 02:37:17 [error] 18434#0')
			self.assertEqual(logTime, mu)
			self.assertEqual(logMatch.group(), '11/10/2012 02:37:17')
		self.__datedetector.sortTemplate()
		# and now back to the original
		( logTime, logMatch ) = self.__datedetector.getTime('2012/10/11 02:37:17 [error] 18434#0')
		self.assertEqual(logTime, mu)
		self.assertEqual(logMatch.group(), '2012/10/11 02:37:17')

	def testDateTemplate(self):
			t = DateTemplate()
			t.setRegex('^a{3,5}b?c*$')
			self.assertEqual(t.getRegex(), '^a{3,5}b?c*$')
			self.assertRaises(Exception, t.getDate, '')
			self.assertEqual(t.matchDate('aaaac').group(), 'aaaac')


#	def testDefaultTempate(self):
#		self.__datedetector.setDefaultRegex("^\S{3}\s{1,2}\d{1,2} \d{2}:\d{2}:\d{2}")
#		self.__datedetector.setDefaultPattern("%b %d %H:%M:%S")
#		
#		log = "Jan 23 21:59:59 [sshd] error: PAM: Authentication failure"
#		date = [2005, 1, 23, 21, 59, 59, 1, 23, -1]
#		dateUnix = 1106513999.0
#		
#		self.assertEqual(self.__datedetector.getTime(log), date)
#		self.assertEqual(self.__datedetector.getUnixTime(log), dateUnix)
	

########NEW FILE########
__FILENAME__ = dummyjail
# emacs: -*- mode: python; py-indent-offset: 4; indent-tabs-mode: t -*-
# vi: set ft=python sts=4 ts=4 sw=4 noet :

# This file is part of Fail2Ban.
#
# Fail2Ban is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# Fail2Ban is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with Fail2Ban; if not, write to the Free Software
# Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA  02110-1301, USA.

# Fail2Ban developers

__copyright__ = "Copyright (c) 2012 Yaroslav Halchenko"
__license__ = "GPL"

from threading import Lock

from ..server.actions import Actions

class DummyJail(object):
	"""A simple 'jail' to suck in all the tickets generated by Filter's
	"""
	def __init__(self):
		self.lock = Lock()
		self.queue = []
		self.idle = False
		self.database = None
		self.actions = Actions(self)

	def __len__(self):
		try:
			self.lock.acquire()
			return len(self.queue)
		finally:
			self.lock.release()

	def putFailTicket(self, ticket):
		try:
			self.lock.acquire()
			self.queue.append(ticket)
		finally:
			self.lock.release()

	def getFailTicket(self):
		try:
			self.lock.acquire()
			try:
				return self.queue.pop()
			except IndexError:
				return False
		finally:
			self.lock.release()

	@property
	def name(self):
		return "DummyJail #%s with %d tickets" % (id(self), len(self))

########NEW FILE########
__FILENAME__ = failmanagertestcase
# emacs: -*- mode: python; py-indent-offset: 4; indent-tabs-mode: t -*-
# vi: set ft=python sts=4 ts=4 sw=4 noet :

# This file is part of Fail2Ban.
#
# Fail2Ban is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# Fail2Ban is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with Fail2Ban; if not, write to the Free Software
# Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA  02110-1301, USA.

# Author: Cyril Jaquier
# 

__author__ = "Cyril Jaquier"
__copyright__ = "Copyright (c) 2004 Cyril Jaquier"
__license__ = "GPL"

import unittest

from ..server.failmanager import FailManager, FailManagerEmpty
from ..server.ticket import FailTicket

class AddFailure(unittest.TestCase):

	def setUp(self):
		"""Call before every test case."""
		self.__items = [[u'193.168.0.128', 1167605999.0],
					    [u'193.168.0.128', 1167605999.0],
					    [u'193.168.0.128', 1167605999.0],
					    [u'193.168.0.128', 1167605999.0],
					    [u'193.168.0.128', 1167605999.0],
					    ['87.142.124.10', 1167605999.0],
					    ['87.142.124.10', 1167605999.0],
					    ['87.142.124.10', 1167605999.0],
					    ['100.100.10.10', 1000000000.0],
					    ['100.100.10.10', 1000000500.0],
					    ['100.100.10.10', 1000001000.0],
					    ['100.100.10.10', 1000001500.0],
					    ['100.100.10.10', 1000002000.0]]
		
		self.__failManager = FailManager()
		for i in self.__items:
			self.__failManager.addFailure(FailTicket(i[0], i[1]))

	def tearDown(self):
		"""Call after every test case."""
	
	def testFailManagerAdd(self):
		self.assertEqual(self.__failManager.size(), 3)
		self.assertEqual(self.__failManager.getFailTotal(), 13)
		self.__failManager.setFailTotal(0)
		self.assertEqual(self.__failManager.getFailTotal(), 0)
		self.__failManager.setFailTotal(13)
	
	def testFailManagerMaxTime(self):
		self.assertEqual(self.__failManager.getMaxTime(), 600)
		self.__failManager.setMaxTime(13)
		self.assertEqual(self.__failManager.getMaxTime(), 13)
		self.__failManager.setMaxTime(600)

	def _testDel(self):
		self.__failManager.delFailure('193.168.0.128')
		self.__failManager.delFailure('111.111.1.111')
		
		self.assertEqual(self.__failManager.size(), 1)
		
	def testCleanupOK(self):
		timestamp = 1167606999.0
		self.__failManager.cleanup(timestamp)
		self.assertEqual(self.__failManager.size(), 0)
		
	def testCleanupNOK(self):
		timestamp = 1167605990.0
		self.__failManager.cleanup(timestamp)
		self.assertEqual(self.__failManager.size(), 2)
	
	def testbanOK(self):
		self.__failManager.setMaxRetry(5)
		#ticket = FailTicket('193.168.0.128', None)
		ticket = self.__failManager.toBan()
		self.assertEqual(ticket.getIP(), "193.168.0.128")
		self.assertTrue(isinstance(ticket.getIP(), str))

		# finish with rudimentary tests of the ticket
		# verify consistent str
		ticket_str = str(ticket)
		ticket_repr = repr(ticket)
		self.assertEqual(
			ticket_str,
			'FailTicket: ip=193.168.0.128 time=1167605999.0 #attempts=5 matches=[]')
		self.assertEqual(
			ticket_repr,
			'FailTicket: ip=193.168.0.128 time=1167605999.0 #attempts=5 matches=[]')
		self.assertFalse(ticket == False)
		# and some get/set-ers otherwise not tested
		ticket.setTime(1000002000.0)
		self.assertEqual(ticket.getTime(), 1000002000.0)
		# and str() adjusted correspondingly
		self.assertEqual(
			str(ticket),
			'FailTicket: ip=193.168.0.128 time=1000002000.0 #attempts=5 matches=[]')
	
	def testbanNOK(self):
		self.__failManager.setMaxRetry(10)
		self.assertRaises(FailManagerEmpty, self.__failManager.toBan)

	def testWindow(self):
		ticket = self.__failManager.toBan()
		self.assertNotEqual(ticket.getIP(), "100.100.10.10")
		ticket = self.__failManager.toBan()
		self.assertNotEqual(ticket.getIP(), "100.100.10.10")
		self.assertRaises(FailManagerEmpty, self.__failManager.toBan)

########NEW FILE########
__FILENAME__ = action

from fail2ban.server.action import ActionBase

class TestAction(ActionBase):

    def __init__(self, jail, name, opt1, opt2=None):
        super(TestAction, self).__init__(jail, name)
        self._logSys.debug("%s initialised" % self.__class__.__name__)
        self.opt1 = opt1
        self.opt2 = opt2
        self._opt3 = "Hello"

    def start(self):
        self._logSys.debug("%s action start" % self.__class__.__name__)

    def stop(self):
        self._logSys.debug("%s action stop" % self.__class__.__name__)

    def ban(self, aInfo):
        self._logSys.debug("%s action ban" % self.__class__.__name__)

    def unban(self, aInfo):
        self._logSys.debug("%s action unban" % self.__class__.__name__)

    def testmethod(self, text):
        return "%s %s %s" % (self._opt3, text, self.opt1)

Action = TestAction

########NEW FILE########
__FILENAME__ = action_errors

from fail2ban.server.action import ActionBase

class TestAction(ActionBase):

    def __init__(self, jail, name):
        super(TestAction, self).__init__(jail, name)

    def start(self):
        raise Exception()

    def stop(self):
        raise Exception()

    def ban(self):
        raise Exception()

    def unban(self):
        raise Exception()

Action = TestAction

########NEW FILE########
__FILENAME__ = action_noAction

from fail2ban.server.action import ActionBase

class TestAction(ActionBase):
    pass

########NEW FILE########
__FILENAME__ = action_nomethod

class TestAction():

    def __init__(self, jail, name):
        pass

    def start(self):
        pass

Action = TestAction

########NEW FILE########
__FILENAME__ = digest
#!/bin/env python
import requests
import md5


def auth(v):

    ha1 = md5.new(username + ':' + realm + ':' + password).hexdigest()
    ha2 = md5.new("GET:" + url).hexdigest()
    
    #response = md5.new(ha1 + ':' + v['nonce'][1:-1] + ':' + v['nc'] + ':' + v['cnonce'][1:-1]
    #                  + ':' + v['qop'][1:-1] + ':' + ha2).hexdigest()
    
    nonce = v['nonce'][1:-1]
    nc=v.get('nc') or ''
    cnonce = v.get('cnonce') or ''
    #opaque = v.get('opaque') or ''
    qop = v['qop'][1:-1]
    algorithm = v['algorithm']
    response = md5.new(ha1 + ':' + nonce + ':' + nc + ':' + cnonce + ':' + qop + ':' + ha2).hexdigest()
    
    p = requests.Request('GET', host + url).prepare()
    #p.headers['Authentication-Info'] = response 
    p.headers['Authorization'] = """
        Digest username="%s",
        algorithm="%s",
        realm="%s",
        uri="%s",
        nonce="%s",
        cnonce="",
        nc="",
        qop=%s,
        response="%s"
    """ % ( username, algorithm, realm, url, nonce, qop, response )
#        opaque="%s",
    print p.method, p.url, p.headers
    s =  requests.Session()
    return s.send(p)

def preauth():
    r = requests.get(host + url)
    print r
    r.headers['www-authenticate'].split(', ')
    return dict([ a.split('=',1) for a in r.headers['www-authenticate'].split(', ') ])


url='/digest/'
host = 'http://localhost:801'

v = preauth()

username="username"
password = "password"
print v

realm = 'so far away'
r = auth(v)

realm = v['Digest realm'][1:-1]

# [Sun Jul 28 21:27:56.549667 2013] [auth_digest:error] [pid 24835:tid 139895297222400] [client 127.0.0.1:57052] AH01788: realm mismatch - got `so far away' but expected `digest private area'


algorithm = v['algorithm']
v['algorithm'] = 'super funky chicken'
r = auth(v)

# [Sun Jul 28 21:41:20 2013] [error] [client 127.0.0.1] Digest: unknown algorithm `super funky chicken' received: /digest/

print r.status_code,r.headers, r.text
v['algorithm'] = algorithm


r = auth(v)
print r.status_code,r.headers, r.text

nonce = v['nonce']
v['nonce']=v['nonce'][5:-5]

r = auth(v)
print r.status_code,r.headers, r.text

# [Sun Jul 28 21:05:31.178340 2013] [auth_digest:error] [pid 24224:tid 139895539455744] [client 127.0.0.1:56906] AH01793: invalid qop `auth' received: /digest/qop_none/


v['nonce']=nonce[0:11] + 'ZZZ' + nonce[14:]

r = auth(v)
print r.status_code,r.headers, r.text

#[Sun Jul 28 21:18:11.769228 2013] [auth_digest:error] [pid 24752:tid 139895505884928] [client 127.0.0.1:56964] AH01776: invalid nonce b9YAiJDiBAZZZ1b1abe02d20063ea3b16b544ea1b0d981c1bafe received - hash is not d42d824dee7aaf50c3ba0a7c6290bd453e3dd35b


url='/digest_time/'
v=preauth()

import time
time.sleep(1)

r = auth(v)
print r.status_code,r.headers, r.text

# Obtained by putting the following code in modules/aaa/mod_auth_digest.c
# in the function initialize_secret
#    {
#       const char *hex = "0123456789abcdef";
#       char secbuff[SECRET_LEN * 4];
#       char *hash = secbuff;
#       int idx;

#       for (idx=0; idx<sizeof(secret); idx++) {
#       *hash++ = hex[secret[idx] >> 4];
#       *hash++ = hex[secret[idx] & 0xF];
#       }
#       *hash = '\0';
#       /* remove comment makings in below for apache-2.4+ */
#       ap_log_error(APLOG_MARK, APLOG_NOTICE, 0, s, /*  APLOGNO(11759) */ "secret: %s", secbuff);
#   }


import sha
import binascii
import base64
import struct

apachesecret = binascii.unhexlify('497d8894adafa5ec7c8c981ddf9c8457da7a90ac')
s = sha.sha(apachesecret)

v=preauth()

print v['nonce']
realm = v['Digest realm'][1:-1]

(t,) = struct.unpack('l',base64.b64decode(v['nonce'][1:13]))

# whee, time travel
t = t + 5540

timepac = base64.b64encode(struct.pack('l',t))

s.update(realm)
s.update(timepac)

v['nonce'] =  v['nonce'][0] + timepac + s.hexdigest() + v['nonce'][-1]

print v

r = auth(v)
#[Mon Jul 29 02:12:55.539813 2013] [auth_digest:error] [pid 9647:tid 139895522670336] [client 127.0.0.1:58474] AH01777: invalid nonce 59QJppTiBAA=b08983fd166ade9840407df1b0f75b9e6e07d88d received - user attempted time travel
print r.status_code,r.headers, r.text

url='/digest_onetime/'
v=preauth()

# Need opaque header handling in auth
r = auth(v)
print r.status_code,r.headers, r.text
r = auth(v)
print r.status_code,r.headers, r.text

########NEW FILE########
__FILENAME__ = ignorecommand
#!/usr/bin/python
import sys
if sys.argv[1] == "10.0.0.1":
	exit(0)
exit(1)

########NEW FILE########
__FILENAME__ = filtertestcase
# emacs: -*- mode: python; py-indent-offset: 4; indent-tabs-mode: t -*-
# vi: set ft=python sts=4 ts=4 sw=4 noet :

# This file is part of Fail2Ban.
#
# Fail2Ban is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# Fail2Ban is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with Fail2Ban; if not, write to the Free Software
# Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA  02110-1301, USA.

# Fail2Ban developers

__copyright__ = "Copyright (c) 2004 Cyril Jaquier; 2012 Yaroslav Halchenko"
__license__ = "GPL"

from __builtin__ import open as fopen
import unittest
import os
import sys
import time
import tempfile
import uuid

try:
	from systemd import journal
except ImportError:
	journal = None

from ..server.jail import Jail
from ..server.filterpoll import FilterPoll
from ..server.filter import Filter, FileFilter, DNSUtils
from ..server.failmanager import FailManagerEmpty
from ..server.mytime import MyTime
from .utils import setUpMyTime, tearDownMyTime, mtimesleep, LogCaptureTestCase
from .dummyjail import DummyJail

TEST_FILES_DIR = os.path.join(os.path.dirname(__file__), "files")

# yoh: per Steven Hiscocks's insight while troubleshooting
# https://github.com/fail2ban/fail2ban/issues/103#issuecomment-15542836
# adding a sufficiently large buffer might help to guarantee that
# writes happen atomically.
def open(*args):
	"""Overload built in open so we could assure sufficiently large buffer

	Explicit .flush would be needed to assure that changes leave the buffer
	"""
	if len(args) == 2:
		# ~50kB buffer should be sufficient for all tests here.
		args = args + (50000,)
	if sys.version_info >= (3,):
		return fopen(*args, **{'encoding': 'utf-8', 'errors': 'ignore'})
	else:
		return fopen(*args)

def _killfile(f, name):
	try:
		f.close()
	except:
		pass
	try:
		os.unlink(name)
	except:
		pass

	# there might as well be the .bak file
	if os.path.exists(name + '.bak'):
		_killfile(None, name + '.bak')


def _assert_equal_entries(utest, found, output, count=None):
	"""Little helper to unify comparisons with the target entries

	and report helpful failure reports instead of millions of seconds ;)
	"""
	utest.assertEqual(found[0], output[0])            # IP
	utest.assertEqual(found[1], count or output[1])   # count
	found_time, output_time = \
				MyTime.localtime(found[2]),\
				MyTime.localtime(output[2])
	utest.assertEqual(found_time, output_time)
	if len(output) > 3 and count is None: # match matches
		# do not check if custom count (e.g. going through them twice)
		if os.linesep != '\n' or sys.platform.startswith('cygwin'):
			# on those where text file lines end with '\r\n', remove '\r'
			srepr = lambda x: repr(x).replace(r'\r', '')
		else:
			srepr = repr
		utest.assertEqual(srepr(found[3]), srepr(output[3]))

def _ticket_tuple(ticket):
	"""Create a tuple for easy comparison from fail ticket
	"""
	attempts = ticket.getAttempt()
	date = ticket.getTime()
	ip = ticket.getIP()
	matches = ticket.getMatches()
	return (ip, attempts, date, matches)

def _assert_correct_last_attempt(utest, filter_, output, count=None):
	"""Additional helper to wrap most common test case

	Test filter to contain target ticket
	"""
	if isinstance(filter_, DummyJail):
		found = _ticket_tuple(filter_.getFailTicket())
	else:
		# when we are testing without jails
		found = _ticket_tuple(filter_.failManager.toBan())

	_assert_equal_entries(utest, found, output, count)

def _copy_lines_between_files(in_, fout, n=None, skip=0, mode='a', terminal_line=""):
	"""Copy lines from one file to another (which might be already open)

	Returns open fout
	"""
	# on old Python st_mtime is int, so we should give at least 1 sec so
	# polling filter could detect the change
	mtimesleep()
	if isinstance(in_, str): # pragma: no branch - only used with str in test cases
		fin = open(in_, 'r')
	else:
		fin = in_
	# Skip
	for i in xrange(skip):
		fin.readline()
	# Read
	i = 0
	lines = []
	while n is None or i < n:
		l = fin.readline()
		if terminal_line is not None and l == terminal_line:
			break
		lines.append(l)
		i += 1
	# Write: all at once and flush
	if isinstance(fout, str):
		fout = open(fout, mode)
	fout.write('\n'.join(lines))
	fout.flush()
	if isinstance(in_, str): # pragma: no branch - only used with str in test cases
		# Opened earlier, therefore must close it
		fin.close()
	# to give other threads possibly some time to crunch
	time.sleep(0.1)
	return fout

def _copy_lines_to_journal(in_, fields={},n=None, skip=0, terminal_line=""): # pragma: systemd no cover
	"""Copy lines from one file to systemd journal

	Returns None
	"""
	if isinstance(in_, str): # pragma: no branch - only used with str in test cases
		fin = open(in_, 'r')
	else:
		fin = in_
	# Required for filtering
	fields.update({"SYSLOG_IDENTIFIER": "fail2ban-testcases",
					"PRIORITY": "7",
					})
	# Skip
	for i in xrange(skip):
		fin.readline()
	# Read/Write
	i = 0
	while n is None or i < n:
		l = fin.readline()
		if terminal_line is not None and l == terminal_line:
			break
		journal.send(MESSAGE=l.strip(), **fields)
		i += 1
	if isinstance(in_, str): # pragma: no branch - only used with str in test cases
		# Opened earlier, therefore must close it
		fin.close()

#
#  Actual tests
#

class BasicFilter(unittest.TestCase):

	def setUp(self):
		self.filter = Filter('name')

	def testGetSetUseDNS(self):
		# default is warn
		self.assertEqual(self.filter.getUseDns(), 'warn')
		self.filter.setUseDns(True)
		self.assertEqual(self.filter.getUseDns(), 'yes')
		self.filter.setUseDns(False)
		self.assertEqual(self.filter.getUseDns(), 'no')

	def testGetSetDatePattern(self):
		self.assertEqual(self.filter.getDatePattern(),
			(None, "Default Detectors"))
		self.filter.setDatePattern("^%Y-%m-%d-%H%M%S.%f %z")
		self.assertEqual(self.filter.getDatePattern(),
			("^%Y-%m-%d-%H%M%S.%f %z",
			"^Year-Month-Day-24hourMinuteSecond.Microseconds Zone offset"))

class IgnoreIP(LogCaptureTestCase):

	def setUp(self):
		"""Call before every test case."""
		LogCaptureTestCase.setUp(self)
		self.jail = DummyJail()
		self.filter = FileFilter(self.jail)

	def testIgnoreIPOK(self):
		ipList = "127.0.0.1", "192.168.0.1", "255.255.255.255", "99.99.99.99"
		for ip in ipList:
			self.filter.addIgnoreIP(ip)
			self.assertTrue(self.filter.inIgnoreIPList(ip))

	def testIgnoreIPNOK(self):
		ipList = "", "999.999.999.999", "abcdef", "192.168.0."
		for ip in ipList:
			self.filter.addIgnoreIP(ip)
			self.assertFalse(self.filter.inIgnoreIPList(ip))

	def testIgnoreIPCIDR(self):
		self.filter.addIgnoreIP('192.168.1.0/25')
		self.assertTrue(self.filter.inIgnoreIPList('192.168.1.0'))
		self.assertTrue(self.filter.inIgnoreIPList('192.168.1.1'))
		self.assertTrue(self.filter.inIgnoreIPList('192.168.1.127'))
		self.assertFalse(self.filter.inIgnoreIPList('192.168.1.128'))
		self.assertFalse(self.filter.inIgnoreIPList('192.168.1.255'))
		self.assertFalse(self.filter.inIgnoreIPList('192.168.0.255'))

	def testIgnoreIPMask(self):
		self.filter.addIgnoreIP('192.168.1.0/255.255.255.128')
		self.assertTrue(self.filter.inIgnoreIPList('192.168.1.0'))
		self.assertTrue(self.filter.inIgnoreIPList('192.168.1.1'))
		self.assertTrue(self.filter.inIgnoreIPList('192.168.1.127'))
		self.assertFalse(self.filter.inIgnoreIPList('192.168.1.128'))
		self.assertFalse(self.filter.inIgnoreIPList('192.168.1.255'))
		self.assertFalse(self.filter.inIgnoreIPList('192.168.0.255'))

	def testIgnoreInProcessLine(self):
		setUpMyTime()
		self.filter.addIgnoreIP('192.168.1.0/25')
		self.filter.addFailRegex('<HOST>')
		self.filter.processLineAndAdd('1387203300.222 192.168.1.32')
		self.assertTrue(self._is_logged('Ignore 192.168.1.32'))
		tearDownMyTime()

	def testIgnoreAddBannedIP(self):
		self.filter.addIgnoreIP('192.168.1.0/25')
		self.filter.addBannedIP('192.168.1.32')
		self.assertFalse(self._is_logged('Ignore 192.168.1.32'))
		self.assertTrue(self._is_logged('Requested to manually ban an ignored IP 192.168.1.32. User knows best. Proceeding to ban it.'))

	def testIgnoreCommand(self):
		self.filter.setIgnoreCommand(sys.executable + ' ' + os.path.join(TEST_FILES_DIR, "ignorecommand.py <ip>"))
		self.assertTrue(self.filter.inIgnoreIPList("10.0.0.1"))
		self.assertFalse(self.filter.inIgnoreIPList("10.0.0.0"))


class IgnoreIPDNS(IgnoreIP):

	def testIgnoreIPDNSOK(self):
		self.filter.addIgnoreIP("www.epfl.ch")
		self.assertTrue(self.filter.inIgnoreIPList("128.178.50.12"))

	def testIgnoreIPDNSNOK(self):
		# Test DNS
		self.filter.addIgnoreIP("www.epfl.ch")
		self.assertFalse(self.filter.inIgnoreIPList("127.177.50.10"))
		self.assertFalse(self.filter.inIgnoreIPList("128.178.50.11"))
		self.assertFalse(self.filter.inIgnoreIPList("128.178.50.13"))

class LogFile(LogCaptureTestCase):

	MISSING = 'testcases/missingLogFile'

	def setUp(self):
		LogCaptureTestCase.setUp(self)

	def tearDown(self):
		LogCaptureTestCase.tearDown(self)

	def testMissingLogFiles(self):
		self.filter = FilterPoll(None)
		self.assertRaises(IOError, self.filter.addLogPath, LogFile.MISSING)

class LogFileFilterPoll(unittest.TestCase):

	FILENAME = os.path.join(TEST_FILES_DIR, "testcase01.log")

	def setUp(self):
		"""Call before every test case."""
		self.filter = FilterPoll(DummyJail())
		self.filter.addLogPath(LogFileFilterPoll.FILENAME)

	def tearDown(self):
		"""Call after every test case."""
		pass

	#def testOpen(self):
	#	self.filter.openLogFile(LogFile.FILENAME)

	def testIsModified(self):
		self.assertTrue(self.filter.isModified(LogFileFilterPoll.FILENAME))
		self.assertFalse(self.filter.isModified(LogFileFilterPoll.FILENAME))


class LogFileMonitor(LogCaptureTestCase):
	"""Few more tests for FilterPoll API
	"""
	def setUp(self):
		"""Call before every test case."""
		setUpMyTime()
		LogCaptureTestCase.setUp(self)
		self.filter = self.name = 'NA'
		_, self.name = tempfile.mkstemp('fail2ban', 'monitorfailures')
		self.file = open(self.name, 'a')
		self.filter = FilterPoll(DummyJail())
		self.filter.addLogPath(self.name)
		self.filter.active = True
		self.filter.addFailRegex("(?:(?:Authentication failure|Failed [-/\w+]+) for(?: [iI](?:llegal|nvalid) user)?|[Ii](?:llegal|nvalid) user|ROOT LOGIN REFUSED) .*(?: from|FROM) <HOST>")

	def tearDown(self):
		tearDownMyTime()
		LogCaptureTestCase.tearDown(self)
		_killfile(self.file, self.name)
		pass

	def isModified(self, delay=2.):
		"""Wait up to `delay` sec to assure that it was modified or not
		"""
		time0 = time.time()
		while time.time() < time0 + delay:
			if self.filter.isModified(self.name):
				return True
			time.sleep(0.1)
		return False

	def notModified(self):
		# shorter wait time for not modified status
		return not self.isModified(0.4)

	def testNoLogFile(self):
		os.chmod(self.name, 0)
		self.filter.getFailures(self.name)
		self.assertTrue(self._is_logged('Unable to open %s' % self.name))

	def testRemovingFailRegex(self):
		self.filter.delFailRegex(0)
		self.assertFalse(self._is_logged('Cannot remove regular expression. Index 0 is not valid'))
		self.filter.delFailRegex(0)
		self.assertTrue(self._is_logged('Cannot remove regular expression. Index 0 is not valid'))

	def testRemovingIgnoreRegex(self):
		self.filter.delIgnoreRegex(0)
		self.assertTrue(self._is_logged('Cannot remove regular expression. Index 0 is not valid'))

	def testNewChangeViaIsModified(self):
		# it is a brand new one -- so first we think it is modified
		self.assertTrue(self.isModified())
		# but not any longer
		self.assertTrue(self.notModified())
		self.assertTrue(self.notModified())
		mtimesleep()				# to guarantee freshier mtime
		for i in range(4):			  # few changes
			# unless we write into it
			self.file.write("line%d\n" % i)
			self.file.flush()
			self.assertTrue(self.isModified())
			self.assertTrue(self.notModified())
			mtimesleep()				# to guarantee freshier mtime
		os.rename(self.name, self.name + '.old')
		# we are not signaling as modified whenever
		# it gets away
		self.assertTrue(self.notModified())
		f = open(self.name, 'a')
		self.assertTrue(self.isModified())
		self.assertTrue(self.notModified())
		mtimesleep()
		f.write("line%d\n" % i)
		f.flush()
		self.assertTrue(self.isModified())
		self.assertTrue(self.notModified())
		_killfile(f, self.name)
		_killfile(self.name, self.name + '.old')
		pass

	def testNewChangeViaGetFailures_simple(self):
		# suck in lines from this sample log file
		self.filter.getFailures(self.name)
		self.assertRaises(FailManagerEmpty, self.filter.failManager.toBan)

		# Now let's feed it with entries from the file
		_copy_lines_between_files(GetFailures.FILENAME_01, self.file, n=5)
		self.filter.getFailures(self.name)
		self.assertRaises(FailManagerEmpty, self.filter.failManager.toBan)
		# and it should have not been enough

		_copy_lines_between_files(GetFailures.FILENAME_01, self.file, skip=5)
		self.filter.getFailures(self.name)
		_assert_correct_last_attempt(self, self.filter, GetFailures.FAILURES_01)

	def testNewChangeViaGetFailures_rewrite(self):
		#
		# if we rewrite the file at once
		self.file.close()
		_copy_lines_between_files(GetFailures.FILENAME_01, self.name).close()
		self.filter.getFailures(self.name)
		_assert_correct_last_attempt(self, self.filter, GetFailures.FAILURES_01)

		# What if file gets overridden
		# yoh: skip so we skip those 2 identical lines which our
		# filter "marked" as the known beginning, otherwise it
		# would not detect "rotation"
		self.file = _copy_lines_between_files(GetFailures.FILENAME_01, self.name,
											  skip=3, mode='w')
		self.filter.getFailures(self.name)
		#self.assertRaises(FailManagerEmpty, self.filter.failManager.toBan)
		_assert_correct_last_attempt(self, self.filter, GetFailures.FAILURES_01)

	def testNewChangeViaGetFailures_move(self):
		#
		# if we move file into a new location while it has been open already
		self.file.close()
		self.file = _copy_lines_between_files(GetFailures.FILENAME_01, self.name,
											  n=14, mode='w')
		self.filter.getFailures(self.name)
		self.assertRaises(FailManagerEmpty, self.filter.failManager.toBan)
		self.assertEqual(self.filter.failManager.getFailTotal(), 2)

		# move aside, but leaving the handle still open...
		os.rename(self.name, self.name + '.bak')
		_copy_lines_between_files(GetFailures.FILENAME_01, self.name, skip=14).close()
		self.filter.getFailures(self.name)
		_assert_correct_last_attempt(self, self.filter, GetFailures.FAILURES_01)
		self.assertEqual(self.filter.failManager.getFailTotal(), 3)


def get_monitor_failures_testcase(Filter_):
	"""Generator of TestCase's for different filters/backends
	"""

	# add Filter_'s name so we could easily identify bad cows
	testclass_name = tempfile.mktemp(
		'fail2ban', 'monitorfailures_%s' % (Filter_.__name__,))

	class MonitorFailures(unittest.TestCase):
		count = 0
		def setUp(self):
			"""Call before every test case."""
			setUpMyTime()
			self.filter = self.name = 'NA'
			self.name = '%s-%d' % (testclass_name, self.count)
			MonitorFailures.count += 1 # so we have unique filenames across tests
			self.file = open(self.name, 'a')
			self.jail = DummyJail()
			self.filter = Filter_(self.jail)
			self.filter.addLogPath(self.name)
			self.filter.active = True
			self.filter.addFailRegex("(?:(?:Authentication failure|Failed [-/\w+]+) for(?: [iI](?:llegal|nvalid) user)?|[Ii](?:llegal|nvalid) user|ROOT LOGIN REFUSED) .*(?: from|FROM) <HOST>")
			self.filter.start()
			# If filter is polling it would sleep a bit to guarantee that
			# we have initial time-stamp difference to trigger "actions"
			self._sleep_4_poll()
			#print "D: started filter %s" % self.filter


		def tearDown(self):
			tearDownMyTime()
			#print "D: SLEEPING A BIT"
			#import time; time.sleep(5)
			#print "D: TEARING DOWN"
			self.filter.stop()
			#print "D: WAITING FOR FILTER TO STOP"
			self.filter.join()		  # wait for the thread to terminate
			#print "D: KILLING THE FILE"
			_killfile(self.file, self.name)
			#time.sleep(0.2)			  # Give FS time to ack the removal
			pass

		def isFilled(self, delay=2.):
			"""Wait up to `delay` sec to assure that it was modified or not
			"""
			time0 = time.time()
			while time.time() < time0 + delay:
				if len(self.jail):
					return True
				time.sleep(0.1)
			return False

		def _sleep_4_poll(self):
			# Since FilterPoll relies on time stamps and some
			# actions might be happening too fast in the tests,
			# sleep a bit to guarantee reliable time stamps
			if isinstance(self.filter, FilterPoll):
				mtimesleep()

		def isEmpty(self, delay=0.4):
			# shorter wait time for not modified status
			return not self.isFilled(delay)

		def assert_correct_last_attempt(self, failures, count=None):
			self.assertTrue(self.isFilled(20)) # give Filter a chance to react
			_assert_correct_last_attempt(self, self.jail, failures, count=count)


		def test_grow_file(self):
			# suck in lines from this sample log file
			self.assertRaises(FailManagerEmpty, self.filter.failManager.toBan)

			# Now let's feed it with entries from the file
			_copy_lines_between_files(GetFailures.FILENAME_01, self.file, n=5)
			self.assertRaises(FailManagerEmpty, self.filter.failManager.toBan)
			# and our dummy jail is empty as well
			self.assertFalse(len(self.jail))
			# since it should have not been enough

			_copy_lines_between_files(GetFailures.FILENAME_01, self.file, skip=5)
			self.assertTrue(self.isFilled(6))
			# so we sleep for up to 2 sec for it not to become empty,
			# and meanwhile pass to other thread(s) and filter should
			# have gathered new failures and passed them into the
			# DummyJail
			self.assertEqual(len(self.jail), 1)
			# and there should be no "stuck" ticket in failManager
			self.assertRaises(FailManagerEmpty, self.filter.failManager.toBan)
			self.assert_correct_last_attempt(GetFailures.FAILURES_01)
			self.assertEqual(len(self.jail), 0)

			#return
			# just for fun let's copy all of them again and see if that results
			# in a new ban
			_copy_lines_between_files(GetFailures.FILENAME_01, self.file, n=100)
			self.assert_correct_last_attempt(GetFailures.FAILURES_01)

		def test_rewrite_file(self):
			# if we rewrite the file at once
			self.file.close()
			_copy_lines_between_files(GetFailures.FILENAME_01, self.name).close()
			self.assert_correct_last_attempt(GetFailures.FAILURES_01)

			# What if file gets overridden
			# yoh: skip so we skip those 2 identical lines which our
			# filter "marked" as the known beginning, otherwise it
			# would not detect "rotation"
			self.file = _copy_lines_between_files(GetFailures.FILENAME_01, self.name,
												  skip=3, mode='w')
			self.assert_correct_last_attempt(GetFailures.FAILURES_01)


		def test_move_file(self):
			# if we move file into a new location while it has been open already
			self.file.close()
			self.file = _copy_lines_between_files(GetFailures.FILENAME_01, self.name,
												  n=14, mode='w')
			# Poll might need more time
			self.assertTrue(self.isEmpty(4 + int(isinstance(self.filter, FilterPoll))*2),
							"Queue must be empty but it is not: %s."
							% (', '.join([str(x) for x in self.jail.queue])))
			self.assertRaises(FailManagerEmpty, self.filter.failManager.toBan)
			self.assertEqual(self.filter.failManager.getFailTotal(), 2)

			# move aside, but leaving the handle still open...
			os.rename(self.name, self.name + '.bak')
			_copy_lines_between_files(GetFailures.FILENAME_01, self.name, skip=14).close()
			self.assert_correct_last_attempt(GetFailures.FAILURES_01)
			self.assertEqual(self.filter.failManager.getFailTotal(), 3)

			# now remove the moved file
			_killfile(None, self.name + '.bak')
			_copy_lines_between_files(GetFailures.FILENAME_01, self.name, n=100).close()
			self.assert_correct_last_attempt(GetFailures.FAILURES_01)
			self.assertEqual(self.filter.failManager.getFailTotal(), 6)


		def _test_move_into_file(self, interim_kill=False):
			# if we move a new file into the location of an old (monitored) file
			_copy_lines_between_files(GetFailures.FILENAME_01, self.name,
									  n=100).close()
			# make sure that it is monitored first
			self.assert_correct_last_attempt(GetFailures.FAILURES_01)
			self.assertEqual(self.filter.failManager.getFailTotal(), 3)

			if interim_kill:
				_killfile(None, self.name)
				time.sleep(0.2)				  # let them know

			# now create a new one to override old one
			_copy_lines_between_files(GetFailures.FILENAME_01, self.name + '.new',
									  n=100).close()
			os.rename(self.name + '.new', self.name)
			self.assert_correct_last_attempt(GetFailures.FAILURES_01)
			self.assertEqual(self.filter.failManager.getFailTotal(), 6)

			# and to make sure that it now monitored for changes
			_copy_lines_between_files(GetFailures.FILENAME_01, self.name,
									  n=100).close()
			self.assert_correct_last_attempt(GetFailures.FAILURES_01)
			self.assertEqual(self.filter.failManager.getFailTotal(), 9)


		def test_move_into_file(self):
			self._test_move_into_file(interim_kill=False)

		def test_move_into_file_after_removed(self):
			# exactly as above test + remove file explicitly
			# to test against possible drop-out of the file from monitoring
		    self._test_move_into_file(interim_kill=True)


		def test_new_bogus_file(self):
			# to make sure that watching whole directory does not effect
			_copy_lines_between_files(GetFailures.FILENAME_01, self.name, n=100).close()
			self.assert_correct_last_attempt(GetFailures.FAILURES_01)

			# create a bogus file in the same directory and see if that doesn't affect
			open(self.name + '.bak2', 'w').close()
			_copy_lines_between_files(GetFailures.FILENAME_01, self.name, n=100).close()
			self.assert_correct_last_attempt(GetFailures.FAILURES_01)
			self.assertEqual(self.filter.failManager.getFailTotal(), 6)
			_killfile(None, self.name + '.bak2')


		def test_delLogPath(self):
			# Smoke test for removing of the path from being watched

			# basic full test
			_copy_lines_between_files(GetFailures.FILENAME_01, self.file, n=100)
			self.assert_correct_last_attempt(GetFailures.FAILURES_01)

			# and now remove the LogPath
			self.filter.delLogPath(self.name)

			_copy_lines_between_files(GetFailures.FILENAME_01, self.file, n=100)
			# so we should get no more failures detected
			self.assertTrue(self.isEmpty(2))

			# but then if we add it back again
			self.filter.addLogPath(self.name)
			# Tricky catch here is that it should get them from the
			# tail written before, so let's not copy anything yet
			#_copy_lines_between_files(GetFailures.FILENAME_01, self.name, n=100)
			# we should detect the failures
			self.assert_correct_last_attempt(GetFailures.FAILURES_01, count=6) # was needed if we write twice above

			# now copy and get even more
			_copy_lines_between_files(GetFailures.FILENAME_01, self.file, n=100)
			# yoh: not sure why count here is not 9... TODO
			self.assert_correct_last_attempt(GetFailures.FAILURES_01)#, count=9)

	MonitorFailures.__name__ = "MonitorFailures<%s>(%s)" \
			  % (Filter_.__name__, testclass_name) # 'tempfile')
	return MonitorFailures

def get_monitor_failures_journal_testcase(Filter_): # pragma: systemd no cover
	"""Generator of TestCase's for journal based filters/backends
	"""

	class MonitorJournalFailures(unittest.TestCase):
		def setUp(self):
			"""Call before every test case."""
			self.test_file = os.path.join(TEST_FILES_DIR, "testcase-journal.log")
			self.jail = DummyJail()
			self.filter = Filter_(self.jail)
			# UUID used to ensure that only meeages generated
			# as part of this test are picked up by the filter
			self.test_uuid = str(uuid.uuid4())
			self.name = "monitorjournalfailures-%s" % self.test_uuid
			self.filter.addJournalMatch([
				"SYSLOG_IDENTIFIER=fail2ban-testcases",
				"TEST_FIELD=1",
				"TEST_UUID=%s" % self.test_uuid])
			self.filter.addJournalMatch([
				"SYSLOG_IDENTIFIER=fail2ban-testcases",
				"TEST_FIELD=2",
				"TEST_UUID=%s" % self.test_uuid])
			self.journal_fields = {
				'TEST_FIELD': "1", 'TEST_UUID': self.test_uuid}
			self.filter.active = True
			self.filter.addFailRegex("(?:(?:Authentication failure|Failed [-/\w+]+) for(?: [iI](?:llegal|nvalid) user)?|[Ii](?:llegal|nvalid) user|ROOT LOGIN REFUSED) .*(?: from|FROM) <HOST>")
			self.filter.start()

		def tearDown(self):
			self.filter.stop()
			self.filter.join()		  # wait for the thread to terminate
			pass

		def __str__(self):
			return "MonitorJournalFailures%s(%s)" \
			  % (Filter_, hasattr(self, 'name') and self.name or 'tempfile')

		def isFilled(self, delay=2.):
			"""Wait up to `delay` sec to assure that it was modified or not
			"""
			time0 = time.time()
			while time.time() < time0 + delay:
				if len(self.jail):
					return True
				time.sleep(0.1)
			return False

		def isEmpty(self, delay=0.4):
			# shorter wait time for not modified status
			return not self.isFilled(delay)

		def assert_correct_ban(self, test_ip, test_attempts):
			self.assertTrue(self.isFilled(10)) # give Filter a chance to react
			ticket = self.jail.getFailTicket()

			attempts = ticket.getAttempt()
			ip = ticket.getIP()
			ticket.getMatches()

			self.assertEqual(ip, test_ip)
			self.assertEqual(attempts, test_attempts)

		def test_grow_file(self):
			self.assertRaises(FailManagerEmpty, self.filter.failManager.toBan)

			# Now let's feed it with entries from the file
			_copy_lines_to_journal(
				self.test_file, self.journal_fields, n=2)
			self.assertRaises(FailManagerEmpty, self.filter.failManager.toBan)
			# and our dummy jail is empty as well
			self.assertFalse(len(self.jail))
			# since it should have not been enough

			_copy_lines_to_journal(
				self.test_file, self.journal_fields, skip=2, n=3)
			self.assertTrue(self.isFilled(6))
			# so we sleep for up to 6 sec for it not to become empty,
			# and meanwhile pass to other thread(s) and filter should
			# have gathered new failures and passed them into the
			# DummyJail
			self.assertEqual(len(self.jail), 1)
			# and there should be no "stuck" ticket in failManager
			self.assertRaises(FailManagerEmpty, self.filter.failManager.toBan)
			self.assert_correct_ban("193.168.0.128", 3)
			self.assertEqual(len(self.jail), 0)

			# Lets read some more to check it bans again
			_copy_lines_to_journal(
				self.test_file, self.journal_fields, skip=5, n=4)
			self.assert_correct_ban("193.168.0.128", 3)

		def test_delJournalMatch(self):
			# Smoke test for removing of match

			# basic full test
			_copy_lines_to_journal(
				self.test_file, self.journal_fields, n=5)
			self.assert_correct_ban("193.168.0.128", 3)

			# and now remove the JournalMatch
			self.filter.delJournalMatch([
				"SYSLOG_IDENTIFIER=fail2ban-testcases",
				"TEST_FIELD=1",
				"TEST_UUID=%s" % self.test_uuid])

			_copy_lines_to_journal(
				self.test_file, self.journal_fields, n=5, skip=5)
			# so we should get no more failures detected
			self.assertTrue(self.isEmpty(2))

			# but then if we add it back again
			self.filter.addJournalMatch([
				"SYSLOG_IDENTIFIER=fail2ban-testcases",
				"TEST_FIELD=1",
				"TEST_UUID=%s" % self.test_uuid])
			self.assert_correct_ban("193.168.0.128", 4)
			_copy_lines_to_journal(
				self.test_file, self.journal_fields, n=6, skip=10)
			# we should detect the failures
			self.assertTrue(self.isFilled(6))

	return MonitorJournalFailures

class GetFailures(unittest.TestCase):

	FILENAME_01 = os.path.join(TEST_FILES_DIR, "testcase01.log")
	FILENAME_02 = os.path.join(TEST_FILES_DIR, "testcase02.log")
	FILENAME_03 = os.path.join(TEST_FILES_DIR, "testcase03.log")
	FILENAME_04 = os.path.join(TEST_FILES_DIR, "testcase04.log")
	FILENAME_USEDNS = os.path.join(TEST_FILES_DIR, "testcase-usedns.log")
	FILENAME_MULTILINE = os.path.join(TEST_FILES_DIR, "testcase-multiline.log")

	# so that they could be reused by other tests
	FAILURES_01 = ('193.168.0.128', 3, 1124017199.0,
				  [u'Aug 14 11:59:59 [sshd] error: PAM: Authentication failure for kevin from 193.168.0.128']*3)

	def setUp(self):
		"""Call before every test case."""
		setUpMyTime()
		self.jail = DummyJail()
		self.filter = FileFilter(self.jail)
		self.filter.active = True
		# TODO Test this
		#self.filter.setTimeRegex("\S{3}\s{1,2}\d{1,2} \d{2}:\d{2}:\d{2}")
		#self.filter.setTimePattern("%b %d %H:%M:%S")

	def tearDown(self):
		"""Call after every test case."""
		tearDownMyTime()

	def testTail(self):
		self.filter.addLogPath(GetFailures.FILENAME_01, tail=True)
		self.assertEqual(self.filter.getLogPath()[-1].getPos(), 1653)
		self.filter.getLogPath()[-1].close()
		self.assertEqual(self.filter.getLogPath()[-1].readline(), "")
		self.filter.delLogPath(GetFailures.FILENAME_01)
		self.assertEqual(self.filter.getLogPath(),[])

	def testGetFailures01(self, filename=None, failures=None):
		filename = filename or GetFailures.FILENAME_01
		failures = failures or GetFailures.FAILURES_01

		self.filter.addLogPath(filename)
		self.filter.addFailRegex("(?:(?:Authentication failure|Failed [-/\w+]+) for(?: [iI](?:llegal|nvalid) user)?|[Ii](?:llegal|nvalid) user|ROOT LOGIN REFUSED) .*(?: from|FROM) <HOST>$")
		self.filter.getFailures(filename)
		_assert_correct_last_attempt(self, self.filter,  failures)

	def testCRLFFailures01(self):
		# We first adjust logfile/failures to end with CR+LF
		fname = tempfile.mktemp(prefix='tmp_fail2ban', suffix='crlf')
		# poor man unix2dos:
		fin, fout = open(GetFailures.FILENAME_01), open(fname, 'w')
		for l in fin.readlines():
			fout.write('%s\r\n' % l.rstrip('\n'))
		fin.close()
		fout.close()

		# now see if we should be getting the "same" failures
		self.testGetFailures01(filename=fname)
		_killfile(fout, fname)


	def testGetFailures02(self):
		output = ('141.3.81.106', 4, 1124017139.0,
				  [u'Aug 14 11:%d:59 i60p295 sshd[12365]: Failed publickey for roehl from ::ffff:141.3.81.106 port 51332 ssh2'
				   % m for m in 53, 54, 57, 58])

		self.filter.addLogPath(GetFailures.FILENAME_02)
		self.filter.addFailRegex("Failed .* from <HOST>")
		self.filter.getFailures(GetFailures.FILENAME_02)
		_assert_correct_last_attempt(self, self.filter, output)

	def testGetFailures03(self):
		output = ('203.162.223.135', 7, 1124017144.0)

		self.filter.addLogPath(GetFailures.FILENAME_03)
		self.filter.addFailRegex("error,relay=<HOST>,.*550 User unknown")
		self.filter.getFailures(GetFailures.FILENAME_03)
		_assert_correct_last_attempt(self, self.filter, output)

	def testGetFailures04(self):
		output = [('212.41.96.186', 4, 1124017200.0),
				  ('212.41.96.185', 4, 1124017198.0)]

		self.filter.addLogPath(GetFailures.FILENAME_04)
		self.filter.addFailRegex("Invalid user .* <HOST>")
		self.filter.getFailures(GetFailures.FILENAME_04)

		try:
			for i, out in enumerate(output):
				_assert_correct_last_attempt(self, self.filter, out)
		except FailManagerEmpty:
			pass

	def testGetFailuresUseDNS(self):
		# We should still catch failures with usedns = no ;-)
		output_yes = ('93.184.216.119', 2, 1124017139.0,
					  [u'Aug 14 11:54:59 i60p295 sshd[12365]: Failed publickey for roehl from example.com port 51332 ssh2',
					   u'Aug 14 11:58:59 i60p295 sshd[12365]: Failed publickey for roehl from ::ffff:93.184.216.119 port 51332 ssh2'])

		output_no = ('93.184.216.119', 1, 1124017139.0,
					  [u'Aug 14 11:58:59 i60p295 sshd[12365]: Failed publickey for roehl from ::ffff:93.184.216.119 port 51332 ssh2'])

		# Actually no exception would be raised -- it will be just set to 'no'
		#self.assertRaises(ValueError,
		#				  FileFilter, None, useDns='wrong_value_for_useDns')

		for useDns, output in (('yes',  output_yes),
							   ('no',   output_no),
							   ('warn', output_yes)):
			jail = DummyJail()
			filter_ = FileFilter(jail, useDns=useDns)
			filter_.active = True
			filter_.failManager.setMaxRetry(1)	# we might have just few failures

			filter_.addLogPath(GetFailures.FILENAME_USEDNS)
			filter_.addFailRegex("Failed .* from <HOST>")
			filter_.getFailures(GetFailures.FILENAME_USEDNS)
			_assert_correct_last_attempt(self, filter_, output)



	def testGetFailuresMultiRegex(self):
		output = ('141.3.81.106', 8, 1124017141.0)

		self.filter.addLogPath(GetFailures.FILENAME_02)
		self.filter.addFailRegex("Failed .* from <HOST>")
		self.filter.addFailRegex("Accepted .* from <HOST>")
		self.filter.getFailures(GetFailures.FILENAME_02)
		_assert_correct_last_attempt(self, self.filter, output)

	def testGetFailuresIgnoreRegex(self):
		self.filter.addLogPath(GetFailures.FILENAME_02)
		self.filter.addFailRegex("Failed .* from <HOST>")
		self.filter.addFailRegex("Accepted .* from <HOST>")
		self.filter.addIgnoreRegex("for roehl")

		self.filter.getFailures(GetFailures.FILENAME_02)

		self.assertRaises(FailManagerEmpty, self.filter.failManager.toBan)

	def testGetFailuresMultiLine(self):
		output = [("192.0.43.10", 2, 1124017199.0),
			("192.0.43.11", 1, 1124017198.0)]
		self.filter.addLogPath(GetFailures.FILENAME_MULTILINE)
		self.filter.addFailRegex("^.*rsyncd\[(?P<pid>\d+)\]: connect from .+ \(<HOST>\)$<SKIPLINES>^.+ rsyncd\[(?P=pid)\]: rsync error: .*$")
		self.filter.setMaxLines(100)
		self.filter.setMaxRetry(1)

		self.filter.getFailures(GetFailures.FILENAME_MULTILINE)

		foundList = []
		while True:
			try:
				foundList.append(
					_ticket_tuple(self.filter.failManager.toBan())[0:3])
			except FailManagerEmpty:
				break
		self.assertEqual(sorted(foundList), sorted(output))

	def testGetFailuresMultiLineIgnoreRegex(self):
		output = [("192.0.43.10", 2, 1124017199.0)]
		self.filter.addLogPath(GetFailures.FILENAME_MULTILINE)
		self.filter.addFailRegex("^.*rsyncd\[(?P<pid>\d+)\]: connect from .+ \(<HOST>\)$<SKIPLINES>^.+ rsyncd\[(?P=pid)\]: rsync error: .*$")
		self.filter.addIgnoreRegex("rsync error: Received SIGINT")
		self.filter.setMaxLines(100)
		self.filter.setMaxRetry(1)

		self.filter.getFailures(GetFailures.FILENAME_MULTILINE)

		_assert_correct_last_attempt(self, self.filter, output.pop())

		self.assertRaises(FailManagerEmpty, self.filter.failManager.toBan)

	def testGetFailuresMultiLineMultiRegex(self):
		output = [("192.0.43.10", 2, 1124017199.0),
			("192.0.43.11", 1, 1124017198.0),
			("192.0.43.15", 1, 1124017198.0)]
		self.filter.addLogPath(GetFailures.FILENAME_MULTILINE)
		self.filter.addFailRegex("^.*rsyncd\[(?P<pid>\d+)\]: connect from .+ \(<HOST>\)$<SKIPLINES>^.+ rsyncd\[(?P=pid)\]: rsync error: .*$")
		self.filter.addFailRegex("^.* sendmail\[.*, msgid=<(?P<msgid>[^>]+).*relay=\[<HOST>\].*$<SKIPLINES>^.+ spamd: result: Y \d+ .*,mid=<(?P=msgid)>(,bayes=[.\d]+)?(,autolearn=\S+)?\s*$")
		self.filter.setMaxLines(100)
		self.filter.setMaxRetry(1)

		self.filter.getFailures(GetFailures.FILENAME_MULTILINE)

		foundList = []
		while True:
			try:
				foundList.append(
					_ticket_tuple(self.filter.failManager.toBan())[0:3])
			except FailManagerEmpty:
				break
		self.assertEqual(sorted(foundList), sorted(output))

class DNSUtilsTests(unittest.TestCase):

	def testUseDns(self):
		res = DNSUtils.textToIp('www.example.com', 'no')
		self.assertEqual(res, [])
		res = DNSUtils.textToIp('www.example.com', 'warn')
		self.assertEqual(res, ['93.184.216.119'])
		res = DNSUtils.textToIp('www.example.com', 'yes')
		self.assertEqual(res, ['93.184.216.119'])

	def testTextToIp(self):
		# Test hostnames
		hostnames = [
			'www.example.com',
			'doh1.2.3.4.buga.xxxxx.yyy.invalid',
			'1.2.3.4.buga.xxxxx.yyy.invalid',
			]
		for s in hostnames:
			res = DNSUtils.textToIp(s, 'yes')
			if s == 'www.example.com':
				self.assertEqual(res, ['93.184.216.119'])
			else:
				self.assertEqual(res, [])

class JailTests(unittest.TestCase):

	def testSetBackend_gh83(self):
		# smoke test
		# Must not fail to initiate
		Jail('test', backend='polling')


########NEW FILE########
__FILENAME__ = misctestcase
# emacs: -*- mode: python; py-indent-offset: 4; indent-tabs-mode: t -*-
# vi: set ft=python sts=4 ts=4 sw=4 noet :

# This file is part of Fail2Ban.
#
# Fail2Ban is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# Fail2Ban is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with Fail2Ban; if not, write to the Free Software
# Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA  02110-1301, USA.

__author__ = "Yaroslav Halchenko"
__copyright__ = "Copyright (c) 2013 Yaroslav Halchenko"
__license__ = "GPL"

import logging
import os
import sys
import unittest
import tempfile
import shutil
import fnmatch
import datetime
from glob import glob
from StringIO import StringIO

from ..helpers import formatExceptionInfo, mbasename, TraceBack, FormatterWithTraceBack
from ..server.datetemplate import DatePatternRegex


class HelpersTest(unittest.TestCase):

	def testFormatExceptionInfoBasic(self):
		try:
			raise ValueError("Very bad exception")
		except:
			name, args = formatExceptionInfo()
			self.assertEqual(name, "ValueError")
			self.assertEqual(args, "Very bad exception")

	def testFormatExceptionConvertArgs(self):
		try:
			raise ValueError("Very bad", None)
		except:
			name, args = formatExceptionInfo()
			self.assertEqual(name, "ValueError")
			# might be fragile due to ' vs "
			self.assertEqual(args, "('Very bad', None)")

# based on
# http://stackoverflow.com/questions/2186525/use-a-glob-to-find-files-recursively-in-python
def recursive_glob(treeroot, pattern):
	results = []
	for base, dirs, files in os.walk(treeroot):
		goodfiles = fnmatch.filter(dirs + files, pattern)
		results.extend(os.path.join(base, f) for f in goodfiles)
	return results

class SetupTest(unittest.TestCase):

	def setUp(self):
		setup = os.path.join(os.path.dirname(__file__), '..', 'setup.py')
		self.setup = os.path.exists(setup) and setup or None
		if not self.setup and sys.version_info >= (2,7): # running not out of the source
			raise unittest.SkipTest(
				"Seems to be running not out of source distribution"
				" -- cannot locate setup.py")

	def testSetupInstallRoot(self):
		if not self.setup: return			  # if verbose skip didn't work out
		tmp = tempfile.mkdtemp()
		os.system("%s %s install --root=%s >/dev/null"
				  % (sys.executable, self.setup, tmp))

		def addpath(l):
			return [os.path.join(tmp, x) for x in l]

		def strippath(l):
			return [x[len(tmp)+1:] for x in l]

		got = strippath(sorted(glob('%s/*' % tmp)))
		need = ['etc', 'usr', 'var']

		# if anything is missing
		if set(need).difference(got):
			#  below code was actually to print out not missing but
			#  rather files in 'excess'.  Left in place in case we
			#  decide to revert to such more strict test
			files = {}
			for missing in set(got).difference(need):
				missing_full = os.path.join(tmp, missing)
				files[missing] = os.path.exists(missing_full) \
					and strippath(recursive_glob(missing_full, '*')) or None

			self.assertEqual(
				got, need,
				msg="Got: %s Needed: %s under %s. Files under new paths: %s"
				% (got, need, tmp, files))

		# Assure presence of some files we expect to see in the installation
		for f in ('etc/fail2ban/fail2ban.conf',
				  'etc/fail2ban/jail.conf'):
			self.assertTrue(os.path.exists(os.path.join(tmp, f)),
							msg="Can't find %s" % f)

		# clean up
		shutil.rmtree(tmp)

class TestsUtilsTest(unittest.TestCase):

	def testmbasename(self):
		self.assertEqual(mbasename("sample.py"), 'sample')
		self.assertEqual(mbasename("/long/path/sample.py"), 'sample')
		# this one would include only the directory for the __init__ and base files
		self.assertEqual(mbasename("/long/path/__init__.py"), 'path.__init__')
		self.assertEqual(mbasename("/long/path/base.py"), 'path.base')
		self.assertEqual(mbasename("/long/path/base"), 'path.base')

	def testTraceBack(self):
		# pretty much just a smoke test since tests runners swallow all the detail

		for compress in True, False:
			tb = TraceBack(compress=compress)

			def func_raise():
				raise ValueError()

			def deep_function(i):
				if i: deep_function(i-1)
				else: func_raise()

			try:
				print deep_function(3)
			except ValueError:
				s = tb()

			# if we run it through 'coverage' (e.g. on travis) then we
			# would get a traceback
			if not ('fail2ban-testcases' in s):
				# we must be calling it from setup or nosetests but using at least
				# nose's core etc
				self.assertTrue('>' in s, msg="no '>' in %r" % s)
			else:
				self.assertFalse('>' in s, msg="'>' present in %r" % s)  # There is only "fail2ban-testcases" in this case, no true traceback
			self.assertTrue(':' in s, msg="no ':' in %r" % s)


	def testFormatterWithTraceBack(self):
		strout = StringIO()
		Formatter = FormatterWithTraceBack

		# and both types of traceback at once
		fmt = ' %(tb)s | %(tbc)s : %(message)s'
		logSys = logging.getLogger("fail2ban_tests")
		out = logging.StreamHandler(strout)
		out.setFormatter(Formatter(fmt))
		logSys.addHandler(out)
		logSys.error("XXX")

		s = strout.getvalue()
		self.assertTrue(s.rstrip().endswith(': XXX'))
		pindex = s.index('|')

		# in this case compressed and not should be the same (?)
		self.assertTrue(pindex > 10)	  # we should have some traceback
		self.assertEqual(s[:pindex], s[pindex+1:pindex*2 + 1])

iso8601 = DatePatternRegex("%Y-%m-%d[T ]%H:%M:%S(?:\.%f)?%z")

class CustomDateFormatsTest(unittest.TestCase):

	def testIso8601(self):
		date = datetime.datetime.utcfromtimestamp(
			iso8601.getDate("2007-01-25T12:00:00Z")[0])
		self.assertEqual(
			date,
			datetime.datetime(2007, 1, 25, 12, 0))
		self.assertRaises(TypeError, iso8601.getDate, None)
		self.assertRaises(TypeError, iso8601.getDate, date)

		self.assertEqual(iso8601.getDate(""), None)
		self.assertEqual(iso8601.getDate("Z"), None)

		self.assertEqual(iso8601.getDate("2007-01-01T120:00:00Z"), None)
		self.assertEqual(iso8601.getDate("2007-13-01T12:00:00Z"), None)
		date = datetime.datetime.utcfromtimestamp(
			iso8601.getDate("2007-01-25T12:00:00+0400")[0])
		self.assertEqual(
			date,
			datetime.datetime(2007, 1, 25, 8, 0))
		date = datetime.datetime.utcfromtimestamp(
			iso8601.getDate("2007-01-25T12:00:00+04:00")[0])
		self.assertEqual(
			date,
			datetime.datetime(2007, 1, 25, 8, 0))
		date = datetime.datetime.utcfromtimestamp(
			iso8601.getDate("2007-01-25T12:00:00-0400")[0])
		self.assertEqual(
			date,
			datetime.datetime(2007, 1, 25, 16, 0))
		date = datetime.datetime.utcfromtimestamp(
			iso8601.getDate("2007-01-25T12:00:00-04")[0])
		self.assertEqual(
			date,
			datetime.datetime(2007, 1, 25, 16, 0))

########NEW FILE########
__FILENAME__ = samplestestcase
# emacs: -*- mode: python; py-indent-offset: 4; indent-tabs-mode: t -*-
# vi: set ft=python sts=4 ts=4 sw=4 noet :

# This file is part of Fail2Ban.
#
# Fail2Ban is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# Fail2Ban is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with Fail2Ban; if not, write to the Free Software
# Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA  02110-1301, USA.

# Fail2Ban developers

__copyright__ = "Copyright (c) 2013 Steven Hiscocks"
__license__ = "GPL"

import unittest, sys, os, fileinput, re, time, datetime, inspect

if sys.version_info >= (2, 6):
	import json
else:
	import simplejson as json
	next = lambda x: x.next()

from ..server.filter import Filter
from ..client.filterreader import FilterReader
from .utils import setUpMyTime, tearDownMyTime

TEST_FILES_DIR = os.path.join(os.path.dirname(__file__), "files")
if os.path.exists('config/fail2ban.conf'):
	CONFIG_DIR = "config"
else:
	CONFIG_DIR='/etc/fail2ban'

class FilterSamplesRegex(unittest.TestCase):

	def setUp(self):
		"""Call before every test case."""
		self.filter = Filter(None)
		self.filter.active = True

		setUpMyTime()

	def tearDown(self):
		"""Call after every test case."""
		tearDownMyTime()

	def testFiltersPresent(self):
		"""Check to ensure some tests exist"""
		self.assertTrue(
			len([test for test in inspect.getmembers(self)
				if test[0].startswith('testSampleRegexs')])
			>= 10,
			"Expected more FilterSampleRegexs tests")

def testSampleRegexsFactory(name):
	def testFilter(self):

		# Check filter exists
		filterConf = FilterReader(name, "jail", {}, basedir=CONFIG_DIR)
		self.assertEqual(filterConf.getFile(), name)
		self.assertEqual(filterConf.getJailName(), "jail")
		filterConf.read()
		filterConf.getOptions({})

		for opt in filterConf.convert():
			if opt[2] == "addfailregex":
				self.filter.addFailRegex(opt[3])
			elif opt[2] == "maxlines":
				self.filter.setMaxLines(opt[3])
			elif opt[2] == "addignoreregex":
				self.filter.addIgnoreRegex(opt[3])
			elif opt[2] == "datepattern":
				self.filter.setDatePattern(opt[3])

		self.assertTrue(
			os.path.isfile(os.path.join(TEST_FILES_DIR, "logs", name)),
			"No sample log file available for '%s' filter" % name)

		logFile = fileinput.FileInput(
			os.path.join(TEST_FILES_DIR, "logs", name))

		regexsUsed = set()
		for line in logFile:
			jsonREMatch = re.match("^# ?failJSON:(.+)$", line)
			if jsonREMatch:
				try:
					faildata = json.loads(jsonREMatch.group(1))
				except ValueError, e:
					raise ValueError("%s: %s:%i" %
						(e, logFile.filename(), logFile.filelineno()))
				line = next(logFile)
			elif line.startswith("#") or not line.strip():
				continue
			else:
				faildata = {}

			ret = self.filter.processLine(
				line, returnRawHost=True, checkAllRegex=True)[1]
			if not ret:
				# Check line is flagged as none match
				self.assertFalse(faildata.get('match', True),
					 "Line not matched when should have: %s:%i %r" %
					(logFile.filename(), logFile.filelineno(), line))
			elif ret:
				# Check line is flagged to match
				self.assertTrue(faildata.get('match', False),
					"Line matched when shouldn't have: %s:%i %r" %
					(logFile.filename(), logFile.filelineno(), line))
				self.assertEqual(len(ret), 1, "Multiple regexs matched %r - %s:%i" %
								 (map(lambda x: x[0], ret),logFile.filename(), logFile.filelineno()))

				# Verify timestamp and host as expected
				failregex, host, fail2banTime, lines = ret[0]
				self.assertEqual(host, faildata.get("host", None))

				t = faildata.get("time", None)
				try:
					jsonTimeLocal =	datetime.datetime.strptime(t, "%Y-%m-%dT%H:%M:%S")
				except ValueError:
					jsonTimeLocal =	datetime.datetime.strptime(t, "%Y-%m-%dT%H:%M:%S.%f")


				jsonTime = time.mktime(jsonTimeLocal.utctimetuple())
				
				jsonTime += jsonTimeLocal.microsecond / 1000000

				self.assertEqual(fail2banTime, jsonTime,
					"UTC Time  mismatch fail2ban %s (%s) != failJson %s (%s)  (diff %.3f seconds) on: %s:%i %r:" % 
					(fail2banTime, time.strftime("%Y-%m-%dT%H:%M:%S", time.gmtime(fail2banTime)),
					jsonTime, time.strftime("%Y-%m-%dT%H:%M:%S", time.gmtime(jsonTime)),
					fail2banTime - jsonTime, logFile.filename(), logFile.filelineno(), line ) )

				regexsUsed.add(failregex)

		for failRegexIndex, failRegex in enumerate(self.filter.getFailRegex()):
			self.assertTrue(
				failRegexIndex in regexsUsed,
				"Regex for filter '%s' has no samples: %i: %r" %
					(name, failRegexIndex, failRegex))

	return testFilter

for filter_ in filter(lambda x: not x.endswith('common.conf'), os.listdir(os.path.join(CONFIG_DIR, "filter.d"))):
	filterName = filter_.rpartition(".")[0]
	if not filterName.startswith('.'):
		setattr(
			FilterSamplesRegex,
			"testSampleRegexs%s" % filterName.upper(),
			testSampleRegexsFactory(filterName))

########NEW FILE########
__FILENAME__ = servertestcase
# emacs: -*- mode: python; py-indent-offset: 4; indent-tabs-mode: t -*-
# vi: set ft=python sts=4 ts=4 sw=4 noet :

# This file is part of Fail2Ban.
#
# Fail2Ban is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# Fail2Ban is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with Fail2Ban; if not, write to the Free Software
# Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA  02110-1301, USA.

# Author: Cyril Jaquier
# 

__author__ = "Cyril Jaquier"
__copyright__ = "Copyright (c) 2004 Cyril Jaquier"
__license__ = "GPL"

import unittest
import time
import tempfile
import os
import locale
import sys
import logging

from ..server.failregex import Regex, FailRegex, RegexException
from ..server.server import Server
from ..server.jail import Jail

try:
	from ..server import filtersystemd
except ImportError: # pragma: no cover
	filtersystemd = None

TEST_FILES_DIR = os.path.join(os.path.dirname(__file__), "files")

class TestServer(Server):
	def setLogLevel(self, *args, **kwargs):
		pass
	def setLogTarget(self, *args, **kwargs):
		pass

class TransmitterBase(unittest.TestCase):
	
	def setUp(self):
		"""Call before every test case."""
		self.transm = self.server._Server__transm
		sock_fd, sock_name = tempfile.mkstemp('fail2ban.sock', 'transmitter')
		os.close(sock_fd)
		pidfile_fd, pidfile_name = tempfile.mkstemp(
			'fail2ban.pid', 'transmitter')
		os.close(pidfile_fd)
		self.server.start(sock_name, pidfile_name, force=False)
		self.jailName = "TestJail1"
		self.server.addJail(self.jailName, "auto")

	def tearDown(self):
		"""Call after every test case."""
		self.server.quit()

	def setGetTest(self, cmd, inValue, outValue=None, jail=None):
		setCmd = ["set", cmd, inValue]
		getCmd = ["get", cmd]
		if jail is not None:
			setCmd.insert(1, jail)
			getCmd.insert(1, jail)
		if outValue is None:
			outValue = inValue

		self.assertEqual(self.transm.proceed(setCmd), (0, outValue))
		self.assertEqual(self.transm.proceed(getCmd), (0, outValue))

	def setGetTestNOK(self, cmd, inValue, jail=None):
		setCmd = ["set", cmd, inValue]
		getCmd = ["get", cmd]
		if jail is not None:
			setCmd.insert(1, jail)
			getCmd.insert(1, jail)

		# Get initial value before trying invalid value
		initValue = self.transm.proceed(getCmd)[1]
		self.assertEqual(self.transm.proceed(setCmd)[0], 1)
		# Check after failed set that value is same as previous
		self.assertEqual(self.transm.proceed(getCmd), (0, initValue))

	def jailAddDelTest(self, cmd, values, jail):
		cmdAdd = "add" + cmd
		cmdDel = "del" + cmd

		self.assertEqual(
			self.transm.proceed(["get", jail, cmd]), (0, []))
		for n, value in enumerate(values):
			self.assertEqual(
				self.transm.proceed(["set", jail, cmdAdd, value]),
				(0, values[:n+1]))
			self.assertEqual(
				self.transm.proceed(["get", jail, cmd]),
				(0, values[:n+1]))
		for n, value in enumerate(values):
			self.assertEqual(
				self.transm.proceed(["set", jail, cmdDel, value]),
				(0, values[n+1:]))
			self.assertEqual(
				self.transm.proceed(["get", jail, cmd]),
				(0, values[n+1:]))

	def jailAddDelRegexTest(self, cmd, inValues, outValues, jail):
		cmdAdd = "add" + cmd
		cmdDel = "del" + cmd

		self.assertEqual(
			self.transm.proceed(["get", jail, cmd]), (0, []))
		for n, value in enumerate(inValues):
			self.assertEqual(
				self.transm.proceed(["set", jail, cmdAdd, value]),
				(0, outValues[:n+1]))
			self.assertEqual(
				self.transm.proceed(["get", jail, cmd]),
				(0, outValues[:n+1]))
		for n, value in enumerate(inValues):
			self.assertEqual(
				self.transm.proceed(["set", jail, cmdDel, 0]), # First item
				(0, outValues[n+1:]))
			self.assertEqual(
				self.transm.proceed(["get", jail, cmd]),
				(0, outValues[n+1:]))

class Transmitter(TransmitterBase):

	def setUp(self):
		self.server = TestServer()
		super(Transmitter, self).setUp()

	def testStopServer(self):
		self.assertEqual(self.transm.proceed(["stop"]), (0, None))

	def testPing(self):
		self.assertEqual(self.transm.proceed(["ping"]), (0, "pong"))

	def testSleep(self):
		t0 = time.time()
		self.assertEqual(self.transm.proceed(["sleep", "1"]), (0, None))
		t1 = time.time()
		# Approx 1 second delay
		self.assertAlmostEqual(t1 - t0, 1, places=1)

	def testDatabase(self):
		tmp, tmpFilename = tempfile.mkstemp(".db", "fail2ban_")
		# Jails present, can't change database
		self.setGetTestNOK("dbfile", tmpFilename)
		self.server.delJail(self.jailName)
		self.setGetTest("dbfile", tmpFilename)
		self.setGetTest("dbpurgeage", "600", 600)
		self.setGetTestNOK("dbpurgeage", "LIZARD")

		# Disable database
		self.assertEqual(self.transm.proceed(
			["set", "dbfile", "None"]),
			(0, None))
		self.assertEqual(self.transm.proceed(
			["get", "dbfile"]),
			(0, None))
		self.assertEqual(self.transm.proceed(
			["set", "dbpurgeage", "500"]),
			(0, None))
		self.assertEqual(self.transm.proceed(
			["get", "dbpurgeage"]),
			(0, None))
		os.close(tmp)
		os.unlink(tmpFilename)

	def testAddJail(self):
		jail2 = "TestJail2"
		jail3 = "TestJail3"
		jail4 = "TestJail4"
		self.assertEqual(
			self.transm.proceed(["add", jail2, "polling"]), (0, jail2))
		self.assertEqual(self.transm.proceed(["add", jail3]), (0, jail3))
		self.assertEqual(
			self.transm.proceed(["add", jail4, "invalid backend"])[0], 1)
		self.assertEqual(
			self.transm.proceed(["add", jail4, "auto"]), (0, jail4))
		# Duplicate Jail
		self.assertEqual(
			self.transm.proceed(["add", self.jailName, "polling"])[0], 1)
		# All name is reserved
		self.assertEqual(
			self.transm.proceed(["add", "all", "polling"])[0], 1)

	def testStartStopJail(self):
		self.assertEqual(
			self.transm.proceed(["start", self.jailName]), (0, None))
		time.sleep(1)
		self.assertEqual(
			self.transm.proceed(["stop", self.jailName]), (0, None))
		self.assertTrue(self.jailName not in self.server._Server__jails)

	def testStartStopAllJail(self):
		self.server.addJail("TestJail2", "auto")
		self.assertEqual(
			self.transm.proceed(["start", self.jailName]), (0, None))
		self.assertEqual(
			self.transm.proceed(["start", "TestJail2"]), (0, None))
		# yoh: workaround for gh-146.  I still think that there is some
		#      race condition and missing locking somewhere, but for now
		#      giving it a small delay reliably helps to proceed with tests
		time.sleep(0.1)
		self.assertEqual(self.transm.proceed(["stop", "all"]), (0, None))
		time.sleep(1)
		self.assertTrue(self.jailName not in self.server._Server__jails)
		self.assertTrue("TestJail2" not in self.server._Server__jails)

	def testJailIdle(self):
		self.assertEqual(
			self.transm.proceed(["set", self.jailName, "idle", "on"]),
			(0, True))
		self.assertEqual(
			self.transm.proceed(["set", self.jailName, "idle", "off"]),
			(0, False))
		self.assertEqual(
			self.transm.proceed(["set", self.jailName, "idle", "CAT"])[0],
			1)

	def testJailFindTime(self):
		self.setGetTest("findtime", "120", 120, jail=self.jailName)
		self.setGetTest("findtime", "60", 60, jail=self.jailName)
		self.setGetTest("findtime", "-60", -60, jail=self.jailName)
		self.setGetTestNOK("findtime", "Dog", jail=self.jailName)

	def testJailBanTime(self):
		self.setGetTest("bantime", "600", 600, jail=self.jailName)
		self.setGetTest("bantime", "50", 50, jail=self.jailName)
		self.setGetTest("bantime", "-50", -50, jail=self.jailName)
		self.setGetTestNOK("bantime", "Cat", jail=self.jailName)

	def testDatePattern(self):
		self.setGetTest("datepattern", "%%%Y%m%d%H%M%S",
			("%%%Y%m%d%H%M%S", "%YearMonthDay24hourMinuteSecond"),
			jail=self.jailName)
		self.setGetTest(
			"datepattern", "Epoch", (None, "Epoch"), jail=self.jailName)
		self.setGetTest(
			"datepattern", "TAI64N", (None, "TAI64N"), jail=self.jailName)
		self.setGetTestNOK("datepattern", "%Cat%a%%%g", jail=self.jailName)

	def testJailUseDNS(self):
		self.setGetTest("usedns", "yes", jail=self.jailName)
		self.setGetTest("usedns", "warn", jail=self.jailName)
		self.setGetTest("usedns", "no", jail=self.jailName)

		# Safe default should be "no"
		value = "Fish"
		self.assertEqual(
			self.transm.proceed(["set", self.jailName, "usedns", value]),
			(0, "no"))

	def testJailBanIP(self):
		self.server.startJail(self.jailName) # Jail must be started

		self.assertEqual(
			self.transm.proceed(["set", self.jailName, "banip", "127.0.0.1"]),
			(0, "127.0.0.1"))
		time.sleep(1) # Give chance to ban
		self.assertEqual(
			self.transm.proceed(["set", self.jailName, "banip", "Badger"]),
			(0, "Badger")) #NOTE: Is IP address validated? Is DNS Lookup done?
		time.sleep(1) # Give chance to ban
		# Unban IP
		self.assertEqual(
			self.transm.proceed(
				["set", self.jailName, "unbanip", "127.0.0.1"]),
			(0, "127.0.0.1"))
		# Unban IP which isn't banned
		self.assertEqual(
			self.transm.proceed(
				["set", self.jailName, "unbanip", "192.168.1.1"])[0],1)

	def testJailMaxRetry(self):
		self.setGetTest("maxretry", "5", 5, jail=self.jailName)
		self.setGetTest("maxretry", "2", 2, jail=self.jailName)
		self.setGetTest("maxretry", "-2", -2, jail=self.jailName)
		self.setGetTestNOK("maxretry", "Duck", jail=self.jailName)

	def testJailMaxLines(self):
		self.setGetTest("maxlines", "5", 5, jail=self.jailName)
		self.setGetTest("maxlines", "2", 2, jail=self.jailName)
		self.setGetTestNOK("maxlines", "-2", jail=self.jailName)
		self.setGetTestNOK("maxlines", "Duck", jail=self.jailName)

	def testJailLogEncoding(self):
		self.setGetTest("logencoding", "UTF-8", jail=self.jailName)
		self.setGetTest("logencoding", "ascii", jail=self.jailName)
		self.setGetTest("logencoding", "auto", locale.getpreferredencoding(),
			jail=self.jailName)
		self.setGetTestNOK("logencoding", "Monkey", jail=self.jailName)

	def testJailLogPath(self):
		self.jailAddDelTest(
			"logpath",
			[
				os.path.join(TEST_FILES_DIR, "testcase01.log"),
				os.path.join(TEST_FILES_DIR, "testcase02.log"),
				os.path.join(TEST_FILES_DIR, "testcase03.log"),
			],
			self.jailName
		)
		# Try duplicates
		value = os.path.join(TEST_FILES_DIR, "testcase04.log")
		self.assertEqual(
			self.transm.proceed(["set", self.jailName, "addlogpath", value]),
			(0, [value]))
		# Will silently ignore duplicate
		self.assertEqual(
			self.transm.proceed(["set", self.jailName, "addlogpath", value]),
			(0, [value]))
		self.assertEqual(
			self.transm.proceed(["get", self.jailName, "logpath"]),
			(0, [value]))
		self.assertEqual(
			self.transm.proceed(["set", self.jailName, "dellogpath", value]),
			(0, []))
		self.assertEqual(
			self.transm.proceed(
				["set", self.jailName, "addlogpath", value, "tail"]),
			(0, [value]))
		self.assertEqual(
			self.transm.proceed(
				["set", self.jailName, "addlogpath", value, "head"]),
			(0, [value]))
		self.assertEqual(
			self.transm.proceed(
				["set", self.jailName, "addlogpath", value, "badger"])[0],
			1)
		self.assertEqual(
			self.transm.proceed(
				["set", self.jailName, "addlogpath", value, value, value])[0],
			1)

	def testJailLogPathInvalidFile(self):
		# Invalid file
		value = "this_file_shouldn't_exist"
		result = self.transm.proceed(
			["set", self.jailName, "addlogpath", value])
		self.assertTrue(isinstance(result[1], IOError))

	def testJailLogPathBrokenSymlink(self):
		# Broken symlink
		name = tempfile.mktemp(prefix='tmp_fail2ban_broken_symlink')
		sname = name + '.slink'
		os.symlink(name, sname)
		result = self.transm.proceed(
			["set", self.jailName, "addlogpath", sname])
		self.assertTrue(isinstance(result[1], IOError))
		os.unlink(sname)

	def testJailIgnoreIP(self):
		self.jailAddDelTest(
			"ignoreip",
			[
				"127.0.0.1",
				"192.168.1.1",
				"8.8.8.8",
			],
			self.jailName
		)

		# Try duplicates
		value = "127.0.0.1"
		self.assertEqual(
			self.transm.proceed(["set", self.jailName, "addignoreip", value]),
			(0, [value]))
		# Will allow duplicate
		#NOTE: Should duplicates be allowed, or silent ignore like logpath?
		self.assertEqual(
			self.transm.proceed(["set", self.jailName, "addignoreip", value]),
			(0, [value, value]))
		self.assertEqual(
			self.transm.proceed(["get", self.jailName, "ignoreip"]),
			(0, [value, value]))
		self.assertEqual(
			self.transm.proceed(["set", self.jailName, "delignoreip", value]),
			(0, [value]))

	def testJailIgnoreCommand(self):
		self.setGetTest("ignorecommand", "bin ", jail=self.jailName)

	def testJailRegex(self):
		self.jailAddDelRegexTest("failregex",
			[
				"user john at <HOST>",
				"Admin user login from <HOST>",
				"failed attempt from <HOST> again",
			],
			[
				"user john at (?:::f{4,6}:)?(?P<host>[\w\-.^_]*\\w)",
				"Admin user login from (?:::f{4,6}:)?(?P<host>[\w\-.^_]*\\w)",
				"failed attempt from (?:::f{4,6}:)?(?P<host>[\w\-.^_]*\\w) again",
			],
			self.jailName
		)

		self.assertEqual(
			self.transm.proceed(
				["set", self.jailName, "addfailregex", "No host regex"])[0],
			1)
		self.assertEqual(
			self.transm.proceed(
				["set", self.jailName, "addfailregex", 654])[0],
			1)

	def testJailIgnoreRegex(self):
		self.jailAddDelRegexTest("ignoreregex",
			[
				"user john",
				"Admin user login from <HOST>",
				"Dont match me!",
			],
			[
				"user john",
				"Admin user login from (?:::f{4,6}:)?(?P<host>[\w\-.^_]*\\w)",
				"Dont match me!",
			],
			self.jailName
		)

		self.assertEqual(
			self.transm.proceed(
				["set", self.jailName, "addignoreregex", "Invalid [regex"])[0],
			1)
		self.assertEqual(
			self.transm.proceed(
				["set", self.jailName, "addignoreregex", 50])[0],
			1)

	def testStatus(self):
		jails = [self.jailName]
		self.assertEqual(self.transm.proceed(["status"]),
			(0, [('Number of jail', len(jails)), ('Jail list', ", ".join(jails))]))
		self.server.addJail("TestJail2", "auto")
		jails.append("TestJail2")
		self.assertEqual(self.transm.proceed(["status"]),
			(0, [('Number of jail', len(jails)), ('Jail list', ", ".join(jails))]))

	def testJailStatus(self):
		self.assertEqual(self.transm.proceed(["status", self.jailName]),
			(0,
				[
					('Filter', [
						('Currently failed', 0),
						('Total failed', 0),
						('File list', [])]
					),
					('Actions', [
						('Currently banned', 0),
						('Total banned', 0),
						('Banned IP list', [])]
					)
				]
			)
		)

	def testAction(self):
		action = "TestCaseAction"
		cmdList = [
			"actionstart",
			"actionstop",
			"actioncheck",
			"actionban",
			"actionunban",
		]
		cmdValueList = [
			"Action Start",
			"Action Stop",
			"Action Check",
			"Action Ban",
			"Action Unban",
		]

		self.assertEqual(
			self.transm.proceed(["set", self.jailName, "addaction", action]),
			(0, action))
		self.assertEqual(
			self.transm.proceed(
				["get", self.jailName, "actions"])[1][0],
			action)
		for cmd, value in zip(cmdList, cmdValueList):
			self.assertEqual(
				self.transm.proceed(
					["set", self.jailName, "action", action, cmd, value]),
				(0, value))
		for cmd, value in zip(cmdList, cmdValueList):
			self.assertEqual(
				self.transm.proceed(["get", self.jailName, "action", action, cmd]),
				(0, value))
		self.assertEqual(
			self.transm.proceed(
				["set", self.jailName, "action", action, "KEY", "VALUE"]),
			(0, "VALUE"))
		self.assertEqual(
			self.transm.proceed(
				["get", self.jailName, "action", action, "KEY"]),
			(0, "VALUE"))
		self.assertEqual(
			self.transm.proceed(
				["get", self.jailName, "action", action, "InvalidKey"])[0],
			1)
		self.assertEqual(
			self.transm.proceed(
				["set", self.jailName, "action", action, "timeout", "10"]),
			(0, 10))
		self.assertEqual(
			self.transm.proceed(
				["get", self.jailName, "action", action, "timeout"]),
			(0, 10))
		self.assertEqual(
			self.transm.proceed(["set", self.jailName, "delaction", action]),
			(0, None))
		self.assertEqual(
			self.transm.proceed(
				["set", self.jailName, "delaction", "Doesn't exist"])[0],1)

	def testPythonActionMethodsAndProperties(self):
		action = "TestCaseAction"
		try:
			out = self.transm.proceed(
				["set", self.jailName, "addaction", action,
				 os.path.join(TEST_FILES_DIR, "action.d", "action.py"),
				'{"opt1": "value"}'])
			self.assertEqual(out, (0, action))
		except AssertionError:
			if ((2, 6) <= sys.version_info < (2, 6, 5)) \
				and '__init__() keywords must be strings' in out[1]:
				# known issue http://bugs.python.org/issue2646 in 2.6 series
				# since general Fail2Ban warnings are suppressed in normal
				# operation -- let's issue Python's native warning here
				import warnings
				warnings.warn(
					"Your version of Python %s seems to experience a known "
					"issue forbidding correct operation of Fail2Ban: "
					"http://bugs.python.org/issue2646  Upgrade your Python and "
					"meanwhile other intestPythonActionMethodsAndProperties will "
					"be skipped" % (sys.version))
				return
			raise
		self.assertEqual(
			sorted(self.transm.proceed(["get", self.jailName,
				"actionproperties", action])[1]),
			['opt1', 'opt2'])
		self.assertEqual(
			self.transm.proceed(["get", self.jailName, "action", action,
				"opt1"]),
			(0, 'value'))
		self.assertEqual(
			self.transm.proceed(["get", self.jailName, "action", action,
				"opt2"]),
			(0, None))
		self.assertEqual(
			sorted(self.transm.proceed(["get", self.jailName, "actionmethods",
				action])[1]),
			['ban', 'start', 'stop', 'testmethod', 'unban'])
		self.assertEqual(
			self.transm.proceed(["set", self.jailName, "action", action,
				"testmethod", '{"text": "world!"}']),
			(0, 'Hello world! value'))
		self.assertEqual(
			self.transm.proceed(["set", self.jailName, "action", action,
				"opt1", "another value"]),
			(0, 'another value'))
		self.assertEqual(
			self.transm.proceed(["set", self.jailName, "action", action,
				"testmethod", '{"text": "world!"}']),
			(0, 'Hello world! another value'))

	def testNOK(self):
		self.assertEqual(self.transm.proceed(["INVALID", "COMMAND"])[0],1)

	def testSetNOK(self):
		self.assertEqual(
			self.transm.proceed(["set", "INVALID", "COMMAND"])[0],1)

	def testGetNOK(self):
		self.assertEqual(
			self.transm.proceed(["get", "INVALID", "COMMAND"])[0],1)

	def testStatusNOK(self):
		self.assertEqual(
			self.transm.proceed(["status", "INVALID", "COMMAND"])[0],1)

	def testJournalMatch(self):
		if not filtersystemd: # pragma: no cover
			if sys.version_info >= (2, 7):
				raise unittest.SkipTest(
					"systemd python interface not available")
			return
		jailName = "TestJail2"
		self.server.addJail(jailName, "systemd")
		values = [
			"_SYSTEMD_UNIT=sshd.service",
			"TEST_FIELD1=ABC",
			"_HOSTNAME=example.com",
		]
		for n, value in enumerate(values):
			self.assertEqual(
				self.transm.proceed(
					["set", jailName, "addjournalmatch", value]),
				(0, [[val] for val in values[:n+1]]))
		for n, value in enumerate(values):
			self.assertEqual(
				self.transm.proceed(
					["set", jailName, "deljournalmatch", value]),
				(0, [[val] for val in values[n+1:]]))

		# Try duplicates
		value = "_COMM=sshd"
		self.assertEqual(
			self.transm.proceed(
				["set", jailName, "addjournalmatch", value]),
			(0, [[value]]))
		# Duplicates are accepted, as automatically OR'd, and journalctl
		# also accepts them without issue.
		self.assertEqual(
			self.transm.proceed(
				["set", jailName, "addjournalmatch", value]),
			(0, [[value], [value]]))
		# Remove first instance
		self.assertEqual(
			self.transm.proceed(
				["set", jailName, "deljournalmatch", value]),
			(0, [[value]]))
		# Remove second instance
		self.assertEqual(
			self.transm.proceed(
				["set", jailName, "deljournalmatch", value]),
			(0, []))

		value = [
			"_COMM=sshd", "+", "_SYSTEMD_UNIT=sshd.service", "_UID=0"]
		self.assertEqual(
			self.transm.proceed(
				["set", jailName, "addjournalmatch"] + value),
			(0, [["_COMM=sshd"], ["_SYSTEMD_UNIT=sshd.service", "_UID=0"]]))
		self.assertEqual(
			self.transm.proceed(
				["set", jailName, "deljournalmatch"] + value[:1]),
			(0, [["_SYSTEMD_UNIT=sshd.service", "_UID=0"]]))
		self.assertEqual(
			self.transm.proceed(
				["set", jailName, "deljournalmatch"] + value[2:]),
			(0, []))

		# Invalid match
		value = "This isn't valid!"
		result = self.transm.proceed(
			["set", jailName, "addjournalmatch", value])
		self.assertTrue(isinstance(result[1], ValueError))

		# Delete invalid match
		value = "FIELD=NotPresent"
		result = self.transm.proceed(
			["set", jailName, "deljournalmatch", value])
		self.assertTrue(isinstance(result[1], ValueError))

class TransmitterLogging(TransmitterBase):

	def setUp(self):
		self.server = Server()
		self.server.setLogTarget("/dev/null")
		self.server.setLogLevel("CRITICAL")
		super(TransmitterLogging, self).setUp()

	def testLogTarget(self):
		logTargets = []
		for _ in xrange(3):
			tmpFile = tempfile.mkstemp("fail2ban", "transmitter")
			logTargets.append(tmpFile[1])
			os.close(tmpFile[0])
		for logTarget in logTargets:
			self.setGetTest("logtarget", logTarget)

		# If path is invalid, do not change logtarget
		value = "/this/path/should/not/exist"
		self.setGetTestNOK("logtarget", value)

		self.transm.proceed(["set", "logtarget", "/dev/null"])
		for logTarget in logTargets:
			os.remove(logTarget)

		self.setGetTest("logtarget", "STDOUT")
		self.setGetTest("logtarget", "STDERR")

	def testLogTargetSYSLOG(self):
		if not os.path.exists("/dev/log") and sys.version_info >= (2, 7):
			raise unittest.SkipTest("'/dev/log' not present")
		elif not os.path.exists("/dev/log"):
			return
		self.setGetTest("logtarget", "SYSLOG")

	def testLogLevel(self):
		self.setGetTest("loglevel", "HEAVYDEBUG")
		self.setGetTest("loglevel", "DEBUG")
		self.setGetTest("loglevel", "INFO")
		self.setGetTest("loglevel", "NOTICE")
		self.setGetTest("loglevel", "WARNING")
		self.setGetTest("loglevel", "ERROR")
		self.setGetTest("loglevel", "CRITICAL")
		self.setGetTest("loglevel", "cRiTiCaL", "CRITICAL")
		self.setGetTestNOK("loglevel", "Bird")

	def testFlushLogs(self):
		self.assertEqual(self.transm.proceed(["flushlogs"]), (0, "rolled over"))
		try:
			f, fn = tempfile.mkstemp("fail2ban.log")
			os.close(f)
			self.server.setLogLevel("WARNING")
			self.assertEqual(self.transm.proceed(["set", "logtarget", fn]), (0, fn))
			l = logging.getLogger('fail2ban.server.server').parent.parent
			l.warning("Before file moved")
			try:
				f2, fn2 = tempfile.mkstemp("fail2ban.log")
				os.close(f2)
				os.rename(fn, fn2)
				l.warning("After file moved")
				self.assertEqual(self.transm.proceed(["flushlogs"]), (0, "rolled over"))
				l.warning("After flushlogs")
				with open(fn2,'r') as f:
					line1 = f.next()
					if line1.find('Changed logging target to') >= 0:
						line1 = f.next()
					self.assertTrue(line1.endswith("Before file moved\n"))
					line2 = f.next()
					self.assertTrue(line2.endswith("After file moved\n"))
					try:
						n = f.next()
						if n.find("Command: ['flushlogs']") >=0:
							self.assertRaises(StopIteration, f.next)
						else:
							self.fail("Exception StopIteration or Command: ['flushlogs'] expected. Got: %s" % n)
					except StopIteration:
						pass # on higher debugging levels this is expected
				with open(fn,'r') as f:
					line1 = f.next()
					if line1.find('rollover performed on') >= 0:
						line1 = f.next()
					self.assertTrue(line1.endswith("After flushlogs\n"))
					self.assertRaises(StopIteration, f.next)
					f.close()
			finally:
				os.remove(fn2)
		finally:
			try:
				os.remove(fn)
			except OSError:
				pass
		self.assertEqual(self.transm.proceed(["set", "logtarget", "STDERR"]), (0, "STDERR"))
		self.assertEqual(self.transm.proceed(["flushlogs"]), (0, "flushed"))


class JailTests(unittest.TestCase):

	def testLongName(self):
		# Just a smoke test for now
		longname = "veryveryverylongname"
		jail = Jail(longname)
		self.assertEqual(jail.name, longname)

class RegexTests(unittest.TestCase):

	def testInit(self):
		# Should raise an Exception upon empty regex
		self.assertRaises(RegexException, Regex, '')
		self.assertRaises(RegexException, Regex, ' ')
		self.assertRaises(RegexException, Regex, '\t')

	def testStr(self):
		# .replace just to guarantee uniform use of ' or " in the %r
		self.assertEqual(str(Regex('a')).replace('"', "'"), "Regex('a')")
		# Class name should be proper
		self.assertTrue(str(FailRegex('<HOST>')).startswith("FailRegex("))

	def testHost(self):
		self.assertRaises(RegexException, FailRegex, '')
		# Testing obscure case when host group might be missing in the matched pattern,
		# e.g. if we made it optional.
		fr = FailRegex('%%<HOST>?')
		self.assertFalse(fr.hasMatched())
		fr.search([('%%',"","")])
		self.assertTrue(fr.hasMatched())
		self.assertRaises(RegexException, fr.getHost)




########NEW FILE########
__FILENAME__ = sockettestcase
# emacs: -*- mode: python; py-indent-offset: 4; indent-tabs-mode: t -*-
# vi: set ft=python sts=4 ts=4 sw=4 noet :

# This file is part of Fail2Ban.
#
# Fail2Ban is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# Fail2Ban is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with Fail2Ban; if not, write to the Free Software
# Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA  02110-1301, USA.

# Author: Steven Hiscocks
# 

__author__ = "Steven Hiscocks"
__copyright__ = "Copyright (c) 2013 Steven Hiscocks"
__license__ = "GPL"

import unittest, time, tempfile, os, threading

from ..server.asyncserver import AsyncServer, AsyncServerException
from ..client.csocket import CSocket

class Socket(unittest.TestCase):

	def setUp(self):
		"""Call before every test case."""
		self.server = AsyncServer(self)
		sock_fd, sock_name = tempfile.mkstemp('fail2ban.sock', 'socket')
		os.close(sock_fd)
		os.remove(sock_name)
		self.sock_name = sock_name

	def tearDown(self):
		"""Call after every test case."""

	@staticmethod
	def proceed(message):
		"""Test transmitter proceed method which just returns first arg"""
		return message

	def testSocket(self):
		serverThread = threading.Thread(
			target=self.server.start, args=(self.sock_name, False))
		serverThread.daemon = True
		serverThread.start()
		time.sleep(1)

		client = CSocket(self.sock_name)
		testMessage = ["A", "test", "message"]
		self.assertEqual(client.send(testMessage), testMessage)

		self.server.stop()
		serverThread.join(1)
		self.assertFalse(os.path.exists(self.sock_name))

	def testSocketForce(self):
		open(self.sock_name, 'w').close() # Create sock file
		# Try to start without force
		self.assertRaises(
			AsyncServerException, self.server.start, self.sock_name, False)

		# Try again with force set
		serverThread = threading.Thread(
			target=self.server.start, args=(self.sock_name, True))
		serverThread.daemon = True
		serverThread.start()
		time.sleep(1)

		self.server.stop()
		serverThread.join(1)
		self.assertFalse(os.path.exists(self.sock_name))

########NEW FILE########
__FILENAME__ = utils
# emacs: -*- mode: python; py-indent-offset: 4; indent-tabs-mode: t -*-
# vi: set ft=python sts=4 ts=4 sw=4 noet :

# This file is part of Fail2Ban.
#
# Fail2Ban is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# Fail2Ban is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with Fail2Ban; if not, write to the Free Software
# Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA  02110-1301, USA.


__author__ = "Yaroslav Halchenko"
__copyright__ = "Copyright (c) 2013 Yaroslav Halchenko"
__license__ = "GPL"

import logging
import os
import re
import time
import unittest
from StringIO import StringIO

from ..server.mytime import MyTime

logSys = logging.getLogger(__name__)

def mtimesleep():
	# no sleep now should be necessary since polling tracks now not only
	# mtime but also ino and size
	pass

old_TZ = os.environ.get('TZ', None)
def setUpMyTime():
	# Set the time to a fixed, known value
	# Sun Aug 14 12:00:00 CEST 2005
	# yoh: we need to adjust TZ to match the one used by Cyril so all the timestamps match
	os.environ['TZ'] = 'Europe/Zurich'
	time.tzset()
	MyTime.setTime(1124013600)

def tearDownMyTime():
	os.environ.pop('TZ')
	if old_TZ:
		os.environ['TZ'] = old_TZ
	time.tzset()
	MyTime.myTime = None

def gatherTests(regexps=None, no_network=False):
	# Import all the test cases here instead of a module level to
	# avoid circular imports
	from . import banmanagertestcase
	from . import clientreadertestcase
	from . import failmanagertestcase
	from . import filtertestcase
	from . import servertestcase
	from . import datedetectortestcase
	from . import actiontestcase
	from . import actionstestcase
	from . import sockettestcase
	from . import misctestcase
	from . import databasetestcase
	from . import samplestestcase

	if not regexps: # pragma: no cover
		tests = unittest.TestSuite()
	else: # pragma: no cover
		class FilteredTestSuite(unittest.TestSuite):
			_regexps = [re.compile(r) for r in regexps]
			def addTest(self, suite):
				suite_str = str(suite)
				for r in self._regexps:
					if r.search(suite_str):
						super(FilteredTestSuite, self).addTest(suite)
						return

		tests = FilteredTestSuite()

	# Server
	#tests.addTest(unittest.makeSuite(servertestcase.StartStop))
	tests.addTest(unittest.makeSuite(servertestcase.Transmitter))
	tests.addTest(unittest.makeSuite(servertestcase.JailTests))
	tests.addTest(unittest.makeSuite(servertestcase.RegexTests))
	tests.addTest(unittest.makeSuite(actiontestcase.CommandActionTest))
	tests.addTest(unittest.makeSuite(actionstestcase.ExecuteActions))
	# FailManager
	tests.addTest(unittest.makeSuite(failmanagertestcase.AddFailure))
	# BanManager
	tests.addTest(unittest.makeSuite(banmanagertestcase.AddFailure))
	# ClientReaders
	tests.addTest(unittest.makeSuite(clientreadertestcase.ConfigReaderTest))
	tests.addTest(unittest.makeSuite(clientreadertestcase.JailReaderTest))
	tests.addTest(unittest.makeSuite(clientreadertestcase.FilterReaderTest))
	tests.addTest(unittest.makeSuite(clientreadertestcase.JailsReaderTest))
	# CSocket and AsyncServer
	tests.addTest(unittest.makeSuite(sockettestcase.Socket))
	# Misc helpers
	tests.addTest(unittest.makeSuite(misctestcase.HelpersTest))
	tests.addTest(unittest.makeSuite(misctestcase.SetupTest))
	tests.addTest(unittest.makeSuite(misctestcase.TestsUtilsTest))
	tests.addTest(unittest.makeSuite(misctestcase.CustomDateFormatsTest))
	# Database
	tests.addTest(unittest.makeSuite(databasetestcase.DatabaseTest))

	# Filter
	tests.addTest(unittest.makeSuite(filtertestcase.IgnoreIP))
	tests.addTest(unittest.makeSuite(filtertestcase.BasicFilter))
	tests.addTest(unittest.makeSuite(filtertestcase.LogFile))
	tests.addTest(unittest.makeSuite(filtertestcase.LogFileMonitor))
	tests.addTest(unittest.makeSuite(filtertestcase.LogFileFilterPoll))
	if not no_network:
		tests.addTest(unittest.makeSuite(filtertestcase.IgnoreIPDNS))
		tests.addTest(unittest.makeSuite(filtertestcase.GetFailures))
		tests.addTest(unittest.makeSuite(filtertestcase.DNSUtilsTests))
	tests.addTest(unittest.makeSuite(filtertestcase.JailTests))

	# DateDetector
	tests.addTest(unittest.makeSuite(datedetectortestcase.DateDetectorTest))
	# Filter Regex tests with sample logs
	tests.addTest(unittest.makeSuite(samplestestcase.FilterSamplesRegex))

	#
	# Python action testcases
	#
	testloader = unittest.TestLoader()
	from . import action_d
	for file_ in os.listdir(
		os.path.abspath(os.path.dirname(action_d.__file__))):
		if file_.startswith("test_") and file_.endswith(".py"):
			if no_network and file_ in ['test_badips.py']: #pragma: no cover
				# Test required network
				continue
			tests.addTest(testloader.loadTestsFromName(
				"%s.%s" % (action_d.__name__, os.path.splitext(file_)[0])))

	#
	# Extensive use-tests of different available filters backends
	#

	from ..server.filterpoll import FilterPoll
	filters = [FilterPoll]					  # always available

	# Additional filters available only if external modules are available
	# yoh: Since I do not know better way for parametric tests
	#      with good old unittest
	try:
		from ..server.filtergamin import FilterGamin
		filters.append(FilterGamin)
	except Exception, e: # pragma: no cover
		logSys.warning("Skipping gamin backend testing. Got exception '%s'" % e)

	try:
		from ..server.filterpyinotify import FilterPyinotify
		filters.append(FilterPyinotify)
	except Exception, e: # pragma: no cover
		logSys.warning("I: Skipping pyinotify backend testing. Got exception '%s'" % e)

	for Filter_ in filters:
		tests.addTest(unittest.makeSuite(
			filtertestcase.get_monitor_failures_testcase(Filter_)))
	try: # pragma: systemd no cover
		from ..server.filtersystemd import FilterSystemd
		tests.addTest(unittest.makeSuite(filtertestcase.get_monitor_failures_journal_testcase(FilterSystemd)))
	except Exception, e: # pragma: no cover
		logSys.warning("I: Skipping systemd backend testing. Got exception '%s'" % e)


	# Server test for logging elements which break logging used to support
	# testcases analysis
	tests.addTest(unittest.makeSuite(servertestcase.TransmitterLogging))

	return tests

class LogCaptureTestCase(unittest.TestCase):

	def setUp(self):

		# For extended testing of what gets output into logging
		# system, we will redirect it to a string
		logSys = logging.getLogger("fail2ban")

		# Keep old settings
		self._old_level = logSys.level
		self._old_handlers = logSys.handlers
		# Let's log everything into a string
		self._log = StringIO()
		logSys.handlers = [logging.StreamHandler(self._log)]
		logSys.setLevel(getattr(logging, 'DEBUG'))

	def tearDown(self):
		"""Call after every test case."""
		# print "O: >>%s<<" % self._log.getvalue()
		logSys = logging.getLogger("fail2ban")
		logSys.handlers = self._old_handlers
		logSys.level = self._old_level

	def _is_logged(self, s):
		return s in self._log.getvalue()

	def printLog(self):
		print(self._log.getvalue())

########NEW FILE########
__FILENAME__ = version
# emacs: -*- mode: python; py-indent-offset: 4; indent-tabs-mode: t -*-
# vi: set ft=python sts=4 ts=4 sw=4 noet :

# This file is part of Fail2Ban.
#
# Fail2Ban is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# Fail2Ban is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with Fail2Ban; if not, write to the Free Software
# Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA  02110-1301, USA.

# Author: Cyril Jaquier
#

__author__ = "Cyril Jaquier, Yaroslav Halchenko, Steven Hiscocks, Daniel Black"
__copyright__ = "Copyright (c) 2004 Cyril Jaquier, 2011-2014 Yaroslav Halchenko, 2013-2013 Steven Hiscocks, Daniel Black"
__license__ = "GPL-v2+"

version = "0.9.0.dev"

########NEW FILE########
