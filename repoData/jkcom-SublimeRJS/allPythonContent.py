__FILENAME__ = context_helper
import json
from pprint import pprint

def initializeContext(context):
	# load settings
	json_data = open(context.settingsPath)
	data = json.load(json_data)
	json_data.close()
	context.setSettings(data)
	# load require main
	if data["require_main"] is not "":
		loadRequireMain(context)
	else:
		context.setModuleAliasMap({})


def loadRequireMain(context):	
		print "REQUIRE MAIN", context.getBaseDir() + context.settings["require_main"]
		f = open(context.getBaseDir() + context.settings["require_main"], "r")
		data = f.read()
		f.close();
		if data.find("require.config") != -1:
			configString = data[data.find("(", data.find("require.config")) + 1:data.find(")", data.find("require.config("))].replace("'", '"')
		else:
			configString = "{\n}"
		
		# find paths
		if configString.find("paths") is not -1:
			pathsString = configString[configString.find("{", configString.find("paths")) + 1:configString.find("}", configString.find("paths"))].replace(" ", "").strip().replace('\n', "")
			pathsString = pathsString.replace("	", "")
			pathElements = pathsString.split(",")
			aliasMap = {}
			for alias in pathElements:
				value = alias.split(":")[0]
				key = alias.split(":")[1].replace("'", "").replace('"', "")
				if value != context.settings["texts_name"] or len(context.settings["text_folder"]) == 0:
					aliasMap[key] = value

		else:
			aliasMap = {}

		# add template alias map
		if len(context.settings["text_folder"]) > 0:

			# find texts folder
			stepsToBaseDir = len(context.settings["require_main"].split("/")) - 1
			textsPath = ""
			for x in range(0, stepsToBaseDir):
				textsPath += "../" + context.settings["text_folder"]

			aliasMap[textsPath] = context.settings["texts_name"]

			# remove current paths:
			if configString.find("paths") is not -1:
				pathsString = configString[configString.find("paths"):configString.find("}", configString.find("paths")) + 1]
				configString = configString.replace(pathsString, "{paths-location}")
				pass

			# render new paths block
			pathsString = "paths: {\n"
			for key in aliasMap:
				pathsString += "		" + aliasMap[key] + ": " + "'" + key + "',\n"
			pathsString = pathsString[0:pathsString.rfind(",")] + "\n"
			pathsString += "	}"

			# insert
			if configString.find("{paths-location}") != -1:
				configString = configString.replace("{paths-location}", pathsString)
			else:
				afterPaths = ""
				if configString.find(":") != -1:
					afterPaths = ","
				configString = "{" + "\n	" + pathsString + afterPaths + configString[configString.find("{") + 1:]

			# write in main data
			
			
			if data.find("require.config") != -1:
				newData = data.replace(data[data.find("(", data.find("require.config")) + 1:data.find(")", data.find("require.config("))], configString)
			else:
				newData = "require.config(" + configString + ");\n\n" + data

			f = open(context.getBaseDir() + context.settings["require_main"], "w+")
			f.write(newData)
			f.close()


		# assign to context
		context.setModuleAliasMap(aliasMap)


########NEW FILE########
__FILENAME__ = editor
import sublime
import math

