__FILENAME__ = accountsmanager
'''
Copyright (c) 2012, Tarek Galal <tarek@wazapp.im>

This file is part of Wazapp, an IM application for Meego Harmattan platform that
allows communication with Whatsapp users

Wazapp is free software: you can redistribute it and/or modify it under the 
terms of the GNU General Public License as published by the Free Software 
Foundation, either version 2 of the License, or (at your option) any later 
version.

Wazapp is distributed in the hope that it will be useful, but WITHOUT ANY 
WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS FOR A 
PARTICULAR PURPOSE. See the GNU General Public License for more details.

You should have received a copy of the GNU General Public License along with 
Wazapp. If not, see http://www.gnu.org/licenses/.
'''
from Models.account import Account as WAAccount;
from Accounts import *

from utilities import Utilities


from wadebug import AccountsDebug;
import base64

class AccountsManager():

	manager = Manager()
		
	@staticmethod
	def getCurrentAccount():
		account = AccountsManager.findAccount()
		
		return account

	@staticmethod
	def setPushName(pushname):
		d = AccountsDebug()
		_d = d.d;
		_d("Finding account for push name update")
		account = AccountsManager.findAccount()
		if account:
			account.accountInstance.setValue("pushName",pushname)
			account.accountInstance.sync()

	@staticmethod
	def getAccountById(accountId):
		account = AccountsManager.manager.account(accountId)
		waaccount = WAAccount(account.valueAsString("cc"),account.valueAsString("phoneNumber"),account.valueAsString("username"),account.valueAsString("status"),account.valueAsString("pushName"),account.valueAsString("imsi"),account.valueAsString("password"));
		waaccount.setAccountInstance(account)
		return waaccount

	@staticmethod	
	def findAccount():
		d = AccountsDebug()
		_d = d.d;
		imsi = Utilities.getImsi()
		_d("Looking for %s "%(imsi))
		accountIds = AccountsManager.manager.accountList()

		for aId in accountIds:
			a = AccountsManager.manager.account(aId)
			services = a.services()
			for s in services:
				if s.name() in ("waxmpp"):
					_d("found waxmpp account with imsi: %s"%(a.valueAsString("imsi")))
					if a.valueAsString("imsi") == imsi:
						account = a
						waaccount = WAAccount(account.valueAsString("cc"),
											account.valueAsString("phoneNumber"),
											account.valueAsString("username"),
											account.valueAsString("status"),
											account.valueAsString("pushName"),
											account.valueAsString("imsi"),
											base64.b64decode(account.valueAsString("password")) 
												if account.valueAsString("penc") == "b64" 
												else str(account.valueAsString("password"))); #to ensure backwards compatibility for non-blocked accounts

						if account.valueAsString("wazapp_version"): #rest of data exist
							waaccount.setExtraData(account.valueAsString("kind"), 
													account.valueAsString("expiration"),
													account.valueAsString("cost"), 
													account.valueAsString("currency"),
													account.valueAsString("price"), 
													account.valueAsString("price_expiration"))
						
						waaccount.setAccountInstance(a)
						
						return waaccount
		
		return None
		
		

########NEW FILE########
__FILENAME__ = connmon
'''
Copyright (c) 2012, Tarek Galal <tarek@wazapp.im>

This file is part of Wazapp, an IM application for Meego Harmattan platform that
allows communication with Whatsapp users

Wazapp is free software: you can redistribute it and/or modify it under the 
terms of the GNU General Public License as published by the Free Software 
Foundation, either version 2 of the License, or (at your option) any later 
version.

Wazapp is distributed in the hope that it will be useful, but WITHOUT ANY 
WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS FOR A 
PARTICULAR PURPOSE. See the GNU General Public License for more details.

You should have received a copy of the GNU General Public License along with 
Wazapp. If not, see http://www.gnu.org/licenses/.
'''
from PySide.QtCore import *
from PySide.QtGui import *
from PySide import QtCore
from PySide.QtNetwork import QNetworkSession, QNetworkConfigurationManager,QNetworkConfiguration, QNetworkAccessManager 
import sys
import PySide

from wadebug import ConnMonDebug;

class ConnMonitor(QObject):

	connectionSwitched = QtCore.Signal();
	connected = QtCore.Signal()
	disconnected = QtCore.Signal()
	
	def __init__(self):
		super(ConnMonitor,self).__init__();
		
		_d = ConnMonDebug();
		self._d = _d.d;
		
		self.session = None
		self.online = False
		self.manager = QNetworkConfigurationManager()
		self.config = self.manager.defaultConfiguration() if self.manager.isOnline() else None
		
		self.manager.onlineStateChanged.connect(self.onOnlineStateChanged)
		self.manager.configurationChanged.connect(self.onConfigurationChanged)
		
		self.connected.connect(self.onOnline)
		self.disconnected.connect(self.onOffline)
		self.session =  QNetworkSession(self.manager.defaultConfiguration());
		self.session.stateChanged.connect(self.sessionStateChanged)
		self.session.closed.connect(self.disconnected);
		#self.session.opened.connect(self.connected);
		#self.createSession();
		#self.session.waitForOpened(-1)
	
	
	def sessionStateChanged(self,state):
		self._d("state changed "+str(state));
	
	def createSession(self):
		
		#self.session.setSessionProperty("ConnectInBackground", True);
		self.session.open();
	
	def isOnline(self):
		return self.manager.isOnline()
	
	def onConfigurationChanged(self,config):
		if self.manager.isOnline() and config.state() == PySide.QtNetwork.QNetworkConfiguration.StateFlag.Active:
			if self.config is None:
				self.config = config
			else:
				self.createSession();
				self.connected.emit()
		
	def onOnlineStateChanged(self,state):
		self.online = state
		if state:
			self.connected.emit()
		elif not self.isOnline():
			self.config = None
			self.disconnected.emit()
	
	def onOnline(self):
		self._d("ONLINE")
		#self.session = QNetworkSession(self.config)
	
	def onOffline(self):
		self._d("OFFLINE");
	

		
		

if __name__=="__main__":
	app = QApplication(sys.argv)
	cm = ConnMon()
	
	
	sys.exit(app.exec_())

########NEW FILE########
__FILENAME__ = constants
'''
Copyright (c) 2012, Tarek Galal <tarek@wazapp.im>

This file is part of Wazapp, an IM application for Meego Harmattan platform that
allows communication with Whatsapp users

Wazapp is free software: you can redistribute it and/or modify it under the 
terms of the GNU General Public License as published by the Free Software 
Foundation, either version 2 of the License, or (at your option) any later 
version.

Wazapp is distributed in the hope that it will be useful, but WITHOUT ANY 
WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS FOR A 
PARTICULAR PURPOSE. See the GNU General Public License for more details.

You should have received a copy of the GNU General Public License along with 
Wazapp. If not, see http://www.gnu.org/licenses/.
'''

import os

class WAConstants():
	
	STORE_PATH = os.path.expanduser('~/.wazapp');
	VHISTORY_PATH = STORE_PATH+"/v"
	
	#MEDIA_PATH = STORE_PATH+'/media'
	MYDOCS_PATH = "/home/user/MyDocs"
	APP_PATH = MYDOCS_PATH+'/Wazapp'
	MEDIA_PATH = APP_PATH+'/media'
	AUDIO_PATH = MEDIA_PATH+'/audio'
	IMAGE_PATH = MEDIA_PATH+'/images'
	VIDEO_PATH = MEDIA_PATH+'/videos'
	VCARD_PATH = MEDIA_PATH+'/contacts'

	CACHE_PATH = os.path.expanduser('~/.cache/wazapp');
	CACHE_CONTACTS = CACHE_PATH+"/contacts"
	CACHE_PROFILE = CACHE_PATH+"/profile"
	
	CACHE_CONV = MYDOCS_PATH+"/Documents"

	THUMBS_PATH = os.path.expanduser('/home/user/.thumbnails');
		
	CLIENT_INSTALL_PATH = '/opt/waxmppplugin/bin/wazapp'
	
	DEFAULT_CONTACT_PICTURE = CLIENT_INSTALL_PATH+'/'+'UI/common/images/user.png';
	DEFAULT_GROUP_PICTURE = CLIENT_INSTALL_PATH+'/'+'UI/common/images/group.png';
	
	DEFAULT_SOUND_NOTIFICATION = "/usr/share/sounds/ring-tones/Message 1.mp3"
	FOCUSED_SOUND_NOTIFICATION = "/usr/share/sounds/ui-tones/snd_default_beep.wav"
	DEFAULT_BEEP_NOTIFICATION = "/usr/share/sounds/ui-tones/snd_chat_fg.wav"
	NO_SOUND = "/usr/share/sounds/ring-tones/No sound.wav"
	
	MEDIA_TYPE_TEXT		= 1
	MEDIA_TYPE_IMAGE	= 2
	MEDIA_TYPE_AUDIO	= 3
	MEDIA_TYPE_VIDEO	= 4
	MEDIA_TYPE_LOCATION	= 5
	MEDIA_TYPE_VCARD	= 6

	INITIAL_USER_STATUS = "Hi there I'm using Wazapp"
	
	DATE_FORMAT = "%d-%m-%Y %H:%M"


	@staticmethod
	def getAllProperties():
		return vars(WAConstants)

########NEW FILE########
__FILENAME__ = contacts
'''
Copyright (c) 2012, Tarek Galal <tarek@wazapp.im>

This file is part of Wazapp, an IM application for Meego Harmattan platform that
allows communication with Whatsapp users

Wazapp is free software: you can redistribute it and/or modify it under the 
terms of the GNU General Public License as published by the Free Software 
Foundation, either version 2 of the License, or (at your option) any later 
version.

Wazapp is distributed in the hope that it will be useful, but WITHOUT ANY 
WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS FOR A 
PARTICULAR PURPOSE. See the GNU General Public License for more details.

You should have received a copy of the GNU General Public License along with 
Wazapp. If not, see http://www.gnu.org/licenses/.
'''
import os
from Yowsup.Contacts.contacts import WAContactsSyncRequest
from Registration.registrationhandler import async
from PySide import QtCore
from PySide.QtCore import QObject, QUrl, QFile, QIODevice
from PySide.QtGui import QImage
from QtMobility.Contacts import *
from QtMobility.Versit import *
from constants import WAConstants
from wadebug import WADebug;
import sys
from waimageprocessor import WAImageProcessor
from accountsmanager import AccountsManager

class ContactsSyncer(QObject):
	'''
	Interfaces with whatsapp contacts server to get contact list
	'''
	contactsRefreshSuccess = QtCore.Signal(str,dict);
	contactsRefreshFail = QtCore.Signal();
	contactsSyncStatus = QtCore.Signal(str);

	def __init__(self,store, contactsManager, mode,userid = None):
		WADebug.attach(self);
		self.store = store;
		self.mode = mode
		self.uid = userid;
		
		super(ContactsSyncer,self).__init__();
		
		acc = AccountsManager.getCurrentAccount();
		
		if not acc:
			self.contactsRefreshFail.emit()
			
		
		username = str(acc.username)
		password = acc.password
		
		self.contactsManager = contactsManager
			
		self.syncer = WAContactsSyncRequest(username, password, [])	
		
	def sync(self):
		self._d("INITiATING SYNC")
		self.contactsSyncStatus.emit("GETTING");

		if self.mode == "STATUS":
			self.uid = "+" + self.uid
			self._d("Sync contact for status: " + self.uid)
			self.syncer.setContacts([self.uid])

		elif self.mode == "SYNC":
			
			phoneContacts = self.contactsManager.getPhoneContacts();
			contacts = []
			for c in phoneContacts:
				for number in c[2]:
					try:
						contacts.append(str(number))
					except UnicodeEncodeError:
						continue
			
			self.syncer.setContacts(contacts)


		self.contactsSyncStatus.emit("SENDING");
		result = self.syncer.send()
		
		if result:
			print("DONE!!")
			self.updateContacts(result["c"]);
		else:
			self.contactsRefreshFail.emit();
		
		
		
	def updateContacts(self, contacts):
		#data = str(data);
	
		if self.mode == "STATUS":
			for c in contacts:
				
				
				if not c['w'] == 1:
					continue

				status = c["s"];
				
				jid = "%s@s.whatsapp.net" % c['n']
				status = c["s"]#.encode('utf-8')

				contact = self.store.Contact.getOrCreateContactByJid(jid)
				contact.status = status.encode("unicode_escape")
				contact.save()

				self.contactsRefreshSuccess.emit(self.mode, contact);

		else:
			for c in contacts:
				self.contactsSyncStatus.emit("LOADING");
				
				if not c['w'] == 1:
					continue
				
				jid = "%s@s.whatsapp.net" % c['n']
				status = c["s"].encode("unicode_escape")
				#number = str(c["p"])
				
				contact = self.store.Contact.getOrCreateContactByJid(jid)
				contact.status = status
				contact.iscontact = "yes"
				contact.save()

			self.contactsRefreshSuccess.emit(self.mode, {});	

		
	def onRefreshing(self):
		self.start();

	@async
	def start(self):
		try:
			self.sync();
		except:
			self._d(sys.exc_info()[1])
			self.contactsRefreshFail.emit()
		#self.exec_();

class WAContacts(QObject):

	refreshing = QtCore.Signal();
	contactsRefreshed = QtCore.Signal(str,dict);
	contactsRefreshFailed = QtCore.Signal();
	contactsSyncStatusChanged = QtCore.Signal(str);
	contactUpdated = QtCore.Signal(str);
	contactPictureUpdated = QtCore.Signal(str);
	contactAdded = QtCore.Signal(str);
	contactExported = QtCore.Signal(str,str);

	def __init__(self,store):
		super(WAContacts,self).__init__();
		self.store = store;
		self.contacts = [];
		self.raw_contacts = None;
		self.manager = ContactsManager();
		self.imageProcessor = WAImageProcessor();
		
		self.syncer = ContactsSyncer(self.store, self, "SYNC");
		
		self.syncer.contactsRefreshSuccess.connect(self.contactsRefreshed);
		self.syncer.contactsRefreshFail.connect(self.contactsRefreshFailed);
		self.syncer.contactsSyncStatus.connect(self.contactsSyncStatusChanged);
		
		
	
	def initiateSyncer(self, mode, userid):
		self.syncer.mode = mode
		self.syncer.uid = userid

	def resync(self, mode, userid=None):
		self.initiateSyncer(mode, userid);
		self.refreshing.emit();
		self.syncer.start();
		
		
	def updateContact(self,jid):
		#if "@g.us" in jid:
		#	user_img = QImage("/opt/waxmppplugin/bin/wazapp/UI/common/images/group.png")
		#else:
		#	user_img = QImage("/opt/waxmppplugin/bin/wazapp/UI/common/images/user.png")

		jname = jid.replace("@s.whatsapp.net","").replace("@g.us","")
		if os.path.isfile(WAConstants.CACHE_CONTACTS + "/" + jname + ".jpg"):
			user_img = QImage(WAConstants.CACHE_CONTACTS + "/" + jname + ".jpg")
			
			user_img.save(WAConstants.CACHE_PROFILE + "/" + jname + ".jpg", "JPEG")
		
			self.imageProcessor.createSquircle(WAConstants.CACHE_CONTACTS + "/" + jname + ".jpg", WAConstants.CACHE_CONTACTS + "/" + jname + ".png")
			self.contactPictureUpdated.emit(jid);

	def checkPicture(self, jname, sourcePath):

		sourcePath = str(sourcePath)
		if os.path.isfile(WAConstants.CACHE_CONTACTS + "/" + jname + ".jpg"):
			#Don't overwrite if profile picture exists
			if os.path.isfile(WAConstants.CACHE_PROFILE + "/" + jname + ".jpg"):
				return
			user_img = WAConstants.CACHE_CONTACTS + "/" + jname + ".jpg"
		else:
			if os.path.isfile(WAConstants.CACHE_PROFILE + "/" + jname + ".jpg"):
				os.remove(WAConstants.CACHE_PROFILE + "/" + jname + ".jpg")
			user_img = sourcePath.replace("file://","")

		self.imageProcessor.createSquircle(user_img, WAConstants.CACHE_CONTACTS + "/" + jname + ".png")

		if os.path.isfile(WAConstants.CACHE_CONTACTS + "/" + jname + ".jpg"):
			os.remove(WAConstants.CACHE_CONTACTS + "/" + jname + ".jpg")

	def getContacts(self):
		contacts = self.store.Contact.fetchAll();
		if len(contacts) == 0:
			print "NO CONTACTS FOUNDED IN DATABASE"
			#self.resync();
			return contacts;		
		#O(n2) matching, need to change that
		cm = self.manager
		phoneContacts = cm.getContacts();
		tmp = []
		self.contacts = {};

		for wc in contacts:
			jname = wc.jid.replace("@s.whatsapp.net","")
			founded = False
			myname = ""
			picturePath = WAConstants.CACHE_CONTACTS + "/" + jname + ".png";
			for c in phoneContacts:
				if wc.number[-8:] == c['number'][-8:]:
					founded = True
					if c['picture']:
						self.checkPicture(jname,c['picture'] if type(c['picture']) == str else c['picture'].toString())

					c['picture'] = picturePath if os.path.isfile(picturePath) else None;
					myname = c['name']
					wc.setRealTimeData(myname,c['picture'],"yes");
					QtCore.QCoreApplication.processEvents()
					break;

			if founded is False and wc.number is not None:
				#self.checkPicture(jname,"")
				myname = wc.pushname.decode("utf8") if wc.pushname is not None else ""
				mypicture = picturePath if os.path.isfile(picturePath) else None;
				wc.setRealTimeData(myname,mypicture,"no");

			if wc.status is not None:
				wc.status = wc.status.decode("unicode_escape")
			if wc.pushname is not None:
				wc.pushname = wc.pushname.decode('utf-8');

			if wc.name is not "" and wc.name is not None:
				#print "ADDING CONTACT : " + myname
				tmp.append(wc.getModelData());
				self.contacts[wc.number] = wc;


		if len(tmp) == 0:
			print "NO CONTACTS ADDED!"
			return []

		print "TOTAL CONTACTS ADDED FROM DATABASE: " + str(len(tmp))
		self.store.cacheContacts(self.contacts);
		return sorted(tmp, key=lambda k: k['name'].upper());



	def getPhoneContacts(self):
		cm = self.manager
		phoneContacts = cm.getPhoneContacts();
		tmp = []

		for c in phoneContacts:
			wc = [];
			c['picture'] = QUrl(c['picture']).toString().replace("file://","")
			wc.append(c['name'])
			#wc.append(c['id'])
			wc.append(c['picture'])
			wc.append(c['numbers'])
			if ( len(c['numbers'])>0):
				tmp.append(wc);
		return sorted(tmp)



	def exportContact(self, jid, name):
		cm = self.manager
		phoneContacts = cm.getQtContacts();
		contacts = []

		for c in phoneContacts:
			if name == c.displayLabel():
				if os.path.isfile(WAConstants.CACHE_CONTACTS + "/" + name + ".vcf"):
					os.remove(WAConstants.CACHE_CONTACTS + "/" + name + ".vcf")
				print "founded contact: " + c.displayLabel()
				contacts.append(c)
				openfile = QFile(WAConstants.VCARD_PATH + "/" + name + ".vcf")
				openfile.open(QIODevice.WriteOnly)
				if openfile.isWritable():
					exporter = QVersitContactExporter()
					if exporter.exportContacts(contacts, QVersitDocument.VCard30Type):
						documents = exporter.documents()
						writer = QVersitWriter()
						writer.setDevice(openfile)
						writer.startWriting(documents)
						writer.waitForFinished()
				openfile.close()
				self.contactExported.emit(jid, name);
				break;



class ContactsManager(QObject):
	'''
	Provides access to phone's contacts manager API
	'''
	def __init__(self):
		super(ContactsManager,self).__init__();
		self.manager = QContactManager(self);
		self.contacts = []

	def getContacts(self):
		'''
		Gets all phone contacts
		'''
		contacts = self.manager.contacts();
		self.contacts = []
		for contact in contacts:
			avatars = contact.details(QContactAvatar.DefinitionName);
			avatar = QContactAvatar(avatars[0]).imageUrl() if len(avatars) > 0 else None;
			label =  contact.displayLabel();
			numbers = contact.details(QContactPhoneNumber.DefinitionName);

			for number in numbers:
				n = QContactPhoneNumber(number).number().replace("(", "").replace(")", "").replace(" ", "").replace("-", "")
				self.contacts.append({"alphabet":label[0].upper(),"name":label,"number":n,"picture":avatar});

		return self.contacts;


	def getPhoneContacts(self):
		contacts = self.manager.contacts();
		self.contacts = []
		for contact in contacts:
			avatars = contact.details(QContactAvatar.DefinitionName);
			avatar = QContactAvatar(avatars[0]).imageUrl() if len(avatars) > 0 else None;
			label =  contact.displayLabel();
			numbers = contact.details(QContactPhoneNumber.DefinitionName);
			allnumbers = []
			
			allnumbers = map(lambda n: QContactPhoneNumber(n).number().replace("(", "").replace(")", "").replace(" ", "").replace("-", ""), numbers   )
			
			#for number in numbers:
			#	allnumbers.append(QContactPhoneNumber(number).number())

			self.contacts.append({"name":label,"numbers":allnumbers,"picture":avatar});

		return self.contacts;


	def getQtContacts(self):
		return self.manager.contacts();
########NEW FILE########
__FILENAME__ = datastore
'''
Copyright (c) 2012, Tarek Galal <tarek@wazapp.im>

This file is part of Wazapp, an IM application for Meego Harmattan platform that
allows communication with Whatsapp users

Wazapp is free software: you can redistribute it and/or modify it under the 
terms of the GNU General Public License as published by the Free Software 
Foundation, either version 2 of the License, or (at your option) any later 
version.

Wazapp is distributed in the hope that it will be useful, but WITHOUT ANY 
WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS FOR A 
PARTICULAR PURPOSE. See the GNU General Public License for more details.

You should have received a copy of the GNU General Public License along with 
Wazapp. If not, see http://www.gnu.org/licenses/.
'''
import abc
from accountsmanager import AccountsManager;
class DataStore():
	

	
	def __init__(self,current_id):
		self.user_id = current_id;
		self.account = AccountsManager.getCurrentAccount();

	__metaclass__ = abc.ABCMeta

	
	@abc.abstractmethod
	def getContacts(self):
		'''get contacts'''

	def saveContact(self,contact):
		'''save contact'''

	def getConversation(self,contact_id):
		'''fetches chats for this contact'''

	def deleteConversation(self,contact_id):
		'''deletes all chats for this contact'''
	
	def logChat(self,FMsg):
		'''logs a message'''
		
	

########NEW FILE########
__FILENAME__ = DBusInterfaceHandler
import dbus
import os
parentdir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
os.sys.path.insert(0,parentdir)
from InterfaceHandler import InterfaceHandlerBase, InvalidSignalException, InvalidMethodException
class DBusInterfaceHandler(InterfaceHandlerBase):
	
	def __init__(self, username):
		bus = dbus.Bus()
		busObj = bus.get_object('com.yowsup.methods', '/com/yowsup/methods')
		
		initMethod = busObj.get_dbus_method("init",'com.yowsup.methods')
		
		result = initMethod(username)
		
		if result:
			self.initSignals(result)
			self.initMethods(result)
		
	def initSignals(self, connId):
		bus = dbus.Bus()
		self.signalRegistrar = bus.get_object('com.yowsup.signals', '/com/yowsup/%s/signals'%connId)

		getter = self.signalRegistrar.get_dbus_method('getSignals', 'com.yowsup.signals')
		self.signals = getter()

	def initMethods(self, connId):
		#get methods
		bus = dbus.Bus()
		self.methodsProvider = bus.get_object('com.yowsup.methods', '/com/yowsup/%s/methods'%connId)
		getter = self.methodsProvider.get_dbus_method('getMethods', 'com.yowsup.methods')
		self.methods = getter()

	
	def connectToSignal(self, signalName, callback):
		if not self.isSignal(signalName):
			raise InvalidSignalException()

		self.signalRegistrar.connect_to_signal(signalName, callback)

	def call(self, methodName, params = ()):
		if not self.isMethod(methodName):
			raise InvalidMethodException()

		
		method = self.methodsProvider.get_dbus_method(methodName, 'com.yowsup.methods')
		return method(*params)
		

########NEW FILE########
__FILENAME__ = InterfaceHandler
class InterfaceHandlerBase(object):
	def __init__(self):
		self.signals = []
		self.methods = []

	def connectToSignal(self, signalName, callback):
		pass

	def call(self, methodName, params = ()):
		pass

	def initSignals(self):
		pass

	def initMethods(self):
		pass

	def isSignal(self, signalName):
		try:
			self.signals.index(signalName)
			return True
		except:
			return False


	def isMethod(self, methodName):
		try:
			self.methods.index(methodName)
			return True
		except:
			return False


class InvalidSignalException(Exception):
	pass

class InvalidMethodException(Exception):
	pass

########NEW FILE########
__FILENAME__ = LibInterfaceHandler
import os
parentdir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
os.sys.path.insert(0,parentdir)
from InterfaceHandler import InterfaceHandlerBase, InvalidSignalException, InvalidMethodException

import sys
#sys.path.append("/home/tarek/Projects/")
#sys.path.append("/home/tarek/Projects/yowsup")

#sys.path.append("/home/developer/")
#sys.path.append("/home/developer/yowsup")

from Yowsup.connectionmanager import YowsupConnectionManager

class LibInterfaceHandler(InterfaceHandlerBase):
	
	def __init__(self, username):
		self.connectionManager = YowsupConnectionManager()
		self.connectionManager.setAutoPong(True)
		
		self.signalInterface = self.connectionManager.getSignalsInterface()
		self.methodInterface = self.connectionManager.getMethodsInterface()
		
		super(LibInterfaceHandler,self).__init__();
		
		self.initSignals()
		self.initMethods()

	def initSignals(self):		
		self.signals = self.signalInterface.getSignals()


	def initMethods(self):
		#get methods
		self.methods = self.methodInterface.getMethods()
	
	def connectToSignal(self, signalName, callback):
		if not self.isSignal(signalName):
			raise InvalidSignalException()
		
		self.signalInterface.registerListener(signalName, callback)

	def call(self, methodName, params = ()):
		if not self.isMethod(methodName):
			raise InvalidMethodException()

		return self.methodInterface.call(methodName, params)
		

########NEW FILE########
__FILENAME__ = wazlibs
# This file was automatically generated by SWIG (http://www.swig.org).
# Version 2.0.4
#
# Do not make changes to this file unless you know what you are doing--modify
# the SWIG interface file instead.



from sys import version_info
if version_info >= (2,6,0):
    def swig_import_helper():
        from os.path import dirname
        import imp
        fp = None
        try:
            fp, pathname, description = imp.find_module('_wazlibs', [dirname(__file__)])
        except ImportError:
            import _wazlibs
            return _wazlibs
        if fp is not None:
            try:
                _mod = imp.load_module('_wazlibs', fp, pathname, description)
            finally:
                fp.close()
            return _mod
    _wazlibs = swig_import_helper()
    del swig_import_helper
else:
    import _wazlibs
del version_info
try:
    _swig_property = property
except NameError:
    pass # Python < 2.2 doesn't have 'property'.
def _swig_setattr_nondynamic(self,class_type,name,value,static=1):
    if (name == "thisown"): return self.this.own(value)
    if (name == "this"):
        if type(value).__name__ == 'SwigPyObject':
            self.__dict__[name] = value
            return
    method = class_type.__swig_setmethods__.get(name,None)
    if method: return method(self,value)
    if (not static):
        self.__dict__[name] = value
    else:
        raise AttributeError("You cannot add attributes to %s" % self)

def _swig_setattr(self,class_type,name,value):
    return _swig_setattr_nondynamic(self,class_type,name,value,0)

def _swig_getattr(self,class_type,name):
    if (name == "thisown"): return self.this.own()
    method = class_type.__swig_getmethods__.get(name,None)
    if method: return method(self)
    raise AttributeError(name)

def _swig_repr(self):
    try: strthis = "proxy of " + self.this.__repr__()
    except: strthis = ""
    return "<%s.%s; %s >" % (self.__class__.__module__, self.__class__.__name__, strthis,)

try:
    _object = object
    _newclass = 1
except AttributeError:
    class _object : pass
    _newclass = 0


class WAProviderPluginProcess(_object):
    __swig_setmethods__ = {}
    __setattr__ = lambda self, name, value: _swig_setattr(self, WAProviderPluginProcess, name, value)
    __swig_getmethods__ = {}
    __getattr__ = lambda self, name: _swig_getattr(self, WAProviderPluginProcess, name)
    __repr__ = _swig_repr
    def __init__(self): 
        this = _wazlibs.new_WAProviderPluginProcess()
        try: self.this.append(this)
        except: self.this = this
    __swig_setmethods__["isUniqueInstance"] = _wazlibs.WAProviderPluginProcess_isUniqueInstance_set
    __swig_getmethods__["isUniqueInstance"] = _wazlibs.WAProviderPluginProcess_isUniqueInstance_get
    if _newclass:isUniqueInstance = _swig_property(_wazlibs.WAProviderPluginProcess_isUniqueInstance_get, _wazlibs.WAProviderPluginProcess_isUniqueInstance_set)
    __swig_setmethods__["initType"] = _wazlibs.WAProviderPluginProcess_initType_set
    __swig_getmethods__["initType"] = _wazlibs.WAProviderPluginProcess_initType_get
    if _newclass:initType = _swig_property(_wazlibs.WAProviderPluginProcess_initType_get, _wazlibs.WAProviderPluginProcess_initType_set)
    __swig_setmethods__["account"] = _wazlibs.WAProviderPluginProcess_account_set
    __swig_getmethods__["account"] = _wazlibs.WAProviderPluginProcess_account_get
    if _newclass:account = _swig_property(_wazlibs.WAProviderPluginProcess_account_get, _wazlibs.WAProviderPluginProcess_account_set)
    def accountValueAsString(self, *args): return _wazlibs.WAProviderPluginProcess_accountValueAsString(self, *args)
    __swig_setmethods__["accountId"] = _wazlibs.WAProviderPluginProcess_accountId_set
    __swig_getmethods__["accountId"] = _wazlibs.WAProviderPluginProcess_accountId_get
    if _newclass:accountId = _swig_property(_wazlibs.WAProviderPluginProcess_accountId_get, _wazlibs.WAProviderPluginProcess_accountId_set)
    __swig_destroy__ = _wazlibs.delete_WAProviderPluginProcess
    __del__ = lambda self : None;
WAProviderPluginProcess_swigregister = _wazlibs.WAProviderPluginProcess_swigregister
WAProviderPluginProcess_swigregister(WAProviderPluginProcess)

# This file is compatible with both classic and new-style classes.



########NEW FILE########
__FILENAME__ = litestore
'''
Copyright (c) 2012, Tarek Galal <tarek@wazapp.im>

This file is part of Wazapp, an IM application for Meego Harmattan platform that
allows communication with Whatsapp users

Wazapp is free software: you can redistribute it and/or modify it under the 
terms of the GNU General Public License as published by the Free Software 
Foundation, either version 2 of the License, or (at your option) any later 
version.

Wazapp is distributed in the hope that it will be useful, but WITHOUT ANY 
WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS FOR A 
PARTICULAR PURPOSE. See the GNU General Public License for more details.

You should have received a copy of the GNU General Public License along with 
Wazapp. If not, see http://www.gnu.org/licenses/.
'''
from datastore import DataStore;
import sqlite3
import os
import shutil
from Models.contact import Contact;
from Models.message import Message, Groupmessage;
from Models.conversation import *
from Models.mediatype import Mediatype
from Models.media import Media
from constants import WAConstants

from wadebug import SqlDebug