class ModuleEdit:

	def __init__(self, content, context):
		self.content = content
		self.context = context
		#parse
		defineRegion = self.getDefineRegion()
		defineString = content[defineRegion.begin():defineRegion.end()]
		#parse modules
		modulesStart = defineString.find("[")
		if modulesStart > -1:
			modulesEnd = defineString.find("]")
			modulesTemp = defineString[(modulesStart + 1):(modulesEnd)]
			modulesTemp = modulesTemp.replace("'", '')
			modulesTemp = modulesTemp.replace('"', '')
			modulesTemp = modulesTemp.replace(' ', '')
			self.modules = modulesTemp.split(",")
			if (self.modules[0] == ""):
				self.modules = []
		else:
			self.modules = []
		#parse refrences
		refrencesStart = defineString.rfind("(")
		refrencesEnd = defineString.find(")")
		refrencesTemp = defineString[(refrencesStart + 1):refrencesEnd].split(" ")
		self.refrences = "".join(refrencesTemp).split(",")
		if (self.refrences[0] == ""):
			self.refrences = []

	def getModuleList(self):
		commentList = "\n    /*\n    *    Module list\n"
		commentList += "    *\n"

		commentList += self.renderListGroup(self.modulesCollection["autoModules"], True)
		commentList += self.renderListGroup(self.modulesCollection["scriptModules"], True)
		commentList += self.renderListGroup(self.modulesCollection["textModules"], False)

		commentList += "    */"

		return commentList

	def renderListGroup(self, items, addBlankLine):
		if len(items) == 0:
			return ""
		listBody = ""
		sortedKeys = sorted(items, reverse = False)
		numSpaces = 20
		for x in range(0, len(sortedKeys)):
			listBody += "    *    " + sortedKeys[x]
			spaces = numSpaces - len(sortedKeys[x])
			for y in range(0, spaces):
				listBody += " "
			listBody += items[sortedKeys[x]] + "\n"
		if addBlankLine == True:
			listBody += "    *" + "\n"
		return listBody

	def getDefineRegion(self):
		startIndex = self.content.find("define(")

		if self.content.find("*    Module list") is not -1:
			endIndex = self.content.find("*/", startIndex) + 2
		else:
			endIndex = self.content.find("{", startIndex) + 1
		return sublime.Region(startIndex, endIndex)

	def addModule(self, module, moduleString):
		if (module is None):
			self.modules.append(moduleString)
			self.refrences.append(moduleString)
		else:
			self.modules.append(module.getImportString())
			self.refrences.append(module.getRefrenceString())

		self.updateModuleList()

	def render(self):
		output = "define("
		# modules
		if len(self.modules) > 0:
			isFirst = True
			output += "["
			for module in self.modules:
				if not isFirst:
					output += ", "
				else:
					isFirst = False
				output += "'" + module + "'"
			output += "], "
		# fundtion
		output += "function("
		# refrences
		isFirst = True
		for refrence in self.refrences:
			if not isFirst:
				output += ", "
			else:
				isFirst = False
			output += refrence
		output += ") {"
		print "settings is ", self.context.settings["list_modules"], self.context.settings["list_modules"] == "true"
		if str(self.context.settings["list_modules"]) == "true":
			print "add list"
			output += "\n" + self.getModuleList()
		
		return output

	def getModules(self):
		modules = []
		for importString in self.modules:
			module = self.context.getModuleByImportString(importString)
			if module is not None:
				modules.append(module)
		return modules

	def removeModule(self, module):
		self.modules.pop(self.modules.index(module.getImportString()))
		self.refrences.pop(self.refrences.index(module.getRefrenceString()))

		self.updateModuleList()

	def updateModuleList(self):
		# run throug for module list
		self.modulesCollection = {
			"autoModules": {},
			"scriptModules": {},
			"textModules": {}
		}
		for importString in self.modules:
			module = self.context.getModuleByImportString(importString)
			if module is not None:
				if module.getImportString() in self.context.settings["auto_add"]:
					self.modulesCollection["autoModules"][module.getRefrenceString()] = module.getRelativePath()
				elif module.type == "script":
					self.modulesCollection["scriptModules"][module.getRefrenceString()] = module.getRelativePath()
				elif module.type == "text":
					self.modulesCollection["textModules"][module.getRefrenceString()] = module.getRelativePath()

########NEW FILE########
__FILENAME__ = factory
import sys
sys.path.append("core")

import os
import model
import editor
import ntpath

global shadowList

global createConfig
createConfig = {}

global context


def createModule(newContext, newCreateConfig):
	global context
	global createConfig
	global shadowList
	context = newContext
	createConfig = newCreateConfig
	if createConfig["type"] == "script":
		packages = context.getScriptPackages()
	elif createConfig["type"] == "text":
		packages = context.getTextPackages()

	context.window.show_quick_panel(packages, onPackageSelected, 0)
	shadowList = packages


def onPackageSelected(selectionIndex):
	global createConfig
	global shadowList
	moduleSuggestiong = shadowList[selectionIndex]
	if selectionIndex == -1:
		return
	if selectionIndex == 0:
		moduleSuggestiong = ""


	if createConfig["type"] == "script":
		packagePath = context.getBaseDir()+ context.settings["script_folder"] + "/" + moduleSuggestiong
		if os.path.exists(packagePath) == True:
			createConfig["packageBase"] = context.settings["script_folder"]
	elif createConfig["type"] == "text":
		
		packagePath = context.getBaseDir()+ context.settings["text_folder"] + "/" + moduleSuggestiong
		if os.path.exists(packagePath) == True:
			createConfig["packageBase"] = context.settings["text_folder"]


	context.window.show_input_panel("Name your new module", moduleSuggestiong+createConfig["name"], onNameDone, onNameChange, onNamceCancle)


def onNameDone(inputString):
	global createConfig
	global context
	global shadowList
	moduleFile = context.getBaseDir() + createConfig["packageBase"] + "/" + inputString
	createConfig["moduleFile"] = moduleFile
	print moduleFile

	name = moduleFile[moduleFile.rfind("/"):]
	if not "." in name:
		if createConfig["type"] == "script":
			ext = ".js"
			name += ext
		elif createConfig["type"] == "text":
			ext = ".html"
			name += ext
	else:
		ext = name[name.rfind("."):]

	moduleDir = moduleFile[0:moduleFile.rfind("/")]
	moduleFile = moduleDir + name
	createConfig["moduleFile"] = moduleFile
	if os.path.exists(moduleDir) == False:
		os.makedirs(moduleDir)

	# ask for snippet
	if len(context.settings["module_templates"]) > 0:
		snippetsDir = context.getBaseDir() + context.settings["module_templates"]
		snippets = []
		shadowList =[]
		snippets.append("Blank")
		shadowList.append("")
		for file in os.listdir(snippetsDir):
			dirfile = os.path.join(snippetsDir, file)
			if os.path.isfile(dirfile):
				print "TEST .=" + str(ntpath.basename(file)[0:1]), str(ntpath.basename(file)[0:1]) is "."
				if "DS_Store" not in ntpath.basename(file):
					snippets.append(ntpath.basename(file))
					shadowList.append(dirfile)

		context.window.show_quick_panel(snippets, onSnippetSelected, 0)
	else:
		finish("")

def onSnippetSelected(selectionIndex):
	global shadowList
	if selectionIndex == 0:
		finish("")
	else:
		moduleName = createConfig["moduleFile"][createConfig["moduleFile"].rfind("/") + 1:createConfig["moduleFile"].rfind(".")]
		f = open(shadowList[selectionIndex], "r")
		data = f.read()
		snippet = data
		snippet = snippet.replace("$MODULE_NAME", moduleName)
		f.close()
		finish(snippet)


def finish(snippet):
	global createConfig
	global context
	fileContent = ""
	if createConfig["type"] == "script":
		fileContent = "define(function(){});"
		if len(context.settings["auto_add"]) > 0:
			for module in context.settings["auto_add"]:
				addEdit = editor.ModuleEdit(fileContent, context)
				addEdit.addModule(context.getModuleByImportString(module), module)
				fileContent = addEdit.render()+ "\n"+snippet+"\n});"
	file = open(createConfig["moduleFile"], 'w+')
	file.write(fileContent)
	file.close()

	# callback to let module be imported
	if createConfig["type"] == "script":
		temp = (createConfig["moduleFile"]).split(context.getBaseDir() + createConfig["packageBase"] + "/")[1];
		importString = temp[0:temp.rfind(".")]
	elif createConfig["type"] == "text":
		temp = (createConfig["moduleFile"]).split(context.getBaseDir() + createConfig["packageBase"] + "/")[1];
		importString = "text!" + context.settings["texts_name"] + "/" + temp
	createConfig["callback"](importString, createConfig)


def onNameChange(input):
	pass

def onNamceCancle(input):
	pass

########NEW FILE########
__FILENAME__ = file_search
import threading
import os
import ntpath
import Queue

global _collectorSingle_thread
_collectorSingle_thread = None

global foundCallback
global que
que = Queue.Queue()


def checkQue():
	global timer
	global que
	global foundCallback
	if que.empty():
		foundCallback(None)
	else:
		foundCallback(que.get())



def findFile(folder, fileName, callback):
	global foundCallback
	foundCallback = callback
	global _collectorSingle_thread
	global timer
	global que
	# stop old
	if _collectorSingle_thread != None:
		_collectorSingle_thread.stop()
	# start thread
	_collectorSingle_thread = ParsingForSingleThread([], folder, fileName, que, 30)
	_collectorSingle_thread.start()


class ParsingForSingleThread(threading.Thread):

	def __init__(self, collector, folder, fileName, que, timeout_seconds):
		self.que = que
		self.collector = collector
		self.timeout = timeout_seconds
		self.folder = folder
		self.fileName = fileName
		threading.Thread.__init__(self)

	def get_javascript_files(self, dir_name, fileToFind):
		for file in os.listdir(dir_name):
			dirfile = os.path.join(dir_name, file)
			if os.path.isfile(dirfile):
				if ntpath.basename(dirfile) == fileToFind:
					self.que.put(dirfile)
					break
			elif os.path.isdir(dirfile):
				self.get_javascript_files(dirfile, fileToFind)



	def run(self):
		self.get_javascript_files(self.folder, self.fileName)
		checkQue()

	def stop(self):
		if self.isAlive():
			self._Thread__stop()