class LiteStore(DataStore):
	db_dir = os.path.expanduser('~/.wazapp');
	
	def __init__(self,current_id):
		self._d = SqlDebug();
		
		self.status = False;
		self.currentId = current_id;
		super(LiteStore,self).__init__(current_id);
		self.db_name = current_id+".db";
		self.db_path = self.get_db_path(current_id);
		
		self.cachedContacts = None;
		
		if not os.path.exists(LiteStore.db_dir):
			os.makedirs(LiteStore.db_dir);

		if not os.path.exists(self.db_path):
			self.status = False;
			#self.conn = sqlite3.connect(self.db_path)
		else:
			self.conn = sqlite3.connect(self.db_path,check_same_thread = False,isolation_level=None)
			self.status = True;
			self.c = self.conn.cursor();
			#self.initModels();
	
	
	def connect(self):
		self.conn = sqlite3.connect(self.db_path,check_same_thread = False,isolation_level=None)
		self.c = self.conn.cursor();
		
	
	def initModels(self):
		self.Contact = Contact();
		self.Contact.setStore(self);
		
		self.Conversation = Conversation();
		self.Conversation.setStore(self);
		
		self.ConversationManager = ConversationManager();
		self.ConversationManager.setStore(self);
		
		self.Groupconversation = Groupconversation();
		self.Groupconversation.setStore(self);
		
		self.GroupconversationsContacts = GroupconversationsContacts();
		self.GroupconversationsContacts.setStore(self);
		
		self.Mediatype = Mediatype();
		self.Mediatype.setStore(self);
		
		
		self.Media = Media()
		self.Media.setStore(self)
		
		self.Message = Message();
		self.Message.setStore(self);
		
		self.Groupmessage = Groupmessage();
		self.Groupmessage.setStore(self);
		
		#self.Groupmedia = Groupmedia()
		#self.Groupmedia.setStore(self)
		
	def get_db_path(self,user_id):
		return LiteStore.db_dir+"/"+self.db_name;

	
	def cacheContacts(self,contacts):
		self.cachedContacts = contacts;
	
	def getCachedContacts(self):
		return self.cachedContacts;
	
	def getContacts(self):
		return self.Contact.fetchAll();
	
	
	def reset(self):
		
		self.db_path = self.get_db_path(self.currentId);
		self.conn = sqlite3.connect(self.db_path,check_same_thread = False,isolation_level=None)
		#shutil.rmtree(LiteStore.db_dir);
		
		
			
		self.c = self.conn.cursor()
		
		self.prepareBase();
		self.prepareGroupConversations();
		
		self.status = True;
		#self.initModels();
		
	
	
	def tableExists(self,tableName):
		c = self.conn.cursor()
		q = "SELECT name FROM sqlite_master WHERE type='table' AND name='%s'" % tableName;
		c.execute(q);
		return len(c.fetchall())
	
	def columnExists(self,tableName,columnName):
		q = "PRAGMA table_info(%s)"%tableName
		c = self.conn.cursor()
		c.execute(q)
		
		for item in c.fetchall():
			if item[1] == columnName:
				return True
		
		return False
		
	def updateDatabase(self):
		
		
		
		##>0.2.6 check that singleconversations is renamed to conversations
		
		self._d.d("Checking > 0.2.6 updates")
		
		if not self.tableExists("conversations"):
			self._d.d("Renaming single conversations to conversations")
			
			q = "ALTER TABLE singleconversations RENAME TO conversations;"
			c = self.conn.cursor()
			c.execute(q);
			
			#q = "PRAGMA writable_schema = 1";
			#UPDATE SQLITE_MASTER SET SQL = 'CREATE TABLE BOOKS ( title TEXT NOT NULL, publication_date TEXT)' WHERE NAME = 'BOOKS';
			#q = "PRAGMA writable_schema = 0";
		
		self._d.d("Checking addition of media_id and created columns in messages")
		
		q = "PRAGMA table_info(messages)"
		c = self.conn.cursor()
		c.execute(q)
		
		media_id = self.columnExists("messages","media_id");
		created = self.columnExists("messages","created");
		pushname = self.columnExists("contacts","pushname");
		pictureid = self.columnExists("contacts","pictureid");
		iscontact = self.columnExists("contacts","iscontact");
		mediaSize = self.columnExists("media", "size");
		
		if not media_id:
			self._d.d("media_id Not found, altering table")
			c.execute("Alter TABLE messages add column 'media_id' INTEGER")
		
		if not created:
			self._d.d("created Not found, altering table")
			c.execute("Alter TABLE messages add column 'created' INTEGER")
			
			self._d.d("Copying data from timestamp to created col")
			c.execute("update messages set created = timestamp")

		if not pushname:
			self._d.d("pushname in contacts Not found, altering table")
			c.execute("Alter TABLE contacts add column 'pushname' TEXT")

		if not pictureid:
			self._d.d("iscontact in contacts Not found, altering table")
			c.execute("Alter TABLE contacts add column 'pictureid' TEXT")

		if not iscontact:
			self._d.d("iscontact in contacts Not found, altering table")
			c.execute("Alter TABLE contacts add column 'iscontact' TEXT")
			
		if not mediaSize:
			self._d.d("size in media not found, altering table")
			c.execute("ALTER TABLE media add column 'size' INTEGER DEFAULT 0")
			
			
		self._d.d("Checking addition of 'new' column to conversation")
		
		newCol = self.columnExists("conversations","new");
		
		if not newCol:
			self._d.d("'new' not found in conversations. Creating")
			c.execute("ALTER TABLE conversations add column 'new' INTEGER NOT NULL DEFAULT 0")
			
		

	def prepareBase(self):
		contacts_q = 'CREATE  TABLE "main"."contacts" ("id" INTEGER PRIMARY KEY  AUTOINCREMENT  NOT NULL , "number" VARCHAR NOT NULL  UNIQUE , "jid" VARCHAR NOT NULL, "last_seen_on" DATETIME, "status" VARCHAR, "pushname" TEXT, "pictureid" TEXT, "iscontact" TEXT)'
		
		
		messages_q = 'CREATE  TABLE "main"."messages" ("id" INTEGER PRIMARY KEY  AUTOINCREMENT  NOT NULL , "conversation_id" INTEGER NOT NULL, "timestamp" INTEGER NOT NULL, "status" INTEGER NOT NULL DEFAULT 0, "content" TEXT NOT NULL,"key" VARCHAR NOT NULL,"type" INTEGER NOT NULL DEFAULT 0,"media_id" INTEGER,"created" INTEGER NOT NULL DEFAULT CURRENT_TIMESTAMP)'
		
		conversations_q = 'CREATE TABLE "main"."conversations" ("id" INTEGER PRIMARY KEY AUTOINCREMENT NOT NULL,"contact_id" INTEGER NOT NULL, "created" DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP)'
		
		self.c.execute(contacts_q);
		self.c.execute(messages_q);
		self.c.execute(conversations_q);
		self.conn.commit()

	def prepareGroupConversations(self):
		
		groupmessages_q = 'CREATE TABLE IF NOT EXISTS "main"."groupmessages" ("id" INTEGER PRIMARY KEY  AUTOINCREMENT  NOT NULL , "contact_id" INTEGER NOT NULL, "groupconversation_id" INTEGER NOT NULL,"timestamp" INTEGER NOT NULL, "status" INTEGER NOT NULL DEFAULT 0, "content" TEXT NOT NULL,"key" VARCHAR NOT NULL,"media_id" INTEGER, "type" INTEGER NOT NULL DEFAULT 0,"created" INTEGER NOT NULL DEFAULT CURRENT_TIMESTAMP)'
		
		groupconversations_q = 'CREATE TABLE IF NOT EXISTS "main"."groupconversations" ("id" INTEGER PRIMARY KEY AUTOINCREMENT NOT NULL,"jid" VARCHAR NOT NULL,contact_id INTEGER,"picture" VARCHAR,"subject" VARCHAR, "subject_owner" INTEGER,"subject_timestamp" INTEGER, "created" DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,"new" INTEGER NOT NULL DEFAULT 0)'
		
		groupconversations_contacts_q = 'CREATE TABLE IF NOT EXISTS "main".groupconversations_contacts ("id" INTEGER PRIMARY KEY AUTOINCREMENT NOT NULL,"groupconversation_id" INTEGER NOT NULL,"contact_id" INTEGER NOT NULL)'
		
		c = self.conn.cursor()
		c.execute(groupmessages_q);
		c.execute(groupconversations_q);
		c.execute(groupconversations_contacts_q);
		self.conn.commit()
	
	def prepareMedia(self):
		if not self.tableExists("mediatypes"):
			q = 'CREATE TABLE IF NOT EXISTS "main"."mediatypes" ("id" INTEGER PRIMARY KEY NOT NULL, "type" VARCHAR NOT NULL, "enabled" INTEGER NOT NULL DEFAULT 1)'
		
			
			c = self.conn.cursor()
			c.execute(q);
			self.conn.commit()
			

			c.execute("INSERT INTO mediatypes(id,type,enabled) VALUES (1,'text',1)")
			c.execute("INSERT INTO mediatypes(id,type,enabled) VALUES (2,'image',0)")
			c.execute("INSERT INTO mediatypes(id,type,enabled) VALUES (3,'video',0)")
			c.execute("INSERT INTO mediatypes(id,type,enabled) VALUES (4,'voice',0)")
			c.execute("INSERT INTO mediatypes(id,type,enabled) VALUES (5,'location',0)")
			c.execute("INSERT INTO mediatypes(id,type,enabled) VALUES (6,'vcf',0)")
			
			
			q = 'CREATE TABLE IF NOT EXISTS "main"."media" ("id" INTEGER PRIMARY KEY AUTOINCREMENT NOT NULL, "mediatype_id" INTEGER NOT NULL, "preview" VARCHAR,"remote_url" VARCHAR, "local_path" VARCHAR, transfer_status INTEGER NOT NULL DEFAULT 0, size INTEGER DEFAULT 0)'
			
			c.execute(q)
			
			qgroup = 'CREATE TABLE IF NOT EXISTS "main"."groupmedia" ("id" INTEGER PRIMARY KEY AUTOINCREMENT NOT NULL, "mediatype_id" INTEGER NOT NULL,"preview" VARCHAR, "remote_url" VARCHAR, "local_path" VARCHAR, groupmessage_id INTEGER NOT NULL,transfer_status INTEGER NOT NULL DEFAULT 0, size INTEGER DEFAULT 0)'
			
			#c.execute(qgroup)
			
			self.conn.commit()
		


	def prepareSettings(self):
	
		if not self.tableExists('settingtypes') or not self.tableExists('settings'):
			types = 'CREATE TABLE IF NOT EXISTS "main".settingtypes ("id" INTEGER PRIMARY KEY AUTOINCREMENT NOT NULL, "label" VARCHAR NOT NULL,"description" VARCHAR,"order" INTEGER NOT NULL DEFAULT 999,"visible" INTEGER NOT NULL)'
		
			settings = 'CREATE TABLE IF NOT EXISTS "settings" ("id" INTEGER PRIMARY KEY AUTOINCREMENT NOT NULL,"settingtype_id" INTEGER NOT NULL,"label" VARCHAR NOT NULL, "description" VARCHAR, "selector" VARCHAR NOT NULL,"order" INTEGER NOT NULL DEFAULT 999,"visible" INTEGER NOT NULL DEFAULT 1, "value" VARCHAR)'
		
			selector_unique = "CREATE UNIQUE INDEX IF NOT EXISTS SettingSelector ON settings (selector)"
			
			c = self.conn.cursor()
			c.execute(types);
			c.execute(settings);
			c.execute(selector_unique);
			self.conn.commit()
			
			####Define Basic Settings####
			#group notifications
				#tone
				#vibra
			#message notifications
				#tone
				#vibra
			#Conversation settings
				#enter is send
				#conversation sounds
	

########NEW FILE########
__FILENAME__ = messagestore
# -*- coding: utf-8 -*-
'''
Copyright (c) 2012, Tarek Galal <tarek@wazapp.im>

This file is part of Wazapp, an IM application for Meego Harmattan platform that
allows communication with Whatsapp users

Wazapp is free software: you can redistribute it and/or modify it under the 
terms of the GNU General Public License as published by the Free Software 
Foundation, either version 2 of the License, or (at your option) any later 
version.

Wazapp is distributed in the hope that it will be useful, but WITHOUT ANY 
WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS FOR A 
PARTICULAR PURPOSE. See the GNU General Public License for more details.

You should have received a copy of the GNU General Public License along with 
Wazapp. If not, see http://www.gnu.org/licenses/.
'''
from PySide import QtCore
from PySide.QtCore import QObject
from PySide.QtGui import QImage
import time
import datetime
from wadebug import MessageStoreDebug
import os
from constants import WAConstants
import dbus

class MessageStore(QObject):


	messageStatusUpdated = QtCore.Signal(str,int,int);
	messagesReady = QtCore.Signal(dict,bool);
	conversationReady = QtCore.Signal(dict);
	conversationExported = QtCore.Signal(str, str); #jid, exportePath
	conversationMedia = QtCore.Signal(list);
	conversationGroups = QtCore.Signal(list);
	
	currKeyId = 0

	def __init__(self,dbstore):
	
		_d = MessageStoreDebug();
		self._d = _d.d;
		super(MessageStore,self).__init__();
		
		self.store = dbstore
		self.conversations = {}
		#get unique contactId from messages
		#messages = self.store.Message.findAll(fields=["DISTINCT contact_id"])
		#for m in messages:
		#	self.loadMessages(m.getContact());
		#load messages for jids of those ids
		
	
	def onConversationOpened(self,jid):
		if not self.conversations.has_key(jid):
			return
			
		conv = self.conversations[jid]
		conv.clearNew();
	
	def deleteConversation(self,jid):
	
		if not self.conversations.has_key(jid):
			return
		
		conv = self.conversations[jid]
		
		if conv.type == "single":
			self.store.Message.delete({"conversation_id":conv.id})
		else:
			self.store.Groupmessage.delete({"groupconversation_id":conv.id})
		conv.delete();
		del self.conversations[jid]

	

	def deleteMessage(self,jid,msgid):

		if not self.conversations.has_key(jid):
			return
		
		conv = self.conversations[jid]
		
		if conv.type == "single":
			self.store.Message.delete({"conversation_id":conv.id, "id":msgid})
		else:
			self.store.Groupmessage.delete({"groupconversation_id":conv.id, "id":msgid})


	def removeSingleContact(self, jid):
		self._d("Removing contact: "+jid);


	def exportConversation(self, jid):
		self._d("Exporting conversations")
		bus = dbus.SessionBus()
		exportDir = WAConstants.CACHE_CONV

		if not os.path.exists(exportDir):
			os.makedirs(exportDir)
			
		conv = self.getOrCreateConversationByJid(jid)
		conv.loadMessages(offset=0, limit=0)
		
		cachedContacts = self.store.getCachedContacts()
		
		contacts = {}
		
		if not conv.isGroup():
			contact = conv.getContact()
			try:
				contacts[contact.id] = cachedContacts[contact.number].name or contact.number
			except:
				contacts[contact.id] = contact.number
				
		else:
			contacts = conv.getContacts()
			for c in contacts:
				try:
					contacts[c.id] = cachedContacts[c.number].name or c.number
				except:
					contacts[c.id] = c.number
		
		fileName = "WhatsApp chat with %s"%(contacts[contact.id])
		exportPath = "%s/%s.txt"%(exportDir, fileName.encode('utf-8'))
		item = "file://"+exportPath
		
		buf = ""

		for m in conv.messages:
			if not conv.isGroup():
				if m.type == m.TYPE_SENT and m.status != m.STATUS_DELIVERED:
					continue
			
			
			tx = int(m.timestamp)/1000 if len(str(m.timestamp)) > 10 else int(m.timestamp)
			t = datetime.datetime.fromtimestamp(tx).strftime('%d-%m-%Y %H:%M')
			author = contacts[m.contact_id] if conv.isGroup() else (contacts[conv.contact_id] if m.type == m.TYPE_RECEIVED else "You")
			content = m.content if not m.media_id else "[media omitted]"
			try:
				authorClean = author.encode('utf-8','replace') #how it's working for you?
			except UnicodeDecodeError:
#				authorClean = "".join(i for i in author if ord(i)<128) #and why this?
				authorClean = author #working great for all cases
			try:
				contentClean = content.encode('utf-8','replace') #same again
			except UnicodeDecodeError:
#				contentClean = "".join(i for i in content if ord(i)<128) #same again
				contentClean = content #same again
			buf+="[%s]%s: %s\n"%(str(t),authorClean,contentClean)

		f = open(exportPath, 'w')		
		f.write(buf)
		f.close()
			
		trackerService = bus.get_object('org.freedesktop.Tracker1.Miner.Files.Index','/org/freedesktop/Tracker1/Miner/Files/Index')
		addFile = trackerService.get_dbus_method('IndexFile','org.freedesktop.Tracker1.Miner.Files.Index')
		addFile(item)
		time.sleep(1) #the most stupid line I ever wrote in my life but it must be here because of the sluggish tracker
		shareService = bus.get_object('com.nokia.ShareUi', '/')
		share = shareService.get_dbus_method('share', 'com.nokia.maemo.meegotouch.ShareUiInterface')
		share([item,])		
			
			
	def getConversationMedia(self,jid):
		tmp = []
		media = []
		gMedia = []

		conversation = self.getOrCreateConversationByJid(jid)

		messages = self.store.Message.findAll({"conversation_id":conversation.id,"NOT media_id":0})
		for m in messages:
			media.append(m.getMedia())

		if media:
			for ind in media:
				if ind.transfer_status == 2:
					tmp.append(ind.getModelData());

		gMessages = self.store.Groupmessage.findAll({"contact_id":conversation.contact_id,"NOT media_id":0})
		for m in gMessages:
			gMedia.append(m.getMedia())

		if gMedia:
			for gind in gMedia:
				if gind.transfer_status == 2:
					tmp.append(gind.getModelData());

		self.conversationMedia.emit(tmp)

	def getConversationGroups(self,jid):

		contact = self.store.Contact.getOrCreateContactByJid(jid)
		groups = self.store.GroupconversationsContacts.findGroups(contact.id)
		cachedContacts = self.store.getCachedContacts()
		
		tmp = []
		
		for group in groups:
			if group.jid is None:
				continue
			groupInfo = {}
			groupInfo["jid"] = str(group.jid)
			jname = group.jid.replace("@g.us","")
			groupInfo["pic"] = WAConstants.CACHE_CONTACTS+"/"+jname+".png" if os.path.isfile(WAConstants.CACHE_CONTACTS+"/"+jname+".png") else WAConstants.DEFAULT_GROUP_PICTURE
			groupInfo["subject"] = str(group.subject)
			groupInfo["contacts"] = ""
			
			contacts = group.getContacts()
			resultContacts = []
			for c in contacts:
				try:
					contact = cachedContacts[c.number].name or c.number
				except:
					contact = c.number
				resultContacts.append(contact.encode('utf-8'))
				
			groupInfo["contacts"] = resultContacts
			
			tmp.append(groupInfo)

		self.conversationGroups.emit(tmp)
	
	def loadConversations(self):
		conversations = self.store.ConversationManager.findAll();
		self._d("init load convs")
		convList = []
		for c in conversations:
			self._d("loading messages")
			jid = c.getJid();
			c.loadMessages();
			
			if self.conversations.has_key(jid) and len(self.conversations[jid].messages) > 0:
				self._d("Duplicate convs in DB for %s!!"%jid)
				continue

			self.conversations[jid] = c

			if len(c.messages) > 0:
				convList.append({"jid":jid,"message":c.messages[0],"lastdate":c.messages[0].created})

		convList = sorted(convList, key=lambda k: k['lastdate']);
		convList.reverse();

		for ci in convList:
			messages = []
			self.sendConversationReady(ci['jid']);
			messages.append(ci['message']);
			self.sendMessagesReady(ci['jid'],messages,False);

			#elif len(c.messages) == 0:
			#	self.deleteConversation(jid)
		

	def loadMessages(self,jid,offset=0, limit=1):
	
		self._d("Load more messages requested");
		
		messages = self.conversations[jid].loadMessages(offset,limit);
		
		self.sendMessagesReady(jid,messages,False);
		return messages
	
	
	def sendConversationReady(self,jid):
		#self._d("SENDING CONV READY %s"%jid)
		'''
			jid,subject,id,contacts..etc
			messages
		'''
		c = self.conversations[jid];
		tmp = c.getModelData();
		#self._d(tmp)
		tmp["isGroup"] = c.isGroup()
		tmp["jid"]=c.getJid();
		picturePath =  WAConstants.CACHE_CONTACTS + "/" + jid.split('@')[0] + ".png"
		tmp["picture"] = picturePath if os.path.isfile(picturePath) else None
		#self._d("Checking if group")
		if c.isGroup():
			#self._d("yes, fetching contacts")
			contacts = c.getContacts();
			tmp["contacts"] = []
			for contact in contacts:
				#self._d(contact.getModelData())
				tmp["contacts"].append(contact.getModelData());
		
		#self._d("emitting ready ")
		self.conversationReady.emit(tmp);
	
	def sendMessagesReady(self,jid,messages,reorder=True):
		if not len(messages):
			return
			
		tmp = {}
		tmp["conversation_id"] = self.conversations[jid].id
		tmp["jid"] = jid
		tmp["data"] = []
		tmp['conversation'] = self.conversations[jid].getModelData();
		tmp['conversation']['unreadCount'] = tmp['conversation']['new']
		
		foreignKeyField = "conversation_id" if self.conversations[jid].type=="single" else "groupconversation_id";
		tmp['conversation']['remainingMessagesCount'] = messages[0].findCount({"id<":self.conversations[jid].messages[0].id,foreignKeyField:self.conversations[jid].id})
		
		for m in messages:
			msg = m.getModelData()
			t = int(msg['timestamp'])/1000 if len(str(msg['timestamp'])) > 10 else int(msg['timestamp']) #keeping backwards compatibility
			msg['formattedDate'] = datetime.datetime.fromtimestamp(t).strftime('%d-%m-%Y %H:%M')
			try:
				undecoded = msg['content'].decode('utf-8'); #maybe usless?
			except:
				undecoded = msg['content']
			undecoded = undecoded.replace("&","&amp;")
			undecoded = undecoded.replace("<","&lt;")
			undecoded = undecoded.replace(">","&gt;")
			undecoded = undecoded.replace("\n","<br />")
			msg['content'] = undecoded
			msg['jid'] = jid
			msg['contact'] = m.getContact().getModelData()
			msg['pushname'] = msg['contact']['pushname']
			media = m.getMedia()
			msg['media']= media.getModelData() if media is not None else None
			msg['msg_id'] = msg['id']
			tmp["data"].append(msg)
			
		self.messagesReady.emit(tmp,reorder);
			
	
	
	def getUnsent(self):
		messages = self.store.Message.findAll(conditions={"status":self.store.Message.STATUS_PENDING,"type":self.store.Message.TYPE_SENT},order=["id ASC"]);
		
		
		groupMessages = self.store.Groupmessage.findAll(conditions={"status":self.store.Message.STATUS_PENDING,"type":self.store.Message.TYPE_SENT},order=["id ASC"]);
		
		
		
		messages.extend(groupMessages);
		
		return messages	
		
	
	def get(self,key):
		
		try:
			key.remote_jid.index('-')
			return self.store.Groupmessage.findFirst({"key":key.toString()});
			
		except ValueError:
			return self.store.Message.findFirst({"key":key.toString()});
		
	def getG(self,key):
		return self.store.Groupmessage.findFirst({"key":key});
		
	def getOrCreateConversationByJid(self,jid):
		
		if self.conversations.has_key(jid):
			return self.conversations[jid];
		
		groupTest = jid.split('-');
		if len(groupTest)==2:
			conv = self.store.Groupconversation.findFirst(conditions={"jid":jid})
			
			if conv is None:
				conv = self.store.Groupconversation.create()
				conv.setData({"jid":jid})
				conv.save()
			
		else:
			contact = self.store.Contact.getOrCreateContactByJid(jid)
			conv = self.store.Conversation.findFirst(conditions={"contact_id":contact.id})
		
			if conv is None:
				conv = self.store.Conversation.create()
				conv.setData({"contact_id":contact.id})
				conv.save()
		
		return conv
	
	def generateKey(self,message):
		
		conv = message.getConversation();
		jid = conv.getJid();
		
		#key = str(int(time.time()))+"-"+MessageStore.currId;
		localKey = Key(jid,True,str(int(time.time()))+"-"+str(MessageStore.currKeyId))
		
		while self.get(localKey) is not None:
			MessageStore.currKeyId += 1
			localKey = Key(jid,True,str(int(time.time()))+"-"+str(MessageStore.currKeyId))
			
		#message.key = localKey
		
		return localKey;
	
	def updateStatus(self,message,status):
		self._d("UPDATING STATUS TO "+str(status));
		message.status = status
		message.save()
		conversation = message.getConversation()
		
		jid = conversation.getJid();
		
		index = self.getMessageIndex(jid,message.id);
		
		if index >= 0:
			#message is loaded
			self.conversations[jid].messages[index] = message
			self.messageStatusUpdated.emit(jid,message.id,status)
	
	def getMessageIndex(self,jid,msg_id):
		if self.conversations.has_key(jid):
			messages = self.conversations[jid].messages;
			for i in range(0,len(messages)):
				if msg_id == messages[i].id:
					return i
		
		return -1
	
	
	def isGroupJid(self,jid):
		try:
			jid.index('-')
			return True
		except:
			return False
	
	def createMessage(self,jid = None):
		'''
		Message creator. If given a jid, it detects the message type (normal/group) and allocates a conversation for it.
				 Otherwise, returns a normal message
		'''
		if jid is not None:
			conversation =  self.getOrCreateConversationByJid(jid);
			if self.isGroupJid(jid):
				msg = self.store.Groupmessage.create()
				msg.groupconversation_id = conversation.id
				msg.Groupconversation = conversation
				
				
			else:
				msg = self.store.Message.create()
				msg.conversation_id = conversation.id
				msg.Conversation = conversation
		else:
			msg = self.store.Message.create()
		
		return msg
		

	def pushMessage(self,jid,message,signal=True):
		
		conversationLoaded = self.conversations.has_key(jid);
		
		conversation = self.getOrCreateConversationByJid(jid);
		message.setConversation(conversation)
		
		if message.key is None:
			message.key = self.generateKey(message).toString();
		#check not duplicate
		#if not self.store.Message.findFirst({"key",message.key}):
		
		if message.Media is not None and message.Media.mediatype_id:
			#message.Media.setMessageId(message.id)
			message.Media.save()
			message.media_id = message.Media.id
			
		message.save();
	
		self.conversations[jid] = conversation #to rebind new unread counts
		self.conversations[jid].messages.append(message)
	
		if signal:
			if not conversationLoaded:
				self.sendConversationReady(jid)
		
			self.sendMessagesReady(jid,[message]);
			
			
	def updateGroupInfo(self,jid,ownerJid,subject,subjectOwnerJid,subjectT,creation):
		
		conversation = self.getOrCreateConversationByJid(jid);
		
		owner = self.store.Contact.getOrCreateContactByJid(ownerJid)
		subjectOwner = self.store.Contact.getOrCreateContactByJid(subjectOwnerJid)
		
		conversation.contact_id = owner.id
		conversation.subject = subject
		conversation.subject_owner = subjectOwner.id
		conversation.subject_timestamp = subjectT
		conversation.created = creation
		
		conversation.save()
		
		self.conversations[jid] = conversation;
		self.sendConversationReady(jid)


	def messageExists(self, jid, msgId):
		k = Key(jid, False, msgId)
		return self.get(k) is not None

	def keyExists(self, k):
		return self.get(k) is not None
		
		
		
class Key():
	def __init__(self,remote_jid, from_me,idd):
		self.remote_jid = remote_jid;
		self.from_me = from_me;
		self.id = idd;

	def toString(self):
		return "Key(idd=\"" + self.id + "\", from_me=" + str(self.from_me) + ", remote_jid=\"" + self.remote_jid + "\")";
		

########NEW FILE########
__FILENAME__ = mnotification
# -*- coding: utf-8 -*-
'''
Copyright (c) 2012, Tarek Galal <tarek@wazapp.im>

This file is part of Wazapp, an IM application for Meego Harmattan platform that
allows communication with Whatsapp users

Wazapp is free software: you can redistribute it and/or modify it under the 
terms of the GNU General Public License as published by the Free Software 
Foundation, either version 2 of the License, or (at your option) any later 
version.

Wazapp is distributed in the hope that it will be useful, but WITHOUT ANY 
WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS FOR A 
PARTICULAR PURPOSE. See the GNU General Public License for more details.

You should have received a copy of the GNU General Public License along with 
Wazapp. If not, see http://www.gnu.org/licenses/.
'''
# -*- coding: utf-8 -*-

'''
Copyright (c) 2012, Tarek Galal <tare2.galal@gmail.com>

This file is part of python-notifications, a library that allows you to post 
notifications on Harmattan platform

python-notifications is free software: you can redistribute it and/or modify it 
under the terms of the GNU Lesser General Public License as published by the 
Free Software Foundation, either version 3 of the License, or (at your option) 
any later version.

python-notifications is distributed in the hope that it will be useful, but WITHOUT ANY 
WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS FOR 
A PARTICULAR PURPOSE. See the GNU Lesser General Public License for more 
details.

You should have received a copy of the GNU General Public License along with 
python-notifications. If not, see http://www.gnu.org/licenses/.
'''

'''
This file is a derivative of Python Event Feed library by Thomas Perl 
Copyright (c) 2011, Thomas Perl <m@thp.io>

Permission to use, copy, modify, and/or distribute this software for any
purpose with or without fee is hereby granted, provided that the above
copyright notice and this permission notice appear in all copies.
'''

# Dependency on PySide for encoding/decoding like MRemoteAction
from PySide.QtCore import QBuffer, QIODevice, QDataStream, QByteArray
from PySide.QtCore import QCoreApplication


# Python D-Bus Library dependency for communcating with the service
import dbus
import dbus.service
import dbus.mainloop
import dbus.glib
import sys,os

# MRemoteAction::toString()
# http://apidocs.meego.com/1.0/mtf/mremoteaction_8cpp_source.html
def qvariant_encode(value):
    buffer = QBuffer()
    buffer.open(QIODevice.ReadWrite)
    stream = QDataStream(buffer)
    stream.writeQVariant(value)
    buffer.close()
    return buffer.buffer().toBase64().data().strip()

# MRemoteAction::fromString()
# http://apidocs.meego.com/1.0/mtf/mremoteaction_8cpp_source.html
def qvariant_decode(data):
    byteArray = QByteArray.fromBase64(data)
    buffer = QBuffer(byteArray)
    buffer.open(QIODevice.ReadOnly)
    stream = QDataStream(buffer)
    result = stream.readQVariant()
    buffer.close()
    return result
    
    