########NEW FILE########
__FILENAME__ = folder_parser
import threading
import os

global _collector_thread
_collector_thread = None


def find(folder, fileName):
	print "Search for : " + fileName + " in " + folder
	global _collector_thread
	if _collector_thread != None:
		_collector_thread.stop()
	print "GOT HERE"
	_collector_thread = ParsingThread([], folder, 30)
	_collector_thread.start()
	return ""


class ParsingThread(threading.Thread):

	def __init__(self, collector, folder, timeout_seconds):
		self.collector = collector
		self.timeout = timeout_seconds
		self.folder = folder
		threading.Thread.__init__(self)

	def get_javascript_files(self, dir_name, *args):
		self.fileList = []
		for file in os.listdir(dir_name):
			dirfile = os.path.join(dir_name, file)
			if os.path.isfile(dirfile):
				fileName, fileExtension = os.path.splitext(dirfile)
				print fileName
				if fileExtension == ".js" and ".min." not in fileName:
					self.fileList.append(dirfile)
			elif os.path.isdir(dirfile):
				self.fileList += self.get_javascript_files(dirfile, *args)
		return self.fileList

	def run(self):
		print "RUN THREAD"
		jsfiles = self.get_javascript_files(self.folder)
		for file_name in jsfiles:
			file_name

	def stop(self):
		if self.isAlive():
			self._Thread__stop()



########NEW FILE########
__FILENAME__ = model
import ntpath

# context
class Context:
	window = None
	settingsPath = ""
	basedir = ""
	scriptModules = None
	textModules = None
	modulesByImportString = {}
	modulesByFullPath = {}
	scriptPackages = []


	def __init__(self, window, settingsPath):
		self.window = window
		self.settingsPath = settingsPath

	def window(self):
		return self.window

	def settingsPath(self):
		return self.settingsPath

	def getBaseDir(self):
		return ntpath.dirname(self.settingsPath).replace("\\", "/") + "/"

	def setSettings(self, settings):
		self.settings = settings

	def settings(self):
		return self.settings

	def isSublimeRJS(self):
		return self.settingsPath is not ""

	def resetModules(self):
		self.scriptModules = []
		self.textModules = []
		self.scriptPackages = []
		self.scriptPackages.append("")
		self.textPackages = []
		self.textPackages.append("")
		self.modulesByFullPath={}

	def addScriptModule(self, module):
		self.scriptModules.append(module)
		self.modulesByImportString[module.getImportString()] = module
		self.modulesByFullPath[module.getFullPath()] = module
		filtred = self.filterModule(module)
		if module.package not in self.scriptPackages and filtred is not None:
			self.scriptPackages.append(module.package)

	def getModuleByImportString(self, importString):
		if importString in self.modulesByImportString:
			return self.modulesByImportString[importString]
		else:
			return None

	def getModuleByFullPath(self, fullPath):
		if fullPath in self.modulesByFullPath:
			return self.modulesByFullPath[fullPath]
		else:
			return None

	def getScriptModules(self):
		return self.scriptModules

	def addTextModule(self, module):
		self.textModules.append(module)
		self.modulesByImportString[module.getImportString()] = module
		self.modulesByFullPath[module.getFullPath()] = module
		filtred = self.filterModule(module)
		if module.package not in self.textPackages and filtred is not None:
			self.textPackages.append(module.package)

	def getTextModules(self):
		return self.textModules

	def setModuleAliasMap(self, moduleAliasMap):
		self.moduleAliasMap = moduleAliasMap

	def getModuleAliasMap(self):
		return self.moduleAliasMap

	def getTextPackages(self):

		collection = []

		return self.textPackages

	def getScriptPackages(self):
		return self.scriptPackages

	def filterModule(self, module):
		if len(self.settings["excludes"]) > 0:
			for exclude in self.settings["excludes"]:
				if self.getBaseDir() + exclude in module.path + "/" + module.name:
					return None
		return module



def reverseSlashes(input):
	return input.replace("")