class MNotificationManager(dbus.service.Object):
	INTERFACE="com.meego.core.MNotificationManager"
	PATH="/notificationmanager"
	
	
	DEFAULT_NAME = 'com.tgalal.meego.MNotificationManager'
	DEFAULT_PATH = '/MNotificationManager'
	DEFAULT_INTF = 'com.tgalal.meego.MNotificationManager'
	
	def __init__(self,source_name, source_display_name, on_data_received=None):
		dbus_main_loop = dbus.glib.DBusGMainLoop(set_as_default=True)
		session_bus = dbus.SessionBus(dbus_main_loop)
		self.userId = 0#os.geteuid();
		
		self.local_name = '.'.join([self.DEFAULT_NAME, source_name])
		print  self.local_name
		bus_name = dbus.service.BusName(self.local_name, bus=session_bus)

		dbus.service.Object.__init__(self,object_path=self.DEFAULT_PATH,bus_name=bus_name)
		
		
		
		self.next_action_id = 1
		self.actions = {}
		self.source_name = source_name
		self.source_display_name = source_display_name
		self.on_data_received = on_data_received
		
		o = session_bus.get_object(self.INTERFACE, self.PATH)
		self.proxy = dbus.Interface(o, self.INTERFACE)
		
		self.userId = self.proxy.notificationUserId()
	
	def notificationList(self):
		return self.proxy.notificationList(self.userId)
		
	def notificationIdList(self):
		return self.proxy.notificationIdList(self.userId)
		
	def notificationGroupList(self):
		return self.proxy.notificationGroupList(self.userId)
	
	
	@dbus.service.method(DEFAULT_INTF)
	def ReceiveActionCallback(self, action_id):
	
		action_id = int(action_id)
		callable = self.actions[action_id]
		callable()

	@dbus.service.method(DEFAULT_INTF)
	def ReceiveActionData(self, *args):
		print 'Received data:'
		if self.on_data_received is not None:
		    self.on_data_received(*args)
		
	def addNotification(self, groupId, eventType, summary, body, action, imageURI, count):
		
		data = {}
		data["eventType"]=eventType;
		data["summary"] = summary;
		data["body"] = body;
		#data["action"] = action;
		if imageURI is not None:
			data["imageId"]=imageURI;
		data["count"]=count;
		
		
		if action is not None:
		    remote_action = [
		            self.local_name,
		            self.DEFAULT_PATH,
		            self.DEFAULT_INTF,
		    ]

		    if action is not None:
		        action_id = self.next_action_id
		        self.next_action_id += 1
		        self.actions[action_id] = action
		        remote_action.extend([
		            'ReceiveActionCallback',
		            qvariant_encode(action_id),
		        ])
		    else: # action_data is not None
		    	print "IN ELSE"
		        remote_action.append('ReceiveActionData')
		        remote_action.extend([qvariant_encode(x) for x in action_data])

		    data['action'] = ' '.join(remote_action)

        	
		return self.proxy.addNotification(self.userId, groupId,data);
	
	#def notifications(self):

	
	def addNonVisualNotification(self,groupId, eventType):
		return self.proxy.addNotification(self.userId,groupId,{'eventType':eventType});
		
	def updateNotification(self, notificationId, eventType, summary, body, action ,imageURI, count):
		data = {}
		data["eventType"]=eventType;
		data["summary"] = summary;
		data["body"] = body;
		
		
		if action is not None:
		    remote_action = [
		            self.local_name,
		            self.DEFAULT_PATH,
		            self.DEFAULT_INTF,
		    ]

		    if action is not None:
		        action_id = self.next_action_id
		        self.next_action_id += 1
		        self.actions[action_id] = action
		        remote_action.extend([
		            'ReceiveActionCallback',
		            qvariant_encode(action_id),
		        ])
		    else: # action_data is not None
		    	print "IN ELSE"
		        remote_action.append('ReceiveActionData')
		        remote_action.extend([qvariant_encode(x) for x in action_data])

		    data['action'] = ' '.join(remote_action)
		
		
		if imageURI is not None:
			data["imageId"]=imageURI;
		
		data["count"]=count;
		
		return self.proxy.updateNotification(self.userId,notificationId, data);
		
	def updateNonVisualNotification(self,notificationId, eventType):
		return self.proxy.addNotification(self.userId,notificationId,{'eventType':eventType});
		
	
	def removeNotification(self,notificationId):
		return self.proxy.removeNotification(self.userId, notificationId);	
		
		
	def addGroup(self, eventType, summary, body, action, imageURI, count):
		
		data = {}
		data["eventType"]=eventType;
		data["summary"] = summary;
		data["body"] = body;
		data["action"] = action;
		data["imageURI"]=imageURI;
		data["count"]=count;
	
		return self.proxy.addGroup(self.userId,data);
	
	def addNonVisualGroup(self, eventType):
		return self.proxy.addNotification(self.userId,{'eventType':eventType});
		
		
	def updateGroup(self, groupId, eventType, summary, body, action ,imageURI, count):
		data = {}
		data["eventType"]=eventType;
		data["summary"] = summary;
		data["body"] = body;
		data["action"] = action;
		data["imageURI"]=imageURI;
		data["count"]=count;
		
		return self.proxy.updateNotification(self.userId,groupId, data);
		
	def updateNonVisualGroup(self,notificationId, eventType):
		return self.proxy.addNotification(self.userId,groupId,{'eventType':eventType});
		
	
	
	def removeGroup(self,groupId):
		return self.proxy.removeGroup(self.userId, groupId);


class MNotification():
	
	DeviceEvent = "device";
	DeviceAddedEvent = "device.added";
	DeviceErrorEvent = "device.error";
	DeviceRemovedEvent = "device.removed";
	EmailEvent = "email";
	EmailArrivedEvent = "email.arrived";
	EmailBouncedEvent = "email.bounced";
	ImEvent = "im";
	ImErrorEvent = "im.error";
	ImReceivedEvent = "im.received";
	NetworkEvent = "network";
	NetworkConnectedEvent = "network.connected";
	NetworkDisconnectedEvent = "network.disconnected";
	NetworkErrorEvent = "network.error";
	PresenceEvent = "presence";
	PresenceOfflineEvent = "presence.offline";
	PresenceOnlineEvent = "presence.online";
	TransferEvent = "transfer";
	TransferCompleteEvent = "transfer.complete";
	TransferErrorEvent = "transfer.error";
	MessageEvent = "x-nokia.message";
	MessageArrivedEvent = "x-nokia.message.arrived";
	
	
	def __init__(self, eventType, summary="",body=""):
	
		self.image = "";
		self.action = "";
		self.count = 1;
		self.id = 0; 
		self.groupId = 0;
		
		
	
		self.eventType = eventType;
		self.summary = summary;
		self.body = body;
		
		
	def id_(self):
		return self.id;
		
	def isPublished(self):
		return self.id != 0;
		
	def setEventType(self,eventType):
		self.eventType
	
	def setGroup(self,group):
		self.groupId = group.id_();
	
	def eventType(self):
		return self.eventType;
	
	def setSummary(self,summary):
		self.summary = summary;
	
	def setBody(self,body):
		self.body = body;
	
	def body(self):
		return self.body;
	
	def setImage(self,image):
		self.image = image;
	
	def image(self):
		return self.image;
	
	#MRemoteAction
	def setAction(self,action):
		self.action = action;
	
	def setCount(self,count):
		self.count = count;
	
	
	
	def remove(self):
		success = False;
		
		if isPublished():
			n_id = self.id;
			self.id = 0;
			success = self.manager.removeNotification(n_id);
		
		return success;
	
	
	def notifications(self):
		return self.manager.notificationList();	
	
	def publish(self):
		success = False;
		
		if self.id == 0:
			if self.summary != "" or self.body !="" or self.image !="" or self.action !="":
				self.id = self.manager.addNotification(self.groupId,self.eventType,self.summary,self.body,self.action,self.image,self.count);
			else:
				self.id = self.manager.addNonVisualNotification(self.groupId, self.eventType);
			
			success = self.id !=0;
		else:
			if self.summary !="" or self.body !="" or self.image !="" or self.action !="":
				success = self.manager.updateNotification(self.id,self.eventType,self.summary,self.body,self.action,self.image,self.count);
			else:
				success = self.manager.updateNonVisualNotification(self.id,self.eventType);

		return success;
	 

class MNotificationGroup(MNotification):

	
	def publish(self):
		success = False;
		
		if self.id == 0:
			if self.summary != "" or self.body !="" or self.image !="" or self.action !="":
				self.id = self.manager.addGroup(self.eventType,self.summary,self.body,self.action,self.image,self.count);
			else:
				self.id = self.manager.addNonVisualGroup(self.eventType);
			
			success = self.id !=0;
		else:
			if self.summary !="" or self.body !="" or self.image !="" or self.action !="":
				success = self.manager.updateGroup(self.id,self.eventType,self.summary,self.body,self.action,self.image,self.count);
			else:
				success = self.manager.updateNonVisualGroup(self.id,self.eventType);

		return success;
		
	def remove(self):
		if not self.isPublished():
			return False;
		else:
			g_id = self.id;
			self.id = 0;
			return self.manager.removeGroup(g_id);
	

	

def sayHello():
	print "HELLOOOOOO"


def on_data_received(*args):
    print 'CLIENT received DATA:', args



if __name__ == "__main__":
	
	app = QCoreApplication(sys.argv)
	manager = MNotificationManager('wazapp_notify','Wazapp Notify');
	
	
	
	#group = MNotificationGroup(MNotification.ImReceivedEvent,"Message from Reem","tikoooooooooooo");
	#group.manager = manager;
	#group.setImage('/usr/share/icons/hicolor/80x80/apps/waxmppplugin80.png');
	#print group.publish();
	
	
	n = MNotification(MNotification.MessageArrivedEvent,"Reem", "Ezayak?");
	n.manager = manager;
	#n.setAction(sayHello);
	n.setImage('/usr/share/icons/hicolor/80x80/apps/waxmppplugin80.png');
	#n.setGroup(group);
	res = n.publish();
	print res;
	'''
	n.setSummary("CHANGED");
	print n.publish();
	'''
	#n.addNotification(0,MNotification.ImReceivedEvent,"THIS IS SUMMARY", "THIS IS BODY", "NONE", "NONE", 1);
		
	app.exec_()		



########NEW FILE########
__FILENAME__ = account
'''
Copyright (c) 2012, Tarek Galal <tarek@wazapp.im>

This file is part of Wazapp, an IM application for Meego Harmattan platform that
allows communication with Whatsapp users

Wazapp is free software: you can redistribute it and/or modify it under the 
terms of the GNU General Public License as published by the Free Software 
Foundation, either version 2 of the License, or (at your option) any later 
version.

Wazapp is distributed in the hope that it will be useful, but WITHOUT ANY 
WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS FOR A 
PARTICULAR PURPOSE. See the GNU General Public License for more details.

You should have received a copy of the GNU General Public License along with 
Wazapp. If not, see http://www.gnu.org/licenses/.
'''
class Account():
	def __init__(self,cc,phoneNumber,username,status,pushName,imsi,password):
		
		self.pushName = pushName.encode('utf-8')
		self.cc = cc;
		self.phoneNumber = phoneNumber;
		self.jid = username+"@s.whatsapp.net";
		self.username = username;
		self.password = password
		self.imsi = imsi
		self.status = status
		
		
		self.kind = None
		self.expiration = None
		self.cost = None
		self.currency = None
		self.price = None
		self.price_expiration = None
		
		print "ACCOUNT INFO"
		#print pushName
		print cc
		print phoneNumber
		print self.jid
		#print password
		print imsi
		#print status
		print "END ACCNT INFO"

	def setExtraData(self, kind, expiration, cost, currency, price, price_expiration):
		self.kind = kind
		try:
			self.expiration = int(expiration)
		except:
			pass
		self.cost = cost
		self.currency = currency
		self.price = price
		self.price_expiration = price_expiration

	def setAccountInstance(self,instance):
		self.accountInstance = instance
	
	def updateStatus(self,status):
		self.accountInstance.setValue("status",status);
		self.accountInstance.sync()

########NEW FILE########
__FILENAME__ = contact
'''
Copyright (c) 2012, Tarek Galal <tarek@wazapp.im>

This file is part of Wazapp, an IM application for Meego Harmattan platform that
allows communication with Whatsapp users

Wazapp is free software: you can redistribute it and/or modify it under the 
terms of the GNU General Public License as published by the Free Software 
Foundation, either version 2 of the License, or (at your option) any later 
version.

Wazapp is distributed in the hope that it will be useful, but WITHOUT ANY 
WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS FOR A 
PARTICULAR PURPOSE. See the GNU General Public License for more details.

You should have received a copy of the GNU General Public License along with 
Wazapp. If not, see http://www.gnu.org/licenses/.
'''
from model import Model;

class Contact(Model):
	def __init__(self):
		self.name = "";
		self.picture = "none";
		self.alphabet = "";
		self.iscontact = "";
		self.pushname = "";
		self.pictureid = "";
	
	def setRealTimeData(self,name,picture,iscontact):
		if name == '':
			return
		self.name = name;
		self.picture = picture;
		self.alphabet = name[0].upper();
		self.iscontact = iscontact
		self.norender = self.iscontact != "yes"
		
		self.modelData.append("name");
		self.modelData.append("picture");
		self.modelData.append("alphabet");
		self.modelData.append("pictureid");
		self.modelData.append("iscontact");
		self.modelData.append("norender");
		

	def getOrCreateContactByJid(self,jid):
		
		contact = self.findFirst({'jid':jid})
		
		if not contact:
			contact = self.create()
			contact.setData({"jid":jid,"number":jid.split('@')[0],"iscontact":"","pushname":""})
			contact.save()
		
		return contact
			
			
			
			
			
			
			
			
			
			

########NEW FILE########
__FILENAME__ = conversation
'''
Copyright (c) 2012, Tarek Galal <tarek@wazapp.im>

This file is part of Wazapp, an IM application for Meego Harmattan platform that
allows communication with Whatsapp users

Wazapp is free software: you can redistribute it and/or modify it under the 
terms of the GNU General Public License as published by the Free Software 
Foundation, either version 2 of the License, or (at your option) any later 
version.

Wazapp is distributed in the hope that it will be useful, but WITHOUT ANY 
WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS FOR A 
PARTICULAR PURPOSE. See the GNU General Public License for more details.

You should have received a copy of the GNU General Public License along with 
Wazapp. If not, see http://www.gnu.org/licenses/.
'''
from model import Model;

class Conversation(Model):
	#MUST INIT BEFORE INITING MESSAGES
	def __init__(self):
		''''''
		self.type="single"
		self.messages = []
	
	def getContact(self):
		if not self.contact_id:
			return 0
			
		if not self.Contact.id:
			self.Contact = self.Contact.read(self.contact_id);
		
		return self.Contact
		
	def getJid(self):
		if not self.contact_id:
			convObj =  self.store.Conversation.getById(self.id);
			contact = convObj.getContact()
		else:
			contact = self.getContact()
			
		return contact.jid
	
	def clearNew(self):
		self.new = 0;
		self.save();
		
	def incrementNew(self):
		self.new = 1 if self.new is None else self.new+1;
		self.save();
		
		
	def loadMessages(self,offset = 0,limit=1):
		conditions = {"conversation_id":self.id}
		
		if offset:
			conditions["id<"] = offset;
		
		messages = self.store.Message.findAll(conditions,order=["id DESC"],limit=limit) if limit else self.store.Message.findAll(conditions,order=["id DESC"])
		
		messages.reverse();
		
		cpy = messages[:]
		messages.extend(self.messages);
		self.messages = messages
		
		return cpy
		
	def isGroup(self):
		return False;

class Groupconversation(Model):
	
	def __init__(self):
		self.type="group"
		self.messages = []
		self.contacts = []
		
	def isGroup(self):
		return True;
	
	def clearNew(self):
		self.new = 0;
		self.save();
	
	def incrementNew(self):
		self.new = 1 if self.new is None else self.new+1;
		self.save();
	
	def getJid(self):
		return self.jid;
		
	
	def getContacts(self):
		if len(self.contacts):
			return self.contacts
		
		gc = self.store.GroupconversationsContacts
		contacts = gc.findContacts(self.id);
		
		return contacts;

	def getOwner(self):
		if not self.contact_id:
			return 0
		if not self.Contact.id:
			self.Contact = self.Contact.read(self.contact_id);

		return self.Contact
		
	def addContact(self,contactId):
		inter = self.store.GroupconversationsContacts.findAll({"groupconversation_id":self.id,"contact_id":contactId});
		
		if len(inter):
			return;
		
		inter = self.store.GroupconversationsContacts.create();
		inter.groupconversation_id = self.id
		inter.contact_id = contactId
		
		inter.save()
		
	def loadMessages(self,offset = 0,limit=1):
		
		conditions = {"groupconversation_id":self.id}
		
		if offset:
			conditions["id<"] = offset;
		
		messages = self.store.Groupmessage.findAll(conditions,order=["id DESC"],limit=limit)
		
		messages.reverse();
		
		cpy = messages[:]
		messages.extend(self.messages);
		self.messages = messages
		
		return cpy
	

class ConversationManager():
	def __init__(self):
		''''''
	
	def setStore(self,store):
		self.store = store;
	
	def findAll(self):
		convs = self.store.Conversation.findAll();
		gconvs = self.store.Groupconversation.findAll();
		
		convs.extend(gconvs);
		
		#for c in convs:
		#	c.getLastMessage();
		
		
		#convs.sort(key=lambda k: k.lastMessage.timestamp,reverse = True);
		
		return convs;
		
		
		
class GroupconversationsContacts(Model):
	def __init__(self):
		self.table = "groupconversations_contacts"
		
		
	def findContacts(self,groupConversationId):
		inter = self.findAll({"groupconversation_id":groupConversationId});
		contacts = []
		for i in inter:
			contact = i.Contact.read(i.contact_id)
			contacts.append(contact)
		
		return contacts
	
	
	def findGroups(self, contact_id):
		inter = self.findAll({"contact_id":contact_id})
		
		groups = []
		
		for g in inter:
			group = g.Groupconversation.read(g.groupconversation_id)
			groups.append(group)
		
		return groups
		

	
		
		
		
		
		
		
		
		
		
		
		

########NEW FILE########
__FILENAME__ = media
from model import Model;
import os
class Media(Model):
	pass

########NEW FILE########
__FILENAME__ = mediatype
'''
Copyright (c) 2012, Tarek Galal <tarek@wazapp.im>

This file is part of Wazapp, an IM application for Meego Harmattan platform that
allows communication with Whatsapp users

Wazapp is free software: you can redistribute it and/or modify it under the 
terms of the GNU General Public License as published by the Free Software 
Foundation, either version 2 of the License, or (at your option) any later 
version.

Wazapp is distributed in the hope that it will be useful, but WITHOUT ANY 
WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS FOR A 
PARTICULAR PURPOSE. See the GNU General Public License for more details.

You should have received a copy of the GNU General Public License along with 
Wazapp. If not, see http://www.gnu.org/licenses/.
'''

from model import Model;
import os

parentdir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
os.sys.path.insert(0,parentdir)
from constants import WAConstants

class Mediatype(Model):

	TYPE_TEXT	= WAConstants.MEDIA_TYPE_TEXT
	TYPE_IMAGE	= WAConstants.MEDIA_TYPE_IMAGE
	TYPE_AUDIO	= WAConstants.MEDIA_TYPE_AUDIO
	TYPE_VIDEO	= WAConstants.MEDIA_TYPE_VIDEO
	TYPE_LOCATION	= WAConstants.MEDIA_TYPE_LOCATION
	TYPE_VCARD	= WAConstants.MEDIA_TYPE_VCARD
	
	
	
	

########NEW FILE########
__FILENAME__ = message
'''
Copyright (c) 2012, Tarek Galal <tarek@wazapp.im>

This file is part of Wazapp, an IM application for Meego Harmattan platform that
allows communication with Whatsapp users

Wazapp is free software: you can redistribute it and/or modify it under the 
terms of the GNU General Public License as published by the Free Software 
Foundation, either version 2 of the License, or (at your option) any later 
version.

Wazapp is distributed in the hope that it will be useful, but WITHOUT ANY 
WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS FOR A 
PARTICULAR PURPOSE. See the GNU General Public License for more details.

You should have received a copy of the GNU General Public License along with 
Wazapp. If not, see http://www.gnu.org/licenses/.
'''
import time;
from model import Model;
from mediatype import Mediatype

class MessageBase(Model):
	
	TYPE_RECEIVED = 0
	TYPE_SENT = 1
	
	STATUS_PENDING = 0
	STATUS_SENT = 1
	STATUS_DELIVERED = 2
	
	
	generating_id = 0;
	generating_header = str(int(time.time()))+"-";
	
	def __init__(self):
		
		self.TYPE_RECEIVED = Message.TYPE_RECEIVED
		self.TYPE_SENT = Message.TYPE_SENT
		self.STATUS_PENDING = Message.STATUS_PENDING
		self.STATUS_SENT = Message.STATUS_SENT
		self.STATUS_DELIVERED = Message.STATUS_DELIVERED
		self.Media = None
		self.media_id = None

		super(MessageBase,self).__init__();
		
		
	
	def getMedia(self):
		if self.media_id is not None:
			if self.Media.id is not None and self.Media.id != 0:
				return self.Media
			else:
				media = self.store.Media.create()
				self.Media = media.findFirst({"id":self.media_id})
				return self.Media

		return None;
		
		
	def setConversation(self,conversation):
		self.conversation_id = conversation.id
		self.Conversation = conversation
	
	def getConversation(self):
		if not self.conversation_id:
			return 0;
			
		if not self.Conversation.id:
			self.Conversation = self.Conversation.read(self.conversation_id)
		
		return self.Conversation	
		
class Message(MessageBase):

	def storeConnected(self):
		self.Conversation = self.store.Conversation
		self.conn.text_factory = str
			
	def getContact(self):
		conversation = self.getConversation();
		
		if not conversation.Contact.id:
			conversation.Contact = conversation.getContact();
		
		
		return conversation.Contact	
			
class Groupmessage(MessageBase):


	def storeConnected(self):
		self.Conversation = self.store.Groupconversation
		self.conn.text_factory = str
	
	
	def setConversation(self,conversation):
		self.groupconversation_id = conversation.id
		self.Groupconversation = conversation
	
	def setContact(self,contact):
		self.contact_id = contact.id;
		self.Contact = contact
		
	
		
	
	def getConversation(self):
		if not self.groupconversation_id:
			return 0;
			
		if not self.Groupconversation.id:
			self.Groupconversation = self.Groupconversation.read(self.groupconversation_id)
		
		return self.Groupconversation	
	
	def getContact(self):
		if not self.contact_id:
			return 0
			
		if not self.Contact.id:
			self.Contact = self.Contact.read(self.contact_id);
		
		return self.Contact
	

########NEW FILE########
__FILENAME__ = model
'''
Copyright (c) 2012, Tarek Galal <tarek@wazapp.im>

This file is part of Wazapp, an IM application for Meego Harmattan platform that
allows communication with Whatsapp users

Wazapp is free software: you can redistribute it and/or modify it under the 
terms of the GNU General Public License as published by the Free Software 
Foundation, either version 2 of the License, or (at your option) any later 
version.

Wazapp is distributed in the hope that it will be useful, but WITHOUT ANY 
WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS FOR A 
PARTICULAR PURPOSE. See the GNU General Public License for more details.

You should have received a copy of the GNU General Public License along with 
Wazapp. If not, see http://www.gnu.org/licenses/.
'''
import sqlite3
import copy
import time

from wadebug import SqlDebug

class Model(object):

	def setConnection(self,connection):
		_d = SqlDebug();
		self._d = _d.d;
		
		self.table = self.getTableName();
		self.conn = connection
		try:
			self.cursor  = connection.cursor()
		except sqlite3.ProgrammingError as e:
			self._d(e)
			self.store.connect()
			self.conn = self.store.conn
			self.cursor = self.conn.cursor()
			
		#Get table description
		q = "PRAGMA table_info('%s')" % self.table
		res = self.runQuery(q)
		self.columns = [];
		self.modelData = [];
		self.hasManytoMany=[];
		
		for item in res:
			relattrib = str(item[1]).split('_id')
			if len(relattrib) == 2 and relattrib[1]=='':
				
				m2mTest = relattrib[0].split('_')
				if len(m2mTest) == 2:
					foreignOne = m2mTest[0].lower()
					foreignOne = foreignOne[0].upper()+foreignOne[1:]
					foreignTwo = m2mTest[1].lower()
					foreignTwo = foreignTwo[0].upper()+foreignTwo[1:]
					foreign = foreignOne + foreignTwo
					
					#foreignInstance = getattr(self.store,foreignOne)
					#self.setInstanceVariable(foreignOne,foreignInstance.create());
					
					#foreignInstance = getattr(self.store,foreignTwo)
					#self.setInstanceVariable(foreignTwo,foreignInstance.create());
				else:	
					foreign = relattrib[0].lower();
					foreign = foreign[0].upper()+foreign[1:]
				
				foreignInstance = getattr(self.store,foreign)
				self.setInstanceVariable(foreign,foreignInstance.create());
				
			self.setInstanceVariable(str(item[1]));
			self.columns.append(str(item[1]));
			self.modelData.append(str(item[1]));
			
	
			
	def getTableName(self):
		if vars(self).has_key("table"):
			return self.table

		table = self.whoami().lower()
		if table[-2:] == "ia":
			return table
		else:
			return table + "s"
		
		
		
	def storeConnected(self):
		''''''
	
	
	def setStore(self,store):
		self.store = store;
		self.setConnection(store.conn);
		self.storeConnected()

	def save(self):
		if self.id:
			self.update();
		else:
			self.insert();
	
	def _getColumnsWithValues(self):
		data = {};
		for c in self.columns:
			data[c] = vars(self)[c];
		
		return data;
		
		
	def getModelData(self):
		data = {};
		for c in self.modelData:
			data[c] = vars(self)[c];
		
		return data;
				
	def getData(self):
		data = self._getColumnsWithValues();	
		
		if vars(self).has_key('name'):
			data['name'] = vars(self)['name'];
		
		return data;	
	
		
	def read(self,idx):
		self = self.create();
		self.setData(self.getById(idx).getData());
		return self
	
	
	def deleteAll(self):
		q = "DELETE FROM %s "%self.table
		
		c = self.conn.cursor();
		c.execute(q)
		self.conn.commit()
		
	
	def delete(self,conds = None):
		
		q = "DELETE FROM %s "%self.table
			
		if conds is not None:
			q+="WHERE %s"%self.buildConds(conds);
		elif self.id:
			q+="WHERE id=%d"%self.id
		else:
			self._d("USE deleteAll to delete all, cancelled!")
			
		c = self.conn.cursor();
		c.execute(q)
		self.conn.commit()
		

	
	def insert(self):
		data = self._getColumnsWithValues();
		
		fields = [];
		values = [];

		for k,v in data.items():
			if k == "id":
				continue;
			if v is None:
				continue
				
			fields.append(k);
			values.append(v);
		
		wq = ['?' for i in values]
		wq = ','.join(wq);
		wq = "("+wq+")";
		fields = ','.join(fields)
		fields = "("+fields+")";
		
		q = "INSERT INTO %s %s VALUES %s" %(self.table,fields,wq);
		c = self.conn.cursor();
		self._d(q)
		self._d(values)
		c.execute(q,values);
		self.conn.commit();
		
		self.id = c.lastrowid;
	
	def update(self):
		data = self._getColumnsWithValues();
		
		updateData = [];
		updateValues = ()
		for k,v in data.items():
			if k == "id":
				continue;
			updateData.append("%s=?"%(k));
			updateValues+=(v,)
		
		q = "UPDATE %s SET %s WHERE id = %d"%(self.table,','.join(updateData),self.id);
		
		try:
			c  = self.conn.cursor()
		except sqlite3.ProgrammingError as e:
			self.reconnect();
		
		c = self.conn.cursor();
		
		self._d(q);
		self._d(updateValues);
		
		try:
			c.execute(q,updateValues);
			self.conn.commit();
		except:
			'''nothing'''
	
	
	def reconnect(self):
		self.store.connect()
		self.conn = self.store.conn
		self.cursor = self.conn.cursor()	
		
	def getById(self,idx):
		q = "SELECT * FROM %s WHERE id=?" %(self.table);
		c= self.conn.cursor();
		c.execute(q,[idx]);
		return self.createInstance(c.fetchone());
		
	
	
	def createInstance(self,resultItem):
		#modelInstance = copy.deepcopy(self);
		modelInstance = self.create();

		if resultItem is None:
			return modelInstance;
		
		for i in range(0,len(resultItem)):
			modelInstance.setInstanceVariable(self.columns[i],resultItem[i]);
		
			
		return modelInstance;
	
	def fetchAll(self):
		q = "SELECT * FROM %s" % (self.table);
		c = self.conn.cursor();
		c.execute(q)
		data = []
		for item in c.fetchall():
			data.append(self.createInstance(item));
		
		return data
			
	
	
	def create(self):
		c = self.__class__
		instance =  c();
		instance.setStore(self.store);
		return instance;
	
	def setData(self,data):
		for k,v in data.items():
			try:
				self.columns.index(k)
				self.setInstanceVariable(k,v)
			except ValueError:
				continue
	
	def setInstanceVariable(self,variable,value=None):
		#variable = "idx" if variable == "id" else variable
		if value is None:
			if variable == "timestamp":
				value =	int(time.time())
			elif variable == "created":
				value =	int(time.time()*1000)
			
		vars(self)[variable] = value
	
	def findFirst(self,conditions,fields = []):
		res = self.findAll(conditions,fields);
		
		if len (res):
			return res[0];
		
		return None;
	
	
	def getComparator(self,key):
		signs = ['<','>','<=','>=','<>','=']
		signs.sort()
		key = key.strip()
		
		for s in signs:
			try:
				index = key.index(s)
				return s
			except:
				continue
		
		return False
			
	def buildConds(self,conditions):
		q = [];
		for k,v in conditions.items():
			comparator = self.getComparator(k)
			
			if comparator:
				index = k.index(comparator)
				k = k[:index]
			else:
				comparator = '='
				
			if type(v) == list:
			
				tmp = []
				for val in v:
					tmp.append("%s %s '%s'" % (k, comparator, str(val)))
				
				tmpStr = ' OR '.join(tmp)
			
				q.append("(%s)"%(tmpStr))
			else:
				q.append("%s %s '%s'" % (k, comparator, str(v)))
	
		condsStr = " AND ".join(q);
		
		return condsStr;
		
	def findCount(self,conditions=""):
		condsStr = "";
		if type(conditions) == dict:
			condsStr = self.buildConds(conditions);
			
		elif type(conditions) == str:
			condsStr = conditions
		else:
			raise "UNKNOWN COND TYPE "+ type(conditions)
			
		
		query = "SELECT COUNT(*) FROM %s " % (self.table)
		
		if len (condsStr):
			query = query +"WHERE %s" % condsStr;
		
		results = self.runQuery(query);
		
		return results[0][0];
		
	
	def findAll(self, conditions="", fields=[], order=[], first=None, limit=None):

		condsStr = "";
		if type(conditions) == dict:
			condsStr = self.buildConds(conditions);
			
		elif type(conditions) == str:
			condsStr = conditions
		else:
			raise "UNKNOWN COND TYPE "+ type(conditions)
			
		
		
		fieldsStr= "*"
		if len(fields):
			fieldsStr = ",".join(fields)
				
		query = "SELECT %s FROM %s " % (fieldsStr,self.table)
		
		if len (condsStr):
			query = query +"WHERE %s" % condsStr;
			
			
		if len(order):
			query = query+" ORDER BY ";
			orderStr = ",".join(order);
			query = query + orderStr;
		

		if limit is not None and type(limit) == int:
			query=query+" LIMIT %i"%limit


		if first is not None and type(first) == int:
			query=query+" OFFSET %i"%first
		

		results = self.runQuery(query);
		
		data = []
		for r in results:
			data.append(self.createInstance(r));
		return data
		
	def whoami(self):
		return self.__class__.__name__
	
	def runQuery(self,query,whereValues = []):
		self._d(query);
		c = self.conn.cursor();
		
		if len(whereValues):
			c.execute(query,whereValues)
		else:
			c.execute(query)
		
		return c.fetchall()
	

########NEW FILE########
__FILENAME__ = settings
'''
Copyright (c) 2012, Tarek Galal <tarek@wazapp.im>

This file is part of Wazapp, an IM application for Meego Harmattan platform that
allows communication with Whatsapp users

Wazapp is free software: you can redistribute it and/or modify it under the 
terms of the GNU General Public License as published by the Free Software 
Foundation, either version 2 of the License, or (at your option) any later 
version.

Wazapp is distributed in the hope that it will be useful, but WITHOUT ANY 
WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS FOR A 
PARTICULAR PURPOSE. See the GNU General Public License for more details.

You should have received a copy of the GNU General Public License along with 
Wazapp. If not, see http://www.gnu.org/licenses/.
'''

from model import Model;

class Setting(Model):
	pass
	
	
class Settingtype(Model):
	pass
	

########NEW FILE########
__FILENAME__ = notifier
'''
Copyright (c) 2012, Tarek Galal <tarek@wazapp.im>

This file is part of Wazapp, an IM application for Meego Harmattan platform that
allows communication with Whatsapp users

Wazapp is free software: you can redistribute it and/or modify it under the 
terms of the GNU General Public License as published by the Free Software 
Foundation, either version 2 of the License, or (at your option) any later 
version.

Wazapp is distributed in the hope that it will be useful, but WITHOUT ANY 
WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS FOR A 
PARTICULAR PURPOSE. See the GNU General Public License for more details.

You should have received a copy of the GNU General Public License along with 
Wazapp. If not, see http://www.gnu.org/licenses/.
'''
from mnotification import MNotificationManager,MNotification
from PySide.QtGui import QSound
from PySide.QtCore import QUrl, QCoreApplication
from QtMobility.Feedback import QFeedbackHapticsEffect #QFeedbackEffect
from QtMobility.SystemInfo import QSystemDeviceInfo
from constants import WAConstants
from utilities import Utilities
from QtMobility.MultimediaKit import QMediaPlayer
from PySide.phonon import Phonon
from wadebug import NotifierDebug
import dbus

class Notifier():
	def __init__(self,audio=True,vibra=True):
		_d = NotifierDebug();
		self._d = _d.d;

		self.manager = MNotificationManager('wazappnotify','WazappNotify');
		self.vibra = vibra

		self.personalRingtone = WAConstants.DEFAULT_SOUND_NOTIFICATION;
		self.personalVibrate = True;
		self.groupRingtone = WAConstants.DEFAULT_SOUND_NOTIFICATION;
		self.groupVibrate = True;
		
		QCoreApplication.setApplicationName("Wazapp");


		self.audioOutput = Phonon.AudioOutput(Phonon.MusicCategory, None)
		self.mediaObject = Phonon.MediaObject(None)
		Phonon.createPath(self.mediaObject, self.audioOutput)		

		self.profileChanged(0, 0, self.getCurrentProfile(), 0)
		bus = dbus.SessionBus()
		mybus = bus.get_object('com.nokia.profiled', '/com/nokia/profiled')
		self.nface = dbus.Interface(mybus, 'com.nokia.profiled')
		self.nface.connect_to_signal("profile_changed", self.profileChanged)
		#prof = self.getCurrentProfile()
		#reply = self.nface.get_value(prof,"ringing.alert.volume");
		#self.currentProfile = prof
		#self.currentVolume = "1.0" if reply=="100" else "0." + reply
		#self._d("Checking current profile: " + prof + " - Volume: " + self.currentVolume)
		#self.audioOutput.setVolume(float(self.currentVolume))

		
		#self.newMessageSound = WAConstants.DEFAULT_SOUND_NOTIFICATION #fetch from settings
		self.devInfo = QSystemDeviceInfo();
		
		#self.devInfo.currentProfileChanged.connect(self.profileChanged);
		
		self.audio = True
		'''if audio:
			self.audio = QMediaPlayer(None,QMediaPlayer.LowLatency); 
			self.audio.setVolume(100);
		else:
			self.audio = False'''
			
		self.enabled = True
		self.notifications = {}
		

		# vibration comes too early here, now handled by ui.py when the message is already added in QML
		# well, the truth is that sound comes too late... :D
		#>> Any notification should be handler by the notifier, not UI :P I don't feel it's too early though,
		# but if necessary connect to a signal and vibrate from here.
		if self.vibra:
			self.vibra = QFeedbackHapticsEffect();
			self.vibra.setIntensity(1.0);
			self.vibra.setDuration(200);
	

	def getCurrentProfile(self):
		bus = dbus.SessionBus()
		notifierbus = bus.get_object('com.nokia.profiled', '/com/nokia/profiled')
		nface = dbus.Interface(notifierbus, 'com.nokia.profiled')
		reply = nface.get_profile();
		return reply;

	
	def profileChanged(self,arg1,arg2,profile,arg4):
		self._d("Profile changed");
		nbus = dbus.SessionBus()
		mynbus = nbus.get_object('com.nokia.profiled', '/com/nokia/profiled')
		nface = dbus.Interface(mynbus, 'com.nokia.profiled')
		reply = nface.get_value(profile,"ringing.alert.volume");
		self.currentProfile = profile
		volume = int(reply) / 100.0
		self.currentVolume = str(volume)
		self._d("Checking current profile: " + profile + " - Volume: " + self.currentVolume)
		self.audioOutput.setVolume(volume)

	
	def enable(self):
		self.enabled = True
	
	def disable(self):
		self.enabled = False
	
	def saveNotification(self,jid,data):
		self.notifications[jid] = data;
		
	
	def getCurrentSoundPath(self,ringtone):
		#activeProfile = self.devInfo.currentProfile();
		
		if self.currentProfile == "general":
			return ringtone
		elif self.currentProfile == "meeting":
			return WAConstants.FOCUSED_SOUND_NOTIFICATION
		else:
			return WAConstants.NO_SOUND
		
	
	
	def hideNotification(self,jid):
		if self.notifications.has_key(jid):
			#jid = jids[0]
			nId = self.notifications[jid]["id"];
			del self.notifications[jid]
			self._d("DELETING NOTIFICATION BY ID "+str(nId));
			self.manager.removeNotification(nId);
			self.mediaObject.clear()

				
	def notificationCallback(self,jid):
		#nId = 0
		#jids = [key for key,value in self.notifications.iteritems() if value["id"]==nId]
		#if len(jids):
		if self.notifications.has_key(jid):
			#jid = jids[0]
			nId = self.notifications[jid]["id"];
			self.notifications[jid]["callback"](jid);
			del self.notifications[jid]
			#self.manager.removeNotification(nId);
		
	def stopSound(self):
		self.mediaObject.clear()

	def playSound(self,soundfile):
		self.mediaObject.clear()
		self.mediaObject.setCurrentSource(Phonon.MediaSource(soundfile))
		self.mediaObject.play()


	def newGroupMessage(self,jid,contactName,message,picture=None,callback=False):
		self.newMessage(jid,contactName,message,self.groupRingtone, self.groupVibrate, picture, callback)

	def newSingleMessage(self,jid,contactName,message,picture=None,callback=False):
		self.newMessage(jid,contactName,message,self.personalRingtone, self.personalVibrate, picture, callback)
	
	def newMessage(self,jid,contactName,message,ringtone,vibration,picture=None,callback=False):
	  
		message = message.replace("<br />", "\n").replace("&lt;", "<").replace("&gt;", ">").replace("&quot;", "\"").replace("&amp;", "&")
		
		self._d("NEW NOTIFICATION! Ringtone: " + ringtone + " - Vibrate: " + str(vibration))

		activeConvJId = self.ui.getActiveConversation()
		
		max_len = min(len(message),20)
		
		if self.enabled:
			
			if(activeConvJId == jid or activeConvJId == ""):
				if self.audio and ringtone!= WAConstants.NO_SOUND:
					soundPath = WAConstants.DEFAULT_BEEP_NOTIFICATION;
					self._d(soundPath)
					self.playSound(soundPath)


				if self.vibra and vibration:
					self.vibra.start()

				return



			if self.audio and ringtone!=WAConstants.NO_SOUND:
				soundPath = self.getCurrentSoundPath(ringtone);
				self._d(soundPath)
				self.playSound(soundPath)

			
			n = MNotification("wazapp.message.new",contactName, message);
			n.image = picture
			n.manager = self.manager;
			action = lambda: self.notificationCallback(jid)
			
			n.setAction(action);
		
			notifications = n.notifications();
			
			if self.notifications.has_key(jid):
				nId = self.notifications[jid]['id'];
				
				for notify in notifications:
					if int(notify[0]) == nId:
						n.id = nId
						break
				
				if n.id != nId:
					del self.notifications[jid]
			
				
			if(n.publish()):
				nId = n.id;
				self.saveNotification(jid,{"id":nId,"callback":callback});
		
		
			if self.vibra and vibration:
				self.vibra.start()
			
			
	
if __name__=="__main__":
	n = Notifier();
	n.newMessage("tgalal@WHATEVER","Tarek Galal","HELLOOOOOOOOOOOO","/usr/share/icons/hicolor/80x80/apps/waxmppplugin80.png");
	n.newMessage("tgalal@WHATEVER","Tarek Galal","YOW","/usr/share/icons/hicolor/80x80/apps/waxmppplugin80.png");

########NEW FILE########
__FILENAME__ = registrationhandler
'''
Copyright (c) 2012, Tarek Galal <tarek@wazapp.im>

This file is part of Wazapp, an IM application for Meego Harmattan platform that
allows communication with Whatsapp users

Wazapp is free software: you can redistribute it and/or modify it under the 
terms of the GNU General Public License as published by the Free Software 
Foundation, either version 2 of the License, or (at your option) any later 
version.

Wazapp is distributed in the hope that it will be useful, but WITHOUT ANY 
WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS FOR A 
PARTICULAR PURPOSE. See the GNU General Public License for more details.

You should have received a copy of the GNU General Public License along with 
Wazapp. If not, see http://www.gnu.org/licenses/.
'''

from PySide.QtDeclarative import QDeclarativeView,QDeclarativeProperty
from PySide import QtCore
from wadebug import WADebug
from PySide.QtCore import QUrl
from accountsmanager import AccountsManager
from utilities import Utilities
from Yowsup.Registration.v2.coderequest import WACodeRequest
from Yowsup.Registration.v2.regrequest import WARegRequest
from Yowsup.Registration.v2.existsrequest import WAExistsRequest
from Yowsup.Common.utilities import Utilities as YowsupUtils
from Yowsup.Common.debugger import Debugger as YowsupDebugger
import threading, time
from constants import WAConstants
import datetime
#from smshandler import SMSHandler


def async(fn):
    def wrapped(self, *args):
        threading.Thread(target = fn, args = (self,) + args).start()
    
    return wrapped

class RegistrationUI(QDeclarativeView):

    statusUpdated = QtCore.Signal(str); #status 
    registrationFailed = QtCore.Signal(str); #reason
    registrationSuccess = QtCore.Signal(str); #phoneNumber
    verificationSuccess = QtCore.Signal()
    verificationFailed = QtCore.Signal(str)
    codeRequestCancelled = QtCore.Signal();
    voiceRequestCancelled = QtCore.Signal();
    voiceCodeRequested = QtCore.Signal();

    gotAccountData = QtCore.Signal(dict) # internally used signal to create the new account in main thread

    def __init__(self, accountId = 0):
        super(RegistrationUI, self).__init__()
        WADebug.attach(self)
        
        YowsupDebugger.enabled = True
        self.deviceIMEI = Utilities.getImei()
        self.account = None #waccount
        self.accountInstance = None #real account
        self.smsHandler = None
        self.number = ""
        self.cc = ""
        
        self.gotAccountData.connect(self.createOrUpdateAccount)
        #AccountsManager.manager.accountCreated.connect(self.onAccountCreated)
        
        if accountId:
            account = AccountsManager.getAccountById(accountId)
            if account:
                self.account = account
                self.cc = account.cc
                self.number = account.phoneNumber
                self.accountInstance = account.accountInstance
                self.setupEditMode()
            else:
                raise Exception("Got account Id but couldn't find account")
        else:
            
            #this is a new account request
            #check existence of an old one 
            account = AccountsManager.findAccount()
            if account:
                self.account = account
                self.cc = account.cc
                self.number = account.phoneNumber
                self.accountInstance = account.accountInstance
                self.setupEditMode()
            else:
                self.setupNewMode()

        src = QUrl('/opt/waxmppplugin/bin/wazapp/UI/Registration/regmain.qml')
        self.setSource(src)

        self.registrationFailed.connect(self.rootObject().onRegistrationFailed)
        self.registrationSuccess.connect(self.rootObject().onRegistrationSuccess)
        self.voiceCodeRequested.connect(self.rootObject().onVoiceCodeRequested)
        self.statusUpdated.connect(self.rootObject().onStatusUpdated)
        self.verificationSuccess.connect(self.rootObject().onVerifySuccess)
        self.verificationFailed.connect(self.rootObject().onVerifyFailed)

        self.rootObject().savePushName.connect(self.savePushname)
        self.rootObject().abraKadabra.connect(self.abraKadabra)
        self.rootObject().codeRequest.connect(self.codeRequest)
        #self.rootObject().stopCodeRequest.connect(self.stopCodeRequest)
        self.rootObject().registerRequest.connect(self.registerRequest)
        self.rootObject().deleteAccount.connect(self.deleteAccount)
        self.rootObject().verifyAccount.connect(self.existsRequest)
        
    def setupEditMode(self):
        
        if self.account is None:
            raise Exception("Requested edit mode with account not set")

        self.rootContext().setContextProperty("initType", 2);
        self.rootContext().setContextProperty("username", self.account.username);
        self.rootContext().setContextProperty("currPhoneNumber", self.account.username);
        self.rootContext().setContextProperty("currPushName", self.account.pushName);

        self.rootContext().setContextProperty("accountKind", self.account.kind);
        
        if self.account.expiration is not None:
            formatted = datetime.datetime.fromtimestamp(self.account.expiration).strftime(WAConstants.DATE_FORMAT)
            self.rootContext().setContextProperty("accountExpiration", formatted);


    def setupNewMode(self):
        self.rootContext().setContextProperty("initType", 1);
        self.rootContext().setContextProperty("mcc", Utilities.getMcc());
        
        #self.smsHandler = SMSHandler()
        #self.smsHandlerThread = QThread()
        #self.smsHandler.moveToThread(self.smsHandlerThread)
        #self.smsHandlerThread.started.connect(self.smsHandler.initManager)
        #self.smsHandlerThread.start()

    def savePushname(self, pushName):
        self.account.accountInstance.setValue("pushName", pushName)
        self.account.accountInstance.sync()

    def abraKadabra(self):
        self._d("ABRA KADABRA!")
        self.registerRequest("919177")

    @async
    def codeRequest(self, cc, number, reqType):
        
        self.number = number
        self.cc = cc

        if reqType in ("sms", "voice"):
            result = WACodeRequest(cc, number, YowsupUtils.processIdentity(self.deviceIMEI), reqType).send()

            if reqType == "sms":
                self.statusUpdated.emit("reg_a")
            
            if "status" in result:
            
                self._d(result["status"])
                
                if result["status"] == "sent":
                    if reqType == "voice":
                        self.voiceCodeRequested.emit()
                    else:
                        self.statusUpdated.emit("reg_b");
                elif result["status"] == "ok":
                    self.gotAccountData.emit(result)
                else:
                    reason = result["status"]
                    if result["reason"] is not None:
                        reason = reason + " reason: %s" % result["reason"]

                    if result["retry_after"] is not None:
                        reason = reason + " retry after %s" % result["retry_after"]

                    if result["param"] is not None:
                        reason = reason + ": %s" % result["param"]

                    self.registrationFailed.emit(reason)  
            else:
                self.registrationFailed.emit("Err: No status received")

    @async
    def registerRequest(self, code):
        code = "".join(code.split('-')) #remove hyphen
        self._d("should register with code %s" % code)
        result = WARegRequest(self.cc, self.number, code, YowsupUtils.processIdentity(self.deviceIMEI)).send()
        
        if "status" in result and result["status"] is not None:
            if result["status"] == "ok":
                self.gotAccountData.emit(result)
            else:
                errMessage = "Failed!"
                if result["reason"] is not None:
                    errMessage = errMessage + " Server said '%s'." % result["reason"]
                
                if result["retry_after"] is not None:
                    errMessage = errMessage + " Retry after: %s" % result["retry_after"]
                    
                self.registrationFailed.emit(errMessage)
        else:
            self.registrationFailed.emit("Err: No status received")
    
    
    @async
    def existsRequest(self):
        result = WAExistsRequest(self.cc, self.number, YowsupUtils.processIdentity(self.deviceIMEI)).send()

        if "status" in result and result["status"] is not None:
            if result["status"] == "ok":
                self.gotAccountData.emit(result)
            else:
                self.verificationFailed.emit("")
        else:
            self.verificationFailed.emit("Err: No status received. Try again.")
      
    
    def createOrUpdateAccount(self, data):

        if self.accountInstance is None:
            self.accountInstance = AccountsManager.manager.createAccount("waxmpp")
            self.accountInstance.sync()
            self.setAccountData(self.accountInstance.id(), data,  True)
        else:
            self.setAccountData(self.accountInstance.id(), data,  False)
            
        if not self.account:
            self.account = AccountsManager.getCurrentAccount();

    def setAccountData(self, accountId, data, isNew):
            result = data
            account = self.accountInstance

            account.setValue("username", result["login"]);
            account.setValue("jid", result["login"]+"@s.whatsapp.net");
            account.setValue("password", result["pw"]);
            account.setValue("penc", "b64")
            account.setValue("kind", result["kind"])
            account.setValue("expiration", result["expiration"])
            account.setValue("cost", result["cost"])
            account.setValue("price", result["price"])
            account.setValue("price_expiration", result["price_expiration"])
            account.setValue("currency", result["currency"])
            account.setValue("wazapp_lastUpdated", int(time.time()))
            account.setValue("wazapp_version", Utilities.waversion)
            account.setEnabled(True);

            if isNew:
                account.setValue("name", self.cc + self.number);
                account.setValue("status", WAConstants.INITIAL_USER_STATUS);
                account.setValue("imsi", Utilities.getImsi());
                account.setValue("cc", self.cc);
                account.setValue("phoneNumber", self.number);
                account.setValue("pushName", self.cc + self.number);
                account.sync();
                self.registrationSuccess.emit(result["login"])
            else:
                account.sync();
                self.verificationSuccess.emit()

            self.rootContext().setContextProperty("accountKind", result["kind"]);

            if result["expiration"]:
                formatted = datetime.datetime.fromtimestamp(int(result["expiration"])).strftime(WAConstants.DATE_FORMAT)
                self.rootContext().setContextProperty("accountExpiration", formatted);

    def deleteAccount(self):
        self.accountInstance.remove()
        self.accountInstance.sync()
        self.engine().quit.emit()
########NEW FILE########
__FILENAME__ = smshandler
#from QtMobility.SystemInfo import QSystemDeviceInfo,QSystemNetworkInfo
from QtMobility.Messaging import QMessageManager, QMessage, QMessageFilter
from PySide.QtCore import QObject
from PySide import QtCore
from wadebug import WADebug
class SMSHandler(QObject):
    
    gotCode = QtCore.Signal(str)
    
    def __init__(self):
        WADebug.attach(self)

        super(SMSHandler, self).__init__()
        
    def messageAdded(self, messageId, matchingFilterIds):
        self._d("GOT A MESSAGE!")
        self._d(matchingFilterIds)
        
        print self.manager.message(messageId).textContent()
    
    
    def initManager(self):
        self.manager = QMessageManager();
        self.manager.messageAdded.connect(self.messageAdded)
        
        
        self.filters = [self.manager.registerNotificationFilter(
                    QMessageFilter.byType(QMessage.Sms) & QMessageFilter.byStandardFolder(QMessage.InboxFolder)
                    )]
        
        self._d(self.filters)

    def stopListener(self):
        pass
    
    def run(self):
        pass
########NEW FILE########
__FILENAME__ = settingsmanager

########NEW FILE########
__FILENAME__ = ui
'''
Copyright (c) 2012, Tarek Galal <tarek@wazapp.im>

This file is part of Wazapp, an IM application for Meego Harmattan platform that
allows communication with Whatsapp users

Wazapp is free software: you can redistribute it and/or modify it under the 
terms of the GNU General Public License as published by the Free Software 
Foundation, either version 2 of the License, or (at your option) any later 
version.

Wazapp is distributed in the hope that it will be useful, but WITHOUT ANY 
WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS FOR A 
PARTICULAR PURPOSE. See the GNU General Public License for more details.

You should have received a copy of the GNU General Public License along with 
Wazapp. If not, see http://www.gnu.org/licenses/.
'''

from PySide import QtCore
from PySide.QtCore import QUrl
from PySide.QtDeclarative import QDeclarativeView,QDeclarativeProperty
from QtMobility.Messaging import *
from contacts import WAContacts
from waxmpp import WAXMPP
from utilities import Utilities
from accountsmanager import AccountsManager
from PySide.QtGui import QApplication

#from registration import Registration

from messagestore import MessageStore
from threading import Timer
from waservice import WAService
import dbus
from wadebug import UIDebug
import os, shutil, time, hashlib
from subprocess import call
import Image
from PIL.ExifTags import TAGS
from constants import WAConstants
import subprocess