# module
class Module:
	name = ""
	path = ""
	type = ""
	package = ""
	importAlias = ""
	refrenceAlias = ""

	def __init__(self, name, path, ext, type, package, context):
		self.name = name
		self.path = path.replace("\\", "/")
		self.ext = ext
		self.type = type
		self.package = package.replace("\\", "/")
		self.context = context

	def name(self):
		return self.name

	def package(self):
		return self.package

	def getImportString(self):
		if self.importAlias is not "":
			return self.importAlias
		if self.type == "script":
			return self.package + self.name.split(self.ext)[0]
		elif self.type == "text":
			return "text!" + self.context.settings["texts_name"] + "/" + self.package + self.name

	def getRefrenceString(self):
		if self.importAlias is not "":
			if self.refrenceAlias is not "":
				return self.refrenceAlias
			return self.importAlias

		if self.refrenceAlias is not "":
			return self.refrenceAlias
		
		return self.name.split(self.ext)[0]

	def setImportAlias(self, alias):
		self.importAlias = alias

	def setRefrenceAlias(self, alias):
		self.refrenceAlias = alias

	def getFullPath(self):
		return self.path + "/" + self.name

	def getRelativePath(self):
		return self.path.split(self.context.getBaseDir())[1] + "/" + self.name


########NEW FILE########
__FILENAME__ = module_parser
import threading
import os
import parsing
import ntpath
import model

global onParseDoneCallback


def parseModules(context, callback):
	global onParseDoneCallback
	onParseDoneCallback = callback
	# clean context
	context.resetModules()
	# scripts
	parseConfig = parsing.ParseConfig()
	parseConfig.folder = context.getBaseDir() + context.settings["script_folder"]
	parseConfig.ext = ".js"
	parseConfig.type = "script"
	parseForModules(context, parseConfig)
	# texts
	parseConfig = parsing.ParseConfig()
	parseConfig.folder = context.getBaseDir() + context.settings["text_folder"]
	parseConfig.ext = ".html"
	parseConfig.type = "text"
	parseForModules(context, parseConfig)

global _collector_thread
_collector_thread = None


def evalutateFile(file, context, parseConfig):
	file = os.path.normpath(file)
	fileName, fileExtension = os.path.splitext(file)
	if (fileExtension == parseConfig.getExt()):
		package = file.split(os.path.normpath(parseConfig.folder))[1][1:].split(ntpath.basename(file))[0]
		module = model.Module(ntpath.basename(file), ntpath.dirname(file), parseConfig.getExt(), parseConfig.getType(), package, context)
		# check module for aliases
		moduleAliasMap = context.getModuleAliasMap()
		if module.getImportString() in moduleAliasMap:
			module.setImportAlias(moduleAliasMap[module.getImportString()])
		# check for refrence aliases
		if module.getImportString() in context.settings["aliases"]:
			module.setRefrenceAlias(context.settings["aliases"][module.getImportString()])
		# add to context
		if module.type == "script":
			context.addScriptModule(module)
		elif module.type == "text":
			context.addTextModule(module)


def parseForModules(context, parseConfig):
	global _collector_thread
	if _collector_thread != None:
		_collector_thread.stop()
	_collector_thread = ParsingThread(context, parseConfig)
	_collector_thread.start()


class ParsingThread(threading.Thread):

	def __init__(self, context, parseConfig):
		self.timeout = 30
		self.parseConfig = parseConfig
		self.context = context
		threading.Thread.__init__(self)

	def parseFolder(self, folder, context, parseConfig):
		
		for file in os.listdir(folder):
			dirfile = os.path.join(folder, file)
			if os.path.isfile(dirfile):
				evalutateFile(dirfile, context, parseConfig)
			elif os.path.isdir(dirfile):
				self.parseFolder(dirfile, context, parseConfig)
		


	def run(self):
		global onParseDoneCallback
		self.parseFolder(self.parseConfig.folder, self.context, self.parseConfig)
		onParseDoneCallback()

	def stop(self):
		if self.isAlive():
			self._Thread__stop()



########NEW FILE########
__FILENAME__ = move_module
import sys
sys.path.append("core")

from threading import Thread

import os
import os.path
import re

global context
global moveConfig
global shadowList
global threads
global moduleToMove
global t 
global onModuleMoved

# test commit

def moveModuleInView(activeContext, onModuleMovedCallBack):
	global onModuleMoved
	onModuleMoved = onModuleMovedCallBack
	global context
	context = activeContext

	global moduleToMove
	