class WAUI(QDeclarativeView):
	splashOperationUpdated = QtCore.Signal(str)
	initialized = QtCore.Signal()
	phoneContactsReady = QtCore.Signal(list)

	
	def __init__(self, accountJid):
		
		_d = UIDebug();
		self._d = _d.d;
	
		self.initializationDone = False
		bus = dbus.SessionBus()
		mybus = bus.get_object('com.nokia.video.Thumbnailer1', '/com/nokia/video/Thumbnailer1')
		self.iface = dbus.Interface(mybus, 'org.freedesktop.thumbnails.SpecializedThumbnailer1')
		self.iface.connect_to_signal("Finished", self.thumbnailUpdated)

		contactsbus = bus.get_object('com.nokia.maemo.meegotouch.Contacts', '/', follow_name_owner_changes=True, )
		self.contactsbus = dbus.Interface(contactsbus, 'com.nokia.maemo.meegotouch.ContactsInterface')
		self.contactsbus.connect_to_signal("contactsPicked", self.contactPicked)

		camerabus = bus.get_object('com.nokia.maemo.CameraService', '/', follow_name_owner_changes=True, )
		self.camera = dbus.Interface(camerabus, 'com.nokia.maemo.meegotouch.CameraInterface')
		self.camera.connect_to_signal("captureCompleted", self.captureCompleted)
		self.camera.connect_to_signal("cameraClosed", self.captureCanceled)
		self.selectedJid = ""
		
		super(WAUI,self).__init__();
		url = QUrl('/opt/waxmppplugin/bin/wazapp/UI/main.qml')

		self.filelist = []
		self.accountJid = accountJid;
		self.accountPushName = None;

		self.rootContext().setContextProperty("waversion", Utilities.waversion);
		self.rootContext().setContextProperty("WAConstants", WAConstants.getAllProperties());
		self.rootContext().setContextProperty("myAccount", accountJid);
		
		currProfilePicture = WAConstants.CACHE_PROFILE + "/" + accountJid.split("@")[0] + ".jpg"
		self.rootContext().setContextProperty("currentPicture", currProfilePicture if os.path.exists(currProfilePicture) else "")
		
		
		
		self.setSource(url);
		self.focus = False
		self.whatsapp = None
		self.idleTimeout = None
		
	
	def setAccountPushName(self, pushName):
		self.accountPushName = pushName;
		self.rootContext().setContextProperty("myPushName", pushName);
		
	def onProcessEventsRequested(self):
		#self._d("Processing events")
		QtCore.QCoreApplication.processEvents()
		
	def initConnections(self,store):
		self.store = store;
		#self.setOrientation(QmlApplicationViewer.ScreenOrientationLockPortrait);
		#self.rootObject().sendRegRequest.connect(self.sendRegRequest);
		self.c = WAContacts(self.store);
		self.c.contactsRefreshed.connect(self.populateContacts);
		self.c.contactsRefreshed.connect(self.rootObject().onRefreshSuccess);
		#self.c.contactsRefreshed.connect(self.updateContactsData); NUEVO!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
		self.c.contactsRefreshFailed.connect(self.rootObject().onRefreshFail);
		self.c.contactsSyncStatusChanged.connect(self.rootObject().onContactsSyncStatusChanged);
		self.c.contactPictureUpdated.connect(self.rootObject().onPictureUpdated);
		#self.c.contactUpdated.connect(self.rootObject().onContactUpdated);
		#self.c.contactAdded.connect(self.onContactAdded);
		self.rootObject().refreshContacts.connect(self.c.resync)
		self.rootObject().sendSMS.connect(self.sendSMS)
		self.rootObject().makeCall.connect(self.makeCall)
		self.rootObject().sendVCard.connect(self.sendVCard)
		self.rootObject().consoleDebug.connect(self.consoleDebug)
		self.rootObject().setLanguage.connect(self.setLanguage)
		self.rootObject().removeFile.connect(self.removeFile)
		self.rootObject().getRingtones.connect(self.getRingtones)
		self.rootObject().startRecording.connect(self.startRecording)
		self.rootObject().stopRecording.connect(self.stopRecording)
		self.rootObject().playRecording.connect(self.playRecording)
		self.rootObject().deleteRecording.connect(self.deleteRecording)
		self.rootObject().breathe.connect(self.onProcessEventsRequested)
		self.rootObject().browseFiles.connect(self.browseFiles)
		self.rootObject().setMyPushName.connect(self.setMyPushName)

		self.rootObject().openContactPicker.connect(self.openContactPicker)

		#self.rootObject().vibrateNow.connect(self.vibrateNow)
				
		#Changed by Tarek: connected directly to QContactManager living inside contacts manager
		#self.c.manager.manager.contactsChanged.connect(self.rootObject().onContactsChanged);
		#self.c.manager.manager.contactsAdded.connect(self.rootObject().onContactsChanged);
		#self.c.manager.manager.contactsRemoved.connect(self.rootObject().onContactsChanged);
		
		#self.contactsReady.connect(self.rootObject().pushContacts)
		self.phoneContactsReady.connect(self.rootObject().pushPhoneContacts)
		self.splashOperationUpdated.connect(self.rootObject().setSplashOperation)
		self.initialized.connect(self.rootObject().onInitDone)
		
		self.messageStore = MessageStore(self.store);
		self.messageStore.messagesReady.connect(self.rootObject().messagesReady)
		self.messageStore.conversationReady.connect(self.rootObject().conversationReady)
		self.rootObject().loadMessages.connect(self.messageStore.loadMessages);
		
		
		self.rootObject().deleteConversation.connect(self.messageStore.deleteConversation)
		self.rootObject().deleteMessage.connect(self.messageStore.deleteMessage)
		self.rootObject().conversationOpened.connect(self.messageStore.onConversationOpened)
		self.rootObject().removeSingleContact.connect(self.messageStore.removeSingleContact)
		self.rootObject().exportConversation.connect(self.messageStore.exportConversation)
		self.rootObject().getConversationGroupsByJid.connect(self.messageStore.getConversationGroups)
		self.messageStore.conversationGroups.connect(self.rootObject().onConversationGroups)
		self.rootObject().getConversationMediaByJid.connect(self.messageStore.getConversationMedia)  
		
		self.rootObject().openAccount.connect(self.openAccount)
		
		self.messageStore.conversationMedia.connect(self.rootObject().onConversationMedia)
		self.dbusService = WAService(self);
		
	def openAccount(self):
		os.system("exec /usr/bin/invoker -w --type=e --single-instance /usr/lib/AccountSetup/bin/waxmppplugin &")
		#self.engine().quit.emit()
	
	def focusChanged(self,old,new):
		if new is None:
			self.onUnfocus();
		else:
			self.onFocus();
	
	def onUnfocus(self):
		self._d("FOCUS OUT")
		self.focus = False
		
		if not self.initializationDone:
			return
		
		self.rootObject().appFocusChanged(False);
		self.idleTimeout = Timer(5,self.whatsapp.eventHandler.onUnavailable)
		self.idleTimeout.start()
		self.whatsapp.eventHandler.onUnfocus();
		
	
	def onFocus(self):
		self._d("FOCUS IN")
		self.focus = True
		
		if not self.initializationDone:
			return

		self.whatsapp.eventHandler.notifier.stopSound();
		self.rootObject().appFocusChanged(True);
		if self.idleTimeout is not None:
			self.idleTimeout.cancel()
		
		self.whatsapp.eventHandler.onFocus();
		#self.whatsapp.eventHandler.onAvailable(self.accountPushName); Is it necessary everytime?
		self.whatsapp.eventHandler.onAvailable();
	
	def closeEvent(self,e):
		self._d("HIDING")
		e.ignore();
		self.whatsapp.eventHandler.onUnfocus();
		
		
		self.hide();
		
		#self.showFullScreen();
	
	def forceRegistration(self):
		''' '''
		self._d("NO VALID ACCOUNT")
		exit();
		self.rootObject().forceRegistration(Utilities.getCountryCode());
		
	def sendRegRequest(self,number,cc):
		
		
		self.reg.do_register(number,cc);
		#reg =  ContactsSyncer();
		#reg.start();
		#reg.done.connect(self.blabla);

		#reg.reg_success.connect(self.rootObject().regSuccess);
		#reg.reg_fail.connect(self.rootObject().regFail);
		
		#reg.start();
		
	def setLanguage(self,lang):
		if os.path.isfile(WAConstants.STORE_PATH + "/language.qm"):
			os.remove(WAConstants.STORE_PATH + "/language.qm")
		shutil.copyfile("/opt/waxmppplugin/bin/wazapp/i18n/" + lang + ".qm", WAConstants.STORE_PATH + "/language.qm")


	def consoleDebug(self,text):
		self._d(text);


	def setMyAccount(self,account):
		self.rootObject().setMyAccount(account)

	def sendSMS(self, num):
		print "SENDING SMS TO " + num
		bus = dbus.SessionBus()
		messaging_if = dbus.Interface(bus.get_object('com.nokia.Messaging', '/'), 'com.nokia.MessagingIf')
		messaging_if.showMessageEditor("sms", [num], "", "", [])


	def makeCall(self, num):
		print "CALLING TO " + num
		bus = dbus.SystemBus()
		csd_call = dbus.Interface(bus.get_object('com.nokia.csd', '/com/nokia/csd/call'), 'com.nokia.csd.Call')
		csd_call.CreateWith(str(num), dbus.UInt32(0))
	
	def sendVCard(self,jid,name):
		self.c.exportContact(jid,name);
	

	def openContactPicker(self,multi,title):
		call(["qdbus", "com.nokia.maemo.meegotouch.Contacts", "/", "com.nokia.maemo.meegotouch.ContactsInterface.openContactPicker", "0", title, multi, "", "1", "("," ",")"])


	def contactPicked(self,contacts,val):
		print "CONTACTS PICKED: " + str(contacts) + " - " + val


		
	def updateContact(self, jid):
		self._d("POPULATE SINGLE");
		self.c.updateContact(jid);
	
	def updatePushName(self, jid, push):
		self._d("UPDATING CONTACTS");
		#contacts = self.c.getContacts();
		#self.rootObject().updateContactsData(contacts, jid, push);
		self.rootObject().updateContactPushName(jid, push)
		#self.rootObject().updateContactName.emit(jid,push);


	def updateContactsData(self):
		contacts = self.c.getContacts();
		position = 0
		for contact in contacts:
			print "CONTACT DATA: " + str(contact)
			if contact.iscontact=="no" and contact.pushname=="":
				self.rootObject().insertNewContact(position,contact);
			position = position +1


		

	def populateContacts(self, mode, contact=[]):
		#syncer = ContactsSyncer(self.store);
		
		#self.c.refreshing.connect(syncer.onRefreshing);
		#syncer.done.connect(c.updateContacts);
		if (mode == "STATUS"):
			self._d("UPDATE CONTACT STATUS");
			self.rootObject().updateContactStatus(contact.jid, contact.status.decode("unicode_escape"))

		else:
			if not self.initializationDone:
				self.splashOperationUpdated.emit("Loading Contacts")

			contacts = self.c.getContacts();
			self._d("POPULATE CONTACTS: " + str(len(contacts)));
			
			
			contactsFiltered = filter(lambda c: c["jid"]!=self.accountJid, contacts)
			self.rootObject().pushContacts(mode,contactsFiltered);

		#if self.whatsapp is not None:
		#	self.whatsapp.eventHandler.networkDisconnected()

		
	def populateConversations(self):
		if not self.initializationDone:
			self.splashOperationUpdated.emit("Loading Conversations")
		self.messageStore.loadConversations()
		

	def populatePhoneContacts(self):
		
		if not self.initializationDone:
			self.splashOperationUpdated.emit("Loading Phone Contacts")
		
		self._d("POPULATE PHONE CONTACTS");
		contacts = self.c.getPhoneContacts();
		self.rootObject().pushPhoneContacts(contacts);
		#self.phoneContactsReady.emit(contacts)

	
	def login(self):
		self.whatsapp.start();
	
	def showUI(self,jid):
		self._d("SHOULD SHOW")
		self.showFullScreen();
		self.rootObject().openConversation(jid)
		
	def getActiveConversation(self):
		
		if not self.focus:
			return 0
		
		self._d("GETTING ACTIVE CONV")
		
		activeConvJId = QDeclarativeProperty(self.rootObject(),"activeConvJId").read();
		
		#self.rootContext().contextProperty("activeConvJId");
		self._d("DONE - " + str(activeConvJId))
		self._d(activeConvJId)
		
		return activeConvJId
		

	def processFiles(self, folder, data): #, ignored):
		#print "Processing " + folder
		
		if not os.path.exists(folder):
			return
		
		currentDir = os.path.abspath(folder)
		filesInCurDir = os.listdir(currentDir)

		for file in filesInCurDir:
			curFile = os.path.join(currentDir, file)

			if os.path.isfile(curFile):
				curFileExtention = curFile.split(".")[-1]
				if curFileExtention in data and not curFile in self.filelist and not "No sound.wav" in curFile:
					self.filelist.append(curFile)
			elif not "." in curFile: #Don't process hidden folders
				#if not curFile in ignored:
				self.processFiles(curFile, data) #, ignored)


	def getImageFiles(self):
		print "GETTING IMAGE FILES..."
		self.filelist = []
		data = ["jpg","jpeg","png","gif","JPG","JPEG","PNG","GIF"]
		'''ignored = ["/home/user/MyDocs/ANDROID","/home/user/MyDocs/openfeint"]
		f = open("/home/user/.config/tracker/tracker-miner-fs.cfg", 'r')
		for line in f:
			if "IgnoredDirectories=" in line:
				values = line.replace("IgnoredDirectories=","").split(';')
				break
		f.close()
		for val in values:
			ignored.append(val.replace("$HOME","/home/user"))'''

		self.processFiles("/home/user/MyDocs/DCIM", data) #, ignored)
		self.processFiles("/home/user/MyDocs/Pictures", data) #, ignored)
		self.processFiles("/home/user/MyDocs/Wazapp", data) #, ignored) @@Remove since using STORE_PATH as well?
		self.processFiles(WAConstants.STORE_PATH, data)


		myfiles = []
		for f in self.filelist:
			stats = os.stat(f)
			lastmod = time.localtime(stats[8])

			m = hashlib.md5()
			url = QtCore.QUrl("file://"+f).toEncoded()
			m.update(url)
			crypto = WAConstants.THUMBS_PATH + "/grid/" + m.hexdigest() + ".jpeg"
			if not os.path.exists(crypto):
				# Thumbnail does'n exist --> Generating...
				if f.split(".")[-1] == "jpg" or f.split(".")[-1] == "JPG":
					self.iface.Queue(str(url),"image/jpeg","grid", True)
				elif f.split(".")[-1] == "png" or f.split(".")[-1] == "PNG":
					self.iface.Queue(str(url),"image/png","grid", True)
				elif f.split(".")[-1] == "gif" or f.split(".")[-1] == "GIF":
					self.iface.Queue(str(url),"image/gif","grid", True)

			myfiles.append({"fileName":f.split('/')[-1],"url":QtCore.QUrl("file://"+f).toEncoded(),"date":lastmod,"thumb":crypto}) 

		self.rootObject().pushImageFiles( sorted(myfiles, key=lambda k: k['date'], reverse=True) );


	def getVideoFiles(self):
		print "GETTING VIDEO FILES..."
		self.filelist = []
		data = ["mov","3gp","mp4","MOV","3GP","MP4"]
		'''ignored = ["/home/user/MyDocs/ANDROID","/home/user/MyDocs/openfeint"]
		f = open("/home/user/.config/tracker/tracker-miner-fs.cfg", 'r')
		for line in f:
			if "IgnoredDirectories=" in line:
				values = line.replace("IgnoredDirectories=","").split(';')
				break
		f.close()
		for val in values:
			ignored.append(val.replace("$HOME","/home/user"))'''

		self.processFiles("/home/user/MyDocs/DCIM", data) #, ignored)
		self.processFiles("/home/user/MyDocs/Movies", data) #, ignored)
		self.processFiles("/home/user/MyDocs/Wazapp", data) #, ignored)
		self.processFiles(WAConstants.STORE_PATH, data)

		myfiles = []
		for f in self.filelist:
			stats = os.stat(f)
			lastmod = time.localtime(stats[8])
			
			m = hashlib.md5()
			url = QtCore.QUrl("file://"+f).toEncoded()
			m.update(url)
			crypto = WAConstants.THUMBS_PATH + "/grid/" + m.hexdigest() + ".jpeg"
			if not os.path.exists(crypto):
				# Thumbnail does'n exist --> Generating...
				if f.split(".")[-1] == "mp4" or f.split(".")[-1] == "MP4":
					self.iface.Queue(str(url),"video/mp4","grid", True)
				elif f.split(".")[-1] == "3gp" or f.split(".")[-1] == "3GP":
					self.iface.Queue(str(url),"video/3gpp4","grid", True)
				elif f.split(".")[-1] == "mov" or f.split(".")[-1] == "MOV":
					self.iface.Queue(str(url),"video/mpquicktime4","grid", True)

			myfiles.append({"fileName":f.split('/')[-1],"url":QtCore.QUrl("file://"+f).toEncoded(),"date":lastmod,"thumb":crypto}) 

		self.rootObject().pushVideoFiles( sorted(myfiles, key=lambda k: k['date'], reverse=True) );


	def getRingtones(self):
		print "GETTING RING TONES..."
		self.filelist = []
		data = ["mp3","MP3","wav","WAV"]
		self.processFiles("/usr/share/sounds/ring-tones/", data) #, ignored)
		self.processFiles("/home/user/MyDocs/Ringtones", data) #, ignored)

		myfiles = []
		for f in self.filelist:
			myfiles.append({"name":f.split('/')[-1].split('.')[0].title(),"value":f}) 

		self.rootObject().pushRingtones( sorted(myfiles, key=lambda k: k['name']) );



	def thumbnailUpdated(self,result):
		self.rootObject().onThumbnailUpdated()


	def openCamera(self, jid, mode):
		#self.camera.showCamera() #Only supports picture mode on start

		self.selectedJid = jid;
		call(["qdbus", "com.nokia.maemo.CameraService", "/", "com.nokia.maemo.meegotouch.CameraInterface.showCamera", "0", "", mode, "true"])

		'''
		# This shit doesn't work!!!
		camera = QCamera;
		viewFinder = QCameraViewfinder();
		viewFinder.show();
		camera.setViewfinder(viewFinder);
		imageCapture = QCameraImageCapture(camera);
		camera.setCaptureMode(QCamera.CaptureStillImage);
		camera.start();'''



	def captureCompleted(self,mode,filepath):
		if self.selectedJid == "":
			return;

		print "CAPTURE COMPLETED! Mode: " + mode
		rotation = 0
		capturemode = "image"
		if filepath.split(".")[-1] == "jpg":
			crypto = ""
			rotation = 0
			im = Image.open(filepath)
			try:
				if ', 274: 6,' in str(im._getexif()):
					rotation = 90
			except:
				rotation = 0
		else:
			capturemode = "video"
			m = hashlib.md5()
			url = QtCore.QUrl("file://"+filepath).toEncoded()
			m.update(url)
			crypto = WAConstants.THUMBS_PATH + "/screen/" + m.hexdigest() + ".jpeg"
			self.iface.Queue(str(url),"video/mp4","screen", True)

		print "CAPTURE COMPLETED! File: " + filepath
		self.rootObject().capturedPreviewPicture(self.selectedJid, filepath, rotation, crypto, capturemode)
		self.selectedJid = ""


	def captureCanceled(self):
		print "CAPTURE CLOSED!!!"
		self.selectedJid = ""


	def removeFile(self, filepath):
		print "REMOVING FILE: " + filepath
		filepath = filepath.replace("file://","")
		os.remove(filepath)


	def startRecording(self):
		print 'Starting the record...'
		self.pipe = subprocess.Popen(['/usr/bin/arecord','-r','16000','-t','wav',WAConstants.CACHE_PATH+'/temprecord.wav'])
		print "The pid is: " + str(self.pipe.pid)


	def stopRecording(self):
		print 'Killing REC Process now!'
		os.kill(self.pipe.pid, 9)
		self.pipe.poll()


	def playRecording(self):
		self.whatsapp.eventHandler.notifier.playSound(WAConstants.CACHE_PATH+'/temprecord.wav')


	def deleteRecording(self):
		if os.path.exists(WAConstants.CACHE_PATH+'/temprecord.wav'):
			os.remove(WAConstants.CACHE_PATH+'/temprecord.wav')


	def browseFiles(self, folder, format):
		print "Processing " + folder
		currentDir = os.path.abspath(folder)
		filesInCurDir = os.listdir(currentDir)
		myfiles = []

		for file in filesInCurDir:
			curFile = os.path.join(currentDir, file)
			curFileName = curFile.split('/')[-1]
			if curFileName[0] != ".":
				if os.path.isfile(curFile):
					curFileExtention = curFile.split(".")[-1]
					if curFileExtention in format:
						myfiles.append({"fileName":curFileName,"filepath":curFile, 
										"filetype":"send-audio", "name":"a"+curFile.split('/')[-1]})
				else:
					myfiles.append({"fileName":curFileName,"filepath":curFile, 
									"filetype":"folder", "name":"a"+curFile.split('/')[-1]})

		self.rootObject().pushBrowserFiles( sorted(myfiles, key=lambda k: k['name']), folder);

	def setMyPushName(self, pushname):
		AccountsManager.setPushName(pushname);
		self.rootContext().setContextProperty("myPushName", pushname);
		self.whatsapp.eventHandler.setMyPushName.emit(pushname)

	def initConnection(self):
		
		password = self.store.account.password;
		usePushName = self.store.account.pushName
		resource = "S40-2.4.7";
		chatUserID = self.store.account.username;
		domain ='s.whatsapp.net'
		
		
		
		whatsapp = WAXMPP(domain,resource,chatUserID,usePushName,password);
		
		WAXMPP.message_store = self.messageStore;
	
		whatsapp.setContactsManager(self.c);
		
		self.rootContext().setContextProperty("interfaceVersion", whatsapp.eventHandler.interfaceVersion)
		
		whatsapp.eventHandler.connected.connect(self.rootObject().onConnected);
		whatsapp.eventHandler.typing.connect(self.rootObject().onTyping)
		whatsapp.eventHandler.paused.connect(self.rootObject().onPaused)
		whatsapp.eventHandler.showUI.connect(self.showUI)
		whatsapp.eventHandler.messageSent.connect(self.rootObject().onMessageSent);
		whatsapp.eventHandler.messageDelivered.connect(self.rootObject().onMessageDelivered);
		whatsapp.eventHandler.connecting.connect(self.rootObject().onConnecting);
		whatsapp.eventHandler.loginFailed.connect(self.rootObject().onLoginFailed);
		whatsapp.eventHandler.sleeping.connect(self.rootObject().onSleeping);
		whatsapp.eventHandler.disconnected.connect(self.rootObject().onDisconnected);
		whatsapp.eventHandler.available.connect(self.rootObject().onAvailable);
		whatsapp.eventHandler.unavailable.connect(self.rootObject().onUnavailable);
		whatsapp.eventHandler.lastSeenUpdated.connect(self.rootObject().onLastSeenUpdated);
		whatsapp.eventHandler.updateAvailable.connect(self.rootObject().onUpdateAvailable)
		
		whatsapp.eventHandler.groupInfoUpdated.connect(self.rootObject().onGroupInfoUpdated);
		whatsapp.eventHandler.groupCreated.connect(self.rootObject().groupCreated);
		whatsapp.eventHandler.groupCreateFailed.connect(self.rootObject().groupCreateFailed);
		whatsapp.eventHandler.addedParticipants.connect(self.rootObject().addedParticipants);
		whatsapp.eventHandler.removedParticipants.connect(self.rootObject().onRemovedParticipants);
		whatsapp.eventHandler.groupParticipants.connect(self.rootObject().onGroupParticipants);
		whatsapp.eventHandler.groupEnded.connect(self.rootObject().onGroupEnded);
		whatsapp.eventHandler.groupSubjectChanged.connect(self.rootObject().onGroupSubjectChanged);
		whatsapp.eventHandler.profilePictureUpdated.connect(self.updateContact);

		whatsapp.eventHandler.setPushName.connect(self.updatePushName);
		whatsapp.eventHandler.statusChanged.connect(self.rootObject().onProfileStatusChanged);
		#whatsapp.eventHandler.setPushName.connect(self.rootObject().updatePushName);
		#whatsapp.eventHandler.profilePictureUpdated.connect(self.rootObject().onPictureUpdated);

		whatsapp.eventHandler.imageRotated.connect(self.rootObject().imageRotated);
		whatsapp.eventHandler.getPicturesFinished.connect(self.rootObject().getPicturesFinished);

		whatsapp.eventHandler.mediaTransferSuccess.connect(self.rootObject().mediaTransferSuccess);
		whatsapp.eventHandler.mediaTransferError.connect(self.rootObject().mediaTransferError);
		whatsapp.eventHandler.mediaTransferProgressUpdated.connect(self.rootObject().mediaTransferProgressUpdated)
		
		
		whatsapp.eventHandler.notifier.ui = self
		
		
		#whatsapp.eventHandler.new_message.connect(self.rootObject().newMessage)
		self.rootObject().sendMessage.connect(whatsapp.eventHandler.sendMessage)
		self.rootObject().sendTyping.connect(whatsapp.eventHandler.sendTyping)
		self.rootObject().sendPaused.connect(whatsapp.eventHandler.sendPaused);
		self.rootObject().conversationActive.connect(whatsapp.eventHandler.getLastOnline);
		self.rootObject().conversationActive.connect(whatsapp.eventHandler.conversationOpened);
		self.rootObject().fetchMedia.connect(whatsapp.eventHandler.fetchMedia)
		self.rootObject().fetchGroupMedia.connect(whatsapp.eventHandler.fetchGroupMedia)
		self.rootObject().uploadMedia.connect(whatsapp.eventHandler.uploadMedia)
		self.rootObject().uploadGroupMedia.connect(whatsapp.eventHandler.uploadMedia)
		self.rootObject().getGroupInfo.connect(whatsapp.eventHandler.getGroupInfo)
		self.rootObject().createGroupChat.connect(whatsapp.eventHandler.createGroupChat)
		self.rootObject().addParticipants.connect(whatsapp.eventHandler.addParticipants)
		self.rootObject().removeParticipants.connect(whatsapp.eventHandler.removeParticipants)
		self.rootObject().getGroupParticipants.connect(whatsapp.eventHandler.getGroupParticipants)
		self.rootObject().endGroupChat.connect(whatsapp.eventHandler.endGroupChat)
		self.rootObject().setGroupSubject.connect(whatsapp.eventHandler.setGroupSubject)
		self.rootObject().getPictureIds.connect(whatsapp.eventHandler.getPictureIds)
		self.rootObject().getPicture.connect(whatsapp.eventHandler.getPicture)
		self.rootObject().setGroupPicture.connect(whatsapp.eventHandler.setGroupPicture)
		self.rootObject().setMyProfilePicture.connect(whatsapp.eventHandler.setProfilePicture)
		self.rootObject().sendMediaImageFile.connect(whatsapp.eventHandler.sendMediaImageFile)
		self.rootObject().sendMediaVideoFile.connect(whatsapp.eventHandler.sendMediaVideoFile)
		self.rootObject().sendMediaAudioFile.connect(whatsapp.eventHandler.sendMediaAudioFile)
		self.rootObject().sendMediaRecordedFile.connect(whatsapp.eventHandler.sendMediaRecordedFile)
		self.rootObject().sendMediaMessage.connect(whatsapp.eventHandler.sendMediaMessage)
		self.rootObject().sendLocation.connect(whatsapp.eventHandler.sendLocation)
		self.rootObject().rotateImage.connect(whatsapp.eventHandler.rotateImage)
		self.rootObject().changeStatus.connect(whatsapp.eventHandler.changeStatus)

		self.c.contactExported.connect(whatsapp.eventHandler.sendVCard)

		self.rootObject().setBlockedContacts.connect(whatsapp.eventHandler.setBlockedContacts)
		self.rootObject().setResizeImages.connect(whatsapp.eventHandler.setResizeImages)
		self.rootObject().setPersonalRingtone.connect(whatsapp.eventHandler.setPersonalRingtone)
		self.rootObject().setPersonalVibrate.connect(whatsapp.eventHandler.setPersonalVibrate)
		self.rootObject().setGroupRingtone.connect(whatsapp.eventHandler.setGroupRingtone)
		self.rootObject().setGroupVibrate.connect(whatsapp.eventHandler.setGroupVibrate)

		self.rootObject().openCamera.connect(self.openCamera)

		self.rootObject().getImageFiles.connect(self.getImageFiles)
		self.rootObject().getVideoFiles.connect(self.getVideoFiles)
		
		self.rootObject().populatePhoneContacts.connect(self.populatePhoneContacts)
		self.rootObject().playSoundFile.connect(whatsapp.eventHandler.notifier.playSound)
		self.rootObject().stopSoundFile.connect(whatsapp.eventHandler.notifier.stopSound)


		#self.reg = Registration();
		self.whatsapp = whatsapp;
		
		QApplication.instance().aboutToQuit.connect(self.whatsapp.eventHandler.quit)
		
		#print "el acks:"
		#print whatsapp.supports_receipt_acks
		
		#self.whatsapp.start();
		
		
		

		


########NEW FILE########
__FILENAME__ = utilities
'''
Copyright (c) 2012, Tarek Galal <tarek@wazapp.im>

This file is part of Wazapp, an IM application for Meego Harmattan platform that
allows communication with Whatsapp users

Wazapp is free software: you can redistribute it and/or modify it under the 
terms of the GNU General Public License as published by the Free Software 
Foundation, either version 2 of the License, or (at your option) any later 
version.

Wazapp is distributed in the hope that it will be useful, but WITHOUT ANY 
WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS FOR A 
PARTICULAR PURPOSE. See the GNU General Public License for more details.

You should have received a copy of the GNU General Public License along with 
Wazapp. If not, see http://www.gnu.org/licenses/.
'''
import md5
import string
import threading, sys, os

from QtMobility.SystemInfo import QSystemDeviceInfo,QSystemNetworkInfo
class Utilities():

	debug_mode = 0;
	
	waversion = "0.9.21"
	

	
	@staticmethod
	def getImsi():
		#return "000000000000000"
		dev_info = QSystemDeviceInfo();
		return dev_info.imsi();
		
	@staticmethod	
	def getProfile():
		dev_info = QSystemDeviceInfo();
		return dev_info.currentProfile();
	
	@staticmethod
	def getCountryCode():
		net_info = QSystemNetworkInfo();
		return net_info.homeMobileCountryCode();
	
	@staticmethod
	def getMcc():
		net_info = QSystemNetworkInfo();
		return net_info.currentMobileCountryCode();
	
	@staticmethod
	def getMnc():
		net_info = QSystemNetworkInfo();
		return net_info.currentMobileNetworkCode();
		
	@staticmethod
	def getImei():
		dev_info = QSystemDeviceInfo();
		return dev_info.imei();
	
	@staticmethod
	def hashCode(string):
		h = 0;
		off =0;
		for i  in range (0,len(string)):
			h = 31*h + ord(string[off]);
			off+=1;

		return h;



	@staticmethod
	def decodeString(url):
		res = "";
		
		for char in url:
			ored = char ^ 0x13
			res = res+chr(ored);
		return res;
	
	@staticmethod
	def encodeString(string):
		res = [];
		for char in string:
			res.append(ord(char))
		return res;
	
	@staticmethod
	def byteArrayToStr(bytearray):
		res = "";
		for b in bytearray:
			res = res+chr(b);
		
		return res;


	@staticmethod
	def getUniqueFilename(fn):
		if not os.path.exists(fn):
			return fn
	
		path, name = os.path.split(fn)
		name, ext = os.path.splitext(name)
	
		make_fn = lambda i: os.path.join(path, '%s_%d%s' % (name, i, ext))
		
		
		_xrange = range if sys.version_info >= (3, 0) else xrange
	
		for i in _xrange(2, sys.maxsize):
			uni_fn = make_fn(i)
			if not os.path.exists(uni_fn):
				return uni_fn
	
		return None
			

	@staticmethod
	def str( number, radix ):
	   """str( number, radix ) -- reverse function to int(str,radix) and long(str,radix)"""

	   if not 2 <= radix <= 36:
	      raise ValueError, "radix must be in 2..36"

	   abc = string.digits + string.letters

	   result = ''

	   if number < 0:
	      number = -number
	      sign = '-'
	   else:
	      sign = ''

	   while True:
	      number, rdigit = divmod( number, radix )
	      result = abc[rdigit] + result
	      if number == 0:
		 return sign + result

	@staticmethod	
	def getChatPassword():
		imei = Utilities.getImei();
		
		
		buffer_str = imei[::-1];
		digest = S40MD5Digest();
		digest.reset();
		digest.update(buffer_str);
		bytes = digest.digest();
		buffer_str = ""
		for b in bytes:
			tmp = b+128;
			c = (tmp >> 8) & 0xff
			f = tmp & 0xff
			buffer_str+=Utilities.str(f,16);
		return buffer_str;
	


class ByteArray():
	def __init__(self,size=0):
		self.size = size;
		self.buf = bytearray(size);	
	
	def toByteArray(self):
		res = ByteArray();
		for b in self.buf:
			res.buf.append(b);
			
		return res;

	def reset(self):
		self.buf = bytearray(self.size);
		
	def getBuffer(self):
		return self.buf
		
	def read(self):
		return self.buf.pop(0);
		
	def read2(self,b,off,length):
		'''reads into a buffer'''
		if off < 0 or length < 0 or (off+length)>len(b):
			raise Exception("Out of bounds");
		
		if length == 0:
			return 0;
		
		if b is None:
			raise Exception("XNull pointerX");
		
		count = 0;
		
		while count < length:
			
			#self.read();
			#print "OKIIIIIIIIIIII";
			#exit();
			b[off+count]=self.read();
			count= count+1;
		
	
		return count;
		
	def write(self,data):
		if type(data) is int:
			self.writeInt(data);
		elif type(data) is chr:
			self.buf.append(ord(data));
		elif type(data) is str:
			self.writeString(data);
		elif type(data) is bytearray:
			self.writeByteArray(data);
		else:
			raise Exception("Unsupported datatype "+str(type(data)));
			
	def writeByteArray(self,b):
		for i in b:
			self.buf.append(i);
	
	def writeInt(self,integer):
		self.buf.append(integer);
	
	def writeString(self,string):
		for c in string:
			self.writeChar(c);
			
	def writeChar(self,char):
		self.buf.append(ord(char))
		

class S40MD5Digest():
	m = None;
	def __init__(self):
		self.m= md5.new()
		
	def update(self,string):
		#Utilities.debug("update digestion");
		self.m.update(str(string));
		
	def reset(self):	
		self.m = md5.new();
		
	def digest(self):
		#res = self.m.digest();
		#return res;
		arr = bytearray(128);
		res = 0;
		res = self.m.digest();
		resArr = bytearray(res);
		
		return resArr;
	
def async(fn):
	def wrapped(self, *args):
		threading.Thread(target = fn, args = (self,) + args).start()
	
	return wrapped

########NEW FILE########
__FILENAME__ = wadebug
from constants import WAConstants
import time

class WADebug():
	
	def __init__(self):
		self.enabled = False
		
		cname = self.__class__.__name__
		self.type= cname[:cname.index("Debug")]
	
	@staticmethod
	def attach(instance):
		d = WADebug();
		d.type = instance.__class__.__name__;
		instance._d = d.d
	
	@staticmethod
	def stdDebug(message,messageType="General"):
		#enabledTypes = ["general","stanzareader","sql","conn","waxmpp","wamanager","walogin","waupdater","messagestore"];
		disabledTypes = ["sql"]
		if messageType.lower() not in disabledTypes:
			try:
				print message;
			except UnicodeEncodeError:
				print "Skipped debug message because of UnicodeEncodeError"
	
	def formatMessage(self,message):
		#default = "{type}:{time}:\t{message}"
		t = time.time()
		message = "%s:\t%s"%(self.type,message)
		return message

	def debug(self,message):
		if self.enabled:
			WADebug.stdDebug(self.formatMessage(message),self.type)
		
	def d(self,message):#shorthand
		self.debug(message)
		message = message
		logline = "" #self.formatMessage(message)+"\n"
		if not "Sql:" in logline:
			try:
				# This tries to open an existing file but creates a new file if necessary.
				logfile = open(WAConstants.STORE_PATH + "/log.txt", "a")
				try:
					logfile.write(logline)
				finally:
					logfile.close()
			except IOError:
				pass

class JsonRequestDebug(WADebug):
	pass

class StatusRequestDebug(WADebug):
	pass

class EventHandlerDebug(WADebug):
	pass

class WaxmppDebug(WADebug):
	pass

class SqlDebug(WADebug):
	pass
	
class ConnDebug(WADebug):
	pass

class GeneralDebug(WADebug):
	pass

class ManagerDebug(WADebug):
	pass

class NotifierDebug(WADebug):
	pass

class MessageStoreDebug(WADebug):
	pass
	
class ConnMonDebug(WADebug):
	pass
	
class ContactsDebug(WADebug):
	pass

class UIDebug(WADebug):
	pass

class UpdaterDebug(WADebug):
	pass

class MediaHandlerDebug(WADebug):
	pass
	
class AccountsDebug(WADebug):
	pass
	
class LoginDebug(WADebug):
	pass
	
class WARequestDebug(WADebug):
	pass
	
		

########NEW FILE########
__FILENAME__ = waimageprocessor
import sys
from PIL import Image, ImageOps, ImageFilter
from wadebug import WADebug

class WAImageProcessor():
	squircleMaskPath = "/usr/share/themes/blanco/meegotouch/images/theme/basement/meegotouch-avatar/meegotouch-avatar-mask-small.png"
	squircleFramePath = "/usr/share/themes/blanco/meegotouch/images/theme/basement/meegotouch-avatar/meegotouch-avatar-frame-small.png"

	def __init__(self):
		WADebug.attach(self);
		self.squircleLoaded = False;
	
	
	def loadSquircle(self):
		self.squircleMask = Image.open(self.squircleMaskPath)
		self.squircleFrame = Image.open(self.squircleFramePath)
		
		self.squircleMask.load();
		self.squircleFrame.load();
		
		self.squircleLoaded = True

		return True;

	def createSquircle(self, source, destination):
		
		if not self.squircleLoaded: 
			self._d("Squircler is not loaded, loading")
			if not self.loadSquircle(): return

		self.maskImage(source, destination, self.squircleMask, self.squircleFrame)


	def maskImage(self, source, destination, mask, frame):
		try:
			if type(source) in (str, unicode):
				source = Image.open(source)
				source.load()

			if type(mask) in (str,unicode):
				mask = Image.open(mask)
				mask.load()

			if type(frame) in (str, unicode):
				frame = Image.open(frame)
				frame.load()

			mask = mask.filter(ImageFilter.SMOOTH)
			croppedImage = ImageOps.fit(source, mask.size, method=Image.ANTIALIAS)
			croppedImage = croppedImage.convert("RGBA")

			r,g,b,a = mask.split()

			croppedImage.paste(frame, mask=a)
			croppedImage.save(destination)
		except:
			self._d("Error creating mask")
			self._d(sys.exc_info()[1])

########NEW FILE########
__FILENAME__ = wajsonrequest
'''
Copyright (c) 2012, Tarek Galal <tarek@wazapp.im>

This file is part of Wazapp, an IM application for Meego Harmattan platform that
allows communication with Whatsapp users

Wazapp is free software: you can redistribute it and/or modify it under the 
terms of the GNU General Public License as published by the Free Software 
Foundation, either version 2 of the License, or (at your option) any later 
version.

Wazapp is distributed in the hope that it will be useful, but WITHOUT ANY 
WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS FOR A 
PARTICULAR PURPOSE. See the GNU General Public License for more details.

You should have received a copy of the GNU General Public License along with 
Wazapp. If not, see http://www.gnu.org/licenses/.
'''
import httplib,urllib
from utilities import Utilities

import threading
from PySide import QtCore
from PySide.QtCore import QThread
from warequest import WARequest
import json
from wadebug import JsonRequestDebug;
class WAJsonRequest(WARequest):


	#BASE_URL = [ 97, 61, 100, 123, 114, 103, 96, 114, 99, 99, 61, 125, 118, 103 ];
	status = None
	result = None
	params = []
	#v = "v1"
	#method = None
	conn = None
	
	done = QtCore.Signal(dict);
	fail = QtCore.Signal();
	
	def __init__(self):
		_d = JsonRequestDebug();
		self._d = _d.debug;
		super(WAJsonRequest,self).__init__();
			
	def addParam(self,name,value):
		self.params.append({name:value});
	
	def getUrl(self):
		return  self.base_url+self.req_file;

	def getUserAgent(self):
		#agent = "WhatsApp/1.2 S40Version/microedition.platform";
		agent = "WhatsApp/2.8.3 iPhone_OS/5.0.1 Device/Unknown_(iPhone4,1)";
		return agent;	

	def sendRequest(self):
		try:
			self.params =  [param.items()[0] for param in self.params];

			params = urllib.urlencode(self.params);
		
			self._d("Opening connection to "+self.base_url);
			self.conn = httplib.HTTPConnection(self.base_url,80);
			headers = {"User-Agent":self.getUserAgent(),
				"Content-Type":"application/x-www-form-urlencoded",
				"Accept":"text/json"
				};
		
			#Utilities.debug(headers);
			#Utilities.debug(params);
		
			self.conn.request("GET",self.req_file,params,headers);
			resp=self.conn.getresponse()
	 		response=resp.read();
	 		#Utilities.debug(response);
	 		
	 		self.done.emit(json.loads(response));
	 		return json.loads(response);
	 	except:
	 		self.fail.emit()
		#response_node  = doc.getElementsByTagName("response")[0];

		#for (name, value) in response_node.attributes.items():
		#self.onResponse(name,value);

########NEW FILE########
__FILENAME__ = walogin
'''
Copyright (c) 2012, Tarek Galal <tarek@wazapp.im>

This file is part of Wazapp, an IM application for Meego Harmattan platform that
allows communication with Whatsapp users

Wazapp is free software: you can redistribute it and/or modify it under the 
terms of the GNU General Public License as published by the Free Software 
Foundation, either version 2 of the License, or (at your option) any later 
version.

Wazapp is distributed in the hope that it will be useful, but WITHOUT ANY 
WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS FOR A 
PARTICULAR PURPOSE. See the GNU General Public License for more details.

You should have received a copy of the GNU General Public License along with 
Wazapp. If not, see http://www.gnu.org/licenses/.
'''
import base64, random;
from utilities import Utilities,S40MD5Digest,ByteArray;
from protocoltreenode import ProtocolTreeNode
from PySide import QtCore
from PySide.QtCore import QThread
import socket
from waexceptions import *
from wadebug import WADebug

class WALogin(QThread):

	dictYappari = [ None, None, None, None, None,  "1", "1.0", "ack", "action", "active", "add", "all", "allow", "apple", "audio", "auth", "author", "available", "bad-request", "base64", "Bell.caf", "bind", "body", "Boing.caf", "cancel", "category", "challenge", "chat", "clean", "code", "composing", "config", "conflict", "contacts", "create", "creation", "default", "delay", "delete", "delivered", "deny", "DIGEST-MD5", "DIGEST-MD5-1", "dirty", "en", "enable", "encoding", "error", "expiration", "expired", "failure", "false", "favorites", "feature", "field", "free", "from", "g.us", "get", "Glass.caf", "google", "group", "groups", "g_sound", "Harp.caf", "http://etherx.jabber.org/streams", "http://jabber.org/protocol/chatstates", "id", "image", "img", "inactive", "internal-server-error", "iq", "item", "item-not-found", "jabber:client", "jabber:iq:last", "jabber:iq:privacy", "jabber:x:delay", "jabber:x:event", "jid", "jid-malformed", "kind", "leave", "leave-all", "list", "location", "max_groups", "max_participants", "max_subject", "mechanism", "mechanisms", "media", "message", "message_acks", "missing", "modify", "name", "not-acceptable", "not-allowed", "not-authorized", "notify", "Offline Storage", "order", "owner", "owning", "paid", "participant", "participants", "participating", "fail", "paused", "picture", "ping", "PLAIN", "platform", "presence", "preview", "probe", "prop", "props", "p_o", "p_t", "query", "raw", "receipt", "receipt_acks", "received", "relay", "remove", "Replaced by new connection", "request", "resource", "resource-constraint", "response", "result", "retry", "rim", "s.whatsapp.net", "seconds", "server", "session", "set", "show", "sid", "sound", "stamp", "starttls", "status", "stream:error", "stream:features", "subject", "subscribe", "success", "system-shutdown", "s_o", "s_t", "t", "TimePassing.caf", "timestamp", "to", "Tri-tone.caf", "type", "unavailable", "uri", "url", "urn:ietf:params:xml:ns:xmpp-bind", "urn:ietf:params:xml:ns:xmpp-sasl", "urn:ietf:params:xml:ns:xmpp-session", "urn:ietf:params:xml:ns:xmpp-stanzas", "urn:ietf:params:xml:ns:xmpp-streams", "urn:xmpp:delay", "urn:xmpp:ping", "urn:xmpp:receipts", "urn:xmpp:whatsapp", "urn:xmpp:whatsapp:dirty", "urn:xmpp:whatsapp:mms", "urn:xmpp:whatsapp:push", "value", "vcard", "version", "video", "w", "w:g", "w:p:r", "wait", "x", "xml-not-well-formed", "xml:lang", "xmlns", "xmlns:stream", "Xylophone.caf", "account", "digest", "g_notify", "method", "password", "registration", "stat", "text", "user", "username", "event", "latitude", "longitude", "true", "after", "before", "broadcast", "count", "features", "first", "index", "invalid-mechanism", "last", "max", "offline", "proceed", "required", "sync", "elapsed", "ip", "microsoft", "mute", "nokia", "off", "pin", "pop_mean_time", "pop_plus_minus", "port", "reason", "server-error", "silent", "timeout", "lc", "lg", "bad-protocol", "none", "remote-server-timeout", "service-unavailable", "w:p", "w:profileicture", "notification" ]
	
	dictionary = [ None, None, None, None, None, "1", "1.0", "ack", "action", "active", "add", "all", "allow", "apple", "audio", "auth", "author", "available", "bad-request", "base64", "Bell.caf", "bind", "body", "Boing.caf", "cancel", "category", "challenge", "chat", "clean", "code", "composing", "config", "conflict", "contacts", "create", "creation", "default", "delay", "delete", "delivered", "deny", "DIGEST-MD5", "DIGEST-MD5-1", "dirty", "en", "enable", "encoding", "error", "expiration", "expired", "failure", "false", "favorites", "feature", "field", "free", "from", "g.us", "get", "Glass.caf", "google", "group", "groups", "g_sound", "Harp.caf", "http://etherx.jabber.org/streams", "http://jabber.org/protocol/chatstates", "id", "image", "img", "inactive", "internal-server-error", "iq", "item", "item-not-found", "jabber:client", "jabber:iq:last", "jabber:iq:privacy", "jabber:x:delay", "jabber:x:event", "jid", "jid-malformed", "kind", "leave", "leave-all", "list", "location", "max_groups", "max_participants", "max_subject", "mechanism", "mechanisms", "media", "message", "message_acks", "missing", "modify", "name", "not-acceptable", "not-allowed", "not-authorized", "notify", "Offline Storage", "order", "owner", "owning", "paid", "participant", "participants", "participating", "particpants", "paused", "picture", "ping", "PLAIN", "platform", "presence", "preview", "probe", "prop", "props", "p_o", "p_t", "query", "raw", "receipt", "receipt_acks", "received", "relay", "remove", "Replaced by new connection", "request", "resource", "resource-constraint", "response", "result", "retry", "rim", "s.whatsapp.net", "seconds", "server", "session", "set", "show", "sid", "sound", "stamp", "starttls", "status", "stream:error", "stream:features", "subject", "subscribe", "success", "system-shutdown", "s_o", "s_t", "t", "TimePassing.caf", "timestamp", "to", "Tri-tone.caf", "type", "unavailable", "uri", "url", "urn:ietf:params:xml:ns:xmpp-bind", "urn:ietf:params:xml:ns:xmpp-sasl", "urn:ietf:params:xml:ns:xmpp-session", "urn:ietf:params:xml:ns:xmpp-stanzas", "urn:ietf:params:xml:ns:xmpp-streams", "urn:xmpp:delay", "urn:xmpp:ping", "urn:xmpp:receipts", "urn:xmpp:whatsapp", "urn:xmpp:whatsapp:dirty", "urn:xmpp:whatsapp:mms", "urn:xmpp:whatsapp:push", "value", "vcard", "version", "video", "w", "w:g", "w:p:r", "wait", "x", "xml-not-well-formed", "xml:lang", "xmlns", "xmlns:stream", "Xylophone.caf", "account","digest","g_notify","method","password","registration","stat","text","user","username","event","latitude","longitude"]

	dictionaryIn = ["w:profile:picture"]

	dictionaryS40 = [ None, None, None, None, None, None, None, None, None, None, "account", "ack", "action", "active", "add", "after", "ib", "all", "allow", "apple", "audio", "auth", "author", "available", "bad-protocol", "bad-request", "before", "Bell.caf", "body", "Boing.caf", "cancel", "category", "challenge", "chat", "clean", "code", "composing", "config", "conflict", "contacts", "count", "create", "creation", "default", "delay", "delete", "delivered", "deny", "digest", "DIGEST-MD5-1", "DIGEST-MD5-2", "dirty", "elapsed", "broadcast", "enable", "encoding", "duplicate", "error", "event", "expiration", "expired", "fail", "failure", "false", "favorites", "feature", "features", "field", "first", "free", "from", "g.us", "get", "Glass.caf", "google", "group", "groups", "g_notify", "g_sound", "Harp.caf", "http://etherx.jabber.org/streams", "http://jabber.org/protocol/chatstates", "id", "image", "img", "inactive", "index", "internal-server-error", "invalid-mechanism", "ip", "iq", "item", "item-not-found", "user-not-found", "jabber:iq:last", "jabber:iq:privacy", "jabber:x:delay", "jabber:x:event", "jid", "jid-malformed", "kind", "last", "latitude", "lc", "leave", "leave-all", "lg", "list", "location", "longitude", "max", "max_groups", "max_participants", "max_subject", "mechanism", "media", "message", "message_acks", "method", "microsoft", "missing", "modify", "mute", "name", "nokia", "none", "not-acceptable", "not-allowed", "not-authorized", "notification", "notify", "off", "offline", "order", "owner", "owning", "paid", "participant", "participants", "participating", "password", "paused", "picture", "pin", "ping", "platform", "pop_mean_time", "pop_plus_minus", "port", "presence", "preview", "probe", "proceed", "prop", "props", "p_o", "p_t", "query", "raw", "reason", "receipt", "receipt_acks", "received", "registration", "relay", "remote-server-timeout", "remove", "Replaced by new connection", "request", "required", "resource", "resource-constraint", "response", "result", "retry", "rim", "s.whatsapp.net", "s.us", "seconds", "server", "server-error", "service-unavailable", "set", "show", "sid", "silent", "sound", "stamp", "unsubscribe", "stat", "status", "stream:error", "stream:features", "subject", "subscribe", "success", "sync", "system-shutdown", "s_o", "s_t", "t", "text", "timeout", "TimePassing.caf", "timestamp", "to", "Tri-tone.caf", "true", "type", "unavailable", "uri", "url", "urn:ietf:params:xml:ns:xmpp-sasl", "urn:ietf:params:xml:ns:xmpp-stanzas", "urn:ietf:params:xml:ns:xmpp-streams", "urn:xmpp:delay", "urn:xmpp:ping", "urn:xmpp:receipts", "urn:xmpp:whatsapp", "urn:xmpp:whatsapp:account", "urn:xmpp:whatsapp:dirty", "urn:xmpp:whatsapp:mms", "urn:xmpp:whatsapp:push", "user", "username", "value", "vcard", "version", "video", "w", "w:g", "w:p", "w:p:r", "w:profile:picture", "wait", "x", "xml-not-well-formed", "xmlns", "xmlns:stream", "Xylophone.caf", "1", "WAUTH-1" ]
	
	
	#unsupported yet:
	''',"true","after","before", "broadcast","count","features","first", "index","invalid-mechanism", "last","max","offline", "proceed","required","sync","elapsed","ip","microsoft","mute","nokia","off","pin","pop_mean_time","pop_plus_minus","port","reason", "server-error","silent","timout", "lc", "lg", "bad-protocol", "none", "remote-server-timeout", "service-unavailable", "w:p", "w:profile:picture", "notification"];'''
	nonce_key = "nonce=\""
	
	
	loginSuccess = QtCore.Signal()
	loginFailed = QtCore.Signal()
	connectionError = QtCore.Signal()
	
	
	def __init__(self,conn,reader,writer,digest):
		super(WALogin,self).__init__();
		
		WADebug.attach(self);
		
		self.conn = conn
		self.out = writer;
		self.inn = reader;
		self.digest = digest;
		
		self._d("WALOGIN INIT");
		
		
	
	def setConnection(self, conn):
		self.connection = conn;



	def run(self):
	
		HOST, PORT = 'bin-nokia.whatsapp.net', 443
		try:
			self.conn.connect((HOST, PORT));
			
			self.conn.connected = True
			self._d("Starting stream");
			self.out.streamStart(self.connection.domain,self.connection.resource);
	
			self.sendFeatures();
			self._d("Sent Features");
			self.sendAuth();
			self._d("Sent Auth");
			self.inn.streamStart();
			self._d("read stream start");
			challengeData = self.readFeaturesAndChallenge();
			self._d("read features and challenge");
			#self._d(challengeData);
			self.sendResponse(challengeData);
			self._d("read stream start");
		
			self.readSuccess();
			#print self.out.out.recv(1638400);
			#sock.send(string)
			#reply = sock.recv(16384)  # limit reply to 16K
			
		except socket.error:
			return self.connectionError.emit()
		except ConnectionClosedException:
			return self.connectionError.emit()
		
	
	def sendFeatures(self):
		toWrite = ProtocolTreeNode("stream:features",None,[ ProtocolTreeNode("receipt_acks",None,None),ProtocolTreeNode("w:profile:picture",{"type":"all"},None), ProtocolTreeNode("w:profile:picture",{"type":"group"},None),ProtocolTreeNode("notification",{"type":"participant"},None), ProtocolTreeNode("status",None,None) ]);
		#toWrite = ProtocolTreeNode("stream:features",None,[ProtocolTreeNode("receipt_acks",None,None),ProtocolTreeNode("w:profile:picture",{"type":"all"},None), ProtocolTreeNode("w:profile:picture",{"type":"group"},None)]);
		#toWrite = ProtocolTreeNode("stream:features",None,[ ProtocolTreeNode("receipt_acks",None,None) ]);
		self.out.write(toWrite);
		#self.out.out.write(0); #HACK
		#self.out.out.write(7); #HACK
		#self.out
		
	def sendAuth(self):
		# "user":self.connection.user,
		node = ProtocolTreeNode("auth",{"xmlns":"urn:ietf:params:xml:ns:xmpp-sasl","mechanism":"DIGEST-MD5-1"});
		self.out.write(node);
		
	def readFeaturesAndChallenge(self):
		server_supports_receipt_acks = True;
		root = self.inn.nextTree();
		
		while root is not None:
			if ProtocolTreeNode.tagEquals(root,"stream:features"):
				self._d("GOT FEATURES !!!!");
				server_supports_receipt_acks = root.getChild("receipt_acks") is not None;
				root = self.inn.nextTree();
				
				continue;
			
			if ProtocolTreeNode.tagEquals(root,"challenge"):
				self._d("GOT CHALLENGE !!!!");
				self.connection.supports_receipt_acks = self.connection.supports_receipt_acks and server_supports_receipt_acks;
				#String data = new String(Base64.decode(root.data.getBytes()));
				data = base64.b64decode(root.data);
				return data;
		raise Exception("fell out of loop in readFeaturesAndChallenge");
		
		
	def sendResponse(self,challengeData):
		#self.out.out.write(0);  #HACK
		#self.out.out.write(255); #HACK
		response = self.getResponse(challengeData);
		node = ProtocolTreeNode("response",{"xmlns":"urn:ietf:params:xml:ns:xmpp-sasl"}, None, str(base64.b64encode(response)));
		#print "THE NODE::";
		#print node.toString();
		#exit();
		self.out.write(node);
		#clear buf
		self.inn.inn.buf = [];
	
	def getResponse(self,challenge):
		print "CHALLENGE: " + str(challenge)
		i = challenge.index(WALogin.nonce_key);
		
		i+=len(WALogin.nonce_key);
		j = challenge.index('"',i);
		
		nonce = challenge[i:j];
		cnonce = Utilities.str(abs(random.getrandbits(64)),36);
		nc = "00000001";
		bos = ByteArray();
		bos.write(self.md5Digest(self.connection.user + ":" + self.connection.domain + ":" + self.connection.password));
		bos.write(58);
		bos.write(nonce);
		bos.write(58);
		bos.write(cnonce);
		
		digest_uri = "xmpp/"+self.connection.domain;

		A1 = bos.toByteArray();
		A2 = "AUTHENTICATE:" + digest_uri;

		KD = str(self.bytesToHex(self.md5Digest(A1.getBuffer()))) + ":"+nonce+":"+nc+":"+cnonce+":auth:"+str(self.bytesToHex(self.md5Digest(A2)));

		response = str(self.bytesToHex(self.md5Digest(KD)));
		bigger_response = "";
		bigger_response += "realm=\"";
		bigger_response += self.connection.domain
		bigger_response += "\",response=";
		bigger_response += response
		bigger_response += ",nonce=\"";
		bigger_response += nonce
		bigger_response += "\",digest-uri=\""
		bigger_response += digest_uri
		bigger_response += "\",cnonce=\""
		bigger_response += cnonce
		bigger_response += "\",qop=auth";
		bigger_response += ",username=\""
		bigger_response += self.connection.user
		bigger_response += "\",nc="
		bigger_response += nc

		print "SENDING: " + str(bigger_response)
		return bigger_response;

	
	def forDigit(self, b):
		if b < 10:
			return (48+b);
		
		return (97+b-10);
	
	
	def bytesToHex(self,bytes):
		ret = bytearray(len(bytes)*2);
		i = 0;
		for c in range(0,len(bytes)):	
			ub = bytes[c];
			if ub < 0:
				ub+=256;
			ret[i] = self.forDigit(ub >> 4);
			i+=1;
			ret[i] = self.forDigit(ub % 16);
			i+=1;
		
		return ret;
			

	def md5Digest(self,inputx):
		self.digest.reset();
		self.digest.update(inputx);
		return self.digest.digest();	
	
	
	
	def readSuccess(self):
		node = self.inn.nextTree();
		self._d("Login Status: %s"%(node.tag));
		
		
		
		if ProtocolTreeNode.tagEquals(node,"failure"):
			self.loginFailed.emit()
			raise Exception("Login Failure");
		
		ProtocolTreeNode.require(node,"success");
		
		expiration = node.getAttributeValue("expiration");
		
		
		if expiration is not None:
			self._d("Expires: "+str(expiration));
			self.connection.expire_date = expiration;
			
	
		kind = node.getAttributeValue("kind");
		self._d("Account type: %s"%(kind))
		
		if kind == "paid":
			self.connection.account_kind = 1;
		elif kind == "free":
			self.connection.account_kind = 0;
		else:
			self.connection.account_kind = -1;
			
		status = node.getAttributeValue("status");
		self._d("Account status: %s"%(status));
		
		if status == "expired":
			self.loginFailed.emit()
			raise Exception("Account expired on "+str(self.connection.expire_date));
		
		if status == "active":
			if expiration is None:	
				#raise Exception ("active account with no expiration");
				'''@@TODO expiration changed to creation'''
		else:
			self.connection.account_kind = 1;

		self.inn.inn.buf = [];
		
		self.loginSuccess.emit()
	
if __name__ == "__main__":
	w = WALogin(1,2,3)

########NEW FILE########
__FILENAME__ = wamanager
'''
Copyright (c) 2012, Tarek Galal <tarek@wazapp.im>

This file is part of Wazapp, an IM application for Meego Harmattan platform that
allows communication with Whatsapp users

Wazapp is free software: you can redistribute it and/or modify it under the 
terms of the GNU General Public License as published by the Free Software 
Foundation, either version 2 of the License, or (at your option) any later 
version.

Wazapp is distributed in the hope that it will be useful, but WITHOUT ANY 
WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS FOR A 
PARTICULAR PURPOSE. See the GNU General Public License for more details.

You should have received a copy of the GNU General Public License along with 
Wazapp. If not, see http://www.gnu.org/licenses/.
'''
import sys,os, shutil
from PySide.QtCore import *
from PySide.QtGui import *
from PySide.QtDeclarative import QDeclarativeView

from PySide.QtGui import QApplication

from ui import WAUI;
from litestore import LiteStore as DataStore
from accountsmanager import AccountsManager;
import dbus
from utilities import Utilities
from wadebug import WADebug
from constants import WAConstants

class WAManager():

	def __init__(self,app):
		self.app = app;
		WADebug.attach(self)
		
		self._d("wazapp %s"%Utilities.waversion)
		
		
		try:
			bus = dbus.SessionBus()
			remote_object = bus.get_object("com.tgalal.meego.Wazapp.WAService", "/")
			self._d("Found a running instance. I will show it instead of relaunching.")
			remote_object.show();
			sys.exit();
		except dbus.exceptions.DBusException as e:
			self._d("No running instance found. Proceeding with relaunch")
			self.proceed()
			
		
		
	def regFallback(self):		
		os.system("exec /usr/bin/invoker -w --type=e --single-instance /usr/lib/AccountSetup/bin/waxmppplugin &")
		
	def processVersionTriggers(self):
		'''
			ONLY FOR MASTER VERSIONS, NO TRIGGERS FOR ANY DEV VERSIONS
			Triggers are executed in ascending order of versions.
			Versions added to triggerables, must have a corresponding function in this format:
				version x.y.z corresponds to function name: t_x_y_z
		'''

		def t_0_9_12():
			#clear cache
			if os.path.isdir(WAConstants.CACHE_PATH):
				shutil.rmtree(WAConstants.CACHE_PATH, True)
				self.createDirs()		
		
		
		triggerables = ["0.9.12", Utilities.waversion]
		
		self._d("Processing version triggers")
		for v in triggerables:
			if not self.isPreviousVersion(v):
				self._d("Running triggers for %s"%v)
				try:
					fname = "t_%s" % v.replace(".","_")
					eval("%s()"%fname)
					self.touchVersion(v)
				except NameError:
					self._d("Couldn't find associated function, skipping triggers for %s"%v)
					pass
			else:
				self._d("Nothing to do for %s"%v)

	
	def isPreviousVersion(self, v):

		checkPath = WAConstants.VHISTORY_PATH+"/"+v
		return os.path.isfile(checkPath)
			
	def touchVersion(self, v):
		f = open(WAConstants.VHISTORY_PATH+"/"+v, 'w')
		f.close()

	def createDirs(self):
		
		dirs = [
			WAConstants.STORE_PATH,
			WAConstants.VHISTORY_PATH,
			WAConstants.APP_PATH,
			WAConstants.MEDIA_PATH,
			WAConstants.AUDIO_PATH,
			WAConstants.IMAGE_PATH,
			WAConstants.VIDEO_PATH,
			WAConstants.VCARD_PATH,

			WAConstants.CACHE_PATH,
			WAConstants.CACHE_PROFILE,
			WAConstants.CACHE_CONTACTS,
			WAConstants.CACHE_CONV,
			
			WAConstants.THUMBS_PATH
			]
		
		for d in dirs:
			self.createDir(d)
		
		
	def createDir(self, d):
		if not os.path.exists(d):
			os.makedirs(d)
		
	
	def proceed(self):
		account = AccountsManager.getCurrentAccount();
		self._d(account)
	
	
		if(account is None):
			#self.d("Forced reg");
			self.regFallback()
			sys.exit()
			return
			#gui.forceRegistration();
			#self.app.exit();
			
		imsi = Utilities.getImsi();
		store = DataStore(imsi);
		
		if store.status == False:
			#or exit
			store.reset();
			
		
		store.prepareGroupConversations();
		store.prepareMedia()
		store.updateDatabase()
		store.initModels()
		
		gui = WAUI(account.jid);
		gui.setAccountPushName(account.pushName)
		#url = QUrl('/opt/waxmppplugin/bin/wazapp/UI/main.qml')
		#gui.setSource(url)
		gui.initConnections(store);
	
		self.app.focusChanged.connect(gui.focusChanged)
		gui.engine().quit.connect(QApplication.instance().quit);

		#gui.populatePhoneContacts();
		
		
		print "SHOW FULL SCREEN"
		gui.showFullScreen();
		
		gui.onProcessEventsRequested()
		
				
		self.createDirs()
		
		
		self.processVersionTriggers()

		gui.populateContacts("ALL");
		
		gui.populateConversations();
		
		gui.populatePhoneContacts()
		
		gui.initializationDone = True
		gui.initialized.emit()
		
		
		print "INIT CONNECTION"
		gui.initConnection();
		#splash.finish(gui);
		gui.setMyAccount(account.jid);

		self.gui = gui;
		
		self.gui.whatsapp.eventHandler.setMyAccount(account.jid)
		

########NEW FILE########
__FILENAME__ = wamediahandler
'''
Copyright (c) 2012, Tarek Galal <tarek@wazapp.im>

This file is part of Wazapp, an IM application for Meego Harmattan platform that
allows communication with Whatsapp users

Wazapp is free software: you can redistribute it and/or modify it under the 
terms of the GNU General Public License as published by the Free Software 
Foundation, either version 2 of the License, or (at your option) any later 
version.

Wazapp is distributed in the hope that it will be useful, but WITHOUT ANY 
WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS FOR A 
PARTICULAR PURPOSE. See the GNU General Public License for more details.

You should have received a copy of the GNU General Public License along with 
Wazapp. If not, see http://www.gnu.org/licenses/.
'''

from PySide import QtCore
from PySide.QtCore import QObject, QThread, Qt
from PySide.QtGui import QImage
from constants import WAConstants
from wadebug import WADebug
import os
import mimetypes
import shutil, sys
from time import gmtime, strftime

from Yowsup.Media.downloader import MediaDownloader
from Yowsup.Media.uploader import MediaUploader
from utilities import async, Utilities


class WAMediaHandler(QObject):
	progressUpdated = QtCore.Signal(int,int) #%,progress,mediaid
	error = QtCore.Signal(str,int)
	success = QtCore.Signal(str,int,str,str, str)
	
	def __init__(self,jid,message_id,url,mediaType_id,mediaId,account,resize=False):
		
		WADebug.attach(self);
		path = self.getSavePath(mediaType_id);
		
		filename = url.split('/')[-1]
		
		if path is None:
			raise Exception("Unknown media type")
		
		if not os.path.exists(path):
			os.makedirs(path)
		
		
		self.uploadHandler = MediaUploader(jid, account, self.onUploadSuccess, self.onError, self.onProgressUpdated)
		self.downloadHandler = MediaDownloader(self.onDownloadSuccess, self.onError, self.onProgressUpdated)

		self.url = url
		self._path = path+"/"+filename

		ext = os.path.splitext(filename)[1]

		self.downloadPath = Utilities.getUniqueFilename(path + "/" + self.getFilenamePrefix(mediaType_id) + ext)

		self.resize = resize
		self.mediaId = mediaId
		self.message_id = message_id
		self.jid = jid

		super(WAMediaHandler,self).__init__();
	

	def onError(self):
		self.error.emit(self.jid,self.message_id)
	
	def onUploadSuccess(self, url):

		#filename = os.path.basename(self._path)
		#filesize = os.path.getsize(self._path)
		#data = url + "," + filename + "," + str(filesize);
		self.success.emit(self.jid,self.message_id, self._path, "upload", url)

	def onDownloadSuccess(self, path):
		try:
			shutil.copyfile(path, self.downloadPath)
			os.remove(path)
			self.success.emit(self.jid, self.message_id, self.downloadPath, "download", "")
		except:
			print("Error occured at transfer %s"%sys.exc_info()[1])
			self.error.emit(self.jid, self.message_id)

	def onProgressUpdated(self,progress):
		self.progressUpdated.emit(progress, self.mediaId);

	@async
	def pull(self):
		self.action = "download"
		self.downloadHandler.download(self.url)

	@async
	def push(self, uploadUrl):
		self.action = "upload"

		path = self.url.replace("file://","")

		filename = os.path.basename(path)
		filetype = mimetypes.guess_type(filename)[0]
		
		self._path = path
		self.uploadHandler.upload(path, uploadUrl)
	
	def getFilenamePrefix(self, mediatype_id):
		if mediatype_id == WAConstants.MEDIA_TYPE_IMAGE:
			return strftime("owhatsapp_image_%Y%m%d_%H%M%S", gmtime())
		
		if mediatype_id == WAConstants.MEDIA_TYPE_AUDIO:
			return strftime("owhatsapp_audio_%Y%m%d_%H%M%S", gmtime())
		
		if mediatype_id == WAConstants.MEDIA_TYPE_VIDEO:
			return strftime("owhatsapp_video_%Y%m%d_%H%M%S", gmtime())

		if mediatype_id == WAConstants.MEDIA_TYPE_VCARD:
			return strftime("owhatsapp_vcard_%Y%m%d_%H%M%S", gmtime())
			
		return ""
	
	def getSavePath(self,mediatype_id):
		
		if mediatype_id == WAConstants.MEDIA_TYPE_IMAGE:
			return WAConstants.IMAGE_PATH
		
		if mediatype_id == WAConstants.MEDIA_TYPE_AUDIO:
			return WAConstants.AUDIO_PATH
		
		if mediatype_id == WAConstants.MEDIA_TYPE_VIDEO:
			return WAConstants.VIDEO_PATH

		if mediatype_id == WAConstants.MEDIA_TYPE_VCARD:
			return WAConstants.VCARD_PATH
			
		return None

########NEW FILE########
__FILENAME__ = warequest
'''
Copyright (c) 2012, Tarek Galal <tarek@wazapp.im>

This file is part of Wazapp, an IM application for Meego Harmattan platform that
allows communication with Whatsapp users

Wazapp is free software: you can redistribute it and/or modify it under the 
terms of the GNU General Public License as published by the Free Software 
Foundation, either version 2 of the License, or (at your option) any later 
version.

Wazapp is distributed in the hope that it will be useful, but WITHOUT ANY 
WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS FOR A 
PARTICULAR PURPOSE. See the GNU General Public License for more details.

You should have received a copy of the GNU General Public License along with 
Wazapp. If not, see http://www.gnu.org/licenses/.
'''
import httplib,urllib
from xml.dom import minidom

import threading
from PySide import QtCore
from PySide.QtCore import QThread

from wadebug import WADebug

class WARequest(QThread):


	#BASE_URL = [ 97, 61, 100, 123, 114, 103, 96, 114, 99, 99, 61, 125, 118, 103 ];
	status = None
	result = None
	params = []
	#v = "v1"
	#method = None
	conn = None
	
	done = QtCore.Signal(str);
	fail = QtCore.Signal();
	
	def __init__(self):
		WADebug.attach(self);
		super(WARequest,self).__init__();
	
	def onResponse(self, name, value):
		if name == "status":
			self.status = value
		elif name == "result":
			self.result = value
			
	def addParam(self,name,value):
		self.params.append({name:value.encode('utf-8')});

	def clearParams(self):
		self.params = []
	
	def getUrl(self):
		return  self.base_url+self.req_file;

	def getUserAgent(self):
		#agent = "WhatsApp/1.2 S40Version/microedition.platform";
		agent = "WhatsApp/2.8.4 S60Version/5.2 Device/C7-00";
		return agent;	
	
	

	def sendRequest(self):


		
		self.params =  [param.items()[0] for param in self.params];
		
		params = urllib.urlencode(self.params);
		
		self._d("Opening connection to "+self.base_url);
		self.conn = httplib.HTTPSConnection(self.base_url,443);
		headers = {"User-Agent":self.getUserAgent(),
			"Content-Type":"application/x-www-form-urlencoded",
			"Accept":"text/xml"
			};
		
		self._d(headers);
		self._d(params);
		
		self.conn.request("POST",self.req_file,params,headers);
		resp=self.conn.getresponse()
 		response=resp.read();
 		self._d(response);
 		doc = minidom.parseString(response);
 		self.done.emit(response);
 		return response;
		#response_node  = doc.getElementsByTagName("response")[0];

		#for (name, value) in response_node.attributes.items():
		#self.onResponse(name,value);

########NEW FILE########
__FILENAME__ = waservice
# -*- coding: utf-8 -*-
'''
Copyright (c) 2012, Tarek Galal <tarek@wazapp.im>

This file is part of Wazapp, an IM application for Meego Harmattan platform that
allows communication with Whatsapp users

Wazapp is free software: you can redistribute it and/or modify it under the 
terms of the GNU General Public License as published by the Free Software 
Foundation, either version 2 of the License, or (at your option) any later 
version.

Wazapp is distributed in the hope that it will be useful, but WITHOUT ANY 
WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS FOR A 
PARTICULAR PURPOSE. See the GNU General Public License for more details.

You should have received a copy of the GNU General Public License along with 
Wazapp. If not, see http://www.gnu.org/licenses/.
'''
# Dependency on PySide for encoding/decoding like MRemoteAction
from PySide.QtCore import QBuffer, QIODevice, QDataStream, QByteArray
from PySide.QtCore import QCoreApplication


# Python D-Bus Library dependency for communcating with the service
import dbus
import dbus.service
import dbus.mainloop
import dbus.glib
import sys,os

# MRemoteAction::toString()
# http://apidocs.meego.com/1.0/mtf/mremoteaction_8cpp_source.html
def qvariant_encode(value):
    buffer = QBuffer()
    buffer.open(QIODevice.ReadWrite)
    stream = QDataStream(buffer)
    stream.writeQVariant(value)
    buffer.close()
    return buffer.buffer().toBase64().data().strip()

# MRemoteAction::fromString()
# http://apidocs.meego.com/1.0/mtf/mremoteaction_8cpp_source.html
def qvariant_decode(data):
    byteArray = QByteArray.fromBase64(data)
    buffer = QBuffer(byteArray)
    buffer.open(QIODevice.ReadOnly)
    stream = QDataStream(buffer)
    result = stream.readQVariant()
    buffer.close()
    return result
    
    
class WAService(dbus.service.Object):

    DEFAULT_NAME = 'com.tgalal.meego.Wazapp'
    DEFAULT_PATH = '/'
    DEFAULT_INTF = 'com.tgalal.meego.Wazapp'
    
    
    
    def __init__(self,ui):
        source_name = "WAService"
        self.ui = ui
        dbus_main_loop = dbus.glib.DBusGMainLoop(set_as_default=True)
        session_bus = dbus.SessionBus(dbus_main_loop)
        self.userId = os.geteuid();
        
        self.local_name = '.'.join([self.DEFAULT_NAME, source_name])
        bus_name = dbus.service.BusName(self.local_name, bus=session_bus)
        
        dbus.service.Object.__init__(self,object_path=self.DEFAULT_PATH,bus_name=bus_name)

    
    @dbus.service.method(DEFAULT_INTF)
    def launch(self):
        self.ui.showFullScreen();
    
    @dbus.service.method(DEFAULT_INTF)
    def show(self):
        self.ui.showFullScreen();

########NEW FILE########
__FILENAME__ = watime
'''
Copyright (c) 2012, Tarek Galal <tarek@wazapp.im>

This file is part of Wazapp, an IM application for Meego Harmattan platform that
allows communication with Whatsapp users

Wazapp is free software: you can redistribute it and/or modify it under the 
terms of the GNU General Public License as published by the Free Software 
Foundation, either version 2 of the License, or (at your option) any later 
version.

Wazapp is distributed in the hope that it will be useful, but WITHOUT ANY 
WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS FOR A 
PARTICULAR PURPOSE. See the GNU General Public License for more details.

You should have received a copy of the GNU General Public License along with 
Wazapp. If not, see http://www.gnu.org/licenses/.
'''
import time,datetime,re
from dateutil import tz

class WATime():
	def parseIso(self,iso):
		d=datetime.datetime(*map(int, re.split('[^\d]', iso)[:-1]))
		return d
		
	def utcToLocal(self,dt):
		utc = tz.gettz('UTC');
		local = tz.tzlocal()
		dtUtc =  dt.replace(tzinfo=utc);
		
		return dtUtc.astimezone(local)
	
	def datetimeToTimestamp(self,dt):
		return time.mktime(dt.timetuple());
		