#	get module to move
	moduleToMove = context.getModuleByFullPath(context.window.active_view().file_name())
	if moduleToMove is None:
		return


	global moveConfig
	global shadowList

	moveConfig = {
		"type": moduleToMove.type,
		"fullPath": moduleToMove.getFullPath(),
		"name": moduleToMove.name[0:moduleToMove.name.find(".")],
		"importString":moduleToMove.package + moduleToMove.name.split(moduleToMove.ext)[0]
	}
	
	
	if moveConfig["type"] == "script":
		packages = context.getScriptPackages()
	elif moveConfig["type"] == "text":
		packages = context.getTextPackages()

	context.window.show_quick_panel(packages, onPackageSelected, 0)
	shadowList = packages


def onPackageSelected(selectionIndex):
	global moveConfig
	global shadowList
	moduleSuggestiong = shadowList[selectionIndex]
	if selectionIndex == -1:
		return
	if selectionIndex == 0:
		moduleSuggestiong = ""


	if moveConfig["type"] == "script":
		packagePath = context.getBaseDir()+ context.settings["script_folder"] + "/" + moduleSuggestiong
		if os.path.exists(packagePath) == True:
			moveConfig["packageBase"] = context.settings["script_folder"]
	elif moveConfig["type"] == "text":
		
		packagePath = context.getBaseDir()+ context.settings["text_folder"] + "/" + moduleSuggestiong
		if os.path.exists(packagePath) == True:
			moveConfig["packageBase"] = context.settings["text_folder"]

	context.window.show_input_panel("Change module path/name to: ", moduleSuggestiong+moveConfig["name"], onNameDone, onNameChange, onNamceCancle)

def onNameDone(inputString):

	global moveConfig
	global onModuleMoved
	global context

	moveConfig["newImportString"] = inputString
	moveConfig["newName"] = inputString[inputString.rfind("/")+1:]
	
	moveModule()
	onModuleMoved()

	updateModules()
	
	
	pass

def moveModule():
	global moduleToMove
	global context
	global moveConfig
	context.window.run_command("close_file")

	if moduleToMove.type is "text":
		current = context.settings["text_folder"] + "/" +moveConfig["importString"]
		new = context.settings["text_folder"] + "/" +moveConfig["newImportString"]
	else:
		current = context.settings["script_folder"] + "/" +moveConfig["importString"]
		new = context.settings["script_folder"] + "/" +moveConfig["newImportString"]

	newFullPath  = moduleToMove.getFullPath().replace(current, new)


	dir = os.path.dirname(newFullPath)

	if not os.path.exists(dir):
		os.makedirs(dir)

	os.rename(moduleToMove.getFullPath(), newFullPath)
	context.window.open_file(newFullPath)

	pass


def onNameChange(input):
	pass

def onNamceCancle(input):
	pass

def updateModules():
	global moveConfig
	global context
	global moduleToMove
	global t


	if moduleToMove.type is "text":
		#moveConfig["importString"] = "text!" + context.settings["texts_name"] + "/" + moveConfig["importString"] + ".html"
		#moveConfig["newImportString"] = "text!" + context.settings["texts_name"] + "/" + moveConfig["newImportString"] + ".html"
		pass
	
	# update module refs
	modulesList = context.getScriptModules()
	if moduleToMove in modulesList:
		modulesList.remove(moduleToMove)
	count = 0
	t = Thread(target=update, args=(modulesList, moveConfig, updateDone))
	t.start()



def updateDone():
	pass
    

def update(modules, moveConfig, callback):
	global moduleToMove
	for module in modules:
		f = open(module.getFullPath(), "r")
		data = f.read()
		f.close();

		if data.find("define([") is not -1 and data.find(moveConfig["importString"]) is not -1:
			updateModule(module, data, moveConfig)

	callback();
	pass

def updateModule(module, data, moveConfig):
	
	#update import string
	data = data.replace("'"+moveConfig["importString"]+"'", "'"+moveConfig["newImportString"]+"'", 1)
	#data = re.sub('\\b'+moveConfig["importString"]+'\\b', moveConfig["importString"], data)

	#update variable name
	if moveConfig["name"] is not moveConfig["newName"]:
		data = re.sub('\\b'+moveConfig["name"]+'\\b', moveConfig["newName"], data)

	f = open(module.getFullPath(), "w+")
	f.write(data)
	f.close()
	pass




########NEW FILE########
__FILENAME__ = parsing
class ParseConfig:

	def getFolder(self):
		return self.folder

	def setFolder(self, folder):
		self.folder = folder

	def getExt(self):
		return self.ext

	def setExt(self, ext):
		self.ext = ext

	def getType(self):
		return self.type

	def setType(self, type):
		self.type = type