if __name__=="__main__":
	ds = "2012-06-16T15:24:36Z"
	watime = WATime();
	
	print ds
	
	parsed = watime.parseIso(ds)
	print parsed
	
	local = watime.utcToLocal(parsed)
	print local
	
	stamp = watime.datetimeToTimestamp(local)
	print stamp
	
	

########NEW FILE########
__FILENAME__ = waupdater
'''
Copyright (c) 2012, Tarek Galal <tarek@wazapp.im>

This file is part of Wazapp, an IM application for Meego Harmattan platform that
allows communication with Whatsapp users

Wazapp is free software: you can redistribute it and/or modify it under the 
terms of the GNU General Public License as published by the Free Software 
Foundation, either version 2 of the License, or (at your option) any later 
version.

Wazapp is distributed in the hope that it will be useful, but WITHOUT ANY 
WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS FOR A 
PARTICULAR PURPOSE. See the GNU General Public License for more details.

You should have received a copy of the GNU General Public License along with 
Wazapp. If not, see http://www.gnu.org/licenses/.
'''
from wajsonrequest import WAJsonRequest
from PySide import QtCore
from distutils.version import StrictVersion
from utilities import Utilities

from wadebug import UpdaterDebug;
import time, sys

class WAUpdater(WAJsonRequest):
	updateAvailable = QtCore.Signal(dict)
	
	def __init__(self):
		_d = UpdaterDebug();
		self._d = _d.d
		
		self.base_url = "wazapp.im"
		self.req_file = "/whatsup/"
		
		self.interval = 60*60 #seconds
		
	
		super(WAUpdater,self).__init__();
	
	def run(self):
		while True:
			self._d("Checking for updates")
			try:
				res = self.sendRequest()
				if res:
					#current = self.version.split('.');
					#latest = res['v'].split('.')
					curr = Utilities.waversion
					test = curr.split('.');
					
					if len(test) == 4:
						curr = '.'.join(test[:3])
						
					if StrictVersion(str(res['l'])) > curr:
						self._d("UPDATE AVAILABLE!")
						self.updateAvailable.emit(res)
			except:
					self._d("Coudn't check for updates error thrown: %s" %  sys.exc_info()[1])

			time.sleep(self.interval)
			
					

########NEW FILE########
__FILENAME__ = waxmpp
# -*- coding: utf-8 -*-
'''
Copyright (c) 2012, Tarek Galal <tarek@wazapp.im>

This file is part of Wazapp, an IM application for Meego Harmattan platform that
allows communication with Whatsapp users

Wazapp is free software: you can redistribute it and/or modify it under the 
terms of the GNU General Public License as published by the Free Software 
Foundation, either version 2 of the License, or (at your option) any later 
version.

Wazapp is distributed in the hope that it will be useful, but WITHOUT ANY 
WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS FOR A 
PARTICULAR PURPOSE. See the GNU General Public License for more details.

You should have received a copy of the GNU General Public License along with 
Wazapp. If not, see http://www.gnu.org/licenses/.
'''
#from InterfaceHandlers.DBus.DBusInterfaceHandler import DBusInterfaceHandler
from InterfaceHandlers.Lib.LibInterfaceHandler import LibInterfaceHandler

from PySide import QtCore
from PySide.QtCore import Qt, QObject, QTimer
from PySide.QtGui import QApplication, QImage, QPixmap, QTransform
from connmon import ConnMonitor
from constants import WAConstants
from messagestore import Key
from notifier import Notifier
from time import sleep
from wadebug import WADebug
from wamediahandler import WAMediaHandler
from waupdater import WAUpdater
import base64
import hashlib
import os
import shutil, datetime
import thread
import Image
from PIL.ExifTags import TAGS
from Context.Provider import *
from HTMLParser import HTMLParser
from utilities import Utilities, async
import time

class MLStripper(HTMLParser):
    def __init__(self):
        self.reset()
        self.fed = []
    def handle_data(self, d):
        self.fed.append(d)
    def get_data(self):
        return ''.join(self.fed)


class WAEventHandler(QObject):
	
	connecting = QtCore.Signal()
	connected = QtCore.Signal();
	sleeping = QtCore.Signal();
	disconnected = QtCore.Signal();
	loginFailed = QtCore.Signal()
	######################################
	new_message = QtCore.Signal(dict);
	typing = QtCore.Signal(str);
	paused = QtCore.Signal(str);
	available = QtCore.Signal(str);
	unavailable = QtCore.Signal(str);
	showUI = QtCore.Signal(str);
	messageSent = QtCore.Signal(int,str);
	messageDelivered = QtCore.Signal(int,str);
	lastSeenUpdated = QtCore.Signal(str,int);
	updateAvailable = QtCore.Signal(dict);
	
	##############Media#####################
	mediaTransferSuccess = QtCore.Signal(int,str)
	mediaTransferError = QtCore.Signal(int)
	mediaTransferProgressUpdated = QtCore.Signal(int,int)
	#########################################
	
	sendTyping = QtCore.Signal(str);
	sendPaused = QtCore.Signal(str);
	getLastOnline = QtCore.Signal(str);
	getGroupInfo = QtCore.Signal(str);
	createGroupChat = QtCore.Signal(str);
	groupCreated = QtCore.Signal(str);
	groupCreateFailed = QtCore.Signal(int);
	groupInfoUpdated = QtCore.Signal(str,str)
	addParticipants = QtCore.Signal(str, str);
	addedParticipants = QtCore.Signal();
	removeParticipants = QtCore.Signal(str, str);
	removedParticipants = QtCore.Signal();
	getGroupParticipants = QtCore.Signal(str);
	groupParticipants = QtCore.Signal(str, str);
	endGroupChat = QtCore.Signal(str);
	groupEnded = QtCore.Signal();
	setGroupSubject = QtCore.Signal(str, str);
	groupSubjectChanged = QtCore.Signal(str);
	getPictureIds = QtCore.Signal(str);
	profilePictureUpdated = QtCore.Signal(str);
	setPushName = QtCore.Signal(str, str);
	imageRotated = QtCore.Signal(str);
	getPicturesFinished = QtCore.Signal();
	changeStatus = QtCore.Signal(str);
	setMyPushName = QtCore.Signal(str);
	statusChanged = QtCore.Signal();

	def __init__(self,conn):
		
		WADebug.attach(self);
		self.conn = conn;
		super(WAEventHandler,self).__init__();
		
		self.notifier = Notifier();
		self.connMonitor = ConnMonitor();
		
		self.connMonitor.connected.connect(self.networkAvailable);
		self.connMonitor.disconnected.connect(self.networkDisconnected);
		
		self.account = "";

		self.blockedContacts = [];

		self.resizeImages = False;
		self.disconnectRequested = False

		#self.interfaceHandler = LibInterfaceHandler()
		
		self.jid = self.conn.jid
		
		self.username = self.jid.split('@')[0]

		self.interfaceHandler = LibInterfaceHandler(self.username)
		self.registerInterfaceSignals()
		
		self.interfaceVersion = self.interfaceHandler.call("getVersion")
		
		self._d("Using Yowsup version %s"%self.interfaceVersion)

		
		self.listJids = [];

		self.mediaHandlers = []
		self.sendTyping.connect(lambda *args: self.interfaceHandler.call("typing_send", args));
		self.sendPaused.connect(lambda *args: self.interfaceHandler.call("typing_paused",args));
		self.getLastOnline.connect(lambda *args: self.interfaceHandler.call("presence_request", args));
		self.getGroupInfo.connect(lambda *args: self.interfaceHandler.call("group_getInfo", args));
		self.createGroupChat.connect(lambda *args: self.interfaceHandler.call("group_create", args));
		self.addParticipants.connect(lambda *args: self.interfaceHandler.call("group_addParticipants", args));
		self.removeParticipants.connect(lambda *args: self.interfaceHandler.call("group_removeParticipants", args));
		self.getGroupParticipants.connect(lambda *args: self.interfaceHandler.call("group_getParticipants", args));
		self.endGroupChat.connect(lambda *args: self.interfaceHandler.call("group_end", args));
		self.setGroupSubject.connect(lambda jid, subject: self.interfaceHandler.call("group_setSubject", (jid, subject.decode("unicode_escape").encode('utf-8'))));
		self.getPictureIds.connect(lambda *args: self.interfaceHandler.call("picture_getIds", args));
		self.changeStatus.connect(lambda status: self.interfaceHandler.call("profile_setStatus", (status.decode("unicode_escape").encode('utf-8'),)));
		self.setMyPushName.connect(lambda pushname: self.interfaceHandler.call("presence_sendAvailableForChat", (pushname.encode('utf-8'),)));


		self.state = 0
		
		self.updater = None
		
		self.mediaRef = {}
		
		
	############### NEW BACKEND STUFF
	def strip(self, text):
		n = text.find("</body>")
		if (n != -1): #there are no dead body to hide, sometimes.
			text = text[:n]
		text = text.replace("text-indent:0px;\"></br >", "text-indent:0px;\">")
		text = text.split("</p>")[0].split("text-indent:0px;\">")[1]
		text = text.strip()
		return text;

	def authSuccess(self, username):
		WAXMPP.contextproperty.setValue('online')
		self.state = 2
		self.connected.emit()
		print "AUTH SUCCESS"
		print username

		#self.interfaceHandler.initSignals(connId)
		#self.interfaceHandler.initMethods(connId)

		#self.registerInterfaceSignals()

		self.interfaceHandler.call("ready")

		self.resendUnsent()

	def authComplete(self):
		pass

	def authConnFail(self,username, err):
		self.state = 0
		print "Auth connection failed"
		print err
		if self.connMonitor.isOnline():
			QTimer.singleShot(5000, lambda: self.networkAvailable() if self.connMonitor.isOnline() else False)


	def authFail(self, username, err):
		self.state = 0
		self.loginFailed.emit()
		print "AUTH FAILED FOR %s!!" % username


	def registerInterfaceSignals(self):
		self.interfaceHandler.connectToSignal("message_received", self.onMessageReceived)
		self.interfaceHandler.connectToSignal("group_messageReceived", self.onMessageReceived)
		#self.registerSignal("status_dirty", self.statusDirtyReceived) #ignored by whatsapp?
		self.interfaceHandler.connectToSignal("receipt_messageSent", self.onMessageSent)
		self.interfaceHandler.connectToSignal("receipt_messageDelivered", self.onMessageDelivered)
		self.interfaceHandler.connectToSignal("receipt_visible", self.onMessageDelivered) #@@TODO check
		self.interfaceHandler.connectToSignal("presence_available", self.presence_available_received)
		self.interfaceHandler.connectToSignal("presence_unavailable", self.presence_unavailable_received)
		self.interfaceHandler.connectToSignal("presence_updated", self.onLastSeen)

		self.interfaceHandler.connectToSignal("contact_gotProfilePictureId", self.onProfilePictureIdReceived)
		self.interfaceHandler.connectToSignal("contact_gotProfilePicture", self.onGetPictureDone)
		self.interfaceHandler.connectToSignal("contact_typing", self.typing_received)
		self.interfaceHandler.connectToSignal("contact_paused", self.paused_received)

		self.interfaceHandler.connectToSignal("group_gotParticipants", self.onGroupParticipants)
		self.interfaceHandler.connectToSignal("group_createSuccess", self.onGroupCreated)
		self.interfaceHandler.connectToSignal("group_createFail", lambda errorCode: self.groupCreateFailed.emit(int(errorCode)))
		self.interfaceHandler.connectToSignal("group_endSuccess", self.onGroupEnded)
		self.interfaceHandler.connectToSignal("group_gotInfo", self.onGroupInfo)
		self.interfaceHandler.connectToSignal("group_infoError", self.onGroupInfoError)
		
		self.interfaceHandler.connectToSignal("group_addParticipantsSuccess", self.onAddedParticipants)
		self.interfaceHandler.connectToSignal("group_removeParticipantsSuccess", self.onRemovedParticipants)
		self.interfaceHandler.connectToSignal("group_setPictureSuccess",self.onSetGroupPicture)
		self.interfaceHandler.connectToSignal("group_setPictureError",self.onSetGroupPictureError)
		self.interfaceHandler.connectToSignal("group_gotPicture", self.onGetPictureDone)
		self.interfaceHandler.connectToSignal("group_subjectReceived", self.onGroupSubjectReceived)
		self.interfaceHandler.connectToSignal("group_setSubjectSuccess", self.onGroupSetSubjectSuccess)


		self.interfaceHandler.connectToSignal("notification_contactProfilePictureUpdated", self.onContactProfilePictureUpdatedNotification)
		self.interfaceHandler.connectToSignal("notification_groupParticipantAdded", self.onGroupParticipantAddedNotification)
		self.interfaceHandler.connectToSignal("notification_groupParticipantRemoved", self.onGroupParticipantRemovedNotification)
		self.interfaceHandler.connectToSignal("notification_groupPictureUpdated", self.onGroupPictureUpdatedNotification)
		
		self.interfaceHandler.connectToSignal("disconnected", self.onDisconnected)


		self.interfaceHandler.connectToSignal("image_received", self.onImageReceived)
		self.interfaceHandler.connectToSignal("group_imageReceived", self.onImageReceived)

		self.interfaceHandler.connectToSignal("audio_received", self.onAudioReceived)
		self.interfaceHandler.connectToSignal("group_audioReceived", self.onAudioReceived)

		self.interfaceHandler.connectToSignal("video_received", self.onVideoReceived)
		self.interfaceHandler.connectToSignal("group_videoReceived", self.onVideoReceived)

		self.interfaceHandler.connectToSignal("location_received", self.onLocationReceived)
		self.interfaceHandler.connectToSignal("group_locationReceived", self.onLocationReceived)
		
		self.interfaceHandler.connectToSignal("vcard_received", self.onVCardReceived)
		self.interfaceHandler.connectToSignal("group_vcardReceived", self.onVCardReceived)
		
		self.interfaceHandler.connectToSignal("message_error", self.onMessageError)
		
		self.interfaceHandler.connectToSignal("profile_setPictureSuccess", self.onSetProfilePicture)
		self.interfaceHandler.connectToSignal("profile_setPictureError", self.onSetProfilePictureError)
		
		self.interfaceHandler.connectToSignal("profile_setStatusSuccess", self.onProfileSetStatusSuccess)
		
		self.interfaceHandler.connectToSignal("auth_success", self.authSuccess)
		self.interfaceHandler.connectToSignal("auth_fail", self.authFail)
		
		
		self.interfaceHandler.connectToSignal("media_uploadRequestSuccess", self.onMediaUploadRequested)
		self.interfaceHandler.connectToSignal("media_uploadRequestFailed", self.onMediaUploadRequestFailed)
		self.interfaceHandler.connectToSignal("media_uploadRequestDuplicate", self.onMediaUploadRequestDuplicate)


	################################################################
	
	def quit(self):
		
		#self.connMonitor.exit()
		#self.conn.disconnect()
		
		'''del self.connMonitor
		del self.conn.inn
		del self.conn.out
		del self.conn.login
		del self.conn.stanzaReader'''
		#del self.conn
		WAXMPP.contextproperty.setValue('offline')
		self.interfaceHandler.call("disconnect")
		
	
	def initialConnCheck(self):
		if self.connMonitor.isOnline():
			self.connMonitor.connected.emit()
		else:
			self.connMonitor.createSession();
	
	def setMyAccount(self, account):
		self.account = account
	
	def onFocus(self):
		'''self.notifier.disable()'''
		
	def onUnfocus(self):
		'''self.notifier.enable();'''	
	
	def onLoginFailed(self):
		self.loginFailed.emit()
	
	def onLastSeen(self,jid,seconds):
		self._d("GOT LAST SEEN ON FROM %s"%(jid))
		
		if seconds is not None:
			self.lastSeenUpdated.emit(jid,int(seconds));


	def resendUnsent(self):
		'''
			Resends all unsent messages, should invoke on connect
		'''


		messages = WAXMPP.message_store.getUnsent();
		self._d("Resending %i old messages"%(len(messages)))
		for m in messages:
			media = m.getMedia()
			jid = m.getConversation().getJid()
			if media is not None:
				if media.transfer_status == 2:
					if media.mediatype_id == 6:
						vcard = self.readVCard(m.content)
						if vcard:
							resultId = self.interfaceHandler.call("message_vcardSend", (jid, vcard, m.content))
							k = Key(jid, True, resultId)
							m.key = k.toString()
							m.save()
										
					elif media.mediatype_id == 5:
						
							latitude,longitude = media.local_path.split(',')
							
							resultId = self.interfaceHandler.call("message_locationSend", (jid, latitude, longitude, media.preview))
							k = Key(jid, True, resultId)
							m.key = k.toString()
							m.save()
					else:
						media.transfer_status = 1
						media.save()
			else:
				try:
					msgId = self.interfaceHandler.call("message_send", (jid, m.content.encode('utf-8')))
					m.key = Key(jid, True, msgId).toString()
					m.save()
				except UnicodeDecodeError:
					self._d("skipped sending an old message because UnicodeDecodeError")

		self._d("Resending old messages done")

	def getDisplayPicture(self, jid = None):
		picture = "/opt/waxmppplugin/bin/wazapp/UI/common/images/user.png"
		if jid is None:
			return picture

		try:
			jid.index('-')
			jid = jid.replace("@g.us","")
			if os.path.isfile(WAConstants.CACHE_PATH+"/contacts/" + jid + ".png"):
				picture = WAConstants.CACHE_PATH+"/contacts/" + jid + ".png"
			else:
				picture =  WAConstants.DEFAULT_GROUP_PICTURE

		except ValueError:
			if jid is not None and os.path.isfile(WAConstants.CACHE_PATH+"/contacts/" + jid.replace("@s.whatsapp.net","") + ".png"):
				picture = WAConstants.CACHE_PATH+"/contacts/" + jid.replace("@s.whatsapp.net","") + ".png"
			else:
				picture = WAConstants.DEFAULT_CONTACT_PICTURE
		return picture



	##SECTION MESSAGERECEPTION##
	def preMessageReceived(fn):

		def wrapped(self, *args):
			messageId = args[0]
			jid = args[1]
			
			try:
				self.blockedContacts.index(jid);
				#self.interfaceHandler.call("message_ack", (jid, messageId))
				self._d("BLOCKED MESSAGE FROM " + jid)
				return
			except ValueError:
				pass

			if WAXMPP.message_store.messageExists(jid, messageId):
				self.interfaceHandler.call("message_ack", (jid, messageId))
				return



			key = Key(jid,False,messageId);
			msg = WAXMPP.message_store.createMessage(jid)

			author = jid
			isGroup = WAXMPP.message_store.isGroupJid(jid)
			if isGroup:
				author = args[2]

			msgContact =  WAXMPP.message_store.store.Contact.getOrCreateContactByJid(author)

			msg.Contact = msgContact
			msg.setData({"status":0,"key":key.toString(),"type":WAXMPP.message_store.store.Message.TYPE_RECEIVED});
			msg.contact_id = msgContact.id

			return fn(self,msg, *args[2:]) if author == jid else fn(self,msg, *args[3:]) #omits author as well if group

		return wrapped

	def postMessageReceived(fn):
		def wrapped(self, *args):
			message = fn(self, *args)
			contact = message.Contact#getContact()
			conversation = message.getConversation()


			msgPicture = self.getDisplayPicture(conversation.getJid())
			conversation.incrementNew()
			WAXMPP.message_store.pushMessage(conversation.getJid(), message)
			
			if contact.iscontact!="yes":
				self.setPushName.emit(contact.jid,contact.pushname)
				
			
			pushName = contact.pushname
			
			try:
				contact = WAXMPP.message_store.store.getCachedContacts()[contact.number];
			except:
				pass



			if conversation.isGroup():
				self.notifier.newGroupMessage(conversation.getJid(), "%s - %s"%(contact.name or pushName or contact.number,conversation.subject.decode("utf8") if conversation.subject else ""), message.content, msgPicture.encode('utf-8'),callback = self.notificationClicked);
			else:
				self.notifier.newSingleMessage(contact.jid, contact.name or pushName or contact.number, message.content, msgPicture.encode('utf-8'),callback = self.notificationClicked);

			if message.wantsReceipt:
				self.interfaceHandler.call("message_ack", (conversation.getJid(), eval(message.key).id))

		return wrapped
	
	@preMessageReceived
	def onMessageError(self,message,errorCode):
		self._d("Message Error {0}\n Error Code: {1}".format(message,str(errorCode)));
	
	@preMessageReceived
	@postMessageReceived
	def onMessageReceived(self, message, content, timestamp, wantsReceipt, pushName=""):

		contact = WAXMPP.message_store.store.Contact.getOrCreateContactByJid(message.getContact().jid)

		if contact.pushname!=pushName and pushName!="":
			self._d("Setting Push Name: "+pushName+" to "+contact.jid)
			contact.setData({"jid":contact.jid,"pushname":pushName})
			contact.save()
			message.Contact = contact

		if contact.pictureid == None:
			self.getPictureIds.emit(contact.jid)


		if content is not None:

			content = content#.encode('utf-8')
			message.timestamp = timestamp
			message.content = content
	
		message.pushname = pushName
		message.wantsReceipt = wantsReceipt
		return message

	@preMessageReceived
	@postMessageReceived
	def onImageReceived(self, message, preview, url, size, wantsReceipt = True):
		
		self._d("MEDIA SIZE IS "+str(size))
		mediaItem = WAXMPP.message_store.store.Media.create()
		mediaItem.remote_url = url
		mediaItem.preview = preview
		mediaItem.mediatype_id = WAConstants.MEDIA_TYPE_IMAGE
		mediaItem.size = size

		message.content = QtCore.QCoreApplication.translate("WAEventHandler", "Image")
		message.Media = mediaItem
		message.wantsReceipt = wantsReceipt

		return message


	@preMessageReceived
	@postMessageReceived
	def onVideoReceived(self, message, preview, url, size, wantsReceipt = True):

		mediaItem = WAXMPP.message_store.store.Media.create()
		mediaItem.remote_url = url
		mediaItem.preview = preview
		mediaItem.mediatype_id = WAConstants.MEDIA_TYPE_VIDEO
		mediaItem.size = size

		message.content = QtCore.QCoreApplication.translate("WAEventHandler", "Video")
		message.Media = mediaItem
		message.wantsReceipt = wantsReceipt

		return message

	@preMessageReceived
	@postMessageReceived
	def onAudioReceived(self, message, url, size, wantsReceipt = True):

		mediaItem = WAXMPP.message_store.store.Media.create()
		mediaItem.remote_url = url
		mediaItem.mediatype_id = WAConstants.MEDIA_TYPE_AUDIO
		mediaItem.size = size

		message.content = QtCore.QCoreApplication.translate("WAEventHandler", "Audio")
		message.Media = mediaItem
		message.wantsReceipt = wantsReceipt

		return message

	@preMessageReceived
	@postMessageReceived
	def onLocationReceived(self, message, name, preview, latitude, longitude, wantsReceipt = True):

		mediaItem = WAXMPP.message_store.store.Media.create()
		mediaItem.remote_url = None
		mediaItem.preview = preview
		mediaItem.mediatype_id = WAConstants.MEDIA_TYPE_LOCATION

		mediaItem.local_path ="%s,%s"%(latitude, longitude)
		mediaItem.transfer_status = 2

		message.content = name or QtCore.QCoreApplication.translate("WAEventHandler", "Location")
		message.Media = mediaItem
		message.wantsReceipt = wantsReceipt

		return message

	@preMessageReceived
	@postMessageReceived
	def onVCardReceived(self, message, name, data, wantsReceipt = True):

		targetPath = WAConstants.VCARD_PATH + "/" + name + ".vcf"
		vcardImage = None

		vcardFile = open(targetPath, "w")
		vcardFile.write(data)
		vcardFile.close()

		mediaItem = WAXMPP.message_store.store.Media.create()
		mediaItem.mediatype_id = WAConstants.MEDIA_TYPE_VCARD
		mediaItem.transfer_status = 2
		mediaItem.local_path = targetPath

		if "PHOTO;BASE64" in data:
			print "GETTING BASE64 PICTURE"
			n = data.find("PHOTO;BASE64") +13
			vcardImage = data[n:]
			vcardImage = vcardImage.replace("END:VCARD","")


		elif "PHOTO;TYPE=JPEG" in data:
			n = data.find("PHOTO;TYPE=JPEG") +27
			vcardImage = data[n:]
			vcardImage = vcardImage.replace("END:VCARD","")

		elif "PHOTO;TYPE=PNG" in data:
			n = data.find("PHOTO;TYPE=PNG") +26
			vcardImage = data[n:]
			vcardImage = vcardImage.replace("END:VCARD","")

		mediaItem.preview = vcardImage

		message.content = name
		message.Media = mediaItem
		message.wantsReceipt = wantsReceipt

		return message


	## ENDSECTION MESSAGERECEPTION ##
	
	## MEDIA SEND/ RECEIVE ##
	
	def getPicture(self, jid):
		if WAXMPP.message_store.isGroupJid(jid):
			self.interfaceHandler.call("group_getPicture", (jid,))
		else:
			self.interfaceHandler.call("contact_getProfilePicture", (jid,))
	
	def fetchMedia(self,mediaId):
		mediaMessage = WAXMPP.message_store.store.Message.create()
		message = mediaMessage.findFirst({"media_id":mediaId})
		jid = message.getConversation().getJid()
		media = message.getMedia()
		
		mediaHandler = WAMediaHandler(jid,message.id,media.remote_url,media.mediatype_id,media.id,self.account)
		
		mediaHandler.success.connect(self._mediaTransferSuccess)
		mediaHandler.error.connect(self._mediaTransferError)
		mediaHandler.progressUpdated.connect(self.mediaTransferProgressUpdated)
		
		mediaHandler.pull();
		
		self.mediaHandlers.append(mediaHandler);
		
	def fetchGroupMedia(self,mediaId):
		
		mediaMessage = WAXMPP.message_store.store.Groupmessage.create()
		message = mediaMessage.findFirst({"media_id":mediaId})
		jid = message.getConversation().getJid()
		media = message.getMedia()
		
		mediaHandler = WAMediaHandler(jid,message.id,media.remote_url,media.mediatype_id,media.id,self.account)
		
		mediaHandler.success.connect(self._mediaTransferSuccess)
		mediaHandler.error.connect(self._mediaTransferError)
		mediaHandler.progressUpdated.connect(self.mediaTransferProgressUpdated)
		
		mediaHandler.pull();
		
		self.mediaHandlers.append(mediaHandler);
	

	def uploadMediaX(self,mediaId):
		mediaMessage = WAXMPP.message_store.store.Message.create()
		message = mediaMessage.findFirst({"media_id":mediaId})
		jid = message.getConversation().getJid()
		media = message.getMedia()
		
		mediaHandler = WAMediaHandler(jid,message.id,media.local_path,media.mediatype_id,media.id,self.account,self.resizeImages)
		
		mediaHandler.success.connect(self._mediaTransferSuccess)
		mediaHandler.error.connect(self._mediaTransferError)
		mediaHandler.progressUpdated.connect(self.mediaTransferProgressUpdated)
		
		mediaHandler.push();
		
		self.mediaHandlers.append(mediaHandler);
		
	def uploadGroupMediaX(self,mediaId):
		mediaMessage = WAXMPP.message_store.store.Groupmessage.create()
		message = mediaMessage.findFirst({"media_id":mediaId})
		jid = message.getConversation().getJid()
		media = message.getMedia()
		
		mediaHandler = WAMediaHandler(jid,message.id,media.local_path,media.mediatype_id,media.id,self.account,self.resizeImages)
		
		mediaHandler.success.connect(self._mediaTransferSuccess)
		mediaHandler.error.connect(self._mediaTransferError)
		mediaHandler.progressUpdated.connect(self.mediaTransferProgressUpdated)
		
		mediaHandler.push();
		
		self.mediaHandlers.append(mediaHandler);

	def uploadMedia(self,mediaId):
		message = WAXMPP.message_store.store.Message.findFirst({"media_id":mediaId}) or WAXMPP.message_store.store.Groupmessage.findFirst({"media_id":mediaId})

		jid = message.getConversation().getJid()
		media = message.getMedia()

		sha1 = hashlib.sha256()
		f = open(media.local_path, 'rb')
		try:
			sha1.update(f.read())
		finally:
			f.close()
		hsh = base64.b64encode(sha1.digest())
		
		if not hsh in self.mediaRef:
			self.mediaRef[hsh] = media.id

		mtype = "image"
		
		if media.mediatype_id == WAConstants.MEDIA_TYPE_VIDEO:
			mtype="video"
		elif media.mediatype_id == WAConstants.MEDIA_TYPE_AUDIO:
			mtype="audio"
		
		self.startMediaUploadRequestTimeoutMonitor(hsh)
			
		self.interfaceHandler.call("media_requestUpload", (hsh,mtype, os.path.getsize(media.local_path)))


	@async
	def startMediaUploadRequestTimeoutMonitor(self, _hash):
		time.sleep(10)
		
		if _hash in self.mediaRef:
			self.onMediaUploadRequestFailed(_hash)
	
	def onMediaUploadRequestDuplicate(self, _hash, url):
		self._d("Duplicate upload request")
		
		if not _hash in self.mediaRef:
			return

		mediaId = self.mediaRef[_hash]


		message = WAXMPP.message_store.store.Message.findFirst({"media_id":mediaId}) or WAXMPP.message_store.store.Groupmessage.findFirst({"media_id":mediaId})
		
		
		if message:
		
			jid = message.getConversation().getJid()
			media = message.getMedia()
			
			if media:
				self._mediaTransferSuccess(jid, message.id, media.local_path, "upload", url)

		del self.mediaRef[_hash]

	def onMediaUploadRequestFailed(self, _hash):
		self._d("REQUEST FAILED")
		
		if not _hash in self.mediaRef:
			return
		
		mediaId = self.mediaRef[_hash]
		
		message = WAXMPP.message_store.store.Message.findFirst({"media_id":mediaId}) or WAXMPP.message_store.store.Groupmessage.findFirst({"media_id":mediaId})
		
		jid = message.getConversation().getJid()
		
		if message:
			self._mediaTransferError(jid, message.id)
			
		del self.mediaRef[_hash]
		

	def onMediaUploadRequested(self, _hash, uploadUrl, resumeFrom):
		print("REQUESTED SUCCESSFULY")
		
		
		if not _hash in self.mediaRef:
			return
		
		
		mediaId = self.mediaRef[_hash]
		
		message = WAXMPP.message_store.store.Message.findFirst({"media_id":mediaId}) or WAXMPP.message_store.store.Groupmessage.findFirst({"media_id":mediaId})
			
		if message:
				
		
			jid = message.getConversation().getJid()
			media = message.getMedia()
			
			if media and message:
				
				media.remote_url = uploadUrl
				media.save()
				
				mediaHandler = WAMediaHandler(jid,message.id,media.local_path,media.mediatype_id,media.id,self.jid,self.resizeImages)
				
				mediaHandler.success.connect(self._mediaTransferSuccess)
				mediaHandler.error.connect(self._mediaTransferError)
				mediaHandler.progressUpdated.connect(self.mediaTransferProgressUpdated)
				
				mediaHandler.push(uploadUrl);
				
				self.mediaHandlers.append(mediaHandler);
		else:
			self._d("upload requested but message not found")
			
		del self.mediaRef[_hash]
		
	
	def _mediaTransferSuccess(self, jid, messageId, path, action, url):
		try:
			jid.index('-')
			message = WAXMPP.message_store.store.Groupmessage.create()
		
		except ValueError:
			message = WAXMPP.message_store.store.Message.create()
		
		message = message.findFirst({'id':messageId});
		
		if(message.id):
			media = message.getMedia()
			if (action=="download"):
				#media.preview = data if media.mediatype_id == WAConstants.MEDIA_TYPE_IMAGE else None
				media.local_path = path
			else:
				media.remote_url = path

			media.transfer_status = 2
			media.save()
			self._d(media.getModelData())
			self.mediaTransferSuccess.emit(media.id, media.local_path)
			if (action=="upload"):
				self.sendMediaMessage(jid,messageId, path, url)

		
	def _mediaTransferError(self, jid, messageId):
		try:
			jid.index('-')
			message = WAXMPP.message_store.store.Groupmessage.create()
		
		except ValueError:
			message = WAXMPP.message_store.store.Message.create()
		
		message = message.findFirst({'id':messageId});
		
		if(message.id):
			media = message.getMedia()
			media.transfer_status = 1
			media.save()
			self.mediaTransferError.emit(media.id)

	## END MEDIA SEND/ RECEIVE ##

	## SECTION: NOTIFICATIONS ##
	
	def onNotificationReceiptRequested(self, jid, notificationId):
		self.interfaceHandler.call("notification_ack", (jid, notificationId))


	def onContactProfilePictureUpdatedNotification(self, jid, timestamp, messageId, wantsReceipt = True):
		if wantsReceipt:
			self.onNotificationReceiptRequested(jid, messageId)


		if WAXMPP.message_store.messageExists(jid, messageId):
			return
		
		self.interfaceHandler.call("contact_getProfilePicture", (jid,))

	def onGroupPictureUpdatedNotification(self, jid, author, timestamp, messageId, wantsReceipt = True):
		if wantsReceipt:
			self.onNotificationReceiptRequested(jid, messageId)

		if WAXMPP.message_store.messageExists(jid, messageId):
			return

		
		key = Key(jid, False, messageId)
		msg = WAXMPP.message_store.createMessage(jid)
		msg.setData({"timestamp": timestamp,"status":0,"key":key.toString(),"content":jid,"type":23})


		contact = WAXMPP.message_store.store.Contact.getOrCreateContactByJid(author)
		msg.contact_id = contact.id

		msg.Conversation = WAXMPP.message_store.getOrCreateConversationByJid(jid)

		msg.content = author#QtCore.QCoreApplication.translate("WAEventHandler", "%1 changed the group picture")

		selfChange = contact.number == self.account
		msg.content = msg.content.replace("%1", (contact.name or contact.number) if not selfChange else "You")

		WAXMPP.message_store.pushMessage(jid, msg)

		if not selfChange:
			self.interfaceHandler.call("contact_getProfilePicture", (jid,)) #@@TODO CHECK NAMING FOR GROUPS


	def onGroupParticipantAddedNotification(self, gJid, jid, author, timestamp, messageId, wantsReceipt = True):
		if wantsReceipt:
			self.onNotificationReceiptRequested(gJid, messageId)

		if WAXMPP.message_store.messageExists(jid, messageId):
			return

		key = Key(gJid, False, messageId)

		if jid == self.account:
			print "THIS IS ME! GETTING OWNER..."
			jid = gJid.split('-')[0]+"@s.whatsapp.net"
		self._d("Contact added: " + jid)

		msg = WAXMPP.message_store.createMessage(gJid)
		msg.setData({"timestamp": timestamp,"status":0,"key":key.toString(),"content":jid,"type":20})

		contact = WAXMPP.message_store.store.Contact.getOrCreateContactByJid(jid)
		msg.contact_id = contact.id
		msg.content = jid
				
		msg.Conversation = WAXMPP.message_store.getOrCreateConversationByJid(gJid)
		msg.Conversation.subject = "" if msg.Conversation.subject is None else msg.Conversation.subject

		if author == jid:
			notifyContent = QtCore.QCoreApplication.translate("WAEventHandler", "%1 joined the group")
			notifyContent = msg.content.replace("%1", contact.name or contact.number)
		else:
			authorContact = WAXMPP.message_store.store.Contact.getOrCreateContactByJid(author)
			notifyContent = QtCore.QCoreApplication.translate("WAEventHandler", "%1 added %2 to the group")
			notifyContent.replace("%1", authorContact.name or authorContact.number)
			notifyContent = msg.content.replace("%2", contact.name or contact.number)
			msg.contact_id = authorContact.id

		WAXMPP.message_store.pushMessage(gJid,msg)

		self.notifier.newGroupMessage(gJid, "%s - %s"%(contact.name or contact.number, msg.Conversation.subject.decode("utf8")), notifyContent, self.getDisplayPicture(gJid).encode('utf-8'),callback = self.notificationClicked);
		

	def onGroupParticipantRemovedNotification(self, gJid, jid, author, timestamp, messageId, wantsReceipt = True):
		if wantsReceipt:
			self.onNotificationReceiptRequested(gJid, messageId)

		if WAXMPP.message_store.messageExists(jid, messageId):
			return

		key = Key(gJid, False, messageId)

		if jid == self.account:
			print "THIS IS ME! GETTING OWNER..."
			jid = gJid.split('-')[0]+"@s.whatsapp.net"
		self._d("Contact removed: " + jid)

		msg = WAXMPP.message_store.createMessage(gJid)
		msg.setData({"timestamp": timestamp,"status":0,"key":key.toString(),"content":jid,"type":21});
		contact = WAXMPP.message_store.store.Contact.getOrCreateContactByJid(jid)
		msg.contact_id = contact.id
		msg.content = jid

		msg.Conversation = WAXMPP.message_store.getOrCreateConversationByJid(gJid)
		msg.Conversation.subject = "" if msg.Conversation.subject is None else msg.Conversation.subject

		if author == jid:
			notifyContent = QtCore.QCoreApplication.translate("WAEventHandler", "%1 left the group")
			notifyContent = msg.content.replace("%1", contact.name or contact.number)
		else:
			authorContact = WAXMPP.message_store.store.Contact.getOrCreateContactByJid(author)
			notifyContent = QtCore.QCoreApplication.translate("WAEventHandler", "%1 removed %2 from the group")
			notifyContent.replace("%1", authorContact.name or authorContact.number)
			notifyContent = msg.content.replace("%2", contact.name or contact.number)
			msg.contact_id = authorContact.id

		WAXMPP.message_store.pushMessage(gJid,msg)

		self.notifier.newGroupMessage(gJid, "%s - %s"%(contact.name or contact.number, msg.Conversation.subject.decode("utf8")), notifyContent, self.getDisplayPicture(gJid).encode('utf-8'),callback = self.notificationClicked);
		
	##ENDSECTION NOTIFICATIONS##
	
	def onGroupSetSubjectSuccess(self, jid):
		self.groupSubjectChanged.emit(jid);
	
	def onGroupSubjectReceived(self,  msgId, jid, author, newSubject, timestamp, receiptRequested):

		self._d("Got group subject update")
		g = WAXMPP.message_store.getOrCreateConversationByJid(jid);
		contact = g.getOwner();
		cjid = contact.jid if contact is not 0 else "";
		
		self.onGroupInfo(jid,cjid,newSubject,author,timestamp,g.created);

	
		if receiptRequested:
			self.interfaceHandler.call("message_ack", (jid, msgId))

	def onDirty(self,categories):
		self._d(categories)
		#ignored by whatsapp?
	
	def onAccountChanged(self,account_kind,expire):
		#nothing to do here
		return;
		
	def onRelayRequest(self,pin,timeoutSeconds,idx):
		#self.wtf("RELAY REQUEST");
		return
	
	def sendPing(self):
		self._d("Pinging")
		if self.connMonitor.isOnline() and self.conn.state == 2:
			self.conn.sendPing();
		else:
			self.connMonitor.createSession();
		
	
	def wtf(self,what):
		self._d("%s, WTF SHOULD I DO NOW???"%(what))
	
		
	
	def networkAvailable(self):
		if self.state != 0:
			return
		self._d("NET AVAILABLE")
		WAXMPP.contextproperty.setValue('connecting')
		self.connecting.emit();
		self.disconnectRequested = False

		self.state = 1
		thread.start_new_thread(self.interfaceHandler.call, ("auth_login", (self.conn.user, self.conn.password)))
		
		self._d("AUTH CALLED")

		if self.updater is None:
			#it is a new instance since it never finished and never run before
			self.updater = WAUpdater()
			self.updater.updateAvailable.connect(self.updateAvailable)
			self.updater.start()
		
		#self.conn.disconnect()
		
		
	def onDisconnected(self, reason):
		WAXMPP.contextproperty.setValue('offline')
		self._d("Got disconnected because %s"%reason)
		self.state = 0
		self.disconnected.emit()

		if reason == "":
			return
		elif reason == "closed" or reason == "dns" or reason == "network":
			if self.connMonitor.isOnline():
				self.networkAvailable()
			elif reason == "network":
				self.sleeping.emit()
		#@@TODO ADD reason another connection
		
	def networkDisconnected(self):
		self.state = 0
		#self.interfaceHandler.call("disconnect")
		'''if self.connMonitor.isOnline():
			self.networkAvailable()
			return
		'''
		self.sleeping.emit();
		
		#thread.start_new_thread(self.conn.changeState, (0,))
		#self.conn.disconnect();
		if not self.disconnectRequested:
			self.disconnectRequested = True
			thread.start_new_thread(lambda: self.interfaceHandler.call("disconnect", ("network",)), ())
		self._d("NET SLEEPING")
		
		
	def networkUnavailable(self):
		self.disconnected.emit();
		self.interfaceHandler.call("disconnect")
		self._d("NET UNAVAILABLE");
		
		
	def onUnavailable(self):
		self._d("SEND UNAVAILABLE")
		self.interfaceHandler.call("presence_sendUnavailable")
	
	
	def conversationOpened(self,jid):
		self.notifier.hideNotification(jid);
	
	def onAvailable(self, pushName=""):
		if self.state == 2:
			if pushName:
				self.interfaceHandler.call("presence_sendAvailableForChat", (pushName.encode('utf-8'),))
			else:
				self.interfaceHandler.call("presence_sendAvailable")
		
	
	def sendMessage(self,jid,msg_text):
		self._d("sending message now")
		fmsg = WAXMPP.message_store.createMessage(jid);
		
		msg_text = msg_text.decode("unicode_escape")
		
		if fmsg.Conversation.type == "group":
			contact = WAXMPP.message_store.store.Contact.getOrCreateContactByJid(self.conn.jid)
			fmsg.setContact(contact);
		
		msg_text = msg_text.replace("<br />", "\n");
		msg_text = msg_text.replace("&quot;","\"")
		msg_text = msg_text.replace("&lt;", "<");
		msg_text = msg_text.replace("&gt;", ">");
		msg_text = msg_text.replace("&amp;", "&");
		#msg_text = msg_text[:count]

		fmsg.setData({"status":0,"content":msg_text.encode('utf-8'),"type":1})
		WAXMPP.message_store.pushMessage(jid,fmsg)

		msgId = self.interfaceHandler.call("message_send", (jid, msg_text.encode('utf-8')))

		fmsg.key = Key(jid, True, msgId).toString()
		fmsg.save()
		#self.conn.sendMessageWithBody(fmsg);

	def sendLocation(self, jid, latitude, longitude, rotate):
		latitude = latitude[:10]
		longitude = longitude[:10]

		self._d("Capturing preview...")
		QPixmap.grabWindow(QApplication.desktop().winId()).save(WAConstants.CACHE_PATH+"/tempimg.png", "PNG")
		img = QImage(WAConstants.CACHE_PATH+"/tempimg.png")

		if rotate == "true":
			rot = QTransform()
			rot = rot.rotate(90)
			img = img.transformed(rot)

		if img.height() > img.width():
			result = img.scaledToWidth(320,Qt.SmoothTransformation);
			result = result.copy(result.width()/2-50,result.height()/2-50,100,100);
		elif img.height() < img.width():
			result = img.scaledToHeight(320,Qt.SmoothTransformation);
			result = result.copy(result.width()/2-50,result.height()/2-50,100,100);
		#result = img.scaled(96, 96, Qt.KeepAspectRatioByExpanding, Qt.SmoothTransformation);

		result.save( WAConstants.CACHE_PATH+"/tempimg2.jpg", "JPG" );

		f = open(WAConstants.CACHE_PATH+"/tempimg2.jpg", 'r')
		stream = base64.b64encode(f.read())
		f.close()


		os.remove(WAConstants.CACHE_PATH+"/tempimg.png")
		os.remove(WAConstants.CACHE_PATH+"/tempimg2.jpg")

		fmsg = WAXMPP.message_store.createMessage(jid);
		
		mediaItem = WAXMPP.message_store.store.Media.create()
		mediaItem.mediatype_id = WAConstants.MEDIA_TYPE_LOCATION
		mediaItem.remote_url = None
		mediaItem.preview = stream
		mediaItem.local_path ="%s,%s"%(latitude,longitude)
		mediaItem.transfer_status = 2

		fmsg.content = QtCore.QCoreApplication.translate("WAEventHandler", "Location")
		fmsg.Media = mediaItem

		if fmsg.Conversation.type == "group":
			contact = WAXMPP.message_store.store.Contact.getOrCreateContactByJid(self.conn.jid)
			fmsg.setContact(contact);
		
		fmsg.setData({"status":0,"content":fmsg.content,"type":1})
		WAXMPP.message_store.pushMessage(jid,fmsg)
		
		
		resultId = self.interfaceHandler.call("message_locationSend", (jid, latitude, longitude, stream))
		k = Key(jid, True, resultId)
		fmsg.key = k.toString()
		fmsg.save()


	def setBlockedContacts(self,contacts):
		self._d("Blocked contacts: " + contacts)
		self.blockedContacts = contacts.split(',');

	
	def setResizeImages(self,resize):
		self._d("Resize images: " + str(resize))
		self.resizeImages = resize;

	def setPersonalRingtone(self,value):
		self._d("Personal Ringtone: " + str(value))
		self.notifier.personalRingtone = value;

	def setPersonalVibrate(self,value):
		self._d("Personal Vibrate: " + str(value))
		self.notifier.personalVibrate = value;

	def setGroupRingtone(self,value):
		self._d("Group Ringtone: " + str(value))
		self.notifier.groupRingtone = value;

	def setGroupVibrate(self,value):
		self._d("Group Vibrate: " + str(value))
		self.notifier.groupVibrate = value;

	
	def readVCard(self, contactName):
		
		path = WAConstants.VCARD_PATH + "/"+contactName+".vcf"
		stream = ""
		if os.path.exists(path):
			try:
				while not "END:VCARD" in stream:
					f = open(path, 'r')
					stream = f.read()
					f.close()
					sleep(0.1)
					
				
				if len(stream) > 65536:
					print "Vcard too large! Removing photo..."
					n = stream.find("PHOTO")
					stream = stream[:n] + "END:VCARD"
					f = open(path, 'w')
					f.write(stream)
					f.close()
			except:
				pass
		
		return stream
	
	def sendVCard(self,jid,contactName):
		contactName = contactName.encode('utf-8')
		self._d("Sending vcard: " + WAConstants.VCARD_PATH + "/" + contactName + ".vcf")

		
		stream = self.readVCard(contactName)
		if not stream:
			return
		#print "DATA: " + stream

		fmsg = WAXMPP.message_store.createMessage(jid);
		
		mediaItem = WAXMPP.message_store.store.Media.create()
		mediaItem.mediatype_id = 6
		mediaItem.remote_url = None
		mediaItem.local_path = WAConstants.VCARD_PATH + "/"+contactName+".vcf"
		mediaItem.transfer_status = 2

		vcardImage = ""

		if "PHOTO;BASE64" in stream:
			n = stream.find("PHOTO;BASE64") +13
			vcardImage = stream[n:]
			vcardImage = vcardImage.replace("END:VCARD","")
			#mediaItem.preview = vcardImage

		if "PHOTO;TYPE=JPEG" in stream:
			n = stream.find("PHOTO;TYPE=JPEG") +27
			vcardImage = stream[n:]
			vcardImage = vcardImage.replace("END:VCARD","")
			#mediaItem.preview = vcardImage

		if "PHOTO;TYPE=PNG" in stream:
			n = stream.find("PHOTO;TYPE=PNG") +26
			vcardImage = stream[n:]
			vcardImage = vcardImage.replace("END:VCARD","")
			#mediaItem.preview = vcardImage

		mediaItem.preview = vcardImage

		fmsg.content = contactName
		fmsg.Media = mediaItem

		if fmsg.Conversation.type == "group":
			contact = WAXMPP.message_store.store.Contact.getOrCreateContactByJid(self.conn.jid)
			fmsg.setContact(contact);
		
		fmsg.setData({"status":0,"content":fmsg.content,"type":1})
		WAXMPP.message_store.pushMessage(jid,fmsg)
		
		resultId = self.interfaceHandler.call("message_vcardSend", (jid, stream, contactName))
		k = Key(jid, True, resultId)
		fmsg.key = k.toString()
		fmsg.save()

		
	def setGroupPicture(self, jid, filepath):
		path = self._getPictureForSending(jid, filepath)
		self.interfaceHandler.call("group_setPicture", (jid, path))
		
	def setProfilePicture(self, filepath):
		path = self._getPictureForSending(self.jid, filepath)
		self.interfaceHandler.call("profile_setPicture", (path,))
	
	def _getPictureForSending(self, jid, filepath):
		print "Preparing picture " + filepath + " for " + jid
		image = filepath.replace("file://","")
		rotation = 0

		ret = {}
		im = Image.open(image)
		try:
			info = im._getexif()
			for tag, value in info.items():
				decoded = TAGS.get(tag, value)
				ret[decoded] = value
			if ret['Orientation'] == 6:
				rotation = 90
		except:
			rotation = 0

		user_img = QImage(image)

		if rotation == 90:
			rot = QTransform()
			rot = rot.rotate(90)
			user_img = user_img.transformed(rot)


		if user_img.height() > user_img.width():
			preimg = user_img.scaledToWidth(480, Qt.SmoothTransformation)
			preimg = preimg.copy( 0, preimg.height()/2-240, 480, 480);
		elif user_img.height() < user_img.width():
			preimg = user_img.scaledToHeight(480, Qt.SmoothTransformation)
			preimg = preimg.copy( preimg.width()/2-240, 0, 480, 480);
		else:
			preimg = user_img.scaled(480, 480, Qt.KeepAspectRatioByExpanding, Qt.SmoothTransformation)

		preimg.save(WAConstants.CACHE_PATH+"/temp.jpg", "JPG")

		''''f = open(WAConstants.CACHE_PATH+"/temp.jpg", 'r')
		stream = f.read()
		stream = bytearray(stream)
		f.close()
		'''
		
		return WAConstants.CACHE_PATH+"/temp.jpg"
		


	def sendMediaImageFile(self,jid,image):
		image = image.replace("file://","")

		user_img = QImage(image)

		if user_img.height() > user_img.width():
			preimg = QPixmap.fromImage(QImage(user_img.scaledToWidth(64, Qt.SmoothTransformation)))
		elif user_img.height() < user_img.width():
			preimg = QPixmap.fromImage(QImage(user_img.scaledToHeight(64, Qt.SmoothTransformation)))
		else:
			preimg = QPixmap.fromImage(QImage(user_img.scaled(64, 64, Qt.KeepAspectRatioByExpanding, Qt.SmoothTransformation)))

		preimg.save(WAConstants.CACHE_PATH+"/temp2.png", "PNG")
		f = open(WAConstants.CACHE_PATH+"/temp2.png", 'r')
		stream = base64.b64encode(f.read())
		f.close()

		self._d("creating PICTURE MMS for " +jid + " - file: " + image)
		fmsg = WAXMPP.message_store.createMessage(jid);
		
		mediaItem = WAXMPP.message_store.store.Media.create()
		mediaItem.mediatype_id = 2
		mediaItem.local_path = image
		mediaItem.transfer_status = 0
		mediaItem.preview = stream
		try:
			mediaItem.size = os.path.getsize(mediaItem.local_path)
		except:
			pass

		fmsg.content = QtCore.QCoreApplication.translate("WAEventHandler", "Image")
		fmsg.Media = mediaItem

		if fmsg.Conversation.type == "group":
			contact = WAXMPP.message_store.store.Contact.getOrCreateContactByJid(self.conn.jid)
			fmsg.setContact(contact);
		
		fmsg.setData({"status":0,"content":fmsg.content,"type":1})
		WAXMPP.message_store.pushMessage(jid,fmsg)
		

	def sendMediaVideoFile(self,jid,video,image):
		self._d("creating VIDEO MMS for " +jid + " - file: " + video)
		fmsg = WAXMPP.message_store.createMessage(jid);

		if image == "NOPREVIEW":
			m = hashlib.md5()
			url = QtCore.QUrl(video).toEncoded()
			m.update(url)
			image = WAConstants.THUMBS_PATH + "/screen/" + m.hexdigest() + ".jpeg"
		else:
			image = image.replace("file://","")

		user_img = QImage(image)
		if user_img.height() > user_img.width():
			preimg = QPixmap.fromImage(QImage(user_img.scaledToWidth(64, Qt.SmoothTransformation)))
		elif user_img.height() < user_img.width():
			preimg = QPixmap.fromImage(QImage(user_img.scaledToHeight(64, Qt.SmoothTransformation)))
		else:
			preimg = QPixmap.fromImage(QImage(user_img.scaled(64, 64, Qt.KeepAspectRatioByExpanding, Qt.SmoothTransformation)))
		preimg.save(WAConstants.CACHE_PATH+"/temp2.png", "PNG")

		f = open(WAConstants.CACHE_PATH+"/temp2.png", 'r')
		stream = base64.b64encode(f.read())
		f.close()

		mediaItem = WAXMPP.message_store.store.Media.create()
		mediaItem.mediatype_id = 4
		mediaItem.local_path = video.replace("file://","")
		mediaItem.transfer_status = 0
		mediaItem.preview = stream
		
		try:
			mediaItem.size = os.path.getsize(mediaItem.local_path)
		except:
			pass

		fmsg.content = QtCore.QCoreApplication.translate("WAEventHandler", "Video")
		fmsg.Media = mediaItem

		if fmsg.Conversation.type == "group":
			contact = WAXMPP.message_store.store.Contact.getOrCreateContactByJid(self.conn.jid)
			fmsg.setContact(contact);
		
		fmsg.setData({"status":0,"content":fmsg.content,"type":1})
		WAXMPP.message_store.pushMessage(jid,fmsg)


	def sendMediaRecordedFile(self,jid):	
		recfile = WAConstants.CACHE_PATH+'/temprecord.wav'
		now = datetime.datetime.now()
		destfile = WAConstants.AUDIO_PATH+"/REC_"+now.strftime("%Y%m%d_%H%M")+".wav"
		shutil.copy(recfile, destfile)

		# Convert to MP3 using lame
		#destfile = WAConstants.AUDIO_PATH+"/REC_"+now.strftime("%Y%m%d_%H%M")+".mp3"
		#pipe=subprocess.Popen(['/usr/bin/lame', recfile, destfile])
		#pipe.wait()
		#os.remove(recfile)
 
		self._d("creating Audio Recorded MMS for " +jid)
		fmsg = WAXMPP.message_store.createMessage(jid);
		
		mediaItem = WAXMPP.message_store.store.Media.create()
		mediaItem.mediatype_id = 3
		mediaItem.local_path = destfile
		mediaItem.transfer_status = 0

		fmsg.content = QtCore.QCoreApplication.translate("WAEventHandler", "Audio")
		fmsg.Media = mediaItem

		if fmsg.Conversation.type == "group":
			contact = WAXMPP.message_store.store.Contact.getOrCreateContactByJid(self.conn.jid)
			fmsg.setContact(contact);
		
		fmsg.setData({"status":0,"content":fmsg.content,"type":1})
		WAXMPP.message_store.pushMessage(jid,fmsg)
		


	def sendMediaAudioFile(self,jid,audio):
		self._d("creating MMS for " +jid + " - file: " + audio)
		fmsg = WAXMPP.message_store.createMessage(jid);
		
		mediaItem = WAXMPP.message_store.store.Media.create()
		mediaItem.mediatype_id = 3
		mediaItem.local_path = audio.replace("file://","")
		mediaItem.transfer_status = 0
		
		try:
			mediaItem.size = os.path.getsize(mediaItem.local_path)
		except:
			pass

		fmsg.content = QtCore.QCoreApplication.translate("WAEventHandler", "Audio")
		fmsg.Media = mediaItem

		if fmsg.Conversation.type == "group":
			contact = WAXMPP.message_store.store.Contact.getOrCreateContactByJid(self.conn.jid)
			fmsg.setContact(contact);
		
		fmsg.setData({"status":0,"content":fmsg.content,"type":1})
		WAXMPP.message_store.pushMessage(jid,fmsg)



	def sendMediaMessage(self,jid,messageId, path, url):
		try:
			jid.index('-')
			message = WAXMPP.message_store.store.Groupmessage.create()
		except ValueError:
			message = WAXMPP.message_store.store.Message.create()
		
		message = message.findFirst({'id':messageId});
		media = message.getMedia()
		
		name = os.path.basename(path)
		size = str(os.path.getsize(path))
		self._d("sending media message to " + jid + " - file: " + url)
		
		
		if media.mediatype_id == WAConstants.MEDIA_TYPE_IMAGE:
			returnedId = self.interfaceHandler.call("message_imageSend", (jid, url, name, size, media.preview))
		elif media.mediatype_id == WAConstants.MEDIA_TYPE_AUDIO:
			returnedId = self.interfaceHandler.call("message_audioSend", (jid, url, name, size))
		elif media.mediatype_id == WAConstants.MEDIA_TYPE_VIDEO:
			returnedId = self.interfaceHandler.call("message_videoSend", (jid, url, name, size, media.preview))

		
		key = Key(jid, True, returnedId)
		message.key = key.toString()
		message.save()
		
		
	
	def rotateImage(self,filepath):
		print "ROTATING FILE: " + filepath
		img = QImage(filepath)
		rot = QTransform()
		rot = rot.rotate(90)
		img = img.transformed(rot)
		img.save(filepath)
		self.imageRotated.emit(filepath)



	def notificationClicked(self,jid):
		self._d("SHOW UI for "+jid)
		self.showUI.emit(jid);

	
	def subjectReceiptRequested(self,to,idx):
		self.conn.sendSubjectReceived(to,idx);
			
	def presence_available_received(self,fromm):
		if(fromm == self.conn.jid):
			return
		self.available.emit(fromm)
		self._d("{Friend} is now available".format(Friend = fromm));
	
	def presence_unavailable_received(self,fromm):
		if(fromm == self.conn.jid):
			return
		self.unavailable.emit(fromm)
		self._d("{Friend} is now unavailable".format(Friend = fromm));
	
	def typing_received(self,fromm):
		self._d("{Friend} is typing ".format(Friend = fromm))
		self.typing.emit(fromm);

	def paused_received(self,fromm):
		self._d("{Friend} has stopped typing ".format(Friend = fromm))
		self.paused.emit(fromm);


	


	def onMessageSent(self, jid, msgId):
		self._d("IN MESSAGE SENT")
		k = Key(jid, True, msgId)
		
		self._d("KEY: %s"%k.toString())


		waMessage =  WAXMPP.message_store.get(k);
			
			
		self._d(waMessage)

		if waMessage:
			WAXMPP.message_store.updateStatus(waMessage,WAXMPP.message_store.store.Message.STATUS_SENT)
			self.messageSent.emit(waMessage.id, jid)

	def onMessageDelivered(self, jid, msgId):
		k = Key(jid, True, msgId)

		waMessage =  WAXMPP.message_store.get(k);

		if waMessage:
			WAXMPP.message_store.updateStatus(waMessage,WAXMPP.message_store.store.Message.STATUS_DELIVERED)
			self.messageDelivered.emit(waMessage.id, jid)
			
		self._d("IN DELIVERED")
		self._d(waMessage)

		self.interfaceHandler.call("delivered_ack", (jid, msgId))
	

	def onGroupCreated(self,jid,group_id):
		self._d("Got group created " + group_id)
		jname = jid.replace("@g.us","")
		img = QImage("/opt/waxmppplugin/bin/wazapp/UI/common/images/group.png")
		img.save(WAConstants.CACHE_PATH+"/contacts/" + jname + ".png")
		self.groupCreated.emit(group_id);
		
	

	def onAddedParticipants(self, jid):
		self._d("participants added!")
		self.addedParticipants.emit();

	def onRemovedParticipants(self, jid):
		self._d("participants removed!")
		self.removedParticipants.emit();

	def onGroupEnded(self, jid):
		self._d("group deleted!")
		#@@TODO use the fucking jid
		self.groupEnded.emit();
		
	def onGroupInfoError(self, jid, code):
		self.groupInfoUpdated.emit(jid,"ERROR")
	
	def onGroupInfo(self,jid,ownerJid,subject,subjectOwnerJid,subjectT,creation):
		self._d("Got group info")
	
		self.groupInfoUpdated.emit(jid,jid+"<<->>"+str(ownerJid)+"<<->>"+subject+"<<->>"+subjectOwnerJid+"<<->>"+str(subjectT)+"<<->>"+str(creation))
		WAXMPP.message_store.updateGroupInfo(jid,ownerJid,subject,subjectOwnerJid,subjectT,creation)
		#self.conn.sendGetPicture("g.us",jid,"group")
		
	def onGroupParticipants(self,jid,jids):
		self._d("GOT group participants")
		self.groupParticipants.emit(jid, ",".join(jids));
		conversation = WAXMPP.message_store.getOrCreateConversationByJid(jid);
		
		# DO WE REALLY NEED TO ADD EVERY CONTACT ?
		for j in jids:
			contact = WAXMPP.message_store.store.Contact.getOrCreateContactByJid(j)
			conversation.addContact(contact.id);
		
		WAXMPP.message_store.sendConversationReady(jid);
		
	
	def onProfileSetStatusSuccess(self, jid, messageId):
		self.statusChanged.emit()
		self.interfaceHandler.call("delivered_ack", (jid, messageId))

	def onProfilePictureIdReceived(self,jid, pictureId):
		contact = WAXMPP.message_store.store.Contact.getOrCreateContactByJid(jid)

		cjid = jid.replace("@s.whatsapp.net","").replace("@g.us","")
		if contact.pictureid != str(pictureId) or not os.path.isfile("%s/%s.jpg"%(WAConstants.CACHE_PROFILE, cjid)) or not os.path.isfile("%s/%s.png"%(WAConstants.CACHE_CONTACTS, cjid)):
			contact.setData({"pictureid":pictureId})
			contact.save()
			self.interfaceHandler.call("contact_getProfilePicture", (jid,))


		self.getPicturesFinished.emit()

	def onGetPictureDone(self, jid, tmpfile):

		if os.path.exists(tmpfile):
			
			cjid = jid.replace("@s.whatsapp.net","").replace("@g.us","")
			shutil.move(tmpfile, WAConstants.CACHE_PATH+"/contacts/" + cjid + ".jpg")
	
			if os.path.isfile(WAConstants.CACHE_PATH+"/contacts/" + cjid + ".png"):
				os.remove(WAConstants.CACHE_PATH+"/contacts/" + cjid + ".png")

			self.profilePictureUpdated.emit(jid);
	
		self.getPicturesFinished.emit()
		
	def onSetProfilePicture(self):
		self._d("GETTING MY PICTURE")
		self.interfaceHandler.call("profile_getPicture")#@@TODO DON'T REFETCH?


	def onSetProfilePictureError(self, errorCode):
		self.profilePictureUpdated.emit(self.jid);


	def onSetGroupPicture(self,jid):
		self.interfaceHandler.call("group_getPicture", (jid,))


	def onSetGroupPictureError(self, jid, errorCode):
		self.profilePictureUpdated.emit(jid);

class WAXMPP():
	message_store = None
	
	myService = Service(SessionBus, 'org.tgalal.wazapp')
	myService.setAsDefault()
	contextproperty = Property('Wazapp.Online')
	contextproperty.setValue('offline')
		
	def __init__(self,domain,resource,user,push_name,password):
		
		WADebug.attach(self);
		
		self.domain = domain;
		self.resource = resource;
		self.user=user;
		self.push_name=push_name;
		self.password = password;
		self.jid = user+'@'+domain
		self.fromm = user+'@'+domain+'/'+resource;
		self.retry = True
		self.eventHandler = WAEventHandler(self);	
		
		
		self.disconnectRequested = False
		
		self.connTries = 0;
		
		self.verbose = True
		self.iqId = 0;
	
		
		self.waiting = 0;
		
		#super(WAXMPP,self).__init__();
		
		#self.eventHandler.initialConnCheck();
		
		#self.do_login();
	def setContactsManager(self,contactsManager):
		self.contactsManager = contactsManager
		


	


########NEW FILE########