########NEW FILE########
__FILENAME__ = SublimeRJS
import sys
sys.path.append( "core")

import model

import sublime
import sublime_plugin
import move_module


import file_search
import module_parser
import editor
import context_helper
import factory
import json
import shutil
import pprint


global context
context = None

global contextWindow
contextWindow = None

global shadowList
shadowList = None

global moduleAddInLine
moduleAddInLine = None

global moduelOpenInLine
moduleOpenInLine = None

global currentModuleEdit

# update contexts
def getContext(window):
	global context
	global contextWindow
	# clean up old context
	context = None
	contextWindow = window

	# find sublime settings file in new active window
	if window is not None:
		for folder in window.folders():
			file_search.findFile(folder, "SublimeRJS.sublime-settings", onSearchedForSettings)


# on searched for contexs.get("script_folders")
def onSearchedForSettings(file):
	if file is not None:
		setContext(model.Context(contextWindow, file))
	else:
		pass


# set context
def setContext(newContext):
	global context
	context = newContext

	# hack to get back to main thread
	sublime.set_timeout(initContext, 1)


# load settings
def initContext():
	global context
	context_helper.initializeContext(context)
	module_parser.parseModules(context, onModulePareDone)

def onModulePareDone(): 
	sublime.set_timeout(checkModulesAddInLine, 1)


def checkModulesAddInLine():
	global moduleAddInLine
	global moduleOpenInLine
	module = context.getModuleByImportString(moduleAddInLine)
	if module is not None:
		addModule(module)
		moduleAddInLine = None
	if moduleOpenInLine is not None:
		openModuleFile(context.getModuleByImportString(moduleOpenInLine))
		moduleOpenInLine = None
	pass


def openModuleFile(module):
	if module.type == "script":
		focus = int(context.settings["script_group"])
		sublime.active_window().focus_group(focus)
	elif module.type == "text":
		focus = int(context.settings["text_group"])
		sublime.active_window().focus_group(focus)
	sublime.active_window().open_file(module.getFullPath())


# application listner
class AppListener(sublime_plugin.EventListener):

	def on_post_save(self, view):
		global context
		if context is not None:
			if sublime.active_window().active_view().file_name() == context.settingsPath:
				getContext(sublime.active_window())
		pass

	def on_activated(self, view):
		if context is not None:
			if sublime.active_window() is not None:
				if sublime.active_window().id() != context.window.id():
					getContext(sublime.active_window())
			else:
				getContext(sublime.active_window())
		else:
			getContext(sublime.active_window())
			

def updateContext():
	getContext(sublime.active_window())
	pass

def moveModule():
	global context
	move_module.moveModuleInView(context, updateContext)

# select module
def selectModule(onSelectCallback, group):
	global shadowList
	global context
	shadowList = []
	list = []

	for module in group:
		module = filterModule(module)
		if module is not None:
			list.append([module.name, module.package])
			shadowList.append(module)
	context.window.show_quick_panel(list, onSelectCallback, 0)

def filterModule(module):
	if len(context.settings["excludes"]) > 0:
		for exclude in context.settings["excludes"]:
			if context.getBaseDir() + exclude in module.path + "/" + module.name:
				return None
	return module

def addModule(module):
	if module is None:
		return
	global context
	addEdit = editor.ModuleEdit(context.window.active_view().substr(sublime.Region(0, context.window.active_view().size())), context)
	# get define region
	defineRegion = addEdit.getDefineRegion()
	addEdit.addModule(module, "")
	edit = context.window.active_view().begin_edit()
	context.window.active_view().replace(edit, defineRegion, addEdit.render())
	context.window.active_view().end_edit(edit)


def onScriptSelectAdd(selectionIndex):
	if selectionIndex == -1:
		return
	global shadowList
	addModule(shadowList[selectionIndex])


def onTextSelectAdd(selectionIndex):
	if selectionIndex == -1:
		return
	global shadowList
	addModule(shadowList[selectionIndex])

# remove module
def removeModule():
	global context
	global currentModuleEdit
	currentModuleEdit = editor.ModuleEdit(context.window.active_view().substr(sublime.Region(0, context.window.active_view().size())), context)
	modules = currentModuleEdit.getModules()
	selectModule(onModuleSelectRemove, modules)

def onModuleSelectRemove(selectionIndex):
	if selectionIndex == -1:
		return
	global shadowList
	global currentModuleEdit
	global context
	currentModuleEdit.removeModule(shadowList[selectionIndex])
	edit = context.window.active_view().begin_edit()
	context.window.active_view().replace(edit, currentModuleEdit.getDefineRegion(), currentModuleEdit.render())
	context.window.active_view().end_edit(edit)

def createModule(importOnCreated, type):
	global context
	region = context.window.active_view().sel()[0]
	moduleName = ""
	if region.begin() != region.end():
		moduleName = context.window.active_view().substr(region)
	createConfig = {
		"type": type,
		"callback": onModuleCreated,
		"name": moduleName,
		"importOnCreated":importOnCreated
	}

	factory.createModule(context, createConfig)

def onModuleCreated(importString, createConfig):
	global moduleAddInLine
	global moduleOpenInLine
	if createConfig["importOnCreated"] == True:
		moduleAddInLine = importString
	moduleOpenInLine = importString
	module_parser.parseModules(context, onModulePareDone)


# main callback
def onMainActionSelected(selectionIndex):
	global context
	if selectionIndex == -1:
		return
	if len(context.settings["text_folder"]) > 0:
		if (selectionIndex == 0):
			selectModule(onScriptSelectAdd, context.getScriptModules())
		elif (selectionIndex == 1):
			selectModule(onTextSelectAdd, context.getTextModules())
		elif selectionIndex == 2:
			removeModule()
		elif selectionIndex == 3:
			createModule(False, "script")
		elif selectionIndex == 4:
			createModule(False, "text")
		elif selectionIndex == 5:
			createModule(True, "script")
		elif selectionIndex == 6:
			createModule(True, "text")
		elif selectionIndex == 7:
			moveModule()
	else:
		if (selectionIndex == 0):
			selectModule(onScriptSelectAdd, context.getScriptModules())
		elif selectionIndex == 1:
			removeModule()
		elif selectionIndex == 2:
			createModule(False, "script")
		elif selectionIndex == 3:
			createModule(True, "script")
		elif selectionIndex == 4:
			moveModule()


def onScriptSelectOpen(selectionIndex):
	if selectionIndex == -1:
		return
	global shadowList
	sublime.active_window().open_file(shadowList[selectionIndex].getFullPath())
	pass


def onTextSelectOpen(selectionIndex):
	if selectionIndex == -1:
		return
	global shadowList
	sublime.active_window().open_file(shadowList[selectionIndex].getFullPath())
	pass


def openModule(index):
	global context
	if context.settings["script_group"] == str(index):
		selectModule(onScriptSelectOpen, context.getScriptModules())
	elif context.settings["text_group"] == str(index):
		selectModule(onTextSelectOpen, context.getTextModules())


class SublimeRjsOpen1Command(sublime_plugin.WindowCommand):
	def run(slef):
		sublime.active_window().focus_group(0)
		openModule(0)


class SublimeRjsOpen2Command(sublime_plugin.WindowCommand):
	def run(slef):
		sublime.active_window().focus_group(1)
		openModule(1)


class SublimeRjsOpen3Command(sublime_plugin.WindowCommand):
	def run(slef):
		sublime.active_window().focus_group(2)
		openModule(2)


class SublimeRjsCommand(sublime_plugin.WindowCommand):
    def run(self):
    	global context
    	# get selection
    	createAndImportScript = "Create and import SCRIPT module"
    	createAndImportText = "Create and import TEXT module"
    	region = context.window.active_view().sel()[0]
    	if region.begin() != region.end():
    		createAndImportScript += " '" +context.window.active_view().substr(region)+"'"
    		createAndImportText += " '" +context.window.active_view().substr(region)+"'"

    	if len(context.settings["text_folder"]) > 0:
    		options = ["Import SCRIPT module", "Import TEXT module", "Remove module", "Create SCRIPT module", "Create TEXT module", createAndImportScript, createAndImportText, "Move/Rename module"]
    	else:
    		options = ["Import SCRIPT module", "Remove module", "Create SCRIPT module", createAndImportScript, "Move/Rename module"]
    	self.window.show_quick_panel(options, onMainActionSelected, 0)


class AddSublimeRjsCommand(sublime_plugin.ApplicationCommand):
	def run(self, dirs):
		srcFile = sublime.packages_path() + "/SublimeRJS/SublimeRJS Project.sublime-settings"
		destFile = dirs[0] + "/SublimeRJS.sublime-settings"
		shutil.copyfile(srcFile, destFile)
		sublime.active_window().open_file(destFile)
		getContext(sublime.active_window())		

# startup
getContext(sublime.active_window())

########NEW FILE########
